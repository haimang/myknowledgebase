"""D02 review residual fixes (R1–R3): CandidateSet edges, typed routing, Execution ownership."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from src.contracts.api.models import ExpectedRevisionRequest, GateDecisionRequest
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.workflow.models import WorkflowOutcomeSelector
from src.runtime.intake.core import IntakeCoreMixin
from src.runtime.intake.pipeline import IntakePipeline
from src.runtime.task.task_commands import TaskCommandsMixin
from src.runtime.task.task_projections import TaskProjectionsMixin
from src.runtime.task_service import TaskService
from src.services.events import DomainEventWriter
from src.services.teams import TeamService
from src.workflows.lsrag_definition import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW
from tests.unit.test_task_projections import _open_gate, _service
from tests.unit.test_workflow_runtime import _seed_runtime


def _command(**overrides: object) -> ProcessCommand:
    base = {
        "schema_version": "mkb.process-command.v1",
        "team_uuid": uuid7(),
        "task_uuid": uuid7(),
        "trace_uuid": uuid7(),
        "execution_uuid": uuid7(),
        "process_uuid": uuid7(),
        "process_key": "intake.collection.seal",
        "process_contract_version": "v1",
        "fencing_generation": 1,
        "command_input_digest": "c" * 64,
        "input_manifest_ref": "mkbtest:input:x",
        "input_manifest_digest": "a" * 64,
        "config_snapshot_ref": "mkbtest:config:x",
        "config_snapshot_digest": "b" * 64,
        "binding_digest": "d" * 64,
    }
    base.update(overrides)
    return ProcessCommand.model_validate(base)


async def _insert_intake_source(tx, *, team_uuid: str, source_uuid: str) -> str:
    now = utc_now()
    definition = await tx.fetchone(
        "SELECT definition_digest FROM mkb_source_kind_definitions "
        "WHERE source_kind='inline_payload' AND definition_version='v1'"
    )
    assert definition is not None
    digest = definition["definition_digest"]
    descriptor = stable_digest({"source": source_uuid})
    await tx.execute(
        "INSERT INTO mkb_intake_sources "
        "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
        "source_descriptor_ref,source_descriptor_digest,created_at,updated_at,payload_extra) "
        "VALUES (?,?,'inline_payload','v1',?,'mkbobj:v1:source',?,?,?,'{}')",
        (team_uuid, source_uuid, digest, descriptor, now, now),
    )
    return digest


# ---------------------------------------------------------------------------
# R1 — CandidateSet open → sealed → accepted; abandon; no INSERT-accepted
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r1_seal_inserts_open_then_preflight_cas_seals(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    source_uuid = uuid7()
    candidate_uuid = uuid7()
    async with persistence.transaction() as tx:
        await _insert_intake_source(tx, team_uuid=ids["team_uuid"], source_uuid=source_uuid)

    pipeline = IntakePipeline(persistence, None, None)  # type: ignore[arg-type]
    producer_execution = uuid7()
    command = _command(
        team_uuid=ids["team_uuid"],
        task_uuid=ids["task_uuid"],
        trace_uuid=ids["trace_uuid"],
        execution_uuid=producer_execution,
        process_key="intake.collection.seal",
    )
    state = {
        "intake_source_uuid": source_uuid,
        "candidate_set_uuid": candidate_uuid,
        "normalized_external_key": "one",
        "raw_digest": "e" * 64,
        "clean_text": "hello candidate",
        "clean_digest": "f" * 64,
        "acquisition_capability": "intake.acquire.inline",
    }
    _material, _extra, callback = await pipeline._seal(command, state)
    refs = {"output_ref": "mkbtest:seal:out", "output_digest": "1" * 64}
    async with persistence.transaction() as tx:
        await callback(tx, refs)
        row = await tx.fetchone(
            "SELECT staging_state,seal_at,admission_result FROM mkb_intake_candidate_sets WHERE candidate_set_uuid=?",
            (candidate_uuid,),
        )
    assert row is not None
    assert row["staging_state"] == "open"
    assert row["seal_at"] is None
    assert row["admission_result"] is None

    async with persistence.transaction() as tx:
        await pipeline._seal_open_candidate_set_tx(
            tx,
            team_uuid=ids["team_uuid"],
            candidate_set_uuid=candidate_uuid,
            preflight_ref="mkbtest:preflight:out",
            preflight_digest="2" * 64,
            admission_result="auto_admitted",
            fence_message="seal failed",
        )
        sealed = await tx.fetchone(
            "SELECT staging_state,seal_at,admission_result,preflight_outcome_ref FROM mkb_intake_candidate_sets "
            "WHERE candidate_set_uuid=?",
            (candidate_uuid,),
        )
        # Accept only from sealed.
        accepted = await tx.execute(
            "UPDATE mkb_intake_candidate_sets SET staging_state='accepted',row_revision=row_revision+1 "
            "WHERE candidate_set_uuid=? AND staging_state='sealed'",
            (candidate_uuid,),
        )
        open_accept = await tx.execute(
            "UPDATE mkb_intake_candidate_sets SET staging_state='accepted' "
            "WHERE candidate_set_uuid=? AND staging_state='open'",
            (candidate_uuid,),
        )
    assert sealed is not None
    assert sealed["staging_state"] == "sealed"
    assert sealed["seal_at"] is not None
    assert sealed["admission_result"] == "auto_admitted"
    assert sealed["preflight_outcome_ref"] == "mkbtest:preflight:out"
    assert accepted.rowcount == 1
    assert open_accept.rowcount == 0
    await persistence.close()


@pytest.mark.asyncio
async def test_r1_cancel_abandons_unaccepted_candidate_and_creates_no_snapshot(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    async with persistence.transaction() as tx:
        seeded = await tx.fetchone(
            "SELECT candidate_set_uuid FROM mkb_intake_candidate_sets WHERE producer_execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert seeded is not None
    candidate_uuid = seeded["candidate_set_uuid"]

    assert await runtime.materialize_root(ids["execution_uuid"])
    assert await runtime.request_cancellation(ids["execution_uuid"]) is True

    async with persistence.transaction() as tx:
        candidate = await tx.fetchone(
            "SELECT staging_state,accepted_snapshot_uuid FROM mkb_intake_candidate_sets WHERE candidate_set_uuid=?",
            (candidate_uuid,),
        )
        snapshots = await tx.fetchone("SELECT COUNT(*) AS n FROM mkb_intake_snapshots")
    assert candidate == {"staging_state": "abandoned", "accepted_snapshot_uuid": None}
    assert snapshots == {"n": 0}
    await persistence.close()


def test_r1_metadata_no_change_does_not_insert_accepted_candidate_set() -> None:
    from src.runtime.intake.acquisition_intents import IntakeAcquisitionIntentsMixin

    source = inspect.getsource(IntakeAcquisitionIntentsMixin._acquire_metadata_update)
    assert "staging_state='accepted'" not in source
    assert 'staging_state="accepted"' not in source
    assert "_insert_no_change_transition" in source


# ---------------------------------------------------------------------------
# R2 — typed route SSOT; no operation_mode passthrough
# ---------------------------------------------------------------------------


def test_r2_material_for_does_not_passthrough_on_operation_mode() -> None:
    source = inspect.getsource(IntakeCoreMixin._material_for)
    assert "operation_mode" not in source
    assert "_passthrough" not in source
    outcome_source = inspect.getsource(IntakeCoreMixin.run)
    assert "payload_extra={}" in outcome_source


@pytest.mark.asyncio
async def test_r2_typed_context_reads_candidate_admission_not_extra(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    async with persistence.transaction() as tx:
        await tx.execute(
            "UPDATE mkb_intake_candidate_sets SET admission_result='human_review_required' "
            "WHERE producer_execution_uuid=?",
            (ids["execution_uuid"],),
        )
        execution = await tx.fetchone(
            "SELECT * FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
        typed = await runtime._typed_route_context_tx(tx, execution)
    assert typed["request_intent"] == "intake.ingest"
    assert typed["admission_result"] == "human_review_required"
    extra_only = runtime._guard_matches(
        BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        next(
            route
            for route in BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.routes
            if route.route_key == "accept_snapshot.auto_admitted"
        ),
        {"admission_result": "auto_admitted"},  # would match if extra were allowed blindly
        {},
    )
    # Extra-shaped dict is fine IFF it is the typed context. Missing key fail-closes:
    missing = runtime._guard_matches(
        BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        next(
            route
            for route in BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.routes
            if route.route_key == "accept_snapshot.auto_admitted"
        ),
        {},
        {},
    )
    assert extra_only is True
    assert missing is False

    decision = runtime._route_decision(
        plan=BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        execution=execution,
        source_step_key="accept_snapshot",
        selector=WorkflowOutcomeSelector.SUCCEEDED,
        route_context={},
    )
    assert decision["routes"] == []
    typed_decision = runtime._route_decision(
        plan=BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
        execution=execution,
        source_step_key="accept_snapshot",
        selector=WorkflowOutcomeSelector.SUCCEEDED,
        route_context=typed,
    )
    assert [route.route_key for route in typed_decision["routes"]] == ["accept_snapshot.human_review"]
    await persistence.close()


def test_r2_route_after_terminal_does_not_use_payload_extra_ssot() -> None:
    from src.runtime.workflow.runtime_outcome import WorkflowOutcomeMixin

    source = inspect.getsource(WorkflowOutcomeMixin._route_after_terminal_process_tx)
    assert "_typed_route_context_tx" in source
    assert "outcome.payload_extra" not in source


# ---------------------------------------------------------------------------
# R3 — Task cancel / decide_gate do not write Execution status
# ---------------------------------------------------------------------------


def test_r3_task_command_writers_do_not_update_execution_status() -> None:
    cancel_src = inspect.getsource(TaskCommandsMixin.cancel)
    decide_src = inspect.getsource(TaskProjectionsMixin.decide_gate)
    assert "UPDATE mkb_executions SET status" not in cancel_src
    assert "UPDATE mkb_executions SET status" not in decide_src


@pytest.mark.asyncio
async def test_r3_cancel_leaves_execution_until_runtime_consume(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    async with persistence.transaction() as tx:
        before = await tx.fetchone(
            "SELECT status FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
    teams = TeamService(persistence)
    service = TaskService(persistence, teams, DomainEventWriter())
    async with persistence.transaction() as tx:
        task = await tx.fetchone(
            "SELECT row_revision FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (ids["team_uuid"], ids["task_uuid"]),
        )
    assert task is not None
    view, accepted = await service.cancel(
        ids["team_uuid"], ids["task_uuid"], ExpectedRevisionRequest(expected_revision=task["row_revision"])
    )
    assert accepted is True
    assert view["status"] == "cancelling"
    async with persistence.transaction() as tx:
        after_command = await tx.fetchone(
            "SELECT status FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
        outbox = await tx.fetchone(
            "SELECT kind FROM mkb_outbox WHERE team_uuid=? AND kind='cancel_execution'",
            (ids["team_uuid"],),
        )
    assert after_command == before
    assert outbox == {"kind": "cancel_execution"}

    assert await runtime.request_cancellation(ids["execution_uuid"]) is True
    async with persistence.transaction() as tx:
        after_runtime = await tx.fetchone(
            "SELECT status FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],)
        )
    assert after_runtime is not None
    assert after_runtime["status"] in {"cancelling", "cancelled"}
    await persistence.close()


@pytest.mark.asyncio
async def test_r3_decide_gate_leaves_waiting_until_consume(tmp_path: Path) -> None:
    persistence, service, team_uuid, task_uuid, trace_uuid = await _service(tmp_path)
    try:
        gate_uuid, target_digest, _ = await _open_gate(persistence, team_uuid, task_uuid, trace_uuid)
        async with persistence.transaction() as tx:
            before = await tx.fetchone(
                "SELECT status,waiting_ref FROM mkb_executions WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
        committed = await service.decide_gate(
            team_uuid,
            task_uuid,
            gate_uuid,
            GateDecisionRequest(
                expected_gate_revision=0,
                target_digest=target_digest,
                action="approve",
                idempotency_key="r3-decision",
            ),
            "actor-fingerprint",
        )
        assert committed["gate"]["status"] == "released"
        async with persistence.transaction() as tx:
            after = await tx.fetchone(
                "SELECT status,waiting_ref FROM mkb_executions WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
        assert after == before
        assert after == {"status": "waiting", "waiting_ref": gate_uuid}
    finally:
        await persistence.close()
