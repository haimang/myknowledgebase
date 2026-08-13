"""Registered-API scatter intake semantic regressions (S03/S04)."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.contracts.storage.models import ObjectHandle
from src.runtime.config import Settings
from src.runtime.intake_pipeline import IntakePipeline
from src.storage.local_store import LocalObjectStore

_TERMINAL = {"succeeded", "failed", "cancelled"}


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="scatter-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        live_inference=False,
        rate_limit_ip_per_min=1_000,
        rate_limit_token_per_min=2_000,
    )


def _task_body(
    *,
    team_uuid: str,
    task_uuid: str,
    trace_uuid: str,
    records: list[dict[str, Any]],
    provider: str = "chinatax",
    operation: str = "get_articles",
    require_human_review: bool = False,
) -> dict[str, Any]:
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {
            "source": {
                "source_kind": "registered_api",
                "external_key": f"collection-{task_uuid}",
                "connector_key": "scatter-e2e",
                "provider": provider,
                "operation": operation,
                "definition_version": "v1",
                "representation": "raw",
                "records": records,
                "exhaustion_proof": "caller_frozen_records.v1",
                "require_human_review": require_human_review,
            }
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "scatter-e2e",
            "created_at": utc_now(),
        },
    }


def _create_team(client: TestClient, *, team_uuid: str, headers: dict[str, str]) -> None:
    response = client.post(
        "/v1/teams",
        headers=headers,
        json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "scatter e2e"},
    )
    assert response.status_code == 201, response.text


def _submit(
    client: TestClient,
    *,
    team_uuid: str,
    headers: dict[str, str],
    records: list[dict[str, Any]],
    provider: str = "chinatax",
    operation: str = "get_articles",
    require_human_review: bool = False,
) -> str:
    task_uuid, trace_uuid = uuid7(), uuid7()
    response = client.post(
        f"/v1/teams/{team_uuid}/tasks",
        headers=headers,
        json=_task_body(
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            trace_uuid=trace_uuid,
            records=records,
            provider=provider,
            operation=operation,
            require_human_review=require_human_review,
        ),
    )
    assert response.status_code == 201, response.text
    return task_uuid


def _get_task(client: TestClient, *, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, Any]:
    response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _wait_for_terminal(
    client: TestClient, *, team_uuid: str, task_uuid: str, headers: dict[str, str]
) -> dict[str, Any]:
    deadline = time.monotonic() + 8
    task: dict[str, Any] = {}
    while time.monotonic() < deadline:
        task = _get_task(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
        if task["status"] in _TERMINAL:
            return task
        time.sleep(0.02)
    raise AssertionError(f"Task {task_uuid} did not become terminal: {task}")


def _wait_for_gate(
    client: TestClient, *, team_uuid: str, task_uuid: str, headers: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any]]:
    deadline = time.monotonic() + 8
    task: dict[str, Any] = {}
    while time.monotonic() < deadline:
        task = _get_task(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
        action_required = task.get("action_required")
        if isinstance(action_required, dict):
            gate = client.get(action_required["href"], headers=headers)
            assert gate.status_code == 200, gate.text
            return task, gate.json()
        assert task["status"] not in _TERMINAL, task
        time.sleep(0.02)
    raise AssertionError(f"Task {task_uuid} did not open a human review Gate: {task}")


def _decide(
    client: TestClient,
    *,
    team_uuid: str,
    task_uuid: str,
    headers: dict[str, str],
    gate: dict[str, Any],
    action: str,
) -> None:
    response = client.post(
        f"/v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate['gate_uuid']}:decide",
        headers=headers,
        json={
            "expected_gate_revision": gate["revision"],
            "target_digest": gate["target_digest"],
            "action": action,
            "idempotency_key": f"scatter-{action}-{uuid7()}",
        },
    )
    assert response.status_code == 200, response.text


def _items(client: TestClient, *, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> list[dict[str, Any]]:
    response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}/items", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["next_cursor"] is None
    return body["items"]


def _records(prefix: str) -> list[dict[str, Any]]:
    return [
        {
            "id": f"{prefix}-alpha",
            "label": "公告",
            "column": "政策法规",
            "content": f"{prefix} alpha member demonstrates independent scatter publication.",
            "title": "Alpha",
            "xxgk_aging": "全文有效",
        },
        {
            "id": f"{prefix}-beta",
            "label": "通知",
            "column": "政策法规",
            "content": f"{prefix} beta member demonstrates exact fan in proof validation.",
            "title": "Beta",
            "xxgk_aging": "全文有效",
        },
    ]


def test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer scatter-token"}
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))
    cases = {
        ("chinatax", "get_articles"): [
            {
                "id": "tax-one",
                "label": "公告",
                "column": "政策法规",
                "title": "Tax title",
                "content": "Tax fixture reaches registered API scatter.",
                "xxgk_aging": "全文有效",
            }
        ],
        ("domain", "get_agency_listings"): [
            {
                "id": 1001,
                "advertiserIdentifiers": {"advertiserId": 12106, "contactIds": []},
                "headline": "Domain title",
                "description": "Domain fixture reaches registered API scatter.",
                "propertyTypes": ["House"],
                "status": "live",
                "saleMode": "buy",
                "channel": "residential",
            }
        ],
        ("realestate", "get_listings"): [
            {
                "listingId": "rea-one",
                "channel": "sold",
                "status": {"label": "Sold", "type": "sold_listing"},
                "title": "REA title",
                "description": "REA fixture reaches <br>registered API scatter.",
                "agency": {"name": "Buxton", "agencyId": "37576"},
            }
        ],
    }
    task_ids: dict[tuple[str, str], str] = {}
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=headers)
        for (provider, operation), records in cases.items():
            task_uuid = _submit(
                client,
                team_uuid=team_uuid,
                headers=headers,
                provider=provider,
                operation=operation,
                records=records,
            )
            terminal = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
            assert terminal["status"] == "succeeded", (provider, terminal)
            task_ids[(provider, operation)] = task_uuid

    store = LocalObjectStore(tmp_path / "objects")
    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        for (provider, operation), task_uuid in task_ids.items():
            process = connection.execute(
                "SELECT output_manifest_ref FROM mkb_processes WHERE team_uuid=? AND task_uuid=? "
                "AND process_key='clean.map.registered_api' AND status='succeeded'",
                (team_uuid, task_uuid),
            ).fetchone()
            assert process is not None
            output = json.loads(
                asyncio.run(store.read_verified(team_uuid, ObjectHandle(value=process["output_manifest_ref"]))).decode()
            )
            evidence = output["output"]["clean_collection"]["evidence"]
            assert evidence == {
                "clean_capability": "clean.map.registered_api",
                "definition_version": "v1",
                "member_count": 1,
                "operation": operation,
                "provider": provider,
            }
            member_evidence = output["state"]["collection_members"][0]["clean_evidence"]
            assert member_evidence["provider"] == provider
            assert member_evidence["operation"] == operation
            semantics = connection.execute(
                "SELECT s.semantic_key,s.value_text,s.value_int FROM mkb_intake_revision_semantics s "
                "JOIN mkb_intake_snapshot_memberships m ON m.team_uuid=s.team_uuid "
                "AND m.observed_revision_uuid=s.intake_revision_uuid "
                "JOIN mkb_tasks t ON t.team_uuid=m.team_uuid AND t.intake_snapshot_uuid=m.intake_snapshot_uuid "
                "WHERE t.team_uuid=? AND t.task_uuid=?",
                (team_uuid, task_uuid),
            ).fetchall()
            semantic_map = {row["semantic_key"]: row["value_text"] if row["value_text"] is not None else row["value_int"] for row in semantics}
            assert {"realm", "type", "channel", "source_name", "is_active", "context_tags"} <= set(semantic_map)


def test_registered_api_scatter_auto_zero_and_fanin_recovery(tmp_path: Path) -> None:
    database_path = tmp_path / "mkb.sqlite3"
    headers = {"Authorization": "Bearer scatter-token"}
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))

    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=headers)
        task_uuid = _submit(client, team_uuid=team_uuid, headers=headers, records=_records("auto"))
        completed = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
        assert completed["status"] == "succeeded", completed
        assert completed["counts"] == {
            "total": 2,
            "required": 2,
            "active": 0,
            "succeeded": 2,
            "failed": 0,
            "cancelled": 0,
            "skipped": 0,
        }
        item_views = _items(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
        assert [item["outcome"] for item in item_views] == ["succeeded", "succeeded"]
        assert all(item["publication_ready"] for item in item_views)

        # Emulate a crash after every required child reached its proof-valid
        # terminal state but before the parent completion projection.  Repair
        # must use the accepted Snapshot/ChangeSet denominator, not queue
        # emptiness, to finish the parent exactly once.
        with sqlite3.connect(database_path, timeout=5) as connection:
            root = connection.execute(
                "SELECT execution_uuid FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
                "AND parent_execution_uuid IS NULL",
                (team_uuid, task_uuid),
            ).fetchone()
            change_set = connection.execute(
                "SELECT change_set_uuid FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?", (team_uuid, task_uuid)
            ).fetchone()
            assert root is not None and change_set is not None
            connection.execute(
                "UPDATE mkb_tasks SET status='running',completed_at=NULL,error_code=NULL,error_message=NULL "
                "WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, task_uuid),
            )
            connection.execute(
                "UPDATE mkb_executions SET status='waiting',waiting_reason='scatter_children',waiting_ref=?,"
                "completed_at=NULL,summary_completed_at=NULL WHERE execution_uuid=?",
                (change_set[0], root[0]),
            )
            connection.commit()
        repaired = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
        assert repaired["status"] == "succeeded", repaired
        assert repaired["proof_ref"]

        zero_task_uuid = _submit(client, team_uuid=team_uuid, headers=headers, records=[])
        zero = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=zero_task_uuid, headers=headers)
        assert zero["status"] == "succeeded", zero
        assert zero["counts"] == {
            "total": 0,
            "required": 0,
            "active": 0,
            "succeeded": 0,
            "failed": 0,
            "cancelled": 0,
            "skipped": 0,
        }
        assert _items(client, team_uuid=team_uuid, task_uuid=zero_task_uuid, headers=headers) == []

    with sqlite3.connect(database_path) as connection:
        membership_count = connection.execute(
            "SELECT COUNT(*) FROM mkb_intake_snapshot_memberships AS m JOIN mkb_tasks AS t "
            "ON t.team_uuid=m.team_uuid AND t.intake_snapshot_uuid=m.intake_snapshot_uuid "
            "WHERE t.team_uuid=? AND t.task_uuid=?",
            (team_uuid, zero_task_uuid),
        ).fetchone()[0]
    assert membership_count == 0


def test_registered_api_scatter_human_gate_release_reject_and_cancel(tmp_path: Path) -> None:
    database_path = tmp_path / "mkb.sqlite3"
    headers = {"Authorization": "Bearer scatter-token"}
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))

    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=headers)

        approved_task_uuid = _submit(
            client, team_uuid=team_uuid, headers=headers, records=_records("approved"), require_human_review=True
        )
        _, gate = _wait_for_gate(client, team_uuid=team_uuid, task_uuid=approved_task_uuid, headers=headers)
        with sqlite3.connect(database_path, timeout=5) as connection:
            root = connection.execute(
                "SELECT status,waiting_reason FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
                "AND parent_execution_uuid IS NULL",
                (team_uuid, approved_task_uuid),
            ).fetchone()
            children = connection.execute(
                "SELECT status,waiting_reason FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
                "AND parent_execution_uuid IS NOT NULL ORDER BY execution_uuid",
                (team_uuid, approved_task_uuid),
            ).fetchall()
            child_processes = connection.execute(
                "SELECT COUNT(*) FROM mkb_processes AS p JOIN mkb_executions AS e "
                "ON e.execution_uuid=p.execution_uuid WHERE e.team_uuid=? AND e.task_uuid=? "
                "AND e.parent_execution_uuid IS NOT NULL",
                (team_uuid, approved_task_uuid),
            ).fetchone()[0]
        assert root == ("waiting", "human_review")
        assert children == [("waiting", "durable_prerequisite"), ("waiting", "durable_prerequisite")]
        assert child_processes == 0
        _decide(
            client,
            team_uuid=team_uuid,
            task_uuid=approved_task_uuid,
            headers=headers,
            gate=gate,
            action="approve",
        )
        approved = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=approved_task_uuid, headers=headers)
        assert approved["status"] == "succeeded", approved

        rejected_task_uuid = _submit(
            client, team_uuid=team_uuid, headers=headers, records=_records("rejected"), require_human_review=True
        )
        _, rejected_gate = _wait_for_gate(client, team_uuid=team_uuid, task_uuid=rejected_task_uuid, headers=headers)
        _decide(
            client,
            team_uuid=team_uuid,
            task_uuid=rejected_task_uuid,
            headers=headers,
            gate=rejected_gate,
            action="reject",
        )
        rejected = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=rejected_task_uuid, headers=headers)
        assert rejected["status"] == "failed", rejected
        assert rejected["error"]["code"] == "gate-rejected"

        cancelled_task_uuid = _submit(
            client, team_uuid=team_uuid, headers=headers, records=_records("cancelled"), require_human_review=True
        )
        cancel_task, _ = _wait_for_gate(client, team_uuid=team_uuid, task_uuid=cancelled_task_uuid, headers=headers)
        cancelled_response = client.post(
            f"/v1/teams/{team_uuid}/tasks/{cancelled_task_uuid}:cancel",
            headers=headers,
            json={"expected_revision": cancel_task["revision"]},
        )
        assert cancelled_response.status_code == 202, cancelled_response.text
        cancelled = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=cancelled_task_uuid, headers=headers)
        assert cancelled["status"] == "cancelled", cancelled
        assert cancelled["counts"]["active"] == 0
        assert cancelled["counts"]["cancelled"] == 2

    with sqlite3.connect(database_path) as connection:
        rejected_children = connection.execute(
            "SELECT status FROM mkb_executions WHERE team_uuid=? AND task_uuid=? AND parent_execution_uuid IS NOT NULL",
            (team_uuid, rejected_task_uuid),
        ).fetchall()
        cancelled_children = connection.execute(
            "SELECT status,waiting_reason,waiting_ref FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
            "AND parent_execution_uuid IS NOT NULL",
            (team_uuid, cancelled_task_uuid),
        ).fetchall()
        cancelled_gate = connection.execute(
            "SELECT status FROM mkb_execution_gates WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, cancelled_task_uuid),
        ).fetchone()
    assert rejected_children == [("cancelled",), ("cancelled",)]
    assert cancelled_children == [("cancelled", None, None), ("cancelled", None, None)]
    assert cancelled_gate == ("superseded",)


class _FailOneScatterChild:
    """Deterministically fail one leaf without changing production routing."""

    def __init__(self, delegate: Any) -> None:
        self._delegate = delegate
        self._failed = False

    async def run(self, command: ProcessCommand) -> ProcessOutcome:
        if command.process_key == "lsrag.structurize" and not self._failed:
            self._failed = True
            return IntakePipeline._failed(command, "forced-scatter-child-failure", "E2E forced one child failure")
        return await self._delegate.run(command)


def test_registered_api_scatter_collects_child_failure_before_parent_terminal(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer scatter-token"}
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))
    app.state.container.workflow_worker.handler = _FailOneScatterChild(app.state.container.workflow_worker.handler)

    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=headers)
        task_uuid = _submit(client, team_uuid=team_uuid, headers=headers, records=_records("leaf-failure"))
        failed = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
        assert failed["status"] == "failed", failed
        assert failed["error"]["code"] == "scatter-required-child-failed"
        # Fan-in is collect-all: the healthy sibling proves publication even
        # though the parent task has the required-child failure terminal.
        outcomes = sorted(item["outcome"] for item in _items(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers))
        assert outcomes == ["failed", "succeeded"]
