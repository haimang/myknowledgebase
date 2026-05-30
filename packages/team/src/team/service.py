from __future__ import annotations

from sqlite3 import Connection, Row
from uuid import uuid4


class TeamService:
    def __init__(self, conn: Connection) -> None:
        self.conn = conn

    def bootstrap(self, user_id: str, name: str, slug: str) -> str:
        team_id = f"team_{uuid4().hex}"
        self.conn.execute(
            "INSERT INTO teams (id, slug, name) VALUES (?, ?, ?)",
            (team_id, slug, name),
        )
        self.conn.execute(
            """
            INSERT INTO team_members (team_id, user_id, role, status, joined_at)
            VALUES (?, ?, 'owner', 'active', strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
            """,
            (team_id, user_id),
        )
        self.conn.commit()
        return team_id

    def list_memberships(self, user_id: str) -> list[Row]:
        return list(
            self.conn.execute(
                """
                SELECT tm.team_id, t.slug, t.name, tm.role
                FROM team_members tm
                JOIN teams t ON t.id = tm.team_id
                WHERE tm.user_id = ? AND tm.status = 'active'
                ORDER BY t.created_at
                """,
                (user_id,),
            ).fetchall()
        )

    def is_member(self, user_id: str, team_id: str) -> bool:
        row = self.conn.execute(
            """
            SELECT 1
            FROM team_members
            WHERE team_id = ? AND user_id = ? AND status = 'active'
            """,
            (team_id, user_id),
        ).fetchone()
        return row is not None

    def select_team(self, session_id: str, team_id: str) -> None:
        self.conn.execute("UPDATE sessions SET team_id = ? WHERE id = ?", (team_id, session_id))
        self.conn.commit()
