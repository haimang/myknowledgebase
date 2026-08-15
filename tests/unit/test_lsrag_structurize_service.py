"""NS3-P2: S06 structurize leaf service is a pure compiler wrapper."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.services.lsrag_compiler import (
    LsragContractCompiler,
    projection_digest,
    structure_document_digest,
    structure_payload,
)
from src.services.lsrag_structurize import LsragStructurizeService, bind_structurize

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]


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


def _legal() -> tuple[str, dict[str, object], tuple[int, ...]]:
    clean = "Whole legal source"
    return clean, _candidate(clean, {0: "Whole legal source", 1: "legal source"}), (0, 1)


def test_binder_fails_closed_on_missing_clean_profile_or_candidate() -> None:
    clean, candidate, profile = _legal()
    with pytest.raises(MkbError, match="STRUCTURE_KERNEL_EMPTY"):
        bind_structurize(
            clean_text="   ",
            clean_artifact_uuid="clean",
            clean_digest="d",
            layered_candidate=candidate,
            granularity_set=profile,
            structure_artifact_uuid="s",
            projection_artifact_uuid="p",
        )
    with pytest.raises(MkbError, match="STRUCTURE_CANDIDATE_MISSING"):
        bind_structurize(
            clean_text=clean,
            clean_artifact_uuid="clean",
            clean_digest="d",
            layered_candidate=None,
            granularity_set=profile,
            structure_artifact_uuid="s",
            projection_artifact_uuid="p",
        )
    with pytest.raises(MkbError, match="STRUCTURE_PROFILE_INVALID"):
        bind_structurize(
            clean_text=clean,
            clean_artifact_uuid="clean",
            clean_digest="d",
            layered_candidate=candidate,
            granularity_set=None,
            structure_artifact_uuid="s",
            projection_artifact_uuid="p",
        )


def test_binder_rejects_profile_without_g0() -> None:
    clean, candidate, _profile = _legal()
    with pytest.raises(MkbError, match="STRUCTURE_PROFILE_INVALID"):
        bind_structurize(
            clean_text=clean,
            clean_artifact_uuid="clean",
            clean_digest="d",
            layered_candidate=candidate,
            granularity_set=(1, 2),
            structure_artifact_uuid="s",
            projection_artifact_uuid="p",
        )


def test_admit_matches_direct_compiler_adopt() -> None:
    clean, candidate, profile = _legal()
    digest = stable_digest({"text": clean})
    compiler = LsragContractCompiler()
    accepted = compiler.normalize_layered_candidate(
        clean_text=clean,
        layered_json=candidate,
        granularity_set=profile,
    )
    structure, projection, report = compiler.adopt_layered_json_with_report(
        clean_text=clean,
        layered_json=accepted,
        generation_artifact_uuid="structure-generation",
        projection_generation_artifact_uuid="projection-generation",
        clean_artifact_uuid="clean-artifact",
        clean_digest=digest,
        granularity_set=profile,
    )
    admitted = LsragStructurizeService(compiler).admit(
        bind_structurize(
            clean_text=clean,
            clean_artifact_uuid="clean-artifact",
            clean_digest=digest,
            layered_candidate=candidate,
            granularity_set=profile,
            structure_artifact_uuid="structure-generation",
            projection_artifact_uuid="projection-generation",
        )
    )
    assert structure_payload(admitted.structure) == structure_payload(structure)
    assert structure_document_digest(admitted.structure) == structure_document_digest(structure)
    assert projection_digest(admitted.projection) == projection_digest(projection)
    assert admitted.adoption_report == report
    assert admitted.accepted_candidate == accepted


def test_admit_rejects_missing_or_summary_bearing_candidate() -> None:
    clean, candidate, profile = _legal()
    digest = stable_digest({"text": clean})
    service = LsragStructurizeService()
    dirty = _candidate(clean, {0: "Whole legal source", 1: "legal source"})
    dirty["layered_content"][0]["llm_summary"] = {"title": None, "body": "nope"}  # type: ignore[index]
    with pytest.raises(MkbError, match="STRUCTURE_SUMMARY_INVALID"):
        service.admit(
            bind_structurize(
                clean_text=clean,
                clean_artifact_uuid="clean-artifact",
                clean_digest=digest,
                layered_candidate=dirty,
                granularity_set=profile,
                structure_artifact_uuid="s",
                projection_artifact_uuid="p",
            )
        )
    with pytest.raises(MkbError, match="STRUCTURE_CANDIDATE_MISSING"):
        bind_structurize(
            clean_text=clean,
            clean_artifact_uuid="clean-artifact",
            clean_digest=digest,
            layered_candidate="not-a-mapping",  # type: ignore[arg-type]
            granularity_set=profile,
            structure_artifact_uuid="s",
            projection_artifact_uuid="p",
        )


def test_structurize_package_has_no_runtime_or_transport_imports() -> None:
    forbidden = ("src.runtime", "src.llm_adapters", "httpx", "openai", "vllm", "sqlite3", "aiosqlite")
    hits: list[str] = []
    root = REPOSITORY_ROOT / "src/services/lsrag_structurize"
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


def test_mixin_no_longer_calls_adopt_directly() -> None:
    text = (REPOSITORY_ROOT / "src/runtime/intake/generation_construct.py").read_text(encoding="utf-8")
    assert "adopt_layered_json_with_report" not in text
    assert "LsragStructurizeService" in text
    assert "_live_structured_generate" in text
    assert "_cli_layered_candidate" in text


def test_core_still_dispatches_structurize_to_mixin_method() -> None:
    text = (REPOSITORY_ROOT / "src/runtime/intake/core.py").read_text(encoding="utf-8")
    assert '"lsrag.structurize": self._structurize' in text


def test_services_package_does_not_own_cli_or_facade() -> None:
    root = REPOSITORY_ROOT / "src/services/lsrag_structurize"
    blob = "\n".join(path.read_text(encoding="utf-8") for path in root.glob("*.py"))
    assert "claude_cli" not in blob
    assert "InferenceFacade" not in blob
    assert "_complete_construct_summaries" not in blob
