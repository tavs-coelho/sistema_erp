from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Employee, PayrollEvent, Payslip, RecalcularPayslipLog, RoleEnum, User
from ..schemas import (
    EmployeeCreate,
    EmployeeOut,
    PayrollCalculationRequest,
    PayrollEventCreate,
    RecalcularPayslipRequest,
    RecalcularPayslipOut,
)
from ..services.payroll import build_simple_pdf

router = APIRouter(prefix="/hr", tags=["hr"])

# ── Helpers ───────────────────────────────────────────────────────────────────

def calcular_valores_payslip(
    db: Session,
    employee_id: int,
    periodo: str,
    taxa_deducao: float = 11.0,
) -> tuple[float, float, float]:
    """Calcula (gross, deductions, net) para um servidor em um período.

    gross = base_salary
            + sum(PayrollEvents kind='provento')
            - sum(PayrollEvents kind='desconto')
    deductions = gross * taxa_deducao / 100
    net = gross - deductions

    Nota: a taxa_deducao é uma simplificação do INSS/IRRF. Refinamentos
    futuros devem usar tabelas progressivas reais.
    """
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail=f"Servidor {employee_id} não encontrado")

    events = (
        db.query(PayrollEvent)
        .filter(PayrollEvent.employee_id == employee_id, PayrollEvent.month == periodo)
        .all()
    )
    proventos = sum(e.value for e in events if e.kind == "provento")
    descontos = sum(e.value for e in events if e.kind == "desconto")
    gross = round(emp.base_salary + proventos - descontos, 2)
    deductions = round(gross * taxa_deducao / 100.0, 2)
    net = round(gross - deductions, 2)
    return gross, deductions, net


def recalcular_payslip_servidor(
    db: Session,
    employee_id: int,
    periodo: str,
    taxa_deducao: float = 11.0,
    origem: str = "manual",
    executado_por_id: int | None = None,
) -> dict:
    """Recalcula e persiste o Payslip de um servidor para o período dado.

    Retorna um dict com status ('criado' | 'atualizado' | 'erro') e valores.
    Não faz commit — o chamador é responsável por commitar.
    """
    try:
        gross, deductions, net = calcular_valores_payslip(db, employee_id, periodo, taxa_deducao)
    except HTTPException as exc:
        return {"employee_id": employee_id, "status": "erro", "motivo": str(exc.detail),
                "gross_amount": 0.0, "deductions": 0.0, "net_amount": 0.0, "variacao_net": 0.0}

    emp = db.get(Employee, employee_id)
    existing = (
        db.query(Payslip)
        .filter(Payslip.employee_id == employee_id, Payslip.month == periodo)
        .first()
    )

    gross_ant = existing.gross_amount if existing else None
    ded_ant = existing.deductions if existing else None
    net_ant = existing.net_amount if existing else None
    variacao = round(net - (net_ant or 0.0), 2)
    status = "atualizado" if existing else "criado"

    if existing:
        existing.gross_amount = gross
        existing.deductions = deductions
        existing.net_amount = net
    else:
        db.add(Payslip(employee_id=employee_id, month=periodo,
                       gross_amount=gross, deductions=deductions, net_amount=net))

    db.add(RecalcularPayslipLog(
        employee_id=employee_id,
        periodo=periodo,
        gross_amount_anterior=gross_ant,
        gross_amount_novo=gross,
        deductions_anterior=ded_ant,
        deductions_novo=deductions,
        net_amount_anterior=net_ant,
        net_amount_novo=net,
        origem=origem,
        executado_por_id=executado_por_id,
    ))

    return {
        "employee_id": employee_id,
        "employee_name": emp.name if emp else "",
        "periodo": periodo,
        "gross_amount": gross,
        "deductions": deductions,
        "net_amount": net,
        "status": status,
        "variacao_net": variacao,
    }


# ── Endpoints ─────────────────────────────────────────────────────────────────


