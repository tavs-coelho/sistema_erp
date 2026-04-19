"""Testes de Protocolo/Processos Administrativos e Convênios."""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_protocolo.db"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Convenio, ConvenioDesembolso, Protocolo, TramitacaoProtocolo
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
        os.remove("./test_protocolo.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ── Protocolo — criação e listagem ───────────────────────────────────────────

def test_create_protocolo_returns_201_like_data():
    headers = auth_headers("admin1")
    resp = client.post(
        "/protocolo/protocolos",
        json={
            "numero": "PROT-2026-001",
            "tipo": "requerimento",
            "assunto": "Solicitação de alvará de funcionamento",
            "interessado": "João da Silva",
            "interessado_doc": "123.456.789-00",
            "status": "protocolado",
            "prioridade": "normal",
            "data_entrada": "2026-01-10",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["numero"] == "PROT-2026-001"
    assert data["status"] == "protocolado"
    assert data["tipo"] == "requerimento"


def test_create_protocolo_duplicate_numero_returns_409():
    headers = auth_headers("admin1")
    payload = {
        "numero": "PROT-DUP-001",
        "tipo": "oficio",
        "assunto": "Teste",
        "interessado": "Interessado X",
        "data_entrada": "2026-01-15",
    }
    client.post("/protocolo/protocolos", json=payload, headers=headers)
    resp = client.post("/protocolo/protocolos", json=payload, headers=headers)
    assert resp.status_code == 409


def test_list_protocolos_returns_paginated():
    headers = auth_headers("admin1")
    resp = client.get("/protocolo/protocolos?page=1&size=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data and "items" in data
    assert data["total"] >= 1


def test_get_protocolo_by_id():
    headers = auth_headers("admin1")
    create = client.post(
        "/protocolo/protocolos",
        json={"numero": "PROT-GET-001", "tipo": "recurso", "assunto": "Recurso de multa", "interessado": "Maria Souza", "data_entrada": "2026-02-01"},
        headers=headers,
    )
    pid = create.json()["id"]
    resp = client.get(f"/protocolo/protocolos/{pid}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["numero"] == "PROT-GET-001"


def test_get_protocolo_unknown_returns_404():
    headers = auth_headers("admin1")
    resp = client.get("/protocolo/protocolos/999999", headers=headers)
    assert resp.status_code == 404


def test_filter_protocolos_by_status():
    headers = auth_headers("admin1")
    resp = client.get("/protocolo/protocolos?status=protocolado&page=1&size=20", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["status"] == "protocolado" for i in items)


def test_filter_protocolos_by_search():
    headers = auth_headers("admin1")
    # Cria protocolo com assunto único
    client.post(
        "/protocolo/protocolos",
        json={"numero": "PROT-SEARCH-001", "tipo": "oficio", "assunto": "Licença ambiental XYZABC", "interessado": "Empresa ABC", "data_entrada": "2026-03-01"},
        headers=headers,
    )
    resp = client.get("/protocolo/protocolos?search=XYZABC&page=1&size=10", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["total"] >= 1
    assert any("XYZABC" in i["assunto"] for i in resp.json()["items"])


# ── Protocolo — workflow de tramitação ───────────────────────────────────────

def test_tramitar_protocolo_end_to_end():
    headers = auth_headers("admin1")

    # Criar protocolo
    prot = client.post(
        "/protocolo/protocolos",
        json={"numero": "PROT-TRAM-001", "tipo": "requerimento", "assunto": "Alvará de obras", "interessado": "Construtora Beta", "data_entrada": "2026-04-01", "destino_department_id": 1},
        headers=headers,
    ).json()
    pid = prot["id"]

    # Tramitar para outro departamento
    tram_resp = client.post(
        f"/protocolo/protocolos/{pid}/tramitar",
        json={"para_department_id": 1, "acao": "encaminhado", "despacho": "Encaminhar para análise técnica."},
        headers=headers,
    )
    assert tram_resp.status_code == 200
    assert tram_resp.json()["acao"] == "encaminhado"

    # Verificar status no banco
    db = SessionLocal()
    try:
        p = db.get(Protocolo, pid)
        assert p.status == "em_tramitacao"
    finally:
        db.close()

    # Deferir
    defer_resp = client.post(
        f"/protocolo/protocolos/{pid}/tramitar",
        json={"para_department_id": 1, "acao": "deferido", "despacho": "Aprovado conforme normas técnicas."},
        headers=headers,
    )
    assert defer_resp.status_code == 200
    assert defer_resp.json()["acao"] == "deferido"

    # Verificar que o protocolo foi deferido
    db = SessionLocal()
    try:
        p = db.get(Protocolo, pid)
        assert p.status == "deferido"
    finally:
        db.close()


def test_tramitacao_invalida_retorna_422():
    """Não deve ser possível deferir um protocolo já arquivado."""
    headers = auth_headers("admin1")
    prot = client.post(
        "/protocolo/protocolos",
        json={"numero": "PROT-INV-001", "tipo": "oficio", "assunto": "Teste de transição inválida", "interessado": "Teste", "data_entrada": "2026-04-05"},
        headers=headers,
    ).json()
    pid = prot["id"]

    # Arquivar direto
    client.patch(f"/protocolo/protocolos/{pid}", json={"status": "arquivado"}, headers=headers)

    # Tentar deferir um protocolo arquivado
    resp = client.post(
        f"/protocolo/protocolos/{pid}/tramitar",
        json={"para_department_id": 1, "acao": "encaminhado", "despacho": ""},
        headers=headers,
    )
    assert resp.status_code == 422


def test_list_tramitacoes_do_protocolo():
    headers = auth_headers("admin1")
    prot = client.post(
        "/protocolo/protocolos",
        json={"numero": "PROT-LISTTRAM-001", "tipo": "requerimento", "assunto": "Listar tramitações", "interessado": "Alguém", "data_entrada": "2026-04-10"},
        headers=headers,
    ).json()
    pid = prot["id"]

    client.post(f"/protocolo/protocolos/{pid}/tramitar", json={"para_department_id": 1, "acao": "encaminhado", "despacho": "Para análise"}, headers=headers)
    client.post(f"/protocolo/protocolos/{pid}/tramitar", json={"para_department_id": 1, "acao": "deferido", "despacho": "Aprovado"}, headers=headers)

    resp = client.get(f"/protocolo/protocolos/{pid}/tramitacoes", headers=headers)
    assert resp.status_code == 200
    assert len(resp.json()) == 2


def test_patch_protocolo_campos():
    headers = auth_headers("admin1")
    prot = client.post(
        "/protocolo/protocolos",
        json={"numero": "PROT-PATCH-001", "tipo": "requerimento", "assunto": "Assunto original", "interessado": "Pedro", "data_entrada": "2026-04-15"},
        headers=headers,
    ).json()
    pid = prot["id"]

    resp = client.patch(f"/protocolo/protocolos/{pid}", json={"assunto": "Assunto corrigido", "prioridade": "urgente"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["assunto"] == "Assunto corrigido"
    assert resp.json()["prioridade"] == "urgente"


def test_estatisticas_retorna_contagens_por_status():
    headers = auth_headers("admin1")
    resp = client.get("/protocolo/estatisticas", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, dict)
    # Deve haver ao menos uma chave de status
    assert len(data) >= 1


# ── Convênios — criação e gestão ─────────────────────────────────────────────

def test_create_convenio_end_to_end():
    headers = auth_headers("admin1")
    resp = client.post(
        "/convenios",
        json={
            "numero": "CONV-2026-001",
            "objeto": "Construção de escola municipal",
            "tipo": "recebimento",
            "concedente": "Ministério da Educação",
            "cnpj_concedente": "00.000.000/0001-00",
            "valor_total": 500000.0,
            "contrapartida": 50000.0,
            "data_assinatura": "2026-01-05",
            "data_inicio": "2026-02-01",
            "data_fim": "2027-01-31",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["numero"] == "CONV-2026-001"
    assert data["valor_total"] == 500000.0


def test_create_convenio_duplicate_returns_409():
    headers = auth_headers("admin1")
    payload = {
        "numero": "CONV-DUP-001",
        "objeto": "Duplicata",
        "concedente": "Órgão X",
        "valor_total": 100000.0,
        "data_assinatura": "2026-01-01",
        "data_inicio": "2026-02-01",
        "data_fim": "2026-12-31",
    }
    client.post("/convenios", json=payload, headers=headers)
    resp = client.post("/convenios", json=payload, headers=headers)
    assert resp.status_code == 409


def test_list_convenios_returns_paginated():
    headers = auth_headers("admin1")
    resp = client.get("/convenios?page=1&size=5", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "total" in data and "items" in data


def test_get_convenio_by_id():
    headers = auth_headers("admin1")
    create = client.post(
        "/convenios",
        json={"numero": "CONV-GET-001", "objeto": "Pavimentação", "concedente": "Estado X", "valor_total": 200000.0, "data_assinatura": "2026-01-10", "data_inicio": "2026-03-01", "data_fim": "2026-12-31"},
        headers=headers,
    ).json()
    cid = create["id"]
    resp = client.get(f"/convenios/{cid}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["numero"] == "CONV-GET-001"


def test_update_convenio_status():
    headers = auth_headers("admin1")
    create = client.post(
        "/convenios",
        json={"numero": "CONV-PATCH-001", "objeto": "Saúde", "concedente": "MS", "valor_total": 300000.0, "data_assinatura": "2026-01-01", "data_inicio": "2026-02-01", "data_fim": "2026-12-31"},
        headers=headers,
    ).json()
    cid = create["id"]
    resp = client.patch(f"/convenios/{cid}", json={"status": "encerrado"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "encerrado"


def test_desembolsos_workflow_completo():
    headers = auth_headers("admin1")

    # Criar convênio
    conv = client.post(
        "/convenios",
        json={
            "numero": "CONV-DESEMB-001",
            "objeto": "Obras de saneamento",
            "concedente": "FUNASA",
            "valor_total": 600000.0,
            "contrapartida": 60000.0,
            "data_assinatura": "2026-01-15",
            "data_inicio": "2026-03-01",
            "data_fim": "2027-02-28",
        },
        headers=headers,
    ).json()
    cid = conv["id"]

    # Adicionar 2 desembolsos
    d1 = client.post(f"/convenios/{cid}/desembolsos", json={"numero_parcela": 1, "valor": 300000.0, "data_prevista": "2026-06-01"}, headers=headers)
    assert d1.status_code == 200
    d1_id = d1.json()["id"]

    d2 = client.post(f"/convenios/{cid}/desembolsos", json={"numero_parcela": 2, "valor": 300000.0, "data_prevista": "2026-12-01"}, headers=headers)
    assert d2.status_code == 200

    # Listar desembolsos
    list_resp = client.get(f"/convenios/{cid}/desembolsos", headers=headers)
    assert list_resp.status_code == 200
    assert len(list_resp.json()) == 2

    # Registrar recebimento da primeira parcela
    recv_resp = client.patch(
        f"/convenios/{cid}/desembolsos/{d1_id}",
        params={"data_efetiva": "2026-06-05", "status": "recebido"},
        headers=headers,
    )
    assert recv_resp.status_code == 200
    assert recv_resp.json()["status"] == "recebido"
    assert recv_resp.json()["data_efetiva"] == "2026-06-05"

    # Verificar banco
    db = SessionLocal()
    try:
        desembolso = db.get(ConvenioDesembolso, d1_id)
        assert desembolso.status == "recebido"
    finally:
        db.close()


def test_saldo_convenio():
    headers = auth_headers("admin1")

    conv = client.post(
        "/convenios",
        json={"numero": "CONV-SALDO-001", "objeto": "Habitação", "concedente": "Caixa", "valor_total": 400000.0, "data_assinatura": "2026-02-01", "data_inicio": "2026-03-01", "data_fim": "2027-12-31"},
        headers=headers,
    ).json()
    cid = conv["id"]

    # Adicionar desembolsos
    d1 = client.post(f"/convenios/{cid}/desembolsos", json={"numero_parcela": 1, "valor": 200000.0, "data_prevista": "2026-06-01"}, headers=headers).json()
    client.post(f"/convenios/{cid}/desembolsos", json={"numero_parcela": 2, "valor": 200000.0, "data_prevista": "2026-12-01"}, headers=headers)

    # Receber a primeira parcela
    client.patch(f"/convenios/{cid}/desembolsos/{d1['id']}", params={"data_efetiva": "2026-06-10", "status": "recebido"}, headers=headers)

    # Verificar saldo
    saldo = client.get(f"/convenios/{cid}/saldo", headers=headers)
    assert saldo.status_code == 200
    data = saldo.json()
    assert data["total_previsto_parcelas"] == 400000.0
    assert data["total_recebido"] == 200000.0
    assert data["saldo_pendente"] == 200000.0
    assert data["percentual_recebido"] == 50.0


def test_convenios_vencendo():
    headers = auth_headers("admin1")
    resp = client.get("/convenios/vencendo", headers=headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


def test_filter_convenios_by_tipo():
    headers = auth_headers("admin1")
    client.post(
        "/convenios",
        json={"numero": "CONV-TIPO-001", "objeto": "Repasse saúde", "tipo": "repasse", "concedente": "MS", "valor_total": 100000.0, "data_assinatura": "2026-01-01", "data_inicio": "2026-02-01", "data_fim": "2026-12-31"},
        headers=headers,
    )
    resp = client.get("/convenios?tipo=repasse&page=1&size=10", headers=headers)
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(i["tipo"] == "repasse" for i in items)
