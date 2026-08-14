"""NS1-T23/T24: B.json and C use explicit layered JSON handoffs."""

from __future__ import annotations

import json

import pytest

from src.runtime.inference.claude_cli import DeterministicNs1Stub
from src.runtime.intake.pipeline import IntakePipeline


@pytest.mark.asyncio
async def test_b_json_uses_material_and_c_runs_once_for_the_whole_package() -> None:
    stub = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, claude_cli=stub)  # type: ignore[arg-type]

    candidate, _ = await pipeline._cli_layered_candidate(
        clean_text="clean source",
        input_text="# markdown source\n\nbody",
        profile=(0, 1, 2),
    )
    completed, _ = await pipeline._cli_layered_summary(layered_candidate=candidate, profile=(0, 1, 2))

    assert [request.role for request in stub.requests] == ["json", "summarizer"]
    assert stub.requests[0].user_prompt == "# markdown source\n\nbody"
    assert stub.requests[0].json_schema is not None
    assert stub.requests[1].json_schema is not None
    whole_package = json.loads(stub.requests[1].user_prompt)
    assert len(whole_package["layered_content"]) == 3
    assert [
        (block["block_id"], block["granularity"], block["original_content"])
        for block in completed["layered_content"]
    ] == [
        (block["block_id"], block["granularity"], block["original_content"])
        for block in whole_package["layered_content"]
    ]
    assert all(block["llm_summary"]["body"] == block["original_content"]["body"] for block in completed["layered_content"])
