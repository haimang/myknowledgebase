from __future__ import annotations

from sqlite3 import Connection, Row


class ArtifactRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def get_artifact(self, artifact_id: str) -> Row | None:
        return self.conn.execute(
            "SELECT * FROM artifacts WHERE id = ?",
            (artifact_id,),
        ).fetchone()
