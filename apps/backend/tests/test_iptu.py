"""Testes: IPTU automático, relatório de arrecadação e parcelamento de dívida ativa."""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_iptu.db"

from datetime import date, timedelta

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AliquotaIPTU,
    Contribuinte,
    DividaAtiva,
    ImovelCadastral,
    LancamentoTributario,
    ParcelamentoDivida,
    ParcelaDivida,
)
from app.seed import seed_data

client = TestClient(app)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    _seed_fixtures(db)
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_iptu.db")
    except FileNotFoundError:
        pass


def _seed_fixtures(db):
    """Cria contribuinte, imóveis, alíquotas e lançamento para os testes."""
    contrib = Contribuinte(cpf_cnpj="999.888.777-66", nome="Contribuinte IPTU Teste", tipo="PF")
    db.add(contrib)
    db.flush()

    imovel_res = ImovelCadastral(
        inscricao="IPTU-TEST-001",
        contribuinte_id=contrib.id,
        logradouro="Rua das Alíquotas",
        numero="10",
        bairro="Centro",
        area_terreno=200.0,
        area_construida=100.0,
        valor_venal=200_000.0,
        uso="residencial",
        ativo=True,
    )
    imovel_com = ImovelCadastral(
        inscricao="IPTU-TEST-002",
        contribuinte_id=contrib.id,
        logradouro="Av. Comercial",
        numero="200",
        bairro="Centro",
        area_terreno=400.0,
        area_construida=300.0,
        valor_venal=500_000.0,
        uso="comercial",
        ativo=True,
    )
    imovel_zero = ImovelCadastral(
        inscricao="IPTU-TEST-003",
        contribuinte_id=contrib.id,
        logradouro="Rua sem Valor",
        numero="1",
        bairro="Sul",
        area_terreno=100.0,
        area_construida=0.0,
        valor_venal=0.0,   # deve ser ignorado ao gerar IPTU
        uso="residencial",
        ativo=True,
    )
    db.add_all([imovel_res, imovel_com, imovel_zero])

    # Alíquotas para exercício 2026
    db.add(AliquotaIPTU(exercicio=2026, uso="residencial", aliquota=0.005, descricao="0.5% residencial"))
    db.add(AliquotaIPTU(exercicio=2026, uso="comercial",   aliquota=0.012, descricao="1.2% comercial"))

    # Lançamento pago para relatório de arrecadação
    lanc_pago = LancamentoTributario(
        contribuinte_id=contrib.id,
        imovel_id=None,
        tributo="IPTU",
        competencia="2025-01",
        exercicio=2025,
        valor_principal=1_500.0,
        valor_total=1_500.0,
        vencimento=date(2025, 3, 31),
        status="pago",
        data_pagamento=date(2025, 3, 25),
    )
    db.add(lanc_pago)

    # Lançamento em dívida ativa para parcelamento
    lanc_divida = LancamentoTributario(
        contribuinte_id=contrib.id,
        imovel_id=None,
        tributo="IPTU",
        competencia="2023-01",
        exercicio=2023,
        valor_principal=3_000.0,
        valor_total=3_000.0,
        vencimento=date(2023, 3, 31),
        status="inscrito_divida",
    )
    db.add(lanc_divida)
    db.flush()

    divida = DividaAtiva(
        lancamento_id=lanc_divida.id,
        contribuinte_id=contrib.id,
        numero_inscricao="DA-IPTU-TEST-001",
        tributo="IPTU",
        exercicio=2023,
        valor_original=3_000.0,
        valor_atualizado=3_300.0,
        data_inscricao=date(2023, 4, 1),
        status="ativa",
    )
    db.add(divida)
    db.commit()


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


# ── AlíquotasIPTU — CRUD ──────────────────────────────────────────────────────

def test_list_aliquotas_exercicio():
    resp = client.get("/tributario/aliquotas-iptu?exercicio=2026", headers=auth_headers("admin1"))
    assert resp.status_code == 200
    items = resp.json()
    assert len(items) >= 2
    usos = {i["uso"] for i in items}
    assert "residencial" in usos
    assert "comercial" in usos


