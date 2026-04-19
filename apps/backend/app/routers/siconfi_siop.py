"""Router SICONFI / SIOP — camada preparatória de exportação.

FINALIDADE:
  Separar a *preparação* dos dados de prestação de contas do *envio* ao governo
  federal. Esta camada gera os dados estruturados a partir dos módulos já
  existentes do ERP, valida internamente e registra o log de exportação.

MÓDULOS MAPEADOS:
  ┌──────────────────────────┬─────────────────────────────────────────────────┐
  │ ERP                      │ SICONFI / SIOP                                  │
  ├──────────────────────────┼─────────────────────────────────────────────────┤
  │ FiscalYear + LOAItem     │ FINBRA — Balanço Orçamentário (Receita/Despesa) │
  │ RevenueEntry             │ FINBRA — Receita Arrecadada por categoria        │
  │ Commitment+Liquidation+  │ FINBRA — Despesa Empenhada/Liquidada/Paga       │
  │   Payment                │                                                  │
  │ Payslip                  │ RGF — Despesa de Pessoal (proxy folha bruta)     │
  │ LOA + LOAItem            │ RREO — Receita e Despesa por Função              │
  │ PPA + PPAProgram         │ SIOP — Programas e Ações do PPA                  │
  │ LDO + LDOGoal            │ SIOP — Metas e Diretrizes da LDO                 │
  └──────────────────────────┴─────────────────────────────────────────────────┘

PREMISSAS E LIMITAÇÕES (ver docs/siconfi-siop.md):
  * Não realiza envio via webservice gov.br — apenas gera payloads exportáveis.
  * Código IBGE, CNPJ e esfera devem ser configurados em /siconfi/config.
  * Despesa de pessoal = soma bruta das folhas (Payslip.gross_amount); não
    inclui Encargos Patronais porque não há módulo de previdência própria.
  * Não implementa classificação funcional programática completa (sem vinculação
    entre Commitment e LOAItem); função é inferida do BudgetAllocation.code.
  * Chaves SICONFI reais (natureza de receita 4-8 dígitos, classificação
    econômica da despesa) precisam ser mapeadas manualmente após implantação.
"""

import json
from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    BudgetAllocation,
    Commitment,
    ConfiguracaoEntidade,
    ExportacaoSiconfi,
    FiscalYear,
    LOA,
    LOAItem,
    LDO,
    LDOGoal,
    Liquidation,
    Payment,
    Payslip,
    PPA,
    PPAProgram,
    RevenueEntry,
    RoleEnum,
    User,
)
from ..schemas import (
    ConfiguracaoEntidadeCreate,
    ConfiguracaoEntidadeOut,
    ExportacaoOut,
    ExportacaoRequest,
    InconsistenciaItem,
)

router = APIRouter(prefix="/siconfi", tags=["siconfi"])

LIMITE_PESSOAL_MUNICIPIO = 0.60   # 60 % RCL — LRF art. 19, III
LIMITE_ALERTA = 0.54              # 90 % do limite


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fy(db: Session, exercicio: int) -> FiscalYear | None:
    return db.query(FiscalYear).filter(FiscalYear.year == exercicio).first()


def _r2(v: float) -> float:
    return round(v, 2)


def _receita_arrecadada(db: Session, inicio: date, fim: date) -> float:
    return float(
        db.query(func.coalesce(func.sum(RevenueEntry.amount), 0.0))
        .filter(RevenueEntry.entry_date >= inicio, RevenueEntry.entry_date <= fim)
        .scalar()
    )


def _despesa_paga(db: Session, inicio: date, fim: date) -> float:
    return float(
        db.query(func.coalesce(func.sum(Payment.amount), 0.0))
        .filter(Payment.payment_date >= inicio, Payment.payment_date <= fim)
        .scalar()
    )


def _rcl_12meses(db: Session, ref: date) -> float:
    inicio = date(ref.year - 1, ref.month, 1)
    return _receita_arrecadada(db, inicio, ref)


