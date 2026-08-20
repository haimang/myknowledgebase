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
from typing import Any, Literal

from src.persistence.engine import apply_capability_gates, probe_concurrent_writes, probe_native_vector
from src.persistence.migration_runner import (
    apply_migrations,
    discover_migrations,
    verify_migrations,
)
from src.persistence.uow import immediate_transaction


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

    def __init__(
        self,
        database_path: Path,
        migration_directory: Path,
        *,
        vector_backend: Literal["deterministic_exact", "native_ann"] = "deterministic_exact",
        concurrent_writes_required: bool = False,
        native_vector_required: bool = False,
    ) -> None:
        if vector_backend not in {"deterministic_exact", "native_ann"}:
            raise ValueError("vector_backend is unsupported")
        self.database_path = database_path
        self.migration_directory = migration_directory
        self.vector_backend = vector_backend
        self.concurrent_writes_required = concurrent_writes_required
        self.native_vector_required = native_vector_required
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

    def _discard_connection(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            try:
                connection.close()
            except Exception:
                pass

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[SqliteUnitOfWork]:
        async with self._write_lock:
            connection = self._connect()
            async with immediate_transaction(connection, discard=self._discard_connection):
                yield SqliteUnitOfWork(connection)

    def _open_probe_connection(self) -> sqlite3.Connection:
        connection = sqlite3.connect(self.database_path, check_same_thread=False, isolation_level=None)
        connection.row_factory = sqlite3.Row
        return connection

    async def readiness(self) -> dict[str, bool]:
        try:
            # SQLite exposes one connection to this single-writer profile.
            # Readiness verification touches that connection too, so it must
            # share the transaction lock; otherwise concurrent claims can race
            # a PRAGMA/schema query against BEGIN IMMEDIATE and falsely fence
            # healthy work as not-ready. Capability probes use a bypass
            # connection so they never flip the live journal_mode.
            async with self._write_lock:
                connection = self._connect()
                migrations = discover_migrations(self.migration_directory)
                schema_ok = await asyncio.to_thread(verify_migrations, connection, migrations)
                probe = self._open_probe_connection()
                try:
                    cw = await asyncio.to_thread(
                        probe_concurrent_writes, probe, restore_journal_mode=False
                    )
                    vector = await asyncio.to_thread(self._probe_native_vector, probe)
                finally:
                    probe.close()
            gates = apply_capability_gates(
                concurrent_writes=cw,
                native_vector=vector,
                concurrent_writes_required=self.concurrent_writes_required,
                native_vector_required=self.native_vector_required,
            )
            return {
                "db_primary": True,
                "schema_migration": schema_ok,
                "concurrent_writes": gates["concurrent_writes"],
                "native_vector": gates["native_vector"],
                "concurrent_writes_probe": gates["concurrent_writes_probe"],
                "native_vector_probe": gates["native_vector_probe"],
            }
        except Exception:
            return {
                "db_primary": False,
                "schema_migration": False,
                "concurrent_writes": False,
                "native_vector": False,
                "concurrent_writes_probe": False,
                "native_vector_probe": False,
            }

    def _probe_native_vector(self, connection: sqlite3.Connection) -> bool:
        # Stock sqlite3 cannot execute Turso native vector ops.  Selecting
        # deterministic_exact is a retrieval scan profile, not ANN evidence.
        del self
        return probe_native_vector(connection)

    async def close(self) -> None:
        if self._connection is not None:
            connection, self._connection = self._connection, None
            await asyncio.to_thread(connection.close)
