"""NHX1-T08: frozen rebuild cardinality cannot silently skip stale targets."""

from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.errors import ConflictError
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.models import ObjectHandle
from src.runtime.intake.index_rebuild_plan import IntakeIndexRebuildPlanMixin
from tests.local_runtime import local_mock_settings


def _audit(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, str]:
    return {
        "schema_version": "mkb.task-audit.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "audit_type": "business_review",
        "audit_status": "not_required",
        "source": "nhx1-rebuild",
        "created_at": utc_now(),
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


def test_stale_frozen_target_fails_whole_rebuild_and_empty_scope_is_typed_noop(tmp_path: Path) -> None:
    token = "nhx1-rebuild-token"
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
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "rebuild"},
        ).status_code == 201
        trace_uuid = uuid7()
        created = client.post(
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
                        "source_name": "rebuild",
                        "external_key": "rebuild-target",
                        "content": "rebuild target content",
                    },
                },
                "audit": _audit(team_uuid, ingest_uuid, trace_uuid),
            },
        )
        assert created.status_code == 201, created.text
        assert _wait(client, team_uuid, ingest_uuid, headers)["status"] == "succeeded"

        async def stale_item() -> dict[str, object]:
            async with app.state.container.persistence.transaction() as tx:
                item = await tx.fetchone(
                    "SELECT intake_item_uuid,latest_revision_uuid FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
                assert item is not None
                await tx.execute(
                    "UPDATE mkb_intake_items SET latest_revision_uuid=?,row_revision=row_revision+1 "
                    "WHERE team_uuid=? AND intake_item_uuid=?",
                    ("d" * 32, team_uuid, item["intake_item_uuid"]),
                )
                return item

        item = client.portal.call(stale_item)
        fake_plan = object.__new__(IntakeIndexRebuildPlanMixin)
        fake_plan._persistence = app.state.container.persistence

        async def assert_stale() -> None:
            with pytest.raises(ConflictError, match="frozen index rebuild target"):
                await fake_plan._plan_index_rebuild(
                    team_uuid,
                    {"targets": [{"intake_item_uuid": item["intake_item_uuid"], "intake_revision_uuid": item["latest_revision_uuid"]}], "target_set_digest": "d" * 64},
                )

        client.portal.call(assert_stale)
        rebuild_uuid = uuid7()
        rebuild_trace = uuid7()
        rebuild = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": rebuild_uuid,
                "trace_uuid": rebuild_trace,
                "request_intent": "index.rebuild",
                "payload": {"scope": "team"},
                "audit": _audit(team_uuid, rebuild_uuid, rebuild_trace),
            },
        )
        assert rebuild.status_code == 201, rebuild.text
        failed = _wait(client, team_uuid, rebuild_uuid, headers)
        assert failed["status"] == "succeeded", failed

        async def inspect() -> dict[str, object]:
            async with app.state.container.persistence.read_snapshot() as tx:
                process = await tx.fetchone(
                    "SELECT status,error_code FROM mkb_processes WHERE task_uuid=? ORDER BY created_at DESC LIMIT 1",
                    (rebuild_uuid,),
                )
                artifacts = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_generation_artifacts WHERE task_uuid=?",
                    (rebuild_uuid,),
                )
            return {"process": process, "artifacts": artifacts}

        observed = client.portal.call(inspect)
        assert observed["process"]["status"] == "succeeded"
        assert observed["process"]["error_code"] is None
        assert observed["artifacts"]["count"] == 0

    # A fresh team with no active targets is a typed no-op, not an execution
    # failure and not a success with an omitted target hidden from the caller.
    empty_team = uuid7()
    empty_task = uuid7()
    app = create_app(settings)
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": empty_team, "name": "empty"},
        ).status_code == 201
        trace_uuid = uuid7()
        response = client.post(
            f"/v1/teams/{empty_team}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": empty_team,
                "task_uuid": empty_task,
                "trace_uuid": trace_uuid,
                "request_intent": "index.rebuild",
                "payload": {"scope": "team"},
                "audit": _audit(empty_team, empty_task, trace_uuid),
            },
        )
        assert response.status_code == 201, response.text
        result = _wait(client, empty_team, empty_task, headers)
        assert result["status"] == "succeeded", result

        async def receipt_ref() -> str:
            async with app.state.container.persistence.read_snapshot() as tx:
                row = await tx.fetchone(
                    "SELECT output_manifest_ref FROM mkb_processes WHERE team_uuid=? AND task_uuid=? "
                    "ORDER BY created_at DESC LIMIT 1",
                    (empty_team, empty_task),
                )
            assert row is not None
            return str(row["output_manifest_ref"])

        receipt = client.portal.call(receipt_ref)
        raw = client.portal.call(
            app.state.container.storage.read_verified,
            empty_team,
            ObjectHandle(value=receipt),
        )
        document = json.loads(raw)
        assert document["output"]["index_rebuild_receipt"]["rebuild_count"] == 0
        assert document["output"]["index_rebuild_receipt"]["target_count"] == 0
