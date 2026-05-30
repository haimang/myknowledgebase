from __future__ import annotations

import json
from sqlite3 import Connection, Row


class StepRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def create_step(
        self,
        *,
        step_id: str,
        team_id: str,
        workflow_run_id: str,
        step_key: str,
        stage: str,
        action: str,
        max_attempts: int = 3,
    ) -> None:
        self.conn.execute(
            """
            INSERT INTO workflow_steps (
                id, team_id, workflow_run_id, step_key, stage, action, payload_json, max_attempts
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                step_id,
                team_id,
                workflow_run_id,
                step_key,
                stage,
                action,
                json.dumps({"seed": True}),
                max_attempts,
            ),
        )
        self.conn.commit()

    def get_step(self, step_id: str) -> Row | None:
        return self.conn.execute(
            "SELECT * FROM workflow_steps WHERE id = ?",
            (step_id,),
        ).fetchone()

    def list_ready_steps(self) -> list[Row]:
        rows = self.conn.execute(
            "SELECT * FROM v_ready_steps ORDER BY priority ASC, available_at ASC"
        ).fetchall()
        return list(rows)
