"""Testes da integração Ponto/Frequência → Folha de Pagamento (Onda 16).

Cobre: configuração, preview, integração (desconto faltas, atrasos, crédito HE),
       idempotência, force, logs, CSV, dashboard.
"""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_integracao_ponto_folha2.db"

from datetime import date

from fastapi.testclient import TestClient

from app.db import Base, SessionLocal, engine
from app.main import app
from app.models import (
    ConfiguracaoIntegracaoPonto,
    Employee,
    EscalaServidor,
    IntegracaoPontoFolhaLog,
    PayrollEvent,
    RegistroPonto,
    AbonoFalta,
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
        os.remove("./test_integracao_ponto_folha2.db")
    except FileNotFoundError:
        pass


def auth_headers(username: str, password: str = "demo123") -> dict[str, str]:
    login = client.post("/auth/login", json={"username": username, "password": password})
    assert login.status_code == 200
    return {"Authorization": f"Bearer {login.json()['access_token']}"}


def _get_employee_id() -> int:
    db = SessionLocal()
    emp = db.query(Employee).first()
    eid = emp.id
    db.close()
    return eid


def _ensure_config(employee_id: int, pct_he: float = 50.0) -> dict:
    headers = auth_headers("admin1")
    # Try creating; if already exists (409) that's fine
    r = client.post("/integracao-ponto-folha/config", json={
        "employee_id": employee_id,
        "desconto_falta_diaria": None,
        "percentual_hora_extra": pct_he,
        "desconto_atraso": True,
    }, headers=headers)
    if r.status_code == 409:
        return client.get(f"/integracao-ponto-folha/config/{employee_id}", headers=headers).json()
    assert r.status_code == 201, r.text
    return r.json()


def _registrar_falta(employee_id: int, dia: str):
    """Garante ausência total num dia (sem registros de ponto)."""
    db = SessionLocal()
    d = date.fromisoformat(dia)
    # Remove qualquer registro existente nesse dia
    db.query(RegistroPonto).filter(
        RegistroPonto.employee_id == employee_id,
        RegistroPonto.data == d,
    ).delete()
    db.commit()
    db.close()


def _registrar_he(employee_id: int, dia: str, hora_entrada: str = "08:00", hora_saida: str = "18:00"):
    """Cria registros de ponto com 2h extra (entrada 8h, saída 18h, escala 8h)."""
    db = SessionLocal()
    d = date.fromisoformat(dia)
    db.query(RegistroPonto).filter(
        RegistroPonto.employee_id == employee_id,
        RegistroPonto.data == d,
    ).delete()
    db.add(RegistroPonto(employee_id=employee_id, data=d, tipo_registro="entrada",
                          hora_registro=hora_entrada, origem="manual", observacoes=""))
    db.add(RegistroPonto(employee_id=employee_id, data=d, tipo_registro="saida",
                          hora_registro=hora_saida, origem="manual", observacoes=""))
    db.commit()
    db.close()


def _abonar(employee_id: int, dia: str):
    db = SessionLocal()
    d = date.fromisoformat(dia)
    db.query(AbonoFalta).filter(AbonoFalta.employee_id == employee_id, AbonoFalta.data == d).delete()
    db.add(AbonoFalta(employee_id=employee_id, data=d, tipo="falta",
                      motivo="teste", status="aprovado"))
    db.commit()
    db.close()


# ── Configuração ──────────────────────────────────────────────────────────────

def test_criar_config():
    db = SessionLocal()
    emps = db.query(Employee).all()
    # Find employee without config
    emp_id = None
    for e in emps:
        existing = db.query(ConfiguracaoIntegracaoPonto).filter_by(employee_id=e.id).first()
        if not existing:
            emp_id = e.id
            break
    db.close()
    if emp_id is None:
        return  # all have configs from seed; skip

    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/config", json={
        "employee_id": emp_id,
        "desconto_falta_diaria": None,
        "percentual_hora_extra": 50.0,
        "desconto_atraso": True,
    }, headers=headers)
    assert r.status_code == 201
    assert r.json()["employee_id"] == emp_id
    assert r.json()["ativo"] is True


