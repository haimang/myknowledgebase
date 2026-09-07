"""Admission policy for the temporary generation-capacity throttle."""

from __future__ import annotations

from typing import Any

from src.contracts.common.errors import MkbError

MODEL_BEARING_INTENTS = frozenset({"intake.ingest", "intake.rebuild"})
LOW_PRIORITY_VALUES = frozenset({"low", "normal"})
HIGH_PRIORITY_VALUES = frozenset({"high", "urgent"})


def is_model_bearing_intent(request_intent: str | None) -> bool:
    return request_intent in MODEL_BEARING_INTENTS


def model_capacity_gate_enabled(config_snapshots: Any | None) -> bool:
    settings = getattr(config_snapshots, "settings", None)
    return bool(getattr(settings, "model_capacity_priority_gate_enabled", False))


def assert_model_capacity_allowed(
    *,
    priority: str | None,
    request_intent: str | None,
    config_snapshots: Any | None,
) -> None:
    """Reject lower-priority generation work before durable admission."""

    if (
        model_capacity_gate_enabled(config_snapshots)
        and is_model_bearing_intent(request_intent)
        and priority in LOW_PRIORITY_VALUES
    ):
        raise MkbError("MODEL_AT_CAPACITY", "model at capacity", 429)


def task_row_is_model_bearing(row: dict[str, Any]) -> bool:
    return is_model_bearing_intent(str(row.get("request_intent") or ""))


__all__ = [
    "HIGH_PRIORITY_VALUES",
    "LOW_PRIORITY_VALUES",
    "MODEL_BEARING_INTENTS",
    "assert_model_capacity_allowed",
    "is_model_bearing_intent",
    "model_capacity_gate_enabled",
    "task_row_is_model_bearing",
]
