"""Router de planejamento orçamentário: PPA, LDO e LOA."""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from ..audit import write_audit
from ..db import get_db
from ..deps import get_current_user, require_roles
from ..models import LDO, LOA, PPA, LDOGoal, LOAItem, PPAProgram, RoleEnum, User
from ..schemas import (
    LDOCreate,
    LDOGoalCreate,
    LDOGoalOut,
    LDOOut,
    LDOUpdate,
    LOACreate,
    LOAItemCreate,
    LOAItemOut,
    LOAItemUpdate,
    LOAOut,
    LOAUpdate,
    PPACreate,
    PPAOut,
    PPAProgramCreate,
    PPAProgramOut,
    PPAUpdate,
)

router = APIRouter(prefix="/budget", tags=["budget"])


def _paginate(query, page: int, size: int):
    total = query.count()
    items = query.offset((page - 1) * size).limit(size).all()
    return {"total": total, "page": page, "size": size, "items": items}


# ── PPA ───────────────────────────────────────────────────────────────────────

@router.get("/ppas")
def list_ppas(
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(PPA)
    if status:
        q = q.filter(PPA.status == status)
    return _paginate(q.order_by(PPA.period_start.desc()), page, size)


@router.get("/ppas/{ppa_id}", response_model=PPAOut)
def get_ppa(ppa_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ppa = db.get(PPA, ppa_id)
    if not ppa:
        raise HTTPException(status_code=404, detail="PPA não encontrado")
    return ppa


@router.post("/ppas", response_model=PPAOut)
def create_ppa(
    payload: PPACreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    if payload.period_end < payload.period_start:
        raise HTTPException(status_code=422, detail="period_end deve ser >= period_start")
    ppa = PPA(**payload.model_dump())
    db.add(ppa)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="ppas", entity_id=str(ppa.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(ppa)
    return ppa


@router.patch("/ppas/{ppa_id}", response_model=PPAOut)
def update_ppa(
    ppa_id: int,
    payload: PPAUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    ppa = db.get(PPA, ppa_id)
    if not ppa:
        raise HTTPException(status_code=404, detail="PPA não encontrado")
    before = {"status": ppa.status}
    if payload.description is not None:
        ppa.description = payload.description
    if payload.status is not None:
        ppa.status = payload.status
    write_audit(db, user_id=current.id, action="update", entity="ppas", entity_id=str(ppa.id), before_data=before, after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(ppa)
    return ppa


@router.post("/ppas/{ppa_id}/programs", response_model=PPAProgramOut)
def add_ppa_program(
    ppa_id: int,
    payload: PPAProgramCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    ppa = db.get(PPA, ppa_id)
    if not ppa:
        raise HTTPException(status_code=404, detail="PPA não encontrado")
    prog = PPAProgram(ppa_id=ppa_id, **payload.model_dump())
    db.add(prog)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="ppa_programs", entity_id=str(prog.id), after_data={"ppa_id": ppa_id, "code": prog.code})
    db.commit()
    db.refresh(prog)
    return prog


@router.get("/ppas/{ppa_id}/programs", response_model=list[PPAProgramOut])
def list_ppa_programs(ppa_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ppa = db.get(PPA, ppa_id)
    if not ppa:
        raise HTTPException(status_code=404, detail="PPA não encontrado")
    return db.query(PPAProgram).filter(PPAProgram.ppa_id == ppa_id).all()


# ── LDO ───────────────────────────────────────────────────────────────────────

@router.get("/ldos")
def list_ldos(
    fiscal_year_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(LDO)
    if fiscal_year_id:
        q = q.filter(LDO.fiscal_year_id == fiscal_year_id)
    if status:
        q = q.filter(LDO.status == status)
    return _paginate(q.order_by(LDO.id.desc()), page, size)


@router.get("/ldos/{ldo_id}", response_model=LDOOut)
def get_ldo(ldo_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ldo = db.get(LDO, ldo_id)
    if not ldo:
        raise HTTPException(status_code=404, detail="LDO não encontrada")
    return ldo


@router.post("/ldos", response_model=LDOOut)
def create_ldo(
    payload: LDOCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    ldo = LDO(**payload.model_dump())
    db.add(ldo)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="ldos", entity_id=str(ldo.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(ldo)
    return ldo


@router.patch("/ldos/{ldo_id}", response_model=LDOOut)
def update_ldo(
    ldo_id: int,
    payload: LDOUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    ldo = db.get(LDO, ldo_id)
    if not ldo:
        raise HTTPException(status_code=404, detail="LDO não encontrada")
    before = {"status": ldo.status}
    if payload.description is not None:
        ldo.description = payload.description
    if payload.status is not None:
        ldo.status = payload.status
    write_audit(db, user_id=current.id, action="update", entity="ldos", entity_id=str(ldo.id), before_data=before, after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(ldo)
    return ldo


@router.post("/ldos/{ldo_id}/goals", response_model=LDOGoalOut)
def add_ldo_goal(
    ldo_id: int,
    payload: LDOGoalCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    ldo = db.get(LDO, ldo_id)
    if not ldo:
        raise HTTPException(status_code=404, detail="LDO não encontrada")
    goal = LDOGoal(ldo_id=ldo_id, **payload.model_dump())
    db.add(goal)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="ldo_goals", entity_id=str(goal.id), after_data={"ldo_id": ldo_id, "code": goal.code})
    db.commit()
    db.refresh(goal)
    return goal


@router.get("/ldos/{ldo_id}/goals", response_model=list[LDOGoalOut])
def list_ldo_goals(ldo_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    ldo = db.get(LDO, ldo_id)
    if not ldo:
        raise HTTPException(status_code=404, detail="LDO não encontrada")
    return db.query(LDOGoal).filter(LDOGoal.ldo_id == ldo_id).all()


# ── LOA ───────────────────────────────────────────────────────────────────────

@router.get("/loas")
def list_loas(
    fiscal_year_id: int | None = None,
    status: str | None = None,
    page: int = Query(1, ge=1),
    size: int = Query(10, ge=1, le=100),
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    q = db.query(LOA)
    if fiscal_year_id:
        q = q.filter(LOA.fiscal_year_id == fiscal_year_id)
    if status:
        q = q.filter(LOA.status == status)
    return _paginate(q.order_by(LOA.id.desc()), page, size)


@router.get("/loas/{loa_id}", response_model=LOAOut)
def get_loa(loa_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    loa = db.get(LOA, loa_id)
    if not loa:
        raise HTTPException(status_code=404, detail="LOA não encontrada")
    return loa


@router.post("/loas", response_model=LOAOut)
def create_loa(
    payload: LOACreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    loa = LOA(**payload.model_dump())
    db.add(loa)
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="loas", entity_id=str(loa.id), after_data=payload.model_dump())
    db.commit()
    db.refresh(loa)
    return loa


@router.patch("/loas/{loa_id}", response_model=LOAOut)
def update_loa(
    loa_id: int,
    payload: LOAUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    loa = db.get(LOA, loa_id)
    if not loa:
        raise HTTPException(status_code=404, detail="LOA não encontrada")
    before = {"status": loa.status, "total_expenditure": loa.total_expenditure}
    if payload.description is not None:
        loa.description = payload.description
    if payload.total_revenue is not None:
        loa.total_revenue = payload.total_revenue
    if payload.total_expenditure is not None:
        loa.total_expenditure = payload.total_expenditure
    if payload.status is not None:
        loa.status = payload.status
    write_audit(db, user_id=current.id, action="update", entity="loas", entity_id=str(loa.id), before_data=before, after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(loa)
    return loa


@router.post("/loas/{loa_id}/items", response_model=LOAItemOut)
def add_loa_item(
    loa_id: int,
    payload: LOAItemCreate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    loa = db.get(LOA, loa_id)
    if not loa:
        raise HTTPException(status_code=404, detail="LOA não encontrada")
    item = LOAItem(loa_id=loa_id, **payload.model_dump())
    db.add(item)
    loa.total_expenditure += payload.authorized_amount
    db.flush()
    write_audit(db, user_id=current.id, action="create", entity="loa_items", entity_id=str(item.id), after_data={"loa_id": loa_id, "action_code": item.action_code})
    db.commit()
    db.refresh(item)
    return item


@router.get("/loas/{loa_id}/items", response_model=list[LOAItemOut])
def list_loa_items(
    loa_id: int,
    function_code: str | None = None,
    category: str | None = None,
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
):
    loa = db.get(LOA, loa_id)
    if not loa:
        raise HTTPException(status_code=404, detail="LOA não encontrada")
    q = db.query(LOAItem).filter(LOAItem.loa_id == loa_id)
    if function_code:
        q = q.filter(LOAItem.function_code == function_code)
    if category:
        q = q.filter(LOAItem.category == category)
    return q.all()


@router.patch("/loas/{loa_id}/items/{item_id}", response_model=LOAItemOut)
def update_loa_item(
    loa_id: int,
    item_id: int,
    payload: LOAItemUpdate,
    db: Session = Depends(get_db),
    current: User = Depends(require_roles(RoleEnum.admin, RoleEnum.accountant)),
):
    item = db.get(LOAItem, item_id)
    if not item or item.loa_id != loa_id:
        raise HTTPException(status_code=404, detail="Item de LOA não encontrado")
    loa = db.get(LOA, loa_id)
    before_amount = item.authorized_amount
    if payload.description is not None:
        item.description = payload.description
    if payload.authorized_amount is not None:
        delta = payload.authorized_amount - before_amount
        item.authorized_amount = payload.authorized_amount
        loa.total_expenditure += delta
    if payload.executed_amount is not None:
        item.executed_amount = payload.executed_amount
    write_audit(db, user_id=current.id, action="update", entity="loa_items", entity_id=str(item.id), after_data=payload.model_dump(exclude_none=True))
    db.commit()
    db.refresh(item)
    return item


@router.get("/loas/{loa_id}/execution-summary")
def loa_execution_summary(loa_id: int, db: Session = Depends(get_db), _: User = Depends(get_current_user)):
    """Resumo de execução orçamentária da LOA: autorizado vs. executado."""
    loa = db.get(LOA, loa_id)
    if not loa:
        raise HTTPException(status_code=404, detail="LOA não encontrada")
    items = db.query(LOAItem).filter(LOAItem.loa_id == loa_id).all()
    total_authorized = sum(i.authorized_amount for i in items)
    total_executed = sum(i.executed_amount for i in items)
    return {
        "loa_id": loa_id,
        "description": loa.description,
        "status": loa.status,
        "total_authorized": total_authorized,
        "total_executed": total_executed,
        "execution_rate": round(total_executed / total_authorized * 100, 2) if total_authorized else 0.0,
        "by_function": _group_by_function(items),
    }


def _group_by_function(items: list) -> list[dict]:
    groups: dict[str, dict] = {}
    for item in items:
        key = item.function_code
        if key not in groups:
            groups[key] = {"function_code": key, "authorized": 0.0, "executed": 0.0}
        groups[key]["authorized"] += item.authorized_amount
        groups[key]["executed"] += item.executed_amount
    return list(groups.values())
