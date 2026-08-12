"""Public lifecycle regressions for rebuild and metadata-only intake commands."""

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
        internal_token="intake-lifecycle-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        live_inference=False,
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
        "source": "intake-lifecycle-e2e",
        "created_at": utc_now(),
    }


def _task_body(
    *,
    team_uuid: str,
    task_uuid: str,
    trace_uuid: str,
    request_intent: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": request_intent,
        "payload": payload,
        "audit": _audit(team_uuid, task_uuid, trace_uuid),
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


def _read_item(connection: sqlite3.Connection, team_uuid: str) -> tuple[str, str, str, int]:
    row = connection.execute(
        "SELECT intake_item_uuid,latest_revision_uuid,serving_revision_uuid,row_revision "
        "FROM mkb_intake_items WHERE team_uuid=?",
        (team_uuid,),
    ).fetchone()
    assert row is not None
    return row


def test_rebuild_and_metadata_lifecycle_paths_complete_through_public_http(tmp_path: Path) -> None:
    """Rebuild preserves canonical revisions; metadata changes append and publish one."""

    database_path = tmp_path / "mkb.sqlite3"
    token = "intake-lifecycle-token"
    headers = {"Authorization": f"Bearer {token}"}
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))

    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "intake lifecycle"},
        )
        assert response.status_code == 201, response.text

        ingest_task_uuid, ingest_trace_uuid = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task_body(
                team_uuid=team_uuid,
                task_uuid=ingest_task_uuid,
                trace_uuid=ingest_trace_uuid,
                request_intent="intake.ingest",
                payload={
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "lifecycle-document",
                        "content": "Lifecycle operations retain and serve this document.",
                    }
                },
            ),
        )
        assert response.status_code == 201, response.text
        assert _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=ingest_task_uuid, headers=headers)["status"] == "succeeded"

        with sqlite3.connect(database_path) as connection:
            item_uuid, original_revision_uuid, serving_revision_uuid, _ = _read_item(connection, team_uuid)
            assert serving_revision_uuid == original_revision_uuid
            original_generation = connection.execute(
                "SELECT active_index_generation FROM mkb_index_active_pointers "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()
            assert original_generation == (1,)

        rebuild_task_uuid, rebuild_trace_uuid = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task_body(
                team_uuid=team_uuid,
                task_uuid=rebuild_task_uuid,
                trace_uuid=rebuild_trace_uuid,
                request_intent="intake.rebuild",
                payload={
                    "intake_item_uuid": item_uuid,
                    "expected_intake_revision_uuid": original_revision_uuid,
                },
            ),
        )
        assert response.status_code == 201, response.text
        rebuild = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=rebuild_task_uuid, headers=headers)
        assert rebuild["status"] == "succeeded", rebuild

        with sqlite3.connect(database_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone() == (1,)
            assert _read_item(connection, team_uuid)[1:3] == (original_revision_uuid, original_revision_uuid)
            assert connection.execute(
                "SELECT active_index_generation FROM mkb_index_active_pointers "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone() == (2,)

        no_change_task_uuid, no_change_trace_uuid = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task_body(
                team_uuid=team_uuid,
                task_uuid=no_change_task_uuid,
                trace_uuid=no_change_trace_uuid,
                request_intent="intake.update_metadata",
                payload={"intake_item_uuid": item_uuid, "semantics": {"context_metadata": "{}"}},
            ),
        )
        assert response.status_code == 201, response.text
        no_change = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=no_change_task_uuid, headers=headers)
        assert no_change["status"] == "succeeded", no_change

        with sqlite3.connect(database_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone() == (1,)
            assert _read_item(connection, team_uuid)[1:3] == (original_revision_uuid, original_revision_uuid)
            assert connection.execute(
                "SELECT active_index_generation FROM mkb_index_active_pointers "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone() == (2,)
            assert connection.execute(
                "SELECT action_key FROM mkb_intake_item_transitions "
                "WHERE team_uuid=? AND causation_task_uuid=?",
                (team_uuid, no_change_task_uuid),
            ).fetchone() == ("no_change",)

        metadata_task_uuid, metadata_trace_uuid = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task_body(
                team_uuid=team_uuid,
                task_uuid=metadata_task_uuid,
                trace_uuid=metadata_trace_uuid,
                request_intent="intake.update_metadata",
                payload={"intake_item_uuid": item_uuid, "semantics": {"context_metadata": "tier=gold"}},
            ),
        )
        assert response.status_code == 201, response.text
        metadata = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=metadata_task_uuid, headers=headers)
        assert metadata["status"] == "succeeded", metadata

        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "query": "lifecycle document",
                "return_k": 1,
                "recall_k": 3,
            },
        )
        assert search.status_code == 200, search.text
        assert search.json()["results"][0]["payload_content"] == "Lifecycle operations retain and serve this document."

    with sqlite3.connect(database_path) as connection:
        item_uuid_after, latest_revision_uuid, serving_revision_uuid, _ = _read_item(connection, team_uuid)
        assert item_uuid_after == item_uuid
        assert latest_revision_uuid != original_revision_uuid
        assert serving_revision_uuid == latest_revision_uuid
        assert connection.execute(
            "SELECT COUNT(*) FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT active_index_generation FROM mkb_index_active_pointers "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone() == (3,)
        assert connection.execute(
            "SELECT intake_revision_uuid,index_generation FROM mkb_publication_proofs "
            "WHERE team_uuid=? AND intake_item_uuid=? ORDER BY created_at DESC LIMIT 1",
            (team_uuid, item_uuid),
        ).fetchone() == (latest_revision_uuid, 3)
        semantic = connection.execute(
            "SELECT value_text FROM mkb_intake_revision_semantics "
            "WHERE team_uuid=? AND intake_revision_uuid=? AND semantic_key='context_metadata'",
            (team_uuid, latest_revision_uuid),
        ).fetchone()
        assert semantic == ("tier=gold",)
