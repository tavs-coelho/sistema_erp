"""Router LRF — Demonstrativos RREO e RGF.

RREO — Relatório Resumido da Execução Orçamentária (LRF art. 52-53):
  - Publicado a cada bimestre
  - Confronta receita prevista vs arrecadada e despesa autorizada vs executada
  - Baseado em: Commitment (empenho), Liquidation, Payment, RevenueEntry, FiscalYear

RGF — Relatório de Gestão Fiscal (LRF art. 55):
  - Publicado a cada quadrimestre
  - Apura: despesa com pessoal (folha), dívida consolidada e disponibilidade financeira
  - Baseado em: Payslip (folha), Commitment, Payment, RevenueEntry

PREMISSAS DE CÁLCULO:
  * Receita prevista = soma das dotações LOA do exercício (LOAItem.authorized_amount onde category='receita')
    ou, na ausência de LOA, 0.
  * Receita arrecadada = SUM(revenue_entries.amount) no período.
  * Despesa autorizada = SUM(commitments.amount) no exercício.
  * Despesa empenhada = SUM(commitments.amount) status in {empenhado, liquidado, pago}.
  * Despesa liquidada = SUM(liquidations.amount).
  * Despesa paga = SUM(payments.amount) no período.
  * Despesa pessoal = SUM(payslips.gross_amount) no período (proxy bruto de folha).
  * RCL (Receita Corrente Líquida) = SUM(revenue_entries.amount) nos últimos 12 meses.
  * Limite pessoal LRF (art. 19): 60 % RCL para municípios.
  * Dívida consolidada = empenhos NÃO pagos (status empenhado ou liquidado).
"""

import csv
from datetime import date, timedelta
from io import StringIO

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user
from ..models import (
    Commitment,
    FiscalYear,
    LOAItem,
    Liquidation,
    Payment,
    Payslip,
    RevenueEntry,
    User,
)

router = APIRouter(prefix="/lrf", tags=["lrf"])

# ── Constantes LRF ────────────────────────────────────────────────────────────

LIMITE_PESSOAL_MUNICIPIO = 0.60   # 60 % RCL — art. 19, III LRF
LIMITE_PESSOAL_ALERTA = 0.54      # 90 % do limite — alerta prudencial

# ── Helpers ───────────────────────────────────────────────────────────────────

def _bimestre_range(ano: int, bimestre: int) -> tuple[date, date]:
    """Retorna (data_inicio, data_fim) para o bimestre 1-6 do ano."""
    mes_inicio = (bimestre - 1) * 2 + 1
    mes_fim = mes_inicio + 1
    inicio = date(ano, mes_inicio, 1)
    if mes_fim == 12:
        fim = date(ano, 12, 31)
    else:
        fim = date(ano, mes_fim + 1, 1) - timedelta(days=1)
    return inicio, fim


def _quadrimestre_range(ano: int, quadrimestre: int) -> tuple[date, date]:
    """Retorna (data_inicio, data_fim) para o quadrimestre 1-3 do ano."""
    mes_inicio = (quadrimestre - 1) * 4 + 1
    mes_fim = mes_inicio + 3
    inicio = date(ano, mes_inicio, 1)
    if mes_fim >= 12:
        fim = date(ano, 12, 31)
    else:
        fim = date(ano, mes_fim + 1, 1) - timedelta(days=1)
    return inicio, fim


def _receita_prevista(db: Session, ano: int) -> float:
    """Receita prevista na LOA para o exercício (itens categoria 'receita')."""
    fy = db.query(FiscalYear).filter(FiscalYear.year == ano).first()
    if not fy:
        return 0.0
    # LOAItem não tem FK direta de exercício — join via LOA → fiscal_year_id
    from ..models import LOA
    total = (
        db.query(func.coalesce(func.sum(LOAItem.authorized_amount), 0.0))
        .join(LOA, LOAItem.loa_id == LOA.id)
        .filter(LOA.fiscal_year_id == fy.id, LOAItem.category == "receita")
        .scalar()
    )
    return float(total)


