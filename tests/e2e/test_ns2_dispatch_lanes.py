"""NS2-T60/T62: four-lane dispatch is visible on mkb_processes rows."""

from __future__ import annotations

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
        internal_token="ns2-e2e-token",
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


def _task_body(team_uuid: str, task_uuid: str, *, priority: str, key: str) -> dict[str, object]:
    trace_uuid = uuid7()
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "priority": priority,
        "payload": {
            "json_prompt_id": "promptB.json.generic",
            "source": {
                "source_kind": "inline_payload",
                "external_key": key,
                "content": (
                    "First paragraph carries enough distinct source material. "
                    "Second paragraph keeps the stub pipeline deterministic."
                ),
            },
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "ns2-e2e",
            "created_at": utc_now(),
        },
    }


def _wait_for_generate_rows(
    database_path: Path,
    team_uuid: str,
    task_uuid: str,
    *,
    expect_admit: bool,
    timeout: float = 8.0,
) -> list[sqlite3.Row]:
    deadline = time.monotonic() + timeout
    last: list[sqlite3.Row] = []
    while time.monotonic() < deadline:
        with sqlite3.connect(database_path) as connection:
            connection.row_factory = sqlite3.Row
            last = list(
                connection.execute(
                    "SELECT process_key, dispatch_pool, dispatch_admitted, status "
                    "FROM mkb_processes WHERE team_uuid=? AND task_uuid=? "
                    "AND process_key IN ('lsrag.construct','lsrag.structurize','lsrag.transcribe_markdown') "
                    "ORDER BY created_at",
                    (team_uuid, task_uuid),
                )
            )
            if last and (not expect_admit or any(row["dispatch_admitted"] == 1 for row in last)):
                return last
        time.sleep(0.05)
    raise AssertionError(f"generate processes not ready for {task_uuid}: { [dict(row) for row in last] }")


def test_four_priority_lanes_are_visible_on_process_rows(tmp_path: Path) -> None:
    # NS2-T60: offline stub still exposes the frozen lane on durable process rows
    settings = _settings(tmp_path)
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer ns2-e2e-token"}
    app = create_app(settings)
    lanes = {
        "urgent": uuid7(),
        "high": uuid7(),
        "normal": uuid7(),
        "low": uuid7(),
    }

    with TestClient(app, raise_server_exceptions=True) as client:
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "ns2-lanes"},
        )
        assert team.status_code == 201, team.text
        for priority, task_uuid in lanes.items():
            response = client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=headers,
                json=_task_body(team_uuid, task_uuid, priority=priority, key=f"ns2-{priority}"),
            )
            assert response.status_code == 201, response.text

        for priority, task_uuid in lanes.items():
            rows = _wait_for_generate_rows(
                settings.resolved_database_path,
                team_uuid,
                task_uuid,
                expect_admit=priority != "low",
            )
            pools = {row["dispatch_pool"] for row in rows}
            if priority in {"urgent", "high", "normal"}:
                assert "non-interactive" in pools
                assert any(row["dispatch_admitted"] == 1 for row in rows)
            else:
                assert "non-interactive" not in pools
                assert all(row["dispatch_admitted"] == 0 for row in rows)

    # NS2-T62: offline vectorize is unpooled and must not occupy embed
    with sqlite3.connect(settings.resolved_database_path) as connection:
        connection.row_factory = sqlite3.Row
        vectorize = list(
            connection.execute(
                "SELECT dispatch_pool, dispatch_admitted FROM mkb_processes "
                "WHERE team_uuid=? AND process_key='lsrag.vectorize'",
                (team_uuid,),
            )
        )
        for row in vectorize:
            assert row["dispatch_pool"] is None
