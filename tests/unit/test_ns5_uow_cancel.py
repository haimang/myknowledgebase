"""NS5-T01: cancellation-safe UoW can BEGIN again after cancel or commit failure."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.persistence.sqlite_port import SqlitePersistence


@pytest.mark.asyncio
async def test_cancelled_uow_allows_next_begin(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "uow.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    async with persistence.transaction() as tx:
        await tx.execute("CREATE TABLE IF NOT EXISTS ns5_uow(x INTEGER)")

    async def cancelled_body() -> None:
        async with persistence.transaction() as tx:
            await tx.execute("INSERT INTO ns5_uow(x) VALUES (7)")
            await asyncio.sleep(30)

    task = asyncio.create_task(cancelled_body())
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    async with persistence.transaction() as tx:
        await tx.execute("INSERT INTO ns5_uow(x) VALUES (1)")
        row = await tx.fetchone("SELECT COUNT(*) AS count FROM ns5_uow")
    assert row == {"count": 1}
    await persistence.close()


@pytest.mark.asyncio
async def test_failed_commit_discards_handle(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "uow-commit.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    inner = persistence._connect()

    class _CommitBoom:
        def __init__(self, wrapped: object) -> None:
            self._wrapped = wrapped

        def commit(self) -> None:
            raise RuntimeError("commit interrupted")

        def __getattr__(self, name: str) -> object:
            return getattr(self._wrapped, name)

    persistence._connection = _CommitBoom(inner)  # type: ignore[assignment]
    with pytest.raises(RuntimeError, match="commit interrupted"):
        async with persistence.transaction() as tx:
            await tx.execute("CREATE TABLE IF NOT EXISTS ns5_uow_commit(x INTEGER)")
    async with persistence.transaction() as tx:
        await tx.execute("SELECT 1")
    await persistence.close()
