from __future__ import annotations

import json
from sqlite3 import Connection, Row


class RestartRequestRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def create(
        self,
        *,
        request_id: str,
        team_id: str,
        workflow_run_id: str,
        mode: str = "recovery",
        scope: dict | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO restart_requests (
                id, team_id, workflow_run_id, mode, scope_json
            ) VALUES (?, ?, ?, ?, ?)
            """,
            (request_id, team_id, workflow_run_id, mode, json.dumps(scope or {"all": True})),
        )
        self.conn.commit()

    def backlog(self) -> list[Row]:
        return list(self.conn.execute("SELECT * FROM v_restart_backlog").fetchall())


class PurgeRequestRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def create(
        self,
        *,
        request_id: str,
        team_id: str,
        target_kind: str,
        target_id: str,
        include_vectors: bool = True,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO purge_requests (
                id, team_id, target_kind, target_id, include_vectors, scope_json
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                request_id,
                team_id,
                target_kind,
                target_id,
                1 if include_vectors else 0,
                json.dumps({"target": target_id}),
            ),
        )
        self.conn.commit()

    def backlog(self) -> list[Row]:
        return list(self.conn.execute("SELECT * FROM v_purge_backlog").fetchall())
