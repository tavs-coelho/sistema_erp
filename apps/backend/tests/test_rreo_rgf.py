"""Testes dos demonstrativos RREO e RGF.

Cobre: estrutura de resposta, cálculos de receita/despesa, despesa de pessoal,
limites LRF, CSV, bimestres/quadrimestres específicos, autenticação obrigatória.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_rreo_rgf.db"

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    BudgetAllocation,
    Commitment,
    Employee,
    FiscalYear,
    LOA,
    LOAItem,
    Liquidation,
    Payment,
    Payslip,
    RevenueEntry,
    Vendor,
)
from app.seed import seed_data

client = TestClient(app)

_FY_ID: int = 0
TODAY = date.today()
YEAR = TODAY.year


def setup_module():
    global _FY_ID
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)

    # The seed already creates FY for YEAR; just grab it
    fy = db.query(FiscalYear).filter(FiscalYear.year == YEAR).first()
    if not fy:
        fy = FiscalYear(year=YEAR, active=True)
        db.add(fy)
        db.flush()
    _FY_ID = fy.id

    # Add a LOA with revenue and expenditure items for YEAR
    loa = LOA(fiscal_year_id=_FY_ID, description=f"LOA {YEAR}", status="aprovada",
               total_revenue=500000.0, total_expenditure=480000.0)
    db.add(loa)
    db.flush()
    db.add(LOAItem(loa_id=loa.id, function_code="04", subfunction_code="122",
                   program_code="0001", action_code="2001",
                   description="Receitas correntes totais", category="receita",
                   authorized_amount=500000.0))
    db.add(LOAItem(loa_id=loa.id, function_code="04", subfunction_code="122",
                   program_code="0002", action_code="2002",
                   description="Pessoal e encargos sociais", category="despesa",
                   authorized_amount=300000.0))
    db.add(LOAItem(loa_id=loa.id, function_code="04", subfunction_code="122",
                   program_code="0003", action_code="2003",
                   description="Outras despesas correntes", category="despesa",
                   authorized_amount=180000.0))
    db.flush()

    # Receitas no 1º bimestre (jan-fev) and 2nd bimestre (mar-abr)
    db.add(RevenueEntry(description="IPTU Jan", amount=80000.0,
                        entry_date=date(YEAR, 1, 15)))
    db.add(RevenueEntry(description="ISS Fev", amount=60000.0,
                        entry_date=date(YEAR, 2, 20)))
    db.add(RevenueEntry(description="FPM Mar", amount=75000.0,
                        entry_date=date(YEAR, 3, 10)))
    db.flush()

    # Extra vendor and commitment for testing (seed already adds some)
    vendor = db.query(Vendor).first()
    # Commitment pago no 1º bimestre
    c1 = Commitment(number=f"RREO-TEST-001", description="Serviços 1",
                    amount=50000.0, fiscal_year_id=_FY_ID,
                    department_id=1, vendor_id=vendor.id, status="pago")
    db.add(c1)
    db.flush()
    db.add(Liquidation(commitment_id=c1.id, amount=50000.0))
    db.add(Payment(commitment_id=c1.id, amount=50000.0,
                   payment_date=date(YEAR, 1, 25)))

    # Commitment pago no 2º bimestre
    c2 = Commitment(number=f"RREO-TEST-002", description="Serviços 2",
                    amount=30000.0, fiscal_year_id=_FY_ID,
                    department_id=1, vendor_id=vendor.id, status="pago")
    db.add(c2)
    db.flush()
    db.add(Liquidation(commitment_id=c2.id, amount=30000.0))
    db.add(Payment(commitment_id=c2.id, amount=30000.0,
                   payment_date=date(YEAR, 3, 5)))

    # Commitment empenhado (não pago) — contribui para dívida
    c3 = Commitment(number="RREO-TEST-003", description="Pendente",
                    amount=15000.0, fiscal_year_id=_FY_ID,
                    department_id=1, vendor_id=vendor.id, status="empenhado")
    db.add(c3)
    db.flush()

    # Folha de pagamento — 1º quadrimestre (jan-abr)
    emp = db.query(Employee).first()
    for m in ["01", "02", "03", "04"]:
        month = f"{YEAR}-{m}"
        ps = db.query(Payslip).filter(Payslip.month == month,
                                      Payslip.employee_id == emp.id).first()
        if not ps:
            db.add(Payslip(employee_id=emp.id, month=month,
                           gross_amount=5000.0, deductions=550.0, net_amount=4450.0))

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_rreo_rgf.db")
    except FileNotFoundError:
        pass


def auth_headers(username="admin1", password="demo123"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    token = r.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


H = auth_headers


# ── RREO ─────────────────────────────────────────────────────────────────────

def test_rreo_estrutura_basica():
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=1", headers=H())
    assert r.status_code == 200, r.text
    d = r.json()
    assert "cabecalho" in d
    assert "linhas" in d
    assert "indicadores" in d
    assert d["cabecalho"]["exercicio"] == YEAR
    assert d["cabecalho"]["bimestre"] == 1


def test_rreo_cabecalho_bimestre():
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=2", headers=H())
    d = r.json()
    assert d["cabecalho"]["bimestre"] == 2
    assert d["cabecalho"]["periodo_bimestre"]["inicio"].startswith(f"{YEAR}-03")


def test_rreo_linhas_nomes():
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=1", headers=H())
    descricoes = [l["descricao"] for l in r.json()["linhas"]]
    assert any("Receita Prevista" in d for d in descricoes)
    assert any("Receita Arrecadada" in d for d in descricoes)
    assert any("Despesa Paga" in d for d in descricoes)
    assert any("Despesa Liquidada" in d for d in descricoes)


def test_rreo_receita_arrecadada_bimestre1():
    """Receita bimestre 1 = jan+fev = 80000+60000 = 140000."""
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=1", headers=H())
    linhas = {l["descricao"]: l for l in r.json()["linhas"]}
    assert linhas["Receita Arrecadada"]["bimestre"] == 140000.0
    assert linhas["Receita Arrecadada"]["acumulado"] == 140000.0


def test_rreo_receita_arrecadada_bimestre2():
    """Receita bimestre 2 = mar-abr = 75000 (apenas março). Acumulado = 215000."""
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=2", headers=H())
    linhas = {l["descricao"]: l for l in r.json()["linhas"]}
    assert linhas["Receita Arrecadada"]["bimestre"] == 75000.0
    assert linhas["Receita Arrecadada"]["acumulado"] == 215000.0


def test_rreo_receita_prevista_loa():
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=1", headers=H())
    linhas = {l["descricao"]: l for l in r.json()["linhas"]}
    assert linhas["Receita Prevista (LOA)"]["acumulado"] == 500000.0


def test_rreo_despesa_paga_bimestre1():
    """Despesa paga bim 1 = pagamento de 50000 em jan."""
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=1", headers=H())
    linhas = {l["descricao"]: l for l in r.json()["linhas"]}
    assert linhas["Despesa Paga"]["bimestre"] == 50000.0


def test_rreo_indicadores_presentes():
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=1", headers=H())
    ind = r.json()["indicadores"]
    assert "saldo_execucao_acumulado" in ind
    assert "pct_receita_realizada" in ind
    assert "resultado" in ind
    assert ind["resultado"] in {"superavit", "deficit"}


def test_rreo_csv():
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=1&export=csv", headers=H())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "Receita Prevista" in r.text
    assert "Despesa Paga" in r.text


def test_rreo_csv_nome_arquivo():
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=2&export=csv", headers=H())
    cd = r.headers.get("content-disposition", "")
    assert f"rreo_{YEAR}_bim2" in cd


def test_rreo_default_sem_parametros():
    """Sem parâmetros, usa ano corrente e bimestre corrente."""
    r = client.get("/lrf/rreo", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["cabecalho"]["exercicio"] == YEAR


def test_rreo_requer_autenticacao():
    r = client.get(f"/lrf/rreo?ano={YEAR}&bimestre=1")
    assert r.status_code == 401


# ── RGF ───────────────────────────────────────────────────────────────────────

def test_rgf_estrutura_basica():
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1", headers=H())
    assert r.status_code == 200, r.text
    d = r.json()
    assert "cabecalho" in d
    assert "linhas" in d
    assert "indicadores" in d
    assert d["cabecalho"]["exercicio"] == YEAR
    assert d["cabecalho"]["quadrimestre"] == 1


def test_rgf_cabecalho_quadrimestre():
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=2", headers=H())
    d = r.json()
    assert d["cabecalho"]["quadrimestre"] == 2
    assert d["cabecalho"]["periodo_quadrimestre"]["inicio"].startswith(f"{YEAR}-05")


def test_rgf_linhas_nomes():
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1", headers=H())
    descricoes = [l["descricao"] for l in r.json()["linhas"]]
    assert any("RCL" in d for d in descricoes)
    assert any("Pessoal" in d for d in descricoes)
    assert any("Dívida" in d for d in descricoes)
    assert any("Disponibilidade" in d for d in descricoes)


def test_rgf_indicadores_chaves():
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1", headers=H())
    ind = r.json()["indicadores"]
    assert "rcl_12meses" in ind
    assert "despesa_pessoal_acumulada" in ind
    assert "limite_pessoal_60pct_rcl" in ind
    assert "pct_despesa_pessoal_rcl" in ind
    assert "situacao_despesa_pessoal" in ind
    assert ind["situacao_despesa_pessoal"] in {"REGULAR", "ALERTA", "EXCEDIDO"}
    assert "divida_consolidada" in ind


def test_rgf_despesa_pessoal_positiva():
    """Payslips lançados em setup devem gerar despesa pessoal > 0."""
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1", headers=H())
    ind = r.json()["indicadores"]
    # At least 1 payslip of 5000 for jan–apr
    assert ind["despesa_pessoal_acumulada"] >= 5000.0


def test_rgf_divida_consolidada_inclui_empenhados():
    """c3 empenhado (15000) deve aparecer na dívida consolidada."""
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1", headers=H())
    ind = r.json()["indicadores"]
    # Seed also adds 2 empenhados, so total >= 15000
    assert ind["divida_consolidada"] >= 15000.0


def test_rgf_limite_pessoal_calculado():
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1", headers=H())
    ind = r.json()["indicadores"]
    assert ind["limite_pessoal_60pct_rcl"] == round(ind["rcl_12meses"] * 0.60, 2)


def test_rgf_csv():
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1&export=csv", headers=H())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "RCL" in r.text
    assert "Pessoal" in r.text
    assert "Dívida" in r.text


def test_rgf_csv_nome_arquivo():
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1&export=csv", headers=H())
    cd = r.headers.get("content-disposition", "")
    assert f"rgf_{YEAR}_quad1" in cd


def test_rgf_default_sem_parametros():
    r = client.get("/lrf/rgf", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["cabecalho"]["exercicio"] == YEAR


def test_rgf_requer_autenticacao():
    r = client.get(f"/lrf/rgf?ano={YEAR}&quadrimestre=1")
    assert r.status_code == 401
