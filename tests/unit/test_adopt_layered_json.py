"""NS1-T10/T11: kernel admission owns anchors and layered projection."""

from __future__ import annotations

from copy import deepcopy

import pytest

from src.contracts.common.errors import MkbError
from src.services.lsrag_compiler import LsragContractCompiler


def _candidate(clean: str, bodies: dict[int, str | None]) -> dict[str, object]:
    return {
        "context_meta": {"title": "fixture"},
        "layered_content": [
            {
                "block_id": block_id,
                "granularity": granularity,
                "original_content": {"title": None, "body": body},
                "llm_summary": {"title": None, "body": None},
            }
            for block_id, (granularity, body) in enumerate(bodies.items())
        ],
    }


def test_adopt_normalizes_fills_g0_and_uses_first_exact_anchor_with_count() -> None:
    clean = "Cafe\u0301\nrepeat\nrepeat"
    candidate = _candidate(clean, {0: None, 1: "repeat\r\nrepeat", 2: "repeat"})

    structure, projection, report = LsragContractCompiler().adopt_layered_json_with_report(
        clean_text=clean,
        layered_json=candidate,
        generation_artifact_uuid="structure-generation",
        projection_generation_artifact_uuid="projection-generation",
        clean_artifact_uuid="clean-artifact",
        granularity_set=(0, 1, 2),
    )

    assert structure.clean_digest
    assert [block.block_id for block in projection.blocks] == ["g0:b0000", "g1:b0001", "g2:b0002"]
    assert projection.blocks[0].original_text == "Café\nrepeat\nrepeat"
    assert projection.blocks[1].original_text == "repeat\nrepeat"
    assert projection.blocks[2].original_text == "repeat"
    assert report["anchors"][2]["occurrence_count"] == 2  # type: ignore[index]
    assert report["anchors"][1]["start_byte"] == len("Café\n".encode())  # type: ignore[index]


@pytest.mark.parametrize(
    ("profile", "bodies"),
    [
        ((0, 1), {0: "Whole legal source", 1: "legal source"}),
        ((0,), {0: "Whole property source"}),
    ],
)
def test_adopt_accepts_closed_domain_profiles_without_silent_layers(
    profile: tuple[int, ...], bodies: dict[int, str]
) -> None:
    _, projection = LsragContractCompiler().adopt_layered_json(
        clean_text="Whole legal source" if profile == (0, 1) else "Whole property source",
        layered_json=_candidate(
            "Whole legal source" if profile == (0, 1) else "Whole property source",
            {granularity: body for granularity, body in bodies.items()},
        ),
        generation_artifact_uuid="structure-generation",
        projection_generation_artifact_uuid="projection-generation",
        clean_artifact_uuid="clean-artifact",
        granularity_set=profile,
    )
    assert {block.granularity for block in projection.blocks} == set(profile)


def test_adopt_rejects_profile_drift_anchor_miss_and_b_summary() -> None:
    compiler = LsragContractCompiler()
    clean = "source text"

    with pytest.raises(MkbError, match="STRUCTURE_GRANULARITY_SET_MISMATCH"):
        compiler.adopt_layered_json(
            clean_text=clean,
            layered_json=_candidate(clean, {0: clean, 1: "source", 2: "text"}),
            generation_artifact_uuid="structure-generation",
            clean_artifact_uuid="clean-artifact",
            granularity_set=(0, 1),
        )

    with pytest.raises(MkbError, match="STRUCTURE_ANCHOR_MISSING"):
        compiler.adopt_layered_json(
            clean_text=clean,
            layered_json=_candidate(clean, {0: clean, 1: "not in clean"}),
            generation_artifact_uuid="structure-generation",
            clean_artifact_uuid="clean-artifact",
            granularity_set=(0, 1),
        )

    bad_summary = _candidate(clean, {0: clean})
    bad_summary["layered_content"][0]["llm_summary"]["body"] = "summary"  # type: ignore[index]
    with pytest.raises(MkbError, match="STRUCTURE_SUMMARY_INVALID"):
        compiler.adopt_layered_json(
            clean_text=clean,
            layered_json=bad_summary,
            generation_artifact_uuid="structure-generation",
            clean_artifact_uuid="clean-artifact",
            granularity_set=(0,),
        )


def test_construct_map_consumes_whole_c_package_and_rejects_original_mutation() -> None:
    clean = "first paragraph.\nsecond paragraph."
    candidate = _candidate(clean, {0: None, 1: "first paragraph."})
    compiler = LsragContractCompiler()
    structure, projection = compiler.adopt_layered_json(
        clean_text=clean,
        layered_json=candidate,
        generation_artifact_uuid="structure-generation",
        projection_generation_artifact_uuid="projection-generation",
        clean_artifact_uuid="clean-artifact",
        granularity_set=(0, 1),
    )
    summaries = {block.block_id: f"summary {block.block_id}" for block in projection.blocks}
    completed = compiler.fill_layered_summaries(
        accepted_layered_json=compiler.normalize_layered_candidate(
            clean_text=clean,
            layered_json=candidate,
            granularity_set=(0, 1),
        ),
        projection=projection,
        summaries_by_block_id=summaries,
    )

    assert compiler.layered_summary_map(
        layered_json=completed,
        projection=projection,
        accepted_layered_json=candidate,
    ) == summaries
    document, dual = compiler.construct(
        structure=structure,
        projection=projection,
        clean_text=clean,
        construction_generation_artifact_uuid="construction-generation",
        summaries_by_block_id=summaries,
        required_granularities=frozenset({0, 1}),
    )
    assert len(document.units) == len(projection.blocks) == len(dual.units)

    mutated = deepcopy(completed)
    mutated["layered_content"][0]["original_content"]["body"] = "mutated"  # type: ignore[index]
    with pytest.raises(MkbError, match="CONSTRUCT_KERNEL_ORIGINAL_MUTATION"):
        compiler.layered_summary_map(
            layered_json=mutated,
            projection=projection,
            accepted_layered_json=candidate,
        )
