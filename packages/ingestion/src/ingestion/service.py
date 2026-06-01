from __future__ import annotations

import json
import os
from sqlite3 import Connection
from uuid import uuid4

from storage_objects import FileSystemObjectStore


def _resolve_action_branch(source_kind: str, source_uri: str) -> str:
    """F6-01 创建侧 branch 派生 (与 workflow_clean._resolve_branch 同规则)。"""
    if source_kind == "url":
        if "chinatax.gov.cn" in (source_uri or ""):
            return "fetch-chinatax-articles"
        return "htmlCrawl"
    return "text"


def _safe_filename(filename: str) -> str:
    """F4-02 纵深防御源头收口: 剥离任何路径分量, 拒绝空 / 含分隔符 / .. 的值。

    控制面为第一道, FileSystemObjectStore._resolve_safe 为最终防线 (part-cr-5 R2)。
    """
    base = os.path.basename(filename or "")
    if not base.strip() or base in (".", "..") or "/" in base or "\\" in base:
        raise ValueError(f"unsafe filename: {filename!r}")
    return base


class IngestionService:
    def __init__(self, conn: Connection, object_store: FileSystemObjectStore) -> None:
        self.conn = conn
        self.object_store = object_store

    def file_initiate(self, team_id: str, user_id: str, filename: str, mime_type: str) -> dict:
        safe_name = _safe_filename(filename)
        upload_id = f"upload_{uuid4().hex}"
        object_key = f"raw/{team_id}/{upload_id}/{safe_name}"
        self.conn.execute(
            """
            INSERT INTO uploads (
                id, team_id, source_kind, object_key, original_filename,
                mime_type, created_by_user_id, status
            ) VALUES (?, ?, 'file', ?, ?, ?, ?, 'initiated')
            """,
            (upload_id, team_id, object_key, safe_name, mime_type, user_id),
        )
        self.conn.commit()
        return {"upload_id": upload_id, "object_key": object_key}

    def static_initiate(self, team_id: str, user_id: str, filename: str, mime_type: str) -> dict:
        upload = self.file_initiate(team_id, user_id, filename, mime_type)
        self.conn.execute(
            "UPDATE uploads SET source_kind='file' WHERE id = ?",
            (upload["upload_id"],),
        )
        self.conn.commit()
        return upload

    def file_confirm(
        self,
        *,
        team_id: str,
        upload_id: str,
        title: str,
        content: str,
        workflow_kind: str = "full",
    ) -> dict:
        upload = self.conn.execute(
            "SELECT * FROM uploads WHERE id = ? AND team_id = ?",
            (upload_id, team_id),
        ).fetchone()
        if not upload:
            raise ValueError("upload not found")
        self.object_store.put_text(upload["object_key"], content)
        self.conn.execute(
            """
            UPDATE uploads
            SET status='confirmed', size_bytes=?, updated_at=strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id=?
            """,
            (len(content.encode("utf-8")), upload_id),
        )
        source_id = f"source_{uuid4().hex}"
        document_id = f"doc_{uuid4().hex}"
        self.conn.execute(
            """
            INSERT INTO sources (id, team_id, upload_id, source_kind, source_uri, title, mime_type)
            VALUES (?, ?, ?, 'file', ?, ?, ?)
            """,
            (source_id, team_id, upload_id, upload["object_key"], title, upload["mime_type"]),
        )
        self.conn.execute(
            """
            INSERT INTO documents (id, team_id, source_id, canonical_uri, title)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, team_id, source_id, upload["object_key"], title),
        )
        run_id = self._create_workflow_run(
            team_id, source_id, document_id, workflow_kind, source_kind="file"
        )
        self.conn.commit()
        return {"source_id": source_id, "document_id": document_id, "workflow_run_id": run_id}

    def url_submit(self, team_id: str, url: str, title: str) -> dict:
        source_id = f"source_{uuid4().hex}"
        document_id = f"doc_{uuid4().hex}"
        self.conn.execute(
            """
            INSERT INTO sources (id, team_id, source_kind, source_uri, title, status)
            VALUES (?, ?, 'url', ?, ?, 'active')
            """,
            (source_id, team_id, url, title),
        )
        self.conn.execute(
            """
            INSERT INTO documents (id, team_id, source_id, canonical_uri, title)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, team_id, source_id, url, title),
        )
        run_id = self._create_workflow_run(
            team_id, source_id, document_id, "full", source_kind="url", source_uri=url
        )
        self.conn.commit()
        return {"source_id": source_id, "document_id": document_id, "workflow_run_id": run_id}

    def api_submit(self, team_id: str, external_ref: str, title: str, payload: dict) -> dict:
        source_id = f"source_{uuid4().hex}"
        document_id = f"doc_{uuid4().hex}"
        self.conn.execute(
            """
            INSERT INTO sources (id, team_id, source_kind, external_ref, title, metadata_json)
            VALUES (?, ?, 'api', ?, ?, ?)
            """,
            (source_id, team_id, external_ref, title, json.dumps(payload)),
        )
        self.conn.execute(
            """
            INSERT INTO documents (id, team_id, source_id, canonical_uri, title)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, team_id, source_id, external_ref, title),
        )
        run_id = self._create_workflow_run(
            team_id, source_id, document_id, "full", source_kind="api"
        )
        self.conn.commit()
        return {"source_id": source_id, "document_id": document_id, "workflow_run_id": run_id}

    def static_confirm(
        self,
        *,
        team_id: str,
        upload_id: str,
        path: str,
        role: str = "uploaded",
        content: str,
    ) -> dict:
        upload = self.conn.execute(
            "SELECT * FROM uploads WHERE id = ? AND team_id = ?",
            (upload_id, team_id),
        ).fetchone()
        if not upload:
            raise ValueError("upload not found")
        self.object_store.put_text(upload["object_key"], content)
        source_id = f"source_{uuid4().hex}"
        document_id = f"doc_{uuid4().hex}"
        static_id = f"static_{uuid4().hex}"
        self.conn.execute(
            """
            INSERT INTO sources (id, team_id, upload_id, source_kind, source_uri, title)
            VALUES (?, ?, ?, 'file', ?, ?)
            """,
            (source_id, team_id, upload_id, upload["object_key"], path),
        )
        self.conn.execute(
            """
            INSERT INTO documents (id, team_id, source_id, canonical_uri, title)
            VALUES (?, ?, ?, ?, ?)
            """,
            (document_id, team_id, source_id, path, path),
        )
        self.conn.execute(
            """
            INSERT INTO static_files (
                id, team_id, source_id, document_id, upload_id,
                object_key, file_role, mime_type, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """,
            (
                static_id,
                team_id,
                source_id,
                document_id,
                upload_id,
                upload["object_key"],
                role,
                upload["mime_type"],
            ),
        )
        self.conn.execute(
            "UPDATE uploads SET status='confirmed' WHERE id = ?",
            (upload_id,),
        )
        self.conn.commit()
        return {"static_file_id": static_id, "source_id": source_id, "document_id": document_id}

    def _create_workflow_run(
        self,
        team_id: str,
        source_id: str,
        document_id: str,
        workflow_kind: str,
        *,
        source_kind: str = "file",
        source_uri: str = "",
    ) -> str:
        run_id = f"run_{uuid4().hex}"
        step_id = f"step_{uuid4().hex}"
        # F6-01: 创建侧写入 action_branch (执行侧据此 registry 分派, 取代硬选)。
        action_branch = _resolve_action_branch(source_kind, source_uri)
        self.conn.execute(
            """
            INSERT INTO workflow_runs (
                id, team_id, source_id, document_id,
                workflow_kind, trigger_kind, status, config_snapshot_json
            ) VALUES (?, ?, ?, ?, ?, 'api', 'pending', ?)
            """,
            (
                run_id,
                team_id,
                source_id,
                document_id,
                workflow_kind,
                json.dumps({"profile": "default"}),
            ),
        )
        self.conn.execute(
            """
            INSERT INTO workflow_steps (
                id, team_id, workflow_run_id, step_key, stage, action, payload_json, status
            ) VALUES (?, ?, ?, 'clean:init', 'clean', 'clean.start', ?, 'pending')
            """,
            (
                step_id,
                team_id,
                run_id,
                json.dumps(
                    {
                        "source_id": source_id,
                        "document_id": document_id,
                        "action_branch": action_branch,
                    }
                ),
            ),
        )
        return run_id
