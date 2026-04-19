"""Testes do módulo Depreciação Patrimonial (NBCASP/IPSAS 17).

Cobre: configuração, cálculo linear, cálculo saldo decrescente, idempotência,
       lançamentos, relatório histórico, exportação CSV, dashboard.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_depreciacao.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import Asset, ConfiguracaoDepreciacao, Department, LancamentoDepreciacao
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
        os.remove("./test_depreciacao.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _make_asset(tag: str, value: float = 12000.0) -> int:
    """Cria um bem patrimonial demo."""
    db = SessionLocal()
    dept = db.query(Department).first()
    a = Asset(tag=tag, description=f"Bem {tag}", classification="equipamento",
              location="Almoxarifado", department_id=dept.id, value=value, status="ativo")
    db.add(a)
    db.commit()
    db.refresh(a)
    aid = a.id
    db.close()
    return aid


def _create_config(asset_id: int, valor_aquisicao: float = 12000.0,
                   vida_util_meses: int = 60, valor_residual: float = 1200.0,
                   metodo: str = "linear") -> dict:
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/config", json={
        "asset_id": asset_id,
        "data_aquisicao": "2023-01-01",
        "valor_aquisicao": valor_aquisicao,
        "vida_util_meses": vida_util_meses,
        "valor_residual": valor_residual,
        "metodo": metodo,
    }, headers=headers)
    assert r.status_code == 201, r.text
    return r.json()


# ── Configuração ──────────────────────────────────────────────────────────────

def test_criar_config():
    asset_id = _make_asset("TST-CONFIG-001")
    data = _create_config(asset_id)
    assert data["asset_id"] == asset_id
    assert data["vida_util_meses"] == 60
    assert data["metodo"] == "linear"
    assert data["ativo"] is True


def test_criar_config_duplicada_409():
    asset_id = _make_asset("TST-CONFIG-DUP")
    _create_config(asset_id)
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/config", json={
        "asset_id": asset_id, "data_aquisicao": "2023-01-01",
        "valor_aquisicao": 10000, "vida_util_meses": 60,
        "valor_residual": 1000, "metodo": "linear",
    }, headers=headers)
    assert r.status_code == 409


def test_criar_config_bem_inexistente_404():
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/config", json={
        "asset_id": 999999, "data_aquisicao": "2023-01-01",
        "valor_aquisicao": 10000, "vida_util_meses": 60,
        "valor_residual": 1000, "metodo": "linear",
    }, headers=headers)
    assert r.status_code == 404


def test_criar_config_residual_maior_que_aquisicao_422():
    asset_id = _make_asset("TST-CONFIG-RINV")
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/config", json={
        "asset_id": asset_id, "data_aquisicao": "2023-01-01",
        "valor_aquisicao": 1000, "vida_util_meses": 60,
        "valor_residual": 1500, "metodo": "linear",
    }, headers=headers)
    assert r.status_code == 422


def test_criar_config_vida_util_zero_422():
    asset_id = _make_asset("TST-CONFIG-VU0")
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/config", json={
        "asset_id": asset_id, "data_aquisicao": "2023-01-01",
        "valor_aquisicao": 10000, "vida_util_meses": 0,
        "valor_residual": 1000, "metodo": "linear",
    }, headers=headers)
    assert r.status_code == 422


def test_criar_config_metodo_invalido_422():
    asset_id = _make_asset("TST-CONFIG-METINV")
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/config", json={
        "asset_id": asset_id, "data_aquisicao": "2023-01-01",
        "valor_aquisicao": 10000, "vida_util_meses": 60,
        "valor_residual": 1000, "metodo": "invalido",
    }, headers=headers)
    assert r.status_code == 422


def test_get_config():
    asset_id = _make_asset("TST-GET-001")
    _create_config(asset_id)
    headers = auth_headers("admin1")
    r = client.get(f"/depreciacao/config/{asset_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["asset_id"] == asset_id


def test_get_config_nao_encontrada_404():
    headers = auth_headers("admin1")
    r = client.get("/depreciacao/config/999999", headers=headers)
    assert r.status_code == 404


def test_list_configs():
    headers = auth_headers("admin1")
    r = client.get("/depreciacao/config", headers=headers)
    assert r.status_code == 200
    assert "total" in r.json()
    assert r.json()["total"] >= 1


def test_atualizar_config():
    asset_id = _make_asset("TST-PATCH-001")
    _create_config(asset_id)
    headers = auth_headers("admin1")
    r = client.patch(f"/depreciacao/config/{asset_id}", json={"vida_util_meses": 120}, headers=headers)
    assert r.status_code == 200
    assert r.json()["vida_util_meses"] == 120


def test_atualizar_config_sem_permissao_403():
    asset_id = _make_asset("TST-PATCH-RO")
    _create_config(asset_id)
    headers = auth_headers("read_only1")
    r = client.patch(f"/depreciacao/config/{asset_id}", json={"vida_util_meses": 120}, headers=headers)
    assert r.status_code == 403


# ── Cálculo Linear ────────────────────────────────────────────────────────────

def test_calcular_linear():
    """quota = (12000 - 1200) / 60 = 180/mês"""
    asset_id = _make_asset("TST-CALC-LIN-001", value=12000)
    _create_config(asset_id, valor_aquisicao=12000, vida_util_meses=60,
                   valor_residual=1200, metodo="linear")
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/calcular", json={"periodo": "2026-01", "asset_id": asset_id},
                    headers=headers)
    assert r.status_code == 200
    assert r.json()["criados"] == 1
    assert r.json()["total_depreciado"] == 180.0


def test_calcular_acumulado_dois_meses():
    """Dois meses de depreciação linear: acumulado = 360, VCL = 11640"""
    asset_id = _make_asset("TST-CALC-LIN-002", value=12000)
    _create_config(asset_id, valor_aquisicao=12000, vida_util_meses=60,
                   valor_residual=1200, metodo="linear")
    headers = auth_headers("admin1")
    client.post("/depreciacao/calcular", json={"periodo": "2025-01", "asset_id": asset_id},
                headers=headers)
    client.post("/depreciacao/calcular", json={"periodo": "2025-02", "asset_id": asset_id},
                headers=headers)

    db = SessionLocal()
    l = db.query(LancamentoDepreciacao).filter(
        LancamentoDepreciacao.asset_id == asset_id,
        LancamentoDepreciacao.periodo == "2025-02"
    ).first()
    db.close()
    assert l is not None
    assert abs(l.depreciacao_acumulada - 360.0) < 0.01
    assert abs(l.valor_contabil_liquido - 11640.0) < 0.01


def test_calcular_linear_nao_desce_abaixo_residual():
    """Bem quase depreciado: VCL já muito próximo do residual → quota = 0."""
    asset_id = _make_asset("TST-CALC-LIN-FLOOR", value=5000)
    headers = auth_headers("admin1")
    # Configura vida útil curta: 5 meses, residual = 500
    client.post("/depreciacao/config", json={
        "asset_id": asset_id, "data_aquisicao": "2020-01-01",
        "valor_aquisicao": 5000, "vida_util_meses": 5,
        "valor_residual": 500, "metodo": "linear",
    }, headers=headers)
    # Calcula 6 meses (1 além da vida útil)
    for i in range(1, 7):
        client.post("/depreciacao/calcular",
                    json={"periodo": f"2020-{i:02d}", "asset_id": asset_id},
                    headers=headers)

    db = SessionLocal()
    lancamentos = db.query(LancamentoDepreciacao).filter(
        LancamentoDepreciacao.asset_id == asset_id
    ).order_by(LancamentoDepreciacao.periodo).all()
    db.close()

    # Após 5 meses de quota = 900 cada: acumulado = 4500, VCL = 500 (residual)
    l5 = lancamentos[4]
    assert abs(l5.valor_contabil_liquido - 500.0) < 0.01
    # Mês 6: quota = 0 (já no residual)
    l6 = lancamentos[5]
    assert l6.valor_depreciado == 0.0
    assert abs(l6.valor_contabil_liquido - 500.0) < 0.01


# ── Cálculo Saldo Decrescente ─────────────────────────────────────────────────

def test_calcular_saldo_decrescente():
    """taxa = 2/60 = 0.0333; quota_m1 = 12000 * 0.0333 = 400"""
    asset_id = _make_asset("TST-CALC-SD-001", value=12000)
    _create_config(asset_id, valor_aquisicao=12000, vida_util_meses=60,
                   valor_residual=1200, metodo="saldo_decrescente")
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/calcular", json={"periodo": "2026-01", "asset_id": asset_id},
                    headers=headers)
    assert r.status_code == 200
    expected_quota = round(12000 * (2 / 60), 6)
    assert abs(r.json()["total_depreciado"] - expected_quota) < 0.01


def test_saldo_decrescente_decresce():
    """Cada mês a quota deve ser menor que a anterior."""
    asset_id = _make_asset("TST-CALC-SD-DEC", value=10000)
    _create_config(asset_id, valor_aquisicao=10000, vida_util_meses=60,
                   valor_residual=1000, metodo="saldo_decrescente")
    headers = auth_headers("admin1")
    for i in range(1, 4):
        client.post("/depreciacao/calcular",
                    json={"periodo": f"2024-{i:02d}", "asset_id": asset_id},
                    headers=headers)

    db = SessionLocal()
    lancamentos = db.query(LancamentoDepreciacao).filter(
        LancamentoDepreciacao.asset_id == asset_id
    ).order_by(LancamentoDepreciacao.periodo).all()
    db.close()

    assert len(lancamentos) == 3
    assert lancamentos[0].valor_depreciado > lancamentos[1].valor_depreciado > lancamentos[2].valor_depreciado


def test_saldo_decrescente_nao_desce_abaixo_residual():
    """Saldo decrescente também respeita o valor residual."""
    asset_id = _make_asset("TST-SD-FLOOR", value=1000)
    headers = auth_headers("admin1")
    client.post("/depreciacao/config", json={
        "asset_id": asset_id, "data_aquisicao": "2020-01-01",
        "valor_aquisicao": 1000, "vida_util_meses": 2,
        "valor_residual": 100, "metodo": "saldo_decrescente",
    }, headers=headers)
    # Muitos meses
    for i in range(1, 13):
        client.post("/depreciacao/calcular",
                    json={"periodo": f"2020-{i:02d}", "asset_id": asset_id},
                    headers=headers)

    db = SessionLocal()
    lancamentos = db.query(LancamentoDepreciacao).filter(
        LancamentoDepreciacao.asset_id == asset_id
    ).all()
    db.close()
    for l in lancamentos:
        assert l.valor_contabil_liquido >= 100.0 - 0.01
        assert l.valor_depreciado >= 0.0


# ── Idempotência ─────────────────────────────────────────────────────────────

def test_calcular_idempotente():
    """Recalcular o mesmo período deve resultar em 'atualizados=1' e mesmos valores."""
    asset_id = _make_asset("TST-IDEM-001", value=6000)
    _create_config(asset_id, valor_aquisicao=6000, vida_util_meses=60,
                   valor_residual=600, metodo="linear")
    headers = auth_headers("admin1")
    r1 = client.post("/depreciacao/calcular", json={"periodo": "2026-02", "asset_id": asset_id},
                     headers=headers)
    assert r1.json()["criados"] == 1

    r2 = client.post("/depreciacao/calcular", json={"periodo": "2026-02", "asset_id": asset_id},
                     headers=headers)
    assert r2.json()["atualizados"] == 1
    assert r1.json()["total_depreciado"] == r2.json()["total_depreciado"]


def test_calcular_todos_bens():
    """Sem asset_id: deve calcular todos os bens com configuração ativa."""
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/calcular", json={"periodo": "2026-03"}, headers=headers)
    assert r.status_code == 200
    assert r.json()["criados"] + r.json()["atualizados"] >= 1


def test_calcular_periodo_invalido_422():
    headers = auth_headers("admin1")
    r = client.post("/depreciacao/calcular", json={"periodo": "2026-13"}, headers=headers)
    assert r.status_code == 422


def test_calcular_sem_permissao_403():
    headers = auth_headers("read_only1")
    r = client.post("/depreciacao/calcular", json={"periodo": "2026-04"}, headers=headers)
    assert r.status_code == 403


# ── Lançamentos ───────────────────────────────────────────────────────────────

def test_list_lancamentos():
    headers = auth_headers("admin1")
    r = client.get("/depreciacao/lancamentos", headers=headers)
    assert r.status_code == 200
    assert "total" in r.json()
    assert r.json()["total"] >= 1


def test_list_lancamentos_por_periodo():
    """Filtrar por período deve retornar apenas lançamentos daquele período."""
    headers = auth_headers("admin1")
    # Garantir que há lançamentos no período
    client.post("/depreciacao/calcular", json={"periodo": "2026-05"}, headers=headers)
    r = client.get("/depreciacao/lancamentos?periodo=2026-05", headers=headers)
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["periodo"] == "2026-05"


# ── Relatório por bem ─────────────────────────────────────────────────────────

def test_relatorio_ativo():
    asset_id = _make_asset("TST-REL-001", value=9000)
    _create_config(asset_id, valor_aquisicao=9000, vida_util_meses=60,
                   valor_residual=900, metodo="linear")
    headers = auth_headers("admin1")
    client.post("/depreciacao/calcular", json={"periodo": "2026-04", "asset_id": asset_id},
                headers=headers)
    r = client.get(f"/depreciacao/relatorio/{asset_id}", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["asset_id"] == asset_id
    assert data["valor_aquisicao"] == 9000
    assert len(data["lancamentos"]) >= 1
    l0 = data["lancamentos"][0]
    assert "periodo" in l0
    assert "valor_depreciado" in l0
    assert "depreciacao_acumulada" in l0
    assert "valor_contabil_liquido" in l0


def test_relatorio_sem_config_404():
    asset_id = _make_asset("TST-REL-NOCONFIG")
    headers = auth_headers("admin1")
    r = client.get(f"/depreciacao/relatorio/{asset_id}", headers=headers)
    assert r.status_code == 404


def test_relatorio_bem_inexistente_404():
    headers = auth_headers("admin1")
    r = client.get("/depreciacao/relatorio/999999", headers=headers)
    assert r.status_code == 404


def test_relatorio_csv():
    asset_id = _make_asset("TST-CSV-001", value=8000)
    _create_config(asset_id, valor_aquisicao=8000, vida_util_meses=60,
                   valor_residual=800, metodo="linear")
    headers = auth_headers("admin1")
    client.post("/depreciacao/calcular", json={"periodo": "2026-06", "asset_id": asset_id},
                headers=headers)
    r = client.get(f"/depreciacao/relatorio/{asset_id}/csv", headers=headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("tombamento,")
    assert len(lines) >= 2   # header + 1 lançamento


def test_relatorio_csv_sem_config_404():
    asset_id = _make_asset("TST-CSV-NOCONFIG")
    headers = auth_headers("admin1")
    r = client.get(f"/depreciacao/relatorio/{asset_id}/csv", headers=headers)
    assert r.status_code == 404


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard():
    headers = auth_headers("admin1")
    # Garante lançamentos no período
    client.post("/depreciacao/calcular", json={"periodo": "2026-07"}, headers=headers)
    r = client.get("/depreciacao/dashboard?periodo=2026-07", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "periodo" in data
    assert "total_bens_configurados" in data
    assert "total_bens_com_lancamento" in data
    assert "total_depreciado_periodo" in data
    assert "total_depreciacao_acumulada" in data
    assert "total_valor_contabil_liquido" in data
    assert "top_bens" in data
    assert data["total_bens_configurados"] >= 1


def test_dashboard_periodo_invalido_422():
    headers = auth_headers("admin1")
    r = client.get("/depreciacao/dashboard?periodo=invalido", headers=headers)
    assert r.status_code == 422


def test_dashboard_sem_auth_401():
    r = client.get("/depreciacao/dashboard?periodo=2026-07")
    assert r.status_code == 401


def test_dashboard_leitura_by_read_only():
    client2 = TestClient(app)
    login = client2.post("/auth/login", json={"username": "read_only1", "password": "demo123"})
    h = {"Authorization": f"Bearer {login.json()['access_token']}"}
    r = client2.get("/depreciacao/dashboard?periodo=2026-07", headers=h)
    assert r.status_code == 200


# ── Seed ──────────────────────────────────────────────────────────────────────

def test_seed_configuracoes():
    db = SessionLocal()
    cfgs = db.query(ConfiguracaoDepreciacao).all()
    assert len(cfgs) >= 1
    for c in cfgs:
        assert c.vida_util_meses > 0
        assert c.valor_residual < c.valor_aquisicao
    db.close()


def test_seed_lancamentos():
    db = SessionLocal()
    lancamentos = db.query(LancamentoDepreciacao).all()
    assert len(lancamentos) >= 1
    for l in lancamentos:
        assert l.valor_contabil_liquido >= 0
        assert l.valor_depreciado >= 0
    db.close()


def test_seed_lancamentos_vcl_consistente():
    """VCL = valor_aquisicao - depreciacao_acumulada para cada lançamento."""
    db = SessionLocal()
    cfgs = {c.asset_id: c for c in db.query(ConfiguracaoDepreciacao).all()}
    lancamentos = db.query(LancamentoDepreciacao).all()
    for l in lancamentos:
        cfg = cfgs.get(l.asset_id)
        if cfg:
            esperado = round(cfg.valor_aquisicao - l.depreciacao_acumulada, 2)
            assert abs(l.valor_contabil_liquido - esperado) < 0.01, (
                f"asset_id={l.asset_id} periodo={l.periodo}: "
                f"VCL={l.valor_contabil_liquido} != esperado={esperado}"
            )
    db.close()
