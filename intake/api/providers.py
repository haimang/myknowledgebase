"""Provider-shaped record mapping (logic ported, not live vendor scrapers)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def _text(value: object) -> str:
    return str(value).strip() if value is not None else ""


def map_provider_record(record: Mapping[str, Any], *, provider: str) -> dict[str, Any]:
    """Normalize a registered-API member into title/body/status facts.

    The field names follow the dedicated-API provider shape (title, body /
    content, type, channel, effective_status) without calling those vendors.
    """

    title = _text(record.get("title") or record.get("name") or record.get("headline"))
    body = _text(
        record.get("body")
        or record.get("content")
        or record.get("raw_text")
        or record.get("description")
        or record.get("text")
    )
    article_type = _text(record.get("type")) or "unknown"
    channel = _text(record.get("channel")) or "unknown"
    status = _text(record.get("effective_status") or record.get("status"))
    is_active = 1 if status in {"全文有效", "active", "in_force", ""} or not status else 0
    identity = _text(record.get("id") or record.get("external_key") or record.get("normalized_external_key"))
    parts = [part for part in (title, body) if part]
    clean_text = "\n\n".join(parts)
    return {
        "provider": provider,
        "identity": identity,
        "title": title,
        "type": article_type,
        "channel": channel,
        "effective_status": status or "unknown",
        "is_active": is_active,
        "clean_text": clean_text,
    }


def infer_provider(record: Mapping[str, Any], explicit: str | None) -> str:
    if isinstance(explicit, str) and explicit.strip():
        return explicit.strip()
    source = record.get("source_name") or record.get("provider")
    if isinstance(source, str) and source.strip():
        return source.strip()
    if record.get("xxgkEffectLevel") is not None or record.get("effective_status") is not None:
        return "chinatax"
    return "generic"
