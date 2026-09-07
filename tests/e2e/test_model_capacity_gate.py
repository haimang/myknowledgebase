"""Temporary model-capacity priority admission contract."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="capacity-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        persistence_backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
        inference_probe_enabled=False,
        live_inference=False,
        generation_local_enabled=False,
        model_capacity_priority_gate_enabled=True,
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=10_000,
    )


def _task(team_uuid: str, task_uuid: str, priority: str) -> dict[str, object]:
    trace_uuid = uuid7()
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "priority": priority,
        "payload": {
            "json_prompt_id": "promptB.json.generic",
            "source": {
                "source_kind": "inline_payload",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "capacity-test",
                "external_key": f"capacity-{task_uuid}",
                "content": "capacity policy source",
            },
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "capacity-test",
            "created_at": utc_now(),
        },
    }


def test_model_work_normal_and_low_return_capacity_429(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer capacity-token"}

    with TestClient(app) as client:
        created = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "capacity"},
        )
        assert created.status_code == 201, created.text
        for priority in ("normal", "low"):
            response = client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=headers,
                json=_task(team_uuid, uuid7(), priority),
            )
            assert response.status_code == 429, response.text
            assert response.json()["error"]["code"] == "MODEL_AT_CAPACITY"
            assert response.json()["error"]["message"] == "model at capacity"


def test_model_work_high_and_urgent_are_admitted(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer capacity-token"}

    with TestClient(app) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "capacity"},
            ).status_code
            == 201
        )
        for priority in ("high", "urgent"):
            response = client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=headers,
                json=_task(team_uuid, uuid7(), priority),
            )
            assert response.status_code == 201, response.text
