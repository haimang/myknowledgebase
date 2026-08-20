"""Cancellation-safe immediate-transaction helper shared by SQLite and Turso."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable
from contextlib import asynccontextmanager
from typing import Any


@asynccontextmanager
async def immediate_transaction(
    connection: Any,
    *,
    discard: Callable[[], None],
    begin_sql: str = "BEGIN IMMEDIATE",
) -> AsyncIterator[None]:
    """Run one write transaction that cannot leave the connection in-transaction.

    ``CancelledError`` is a ``BaseException``: catching only ``Exception``
    would skip rollback and the next ``BEGIN`` would fail. Commit lives inside
    the ``try`` so a failed commit also rolls back (or discards the handle when
    rollback itself is uncertain).
    """

    body_ok = False
    begun = False
    try:
        # BEGIN lives in the same BaseException fence as commit. Cancel during
        # to_thread(BEGIN) leaves the handle's transaction state unknown, so
        # the caller must discard rather than return a poisoned singleton.
        await asyncio.to_thread(connection.execute, begin_sql)
        begun = True
        yield
        body_ok = True
        await asyncio.to_thread(connection.commit)
    except BaseException:
        if not begun:
            discard()
            raise
        try:
            await asyncio.shield(asyncio.to_thread(connection.rollback))
        except Exception:
            discard()
        else:
            if body_ok:
                # Commit raised after the body succeeded. Rollback may not
                # undo a driver-partial commit; drop the handle.
                discard()
        raise
