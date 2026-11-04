"""Tenant-restricted and role-restricted municipal people directory tests."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.models import AuditLog, MunicipalParty, RoleEnum, TenantBranding, User
from app.security import create_access_token, hash_password


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([
            TenantBranding(id=1, org_name="Município A"),
            TenantBranding(id=2, org_name="Município B"),
            User(id=41, username="party-admin-a", full_name="A", email="a@demo.invalid",
                 hashed_password=hash_password("test"), role=RoleEnum.admin, tenant_id=1),
            User(id=42, username="party-admin-b", full_name="B", email="b@demo.invalid",
                 hashed_password=hash_password("test"), role=RoleEnum.admin, tenant_id=2),
            User(id=43, username="party-reader-b", full_name="C", email="c@demo.invalid",
                 hashed_password=hash_password("test"), role=RoleEnum.read_only, tenant_id=2),
        ])
        db.commit()
    def dep():
        with factory() as db:
            yield db
    app.dependency_overrides[get_db] = dep
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)
    try:
        yield client, factory, lambda tenant: app.dependency_overrides.__setitem__(get_tenant_id, lambda: tenant)
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def auth(uid, role="admin"):
    return {"Authorization": f"Bearer {create_access_token(uid, role)}"}


def test_supplier_create_update_duplicate_and_audit_minimization(env):
    client, factory, _ = env
    data = {"kind": "fornecedor", "name": "Fornecedor teste", "document": "12.345.678/0001-90",
            "email": "fornecedor@example.org"}
    result = client.post("/nucleo/pessoas", json=data, headers=auth(41))
    assert result.status_code == 201, result.text
    key = result.json()["id"]
    assert result.json()["document"] == "12345678000190"
    assert client.post("/nucleo/pessoas", json=data, headers=auth(41)).status_code == 409
    assert len(client.get("/nucleo/pessoas?kind=fornecedor", headers=auth(41)).json()) == 1
    assert client.patch(f"/nucleo/pessoas/{key}", json={"name": "Novo nome", "active": False},
                        headers=auth(41)).status_code == 200
    with factory() as db:
        logs = db.query(AuditLog).filter(AuditLog.entity == "municipal_parties").all()
        assert len(logs) == 2
        assert all("12345678000190" not in str(log.after_data) for log in logs)


def test_cross_tenant_idor_and_read_only_rejected(env):
    client, _, switch = env
    created = client.post("/nucleo/pessoas", json={"kind": "pessoa", "name": "Pessoa teste", "document": "12345678901"},
                          headers=auth(41))
    assert created.status_code == 201
    key = created.json()["id"]
    switch(2)
    assert client.get("/nucleo/pessoas", headers=auth(42)).json() == []
    assert client.get(f"/nucleo/pessoas/{key}", headers=auth(42)).status_code == 404
    assert client.patch(f"/nucleo/pessoas/{key}", json={"name": "Invasor"}, headers=auth(42)).status_code == 404
    assert client.get("/nucleo/pessoas", headers=auth(43, "read_only")).status_code == 403
    assert client.post("/nucleo/pessoas", headers=auth(42),
                       json={"kind": "pessoa", "name": "Outro", "document": "12345678901"}).status_code == 201
