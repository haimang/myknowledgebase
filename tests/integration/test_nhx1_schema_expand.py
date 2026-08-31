"""NHX1 Phase-2 EXIT: 025-028 expand, constraints, parity, and resumability."""

from __future__ import annotations

import shutil
import sqlite3
from pathlib import Path

import pytest

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.governance import ERROR_DEFINITIONS, OUTBOX_KIND_DEFINITIONS, resolve_error_definition
from src.persistence.migration_runner import discover_migrations
from src.persistence.nhx1_migration import MigrationStage, MigrationStatus, Nhx1MigrationService
from src.persistence.sqlite_port import SqlitePersistence
from src.persistence.turso.port import TursoPersistence
from src.services.governance_registry import GovernanceRegistryService

ROOT = Path(__file__).resolve().parents[2]
MIGRATIONS = ROOT / "src/persistence/migrations"
FIXTURE = ROOT / "tests/fixtures/new_harvest_nhx1/pre-fix-024.db"
NOW = "2026-08-31T00:00:00Z"

EXPECTED_TABLES = {
    "mkb_intake_observations",
    "mkb_observation_attempts",
    "mkb_intake_acceptance_facts",
    "mkb_item_epoch_transitions",
    "mkb_object_upload_sessions",
    "mkb_object_promotion_journals",
    "mkb_object_deletion_jobs",
    "mkb_cleanup_jobs",
    "mkb_cleanup_job_steps",
    "mkb_processing_binding_assertions",
    "mkb_selection_assertions_v2",
    "mkb_evidence_verifications",
    "mkb_evidence_corrections",
    "mkb_publication_manifests",
    "mkb_publication_manifest_members",
    "mkb_outbox_kind_definitions",
    "mkb_command_receipts",
    "mkb_process_capability_definitions",
    "mkb_error_definitions",
    "mkb_error_aliases",
    "mkb_operational_signal_definitions",
    "mkb_nhx1_migration_state",
    "mkb_nhx1_shadow_mismatches",
    "mkb_nhx1_cutover_state",
}


async def _schema(persistence) -> tuple[set[str], dict[str, set[str]]]:
    async with persistence.read_snapshot() as tx:
        table_rows = await tx.fetchall("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'mkb_%'")
        tables = {str(row["name"]) for row in table_rows}
        columns: dict[str, set[str]] = {}
        for table in EXPECTED_TABLES:
            rows = await tx.fetchall(f"PRAGMA table_info({table})")
            columns[table] = {str(row["name"]) for row in rows}
    return tables, columns


