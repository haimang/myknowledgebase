"""Bounded background scheduling for the S13 object-GC protocol.

Scheduling and metrics belong to runtime/ops, while the durable deletion
protocol remains in :mod:`src.services.object_gc`.  Application composition
can attach this scanner to its existing supervisor without exposing an object
HTTP surface or giving business services filesystem access.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from src.services.object_gc import ObjectGcScanResult, ObjectGcService


@dataclass(frozen=True, slots=True)
class ObjectGcSchedule:
    """Runtime-only cadence; S13 fixes semantics, not an exact interval."""

    interval: timedelta = timedelta(minutes=10)
    batch_size: int = 100

    def __post_init__(self) -> None:
        if self.interval <= timedelta(0):
            raise ValueError("object GC interval must be greater than zero")
        if not 1 <= self.batch_size <= 10_000:
            raise ValueError("object GC batch_size must be between 1 and 10000")


class ObjectGcScanner:
    """Cooperative periodic runner with an explicit stop event."""

    def __init__(self, service: ObjectGcService, schedule: ObjectGcSchedule | None = None) -> None:
        self._service = service
        self._schedule = schedule or ObjectGcSchedule()

    async def run_once(self) -> ObjectGcScanResult:
        return await self._service.scan_once(limit=self._schedule.batch_size)

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        """Run until stopped, never using an uninterruptible sleep."""

        while not stop_event.is_set():
            try:
                await self.run_once()
            except asyncio.CancelledError:
                raise
            except Exception:
                # One BUSY / adapter failure must not stop the only scanner.
                timeout = max(self._schedule.interval.total_seconds(), 1.0)
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=timeout)
                except TimeoutError:
                    continue
                return
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._schedule.interval.total_seconds())
            except TimeoutError:
                continue


__all__ = ["ObjectGcScanner", "ObjectGcSchedule"]
