"""Canonical semantic surface shared by registered-API providers."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any, Literal

from pydantic import Field, field_validator

from src.contracts.common.models import StrictModel

SemanticProvenance = Literal["caller", "mapper", "system"]


class FilterMeta(StrictModel):
    """The five versioned filter dimensions required by D08-T007."""

    realm: str = Field(min_length=1, max_length=256)
    type: str = Field(min_length=1, max_length=256)
    channel: str = Field(min_length=1, max_length=256)
    source_name: str = Field(min_length=1, max_length=512)
    is_active: Literal[0, 1]

    @field_validator("realm", "type", "channel", "source_name")
    @classmethod
    def reject_unknown(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized or normalized.casefold() == "unknown":
            raise ValueError("FilterMeta values must be non-empty and cannot be unknown")
        return normalized


class ContextMeta(StrictModel):
    realm: str = Field(min_length=1, max_length=256)
    type: str = Field(min_length=1, max_length=256)
    channel: str = Field(min_length=1, max_length=256)
    source_name: str = Field(min_length=1, max_length=512)
    title: str = Field(min_length=1, max_length=4096)
    tags: list[str] = Field(default_factory=list, max_length=256)


class SemanticTuple(StrictModel):
    semantic_key: Literal["realm", "type", "channel", "source_name", "is_active", "context_tags"]
    definition_version: Literal["v1"] = "v1"
    value: str | int
    provenance: SemanticProvenance


class MappedProviderMember(StrictModel):
    """One raw provider member after strict, versioned semantic mapping."""

    provider: Literal["chinatax", "domain", "realestate"]
    operation: Literal["get_articles", "get_agency_listings", "get_listings"]
    definition_version: Literal["v1"]
    external_key: str = Field(min_length=1, max_length=1024)
    clean_text: str = Field(min_length=1, max_length=8 * 1024 * 1024)
    media_type: Literal["text/plain"] = "text/plain"
    parsed_payload: dict[str, Any]
    content_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    meta_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    filter_meta: FilterMeta
    context_meta: ContextMeta
    semantic_tuples: list[SemanticTuple] = Field(min_length=6, max_length=6)
    identity_evidence: dict[str, str] = Field(default_factory=dict)


def semantic_tuples(
    filter_meta: FilterMeta,
    context_meta: ContextMeta,
    *,
    provenance: SemanticProvenance = "mapper",
) -> list[SemanticTuple]:
    return [
        SemanticTuple(semantic_key="realm", value=filter_meta.realm, provenance=provenance),
        SemanticTuple(semantic_key="type", value=filter_meta.type, provenance=provenance),
        SemanticTuple(semantic_key="channel", value=filter_meta.channel, provenance=provenance),
        SemanticTuple(semantic_key="source_name", value=filter_meta.source_name, provenance=provenance),
        SemanticTuple(semantic_key="is_active", value=filter_meta.is_active, provenance=provenance),
        SemanticTuple(semantic_key="context_tags", value="\n".join(context_meta.tags), provenance=provenance),
    ]


def generic_semantic_authority(
    descriptor: Mapping[str, Any],
) -> tuple[FilterMeta, ContextMeta, list[SemanticTuple]]:
    """Build the generic caller ledger while keeping is_active system-owned."""

    filter_meta = FilterMeta(
        realm=descriptor.get("realm"),
        type=descriptor.get("type"),
        channel=descriptor.get("channel"),
        source_name=descriptor.get("source_name"),
        is_active=1,
    )
    title = descriptor.get("title")
    context_meta = ContextMeta(
        realm=filter_meta.realm,
        type=filter_meta.type,
        channel=filter_meta.channel,
        source_name=filter_meta.source_name,
        title=title.strip() if isinstance(title, str) and title.strip() else filter_meta.source_name,
        tags=descriptor.get("context_tags") or [],
    )
    tuples = semantic_tuples(filter_meta, context_meta, provenance="caller")
    tuples = [
        item.model_copy(update={"provenance": "system"}) if item.semantic_key == "is_active" else item
        for item in tuples
    ]
    return filter_meta, context_meta, tuples


__all__ = [
    "ContextMeta",
    "FilterMeta",
    "generic_semantic_authority",
    "MappedProviderMember",
    "SemanticProvenance",
    "SemanticTuple",
    "semantic_tuples",
]
