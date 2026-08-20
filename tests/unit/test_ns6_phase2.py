"""NS6-T09–T16: schema closed set, tombstone lookup, outbox CAS, fencing, Team 409."""

from __future__ import annotations

import asyncio
import json
import sqlite3
from contextlib import asynccontextmanager
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest

from src.contracts.api.models import ExpectedRevisionRequest, TeamCreateRequest
from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.metrics import MetricRegistry
from src.runtime.task.service import TaskService
from src.runtime.workflow.worker import WorkflowWorker
from src.services.events import DomainEventWriter
from src.services.index_retirement import (
    RETIREMENT_POLICY_REF,
    RETIREMENT_TARGET_KIND,
    IndexGenerationRetirementDisposition,
    IndexGenerationRetirementService,
)
from src.services.scatter_intake import ScatterAcceptanceWriter
from src.services.teams import TeamService
from tests.unit.test_index_generation_retirement import (
    CUTOVER,
    ITEM,
    NAMESPACE,
    TEAM,
    MutableClock,
    _seed_retired_generation,
    _timestamp,
)
from tests.unit.test_object_gc import _seed_orphan, _service
from tests.unit.test_workflow_runtime import _AlwaysSuccessfulStage, _seed_runtime


@pytest.mark.asyncio
async def test_drop_outbox_fails_schema_readiness(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "schema.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    connection = persistence._connect()
    connection.execute("DROP TABLE mkb_outbox")
    connection.commit()
    ready = await persistence.readiness()
    assert ready["schema_migration"] is False
    await persistence.close()


@pytest.mark.asyncio
async def test_tombstone_then_dirty_catalog_allocates_new_live_uuid(tmp_path: Path) -> None:
    seed = await _seed_orphan(tmp_path)
    try:
        result = await _service(seed).scan_once()
        assert result.deleted_count == 1
        async with seed.persistence.transaction() as tx:
            new_uuid = await ScatterAcceptanceWriter._catalog_stat(tx, seed.team_uuid, seed.stat)
            await tx.execute(
                "INSERT INTO mkb_object_references "
                "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
                "created_at,payload_extra) VALUES (?,?,?,'process_io','test_owner',?,?,?,?, '{}')",
                (uuid7(), seed.team_uuid, new_uuid, "catalog", seed.stat.sha256, seed.stat.size_bytes, utc_now()),
            )
        assert new_uuid != seed.stored_object_uuid
        async with seed.persistence.transaction() as tx:
            live = await tx.fetchone(
                "SELECT stored_object_uuid FROM mkb_stored_objects "
                "WHERE team_uuid=? AND content_digest=? AND size_bytes=? AND tombstoned_at IS NULL",
                (seed.team_uuid, seed.stat.sha256, seed.stat.size_bytes),
            )
            refs = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_object_references WHERE stored_object_uuid=? AND released_at IS NULL",
                (new_uuid,),
            )
        assert live == {"stored_object_uuid": new_uuid}
        assert refs == {"count": 1}
    finally:
        await seed.persistence.close()


@pytest.mark.asyncio
async def test_poison_outbox_increments_dead_metric_with_task_trace(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    metrics = MetricRegistry()
    runtime.metrics = metrics
    await runtime.materialize_root(ids["execution_uuid"])
    now = utc_now()
    poison_id = uuid7()
    payload = {"execution_uuid": ids["execution_uuid"], "task_uuid": ids["task_uuid"]}
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?, 'wake_process',?,?,?,?,?,?,?,'{}')",
            (
                poison_id,
                ids["team_uuid"],
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                "c" * 64,
                f"poison:{poison_id}",
                "pending",
                "2000-01-01T00:00:00.000000Z",
                "2000-01-01T00:00:00.000000Z",
                now,
            ),
        )
    claimed = await runtime.claim_outbox("ns6-metrics-owner")
    assert claimed is None
    rendered = metrics.render()
    assert 'mkb_outbox_dead_total{kind="wake_process"} 1.0' in rendered
    async with persistence.transaction() as tx:
        event = await tx.fetchone(
            "SELECT trace_uuid,event_type FROM mkb_domain_events WHERE event_type='outbox.dead' ORDER BY occurred_at DESC LIMIT 1"
        )
    assert event is not None
    assert event["trace_uuid"] == ids["trace_uuid"]
    await persistence.close()


