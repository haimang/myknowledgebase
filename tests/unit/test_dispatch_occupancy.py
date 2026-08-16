"""Unit tests for occupancy querying arithmetic (NS2-T11)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.workflow.dispatch import get_pool_occupancies, get_waiting_count


@pytest.mark.asyncio
async def test_occupancy_three_counters_definition(tmp_path: Path) -> None:
    # NS2-T11: Insert 2 claimed local, 6 ready admitted local, 3 ready unadmitted generate.
    # Expect running=2, queued=6, waiting=3.
    db_path = tmp_path / "occupancy.sqlite3"
    persistence = SqlitePersistence(db_path, Path("src/persistence/migrations"))
    try:
        await persistence.migrate()
        async with persistence.transaction() as tx:
            await tx.execute(
                """
                INSERT INTO mkb_teams (team_uuid, name, creation_fingerprint, created_at, updated_at)
                VALUES ('team-1', 'Team 1', 'd'*64, '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z')
                """
            )
            await tx.execute(
                """
                INSERT INTO mkb_tasks (team_uuid, task_uuid, trace_uuid, schema_version, request_intent,
                                      creation_fingerprint, audit_bound, title, priority, status,
                                      current_generation, current_root_execution_uuid, received_at, created_at, updated_at)
                VALUES ('team-1', 'task-1', 'trace-1', 'mkb.task.v1', 'intake.ingest',
                        'd'*64, 1, 'Task 1', 'normal', 'queued', 1, 'exec-1', '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z')
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
                """
            )

            # 2 claimed local
            for i in range(2):
                await tx.execute(
                    """
                    INSERT INTO mkb_processes (process_uuid, team_uuid, execution_uuid, task_uuid, root_execution_uuid,
                                              workflow_step_uuid, step_key, process_key, process_contract_version,
                                              materialization_key, route_decision_digest, requiredness, process_spec_digest,
                                              input_manifest_ref, input_manifest_digest, control_snapshot_ref,
                                              config_snapshot_ref, config_snapshot_digest, proof_kind, status, row_revision,
                                              available_at, priority_rank, deadline_at, fencing_generation, max_retries,
                                              max_recoveries, backoff_policy_json, created_at, updated_at, payload_extra,
                                              dispatch_pool, dispatch_admitted, claim_token_hash, lease_owner, lease_expires_at)
                    VALUES (?, 'team-1', 'exec-1', 'task-1', 'exec-1', ?, 'sk-1', 'lsrag.construct', 'v1', ?, 'rd'*32,
                            'required', 'ps'*32, 'in-ref', 'in-dig'*16, 'ctl-ref', 'cfg-ref', 'cfg-dig'*16, 'proof',
                            'claimed', 0, '2026-08-15T00:00:00Z', 200, '2099-01-01T00:00:00Z', 0, 3, 3, '{}',
                            '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z', '{}', 'local-inference', 1,
                            'cth'*16, 'worker-1', '2099-01-01T00:00:00Z')
                    """,
                    (f"proc-claimed-{i}", f"ws-claimed-{i}", f"mk-claimed-{i}"),
                )

            # 6 ready admitted local
            for i in range(6):
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
                    VALUES (?, 'team-1', 'exec-1', 'task-1', 'exec-1', ?, 'sk-1', 'lsrag.construct', 'v1', ?, 'rd'*32,
                            'required', 'ps'*32, 'in-ref', 'in-dig'*16, 'ctl-ref', 'cfg-ref', 'cfg-dig'*16, 'proof',
                            'ready', 0, '2026-08-15T00:00:00Z', 200, '2099-01-01T00:00:00Z', 0, 3, 3, '{}',
                            '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z', '{}', 'local-inference', 1)
                    """,
                    (f"proc-queued-{i}", f"ws-queued-{i}", f"mk-queued-{i}"),
                )

            # 3 ready unadmitted generate
            for i in range(3):
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
                    VALUES (?, 'team-1', 'exec-1', 'task-1', 'exec-1', ?, 'sk-1', 'lsrag.construct', 'v1', ?, 'rd'*32,
                            'required', 'ps'*32, 'in-ref', 'in-dig'*16, 'ctl-ref', 'cfg-ref', 'cfg-dig'*16, 'proof',
                            'ready', 0, '2026-08-15T00:00:00Z', 200, '2099-01-01T00:00:00Z', 0, 3, 3, '{}',
                            '2026-08-15T00:00:00Z', '2026-08-15T00:00:00Z', '{}', NULL, 0)
                    """,
                    (f"proc-waiting-{i}", f"ws-waiting-{i}", f"mk-waiting-{i}"),
                )

            occupancies = await get_pool_occupancies(tx)
            assert occupancies["local-inference"].running == 2
            assert occupancies["local-inference"].queued == 6
            assert occupancies["non-interactive"].running == 0
            assert occupancies["non-interactive"].queued == 0
            assert occupancies["embed"].running == 0
            assert occupancies["embed"].queued == 0

            waiting = await get_waiting_count(tx)
            assert waiting == 3
    finally:
        await persistence.close()
