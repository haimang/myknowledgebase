"""NH8-T06: delete tombstone rejects rebuild/reactivate and keeps search empty."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings

_TOKEN = "nh8-delete-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}
_BODY = "Deleted tombstone documents must not remain retrievable after cleanup."


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token=_TOKEN,
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        live_inference=False,
        persistence_backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
        rate_limit_ip_per_min=1_000,
        rate_limit_token_per_min=2_000,
    )


def _audit(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, str]:
    return {
        "schema_version": "mkb.task-audit.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "audit_type": "business_review",
        "audit_status": "not_required",
        "source": "nh8-delete",
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
    body: dict[str, Any] = {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": intent,
        "payload": payload,
        "audit": _audit(team_uuid, task_uuid, trace_uuid),
    }
    if intent == "intake.ingest":
        body["payload"] = {"json_prompt_id": "promptB.json.generic", **payload}
    response = client.post(f"/v1/teams/{team_uuid}/tasks", headers=_HEADERS, json=body)
    if wait:
        assert response.status_code == 201, response.text
        return task_uuid, response, _wait(client, team_uuid, task_uuid)
    return task_uuid, response, None


def _port(app, client: TestClient, query: str, params: tuple[object, ...]) -> Any:
    async def inspect() -> Any:
        async with app.state.container.persistence.transaction() as tx:
            return await tx.fetchone(query, params)

    return client.portal.call(inspect)


def _search(client: TestClient, team_uuid: str, namespace: str | None):
    body: dict[str, Any] = {
        "schema_version": "mkb.retrieval.v2",
        "team_uuid": team_uuid,
        "query": "Deleted tombstone documents",
        "return_k": 10,
        "recall_k": 20,
    }
    if namespace is not None:
        body["namespace_key"] = namespace
    return client.post(f"/v1/teams/{team_uuid}/retrieval:search", headers=_HEADERS, json=body)


def _published(app, client: TestClient) -> dict[str, Any]:
    team_uuid = uuid7()
    created = client.post(
        "/v1/teams",
        headers=_HEADERS,
        json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh8-delete"},
    )
    assert created.status_code == 201, created.text
    _, _, ingest = _post(
        client,
        team_uuid,
        "intake.ingest",
        {
            "source": {
                "source_kind": "inline_payload",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "nh8-delete",
                "external_key": "deleted-document",
                "content": _BODY,
            }
        },
    )
    assert ingest is not None and ingest["status"] == "succeeded", ingest
    row = _port(
        app,
        client,
        "SELECT i.intake_item_uuid,i.latest_revision_uuid,n.namespace_key FROM mkb_intake_items i "
        "JOIN mkb_vector_namespaces n ON n.team_uuid=i.team_uuid AND n.status='active' WHERE i.team_uuid=?",
        (team_uuid,),
    )
    assert row is not None
    return {"team_uuid": team_uuid, **dict(row)}


def test_delete_tombstone_rejects_rebuild_and_search_empty(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        published = _published(app, client)
        team_uuid = published["team_uuid"]
        item_uuid = published["intake_item_uuid"]
        namespace = str(published["namespace_key"])
        _, _, deleted = _post(client, team_uuid, "intake.delete", {"intake_item_uuid": item_uuid})
        assert deleted is not None and deleted["status"] == "succeeded", deleted
        item = _port(
            app,
            client,
            "SELECT lifecycle_state FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        assert item is not None and item["lifecycle_state"] == "deleted"
        empty = _search(client, team_uuid, namespace)
        assert empty.status_code == 200, empty.text
        assert empty.json()["results"] == []
        omitted = _search(client, team_uuid, None)
        assert omitted.status_code == 422
        assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"
        rebuild_uuid, rebuild, _ = _post(
            client,
            team_uuid,
            "intake.rebuild",
            {"intake_item_uuid": item_uuid},
            wait=False,
        )
        assert rebuild.status_code == 409, rebuild.text
        assert rebuild.json()["error"]["code"] == "intake-item-deleted"
        counts = _port(
            app,
            client,
            "SELECT (SELECT COUNT(*) FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?) AS tasks,"
            "(SELECT COUNT(*) FROM mkb_processes WHERE team_uuid=? AND task_uuid=?) AS processes",
            (team_uuid, rebuild_uuid, team_uuid, rebuild_uuid),
        )
        assert counts is not None and int(counts["tasks"]) == 0 and int(counts["processes"]) == 0
        cleanup = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_intake_cleanup_intents "
            "WHERE team_uuid=? AND target_kind='intake_item' AND target_ref=?",
            (team_uuid, f"intake_item:{item_uuid}"),
        )
        assert cleanup is not None and int(cleanup["n"]) == 1
        again_uuid, deleted_again, _ = _post(
            client, team_uuid, "intake.delete", {"intake_item_uuid": item_uuid}, wait=False
        )
        assert deleted_again.status_code == 409, deleted_again.text
        assert deleted_again.json()["error"]["code"] == "intake-item-deleted"
        again_counts = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, again_uuid),
        )
        assert again_counts is not None and int(again_counts["n"]) == 0
        cleanup_after = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_intake_cleanup_intents "
            "WHERE team_uuid=? AND target_kind='intake_item' AND target_ref=?",
            (team_uuid, f"intake_item:{item_uuid}"),
        )
        assert cleanup_after is not None and int(cleanup_after["n"]) == 1


def test_deleted_item_reactivate_409(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        published = _published(app, client)
        team_uuid = published["team_uuid"]
        item_uuid = published["intake_item_uuid"]
        namespace = str(published["namespace_key"])
        _, _, deleted = _post(client, team_uuid, "intake.delete", {"intake_item_uuid": item_uuid})
        assert deleted is not None and deleted["status"] == "succeeded", deleted
        reactivate_uuid, reactivate, _ = _post(
            client,
            team_uuid,
            "intake.reactivate",
            {"intake_item_uuid": item_uuid},
            wait=False,
        )
        assert reactivate.status_code == 409, reactivate.text
        assert reactivate.json()["error"]["code"] == "intake-item-deleted"
        counts = _port(
            app,
            client,
            "SELECT (SELECT COUNT(*) FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?) AS tasks",
            (team_uuid, reactivate_uuid),
        )
        assert counts is not None and int(counts["tasks"]) == 0
        empty = _search(client, team_uuid, namespace)
        assert empty.status_code == 200, empty.text
        assert empty.json()["results"] == []
        index_uuid, indexed, _ = _post(
            client,
            team_uuid,
            "index.rebuild",
            {"scope": "intake_item", "intake_item_uuid": item_uuid},
            wait=False,
        )
        assert indexed.status_code == 409, indexed.text
        assert indexed.json()["error"]["code"] == "intake-item-deleted"
        index_counts = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, index_uuid),
        )
        assert index_counts is not None and int(index_counts["n"]) == 0
