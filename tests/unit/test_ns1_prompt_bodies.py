"""NS1-T02: checked-in four-role prompt bodies are hashable and contract-safe."""

from __future__ import annotations

import hashlib
from pathlib import Path


def test_four_role_prompt_bodies_are_nonempty_and_b_json_has_no_legacy_contract_terms() -> None:
    paths = {
        "clean": Path("data/prompts/clean/promptA.clean.v1.md"),
        "markdown": Path("data/prompts/markdown/promptB.markdown.legal.v1.md"),
        "json": Path("data/prompts/json/promptB.json.generic.v1.md"),
        "json_legal": Path("data/prompts/json/promptB.json.legal.v1.md"),
        "json_realestate": Path("data/prompts/json/promptB.json.realestate.v1.md"),
        "json_documentation": Path("data/prompts/json/promptB.documentation.default.v1.md"),
        "json_documentation_g0": Path("data/prompts/json/promptB.documentation.g0.v1.md"),
        "json_documentation_g1": Path("data/prompts/json/promptB.documentation.g1.v1.md"),
        "json_documentation_g2": Path("data/prompts/json/promptB.documentation.g2.v1.md"),
        "json_documentation_v2": Path("data/prompts/json/promptB.documentation.default.v2.md"),
        "json_documentation_g1_v2": Path("data/prompts/json/promptB.documentation.g1.v2.md"),
        "json_documentation_g1_v3": Path("data/prompts/json/promptB.documentation.g1.v3.md"),
        "json_documentation_g1_v4": Path("data/prompts/json/promptB.documentation.g1.v4.md"),
        "json_documentation_g2_v2": Path("data/prompts/json/promptB.documentation.g2.v2.md"),
        "json_g0": Path("data/prompts/json/promptB.json.g0.v1.md"),
        "json_g1": Path("data/prompts/json/promptB.json.g1.v1.md"),
        "json_g2": Path("data/prompts/json/promptB.json.g2.v1.md"),
        "clean_documentation": Path("data/prompts/clean/promptA.documentation.default.v1.md"),
        "markdown_qna": Path("data/prompts/markdown/promptB.documentation.qna.v1.md"),
        "markdown_eval": Path("data/prompts/markdown/promptB.documentation.eval.v1.md"),
        "markdown_closure": Path("data/prompts/markdown/promptB.documentation.closure.v1.md"),
        "markdown_plan": Path("data/prompts/markdown/promptB.documentation.plan.v1.md"),
        "markdown_review": Path("data/prompts/markdown/promptB.documentation.code-review.v1.md"),
        "summarizer": Path("data/prompts/summarizer/promptC.summarizer.v1.md"),
        "summarizer_documentation": Path("data/prompts/summarizer/promptC.documentation.default.v1.md"),
        "summarizer_documentation_v2": Path("data/prompts/summarizer/promptC.documentation.default.v2.md"),
    }
    for role, path in paths.items():
        body = path.read_bytes()
        assert body and hashlib.sha256(body).hexdigest()
        assert path.is_relative_to(Path("data/prompts")), role
    for key in (
        "json",
        "json_legal",
        "json_realestate",
        "json_documentation",
        "json_documentation_g0",
        "json_documentation_g1",
        "json_documentation_g2",
        "json_documentation_v2",
        "json_documentation_g1_v2",
        "json_documentation_g1_v3",
        "json_documentation_g1_v4",
        "json_documentation_g2_v2",
        "json_g0",
        "json_g1",
        "json_g2",
    ):
        json_prompt = paths[key].read_text(encoding="utf-8")
        assert "semantic_understanding" not in json_prompt
        assert "semantic_block" not in json_prompt
        assert "mkb.b-json-material.v1" in json_prompt
    for key in (
        "json_documentation_v2",
        "json_documentation_g1_v2",
        "json_documentation_g1_v3",
        "json_documentation_g1_v4",
        "json_documentation_g2_v2",
        "summarizer_documentation_v2",
    ):
        body = paths[key].read_text(encoding="utf-8")
        assert "步骤 1" in body, key
        assert "正例" in body and "反例" in body, key
    g1_v3 = paths["json_documentation_g1_v3"].read_text(encoding="utf-8")
    assert "出现 granularity=2 则整包失败" in g1_v3
    assert '"granularity":2' not in g1_v3
    g1_v4 = paths["json_documentation_g1_v4"].read_text(encoding="utf-8")
    assert "只交一块 granularity=0" in g1_v4
    assert "只交 g=1，没有 g=0" in g1_v4
    assert "必须至少一块 g=1" in g1_v4
    assert '"granularity":2' not in g1_v4
    for key, path in paths.items():
        if "documentation" in key or key.startswith("markdown_"):
            body = path.read_text(encoding="utf-8")
            assert "MKB" not in body, key
