"""Testes da integração Almoxarifado ↔ Compras.

Cobre: criação de recebimento, confirmação (gera entradas automáticas),
recusa, filtros, rastreabilidade nas movimentações e endpoints de procurement.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_integracao.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Commitment,
    Contract,
    Department,
    FiscalYear,
    ItemAlmoxarifado,
    MovimentacaoEstoque,
    ProcurementProcess,
    RecebimentoMaterial,
    Vendor,
)
from app.seed import seed_data

client = TestClient(app)

# IDs criados em setup_module e reutilizados em todos os testes
_PROC_ID: int = 0
_VENDOR_ID: int = 0
_CONTRACT_ID: int = 0
_COMMITMENT_ID: int = 0
_ITEM1_ID: int = 0
_ITEM2_ID: int = 0


def setup_module():
    global _PROC_ID, _VENDOR_ID, _CONTRACT_ID, _COMMITMENT_ID, _ITEM1_ID, _ITEM2_ID
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)

    # Números únicos para não conflitar com os criados por seed_data
    proc = ProcurementProcess(
        number="PE-INTEG-2026-001",
        object_description="Aquisição de material de escritório — Integração Test",
    )
    db.add(proc)
    db.flush()

    vendor = Vendor(name="Papelaria Integração Test", document="00.111.222/0001-88")
    db.add(vendor)
    db.flush()

    contract = Contract(
        number="CT-INTEG-2026-001",
        process_id=proc.id,
        vendor_id=vendor.id,
        start_date=date(2026, 1, 1),
        end_date=date(2026, 12, 31),
        amount=50000.0,
    )
    db.add(contract)
    db.flush()

    fy = db.query(FiscalYear).first()
    dept = db.query(Department).first()
    commitment = Commitment(
        number="EMP-INTEG-2026-001",
        description="Empenho material escritório integração",
        amount=5000.0,
        fiscal_year_id=fy.id,
        department_id=dept.id,
        vendor_id=vendor.id,
    )
    db.add(commitment)
    db.flush()

    item1 = ItemAlmoxarifado(
        codigo="INT-001",
        descricao="Papel A4 (resma) — Integração Test",
        unidade="RM",
        categoria="material_consumo",
        estoque_minimo=5.0,
        valor_unitario=25.0,
    )
    item2 = ItemAlmoxarifado(
        codigo="INT-002",
        descricao="Caneta esferográfica azul — Integração Test",
        unidade="CX",
        categoria="material_consumo",
        estoque_minimo=2.0,
        valor_unitario=12.0,
    )
    db.add_all([item1, item2])
    db.flush()

    _PROC_ID = proc.id
    _VENDOR_ID = vendor.id
    _CONTRACT_ID = contract.id
    _COMMITMENT_ID = commitment.id
    _ITEM1_ID = item1.id
    _ITEM2_ID = item2.id

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_integracao.db")
    except FileNotFoundError:
        pass


def auth_headers(username="admin1", password="demo123"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


H = auth_headers


def _get_rec_id(status="pendente"):
    db = SessionLocal()
    rec = (
        db.query(RecebimentoMaterial)
        .filter_by(processo_id=_PROC_ID, status=status)
        .order_by(RecebimentoMaterial.id.desc())
        .first()
    )
    db.close()
    return rec.id if rec else None


# ── Criação ───────────────────────────────────────────────────────────────────

def test_criar_recebimento_pendente():
    r = client.post("/almoxarifado/recebimentos", json={
        "processo_id": _PROC_ID,
        "contrato_id": _CONTRACT_ID,
        "vendor_id": _VENDOR_ID,
        "commitment_id": _COMMITMENT_ID,
        "nota_fiscal": "NF-88888",
        "data_recebimento": "2026-04-10",
        "observacoes": "Entrega conforme edital",
        "itens": [
            {"item_almoxarifado_id": _ITEM1_ID, "quantidade_recebida": 50.0, "valor_unitario": 26.50},
            {"item_almoxarifado_id": _ITEM2_ID, "quantidade_recebida": 20.0, "valor_unitario": 13.00},
        ],
    }, headers=H())
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "pendente"
    assert d["processo_id"] == _PROC_ID
    assert d["nota_fiscal"] == "NF-88888"
    assert len(d["itens"]) == 2
    # Estoque ainda não deve ter sido alterado
    db = SessionLocal()
    item1 = db.get(ItemAlmoxarifado, _ITEM1_ID)
    assert item1.estoque_atual == 0.0
    db.close()


def test_criar_recebimento_processo_inexistente():
    r = client.post("/almoxarifado/recebimentos", json={
        "processo_id": 99999,
        "nota_fiscal": "NF-X",
        "data_recebimento": "2026-04-10",
        "itens": [{"item_almoxarifado_id": _ITEM1_ID, "quantidade_recebida": 5.0, "valor_unitario": 25.0}],
    }, headers=H())
    assert r.status_code == 404


def test_criar_recebimento_sem_itens():
    r = client.post("/almoxarifado/recebimentos", json={
        "processo_id": _PROC_ID,
        "nota_fiscal": "NF-VAZIO",
        "data_recebimento": "2026-04-10",
        "itens": [],
    }, headers=H())
    assert r.status_code == 422


def test_criar_recebimento_item_inexistente():
    r = client.post("/almoxarifado/recebimentos", json={
        "processo_id": _PROC_ID,
        "nota_fiscal": "NF-GHOST",
        "data_recebimento": "2026-04-10",
        "itens": [{"item_almoxarifado_id": 99999, "quantidade_recebida": 5.0, "valor_unitario": 10.0}],
    }, headers=H())
    assert r.status_code == 404


# ── Confirmação ───────────────────────────────────────────────────────────────

def test_confirmar_recebimento():
    rec_id = _get_rec_id("pendente")
    assert rec_id is not None
    r = client.post(f"/almoxarifado/recebimentos/{rec_id}/confirmar", headers=H())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "conferido"
    for it in d["itens"]:
        assert it["movimentacao_id"] is not None
    db = SessionLocal()
    assert db.get(ItemAlmoxarifado, _ITEM1_ID).estoque_atual == 50.0
    assert db.get(ItemAlmoxarifado, _ITEM2_ID).estoque_atual == 20.0
    db.close()


def test_estoque_apos_confirmacao():
    r1 = client.get(f"/almoxarifado/saldo/{_ITEM1_ID}", headers=H())
    r2 = client.get(f"/almoxarifado/saldo/{_ITEM2_ID}", headers=H())
    assert r1.json()["estoque_atual"] == 50.0
    assert r2.json()["estoque_atual"] == 20.0


def test_movimentacao_tem_rastreabilidade_compras():
    r = client.get(f"/almoxarifado/movimentacoes?item_id={_ITEM1_ID}", headers=H())
    assert r.status_code == 200
    movs = r.json()["items"]
    assert len(movs) >= 1
    mov = movs[0]
    assert mov["processo_id"] == _PROC_ID
    assert mov["contrato_id"] == _CONTRACT_ID
    assert mov["recebimento_id"] is not None
    assert mov["tipo"] == "entrada"


def test_confirmar_recebimento_ja_conferido():
    rec_id = _get_rec_id("conferido")
    assert rec_id is not None
    r = client.post(f"/almoxarifado/recebimentos/{rec_id}/confirmar", headers=H())
    assert r.status_code == 422
    assert "conferido" in r.json()["detail"].lower()


# ── Recusa ────────────────────────────────────────────────────────────────────

def test_recusar_recebimento():
    cr = client.post("/almoxarifado/recebimentos", json={
        "processo_id": _PROC_ID,
        "vendor_id": _VENDOR_ID,
        "nota_fiscal": "NF-RECUSA",
        "data_recebimento": "2026-04-15",
        "itens": [{"item_almoxarifado_id": _ITEM1_ID, "quantidade_recebida": 5.0, "valor_unitario": 26.0}],
    }, headers=H())
    assert cr.status_code == 201
    rec_id = cr.json()["id"]

    rr = client.post(f"/almoxarifado/recebimentos/{rec_id}/recusar?motivo=Material+com+defeito", headers=H())
    assert rr.status_code == 200
    assert rr.json()["status"] == "recusado"
    # Estoque não muda em recusa
    assert client.get(f"/almoxarifado/saldo/{_ITEM1_ID}", headers=H()).json()["estoque_atual"] == 50.0


def test_confirmar_recebimento_recusado():
    rec_id = _get_rec_id("recusado")
    assert rec_id is not None
    r = client.post(f"/almoxarifado/recebimentos/{rec_id}/confirmar", headers=H())
    assert r.status_code == 422


# ── Filtros ───────────────────────────────────────────────────────────────────

def test_list_recebimentos():
    r = client.get("/almoxarifado/recebimentos", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2
    assert "items" in d


def test_filter_por_processo():
    r = client.get(f"/almoxarifado/recebimentos?processo_id={_PROC_ID}", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(rec["processo_id"] == _PROC_ID for rec in d["items"])


def test_filter_por_status_conferido():
    r = client.get("/almoxarifado/recebimentos?status=conferido", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(rec["status"] == "conferido" for rec in d["items"])


def test_filter_por_contrato():
    r = client.get(f"/almoxarifado/recebimentos?contrato_id={_CONTRACT_ID}", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_filter_por_periodo():
    r = client.get("/almoxarifado/recebimentos?data_inicio=2026-04-01&data_fim=2026-04-12", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_filter_por_vendor():
    r = client.get(f"/almoxarifado/recebimentos?vendor_id={_VENDOR_ID}", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_get_recebimento_detalhe():
    rec_id = _get_rec_id("conferido")
    assert rec_id is not None
    r = client.get(f"/almoxarifado/recebimentos/{rec_id}", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == rec_id
    assert len(d["itens"]) == 2


def test_get_recebimento_not_found():
    r = client.get("/almoxarifado/recebimentos/99999", headers=H())
    assert r.status_code == 404


# ── Procurement endpoints ─────────────────────────────────────────────────────

def test_procurement_process_recebimentos():
    r = client.get(f"/procurement/processes/{_PROC_ID}/recebimentos", headers=H())
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_procurement_contract_recebimentos():
    r = client.get(f"/procurement/contracts/{_CONTRACT_ID}/recebimentos", headers=H())
    assert r.status_code == 200
    data = r.json()
    assert isinstance(data, list)
    assert len(data) >= 1


def test_procurement_process_recebimentos_nao_existe():
    r = client.get("/procurement/processes/99999/recebimentos", headers=H())
    assert r.status_code == 404


# ── Custo médio ponderado ─────────────────────────────────────────────────────

def test_segunda_entrada_atualiza_custo_medio():
    cr = client.post("/almoxarifado/recebimentos", json={
        "processo_id": _PROC_ID,
        "vendor_id": _VENDOR_ID,
        "nota_fiscal": "NF-SEGUNDA",
        "data_recebimento": "2026-04-20",
        "itens": [{"item_almoxarifado_id": _ITEM1_ID, "quantidade_recebida": 50.0, "valor_unitario": 27.00}],
    }, headers=H())
    assert cr.status_code == 201
    rec_id = cr.json()["id"]

    cf = client.post(f"/almoxarifado/recebimentos/{rec_id}/confirmar", headers=H())
    assert cf.status_code == 200

    db = SessionLocal()
    item1 = db.get(ItemAlmoxarifado, _ITEM1_ID)
    assert item1.estoque_atual == 100.0
    # Custo médio: (50 * 26.50 + 50 * 27.00) / 100 = 26.75
    assert abs(item1.valor_unitario - 26.75) < 0.01
    db.close()


# ── Rastreabilidade ───────────────────────────────────────────────────────────

def test_movimentacoes_rastreabilidade_processo():
    db = SessionLocal()
    movs = db.query(MovimentacaoEstoque).filter(
        MovimentacaoEstoque.processo_id == _PROC_ID
    ).all()
    assert len(movs) >= 2
    for m in movs:
        assert m.processo_id == _PROC_ID
        assert m.recebimento_id is not None
        assert m.tipo == "entrada"
    db.close()
