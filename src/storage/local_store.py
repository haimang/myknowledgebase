"""Durable local filesystem content-addressed object store (S13)."""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest

_HANDLE_ID = re.compile(r"^mkbobj:v1:([0-9a-f]{64})$")


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

    def _object_path(self, digest: str) -> Path:
        return self.root / "cas" / digest[:2] / digest[2:4] / digest

    def _ensure_root(self) -> None:
        self.root.mkdir(mode=0o700, parents=True, exist_ok=True)
        (self.root / "cas").mkdir(mode=0o700, exist_ok=True)
        (self.root / "staging").mkdir(mode=0o700, exist_ok=True)
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
        if len(data) > self.max_object_bytes:
            raise MkbError("OBJECT_BUDGET_SIZE", "Object exceeds the configured size limit", 413)
        digest = hashlib.sha256(data).hexdigest()
        if request.expected_sha256 and request.expected_sha256 != digest:
            raise MkbError("OBJECT_INTEGRITY_DIGEST", "Object digest does not match expected digest", 422)
        async with self._write_lock:
            return await asyncio.to_thread(self._promote_sync, data, digest, request.media_type)

    def _promote_sync(self, data: bytes, digest: str, media_type: str | None) -> ObjectStat:
        self._ensure_root()
        target = self._object_path(digest)
        target.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        if target.exists():
            existing = target.read_bytes()
            if hashlib.sha256(existing).hexdigest() != digest:
                raise MkbError("OBJECT_INTEGRITY_COLLISION", "CAS object integrity mismatch", 503)
        else:
            descriptor, temporary = tempfile.mkstemp(prefix="promote-", dir=self.root / "staging")
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
                    stream.flush()
                    os.fsync(stream.fileno())
                os.replace(temporary, target)
                self._fsync_dir(target.parent)
            finally:
                if os.path.exists(temporary):
                    os.unlink(temporary)
        return ObjectStat(
            handle=ObjectHandle(value=f"mkbobj:v1:{digest}"),
            sha256=digest,
            size_bytes=len(data),
            media_type=media_type,
        )

    async def read_verified(self, team_uuid: str, handle: ObjectHandle) -> bytes:
        del team_uuid  # Team authorization is enforced by the catalog/reference port.
        match = _HANDLE_ID.match(handle.value)
        if not match:
            raise MkbError("SEC_PATH_REJECTED", "Object handle is invalid", 422)
        return await asyncio.to_thread(self._read_verified_sync, match.group(1))

    def _read_verified_sync(self, digest: str) -> bytes:
        path = self._object_path(digest)
        if not path.exists():
            raise MkbError("OBJECT_MISSING", "Object bytes are unavailable", 404)
        data = path.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise MkbError("OBJECT_INTEGRITY_DIGEST", "Object bytes failed integrity verification", 503)
        return data

    async def delete_if_unreferenced(self, team_uuid: str, handle: ObjectHandle) -> bool:
        """Physical delete only; the caller must recheck DB reference/hold fences first."""

        del team_uuid
        match = _HANDLE_ID.match(handle.value)
        if not match:
            raise MkbError("SEC_PATH_REJECTED", "Object handle is invalid", 422)
        path = self._object_path(match.group(1))
        if not path.exists():
            return False
        await asyncio.to_thread(path.unlink)
        return True

    async def readiness(self) -> bool:
        try:
            await asyncio.to_thread(self._ensure_root)
            return self._identity_path.exists() and os.access(self.root, os.W_OK)
        except OSError:
            return False
