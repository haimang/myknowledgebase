"""NH2-T02: production selected-output CONTROL over a real registry and UoW."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.workflow.models import (
    WorkflowBindingSourceKind,
    WorkflowDefinition,
    WorkflowPortDefinition,
    WorkflowValueType,
)
from src.persistence.factory import build_persistence
from src.runtime.workflow.helpers import _compiled_workflow_digest
from src.runtime.workflow.runtime_materialize import WorkflowMaterializeMixin
from src.runtime.workflow_engine import WorkflowRuntime
from src.services.workflow_registry import WorkflowRegistryService
from tests.unit.test_nh1_selected_output_control import selected_output_test_graph


async def _seed(
    tmp_path: Path,
    name: str,
    *,
    graph: WorkflowDefinition | None = None,
    representation_facts: object | None = None,
):
    persistence = build_persistence(
        tmp_path / f"{name}.sqlite3",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    definition = graph or selected_output_test_graph()
    identity = await WorkflowRegistryService(persistence).register(definition)
    ids = {
        "team_uuid": uuid7(),
        "task_uuid": uuid7(),
        "trace_uuid": uuid7(),
        "execution_uuid": uuid7(),
    }
    now = utc_now()
    config_digest = stable_digest({"config": name})
    root_digest = stable_digest({"root": name})
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (ids["team_uuid"], name, stable_digest({"team": name}), now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_tasks(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,"
            "audit_bound,title,status,priority,current_generation,current_root_execution_uuid,received_at,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,1,?,'running','normal',1,?,?,?,?)",
            (
                ids["team_uuid"],
                ids["task_uuid"],
                ids["trace_uuid"],
                "mkb.task.v1",
                "intake.ingest",
                stable_digest({"task": name}),
                name,
                ids["execution_uuid"],
                now,
                now,
                now,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_executions(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,"
            "execution_role,target_kind,workflow_uuid,workflow_revision_uuid,compiled_digest,resolver_decision_digest,"
            "domain_binding_digest,s05_binding_digest,config_snapshot_ref,config_snapshot_digest,status,manifest_ref,"
            "manifest_digest,created_at,updated_at) VALUES (?,?,?,?,?,?,'root','task',?,?,?,?,?,?,?,?, 'running',?,?,?,?)",
            (
                ids["execution_uuid"],
                ids["team_uuid"],
                ids["task_uuid"],
                ids["trace_uuid"],
                1,
                ids["execution_uuid"],
                identity.workflow_uuid,
                identity.workflow_revision_uuid,
                identity.compiled_digest,
                stable_digest({"resolver": name}),
                stable_digest({"domain": name}),
                stable_digest({"legacy_s05": name}),
                f"mkbtest:config:{config_digest}",
                config_digest,
                f"mkbtest:root:{root_digest}",
                root_digest,
                now,
                now,
            ),
        )
    return (
        persistence,
        WorkflowRuntime(persistence, definition, representation_facts=representation_facts),  # type: ignore[arg-type]
        definition,
        identity,
        ids,
    )


async def _seed_candidate(
    persistence: object,
    identity: object,
    ids: dict[str, str],
    *,
    step_key: str,
    suffix: str,
) -> tuple[str, str]:
    process_uuid = uuid7()
    output_digest = stable_digest({"candidate": suffix})
    proof_digest = stable_digest({"proof": suffix})
    now = utc_now()
    async with persistence.transaction() as tx:  # type: ignore[attr-defined]
        step = await tx.fetchone(
            "SELECT workflow_step_uuid,process_key,process_contract_version,requiredness "
            "FROM mkb_workflow_steps WHERE workflow_revision_uuid=? AND step_key=?",
            (identity.workflow_revision_uuid, step_key),  # type: ignore[attr-defined]
        )
        assert step is not None
        await tx.execute(
            "INSERT INTO mkb_processes(process_uuid,team_uuid,execution_uuid,task_uuid,root_execution_uuid,"
            "workflow_step_uuid,step_key,process_key,process_contract_version,materialization_key,requiredness,"
            "process_spec_digest,config_snapshot_ref,config_snapshot_digest,proof_kind,status,row_revision,available_at,"
            "priority_rank,fencing_generation,max_retries,max_recoveries,backoff_policy_json,accepted_outcome_digest,"
            "output_manifest_ref,output_manifest_digest,proof_ref,proof_digest,completed_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,0,0,0,0,'{}',?,?,?,?,?,?,?,?,'{}')",
            (
                process_uuid,
                ids["team_uuid"],
                ids["execution_uuid"],
                ids["task_uuid"],
                ids["execution_uuid"],
                step["workflow_step_uuid"],
                step_key,
                step["process_key"],
                step["process_contract_version"],
                stable_digest({"materialization": suffix}),
                step["requiredness"],
                stable_digest({"spec": suffix}),
                "mkbtest:config",
                stable_digest({"config": "candidate"}),
                "clean_candidate",
                "succeeded",
                now,
                stable_digest({"outcome": suffix}),
                f"mkbtest:output:{suffix}",
                output_digest,
                f"mkbtest:proof:{suffix}",
                proof_digest,
                now,
                now,
                now,
            ),
        )
    return process_uuid, output_digest


async def _enter(runtime: WorkflowRuntime, definition: WorkflowDefinition, ids: dict[str, str]) -> bool:
    async with runtime.persistence.transaction() as tx:
        execution = await tx.fetchone("SELECT * FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],))
        assert execution is not None
        control = next(step for step in definition.steps if step.step_key == "merge")
        return await runtime._enter_selected_output_tx(  # noqa: SLF001
            tx,
            plan=definition,
            execution=execution,
            step=control,
            route_digest=stable_digest({"route": "candidate-to-control"}),
        )


def _fallback_graph() -> WorkflowDefinition:
    payload = selected_output_test_graph().model_dump()
    payload["workflow_key"] = "test.nh2.selected-output-fallback"
    payload["context_slots"] = [
        WorkflowPortDefinition(
            slot_name="root_candidate",
            value_type=WorkflowValueType.LOGICAL_REF,
            schema_ref="mkb.test.clean-candidate.v1",
        ).model_dump()
    ]
    merge = next(step for step in payload["steps"] if step["step_key"] == "merge")
    merge["control_fallback_port"] = "candidate_a"
    binding = next(
        item
        for item in payload["bindings"]
        if item["target_step_key"] == "merge" and item["target_slot_name"] == "candidate_a"
    )
    binding.update(
        {
            "source_kind": WorkflowBindingSourceKind.EXECUTION_CONTEXT,
            "source_ref_key": "root_candidate",
            "source_step_key": None,
            "source_port_name": None,
        }
    )
    return WorkflowDefinition.model_validate(payload)


@pytest.mark.asyncio
async def test_exactly_one_projects_canonical_output(tmp_path: Path) -> None:
    persistence, runtime, definition, identity, ids = await _seed(tmp_path, "exactly-one")
    try:
        _, output_digest = await _seed_candidate(
            persistence, identity, ids, step_key="candidate_a", suffix="candidate-a"
        )
        assert await _enter(runtime, definition, ids)
        async with persistence.transaction() as tx:
            selection = await tx.fetchone(
                "SELECT candidate_port,output_manifest_ref,output_manifest_digest FROM mkb_workflow_selected_outputs "
                "WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            tail = await tx.fetchone(
                "SELECT process_key,input_manifest_ref,input_manifest_digest FROM mkb_processes "
                "WHERE execution_uuid=? AND step_key='tail'",
                (ids["execution_uuid"],),
            )
        assert selection == {
            "candidate_port": "candidate_a",
            "output_manifest_ref": "mkbtest:output:candidate-a",
            "output_manifest_digest": output_digest,
        }
        assert tail == {
            "process_key": "test.publication_tail",
            "input_manifest_ref": "mkbtest:output:candidate-a",
            "input_manifest_digest": output_digest,
        }
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_zero_hit_fails_loud_without_fallback(tmp_path: Path) -> None:
    persistence, runtime, definition, _, ids = await _seed(tmp_path, "zero")
    try:
        assert not await _enter(runtime, definition, ids)
        async with persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT status,waiting_reason,final_error_code FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            tail = await tx.fetchall(
                "SELECT process_uuid FROM mkb_processes WHERE execution_uuid=? AND step_key='tail'",
                (ids["execution_uuid"],),
            )
        assert execution == {
            "status": "failed",
            "waiting_reason": None,
            "final_error_code": "workflow-selected-output-missing",
        }
        assert tail == []
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_double_hit_fails_integrity(tmp_path: Path) -> None:
    persistence, runtime, definition, identity, ids = await _seed(tmp_path, "double")
    try:
        await _seed_candidate(persistence, identity, ids, step_key="candidate_a", suffix="candidate-a")
        await _seed_candidate(persistence, identity, ids, step_key="candidate_b", suffix="candidate-b")
        assert not await _enter(runtime, definition, ids)
        async with persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT status,final_error_code FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            tail = await tx.fetchall(
                "SELECT process_uuid FROM mkb_processes WHERE execution_uuid=? AND step_key='tail'",
                (ids["execution_uuid"],),
            )
        assert execution == {"status": "failed", "final_error_code": "workflow-selected-output-conflict"}
        assert tail == []
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_unmaterialized_optional_is_absent_not_wait(tmp_path: Path) -> None:
    persistence, runtime, definition, identity, ids = await _seed(tmp_path, "optional-absent")
    try:
        await _seed_candidate(persistence, identity, ids, step_key="candidate_b", suffix="only-b")
        assert await _enter(runtime, definition, ids)
        async with persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT status,waiting_reason FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            candidate_a = await tx.fetchall(
                "SELECT process_uuid FROM mkb_processes WHERE execution_uuid=? AND step_key='candidate_a'",
                (ids["execution_uuid"],),
            )
        assert execution == {"status": "ready", "waiting_reason": None}
        assert candidate_a == []
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_registered_fallback_enters_compiled_digest(tmp_path: Path) -> None:
    no_fallback = selected_output_test_graph()
    fallback = _fallback_graph()
    assert _compiled_workflow_digest(no_fallback) != _compiled_workflow_digest(fallback)
    persistence, runtime, definition, _, ids = await _seed(tmp_path, "fallback", graph=fallback)
    try:
        assert await _enter(runtime, definition, ids)
        async with persistence.transaction() as tx:
            selection = await tx.fetchone(
                "SELECT candidate_port,fallback_used,output_manifest_ref FROM mkb_workflow_selected_outputs "
                "WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
        assert selection is not None
        assert selection["candidate_port"] == "candidate_a"
        assert selection["fallback_used"] == 1
        assert str(selection["output_manifest_ref"]).startswith("mkbtest:root:")
    finally:
        await persistence.close()


def test_does_not_call_scatter_join_wait() -> None:
    source = inspect.getsource(WorkflowMaterializeMixin._enter_selected_output_tx)
    forbidden = "_enter_" + "scatter_children_join_tx"
    assert forbidden not in source
    assert "waiting_reason" not in source
