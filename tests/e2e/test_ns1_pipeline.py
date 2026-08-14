"""NS1-T41/T42: local stub journeys for the optional Markdown hop."""

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


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="ns1-e2e-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        persistence_backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
        inference_probe_enabled=False,
        live_inference=False,
        rate_limit_ip_per_min=1_000,
        rate_limit_token_per_min=2_000,
    )


def _task_body(team_uuid: str, task_uuid: str, *, markdown: bool) -> dict[str, object]:
    prompt_payload: dict[str, object] = {
        "json_prompt_id": "promptB.json.legal" if markdown else "promptB.json.generic"
    }
    if markdown:
        prompt_payload["markdown_prompt_id"] = "promptB.markdown.legal"
    prompt_payload["source"] = {
        "source_kind": "inline_payload",
        "external_key": "ns1-with-markdown" if markdown else "ns1-generic",
        "content": (
            "First paragraph carries enough distinct source material. "
            "Second paragraph proves the local layered stub does not duplicate every level."
        ),
    }
    trace_uuid = uuid7()
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": prompt_payload,
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "ns1-e2e",
            "created_at": utc_now(),
        },
    }


def _wait_for_terminal(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 8
    task: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        task = response.json()
        if task["status"] in {"succeeded", "failed", "cancelled"}:
            return task
        time.sleep(0.02)
    raise AssertionError(f"Task did not become terminal: {task}")


def _object_bytes(object_root: Path, team_uuid: str, logical_handle: str) -> bytes:
    digest = logical_handle.rsplit(":", maxsplit=1)[-1]
    return (object_root / "objects" / team_uuid / "sha256" / digest[:2] / digest[2:4] / digest).read_bytes()


def test_stub_pipeline_runs_generic_and_markdown_journeys(tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    team_uuid = uuid7()
    generic_task_uuid = uuid7()
    markdown_task_uuid = uuid7()
    headers = {"Authorization": "Bearer ns1-e2e-token"}
    app = create_app(settings)

    with TestClient(app, raise_server_exceptions=True) as client:
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "ns1-e2e"},
        )
        assert team.status_code == 201, team.text
        for task_uuid, markdown in ((generic_task_uuid, False), (markdown_task_uuid, True)):
            response = client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=headers,
                json=_task_body(team_uuid, task_uuid, markdown=markdown),
            )
            assert response.status_code == 201, response.text
            terminal = _wait_for_terminal(client, team_uuid, task_uuid, headers)
            assert terminal["status"] == "succeeded", terminal

    with sqlite3.connect(settings.resolved_database_path) as connection:
        connection.row_factory = sqlite3.Row
        for task_uuid, markdown in ((generic_task_uuid, False), (markdown_task_uuid, True)):
            steps = [
                row["step_key"]
                for row in connection.execute(
                    "SELECT step_key FROM mkb_processes WHERE team_uuid=? AND task_uuid=? ORDER BY created_at",
                    (team_uuid, task_uuid),
                )
            ]
            assert ("transcribe_markdown" in steps) is markdown
            projection_row = connection.execute(
                "SELECT logical_handle FROM mkb_generation_artifacts "
                "WHERE team_uuid=? AND task_uuid=? AND artifact_type='retrieval_block_projection'",
                (team_uuid, task_uuid),
            ).fetchone()
            assert projection_row is not None
            projection = json.loads(_object_bytes(settings.resolved_object_root, team_uuid, projection_row["logical_handle"]))
            blocks = projection["blocks"]
            expected = {0, 1} if markdown else {0, 1, 2}
            assert {block["granularity"] for block in blocks} == expected
            assert len({block["original"] for block in blocks}) > 1
