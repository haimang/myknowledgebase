"""D07-E2E-03: a bounded human gate resumes the same durable workflow."""

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


def _terminal_task(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.02)
    raise AssertionError("workflow did not reach a terminal Task state")


def test_human_review_gate_is_task_scoped_idempotent_and_resumes(tmp_path: Path) -> None:
    token = "gate-integration-token"
    settings = Settings(
        internal_token=token,
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        persistence_backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
        # The test polls a local supervisor every 20ms.  Isolate that load
        # from production's deliberately conservative S16 defaults.
        rate_limit_ip_per_min=1_000,
        rate_limit_token_per_min=2_000,
    )
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(create_app(settings), raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "review-golden"},
            ).status_code
            == 201
        )
        assert (
            client.post(
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
                            "external_key": "requires-review",
                            "content": "Human review preserves immutable candidate evidence.",
                            "require_human_review": True,
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
            ).status_code
            == 201
        )

        deadline = time.monotonic() + 5
        task: dict[str, object] = {}
        while time.monotonic() < deadline:
            response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
            assert response.status_code == 200, response.text
            task = response.json()
            if task["action_required"]:
                break
            time.sleep(0.02)
        assert task["status"] == "running"
        action_required = task["action_required"]
        assert isinstance(action_required, dict)

        gates = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}/gates", headers=headers)
        assert gates.status_code == 200, gates.text
        gate = gates.json()["items"][0]
        assert gate["gate_uuid"] == action_required["gate_uuid"]
        assert gate["allowed_actions"] == ["approve", "reject"]
        assert "execution_uuid" not in str(gate)
        assert "process_uuid" not in str(gate)

        # The public projection intentionally hides runtime IDs, but the
        # durable Gate target must still bind the exact accepted Intake and
        # predecessor preflight evidence.  In particular, no route-derived
        # placeholder may stand in for a clean Artifact or output ref.
        connection = sqlite3.connect(settings.resolved_database_path)
        connection.row_factory = sqlite3.Row
        try:
            target_row = connection.execute(
                "SELECT * FROM mkb_execution_gate_targets WHERE gate_uuid=?", (gate["gate_uuid"],)
            ).fetchone()
            assert target_row is not None
            target = json.loads(target_row["review_target_json"])
            intake_refs = json.loads(target_row["intake_refs_json"])
            assert target["intake_refs"] == intake_refs
            assert target["intake_refs"]["intake_item_uuid"]
            assert target["intake_refs"]["intake_revision_uuid"]
            assert target["intake_refs"]["intake_snapshot_uuid"]
            assert target["intake_refs"]["candidate_set_uuid"]
            assert target["accept_process"]["process_uuid"]
            assert target["accept_process"]["fencing_generation"] >= 0
            assert target["preflight_outcome"]["process_uuid"]
            assert target["preflight_outcome"]["check_set_digest"]
            assert target["preflight_outcome"]["output_manifest_ref"] == target_row["preflight_outcome_ref"]
            assert "placeholder" not in target_row["clean_artifact_digest"]
            assert not target_row["preflight_outcome_ref"].startswith("mkbworkflow:")

            preflight = connection.execute(
                "SELECT output_manifest_ref,output_manifest_digest,status FROM mkb_processes WHERE process_uuid=?",
                (target["preflight_outcome"]["process_uuid"],),
            ).fetchone()
            clean_artifact = connection.execute(
                "SELECT content_digest,owner_revision_uuid FROM mkb_intake_artifacts WHERE intake_artifact_uuid=?",
                (target["clean_artifact"]["intake_artifact_uuid"],),
            ).fetchone()
            assert preflight is not None and preflight["status"] == "succeeded"
            assert preflight["output_manifest_ref"] == target_row["preflight_outcome_ref"]
            assert preflight["output_manifest_digest"] == target["preflight_outcome"]["output_manifest_digest"]
            assert clean_artifact is not None
            assert clean_artifact["content_digest"] == target_row["clean_artifact_digest"]
            assert clean_artifact["owner_revision_uuid"] == target["intake_refs"]["intake_revision_uuid"]
        finally:
            connection.close()

        decision_body = {
            "expected_gate_revision": gate["revision"],
            "target_digest": gate["target_digest"],
            "action": "approve",
            "idempotency_key": "gate-approve-e2e",
        }
        accepted = client.post(
            f"/v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate['gate_uuid']}:decide",
            headers=headers,
            json=decision_body,
        )
        assert accepted.status_code == 200, accepted.text
        replay = client.post(
            f"/v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate['gate_uuid']}:decide",
            headers=headers,
            json=decision_body,
        )
        assert replay.status_code == 200, replay.text
        assert replay.json()["idempotent"] is True
        assert replay.json()["decision_uuid"] == accepted.json()["decision_uuid"]

        final = _terminal_task(client, team_uuid, task_uuid, headers)
        assert final["status"] == "succeeded", final
        assert final["proof_ref"]
