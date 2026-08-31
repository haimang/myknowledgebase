"""NHX1-T05: one Snapshot per Observation and one ItemEpoch owner."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.local_runtime import local_mock_settings


def _payload(team_uuid: str, task_uuid: str, observation_key: str, content: str) -> dict[str, object]:
    trace_uuid = uuid7()
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
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "nhx1-epoch",
                "external_key": "epoch-source",
                "observation_key": observation_key,
                "content": content,
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


def test_changed_and_no_change_observations_have_snapshot_facts_and_epoch_fence(tmp_path: Path) -> None:
    team_uuid = uuid7()
    token = "nhx1-epoch-token"
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            internal_token=token,
            inference_probe_enabled=False,
            live_inference=False,
        )
    )
    first_uuid, second_uuid, third_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "epoch"},
        ).status_code == 201
        first = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_payload(team_uuid, first_uuid, "epoch-a", "first bytes"),
        )
        assert first.status_code == 201, first.text
        assert _wait(client, team_uuid, first_uuid, headers)["status"] == "succeeded"
        second = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_payload(team_uuid, second_uuid, "epoch-b", "first bytes"),
        )
        assert second.status_code == 201, second.text
        assert _wait(client, team_uuid, second_uuid, headers)["status"] == "succeeded"

        async def inspect() -> dict[str, object]:
            async with app.state.container.persistence.read_snapshot() as tx:
                facts = await tx.fetchall(
                    "SELECT observation_uuid,disposition,expected_item_epoch,resulting_item_epoch "
                    "FROM mkb_intake_acceptance_facts WHERE team_uuid=? ORDER BY created_at",
                    (team_uuid,),
                )
                snapshots = await tx.fetchall(
                    "SELECT intake_snapshot_uuid,observation_key FROM mkb_intake_snapshots WHERE team_uuid=? "
                    "ORDER BY accepted_at",
                    (team_uuid,),
                )
                item = await tx.fetchone(
                    "SELECT intake_item_uuid,latest_revision_uuid,row_revision,lifecycle_state "
                    "FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
            return {"facts": facts, "snapshots": snapshots, "item": item}

        observed = client.portal.call(inspect)
        assert [row["disposition"] for row in observed["facts"]] == ["changed", "no_change"]
        assert observed["facts"][0]["resulting_item_epoch"] == observed["facts"][0]["expected_item_epoch"] + 1
        assert observed["facts"][1]["resulting_item_epoch"] == observed["facts"][1]["expected_item_epoch"]
        assert [row["observation_key"] for row in observed["snapshots"]] == ["epoch-a", "epoch-b"]
        assert observed["item"]["latest_revision_uuid"] is not None

        # A stale callback carrying the pre-delete epoch cannot mutate the Item.
        item_uuid = observed["item"]["intake_item_uuid"]
        old_epoch = int(observed["item"]["row_revision"])
        delete_trace_uuid = uuid7()
        deleted = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": third_uuid,
                "trace_uuid": delete_trace_uuid,
                "request_intent": "intake.delete",
                "payload": {"intake_item_uuid": item_uuid},
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": third_uuid,
                    "trace_uuid": delete_trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nhx1",
                    "created_at": utc_now(),
                },
            },
        )
        # The request is admitted with a frozen epoch; only its eventual worker
        # result decides the lifecycle.  The direct CAS below is the late-callback
        # probe and must affect zero rows after delete has advanced the epoch.
        assert deleted.status_code == 201, deleted.text
        _wait(client, team_uuid, third_uuid, headers)

        rejected = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_payload(team_uuid, uuid7(), "epoch-after-delete", "new bytes"),
        )
        assert rejected.status_code == 409, rejected.text
        assert rejected.json()["error"]["code"] == "INTAKE_ITEM_DELETED"

        async def stale_callback() -> int:
            async with app.state.container.persistence.transaction() as tx:
                changed = await tx.execute(
                    "UPDATE mkb_intake_items SET latest_revision_uuid=?,row_revision=row_revision+1 "
                    "WHERE team_uuid=? AND intake_item_uuid=? AND row_revision=? AND lifecycle_state='active'",
                    (observed["item"]["latest_revision_uuid"], team_uuid, item_uuid, old_epoch),
                )
                return int(changed.rowcount)

        assert client.portal.call(stale_callback) == 0
