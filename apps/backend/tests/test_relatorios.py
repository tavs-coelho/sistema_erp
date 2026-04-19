"""Testes dos relatórios consolidados de custo operacional.

Cobre: custo por veículo, custo por departamento, exportação CSV,
filtros de data, de veículo e de departamento, ausência de dados.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_relatorios.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    Abastecimento,
    Department,
    ItemAlmoxarifado,
    ItemManutencao,
    ManutencaoVeiculo,
    Veiculo,
)
from app.seed import seed_data

client = TestClient(app)

_DEPT_ID: int = 0
_DEPT2_ID: int = 0
_ITEM_ID: int = 0
_V1_ID: int = 0
_V2_ID: int = 0
TODAY = str(date.today())


def setup_module():
    global _DEPT_ID, _DEPT2_ID, _ITEM_ID, _V1_ID, _V2_ID
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)

    dept = db.query(Department).first()
    _DEPT_ID = dept.id

    dept2 = Department(name="Secretaria de Obras — Relat")
    db.add(dept2)
    db.flush()
    _DEPT2_ID = dept2.id

    item = ItemAlmoxarifado(
        codigo="REL-001",
        descricao="Óleo Motor 5W30 — Relatório",
        unidade="L",
        categoria="material_consumo",
        estoque_minimo=2.0,
        estoque_atual=50.0,
        valor_unitario=30.0,
    )
    db.add(item)
    db.flush()
    _ITEM_ID = item.id

    # Veículo 1 — departamento 1
    v1 = Veiculo(placa="REL-0001", descricao="Veículo Relatório 1", tipo="leve",
                 combustivel="flex", departamento_id=_DEPT_ID)
    db.add(v1)
    db.flush()
    _V1_ID = v1.id

    # Veículo 2 — departamento 2
    v2 = Veiculo(placa="REL-0002", descricao="Veículo Relatório 2", tipo="pesado",
                 combustivel="diesel", departamento_id=_DEPT2_ID)
    db.add(v2)
    db.flush()
    _V2_ID = v2.id

    # Abastecimentos
    db.add(Abastecimento(veiculo_id=_V1_ID, data_abastecimento=date.today(),
                         combustivel="flex", litros=40.0, valor_litro=5.0, valor_total=200.0,
                         odometro=10000, departamento_id=_DEPT_ID))
    db.add(Abastecimento(veiculo_id=_V1_ID, data_abastecimento=date.today(),
                         combustivel="flex", litros=20.0, valor_litro=5.0, valor_total=100.0,
                         odometro=10500, departamento_id=_DEPT_ID))
    db.add(Abastecimento(veiculo_id=_V2_ID, data_abastecimento=date.today(),
                         combustivel="diesel", litros=60.0, valor_litro=6.0, valor_total=360.0,
                         odometro=50000, departamento_id=_DEPT2_ID))

    # Manutenção V1 com peças
    man1 = ManutencaoVeiculo(veiculo_id=_V1_ID, tipo="preventiva",
                              descricao="Troca de óleo", data_abertura=date.today(),
                              valor_servico=150.0, status="concluida",
                              departamento_id=_DEPT_ID)
    db.add(man1)
    db.flush()
    db.add(ItemManutencao(manutencao_id=man1.id, descricao="Óleo Motor",
                          quantidade=4.0, valor_unitario=30.0, valor_total=120.0,
                          item_almoxarifado_id=_ITEM_ID))
    # Update almoxarifado stock
    item.estoque_atual -= 4.0

    # Manutenção V2 sem peças
    man2 = ManutencaoVeiculo(veiculo_id=_V2_ID, tipo="corretiva",
                              descricao="Freios", data_abertura=date.today(),
                              valor_servico=400.0, status="concluida",
                              departamento_id=_DEPT2_ID)
    db.add(man2)

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_relatorios.db")
    except FileNotFoundError:
        pass


def auth_headers(username="admin1", password="demo123"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


H = auth_headers


# ── Custo por veículo ─────────────────────────────────────────────────────────

def test_custo_por_veiculo_lista_todos():
    r = client.get("/relatorios/frota/custo-por-veiculo", headers=H())
    assert r.status_code == 200, r.text
    d = r.json()
    assert "itens" in d
    assert "totais" in d
    assert len(d["itens"]) >= 2


def test_custo_por_veiculo_composicao_v1():
    r = client.get(f"/relatorios/frota/custo-por-veiculo?veiculo_id={_V1_ID}", headers=H())
    assert r.status_code == 200, r.text
    d = r.json()
    assert len(d["itens"]) == 1
    row = d["itens"][0]
    assert row["veiculo_id"] == _V1_ID
    # Abastecimento V1: 200 + 100 = 300
    assert row["custo_abastecimento"] == 300.0
    assert row["n_abastecimentos"] == 2
    assert row["total_litros"] == 60.0
    # Manutenção serviço V1: 150
    assert row["custo_manutencao_servico"] == 150.0
    assert row["n_manutencoes"] == 1
    # Peças V1: 120
    assert row["custo_pecas_almoxarifado"] == 120.0
    assert row["n_pecas_almoxarifado"] == 1
    # Total V1: 300 + 150 + 120 = 570
    assert row["custo_total"] == 570.0


def test_custo_por_veiculo_composicao_v2():
    r = client.get(f"/relatorios/frota/custo-por-veiculo?veiculo_id={_V2_ID}", headers=H())
    assert r.status_code == 200, r.text
    row = r.json()["itens"][0]
    assert row["custo_abastecimento"] == 360.0
    assert row["custo_manutencao_servico"] == 400.0
    assert row["custo_pecas_almoxarifado"] == 0.0  # manutenção sem peças
    assert row["custo_total"] == 760.0


def test_custo_por_veiculo_totais():
    r = client.get("/relatorios/frota/custo-por-veiculo", headers=H())
    d = r.json()
    # Sum of all vehicles
    total_calc = sum(row["custo_total"] for row in d["itens"])
    assert abs(d["totais"]["total_geral"] - total_calc) < 0.01


def test_custo_por_veiculo_filtro_departamento():
    r = client.get(f"/relatorios/frota/custo-por-veiculo?departamento_id={_DEPT_ID}", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert all(row["departamento_id"] == _DEPT_ID for row in d["itens"])


def test_custo_por_veiculo_filtro_data_inicio_excluente():
    """Data início futura deve retornar custo 0 para todos veículos."""
    r = client.get("/relatorios/frota/custo-por-veiculo?data_inicio=2099-01-01", headers=H())
    assert r.status_code == 200
    d = r.json()
    for row in d["itens"]:
        assert row["custo_abastecimento"] == 0.0
        assert row["custo_manutencao_servico"] == 0.0
        assert row["custo_pecas_almoxarifado"] == 0.0
        assert row["custo_total"] == 0.0


def test_custo_por_veiculo_csv():
    r = client.get(f"/relatorios/frota/custo-por-veiculo?veiculo_id={_V1_ID}&export=csv",
                   headers=H())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().split("\n")
    # Header + 1 data row
    assert len(lines) >= 2
    assert "placa" in lines[0]
    assert "custo_total" in lines[0]
    # Data row should contain the placa
    assert "REL-0001" in r.text


def test_custo_por_veiculo_csv_sem_filtro():
    r = client.get("/relatorios/frota/custo-por-veiculo?export=csv", headers=H())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().split("\n")
    assert len(lines) >= 3  # header + at least 2 rows


# ── Custo por departamento ────────────────────────────────────────────────────

def test_custo_por_departamento_lista():
    r = client.get("/relatorios/frota/custo-por-departamento", headers=H())
    assert r.status_code == 200, r.text
    d = r.json()
    assert "itens" in d
    assert "totais" in d
    assert len(d["itens"]) >= 2


def test_custo_por_departamento_composicao_dept1():
    r = client.get(f"/relatorios/frota/custo-por-departamento?departamento_id={_DEPT_ID}",
                   headers=H())
    assert r.status_code == 200
    d = r.json()
    assert len(d["itens"]) == 1
    row = d["itens"][0]
    assert row["departamento_id"] == _DEPT_ID
    assert row["custo_abastecimento"] == 300.0
    assert row["custo_manutencao_servico"] == 150.0
    assert row["custo_pecas_almoxarifado"] == 120.0
    assert row["custo_total"] == 570.0


def test_custo_por_departamento_composicao_dept2():
    r = client.get(f"/relatorios/frota/custo-por-departamento?departamento_id={_DEPT2_ID}",
                   headers=H())
    assert r.status_code == 200
    row = r.json()["itens"][0]
    assert row["custo_abastecimento"] == 360.0
    assert row["custo_manutencao_servico"] == 400.0
    assert row["custo_pecas_almoxarifado"] == 0.0
    assert row["custo_total"] == 760.0


def test_custo_por_departamento_totais():
    r = client.get("/relatorios/frota/custo-por-departamento", headers=H())
    d = r.json()
    total_calc = sum(row["custo_total"] for row in d["itens"])
    assert abs(d["totais"]["total_geral"] - total_calc) < 0.01


def test_custo_por_departamento_filtro_data_excluente():
    r = client.get("/relatorios/frota/custo-por-departamento?data_inicio=2099-01-01",
                   headers=H())
    assert r.status_code == 200
    d = r.json()
    for row in d["itens"]:
        assert row["custo_total"] == 0.0


def test_custo_por_departamento_csv():
    r = client.get("/relatorios/frota/custo-por-departamento?export=csv", headers=H())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().split("\n")
    assert len(lines) >= 3
    assert "departamento_nome" in lines[0]
    assert "custo_total" in lines[0]


def test_custo_por_departamento_csv_com_filtro():
    r = client.get(
        f"/relatorios/frota/custo-por-departamento?departamento_id={_DEPT_ID}&export=csv",
        headers=H())
    assert r.status_code == 200
    lines = r.text.strip().split("\n")
    assert len(lines) == 2  # header + 1 row


def test_requer_autenticacao():
    r = client.get("/relatorios/frota/custo-por-veiculo")
    assert r.status_code == 401
