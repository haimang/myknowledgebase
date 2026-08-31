"""NHX1-T20: cleanup jobs expose per-substrate proofs and typed hold blocking."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.services.cleanup_jobs import CleanupJobService
from tests.local_runtime import local_mock_settings


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


def test_cleanup_converges_after_hold_is_released(tmp_path: Path) -> None:
    token = "nhx1-cleanup-token"
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
    team_uuid, ingest_uuid = uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "cleanup"},
        ).status_code == 201
        trace_uuid = uuid7()
        ingest = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": ingest_uuid,
                "trace_uuid": trace_uuid,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "cleanup",
                        "external_key": "cleanup-source",
                        "content": "cleanup convergence test body",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": ingest_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nhx1",
                    "created_at": utc_now(),
                },
            },
        )
        assert ingest.status_code == 201, ingest.text
        assert _wait(client, team_uuid, ingest_uuid, headers)["status"] == "succeeded"

        async def item_data() -> dict[str, object]:
            async with app.state.container.persistence.read_snapshot() as tx:
                item = await tx.fetchone("SELECT * FROM mkb_intake_items WHERE team_uuid=?", (team_uuid,))
                assert item is not None
                object_row = await tx.fetchone(
                    "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? LIMIT 1", (team_uuid,)
                )
            return {"item": item, "object_uuid": None if object_row is None else object_row["stored_object_uuid"]}

        data = client.portal.call(item_data)
        item = data["item"]
        delete_uuid, delete_trace = uuid7(), uuid7()
        delete = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": delete_uuid,
                "trace_uuid": delete_trace,
                "request_intent": "intake.delete",
                "payload": {"intake_item_uuid": item["intake_item_uuid"]},
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": delete_uuid,
                    "trace_uuid": delete_trace,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nhx1",
                    "created_at": utc_now(),
                },
            },
        )
        assert delete.status_code == 201, delete.text
        assert _wait(client, team_uuid, delete_uuid, headers)["status"] == "succeeded"

        async def cleanup_setup() -> tuple[str, str | None]:
            async with app.state.container.persistence.transaction() as tx:
                intent = await tx.fetchone(
                    "SELECT intent_uuid,required_substrate_set_digest FROM mkb_intake_cleanup_intents "
                    "WHERE team_uuid=? ORDER BY requested_at DESC LIMIT 1",
                    (team_uuid,),
                )
                assert intent is not None
                hold_uuid = None
                if data["object_uuid"] is not None:
                    hold_uuid = uuid7()
                    await tx.execute(
                        "INSERT INTO mkb_object_references(reference_uuid,team_uuid,stored_object_uuid,purpose,"
                        "owner_kind,owner_uuid,expected_digest,expected_size,created_at) "
                        "SELECT ?,team_uuid,stored_object_uuid,'operator_hold','cleanup_hold',?,?,size_bytes,? "
                        "FROM mkb_stored_objects WHERE stored_object_uuid=?",
                        (hold_uuid, item["intake_item_uuid"], "b" * 64, utc_now(), data["object_uuid"]),
                    )
            return intent["intent_uuid"], hold_uuid

        intent_uuid, hold_uuid = client.portal.call(cleanup_setup)
        service = CleanupJobService(app.state.container.persistence)

        async def ensure() -> str:
            return await service.ensure_for_item(
                team_uuid=team_uuid,
                intake_item_uuid=item["intake_item_uuid"],
                intent_uuid=intent_uuid,
                item_epoch=int(item["row_revision"]),
                required_substrate_set_digest="a" * 64,
                retention_until="2020-01-01T00:00:00Z",
            )

        cleanup_uuid = client.portal.call(ensure)
        first = client.portal.call(service.run_once)
        assert first[0].state == "blocked"
        assert any(step.blocked_reason == "cleanup_hold_active" for step in first[0].steps)
        if hold_uuid is not None:
            async def release_hold() -> None:
                async with app.state.container.persistence.transaction() as tx:
                    await tx.execute("UPDATE mkb_object_references SET released_at=? WHERE reference_uuid=?", (utc_now(), hold_uuid))

            client.portal.call(release_hold)
        second = client.portal.call(service.run_once)
        assert second[0].cleanup_job_uuid == cleanup_uuid
        assert second[0].state == "completed"
        assert {step.substrate_kind for step in second[0].steps} == {
            "intake_artifact",
            "derived_generation",
            "vector_projection",
            "object_reference",
            "object_gc",
        }
        assert all(step.state == "completed" and step.proof_uuid for step in second[0].steps)
