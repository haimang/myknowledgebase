from __future__ import annotations

from importlib import resources
from pathlib import Path
from sqlite3 import Connection, OperationalError


def _repo_sql_path() -> Path | None:
    path = Path(__file__).resolve()
    for parent in path.parents:
        candidate = parent / "docs" / "refactor" / "vec.sql"
        if candidate.exists():
            return candidate
    return None


def _ensure_migration_table(conn: Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS vec_schema_migrations (
            migration_id TEXT PRIMARY KEY,
            applied_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ', 'now'))
        );
        """
    )


def _fallback_vec_sql(sql_text: str) -> str:
    virtual_stmt = (
        "CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embedding_index USING vec0(\n"
        "    embedding float[1536]\n"
        ");"
    )
    return sql_text.replace(
        virtual_stmt,
        """
CREATE TABLE IF NOT EXISTS chunk_embedding_index (
    rowid INTEGER PRIMARY KEY,
    embedding TEXT NOT NULL
);
""".strip(),
    )


def apply_vec_schema(conn: Connection) -> None:
    _ensure_migration_table(conn)
    migration_id = "vec-0001-ssot"
    row = conn.execute(
        "SELECT migration_id FROM vec_schema_migrations WHERE migration_id = ?",
        (migration_id,),
    ).fetchone()
    if row:
        return

    sql_path = _repo_sql_path()
    if sql_path is not None:
        sql_text = sql_path.read_text(encoding="utf-8")
    else:
        sql_text = resources.files("vector_sqlite_vec").joinpath("vec.sql").read_text(
            encoding="utf-8"
        )
    try:
        conn.executescript(sql_text)
    except OperationalError as exc:
        if "vec0" not in str(exc):
            raise
        conn.executescript(_fallback_vec_sql(sql_text))
    conn.execute(
        "INSERT INTO vec_schema_migrations (migration_id) VALUES (?)",
        (migration_id,),
    )
    conn.commit()
