"""Authenticated-upload core: streamed CAS bytes plus atomic catalog/pending truth."""

from __future__ import annotations

import hashlib
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
    session_token: str | None = None


@dataclass(frozen=True, slots=True)
class ObjectStatusRecord:
    stat: ObjectStat
    disposition: str
    session_token: str | None = None


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
        idempotency_key: str | None = None,
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
        requested_idempotency_key = idempotency_key.strip() if isinstance(idempotency_key, str) else None
        if requested_idempotency_key is not None and not requested_idempotency_key:
            raise MkbError("OBJECT_IDEMPOTENCY_INVALID", "Object idempotency key is empty", 422)
        # Pre-session callers did not send an idempotency key.  Preserve the
        # NH4 digest replay contract for those clients while giving explicit
        # NHX1 keys an opaque, command-owned session.  A tombstoned catalog
        # entry starts a fresh legacy generation so re-upload is still a new
        # command rather than a replay of dead bytes.
        effective_idempotency_key = requested_idempotency_key or f"legacy:{stat.sha256}:{stat.size_bytes}"
        async with self._persistence.transaction() as tx:
            team = await tx.fetchone("SELECT status FROM mkb_teams WHERE team_uuid=?", (team_uuid,))
            if team is None:
                raise MkbError("team-not-found", "Team was not found", 404)
            if team["status"] != "active":
                raise MkbError("team-not-active", "Team is not active", 409)
            existing_session = await tx.fetchone(
                "SELECT * FROM mkb_object_upload_sessions WHERE team_uuid=? AND idempotency_key=?",
                (team_uuid, effective_idempotency_key),
            )
            if existing_session is not None:
                if (
                    existing_session["prepared_content_digest"] != stat.sha256
                    or existing_session["prepared_size_bytes"] != stat.size_bytes
                ):
                    raise MkbError("OBJECT_SESSION_CONFLICT", "Idempotent upload key has different bytes", 409)
                stored = await tx.fetchone(
                    "SELECT stored_object_uuid,size_bytes,media_type,tombstoned_at FROM mkb_stored_objects "
                    "WHERE team_uuid=? AND stored_object_uuid=?",
                    (team_uuid, existing_session["stored_object_uuid"]),
                )
                if stored is None or stored["tombstoned_at"] is not None:
                    if requested_idempotency_key is not None:
                        raise MkbError("OBJECT_SESSION_CONFLICT", "Upload session catalog is unavailable", 503)
                    # Legacy digest replay is only valid while its catalog
                    # object remains live.  Allocate a new command key after
                    # tombstoning; the old session/reference remains
                    # historical and is not mutated.
                    effective_idempotency_key = f"legacy:{stat.sha256}:{stat.size_bytes}:{uuid7()}"
                    existing_session = None
                else:
                    session_token = self._session_token(team_uuid, effective_idempotency_key, existing_session["upload_session_uuid"])
                    if requested_idempotency_key is None:
                        # NH4 legacy replay created one pending hold per
                        # upload call.  Keep that observable compatibility
                        # without conflating it with the canonical session's
                        # exact pending reference.
                        await tx.execute(
                            "INSERT INTO mkb_object_references "
                            "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,"
                            "expected_size,created_at,payload_extra) VALUES (?,?,?,'upload_pending','public_upload',?,?,?,?,'{}')",
                            (
                                uuid7(),
                                team_uuid,
                                stored["stored_object_uuid"],
                                uuid7(),
                                stat.sha256,
                                stat.size_bytes,
                                utc_now(),
                            ),
                        )
                    return ObjectUploadRecord(
                        stat=stat.model_copy(update={"media_type": stored["media_type"]}),
                        stored_object_uuid=stored["stored_object_uuid"],
                        replay=True,
                        session_token=session_token if requested_idempotency_key is not None else None,
                    )
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
                # A matching CAS byte object is not an idempotency replay:
                # each new command owns an independent upload session.
                replay = False
            await self._run_fault_hook("after_catalog_before_pending")
            session_uuid = uuid7()
            session_token = self._session_token(team_uuid, effective_idempotency_key, session_uuid)
            await tx.execute(
                "INSERT INTO mkb_object_upload_sessions"
                "(upload_session_uuid,team_uuid,session_token_hash,idempotency_key,command_fingerprint,staging_id,state,"
                "stored_object_uuid,prepared_content_digest,prepared_size_bytes,media_type,row_revision,expires_at,"
                "created_at,prepared_at,promoted_at,payload_extra) VALUES (?,?,?,?,?,?, 'promoted',?,?,?,?,0,?,?,?,?,'{}')",
                (
                    session_uuid,
                    team_uuid,
                    self._token_hash(session_token),
                    effective_idempotency_key,
                    hashlib.sha256(f"{team_uuid}:{effective_idempotency_key}:{stat.sha256}".encode()).hexdigest(),
                    f"staging:{session_uuid}",
                    stored_object_uuid,
                    stat.sha256,
                    stat.size_bytes,
                    stat.media_type,
                    utc_now(),
                    utc_now(),
                    utc_now(),
                    utc_now(),
                ),
            )
            await tx.execute(
                "INSERT INTO mkb_object_promotion_journals"
                "(promotion_journal_uuid,team_uuid,upload_session_uuid,staging_id,stored_object_uuid,state,"
                "expected_content_digest,expected_size_bytes,row_revision,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,'promoted',?,?,0,?,?, '{}')",
                (
                    uuid7(),
                    team_uuid,
                    session_uuid,
                    f"staging:{session_uuid}",
                    stored_object_uuid,
                    stat.sha256,
                    stat.size_bytes,
                    utc_now(),
                    utc_now(),
                ),
            )
            hold_owner = session_uuid if requested_idempotency_key is not None else uuid7()
            owner_kind = "upload_session" if requested_idempotency_key is not None else "public_upload"
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_object_references "
                "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,"
                "expected_size,created_at,upload_session_uuid,payload_extra) "
                "VALUES (?,?,?,'upload_pending',?,?,?,?,?,?, '{}')",
                (
                    uuid7(),
                    team_uuid,
                    stored_object_uuid,
                    owner_kind,
                    hold_owner,
                    stat.sha256,
                    stat.size_bytes,
                    utc_now(),
                    session_uuid,
                ),
            )
            pending = await tx.fetchone(
                "SELECT reference_uuid FROM mkb_object_references WHERE team_uuid=? AND stored_object_uuid=? "
                "AND purpose='upload_pending' AND owner_uuid=? "
                "AND released_at IS NULL",
                (team_uuid, stored_object_uuid, hold_owner),
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
            await tx.execute(
                "UPDATE mkb_object_upload_sessions SET state='committed',pending_reference_uuid=?,committed_at=?,"
                "row_revision=row_revision+1 WHERE upload_session_uuid=? AND state='promoted'",
                (pending["reference_uuid"], utc_now(), session_uuid),
            )
            await tx.execute(
                "UPDATE mkb_object_promotion_journals SET state='catalog_committed',terminal_at=?,updated_at=?,"
                "row_revision=row_revision+1 WHERE upload_session_uuid=? AND state='promoted'",
                (utc_now(), utc_now(), session_uuid),
            )
            committed_stat = stat.model_copy(update={"media_type": catalog["media_type"]})
        return ObjectUploadRecord(
            stat=committed_stat,
            stored_object_uuid=stored_object_uuid,
            replay=replay,
            session_token=session_token if requested_idempotency_key is not None else None,
        )

    async def stat(
        self, *, team_uuid: str, handle: ObjectHandle, session_token: str | None = None
    ) -> ObjectStatusRecord:
        digest = digest_from_handle(team_uuid, handle)
        async with self._persistence.transaction() as tx:
            session = None
            if session_token is not None:
                session = await self._session_tx(tx, team_uuid, session_token)
                if session is None:
                    raise MkbError("OBJECT_SESSION_NOT_FOUND", "Upload session token is invalid", 404)
                if session["prepared_content_digest"] != digest:
                    raise MkbError("OBJECT_SESSION_CONFLICT", "Upload session does not own this handle", 409)
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
                    "AND purpose='upload_pending' AND released_at IS NULL "
                    + ("AND upload_session_uuid=? " if session is not None else "")
                    + "LIMIT 1",
                    (team_uuid, row["stored_object_uuid"], session["upload_session_uuid"])
                    if session is not None
                    else (team_uuid, row["stored_object_uuid"]),
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
            session_token=(
                self._session_token(team_uuid, session["idempotency_key"], session["upload_session_uuid"])
                if session is not None
                else None
            ),
        )

    async def reserve_session(
        self,
        *,
        team_uuid: str,
        session_token: str,
        task_uuid: str,
        task_generation: int,
    ) -> bool:
        """Bind one committed upload session to exactly one Task generation."""

        if task_generation < 1:
            raise MkbError("OBJECT_SESSION_COMMAND_INVALID", "Task generation is invalid", 422)
        async with self._persistence.transaction() as tx:
            session = await self._session_tx(tx, team_uuid, session_token)
            if session is None:
                raise MkbError("OBJECT_SESSION_NOT_FOUND", "Upload session token is invalid", 404)
            updated = await tx.execute(
                "UPDATE mkb_object_upload_sessions SET state='reserved',reserved_task_uuid=?,reserved_task_generation=?,"
                "row_revision=row_revision+1 WHERE upload_session_uuid=? AND state='committed'",
                (task_uuid, task_generation, session["upload_session_uuid"]),
            )
        return updated.rowcount == 1

    async def consume_session(self, *, team_uuid: str, session_token: str) -> bool:
        """Consume the exact reserved session and release only its pending ref."""

        now = utc_now()
        async with self._persistence.transaction() as tx:
            session = await self._session_tx(tx, team_uuid, session_token)
            if session is None:
                raise MkbError("OBJECT_SESSION_NOT_FOUND", "Upload session token is invalid", 404)
            updated = await tx.execute(
                "UPDATE mkb_object_upload_sessions SET state='consumed',terminal_at=?,row_revision=row_revision+1 "
                "WHERE upload_session_uuid=? AND state='reserved'",
                (now, session["upload_session_uuid"]),
            )
            if updated.rowcount != 1:
                return False
            await tx.execute(
                "UPDATE mkb_object_references SET released_at=? WHERE upload_session_uuid=? "
                "AND purpose='upload_pending' AND released_at IS NULL",
                (now, session["upload_session_uuid"]),
            )
        return True

    @staticmethod
    def _token_hash(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    @classmethod
    def _session_token(cls, team_uuid: str, idempotency_key: str, session_uuid: str) -> str:
        suffix = hashlib.sha256(f"{team_uuid}:{idempotency_key}:{session_uuid}".encode()).hexdigest()[:32]
        return f"mkbsession:v1:{session_uuid}:{suffix}"

    @classmethod
    async def _session_tx(cls, tx, team_uuid: str, token: str) -> dict[str, Any] | None:
        parts = token.split(":")
        if len(parts) != 4 or parts[0] != "mkbsession" or parts[1] != "v1":
            return None
        row = await tx.fetchone(
            "SELECT * FROM mkb_object_upload_sessions WHERE team_uuid=? AND upload_session_uuid=?",
            (team_uuid, parts[2]),
        )
        if row is None:
            return None
        expected = cls._session_token(team_uuid, row["idempotency_key"], row["upload_session_uuid"])
        if expected != token or cls._token_hash(token) != row["session_token_hash"]:
            return None
        return row

    async def _run_fault_hook(self, stage: str) -> None:
        if self._uow_fault_hook is None:
            return
        result = self._uow_fault_hook(stage)
        if inspect.isawaitable(result):
            await result


__all__ = ["ObjectStatusRecord", "ObjectUploadRecord", "ObjectUploadService"]
