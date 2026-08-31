"""NHX1-T13: full Task retry replays frozen bytes without re-fetching."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.local_runtime import local_mock_settings


class _CountingHttpFetcher:
    def __init__(self) -> None:
        self.calls: list[str] = []
        self.body = "<article><h1>Frozen title</h1><p>frozen upstream bytes</p></article>"

    async def acquire(self, url: str) -> str:
        self.calls.append(url)
        return self.body


def _task(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, object]:
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {
            "json_prompt_id": "promptB.json.generic",
            "source": {
                "source_kind": "http_resource",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "exact-replay",
                "external_key": "exact-replay-source",
                "observation_key": "exact-replay-observation",
                "url": "https://example.com/frozen",
                "acquisition_mode": "static",
            },
        },
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
    deadline = time.monotonic() + 40
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    raise AssertionError(latest)


def test_http_full_retry_uses_frozen_artifact_and_zero_refetch(tmp_path: Path) -> None:
    token = "nhx1-exact-replay-token"
    headers = {"Authorization": f"Bearer {token}"}
    settings = local_mock_settings(
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        internal_token=token,
        inference_probe_enabled=False,
        live_inference=False,
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=20_000,
    )
    app = create_app(settings)
    fetcher = _CountingHttpFetcher()
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        app.state.container.workflow_worker.handler._http_fetcher = fetcher
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "exact"},
        ).status_code == 201
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task(team_uuid, task_uuid, trace_uuid),
        )
        assert created.status_code == 201, created.text
        assert _wait(client, team_uuid, task_uuid, headers)["status"] == "succeeded"
        assert len(fetcher.calls) == 1

        async def fail_original() -> int:
            async with app.state.container.persistence.transaction() as tx:
                task = await tx.fetchone(
                    "SELECT row_revision,current_root_execution_uuid FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                    (team_uuid, task_uuid),
                )
                assert task is not None
                await tx.execute(
                    "UPDATE mkb_executions SET status='failed',final_error_code='TEST_RETRY',completed_at=?,updated_at=? "
                    "WHERE execution_uuid=?",
                    (utc_now(), utc_now(), task["current_root_execution_uuid"]),
                )
                await tx.execute(
                    "UPDATE mkb_tasks SET status='failed',error_code='TEST_RETRY',completed_at=?,updated_at=?,"
                    "row_revision=row_revision+1 WHERE team_uuid=? AND task_uuid=?",
                    (utc_now(), utc_now(), team_uuid, task_uuid),
                )
                return int(task["row_revision"]) + 1

        expected_revision = client.portal.call(fail_original)
        fetcher.body = "<article><h1>Changed title</h1><p>changed upstream bytes must not be observed</p></article>"
        retry = client.post(
            f"/v1/teams/{team_uuid}/tasks/{task_uuid}:retry",
            headers=headers,
            json={"expected_revision": expected_revision, "reason": "exact replay"},
        )
        assert retry.status_code == 202, retry.text
        final = _wait(client, team_uuid, task_uuid, headers)
        assert final["status"] == "succeeded", final
        assert len(fetcher.calls) == 1

        async def inspect() -> dict[str, object]:
            async with app.state.container.persistence.read_snapshot() as tx:
                roots = await tx.fetchall(
                    "SELECT generation,payload_extra,observation_uuid,workflow_revision_uuid,actual_binding_state "
                    "FROM mkb_executions WHERE team_uuid=? AND task_uuid=? ORDER BY generation",
                    (team_uuid, task_uuid),
                )
                snapshots = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_intake_snapshots WHERE team_uuid=?", (team_uuid,)
                )
            return {"roots": roots, "snapshots": snapshots["count"]}

        observed = client.portal.call(inspect)
        assert observed["roots"][0]["observation_uuid"] == observed["roots"][1]["observation_uuid"]
        assert json.loads(observed["roots"][1]["payload_extra"])["full_retry"] is True
        assert observed["snapshots"] == 1


def test_no_frozen_input_is_rejected_for_production_retry(tmp_path: Path) -> None:
    """A failed acquire has no accepted artifact and cannot be called exact replay."""

    token = "nhx1-no-frozen-token"
    headers = {"Authorization": f"Bearer {token}"}
    settings = local_mock_settings(
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        internal_token=token,
        inference_probe_enabled=False,
        live_inference=False,
        egress_allow_private_default=False,
        egress_allow_http=True,
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=20_000,
    )
    app = create_app(settings)
    task_uuid, trace_uuid, team_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "no-frozen"},
        ).status_code == 201
        body = _task(team_uuid, task_uuid, trace_uuid)
        source = body["payload"]["source"]
        source["url"] = "http://127.0.0.1:9/no-frozen"
        created = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=body)
        assert created.status_code == 201, created.text
        assert _wait(client, team_uuid, task_uuid, headers)["status"] == "failed"
        task = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers).json()
        retry = client.post(
            f"/v1/teams/{team_uuid}/tasks/{task_uuid}:retry",
            headers=headers,
            json={"expected_revision": task["revision"], "reason": "must reject"},
        )
        assert retry.status_code == 409, retry.text
        assert retry.json()["error"]["code"] == "FULL_REPLAY_INPUT_UNAVAILABLE"
