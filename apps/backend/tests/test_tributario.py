"""Testes do módulo Tributário / Arrecadação Municipal.

Cobre: contribuintes, cadastro imobiliário, lançamentos tributários,
emissão e baixa de guias, inscrição em dívida ativa e dashboard.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_tributario.db"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Contribuinte, DividaAtiva, GuiaPagamento, ImovelCadastral, LancamentoTributario
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
        os.remove("./test_tributario.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ── Contribuintes ─────────────────────────────────────────────────────────────

def test_create_contribuinte_pf():
    headers = auth_headers("admin1")
    resp = client.post(
        "/tributario/contribuintes",
        json={
            "cpf_cnpj": "123.456.789-00",
            "nome": "João da Silva",
            "tipo": "PF",
            "email": "joao@example.com",
            "telefone": "(11) 9999-8888",
            "logradouro": "Rua das Flores",
            "numero": "100",
            "bairro": "Centro",
            "municipio": "Municipio Teste",
            "uf": "SP",
            "cep": "01000-000",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["cpf_cnpj"] == "123.456.789-00"
    assert data["nome"] == "João da Silva"
    assert data["tipo"] == "PF"
    assert data["ativo"] is True


def test_create_contribuinte_pj():
    headers = auth_headers("admin1")
    resp = client.post(
        "/tributario/contribuintes",
        json={"cpf_cnpj": "12.345.678/0001-99", "nome": "Empresa ABC Ltda", "tipo": "PJ", "municipio": "Municipio Teste", "uf": "SP"},
        headers=headers,
    )
    assert resp.status_code == 200
    assert resp.json()["tipo"] == "PJ"


def test_create_contribuinte_duplicate_cpf_returns_409():
    headers = auth_headers("admin1")
    payload = {"cpf_cnpj": "999.999.999-99", "nome": "Duplicata Teste", "tipo": "PF"}
    client.post("/tributario/contribuintes", json=payload, headers=headers)
    resp = client.post("/tributario/contribuintes", json=payload, headers=headers)
    assert resp.status_code == 409


def test_list_contribuintes_paginated():
    headers = auth_headers("admin1")
    resp = client.get("/tributario/contribuintes?page=1&size=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data and "items" in data
    assert data["total"] >= 1


def test_search_contribuintes_by_nome():
    headers = auth_headers("admin1")
    resp = client.get("/tributario/contribuintes?search=João&page=1&size=10", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all("João" in i["nome"] or "123.456.789-00" in i["cpf_cnpj"] for i in items)


def test_get_contribuinte_not_found():
    headers = auth_headers("admin1")
    resp = client.get("/tributario/contribuintes/999999", headers=headers)
    assert resp.status_code == 404


def test_update_contribuinte():
    headers = auth_headers("admin1")
    # Criar para atualizar
    create = client.post(
        "/tributario/contribuintes",
        json={"cpf_cnpj": "111.222.333-44", "nome": "Pedro Alves", "tipo": "PF"},
        headers=headers,
    ).json()
    cid = create["id"]
    resp = client.patch(f"/tributario/contribuintes/{cid}", json={"telefone": "(21) 1234-5678", "bairro": "Bairro Novo"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["telefone"] == "(21) 1234-5678"
    assert resp.json()["bairro"] == "Bairro Novo"


# ── Cadastro Imobiliário ──────────────────────────────────────────────────────

def _criar_contribuinte(cpf: str, nome: str, headers: dict) -> int:
    resp = client.post("/tributario/contribuintes", json={"cpf_cnpj": cpf, "nome": nome, "tipo": "PF"}, headers=headers)
    assert resp.status_code == 200
    return resp.json()["id"]


def test_create_imovel():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("222.333.444-55", "Maria Lima", headers)
    resp = client.post(
        "/tributario/imoveis",
        json={
            "inscricao": "IMOV-001-2026",
            "contribuinte_id": cid,
            "logradouro": "Av. Principal",
            "numero": "500",
            "bairro": "Centro",
            "area_terreno": 250.0,
            "area_construida": 120.0,
            "valor_venal": 180000.0,
            "uso": "residencial",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["inscricao"] == "IMOV-001-2026"
    assert data["valor_venal"] == 180000.0
    assert data["ativo"] is True


def test_create_imovel_duplicate_inscricao_409():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("333.444.555-66", "Carlos Melo", headers)
    payload = {"inscricao": "IMOV-DUP-001", "contribuinte_id": cid, "logradouro": "Rua A", "area_terreno": 100.0, "valor_venal": 50000.0}
    client.post("/tributario/imoveis", json=payload, headers=headers)
    resp = client.post("/tributario/imoveis", json=payload, headers=headers)
    assert resp.status_code == 409


def test_create_imovel_contribuinte_nao_existe_404():
    headers = auth_headers("admin1")
    resp = client.post(
        "/tributario/imoveis",
        json={"inscricao": "IMOV-NOREF-001", "contribuinte_id": 999999, "logradouro": "Rua X", "area_terreno": 100.0, "valor_venal": 50000.0},
        headers=headers,
    )
    assert resp.status_code == 404


def test_list_imoveis_por_contribuinte():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("444.555.666-77", "Fernanda Souza", headers)
    client.post(
        "/tributario/imoveis",
        json={"inscricao": "IMOV-FILT-001", "contribuinte_id": cid, "logradouro": "Rua B", "area_terreno": 200.0, "valor_venal": 90000.0},
        headers=headers,
    )
    resp = client.get(f"/tributario/imoveis?contribuinte_id={cid}&page=1&size=5", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["contribuinte_id"] == cid for i in items)


def test_update_imovel_valor_venal():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("555.666.777-88", "Roberto Faria", headers)
    imovel = client.post(
        "/tributario/imoveis",
        json={"inscricao": "IMOV-UPD-001", "contribuinte_id": cid, "logradouro": "Rua C", "area_terreno": 300.0, "valor_venal": 120000.0},
        headers=headers,
    ).json()
    iid = imovel["id"]
    resp = client.patch(f"/tributario/imoveis/{iid}", json={"valor_venal": 150000.0}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["valor_venal"] == 150000.0


# ── Lançamentos Tributários ───────────────────────────────────────────────────

def _setup_contribuinte_imovel(suffix: str, headers: dict) -> tuple[int, int]:
    cpf = f"{suffix[:3]}.{suffix[3:6]}.{suffix[6:9]}-{suffix[9:11]}"[:14] if len(suffix) >= 11 else f"000.{suffix}-00"
    cid = _criar_contribuinte(f"CPF-LANC-{suffix}", f"Contribuinte {suffix}", headers)
    resp = client.post(
        "/tributario/imoveis",
        json={"inscricao": f"IMOV-LANC-{suffix}", "contribuinte_id": cid, "logradouro": "Rua Z", "area_terreno": 200.0, "valor_venal": 200000.0},
        headers=headers,
    )
    iid = resp.json()["id"]
    return cid, iid


def test_create_lancamento_iptu():
    headers = auth_headers("admin1")
    cid, iid = _setup_contribuinte_imovel("LC001", headers)
    resp = client.post(
        "/tributario/lancamentos",
        json={
            "contribuinte_id": cid,
            "imovel_id": iid,
            "tributo": "IPTU",
            "competencia": "2026-01",
            "exercicio": 2026,
            "valor_principal": 1200.0,
            "vencimento": "2026-03-31",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tributo"] == "IPTU"
    assert data["valor_total"] == 1200.0
    assert data["status"] == "aberto"


def test_create_lancamento_iss():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-ISS-001", "Prestadora ISS", headers)
    resp = client.post(
        "/tributario/lancamentos",
        json={
            "contribuinte_id": cid,
            "tributo": "ISS",
            "competencia": "2026-02",
            "exercicio": 2026,
            "valor_principal": 500.0,
            "valor_juros": 25.0,
            "valor_multa": 10.0,
            "valor_desconto": 5.0,
            "vencimento": "2026-03-15",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["tributo"] == "ISS"
    # total = 500 + 25 + 10 - 5 = 530
    assert data["valor_total"] == 530.0


def test_lancamento_contribuinte_nao_existe_404():
    headers = auth_headers("admin1")
    resp = client.post(
        "/tributario/lancamentos",
        json={"contribuinte_id": 999999, "tributo": "IPTU", "competencia": "2026-01", "exercicio": 2026, "valor_principal": 100.0, "vencimento": "2026-03-31"},
        headers=headers,
    )
    assert resp.status_code == 404


def test_list_lancamentos_filtros():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-FILT-L01", "Contribuinte Filtro L", headers)
    client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "IPTU", "competencia": "2026-01", "exercicio": 2026, "valor_principal": 800.0, "vencimento": "2026-03-31"}, headers=headers)
    client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "ISS", "competencia": "2026-02", "exercicio": 2026, "valor_principal": 300.0, "vencimento": "2026-04-30"}, headers=headers)

    resp_iptu = client.get(f"/tributario/lancamentos?contribuinte_id={cid}&tributo=IPTU&page=1&size=10", headers=headers)
    assert resp_iptu.status_code == 200
    items = resp_iptu.json()["items"]
    assert all(i["tributo"] == "IPTU" for i in items)


def test_update_lancamento_juros_recalcula_total():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-UPD-L01", "Contribuinte UPD L", headers)
    lanc = client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "IPTU", "competencia": "2026-01", "exercicio": 2026, "valor_principal": 1000.0, "vencimento": "2026-03-31"}, headers=headers).json()
    lid = lanc["id"]

    resp = client.patch(f"/tributario/lancamentos/{lid}", json={"valor_juros": 50.0, "valor_multa": 20.0}, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["valor_juros"] == 50.0
    # total = 1000 + 50 + 20 - 0 = 1070
    assert data["valor_total"] == 1070.0


# ── Guias de Arrecadação ──────────────────────────────────────────────────────

def test_emitir_guia_e_baixar():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-GUIA-001", "Contribuinte Guia", headers)
    lanc = client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "IPTU", "competencia": "2026-03", "exercicio": 2026, "valor_principal": 600.0, "vencimento": "2026-03-31"}, headers=headers).json()
    lid = lanc["id"]

    # Emitir guia
    guia_resp = client.post(f"/tributario/lancamentos/{lid}/emitir-guia", headers=headers)
    assert guia_resp.status_code == 200
    guia = guia_resp.json()
    assert guia["status"] == "emitida"
    assert guia["valor"] == 600.0
    assert "PREFMUN." in guia["codigo_barras"]

    # Baixar (pagar) a guia
    baixa = client.post(
        f"/tributario/guias/{guia['id']}/baixar",
        params={"data_pagamento": "2026-03-20", "banco": "Banco do Brasil"},
        headers=headers,
    )
    assert baixa.status_code == 200
    assert baixa.json()["status"] == "paga"
    assert baixa.json()["data_pagamento"] == "2026-03-20"

    # Verificar que o lançamento também foi marcado como pago
    db = SessionLocal()
    try:
        l = db.get(LancamentoTributario, lid)
        assert l.status == "pago"
        assert str(l.data_pagamento) == "2026-03-20"
    finally:
        db.close()


def test_emitir_guia_lancamento_pago_422():
    """Lançamento já pago não deve permitir nova guia."""
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-GUIA-002", "Contribuinte Guia 2", headers)
    lanc = client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "ISS", "competencia": "2026-04", "exercicio": 2026, "valor_principal": 200.0, "vencimento": "2026-04-30"}, headers=headers).json()
    lid = lanc["id"]

    guia = client.post(f"/tributario/lancamentos/{lid}/emitir-guia", headers=headers).json()
    client.post(f"/tributario/guias/{guia['id']}/baixar", params={"data_pagamento": "2026-04-10"}, headers=headers)

    resp = client.post(f"/tributario/lancamentos/{lid}/emitir-guia", headers=headers)
    assert resp.status_code == 422


def test_emitir_nova_guia_cancela_anterior():
    """Emitir nova guia deve cancelar a guia anterior."""
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-GUIA-003", "Contribuinte Guia 3", headers)
    lanc = client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "IPTU", "competencia": "2026-05", "exercicio": 2026, "valor_principal": 400.0, "vencimento": "2026-05-31"}, headers=headers).json()
    lid = lanc["id"]

    guia1 = client.post(f"/tributario/lancamentos/{lid}/emitir-guia", headers=headers).json()
    assert guia1["status"] == "emitida"

    # Atualizar juros no lançamento primeiro
    client.patch(f"/tributario/lancamentos/{lid}", json={"valor_juros": 10.0}, headers=headers)

    guia2 = client.post(f"/tributario/lancamentos/{lid}/emitir-guia", headers=headers).json()
    assert guia2["status"] == "emitida"

    # Verificar que a primeira foi cancelada
    db = SessionLocal()
    try:
        g1 = db.get(GuiaPagamento, guia1["id"])
        assert g1.status == "cancelada"
    finally:
        db.close()


def test_list_guias_filtro_status():
    headers = auth_headers("admin1")
    resp = client.get("/tributario/guias?status=emitida&page=1&size=10", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "emitida" for i in items)


# ── Dívida Ativa ──────────────────────────────────────────────────────────────

def test_inscrever_divida_ativa_fluxo_completo():
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-DA-001", "Inadimplente Fiscal", headers)
    lanc = client.post(
        "/tributario/lancamentos",
        json={"contribuinte_id": cid, "tributo": "IPTU", "competencia": "2025-01", "exercicio": 2025, "valor_principal": 1500.0, "vencimento": "2025-03-31"},
        headers=headers,
    ).json()
    lid = lanc["id"]

    resp = client.post(
        "/tributario/divida-ativa",
        json={
            "lancamento_id": lid,
            "numero_inscricao": "DA-2025-001",
            "data_inscricao": "2025-04-01",
            "valor_atualizado": 1650.0,
            "observacoes": "Vencido sem pagamento",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    da = resp.json()
    assert da["numero_inscricao"] == "DA-2025-001"
    assert da["tributo"] == "IPTU"
    assert da["valor_original"] == 1500.0
    assert da["valor_atualizado"] == 1650.0
    assert da["status"] == "ativa"

    # Lançamento deve ter status inscrito_divida
    db = SessionLocal()
    try:
        l = db.get(LancamentoTributario, lid)
        assert l.status == "inscrito_divida"
    finally:
        db.close()


def test_inscrever_divida_lancamento_pago_422():
    """Lançamento pago não pode ser inscrito em dívida ativa."""
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-DA-002", "Contribuinte Pago", headers)
    lanc = client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "ISS", "competencia": "2025-02", "exercicio": 2025, "valor_principal": 300.0, "vencimento": "2025-03-31"}, headers=headers).json()
    lid = lanc["id"]

    # Pagar via guia
    guia = client.post(f"/tributario/lancamentos/{lid}/emitir-guia", headers=headers).json()
    client.post(f"/tributario/guias/{guia['id']}/baixar", params={"data_pagamento": "2025-03-20"}, headers=headers)

    resp = client.post(
        "/tributario/divida-ativa",
        json={"lancamento_id": lid, "numero_inscricao": "DA-PAGO-001", "data_inscricao": "2025-04-01", "valor_atualizado": 310.0},
        headers=headers,
    )
    assert resp.status_code == 422


def test_inscrever_divida_duplicada_409():
    """Mesmo lançamento não pode ser inscrito duas vezes."""
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-DA-003", "Contribuinte DUP DA", headers)
    lanc = client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "IPTU", "competencia": "2025-03", "exercicio": 2025, "valor_principal": 800.0, "vencimento": "2025-03-31"}, headers=headers).json()
    lid = lanc["id"]

    client.post("/tributario/divida-ativa", json={"lancamento_id": lid, "numero_inscricao": "DA-DUP-001", "data_inscricao": "2025-04-01", "valor_atualizado": 850.0}, headers=headers)
    resp = client.post("/tributario/divida-ativa", json={"lancamento_id": lid, "numero_inscricao": "DA-DUP-002", "data_inscricao": "2025-04-01", "valor_atualizado": 850.0}, headers=headers)
    assert resp.status_code == 409


def test_quitar_divida_ativa():
    """Quitar dívida ativa deve marcar lançamento como pago."""
    headers = auth_headers("admin1")
    cid = _criar_contribuinte("CPF-DA-004", "Contribuinte Quitação", headers)
    lanc = client.post("/tributario/lancamentos", json={"contribuinte_id": cid, "tributo": "IPTU", "competencia": "2024-01", "exercicio": 2024, "valor_principal": 2000.0, "vencimento": "2024-03-31"}, headers=headers).json()
    lid = lanc["id"]

    da = client.post("/tributario/divida-ativa", json={"lancamento_id": lid, "numero_inscricao": "DA-QUIT-001", "data_inscricao": "2024-04-01", "valor_atualizado": 2200.0}, headers=headers).json()

    resp = client.patch(f"/tributario/divida-ativa/{da['id']}", json={"status": "quitada", "valor_atualizado": 2200.0}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "quitada"

    db = SessionLocal()
    try:
        l = db.get(LancamentoTributario, lid)
        assert l.status == "pago"
    finally:
        db.close()


def test_list_divida_ativa():
    headers = auth_headers("admin1")
    resp = client.get("/tributario/divida-ativa?status=ativa&page=1&size=10", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "ativa" for i in items)


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard_retorna_resumo():
    headers = auth_headers("admin1")
    resp = client.get("/tributario/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total_contribuintes_ativos" in data
    assert "total_imoveis_ativos" in data
    assert "valor_aberto" in data
    assert "valor_arrecadado" in data
    assert "valor_divida_ativa" in data
    assert "lancamentos_vencidos_abertos" in data
    assert "lancamentos_por_status" in data
    # Deve haver ao menos contribuintes e lançamentos criados nos testes anteriores
    assert data["total_contribuintes_ativos"] >= 1
