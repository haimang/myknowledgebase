"""NHX1-T19: publication manifest membership is part of the retrieval fence."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.local_runtime import local_mock_settings


def test_publication_manifest_has_exact_members_and_is_immutable(tmp_path: Path) -> None:
    token = "nhx1-publication-token"
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
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "manifest"},
        ).status_code == 201
        response = client.post(
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
                        "source_name": "manifest",
                        "external_key": "manifest-source",
                        "content": "publication manifest content with enough words",
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
            },
        )
        assert response.status_code == 201, response.text
        deadline = time.monotonic() + 40
        while time.monotonic() < deadline:
            task = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers).json()
            if task["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.02)
        assert task["status"] == "succeeded", task

        async def inspect() -> tuple[dict[str, object], int]:
            async with app.state.container.persistence.read_snapshot() as tx:
                manifest = await tx.fetchone(
                    "SELECT publication_manifest_uuid,proof_uuid,record_count,record_set_digest,manifest_digest "
                    "FROM mkb_publication_manifests WHERE team_uuid=?",
                    (team_uuid,),
                )
                count = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_publication_manifest_members WHERE publication_manifest_uuid=?",
                    (manifest["publication_manifest_uuid"],),
                )
            assert manifest is not None and count is not None
            return manifest, int(count["count"])

        manifest, member_count = client.portal.call(inspect)
        assert manifest["record_count"] == member_count > 0
        assert len(manifest["record_set_digest"]) == 64
        assert len(manifest["manifest_digest"]) == 64

        async def attack() -> None:
            async with app.state.container.persistence.transaction() as tx:
                try:
                    await tx.execute(
                        "UPDATE mkb_publication_manifests SET manifest_digest=? WHERE publication_manifest_uuid=?",
                        ("0" * 64, manifest["publication_manifest_uuid"]),
                    )
                except Exception:
                    return
                raise AssertionError("immutable publication manifest accepted an identity UPDATE")

        client.portal.call(attack)
