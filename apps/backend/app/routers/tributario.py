"""Router Tributário / Arrecadação Municipal.

Cobre:
  - Cadastro de contribuintes
  - Cadastro imobiliário (imóveis para IPTU)
  - Lançamentos tributários (IPTU, ISS, ITBI, taxas)
  - Emissão e baixa de guias de arrecadação
  - Inscrição e gestão de dívida ativa
"""

import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    Contribuinte,
    DividaAtiva,
    GuiaPagamento,
    ImovelCadastral,
    LancamentoTributario,
    RoleEnum,
    User,
)
from ..schemas import (
    ContribuinteCreate,
    ContribuinteOut,
    ContribuinteUpdate,
    DividaAtivaCreate,
    DividaAtivaOut,
    DividaAtivaUpdate,
    GuiaOut,
    ImovelCreate,
    ImovelOut,
    ImovelUpdate,
    LancamentoCreate,
    LancamentoOut,
    LancamentoUpdate,
)

router = APIRouter(prefix="/tributario", tags=["tributario"])


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


def _calc_total(p: float, j: float, m: float, d: float) -> float:
    return round(p + j + m - d, 2)


def _gerar_codigo_barras(lancamento_id: int, vencimento: date) -> str:
    """Gera código de barras simulado (numérico) para a guia."""
    uid = uuid.uuid4().hex[:8].upper()
    return f"PREFMUN.{lancamento_id:06d}.{vencimento.strftime('%Y%m%d')}.{uid}"


# ── Contribuintes ─────────────────────────────────────────────────────────────

@router.get("/contribuintes")
def list_contribuintes(
    search: str | None = None,
    tipo: str | None = None,
    ativo: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Contribuinte)
    if search:
        q = q.filter(
            Contribuinte.nome.ilike(f"%{search}%")
            | Contribuinte.cpf_cnpj.ilike(f"%{search}%")
        )
    if tipo:
        q = q.filter(Contribuinte.tipo == tipo)
    if ativo is not None:
        q = q.filter(Contribuinte.ativo == ativo)
    return _paginate(q.order_by(Contribuinte.nome), page, size)


