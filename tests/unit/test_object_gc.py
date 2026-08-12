"""Focused S13 orphan-GC tests against the real SQLite/object-store pair."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.contracts.api.models import TeamCreateRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.object_gc import ObjectGcScanner, ObjectGcSchedule
from src.services.object_gc import ObjectGcDisposition, ObjectGcService
from src.services.teams import TeamService
from src.storage.local_store import LocalObjectStore
from src.storage.ports import ObjectStorePort


@dataclass(frozen=True, slots=True)
class SeededObject:
    persistence: SqlitePersistence
    storage: LocalObjectStore
    team_uuid: str
    stored_object_uuid: str
    stat: ObjectStat
    clock: datetime


async def _seed_orphan(tmp_path: Path, *, age: timedelta = timedelta(days=2)) -> SeededObject:
    persistence = SqlitePersistence(tmp_path / "gc.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    storage = LocalObjectStore(tmp_path / "objects")
    team_uuid = uuid7()
    await TeamService(persistence).create(
        TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="object-gc")
    )
    stat = await storage.promote(
        b"unowned bytes eligible for S13 collection",
        PromoteRequest(team_uuid=team_uuid, purpose="process_io", media_type="text/plain"),
    )
    stored_object_uuid = uuid7()
    clock = datetime(2026, 8, 12, 12, 0, tzinfo=UTC)
    created_at = (clock - age).isoformat(timespec="microseconds").replace("+00:00", "Z")
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_stored_objects "
            "(stored_object_uuid,team_uuid,digest_algorithm,content_digest,size_bytes,media_type,storage_backend,"
            "created_at,payload_extra) VALUES (?,?, 'sha256',?,?,?,?,?,'{}')",
            (
                stored_object_uuid,
                team_uuid,
                stat.sha256,
                stat.size_bytes,
                stat.media_type,
                "local_fs",
                created_at,
            ),
        )
    return SeededObject(persistence, storage, team_uuid, stored_object_uuid, stat, clock)


def _service(seed: SeededObject, storage: ObjectStorePort | None = None) -> ObjectGcService:
    return ObjectGcService(
        seed.persistence,
        storage or seed.storage,
        orphan_grace=timedelta(hours=24),
        scanner_id="test-object-gc",
        clock=lambda: seed.clock,
    )


@pytest.mark.asyncio
async def test_orphan_gc_unlinks_then_records_proof_and_tombstones(tmp_path: Path) -> None:
    seed = await _seed_orphan(tmp_path)
    try:
        result = await _service(seed).scan_once()
        assert result.candidate_count == 1
        assert result.deleted_count == 1
        assert result.results[0].disposition is ObjectGcDisposition.DELETED

        with pytest.raises(MkbError, match="Object bytes are unavailable"):
            await seed.storage.read_verified(seed.team_uuid, seed.stat.handle)
        async with seed.persistence.transaction() as tx:
            catalog = await tx.fetchone(
                "SELECT tombstoned_at FROM mkb_stored_objects WHERE team_uuid=? AND stored_object_uuid=?",
                (seed.team_uuid, seed.stored_object_uuid),
            )
            proofs = await tx.fetchall(
                "SELECT content_digest,size_bytes,delete_fence_digest,scanner_id FROM mkb_object_delete_proofs "
                "WHERE team_uuid=? AND stored_object_uuid=?",
                (seed.team_uuid, seed.stored_object_uuid),
            )
        assert catalog is not None and catalog["tombstoned_at"] is not None
        assert len(proofs) == 1
        assert proofs[0]["content_digest"] == seed.stat.sha256
        assert proofs[0]["size_bytes"] == seed.stat.size_bytes
        assert proofs[0]["scanner_id"] == "test-object-gc"
        assert len(proofs[0]["delete_fence_digest"]) == 64

        # Tombstoned catalogues are never re-collected or re-proved.
        retry = await _service(seed).scan_once()
        assert retry.candidate_count == 0
    finally:
        await seed.persistence.close()


@pytest.mark.asyncio
async def test_candidate_is_rechecked_when_live_reference_arrives_after_scan(tmp_path: Path) -> None:
    seed = await _seed_orphan(tmp_path)
    try:
        service = _service(seed)
        (candidate,) = await service.collect_candidates()
        async with seed.persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_object_references "
                "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
                "created_at,payload_extra) VALUES (?,?,?,'process_io','test_owner',?,?,?,?, '{}')",
                (
                    uuid7(),
                    seed.team_uuid,
                    seed.stored_object_uuid,
                    uuid7(),
                    seed.stat.sha256,
                    seed.stat.size_bytes,
                    seed.clock.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                ),
            )
        outcome = await service.delete_candidate(candidate)
        assert outcome.disposition is ObjectGcDisposition.LIVE_REFERENCE
        assert await seed.storage.read_verified(seed.team_uuid, seed.stat.handle)
        async with seed.persistence.transaction() as tx:
            proof_count = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_object_delete_proofs")
            tombstone = await tx.fetchone(
                "SELECT tombstoned_at FROM mkb_stored_objects WHERE stored_object_uuid=?", (seed.stored_object_uuid,)
            )
        assert proof_count == {"count": 0}
        assert tombstone == {"tombstoned_at": None}
    finally:
        await seed.persistence.close()


@pytest.mark.asyncio
async def test_hold_and_explicit_cleanup_fence_block_collection(tmp_path: Path) -> None:
    seed = await _seed_orphan(tmp_path)
    try:
        service = _service(seed)
        (candidate,) = await service.collect_candidates()
        async with seed.persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_object_references "
                "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
                "created_at,payload_extra) VALUES (?,?,?,'operator_hold','operator',?,?,?,?, '{}')",
                (
                    uuid7(),
                    seed.team_uuid,
                    seed.stored_object_uuid,
                    uuid7(),
                    seed.stat.sha256,
                    seed.stat.size_bytes,
                    seed.clock.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                ),
            )
        assert (await service.delete_candidate(candidate)).disposition is ObjectGcDisposition.HOLD

        async with seed.persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_object_references SET released_at=? WHERE team_uuid=? AND stored_object_uuid=?",
                (
                    seed.clock.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                    seed.team_uuid,
                    seed.stored_object_uuid,
                ),
            )
            await tx.execute(
                "INSERT INTO mkb_intake_cleanup_intents "
                "(intent_uuid,team_uuid,policy_ref,target_kind,target_ref,required_substrate_set_digest,hold_refs_json,"
                "reference_snapshot_ref,status,requested_trace_uuid,requested_at,payload_extra) "
                "VALUES (?,?,?,'object',?,?,?,NULL,'open',?,?, '{}')",
                (
                    uuid7(),
                    seed.team_uuid,
                    "mkb.retention.test.v1",
                    candidate.handle.value,
                    stable_digest({"required": "object"}),
                    f'["{candidate.handle.value}"]',
                    uuid7(),
                    seed.clock.isoformat(timespec="microseconds").replace("+00:00", "Z"),
                ),
            )
        assert (await service.delete_candidate(candidate)).disposition is ObjectGcDisposition.CLEANUP_FENCE
        assert await seed.storage.read_verified(seed.team_uuid, seed.stat.handle)
    finally:
        await seed.persistence.close()


class _MissingDeleteStore:
    """A storage adapter observation where catalogued bytes have disappeared."""

    def __init__(self, inner: LocalObjectStore) -> None:
        self._inner = inner

    async def promote(self, data: bytes, request: PromoteRequest) -> ObjectStat:
        return await self._inner.promote(data, request)

    async def read_verified(self, team_uuid: str, handle: ObjectHandle) -> bytes:
        return await self._inner.read_verified(team_uuid, handle)

    async def delete_if_unreferenced(self, team_uuid: str, handle: ObjectHandle) -> bool:
        return False

    async def readiness(self) -> bool:
        return await self._inner.readiness()


@pytest.mark.asyncio
async def test_failed_physical_delete_never_tombstones_or_proves(tmp_path: Path) -> None:
    seed = await _seed_orphan(tmp_path)
    try:
        result = await _service(seed, _MissingDeleteStore(seed.storage)).scan_once()
        assert result.results[0].disposition is ObjectGcDisposition.MISSING_BYTES
        async with seed.persistence.transaction() as tx:
            catalog = await tx.fetchone(
                "SELECT tombstoned_at FROM mkb_stored_objects WHERE stored_object_uuid=?", (seed.stored_object_uuid,)
            )
            proof_count = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_object_delete_proofs")
        assert catalog == {"tombstoned_at": None}
        assert proof_count == {"count": 0}
    finally:
        await seed.persistence.close()


@pytest.mark.asyncio
async def test_grace_window_and_zero_grace_are_fail_closed(tmp_path: Path) -> None:
    seed = await _seed_orphan(tmp_path, age=timedelta(hours=23, minutes=59))
    try:
        assert (await _service(seed).scan_once()).candidate_count == 0
        with pytest.raises(ValueError, match="grace"):
            ObjectGcService(seed.persistence, seed.storage, orphan_grace=timedelta(0))
    finally:
        await seed.persistence.close()


@pytest.mark.asyncio
async def test_runtime_scanner_delegates_bounded_s13_scan(tmp_path: Path) -> None:
    seed = await _seed_orphan(tmp_path)
    try:
        scanner = ObjectGcScanner(_service(seed), ObjectGcSchedule(interval=timedelta(minutes=5), batch_size=1))
        result = await scanner.run_once()
        assert result.deleted_count == 1
        with pytest.raises(ValueError, match="interval"):
            ObjectGcSchedule(interval=timedelta(0))
    finally:
        await seed.persistence.close()
