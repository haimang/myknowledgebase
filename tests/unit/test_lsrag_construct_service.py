"""NS3-P3: S07 construct leaf service is a pure compiler wrapper."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest
from src.services.lsrag_compiler import (
    LsragContractCompiler,
    construction_document_digest,
    construction_payload,
    dual_channel_payload,
    projection_digest,
    retrieval_projection_payload,
    structure_document_digest,
    structure_payload,
)
from src.services.lsrag_construct import LsragConstructService, bind_construct

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


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


def test_reprove_structure_from_candidate_matches_adopt() -> None:
    clean = "Whole legal source"
    candidate = {
        "context_meta": {"title": "fixture"},
        "layered_content": [
            {
                "block_id": 0,
                "granularity": 0,
                "original_content": {"title": None, "body": clean},
                "llm_summary": {"title": None, "body": None},
            },
            {
                "block_id": 1,
                "granularity": 1,
                "original_content": {"title": None, "body": "legal source"},
                "llm_summary": {"title": None, "body": None},
            },
        ],
    }
    digest = stable_digest({"text": clean})
    compiler = LsragContractCompiler()
    expected_structure, expected_projection = compiler.adopt_layered_json(
        clean_text=clean,
        layered_json=candidate,
        generation_artifact_uuid="structure-generation",
        projection_generation_artifact_uuid="projection-generation",
        clean_artifact_uuid="clean-artifact",
        clean_digest=digest,
        granularity_set=(0, 1),
    )
    _kernel, structure, projection = LsragConstructService(compiler).reprove_structure_from_candidate(
        clean_text=clean,
        layered_candidate=candidate,
        granularity_set=(0, 1),
        structure_artifact_uuid="structure-generation",
        projection_artifact_uuid="projection-generation",
        clean_artifact_uuid="clean-artifact",
        clean_digest=digest,
    )
    assert structure_payload(structure) == structure_payload(expected_structure)
    assert projection_digest(projection) == projection_digest(expected_projection)


def test_assert_construction_bytes_rejects_tampered_payload() -> None:
    compiler, structure, projection, clean = _compiled()
    summaries = {block.block_id: f"Summary for {block.block_id}" for block in projection.blocks}
    construction, dual = LsragConstructService(compiler).admit(
        bind_construct(
            mode="full_construct",
            clean_text=clean,
            structure=structure,
            projection=projection,
            summaries_by_block_id=summaries,
            construction_artifact_uuid="construct-generation",
            dual_channel_artifact_uuid="dual-generation",
        )
    )
    good = canonical_json(construction_payload(construction))
    dual_bytes = canonical_json(dual_channel_payload(dual))
    LsragConstructService().assert_construction_bytes(
        construction=construction,
        dual=dual,
        construction_data=good,
        dual_data=dual_bytes,
        construction_digest=construction_document_digest(construction),
    )
    tampered = good[:-2] + (b"X" if good[-2:-1] != b"X" else b"Y") + good[-1:]
    with pytest.raises(MkbError, match="CONSTRUCT_TO_VECTORIZE_GATE"):
        LsragConstructService().assert_construction_bytes(
            construction=construction,
            dual=dual,
            construction_data=tampered,
            dual_data=dual_bytes,
            construction_digest=construction_document_digest(construction),
        )


def test_admit_matches_direct_compiler_construct() -> None:
    compiler, structure, projection, clean = _compiled()
    summaries = {block.block_id: f"Summary for {block.block_id}" for block in projection.blocks}
    expected_document, expected_dual = compiler.construct(
        structure=structure,
        projection=projection,
        clean_text=clean,
        construction_generation_artifact_uuid="construct-generation",
        dual_channel_generation_artifact_uuid="dual-generation",
        summaries_by_block_id=summaries,
    )
    document, dual = LsragConstructService(compiler).admit(
        bind_construct(
            mode="full_construct",
            clean_text=clean,
            structure=structure,
            projection=projection,
            summaries_by_block_id=summaries,
            construction_artifact_uuid="construct-generation",
            dual_channel_artifact_uuid="dual-generation",
        )
    )
    assert construction_payload(document) == construction_payload(expected_document)
    assert dual_channel_payload(dual) == dual_channel_payload(expected_dual)


def test_binder_and_admit_fail_closed_on_missing_summaries() -> None:
    compiler, structure, projection, clean = _compiled()
    with pytest.raises(MkbError, match="CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE"):
        bind_construct(
            mode="full_construct",
            clean_text=clean,
            structure=structure,
            projection=projection,
            summaries_by_block_id={},
            construction_artifact_uuid="construct-generation",
            dual_channel_artifact_uuid="dual-generation",
        )


def test_binder_splits_full_construct_and_metadata_refresh() -> None:
    compiler, structure, projection, clean = _compiled()
    summaries = {block.block_id: "grounded summary" for block in projection.blocks}
    full = bind_construct(
        mode="full_construct",
        clean_text=clean,
        structure=structure,
        projection=projection,
        summaries_by_block_id=summaries,
        construction_artifact_uuid="c",
        dual_channel_artifact_uuid="d",
    )
    assert full.mode == "full_construct"
    assert full.metadata_headers is None
    refresh = bind_construct(
        mode="metadata_refresh",
        clean_text=clean,
        structure=structure,
        projection=projection,
        summaries_by_block_id=summaries,
        construction_artifact_uuid="c",
        dual_channel_artifact_uuid="d",
        metadata_headers={"title": "Evidence"},
    )
    assert refresh.mode == "metadata_refresh"
    assert refresh.metadata_headers == {"title": "Evidence"}
    with pytest.raises(MkbError, match="CONSTRUCT_MODE_INVALID"):
        bind_construct(
            mode="full_construct",
            clean_text=clean,
            structure=structure,
            projection=projection,
            summaries_by_block_id=summaries,
            construction_artifact_uuid="c",
            dual_channel_artifact_uuid="d",
            metadata_headers={"title": "Evidence"},
        )


def test_original_mutation_is_rejected_by_construct_service() -> None:
    from dataclasses import replace

    compiler, structure, projection, clean = _compiled()
    summaries = {block.block_id: "grounded summary" for block in projection.blocks}
    mutated = replace(
        projection.blocks[0],
        original_text="tampered original",
        original_digest=stable_digest({"text": "tampered original"}),
    )
    mutated_projection = replace(projection, blocks=(mutated, *projection.blocks[1:]))
    with pytest.raises(MkbError):
        LsragConstructService(compiler).admit(
            bind_construct(
                mode="full_construct",
                clean_text=clean,
                structure=structure,
                projection=mutated_projection,
                summaries_by_block_id=summaries,
                construction_artifact_uuid="construct-generation",
                dual_channel_artifact_uuid="dual-generation",
            )
        )


def test_reprove_stored_payloads_roundtrip() -> None:
    compiler, structure, projection, clean = _compiled()
    structure_data = canonical_json(structure_payload(structure))
    projection_data = canonical_json(retrieval_projection_payload(projection))
    _kernel, proven_structure, proven_projection = LsragConstructService(compiler).reprove_structure_from_stored_payloads(
        clean_text=clean,
        structure_data=structure_data,
        projection_data=projection_data,
    )
    assert structure_document_digest(proven_structure) == structure_document_digest(structure)
    assert projection_digest(proven_projection) == projection_digest(projection)


def test_mixin_keeps_summary_io_and_drops_direct_construct() -> None:
    text = (REPOSITORY_ROOT / "src/runtime/intake/generation_construct.py").read_text(encoding="utf-8")
    assert "compiler.construct(" not in text
    assert "def _complete_construct_summaries" in text
    assert "_live_layered_summary_generate" in text
    assert "_salvage_summary_via_cli" in text
    service_blob = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (REPOSITORY_ROOT / "src/services/lsrag_construct").glob("*.py")
    )
    assert "claude_cli" not in service_blob
    assert "InferenceFacade" not in service_blob


def test_construct_package_has_no_runtime_or_transport_imports() -> None:
    forbidden = ("src.runtime", "src.llm_adapters", "httpx", "openai", "vllm", "sqlite3", "aiosqlite")
    hits: list[str] = []
    root = REPOSITORY_ROOT / "src/services/lsrag_construct"
    for path in root.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                if any(name == item or name.startswith(f"{item}.") for item in forbidden):
                    hits.append(f"{path.name}:{node.lineno}:{name}")
    assert hits == []
