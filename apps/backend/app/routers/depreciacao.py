"""Router de Depreciação Patrimonial (NBCASP / IPSAS 17).

Cobre:
  - Configuração de parâmetros de depreciação por bem (data aquisição, vida útil,
    valor residual, método)
  - Cálculo e persistência dos lançamentos mensais
  - Relatório histórico por bem (com export CSV)
  - Dashboard consolidado por período

MÉTODOS SUPORTADOS:
  linear            (NBC T 16.9 padrão)
    quota_mensal = (valor_aquisicao - valor_residual) / vida_util_meses
    A quota é constante; para quando valor_contábil <= valor_residual.

  saldo_decrescente  (acelarado)
    taxa_mensal = 2 / vida_util_meses
    quota_mes  = valor_contabil_anterior * taxa_mensal
    Para quando valor_contábil <= valor_residual.

IDEMPOTÊNCIA:
  POST /depreciacao/calcular é idempotente por (asset_id, periodo): se já existe
  um lançamento para o par, ele é recalculado com base nos lançamentos anteriores.

INTEGRAÇÃO:
  O campo Asset.value NÃO é alterado pelo módulo de depreciação para preservar
  compatibilidade com os módulos existentes. O valor contábil líquido está em
  LancamentoDepreciacao.valor_contabil_liquido.
"""

import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    Asset,
    ConfiguracaoDepreciacao,
    LancamentoDepreciacao,
    RoleEnum,
    User,
)
from ..schemas import (
    CalcularDepreciacaoRequest,
    ConfiguracaoDepreciacaoCreate,
    ConfiguracaoDepreciacaoOut,
    ConfiguracaoDepreciacaoUpdate,
    LancamentoDepreciacaoOut,
)

router = APIRouter(prefix="/depreciacao", tags=["depreciacao"])

METODOS_VALIDOS = {"linear", "saldo_decrescente"}


# ── Engine de cálculo ─────────────────────────────────────────────────────────

def _calcular_quota(cfg: ConfiguracaoDepreciacao, valor_contabil_anterior: float) -> float:
    """Retorna a quota de depreciação para o próximo período."""
    if valor_contabil_anterior <= cfg.valor_residual:
        return 0.0

    if cfg.metodo == "linear":
        quota = (cfg.valor_aquisicao - cfg.valor_residual) / cfg.vida_util_meses
    else:  # saldo_decrescente
        taxa = 2.0 / cfg.vida_util_meses
        quota = valor_contabil_anterior * taxa

    # Limita para não ultrapassar o piso do valor residual
    maximo = valor_contabil_anterior - cfg.valor_residual
    return round(min(quota, max(0.0, maximo)), 6)


def _depreciacao_acumulada_ate(db: Session, asset_id: int, periodo_exclusive: str) -> float:
    """Retorna depreciação acumulada em todos os lançamentos anteriores ao período."""
    result = (
        db.query(func.sum(LancamentoDepreciacao.valor_depreciado))
        .filter(
            LancamentoDepreciacao.asset_id == asset_id,
            LancamentoDepreciacao.periodo < periodo_exclusive,
        )
        .scalar()
    )
    return result or 0.0


def _processar_bem(db: Session, cfg: ConfiguracaoDepreciacao, periodo: str, user_id: int | None) -> dict:
    """Calcula e persiste (upsert) o lançamento de um bem para um período."""
    dep_acum_anterior = _depreciacao_acumulada_ate(db, cfg.asset_id, periodo)
    valor_contabil_anterior = cfg.valor_aquisicao - dep_acum_anterior

    quota = _calcular_quota(cfg, valor_contabil_anterior)
    dep_acum_nova = round(dep_acum_anterior + quota, 6)
    vcl = round(cfg.valor_aquisicao - dep_acum_nova, 6)

    # Upsert
    lancamento = (
        db.query(LancamentoDepreciacao)
        .filter(LancamentoDepreciacao.asset_id == cfg.asset_id,
                LancamentoDepreciacao.periodo == periodo)
        .first()
    )
    if lancamento:
        lancamento.valor_depreciado = quota
        lancamento.depreciacao_acumulada = dep_acum_nova
        lancamento.valor_contabil_liquido = vcl
        lancamento.criado_por_id = user_id
        action = "update"
    else:
        lancamento = LancamentoDepreciacao(
            asset_id=cfg.asset_id,
            periodo=periodo,
            valor_depreciado=quota,
            depreciacao_acumulada=dep_acum_nova,
            valor_contabil_liquido=vcl,
            criado_por_id=user_id,
        )
        db.add(lancamento)
        action = "create"

    return {"action": action, "quota": quota}