def _despesa_pessoal(db: Session, inicio: date, fim: date) -> float:
    mes_inicio = inicio.strftime("%Y-%m")
    mes_fim = fim.strftime("%Y-%m")
    return float(
        db.query(func.coalesce(func.sum(Payslip.gross_amount), 0.0))
        .filter(Payslip.month >= mes_inicio, Payslip.month <= mes_fim)
        .scalar()
    )


def _loa_receita(db: Session, fy: FiscalYear) -> float:
    total = (
        db.query(func.coalesce(func.sum(LOAItem.authorized_amount), 0.0))
        .join(LOA, LOAItem.loa_id == LOA.id)
        .filter(LOA.fiscal_year_id == fy.id, LOAItem.category == "receita")
        .scalar()
    )
    return float(total)


def _loa_despesa(db: Session, fy: FiscalYear) -> float:
    total = (
        db.query(func.coalesce(func.sum(LOAItem.authorized_amount), 0.0))
        .join(LOA, LOAItem.loa_id == LOA.id)
        .filter(LOA.fiscal_year_id == fy.id, LOAItem.category != "receita")
        .scalar()
    )
    return float(total)


def _despesa_empenhada(db: Session, fy: FiscalYear) -> float:
    return float(
        db.query(func.coalesce(func.sum(Commitment.amount), 0.0))
        .filter(Commitment.fiscal_year_id == fy.id)
        .scalar()
    )


def _despesa_liquidada(db: Session, fy: FiscalYear) -> float:
    # liquidações com commitment nesse exercício
    total = (
        db.query(func.coalesce(func.sum(Liquidation.amount), 0.0))
        .join(Commitment, Liquidation.commitment_id == Commitment.id)
        .filter(Commitment.fiscal_year_id == fy.id)
        .scalar()
    )
    return float(total)


def _despesa_paga_exercicio(db: Session, fy: FiscalYear) -> float:
    inicio = date(fy.year, 1, 1)
    fim = date(fy.year, 12, 31)
    return _despesa_paga(db, inicio, fim)


def _dividida_consolidada(db: Session, fy: FiscalYear) -> float:
    total = (
        db.query(func.coalesce(func.sum(Commitment.amount), 0.0))
        .filter(Commitment.fiscal_year_id == fy.id,
                Commitment.status.in_(["empenhado", "liquidado"]))
        .scalar()
    )
    return float(total)


def _loa_itens_por_funcao(db: Session, fy: FiscalYear) -> list[dict]:
    """Agrupa LOAItems de despesa por função para RREO."""
    rows = (
        db.query(
            LOAItem.function_code,
            func.sum(LOAItem.authorized_amount),
            func.sum(LOAItem.executed_amount),
        )
        .join(LOA, LOAItem.loa_id == LOA.id)
        .filter(LOA.fiscal_year_id == fy.id, LOAItem.category != "receita")
        .group_by(LOAItem.function_code)
        .all()
    )
    result = []
    for function_code, autorizado, executado in rows:
        result.append({
            "function_code": function_code,
            "dotacao_autorizada": _r2(float(autorizado or 0)),
            "dotacao_executada": _r2(float(executado or 0)),
        })
    return result


