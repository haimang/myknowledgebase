"""Authenticated-upload core: streamed CAS bytes plus atomic catalog/pending truth."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterable, Callable
from dataclasses import dataclass
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.handles import digest_from_handle, object_handle
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest
from src.persistence.ports import PersistencePort
from src.services.artifacts import live_stored_object_uuid
from src.storage.ports import ObjectStorePort


@dataclass(frozen=True, slots=True)
class ObjectUploadRecord:
    stat: ObjectStat
    stored_object_uuid: str
    replay: bool


@dataclass(frozen=True, slots=True)
class ObjectStatusRecord:
    stat: ObjectStat
    disposition: str


class ObjectUploadService:
    """Return a usable handle only after catalog + upload_pending commit."""

    def __init__(
        self,
        persistence: PersistencePort,
        storage: ObjectStorePort,
        *,
        uow_fault_hook: Callable[[str], Any] | None = None,
    ) -> None:
        self._persistence = persistence
        self._storage = storage
        self._uow_fault_hook = uow_fault_hook

    async def upload(
        self,
        *,
        team_uuid: str,
        chunks: AsyncIterable[bytes],
        media_type: str | None,
        expected_sha256: str | None,
    ) -> ObjectUploadRecord:
        stat = await self._storage.promote_stream(
            chunks,
            PromoteRequest(
                team_uuid=team_uuid,
                purpose="upload_pending",
                media_type=media_type,
                expected_sha256=expected_sha256,
            ),
        )
        await self._run_fault_hook("after_promote_before_catalog")
        replay = False
        async with self._persistence.transaction() as tx:
            team = await tx.fetchone("SELECT status FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
            if team is None:
                raise MkbError("team-not-found", "Team was not found", 404)
            if team["status"] != "active":
                raise MkbError("team-not-active", "Team is not active", 409)
            stored_object_uuid = await live_stored_object_uuid(
                tx,
                team_uuid,
                stat.sha256,
                stat.size_bytes,
            )
            if stored_object_uuid is None:
                candidate_uuid = uuid7()
                await tx.execute(
                    "INSERT OR IGNORE INTO mkb_stored_objects "
                    "(stored_object_uuid,team_uuid,digest_algorithm,content_digest,size_bytes,media_type,"
                    "storage_backend,created_at,payload_extra) VALUES (?,?,'sha256',?,?,?,'local_fs',?,'{}')",
                    (
                        candidate_uuid,
                        team_uuid,
                        stat.sha256,
                        stat.size_bytes,
                        stat.media_type,
                        utc_now(),
                    ),
                )
                stored_object_uuid = await live_stored_object_uuid(
                    tx,
                    team_uuid,
                    stat.sha256,
                    stat.size_bytes,
                )
                if stored_object_uuid is None:
                    raise MkbError("OBJECT_CATALOG_COMMIT_FAILED", "Object catalog did not accept upload", 503)
                replay = stored_object_uuid != candidate_uuid
            else:
                replay = True
            await self._run_fault_hook("after_catalog_before_pending")
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_object_references "
                "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,"
                "expected_size,created_at,payload_extra) "
                "VALUES (?,?,?,'upload_pending','public_upload',?,?,?,?,'{}')",
                (
                    uuid7(),
                    team_uuid,
                    stored_object_uuid,
                    stored_object_uuid,
                    stat.sha256,
                    stat.size_bytes,
                    utc_now(),
                ),
            )
            pending = await tx.fetchone(
                "SELECT reference_uuid FROM mkb_object_references WHERE team_uuid=? AND stored_object_uuid=? "
                "AND purpose='upload_pending' AND owner_kind='public_upload' AND owner_uuid=? "
                "AND released_at IS NULL",
                (team_uuid, stored_object_uuid, stored_object_uuid),
            )
            if pending is None:
                raise MkbError("OBJECT_PENDING_COMMIT_FAILED", "Object pending hold did not commit", 503)
            catalog = await tx.fetchone(
                "SELECT media_type FROM mkb_stored_objects WHERE team_uuid=? AND stored_object_uuid=? "
                "AND tombstoned_at IS NULL",
                (team_uuid, stored_object_uuid),
            )
            if catalog is None:
                raise MkbError("OBJECT_CATALOG_COMMIT_FAILED", "Object catalog disappeared during upload", 503)
            committed_stat = stat.model_copy(update={"media_type": catalog["media_type"]})
        return ObjectUploadRecord(stat=committed_stat, stored_object_uuid=stored_object_uuid, replay=replay)

    async def stat(self, *, team_uuid: str, handle: ObjectHandle) -> ObjectStatusRecord:
        digest = digest_from_handle(team_uuid, handle)
        async with self._persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT stored_object_uuid,size_bytes,media_type,tombstoned_at FROM mkb_stored_objects "
                "WHERE team_uuid=? AND content_digest=? "
                "ORDER BY (tombstoned_at IS NULL) DESC,created_at DESC LIMIT 1",
                (team_uuid, digest),
            )
            if row is None:
                raise MkbError("OBJECT_NOT_FOUND", "Object was not found", 404)
            if row["tombstoned_at"] is not None:
                disposition = "tombstoned"
            else:
                pending = await tx.fetchone(
                    "SELECT 1 AS present FROM mkb_object_references WHERE team_uuid=? AND stored_object_uuid=? "
                    "AND purpose='upload_pending' AND released_at IS NULL LIMIT 1",
                    (team_uuid, row["stored_object_uuid"]),
                )
                live = await tx.fetchone(
                    "SELECT 1 AS present FROM mkb_object_references WHERE team_uuid=? AND stored_object_uuid=? "
                    "AND purpose='intake_snapshot_artifact' AND owner_kind='intake_snapshot_source_object' "
                    "AND released_at IS NULL LIMIT 1",
                    (team_uuid, row["stored_object_uuid"]),
                )
                disposition = "pending" if pending is not None else "ingested" if live is not None else "expired"
        return ObjectStatusRecord(
            stat=ObjectStat(
                handle=object_handle(team_uuid, digest),
                sha256=digest,
                size_bytes=int(row["size_bytes"]),
                media_type=row["media_type"],
            ),
            disposition=disposition,
        )

    async def _run_fault_hook(self, stage: str) -> None:
        if self._uow_fault_hook is None:
            return
        result = self._uow_fault_hook(stage)
        if inspect.isawaitable(result):
            await result


__all__ = ["ObjectStatusRecord", "ObjectUploadRecord", "ObjectUploadService"]
