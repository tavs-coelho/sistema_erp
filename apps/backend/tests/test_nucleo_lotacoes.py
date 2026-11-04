"""User-unit memberships cannot span tenants or elevate permissions."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.models import Department, MunicipalUnit, MunicipalAssignment, RoleEnum, TenantBranding, User
from app.security import create_access_token, hash_password


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    with factory() as db:
        db.add_all([
            TenantBranding(id=1, org_name="Cidade A"), TenantBranding(id=2, org_name="Cidade B"),
            Department(id=1, name="Saúde", tenant_id=1), Department(id=2, name="Saúde", tenant_id=2),
            MunicipalUnit(id=1, code="A", name="Centro A", tenant_id=1, department_id=1),
            MunicipalUnit(id=2, code="B", name="Centro B", tenant_id=2, department_id=2),
            User(id=81, username="admin-81", full_name="Admin A", email="u81@example.org",
                 hashed_password=hash_password("test"), role=RoleEnum.admin, tenant_id=1),
            User(id=82, username="admin-82", full_name="Admin B", email="u82@example.org",
                 hashed_password=hash_password("test"), role=RoleEnum.admin, tenant_id=2),
            User(id=83, username="reader-83", full_name="Leitor", email="u83@example.org",
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


def auth(id, role="admin"):
    return {"Authorization": f"Bearer {create_access_token(id, role)}"}


def test_assign_revoke_reactivate_and_list_mine(env):
    client, factory, _ = env
    p = {"user_id": 81, "unit_id": 1}
    result = client.post("/nucleo/lotacoes", json=p, headers=auth(81))
    assert result.status_code == 201, result.text
    key = result.json()["id"]
    assert client.post("/nucleo/lotacoes", json=p, headers=auth(81)).status_code == 409
    assert len(client.get("/nucleo/lotacoes/minhas", headers=auth(81)).json()) == 1
    assert client.delete(f"/nucleo/lotacoes/{key}", headers=auth(81)).status_code == 200
    assert client.get("/nucleo/lotacoes/minhas", headers=auth(81)).json() == []
    again = client.post("/nucleo/lotacoes", json=p, headers=auth(81))
    assert again.status_code == 201 and again.json()["id"] == key
    with factory() as db:
        assert db.query(MunicipalAssignment).count() == 1


def test_cross_tenant_users_units_and_permissions(env):
    client, _, switch = env
    for p in ({"user_id": 82, "unit_id": 1}, {"user_id": 81, "unit_id": 2}):
        assert client.post("/nucleo/lotacoes", json=p, headers=auth(81)).status_code == 404
    assigned = client.post("/nucleo/lotacoes", json={"user_id": 81, "unit_id": 1}, headers=auth(81)).json()
    switch(2)
    assert client.get("/nucleo/lotacoes", headers=auth(82)).json() == []
    assert client.delete(f"/nucleo/lotacoes/{assigned['id']}", headers=auth(82)).status_code == 404
    assert client.get("/nucleo/lotacoes", headers=auth(83, "read_only")).status_code == 403
    assert client.post("/nucleo/lotacoes", json={"user_id": 83, "unit_id": 2},
                       headers=auth(83, "read_only")).status_code == 403
