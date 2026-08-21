"""NS7 RED-first unit tests for anchor tolerance and resilient slicing."""

from __future__ import annotations

import pytest

from src.contracts.common.errors import MkbError
from src.runtime.intake.generation_assemble import (
    assemble_from_cuts,
)
from src.services.lsrag_compiler.adopt import adopt_layered_json_with_report


def _sample_doc() -> str:
    return (
        "# 治理总览\n\n"
        "> 状态: active\n\n"
        "## 1. 系统要求\n\n"
        "运行环境必须在 `-p`，建议 `--bare`)\n\n"
        "# 转录说明\n\n"
        "所有转录步骤必须遵循幂等约束。\n\n"
        "## 3. 最终结论\n\n"
        "本次治理全面收口。"
    )


def test_ns7_t01_trailing_punctuation_tolerance() -> None:
    """NS7-T01: model end anchor adds a Chinese period '。' not in clean text."""
    clean = _sample_doc()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {
                "title": "系统要求",
                "start": "## 1. 系统要求",
                "end": "必须在 `-p`，建议 `--bare`)。",  # Clean text does NOT have trailing '。'
            },
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
    # Verify the sliced body is exact substring of clean text
    sliced_body = assembled["layered_content"][1]["original_content"]["body"]
    assert sliced_body in clean
    assert "建议 `--bare`)" in sliced_body


def test_ns7_t02_markdown_heading_level_tolerance() -> None:
    """NS7-T02: model start anchor outputs '## 转录说明' while clean has '# 转录说明'."""
    clean = _sample_doc()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {
                "title": "转录说明",
                "start": "## 转录说明",  # Clean text has '# 转录说明'
                "end": "所有转录步骤必须遵循幂等约束。",
            },
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
    sliced_body = assembled["layered_content"][1]["original_content"]["body"]
    assert sliced_body in clean
    assert "# 转录说明" in sliced_body


def test_ns7_t03_whitespace_and_inline_code_tolerance() -> None:
    """NS7-T03: model normalizes whitespace or omits backticks in anchor search."""
    clean = _sample_doc()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {
                "title": "系统要求",
                "start": "1. 系统要求",  # Omitted '## '
                "end": "建议 --bare)",  # Omitted backticks
            },
        ],
    }
    assembled = assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    sliced_body = assembled["layered_content"][1]["original_content"]["body"]
    assert sliced_body in clean
    assert "必须在 `-p`" in sliced_body


def test_ns7_t05_genuinely_missing_anchor_fails_closed() -> None:
    """NS7-T05: completely non-existent text must still fail-closed with CUTS_ANCHOR_MISSING."""
    clean = _sample_doc()
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {
                "title": "不存在",
                "start": "完全不存在的起始文本内容XYZ123",
                "end": "本次治理全面收口。",
            },
        ],
    }
    with pytest.raises(MkbError) as exc:
        assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    assert exc.value.code == "CUTS_ANCHOR_MISSING"


def test_ns7_t06_ambiguous_anchor_fails_closed() -> None:
    """NS7-T06: ambiguous anchor matching multiple disjoint locations must fail-closed."""
    clean = "重复内容 章节A 结尾1\n\n重复内容 章节B 结尾2"
    cuts_pack = {
        "schema_version": "mkb.b-json-cuts.v1",
        "cuts": [
            {
                "title": "重复",
                "start": "重复内容",
                "end": "结尾2",
            },
        ],
    }
    with pytest.raises(MkbError) as exc:
        assemble_from_cuts(clean_text=clean, cuts_pack=cuts_pack, profile=(0, 1))
    assert exc.value.code == "CUTS_ANCHOR_AMBIGUOUS"
