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
async def test_sqlite_constitution_defaults_do_not_report_cw_or_native_vector(tmp_path: Path) -> None:
    persistence = SqlitePersistence(
        tmp_path / "constitution.sqlite3",
        Path("src/persistence/migrations"),
        concurrent_writes_required=True,
        native_vector_required=True,
    )
    try:
        await persistence.migrate()
        readiness = await persistence.readiness()
        assert readiness["schema_migration"]
        assert readiness["concurrent_writes"] is False
        assert readiness["native_vector"] is False
        assert readiness["concurrent_writes_probe"] is False
        assert readiness["native_vector_probe"] is False
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_sqlite_never_mistakes_compatibility_btree_for_native_ann(tmp_path: Path) -> None:
    persistence = SqlitePersistence(
        tmp_path / "native-ann.sqlite3",
        Path("src/persistence/migrations"),
        vector_backend="native_ann",
        concurrent_writes_required=True,
        native_vector_required=True,
    )
    try:
        await persistence.migrate()
        readiness = await persistence.readiness()
        assert readiness["schema_migration"]
        assert not readiness["native_vector"]
        assert not readiness["native_vector_probe"]
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_explicit_local_waiver_is_opt_in_not_engine_evidence(tmp_path: Path) -> None:
    persistence = SqlitePersistence(
        tmp_path / "waiver.sqlite3",
        Path("src/persistence/migrations"),
        vector_backend="deterministic_exact",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    try:
        await persistence.migrate()
        readiness = await persistence.readiness()
        assert readiness["native_vector"] is True
        assert readiness["concurrent_writes"] is True
        assert readiness["native_vector_probe"] is False
        assert readiness["concurrent_writes_probe"] is False
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
            persistence_backend="sqlite",
            concurrent_writes_required=False,
            native_vector_required=False,
        )
    )
    try:
        calls = 0

        async def probe() -> dict[str, bool]:
            nonlocal calls
            calls += 1
            return {name: name != unready_component for name in HealthAggregator.REQUIRED}

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
            persistence_backend="sqlite",
            concurrent_writes_required=False,
            native_vector_required=False,
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


@pytest.mark.asyncio
async def test_constitution_defaults_make_stock_sqlite_app_not_ready(tmp_path: Path) -> None:
    container = create_container(
        Settings(
            internal_token="readiness-token",
            database_path=tmp_path / "constitution-app.sqlite3",
            object_root=tmp_path / "objects",
            persistence_backend="sqlite",
        )
    )
    try:
        await container.persistence.migrate()
        await container.registry.bootstrap()
        await container.workflows.bootstrap()
        ready = await container.health.ready()
        assert ready["status"] == "not_ready"
        names = {item["name"]: item["ok"] for item in ready["components"]}
        assert names["concurrent_writes"] is False
        assert names["native_vector"] is False
    finally:
        await container.persistence.close()
