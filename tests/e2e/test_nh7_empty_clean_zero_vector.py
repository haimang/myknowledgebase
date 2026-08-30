"""NH7-T10: empty admitted-clean cannot index or retrieve."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.e2e.test_source_capability_paths import _settings


def test_empty_inline_whitespace_zero_vector(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    headers = {"Authorization": "Bearer source-capability-token"}
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-empty"},
            ).status_code
            == 201
        )
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
                        "external_key": "nh7-empty",
                        "content": "   \n\t  ",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-empty-source",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t10",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        deadline = time.monotonic() + 30
        latest: dict[str, object] = {}
        while time.monotonic() < deadline:
            response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
            latest = response.json()
            if latest["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.02)
        assert latest["status"] == "failed", latest

        async def vector_count() -> int:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=?",
                    (team_uuid,),
                )
            return int(row["n"]) if row is not None else -1

        assert client.portal.call(vector_count) == 0