@router.get("/employees", response_model=list[EmployeeOut])
def list_employees(
    search: str | None = None,
    department_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Employee)
    if search:
        q = q.filter(Employee.name.ilike(f"%{search}%"))
    if department_id:
        q = q.filter(Employee.department_id == department_id)
    items = q.order_by(Employee.id.desc()).offset((page - 1) * size).limit(size).all()
    return items


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
        gross, deductions, net = calcular_valores_payslip(db, emp.id, payload.month)
        existing = db.query(Payslip).filter(Payslip.employee_id == emp.id, Payslip.month == payload.month).first()
        if existing:
            existing.gross_amount, existing.deductions, existing.net_amount = gross, deductions, net
        else:
            db.add(Payslip(employee_id=emp.id, month=payload.month, gross_amount=gross, deductions=deductions, net_amount=net))
            created += 1
    write_audit(db, user_id=current.id, action="create", entity="payroll", entity_id=payload.month, after_data={"created": created})
    db.commit()
    return {"message": "Folha calculada", "created": created}


@router.post("/payslips/recalcular", response_model=RecalcularPayslipOut)
def recalcular_payslips(
    payload: RecalcularPayslipRequest,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    """Recalcula holerites de um período, atualizando gross/deductions/net.

    Diferentemente de /payroll/calculate (que processa TODOS os servidores),
    este endpoint:
    - aceita filtro por employee_id
    - usa taxa_deducao configurável (padrão 11%)
    - registra RecalcularPayslipLog com valores antes/depois
    - retorna variação de net por servidor
    """
    try:
        year, month = int(payload.periodo[:4]), int(payload.periodo[5:7])
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Período inválido; use YYYY-MM")

    if payload.taxa_deducao < 0 or payload.taxa_deducao > 100:
        raise HTTPException(status_code=422, detail="taxa_deducao deve estar entre 0 e 100")

    if payload.employee_id:
        if not db.get(Employee, payload.employee_id):
            raise HTTPException(status_code=404, detail="Servidor não encontrado")
        employees = [db.get(Employee, payload.employee_id)]
    else:
        employees = db.query(Employee).all()

    resultados = []
    for emp in employees:
        r = recalcular_payslip_servidor(
            db, emp.id, payload.periodo,
            taxa_deducao=payload.taxa_deducao,
            origem="manual",
            executado_por_id=current.id,
        )
        resultados.append(r)

    criados = sum(1 for r in resultados if r.get("status") == "criado")
    atualizados = sum(1 for r in resultados if r.get("status") == "atualizado")
    erros = sum(1 for r in resultados if r.get("status") == "erro")

    write_audit(db, user_id=current.id, action="update", entity="payslips",
                entity_id=payload.periodo,
                after_data={"periodo": payload.periodo, "criados": criados,
                            "atualizados": atualizados, "erros": erros})
    db.commit()

    return RecalcularPayslipOut(
        periodo=payload.periodo,
        total_criados=criados,
        total_atualizados=atualizados,
        total_erros=erros,
        resultados=resultados,
    )


@router.get("/payslips/recalcular/logs", response_model=None)
def list_recalcular_logs(
    employee_id: int | None = None,
    periodo: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr, RoleEnum.read_only)),
):
    """Lista logs de recálculo de holerite com filtros opcionais."""
    q = db.query(RecalcularPayslipLog)
    if employee_id:
        q = q.filter(RecalcularPayslipLog.employee_id == employee_id)
    if periodo:
        q = q.filter(RecalcularPayslipLog.periodo == periodo)
    total = q.count()
    items = q.order_by(RecalcularPayslipLog.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/payslips")
def list_payslips(
    month: str | None = None,
    employee_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr, RoleEnum.read_only)),
):
    q = db.query(Payslip)
    if month:
        q = q.filter(Payslip.month == month)
    if employee_id:
        q = q.filter(Payslip.employee_id == employee_id)
    total = q.count()
    items = q.order_by(Payslip.id.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


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
