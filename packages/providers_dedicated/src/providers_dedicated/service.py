from __future__ import annotations


def maybe_clean_with_provider(canonical_uri: str, payload: str) -> str | None:
    if "chinatax.gov.cn" not in canonical_uri:
        return None
    marker = "[provider:chinatax]"
    return f"{marker} {payload.strip()}"

