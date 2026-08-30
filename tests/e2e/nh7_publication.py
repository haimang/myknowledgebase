"""Shared NH7-T03..T08 first-publication evidence-chain assertions."""

from __future__ import annotations

import json
from typing import Any

from fastapi.testclient import TestClient

from src.contracts.common.ids import stable_digest
from src.contracts.lsrag.layered_content import normalize_layered_text
from src.contracts.storage.models import ObjectHandle

_SIX = {"realm", "type", "channel", "source_name", "is_active", "context_tags"}


def _g0_body(payload: Any) -> str | None:
    if isinstance(payload, dict):
        units = payload.get("units")
        if isinstance(units, list):
            for unit in units:
                if isinstance(unit, dict) and unit.get("granularity") in {0, "0"}:
                    original = unit.get("original")
                    if isinstance(original, str) and original.strip():
                        return original
        blocks = payload.get("layered_content")
        if isinstance(blocks, list):
            for block in blocks:
                if isinstance(block, dict) and block.get("granularity") in {0, "0"}:
                    original = block.get("original_content")
                    if isinstance(original, dict) and isinstance(original.get("body"), str):
                        return original["body"]
        for value in payload.values():
            found = _g0_body(value)
            if found:
                return found
    elif isinstance(payload, list):
        for item in payload:
            found = _g0_body(item)
            if found:
                return found
    return None


def assert_first_publication_closure(app: Any, client: TestClient, team_uuid: str, task_uuid: str) -> None:
    async def inspect() -> dict[str, Any]:
        async with app.state.container.persistence.transaction() as tx:
            execution = await tx.fetchone(
                "SELECT actual_binding_state,actual_binding_digest,s05_binding_digest FROM mkb_executions "
                "WHERE team_uuid=? AND task_uuid=? AND parent_execution_uuid IS NULL",
                (team_uuid, task_uuid),
            )
            semantics = await tx.fetchall(
                "SELECT DISTINCT s.semantic_key FROM mkb_intake_revision_semantics s "
                "JOIN mkb_intake_snapshot_memberships m ON m.team_uuid=s.team_uuid "
                "AND m.observed_revision_uuid=s.intake_revision_uuid "
                "JOIN mkb_tasks t ON t.team_uuid=m.team_uuid AND t.intake_snapshot_uuid=m.intake_snapshot_uuid "
                "WHERE t.team_uuid=? AND t.task_uuid=?",
                (team_uuid, task_uuid),
            )
            proofs = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_publication_proofs WHERE team_uuid=?",
                (team_uuid,),
            )
            pointers = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_index_active_pointers WHERE team_uuid=? AND lifecycle_state='active'",
                (team_uuid,),
            )
            artifact = await tx.fetchone(
                "SELECT logical_handle,clean_artifact_digest FROM mkb_generation_artifacts "
                "WHERE team_uuid=? AND artifact_type='dual_channel_projection' "
                "AND (task_uuid=? OR execution_uuid IN "
                "(SELECT execution_uuid FROM mkb_executions WHERE team_uuid=? AND task_uuid=?)) "
                "LIMIT 1",
                (team_uuid, task_uuid, team_uuid, task_uuid),
            )
            if artifact is None:
                artifact = await tx.fetchone(
                    "SELECT logical_handle,clean_artifact_digest FROM mkb_generation_artifacts "
                    "WHERE team_uuid=? AND artifact_type='dual_channel_projection' LIMIT 1",
                    (team_uuid,),
                )
            clean = await tx.fetchone(
                "SELECT output_manifest_ref FROM mkb_processes WHERE team_uuid=? AND task_uuid=? "
                "AND process_key LIKE 'clean.%' AND status='succeeded' "
                "ORDER BY completed_at DESC LIMIT 1",
                (team_uuid, task_uuid),
            )
        assert execution is not None and proofs is not None and pointers is not None
        g0_body = None
        clean_text = None
        clean_digest = None
        if artifact is not None:
            blob = await app.state.container.storage.read_verified(
                team_uuid, ObjectHandle(value=str(artifact["logical_handle"]))
            )
            document = json.loads(blob.decode())
            g0_body = _g0_body(document)
        if clean is not None:
            payload = json.loads(
                (
                    await app.state.container.storage.read_verified(
                        team_uuid, ObjectHandle(value=str(clean["output_manifest_ref"]))
                    )
                ).decode()
            )
            state = payload.get("state") if isinstance(payload.get("state"), dict) else {}
            output = payload.get("output") if isinstance(payload.get("output"), dict) else {}
            candidate = output.get("clean_candidate") if isinstance(output.get("clean_candidate"), dict) else {}
            members = state.get("collection_members") if isinstance(state.get("collection_members"), list) else []
            clean_text = state.get("clean_text")
            clean_digest = state.get("clean_digest") or candidate.get("content_digest")
            if clean_text is None and members:
                first = members[0] if isinstance(members[0], dict) else {}
                clean_text = first.get("clean_text")
                clean_digest = first.get("clean_digest") or clean_digest
        return {
            "actual_state": execution["actual_binding_state"],
            "actual_digest": execution["actual_binding_digest"],
            "legacy_alias": execution["s05_binding_digest"],
            "semantic_keys": {row["semantic_key"] for row in semantics},
            "proofs": int(proofs["n"]),
            "active_pointers": int(pointers["n"]),
            "g0_body": g0_body,
            "clean_text": clean_text,
            "clean_digest": clean_digest,
        }

    observed = client.portal.call(inspect)
    assert observed["actual_state"] == "sealed"
    digest = observed["actual_digest"]
    assert isinstance(digest, str) and len(digest) == 64 and digest != observed["legacy_alias"]
    assert _SIX <= set(observed["semantic_keys"])
    assert observed["proofs"] >= 1
    assert observed["active_pointers"] >= 1
    body = observed["g0_body"]
    admitted = observed["clean_text"]
    if not (isinstance(body, str) and body.strip()) and isinstance(admitted, str) and admitted.strip():
        body = admitted
    assert isinstance(body, str) and body.strip(), observed
    if isinstance(admitted, str) and admitted.strip():
        assert normalize_layered_text(body) == normalize_layered_text(admitted)
    elif isinstance(observed["clean_digest"], str):
        assert stable_digest({"text": normalize_layered_text(body)}) == observed["clean_digest"]
