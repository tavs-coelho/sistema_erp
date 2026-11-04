"""Administrative task workflow, state transitions and role/tenant boundaries."""
from datetime import date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app.deps import get_tenant_id
from app.main import app
from app.models import AuditLog, MunicipalTask, Protocolo, RoleEnum, TenantBranding, User
from app.security import create_access_token, hash_password


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as db:
        db.add_all([
            TenantBranding(id=1, org_name="Cidade A"), TenantBranding(id=2, org_name="Cidade B"),
            User(id=301, username="task-admin-a", full_name="Admin", email="task301@example.org",
                 hashed_password=hash_password("test"), tenant_id=1, role=RoleEnum.admin),
            User(id=302, username="task-employee-a", full_name="Responsável", email="task302@example.org",
                 hashed_password=hash_password("test"), tenant_id=1, role=RoleEnum.employee),
            User(id=303, username="task-admin-b", full_name="Outro Admin", email="task303@example.org",
                 hashed_password=hash_password("test"), tenant_id=2, role=RoleEnum.admin),
            User(id=304, username="task-reader-a", full_name="Leitor", email="task304@example.org",
                 hashed_password=hash_password("test"), tenant_id=1, role=RoleEnum.read_only),
        ])
        db.add_all([
            Protocolo(id=501, tenant_id=1, numero="TASK-A", tipo="requerimento",
                      assunto="Registro A", interessado="Público fictício", data_entrada=date(2026, 11, 3)),
            Protocolo(id=502, tenant_id=2, numero="TASK-B", tipo="requerimento",
                      assunto="Registro B", interessado="Público fictício", data_entrada=date(2026, 11, 3)),
            Protocolo(id=503, tenant_id=1, numero="TASK-ARCHIVED", tipo="requerimento",
                      assunto="Arquivado", interessado="Público fictício", status="arquivado",
                      data_entrada=date(2026, 11, 3)),
        ])
        db.commit()
    def dep():
        with maker() as db:
            yield db
    app.dependency_overrides[get_db] = dep
    app.dependency_overrides[get_tenant_id] = lambda: 1
    client = TestClient(app)
    try:
        yield client, maker, lambda tenant: app.dependency_overrides.__setitem__(get_tenant_id, lambda: tenant)
    finally:
        client.close()
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_tenant_id, None)
        engine.dispose()


def auth(uid, role="admin"):
    return {"Authorization": f"Bearer {create_access_token(uid, role)}"}


def test_create_assign_complete_and_audit(env):
    client, maker, _ = env
    created = client.post("/nucleo/tarefas", headers=auth(301), json={
        "protocol_id": 501, "title": "Analisar processo",
        "assigned_user_id": 302, "due_date": "2026-11-15", "priority": "urgente",
    })
    assert created.status_code == 201, created.text
    task = created.json()
    assert task["status"] == "aberta" and task["due_date"] == "2026-11-15"
    assert len(client.get("/nucleo/tarefas", headers=auth(302, "employee")).json()) == 1
    changed = client.patch(f"/nucleo/tarefas/{task['id']}/status", headers=auth(302, "employee"),
                           json={"status": "em_andamento"})
    assert changed.status_code == 200, changed.text
    done = client.patch(f"/nucleo/tarefas/{task['id']}/status", headers=auth(302, "employee"),
                        json={"status": "concluida"})
    assert done.status_code == 200 and done.json()["completed_at"] is not None
    assert client.patch(f"/nucleo/tarefas/{task['id']}/status", headers=auth(301),
                        json={"status": "cancelada"}).status_code == 409
    with maker() as db:
        assert db.query(AuditLog).filter(AuditLog.entity == "municipal_tasks").count() == 3


def test_tenant_idor_read_only_and_invalid_protocol(env):
    client, _, switch = env
    assert client.post("/nucleo/tarefas", headers=auth(301), json={
        "protocol_id": 502, "title": "Invasão"}).status_code == 404
    assert client.post("/nucleo/tarefas", headers=auth(301), json={
        "protocol_id": 503, "title": "Não pode abrir"}).status_code == 409
    assert client.post("/nucleo/tarefas", headers=auth(301), json={
        "protocol_id": 501, "title": "Vínculo ilegal", "assigned_user_id": 303}).status_code == 404
    created = client.post("/nucleo/tarefas", headers=auth(301), json={
        "protocol_id": 501, "title": "Tarefa legítima", "assigned_user_id": 302}).json()
    tid = created["id"]
    assert client.post("/nucleo/tarefas", headers=auth(304, "read_only"), json={
        "protocol_id": 501, "title": "Falha"}).status_code == 403
    assert client.get(f"/nucleo/tarefas/{tid}", headers=auth(304, "read_only")).status_code == 404
    switch(2)
    assert client.get("/nucleo/tarefas", headers=auth(303)).json() == []
    assert client.get(f"/nucleo/tarefas/{tid}", headers=auth(303)).status_code == 404
    assert client.patch(f"/nucleo/tarefas/{tid}/status", headers=auth(303),
                        json={"status": "concluida"}).status_code == 404
