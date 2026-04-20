"""Router Frota — Gestão de Veículos, Abastecimentos e Manutenções.

Cobre:
  - Cadastro de veículos com tipo, combustível e status
  - Registro de abastecimentos com consumo e odômetro
  - Ordens de manutenção com peças/insumos (integração almoxarifado)
  - Dashboard consolidado por veículo
  - Auditoria nas operações principais
"""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    Abastecimento,
    Department,
    ItemAlmoxarifado,
    ItemManutencao,
    ManutencaoVeiculo,
    MovimentacaoEstoque,
    RoleEnum,
    User,
    Veiculo,
    utc_now,
)
from ..schemas import (
    AbastecimentoCreate,
    AbastecimentoOut,
    ItemManutencaoCreate,
    ManutencaoConcluir,
    ManutencaoCreate,
    ManutencaoOut,
    VeiculoCreate,
    VeiculoOut,
    VeiculoUpdate,
)

router = APIRouter(prefix="/frota", tags=["frota"])

_TIPOS_VEICULO = {"leve", "pesado", "onibus", "maquina", "moto"}
_COMBUSTIVEIS = {"flex", "gasolina", "diesel", "etanol", "eletrico", "gnv"}
_STATUS_VEICULO = {"ativo", "manutencao", "inativo"}
_TIPOS_MANUTENCAO = {"preventiva", "corretiva", "revisao"}
_STATUS_MANUTENCAO = {"aberta", "em_andamento", "concluida", "cancelada"}


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


# ── Veículos ──────────────────────────────────────────────────────────────────

