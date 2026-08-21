"""Unit tests for NS8: 10k adaptive chunking and vLLM Cuts schema routing."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.contracts.inference.models import (
    InferenceBinding,
    StructuredGenerateRequest,
    StructuredGenerateResponse,
)
from src.llm_adapters.local_vllm import _structured_json_schema
from src.runtime.inference.claude_cli import ClaudeCliResult


def _make_dummy_binding() -> InferenceBinding:
    return InferenceBinding(
        capability_key="structured_generate",
        adapter_kind="local_vllm",
        model_key="unsloth/Qwen3.8-27B-NVFP4",
        model_version="local",
        binding_digest="a" * 64,
    )


def test_ns8_t03_vllm_cuts_schema_routing_and_cleansing() -> None:
    """NS8-T03: _structured_json_schema defaults to mkb.b-json-cuts for cuts schema refs."""
    # Case 1: Explicit json_schema in payload_extra
    custom_schema = {
        "$id": "https://example.com/schema",
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "cuts": {
                "type": "array",
                "items": {"type": "object", "properties": {"title": {"type": "string"}}},
            }
        },
    }
    req1 = StructuredGenerateRequest(
        team_uuid="01a00822-bc2b-7145-ad55-e9b5c3aa2c60",
        binding=_make_dummy_binding(),
        prompt_ref="promptB.documentation.g1.v5",
        prompt_digest="b" * 64,
        input_text="sample text",
        json_schema_ref="mkb.b-json-cuts@v1",
        json_schema_digest="c" * 64,
        payload_extra={"json_schema": custom_schema},
    )
    res1 = _structured_json_schema(req1)
    assert "$id" not in res1
    assert "$schema" not in res1
    assert "cuts" in res1.get("properties", {})

    # Case 2: No schema provided, json_schema_ref points to mkb.b-json-cuts
    req2 = StructuredGenerateRequest(
        team_uuid="01a00822-bc2b-7145-ad55-e9b5c3aa2c60",
        binding=_make_dummy_binding(),
        prompt_ref="promptB.documentation.g1.v5",
        prompt_digest="b" * 64,
        input_text="sample text",
        json_schema_ref="mkb.b-json-cuts@v1",
        json_schema_digest="c" * 64,
    )
    res2 = _structured_json_schema(req2)
    assert "$id" not in res2
    assert "$schema" not in res2
    # Must be cuts schema with cuts property, NOT layered_content
    assert "cuts" in res2.get("properties", {}), f"Expected cuts property in schema, got: {list(res2.keys())}"
    assert "layered_content" not in res2.get("properties", {})


@pytest.mark.asyncio
async def test_ns8_t01_cli_layered_candidate_10k_chunking() -> None:
    """NS8-T01: _cli_layered_candidate triggers chunking for >10k characters (e.g. 18.5k)."""
    from src.runtime.intake.generation_construct import IntakeGenerationConstructMixin

    # Generate ~18.5k markdown text with headings
    section1 = "# Section 1\n" + ("This is paragraph content in section 1. " * 150) + "\n\n"
    section2 = "## Section 2\n" + ("This is paragraph content in section 2. " * 150) + "\n\n"
    section3 = "### Section 3\n" + ("This is paragraph content in section 3. " * 150) + "\n\n"
    long_text = section1 + section2 + section3
    assert 10000 < len(long_text) < 20000, f"Text length was {len(long_text)}, expected between 10k and 20k"

    mixin = IntakeGenerationConstructMixin()
    mixin._prompt_root = Path("data/prompts")
    mixin._storage = MagicMock()
    mixin._persistence = MagicMock()

    # Mock prompt file resolution to return g1.v5 path
    g1_v5_path = Path("data/prompts/json/promptB.documentation.g1.v5.md")
    mixin._ns1_prompt_file = MagicMock(return_value=(g1_v5_path, "a" * 64))
    mixin._prompt_relative_path = MagicMock(return_value="json/promptB.documentation.g1.v5.md")

    # Mock Claude CLI on mixin
    mock_cli = MagicMock()
    mock_cli.run = AsyncMock(
        return_value=ClaudeCliResult(
            "{}",
            {"schema_version": "mkb.b-json-cuts.v1", "cuts": [{"cut_index": 0, "title": "Sec"}]},
            0,
            session_id="test-session",
            usage={"input_tokens": 100, "output_tokens": 50, "total_tokens": 150},
            is_error=False,
        )
    )
    mixin._claude_cli = mock_cli

    candidate, receipt = await mixin._cli_layered_candidate(
        clean_text=long_text,
        input_text=None,
        profile=(1,),
        state=None,
    )

    # With 10k threshold, an 18.5k doc MUST be chunked into at least 2 chunks
    assert mock_cli.run.call_count >= 2, f"Expected at least 2 chunk calls, but got {mock_cli.run.call_count}"
    assert candidate["schema_version"] == "mkb.b-json-cuts.v1"
    assert len(candidate["cuts"]) >= 2
    assert receipt["transport"] == "claude_cli"


@pytest.mark.asyncio
async def test_ns8_t02_live_structured_generate_schema_passthrough() -> None:
    """NS8-T02: _live_structured_generate transmits schema in request."""
    from src.contracts.runtime.models import ProcessCommand
    from src.runtime.intake.generation_live import IntakeGenerationLiveMixin
    from src.runtime.intake.types import _FrozenGenerationConfig

    mixin = IntakeGenerationLiveMixin()
    mock_resp = StructuredGenerateResponse(
        text="{}",
        value={"schema_version": "mkb.b-json-cuts.v1", "cuts": []},
        model_key="unsloth/Qwen3.8-27B-NVFP4",
        model_version="local",
        latency_ms=10,
        invocation_uuid="01a02342-89fa-7218-ad7c-23af4b50bd68",
        request_digest="e" * 64,
    )
    mock_inference = MagicMock()
    mock_inference.structured_generate = AsyncMock(return_value=(mock_resp, mock_resp.value))
    mixin._inference = mock_inference
    mixin._prompt_root = Path("data/prompts")
    mixin._persistence = MagicMock()
    mixin._storage = MagicMock()
    mixin._persist_completed_generation_invocation = AsyncMock()

    # Mock _resolve_frozen_generation_config
    dummy_binding = _make_dummy_binding()
    frozen_cfg = _FrozenGenerationConfig(
        capability_key="structured_generate",
        binding=dummy_binding,
        prompt_key="promptB.documentation.g1",
        prompt_version="v5",
        prompt_digest="a" * 64,
        prompt_text="dummy prompt",
        schema_key="mkb.b-json-cuts",
        schema_version="v1",
        schema_digest="b" * 64,
    )
    mixin._resolve_frozen_generation_config = AsyncMock(return_value=frozen_cfg)

    command = ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid="01a00822-bc2b-7145-ad55-e9b5c3aa2c60",
        task_uuid="01a02342-89fa-7218-ad7c-23af4b50bd68",
        process_uuid="01a02342-89fa-7219-ad7c-23af4b50bd69",
        trace_uuid="01a02342-89fa-721a-ad7c-23af4b50bd70",
        execution_uuid="01a02342-89fa-721b-ad7c-23af4b50bd71",
        process_key="structurize",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest="d" * 64,
        input_manifest_ref="input-manifest-ref",
        input_manifest_digest="e" * 64,
        config_snapshot_ref="mock-ref",
        config_snapshot_digest="c" * 64,
        binding_digest="f" * 64,
    )

    await mixin._live_structured_generate(
        command,
        stage_key="structurize",
        input_text="Sample input text",
        prompt_key="promptB.documentation.g1",
        prompt_version="v5",
        schema_key="mkb.b-json-cuts",
        schema_version="v1",
        input_digest="d" * 64,
    )

    assert mock_inference.structured_generate.call_count == 1
    call_req = mock_inference.structured_generate.call_args[0][0]
    # Verify schema is passed either in payload_extra["json_schema"] or directly
    schema_in_req = getattr(call_req, "json_schema", None) or call_req.payload_extra.get("json_schema")
    assert isinstance(schema_in_req, dict)
    assert "cuts" in schema_in_req.get("properties", {})
