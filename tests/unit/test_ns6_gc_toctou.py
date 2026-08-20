"""NS6-T07: GC quarantine window must restore bytes when a live ref appears."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest
from src.services.object_gc import ObjectGcDisposition
from src.storage.local_store import LocalObjectStore
from tests.unit.test_object_gc import _seed_orphan, _service


class _InterleavePromoteStore:
    """Promote + catalog a live reference after the bytes have been quarantined."""

    def __init__(self, inner: LocalObjectStore, seed: object) -> None:
        self._inner = inner
        self._seed = seed

    async def promote(self, data: bytes, request: PromoteRequest) -> ObjectStat:
        return await self._inner.promote(data, request)

    async def read_verified(self, team_uuid: str, handle: ObjectHandle) -> bytes:
        return await self._inner.read_verified(team_uuid, handle)

    async def delete_if_unreferenced(self, team_uuid: str, handle: ObjectHandle) -> bool:
        return await self._inner.delete_if_unreferenced(team_uuid, handle)

    async def quarantine_object(self, team_uuid: str, handle: ObjectHandle) -> bool:
        moved = await self._inner.quarantine_object(team_uuid, handle)
        payload = b"unowned bytes eligible for S13 collection"
        await self._inner.promote(
            payload,
            PromoteRequest(team_uuid=team_uuid, purpose="process_io", media_type="text/plain"),
        )
        seed = self._seed
        async with seed.persistence.transaction() as tx:  # type: ignore[attr-defined]
            await tx.execute(
                "INSERT INTO mkb_object_references "
                "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
                "created_at,payload_extra) VALUES (?,?,?,'process_io','test_owner',?,?,?,?, '{}')",
                (
                    uuid7(),
                    seed.team_uuid,  # type: ignore[attr-defined]
                    seed.stored_object_uuid,  # type: ignore[attr-defined]
                    "interleave",
                    seed.stat.sha256,  # type: ignore[attr-defined]
                    seed.stat.size_bytes,  # type: ignore[attr-defined]
                    utc_now(),
                ),
            )
        return moved

    async def restore_quarantined(self, team_uuid: str, handle: ObjectHandle) -> bool:
        return await self._inner.restore_quarantined(team_uuid, handle)

    async def destroy_quarantined(self, team_uuid: str, handle: ObjectHandle) -> None:
        await self._inner.destroy_quarantined(team_uuid, handle)

    async def readiness(self) -> bool:
        return await self._inner.readiness()


@pytest.mark.asyncio
async def test_gc_restore_when_live_reference_arrives_during_quarantine(tmp_path: Path) -> None:
    seed = await _seed_orphan(tmp_path)
    try:
        service = _service(seed, _InterleavePromoteStore(seed.storage, seed))
        (candidate,) = await service.collect_candidates()
        result = await service.delete_candidate(candidate)
        assert result.disposition is ObjectGcDisposition.LIVE_REFERENCE
        recovered = await seed.storage.read_verified(seed.team_uuid, seed.stat.handle)
        assert recovered == b"unowned bytes eligible for S13 collection"
        async with seed.persistence.transaction() as tx:
            catalog = await tx.fetchone(
                "SELECT tombstoned_at FROM mkb_stored_objects WHERE stored_object_uuid=?",
                (seed.stored_object_uuid,),
            )
            live_refs = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_object_references "
                "WHERE stored_object_uuid=? AND released_at IS NULL",
                (seed.stored_object_uuid,),
            )
        assert catalog == {"tombstoned_at": None}
        assert live_refs == {"count": 1}
    finally:
        await seed.persistence.close()
