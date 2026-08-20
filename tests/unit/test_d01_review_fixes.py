"""D01 review residual fixes (R1–R6): retry classification, projection, cancel tree."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.models import TaskStatus
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.intake.core import IntakeCoreMixin
from src.runtime.task.task_commands import TaskCommandsMixin
from src.runtime.task.task_projection import project_task_status_tx
from src.runtime.task.task_views import TaskViewsMixin
from src.runtime.workflow_engine import WorkflowWorker, canonical_outcome_digest
from src.services.events import DomainEventWriter
from tests.unit.test_workflow_runtime import _AlwaysSuccessfulStage, _seed_runtime


def _fake_command(**overrides: object) -> ProcessCommand:
    base = {
        "schema_version": "mkb.process-command.v1",
        "team_uuid": uuid7(),
        "task_uuid": uuid7(),
        "trace_uuid": uuid7(),
        "execution_uuid": uuid7(),
        "process_uuid": uuid7(),
        "process_key": "lsrag.vectorize",
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


# ---------------------------------------------------------------------------
# R1 — recoverable intake errors → retryable_failure
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "code,status_code",
    [
        # True transient / transport failures only (see vectorize.py FAILED path,
        # generation_live FAILED path, inference transport, readiness fence).
        ("VECTORIZE_INFERENCE_FAILED", 502),
        ("GENERATION_INFERENCE_FAILED", 500),
        ("VECTORIZE_CONFIG_SNAPSHOT_UNAVAILABLE", 503),
        ("INFERENCE_TRANSPORT_RETRYABLE", 503),
        ("not-ready", 503),
    ],
)
def test_r1_recoverable_mkb_error_maps_to_retryable_failure(code: str, status_code: int) -> None:
    command = _fake_command()
    exc = MkbError(code, "transient stage failure", status_code)
    outcome = IntakeCoreMixin._outcome_from_error(command, exc)
    assert outcome.disposition == "retryable_failure"
    assert outcome.error_code == code
    assert outcome.process_uuid == command.process_uuid


@pytest.mark.parametrize(
    "code,status_code",
    [
        ("PIPELINE_INPUT_INVALID", 422),
        ("catalogue-ref-invalid", 409),
        ("OBJECT_INTEGRITY_DIGEST", 400),
        ("gate-target-evidence-invalid", 409),
        # Permanent capability / config gaps ("not configured") must fail-closed
        # even when raised as HTTP 503 — same class as OCR missing.
        ("CLEAN_OCR_CAPABILITY_UNAVAILABLE", 503),
        ("VECTORIZE_INFERENCE_UNAVAILABLE", 503),
        ("GENERATION_INFERENCE_UNAVAILABLE", 503),
        ("REGISTRY_NOT_FOUND", 503),
        ("ACQUISITION_HTTP_UNAVAILABLE", 503),
    ],
)
def test_r1_contract_failures_stay_terminal_failed(code: str, status_code: int) -> None:
    command = _fake_command()
    exc = MkbError(code, "contract or validation failure", status_code)
    outcome = IntakeCoreMixin._outcome_from_error(command, exc)
    assert outcome.disposition == "failed"
    assert outcome.error_code == code


@pytest.mark.asyncio
async def test_r1_retryable_failure_reclaims_same_process_uuid(tmp_path: Path) -> None:
    """Engine path: retryable_failure → retry_wait → promote → re-claim same process."""

    persistence, runtime, ids = await _seed_runtime(tmp_path)
    await runtime.materialize_root(ids["execution_uuid"])
    first = await runtime.claim_next("r1-worker", lease_seconds=30)
    assert first is not None
    process_uuid = first.command.process_uuid
    await runtime.mark_running(process_uuid, first.command.fencing_generation)

    retryable = ProcessOutcome(
        schema_version="mkb.process-outcome.v1",
        team_uuid=first.command.team_uuid,
        task_uuid=first.command.task_uuid,
        execution_uuid=first.command.execution_uuid,
        process_uuid=process_uuid,
        fencing_generation=first.command.fencing_generation,
        disposition="retryable_failure",
        outcome_digest="0" * 64,
        error_code="VECTORIZE_INFERENCE_FAILED",
        error_message="embedding endpoint transient failure",
    )
    retryable = retryable.model_copy(update={"outcome_digest": canonical_outcome_digest(retryable)})
    assert await runtime.accept_outcome(retryable)

    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT status,retry_count,process_uuid FROM mkb_processes WHERE process_uuid=?",
            (process_uuid,),
        )
    assert process is not None
    assert process["status"] == "retry_wait"
    assert process["retry_count"] == 1

    assert await runtime.promote_due_retries() == 1
    second = await runtime.claim_next("r1-worker-2", lease_seconds=30)
    assert second is not None
    assert second.command.process_uuid == process_uuid
    assert second.command.fencing_generation > first.command.fencing_generation
    await persistence.close()


# ---------------------------------------------------------------------------
# R2 — single Task projection helper (success-wins, proof-required, root match)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r2_project_task_status_success_wins_while_cancelling(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "r2.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    now = utc_now()
    team_uuid, task_uuid, root = uuid7(), uuid7(), uuid7()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team_uuid, "r2", stable_digest({"t": "r2"}), now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_tasks "
            "(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,audit_bound,title,"
            "status,current_generation,current_root_execution_uuid,received_at,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,1,?,'cancelling',1,?,?,?,?)",
            (
                team_uuid,
                task_uuid,
                uuid7(),
                "mkb.task.v1",
                "intake.ingest",
                stable_digest({"task": task_uuid}),
                "r2 success-wins",
                root,
                now,
                now,
                now,
            ),
        )
        ok = await project_task_status_tx(
            tx,
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            target=TaskStatus.SUCCEEDED,
            events=DomainEventWriter(),
            current_root_execution_uuid=root,
            proof_ref="mkbtest:proof:ok",
            result_ref="mkbtest:result:ok",
        )
        assert ok is False
        row = await tx.fetchone(
            "SELECT status,proof_ref FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
    assert row == {"status": "cancelling", "proof_ref": None}
    await persistence.close()


@pytest.mark.asyncio
async def test_r2_project_task_status_requires_proof_for_succeeded(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "r2-proof.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    now = utc_now()
    team_uuid, task_uuid, root = uuid7(), uuid7(), uuid7()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team_uuid, "r2p", stable_digest({"t": "r2p"}), now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_tasks "
            "(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,audit_bound,title,"
            "status,current_generation,current_root_execution_uuid,received_at,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,1,?,'running',1,?,?,?,?)",
            (
                team_uuid,
                task_uuid,
                uuid7(),
                "mkb.task.v1",
                "intake.ingest",
                stable_digest({"task": task_uuid}),
                "r2 proof",
                root,
                now,
                now,
                now,
            ),
        )
        with pytest.raises(MkbError) as raised:
            await project_task_status_tx(
                tx,
                team_uuid=team_uuid,
                task_uuid=task_uuid,
                target=TaskStatus.SUCCEEDED,
                current_root_execution_uuid=root,
                proof_ref=None,
            )
        assert raised.value.code == "task-proof-missing"
    await persistence.close()


@pytest.mark.asyncio
async def test_r2_project_task_status_rejects_stale_root(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "r2-root.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    now = utc_now()
    team_uuid, task_uuid, current_root, stale_root = uuid7(), uuid7(), uuid7(), uuid7()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team_uuid, "r2r", stable_digest({"t": "r2r"}), now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_tasks "
            "(team_uuid,task_uuid,trace_uuid,schema_version,request_intent,creation_fingerprint,audit_bound,title,"
            "status,current_generation,current_root_execution_uuid,received_at,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,1,?,'running',2,?,?,?,?)",
            (
                team_uuid,
                task_uuid,
                uuid7(),
                "mkb.task.v1",
                "intake.ingest",
                stable_digest({"task": task_uuid}),
                "r2 stale root",
                current_root,
                now,
                now,
                now,
            ),
        )
        ok = await project_task_status_tx(
            tx,
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            target=TaskStatus.FAILED,
            current_root_execution_uuid=stale_root,
            error_code="stale",
            error_message="old generation",
        )
        assert ok is False
        row = await tx.fetchone("SELECT status FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?", (team_uuid, task_uuid))
    assert row == {"status": "running"}
    await persistence.close()


@pytest.mark.asyncio
async def test_r2_runtime_terminal_uses_shared_projection(tmp_path: Path) -> None:
    """Happy-path root success projects Task via the shared helper."""

    persistence, runtime, ids = await _seed_runtime(tmp_path)
    assert await runtime.materialize_root(ids["execution_uuid"])
    worker = WorkflowWorker(runtime, _AlwaysSuccessfulStage())
    for _ in range(12):
        progressed = await worker.run_once("r2-worker")
        if not progressed:
            break
    async with persistence.transaction() as tx:
        task = await tx.fetchone(
            "SELECT status,proof_ref FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (ids["team_uuid"], ids["task_uuid"]),
        )
        execution = await tx.fetchone(
            "SELECT status,publication_proof_ref,current_process_uuid FROM mkb_executions WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert execution is not None and execution["status"] == "succeeded"
    assert execution["publication_proof_ref"] is not None
    assert execution["current_process_uuid"] is None  # R5 soft-pointer hygiene on terminal
    assert task is not None and task["status"] == "succeeded"
    assert task["proof_ref"] is not None
    await persistence.close()


# ---------------------------------------------------------------------------
# R3 — generation counts cancelled axis is child-execution, not process
# ---------------------------------------------------------------------------


def test_r3_generation_view_cancelled_uses_child_axis() -> None:
    row = {
        "generation": 1,
        "status": "cancelled",
        "total_child_count": 3,
        "active_child_count": 0,
        "succeeded_child_count": 1,
        "failed_child_count": 0,
        "cancelled_child_count": 2,
        "cancelled_process_count": 9,  # must not leak into public counts.cancelled
        "result_ref": None,
        "publication_proof_ref": None,
        "final_error_code": None,
        "created_at": utc_now(),
        "started_at": None,
        "completed_at": utc_now(),
    }
    view = TaskViewsMixin._generation_view(row)
    assert view["counts"] == {
        "total": 3,
        "active": 0,
        "succeeded": 1,
        "failed": 0,
        "cancelled": 2,
    }


# ---------------------------------------------------------------------------
# R4 — idle Process cancel goes through cancelling then terminal in one UoW
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r4_idle_process_cancel_converges_via_cancelling(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    assert await runtime.materialize_root(ids["execution_uuid"])

    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT process_uuid,status,lease_owner,claim_token_hash FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert process is not None
    assert process["status"] == "ready"
    assert process["lease_owner"] is None

    assert await runtime.request_cancellation(ids["execution_uuid"]) is True

    async with persistence.transaction() as tx:
        process_after = await tx.fetchone(
            "SELECT status,lease_owner FROM mkb_processes WHERE process_uuid=?",
            (process["process_uuid"],),
        )
        execution = await tx.fetchone(
            "SELECT status,current_process_uuid FROM mkb_executions WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        task = await tx.fetchone(
            "SELECT status FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (ids["team_uuid"], ids["task_uuid"]),
        )
    assert process_after == {"status": "cancelled", "lease_owner": None}
    assert execution is not None and execution["status"] == "cancelled"
    assert execution["current_process_uuid"] is None
    # Task was still queued; cancel projection only updates cancelling Tasks.
    # request_cancellation does not flip Task to cancelling (command path does).
    assert task is not None
    await persistence.close()


@pytest.mark.asyncio
async def test_r4_claimed_process_stays_cancelling_until_converge(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    assert await runtime.materialize_root(ids["execution_uuid"])
    claimed = await runtime.claim_next("r4-lease-worker", lease_seconds=60)
    assert claimed is not None
    await runtime.mark_running(claimed.command.process_uuid, claimed.command.fencing_generation)

    assert await runtime.request_cancellation(ids["execution_uuid"]) is True

    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT status FROM mkb_processes WHERE process_uuid=?",
            (claimed.command.process_uuid,),
        )
        execution = await tx.fetchone(
            "SELECT status FROM mkb_executions WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert process == {"status": "cancelling"}
    assert execution == {"status": "cancelling"}
    await persistence.close()


# ---------------------------------------------------------------------------
# R5 — Process root denorm on materialize; migration column present
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r5_materialize_writes_root_execution_uuid(tmp_path: Path) -> None:
    persistence, runtime, ids = await _seed_runtime(tmp_path)
    assert await runtime.materialize_root(ids["execution_uuid"])
    async with persistence.transaction() as tx:
        process = await tx.fetchone(
            "SELECT root_execution_uuid,execution_uuid FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
    assert process is not None
    assert process["root_execution_uuid"] == ids["execution_uuid"]
    assert process["execution_uuid"] == ids["execution_uuid"]
    await persistence.close()


@pytest.mark.asyncio
async def test_r5_migration_adds_cancelled_child_count_default(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "r5-mig.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    async with persistence.transaction() as tx:
        cols = await tx.fetchall("PRAGMA table_info(mkb_executions)")
        proc_cols = await tx.fetchall("PRAGMA table_info(mkb_processes)")
    exec_names = {row["name"] for row in cols}
    proc_names = {row["name"] for row in proc_cols}
    assert "cancelled_child_count" in exec_names
    assert "root_execution_uuid" in proc_names
    await persistence.close()


# ---------------------------------------------------------------------------
# R6 — cancel tree + success-wins race at runtime boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_r6_cancel_tree_idle_ready_processes_all_terminal(tmp_path: Path) -> None:
    """Cancel while multiple ready Processes exist converges the root tree."""

    persistence, runtime, ids = await _seed_runtime(tmp_path)
    assert await runtime.materialize_root(ids["execution_uuid"])
    # First step is ready; cancel before any claim.
    async with persistence.transaction() as tx:
        count = await tx.fetchone(
            "SELECT COUNT(*) AS n FROM mkb_processes WHERE execution_uuid=? AND status='ready'",
            (ids["execution_uuid"],),
        )
    assert count is not None and count["n"] >= 1

    assert await runtime.request_cancellation(ids["execution_uuid"]) is True

    async with persistence.transaction() as tx:
        processes = await tx.fetchall(
            "SELECT status FROM mkb_processes WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        execution = await tx.fetchone(
            "SELECT status FROM mkb_executions WHERE execution_uuid=?",
            (ids["execution_uuid"],),
        )
        active = await tx.fetchone(
            "SELECT COUNT(*) AS n FROM mkb_processes WHERE execution_uuid=? "
            "AND status IN ('ready','claimed','running','retry_wait','cancelling')",
            (ids["execution_uuid"],),
        )
    assert all(row["status"] == "cancelled" for row in processes)
    assert execution == {"status": "cancelled"}
    assert active == {"n": 0}
    await persistence.close()


def test_r2_transition_from_runtime_delegates_to_projection() -> None:
    """Smoke: TaskCommandsMixin.transition_from_runtime is a thin delegate."""

    source = inspect.getsource(TaskCommandsMixin.transition_from_runtime)
    assert "project_task_status_tx" in source
    module_doc = inspect.getdoc(project_task_status_tx) or ""
    projection_source = inspect.getsource(project_task_status_tx)
    assert "cancelling" in projection_source
    assert "success-wins" not in projection_source.lower()
    assert "success-wins" not in module_doc.lower()
