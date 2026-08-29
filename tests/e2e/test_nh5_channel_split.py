"""NH5-T05 L3: the v2 wire accepts both channel axes in one request."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from tests.e2e.test_nh5_facet_retrieval import _task, _wait
from tests.e2e.test_source_capability_paths import _settings


def test_new_schema_dual_channel_same_request(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer source-capability-token"}
    task = _task(team_uuid, suffix="dual", realm="realm-dual", channel="semantic-dual")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh5-dual"},
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
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": client.portal.call(namespace),
                "query": "facet retrieval dual",
                "filters": {"semantic_channel": "semantic-dual", "vector_channel": "summary"},
                "return_k": 5,
                "recall_k": 10,
            },
        )
        assert response.status_code == 200, response.text
        assert response.json()["disposition"] == "ok"
        assert response.json()["results"]
