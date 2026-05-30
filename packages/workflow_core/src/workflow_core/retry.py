from sqlite3 import Connection

from ._utils import now_iso
from .events import append_audit_log, append_workflow_event


def succeed_claim(conn: Connection, claim_token: str) -> bool:
    claim = conn.execute(
        "SELECT * FROM task_claims WHERE claim_token = ? AND status = 'active'",
        (claim_token,),
    ).fetchone()
    if not claim:
        return False
    now = now_iso()
    conn.execute(
        "UPDATE task_claims SET status='finished', finished_at=? WHERE id=?",
        (now, claim["id"]),
    )
    conn.execute(
        """
        UPDATE workflow_steps
        SET status='succeeded', finished_at=?, updated_at=?
        WHERE id=?
        """,
        (now, now, claim["step_id"]),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO step_attempts (
            id, team_id, workflow_run_id, step_id, claim_id, attempt_number,
            termination_reason, retryable, started_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'success', 0, ?, ?)
        """,
        (
            f"attempt_{claim['id']}",
            claim["team_id"],
            claim["workflow_run_id"],
            claim["step_id"],
            claim["id"],
            claim["attempt_number"],
            claim["claimed_at"],
            now,
        ),
    )
    append_workflow_event(
        conn,
        team_id=claim["team_id"],
        workflow_run_id=claim["workflow_run_id"],
        step_id=claim["step_id"],
        event_type="step.succeeded",
        emitted_by="worker",
        payload={"claim_id": claim["id"], "attempt_number": claim["attempt_number"]},
    )
    append_audit_log(
        conn,
        team_id=claim["team_id"],
        actor_type="worker",
        actor_id=claim["worker_id"],
        action="step.succeeded",
        target_type="workflow_step",
        target_id=claim["step_id"],
        payload={"claim_id": claim["id"], "attempt_number": claim["attempt_number"]},
    )
    conn.commit()
    return True


def fail_claim(
    conn: Connection,
    claim_token: str,
    *,
    error_code: str = "EXECUTOR_FAILURE",
    error_message: str = "executor failed",
    retry_backoff_seconds: int = 1,
) -> bool:
    claim = conn.execute(
        """
        SELECT tc.*, ws.attempt_count, ws.max_attempts
        FROM task_claims tc
        JOIN workflow_steps ws ON ws.id = tc.step_id
        WHERE tc.claim_token = ? AND tc.status = 'active'
        """,
        (claim_token,),
    ).fetchone()
    if not claim:
        return False
    now = now_iso()
    retryable = 1 if claim["attempt_count"] < claim["max_attempts"] else 0
    next_status = "retry_wait" if retryable else "failed"
    conn.execute(
        "UPDATE task_claims SET status='finished', finished_at=? WHERE id=?",
        (now, claim["id"]),
    )
    conn.execute(
        """
        UPDATE workflow_steps
        SET status=?,
            available_at=CASE WHEN ? = 1
                THEN strftime('%Y-%m-%dT%H:%M:%fZ', 'now', '+' || ? || ' seconds')
                ELSE available_at END,
            error_code=?,
            error_message=?,
            updated_at=?,
            finished_at=CASE WHEN ? = 1 THEN NULL ELSE ? END
        WHERE id=?
        """,
        (
            next_status,
            retryable,
            retry_backoff_seconds,
            error_code,
            error_message,
            now,
            retryable,
            now,
            claim["step_id"],
        ),
    )
    conn.execute(
        """
        INSERT OR REPLACE INTO step_attempts (
            id, team_id, workflow_run_id, step_id, claim_id, attempt_number,
            termination_reason, retryable, error_code, error_message, started_at, finished_at
        ) VALUES (?, ?, ?, ?, ?, ?, 'executor_failure', ?, ?, ?, ?, ?)
        """,
        (
            f"attempt_{claim['id']}",
            claim["team_id"],
            claim["workflow_run_id"],
            claim["step_id"],
            claim["id"],
            claim["attempt_number"],
            retryable,
            error_code,
            error_message,
            claim["claimed_at"],
            now,
        ),
    )
    append_workflow_event(
        conn,
        team_id=claim["team_id"],
        workflow_run_id=claim["workflow_run_id"],
        step_id=claim["step_id"],
        event_type="step.retry_scheduled" if retryable else "step.failed",
        emitted_by="worker",
        payload={
            "claim_id": claim["id"],
            "attempt_number": claim["attempt_number"],
            "error_code": error_code,
        },
    )
    append_audit_log(
        conn,
        team_id=claim["team_id"],
        actor_type="worker",
        actor_id=claim["worker_id"],
        action="step.retry_scheduled" if retryable else "step.failed",
        target_type="workflow_step",
        target_id=claim["step_id"],
        payload={
            "claim_id": claim["id"],
            "attempt_number": claim["attempt_number"],
            "error_code": error_code,
        },
    )
    conn.commit()
    return True
