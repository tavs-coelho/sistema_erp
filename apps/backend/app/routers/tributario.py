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
