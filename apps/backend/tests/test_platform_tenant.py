"""IDOR regression: two entities cannot see or mutate each other's protocols/uploads."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.models import Department, RoleEnum, TenantBranding, User
from app.security import create_access_token, hash_password


@pytest.fixture
def tenants(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "demo_mode", True)
    monkeypatch.setattr(settings, "upload_dir", str(tmp_path))
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False, autoflush=False)
    with maker() as db:
        db.add_all([
            TenantBranding(id=1, subdomain="cidade-a", org_name="Cidade A"),
            TenantBranding(id=2, subdomain="cidade-b", org_name="Cidade B"),
            Department(id=101, tenant_id=1, name="Administração"),
            Department(id=202, tenant_id=2, name="Administração"),
            User(id=101, tenant_id=1, username="a-admin", full_name="A Admin",
                 email="a@example.invalid", hashed_password=hash_password("a-password"),
                 role=RoleEnum.admin, active=True),
            User(id=202, tenant_id=2, username="b-admin", full_name="B Admin",
                 email="b@example.invalid", hashed_password=hash_password("b-password"),
                 role=RoleEnum.admin, active=True),
            User(id=203, tenant_id=2, username="b-reader", full_name="B Reader",
                 email="breader@example.invalid", hashed_password=hash_password("reader-password"),
                 role=RoleEnum.read_only, active=True),
        ])
        db.commit()
    def get_test_db():
        with maker() as db:
            yield db
    app.dependency_overrides[get_db] = get_test_db
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)
    try:
        def switch(tenant_id):
            app.dependency_overrides[get_tenant_id] = lambda: tenant_id
        yield client, switch
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def auth(user_id, role="admin"):
    return {"Authorization": f"Bearer {create_access_token(user_id, role)}"}


def create_protocol(client, header, department_id, number):
    return client.post("/protocolo/protocolos", headers=header, json={
        "numero": number, "tipo": "requerimento", "assunto": "Solicitação isolada",
        "interessado": "Pessoa fictícia", "data_entrada": "2026-11-03",
        "origem_department_id": department_id,
        "destino_department_id": department_id,
    })


def test_departments_same_name_are_scoped_per_tenant(tenants):
    client, switch = tenants
    first = client.get("/core/departments", headers=auth(101))
    assert first.status_code == 200
    assert [d["id"] for d in first.json()] == [101]
    switch(2)
    second = client.get("/core/departments", headers=auth(202))
    assert second.status_code == 200
    assert [d["id"] for d in second.json()] == [202]
    assert client.patch("/core/departments/101", headers=auth(202), json={"active": False}).status_code == 404
    assert client.post("/core/departments", headers=auth(202), json={"name": "Administração"}).status_code == 409
    assert client.post("/core/departments", headers=auth(202), json={"name": "Saúde"}).status_code == 200


def test_protocol_idor_list_detail_status_update_tramitation_and_uploads(tenants):
    client, switch = tenants
    one = create_protocol(client, auth(101), 101, "A-ONLY-001")
    assert one.status_code == 200, one.text
    one_id = one.json()["id"]
    uploaded = client.post(
        f"/protocolo/protocolos/{one_id}/anexos", headers=auth(101),
        files={"file": ("anexo.txt", b"not confidential mock", "text/plain")},
    )
    assert uploaded.status_code == 200, uploaded.text
    attachment_id = uploaded.json()["id"]

    switch(2)
    two = create_protocol(client, auth(202), 202, "B-ONLY-001")
    assert two.status_code == 200, two.text
    q = client.get("/protocolo/protocolos", headers=auth(202))
    assert q.status_code == 200 and q.json()["total"] == 1
    assert q.json()["items"][0]["id"] == two.json()["id"]
    assert client.get(f"/protocolo/protocolos/{one_id}", headers=auth(202)).status_code == 404
    assert client.patch(f"/protocolo/protocolos/{one_id}", headers=auth(202), json={"assunto": "MUTATION"}).status_code == 404
    assert client.post(f"/protocolo/protocolos/{one_id}/tramitar", headers=auth(202), json={
        "para_department_id": 202, "acao": "encaminhado",
    }).status_code == 404
    assert client.get(f"/protocolo/protocolos/{one_id}/tramitacoes", headers=auth(202)).status_code == 404
    assert client.get(f"/protocolo/protocolos/{one_id}/anexos", headers=auth(202)).status_code == 404
    assert client.post(f"/protocolo/protocolos/{one_id}/anexos", headers=auth(202),
                       files={"file": ("bad.txt", b"bad", "text/plain")}).status_code == 404
    assert client.get(f"/protocolo/anexos/{attachment_id}/download", headers=auth(202)).status_code == 404
    assert client.delete(f"/protocolo/anexos/{attachment_id}", headers=auth(202)).status_code == 404
    assert client.get("/protocolo/estatisticas", headers=auth(202)).json() == {"protocolado": 1}
    switch(1)
    assert client.get(f"/protocolo/anexos/{attachment_id}/download", headers=auth(101)).status_code == 200


def test_cross_entity_department_fk_and_read_only_rbac(tenants):
    client, switch = tenants
    assert create_protocol(client, auth(101), 202, "INVALID-DEPT").status_code == 404
    protocol = create_protocol(client, auth(101), 101, "OWN-001")
    pid = protocol.json()["id"]
    assert client.patch(f"/protocolo/protocolos/{pid}", headers=auth(101), json={
        "destino_department_id": 202,
    }).status_code == 404
    assert client.post(f"/protocolo/protocolos/{pid}/tramitar", headers=auth(101), json={
        "para_department_id": 202, "acao": "encaminhado",
    }).status_code == 404
    switch(2)
    assert create_protocol(client, auth(203, "read_only"), 202, "FORBIDDEN").status_code == 403
    assert client.post("/core/attachments?entity_type=protocolo&entity_id=1",
                       headers=auth(203, "read_only"),
                       files={"file": ("wrong.txt", b"bad", "text/plain")}).status_code == 403