@pytest.mark.asyncio
async def test_empty_database_expand_has_sqlite_turso_parity(tmp_path: Path) -> None:
    sqlite = SqlitePersistence(tmp_path / "empty-sqlite.db", MIGRATIONS)
    turso = TursoPersistence(
        tmp_path / "empty-turso.db",
        MIGRATIONS,
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await sqlite.migrate()
        await turso.migrate()
        sqlite_tables, sqlite_columns = await _schema(sqlite)
        turso_tables, turso_columns = await _schema(turso)
        assert EXPECTED_TABLES <= sqlite_tables
        assert EXPECTED_TABLES <= turso_tables
        assert sqlite_columns == turso_columns
        assert {row.migration_id for row in discover_migrations(MIGRATIONS)} >= {
            "025_nhx1_observation_item_epoch",
            "026_nhx1_object_sessions_cleanup",
            "027_nhx1_evidence_v2",
            "028_nhx1_ops_contracts",
        }
    finally:
        await sqlite.close()
        await turso.close()


@pytest.mark.asyncio
async def test_prefx_024_database_migrates_forward_without_fabricating_history(tmp_path: Path) -> None:
    database = tmp_path / "pre-fix-024.db"
    shutil.copyfile(FIXTURE, database)
    persistence = SqlitePersistence(database, MIGRATIONS)
    try:
        async with persistence.read_snapshot() as tx:
            before_selection = await tx.fetchone("SELECT * FROM mkb_workflow_selected_outputs")
            before_pending = await tx.fetchone(
                "SELECT reference_uuid,owner_uuid,purpose,released_at FROM mkb_object_references"
            )
        await persistence.migrate()
        await persistence.migrate()
        async with persistence.read_snapshot() as tx:
            after_selection = await tx.fetchone("SELECT * FROM mkb_workflow_selected_outputs")
            after_pending = await tx.fetchone(
                "SELECT reference_uuid,owner_uuid,purpose,released_at FROM mkb_object_references"
            )
            ledger = await tx.fetchall("SELECT migration_id FROM mkb_schema_migrations ORDER BY migration_id")
            fabricated = {
                "observations": (await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_intake_observations"))["count"],
                "sessions": (await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_object_upload_sessions"))["count"],
                "bindings": (await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_processing_binding_assertions"))[
                    "count"
                ],
                "selection_v2": (await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_selection_assertions_v2"))[
                    "count"
                ],
            }
        assert before_selection == after_selection
        assert before_pending == after_pending
        assert len(ledger) == 28 and ledger[-1]["migration_id"] == "028_nhx1_ops_contracts"
        assert fabricated == {"observations": 0, "sessions": 0, "bindings": 0, "selection_v2": 0}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_schema_constraints_and_append_only_triggers_reject_attacks(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "constraints.db", MIGRATIONS)
    await persistence.migrate()
    try:
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
                ("team", "team", stable_digest({"team": "team"}), NOW, NOW),
            )
            await tx.execute(
                "INSERT INTO mkb_evidence_verifications(verification_uuid,team_uuid,evidence_kind,evidence_uuid,"
                "verdict,reason_code,verifier_key,verifier_version,checked_at) VALUES (?,?,?,?,?,?,?,?,?)",
                ("verification", "team", "selected_output", "legacy", "legacy_unverifiable", "legacy", "nhx1", "v1", NOW),
            )
            acceptance_table = await tx.fetchone(
                "SELECT sql FROM sqlite_master WHERE type='table' AND name='mkb_intake_acceptance_facts'"
            )
            assert acceptance_table is not None
            assert "resulting_item_epoch = expected_item_epoch + 1" in acceptance_table["sql"]
            assert "resulting_item_epoch = expected_item_epoch" in acceptance_table["sql"]
        with pytest.raises(sqlite3.IntegrityError, match="append-only"):
            async with persistence.transaction() as tx:
                await tx.execute(
                    "UPDATE mkb_evidence_verifications SET verdict='verified' WHERE verification_uuid='verification'"
                )
        with pytest.raises(sqlite3.IntegrityError):
            async with persistence.transaction() as tx:
                await tx.execute(
                    "INSERT INTO mkb_error_definitions(error_code,definition_version,category,http_status,retryable,"
                    "public_message,definition_digest,registered_at) VALUES (?,?,?,?,?,?,?,?)",
                    ("lower-case", "v2", "conflict", 409, 0, "bad", "a" * 64, NOW),
                )
        with pytest.raises(sqlite3.IntegrityError):
            async with persistence.transaction() as tx:
                await tx.execute(
                    "INSERT INTO mkb_object_upload_sessions(upload_session_uuid,team_uuid,session_token_hash,"
                    "idempotency_key,command_fingerprint,staging_id,state,expires_at,created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?)",
                    ("session", "team", "token", "key", "fingerprint", "stage", "unknown", NOW, NOW),
                )
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_migration_resume_and_shadow_mismatch_are_durable(tmp_path: Path) -> None:
    database = tmp_path / "resume.db"
    first = SqlitePersistence(database, MIGRATIONS)
    await first.migrate()
    service = Nhx1MigrationService(first)
    progress = await service.start_or_resume("observation-backfill", MigrationStage.BACKFILL)
    progress = await service.advance(
        "observation-backfill", expected_revision=progress.row_revision, cursor_value="row-100", processed_delta=100
    )
    await first.close()

    resumed_persistence = SqlitePersistence(database, MIGRATIONS)
    resumed = Nhx1MigrationService(resumed_persistence)
    try:
        progress = await resumed.start_or_resume("observation-backfill", MigrationStage.BACKFILL)
        assert progress.cursor_value == "row-100" and progress.processed_count == 100
        await resumed.record_shadow_mismatch(
            "observation-backfill",
            team_uuid=None,
            aggregate_kind="observation",
            aggregate_uuid_hash="a" * 64,
            old_digest="b" * 64,
            new_digest="c" * 64,
            mismatch_kind="projection_drift",
        )
        progress, unresolved = await resumed.snapshot("observation-backfill")
        assert progress.status is MigrationStatus.BLOCKED
        assert progress.mismatch_count == 1 and unresolved == 1
        with pytest.raises(ConflictError, match="Migration progress changed"):
            await resumed.advance(
                "observation-backfill",
                expected_revision=progress.row_revision,
                cursor_value="row-200",
                processed_delta=100,
            )
    finally:
        await resumed_persistence.close()


def test_code_owned_outbox_and_error_registries_are_closed() -> None:
    assert set(OUTBOX_KIND_DEFINITIONS) == {
        "wake_execution",
        "wake_process",
        "cancel_execution",
        "gate_decision",
        "vectorize_construct",
    }
    assert all(definition.attempt_budget >= 1 for definition in OUTBOX_KIND_DEFINITIONS.values())
    assert all(definition.definition_digest for definition in OUTBOX_KIND_DEFINITIONS.values())
    assert all(code == code.upper() and "-" not in code for code in ERROR_DEFINITIONS)
    assert len({definition.definition_digest for definition in ERROR_DEFINITIONS.values()}) == len(ERROR_DEFINITIONS)
    assert resolve_error_definition("ITEM_EPOCH_CONFLICT").retryable is True
    with pytest.raises(KeyError):
        resolve_error_definition("unregistered-error")


@pytest.mark.asyncio
async def test_governance_registry_roundtrip_and_digest_fence(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "registry.db", MIGRATIONS)
    await persistence.migrate()
    registry = GovernanceRegistryService(persistence)
    try:
        await registry.bootstrap()
        await registry.bootstrap()
        assert await registry.readiness()
        async with persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_error_definitions SET definition_digest=? WHERE error_code='ITEM_EPOCH_CONFLICT'",
                ("0" * 64,),
            )
        with pytest.raises(MkbError, match="Error definition conflicts"):
            await registry.bootstrap()
    finally:
        await persistence.close()
