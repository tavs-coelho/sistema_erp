"""Finance setup is operational (not just a demo screen)."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.models import AuditLog, RoleEnum, TenantBranding, User
from app.security import create_access_token, hash_password


@pytest.fixture
def client_db():
    engine = create_engine("sqlite://", poolclass=StaticPool, connect_args={"check_same_thread": False})
    Base.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker() as db:
        db.add(TenantBranding(id=1, org_name="Teste ERP", subdomain="test-erp"))
        db.add(User(
            id=99, username="financial-admin", full_name="Admin",
            email="finance@example.org", role=RoleEnum.admin,
            hashed_password=hash_password("password-long-test"),
            active=True, tenant_id=1, session_version=0,
        ))
        db.add(User(
            id=100, username="read-only", full_name="Read Only",
            email="read@example.org", role=RoleEnum.read_only,
            hashed_password=hash_password("password-long-test"),
            active=True, tenant_id=1, session_version=0,
        ))
        db.commit()

    def override_db():
        with maker() as db:
            yield db

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)
    try:
        yield client, maker
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def bearer(user_id, role):
    return {"Authorization": "Bearer " + create_access_token(user_id, role)}


def test_create_list_duplicate_and_audit_fiscal_year(client_db):
    client, maker = client_db
    access = bearer(99, "admin")
    created = client.post("/core/fiscal-years", json={"year": 2034}, headers=access)
    assert created.status_code == 201, created.text
    assert created.json()["year"] == 2034 and created.json()["active"] is True
    assert client.post("/core/fiscal-years", json={"year": 2034}, headers=access).status_code == 409
    listed = client.get("/core/fiscal-years", headers=access)
    assert listed.status_code == 200
    assert any(x["id"] == created.json()["id"] for x in listed.json())
    with maker() as db:
        audit = db.query(AuditLog).filter(AuditLog.entity == "fiscal_years").first()
        assert audit is not None and audit.action == "create"


def test_fiscal_year_requires_authorization_and_valid_year(client_db):
    client, _ = client_db
    assert client.post("/core/fiscal-years", json={"year": 2034}).status_code == 401
    assert client.post("/core/fiscal-years", json={"year": 2034},
                       headers=bearer(100, "read_only")).status_code == 403
    assert client.post("/core/fiscal-years", json={"year": 1800},
                       headers=bearer(99, "admin")).status_code == 422