@pytest.mark.asyncio
async def test_stale_owner_cannot_insert_outbox_dead(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    now = utc_now()
    outbox_id = uuid7()
    payload = {"execution_uuid": ids["execution_uuid"]}
    payload_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?, 'wake_process',?,?,?,?,?,?,?,'{}')",
            (
                outbox_id,
                ids["team_uuid"],
                payload_json,
                stable_digest(payload),
                f"stale:{outbox_id}",
                "pending",
                now,
                now,
                now,
            ),
        )
    first = await runtime.claim_outbox("owner-a", lease_seconds=1)
    assert first is not None
    assert first.outbox_id == outbox_id
    async with persistence.transaction() as tx:
        await tx.execute(
            "UPDATE mkb_outbox SET lease_expires_at=? WHERE outbox_id=?",
            ("2000-01-01T00:00:00.000000Z", outbox_id),
        )
    second = await runtime.claim_outbox("owner-b", lease_seconds=30)
    assert second is not None
    assert second.outbox_id == outbox_id
    await runtime._mark_outbox_dead(outbox_id, first.lease_owner, "stale owner")
    async with persistence.transaction() as tx:
        current = await tx.fetchone("SELECT status FROM mkb_outbox WHERE outbox_id=?", (outbox_id,))
        dead_events = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_domain_events WHERE event_type='outbox.dead'"
        )
    assert current is not None
    assert current["status"] != "dead"
    assert dead_events == {"count": 0}
    await persistence.close()


@pytest.mark.asyncio
async def test_namespace_inactive_intents_yield_to_healthy(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "ns-retire.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    await _seed_retired_generation(persistence)
    clock = MutableClock(CUTOVER + timedelta(hours=2))
    now = _timestamp(clock.now)
    connection = persistence._connect()
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute("UPDATE mkb_vector_namespaces SET status='disabled' WHERE namespace_uuid=?", (NAMESPACE,))
    digest = "b" * 64
    for index in range(100):
        connection.execute(
            "INSERT INTO mkb_intake_cleanup_intents "
            "(intent_uuid,team_uuid,policy_ref,target_kind,target_ref,required_substrate_set_digest,hold_refs_json,"
            "status,requested_at,eligible_at,payload_extra) VALUES (?,?,?,?,?,?, '[]','open',?,?, '{}')",
            (
                uuid7(),
                TEAM,
                RETIREMENT_POLICY_REF,
                RETIREMENT_TARGET_KIND,
                f"index-generation:v1:{ITEM}:{NAMESPACE}:{index + 10}",
                digest,
                now,
                now,
            ),
        )
    healthy_item = "123e4567-e89b-42d3-a456-426614174099"
    healthy_ns = "123e4567-e89b-42d3-a456-426614174098"
    healthy_intent = uuid7()
    connection.execute(
        "INSERT INTO mkb_vector_namespaces "
        "(namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,embedding_model_version,"
        "adapter_kind,dimension,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (healthy_ns, TEAM, "healthy", "model", "model", "v1", "local", 2, now, now),
    )
    connection.execute(
        "INSERT INTO mkb_intake_items "
        "(team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,"
        "latest_revision_uuid,serving_revision_uuid,row_revision,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (
            TEAM,
            healthy_item,
            "123e4567-e89b-42d3-a456-426614174006",
            "healthy",
            "active",
            "123e4567-e89b-42d3-a456-426614174003",
            "123e4567-e89b-42d3-a456-426614174003",
            0,
            now,
            now,
        ),
    )
    connection.execute(
        "INSERT INTO mkb_index_active_pointers "
        "(team_uuid,intake_item_uuid,namespace_uuid,active_index_generation,pointer_row_revision,lifecycle_state,"
        "updated_at) VALUES (?,?,?,?,?,?,?)",
        (TEAM, healthy_item, healthy_ns, 2, 1, "active", now),
    )
    connection.execute(
        "INSERT INTO mkb_intake_cleanup_intents "
        "(intent_uuid,team_uuid,policy_ref,target_kind,target_ref,required_substrate_set_digest,hold_refs_json,"
        "status,requested_at,eligible_at,payload_extra) VALUES (?,?,?,?,?,?, '[]','open',?,?, '{}')",
        (
            healthy_intent,
            TEAM,
            RETIREMENT_POLICY_REF,
            RETIREMENT_TARGET_KIND,
            f"index-generation:v1:{healthy_item}:{healthy_ns}:1",
            "c" * 64,
            now,
            now,
        ),
    )
    connection.commit()
    service = IndexGenerationRetirementService(persistence, grace=timedelta(hours=1), clock=clock)
    first = await service.scan_once(limit=100)
    assert any(result.disposition is IndexGenerationRetirementDisposition.ABANDONED for result in first.results)
    second = await service.scan_once(limit=100)
    intent_ids = {result.intent_uuid for result in second.results}
    due = await service.collect_due(limit=100)
    due_ids = {item.intent_uuid for item in due}
    assert healthy_intent in intent_ids or healthy_intent in due_ids
    await persistence.close()


