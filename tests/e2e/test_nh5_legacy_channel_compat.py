"""NH5-T06: v1 channel is a narrow vector-axis adapter only."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from tests.e2e.test_nh5_facet_retrieval import _task, _wait
from tests.e2e.test_source_capability_paths import _settings


def test_v1_channel_original_maps_to_vector_channel(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer source-capability-token"}
    task = _task(team_uuid, suffix="legacy", realm="realm-legacy", channel="semantic-legacy")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh5-legacy"},
        ).status_code == 201
        assert client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=task).status_code == 201
        assert _wait(client, team_uuid, task["task_uuid"], headers)["status"] == "succeeded"

        async def namespace() -> str:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["namespace_key"])

        response = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "namespace_key": client.portal.call(namespace),
                "query": "legacy original",
                "filters": {"channel": "original"},
            },
        )
        assert response.status_code == 200, response.text


def test_v1_channel_web_422(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers={"Authorization": "Bearer source-capability-token"},
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "namespace_key": "not-reached",
                "query": "query",
                "filters": {"channel": "web"},
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "RETRIEVE_FILTER_INVALID"


def test_new_schema_legacy_channel_key_422(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers={"Authorization": "Bearer source-capability-token"},
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": "not-reached",
                "query": "query",
                "filters": {"channel": "original"},
            },
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "RETRIEVE_FILTER_INVALID"
