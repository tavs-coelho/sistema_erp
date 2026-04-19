"""Router de Conciliação Bancária.

Gerencia contas bancárias da entidade e seus lançamentos do extrato.
Oferece mecanismo automático de cruzamento (conciliação) com Payment e RevenueEntry.

LÓGICA DE CONCILIAÇÃO AUTOMÁTICA:
  Para cada LancamentoBancario pendente na janela de datas:
    - Débito → tenta cruzar com Payment pelo valor exato e data ±TOLERANCIA_DIAS.
    - Crédito → tenta cruzar com RevenueEntry pelo valor exato e data ±TOLERANCIA_DIAS.
    - Se valor bate mas data excede a tolerância → status = divergente (com observação).
    - Se nenhum match → permanece pendente.

EXPORTAÇÃO:
  GET /banco/conciliacao/relatorio?export=csv
"""

import csv
from datetime import date, datetime, timedelta, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    ContaBancaria,
    LancamentoBancario,
    Payment,
    RevenueEntry,
    RoleEnum,
    User,
)

router = APIRouter(prefix="/banco", tags=["banco"])

TOLERANCIA_DIAS = 3  # janela de tolerância para conciliação por data


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


def _conta_out(c: ContaBancaria) -> dict:
    return {
        "id": c.id,
        "banco": c.banco,
        "agencia": c.agencia,
        "numero_conta": c.numero_conta,
        "descricao": c.descricao,
        "tipo": c.tipo,
        "ativa": c.ativa,
        "saldo_inicial": c.saldo_inicial,
        "data_saldo_inicial": c.data_saldo_inicial.isoformat(),
        "created_at": c.created_at.isoformat(),
    }


def _lanc_out(l: LancamentoBancario) -> dict:
    return {
        "id": l.id,
        "conta_id": l.conta_id,
        "data_lancamento": l.data_lancamento.isoformat(),
        "tipo": l.tipo,
        "valor": l.valor,
        "descricao": l.descricao,
        "documento_ref": l.documento_ref,
        "status": l.status,
        "payment_id": l.payment_id,
        "revenue_entry_id": l.revenue_entry_id,
        "divergencia_obs": l.divergencia_obs,
        "conciliado_em": l.conciliado_em.isoformat() if l.conciliado_em else None,
        "conciliado_por_id": l.conciliado_por_id,
        "created_at": l.created_at.isoformat(),
    }


# ── Contas Bancárias ──────────────────────────────────────────────────────────

@router.get("/contas")
def list_contas(
    ativa: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ContaBancaria)
    if ativa is not None:
        q = q.filter(ContaBancaria.ativa == ativa)
    q = q.order_by(ContaBancaria.banco, ContaBancaria.numero_conta)
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": [_conta_out(c) for c in items]}


@router.post("/contas", status_code=201)
def create_conta(
    banco: str,
    agencia: str,
    numero_conta: str,
    data_saldo_inicial: date,
    descricao: str = "",
    tipo: str = "corrente",
    saldo_inicial: float = 0.0,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    if db.query(ContaBancaria).filter(ContaBancaria.numero_conta == numero_conta).first():
        raise HTTPException(status_code=400, detail="Conta já cadastrada")
    conta = ContaBancaria(
        banco=banco,
        agencia=agencia,
        numero_conta=numero_conta,
        descricao=descricao,
        tipo=tipo,
        saldo_inicial=saldo_inicial,
        data_saldo_inicial=data_saldo_inicial,
    )
    db.add(conta)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="contas_bancarias",
                entity_id=str(conta.id), after_data={"banco": banco, "numero_conta": numero_conta})
    db.commit()
    db.refresh(conta)
    return _conta_out(conta)


