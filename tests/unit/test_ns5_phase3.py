"""NS5 Phase 3: inference lane and evidence (T20–T29 subset)."""

from __future__ import annotations

import asyncio
import os

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.runtime.models import ProcessCommand
from src.runtime.inference.claude_cli import (
    ClaudeCliCleanLanguageModel,
    SubprocessClaudeCli,
    prompt_transport_for,
)
from src.runtime.intake.core import IntakeCoreMixin
from src.runtime.intake.generation_construct import IntakeGenerationConstructMixin
from src.runtime.intake.generation_evidence import (
    record_pending_generation_evidence,
    take_pending_generation_evidence,
)
from src.runtime.workflow.dispatch import OVER_BUDGET_PROCESS_KEYS


def _command(**kwargs: object) -> ProcessCommand:
    digest = "a" * 64
    payload = dict(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        process_key="lsrag.construct",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:in",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:cfg",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )
    payload.update(kwargs)
    return ProcessCommand(**payload)  # type: ignore[arg-type]


def test_prompt_transport_is_always_stdin() -> None:
    assert prompt_transport_for("short") == "stdin"
    argv = SubprocessClaudeCli(executable="claude")._env
    assert "MKB_INTERNAL_TOKEN" not in argv


def test_cli_child_env_strips_mkb(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MKB_INTERNAL_TOKEN", "secret-token")
    monkeypatch.setenv("PATH", os.environ.get("PATH", "/bin"))
    cli = SubprocessClaudeCli(executable="claude")
    assert "MKB_INTERNAL_TOKEN" not in cli._env


def test_salvage_allows_urgent_local() -> None:
    mixin = IntakeGenerationConstructMixin()
    mixin._claude_cli = object()  # type: ignore[attr-defined]
    exc = MkbError("INFERENCE_TRANSPORT_RETRYABLE", "retry", 503)
    urgent = _command(dispatch_pool="local-inference", task_priority="urgent")
    low = _command(dispatch_pool="local-inference", task_priority="low")
    assert mixin._can_salvage_local_inference(exc, urgent) is True
    assert mixin._can_salvage_local_inference(exc, low) is False


def test_ns1_prompt_file_requires_state() -> None:
    mixin = IntakeGenerationConstructMixin()
    mixin._prompt_root = __import__("pathlib").Path("data/prompts")  # type: ignore[attr-defined]
    with pytest.raises(MkbError, match="PROMPT_NOT_REGISTERED"):
        mixin._ns1_prompt_file(
            "json/promptB.json.generic.v1.md",
            error_code="PROMPT_HASH_MISMATCH",
            state=None,
            role="json",
        )


def test_exhausted_is_process_retryable() -> None:
    assert "INFERENCE_TRANSPORT_EXHAUSTED" in IntakeCoreMixin._RECOVERABLE_ERROR_CODES
    assert "INFERENCE_BACKPRESSURE" in IntakeCoreMixin._RECOVERABLE_ERROR_CODES


def test_construct_is_over_budget_key() -> None:
    assert "lsrag.construct" in OVER_BUDGET_PROCESS_KEYS


def test_evidence_is_keyed_by_process_uuid() -> None:
    first = uuid7()
    second = uuid7()
    record_pending_generation_evidence(
        invocation={"status": "failed", "error_code": "one", "input_digest": "a" * 64},
        process_uuid=first,
    )
    record_pending_generation_evidence(
        invocation={"status": "failed", "error_code": "two", "input_digest": "a" * 64},
        process_uuid=second,
    )
    items = take_pending_generation_evidence(second)
    assert items[0]["invocation"]["error_code"] == "two"
    leftover = take_pending_generation_evidence(first)
    assert leftover[0]["invocation"]["error_code"] == "one"


@pytest.mark.asyncio
async def test_non_text_blob_is_rejected() -> None:
    model = ClaudeCliCleanLanguageModel(cli=None, system_prompt_file="p.md")  # type: ignore[arg-type]
    with pytest.raises(MkbError, match="CLEAN_MEDIA_UNSUPPORTED"):
        await model.complete(prompt="x", blob=b"%PDF-1.4", media_type="application/pdf")


@pytest.mark.asyncio
async def test_cli_max_one_second_run_is_backpressure() -> None:
    from src.runtime.inference.claude_cli import ClaudeCliRequest, ClaudeCliResult, RecordingStub
    from src.runtime.inference.facade import ConcurrencyGate

    gate = ConcurrencyGate(4, capability_limits={"cli": 1})
    started = asyncio.Event()
    release = asyncio.Event()

    async def slow(_request: ClaudeCliRequest) -> ClaudeCliResult:
        started.set()
        await release.wait()
        return ClaudeCliResult("ok", None, 0)

    stub = RecordingStub(response_factory=slow, concurrency_gate=gate)
    request = ClaudeCliRequest(user_prompt="hello", system_prompt_file="p.md", role="markdown")
    first = asyncio.create_task(stub.run(request))
    await started.wait()
    with pytest.raises(MkbError, match="INFERENCE_BACKPRESSURE"):
        await stub.run(request)
    release.set()
    await first


@pytest.mark.asyncio
async def test_shared_dispatch_caps_embed_gate_fills_together() -> None:
    from src.contracts.inference.models import EmbeddingRequest, EmbeddingResponse, InferenceBinding
    from src.runtime.inference.facade import ConcurrencyGate, InferenceFacade
    from src.runtime.workflow.dispatch import DispatchCaps

    class _HoldingAdapter:
        adapter_kind = "local_vllm"

        def __init__(self) -> None:
            self.entered = asyncio.Event()
            self.release = asyncio.Event()

        async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
            self.entered.set()
            await self.release.wait()
            return EmbeddingResponse(
                vectors=[[0.0] * 4],
                model_key=request.binding.model_key,
                model_version=request.binding.model_version,
                dimension=4,
            )

        async def probe(self) -> bool:
            return True

    caps = DispatchCaps(embed_running=1)
    gate = ConcurrencyGate(4, capability_limits={"embed": caps.embed_running})
    adapter = _HoldingAdapter()
    facade = InferenceFacade(adapter, dispatch_caps=caps, gate=gate)  # type: ignore[arg-type]
    assert facade.dispatch_caps is caps
    binding = InferenceBinding(
        capability_key="embed",
        adapter_kind="local_vllm",
        model_key="m",
        model_version="v1",
        binding_digest="a" * 64,
    )
    request = EmbeddingRequest(team_uuid="t", binding=binding, texts=["q"], expected_dimension=4)
    first = asyncio.create_task(facade.embed(request))
    await adapter.entered.wait()
    assert gate.in_flight("embed") == caps.embed_running
    with pytest.raises(MkbError, match="INFERENCE_BACKPRESSURE"):
        await facade.embed(request)
    adapter.release.set()
    await first


def test_coerce_rejects_multiple_top_level_objects() -> None:
    from src.runtime.inference.facade import coerce_json_object_text

    assert coerce_json_object_text('prefix {"ok": true} suffix') == '{"ok": true}'
    with pytest.raises(MkbError, match="INFERENCE_VALIDATION_STRUCTURED"):
        coerce_json_object_text('see {"a": 1} or {"b": 2}')


@pytest.mark.asyncio
async def test_vllm_probe_rejects_non_2xx_and_wrong_model() -> None:
    import httpx

    from src.llm_adapters.local_vllm import LocalVllmAdapter

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path.endswith("/v1/models") and request.url.params.get("redirect") == "1":
            return httpx.Response(302, headers={"location": "/elsewhere"})
        if "wrong" in str(request.url):
            return httpx.Response(200, json={"data": [{"id": "other-model"}]})
        return httpx.Response(200, json={"data": [{"id": "exact-model"}]})

    redirect = LocalVllmAdapter("http://127.0.0.1:668", transport=httpx.MockTransport(lambda r: httpx.Response(302)))
    assert await redirect.probe(model_key="exact-model") is False
    ok = LocalVllmAdapter("http://127.0.0.1:668", transport=httpx.MockTransport(handler))
    assert await ok.probe(model_key="exact-model") is True
    assert await ok.probe(model_key="missing-model") is False
