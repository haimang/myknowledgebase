"""NH4 Phase 2: usable upload identity requires catalog and pending in one UoW."""

from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import pytest

from src.contracts.api.models import TeamCreateRequest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import PromoteRequest
from src.persistence.factory import build_persistence
from src.runtime.intake.pipeline import IntakePipeline
from src.services.object_upload import ObjectUploadService
from src.services.teams import TeamService
from src.storage.local_store import LocalObjectStore


async def _chunks(*values: bytes):
    for value in values:
        yield value


async def _fixture(tmp_path: Path, *, fault=None):
    persistence = build_persistence(
        tmp_path / "upload.sqlite3",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    team_uuid = uuid7()
    await TeamService(persistence).create(
        TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="nh4-upload")
    )
    storage = LocalObjectStore(tmp_path / "objects", max_object_bytes=1024 * 1024)
    return persistence, storage, ObjectUploadService(persistence, storage, uow_fault_hook=fault), team_uuid


@pytest.mark.asyncio
async def test_catalog_and_upload_pending_commit_before_record_is_returned(tmp_path: Path) -> None:
    persistence, storage, service, team_uuid = await _fixture(tmp_path)
    body = b"catalog-pending-atomic"
    try:
        record = await service.upload(
            team_uuid=team_uuid,
            chunks=_chunks(body[:7], body[7:]),
            media_type="text/plain",
            expected_sha256=hashlib.sha256(body).hexdigest(),
        )
        assert record.replay is False
        assert await storage.read_verified(team_uuid, record.stat.handle) == body
        async with persistence.transaction() as tx:
            catalog = await tx.fetchone(
                "SELECT stored_object_uuid,content_digest,size_bytes,tombstoned_at FROM mkb_stored_objects "
                "WHERE team_uuid=?",
                (team_uuid,),
            )
            pending = await tx.fetchone(
                "SELECT purpose,owner_kind,owner_uuid,released_at FROM mkb_object_references "
                "WHERE team_uuid=?",
                (team_uuid,),
            )
            counts = {
                table: await tx.fetchone(f"SELECT COUNT(*) AS count FROM {table} WHERE team_uuid=?", (team_uuid,))
                for table in ("mkb_intake_sources", "mkb_intake_items", "mkb_intake_revisions")
            }
        assert catalog == {
            "stored_object_uuid": record.stored_object_uuid,
            "content_digest": record.stat.sha256,
            "size_bytes": len(body),
            "tombstoned_at": None,
        }
        assert pending == {
            "purpose": "upload_pending",
            "owner_kind": "public_upload",
            "owner_uuid": record.stored_object_uuid,
            "released_at": None,
        }
        assert all(value == {"count": 0} for value in counts.values())
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_same_bytes_replay_one_live_catalog_and_pending(tmp_path: Path) -> None:
    persistence, _, service, team_uuid = await _fixture(tmp_path)
    body = b"same-upload"
    try:
        first = await service.upload(
            team_uuid=team_uuid,
            chunks=_chunks(body),
            media_type="text/plain",
            expected_sha256=None,
        )
        second = await service.upload(
            team_uuid=team_uuid,
            chunks=_chunks(body[:2], body[2:]),
            media_type="application/octet-stream",
            expected_sha256=None,
        )
        assert first.stat.handle == second.stat.handle
        assert second.replay is True
        assert second.stat.media_type == "text/plain"
        async with persistence.transaction() as tx:
            catalogs = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_stored_objects WHERE team_uuid=? AND tombstoned_at IS NULL",
                (team_uuid,),
            )
            pending = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_object_references WHERE team_uuid=? "
                "AND purpose='upload_pending' AND released_at IS NULL",
                (team_uuid,),
            )
        assert catalogs == pending == {"count": 1}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_uow_fault_rolls_back_catalog_and_pending_and_returns_no_record(tmp_path: Path) -> None:
    def fault(stage: str) -> None:
        if stage == "after_catalog_before_pending":
            raise RuntimeError("fault-after-catalog")

    persistence, storage, service, team_uuid = await _fixture(tmp_path, fault=fault)
    body = b"orphan-after-uow-rollback"
    digest = hashlib.sha256(body).hexdigest()
    try:
        with pytest.raises(RuntimeError, match="fault-after-catalog"):
            await service.upload(
                team_uuid=team_uuid,
                chunks=_chunks(body),
                media_type=None,
                expected_sha256=None,
            )
        async with persistence.transaction() as tx:
            catalog = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=?",
                (team_uuid, digest),
            )
            pending = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_object_references WHERE team_uuid=?",
                (team_uuid,),
            )
        assert catalog == pending == {"count": 0}
        # Bytes-first may leave a GC-reapable orphan, but no usable record was
        # returned and no catalog row falsely claims upload success.
        handle = PromoteRequest(
            team_uuid=team_uuid,
            purpose="upload_pending",
            expected_sha256=digest,
        )
        assert handle.purpose == "upload_pending"
        assert (storage.root / "objects" / team_uuid / "sha256" / digest[:2] / digest[2:4] / digest).is_file()
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_migration_preserves_legacy_purposes_and_object_views(tmp_path: Path) -> None:
    before = tmp_path / "before-migrations"
    before.mkdir()
    for path in Path("src/persistence/migrations").glob("*.sql"):
        if path.name < "021_nh4_upload_pending.sql":
            shutil.copy2(path, before / path.name)
    persistence = build_persistence(
        tmp_path / "migration.sqlite3",
        before,
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    team_uuid, stored_uuid, reference_uuid = uuid7(), uuid7(), uuid7()
    digest = hashlib.sha256(b"legacy-ref").hexdigest()
    now = utc_now()
    try:
        await TeamService(persistence).create(
            TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="nh4-migrate")
        )
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_stored_objects(stored_object_uuid,team_uuid,content_digest,size_bytes,created_at) "
                "VALUES (?,?,?,?,?)",
                (stored_uuid, team_uuid, digest, 10, now),
            )
            await tx.execute(
                "INSERT INTO mkb_object_references(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,"
                "owner_uuid,expected_digest,expected_size,created_at) VALUES (?,?,?,'process_io','fixture',?,?,?,?)",
                (reference_uuid, team_uuid, stored_uuid, uuid7(), digest, 10, now),
            )
        persistence.migration_directory = Path("src/persistence/migrations")
        await persistence.migrate()
        async with persistence.transaction() as tx:
            legacy = await tx.fetchone(
                "SELECT purpose,released_at FROM mkb_object_references WHERE reference_uuid=?",
                (reference_uuid,),
            )
            live_view = await tx.fetchone(
                "SELECT purpose FROM mkb_v_object_live_refs WHERE reference_uuid=?",
                (reference_uuid,),
            )
            orphan_count = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_v_object_orphan_candidates")
        assert legacy == {"purpose": "process_io", "released_at": None}
        assert live_view == {"purpose": "process_io"}
        assert orphan_count == {"count": 0}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_uncatalogued_internal_promote_is_not_a_local_object_ingest_input(tmp_path: Path) -> None:
    persistence, storage, _, team_uuid = await _fixture(tmp_path)
    digest = "a" * 64
    command = ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=team_uuid,
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        step_key="acquire_local",
        process_key="intake.acquire.local_object",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:input",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:config",
        config_snapshot_digest=digest,
        binding_state="unsealed",
        policy_binding_digest=digest,
    )
    try:
        stat = await storage.promote(
            b"internal promote is not public upload",
            PromoteRequest(team_uuid=team_uuid, purpose="process_io", media_type="text/plain"),
        )
        pipeline = IntakePipeline(persistence, storage, None)  # type: ignore[arg-type]
        with pytest.raises(MkbError) as raised:
            await pipeline._acquire_content(  # noqa: SLF001
                command,
                {
                    "source_kind": "local_object",
                    "external_key": "uncatalogued",
                    "logical_handle": stat.handle.value,
                    "media_type": "text/plain",
                },
            )
        assert raised.value.code == "OBJECT_CATALOG_REQUIRED"
        assert raised.value.status_code == 409
    finally:
        await persistence.close()
