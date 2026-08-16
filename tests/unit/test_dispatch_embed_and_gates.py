"""Unit tests for vectorize stage pool admission, FIFO, Facade concurrency gate, and backpressure recovery (NS2-T50..T53)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.inference.facade import ConcurrencyGate
from src.runtime.workflow.dispatch import (
    DISPATCH_EMBED_QUEUED_CAP,
    DISPATCH_EMBED_RUNNING_CAP,
    pool_kind,
)
from src.runtime.workflow.helpers import _compiled_workflow_digest
from src.runtime.workflow_engine import WorkflowRuntime
from src.workflows.builtin_lsrag import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW


async def _setup_runtime(tmp_path: Path):
    db_path = tmp_path / "embed_runtime.sqlite3"
    persistence = SqlitePersistence(db_path, Path("src/persistence/migrations"))
    await persistence.migrate()
    runtime = WorkflowRuntime(persistence, BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW)
    now = utc_now()
    team_uuid = uuid7()
    definition = BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW
    compiled_digest = _compiled_workflow_digest(definition)
    workflow_uuid = uuid7()
    workflow_revision_uuid = uuid7()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid, name, creation_fingerprint, created_at, updated_at) "
            "VALUES (?, 'Team', 'd'*64, ?, ?)",
            (team_uuid, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_workflow_registry "
            "(workflow_uuid,workflow_key,purpose_key,execution_role,active_revision_uuid,created_at,updated_at,created_by_origin) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                workflow_uuid,
                definition.workflow_key,
                definition.purpose_key,
                definition.execution_role.value,
                workflow_revision_uuid,
                now,
                now,
                "test",
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_workflow_revisions "
            "(workflow_revision_uuid,workflow_uuid,revision_number,schema_version,capability_registry_digest,"
            "registration_fingerprint,canonical_definition_digest,compiled_digest,registered_at) "
            "VALUES (?,?,?,?,?,?,?,?,?)",
            (
                workflow_revision_uuid,
                workflow_uuid,
                definition.revision_number,
                definition.schema_version,
                stable_digest({"capabilities": "test"}),
                stable_digest({"registration": "test"}),
                compiled_digest,
                compiled_digest,
                now,
            ),
        )
        step_map: dict[str, str] = {}
        for order_hint, step in enumerate(definition.steps):
            step_uuid = uuid7()
            step_map[step.step_key] = step_uuid
            await tx.execute(
                "INSERT INTO mkb_workflow_steps "
                "(workflow_step_uuid,workflow_revision_uuid,step_key,step_kind,process_key,process_contract_version,"
                "phase_key,requiredness,terminal_kind,order_hint) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    step_uuid,
                    workflow_revision_uuid,
                    step.step_key,
                    step.step_kind.value,
                    step.process_key,
                    step.contract_version,
                    None if step.phase_key is None else step.phase_key.value,
                    step.requiredness.value,
                    None if step.terminal_kind is None else step.terminal_kind.value,
                    order_hint,
                ),
            )
    return persistence, runtime, team_uuid, compiled_digest, workflow_uuid, workflow_revision_uuid, step_map


async def _insert_embed_process(
    persistence: SqlitePersistence,
    team_uuid: str,
    *,
    workflow_uuid: str,
    workflow_revision_uuid: str,
    workflow_step_uuid: str,
    compiled_digest: str,
    proc_id: str,
    priority: str = "normal",
    priority_rank: int = 200,
    created_at: str = "2026-08-15T00:00:00Z",
    available_at: str = "2026-08-15T00:00:00Z",
    status: str = "ready",
    dispatch_pool: str | None = None,
    dispatch_admitted: int = 0,
    claim_token_hash: str | None = None,
    lease_owner: str | None = None,
    lease_expires_at: str | None = None,
):
    now = utc_now()
    task_id = uuid7()
    exec_id = uuid7()
    trace_uuid = uuid7()
    digest64 = "0" * 64
    async with persistence.transaction() as tx:
        await tx.execute(
            """
            INSERT INTO mkb_tasks (team_uuid, task_uuid, trace_uuid, schema_version, request_intent,
                                  creation_fingerprint, audit_bound, title, priority, status,
                                  current_generation, current_root_execution_uuid, received_at, created_at, updated_at)
            VALUES (?, ?, ?, 'mkb.task.v1', 'intake.ingest',
                    ?, 1, 'Task', ?, 'queued', 1, ?, ?, ?, ?)
            """,
            (team_uuid, task_id, trace_uuid, digest64, priority, exec_id, now, now, now),
        )
        await tx.execute(
            """
            INSERT INTO mkb_executions (execution_uuid, team_uuid, task_uuid, trace_uuid, generation,
                                       root_execution_uuid, execution_role, target_kind, workflow_uuid,
                                       workflow_revision_uuid, compiled_digest, resolver_decision_digest,
                                       domain_binding_digest, s05_binding_digest, config_snapshot_ref,
                                       config_snapshot_digest, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, 1, ?, 'primary', 'intake',
                    ?, ?, ?, ?, ?, ?, 'cfg-ref', ?,
                    'running', ?, ?)
            """,
            (
                exec_id,
                team_uuid,
                task_id,
                trace_uuid,
                exec_id,
                workflow_uuid,
                workflow_revision_uuid,
                compiled_digest,
                digest64,
                digest64,
                digest64,
                digest64,
                now,
                now,
            ),
        )
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
            VALUES (?, ?, ?, ?, ?, ?, 'vectorize', 'lsrag.vectorize', 'v1', ?, ?,
                    'required', ?, 'in-ref', ?, 'ctl-ref', 'cfg-ref', ?, 'proof',
                    ?, 0, ?, ?, '2099-01-01T00:00:00Z', 0, 3, 3, '{}',
                    ?, ?, '{}', ?, ?, ?, ?, ?)
            """,
            (
                proc_id,
                team_uuid,
                exec_id,
                task_id,
                exec_id,
                workflow_step_uuid,
                f"mk-{proc_id}",
                digest64,
                digest64,
                digest64,
                digest64,
                status,
                available_at,
                priority_rank,
                created_at,
                created_at,
                dispatch_pool,
                dispatch_admitted,
                claim_token_hash,
                lease_owner,
                lease_expires_at,
            ),
        )


