"""Release abandoned upload holds and reap crash-only staging files."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from src.contracts.common.errors import MkbError
from src.contracts.storage.handles import digest_from_handle
from src.contracts.storage.models import ObjectHandle
from src.persistence.ports import PersistencePort
from src.storage.ports import ObjectStorePort


@dataclass(frozen=True, slots=True)
class ObjectUploadLifecycleResult:
    released_pending: int
    reaped_staging: int


class ObjectUploadLifecycleService:
    def __init__(
        self,
        persistence: PersistencePort,
        storage: ObjectStorePort,
        *,
        pending_ttl: timedelta,
        staging_ttl: timedelta,
        clock: Callable[[], datetime] | None = None,
    ) -> None:
        if pending_ttl <= timedelta(0) or staging_ttl <= timedelta(0):
            raise ValueError("object upload TTLs must be greater than zero")
        self._persistence = persistence
        self._storage = storage
        self._pending_ttl = pending_ttl
        self._staging_ttl = staging_ttl
        self._clock = clock or (lambda: datetime.now(UTC))

    async def scan_once(self, *, limit: int = 100) -> ObjectUploadLifecycleResult:
        if not 1 <= limit <= 10_000:
            raise ValueError("object upload lifecycle limit must be between 1 and 10000")
        now = self._now()
        cutoff = self._timestamp(now - self._pending_ttl)
        async with self._persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT reference_uuid FROM mkb_object_references WHERE purpose='upload_pending' "
                "AND released_at IS NULL AND created_at<=? ORDER BY created_at,reference_uuid LIMIT ?",
                (cutoff, limit),
            )
            released = 0
            for row in rows:
                result = await tx.execute(
                    "UPDATE mkb_object_references SET released_at=? WHERE reference_uuid=? AND released_at IS NULL",
                    (self._timestamp(now), row["reference_uuid"]),
                )
                released += int(result.rowcount)
        reaper = getattr(self._storage, "reap_staging_before", None)
        reaped = 0 if not callable(reaper) else int(await reaper(now - self._staging_ttl))
        return ObjectUploadLifecycleResult(released_pending=released, reaped_staging=reaped)

    async def cancel(self, *, team_uuid: str, handle: ObjectHandle) -> bool:
        digest = digest_from_handle(team_uuid, handle)
        now = self._timestamp(self._now())
        async with self._persistence.transaction() as tx:
            stored = await tx.fetchone(
                "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=? "
                "AND tombstoned_at IS NULL",
                (team_uuid, digest),
            )
            if stored is None:
                raise MkbError("OBJECT_NOT_FOUND", "Object was not found", 404)
            result = await tx.execute(
                "UPDATE mkb_object_references SET released_at=? WHERE reference_uuid=("
                "SELECT reference_uuid FROM mkb_object_references "
                "WHERE team_uuid=? AND stored_object_uuid=? AND purpose='upload_pending' "
                "AND owner_kind='public_upload' AND released_at IS NULL "
                "ORDER BY created_at DESC, reference_uuid DESC LIMIT 1"
                ") AND released_at IS NULL",
                (now, team_uuid, stored["stored_object_uuid"]),
            )
        return result.rowcount > 0

    def _now(self) -> datetime:
        now = self._clock()
        if now.tzinfo is None:
            raise ValueError("object upload lifecycle clock must be timezone-aware")
        return now.astimezone(UTC)

    @staticmethod
    def _timestamp(value: datetime) -> str:
        return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


__all__ = ["ObjectUploadLifecycleResult", "ObjectUploadLifecycleService"]
