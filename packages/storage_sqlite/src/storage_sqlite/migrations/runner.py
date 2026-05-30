from __future__ import annotations

from importlib import resources
from pathlib import Path
from sqlite3 import Connection


def _repo_sql_path() -> Path | None:
    path = Path(__file__).resolve()
    for parent in path.parents:
        candidate = parent / "docs" / "refactor" / "core.sql"
        if candidate.exists():
            return candidate
    return None


def _ensure_migration_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        """
    )


def apply_core_migrations(conn: Connection) -> None:
    _ensure_migration_table(conn)
    migration_id = "core-0001-ssot"
    row = conn.execute(
        "SELECT migration_id FROM schema_migrations WHERE migration_id = ?",
        (migration_id,),
    ).fetchone()
    if row:
        return

    sql_path = _repo_sql_path()
    if sql_path is not None:
        sql_text = sql_path.read_text(encoding="utf-8")
    else:
        sql_text = resources.files("storage_sqlite.migrations").joinpath("core.sql").read_text(
            encoding="utf-8"
        )
    conn.executescript(sql_text)
    conn.execute(
        "INSERT INTO schema_migrations (migration_id) VALUES (?)",
        (migration_id,),
    )
    conn.commit()
