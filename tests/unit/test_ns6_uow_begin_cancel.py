"""NS6-T01: cancel during to_thread(BEGIN) must not poison the singleton connection."""

from __future__ import annotations

import asyncio
import threading
from pathlib import Path

import pytest

from src.persistence.sqlite_port import SqlitePersistence


@pytest.mark.asyncio
async def test_cancel_during_begin_allows_next_immediate_begin(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "uow-begin.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    inner = persistence._connect()
    begin_entered = threading.Event()
    allow_begin = threading.Event()

    class _BeginGate:
        def __init__(self, wrapped: object) -> None:
            self._wrapped = wrapped

        def execute(self, sql: object, *args: object, **kwargs: object) -> object:
            if isinstance(sql, str) and sql.strip().upper().startswith("BEGIN"):
                begin_entered.set()
                if not allow_begin.wait(timeout=5):
                    raise TimeoutError("BEGIN test gate timed out")
            return self._wrapped.execute(sql, *args, **kwargs)  # type: ignore[attr-defined]

        def __getattr__(self, name: str) -> object:
            return getattr(self._wrapped, name)

    persistence._connection = _BeginGate(inner)  # type: ignore[assignment]

    async def cancelled_begin() -> None:
        async with persistence.transaction():
            pass

    task = asyncio.create_task(cancelled_begin())
    await asyncio.to_thread(begin_entered.wait, 5)
    assert begin_entered.is_set()
    task.cancel()
    allow_begin.set()
    with pytest.raises(asyncio.CancelledError):
        await task

    async with persistence.transaction() as tx:
        await tx.execute("CREATE TABLE IF NOT EXISTS ns6_begin(x INTEGER)")
        await tx.execute("INSERT INTO ns6_begin(x) VALUES (1)")
        row = await tx.fetchone("SELECT COUNT(*) AS count FROM ns6_begin")
    assert row == {"count": 1}
    await persistence.close()
