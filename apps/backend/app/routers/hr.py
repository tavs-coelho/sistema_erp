from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Employee, PayrollEvent, Payslip, RoleEnum, User
from ..schemas import EmployeeCreate, EmployeeOut, PayrollCalculationRequest, PayrollEventCreate
from ..services.payroll import build_simple_pdf

router = APIRouter(prefix="/hr", tags=["hr"])


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    return db.query(Employee).order_by(Employee.id).all()


@router.post("/employees", response_model=EmployeeOut)
def create_employee(payload: EmployeeCreate, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr))):
    employee = Employee(**payload.model_dump())
    db.add(employee)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="employees", entity_id=str(employee.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(employee)
    return employee


@router.get("/payroll-events")
def list_payroll_events(
    month: str | None = None,
    employee_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr, RoleEnum.read_only)),
):
    q = db.query(PayrollEvent)
    if month:
        q = q.filter(PayrollEvent.month == month)
    if employee_id:
        q = q.filter(PayrollEvent.employee_id == employee_id)
    total = q.count()
    items = q.order_by(PayrollEvent.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.post("/payroll-events")
def create_payroll_event(
    payload: PayrollEventCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    event = PayrollEvent(**payload.model_dump())
    db.add(event)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="payroll_events", entity_id=str(event.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(event)
    return event


@router.post("/payroll/calculate")
def calculate_payroll(payload: PayrollCalculationRequest, db: Session = Depends(get_db), current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr))):
    employees = db.query(Employee).all()
    created = 0
    for emp in employees:
        total_events = sum(v.value for v in db.query(PayrollEvent).filter(PayrollEvent.employee_id == emp.id, PayrollEvent.month == payload.month).all())
        gross = emp.base_salary + total_events
        deductions = gross * 0.11
        net = gross - deductions
        existing = db.query(Payslip).filter(Payslip.employee_id == emp.id, Payslip.month == payload.month).first()
        if existing:
            existing.gross_amount, existing.deductions, existing.net_amount = gross, deductions, net
        else:
            db.add(Payslip(employee_id=emp.id, month=payload.month, gross_amount=gross, deductions=deductions, net_amount=net))
            created += 1
    write_audit(db, user_id=current.id, action="create", entity="payroll", entity_id=payload.month, after_data={"created": created})
    db.commit()
    return {"message": "Folha calculada", "created": created}


@router.get("/payslips/{payslip_id}/pdf")
def payslip_pdf(payslip_id: int, db: Session = Depends(get_db), user: User = Depends(get_current_user)):
    payslip = db.get(Payslip, payslip_id)
    if not payslip:
        raise HTTPException(status_code=404, detail="Holerite não encontrado")
    if user.role == RoleEnum.employee and user.employee_id != payslip.employee_id:
        raise HTTPException(status_code=403, detail="Sem permissão")
    pdf = build_simple_pdf(
        "Holerite",
        [
            f"Mes: {payslip.month}",
            f"Bruto: {payslip.gross_amount:.2f}",
            f"Descontos: {payslip.deductions:.2f}",
            f"Liquido: {payslip.net_amount:.2f}",
        ],
    )
    return Response(content=pdf, media_type="application/pdf", headers={"Content-Disposition": f"inline; filename=holerite-{payslip.id}.pdf"})


@router.get("/reports/by-department")
def payroll_by_department(db: Session = Depends(get_db), _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr, RoleEnum.read_only))):
    rows = []
    for emp in db.query(Employee).all():
        rows.append({"department_id": emp.department_id, "employee": emp.name, "salary": emp.base_salary})
    return rows
