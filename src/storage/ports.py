"""Object storage port; no service touches ``object_root`` directly."""

from __future__ import annotations

from collections.abc import AsyncIterable
from datetime import datetime
from typing import Protocol, runtime_checkable

from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest


@runtime_checkable
class ObjectStorePort(Protocol):
    async def promote(self, data: bytes, request: PromoteRequest) -> ObjectStat: ...

    async def promote_stream(self, chunks: AsyncIterable[bytes], request: PromoteRequest) -> ObjectStat: ...

    async def read_verified(self, team_uuid: str, handle: ObjectHandle) -> bytes: ...

    async def delete_if_unreferenced(self, team_uuid: str, handle: ObjectHandle) -> bool: ...

    async def quarantine_object(self, team_uuid: str, handle: ObjectHandle) -> bool: ...

    async def restore_quarantined(self, team_uuid: str, handle: ObjectHandle) -> bool: ...

    async def destroy_quarantined(self, team_uuid: str, handle: ObjectHandle) -> None: ...

    async def reap_staging_before(self, cutoff: datetime) -> int: ...

    async def readiness(self) -> bool: ...