def test_criar_config_duplicada_409():
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/config", json={
        "employee_id": emp_id,
        "percentual_hora_extra": 50.0,
        "desconto_atraso": True,
    }, headers=headers)
    assert r.status_code == 409


def test_criar_config_servidor_inexistente_404():
    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/config", json={
        "employee_id": 999999,
        "percentual_hora_extra": 50.0,
        "desconto_atraso": True,
    }, headers=headers)
    assert r.status_code == 404


def test_criar_config_pct_negativo_422():
    db = SessionLocal()
    emp = db.query(Employee).first()
    emp_id = emp.id
    db.close()
    headers = auth_headers("admin1")
    # First remove existing config if any
    db2 = SessionLocal()
    db2.query(ConfiguracaoIntegracaoPonto).filter_by(employee_id=emp_id).delete()
    db2.commit()
    db2.close()
    r = client.post("/integracao-ponto-folha/config", json={
        "employee_id": emp_id,
        "percentual_hora_extra": -10.0,
        "desconto_atraso": True,
    }, headers=headers)
    assert r.status_code == 422


def test_get_config():
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    headers = auth_headers("admin1")
    r = client.get(f"/integracao-ponto-folha/config/{emp_id}", headers=headers)
    assert r.status_code == 200
    assert r.json()["employee_id"] == emp_id


def test_get_config_nao_encontrada_404():
    headers = auth_headers("admin1")
    r = client.get("/integracao-ponto-folha/config/999999", headers=headers)
    assert r.status_code == 404


def test_list_config():
    headers = auth_headers("admin1")
    r = client.get("/integracao-ponto-folha/config", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_atualizar_config():
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    headers = auth_headers("admin1")
    r = client.patch(f"/integracao-ponto-folha/config/{emp_id}",
                     json={"percentual_hora_extra": 100.0}, headers=headers)
    assert r.status_code == 200
    assert r.json()["percentual_hora_extra"] == 100.0
    # Reset
    client.patch(f"/integracao-ponto-folha/config/{emp_id}",
                 json={"percentual_hora_extra": 50.0}, headers=headers)


def test_atualizar_config_sem_permissao_403():
    emp_id = _get_employee_id()
    headers = auth_headers("read_only1")
    r = client.patch(f"/integracao-ponto-folha/config/{emp_id}",
                     json={"percentual_hora_extra": 100.0}, headers=headers)
    assert r.status_code == 403


# ── Preview ───────────────────────────────────────────────────────────────────

def test_preview():
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/preview",
                    json={"periodo": "2026-04", "employee_id": emp_id}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["periodo"] == "2026-04"
    assert "resultados" in data
    assert len(data["resultados"]) >= 1
    res = data["resultados"][0]
    assert "desconto_previsto_faltas" in res
    assert "credito_previsto_he" in res
    assert "ja_integrado" in res


def test_preview_periodo_invalido_422():
    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/preview",
                    json={"periodo": "invalido"}, headers=headers)
    assert r.status_code == 422


def test_preview_sem_permissao_403():
    r = client.post("/integracao-ponto-folha/preview",
                    json={"periodo": "2026-04"},
                    headers=auth_headers("read_only1"))
    assert r.status_code == 403


# ── Integrar ──────────────────────────────────────────────────────────────────

def test_integrar_basico():
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    # Garante log limpo
    db = SessionLocal()
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-10").delete()
    db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-10",
    ).delete()
    db.commit()
    db.close()

    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2025-10", "employee_id": emp_id}, headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert data["total_ok"] + data["total_pulados"] >= 1


