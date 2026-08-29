"""NH4-T04: public upload and local_object ingest are separate product commits."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.e2e.test_nh4_public_upload import _settings, _team, _upload


def _task(team_uuid: str, *, source: dict[str, object]) -> dict[str, object]:
    task_uuid, trace_uuid = uuid7(), uuid7()
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {"json_prompt_id": "promptB.json.generic", "source": source},
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nh4-two-step",
            "created_at": utc_now(),
        },
    }


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict:
    deadline = time.monotonic() + 30
    latest: dict = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def _search(
    client: TestClient,
    team_uuid: str,
    namespace_key: str,
    headers: dict[str, str],
    query: str,
) -> dict:
    response = client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers=headers,
        json={
            "schema_version": "mkb.retrieval.v1",
            "team_uuid": team_uuid,
            "namespace_key": namespace_key,
            "query": query,
            "filters": {"channel": "summary"},
            "return_k": 10,
            "recall_k": 20,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_upload_search_empty_then_independent_ingest_namespace_hit(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer nh4-upload-token"}
    sentinel = "NH4 public upload independent ingest sentinel zephyrquartz"
    with TestClient(app, raise_server_exceptions=True) as client:
        _team(client, team_uuid, headers)

        seed = _task(
            team_uuid,
            source={
                "source_kind": "inline_payload",
                "external_key": "nh4-namespace-seed",
                "content": "namespace seed unrelated baseline",
                "media_type": "text/plain",
            },
        )
        created_seed = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=seed)
        assert created_seed.status_code == 201, created_seed.text
        assert _wait(client, team_uuid, str(seed["task_uuid"]), headers)["status"] == "succeeded"

        async def namespace_and_items() -> tuple[str, int]:
            async with app.state.container.persistence.transaction() as tx:
                namespace = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
                count = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
            assert namespace is not None and count is not None
            return str(namespace["namespace_key"]), int(count["count"])

        namespace_key, baseline_items = client.portal.call(namespace_and_items)
        uploaded_response = _upload(client, team_uuid, headers, sentinel.encode())
        assert uploaded_response.status_code == 201, uploaded_response.text
        uploaded = uploaded_response.json()

        before = _search(client, team_uuid, namespace_key, headers, "zephyrquartz")
        assert all("zephyrquartz" not in str(hit.get("payload_content", "")) for hit in before["results"])
        assert client.portal.call(namespace_and_items)[1] == baseline_items

        ingest = _task(
            team_uuid,
            source={
                "source_kind": "local_object",
                "external_key": "nh4-uploaded-local-object",
                "logical_handle": uploaded["handle"],
                "media_type": "text/plain",
            },
        )
        created = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=ingest)
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, str(ingest["task_uuid"]), headers)
        assert terminal["status"] == "succeeded", terminal

        after = _search(client, team_uuid, namespace_key, headers, "zephyrquartz")
        assert any("zephyrquartz" in str(hit.get("payload_content", "")) for hit in after["results"])

        async def handoff() -> tuple[dict, dict, int]:
            async with app.state.container.persistence.transaction() as tx:
                catalog = await tx.fetchone(
                    "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=? "
                    "AND tombstoned_at IS NULL",
                    (team_uuid, uploaded["digest"]),
                )
                assert catalog is not None
                pending = await tx.fetchone(
                    "SELECT released_at FROM mkb_object_references WHERE team_uuid=? AND stored_object_uuid=? "
                    "AND purpose='upload_pending'",
                    (team_uuid, catalog["stored_object_uuid"]),
                )
                business = await tx.fetchone(
                    "SELECT purpose,owner_kind,released_at FROM mkb_object_references WHERE team_uuid=? "
                    "AND stored_object_uuid=? AND purpose='intake_snapshot_artifact' "
                    "AND owner_kind='intake_snapshot_source_object'",
                    (team_uuid, catalog["stored_object_uuid"]),
                )
                items = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_intake_items WHERE team_uuid=?",
                    (team_uuid,),
                )
            assert pending is not None and business is not None and items is not None
            return pending, business, int(items["count"])

        pending, business, item_count = client.portal.call(handoff)
        assert pending["released_at"] is not None
        assert business == {
            "purpose": "intake_snapshot_artifact",
            "owner_kind": "intake_snapshot_source_object",
            "released_at": None,
        }
        assert item_count == baseline_items + 1
