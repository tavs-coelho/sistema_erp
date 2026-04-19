"""Router Ponto e Frequência de Servidores.

Cobre:
  - Escala (carga horária contratual) por servidor
  - Registro de ponto (entrada, saída, intervalos)
  - Folha de frequência mensal por servidor (dias úteis, faltas, horas extras, atrasos)
  - Abonos de falta/atraso com fluxo de aprovação
  - Dashboard resumido por período
  - Exportação CSV da folha

LÓGICA DE CÁLCULO:
  Para cada dia útil da escala do servidor no período:
    - Se há marcação de entrada e saída:
        intervalo = fim_intervalo - inicio_intervalo  (em horas, default 1h)
        horas_trabalhadas = (saida - entrada) - intervalo
        horas_extras = max(0, horas_trabalhadas - escala.horas_dia)
        atraso = max(0, entrada_real - entrada_prevista) em minutos
    - Se não há marcação:
        falta = True (a menos que haja abono aprovado para o dia)
"""

import calendar
import csv
from datetime import date, datetime, timezone
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    AbonoFalta,
    Employee,
    EscalaServidor,
    RegistroPonto,
    RoleEnum,
    User,
)
from ..schemas import (
    AbonoFaltaCreate,
    AbonoFaltaOut,
    AbonoFaltaUpdate,
    EscalaServidorCreate,
    EscalaServidorOut,
    EscalaServidorUpdate,
    RegistroPontoCreate,
    RegistroPontoOut,
)

router = APIRouter(prefix="/ponto", tags=["ponto"])

# Nomes curtos de dia da semana (0=Segunda, 6=Domingo)
_DIA_SEMANA_NOME = ["Seg", "Ter", "Qua", "Qui", "Sex", "Sáb", "Dom"]

# Escala padrão quando não cadastrada
_ESCALA_PADRAO = {
    "horas_dia": 8.0,
    "dias_semana": "12345",
    "hora_entrada": "08:00",
    "hora_saida": "17:00",
    "hora_inicio_intervalo": "12:00",
    "hora_fim_intervalo": "13:00",
}

TIPOS_REGISTRO = {"entrada", "saida", "inicio_intervalo", "fim_intervalo"}
TIPOS_ABONO = {"falta", "atraso", "folga_compensacao"}
STATUS_ABONO = {"pendente", "aprovado", "rejeitado"}


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


def _hm_to_min(hm: str) -> int:
    """Converte 'HH:MM' em minutos desde meia-noite."""
    h, m = hm.split(":")
    return int(h) * 60 + int(m)


def _min_to_horas(m: int) -> float:
    return round(m / 60, 2)


def _get_escala(db: Session, employee_id: int) -> dict:
    e = db.query(EscalaServidor).filter(EscalaServidor.employee_id == employee_id).first()
    if e:
        return {
            "horas_dia": e.horas_dia,
            "dias_semana": e.dias_semana,
            "hora_entrada": e.hora_entrada,
            "hora_saida": e.hora_saida,
            "hora_inicio_intervalo": e.hora_inicio_intervalo,
            "hora_fim_intervalo": e.hora_fim_intervalo,
        }
    return dict(_ESCALA_PADRAO)


def _is_dia_util(d: date, dias_semana: str) -> bool:
    """Verifica se o dia é útil para a escala. weekday(): 0=Seg … 6=Dom.
    dias_semana string usa '1'=Seg … '7'=Dom."""
    wd = d.weekday() + 1  # 1..7
    return str(wd) in dias_semana