def _receita_arrecadada(db: Session, inicio: date, fim: date) -> float:
    return float(
        db.query(func.coalesce(func.sum(RevenueEntry.amount), 0.0))
        .filter(RevenueEntry.entry_date >= inicio, RevenueEntry.entry_date <= fim)
        .scalar()
    )


def _despesa_autorizada(db: Session, ano: int) -> float:
    """Dotação autorizada: soma das dotações LOA (itens categoria 'despesa')."""
    from ..models import LOA
    fy = db.query(FiscalYear).filter(FiscalYear.year == ano).first()
    if not fy:
        return 0.0
    total = (
        db.query(func.coalesce(func.sum(LOAItem.authorized_amount), 0.0))
        .join(LOA, LOAItem.loa_id == LOA.id)
        .filter(LOA.fiscal_year_id == fy.id, LOAItem.category != "receita")
        .scalar()
    )
    return float(total)


def _despesa_empenhada_ano(db: Session, ano: int) -> float:
    """Total empenhado no exercício fiscal (todos os empenhos do ano)."""
    fy = db.query(FiscalYear).filter(FiscalYear.year == ano).first()
    if not fy:
        return 0.0
    total = (
        db.query(func.coalesce(func.sum(Commitment.amount), 0.0))
        .filter(Commitment.fiscal_year_id == fy.id)
        .scalar()
    )
    return float(total)


def _despesa_liquidada_periodo(db: Session, inicio: date, fim: date) -> float:
    """Despesa liquidada (Liquidation criada) no período."""
    total = (
        db.query(func.coalesce(func.sum(Liquidation.amount), 0.0))
        .filter(Liquidation.created_at >= inicio, Liquidation.created_at <= fim)
        .scalar()
    )
    return float(total)


def _despesa_paga_periodo(db: Session, inicio: date, fim: date) -> float:
    total = (
        db.query(func.coalesce(func.sum(Payment.amount), 0.0))
        .filter(Payment.payment_date >= inicio, Payment.payment_date <= fim)
        .scalar()
    )
    return float(total)


def _divida_consolidada(db: Session, ano: int) -> float:
    """Empenhos não pagos do exercício (empenhado ou liquidado)."""
    fy = db.query(FiscalYear).filter(FiscalYear.year == ano).first()
    if not fy:
        return 0.0
    total = (
        db.query(func.coalesce(func.sum(Commitment.amount), 0.0))
        .filter(
            Commitment.fiscal_year_id == fy.id,
            Commitment.status.in_(["empenhado", "liquidado"]),
        )
        .scalar()
    )
    return float(total)


def _rcl_12meses(db: Session, ref: date) -> float:
    """Receita corrente líquida: arrecadação dos 12 meses encerrados em 'ref'."""
    inicio = date(ref.year - 1, ref.month, 1)
    return _receita_arrecadada(db, inicio, ref)


def _despesa_pessoal(db: Session, inicio: date, fim: date) -> float:
    """Despesa de pessoal: soma bruta das folhas (Payslip) no período.

    O campo 'month' é do formato 'YYYY-MM'. Filtramos pelo intervalo de meses.
    """
    mes_inicio = inicio.strftime("%Y-%m")
    mes_fim = fim.strftime("%Y-%m")
    total = (
        db.query(func.coalesce(func.sum(Payslip.gross_amount), 0.0))
        .filter(Payslip.month >= mes_inicio, Payslip.month <= mes_fim)
        .scalar()
    )
    return float(total)


def _round2(v: float) -> float:
    return round(v, 2)


# ── RREO ──────────────────────────────────────────────────────────────────────