# ── Configuração ──────────────────────────────────────────────────────────────

@router.post("/config", response_model=ConfiguracaoDepreciacaoOut, status_code=201)
def criar_configuracao(
    payload: ConfiguracaoDepreciacaoCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony)),
):
    if payload.metodo not in METODOS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"metodo inválido; use: {METODOS_VALIDOS}")
    if payload.vida_util_meses <= 0:
        raise HTTPException(status_code=422, detail="vida_util_meses deve ser positivo")
    if payload.valor_residual < 0:
        raise HTTPException(status_code=422, detail="valor_residual não pode ser negativo")
    if payload.valor_aquisicao <= 0:
        raise HTTPException(status_code=422, detail="valor_aquisicao deve ser positivo")
    if payload.valor_residual >= payload.valor_aquisicao:
        raise HTTPException(status_code=422, detail="valor_residual deve ser menor que valor_aquisicao")
    if not db.get(Asset, payload.asset_id):
        raise HTTPException(status_code=404, detail="Bem não encontrado")
    existente = (
        db.query(ConfiguracaoDepreciacao)
        .filter(ConfiguracaoDepreciacao.asset_id == payload.asset_id)
        .first()
    )
    if existente:
        raise HTTPException(status_code=409, detail="Configuração já existe; use PATCH para atualizar")

    cfg = ConfiguracaoDepreciacao(**payload.model_dump())
    db.add(cfg)
    db.flush()
    audit_data = payload.model_dump()
    audit_data["data_aquisicao"] = str(audit_data["data_aquisicao"])
    write_audit(db, user_id=current.id, action="create", entity="configuracoes_depreciacao",
                entity_id=str(cfg.id), after_data=audit_data)
    db.commit()
    db.refresh(cfg)
    return cfg


