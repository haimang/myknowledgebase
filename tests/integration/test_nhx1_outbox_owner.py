"""NHX1-T14: dead delivery has an explicit owner and terminal policy."""

from __future__ import annotations

from pathlib import Path

import pytest

from tests.unit.test_workflow_runtime import _seed_runtime


@pytest.mark.asyncio
async def test_critical_dead_delivery_terminalizes_owner_and_preserves_row(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    try:
        async with persistence.transaction() as tx:
            await runtime._enqueue_tx(  # noqa: SLF001
                tx,
                ids["team_uuid"],
                "wake_execution",
                {"execution_uuid": ids["execution_uuid"], "task_uuid": ids["task_uuid"], "generation": 1},
                "nhx1-owner-wake",
            )
            owner = await tx.fetchone(
                "SELECT owner_kind,owner_uuid,owner_generation,criticality,attempt_budget,dead_error_code "
                "FROM mkb_outbox WHERE dedupe_key='nhx1-owner-wake'"
            )
            assert owner == {
                "owner_kind": "execution",
                "owner_uuid": ids["execution_uuid"],
                "owner_generation": 1,
                "criticality": "critical",
                "attempt_budget": 8,
                "dead_error_code": "OUTBOX_WAKE_DEAD",
            }
            outbox = await tx.fetchone("SELECT outbox_id FROM mkb_outbox WHERE dedupe_key='nhx1-owner-wake'")
            assert outbox is not None
            await tx.execute(
                "UPDATE mkb_outbox SET status='in_flight',attempts=8,lease_owner='owner',lease_expires_at=? "
                "WHERE outbox_id=?",
                ("2026-08-31T00:00:00Z", outbox["outbox_id"]),
            )
            outbox_id = str(outbox["outbox_id"])
        await runtime._release_outbox(outbox_id, "owner", "poison delivery")  # noqa: SLF001
        async with persistence.read_snapshot() as tx:
            dead = await tx.fetchone("SELECT status,attempts FROM mkb_outbox WHERE outbox_id=?", (outbox_id,))
            execution = await tx.fetchone(
                "SELECT status,final_error_code FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            task = await tx.fetchone("SELECT status,error_code FROM mkb_tasks WHERE task_uuid=?", (ids["task_uuid"],))
        assert dead == {"status": "dead", "attempts": 8}
        assert execution == {"status": "failed", "final_error_code": "OUTBOX_WAKE_DEAD"}
        assert task == {"status": "failed", "error_code": "OUTBOX_WAKE_DEAD"}
        requeued = await runtime.requeue_dead_outbox(
            outbox_id,
            expected_generation=1,
            idempotency_key="requeue-once",
        )
        replay = await runtime.requeue_dead_outbox(
            outbox_id,
            expected_generation=1,
            idempotency_key="requeue-once",
        )
        assert requeued["disposition"] == "applied"
        assert replay["disposition"] == "replayed"
        async with persistence.read_snapshot() as tx:
            predecessor = await tx.fetchone(
                "SELECT retry_of_outbox_id,status,delivery_generation FROM mkb_outbox WHERE outbox_id=?",
                (requeued["outbox_id"],),
            )
        assert predecessor == {"retry_of_outbox_id": outbox_id, "status": "pending", "delivery_generation": 2}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_advisory_dead_delivery_does_not_kill_owner(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    try:
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_outbox(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,"
                "attempts,available_at,created_at,updated_at,lease_owner,owner_kind,owner_uuid,owner_generation,criticality,"
                "attempt_budget,dead_error_code) VALUES (?,?,?,?,?,?,'in_flight',8,?,?,?,?,'execution',?,?,'advisory',8,?)",
                (
                    "advisory-outbox",
                    ids["team_uuid"],
                    "wake_process",
                    "{}",
                    "0" * 64,
                    "advisory",
                    "2026-08-31T00:00:00Z",
                    "2026-08-31T00:00:00Z",
                    "2026-08-31T00:00:00Z",
                    "",
                    ids["execution_uuid"],
                    1,
                    "ADVISORY_DELIVERY_DEAD",
                ),
            )
        await runtime._release_outbox("advisory-outbox", "", "advisory poison")  # noqa: SLF001
        async with persistence.read_snapshot() as tx:
            execution = await tx.fetchone("SELECT status FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],))
            dead = await tx.fetchone("SELECT status FROM mkb_outbox WHERE outbox_id='advisory-outbox'")
        assert execution == {"status": "ready"}
        assert dead == {"status": "dead"}
    finally:
        await persistence.close()
