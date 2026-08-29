"""NH5-T08: semantic cutover inherits clean and republishes context/facets."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.models import ObjectHandle
from tests.e2e.test_source_capability_paths import _settings


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict:
    deadline = time.monotonic() + 30
    latest = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def _search(client: TestClient, team_uuid: str, headers: dict[str, str], namespace: str, realm: str) -> dict:
    response = client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers=headers,
        json={
            "schema_version": "mkb.retrieval.v2",
            "team_uuid": team_uuid,
            "namespace_key": namespace,
            "query": "NH5 metadata semantic refresh",
            "filters": {"realm": realm, "vector_channel": "original"},
            "return_k": 10,
            "recall_k": 20,
        },
    )
    assert response.status_code == 200, response.text
    return response.json()


def test_metadata_refresh_inherits_clean_and_projects_facets(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid, ingest_task, ingest_trace = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": "Bearer source-capability-token"}
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh5-metadata"},
        ).status_code == 201
        ingest = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": ingest_task,
                "trace_uuid": ingest_trace,
                "request_intent": "intake.ingest",
                "payload": {
                    "json_prompt_id": "promptB.json.generic",
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "nh5-metadata-source",
                        "content": "NH5 metadata semantic refresh admitted clean body",
                        "realm": "realm-before",
                        "type": "article",
                        "channel": "policy",
                        "source_name": "metadata-source",
                        "context_tags": ["tag:before"],
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": ingest_task,
                    "trace_uuid": ingest_trace,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh5-metadata",
                    "created_at": utc_now(),
                },
            },
        )
        assert ingest.status_code == 201, ingest.text
        assert _wait(client, team_uuid, ingest_task, headers)["status"] == "succeeded"

        async def before() -> dict:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT i.intake_item_uuid,i.latest_revision_uuid,a.content_digest,a.stored_object_uuid "
                    "FROM mkb_intake_items i JOIN mkb_intake_artifacts a ON a.team_uuid=i.team_uuid "
                    "AND a.owner_revision_uuid=i.latest_revision_uuid AND a.artifact_role='clean_text' "
                    "WHERE i.team_uuid=?",
                    (team_uuid,),
                )
                namespace = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert row is not None and namespace is not None
            return {**row, "namespace_key": namespace["namespace_key"]}

        old = client.portal.call(before)
        metadata_task, metadata_trace = uuid7(), uuid7()
        update = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json={
                "schema_version": "mkb.task.v1",
                "team_uuid": team_uuid,
                "task_uuid": metadata_task,
                "trace_uuid": metadata_trace,
                "request_intent": "intake.update_metadata",
                "payload": {
                    "intake_item_uuid": old["intake_item_uuid"],
                    "expected_intake_revision_uuid": old["latest_revision_uuid"],
                    "semantics": {"realm": "realm-after", "context_tags": "tag:after"},
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": metadata_task,
                    "trace_uuid": metadata_trace,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh5-metadata",
                    "created_at": utc_now(),
                },
            },
        )
        assert update.status_code == 201, update.text
        terminal = _wait(client, team_uuid, metadata_task, headers)
        assert terminal["status"] == "succeeded", terminal

        async def after() -> tuple[dict, dict, bytes, int]:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT i.latest_revision_uuid,a.content_digest,a.stored_object_uuid "
                    "FROM mkb_intake_items i JOIN mkb_intake_artifacts a ON a.team_uuid=i.team_uuid "
                    "AND a.owner_revision_uuid=i.latest_revision_uuid AND a.artifact_role='clean_text' "
                    "WHERE i.team_uuid=? AND i.intake_item_uuid=?",
                    (team_uuid, old["intake_item_uuid"]),
                )
                semantics = await tx.fetchall(
                    "SELECT semantic_key,value_text,value_int FROM mkb_intake_revision_semantics "
                    "WHERE team_uuid=? AND intake_revision_uuid=(SELECT latest_revision_uuid FROM mkb_intake_items "
                    "WHERE team_uuid=? AND intake_item_uuid=?)",
                    (team_uuid, team_uuid, old["intake_item_uuid"]),
                )
                structure = await tx.fetchone(
                    "SELECT a.logical_handle FROM mkb_generation_pointers p JOIN mkb_generation_artifacts a "
                    "ON a.team_uuid=p.team_uuid AND a.generation_artifact_uuid=p.current_generation_artifact_uuid "
                    "WHERE p.team_uuid=? AND p.artifact_type='structure_document' "
                    "AND a.intake_revision_uuid=(SELECT latest_revision_uuid FROM mkb_intake_items "
                    "WHERE team_uuid=? AND intake_item_uuid=?)",
                    (team_uuid, team_uuid, old["intake_item_uuid"]),
                )
                facets = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_vector_record_facets f JOIN mkb_vector_records r "
                    "ON r.vector_record_uuid=f.vector_record_uuid WHERE f.team_uuid=? "
                    "AND r.intake_revision_uuid=(SELECT latest_revision_uuid FROM mkb_intake_items "
                    "WHERE team_uuid=? AND intake_item_uuid=?) AND f.facet_key='realm' AND f.facet_value='realm-after'",
                    (team_uuid, team_uuid, old["intake_item_uuid"]),
                )
            assert row is not None and structure is not None and facets is not None
            structure_bytes = await app.state.container.storage.read_verified(
                team_uuid, ObjectHandle(value=structure["logical_handle"])
            )
            return row, {entry["semantic_key"]: entry for entry in semantics}, structure_bytes, int(facets["count"])

        new, semantics, structure_bytes, facet_count = client.portal.call(after)
        assert new["latest_revision_uuid"] != old["latest_revision_uuid"]
        assert new["content_digest"] == old["content_digest"]
        assert new["stored_object_uuid"] == old["stored_object_uuid"]
        assert semantics["realm"]["value_text"] == "realm-after"
        assert semantics["context_tags"]["value_text"] == "tag:after"
        assert json.loads(semantics["filter_metadata"]["value_text"])["realm"] == "realm-after"
        assert json.loads(semantics["context_metadata"]["value_text"])["tags"] == ["tag:after"]
        assert json.loads(structure_bytes)["context_meta"]["realm"] == "realm-after"
        assert facet_count > 0
        assert _search(client, team_uuid, headers, old["namespace_key"], "realm-after")["results"]
        assert _search(client, team_uuid, headers, old["namespace_key"], "realm-before")["results"] == []
