"""NHX1-T16: tombstoned quarantine is destroyed on cold maintenance reconcile."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.models import PromoteRequest
from src.persistence.sqlite_port import SqlitePersistence
from src.services.object_gc import ObjectGcService
from src.storage.local_store import LocalObjectStore


@pytest.mark.asyncio
async def test_tombstoned_quarantine_is_destroyed_after_restart_reconcile(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "objects.db", Path("src/persistence/migrations"))
    storage = LocalObjectStore(tmp_path / "objects")
    await persistence.migrate()
    team_uuid = uuid7()
    try:
        stat = await storage.promote(b"tombstone-quarantine", PromoteRequest(team_uuid=team_uuid, purpose="process_io"))
        object_uuid = uuid7()
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
                (team_uuid, "gc", stable_digest({"team": team_uuid}), utc_now(), utc_now()),
            )
            await tx.execute(
                "INSERT INTO mkb_stored_objects(stored_object_uuid,team_uuid,content_digest,size_bytes,created_at) "
                "VALUES (?,?,?,?,?)",
                (object_uuid, team_uuid, stat.sha256, stat.size_bytes, utc_now()),
            )
        handle = stat.handle
        assert await storage.quarantine_object(team_uuid, handle)
        async with persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_stored_objects SET tombstoned_at=? WHERE team_uuid=? AND stored_object_uuid=?",
                (utc_now(), team_uuid, object_uuid),
            )
        gc = ObjectGcService(persistence, storage, orphan_grace=timedelta(hours=1))
        assert await gc.reconcile_quarantine() == 0
        assert not any(path.is_file() for path in (tmp_path / "objects" / "quarantine").rglob("*"))
    finally:
        await persistence.close()
