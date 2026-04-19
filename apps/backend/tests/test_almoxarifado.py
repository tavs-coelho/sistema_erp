"""Testes do módulo Almoxarifado.

Cobre: cadastro de itens, entradas, saídas, saldo, histórico e dashboard.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_almoxarifado.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import ItemAlmoxarifado, MovimentacaoEstoque
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
        os.remove("./test_almoxarifado.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str = "admin1", password: str = "demo123") -> dict:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


H = auth_headers  # shorthand


# ── Itens — CRUD ──────────────────────────────────────────────────────────────

def test_create_item():
    r = client.post("/almoxarifado/itens", json={
        "codigo": "MAT-001",
        "descricao": "Papel A4 (resma 500 folhas)",
        "unidade": "RM",
        "categoria": "material_consumo",
        "estoque_minimo": 10.0,
        "valor_unitario": 25.50,
    }, headers=H())
    assert r.status_code == 201
    d = r.json()
    assert d["codigo"] == "MAT-001"
    assert d["estoque_atual"] == 0.0


def test_create_item_duplicata_rejeitada():
    r = client.post("/almoxarifado/itens", json={
        "codigo": "MAT-001",
        "descricao": "Outro item mesmo código",
        "unidade": "UN",
    }, headers=H())
    assert r.status_code == 400


def test_create_segundo_item():
    r = client.post("/almoxarifado/itens", json={
        "codigo": "MAT-002",
        "descricao": "Caneta esferográfica azul",
        "unidade": "CX",
        "categoria": "material_consumo",
        "estoque_minimo": 5.0,
        "valor_unitario": 12.00,
    }, headers=H())
    assert r.status_code == 201


def test_list_itens():
    r = client.get("/almoxarifado/itens", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert "total" in d
    assert d["total"] >= 2


def test_list_itens_search():
    r = client.get("/almoxarifado/itens?search=papel", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert any("papel" in i["descricao"].lower() for i in d["items"])


def test_list_itens_categoria():
    r = client.get("/almoxarifado/itens?categoria=material_consumo", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 2


def test_list_itens_csv():
    r = client.get("/almoxarifado/itens?export=csv", headers=H())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().split("\n")
    assert lines[0].startswith("id")
    assert len(lines) >= 3  # header + 2 itens


def test_get_item():
    r = client.get("/almoxarifado/itens/1", headers=H())
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_get_item_not_found():
    r = client.get("/almoxarifado/itens/9999", headers=H())
    assert r.status_code == 404


def test_update_item():
    r = client.put("/almoxarifado/itens/1", json={"descricao": "Papel A4 500fls (atualizado)"}, headers=H())
    assert r.status_code == 200
    assert "atualizado" in r.json()["descricao"]


# ── Entradas de Estoque ───────────────────────────────────────────────────────

def test_entrada_estoque():
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": 1,
        "tipo": "entrada",
        "quantidade": 50.0,
        "valor_unitario": 25.50,
        "data_movimentacao": "2026-04-01",
        "documento_ref": "NF-12345",
        "observacoes": "Compra exercício 2026",
    }, headers=H())
    assert r.status_code == 201
    d = r.json()
    assert d["tipo"] == "entrada"
    assert d["quantidade"] == 50.0
    assert d["valor_total"] == round(50.0 * 25.50, 2)
    assert d["saldo_pos"] == 50.0


def test_entrada_segunda():
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": 1,
        "tipo": "entrada",
        "quantidade": 20.0,
        "valor_unitario": 26.00,
        "data_movimentacao": "2026-04-05",
        "documento_ref": "NF-12346",
    }, headers=H())
    assert r.status_code == 201
    assert r.json()["saldo_pos"] == 70.0


def test_estoque_atual_atualizado_apos_entradas():
    r = client.get("/almoxarifado/itens/1", headers=H())
    assert r.json()["estoque_atual"] == 70.0


def test_entrada_para_item2():
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": 2,
        "tipo": "entrada",
        "quantidade": 30.0,
        "valor_unitario": 12.00,
        "data_movimentacao": "2026-04-02",
        "documento_ref": "NF-99999",
    }, headers=H())
    assert r.status_code == 201
    assert r.json()["saldo_pos"] == 30.0


# ── Saídas / Requisições ──────────────────────────────────────────────────────

def test_saida_estoque():
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": 1,
        "tipo": "saida",
        "quantidade": 10.0,
        "valor_unitario": 25.50,
        "data_movimentacao": "2026-04-10",
        "departamento_id": 1,
        "documento_ref": "REQ-001",
        "observacoes": "Requisição Saúde",
    }, headers=H())
    assert r.status_code == 201
    d = r.json()
    assert d["tipo"] == "saida"
    assert d["saldo_pos"] == 60.0


def test_saldo_apos_saida():
    r = client.get("/almoxarifado/saldo/1", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["estoque_atual"] == 60.0
    assert d["abaixo_minimo"] is False


def test_saida_saldo_insuficiente():
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": 1,
        "tipo": "saida",
        "quantidade": 9999.0,
        "valor_unitario": 0.0,
        "data_movimentacao": "2026-04-15",
    }, headers=H())
    assert r.status_code == 422
    assert "insuficiente" in r.json()["detail"].lower()


def test_saida_quantidade_zero_rejeitada():
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": 1,
        "tipo": "saida",
        "quantidade": 0.0,
        "valor_unitario": 0.0,
        "data_movimentacao": "2026-04-15",
    }, headers=H())
    assert r.status_code == 422


def test_saida_tipo_invalido():
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": 1,
        "tipo": "transferencia",
        "quantidade": 5.0,
        "valor_unitario": 0.0,
        "data_movimentacao": "2026-04-15",
    }, headers=H())
    assert r.status_code == 422


# ── Saldo e Dashboard ─────────────────────────────────────────────────────────

def test_saldo_abaixo_minimo():
    """Cria item com estoque_minimo alto e verifica alerta."""
    r = client.post("/almoxarifado/itens", json={
        "codigo": "MAT-003",
        "descricao": "Detergente",
        "unidade": "UN",
        "estoque_minimo": 100.0,
        "valor_unitario": 5.0,
    }, headers=H())
    assert r.status_code == 201
    item_id = r.json()["id"]
    # Sem entrada, saldo = 0 < 100 → abaixo_minimo = True
    sr = client.get(f"/almoxarifado/saldo/{item_id}", headers=H())
    assert sr.json()["abaixo_minimo"] is True


def test_list_itens_abaixo_minimo():
    r = client.get("/almoxarifado/itens?abaixo_minimo=true", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 1  # MAT-003 está abaixo


def test_dashboard():
    r = client.get("/almoxarifado/dashboard", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert "total_itens_ativos" in d
    assert "itens_abaixo_minimo" in d
    assert "valor_total_estoque" in d
    assert d["total_itens_ativos"] >= 3
    assert d["itens_abaixo_minimo"] >= 1


# ── Histórico / Movimentações ─────────────────────────────────────────────────

def test_list_movimentacoes():
    r = client.get("/almoxarifado/movimentacoes", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 4  # 2 entradas + 1 saída + 1 entrada item2


def test_filter_movimentacoes_por_item():
    r = client.get("/almoxarifado/movimentacoes?item_id=1", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert all(m["item_id"] == 1 for m in d["items"])
    assert d["total"] >= 3


def test_filter_movimentacoes_por_tipo():
    r = client.get("/almoxarifado/movimentacoes?tipo=entrada", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert all(m["tipo"] == "entrada" for m in d["items"])


def test_filter_movimentacoes_por_periodo():
    r = client.get("/almoxarifado/movimentacoes?data_inicio=2026-04-01&data_fim=2026-04-06", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2  # entradas de 1 e 2 de abril


def test_filter_movimentacoes_por_departamento():
    r = client.get("/almoxarifado/movimentacoes?departamento_id=1", headers=H())
    assert r.status_code == 200
    # Saída com departamento_id=1 deve aparecer
    assert r.json()["total"] >= 1


def test_movimentacoes_csv():
    r = client.get("/almoxarifado/movimentacoes?export=csv", headers=H())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().split("\n")
    assert lines[0].startswith("id")
    assert len(lines) >= 5  # header + 4 movimentações


def test_get_movimentacao():
    r = client.get("/almoxarifado/movimentacoes/1", headers=H())
    assert r.status_code == 200
    assert r.json()["id"] == 1


def test_get_movimentacao_not_found():
    r = client.get("/almoxarifado/movimentacoes/9999", headers=H())
    assert r.status_code == 404


# ── Inativação e exclusão ─────────────────────────────────────────────────────

def test_inativar_item():
    r = client.put("/almoxarifado/itens/1", json={"ativo": False}, headers=H())
    assert r.status_code == 200
    assert r.json()["ativo"] is False


def test_movimentar_item_inativo_rejeitado():
    r = client.post("/almoxarifado/movimentacoes", json={
        "item_id": 1,
        "tipo": "entrada",
        "quantidade": 10.0,
        "valor_unitario": 25.0,
        "data_movimentacao": "2026-04-20",
    }, headers=H())
    assert r.status_code == 422
    assert "inativo" in r.json()["detail"].lower()


def test_reativar_item():
    r = client.put("/almoxarifado/itens/1", json={"ativo": True}, headers=H())
    assert r.status_code == 200
    assert r.json()["ativo"] is True


def test_delete_item_com_movimentacoes_rejeitado():
    """Não pode excluir item que já tem movimentações."""
    r = client.delete("/almoxarifado/itens/1", headers=H())
    assert r.status_code == 409


def test_delete_item_novo_sem_movimentacoes():
    """Item sem movimentações pode ser excluído."""
    cr = client.post("/almoxarifado/itens", json={
        "codigo": "MAT-TMP",
        "descricao": "Temporário",
        "unidade": "UN",
    }, headers=H())
    assert cr.status_code == 201
    item_id = cr.json()["id"]
    dr = client.delete(f"/almoxarifado/itens/{item_id}", headers=H())
    assert dr.status_code == 204