def _calcular_dia(
    data_dia: date,
    escala: dict,
    registros: list[RegistroPonto],
    abono: AbonoFalta | None,
) -> dict:
    """Calcula o resumo de frequência de um único dia."""
    dia_util = _is_dia_util(data_dia, escala["dias_semana"])
    wd = data_dia.weekday()  # 0=Seg
    dia_semana_nome = _DIA_SEMANA_NOME[wd]

    reg_por_tipo = {r.tipo_registro: r.hora_registro for r in registros}
    entrada = reg_por_tipo.get("entrada")
    saida = reg_por_tipo.get("saida")
    ini_interv = reg_por_tipo.get("inicio_intervalo")
    fim_interv = reg_por_tipo.get("fim_intervalo")

    abonado = abono is not None and abono.status == "aprovado"
    abono_tipo = abono.tipo if abono else None

    if not dia_util:
        return {
            "data": data_dia,
            "dia_semana": dia_semana_nome,
            "dia_util": False,
            "entrada": entrada,
            "saida": saida,
            "inicio_intervalo": ini_interv,
            "fim_intervalo": fim_interv,
            "horas_trabalhadas": 0.0,
            "horas_extras": 0.0,
            "minutos_atraso": 0,
            "falta": False,
            "abonado": False,
            "abono_tipo": None,
            "status_dia": "fim_semana" if wd >= 5 else "folga",
        }

    # Calcular horas trabalhadas
    horas_trab = 0.0
    horas_extras = 0.0
    minutos_atraso = 0
    falta = False

    if entrada and saida:
        min_entrada = _hm_to_min(entrada)
        min_saida = _hm_to_min(saida)

        # Intervalo
        if ini_interv and fim_interv:
            min_interv = max(0, _hm_to_min(fim_interv) - _hm_to_min(ini_interv))
        else:
            # Usa intervalo da escala como default
            min_interv = max(0, _hm_to_min(escala["hora_fim_intervalo"]) - _hm_to_min(escala["hora_inicio_intervalo"]))

        min_trab = max(0, min_saida - min_entrada - min_interv)
        horas_trab = _min_to_horas(min_trab)
        horas_dia = escala["horas_dia"]
        horas_extras = round(max(0.0, horas_trab - horas_dia), 2)

        # Atraso em relação à hora de entrada prevista
        min_entrada_prevista = _hm_to_min(escala["hora_entrada"])
        minutos_atraso = max(0, min_entrada - min_entrada_prevista)
        status_dia = "presente"
    else:
        falta = True
        status_dia = "falta_abonada" if abonado else "falta"

    return {
        "data": data_dia,
        "dia_semana": dia_semana_nome,
        "dia_util": True,
        "entrada": entrada,
        "saida": saida,
        "inicio_intervalo": ini_interv,
        "fim_intervalo": fim_interv,
        "horas_trabalhadas": horas_trab,
        "horas_extras": horas_extras,
        "minutos_atraso": minutos_atraso,
        "falta": falta,
        "abonado": abonado,
        "abono_tipo": abono_tipo,
        "status_dia": status_dia,
    }


def _calcular_folha(db: Session, employee_id: int, periodo: str) -> dict:
    """Gera a folha de frequência mensal para um servidor."""
    emp = db.get(Employee, employee_id)
    if not emp:
        raise HTTPException(status_code=404, detail="Servidor não encontrado")

    year, month = int(periodo[:4]), int(periodo[5:7])
    _, days_in_month = calendar.monthrange(year, month)
    escala = _get_escala(db, employee_id)

    # Buscar todos os registros do mês
    data_inicio = date(year, month, 1)
    data_fim = date(year, month, days_in_month)
    registros = (
        db.query(RegistroPonto)
        .filter(RegistroPonto.employee_id == employee_id,
                RegistroPonto.data >= data_inicio,
                RegistroPonto.data <= data_fim)
        .all()
    )
    # Agrupar por data
    reg_por_dia: dict[date, list[RegistroPonto]] = {}
    for r in registros:
        reg_por_dia.setdefault(r.data, []).append(r)

    # Abonos do mês
    abonos = (
        db.query(AbonoFalta)
        .filter(AbonoFalta.employee_id == employee_id,
                AbonoFalta.data >= data_inicio,
                AbonoFalta.data <= data_fim)
        .all()
    )
    abono_por_dia: dict[date, AbonoFalta] = {a.data: a for a in abonos}

    dias = []
    total_dias_uteis = 0
    total_presencas = 0
    total_faltas = 0
    total_faltas_abonadas = 0
    total_horas_trab = 0.0
    total_horas_extras = 0.0
    total_min_atraso = 0

    for day_num in range(1, days_in_month + 1):
        d = date(year, month, day_num)
        regs_dia = reg_por_dia.get(d, [])
        abono = abono_por_dia.get(d)
        dia_info = _calcular_dia(d, escala, regs_dia, abono)
        dias.append(dia_info)

        if dia_info["dia_util"]:
            total_dias_uteis += 1
            if dia_info["falta"]:
                if dia_info["abonado"]:
                    total_faltas_abonadas += 1
                else:
                    total_faltas += 1
            else:
                total_presencas += 1

        total_horas_trab += dia_info["horas_trabalhadas"]
        total_horas_extras += dia_info["horas_extras"]
        total_min_atraso += dia_info["minutos_atraso"]

    return {
        "employee_id": employee_id,
        "employee_name": emp.name,
        "periodo": periodo,
        "total_dias_uteis": total_dias_uteis,
        "total_presencas": total_presencas,
        "total_faltas": total_faltas,
        "total_faltas_abonadas": total_faltas_abonadas,
        "total_horas_trabalhadas": round(total_horas_trab, 2),
        "total_horas_extras": round(total_horas_extras, 2),
        "total_minutos_atraso": total_min_atraso,
        "dias": dias,
    }