@router.get("/config/{asset_id}", response_model=ConfiguracaoDepreciacaoOut)
def get_configuracao(
    asset_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cfg = db.query(ConfiguracaoDepreciacao).filter(ConfiguracaoDepreciacao.asset_id == asset_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuração de depreciação não encontrada para este bem")
    return cfg


@router.get("/config", response_model=None)
def list_configuracoes(
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ConfiguracaoDepreciacao)
    total = q.count()
    items = q.order_by(ConfiguracaoDepreciacao.id).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.patch("/config/{asset_id}", response_model=ConfiguracaoDepreciacaoOut)
def atualizar_configuracao(
    asset_id: int,
    payload: ConfiguracaoDepreciacaoUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony)),
):
    cfg = db.query(ConfiguracaoDepreciacao).filter(ConfiguracaoDepreciacao.asset_id == asset_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    updates = payload.model_dump(exclude_none=True)
    if "metodo" in updates and updates["metodo"] not in METODOS_VALIDOS:
        raise HTTPException(status_code=422, detail=f"metodo inválido; use: {METODOS_VALIDOS}")
    if "vida_util_meses" in updates and updates["vida_util_meses"] <= 0:
        raise HTTPException(status_code=422, detail="vida_util_meses deve ser positivo")
    before = {k: getattr(cfg, k) for k in updates}
    for field, value in updates.items():
        setattr(cfg, field, value)
    if "data_aquisicao" in updates:
        before["data_aquisicao"] = str(before.get("data_aquisicao", ""))
        updates["data_aquisicao"] = str(updates["data_aquisicao"])
    write_audit(db, user_id=current.id, action="update", entity="configuracoes_depreciacao",
                entity_id=str(cfg.id), before_data=before, after_data=updates)
    db.commit()
    db.refresh(cfg)
    return cfg


# ── Cálculo ───────────────────────────────────────────────────────────────────

@router.post("/calcular", status_code=200)
def calcular_depreciacao(
    payload: CalcularDepreciacaoRequest,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony)),
):
    """Calcula e persiste os lançamentos de depreciação para o período informado.

    Se `asset_id` for informado, processa apenas aquele bem.
    Caso contrário, processa todos os bens com configuração ativa.
    Idempotente: re-executar para o mesmo período recalcula o lançamento existente.
    """
    try:
        year, month = int(payload.periodo[:4]), int(payload.periodo[5:7])
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Período inválido; use YYYY-MM")

    q = db.query(ConfiguracaoDepreciacao).filter(ConfiguracaoDepreciacao.ativo == True)
    if payload.asset_id:
        if not db.get(Asset, payload.asset_id):
            raise HTTPException(status_code=404, detail="Bem não encontrado")
        q = q.filter(ConfiguracaoDepreciacao.asset_id == payload.asset_id)

    cfgs = q.all()
    if not cfgs:
        raise HTTPException(status_code=404, detail="Nenhum bem com configuração de depreciação ativa encontrado")

    criados = 0
    atualizados = 0
    total_depreciado = 0.0

    for cfg in cfgs:
        resultado = _processar_bem(db, cfg, payload.periodo, current.id)
        if resultado["action"] == "create":
            criados += 1
        else:
            atualizados += 1
        total_depreciado += resultado["quota"]

    write_audit(db, user_id=current.id, action="create", entity="lancamentos_depreciacao",
                entity_id=payload.periodo,
                after_data={"periodo": payload.periodo, "criados": criados,
                            "atualizados": atualizados, "total_depreciado": round(total_depreciado, 2)})
    db.commit()

    return {
        "periodo": payload.periodo,
        "criados": criados,
        "atualizados": atualizados,
        "total_depreciado": round(total_depreciado, 2),
    }


# ── Lançamentos ───────────────────────────────────────────────────────────────

