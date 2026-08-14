"""S06 Task-scoped immutable generation-artifact read-contract coverage."""

from __future__ import annotations

import asyncio
import base64
import json
from dataclasses import dataclass
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.api.models import TaskCreateRequest, TeamCreateRequest
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.config import Settings
from src.runtime.task_service import TaskService
from src.services.events import DomainEventWriter
from src.services.teams import TeamService


@dataclass(frozen=True, slots=True)
class Seed:
    team_uuid: str
    task_uuid: str
    foreign_task_uuid: str
    execution_uuid: str
    foreign_execution_uuid: str
    process_uuid: str
    first_structure_uuid: str
    second_structure_uuid: str
    projection_uuid: str
    invalid_uuid: str
    foreign_artifact_uuid: str
    mismatched_artifact_uuid: str


def _cursor_payload(cursor: str) -> dict[str, object]:
    padded = cursor + "=" * (-len(cursor) % 4)
    value = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    assert isinstance(value, dict)
    return value


def _task_request(team_uuid: str, task_uuid: str, trace_uuid: str, external_key: str) -> TaskCreateRequest:
    return TaskCreateRequest.model_validate(
        {
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
                    "content": "safe fixture body",
                }
            },
            "audit": {
                "schema_version": "mkb.task-audit.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit_type": "business_review",
                "audit_status": "not_required",
                "source": "generation-artifact-contract-test",
                "created_at": utc_now(),
            },
        }
    )


async def _seed(tmp_path: Path) -> Seed:
    persistence = SqlitePersistence(tmp_path / "generation-artifacts.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    teams = TeamService(persistence)
    tasks = TaskService(persistence, teams, DomainEventWriter())
    team_uuid, task_uuid, foreign_task_uuid = uuid7(), uuid7(), uuid7()
    await teams.create(TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="artifact-team"))
    await tasks.create(_task_request(team_uuid, task_uuid, uuid7(), "target"), "fixture-token")
    await tasks.create(_task_request(team_uuid, foreign_task_uuid, uuid7(), "foreign"), "fixture-token")
    first_structure_uuid, second_structure_uuid = uuid7(), uuid7()
    projection_uuid, invalid_uuid = uuid7(), uuid7()
    foreign_artifact_uuid, mismatched_artifact_uuid = uuid7(), uuid7()
    process_uuid = uuid7()

    async with persistence.transaction() as tx:
        target_execution = await tx.fetchone(
            "SELECT current_root_execution_uuid FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, task_uuid),
        )
        foreign_execution = await tx.fetchone(
            "SELECT current_root_execution_uuid FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
            (team_uuid, foreign_task_uuid),
        )
        assert target_execution is not None and foreign_execution is not None
        execution_uuid = target_execution["current_root_execution_uuid"]
        foreign_execution_uuid = foreign_execution["current_root_execution_uuid"]

        async def insert_artifact(
            artifact_uuid: str,
            artifact_type: str,
            artifact_task_uuid: str,
            artifact_execution_uuid: str,
            *,
            ordinal: int,
            disposition: str = "full_valid",
            created_at: str,
            digest_char: str,
        ) -> None:
            await tx.execute(
                "INSERT INTO mkb_generation_artifacts "
                "(generation_artifact_uuid,team_uuid,artifact_type,artifact_ordinal,task_uuid,execution_uuid,process_uuid,"
                "process_attempt,process_fence,logical_handle,media_type,size_bytes,digest_algorithm,content_digest,"
                "validation_disposition,validation_report_ref,validation_report_digest,proof_ref,proof_digest,"
                "repair_causation_ref,created_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    artifact_uuid,
                    team_uuid,
                    artifact_type,
                    ordinal,
                    artifact_task_uuid,
                    artifact_execution_uuid,
                    process_uuid,
                    7,
                    "f" * 64,
                    f"mkbobj:v1:{artifact_uuid}",
                    "application/json",
                    ordinal + 1,
                    "sha256",
                    digest_char * 64,
                    disposition,
                    f"mkbvalidation:v1:{artifact_uuid}",
                    "d" * 64,
                    f"mkbproof:v1:{artifact_uuid}",
                    "e" * 64,
                    "mkbrepair:v1:internal-only",
                    created_at,
                    '{"internal":"never-public"}',
                ),
            )

        await insert_artifact(
            first_structure_uuid,
            "structure_document",
            task_uuid,
            execution_uuid,
            ordinal=0,
            created_at="2026-08-12T00:00:01Z",
            digest_char="a",
        )
        await insert_artifact(
            second_structure_uuid,
            "structure_document",
            task_uuid,
            execution_uuid,
            ordinal=1,
            created_at="2026-08-12T00:00:02Z",
            digest_char="b",
        )
        await insert_artifact(
            projection_uuid,
            "retrieval_block_projection",
            task_uuid,
            execution_uuid,
            ordinal=0,
            created_at="2026-08-12T00:00:03Z",
            digest_char="c",
        )
        await insert_artifact(
            invalid_uuid,
            "structure_validation_report",
            task_uuid,
            execution_uuid,
            ordinal=0,
            disposition="invalid",
            created_at="2026-08-12T00:00:04Z",
            digest_char="d",
        )
        await insert_artifact(
            foreign_artifact_uuid,
            "structure_document",
            foreign_task_uuid,
            foreign_execution_uuid,
            ordinal=0,
            created_at="2026-08-12T00:00:05Z",
            digest_char="e",
        )
        # The schema's separate Task and Execution foreign keys permit this
        # malformed pair.  The read API must still reject it by joining the
        # artifact through an Execution belonging to the requested Task.
        await insert_artifact(
            mismatched_artifact_uuid,
            "structure_document",
            task_uuid,
            foreign_execution_uuid,
            ordinal=2,
            created_at="2026-08-12T00:00:06Z",
            digest_char="f",
        )
        for artifact_type, artifact_uuid, updated_at in (
            ("structure_document", second_structure_uuid, "2026-08-12T01:00:01Z"),
            ("retrieval_block_projection", projection_uuid, "2026-08-12T01:00:02Z"),
            ("structure_validation_report", invalid_uuid, "2026-08-12T01:00:00Z"),
        ):
            await tx.execute(
                "INSERT INTO mkb_generation_pointers "
                "(team_uuid,execution_uuid,artifact_type,current_generation_artifact_uuid,pointer_revision,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?)",
                (team_uuid, execution_uuid, artifact_type, artifact_uuid, 3, updated_at, '{"internal":"never-public"}'),
            )
        await tx.execute(
            "UPDATE mkb_tasks SET deleted_at=? WHERE team_uuid=? AND task_uuid=?",
            ("2026-08-12T02:00:00Z", team_uuid, foreign_task_uuid),
        )
        await tx.execute("DELETE FROM mkb_outbox")
    await persistence.close()
    return Seed(
        team_uuid=team_uuid,
        task_uuid=task_uuid,
        foreign_task_uuid=foreign_task_uuid,
        execution_uuid=execution_uuid,
        foreign_execution_uuid=foreign_execution_uuid,
        process_uuid=process_uuid,
        first_structure_uuid=first_structure_uuid,
        second_structure_uuid=second_structure_uuid,
        projection_uuid=projection_uuid,
        invalid_uuid=invalid_uuid,
        foreign_artifact_uuid=foreign_artifact_uuid,
        mismatched_artifact_uuid=mismatched_artifact_uuid,
    )


