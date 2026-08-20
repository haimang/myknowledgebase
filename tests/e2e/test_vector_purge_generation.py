"""S08 generation-scoped logical vector purge coverage."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.vector.models import VectorizeCommand
from src.runtime.config import Settings
from src.runtime.intake_pipeline import IntakePipeline


def _task_request(*, team_uuid: str, task_uuid: str, trace_uuid: str, external_key: str, content: str) -> dict[str, object]:
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
                "external_key": external_key,
                "content": content,
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
    }


def _wait_for_terminal(client: TestClient, *, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        if body["status"] in {"succeeded", "failed", "cancelled"}:
            return body
        time.sleep(0.02)
    raise AssertionError("task did not reach a terminal state")


def test_purge_generation_soft_deletes_only_the_requested_generation(tmp_path: Path) -> None:
    team_uuid = uuid7()
    first_task_uuid, second_task_uuid = uuid7(), uuid7()
    first_trace_uuid, second_trace_uuid = uuid7(), uuid7()
    token = "vector-purge-token"
    app = create_app(
        Settings(
            internal_token=token,
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
    )
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app, raise_server_exceptions=True) as client:
        created_team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "vector-purge"},
        )
        assert created_team.status_code == 201, created_team.text
        for task_uuid, trace_uuid, external_key, content in (
            (first_task_uuid, first_trace_uuid, "purge-first", "First document. Its original channel must be purged."),
            (second_task_uuid, second_trace_uuid, "purge-second", "Second document remains wholly active."),
        ):
            created = client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=headers,
                json=_task_request(
                    team_uuid=team_uuid,
                    task_uuid=task_uuid,
                    trace_uuid=trace_uuid,
                    external_key=external_key,
                    content=content,
                ),
            )
            assert created.status_code == 201, created.text
            terminal = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
            assert terminal["status"] == "succeeded", terminal

        persistence = app.state.container.persistence

        async def inspect_and_purge() -> dict[str, object]:
            async with persistence.transaction() as tx:
                target = await tx.fetchone(
                    "SELECT execution_uuid,generation_artifact_uuid FROM mkb_generation_artifacts "
                    "WHERE team_uuid=? AND task_uuid=? AND artifact_type='dual_channel_projection'",
                    (team_uuid, first_task_uuid),
                )
                other = await tx.fetchone(
                    "SELECT generation_artifact_uuid FROM mkb_generation_artifacts "
                    "WHERE team_uuid=? AND task_uuid=? AND artifact_type='dual_channel_projection'",
                    (team_uuid, second_task_uuid),
                )
                before_target = await tx.fetchall(
                    "SELECT channel,COUNT(*) AS count FROM mkb_vector_records "
                    "WHERE team_uuid=? AND generation_artifact_uuid=? AND deleted_at IS NULL GROUP BY channel ORDER BY channel",
                    (team_uuid, target["generation_artifact_uuid"]),
                )
            assert target is not None and other is not None
            assert {row["channel"] for row in before_target} == {"original", "summary"}
            command_digest = stable_digest(
                {
                    "mode": "purge_generation",
                    "team_uuid": team_uuid,
                    "execution_uuid": target["execution_uuid"],
                    "target_generation_artifact_uuid": target["generation_artifact_uuid"],
                    "channel_filter": "all",
                }
            )
            command = ProcessCommand(
                schema_version="mkb.process-command.v1",
                team_uuid=team_uuid,
                task_uuid=first_task_uuid,
                trace_uuid=uuid7(),
                execution_uuid=target["execution_uuid"],
                process_uuid=uuid7(),
                process_key="lsrag.vectorize",
                process_contract_version="v1",
                fencing_generation=1,
                command_input_digest=command_digest,
                input_manifest_ref=f"mkbobj:v1:purge:{command_digest}",
                input_manifest_digest=command_digest,
                config_snapshot_ref=f"mkbobj:v1:config:{command_digest}",
                config_snapshot_digest=command_digest,
                binding_digest=command_digest,
            )
            vectorize_command = VectorizeCommand(
                mode="purge_generation",
                team_uuid=team_uuid,
                execution_uuid=target["execution_uuid"],
                command_input_digest=command_digest,
                target_generation_artifact_uuids=[target["generation_artifact_uuid"]],
                channel_filter="all",
            )
            pipeline = IntakePipeline(persistence, None, None)  # type: ignore[arg-type]
            material, route_extra, callback = await pipeline._vectorize(
                command,
                {"request_intent": "intake.ingest", "vectorize_command": vectorize_command.model_dump(mode="json")},
            )
            async with persistence.transaction() as tx:
                await callback(tx, {})
            receipt = material.envelope["output"]["vectorization_receipt"]
            async with persistence.transaction() as tx:
                target_rows = await tx.fetchall(
                    "SELECT channel,deleted_at FROM mkb_vector_records WHERE team_uuid=? AND generation_artifact_uuid=?",
                    (team_uuid, target["generation_artifact_uuid"]),
                )
                other_rows = await tx.fetchall(
                    "SELECT deleted_at FROM mkb_vector_records WHERE team_uuid=? AND generation_artifact_uuid=?",
                    (team_uuid, other["generation_artifact_uuid"]),
                )
                artifacts = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_generation_artifacts WHERE team_uuid=? AND generation_artifact_uuid IN (?,?)",
                    (team_uuid, target["generation_artifact_uuid"], other["generation_artifact_uuid"]),
                )
                task_states = await tx.fetchall(
                    "SELECT task_uuid,status FROM mkb_tasks WHERE team_uuid=? AND task_uuid IN (?,?) ORDER BY task_uuid",
                    (team_uuid, first_task_uuid, second_task_uuid),
                )
            return {
                "receipt": receipt,
                "route_extra": route_extra,
                "before_count": sum(int(row["count"]) for row in before_target),
                "target_rows": list(target_rows),
                "other_rows": list(other_rows),
                "artifacts": artifacts,
                "task_states": list(task_states),
            }

        observed = client.portal.call(inspect_and_purge)

    receipt = observed["receipt"]
    assert observed["route_extra"] == {"vectorize_outcome": receipt}
    assert receipt["schema_version"] == "mkb.vectorize-outcome.v1"
    assert receipt["mode"] == "purge_generation"
    assert receipt["handoff"] is None
    purge_receipt = receipt["purge_receipt"]
    assert purge_receipt["channel_filter"] == "all"
    assert purge_receipt["matched_records"] == purge_receipt["soft_deleted_records"]
    assert purge_receipt["matched_records"] == observed["before_count"]
    target_rows = observed["target_rows"]
    assert target_rows
    assert all(row["deleted_at"] is not None for row in target_rows)
    assert observed["other_rows"] and all(row["deleted_at"] is None for row in observed["other_rows"])
    assert observed["artifacts"] == {"count": 2}
    assert {row["status"] for row in observed["task_states"]} == {"succeeded"}
