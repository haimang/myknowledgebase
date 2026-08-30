"""NH8-T07: index.rebuild cuts a new generation without Revision/source/clean."""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings

_TOKEN = "index-rebuild-token"
_HEADERS = {"Authorization": f"Bearer {_TOKEN}"}
_BODY = "A retained document must survive an index generation rebuild."
_STALE_BODY = "The old active generation remains grounded after a rejected rebuild."


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
        "source": "index-rebuild-e2e",
        "created_at": utc_now(),
    }


def _wait(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, Any]:
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


def _search(client: TestClient, team_uuid: str, namespace: str | None, query: str):
    body: dict[str, Any] = {
        "schema_version": "mkb.retrieval.v2",
        "team_uuid": team_uuid,
        "query": query,
        "filters": {"vector_channel": "original"},
        "return_k": 10,
        "recall_k": 20,
    }
    if namespace is not None:
        body["namespace_key"] = namespace
    return client.post(f"/v1/teams/{team_uuid}/retrieval:search", headers=_HEADERS, json=body)


def _ingest(client: TestClient, team_uuid: str, content: str, external_key: str) -> str:
    task_uuid, trace_uuid = uuid7(), uuid7()
    created = client.post(
        f"/v1/teams/{team_uuid}/tasks",
        headers=_HEADERS,
        json={
            "schema_version": "mkb.task.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "request_intent": "intake.ingest",
            "payload": {
                "json_prompt_id": "promptB.json.generic",
                "source": {
                    "source_kind": "inline_payload",
                    "realm": "documentation",
                    "type": "article",
                    "channel": "general",
                    "source_name": "test-fixture",
                    "external_key": external_key,
                    "content": content,
                },
            },
            "audit": _audit(team_uuid, task_uuid, trace_uuid),
        },
    )
    assert created.status_code == 201, created.text
    terminal = _wait(client, team_uuid, task_uuid)
    assert terminal["status"] == "succeeded", terminal
    return task_uuid


def test_scoped_index_rebuild_promotes_generation_without_new_intake_revision(tmp_path: Path) -> None:
    """A successful rebuild must cut over only after a complete new index set."""

    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        created_team = client.post(
            "/v1/teams",
            headers=_HEADERS,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "index rebuild regression"},
        )
        assert created_team.status_code == 201, created_team.text
        _ingest(client, team_uuid, _BODY, "index-rebuild-document")
        before = _port(
            app,
            client,
            "SELECT i.intake_item_uuid,i.latest_revision_uuid,i.serving_revision_uuid,"
            "p.active_index_generation,p.pointer_row_revision,p.last_proof_uuid,n.namespace_key "
            "FROM mkb_intake_items i "
            "JOIN mkb_index_active_pointers p ON p.team_uuid=i.team_uuid AND p.intake_item_uuid=i.intake_item_uuid "
            "JOIN mkb_vector_namespaces n ON n.team_uuid=i.team_uuid AND n.status='active' "
            "WHERE i.team_uuid=?",
            (team_uuid,),
        )
        assert before is not None
        assert int(before["active_index_generation"]) == 1
        revisions = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, before["intake_item_uuid"]),
        )
        assert revisions is not None and int(revisions["n"]) == 1
        omitted = _search(client, team_uuid, None, "retained document index generation rebuild")
        assert omitted.status_code == 422
        assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"

        rebuild_task_uuid, rebuild_trace_uuid = uuid7(), uuid7()
        created_rebuild = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": rebuild_task_uuid,
                "trace_uuid": rebuild_trace_uuid,
                "request_intent": "index.rebuild",
                "payload": {"scope": "intake_item", "intake_item_uuid": before["intake_item_uuid"]},
                "audit": _audit(team_uuid, rebuild_task_uuid, rebuild_trace_uuid),
            },
        )
        assert created_rebuild.status_code == 201, created_rebuild.text
        terminal = _wait(client, team_uuid, rebuild_task_uuid)
        assert terminal["status"] == "succeeded", terminal

        search = _search(client, team_uuid, str(before["namespace_key"]), "retained document index generation rebuild")
        assert search.status_code == 200, search.text
        results = search.json()["results"]
        assert results
        payloads = [str(item.get("payload_content") or "") for item in results]
        assert any(_BODY in payload or payload in _BODY for payload in payloads), payloads

        item = _port(
            app,
            client,
            "SELECT latest_revision_uuid,serving_revision_uuid FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, before["intake_item_uuid"]),
        )
        assert item is not None
        assert item["latest_revision_uuid"] == before["latest_revision_uuid"]
        assert item["serving_revision_uuid"] == before["serving_revision_uuid"]
        after_revisions = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, before["intake_item_uuid"]),
        )
        assert after_revisions is not None and int(after_revisions["n"]) == 1
        pointer = _port(
            app,
            client,
            "SELECT active_index_generation,pointer_row_revision,last_proof_uuid,lifecycle_state "
            "FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, before["intake_item_uuid"]),
        )
        assert pointer is not None
        assert int(pointer["active_index_generation"]) == 2
        assert int(pointer["pointer_row_revision"]) == int(before["pointer_row_revision"]) + 1
        assert pointer["last_proof_uuid"] != before["last_proof_uuid"]
        assert pointer["lifecycle_state"] == "active"
        new_gen = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=? "
            "AND index_generation=2 AND publication_state='indexed' AND deleted_at IS NULL",
            (team_uuid, before["intake_item_uuid"]),
        )
        old_gen = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=? "
            "AND index_generation=1 AND deleted_at IS NULL",
            (team_uuid, before["intake_item_uuid"]),
        )
        assert new_gen is not None and int(new_gen["n"]) > 0
        assert old_gen is not None and int(old_gen["n"]) > 0
        artifact_uuids = [
            str(item["coordinate"]["generation_artifact_uuid"])
            for item in results
            if isinstance(item.get("coordinate"), dict) and item["coordinate"].get("generation_artifact_uuid")
        ]
        assert artifact_uuids
        hit_generations = {
            int(row["index_generation"])
            for artifact in artifact_uuids
            for row in [
                _port(
                    app,
                    client,
                    "SELECT index_generation FROM mkb_vector_records "
                    "WHERE team_uuid=? AND generation_artifact_uuid=? LIMIT 1",
                    (team_uuid, artifact),
                )
            ]
            if row is not None
        }
        assert hit_generations == {2}
        processes = _port_all(
            app,
            client,
            "SELECT process_key,status FROM mkb_processes WHERE team_uuid=? AND task_uuid=? ORDER BY created_at",
            (team_uuid, rebuild_task_uuid),
        )
        assert [(row["process_key"], row["status"]) for row in processes] == [("index.rebuild", "succeeded")]