@router.get("/rreo")
def rreo(
    ano: int = Query(default=None, description="Exercício (padrão: ano corrente)"),
    bimestre: int = Query(default=None, ge=1, le=6, description="Bimestre 1-6 (padrão: bimestre corrente)"),
    export: str | None = Query(default=None, description="csv para download"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório Resumido da Execução Orçamentária — LRF art. 52-53.

    Confronta receita e despesa por bimestre.
    Inclui evolução acumulada do ano até o bimestre solicitado.
    """
    hoje = date.today()
    if not ano:
        ano = hoje.year
    if not bimestre:
        # bimestre corrente: mês / 2, arredondando para cima
        bimestre = min(6, (hoje.month - 1) // 2 + 1)

    inicio, fim = _bimestre_range(ano, bimestre)

    # Acumulado do ano até o fim do bimestre
    inicio_ano = date(ano, 1, 1)

    receita_prevista = _round2(_receita_prevista(db, ano))
    receita_bimestre = _round2(_receita_arrecadada(db, inicio, fim))
    receita_acumulada = _round2(_receita_arrecadada(db, inicio_ano, fim))

    despesa_autorizada = _round2(_despesa_autorizada(db, ano))
    despesa_empenhada = _round2(_despesa_empenhada_ano(db, ano))
    despesa_liquidada_bimestre = _round2(_despesa_liquidada_periodo(db, inicio, fim))
    despesa_liquidada_acumulada = _round2(_despesa_liquidada_periodo(db, inicio_ano, fim))
    despesa_paga_bimestre = _round2(_despesa_paga_periodo(db, inicio, fim))
    despesa_paga_acumulada = _round2(_despesa_paga_periodo(db, inicio_ano, fim))

    saldo_execucao = _round2(receita_acumulada - despesa_paga_acumulada)
    pct_receita_realizada = _round2(
        (receita_acumulada / receita_prevista * 100) if receita_prevista else 0.0
    )
    pct_despesa_executada = _round2(
        (despesa_paga_acumulada / despesa_empenhada * 100) if despesa_empenhada else 0.0
    )

    rows = [
        {"descricao": "Receita Prevista (LOA)", "bimestre": None, "acumulado": receita_prevista},
        {"descricao": "Receita Arrecadada", "bimestre": receita_bimestre, "acumulado": receita_acumulada},
        {"descricao": "Dotação Autorizada (LOA)", "bimestre": None, "acumulado": despesa_autorizada},
        {"descricao": "Despesa Empenhada (ano)", "bimestre": None, "acumulado": despesa_empenhada},
        {"descricao": "Despesa Liquidada", "bimestre": despesa_liquidada_bimestre, "acumulado": despesa_liquidada_acumulada},
        {"descricao": "Despesa Paga", "bimestre": despesa_paga_bimestre, "acumulado": despesa_paga_acumulada},
    ]

    indicadores = {
        "saldo_execucao_acumulado": saldo_execucao,
        "pct_receita_realizada": pct_receita_realizada,
        "pct_despesa_executada": pct_despesa_executada,
        "resultado": "superavit" if saldo_execucao >= 0 else "deficit",
    }

    if export == "csv":
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["Descrição", f"Bimestre {bimestre}/{ano}", f"Acumulado até {fim}"])
        for r in rows:
            w.writerow([r["descricao"], r["bimestre"] if r["bimestre"] is not None else "—", r["acumulado"]])
        w.writerow([])
        w.writerow(["Indicador", "Valor"])
        for k, v in indicadores.items():
            w.writerow([k, v])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=rreo_{ano}_bim{bimestre}.csv"},
        )

    return {
        "cabecalho": {
            "exercicio": ano,
            "bimestre": bimestre,
            "periodo_bimestre": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            "referencia": f"{bimestre}º Bimestre de {ano}",
            "base_legal": "LRF art. 52-53",
        },
        "linhas": rows,
        "indicadores": indicadores,
    }


# ── RGF ───────────────────────────────────────────────────────────────────────

@router.get("/rgf")
def rgf(
    ano: int = Query(default=None, description="Exercício (padrão: ano corrente)"),
    quadrimestre: int = Query(default=None, ge=1, le=3, description="Quadrimestre 1-3 (padrão: quadrimestre corrente)"),
    export: str | None = Query(default=None, description="csv para download"),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório de Gestão Fiscal — LRF art. 55.

    Apura despesa com pessoal, dívida consolidada e disponibilidade financeira.
    Compara despesa com pessoal com limite de 60 % da RCL (municípios).
    """
    hoje = date.today()
    if not ano:
        ano = hoje.year
    if not quadrimestre:
        quadrimestre = min(3, (hoje.month - 1) // 4 + 1)

    inicio, fim = _quadrimestre_range(ano, quadrimestre)
    inicio_ano = date(ano, 1, 1)

    rcl = _round2(_rcl_12meses(db, fim))
    despesa_pessoal_quad = _round2(_despesa_pessoal(db, inicio, fim))
    despesa_pessoal_ano = _round2(_despesa_pessoal(db, inicio_ano, fim))
    despesa_paga_quad = _round2(_despesa_paga_periodo(db, inicio, fim))
    despesa_paga_ano = _round2(_despesa_paga_periodo(db, inicio_ano, fim))
    receita_quad = _round2(_receita_arrecadada(db, inicio, fim))
    receita_ano = _round2(_receita_arrecadada(db, inicio_ano, fim))
    divida = _round2(_divida_consolidada(db, ano))

    limite_pessoal_valor = _round2(rcl * LIMITE_PESSOAL_MUNICIPIO)
    alerta_pessoal_valor = _round2(rcl * LIMITE_PESSOAL_ALERTA)
    pct_pessoal_rcl = _round2((despesa_pessoal_ano / rcl * 100) if rcl else 0.0)
    excesso_pessoal = _round2(max(0.0, despesa_pessoal_ano - limite_pessoal_valor))
    situacao_pessoal = (
        "EXCEDIDO" if despesa_pessoal_ano > limite_pessoal_valor
        else "ALERTA" if despesa_pessoal_ano > alerta_pessoal_valor
        else "REGULAR"
    )

    disponibilidade = _round2(receita_ano - despesa_paga_ano)

    rows = [
        {"descricao": "RCL — Receita Corrente Líquida (12 meses)", "quadrimestre": None, "acumulado": rcl},
        {"descricao": "Despesa com Pessoal (quadrimestre)", "quadrimestre": despesa_pessoal_quad, "acumulado": despesa_pessoal_ano},
        {"descricao": "Limite legal pessoal (60 % RCL)", "quadrimestre": None, "acumulado": limite_pessoal_valor},
        {"descricao": "Limite alerta pessoal (54 % RCL)", "quadrimestre": None, "acumulado": alerta_pessoal_valor},
        {"descricao": "Dívida Consolidada (empenhos pendentes)", "quadrimestre": None, "acumulado": divida},
        {"descricao": "Receita Arrecadada", "quadrimestre": receita_quad, "acumulado": receita_ano},
        {"descricao": "Despesa Paga", "quadrimestre": despesa_paga_quad, "acumulado": despesa_paga_ano},
        {"descricao": "Disponibilidade Financeira (receita − pago)", "quadrimestre": None, "acumulado": disponibilidade},
    ]

    indicadores = {
        "rcl_12meses": rcl,
        "despesa_pessoal_acumulada": despesa_pessoal_ano,
        "limite_pessoal_60pct_rcl": limite_pessoal_valor,
        "pct_despesa_pessoal_rcl": pct_pessoal_rcl,
        "excesso_despesa_pessoal": excesso_pessoal,
        "situacao_despesa_pessoal": situacao_pessoal,
        "divida_consolidada": divida,
        "disponibilidade_financeira": disponibilidade,
        "saldo_exercicio": _round2(receita_ano - despesa_paga_ano),
    }

    if export == "csv":
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow(["Descrição", f"Quadrimestre {quadrimestre}/{ano}", f"Acumulado até {fim}"])
        for r in rows:
            w.writerow([r["descricao"], r["quadrimestre"] if r["quadrimestre"] is not None else "—", r["acumulado"]])
        w.writerow([])
        w.writerow(["Indicador", "Valor"])
        for k, v in indicadores.items():
            w.writerow([k, v])
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename=rgf_{ano}_quad{quadrimestre}.csv"},
        )

    return {
        "cabecalho": {
            "exercicio": ano,
            "quadrimestre": quadrimestre,
            "periodo_quadrimestre": {"inicio": inicio.isoformat(), "fim": fim.isoformat()},
            "referencia": f"{quadrimestre}º Quadrimestre de {ano}",
            "base_legal": "LRF art. 55",
        },
        "linhas": rows,
        "indicadores": indicadores,
    }
