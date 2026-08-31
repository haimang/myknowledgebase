"""NHX1-T22-E: the 10+3 surface and missing-supply claim fence are explicit."""

from __future__ import annotations

from pathlib import Path

from api.app import create_container
from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS
from src.runtime.config import Settings
from src.runtime.workflow.capability_registry import DEFAULT_PROCESS_CAPABILITY_REGISTRY
from src.workflows.builtin_lsrag import BUILTIN_WORKFLOWS
from src.workflows.builtin_scatter import BUILTIN_SCATTER_WORKFLOWS


def test_ten_clean_strategies_and_three_registered_operations_are_closed() -> None:
    assert len(CLEAN_STRATEGY_DEFINITIONS) == 10
    assert len({item.strategy_key for item in CLEAN_STRATEGY_DEFINITIONS}) == 10
    assert len(REGISTERED_PROVIDER_OPERATIONS) == 3
    assert len({(item.provider, item.operation, item.definition_version) for item in REGISTERED_PROVIDER_OPERATIONS}) == 3
    manifests = DEFAULT_PROCESS_CAPABILITY_REGISTRY.required_for((*BUILTIN_WORKFLOWS, *BUILTIN_SCATTER_WORKFLOWS))
    assert all(item.handler_key == "intake_pipeline" for item in manifests)
    assert all(item.definition_digest for item in manifests)


def test_missing_native_supply_is_removed_from_worker_claim_set(tmp_path: Path) -> None:
    container = create_container(
        Settings(
            internal_token="nhx1-gate-token",
            database_path=tmp_path / "gate.db",
            object_root=tmp_path / "objects",
            persistence_backend="turso",
            concurrent_writes_required=False,
            native_vector_required=False,
            deployment_role="workflow_worker",
            runtime_supply_readiness_required=True,
            pdf_parser_enabled=False,
            browser_runtime_enabled=False,
            deterministic_ocr_enabled=False,
            multimodal_enabled=False,
        )
    )
    try:
        claimable = container.workflow_runtime.claimable_process_keys
        assert claimable is not None
        assert "intake.decode.pdf" not in claimable
        assert "intake.acquire.http_browser" not in claimable
        assert "clean.ocr.local" not in claimable
        assert "clean.extract.doc_llm" not in claimable
        assert "intake.acquire.inline" in claimable
    finally:
        import asyncio

        asyncio.run(container.persistence.close())
