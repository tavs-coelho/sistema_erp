"""Router NFS-e / ITBI — Receitas de ISS e transmissão imobiliária.

Rotas NFS-e  (prefixo /nfse):
  POST   /nfse/emitir                          — emite NFS-e e cria LancamentoTributario ISS
  GET    /nfse                                 — lista com filtros + paginação
  GET    /nfse/{id}                            — detalhe
  PATCH  /nfse/{id}/cancelar                   — cancela nota e lançamento associado
  GET    /nfse/relatorio?export=csv            — relatório JSON ou CSV

Rotas ITBI   (prefixo /itbi):
  POST   /itbi/registrar                       — registra operação e cria LancamentoTributario ITBI
  GET    /itbi                                 — lista com filtros + paginação
  GET    /itbi/{id}                            — detalhe
  PATCH  /itbi/{id}/cancelar                   — cancela operação e lançamento associado
  GET    /itbi/relatorio?export=csv            — relatório JSON ou CSV

Dashboard:
  GET    /nfse-itbi/dashboard                  — KPIs consolidados NFS-e + ITBI

LÓGICA DE CÁLCULO:
  ISS   = (valor_servico - valor_deducoes) * aliquota_iss / 100
  ITBI  — base_calculo = max(valor_declarado, valor_venal_referencia)
          valor_devido = base_calculo * aliquota_itbi / 100
"""

import csv
import uuid
from datetime import date, datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    Contribuinte,
    ImovelCadastral,
    LancamentoTributario,
    NotaFiscalServico,
    OperacaoITBI,
    RoleEnum,
    User,
)
from ..schemas import ITBICreate, ITBIOut, ITBIUpdate, NFSeCreate, NFSeOut, NFSeUpdate

router = APIRouter(tags=["nfse_itbi"])

# ── Alíquota ISS padrão quando não informada pelo usuário (em %) ──────────────
ALIQUOTA_ISS_PADRAO = 2.0
ALIQUOTA_ITBI_PADRAO = 2.0


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


def _nfse_numero(db: Session) -> str:
    year = date.today().year
    seq = db.query(func.count(NotaFiscalServico.id)).scalar() + 1
    return f"NFS/{year}-{seq:04d}"


def _itbi_numero(db: Session) -> str:
    year = date.today().year
    seq = db.query(func.count(OperacaoITBI.id)).scalar() + 1
    return f"ITBI/{year}-{seq:04d}"


def _calc_iss(valor_servico: float, valor_deducoes: float, aliquota: float) -> float:
    base = max(valor_servico - valor_deducoes, 0.0)
    return round(base * aliquota / 100, 2)


def _calc_itbi(valor_declarado: float, valor_venal_ref: float, aliquota: float) -> tuple[float, float]:
    base = max(valor_declarado, valor_venal_ref)
    valor = round(base * aliquota / 100, 2)
    return base, valor


def _criar_lancamento_tributario(
    db: Session,
    contribuinte_id: int,
    imovel_id: int | None,
    tributo: str,
    competencia: str,
    exercicio: int,
    valor: float,
    vencimento: date,
    observacoes: str = "",
) -> LancamentoTributario:
    lanc = LancamentoTributario(
        contribuinte_id=contribuinte_id,
        imovel_id=imovel_id,
        tributo=tributo,
        competencia=competencia,
        exercicio=exercicio,
        valor_principal=valor,
        valor_total=valor,
        vencimento=vencimento,
        observacoes=observacoes,
    )
    db.add(lanc)
    db.flush()
    return lanc


# ══════════════════════════════════════════════════════════════════════════════
#  NFS-e
# ══════════════════════════════════════════════════════════════════════════════

nfse_router = APIRouter(prefix="/nfse", tags=["nfse"])


def _nfse_out(n: NotaFiscalServico) -> dict:
    return NFSeOut.model_validate(n).model_dump()


