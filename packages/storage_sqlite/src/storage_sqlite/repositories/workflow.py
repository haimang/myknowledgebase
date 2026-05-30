from __future__ import annotations

import json
from sqlite3 import Connection, Row


class WorkflowRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def create_run(
        self,
        *,
        run_id: str,
        team_id: str,
        source_id: str,
        document_id: str,
        workflow_kind: str = "full",
        trigger_kind: str = "api",
        config_snapshot: dict | None = None,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO workflow_runs (
                id, team_id, source_id, document_id,
                workflow_kind, trigger_kind, config_snapshot_json, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
            """,
            (
                run_id,
                team_id,
                source_id,
                document_id,
                workflow_kind,
                trigger_kind,
                json.dumps(config_snapshot or {"version": "p1"}),
            ),
        )
        self.conn.commit()

    def get_run(self, run_id: str) -> Row | None:
        return self.conn.execute(
            "SELECT * FROM workflow_runs WHERE id = ?",
            (run_id,),
        ).fetchone()
