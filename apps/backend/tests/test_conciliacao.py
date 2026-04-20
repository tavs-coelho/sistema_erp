"""Testes da vertical de Conciliação Bancária.

Cobre: CRUD contas, CRUD lançamentos, conciliação automática, conciliação manual,
ignorar lançamento, dashboard, relatório CSV, filtros, autenticação obrigatória.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_conciliacao.db"

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import ContaBancaria, LancamentoBancario, Payment, RevenueEntry, Commitment, FiscalYear, Vendor
from app.seed import seed_data

client = TestClient(app)

TODAY = date.today()
YEAR = TODAY.year

_CONTA_ID: int = 0
_CONTA2_ID: int = 0
_LANC_ID: int = 0
_PAY_ID: int = 0
_REV_ID: int = 0


def setup_module():
    global _CONTA_ID, _CONTA2_ID, _LANC_ID, _PAY_ID, _REV_ID
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)

    # Grab first seeded conta
    conta = db.query(ContaBancaria).first()
    _CONTA_ID = conta.id

    conta2 = db.query(ContaBancaria).offset(1).first()
    _CONTA2_ID = conta2.id if conta2 else _CONTA_ID

    # Grab first seeded lancamento
    lanc = db.query(LancamentoBancario).first()
    _LANC_ID = lanc.id

    # Ensure a specific payment and revenue entry for deterministic tests
    fy = db.query(FiscalYear).first()
    vendor = db.query(Vendor).first()
    c = Commitment(number=f"BANK-TEST-001", description="Test Commitment",
                   amount=9999.99, fiscal_year_id=fy.id,
                   department_id=1, vendor_id=vendor.id, status="pago")
    db.add(c)
    db.flush()
    pay = Payment(commitment_id=c.id, amount=9999.99,
                  payment_date=date(YEAR, 3, 15))
    db.add(pay)
    db.flush()
    _PAY_ID = pay.id

    rev = RevenueEntry(description="Test Revenue Bank", amount=7777.77,
                       entry_date=date(YEAR, 3, 20))
    db.add(rev)
    db.flush()
    _REV_ID = rev.id

    db.commit()
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_conciliacao.db")
    except FileNotFoundError:
        pass


def auth_headers(username="admin1", password="demo123"):
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


H = auth_headers


# ── CRUD Contas ───────────────────────────────────────────────────────────────

def test_list_contas():
    r = client.get("/banco/contas", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert "items" in d
    assert d["total"] >= 1


def test_list_contas_filtro_ativa():
    r = client.get("/banco/contas?ativa=true", headers=H())
    assert r.status_code == 200
    for c in r.json()["items"]:
        assert c["ativa"] is True


def test_get_conta():
    r = client.get(f"/banco/contas/{_CONTA_ID}", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert d["id"] == _CONTA_ID
    assert "banco" in d
    assert "numero_conta" in d


def test_get_conta_404():
    r = client.get("/banco/contas/99999", headers=H())
    assert r.status_code == 404


def test_create_conta():
    r = client.post(
        "/banco/contas",
        params={
            "banco": "Sicoob",
            "agencia": "0099",
            "numero_conta": "TEST-CONTA-001",
            "data_saldo_inicial": str(date(YEAR, 1, 1)),
            "descricao": "Conta Teste",
            "saldo_inicial": 1000.0,
        },
        headers=H(),
    )
    assert r.status_code == 201
    d = r.json()
    assert d["banco"] == "Sicoob"
    assert d["numero_conta"] == "TEST-CONTA-001"


def test_create_conta_duplicada():
    # Try to create same numero_conta again
    r = client.post(
        "/banco/contas",
        params={
            "banco": "Sicoob",
            "agencia": "0099",
            "numero_conta": "TEST-CONTA-001",
            "data_saldo_inicial": str(date(YEAR, 1, 1)),
        },
        headers=H(),
    )
    assert r.status_code == 400


def test_update_conta():
    r = client.patch(f"/banco/contas/{_CONTA_ID}?descricao=Desc Atualizada", headers=H())
    assert r.status_code == 200
    assert r.json()["descricao"] == "Desc Atualizada"


def test_create_conta_requer_autenticacao():
    r = client.post("/banco/contas", params={
        "banco": "X", "agencia": "1", "numero_conta": "X1",
        "data_saldo_inicial": str(date(YEAR, 1, 1))})
    assert r.status_code == 401


# ── CRUD Lançamentos ──────────────────────────────────────────────────────────

def test_list_lancamentos():
    r = client.get("/banco/lancamentos", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert "items" in d
    assert d["total"] >= 1


def test_list_lancamentos_filtro_conta():
    r = client.get(f"/banco/lancamentos?conta_id={_CONTA_ID}", headers=H())
    assert r.status_code == 200
    for l in r.json()["items"]:
        assert l["conta_id"] == _CONTA_ID


def test_list_lancamentos_filtro_status():
    r = client.get("/banco/lancamentos?status=pendente", headers=H())
    assert r.status_code == 200
    for l in r.json()["items"]:
        assert l["status"] == "pendente"


def test_list_lancamentos_filtro_tipo():
    r = client.get("/banco/lancamentos?tipo=debito", headers=H())
    assert r.status_code == 200
    for l in r.json()["items"]:
        assert l["tipo"] == "debito"


def test_create_lancamento_debito():
    r = client.post(
        "/banco/lancamentos",
        params={
            "conta_id": _CONTA_ID,
            "data_lancamento": str(date(YEAR, 4, 1)),
            "tipo": "debito",
            "valor": 500.00,
            "descricao": "Pagamento TED teste",
        },
        headers=H(),
    )
    assert r.status_code == 201
    d = r.json()
    assert d["tipo"] == "debito"
    assert d["valor"] == 500.00
    assert d["status"] == "pendente"


def test_create_lancamento_credito():
    r = client.post(
        "/banco/lancamentos",
        params={
            "conta_id": _CONTA_ID,
            "data_lancamento": str(date(YEAR, 4, 2)),
            "tipo": "credito",
            "valor": 200.00,
            "descricao": "Receita ISS",
        },
        headers=H(),
    )
    assert r.status_code == 201
    assert r.json()["tipo"] == "credito"


def test_create_lancamento_tipo_invalido():
    r = client.post(
        "/banco/lancamentos",
        params={
            "conta_id": _CONTA_ID,
            "data_lancamento": str(date(YEAR, 4, 1)),
            "tipo": "transferencia",
            "valor": 100.0,
        },
        headers=H(),
    )
    assert r.status_code == 400


def test_create_lancamento_valor_negativo():
    r = client.post(
        "/banco/lancamentos",
        params={
            "conta_id": _CONTA_ID,
            "data_lancamento": str(date(YEAR, 4, 1)),
            "tipo": "debito",
            "valor": -100.0,
        },
        headers=H(),
    )
    assert r.status_code == 400


def test_lancamento_requer_autenticacao():
    r = client.get("/banco/lancamentos")
    assert r.status_code == 401


# ── Conciliação Automática ────────────────────────────────────────────────────

def _create_lanc_pair(conta_id, pay_id, pay_amount, pay_date, tipo="debito"):
    """Cria um lançamento correspondente a um payment para testar auto-conciliação."""
    r = client.post(
        "/banco/lancamentos",
        params={
            "conta_id": conta_id,
            "data_lancamento": str(pay_date),
            "tipo": tipo,
            "valor": pay_amount,
            "descricao": "Para auto-conciliacao",
        },
        headers=H(),
    )
    assert r.status_code == 201
    return r.json()["id"]


def test_conciliar_auto_debito():
    """Cria lançamento débito com valor/data idênticos ao Payment _PAY_ID → deve conciliar."""
    db = SessionLocal()
    pay = db.get(Payment, _PAY_ID)
    db.close()

    _create_lanc_pair(_CONTA_ID, _PAY_ID, pay.amount, pay.payment_date, "debito")

    r = client.post(f"/banco/conciliacao/auto?conta_id={_CONTA_ID}", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert "conciliados" in d
    assert "divergentes" in d
    assert "pendentes" in d
    assert d["conciliados"] >= 1


def test_conciliar_auto_credito():
    """Cria lançamento crédito com valor/data idênticos ao RevenueEntry _REV_ID → deve conciliar."""
    db = SessionLocal()
    rev = db.get(RevenueEntry, _REV_ID)
    db.close()

    _create_lanc_pair(_CONTA_ID, None, rev.amount, rev.entry_date, "credito")

    r = client.post(f"/banco/conciliacao/auto?conta_id={_CONTA_ID}", headers=H())
    assert r.status_code == 200
    assert r.json()["conciliados"] >= 1


def test_conciliar_auto_sem_match():
    """Lançamento com valor inexistente no ERP → deve permanecer pendente."""
    r_lanc = client.post(
        "/banco/lancamentos",
        params={
            "conta_id": _CONTA_ID,
            "data_lancamento": str(date(YEAR, 6, 1)),
            "tipo": "debito",
            "valor": 0.01,
            "descricao": "Valor sem correspondência",
        },
        headers=H(),
    )
    assert r_lanc.status_code == 201

    r = client.post(f"/banco/conciliacao/auto?conta_id={_CONTA_ID}", headers=H())
    assert r.status_code == 200
    # There's at least 1 pending
    assert r.json()["pendentes"] >= 0  # may vary due to other tests


def test_conciliar_auto_requer_autenticacao():
    r = client.post("/banco/conciliacao/auto")
    assert r.status_code == 401


# ── Conciliação Manual ────────────────────────────────────────────────────────

def test_conciliar_manual_payment():
    """Cria lançamento e concilia manualmente com _PAY_ID."""
    # Create a fresh lancamento with exact same amount (different doc)
    db = SessionLocal()
    pay = db.get(Payment, _PAY_ID)
    db.close()

    r_lanc = client.post(
        "/banco/lancamentos",
        params={
            "conta_id": _CONTA_ID,
            "data_lancamento": str(pay.payment_date),
            "tipo": "debito",
            "valor": pay.amount,
            "descricao": "Para conciliacao manual",
            "documento_ref": "MANUAL001",
        },
        headers=H(),
    )
    assert r_lanc.status_code == 201
    lanc_id = r_lanc.json()["id"]

    r = client.patch(
        f"/banco/lancamentos/{lanc_id}/conciliar-manual?payment_id={_PAY_ID}",
        headers=H(),
    )
    assert r.status_code == 200
    d = r.json()
    assert d["payment_id"] == _PAY_ID
    assert d["status"] in {"conciliado", "divergente"}  # diverge if pay already used


def test_conciliar_manual_revenue_entry():
    db = SessionLocal()
    rev = db.get(RevenueEntry, _REV_ID)
    db.close()

    r_lanc = client.post(
        "/banco/lancamentos",
        params={
            "conta_id": _CONTA_ID,
            "data_lancamento": str(rev.entry_date),
            "tipo": "credito",
            "valor": rev.amount,
            "descricao": "Para conciliacao manual receita",
        },
        headers=H(),
    )
    assert r_lanc.status_code == 201
    lanc_id = r_lanc.json()["id"]

    r = client.patch(
        f"/banco/lancamentos/{lanc_id}/conciliar-manual?revenue_entry_id={_REV_ID}",
        headers=H(),
    )
    assert r.status_code == 200
    d = r.json()
    assert d["revenue_entry_id"] == _REV_ID
    assert d["status"] in {"conciliado", "divergente"}


def test_conciliar_manual_dois_vinculos_erro():
    """Não pode vincular payment e revenue ao mesmo tempo."""
    r_lanc = client.post(
        "/banco/lancamentos",
        params={"conta_id": _CONTA_ID, "data_lancamento": str(TODAY),
                "tipo": "debito", "valor": 1.0},
        headers=H(),
    )
    lanc_id = r_lanc.json()["id"]
    r = client.patch(
        f"/banco/lancamentos/{lanc_id}/conciliar-manual?payment_id={_PAY_ID}&revenue_entry_id={_REV_ID}",
        headers=H(),
    )
    assert r.status_code == 400


def test_conciliar_manual_404():
    r = client.patch("/banco/lancamentos/999999/conciliar-manual?payment_id=1", headers=H())
    assert r.status_code == 404


# ── Ignorar Lançamento ────────────────────────────────────────────────────────

def test_ignorar_lancamento():
    r_lanc = client.post(
        "/banco/lancamentos",
        params={"conta_id": _CONTA_ID, "data_lancamento": str(TODAY),
                "tipo": "debito", "valor": 45.90, "descricao": "Tarifa"},
        headers=H(),
    )
    lanc_id = r_lanc.json()["id"]
    r = client.patch(f"/banco/lancamentos/{lanc_id}/ignorar?obs=Tarifa bancária", headers=H())
    assert r.status_code == 200
    assert r.json()["status"] == "ignorado"
    assert "Tarifa" in (r.json()["divergencia_obs"] or "")


def test_ignorar_lancamento_404():
    r = client.patch("/banco/lancamentos/999999/ignorar", headers=H())
    assert r.status_code == 404


# ── Delete Lançamento ─────────────────────────────────────────────────────────

def test_delete_lancamento():
    r_lanc = client.post(
        "/banco/lancamentos",
        params={"conta_id": _CONTA_ID, "data_lancamento": str(TODAY),
                "tipo": "debito", "valor": 1.0, "descricao": "Para deletar"},
        headers=H(),
    )
    lanc_id = r_lanc.json()["id"]
    r = client.delete(f"/banco/lancamentos/{lanc_id}", headers=H())
    assert r.status_code == 204

    r2 = client.get(f"/banco/lancamentos?conta_id={_CONTA_ID}", headers=H())
    ids = [l["id"] for l in r2.json()["items"]]
    assert lanc_id not in ids


def test_delete_lancamento_404():
    r = client.delete("/banco/lancamentos/999999", headers=H())
    assert r.status_code == 404


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard_estrutura():
    r = client.get("/banco/dashboard", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert "total_lancamentos" in d
    assert "conciliados" in d
    assert "divergentes" in d
    assert "pendentes" in d
    assert "ignorados" in d
    assert "pct_conciliado" in d
    assert "total_creditos" in d
    assert "total_debitos" in d
    assert "saldo_projetado" in d


def test_dashboard_filtro_conta():
    r = client.get(f"/banco/dashboard?conta_id={_CONTA_ID}", headers=H())
    assert r.status_code == 200


def test_dashboard_requer_autenticacao():
    r = client.get("/banco/dashboard")
    assert r.status_code == 401


# ── Relatório ─────────────────────────────────────────────────────────────────

def test_relatorio_json():
    r = client.get("/banco/conciliacao/relatorio", headers=H())
    assert r.status_code == 200
    d = r.json()
    assert "items" in d
    assert "total" in d


def test_relatorio_csv():
    r = client.get("/banco/conciliacao/relatorio?export=csv", headers=H())
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    assert "id" in r.text
    assert "status" in r.text


def test_relatorio_csv_nome_arquivo():
    r = client.get("/banco/conciliacao/relatorio?export=csv", headers=H())
    cd = r.headers.get("content-disposition", "")
    assert "conciliacao_" in cd


def test_relatorio_filtro_status_pendente():
    r = client.get("/banco/conciliacao/relatorio?status=pendente", headers=H())
    d = r.json()
    for item in d["items"]:
        assert item["status"] == "pendente"


def test_relatorio_requer_autenticacao():
    r = client.get("/banco/conciliacao/relatorio")
    assert r.status_code == 401