@router.get("/contas/{conta_id}")
def get_conta(conta_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    conta = db.get(ContaBancaria, conta_id)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    return _conta_out(conta)


@router.patch("/contas/{conta_id}")
def update_conta(
    conta_id: int,
    descricao: str | None = None,
    ativa: bool | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    conta = db.get(ContaBancaria, conta_id)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    if descricao is not None:
        conta.descricao = descricao
    if ativa is not None:
        conta.ativa = ativa
    write_audit(db, user_id=current.id, action="update", entity="contas_bancarias",
                entity_id=str(conta_id), after_data={"ativa": conta.ativa})
    db.commit()
    db.refresh(conta)
    return _conta_out(conta)


# ── Lançamentos Bancários ─────────────────────────────────────────────────────

@router.get("/lancamentos")
def list_lancamentos(
    conta_id: int | None = None,
    status: str | None = None,
    tipo: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(LancamentoBancario)
    if conta_id:
        q = q.filter(LancamentoBancario.conta_id == conta_id)
    if status:
        q = q.filter(LancamentoBancario.status == status)
    if tipo:
        q = q.filter(LancamentoBancario.tipo == tipo)
    if data_inicio:
        q = q.filter(LancamentoBancario.data_lancamento >= data_inicio)
    if data_fim:
        q = q.filter(LancamentoBancario.data_lancamento <= data_fim)
    q = q.order_by(LancamentoBancario.data_lancamento.desc(), LancamentoBancario.id.desc())
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": [_lanc_out(l) for l in items]}


@router.post("/lancamentos", status_code=201)
def create_lancamento(
    conta_id: int,
    data_lancamento: date,
    tipo: str,
    valor: float,
    descricao: str = "",
    documento_ref: str = "",
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Cadastro manual de lançamento bancário (extrato).

    tipo: 'credito' ou 'debito'
    valor: sempre positivo.
    """
    if tipo not in {"credito", "debito"}:
        raise HTTPException(status_code=400, detail="tipo deve ser 'credito' ou 'debito'")
    if valor <= 0:
        raise HTTPException(status_code=400, detail="valor deve ser positivo")
    conta = db.get(ContaBancaria, conta_id)
    if not conta:
        raise HTTPException(status_code=404, detail="Conta não encontrada")
    lanc = LancamentoBancario(
        conta_id=conta_id,
        data_lancamento=data_lancamento,
        tipo=tipo,
        valor=round(valor, 2),
        descricao=descricao,
        documento_ref=documento_ref,
    )
    db.add(lanc)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="lancamentos_bancarios",
                entity_id=str(lanc.id), after_data={"valor": valor, "tipo": tipo})
    db.commit()
    db.refresh(lanc)
    return _lanc_out(lanc)


@router.delete("/lancamentos/{lancamento_id}", status_code=204)
def delete_lancamento(
    lancamento_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    lanc = db.get(LancamentoBancario, lancamento_id)
    if not lanc:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    write_audit(db, user_id=current.id, action="delete", entity="lancamentos_bancarios",
                entity_id=str(lancamento_id), after_data={"status": lanc.status})
    db.delete(lanc)
    db.commit()


@router.patch("/lancamentos/{lancamento_id}/ignorar")
def ignorar_lancamento(
    lancamento_id: int,
    obs: str = "",
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Marca um lançamento como ignorado (ex: tarifa bancária sem correspondência ERP)."""
    lanc = db.get(LancamentoBancario, lancamento_id)
    if not lanc:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    lanc.status = "ignorado"
    lanc.divergencia_obs = obs or "Ignorado manualmente"
    lanc.conciliado_em = datetime.now(timezone.utc)
    lanc.conciliado_por_id = current.id
    write_audit(db, user_id=current.id, action="update", entity="lancamentos_bancarios",
                entity_id=str(lancamento_id), after_data={"status": "ignorado"})
    db.commit()
    db.refresh(lanc)
    return _lanc_out(lanc)


@router.patch("/lancamentos/{lancamento_id}/conciliar-manual")
def conciliar_manual(
    lancamento_id: int,
    payment_id: int | None = None,
    revenue_entry_id: int | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Conciliação manual: vincula um lançamento a um Payment ou RevenueEntry específico."""
    lanc = db.get(LancamentoBancario, lancamento_id)
    if not lanc:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if not payment_id and not revenue_entry_id:
        raise HTTPException(status_code=400, detail="Informe payment_id ou revenue_entry_id")
    if payment_id and revenue_entry_id:
        raise HTTPException(status_code=400, detail="Informe apenas um vínculo por vez")
    if payment_id:
        pay = db.get(Payment, payment_id)
        if not pay:
            raise HTTPException(status_code=404, detail="Pagamento não encontrado")
        lanc.payment_id = payment_id
        lanc.revenue_entry_id = None
        if round(pay.amount, 2) != round(lanc.valor, 2):
            lanc.status = "divergente"
            lanc.divergencia_obs = f"Valor ERP {pay.amount} ≠ extrato {lanc.valor}"
        else:
            lanc.status = "conciliado"
            lanc.divergencia_obs = None
    else:
        rev = db.get(RevenueEntry, revenue_entry_id)
        if not rev:
            raise HTTPException(status_code=404, detail="Receita não encontrada")
        lanc.revenue_entry_id = revenue_entry_id
        lanc.payment_id = None
        if round(rev.amount, 2) != round(lanc.valor, 2):
            lanc.status = "divergente"
            lanc.divergencia_obs = f"Valor ERP {rev.amount} ≠ extrato {lanc.valor}"
        else:
            lanc.status = "conciliado"
            lanc.divergencia_obs = None
    lanc.conciliado_em = datetime.now(timezone.utc)
    lanc.conciliado_por_id = current.id
    write_audit(db, user_id=current.id, action="update", entity="lancamentos_bancarios",
                entity_id=str(lancamento_id), after_data={"status": lanc.status})
    db.commit()
    db.refresh(lanc)
    return _lanc_out(lanc)


# ── Conciliação Automática ────────────────────────────────────────────────────

@router.post("/conciliacao/auto")
def conciliar_auto(
    conta_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Executa conciliação automática por valor exato ± tolerância de data.

    Regras:
      - Débito: cruza com Payment (valor exato, payment_date ±TOLERANCIA_DIAS).
      - Crédito: cruza com RevenueEntry (valor exato, entry_date ±TOLERANCIA_DIAS).
      - Se valor bate, data não → status divergente.
      - Não sobrescreve lançamentos já conciliados ou ignorados.

    Retorna resumo com totais de conciliados, divergentes e pendentes.
    """
    q = db.query(LancamentoBancario).filter(
        LancamentoBancario.status == "pendente"
    )
    if conta_id:
        q = q.filter(LancamentoBancario.conta_id == conta_id)
    if data_inicio:
        q = q.filter(LancamentoBancario.data_lancamento >= data_inicio)
    if data_fim:
        q = q.filter(LancamentoBancario.data_lancamento <= data_fim)

    lancamentos = q.all()

    # Pre-fetch unmatched payments and revenue entries for efficiency
    used_payment_ids: set[int] = set()
    used_revenue_ids: set[int] = set()

    # Payments already matched (conciliados)
    matched_pids = {r[0] for r in db.query(LancamentoBancario.payment_id).filter(
        LancamentoBancario.payment_id.isnot(None),
        LancamentoBancario.status == "conciliado",
    ).all()}
    matched_rids = {r[0] for r in db.query(LancamentoBancario.revenue_entry_id).filter(
        LancamentoBancario.revenue_entry_id.isnot(None),
        LancamentoBancario.status == "conciliado",
    ).all()}

    stats = {"conciliados": 0, "divergentes": 0, "pendentes": 0, "total_processados": len(lancamentos)}
    agora = datetime.now(timezone.utc)

    for lanc in lancamentos:
        tol_inicio = lanc.data_lancamento - timedelta(days=TOLERANCIA_DIAS)
        tol_fim = lanc.data_lancamento + timedelta(days=TOLERANCIA_DIAS)

        if lanc.tipo == "debito":
            # Try exact value match first, then relax date
            exact = (
                db.query(Payment)
                .filter(
                    Payment.amount == lanc.valor,
                    Payment.payment_date >= tol_inicio,
                    Payment.payment_date <= tol_fim,
                    ~Payment.id.in_(matched_pids | used_payment_ids),
                )
                .order_by(func.abs(Payment.payment_date - lanc.data_lancamento))
                .first()
            )
            if exact:
                lanc.payment_id = exact.id
                lanc.status = "conciliado"
                lanc.conciliado_em = agora
                lanc.conciliado_por_id = current.id
                lanc.divergencia_obs = None
                used_payment_ids.add(exact.id)
                stats["conciliados"] += 1
            else:
                # Check if value matches but date outside tolerance → divergente
                close = (
                    db.query(Payment)
                    .filter(
                        Payment.amount == lanc.valor,
                        ~Payment.id.in_(matched_pids | used_payment_ids),
                    )
                    .first()
                )
                if close:
                    delta = abs((close.payment_date - lanc.data_lancamento).days)
                    lanc.payment_id = close.id
                    lanc.status = "divergente"
                    lanc.divergencia_obs = f"Valor OK mas datas diferem em {delta} dias (tolerância {TOLERANCIA_DIAS})"
                    lanc.conciliado_em = agora
                    lanc.conciliado_por_id = current.id
                    used_payment_ids.add(close.id)
                    stats["divergentes"] += 1
                else:
                    stats["pendentes"] += 1

        else:  # credito
            exact = (
                db.query(RevenueEntry)
                .filter(
                    RevenueEntry.amount == lanc.valor,
                    RevenueEntry.entry_date >= tol_inicio,
                    RevenueEntry.entry_date <= tol_fim,
                    ~RevenueEntry.id.in_(matched_rids | used_revenue_ids),
                )
                .order_by(func.abs(RevenueEntry.entry_date - lanc.data_lancamento))
                .first()
            )
            if exact:
                lanc.revenue_entry_id = exact.id
                lanc.status = "conciliado"
                lanc.conciliado_em = agora
                lanc.conciliado_por_id = current.id
                lanc.divergencia_obs = None
                used_revenue_ids.add(exact.id)
                stats["conciliados"] += 1
            else:
                close = (
                    db.query(RevenueEntry)
                    .filter(
                        RevenueEntry.amount == lanc.valor,
                        ~RevenueEntry.id.in_(matched_rids | used_revenue_ids),
                    )
                    .first()
                )
                if close:
                    delta = abs((close.entry_date - lanc.data_lancamento).days)
                    lanc.revenue_entry_id = close.id
                    lanc.status = "divergente"
                    lanc.divergencia_obs = f"Valor OK mas datas diferem em {delta} dias (tolerância {TOLERANCIA_DIAS})"
                    lanc.conciliado_em = agora
                    lanc.conciliado_por_id = current.id
                    used_revenue_ids.add(close.id)
                    stats["divergentes"] += 1
                else:
                    stats["pendentes"] += 1

    db.commit()
    return {
        "message": "Conciliação automática concluída",
        "tolerancia_dias": TOLERANCIA_DIAS,
        **stats,
    }


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(
    conta_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Dashboard de conciliação: saldos, resumo por status, totais de crédito/débito."""
    q = db.query(LancamentoBancario)
    if conta_id:
        q = q.filter(LancamentoBancario.conta_id == conta_id)
    if data_inicio:
        q = q.filter(LancamentoBancario.data_lancamento >= data_inicio)
    if data_fim:
        q = q.filter(LancamentoBancario.data_lancamento <= data_fim)

    total_geral = q.count()
    conciliados = q.filter(LancamentoBancario.status == "conciliado").count()
    divergentes = q.filter(LancamentoBancario.status == "divergente").count()
    pendentes = q.filter(LancamentoBancario.status == "pendente").count()
    ignorados = q.filter(LancamentoBancario.status == "ignorado").count()

    # Reset filter for totals — re-apply base filters
    def base_q():
        bq = db.query(LancamentoBancario)
        if conta_id:
            bq = bq.filter(LancamentoBancario.conta_id == conta_id)
        if data_inicio:
            bq = bq.filter(LancamentoBancario.data_lancamento >= data_inicio)
        if data_fim:
            bq = bq.filter(LancamentoBancario.data_lancamento <= data_fim)
        return bq

    total_creditos = float(
        base_q().filter(LancamentoBancario.tipo == "credito")
        .with_entities(func.coalesce(func.sum(LancamentoBancario.valor), 0.0))
        .scalar()
    )
    total_debitos = float(
        base_q().filter(LancamentoBancario.tipo == "debito")
        .with_entities(func.coalesce(func.sum(LancamentoBancario.valor), 0.0))
        .scalar()
    )

    # Saldo bancário projetado: soma saldos iniciais das contas + créditos - débitos
    contas_q = db.query(ContaBancaria).filter(ContaBancaria.ativa == True)
    if conta_id:
        contas_q = contas_q.filter(ContaBancaria.id == conta_id)
    saldo_inicial_total = float(
        contas_q.with_entities(func.coalesce(func.sum(ContaBancaria.saldo_inicial), 0.0)).scalar()
    )
    saldo_projetado = round(saldo_inicial_total + total_creditos - total_debitos, 2)

    pct_conciliado = round(conciliados / total_geral * 100, 1) if total_geral else 0.0

    return {
        "total_lancamentos": total_geral,
        "conciliados": conciliados,
        "divergentes": divergentes,
        "pendentes": pendentes,
        "ignorados": ignorados,
        "pct_conciliado": pct_conciliado,
        "total_creditos": round(total_creditos, 2),
        "total_debitos": round(total_debitos, 2),
        "saldo_inicial_contas": round(saldo_inicial_total, 2),
        "saldo_projetado": saldo_projetado,
    }


# ── Relatório ─────────────────────────────────────────────────────────────────

@router.get("/conciliacao/relatorio")
def relatorio_conciliacao(
    conta_id: int | None = None,
    status: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    export: str | None = Query(default=None),
    page: int = Query(1, ge=1),
    size: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório detalhado de lançamentos com status de conciliação."""
    q = db.query(LancamentoBancario)
    if conta_id:
        q = q.filter(LancamentoBancario.conta_id == conta_id)
    if status:
        q = q.filter(LancamentoBancario.status == status)
    if data_inicio:
        q = q.filter(LancamentoBancario.data_lancamento >= data_inicio)
    if data_fim:
        q = q.filter(LancamentoBancario.data_lancamento <= data_fim)
    q = q.order_by(LancamentoBancario.data_lancamento.asc(), LancamentoBancario.id.asc())

    if export == "csv":
        rows = q.all()
        buf = StringIO()
        w = csv.writer(buf)
        w.writerow([
            "id", "conta_id", "data", "tipo", "valor", "descricao",
            "documento_ref", "status", "payment_id", "revenue_entry_id", "divergencia_obs",
        ])
        for l in rows:
            w.writerow([
                l.id, l.conta_id, l.data_lancamento, l.tipo, l.valor,
                l.descricao, l.documento_ref, l.status,
                l.payment_id or "", l.revenue_entry_id or "", l.divergencia_obs or "",
            ])
        fname = f"conciliacao_{data_inicio or 'todos'}_{data_fim or 'todos'}.csv"
        return Response(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={fname}"},
        )

    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": [_lanc_out(l) for l in items]}