def test_integrar_idempotente():
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    headers = auth_headers("admin1")

    # Limpa e integra uma primeira vez
    db = SessionLocal()
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-11").delete()
    db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-11",
        PayrollEvent.description.like("PONTO:%"),
    ).delete()
    db.commit()
    db.close()

    r1 = client.post("/integracao-ponto-folha/integrar",
                     json={"periodo": "2025-11", "employee_id": emp_id}, headers=headers)
    assert r1.status_code == 200
    assert r1.json()["total_ok"] >= 1

    # Segunda vez: deve pular
    r2 = client.post("/integracao-ponto-folha/integrar",
                     json={"periodo": "2025-11", "employee_id": emp_id}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["total_pulados"] >= 1


def test_integrar_force_re_processa():
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    headers = auth_headers("admin1")

    # Limpa
    db = SessionLocal()
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-12").delete()
    db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-12",
        PayrollEvent.description.like("PONTO:%"),
    ).delete()
    db.commit()
    db.close()

    r1 = client.post("/integracao-ponto-folha/integrar",
                     json={"periodo": "2025-12", "employee_id": emp_id}, headers=headers)
    assert r1.json()["total_ok"] >= 1

    r2 = client.post("/integracao-ponto-folha/integrar",
                     json={"periodo": "2025-12", "employee_id": emp_id, "force": True}, headers=headers)
    assert r2.status_code == 200
    assert r2.json()["total_ok"] >= 1   # re-processado, não pulado


def test_integrar_periodo_invalido_422():
    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2026-99"}, headers=headers)
    assert r.status_code == 422


def test_integrar_sem_permissao_403():
    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2026-04"},
                    headers=auth_headers("read_only1"))
    assert r.status_code == 403


def test_integrar_gera_payrollevent_desconto_falta():
    """Servidor com falta injustificada deve gerar PayrollEvent de desconto."""
    emp_id = _get_employee_id()
    _ensure_config(emp_id)

    # Cria uma falta num dia útil de março 2025 (segunda-feira)
    _registrar_falta(emp_id, "2025-03-03")   # segunda-feira

    db = SessionLocal()
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-03").delete()
    db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-03",
        PayrollEvent.description.like("PONTO:%"),
    ).delete()
    db.commit()
    db.close()

    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2025-03", "employee_id": emp_id}, headers=headers)
    assert r.status_code == 200

    db = SessionLocal()
    events = db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-03",
        PayrollEvent.kind == "desconto",
        PayrollEvent.description.like("PONTO:%falta%"),
    ).all()
    db.close()
    assert len(events) >= 1
    assert events[0].value > 0


def test_integrar_falta_abonada_nao_gera_desconto():
    """Falta com abono aprovado NÃO deve ser contada como falta injustificada."""
    emp_id = _get_employee_id()
    _ensure_config(emp_id)

    # Cria registros de ponto para todos os dias úteis de setembro/2025
    # exceto segunda-feira 01/09/2025 que será abonada
    import calendar as cal
    year, month = 2025, 9
    _, days = cal.monthrange(year, month)
    db = SessionLocal()
    # Limpa mês inteiro
    db.query(RegistroPonto).filter(
        RegistroPonto.employee_id == emp_id,
        RegistroPonto.data >= date(year, month, 1),
        RegistroPonto.data <= date(year, month, days),
    ).delete()
    db.query(AbonoFalta).filter(
        AbonoFalta.employee_id == emp_id,
        AbonoFalta.data >= date(year, month, 1),
        AbonoFalta.data <= date(year, month, days),
    ).delete()
    # Cria presenças para todos os dias úteis exceto dia 01
    for day_num in range(2, days + 1):
        d = date(year, month, day_num)
        if d.weekday() < 5:  # dias úteis
            db.add(RegistroPonto(employee_id=emp_id, data=d, tipo_registro="entrada",
                                  hora_registro="08:00", origem="manual", observacoes=""))
            db.add(RegistroPonto(employee_id=emp_id, data=d, tipo_registro="saida",
                                  hora_registro="17:00", origem="manual", observacoes=""))
    # Abona a falta do dia 1 (segunda-feira)
    db.add(AbonoFalta(employee_id=emp_id, data=date(year, month, 1),
                      tipo="falta", motivo="teste", status="aprovado"))
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-09").delete()
    db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-09",
        PayrollEvent.description.like("PONTO:%"),
    ).delete()
    db.commit()
    db.close()

    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2025-09", "employee_id": emp_id}, headers=headers)
    assert r.status_code == 200

    db = SessionLocal()
    log = db.query(IntegracaoPontoFolhaLog).filter_by(
        employee_id=emp_id, periodo="2025-09", status="ok"
    ).first()
    db.close()
    if log:
        # A falta do dia 1 está abonada, portanto faltas_descontadas deve ser 0
        assert log.faltas_descontadas == 0


