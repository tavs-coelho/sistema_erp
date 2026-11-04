"""Validações mínimas de integridade orçamentária para LDO/LOA."""
from fastapi import HTTPException


def require_draft(status: str, label: str) -> None:
    if status != "rascunho":
        raise HTTPException(status_code=409, detail=f"{label} não editável fora do rascunho")


def validate_amount(amount: float) -> None:
    if amount < 0:
        raise HTTPException(status_code=422, detail="Valor orçamentário não pode ser negativo")


def validate_execution(authorized: float, executed: float) -> None:
    validate_amount(authorized)
    validate_amount(executed)
    if executed > authorized:
        raise HTTPException(status_code=409, detail="Execução excede a dotação autorizada")


def require_same_fiscal_year(loa_year: int, ldo_year: int) -> None:
    if loa_year != ldo_year:
        raise HTTPException(status_code=409, detail="LDO e LOA devem pertencer ao mesmo exercício")
