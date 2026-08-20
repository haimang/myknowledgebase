"""NS6-T02 / T08: default Turso ready+claim, and sequential TTL cache."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.app import create_container
from src.runtime.config import Settings
from src.runtime.health import HealthAggregator
from src.runtime.metrics import MetricRegistry


@pytest.mark.asyncio
async def test_default_turso_settings_are_ready_and_can_claim(tmp_path: Path) -> None:
    settings = Settings(
        internal_token="ns6-default-ready-token",
        database_path=tmp_path / "mkb.db",
        object_root=tmp_path / "objects",
    )
    assert settings.persistence_backend == "turso"
    assert settings.concurrent_writes_required is True
    assert settings.native_vector_required is True

    container = create_container(settings)
    try:
        await container.persistence.migrate()
        await container.registry.bootstrap()
        await container.workflows.bootstrap()
        ready = await container.health.ready()
        assert ready["status"] == "ready", ready
        names = {item["name"]: item["ok"] for item in ready["components"]}
        assert names["write_path_ready"] is True
        persistence_ready = await container.persistence.readiness()
        assert persistence_ready["concurrent_writes"] is False
        assert "concurrent_writes_probe" in persistence_ready
        claimed = await container.workflow_runtime.claim_next("ns6-default-worker")
        assert claimed is None
    finally:
        await container.persistence.close()


@pytest.mark.asyncio
async def test_health_ttl_returns_cached_result_on_sequential_ready() -> None:
    calls = {"n": 0}

    async def probe() -> dict[str, bool]:
        calls["n"] += 1
        return {name: True for name in HealthAggregator.REQUIRED}

    health = HealthAggregator(probe, MetricRegistry(), ttl_seconds=5)
    first = await health.ready()
    second = await health.ready()
    assert first["status"] == "ready"
    assert second["status"] == "ready"
    assert calls["n"] == 1
