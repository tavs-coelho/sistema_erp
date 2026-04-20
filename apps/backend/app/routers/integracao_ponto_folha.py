"""Integração Ponto/Frequência → Folha de Pagamento (Onda 16).

Converte automaticamente a apuração de ponto/frequência (módulo ponto) em
PayrollEvents no módulo de folha, para que o Payslip reflita descontos por
faltas/atrasos e créditos por horas extras.

LÓGICA DE CONVERSÃO
===================
Para cada servidor no período:

1. Busca a folha de frequência (_calcular_folha) do módulo ponto.
2. Desconto por faltas injustificadas:
   - Se ConfiguracaoIntegracaoPonto.desconto_falta_diaria IS NOT NULL:
       desconto = faltas_injustificadas × desconto_falta_diaria
   - Caso contrário (proporcional ao salário):
       valor_dia = employee.base_salary / total_dias_uteis
       desconto  = faltas_injustificadas × valor_dia
   - Cria PayrollEvent(kind='desconto', description='Desconto por faltas injustificadas...')
3. Desconto por atrasos (se desconto_atraso=True):
   - valor_minuto = (employee.base_salary / total_dias_uteis) / horas_dia / 60
   - desconto_atraso = total_minutos_atraso × valor_minuto
   - Cria PayrollEvent(kind='desconto', description='Desconto por atrasos ...')
4. Crédito por horas extras:
   - valor_hora = employee.base_salary / total_dias_uteis / horas_dia
   - credito = total_horas_extras × valor_hora × (1 + percentual_hora_extra / 100)
   - Cria PayrollEvent(kind='provento', description='Horas extras ...')

IDEMPOTÊNCIA
============
- Antes de criar eventos, verifica se já existe IntegracaoPontoFolhaLog com
  status='ok' para (employee_id, periodo).
- Se existir e force=False: pula o servidor (retorna 'pulado').
- Se force=True: deleta os PayrollEvents criados anteriormente (identificados
  pela description prefix 'PONTO:') e o log, depois recria.

LIMITAÇÕES
==========
- Não trata regime diferenciado de horas extras (50% vs 100%) — usa percentual único
  configurável. Refinamento futuro.
- Não considera INSS/IRRF sobre os valores gerados — esses impostos são calculados
  na geração do Payslip pelo módulo HR.
- Não gera Payslip automaticamente — apenas cria/atualiza os PayrollEvents. O usuário
  deve acionar o cálculo do Payslip no módulo de folha.
- Sem pro-rata no primeiro mês de contratação.
"""

import csv
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    AbonoFalta,
    ConfiguracaoIntegracaoPonto,
    Employee,
    EscalaServidor,
    IntegracaoPontoFolhaLog,
    PayrollEvent,
    RegistroPonto,
    RoleEnum,
    User,
)
from ..routers.hr import recalcular_payslip_servidor
from ..routers.ponto import _calcular_folha
from ..schemas import (
    ConfiguracaoIntegracaoPontoCreate,
    ConfiguracaoIntegracaoPontoOut,
    ConfiguracaoIntegracaoPontoUpdate,
    IntegrarPontoFolhaRequest,
)

router = APIRouter(prefix="/integracao-ponto-folha", tags=["integracao_ponto_folha"])

# Prefixo usado em description dos PayrollEvents para identificá-los neste módulo
_PREFIX = "PONTO:"


# ── Helpers ───────────────────────────────────────────────────────────────────

def _horas_dia_escala(db: Session, employee_id: int) -> float:
    esc = db.query(EscalaServidor).filter(EscalaServidor.employee_id == employee_id).first()
    return float(esc.horas_dia) if esc else 8.0


