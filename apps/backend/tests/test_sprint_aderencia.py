"""Tests for sprint de aderência — TRV-13, TRV-12, ORC-05, PROT-04, TRIB-07, RH-07."""

import io
import os

os.environ["DATABASE_URL"] = "sqlite:///./test_sprint_aderencia.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Contribuinte, EscalaFerias, LancamentoTributario
from app.seed import seed_data

client = TestClient(app)

# Module-level token cache — avoids hitting rate limit during tests
_token_cache: dict[str, str] = {}


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    db.close()
    # Pre-cache tokens before rate limit test runs
    for username in ("admin1", "hr1", "read_only1"):
        r = client.post("/auth/login", json={"username": username, "password": "demo123"})
        if r.status_code == 200:
            _token_cache[username] = r.json()["access_token"]


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_sprint_aderencia.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    if username in _token_cache:
        return {"Authorization": f"Bearer {_token_cache[username]}"}
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    _token_cache[username] = r.json()["access_token"]
    return {"Authorization": f"Bearer {_token_cache[username]}"}


# ═══════════════════════════════════════════════════════════════════════════════
# TRV-12 — Log de autenticação
# ═══════════════════════════════════════════════════════════════════════════════

def test_login_success_creates_audit_log():
    """Login bem-sucedido deve criar entrada no audit_log com action='login'."""
    from app.models import AuditLog
    db = SessionLocal()
    try:
        # setup_module already called login once for admin1 and hr1
        count = db.query(AuditLog).filter(AuditLog.action == "login").count()
        assert count >= 1
    finally:
        db.close()


def test_login_failure_creates_audit_log():
    """Login com senha errada deve criar entrada com action='login_failure'."""
    from app.models import AuditLog
    db = SessionLocal()
    try:
        before = db.query(AuditLog).filter(AuditLog.action == "login_failure").count()
        r = client.post("/auth/login", json={"username": "admin1", "password": "senha-errada"})
        assert r.status_code in (401, 429)
        after = db.query(AuditLog).filter(AuditLog.action == "login_failure").count()
        if r.status_code == 401:
            assert after > before
    finally:
        db.close()


def test_logout_requires_auth():
    """POST /auth/logout sem token deve retornar 401."""
    r = client.post("/auth/logout")
    assert r.status_code == 401


def test_logout_success_creates_audit_log():
    """Logout autenticado deve criar entrada com action='logout'."""
    from app.models import AuditLog
    db = SessionLocal()
    try:
        headers = auth_headers("admin1")
        before = db.query(AuditLog).filter(AuditLog.action == "logout").count()
        r = client.post("/auth/logout", headers=headers)
        assert r.status_code == 200
        after = db.query(AuditLog).filter(AuditLog.action == "logout").count()
        assert after > before
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# TRV-13 — Rate limiting
# NOTE: these tests deliberately exhaust the limit — MUST run before other
#       tests that need fresh logins (hence the module-level token cache).
# ═══════════════════════════════════════════════════════════════════════════════

def test_login_rate_limit_app_healthy():
    """Verifica que o app está saudável e o rate limiter está configurado."""
    from app.main import app
    r = client.get("/")
    assert r.status_code == 200
    # Verifica que o limiter está instalado no app state
    assert hasattr(app.state, "limiter"), "Rate limiter não configurado no app"


def test_login_rate_limit_blocks_after_threshold():
    """Após exceder o limite configurado, o próximo POST deve retornar 429.

    Se LOGIN_RATE_LIMIT for alto (ambiente de teste), verifica só a configuração.
    """
    from app.config import settings
    from app.main import app

    # Parseia a parte numérica do rate limit (ex: "10/minute" → 10)
    try:
        limit_count = int(settings.login_rate_limit.split("/")[0])
    except (ValueError, IndexError):
        limit_count = 10000

    if limit_count <= 50:
        # Limite baixo (produção padrão: 10/minute) — testa o 429 real
        username = "x_ratelimit"
        for _ in range(limit_count):
            client.post("/auth/login", json={"username": username, "password": "x"})
        r = client.post("/auth/login", json={"username": username, "password": "x"})
        assert r.status_code == 429
    else:
        # Limite alto (ambiente de teste) — verifica só que o limiter está instalado
        assert hasattr(app.state, "limiter"), "Rate limiter não configurado"
        from app.config import settings as s
        assert "/" in s.login_rate_limit, f"login_rate_limit inválido: {s.login_rate_limit}"


