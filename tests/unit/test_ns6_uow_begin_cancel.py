"""NS6-T01: cancel during to_thread(BEGIN) must not poison the singleton connection."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.persistence import uow as uow_mod
from src.persistence.sqlite_port import SqlitePersistence


@pytest.mark.asyncio
async def test_cancel_during_begin_allows_next_immediate_begin(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "uow-begin.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    begin_entered = asyncio.Event()
    real_to_thread = uow_mod.asyncio.to_thread

    async def gated_to_thread(func: object, *args: object, **kwargs: object) -> object:
        sql = args[0] if args else None
        if isinstance(sql, str) and sql.strip().upper().startswith("BEGIN"):
            begin_entered.set()
            await asyncio.sleep(30)
        return await real_to_thread(func, *args, **kwargs)

    uow_mod.asyncio.to_thread = gated_to_thread  # type: ignore[method-assign]
    try:
        async def cancelled_begin() -> None:
            async with persistence.transaction():
                pass

        task = asyncio.create_task(cancelled_begin())
        await begin_entered.wait()
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
    finally:
        uow_mod.asyncio.to_thread = real_to_thread  # type: ignore[method-assign]

    async with persistence.transaction() as tx:
        await tx.execute("CREATE TABLE IF NOT EXISTS ns6_begin(x INTEGER)")
        await tx.execute("INSERT INTO ns6_begin(x) VALUES (1)")
        row = await tx.fetchone("SELECT COUNT(*) AS count FROM ns6_begin")
    assert row == {"count": 1}
    await persistence.close()
