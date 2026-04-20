"""Router Almoxarifado — Controle de Estoque Municipal.

Cobre:
  - Cadastro de itens/materiais
  - Entradas de estoque (compras, doações, devoluções)
  - Saídas / requisições por departamento
  - Saldo atual por item
  - Histórico de movimentações com filtros e exportação CSV
  - Recebimento de material vinculado a processo/contrato de compras
  - Alertas de estoque mínimo e requisições de compra automáticas
"""

import csv
from datetime import date
from io import StringIO

from fastapi import APIRouter, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import (
    AlertaEstoqueMinimo,
    Commitment,
    Contract,
    Department,
    ItemAlmoxarifado,
    ItemRecebimento,
    MovimentacaoEstoque,
    ProcurementProcess,
    RecebimentoMaterial,
    RequisicaoCompra,
    RoleEnum,
    User,
    Vendor,
)
from ..schemas import (
    AlertaOut,
    ItemAlmoxarifadoCreate,
    ItemAlmoxarifadoOut,
    ItemAlmoxarifadoUpdate,
    MovimentacaoCreate,
    MovimentacaoOut,
    RecebimentoCreate,
    RecebimentoOut,
    RequisicaoCompraCreate,
    RequisicaoCompraOut,
    RequisicaoCompraVincular,
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

    # Auto-gerar alerta de estoque mínimo quando saída deixa saldo abaixo do mínimo
    if data.tipo == "saida" and item.estoque_minimo > 0 and item.estoque_atual < item.estoque_minimo:
        alerta_aberto = db.query(AlertaEstoqueMinimo).filter(
            AlertaEstoqueMinimo.item_id == item.id,
            AlertaEstoqueMinimo.status == "aberto",
        ).first()
        if not alerta_aberto:
            alerta = AlertaEstoqueMinimo(
                item_id=item.id,
                movimentacao_id=mov.id,
                saldo_no_momento=item.estoque_atual,
                estoque_minimo=item.estoque_minimo,
                status="aberto",
            )
            db.add(alerta)
            db.flush()
            write_audit(db, user_id=current_user.id, entity="alertas_estoque_minimo",
                        entity_id=str(alerta.id), action="create",
                        after_data={"item_id": item.id, "saldo": item.estoque_atual,
                                    "minimo": item.estoque_minimo})

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


# ── Recebimentos de Material (Integração Compras ↔ Almoxarifado) ──────────────

@router.post("/recebimentos", response_model=RecebimentoOut, status_code=201)
def criar_recebimento(
    data: RecebimentoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Registra recebimento físico de material vinculado a processo/contrato.

    O recebimento fica com status='pendente' até ser confirmado.
    Apenas ao confirmar (`POST /recebimentos/{id}/confirmar`) o estoque é atualizado.
    """
    if not db.get(ProcurementProcess, data.processo_id):
        raise HTTPException(404, "Processo de compra não encontrado.")
    if data.contrato_id and not db.get(Contract, data.contrato_id):
        raise HTTPException(404, "Contrato não encontrado.")
    if data.vendor_id and not db.get(Vendor, data.vendor_id):
        raise HTTPException(404, "Fornecedor não encontrado.")
    if data.commitment_id and not db.get(Commitment, data.commitment_id):
        raise HTTPException(404, "Empenho não encontrado.")
    if not data.itens:
        raise HTTPException(422, "O recebimento deve ter ao menos um item.")

    for i, it in enumerate(data.itens):
        item_alm = db.get(ItemAlmoxarifado, it.item_almoxarifado_id)
        if not item_alm:
            raise HTTPException(404, f"Item almoxarifado id={it.item_almoxarifado_id} não encontrado.")
        if not item_alm.ativo:
            raise HTTPException(422, f"Item '{item_alm.codigo}' está inativo.")
        if it.quantidade_recebida <= 0:
            raise HTTPException(422, f"Quantidade do item #{i+1} deve ser positiva.")

    rec = RecebimentoMaterial(
        processo_id=data.processo_id,
        contrato_id=data.contrato_id,
        vendor_id=data.vendor_id,
        commitment_id=data.commitment_id,
        nota_fiscal=data.nota_fiscal,
        data_recebimento=data.data_recebimento,
        status="pendente",
        observacoes=data.observacoes,
        responsavel_id=current_user.id,
    )
    db.add(rec)
    db.flush()

    for it in data.itens:
        vt = round(it.quantidade_recebida * it.valor_unitario, 2)
        ir = ItemRecebimento(
            recebimento_id=rec.id,
            item_almoxarifado_id=it.item_almoxarifado_id,
            quantidade_recebida=it.quantidade_recebida,
            valor_unitario=it.valor_unitario,
            valor_total=vt,
        )
        db.add(ir)

    db.flush()
    write_audit(db, user_id=current_user.id, entity="recebimentos_material", entity_id=str(rec.id),
                action="create", after_data={
                    "processo_id": data.processo_id, "nota_fiscal": data.nota_fiscal,
                    "data_recebimento": str(data.data_recebimento), "status": "pendente",
                    "n_itens": len(data.itens),
                })
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/recebimentos/{rec_id}/confirmar", response_model=RecebimentoOut)
def confirmar_recebimento(
    rec_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Confirma o recebimento, gerando automaticamente entradas de estoque para cada item.

    Regras:
    - Status deve ser 'pendente'.
    - Para cada ItemRecebimento cria um MovimentacaoEstoque (entrada).
    - Atualiza estoque_atual e valor_unitario (custo médio ponderado) do ItemAlmoxarifado.
    - Registra processo_id, contrato_id e recebimento_id na movimentação para rastreabilidade.
    """
    rec = db.get(RecebimentoMaterial, rec_id)
    if not rec:
        raise HTTPException(404, "Recebimento não encontrado.")
    if rec.status != "pendente":
        raise HTTPException(422, f"Recebimento já está '{rec.status}' — não pode ser confirmado novamente.")

    processo = db.get(ProcurementProcess, rec.processo_id)
    obs_base = f"Recebimento #{rec.id} — Processo {processo.number if processo else rec.processo_id}"
    if rec.nota_fiscal:
        obs_base += f" — NF {rec.nota_fiscal}"

    for ir in rec.itens:
        item = db.get(ItemAlmoxarifado, ir.item_almoxarifado_id)
        if not item:
            raise HTTPException(404, f"Item almoxarifado id={ir.item_almoxarifado_id} não encontrado.")
        if not item.ativo:
            raise HTTPException(422, f"Item '{item.codigo}' foi inativado — confirme após reativar.")

        valor_total = round(ir.quantidade_recebida * ir.valor_unitario, 2)

        # Atualiza estoque e custo médio ponderado
        novo_saldo = round(item.estoque_atual + ir.quantidade_recebida, 4)
        if ir.valor_unitario > 0:
            total_custo = (item.estoque_atual * item.valor_unitario) + valor_total
            item.valor_unitario = round(total_custo / novo_saldo, 4)
        item.estoque_atual = novo_saldo

        mov = MovimentacaoEstoque(
            item_id=item.id,
            tipo="entrada",
            quantidade=ir.quantidade_recebida,
            valor_unitario=ir.valor_unitario,
            valor_total=valor_total,
            data_movimentacao=rec.data_recebimento,
            responsavel_id=current_user.id,
            documento_ref=rec.nota_fiscal or f"REC-{rec.id}",
            observacoes=obs_base,
            saldo_pos=novo_saldo,
            processo_id=rec.processo_id,
            contrato_id=rec.contrato_id,
            recebimento_id=rec.id,
        )
        db.add(mov)
        db.flush()
        ir.movimentacao_id = mov.id
        ir.valor_total = valor_total

    rec.status = "conferido"
    db.flush()
    write_audit(db, user_id=current_user.id, entity="recebimentos_material", entity_id=str(rec.id),
                action="confirmar", after_data={"status": "conferido", "n_itens": len(rec.itens)})
    db.commit()
    db.refresh(rec)
    return rec


@router.post("/recebimentos/{rec_id}/recusar", response_model=RecebimentoOut)
def recusar_recebimento(
    rec_id: int,
    motivo: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Marca o recebimento como recusado (material devolvido ao fornecedor)."""
    rec = db.get(RecebimentoMaterial, rec_id)
    if not rec:
        raise HTTPException(404, "Recebimento não encontrado.")
    if rec.status != "pendente":
        raise HTTPException(422, f"Recebimento já está '{rec.status}'.")
    rec.status = "recusado"
    if motivo:
        rec.observacoes = (rec.observacoes + f"\n[Recusa] {motivo}").strip()
    db.flush()
    write_audit(db, user_id=current_user.id, entity="recebimentos_material", entity_id=str(rec.id),
                action="recusar", after_data={"status": "recusado", "motivo": motivo})
    db.commit()
    db.refresh(rec)
    return rec


@router.get("/recebimentos", response_model=None)
def list_recebimentos(
    processo_id: int | None = None,
    contrato_id: int | None = None,
    vendor_id: int | None = None,
    status: str | None = None,
    data_inicio: date | None = None,
    data_fim: date | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista recebimentos com filtros e paginação."""
    q = db.query(RecebimentoMaterial)
    if processo_id:
        q = q.filter(RecebimentoMaterial.processo_id == processo_id)
    if contrato_id:
        q = q.filter(RecebimentoMaterial.contrato_id == contrato_id)
    if vendor_id:
        q = q.filter(RecebimentoMaterial.vendor_id == vendor_id)
    if status:
        q = q.filter(RecebimentoMaterial.status == status)
    if data_inicio:
        q = q.filter(RecebimentoMaterial.data_recebimento >= data_inicio)
    if data_fim:
        q = q.filter(RecebimentoMaterial.data_recebimento <= data_fim)
    q = q.order_by(RecebimentoMaterial.id.desc())
    return _paginate(q, page, size)


@router.get("/recebimentos/{rec_id}", response_model=RecebimentoOut)
def get_recebimento(rec_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    rec = db.get(RecebimentoMaterial, rec_id)
    if not rec:
        raise HTTPException(404, "Recebimento não encontrado.")
    return rec


# ── Alertas de Estoque Mínimo ─────────────────────────────────────────────────

@router.get("/alertas", response_model=None)
def list_alertas(
    item_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista alertas de estoque mínimo com filtros."""
    q = db.query(AlertaEstoqueMinimo)
    if item_id:
        q = q.filter(AlertaEstoqueMinimo.item_id == item_id)
    if status:
        q = q.filter(AlertaEstoqueMinimo.status == status)
    q = q.order_by(AlertaEstoqueMinimo.id.desc())
    return _paginate(q, page, size)


@router.get("/alertas/{alerta_id}", response_model=AlertaOut)
def get_alerta(alerta_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    alerta = db.get(AlertaEstoqueMinimo, alerta_id)
    if not alerta:
        raise HTTPException(404, "Alerta não encontrado.")
    return alerta


@router.post("/alertas/{alerta_id}/resolver", response_model=AlertaOut)
def resolver_alerta(
    alerta_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Marca alerta como resolvido (estoque reabastecido manualmente ou via recebimento)."""
    from ..models import utc_now
    alerta = db.get(AlertaEstoqueMinimo, alerta_id)
    if not alerta:
        raise HTTPException(404, "Alerta não encontrado.")
    if alerta.status == "resolvido":
        raise HTTPException(422, "Alerta já está resolvido.")
    alerta.status = "resolvido"
    alerta.resolvido_em = utc_now()
    write_audit(db, user_id=current_user.id, entity="alertas_estoque_minimo",
                entity_id=str(alerta.id), action="resolver", after_data={"status": "resolvido"})
    db.commit()
    db.refresh(alerta)
    return alerta


# ── Requisições de Compra ─────────────────────────────────────────────────────

@router.post("/requisicoes", response_model=RequisicaoCompraOut, status_code=201)
def criar_requisicao(
    data: RequisicaoCompraCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Cria uma requisição/minuta de compra, opcionalmente vinculada a um alerta de estoque mínimo."""
    item = db.get(ItemAlmoxarifado, data.item_id)
    if not item:
        raise HTTPException(404, "Item não encontrado.")
    if not item.ativo:
        raise HTTPException(422, "Item inativo.")
    if data.departamento_id and not db.get(Department, data.departamento_id):
        raise HTTPException(404, "Departamento não encontrado.")
    if data.alerta_id:
        alerta = db.get(AlertaEstoqueMinimo, data.alerta_id)
        if not alerta:
            raise HTTPException(404, "Alerta não encontrado.")
        if alerta.item_id != data.item_id:
            raise HTTPException(422, "Alerta pertence a item diferente.")
        # Marca alerta como em processo
        if alerta.status == "aberto":
            alerta.status = "em_processo"
    if data.quantidade_sugerida <= 0:
        raise HTTPException(422, "Quantidade sugerida deve ser positiva.")

    req = RequisicaoCompra(
        item_id=data.item_id,
        departamento_id=data.departamento_id,
        alerta_id=data.alerta_id,
        quantidade_sugerida=data.quantidade_sugerida,
        justificativa=data.justificativa,
        status="rascunho",
        solicitante_id=current_user.id,
    )
    db.add(req)
    db.flush()
    write_audit(db, user_id=current_user.id, entity="requisicoes_compra",
                entity_id=str(req.id), action="create",
                after_data={"item_id": data.item_id, "quantidade_sugerida": data.quantidade_sugerida,
                            "alerta_id": data.alerta_id})
    db.commit()
    db.refresh(req)
    return req


@router.post("/requisicoes/{req_id}/aprovar", response_model=RequisicaoCompraOut)
def aprovar_requisicao(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Aprova uma requisição de compra (muda status rascunho → aprovada)."""
    req = db.get(RequisicaoCompra, req_id)
    if not req:
        raise HTTPException(404, "Requisição não encontrada.")
    if req.status != "rascunho":
        raise HTTPException(422, f"Requisição já está '{req.status}'.")
    req.status = "aprovada"
    write_audit(db, user_id=current_user.id, entity="requisicoes_compra",
                entity_id=str(req.id), action="aprovar", after_data={"status": "aprovada"})
    db.commit()
    db.refresh(req)
    return req


@router.post("/requisicoes/{req_id}/cancelar", response_model=RequisicaoCompraOut)
def cancelar_requisicao(
    req_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Cancela uma requisição (rascunho ou aprovada)."""
    req = db.get(RequisicaoCompra, req_id)
    if not req:
        raise HTTPException(404, "Requisição não encontrada.")
    if req.status in ("cancelada", "vinculada"):
        raise HTTPException(422, f"Requisição já está '{req.status}'.")
    req.status = "cancelada"
    # Se havia alerta em_processo e não há outra requisição ativa, reabre o alerta
    if req.alerta_id:
        outras = db.query(RequisicaoCompra).filter(
            RequisicaoCompra.alerta_id == req.alerta_id,
            RequisicaoCompra.id != req.id,
            RequisicaoCompra.status.notin_(["cancelada"]),
        ).first()
        if not outras:
            alerta = db.get(AlertaEstoqueMinimo, req.alerta_id)
            if alerta and alerta.status == "em_processo":
                alerta.status = "aberto"
    write_audit(db, user_id=current_user.id, entity="requisicoes_compra",
                entity_id=str(req.id), action="cancelar", after_data={"status": "cancelada"})
    db.commit()
    db.refresh(req)
    return req


@router.post("/requisicoes/{req_id}/vincular-processo", response_model=RequisicaoCompraOut)
def vincular_processo(
    req_id: int,
    payload: RequisicaoCompraVincular,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_roles(RoleEnum.admin, RoleEnum.procurement)),
):
    """Vincula uma requisição aprovada a um processo licitatório existente."""
    req = db.get(RequisicaoCompra, req_id)
    if not req:
        raise HTTPException(404, "Requisição não encontrada.")
    if req.status not in ("rascunho", "aprovada"):
        raise HTTPException(422, f"Requisição não pode ser vinculada no status '{req.status}'.")
    if not db.get(ProcurementProcess, payload.processo_id):
        raise HTTPException(404, "Processo de compra não encontrado.")
    req.processo_id = payload.processo_id
    req.status = "vinculada"
    # Marcar alerta como resolvido quando requisição é vinculada a processo
    if req.alerta_id:
        from ..models import utc_now
        alerta = db.get(AlertaEstoqueMinimo, req.alerta_id)
        if alerta and alerta.status in ("aberto", "em_processo"):
            alerta.status = "resolvido"
            alerta.resolvido_em = utc_now()
    write_audit(db, user_id=current_user.id, entity="requisicoes_compra",
                entity_id=str(req.id), action="vincular",
                after_data={"processo_id": payload.processo_id, "status": "vinculada"})
    db.commit()
    db.refresh(req)
    return req


@router.get("/requisicoes", response_model=None)
def list_requisicoes(
    item_id: int | None = None,
    departamento_id: int | None = None,
    status: str | None = None,
    alerta_id: int | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    """Lista requisições de compra com filtros e paginação."""
    q = db.query(RequisicaoCompra)
    if item_id:
        q = q.filter(RequisicaoCompra.item_id == item_id)
    if departamento_id:
        q = q.filter(RequisicaoCompra.departamento_id == departamento_id)
    if status:
        q = q.filter(RequisicaoCompra.status == status)
    if alerta_id:
        q = q.filter(RequisicaoCompra.alerta_id == alerta_id)
    q = q.order_by(RequisicaoCompra.id.desc())
    return _paginate(q, page, size)


@router.get("/requisicoes/{req_id}", response_model=RequisicaoCompraOut)
def get_requisicao(req_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    req = db.get(RequisicaoCompra, req_id)
    if not req:
        raise HTTPException(404, "Requisição não encontrada.")
    return req