def _inconsistencias(db: Session, exercicio: int) -> list[InconsistenciaItem]:
    """Validações pré-envio — detecta dados faltantes ou inconsistentes."""
    erros: list[InconsistenciaItem] = []

    fy = _fy(db, exercicio)
    if not fy:
        erros.append(InconsistenciaItem(
            severidade="ERRO", codigo="FY001",
            mensagem=f"Exercício fiscal {exercicio} não encontrado",
            valor_encontrado="ausente", valor_esperado="FiscalYear cadastrado",
        ))
        return erros  # demais validações dependem do exercício

    # Configuração da entidade
    cfg = db.query(ConfiguracaoEntidade).filter_by(ativo=True).first()
    if not cfg:
        erros.append(InconsistenciaItem(
            severidade="ERRO", codigo="ENT001",
            mensagem="Configuração da entidade não cadastrada (CNPJ, código IBGE, UF)",
            valor_encontrado="ausente", valor_esperado="ConfiguracaoEntidade ativa",
        ))
    else:
        if not cfg.cnpj or len(cfg.cnpj.replace(".", "").replace("/", "").replace("-", "")) != 14:
            erros.append(InconsistenciaItem(
                severidade="ERRO", codigo="ENT002",
                mensagem="CNPJ da entidade inválido ou ausente",
                valor_encontrado=cfg.cnpj or "vazio",
                valor_esperado="XX.XXX.XXX/XXXX-XX",
            ))
        if not cfg.codigo_ibge or len(cfg.codigo_ibge.replace("-", "").replace(".", "")) != 7:
            erros.append(InconsistenciaItem(
                severidade="ERRO", codigo="ENT003",
                mensagem="Código IBGE inválido ou ausente (deve ter 7 dígitos)",
                valor_encontrado=cfg.codigo_ibge or "vazio",
                valor_esperado="7 dígitos numéricos",
            ))
        if cfg.responsavel_nome == "":
            erros.append(InconsistenciaItem(
                severidade="AVISO", codigo="ENT004",
                mensagem="Nome do responsável não informado",
            ))

    # LOA do exercício
    loa = db.query(LOA).filter_by(fiscal_year_id=fy.id).first()
    if not loa:
        erros.append(InconsistenciaItem(
            severidade="ERRO", codigo="LOA001",
            mensagem=f"LOA do exercício {exercicio} não encontrada",
            valor_encontrado="ausente", valor_esperado="LOA com status aprovada",
        ))
    else:
        if loa.status == "rascunho":
            erros.append(InconsistenciaItem(
                severidade="AVISO", codigo="LOA002",
                mensagem="LOA do exercício está em rascunho",
                valor_encontrado=loa.status, valor_esperado="aprovada",
            ))
        receita_loa = _loa_receita(db, fy)
        despesa_loa = _loa_despesa(db, fy)
        if abs(receita_loa - despesa_loa) > 1.0:
            erros.append(InconsistenciaItem(
                severidade="AVISO", codigo="LOA003",
                mensagem="Receita e despesa da LOA não estão equilibradas (diferença > R$ 1,00)",
                valor_encontrado=f"receita={receita_loa:.2f} despesa={despesa_loa:.2f}",
                valor_esperado="receita == despesa",
            ))

    # PPA vigente
    ppa = db.query(PPA).filter(
        PPA.period_start <= exercicio, PPA.period_end >= exercicio
    ).first()
    if not ppa:
        erros.append(InconsistenciaItem(
            severidade="AVISO", codigo="PPA001",
            mensagem=f"Nenhum PPA vigente cobre o exercício {exercicio}",
            valor_encontrado="ausente", valor_esperado="PPA com period_start <= exercicio <= period_end",
        ))

    # LDO do exercício
    ldo = db.query(LDO).filter_by(fiscal_year_id=fy.id).first()
    if not ldo:
        erros.append(InconsistenciaItem(
            severidade="AVISO", codigo="LDO001",
            mensagem=f"LDO do exercício {exercicio} não encontrada",
        ))

    # Equilíbrio receita arrecadada vs despesa paga
    inicio_ano = date(exercicio, 1, 1)
    fim_ano = date(exercicio, 12, 31)
    receita_real = _r2(_receita_arrecadada(db, inicio_ano, fim_ano))
    despesa_real = _r2(_despesa_paga(db, inicio_ano, fim_ano))
    if despesa_real > receita_real and receita_real > 0:
        erros.append(InconsistenciaItem(
            severidade="AVISO", codigo="EXE001",
            mensagem="Despesa paga no exercício supera receita arrecadada (deficit de caixa)",
            valor_encontrado=f"despesa_paga={despesa_real:.2f} > receita={receita_real:.2f}",
            valor_esperado="receita >= despesa",
        ))

    # Limite de pessoal LRF
    rcl = _r2(_rcl_12meses(db, fim_ano))
    desp_pessoal = _r2(_despesa_pessoal(db, inicio_ano, fim_ano))
    if rcl > 0:
        pct = desp_pessoal / rcl
        if pct > LIMITE_PESSOAL_MUNICIPIO:
            erros.append(InconsistenciaItem(
                severidade="ERRO", codigo="LRF001",
                mensagem=f"Despesa de pessoal excede 60% da RCL (art. 19 LRF) — {pct*100:.1f}%",
                valor_encontrado=f"{pct*100:.2f}%",
                valor_esperado=f"≤ {LIMITE_PESSOAL_MUNICIPIO*100:.0f}%",
            ))
        elif pct > LIMITE_ALERTA:
            erros.append(InconsistenciaItem(
                severidade="AVISO", codigo="LRF002",
                mensagem=f"Despesa de pessoal acima de 90% do limite (alerta prudencial) — {pct*100:.1f}%",
                valor_encontrado=f"{pct*100:.2f}%",
                valor_esperado=f"≤ {LIMITE_ALERTA*100:.0f}%",
            ))

    return erros