def test_create_aliquota_nova():
    resp = client.post(
        "/tributario/aliquotas-iptu",
        json={"exercicio": 2026, "uso": "industrial", "aliquota": 0.015, "descricao": "1.5% industrial"},
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["uso"] == "industrial"
    assert data["aliquota"] == 0.015


def test_create_aliquota_duplicata_rejeitada():
    # residencial para 2026 já existe
    resp = client.post(
        "/tributario/aliquotas-iptu",
        json={"exercicio": 2026, "uso": "residencial", "aliquota": 0.008},
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 400


def test_update_aliquota():
    items = client.get("/tributario/aliquotas-iptu?exercicio=2026", headers=auth_headers("admin1")).json()
    res_item = next(i for i in items if i["uso"] == "residencial")
    resp = client.put(
        f"/tributario/aliquotas-iptu/{res_item['id']}",
        json={"aliquota": 0.006},
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 200
    assert resp.json()["aliquota"] == 0.006
    # Reset
    client.put(f"/tributario/aliquotas-iptu/{res_item['id']}", json={"aliquota": 0.005}, headers=auth_headers("admin1"))


def test_delete_aliquota():
    # Create a throwaway aliquota then delete it
    r = client.post(
        "/tributario/aliquotas-iptu",
        json={"exercicio": 2099, "uso": "rural", "aliquota": 0.001},
        headers=auth_headers("admin1"),
    )
    assert r.status_code == 201
    aid = r.json()["id"]
    del_r = client.delete(f"/tributario/aliquotas-iptu/{aid}", headers=auth_headers("admin1"))
    assert del_r.status_code == 204


# ── Geração automática de IPTU ────────────────────────────────────────────────

def test_gerar_iptu_sem_aliquotas_retorna_422():
    resp = client.post(
        "/tributario/lancamentos/gerar-iptu?exercicio=1900&vencimento=1900-03-31",
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 422


def test_gerar_iptu_cria_lancamentos():
    resp = client.post(
        "/tributario/lancamentos/gerar-iptu?exercicio=2026&vencimento=2026-03-31",
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["exercicio"] == 2026
    # At least 2 imóveis with valor_venal > 0 and aliquota configured
    assert data["gerados"] >= 2
    # Imóvel com valor_venal = 0 deve ser ignorado
    assert data["ignorados_valor_zero"] >= 1


def test_gerar_iptu_calcula_valor_correto():
    """Verifica que valor_principal = valor_venal * aliquota."""
    db = SessionLocal()
    try:
        imovel = db.query(ImovelCadastral).filter_by(inscricao="IPTU-TEST-001").first()
        aliquota = db.query(AliquotaIPTU).filter_by(exercicio=2026, uso="residencial").first()
        lancamento = db.query(LancamentoTributario).filter_by(
            imovel_id=imovel.id, tributo="IPTU", exercicio=2026
        ).first()
        assert lancamento is not None
        expected = round(imovel.valor_venal * aliquota.aliquota, 2)
        assert lancamento.valor_principal == expected
        assert lancamento.valor_total == expected
    finally:
        db.close()


def test_gerar_iptu_idempotente():
    """Chamar gerar-iptu novamente para o mesmo exercício não duplica lançamentos."""
    resp1 = client.post(
        "/tributario/lancamentos/gerar-iptu?exercicio=2026&vencimento=2026-03-31",
        headers=auth_headers("admin1"),
    )
    assert resp1.status_code == 200
    # Na segunda chamada tudo deve ser ignorado (já existia)
    assert resp1.json()["gerados"] == 0
    assert resp1.json()["ignorados_ja_existia"] >= 2


def test_gerar_iptu_ignora_imovel_sem_aliquota():
    """Imóvel com uso 'rural' não tem alíquota 2026 → deve ser contado em ignorados_sem_aliquota."""
    # Add temporary rural imovel
    db = SessionLocal()
    try:
        contrib = db.query(Contribuinte).filter_by(cpf_cnpj="999.888.777-66").first()
        rural = ImovelCadastral(
            inscricao="IPTU-TEST-RURAL",
            contribuinte_id=contrib.id,
            logradouro="Estrada Rural",
            numero="KM5",
            bairro="Zona Rural",
            area_terreno=10000.0,
            area_construida=200.0,
            valor_venal=80_000.0,
            uso="rural",
            ativo=True,
        )
        db.add(rural)
        db.commit()
    finally:
        db.close()

    # 2026 has no 'rural' aliquota → ignorados_sem_aliquota should be >= 1
    resp = client.post(
        "/tributario/lancamentos/gerar-iptu?exercicio=2026&vencimento=2026-03-31",
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 200
    assert resp.json()["ignorados_sem_aliquota"] >= 1


# ── Relatório de Arrecadação ──────────────────────────────────────────────────

def test_relatorio_arrecadacao_json():
    resp = client.get(
        "/tributario/relatorio/arrecadacao?tributo=IPTU&exercicio=2025",
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "total_arrecadado" in data
    assert "registros" in data
    assert data["total_arrecadado"] >= 1_500.0


def test_relatorio_arrecadacao_sem_filtro():
    resp = client.get("/tributario/relatorio/arrecadacao", headers=auth_headers("admin1"))
    assert resp.status_code == 200
    data = resp.json()
    assert "total_arrecadado" in data
    assert isinstance(data["registros"], list)


def test_relatorio_arrecadacao_csv():
    resp = client.get(
        "/tributario/relatorio/arrecadacao?export=csv",
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().split("\n")
    assert lines[0].startswith("tributo")
    # Must have header + at least one data row
    assert len(lines) >= 2


def test_relatorio_sem_pagamentos_retorna_zero():
    resp = client.get(
        "/tributario/relatorio/arrecadacao?tributo=TAXA_LIXO&exercicio=1800",
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 200
    assert resp.json()["total_arrecadado"] == 0.0
    assert resp.json()["registros"] == []


# ── Parcelamento de Dívida Ativa ──────────────────────────────────────────────

def _get_divida_id() -> int:
    db = SessionLocal()
    try:
        d = db.query(DividaAtiva).filter_by(numero_inscricao="DA-IPTU-TEST-001").first()
        return d.id
    finally:
        db.close()


def test_create_parcelamento():
    divida_id = _get_divida_id()
    resp = client.post(
        "/tributario/parcelamentos",
        json={
            "divida_id": divida_id,
            "numero_parcelas": 6,
            "valor_total": 3_300.0,
            "data_acordo": "2026-05-01",
            "observacoes": "Parcelamento em 6x",
        },
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 201
    data = resp.json()
    assert data["numero_parcelas"] == 6
    assert data["status"] == "ativo"
    assert len(data["parcelas"]) == 6
    # Check soma das parcelas == valor_total
    total = sum(p["valor"] for p in data["parcelas"])
    assert round(total, 2) == 3_300.0


def test_create_parcelamento_duplicado_rejeitado():
    """Não pode criar segundo parcelamento para dívida já parcelada."""
    divida_id = _get_divida_id()
    resp = client.post(
        "/tributario/parcelamentos",
        json={"divida_id": divida_id, "numero_parcelas": 3, "valor_total": 3_300.0, "data_acordo": "2026-06-01"},
        headers=auth_headers("admin1"),
    )
    # 400 = parcelamento ativo já existe; 422 = status da dívida não permite parcelar
    assert resp.status_code in (400, 422)


def test_divida_fica_parcelada():
    """Após criar parcelamento, status da dívida deve ser 'parcelada'."""
    divida_id = _get_divida_id()
    resp = client.get(f"/tributario/divida-ativa/{divida_id}", headers=auth_headers("admin1"))
    assert resp.status_code == 200
    assert resp.json()["status"] == "parcelada"


def test_list_parcelamentos():
    divida_id = _get_divida_id()
    resp = client.get(f"/tributario/parcelamentos?divida_id={divida_id}", headers=auth_headers("admin1"))
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1


def test_get_parcelamento_detail():
    divida_id = _get_divida_id()
    listagem = client.get(f"/tributario/parcelamentos?divida_id={divida_id}", headers=auth_headers("admin1")).json()
    pid = listagem["items"][0]["id"]
    resp = client.get(f"/tributario/parcelamentos/{pid}", headers=auth_headers("admin1"))
    assert resp.status_code == 200
    assert resp.json()["id"] == pid
    assert len(resp.json()["parcelas"]) == 6


def test_pagar_parcela():
    divida_id = _get_divida_id()
    listagem = client.get(f"/tributario/parcelamentos?divida_id={divida_id}", headers=auth_headers("admin1")).json()
    pid = listagem["items"][0]["id"]
    detail = client.get(f"/tributario/parcelamentos/{pid}", headers=auth_headers("admin1")).json()
    parcela_id = detail["parcelas"][0]["id"]

    resp = client.post(
        f"/tributario/parcelamentos/{pid}/parcelas/{parcela_id}/pagar",
        json={"data_pagamento": "2026-05-15"},
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
    assert resp.json()["parcelamento_quitado"] is False


def test_pagar_parcela_duplicada_rejeitada():
    divida_id = _get_divida_id()
    listagem = client.get(f"/tributario/parcelamentos?divida_id={divida_id}", headers=auth_headers("admin1")).json()
    pid = listagem["items"][0]["id"]
    detail = client.get(f"/tributario/parcelamentos/{pid}", headers=auth_headers("admin1")).json()
    # parcela[0] already paid in previous test
    parcela_id = detail["parcelas"][0]["id"]
    resp = client.post(
        f"/tributario/parcelamentos/{pid}/parcelas/{parcela_id}/pagar",
        json={"data_pagamento": "2026-05-20"},
        headers=auth_headers("admin1"),
    )
    assert resp.status_code == 400


def test_quitacao_total_muda_status():
    """Pagar todas as parcelas deve quitar o parcelamento e a dívida."""
    divida_id = _get_divida_id()
    listagem = client.get(f"/tributario/parcelamentos?divida_id={divida_id}", headers=auth_headers("admin1")).json()
    pid = listagem["items"][0]["id"]
    detail = client.get(f"/tributario/parcelamentos/{pid}", headers=auth_headers("admin1")).json()

    # Pay remaining parcelas (2 through 6)
    for p in detail["parcelas"][1:]:
        r = client.post(
            f"/tributario/parcelamentos/{pid}/parcelas/{p['id']}/pagar",
            json={"data_pagamento": "2026-06-01"},
            headers=auth_headers("admin1"),
        )
        assert r.status_code == 200

    # Last payment should report quitado
    last = detail["parcelas"][-1]
    r = client.post(
        f"/tributario/parcelamentos/{pid}/parcelas/{last['id']}/pagar",
        json={"data_pagamento": "2026-11-01"},
        headers=auth_headers("admin1"),
    )
    # Either already paid (400) or quitado
    assert r.status_code in (200, 400)

    # Parcelamento should now be quitado
    parc = client.get(f"/tributario/parcelamentos/{pid}", headers=auth_headers("admin1")).json()
    assert parc["status"] == "quitado"

    # Dívida should also be quitada
    divida_resp = client.get(f"/tributario/divida-ativa/{divida_id}", headers=auth_headers("admin1")).json()
    assert divida_resp["status"] == "quitada"


def test_parcelamento_divida_nao_ativa_rejeitado():
    """Tentar parcelar dívida já quitada deve ser rejeitado."""
    divida_id = _get_divida_id()
    resp = client.post(
        "/tributario/parcelamentos",
        json={"divida_id": divida_id, "numero_parcelas": 3, "valor_total": 1000.0, "data_acordo": "2026-07-01"},
        headers=auth_headers("admin1"),
    )
    # 400 (ativo duplicado) or 422 (status não permite)
    assert resp.status_code in (400, 422)
