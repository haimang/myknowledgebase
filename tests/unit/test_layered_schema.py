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
    with pytest.raises(MkbError, match="granularity 0"):
        validate_layered_content({"context_meta": {}, "layered_content": [_block(1)]})


def test_checked_in_ns1_goldens_adopt_their_closed_profiles() -> None:
    from src.services.lsrag_compiler import LsragContractCompiler

    cases = (
        ("generic.layered.v1.json", "First paragraph. Second paragraph.", (0, 1, 2)),
        ("legal.layered.v1.json", "Article 1 Notice. Article 2 Scope.", (0, 1)),
        ("realestate.layered.v1.json", "Two bedroom listing near the station.", (0,)),
    )
    compiler = LsragContractCompiler()
    for name, clean, profile in cases:
        candidate = json.loads(Path("tests/fixtures/ns1", name).read_text(encoding="utf-8"))
        assert validate_layered_content(candidate, summaries_must_be_null=True)
        _, projection = compiler.adopt_layered_json(
            clean_text=clean,
            layered_json=candidate,
            generation_artifact_uuid="structure-generation",
            projection_generation_artifact_uuid="projection-generation",
            clean_artifact_uuid="clean-artifact",
            granularity_set=profile,
        )
        assert {block.granularity for block in projection.blocks} == set(profile)


def test_b_summary_is_null_but_c_summary_requires_body() -> None:
    candidate = {"context_meta": {}, "layered_content": [_block(0)]}
    assert validate_layered_content(candidate, summaries_must_be_null=True)
    with pytest.raises(MkbError, match="STRUCTURE_SUMMARY_INVALID"):
        validate_layered_content(candidate, summary_required=True)
