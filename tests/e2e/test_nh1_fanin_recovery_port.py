"""NH1-T02: fan-in crash recovery is observed through PersistencePort."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from tests.e2e.test_registered_api_scatter import (
    _create_team,
    _records,
    _settings,
    _submit,
    _wait_for_terminal,
)


def test_fanin_recovery_uses_application_port_and_finishes_once(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer scatter-token"}
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))

    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=headers)
        task_uuid = _submit(client, team_uuid=team_uuid, headers=headers, records=_records("nh1-port-repair"))
        initial = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
        assert initial["status"] == "succeeded", initial
        assert initial["proof_ref"]

        persistence = app.state.container.persistence

        async def inject_after_children_terminal() -> None:
            async with persistence.transaction() as tx:
                root = await tx.fetchone(
                    "SELECT execution_uuid FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
                    "AND parent_execution_uuid IS NULL",
                    (team_uuid, task_uuid),
                )
                task = await tx.fetchone(
                    "SELECT change_set_uuid FROM mkb_tasks WHERE team_uuid=? AND task_uuid=?",
                    (team_uuid, task_uuid),
                )
                assert root is not None and task is not None
                await tx.execute(
                    "UPDATE mkb_tasks SET status='running',completed_at=NULL,error_code=NULL,error_message=NULL "
                    "WHERE team_uuid=? AND task_uuid=?",
                    (team_uuid, task_uuid),
                )
                await tx.execute(
                    "UPDATE mkb_executions SET status='waiting',waiting_reason='scatter_children',waiting_ref=?,"
                    "completed_at=NULL,summary_completed_at=NULL WHERE execution_uuid=?",
                    (task["change_set_uuid"], root["execution_uuid"]),
                )

        client.portal.call(inject_after_children_terminal)
        repaired = _wait_for_terminal(client, team_uuid=team_uuid, task_uuid=task_uuid, headers=headers)
        assert repaired["status"] == "succeeded", repaired
        assert repaired["proof_ref"] == initial["proof_ref"]

        async def inspect_repaired_root() -> tuple[dict[str, Any], int]:
            async with persistence.transaction() as tx:
                root = await tx.fetchone(
                    "SELECT status,publication_proof_ref,terminal_summary_digest,summary_completed_at "
                    "FROM mkb_executions WHERE team_uuid=? AND task_uuid=? AND parent_execution_uuid IS NULL",
                    (team_uuid, task_uuid),
                )
                count = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
                    "AND parent_execution_uuid IS NULL",
                    (team_uuid, task_uuid),
                )
            assert root is not None and count is not None
            return root, int(count["count"])

        root, root_count = client.portal.call(inspect_repaired_root)
        assert root_count == 1
        assert root["status"] == "succeeded"
        assert root["publication_proof_ref"] == repaired["proof_ref"]
        assert root["terminal_summary_digest"]
        assert root["summary_completed_at"]


def test_nh1_recovery_files_forbid_driver_bypass() -> None:
    forbidden = ("import " + "sqlite3", "sqlite3" + ".connect")
    for path in (
        Path("tests/e2e/test_registered_api_scatter.py"),
        Path("tests/e2e/test_nh1_fanin_recovery_port.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert all(token not in source for token in forbidden)
