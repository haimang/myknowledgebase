from __future__ import annotations

from sqlite3 import Connection


def collect_health(conn: Connection, *, team_id: str) -> dict:
    stale_claims = conn.execute(
        "SELECT COUNT(1) AS c FROM v_stale_claims WHERE team_id = ?",
        (team_id,),
    ).fetchone()["c"]
    restart_backlog = conn.execute(
        "SELECT COUNT(1) AS c FROM v_restart_backlog WHERE team_id = ?",
        (team_id,),
    ).fetchone()["c"]
    purge_backlog = conn.execute(
        "SELECT COUNT(1) AS c FROM v_purge_backlog WHERE team_id = ?",
        (team_id,),
    ).fetchone()["c"]
    pending_purge = conn.execute(
        "SELECT COUNT(1) AS c FROM v_pending_purge_chunks WHERE team_id = ?",
        (team_id,),
    ).fetchone()["c"]
    return {
        "stale_claims": int(stale_claims),
        "restart_backlog": int(restart_backlog),
        "purge_backlog": int(purge_backlog),
        "pending_purge_chunks": int(pending_purge),
    }

