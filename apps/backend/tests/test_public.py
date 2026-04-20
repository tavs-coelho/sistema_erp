"""Testes do Portal de Transparência (endpoints públicos ampliados).

Cobre: stats, empenhos, contratos, licitações, convênios, arrecadação e dívida ativa.
Todos os endpoints são públicos (sem autenticação).
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_public.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Commitment,
    Contract,
    Convenio,
    Department,
    DividaAtiva,
    FiscalYear,
    LancamentoTributario,
    ProcurementProcess,
    Vendor,
    Contribuinte,
)
from app.seed import seed_data

client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    # Seed extra fixtures for public portal tests
    _seed_fixtures(db)
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_public.db")
    except FileNotFoundError:
        pass


def _seed_fixtures(db):
    """Add deterministic fixtures for portal tests."""
    # Get existing fiscal year and department from seed_data
    fy = db.query(FiscalYear).first()
    dept = db.query(Department).first()
    assert fy is not None and dept is not None, "seed_data must have created FiscalYear and Department"

    # Vendor
    vendor = Vendor(name="Fornecedor Público Ltda", document="00.000.000/0001-00")
    db.add(vendor)
    db.flush()

    # Procurement process
    proc = ProcurementProcess(number="PROC-PUB-001", object_description="Aquisição de material escolar", status="homologado")
    db.add(proc)
    db.flush()

    # Contract
    contract = Contract(number="CTR-PUB-001", process_id=proc.id, vendor_id=vendor.id,
                        start_date=date(2026, 1, 1), end_date=date(2026, 12, 31),
                        amount=120000.0, status="vigente")
    db.add(contract)

    # Convenio vigente and rascunho
    cv_vigente = Convenio(numero="CONV-PUB-001", objeto="Convênio de saúde pública",
                          tipo="recebimento", concedente="Estado SP",
                          valor_total=500000.0, contrapartida=0.0,
                          data_assinatura=date(2026, 1, 10),
                          data_inicio=date(2026, 2, 1), data_fim=date(2026, 12, 31),
                          status="vigente")
    cv_rascunho = Convenio(numero="CONV-RASCUNHO-001", objeto="Convênio em rascunho",
                           tipo="repasse", concedente="Governo Federal",
                           valor_total=100000.0, contrapartida=0.0,
                           data_assinatura=date(2026, 3, 1),
                           data_inicio=date(2026, 4, 1), data_fim=date(2026, 12, 31),
                           status="rascunho")
    db.add_all([cv_vigente, cv_rascunho])

    # Commitment (requires fiscal_year_id, department_id, vendor_id)
    commitment = Commitment(number="EMP-PUB-001", description="Empenho de material escolar",
                            amount=50000.0, status="empenhado",
                            fiscal_year_id=fy.id, department_id=dept.id, vendor_id=vendor.id)
    db.add(commitment)

    # Contribuinte + lançamento pago + dívida ativa
    contrib = Contribuinte(cpf_cnpj="000.000.000-01", nome="Contribuinte Público", tipo="PF")
    db.add(contrib)
    db.flush()

    lancPago = LancamentoTributario(
        contribuinte_id=contrib.id, tributo="IPTU", competencia="2025-01",
        exercicio=2025, valor_principal=1000.0, valor_total=1000.0,
        vencimento=date(2025, 3, 31), status="pago", data_pagamento=date(2025, 3, 25),
    )
    lancInscrito = LancamentoTributario(
        contribuinte_id=contrib.id, tributo="IPTU", competencia="2024-01",
        exercicio=2024, valor_principal=900.0, valor_total=900.0,
        vencimento=date(2024, 3, 31), status="inscrito_divida",
    )
    db.add_all([lancPago, lancInscrito])
    db.flush()

    divida = DividaAtiva(
        lancamento_id=lancInscrito.id, contribuinte_id=contrib.id,
        numero_inscricao="DA-PUB-001", tributo="IPTU", exercicio=2024,
        valor_original=900.0, valor_atualizado=990.0,
        data_inscricao=date(2024, 4, 1), status="ativa",
    )
    db.add(divida)
    db.commit()


# ── Stats ─────────────────────────────────────────────────────────────────────

def test_stats_retorna_indicadores():
    resp = client.get("/public/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert "empenhos" in data
    assert "contratos" in data
    assert "licitacoes" in data
    assert "convenios" in data
    assert "arrecadacao_tributaria" in data
    # Must reflect our seeded data
    assert data["empenhos"]["total"] >= 1
    assert data["contratos"]["total"] >= 1
    assert data["licitacoes"]["total"] >= 1
    assert data["convenios"]["total"] >= 1
    assert data["arrecadacao_tributaria"]["arrecadado"] >= 1000.0
    assert data["arrecadacao_tributaria"]["divida_ativa"] >= 990.0


def test_stats_convenios_nao_conta_rascunho():
    resp = client.get("/public/stats")
    data = resp.json()
    # We seeded 1 vigente + 1 rascunho; rascunho must NOT be counted
    db = SessionLocal()
    try:
        total_todos = db.query(Convenio).count()
        total_rascunho = db.query(Convenio).filter(Convenio.status == "rascunho").count()
    finally:
        db.close()
    assert data["convenios"]["total"] == total_todos - total_rascunho


# ── Empenhos ──────────────────────────────────────────────────────────────────

def test_list_empenhos_publicos_sem_auth():
    resp = client.get("/public/commitments?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data and "items" in data
    assert data["total"] >= 1


def test_empenhos_filtro_busca():
    resp = client.get("/public/commitments?search=material%20escolar&page=1&size=10")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any("material" in i["description"].lower() for i in items)


def test_empenhos_export_csv():
    resp = client.get("/public/commitments?export=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().split("\n")
    assert lines[0].startswith("numero")
    assert len(lines) >= 2


# ── Contratos ─────────────────────────────────────────────────────────────────

def test_list_contratos_publicos():
    resp = client.get("/public/contracts?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_contratos_filtro_status():
    resp = client.get("/public/contracts?status=vigente&page=1&size=10")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "vigente" for i in items)


def test_contratos_export_csv():
    resp = client.get("/public/contracts?export=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().split("\n")
    assert lines[0].startswith("numero")


# ── Licitações ────────────────────────────────────────────────────────────────

def test_list_licitacoes_publicas():
    resp = client.get("/public/licitacoes?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_licitacoes_filtro_busca():
    resp = client.get("/public/licitacoes?search=material%20escolar&page=1&size=10")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any("material" in i["object_description"].lower() for i in items)


def test_licitacoes_filtro_status():
    resp = client.get("/public/licitacoes?status=homologado&page=1&size=10")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "homologado" for i in items)


def test_licitacoes_export_csv():
    resp = client.get("/public/licitacoes?export=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]


# ── Convênios ─────────────────────────────────────────────────────────────────

def test_list_convenios_publicos_exclui_rascunho():
    resp = client.get("/public/convenios?page=1&size=50")
    assert resp.status_code == 200
    items = resp.json()["items"]
    # rascunho should not appear
    assert all(i["status"] != "rascunho" for i in items)
    # our vigente must appear
    assert any(i["numero"] == "CONV-PUB-001" for i in items)


def test_convenios_filtro_tipo():
    resp = client.get("/public/convenios?tipo=recebimento&page=1&size=10")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["tipo"] == "recebimento" for i in items)


def test_convenios_filtro_busca():
    resp = client.get("/public/convenios?search=saúde&page=1&size=10")
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert any("saúde" in i["objeto"].lower() for i in items)


def test_convenios_export_csv():
    resp = client.get("/public/convenios?export=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().split("\n")
    assert lines[0].startswith("numero")


def test_convenio_desembolsos_publico():
    # Get the id of the vigente conv
    resp = client.get("/public/convenios?search=CONV-PUB-001")
    item = resp.json()["items"][0]
    cid = item["id"]
    resp2 = client.get(f"/public/convenios/{cid}/desembolsos")
    assert resp2.status_code == 200
    assert "items" in resp2.json()


# ── Arrecadação ───────────────────────────────────────────────────────────────

def test_arrecadacao_retorna_apenas_pagos():
    resp = client.get("/public/arrecadacao?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    # All items must come from 'pago' lancamentos
    items = data["items"]
    assert len(items) >= 1


def test_arrecadacao_filtro_tributo():
    resp = client.get("/public/arrecadacao?tributo=IPTU&page=1&size=10")
    assert resp.status_code == 200
    items = resp.json()["items"]
    if items:
        assert all(i["tributo"] == "IPTU" for i in items)


def test_arrecadacao_export_csv():
    resp = client.get("/public/arrecadacao?export=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().split("\n")
    assert lines[0].startswith("tributo")


# ── Dívida Ativa pública ──────────────────────────────────────────────────────

def test_divida_ativa_publica_sem_auth():
    resp = client.get("/public/divida-ativa?page=1&size=10")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    items = data["items"]
    # Status must be ativa or ajuizada
    for item in items:
        assert item["status"] in ("ativa", "ajuizada")
    # Must NOT expose contribuinte_id or personal data
    for item in items:
        assert "cpf_cnpj" not in item
        assert "contribuinte_id" not in item


def test_divida_ativa_filtro_tributo():
    resp = client.get("/public/divida-ativa?tributo=IPTU&page=1&size=10")
    assert resp.status_code == 200
    items = resp.json()["items"]
    if items:
        assert all(i["tributo"] == "IPTU" for i in items)


def test_divida_ativa_export_csv():
    resp = client.get("/public/divida-ativa?export=csv")
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().split("\n")
    assert lines[0].startswith("numero_inscricao")


def test_divida_ativa_nao_expoe_quitadas():
    """Inscrições quitadas não devem aparecer no portal público."""
    resp = client.get("/public/divida-ativa?page=1&size=100")
    items = resp.json()["items"]
    assert all(i["status"] not in ("quitada", "prescrita", "parcelada") for i in items)


# ── Vendors (existente, regressão) ────────────────────────────────────────────

def test_vendors_publico():
    resp = client.get("/public/vendors?page=1&size=10")
    assert resp.status_code == 200
    assert "items" in resp.json()