# ══════════════════════════════════════════════════════════════════════════════
#  Escala
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/escalas", response_model=EscalaServidorOut, status_code=201)
def criar_escala(
    payload: EscalaServidorCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    if not db.get(Employee, payload.employee_id):
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    existente = db.query(EscalaServidor).filter(EscalaServidor.employee_id == payload.employee_id).first()
    if existente:
        raise HTTPException(status_code=409, detail="Escala já cadastrada para este servidor; use PATCH para atualizar")
    obj = EscalaServidor(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="escalas_servidores",
                entity_id=str(obj.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/escalas/{employee_id}", response_model=EscalaServidorOut)
def get_escala(employee_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.query(EscalaServidor).filter(EscalaServidor.employee_id == employee_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Escala não encontrada; padrão 8h/dia seg-sex aplicado")
    return obj


@router.patch("/escalas/{employee_id}", response_model=EscalaServidorOut)
def atualizar_escala(
    employee_id: int,
    payload: EscalaServidorUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    obj = db.query(EscalaServidor).filter(EscalaServidor.employee_id == employee_id).first()
    if not obj:
        raise HTTPException(status_code=404, detail="Escala não encontrada")
    before = {"horas_dia": obj.horas_dia, "hora_entrada": obj.hora_entrada}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    write_audit(db, user_id=current.id, action="update", entity="escalas_servidores",
                entity_id=str(obj.id), before_data=before,
                after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
#  Registros de Ponto
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/registros", response_model=RegistroPontoOut, status_code=201)
def registrar_ponto(
    payload: RegistroPontoCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Registra uma marcação de ponto. Qualquer usuário autenticado pode registrar
    seu próprio ponto; admin/hr podem registrar para qualquer servidor."""
    if payload.tipo_registro not in TIPOS_REGISTRO:
        raise HTTPException(status_code=422, detail=f"tipo_registro inválido; use: {TIPOS_REGISTRO}")
    if not db.get(Employee, payload.employee_id):
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    # Servidor logado só pode registrar o próprio ponto
    if current.role not in (RoleEnum.admin, RoleEnum.hr):
        if current.employee_id != payload.employee_id:
            raise HTTPException(status_code=403, detail="Você só pode registrar o seu próprio ponto")

    # Verifica duplicidade de tipo_registro no mesmo dia
    existente = (
        db.query(RegistroPonto)
        .filter(
            RegistroPonto.employee_id == payload.employee_id,
            RegistroPonto.data == payload.data,
            RegistroPonto.tipo_registro == payload.tipo_registro,
        )
        .first()
    )
    if existente:
        raise HTTPException(
            status_code=409,
            detail=f"Já existe marcação de '{payload.tipo_registro}' para este servidor neste dia",
        )

    obj = RegistroPonto(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="registros_ponto",
                entity_id=str(obj.id),
                after_data={"employee_id": obj.employee_id, "data": str(obj.data),
                            "tipo_registro": obj.tipo_registro, "hora_registro": obj.hora_registro})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/registros", response_model=None)
def list_registros(
    employee_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    tipo_registro: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = db.query(RegistroPonto)
    # Servidor só vê próprios registros
    if current.role == RoleEnum.employee:
        q = q.filter(RegistroPonto.employee_id == current.employee_id)
    elif employee_id:
        q = q.filter(RegistroPonto.employee_id == employee_id)
    if data_inicio:
        q = q.filter(RegistroPonto.data >= data_inicio)
    if data_fim:
        q = q.filter(RegistroPonto.data <= data_fim)
    if tipo_registro:
        q = q.filter(RegistroPonto.tipo_registro == tipo_registro)
    q = q.order_by(RegistroPonto.data.desc(), RegistroPonto.hora_registro)
    return _paginate(q, page, size)


@router.delete("/registros/{registro_id}", status_code=204)
def deletar_registro(
    registro_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    obj = db.get(RegistroPonto, registro_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Registro não encontrado")
    write_audit(db, user_id=current.id, action="delete", entity="registros_ponto",
                entity_id=str(obj.id),
                before_data={"employee_id": obj.employee_id, "data": str(obj.data),
                             "tipo_registro": obj.tipo_registro})
    db.delete(obj)
    db.commit()


# ══════════════════════════════════════════════════════════════════════════════
#  Folha de Frequência
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/folha/{employee_id}/{periodo}")
def folha_frequencia(
    employee_id: int,
    periodo: str,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Retorna a folha de frequência mensal de um servidor (período = YYYY-MM)."""
    # Servidor só vê a própria folha
    if current.role == RoleEnum.employee and current.employee_id != employee_id:
        raise HTTPException(status_code=403, detail="Sem permissão para ver a folha deste servidor")
    try:
        year, month = int(periodo[:4]), int(periodo[5:7])
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Período inválido; use YYYY-MM")
    return _calcular_folha(db, employee_id, periodo)


@router.get("/folha/{employee_id}/{periodo}/csv")
def folha_frequencia_csv(
    employee_id: int,
    periodo: str,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr, RoleEnum.read_only)),
):
    """Exporta a folha de frequência em CSV."""
    folha = _calcular_folha(db, employee_id, periodo)
    buf = StringIO()
    writer = csv.writer(buf)
    writer.writerow(["data", "dia_semana", "dia_util", "entrada", "saida",
                     "inicio_intervalo", "fim_intervalo", "horas_trabalhadas",
                     "horas_extras", "minutos_atraso", "falta", "abonado", "abono_tipo", "status_dia"])
    for d in folha["dias"]:
        writer.writerow([
            d["data"], d["dia_semana"], d["dia_util"],
            d["entrada"], d["saida"], d["inicio_intervalo"], d["fim_intervalo"],
            d["horas_trabalhadas"], d["horas_extras"], d["minutos_atraso"],
            d["falta"], d["abonado"], d["abono_tipo"], d["status_dia"],
        ])
    return Response(
        content=buf.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=frequencia_{employee_id}_{periodo}.csv"},
    )


# ══════════════════════════════════════════════════════════════════════════════
#  Abonos
# ══════════════════════════════════════════════════════════════════════════════

@router.post("/abonos", response_model=AbonoFaltaOut, status_code=201)
def criar_abono(
    payload: AbonoFaltaCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Cria uma solicitação de abono. Qualquer usuário pode solicitar para si mesmo;
    admin/hr podem solicitar para qualquer servidor."""
    if payload.tipo not in TIPOS_ABONO:
        raise HTTPException(status_code=422, detail=f"tipo inválido; use: {TIPOS_ABONO}")
    if not db.get(Employee, payload.employee_id):
        raise HTTPException(status_code=404, detail="Servidor não encontrado")
    if current.role not in (RoleEnum.admin, RoleEnum.hr):
        if current.employee_id != payload.employee_id:
            raise HTTPException(status_code=403, detail="Você só pode solicitar abono para si mesmo")

    existente = (
        db.query(AbonoFalta)
        .filter(AbonoFalta.employee_id == payload.employee_id, AbonoFalta.data == payload.data)
        .first()
    )
    if existente:
        raise HTTPException(status_code=409, detail="Já existe abono para este servidor nesta data")

    obj = AbonoFalta(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="abonos_falta",
                entity_id=str(obj.id),
                after_data={"employee_id": obj.employee_id, "data": str(obj.data), "tipo": obj.tipo})
    db.commit()
    db.refresh(obj)
    return obj


@router.get("/abonos", response_model=None)
def list_abonos(
    employee_id: int | None = None,
    status: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(30, ge=1, le=200),
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    q = db.query(AbonoFalta)
    if current.role == RoleEnum.employee:
        q = q.filter(AbonoFalta.employee_id == current.employee_id)
    elif employee_id:
        q = q.filter(AbonoFalta.employee_id == employee_id)
    if status:
        q = q.filter(AbonoFalta.status == status)
    if data_inicio:
        q = q.filter(AbonoFalta.data >= data_inicio)
    if data_fim:
        q = q.filter(AbonoFalta.data <= data_fim)
    q = q.order_by(AbonoFalta.data.desc())
    return _paginate(q, page, size)


@router.patch("/abonos/{abono_id}", response_model=AbonoFaltaOut)
def aprovar_rejeitar_abono(
    abono_id: int,
    payload: AbonoFaltaUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr)),
):
    """Aprova ou rejeita um abono de falta/atraso."""
    if payload.status not in STATUS_ABONO:
        raise HTTPException(status_code=422, detail=f"status inválido; use: {STATUS_ABONO}")
    obj = db.get(AbonoFalta, abono_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Abono não encontrado")
    before = {"status": obj.status}
    obj.status = payload.status
    if payload.motivo is not None:
        obj.motivo = payload.motivo
    obj.aprovado_por_id = current.id
    write_audit(db, user_id=current.id, action="update", entity="abonos_falta",
                entity_id=str(obj.id), before_data=before,
                after_data={"status": obj.status})
    db.commit()
    db.refresh(obj)
    return obj


# ══════════════════════════════════════════════════════════════════════════════
#  Dashboard
# ══════════════════════════════════════════════════════════════════════════════

@router.get("/dashboard")
def dashboard(
    periodo: str = Query(..., description="YYYY-MM"),
    db: Session = Depends(get_db),
    _: User = Depends(require_roles(RoleEnum.admin, RoleEnum.hr, RoleEnum.read_only)),
):
    """KPIs de frequência de todos os servidores em um período."""
    try:
        year, month = int(periodo[:4]), int(periodo[5:7])
        if not (1 <= month <= 12):
            raise ValueError
    except (ValueError, IndexError):
        raise HTTPException(status_code=422, detail="Período inválido; use YYYY-MM")

    employees = db.query(Employee).all()
    total_servidores = len(employees)
    soma_presencas = 0
    soma_faltas = 0
    soma_faltas_abonadas = 0
    soma_horas_extras = 0.0
    soma_min_atraso = 0
    servidores_com_falta: list[dict] = []

    for emp in employees:
        try:
            folha = _calcular_folha(db, emp.id, periodo)
        except HTTPException:
            continue
        soma_presencas += folha["total_presencas"]
        soma_faltas += folha["total_faltas"]
        soma_faltas_abonadas += folha["total_faltas_abonadas"]
        soma_horas_extras += folha["total_horas_extras"]
        soma_min_atraso += folha["total_minutos_atraso"]
        if folha["total_faltas"] > 0:
            servidores_com_falta.append({
                "employee_id": emp.id,
                "employee_name": emp.name,
                "faltas": folha["total_faltas"],
            })

    abonos_pendentes = (
        db.query(func.count(AbonoFalta.id))
        .filter(AbonoFalta.status == "pendente")
        .scalar() or 0
    )

    return {
        "periodo": periodo,
        "total_servidores": total_servidores,
        "total_presencas": soma_presencas,
        "total_faltas": soma_faltas,
        "total_faltas_abonadas": soma_faltas_abonadas,
        "total_horas_extras": round(soma_horas_extras, 2),
        "total_minutos_atraso": soma_min_atraso,
        "abonos_pendentes": abonos_pendentes,
        "servidores_com_falta": sorted(servidores_com_falta, key=lambda x: -x["faltas"])[:10],
    }