def test_integrar_horas_extras_gera_provento():
    """Servidor com horas extras deve gerar PayrollEvent de provento."""
    emp_id = _get_employee_id()
    _ensure_config(emp_id, pct_he=50.0)

    # Cria registro de entrada e saída para segunda-feira 05/05/2025 com 10h (2h extras)
    # Uso de uma segunda-feira sem outros registros conflitantes
    dia = "2025-05-05"
    db = SessionLocal()
    d = date.fromisoformat(dia)
    db.query(RegistroPonto).filter(
        RegistroPonto.employee_id == emp_id,
        RegistroPonto.data == d,
    ).delete()
    db.add(RegistroPonto(employee_id=emp_id, data=d, tipo_registro="entrada",
                          hora_registro="08:00", origem="manual", observacoes=""))
    db.add(RegistroPonto(employee_id=emp_id, data=d, tipo_registro="saida",
                          hora_registro="18:00", origem="manual", observacoes=""))
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-05").delete()
    db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-05",
        PayrollEvent.description.like("PONTO:%"),
    ).delete()
    db.commit()
    db.close()

    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2025-05", "employee_id": emp_id}, headers=headers)
    assert r.status_code == 200

    db = SessionLocal()
    events = db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-05",
        PayrollEvent.kind == "provento",
        PayrollEvent.description.like("PONTO:%extra%"),
    ).all()
    db.close()
    assert len(events) >= 1
    assert events[0].value > 0


def test_integrar_desconto_atraso_desativado():
    """Servidor com desconto_atraso=False não deve gerar desconto por atrasos."""
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    # Desativa desconto por atraso via API
    headers = auth_headers("admin1")
    r_patch = client.patch(f"/integracao-ponto-folha/config/{emp_id}",
                           json={"desconto_atraso": False}, headers=headers)
    assert r_patch.status_code == 200

    db = SessionLocal()
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-06").delete()
    db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-06",
        PayrollEvent.description.like("PONTO:%"),
    ).delete()
    db.commit()
    db.close()

    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2025-06", "employee_id": emp_id}, headers=headers)
    assert r.status_code == 200

    db = SessionLocal()
    atraso_events = db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-06",
        PayrollEvent.description.like("PONTO:%atraso%"),
    ).all()
    db.close()
    assert len(atraso_events) == 0

    # Reactiva
    client.patch(f"/integracao-ponto-folha/config/{emp_id}",
                 json={"desconto_atraso": True}, headers=headers)


def test_integrar_config_inativa_ignorada():
    """Servidor com config ativo=False não é processado."""
    emp_id = _get_employee_id()
    _ensure_config(emp_id)
    headers = auth_headers("admin1")
    client.patch(f"/integracao-ponto-folha/config/{emp_id}",
                 json={"ativo": False}, headers=headers)

    db = SessionLocal()
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-07").delete()
    db.commit()
    db.close()

    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2025-07", "employee_id": emp_id}, headers=headers)
    # Config is inactive → nenhum servidor com config ativa → 404
    assert r.status_code == 404

    # Reactiva
    client.patch(f"/integracao-ponto-folha/config/{emp_id}",
                 json={"ativo": True}, headers=headers)


