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
        "summarizer": Path("data/prompts/summarizer/promptC.summarizer.v1.md"),
    }
    for role, path in paths.items():
        body = path.read_bytes()
        assert body and hashlib.sha256(body).hexdigest()
        assert path.is_relative_to(Path("data/prompts")), role
    for key in ("json", "json_legal", "json_realestate"):
        json_prompt = paths[key].read_text(encoding="utf-8")
        assert "semantic_understanding" not in json_prompt
        assert "semantic_block" not in json_prompt
        assert "mkb.b-json-material.v1" in json_prompt
