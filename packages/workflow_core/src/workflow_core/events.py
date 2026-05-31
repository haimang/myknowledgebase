from __future__ import annotations

import json
from sqlite3 import Connection

from smind_common.time import utc_now_iso as now_iso

from ._utils import new_id


def append_workflow_event(
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
          id, team_id, workflow_run_id, step_id, event_type, event_payload_json,
          emitted_by, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("event"),
            team_id,
            workflow_run_id,
            step_id,
            event_type,
            json.dumps(payload or {}),
            emitted_by,
            now_iso(),
        ),
    )


def append_audit_log(
    conn: Connection,
    *,
    team_id: str | None,
    actor_type: str,
    actor_id: str | None,
    action: str,
    target_type: str,
    target_id: str | None,
    payload: dict | None = None,
) -> None:
    conn.execute(
        """
        INSERT INTO audit_logs (
          id, team_id, actor_type, actor_id, action, target_type, target_id,
          payload_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            new_id("audit"),
            team_id,
            actor_type,
            actor_id,
            action,
            target_type,
            target_id,
            json.dumps(payload or {}),
        ),
    )
