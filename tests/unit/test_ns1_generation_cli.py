"""NS1-T23/T24: B.json and C use explicit layered JSON handoffs."""

from __future__ import annotations

import json

import pytest

from src.contracts.common.errors import MkbError
from src.runtime.inference.claude_cli import DeterministicNs1Stub
from src.runtime.intake.pipeline import IntakePipeline


@pytest.mark.asyncio
async def test_b_json_uses_material_and_c_runs_once_for_the_whole_package() -> None:
    stub = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, claude_cli=stub)  # type: ignore[arg-type]
    package = IntakePipeline._bjson_user_material(
        clean_text="clean source",
        markdown_text="# markdown source\n\nbody",
    )

    candidate, _ = await pipeline._cli_layered_candidate(
        clean_text="clean source",
        input_text=package,
        profile=(0, 1, 2),
    )
    completed, _ = await pipeline._cli_layered_summary(layered_candidate=candidate, profile=(0, 1, 2))

    assert [request.role for request in stub.requests] == ["json", "summarizer"]
    assert stub.requests[0].user_prompt == package
    assert candidate["layered_content"][0]["original_content"]["body"] == "clean source"
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


@pytest.mark.asyncio
async def test_b_json_without_frozen_json_selection_fails_closed() -> None:
    stub = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, claude_cli=stub)  # type: ignore[arg-type]
    with pytest.raises(MkbError, match="PROMPT_NOT_REGISTERED"):
        await pipeline._cli_layered_candidate(
            clean_text="clean source",
            input_text="clean source",
            profile=(0, 1, 2),
            state={"payload": {}},
        )


def test_live_app_composition_wires_ns1_cli(tmp_path) -> None:
    from fastapi.testclient import TestClient

    from api.app import create_app
    from src.runtime.config import Settings

    app = create_app(
        Settings(
            internal_token="ns1-live-cli",
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            persistence_backend="sqlite",
            concurrent_writes_required=False,
            native_vector_required=False,
            inference_probe_enabled=False,
            live_inference=True,
            ns1_cli_mode="stub",
        )
    )
    with TestClient(app):
        handler = app.state.container.workflow_worker.handler
        assert isinstance(handler._claude_cli, DeterministicNs1Stub)
        assert handler._live_inference is True


def test_layered_profile_does_not_invent_generic_set() -> None:
    from src.contracts.common.errors import MkbError as ProfileError

    with pytest.raises(ProfileError, match="unavailable"):
        IntakePipeline._layered_profile({"payload": {}}, error_code="STRUCTURE_PROFILE_INVALID")
