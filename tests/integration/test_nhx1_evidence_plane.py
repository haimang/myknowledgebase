"""NHX1-T17: legacy evidence is verified/corrected beside immutable rows."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence


@pytest.mark.asyncio
async def test_identity_update_delete_attacks_abort_and_corrections_append(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "evidence.db", Path("src/persistence/migrations"))
    await persistence.migrate()
    try:
        async with persistence.transaction() as tx:
            team_uuid = uuid7()
            await tx.execute(
                "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
                (team_uuid, "evidence", stable_digest({"team": team_uuid}), utc_now(), utc_now()),
            )
            stored = uuid7()
            await tx.execute(
                "INSERT INTO mkb_stored_objects(stored_object_uuid,team_uuid,content_digest,size_bytes,created_at) "
                "VALUES (?,?,?,?,?)",
                (stored, team_uuid, "a" * 64, 1, utc_now()),
            )
            await tx.execute(
                "INSERT INTO mkb_object_references(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,"
                "owner_uuid,expected_digest,expected_size,created_at) VALUES (?,?,?,'process_io','evidence','owner',?,?,?)",
                (uuid7(), team_uuid, stored, "a" * 64, 1, utc_now()),
            )
            verification = uuid7()
            await tx.execute(
                "INSERT INTO mkb_evidence_verifications(verification_uuid,team_uuid,evidence_kind,evidence_uuid,"
                "formula_version,verdict,reason_code,verifier_key,verifier_version,observed_digest,recomputed_digest,checked_at) "
                "VALUES (?,?,?,?,?,'legacy_unverifiable',?,?,?,?,?,?)",
                (
                    verification,
                    team_uuid,
                    "selected_output",
                    "legacy-selection",
                    "v1",
                    "legacy_unverifiable",
                    "nhx1",
                    "v1",
                    "a" * 64,
                    "b" * 64,
                    utc_now(),
                ),
            )
            correction = uuid7()
            await tx.execute(
                "INSERT INTO mkb_evidence_corrections(correction_uuid,team_uuid,evidence_kind,evidence_uuid,"
                "correction_kind,corrected_assertion_uuid,corrected_digest,formula_version,reason_code,created_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?)",
                (correction, team_uuid, "selected_output", "legacy-selection", "recomputed", uuid7(), "c" * 64, "v2", "formula_recomputed", utc_now()),
            )
        for sql in (
            "UPDATE mkb_evidence_verifications SET verdict='verified' WHERE verification_uuid=?",
            "DELETE FROM mkb_evidence_verifications WHERE verification_uuid=?",
            "UPDATE mkb_evidence_corrections SET corrected_digest=? WHERE correction_uuid=?",
            "DELETE FROM mkb_evidence_corrections WHERE correction_uuid=?",
        ):
            with pytest.raises(sqlite3.IntegrityError):
                async with persistence.transaction() as tx:
                    if sql.startswith("UPDATE mkb_evidence_corrections"):
                        await tx.execute(sql, ("d" * 64, correction))
                    else:
                        await tx.execute(sql, (verification if "verifications" in sql else correction,))
        async with persistence.read_snapshot() as tx:
            rows = await tx.fetchall(
                "SELECT verdict FROM mkb_evidence_verifications WHERE verification_uuid=?", (verification,)
            )
            corrections = await tx.fetchall(
                "SELECT correction_uuid FROM mkb_evidence_corrections WHERE correction_uuid=?", (correction,)
            )
        assert rows == [{"verdict": "legacy_unverifiable"}]
        assert corrections == [{"correction_uuid": correction}]
    finally:
        await persistence.close()
