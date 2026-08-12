"""Readiness composition regressions for worker claims and vector backends."""

from __future__ import annotations

from pathlib import Path

import pytest

from api.app import create_container
from src.contracts.common.errors import NotReadyError
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.config import Settings
from src.runtime.health import HealthAggregator


@pytest.mark.asyncio
async def test_sqlite_never_mistakes_compatibility_btree_for_native_ann(tmp_path: Path) -> None:
    persistence = SqlitePersistence(
        tmp_path / "native-ann.sqlite3",
        Path("src/persistence/migrations"),
        vector_backend="native_ann",
    )
    try:
        await persistence.migrate()
        readiness = await persistence.readiness()
        assert readiness["schema_migration"]
        assert not readiness["native_vector"]
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_explicit_deterministic_exact_profile_is_ready(tmp_path: Path) -> None:
    persistence = SqlitePersistence(
        tmp_path / "deterministic.sqlite3",
        Path("src/persistence/migrations"),
        vector_backend="deterministic_exact",
    )
    try:
        await persistence.migrate()
        readiness = await persistence.readiness()
        assert readiness["native_vector"]
    finally:
        await persistence.close()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "unready_component",
    ("registry_bootstrap", "object_root", "inference_binding", "sec_token_loaded"),
)
async def test_app_worker_claims_use_full_health_closure(tmp_path: Path, unready_component: str) -> None:
    """A persistence-only check must not let a worker claim new work."""

    container = create_container(
        Settings(
            internal_token="readiness-token",
            database_path=tmp_path / "claims.sqlite3",
            object_root=tmp_path / "objects",
            vector_backend="deterministic_exact",
        )
    )
    try:
        calls = 0

        async def probe() -> dict[str, bool]:
            nonlocal calls
            calls += 1
            return {name: name != unready_component for name in HealthAggregator.REQUIRED}

        # The runtime closure resolves this current container field at claim
        # time. Replacing it makes every required health component observable
        # here without weakening the real application probe's ownership.
        container.health = HealthAggregator(probe, container.metrics)
        with pytest.raises(NotReadyError, match="workflow-not-ready"):
            await container.workflow_runtime.claim_next("readiness-test-worker")
        assert calls == 1
    finally:
        await container.persistence.close()


@pytest.mark.asyncio
async def test_app_claim_readiness_uses_the_real_aggregator_after_bootstrap(tmp_path: Path) -> None:
    container = create_container(
        Settings(
            internal_token="readiness-token",
            database_path=tmp_path / "bootstrapped.sqlite3",
            object_root=tmp_path / "objects",
            vector_backend="deterministic_exact",
        )
    )
    try:
        await container.persistence.migrate()
        await container.registry.bootstrap()
        await container.workflows.bootstrap()
        assert (await container.health.ready())["status"] == "ready"

        container.tokens.replace(())
        assert (await container.health.ready())["status"] == "not_ready"
        with pytest.raises(NotReadyError, match="workflow-not-ready"):
            await container.workflow_runtime.claim_next("token-fenced-worker")
    finally:
        await container.persistence.close()
