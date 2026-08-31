"""Closed 7-intent × lifecycle-state admission matrix (NHX1-T07)."""

from __future__ import annotations

from types import MappingProxyType

from src.contracts.common.errors import ConflictError

LIFECYCLE_STATES = ("active", "deactivated", "deleted")
INTAKE_INTENT_APPLICABILITY = MappingProxyType(
    {
        "intake.ingest": frozenset({"active"}),
        "intake.rebuild": frozenset({"active"}),
        "intake.update_metadata": frozenset({"active"}),
        "intake.deactivate": frozenset({"active"}),
        "intake.reactivate": frozenset({"deactivated"}),
        "intake.delete": frozenset({"active", "deactivated"}),
        "index.rebuild": frozenset({"active"}),
    }
)


def assert_intent_applicable(intent: str, lifecycle_state: str) -> None:
    allowed = INTAKE_INTENT_APPLICABILITY.get(intent)
    if allowed is None:
        raise ConflictError("INTAKE_INTENT_INVALID", "Intake intent is not registered")
    if lifecycle_state not in allowed:
        code = "INTAKE_ITEM_DELETED" if lifecycle_state == "deleted" else "INTAKE_INTENT_STATE_CONFLICT"
        raise ConflictError(code, "Intake intent is not applicable in the current lifecycle state")
