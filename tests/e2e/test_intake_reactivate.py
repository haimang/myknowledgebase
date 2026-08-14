"""Public S04 regression for the reactivation lifecycle Task."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="reactivate-token",
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


def _wait_for_terminal(
    client: TestClient, *, team_uuid: str, task_uuid: str, headers: dict[str, str]
) -> dict[str, Any]:
    deadline = time.monotonic() + 8
    task: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.02)
    raise AssertionError(f"Task {task_uuid} did not become terminal: {task}")


def _submit_and_wait(
    client: TestClient,
    *,
    team_uuid: str,
    headers: dict[str, str],
    request_intent: str,
    payload: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    task_uuid, trace_uuid = uuid7(), uuid7()
    response = client.post(
        f"/v1/teams/{team_uuid}/tasks",
        headers=headers,
        json=_task_body(
            team_uuid=team_uuid,
            task_uuid=task_uuid,
            trace_uuid=trace_uuid,
            request_intent=request_intent,
            payload=payload,
        ),
    )
    assert response.status_code == 201, response.text
    return task_uuid, _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)


def _search(client: TestClient, *, team_uuid: str, headers: dict[str, str]) -> dict[str, Any]:
    response = client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers=headers,
        json={
            "schema_version": "mkb.retrieval.v1",
            "team_uuid": team_uuid,
            "query": "reactivation must require fresh publication",
            "return_k": 3,
            "recall_k": 5,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_reactivate_restores_active_lifecycle_but_not_stale_serving_state(tmp_path: Path) -> None:
    database_path = tmp_path / "mkb.sqlite3"
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer reactivate-token"}
    app = create_app(_settings(tmp_path))

    with TestClient(app, raise_server_exceptions=True) as client:
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "reactivation lifecycle"},
        )
        assert team.status_code == 201, team.text

        _, ingest = _submit_and_wait(
            client,
            team_uuid=team_uuid,
            headers=headers,
            request_intent="intake.ingest",
            payload={
                "source": {
                    "source_kind": "inline_payload",
                    "external_key": "reactivation-document",
                    "content": "Reactivation must require fresh publication before retrieval can serve this document.",
                }
            },
        )
        assert ingest["status"] == "succeeded", ingest
        with sqlite3.connect(database_path) as connection:
            item_uuid, revision_uuid, serving_revision_uuid = connection.execute(
                "SELECT intake_item_uuid,latest_revision_uuid,serving_revision_uuid FROM mkb_intake_items WHERE team_uuid=?",
                (team_uuid,),
            ).fetchone()
        assert serving_revision_uuid == revision_uuid

        _, deactivated = _submit_and_wait(
            client,
            team_uuid=team_uuid,
            headers=headers,
            request_intent="intake.deactivate",
            payload={"intake_item_uuid": item_uuid},
        )
        assert deactivated["status"] == "succeeded", deactivated
        with sqlite3.connect(database_path) as connection:
            deactivated_item_revision = connection.execute(
                "SELECT row_revision FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()[0]
        assert _search(client, team_uuid=team_uuid, headers=headers)["results"] == []

        reactivate_task_uuid, reactivated = _submit_and_wait(
            client,
            team_uuid=team_uuid,
            headers=headers,
            request_intent="intake.reactivate",
            payload={"intake_item_uuid": item_uuid},
        )
        assert reactivated["status"] == "succeeded", reactivated
        with sqlite3.connect(database_path) as connection:
            item = connection.execute(
                "SELECT lifecycle_state,serving_revision_uuid,row_revision FROM mkb_intake_items "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()
            pointer = connection.execute(
                "SELECT lifecycle_state FROM mkb_index_active_pointers "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()
            vector = connection.execute(
                "SELECT publication_state FROM mkb_vector_records "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()
            transition = connection.execute(
                "SELECT action_key,before_lifecycle,after_lifecycle,after_serving_revision_uuid "
                "FROM mkb_intake_item_transitions WHERE team_uuid=? AND causation_task_uuid=?",
                (team_uuid, reactivate_task_uuid),
            ).fetchone()
        assert item == ("active", None, deactivated_item_revision + 1)
        assert pointer == ("withdrawn",)
        assert vector == ("withdrawn",)
        assert transition == ("reactivate", "deactivated", "active", None)
        assert _search(client, team_uuid=team_uuid, headers=headers)["results"] == []

        _, rebuilt = _submit_and_wait(
            client,
            team_uuid=team_uuid,
            headers=headers,
            request_intent="intake.rebuild",
            payload={"intake_item_uuid": item_uuid, "expected_intake_revision_uuid": revision_uuid},
        )
        assert rebuilt["status"] == "succeeded", rebuilt
        search = _search(client, team_uuid=team_uuid, headers=headers)
        assert search["results"]
        assert search["results"][0]["payload_content"] == (
            "Reactivation must require fresh publication before retrieval can serve this document."
        )

    with sqlite3.connect(database_path) as connection:
        item = connection.execute(
            "SELECT lifecycle_state,latest_revision_uuid,serving_revision_uuid FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone()
        pointer = connection.execute(
            "SELECT lifecycle_state FROM mkb_index_active_pointers "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone()
    assert item == ("active", revision_uuid, revision_uuid)
    assert pointer == ("active",)
