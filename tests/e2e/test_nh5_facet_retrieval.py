"""NH5-T07 L4: default-root ingest produces SQL-filterable S04 facets."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.e2e.test_source_capability_paths import _settings


def _task(team_uuid: str, *, suffix: str, realm: str, channel: str) -> dict:
    task_uuid, trace_uuid = uuid7(), uuid7()
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {
            "json_prompt_id": "promptB.json.generic",
            "source": {
                "source_kind": "inline_payload",
                "external_key": f"nh5-{suffix}",
                "content": f"NH5 facet retrieval {suffix} admitted clean body",
                "realm": realm,
                "type": "article",
                "channel": channel,
                "source_name": f"source-{suffix}",
                "context_tags": [f"tag:{suffix}"],
            },
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nh5-facet",
            "created_at": utc_now(),
        },
    }


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict:
    deadline = time.monotonic() + 30
    latest = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def _search(client: TestClient, team_uuid: str, headers: dict[str, str], namespace: str | None, filters: dict):
    payload = {
        "schema_version": "mkb.retrieval.v2",
        "team_uuid": team_uuid,
        "query": "NH5 facet retrieval admitted clean",
        "filters": filters,
        "return_k": 20,
        "recall_k": 100,
    }
    if namespace is not None:
        payload["namespace_key"] = namespace
    return client.post(f"/v1/teams/{team_uuid}/retrieval:search", headers=headers, json=payload)


def test_realm_or_semantic_channel_hit_and_exclude_at_sql(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer source-capability-token"}
    alpha = _task(team_uuid, suffix="alpha", realm="realm-alpha", channel="channel-alpha")
    beta = _task(team_uuid, suffix="beta", realm="realm-beta", channel="channel-beta")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh5-facets"},
        ).status_code == 201
        for request in (alpha, beta):
            response = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=request)
            assert response.status_code == 201, response.text
            terminal = _wait(client, team_uuid, request["task_uuid"], headers)
            assert terminal["status"] == "succeeded", terminal

        async def coordinates() -> tuple[str, dict[str, str], dict]:
            async with app.state.container.persistence.transaction() as tx:
                namespace = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
                items = await tx.fetchall(
                    "SELECT normalized_external_key,intake_item_uuid FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
                facets = await tx.fetchone(
                    "SELECT COUNT(DISTINCT facet_key) AS keys,COUNT(*) AS rows "
                    "FROM mkb_vector_record_facets WHERE team_uuid=? AND facet_key IN "
                    "('realm','type','channel','source_name','is_active','context_tags')",
                    (team_uuid,),
                )
            assert namespace is not None and facets is not None
            return str(namespace["namespace_key"]), {
                row["normalized_external_key"]: row["intake_item_uuid"] for row in items
            }, facets

        namespace, items, facets = client.portal.call(coordinates)
        assert facets["keys"] == 6 and facets["rows"] > 0
        no_namespace = _search(client, team_uuid, headers, None, {"realm": "realm-alpha"})
        assert no_namespace.status_code == 422
        assert no_namespace.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"
        unknown = _search(client, team_uuid, headers, namespace, {"forbidden": "x"})
        assert unknown.status_code == 422
        assert unknown.json()["error"]["code"] == "RETRIEVE_FILTER_INVALID"

        by_realm = _search(
            client,
            team_uuid,
            headers,
            namespace,
            {"realm": "realm-alpha", "vector_channel": "summary"},
        )
        assert by_realm.status_code == 200, by_realm.text
        realm_results = by_realm.json()["results"]
        assert realm_results

        async def result_item_ids(results: list[dict]) -> set[str]:
            generations = sorted({result["coordinate"]["generation_artifact_uuid"] for result in results})
            async with app.state.container.persistence.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT DISTINCT intake_item_uuid FROM mkb_generation_artifacts WHERE team_uuid=? "
                    f"AND generation_artifact_uuid IN ({','.join('?' for _ in generations)})",
                    (team_uuid, *generations),
                )
            return {str(row["intake_item_uuid"]) for row in rows}

        assert client.portal.call(result_item_ids, realm_results) == {items["nh5-alpha"]}

        by_channel = _search(
            client,
            team_uuid,
            headers,
            namespace,
            {"semantic_channel": "channel-beta", "vector_channel": "original"},
        )
        assert by_channel.status_code == 200, by_channel.text
        channel_results = by_channel.json()["results"]
        assert channel_results
        assert client.portal.call(result_item_ids, channel_results) == {items["nh5-beta"]}
