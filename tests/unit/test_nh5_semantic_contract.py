"""NH5-T01: generic sources require caller-owned nonunknown semantic dimensions."""

from __future__ import annotations

from copy import deepcopy

import pytest
from pydantic import ValidationError

from src.contracts.api.models import HttpSourceDescriptor, InlineSourceDescriptor, LocalObjectSourceDescriptor

BASE = {
    "realm": "documentation",
    "type": "article",
    "channel": "summary",
    "source_name": "owner-authored",
    "context_tags": ["product: mkb", "phase: nh5"],
}


@pytest.mark.parametrize(
    ("model", "specific"),
    [
        (
            InlineSourceDescriptor,
            {"source_kind": "inline_payload", "external_key": "inline", "content": "semantic body"},
        ),
        (
            LocalObjectSourceDescriptor,
            {
                "source_kind": "local_object",
                "external_key": "local",
                "logical_handle": "mkbobj:v1:11111111-1111-4111-8111-111111111111:" + "a" * 64,
            },
        ),
        (
            HttpSourceDescriptor,
            {"source_kind": "http_resource", "external_key": "http", "url": "https://public.example/doc"},
        ),
    ],
)
def test_generic_descriptor_requires_all_four_semantic_fields(model, specific: dict) -> None:
    valid = {**specific, **BASE}
    parsed = model.model_validate(valid)
    assert parsed.realm == "documentation"
    assert parsed.channel == "summary"  # business values are not the vector-channel enum
    assert parsed.context_tags == BASE["context_tags"]
    for key in ("realm", "type", "channel", "source_name"):
        missing = deepcopy(valid)
        missing.pop(key)
        with pytest.raises(ValidationError):
            model.model_validate(missing)


@pytest.mark.parametrize("value", ["unknown", "Unknown", "  unknown  ", "   "])
def test_generic_semantic_unknown_and_blank_are_rejected(value: str) -> None:
    payload = {
        "source_kind": "inline_payload",
        "external_key": "inline",
        "content": "semantic body",
        **BASE,
        "realm": value,
    }
    with pytest.raises(ValidationError):
        InlineSourceDescriptor.model_validate(payload)


def test_is_active_is_system_owned_and_payload_extra_cannot_supply_semantics() -> None:
    with pytest.raises(ValidationError):
        InlineSourceDescriptor.model_validate(
            {
                "source_kind": "inline_payload",
                "external_key": "inline",
                "content": "semantic body",
                **BASE,
                "is_active": 1,
            }
        )
    with pytest.raises(ValidationError):
        InlineSourceDescriptor.model_validate(
            {
                "source_kind": "inline_payload",
                "external_key": "inline",
                "content": "semantic body",
                "payload_extra": BASE,
            }
        )
