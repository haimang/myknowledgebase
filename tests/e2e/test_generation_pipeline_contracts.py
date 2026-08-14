"""S06--S08 durable handoff and multi-unit vectorization coverage."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def _object_bytes(root: Path, team_uuid: str, handle: str) -> bytes:
    """Read the local S13 CAS object strictly through its logical digest form."""

    digest = handle.rsplit(":", maxsplit=1)[-1]
    return (root / "objects" / team_uuid / "sha256" / digest[:2] / digest[2:4] / digest).read_bytes()


def test_generation_members_are_independent_and_vectorize_every_channel(tmp_path: Path) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    token = "generation-contract-token"
    object_root = tmp_path / "objects"
    app = create_app(
        Settings(
            internal_token=token,
            database_path=tmp_path / "mkb.sqlite3",
            object_root=object_root,
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
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "generation-contracts"},
        ).status_code == 201
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
                        "external_key": "generation-contracts",
                        # Sentence boundaries force a real g2 multi-unit set.
                        "content": "First evidence sentence. Second evidence sentence! Third evidence sentence?",
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
                    "source": "e2e",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        deadline = time.monotonic() + 5
        while time.monotonic() < deadline:
            task = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
            assert task.status_code == 200, task.text
            if task.json()["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.02)
        assert task.json()["status"] == "succeeded", task.text

    database_uri = f"file:{tmp_path / 'mkb.sqlite3'}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        artifacts = [
            dict(row)
            for row in connection.execute(
                "SELECT generation_artifact_uuid,artifact_type,logical_handle,content_digest,size_bytes,"
                "validation_report_ref,validation_report_digest,validation_disposition "
                "FROM mkb_generation_artifacts WHERE team_uuid=? AND task_uuid=? ORDER BY artifact_type",
                (team_uuid, task_uuid),
            )
        ]
        pointers = [
            dict(row)
            for row in connection.execute(
                "SELECT artifact_type,current_generation_artifact_uuid FROM mkb_generation_pointers "
                "WHERE team_uuid=? ORDER BY artifact_type",
                (team_uuid,),
            )
        ]
        vectors = [
            dict(row)
            for row in connection.execute(
                "SELECT vector_record_uuid,generation_artifact_uuid,block_or_unit_id,channel,content_digest,source_handle,"
                "publication_state FROM mkb_vector_records WHERE team_uuid=? ORDER BY block_or_unit_id,channel",
                (team_uuid,),
            )
        ]
        outbox = connection.execute(
            "SELECT payload_json,payload_digest FROM mkb_outbox WHERE team_uuid=? AND kind='vectorize_construct'",
            (team_uuid,),
        ).fetchone()

    by_type = {artifact["artifact_type"]: artifact for artifact in artifacts}
    expected_types = {
        "structure_document",
        "retrieval_block_projection",
        "structure_validation_report",
        "construction_document",
        "dual_channel_projection",
        "construction_validation_report",
    }
    assert set(by_type) == expected_types
    assert len({artifact["logical_handle"] for artifact in artifacts}) == len(expected_types)
    assert all(artifact["validation_disposition"] == "full_valid" for artifact in artifacts)
    assert all(
        artifact["validation_report_ref"] == by_type[
            "structure_validation_report"
            if artifact["artifact_type"].startswith("structure") or artifact["artifact_type"] == "retrieval_block_projection"
            else "construction_validation_report"
        ]["logical_handle"]
        for artifact in artifacts
    )
    assert {pointer["artifact_type"] for pointer in pointers} == expected_types
    assert {
        pointer["artifact_type"]: pointer["current_generation_artifact_uuid"] for pointer in pointers
    } == {artifact_type: artifact["generation_artifact_uuid"] for artifact_type, artifact in by_type.items()}

    structure_document = json.loads(_object_bytes(object_root, team_uuid, by_type["structure_document"]["logical_handle"]))
    projection = json.loads(_object_bytes(object_root, team_uuid, by_type["retrieval_block_projection"]["logical_handle"]))
    construction = json.loads(_object_bytes(object_root, team_uuid, by_type["construction_document"]["logical_handle"]))
    dual = json.loads(_object_bytes(object_root, team_uuid, by_type["dual_channel_projection"]["logical_handle"]))
    assert projection["structure_generation_artifact_uuid"] == by_type["structure_document"]["generation_artifact_uuid"]
    assert projection["structure_document_digest"]
    assert construction["structure_generation_artifact_uuid"] == by_type["structure_document"]["generation_artifact_uuid"]
    assert construction["projection_generation_artifact_uuid"] == by_type["retrieval_block_projection"]["generation_artifact_uuid"]
    assert dual["generation_artifact_uuid"] == by_type["dual_channel_projection"]["generation_artifact_uuid"]
    assert structure_document["generation_artifact_uuid"] == by_type["structure_document"]["generation_artifact_uuid"]
    assert {block["granularity"] for block in projection["blocks"]} == {0, 1, 2}
    assert {unit["granularity"] for unit in dual["units"]} == {0, 1, 2}

    expected_coordinates = {(unit["unit_id"], channel) for unit in dual["units"] for channel in ("original", "summary")}
    assert {(vector["block_or_unit_id"], vector["channel"]) for vector in vectors} == expected_coordinates
    assert len({vector["vector_record_uuid"] for vector in vectors}) == len(vectors)
    assert all(vector["generation_artifact_uuid"] == by_type["dual_channel_projection"]["generation_artifact_uuid"] for vector in vectors)
    assert all(vector["source_handle"] == by_type["dual_channel_projection"]["logical_handle"] for vector in vectors)
    assert all(vector["publication_state"] == "indexed" for vector in vectors)

    assert outbox is not None
    vectorize_intent = json.loads(outbox["payload_json"])
    assert vectorize_intent["construction_artifact_uuid"] == by_type["construction_document"]["generation_artifact_uuid"]
    assert vectorize_intent["dual_channel_artifact_uuid"] == by_type["dual_channel_projection"]["generation_artifact_uuid"]
    assert vectorize_intent["content_full_recipe_version"] == "content_full.v1"