@pytest.mark.parametrize(
    ("drift", "expected_error"),
    [
        ("item", "INDEX_REBUILD_TARGET_STALE"),
        ("pointer", "INDEX_REBUILD_POINTER_FENCE"),
    ],
)
def test_index_rebuild_stale_fence_fails_without_cutover_and_old_generation_remains_retrievable(
    tmp_path: Path,
    drift: str,
    expected_error: str,
) -> None:
    """A stale source or selection pointer must fail closed before promotion."""

    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        team = client.post(
            "/v1/teams",
            headers=_HEADERS,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": f"index rebuild stale {drift}"},
        )
        assert team.status_code == 201, team.text
        _ingest(client, team_uuid, _STALE_BODY, f"index-rebuild-stale-{drift}")
        before = _port(
            app,
            client,
            "SELECT i.intake_item_uuid,p.active_index_generation,p.pointer_row_revision,p.last_proof_uuid,"
            "n.namespace_key FROM mkb_intake_items i "
            "JOIN mkb_index_active_pointers p ON p.team_uuid=i.team_uuid AND p.intake_item_uuid=i.intake_item_uuid "
            "JOIN mkb_vector_namespaces n ON n.team_uuid=i.team_uuid AND n.status='active' "
            "WHERE i.team_uuid=?",
            (team_uuid,),
        )
        assert before is not None
        item_uuid = str(before["intake_item_uuid"])
        pipeline = app.state.container.workflow_worker.handler
        original_plan = pipeline._plan_index_rebuild  # type: ignore[attr-defined]

        async def plan_then_drift(frozen_team_uuid: str, scope: object) -> object:
            plans = await original_plan(frozen_team_uuid, scope)
            async with app.state.container.persistence.transaction() as tx:
                if drift == "item":
                    changed = await tx.execute(
                        "UPDATE mkb_intake_items SET row_revision=row_revision+1 "
                        "WHERE team_uuid=? AND intake_item_uuid=?",
                        (team_uuid, item_uuid),
                    )
                else:
                    changed = await tx.execute(
                        "UPDATE mkb_index_active_pointers "
                        "SET pointer_row_revision=pointer_row_revision+1 "
                        "WHERE team_uuid=? AND intake_item_uuid=?",
                        (team_uuid, item_uuid),
                    )
            assert changed.rowcount == 1
            return plans

        pipeline._plan_index_rebuild = plan_then_drift  # type: ignore[attr-defined]
        rebuild_task_uuid, rebuild_trace_uuid = uuid7(), uuid7()
        rebuild = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_HEADERS,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": rebuild_task_uuid,
                "trace_uuid": rebuild_trace_uuid,
                "request_intent": "index.rebuild",
                "payload": {"scope": "intake_item", "intake_item_uuid": item_uuid},
                "audit": _audit(team_uuid, rebuild_task_uuid, rebuild_trace_uuid),
            },
        )
        assert rebuild.status_code == 201, rebuild.text
        terminal = _wait(client, team_uuid, rebuild_task_uuid)
        assert terminal["status"] == "failed", terminal
        assert terminal["error"] is not None
        assert terminal["error"]["code"] == expected_error
        search = _search(client, team_uuid, str(before["namespace_key"]), "old active generation grounded")
        assert search.status_code == 200, search.text
        payloads = [str(item.get("payload_content") or "") for item in search.json()["results"]]
        assert payloads and all(chunk in _STALE_BODY or _STALE_BODY in chunk for chunk in payloads), payloads
        pointer = _port(
            app,
            client,
            "SELECT active_index_generation,pointer_row_revision,last_proof_uuid "
            "FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        assert pointer is not None
        assert int(pointer["active_index_generation"]) == int(before["active_index_generation"]) == 1
        assert pointer["last_proof_uuid"] == before["last_proof_uuid"]
        expected_pointer_revision = int(before["pointer_row_revision"]) + (1 if drift == "pointer" else 0)
        assert int(pointer["pointer_row_revision"]) == expected_pointer_revision
        gen2 = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=? "
            "AND index_generation=2",
            (team_uuid, item_uuid),
        )
        proofs = _port(
            app,
            client,
            "SELECT COUNT(*) AS n FROM mkb_publication_proofs WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        )
        assert gen2 is not None and int(gen2["n"]) == 0
        assert proofs is not None and int(proofs["n"]) == 1
        processes = _port_all(
            app,
            client,
            "SELECT process_key,status,error_code FROM mkb_processes "
            "WHERE team_uuid=? AND task_uuid=? ORDER BY created_at",
            (team_uuid, rebuild_task_uuid),
        )
        assert [(row["process_key"], row["status"], row["error_code"]) for row in processes] == [
            ("index.rebuild", "failed", expected_error)
        ]