def _processar_servidor(
    db: Session,
    cfg: ConfiguracaoIntegracaoPonto,
    periodo: str,
    executado_por_id: int | None,
    force: bool,
) -> dict:
    """Integra ponto → folha para um servidor em um período. Retorna log dict."""

    employee_id = cfg.employee_id
    emp = db.get(Employee, employee_id)
    if not emp:
        return {"employee_id": employee_id, "status": "erro", "motivo": "Servidor não encontrado"}

    # Idempotência
    log_existente = (
        db.query(IntegracaoPontoFolhaLog)
        .filter(
            IntegracaoPontoFolhaLog.employee_id == employee_id,
            IntegracaoPontoFolhaLog.periodo == periodo,
            IntegracaoPontoFolhaLog.status == "ok",
        )
        .first()
    )
    if log_existente and not force:
        return {"employee_id": employee_id, "status": "pulado", "motivo": "Já integrado"}

    # Se force=True, apaga eventos e log anteriores
    if log_existente and force:
        db.query(PayrollEvent).filter(
            PayrollEvent.employee_id == employee_id,
            PayrollEvent.month == periodo,
            PayrollEvent.description.like(f"{_PREFIX}%"),
        ).delete(synchronize_session=False)
        db.delete(log_existente)

    # Calcula folha de frequência
    try:
        folha = _calcular_folha(db, employee_id, periodo)
    except HTTPException as exc:
        return {"employee_id": employee_id, "status": "erro", "motivo": str(exc.detail)}

    total_dias_uteis = folha["total_dias_uteis"] or 1   # evita divisão por zero
    total_faltas = folha["total_faltas"]                # já exclui faltas abonadas
    total_horas_extras = folha["total_horas_extras"]
    total_min_atraso = folha["total_minutos_atraso"]

    horas_dia = _horas_dia_escala(db, employee_id)
    valor_dia = emp.base_salary / total_dias_uteis
    valor_hora = valor_dia / horas_dia
    valor_minuto = valor_hora / 60.0

    desconto_faltas = 0.0
    desconto_atrasos = 0.0
    credito_he = 0.0

    events_criados = []

    # 1. Desconto faltas
    if total_faltas > 0:
        if cfg.desconto_falta_diaria is not None:
            desconto_faltas = round(total_faltas * cfg.desconto_falta_diaria, 2)
        else:
            desconto_faltas = round(total_faltas * valor_dia, 2)
        ev = PayrollEvent(
            employee_id=employee_id,
            month=periodo,
            kind="desconto",
            description=f"{_PREFIX}Desconto por {total_faltas} falta(s) injustificada(s) em {periodo}",
            value=desconto_faltas,
        )
        db.add(ev)
        events_criados.append(ev)

    # 2. Desconto atrasos
    if cfg.desconto_atraso and total_min_atraso > 0:
        desconto_atrasos = round(total_min_atraso * valor_minuto, 2)
        ev = PayrollEvent(
            employee_id=employee_id,
            month=periodo,
            kind="desconto",
            description=f"{_PREFIX}Desconto por {total_min_atraso} min de atraso em {periodo}",
            value=desconto_atrasos,
        )
        db.add(ev)
        events_criados.append(ev)

    # 3. Crédito horas extras
    if total_horas_extras > 0:
        fator = 1 + cfg.percentual_hora_extra / 100.0
        credito_he = round(total_horas_extras * valor_hora * fator, 2)
        ev = PayrollEvent(
            employee_id=employee_id,
            month=periodo,
            kind="provento",
            description=f"{_PREFIX}{total_horas_extras}h extra(s) em {periodo} ({cfg.percentual_hora_extra:.0f}%)",
            value=credito_he,
        )
        db.add(ev)
        events_criados.append(ev)

    # Log
    log = IntegracaoPontoFolhaLog(
        employee_id=employee_id,
        periodo=periodo,
        faltas_descontadas=total_faltas,
        horas_extras_creditadas=total_horas_extras,
        valor_desconto_faltas=desconto_faltas,
        valor_desconto_atrasos=desconto_atrasos,
        valor_credito_horas_extras=credito_he,
        status="ok",
        executado_por_id=executado_por_id,
    )
    db.add(log)

    return {
        "employee_id": employee_id,
        "employee_name": emp.name,
        "status": "ok",
        "faltas_descontadas": total_faltas,
        "horas_extras_creditadas": total_horas_extras,
        "valor_desconto_faltas": desconto_faltas,
        "valor_desconto_atrasos": desconto_atrasos,
        "valor_credito_horas_extras": credito_he,
        "eventos_gerados": len(events_criados),
    }


