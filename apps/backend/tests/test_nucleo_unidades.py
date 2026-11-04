"""End-to-end API contract for municipal units and tenant ownership."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.models import AuditLog, Department, MunicipalUnit, RoleEnum, TenantBranding, User
from app.security import create_access_token, hash_password


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)
    with maker() as db:
        db.add_all([
            TenantBranding(id=1, subdomain="one", org_name="Cidade 1"),
            TenantBranding(id=2, subdomain="two", org_name="Cidade 2"),
            Department(id=11, tenant_id=1, name="Saúde"),
            Department(id=22, tenant_id=2, name="Saúde"),
            User(id=11, username="nucleo-admin-1", full_name="Admin 1",
                 email="admin-nucleo1@example.org", hashed_password=hash_password("test-only"),
                 tenant_id=1, role=RoleEnum.admin, active=True),
            User(id=22, username="nucleo-admin-2", full_name="Admin 2",
                 email="admin-nucleo2@example.org", hashed_password=hash_password("test-only"),
                 tenant_id=2, role=RoleEnum.admin, active=True),
            User(id=23, username="nucleo-reader-2", full_name="Reader 2",
                 email="reader-nucleo2@example.org", hashed_password=hash_password("test-only"),
                 tenant_id=2, role=RoleEnum.read_only, active=True),
        ])
        db.commit()
    def override():
        with maker() as db:
            yield db
    app.dependency_overrides[get_db] = override
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)
    try:
        yield client, maker, lambda tenant: app.dependency_overrides.__setitem__(get_tenant_id, lambda: tenant)
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def bearer(user_id, role="admin"):
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def test_unit_creation_search_update_audit_and_duplicate(env):
    client, maker, _ = env
    payload = {"code": "UBS-001", "name": "Unidade Básica", "department_id": 11,
               "address": "Rua Central, 1"}
    created = client.post("/nucleo/unidades", json=payload, headers=bearer(11))
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["tenant_id"] == 1 and item["code"] == "UBS-001"
    assert client.post("/nucleo/unidades", json=payload, headers=bearer(11)).status_code == 409
    listed = client.get("/nucleo/unidades?search=UBS", headers=bearer(11))
    assert listed.status_code == 200 and len(listed.json()) == 1
    updated = client.patch(f"/nucleo/unidades/{item['id']}", json={"name": "UBS Centro", "active": False}, headers=bearer(11))
    assert updated.status_code == 200 and updated.json()["name"] == "UBS Centro"
    assert client.get("/nucleo/unidades?active=true", headers=bearer(11)).json() == []
    with maker() as db:
        assert db.query(AuditLog).filter(AuditLog.entity == "municipal_units").count() == 2


def test_units_cannot_cross_tenant_or_department_or_role(env):
    client, maker, switch = env
    assert client.post("/nucleo/unidades", json={"code": "BAD", "name": "Invasão", "department_id": 22},
                       headers=bearer(11)).status_code == 404
    one = client.post("/nucleo/unidades", json={"code": "U-01", "name": "Unidade A", "department_id": 11},
                      headers=bearer(11)).json()
    switch(2)
    assert client.get("/nucleo/unidades", headers=bearer(22)).json() == []
    assert client.get(f"/nucleo/unidades/{one['id']}", headers=bearer(22)).status_code == 404
    assert client.patch(f"/nucleo/unidades/{one['id']}", json={"name": "Alterada"}, headers=bearer(22)).status_code == 404
    assert client.post("/nucleo/unidades", json={"code": "U-01", "name": "Unidade B", "department_id": 22},
                       headers=bearer(22)).status_code == 201
    assert client.post("/nucleo/unidades", json={"code": "RO", "name": "Somente Leitura", "department_id": 22},
                       headers=bearer(23, "read_only")).status_code == 403
