"""NHX1-T26: shadow/cutover/retirement and legacy verification are durable."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import ConflictError, MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.persistence.nhx1_migration import MigrationStage, Nhx1MigrationService
from src.persistence.sqlite_port import SqlitePersistence
from src.services.evidence_verification import EvidenceVerificationService
from src.services.nhx1_cutover import Nhx1CutoverService


@pytest.mark.asyncio
async def test_shadow_mismatch_blocks_cutover_then_resolved_cutover_is_forward_only(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "cutover.db", Path("src/persistence/migrations"))
    await persistence.migrate()
    service = Nhx1CutoverService(persistence)
    migration = Nhx1MigrationService(persistence)
    try:
        shadow = await service.begin_shadow()
        await migration.start_or_resume("cutover-check", MigrationStage.VALIDATE)
        mismatch_uuid = await migration.record_shadow_mismatch(
            "cutover-check",
            team_uuid=None,
            aggregate_kind="task",
            aggregate_uuid_hash="a" * 64,
            old_digest="b" * 64,
            new_digest="c" * 64,
            mismatch_kind="projection_drift",
        )
        with pytest.raises(MkbError, match="Shadow mismatch"):
            await service.cutover(expected_revision=shadow.row_revision)
        await service.resolve_shadow_mismatch(mismatch_uuid, resolution_code="recomputed_v2")
        cutover = await service.cutover(expected_revision=shadow.row_revision)
        assert cutover.writer_mode == "v2_only"
        assert cutover.reader_mode == "v2"
        service.assert_writer_allowed(cutover, "v2")
        with pytest.raises(MkbError, match="writer is disabled"):
            service.assert_writer_allowed(cutover, "legacy")
        stopped = await service.stop_admission(expected_revision=cutover.row_revision)
        assert stopped.admission_enabled is False
        persisted = await service.ensure_state()
        assert persisted.writer_mode == "v2_only" and persisted.reader_mode == "v2"
        with pytest.raises(ConflictError):
            await service.stop_admission(expected_revision=cutover.row_revision)
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_legacy_verification_and_correction_are_append_only(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "evidence.db", Path("src/persistence/migrations"))
    await persistence.migrate()
    service = EvidenceVerificationService(persistence)
    try:
        async with persistence.transaction() as tx:
            team = uuid7()
            await tx.execute(
                "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
                (team, "legacy", stable_digest({"team": team}), "2026-08-31T00:00:00Z", "2026-08-31T00:00:00Z"),
            )
        invalid = await service.verify(
            team_uuid=team,
            evidence_kind="selected_output",
            evidence_uuid="legacy",
            formula_version="v1",
            verifier_key="nhx1",
            verifier_version="v1",
            observed_digest="a" * 64,
            recomputed_digest="b" * 64,
            reason_code="formula_drift",
        )
        assert invalid["verdict"] == "invalid"
        correction = await service.correct(
            team_uuid=team,
            evidence_kind="selected_output",
            evidence_uuid="legacy",
            correction_kind="recomputed",
            corrected_assertion_uuid=uuid7(),
            corrected_digest="c" * 64,
            formula_version="v2",
            reason_code="formula_recomputed",
        )
        assert correction
        counts = await service.inventory(team_uuid=team)
        assert counts == {"invalid": 1}
    finally:
        await persistence.close()
