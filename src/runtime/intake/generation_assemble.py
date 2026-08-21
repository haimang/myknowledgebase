"""MKB R5 layered JSON assembly: system-owned g0 overlay and cuts assembly."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.lsrag.cuts import validate_cuts
from src.contracts.lsrag.layered_content import normalize_layered_text


def _fail(code: str, detail: str) -> None:
    raise MkbError(code, detail, 422)


def overlay_system_g0(
    *,
    clean_text: str,
    candidate: Mapping[str, object],
    profile: tuple[int, ...],
) -> dict[str, object]:
    """Drop every model g0 block; insert exactly one system g0 (body=clean)."""

    clean = normalize_layered_text(clean_text)
    raw_blocks = candidate.get("layered_content")
    if not isinstance(raw_blocks, list):
        raw_blocks = []

    remaining: list[dict[str, Any]] = []
    for blk in raw_blocks:
        if not isinstance(blk, Mapping):
            continue
        granularity = blk.get("granularity")
        if granularity == 0 or granularity == "0":
            continue
        remaining.append(dict(blk))

    system_g0: dict[str, Any] = {
        "block_id": 0,
        "granularity": 0,
        "original_content": {"title": None, "body": clean},
        "llm_summary": {"title": None, "body": None},
    }

    new_blocks: list[dict[str, Any]] = [system_g0]
    for idx, blk in enumerate(remaining, start=1):
        blk["block_id"] = idx
        new_blocks.append(blk)

    result = dict(candidate)
    result.pop("schema_version", None)
    result["layered_content"] = new_blocks

    for key in ("date", "knowledge_tree"):
        if key in result and not isinstance(result[key], Mapping):
            result.pop(key, None)

    if "context_meta" not in result or not isinstance(result["context_meta"], Mapping):
        result["context_meta"] = {}

    return result


_IGNORABLE_CHARS = set("#*_`~>|+-=。，,！!？?:：;；()（）[]【】\"'“”'、\t\r\n ")


def find_anchor_span(
    clean: str,
    start_query: str,
    end_query: str,
    search_start: int = 0,
    idx: int = 0,
) -> tuple[int, int]:
    """Locate start and end positions in clean text with resilient normalization."""
    # 1. Exact match tier
    s = clean.find(start_query, search_start)
    if s >= 0:
        e = clean.find(end_query, s)
        if e >= 0:
            second_s = clean.find(start_query, s + 1)
            if second_s >= 0 and second_s < e:
                _fail("CUTS_ANCHOR_AMBIGUOUS", f"cuts[{idx}].start appears multiple times before end: {start_query!r}")
            end_pos = e + len(end_query)
            if end_pos > s:
                return s, end_pos

    # 2. Resilient normalized match tier
    clean_sub = clean[search_start:]
    clean_compact: list[str] = []
    orig_indices: list[int] = []
    for char_i, ch in enumerate(clean_sub):
        if ch not in _IGNORABLE_CHARS:
            clean_compact.append(ch)
            orig_indices.append(search_start + char_i)

    compact_str = "".join(clean_compact)
    start_compact = "".join(c for c in start_query if c not in _IGNORABLE_CHARS)
    end_compact = "".join(c for c in end_query if c not in _IGNORABLE_CHARS)

    if not start_compact:
        start_compact = start_query.strip()
    if not end_compact:
        end_compact = end_query.strip()

    c_s = compact_str.find(start_compact)
    if c_s < 0:
        _fail("CUTS_ANCHOR_MISSING", f"cuts[{idx}].start not found in clean text: {start_query!r}")

    c_e = compact_str.find(end_compact, c_s)
    if c_e < 0:
        _fail("CUTS_ANCHOR_MISSING", f"cuts[{idx}].end not found after start: {end_query!r}")

    c_second_s = compact_str.find(start_compact, c_s + 1)
    if c_second_s >= 0 and c_second_s < c_e:
        _fail("CUTS_ANCHOR_AMBIGUOUS", f"cuts[{idx}].start appears multiple times before end: {start_query!r}")

    s_idx = orig_indices[c_s]
    line_start = clean.rfind("\n", 0, s_idx)
    line_start = 0 if line_start < 0 else line_start + 1
    prefix = clean[line_start:s_idx]
    if all(c in "#*_`~>|-+ \t" for c in prefix):
        s_idx = line_start

    last_compact_idx = c_e + len(end_compact) - 1
    e_idx = orig_indices[last_compact_idx] + 1
    while e_idx < len(clean) and clean[e_idx] in "`)]）】\"' \t" and clean[e_idx] != "\n":
        e_idx += 1
    if e_idx < len(clean) and clean[e_idx] in "。，.!,;；：:":
        e_idx += 1

    if e_idx <= s_idx:
        _fail("CUTS_ORDER_INVALID", f"cuts[{idx}] end position <= start position")

    return s_idx, e_idx


def assemble_from_cuts(
    *,
    clean_text: str,
    cuts_pack: Mapping[str, object],
    profile: tuple[int, ...],
) -> dict[str, object]:
    """Validate cuts, slice clean, overlay system g0, return layered_content.v1."""

    clean = normalize_layered_text(clean_text)
    validated = validate_cuts(cuts_pack)
    cuts = validated.get("cuts") or []

    g1_blocks: list[dict[str, Any]] = []
    for idx, cut in enumerate(cuts):
        start = cut["start"]
        end = cut["end"]
        title = cut.get("title")

        s, end_pos = find_anchor_span(clean, start, end, idx=idx)

        cut_body = clean[s:end_pos]
        g1_blocks.append(
            {
                "block_id": idx + 1,
                "granularity": 1,
                "original_content": {"title": title, "body": cut_body},
                "llm_summary": {"title": None, "body": None},
            }
        )

    raw_candidate: dict[str, Any] = {
        "layered_content": g1_blocks,
    }
    if "context_meta" in validated and isinstance(validated["context_meta"], Mapping):
        raw_candidate["context_meta"] = dict(validated["context_meta"])

    return overlay_system_g0(clean_text=clean, candidate=raw_candidate, profile=profile)


def realign_construct_original(
    *,
    accepted: Mapping[str, Any],
    completed: Mapping[str, Any],
) -> dict[str, Any]:
    """Realign original_content from accepted structurize candidate onto completed."""

    accepted_blocks = accepted.get("layered_content") or []
    completed_blocks = completed.get("layered_content") or []

    accepted_by_key: dict[tuple[int, int], Mapping[str, Any]] = {}
    for blk in accepted_blocks:
        if not isinstance(blk, Mapping):
            continue
        try:
            key = (int(blk.get("granularity", -1)), int(blk.get("block_id", -1)))
            accepted_by_key[key] = blk
        except (TypeError, ValueError):
            continue

    new_blocks: list[dict[str, Any]] = []
    for blk in completed_blocks:
        if not isinstance(blk, Mapping):
            new_blocks.append(dict(blk) if isinstance(blk, dict | list) else blk)
            continue
        try:
            key = (int(blk.get("granularity", -1)), int(blk.get("block_id", -1)))
        except (TypeError, ValueError):
            new_blocks.append(dict(blk))
            continue
        accepted_blk = accepted_by_key.get(key)
        if accepted_blk is None:
            new_blocks.append(dict(blk))
            continue
        new_blk = dict(blk)
        accepted_original = accepted_blk.get("original_content")
        if isinstance(accepted_original, Mapping):
            new_blk["original_content"] = dict(accepted_original)
        new_blocks.append(new_blk)

    result = dict(completed)
    result["layered_content"] = new_blocks

    for k in ("context_meta", "date", "knowledge_tree"):
        if k not in result and k in accepted and isinstance(accepted[k], Mapping):
            result[k] = dict(accepted[k])

    return result


__all__ = [
    "overlay_system_g0",
    "assemble_from_cuts",
    "realign_construct_original",
]