@router.get("/lancamentos", response_model=None)
def list_lancamentos(
    asset_id: int | None = None,
    periodo: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(LancamentoDepreciacao)
    if asset_id:
        q = q.filter(LancamentoDepreciacao.asset_id == asset_id)
    if periodo:
        q = q.filter(LancamentoDepreciacao.periodo == periodo)
    total = q.count()
    items = q.order_by(LancamentoDepreciacao.periodo.desc(), LancamentoDepreciacao.asset_id).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


# ── Relatório histórico por bem ────────────────────────────────────────────────

@router.get("/relatorio/{asset_id}")
def relatorio_ativo(
    asset_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório histórico completo de depreciação de um bem."""
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Bem não encontrado")
    cfg = db.query(ConfiguracaoDepreciacao).filter(ConfiguracaoDepreciacao.asset_id == asset_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuração de depreciação não encontrada para este bem")

    lancamentos = (
        db.query(LancamentoDepreciacao)
        .filter(LancamentoDepreciacao.asset_id == asset_id)
        .order_by(LancamentoDepreciacao.periodo)
        .all()
    )

    return {
        "asset_id": asset.id,
        "asset_tag": asset.tag,
        "asset_description": asset.description,
        "valor_aquisicao": cfg.valor_aquisicao,
        "valor_residual": cfg.valor_residual,
        "vida_util_meses": cfg.vida_util_meses,
        "metodo": cfg.metodo,
        "data_aquisicao": str(cfg.data_aquisicao),
        "lancamentos": [
            {
                "periodo": l.periodo,
                "valor_depreciado": l.valor_depreciado,
                "depreciacao_acumulada": l.depreciacao_acumulada,
                "valor_contabil_liquido": l.valor_contabil_liquido,
            }
            for l in lancamentos
        ],
    }


@router.get("/relatorio/{asset_id}/csv")
def relatorio_ativo_csv(
    asset_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony, RoleEnum.read_only)),
):
    asset = db.get(Asset, asset_id)
    if not asset:
        raise HTTPException(status_code=404, detail="Bem não encontrado")
    cfg = db.query(ConfiguracaoDepreciacao).filter(ConfiguracaoDepreciacao.asset_id == asset_id).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuração de depreciação não encontrada")

    lancamentos = (
        db.query(LancamentoDepreciacao)
        .filter(LancamentoDepreciacao.asset_id == asset_id)
        .order_by(LancamentoDepreciacao.periodo)
        .all()
    )

    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["tombamento", "descricao", "valor_aquisicao", "metodo", "periodo",
                     "valor_depreciado", "depreciacao_acumulada", "valor_contabil_liquido"])
    for l in lancamentos:
        writer.writerow([
            asset.tag, asset.description, cfg.valor_aquisicao, cfg.metodo,
            l.periodo, l.valor_depreciado, l.depreciacao_acumulada, l.valor_contabil_liquido,
        ])

    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=depreciacao_{asset.tag}_{asset_id}.csv"},
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(
    periodo: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.patrimony, RoleEnum.read_only)),
):
    """KPIs consolidados de depreciação para um período."""
    try:
        year, month = int(periodo[:4]), int(periodo[5:7])
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Período inválido; use YYYY-MM")

    total_bens_configurados = db.query(func.count(ConfiguracaoDepreciacao.id)).filter(
        ConfiguracaoDepreciacao.ativo == True
    ).scalar() or 0

    total_bens_com_lancamento = db.query(func.count(LancamentoDepreciacao.id)).filter(
        LancamentoDepreciacao.periodo == periodo
    ).scalar() or 0

    total_depreciado_periodo = db.query(func.sum(LancamentoDepreciacao.valor_depreciado)).filter(
        LancamentoDepreciacao.periodo == periodo
    ).scalar() or 0.0

    total_depreciacao_acumulada = db.query(func.sum(LancamentoDepreciacao.depreciacao_acumulada)).filter(
        LancamentoDepreciacao.periodo == periodo
    ).scalar() or 0.0

    total_vcl = db.query(func.sum(LancamentoDepreciacao.valor_contabil_liquido)).filter(
        LancamentoDepreciacao.periodo == periodo
    ).scalar() or 0.0

    total_valor_aquisicao = db.query(func.sum(ConfiguracaoDepreciacao.valor_aquisicao)).filter(
        ConfiguracaoDepreciacao.ativo == True
    ).scalar() or 0.0

    # Top 10 bens por depreciação no período
    top_lancamentos = (
        db.query(LancamentoDepreciacao)
        .filter(LancamentoDepreciacao.periodo == periodo)
        .order_by(LancamentoDepreciacao.valor_depreciado.desc())
        .limit(10)
        .all()
    )
    top_bens = []
    for l in top_lancamentos:
        a = db.get(Asset, l.asset_id)
        top_bens.append({
            "asset_id": l.asset_id,
            "asset_tag": a.tag if a else "",
            "asset_description": a.description if a else "",
            "valor_depreciado": l.valor_depreciado,
            "valor_contabil_liquido": l.valor_contabil_liquido,
        })

    return {
        "periodo": periodo,
        "total_bens_configurados": total_bens_configurados,
        "total_bens_com_lancamento": total_bens_com_lancamento,
        "total_depreciado_periodo": round(float(total_depreciado_periodo), 2),
        "total_depreciacao_acumulada": round(float(total_depreciacao_acumulada), 2),
        "total_valor_contabil_liquido": round(float(total_vcl), 2),
        "total_valor_aquisicao": round(float(total_valor_aquisicao), 2),
        "top_bens": top_bens,
    }
