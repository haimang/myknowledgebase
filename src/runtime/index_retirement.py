"""Cooperative scheduling for fenced S09 old-generation retirement."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from datetime import timedelta

from src.services.index_retirement import IndexGenerationRetirementScanResult, IndexGenerationRetirementService


@dataclass(frozen=True, slots=True)
class IndexGenerationRetirementSchedule:
    """Runtime cadence only; S09 ownership stays in the durable service."""

    interval: timedelta = timedelta(minutes=10)
    batch_size: int = 100

    def __post_init__(self) -> None:
        if self.interval <= timedelta(0):
            raise ValueError("index generation retirement interval must be greater than zero")
        if not 1 <= self.batch_size <= 10_000:
            raise ValueError("index generation retirement batch_size must be between 1 and 10000")


class IndexGenerationRetirementScanner:
    """Run discovery plus due soft-purge without exposing a business endpoint."""

    def __init__(
        self,
        service: IndexGenerationRetirementService,
        schedule: IndexGenerationRetirementSchedule | None = None,
    ) -> None:
        self._service = service
        self._schedule = schedule or IndexGenerationRetirementSchedule()

    async def run_once(self) -> IndexGenerationRetirementScanResult:
        return await self._service.scan_once(limit=self._schedule.batch_size)

    async def run_forever(self, stop_event: asyncio.Event) -> None:
        while not stop_event.is_set():
            await self.run_once()
            try:
                await asyncio.wait_for(stop_event.wait(), timeout=self._schedule.interval.total_seconds())
            except TimeoutError:
                continue


__all__ = ["IndexGenerationRetirementScanner", "IndexGenerationRetirementSchedule"]
