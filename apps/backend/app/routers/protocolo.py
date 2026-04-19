"""Router de Protocolo e Processos Administrativos."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Protocolo, TramitacaoProtocolo, RoleEnum, User
from ..schemas import (
    ProtocoloCreate,
    ProtocoloOut,
    ProtocoloUpdate,
    TramitacaoCreate,
    TramitacaoOut,
)

router = APIRouter(prefix="/protocolo", tags=["protocolo"])

# Status válidos para transições
VALID_TRANSITIONS: dict[str, list[str]] = {
    "protocolado":     ["em_tramitacao", "deferido", "indeferido", "arquivado"],
    "em_tramitacao":   ["deferido", "indeferido", "arquivado"],
    "deferido":        ["arquivado"],
    "indeferido":      ["arquivado"],
    "arquivado":       [],
}


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("/protocolos")
def list_protocolos(
    status: str | None = None,
    tipo: str | None = None,
    prioridade: str | None = None,
    search: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Protocolo)
    if status:
        q = q.filter(Protocolo.status == status)
    if tipo:
        q = q.filter(Protocolo.tipo == tipo)
    if prioridade:
        q = q.filter(Protocolo.prioridade == prioridade)
    if search:
        q = q.filter(
            Protocolo.assunto.ilike(f"%{search}%")
            | Protocolo.interessado.ilike(f"%{search}%")
            | Protocolo.numero.ilike(f"%{search}%")
        )
    return _paginate(q.order_by(Protocolo.created_at.desc()), page, size)


@router.get("/protocolos/{protocolo_id}", response_model=ProtocoloOut)
def get_protocolo(protocolo_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    return obj


@router.post("/protocolos", response_model=ProtocoloOut)
def create_protocolo(
    payload: ProtocoloCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    if db.query(Protocolo).filter(Protocolo.numero == payload.numero).first():
        raise HTTPException(status_code=409, detail="Número de protocolo já existe")
    obj = Protocolo(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(
        db, user_id=current.id, action="create",
        entity="protocolos", entity_id=str(obj.id),
        after_data={"numero": obj.numero, "tipo": obj.tipo, "assunto": obj.assunto},
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/protocolos/{protocolo_id}", response_model=ProtocoloOut)
def update_protocolo(
    protocolo_id: int,
    payload: ProtocoloUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    before = {"status": obj.status, "assunto": obj.assunto}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    write_audit(
        db, user_id=current.id, action="update",
        entity="protocolos", entity_id=str(obj.id),
        before_data=before, after_data=payload.model_dump(exclude_none=True),
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/protocolos/{protocolo_id}/tramitar", response_model=TramitacaoOut)
def tramitar_protocolo(
    protocolo_id: int,
    payload: TramitacaoCreate,
    db: Session = Depends(get_db),
    current: User = Depends(get_current_user),
):
    """Tramita o protocolo para um novo departamento, registrando o despacho."""
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")

    # Calcula o novo status com base na ação
    ACAO_PARA_STATUS = {
        "encaminhado": "em_tramitacao",
        "deferido":    "deferido",
        "indeferido":  "indeferido",
        "arquivado":   "arquivado",
        "devolvido":   "em_tramitacao",
    }
    novo_status = ACAO_PARA_STATUS.get(payload.acao)
    if novo_status:
        allowed = VALID_TRANSITIONS.get(obj.status, [])
        if novo_status not in allowed and novo_status != obj.status:
            raise HTTPException(
                status_code=422,
                detail=f"Transição inválida: '{obj.status}' → '{novo_status}' (ação '{payload.acao}'). "
                       f"Transições válidas: {allowed}",
            )

    tram = TramitacaoProtocolo(
        protocolo_id=protocolo_id,
        de_department_id=obj.destino_department_id,
        para_department_id=payload.para_department_id,
        responsavel_id=current.id,
        acao=payload.acao,
        despacho=payload.despacho,
    )
    db.add(tram)

    # Atualiza status e destino do protocolo
    if novo_status:
        obj.status = novo_status
    obj.destino_department_id = payload.para_department_id

    db.flush()
    write_audit(
        db, user_id=current.id, action="update",
        entity="protocolos", entity_id=str(obj.id),
        after_data={"acao": payload.acao, "para_department": payload.para_department_id, "novo_status": obj.status},
    )
    db.commit()
    db.refresh(tram)
    return tram


@router.get("/protocolos/{protocolo_id}/tramitacoes", response_model=list[TramitacaoOut])
def list_tramitacoes(
    protocolo_id: int,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    obj = db.get(Protocolo, protocolo_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Protocolo não encontrado")
    return db.query(TramitacaoProtocolo).filter(
        TramitacaoProtocolo.protocolo_id == protocolo_id
    ).order_by(TramitacaoProtocolo.created_at).all()


@router.get("/estatisticas")
def estatisticas(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Resumo quantitativo de protocolos por status."""
    from sqlalchemy import func
    rows = (
        db.query(Protocolo.status, func.count(Protocolo.id))
        .group_by(Protocolo.status)
        .all()
    )
    return {status: count for status, count in rows}
