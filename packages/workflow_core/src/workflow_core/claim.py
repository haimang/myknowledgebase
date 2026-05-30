from __future__ import annotations

from sqlite3 import Connection, Row

from ._utils import add_seconds_iso, new_id, now_iso
from .events import append_audit_log, append_workflow_event


def claim_next_step(
    conn: Connection,
    *,
    worker_type: str,
    worker_id: str,
    lease_seconds: int = 60,
) -> Row | None:
    conn.execute("BEGIN IMMEDIATE")
    try:
        row = conn.execute(
            """
            SELECT step_id, team_id, workflow_run_id, attempt_count
            FROM v_ready_steps
            ORDER BY priority ASC, available_at ASC
            LIMIT 1
            """
        ).fetchone()
        if not row:
            conn.commit()
            return None

        step_id = row["step_id"]
        attempt_number = int(row["attempt_count"]) + 1
        claim_id = new_id("claim")
        claim_token = new_id("token")
        now = now_iso()
        conn.execute(
            """
            UPDATE workflow_steps
            SET status='running',
                attempt_count=?,
                started_at=COALESCE(started_at, ?),
                updated_at=?
            WHERE id=?
            """,
            (attempt_number, now, now, step_id),
        )
        conn.execute(
            """
            INSERT INTO task_claims (
                id, team_id, workflow_run_id, step_id, attempt_number,
                claim_token, worker_type, worker_id, status, claimed_at,
                lease_expires_at, last_heartbeat_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active', ?, ?, ?)
            """,
            (
                claim_id,
                row["team_id"],
                row["workflow_run_id"],
                step_id,
                attempt_number,
                claim_token,
                worker_type,
                worker_id,
                now,
                add_seconds_iso(lease_seconds),
                now,
            ),
        )
        append_workflow_event(
            conn,
            team_id=row["team_id"],
            workflow_run_id=row["workflow_run_id"],
            step_id=step_id,
            event_type="step.claimed",
            emitted_by="worker",
            payload={
                "claim_id": claim_id,
                "attempt_number": attempt_number,
                "worker_id": worker_id,
            },
        )
        append_audit_log(
            conn,
            team_id=row["team_id"],
            actor_type="worker",
            actor_id=worker_id,
            action="step.claimed",
            target_type="workflow_step",
            target_id=step_id,
            payload={"claim_id": claim_id, "attempt_number": attempt_number},
        )
        conn.commit()
        return conn.execute("SELECT * FROM task_claims WHERE id = ?", (claim_id,)).fetchone()
    except Exception:
        conn.rollback()
        raise
