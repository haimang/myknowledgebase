"""Pure checks for the temporary model-capacity priority policy."""

from __future__ import annotations

import pytest

from src.contracts.common.errors import MkbError
from src.runtime.task.model_capacity import assert_model_capacity_allowed


class _Config:
    class settings:
        model_capacity_priority_gate_enabled = True


@pytest.mark.parametrize("priority", ["high", "urgent"])
def test_high_priority_model_work_is_allowed(priority: str) -> None:
    assert_model_capacity_allowed(
        priority=priority,
        request_intent="intake.ingest",
        config_snapshots=_Config(),
    )


@pytest.mark.parametrize("priority", ["normal", "low"])
def test_lower_priority_model_work_is_rejected(priority: str) -> None:
    with pytest.raises(MkbError) as raised:
        assert_model_capacity_allowed(
            priority=priority,
            request_intent="intake.ingest",
            config_snapshots=_Config(),
        )
    assert raised.value.code == "MODEL_AT_CAPACITY"
    assert raised.value.status_code == 429


def test_non_model_task_is_not_rejected() -> None:
    assert_model_capacity_allowed(
        priority="low",
        request_intent="index.rebuild",
        config_snapshots=_Config(),
    )