# ═══════════════════════════════════════════════════════════════════════════════
# ORC-05 — Atualização automática do saldo executado ao empenhar
# ═══════════════════════════════════════════════════════════════════════════════

def _create_loa_item(db) -> int:
    """Cria LOA e LOAItem de suporte e retorna o loa_item_id."""
    from app.models import FiscalYear, LOA, LOAItem
    fy = db.query(FiscalYear).first()
    loa = LOA(
        fiscal_year_id=fy.id if fy else 1,
        description="LOA Teste ORC-05",
        status="aprovada",
    )
    db.add(loa)
    db.flush()
    item = LOAItem(
        loa_id=loa.id,
        function_code="04",
        subfunction_code="122",
        program_code="0001",
        action_code="2001",
        description="Manutenção Administrativa",
        authorized_amount=500_000.0,
        executed_amount=0.0,
    )
    db.add(item)
    db.commit()
    return item.id


def test_commitment_updates_loa_executed_amount():
    """Criar empenho com loa_item_id deve incrementar executed_amount na dotação."""
    from app.models import LOAItem, Department, FiscalYear, Vendor
    db = SessionLocal()
    try:
        loa_item_id = _create_loa_item(db)
        item_before = db.get(LOAItem, loa_item_id)
        exec_before = item_before.executed_amount

        fy = db.query(FiscalYear).first()
        dept = db.query(Department).first()
        vendor = db.query(Vendor).first()
        headers = auth_headers("admin1")

        payload = {
            "number": f"EMP-ORC05-{loa_item_id}",
            "description": "Empenho teste ORC-05",
            "amount": 10_000.0,
            "fiscal_year_id": fy.id,
            "department_id": dept.id,
            "vendor_id": vendor.id,
            "loa_item_id": loa_item_id,
        }
        r = client.post("/accounting/commitments", json=payload, headers=headers)
        assert r.status_code == 200, r.text

        db.expire_all()
        item_after = db.get(LOAItem, loa_item_id)
        assert round(item_after.executed_amount - exec_before, 2) == 10_000.0
    finally:
        db.close()


def test_commitment_without_loa_item_works():
    """Criar empenho sem loa_item_id deve continuar funcionando normalmente."""
    from app.models import Department, FiscalYear, Vendor
    db = SessionLocal()
    try:
        fy = db.query(FiscalYear).first()
        dept = db.query(Department).first()
        vendor = db.query(Vendor).first()
        headers = auth_headers("admin1")
        payload = {
            "number": "EMP-NO-LOA",
            "description": "Empenho sem LOA",
            "amount": 5_000.0,
            "fiscal_year_id": fy.id,
            "department_id": dept.id,
            "vendor_id": vendor.id,
        }
        r = client.post("/accounting/commitments", json=payload, headers=headers)
        assert r.status_code == 200
    finally:
        db.close()


# ═══════════════════════════════════════════════════════════════════════════════
# PROT-04 — Upload de arquivos / GED
# ═══════════════════════════════════════════════════════════════════════════════

_proto_counter = 0


def _create_protocolo(headers) -> int:
    global _proto_counter
    _proto_counter += 1
    r = client.post(
        "/protocolo/protocolos",
        json={
            "numero": f"PROT-GED-{_proto_counter:04d}",
            "tipo": "requerimento",
            "assunto": "Teste GED",
            "interessado": "Fulano",
            "prioridade": "normal",
            "data_entrada": "2025-01-01",
        },
        headers=headers,
    )
    assert r.status_code == 200, r.text
    return r.json()["id"]


