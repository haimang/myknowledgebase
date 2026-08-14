"""NS1-T01: layered_content.v1 shape is strict and span-free."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.lsrag.layered_content import validate_layered_content


def _block(granularity: int, body: str = "source") -> dict[str, object]:
    return {
        "block_id": granularity,
        "granularity": granularity,
        "original_content": {"title": None, "body": body},
        "llm_summary": {"title": None, "body": None},
    }


def test_checked_in_schema_is_strict_and_candidate_fixture_is_valid() -> None:
    schema = json.loads(Path("data/schemas/lsrag.layered_content.v1.json").read_text(encoding="utf-8"))
    assert schema["additionalProperties"] is False
    assert "span" not in json.dumps(schema)
    candidate = {"context_meta": {"title": "fixture"}, "layered_content": [_block(0)]}
    assert validate_layered_content(candidate)["layered_content"][0]["granularity"] == 0


def test_schema_rejects_unknown_span_and_missing_wire_fields() -> None:
    with pytest.raises(MkbError, match="STRUCTURE_SCHEMA_INVALID"):
        validate_layered_content({"context_meta": {}, "layered_content": [{**_block(0), "span": {}}]})
    bad = _block(0)
    del bad["llm_summary"]
    with pytest.raises(MkbError, match="STRUCTURE_SCHEMA_INVALID"):
        validate_layered_content({"context_meta": {}, "layered_content": [bad]})


def test_b_summary_is_null_but_c_summary_requires_body() -> None:
    candidate = {"context_meta": {}, "layered_content": [_block(0)]}
    assert validate_layered_content(candidate, summaries_must_be_null=True)
    with pytest.raises(MkbError, match="STRUCTURE_SUMMARY_INVALID"):
        validate_layered_content(candidate, summary_required=True)