def _build_finbra(db: Session, exercicio: int) -> dict:
    """Monta payload FINBRA — Balanço Orçamentário."""
    fy = _fy(db, exercicio)
    inicio = date(exercicio, 1, 1)
    fim = date(exercicio, 12, 31)

    receita_prevista = _r2(_loa_receita(db, fy) if fy else 0.0)
    receita_arrecadada = _r2(_receita_arrecadada(db, inicio, fim))
    despesa_autorizada = _r2(_loa_despesa(db, fy) if fy else 0.0)
    despesa_empenhada = _r2(_despesa_empenhada(db, fy) if fy else 0.0)
    despesa_liquidada = _r2(_despesa_liquidada(db, fy) if fy else 0.0)
    despesa_paga = _r2(_despesa_paga(db, inicio, fim))
    desp_pessoal = _r2(_despesa_pessoal(db, inicio, fim))
    rcl = _r2(_rcl_12meses(db, fim))
    divida = _r2(_dividida_consolidada(db, fy) if fy else 0.0)

    return {
        "cabecalho": {
            "exercicio": exercicio,
            "tipo_relatorio": "FINBRA_BALANCO_ORCAMENTARIO",
            "periodo": "ANUAL",
            "data_geracao": date.today().isoformat(),
        },
        "balanco_receita": {
            "receita_prevista_loa": receita_prevista,
            "receita_arrecadada": receita_arrecadada,
            "diferenca_arrecadamento": _r2(receita_arrecadada - receita_prevista),
            "pct_realizacao": _r2((receita_arrecadada / receita_prevista * 100) if receita_prevista else 0.0),
        },
        "balanco_despesa": {
            "dotacao_autorizada": despesa_autorizada,
            "despesa_empenhada": despesa_empenhada,
            "despesa_liquidada": despesa_liquidada,
            "despesa_paga": despesa_paga,
            "saldo_a_pagar": _r2(despesa_empenhada - despesa_paga),
        },
        "indicadores_lrf": {
            "rcl_12meses": rcl,
            "despesa_pessoal_bruta": desp_pessoal,
            "pct_pessoal_rcl": _r2((desp_pessoal / rcl * 100) if rcl else 0.0),
            "limite_pessoal_60pct": _r2(rcl * LIMITE_PESSOAL_MUNICIPIO),
            "situacao_pessoal": (
                "EXCEDIDO" if rcl > 0 and desp_pessoal > rcl * LIMITE_PESSOAL_MUNICIPIO
                else "ALERTA" if rcl > 0 and desp_pessoal > rcl * LIMITE_ALERTA
                else "REGULAR"
            ),
            "divida_consolidada": divida,
        },
        "resultado_exercicio": {
            "receita": receita_arrecadada,
            "despesa": despesa_paga,
            "saldo": _r2(receita_arrecadada - despesa_paga),
            "tipo": "superavit" if receita_arrecadada >= despesa_paga else "deficit",
        },
    }


