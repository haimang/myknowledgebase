"""S15 readiness aggregation. Liveness lives outside this object by design."""

from __future__ import annotations

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

    def __init__(self, probe: ReadinessProbe, metrics: MetricRegistry) -> None:
        self._probe = probe
        self._metrics = metrics

    async def ready(self) -> dict[str, object]:
        supplied = await self._probe()
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
