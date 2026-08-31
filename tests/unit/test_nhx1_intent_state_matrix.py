"""NHX1-T07: the complete 7 × 3 applicability matrix is code-owned."""

from __future__ import annotations

import pytest

from src.contracts.common.errors import ConflictError
from src.services.intake_lifecycle.admission_matrix import (
    INTAKE_INTENT_APPLICABILITY,
    LIFECYCLE_STATES,
    assert_intent_applicable,
)


def test_matrix_has_exactly_seven_intents_and_three_states() -> None:
    assert set(INTAKE_INTENT_APPLICABILITY) == {
        "intake.ingest",
        "intake.rebuild",
        "intake.update_metadata",
        "intake.deactivate",
        "intake.reactivate",
        "intake.delete",
        "index.rebuild",
    }
    assert LIFECYCLE_STATES == ("active", "deactivated", "deleted")


@pytest.mark.parametrize("intent, state", [(intent, state) for intent, states in INTAKE_INTENT_APPLICABILITY.items() for state in states])
def test_legal_matrix_cells_are_admitted(intent: str, state: str) -> None:
    assert_intent_applicable(intent, state)


@pytest.mark.parametrize(
    "intent, state",
    [
        (intent, state)
        for intent, states in INTAKE_INTENT_APPLICABILITY.items()
        for state in LIFECYCLE_STATES
        if state not in states
    ],
)
def test_illegal_matrix_cells_fail_before_task_creation(intent: str, state: str) -> None:
    with pytest.raises(ConflictError):
        assert_intent_applicable(intent, state)
