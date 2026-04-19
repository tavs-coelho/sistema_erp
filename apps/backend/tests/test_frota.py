"""Testes do módulo Frota.

Cobre: cadastro de veículos, abastecimentos, manutenções (com e sem almoxarifado),
dashboard, consumo por veículo, lifecycle de manutenção, integração almoxarifado.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_frota.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AlertaEstoqueMinimo,
    Department,
    ItemAlmoxarifado,
    ManutencaoVeiculo,
    Veiculo,
)
from app.seed import seed_data

client = TestClient(app)

# Globals
_DEPT_ID: int = 0
_ITEM_ID: int = 0
_VEICULO_ID: int = 0
_VEICULO2_ID: int = 0


def setup_module():
    global _DEPT_ID, _ITEM_ID, _VEICULO_ID, _VEICULO2_ID
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)

    dept = db.query(Department).first()
    _DEPT_ID = dept.id

    item = ItemAlmoxarifado(
        codigo="FROTA-001",
        descricao="Óleo Motor 5W30 — Frota",
        unidade="L",
        categoria="material_consumo",
        estoque_minimo=5.0,
        estoque_atual=20.0,
        valor_unitario=30.0,
    )
    db.add(item)
    db.flush()
    _ITEM_ID = item.id

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_frota.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str = "admin1", password: str = "demo123") -> dict:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


H = auth_headers


# ── Veículos — CRUD ───────────────────────────────────────────────────────────

def test_criar_veiculo():
    global _VEICULO_ID
    r = client.post("/frota/veiculos", json={
        "placa": "ABC-1234",
        "descricao": "Caminhonete Ford Ranger 2022",
        "tipo": "leve",
        "marca": "Ford",
        "modelo": "Ranger XLS",
        "ano_fabricacao": 2022,
        "combustivel": "diesel",
        "odometro_atual": 15000.0,
        "departamento_id": _DEPT_ID,
    }, headers=H())
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["placa"] == "ABC-1234"
    assert d["status"] == "ativo"
    _VEICULO_ID = d["id"]


def test_criar_veiculo_placa_duplicada():
    r = client.post("/frota/veiculos", json={
        "placa": "ABC-1234",
        "descricao": "Outro veículo",
        "tipo": "leve",
        "combustivel": "flex",
    }, headers=H())
    assert r.status_code == 422


def test_criar_veiculo_tipo_invalido():
    r = client.post("/frota/veiculos", json={
        "placa": "ZZZ-9999",
        "descricao": "X",
        "tipo": "navio",
        "combustivel": "flex",
    }, headers=H())
    assert r.status_code == 422


def test_criar_segundo_veiculo():
    global _VEICULO2_ID
    r = client.post("/frota/veiculos", json={
        "placa": "XYZ-5678",
        "descricao": "Ônibus Escolar 2019",
        "tipo": "onibus",
        "marca": "Mercedes",
        "modelo": "OF 1418",
        "combustivel": "diesel",
        "odometro_atual": 80000.0,
        "departamento_id": _DEPT_ID,
    }, headers=H())
    assert r.status_code == 201
    _VEICULO2_ID = r.json()["id"]


def test_list_veiculos():
    r = client.get("/frota/veiculos", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 2
    assert "items" in d


def test_filter_veiculos_por_tipo():
    r = client.get("/frota/veiculos?tipo=onibus", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1
    assert all(v["tipo"] == "onibus" for v in d["items"])


def test_filter_veiculos_search():
    r = client.get("/frota/veiculos?search=ranger", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_get_veiculo_detalhe():
    r = client.get(f"/frota/veiculos/{_VEICULO_ID}", headers=H())
    assert r.status_code == 200
    assert r.json()["id"] == _VEICULO_ID


def test_get_veiculo_not_found():
    r = client.get("/frota/veiculos/99999", headers=H())
    assert r.status_code == 404


def test_atualizar_veiculo():
    r = client.patch(f"/frota/veiculos/{_VEICULO_ID}",
                     json={"odometro_atual": 16000.0, "observacoes": "Revisão feita"},
                     headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["odometro_atual"] == 16000.0
    assert d["observacoes"] == "Revisão feita"


# ── Abastecimentos ────────────────────────────────────────────────────────────

_ABAST_ID: int = 0


def test_registrar_abastecimento():
    global _ABAST_ID
    r = client.post("/frota/abastecimentos", json={
        "veiculo_id": _VEICULO_ID,
        "data_abastecimento": str(date.today()),
        "combustivel": "diesel",
        "litros": 50.0,
        "valor_litro": 6.50,
        "odometro": 16200.0,
        "posto": "Posto Expresso",
        "nota_fiscal": "NF-001",
        "departamento_id": _DEPT_ID,
    }, headers=H())
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["litros"] == 50.0
    assert d["valor_total"] == round(50.0 * 6.50, 2)
    _ABAST_ID = d["id"]


def test_abastecimento_atualiza_odometro():
    """Odômetro do veículo deve ser atualizado se novo valor for maior."""
    db = SessionLocal()
    v = db.get(Veiculo, _VEICULO_ID)
    assert v.odometro_atual == 16200.0
    db.close()


def test_abastecimento_litros_invalidos():
    r = client.post("/frota/abastecimentos", json={
        "veiculo_id": _VEICULO_ID,
        "data_abastecimento": str(date.today()),
        "combustivel": "diesel",
        "litros": 0.0,
        "valor_litro": 6.50,
    }, headers=H())
    assert r.status_code == 422


def test_abastecimento_veiculo_inexistente():
    r = client.post("/frota/abastecimentos", json={
        "veiculo_id": 99999,
        "data_abastecimento": str(date.today()),
        "combustivel": "diesel",
        "litros": 10.0,
        "valor_litro": 6.0,
    }, headers=H())
    assert r.status_code == 404


def test_list_abastecimentos():
    r = client.get("/frota/abastecimentos", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1


def test_filter_abastecimentos_veiculo():
    r = client.get(f"/frota/abastecimentos?veiculo_id={_VEICULO_ID}", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_get_abastecimento_detalhe():
    r = client.get(f"/frota/abastecimentos/{_ABAST_ID}", headers=H())
    assert r.status_code == 200
    assert r.json()["id"] == _ABAST_ID


def test_get_abastecimento_not_found():
    r = client.get("/frota/abastecimentos/99999", headers=H())
    assert r.status_code == 404


# ── Manutenções ───────────────────────────────────────────────────────────────

_MAN_ID: int = 0
_MAN2_ID: int = 0


def test_abrir_manutencao_sem_itens():
    global _MAN_ID
    r = client.post("/frota/manutencoes", json={
        "veiculo_id": _VEICULO_ID,
        "tipo": "preventiva",
        "descricao": "Troca de óleo e filtro",
        "data_abertura": str(date.today()),
        "odometro": 16200.0,
        "oficina": "Oficina Central",
        "departamento_id": _DEPT_ID,
    }, headers=H())
    assert r.status_code == 201, r.text
    d = r.json()
    assert d["status"] == "aberta"
    assert d["itens"] == []
    _MAN_ID = d["id"]


def test_manutencao_muda_status_veiculo():
    """Ao abrir manutenção, veículo deve ficar status='manutencao'."""
    db = SessionLocal()
    v = db.get(Veiculo, _VEICULO_ID)
    assert v.status == "manutencao"
    db.close()


def test_abrir_manutencao_com_item_almoxarifado():
    """Manutenção com peça do almoxarifado deve gerar saída de estoque."""
    global _MAN2_ID
    r = client.post("/frota/manutencoes", json={
        "veiculo_id": _VEICULO2_ID,
        "tipo": "corretiva",
        "descricao": "Troca de óleo",
        "data_abertura": str(date.today()),
        "departamento_id": _DEPT_ID,
        "itens": [{
            "descricao": "Óleo Motor 5W30",
            "quantidade": 5.0,
            "valor_unitario": 30.0,
            "item_almoxarifado_id": _ITEM_ID,
        }],
    }, headers=H())
    assert r.status_code == 201, r.text
    d = r.json()
    assert len(d["itens"]) == 1
    assert d["itens"][0]["item_almoxarifado_id"] == _ITEM_ID
    assert d["itens"][0]["movimentacao_id"] is not None
    _MAN2_ID = d["id"]

    # Verifica saída no almoxarifado (20 - 5 = 15)
    db = SessionLocal()
    item = db.get(ItemAlmoxarifado, _ITEM_ID)
    assert item.estoque_atual == 15.0
    db.close()


def test_manutencao_com_item_saldo_insuficiente():
    r = client.post("/frota/manutencoes", json={
        "veiculo_id": _VEICULO2_ID,
        "tipo": "preventiva",
        "descricao": "Troca de filtro",
        "data_abertura": str(date.today()),
        "itens": [{
            "descricao": "Óleo em excesso",
            "quantidade": 100.0,  # muito mais que o estoque
            "valor_unitario": 30.0,
            "item_almoxarifado_id": _ITEM_ID,
        }],
    }, headers=H())
    assert r.status_code == 422


def test_manutencao_tipo_invalido():
    r = client.post("/frota/manutencoes", json={
        "veiculo_id": _VEICULO_ID,
        "tipo": "reforma",
        "descricao": "X",
        "data_abertura": str(date.today()),
    }, headers=H())
    assert r.status_code == 422


def test_list_manutencoes():
    r = client.get("/frota/manutencoes", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["total"] >= 1


def test_filter_manutencoes_status():
    r = client.get("/frota/manutencoes?status=aberta", headers=H())
    assert r.status_code == 200
    assert r.json()["total"] >= 1
    assert all(m["status"] == "aberta" for m in r.json()["items"])


def test_get_manutencao_detalhe():
    r = client.get(f"/frota/manutencoes/{_MAN_ID}", headers=H())
    assert r.status_code == 200
    assert r.json()["id"] == _MAN_ID


def test_get_manutencao_not_found():
    r = client.get("/frota/manutencoes/99999", headers=H())
    assert r.status_code == 404


def test_adicionar_item_manutencao_aberta():
    """Adicionar peça depois da abertura (sem almoxarifado)."""
    r = client.post(f"/frota/manutencoes/{_MAN_ID}/itens", json={
        "descricao": "Filtro de óleo",
        "quantidade": 1.0,
        "valor_unitario": 45.0,
    }, headers=H())
    assert r.status_code == 201, r.text
    assert len(r.json()["itens"]) == 1


def test_adicionar_item_manutencao_almoxarifado():
    """Adicionar peça com vínculo almoxarifado em manutenção aberta."""
    r = client.post(f"/frota/manutencoes/{_MAN_ID}/itens", json={
        "descricao": "Óleo Motor 5W30",
        "quantidade": 2.0,
        "valor_unitario": 30.0,
        "item_almoxarifado_id": _ITEM_ID,
    }, headers=H())
    assert r.status_code == 201, r.text
    d = r.json()
    # now 2 items: filtro + óleo
    assert len(d["itens"]) == 2

    # Estoque: 15 - 2 = 13
    db = SessionLocal()
    item = db.get(ItemAlmoxarifado, _ITEM_ID)
    assert item.estoque_atual == 13.0
    db.close()


# ── Concluir / Cancelar Manutenção ────────────────────────────────────────────

def test_concluir_manutencao():
    r = client.post(f"/frota/manutencoes/{_MAN_ID}/concluir", json={
        "data_conclusao": str(date.today()),
        "valor_servico": 350.0,
        "oficina": "Oficina Central",
    }, headers=H())
    assert r.status_code == 200, r.text
    d = r.json()
    assert d["status"] == "concluida"
    assert d["valor_servico"] == 350.0

    # Veículo volta a "ativo" pois não há outras manutenções abertas
    db = SessionLocal()
    v = db.get(Veiculo, _VEICULO_ID)
    assert v.status == "ativo"
    db.close()


def test_concluir_manutencao_ja_concluida():
    r = client.post(f"/frota/manutencoes/{_MAN_ID}/concluir", json={
        "data_conclusao": str(date.today()),
        "valor_servico": 100.0,
    }, headers=H())
    assert r.status_code == 422


def test_cancelar_manutencao():
    # Cria nova manutenção para cancelar
    r = client.post("/frota/manutencoes", json={
        "veiculo_id": _VEICULO2_ID,
        "tipo": "preventiva",
        "descricao": "Para cancelar",
        "data_abertura": str(date.today()),
    }, headers=H())
    assert r.status_code == 201
    man_id = r.json()["id"]

    r2 = client.post(f"/frota/manutencoes/{man_id}/cancelar", headers=H())
    assert r2.status_code == 200
    assert r2.json()["status"] == "cancelada"


def test_cancelar_manutencao_ja_cancelada():
    db = SessionLocal()
    man = db.query(ManutencaoVeiculo).filter_by(status="cancelada").first()
    man_id = man.id
    db.close()
    r = client.post(f"/frota/manutencoes/{man_id}/cancelar", headers=H())
    assert r.status_code == 422


# ── Dashboard & Consumo ───────────────────────────────────────────────────────

def test_dashboard_frota():
    r = client.get("/frota/veiculos/dashboard", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert "total_veiculos" in d
    assert d["total_veiculos"] >= 2
    assert "litros_mes" in d
    assert "custo_abastecimento_mes" in d
    assert "manutencoes_abertas" in d
    assert "custo_manutencao_mes" in d


def test_consumo_veiculo():
    r = client.get(f"/frota/veiculos/{_VEICULO_ID}/consumo", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["veiculo_id"] == _VEICULO_ID
    assert d["total_abastecimentos"] >= 1
    assert d["custo_total"] >= 0


def test_consumo_veiculo_not_found():
    r = client.get("/frota/veiculos/99999/consumo", headers=H())
    assert r.status_code == 404


# ── Integração: Alerta de estoque via manutenção ──────────────────────────────

def test_manutencao_gera_alerta_estoque():
    """Saída de item almoxarifado via manutenção deve gerar alerta se ficar abaixo do mínimo."""
    # Estoque atual apos testes anteriores: 13 (20 - 5 - 2)
    # Vamos consumir 11 (13 - 11 = 2 < 5 → ALERTA)
    r = client.post("/frota/manutencoes", json={
        "veiculo_id": _VEICULO2_ID,
        "tipo": "corretiva",
        "descricao": "Troca de óleo adicional",
        "data_abertura": str(date.today()),
        "departamento_id": _DEPT_ID,
        "itens": [{
            "descricao": "Óleo Motor 5W30",
            "quantidade": 11.0,
            "valor_unitario": 30.0,
            "item_almoxarifado_id": _ITEM_ID,
        }],
    }, headers=H())
    assert r.status_code == 201, r.text

    db = SessionLocal()
    item = db.get(ItemAlmoxarifado, _ITEM_ID)
    assert item.estoque_atual == 2.0  # 13 - 11
    alerta = db.query(AlertaEstoqueMinimo).filter(
        AlertaEstoqueMinimo.item_id == _ITEM_ID,
        AlertaEstoqueMinimo.status == "aberto",
    ).first()
    assert alerta is not None
    assert alerta.saldo_no_momento == 2.0
    db.close()


def test_veiculo_inativo_nao_abastece():
    """Veículo inativo não pode ser abastecido."""
    # Cria e inativa um veículo
    cr = client.post("/frota/veiculos", json={
        "placa": "INA-0001",
        "descricao": "Veículo inativo",
        "tipo": "leve",
        "combustivel": "flex",
        "status": "inativo",
    }, headers=H())
    assert cr.status_code == 201
    v_id = cr.json()["id"]

    r = client.post("/frota/abastecimentos", json={
        "veiculo_id": v_id,
        "data_abastecimento": str(date.today()),
        "combustivel": "flex",
        "litros": 20.0,
        "valor_litro": 5.0,
    }, headers=H())
    assert r.status_code == 422