def _build_rreo_estruturado(db: Session, exercicio: int, bimestre: int) -> dict:
    """RREO bimestral estruturado por função/subfunção (baseado nos LOAItems)."""
    fy = _fy(db, exercicio)
    mes_inicio = (bimestre - 1) * 2 + 1
    mes_fim = mes_inicio + 1
    inicio = date(exercicio, mes_inicio, 1)
    fim = (date(exercicio, mes_fim + 1, 1) - timedelta(days=1)) if mes_fim < 12 else date(exercicio, 12, 31)
    inicio_ano = date(exercicio, 1, 1)

    funcoes = _loa_itens_por_funcao(db, fy) if fy else []

    return {
        "cabecalho": {
            "exercicio": exercicio,
            "bimestre": bimestre,
            "referencia": f"{bimestre}º Bimestre/{exercicio}",
            "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            "tipo_relatorio": "RREO_BALANCO_ORCAMENTARIO",
            "base_legal": "LRF art. 52-53",
        },
        "receitas": {
            "prevista_loa": _r2(_loa_receita(db, fy) if fy else 0.0),
            "arrecadada_bimestre": _r2(_receita_arrecadada(db, inicio, fim)),
            "arrecadada_acumulada": _r2(_receita_arrecadada(db, inicio_ano, fim)),
        },
        "despesas_por_funcao": funcoes,
        "despesas_totais": {
            "empenhada_exercicio": _r2(_despesa_empenhada(db, fy) if fy else 0.0),
            "liquidada_bimestre": _r2(
                float(db.query(func.coalesce(func.sum(Liquidation.amount), 0.0))
                      .join(Commitment, Liquidation.commitment_id == Commitment.id)
                      .filter(Commitment.fiscal_year_id == fy.id,
                              Liquidation.created_at >= inicio,
                              Liquidation.created_at <= fim)
                      .scalar()) if fy else 0.0
            ),
            "paga_bimestre": _r2(_despesa_paga(db, inicio, fim)),
            "paga_acumulada": _r2(_despesa_paga(db, inicio_ano, fim)),
        },
    }


def _build_rgf_estruturado(db: Session, exercicio: int, quadrimestre: int) -> dict:
    """RGF quadrimestral estruturado."""
    fy = _fy(db, exercicio)
    mes_inicio = (quadrimestre - 1) * 4 + 1
    mes_fim = mes_inicio + 3
    inicio = date(exercicio, mes_inicio, 1)
    fim = (date(exercicio, mes_fim + 1, 1) - timedelta(days=1)) if mes_fim < 12 else date(exercicio, 12, 31)
    inicio_ano = date(exercicio, 1, 1)

    rcl = _r2(_rcl_12meses(db, fim))
    desp_pessoal_quad = _r2(_despesa_pessoal(db, inicio, fim))
    desp_pessoal_ano = _r2(_despesa_pessoal(db, inicio_ano, fim))
    limite = _r2(rcl * LIMITE_PESSOAL_MUNICIPIO)
    excesso = _r2(max(0.0, desp_pessoal_ano - limite))
    pct = _r2((desp_pessoal_ano / rcl * 100) if rcl else 0.0)

    return {
        "cabecalho": {
            "exercicio": exercicio,
            "quadrimestre": quadrimestre,
            "referencia": f"{quadrimestre}º Quadrimestre/{exercicio}",
            "periodo": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            "tipo_relatorio": "RGF_DESPESA_PESSOAL_DIVIDA",
            "base_legal": "LRF art. 55",
        },
        "despesa_pessoal": {
            "quadrimestre": desp_pessoal_quad,
            "acumulada_ano": desp_pessoal_ano,
            "rcl_12meses": rcl,
            "limite_legal_60pct": limite,
            "limite_alerta_54pct": _r2(rcl * LIMITE_ALERTA),
            "pct_rcl": pct,
            "excesso": excesso,
            "situacao": (
                "EXCEDIDO" if rcl > 0 and desp_pessoal_ano > limite
                else "ALERTA" if rcl > 0 and desp_pessoal_ano > rcl * LIMITE_ALERTA
                else "REGULAR"
            ),
        },
        "divida_consolidada": {
            "saldo": _r2(_dividida_consolidada(db, fy) if fy else 0.0),
        },
        "disponibilidade_financeira": {
            "receita_acumulada": _r2(_receita_arrecadada(db, inicio_ano, fim)),
            "despesa_paga_acumulada": _r2(_despesa_paga(db, inicio_ano, fim)),
            "saldo": _r2(
                _receita_arrecadada(db, inicio_ano, fim) - _despesa_paga(db, inicio_ano, fim)
            ),
        },
    }


