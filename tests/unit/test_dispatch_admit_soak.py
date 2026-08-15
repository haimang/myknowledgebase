"""NS2-T70: concurrent claim_next must never oversell pool running/queued caps."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.workflow.dispatch import (
    DISPATCH_EMBED_QUEUED_CAP,
    DISPATCH_EMBED_RUNNING_CAP,
    DISPATCH_LOCAL_QUEUED_CAP,
    DISPATCH_LOCAL_RUNNING_CAP,
    DISPATCH_NI_QUEUED_CAP,
    DISPATCH_NI_RUNNING_CAP,
    get_pool_occupancies,
)
from src.runtime.workflow.helpers import _compiled_workflow_digest
from src.runtime.workflow_engine import WorkflowRuntime
from src.workflows.builtin_lsrag import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW


async def _setup(tmp_path: Path):
    persistence = SqlitePersistence(tmp_path / "soak.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    runtime = WorkflowRuntime(persistence, BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, live_inference=True)
    now = utc_now()
    team_uuid = uuid7()
    definition = BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW
    compiled_digest = _compiled_workflow_digest(definition)
    workflow_uuid = uuid7()
    workflow_revision_uuid = uuid7()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid, name, creation_fingerprint, created_at, updated_at) "
            "VALUES (?, 'soak', 'd'*64, ?, ?)",
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
                stable_digest({"capabilities": "soak"}),
                stable_digest({"registration": "soak"}),
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


async def _insert(
    persistence: SqlitePersistence,
    team_uuid: str,
    *,
    workflow_uuid: str,
    workflow_revision_uuid: str,
    workflow_step_uuid: str,
    compiled_digest: str,
    process_key: str,
    step_key: str,
    priority: str,
    priority_rank: int,
) -> str:
    now = utc_now()
    proc_id = uuid7()
    task_id = uuid7()
    exec_id = uuid7()
    digest64 = "0" * 64
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_tasks (team_uuid, task_uuid, trace_uuid, schema_version, request_intent,"
            "creation_fingerprint, audit_bound, title, priority, status, current_generation,"
            "current_root_execution_uuid, received_at, created_at, updated_at) "
            "VALUES (?, ?, ?, 'mkb.task.v1', 'intake.ingest', ?, 1, 'soak', ?, 'queued', 1, ?, ?, ?, ?)",
            (team_uuid, task_id, uuid7(), digest64, priority, exec_id, now, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_executions (execution_uuid, team_uuid, task_uuid, trace_uuid, generation,"
            "root_execution_uuid, execution_role, target_kind, workflow_uuid, workflow_revision_uuid,"
            "compiled_digest, resolver_decision_digest, domain_binding_digest, s05_binding_digest,"
            "config_snapshot_ref, config_snapshot_digest, status, created_at, updated_at) "
            "VALUES (?, ?, ?, ?, 1, ?, 'primary', 'intake', ?, ?, ?, ?, ?, ?, 'cfg-ref', ?, 'running', ?, ?)",
            (
                exec_id,
                team_uuid,
                task_id,
                uuid7(),
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
            "INSERT INTO mkb_processes (process_uuid, team_uuid, execution_uuid, task_uuid, root_execution_uuid,"
            "workflow_step_uuid, step_key, process_key, process_contract_version, materialization_key,"
            "route_decision_digest, requiredness, process_spec_digest, input_manifest_ref, input_manifest_digest,"
            "control_snapshot_ref, config_snapshot_ref, config_snapshot_digest, proof_kind, status, row_revision,"
            "available_at, priority_rank, deadline_at, fencing_generation, max_retries, max_recoveries,"
            "backoff_policy_json, created_at, updated_at, payload_extra, dispatch_admitted) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'v1', ?, ?, 'required', ?, 'in-ref', ?, 'ctl-ref', 'cfg-ref', ?,"
            "'proof', 'ready', 0, ?, ?, '2026-08-16T00:00:00Z', 0, 3, 3, '{}', ?, ?, '{}', 0)",
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
                now,
                priority_rank,
                now,
                now,
            ),
        )
    return proc_id


@pytest.mark.asyncio
async def test_concurrent_claim_next_never_oversells_pool_caps(tmp_path: Path) -> None:
    # NS2-T70: 32 coroutines × 32 rounds; running/queued never exceed frozen caps
    persistence, runtime, team_uuid, compiled_digest, wf_uuid, wfr_uuid, step_map = await _setup(tmp_path)
    try:
        for _ in range(20):
            await _insert(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                process_key="lsrag.construct",
                step_key="construct",
                priority="normal",
                priority_rank=200,
            )
        for _ in range(10):
            await _insert(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["construct"],
                compiled_digest=compiled_digest,
                process_key="lsrag.construct",
                step_key="construct",
                priority="urgent",
                priority_rank=400,
            )
        for _ in range(30):
            await _insert(
                persistence,
                team_uuid,
                workflow_uuid=wf_uuid,
                workflow_revision_uuid=wfr_uuid,
                workflow_step_uuid=step_map["vectorize"],
                compiled_digest=compiled_digest,
                process_key="lsrag.vectorize",
                step_key="vectorize",
                priority="low",
                priority_rank=100,
            )

        for _round in range(32):
            claimed = await asyncio.gather(*[runtime.claim_next(f"soak-{_round}-{idx}") for idx in range(32)])
            async with persistence.transaction() as tx:
                occupancies = await get_pool_occupancies(tx)
            assert occupancies["local-inference"].running <= DISPATCH_LOCAL_RUNNING_CAP
            assert occupancies["local-inference"].queued <= DISPATCH_LOCAL_QUEUED_CAP
            assert occupancies["non-interactive"].running <= DISPATCH_NI_RUNNING_CAP
            assert occupancies["non-interactive"].queued <= DISPATCH_NI_QUEUED_CAP
            assert occupancies["embed"].running <= DISPATCH_EMBED_RUNNING_CAP
            assert occupancies["embed"].queued <= DISPATCH_EMBED_QUEUED_CAP
            if _round == 0:
                assert any(item is not None for item in claimed)
    finally:
        await persistence.close()
