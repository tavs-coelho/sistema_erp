"""Testes — Alerta de Estoque Mínimo + Requisição de Compra.

Cobre: geração automática de alerta em saída abaixo do mínimo, idempotência
de alertas, criação de requisição vinculada a alerta, lifecycle completo
(rascunho → aprovada → vinculada a processo), cancelamento, filtros.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_alerta.db"

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AlertaEstoqueMinimo,
    Department,
    FiscalYear,
    ItemAlmoxarifado,
    ProcurementProcess,
    RequisicaoCompra,
)
from app.seed import seed_data

client = TestClient(app)

# IDs globais
_ITEM_ID: int = 0
_ITEM_SEM_MINIMO_ID: int = 0
_DEPT_ID: int = 0
_PROC_ID: int = 0


def setup_module():
    global _ITEM_ID, _ITEM_SEM_MINIMO_ID, _DEPT_ID, _PROC_ID
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)

    dept = db.query(Department).first()
    proc = ProcurementProcess(
        number="PE-ALERTA-001",
        object_description="Processo para vincular requisição",
    )
    db.add(proc)
    db.flush()

    # Item com estoque mínimo configurado (estoque_atual = 0, mínimo = 5)
    item = ItemAlmoxarifado(
        codigo="ALR-001",
        descricao="Resma de papel — Alerta Test",
        unidade="RM",
        categoria="material_consumo",
        estoque_minimo=5.0,
        estoque_atual=10.0,   # começamos acima do mínimo
        valor_unitario=25.0,
    )
    # Item sem estoque mínimo — não deve gerar alerta
    item_sem_min = ItemAlmoxarifado(
        codigo="ALR-002",
        descricao="Caneta — sem mínimo",
        unidade="UN",
        categoria="material_consumo",
        estoque_minimo=0.0,
        estoque_atual=50.0,
        valor_unitario=2.0,
    )
    db.add_all([item, item_sem_min])
    db.flush()

    _ITEM_ID = item.id
    _ITEM_SEM_MINIMO_ID = item_sem_min.id
    _DEPT_ID = dept.id
    _PROC_ID = proc.id

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_alerta.db")
    except FileNotFoundError:
        pass


def auth_headers(username="admin1", password="demo123"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": "Bearer " + token}


H = auth_headers


def _saida(item_id: int, quantidade: float):
    """Registra saída via endpoint."""
    from datetime import date
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": item_id,
        "tipo": "saida",
        "quantidade": quantidade,
        "valor_unitario": 0.0,
        "data_movimentacao": str(date.today()),
        "departamento_id": _DEPT_ID,
        "documento_ref": "REQ-TEST",
        "observacoes": "teste alerta",
    }, headers=H())
    return r


def _entrada(item_id: int, quantidade: float, valor: float = 0.0):
    from datetime import date
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": item_id,
        "tipo": "entrada",
        "quantidade": quantidade,
        "valor_unitario": valor,
        "data_movimentacao": str(date.today()),
        "departamento_id": None,
        "documento_ref": "REPOSICAO",
        "observacoes": "reposicao teste",
    }, headers=H())
    return r


# ── Geração Automática de Alerta ──────────────────────────────────────────────

def test_saida_acima_minimo_nao_gera_alerta():
    """Saída que mantém saldo >= mínimo não gera alerta."""
    r = _saida(_ITEM_ID, 3.0)  # 10 - 3 = 7, mínimo = 5, OK
    assert r.status_code == 201, r.text

    db = SessionLocal()
    alertas = db.query(AlertaEstoqueMinimo).filter_by(item_id=_ITEM_ID).all()
    assert len(alertas) == 0
    db.close()


def test_saida_abaixo_minimo_gera_alerta():
    """Saída que leva saldo abaixo do mínimo deve gerar alerta automático."""
    r = _saida(_ITEM_ID, 4.0)   # 7 - 4 = 3 < 5 (mínimo)
    assert r.status_code == 201, r.text

    db = SessionLocal()
    alertas = db.query(AlertaEstoqueMinimo).filter(
        AlertaEstoqueMinimo.item_id == _ITEM_ID,
        AlertaEstoqueMinimo.status == "aberto",
    ).all()
    assert len(alertas) == 1
    alerta = alertas[0]
    assert alerta.saldo_no_momento == 3.0
    assert alerta.estoque_minimo == 5.0
    db.close()


def test_saida_repetida_nao_duplica_alerta():
    """Segunda saída enquanto alerta aberto não cria segundo alerta."""
    r = _saida(_ITEM_ID, 1.0)   # 3 - 1 = 2
    assert r.status_code == 201, r.text

    db = SessionLocal()
    alertas = db.query(AlertaEstoqueMinimo).filter(
        AlertaEstoqueMinimo.item_id == _ITEM_ID,
        AlertaEstoqueMinimo.status == "aberto",
    ).all()
    assert len(alertas) == 1   # ainda só 1
    db.close()


def test_item_sem_minimo_nao_gera_alerta():
    """Item com estoque_mínimo=0 nunca deve gerar alerta."""
    r = _saida(_ITEM_SEM_MINIMO_ID, 48.0)
    assert r.status_code == 201

    db = SessionLocal()
    alertas = db.query(AlertaEstoqueMinimo).filter_by(item_id=_ITEM_SEM_MINIMO_ID).all()
    assert len(alertas) == 0
    db.close()


# ── Endpoints de Alertas ──────────────────────────────────────────────────────

def test_list_alertas():
    r = client.get("/almoxarifado/alertas", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert "items" in d


def test_filter_alertas_status():
    r = client.get("/almoxarifado/alertas?status=aberto", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(a["status"] == "aberto" for a in d["items"])


def test_filter_alertas_por_item():
    r = client.get(f"/almoxarifado/alertas?item_id={_ITEM_ID}", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(a["item_id"] == _ITEM_ID for a in d["items"])


def test_get_alerta_detalhe():
    db = SessionLocal()
    alerta = db.query(AlertaEstoqueMinimo).filter_by(item_id=_ITEM_ID).first()
    alerta_id = alerta.id
    db.close()

    r = client.get(f"/almoxarifado/alertas/{alerta_id}", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == alerta_id
    assert d["item_id"] == _ITEM_ID


def test_get_alerta_not_found():
    r = client.get("/almoxarifado/alertas/99999", headers=H())
    assert r.status_code == 404


# ── Requisição de Compra ──────────────────────────────────────────────────────

def _get_alerta_id():
    db = SessionLocal()
    alerta = db.query(AlertaEstoqueMinimo).filter_by(item_id=_ITEM_ID).first()
    db.close()
    return alerta.id if alerta else None


def test_criar_requisicao_com_alerta():
    alerta_id = _get_alerta_id()
    assert alerta_id is not None

    r = client.post("/almoxarifado/requisicoes", json={
        "item_id": _ITEM_ID,
        "departamento_id": _DEPT_ID,
        "alerta_id": alerta_id,
        "quantidade_sugerida": 20.0,
        "justificativa": "Estoque abaixo do mínimo — reposição urgente",
    }, headers=H())
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "rascunho"
    assert d["item_id"] == _ITEM_ID
    assert d["alerta_id"] == alerta_id
    assert d["quantidade_sugerida"] == 20.0

    # Alerta deve ter mudado para em_processo
    db = SessionLocal()
    alerta = db.get(AlertaEstoqueMinimo, alerta_id)
    assert alerta.status == "em_processo"
    db.close()


def test_criar_requisicao_sem_alerta():
    """Requisição pode ser criada sem alerta vinculado (demanda direta)."""
    r = client.post("/almoxarifado/requisicoes", json={
        "item_id": _ITEM_ID,
        "departamento_id": _DEPT_ID,
        "quantidade_sugerida": 10.0,
        "justificativa": "Demanda direta de departamento",
    }, headers=H())
    assert r.status_code == 201
    assert r.json()["status"] == "rascunho"
    assert r.json()["alerta_id"] is None


def test_criar_requisicao_item_inexistente():
    r = client.post("/almoxarifado/requisicoes", json={
        "item_id": 99999,
        "quantidade_sugerida": 5.0,
    }, headers=H())
    assert r.status_code == 404


def test_criar_requisicao_quantidade_invalida():
    r = client.post("/almoxarifado/requisicoes", json={
        "item_id": _ITEM_ID,
        "quantidade_sugerida": 0.0,
    }, headers=H())
    assert r.status_code == 422


def test_criar_requisicao_alerta_item_errado():
    """alerta_id pertencente a item diferente deve ser rejeitado."""
    alerta_id = _get_alerta_id()
    r = client.post("/almoxarifado/requisicoes", json={
        "item_id": _ITEM_SEM_MINIMO_ID,   # item diferente do alerta
        "alerta_id": alerta_id,
        "quantidade_sugerida": 5.0,
    }, headers=H())
    assert r.status_code == 422


# ── Lifecycle da Requisição ───────────────────────────────────────────────────

def _get_req_id(status="rascunho"):
    db = SessionLocal()
    req = db.query(RequisicaoCompra).filter_by(status=status).order_by(
        RequisicaoCompra.id.desc()
    ).first()
    db.close()
    return req.id if req else None


def test_aprovar_requisicao():
    req_id = _get_req_id("rascunho")
    assert req_id is not None

    r = client.post(f"/almoxarifado/requisicoes/{req_id}/aprovar", headers=H())
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "aprovada"


def test_aprovar_requisicao_ja_aprovada():
    req_id = _get_req_id("aprovada")
    assert req_id is not None
    r = client.post(f"/almoxarifado/requisicoes/{req_id}/aprovar", headers=H())
    assert r.status_code == 422


def test_vincular_processo():
    req_id = _get_req_id("aprovada")
    assert req_id is not None

    r = client.post(f"/almoxarifado/requisicoes/{req_id}/vincular-processo",
                    json={"processo_id": _PROC_ID}, headers=H())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "vinculada"
    assert d["processo_id"] == _PROC_ID

    # Alerta deve ter sido resolvido ao vincular
    alerta_id = d.get("alerta_id")
    if alerta_id:
        db = SessionLocal()
        alerta = db.get(AlertaEstoqueMinimo, alerta_id)
        assert alerta.status == "resolvido"
        db.close()


def test_vincular_processo_inexistente():
    req_id = _get_req_id("rascunho")
    if req_id is None:
        # Cria uma nova rascunho para ter algo para vincular
        r = client.post("/almoxarifado/requisicoes", json={
            "item_id": _ITEM_ID, "quantidade_sugerida": 5.0,
        }, headers=H())
        req_id = r.json()["id"]

    r = client.post(f"/almoxarifado/requisicoes/{req_id}/vincular-processo",
                    json={"processo_id": 99999}, headers=H())
    assert r.status_code == 404


def test_cancelar_requisicao():
    # Cria nova rascunho para cancelar
    cr = client.post("/almoxarifado/requisicoes", json={
        "item_id": _ITEM_ID,
        "quantidade_sugerida": 7.0,
        "justificativa": "Para cancelar",
    }, headers=H())
    assert cr.status_code == 201
    req_id = cr.json()["id"]

    r = client.post(f"/almoxarifado/requisicoes/{req_id}/cancelar", headers=H())
    assert r.status_code == 200
    assert r.json()["status"] == "cancelada"


def test_cancelar_requisicao_ja_cancelada():
    req_id = _get_req_id("cancelada")
    assert req_id is not None
    r = client.post(f"/almoxarifado/requisicoes/{req_id}/cancelar", headers=H())
    assert r.status_code == 422


# ── Filtros de Requisições ────────────────────────────────────────────────────

def test_list_requisicoes():
    r = client.get("/almoxarifado/requisicoes", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2
    assert "items" in d


def test_filter_requisicoes_por_status():
    r = client.get("/almoxarifado/requisicoes?status=vinculada", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(req["status"] == "vinculada" for req in d["items"])


def test_filter_requisicoes_por_item():
    r = client.get(f"/almoxarifado/requisicoes?item_id={_ITEM_ID}", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_get_requisicao_detalhe():
    req_id = _get_req_id("vinculada")
    assert req_id is not None
    r = client.get(f"/almoxarifado/requisicoes/{req_id}", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == req_id


def test_get_requisicao_not_found():
    r = client.get("/almoxarifado/requisicoes/99999", headers=H())
    assert r.status_code == 404


# ── Resolver Alerta Manualmente ───────────────────────────────────────────────

def test_resolver_alerta_manual():
    """Alerta aberto pode ser resolvido manualmente pelo gestor."""
    # Forçar novo alerta em item diferente
    from datetime import date
    # Reabastece e depois consome para criar novo alerta
    _entrada(_ITEM_SEM_MINIMO_ID, 10.0)
    db = SessionLocal()
    item = db.get(ItemAlmoxarifado, _ITEM_SEM_MINIMO_ID)
    item.estoque_minimo = 5.0
    db.commit()
    db.close()

    _saida(_ITEM_SEM_MINIMO_ID, 8.0)  # deve gerar alerta (2 < 5)

    db = SessionLocal()
    alerta = db.query(AlertaEstoqueMinimo).filter_by(
        item_id=_ITEM_SEM_MINIMO_ID, status="aberto"
    ).first()
    alerta_id = alerta.id if alerta else None
    db.close()

    assert alerta_id is not None
    r = client.post(f"/almoxarifado/alertas/{alerta_id}/resolver", headers=H())
    assert r.status_code == 200
    assert r.json()["status"] == "resolvido"
    assert r.json()["resolvido_em"] is not None


def test_resolver_alerta_ja_resolvido():
    db = SessionLocal()
    alerta = db.query(AlertaEstoqueMinimo).filter_by(status="resolvido").first()
    alerta_id = alerta.id if alerta else None
    db.close()

    if alerta_id:
        r = client.post(f"/almoxarifado/alertas/{alerta_id}/resolver", headers=H())
        assert r.status_code == 422


# ── Novo alerta após resolução ────────────────────────────────────────────────

def test_novo_alerta_apos_resolucao():
    """Após resolver o alerta e o item cair abaixo do mínimo novamente, deve gerar novo alerta."""
    # Resolve o alerta atual do _ITEM_ID se houver
    db = SessionLocal()
    alertas_abertos = db.query(AlertaEstoqueMinimo).filter(
        AlertaEstoqueMinimo.item_id == _ITEM_ID,
        AlertaEstoqueMinimo.status.in_(["aberto", "em_processo"]),
    ).all()
    for a in alertas_abertos:
        from app.models import utc_now
        a.status = "resolvido"
        a.resolvido_em = utc_now()
    db.commit()
    # Repõe estoque acima do mínimo
    item = db.get(ItemAlmoxarifado, _ITEM_ID)
    item.estoque_atual = 20.0
    db.commit()
    db.close()

    # Saída que derruba abaixo do mínimo
    r = _saida(_ITEM_ID, 17.0)   # 20 - 17 = 3 < 5
    assert r.status_code == 201

    db = SessionLocal()
    novos = db.query(AlertaEstoqueMinimo).filter(
        AlertaEstoqueMinimo.item_id == _ITEM_ID,
        AlertaEstoqueMinimo.status == "aberto",
    ).all()
    assert len(novos) == 1
    db.close()
