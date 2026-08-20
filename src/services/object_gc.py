"""Reference-first S13 orphan collection.

The scanner deliberately owns neither a business lifecycle nor reference
release.  Its only authority is to remove *already unowned* local CAS bytes
after the grace window, recording immutable physical-delete evidence in the
same database transaction that tombstones the catalogue row.

Physical unlink runs *outside* the persistence write lock. TX1 rechecks
blockers; bytes are renamed to a quarantine path after that transaction
commits; TX2 rechecks again then writes proof + tombstone and destroys the
quarantine. If TX2 sees a new live reference, the quarantine is restored so
the catalogue never points at missing bytes.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.storage.models import ObjectHandle
from src.persistence.ports import PersistencePort, UnitOfWork
from src.storage.ports import ObjectStorePort


class ObjectGcDisposition(StrEnum):
    """One safe terminal observation for a catalogued CAS candidate."""

    DELETED = "deleted"
    STALE = "stale"
    LIVE_REFERENCE = "live_reference"
    HOLD = "hold"
    CLEANUP_FENCE = "cleanup_fence"
    DUPLICATE_CATALOG = "duplicate_catalog"
    MISSING_BYTES = "missing_bytes"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class ObjectGcCandidate:
    """A read-only candidate snapshot; it must be rechecked before unlink."""

    team_uuid: str
    stored_object_uuid: str
    content_digest: str
    size_bytes: int
    created_at: str
    media_type: str | None

    @property
    def handle(self) -> ObjectHandle:
        # The current v1 local adapter resolves the opaque CAS reference by
        # Team + digest.  No filesystem location crosses this boundary.
        return ObjectHandle(value=f"mkbobj:v1:{self.team_uuid}:{self.content_digest}")


@dataclass(frozen=True, slots=True)
class ObjectGcCandidateResult:
    candidate: ObjectGcCandidate
    disposition: ObjectGcDisposition
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class ObjectGcScanResult:
    scanner_id: str
    results: tuple[ObjectGcCandidateResult, ...]

    @property
    def candidate_count(self) -> int:
        return len(self.results)

    @property
    def deleted_count(self) -> int:
        return sum(result.disposition is ObjectGcDisposition.DELETED for result in self.results)

    @property
    def fenced_count(self) -> int:
        fenced = {
            ObjectGcDisposition.LIVE_REFERENCE,
            ObjectGcDisposition.HOLD,
            ObjectGcDisposition.CLEANUP_FENCE,
            ObjectGcDisposition.DUPLICATE_CATALOG,
        }
        return sum(result.disposition in fenced for result in self.results)

    @property
    def error_count(self) -> int:
        return sum(result.disposition is ObjectGcDisposition.ERROR for result in self.results)


class ObjectGcService:
    """Collect only catalogued, grace-expired, reference-free local CAS bytes.

    Reference release belongs to the owning S03/S04/S06 domain.  This service
    therefore never derives eligibility from a Task, Process, pointer, or
    payload blob.  The S13 reference ledger and explicit cleanup fences are
    the sole deletion authority.
    """

    def __init__(
        self,
        persistence: PersistencePort,
        storage: ObjectStorePort,
        *,
        orphan_grace: timedelta = timedelta(hours=24),
        scanner_id: str | None = None,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if orphan_grace <= timedelta(0):
            # S13-T026: zero grace would turn a rollback/orphan race into a
            # destructive path.  Reject it at construction rather than
            # quietly accepting an unsafe scanner configuration.
            raise ValueError("object orphan grace must be greater than zero")
        if scanner_id is not None and (not scanner_id.strip() or len(scanner_id) > 128):
            raise ValueError("scanner_id must be a non-empty value of at most 128 characters")
        self._persistence = persistence
        self._storage = storage
        self._orphan_grace = orphan_grace
        self._scanner_id = scanner_id or f"object-gc:{uuid7()}"
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def scanner_id(self) -> str:
        return self._scanner_id

    async def collect_candidates(self, *, limit: int = 100) -> tuple[ObjectGcCandidate, ...]:
        """Return a bounded stale snapshot of eligible-looking candidates.

        The result deliberately grants no deletion permission.  Each item is
        re-read under the delete fence by :meth:`delete_candidate`, which also
        makes this method useful to controlled maintenance callers.
        """

        if not 1 <= limit <= 10_000:
            raise ValueError("object GC limit must be between 1 and 10000")
        cutoff = self._timestamp(self._now() - self._orphan_grace)
        async with self._persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT o.team_uuid,o.stored_object_uuid,o.content_digest,o.size_bytes,o.created_at,o.media_type "
                "FROM mkb_stored_objects AS o "
                "WHERE o.tombstoned_at IS NULL "
                "AND o.digest_algorithm='sha256' "
                "AND o.storage_backend='local_fs' "
                "AND o.created_at <= ? "
                "AND NOT EXISTS ("
                "  SELECT 1 FROM mkb_object_references AS r "
                "  WHERE r.team_uuid=o.team_uuid "
                "    AND r.stored_object_uuid=o.stored_object_uuid "
                "    AND r.released_at IS NULL"
                ") "
                "ORDER BY o.created_at,o.stored_object_uuid LIMIT ?",
                (cutoff, limit),
            )
        return tuple(self._candidate_from_row(row) for row in rows)

    async def scan_once(self, *, limit: int = 100) -> ObjectGcScanResult:
        """Run one bounded scan, leaving every uncertainty catalogued/live."""

        candidates = await self.collect_candidates(limit=limit)
        results: list[ObjectGcCandidateResult] = []
        for candidate in candidates:
            try:
                results.append(await self.delete_candidate(candidate))
            except asyncio.CancelledError:
                raise
            except MkbError as exc:
                # A storage or post-unlink fence failure must not be converted
                # into a tombstone.  The caller receives a bounded code for
                # metrics/alerts while the live catalogue row remains intact.
                results.append(ObjectGcCandidateResult(candidate, ObjectGcDisposition.ERROR, error_code=exc.code))
            except Exception:
                # Do not leak backend details from a maintenance result.
                results.append(
                    ObjectGcCandidateResult(
                        candidate,
                        ObjectGcDisposition.ERROR,
                        error_code="OBJECT_UNAVAILABLE_GC",
                    )
                )
        return ObjectGcScanResult(scanner_id=self._scanner_id, results=tuple(results))

    async def delete_candidate(self, candidate: ObjectGcCandidate) -> ObjectGcCandidateResult:
        """Recheck fences, unlink bytes, then atomically prove + tombstone.

        There is intentionally no pre-emptive tombstone: a false/missing
        physical delete leaves the catalog live so verified readers report a
        missing object instead of silently treating it as retired.
        """

        async with self._persistence.transaction() as tx:
            current = await tx.fetchone(
                "SELECT team_uuid,stored_object_uuid,content_digest,size_bytes,created_at,media_type,"
                "digest_algorithm,storage_backend,tombstoned_at "
                "FROM mkb_stored_objects WHERE team_uuid=? AND stored_object_uuid=?",
                (candidate.team_uuid, candidate.stored_object_uuid),
            )
            if not self._same_catalogue_row(candidate, current):
                return ObjectGcCandidateResult(candidate, ObjectGcDisposition.STALE)
            if not self._is_grace_expired(candidate.created_at):
                # ``delete_candidate`` is intentionally public to controlled
                # maintenance callers, so it repeats the grace check instead
                # of trusting that the candidate came from collect_candidates.
                return ObjectGcCandidateResult(candidate, ObjectGcDisposition.STALE)

            blocker = await self._delete_blocker_tx(tx, candidate)
            if blocker is not None:
                return ObjectGcCandidateResult(candidate, blocker)

        quarantined = await self._quarantine_candidate(candidate)
        if not quarantined:
            return ObjectGcCandidateResult(candidate, ObjectGcDisposition.MISSING_BYTES)

        blocked: ObjectGcDisposition | None = None
        conflict_code = ""
        deleted = False
        try:
            async with self._persistence.transaction() as tx:
                current = await tx.fetchone(
                    "SELECT team_uuid,stored_object_uuid,content_digest,size_bytes,created_at,media_type,"
                    "digest_algorithm,storage_backend,tombstoned_at "
                    "FROM mkb_stored_objects WHERE team_uuid=? AND stored_object_uuid=?",
                    (candidate.team_uuid, candidate.stored_object_uuid),
                )
                if not self._same_catalogue_row(candidate, current):
                    conflict_code = "OBJECT_CONFLICT_DELETE_FENCE"
                    raise MkbError(
                        conflict_code,
                        "Object catalogue changed during physical unlink",
                        409,
                    )
                blocker = await self._delete_blocker_tx(tx, candidate)
                if blocker is not None:
                    blocked = blocker
                else:
                    unlinked_at = self._timestamp(self._now())
                    fence_digest = self._delete_fence_digest(candidate)
                    await tx.execute(
                        "INSERT INTO mkb_object_delete_proofs "
                        "(delete_proof_uuid,team_uuid,stored_object_uuid,content_digest,size_bytes,delete_fence_digest,"
                        "unlinked_at,scanner_id,payload_extra) VALUES (?,?,?,?,?,?,?,?, '{}')",
                        (
                            uuid7(),
                            candidate.team_uuid,
                            candidate.stored_object_uuid,
                            candidate.content_digest,
                            candidate.size_bytes,
                            fence_digest,
                            unlinked_at,
                            self._scanner_id,
                        ),
                    )
                    updated = await tx.execute(
                        "UPDATE mkb_stored_objects SET tombstoned_at=? "
                        "WHERE team_uuid=? AND stored_object_uuid=? AND tombstoned_at IS NULL",
                        (unlinked_at, candidate.team_uuid, candidate.stored_object_uuid),
                    )
                    if updated.rowcount != 1:
                        conflict_code = "OBJECT_CONFLICT_DELETE_TOMBSTONE"
                        raise MkbError(
                            conflict_code,
                            "Object catalogue changed during physical unlink",
                            409,
                        )
                    deleted = True
        except MkbError:
            await self._restore_candidate(candidate)
            raise
        if blocked is not None:
            await self._restore_candidate(candidate)
            return ObjectGcCandidateResult(candidate, blocked)
        if deleted:
            await self._destroy_candidate(candidate)
            return ObjectGcCandidateResult(candidate, ObjectGcDisposition.DELETED)
        await self._restore_candidate(candidate)
        raise MkbError("OBJECT_CONFLICT_DELETE_FENCE", "Object catalogue changed during physical unlink", 409)

    async def _quarantine_candidate(self, candidate: ObjectGcCandidate) -> bool:
        quarantine = getattr(self._storage, "quarantine_object", None)
        if callable(quarantine):
            return bool(await quarantine(candidate.team_uuid, candidate.handle))
        return bool(await self._storage.delete_if_unreferenced(candidate.team_uuid, candidate.handle))

    async def _restore_candidate(self, candidate: ObjectGcCandidate) -> None:
        restore = getattr(self._storage, "restore_quarantined", None)
        if callable(restore):
            await restore(candidate.team_uuid, candidate.handle)

    async def _destroy_candidate(self, candidate: ObjectGcCandidate) -> None:
        destroy = getattr(self._storage, "destroy_quarantined", None)
        if callable(destroy):
            await destroy(candidate.team_uuid, candidate.handle)

    async def _delete_blocker_tx(self, tx: UnitOfWork, candidate: ObjectGcCandidate) -> ObjectGcDisposition | None:
        """Return a conservative fence result using durable tables only."""

        # Local CAS is physically keyed by Team+digest.  The intended schema
        # has one row per such object; until a deployment's catalogue proves
        # that invariant, duplicate non-tombstoned rows are unsafe to unlink.
        duplicate = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_stored_objects "
            "WHERE team_uuid=? AND content_digest=? AND tombstoned_at IS NULL",
            (candidate.team_uuid, candidate.content_digest),
        )
        if duplicate is None or int(duplicate["count"]) != 1:
            return ObjectGcDisposition.DUPLICATE_CATALOG

        reference = await tx.fetchone(
            "SELECT purpose FROM mkb_object_references "
            "WHERE team_uuid=? AND stored_object_uuid=? AND released_at IS NULL "
            "ORDER BY created_at,reference_uuid LIMIT 1",
            (candidate.team_uuid, candidate.stored_object_uuid),
        )
        if reference is not None:
            if reference["purpose"] in {"operator_hold", "backup_hold"}:
                return ObjectGcDisposition.HOLD
            return ObjectGcDisposition.LIVE_REFERENCE

        if await self._has_cleanup_fence_tx(tx, candidate):
            return ObjectGcDisposition.CLEANUP_FENCE
        return None

    async def _has_cleanup_fence_tx(self, tx: UnitOfWork, candidate: ObjectGcCandidate) -> bool:
        """Check explicit open cleanup holds without guessing business state.

        S04 stores a generic cleanup ledger rather than an object-only table.
        We therefore honour only explicit object coordinates in its frozen
        hold/target/reference fields.  A malformed ``hold_refs_json`` is an
        unknown fence and blocks collection for that Team rather than being
        silently ignored.
        """

        intents = await tx.fetchall(
            "SELECT intent_uuid,target_ref,hold_refs_json,reference_snapshot_ref "
            "FROM mkb_intake_cleanup_intents WHERE team_uuid=? AND status='open' "
            "ORDER BY requested_at,intent_uuid",
            (candidate.team_uuid,),
        )
        for intent in intents:
            hold_refs = intent["hold_refs_json"]
            try:
                decoded = json.loads(hold_refs)
            except (TypeError, json.JSONDecodeError):
                return True
            if not isinstance(decoded, list):
                return True
            if self._mentions_candidate(decoded, candidate):
                return True
            if self._mentions_candidate(intent["target_ref"], candidate):
                return True
            if self._mentions_candidate(intent["reference_snapshot_ref"], candidate):
                return True
        return False

    @staticmethod
    def _mentions_candidate(value: Any, candidate: ObjectGcCandidate) -> bool:
        """Find an explicit logical-object coordinate in a cleanup field."""

        acceptable = {
            candidate.stored_object_uuid,
            candidate.content_digest,
            candidate.handle.value,
            f"stored_object:{candidate.stored_object_uuid}",
            f"object:{candidate.stored_object_uuid}",
            f"sha256:{candidate.content_digest}",
        }
        if isinstance(value, str):
            return value in acceptable
        if isinstance(value, Mapping):
            return any(ObjectGcService._mentions_candidate(item, candidate) for item in value.values())
        if isinstance(value, list | tuple):
            return any(ObjectGcService._mentions_candidate(item, candidate) for item in value)
        return False

    def _delete_fence_digest(self, candidate: ObjectGcCandidate) -> str:
        """Bind the proof to the exact pre-unlink CAS coordinate and scanner."""

        return stable_digest(
            {
                "schema_version": "mkb.object-delete-fence.v1",
                "scanner_id": self._scanner_id,
                "team_uuid": candidate.team_uuid,
                "stored_object_uuid": candidate.stored_object_uuid,
                "content_digest": candidate.content_digest,
                "size_bytes": candidate.size_bytes,
                "catalogued_at": candidate.created_at,
                "live_reference_count": 0,
            }
        )

    @staticmethod
    def _candidate_from_row(row: Mapping[str, Any]) -> ObjectGcCandidate:
        return ObjectGcCandidate(
            team_uuid=str(row["team_uuid"]),
            stored_object_uuid=str(row["stored_object_uuid"]),
            content_digest=str(row["content_digest"]),
            size_bytes=int(row["size_bytes"]),
            created_at=str(row["created_at"]),
            media_type=None if row["media_type"] is None else str(row["media_type"]),
        )

    @staticmethod
    def _same_catalogue_row(candidate: ObjectGcCandidate, row: Mapping[str, Any] | None) -> bool:
        return bool(
            row
            and row["tombstoned_at"] is None
            and row["digest_algorithm"] == "sha256"
            and row["storage_backend"] == "local_fs"
            and row["team_uuid"] == candidate.team_uuid
            and row["stored_object_uuid"] == candidate.stored_object_uuid
            and row["content_digest"] == candidate.content_digest
            and int(row["size_bytes"]) == candidate.size_bytes
            and row["created_at"] == candidate.created_at
        )

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("object GC clock must return an aware UTC timestamp")
        return now.astimezone(UTC)

    def _is_grace_expired(self, created_at: str) -> bool:
        try:
            parsed = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
        except ValueError:
            return False
        if parsed.tzinfo is None:
            return False
        return parsed.astimezone(UTC) <= self._now() - self._orphan_grace

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


__all__ = [
    "ObjectGcCandidate",
    "ObjectGcCandidateResult",
    "ObjectGcDisposition",
    "ObjectGcScanResult",
    "ObjectGcService",
]
