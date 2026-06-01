from __future__ import annotations

from sqlite3 import Connection
from typing import Protocol

from storage_sqlite.repositories.requests import PurgeRequestRepository
from vector_sqlite_vec import VectorStore

from smind_common.time import utc_now_iso as now_iso
from .events import append_audit_log, append_workflow_event


class _ObjectStore(Protocol):
    def delete(self, object_key: str) -> None: ...


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


def process_purge_requests(
    conn: Connection,
    vec_conn: Connection | None,
    object_store: _ObjectStore | None = None,
) -> int:
    # Whole batch wrapped in one BEGIN IMMEDIATE on the core connection
    # (autocommit; F1-04 batch boundary). NOTE (CR-4 R5/R12): the cross-DB
    # vec write via ``VectorStore(vec_conn).delete_chunks`` AND the object_store
    # deletes (F4-05) are SEPARATE substrates, NOT covered by this core
    # transaction — F1 guarantees core-side atomicity only; vec/object
    # reconciliation is out of scope here.
    conn.execute("BEGIN IMMEDIATE")
    try:
        return _process_purge_requests_body(conn, vec_conn, object_store)
    except Exception:
        conn.rollback()
        raise


def _collect_object_keys(conn: Connection, *, document_id: str, team_id: str) -> list[str]:
    """F4-05 合规清退: 收集被 purge 文档名下所有落 object_store 的 object_key。

    覆盖 raw 上传 (uploads, 经 source→document)、静态文件 (static_files) 与
    chunk 正文等产物 (artifacts, storage_backend='object_store')。AP §4.3 字面
    枚举 uploads/static_files; 此处据 §0「正文不残留磁盘」目标纳入 artifacts
    (rag 把 chunk_text 经 put_text 落盘, 见 workflow_rag/service.py:115)。
    """
    keys: list[str] = []
    rows = conn.execute(
        """
        SELECT u.object_key AS k
        FROM uploads u
        JOIN sources s ON s.upload_id = u.id
        JOIN documents d ON d.source_id = s.id
        WHERE d.id = ? AND d.team_id = ?
        UNION
        SELECT object_key AS k FROM static_files
        WHERE document_id = ? AND team_id = ?
        UNION
        SELECT object_key AS k FROM artifacts
        WHERE document_id = ? AND team_id = ?
          AND storage_backend = 'object_store'
        """,
        (document_id, team_id, document_id, team_id, document_id, team_id),
    ).fetchall()
    for row in rows:
        if row["k"]:
            keys.append(row["k"])
    return keys


def _process_purge_requests_body(
    conn: Connection,
    vec_conn: Connection | None,
    object_store: _ObjectStore | None = None,
) -> int:
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
        if object_store is not None:
            # F4-05 合规清退: 删被 purge 文档名下的 object_store 对象。delete 经
            # _resolve_safe 校验且缺失幂等; 真实删除失败 fail-loud (异常上抛触发
            # 整批 rollback, 不静默吞——⛔6)。NOT covered by core tx (FS substrate)。
            object_keys = _collect_object_keys(
                conn, document_id=target_document_id, team_id=req["team_id"]
            )
            for object_key in object_keys:
                object_store.delete(object_key)
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
