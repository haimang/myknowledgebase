"""Focused S02 projection/control tests against the real SQLite migration."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.api.models import GateDecisionRequest, RetryRequest, TaskCreateRequest, TeamCreateRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.task_service import TaskService
from src.services.events import DomainEventWriter
from src.services.teams import TeamService


async def _service(tmp_path: Path) -> tuple[SqlitePersistence, TaskService, str, str, str]:
    persistence = SqlitePersistence(tmp_path / "mkb.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    teams = TeamService(persistence)
    service = TaskService(persistence, teams, DomainEventWriter())
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    await teams.create(TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="projection-team"))
    now = utc_now()
    request = TaskCreateRequest.model_validate(
        {
            "schema_version": "mkb.task.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "request_intent": "intake.ingest",
            "payload": {"source": {"source_kind": "inline_payload", "external_key": "one", "content": "hello"}},
            "audit": {
                "schema_version": "mkb.task-audit.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit_type": "business_review",
                "audit_status": "not_required",
                "source": "test",
                "created_at": now,
            },
        }
    )
    await service.create(request, "token-fingerprint")
    return persistence, service, team_uuid, task_uuid, trace_uuid


async def _open_gate(
    persistence: SqlitePersistence, team_uuid: str, task_uuid: str, trace_uuid: str
) -> tuple[str, str, str]:
    """Seed a fully bound waiting gate as the workflow runtime would."""

    gate_uuid, target_digest = uuid7(), "a" * 64
    now = utc_now()
    async with persistence.transaction() as tx:
        root = await tx.fetchone(
            "SELECT * FROM mkb_executions WHERE team_uuid=? AND task_uuid=? AND execution_role='root'",
            (team_uuid, task_uuid),
        )
        assert root is not None
        await tx.execute(
            "UPDATE mkb_tasks SET status='running' WHERE team_uuid=? AND task_uuid=?", (team_uuid, task_uuid)
        )
        await tx.execute(
            "UPDATE mkb_executions SET status='waiting',row_revision=1,waiting_reason='human_review',waiting_ref=? "
            "WHERE execution_uuid=?",
            (gate_uuid, root["execution_uuid"]),
        )
        target = {
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "generation": 1,
            "waiting_ref": gate_uuid,
            "expected_execution_revision": 1,
            "allowed_actions": ["approve", "reject"],
            "review_summary": "Review the clean evidence",
        }
        await tx.execute(
            "INSERT INTO mkb_execution_gates "
            "(gate_uuid,team_uuid,task_uuid,execution_uuid,generation,gate_kind,status,gate_revision,opened_at,payload_extra) "
            "VALUES (?,?,?,?,?,'human_review','open',0,?,'{}')",
            (gate_uuid, team_uuid, task_uuid, root["execution_uuid"], 1, now),
        )
        await tx.execute(
            "INSERT INTO mkb_execution_gate_targets "
            "(gate_uuid,team_uuid,target_digest,review_target_json,clean_artifact_digest,intake_refs_json,created_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,'{}')",
            (gate_uuid, team_uuid, target_digest, json.dumps(target), "b" * 64, "[]", now),
        )
    return gate_uuid, target_digest, trace_uuid


@pytest.mark.asyncio
async def test_gate_decision_is_idempotent_and_never_leaks_runtime_ids(tmp_path: Path) -> None:
    persistence, service, team_uuid, task_uuid, trace_uuid = await _service(tmp_path)
    try:
        gate_uuid, target_digest, _ = await _open_gate(persistence, team_uuid, task_uuid, trace_uuid)
        task = await service.get(team_uuid, task_uuid)
        gates, cursor = await service.gates(team_uuid, task_uuid)
        assert cursor is None
        assert task["action_required"] == {
            "count": 1,
            "gate_uuid": gate_uuid,
            "gate_kind": "human_review",
            "revision": 0,
            "review_summary": "Review the clean evidence",
            "href": f"/v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate_uuid}",
        }
        assert gates[0]["gate_uuid"] == gate_uuid
        assert gates[0]["allowed_actions"] == ["approve", "reject"]
        assert "execution_uuid" not in json.dumps(gates[0])

        decision = GateDecisionRequest(
            expected_gate_revision=0,
            target_digest=target_digest,
            action="approve",
            idempotency_key="decision-1",
        )
        committed = await service.decide_gate(team_uuid, task_uuid, gate_uuid, decision, "actor-fingerprint")
        replay = await service.decide_gate(team_uuid, task_uuid, gate_uuid, decision, "actor-fingerprint")
        assert committed["committed"] is True
        assert committed["idempotent"] is False
        assert replay["idempotent"] is True
        assert replay["decision_uuid"] == committed["decision_uuid"]
        assert committed["gate"]["status"] == "released"
        assert committed["gate"]["allowed_actions"] == []

        async with persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT status,waiting_ref FROM mkb_executions WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
            outbox = await tx.fetchone(
                "SELECT kind,payload_json FROM mkb_outbox WHERE team_uuid=? AND kind='gate_decision'",
                (team_uuid,),
            )
            decisions = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_execution_gate_decisions WHERE gate_uuid=?", (gate_uuid,)
            )
        assert execution == {"status": "running", "waiting_ref": None}
        assert outbox is not None and outbox["kind"] == "gate_decision"
        assert json.loads(outbox["payload_json"])["decision_uuid"] == committed["decision_uuid"]
        assert decisions == {"count": 1}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_generation_restart_and_lineage_are_task_scoped_summaries(tmp_path: Path) -> None:
    persistence, service, team_uuid, task_uuid, _ = await _service(tmp_path)
    try:
        async with persistence.transaction() as tx:
            task = await tx.fetchone(
                "SELECT * FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?", (team_uuid, task_uuid)
            )
            assert task is not None
            await tx.execute(
                "UPDATE mkb_tasks SET status='failed',error_code='terminal-test' WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
            await tx.execute(
                "UPDATE mkb_executions SET status='failed' WHERE execution_uuid=?",
                (task["current_root_execution_uuid"],),
            )

        # This exercises the full-retry restart insert, including the placeholder
        # count regression that would otherwise fail before the projection exists.
        retried = await service.retry(team_uuid, task_uuid, RetryRequest(expected_revision=0, reason="retry"))
        generations, _ = await service.generations(team_uuid, task_uuid)
        restarts, _ = await service.restarts(team_uuid, source_task_uuid=task_uuid)
        graph = await service.lineage(team_uuid, task_uuid=task_uuid)

        assert retried["current_generation"] == 2
        assert [row["generation"] for row in generations] == [2, 1]
        assert len(restarts) == 1 and restarts[0]["scope"] == "full_task"
        filtered, _ = await service.restarts(
            team_uuid,
            restart_uuid=restarts[0]["restart_uuid"],
            requested_at_from="2000-01-01T00:00:00Z",
            requested_at_to="2100-01-01T00:00:00Z",
        )
        assert [row["restart_uuid"] for row in filtered] == [restarts[0]["restart_uuid"]]
        with pytest.raises(MkbError, match="time range"):
            await service.restarts(
                team_uuid,
                requested_at_from="2100-01-01T00:00:00Z",
                requested_at_to="2000-01-01T00:00:00Z",
            )
        wrong_filter_cursor = service._encode_cursor(
            "task-restarts",
            filter_digest="not-the-current-filter",
            requested_at=restarts[0]["requested_at"],
            restart_uuid=restarts[0]["restart_uuid"],
        )
        with pytest.raises(MkbError, match="Cursor"):
            await service.restarts(team_uuid, cursor=wrong_filter_cursor)
        assert any(node["kind"] == "restart" for node in graph["nodes"])
        rendered = json.dumps({"generations": generations, "restarts": restarts, "graph": graph})
        assert "execution_uuid" not in rendered
        assert "process_uuid" not in rendered
        assert "fencing_generation" not in rendered
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_items_without_accepted_membership_are_empty_and_cursor_is_rejected(tmp_path: Path) -> None:
    persistence, service, team_uuid, task_uuid, _ = await _service(tmp_path)
    try:
        items, cursor = await service.items(team_uuid, task_uuid)
        assert items == [] and cursor is None
        with pytest.raises(MkbError, match="Cursor"):
            await service.items(team_uuid, task_uuid, cursor="not-a-cursor")
    finally:
        await persistence.close()
