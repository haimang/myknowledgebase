from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.workflow.dispatch import (
    DISPATCH_EMBED_RUNNING_CAP,
    DISPATCH_LOCAL_RUNNING_CAP,
    DISPATCH_NI_RUNNING_CAP,
    choose_pool,
    get_pool_occupancies,
)
from src.runtime.workflow.helpers import _compiled_workflow_digest
from src.runtime.workflow_engine import WorkflowRuntime
from src.services.billing import BillingPort
from src.workflows.builtin_lsrag import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW


class MockConfigurableBillingService(BillingPort):
    def __init__(self, allow_ni: bool = True) -> None:
        self.allow_ni = allow_ni

    def has_quota(self, channel: str) -> bool:
        if channel == "non-interactive":
            return self.allow_ni
        return True


async def _setup_mega_runtime(tmp_path: Path, *, billing: BillingPort | None = None, live: bool = True):
    db_path = tmp_path / "mega_runtime.sqlite3"
    persistence = SqlitePersistence(db_path, Path("src/persistence/migrations"))
    await persistence.migrate()
    runtime = WorkflowRuntime(
        persistence,
        BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        billing=billing,
        live_inference=live,
    )
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


async def _insert_process(
    persistence: SqlitePersistence,
    team_uuid: str,
    *,
    workflow_uuid: str,
    workflow_revision_uuid: str,
    workflow_step_uuid: str,
    compiled_digest: str,
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
                                      dispatch_pool, dispatch_admitted)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'v1', ?, ?,
                    'required', ?, 'in-ref', ?, 'ctl-ref', 'cfg-ref', ?, 'proof',
                    ?, 0, ?, ?, ?, 0, 3, 3, '{}',
                    ?, ?, '{}', ?, ?)
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
            ),
        )


def test_mega_matrix_policy_exhaustive() -> None:
    # NS2-T60: Exhaustive pure matrix coverage
    # (priority, local_queued, ni_queued, local_available, ni_quota, over_budget) -> expected pool
    cases = [
        # Urgent: always NI if ni_queued < 4 & quota
        ("urgent", 0, 0, True, True, False, "non-interactive"),
        ("urgent", 0, 3, True, True, False, "non-interactive"),
        ("urgent", 0, 4, True, True, False, None),
        ("urgent", 0, 0, True, False, False, None),  # no quota
        # High: always NI if ni_queued < 4 & quota
        ("high", 0, 0, True, True, False, "non-interactive"),
        ("high", 0, 3, True, True, False, "non-interactive"),
        ("high", 0, 4, True, True, False, None),
        ("high", 0, 0, True, False, False, None),  # no quota
        # Normal: local first, overflows to NI if local full / offline / over_budget
        ("normal", 0, 0, True, True, False, "local-inference"),
        ("normal", 5, 0, True, True, False, "local-inference"),
        ("normal", 6, 0, True, True, False, "non-interactive"),  # local full -> NI
        ("normal", 6, 4, True, True, False, None),  # both full -> wait
        ("normal", 0, 0, False, True, False, "non-interactive"),  # local offline -> NI
        ("normal", 0, 0, True, True, True, "non-interactive"),  # over budget -> NI
        ("normal", 6, 0, True, False, False, None),  # local full + no NI quota -> wait
        # Low: always local, never NI, waits when local full/offline
        ("low", 0, 0, True, True, False, "local-inference"),
        ("low", 5, 0, True, True, False, "local-inference"),
        ("low", 6, 0, True, True, False, None),  # local full -> wait (never NI)
        ("low", 0, 0, False, True, False, None),  # local offline -> wait (never NI)
        ("low", 0, 0, True, True, True, "local-inference"),  # over budget -> still local
    ]

    for prio, lq, nq, la, nquota, ob, expected in cases:
        pool = choose_pool(
            prio,
            "generate",
            local_queued=lq,
            ni_queued=nq,
            local_available=la,
            ni_quota=nquota,
            over_budget=ob,
        )
        assert pool == expected, f"Failed on case: ({prio}, lq={lq}, nq={nq}, la={la}, quota={nquota}, ob={ob})"


@pytest.mark.asyncio
async def test_soak_mixed_concurrent_claims(tmp_path: Path) -> None:
    # NS2-T61: Concurrency soak simulation with mixed tasks:
    # 4 urgent generate, 8 normal generate, 6 low generate, 12 embed, 5 unpooled
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup_mega_runtime(tmp_path)
    try:
        # 1. Insert 4 urgent generate
        for i in range(4):
            await _insert_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                proc_id=uuid7(),
                step_key="construct",
                process_key="lsrag.construct",
                priority="urgent",
                priority_rank=400,
                created_at=f"2026-08-15T00:00:{i:02d}Z",
            )

        # 2. Insert 8 normal generate
        for i in range(8):
            await _insert_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                proc_id=uuid7(),
                step_key="construct",
                process_key="lsrag.construct",
                priority="normal",
                priority_rank=200,
                created_at=f"2026-08-15T00:01:{i:02d}Z",
            )

        # 3. Insert 6 low generate
        for i in range(6):
            await _insert_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                proc_id=uuid7(),
                step_key="construct",
                process_key="lsrag.construct",
                priority="low",
                priority_rank=100,
                created_at=f"2026-08-15T00:02:{i:02d}Z",
            )

        # 4. Insert 12 embed
        for i in range(12):
            await _insert_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["vectorize"],
                compiled_digest=compiled_digest,
                proc_id=uuid7(),
                step_key="vectorize",
                process_key="lsrag.vectorize",
                priority="normal",
                priority_rank=200,
                created_at=f"2026-08-15T00:03:{i:02d}Z",
            )

        # 5. Insert 5 unpooled
        for i in range(5):
            await _insert_process(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["validate_publication"],
                compiled_digest=compiled_digest,
                proc_id=uuid7(),
                step_key="validate_publication",
                process_key="index.validate_publication",
                priority="normal",
                priority_rank=200,
                created_at=f"2026-08-15T00:04:{i:02d}Z",
            )

        # Simulate concurrent worker claims
        claimed_processes = []
        for worker_idx in range(50):
            claimed = await runtime.claim_next(f"soak-worker-{worker_idx}")
            if claimed is not None:
                claimed_processes.append(claimed)

        # Verify pool occupancy invariant: running count never exceeds pool running cap
        async with persistence.transaction() as tx:
            occupancies = await get_pool_occupancies(tx)
            assert occupancies["local-inference"].running <= DISPATCH_LOCAL_RUNNING_CAP == 2
            assert occupancies["non-interactive"].running <= DISPATCH_NI_RUNNING_CAP == 2
            assert occupancies["embed"].running <= DISPATCH_EMBED_RUNNING_CAP == 8

        # 2 local + 2 NI + 8 embed + 5 unpooled = 17 claimed processes
        assert len(claimed_processes) == 17
    finally:
        await persistence.close()
