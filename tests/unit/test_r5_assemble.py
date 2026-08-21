"""R5 layered JSON assemble and overlay tests."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.lsrag.layered_content import normalize_layered_text
from src.runtime.intake.generation_assemble import (
    assemble_from_cuts,
    overlay_system_g0,
)
from src.services.lsrag_compiler.adopt import adopt_layered_json_with_report


def _clean() -> str:
    return (
        "# 阶段收口\n\n"
        "> 状态: closed-with-explicit-deferrals\n\n"
        "## 0. 一句话\n\n"
        "按能力边界抽出叶服务。\n\n"
        "## 1. 工作项\n\n"
        "P1-01 已验证。"
    )


def test_overlay_drops_fragment_g0_and_admits() -> None:
    clean = _clean()
    frag_g0 = clean[:-10]
    g1_1 = "# 阶段收口\n\n> 状态: closed-with-explicit-deferrals"
    g1_2 = "## 0. 一句话\n\n按能力边界抽出叶服务。"
    g1_3 = "## 1. 工作项\n\nP1-01 已验证。"
    candidate = {
        "schema_version": "lsrag.layered_content.v1",
        "layered_content": [
            {
                "block_id": 0,
                "granularity": 0,
                "original_content": {"title": None, "body": frag_g0},
                "llm_summary": {"title": None, "body": None},
            },
            {
                "block_id": 1,
                "granularity": 1,
                "original_content": {"title": "T1", "body": g1_1},
                "llm_summary": {"title": None, "body": None},
            },
            {
                "block_id": 2,
                "granularity": 1,
                "original_content": {"title": "T2", "body": g1_2},
                "llm_summary": {"title": None, "body": None},
            },
            {
                "block_id": 3,
                "granularity": 1,
                "original_content": {"title": "T3", "body": g1_3},
                "llm_summary": {"title": None, "body": None},
            },
        ],
    }
    assembled = overlay_system_g0(clean_text=clean, candidate=candidate, profile=(0, 1))
    structure, projection, report = adopt_layered_json_with_report(
        clean_text=clean,
        layered_json=assembled,
        generation_artifact_uuid="018f0000-0000-7000-8000-000000000001",
        clean_artifact_uuid="018f0000-0000-7000-8000-000000000002",
        granularity_set=(0, 1),
    )
    assert structure is not None
    assert len(projection.blocks) >= 4


def test_overlay_only_fragment_g0_still_mismatch() -> None:
    clean = _clean()
    candidate = {
        "schema_version": "lsrag.layered_content.v1",
        "layered_content": [
            {
                "block_id": 0,
                "granularity": 0,
                "original_content": {"title": None, "body": "short"},
                "llm_summary": {"title": None, "body": None},
            },
        ],
    }
    assembled = overlay_system_g0(clean_text=clean, candidate=candidate, profile=(0, 1))
    with pytest.raises(MkbError) as exc:
        adopt_layered_json_with_report(
            clean_text=clean,
            layered_json=assembled,
            generation_artifact_uuid="018f0000-0000-7000-8000-000000000001",
            clean_artifact_uuid="018f0000-0000-7000-8000-000000000002",
            granularity_set=(0, 1),
        )
    assert exc.value.code == "STRUCTURE_GRANULARITY_SET_MISMATCH"


def test_overlay_no_g0_two_g1_inserts_system_g0() -> None:
    clean = _clean()
    g1_1 = "## 0. 一句话\n\n按能力边界抽出叶服务。"
    candidate = {
        "schema_version": "lsrag.layered_content.v1",
        "layered_content": [
            {
                "block_id": 1,
                "granularity": 1,
                "original_content": {"title": "T1", "body": g1_1},
                "llm_summary": {"title": None, "body": None},
            },
        ],
    }
    assembled = overlay_system_g0(clean_text=clean, candidate=candidate, profile=(0, 1))
    assert assembled["layered_content"][0]["granularity"] == 0
    assert assembled["layered_content"][0]["original_content"]["body"] == normalize_layered_text(clean)
    assert assembled["layered_content"][1]["granularity"] == 1


def test_overlay_drops_secret() -> None:
    clean = _clean()
    candidate = {
        "schema_version": "lsrag.layered_content.v1",
        "layered_content": [
            {
                "block_id": 0,
                "granularity": 0,
                "original_content": {"title": None, "body": "TOP_SECRET_PASSWORD"},
                "llm_summary": {"title": None, "body": None},
            },
            {
                "block_id": 1,
                "granularity": 1,
                "original_content": {"title": "T1", "body": "P1-01 已验证。"},
                "llm_summary": {"title": None, "body": None},
            },
        ],
    }
    assembled = overlay_system_g0(clean_text=clean, candidate=candidate, profile=(0, 1))
    text_repr = str(assembled)
    assert "TOP_SECRET_PASSWORD" not in text_repr


def test_assemble_from_cuts_positive() -> None:
    clean = _clean()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {"title": "文首", "start": "# 阶段收口", "end": "closed-with-explicit-deferrals"},
            {"title": "一句话", "start": "## 0. 一句话", "end": "按能力边界抽出叶服务。"},
            {"title": "工作项", "start": "## 1. 工作项", "end": "P1-01 已验证。"},
        ],
    }
    assembled = assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    structure, projection, report = adopt_layered_json_with_report(
        clean_text=clean,
        layered_json=assembled,
        generation_artifact_uuid="018f0000-0000-7000-8000-000000000001",
        clean_artifact_uuid="018f0000-0000-7000-8000-000000000002",
        granularity_set=(0, 1),
    )
    assert structure is not None
    assert len(projection.blocks) == 4


def test_assemble_cut_start_missing() -> None:
    clean = _clean()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {"title": "文首", "start": "NONEXISTENT_START", "end": "closed-with-explicit-deferrals"},
        ],
    }
    with pytest.raises(MkbError) as exc:
        assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    assert exc.value.code == "CUTS_ANCHOR_MISSING"


def test_assemble_cut_ambiguous_start() -> None:
    clean = "AAA middle AAA end"
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {"title": "T", "start": "AAA", "end": "end"},
        ],
    }
    with pytest.raises(MkbError) as exc:
        assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    assert exc.value.code == "CUTS_ANCHOR_AMBIGUOUS"


def test_assemble_cut_order_invalid() -> None:
    clean = _clean()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {"title": "T", "start": "P1-01 已验证。", "end": "# 阶段收口"},
        ],
    }
    with pytest.raises(MkbError) as exc:
        assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    assert exc.value.code in ("CUTS_ANCHOR_MISSING", "CUTS_ORDER_INVALID")


def test_assemble_cuts_empty() -> None:
    clean = _clean()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [],
    }
    with pytest.raises(MkbError) as exc:
        assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    assert exc.value.code == "CUTS_EMPTY"


def test_assemble_cuts_forbidden_key() -> None:
    clean = _clean()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {"title": "T", "start": "# 阶段收口", "end": "closed-with-explicit-deferrals", "span": [0, 10]},
        ],
    }
    with pytest.raises(MkbError) as exc:
        assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    assert exc.value.code == "CUTS_SCHEMA_INVALID"


def test_assemble_keeps_clean_normalization() -> None:
    clean = "  # Unnormalized Text \r\n\r\n Line 2 \r\n"
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {"title": "T", "start": "# Unnormalized Text", "end": "Line 2"},
        ],
    }
    assembled = assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    assert assembled["layered_content"][0]["original_content"]["body"] == normalize_layered_text(clean)


def test_architecture_generation_assemble_not_in_leaf() -> None:
    assemble_file = Path("src/runtime/intake/generation_assemble.py")
    text = assemble_file.read_text(encoding="utf-8")
    assert "src.services.lsrag" not in text
    assert "from src.services.lsrag" not in text
