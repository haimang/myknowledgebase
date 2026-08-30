"""NH8-T02/T03: rebuild/metadata replay frozen clean without acquire/decode/clean."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings

_TOKEN = "intake-lifecycle-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}
_GOLDEN = "Lifecycle operations retain and serve this document."
_FORBIDDEN_PREFIXES = ("intake.acquire.", "intake.decode.", "clean.")


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
    if request_intent == "intake.ingest":
        payload = {"json_prompt_id": "promptB.json.generic", **payload}
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": request_intent,
        "payload": payload,
        "audit": _audit(team_uuid, task_uuid, trace_uuid),
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


def _post_task(client: TestClient, team_uuid: str, request_intent: str, payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
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


def _search(client: TestClient, team_uuid: str, namespace: str | None, query: str, filters: dict[str, str] | None = None):
    body: dict[str, Any] = {
        "schema_version": "mkb.retrieval.v2",
        "team_uuid": team_uuid,
        "query": query,
        "return_k": 10,
        "recall_k": 20,
    }
    if namespace is not None:
        body["namespace_key"] = namespace
    if filters:
        body["filters"] = filters
    return client.post(f"/v1/teams/{team_uuid}/retrieval:search", headers=_HEADERS, json=body)


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


def _ingest(client: TestClient, team_uuid: str, *, realm: str = "documentation", content: str = _GOLDEN) -> str:
    _, terminal = _post_task(
        client,
        team_uuid,
        "intake.ingest",
        {
            "source": {
                "source_kind": "inline_payload",
                "realm": realm,
                "type": "article",
                "channel": "general",
                "source_name": "test-fixture",
                "external_key": f"lifecycle-{uuid7()}",
                "content": content,
            }
        },
    )
    assert terminal["status"] == "succeeded", terminal
    return team_uuid


def _item_state(app, client: TestClient, team_uuid: str) -> dict[str, Any]:
    row = _port(
        app,
        client,
        "SELECT i.intake_item_uuid,i.latest_revision_uuid,i.serving_revision_uuid,"
        "a.content_digest,a.stored_object_uuid,p.active_index_generation,n.namespace_key "
        "FROM mkb_intake_items i "
        "JOIN mkb_intake_artifacts a ON a.team_uuid=i.team_uuid "
        "AND a.owner_revision_uuid=i.latest_revision_uuid AND a.artifact_role='clean_text' "
        "JOIN mkb_index_active_pointers p ON p.team_uuid=i.team_uuid AND p.intake_item_uuid=i.intake_item_uuid "
        "JOIN mkb_vector_namespaces n ON n.team_uuid=i.team_uuid AND n.status='active' "
        "WHERE i.team_uuid=?",
        (team_uuid,),
    )
    assert row is not None
    return dict(row)


def _forbidden_process_count(app, client: TestClient, team_uuid: str, task_uuid: str) -> tuple[int, set[str]]:
    rows = _port_all(
        app,
        client,
        "SELECT process_key FROM mkb_processes WHERE team_uuid=? AND task_uuid=?",
        (team_uuid, task_uuid),
    )
    keys = {str(row["process_key"]) for row in rows}
    forbidden = {key for key in keys if key.startswith(_FORBIDDEN_PREFIXES)}
    return len(forbidden), keys


def _create_team(client: TestClient) -> str:
    team_uuid = uuid7()
    created = client.post(
        "/v1/teams",
        headers=_HEADERS,
        json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "intake lifecycle"},
    )
    assert created.status_code == 201, created.text
    return team_uuid


def test_rebuild_replays_frozen_clean_without_acquire_decode_clean(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        team_uuid = _create_team(client)
        _ingest(client, team_uuid)
        before = _item_state(app, client, team_uuid)
        omitted = _search(client, team_uuid, None, _GOLDEN)
        assert omitted.status_code == 422, omitted.text
        assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"
        rebuild_uuid, rebuild = _post_task(
            client,
            team_uuid,
            "intake.rebuild",
            {
                "intake_item_uuid": before["intake_item_uuid"],
                "expected_intake_revision_uuid": before["latest_revision_uuid"],
            },
        )
        assert rebuild["status"] == "succeeded", rebuild
        after = _item_state(app, client, team_uuid)
        forbidden, keys = _forbidden_process_count(app, client, team_uuid, rebuild_uuid)
        assert forbidden == 0, keys
        assert "intake.replay_frozen_clean" in keys
        assert after["latest_revision_uuid"] == before["latest_revision_uuid"]
        assert after["content_digest"] == before["content_digest"]
        assert after["stored_object_uuid"] == before["stored_object_uuid"]
        assert after["active_index_generation"] == int(before["active_index_generation"]) + 1
        hit = _search(client, team_uuid, str(before["namespace_key"]), "lifecycle document")
        assert hit.status_code == 200, hit.text
        results = hit.json()["results"]
        assert results
        assert results[0]["payload_content"] == _GOLDEN
        revision_count = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, before["intake_item_uuid"]),
        )
        assert int(revision_count["n"]) == 1


def test_metadata_no_change_changed_zero_acquire_decode_clean(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        team_uuid = _create_team(client)
        _ingest(client, team_uuid, realm="realm-before")
        before = _item_state(app, client, team_uuid)
        no_change_uuid, no_change = _post_task(
            client,
            team_uuid,
            "intake.update_metadata",
            {"intake_item_uuid": before["intake_item_uuid"], "semantics": {"realm": "realm-before"}},
        )
        assert no_change["status"] == "succeeded", no_change
        after_no_change = _item_state(app, client, team_uuid)
        forbidden_no_change, keys_no_change = _forbidden_process_count(app, client, team_uuid, no_change_uuid)
        assert forbidden_no_change == 0, keys_no_change
        assert "intake.metadata_no_change" in keys_no_change
        assert after_no_change["latest_revision_uuid"] == before["latest_revision_uuid"]
        assert after_no_change["active_index_generation"] == before["active_index_generation"]
        transition = _port(
            app,
            client,
            "SELECT action_key FROM mkb_intake_item_transitions WHERE team_uuid=? AND causation_task_uuid=?",
            (team_uuid, no_change_uuid),
        )
        assert transition is not None and transition["action_key"] == "no_change"
        still_hits = _search(
            client,
            team_uuid,
            str(before["namespace_key"]),
            "lifecycle document",
            {"realm": "realm-before"},
        )
        assert still_hits.status_code == 200, still_hits.text
        assert still_hits.json()["results"]

        changed_uuid, changed = _post_task(
            client,
            team_uuid,
            "intake.update_metadata",
            {"intake_item_uuid": before["intake_item_uuid"], "semantics": {"realm": "realm-after"}},
        )
        assert changed["status"] == "succeeded", changed
        after = _item_state(app, client, team_uuid)
        forbidden, keys = _forbidden_process_count(app, client, team_uuid, changed_uuid)
        assert forbidden == 0, keys
        assert "intake.replay_frozen_clean" in keys
        assert "lsrag.structurize" not in keys
        assert after["latest_revision_uuid"] != before["latest_revision_uuid"]
        assert after["content_digest"] == before["content_digest"]
        assert after["stored_object_uuid"] == before["stored_object_uuid"]
        omitted = _search(client, team_uuid, None, _GOLDEN)
        assert omitted.status_code == 422
        assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"
        new_hits = _search(
            client,
            team_uuid,
            str(before["namespace_key"]),
            "lifecycle document",
            {"realm": "realm-after"},
        )
        old_hits = _search(
            client,
            team_uuid,
            str(before["namespace_key"]),
            "lifecycle document",
            {"realm": "realm-before"},
        )
        assert new_hits.status_code == 200, new_hits.text
        assert new_hits.json()["results"]
        assert new_hits.json()["results"][0]["payload_content"] == _GOLDEN
        assert old_hits.status_code == 200, old_hits.text
        assert old_hits.json()["results"] == []


def test_rebuild_and_metadata_lifecycle_paths_complete_through_public_http(tmp_path: Path) -> None:
    """Metadata refresh reuses S06/source summaries and recalculates S07/S08."""

    app = create_app(_settings(tmp_path))
    with TestClient(app, raise_server_exceptions=True) as client:
        team_uuid = _create_team(client)
        _ingest(client, team_uuid)
        original = _item_state(app, client, team_uuid)
        rebuild_uuid, rebuild = _post_task(
            client,
            team_uuid,
            "intake.rebuild",
            {
                "intake_item_uuid": original["intake_item_uuid"],
                "expected_intake_revision_uuid": original["latest_revision_uuid"],
            },
        )
        assert rebuild["status"] == "succeeded", rebuild
        after_rebuild = _item_state(app, client, team_uuid)
        assert after_rebuild["latest_revision_uuid"] == original["latest_revision_uuid"]
        assert after_rebuild["active_index_generation"] == int(original["active_index_generation"]) + 1
        forbidden, _ = _forbidden_process_count(app, client, team_uuid, rebuild_uuid)
        assert forbidden == 0

        no_change_uuid, no_change = _post_task(
            client,
            team_uuid,
            "intake.update_metadata",
            {"intake_item_uuid": original["intake_item_uuid"], "semantics": {"realm": "documentation"}},
        )
        assert no_change["status"] == "succeeded", no_change
        after_no_change = _item_state(app, client, team_uuid)
        assert after_no_change["latest_revision_uuid"] == original["latest_revision_uuid"]
        transition = _port(
            app,
            client,
            "SELECT action_key FROM mkb_intake_item_transitions WHERE team_uuid=? AND causation_task_uuid=?",
            (team_uuid, no_change_uuid),
        )
        assert transition is not None and transition["action_key"] == "no_change"

        metadata_uuid, metadata = _post_task(
            client,
            team_uuid,
            "intake.update_metadata",
            {"intake_item_uuid": original["intake_item_uuid"], "semantics": {"realm": "documentation", "type": "policy"}},
        )
        assert metadata["status"] == "succeeded", metadata
        after = _item_state(app, client, team_uuid)
        assert after["latest_revision_uuid"] != original["latest_revision_uuid"]
        assert after["serving_revision_uuid"] == after["latest_revision_uuid"]
        assert after["content_digest"] == original["content_digest"]
        search = _search(client, team_uuid, str(original["namespace_key"]), "lifecycle document")
        assert search.status_code == 200, search.text
        assert search.json()["results"][0]["payload_content"] == _GOLDEN
        artifacts = {
            str(row["artifact_type"])
            for row in _port_all(
                app,
                client,
                "SELECT artifact_type FROM mkb_generation_artifacts WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, metadata_uuid),
            )
        }
        processes, _ = _forbidden_process_count(app, client, team_uuid, metadata_uuid)
        keys = _port_all(
            app,
            client,
            "SELECT process_key FROM mkb_processes WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, metadata_uuid),
        )
        process_keys = {str(row["process_key"]) for row in keys}
        assert processes == 0
        assert "lsrag.structurize" not in process_keys
        assert {
            "construction_document",
            "dual_channel_projection",
            "construction_validation_report",
        } <= artifacts