# ── Configuração ──────────────────────────────────────────────────────────────

@router.post("/config", response_model=ConfiguracaoIntegracaoPontoOut, status_code=201)
def criar_config(
    payload: ConfiguracaoIntegracaoPontoCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    if not db.get(Employee, payload.employee_id):
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    existente = db.query(ConfiguracaoIntegracaoPonto).filter(
        ConfiguracaoIntegracaoPonto.employee_id == payload.employee_id
    ).first()
    if existente:
        raise HTTPException(status_code=409, detail="Configuração já existe; use PATCH para atualizar")
    if payload.percentual_hora_extra < 0:
        raise HTTPException(status_code=422, detail="percentual_hora_extra não pode ser negativo")

    cfg = ConfiguracaoIntegracaoPonto(**payload.model_dump())
    db.add(cfg)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="configuracoes_integracao_ponto",
                entity_id=str(cfg.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(cfg)
    return cfg


@router.get("/config/{employee_id}", response_model=ConfiguracaoIntegracaoPontoOut)
def get_config(
    employee_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    cfg = db.query(ConfiguracaoIntegracaoPonto).filter(
        ConfiguracaoIntegracaoPonto.employee_id == employee_id
    ).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuração não encontrada para este servidor")
    return cfg


@router.get("/config", response_model=None)
def list_config(
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ConfiguracaoIntegracaoPonto)
    total = q.count()
    items = q.order_by(ConfiguracaoIntegracaoPonto.id).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.patch("/config/{employee_id}", response_model=ConfiguracaoIntegracaoPontoOut)
def atualizar_config(
    employee_id: int,
    payload: ConfiguracaoIntegracaoPontoUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    cfg = db.query(ConfiguracaoIntegracaoPonto).filter(
        ConfiguracaoIntegracaoPonto.employee_id == employee_id
    ).first()
    if not cfg:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")
    updates = payload.model_dump(exclude_none=True)
    if "percentual_hora_extra" in updates and updates["percentual_hora_extra"] < 0:
        raise HTTPException(status_code=422, detail="percentual_hora_extra não pode ser negativo")
    before = {k: getattr(cfg, k) for k in updates}
    for field, value in updates.items():
        setattr(cfg, field, value)
    write_audit(db, user_id=current.id, action="update", entity="configuracoes_integracao_ponto",
                entity_id=str(cfg.id), before_data=before, after_data=updates)
    db.commit()
    db.refresh(cfg)
    return cfg


# ── Preview (dry-run) ─────────────────────────────────────────────────────────

@router.post("/preview")
def preview_integracao(
    payload: IntegrarPontoFolhaRequest,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    """Retorna o que seria gerado sem persistir nada (dry-run)."""
    try:
        year, month = int(payload.periodo[:4]), int(payload.periodo[5:7])
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Período inválido; use YYYY-MM")

    q = db.query(ConfiguracaoIntegracaoPonto).filter(ConfiguracaoIntegracaoPonto.ativo == True)
    if payload.employee_id:
        if not db.get(Employee, payload.employee_id):
            raise HTTPException(status_code=404, detail="Servidor não encontrado")
        q = q.filter(ConfiguracaoIntegracaoPonto.employee_id == payload.employee_id)

    cfgs = q.all()
    if not cfgs:
        raise HTTPException(status_code=404, detail="Nenhum servidor com configuração de integração ativa encontrado")

    results = []
    for cfg in cfgs:
        emp = db.get(Employee, cfg.employee_id)
        if not emp:
            continue
        try:
            folha = _calcular_folha(db, cfg.employee_id, payload.periodo)
        except HTTPException:
            continue

        total_dias_uteis = folha["total_dias_uteis"] or 1
        horas_dia = _horas_dia_escala(db, cfg.employee_id)
        valor_dia = emp.base_salary / total_dias_uteis
        valor_hora = valor_dia / horas_dia
        valor_minuto = valor_hora / 60.0

        desconto_faltas = 0.0
        if folha["total_faltas"] > 0:
            if cfg.desconto_falta_diaria is not None:
                desconto_faltas = round(folha["total_faltas"] * cfg.desconto_falta_diaria, 2)
            else:
                desconto_faltas = round(folha["total_faltas"] * valor_dia, 2)

        desconto_atrasos = 0.0
        if cfg.desconto_atraso and folha["total_minutos_atraso"] > 0:
            desconto_atrasos = round(folha["total_minutos_atraso"] * valor_minuto, 2)

        credito_he = 0.0
        if folha["total_horas_extras"] > 0:
            fator = 1 + cfg.percentual_hora_extra / 100.0
            credito_he = round(folha["total_horas_extras"] * valor_hora * fator, 2)

        ja_integrado = db.query(IntegracaoPontoFolhaLog).filter(
            IntegracaoPontoFolhaLog.employee_id == cfg.employee_id,
            IntegracaoPontoFolhaLog.periodo == payload.periodo,
            IntegracaoPontoFolhaLog.status == "ok",
        ).first() is not None

        results.append({
            "employee_id": cfg.employee_id,
            "employee_name": emp.name,
            "total_faltas_injustificadas": folha["total_faltas"],
            "total_horas_extras": folha["total_horas_extras"],
            "total_minutos_atraso": folha["total_minutos_atraso"],
            "desconto_previsto_faltas": desconto_faltas,
            "desconto_previsto_atrasos": desconto_atrasos,
            "credito_previsto_he": credito_he,
            "ja_integrado": ja_integrado,
        })

    return {"periodo": payload.periodo, "resultados": results}


# ── Integrar ──────────────────────────────────────────────────────────────────

@router.post("/integrar", status_code=200)
def integrar(
    payload: IntegrarPontoFolhaRequest,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    """Persiste os PayrollEvents calculados a partir da apuração de ponto.

    Idempotente: servidores já integrados para o período são ignorados
    a menos que force=True seja passado.
    """
    try:
        year, month = int(payload.periodo[:4]), int(payload.periodo[5:7])
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Período inválido; use YYYY-MM")

    q = db.query(ConfiguracaoIntegracaoPonto).filter(ConfiguracaoIntegracaoPonto.ativo == True)
    if payload.employee_id:
        if not db.get(Employee, payload.employee_id):
            raise HTTPException(status_code=404, detail="Servidor não encontrado")
        q = q.filter(ConfiguracaoIntegracaoPonto.employee_id == payload.employee_id)

    cfgs = q.all()
    if not cfgs:
        raise HTTPException(status_code=404, detail="Nenhum servidor com configuração de integração ativa encontrado")

    resultados = []
    for cfg in cfgs:
        r = _processar_servidor(db, cfg, payload.periodo, current.id, payload.force)
        resultados.append(r)

    total_ok = sum(1 for r in resultados if r.get("status") == "ok")
    total_pulados = sum(1 for r in resultados if r.get("status") == "pulado")
    total_erros = sum(1 for r in resultados if r.get("status") == "erro")

    # Recálculo automático do Payslip (se solicitado)
    payslip_resultados = []
    if payload.recalcular_payslip:
        taxa = payload.taxa_deducao if 0 <= payload.taxa_deducao <= 100 else 11.0
        for r in resultados:
            if r.get("status") in ("ok",):
                ps = recalcular_payslip_servidor(
                    db, r["employee_id"], payload.periodo,
                    taxa_deducao=taxa,
                    origem="integracao_ponto",
                    executado_por_id=current.id,
                )
                payslip_resultados.append(ps)

    write_audit(db, user_id=current.id, action="create",
                entity="integracao_ponto_folha_logs", entity_id=payload.periodo,
                after_data={"periodo": payload.periodo, "total_ok": total_ok,
                            "total_pulados": total_pulados, "total_erros": total_erros,
                            "payslips_recalculados": len(payslip_resultados)})
    db.commit()

    resp = {
        "periodo": payload.periodo,
        "total_ok": total_ok,
        "total_pulados": total_pulados,
        "total_erros": total_erros,
        "resultados": resultados,
    }
    if payload.recalcular_payslip:
        resp["payslips_recalculados"] = payslip_resultados
    return resp


# ── Logs ──────────────────────────────────────────────────────────────────────

@router.get("/logs", response_model=None)
def list_logs(
    employee_id: int | None = None,
    periodo: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(IntegracaoPontoFolhaLog)
    if employee_id:
        q = q.filter(IntegracaoPontoFolhaLog.employee_id == employee_id)
    if periodo:
        q = q.filter(IntegracaoPontoFolhaLog.periodo == periodo)
    total = q.count()
    items = q.order_by(IntegracaoPontoFolhaLog.created_at.desc()).offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/logs/csv")
def logs_csv(
    periodo: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr, RoleEnum.read_only)),
):
    logs = (
        db.query(IntegracaoPontoFolhaLog)
        .filter(IntegracaoPontoFolhaLog.periodo == periodo)
        .order_by(IntegracaoPontoFolhaLog.employee_id)
        .all()
    )
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow([
        "employee_id", "employee_name", "periodo", "faltas_descontadas",
        "horas_extras_creditadas", "valor_desconto_faltas",
        "valor_desconto_atrasos", "valor_credito_horas_extras", "status",
    ])
    for log in logs:
        emp = db.get(Employee, log.employee_id)
        writer.writerow([
            log.employee_id, emp.name if emp else "", log.periodo,
            log.faltas_descontadas, log.horas_extras_creditadas,
            log.valor_desconto_faltas, log.valor_desconto_atrasos,
            log.valor_credito_horas_extras, log.status,
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=integracao_ponto_folha_{periodo}.csv"},
    )


# ── Dashboard ─────────────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(
    periodo: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr, RoleEnum.read_only)),
):
    try:
        year, month = int(periodo[:4]), int(periodo[5:7])
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Período inválido; use YYYY-MM")

    from sqlalchemy import func

    total_configurados = db.query(func.count(ConfiguracaoIntegracaoPonto.id)).filter(
        ConfiguracaoIntegracaoPonto.ativo == True
    ).scalar() or 0

    logs_periodo = (
        db.query(IntegracaoPontoFolhaLog)
        .filter(IntegracaoPontoFolhaLog.periodo == periodo,
                IntegracaoPontoFolhaLog.status == "ok")
        .all()
    )

    total_integrados = len(logs_periodo)
    total_faltas = sum(l.faltas_descontadas for l in logs_periodo)
    total_he = round(sum(l.horas_extras_creditadas for l in logs_periodo), 2)
    total_desc_faltas = round(sum(l.valor_desconto_faltas for l in logs_periodo), 2)
    total_desc_atrasos = round(sum(l.valor_desconto_atrasos for l in logs_periodo), 2)
    total_cred_he = round(sum(l.valor_credito_horas_extras for l in logs_periodo), 2)

    servidores = []
    for log in logs_periodo:
        emp = db.get(Employee, log.employee_id)
        servidores.append({
            "employee_id": log.employee_id,
            "employee_name": emp.name if emp else "",
            "faltas_descontadas": log.faltas_descontadas,
            "horas_extras_creditadas": log.horas_extras_creditadas,
            "valor_desconto_faltas": log.valor_desconto_faltas,
            "valor_desconto_atrasos": log.valor_desconto_atrasos,
            "valor_credito_horas_extras": log.valor_credito_horas_extras,
        })

    return {
        "periodo": periodo,
        "total_configurados": total_configurados,
        "total_integrados": total_integrados,
        "total_faltas_descontadas": total_faltas,
        "total_horas_extras_creditadas": total_he,
        "total_desconto_faltas": total_desc_faltas,
        "total_desconto_atrasos": total_desc_atrasos,
        "total_credito_horas_extras": total_cred_he,
        "saldo_liquido": round(total_cred_he - total_desc_faltas - total_desc_atrasos, 2),
        "servidores": servidores,
    }
