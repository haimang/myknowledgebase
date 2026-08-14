"""S05 regression: inline bytes never persist in Task-facing documents."""

from __future__ import annotations

import asyncio
import hashlib
import json
import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.models import ObjectHandle
from src.runtime.config import Settings
from src.storage.local_store import LocalObjectStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="inline-ingress-token",
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


def test_inline_ingress_is_staged_before_task_audit_and_execution_manifest(tmp_path: Path) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    token = "inline-ingress-token"
    # Deliberately include both CRLF and decomposed Unicode.  The staged bytes
    # have a deterministic UTF-8/NFC/LF identity while neither raw form may
    # appear in durable Task-facing JSON.
    raw_content = "S05-INLINE-SENTINEL:\r\nCafe\u0301"
    canonical_content = "S05-INLINE-SENTINEL:\nCafé"
    payload = {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {
            "json_prompt_id": "promptB.json.generic",
            "source": {
                "source_kind": "inline_payload",
                "external_key": "staged-inline-document",
                "content": raw_content,
                "media_type": "text/plain",
            }
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "s05-e2e",
            "created_at": utc_now(),
        },
    }
    headers = {"Authorization": f"Bearer {token}"}
    app = create_app(_settings(tmp_path))

    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "inline-ingress"},
            ).status_code
            == 201
        )
        created = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=payload)
        assert created.status_code == 201, created.text
        # Exact replay must retain the normal idempotency result and avoid a
        # second Task UoW/object-reference sequence.
        replay = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=payload)
        assert replay.status_code == 200, replay.text

        deadline = time.monotonic() + 5
        task: dict[str, object] = {}
        while time.monotonic() < deadline:
            response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
            assert response.status_code == 200, response.text
            task = response.json()
            if task["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.02)
        assert task["status"] == "succeeded", task

    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        audit = connection.execute(
            "SELECT strict_payload_json FROM mkb_task_audits WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        ).fetchone()
        root = connection.execute(
            "SELECT execution_uuid,manifest_ref FROM mkb_executions "
            "WHERE team_uuid=? AND task_uuid=? AND execution_role='root'",
            (team_uuid, task_uuid),
        ).fetchone()
        ingress_refs = connection.execute(
            "SELECT COUNT(*) AS count FROM mkb_object_references "
            "WHERE team_uuid=? AND owner_kind='execution_inline_ingress'",
            (team_uuid,),
        ).fetchone()

    assert audit is not None and root is not None and ingress_refs is not None
    audit_json = audit["strict_payload_json"]
    assert raw_content not in audit_json
    assert canonical_content not in audit_json
    assert ingress_refs["count"] == 1

    manifest_bytes = asyncio.run(
        LocalObjectStore(tmp_path / "objects").read_verified(team_uuid, ObjectHandle(value=root["manifest_ref"]))
    )
    manifest_text = manifest_bytes.decode("utf-8")
    assert raw_content not in manifest_text
    assert canonical_content not in manifest_text
    source = json.loads(manifest_bytes)["payload"]["source"]
    assert "content" not in source
    assert source["size_bytes"] == len(canonical_content.encode("utf-8"))
    assert source["content_digest"] == hashlib.sha256(canonical_content.encode("utf-8")).hexdigest()
    staged = asyncio.run(
        LocalObjectStore(tmp_path / "objects").read_verified(team_uuid, ObjectHandle(value=source["logical_handle"]))
    )
    assert staged == canonical_content.encode("utf-8")
