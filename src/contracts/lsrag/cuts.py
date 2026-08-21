"""MKB B-JSON cuts contract and validation."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.common.errors import MkbError

CUTS_SCHEMA_VERSION = "mkb.b-json-cuts.v1"
_CUTS_TOP_ALLOWED = frozenset({"schema_version", "cuts", "context_meta"})
_CUTS_BLOCK_ALLOWED = frozenset({"title", "start", "end"})
_CUTS_FORBIDDEN = frozenset(
    {
        "span",
        "start_byte",
        "end_byte",
        "offset",
        "index",
        "body",
        "original",
        "clean",
        "layered_content",
        "block_id",
        "granularity",
    }
)


def _fail(code: str, detail: str) -> None:
    raise MkbError(code, detail, 422)


def validate_cuts(pack: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(pack, Mapping):
        _fail("CUTS_SCHEMA_INVALID", "cuts pack must be a JSON object")

    for key in sorted(_CUTS_FORBIDDEN):
        if key in pack:
            _fail("CUTS_SCHEMA_INVALID", f"top-level contains forbidden field: {key}")

    unknown_top = set(pack.keys()) - _CUTS_TOP_ALLOWED
    if unknown_top:
        _fail("CUTS_SCHEMA_INVALID", f"top-level contains unknown fields: {sorted(unknown_top)}")

    schema_version = pack.get("schema_version")
    if schema_version != CUTS_SCHEMA_VERSION:
        _fail("CUTS_SCHEMA_INVALID", f"schema_version must be {CUTS_SCHEMA_VERSION!r}, got {schema_version!r}")

    cuts = pack.get("cuts")
    if cuts is None:
        _fail("CUTS_EMPTY", "cuts array is required")
    if not isinstance(cuts, list):
        _fail("CUTS_SCHEMA_INVALID", "cuts must be an array")
    if len(cuts) == 0:
        _fail("CUTS_EMPTY", "cuts array must be non-empty")

    validated_cuts: list[dict[str, Any]] = []
    for idx, raw in enumerate(cuts):
        if not isinstance(raw, Mapping):
            _fail("CUTS_SCHEMA_INVALID", f"cuts[{idx}] must be an object")
        for key in sorted(_CUTS_FORBIDDEN):
            if key in raw:
                _fail("CUTS_SCHEMA_INVALID", f"cuts[{idx}] contains forbidden field: {key}")
        unknown = set(raw.keys()) - _CUTS_BLOCK_ALLOWED
        if unknown:
            _fail("CUTS_SCHEMA_INVALID", f"cuts[{idx}] contains unknown fields: {sorted(unknown)}")
        if "start" not in raw or "end" not in raw:
            _fail("CUTS_SCHEMA_INVALID", f"cuts[{idx}] missing start/end")
        start = raw["start"]
        end = raw["end"]
        title = raw.get("title")
        if not isinstance(start, str) or not start.strip():
            _fail("CUTS_SCHEMA_INVALID", f"cuts[{idx}].start must be non-empty string")
        if not isinstance(end, str) or not end.strip():
            _fail("CUTS_SCHEMA_INVALID", f"cuts[{idx}].end must be non-empty string")
        if title is not None and not isinstance(title, str):
            _fail("CUTS_SCHEMA_INVALID", f"cuts[{idx}].title must be string or null")
        validated_cuts.append({"title": title, "start": start, "end": end})

    result: dict[str, Any] = {
        "schema_version": CUTS_SCHEMA_VERSION,
        "cuts": validated_cuts,
    }
    if "context_meta" in pack and isinstance(pack["context_meta"], Mapping):
        result["context_meta"] = dict(pack["context_meta"])
    return result


__all__ = [
    "CUTS_SCHEMA_VERSION",
    "validate_cuts",
]