@nfse_router.post("/emitir", response_model=NFSeOut, status_code=201)
def emitir_nfse(
    payload: NFSeCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Emite uma NFS-e simplificada e gera o LancamentoTributario de ISS automaticamente."""
    if not db.get(Contribuinte, payload.prestador_id):
        raise HTTPException(status_code=404, detail="Prestador não encontrado")
    if payload.tomador_id and not db.get(Contribuinte, payload.tomador_id):
        raise HTTPException(status_code=404, detail="Tomador não encontrado")
    if payload.aliquota_iss <= 0:
        raise HTTPException(status_code=422, detail="Alíquota ISS deve ser maior que zero")

    valor_iss = _calc_iss(payload.valor_servico, payload.valor_deducoes, payload.aliquota_iss)

    # Cria o lançamento tributário ISS
    vencimento = date(payload.data_emissao.year, payload.data_emissao.month, 20)
    lanc = _criar_lancamento_tributario(
        db=db,
        contribuinte_id=payload.prestador_id,
        imovel_id=None,
        tributo="ISS",
        competencia=payload.competencia,
        exercicio=payload.data_emissao.year,
        valor=valor_iss,
        vencimento=vencimento,
        observacoes=f"ISS gerado automaticamente pela NFS-e (competência {payload.competencia})",
    )

    nota = NotaFiscalServico(
        numero=_nfse_numero(db),
        prestador_id=payload.prestador_id,
        tomador_id=payload.tomador_id,
        descricao_servico=payload.descricao_servico,
        codigo_servico=payload.codigo_servico,
        competencia=payload.competencia,
        data_emissao=payload.data_emissao,
        valor_servico=payload.valor_servico,
        valor_deducoes=payload.valor_deducoes,
        aliquota_iss=payload.aliquota_iss,
        valor_iss=valor_iss,
        retencao_fonte=payload.retencao_fonte,
        status="emitida",
        lancamento_id=lanc.id,
        observacoes=payload.observacoes,
    )
    db.add(nota)
    db.flush()
    write_audit(
        db, user_id=current.id, action="create", entity="notas_fiscais_servico",
        entity_id=str(nota.id),
        after_data={"numero": nota.numero, "prestador_id": nota.prestador_id,
                    "valor_servico": nota.valor_servico, "valor_iss": nota.valor_iss},
    )
    db.commit()
    db.refresh(nota)
    return nota


@nfse_router.get("", response_model=None)
def list_nfse(
    prestador_id: int | None = None,
    tomador_id: int | None = None,
    status: str | None = None,
    competencia: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(NotaFiscalServico)
    if prestador_id:
        q = q.filter(NotaFiscalServico.prestador_id == prestador_id)
    if tomador_id:
        q = q.filter(NotaFiscalServico.tomador_id == tomador_id)
    if status:
        q = q.filter(NotaFiscalServico.status == status)
    if competencia:
        q = q.filter(NotaFiscalServico.competencia == competencia)
    if data_inicio:
        q = q.filter(NotaFiscalServico.data_emissao >= data_inicio)
    if data_fim:
        q = q.filter(NotaFiscalServico.data_emissao <= data_fim)
    q = q.order_by(NotaFiscalServico.data_emissao.desc())
    return _paginate(q, page, size)


@nfse_router.get("/relatorio")
def relatorio_nfse(
    competencia: str | None = None,
    status: str | None = None,
    export: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório de NFS-e emitidas. Use ?export=csv para download CSV."""
    q = db.query(NotaFiscalServico)
    if competencia:
        q = q.filter(NotaFiscalServico.competencia == competencia)
    if status:
        q = q.filter(NotaFiscalServico.status == status)
    q = q.order_by(NotaFiscalServico.data_emissao.desc())

    if export == "csv":
        notas = q.all()
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["numero", "prestador_id", "tomador_id", "competencia", "data_emissao",
                         "valor_servico", "valor_deducoes", "aliquota_iss", "valor_iss",
                         "retencao_fonte", "status", "lancamento_id"])
        for n in notas:
            writer.writerow([n.numero, n.prestador_id, n.tomador_id, n.competencia,
                             n.data_emissao, n.valor_servico, n.valor_deducoes, n.aliquota_iss,
                             n.valor_iss, n.retencao_fonte, n.status, n.lancamento_id])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=nfse_{date.today()}.csv"},
        )
    return _paginate(q, page, size)


