"""Router Almoxarifado — Controle de Estoque Municipal.

Cobre:
  - Cadastro de itens/materiais
  - Entradas de estoque (compras, doações, devoluções)
  - Saídas / requisições por departamento
  - Saldo atual por item
  - Histórico de movimentações com filtros e exportação CSV
"""

import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Department, ItemAlmoxarifado, MovimentacaoEstoque, RoleEnum, User
from ..schemas import (
    ItemAlmoxarifadoCreate,
    ItemAlmoxarifadoOut,
    ItemAlmoxarifadoUpdate,
    MovimentacaoCreate,
    MovimentacaoOut,
)

router = APIRouter(prefix="/almoxarifado", tags=["almoxarifado"])

_TIPOS_VALIDOS = {"entrada", "saida"}


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


# ── Itens / Materiais ─────────────────────────────────────────────────────────

@router.get("/itens", response_model=None)
def list_itens(
    search: str | None = None,
    categoria: str | None = None,
    ativo: bool | None = None,
    abaixo_minimo: bool | None = None,
    export: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista itens do almoxarifado com filtros e exportação CSV."""
    q = db.query(ItemAlmoxarifado)
    if search:
        q = q.filter(
            ItemAlmoxarifado.descricao.ilike(f"%{search}%")
            | ItemAlmoxarifado.codigo.ilike(f"%{search}%")
        )
    if categoria:
        q = q.filter(ItemAlmoxarifado.categoria == categoria)
    if ativo is not None:
        q = q.filter(ItemAlmoxarifado.ativo == ativo)
    if abaixo_minimo:
        q = q.filter(ItemAlmoxarifado.estoque_atual < ItemAlmoxarifado.estoque_minimo)

    if export == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "codigo", "descricao", "unidade", "categoria", "localizacao",
                          "estoque_minimo", "estoque_atual", "valor_unitario", "ativo"])
        for it in q.order_by(ItemAlmoxarifado.codigo).all():
            writer.writerow([it.id, it.codigo, it.descricao, it.unidade, it.categoria,
                              it.localizacao, it.estoque_minimo, it.estoque_atual,
                              it.valor_unitario, it.ativo])
        return Response(content=buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=itens_almoxarifado.csv"})

    q = q.order_by(ItemAlmoxarifado.codigo)
    return _paginate(q, page, size)


@router.get("/itens/{item_id}", response_model=ItemAlmoxarifadoOut)
def get_item(item_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    item = db.get(ItemAlmoxarifado, item_id)
    if not item:
        raise HTTPException(404, "Item não encontrado.")
    return item


@router.post("/itens", response_model=ItemAlmoxarifadoOut, status_code=201)
def create_item(
    data: ItemAlmoxarifadoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    if db.query(ItemAlmoxarifado).filter_by(codigo=data.codigo).first():
        raise HTTPException(400, f"Código '{data.codigo}' já cadastrado.")
    item = ItemAlmoxarifado(**data.model_dump())
    db.add(item)
    db.flush()
    write_audit(db, user_id=current_user.id, entity="itens_almoxarifado", entity_id=str(item.id),
                action="create", after_data=data.model_dump())
    db.commit()
    db.refresh(item)
    return item


@router.put("/itens/{item_id}", response_model=ItemAlmoxarifadoOut)
def update_item(
    item_id: int,
    data: ItemAlmoxarifadoUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    item = db.get(ItemAlmoxarifado, item_id)
    if not item:
        raise HTTPException(404, "Item não encontrado.")
    before = {k: getattr(item, k) for k in data.model_dump(exclude_none=True)}
    for k, v in data.model_dump(exclude_none=True).items():
        setattr(item, k, v)
    db.flush()
    write_audit(db, user_id=current_user.id, entity="itens_almoxarifado", entity_id=str(item.id),
                action="update", before_data=before, after_data=data.model_dump(exclude_none=True))
    db.commit()
    db.refresh(item)
    return item


@router.delete("/itens/{item_id}", status_code=204)
def delete_item(
    item_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin)),
):
    item = db.get(ItemAlmoxarifado, item_id)
    if not item:
        raise HTTPException(404, "Item não encontrado.")
    if db.query(MovimentacaoEstoque).filter_by(item_id=item_id).count() > 0:
        raise HTTPException(409, "Item possui movimentações — inative-o em vez de excluir.")
    db.delete(item)
    db.commit()
    write_audit(db, user_id=current_user.id, entity="itens_almoxarifado", entity_id=str(item_id),
                action="delete")


# ── Movimentações (entradas e saídas) ─────────────────────────────────────────

@router.post("/movimentacoes", response_model=MovimentacaoOut, status_code=201)
def registrar_movimentacao(
    data: MovimentacaoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Registra entrada ou saída de estoque.

    - Atualiza `estoque_atual` do item atomicamente.
    - Saída é rejeitada se não houver saldo suficiente.
    - Registra `saldo_pos` na movimentação para rastreabilidade histórica.
    - Valor total = quantidade × valor_unitario.
    """
    if data.tipo not in _TIPOS_VALIDOS:
        raise HTTPException(422, f"tipo deve ser 'entrada' ou 'saida'; recebido: '{data.tipo}'")

    item = db.get(ItemAlmoxarifado, data.item_id)
    if not item:
        raise HTTPException(404, "Item não encontrado.")
    if not item.ativo:
        raise HTTPException(422, "Item inativo — reative-o antes de movimentar.")

    if data.departamento_id is not None:
        if not db.get(Department, data.departamento_id):
            raise HTTPException(404, "Departamento não encontrado.")

    if data.quantidade <= 0:
        raise HTTPException(422, "Quantidade deve ser positiva.")

    if data.tipo == "saida" and item.estoque_atual < data.quantidade:
        raise HTTPException(422,
            f"Saldo insuficiente: disponível={item.estoque_atual}, solicitado={data.quantidade}.")

    valor_total = round(data.quantidade * data.valor_unitario, 2)

    # Atualiza estoque
    if data.tipo == "entrada":
        item.estoque_atual = round(item.estoque_atual + data.quantidade, 4)
        # Atualiza custo médio ponderado
        if data.valor_unitario > 0:
            total_valor = item.estoque_atual * item.valor_unitario + valor_total
            item.valor_unitario = round(total_valor / (item.estoque_atual or 1), 4)
    else:
        item.estoque_atual = round(item.estoque_atual - data.quantidade, 4)

    mov = MovimentacaoEstoque(
        item_id=data.item_id,
        tipo=data.tipo,
        quantidade=data.quantidade,
        valor_unitario=data.valor_unitario,
        valor_total=valor_total,
        data_movimentacao=data.data_movimentacao,
        departamento_id=data.departamento_id,
        responsavel_id=current_user.id,
        documento_ref=data.documento_ref,
        observacoes=data.observacoes,
        saldo_pos=item.estoque_atual,
    )
    db.add(mov)
    db.flush()
    write_audit(db, user_id=current_user.id, entity="movimentacoes_estoque", entity_id=str(mov.id),
                action=data.tipo, after_data={k: str(v) if isinstance(v, date) else v for k, v in data.model_dump().items()})
    db.commit()
    db.refresh(mov)
    return mov


@router.get("/movimentacoes", response_model=None)
def list_movimentacoes(
    item_id: int | None = None,
    tipo: str | None = None,
    departamento_id: int | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    export: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Histórico de movimentações com filtros e exportação CSV."""
    q = db.query(MovimentacaoEstoque)
    if item_id:
        q = q.filter(MovimentacaoEstoque.item_id == item_id)
    if tipo:
        q = q.filter(MovimentacaoEstoque.tipo == tipo)
    if departamento_id:
        q = q.filter(MovimentacaoEstoque.departamento_id == departamento_id)
    if data_inicio:
        q = q.filter(MovimentacaoEstoque.data_movimentacao >= data_inicio)
    if data_fim:
        q = q.filter(MovimentacaoEstoque.data_movimentacao <= data_fim)

    if export == "csv":
        buf = StringIO()
        writer = csv.writer(buf)
        writer.writerow(["id", "item_id", "tipo", "quantidade", "valor_unitario", "valor_total",
                          "data", "departamento_id", "responsavel_id", "documento_ref", "saldo_pos"])
        for m in q.order_by(MovimentacaoEstoque.id.desc()).all():
            writer.writerow([m.id, m.item_id, m.tipo, m.quantidade, m.valor_unitario, m.valor_total,
                              m.data_movimentacao, m.departamento_id, m.responsavel_id,
                              m.documento_ref, m.saldo_pos])
        return Response(content=buf.getvalue(), media_type="text/csv",
                        headers={"Content-Disposition": "attachment; filename=movimentacoes.csv"})

    q = q.order_by(MovimentacaoEstoque.id.desc())
    return _paginate(q, page, size)


@router.get("/movimentacoes/{mov_id}", response_model=MovimentacaoOut)
def get_movimentacao(mov_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    mov = db.get(MovimentacaoEstoque, mov_id)
    if not mov:
        raise HTTPException(404, "Movimentação não encontrada.")
    return mov


# ── Saldo e Dashboard ─────────────────────────────────────────────────────────

@router.get("/saldo/{item_id}")
def saldo_item(item_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Retorna saldo atual, valor de estoque e alertas do item."""
    item = db.get(ItemAlmoxarifado, item_id)
    if not item:
        raise HTTPException(404, "Item não encontrado.")
    return {
        "item_id": item.id,
        "codigo": item.codigo,
        "descricao": item.descricao,
        "unidade": item.unidade,
        "estoque_atual": item.estoque_atual,
        "estoque_minimo": item.estoque_minimo,
        "valor_unitario": item.valor_unitario,
        "valor_estoque": round(item.estoque_atual * item.valor_unitario, 2),
        "abaixo_minimo": item.estoque_atual < item.estoque_minimo,
    }


@router.get("/dashboard")
def dashboard(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Resumo quantitativo do almoxarifado."""
    from sqlalchemy import func

    total_itens = db.query(func.count(ItemAlmoxarifado.id)).filter(ItemAlmoxarifado.ativo == True).scalar() or 0
    itens_abaixo_minimo = db.query(func.count(ItemAlmoxarifado.id)).filter(
        ItemAlmoxarifado.ativo == True,
        ItemAlmoxarifado.estoque_atual < ItemAlmoxarifado.estoque_minimo,
    ).scalar() or 0
    valor_total_estoque = db.query(
        func.sum(ItemAlmoxarifado.estoque_atual * ItemAlmoxarifado.valor_unitario)
    ).filter(ItemAlmoxarifado.ativo == True).scalar() or 0.0

    entradas_mes = db.query(func.count(MovimentacaoEstoque.id)).filter(
        MovimentacaoEstoque.tipo == "entrada",
        func.strftime("%Y-%m", MovimentacaoEstoque.data_movimentacao) == func.strftime("%Y-%m", "now"),
    ).scalar() or 0
    saidas_mes = db.query(func.count(MovimentacaoEstoque.id)).filter(
        MovimentacaoEstoque.tipo == "saida",
        func.strftime("%Y-%m", MovimentacaoEstoque.data_movimentacao) == func.strftime("%Y-%m", "now"),
    ).scalar() or 0

    return {
        "total_itens_ativos": total_itens,
        "itens_abaixo_minimo": itens_abaixo_minimo,
        "valor_total_estoque": round(valor_total_estoque, 2),
        "entradas_no_mes": entradas_mes,
        "saidas_no_mes": saidas_mes,
    }
