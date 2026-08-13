"""Checksum-guarded, linear migration runner for the single MKB primary DB."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from src.contracts.common.errors import MkbError
from src.contracts.common.time import utc_now


class MigrationConnection(Protocol):
    def execute(self, sql: str, params: tuple[Any, ...] = ...) -> Any: ...

    def rollback(self) -> Any: ...


def _fetchall(connection: MigrationConnection, sql: str) -> list[Any]:
    cursor = connection.execute(sql)
    fetchall = getattr(cursor, "fetchall", None)
    if callable(fetchall):
        return list(fetchall())
    return list(cursor)


def strip_sql_line_comments(sql: str) -> str:
    """Remove ``--`` comments that Turso's script parser does not accept.

    Checksums stay on the original file bytes. This only changes how SQL is
    sent to the engine. Apostrophes inside string literals are preserved.
    """

    out: list[str] = []
    index = 0
    length = len(sql)
    in_string = False
    while index < length:
        char = sql[index]
        if in_string:
            out.append(char)
            if char == "'" and index + 1 < length and sql[index + 1] == "'":
                out.append(sql[index + 1])
                index += 2
                continue
            if char == "'":
                in_string = False
            index += 1
            continue
        if char == "'":
            in_string = True
            out.append(char)
            index += 1
            continue
        if char == "-" and index + 1 < length and sql[index + 1] == "-":
            while index < length and sql[index] != "\n":
                index += 1
            continue
        out.append(char)
        index += 1
    return "".join(out)


def _executescript(connection: MigrationConnection, script: str) -> None:
    executable = strip_sql_line_comments(script)
    executescript = getattr(connection, "executescript", None)
    if callable(executescript):
        executescript(executable)
        return
    connection.execute(executable)


@dataclass(frozen=True, slots=True)
class Migration:
    migration_id: str
    sql: str
    checksum: str


def discover_migrations(directory: Path) -> list[Migration]:
    migrations: list[Migration] = []
    for path in sorted(directory.glob("[0-9][0-9][0-9]_*.sql")):
        migrations.append(
            Migration(
                migration_id=path.stem,
                sql=path.read_text(encoding="utf-8"),
                checksum=hashlib.sha256(path.read_bytes()).hexdigest(),
            )
        )
    if not migrations:
        raise MkbError("migration-missing", "No MKB migrations were found", 503)
    return migrations


def ensure_migration_ledger(connection: MigrationConnection) -> None:
    connection.execute(
        """
        CREATE TABLE IF NOT EXISTS mkb_schema_migrations (
            migration_id TEXT PRIMARY KEY,
            checksum TEXT NOT NULL,
            applied_at TEXT NOT NULL,
            applied_by TEXT
        )
        """
    )


def apply_migrations(connection: MigrationConnection, migrations: list[Migration]) -> None:
    """Apply one globally ordered chain and fail loudly on any checksum drift."""

    ensure_migration_ledger(connection)
    applied = {
        row[0]: row[1]
        for row in _fetchall(connection, "SELECT migration_id, checksum FROM mkb_schema_migrations ORDER BY migration_id")
    }
    known = {migration.migration_id for migration in migrations}
    unknown = set(applied) - known
    if unknown:
        raise MkbError("migration-unknown", "Database contains an unknown migration", 503)
    for migration in migrations:
        existing = applied.get(migration.migration_id)
        if existing is not None:
            if existing != migration.checksum:
                raise MkbError("migration-checksum-drift", "Migration checksum drift detected", 503)
            continue
        try:
            # MKB migrations carry their own BEGIN/COMMIT so DDL and the ledger
            # row are one SQLite transaction. ``executescript`` would otherwise
            # implicitly commit an already-open Python transaction.
            marker = "COMMIT;"
            if migration.sql.rstrip().endswith(marker):
                ledger_sql = (
                    "INSERT INTO mkb_schema_migrations(migration_id, checksum, applied_at, applied_by) "
                    f"VALUES ({migration.migration_id!r}, {migration.checksum!r}, {utc_now()!r}, 'mkb');\n"
                    "COMMIT;"
                )
                script = migration.sql.rstrip()[: -len(marker)] + ledger_sql
            else:
                raise MkbError("migration-transaction-missing", "Migration must end with COMMIT", 503)
            _executescript(connection, script)
        except Exception:
            connection.rollback()
            raise


def verify_migrations(connection: MigrationConnection, migrations: list[Migration]) -> bool:
    try:
        ensure_migration_ledger(connection)
        applied = dict(_fetchall(connection, "SELECT migration_id, checksum FROM mkb_schema_migrations"))
    except Exception:
        return False
    return len(applied) == len(migrations) and all(
        applied.get(migration.migration_id) == migration.checksum for migration in migrations
    )
