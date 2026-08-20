"""NS6-T05 / T06: cancel handler_task; heartbeat exception fences."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.runtime.workflow.worker import WorkflowWorker
from src.services.artifacts import OutcomeArtifactCommitter
from src.storage.local_store import LocalObjectStore
from tests.unit.test_workflow_runtime import _AlwaysSuccessfulStage, _seed_runtime


@pytest.mark.asyncio
async def test_run_once_cancel_cancels_handler_and_discards_pending(tmp_path: Path) -> None:
    storage = LocalObjectStore(tmp_path / "objects")
    committer = OutcomeArtifactCommitter(storage)
    persistence, runtime, ids = await _seed_runtime(tmp_path, outcome_committer=committer)
    await runtime.materialize_root(ids["execution_uuid"])

    class SlowStage(_AlwaysSuccessfulStage):
        def __init__(self) -> None:
            self.task: asyncio.Task[ProcessOutcome] | None = None
            self.command: ProcessCommand | None = None

        async def run(self, command: ProcessCommand) -> ProcessOutcome:
            current = asyncio.current_task()
            assert current is not None
            self.task = current
            self.command = command
            await asyncio.sleep(30)
            return await super().run(command)

    stage = SlowStage()
    worker = WorkflowWorker(runtime, stage)
    run = asyncio.create_task(worker.run_once("ns6-cancel-owner", lease_seconds=30))
    for _ in range(100):
        if stage.command is not None:
            break
        await asyncio.sleep(0.02)
    assert stage.command is not None
    committer._pending[(stage.command.process_uuid, stage.command.fencing_generation)] = object()  # type: ignore[assignment]
    run.cancel()
    with pytest.raises(asyncio.CancelledError):
        await run
    assert stage.task is not None
    assert stage.task.cancelled()
    assert committer._pending == {}
    await persistence.close()


@pytest.mark.asyncio
async def test_heartbeat_exception_fences_and_does_not_succeed(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    finished = {"value": False}

    class SlowStage(_AlwaysSuccessfulStage):
        async def run(self, command: ProcessCommand) -> ProcessOutcome:
            try:
                await asyncio.sleep(2)
                finished["value"] = True
                return await super().run(command)
            except asyncio.CancelledError:
                raise

    async def boom(*_args: object, **_kwargs: object) -> bool:
        raise RuntimeError("heartbeat storage failed")

    runtime.heartbeat = boom  # type: ignore[method-assign]
    worker = WorkflowWorker(runtime, SlowStage())
    ran = await asyncio.wait_for(worker.run_once("ns6-heartbeat-owner", lease_seconds=1), timeout=3)
    assert ran is True
    assert finished["value"] is False
    async with persistence.transaction() as tx:
        row = await tx.fetchone(
            "SELECT status FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert row is not None
    assert row["status"] != "succeeded"
    await persistence.close()
