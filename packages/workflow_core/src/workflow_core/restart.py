from __future__ import annotations

import json
from sqlite3 import Connection

from storage_sqlite.repositories.requests import RestartRequestRepository

from smind_common.time import utc_now_iso as now_iso
from .events import append_audit_log, append_workflow_event


def create_restart_request(
    conn_or_repo: Connection | RestartRequestRepository,
    **kwargs: str,
) -> None:
    repo = (
        conn_or_repo
        if isinstance(conn_or_repo, RestartRequestRepository)
        else RestartRequestRepository(conn_or_repo)
    )
    repo.create(
        request_id=kwargs["request_id"],
        team_id=kwargs["team_id"],
        workflow_run_id=kwargs["workflow_run_id"],
        mode=kwargs.get("mode", "recovery"),
    )


def process_restart_requests(conn: Connection) -> int:
    # Whole batch wrapped in one BEGIN IMMEDIATE (autocommit; F1-04 batch
    # boundary — keeps existing single-transaction semantics under autocommit).
    conn.execute("BEGIN IMMEDIATE")
    try:
        return _process_restart_requests_body(conn)
    except Exception:
        conn.rollback()
        raise


def _process_restart_requests_body(conn: Connection) -> int:
    requests = conn.execute(
        "SELECT * FROM restart_requests WHERE status = 'pending' ORDER BY created_at ASC"
    ).fetchall()
    count = 0
    for req in requests:
        started_at = now_iso()
        conn.execute(
            """
            UPDATE restart_requests
            SET status='processing', started_at=?
            WHERE id = ?
            """,
            (started_at, req["id"]),
        )
        run = conn.execute(
            "SELECT * FROM workflow_runs WHERE id = ?",
            (req["workflow_run_id"],),
        ).fetchone()
        if run is None:
            completed_at = now_iso()
            conn.execute(
                """
                UPDATE restart_requests
                SET status='failed',
                    error_message='workflow not found',
                    completed_at=?
                WHERE id = ?
                """,
                (completed_at, req["id"]),
            )
            append_audit_log(
                conn,
                team_id=req["team_id"],
                actor_type="system",
                actor_id=None,
                action="restart.failed",
                target_type="workflow_run",
                target_id=req["workflow_run_id"],
                payload={"request_id": req["id"], "reason": "workflow not found"},
            )
            continue
        mode = req["mode"] or "recovery"
        # [Q4] recovery only this round; force/kickstart explicitly deferred.
        if mode not in ("recovery",):
            completed_at = now_iso()
            conn.execute(
                """
                UPDATE restart_requests
                SET status='failed',
                    error_message='mode not supported this round (only recovery)',
                    completed_at=?
                WHERE id = ?
                """,
                (completed_at, req["id"]),
            )
            append_audit_log(
                conn,
                team_id=req["team_id"],
                actor_type="system",
                actor_id=None,
                action="restart.failed",
                target_type="workflow_run",
                target_id=req["workflow_run_id"],
                payload={"request_id": req["id"], "reason": f"mode {mode} deferred"},
            )
            continue

        # F3-05: recovery anchors on the last failed/retry_wait step's stage
        # (else the run's current_stage), instead of always re-running from
        # clean head. Only the failed work is reset, not already-succeeded steps.
        failed = conn.execute(
            """
            SELECT id, stage FROM workflow_steps
            WHERE workflow_run_id = ? AND status IN ('failed', 'retry_wait')
            ORDER BY updated_at DESC LIMIT 1
            """,
            (run["id"],),
        ).fetchone()
        anchor_stage = failed["stage"] if failed else (run["current_stage"] or "clean")
        # F3-04: available_at written via SQL strftime so the reset step is
        # confirmed ready (same expression as v_ready_steps).
        reset = conn.execute(
            """
            UPDATE workflow_steps
            SET status='pending',
                available_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now'),
                error_code=NULL,
                error_message=NULL,
                updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE workflow_run_id = ? AND status IN ('failed', 'retry_wait')
            """,
            (run["id"],),
        ).rowcount
        if reset:
            conn.execute(
                """
                UPDATE workflow_runs
                SET status='running', current_stage=?,
                    updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
                WHERE id = ?
                """,
                (anchor_stage, run["id"]),
            )
        completed_at = now_iso()
        conn.execute(
            """
            UPDATE restart_requests
            SET status='completed', completed_at=?
            WHERE id = ?
            """,
            (completed_at, req["id"]),
        )
        anchor_step_row = conn.execute(
            """
            SELECT id FROM workflow_steps
            WHERE workflow_run_id = ? AND stage = ?
            ORDER BY updated_at DESC LIMIT 1
            """,
            (run["id"], anchor_stage),
        ).fetchone()
        append_workflow_event(
            conn,
            team_id=run["team_id"],
            workflow_run_id=run["id"],
            step_id=anchor_step_row["id"] if anchor_step_row is not None else None,
            event_type="workflow.restarted",
            emitted_by="system",
            payload={
                "request_id": req["id"],
                "mode": mode,
                "anchor_stage": anchor_stage,
                "reset_steps": reset,
            },
        )
        append_audit_log(
            conn,
            team_id=run["team_id"],
            actor_type="system",
            actor_id=None,
            action="restart.completed",
            target_type="workflow_run",
            target_id=run["id"],
            payload={"request_id": req["id"], "mode": req["mode"]},
        )
        count += 1
    conn.commit()
    return count
