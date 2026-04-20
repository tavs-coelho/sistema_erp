"""Testes do módulo NFS-e / ITBI.

Cobre: emissão de NFS-e, cancelamento, filtros, relatório CSV,
       registro de ITBI, cancelamento, base de cálculo, filtros,
       dashboard consolidado e geração automática de LancamentoTributario.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_nfse_itbi.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Contribuinte,
    ImovelCadastral,
    LancamentoTributario,
    NotaFiscalServico,
    OperacaoITBI,
)
from app.seed import seed_data

client = TestClient(app)

YEAR = date.today().year


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_nfse_itbi.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ── Fixtures helpers ──────────────────────────────────────────────────────────

def _make_contribuinte(cpf_cnpj: str, nome: str, tipo: str = "PJ") -> int:
    db = SessionLocal()
    c = Contribuinte(
        cpf_cnpj=cpf_cnpj, nome=nome, tipo=tipo,
        municipio="Teste", uf="SP", cep="00000-000",
        logradouro="Rua Teste", numero="1", bairro="Centro",
    )
    db.add(c)
    db.commit()
    db.refresh(c)
    cid = c.id
    db.close()
    return cid


def _make_imovel(contribuinte_id: int, inscricao: str, valor_venal: float = 100000.0) -> int:
    db = SessionLocal()
    im = ImovelCadastral(
        inscricao=inscricao,
        contribuinte_id=contribuinte_id,
        logradouro="Rua Imóvel",
        numero="10",
        bairro="Bairro",
        area_terreno=100.0,
        area_construida=60.0,
        valor_venal=valor_venal,
        uso="residencial",
    )
    db.add(im)
    db.commit()
    db.refresh(im)
    iid = im.id
    db.close()
    return iid


# ── NFS-e ─────────────────────────────────────────────────────────────────────

def test_emitir_nfse_ok():
    headers = auth_headers("admin1")
    prestador = _make_contribuinte("10.000.001/0001-01", "Prestador Teste 1")
    resp = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": prestador,
            "descricao_servico": "Desenvolvimento de software sob demanda",
            "codigo_servico": "1.07",
            "competencia": f"{YEAR}-03",
            "data_emissao": f"{YEAR}-03-10",
            "valor_servico": 10000.0,
            "aliquota_iss": 2.0,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "emitida"
    assert data["numero"].startswith("NFS/")
    assert data["valor_iss"] == 200.0          # 10000 * 2% = 200
    assert data["lancamento_id"] is not None


def test_emitir_nfse_com_tomador():
    headers = auth_headers("admin1")
    prestador = _make_contribuinte("10.000.002/0001-02", "Prestador Teste 2")
    tomador = _make_contribuinte("10.000.003/0001-03", "Tomador Teste 3")
    resp = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": prestador,
            "tomador_id": tomador,
            "descricao_servico": "Serviço de limpeza predial",
            "competencia": f"{YEAR}-04",
            "data_emissao": f"{YEAR}-04-05",
            "valor_servico": 4000.0,
            "aliquota_iss": 3.0,
            "retencao_fonte": True,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["tomador_id"] == tomador
    assert data["retencao_fonte"] is True
    assert data["valor_iss"] == 120.0          # 4000 * 3%


def test_emitir_nfse_com_deducoes():
    headers = auth_headers("admin1")
    prestador = _make_contribuinte("10.000.004/0001-04", "Prestador Teste 4")
    resp = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": prestador,
            "descricao_servico": "Obra com material incluso",
            "competencia": f"{YEAR}-05",
            "data_emissao": f"{YEAR}-05-02",
            "valor_servico": 8000.0,
            "valor_deducoes": 3000.0,          # base = 5000
            "aliquota_iss": 2.5,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    assert resp.json()["valor_iss"] == 125.0   # 5000 * 2.5%


def test_emitir_nfse_prestador_inexistente():
    headers = auth_headers("admin1")
    resp = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": 999999,
            "descricao_servico": "Serviço qualquer",
            "competencia": f"{YEAR}-01",
            "data_emissao": f"{YEAR}-01-01",
            "valor_servico": 1000.0,
            "aliquota_iss": 2.0,
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_emitir_nfse_aliquota_zero():
    headers = auth_headers("admin1")
    prestador = _make_contribuinte("10.000.005/0001-05", "Prestador Teste 5")
    resp = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": prestador,
            "descricao_servico": "Serviço qualquer",
            "competencia": f"{YEAR}-01",
            "data_emissao": f"{YEAR}-01-01",
            "valor_servico": 1000.0,
            "aliquota_iss": 0.0,
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_emitir_nfse_sem_auth():
    resp = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": 1,
            "descricao_servico": "X",
            "competencia": f"{YEAR}-01",
            "data_emissao": f"{YEAR}-01-01",
            "valor_servico": 100.0,
            "aliquota_iss": 2.0,
        },
    )
    assert resp.status_code == 401


def test_list_nfse():
    headers = auth_headers("admin1")
    resp = client.get("/nfse", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data
    assert data["total"] >= 2   # seed has 2 NFS-e


def test_list_nfse_filtro_status():
    headers = auth_headers("admin1")
    resp = client.get("/nfse?status=emitida", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "emitida"


def test_list_nfse_filtro_competencia():
    headers = auth_headers("admin1")
    resp = client.get(f"/nfse?competencia={YEAR}-03", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["competencia"] == f"{YEAR}-03"


def test_get_nfse_detalhe():
    headers = auth_headers("admin1")
    # Get first NFS-e from seed
    resp = client.get("/nfse?size=1", headers=headers)
    nfse_id = resp.json()["items"][0]["id"]
    resp2 = client.get(f"/nfse/{nfse_id}", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["id"] == nfse_id


def test_get_nfse_nao_encontrada():
    headers = auth_headers("admin1")
    resp = client.get("/nfse/999999", headers=headers)
    assert resp.status_code == 404


def test_cancelar_nfse():
    headers = auth_headers("admin1")
    prestador = _make_contribuinte("10.000.010/0001-10", "Prestador Cancel")
    # Emite
    em = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": prestador,
            "descricao_servico": "Serviço a cancelar",
            "competencia": f"{YEAR}-06",
            "data_emissao": f"{YEAR}-06-01",
            "valor_servico": 500.0,
            "aliquota_iss": 2.0,
        },
        headers=headers,
    )
    assert em.status_code == 201
    nfse_id = em.json()["id"]
    lancamento_id = em.json()["lancamento_id"]

    # Cancela
    resp = client.patch(f"/nfse/{nfse_id}/cancelar?motivo=Serviço não prestado", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelada"

    # Verifica lançamento tributário cancelado
    db = SessionLocal()
    lanc = db.get(LancamentoTributario, lancamento_id)
    assert lanc.status == "cancelado"
    db.close()


def test_cancelar_nfse_ja_cancelada():
    headers = auth_headers("admin1")
    prestador = _make_contribuinte("10.000.011/0001-11", "Prestador Cancel2")
    em = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": prestador,
            "descricao_servico": "X",
            "competencia": f"{YEAR}-06",
            "data_emissao": f"{YEAR}-06-01",
            "valor_servico": 200.0,
            "aliquota_iss": 2.0,
        },
        headers=headers,
    )
    nfse_id = em.json()["id"]
    client.patch(f"/nfse/{nfse_id}/cancelar", headers=headers)
    # Segunda tentativa deve falhar
    resp = client.patch(f"/nfse/{nfse_id}/cancelar", headers=headers)
    assert resp.status_code == 422


def test_cancelar_nfse_sem_permissao():
    """read_only não pode cancelar NFS-e."""
    headers_ro = auth_headers("read_only1")
    headers_admin = auth_headers("admin1")
    prestador = _make_contribuinte("10.000.012/0001-12", "Prestador RO")
    em = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": prestador,
            "descricao_servico": "X",
            "competencia": f"{YEAR}-07",
            "data_emissao": f"{YEAR}-07-01",
            "valor_servico": 200.0,
            "aliquota_iss": 2.0,
        },
        headers=headers_admin,
    )
    nfse_id = em.json()["id"]
    resp = client.patch(f"/nfse/{nfse_id}/cancelar", headers=headers_ro)
    assert resp.status_code == 403


def test_relatorio_nfse_json():
    headers = auth_headers("admin1")
    resp = client.get("/nfse/relatorio", headers=headers)
    assert resp.status_code == 200
    assert "total" in resp.json()


def test_relatorio_nfse_csv():
    headers = auth_headers("admin1")
    resp = client.get("/nfse/relatorio?export=csv", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().splitlines()
    assert lines[0].startswith("numero,")
    assert len(lines) >= 2   # header + at least 1 data row


def test_nfse_gera_lancamento_tributario():
    """Verifica que a NFS-e cria corretamente um LancamentoTributario com tributo=ISS."""
    headers = auth_headers("admin1")
    prestador = _make_contribuinte("10.000.020/0001-20", "Prestador ISS Check")
    resp = client.post(
        "/nfse/emitir",
        json={
            "prestador_id": prestador,
            "descricao_servico": "Auditoria contábil",
            "competencia": f"{YEAR}-08",
            "data_emissao": f"{YEAR}-08-01",
            "valor_servico": 6000.0,
            "aliquota_iss": 2.5,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    lancamento_id = resp.json()["lancamento_id"]
    assert lancamento_id is not None

    db = SessionLocal()
    lanc = db.get(LancamentoTributario, lancamento_id)
    assert lanc is not None
    assert lanc.tributo == "ISS"
    assert lanc.valor_total == 150.0  # 6000 * 2.5%
    assert lanc.contribuinte_id == prestador
    db.close()


# ── ITBI ──────────────────────────────────────────────────────────────────────

def test_registrar_itbi_ok():
    headers = auth_headers("admin1")
    transmitente = _make_contribuinte("20.000.001/0001-01", "Transmitente ITBI 1")
    adquirente = _make_contribuinte("20.000.002/0001-02", "Adquirente ITBI 1")
    imovel = _make_imovel(transmitente, "TST-ITBI-001", valor_venal=200000.0)
    resp = client.post(
        "/itbi/registrar",
        json={
            "transmitente_id": transmitente,
            "adquirente_id": adquirente,
            "imovel_id": imovel,
            "natureza_operacao": "compra_venda",
            "data_operacao": f"{YEAR}-04-10",
            "valor_declarado": 180000.0,
            "valor_venal_referencia": 200000.0,  # > declarado → usa venal como base
            "aliquota_itbi": 2.0,
        },
        headers=headers,
    )
    assert resp.status_code == 201, resp.text
    data = resp.json()
    assert data["status"] == "aberto"
    assert data["numero"].startswith("ITBI/")
    assert data["base_calculo"] == 200000.0     # max(180000, 200000)
    assert data["valor_devido"] == 4000.0       # 200000 * 2%
    assert data["lancamento_id"] is not None


def test_registrar_itbi_base_declarado_maior():
    """Quando valor declarado > venal referência, usa declarado como base."""
    headers = auth_headers("admin1")
    transmitente = _make_contribuinte("20.000.003/0001-03", "Transmitente ITBI 3")
    adquirente = _make_contribuinte("20.000.004/0001-04", "Adquirente ITBI 4")
    imovel = _make_imovel(transmitente, "TST-ITBI-002", valor_venal=100000.0)
    resp = client.post(
        "/itbi/registrar",
        json={
            "transmitente_id": transmitente,
            "adquirente_id": adquirente,
            "imovel_id": imovel,
            "natureza_operacao": "compra_venda",
            "data_operacao": f"{YEAR}-05-01",
            "valor_declarado": 150000.0,        # > venal 100k → usa declarado
            "valor_venal_referencia": 100000.0,
            "aliquota_itbi": 2.0,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["base_calculo"] == 150000.0
    assert data["valor_devido"] == 3000.0


def test_registrar_itbi_usa_venal_imovel_quando_sem_referencia():
    """Quando valor_venal_referencia=0, usa valor_venal do imóvel."""
    headers = auth_headers("admin1")
    transmitente = _make_contribuinte("20.000.005/0001-05", "Transmitente ITBI 5")
    adquirente = _make_contribuinte("20.000.006/0001-06", "Adquirente ITBI 6")
    imovel = _make_imovel(transmitente, "TST-ITBI-003", valor_venal=120000.0)
    resp = client.post(
        "/itbi/registrar",
        json={
            "transmitente_id": transmitente,
            "adquirente_id": adquirente,
            "imovel_id": imovel,
            "natureza_operacao": "doacao",
            "data_operacao": f"{YEAR}-05-15",
            "valor_declarado": 80000.0,         # < venal 120k
            "aliquota_itbi": 2.0,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["base_calculo"] == 120000.0     # valor_venal do imóvel
    assert data["valor_devido"] == 2400.0


def test_registrar_itbi_transmitente_inexistente():
    headers = auth_headers("admin1")
    adquirente = _make_contribuinte("20.000.007/0001-07", "Adquirente ITBI 7")
    imovel = _make_imovel(adquirente, "TST-ITBI-004")
    resp = client.post(
        "/itbi/registrar",
        json={
            "transmitente_id": 999999,
            "adquirente_id": adquirente,
            "imovel_id": imovel,
            "natureza_operacao": "compra_venda",
            "data_operacao": f"{YEAR}-01-01",
            "valor_declarado": 100000.0,
            "aliquota_itbi": 2.0,
        },
        headers=headers,
    )
    assert resp.status_code == 404


def test_registrar_itbi_aliquota_zero():
    headers = auth_headers("admin1")
    transmitente = _make_contribuinte("20.000.008/0001-08", "Transmitente ITBI 8")
    adquirente = _make_contribuinte("20.000.009/0001-09", "Adquirente ITBI 9")
    imovel = _make_imovel(transmitente, "TST-ITBI-005")
    resp = client.post(
        "/itbi/registrar",
        json={
            "transmitente_id": transmitente,
            "adquirente_id": adquirente,
            "imovel_id": imovel,
            "natureza_operacao": "compra_venda",
            "data_operacao": f"{YEAR}-01-01",
            "valor_declarado": 100000.0,
            "aliquota_itbi": 0.0,
        },
        headers=headers,
    )
    assert resp.status_code == 422


def test_list_itbi():
    headers = auth_headers("admin1")
    resp = client.get("/itbi", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1   # seed has 1 ITBI


def test_list_itbi_filtro_status():
    headers = auth_headers("admin1")
    resp = client.get("/itbi?status=aberto", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "aberto"


def test_list_itbi_filtro_natureza():
    headers = auth_headers("admin1")
    resp = client.get("/itbi?natureza_operacao=compra_venda", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["natureza_operacao"] == "compra_venda"


def test_get_itbi_detalhe():
    headers = auth_headers("admin1")
    resp = client.get("/itbi?size=1", headers=headers)
    itbi_id = resp.json()["items"][0]["id"]
    resp2 = client.get(f"/itbi/{itbi_id}", headers=headers)
    assert resp2.status_code == 200
    assert resp2.json()["id"] == itbi_id


def test_get_itbi_nao_encontrado():
    headers = auth_headers("admin1")
    resp = client.get("/itbi/999999", headers=headers)
    assert resp.status_code == 404


def test_cancelar_itbi():
    headers = auth_headers("admin1")
    transmitente = _make_contribuinte("20.000.020/0001-20", "Transmitente Cancel")
    adquirente = _make_contribuinte("20.000.021/0001-21", "Adquirente Cancel")
    imovel = _make_imovel(transmitente, "TST-ITBI-CANCEL-01")
    reg = client.post(
        "/itbi/registrar",
        json={
            "transmitente_id": transmitente,
            "adquirente_id": adquirente,
            "imovel_id": imovel,
            "natureza_operacao": "compra_venda",
            "data_operacao": f"{YEAR}-06-01",
            "valor_declarado": 120000.0,
            "aliquota_itbi": 2.0,
        },
        headers=headers,
    )
    assert reg.status_code == 201
    itbi_id = reg.json()["id"]
    lancamento_id = reg.json()["lancamento_id"]

    resp = client.patch(f"/itbi/{itbi_id}/cancelar?motivo=Erro na transmissão", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "cancelado"

    db = SessionLocal()
    lanc = db.get(LancamentoTributario, lancamento_id)
    assert lanc.status == "cancelado"
    db.close()


def test_cancelar_itbi_ja_cancelado():
    headers = auth_headers("admin1")
    transmitente = _make_contribuinte("20.000.022/0001-22", "Transmitente Cancel2")
    adquirente = _make_contribuinte("20.000.023/0001-23", "Adquirente Cancel2")
    imovel = _make_imovel(transmitente, "TST-ITBI-CANCEL-02")
    reg = client.post(
        "/itbi/registrar",
        json={
            "transmitente_id": transmitente,
            "adquirente_id": adquirente,
            "imovel_id": imovel,
            "natureza_operacao": "doacao",
            "data_operacao": f"{YEAR}-06-01",
            "valor_declarado": 80000.0,
            "aliquota_itbi": 2.0,
        },
        headers=headers,
    )
    itbi_id = reg.json()["id"]
    client.patch(f"/itbi/{itbi_id}/cancelar", headers=headers)
    resp = client.patch(f"/itbi/{itbi_id}/cancelar", headers=headers)
    assert resp.status_code == 422


def test_relatorio_itbi_json():
    headers = auth_headers("admin1")
    resp = client.get("/itbi/relatorio", headers=headers)
    assert resp.status_code == 200
    assert "total" in resp.json()


def test_relatorio_itbi_csv():
    headers = auth_headers("admin1")
    resp = client.get("/itbi/relatorio?export=csv", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().splitlines()
    assert lines[0].startswith("numero,")
    assert len(lines) >= 2


def test_itbi_gera_lancamento_tributario():
    headers = auth_headers("admin1")
    transmitente = _make_contribuinte("20.000.030/0001-30", "Transmitente Lanc Check")
    adquirente = _make_contribuinte("20.000.031/0001-31", "Adquirente Lanc Check")
    imovel = _make_imovel(transmitente, "TST-ITBI-LANC-01", valor_venal=300000.0)
    resp = client.post(
        "/itbi/registrar",
        json={
            "transmitente_id": transmitente,
            "adquirente_id": adquirente,
            "imovel_id": imovel,
            "natureza_operacao": "permuta",
            "data_operacao": f"{YEAR}-07-01",
            "valor_declarado": 300000.0,
            "aliquota_itbi": 2.5,
        },
        headers=headers,
    )
    assert resp.status_code == 201
    lancamento_id = resp.json()["lancamento_id"]

    db = SessionLocal()
    lanc = db.get(LancamentoTributario, lancamento_id)
    assert lanc is not None
    assert lanc.tributo == "ITBI"
    assert lanc.valor_total == 7500.0   # 300000 * 2.5%
    assert lanc.contribuinte_id == adquirente
    assert lanc.imovel_id == imovel
    db.close()


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard_nfse_itbi():
    headers = auth_headers("admin1")
    resp = client.get("/nfse-itbi/dashboard", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "nfse" in data
    assert "itbi" in data
    nfse = data["nfse"]
    itbi = data["itbi"]
    assert nfse["emitidas"] >= 2       # seed has 2
    assert itbi["total"] >= 1          # seed has 1
    assert nfse["total_iss_emitido"] > 0
    assert itbi["total_pendente"] > 0


def test_dashboard_sem_auth():
    resp = client.get("/nfse-itbi/dashboard")
    assert resp.status_code == 401


# ── Seed data ─────────────────────────────────────────────────────────────────

def test_seed_nfse_emitidas():
    db = SessionLocal()
    notas = db.query(NotaFiscalServico).filter(NotaFiscalServico.status == "emitida").all()
    assert len(notas) >= 2
    for nota in notas:
        assert nota.lancamento_id is not None
        assert nota.valor_iss > 0
    db.close()


def test_seed_itbi_aberto():
    db = SessionLocal()
    ops = db.query(OperacaoITBI).filter(OperacaoITBI.status == "aberto").all()
    assert len(ops) >= 1
    for op in ops:
        assert op.lancamento_id is not None
        assert op.base_calculo >= op.valor_declarado
    db.close()
