"""R4 prompt freeze: g1 v4 exact-set, C stays v2, catalog default is v4."""

from __future__ import annotations

from pathlib import Path

from src.services.registry import DEFAULT_CATALOG_PROMPTS

ROOT = Path(__file__).resolve().parents[2]
G1 = ROOT / "data/prompts/json/promptB.documentation.g1.v4.md"
C = ROOT / "data/prompts/summarizer/promptC.documentation.default.v2.md"
V3 = ROOT / "data/prompts/json/promptB.documentation.g1.v3.md"


def test_g1_v4_requires_both_layers_and_forbids_g2() -> None:
    text = G1.read_text(encoding="utf-8")
    assert "只交一块 granularity=0" in text
    assert "只交 g=1，没有 g=0" in text
    assert "必须至少一块 g=1" in text
    assert "恰好" in text
    assert "步骤 1" in text
    assert "正例" in text
    assert "反例" in text
    assert "MKB" not in text
    assert '"granularity":2' not in text
    assert "semantic_block" not in text


def test_v3_bytes_are_not_overwritten() -> None:
    text = V3.read_text(encoding="utf-8")
    assert "出现 granularity=2 则整包失败" in text
    assert "只交一块 granularity=0" not in text


def test_catalog_default_is_g1_v4_and_c_stays_v2() -> None:
    catalog = {row[0]: row for row in DEFAULT_CATALOG_PROMPTS}
    assert catalog["promptB.documentation.g1"][1] == "v4"
    assert catalog["promptB.documentation.g1"][2].endswith("g1.v4.md")
    assert catalog["promptC.documentation.default"][1] == "v2"
