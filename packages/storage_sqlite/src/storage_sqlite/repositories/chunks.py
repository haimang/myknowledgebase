from __future__ import annotations

from sqlite3 import Connection, Row


class ChunkRepository:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def get_chunk(self, chunk_id: str) -> Row | None:
        return self.conn.execute(
            "SELECT * FROM chunks WHERE id = ?",
            (chunk_id,),
        ).fetchone()

    def set_vec_status(self, chunk_id: str, vec_status: str) -> None:
        self.conn.execute(
            """
            UPDATE chunks
            SET vec_status = ?, updated_at = strftime('%Y-%m-%dT%H:%M:%fZ', 'now')
            WHERE id = ?
            """,
            (vec_status, chunk_id),
        )
        self.conn.commit()
