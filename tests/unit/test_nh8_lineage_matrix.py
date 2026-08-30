"""NH8-T10: restart/rebuild/index/upgrade lineage split."""

from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from src.contracts.api.models import RetryRequest, TaskCreateRequest
from src.contracts.common.ids import stable_digest
from src.runtime.intake.acquisition_intents import IntakeAcquisitionIntentsMixin
from src.runtime.intake.index_rebuild_plan import IntakeIndexRebuildPlanMixin
from src.workflows.kind_family import BUILTIN_INLINE_KIND_WORKFLOW
from tests.unit.test_nh3_lineage_matrix import _request, _task_service


@pytest.mark.asyncio
async def test_full_task_copies_exact_sealed_actual(tmp_path: Path) -> None:
    persistence, service, team_uuid = await _task_service(tmp_path)
    request = _request(team_uuid, intent="intake.ingest")
    actual = stable_digest({"actual": "frozen-nh8"})
    route = stable_digest({"route": "frozen-nh8"})
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
    finally:
        await persistence.close()


def test_rebuild_does_not_write_source_actual_or_clean_process() -> None:
    source = inspect.getsource(IntakeAcquisitionIntentsMixin._acquire_rebuild)
    replay = inspect.getsource(IntakeAcquisitionIntentsMixin._replay_frozen_clean)
    assert "append_representation_tx" not in source
    assert "actual_binding_digest" not in source
    assert "append_representation_tx" not in replay
    start = [route for route in BUILTIN_INLINE_KIND_WORKFLOW.routes if route.from_step_key == "start"]
    rebuild = next(route for route in start if route.guard_key == "request_intent_rebuild")
    acquire = next(route for route in start if route.to_step_key == "acquire_inline")
    assert rebuild.priority < acquire.priority
    assert rebuild.to_step_key == "replay_frozen_clean"
    process_keys = {
        step.process_key
        for step in BUILTIN_INLINE_KIND_WORKFLOW.steps
        if step.step_key == "replay_frozen_clean"
    }
    assert process_keys == {"intake.replay_frozen_clean"}


def test_index_rebuild_does_not_touch_s05_or_revision() -> None:
    source = inspect.getsource(IntakeIndexRebuildPlanMixin._index_rebuild)
    assert "INSERT INTO mkb_intake_revisions" not in source
    assert "actual_binding_digest" not in source
    assert "s05_binding_digest" not in source
    start = [route for route in BUILTIN_INLINE_KIND_WORKFLOW.routes if route.from_step_key == "start"]
    index = next(route for route in start if route.guard_key == "request_intent_index_rebuild")
    acquire = next(route for route in start if route.to_step_key == "acquire_inline")
    assert index.priority < acquire.priority
    assert index.to_step_key == "index_rebuild"


def test_upgrade_entrance_scan_is_zero() -> None:
    root = Path(__file__).resolve().parents[2]
    ddl = (root / "src/persistence/migrations/001_initial.sql").read_text(encoding="utf-8")
    assert "CHECK (restart_scope IN ('atomic_intake_item', 'full_task'))" in ddl
    assert "upgrade" not in ddl.casefold()
    models = (root / "src/contracts/api/models.py").read_text(encoding="utf-8")
    tree = ast.parse(models)
    intents: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "request_intent":
            annotation = ast.unparse(node.annotation)
            for intent in (
                "intake.ingest",
                "intake.rebuild",
                "intake.update_metadata",
                "intake.deactivate",
                "intake.reactivate",
                "intake.delete",
                "index.rebuild",
            ):
                if intent in annotation:
                    intents.add(intent)
    assert intents == {
        "intake.ingest",
        "intake.rebuild",
        "intake.update_metadata",
        "intake.deactivate",
        "intake.reactivate",
        "intake.delete",
        "index.rebuild",
    }
    assert "intake.upgrade" not in models
    commands = (root / "src/runtime/task/task_commands.py").read_text(encoding="utf-8")
    assert "upgrade" not in commands.casefold()
    assert "upgrade" not in inspect.getsource(TaskCreateRequest).casefold()
