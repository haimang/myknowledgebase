"""Registered-API member mapping + scatter clean channel."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from intake.api.registry import parse_registered_api_member, resolve_provider_operation
from intake.types import CleanMember
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest


def clean_registered_api_members(
    members: Sequence[Mapping[str, Any]],
    *,
    provider: str,
    operation: str,
    definition_version: str,
    capability: str = "clean.map.registered_api",
) -> list[CleanMember]:
    """Map a sealed collection of API records into independently cleaned members."""

    resolve_provider_operation(provider, operation, definition_version)
    cleaned: list[CleanMember] = []
    seen_keys: set[str] = set()
    if not members:
        return cleaned
    for ordinal, raw in enumerate(members):
        if not isinstance(raw, Mapping):
            raise MkbError("SCATTER_MEMBER_INVALID", "Registered API member must be an object", 422)
        if raw.get("member_ordinal") not in {None, ordinal}:
            raise MkbError("SCATTER_MEMBER_ORDER_INVALID", "Registered API member order is invalid", 422)
        raw_record = raw.get("raw_record") if isinstance(raw.get("raw_record"), Mapping) else raw
        mapped = parse_registered_api_member(
            raw_record,
            provider=provider,
            operation=operation,
            definition_version=definition_version,
        )
        external_key = mapped.external_key
        normalized = external_key.strip().casefold()
        if normalized in seen_keys:
            raise MkbError("SCATTER_MEMBER_KEY_DUPLICATE", "Registered API member external key is duplicated", 422)
        seen_keys.add(normalized)
        raw_digest = str(
            raw.get("raw_digest")
            or stable_digest(
                {
                    "provider": provider,
                    "operation": operation,
                    "definition_version": definition_version,
                    "raw": dict(raw_record),
                }
            )
        )
        filter_meta = mapped.filter_meta.model_dump(mode="json")
        context_meta = mapped.context_meta.model_dump(mode="json")
        semantic = tuple(item.model_dump(mode="json") for item in mapped.semantic_tuples)
        evidence = {
            "parser": f"intake.api.{provider}.{operation}.{definition_version}",
            "channel": "api",
            "provider": provider,
            "operation": operation,
            "definition_version": definition_version,
            "identity": mapped.external_key,
            "identity_evidence": mapped.identity_evidence,
            "content_digest": mapped.content_digest,
            "meta_digest": mapped.meta_digest,
            "filter_meta": filter_meta,
            "context_meta": context_meta,
            "semantic_tuples": list(semantic),
            "clean_capability": capability,
            "input_raw_digest": raw_digest,
        }
        cleaned.append(
            CleanMember(
                ordinal=ordinal,
                external_key=external_key,
                normalized_external_key=normalized,
                raw_digest=raw_digest,
                content_digest=mapped.content_digest,
                meta_digest=mapped.meta_digest,
                clean_text=mapped.clean_text,
                media_type=mapped.media_type,
                filter_meta=filter_meta,
                context_meta=context_meta,
                semantic_tuples=semantic,
                payload=mapped.parsed_payload,
                evidence=evidence,
            )
        )
    return cleaned


__all__ = ["clean_registered_api_members"]
