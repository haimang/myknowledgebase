"""NH7-T03: inline and HTTP static reach namespaced facet retrieval."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.e2e.test_source_capability_paths import _settings
from tests.nh6_runtime_support import local_spa_server


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer source-capability-token"}


def _wait(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, object]:
    deadline = time.monotonic() + 40
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_headers())
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def _search(client: TestClient, team_uuid: str, namespace: str, query: str, filters: dict[str, str]):
    return client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers=_headers(),
        json={
            "schema_version": "mkb.retrieval.v2",
            "team_uuid": team_uuid,
            "namespace_key": namespace,
            "query": query,
            "filters": filters,
            "return_k": 20,
            "recall_k": 100,
        },
    )


def test_inline_doc_deterministic_namespace_facet_hit(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    sentinel = "NH7 inline admitted clean sentinel"
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_headers(),
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-inline"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_headers(),
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
                        "external_key": "nh7-inline",
                        "content": sentinel,
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-inline-source",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t03",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal

        async def namespace_key() -> str:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["namespace_key"])

        namespace = client.portal.call(namespace_key)
        omitted = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_headers(),
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "query": sentinel,
                "filters": {"vector_channel": "original"},
                "return_k": 5,
                "recall_k": 20,
            },
        )
        assert omitted.status_code == 422
        assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"
        found = _search(
            client,
            team_uuid,
            namespace,
            sentinel,
            {"realm": "documentation", "vector_channel": "original"},
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"]


def test_http_static_web_deterministic_namespace_facet_hit(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with local_spa_server() as (origin, marker), TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_headers(),
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-static"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=_headers(),
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "http_resource",
                        "external_key": "nh7-static",
                        "url": f"{origin}/static",
                        "acquisition_mode": "static",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-static-source",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t03",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal

        async def namespace_key() -> str:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["namespace_key"])

        namespace = client.portal.call(namespace_key)
        found = _search(
            client,
            team_uuid,
            namespace,
            "static capability text",
            {"source_name": "nh7-static-source", "vector_channel": "original"},
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"]
        del marker
