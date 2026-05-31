from __future__ import annotations

from sqlite3 import Connection

from storage_sqlite.repositories.requests import PurgeRequestRepository
from vector_sqlite_vec import VectorStore

from smind_common.time import utc_now_iso as now_iso
from .events import append_audit_log, append_workflow_event


def create_purge_request(
    conn_or_repo: Connection | PurgeRequestRepository,
    **kwargs: str,
) -> None:
    repo = (
        conn_or_repo
        if isinstance(conn_or_repo, PurgeRequestRepository)
        else PurgeRequestRepository(conn_or_repo)
    )
    repo.create(
        request_id=kwargs["request_id"],
        team_id=kwargs["team_id"],
        target_kind=kwargs.get("target_kind", "document"),
        target_id=kwargs["target_id"],
    )


def process_purge_requests(conn: Connection, vec_conn: Connection | None) -> int:
    # Whole batch wrapped in one BEGIN IMMEDIATE on the core connection
    # (autocommit; F1-04 batch boundary). NOTE (CR-4 R5/R12): the cross-DB
    # vec write via ``VectorStore(vec_conn).delete_chunks`` is a SEPARATE
    # connection and is NOT covered by this core transaction — F1 guarantees
    # core-side atomicity only; vec reconciliation is out of scope here.
    conn.execute("BEGIN IMMEDIATE")
    try:
        return _process_purge_requests_body(conn, vec_conn)
    except Exception:
        conn.rollback()
        raise


def _process_purge_requests_body(conn: Connection, vec_conn: Connection | None) -> int:
    requests = conn.execute(
        "SELECT * FROM purge_requests WHERE status = 'pending' ORDER BY created_at ASC"
    ).fetchall()
    processed = 0
    for req in requests:
        started_at = now_iso()
        conn.execute(
            """
            UPDATE purge_requests
            SET status='processing', started_at=?
            WHERE id = ?
            """,
            (started_at, req["id"]),
        )
        target_document_id: str | None = None
        if req["target_kind"] == "document":
            target_document_id = req["target_id"]
        elif req["target_kind"] == "workflow_run":
            run = conn.execute(
                "SELECT document_id FROM workflow_runs WHERE id = ? AND team_id = ?",
                (req["target_id"], req["team_id"]),
            ).fetchone()
            target_document_id = run["document_id"] if run else None
        if target_document_id is None:
            completed_at = now_iso()
            conn.execute(
                """
                UPDATE purge_requests
                SET status='failed',
                    error_message='unsupported target',
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
                action="purge.failed",
                target_type=req["target_kind"],
                target_id=req["target_id"],
                payload={"request_id": req["id"], "reason": "unsupported target"},
            )
            continue
        chunk_rows = conn.execute(
            "SELECT id FROM chunks WHERE document_id = ? AND team_id = ?",
            (target_document_id, req["team_id"]),
        ).fetchall()
        chunk_ids = [row["id"] for row in chunk_rows]
        marked_at = now_iso()
        conn.execute(
            """
            UPDATE chunks
            SET vec_status='pending_purge', updated_at=?
            WHERE document_id = ? AND team_id = ?
            """,
            (marked_at, target_document_id, req["team_id"]),
        )
        if vec_conn is not None and chunk_ids:
            # NOT covered by the core BEGIN IMMEDIATE above (separate vec DB).
            VectorStore(vec_conn, workspace_key=req["team_id"]).delete_chunks(chunk_ids)
        purged_at = now_iso()
        conn.execute(
            """
            UPDATE chunks
            SET vec_status='purged', updated_at=?
            WHERE document_id = ? AND team_id = ?
            """,
            (purged_at, target_document_id, req["team_id"]),
        )
        conn.execute(
            """
            UPDATE documents
            SET status='purged', updated_at=?
            WHERE id = ? AND team_id = ?
            """,
            (purged_at, target_document_id, req["team_id"]),
        )
        completed_at = now_iso()
        conn.execute(
            """
            UPDATE purge_requests
            SET status='completed', completed_at=?
            WHERE id = ?
            """,
            (completed_at, req["id"]),
        )
        run_row = conn.execute(
            """
            SELECT id
            FROM workflow_runs
            WHERE document_id = ? AND team_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (target_document_id, req["team_id"]),
        ).fetchone()
        if run_row is not None:
            append_workflow_event(
                conn,
                team_id=req["team_id"],
                workflow_run_id=run_row["id"],
                step_id=None,
                event_type="document.purged",
                emitted_by="system",
                payload={"request_id": req["id"], "document_id": target_document_id},
            )
        append_audit_log(
            conn,
            team_id=req["team_id"],
            actor_type="system",
            actor_id=None,
            action="purge.completed",
            target_type="document",
            target_id=target_document_id,
            payload={"request_id": req["id"], "chunk_count": len(chunk_ids)},
        )
        processed += 1
    conn.commit()
    return processed
