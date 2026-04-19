"""Testes Onda 19 Fase 1 — Geração XML SICONFI + Validação Local.

Cobre:
- build_xml_finbra / build_xml_rreo / build_xml_rgf (siconfi_xml.py)
- validate_xml com XSD inline
- GET /siconfi/xml/finbra (JSON e download)
- GET /siconfi/xml/rreo (JSON e download, todos bimestres)
- GET /siconfi/xml/rgf (JSON e download, todos quadrimestres)
- POST /siconfi/xml/validar
- GET /siconfi/xml/historico (filtros)
- GET /siconfi/xml/{id}/download
- POST /siconfi/envio (stub → 501)
- GET /siconfi/envio/historico
- Permissões
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_siconfi_xml.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import FiscalYear, ValidacaoXmlLog
from app.seed import seed_data
from app.siconfi_xml import (
    build_xml_finbra,
    build_xml_rreo,
    build_xml_rgf,
    validate_xml,
)

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
        os.remove("./test_siconfi_xml.db")
    except FileNotFoundError:
        pass


def auth(username: str, password: str = "demo123") -> dict:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _fy_year() -> int:
    db = SessionLocal()
    yr = db.query(FiscalYear).first().year
    db.close()
    return yr


# ── Unit tests — siconfi_xml.py ───────────────────────────────────────────────

def _dummy_cfg() -> dict:
    return {
        "nome_entidade": "Prefeitura Demo",
        "cnpj": "12.345.678/0001-90",
        "codigo_ibge": "1234567",
        "uf": "SP",
        "esfera": "Municipal",
        "poder": "Executivo",
        "responsavel_nome": "João Silva",
        "responsavel_cargo": "Prefeito",
        "responsavel_cpf": "000.000.000-01",
    }


def _dummy_finbra(yr: int) -> dict:
    return {
        "cabecalho": {"exercicio": yr, "tipo_relatorio": "FINBRA_BALANCO_ORCAMENTARIO", "periodo": "ANUAL", "data_geracao": str(date.today())},
        "balanco_receita": {"receita_prevista_loa": 100000.0, "receita_arrecadada": 95000.0, "diferenca_arrecadamento": -5000.0, "pct_realizacao": 95.0},
        "balanco_despesa": {"dotacao_autorizada": 100000.0, "despesa_empenhada": 90000.0, "despesa_liquidada": 85000.0, "despesa_paga": 80000.0, "saldo_a_pagar": 10000.0},
        "indicadores_lrf": {"rcl_12meses": 500000.0, "despesa_pessoal_bruta": 200000.0, "pct_pessoal_rcl": 40.0, "limite_pessoal_60pct": 300000.0, "situacao_pessoal": "REGULAR", "divida_consolidada": 50000.0},
        "resultado_exercicio": {"receita": 95000.0, "despesa": 80000.0, "saldo": 15000.0, "tipo": "superavit"},
    }


def _dummy_rreo(yr: int, bim: int = 1) -> dict:
    return {
        "cabecalho": {"exercicio": yr, "bimestre": bim, "referencia": f"{bim}º Bimestre/{yr}", "periodo": {"inicio": f"{yr}-01-01", "fim": f"{yr}-02-28"}, "tipo_relatorio": "RREO_BALANCO_ORCAMENTARIO", "base_legal": "LRF art. 52-53"},
        "receitas": {"prevista_loa": 100000.0, "arrecadada_bimestre": 15000.0, "arrecadada_acumulada": 15000.0},
        "despesas_por_funcao": [{"function_code": "10", "dotacao_autorizada": 50000.0, "dotacao_executada": 10000.0}],
        "despesas_totais": {"empenhada_exercicio": 90000.0, "liquidada_bimestre": 12000.0, "paga_bimestre": 10000.0, "paga_acumulada": 10000.0},
    }


def _dummy_rgf(yr: int, quad: int = 1) -> dict:
    return {
        "cabecalho": {"exercicio": yr, "quadrimestre": quad, "referencia": f"{quad}º Quadrimestre/{yr}", "periodo": {"inicio": f"{yr}-01-01", "fim": f"{yr}-04-30"}, "tipo_relatorio": "RGF_DESPESA_PESSOAL_DIVIDA", "base_legal": "LRF art. 55"},
        "despesa_pessoal": {"quadrimestre": 60000.0, "acumulada_ano": 60000.0, "rcl_12meses": 500000.0, "limite_legal_60pct": 300000.0, "limite_alerta_54pct": 270000.0, "pct_rcl": 12.0, "excesso": 0.0, "situacao": "REGULAR"},
        "divida_consolidada": {"saldo": 50000.0},
        "disponibilidade_financeira": {"receita_acumulada": 150000.0, "despesa_paga_acumulada": 80000.0, "saldo": 70000.0},
    }


def test_build_xml_finbra_is_valid_xml():
    yr = _fy_year()
    xml_bytes = build_xml_finbra(_dummy_finbra(yr), _dummy_cfg())
    assert xml_bytes.startswith(b"<?xml")
    assert b"SiconfiRelatorio" in xml_bytes
    assert b"BalancoOrcamentario" in xml_bytes
    assert b"FINBRA" in xml_bytes


def test_build_xml_rreo_is_valid_xml():
    yr = _fy_year()
    xml_bytes = build_xml_rreo(_dummy_rreo(yr), _dummy_cfg())
    assert b"RREO" in xml_bytes
    assert b"BalancoOrcamentarioBimestral" in xml_bytes
    assert b"DespesasPorFuncao" in xml_bytes


def test_build_xml_rgf_is_valid_xml():
    yr = _fy_year()
    xml_bytes = build_xml_rgf(_dummy_rgf(yr), _dummy_cfg())
    assert b"RGF" in xml_bytes
    assert b"RelatorioGestaoFiscal" in xml_bytes
    assert b"DespesaPessoal" in xml_bytes


def test_validate_xml_finbra_valido():
    yr = _fy_year()
    xml_bytes = build_xml_finbra(_dummy_finbra(yr), _dummy_cfg())
    valido, erros, avisos = validate_xml(xml_bytes, "finbra")
    assert valido is True
    assert erros == []
    # Deve ter aviso sobre XSD inline
    assert any("XSD" in a for a in avisos)


def test_validate_xml_rreo_valido():
    yr = _fy_year()
    xml_bytes = build_xml_rreo(_dummy_rreo(yr), _dummy_cfg())
    valido, erros, _ = validate_xml(xml_bytes, "rreo")
    assert valido is True
    assert erros == []


def test_validate_xml_rgf_valido():
    yr = _fy_year()
    xml_bytes = build_xml_rgf(_dummy_rgf(yr), _dummy_cfg())
    valido, erros, _ = validate_xml(xml_bytes, "rgf")
    assert valido is True
    assert erros == []


def test_validate_xml_cnpj_invalido_gera_erro():
    yr = _fy_year()
    cfg = _dummy_cfg()
    cfg["cnpj"] = "invalido"
    xml_bytes = build_xml_finbra(_dummy_finbra(yr), cfg)
    valido, erros, _ = validate_xml(xml_bytes, "finbra")
    assert valido is False
    assert len(erros) > 0


def test_validate_xml_mal_formado():
    valido, erros, _ = validate_xml(b"<broken xml>", "finbra")
    assert valido is False
    assert "mal formado" in erros[0].lower() or len(erros) > 0


def test_validate_xml_aviso_responsavel_ausente():
    yr = _fy_year()
    cfg = _dummy_cfg()
    cfg["responsavel_nome"] = ""
    xml_bytes = build_xml_finbra(_dummy_finbra(yr), cfg)
    _, _, avisos = validate_xml(xml_bytes, "finbra")
    assert any("Responsável" in a for a in avisos)


def test_validate_xml_ibge_vazio():
    yr = _fy_year()
    cfg = _dummy_cfg()
    cfg["codigo_ibge"] = ""
    xml_bytes = build_xml_finbra(_dummy_finbra(yr), cfg)
    valido, erros, _ = validate_xml(xml_bytes, "finbra")
    assert valido is False


# ── Endpoint /xml/finbra ──────────────────────────────────────────────────────

def test_xml_finbra_retorna_json():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/finbra?exercicio={yr}", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert "valido" in d
    assert "xml_preview" in d
    assert d["tipo"] == "finbra"
    assert d["xml_tamanho_bytes"] > 0


def test_xml_finbra_download():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/finbra?exercicio={yr}&download=true", headers=auth("admin1"))
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/xml"
    assert b"SiconfiRelatorio" in r.content


def test_xml_finbra_exercicio_404():
    r = client.get("/siconfi/xml/finbra?exercicio=1800", headers=auth("admin1"))
    assert r.status_code == 404


def test_xml_finbra_sem_auth_401():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/finbra?exercicio={yr}")
    assert r.status_code == 401


def test_xml_finbra_salva_log():
    yr = _fy_year()
    client.get(f"/siconfi/xml/finbra?exercicio={yr}", headers=auth("admin1"))
    db = SessionLocal()
    count = db.query(ValidacaoXmlLog).filter_by(tipo="finbra", exercicio=yr).count()
    db.close()
    assert count >= 1


# ── Endpoint /xml/rreo ────────────────────────────────────────────────────────

def test_xml_rreo_retorna_json():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/rreo?exercicio={yr}&bimestre=1", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert d["tipo"] == "rreo"
    assert d["bimestre"] == 1


def test_xml_rreo_download():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/rreo?exercicio={yr}&bimestre=2&download=true", headers=auth("admin1"))
    assert r.status_code == 200
    assert b"RREO" in r.content


def test_xml_rreo_todos_bimestres():
    yr = _fy_year()
    h = auth("admin1")
    for bim in range(1, 7):
        r = client.get(f"/siconfi/xml/rreo?exercicio={yr}&bimestre={bim}", headers=h)
        assert r.status_code == 200


def test_xml_rreo_bimestre_invalido_422():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/rreo?exercicio={yr}&bimestre=7", headers=auth("admin1"))
    assert r.status_code == 422


# ── Endpoint /xml/rgf ─────────────────────────────────────────────────────────

def test_xml_rgf_retorna_json():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/rgf?exercicio={yr}&quadrimestre=1", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert d["tipo"] == "rgf"
    assert d["quadrimestre"] == 1


def test_xml_rgf_download():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/rgf?exercicio={yr}&quadrimestre=1&download=true", headers=auth("admin1"))
    assert r.status_code == 200
    assert b"RGF" in r.content


def test_xml_rgf_todos_quadrimestres():
    yr = _fy_year()
    h = auth("admin1")
    for q in range(1, 4):
        r = client.get(f"/siconfi/xml/rgf?exercicio={yr}&quadrimestre={q}", headers=h)
        assert r.status_code == 200


def test_xml_rgf_quadrimestre_invalido_422():
    yr = _fy_year()
    r = client.get(f"/siconfi/xml/rgf?exercicio={yr}&quadrimestre=4", headers=auth("admin1"))
    assert r.status_code == 422


# ── POST /xml/validar ─────────────────────────────────────────────────────────

def test_xml_validar_finbra():
    yr = _fy_year()
    r = client.post("/siconfi/xml/validar", json={"tipo": "finbra", "exercicio": yr}, headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert "valido" in d
    assert d["tipo"] == "finbra"


def test_xml_validar_rreo_com_periodo():
    yr = _fy_year()
    r = client.post("/siconfi/xml/validar", json={"tipo": "rreo", "exercicio": yr, "periodo": "bimestre_3"}, headers=auth("admin1"))
    assert r.status_code == 200
    assert r.json()["tipo"] == "rreo"


def test_xml_validar_rgf_com_periodo():
    yr = _fy_year()
    r = client.post("/siconfi/xml/validar", json={"tipo": "rgf", "exercicio": yr, "periodo": "quad_2"}, headers=auth("admin1"))
    assert r.status_code == 200
    assert r.json()["tipo"] == "rgf"


def test_xml_validar_tipo_invalido_422():
    yr = _fy_year()
    r = client.post("/siconfi/xml/validar", json={"tipo": "xpto", "exercicio": yr}, headers=auth("admin1"))
    assert r.status_code == 422


def test_xml_validar_exercicio_inexistente_404():
    r = client.post("/siconfi/xml/validar", json={"tipo": "finbra", "exercicio": 1800}, headers=auth("admin1"))
    assert r.status_code == 404


# ── Histórico /xml/historico ──────────────────────────────────────────────────

def test_xml_historico_lista():
    yr = _fy_year()
    client.get(f"/siconfi/xml/finbra?exercicio={yr}", headers=auth("admin1"))
    r = client.get("/siconfi/xml/historico", headers=auth("admin1"))
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_xml_historico_filtro_tipo():
    yr = _fy_year()
    client.get(f"/siconfi/xml/finbra?exercicio={yr}", headers=auth("admin1"))
    r = client.get(f"/siconfi/xml/historico?tipo=finbra&exercicio={yr}", headers=auth("admin1"))
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["tipo"] == "finbra"


def test_xml_historico_filtro_valido():
    r = client.get("/siconfi/xml/historico?valido=true", headers=auth("admin1"))
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["valido"] is True


def test_xml_historico_sem_auth_401():
    r = client.get("/siconfi/xml/historico")
    assert r.status_code == 401


# ── Download de validação salva ───────────────────────────────────────────────

def test_download_xml_por_id():
    yr = _fy_year()
    r1 = client.get(f"/siconfi/xml/finbra?exercicio={yr}", headers=auth("admin1"))
    vid = r1.json()["validacao_id"]
    r2 = client.get(f"/siconfi/xml/{vid}/download", headers=auth("admin1"))
    assert r2.status_code == 200
    assert b"SiconfiRelatorio" in r2.content


def test_download_xml_id_invalido_404():
    r = client.get("/siconfi/xml/99999/download", headers=auth("admin1"))
    assert r.status_code == 404


# ── Fase 2 stub ───────────────────────────────────────────────────────────────

def test_envio_stub_retorna_501():
    yr = _fy_year()
    # Gera uma validação para usar como referência
    r1 = client.post("/siconfi/xml/validar", json={"tipo": "finbra", "exercicio": yr}, headers=auth("admin1"))
    vid = r1.json()["id"]
    r2 = client.post("/siconfi/envio", json={
        "validacao_xml_id": vid,
        "certificado_pfx_base64": "AAAA",
        "certificado_senha": "senha123",
        "dry_run": True,
    }, headers=auth("admin1"))
    assert r2.status_code == 501
    d = r2.json()
    assert d["status"] == "NOT_IMPLEMENTED"
    assert "requisitos_pendentes" in d


def test_envio_stub_sem_admin_403():
    r = client.post("/siconfi/envio", json={
        "validacao_xml_id": 1,
        "certificado_pfx_base64": "AAAA",
        "certificado_senha": "x",
        "dry_run": True,
    }, headers=auth("hr1"))
    assert r.status_code == 403


def test_envio_historico_vazio():
    r = client.get("/siconfi/envio/historico", headers=auth("admin1"))
    assert r.status_code == 200
    d = r.json()
    assert "nota" in d
    assert d["items"] == []