@router.get("/contribuintes/{contribuinte_id}", response_model=ContribuinteOut)
def get_contribuinte(contribuinte_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(Contribuinte, contribuinte_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Contribuinte não encontrado")
    return obj


@router.post("/contribuintes", response_model=ContribuinteOut)
def create_contribuinte(
    payload: ContribuinteCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if db.query(Contribuinte).filter(Contribuinte.cpf_cnpj == payload.cpf_cnpj).first():
        raise HTTPException(status_code=409, detail="CPF/CNPJ já cadastrado")
    obj = Contribuinte(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="contribuintes", entity_id=str(obj.id),
                after_data={"cpf_cnpj": obj.cpf_cnpj, "nome": obj.nome})
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/contribuintes/{contribuinte_id}", response_model=ContribuinteOut)
def update_contribuinte(
    contribuinte_id: int,
    payload: ContribuinteUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    obj = db.get(Contribuinte, contribuinte_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Contribuinte não encontrado")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    write_audit(db, user_id=current.id, action="update", entity="contribuintes", entity_id=str(obj.id),
                after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(obj)
    return obj


# ── Cadastro Imobiliário ──────────────────────────────────────────────────────

@router.get("/imoveis")
def list_imoveis(
    contribuinte_id: int | None = None,
    bairro: str | None = None,
    uso: str | None = None,
    ativo: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ImovelCadastral)
    if contribuinte_id:
        q = q.filter(ImovelCadastral.contribuinte_id == contribuinte_id)
    if bairro:
        q = q.filter(ImovelCadastral.bairro.ilike(f"%{bairro}%"))
    if uso:
        q = q.filter(ImovelCadastral.uso == uso)
    if ativo is not None:
        q = q.filter(ImovelCadastral.ativo == ativo)
    return _paginate(q.order_by(ImovelCadastral.inscricao), page, size)


@router.get("/imoveis/{imovel_id}", response_model=ImovelOut)
def get_imovel(imovel_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(ImovelCadastral, imovel_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    return obj


@router.post("/imoveis", response_model=ImovelOut)
def create_imovel(
    payload: ImovelCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not db.get(Contribuinte, payload.contribuinte_id):
        raise HTTPException(status_code=404, detail="Contribuinte não encontrado")
    if db.query(ImovelCadastral).filter(ImovelCadastral.inscricao == payload.inscricao).first():
        raise HTTPException(status_code=409, detail="Inscrição cadastral já existe")
    obj = ImovelCadastral(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="imoveis_cadastrais", entity_id=str(obj.id),
                after_data={"inscricao": obj.inscricao, "logradouro": obj.logradouro})
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/imoveis/{imovel_id}", response_model=ImovelOut)
def update_imovel(
    imovel_id: int,
    payload: ImovelUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    obj = db.get(ImovelCadastral, imovel_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    write_audit(db, user_id=current.id, action="update", entity="imoveis_cadastrais", entity_id=str(obj.id),
                after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(obj)
    return obj


# ── Lançamentos Tributários ───────────────────────────────────────────────────

@router.get("/lancamentos")
def list_lancamentos(
    contribuinte_id: int | None = None,
    tributo: str | None = None,
    status: str | None = None,
    exercicio: int | None = None,
    vencidos: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(LancamentoTributario)
    if contribuinte_id:
        q = q.filter(LancamentoTributario.contribuinte_id == contribuinte_id)
    if tributo:
        q = q.filter(LancamentoTributario.tributo == tributo)
    if status:
        q = q.filter(LancamentoTributario.status == status)
    if exercicio:
        q = q.filter(LancamentoTributario.exercicio == exercicio)
    if vencidos:
        q = q.filter(LancamentoTributario.vencimento < date.today(), LancamentoTributario.status == "aberto")
    return _paginate(q.order_by(LancamentoTributario.vencimento), page, size)


@router.get("/lancamentos/{lancamento_id}", response_model=LancamentoOut)
def get_lancamento(lancamento_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(LancamentoTributario, lancamento_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    return obj


@router.post("/lancamentos", response_model=LancamentoOut)
def create_lancamento(
    payload: LancamentoCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if not db.get(Contribuinte, payload.contribuinte_id):
        raise HTTPException(status_code=404, detail="Contribuinte não encontrado")
    if payload.imovel_id and not db.get(ImovelCadastral, payload.imovel_id):
        raise HTTPException(status_code=404, detail="Imóvel não encontrado")
    data = payload.model_dump()
    data["valor_total"] = _calc_total(
        data["valor_principal"], data["valor_juros"],
        data["valor_multa"], data["valor_desconto"],
    )
    obj = LancamentoTributario(**data)
    db.add(obj)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="lancamentos_tributarios", entity_id=str(obj.id),
                after_data={"tributo": obj.tributo, "valor_total": obj.valor_total, "vencimento": str(obj.vencimento)})
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/lancamentos/{lancamento_id}", response_model=LancamentoOut)
def update_lancamento(
    lancamento_id: int,
    payload: LancamentoUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    obj = db.get(LancamentoTributario, lancamento_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    before = {"status": obj.status, "valor_total": obj.valor_total}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    # Recalculate total when financial fields change
    obj.valor_total = _calc_total(obj.valor_principal, obj.valor_juros, obj.valor_multa, obj.valor_desconto)
    write_audit(db, user_id=current.id, action="update", entity="lancamentos_tributarios", entity_id=str(obj.id),
                before_data=before, after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(obj)
    return obj


# ── Guias de Arrecadação ──────────────────────────────────────────────────────

@router.post("/lancamentos/{lancamento_id}/emitir-guia", response_model=GuiaOut)
def emitir_guia(
    lancamento_id: int,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Emite (gera) uma guia de arrecadação para o lançamento.
    Apenas lançamentos em status 'aberto' podem ter guia emitida."""
    obj = db.get(LancamentoTributario, lancamento_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if obj.status not in ("aberto",):
        raise HTTPException(status_code=422, detail=f"Lançamento em status '{obj.status}' não permite nova guia")

    # Cancela guias abertas anteriores para este lançamento
    db.query(GuiaPagamento).filter(
        GuiaPagamento.lancamento_id == lancamento_id,
        GuiaPagamento.status == "emitida",
    ).update({"status": "cancelada"})

    guia = GuiaPagamento(
        lancamento_id=lancamento_id,
        codigo_barras=_gerar_codigo_barras(lancamento_id, obj.vencimento),
        valor=obj.valor_total,
        vencimento=obj.vencimento,
        status="emitida",
    )
    db.add(guia)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="guias_pagamento", entity_id=str(guia.id),
                after_data={"lancamento_id": lancamento_id, "valor": guia.valor, "codigo_barras": guia.codigo_barras})
    db.commit()
    db.refresh(guia)
    return guia


@router.post("/guias/{guia_id}/baixar", response_model=GuiaOut)
def baixar_guia(
    guia_id: int,
    data_pagamento: date,
    banco: str | None = None,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Registra o pagamento (baixa) de uma guia, marcando o lançamento como pago."""
    guia = db.get(GuiaPagamento, guia_id)
    if not guia:
        raise HTTPException(status_code=404, detail="Guia não encontrada")
    if guia.status != "emitida":
        raise HTTPException(status_code=422, detail=f"Guia em status '{guia.status}' não pode ser baixada")

    guia.status = "paga"
    guia.data_pagamento = data_pagamento
    if banco:
        guia.banco = banco

    # Atualiza lançamento
    lancamento = db.get(LancamentoTributario, guia.lancamento_id)
    if lancamento:
        lancamento.status = "pago"
        lancamento.data_pagamento = data_pagamento

    write_audit(db, user_id=current.id, action="update", entity="guias_pagamento", entity_id=str(guia_id),
                after_data={"status": "paga", "data_pagamento": str(data_pagamento)})
    db.commit()
    db.refresh(guia)
    return guia


@router.get("/guias")
def list_guias(
    lancamento_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(GuiaPagamento)
    if lancamento_id:
        q = q.filter(GuiaPagamento.lancamento_id == lancamento_id)
    if status:
        q = q.filter(GuiaPagamento.status == status)
    return _paginate(q.order_by(GuiaPagamento.created_at.desc()), page, size)


# ── Dívida Ativa ──────────────────────────────────────────────────────────────

@router.post("/divida-ativa", response_model=DividaAtivaOut)
def inscrever_divida(
    payload: DividaAtivaCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Inscreve um lançamento em dívida ativa municipal."""
    lancamento = db.get(LancamentoTributario, payload.lancamento_id)
    if not lancamento:
        raise HTTPException(status_code=404, detail="Lançamento não encontrado")
    if lancamento.status == "pago":
        raise HTTPException(status_code=422, detail="Lançamento já foi pago; não pode ser inscrito em dívida ativa")
    if db.query(DividaAtiva).filter(DividaAtiva.lancamento_id == payload.lancamento_id).first():
        raise HTTPException(status_code=409, detail="Lançamento já inscrito em dívida ativa")
    if db.query(DividaAtiva).filter(DividaAtiva.numero_inscricao == payload.numero_inscricao).first():
        raise HTTPException(status_code=409, detail="Número de inscrição já existe")

    divida = DividaAtiva(
        lancamento_id=payload.lancamento_id,
        contribuinte_id=lancamento.contribuinte_id,
        numero_inscricao=payload.numero_inscricao,
        tributo=lancamento.tributo,
        exercicio=lancamento.exercicio,
        valor_original=lancamento.valor_total,
        valor_atualizado=payload.valor_atualizado,
        data_inscricao=payload.data_inscricao,
        observacoes=payload.observacoes,
    )
    db.add(divida)
    # Marcar lançamento como inscrito em dívida ativa
    lancamento.status = "inscrito_divida"
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="divida_ativa", entity_id=str(divida.id),
                after_data={"numero_inscricao": divida.numero_inscricao, "tributo": divida.tributo, "valor_original": divida.valor_original})
    db.commit()
    db.refresh(divida)
    return divida


@router.get("/divida-ativa", response_model=None)
def list_divida(
    contribuinte_id: int | None = None,
    status: str | None = None,
    exercicio: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(DividaAtiva)
    if contribuinte_id:
        q = q.filter(DividaAtiva.contribuinte_id == contribuinte_id)
    if status:
        q = q.filter(DividaAtiva.status == status)
    if exercicio:
        q = q.filter(DividaAtiva.exercicio == exercicio)
    return _paginate(q.order_by(DividaAtiva.data_inscricao.desc()), page, size)


@router.get("/divida-ativa/{divida_id}", response_model=DividaAtivaOut)
def get_divida(divida_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(DividaAtiva, divida_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inscrição de dívida ativa não encontrada")
    return obj


@router.patch("/divida-ativa/{divida_id}", response_model=DividaAtivaOut)
def update_divida(
    divida_id: int,
    payload: DividaAtivaUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    obj = db.get(DividaAtiva, divida_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Inscrição de dívida ativa não encontrada")
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    # Se quitada, atualiza lançamento
    if payload.status == "quitada":
        lancamento = db.get(LancamentoTributario, obj.lancamento_id)
        if lancamento:
            lancamento.status = "pago"
    write_audit(db, user_id=current.id, action="update", entity="divida_ativa", entity_id=str(divida_id),
                after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(obj)
    return obj


# ── Dashboard / Resumo ────────────────────────────────────────────────────────

@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Resumo quantitativo e financeiro do módulo tributário."""
    from sqlalchemy import func

    total_contribuintes = db.query(func.count(Contribuinte.id)).filter(Contribuinte.ativo == True).scalar() or 0
    total_imoveis = db.query(func.count(ImovelCadastral.id)).filter(ImovelCadastral.ativo == True).scalar() or 0

    lancamentos_status = dict(
        db.query(LancamentoTributario.status, func.count(LancamentoTributario.id))
        .group_by(LancamentoTributario.status).all()
    )

    valor_aberto = db.query(func.sum(LancamentoTributario.valor_total)).filter(
        LancamentoTributario.status == "aberto"
    ).scalar() or 0.0

    valor_pago = db.query(func.sum(LancamentoTributario.valor_total)).filter(
        LancamentoTributario.status == "pago"
    ).scalar() or 0.0

    valor_divida_ativa = db.query(func.sum(DividaAtiva.valor_atualizado)).filter(
        DividaAtiva.status == "ativa"
    ).scalar() or 0.0

    vencidos_hoje = db.query(func.count(LancamentoTributario.id)).filter(
        LancamentoTributario.vencimento < date.today(),
        LancamentoTributario.status == "aberto",
    ).scalar() or 0

    return {
        "total_contribuintes_ativos": total_contribuintes,
        "total_imoveis_ativos": total_imoveis,
        "lancamentos_por_status": lancamentos_status,
        "valor_aberto": round(valor_aberto, 2),
        "valor_arrecadado": round(valor_pago, 2),
        "valor_divida_ativa": round(valor_divida_ativa, 2),
        "lancamentos_vencidos_abertos": vencidos_hoje,
    }


# ── Alíquotas IPTU ────────────────────────────────────────────────────────────

from ..models import AliquotaIPTU, ParcelamentoDivida, ParcelaDivida
from ..schemas import (
    AliquotaIPTUCreate, AliquotaIPTUOut, AliquotaIPTUUpdate,
    ParcelamentoDividaCreate, ParcelamentoDividaOut, ParcelamentoDividaUpdate, ParcelaDividaBaixa,
)


@router.get("/aliquotas-iptu", response_model=list[AliquotaIPTUOut])
def list_aliquotas(
    exercicio: int | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(AliquotaIPTU)
    if exercicio:
        q = q.filter(AliquotaIPTU.exercicio == exercicio)
    return q.order_by(AliquotaIPTU.exercicio.desc(), AliquotaIPTU.uso).all()


@router.post("/aliquotas-iptu", response_model=AliquotaIPTUOut, status_code=201)
def create_aliquota(
    data: AliquotaIPTUCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    # Enforce at most one aliquota per (exercicio, uso)
    existing = db.query(AliquotaIPTU).filter_by(exercicio=data.exercicio, uso=data.uso).first()
    if existing:
        raise HTTPException(400, f"Já existe alíquota para uso '{data.uso}' no exercício {data.exercicio}.")
    obj = AliquotaIPTU(**data.model_dump())
    db.add(obj)
    db.commit()
    db.refresh(obj)
    write_audit(db, user_id=current_user.id, entity="aliquota_iptu", entity_id=str(obj.id), action="create")
    return obj


@router.put("/aliquotas-iptu/{aliquota_id}", response_model=AliquotaIPTUOut)
def update_aliquota(
    aliquota_id: int,
    data: AliquotaIPTUUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    obj = db.get(AliquotaIPTU, aliquota_id)
    if not obj:
        raise HTTPException(404, "Alíquota não encontrada.")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    write_audit(db, user_id=current_user.id, entity="aliquota_iptu", entity_id=str(obj.id), action="update", after_data=data.model_dump(exclude_none=True))
    return obj


@router.delete("/aliquotas-iptu/{aliquota_id}", status_code=204)
def delete_aliquota(
    aliquota_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin)),
):
    obj = db.get(AliquotaIPTU, aliquota_id)
    if not obj:
        raise HTTPException(404, "Alíquota não encontrada.")
    db.delete(obj)
    db.commit()
    write_audit(db, user_id=current_user.id, entity="aliquota_iptu", entity_id=str(obj.id), action="delete")


# ── Geração automática de IPTU ────────────────────────────────────────────────

@router.post("/lancamentos/gerar-iptu")
def gerar_iptu(
    exercicio: int,
    vencimento: date,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Gera lançamentos de IPTU para todos os imóveis ativos do exercício.

    - Busca a alíquota configurada para (exercicio, uso do imóvel).
    - Calcula valor_principal = valor_venal × alíquota.
    - Pula imóveis que já têm lançamento IPTU para o exercício.
    - Pula imóveis com valor_venal = 0 ou sem alíquota configurada.
    - Retorna resumo com totais gerados e ignorados.
    """
    from sqlalchemy import func as sqlfunc

    competencia = f"{exercicio}-01"

    # Carregar alíquotas do exercício
    aliquotas = {
        a.uso: a.aliquota
        for a in db.query(AliquotaIPTU).filter(AliquotaIPTU.exercicio == exercicio).all()
    }
    if not aliquotas:
        raise HTTPException(422, f"Nenhuma alíquota cadastrada para o exercício {exercicio}. Cadastre antes de gerar.")

    # IDs de imóveis que já têm lançamento IPTU neste exercício
    ja_lancados: set[int] = {
        row[0]
        for row in db.query(LancamentoTributario.imovel_id)
        .filter(
            LancamentoTributario.tributo == "IPTU",
            LancamentoTributario.exercicio == exercicio,
            LancamentoTributario.imovel_id.isnot(None),
        )
        .all()
        if row[0] is not None
    }

    imoveis = db.query(ImovelCadastral).filter(ImovelCadastral.ativo == True).all()

    gerados = 0
    ignorados_sem_aliquota = 0
    ignorados_valor_zero = 0
    ignorados_ja_existia = 0

    for imovel in imoveis:
        if imovel.id in ja_lancados:
            ignorados_ja_existia += 1
            continue
        if imovel.valor_venal <= 0:
            ignorados_valor_zero += 1
            continue
        aliquota = aliquotas.get(imovel.uso)
        if aliquota is None:
            ignorados_sem_aliquota += 1
            continue

        valor_principal = round(imovel.valor_venal * aliquota, 2)
        lanc = LancamentoTributario(
            contribuinte_id=imovel.contribuinte_id,
            imovel_id=imovel.id,
            tributo="IPTU",
            competencia=competencia,
            exercicio=exercicio,
            valor_principal=valor_principal,
            valor_juros=0.0,
            valor_multa=0.0,
            valor_desconto=0.0,
            valor_total=valor_principal,
            vencimento=vencimento,
        )
        db.add(lanc)
        gerados += 1

    db.commit()
    write_audit(db, user_id=current_user.id, entity="lancamento_tributario", entity_id=str(None), action="gerar_iptu", after_data={"exercicio": exercicio, "gerados": gerados})
    return {
        "exercicio": exercicio,
        "vencimento": str(vencimento),
        "gerados": gerados,
        "ignorados_ja_existia": ignorados_ja_existia,
        "ignorados_sem_aliquota": ignorados_sem_aliquota,
        "ignorados_valor_zero": ignorados_valor_zero,
        "total_imoveis_ativos": len(imoveis),
    }


# ── Relatório de Arrecadação ──────────────────────────────────────────────────

import csv as _csv
from io import StringIO


@router.get("/relatorio/arrecadacao")
def relatorio_arrecadacao(
    tributo: str | None = None,
    exercicio: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    export: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Relatório consolidado de arrecadação por tributo/período, com exportação CSV."""
    from sqlalchemy import func as sqlfunc
    from fastapi import Response as FastResponse

    q = db.query(
        LancamentoTributario.tributo,
        LancamentoTributario.exercicio,
        LancamentoTributario.competencia,
        sqlfunc.count(LancamentoTributario.id).label("qtd"),
        sqlfunc.sum(LancamentoTributario.valor_total).label("valor_total"),
    ).filter(LancamentoTributario.status == "pago")

    if tributo:
        q = q.filter(LancamentoTributario.tributo == tributo)
    if exercicio:
        q = q.filter(LancamentoTributario.exercicio == exercicio)
    if data_inicio:
        q = q.filter(LancamentoTributario.data_pagamento >= data_inicio)
    if data_fim:
        q = q.filter(LancamentoTributario.data_pagamento <= data_fim)

    q = q.group_by(
        LancamentoTributario.tributo,
        LancamentoTributario.exercicio,
        LancamentoTributario.competencia,
    ).order_by(LancamentoTributario.exercicio.desc(), LancamentoTributario.competencia.desc())

    rows = q.all()

    if export == "csv":
        buf = StringIO()
        w = _csv.writer(buf)
        w.writerow(["tributo", "exercicio", "competencia", "qtd_lancamentos", "valor_total"])
        for r in rows:
            w.writerow([r.tributo, r.exercicio, r.competencia, r.qtd, round(r.valor_total or 0, 2)])
        from fastapi.responses import Response as FR
        return FR(
            content=buf.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=arrecadacao.csv"},
        )

    total_geral = sum(r.valor_total or 0 for r in rows)
    return {
        "filtros": {"tributo": tributo, "exercicio": exercicio, "data_inicio": str(data_inicio) if data_inicio else None, "data_fim": str(data_fim) if data_fim else None},
        "total_arrecadado": round(total_geral, 2),
        "registros": [
            {"tributo": r.tributo, "exercicio": r.exercicio, "competencia": r.competencia, "qtd_lancamentos": r.qtd, "valor_total": round(r.valor_total or 0, 2)}
            for r in rows
        ],
    }


# ── Parcelamento de Dívida Ativa ──────────────────────────────────────────────

@router.post("/parcelamentos", response_model=ParcelamentoDividaOut, status_code=201)
def create_parcelamento(
    data: ParcelamentoDividaCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Cria acordo de parcelamento e gera as parcelas mensais automaticamente."""
    divida = db.get(DividaAtiva, data.divida_id)
    if not divida:
        raise HTTPException(404, "Dívida ativa não encontrada.")
    if divida.status not in ("ativa", "ajuizada"):
        raise HTTPException(422, f"Dívida com status '{divida.status}' não pode ser parcelada.")
    if db.query(ParcelamentoDivida).filter_by(divida_id=data.divida_id, status="ativo").first():
        raise HTTPException(400, "Já existe parcelamento ativo para esta dívida.")

    parc = ParcelamentoDivida(
        divida_id=data.divida_id,
        numero_parcelas=data.numero_parcelas,
        valor_total=data.valor_total,
        data_acordo=data.data_acordo,
        observacoes=data.observacoes,
    )
    db.add(parc)
    db.flush()

    # Gera parcelas mensais a partir do mês seguinte ao acordo
    from dateutil.relativedelta import relativedelta as rdelta
    valor_parcela = round(data.valor_total / data.numero_parcelas, 2)
    # Ajuste da última parcela para absorver diferença de centavos
    total_parcelas = valor_parcela * (data.numero_parcelas - 1)
    valor_ultima = round(data.valor_total - total_parcelas, 2)

    for i in range(data.numero_parcelas):
        vencimento = data.data_acordo + rdelta(months=i + 1)
        valor = valor_ultima if i == data.numero_parcelas - 1 else valor_parcela
        db.add(ParcelaDivida(
            parcelamento_id=parc.id,
            divida_id=data.divida_id,
            numero_parcela=i + 1,
            valor=valor,
            vencimento=vencimento,
        ))

    # Update divida status to parcelada
    divida.status = "parcelada"
    db.commit()
    db.refresh(parc)
    write_audit(db, user_id=current_user.id, entity="parcelamento_divida", entity_id=str(parc.id), action="create", after_data=data.model_dump())
    return parc


@router.get("/parcelamentos")
def list_parcelamentos(
    divida_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(ParcelamentoDivida)
    if divida_id:
        q = q.filter(ParcelamentoDivida.divida_id == divida_id)
    if status:
        q = q.filter(ParcelamentoDivida.status == status)
    q = q.order_by(ParcelamentoDivida.id.desc())
    total = q.count()
    items = q.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/parcelamentos/{parcelamento_id}", response_model=ParcelamentoDividaOut)
def get_parcelamento(
    parcelamento_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = db.get(ParcelamentoDivida, parcelamento_id)
    if not obj:
        raise HTTPException(404, "Parcelamento não encontrado.")
    return obj


@router.post("/parcelamentos/{parcelamento_id}/parcelas/{parcela_id}/pagar", response_model=None)
def pagar_parcela(
    parcelamento_id: int,
    parcela_id: int,
    data: ParcelaDividaBaixa,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Registra pagamento de uma parcela e verifica quitação total do parcelamento."""
    parcela = db.get(ParcelaDivida, parcela_id)
    if not parcela or parcela.parcelamento_id != parcelamento_id:
        raise HTTPException(404, "Parcela não encontrada.")
    if parcela.status == "paga":
        raise HTTPException(400, "Parcela já está paga.")

    parcela.status = "paga"
    parcela.data_pagamento = data.data_pagamento

    # Check if all parcelas of the parcelamento are paid
    parcelamento = db.get(ParcelamentoDivida, parcelamento_id)
    todas_pagas = all(
        p.status == "paga" or p.id == parcela_id
        for p in parcelamento.parcelas
    )
    if todas_pagas:
        parcelamento.status = "quitado"
        divida = db.get(DividaAtiva, parcelamento.divida_id)
        if divida:
            divida.status = "quitada"

    db.commit()
    write_audit(db, user_id=current_user.id, entity="parcela_divida", entity_id=str(parcela.id), action="pagar", after_data={"data_pagamento": str(data.data_pagamento)})
    return {"ok": True, "parcelamento_quitado": todas_pagas}


@router.put("/parcelamentos/{parcelamento_id}", response_model=ParcelamentoDividaOut)
def update_parcelamento(
    parcelamento_id: int,
    data: ParcelamentoDividaUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    obj = db.get(ParcelamentoDivida, parcelamento_id)
    if not obj:
        raise HTTPException(404, "Parcelamento não encontrado.")
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(obj, k, v)
    db.commit()
    db.refresh(obj)
    write_audit(db, user_id=current_user.id, entity="parcelamento_divida", entity_id=str(obj.id), action="update", after_data=data.model_dump(exclude_none=True))
    return obj
