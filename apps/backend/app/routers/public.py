from io import StringIO
import csv

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from ..db import get_db
from ..models import Commitment, Contract, Payment, Vendor

router = APIRouter(prefix="/public", tags=["public"])


def paginated(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/commitments")
def commitments(search: str | None = None, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), export: str | None = None, db: Session = Depends(get_db)):
    q = db.query(Commitment)
    if search:
        q = q.filter(Commitment.description.ilike(f"%{search}%"))
    items = q.order_by(Commitment.id.desc())
    if export == "csv":
        buf = StringIO(); w = csv.writer(buf); w.writerow(["numero", "descricao", "valor", "status"])
        for row in items.all():
            w.writerow([row.number, row.description, row.amount, row.status])
        return Response(content=buf.getvalue(), media_type="text/csv")
    return paginated(items, page, size)


@router.get("/payments")
def payments(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return paginated(db.query(Payment).order_by(Payment.id.desc()), page, size)


@router.get("/contracts")
def contracts(page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    return paginated(db.query(Contract).order_by(Contract.id.desc()), page, size)


@router.get("/vendors")
def vendors(search: str | None = None, page: int = Query(1, ge=1), size: int = Query(10, ge=1, le=100), db: Session = Depends(get_db)):
    q = db.query(Vendor)
    if search:
        q = q.filter(Vendor.name.ilike(f"%{search}%"))
    return paginated(q.order_by(Vendor.name), page, size)
