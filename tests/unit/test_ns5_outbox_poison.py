"""NS5-T05: illegal outbox JSON is marked dead and the same tick still claims work."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.runtime.workflow_engine import WorkflowWorker
from src.runtime.workflow_supervisor import WorkflowSupervisor
from tests.unit.test_workflow_runtime import _AlwaysSuccessfulStage, _seed_runtime


@pytest.mark.asyncio
async def test_poison_outbox_is_dead_and_next_process_is_claimed(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    now = utc_now()
    poison_id = uuid7()
    wake_id = uuid7()
    process = None
    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT process_uuid FROM mkb_processes WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
    assert process is not None
    wake_payload = {"execution_uuid": ids["execution_uuid"], "process_uuid": process["process_uuid"]}
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?, 'wake_process',?,?,?,?,?,?,?,'{}')",
            (
                poison_id,
                ids["team_uuid"],
                "not-json",
                "b" * 64,
                f"poison:{poison_id}",
                "pending",
                now,
                now,
                now,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?, 'wake_process',?,?,?,?,?,?,?,'{}')",
            (
                wake_id,
                ids["team_uuid"],
                json.dumps(wake_payload, sort_keys=True, separators=(",", ":")),
                stable_digest(wake_payload),
                f"wake:{wake_id}",
                "pending",
                now,
                now,
                now,
            ),
        )

    worker = WorkflowWorker(runtime, _AlwaysSuccessfulStage())
    supervisor = WorkflowSupervisor(runtime, worker, max_outbox_per_tick=8, max_processes_per_tick=4)
    progressed = await supervisor.drain_once()
    assert progressed >= 1

    async with persistence.transaction() as tx:
        poison = await tx.fetchone("SELECT status,last_error FROM mkb_outbox WHERE outbox_id=?", (poison_id,))
        second = await tx.fetchone("SELECT status FROM mkb_outbox WHERE outbox_id=?", (wake_id,))
        claimed = await tx.fetchone(
            "SELECT status FROM mkb_processes WHERE execution_uuid=? ORDER BY created_at LIMIT 1",
            (ids["execution_uuid"],),
        )
    assert poison is not None and poison["status"] == "dead"
    assert poison["last_error"]
    assert second is not None and second["status"] in {"done", "in_flight", "pending"}
    assert claimed is not None and claimed["status"] in {"claimed", "running", "succeeded", "ready"}
    await persistence.close()
