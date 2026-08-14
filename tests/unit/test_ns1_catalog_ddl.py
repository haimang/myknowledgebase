"""NS1-T03: the prompt catalog is a column promotion, not a new table."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.persistence.sqlite_port import SqlitePersistence


@pytest.mark.asyncio
async def test_prompt_catalog_columns_and_checks_exist_after_fresh_migration(tmp_path: Path) -> None:
    database = tmp_path / "ddl.sqlite3"
    persistence = SqlitePersistence(database, Path("src/persistence/migrations"))
    try:
        await persistence.migrate()
    finally:
        await persistence.close()
    with sqlite3.connect(database) as connection:
        columns = {row[1] for row in connection.execute("PRAGMA table_info(mkb_prompt_hash_pointers)")}
        assert {"prompt_id", "role", "status", "granularity_set"} <= columns
        table_count = connection.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name LIKE '%prompt_catalog%'"
        ).fetchone()[0]
        assert table_count == 0
        with pytest.raises(sqlite3.IntegrityError):
            connection.execute(
                "INSERT INTO mkb_prompt_hash_pointers "
                "(prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,registered_at) "
                "VALUES ('x','x','v1','x.md',?, 'not-a-role','active','now')",
                ("a" * 64,),
            )
