"""NH8-T08: registered_api member Items share single lifecycle/exact-clean services."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.e2e.test_registered_api_scatter import _create_team, _settings, _submit, _wait_for_terminal

_HEADERS = {"Authorization": "Bearer scatter-token"}
_SENTINEL = "Tax fixture reaches registered API scatter."
_FORBIDDEN = ("intake.acquire.", "intake.decode.", "clean.")


def _audit(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, str]:
    return {
        "schema_version": "mkb.task-audit.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "audit_type": "business_review",
        "audit_status": "not_required",
        "source": "nh8-api-item",
        "created_at": utc_now(),
    }


def _wait(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, Any]:
    deadline = time.monotonic() + 40
    latest: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_HEADERS)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    raise AssertionError(f"Task {task_uuid} did not become terminal: {latest}")


def _post(client: TestClient, team_uuid: str, intent: str, payload: dict[str, Any], *, wait: bool = True):
    task_uuid, trace_uuid = uuid7(), uuid7()
    response = client.post(
        f"/v1/teams/{team_uuid}/tasks",
        headers=_HEADERS,
        json={
            "schema_version": "mkb.task.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "request_intent": intent,
            "payload": payload,
            "audit": _audit(team_uuid, task_uuid, trace_uuid),
        },
    )
    if not wait:
        return task_uuid, response
    assert response.status_code == 201, response.text
    return task_uuid, _wait(client, team_uuid, task_uuid)


def _port(app, client: TestClient, query: str, params: tuple[object, ...]) -> Any:
    async def inspect() -> Any:
        async with app.state.container.persistence.transaction() as tx:
            return await tx.fetchone(query, params)

    return client.portal.call(inspect)


def _port_all(app, client: TestClient, query: str, params: tuple[object, ...]) -> list[Any]:
    async def inspect() -> list[Any]:
        async with app.state.container.persistence.transaction() as tx:
            return list(await tx.fetchall(query, params))

    return client.portal.call(inspect)


def _search(client: TestClient, team_uuid: str, namespace: str | None, realm: str = "tax_china"):
    body: dict[str, Any] = {
        "schema_version": "mkb.retrieval.v2",
        "team_uuid": team_uuid,
        "query": _SENTINEL,
        "filters": {"realm": realm, "vector_channel": "original"},
        "return_k": 20,
        "recall_k": 100,
    }
    if namespace is not None:
        body["namespace_key"] = namespace
    return client.post(f"/v1/teams/{team_uuid}/retrieval:search", headers=_HEADERS, json=body)


def _forbidden_keys(app, client: TestClient, team_uuid: str, task_uuid: str) -> list[str]:
    rows = _port_all(
        app,
        client,
        "SELECT process_key FROM mkb_processes WHERE team_uuid=? AND task_uuid=?",
        (team_uuid, task_uuid),
    )
    return [str(row["process_key"]) for row in rows if str(row["process_key"]).startswith(_FORBIDDEN)]


def test_registered_api_item_seven_intents_share_single_services(tmp_path: Path) -> None:
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=_HEADERS)
        ingest_uuid = _submit(
            client,
            team_uuid=team_uuid,
            headers=_HEADERS,
            provider="chinatax",
            operation="get_articles",
            records=[
                {
                    "id": "tax-one",
                    "label": "公告",
                    "column": "政策法规",
                    "title": "Tax title",
                    "content": _SENTINEL,
                    "xxgk_aging": "全文有效",
                }
            ],
        )
        terminal = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=ingest_uuid, headers=_HEADERS)
        assert terminal["status"] == "succeeded", terminal
        member = _port(
            app,
            client,
            "SELECT i.intake_item_uuid,i.latest_revision_uuid,i.serving_revision_uuid,s.source_kind,n.namespace_key "
            "FROM mkb_intake_items i "
            "JOIN mkb_intake_sources s ON s.team_uuid=i.team_uuid AND s.intake_source_uuid=i.intake_source_uuid "
            "JOIN mkb_vector_namespaces n ON n.team_uuid=i.team_uuid AND n.status='active' "
            "WHERE i.team_uuid=? AND i.lifecycle_state='active' AND i.serving_revision_uuid IS NOT NULL "
            "AND s.source_kind='registered_api' ORDER BY i.created_at LIMIT 1",
            (team_uuid,),
        )
        assert member is not None
        item_uuid = str(member["intake_item_uuid"])
        revision_uuid = str(member["latest_revision_uuid"])
        namespace = str(member["namespace_key"])
        omitted = _search(client, team_uuid, None)
        assert omitted.status_code == 422
        assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"
        before = _search(client, team_uuid, namespace)
        assert before.status_code == 200, before.text
        assert before.json()["results"]

        rebuild_uuid, rebuilt = _post(
            client,
            team_uuid,
            "intake.rebuild",
            {"intake_item_uuid": item_uuid, "expected_intake_revision_uuid": revision_uuid},
        )
        assert rebuilt["status"] == "succeeded", rebuilt
        assert _forbidden_keys(app, client, team_uuid, rebuild_uuid) == []
        role = _port(
            app,
            client,
            "SELECT execution_role FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
            "AND parent_execution_uuid IS NULL",
            (team_uuid, rebuild_uuid),
        )
        assert role is not None
        assert str(role["execution_role"]) != "scatter_child"
        hit = _search(client, team_uuid, namespace)
        assert hit.status_code == 200 and hit.json()["results"]

        no_change_uuid, no_change = _post(
            client,
            team_uuid,
            "intake.update_metadata",
            {"intake_item_uuid": item_uuid, "semantics": {"realm": "tax_china"}},
        )
        assert no_change["status"] == "succeeded", no_change
        assert _forbidden_keys(app, client, team_uuid, no_change_uuid) == []

        _, deactivated = _post(client, team_uuid, "intake.deactivate", {"intake_item_uuid": item_uuid})
        assert deactivated["status"] == "succeeded", deactivated
        empty = _search(client, team_uuid, namespace)
        assert empty.status_code == 200 and empty.json()["results"] == []

        _, reactivated = _post(client, team_uuid, "intake.reactivate", {"intake_item_uuid": item_uuid})
        assert reactivated["status"] == "succeeded", reactivated
        still_empty = _search(client, team_uuid, namespace)
        assert still_empty.status_code == 200 and still_empty.json()["results"] == []

        index_uuid, indexed = _post(
            client,
            team_uuid,
            "index.rebuild",
            {"scope": "intake_item", "intake_item_uuid": item_uuid},
        )
        assert indexed["status"] == "succeeded", indexed
        index_keys = {
            str(row["process_key"])
            for row in _port_all(
                app,
                client,
                "SELECT process_key FROM mkb_processes WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, index_uuid),
            )
        }
        assert index_keys == {"index.rebuild"}
        assert _search(client, team_uuid, namespace).json()["results"] == []

        _, published = _post(
            client,
            team_uuid,
            "intake.rebuild",
            {"intake_item_uuid": item_uuid, "expected_intake_revision_uuid": revision_uuid},
        )
        assert published["status"] == "succeeded", published
        restored = _search(client, team_uuid, namespace)
        assert restored.status_code == 200 and restored.json()["results"]

        _, deleted = _post(client, team_uuid, "intake.delete", {"intake_item_uuid": item_uuid})
        assert deleted["status"] == "succeeded", deleted
        tombstone_uuid, tombstone = _post(
            client,
            team_uuid,
            "intake.rebuild",
            {"intake_item_uuid": item_uuid},
            wait=False,
        )
        assert tombstone.status_code == 409, tombstone.text
        assert tombstone.json()["error"]["code"] == "intake-item-deleted"
        counts = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, tombstone_uuid),
        )
        assert counts is not None and int(counts["n"]) == 0
        assert _search(client, team_uuid, namespace).json()["results"] == []
        children = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_executions WHERE team_uuid=? AND execution_role='scatter_child' "
            "AND task_uuid IN (SELECT task_uuid FROM mkb_tasks WHERE team_uuid=? AND request_intent!='intake.ingest')",
            (team_uuid, team_uuid),
        )
        assert children is not None and int(children["n"]) == 0