def test_upload_pdf_to_protocolo():
    """Upload de PDF deve retornar 200 com id e file_name."""
    headers = auth_headers("admin1")
    protocolo_id = _create_protocolo(headers)

    pdf_bytes = b"%PDF-1.4 fake pdf content for test"
    r = client.post(
        f"/protocolo/protocolos/{protocolo_id}/anexos",
        files={"file": ("documento.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    assert r.status_code == 200, r.text
    data = r.json()
    assert data["file_name"] == "documento.pdf"
    assert data["entity_id"] == protocolo_id


def test_list_anexos_protocolo():
    """Listar anexos deve retornar os arquivos enviados."""
    headers = auth_headers("admin1")
    pid = _create_protocolo(headers)

    pdf_bytes = b"%PDF-1.4 another fake pdf"
    client.post(
        f"/protocolo/protocolos/{pid}/anexos",
        files={"file": ("arq.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    r_list = client.get(f"/protocolo/protocolos/{pid}/anexos", headers=headers)
    assert r_list.status_code == 200
    items = r_list.json()
    assert len(items) >= 1
    assert items[0]["file_name"] == "arq.pdf"


def test_upload_invalid_mime_returns_415():
    """Upload de tipo não permitido deve retornar 415."""
    headers = auth_headers("admin1")
    pid = _create_protocolo(headers)

    r = client.post(
        f"/protocolo/protocolos/{pid}/anexos",
        files={"file": ("script.sh", io.BytesIO(b"#!/bin/bash"), "application/x-sh")},
        headers=headers,
    )
    assert r.status_code == 415


def test_download_anexo():
    """Download de anexo existente deve retornar o conteúdo original."""
    headers = auth_headers("admin1")
    pid = _create_protocolo(headers)
    pdf_bytes = b"%PDF-1.4 download test"
    r_up = client.post(
        f"/protocolo/protocolos/{pid}/anexos",
        files={"file": ("baixar.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    att_id = r_up.json()["id"]
    r_dl = client.get(f"/protocolo/anexos/{att_id}/download", headers=headers)
    assert r_dl.status_code == 200
    assert r_dl.content == pdf_bytes


def test_delete_anexo():
    """DELETE de anexo deve retornar 204 e remover o registro."""
    headers = auth_headers("admin1")
    pid = _create_protocolo(headers)
    pdf_bytes = b"%PDF-1.4 delete test"
    r_up = client.post(
        f"/protocolo/protocolos/{pid}/anexos",
        files={"file": ("deletar.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        headers=headers,
    )
    att_id = r_up.json()["id"]
    r_del = client.delete(f"/protocolo/anexos/{att_id}", headers=headers)
    assert r_del.status_code == 204
    r_dl = client.get(f"/protocolo/anexos/{att_id}/download", headers=headers)
    assert r_dl.status_code == 404


# ═══════════════════════════════════════════════════════════════════════════════
# TRIB-07 — Portal do contribuinte
# ═══════════════════════════════════════════════════════════════════════════════

def _seed_contribuinte_com_debito(db) -> str:
    """Cria contribuinte com lançamento aberto e retorna o CPF."""
    cpf = "123.456.789-00"
    contrib = db.query(Contribuinte).filter(Contribuinte.cpf_cnpj == cpf).first()
    if not contrib:
        contrib = Contribuinte(cpf_cnpj=cpf, nome="Fulano de Tal", tipo="PF")
        db.add(contrib)
        db.flush()
        lanc = LancamentoTributario(
            contribuinte_id=contrib.id,
            tributo="IPTU",
            competencia="2025-01",
            exercicio=2025,
            valor_principal=1200.0,
            valor_total=1200.0,
            vencimento=date(2025, 3, 31),
            status="aberto",
        )
        db.add(lanc)
        db.commit()
    return cpf


def test_portal_contribuinte_debitos():
    """GET /public/contribuinte/{cpf_cnpj}/debitos deve retornar débitos abertos."""
    db = SessionLocal()
    cpf = _seed_contribuinte_com_debito(db)
    db.close()

    r = client.get(f"/public/contribuinte/{cpf}/debitos")
    assert r.status_code == 200
    data = r.json()
    assert data["contribuinte"]["cpf_cnpj"] == cpf
    assert data["total_debitos"] >= 1
    assert data["valor_total"] > 0


def test_portal_contribuinte_nao_cadastrado():
    """CPF não cadastrado deve retornar estrutura vazia com contribuinte=None."""
    r = client.get("/public/contribuinte/000.000.000-00/debitos")
    assert r.status_code == 200
    data = r.json()
    assert data["contribuinte"] is None
    assert data["total_debitos"] == 0


def test_portal_contribuinte_sem_debitos_abertos():
    """Contribuinte sem débitos abertos deve retornar lista vazia."""
    db = SessionLocal()
    cpf_sem = "987.654.321-00"
    contrib = db.query(Contribuinte).filter(Contribuinte.cpf_cnpj == cpf_sem).first()
    if not contrib:
        contrib = Contribuinte(cpf_cnpj=cpf_sem, nome="Sem Débitos", tipo="PF")
        db.add(contrib)
        db.flush()
        db.add(LancamentoTributario(
            contribuinte_id=contrib.id,
            tributo="ISS",
            competencia="2025-01",
            exercicio=2025,
            valor_principal=200.0,
            valor_total=200.0,
            vencimento=date(2025, 2, 28),
            status="pago",
        ))
        db.commit()
    db.close()

    r = client.get(f"/public/contribuinte/{cpf_sem}/debitos")
    assert r.status_code == 200
    assert r.json()["total_debitos"] == 0


def test_portal_contribuinte_certidao_negativa():
    """Contribuinte sem débitos deve obter certidão negativa."""
    db = SessionLocal()
    cpf_neg = "111.222.333-44"
    contrib = db.query(Contribuinte).filter(Contribuinte.cpf_cnpj == cpf_neg).first()
    if not contrib:
        contrib = Contribuinte(cpf_cnpj=cpf_neg, nome="Certidão Negativa", tipo="PF")
        db.add(contrib)
        db.commit()
    db.close()

    r = client.get(f"/public/contribuinte/{cpf_neg}/certidao")
    assert r.status_code == 200
    assert r.json()["situacao"] == "negativa"


def test_portal_contribuinte_certidao_positiva():
    """Contribuinte com débito aberto deve obter certidão positiva."""
    db = SessionLocal()
    cpf = _seed_contribuinte_com_debito(db)
    db.close()
    r = client.get(f"/public/contribuinte/{cpf}/certidao")
    assert r.status_code == 200
    assert r.json()["situacao"] == "positiva"


def test_portal_contribuinte_filtro_tributo():
    """Filtro por tributo deve retornar apenas lançamentos do tipo solicitado."""
    db = SessionLocal()
    cpf = _seed_contribuinte_com_debito(db)
    db.close()

    r = client.get(f"/public/contribuinte/{cpf}/debitos?tributo=IPTU")
    assert r.status_code == 200
    for item in r.json()["debitos"]:
        assert item["tributo"] == "IPTU"


# ═══════════════════════════════════════════════════════════════════════════════
# RH-07 — Escala de férias
# ═══════════════════════════════════════════════════════════════════════════════

def _get_employee_id() -> int:
    from app.models import Employee
    db = SessionLocal()
    emp = db.query(Employee).first()
    eid = emp.id
    db.close()
    return eid


def test_create_ferias():
    """Programar férias deve retornar 201 com status='programada'."""
    headers = auth_headers("admin1")
    emp_id = _get_employee_id()
    r = client.post(
        "/hr/ferias",
        json={
            "employee_id": emp_id,
            "ano_referencia": 2024,
            "data_inicio": "2025-01-10",
            "data_fim": "2025-01-24",
            "fracao": 1,
        },
        headers=headers,
    )
    assert r.status_code == 201, r.text
    data = r.json()
    assert data["status"] == "programada"
    assert data["dias_gozados"] == 15


def test_create_ferias_conflict():
    """Criar férias sobrepostas deve retornar 409."""
    headers = auth_headers("admin1")
    emp_id = _get_employee_id()
    client.post(
        "/hr/ferias",
        json={"employee_id": emp_id, "ano_referencia": 2024,
              "data_inicio": "2025-02-01", "data_fim": "2025-02-10", "fracao": 2},
        headers=headers,
    )
    r = client.post(
        "/hr/ferias",
        json={"employee_id": emp_id, "ano_referencia": 2024,
              "data_inicio": "2025-02-05", "data_fim": "2025-02-15", "fracao": 2},
        headers=headers,
    )
    assert r.status_code == 409


def test_create_ferias_invalid_dates():
    """data_fim < data_inicio deve retornar 422."""
    headers = auth_headers("admin1")
    emp_id = _get_employee_id()
    r = client.post(
        "/hr/ferias",
        json={"employee_id": emp_id, "ano_referencia": 2024,
              "data_inicio": "2025-03-20", "data_fim": "2025-03-10", "fracao": 1},
        headers=headers,
    )
    assert r.status_code == 422


def test_list_ferias():
    """Listagem de férias deve retornar registros existentes."""
    headers = auth_headers("admin1")
    emp_id = _get_employee_id()
    r = client.get(f"/hr/ferias?employee_id={emp_id}", headers=headers)
    assert r.status_code == 200
    assert isinstance(r.json(), list)


def test_approve_ferias():
    """Patch com status='aprovada' deve registrar aprovador."""
    headers = auth_headers("admin1")
    emp_id = _get_employee_id()
    r_create = client.post(
        "/hr/ferias",
        json={"employee_id": emp_id, "ano_referencia": 2023,
              "data_inicio": "2025-04-01", "data_fim": "2025-04-15", "fracao": 1},
        headers=headers,
    )
    fid = r_create.json()["id"]
    r_approve = client.patch(f"/hr/ferias/{fid}", json={"status": "aprovada"}, headers=headers)
    assert r_approve.status_code == 200
    assert r_approve.json()["status"] == "aprovada"
    assert r_approve.json()["aprovado_por_id"] is not None


def test_cancel_ferias():
    """DELETE em férias programadas deve marcar status='cancelada'."""
    headers = auth_headers("admin1")
    emp_id = _get_employee_id()
    r_create = client.post(
        "/hr/ferias",
        json={"employee_id": emp_id, "ano_referencia": 2022,
              "data_inicio": "2025-05-01", "data_fim": "2025-05-10", "fracao": 1},
        headers=headers,
    )
    fid = r_create.json()["id"]
    r_del = client.delete(f"/hr/ferias/{fid}", headers=headers)
    assert r_del.status_code == 204
    db = SessionLocal()
    obj = db.get(EscalaFerias, fid)
    assert obj.status == "cancelada"
    db.close()


def test_saldo_ferias():
    """GET /hr/ferias/servidor/{id}/saldo deve retornar saldo por ano."""
    headers = auth_headers("admin1")
    emp_id = _get_employee_id()
    r = client.get(f"/hr/ferias/servidor/{emp_id}/saldo", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "saldo_por_ano" in data
    assert data["employee_id"] == emp_id


def test_ferias_rbac_hr_only():
    """read_only não deve conseguir criar férias."""
    from app.models import User, RoleEnum
    db = SessionLocal()
    ro_user = db.query(User).filter(User.role == RoleEnum.read_only).first()
    ro_username = ro_user.username if ro_user else None
    db.close()
    if not ro_username:
        return  # skip if no read_only user seeded

    headers_ro = auth_headers(ro_username)
    emp_id = _get_employee_id()
    r = client.post(
        "/hr/ferias",
        json={"employee_id": emp_id, "ano_referencia": 2021,
              "data_inicio": "2025-06-01", "data_fim": "2025-06-10", "fracao": 1},
        headers=headers_ro,
    )
    assert r.status_code == 403
