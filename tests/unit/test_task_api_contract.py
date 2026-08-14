"""HTTP-level S02 contract tests for Task schema and error correlation."""

from __future__ import annotations

import uuid
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def _client(tmp_path: Path) -> TestClient:
    app = create_app(
        Settings(
            internal_token="task-contract-token",
            database_path=tmp_path / "mkb.sqlite3",
            persistence_backend="sqlite",
            concurrent_writes_required=False,
            native_vector_required=False,
            object_root=tmp_path / "objects",
            inference_probe_enabled=False,
            rate_limit_ip_per_min=1_000,
            rate_limit_token_per_min=1_000,
        )
    )
    return TestClient(app, raise_server_exceptions=True)


def _body(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, object]:
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
                "external_key": "contract-test",
                "content": "safe body",
            }
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "test",
            "created_at": utc_now(),
        },
    }


def test_task_schema_error_keeps_valid_root_trace_without_echoing_body(tmp_path: Path) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    body = _body(team_uuid, task_uuid, trace_uuid)
    body["unexpected_control"] = "must-not-echo"
    with _client(tmp_path) as client:
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers={"Authorization": "Bearer task-contract-token", "X-Request-Id": "contract-request"},
            json=body,
        )
    assert response.status_code == 422
    envelope = response.json()
    assert envelope["error"]["code"] == "task-schema-invalid"
    assert envelope["trace_uuid"] == trace_uuid
    assert envelope["request_id"] == "contract-request"
    assert "must-not-echo" not in response.text


def test_task_deadline_requires_future_utc_rfc3339(tmp_path: Path) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    body = _body(team_uuid, task_uuid, trace_uuid)
    body["deadline_at"] = "2020-01-01T00:00:00+08:00"
    with _client(tmp_path) as client:
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers={"Authorization": "Bearer task-contract-token"},
            json=body,
        )
    assert response.status_code == 422
    envelope = response.json()
    assert envelope["error"]["code"] == "task-schema-invalid"
    assert envelope["trace_uuid"] == trace_uuid

    task_uuid, trace_uuid = uuid7(), uuid7()
    body = _body(team_uuid, task_uuid, trace_uuid)
    body["audit"]["created_at"] = "not-a-time"  # type: ignore[index]
    with _client(tmp_path) as client:
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers={"Authorization": "Bearer task-contract-token"},
            json=body,
        )
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "task-schema-invalid"
    assert response.json()["trace_uuid"] == trace_uuid

    # A request without an admissible client root trace still receives a safe
    # server-side correlation UUID rather than a missing/echoed trace field.
    body.pop("trace_uuid")
    with _client(tmp_path) as client:
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers={"Authorization": "Bearer task-contract-token"},
            json=body,
        )
    assert response.status_code == 422
    parsed = uuid.UUID(response.json()["trace_uuid"])
    assert parsed.version == 7
