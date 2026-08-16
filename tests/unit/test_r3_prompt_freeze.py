"""R3 prompt freeze: g1 v3 closed set, C stays v2, catalog default is v3."""

from __future__ import annotations

from pathlib import Path

from src.services.registry import DEFAULT_CATALOG_PROMPTS

ROOT = Path(__file__).resolve().parents[2]
G1 = ROOT / "data/prompts/json/promptB.documentation.g1.v3.md"
C = ROOT / "data/prompts/summarizer/promptC.documentation.default.v2.md"


def test_g1_v3_is_closed_to_zero_and_one() -> None:
    text = G1.read_text(encoding="utf-8")
    assert "出现 granularity=2 则整包失败" in text
    assert "步骤 1" in text
    assert "正例" in text
    assert "反例" in text
    assert "MKB" not in text
    assert '"granularity":2' not in text
    assert "semantic_block" not in text


def test_c_default_stays_v2_and_mentions_original() -> None:
    text = C.read_text(encoding="utf-8")
    assert "original_content" in text
    assert "MKB" not in text
    catalog = {row[0]: row for row in DEFAULT_CATALOG_PROMPTS}
    assert catalog["promptC.documentation.default"][1] == "v2"
    assert catalog["promptB.documentation.g1"][1] == "v4"


def test_markdown_hop_writes_evidence_stage_markdown() -> None:
    construct = (ROOT / "src/runtime/intake/generation_construct.py").read_text(encoding="utf-8")
    assert 'stage_key="markdown"' in construct
    assert 'stage_key="transcribe_markdown"' not in construct
