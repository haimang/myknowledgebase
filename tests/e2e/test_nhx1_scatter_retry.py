"""NHX1-T06: failed Observation retry reuses the durable key and adds an attempt."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.local_runtime import local_mock_settings


def _payload(
    team_uuid: str,
    task_uuid: str,
    trace_uuid: str,
    *,
    retry: bool = False,
) -> dict[str, object]:
    source: dict[str, object] = {
        "source_kind": "http_resource",
        "realm": "documentation",
        "type": "article",
        "channel": "general",
        "source_name": "nhx1-retry",
        "external_key": "failed-observation",
        "observation_key": "failed-observation-key",
        "url": "http://127.0.0.1:9/nhx1-unavailable",
        "acquisition_mode": "static",
    }
    if retry:
        source["retry_failed_observation"] = True
        source["expected_observation_attempt_generation"] = 1
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {"json_prompt_id": "promptB.json.generic", "source": source},
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nhx1",
            "created_at": utc_now(),
        },
    }


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 30
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    raise AssertionError(latest)


def test_failed_observation_retry_adds_attempt_without_new_source_or_snapshot(tmp_path: Path) -> None:
    token = "nhx1-retry-token"
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            internal_token=token,
            inference_probe_enabled=False,
            live_inference=False,
            egress_allow_private_default=False,
            egress_allow_http=True,
        )
    )
    team_uuid, first_uuid, retry_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "retry"},
        ).status_code == 201
        first_trace = uuid7()
        first = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_payload(team_uuid, first_uuid, first_trace),
        )
        assert first.status_code == 201, first.text
        assert _wait(client, team_uuid, first_uuid, headers)["status"] == "failed"
        retry_trace = uuid7()
        retry = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_payload(team_uuid, retry_uuid, retry_trace, retry=True),
        )
        assert retry.status_code == 201, retry.text
        assert _wait(client, team_uuid, retry_uuid, headers)["status"] == "failed"

        async def inspect() -> dict[str, object]:
            async with app.state.container.persistence.read_snapshot() as tx:
                sources = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_intake_sources WHERE team_uuid=?", (team_uuid,)
                )
                observations = await tx.fetchall(
                    "SELECT observation_key,state,current_attempt_generation FROM mkb_intake_observations "
                    "WHERE team_uuid=?",
                    (team_uuid,),
                )
                attempts = await tx.fetchall(
                    "SELECT attempt_generation,state FROM mkb_observation_attempts WHERE team_uuid=? "
                    "ORDER BY attempt_generation",
                    (team_uuid,),
                )
                snapshots = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_intake_snapshots WHERE team_uuid=?", (team_uuid,)
                )
            return {"sources": sources["count"], "observations": observations, "attempts": attempts, "snapshots": snapshots["count"]}

        observed = client.portal.call(inspect)
        assert observed["sources"] == 1
        assert observed["observations"] == [
            {"observation_key": "failed-observation-key", "state": "failed", "current_attempt_generation": 2}
        ]
        assert [row["attempt_generation"] for row in observed["attempts"]] == [1, 2]
        assert all(row["state"] == "failed" for row in observed["attempts"])
        assert observed["snapshots"] == 0
