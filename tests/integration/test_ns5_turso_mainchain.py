"""NS5-T60: generation main-chain inspected through the Turso port, not sqlite3."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def test_generation_mainchain_is_inspected_via_turso_port(tmp_path: Path) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    token = "ns5-t60-token"
    app = create_app(
        Settings(
            internal_token=token,
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            inference_probe_enabled=False,
            live_inference=False,
            persistence_backend="turso",
            concurrent_writes_required=False,
            native_vector_required=False,
            rate_limit_ip_per_min=1_000,
            rate_limit_token_per_min=2_000,
        )
    )
    headers = {"Authorization": f"Bearer {token}"}
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "ns5-t60"},
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
                        "external_key": "ns5-t60",
                        "content": "First evidence sentence. Second evidence sentence.",
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
                    "source": "ns5-t60",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        deadline = time.monotonic() + 8
        while time.monotonic() < deadline:
            task = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
            assert task.status_code == 200, task.text
            if task.json()["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.05)
        assert task.json()["status"] == "succeeded", task.text

        persistence = app.state.container.persistence

        async def inspect() -> tuple[list[dict[str, object]], int]:
            async with persistence.transaction() as tx:
                artifacts = await tx.fetchall(
                    "SELECT artifact_type,validation_disposition FROM mkb_generation_artifacts WHERE team_uuid=?",
                    (team_uuid,),
                )
                items = await tx.fetchall(
                    "SELECT intake_item_uuid FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
                return list(artifacts), len(items)

        artifacts, item_count = client.portal.call(inspect)
        assert item_count == 1
        types = {row["artifact_type"] for row in artifacts}
        assert "dual_channel_projection" in types
        assert all(
            row["validation_disposition"] == "full_valid"
            for row in artifacts
            if row["artifact_type"] == "dual_channel_projection"
        )

        async def inspect_vectors() -> int:
            async with persistence.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT vector_record_uuid FROM mkb_vector_records WHERE team_uuid=?",
                    (team_uuid,),
                )
                return len(rows)

        vector_count = client.portal.call(inspect_vectors)
        assert vector_count >= 1
