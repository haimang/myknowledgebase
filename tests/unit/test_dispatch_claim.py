"""Unit tests for same-transaction admit, pool-aware claim_next, embed FIFO, and deadline checks (NS2-T20..T27)."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.workflow.helpers import _compiled_workflow_digest
from src.runtime.workflow_engine import WorkflowRuntime
from src.workflows.builtin_lsrag import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW


async def _setup_runtime(tmp_path: Path):
    db_path = tmp_path / "dispatch_claim.sqlite3"
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


async def _insert_task_and_process(
    persistence: SqlitePersistence,
    team_uuid: str,
    *,
    workflow_uuid: str,
    workflow_revision_uuid: str,
    workflow_step_uuid: str,
    compiled_digest: str,
    task_id: str,
    exec_id: str,
    proc_id: str,
    step_key: str = "construct",
    process_key: str = "lsrag.construct",
    priority: str = "normal",
    priority_rank: int = 200,
    created_at: str = "2026-08-15T00:00:00Z",
    available_at: str = "2026-08-15T00:00:00Z",
    deadline_at: str = "2026-08-16T00:00:00Z",
    status: str = "ready",
    dispatch_pool: str | None = None,
    dispatch_admitted: int = 0,
    claim_token_hash: str | None = None,
    lease_owner: str | None = None,
    lease_expires_at: str | None = None,
):
    now = utc_now()
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
            ON CONFLICT DO NOTHING
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
            ON CONFLICT DO NOTHING
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
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'v1', ?, ?,
                    'required', ?, 'in-ref', ?, 'ctl-ref', 'cfg-ref', ?, 'proof',
                    ?, 0, ?, ?, ?, 0, 3, 3, '{}',
                    ?, ?, '{}', ?, ?, ?, ?, ?)
            """,
            (
                proc_id,
                team_uuid,
                exec_id,
                task_id,
                exec_id,
                workflow_step_uuid,
                step_key,
                process_key,
                f"mk-{proc_id}",
                digest64,
                digest64,
                digest64,
                digest64,
                status,
                available_at,
                priority_rank,
                deadline_at,
                created_at,
                created_at,
                dispatch_pool,
                dispatch_admitted,
                claim_token_hash,
                lease_owner,
                lease_expires_at,
            ),
        )