def _client(tmp_path: Path) -> TestClient:
    return TestClient(
        create_app(
            Settings(
                internal_token="generation-artifact-contract-token",
                database_path=tmp_path / "generation-artifacts.sqlite3",
                object_root=tmp_path / "objects",
                persistence_backend="sqlite",
                concurrent_writes_required=False,
                native_vector_required=False,
                inference_probe_enabled=False,
                rate_limit_ip_per_min=1_000,
                rate_limit_token_per_min=1_000,
            )
        ),
        raise_server_exceptions=True,
    )


def test_generation_artifact_reads_are_task_scoped_typed_and_non_leaking(tmp_path: Path) -> None:
    seed = asyncio.run(_seed(tmp_path))
    client = _client(tmp_path)
    headers = {"Authorization": "Bearer generation-artifact-contract-token"}
    root = f"/v1/teams/{seed.team_uuid}/tasks/{seed.task_uuid}"
    try:
        first_page = client.get(f"{root}/generation-artifacts?artifact_type=structure_document&limit=1", headers=headers)
        assert first_page.status_code == 200
        first_payload = first_page.json()
        assert [item["generation_artifact_uuid"] for item in first_payload["items"]] == [seed.second_structure_uuid]
        assert first_payload["next_cursor"]
        first_item = first_payload["items"][0]
        assert first_item["task_generation"] == 1
        assert first_item["links"] == {
            "self": f"{root}/generation-artifacts/{seed.second_structure_uuid}",
            "task": root,
        }
        assert {
            "execution_uuid",
            "process_uuid",
            "process_attempt",
            "process_fence",
            "stored_object_uuid",
            "repair_causation_ref",
            "payload_extra",
        }.isdisjoint(first_item)
        rendered = json.dumps(first_payload, sort_keys=True)
        assert seed.execution_uuid not in rendered
        assert seed.foreign_execution_uuid not in rendered
        assert seed.process_uuid not in rendered
        assert "internal-only" not in rendered
        artifact_cursor = _cursor_payload(first_payload["next_cursor"])
        assert set(artifact_cursor) == {"kind", "filter_digest", "created_at", "generation_artifact_uuid"}
        assert seed.execution_uuid not in json.dumps(artifact_cursor, sort_keys=True)

        second_page = client.get(
            f"{root}/generation-artifacts?artifact_type=structure_document&limit=1&cursor={first_payload['next_cursor']}",
            headers=headers,
        )
        assert second_page.status_code == 200
        assert [item["generation_artifact_uuid"] for item in second_page.json()["items"]] == [seed.first_structure_uuid]

        bound_cursor = client.get(
            f"{root}/generation-artifacts?artifact_type=retrieval_block_projection&cursor={first_payload['next_cursor']}",
            headers=headers,
        )
        assert bound_cursor.status_code == 422
        assert bound_cursor.json()["error"]["code"] == "cursor-invalid"
        invalid_filter = client.get(f"{root}/generation-artifacts?artifact_type=unknown", headers=headers)
        assert invalid_filter.status_code == 422
        assert invalid_filter.json()["error"]["code"] == "generation-artifact-type-invalid"

        detail = client.get(f"{root}/generation-artifacts/{seed.invalid_uuid}", headers=headers)
        assert detail.status_code == 200
        assert detail.json()["validation_disposition"] == "invalid"
        for artifact_uuid in (seed.foreign_artifact_uuid, seed.mismatched_artifact_uuid):
            denied = client.get(f"{root}/generation-artifacts/{artifact_uuid}", headers=headers)
            assert denied.status_code == 404
            assert denied.json()["error"]["code"] == "generation-artifact-not-found"
        deleted_task = client.get(
            f"/v1/teams/{seed.team_uuid}/tasks/{seed.foreign_task_uuid}/generation-artifacts",
            headers=headers,
        )
        assert deleted_task.status_code == 410
        assert deleted_task.json()["error"]["code"] == "task-deleted"

        pointers = client.get(f"{root}/generation-artifact-pointers?limit=1", headers=headers)
        assert pointers.status_code == 200
        pointer_payload = pointers.json()
        assert pointer_payload["next_cursor"]
        pointer = pointer_payload["items"][0]
        assert pointer["artifact_type"] == "retrieval_block_projection"
        assert pointer["current_generation_artifact_uuid"] == seed.projection_uuid
        assert pointer["validation_disposition"] == "full_valid"
        assert {
            "execution_uuid",
            "process_uuid",
            "pointer_execution_uuid",
            "payload_extra",
        }.isdisjoint(pointer)
        rendered_pointers = json.dumps(pointer_payload, sort_keys=True)
        assert seed.execution_uuid not in rendered_pointers
        assert seed.process_uuid not in rendered_pointers
        pointer_cursor = _cursor_payload(pointer_payload["next_cursor"])
        assert set(pointer_cursor) == {"kind", "filter_digest", "updated_at", "current_generation_artifact_uuid"}
        assert seed.execution_uuid not in json.dumps(pointer_cursor, sort_keys=True)

        pointer_page_two = client.get(
            f"{root}/generation-artifact-pointers?limit=1&cursor={pointer_payload['next_cursor']}",
            headers=headers,
        )
        assert pointer_page_two.status_code == 200
        assert pointer_page_two.json()["items"][0]["current_generation_artifact_uuid"] == seed.second_structure_uuid
        pointer_cursor_mismatch = client.get(
            f"{root}/generation-artifact-pointers?artifact_type=structure_document&cursor={pointer_payload['next_cursor']}",
            headers=headers,
        )
        assert pointer_cursor_mismatch.status_code == 422
        assert pointer_cursor_mismatch.json()["error"]["code"] == "cursor-invalid"
        invalid_pointer = client.get(
            f"{root}/generation-artifact-pointers?artifact_type=structure_validation_report",
            headers=headers,
        )
        assert invalid_pointer.status_code == 409
        assert invalid_pointer.json()["error"]["code"] == "generation-pointer-invalid"

        no_write_surface = client.post(f"{root}/generation-artifacts", headers=headers, json={})
        assert no_write_surface.status_code == 405
    finally:
        client.close()
        asyncio.run(client.app.state.container.persistence.close())
