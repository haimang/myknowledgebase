"""Registered-API member mapping + scatter clean channel."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from intake.api.providers import infer_provider, map_provider_record
from intake.text import clean_plain_text, extract_html_text
from intake.types import CleanMember
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest


def clean_registered_api_members(
    members: Sequence[Mapping[str, Any]],
    *,
    provider: str | None = None,
    capability: str = "clean.map.registered_api",
) -> list[CleanMember]:
    """Map a sealed collection of API records into independently cleaned members."""

    cleaned: list[CleanMember] = []
    if not members:
        return cleaned
    for ordinal, raw in enumerate(members):
        if not isinstance(raw, Mapping):
            raise MkbError("SCATTER_MEMBER_INVALID", "Registered API member must be an object", 422)
        if raw.get("member_ordinal") not in {None, ordinal}:
            raise MkbError("SCATTER_MEMBER_ORDER_INVALID", "Registered API member order is invalid", 422)
        mapped = map_provider_record(raw, provider=infer_provider(raw, provider))
        raw_text = mapped["clean_text"] or str(raw.get("raw_text") or "")
        media_type = str(raw.get("media_type") or "text/plain")
        if media_type == "text/html":
            text, evidence = extract_html_text(raw_text)
        else:
            text = clean_plain_text(raw_text)
            evidence = {"parser": "intake.api.provider-map.v1"}
        if not text:
            raise MkbError("CLEAN_EMPTY", "Registered API member cleaning produced no admissible text", 422)
        external_key = str(raw.get("external_key") or mapped["identity"] or f"member-{ordinal}")
        normalized = str(raw.get("normalized_external_key") or external_key)
        raw_digest = str(raw.get("raw_digest") or stable_digest({"text": raw_text}))
        evidence = {
            **evidence,
            "channel": "api",
            "provider": mapped["provider"],
            "identity": mapped["identity"],
            "is_active": mapped["is_active"],
            "clean_capability": capability,
            "input_raw_digest": raw_digest,
        }
        cleaned.append(
            CleanMember(
                ordinal=ordinal,
                external_key=external_key,
                normalized_external_key=normalized,
                raw_digest=raw_digest,
                clean_text=text,
                media_type=media_type,
                payload=mapped,
                evidence=evidence,
            )
        )
    return cleaned


__all__ = ["clean_registered_api_members"]
