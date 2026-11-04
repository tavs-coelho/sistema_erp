import pytest
from fastapi import HTTPException
from app.appropriation_policy import (
    require_draft, validate_amount, validate_execution, require_same_fiscal_year,
)


def test_loa_prohibits_overspending():
    validate_execution(100, 100)
    for authorized, executed in [(100, 101), (-1, 0), (100, -1)]:
        with pytest.raises(HTTPException):
            validate_execution(authorized, executed)


def test_approved_documents_are_read_only():
    require_draft("rascunho", "LOA")
    for state in ["aprovado", "em_revisao"]:
        with pytest.raises(HTTPException) as exc:
            require_draft(state, "LOA")
        assert exc.value.status_code == 409


def test_ldo_must_match_loa_year():
    require_same_fiscal_year(2027, 2027)
    with pytest.raises(HTTPException):
        require_same_fiscal_year(2027, 2026)


def test_negative_amount_blocked():
    with pytest.raises(HTTPException):
        validate_amount(-0.01)
