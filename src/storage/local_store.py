"""Durable local filesystem content-addressed object store (S13)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import tempfile
from collections.abc import AsyncIterable
from datetime import UTC, datetime
from pathlib import Path
from typing import BinaryIO

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.storage.handles import digest_from_handle, object_handle
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest


# A promoted-but-not-yet-catalogued CAS handle is scoped to its Team and digest.
# The catalog can later expose an even more opaque stored-object handle, but
# this pre-transaction identity is already safe to put in a Process outcome:
# it contains no host path and cannot cross a Team's byte namespace.
class LocalObjectStore:
    """Bytes-first CAS with fsync + atomic promotion.

    A promoted object is not business-usable until its caller writes catalog and
    reference rows in a persistence transaction. A transaction failure therefore
    leaves a safe orphan for the GC scanner.
    """

    def __init__(self, root: Path, *, max_object_bytes: int = 256 * 1024 * 1024) -> None:
        self.root = root.resolve()
        self.max_object_bytes = max_object_bytes
        self._write_lock = asyncio.Lock()
        self._identity_path = self.root / "identity.json"

    def _object_path(self, team_uuid: str, digest: str) -> Path:
        return self.root / "objects" / team_uuid / "sha256" / digest[:2] / digest[2:4] / digest

    def _quarantine_path(self, team_uuid: str, digest: str) -> Path:
        return self.root / "quarantine" / team_uuid / digest

    def _ensure_root(self) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        (self.root / "objects").mkdir(mode=0o700, exist_ok=True)
        (self.root / "staging").mkdir(mode=0o700, exist_ok=True)
        (self.root / "quarantine").mkdir(mode=0o700, exist_ok=True)
        if not self._identity_path.exists():
            self._identity_path.write_text(json.dumps({"identity": uuid7()}), encoding="utf-8")
            os.chmod(self._identity_path, 0o600)
            self._fsync_file(self._identity_path)
            self._fsync_dir(self.root)

    @staticmethod
    def _fsync_file(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    @staticmethod
    def _fsync_dir(path: Path) -> None:
        descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)

    async def promote(self, data: bytes, request: PromoteRequest) -> ObjectStat:
        async def one_chunk() -> AsyncIterable[bytes]:
            yield data

        return await self.promote_stream(one_chunk(), request)

    async def promote_stream(self, chunks: AsyncIterable[bytes], request: PromoteRequest) -> ObjectStat:
        """Hash and bound an async byte stream before one atomic CAS promotion."""

        stream, temporary = await asyncio.to_thread(self._open_staging_sync)
        digest = hashlib.sha256()
        observed = 0
        try:
            async for chunk in chunks:
                if not isinstance(chunk, bytes):
                    raise MkbError("OBJECT_STREAM_CHUNK_INVALID", "Object stream yielded a non-byte chunk", 422)
                if not chunk:
                    continue
                observed += len(chunk)
                if observed > self.max_object_bytes:
                    raise MkbError("OBJECT_BUDGET_SIZE", "Object exceeds the configured size limit", 413)
                digest.update(chunk)
                await asyncio.to_thread(stream.write, chunk)
            await asyncio.to_thread(self._finish_staging_sync, stream)
            stream = None
            if observed == 0 and request.purpose == "upload_pending":
                raise MkbError("OBJECT_EMPTY", "Object upload body is empty", 422)
            content_digest = digest.hexdigest()
            if request.expected_sha256 and request.expected_sha256 != content_digest:
                raise MkbError("OBJECT_INTEGRITY_DIGEST", "Object digest does not match expected digest", 422)
            async with self._write_lock:
                return await asyncio.to_thread(
                    self._promote_staging_sync,
                    temporary,
                    content_digest,
                    observed,
                    request.team_uuid,
                    request.media_type,
                )
        finally:
            if stream is not None:
                await asyncio.to_thread(stream.close)
            await asyncio.to_thread(lambda: Path(temporary).unlink(missing_ok=True))

    def _open_staging_sync(self) -> tuple[BinaryIO, str]:
        self._ensure_root()
        descriptor, temporary = tempfile.mkstemp(prefix="promote-", dir=self.root / "staging")
        return os.fdopen(descriptor, "wb"), temporary

    @staticmethod
    def _finish_staging_sync(stream: BinaryIO) -> None:
        stream.flush()
        os.fsync(stream.fileno())
        stream.close()

    def _promote_staging_sync(
        self,
        temporary: str,
        digest: str,
        size_bytes: int,
        team_uuid: str,
        media_type: str | None,
    ) -> ObjectStat:
        target = self._object_path(team_uuid, digest)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if target.exists():
            existing_digest, existing_size = self._digest_file(target)
            if existing_digest != digest or existing_size != size_bytes:
                raise MkbError("OBJECT_INTEGRITY_COLLISION", "CAS object integrity mismatch", 503)
            Path(temporary).unlink(missing_ok=True)
        else:
            os.replace(temporary, target)
            self._fsync_dir(target.parent)
        return ObjectStat(
            handle=object_handle(team_uuid, digest),
            sha256=digest,
            size_bytes=size_bytes,
            media_type=media_type,
        )

    @staticmethod
    def _digest_file(path: Path) -> tuple[str, int]:
        digest = hashlib.sha256()
        size = 0
        with path.open("rb") as stream:
            while chunk := stream.read(1024 * 1024):
                digest.update(chunk)
                size += len(chunk)
        return digest.hexdigest(), size

    async def read_verified(self, team_uuid: str, handle: ObjectHandle) -> bytes:
        digest = digest_from_handle(team_uuid, handle)
        return await asyncio.to_thread(self._read_verified_sync, team_uuid, digest)

    def _read_verified_sync(self, team_uuid: str, digest: str) -> bytes:
        path = self._object_path(team_uuid, digest)
        if not path.exists():
            raise MkbError("OBJECT_MISSING", "Object bytes are unavailable", 404)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise MkbError("OBJECT_INTEGRITY_DIGEST", "Object bytes failed integrity verification", 503)
        return data

    async def delete_if_unreferenced(self, team_uuid: str, handle: ObjectHandle) -> bool:
        """Physical delete only; the caller must recheck DB reference/hold fences first."""

        digest = digest_from_handle(team_uuid, handle)
        path = self._object_path(team_uuid, digest)
        async with self._write_lock:
            if not path.exists():
                return False
            await asyncio.to_thread(path.unlink)
            return True

    async def quarantine_object(self, team_uuid: str, handle: ObjectHandle) -> bool:
        """Rename live bytes off the CAS path so TX2 can restore them."""

        digest = digest_from_handle(team_uuid, handle)
        source = self._object_path(team_uuid, digest)
        target = self._quarantine_path(team_uuid, digest)
        async with self._write_lock:
            return await asyncio.to_thread(self._quarantine_sync, source, target)

    @staticmethod
    def _quarantine_sync(source: Path, target: Path) -> bool:
        if not source.exists():
            return False
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.replace(source, target)
        return True

    async def restore_quarantined(self, team_uuid: str, handle: ObjectHandle) -> bool:
        digest = digest_from_handle(team_uuid, handle)
        quarantined = self._quarantine_path(team_uuid, digest)
        live = self._object_path(team_uuid, digest)
        async with self._write_lock:
            return await asyncio.to_thread(self._restore_quarantine_sync, quarantined, live)

    @staticmethod
    def _restore_quarantine_sync(quarantined: Path, live: Path) -> bool:
        if live.exists():
            if quarantined.exists():
                quarantined.unlink()
            return True
        if not quarantined.exists():
            return False
        live.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.replace(quarantined, live)
        return True

    async def destroy_quarantined(self, team_uuid: str, handle: ObjectHandle) -> None:
        digest = digest_from_handle(team_uuid, handle)
        quarantined = self._quarantine_path(team_uuid, digest)
        async with self._write_lock:
            await asyncio.to_thread(lambda: quarantined.unlink(missing_ok=True))

    async def reap_staging_before(self, cutoff: datetime) -> int:
        if cutoff.tzinfo is None:
            raise ValueError("staging cutoff must be timezone-aware")
        await asyncio.to_thread(self._ensure_root)
        async with self._write_lock:
            return await asyncio.to_thread(self._reap_staging_sync, cutoff.astimezone(UTC).timestamp())

    def _reap_staging_sync(self, cutoff_timestamp: float) -> int:
        reaped = 0
        for path in (self.root / "staging").glob("promote-*"):
            try:
                if path.is_file() and path.stat().st_mtime <= cutoff_timestamp:
                    path.unlink()
                    reaped += 1
            except FileNotFoundError:
                continue
        return reaped

    async def readiness(self) -> bool:
        try:
            await asyncio.to_thread(self._ensure_root)
            if not self._identity_path.exists() or not os.access(self.root, os.W_OK):
                return False
            payload = json.loads(self._identity_path.read_text(encoding="utf-8"))
            return isinstance(payload, dict) and isinstance(payload.get("identity"), str) and bool(payload["identity"])
        except (OSError, json.JSONDecodeError, TypeError, ValueError):
            return False
