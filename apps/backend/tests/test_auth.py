import os

os.environ["DATABASE_URL"] = "sqlite:///./test.db"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.seed import seed_data


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    db.close()


client = TestClient(app)


def test_login_and_refresh_flow():
    login = client.post("/auth/login", json={"username": "admin1", "password": "demo123"})
    assert login.status_code == 200
    tokens = login.json()
    assert tokens["access_token"]
    refresh = client.post("/auth/refresh", json={"refresh_token": tokens["refresh_token"]})
    assert refresh.status_code == 200


def test_public_transparency_listing():
    response = client.get("/public/commitments?page=1&size=5")
    assert response.status_code == 200
    assert response.json()["total"] >= 12


def test_phase2_admin_workflow_end_to_end():
    login = client.post("/auth/login", json={"username": "admin1", "password": "demo123"})
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

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

    audit = client.get("/core/audit-logs?page=1&size=50", headers=headers)
    assert audit.status_code == 200
    entities = [row["entity"] for row in audit.json()["items"]]
    assert "departments" in entities
    assert "vendors" in entities
    assert "budget_allocations" in entities
    assert "commitments" in entities
    assert "payments" in entities
