"""Fenced S09 retirement of superseded index generations.

An ``mkb_index_active_pointers`` row is the serving alias only.  It deliberately
does not carry lifecycle truth for generations that are no longer active.  This
service records those old-generation retirements in the existing S04 cleanup
intent/proof ledger, freezes a grace deadline at cutover, and soft-deletes rows
only after rechecking the live pointer in the same transaction.

The service never creates an IntakeRevision, changes an IntakeItem lifecycle,
or touches generation-artifact bytes.  It owns only the S09 projection cleanup
for an already superseded ``index_generation``.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.persistence.ports import PersistencePort, UnitOfWork

RETIREMENT_POLICY_REF = "mkb.retention.index-generation.v1"
RETIREMENT_TARGET_KIND = "index_generation"
_RETIREMENT_TARGET_PREFIX = "index-generation:v1"
_REQUIRED_SUBSTRATE_SET_DIGEST = stable_digest(
    {
        "schema_version": "mkb.index-generation-retirement-substrates.v1",
        "substrates": ("vector_projection_soft_delete",),
    }
)


class IndexGenerationRetirementDisposition(StrEnum):
    """One bounded outcome for a due retirement attempt."""

    SOFT_PURGED = "soft_purged"
    NOT_DUE = "not_due"
    STALE = "stale"
    ACTIVE_GENERATION = "active_generation"
    POINTER_UNAVAILABLE = "pointer_unavailable"
    INVALID_TARGET = "invalid_target"
    ABANDONED = "abandoned"
    ERROR = "error"


@dataclass(frozen=True, slots=True)
class IndexGenerationRetirementIntent:
    """The durable S09 cleanup intent, projected from the generic ledger."""

    intent_uuid: str
    team_uuid: str
    intake_item_uuid: str
    namespace_uuid: str
    retired_index_generation: int
    eligible_at: str
    requested_at: str
    reference_snapshot_ref: str | None


@dataclass(frozen=True, slots=True)
class IndexGenerationRetirementCandidate:
    """A stale read of one due intent; it grants no delete permission."""

    intent_uuid: str
    team_uuid: str
    target_ref: str
    eligible_at: str
    requested_at: str


@dataclass(frozen=True, slots=True)
class IndexGenerationRetirementResult:
    intent_uuid: str
    disposition: IndexGenerationRetirementDisposition
    soft_deleted_count: int = 0
    error_code: str | None = None


@dataclass(frozen=True, slots=True)
class IndexGenerationRetirementScanResult:
    discovered_count: int
    results: tuple[IndexGenerationRetirementResult, ...]

    @property
    def soft_purged_count(self) -> int:
        return sum(result.disposition is IndexGenerationRetirementDisposition.SOFT_PURGED for result in self.results)

    @property
    def soft_deleted_count(self) -> int:
        return sum(result.soft_deleted_count for result in self.results)


class IndexGenerationRetirementService:
    """Apply S09's ``CAS → grace → soft-delete`` retirement discipline.

    ``grace`` is frozen into each cleanup intent's ``eligible_at`` column.
    This makes a later configuration change prospective rather than silently
    shortening a rollback window that was already committed at cutover.
    """

    def __init__(
        self,
        persistence: PersistencePort,
        *,
        grace: timedelta = timedelta(hours=1),
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if grace <= timedelta(0):
            # A zero window would turn a pointer cutover into an immediate,
            # irreversible substrate mutation and defeats S09-T023/T026.
            raise ValueError("index generation retirement grace must be greater than zero")
        self._persistence = persistence
        self._grace = grace
        self._clock = clock or (lambda: datetime.now(UTC))

    @property
    def grace(self) -> timedelta:
        return self._grace

    async def schedule_retirement(
        self,
        *,
        team_uuid: str,
        intake_item_uuid: str,
        namespace_uuid: str,
        retired_index_generation: int,
        successor_index_generation: int,
        expected_pointer_row_revision: int,
        trace_uuid: str | None = None,
        cutover_at: datetime | None = None,
    ) -> IndexGenerationRetirementIntent:
        """Durably schedule retirement after a successful active-pointer CAS.

        A caller should invoke :meth:`schedule_retirement_tx` in the same
        transaction as its pointer CAS.  The public wrapper is useful to a
        controlled reconciler and still requires the current pointer fence.
        """

        async with self._persistence.transaction() as tx:
            intent, _ = await self.schedule_retirement_tx(
                tx,
                team_uuid=team_uuid,
                intake_item_uuid=intake_item_uuid,
                namespace_uuid=namespace_uuid,
                retired_index_generation=retired_index_generation,
                successor_index_generation=successor_index_generation,
                expected_pointer_row_revision=expected_pointer_row_revision,
                trace_uuid=trace_uuid,
                cutover_at=cutover_at,
            )
            return intent

    async def schedule_retirement_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        intake_item_uuid: str,
        namespace_uuid: str,
        retired_index_generation: int,
        successor_index_generation: int,
        expected_pointer_row_revision: int,
        trace_uuid: str | None = None,
        cutover_at: datetime | None = None,
    ) -> tuple[IndexGenerationRetirementIntent, bool]:
        """Create one idempotent intent after verifying the promoted pointer.

        The returned flag is true only when this call inserted the durable
        intent.  Existing open intents keep their original frozen deadline.
        """

        self._validate_schedule(
            team_uuid=team_uuid,
            intake_item_uuid=intake_item_uuid,
            namespace_uuid=namespace_uuid,
            retired_index_generation=retired_index_generation,
            successor_index_generation=successor_index_generation,
            expected_pointer_row_revision=expected_pointer_row_revision,
        )
        pointer = await tx.fetchone(
            "SELECT p.active_index_generation,p.pointer_row_revision,p.lifecycle_state,p.generation_artifact_uuid,p.updated_at "
            "FROM mkb_index_active_pointers AS p "
            "JOIN mkb_vector_namespaces AS n ON n.namespace_uuid=p.namespace_uuid AND n.team_uuid=p.team_uuid "
            "JOIN mkb_intake_items AS i ON i.intake_item_uuid=p.intake_item_uuid AND i.team_uuid=p.team_uuid "
            "WHERE p.team_uuid=? AND p.intake_item_uuid=? AND p.namespace_uuid=? "
            "AND n.status='active' AND n.deleted_at IS NULL "
            "AND i.lifecycle_state='active' AND i.deleted_at IS NULL AND i.serving_revision_uuid IS NOT NULL",
            (team_uuid, intake_item_uuid, namespace_uuid),
        )
        if (
            pointer is None
            or pointer["lifecycle_state"] != "active"
            or int(pointer["active_index_generation"]) != successor_index_generation
            or int(pointer["pointer_row_revision"]) != expected_pointer_row_revision
        ):
            raise MkbError(
                "INDEX_RETIREMENT_POINTER_FENCE",
                "The active index pointer changed before its retirement intent was recorded",
                409,
            )

        effective_cutover = cutover_at or self._parse_timestamp(pointer["updated_at"])
        if effective_cutover is None:
            raise MkbError(
                "INDEX_RETIREMENT_CUTOVER_INVALID",
                "The active index pointer has no valid cutover timestamp",
                409,
            )
        target_ref = self.target_ref(intake_item_uuid, namespace_uuid, retired_index_generation)
        existing = await tx.fetchone(
            "SELECT intent_uuid,team_uuid,target_ref,eligible_at,requested_at,reference_snapshot_ref "
            "FROM mkb_intake_cleanup_intents "
            "WHERE team_uuid=? AND policy_ref=? AND target_kind=? AND target_ref=? AND status='open'",
            (team_uuid, RETIREMENT_POLICY_REF, RETIREMENT_TARGET_KIND, target_ref),
        )
        if existing is not None:
            return self._intent_from_row(existing), False

        requested_at = self._timestamp(effective_cutover)
        eligible_at = self._timestamp(effective_cutover + self._grace)
        intent_uuid = uuid7()
        snapshot_ref = self._pointer_snapshot_ref(
            team_uuid=team_uuid,
            intake_item_uuid=intake_item_uuid,
            namespace_uuid=namespace_uuid,
            retired_index_generation=retired_index_generation,
            successor_index_generation=successor_index_generation,
            pointer_row_revision=expected_pointer_row_revision,
            successor_generation_artifact_uuid=pointer["generation_artifact_uuid"],
        )
        await tx.execute(
            "INSERT INTO mkb_intake_cleanup_intents "
            "(intent_uuid,team_uuid,policy_ref,target_kind,target_ref,required_substrate_set_digest,hold_refs_json,"
            "reference_snapshot_ref,status,requested_trace_uuid,requested_at,eligible_at,payload_extra) "
            "VALUES (?,?,?,?,?,?, '[]',?,'open',?,?,?,'{}')",
            (
                intent_uuid,
                team_uuid,
                RETIREMENT_POLICY_REF,
                RETIREMENT_TARGET_KIND,
                target_ref,
                _REQUIRED_SUBSTRATE_SET_DIGEST,
                snapshot_ref,
                trace_uuid,
                requested_at,
                eligible_at,
            ),
        )
        return (
            IndexGenerationRetirementIntent(
                intent_uuid=intent_uuid,
                team_uuid=team_uuid,
                intake_item_uuid=intake_item_uuid,
                namespace_uuid=namespace_uuid,
                retired_index_generation=retired_index_generation,
                eligible_at=eligible_at,
                requested_at=requested_at,
                reference_snapshot_ref=snapshot_ref,
            ),
            True,
        )

    async def discover_retirements(self, *, limit: int = 100) -> int:
        """Backfill intents for existing cutovers without deleting anything.

        The service can be introduced after an index rebuild deployment.  It
        therefore derives only old, still-live generations from the active
        pointer and freezes the pointer's ``updated_at`` plus the configured
        grace.  A malformed timestamp is deliberately skipped: uncertainty
        extends retention rather than authorizing an early soft-delete.
        """

        self._validate_limit(limit)
        async with self._persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT p.team_uuid,p.intake_item_uuid,p.namespace_uuid,p.active_index_generation,"
                "p.pointer_row_revision,p.updated_at,r.index_generation AS retired_index_generation "
                "FROM mkb_index_active_pointers AS p "
                "JOIN mkb_vector_records AS r "
                "ON r.team_uuid=p.team_uuid AND r.intake_item_uuid=p.intake_item_uuid "
                "AND r.namespace_uuid=p.namespace_uuid "
                "JOIN mkb_vector_namespaces AS n ON n.namespace_uuid=p.namespace_uuid AND n.team_uuid=p.team_uuid "
                "JOIN mkb_intake_items AS i ON i.intake_item_uuid=p.intake_item_uuid AND i.team_uuid=p.team_uuid "
                "WHERE p.lifecycle_state='active' AND n.status='active' AND n.deleted_at IS NULL "
                "AND i.lifecycle_state='active' AND i.deleted_at IS NULL AND i.serving_revision_uuid IS NOT NULL "
                "AND r.deleted_at IS NULL "
                "AND r.index_generation < p.active_index_generation "
                "GROUP BY p.team_uuid,p.intake_item_uuid,p.namespace_uuid,p.active_index_generation,"
                "p.pointer_row_revision,p.updated_at,r.index_generation "
                "ORDER BY p.updated_at,p.team_uuid,p.intake_item_uuid,p.namespace_uuid,r.index_generation LIMIT ?",
                (limit,),
            )
            created = 0
            for row in rows:
                cutover_at = self._parse_timestamp(row["updated_at"])
                if cutover_at is None:
                    continue
                _, inserted = await self.schedule_retirement_tx(
                    tx,
                    team_uuid=str(row["team_uuid"]),
                    intake_item_uuid=str(row["intake_item_uuid"]),
                    namespace_uuid=str(row["namespace_uuid"]),
                    retired_index_generation=int(row["retired_index_generation"]),
                    successor_index_generation=int(row["active_index_generation"]),
                    expected_pointer_row_revision=int(row["pointer_row_revision"]),
                    cutover_at=cutover_at,
                )
                created += int(inserted)
            return created

    async def collect_due(self, *, limit: int = 100) -> tuple[IndexGenerationRetirementCandidate, ...]:
        """Return a bounded stale snapshot of due, still-open S09 intents."""

        self._validate_limit(limit)
        now = self._timestamp(self._now())
        async with self._persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT intent_uuid,team_uuid,target_ref,eligible_at,requested_at "
                "FROM mkb_intake_cleanup_intents "
                "WHERE policy_ref=? AND target_kind=? AND status='open' "
                "AND eligible_at IS NOT NULL AND eligible_at <= ? "
                "ORDER BY eligible_at,requested_at,intent_uuid LIMIT ?",
                (RETIREMENT_POLICY_REF, RETIREMENT_TARGET_KIND, now, limit),
            )
        return tuple(
            IndexGenerationRetirementCandidate(
                intent_uuid=str(row["intent_uuid"]),
                team_uuid=str(row["team_uuid"]),
                target_ref=str(row["target_ref"]),
                eligible_at=str(row["eligible_at"]),
                requested_at=str(row["requested_at"]),
            )
            for row in rows
        )

    async def scan_once(self, *, limit: int = 100) -> IndexGenerationRetirementScanResult:
        """Discover stale generations, then soft-purge only due fenced intents."""

        discovered = await self.discover_retirements(limit=limit)
        candidates = await self.collect_due(limit=limit)
        results: list[IndexGenerationRetirementResult] = []
        for candidate in candidates:
            try:
                results.append(await self.soft_purge(candidate))
            except asyncio.CancelledError:
                raise
            except MkbError as exc:
                results.append(
                    IndexGenerationRetirementResult(
                        intent_uuid=candidate.intent_uuid,
                        disposition=IndexGenerationRetirementDisposition.ERROR,
                        error_code=exc.code,
                    )
                )
            except Exception:
                results.append(
                    IndexGenerationRetirementResult(
                        intent_uuid=candidate.intent_uuid,
                        disposition=IndexGenerationRetirementDisposition.ERROR,
                        error_code="INDEX_RETIREMENT_UNAVAILABLE",
                    )
                )
        return IndexGenerationRetirementScanResult(discovered_count=discovered, results=tuple(results))

    async def soft_purge(
        self, candidate: IndexGenerationRetirementCandidate
    ) -> IndexGenerationRetirementResult:
        """Recheck the active pointer and soft-delete exactly one old index gen."""

        async with self._persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT intent_uuid,team_uuid,target_ref,eligible_at,requested_at,status "
                "FROM mkb_intake_cleanup_intents WHERE intent_uuid=?",
                (candidate.intent_uuid,),
            )
            if not self._same_candidate(candidate, row):
                return IndexGenerationRetirementResult(
                    intent_uuid=candidate.intent_uuid,
                    disposition=IndexGenerationRetirementDisposition.STALE,
                )
            if not self._is_due(row["eligible_at"]):
                return IndexGenerationRetirementResult(
                    intent_uuid=candidate.intent_uuid,
                    disposition=IndexGenerationRetirementDisposition.NOT_DUE,
                )
            target = self._parse_target_ref(str(row["target_ref"]))
            if target is None:
                return IndexGenerationRetirementResult(
                    intent_uuid=candidate.intent_uuid,
                    disposition=IndexGenerationRetirementDisposition.INVALID_TARGET,
                )
            intake_item_uuid, namespace_uuid, retired_generation = target
            pointer = await self._active_pointer_tx(
                tx,
                team_uuid=candidate.team_uuid,
                intake_item_uuid=intake_item_uuid,
                namespace_uuid=namespace_uuid,
            )
            if pointer is None:
                closed = await self._close_unavailable_intent_tx(
                    tx,
                    candidate,
                    intake_item_uuid=intake_item_uuid,
                    namespace_uuid=namespace_uuid,
                    retired_generation=retired_generation,
                )
                if closed is not None:
                    return closed
                return IndexGenerationRetirementResult(
                    intent_uuid=candidate.intent_uuid,
                    disposition=IndexGenerationRetirementDisposition.POINTER_UNAVAILABLE,
                )
            if int(pointer["active_index_generation"]) <= retired_generation:
                # A recovery/rollback can route back to this generation while
                # the grace intent is open.  Keep the intent open and let a
                # later, safely newer pointer make it eligible again.
                return IndexGenerationRetirementResult(
                    intent_uuid=candidate.intent_uuid,
                    disposition=IndexGenerationRetirementDisposition.ACTIVE_GENERATION,
                )

            now = self._timestamp(self._now())
            changed = await tx.execute(
                "UPDATE mkb_vector_records SET deleted_at=?,updated_at=? "
                "WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=? "
                "AND index_generation=? AND deleted_at IS NULL",
                (
                    now,
                    now,
                    candidate.team_uuid,
                    intake_item_uuid,
                    namespace_uuid,
                    retired_generation,
                ),
            )
            # The first pointer check guards the normal path.  A second read
            # turns an unexpected non-coordinated-store race into a rollback:
            # no proof or soft-delete may be committed if the alias changed.
            post_pointer = await self._active_pointer_tx(
                tx,
                team_uuid=candidate.team_uuid,
                intake_item_uuid=intake_item_uuid,
                namespace_uuid=namespace_uuid,
            )
            if post_pointer is None or int(post_pointer["active_index_generation"]) <= retired_generation:
                raise MkbError(
                    "INDEX_RETIREMENT_POINTER_FENCE",
                    "The active index pointer changed during old-generation soft-delete",
                    409,
                )

            soft_deleted_count = max(int(changed.rowcount), 0)
            proof_uuid = uuid7()
            proof_digest = stable_digest(
                {
                    "schema_version": "mkb.index-generation-cleanup-proof.v1",
                    "intent_uuid": candidate.intent_uuid,
                    "team_uuid": candidate.team_uuid,
                    "intake_item_uuid": intake_item_uuid,
                    "namespace_uuid": namespace_uuid,
                    "retired_index_generation": retired_generation,
                    "active_index_generation": int(post_pointer["active_index_generation"]),
                    "pointer_row_revision": int(post_pointer["pointer_row_revision"]),
                    "soft_deleted_count": soft_deleted_count,
                    "eligible_at": row["eligible_at"],
                    "soft_deleted_at": now,
                }
            )
            await tx.execute(
                "INSERT INTO mkb_intake_cleanup_proofs "
                "(proof_uuid,intent_uuid,team_uuid,substrate_kind,target_ref,target_digest,proof_kind,proof_digest,"
                "producer_execution_uuid,producer_process_uuid,verified_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?, ?,NULL,NULL,?,'{}')",
                (
                    proof_uuid,
                    candidate.intent_uuid,
                    candidate.team_uuid,
                    "vector_projection",
                    candidate.target_ref,
                    proof_digest,
                    "index_generation_soft_delete.v1",
                    proof_digest,
                    now,
                ),
            )
            completed = await tx.execute(
                "UPDATE mkb_intake_cleanup_intents SET status='completed',completed_at=?,completion_projection_ref=? "
                "WHERE intent_uuid=? AND status='open'",
                (now, f"mkb.cleanup-proof:v1:{proof_uuid}", candidate.intent_uuid),
            )
            if completed.rowcount != 1:
                raise MkbError(
                    "INDEX_RETIREMENT_INTENT_FENCE",
                    "The retirement intent changed during old-generation soft-delete",
                    409,
                )
        return IndexGenerationRetirementResult(
            intent_uuid=candidate.intent_uuid,
            disposition=IndexGenerationRetirementDisposition.SOFT_PURGED,
            soft_deleted_count=soft_deleted_count,
        )

    async def _close_unavailable_intent_tx(
        self,
        tx: UnitOfWork,
        candidate: IndexGenerationRetirementCandidate,
        *,
        intake_item_uuid: str,
        namespace_uuid: str,
        retired_generation: int,
    ) -> IndexGenerationRetirementResult | None:
        """Finish intents whose serving item is gone so they cannot occupy the due queue."""

        now = self._timestamp(self._now())
        await tx.execute(
            "UPDATE mkb_vector_records SET deleted_at=?,updated_at=? "
            "WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=? "
            "AND index_generation=? AND deleted_at IS NULL",
            (now, now, candidate.team_uuid, intake_item_uuid, namespace_uuid, retired_generation),
        )
        abandoned = await tx.execute(
            "UPDATE mkb_intake_cleanup_intents SET status='abandoned',completed_at=? "
            "WHERE intent_uuid=? AND status='open'",
            (now, candidate.intent_uuid),
        )
        if abandoned.rowcount != 1:
            raise MkbError(
                "INDEX_RETIREMENT_INTENT_FENCE",
                "The retirement intent changed while abandoning a missing item",
                409,
            )
        return IndexGenerationRetirementResult(
            intent_uuid=candidate.intent_uuid,
            disposition=IndexGenerationRetirementDisposition.ABANDONED,
        )

    async def _active_pointer_tx(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        intake_item_uuid: str,
        namespace_uuid: str,
    ) -> dict[str, object] | None:
        pointer = await tx.fetchone(
            "SELECT p.active_index_generation,p.pointer_row_revision,p.lifecycle_state "
            "FROM mkb_index_active_pointers AS p "
            "JOIN mkb_vector_namespaces AS n ON n.namespace_uuid=p.namespace_uuid AND n.team_uuid=p.team_uuid "
            "JOIN mkb_intake_items AS i ON i.intake_item_uuid=p.intake_item_uuid AND i.team_uuid=p.team_uuid "
            "WHERE p.team_uuid=? AND p.intake_item_uuid=? AND p.namespace_uuid=? "
            "AND n.status='active' AND n.deleted_at IS NULL "
            "AND i.lifecycle_state='active' AND i.deleted_at IS NULL AND i.serving_revision_uuid IS NOT NULL",
            (team_uuid, intake_item_uuid, namespace_uuid),
        )
        if pointer is None or pointer["lifecycle_state"] != "active":
            return None
        return pointer

    @staticmethod
    def target_ref(intake_item_uuid: str, namespace_uuid: str, retired_index_generation: int) -> str:
        if not intake_item_uuid or not namespace_uuid or ":" in intake_item_uuid or ":" in namespace_uuid:
            raise ValueError("index generation retirement coordinates are invalid")
        if (
            isinstance(retired_index_generation, bool)
            or not isinstance(retired_index_generation, int)
            or retired_index_generation < 0
        ):
            raise ValueError("retired_index_generation must be a non-negative integer")
        return f"{_RETIREMENT_TARGET_PREFIX}:{intake_item_uuid}:{namespace_uuid}:{retired_index_generation}"

    @staticmethod
    def _parse_target_ref(value: str) -> tuple[str, str, int] | None:
        parts = value.split(":")
        if len(parts) != 5:
            return None
        prefix, version, item_uuid, namespace_uuid, generation = parts
        if prefix != "index-generation" or version != "v1" or not item_uuid or not namespace_uuid:
            return None
        try:
            parsed_generation = int(generation)
        except ValueError:
            return None
        if parsed_generation < 0 or str(parsed_generation) != generation:
            return None
        return item_uuid, namespace_uuid, parsed_generation

    @staticmethod
    def _pointer_snapshot_ref(
        *,
        team_uuid: str,
        intake_item_uuid: str,
        namespace_uuid: str,
        retired_index_generation: int,
        successor_index_generation: int,
        pointer_row_revision: int,
        successor_generation_artifact_uuid: object,
    ) -> str:
        return "mkb.index-pointer-retirement.v1:" + stable_digest(
            {
                "team_uuid": team_uuid,
                "intake_item_uuid": intake_item_uuid,
                "namespace_uuid": namespace_uuid,
                "retired_index_generation": retired_index_generation,
                "successor_index_generation": successor_index_generation,
                "pointer_row_revision": pointer_row_revision,
                "successor_generation_artifact_uuid": successor_generation_artifact_uuid,
            }
        )

    @staticmethod
    def _intent_from_row(row: Mapping[str, object]) -> IndexGenerationRetirementIntent:
        target = IndexGenerationRetirementService._parse_target_ref(str(row["target_ref"]))
        if target is None:
            raise MkbError("INDEX_RETIREMENT_TARGET_INVALID", "A stored index retirement target is invalid", 409)
        intake_item_uuid, namespace_uuid, retired_generation = target
        return IndexGenerationRetirementIntent(
            intent_uuid=str(row["intent_uuid"]),
            team_uuid=str(row["team_uuid"]),
            intake_item_uuid=intake_item_uuid,
            namespace_uuid=namespace_uuid,
            retired_index_generation=retired_generation,
            eligible_at=str(row["eligible_at"]),
            requested_at=str(row["requested_at"]),
            reference_snapshot_ref=(
                None if row["reference_snapshot_ref"] is None else str(row["reference_snapshot_ref"])
            ),
        )

    @staticmethod
    def _same_candidate(candidate: IndexGenerationRetirementCandidate, row: Mapping[str, object] | None) -> bool:
        return bool(
            row
            and row["status"] == "open"
            and row["team_uuid"] == candidate.team_uuid
            and row["intent_uuid"] == candidate.intent_uuid
            and row["target_ref"] == candidate.target_ref
            and row["eligible_at"] == candidate.eligible_at
            and row["requested_at"] == candidate.requested_at
        )

    def _is_due(self, value: object) -> bool:
        eligible_at = self._parse_timestamp(value)
        return eligible_at is not None and eligible_at <= self._now()

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("index retirement clock must return an aware timestamp")
        return now.astimezone(UTC)

    @staticmethod
    def _parse_timestamp(value: object) -> datetime | None:
        if not isinstance(value, str):
            return None
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
        if parsed.tzinfo is None:
            return None
        return parsed.astimezone(UTC)

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")

    @staticmethod
    def _validate_limit(limit: int) -> None:
        if isinstance(limit, bool) or not isinstance(limit, int) or not 1 <= limit <= 10_000:
            raise ValueError("index generation retirement limit must be between 1 and 10000")

    @staticmethod
    def _validate_schedule(
        *,
        team_uuid: str,
        intake_item_uuid: str,
        namespace_uuid: str,
        retired_index_generation: int,
        successor_index_generation: int,
        expected_pointer_row_revision: int,
    ) -> None:
        IndexGenerationRetirementService.target_ref(
            intake_item_uuid,
            namespace_uuid,
            retired_index_generation,
        )
        if not team_uuid:
            raise ValueError("team_uuid is required")
        if (
            isinstance(successor_index_generation, bool)
            or not isinstance(successor_index_generation, int)
            or successor_index_generation <= retired_index_generation
        ):
            raise ValueError("successor_index_generation must be greater than retired_index_generation")
        if (
            isinstance(expected_pointer_row_revision, bool)
            or not isinstance(expected_pointer_row_revision, int)
            or expected_pointer_row_revision < 0
        ):
            raise ValueError("expected_pointer_row_revision must be a non-negative integer")


__all__ = [
    "IndexGenerationRetirementCandidate",
    "IndexGenerationRetirementDisposition",
    "IndexGenerationRetirementIntent",
    "IndexGenerationRetirementResult",
    "IndexGenerationRetirementScanResult",
    "IndexGenerationRetirementService",
    "RETIREMENT_POLICY_REF",
    "RETIREMENT_TARGET_KIND",
]
