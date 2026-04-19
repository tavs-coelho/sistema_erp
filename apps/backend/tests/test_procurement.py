"""Testes de compras/contratos (procurement) e orçamento público (PPA/LDO/LOA)."""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_procurement.db"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import LDO, LOA, PPA, Contract, LDOGoal, LOAItem, PPAProgram, ProcurementProcess
from app.seed import seed_data

client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_procurement.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ── Procurement / Processos ───────────────────────────────────────────────────

def test_list_processes_returns_paginated_response():
    headers = auth_headers("procurement1")
    resp = client.get("/procurement/processes?page=1&size=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data
    assert data["total"] >= 0


def test_create_process_and_award():
    headers = auth_headers("procurement1")

    create_resp = client.post(
        "/procurement/processes",
        json={"number": "PROC-TEST-001", "object_description": "Aquisição de material de escritório", "status": "aberto"},
        headers=headers,
    )
    assert create_resp.status_code == 200
    proc_id = create_resp.json()["id"]
    assert create_resp.json()["status"] == "aberto"

    # Buscar processo por ID
    get_resp = client.get(f"/procurement/processes/{proc_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["number"] == "PROC-TEST-001"

    # Homologar processo
    award_resp = client.post(f"/procurement/processes/{proc_id}/award", headers=headers)
    assert award_resp.status_code == 200

    # Verificar status atualizado
    db = SessionLocal()
    try:
        proc = db.get(ProcurementProcess, proc_id)
        assert proc.status == "homologado"
    finally:
        db.close()


def test_create_process_duplicate_number_returns_409():
    headers = auth_headers("procurement1")
    client.post("/procurement/processes", json={"number": "PROC-DUP-001", "object_description": "Teste duplicata"}, headers=headers)
    resp = client.post("/procurement/processes", json={"number": "PROC-DUP-001", "object_description": "Outro processo"}, headers=headers)
    assert resp.status_code == 409


def test_update_process_via_patch():
    headers = auth_headers("procurement1")
    create_resp = client.post(
        "/procurement/processes",
        json={"number": "PROC-PATCH-001", "object_description": "Descrição original"},
        headers=headers,
    )
    proc_id = create_resp.json()["id"]
    patch_resp = client.patch(f"/procurement/processes/{proc_id}", json={"object_description": "Descrição atualizada"}, headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["object_description"] == "Descrição atualizada"


def test_filter_processes_by_status():
    headers = auth_headers("admin1")
    resp = client.get("/procurement/processes?status=homologado&page=1&size=10", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "homologado" for i in items)


def test_award_process_returns_404_for_missing():
    headers = auth_headers("admin1")
    resp = client.post("/procurement/processes/999999/award", headers=headers)
    assert resp.status_code == 404


# ── Procurement / Contratos ───────────────────────────────────────────────────

def test_list_contracts_returns_paginated_response():
    headers = auth_headers("procurement1")
    resp = client.get("/procurement/contracts?page=1&size=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert "items" in data


def test_create_contract_end_to_end():
    headers_proc = auth_headers("procurement1")

    # Criar processo para vincular ao contrato
    proc = client.post(
        "/procurement/processes",
        json={"number": "PROC-CT-E2E-001", "object_description": "Processo para contrato E2E"},
        headers=headers_proc,
    ).json()
    proc_id = proc["id"]

    # Criar contrato
    contract_resp = client.post(
        "/procurement/contracts",
        json={
            "number": "CT-TEST-E2E-001",
            "process_id": proc_id,
            "vendor_id": 1,
            "start_date": "2026-01-01",
            "end_date": "2026-12-31",
            "amount": 50000.00,
            "status": "vigente",
        },
        headers=headers_proc,
    )
    assert contract_resp.status_code == 200
    contract_id = contract_resp.json()["id"]
    assert contract_resp.json()["amount"] == 50000.00

    # Buscar contrato por ID
    get_resp = client.get(f"/procurement/contracts/{contract_id}", headers=headers_proc)
    assert get_resp.status_code == 200
    assert get_resp.json()["number"] == "CT-TEST-E2E-001"

    # Adicionar aditivo
    addendum_resp = client.post(
        f"/procurement/contracts/{contract_id}/addenda",
        params={"description": "Aditivo de prazo e valor", "amount_delta": 5000.0},
        headers=headers_proc,
    )
    assert addendum_resp.status_code == 200

    # Verificar que o valor do contrato foi atualizado
    db = SessionLocal()
    try:
        contract = db.get(Contract, contract_id)
        assert contract.amount == 55000.00
    finally:
        db.close()

    # Listar aditivos
    addenda_resp = client.get(f"/procurement/contracts/{contract_id}/addenda", headers=headers_proc)
    assert addenda_resp.status_code == 200
    assert len(addenda_resp.json()) == 1


def test_create_contract_duplicate_number_returns_409():
    headers = auth_headers("procurement1")
    payload = {"number": "CT-DUP-001", "process_id": 1, "vendor_id": 1, "start_date": "2026-01-01", "end_date": "2026-12-31", "amount": 10000}
    client.post("/procurement/contracts", json=payload, headers=headers)
    resp = client.post("/procurement/contracts", json=payload, headers=headers)
    assert resp.status_code == 409


def test_update_contract_status_via_patch():
    headers = auth_headers("procurement1")
    create_resp = client.post(
        "/procurement/contracts",
        json={"number": "CT-PATCH-001", "process_id": 1, "vendor_id": 1, "start_date": "2026-01-01", "end_date": "2026-12-31", "amount": 20000},
        headers=headers,
    )
    contract_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/procurement/contracts/{contract_id}", json={"status": "encerrado"}, headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "encerrado"


def test_list_expiring_contracts():
    headers = auth_headers("procurement1")
    resp = client.get("/procurement/contracts/expiring?days=365", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_filter_contracts_by_status():
    headers = auth_headers("procurement1")
    resp = client.get("/procurement/contracts?status=vigente&page=1&size=10", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "vigente" for i in items)


# ── Orçamento: PPA ────────────────────────────────────────────────────────────

def test_create_ppa_and_add_program():
    headers = auth_headers("admin1")

    ppa_resp = client.post(
        "/budget/ppas",
        json={"period_start": 2026, "period_end": 2029, "description": "PPA 2026–2029 Demo", "status": "rascunho"},
        headers=headers,
    )
    assert ppa_resp.status_code == 200
    ppa_id = ppa_resp.json()["id"]
    assert ppa_resp.json()["period_start"] == 2026

    prog_resp = client.post(
        f"/budget/ppas/{ppa_id}/programs",
        json={"code": "PROG-01", "name": "Saúde Preventiva", "objective": "Ampliar cobertura de saúde", "estimated_amount": 1200000},
        headers=headers,
    )
    assert prog_resp.status_code == 200
    assert prog_resp.json()["code"] == "PROG-01"

    # Listar programas
    list_resp = client.get(f"/budget/ppas/{ppa_id}/programs", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Verificar banco
    db = SessionLocal()
    try:
        ppa = db.get(PPA, ppa_id)
        assert ppa is not None
        assert len(ppa.programs) == 1
        assert ppa.programs[0].name == "Saúde Preventiva"
    finally:
        db.close()


def test_update_ppa_status():
    headers = auth_headers("admin1")
    create_resp = client.post(
        "/budget/ppas",
        json={"period_start": 2030, "period_end": 2033, "description": "PPA Patch Test"},
        headers=headers,
    )
    ppa_id = create_resp.json()["id"]

    patch_resp = client.patch(f"/budget/ppas/{ppa_id}", json={"status": "aprovado"}, headers=headers)
    assert patch_resp.status_code == 200
    assert patch_resp.json()["status"] == "aprovado"


def test_ppa_period_validation():
    headers = auth_headers("admin1")
    resp = client.post(
        "/budget/ppas",
        json={"period_start": 2029, "period_end": 2025, "description": "PPA Inválido"},
        headers=headers,
    )
    assert resp.status_code == 422


# ── Orçamento: LDO ────────────────────────────────────────────────────────────

def test_create_ldo_and_add_goal():
    headers = auth_headers("admin1")

    ldo_resp = client.post(
        "/budget/ldos",
        json={"fiscal_year_id": 1, "description": "LDO 2026 Demo", "status": "rascunho"},
        headers=headers,
    )
    assert ldo_resp.status_code == 200
    ldo_id = ldo_resp.json()["id"]

    goal_resp = client.post(
        f"/budget/ldos/{ldo_id}/goals",
        json={"code": "META-01", "description": "Controlar despesas com pessoal", "category": "meta_fiscal"},
        headers=headers,
    )
    assert goal_resp.status_code == 200
    assert goal_resp.json()["code"] == "META-01"

    # Listar metas
    list_resp = client.get(f"/budget/ldos/{ldo_id}/goals", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 1

    # Verificar banco
    db = SessionLocal()
    try:
        ldo = db.get(LDO, ldo_id)
        assert ldo is not None
        assert len(ldo.goals) == 1
        assert ldo.goals[0].category == "meta_fiscal"
    finally:
        db.close()


def test_list_ldos_with_filters():
    headers = auth_headers("admin1")
    client.post("/budget/ldos", json={"fiscal_year_id": 1, "description": "LDO Filtro Test", "status": "aprovado"}, headers=headers)
    resp = client.get("/budget/ldos?status=aprovado&page=1&size=10", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "aprovado" for i in items)


# ── Orçamento: LOA ────────────────────────────────────────────────────────────

def test_create_loa_add_items_and_check_execution():
    headers = auth_headers("admin1")

    # Criar LDO de referência
    ldo = client.post(
        "/budget/ldos",
        json={"fiscal_year_id": 1, "description": "LDO para LOA E2E"},
        headers=headers,
    ).json()
    ldo_id = ldo["id"]

    # Criar LOA
    loa_resp = client.post(
        "/budget/loas",
        json={
            "fiscal_year_id": 1,
            "ldo_id": ldo_id,
            "description": "LOA 2026 E2E",
            "total_revenue": 5000000.0,
            "total_expenditure": 0.0,
        },
        headers=headers,
    )
    assert loa_resp.status_code == 200
    loa_id = loa_resp.json()["id"]

    # Adicionar item (dotação)
    item_resp = client.post(
        f"/budget/loas/{loa_id}/items",
        json={
            "function_code": "10",
            "subfunction_code": "301",
            "program_code": "0015",
            "action_code": "2001",
            "description": "Atenção básica à saúde",
            "category": "despesa",
            "authorized_amount": 800000.0,
        },
        headers=headers,
    )
    assert item_resp.status_code == 200
    item_id = item_resp.json()["id"]

    # Verificar que total_expenditure foi atualizado automaticamente
    db = SessionLocal()
    try:
        loa = db.get(LOA, loa_id)
        assert loa.total_expenditure == 800000.0
    finally:
        db.close()

    # Atualizar execução do item
    patch_resp = client.patch(
        f"/budget/loas/{loa_id}/items/{item_id}",
        json={"executed_amount": 320000.0},
        headers=headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["executed_amount"] == 320000.0

    # Verificar resumo de execução
    summary = client.get(f"/budget/loas/{loa_id}/execution-summary", headers=headers)
    assert summary.status_code == 200
    data = summary.json()
    assert data["total_authorized"] == 800000.0
    assert data["total_executed"] == 320000.0
    assert data["execution_rate"] == 40.0
    assert len(data["by_function"]) == 1
    assert data["by_function"][0]["function_code"] == "10"


def test_loa_execution_summary_returns_404_for_unknown():
    headers = auth_headers("admin1")
    resp = client.get("/budget/loas/999999/execution-summary", headers=headers)
    assert resp.status_code == 404


def test_list_loa_items_with_filters():
    headers = auth_headers("admin1")
    loa = client.post(
        "/budget/loas",
        json={"fiscal_year_id": 1, "description": "LOA Filtro"},
        headers=headers,
    ).json()
    loa_id = loa["id"]

    client.post(
        f"/budget/loas/{loa_id}/items",
        json={"function_code": "12", "subfunction_code": "361", "program_code": "0016", "action_code": "2002", "description": "Ensino fundamental", "category": "despesa", "authorized_amount": 500000},
        headers=headers,
    )
    client.post(
        f"/budget/loas/{loa_id}/items",
        json={"function_code": "10", "subfunction_code": "305", "program_code": "0017", "action_code": "2003", "description": "Vigilância sanitária", "category": "despesa", "authorized_amount": 200000},
        headers=headers,
    )

    resp = client.get(f"/budget/loas/{loa_id}/items?function_code=12", headers=headers)
    assert resp.status_code == 200
    assert all(i["function_code"] == "12" for i in resp.json())
