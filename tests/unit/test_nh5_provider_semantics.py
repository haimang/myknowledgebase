"""NH5-T02: registered provider mappers cannot manufacture unknown authority."""

from __future__ import annotations

import inspect

import pytest
from pydantic import ValidationError

from intake.api.providers.chinatax import parse_chinatax_member
from intake.api.providers.domain import parse_domain_member
from intake.api.providers.realestate import parse_realestate_member
from intake.api.registry import (
    REGISTERED_PROVIDER_OPERATIONS,
    assert_declared_provider_semantics,
)
from src.contracts.api.models import RegisteredApiSourceDescriptor
from src.contracts.common.errors import MkbError
from src.contracts.intake.providers import ChinaTaxRawMember, DomainRawMember, RealestateRawMember


def test_provider_registry_defaults_to_no_optional_unknown_fields() -> None:
    assert all(definition.optional_unknown_fields == () for definition in REGISTERED_PROVIDER_OPERATIONS)


@pytest.mark.parametrize("field", ["label", "column"])
def test_chinatax_required_semantics_fail_when_missing(field: str) -> None:
    payload = {"id": "tax", "label": "公告", "column": "政策法规", "title": "title", "content": "body"}
    payload[field] = None
    with pytest.raises(ValueError, match=field):
        parse_chinatax_member(ChinaTaxRawMember.model_validate(payload))


@pytest.mark.parametrize(
    ("field", "value"),
    [("status", None), ("saleMode", None), ("channel", None), ("propertyTypes", [])],
)
def test_domain_required_semantics_fail_when_missing(field: str, value: object) -> None:
    payload = {
        "id": 1,
        "headline": "title",
        "description": "body",
        "status": "live",
        "saleMode": "buy",
        "channel": "residential",
        "propertyTypes": ["House"],
    }
    payload[field] = value
    with pytest.raises(ValueError):
        parse_domain_member(DomainRawMember.model_validate(payload))


@pytest.mark.parametrize("field", ["channel", "agency"])
def test_realestate_required_semantics_fail_when_missing(field: str) -> None:
    payload = {
        "listingId": "rea",
        "channel": "sold",
        "title": "title",
        "description": "body",
        "agency": {"name": "Agency", "agencyId": "1"},
    }
    payload[field] = None
    with pytest.raises(ValueError):
        parse_realestate_member(RealestateRawMember.model_validate(payload))


def test_caller_duplicate_semantics_are_equality_fences() -> None:
    mapped = parse_chinatax_member(
        ChinaTaxRawMember(id="tax", label="公告", column="政策法规", title="title", content="body")
    )
    assert_declared_provider_semantics(
        {"realm": "tax_china", "type": "公告", "channel": "政策法规", "source_name": "chinatax.gov.cn"},
        mapped,
    )
    with pytest.raises(MkbError) as raised:
        assert_declared_provider_semantics({"realm": "caller-overrides-mapper"}, mapped)
    assert raised.value.code == "CLEAN_SEMANTIC_CONFLICT"
    assert raised.value.status_code == 422

    base = {
        "source_kind": "registered_api",
        "external_key": "tax",
        "connector_key": "fixture",
        "provider": "chinatax",
        "operation": "get_articles",
        "definition_version": "v1",
        "records": [{"id": "tax", "label": "公告", "column": "政策法规", "title": "title", "content": "body"}],
    }
    accepted = RegisteredApiSourceDescriptor.model_validate({**base, "realm": "tax_china"})
    assert accepted.realm == "tax_china"
    with pytest.raises(ValidationError):
        RegisteredApiSourceDescriptor.model_validate({**base, "realm": "caller-overrides-mapper"})


def test_provider_sources_have_no_automatic_unknown_fallback() -> None:
    source = "\n".join(
        inspect.getsource(module)
        for module in (parse_chinatax_member, parse_domain_member, parse_realestate_member)
    ).casefold()
    assert 'or "unknown"' not in source
    assert "or 'unknown'" not in source
    assert "unknown agency" not in source
