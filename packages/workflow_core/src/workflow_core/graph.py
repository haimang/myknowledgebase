from __future__ import annotations

import json
from sqlite3 import Connection

from ._utils import new_id


def write_workflow_event(
    conn: Connection,
    *,
    team_id: str,
    workflow_run_id: str,
    step_id: str | None,
    event_type: str,
    emitted_by: str,
    payload: dict | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO workflow_events (
            id, team_id, workflow_run_id, step_id, event_type, event_payload_json, emitted_by
        ) VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("event"),
            team_id,
            workflow_run_id,
            step_id,
            event_type,
            json.dumps(payload or {}),
            emitted_by,
        ),
    )
    conn.commit()
