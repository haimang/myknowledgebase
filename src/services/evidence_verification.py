"""Append-only legacy evidence verification and correction ledger."""

from __future__ import annotations

from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort


class EvidenceVerificationService:
    def __init__(self, persistence: PersistencePort) -> None:
        self._persistence = persistence

    async def verify(
        self,
        *,
        team_uuid: str,
        evidence_kind: str,
        evidence_uuid: str,
        formula_version: str | None,
        verifier_key: str,
        verifier_version: str,
        observed_digest: str | None,
        recomputed_digest: str | None,
        reason_code: str,
    ) -> dict[str, Any]:
        if not verifier_key or not verifier_version or not reason_code:
            raise MkbError("EVIDENCE_VERIFIER_INVALID", "Evidence verifier coordinates are invalid", 422)
        if observed_digest is not None and len(observed_digest) != 64:
            raise MkbError("EVIDENCE_DIGEST_INVALID", "Observed evidence digest is invalid", 422)
        if recomputed_digest is not None and len(recomputed_digest) != 64:
            raise MkbError("EVIDENCE_DIGEST_INVALID", "Recomputed evidence digest is invalid", 422)
        if observed_digest is not None and recomputed_digest is not None and observed_digest == recomputed_digest:
            verdict = "verified"
        elif recomputed_digest is None:
            verdict = "legacy_unverifiable"
        else:
            verdict = "invalid"
        async with self._persistence.transaction() as tx:
            existing = await tx.fetchone(
                "SELECT * FROM mkb_evidence_verifications WHERE team_uuid=? AND evidence_kind=? AND evidence_uuid=? "
                "AND verifier_key=? AND verifier_version=?",
                (team_uuid, evidence_kind, evidence_uuid, verifier_key, verifier_version),
            )
            if existing is not None:
                return dict(existing)
            verification_uuid = uuid7()
            await tx.execute(
                "INSERT INTO mkb_evidence_verifications(verification_uuid,team_uuid,evidence_kind,evidence_uuid,"
                "formula_version,verdict,reason_code,verifier_key,verifier_version,observed_digest,recomputed_digest,checked_at) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    verification_uuid,
                    team_uuid,
                    evidence_kind,
                    evidence_uuid,
                    formula_version,
                    verdict,
                    reason_code,
                    verifier_key,
                    verifier_version,
                    observed_digest,
                    recomputed_digest,
                    utc_now(),
                ),
            )
            row = await tx.fetchone(
                "SELECT * FROM mkb_evidence_verifications WHERE verification_uuid=?", (verification_uuid,)
            )
        assert row is not None
        return dict(row)

    async def correct(
        self,
        *,
        team_uuid: str,
        evidence_kind: str,
        evidence_uuid: str,
        correction_kind: str,
        corrected_assertion_uuid: str,
        corrected_digest: str,
        formula_version: str,
        reason_code: str,
    ) -> str:
        if len(corrected_digest) != 64:
            raise MkbError("EVIDENCE_DIGEST_INVALID", "Corrected evidence digest is invalid", 422)
        async with self._persistence.transaction() as tx:
            correction_uuid = uuid7()
            try:
                await tx.execute(
                    "INSERT INTO mkb_evidence_corrections(correction_uuid,team_uuid,evidence_kind,evidence_uuid,"
                    "correction_kind,corrected_assertion_uuid,corrected_digest,formula_version,reason_code,created_at) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?)",
                    (
                        correction_uuid,
                        team_uuid,
                        evidence_kind,
                        evidence_uuid,
                        correction_kind,
                        corrected_assertion_uuid,
                        corrected_digest,
                        formula_version,
                        reason_code,
                        utc_now(),
                    ),
                )
            except Exception as exc:
                if "UNIQUE" in str(exc).upper() or "constraint" in str(exc).lower():
                    existing = await tx.fetchone(
                        "SELECT correction_uuid FROM mkb_evidence_corrections WHERE evidence_kind=? AND evidence_uuid=? "
                        "AND corrected_assertion_uuid=?",
                        (evidence_kind, evidence_uuid, corrected_assertion_uuid),
                    )
                    if existing is not None:
                        return str(existing["correction_uuid"])
                raise
        return correction_uuid

    async def inventory(self, *, team_uuid: str | None = None) -> dict[str, int]:
        clauses = " WHERE team_uuid=?" if team_uuid else ""
        params = (team_uuid,) if team_uuid else ()
        async with self._persistence.read_snapshot() as tx:
            rows = await tx.fetchall(
                "SELECT verdict,COUNT(*) AS count FROM mkb_evidence_verifications"
                + clauses
                + " GROUP BY verdict",
                params,
            )
        return {str(row["verdict"]): int(row["count"]) for row in rows}


__all__ = ["EvidenceVerificationService"]
