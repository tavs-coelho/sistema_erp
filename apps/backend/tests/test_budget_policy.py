import pytest
from fastapi import HTTPException
from app.budget_policy import validate_ppa_period, ppa_transition, require_ppa_editable


def test_ppa_four_fiscal_years():
    validate_ppa_period(2026, 2029)
    for dates in [(2026, 2028), (2026, 2030), (1999, 2002)]:
        with pytest.raises(HTTPException):
            validate_ppa_period(*dates)


def test_valid_transitions():
    ppa_transition("rascunho", "em_revisao")
    ppa_transition("em_revisao", "aprovado")
    ppa_transition("em_revisao", "rascunho")


@pytest.mark.parametrize("source,target", [
    ("rascunho", "aprovado"), ("aprovado", "rascunho"),
    ("aprovado", "em_revisao"), ("desconhecido", "aprovado"),
    ("rascunho", "rascunho"),
])
def test_invalid_transitions(source, target):
    with pytest.raises(HTTPException) as exc:
        ppa_transition(source, target)
    assert exc.value.status_code == 409


def test_only_drafts_are_editable():
    require_ppa_editable("rascunho")
    for status in ["em_revisao", "aprovado"]:
        with pytest.raises(HTTPException):
            require_ppa_editable(status)