@pytest.mark.asyncio
async def test_claim_next_same_transaction_admit(tmp_path: Path) -> None:
    # NS2-T20: single waiting generate process is admitted and claimed in same transaction
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_runtime(tmp_path)
    proc_uuid = uuid7()
    try:
        await _insert_task_and_process(
            persistence,
            team_uuid,
            workflow_uuid=wf_uuid,
            workflow_revision_uuid=wfr_uuid,
            workflow_step_uuid=step_map["construct"],
            compiled_digest=compiled_digest,
            task_id=uuid7(),
            exec_id=uuid7(),
            proc_id=proc_uuid,
            priority="normal",
            priority_rank=200,
        )

        claimed = await runtime.claim_next("worker-1")
        assert claimed is not None
        assert claimed.command.process_uuid == proc_uuid

        async with persistence.transaction() as tx:
            proc = await tx.fetchone("SELECT status, dispatch_pool, dispatch_admitted FROM mkb_processes WHERE process_uuid=?", (proc_uuid,))
            assert proc == {"status": "claimed", "dispatch_pool": "local-inference", "dispatch_admitted": 1}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_local_queued_cap_bounds_admission(tmp_path: Path) -> None:
    # NS2-T21: 7 normal generate tasks. 6 are admitted to local-inference (cap=6),
    # 7th overflows to non-interactive (cap=4).
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_runtime(tmp_path)
    proc_ids = [uuid7() for _ in range(11)]
    try:
        for i in range(11):
            await _insert_task_and_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                task_id=uuid7(),
                exec_id=uuid7(),
                proc_id=proc_ids[i],
                priority="normal",
                priority_rank=200,
                created_at=f"2026-08-15T00:00:{i:02d}Z",
            )

        # Trigger admission via claim_next
        claimed = await runtime.claim_next("worker-1")
        assert claimed is not None

        async with persistence.transaction() as tx:
            local_admitted = await tx.fetchall("SELECT process_uuid FROM mkb_processes WHERE dispatch_pool='local-inference' AND dispatch_admitted=1")
            ni_admitted = await tx.fetchall("SELECT process_uuid FROM mkb_processes WHERE dispatch_pool='non-interactive' AND dispatch_admitted=1")
            unadmitted = await tx.fetchall("SELECT process_uuid FROM mkb_processes WHERE dispatch_admitted=0")

            assert len(local_admitted) == 6
            assert len(ni_admitted) == 4
            assert len(unadmitted) == 1
            assert unadmitted[0]["process_uuid"] == proc_ids[10]
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_local_running_cap_stops_claiming_without_sleeping(tmp_path: Path) -> None:
    # NS2-T22 & NS2-T27: local_running cap is 2. Claiming 2 processes succeeds; 3rd returns None immediately.
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_runtime(tmp_path)
    proc_ids = [uuid7() for _ in range(5)]
    try:
        for i in range(5):
            await _insert_task_and_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                task_id=uuid7(),
                exec_id=uuid7(),
                proc_id=proc_ids[i],
                priority="low",  # Low always stays in local pool
                priority_rank=100,
                created_at=f"2026-08-15T00:00:{i:02d}Z",
            )

        # 1st claim -> succeeds (local running: 1)
        c1 = await runtime.claim_next("worker-1")
        assert c1 is not None and c1.command.process_uuid == proc_ids[0]

        # 2nd claim -> succeeds (local running: 2)
        c2 = await runtime.claim_next("worker-2")
        assert c2 is not None and c2.command.process_uuid == proc_ids[1]

        # 3rd claim -> local pool running cap (2) reached, returns None immediately without waiting
        c3 = await runtime.claim_next("worker-3")
        assert c3 is None
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_embed_fifo_claim_ignores_priority_rank(tmp_path: Path) -> None:
    # NS2-T25: Low priority embed arriving at T0 must be claimed BEFORE Urgent priority embed arriving at T1.
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_runtime(tmp_path)
    proc_low = uuid7()
    proc_urgent = uuid7()
    try:
        # Low embed arrives earlier
        await _insert_task_and_process(
            persistence,
            team_uuid,
            workflow_uuid=wf_uuid,
            workflow_revision_uuid=wfr_uuid,
            workflow_step_uuid=step_map["vectorize"],
            compiled_digest=compiled_digest,
            task_id=uuid7(),
            exec_id=uuid7(),
            proc_id=proc_low,
            step_key="vectorize",
            process_key="lsrag.vectorize",
            priority="low",
            priority_rank=100,
            available_at="2026-08-15T00:00:01Z",
            created_at="2026-08-15T00:00:01Z",
        )
        # Urgent embed arrives later
        await _insert_task_and_process(
            persistence,
            team_uuid,
            workflow_uuid=wf_uuid,
            workflow_revision_uuid=wfr_uuid,
            workflow_step_uuid=step_map["vectorize"],
            compiled_digest=compiled_digest,
            task_id=uuid7(),
            exec_id=uuid7(),
            proc_id=proc_urgent,
            step_key="vectorize",
            process_key="lsrag.vectorize",
            priority="urgent",
            priority_rank=400,
            available_at="2026-08-15T00:00:02Z",
            created_at="2026-08-15T00:00:02Z",
        )

        claimed = await runtime.claim_next("worker-1")
        assert claimed is not None
        # First claimed MUST be p-low because embed is strictly FIFO
        assert claimed.command.process_uuid == proc_low
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_unadmitted_waiting_process_fails_on_deadline_elapsed(tmp_path: Path) -> None:
    # NS2-T26: Waiting process with deadline elapsed is failed with deadline-exceeded-before-start
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_runtime(tmp_path)
    proc_expired = uuid7()
    try:
        await _insert_task_and_process(
            persistence,
            team_uuid,
            workflow_uuid=wf_uuid,
            workflow_revision_uuid=wfr_uuid,
            workflow_step_uuid=step_map["construct"],
            compiled_digest=compiled_digest,
            task_id=uuid7(),
            exec_id=uuid7(),
            proc_id=proc_expired,
            deadline_at="2020-01-01T00:00:00Z",  # in the past
            dispatch_admitted=0,
        )

        claimed = await runtime.claim_next("worker-1")
        assert claimed is None

        async with persistence.transaction() as tx:
            proc = await tx.fetchone("SELECT status, error_code FROM mkb_processes WHERE process_uuid=?", (proc_expired,))
            assert proc == {"status": "failed", "error_code": "deadline-exceeded-before-start"}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_unadmitted_process_never_claimed(tmp_path: Path) -> None:
    # NS2-T23: Unadmitted waiting processes are NEVER claimed when pool caps are filled
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_runtime(tmp_path)
    proc_overflow = uuid7()
    try:
        # Fill local queued capacity: 2 running (claimed) + 6 queued (ready admitted) = 8
        for i in range(2):
            await _insert_task_and_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                task_id=uuid7(),
                exec_id=uuid7(),
                proc_id=uuid7(),
                status="claimed",
                dispatch_pool="local-inference",
                dispatch_admitted=1,
                claim_token_hash="0" * 64,
                lease_owner="worker-other",
                lease_expires_at="2026-08-16T00:00:00Z",
                created_at=f"2026-08-15T00:00:{i:02d}Z",
            )
        for i in range(2, 8):
            await _insert_task_and_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                task_id=uuid7(),
                exec_id=uuid7(),
                proc_id=uuid7(),
                status="ready",
                dispatch_pool="local-inference",
                dispatch_admitted=1,
                created_at=f"2026-08-15T00:00:{i:02d}Z",
            )
        # 9th low priority process (cannot overflow to NI because priority is low; cannot enter local because queued=6 is full)
        await _insert_task_and_process(
            persistence,
            team_uuid,
            workflow_uuid=wf_uuid,
            workflow_revision_uuid=wfr_uuid,
            workflow_step_uuid=step_map["construct"],
            compiled_digest=compiled_digest,
            task_id=uuid7(),
            exec_id=uuid7(),
            proc_id=proc_overflow,
            priority="low",
            priority_rank=100,
            status="ready",
            dispatch_admitted=0,
            created_at="2026-08-15T00:01:00Z",
        )

        # Claim attempt -> running cap is 2 (occupied), returns None; overflow row remains admitted=0
        c = await runtime.claim_next("worker-1")
        assert c is None

        async with persistence.transaction() as tx:
            overflow_row = await tx.fetchone("SELECT status, dispatch_admitted FROM mkb_processes WHERE process_uuid=?", (proc_overflow,))
            assert overflow_row == {"status": "ready", "dispatch_admitted": 0}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_unpooled_preserves_s03_priority_ordering(tmp_path: Path) -> None:
    # NS2-T24: Unpooled processes strictly follow S03 priority rank ordering
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_runtime(tmp_path)
    proc_normal = uuid7()
    proc_urgent = uuid7()
    try:
        # Normal unpooled arrives first at T0
        await _insert_task_and_process(
            persistence,
            team_uuid,
            workflow_uuid=wf_uuid,
            workflow_revision_uuid=wfr_uuid,
            workflow_step_uuid=step_map["validate_publication"],
            compiled_digest=compiled_digest,
            task_id=uuid7(),
            exec_id=uuid7(),
            proc_id=proc_normal,
            step_key="validate_publication",
            process_key="index.validate_publication",  # unpooled
            priority="normal",
            priority_rank=200,
            created_at="2026-08-15T00:00:01Z",
        )
        # Urgent unpooled arrives later at T1
        await _insert_task_and_process(
            persistence,
            team_uuid,
            workflow_uuid=wf_uuid,
            workflow_revision_uuid=wfr_uuid,
            workflow_step_uuid=step_map["validate_publication"],
            compiled_digest=compiled_digest,
            task_id=uuid7(),
            exec_id=uuid7(),
            proc_id=proc_urgent,
            step_key="validate_publication",
            process_key="index.validate_publication",  # unpooled
            priority="urgent",
            priority_rank=400,
            created_at="2026-08-15T00:00:02Z",
        )

        # First claimed must be Urgent because priority_rank is higher
        claimed = await runtime.claim_next("worker-1")
        assert claimed is not None
        assert claimed.command.process_uuid == proc_urgent
    finally:
        await persistence.close()