def test_vectorize_pool_kind_classification() -> None:
    # NS2-T50: vectorize is classified as embed pool in live mode, unpooled in deterministic mode
    assert pool_kind("lsrag.vectorize") == "embed"
    assert pool_kind("lsrag.vectorize", {"l2": {"inference_mode": "live"}}) == "embed"
    assert pool_kind("lsrag.vectorize", {"l2": {"inference_mode": "deterministic"}}) == "unpooled"


@pytest.mark.asyncio
async def test_embed_pool_concurrency_bounds_and_fifo(tmp_path: Path) -> None:
    # NS2-T51: Embed pool has cap running=8, queued=20.
    # We test admitting up to 20 queued processes, then verifying that the 21st process remains unadmitted.
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_runtime(tmp_path)
    proc_ids = [uuid7() for _ in range(25)]
    try:
        for i in range(25):
            await _insert_embed_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["vectorize"],
                compiled_digest=compiled_digest,
                proc_id=proc_ids[i],
                priority="normal",
                created_at=f"2026-08-15T00:00:{i:02d}Z",
                available_at=f"2026-08-15T00:00:{i:02d}Z",
            )

        # Trigger admission via claim_next
        c1 = await runtime.claim_next("worker-1")
        assert c1 is not None

        async with persistence.transaction() as tx:
            admitted = await tx.fetchall("SELECT process_uuid FROM mkb_processes WHERE dispatch_pool='embed' AND dispatch_admitted=1")
            unadmitted = await tx.fetchall("SELECT process_uuid FROM mkb_processes WHERE dispatch_admitted=0")
            assert len(admitted) == DISPATCH_EMBED_QUEUED_CAP  # 20 admitted
            assert len(unadmitted) == 5  # 5 remain in orchestrator

        # Next 7 claims succeed (running: 1 -> 8)
        claimed_ids = [c1.command.process_uuid]
        for w in range(2, 9):
            c = await runtime.claim_next(f"worker-{w}")
            assert c is not None
            claimed_ids.append(c.command.process_uuid)

        assert len(claimed_ids) == DISPATCH_EMBED_RUNNING_CAP  # 8 claimed
        # Strict FIFO order verified
        assert claimed_ids == proc_ids[:8]

        # 9th claim returns None because embed running cap (8) is saturated
        c9 = await runtime.claim_next("worker-9")
        assert c9 is None
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_facade_concurrency_gate_limits_and_backpressure() -> None:
    # NS2-T52 & NS2-T53: ConcurrencyGate enforces global 12, embed 8, structured_generate 2, text_generate 2
    gate = ConcurrencyGate(12, capability_limits={"embed": 8, "structured_generate": 2, "text_generate": 2})

    # Acquire 8 embed leases
    embed_leases = []
    for _ in range(8):
        lease = await gate.try_acquire("embed")
        assert lease is not None
        embed_leases.append(lease)

    # 9th embed attempt is rejected (backpressure)
    assert await gate.try_acquire("embed") is None

    # Acquire 2 structured_generate leases
    gen_leases = []
    for _ in range(2):
        lease = await gate.try_acquire("structured_generate")
        assert lease is not None
        gen_leases.append(lease)

    # 3rd structured_generate attempt is rejected
    assert await gate.try_acquire("structured_generate") is None

    # Acquire 2 text_generate leases (total now = 8 + 2 + 2 = 12)
    text_leases = []
    for _ in range(2):
        lease = await gate.try_acquire("text_generate")
        assert lease is not None
        text_leases.append(lease)

    # Global limit 12 reached
    assert await gate.try_acquire("text_generate") is None

    # Release 1 embed lease -> can acquire 1 embed again (recoverability)
    await gate.release(embed_leases.pop())
    new_embed_lease = await gate.try_acquire("embed")
    assert new_embed_lease is not None

    # Clean up all leases
    for lease in (*embed_leases, new_embed_lease, *gen_leases, *text_leases):
        await gate.release(lease)
