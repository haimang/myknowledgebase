"""Pure S06--S08 generation contract coverage."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.persistence.retrieval_access import ArtifactRetrievalAccess
from src.services.lsrag_compiler import (
    LsragContractCompiler,
    TextSpan,
    deterministic_summaries,
    dual_channel_payload,
    structure_document_digest,
    summary_plan,
)


def _compiled() -> tuple[LsragContractCompiler, object, object, str]:
    clean = "第一段 evidence。\n\nSecond paragraph proves the result."
    compiler = LsragContractCompiler()
    structure, projection = compiler.structurize(
        clean_text=clean,
        generation_artifact_uuid="structure-generation",
        projection_generation_artifact_uuid="projection-generation",
        clean_artifact_uuid="clean-artifact",
    )
    return compiler, structure, projection, clean


def test_structure_is_generation_local_utf8_anchored_and_projects_g0_g1_g2() -> None:
    compiler, structure, projection, clean = _compiled()

    assert structure.document_root_node_id == "root"
    assert projection.generation_artifact_uuid == "projection-generation"
    assert projection.structure_generation_artifact_uuid == structure.generation_artifact_uuid
    assert [node.reading_ordinal for node in structure.nodes] == [0, 1]
    anchor = structure.nodes[1].source_anchor
    assert anchor == TextSpan(0, len(clean.encode("utf-8")))
    assert {block.granularity for block in projection.blocks} == {0, 1, 2}
    assert projection.blocks[0].block_id == "g0:document"
    compiler.validate_structure(document=structure, projection=projection, clean_text=clean)


def test_structure_rejects_cross_generation_projection_and_anchor_tampering() -> None:
    compiler, structure, projection, clean = _compiled()

    with pytest.raises(MkbError, match="STRUCTURE_BINDING_CROSS_GENERATION"):
        compiler.validate_structure(
            document=structure,
            projection=replace(projection, structure_generation_artifact_uuid="different-generation"),
            clean_text=clean,
        )

    bad_leaf = replace(structure.nodes[1], source_anchor=TextSpan(1, len(clean.encode("utf-8"))))
    bad_structure = replace(structure, nodes=(structure.nodes[0], bad_leaf))
    with pytest.raises(MkbError, match="STRUCTURE_ANCHOR_INVALID"):
        compiler.validate_structure(
            document=bad_structure,
            projection=replace(projection, structure_document_digest=structure_document_digest(bad_structure)),
            clean_text=clean,
        )

    partial = "第一段 evidence。"
    partial_leaf = replace(
        structure.nodes[1],
        source_anchor=TextSpan(0, len(partial.encode("utf-8"))),
        content_digest=stable_digest({"text": partial}),
        subtree_digest=stable_digest({"text": partial}),
    )
    partial_structure = replace(structure, nodes=(structure.nodes[0], partial_leaf))
    partial_projection = replace(projection, structure_document_digest=structure_document_digest(partial_structure))
    with pytest.raises(MkbError, match="STRUCTURE_COVERAGE_INVALID"):
        compiler.validate_structure(document=partial_structure, projection=partial_projection, clean_text=clean)


def test_constructs_full_valid_dual_channels_and_required_vector_units() -> None:
    compiler, structure, projection, clean = _compiled()
    summaries = {block.block_id: f"Summary for {block.block_id}" for block in projection.blocks}
    document, dual = compiler.construct(
        structure=structure,
        projection=projection,
        clean_text=clean,
        construction_generation_artifact_uuid="construct-generation",
        dual_channel_generation_artifact_uuid="dual-generation",
        summaries_by_block_id=summaries,
        metadata_headers={"title": "Evidence"},
    )
    plan = compiler.vectorization_plan(document=document, dual=dual, metadata_headers={"title": "Evidence"})

    assert len(document.units) == len(projection.blocks)
    assert dual.generation_artifact_uuid == "dual-generation"
    assert dual.construction_generation_artifact_uuid == document.generation_artifact_uuid
    assert len(plan.required) == len(document.units) * 2
    assert [(unit.granularity, unit.unit_id, unit.channel) for unit in plan.required] == sorted(
        (unit.granularity, unit.unit_id, unit.channel) for unit in plan.required
    )
    assert any(unit.granularity == 0 and unit.channel == "original" for unit in plan.required)
    assert all(unit.content_full_digest == stable_digest({"text": unit.content_full}) for unit in plan.required)
    payload = dual_channel_payload(dual)
    assert payload["generation_artifact_uuid"] == "dual-generation"
    assert set(payload) == {"schema_version", "generation_artifact_uuid", "recipe_version", "units"}
    first = payload["units"][0]
    assert isinstance(first, dict)
    assert set(first) == {"unit_id", "granularity", "original", "summary", "original_digest", "summary_digest"}
    # The serializer is intentionally strict-compatible with the deployed
    # retrieval adapter, rather than requiring a parallel hydration parser.
    parser = ArtifactRetrievalAccess(None, None)  # type: ignore[arg-type]
    parsed = parser._parse_projection(  # noqa: SLF001 - contract compatibility assertion
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8"),
        expected_generation_artifact_uuid="dual-generation",
    )
    assert set(parsed) == {unit.unit_id for unit in dual.units}


def test_summary_plan_and_offline_summaries_are_projection_deterministic() -> None:
    _, _, projection, _ = _compiled()

    plan = summary_plan(projection)
    summaries = deterministic_summaries(projection, max_chars=12)

    assert plan.block_ids == tuple(sorted((block.block_id for block in projection.blocks), key=lambda item: (int(item[1]), item)))
    assert set(summaries) == set(plan.block_ids)
    assert all(summary for summary in summaries.values())


def test_construct_and_vectorization_fail_closed_on_missing_summary_and_digest_mismatch() -> None:
    compiler, structure, projection, clean = _compiled()
    with pytest.raises(MkbError, match="CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE"):
        compiler.construct(
            structure=structure,
            projection=projection,
            clean_text=clean,
            construction_generation_artifact_uuid="construct-generation",
            summaries_by_block_id={},
        )

    summaries = {block.block_id: "grounded summary" for block in projection.blocks}
    document, dual = compiler.construct(
        structure=structure,
        projection=projection,
        clean_text=clean,
        construction_generation_artifact_uuid="construct-generation",
        summaries_by_block_id=summaries,
    )
    broken_original = replace(dual.units[0].original, content_full_digest="not-a-digest")
    broken_unit = replace(dual.units[0], original=broken_original)
    with pytest.raises(MkbError, match="CONSTRUCT_CONTENT_MISMATCH"):
        compiler.vectorization_plan(document=document, dual=replace(dual, units=(broken_unit, *dual.units[1:])))
