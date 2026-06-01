from __future__ import annotations

from sqlite3 import Connection, Row

from rag_vectorizer import SearchService
from storage_objects import FileSystemObjectStore
from workflow_core.health import collect_health
from workflow_core.purge import create_purge_request, process_purge_requests
from workflow_core.restart import create_restart_request, process_restart_requests


class ManagementService:
    def __init__(
        self,
        conn: Connection,
        *,
        vec_conn: Connection | None = None,
        object_store: FileSystemObjectStore,
    ) -> None:
        self.conn = conn
        self.vec_conn = vec_conn
        self.object_store = object_store

    def list_workflows(self, team_id: str) -> list[Row]:
        return list(
            self.conn.execute(
                """
                SELECT id, workflow_kind, status, created_at, document_id
                FROM workflow_runs
                WHERE team_id = ?
                ORDER BY created_at DESC
                """,
                (team_id,),
            ).fetchall()
        )

    def get_workflow(self, team_id: str, run_id: str) -> Row | None:
        return self.conn.execute(
            "SELECT * FROM workflow_runs WHERE id = ? AND team_id = ?",
            (run_id, team_id),
        ).fetchone()

    def list_documents(self, team_id: str) -> list[Row]:
        return list(
            self.conn.execute(
                """
                SELECT d.id, d.title, d.status, d.canonical_uri, d.created_at, d.source_id
                FROM documents d
                WHERE d.team_id = ?
                ORDER BY d.created_at DESC
                """,
                (team_id,),
            ).fetchall()
        )

    def get_document(self, team_id: str, document_id: str) -> Row | None:
        return self.conn.execute(
            "SELECT * FROM documents WHERE id = ? AND team_id = ?",
            (document_id, team_id),
        ).fetchone()

    def list_static_files(self, team_id: str) -> list[Row]:
        return list(
            self.conn.execute(
                """
                SELECT id, document_id, object_key, file_role, status, created_at
                FROM static_files
                WHERE team_id = ?
                ORDER BY created_at DESC
                """,
                (team_id,),
            ).fetchall()
        )

    def get_static_file(self, team_id: str, static_file_id: str) -> Row | None:
        return self.conn.execute(
            "SELECT * FROM static_files WHERE id = ? AND team_id = ?",
            (static_file_id, team_id),
        ).fetchone()

    def search(self, team_id: str, query: str, limit: int = 6) -> list[dict]:
        if self.vec_conn is None:
            raise ValueError("vec connection is required for search")
        return SearchService(
            self.conn,
            self.vec_conn,
            workspace_key=team_id,
            object_store=self.object_store,
        ).search(
            team_id=team_id,
            query=query,
            limit=limit,
        )

    def search_debug(self, team_id: str, query: str, limit: int = 6) -> dict:
        if self.vec_conn is None:
            raise ValueError("vec connection is required for search")
        return SearchService(
            self.conn,
            self.vec_conn,
            workspace_key=team_id,
            object_store=self.object_store,
        ).search_debug(team_id=team_id, query=query, limit=limit)

    def list_active_claims(self, team_id: str) -> list[Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM v_active_claims WHERE team_id = ? ORDER BY claimed_at DESC",
                (team_id,),
            ).fetchall()
        )

    def list_restart_backlog(self, team_id: str) -> list[Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM v_restart_backlog WHERE team_id = ? ORDER BY created_at ASC",
                (team_id,),
            ).fetchall()
        )

    def list_purge_backlog(self, team_id: str) -> list[Row]:
        return list(
            self.conn.execute(
                "SELECT * FROM v_purge_backlog WHERE team_id = ? ORDER BY created_at ASC",
                (team_id,),
            ).fetchall()
        )

    def restart_workflow(
        self,
        *,
        team_id: str,
        workflow_run_id: str,
        mode: str = "recovery",
    ) -> str:
        request_id = f"restart_{workflow_run_id}"
        create_restart_request(
            self.conn,
            request_id=request_id,
            team_id=team_id,
            workflow_run_id=workflow_run_id,
            mode=mode,
        )
        process_restart_requests(self.conn)
        return request_id

    def purge_document(self, *, team_id: str, document_id: str) -> str:
        request_id = f"purge_{document_id}"
        create_purge_request(
            self.conn,
            request_id=request_id,
            team_id=team_id,
            target_kind="document",
            target_id=document_id,
        )
        process_purge_requests(self.conn, self.vec_conn, self.object_store)
        return request_id

    def health(self, team_id: str) -> dict:
        return collect_health(self.conn, team_id=team_id)
