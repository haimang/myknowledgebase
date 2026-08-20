"""S15 readiness aggregation. Liveness lives outside this object by design."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Awaitable, Callable

from src.runtime.metrics import MetricRegistry

ReadinessProbe = Callable[[], Awaitable[dict[str, bool]]]
CacheFingerprint = Callable[[], object]


class HealthAggregator:
    REQUIRED = (
        "schema_migration",
        "registry_bootstrap",
        "db_primary",
        "write_path_ready",
        "native_vector",
        "object_root",
        "inference_binding",
        "obs_tables",
        "sec_token_loaded",
    )

    def __init__(
        self,
        probe: ReadinessProbe,
        metrics: MetricRegistry,
        *,
        ttl_seconds: float = 0.5,
        cache_fingerprint: CacheFingerprint | None = None,
    ) -> None:
        self._probe = probe
        self._metrics = metrics
        self._ttl_seconds = ttl_seconds
        self._cache_fingerprint = cache_fingerprint
        self._lock = asyncio.Lock()
        self._inflight: asyncio.Task[dict[str, object]] | None = None
        self._last_result: dict[str, object] | None = None
        self._last_at: float | None = None
        self._last_bootstrap_failures = 0
        self._last_fingerprint: object = None
        self.bootstrap_failures = 0

    def invalidate(self) -> None:
        self._last_result = None
        self._last_at = None
        self._last_fingerprint = None

    def _fingerprint(self) -> object:
        if self._cache_fingerprint is None:
            return None
        return self._cache_fingerprint()

    def _cache_valid(self, now: float) -> bool:
        if self._ttl_seconds <= 0 or self._last_result is None or self._last_at is None:
            return False
        if (now - self._last_at) >= self._ttl_seconds:
            return False
        if self._last_bootstrap_failures != self.bootstrap_failures:
            return False
        return self._last_fingerprint == self._fingerprint()

    async def ready(self) -> dict[str, object]:
        async with self._lock:
            now = time.monotonic()
            if self._cache_valid(now):
                assert self._last_result is not None
                return self._last_result
            captured = self._fingerprint()
            inflight = self._inflight
            if inflight is None:
                inflight = asyncio.create_task(self._compute())
                self._inflight = inflight
        try:
            result = await inflight
        finally:
            if self._inflight is inflight:
                self._inflight = None
        async with self._lock:
            self._last_result = result
            self._last_bootstrap_failures = self.bootstrap_failures
            self._last_fingerprint = captured
            if self._fingerprint() != captured:
                self._last_at = None
            else:
                self._last_at = time.monotonic()
        return result

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
