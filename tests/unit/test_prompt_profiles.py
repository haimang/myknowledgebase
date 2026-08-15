"""Closed domain/flavor/granularity defaults for documentation prompt clusters."""

from __future__ import annotations

import pytest

from src.services.prompt_profiles import default_prompt_ids, json_prompt_id_for


def test_documentation_flavor_selects_markdown_hop_and_g1_json() -> None:
    selected = default_prompt_ids(domain="documentation", flavor="code-review")
    assert selected == {
        "clean": "promptA.documentation.default",
        "markdown": "promptB.documentation.code-review",
        "json": "promptB.documentation.g1",
        "summarizer": "promptC.documentation.default",
    }
    assert default_prompt_ids(domain="documentation", flavor="eval")["markdown"] == "promptB.documentation.eval"


def test_documentation_without_flavor_skips_markdown_and_defaults_to_g1() -> None:
    selected = default_prompt_ids(domain="documentation", flavor=None)
    assert selected["json"] == "promptB.documentation.g1"
    assert selected["markdown"] is None


def test_granularity_selects_inclusive_json_templates() -> None:
    assert json_prompt_id_for(domain="documentation", granularity="g0") == "promptB.documentation.g0"
    assert json_prompt_id_for(domain="documentation", granularity="g1") == "promptB.documentation.g1"
    assert json_prompt_id_for(domain="documentation", granularity="g2") == "promptB.documentation.g2"
    assert json_prompt_id_for(domain=None, granularity="g1") == "promptB.json.g1"
    assert default_prompt_ids(domain=None, flavor=None, granularity="g0")["json"] == "promptB.json.g0"
    assert default_prompt_ids(domain="documentation", flavor="qna", granularity="g2")["json"] == "promptB.documentation.g2"


def test_unknown_or_incomplete_profile_fails_closed() -> None:
    assert default_prompt_ids(domain=None, flavor=None) == {}
    with pytest.raises(ValueError, match="flavor requires domain"):
        default_prompt_ids(domain=None, flavor="qna")
    with pytest.raises(ValueError, match="unsupported intake domain"):
        default_prompt_ids(domain="legal", flavor="qna")
    with pytest.raises(ValueError, match="unsupported documentation flavor"):
        default_prompt_ids(domain="documentation", flavor="handbook")
    with pytest.raises(ValueError, match="unsupported granularity"):
        default_prompt_ids(domain="documentation", flavor=None, granularity="g3")
