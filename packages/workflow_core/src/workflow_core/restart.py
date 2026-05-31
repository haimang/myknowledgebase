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
        updated_at = now_iso()
        conn.execute(
            """
            INSERT INTO workflow_steps(
              id, team_id, workflow_run_id, step_key, stage, action, payload_json, status
            ) VALUES (?, ?, ?, ?, 'clean', 'clean.start', ?, 'pending')
            ON CONFLICT(workflow_run_id, step_key) DO UPDATE
              SET status='pending',
                  available_at=?,
                  updated_at=?
            """,
            (
                f"restart_step_{run['id']}",
                run["team_id"],
                run["id"],
                "clean:init",
                json.dumps({"source_id": run["source_id"], "document_id": run["document_id"]}),
                updated_at,
                updated_at,
            ),
        )
        conn.execute(
            """
            UPDATE workflow_runs
            SET status='pending', current_stage='clean', updated_at=?
            WHERE id = ?
            """,
            (updated_at, run["id"]),
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
        step_row = conn.execute(
            """
            SELECT id
            FROM workflow_steps
            WHERE workflow_run_id = ? AND step_key = 'clean:init'
            LIMIT 1
            """,
            (run["id"],),
        ).fetchone()
        append_workflow_event(
            conn,
            team_id=run["team_id"],
            workflow_run_id=run["id"],
            step_id=step_row["id"] if step_row is not None else None,
            event_type="workflow.restarted",
            emitted_by="system",
            payload={"request_id": req["id"], "mode": req["mode"]},
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
