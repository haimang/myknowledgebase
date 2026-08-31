"""NHX1-T02: the non-empty migration-024 input fixture is immutable and real."""

from __future__ import annotations

import ast
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from src.persistence.nhx1_migration import MigrationStage, Nhx1MigrationService
from src.persistence.sqlite_port import SqlitePersistence

ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests/fixtures/new_harvest_nhx1"


def test_prefx_fixture_checksum_and_builder_independence() -> None:
    database = FIXTURES / "pre-fix-024.db"
    expected = (FIXTURES / "pre-fix-024.sha256").read_text(encoding="utf-8").split()[0]
    assert hashlib.sha256(database.read_bytes()).hexdigest() == expected
    builder = (FIXTURES / "build_prefx_fixture.py").read_text(encoding="utf-8")
    imports = {
        node.module
        for node in ast.walk(ast.parse(builder))
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }
    assert "src.workflows.kind_family" not in imports
    assert "canonical_definition" in builder


@pytest.mark.asyncio
async def test_prefx_024_database_contains_rev1_and_legacy_rows(tmp_path: Path) -> None:
    target = tmp_path / "pre-fix-024.db"
    shutil.copyfile(FIXTURES / "pre-fix-024.db", target)
    persistence = SqlitePersistence(target, ROOT / "src/persistence/migrations")
    manifest = json.loads((FIXTURES / "rev1-manifest.json").read_text(encoding="utf-8"))
    try:
        async with persistence.read_snapshot() as tx:
            migrations = await tx.fetchall(
                "SELECT migration_id,checksum,applied_at FROM mkb_schema_migrations ORDER BY migration_id"
            )
            workflows = await tx.fetchall(
                "SELECT r.workflow_key,v.revision_number,v.registration_fingerprint,v.compiled_digest "
                "FROM mkb_workflow_registry r JOIN mkb_workflow_revisions v "
                "ON v.workflow_revision_uuid=r.active_revision_uuid ORDER BY r.workflow_key"
            )
            selection = await tx.fetchone(
                "SELECT control_version,output_manifest_digest,selection_digest "
                "FROM mkb_workflow_selected_outputs WHERE control_step_key='selected_clean'"
            )
            pending = await tx.fetchone(
                "SELECT purpose,owner_kind,released_at FROM mkb_object_references WHERE purpose='upload_pending'"
            )
            execution = await tx.fetchone("SELECT actual_binding_state,status FROM mkb_executions")
        assert len(migrations) == 24
        assert migrations[-1]["migration_id"] == "024_nh_review_invariants"
        assert {row["applied_at"] for row in migrations} == {"2026-08-31T00:00:00Z"}
        expected = {
            (
                row["workflow_key"],
                row["revision_number"],
                row["registration_fingerprint"],
                row["compiled_digest"],
            )
            for row in manifest["workflows"]
        }
        observed = {
            (
                row["workflow_key"],
                row["revision_number"],
                row["registration_fingerprint"],
                row["compiled_digest"],
            )
            for row in workflows
        }
        assert observed == expected
        assert selection == {
            "control_version": "mkb.selected-output.v1",
            "output_manifest_digest": "a" * 64,
            "selection_digest": "c" * 64,
        }
        assert pending == {"purpose": "upload_pending", "owner_kind": "public_upload", "released_at": None}
        assert execution == {"actual_binding_state": "legacy_unverifiable", "status": "failed"}
    finally:
        await persistence.close()


def test_rev1_manifest_digest_is_self_authenticating() -> None:
    manifest = json.loads((FIXTURES / "rev1-manifest.json").read_text(encoding="utf-8"))
    digest = manifest.pop("manifest_digest")
    canonical = json.dumps(manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == digest
    assert manifest["source_commit"] == "ba099ee305577cca2281a669afbca364111f200b"
    assert len(manifest["workflows"]) == 3
    assert {row["revision_number"] for row in manifest["workflows"]} == {1}


@pytest.mark.asyncio
async def test_prefx_024_database_migrates_forward(tmp_path: Path) -> None:
    target = tmp_path / "upgrade.db"
    shutil.copyfile(FIXTURES / "pre-fix-024.db", target)
    persistence = SqlitePersistence(target, ROOT / "src/persistence/migrations")
    try:
        await persistence.migrate()
        async with persistence.read_snapshot() as tx:
            ledger = await tx.fetchall("SELECT migration_id FROM mkb_schema_migrations ORDER BY migration_id")
            tables = await tx.fetchall("SELECT name FROM sqlite_master WHERE type='table'")
        assert len(ledger) == 28
        assert ledger[-1]["migration_id"] == "028_nhx1_ops_contracts"
        assert "mkb_intake_observations" in {row["name"] for row in tables}
        assert "mkb_publication_manifests" in {row["name"] for row in tables}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_migration_resume_is_idempotent(tmp_path: Path) -> None:
    database = tmp_path / "resume.db"
    persistence = SqlitePersistence(database, ROOT / "src/persistence/migrations")
    await persistence.migrate()
    service = Nhx1MigrationService(persistence)
    progress = await service.start_or_resume("nhx1-fixture", MigrationStage.BACKFILL)
    progress = await service.advance(
        "nhx1-fixture", expected_revision=progress.row_revision, cursor_value="cursor-1", processed_delta=1
    )
    await persistence.close()
    reopened = SqlitePersistence(database, ROOT / "src/persistence/migrations")
    try:
        service = Nhx1MigrationService(reopened)
        resumed = await service.start_or_resume("nhx1-fixture", MigrationStage.BACKFILL)
        assert resumed == progress
    finally:
        await reopened.close()


@pytest.mark.asyncio
async def test_legacy_rows_are_not_fabricated(tmp_path: Path) -> None:
    target = tmp_path / "legacy.db"
    shutil.copyfile(FIXTURES / "pre-fix-024.db", target)
    persistence = SqlitePersistence(target, ROOT / "src/persistence/migrations")
    try:
        async with persistence.read_snapshot() as tx:
            before = await tx.fetchone("SELECT * FROM mkb_workflow_selected_outputs")
        await persistence.migrate()
        async with persistence.read_snapshot() as tx:
            after = await tx.fetchone("SELECT * FROM mkb_workflow_selected_outputs")
            counts = [
                (await tx.fetchone(f"SELECT COUNT(*) AS count FROM {table}"))["count"]
                for table in (
                    "mkb_intake_observations",
                    "mkb_object_upload_sessions",
                    "mkb_processing_binding_assertions",
                    "mkb_selection_assertions_v2",
                    "mkb_evidence_corrections",
                )
            ]
        assert after == before
        assert counts == [0, 0, 0, 0, 0]
    finally:
        await persistence.close()
