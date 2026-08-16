"""NS4-T11 / T12 / T13: evidence-plane migration on the test sqlite fixture."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.persistence.factory import build_persistence
from src.persistence.migration_runner import discover_migrations


@pytest.mark.asyncio
async def test_migration_013_adds_columns_and_stage_report_table(tmp_path: Path) -> None:
    persistence = build_persistence(
        tmp_path / "ns4.db",
        Path("src/persistence/migrations"),
        backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
        async with persistence.transaction() as tx:
            applied = [
                row["migration_id"]
                for row in await tx.fetchall("SELECT migration_id FROM mkb_schema_migrations ORDER BY migration_id")
            ]
            columns = {
                row["name"]
                for row in await tx.fetchall("PRAGMA table_info(mkb_generation_invocations)")
            }
            tables = {
                row["name"]
                for row in await tx.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
            }
        expected = [item.migration_id for item in discover_migrations(Path("src/persistence/migrations"))]
        assert applied == expected
        assert "013_generation_evidence_plane" in applied
        assert {"status", "stage_key", "error_code", "adapter_kind", "cli_structured_kind"} <= columns
        assert "mkb_generation_stage_reports" in tables
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_invocation_status_check_rejects_unknown(tmp_path: Path) -> None:
    persistence = build_persistence(
        tmp_path / "ns4-check.db",
        Path("src/persistence/migrations"),
        backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
        with pytest.raises(Exception):
            async with persistence.transaction() as tx:
                await tx.execute(
                    "INSERT INTO mkb_generation_invocations ("
                    "invocation_uuid,team_uuid,execution_uuid,process_uuid,process_attempt,"
                    "invocation_ordinal,invocation_kind,input_digest,occurred_at,status"
                    ") VALUES ('i','t','e','p',0,0,'generation','aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa','now','maybe')"
                )
    finally:
        await persistence.close()
