"""Focused S03 runtime tests: durable materialization, fence, and recovery."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path

import pytest

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.persistence.ports import UnitOfWork
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.workflow_engine import (
    ProcessOutcomeCommitter,
    WorkflowRuntime,
    WorkflowWorker,
    canonical_outcome_digest,
)
from src.workflows.builtin_lsrag import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW


class _AlwaysSuccessfulStage:
    async def run(self, command: ProcessCommand) -> ProcessOutcome:
        output_digest = stable_digest({"output": command.process_uuid, "fence": command.fencing_generation})
        proof_digest = stable_digest({"proof": command.process_key, "output": output_digest})
        provisional = ProcessOutcome(
            schema_version="mkb.process-outcome.v1",
            team_uuid=command.team_uuid,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            process_uuid=command.process_uuid,
            fencing_generation=command.fencing_generation,
            disposition="succeeded",
            outcome_digest="0" * 64,
            output_manifest_ref=f"mkbtest:output:{output_digest}",
            output_manifest_digest=output_digest,
            proof_ref=f"mkbtest:proof:{proof_digest}",
            proof_digest=proof_digest,
            payload_extra=(
                {"admission_result": "auto_admitted"} if command.process_key == "intake.accept_snapshot" else {}
            ),
        )
        return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})


class _HumanReviewStage(_AlwaysSuccessfulStage):
    async def run(self, command: ProcessCommand) -> ProcessOutcome:
        outcome = await super().run(command)
        if command.process_key != "intake.accept_snapshot":
            return outcome
        reviewed = outcome.model_copy(update={"payload_extra": {"admission_result": "human_review_required"}})
        return reviewed.model_copy(update={"outcome_digest": canonical_outcome_digest(reviewed)})


class _RecordingOutcomeCommitter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, str]] = []

    async def validate_and_commit(
        self,
        tx: UnitOfWork,
        command: ProcessCommand,
        outcome: ProcessOutcome,
    ) -> None:
        # The real owner may write CAS/catalogue rows here.  This test double
        # verifies it is called before the runtime changes Process success.
        row = await tx.fetchone("SELECT status FROM mkb_processes WHERE process_uuid=?", (command.process_uuid,))
        assert row == {"status": "running"}
        self.calls.append((command.process_uuid, outcome.output_manifest_ref or "", outcome.proof_ref or ""))


class _RejectingOutcomeCommitter:
    async def validate_and_commit(
        self,
        tx: UnitOfWork,
        command: ProcessCommand,
        outcome: ProcessOutcome,
    ) -> None:
        del tx, command, outcome
        raise MkbError("catalogue-ref-invalid", "Output catalogue refused the promoted reference", 409)


class _ExplodingOutcomeCommitter:
    async def validate_and_commit(
        self,
        tx: UnitOfWork,
        command: ProcessCommand,
        outcome: ProcessOutcome,
    ) -> None:
        del tx, command, outcome
        raise RuntimeError("database adapter interrupted")


class _StaleFenceStage(_AlwaysSuccessfulStage):
    async def run(self, command: ProcessCommand) -> ProcessOutcome:
        outcome = await super().run(command)
        stale = outcome.model_copy(update={"fencing_generation": command.fencing_generation + 1})
        return stale.model_copy(update={"outcome_digest": canonical_outcome_digest(stale)})


async def _seed_runtime(
    tmp_path: Path,
    *,
    outcome_committer: ProcessOutcomeCommitter | None = None,
    cleanup_recovery_window_seconds: int = 60,
) -> tuple[SqlitePersistence, WorkflowRuntime, dict[str, str]]:
    persistence = SqlitePersistence(tmp_path / "workflow-runtime.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    definition = BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW
    now = utc_now()
    ids = {
        "team_uuid": uuid7(),
        "task_uuid": uuid7(),
        "trace_uuid": uuid7(),
        "execution_uuid": uuid7(),
        "workflow_uuid": uuid7(),
        "workflow_revision_uuid": uuid7(),
    }
    compiled_digest = stable_digest(
        {
            "compiler": "mkb.workflow-compiler.v1",
            "definition": definition.model_dump(mode="json"),
            "capability_registry": sorted(definition.required_process_keys),
        }
    )
    config_digest = stable_digest({"config": "test"})
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (ids["team_uuid"], "workflow-runtime", stable_digest({"team": "workflow-runtime"}), now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_tasks "
            "(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,audit_bound,title,status,"
            "current_generation,current_root_execution_uuid,received_at,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,1,?,'queued',1,?,?,?,?)",
            (
                ids["team_uuid"],
                ids["task_uuid"],
                ids["trace_uuid"],
                "mkb.task.v1",
                "intake.ingest",
                stable_digest({"task": ids["task_uuid"]}),
                "Workflow runtime test",
                ids["execution_uuid"],
                now,
                now,
                now,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_workflow_registry "
            "(workflow_uuid,workflow_key,purpose_key,execution_role,active_revision_uuid,created_at,updated_at,created_by_origin) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (
                ids["workflow_uuid"],
                definition.workflow_key,
                definition.purpose_key,
                definition.execution_role.value,
                ids["workflow_revision_uuid"],
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
                ids["workflow_revision_uuid"],
                ids["workflow_uuid"],
                definition.revision_number,
                definition.schema_version,
                stable_digest({"capabilities": "test"}),
                stable_digest({"registration": "test"}),
                compiled_digest,
                compiled_digest,
                now,
            ),
        )
        for order_hint, step in enumerate(definition.steps):
            await tx.execute(
                "INSERT INTO mkb_workflow_steps "
                "(workflow_step_uuid,workflow_revision_uuid,step_key,step_kind,process_key,process_contract_version,"
                "phase_key,requiredness,terminal_kind,order_hint) VALUES (?,?,?,?,?,?,?,?,?,?)",
                (
                    uuid7(),
                    ids["workflow_revision_uuid"],
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
        await tx.execute(
            "INSERT INTO mkb_executions "
            "(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,execution_role,target_kind,"
            "workflow_uuid,workflow_revision_uuid,compiled_digest,resolver_decision_digest,domain_binding_digest,"
            "s05_binding_digest,config_snapshot_ref,config_snapshot_digest,status,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,'root','task',?,?,?,?,?,?,?,?, 'ready',?,?)",
            (
                ids["execution_uuid"],
                ids["team_uuid"],
                ids["task_uuid"],
                ids["trace_uuid"],
                1,
                ids["execution_uuid"],
                ids["workflow_uuid"],
                ids["workflow_revision_uuid"],
                compiled_digest,
                stable_digest({"resolver": ids["workflow_revision_uuid"]}),
                stable_digest({"binding": "domain"}),
                stable_digest({"binding": "s05"}),
                f"mkbtest:config:{config_digest}",
                config_digest,
                now,
                now,
            ),
        )
    return (
        persistence,
        WorkflowRuntime(
            persistence,
            definition,
            retry_delay_seconds=0,
            outcome_committer=outcome_committer,
            cleanup_recovery_window_seconds=cleanup_recovery_window_seconds,
        ),
        ids,
    )


@pytest.mark.asyncio
async def test_single_declarative_workflow_materializes_and_reaches_publication_proof(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    assert await runtime.materialize_root(ids["execution_uuid"])
    assert not await runtime.materialize_root(ids["execution_uuid"])

    worker = WorkflowWorker(runtime, _AlwaysSuccessfulStage())
    for _ in range(12):
        if not await worker.run_once("unit-worker"):
            break

    async with persistence.transaction() as tx:
        execution = await tx.fetchone("SELECT * FROM mkb_executions WHERE execution_uuid=?", (ids["execution_uuid"],))
        task = await tx.fetchone(
            "SELECT status,proof_ref FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (ids["team_uuid"], ids["task_uuid"]),
        )
        counts = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_processes WHERE execution_uuid=? AND status='succeeded'",
            (ids["execution_uuid"],),
        )
        duplicate_outbox = await tx.fetchone(
            "SELECT COUNT(*) AS total,COUNT(DISTINCT dedupe_key) AS unique_count FROM mkb_outbox",
        )
    assert execution is not None and execution["status"] == "succeeded"
    assert execution["publication_proof_ref"]
    assert task == {"status": "succeeded", "proof_ref": execution["publication_proof_ref"]}
    assert counts == {"count": 10}
    assert duplicate_outbox is not None
    assert duplicate_outbox["total"] == duplicate_outbox["unique_count"]
    await persistence.close()


@pytest.mark.asyncio
async def test_materialized_processes_copy_task_priority_and_latest_claim_deadline(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    deadline_at = "2099-01-01T00:00:00.000Z"
    async with persistence.transaction() as tx:
        await tx.execute(
            "UPDATE mkb_tasks SET priority='urgent',deadline_at=? WHERE team_uuid=? AND task_uuid=?",
            (deadline_at, ids["team_uuid"], ids["task_uuid"]),
        )

    assert await runtime.materialize_root(ids["execution_uuid"])
    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT priority_rank,deadline_at FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert process == {"priority_rank": 400, "deadline_at": deadline_at}
    await persistence.close()


async def _seed_vectorize_construct_intent(
    persistence: SqlitePersistence,
    ids: dict[str, str],
    *,
    corrupt_dual_digest: bool = False,
) -> tuple[dict[str, str], dict[str, str]]:
    """Create the smallest durable S07 package consumed by the S08 handoff."""

    schema_digest = stable_digest({"schema": "construction", "version": "v1"})
    construction_uuid, dual_uuid, validation_uuid = uuid7(), uuid7(), uuid7()
    construction_digest = stable_digest({"member": construction_uuid})
    dual_digest = stable_digest({"member": dual_uuid})
    validation_digest = stable_digest({"member": validation_uuid})
    construction_ref = f"mkbtest:generation:{construction_uuid}"
    dual_ref = f"mkbtest:generation:{dual_uuid}"
    validation_ref = f"mkbtest:generation:{validation_uuid}"
    payload = {
        "schema_version": "mkb.vectorize-construct-intent.v1",
        "team_uuid": ids["team_uuid"],
        "task_uuid": ids["task_uuid"],
        "execution_uuid": ids["execution_uuid"],
        "construction_artifact_uuid": construction_uuid,
        "construction_ref": construction_ref,
        "construction_content_digest": construction_digest,
        "dual_channel_artifact_uuid": dual_uuid,
        "dual_channel_ref": dual_ref,
        "dual_channel_content_digest": "0" * 64 if corrupt_dual_digest else dual_digest,
        "construction_schema_digest": schema_digest,
        "content_full_recipe_version": "content_full.v1",
    }
    now = utc_now()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_construction_schema_definitions "
            "(schema_key,schema_version,schema_digest,structure_schema_range,content_full_recipe_version,"
            "channel_contracts_digest,semantic_invariant_manifest_digest,media_contracts_digest,registration_origin,"
            "definition_body_json,registered_at,payload_extra) VALUES "
            "('lsrag.construction.default','v1',?,'lsrag.structure.default@v1','content_full.v1',?,?,?,"
            "'test','{}',?,'{}')",
            (
                schema_digest,
                stable_digest({"channels": ["original", "summary"]}),
                stable_digest({"invariants": "construction"}),
                stable_digest({"media": "application/json"}),
                now,
            ),
        )
        step = await tx.fetchone(
            "SELECT workflow_step_uuid FROM mkb_workflow_steps WHERE workflow_revision_uuid=? AND step_key='vectorize'",
            (ids["workflow_revision_uuid"],),
        )
        assert step is not None
        await tx.execute(
            "INSERT INTO mkb_processes "
            "(process_uuid,team_uuid,execution_uuid,task_uuid,workflow_step_uuid,step_key,process_key,"
            "process_contract_version,materialization_key,process_spec_digest,config_snapshot_ref,"
            "config_snapshot_digest,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,'vectorize','lsrag.vectorize','v1',?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                ids["team_uuid"],
                ids["execution_uuid"],
                ids["task_uuid"],
                step["workflow_step_uuid"],
                stable_digest({"materialization": "vectorize"}),
                stable_digest({"process": "vectorize"}),
                f"mkbtest:config:{stable_digest({'config': 'test'})}",
                stable_digest({"config": "test"}),
                now,
                now,
                now,
            ),
        )
        for artifact_uuid, artifact_type, handle, digest in (
            (construction_uuid, "construction_document", construction_ref, construction_digest),
            (dual_uuid, "dual_channel_projection", dual_ref, dual_digest),
            (validation_uuid, "construction_validation_report", validation_ref, validation_digest),
        ):
            await tx.execute(
                "INSERT INTO mkb_generation_artifacts "
                "(generation_artifact_uuid,team_uuid,artifact_type,task_uuid,execution_uuid,schema_key,schema_version,"
                "schema_digest,logical_handle,media_type,size_bytes,content_digest,validation_disposition,"
                "validation_report_ref,validation_report_digest,created_at,payload_extra) "
                "VALUES (?,?,?,?,?,'lsrag.construction.default','v1',?,?,'application/json',?,?,'full_valid',?,?,?,'{}')",
                (
                    artifact_uuid,
                    ids["team_uuid"],
                    artifact_type,
                    ids["task_uuid"],
                    ids["execution_uuid"],
                    schema_digest,
                    handle,
                    1,
                    digest,
                    validation_ref,
                    validation_digest,
                    now,
                ),
            )
            await tx.execute(
                "INSERT INTO mkb_generation_pointers "
                "(team_uuid,execution_uuid,artifact_type,current_generation_artifact_uuid,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,'{}')",
                (ids["team_uuid"], ids["execution_uuid"], artifact_type, artifact_uuid, now),
            )
        await tx.execute(
            "INSERT INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?, 'vectorize_construct',?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                ids["team_uuid"],
                json.dumps(payload, sort_keys=True, separators=(",", ":")),
                stable_digest(payload),
                f"vectorize-construct:{stable_digest(payload)}",
                "pending",
                now,
                now,
                now,
            ),
        )
    return payload, {"construction": construction_uuid, "dual": dual_uuid, "validation": validation_uuid}


@pytest.mark.asyncio
async def test_vectorize_construct_outbox_only_acknowledges_exact_current_package(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    payload, _ = await _seed_vectorize_construct_intent(persistence, ids)

    assert await runtime.dispatch_outbox_once("vectorize-intent-worker")
    async with persistence.transaction() as tx:
        outbox = await tx.fetchone(
            "SELECT status FROM mkb_outbox WHERE team_uuid=? AND dedupe_key=?",
            (ids["team_uuid"], f"vectorize-construct:{stable_digest(payload)}"),
        )
        vectors = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_vector_records")
        process = await tx.fetchone(
            "SELECT status FROM mkb_processes WHERE team_uuid=? AND execution_uuid=? AND process_key='lsrag.vectorize'",
            (ids["team_uuid"], ids["execution_uuid"]),
        )
    assert outbox == {"status": "done"}
    assert vectors == {"count": 0}
    assert process == {"status": "ready"}
    await persistence.close()


@pytest.mark.asyncio
async def test_vectorize_construct_outbox_rejects_mixed_generation_digest(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    payload, _ = await _seed_vectorize_construct_intent(persistence, ids, corrupt_dual_digest=True)

    with pytest.raises(MkbError, match="current full-valid generation member"):
        await runtime.dispatch_outbox_once("vectorize-intent-worker")
    async with persistence.transaction() as tx:
        outbox = await tx.fetchone(
            "SELECT status,last_error FROM mkb_outbox WHERE team_uuid=? AND dedupe_key=?",
            (ids["team_uuid"], f"vectorize-construct:{stable_digest(payload)}"),
        )
    assert outbox is not None
    assert outbox["status"] == "pending"
    assert "generation member" in (outbox["last_error"] or "")
    await persistence.close()


@pytest.mark.asyncio
async def test_cleanup_eligibility_requires_quiescence_and_appends_only_fences(tmp_path: Path) -> None:
    """S03 cleanup is an evidence marker, never an eager cascade delete."""

    persistence, runtime, ids = await _seed_runtime(tmp_path, cleanup_recovery_window_seconds=0)
    await runtime.materialize_root(ids["execution_uuid"])
    worker = WorkflowWorker(runtime, _AlwaysSuccessfulStage())
    for _ in range(16):
        if not await worker.run_once("cleanup-worker"):
            break

    async with persistence.transaction() as tx:
        execution = await tx.fetchone(
            "SELECT status,terminal_summary_digest,summary_completed_at,current_process_uuid "
            "FROM mkb_executions WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        pending = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_outbox WHERE status IN ('pending','in_flight')",
        )
    assert execution is not None
    assert execution["status"] == "succeeded"
    assert execution["terminal_summary_digest"]
    assert execution["summary_completed_at"]
    assert execution["current_process_uuid"] is None
    assert pending is not None and pending["count"] > 0

    # Unconsumed scheduling intents are a durable recovery trigger and must
    # keep every terminal Process ineligible.
    assert await runtime.evaluate_cleanup_eligibility_once() == 0

    for _ in range(32):
        if not await runtime.dispatch_outbox_once("cleanup-dispatch"):
            break

    marked = await runtime.evaluate_cleanup_eligibility_once()
    async with persistence.transaction() as tx:
        processes = await tx.fetchone(
            "SELECT COUNT(*) AS total,COUNT(cleanup_eligible_at) AS eligible,"
            "COUNT(cleanup_fence_digest) AS fenced FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        events = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_domain_events "
            "WHERE execution_uuid=? AND event_type='process.cleanup_eligible'",
            (ids["execution_uuid"],),
        )
        fences = await tx.fetchall(
            "SELECT process_uuid,cleanup_fence_digest FROM mkb_processes WHERE execution_uuid=? ORDER BY process_uuid",
            (ids["execution_uuid"],),
        )
    assert processes is not None
    assert marked == processes["total"]
    assert processes["total"] == processes["eligible"] == processes["fenced"]
    assert events == {"count": marked}
    assert all(row["cleanup_fence_digest"] for row in fences)

    # A replay cannot rewrite the terminal eligibility timestamp/fence or add
    # duplicate evidence.
    assert await runtime.evaluate_cleanup_eligibility_once() == 0
    async with persistence.transaction() as tx:
        replayed = await tx.fetchall(
            "SELECT process_uuid,cleanup_fence_digest FROM mkb_processes WHERE execution_uuid=? ORDER BY process_uuid",
            (ids["execution_uuid"],),
        )
        event_count = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_domain_events "
            "WHERE execution_uuid=? AND event_type='process.cleanup_eligible'",
            (ids["execution_uuid"],),
        )
    assert replayed == fences
    assert event_count == {"count": marked}
    await persistence.close()


@pytest.mark.asyncio
async def test_claim_cas_accepts_one_worker_and_fences_stale_outcome(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    claims = await asyncio.gather(*(runtime.claim_next(f"worker-{number}") for number in range(12)))
    claimed = [claim for claim in claims if claim is not None]
    assert len(claimed) == 1
    claim = claimed[0]
    await runtime.mark_running(claim.command.process_uuid, claim.command.fencing_generation)
    stale = ProcessOutcome(
        schema_version="mkb.process-outcome.v1",
        team_uuid=claim.command.team_uuid,
        task_uuid=claim.command.task_uuid,
        execution_uuid=claim.command.execution_uuid,
        process_uuid=claim.command.process_uuid,
        fencing_generation=claim.command.fencing_generation + 1,
        disposition="failed",
        outcome_digest="0" * 64,
        error_code="stale",
        error_message="stale fence",
    )
    stale = stale.model_copy(update={"outcome_digest": canonical_outcome_digest(stale)})
    with pytest.raises(ConflictError, match="stale-process-fence"):
        await runtime.accept_outcome(stale)
    await persistence.close()


@pytest.mark.asyncio
async def test_outcome_committer_is_inside_process_success_transaction(tmp_path: Path) -> None:
    committer = _RecordingOutcomeCommitter()
    persistence, runtime, ids = await _seed_runtime(tmp_path, outcome_committer=committer)
    await runtime.materialize_root(ids["execution_uuid"])
    assert await WorkflowWorker(runtime, _AlwaysSuccessfulStage()).run_once("catalogue-worker")
    assert len(committer.calls) == 1
    process_uuid, output_ref, proof_ref = committer.calls[0]
    assert output_ref.startswith("mkbtest:output:")
    assert proof_ref.startswith("mkbtest:proof:")
    async with persistence.transaction() as tx:
        process = await tx.fetchone("SELECT status FROM mkb_processes WHERE process_uuid=?", (process_uuid,))
    assert process == {"status": "succeeded"}
    await persistence.close()


@pytest.mark.asyncio
async def test_rejecting_outcome_committer_leaves_current_fenced_process_running(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path, outcome_committer=_RejectingOutcomeCommitter())
    await runtime.materialize_root(ids["execution_uuid"])
    claim = await runtime.claim_next("catalogue-reject-worker")
    assert claim is not None
    await runtime.mark_running(claim.command.process_uuid, claim.command.fencing_generation)
    outcome = await _AlwaysSuccessfulStage().run(claim.command)
    with pytest.raises(MkbError, match="catalogue-ref-invalid"):
        await runtime.accept_outcome(outcome)
    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT status,fencing_generation,accepted_outcome_digest FROM mkb_processes WHERE process_uuid=?",
            (claim.command.process_uuid,),
        )
    assert process == {
        "status": "running",
        "fencing_generation": claim.command.fencing_generation,
        "accepted_outcome_digest": None,
    }
    await persistence.close()


@pytest.mark.asyncio
async def test_worker_commits_typed_outcome_callback_error_as_terminal_failure(tmp_path: Path) -> None:
    """A typed callback rejection must not strand the claimed Process lease."""

    persistence, runtime, ids = await _seed_runtime(tmp_path, outcome_committer=_RejectingOutcomeCommitter())
    await runtime.materialize_root(ids["execution_uuid"])

    assert await WorkflowWorker(runtime, _AlwaysSuccessfulStage()).run_once("catalogue-reject-worker")

    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT status,error_code,failure_disposition,lease_owner FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        execution = await tx.fetchone(
            "SELECT status,final_error_code FROM mkb_executions WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        task = await tx.fetchone(
            "SELECT status,error_code FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (ids["team_uuid"], ids["task_uuid"]),
        )
    assert process == {
        "status": "failed",
        "error_code": "catalogue-ref-invalid",
        "failure_disposition": "non-retryable",
        "lease_owner": None,
    }
    assert execution == {"status": "failed", "final_error_code": "catalogue-ref-invalid"}
    assert task == {"status": "failed", "error_code": "catalogue-ref-invalid"}
    await persistence.close()


@pytest.mark.asyncio
async def test_worker_retries_unexpected_outcome_callback_error(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path, outcome_committer=_ExplodingOutcomeCommitter())
    await runtime.materialize_root(ids["execution_uuid"])

    assert await WorkflowWorker(runtime, _AlwaysSuccessfulStage()).run_once("catalogue-exception-worker")

    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT status,retry_count,error_code,error_message,failure_disposition,lease_owner "
            "FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert process == {
        "status": "retry_wait",
        "retry_count": 1,
        "error_code": "outcome-commit-exception",
        "error_message": "Outcome commit raised an unexpected error",
        "failure_disposition": "retryable",
        "lease_owner": None,
    }
    await persistence.close()


@pytest.mark.asyncio
async def test_worker_preserves_stale_outcome_conflict_fence(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])

    with pytest.raises(ConflictError, match="stale-process-fence"):
        await WorkflowWorker(runtime, _StaleFenceStage()).run_once("stale-fence-worker")

    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT status,error_code,lease_owner FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert process == {"status": "running", "error_code": None, "lease_owner": "stale-fence-worker"}
    await persistence.close()


@pytest.mark.asyncio
async def test_retry_and_lease_recovery_are_separate_counters(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    first = await runtime.claim_next("retry-worker", lease_seconds=1)
    assert first is not None
    await runtime.mark_running(first.command.process_uuid, first.command.fencing_generation)
    retryable = ProcessOutcome(
        schema_version="mkb.process-outcome.v1",
        team_uuid=first.command.team_uuid,
        task_uuid=first.command.task_uuid,
        execution_uuid=first.command.execution_uuid,
        process_uuid=first.command.process_uuid,
        fencing_generation=first.command.fencing_generation,
        disposition="retryable_failure",
        outcome_digest="0" * 64,
        error_code="transient",
        error_message="please retry",
    )
    retryable = retryable.model_copy(update={"outcome_digest": canonical_outcome_digest(retryable)})
    assert await runtime.accept_outcome(retryable)
    assert await runtime.promote_due_retries() == 1
    second = await runtime.claim_next("recovery-worker", lease_seconds=1)
    assert second is not None and second.command.fencing_generation > first.command.fencing_generation

    async with persistence.transaction() as tx:
        await tx.execute(
            "UPDATE mkb_processes SET lease_expires_at='2000-01-01T00:00:00.000000Z' WHERE process_uuid=?",
            (second.command.process_uuid,),
        )
    assert await runtime.recover_expired_leases() == 1
    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT status,retry_count,recovery_count FROM mkb_processes WHERE process_uuid=?",
            (second.command.process_uuid,),
        )
    assert process == {"status": "ready", "retry_count": 1, "recovery_count": 1}
    await persistence.close()


@pytest.mark.asyncio
async def test_human_review_fails_closed_without_durable_acceptance_evidence(tmp_path: Path) -> None:
    """A route fact alone must never create a placeholder review target."""

    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    worker = WorkflowWorker(runtime, _HumanReviewStage())
    for _ in range(6):
        assert await worker.run_once("human-review-worker")

    async with persistence.transaction() as tx:
        execution = await tx.fetchone(
            "SELECT status,final_error_code FROM mkb_executions WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        task = await tx.fetchone(
            "SELECT status,error_code FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (ids["team_uuid"], ids["task_uuid"]),
        )
        accepted = await tx.fetchone(
            "SELECT status FROM mkb_processes WHERE execution_uuid=? AND step_key='accept_snapshot'",
            (ids["execution_uuid"],),
        )
        gate_count = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_execution_gates WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        target_count = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_execution_gate_targets",
        )
    assert accepted == {"status": "succeeded"}
    assert execution == {"status": "failed", "final_error_code": "gate-target-evidence-invalid"}
    assert task == {"status": "failed", "error_code": "gate-target-evidence-invalid"}
    assert gate_count == {"count": 0}
    assert target_count == {"count": 0}
    await persistence.close()
