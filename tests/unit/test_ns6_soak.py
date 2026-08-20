"""NS6-T36: BEGIN-cancel and heartbeat-raise soaks."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.test_ns6_uow_begin_cancel import test_cancel_during_begin_allows_next_immediate_begin
from tests.unit.test_ns6_worker_cancel import test_heartbeat_exception_fences_and_does_not_succeed


@pytest.mark.asyncio
async def test_begin_cancel_soak(tmp_path: Path) -> None:
    for index in range(5):
        await test_cancel_during_begin_allows_next_immediate_begin(tmp_path / f"begin-{index}")


@pytest.mark.asyncio
async def test_heartbeat_raise_soak(tmp_path: Path) -> None:
    for index in range(3):
        await test_heartbeat_exception_fences_and_does_not_succeed(tmp_path / f"hb-{index}")
