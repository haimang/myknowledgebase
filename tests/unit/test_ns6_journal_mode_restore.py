"""NS6-T03: readiness must not flip the live database journal_mode."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persistence.factory import build_persistence


def _journal_mode(database_path: Path) -> str:
    import turso

    connection = turso.connect(str(database_path))
    try:
        cursor = connection.execute("PRAGMA journal_mode")
        row = cursor.fetchone()
        value = row[0] if not isinstance(row, dict) else next(iter(row.values()))
        return str(value).lower()
    finally:
        closer = getattr(connection, "close", None)
        if closer is not None:
            closer()


@pytest.mark.asyncio
async def test_turso_readiness_does_not_mutate_live_journal_mode(tmp_path: Path) -> None:
    database_path = tmp_path / "live.db"
    persistence = build_persistence(
        database_path,
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=True,
        native_vector_required=True,
    )
    try:
        await persistence.migrate()
        before = _journal_mode(database_path)
        assert before
        await persistence.readiness()
        after = _journal_mode(database_path)
        assert after == before
        assert after != "mvcc"
    finally:
        await persistence.close()
