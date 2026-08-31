"""NHX1-T21: deployment ownership and capability readiness are explicit."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import _health_required, create_app
from src.contracts.common.errors import MkbError
from src.runtime.config import Settings
from src.runtime.health import HealthAggregator
from src.runtime.roles import DeploymentRole, role_spec
from src.runtime.workflow.capability_registry import DEFAULT_PROCESS_CAPABILITY_REGISTRY


def _settings(tmp_path: Path, role: str, **overrides: object) -> Settings:
    return Settings(
        internal_token="nhx1-role-token",
        database_path=tmp_path / f"{role}.sqlite3",
        object_root=tmp_path / f"{role}-objects",
        persistence_backend="sqlite",
        concurrent_writes_required=False,
        native_vector_required=False,
        inference_probe_enabled=False,
        live_inference=False,
        deployment_role=role,  # type: ignore[arg-type]
        rate_limit_ip_per_min=10_000,
        rate_limit_token_per_min=10_000,
        **overrides,
    )


def test_role_specs_are_disjoint_and_all_is_explicit() -> None:
    assert role_spec(DeploymentRole.API).owns_api
    assert not role_spec(DeploymentRole.API).owns_workflow_claims
    assert role_spec("workflow_worker").owns_workflow_claims
    assert not role_spec("workflow_worker").owns_maintenance
    assert role_spec("maintenance").owns_maintenance
    assert not role_spec("maintenance").owns_workflow_claims
    assert role_spec("all").loop_names == (
        "workflow_supervisor",
        "object_gc",
        "object_upload_lifecycle",
        "index_retirement",
        "observability_retention",
    )


def test_capability_manifest_is_closed_and_supply_aware() -> None:
    registry = DEFAULT_PROCESS_CAPABILITY_REGISTRY
    assert len(registry.manifests) >= 20
    assert len({item.process_key for item in registry.manifests}) == len(registry.manifests)
    assert registry.definition_digest == registry.definition_digest
    browser = registry.resolve("intake.acquire.http_browser")
    assert browser.handler_key == "intake_pipeline"
    assert set(browser.supply_requirements) == {"browser.render", "browser.print_pdf"}
    with pytest.raises(MkbError, match="not registered"):
        registry.resolve("unknown.process")
    availability = registry.availability({"browser.render": True, "browser.print_pdf": False})
    browser_status = next(item for item in availability if item["process_key"] == browser.process_key)
    assert browser_status["available"] is False
    assert browser_status["missing_supplies"] == ["browser.print_pdf"]


def test_role_health_required_sets_do_not_claim_worker_components(tmp_path: Path) -> None:
    api_required = _health_required(_settings(tmp_path, "api"))
    maintenance_required = _health_required(_settings(tmp_path, "maintenance"))
    worker_required = _health_required(_settings(tmp_path, "workflow_worker"))
    assert "workflow_supervisor" not in api_required
    assert "inference_binding" not in api_required
    assert "workflow_supervisor" not in maintenance_required
    assert "workflow_supervisor" in worker_required
    assert worker_required == HealthAggregator.BASE_REQUIRED


def test_api_role_does_not_start_worker_or_maintenance_loops(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path, "api"))
    with TestClient(app, raise_server_exceptions=True) as client:
        ready = client.get("/ready")
        assert ready.status_code == 200, ready.text
        async def task_names() -> tuple[str, ...]:
            return tuple(sorted(task.get_name() for task in asyncio.all_tasks() if not task.done()))

        names = client.portal.call(task_names)
        assert "mkb-workflow-supervisor" not in names
        assert "mkb-object-gc" not in names
        assert "mkb-observability-retention" not in names
        assert ready.json()["status"] == "ready"
        assert ready.json()["deployment_role"] == "api"
        assert ready.json()["owned_loops"] == []

        async def capability_rows() -> int:
            async with app.state.container.persistence.read_snapshot() as tx:
                row = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_process_capability_definitions")
            assert row is not None
            return int(row["count"])

        assert client.portal.call(capability_rows) >= 20


def test_worker_role_claims_are_filtered_by_explicit_allowlist(tmp_path: Path) -> None:
    app = create_app(
        _settings(
            tmp_path,
            "workflow_worker",
            worker_capability_allowlist="intake.acquire.inline",
        )
    )
    assert app.state.container.workflow_runtime.claimable_process_keys == frozenset({"intake.acquire.inline"})


def test_prod_profile_rejects_stub_and_missing_supply_gate() -> None:
    with pytest.raises(ValueError, match="subprocess NS1"):
        Settings(runtime_profile="prod")
    with pytest.raises(ValueError, match="supply readiness"):
        Settings(runtime_profile="prod", ns1_cli_mode="subprocess")
    with pytest.raises(ValueError, match="multimodal"):
        Settings(
            runtime_profile="prod",
            ns1_cli_mode="subprocess",
            runtime_supply_readiness_required=True,
        )
