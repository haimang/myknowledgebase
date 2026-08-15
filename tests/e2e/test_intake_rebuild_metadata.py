"""Public lifecycle regressions for rebuild and metadata-only intake commands."""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="intake-lifecycle-token",
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


def _audit(team_uuid: str, task_uuid: str, trace_uuid: str) -> dict[str, str]:
    return {
        "schema_version": "mkb.task-audit.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "audit_type": "business_review",
        "audit_status": "not_required",
        "source": "intake-lifecycle-e2e",
        "created_at": utc_now(),
    }


def _task_body(
    *,
    team_uuid: str,
    task_uuid: str,
    trace_uuid: str,
    request_intent: str,
    payload: dict[str, Any],
) -> dict[str, Any]:
    if request_intent == "intake.ingest":
        payload = {"json_prompt_id": "promptB.json.generic", **payload}
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": request_intent,
        "payload": payload,
        "audit": _audit(team_uuid, task_uuid, trace_uuid),
    }


def _wait_for_terminal(
    client: TestClient, *, team_uuid: str, task_uuid: str, headers: dict[str, str]
) -> dict[str, Any]:
    deadline = time.monotonic() + 8
    task: dict[str, Any] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.02)
    raise AssertionError(f"Task {task_uuid} did not become terminal: {task}")


def _read_item(connection: sqlite3.Connection, team_uuid: str) -> tuple[str, str, str, int]:
    row = connection.execute(
        "SELECT intake_item_uuid,latest_revision_uuid,serving_revision_uuid,row_revision "
        "FROM mkb_intake_items WHERE team_uuid=?",
        (team_uuid,),
    ).fetchone()
    assert row is not None
    return row


def _generation_object_bytes(root: Path, team_uuid: str, logical_handle: str) -> bytes:
    """Read a local generation object through its digest-only logical handle."""

    digest = logical_handle.rsplit(":", maxsplit=1)[-1]
    return (root / "objects" / team_uuid / "sha256" / digest[:2] / digest[2:4] / digest).read_bytes()