def _build_siop_programas(db: Session, exercicio: int) -> dict:
    """Exportação dos programas PPA e LOA para SIOP."""
    ppa = db.query(PPA).filter(
        PPA.period_start <= exercicio, PPA.period_end >= exercicio
    ).order_by(PPA.id.desc()).first()

    programas_ppa = []
    if ppa:
        for prog in db.query(PPAProgram).filter_by(ppa_id=ppa.id).all():
            programas_ppa.append({
                "codigo": prog.code,
                "nome": prog.name,
                "objetivo": prog.objective,
                "valor_estimado": _r2(prog.estimated_amount),
                "ppa_periodo": f"{ppa.period_start}-{ppa.period_end}",
            })

    fy = _fy(db, exercicio)
    loa = db.query(LOA).filter_by(fiscal_year_id=fy.id).first() if fy else None
    acoes_loa = []
    if loa:
        for item in db.query(LOAItem).filter_by(loa_id=loa.id).all():
            acoes_loa.append({
                "funcao": item.function_code,
                "subfuncao": item.subfunction_code,
                "programa": item.program_code,
                "acao": item.action_code,
                "descricao": item.description,
                "categoria": item.category,
                "dotacao_autorizada": _r2(item.authorized_amount),
                "dotacao_executada": _r2(item.executed_amount),
            })

    ldo = db.query(LDO).filter_by(fiscal_year_id=fy.id).first() if fy else None
    metas_ldo = []
    if ldo:
        for goal in db.query(LDOGoal).filter_by(ldo_id=ldo.id).all():
            metas_ldo.append({
                "codigo": goal.code,
                "descricao": goal.description,
                "categoria": goal.category,
            })

    return {
        "cabecalho": {
            "exercicio": exercicio,
            "tipo_relatorio": "SIOP_PROGRAMAS_ACOES",
            "data_geracao": date.today().isoformat(),
        },
        "programas_ppa": programas_ppa,
        "acoes_loa": acoes_loa,
        "metas_ldo": metas_ldo,
        "totais": {
            "programas_ppa": len(programas_ppa),
            "acoes_loa": len(acoes_loa),
            "metas_ldo": len(metas_ldo),
        },
    }


# ── Configuração da entidade ──────────────────────────────────────────────────

