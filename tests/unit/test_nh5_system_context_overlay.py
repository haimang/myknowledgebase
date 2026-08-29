"""NH5-T04: S04 owns context metadata while g0 remains admitted clean."""

from __future__ import annotations

import pytest

from src.contracts.common.errors import MkbError
from src.runtime.intake.generation_assemble import overlay_system_context_meta, overlay_system_g0


def test_system_context_overwrites_model_authority_and_preserves_title() -> None:
    clean = "Admitted clean body"
    candidate = overlay_system_g0(
        clean_text=clean,
        candidate={
            "context_meta": {
                "title": "Model title candidate",
                "realm": "hallucinated",
                "channel": "hallucinated",
            },
            "layered_content": [
                {
                    "block_id": 77,
                    "granularity": 0,
                    "original_content": {"title": "wrong", "body": "wrong"},
                    "llm_summary": {"title": None, "body": None},
                }
            ],
        },
        profile=(0,),
    )
    overlaid = overlay_system_context_meta(
        candidate=candidate,
        revision_semantics={
            "realm": "documentation",
            "type": "article",
            "channel": "policy",
            "source_name": "owner-source",
            "context_tags": ["tag:a", "tag:b"],
            "is_active": 1,
        },
    )
    assert overlaid["context_meta"] == {
        "title": "Model title candidate",
        "realm": "documentation",
        "type": "article",
        "channel": "policy",
        "source_name": "owner-source",
        "tags": ["tag:a", "tag:b"],
    }
    g0 = overlaid["layered_content"][0]
    assert g0["granularity"] == 0
    assert g0["original_content"]["body"] == clean
    assert "documentation" not in g0["original_content"]["body"]


def test_missing_s04_context_never_becomes_empty_overlay_success() -> None:
    with pytest.raises(MkbError) as raised:
        overlay_system_context_meta(candidate={"context_meta": {}}, revision_semantics={})
    assert raised.value.code == "STRUCTURE_CONTEXT_SEMANTICS_INCOMPLETE"
