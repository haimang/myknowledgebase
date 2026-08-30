"""Bounded periodic scheduling for upload hold expiry and staging cleanup."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import timedelta

from src.services.object_upload_ttl import ObjectUploadLifecycleResult, ObjectUploadLifecycleService

_LOG = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class ObjectUploadLifecycleSchedule:
    interval: timedelta = timedelta(minutes=10)
    batch_size: int = 100

    def __post_init__(self) -> None:
        if self.interval <= timedelta(0):
            raise ValueError("object upload lifecycle interval must be greater than zero")
        if not 1 <= self.batch_size <= 10_000:
            raise ValueError("object upload lifecycle batch_size must be between 1 and 10000")


class ObjectUploadLifecycleScanner:
    def __init__(
        self,
        service: ObjectUploadLifecycleService,
        schedule: ObjectUploadLifecycleSchedule | None = None,
    ) -> None:
        self._service = service
        self._schedule = schedule or ObjectUploadLifecycleSchedule()

    async def run_once(self) -> ObjectUploadLifecycleResult:
        return await self._service.scan_once(limit=self._schedule.batch_size)

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                _LOG.exception("object upload lifecycle scan failed")
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._schedule.interval.total_seconds())
            except TimeoutError:
                continue


__all__ = ["ObjectUploadLifecycleScanner", "ObjectUploadLifecycleSchedule"]
