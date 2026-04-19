import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import BudgetAllocation, Commitment, FundingSource, Payment, RevenueEntry, RoleEnum, User, Vendor
from ..schemas import CommitmentCreate, CommitmentOut, PaymentCreate, PaymentOut, VendorCreate, VendorOut

router = APIRouter(prefix="/accounting", tags=["accounting"])


@router.get("/vendors", response_model=list[VendorOut])
def list_vendors(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Vendor).order_by(Vendor.name).all()


@router.post("/vendors", response_model=VendorOut)
def create_vendor(payload: VendorCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant, RoleEnum.procurement))):
    vendor = Vendor(**payload.model_dump())
    db.add(vendor)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="vendors", entity_id=str(vendor.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(vendor)
    return vendor


@router.get("/commitments", response_model=list[CommitmentOut])
def list_commitments(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Commitment).order_by(Commitment.id.desc()).all()


@router.post("/commitments", response_model=CommitmentOut)
def create_commitment(payload: CommitmentCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant))):
    obj = Commitment(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="commitments", entity_id=str(obj.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/liquidate/{commitment_id}")
def liquidate_commitment(commitment_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant))):
    commitment = db.get(Commitment, commitment_id)
    commitment.status = "liquidado"
    write_audit(db, user_id=current.id, action="update", entity="commitments", entity_id=str(commitment.id), after_data={"status": commitment.status})
    db.commit()
    return {"message": "Empenho liquidado"}


@router.get("/payments", response_model=list[PaymentOut])
def list_payments(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Payment).order_by(Payment.payment_date.desc()).all()


@router.post("/payments", response_model=PaymentOut)
def create_payment(payload: PaymentCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant))):
    obj = Payment(**payload.model_dump())
    db.add(obj)
    commitment = db.get(Commitment, payload.commitment_id)
    if commitment:
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
    export: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    query = db.query(Commitment)
    if status:
        query = query.filter(Commitment.status == status)
    data = query.order_by(Commitment.number).all()
    if export == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["numero", "descricao", "valor", "status"])
        for c in data:
            writer.writerow([c.number, c.description, c.amount, c.status])
        return Response(content=buf.getvalue(), media_type="text/csv")
    return data
