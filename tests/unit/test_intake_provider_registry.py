"""D08 provider registry, strict schema, and architecture fences."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest
from pydantic import ValidationError

from intake import dispatch_clean
from intake.api.registry import (
    REGISTERED_PROVIDER_OPERATIONS,
    parse_registered_api_member,
    registered_provider_manifest_digest,
    resolve_provider_operation,
)
from src.contracts.api.models import RegisteredApiSourceDescriptor
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.intake.providers import ChinaTaxRawMember, DomainRawMember, RealestateRawMember
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS, clean_strategy_manifest_digest
from src.contracts.runtime.models import ProcessCommand
from src.runtime.intake.clean_preflight import IntakeCleanPreflightMixin
from src.runtime.intake.pipeline import IntakePipeline


def test_provider_registry_is_the_exact_three_operation_closed_set_and_unknown_fails() -> None:
    assert {
        (definition.provider, definition.operation, definition.definition_version)
        for definition in REGISTERED_PROVIDER_OPERATIONS
    } == {
        ("chinatax", "get_articles", "v1"),
        ("domain", "get_agency_listings", "v1"),
        ("realestate", "get_listings", "v1"),
    }
    assert len(registered_provider_manifest_digest()) == 64
    with pytest.raises(MkbError) as unsupported:
        resolve_provider_operation("chinatax", "unknown", "v1")
    assert unsupported.value.code == "CLEAN_PROVIDER_OPERATION_UNSUPPORTED"


def test_member_schemas_and_public_descriptor_forbid_extra_fields() -> None:
    for model, raw in (
        (ChinaTaxRawMember, {"id": "tax", "unexpected": True}),
        (DomainRawMember, {"id": 1, "unexpected": True}),
        (RealestateRawMember, {"listingId": "rea", "unexpected": True}),
    ):
        with pytest.raises(ValidationError):
            model.model_validate(raw)

    with pytest.raises(ValidationError):
        RegisteredApiSourceDescriptor.model_validate(
            {
                "source_kind": "registered_api",
                "external_key": "collection",
                "connector_key": "tax-fixture",
                "provider": "chinatax",
                "operation": "get_articles",
                "definition_version": "v1",
                "representation": "raw",
                "records": [{"id": "tax", "unexpected": True}],
                "exhaustion_proof": "caller_frozen_records.v1",
            }
        )


def test_parser_failure_is_typed_rejection_and_never_invents_external_key() -> None:
    with pytest.raises(MkbError) as rejected:
        parse_registered_api_member(
            {"label": "missing-id"},
            provider="chinatax",
            operation="get_articles",
            definition_version="v1",
        )
    assert rejected.value.code == "CLEAN_MEMBER_SCHEMA_INVALID"
    assert rejected.value.details == {
        "rejection_evidence": {
            "provider": "chinatax",
            "operation": "get_articles",
            "definition_version": "v1",
            "reason": "member_schema_invalid",
        }
    }


@pytest.mark.asyncio
async def test_dispatch_requires_exact_provider_operation_version() -> None:
    with pytest.raises(MkbError) as missing:
        await dispatch_clean("clean.map.registered_api", members=[{"id": "tax"}], provider="chinatax")
    assert missing.value.code == "CLEAN_PROVIDER_OPERATION_REQUIRED"


def _command(process_key: str) -> ProcessCommand:
    return ProcessCommand.model_validate(
        {
            "schema_version": "mkb.process-command.v1",
            "team_uuid": uuid7(),
            "task_uuid": uuid7(),
            "trace_uuid": uuid7(),
            "execution_uuid": uuid7(),
            "process_uuid": uuid7(),
            "process_key": process_key,
            "process_contract_version": "v1",
            "fencing_generation": 1,
            "command_input_digest": "a" * 64,
            "input_manifest_ref": "mkbtest:input:x",
            "input_manifest_digest": "b" * 64,
            "config_snapshot_ref": "mkbtest:config:x",
            "config_snapshot_digest": "c" * 64,
            "binding_digest": "d" * 64,
        }
    )


@pytest.mark.asyncio
async def test_empty_collection_without_exhaustion_proof_cannot_seal_complete() -> None:
    pipeline = IntakePipeline(None, None, None)  # type: ignore[arg-type]
    with pytest.raises(MkbError) as rejected:
        await pipeline._seal_registered_api_collection(
            _command("intake.collection.seal"),
            {
                "collection_members": [],
                "candidate_root_digest": "e" * 64,
                "collection_exhaustion_proof": None,
            },
        )
    assert rejected.value.code == "SCATTER_EXHAUSTION_PROOF_REQUIRED"


def test_clean_strategy_registry_is_versioned_and_complete() -> None:
    assert {definition.strategy_key.value for definition in CLEAN_STRATEGY_DEFINITIONS} == {
        "web.deterministic",
        "web.llm_rewrite",
        "web.browser_print_pdf",
        "pdf.text_layer",
        "pdf.document_understanding",
        "pdf.ocr",
        "doc.deterministic",
        "doc.document_understanding",
        "doc.ocr",
        "doc.vision",
    }
    assert len(clean_strategy_manifest_digest()) == 64
    assert all(len(definition.definition_digest) == 64 for definition in CLEAN_STRATEGY_DEFINITIONS)


def test_runtime_has_one_clean_transform_entry_and_no_legacy_or_vendor_url_dependency() -> None:
    source = inspect.getsource(IntakeCleanPreflightMixin)
    assert "dispatch_clean" in source
    assert "HTMLParser" not in source
    assert "parse_registered_api_member" not in source

    repository = Path(__file__).resolve().parents[2]
    production = "\n".join(
        path.read_text(encoding="utf-8")
        for root in (repository / "intake", repository / "src")
        for path in root.rglob("*.py")
    ).casefold()
    for forbidden in (
        "legacy-family",
        "chinatax.sourcemind",
        "services.realestate.com.au",
        "cloudflare.com/client",
    ):
        assert forbidden not in production
