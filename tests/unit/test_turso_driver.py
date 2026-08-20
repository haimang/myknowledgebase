"""Driver-layer tests for the local Turso Database (pyturso) adapter.

These tests open the shipped factory/adapter. They do not reimplement
connect/migrate, and they do not import libsql as the selected engine.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persistence.engine import probe_concurrent_writes, probe_native_vector
from src.persistence.factory import build_persistence
from src.persistence.migration_runner import discover_migrations
from src.persistence.sqlite_port import SqlitePersistence


def test_factory_rejects_libsql_as_selected_backend(tmp_path: Path) -> None:
    with pytest.raises(ValueError, match="persistence backend is unsupported"):
        build_persistence(
            tmp_path / "x.db",
            Path("src/persistence/migrations"),
            backend="libsql",  # type: ignore[arg-type]
        )


@pytest.mark.asyncio
async def test_turso_adapter_migrates_write_commit_and_reopens(tmp_path: Path) -> None:
    path = tmp_path / "mkb_primary.db"
    persistence = build_persistence(
        path,
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_teams(team_uuid,name,status,creation_fingerprint,created_at,updated_at,payload_extra) "
                "VALUES ('11111111-1111-1111-1111-111111111111','probe','active','fp','t','t','{}')"
            )
        await persistence.close()
        again = build_persistence(
            path,
            Path("src/persistence/migrations"),
            backend="turso",
            concurrent_writes_required=False,
            native_vector_required=False,
        )
        try:
            async with again.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT migration_id FROM mkb_schema_migrations ORDER BY migration_id"
                )
                team = await tx.fetchone(
                    "SELECT name FROM mkb_teams WHERE team_uuid='11111111-1111-1111-1111-111111111111'"
                )
            applied = [row["migration_id"] for row in rows]
            expected = [item.migration_id for item in discover_migrations(Path("src/persistence/migrations"))]
            assert applied == expected
            assert team is not None
            assert team["name"] == "probe"
        finally:
            await again.close()
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_turso_adapter_runs_manual_vector_sql(tmp_path: Path) -> None:
    persistence = build_persistence(
        tmp_path / "vector.db",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=True,
    )
    try:
        await persistence.migrate()
        async with persistence.transaction() as tx:
            await tx.execute(
                "CREATE TABLE IF NOT EXISTS vec_probe(id INTEGER PRIMARY KEY, embedding BLOB)"
            )
            await tx.execute(
                "INSERT INTO vec_probe(id, embedding) VALUES (1, vector32('[1.0, 0.0]'))"
            )
            row = await tx.fetchone(
                "SELECT vector_distance_cos(embedding, vector32('[0.0, 1.0]')) AS distance "
                "FROM vec_probe WHERE id=1"
            )
        assert row is not None
        assert row["distance"] == pytest.approx(1.0)
        readiness = await persistence.readiness()
        assert readiness["native_vector_probe"] is True
        assert readiness["native_vector"] is True
        assert "libsql_vector_idx" not in (probe_native_vector.__doc__ or "")
    finally:
        await persistence.close()


def test_native_vector_probe_does_not_mention_libsql_index() -> None:
    source = Path("src/persistence/engine.py").read_text(encoding="utf-8")
    assert "libsql_vector_idx" not in Path("src/persistence/engine.py").read_text(encoding="utf-8").split("def probe_native_vector")[1].split("def ")[0]
    assert "vector32" in source
    assert "vector_distance_cos" in source


@pytest.mark.asyncio
async def test_turso_readiness_reports_honest_cw_and_vector(tmp_path: Path) -> None:
    persistence = build_persistence(
        tmp_path / "ready.db",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=True,
        native_vector_required=True,
    )
    try:
        await persistence.migrate()
        readiness = await persistence.readiness()
        assert readiness["schema_migration"] is True
        assert readiness["native_vector_probe"] is True
        assert readiness["native_vector"] is True
        if not readiness["concurrent_writes_probe"]:
            pytest.skip("Turso BEGIN CONCURRENT is not available on this engine")
        # Probe can be true while UoW remains BEGIN IMMEDIATE.  The gated
        # flag must not advertise CONCURRENT writers that the write path
        # does not use.
        assert readiness["concurrent_writes"] is False
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_sqlite_constitution_defaults_remain_not_ready(tmp_path: Path) -> None:
    persistence = SqlitePersistence(
        tmp_path / "sqlite.db",
        Path("src/persistence/migrations"),
        concurrent_writes_required=True,
        native_vector_required=True,
    )
    try:
        await persistence.migrate()
        readiness = await persistence.readiness()
        assert readiness["concurrent_writes"] is False
        assert readiness["native_vector"] is False
        assert probe_concurrent_writes is not None
        assert probe_native_vector is not None
    finally:
        await persistence.close()
