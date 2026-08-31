"""NHX1-T23: safe discovery and typed public projections require no SQL."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from tests.local_runtime import local_mock_settings


def test_public_catalog_and_cold_start_lists_are_strict(tmp_path: Path) -> None:
    token = "nhx1-public-contract-token"
    team_uuid = uuid7()
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "public.sqlite3",
            object_root=tmp_path / "objects",
            internal_token=token,
            rate_limit_ip_per_min=10_000,
            rate_limit_token_per_min=10_000,
        )
    )
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app, raise_server_exceptions=True) as client:
        created = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "catalog"},
        )
        assert created.status_code == 201, created.text
        catalog = client.get("/v1/catalog", headers=headers)
        assert catalog.status_code == 200, catalog.text
        payload = catalog.json()
        assert payload["schema_version"] == "mkb.catalog.v1"
        assert payload["deployment_role"] == "all"
        assert payload["workflows"]
        assert payload["capabilities"]
        assert {item["process_key"] for item in payload["capabilities"]} >= {"intake.acquire.inline"}
        assert {item["source_kind"] for item in payload["source_kinds"]} == {
            "inline_payload",
            "local_object",
            "http_resource",
            "registered_api",
        }

        items = client.get(f"/v1/teams/{team_uuid}/intake-items", headers=headers)
        namespaces = client.get(f"/v1/teams/{team_uuid}/namespaces", headers=headers)
        assert items.status_code == namespaces.status_code == 200
        assert items.json() == {"items": [], "next_cursor": None}
        assert namespaces.json() == {"items": [], "next_cursor": None}

        invalid_filter = client.get(
            f"/v1/teams/{team_uuid}/intake-items", headers=headers, params={"lifecycle_state": "unknown"}
        )
        assert invalid_filter.status_code == 422


def test_task_read_is_typed_and_workflow_selector_is_not_a_create_field(tmp_path: Path) -> None:
    token = "nhx1-task-contract-token"
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "task.sqlite3",
            object_root=tmp_path / "objects",
            internal_token=token,
            rate_limit_ip_per_min=10_000,
            rate_limit_token_per_min=10_000,
        )
    )
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app, raise_server_exceptions=True) as client:
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "task"},
        )
        assert team.status_code == 201, team.text
        body = {
            "schema_version": "mkb.task.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "request_intent": "intake.ingest",
            "workflow_key": "caller.selected.graph",
            "payload": {
                "json_prompt_id": "promptB.json.generic",
                "source": {
                    "source_kind": "inline_payload",
                    "realm": "documentation",
                    "type": "article",
                    "channel": "general",
                    "source_name": "selector",
                    "external_key": "selector",
                    "content": "selector test",
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
                "created_at": "2026-08-31T00:00:00Z",
            },
        }
        rejected = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=body)
        assert rejected.status_code == 422
        assert rejected.json()["error"]["code"] == "task-schema-invalid"
