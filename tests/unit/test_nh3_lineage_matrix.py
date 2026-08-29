"""NH3-T08: retry/rebuild lineage cannot silently choose a new S05 worker."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from src.contracts.api.models import RetryRequest, TaskCreateRequest, TeamCreateRequest
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessOutcome
from src.persistence.factory import build_persistence
from src.runtime.intake.acquisition_intents import IntakeAcquisitionIntentsMixin
from src.runtime.task_service import TaskService
from src.runtime.workflow.helpers import canonical_outcome_digest
from src.services.events import DomainEventWriter
from src.services.teams import TeamService
from tests.e2e.test_nh3_seal_crash_windows import _runtime
from tests.integration.test_nh3_fact_history_uow import _success


async def _task_service(tmp_path: Path):
    persistence = build_persistence(
        tmp_path / "lineage.sqlite3",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    teams = TeamService(persistence)
    service = TaskService(persistence, teams, DomainEventWriter())
    team_uuid = uuid7()
    await teams.create(TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="nh3-lineage"))
    return persistence, service, team_uuid


def _request(team_uuid: str, *, intent: str, task_uuid: str | None = None) -> TaskCreateRequest:
    task_uuid = task_uuid or uuid7()
    trace_uuid = uuid7()
    payload = (
        {
            "json_prompt_id": "promptB.json.generic",
            "source": {
                "source_kind": "inline_payload",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "test-fixture",
                "external_key": task_uuid,
                "content": "lineage",
            },
        }
        if intent == "intake.ingest"
        else {"intake_item_uuid": uuid7()}
    )
    return TaskCreateRequest.model_validate(
        {
            "schema_version": "mkb.task.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "request_intent": intent,
            "payload": payload,
            "audit": {
                "schema_version": "mkb.task-audit.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit_type": "business_review",
                "audit_status": "not_required",
                "source": "nh3-lineage",
                "created_at": utc_now(),
            },
        }
    )


@pytest.mark.asyncio
async def test_full_task_copies_exact_sealed_actual(tmp_path: Path) -> None:
    persistence, service, team_uuid = await _task_service(tmp_path)
    request = _request(team_uuid, intent="intake.ingest")
    actual = stable_digest({"actual": "frozen"})
    route = stable_digest({"route": "frozen"})
    try:
        await service.create(request, "token-fingerprint")
        async with persistence.transaction() as tx:
            task = await tx.fetchone(
                "SELECT current_root_execution_uuid FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, request.task_uuid),
            )
            assert task is not None
            await tx.execute(
                "UPDATE mkb_tasks SET status='failed',error_code='fixture' WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, request.task_uuid),
            )
            await tx.execute(
                "UPDATE mkb_executions SET status='failed',actual_binding_digest=?,actual_binding_state='sealed',"
                "seal_generation=1,actual_selected_route_digest=?,actual_clean_step_key='clean_deterministic',"
                "actual_clean_process_key='clean.extract.deterministic',actual_clean_strategy='doc.deterministic' "
                "WHERE execution_uuid=?",
                (actual, route, task["current_root_execution_uuid"]),
            )
        await service.retry(
            team_uuid,
            request.task_uuid,
            RetryRequest(expected_revision=0, reason="exact full-task replay"),
        )
        async with persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT generation,workflow_revision_uuid,compiled_digest,domain_binding_digest,actual_binding_digest,"
                "actual_binding_state,seal_generation,actual_selected_route_digest,actual_clean_step_key,"
                "actual_clean_process_key,actual_clean_strategy FROM mkb_executions "
                "WHERE team_uuid=? AND task_uuid=? ORDER BY generation",
                (team_uuid, request.task_uuid),
            )
        assert len(rows) == 2
        for key in (
            "workflow_revision_uuid",
            "compiled_digest",
            "domain_binding_digest",
            "actual_binding_digest",
            "actual_binding_state",
            "seal_generation",
            "actual_selected_route_digest",
            "actual_clean_step_key",
            "actual_clean_process_key",
            "actual_clean_strategy",
        ):
            assert rows[0][key] == rows[1][key]
        assert rows[1]["actual_binding_digest"] == actual
        assert rows[1]["actual_binding_state"] == "sealed"
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_process_retry_keeps_actual(tmp_path: Path) -> None:
    persistence, runtime, ids, decode_process = await _runtime(tmp_path, "process-retry")
    try:
        assert await runtime.accept_outcome(_success(ids, decode_process, "seal-before-retry"))
        claimed = await runtime.claim_next("nh3-retry-worker")
        assert claimed is not None and claimed.command.process_key == "clean.extract.web"
        assert await runtime.mark_running(
            claimed.command.process_uuid,
            claimed.command.fencing_generation,
        )
        before = claimed.command.binding_digest
        provisional = ProcessOutcome(
            schema_version="mkb.process-outcome.v1",
            team_uuid=claimed.command.team_uuid,
            task_uuid=claimed.command.task_uuid,
            execution_uuid=claimed.command.execution_uuid,
            process_uuid=claimed.command.process_uuid,
            fencing_generation=claimed.command.fencing_generation,
            disposition="retryable_failure",
            outcome_digest="0" * 64,
            error_code="TRANSIENT_TEST",
            error_message="retry without worker reselection",
        )
        outcome = provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})
        assert await runtime.accept_outcome(outcome)
        async with persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT actual_binding_digest,actual_binding_state,seal_generation,actual_clean_process_key "
                "FROM mkb_executions WHERE execution_uuid=?",
                (ids["execution_uuid"],),
            )
            process = await tx.fetchone(
                "SELECT status,retry_count FROM mkb_processes WHERE process_uuid=?",
                (claimed.command.process_uuid,),
            )
        assert execution == {
            "actual_binding_digest": before,
            "actual_binding_state": "sealed",
            "seal_generation": 1,
            "actual_clean_process_key": "clean.extract.web",
        }
        assert process == {"status": "retry_wait", "retry_count": 1}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_rebuild_does_not_write_new_actual(tmp_path: Path) -> None:
    persistence, service, team_uuid = await _task_service(tmp_path)
    request = _request(team_uuid, intent="intake.rebuild")
    try:
        await service.create(request, "token-fingerprint")
        async with persistence.transaction() as tx:
            root = await tx.fetchone(
                "SELECT execution_uuid,actual_binding_digest,actual_binding_state,seal_generation "
                "FROM mkb_executions WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, request.task_uuid),
            )
            facts = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_representation_facts WHERE team_uuid=?",
                (team_uuid,),
            )
        assert root is not None
        assert root["actual_binding_digest"] is None
        assert root["actual_binding_state"] == "unsealed"
        assert root["seal_generation"] == 0
        assert facts == {"count": 0}
        source = inspect.getsource(IntakeAcquisitionIntentsMixin._acquire_rebuild)
        assert "append_representation_tx" not in source
        assert "actual_binding_digest" not in source
    finally:
        await persistence.close()


def test_upgrade_restart_scope_and_intent_absent() -> None:
    root = Path(__file__).resolve().parents[2]
    ddl = (root / "src/persistence/migrations/001_initial.sql").read_text(encoding="utf-8")
    assert "CHECK (restart_scope IN ('atomic_intake_item', 'full_task'))" in ddl
    surfaces = [
        root / "src/contracts/api/models.py",
        root / "src/runtime/task/task_commands.py",
        root / "src/runtime/task/task_projections.py",
        root / "src/workflows/lsrag_definition.py",
    ]
    assert all("upgrade" not in path.read_text(encoding="utf-8").casefold() for path in surfaces)
