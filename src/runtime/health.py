"""S15 readiness aggregation. Liveness lives outside this object by design."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from src.runtime.metrics import MetricRegistry

ReadinessProbe = Callable[[], Awaitable[dict[str, bool]]]


class HealthAggregator:
    REQUIRED = (
        "schema_migration",
        "registry_bootstrap",
        "db_primary",
        "concurrent_writes",
        "native_vector",
        "object_root",
        "inference_binding",
        "obs_tables",
        "sec_token_loaded",
    )

    def __init__(self, probe: ReadinessProbe, metrics: MetricRegistry, *, ttl_seconds: float = 0.5) -> None:
        self._probe = probe
        self._metrics = metrics
        self._ttl_seconds = ttl_seconds
        self._lock = asyncio.Lock()
        self._inflight: asyncio.Task[dict[str, object]] | None = None
        self.bootstrap_failures = 0

    async def ready(self) -> dict[str, object]:
        async with self._lock:
            inflight = self._inflight
            if inflight is None:
                inflight = asyncio.create_task(self._compute())
                self._inflight = inflight
        try:
            return await inflight
        finally:
            if self._inflight is inflight:
                self._inflight = None

    async def _compute(self) -> dict[str, object]:
        supplied = await self._probe()
        if self.bootstrap_failures:
            supplied = {**supplied, "registry_bootstrap": False}
        components = [
            {
                "name": name,
                "ok": bool(supplied.get(name, False)),
                "code": None if supplied.get(name, False) else "not_ready",
            }
            for name in self.REQUIRED
        ]
        for component in components:
            self._metrics.set("mkb_readiness", float(component["ok"]), component=component["name"])
        is_ready = all(component["ok"] for component in components)
        return {"status": "ready" if is_ready else "not_ready", "live": True, "components": components}
