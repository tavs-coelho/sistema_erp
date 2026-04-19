from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Contract, ContractAddendum, ProcurementProcess, RoleEnum, User
from ..schemas import ContractCreate, ProcurementProcessCreate

router = APIRouter(prefix="/procurement", tags=["procurement"])


@router.get("/processes")
def list_processes(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(ProcurementProcess).order_by(ProcurementProcess.id.desc()).all()


@router.post("/processes")
def create_process(payload: ProcurementProcessCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement))):
    obj = ProcurementProcess(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="procurement_processes", entity_id=str(obj.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/processes/{process_id}/award")
def award_process(process_id: int, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement))):
    obj = db.get(ProcurementProcess, process_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Processo não encontrado")
    obj.status = "homologado"
    write_audit(db, user_id=current.id, action="update", entity="procurement_processes", entity_id=str(obj.id), after_data={"status": obj.status})
    db.commit()
    return {"message": "Processo homologado"}


@router.get("/contracts")
def list_contracts(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Contract).order_by(Contract.id.desc()).all()


@router.post("/contracts")
def create_contract(payload: ContractCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement))):
    contract = Contract(**payload.model_dump())
    db.add(contract)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="contracts", entity_id=str(contract.id), after_data=payload.model_dump(mode="json"))
    db.commit()
    db.refresh(contract)
    return contract


@router.post("/contracts/{contract_id}/addenda")
def add_addendum(contract_id: int, description: str, amount_delta: float, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement))):
    add = ContractAddendum(contract_id=contract_id, description=description, amount_delta=amount_delta)
    db.add(add)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="contract_addenda", entity_id=str(add.id), after_data={"contract_id": contract_id})
    db.commit()
    return {"id": add.id}


@router.get("/contracts/expiring")
def expiring_contracts(days: int = 60, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    limit_date = date.today() + timedelta(days=days)
    return db.query(Contract).filter(Contract.end_date <= limit_date).all()
