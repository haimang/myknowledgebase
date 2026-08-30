"""NH8-T04/T05: deactivate withdraws retrieval; reactivate does not restore serving."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings

_TOKEN = "reactivate-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}
_BODY = "Reactivation must require fresh publication before retrieval can serve this document."


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


def _task_body(
    *,
    team_uuid: str,
    task_uuid: str,
    trace_uuid: str,
    request_intent: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if request_intent == "intake.ingest":
        payload = {"json_prompt_id": "promptB.json.generic", **payload}
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": request_intent,
        "payload": payload,
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "reactivate-e2e",
            "created_at": utc_now(),
        },
    }


def _wait(client: TestClient, *, team_uuid: str, task_uuid: str) -> dict[str, Any]:
    deadline = time.monotonic() + 40
    task: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_HEADERS)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.02)
    raise AssertionError(f"Task {task_uuid} did not become terminal: {task}")


def _submit(client: TestClient, team_uuid: str, request_intent: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    task_uuid, trace_uuid = uuid7(), uuid7()
    response = client.post(
        f"/v1/teams/{team_uuid}/tasks",
        headers=_HEADERS,
        json=_task_body(
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            trace_uuid=trace_uuid,
            request_intent=request_intent,
            payload=payload,
        ),
    )
    assert response.status_code == 201, response.text
    return task_uuid, _wait(client, team_uuid=team_uuid, task_uuid=task_uuid)


def _search(client: TestClient, team_uuid: str, namespace: str | None):
    body: dict[str, Any] = {
        "schema_version": "mkb.retrieval.v2",
        "team_uuid": team_uuid,
        "query": "reactivation must require fresh publication",
        "filters": {"vector_channel": "original"},
        "return_k": 20,
        "recall_k": 40,
    }
    if namespace is not None:
        body["namespace_key"] = namespace
    return client.post(f"/v1/teams/{team_uuid}/retrieval:search", headers=_HEADERS, json=body)


def _port(app, client: TestClient, query: str, params: tuple[object, ...]) -> Any:
    async def inspect() -> Any:
        async with app.state.container.persistence.transaction() as tx:
            return await tx.fetchone(query, params)

    return client.portal.call(inspect)


def _ingest_published(app, client: TestClient) -> dict[str, Any]:
    team_uuid = uuid7()
    created = client.post(
        "/v1/teams",
        headers=_HEADERS,
        json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "reactivation lifecycle"},
    )
    assert created.status_code == 201, created.text
    _, ingest = _submit(
        client,
        team_uuid,
        "intake.ingest",
        {
            "source": {
                "source_kind": "inline_payload",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "test-fixture",
                "external_key": "reactivation-document",
                "content": _BODY,
            }
        },
    )
    assert ingest["status"] == "succeeded", ingest
    row = _port(
        app,
        client,
        "SELECT i.intake_item_uuid,i.latest_revision_uuid,i.serving_revision_uuid,i.lifecycle_state,"
        "i.row_revision,n.namespace_key FROM mkb_intake_items i "
        "JOIN mkb_vector_namespaces n ON n.team_uuid=i.team_uuid AND n.status='active' "
        "WHERE i.team_uuid=?",
        (team_uuid,),
    )
    assert row is not None
    assert row["serving_revision_uuid"] == row["latest_revision_uuid"]
    hit = _search(client, team_uuid, str(row["namespace_key"]))
    assert hit.status_code == 200, hit.text
    assert hit.json()["results"]
    omitted = _search(client, team_uuid, None)
    assert omitted.status_code == 422, omitted.text
    assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"
    return {"team_uuid": team_uuid, **dict(row)}


def test_reactivate_restores_active_lifecycle_but_not_stale_serving_state(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        published = _ingest_published(app, client)
        team_uuid = published["team_uuid"]
        item_uuid = published["intake_item_uuid"]
        namespace = str(published["namespace_key"])
        _, deactivated = _submit(client, team_uuid, "intake.deactivate", {"intake_item_uuid": item_uuid})
        assert deactivated["status"] == "succeeded", deactivated
        item = _port(
            app,
            client,
            "SELECT lifecycle_state,serving_revision_uuid,row_revision FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        pointer = _port(
            app,
            client,
            "SELECT lifecycle_state FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        vector = _port(
            app,
            client,
            "SELECT publication_state FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        assert item is not None and pointer is not None and vector is not None
        assert item["lifecycle_state"] == "deactivated"
        assert item["serving_revision_uuid"] is None
        assert pointer["lifecycle_state"] == "withdrawn"
        assert vector["publication_state"] == "withdrawn"
        empty = _search(client, team_uuid, namespace)
        assert empty.status_code == 200, empty.text
        assert empty.json()["results"] == []


def test_reactivate_search_empty_until_rebuild(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        published = _ingest_published(app, client)
        team_uuid = published["team_uuid"]
        item_uuid = published["intake_item_uuid"]
        revision_uuid = published["latest_revision_uuid"]
        namespace = str(published["namespace_key"])
        _, deactivated = _submit(client, team_uuid, "intake.deactivate", {"intake_item_uuid": item_uuid})
        assert deactivated["status"] == "succeeded", deactivated
        before = _port(
            app,
            client,
            "SELECT row_revision FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        assert before is not None
        reactivate_uuid, reactivated = _submit(
            client, team_uuid, "intake.reactivate", {"intake_item_uuid": item_uuid}
        )
        assert reactivated["status"] == "succeeded", reactivated
        item = _port(
            app,
            client,
            "SELECT lifecycle_state,serving_revision_uuid,row_revision FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        pointer = _port(
            app,
            client,
            "SELECT lifecycle_state FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        vector = _port(
            app,
            client,
            "SELECT publication_state FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        transition = _port(
            app,
            client,
            "SELECT action_key,before_lifecycle,after_lifecycle,after_serving_revision_uuid "
            "FROM mkb_intake_item_transitions WHERE team_uuid=? AND causation_task_uuid=?",
            (team_uuid, reactivate_uuid),
        )
        assert item is not None and pointer is not None and vector is not None and transition is not None
        assert item["lifecycle_state"] == "active"
        assert item["serving_revision_uuid"] is None
        assert item["row_revision"] == int(before["row_revision"]) + 1
        assert pointer["lifecycle_state"] == "withdrawn"
        assert vector["publication_state"] == "withdrawn"
        assert (
            transition["action_key"],
            transition["before_lifecycle"],
            transition["after_lifecycle"],
            transition["after_serving_revision_uuid"],
        ) == ("reactivate", "deactivated", "active", None)
        still_empty = _search(client, team_uuid, namespace)
        assert still_empty.status_code == 200, still_empty.text
        assert still_empty.json()["results"] == []
        _, rebuilt = _submit(
            client,
            team_uuid,
            "intake.rebuild",
            {"intake_item_uuid": item_uuid, "expected_intake_revision_uuid": revision_uuid},
        )
        assert rebuilt["status"] == "succeeded", rebuilt
        hit = _search(client, team_uuid, namespace)
        assert hit.status_code == 200, hit.text
        payloads = [str(item.get("payload_content") or "") for item in hit.json()["results"]]
        assert payloads and all(chunk in _BODY for chunk in payloads), payloads
        reconstructed = "".join(sorted(dict.fromkeys(payloads), key=_BODY.find))
        assert reconstructed == _BODY, payloads
        after = _port(
            app,
            client,
            "SELECT lifecycle_state,latest_revision_uuid,serving_revision_uuid FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        pointer_after = _port(
            app,
            client,
            "SELECT lifecycle_state FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        assert after is not None and pointer_after is not None
        assert after["lifecycle_state"] == "active"
        assert after["latest_revision_uuid"] == revision_uuid
        assert after["serving_revision_uuid"] == revision_uuid
        assert pointer_after["lifecycle_state"] == "active"
