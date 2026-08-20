"""D04 review residuals: ChangeSet, covering events, scatter columns, Task CAS."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.api.models import TeamCreateRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.common.models import TaskStatus
from src.contracts.common.time import utc_now
from src.persistence.factory import build_persistence
from src.persistence.migration_runner import discover_migrations
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.task.task_projection import project_task_status_tx
from src.services.events import DomainEventWriter
from src.services.teams import TeamService


async def _db(tmp_path: Path) -> SqlitePersistence:
    persistence = SqlitePersistence(
        tmp_path / "d04.sqlite3",
        Path("src/persistence/migrations"),
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    return persistence


@pytest.mark.asyncio
async def test_migration_chain_includes_scatter_identity_columns(tmp_path: Path) -> None:
    persistence = await _db(tmp_path)
    try:
        ids = [item.migration_id for item in discover_migrations(Path("src/persistence/migrations"))]
        assert "010_spark_vl_embed_model_key" in ids
        assert "013_generation_evidence_plane" in ids
        assert "014_ns5_uuid_and_tombstone" in ids
        assert "015_vec_coord_generation" in ids
        assert "012_dispatch_embed_fifo_index" in ids
        async with persistence.transaction() as tx:
            columns = await tx.fetchall("PRAGMA table_info(mkb_executions)")
        names = {row["name"] for row in columns}
        assert "scatter_intake_revision_uuid" in names
        assert "scatter_member_ordinal" in names
        assert "scatter_change_set_uuid" in names
        async with persistence.transaction() as tx:
            prompt_columns = await tx.fetchall("PRAGMA table_info(mkb_prompt_hash_pointers)")
        assert {"prompt_id", "role", "status", "granularity_set"} <= {row["name"] for row in prompt_columns}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_task_projection_cas_is_noop_when_revision_or_status_is_stale(tmp_path: Path) -> None:
    persistence = await _db(tmp_path)
    try:
        team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
        await TeamService(persistence).create(
            TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="cas")
        )
        now = utc_now()
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_tasks "
                "(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,audit_bound,"
                "title,status,row_revision,current_generation,received_at,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,'mkb.task.v1','intake.ingest','fp',1,'t','succeeded',3,1,?,?,?,'{}')",
                (team_uuid, task_uuid, trace_uuid, now, now, now),
            )
            changed = await project_task_status_tx(
                tx,
                team_uuid=team_uuid,
                task_uuid=task_uuid,
                target=TaskStatus.FAILED,
                error_code="stale",
                error_message="stale",
            )
            assert changed is False
            row = await tx.fetchone(
                "SELECT status,row_revision FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
        assert row is not None
        assert row["status"] == "succeeded"
        assert row["row_revision"] == 3
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_covering_domain_event_failure_rolls_back_business_row(tmp_path: Path) -> None:
    persistence = await _db(tmp_path)
    try:
        team_uuid = uuid7()
        await TeamService(persistence).create(
            TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="events")
        )
        outbox_id = uuid7()
        now = utc_now()
        with pytest.raises(MkbError, match="OBS_EVENT_PAYLOAD_INVALID"):
            async with persistence.transaction() as tx:
                await tx.execute(
                    "INSERT INTO mkb_outbox "
                    "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
                    "VALUES (?,?, 'wake_process','{}',?,'dedupe-1','pending',?,?,?,'{}')",
                    (outbox_id, team_uuid, "a" * 64, now, now, now),
                )
                await DomainEventWriter().write(
                    tx,
                    team_uuid=team_uuid,
                    trace_uuid=uuid7(),
                    event_type="not.a.registered.type",
                    aggregate="intake",
                    summary="must fail",
                )
        async with persistence.transaction() as tx:
            row = await tx.fetchone("SELECT outbox_id FROM mkb_outbox WHERE outbox_id=?", (outbox_id,))
            events = await tx.fetchall("SELECT event_uuid FROM mkb_domain_events")
        assert row is None
        assert events == []
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_scatter_identity_is_readable_without_payload_extra(tmp_path: Path) -> None:
    persistence = await _db(tmp_path)
    try:
        team_uuid = uuid7()
        await TeamService(persistence).create(
            TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="scatter")
        )
        now = utc_now()
        task_uuid, root_uuid, child_uuid = uuid7(), uuid7(), uuid7()
        revision_uuid, change_set_uuid = uuid7(), uuid7()
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_tasks "
                "(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,audit_bound,"
                "title,status,row_revision,current_generation,received_at,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,'mkb.task.v1','intake.ingest','fp',1,'t','running',0,1,?,?,?,'{}')",
                (team_uuid, task_uuid, uuid7(), now, now, now),
            )
            shared = (
                "execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,parent_execution_uuid,"
                "execution_role,requiredness,target_kind,target_uuid,workflow_uuid,workflow_revision_uuid,"
                "compiled_digest,resolver_decision_digest,domain_binding_digest,s05_binding_digest,"
                "config_snapshot_ref,config_snapshot_digest,status,created_at,updated_at,payload_extra,"
                "scatter_intake_revision_uuid,scatter_member_ordinal,scatter_change_set_uuid"
            )
            placeholders = ",".join("?" for _ in shared.split(","))
            digest = "a" * 64
            await tx.execute(
                f"INSERT INTO mkb_executions ({shared}) VALUES ({placeholders})",
                (
                    root_uuid,
                    team_uuid,
                    task_uuid,
                    uuid7(),
                    1,
                    root_uuid,
                    None,
                    "root",
                    "required",
                    "task",
                    task_uuid,
                    uuid7(),
                    uuid7(),
                    digest,
                    digest,
                    digest,
                    digest,
                    "mkbobj:cfg",
                    digest,
                    "ready",
                    now,
                    now,
                    "{}",
                    None,
                    None,
                    None,
                ),
            )
            await tx.execute(
                f"INSERT INTO mkb_executions ({shared}) VALUES ({placeholders})",
                (
                    child_uuid,
                    team_uuid,
                    task_uuid,
                    uuid7(),
                    1,
                    root_uuid,
                    root_uuid,
                    "scatter_child",
                    "required",
                    "intake_item",
                    uuid7(),
                    uuid7(),
                    uuid7(),
                    digest,
                    digest,
                    digest,
                    digest,
                    "mkbobj:cfg",
                    digest,
                    "ready",
                    now,
                    now,
                    "{}",
                    revision_uuid,
                    2,
                    change_set_uuid,
                ),
            )
            row = await tx.fetchone(
                "SELECT scatter_intake_revision_uuid,scatter_member_ordinal,scatter_change_set_uuid,payload_extra "
                "FROM mkb_executions WHERE execution_uuid=?",
                (child_uuid,),
            )
        assert row is not None
        assert row["scatter_intake_revision_uuid"] == revision_uuid
        assert row["scatter_member_ordinal"] == 2
        assert row["scatter_change_set_uuid"] == change_set_uuid
        assert row["payload_extra"] == "{}"
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_turso_empty_db_applies_full_migration_chain(tmp_path: Path) -> None:
    persistence = build_persistence(
        tmp_path / "mkb_primary.db",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
        async with persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT migration_id FROM mkb_schema_migrations ORDER BY migration_id"
            )
        applied = [row["migration_id"] for row in rows]
        expected = [item.migration_id for item in discover_migrations(Path("src/persistence/migrations"))]
        assert applied == expected
        assert "004_process_root_and_child_cancelled" in applied
        assert "005_candidate_admission_result" in applied
        assert "006_scatter_child_identity" in applied
    finally:
        await persistence.close()
