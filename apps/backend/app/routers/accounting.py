import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import BudgetAllocation, Commitment, FundingSource, Liquidation, LOAItem, Payment, RevenueEntry, RoleEnum, User, Vendor
from ..schemas import (
    BudgetAllocationCreate,
    BudgetAllocationOut,
    CommitmentCreate,
    CommitmentOut,
    PaymentCreate,
    PaymentOut,
    VendorCreate,
    VendorOut,
    VendorUpdate,
)

router = APIRouter(prefix="/accounting", tags=["accounting"])


def paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/vendors")
def list_vendors(
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Vendor)
    if search:
        query = query.filter(Vendor.name.ilike(f"%{search}%"))
    return paginate(query.order_by(Vendor.name), page, size)


@router.post("/vendors", response_model=VendorOut)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant, RoleEnum.procurement))):
    vendor = Vendor(**payload.model_dump())
    db.add(vendor)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="vendors", entity_id=str(vendor.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/budget-allocations")
def list_budget_allocations(
    search: str | None = None,
    fiscal_year_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(BudgetAllocation)
    if search:
        query = query.filter(BudgetAllocation.description.ilike(f"%{search}%"))
    if fiscal_year_id:
        query = query.filter(BudgetAllocation.fiscal_year_id == fiscal_year_id)
    return paginate(query.order_by(BudgetAllocation.code), page, size)


@router.post("/budget-allocations", response_model=BudgetAllocationOut)
def create_budget_allocation(
    payload: BudgetAllocationCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    allocation = BudgetAllocation(**payload.model_dump())
    db.add(allocation)
    db.flush()
    write_audit(
        db,
        user_id=current.id,
        action="create",
        entity="budget_allocations",
        entity_id=str(allocation.id),
        after_data=payload.model_dump(),
    )
    db.commit()
    db.refresh(allocation)
    return allocation


@router.get("/commitments")
def list_commitments(
    status: str | None = None,
    vendor_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Commitment)
    if status:
        query = query.filter(Commitment.status == status)
    if vendor_id:
        query = query.filter(Commitment.vendor_id == vendor_id)
    return paginate(query.order_by(Commitment.id.desc()), page, size)


@router.post("/commitments", response_model=CommitmentOut)
def create_commitment(payload: CommitmentCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant))):
    obj = Commitment(**payload.model_dump())
    db.add(obj)
    db.flush()
    # ORC-05: atualiza executed_amount na dotação LOA vinculada
    if payload.loa_item_id:
        loa_item = db.get(LOAItem, payload.loa_item_id)
        if loa_item:
            loa_item.executed_amount = round(loa_item.executed_amount + payload.amount, 2)
    write_audit(db, user_id=current.id, action="create", entity="commitments", entity_id=str(obj.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/liquidate/{commitment_id}")
def liquidate_commitment(commitment_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant))):
    commitment = db.get(Commitment, commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Empenho não encontrado")
    if commitment.status in {"liquidado", "pago"}:
        return {"message": f"Empenho já está {commitment.status}"}
    db.add(Liquidation(commitment_id=commitment.id, amount=commitment.amount))
    commitment.status = "liquidado"
    write_audit(db, user_id=current.id, action="update", entity="commitments", entity_id=str(commitment.id), after_data={"status": commitment.status})
    db.commit()
    return {"message": "Empenho liquidado"}


@router.get("/payments")
def list_payments(
    commitment_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Payment)
    if commitment_id:
        query = query.filter(Payment.commitment_id == commitment_id)
    return paginate(query.order_by(Payment.payment_date.desc(), Payment.id.desc()), page, size)


@router.post("/payments", response_model=PaymentOut)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant))):
    commitment = db.get(Commitment, payload.commitment_id)
    if not commitment:
        raise HTTPException(status_code=404, detail="Empenho não encontrado")
    obj = Payment(**payload.model_dump())
    db.add(obj)
    commitment.status = "pago"
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="payments", entity_id=str(obj.id), after_data=payload.model_dump(mode="json"))
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/revenue")
def create_revenue(description: str, amount: float, entry_date: date = date.today(), db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant))):
    rev = RevenueEntry(description=description, amount=amount, entry_date=entry_date)
    db.add(rev)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="revenue_entries", entity_id=str(rev.id), after_data={"amount": amount})
    db.commit()
    return {"id": rev.id}


@router.get("/dashboard")
def accounting_dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return {
        "total_empenhado": db.query(func.coalesce(func.sum(Commitment.amount), 0)).scalar(),
        "total_pago": db.query(func.coalesce(func.sum(Payment.amount), 0)).scalar(),
        "total_receita": db.query(func.coalesce(func.sum(RevenueEntry.amount), 0)).scalar(),
    }


@router.get("/reports/commitments")
def commitments_report(
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    export: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Commitment)
    if status:
        query = query.filter(Commitment.status == status)
    query = query.order_by(Commitment.number)
    data = query.all()
    if export == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["numero", "descricao", "valor", "status"])
        for c in data:
            writer.writerow([c.number, c.description, c.amount, c.status])
        return Response(content=buf.getvalue(), media_type="text/csv")
    return paginate(query, page, size)
