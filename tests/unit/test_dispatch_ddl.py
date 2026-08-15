"""Unit/integration tests for migration 011_process_dispatch_pools (NS2-T10)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.persistence.sqlite_port import SqlitePersistence


@pytest.mark.asyncio
async def test_migration_011_applies_to_fresh_database(tmp_path: Path) -> None:
    db_path = tmp_path / "fresh_011.sqlite3"
    migrations_dir = Path("src/persistence/migrations")
    persistence = SqlitePersistence(db_path, migrations_dir)
    try:
        await persistence.migrate()
        async with persistence.transaction() as tx:
            columns_info = await tx.fetchall("PRAGMA table_info(mkb_processes)")
            cols = {row["name"]: row for row in columns_info}
            assert "dispatch_pool" in cols
            assert "dispatch_admitted" in cols
            assert "dispatch_enqueued_at" in cols
            assert cols["dispatch_admitted"]["dflt_value"] == "0"
            assert cols["dispatch_admitted"]["notnull"] == 1

            indexes = await tx.fetchall("PRAGMA index_list(mkb_processes)")
            index_names = {row["name"] for row in indexes}
            assert "ix_mkb_proc_dispatch_ready" in index_names
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_migration_011_check_constraint_rejects_illegal_pool(tmp_path: Path) -> None:
    db_path = tmp_path / "check_pool.sqlite3"
    migrations_dir = Path("src/persistence/migrations")
    persistence = SqlitePersistence(db_path, migrations_dir)
    try:
        await persistence.migrate()
        async with persistence.transaction() as tx:
            # Legal pools
            for pool in (None, "local-inference", "non-interactive", "embed"):
                await tx.execute(
                    """
                    INSERT INTO mkb_teams (team_uuid, name, creation_fingerprint, created_at, updated_at)
                    VALUES ('team-1', 'Team 1', 'd'*64, '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z')
                    ON CONFLICT DO NOTHING
                    """
                )
                await tx.execute(
                    """
                    INSERT INTO mkb_tasks (team_uuid, task_uuid, trace_uuid, schema_version, request_intent,
                                          creation_fingerprint, audit_bound, title, priority, status,
                                          current_generation, current_root_execution_uuid, received_at, created_at, updated_at)
                    VALUES ('team-1', 'task-1', 'trace-1', 'mkb.task.v1', 'intake.ingest',
                            'd'*64, 1, 'Task 1', 'normal', 'queued', 1, 'exec-1', '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z')
                    ON CONFLICT DO NOTHING
                    """
                )
                await tx.execute(
                    """
                    INSERT INTO mkb_executions (execution_uuid, team_uuid, task_uuid, trace_uuid, generation,
                                               root_execution_uuid, execution_role, target_kind, workflow_uuid,
                                               workflow_revision_uuid, compiled_digest, resolver_decision_digest,
                                               domain_binding_digest, s05_binding_digest, config_snapshot_ref,
                                               config_snapshot_digest, status, created_at, updated_at)
                    VALUES ('exec-1', 'team-1', 'task-1', 'trace-1', 1, 'exec-1', 'primary', 'intake',
                            'w1', 'wr1', 'cd'*32, 'rd'*32, 'db'*32, 's5'*32, 'cfg-ref', 'cfg-dig'*16,
                            'running', '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z')
                    ON CONFLICT DO NOTHING
                    """
                )
                proc_uuid = f"proc-{pool or 'none'}"
                step_uuid = f"ws-{pool or 'none'}"
                mat_key = f"mk-{pool or 'none'}"
                await tx.execute(
                    """
                    INSERT INTO mkb_processes (process_uuid, team_uuid, execution_uuid, task_uuid, root_execution_uuid,
                                              workflow_step_uuid, step_key, process_key, process_contract_version,
                                              materialization_key, route_decision_digest, requiredness, process_spec_digest,
                                              input_manifest_ref, input_manifest_digest, control_snapshot_ref,
                                              config_snapshot_ref, config_snapshot_digest, proof_kind, status, row_revision,
                                              available_at, priority_rank, deadline_at, fencing_generation, max_retries,
                                              max_recoveries, backoff_policy_json, created_at, updated_at, payload_extra,
                                              dispatch_pool, dispatch_admitted)
                    VALUES (?, 'team-1', 'exec-1', 'task-1', 'exec-1', ?, 'sk-1', 'pk-1', 'v1', ?, 'rd'*32,
                            'required', 'ps'*32, 'in-ref', 'in-dig'*16, 'ctl-ref', 'cfg-ref', 'cfg-dig'*16, 'proof',
                            'ready', 0, '2026-08-15T00:00:00Z', 200, '2026-08-16T00:00:00Z', 0, 3, 3, '{}',
                            '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z', '{}', ?, 0)
                    """,
                    (proc_uuid, step_uuid, mat_key, pool),
                )

            # Illegal pool: cloud-inference or invalid string rejected by CHECK
            with pytest.raises((sqlite3.IntegrityError, Exception)):
                await tx.execute(
                    """
                    INSERT INTO mkb_processes (process_uuid, team_uuid, execution_uuid, task_uuid, root_execution_uuid,
                                              workflow_step_uuid, step_key, process_key, process_contract_version,
                                              materialization_key, route_decision_digest, requiredness, process_spec_digest,
                                              input_manifest_ref, input_manifest_digest, control_snapshot_ref,
                                              config_snapshot_ref, config_snapshot_digest, proof_kind, status, row_revision,
                                              available_at, priority_rank, deadline_at, fencing_generation, max_retries,
                                              max_recoveries, backoff_policy_json, created_at, updated_at, payload_extra,
                                              dispatch_pool, dispatch_admitted)
                    VALUES ('proc-illegal', 'team-1', 'exec-1', 'task-1', 'exec-1', 'ws-illegal', 'sk-1', 'pk-1', 'v1', 'mk-illegal', 'rd'*32,
                            'required', 'ps'*32, 'in-ref', 'in-dig'*16, 'ctl-ref', 'cfg-ref', 'cfg-dig'*16, 'proof',
                            'ready', 0, '2026-08-15T00:00:00Z', 200, '2026-08-16T00:00:00Z', 0, 3, 3, '{}',
                            '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z', '{}', 'cloud-inference', 0)
                    """
                )
    finally:
        await persistence.close()
