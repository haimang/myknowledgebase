"""S08 generation-scoped logical vector purge coverage."""

from __future__ import annotations

import asyncio
import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.vector.models import VectorizeCommand
from src.persistence.sqlite_port import SqlitePersistence
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
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        body = response.json()
        if body["status"] in {"succeeded", "failed", "cancelled"}:
            return body
        time.sleep(0.02)
    raise AssertionError("task did not reach a terminal state")


async def _run_purge_process(
    *,
    database_path: Path,
    team_uuid: str,
    task_uuid: str,
    execution_uuid: str,
    generation_artifact_uuid: str,
) -> dict[str, object]:
    persistence = SqlitePersistence(database_path, Path("src/persistence/migrations"))
    await persistence.migrate()
    command_digest = stable_digest(
        {
            "mode": "purge_generation",
            "team_uuid": team_uuid,
            "execution_uuid": execution_uuid,
            "target_generation_artifact_uuid": generation_artifact_uuid,
            "channel_filter": "original",
        }
    )
    command = ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=team_uuid,
        task_uuid=task_uuid,
        trace_uuid=uuid7(),
        execution_uuid=execution_uuid,
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
        execution_uuid=execution_uuid,
        command_input_digest=command_digest,
        target_generation_artifact_uuids=[generation_artifact_uuid],
        channel_filter="original",
    )
    # The Process leaf is deliberately invoked with only its frozen command;
    # no Task endpoint or public request intent can select a vector purge.
    pipeline = IntakePipeline(persistence, None, None)  # type: ignore[arg-type]
    material, route_extra, callback = await pipeline._vectorize(
        command,
        {"request_intent": "intake.ingest", "vectorize_command": vectorize_command.model_dump(mode="json")},
    )
    async with persistence.transaction() as tx:
        await callback(tx, {})
    await persistence.close()
    receipt = material.envelope["output"]["vectorization_receipt"]
    assert route_extra == {"vectorize_outcome": receipt}
    return receipt


def test_purge_generation_soft_deletes_only_the_requested_generation_and_channel(tmp_path: Path) -> None:
    team_uuid = uuid7()
    first_task_uuid, second_task_uuid = uuid7(), uuid7()
    first_trace_uuid, second_trace_uuid = uuid7(), uuid7()
    token = "vector-purge-token"
    database_path = tmp_path / "mkb.sqlite3"
    app = create_app(
        Settings(
            internal_token=token,
            database_path=database_path,
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

    database_uri = f"file:{database_path}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        target = connection.execute(
            "SELECT execution_uuid,generation_artifact_uuid FROM mkb_generation_artifacts "
            "WHERE team_uuid=? AND task_uuid=? AND artifact_type='dual_channel_projection'",
            (team_uuid, first_task_uuid),
        ).fetchone()
        other = connection.execute(
            "SELECT generation_artifact_uuid FROM mkb_generation_artifacts "
            "WHERE team_uuid=? AND task_uuid=? AND artifact_type='dual_channel_projection'",
            (team_uuid, second_task_uuid),
        ).fetchone()
        assert target is not None and other is not None
        before_target = connection.execute(
            "SELECT channel,COUNT(*) AS count FROM mkb_vector_records "
            "WHERE team_uuid=? AND generation_artifact_uuid=? AND deleted_at IS NULL GROUP BY channel ORDER BY channel",
            (team_uuid, target["generation_artifact_uuid"]),
        ).fetchall()
        assert {row["channel"] for row in before_target} == {"original", "summary"}

    receipt = asyncio.run(
        _run_purge_process(
            database_path=database_path,
            team_uuid=team_uuid,
            task_uuid=first_task_uuid,
            execution_uuid=target["execution_uuid"],
            generation_artifact_uuid=target["generation_artifact_uuid"],
        )
    )
    assert receipt["schema_version"] == "mkb.vectorize-outcome.v1"
    assert receipt["mode"] == "purge_generation"
    assert receipt["handoff"] is None
    purge_receipt = receipt["purge_receipt"]
    assert purge_receipt["channel_filter"] == "original"
    assert purge_receipt["matched_records"] == purge_receipt["soft_deleted_records"]
    assert purge_receipt["matched_records"] == sum(row["count"] for row in before_target if row["channel"] == "original")

    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        target_rows = connection.execute(
            "SELECT channel,deleted_at FROM mkb_vector_records WHERE team_uuid=? AND generation_artifact_uuid=?",
            (team_uuid, target["generation_artifact_uuid"]),
        ).fetchall()
        other_rows = connection.execute(
            "SELECT deleted_at FROM mkb_vector_records WHERE team_uuid=? AND generation_artifact_uuid=?",
            (team_uuid, other["generation_artifact_uuid"]),
        ).fetchall()
        artifacts = connection.execute(
            "SELECT COUNT(*) FROM mkb_generation_artifacts WHERE team_uuid=? AND generation_artifact_uuid IN (?,?)",
            (team_uuid, target["generation_artifact_uuid"], other["generation_artifact_uuid"]),
        ).fetchone()
        task_states = connection.execute(
            "SELECT task_uuid,status FROM mkb_tasks WHERE team_uuid=? AND task_uuid IN (?,?) ORDER BY task_uuid",
            (team_uuid, first_task_uuid, second_task_uuid),
        ).fetchall()

    assert target_rows
    assert all(row["deleted_at"] is not None for row in target_rows if row["channel"] == "original")
    assert all(row["deleted_at"] is None for row in target_rows if row["channel"] == "summary")
    assert other_rows and all(row["deleted_at"] is None for row in other_rows)
    assert artifacts is not None and artifacts[0] == 2
    assert {row["status"] for row in task_states} == {"succeeded"}
