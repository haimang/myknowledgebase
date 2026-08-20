"""Local Turso Database adapter (pyturso / ``import turso``).

Domain and runtime never import this module. The composition root selects it
through ``src.persistence.factory``. This is the in-process Turso engine from
https://github.com/tursodatabase/turso — not libSQL and not Turso Cloud.
"""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from src.persistence.engine import apply_capability_gates, probe_concurrent_writes, probe_native_vector
from src.persistence.migration_runner import apply_migrations, discover_migrations, verify_migrations
from src.persistence.uow import immediate_transaction


class _RowcountCursor:
    """Normalize pyturso cursors that report ``rowcount=-1`` after DML."""

    def __init__(self, cursor: Any, rowcount: int) -> None:
        self._cursor = cursor
        self.rowcount = rowcount

    def __getattr__(self, name: str) -> Any:
        return getattr(self._cursor, name)


class TursoUnitOfWork:
    def __init__(self, connection: Any) -> None:
        self._connection = connection

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> Any:
        cursor = await asyncio.to_thread(self._connection.execute, sql, params)
        rowcount = getattr(cursor, "rowcount", -1)
        if not isinstance(rowcount, int) or rowcount < 0:
            changes = getattr(self._connection, "changes", None)
            rowcount = int(changes()) if callable(changes) else 0
        return _RowcountCursor(cursor, rowcount)

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        cursor = await self.execute(sql, params)
        row = await asyncio.to_thread(cursor.fetchone)
        return None if row is None else _row_dict(cursor, row)

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        cursor = await self.execute(sql, params)
        rows = await asyncio.to_thread(cursor.fetchall)
        return [_row_dict(cursor, row) for row in rows]


def _row_dict(cursor: Any, row: Any) -> dict[str, Any]:
    if isinstance(row, dict):
        return dict(row)
    description = getattr(cursor, "description", None) or ()
    names = [item[0] for item in description]
    if names:
        return {name: row[index] for index, name in enumerate(names)}
    return dict(row)


class TursoPersistence:
    """Local-file Turso Database connection used as mkb_primary."""

    def __init__(
        self,
        database_path: Path,
        migration_directory: Path,
        *,
        concurrent_writes_required: bool = True,
        native_vector_required: bool = True,
    ) -> None:
        self.database_path = database_path
        self.migration_directory = migration_directory
        self.concurrent_writes_required = concurrent_writes_required
        self.native_vector_required = native_vector_required
        self._write_lock = asyncio.Lock()
        self._connection: Any | None = None

    def _discard_connection(self) -> None:
        connection = self._connection
        self._connection = None
        if connection is not None:
            close = getattr(connection, "close", None)
            if close is not None:
                try:
                    close()
                except Exception:
                    pass

    def _connect(self) -> Any:
        if self._connection is None:
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            import turso

            connection = turso.connect(str(self.database_path))
            try:
                connection.execute("PRAGMA busy_timeout = 5000")
            except Exception:
                pass
            try:
                connection.execute("PRAGMA foreign_keys = ON")
            except Exception:
                pass
            try:
                cursor = connection.execute("PRAGMA foreign_keys")
                row = cursor.fetchone() if hasattr(cursor, "fetchone") else None
                if row is not None:
                    value = row[0] if not isinstance(row, dict) else next(iter(row.values()))
                    if int(value or 0) != 1:
                        raise RuntimeError("foreign_keys pragma did not read back as 1")
            except RuntimeError:
                try:
                    connection.close()
                except Exception:
                    pass
                raise
            except Exception:
                pass
            self._connection = connection
        return self._connection

    def _open_probe_connection(self) -> Any:
        import turso

        return turso.connect(str(self.database_path))

    async def migrate(self) -> None:
        async with self._write_lock:
            await asyncio.to_thread(
                apply_migrations,
                self._connect(),
                discover_migrations(self.migration_directory),
            )

    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[TursoUnitOfWork]:
        async with self._write_lock:
            connection = self._connect()
            async with immediate_transaction(connection, discard=self._discard_connection):
                yield TursoUnitOfWork(connection)

    async def readiness(self) -> dict[str, bool]:
        try:
            async with self._write_lock:
                connection = self._connect()
                migrations = discover_migrations(self.migration_directory)
                schema_ok = await asyncio.to_thread(verify_migrations, connection, migrations)
                probe = self._open_probe_connection()
                try:
                    cw = await asyncio.to_thread(
                        probe_concurrent_writes, probe, restore_journal_mode=False
                    )
                    vector = await asyncio.to_thread(probe_native_vector, probe)
                finally:
                    close = getattr(probe, "close", None)
                    if close is not None:
                        try:
                            close()
                        except Exception:
                            pass
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

    async def close(self) -> None:
        if self._connection is not None:
            connection, self._connection = self._connection, None
            close = getattr(connection, "close", None)
            if close is not None:
                await asyncio.to_thread(close)



