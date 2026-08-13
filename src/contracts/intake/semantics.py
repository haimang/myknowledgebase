"""Canonical semantic surface shared by registered-API providers."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from src.contracts.common.models import StrictModel


class FilterMeta(StrictModel):
    """The five versioned filter dimensions required by D08-T007."""

    realm: str = Field(min_length=1, max_length=256)
    type: str = Field(min_length=1, max_length=256)
    channel: str = Field(min_length=1, max_length=256)
    source_name: str = Field(min_length=1, max_length=512)
    is_active: Literal[0, 1]


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


def semantic_tuples(filter_meta: FilterMeta, context_meta: ContextMeta) -> list[SemanticTuple]:
    return [
        SemanticTuple(semantic_key="realm", value=filter_meta.realm),
        SemanticTuple(semantic_key="type", value=filter_meta.type),
        SemanticTuple(semantic_key="channel", value=filter_meta.channel),
        SemanticTuple(semantic_key="source_name", value=filter_meta.source_name),
        SemanticTuple(semantic_key="is_active", value=filter_meta.is_active),
        SemanticTuple(semantic_key="context_tags", value="\n".join(context_meta.tags)),
    ]


__all__ = ["ContextMeta", "FilterMeta", "MappedProviderMember", "SemanticTuple", "semantic_tuples"]
