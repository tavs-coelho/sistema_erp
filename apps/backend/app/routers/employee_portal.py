from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Payslip, RoleEnum, User
from ..schemas import ChangePasswordRequest
from ..security import hash_password

router = APIRouter(prefix="/employee-portal", tags=["employee_portal"])


@router.get("/me")
def me(user: User = Depends(require_roles(RoleEnum.employee, RoleEnum.admin, RoleEnum.hr))):
    return {"id": user.id, "username": user.username, "name": user.full_name, "role": user.role}


@router.get("/payslips")
def my_payslips(db: Session = Depends(get_db), user: User = Depends(require_roles(RoleEnum.employee, RoleEnum.admin, RoleEnum.hr))):
    if user.role == RoleEnum.employee:
        return db.query(Payslip).filter(Payslip.employee_id == user.employee_id).all()
    return db.query(Payslip).all()


@router.get("/income-statement")
def income_statement(db: Session = Depends(get_db), user: User = Depends(require_roles(RoleEnum.employee, RoleEnum.admin, RoleEnum.hr))):
    if user.employee_id is None:
        return {"employee": user.full_name, "total_liquido": 0.0, "periodos": 0}
    slips = db.query(Payslip).filter(Payslip.employee_id == user.employee_id).all()
    total = sum(s.net_amount for s in slips)
    return {"employee": user.full_name, "total_liquido": total, "periodos": len(slips)}


@router.post("/change-password")
def change_password(payload: ChangePasswordRequest, db: Session = Depends(get_db), user: User = Depends(require_roles(RoleEnum.employee, RoleEnum.admin, RoleEnum.hr))):
    user.hashed_password = hash_password(payload.new_password)
    user.must_change_password = False
    db.commit()
    return {"message": "Senha alterada"}
