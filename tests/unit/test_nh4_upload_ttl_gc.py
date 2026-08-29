"""NH4-T06: upload expiry starts grace; crash staging is independently reaped."""

from __future__ import annotations

import os
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.contracts.api.models import TeamCreateRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.persistence.factory import build_persistence
from src.services.object_gc import ObjectGcDisposition, ObjectGcService
from src.services.object_upload import ObjectUploadService
from src.services.object_upload_ttl import ObjectUploadLifecycleService
from src.services.teams import TeamService
from src.storage.local_store import LocalObjectStore


async def _chunks(value: bytes):
    yield value


async def _fixture(tmp_path: Path):
    persistence = build_persistence(
        tmp_path / "ttl.sqlite3",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    team_uuid = uuid7()
    await TeamService(persistence).create(
        TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="nh4-ttl")
    )
    storage = LocalObjectStore(tmp_path / "objects", max_object_bytes=1024)
    return persistence, storage, team_uuid


@pytest.mark.asyncio
async def test_ttl_without_ingest_releases_then_grace_tombstone(tmp_path: Path) -> None:
    persistence, storage, team_uuid = await _fixture(tmp_path)
    body = b"expire-without-ingest"
    try:
        uploaded = await ObjectUploadService(persistence, storage).upload(
            team_uuid=team_uuid,
            chunks=_chunks(body),
            media_type="text/plain",
            expected_sha256=None,
        )
        async with persistence.transaction() as tx:
            pending = await tx.fetchone(
                "SELECT created_at FROM mkb_object_references WHERE team_uuid=? AND purpose='upload_pending'",
                (team_uuid,),
            )
        assert pending is not None
        created = datetime.fromisoformat(str(pending["created_at"]).replace("Z", "+00:00")).astimezone(UTC)
        clock = [created]
        lifecycle = ObjectUploadLifecycleService(
            persistence,
            storage,
            pending_ttl=timedelta(seconds=10),
            staging_ttl=timedelta(seconds=5),
            clock=lambda: clock[0],
        )
        gc = ObjectGcService(
            persistence,
            storage,
            orphan_grace=timedelta(seconds=10),
            scanner_id="nh4-ttl-gc",
            clock=lambda: clock[0],
        )

        clock[0] = created + timedelta(seconds=9)
        assert (await lifecycle.scan_once()).released_pending == 0
        assert await gc.collect_candidates() == ()

        clock[0] = created + timedelta(seconds=11)
        assert (await lifecycle.scan_once()).released_pending == 1
        assert await storage.read_verified(team_uuid, uploaded.stat.handle) == body
        assert await gc.collect_candidates() == ()

        clock[0] = created + timedelta(seconds=20)
        assert await gc.collect_candidates() == ()
        clock[0] = created + timedelta(seconds=22)
        result = await gc.scan_once()
        assert result.deleted_count == 1
        assert result.results[0].disposition is ObjectGcDisposition.DELETED
        with pytest.raises(MkbError) as raised:
            await storage.read_verified(team_uuid, uploaded.stat.handle)
        assert raised.value.code == "OBJECT_MISSING"
        async with persistence.transaction() as tx:
            ref = await tx.fetchone(
                "SELECT released_at FROM mkb_object_references WHERE team_uuid=? AND purpose='upload_pending'",
                (team_uuid,),
            )
            catalog = await tx.fetchone(
                "SELECT tombstoned_at FROM mkb_stored_objects WHERE team_uuid=?",
                (team_uuid,),
            )
            proof = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_object_delete_proofs WHERE team_uuid=?",
                (team_uuid,),
            )
        assert ref is not None and ref["released_at"] is not None
        assert catalog is not None and catalog["tombstoned_at"] is not None
        assert proof == {"count": 1}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_staging_incomplete_never_catalogued_is_reaped(tmp_path: Path) -> None:
    persistence, storage, team_uuid = await _fixture(tmp_path)
    del team_uuid
    now = datetime(2026, 8, 29, 12, 0, tzinfo=UTC)
    try:
        assert await storage.readiness()
        staging = storage.root / "staging" / "promote-crashed-worker"
        staging.write_bytes(b"partial transport bytes")
        old = (now - timedelta(seconds=30)).timestamp()
        os.utime(staging, (old, old))
        lifecycle = ObjectUploadLifecycleService(
            persistence,
            storage,
            pending_ttl=timedelta(seconds=10),
            staging_ttl=timedelta(seconds=5),
            clock=lambda: now,
        )
        result = await lifecycle.scan_once()
        assert result.released_pending == 0
        assert result.reaped_staging == 1
        assert not staging.exists()
        async with persistence.transaction() as tx:
            count = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_stored_objects")
        assert count == {"count": 0}
    finally:
        await persistence.close()


def test_upload_ttls_must_be_positive() -> None:
    with pytest.raises(ValueError, match="TTL"):
        ObjectUploadLifecycleService(  # type: ignore[arg-type]
            None,
            None,
            pending_ttl=timedelta(0),
            staging_ttl=timedelta(seconds=1),
        )