@nfse_router.get("/{nfse_id}", response_model=NFSeOut)
def get_nfse(nfse_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    nota = db.get(NotaFiscalServico, nfse_id)
    if not nota:
        raise HTTPException(status_code=404, detail="NFS-e não encontrada")
    return nota


@nfse_router.patch("/{nfse_id}/cancelar", response_model=NFSeOut)
def cancelar_nfse(
    nfse_id: int,
    motivo: str = Query("", description="Motivo do cancelamento"),
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Cancela uma NFS-e emitida e o lançamento tributário de ISS associado."""
    nota = db.get(NotaFiscalServico, nfse_id)
    if not nota:
        raise HTTPException(status_code=404, detail="NFS-e não encontrada")
    if nota.status != "emitida":
        raise HTTPException(status_code=422, detail=f"NFS-e em status '{nota.status}' não pode ser cancelada")

    nota.status = "cancelada"
    nota.observacoes = (nota.observacoes + f"\nCancelamento: {motivo}").strip()

    if nota.lancamento_id:
        lanc = db.get(LancamentoTributario, nota.lancamento_id)
        if lanc and lanc.status == "aberto":
            lanc.status = "cancelado"
            lanc.observacoes = (lanc.observacoes + f"\nCancelado via NFS-e #{nota.numero}: {motivo}").strip()

    write_audit(db, user_id=current.id, action="update", entity="notas_fiscais_servico",
                entity_id=str(nota.id), after_data={"status": "cancelada", "motivo": motivo})
    db.commit()
    db.refresh(nota)
    return nota


# ══════════════════════════════════════════════════════════════════════════════
#  ITBI
# ══════════════════════════════════════════════════════════════════════════════

itbi_router = APIRouter(prefix="/itbi", tags=["itbi"])


@itbi_router.post("/registrar", response_model=ITBIOut, status_code=201)
def registrar_itbi(
    payload: ITBICreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Registra uma operação de ITBI e gera o LancamentoTributario automaticamente."""
    if not db.get(Contribuinte, payload.transmitente_id):
        raise HTTPException(status_code=404, detail="Transmitente não encontrado")
    if not db.get(Contribuinte, payload.adquirente_id):
        raise HTTPException(status_code=404, detail="Adquirente não encontrado")
    imovel = db.get(ImovelCadastral, payload.imovel_id)
    if not imovel:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    if payload.aliquota_itbi <= 0:
        raise HTTPException(status_code=422, detail="Alíquota ITBI deve ser maior que zero")

    # Usa valor venal do imóvel como referência se não informado
    venal_ref = payload.valor_venal_referencia if payload.valor_venal_referencia > 0 else imovel.valor_venal
    base_calculo, valor_devido = _calc_itbi(payload.valor_declarado, venal_ref, payload.aliquota_itbi)

    competencia = payload.data_operacao.strftime("%Y-%m")
    lanc = _criar_lancamento_tributario(
        db=db,
        contribuinte_id=payload.adquirente_id,
        imovel_id=payload.imovel_id,
        tributo="ITBI",
        competencia=competencia,
        exercicio=payload.data_operacao.year,
        valor=valor_devido,
        vencimento=payload.data_operacao,
        observacoes=f"ITBI gerado automaticamente para operação {payload.natureza_operacao}",
    )

    op = OperacaoITBI(
        numero=_itbi_numero(db),
        transmitente_id=payload.transmitente_id,
        adquirente_id=payload.adquirente_id,
        imovel_id=payload.imovel_id,
        natureza_operacao=payload.natureza_operacao,
        data_operacao=payload.data_operacao,
        valor_declarado=payload.valor_declarado,
        valor_venal_referencia=venal_ref,
        base_calculo=base_calculo,
        aliquota_itbi=payload.aliquota_itbi,
        valor_devido=valor_devido,
        status="aberto",
        lancamento_id=lanc.id,
        observacoes=payload.observacoes,
    )
    db.add(op)
    db.flush()
    write_audit(
        db, user_id=current.id, action="create", entity="operacoes_itbi",
        entity_id=str(op.id),
        after_data={"numero": op.numero, "imovel_id": op.imovel_id,
                    "base_calculo": op.base_calculo, "valor_devido": op.valor_devido},
    )
    db.commit()
    db.refresh(op)
    return op


@itbi_router.get("", response_model=None)
def list_itbi(
    adquirente_id: int | None = None,
    transmitente_id: int | None = None,
    imovel_id: int | None = None,
    status: str | None = None,
    natureza_operacao: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(OperacaoITBI)
    if adquirente_id:
        q = q.filter(OperacaoITBI.adquirente_id == adquirente_id)
    if transmitente_id:
        q = q.filter(OperacaoITBI.transmitente_id == transmitente_id)
    if imovel_id:
        q = q.filter(OperacaoITBI.imovel_id == imovel_id)
    if status:
        q = q.filter(OperacaoITBI.status == status)
    if natureza_operacao:
        q = q.filter(OperacaoITBI.natureza_operacao == natureza_operacao)
    if data_inicio:
        q = q.filter(OperacaoITBI.data_operacao >= data_inicio)
    if data_fim:
        q = q.filter(OperacaoITBI.data_operacao <= data_fim)
    q = q.order_by(OperacaoITBI.data_operacao.desc())
    return _paginate(q, page, size)


@itbi_router.get("/relatorio")
def relatorio_itbi(
    status: str | None = None,
    natureza_operacao: str | None = None,
    export: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório de operações ITBI. Use ?export=csv para download CSV."""
    q = db.query(OperacaoITBI)
    if status:
        q = q.filter(OperacaoITBI.status == status)
    if natureza_operacao:
        q = q.filter(OperacaoITBI.natureza_operacao == natureza_operacao)
    q = q.order_by(OperacaoITBI.data_operacao.desc())

    if export == "csv":
        ops = q.all()
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["numero", "transmitente_id", "adquirente_id", "imovel_id",
                         "natureza_operacao", "data_operacao", "valor_declarado",
                         "valor_venal_referencia", "base_calculo", "aliquota_itbi",
                         "valor_devido", "status", "lancamento_id"])
        for o in ops:
            writer.writerow([o.numero, o.transmitente_id, o.adquirente_id, o.imovel_id,
                             o.natureza_operacao, o.data_operacao, o.valor_declarado,
                             o.valor_venal_referencia, o.base_calculo, o.aliquota_itbi,
                             o.valor_devido, o.status, o.lancamento_id])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=itbi_{date.today()}.csv"},
        )
    return _paginate(q, page, size)


@itbi_router.get("/{itbi_id}", response_model=ITBIOut)
def get_itbi(itbi_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    op = db.get(OperacaoITBI, itbi_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operação ITBI não encontrada")
    return op


@itbi_router.patch("/{itbi_id}/cancelar", response_model=ITBIOut)
def cancelar_itbi(
    itbi_id: int,
    motivo: str = Query("", description="Motivo do cancelamento"),
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Cancela uma operação ITBI e o lançamento tributário associado."""
    op = db.get(OperacaoITBI, itbi_id)
    if not op:
        raise HTTPException(status_code=404, detail="Operação ITBI não encontrada")
    if op.status != "aberto":
        raise HTTPException(status_code=422, detail=f"Operação ITBI em status '{op.status}' não pode ser cancelada")

    op.status = "cancelado"
    op.observacoes = (op.observacoes + f"\nCancelamento: {motivo}").strip()

    if op.lancamento_id:
        lanc = db.get(LancamentoTributario, op.lancamento_id)
        if lanc and lanc.status == "aberto":
            lanc.status = "cancelado"
            lanc.observacoes = (lanc.observacoes + f"\nCancelado via ITBI #{op.numero}: {motivo}").strip()

    write_audit(db, user_id=current.id, action="update", entity="operacoes_itbi",
                entity_id=str(op.id), after_data={"status": "cancelado", "motivo": motivo})
    db.commit()
    db.refresh(op)
    return op


# ══════════════════════════════════════════════════════════════════════════════
#  Dashboard consolidado NFS-e + ITBI
# ══════════════════════════════════════════════════════════════════════════════

dashboard_router = APIRouter(prefix="/nfse-itbi", tags=["nfse_itbi"])


@dashboard_router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """KPIs consolidados NFS-e + ITBI."""
    # NFS-e
    nfse_total = db.query(func.count(NotaFiscalServico.id)).scalar() or 0
    nfse_emitidas = db.query(func.count(NotaFiscalServico.id)).filter(NotaFiscalServico.status == "emitida").scalar() or 0
    nfse_canceladas = db.query(func.count(NotaFiscalServico.id)).filter(NotaFiscalServico.status == "cancelada").scalar() or 0
    total_iss_emitido = db.query(func.coalesce(func.sum(NotaFiscalServico.valor_iss), 0.0)).filter(
        NotaFiscalServico.status == "emitida"
    ).scalar() or 0.0
    total_servicos_emitido = db.query(func.coalesce(func.sum(NotaFiscalServico.valor_servico), 0.0)).filter(
        NotaFiscalServico.status == "emitida"
    ).scalar() or 0.0

    # ITBI
    itbi_total = db.query(func.count(OperacaoITBI.id)).scalar() or 0
    itbi_aberto = db.query(func.count(OperacaoITBI.id)).filter(OperacaoITBI.status == "aberto").scalar() or 0
    itbi_pago = db.query(func.count(OperacaoITBI.id)).filter(OperacaoITBI.status == "pago").scalar() or 0
    itbi_cancelado = db.query(func.count(OperacaoITBI.id)).filter(OperacaoITBI.status == "cancelado").scalar() or 0
    total_itbi_aberto = db.query(func.coalesce(func.sum(OperacaoITBI.valor_devido), 0.0)).filter(
        OperacaoITBI.status == "aberto"
    ).scalar() or 0.0
    total_itbi_arrecadado = db.query(func.coalesce(func.sum(OperacaoITBI.valor_devido), 0.0)).filter(
        OperacaoITBI.status == "pago"
    ).scalar() or 0.0

    # ISS arrecadado (lançamentos pagos)
    from ..models import LancamentoTributario as LT
    total_iss_arrecadado = (
        db.query(func.coalesce(func.sum(LT.valor_total), 0.0))
        .filter(LT.tributo == "ISS", LT.status == "pago")
        .scalar() or 0.0
    )

    return {
        "nfse": {
            "total": nfse_total,
            "emitidas": nfse_emitidas,
            "canceladas": nfse_canceladas,
            "total_valor_servicos": round(total_servicos_emitido, 2),
            "total_iss_emitido": round(total_iss_emitido, 2),
            "total_iss_arrecadado": round(total_iss_arrecadado, 2),
        },
        "itbi": {
            "total": itbi_total,
            "aberto": itbi_aberto,
            "pago": itbi_pago,
            "cancelado": itbi_cancelado,
            "total_pendente": round(total_itbi_aberto, 2),
            "total_arrecadado": round(total_itbi_arrecadado, 2),
        },
    }


# ── Aggregate all sub-routers under a single router ──────────────────────────
# included as: app.include_router(nfse_itbi.router)
# The dashboard_router, nfse_router, itbi_router are standalone APIRouters;
# we export a combined `router` here for simplicity.

# Re-export all three as a list; main.py will include each individually.
all_routers = [nfse_router, itbi_router, dashboard_router]
