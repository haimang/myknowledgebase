"""Unit tests for generation stage wiring, Qwen adapter contract, and salvage (NS2-T30..T35)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.inference.models import InferenceBinding, StructuredGenerateRequest
from src.contracts.runtime.models import ProcessCommand
from src.llm_adapters.local_vllm import LocalVllmAdapter
from src.runtime.inference.claude_cli import DeterministicNs1Stub
from src.runtime.intake.pipeline import IntakePipeline
from src.services.lsrag_compiler import LsragContractCompiler
from src.services.registry import SPARK_QWEN_GENERATE_MODEL_KEY


def _sample_command(*, pool: str = "local-inference") -> ProcessCommand:
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        process_key="lsrag.construct",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest="0" * 64,
        input_manifest_ref="ref",
        input_manifest_digest="0" * 64,
        config_snapshot_ref="cfg-ref",
        config_snapshot_digest="0" * 64,
        binding_digest="0" * 64,
        dispatch_pool=pool,  # type: ignore[arg-type]
        task_priority="normal",
    )


def _seed_construct_context(clean: str = "sample text") -> tuple[LsragContractCompiler, Any, dict[str, Any]]:
    compiler = LsragContractCompiler()
    accepted = {
        "context_meta": {},
        "layered_content": [
            {
                "block_id": 0,
                "granularity": 0,
                "original_content": {"title": None, "body": clean},
                "llm_summary": {"title": None, "body": None},
            }
        ],
    }
    _structure, projection = compiler.adopt_layered_json(
        clean_text=clean,
        layered_json=accepted,
        generation_artifact_uuid=uuid7(),
        projection_generation_artifact_uuid=uuid7(),
        clean_artifact_uuid=uuid7(),
        granularity_set=(0,),
    )
    return compiler, projection, accepted


@pytest.mark.asyncio
async def test_construct_dispatches_to_local_vllm_when_local_inference() -> None:
    # NS2-T30: dispatch_pool == 'local-inference' routes to local vLLM generate
    cli = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, inference=object(), claude_cli=cli, live_inference=True)  # type: ignore[arg-type]
    compiler, projection, accepted = _seed_construct_context()

    async def ok_generate(_command, *, layered_candidate):
        package = {
            **layered_candidate,
            "layered_content": [
                {
                    **block,
                    "llm_summary": {"title": None, "body": "local generated summary"},
                }
                for block in layered_candidate["layered_content"]
            ],
        }
        return package, {"status": "succeeded", "model_key": SPARK_QWEN_GENERATE_MODEL_KEY}

    pipeline._live_layered_summary_generate = ok_generate  # type: ignore[method-assign]
    command = _sample_command(pool="local-inference")
    state = {"payload": {}}

    completed, _summaries, invocations, cli_receipt = await pipeline._complete_construct_summaries(
        command,
        state,
        compiler=compiler,
        projection=projection,
        accepted_layered_candidate=accepted,
        profile=(0,),
    )

    assert cli.requests == []  # CLI not called
    assert cli_receipt is None
    assert invocations[0]["transport"] == "api_inference"
    assert invocations[0]["model_key"] == SPARK_QWEN_GENERATE_MODEL_KEY
    assert completed["layered_content"][0]["llm_summary"]["body"] == "local generated summary"


@pytest.mark.asyncio
async def test_construct_dispatches_to_claude_cli_when_non_interactive() -> None:
    # NS2-T31: dispatch_pool == 'non-interactive' routes to Claude CLI without touching local facade
    cli = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, inference=object(), claude_cli=cli, live_inference=True)  # type: ignore[arg-type]
    compiler, projection, accepted = _seed_construct_context()

    live_called = False

    async def boom_generate(_command, *, layered_candidate):
        nonlocal live_called
        live_called = True
        raise RuntimeError("Should not be called")

    pipeline._live_layered_summary_generate = boom_generate  # type: ignore[method-assign]
    command = _sample_command(pool="non-interactive")
    prompt = Path("data/prompts/summarizer/promptC.summarizer.v1.md")
    state = {
        "payload": {
            "compression_channel": "non-interactive",
            "prompt_selection": {
                "summarizer": {
                    "prompt_id": "promptC.summarizer",
                    "version": "v1",
                    "content_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
                    "git_relative_path": "summarizer/promptC.summarizer.v1.md",
                    "role": "summarizer",
                }
            },
        }
    }

    completed, _summaries, invocations, cli_receipt = await pipeline._complete_construct_summaries(
        command,
        state,
        compiler=compiler,
        projection=projection,
        accepted_layered_candidate=accepted,
        profile=(0,),
    )

    assert not live_called
    assert [req.role for req in cli.requests] == ["summarizer"]
    assert invocations == []
    assert cli_receipt is not None
    assert cli_receipt["transport"] == "claude_cli"
    assert cli_receipt["compression_channel"] == "non-interactive"
    assert "salvage_from" not in cli_receipt


@pytest.mark.asyncio
async def test_local_inference_failure_salvages_once_with_claude_cli() -> None:
    # NS2-T32: local inference failure records salvage receipt and falls back to Claude -p exactly once
    cli = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, inference=object(), claude_cli=cli, live_inference=True)  # type: ignore[arg-type]
    compiler, projection, accepted = _seed_construct_context()

    async def fail_generate(_command, *, layered_candidate):
        del layered_candidate
        raise MkbError("INFERENCE_VALIDATION_RESPONSE", "vLLM output was empty", 502)

    pipeline._live_layered_summary_generate = fail_generate  # type: ignore[method-assign]
    command = _sample_command(pool="local-inference")
    prompt = Path("data/prompts/summarizer/promptC.summarizer.v1.md")
    state = {
        "payload": {
            "compression_channel": "local-inference",
            "prompt_selection": {
                "summarizer": {
                    "prompt_id": "promptC.summarizer",
                    "version": "v1",
                    "content_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
                    "git_relative_path": "summarizer/promptC.summarizer.v1.md",
                    "role": "summarizer",
                }
            },
        }
    }

    completed, _summaries, invocations, cli_receipt = await pipeline._complete_construct_summaries(
        command,
        state,
        compiler=compiler,
        projection=projection,
        accepted_layered_candidate=accepted,
        profile=(0,),
    )

    assert len(cli.requests) == 1
    assert cli_receipt is not None
    assert cli_receipt["transport"] == "claude_cli"
    assert cli_receipt["compression_channel"] == "non-interactive"
    assert cli_receipt["salvage_from"] == "local-inference"
    assert cli_receipt["salvage_error_code"] == "INFERENCE_VALIDATION_RESPONSE"
    assert completed["layered_content"][0]["llm_summary"]["body"]


@pytest.mark.asyncio
async def test_low_priority_local_failure_does_not_salvage_to_cli() -> None:
    # NS2-T37: low + salvageable local error must fail-closed with zero CLI calls
    cli = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, inference=object(), claude_cli=cli, live_inference=True)  # type: ignore[arg-type]
    compiler, projection, accepted = _seed_construct_context()

    async def fail_generate(_command, *, layered_candidate):
        del layered_candidate
        raise MkbError("INFERENCE_VALIDATION_RESPONSE", "vLLM output was empty", 502)

    pipeline._live_layered_summary_generate = fail_generate  # type: ignore[method-assign]
    command = _sample_command(pool="local-inference")
    command = command.model_copy(update={"task_priority": "low"})
    prompt = Path("data/prompts/summarizer/promptC.summarizer.v1.md")
    state = {
        "payload": {
            "prompt_selection": {
                "summarizer": {
                    "prompt_id": "promptC.summarizer",
                    "version": "v1",
                    "content_sha256": hashlib.sha256(prompt.read_bytes()).hexdigest(),
                    "git_relative_path": "summarizer/promptC.summarizer.v1.md",
                    "role": "summarizer",
                }
            },
        }
    }

    with pytest.raises(MkbError) as rejected:
        await pipeline._complete_construct_summaries(
            command,
            state,
            compiler=compiler,
            projection=projection,
            accepted_layered_candidate=accepted,
            profile=(0,),
        )

    assert rejected.value.code == "INFERENCE_VALIDATION_RESPONSE"
    assert cli.requests == []


@pytest.mark.asyncio
async def test_local_vllm_adapter_sends_exact_qwen_json_object_payload() -> None:
    # NS2-T34: Qwen adapter sends system + user + json_object, omits max_tokens, strips reasoning.
    # enable_thinking=false is required so this checkpoint fills content instead of reasoning.
    captured: dict[str, Any] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["body"] = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": SPARK_QWEN_GENERATE_MODEL_KEY,
                "choices": [
                    {
                        "message": {
                            "reasoning": "internal scratch to drop",
                            "content": '{"summary": "clean content"}',
                        }
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            },
        )

    adapter = LocalVllmAdapter("https://models.example:8443/", transport=httpx.MockTransport(handler))
    binding = InferenceBinding(
        capability_key="structured_generate",
        adapter_kind="local_vllm",
        model_key=SPARK_QWEN_GENERATE_MODEL_KEY,
        model_version="v1",
        binding_digest="0" * 64,
    )
    response = await adapter.generate(
        StructuredGenerateRequest(
            team_uuid="team-1",
            binding=binding,
            prompt_ref="prompt",
            prompt_digest="0" * 64,
            input_text='{"data": "val"}',
            system_text="System instructions",
            json_schema_ref="schema",
            json_schema_digest="0" * 64,
        )
    )

    body = captured["body"]
    assert body["model"] == SPARK_QWEN_GENERATE_MODEL_KEY
    assert body["messages"] == [
        {"role": "system", "content": "System instructions"},
        {"role": "user", "content": '{"data": "val"}'},
    ]
    assert body["response_format"]["type"] == "json_schema"
    assert body["response_format"]["json_schema"]["name"] == "schema"
    assert isinstance(body["response_format"]["json_schema"]["schema"], dict)
    assert "max_tokens" not in body
    assert body["chat_template_kwargs"] == {"enable_thinking": False}
    assert response.text == '{"summary": "clean content"}'
