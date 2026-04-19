"""Testes da camada preparatória SICONFI / SIOP (Onda 18).

Cobre:
- ConfiguracaoEntidade (CRUD)
- GET /siconfi/validar (inconsistências)
- GET /siconfi/finbra
- GET /siconfi/rreo
- GET /siconfi/rgf
- GET /siconfi/siop-programas
- GET /siconfi/dashboard
- POST /siconfi/exportar (tipos, log, idempotência)
- GET /siconfi/exportacoes (filtros)
- Permissões
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_siconfi_siop.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    BudgetAllocation,
    Commitment,
    ConfiguracaoEntidade,
    ExportacaoSiconfi,
    FiscalYear,
    LOA,
    LOAItem,
    LDO,
    LDOGoal,
    Liquidation,
    Payment,
    Payslip,
    PPA,
    PPAProgram,
    RevenueEntry,
)
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
        os.remove("./test_siconfi_siop.db")
    except FileNotFoundError:
        pass


def auth(username: str, password: str = "demo123") -> dict:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _get_fy_year() -> int:
    db = SessionLocal()
    fy = db.query(FiscalYear).first()
    yr = fy.year
    db.close()
    return yr


# ── ConfiguracaoEntidade ──────────────────────────────────────────────────────

def test_get_config_returns_seed():
    h = auth("admin1")
    r = client.get("/siconfi/config", headers=h)
    assert r.status_code == 200
    d = r.json()
    assert d["cnpj"] == "12.345.678/0001-90"
    assert d["codigo_ibge"] == "1234567"


def test_upsert_config_admin():
    h = auth("admin1")
    payload = {
        "nome_entidade": "Prefeitura Demo",
        "cnpj": "12.345.678/0001-90",
        "codigo_ibge": "9876543",
        "uf": "MG",
        "esfera": "Municipal",
        "poder": "Executivo",
        "tipo_entidade": "Prefeitura Municipal",
        "responsavel_nome": "Maria Souza",
        "responsavel_cargo": "Prefeita",
        "responsavel_cpf": "111.111.111-11",
    }
    r = client.post("/siconfi/config", json=payload, headers=h)
    assert r.status_code == 200
    assert r.json()["codigo_ibge"] == "9876543"


def test_upsert_config_sem_permissao():
    r = client.post("/siconfi/config", json={
        "nome_entidade": "X", "cnpj": "00.000.000/0000-00",
        "codigo_ibge": "0000000", "uf": "SP",
    }, headers=auth("hr1"))
    assert r.status_code == 403


def test_get_config_sem_auth():
    r = client.get("/siconfi/config")
    assert r.status_code == 401


# ── Validar ───────────────────────────────────────────────────────────────────

def test_validar_exercicio_valido():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/validar?exercicio={yr}", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert "pode_exportar" in d
    assert "inconsistencias" in d
    assert isinstance(d["inconsistencias"], list)


def test_validar_exercicio_invalido():
    r = client.get("/siconfi/validar?exercicio=1800", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    # FiscalYear 1800 não existe → ERRO FY001
    codigos = [i["codigo"] for i in d["inconsistencias"]]
    assert "FY001" in codigos
    assert d["pode_exportar"] is False


def test_validar_sem_loa_gera_aviso_ou_erro():
    """Exercício sem LOA deve gerar inconsistência LOA001."""
    # Cria FY sem LOA
    db = SessionLocal()
    fy_novo = FiscalYear(year=1999, active=False)
    db.add(fy_novo)
    db.commit()
    db.close()
    r = client.get("/siconfi/validar?exercicio=1999", headers=auth("admin1"))
    codigos = [i["codigo"] for i in r.json()["inconsistencias"]]
    assert "LOA001" in codigos


def test_validar_cnpj_invalido_gera_erro():
    db = SessionLocal()
    db.query(ConfiguracaoEntidade).update({"ativo": False})
    cfg = ConfiguracaoEntidade(
        nome_entidade="X", cnpj="invalido", codigo_ibge="1234567",
        uf="SP", ativo=True
    )
    db.add(cfg)
    db.commit()
    db.close()
    yr = _get_fy_year()
    r = client.get(f"/siconfi/validar?exercicio={yr}", headers=auth("admin1"))
    codigos = [i["codigo"] for i in r.json()["inconsistencias"]]
    assert "ENT002" in codigos
    # Restaura config correta
    db = SessionLocal()
    db.query(ConfiguracaoEntidade).update({"ativo": False})
    db.add(ConfiguracaoEntidade(
        nome_entidade="Prefeitura Municipal de Vila Esperança",
        cnpj="12.345.678/0001-90", codigo_ibge="1234567", uf="SP", ativo=True
    ))
    db.commit()
    db.close()


# ── FINBRA ────────────────────────────────────────────────────────────────────

def test_finbra_retorna_estrutura_esperada():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/finbra?exercicio={yr}", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert "cabecalho" in d
    assert d["cabecalho"]["tipo_relatorio"] == "FINBRA_BALANCO_ORCAMENTARIO"
    assert "balanco_receita" in d
    assert "balanco_despesa" in d
    assert "indicadores_lrf" in d
    assert "resultado_exercicio" in d


def test_finbra_resultado_exercicio_tem_saldo():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/finbra?exercicio={yr}", headers=auth("admin1"))
    res = r.json()["resultado_exercicio"]
    assert "saldo" in res
    assert res["tipo"] in ("superavit", "deficit")


def test_finbra_exercicio_inexistente_404():
    r = client.get("/siconfi/finbra?exercicio=1800", headers=auth("admin1"))
    assert r.status_code == 404


def test_finbra_indicadores_lrf():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/finbra?exercicio={yr}", headers=auth("admin1"))
    ind = r.json()["indicadores_lrf"]
    assert "rcl_12meses" in ind
    assert "despesa_pessoal_bruta" in ind
    assert ind["situacao_pessoal"] in ("REGULAR", "ALERTA", "EXCEDIDO")


def test_finbra_com_receitas_e_despesas():
    """Com RevenueEntry e Payment no banco → saldo coerente."""
    yr = _get_fy_year()
    db = SessionLocal()
    db.add(RevenueEntry(description="Receita FINBRA", amount=50000.0,
                        entry_date=date(yr, 6, 1)))
    db.add(Payment(amount=20000.0, payment_date=date(yr, 6, 15),
                   commitment_id=db.query(Commitment).first().id if db.query(Commitment).first() else None))
    db.commit()
    db.close()
    r = client.get(f"/siconfi/finbra?exercicio={yr}", headers=auth("admin1"))
    res = r.json()["resultado_exercicio"]
    assert res["receita"] >= 50000.0


# ── RREO ──────────────────────────────────────────────────────────────────────

def test_rreo_retorna_estrutura():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/rreo?exercicio={yr}&bimestre=1", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert d["cabecalho"]["tipo_relatorio"] == "RREO_BALANCO_ORCAMENTARIO"
    assert "receitas" in d
    assert "despesas_totais" in d
    assert "despesas_por_funcao" in d


def test_rreo_bimestre_invalido_422():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/rreo?exercicio={yr}&bimestre=7", headers=auth("admin1"))
    assert r.status_code == 422


def test_rreo_exercicio_inexistente_404():
    r = client.get("/siconfi/rreo?exercicio=1800&bimestre=1", headers=auth("admin1"))
    assert r.status_code == 404


def test_rreo_todos_bimestres():
    """Deve retornar 200 para todos os 6 bimestres."""
    yr = _get_fy_year()
    h = auth("admin1")
    for bim in range(1, 7):
        r = client.get(f"/siconfi/rreo?exercicio={yr}&bimestre={bim}", headers=h)
        assert r.status_code == 200


# ── RGF ───────────────────────────────────────────────────────────────────────

def test_rgf_retorna_estrutura():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/rgf?exercicio={yr}&quadrimestre=1", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert d["cabecalho"]["tipo_relatorio"] == "RGF_DESPESA_PESSOAL_DIVIDA"
    assert "despesa_pessoal" in d
    assert d["despesa_pessoal"]["situacao"] in ("REGULAR", "ALERTA", "EXCEDIDO")


def test_rgf_quadrimestre_invalido_422():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/rgf?exercicio={yr}&quadrimestre=4", headers=auth("admin1"))
    assert r.status_code == 422


def test_rgf_exercicio_inexistente_404():
    r = client.get("/siconfi/rgf?exercicio=1800&quadrimestre=1", headers=auth("admin1"))
    assert r.status_code == 404


# ── SIOP Programas ────────────────────────────────────────────────────────────

def test_siop_programas_retorna_estrutura():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/siop-programas?exercicio={yr}", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert d["cabecalho"]["tipo_relatorio"] == "SIOP_PROGRAMAS_ACOES"
    assert "programas_ppa" in d
    assert "acoes_loa" in d
    assert "metas_ldo" in d
    assert "totais" in d


def test_siop_sem_ppa_retorna_lista_vazia():
    """Exercício sem PPA vigente → lista programas_ppa vazia."""
    r = client.get("/siconfi/siop-programas?exercicio=1999", headers=auth("admin1"))
    assert r.status_code == 200
    assert r.json()["programas_ppa"] == []


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard_retorna_estrutura():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/dashboard?exercicio={yr}", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert "status_preparacao" in d
    assert "validacao" in d
    assert "modulos" in d
    assert "resumo_financeiro" in d
    assert d["status_preparacao"] in ("PRONTO", "PENDENTE")


def test_dashboard_modulos():
    yr = _get_fy_year()
    r = client.get(f"/siconfi/dashboard?exercicio={yr}", headers=auth("admin1"))
    mod = r.json()["modulos"]
    assert "entidade_configurada" in mod
    assert "loa_vigente" in mod
    assert mod["entidade_configurada"] is True


# ── Exportar ─────────────────────────────────────────────────────────────────

def test_exportar_finbra():
    yr = _get_fy_year()
    r = client.post("/siconfi/exportar", json={
        "tipo": "finbra", "exercicio": yr,
    }, headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert d["tipo"] == "finbra"
    assert d["exercicio"] == yr
    assert d["status"] in ("rascunho", "validado")
    assert "id" in d


def test_exportar_rreo():
    yr = _get_fy_year()
    r = client.post("/siconfi/exportar", json={
        "tipo": "rreo", "exercicio": yr, "periodo": "bimestre_2",
    }, headers=auth("admin1"))
    assert r.status_code == 200
    assert r.json()["tipo"] == "rreo"


def test_exportar_rgf():
    yr = _get_fy_year()
    r = client.post("/siconfi/exportar", json={
        "tipo": "rgf", "exercicio": yr, "periodo": "quad_1",
    }, headers=auth("admin1"))
    assert r.status_code == 200
    assert r.json()["tipo"] == "rgf"


def test_exportar_siop_programas():
    yr = _get_fy_year()
    r = client.post("/siconfi/exportar", json={
        "tipo": "siop_programas", "exercicio": yr,
    }, headers=auth("admin1"))
    assert r.status_code == 200


def test_exportar_tipo_invalido_422():
    yr = _get_fy_year()
    r = client.post("/siconfi/exportar", json={
        "tipo": "tipo_inexistente", "exercicio": yr,
    }, headers=auth("admin1"))
    assert r.status_code == 422


def test_exportar_exercicio_invalido_404():
    r = client.post("/siconfi/exportar", json={
        "tipo": "finbra", "exercicio": 1800,
    }, headers=auth("admin1"))
    assert r.status_code == 404


def test_exportar_sem_permissao():
    yr = _get_fy_year()
    r = client.post("/siconfi/exportar", json={
        "tipo": "finbra", "exercicio": yr,
    }, headers=auth("read_only1"))
    assert r.status_code == 403


def test_exportar_gera_log():
    yr = _get_fy_year()
    h = auth("admin1")
    client.post("/siconfi/exportar", json={"tipo": "finbra", "exercicio": yr}, headers=h)
    db = SessionLocal()
    count = db.query(ExportacaoSiconfi).filter_by(tipo="finbra", exercicio=yr).count()
    db.close()
    assert count >= 1


def test_exportar_idempotente():
    """Exportar duas vezes o mesmo tipo/exercício deve criar dois logs distintos (sem duplicidade de dados)."""
    yr = _get_fy_year()
    h = auth("admin1")
    r1 = client.post("/siconfi/exportar", json={"tipo": "finbra", "exercicio": yr}, headers=h)
    r2 = client.post("/siconfi/exportar", json={"tipo": "finbra", "exercicio": yr}, headers=h)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["id"] != r2.json()["id"]


# ── List exportações ──────────────────────────────────────────────────────────

def test_list_exportacoes():
    yr = _get_fy_year()
    h = auth("admin1")
    client.post("/siconfi/exportar", json={"tipo": "finbra", "exercicio": yr}, headers=h)
    r = client.get("/siconfi/exportacoes", headers=h)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_list_exportacoes_filtro_tipo():
    yr = _get_fy_year()
    h = auth("admin1")
    r = client.get(f"/siconfi/exportacoes?tipo=finbra&exercicio={yr}", headers=h)
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["tipo"] == "finbra"


def test_list_exportacoes_sem_auth():
    r = client.get("/siconfi/exportacoes")
    assert r.status_code == 401
