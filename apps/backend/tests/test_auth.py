import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import AssetMovement, Liquidation, Payslip
from app.seed import seed_data


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    db.close()


client = TestClient(app)


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def test_login_and_refresh_flow():
    login = client.post("/auth/login", json={"username": "admin1", "password": "demo123"})
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"]
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200


def test_login_failure_returns_401():
    response = client.post("/auth/login", json={"username": "admin1", "password": "senha-invalida"})
    assert response.status_code == 401


def test_rbac_protects_admin_only_route():
    headers = auth_headers("hr1")
    response = client.post("/core/departments", json={"name": "Departamento Sem Permissão"}, headers=headers)
    assert response.status_code == 403


def test_public_transparency_listing():
    response = client.get("/public/commitments?page=1&size=5")
    assert response.status_code == 200
    assert response.json()["total"] >= 12


def test_phase2_admin_workflow_end_to_end():
    headers = auth_headers("admin1")

    dep = client.post("/core/departments", json={"name": "Planejamento Integrado"}, headers=headers)
    assert dep.status_code == 200
    department_id = dep.json()["id"]

    vendor = client.post(
        "/accounting/vendors",
        json={"name": "Fornecedor Fluxo E2E", "document": "55.444.333/0001-12"},
        headers=headers,
    )
    assert vendor.status_code == 200
    vendor_id = vendor.json()["id"]

    allocation = client.post(
        "/accounting/budget-allocations",
        json={"code": "BA-E2E-001", "description": "Dotação E2E", "amount": 150000, "fiscal_year_id": 1},
        headers=headers,
    )
    assert allocation.status_code == 200

    commitment = client.post(
        "/accounting/commitments",
        json={
            "number": "EMP-E2E-001",
            "description": "Empenho Fluxo E2E",
            "amount": 12000,
            "fiscal_year_id": 1,
            "department_id": department_id,
            "vendor_id": vendor_id,
        },
        headers=headers,
    )
    assert commitment.status_code == 200
    commitment_id = commitment.json()["id"]

    liquidate = client.post(f"/accounting/liquidate/{commitment_id}", headers=headers)
    assert liquidate.status_code == 200

    payment = client.post(
        "/accounting/payments",
        json={"commitment_id": commitment_id, "amount": 12000, "payment_date": "2026-04-19"},
        headers=headers,
    )
    assert payment.status_code == 200

    internal_list = client.get("/accounting/commitments?status=pago&page=1&size=10", headers=headers)
    assert internal_list.status_code == 200
    assert any(item["number"] == "EMP-E2E-001" for item in internal_list.json()["items"])

    public_list = client.get("/public/commitments?search=Fluxo E2E&page=1&size=10")
    assert public_list.status_code == 200
    assert public_list.json()["total"] >= 1

    db = SessionLocal()
    try:
        assert db.query(Liquidation).filter(Liquidation.commitment_id == commitment_id).count() == 1
    finally:
        db.close()

    audit = client.get("/core/audit-logs?page=1&size=50", headers=headers)
    assert audit.status_code == 200
    entities = [row["entity"] for row in audit.json()["items"]]
    assert "departments" in entities
    assert "vendors" in entities
    assert "budget_allocations" in entities
    assert "commitments" in entities
    assert "payments" in entities


def test_hr_employee_flow_payroll_and_payslip_pdf():
    hr_headers = auth_headers("hr1")

    employee = client.post(
        "/hr/employees",
        json={
            "name": "Servidor Fluxo RH",
            "cpf": "987.654.321-00",
            "job_title": "Analista de RH",
            "employment_type": "Efetivo",
            "base_salary": 5000,
            "department_id": 1,
        },
        headers=hr_headers,
    )
    assert employee.status_code == 200
    employee_id = employee.json()["id"]

    event = client.post(
        "/hr/payroll-events",
        json={
            "employee_id": employee_id,
            "month": "2026-04",
            "kind": "provento",
            "description": "Gratificação de teste",
            "value": 350,
        },
        headers=hr_headers,
    )
    assert event.status_code == 200

    payroll = client.post("/hr/payroll/calculate", json={"month": "2026-04"}, headers=hr_headers)
    assert payroll.status_code == 200

    events = client.get("/hr/payroll-events?month=2026-04&page=1&size=20", headers=hr_headers)
    assert events.status_code == 200
    assert any(row["employee_id"] == employee_id for row in events.json()["items"])

    employee_headers = auth_headers("employee1")
    my_payslips = client.get("/employee-portal/payslips", headers=employee_headers)
    assert my_payslips.status_code == 200
    assert len(my_payslips.json()) >= 1
    payslip_id = my_payslips.json()[0]["id"]

    pdf = client.get(f"/hr/payslips/{payslip_id}/pdf", headers=employee_headers)
    assert pdf.status_code == 200
    assert pdf.headers["content-type"] == "application/pdf"
    assert pdf.content.startswith(b"%PDF")

    db = SessionLocal()
    try:
        assert db.query(Payslip).filter(Payslip.month == "2026-04").count() >= 1
    finally:
        db.close()


def test_patrimony_transfer_creates_movement_history():
    headers = auth_headers("patrimony1")
    create = client.post(
        "/patrimony/assets",
        json={
            "tag": "PAT-E2E-9001",
            "description": "Notebook Patrimônio E2E",
            "classification": "Informática",
            "location": "Sala TI",
            "department_id": 1,
            "responsible_employee_id": 1,
            "value": 4500,
            "status": "ativo",
        },
        headers=headers,
    )
    assert create.status_code == 200
    asset_id = create.json()["id"]

    transfer = client.post(
        f"/patrimony/assets/{asset_id}/transfer",
        json={"to_department_id": 2, "new_location": "Sala Financeiro", "new_responsible_employee_id": 2},
        headers=headers,
    )
    assert transfer.status_code == 200

    movements = client.get(f"/patrimony/movements?asset_id={asset_id}&page=1&size=10", headers=headers)
    assert movements.status_code == 200
    assert movements.json()["total"] >= 1
    assert movements.json()["items"][0]["movement_type"] == "transferencia"

    report = client.get("/patrimony/reports/by-department?department_id=2", headers=headers)
    assert report.status_code == 200
    assert any(tag == "PAT-E2E-9001" for tags in report.json().values() for tag in tags)

    db = SessionLocal()
    try:
        assert db.query(AssetMovement).filter(AssetMovement.asset_id == asset_id).count() >= 1
    finally:
        db.close()
