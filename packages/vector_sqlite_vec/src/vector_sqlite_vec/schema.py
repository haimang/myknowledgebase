from __future__ import annotations

import logging
import re
from importlib import resources
from pathlib import Path
from sqlite3 import Connection, OperationalError

logger = logging.getLogger("vector_sqlite_vec.schema")


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


# RWA-09: 维度无关匹配 (任意 float[N]) — 避免 vec.sql 维度变更时 fallback 静默失配
# (1536→1024 迁移踩到的坑: 字面匹配在维度改动后不替换, vec0 语句残留致 OperationalError)。
_VEC0_STMT_RE = re.compile(
    r"CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embedding_index USING vec0\(\s*"
    r"embedding float\[\d+\]\s*\);",
)
_FALLBACK_TEXT_TABLE = (
    "CREATE TABLE IF NOT EXISTS chunk_embedding_index (\n"
    "    rowid INTEGER PRIMARY KEY,\n"
    "    embedding TEXT NOT NULL\n"
    ");"
)


def _fallback_vec_sql(sql_text: str) -> str:
    new_text, n = _VEC0_STMT_RE.subn(_FALLBACK_TEXT_TABLE, sql_text)
    if n == 0:
        raise ValueError(
            "fallback failed: vec0 virtual-table statement not found in vec.sql "
            "(reason=vec0_fallback_pattern_unmatched)"
        )
    return new_text


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
        # [Q1] degraded 必须 fail-loud, 禁止静默退化 (G-CR3-02 假绿根因, ⛔1)。
        logger.warning(
            "vec0 virtual table unavailable (%s); degrading to brute-force TEXT index. "
            "reason=sqlite_vec_unavailable_degraded_to_bruteforce",
            exc,
        )
        conn.executescript(_fallback_vec_sql(sql_text))
    conn.execute(
        "INSERT INTO vec_schema_migrations (migration_id) VALUES (?)",
        (migration_id,),
    )
    conn.commit()