@router.get("/config", response_model=ConfiguracaoEntidadeOut | None)
def get_config(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Retorna a configuração ativa da entidade."""
    return db.query(ConfiguracaoEntidade).filter_by(ativo=True).first()


@router.post("/config", response_model=ConfiguracaoEntidadeOut)
def upsert_config(
    payload: ConfiguracaoEntidadeCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin)),
):
    """Cria ou substitui a configuração da entidade (apenas admin)."""
    # Desativa todas anteriores
    db.query(ConfiguracaoEntidade).update({"ativo": False})
    cfg = ConfiguracaoEntidade(**payload.model_dump(), ativo=True)
    db.add(cfg)
    write_audit(db, user_id=current.id, action="update", entity="configuracoes_entidade",
                entity_id="1", after_data=payload.model_dump())
    db.commit()
    db.refresh(cfg)
    return cfg


# ── Validação pré-envio ───────────────────────────────────────────────────────

@router.get("/validar")
def validar(
    exercicio: int = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista inconsistências encontradas nos dados pré-exportação SICONFI."""
    if not exercicio:
        exercicio = date.today().year
    erros = _inconsistencias(db, exercicio)
    return {
        "exercicio": exercicio,
        "total_erros": sum(1 for e in erros if e.severidade == "ERRO"),
        "total_avisos": sum(1 for e in erros if e.severidade == "AVISO"),
        "pode_exportar": all(e.severidade != "ERRO" for e in erros),
        "inconsistencias": [e.model_dump() for e in erros],
    }


# ── FINBRA — Balanço Orçamentário ─────────────────────────────────────────────

@router.get("/finbra")
def finbra(
    exercicio: int = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Balanço Orçamentário FINBRA — Receita, Despesa e LRF."""
    if not exercicio:
        exercicio = date.today().year
    if not _fy(db, exercicio):
        raise HTTPException(status_code=404, detail=f"Exercício {exercicio} não encontrado")
    return _build_finbra(db, exercicio)


# ── RREO estruturado ──────────────────────────────────────────────────────────

@router.get("/rreo")
def rreo_estruturado(
    exercicio: int = Query(default=None),
    bimestre: int = Query(default=None, ge=1, le=6),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """RREO bimestral estruturado com despesas por função (LRF art. 52-53)."""
    hoje = date.today()
    if not exercicio:
        exercicio = hoje.year
    if not bimestre:
        bimestre = min(6, (hoje.month - 1) // 2 + 1)
    if not _fy(db, exercicio):
        raise HTTPException(status_code=404, detail=f"Exercício {exercicio} não encontrado")
    return _build_rreo_estruturado(db, exercicio, bimestre)


# ── RGF estruturado ───────────────────────────────────────────────────────────

@router.get("/rgf")
def rgf_estruturado(
    exercicio: int = Query(default=None),
    quadrimestre: int = Query(default=None, ge=1, le=3),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """RGF quadrimestral estruturado — Despesa Pessoal, Dívida, Disponibilidade (LRF art. 55)."""
    hoje = date.today()
    if not exercicio:
        exercicio = hoje.year
    if not quadrimestre:
        quadrimestre = min(3, (hoje.month - 1) // 4 + 1)
    if not _fy(db, exercicio):
        raise HTTPException(status_code=404, detail=f"Exercício {exercicio} não encontrado")
    return _build_rgf_estruturado(db, exercicio, quadrimestre)


# ── SIOP — Programas e Ações ──────────────────────────────────────────────────

@router.get("/siop-programas")
def siop_programas(
    exercicio: int = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Exportação dos Programas PPA, Ações LOA e Metas LDO para SIOP."""
    if not exercicio:
        exercicio = date.today().year
    return _build_siop_programas(db, exercicio)


# ── Dashboard / Resumo ────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(
    exercicio: int = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Resumo executivo — status de preparação SICONFI/SIOP."""
    if not exercicio:
        exercicio = date.today().year

    erros = _inconsistencias(db, exercicio)
    n_erros = sum(1 for e in erros if e.severidade == "ERRO")
    n_avisos = sum(1 for e in erros if e.severidade == "AVISO")

    fy = _fy(db, exercicio)
    cfg = db.query(ConfiguracaoEntidade).filter_by(ativo=True).first()
    loa = db.query(LOA).filter_by(fiscal_year_id=fy.id).first() if fy else None
    ppa = db.query(PPA).filter(
        PPA.period_start <= exercicio, PPA.period_end >= exercicio
    ).first()
    ldo = db.query(LDO).filter_by(fiscal_year_id=fy.id).first() if fy else None
    n_exportacoes = db.query(ExportacaoSiconfi).filter_by(exercicio=exercicio).count()

    inicio = date(exercicio, 1, 1)
    fim = date(exercicio, 12, 31)
    receita = _r2(_receita_arrecadada(db, inicio, fim))
    despesa = _r2(_despesa_paga(db, inicio, fim))
    rcl = _r2(_rcl_12meses(db, fim))
    desp_pessoal = _r2(_despesa_pessoal(db, inicio, fim))

    return {
        "exercicio": exercicio,
        "status_preparacao": "PRONTO" if n_erros == 0 else "PENDENTE",
        "validacao": {
            "erros": n_erros,
            "avisos": n_avisos,
            "pode_exportar": n_erros == 0,
        },
        "modulos": {
            "entidade_configurada": cfg is not None,
            "loa_vigente": loa is not None,
            "ppa_vigente": ppa is not None,
            "ldo_vigente": ldo is not None,
        },
        "resumo_financeiro": {
            "receita_arrecadada": receita,
            "despesa_paga": despesa,
            "saldo": _r2(receita - despesa),
            "rcl_12meses": rcl,
            "despesa_pessoal_bruta": desp_pessoal,
            "pct_pessoal_rcl": _r2((desp_pessoal / rcl * 100) if rcl else 0.0),
        },
        "exportacoes_geradas": n_exportacoes,
    }


# ── Exportar (log) ────────────────────────────────────────────────────────────

@router.post("/exportar", response_model=ExportacaoOut)
def exportar(
    payload: ExportacaoRequest,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Gera e registra um snapshot da exportação SICONFI/SIOP.

    Tipos aceitos: finbra | rreo | rgf | siop_programas
    Retorna o log gerado. O payload JSON fica salvo para rastreabilidade.
    Não faz envio ao governo federal.
    """
    tipos_validos = {"finbra", "rreo", "rgf", "siop_programas"}
    if payload.tipo not in tipos_validos:
        raise HTTPException(status_code=422,
                            detail=f"Tipo inválido. Use: {', '.join(sorted(tipos_validos))}")

    if not _fy(db, payload.exercicio):
        raise HTTPException(status_code=404,
                            detail=f"Exercício {payload.exercicio} não encontrado")

    erros = _inconsistencias(db, payload.exercicio)
    n_inconsistencias = len(erros)
    status_exp = "validado" if all(e.severidade != "ERRO" for e in erros) else "rascunho"

    # Constrói payload de acordo com tipo
    periodo_str = payload.periodo or "ANUAL"
    if payload.tipo == "finbra":
        dados = _build_finbra(db, payload.exercicio)
    elif payload.tipo == "rreo":
        bim = int(payload.periodo.split("_")[-1]) if payload.periodo and "_" in payload.periodo else (date.today().month - 1) // 2 + 1
        dados = _build_rreo_estruturado(db, payload.exercicio, min(bim, 6))
    elif payload.tipo == "rgf":
        quad = int(payload.periodo.split("_")[-1]) if payload.periodo and "_" in payload.periodo else (date.today().month - 1) // 4 + 1
        dados = _build_rgf_estruturado(db, payload.exercicio, min(quad, 3))
    else:  # siop_programas
        dados = _build_siop_programas(db, payload.exercicio)

    exp = ExportacaoSiconfi(
        tipo=payload.tipo,
        exercicio=payload.exercicio,
        periodo=periodo_str,
        status=status_exp,
        inconsistencias=n_inconsistencias,
        payload_json=dados,
        gerado_por_id=current.id,
    )
    db.add(exp)
    write_audit(db, user_id=current.id, action="create", entity="exportacoes_siconfi",
                entity_id=str(payload.tipo),
                after_data={"tipo": payload.tipo, "exercicio": payload.exercicio,
                            "status": status_exp, "inconsistencias": n_inconsistencias})
    db.commit()
    db.refresh(exp)
    return exp


# ── Listagem das exportações ──────────────────────────────────────────────────

@router.get("/exportacoes", response_model=None)
def list_exportacoes(
    exercicio: int | None = None,
    tipo: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista exportações geradas com filtros opcionais."""
    q = db.query(ExportacaoSiconfi)
    if exercicio:
        q = q.filter(ExportacaoSiconfi.exercicio == exercicio)
    if tipo:
        q = q.filter(ExportacaoSiconfi.tipo == tipo)
    total = q.count()
    items = q.order_by(ExportacaoSiconfi.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}
