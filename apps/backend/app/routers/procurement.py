from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Contract, ContractAddendum, ProcurementProcess, RoleEnum, User
from ..schemas import ContractCreate, ContractUpdate, ProcurementProcessCreate, ProcurementProcessUpdate

router = APIRouter(prefix="/procurement", tags=["procurement"])


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/processes")
def list_processes(
    status: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ProcurementProcess)
    if status:
        q = q.filter(ProcurementProcess.status == status)
    if search:
        q = q.filter(ProcurementProcess.object_description.ilike(f"%{search}%"))
    return _paginate(q.order_by(ProcurementProcess.id.desc()), page, size)


@router.post("/processes")
def create_process(payload: ProcurementProcessCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement))):
    if db.query(ProcurementProcess).filter(ProcurementProcess.number == payload.number).first():
        raise HTTPException(status_code=409, detail="Número de processo já existe")
    obj = ProcurementProcess(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="procurement_processes", entity_id=str(obj.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/processes/{process_id}")
def get_process(process_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(ProcurementProcess, process_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    return obj


@router.patch("/processes/{process_id}")
def update_process(
    process_id: int,
    payload: ProcurementProcessUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    obj = db.get(ProcurementProcess, process_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    before = {"status": obj.status, "object_description": obj.object_description}
    if payload.object_description is not None:
        obj.object_description = payload.object_description
    if payload.status is not None:
        obj.status = payload.status
    write_audit(db, user_id=current.id, action="update", entity="procurement_processes", entity_id=str(obj.id), before_data=before, after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/processes/{process_id}/award")
def award_process(process_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement))):
    obj = db.get(ProcurementProcess, process_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    before = {"status": obj.status}
    obj.status = "homologado"
    write_audit(db, user_id=current.id, action="update", entity="procurement_processes", entity_id=str(obj.id), before_data=before, after_data={"status": obj.status})
    db.commit()
    return {"message": "Processo homologado"}


@router.get("/contracts")
def list_contracts(
    status: str | None = None,
    vendor_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Contract)
    if status:
        q = q.filter(Contract.status == status)
    if vendor_id:
        q = q.filter(Contract.vendor_id == vendor_id)
    return _paginate(q.order_by(Contract.id.desc()), page, size)


@router.get("/contracts/expiring")
def expiring_contracts(days: int = 60, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    limit_date = date.today() + timedelta(days=days)
    return db.query(Contract).filter(Contract.end_date <= limit_date, Contract.status == "vigente").all()


@router.get("/contracts/{contract_id}")
def get_contract(contract_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(Contract, contract_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return obj


@router.post("/contracts")
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement))):
    if db.query(Contract).filter(Contract.number == payload.number).first():
        raise HTTPException(status_code=409, detail="Número de contrato já existe")
    contract = Contract(**payload.model_dump())
    db.add(contract)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="contracts", entity_id=str(contract.id), after_data=payload.model_dump(mode="json"))
    db.commit()
    db.refresh(contract)
    return contract


@router.patch("/contracts/{contract_id}")
def update_contract(
    contract_id: int,
    payload: ContractUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    obj = db.get(Contract, contract_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    before = {"status": obj.status, "amount": obj.amount}
    if payload.start_date is not None:
        obj.start_date = payload.start_date
    if payload.end_date is not None:
        obj.end_date = payload.end_date
    if payload.amount is not None:
        obj.amount = payload.amount
    if payload.status is not None:
        obj.status = payload.status
    write_audit(db, user_id=current.id, action="update", entity="contracts", entity_id=str(obj.id), before_data=before, after_data=payload.model_dump(exclude_none=True, mode="json"))
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/contracts/{contract_id}/addenda")
def add_addendum(contract_id: int, description: str, amount_delta: float, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement))):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    add = ContractAddendum(contract_id=contract_id, description=description, amount_delta=amount_delta)
    db.add(add)
    contract.amount += amount_delta
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="contract_addenda", entity_id=str(add.id), after_data={"contract_id": contract_id, "amount_delta": amount_delta})
    db.commit()
    return {"id": add.id}


@router.get("/contracts/{contract_id}/addenda")
def list_addenda(contract_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    contract = db.get(Contract, contract_id)
    if not contract:
        raise HTTPException(status_code=404, detail="Contrato não encontrado")
    return db.query(ContractAddendum).filter(ContractAddendum.contract_id == contract_id).all()
