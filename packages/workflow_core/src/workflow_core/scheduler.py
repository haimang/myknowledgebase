from __future__ import annotations

from sqlite3 import Connection, Row

from .claim import claim_next_step


class WorkflowScheduler:
    def __init__(self, conn: Connection, *, worker_type: str, worker_id: str) -> None:
        self.conn = conn
        self.worker_type = worker_type
        self.worker_id = worker_id

    def claim_one(self) -> Row | None:
        return claim_next_step(
            self.conn,
            worker_type=self.worker_type,
            worker_id=self.worker_id,
        )
