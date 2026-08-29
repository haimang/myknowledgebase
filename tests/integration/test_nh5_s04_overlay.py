"""NH5-T04: committed S04 semantics overlay the generated S06 document."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.storage.models import ObjectHandle
from tests.e2e.test_source_capability_paths import _settings
from tests.integration.test_nh5_four_kind_semantics import _body, _wait


def test_structure_context_equals_committed_s04_and_g0_equals_clean(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer source-capability-token"}
    source = {
        "source_kind": "inline_payload",
        "external_key": "nh5-overlay",
        "content": "NH5 admitted clean overlay body",
        "realm": "documentation",
        "type": "closure",
        "channel": "owner-channel",
        "source_name": "s04-owner",
        "context_tags": ["tag:one", "tag:two"],
    }
    request = _body(team_uuid, source)
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh5-overlay"},
        ).status_code == 201
        created = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=request)
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, request["task_uuid"], headers)
        assert terminal["status"] == "succeeded", terminal

        async def inspect() -> tuple[dict, dict, bytes, bytes, bytes]:
            async with app.state.container.persistence.transaction() as tx:
                semantics = await tx.fetchall(
                    "SELECT v.semantic_key,v.value_text,v.value_int FROM mkb_intake_revision_semantics v "
                    "JOIN mkb_intake_items i ON i.team_uuid=v.team_uuid "
                    "AND i.latest_revision_uuid=v.intake_revision_uuid WHERE v.team_uuid=?",
                    (team_uuid,),
                )
                structure = await tx.fetchone(
                    "SELECT logical_handle FROM mkb_generation_artifacts WHERE team_uuid=? "
                    "AND artifact_type='structure_document'",
                    (team_uuid,),
                )
                clean = await tx.fetchone(
                    "SELECT logical_handle FROM mkb_intake_artifacts WHERE team_uuid=? AND artifact_role='clean_text'",
                    (team_uuid,),
                )
                process = await tx.fetchone(
                    "SELECT output_manifest_ref FROM mkb_processes WHERE team_uuid=? "
                    "AND process_key='lsrag.structurize' AND status='succeeded'",
                    (team_uuid,),
                )
            assert structure is not None and clean is not None and process is not None
            structure_bytes = await app.state.container.storage.read_verified(
                team_uuid, ObjectHandle(value=structure["logical_handle"])
            )
            clean_bytes = await app.state.container.storage.read_verified(
                team_uuid, ObjectHandle(value=clean["logical_handle"])
            )
            process_bytes = await app.state.container.storage.read_verified(
                team_uuid, ObjectHandle(value=process["output_manifest_ref"])
            )
            return {row["semantic_key"]: row for row in semantics}, structure, structure_bytes, clean_bytes, process_bytes

        semantics, _, structure_bytes, clean_bytes, process_bytes = client.portal.call(inspect)
    document = json.loads(structure_bytes)
    assert document["context_meta"] == {
        "realm": semantics["realm"]["value_text"],
        "type": semantics["type"]["value_text"],
        "channel": semantics["channel"]["value_text"],
        "source_name": semantics["source_name"]["value_text"],
        "tags": semantics["context_tags"]["value_text"].splitlines(),
    }
    stage = json.loads(process_bytes)
    layered = stage["state"]["layered_content_candidate"]
    assert layered["context_meta"] == document["context_meta"]
    g0 = next(block for block in layered["layered_content"] if block["granularity"] == 0)
    assert g0["original_content"]["body"] == clean_bytes.decode("utf-8")
    assert source["realm"] not in g0["original_content"]["body"]
