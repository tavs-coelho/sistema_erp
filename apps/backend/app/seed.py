from datetime import date, timedelta

from sqlalchemy.orm import Session

from .models import (
    Asset,
    BudgetAllocation,
    Commitment,
    Contract,
    Department,
    Employee,
    FiscalYear,
    FundingSource,
    Municipality,
    Payment,
    ProcurementProcess,
    RoleEnum,
    User,
    Vendor,
)
from .security import hash_password


def seed_data(db: Session):
    if db.query(User).first():
        return

    db.add(Municipality(name="Município de Vila Esperança"))

    departments = [
        Department(name="Saúde"),
        Department(name="Educação"),
        Department(name="Administração"),
        Department(name="Obras"),
        Department(name="Assistência Social"),
    ]
    db.add_all(departments)
    db.flush()

    fy = FiscalYear(year=2026, active=True)
    db.add(fy)
    db.flush()

    employees = []
    for i in range(1, 21):
        employees.append(
            Employee(
                name=f"Servidor {i}",
                cpf=f"000.000.000-{i:02d}",
                job_title=["Analista", "Técnico", "Assistente"][i % 3],
                employment_type="Efetivo" if i % 2 == 0 else "Comissionado",
                base_salary=2500 + i * 120,
                department_id=departments[i % 5].id,
            )
        )
    db.add_all(employees)
    db.flush()

    roles = [
        RoleEnum.admin,
        RoleEnum.accountant,
        RoleEnum.hr,
        RoleEnum.procurement,
        RoleEnum.patrimony,
        RoleEnum.employee,
        RoleEnum.read_only,
    ]
    users = []
    for role in roles:
        for idx in range(1, 4):
            users.append(
                User(
                    username=f"{role.value}{idx}",
                    full_name=f"{role.value.title()} {idx}",
                    email=f"{role.value}{idx}@demo.local",
                    role=role,
                    hashed_password=hash_password("demo123"),
                    must_change_password=(idx == 1),
                    employee_id=employees[idx - 1].id if role == RoleEnum.employee else None,
                )
            )
    db.add_all(users)

    vendors = [Vendor(name=f"Fornecedor {i}", document=f"12.345.678/000{i:02d}") for i in range(1, 16)]
    db.add_all(vendors)
    db.flush()

    db.add_all(
        [
            BudgetAllocation(code=f"BA-{i:03d}", description=f"Dotação {i}", amount=50000 + i * 3000, fiscal_year_id=fy.id)
            for i in range(1, 6)
        ]
    )
    db.add_all([FundingSource(code=f"FS-{i:02d}", name=f"Fonte {i}") for i in range(1, 4)])

    commitments = []
    for i in range(1, 13):
        commitments.append(
            Commitment(
                number=f"EMP-2026-{i:03d}",
                description=f"Empenho de serviço {i}",
                amount=3000 + i * 700,
                fiscal_year_id=fy.id,
                department_id=departments[i % 5].id,
                vendor_id=vendors[i % 15].id,
                status="pago" if i <= 10 else "empenhado",
            )
        )
    db.add_all(commitments)
    db.flush()

    db.add_all(
        [
            Payment(
                commitment_id=commitments[i - 1].id,
                amount=commitments[i - 1].amount,
                payment_date=date.today() - timedelta(days=i * 3),
            )
            for i in range(1, 11)
        ]
    )

    processes = [ProcurementProcess(number=f"PROC-2026-{i:03d}", object_description=f"Processo licitatório {i}", status="homologado") for i in range(1, 9)]
    db.add_all(processes)
    db.flush()

    db.add_all(
        [
            Contract(
                number=f"CT-2026-{i:03d}",
                process_id=processes[i - 1].id,
                vendor_id=vendors[i % 15].id,
                start_date=date(2026, 1, 1) + timedelta(days=i * 5),
                end_date=date(2026, 12, 31) - timedelta(days=i * 10),
                amount=12000 + i * 2500,
                status="vigente" if i < 7 else "encerrado",
            )
            for i in range(1, 9)
        ]
    )

    db.add_all(
        [
            Asset(
                tag=f"PAT-{i:04d}",
                description=f"Bem patrimonial {i}",
                classification=["Mobiliário", "Informática", "Veículo"][i % 3],
                location=f"Sala {i%10 + 1}",
                department_id=departments[i % 5].id,
                responsible_employee_id=employees[i % 20].id,
                value=1000 + i * 250,
                status="ativo",
            )
            for i in range(1, 31)
        ]
    )

    db.commit()
