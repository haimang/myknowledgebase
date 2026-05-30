from __future__ import annotations

from browser_runtime import extract_text


def clean_payload(source_kind: str, payload: str) -> str:
    if source_kind in {"url", "api"}:
        return extract_text(payload)
    return payload.strip()
