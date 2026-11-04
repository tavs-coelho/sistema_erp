"""Support and task notifications: isolation, authorization and useful FAQ."""
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
from app.models import MunicipalNotice, Protocolo, RoleEnum, TenantBranding, User
from app.security import create_access_token, hash_password


@pytest.fixture
def env(monkeypatch):
    monkeypatch.setattr(settings, "demo_mode", True)
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    with maker() as db:
        db.add_all([
            TenantBranding(id=1, org_name="Município A"),
            TenantBranding(id=2, org_name="Município B"),
            User(id=401, username="central-admin-a", full_name="Admin A", email="central401@example.org",
                 hashed_password=hash_password("test"), tenant_id=1, role=RoleEnum.admin),
            User(id=402, username="central-employee-a", full_name="Servidor A", email="central402@example.org",
                 hashed_password=hash_password("test"), tenant_id=1, role=RoleEnum.employee),
            User(id=403, username="central-admin-b", full_name="Admin B", email="central403@example.org",
                 hashed_password=hash_password("test"), tenant_id=2, role=RoleEnum.admin),
        ])
        db.add(Protocolo(id=601, tenant_id=1, numero="SUP-001", tipo="requerimento",
                         assunto="Processo", interessado="Teste", data_entrada=date(2026, 11, 3)))
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


def test_support_lifecycle_and_private_notifications(env):
    client, factory, _ = env
    created = client.post("/nucleo/central/tickets", headers=auth(402, "employee"), json={
        "subject": "Erro no protocolo", "description": "Falha fictícia de envio após autenticação.",
        "priority": "alta",
    })
    assert created.status_code == 201, created.text
    tid = created.json()["id"]
    inbox_admin = client.get("/nucleo/central/notificacoes?unread=true", headers=auth(401))
    assert inbox_admin.status_code == 200 and len(inbox_admin.json()) == 1
    notice_id = inbox_admin.json()[0]["id"]
    assert client.get("/nucleo/central/notificacoes", headers=auth(402, "employee")).json() == []
    assert client.patch(f"/nucleo/central/notificacoes/{notice_id}/ler",
                        headers=auth(402, "employee")).status_code == 404
    assert client.patch(f"/nucleo/central/notificacoes/{notice_id}/ler",
                        headers=auth(401)).status_code == 200
    assert client.get("/nucleo/central/notificacoes?unread=true", headers=auth(401)).json() == []
    reply = client.post(f"/nucleo/central/tickets/{tid}/respostas", headers=auth(401),
                        json={"message": "Chamado recebido e em análise"})
    assert reply.status_code == 201, reply.text
    assert len(client.get("/nucleo/central/notificacoes", headers=auth(402, "employee")).json()) == 1
    assert len(client.get(f"/nucleo/central/tickets/{tid}/respostas", headers=auth(402, "employee")).json()) == 1
    assert client.patch(f"/nucleo/central/tickets/{tid}/status", headers=auth(402, "employee"),
                        json={"status": "fechado"}).status_code == 403
    assert client.patch(f"/nucleo/central/tickets/{tid}/status", headers=auth(401),
                        json={"status": "fechado"}).status_code == 200
    assert client.post(f"/nucleo/central/tickets/{tid}/respostas", headers=auth(401),
                       json={"message": "Mensagem depois do encerramento"}).status_code == 409
    with factory() as db:
        assert db.query(MunicipalNotice).count() >= 2


def test_cross_tenant_support_idor_and_task_assignment_notifications(env):
    client, _, switch = env
    ticket = client.post("/nucleo/central/tickets", headers=auth(402, "employee"), json={
        "subject": "Dúvida institucional", "description": "Como posso solicitar auxílio ao departamento?",
    }).json()
    task = client.post("/nucleo/tarefas", headers=auth(401), json={
        "protocol_id": 601, "title": "Responder diligência", "assigned_user_id": 402,
    })
    assert task.status_code == 201, task.text
    notices = client.get("/nucleo/central/notificacoes", headers=auth(402, "employee")).json()
    assert any(n["kind"] == "tarefa" and n["reference_id"] == task.json()["id"] for n in notices)
    faq = client.get("/nucleo/central/faq", headers=auth(402, "employee"))
    assert faq.status_code == 200 and len(faq.json()) >= 18
    switch(2)
    assert client.get("/nucleo/central/tickets", headers=auth(403)).json() == []
    assert client.get(f"/nucleo/central/tickets/{ticket['id']}", headers=auth(403)).status_code == 404
    assert client.get(f"/nucleo/central/tickets/{ticket['id']}/respostas", headers=auth(403)).status_code == 404
    assert client.post(f"/nucleo/central/tickets/{ticket['id']}/respostas", headers=auth(403),
                       json={"message": "Tentativa indevida"}).status_code == 404
    assert client.get("/nucleo/central/notificacoes", headers=auth(403)).json() == []