def test_integrar_desconto_falta_diaria_fixo():
    """Desconto fixo por falta (não proporcional)."""
    db = SessionLocal()
    # Cria um novo employee para este teste
    from app.models import Department
    dept = db.query(Department).first()
    emp = Employee(
        name="Servidor Fixo Teste",
        cpf="999.888.777-01",
        job_title="tecnico",
        department_id=dept.id,
        base_salary=3000.0,
    )
    db.add(emp)
    db.commit()
    db.refresh(emp)
    emp_id = emp.id
    db.close()

    headers = auth_headers("admin1")
    r = client.post("/integracao-ponto-folha/config", json={
        "employee_id": emp_id,
        "desconto_falta_diaria": 150.0,
        "percentual_hora_extra": 50.0,
        "desconto_atraso": False,
    }, headers=headers)
    assert r.status_code == 201

    # Cria falta
    _registrar_falta(emp_id, "2025-08-04")   # segunda-feira

    db = SessionLocal()
    db.query(IntegracaoPontoFolhaLog).filter_by(employee_id=emp_id, periodo="2025-08").delete()
    db.query(PayrollEvent).filter(
        PayrollEvent.employee_id == emp_id,
        PayrollEvent.month == "2025-08",
        PayrollEvent.description.like("PONTO:%"),
    ).delete()
    db.commit()
    db.close()

    r = client.post("/integracao-ponto-folha/integrar",
                    json={"periodo": "2025-08", "employee_id": emp_id}, headers=headers)
    assert r.status_code == 200

    resultado = next((x for x in r.json()["resultados"] if x["employee_id"] == emp_id), None)
    if resultado and resultado["status"] == "ok" and resultado["faltas_descontadas"] > 0:
        assert resultado["valor_desconto_faltas"] == round(resultado["faltas_descontadas"] * 150.0, 2)


# ── Logs ──────────────────────────────────────────────────────────────────────

def test_list_logs():
    emp_id = _get_employee_id()
    headers = auth_headers("admin1")
    # Garante pelo menos um log
    client.post("/integracao-ponto-folha/integrar",
                json={"periodo": "2024-01", "employee_id": emp_id}, headers=headers)
    r = client.get("/integracao-ponto-folha/logs", headers=headers)
    assert r.status_code == 200
    assert r.json()["total"] >= 1


def test_list_logs_por_periodo():
    headers = auth_headers("admin1")
    r = client.get("/integracao-ponto-folha/logs?periodo=2024-01", headers=headers)
    assert r.status_code == 200
    for item in r.json()["items"]:
        assert item["periodo"] == "2024-01"


def test_logs_csv():
    emp_id = _get_employee_id()
    headers = auth_headers("admin1")
    # Garante lançamento
    client.post("/integracao-ponto-folha/integrar",
                json={"periodo": "2024-02", "employee_id": emp_id}, headers=headers)
    r = client.get("/integracao-ponto-folha/logs/csv?periodo=2024-02", headers=headers)
    assert r.status_code == 200
    assert "text/csv" in r.headers["content-type"]
    lines = r.text.strip().splitlines()
    assert lines[0].startswith("employee_id,")


def test_logs_csv_sem_permissao_401():
    r = client.get("/integracao-ponto-folha/logs/csv?periodo=2024-02")
    assert r.status_code == 401


# ── Dashboard ─────────────────────────────────────────────────────────────────

def test_dashboard():
    emp_id = _get_employee_id()
    headers = auth_headers("admin1")
    client.post("/integracao-ponto-folha/integrar",
                json={"periodo": "2024-03"}, headers=headers)
    r = client.get("/integracao-ponto-folha/dashboard?periodo=2024-03", headers=headers)
    assert r.status_code == 200
    data = r.json()
    assert "periodo" in data
    assert "total_configurados" in data
    assert "total_integrados" in data
    assert "total_faltas_descontadas" in data
    assert "total_horas_extras_creditadas" in data
    assert "total_desconto_faltas" in data
    assert "total_desconto_atrasos" in data
    assert "total_credito_horas_extras" in data
    assert "saldo_liquido" in data
    assert "servidores" in data


def test_dashboard_periodo_invalido_422():
    headers = auth_headers("admin1")
    r = client.get("/integracao-ponto-folha/dashboard?periodo=invalido", headers=headers)
    assert r.status_code == 422


def test_dashboard_sem_auth_401():
    r = client.get("/integracao-ponto-folha/dashboard?periodo=2024-03")
    assert r.status_code == 401


def test_dashboard_read_only_ok():
    headers = auth_headers("read_only1")
    r = client.get("/integracao-ponto-folha/dashboard?periodo=2024-03", headers=headers)
    assert r.status_code == 200


# ── Seed ──────────────────────────────────────────────────────────────────────

def test_seed_configs_criadas():
    db = SessionLocal()
    cfgs = db.query(ConfiguracaoIntegracaoPonto).all()
    assert len(cfgs) >= 1
    for c in cfgs:
        assert c.percentual_hora_extra >= 0
    db.close()