def test_rebuild_and_metadata_lifecycle_paths_complete_through_public_http(tmp_path: Path) -> None:
    """Metadata refresh reuses S06/source summaries and recalculates S07/S08."""

    database_path = tmp_path / "mkb.sqlite3"
    token = "intake-lifecycle-token"
    headers = {"Authorization": f"Bearer {token}"}
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))

    with TestClient(app, raise_server_exceptions=True) as client:
        response = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "intake lifecycle"},
        )
        assert response.status_code == 201, response.text

        ingest_task_uuid, ingest_trace_uuid = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task_body(
                team_uuid=team_uuid,
                task_uuid=ingest_task_uuid,
                trace_uuid=ingest_trace_uuid,
                request_intent="intake.ingest",
                payload={
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "lifecycle-document",
                        "content": "Lifecycle operations retain and serve this document.",
                    }
                },
            ),
        )
        assert response.status_code == 201, response.text
        assert _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=ingest_task_uuid, headers=headers)["status"] == "succeeded"

        with sqlite3.connect(database_path) as connection:
            item_uuid, original_revision_uuid, serving_revision_uuid, _ = _read_item(connection, team_uuid)
            assert serving_revision_uuid == original_revision_uuid
            original_generation = connection.execute(
                "SELECT active_index_generation FROM mkb_index_active_pointers "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone()
            assert original_generation == (1,)

        rebuild_task_uuid, rebuild_trace_uuid = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task_body(
                team_uuid=team_uuid,
                task_uuid=rebuild_task_uuid,
                trace_uuid=rebuild_trace_uuid,
                request_intent="intake.rebuild",
                payload={
                    "intake_item_uuid": item_uuid,
                    "expected_intake_revision_uuid": original_revision_uuid,
                },
            ),
        )
        assert response.status_code == 201, response.text
        rebuild = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=rebuild_task_uuid, headers=headers)
        print("REBUILD TASK:", rebuild)
        assert rebuild["status"] == "succeeded", rebuild

        with sqlite3.connect(database_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone() == (1,)
            assert _read_item(connection, team_uuid)[1:3] == (original_revision_uuid, original_revision_uuid)
            assert connection.execute(
                "SELECT active_index_generation FROM mkb_index_active_pointers "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone() == (2,)

        no_change_task_uuid, no_change_trace_uuid = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task_body(
                team_uuid=team_uuid,
                task_uuid=no_change_task_uuid,
                trace_uuid=no_change_trace_uuid,
                request_intent="intake.update_metadata",
                payload={"intake_item_uuid": item_uuid, "semantics": {"context_metadata": "{}"}},
            ),
        )
        assert response.status_code == 201, response.text
        no_change = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=no_change_task_uuid, headers=headers)
        assert no_change["status"] == "succeeded", no_change

        with sqlite3.connect(database_path) as connection:
            assert connection.execute(
                "SELECT COUNT(*) FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone() == (1,)
            assert _read_item(connection, team_uuid)[1:3] == (original_revision_uuid, original_revision_uuid)
            assert connection.execute(
                "SELECT active_index_generation FROM mkb_index_active_pointers "
                "WHERE team_uuid=? AND intake_item_uuid=?",
                (team_uuid, item_uuid),
            ).fetchone() == (2,)
            assert connection.execute(
                "SELECT action_key FROM mkb_intake_item_transitions "
                "WHERE team_uuid=? AND causation_task_uuid=?",
                (team_uuid, no_change_task_uuid),
            ).fetchone() == ("no_change",)

        metadata_task_uuid, metadata_trace_uuid = uuid7(), uuid7()
        response = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task_body(
                team_uuid=team_uuid,
                task_uuid=metadata_task_uuid,
                trace_uuid=metadata_trace_uuid,
                request_intent="intake.update_metadata",
                payload={"intake_item_uuid": item_uuid, "semantics": {"context_metadata": "tier=gold"}},
            ),
        )
        assert response.status_code == 201, response.text
        metadata = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=metadata_task_uuid, headers=headers)
        assert metadata["status"] == "succeeded", metadata

        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "query": "lifecycle document",
                "return_k": 1,
                "recall_k": 3,
            },
        )
        assert search.status_code == 200, search.text
        assert search.json()["results"][0]["payload_content"] == "Lifecycle operations retain and serve this document."

    with sqlite3.connect(database_path) as connection:
        item_uuid_after, latest_revision_uuid, serving_revision_uuid, _ = _read_item(connection, team_uuid)
        assert item_uuid_after == item_uuid
        assert latest_revision_uuid != original_revision_uuid
        assert serving_revision_uuid == latest_revision_uuid
        assert connection.execute(
            "SELECT COUNT(*) FROM mkb_intake_revisions WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone() == (2,)
        assert connection.execute(
            "SELECT active_index_generation FROM mkb_index_active_pointers "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (team_uuid, item_uuid),
        ).fetchone() == (3,)
        assert connection.execute(
            "SELECT intake_revision_uuid,index_generation FROM mkb_publication_proofs "
            "WHERE team_uuid=? AND intake_item_uuid=? ORDER BY created_at DESC LIMIT 1",
            (team_uuid, item_uuid),
        ).fetchone() == (latest_revision_uuid, 3)
        semantic = connection.execute(
            "SELECT value_text FROM mkb_intake_revision_semantics "
            "WHERE team_uuid=? AND intake_revision_uuid=? AND semantic_key='context_metadata'",
            (team_uuid, latest_revision_uuid),
        ).fetchone()
        assert semantic == ("tier=gold",)
        metadata_artifacts = [
            {
                "generation_artifact_uuid": row[0],
                "artifact_type": row[1],
                "execution_uuid": row[2],
                "logical_handle": row[3],
                "content_digest": row[4],
            }
            for row in connection.execute(
                "SELECT generation_artifact_uuid,artifact_type,execution_uuid,logical_handle,content_digest "
                "FROM mkb_generation_artifacts WHERE team_uuid=? AND task_uuid=? ORDER BY artifact_type",
                (team_uuid, metadata_task_uuid),
            )
        ]
        metadata_processes = {
            row[0]
            for row in connection.execute(
                "SELECT process_key FROM mkb_processes WHERE team_uuid=? AND task_uuid=?",
                (team_uuid, metadata_task_uuid),
            )
        }

        # The metadata Task owns a fresh S07 package only.  No S06 Process or
        # artifact may be manufactured merely because S04 semantics changed.
        assert {artifact["artifact_type"] for artifact in metadata_artifacts} == {
            "construction_document",
            "dual_channel_projection",
            "construction_validation_report",
        }
        assert "lsrag.structurize" not in metadata_processes
        metadata_by_type = {artifact["artifact_type"]: artifact for artifact in metadata_artifacts}
        metadata_construction = json.loads(
            _generation_object_bytes(
                tmp_path / "objects",
                team_uuid,
                metadata_by_type["construction_document"]["logical_handle"],
            )
        )
        metadata_dual = json.loads(
            _generation_object_bytes(
                tmp_path / "objects",
                team_uuid,
                metadata_by_type["dual_channel_projection"]["logical_handle"],
            )
        )
        source_structure = connection.execute(
            "SELECT execution_uuid,generation_artifact_uuid FROM mkb_generation_artifacts "
            "WHERE team_uuid=? AND generation_artifact_uuid=? AND artifact_type='structure_document'",
            (team_uuid, metadata_construction["structure_generation_artifact_uuid"]),
        ).fetchone()
        assert source_structure is not None
        source_projection = connection.execute(
            "SELECT generation_artifact_uuid FROM mkb_generation_artifacts "
            "WHERE team_uuid=? AND generation_artifact_uuid=? AND artifact_type='retrieval_block_projection'",
            (team_uuid, metadata_construction["projection_generation_artifact_uuid"]),
        ).fetchone()
        assert source_projection is not None
        source_dual = connection.execute(
            "SELECT logical_handle FROM mkb_generation_artifacts WHERE team_uuid=? AND execution_uuid=? "
            "AND artifact_type='dual_channel_projection'",
            (team_uuid, source_structure[0]),
        ).fetchone()
        assert source_dual is not None
        source_dual_payload = json.loads(
            _generation_object_bytes(tmp_path / "objects", team_uuid, source_dual[0])
        )
        assert metadata_construction["structure_generation_artifact_uuid"] == source_structure[1]
        assert metadata_construction["projection_generation_artifact_uuid"] == source_projection[0]
        assert {
            unit["unit_id"]: unit["summary"] for unit in metadata_dual["units"]
        } == {unit["unit_id"]: unit["summary"] for unit in source_dual_payload["units"]}

        source_vector_digests = {
            (row[0], row[1]): row[2]
            for row in connection.execute(
                "SELECT block_or_unit_id,channel,content_digest FROM mkb_vector_records "
                "WHERE team_uuid=? AND execution_uuid=? ORDER BY block_or_unit_id,channel",
                (team_uuid, source_structure[0]),
            )
        }
        metadata_vector_digests = {
            (row[0], row[1]): row[2]
            for row in connection.execute(
                "SELECT block_or_unit_id,channel,content_digest FROM mkb_vector_records "
                "WHERE team_uuid=? AND task_uuid=? ORDER BY block_or_unit_id,channel",
                (team_uuid, metadata_task_uuid),
            )
        }
        assert metadata_vector_digests.keys() == source_vector_digests.keys()
        assert all(
            metadata_vector_digests[coordinate] != source_vector_digests[coordinate]
            for coordinate in metadata_vector_digests
        )
