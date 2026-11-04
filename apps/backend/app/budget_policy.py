"""Regras de transição do Plano Plurianual (PPA)."""
from fastapi import HTTPException

PPA_STATES = ("rascunho", "em_revisao", "aprovado")


def validate_ppa_period(start: int, end: int) -> None:
    if start < 2000 or end != start + 3:
        raise HTTPException(status_code=422, detail="PPA exige quatro exercícios consecutivos")


def ppa_transition(current: str, target: str) -> None:
    allowed = {
        "rascunho": {"em_revisao"},
        "em_revisao": {"rascunho", "aprovado"},
        "aprovado": set(),
    }
    if current not in allowed or target not in allowed[current]:
        raise HTTPException(status_code=409, detail="Transição de situação do PPA inválida")


def require_ppa_editable(status: str) -> None:
    if status != "rascunho":
        raise HTTPException(status_code=409, detail="PPA em revisão ou aprovado não permite edição")
