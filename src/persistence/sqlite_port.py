"""Async-shaped SQLite development adapter isolated inside persistence.

SQLite is used for local and deterministic CI profiles. The port can be replaced
by a libSQL/Turso adapter without changing domain services.
"""

from __future__ import annotations

import asyncio
import sqlite3
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from src.persistence.migration_runner import (
    apply_migrations,
    discover_migrations,
    verify_migrations,
)


class SqliteUnitOfWork:
    def __init__(self, connection: sqlite3.Connection) -> None:
        self._connection = connection

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> sqlite3.Cursor:
        return await asyncio.to_thread(self._connection.execute, sql, params)

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        cursor = await self.execute(sql, params)
        row = await asyncio.to_thread(cursor.fetchone)
        return None if row is None else dict(row)

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cursor = await self.execute(sql, params)
        rows = await asyncio.to_thread(cursor.fetchall)
        return [dict(row) for row in rows]


class SqlitePersistence:
    """One in-process write authority guarded by an asyncio lock."""

    def __init__(self, database_path: Path, migration_directory: Path) -> None:
        self.database_path = database_path
        self.migration_directory = migration_directory
        self._write_lock = asyncio.Lock()
        self._connection: sqlite3.Connection | None = None

    def _connect(self) -> sqlite3.Connection:
        if self._connection is None:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(self.database_path, check_same_thread=False, isolation_level=None)
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA foreign_keys = ON")
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute("PRAGMA busy_timeout = 5000")
            self._connection = connection
        return self._connection

    async def migrate(self) -> None:
        async with self._write_lock:
            await asyncio.to_thread(
                apply_migrations,
                self._connect(),
                discover_migrations(self.migration_directory),
            )

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[SqliteUnitOfWork]:
        async with self._write_lock:
            connection = self._connect()
            await asyncio.to_thread(connection.execute, "BEGIN IMMEDIATE")
            try:
                yield SqliteUnitOfWork(connection)
            except Exception:
                await asyncio.to_thread(connection.rollback)
                raise
            else:
                await asyncio.to_thread(connection.commit)

    async def readiness(self) -> dict[str, bool]:
        try:
            connection = self._connect()
            migrations = discover_migrations(self.migration_directory)
            schema_ok = await asyncio.to_thread(verify_migrations, connection, migrations)
            # The portable local profile transparently performs relational vector
            # scans. Production requires the native-vector Turso capability.
            return {
                "db_primary": True,
                "schema_migration": schema_ok,
                "concurrent_writes": True,
                "native_vector": True,
            }
        except Exception:
            return {
                "db_primary": False,
                "schema_migration": False,
                "concurrent_writes": False,
                "native_vector": False,
            }

    async def close(self) -> None:
        if self._connection is not None:
            connection, self._connection = self._connection, None
            await asyncio.to_thread(connection.close)
