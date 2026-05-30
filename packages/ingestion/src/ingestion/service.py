from __future__ import annotations

import json
from sqlite3 import Connection
from uuid import uuid4

from storage_objects import FileSystemObjectStore


class IngestionService:
    def __init__(self, conn: Connection, object_store: FileSystemObjectStore) -> None:
        self.conn = conn
        self.object_store = object_store

    def file_initiate(self, team_id: str, user_id: str, filename: str, mime_type: str) -> dict:
        upload_id = f"upload_{uuid4().hex}"
        object_key = f"raw/{team_id}/{upload_id}/{filename}"
        self.conn.execute(
            """
            INSERT INTO uploads (
                id, team_id, source_kind, object_key, original_filename,
                mime_type, created_by_user_id, status
            ) VALUES (?, ?, 'file', ?, ?, ?, ?, 'initiated')
            """,
            (upload_id, team_id, object_key, filename, mime_type, user_id),
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
        run_id = self._create_workflow_run(team_id, source_id, document_id, workflow_kind)
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
        run_id = self._create_workflow_run(team_id, source_id, document_id, "full")
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
        run_id = self._create_workflow_run(team_id, source_id, document_id, "full")
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
        self, team_id: str, source_id: str, document_id: str, workflow_kind: str
    ) -> str:
        run_id = f"run_{uuid4().hex}"
        step_id = f"step_{uuid4().hex}"
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
                json.dumps({"source_id": source_id, "document_id": document_id}),
            ),
        )
        return run_id
