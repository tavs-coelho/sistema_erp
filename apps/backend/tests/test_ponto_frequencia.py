"""Testes do módulo Ponto e Frequência de Servidores.

Cobre: escala, registro de ponto, cálculo de horas trabalhadas/extras/atrasos,
       faltas, abonos, folha de frequência mensal, exportação CSV, dashboard.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_ponto_frequencia.db"

import calendar
from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    AbonoFalta,
    Employee,
    EscalaServidor,
    RegistroPonto,
)
from app.seed import seed_data

client = TestClient(app)

YEAR = date.today().year
MONTH = date.today().month
# Use mes anterior para ter dados completos
REF_YEAR, REF_MONTH = (YEAR - 1, 12) if MONTH == 1 else (YEAR, MONTH - 1)
PERIODO = f"{REF_YEAR}-{REF_MONTH:02d}"
_, DAYS_IN_MONTH = calendar.monthrange(REF_YEAR, REF_MONTH)


def setup_module():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    seed_data(db)
    db.close()


def teardown_module():
    Base.metadata.drop_all(bind=engine)
    try:
        os.remove("./test_ponto_frequencia.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    r = client.post("/auth/login", json={"username": username, "password": password})
    assert r.status_code == 200
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


def _first_employee_id() -> int:
    db = SessionLocal()
    emp = db.query(Employee).first()
    db.close()
    return emp.id


def _make_employee(name: str = "Servidor Teste", cpf: str = "000.001.002-03") -> int:
    db = SessionLocal()
    from app.models import Department
    dept = db.query(Department).first()
    emp = Employee(name=name, cpf=cpf, job_title="Técnico", employment_type="Efetivo",
                   base_salary=3000.0, department_id=dept.id)
    db.add(emp)
    db.commit()
    db.refresh(emp)
    eid = emp.id
    db.close()
    return eid


def _next_weekday(year: int, month: int, skip_days: int = 0) -> date:
    """Retorna o (skip_days+1)-ésimo dia útil do mês."""
    count = 0
    for day in range(1, calendar.monthrange(year, month)[1] + 1):
        d = date(year, month, day)
        if d.weekday() < 5:
            if count == skip_days:
                return d
            count += 1
    raise ValueError("Sem dias úteis suficientes")


# ── Escala ────────────────────────────────────────────────────────────────────

def test_criar_escala():
    headers = auth_headers("admin1")
    emp = _make_employee("Escala Teste", "111.222.333-01")
    resp = client.post("/ponto/escalas", json={
        "employee_id": emp,
        "horas_dia": 8.0,
        "dias_semana": "12345",
        "hora_entrada": "08:00",
        "hora_saida": "17:00",
        "hora_inicio_intervalo": "12:00",
        "hora_fim_intervalo": "13:00",
    }, headers=headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["employee_id"] == emp
    assert data["horas_dia"] == 8.0


def test_criar_escala_duplicada_409():
    headers = auth_headers("admin1")
    emp = _make_employee("Escala Dup", "111.222.333-02")
    client.post("/ponto/escalas", json={
        "employee_id": emp, "horas_dia": 8.0, "dias_semana": "12345",
        "hora_entrada": "08:00", "hora_saida": "17:00",
        "hora_inicio_intervalo": "12:00", "hora_fim_intervalo": "13:00",
    }, headers=headers)
    resp = client.post("/ponto/escalas", json={
        "employee_id": emp, "horas_dia": 6.0, "dias_semana": "12345",
        "hora_entrada": "07:00", "hora_saida": "13:00",
        "hora_inicio_intervalo": "10:00", "hora_fim_intervalo": "10:15",
    }, headers=headers)
    assert resp.status_code == 409


def test_get_escala():
    headers = auth_headers("admin1")
    emp = _make_employee("Escala Get", "111.222.333-03")
    client.post("/ponto/escalas", json={
        "employee_id": emp, "horas_dia": 6.0, "dias_semana": "12345",
        "hora_entrada": "07:00", "hora_saida": "13:00",
        "hora_inicio_intervalo": "10:00", "hora_fim_intervalo": "10:15",
    }, headers=headers)
    resp = client.get(f"/ponto/escalas/{emp}", headers=headers)
    assert resp.status_code == 200
    assert resp.json()["horas_dia"] == 6.0


def test_get_escala_nao_encontrada():
    headers = auth_headers("admin1")
    resp = client.get("/ponto/escalas/999999", headers=headers)
    assert resp.status_code == 404


def test_atualizar_escala():
    headers = auth_headers("admin1")
    emp = _make_employee("Escala Patch", "111.222.333-04")
    client.post("/ponto/escalas", json={
        "employee_id": emp, "horas_dia": 8.0, "dias_semana": "12345",
        "hora_entrada": "08:00", "hora_saida": "17:00",
        "hora_inicio_intervalo": "12:00", "hora_fim_intervalo": "13:00",
    }, headers=headers)
    resp = client.patch(f"/ponto/escalas/{emp}", json={"horas_dia": 6.0, "hora_entrada": "07:30"},
                        headers=headers)
    assert resp.status_code == 200
    assert resp.json()["horas_dia"] == 6.0
    assert resp.json()["hora_entrada"] == "07:30"


def test_escala_sem_permissao():
    headers = auth_headers("read_only1")
    emp = _make_employee("Escala RO", "111.222.333-05")
    resp = client.post("/ponto/escalas", json={
        "employee_id": emp, "horas_dia": 8.0, "dias_semana": "12345",
        "hora_entrada": "08:00", "hora_saida": "17:00",
        "hora_inicio_intervalo": "12:00", "hora_fim_intervalo": "13:00",
    }, headers=headers)
    assert resp.status_code == 403


# ── Registro de Ponto ─────────────────────────────────────────────────────────

def test_registrar_ponto_entrada():
    headers = auth_headers("admin1")
    emp = _make_employee("Ponto Entrada", "222.000.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH)
    resp = client.post("/ponto/registros", json={
        "employee_id": emp,
        "data": str(d),
        "tipo_registro": "entrada",
        "hora_registro": "08:05",
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["tipo_registro"] == "entrada"
    assert resp.json()["hora_registro"] == "08:05"


def test_registrar_ponto_tipo_invalido():
    headers = auth_headers("admin1")
    emp = _make_employee("Ponto Tipo Inv", "222.000.001-02")
    d = _next_weekday(REF_YEAR, REF_MONTH)
    resp = client.post("/ponto/registros", json={
        "employee_id": emp, "data": str(d),
        "tipo_registro": "tipo_invalido", "hora_registro": "08:00",
    }, headers=headers)
    assert resp.status_code == 422


def test_registrar_ponto_duplicado_409():
    headers = auth_headers("admin1")
    emp = _make_employee("Ponto Dup", "222.000.001-03")
    d = _next_weekday(REF_YEAR, REF_MONTH)
    client.post("/ponto/registros", json={
        "employee_id": emp, "data": str(d),
        "tipo_registro": "entrada", "hora_registro": "08:00",
    }, headers=headers)
    resp = client.post("/ponto/registros", json={
        "employee_id": emp, "data": str(d),
        "tipo_registro": "entrada", "hora_registro": "08:10",
    }, headers=headers)
    assert resp.status_code == 409


def test_registrar_todos_tipos_ponto():
    headers = auth_headers("admin1")
    emp = _make_employee("Ponto Completo", "222.000.002-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=2)
    for tipo, hora in [
        ("entrada", "08:00"),
        ("inicio_intervalo", "12:00"),
        ("fim_intervalo", "13:00"),
        ("saida", "17:00"),
    ]:
        resp = client.post("/ponto/registros", json={
            "employee_id": emp, "data": str(d),
            "tipo_registro": tipo, "hora_registro": hora,
        }, headers=headers)
        assert resp.status_code == 201


def test_list_registros():
    headers = auth_headers("admin1")
    emp_id = _first_employee_id()
    resp = client.get(f"/ponto/registros?employee_id={emp_id}", headers=headers)
    assert resp.status_code == 200
    assert "total" in resp.json()


def test_deletar_registro():
    headers = auth_headers("admin1")
    emp = _make_employee("Ponto Delete", "222.000.003-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=3)
    reg = client.post("/ponto/registros", json={
        "employee_id": emp, "data": str(d),
        "tipo_registro": "entrada", "hora_registro": "08:00",
    }, headers=headers)
    rid = reg.json()["id"]
    resp = client.delete(f"/ponto/registros/{rid}", headers=headers)
    assert resp.status_code == 204


# ── Folha de Frequência ───────────────────────────────────────────────────────

def test_folha_frequencia_basica():
    headers = auth_headers("admin1")
    emp_id = _first_employee_id()
    resp = client.get(f"/ponto/folha/{emp_id}/{PERIODO}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["employee_id"] == emp_id
    assert data["periodo"] == PERIODO
    assert "total_dias_uteis" in data
    assert "dias" in data
    assert len(data["dias"]) == DAYS_IN_MONTH


def test_folha_presencas_e_faltas():
    """Verifica que presencas + faltas + faltas_abonadas = total_dias_uteis."""
    headers = auth_headers("admin1")
    emp_id = _first_employee_id()
    resp = client.get(f"/ponto/folha/{emp_id}/{PERIODO}", headers=headers)
    data = resp.json()
    total = data["total_presencas"] + data["total_faltas"] + data["total_faltas_abonadas"]
    assert total == data["total_dias_uteis"]


def test_folha_horas_trabalhadas():
    """Servidor com entrada 08:00, saída 17:00, intervalo 1h → 8h/dia."""
    headers = auth_headers("admin1")
    emp = _make_employee("Horas Teste", "333.001.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=4)
    for tipo, hora in [("entrada", "08:00"), ("inicio_intervalo", "12:00"),
                       ("fim_intervalo", "13:00"), ("saida", "17:00")]:
        client.post("/ponto/registros", json={
            "employee_id": emp, "data": str(d),
            "tipo_registro": tipo, "hora_registro": hora,
        }, headers=headers)
    resp = client.get(f"/ponto/folha/{emp}/{PERIODO}", headers=headers)
    dia = next(x for x in resp.json()["dias"] if x["data"] == str(d))
    assert dia["horas_trabalhadas"] == 8.0
    assert dia["horas_extras"] == 0.0
    assert dia["minutos_atraso"] == 0


def test_folha_horas_extras():
    """Servidor sai às 19h → 2h extras (escala padrão 8h)."""
    headers = auth_headers("admin1")
    emp = _make_employee("Horas Extras Teste", "333.002.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=5)
    for tipo, hora in [("entrada", "08:00"), ("inicio_intervalo", "12:00"),
                       ("fim_intervalo", "13:00"), ("saida", "19:00")]:
        client.post("/ponto/registros", json={
            "employee_id": emp, "data": str(d),
            "tipo_registro": tipo, "hora_registro": hora,
        }, headers=headers)
    resp = client.get(f"/ponto/folha/{emp}/{PERIODO}", headers=headers)
    dia = next(x for x in resp.json()["dias"] if x["data"] == str(d))
    assert dia["horas_trabalhadas"] == 10.0
    assert dia["horas_extras"] == 2.0


def test_folha_atraso():
    """Servidor chega às 08:30 → 30 min de atraso."""
    headers = auth_headers("admin1")
    emp = _make_employee("Atraso Teste", "333.003.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=6)
    for tipo, hora in [("entrada", "08:30"), ("inicio_intervalo", "12:00"),
                       ("fim_intervalo", "13:00"), ("saida", "17:00")]:
        client.post("/ponto/registros", json={
            "employee_id": emp, "data": str(d),
            "tipo_registro": tipo, "hora_registro": hora,
        }, headers=headers)
    resp = client.get(f"/ponto/folha/{emp}/{PERIODO}", headers=headers)
    dia = next(x for x in resp.json()["dias"] if x["data"] == str(d))
    assert dia["minutos_atraso"] == 30
    assert dia["status_dia"] == "presente"


def test_folha_falta_sem_abono():
    """Dia útil sem marcação → falta."""
    headers = auth_headers("admin1")
    emp = _make_employee("Falta Teste", "333.004.001-01")
    resp = client.get(f"/ponto/folha/{emp}/{PERIODO}", headers=headers)
    data = resp.json()
    # Sem nenhum registro, todos os dias úteis são falta
    assert data["total_faltas"] == data["total_dias_uteis"]
    dias_falta = [d for d in data["dias"] if d["dia_util"] and d["falta"]]
    for dia in dias_falta:
        assert dia["status_dia"] == "falta"
        assert dia["abonado"] is False


def test_folha_falta_abonada():
    """Falta com abono aprovado → falta_abonada."""
    headers = auth_headers("admin1")
    emp = _make_employee("Abono Teste", "333.005.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=7)
    # Não registra ponto → falta
    # Cria abono aprovado
    abono_resp = client.post("/ponto/abonos", json={
        "employee_id": emp, "data": str(d), "tipo": "falta",
        "motivo": "Atestado médico",
    }, headers=headers)
    abono_id = abono_resp.json()["id"]
    client.patch(f"/ponto/abonos/{abono_id}", json={"status": "aprovado"}, headers=headers)

    resp = client.get(f"/ponto/folha/{emp}/{PERIODO}", headers=headers)
    dia = next(x for x in resp.json()["dias"] if x["data"] == str(d))
    assert dia["falta"] is True
    assert dia["abonado"] is True
    assert dia["status_dia"] == "falta_abonada"


def test_folha_fim_semana_nao_conta_falta():
    """Sábado e domingo não são faltas."""
    headers = auth_headers("admin1")
    emp = _make_employee("FimSemana Teste", "333.006.001-01")
    resp = client.get(f"/ponto/folha/{emp}/{PERIODO}", headers=headers)
    for dia in resp.json()["dias"]:
        d = date.fromisoformat(dia["data"])
        if d.weekday() >= 5:
            assert dia["falta"] is False
            assert dia["status_dia"] in ("fim_semana", "folga")


def test_folha_periodo_invalido():
    headers = auth_headers("admin1")
    emp_id = _first_employee_id()
    resp = client.get(f"/ponto/folha/{emp_id}/2026-13", headers=headers)
    assert resp.status_code == 422


def test_folha_csv():
    headers = auth_headers("admin1")
    emp_id = _first_employee_id()
    resp = client.get(f"/ponto/folha/{emp_id}/{PERIODO}/csv", headers=headers)
    assert resp.status_code == 200
    assert "text/csv" in resp.headers["content-type"]
    lines = resp.text.strip().splitlines()
    assert lines[0].startswith("data,")
    assert len(lines) == DAYS_IN_MONTH + 1  # header + days


def test_folha_csv_sem_permissao_read_only():
    """read_only pode acessar CSV da folha."""
    headers = auth_headers("read_only1")
    emp_id = _first_employee_id()
    resp = client.get(f"/ponto/folha/{emp_id}/{PERIODO}/csv", headers=headers)
    assert resp.status_code == 200


# ── Abonos ────────────────────────────────────────────────────────────────────

def test_criar_abono():
    headers = auth_headers("admin1")
    emp = _make_employee("Abono Create", "444.001.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=8)
    resp = client.post("/ponto/abonos", json={
        "employee_id": emp, "data": str(d), "tipo": "falta",
        "motivo": "Licença por doença",
    }, headers=headers)
    assert resp.status_code == 201
    assert resp.json()["status"] == "pendente"
    assert resp.json()["tipo"] == "falta"


def test_criar_abono_tipo_invalido():
    headers = auth_headers("admin1")
    emp = _make_employee("Abono Tipo Inv", "444.002.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=9)
    resp = client.post("/ponto/abonos", json={
        "employee_id": emp, "data": str(d), "tipo": "invalido",
        "motivo": "X",
    }, headers=headers)
    assert resp.status_code == 422


def test_criar_abono_duplicado_409():
    headers = auth_headers("admin1")
    emp = _make_employee("Abono Dup", "444.003.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=10)
    client.post("/ponto/abonos", json={"employee_id": emp, "data": str(d),
                                       "tipo": "falta", "motivo": "X"}, headers=headers)
    resp = client.post("/ponto/abonos", json={"employee_id": emp, "data": str(d),
                                              "tipo": "atraso", "motivo": "Y"}, headers=headers)
    assert resp.status_code == 409


def test_aprovar_abono():
    headers = auth_headers("admin1")
    emp = _make_employee("Abono Aprovar", "444.004.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=11)
    abono = client.post("/ponto/abonos", json={"employee_id": emp, "data": str(d),
                                               "tipo": "atraso", "motivo": "Transporte"}, headers=headers)
    abono_id = abono.json()["id"]
    resp = client.patch(f"/ponto/abonos/{abono_id}", json={"status": "aprovado"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "aprovado"
    assert resp.json()["aprovado_por_id"] is not None


def test_rejeitar_abono():
    headers = auth_headers("admin1")
    emp = _make_employee("Abono Rejeitar", "444.005.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=12)
    abono = client.post("/ponto/abonos", json={"employee_id": emp, "data": str(d),
                                               "tipo": "falta", "motivo": "Sem justificativa"}, headers=headers)
    abono_id = abono.json()["id"]
    resp = client.patch(f"/ponto/abonos/{abono_id}", json={"status": "rejeitado"}, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejeitado"


def test_aprovar_abono_status_invalido():
    headers = auth_headers("admin1")
    emp = _make_employee("Abono Inv Status", "444.006.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=13)
    abono = client.post("/ponto/abonos", json={"employee_id": emp, "data": str(d),
                                               "tipo": "falta", "motivo": "X"}, headers=headers)
    abono_id = abono.json()["id"]
    resp = client.patch(f"/ponto/abonos/{abono_id}", json={"status": "status_invalido"}, headers=headers)
    assert resp.status_code == 422


def test_list_abonos():
    headers = auth_headers("admin1")
    resp = client.get("/ponto/abonos", headers=headers)
    assert resp.status_code == 200
    assert "total" in resp.json()


def test_list_abonos_filtro_pendente():
    headers = auth_headers("admin1")
    resp = client.get("/ponto/abonos?status=pendente", headers=headers)
    assert resp.status_code == 200
    for item in resp.json()["items"]:
        assert item["status"] == "pendente"


def test_aprovar_abono_sem_permissao():
    """read_only não pode aprovar abono."""
    headers_ro = auth_headers("read_only1")
    headers_admin = auth_headers("admin1")
    emp = _make_employee("Abono RO", "444.007.001-01")
    d = _next_weekday(REF_YEAR, REF_MONTH, skip_days=14)
    abono = client.post("/ponto/abonos", json={"employee_id": emp, "data": str(d),
                                               "tipo": "falta", "motivo": "X"}, headers=headers_admin)
    abono_id = abono.json()["id"]
    resp = client.patch(f"/ponto/abonos/{abono_id}", json={"status": "aprovado"}, headers=headers_ro)
    assert resp.status_code == 403


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard():
    headers = auth_headers("admin1")
    resp = client.get(f"/ponto/dashboard?periodo={PERIODO}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "periodo" in data
    assert "total_servidores" in data
    assert "total_presencas" in data
    assert "total_faltas" in data
    assert "total_horas_extras" in data
    assert "abonos_pendentes" in data
    assert "servidores_com_falta" in data
    assert data["total_servidores"] >= 1


def test_dashboard_sem_auth():
    resp = client.get(f"/ponto/dashboard?periodo={PERIODO}")
    assert resp.status_code == 401


def test_dashboard_periodo_invalido():
    headers = auth_headers("admin1")
    resp = client.get("/ponto/dashboard?periodo=2026-99", headers=headers)
    assert resp.status_code == 422


# ── Seed ──────────────────────────────────────────────────────────────────────

def test_seed_escala():
    db = SessionLocal()
    escalas = db.query(EscalaServidor).all()
    assert len(escalas) >= 1
    for e in escalas:
        assert 1.0 <= e.horas_dia <= 12.0
    db.close()


def test_seed_registros_ponto():
    db = SessionLocal()
    registros = db.query(RegistroPonto).all()
    assert len(registros) > 0
    for r in registros:
        assert r.tipo_registro in ("entrada", "saida", "inicio_intervalo", "fim_intervalo")
    db.close()


def test_seed_abono_aprovado():
    db = SessionLocal()
    abonos = db.query(AbonoFalta).filter(AbonoFalta.status == "aprovado").all()
    assert len(abonos) >= 1
    db.close()


def test_folha_seed_tem_presencas_e_abono():
    """A folha do emp1 no mês de referência deve ter presenças, 1 falta abonada e 1 h.extra."""
    headers = auth_headers("admin1")
    db = SessionLocal()
    emp = db.query(Employee).first()
    db.close()
    resp = client.get(f"/ponto/folha/{emp.id}/{PERIODO}", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_presencas"] >= 1
    assert data["total_faltas_abonadas"] >= 1     # abono aprovado no dia 5
    # Verifica que dia 15 tem horas extras (saída às 19h → +2h)
    dia_15 = date(REF_YEAR, REF_MONTH, 15)
    if dia_15.weekday() < 5:
        d15 = next(x for x in data["dias"] if x["data"] == str(dia_15))
        assert d15["horas_extras"] >= 2.0
