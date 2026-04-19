import csv
from io import StringIO

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import (
    Commitment,
    Contract,
    Convenio,
    ConvenioDesembolso,
    DividaAtiva,
    LancamentoTributario,
    Payment,
    ProcurementProcess,
    Vendor,
)

router = APIRouter(prefix="/public", tags=["public"])


def paginated(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


def _csv(headers: list[str], rows: list[list]) -> Response:
    buf = StringIO()
    w = csv.writer(buf)
    w.writerow(headers)
    for r in rows:
        w.writerow(r)
    return Response(content=buf.getvalue(), media_type="text/csv",
                    headers={"Content-Disposition": "attachment; filename=export.csv"})


# ── Empenhos ──────────────────────────────────────────────────────────────────

@router.get("/commitments")
def commitments(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    export: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Commitment)
    if search:
        q = q.filter(Commitment.description.ilike(f"%{search}%"))
    items = q.order_by(Commitment.id.desc())
    if export == "csv":
        return _csv(
            ["numero", "descricao", "valor", "status"],
            [[r.number, r.description, r.amount, r.status] for r in items.all()],
        )
    return paginated(items, page, size)


# ── Pagamentos ────────────────────────────────────────────────────────────────

@router.get("/payments")
def payments(
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return paginated(db.query(Payment).order_by(Payment.id.desc()), page, size)


# ── Fornecedores ──────────────────────────────────────────────────────────────

@router.get("/vendors")
def vendors(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
):
    q = db.query(Vendor)
    if search:
        q = q.filter(Vendor.name.ilike(f"%{search}%"))
    return paginated(q.order_by(Vendor.name), page, size)


# ── Contratos ─────────────────────────────────────────────────────────────────

@router.get("/contracts")
def contracts(
    search: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    export: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Contract)
    if search:
        q = q.filter(Contract.number.ilike(f"%{search}%"))
    if status:
        q = q.filter(Contract.status == status)
    q = q.order_by(Contract.id.desc())
    if export == "csv":
        return _csv(
            ["numero", "inicio", "fim", "valor", "status"],
            [[r.number, str(r.start_date), str(r.end_date), r.amount, r.status] for r in q.all()],
        )
    return paginated(q, page, size)


# ── Processos Licitatórios ────────────────────────────────────────────────────

@router.get("/licitacoes")
def licitacoes(
    search: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    export: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(ProcurementProcess)
    if search:
        q = q.filter(
            ProcurementProcess.number.ilike(f"%{search}%")
            | ProcurementProcess.object_description.ilike(f"%{search}%")
        )
    if status:
        q = q.filter(ProcurementProcess.status == status)
    q = q.order_by(ProcurementProcess.id.desc())
    if export == "csv":
        return _csv(
            ["numero", "objeto", "status"],
            [[r.number, r.object_description, r.status] for r in q.all()],
        )
    return paginated(q, page, size)


# ── Convênios ─────────────────────────────────────────────────────────────────

@router.get("/convenios")
def convenios(
    search: str | None = None,
    tipo: str | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    export: str | None = None,
    db: Session = Depends(get_db),
):
    q = db.query(Convenio)
    # Exclude draft (rascunho) from public view
    q = q.filter(Convenio.status != "rascunho")
    if search:
        q = q.filter(
            Convenio.numero.ilike(f"%{search}%")
            | Convenio.objeto.ilike(f"%{search}%")
            | Convenio.concedente.ilike(f"%{search}%")
        )
    if tipo:
        q = q.filter(Convenio.tipo == tipo)
    if status:
        q = q.filter(Convenio.status == status)
    q = q.order_by(Convenio.data_assinatura.desc())
    if export == "csv":
        return _csv(
            ["numero", "objeto", "concedente", "tipo", "valor_total", "data_assinatura", "data_inicio", "data_fim", "status"],
            [[r.numero, r.objeto, r.concedente, r.tipo, r.valor_total,
              str(r.data_assinatura), str(r.data_inicio), str(r.data_fim), r.status]
             for r in q.all()],
        )
    return paginated(q, page, size)


@router.get("/convenios/{convenio_id}/desembolsos")
def convenio_desembolsos(
    convenio_id: int,
    db: Session = Depends(get_db),
):
    rows = db.query(ConvenioDesembolso).filter(ConvenioDesembolso.convenio_id == convenio_id).order_by(ConvenioDesembolso.numero_parcela).all()
    return {"items": [{"parcela": r.numero_parcela, "valor": r.valor, "data_prevista": str(r.data_prevista), "data_efetiva": str(r.data_efetiva) if r.data_efetiva else None, "status": r.status} for r in rows]}


# ── Arrecadação Tributária (dados públicos) ───────────────────────────────────

@router.get("/arrecadacao")
def arrecadacao(
    tributo: str | None = None,
    exercicio: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    export: str | None = None,
    db: Session = Depends(get_db),
):
    """Lançamentos tributários pagos — publicidade da arrecadação municipal."""
    q = db.query(LancamentoTributario).filter(LancamentoTributario.status == "pago")
    if tributo:
        q = q.filter(LancamentoTributario.tributo == tributo)
    if exercicio:
        q = q.filter(LancamentoTributario.exercicio == exercicio)
    q = q.order_by(LancamentoTributario.data_pagamento.desc())
    if export == "csv":
        return _csv(
            ["tributo", "competencia", "exercicio", "valor_total", "data_pagamento"],
            [[r.tributo, r.competencia, r.exercicio, r.valor_total, str(r.data_pagamento)] for r in q.all()],
        )
    return paginated(q, page, size)


@router.get("/divida-ativa")
def divida_ativa_publica(
    tributo: str | None = None,
    exercicio: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    export: str | None = None,
    db: Session = Depends(get_db),
):
    """Inscrições em dívida ativa (ativa/ajuizada) — dados públicos sem identificação pessoal."""
    q = db.query(DividaAtiva).filter(DividaAtiva.status.in_(["ativa", "ajuizada"]))
    if tributo:
        q = q.filter(DividaAtiva.tributo == tributo)
    if exercicio:
        q = q.filter(DividaAtiva.exercicio == exercicio)
    q = q.order_by(DividaAtiva.data_inscricao.desc())
    if export == "csv":
        return _csv(
            ["numero_inscricao", "tributo", "exercicio", "valor_original", "valor_atualizado", "data_inscricao", "status"],
            [[r.numero_inscricao, r.tributo, r.exercicio, r.valor_original, r.valor_atualizado, str(r.data_inscricao), r.status] for r in q.all()],
        )
    # Strip personal data from public listing
    items = [
        {
            "numero_inscricao": r.numero_inscricao,
            "tributo": r.tributo,
            "exercicio": r.exercicio,
            "valor_original": r.valor_original,
            "valor_atualizado": r.valor_atualizado,
            "data_inscricao": str(r.data_inscricao),
            "status": r.status,
        }
        for r in q.offset((page - 1) * size).limit(size).all()
    ]
    return {"total": q.count(), "page": page, "size": size, "items": items}


# ── Estatísticas / Dashboard público ─────────────────────────────────────────

@router.get("/stats")
def stats(db: Session = Depends(get_db)):
    """Indicadores de transparência municipal consolidados."""
    total_empenhos = db.query(func.count(Commitment.id)).scalar() or 0
    valor_empenhos = db.query(func.sum(Commitment.amount)).scalar() or 0.0
    total_contratos = db.query(func.count(Contract.id)).scalar() or 0
    valor_contratos = db.query(func.sum(Contract.amount)).scalar() or 0.0
    total_licitacoes = db.query(func.count(ProcurementProcess.id)).scalar() or 0
    total_convenios = db.query(func.count(Convenio.id)).filter(Convenio.status != "rascunho").scalar() or 0
    valor_convenios = db.query(func.sum(Convenio.valor_total)).filter(Convenio.status != "rascunho").scalar() or 0.0
    arrecadacao_total = db.query(func.sum(LancamentoTributario.valor_total)).filter(LancamentoTributario.status == "pago").scalar() or 0.0
    divida_total = db.query(func.sum(DividaAtiva.valor_atualizado)).filter(DividaAtiva.status.in_(["ativa", "ajuizada"])).scalar() or 0.0

    return {
        "empenhos": {"total": total_empenhos, "valor": round(valor_empenhos, 2)},
        "contratos": {"total": total_contratos, "valor": round(valor_contratos, 2)},
        "licitacoes": {"total": total_licitacoes},
        "convenios": {"total": total_convenios, "valor": round(valor_convenios, 2)},
        "arrecadacao_tributaria": {"arrecadado": round(arrecadacao_total, 2), "divida_ativa": round(divida_total, 2)},
    }