@router.post("/veiculos", response_model=VeiculoOut, status_code=201)
def criar_veiculo(
    data: VeiculoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Cadastra um novo veículo na frota."""
    data.placa = data.placa.upper().strip()
    if db.query(Veiculo).filter_by(placa=data.placa).first():
        raise HTTPException(422, "Placa já cadastrada.")
    if data.tipo not in _TIPOS_VEICULO:
        raise HTTPException(422, f"tipo inválido. Válidos: {sorted(_TIPOS_VEICULO)}")
    if data.combustivel not in _COMBUSTIVEIS:
        raise HTTPException(422, f"combustivel inválido. Válidos: {sorted(_COMBUSTIVEIS)}")
    if data.status not in _STATUS_VEICULO:
        raise HTTPException(422, f"status inválido. Válidos: {sorted(_STATUS_VEICULO)}")
    if data.departamento_id and not db.get(Department, data.departamento_id):
        raise HTTPException(404, "Departamento não encontrado.")

    veiculo = Veiculo(**data.model_dump())
    db.add(veiculo)
    db.flush()
    write_audit(db, user_id=current_user.id, entity="veiculos", entity_id=str(veiculo.id),
                action="create", after_data=data.model_dump())
    db.commit()
    db.refresh(veiculo)
    return veiculo


@router.get("/veiculos", response_model=None)
def list_veiculos(
    search: str | None = None,
    tipo: str | None = None,
    status: str | None = None,
    departamento_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista veículos com filtros e paginação."""
    q = db.query(Veiculo)
    if search:
        q = q.filter(
            Veiculo.descricao.ilike(f"%{search}%")
            | Veiculo.placa.ilike(f"%{search}%")
            | Veiculo.modelo.ilike(f"%{search}%")
        )
    if tipo:
        q = q.filter(Veiculo.tipo == tipo)
    if status:
        q = q.filter(Veiculo.status == status)
    if departamento_id:
        q = q.filter(Veiculo.departamento_id == departamento_id)
    q = q.order_by(Veiculo.placa)
    return _paginate(q, page, size)


@router.get("/veiculos/dashboard")
def dashboard_frota(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Resumo executivo da frota."""
    total = db.query(func.count(Veiculo.id)).scalar()
    ativos = db.query(func.count(Veiculo.id)).filter(Veiculo.status == "ativo").scalar()
    em_manutencao = db.query(func.count(Veiculo.id)).filter(Veiculo.status == "manutencao").scalar()
    inativos = db.query(func.count(Veiculo.id)).filter(Veiculo.status == "inativo").scalar()

    mes_atual = date.today().replace(day=1)
    abastecimentos_mes = db.query(func.count(Abastecimento.id)).filter(
        Abastecimento.data_abastecimento >= mes_atual
    ).scalar()
    litros_mes = db.query(func.coalesce(func.sum(Abastecimento.litros), 0)).filter(
        Abastecimento.data_abastecimento >= mes_atual
    ).scalar()
    custo_abastecimento_mes = db.query(func.coalesce(func.sum(Abastecimento.valor_total), 0)).filter(
        Abastecimento.data_abastecimento >= mes_atual
    ).scalar()

    manutencoes_abertas = db.query(func.count(ManutencaoVeiculo.id)).filter(
        ManutencaoVeiculo.status.in_(["aberta", "em_andamento"])
    ).scalar()
    custo_manutencao_mes = db.query(func.coalesce(func.sum(ManutencaoVeiculo.valor_servico), 0)).filter(
        ManutencaoVeiculo.data_abertura >= mes_atual
    ).scalar()

    return {
        "total_veiculos": total,
        "ativos": ativos,
        "em_manutencao": em_manutencao,
        "inativos": inativos,
        "abastecimentos_mes": abastecimentos_mes,
        "litros_mes": round(float(litros_mes), 2),
        "custo_abastecimento_mes": round(float(custo_abastecimento_mes), 2),
        "manutencoes_abertas": manutencoes_abertas,
        "custo_manutencao_mes": round(float(custo_manutencao_mes), 2),
    }


@router.get("/veiculos/{veiculo_id}", response_model=VeiculoOut)
def get_veiculo(veiculo_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    v = db.get(Veiculo, veiculo_id)
    if not v:
        raise HTTPException(404, "Veículo não encontrado.")
    return v


@router.patch("/veiculos/{veiculo_id}", response_model=VeiculoOut)
def atualizar_veiculo(
    veiculo_id: int,
    data: VeiculoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Atualiza campos do veículo (incluindo odômetro e status)."""
    v = db.get(Veiculo, veiculo_id)
    if not v:
        raise HTTPException(404, "Veículo não encontrado.")
    before = {c: getattr(v, c) for c in VeiculoUpdate.model_fields}
    updates = data.model_dump(exclude_none=True)
    if "tipo" in updates and updates["tipo"] not in _TIPOS_VEICULO:
        raise HTTPException(422, f"tipo inválido. Válidos: {sorted(_TIPOS_VEICULO)}")
    if "combustivel" in updates and updates["combustivel"] not in _COMBUSTIVEIS:
        raise HTTPException(422, f"combustivel inválido. Válidos: {sorted(_COMBUSTIVEIS)}")
    if "status" in updates and updates["status"] not in _STATUS_VEICULO:
        raise HTTPException(422, f"status inválido. Válidos: {sorted(_STATUS_VEICULO)}")
    if "departamento_id" in updates and updates["departamento_id"] and not db.get(Department, updates["departamento_id"]):
        raise HTTPException(404, "Departamento não encontrado.")
    for k, val in updates.items():
        setattr(v, k, val)
    write_audit(db, user_id=current_user.id, entity="veiculos", entity_id=str(v.id),
                action="update", before_data=before, after_data=updates)
    db.commit()
    db.refresh(v)
    return v


# ── Abastecimentos ────────────────────────────────────────────────────────────

@router.post("/abastecimentos", response_model=AbastecimentoOut, status_code=201)
def registrar_abastecimento(
    data: AbastecimentoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Registra abastecimento. Atualiza odômetro do veículo se fornecido."""
    veiculo = db.get(Veiculo, data.veiculo_id)
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado.")
    if veiculo.status == "inativo":
        raise HTTPException(422, "Veículo inativo não pode ser abastecido.")
    if data.litros <= 0:
        raise HTTPException(422, "Litros deve ser positivo.")
    if data.combustivel not in _COMBUSTIVEIS:
        raise HTTPException(422, f"combustivel inválido. Válidos: {sorted(_COMBUSTIVEIS)}")
    if data.departamento_id and not db.get(Department, data.departamento_id):
        raise HTTPException(404, "Departamento não encontrado.")
    if data.motorista_id and not db.get(User, data.motorista_id):
        raise HTTPException(404, "Motorista/usuário não encontrado.")
    if data.movimentacao_id and not db.get(MovimentacaoEstoque, data.movimentacao_id):
        raise HTTPException(404, "Movimentação de almoxarifado não encontrada.")

    valor_total = round(data.litros * data.valor_litro, 2)

    # Atualiza odômetro do veículo se o novo valor for maior
    if data.odometro > veiculo.odometro_atual:
        veiculo.odometro_atual = data.odometro

    ab = Abastecimento(
        veiculo_id=data.veiculo_id,
        data_abastecimento=data.data_abastecimento,
        combustivel=data.combustivel,
        litros=data.litros,
        valor_litro=data.valor_litro,
        valor_total=valor_total,
        odometro=data.odometro,
        posto=data.posto,
        nota_fiscal=data.nota_fiscal,
        departamento_id=data.departamento_id,
        motorista_id=data.motorista_id,
        movimentacao_id=data.movimentacao_id,
        observacoes=data.observacoes,
    )
    db.add(ab)
    db.flush()
    write_audit(db, user_id=current_user.id, entity="abastecimentos", entity_id=str(ab.id),
                action="create",
                after_data={k: str(v) if isinstance(v, date) else v for k, v in data.model_dump().items()})
    db.commit()
    db.refresh(ab)
    return ab


@router.get("/abastecimentos", response_model=None)
def list_abastecimentos(
    veiculo_id: int | None = None,
    departamento_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista abastecimentos com filtros de veículo, departamento e período."""
    q = db.query(Abastecimento)
    if veiculo_id:
        q = q.filter(Abastecimento.veiculo_id == veiculo_id)
    if departamento_id:
        q = q.filter(Abastecimento.departamento_id == departamento_id)
    if data_inicio:
        q = q.filter(Abastecimento.data_abastecimento >= data_inicio)
    if data_fim:
        q = q.filter(Abastecimento.data_abastecimento <= data_fim)
    q = q.order_by(Abastecimento.data_abastecimento.desc(), Abastecimento.id.desc())
    return _paginate(q, page, size)


@router.get("/abastecimentos/{ab_id}", response_model=AbastecimentoOut)
def get_abastecimento(ab_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ab = db.get(Abastecimento, ab_id)
    if not ab:
        raise HTTPException(404, "Abastecimento não encontrado.")
    return ab


# ── Manutenções ───────────────────────────────────────────────────────────────

@router.post("/manutencoes", response_model=ManutencaoOut, status_code=201)
def abrir_manutencao(
    data: ManutencaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Abre uma ordem de manutenção; opcionalmente adiciona peças/insumos do almoxarifado."""
    veiculo = db.get(Veiculo, data.veiculo_id)
    if not veiculo:
        raise HTTPException(404, "Veículo não encontrado.")
    if data.tipo not in _TIPOS_MANUTENCAO:
        raise HTTPException(422, f"tipo inválido. Válidos: {sorted(_TIPOS_MANUTENCAO)}")
    if data.departamento_id and not db.get(Department, data.departamento_id):
        raise HTTPException(404, "Departamento não encontrado.")

    man = ManutencaoVeiculo(
        veiculo_id=data.veiculo_id,
        tipo=data.tipo,
        descricao=data.descricao,
        data_abertura=data.data_abertura,
        odometro=data.odometro,
        oficina=data.oficina,
        departamento_id=data.departamento_id,
        responsavel_id=current_user.id,
        observacoes=data.observacoes,
        status="aberta",
    )
    db.add(man)
    db.flush()

    # Muda status do veículo para "manutencao"
    if veiculo.status == "ativo":
        veiculo.status = "manutencao"

    # Itens/peças
    for item_data in data.itens:
        _adicionar_item_manutencao(db, man, item_data, current_user, data.departamento_id)

    write_audit(db, user_id=current_user.id, entity="manutencoes_veiculo", entity_id=str(man.id),
                action="create",
                after_data={"veiculo_id": data.veiculo_id, "tipo": data.tipo, "descricao": data.descricao})
    db.commit()
    db.refresh(man)
    return man


def _adicionar_item_manutencao(db, man: ManutencaoVeiculo, item_data, current_user: User, departamento_id):
    """Cria ItemManutencao e, se item_almoxarifado_id fornecido, registra saída no almoxarifado."""
    from ..models import AlertaEstoqueMinimo

    valor_total = round(item_data.quantidade * item_data.valor_unitario, 2)
    mov_id = None

    alm_vu = None
    if item_data.item_almoxarifado_id:
        alm_item = db.get(ItemAlmoxarifado, item_data.item_almoxarifado_id)
        if not alm_item:
            raise HTTPException(404, f"Item almoxarifado {item_data.item_almoxarifado_id} não encontrado.")
        if not alm_item.ativo:
            raise HTTPException(422, f"Item almoxarifado {item_data.item_almoxarifado_id} está inativo.")
        if alm_item.estoque_atual < item_data.quantidade:
            raise HTTPException(422,
                f"Saldo insuficiente para '{alm_item.descricao}': "
                f"disponível={alm_item.estoque_atual}, solicitado={item_data.quantidade}.")

        alm_vu = alm_item.valor_unitario
        valor_total_mov = round(item_data.quantidade * alm_vu, 2)
        alm_item.estoque_atual = round(alm_item.estoque_atual - item_data.quantidade, 4)

        mov = MovimentacaoEstoque(
            item_id=alm_item.id,
            tipo="saida",
            quantidade=item_data.quantidade,
            valor_unitario=alm_vu,
            valor_total=valor_total_mov,
            data_movimentacao=man.data_abertura,
            departamento_id=departamento_id,
            responsavel_id=current_user.id,
            documento_ref=f"MANUT-{man.id}",
            observacoes=f"Saída automática — manutenção veículo {man.veiculo_id}",
            saldo_pos=alm_item.estoque_atual,
        )
        db.add(mov)
        db.flush()
        mov_id = mov.id

        # Auto-alerta estoque mínimo
        if alm_item.estoque_minimo > 0 and alm_item.estoque_atual < alm_item.estoque_minimo:
            alerta_aberto = db.query(AlertaEstoqueMinimo).filter(
                AlertaEstoqueMinimo.item_id == alm_item.id,
                AlertaEstoqueMinimo.status == "aberto",
            ).first()
            if not alerta_aberto:
                db.add(AlertaEstoqueMinimo(
                    item_id=alm_item.id,
                    movimentacao_id=mov.id,
                    saldo_no_momento=alm_item.estoque_atual,
                    estoque_minimo=alm_item.estoque_minimo,
                    status="aberto",
                ))

        write_audit(db, user_id=current_user.id, entity="movimentacoes_estoque",
                    entity_id=str(mov.id), action="saida",
                    after_data={"item_id": alm_item.id, "quantidade": item_data.quantidade,
                                "origem": "manutencao"})

        valor_total = round(item_data.quantidade * alm_vu, 2)

    it = ItemManutencao(
        manutencao_id=man.id,
        descricao=item_data.descricao,
        quantidade=item_data.quantidade,
        valor_unitario=alm_vu if alm_vu is not None else item_data.valor_unitario,
        valor_total=valor_total,
        item_almoxarifado_id=item_data.item_almoxarifado_id,
        movimentacao_id=mov_id,
    )
    db.add(it)
    db.flush()


@router.get("/manutencoes", response_model=None)
def list_manutencoes(
    veiculo_id: int | None = None,
    status: str | None = None,
    tipo: str | None = None,
    departamento_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista manutenções com filtros."""
    q = db.query(ManutencaoVeiculo)
    if veiculo_id:
        q = q.filter(ManutencaoVeiculo.veiculo_id == veiculo_id)
    if status:
        q = q.filter(ManutencaoVeiculo.status == status)
    if tipo:
        q = q.filter(ManutencaoVeiculo.tipo == tipo)
    if departamento_id:
        q = q.filter(ManutencaoVeiculo.departamento_id == departamento_id)
    if data_inicio:
        q = q.filter(ManutencaoVeiculo.data_abertura >= data_inicio)
    if data_fim:
        q = q.filter(ManutencaoVeiculo.data_abertura <= data_fim)
    q = q.order_by(ManutencaoVeiculo.id.desc())
    return _paginate(q, page, size)


@router.get("/manutencoes/{man_id}", response_model=ManutencaoOut)
def get_manutencao(man_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    man = db.get(ManutencaoVeiculo, man_id)
    if not man:
        raise HTTPException(404, "Manutenção não encontrada.")
    return man


@router.post("/manutencoes/{man_id}/concluir", response_model=ManutencaoOut)
def concluir_manutencao(
    man_id: int,
    data: ManutencaoConcluir,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Conclui a manutenção e reativa o veículo."""
    man = db.get(ManutencaoVeiculo, man_id)
    if not man:
        raise HTTPException(404, "Manutenção não encontrada.")
    if man.status in ("concluida", "cancelada"):
        raise HTTPException(422, f"Manutenção já está '{man.status}'.")

    man.status = "concluida"
    man.data_conclusao = data.data_conclusao
    man.valor_servico = data.valor_servico
    if data.oficina:
        man.oficina = data.oficina
    if data.observacoes:
        man.observacoes = data.observacoes

    # Reativa o veículo se não há outras manutenções abertas
    outras = db.query(ManutencaoVeiculo).filter(
        ManutencaoVeiculo.veiculo_id == man.veiculo_id,
        ManutencaoVeiculo.id != man.id,
        ManutencaoVeiculo.status.in_(["aberta", "em_andamento"]),
    ).first()
    if not outras:
        veiculo = db.get(Veiculo, man.veiculo_id)
        if veiculo and veiculo.status == "manutencao":
            veiculo.status = "ativo"

    write_audit(db, user_id=current_user.id, entity="manutencoes_veiculo", entity_id=str(man.id),
                action="concluir",
                after_data={"status": "concluida", "data_conclusao": str(data.data_conclusao),
                            "valor_servico": data.valor_servico})
    db.commit()
    db.refresh(man)
    return man


@router.post("/manutencoes/{man_id}/cancelar", response_model=ManutencaoOut)
def cancelar_manutencao(
    man_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Cancela a ordem de manutenção e reativa o veículo."""
    man = db.get(ManutencaoVeiculo, man_id)
    if not man:
        raise HTTPException(404, "Manutenção não encontrada.")
    if man.status in ("concluida", "cancelada"):
        raise HTTPException(422, f"Manutenção já está '{man.status}'.")

    man.status = "cancelada"

    outras = db.query(ManutencaoVeiculo).filter(
        ManutencaoVeiculo.veiculo_id == man.veiculo_id,
        ManutencaoVeiculo.id != man.id,
        ManutencaoVeiculo.status.in_(["aberta", "em_andamento"]),
    ).first()
    if not outras:
        veiculo = db.get(Veiculo, man.veiculo_id)
        if veiculo and veiculo.status == "manutencao":
            veiculo.status = "ativo"

    write_audit(db, user_id=current_user.id, entity="manutencoes_veiculo", entity_id=str(man.id),
                action="cancelar", after_data={"status": "cancelada"})
    db.commit()
    db.refresh(man)
    return man


@router.post("/manutencoes/{man_id}/itens", response_model=ManutencaoOut, status_code=201)
def adicionar_item(
    man_id: int,
    item_data: ItemManutencaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Adiciona peça/insumo a uma manutenção aberta; opcionalmente faz saída do almoxarifado."""
    man = db.get(ManutencaoVeiculo, man_id)
    if not man:
        raise HTTPException(404, "Manutenção não encontrada.")
    if man.status in ("concluida", "cancelada"):
        raise HTTPException(422, f"Manutenção já está '{man.status}'.")
    _adicionar_item_manutencao(db, man, item_data, current_user, man.departamento_id)
    db.commit()
    db.refresh(man)
    return man


@router.get("/veiculos/{veiculo_id}/consumo")
def consumo_veiculo(
    veiculo_id: int,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Resumo de consumo (abastecimentos + manutenções) para um veículo."""
    v = db.get(Veiculo, veiculo_id)
    if not v:
        raise HTTPException(404, "Veículo não encontrado.")

    q_ab = db.query(Abastecimento).filter(Abastecimento.veiculo_id == veiculo_id)
    q_man = db.query(ManutencaoVeiculo).filter(ManutencaoVeiculo.veiculo_id == veiculo_id)
    if data_inicio:
        q_ab = q_ab.filter(Abastecimento.data_abastecimento >= data_inicio)
        q_man = q_man.filter(ManutencaoVeiculo.data_abertura >= data_inicio)
    if data_fim:
        q_ab = q_ab.filter(Abastecimento.data_abastecimento <= data_fim)
        q_man = q_man.filter(ManutencaoVeiculo.data_abertura <= data_fim)

    total_litros = sum(a.litros for a in q_ab.all())
    custo_combustivel = sum(a.valor_total for a in q_ab.all())
    custo_manutencao = sum(m.valor_servico for m in q_man.all())

    return {
        "veiculo_id": veiculo_id,
        "placa": v.placa,
        "descricao": v.descricao,
        "odometro_atual": v.odometro_atual,
        "total_abastecimentos": q_ab.count(),
        "total_litros": round(total_litros, 2),
        "custo_combustivel": round(custo_combustivel, 2),
        "total_manutencoes": q_man.count(),
        "custo_manutencao": round(custo_manutencao, 2),
        "custo_total": round(custo_combustivel + custo_manutencao, 2),
    }
