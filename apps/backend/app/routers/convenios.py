"""Router de Convênios."""

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import Convenio, ConvenioDesembolso, RoleEnum, User
from ..schemas import (
    ConvenioCreate,
    ConvenioDesembolsoCreate,
    ConvenioDesembolsoOut,
    ConvenioOut,
    ConvenioUpdate,
)

router = APIRouter(prefix="/convenios", tags=["convenios"])


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


@router.get("")
def list_convenios(
    status: str | None = None,
    tipo: str | None = None,
    search: str | None = None,
    vencendo: bool | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(Convenio)
    if status:
        q = q.filter(Convenio.status == status)
    if tipo:
        q = q.filter(Convenio.tipo == tipo)
    if search:
        q = q.filter(
            Convenio.objeto.ilike(f"%{search}%")
            | Convenio.concedente.ilike(f"%{search}%")
            | Convenio.numero.ilike(f"%{search}%")
        )
    if vencendo:
        from datetime import timedelta
        limit_date = date.today() + timedelta(days=90)
        q = q.filter(Convenio.data_fim <= limit_date, Convenio.status == "vigente")
    return _paginate(q.order_by(Convenio.created_at.desc()), page, size)


@router.get("/vencendo")
def vencendo_em_90_dias(db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    from datetime import timedelta
    limit_date = date.today() + timedelta(days=90)
    return db.query(Convenio).filter(
        Convenio.data_fim <= limit_date,
        Convenio.status == "vigente",
    ).order_by(Convenio.data_fim).all()


@router.get("/{convenio_id}", response_model=ConvenioOut)
def get_convenio(convenio_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(Convenio, convenio_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    return obj


@router.post("", response_model=ConvenioOut)
def create_convenio(
    payload: ConvenioCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    if db.query(Convenio).filter(Convenio.numero == payload.numero).first():
        raise HTTPException(status_code=409, detail="Número de convênio já existe")
    obj = Convenio(**payload.model_dump())
    db.add(obj)
    db.flush()
    write_audit(
        db, user_id=current.id, action="create",
        entity="convenios", entity_id=str(obj.id),
        after_data={"numero": obj.numero, "objeto": obj.objeto, "valor_total": obj.valor_total},
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.patch("/{convenio_id}", response_model=ConvenioOut)
def update_convenio(
    convenio_id: int,
    payload: ConvenioUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    obj = db.get(Convenio, convenio_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    before = {"status": obj.status, "valor_total": obj.valor_total}
    for field, value in payload.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    write_audit(
        db, user_id=current.id, action="update",
        entity="convenios", entity_id=str(obj.id),
        before_data=before, after_data=payload.model_dump(exclude_none=True, mode="json"),
    )
    db.commit()
    db.refresh(obj)
    return obj


@router.post("/{convenio_id}/desembolsos", response_model=ConvenioDesembolsoOut)
def add_desembolso(
    convenio_id: int,
    payload: ConvenioDesembolsoCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    obj = db.get(Convenio, convenio_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    desembolso = ConvenioDesembolso(convenio_id=convenio_id, **payload.model_dump())
    db.add(desembolso)
    db.flush()
    write_audit(
        db, user_id=current.id, action="create",
        entity="convenio_desembolsos", entity_id=str(desembolso.id),
        after_data={"convenio_id": convenio_id, "parcela": payload.numero_parcela, "valor": payload.valor},
    )
    db.commit()
    db.refresh(desembolso)
    return desembolso


@router.get("/{convenio_id}/desembolsos", response_model=list[ConvenioDesembolsoOut])
def list_desembolsos(convenio_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    obj = db.get(Convenio, convenio_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    return db.query(ConvenioDesembolso).filter(
        ConvenioDesembolso.convenio_id == convenio_id
    ).order_by(ConvenioDesembolso.numero_parcela).all()


@router.patch("/{convenio_id}/desembolsos/{desembolso_id}", response_model=ConvenioDesembolsoOut)
def update_desembolso(
    convenio_id: int,
    desembolso_id: int,
    data_efetiva: date,
    status: str = "recebido",
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    """Registra o recebimento efetivo de um desembolso."""
    desembolso = db.get(ConvenioDesembolso, desembolso_id)
    if not desembolso or desembolso.convenio_id != convenio_id:
        raise HTTPException(status_code=404, detail="Desembolso não encontrado")
    desembolso.data_efetiva = data_efetiva
    desembolso.status = status
    write_audit(
        db, user_id=current.id, action="update",
        entity="convenio_desembolsos", entity_id=str(desembolso.id),
        after_data={"data_efetiva": str(data_efetiva), "status": status},
    )
    db.commit()
    db.refresh(desembolso)
    return desembolso


@router.get("/{convenio_id}/saldo")
def saldo_convenio(convenio_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Calcula o saldo recebido vs. total e contrapartida pendente."""
    obj = db.get(Convenio, convenio_id)
    if not obj:
        raise HTTPException(status_code=404, detail="Convênio não encontrado")
    desembolsos = db.query(ConvenioDesembolso).filter(
        ConvenioDesembolso.convenio_id == convenio_id
    ).all()
    total_previsto = sum(d.valor for d in desembolsos)
    total_recebido = sum(d.valor for d in desembolsos if d.status == "recebido")
    pendente = total_previsto - total_recebido
    return {
        "convenio_id": convenio_id,
        "numero": obj.numero,
        "valor_total": obj.valor_total,
        "contrapartida": obj.contrapartida,
        "total_previsto_parcelas": total_previsto,
        "total_recebido": total_recebido,
        "saldo_pendente": pendente,
        "percentual_recebido": round(total_recebido / total_previsto * 100, 2) if total_previsto else 0.0,
    }
