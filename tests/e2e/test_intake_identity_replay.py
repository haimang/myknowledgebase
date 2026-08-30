"""NS9-FX2 / NH9-T02: intake identity replay must not dangle the item revision pointer."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.local_runtime import local_mock_settings


def _ingest(
    client: TestClient, headers: dict[str, str], team_uuid: str, task_uuid: str, content: str
) -> dict[str, object]:
    trace_uuid = uuid7()
    created = client.post(
        f"/v1/teams/{team_uuid}/tasks",
        headers=headers,
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
                    "external_key": "intake-identity-replay-golden",
                    "content": content,
                    "media_type": "text/plain",
                },
            },
            "audit": {
                "schema_version": "mkb.task-audit.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit_type": "business_review",
                "audit_status": "not_required",
                "source": "e2e",
                "created_at": utc_now(),
            },
        },
    )
    assert created.status_code == 201, created.text
    deadline = time.monotonic() + 30
    task: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.05)
    raise AssertionError(f"task did not reach a terminal status in time: {task}")


def test_identity_replay_reuses_revision_and_keeps_pointer_resolved(tmp_path: Path) -> None:
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer integration-token"}
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            internal_token="integration-token",
            inference_probe_enabled=False,
            live_inference=False,
            rate_limit_ip_per_min=1_000,
            rate_limit_token_per_min=2_000,
        )
    )
    content = "intake identity replay golden document body"

    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "identity-replay"},
            ).status_code
            == 201
        )

        first = _ingest(client, headers, team_uuid, uuid7(), content)
        assert first["status"] == "succeeded", first

        second = _ingest(client, headers, team_uuid, uuid7(), content)
        assert second["status"] == "succeeded", second

        async def inspect() -> tuple[str, int, int, int]:
            async with app.state.container.persistence.transaction() as tx:
                item = await tx.fetchone(
                    "SELECT intake_item_uuid,latest_revision_uuid FROM mkb_intake_items "
                    "WHERE team_uuid=? AND normalized_external_key=?",
                    (team_uuid, "intake-identity-replay-golden"),
                )
                assert item is not None
                dangling = await tx.fetchone(
                    "SELECT COUNT(*) AS n FROM mkb_intake_revisions "
                    "WHERE team_uuid=? AND intake_revision_uuid=?",
                    (team_uuid, item["latest_revision_uuid"]),
                )
                revision_count = await tx.fetchone(
                    "SELECT COUNT(*) AS n FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
                    (team_uuid, item["intake_item_uuid"]),
                )
                orphans = await tx.fetchone(
                    "SELECT COUNT(*) AS n FROM mkb_generation_artifacts WHERE team_uuid=? "
                    "AND intake_revision_uuid IS NOT NULL AND intake_revision_uuid NOT IN "
                    "(SELECT intake_revision_uuid FROM mkb_intake_revisions WHERE team_uuid=?)",
                    (team_uuid, team_uuid),
                )
            assert dangling is not None and revision_count is not None and orphans is not None
            return str(item["latest_revision_uuid"]), int(dangling["n"]), int(revision_count["n"]), int(orphans["n"])

        latest, dangling, revision_count, orphans = client.portal.call(inspect)
        assert latest
        assert dangling == 1, "latest_revision_uuid must point at an existing revision row after replay"
        assert revision_count == 1, "identical content must replay one revision, not mint new ones"
        assert orphans == 0


def test_identity_replay_queries_via_persistence_port(tmp_path: Path) -> None:
    test_identity_replay_reuses_revision_and_keeps_pointer_resolved(tmp_path)
