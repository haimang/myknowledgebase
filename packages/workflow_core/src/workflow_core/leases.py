from sqlite3 import Connection

from ._utils import add_seconds_iso, now_iso
from .events import append_audit_log, append_workflow_event


def heartbeat_claim(conn: Connection, claim_token: str, *, lease_seconds: int = 60) -> bool:
    row = conn.execute(
        "SELECT id FROM task_claims WHERE claim_token = ? AND status = 'active'",
        (claim_token,),
    ).fetchone()
    if not row:
        return False
    now = now_iso()
    conn.execute(
        """
        UPDATE task_claims
        SET last_heartbeat_at = ?, lease_expires_at = ?
        WHERE claim_token = ? AND status = 'active'
        """,
        (now, add_seconds_iso(lease_seconds), claim_token),
    )
    conn.commit()
    return True


def reap_expired_claims(conn: Connection) -> int:
    claims = conn.execute(
        """
        SELECT tc.*, ws.attempt_count, ws.max_attempts
        FROM task_claims tc
        JOIN workflow_steps ws ON ws.id = tc.step_id
        WHERE tc.status = 'active'
          AND tc.lease_expires_at <= strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
        """
    ).fetchall()
    reaped = 0
    for claim in claims:
        now = now_iso()
        retryable = 1 if claim["attempt_count"] < claim["max_attempts"] else 0
        next_status = "retry_wait" if retryable else "failed"
        conn.execute(
            """
            UPDATE task_claims
            SET status='expired', finished_at=?
            WHERE id=?
            """,
            (now, claim["id"]),
        )
        conn.execute(
            """
            INSERT OR REPLACE INTO step_attempts (
                id, team_id, workflow_run_id, step_id, claim_id, attempt_number,
                termination_reason, retryable, error_code, error_message, started_at, finished_at
            ) VALUES (
                ?, ?, ?, ?, ?, ?, 'lease_timeout', ?, 'LEASE_TIMEOUT', 'claim expired', ?, ?
            )
            """,
            (
                f"attempt_{claim['id']}",
                claim["team_id"],
                claim["workflow_run_id"],
                claim["step_id"],
                claim["id"],
                claim["attempt_number"],
                retryable,
                claim["claimed_at"],
                now,
            ),
        )
        conn.execute(
            """
            UPDATE workflow_steps
            SET status = ?,
                available_at = CASE WHEN ? = 1
                    THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                    ELSE available_at END,
                error_code='LEASE_TIMEOUT',
                error_message='claim expired without heartbeat',
                updated_at=?
            WHERE id = ?
            """,
            (next_status, retryable, now, claim["step_id"]),
        )
        append_workflow_event(
            conn,
            team_id=claim["team_id"],
            workflow_run_id=claim["workflow_run_id"],
            step_id=claim["step_id"],
            event_type="step.lease_expired",
            emitted_by="system",
            payload={"claim_id": claim["id"], "attempt_number": claim["attempt_number"]},
        )
        append_audit_log(
            conn,
            team_id=claim["team_id"],
            actor_type="system",
            actor_id=None,
            action="step.lease_expired",
            target_type="workflow_step",
            target_id=claim["step_id"],
            payload={"claim_id": claim["id"], "attempt_number": claim["attempt_number"]},
        )
        reaped += 1
    conn.commit()
    return reaped