@pytest.mark.asyncio
async def test_stale_fencing_fail_does_not_kill_new_generation(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    claim = await runtime.claim_next("fence-owner")
    assert claim is not None
    await runtime.mark_running(claim.command.process_uuid, claim.command.fencing_generation)
    async with persistence.transaction() as tx:
        process = await tx.fetchone("SELECT * FROM mkb_processes WHERE process_uuid=?", (claim.command.process_uuid,))
        assert process is not None
        await tx.execute(
            "UPDATE mkb_processes SET fencing_generation=fencing_generation+1,status='running' WHERE process_uuid=?",
            (claim.command.process_uuid,),
        )
        await runtime._fail_process_tx(
            tx,
            dict(process),
            error_code="stale-fail",
            error_message="old generation",
            failure_disposition="error",
        )
        current = await tx.fetchone(
            "SELECT status,fencing_generation FROM mkb_processes WHERE process_uuid=?",
            (claim.command.process_uuid,),
        )
    assert current is not None
    assert current["status"] == "running"
    assert current["fencing_generation"] == process["fencing_generation"] + 1
    await persistence.close()


@pytest.mark.asyncio
async def test_cancel_prevents_succeeded_task(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])

    started = asyncio.Event()

    class SlowStage(_AlwaysSuccessfulStage):
        async def run(self, command: ProcessCommand) -> ProcessOutcome:
            started.set()
            await asyncio.sleep(0.4)
            return await super().run(command)

    worker = WorkflowWorker(runtime, SlowStage())
    run = asyncio.create_task(worker.run_once("ns6-cancel-task"))
    try:
        await asyncio.wait_for(started.wait(), timeout=2)
        async with persistence.transaction() as tx:
            current = await tx.fetchone("SELECT row_revision FROM mkb_tasks WHERE task_uuid=?", (ids["task_uuid"],))
        assert current is not None
        tasks = TaskService(persistence, TeamService(persistence), DomainEventWriter())
        await tasks.cancel(
            ids["team_uuid"],
            ids["task_uuid"],
            ExpectedRevisionRequest(expected_revision=int(current["row_revision"])),
        )
        with pytest.raises((ConflictError, asyncio.CancelledError)):
            await asyncio.wait_for(run, timeout=3)
    finally:
        if not run.done():
            run.cancel()
            with pytest.raises(asyncio.CancelledError):
                await run
    async with persistence.transaction() as tx:
        task = await tx.fetchone("SELECT status FROM mkb_tasks WHERE task_uuid=?", (ids["task_uuid"],))
        execution = await tx.fetchone(
            "SELECT status FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
    assert task is not None
    assert task["status"] != "succeeded"
    assert execution is not None
    assert execution["status"] != "succeeded"
    await persistence.close()


@pytest.mark.asyncio
async def test_team_create_unique_conflict_maps_to_409(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "team.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    service = TeamService(persistence)
    request = TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=uuid7(), name="dup")

    @asynccontextmanager
    async def boom_tx() -> Any:
        class _Boom:
            async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
                del sql, params
                return None

            async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
                del params
                if "INSERT INTO mkb_teams" in sql:
                    raise sqlite3.IntegrityError("UNIQUE constraint failed: mkb_teams.team_uuid")
                return type("Cursor", (), {"rowcount": 0})()

        yield _Boom()

    persistence.transaction = boom_tx  # type: ignore[method-assign]
    with pytest.raises(ConflictError, match="team-identity"):
        await service.create(request)
    await persistence.close()
