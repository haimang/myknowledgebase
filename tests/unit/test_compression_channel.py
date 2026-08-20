"""Intake compression channel: Claude -p vs Local vLLM generate."""

from __future__ import annotations

import hashlib
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest
from pydantic import ValidationError

from src.contracts.api.models import IntakeIngestPayload
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.inference.models import (
    GenerateRequest,
    InferenceBinding,
    StructuredGenerateRequest,
)
from src.llm_adapters.local_vllm import LocalVllmAdapter
from src.runtime.inference.claude_cli import DeterministicNs1Stub
from src.runtime.inference.facade import coerce_json_object_text
from src.runtime.intake.pipeline import IntakePipeline
from src.services.registry import (
    DEFAULT_BINDINGS,
    SPARK_LIGHTNING_GENERATE_MODEL_KEY,
    SPARK_QWEN_GENERATE_MODEL_KEY,
    default_enabled_inference_bindings,
)


def _payload(**extra: object) -> dict[str, object]:
    value: dict[str, object] = {
        "source": {
            "source_kind": "inline_payload",
            "external_key": "compression-channel",
            "content": "source text",
        },
        "json_prompt_id": "promptB.json.generic",
    }
    value.update(extra)
    return value


def _binding() -> InferenceBinding:
    return InferenceBinding(
        capability_key="structured_generate",
        adapter_kind="local_vllm",
        model_key=SPARK_QWEN_GENERATE_MODEL_KEY,
        model_version="v1",
        binding_digest=stable_digest(
            {
                "capability": "structured_generate",
                "adapter_kind": "local_vllm",
                "model_key": SPARK_QWEN_GENERATE_MODEL_KEY,
                "model_version": "v1",
            }
        ),
    )


def test_payload_defaults_to_non_interactive_and_rejects_unknown_channel() -> None:
    omitted = IntakeIngestPayload.model_validate(_payload())
    assert omitted.compression_channel is None
    assert IntakeIngestPayload.model_validate(_payload(compression_channel="non-interactive")).compression_channel == (
        "non-interactive"
    )
    assert IntakeIngestPayload.model_validate(_payload(compression_channel="local-inference")).compression_channel == (
        "local-inference"
    )
    with pytest.raises(ValidationError):
        IntakeIngestPayload.model_validate(_payload(compression_channel="api-inference"))
    with pytest.raises(ValidationError):
        IntakeIngestPayload.model_validate(_payload(compression_channel="cloud-inference"))
    with pytest.raises(ValidationError):
        IntakeIngestPayload.model_validate(_payload(compression_channel="spark"))
    with pytest.raises(ValidationError):
        IntakeIngestPayload.model_validate(_payload(compression_channel="claude"))


def test_summary_transport_uses_dispatch_pool_as_ssot() -> None:
    from src.contracts.common.ids import uuid7
    from src.contracts.runtime.models import ProcessCommand

    pipeline = IntakePipeline(None, None, None, claude_cli=object())  # type: ignore[arg-type]
    assert pipeline._summary_transport({"payload": {"compression_channel": "non-interactive"}}) == "claude_cli"
    local_command = ProcessCommand(
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
        dispatch_pool="non-interactive",
        task_priority="normal",
    )
    assert pipeline._compression_channel({"payload": {}}, local_command) == "non-interactive"


def test_summary_transport_uses_spark_only_when_local_inference_is_live() -> None:
    offline = IntakePipeline(None, None, None, claude_cli=object())  # type: ignore[arg-type]
    with pytest.raises(MkbError) as rejected:
        offline._summary_transport({"payload": {"compression_channel": "local-inference"}})
    assert rejected.value.code == "COMPRESSION_CHANNEL_UNAVAILABLE"

    live = IntakePipeline(None, None, None, inference=object(), live_inference=True)  # type: ignore[arg-type]
    assert live._summary_transport({"payload": {"compression_channel": "local-inference"}}) == "api_inference"
    # A live facade must not steal the default Claude path.
    live_with_cli = IntakePipeline(
        None,
        None,
        None,
        inference=object(),
        claude_cli=object(),
        live_inference=True,
    )  # type: ignore[arg-type]
    assert live_with_cli._summary_transport({"payload": {"compression_channel": "non-interactive"}}) == "claude_cli"


def test_snapshot_rejects_explicit_local_inference_when_live_inference_is_off() -> None:
    from src.services.config_snapshots import ConfigSnapshotService

    service = object.__new__(ConfigSnapshotService)
    service.settings = SimpleNamespace(live_inference=False)
    request = SimpleNamespace(
        payload=IntakeIngestPayload.model_validate(_payload(compression_channel="local-inference")),
        priority="normal",
    )
    assert ConfigSnapshotService._resolve_compression_channel(request) == ("local-inference", "explicit")
    with pytest.raises(MkbError) as rejected:
        service._require_compression_channel(request)
    assert rejected.value.code == "COMPRESSION_CHANNEL_UNAVAILABLE"
    service.settings = SimpleNamespace(live_inference=True)
    assert service._require_compression_channel(request) == ("local-inference", "explicit")


@pytest.mark.asyncio
async def test_local_adapter_sends_system_prompt_and_json_object_for_qwen() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = __import__("json").loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": SPARK_QWEN_GENERATE_MODEL_KEY,
                "choices": [
                    {
                        "message": {
                            "reasoning": "internal scratch that must not enter the result",
                            "content": '{"ok":true}',
                        }
                    }
                ],
                "usage": {"prompt_tokens": 4, "completion_tokens": 2, "total_tokens": 6},
            },
        )

    adapter = LocalVllmAdapter("https://models.example:8443/", transport=httpx.MockTransport(handler))
    response = await adapter.generate(
        StructuredGenerateRequest(
            team_uuid="team-a",
            binding=_binding(),
            prompt_ref="promptC.documentation.default.v1",
            prompt_digest="a" * 64,
            input_text='{"layered_content":[]}',
            system_text="You are the summarizer worker.",
            json_schema_ref="lsrag.layered_content.default@v1",
            json_schema_digest="b" * 64,
        )
    )

    assert captured["url"] == "https://models.example:8443/v1/chat/completions"
    body = captured["body"]
    format_block = body.pop("response_format")
    assert format_block["type"] == "json_schema"
    assert format_block["json_schema"]["name"] == "lsrag.layered_content.default@v1"
    assert format_block["json_schema"]["schema"]["type"] == "object"
    assert body == {
        "model": SPARK_QWEN_GENERATE_MODEL_KEY,
        "messages": [
            {"role": "system", "content": "You are the summarizer worker."},
            {"role": "user", "content": '{"layered_content":[]}'},
        ],
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    assert "max_tokens" not in captured["body"]
    assert captured["body"]["chat_template_kwargs"] == {"enable_thinking": False}
    assert response.model_key == SPARK_QWEN_GENERATE_MODEL_KEY
    assert response.text == '{"ok":true}'


def test_adapter_keeps_content_and_drops_reasoning() -> None:
    from src.llm_adapters.local_vllm import LocalVllmAdapter

    text = LocalVllmAdapter._completion_content(
        {
            "choices": [
                {
                    "message": {
                        "reasoning": "do not use this scratch",
                        "content": '{"ok":true}',
                    }
                }
            ]
        }
    )
    assert text == '{"ok":true}'
    with pytest.raises(MkbError) as rejected:
        LocalVllmAdapter._completion_content({"choices": [{"message": {"reasoning": "only thinking", "content": None}}]})
    assert rejected.value.code == "INFERENCE_VALIDATION_RESPONSE"


def test_plain_generate_omits_json_response_format() -> None:
    request = GenerateRequest(
        team_uuid="team-a",
        binding=_binding(),
        prompt_ref="prompt",
        prompt_digest="a" * 64,
        input_text="hello",
    )
    assert request.system_text is None


def test_coerce_json_object_text_strips_fences() -> None:
    assert coerce_json_object_text('```json\n{"ok": true}\n```') == '{"ok": true}'
    assert coerce_json_object_text('prefix {"ok": true} suffix') == '{"ok": true}'


def test_local_inference_errors_are_salvageable_only_with_cli() -> None:
    bare = IntakePipeline(None, None, None, inference=object(), live_inference=True)  # type: ignore[arg-type]
    with_cli = IntakePipeline(
        None,
        None,
        None,
        inference=object(),
        claude_cli=object(),
        live_inference=True,
    )  # type: ignore[arg-type]
    from src.contracts.common.ids import uuid7
    from src.contracts.runtime.models import ProcessCommand

    empty = MkbError("INFERENCE_VALIDATION_RESPONSE", "empty content", 502)
    command = ProcessCommand(
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
        dispatch_pool="local-inference",
        task_priority="normal",
    )
    assert bare._can_salvage_local_inference(empty, command) is False
    assert with_cli._can_salvage_local_inference(empty, command) is True
    assert with_cli._can_salvage_local_inference(MkbError("PROMPT_HASH_MISMATCH", "drift", 503), command) is False
    assert with_cli._can_salvage_local_inference(MkbError("CONSTRUCT_KERNEL_SUMMARY_INVALID", "bad json", 422), command) is True
    low_command = command.model_copy(update={"task_priority": "low"})
    assert with_cli._can_salvage_local_inference(empty, low_command) is False


@pytest.mark.asyncio
async def test_invalid_local_inference_result_salvages_once_via_claude_cli() -> None:
    from src.contracts.common.ids import uuid7
    from src.services.lsrag_compiler import LsragContractCompiler

    cli = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, inference=object(), claude_cli=cli, live_inference=True)  # type: ignore[arg-type]
    live_calls = 0

    async def boom(_command, *, layered_candidate):
        nonlocal live_calls
        live_calls += 1
        del layered_candidate
        raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Local inference content was empty", 502)

    pipeline._live_layered_summary_generate = boom  # type: ignore[method-assign]
    compiler = LsragContractCompiler()
    clean = "salvage source"
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
    command = SimpleNamespace(dispatch_pool="local-inference", task_priority="normal")
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

    completed, summaries, invocations, cli_receipt = await pipeline._complete_construct_summaries(
        command,  # type: ignore[arg-type]
        state,
        compiler=compiler,
        projection=projection,
        accepted_layered_candidate=accepted,
        profile=(0,),
    )

    assert live_calls == 1
    assert [request.role for request in cli.requests] == ["summarizer"]
    assert invocations == []
    assert cli_receipt is not None
    assert cli_receipt["transport"] == "claude_cli"
    assert cli_receipt["compression_channel"] == "non-interactive"
    assert cli_receipt["salvage_from"] == "local-inference"
    assert cli_receipt["salvage_error_code"] == "INFERENCE_VALIDATION_RESPONSE"
    assert completed["layered_content"][0]["llm_summary"]["body"]
    assert summaries


@pytest.mark.asyncio
async def test_explicit_channel_override_writes_security_audit(tmp_path: Path) -> None:
    # NS2-T38: explicit compression_channel must write an allowed security audit
    import json

    from src.contracts.common.ids import uuid7
    from src.contracts.common.time import utc_now
    from src.persistence.sqlite_port import SqlitePersistence
    from src.services.config_snapshots import ConfigSnapshotService
    from src.services.events import SecurityAuditWriter

    persistence = SqlitePersistence(tmp_path / "audit.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    team_uuid = uuid7()
    task_uuid = uuid7()
    trace_uuid = uuid7()
    now = utc_now()
    service = object.__new__(ConfigSnapshotService)
    service.security_audit = SecurityAuditWriter()
    request = SimpleNamespace(
        payload=IntakeIngestPayload.model_validate(_payload(compression_channel="non-interactive")),
        priority="low",
        team_uuid=team_uuid,
        task_uuid=task_uuid,
        trace_uuid=trace_uuid,
    )
    try:
        async with persistence.transaction() as tx:
            await tx.execute(
                "INSERT INTO mkb_teams (team_uuid, name, creation_fingerprint, created_at, updated_at) "
                "VALUES (?, 'audit', ?, ?, ?)",
                (team_uuid, "d" * 64, now, now),
            )
            await service.audit_explicit_channel(tx, request)  # type: ignore[arg-type]
            row = await tx.fetchone(
                "SELECT action, outcome, payload_json FROM mkb_security_audit_events WHERE target_uuid=?",
                (task_uuid,),
            )
        assert row is not None
        assert row["action"] == "config.compression_channel_override"
        assert row["outcome"] == "allowed"
        payload = json.loads(row["payload_json"])
        assert payload["channel"] == "non-interactive"
        assert payload["channel_source"] == "explicit"
        assert payload["priority"] == "low"
        assert "content" not in payload
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_kernel_rejected_local_inference_package_salvages_once() -> None:
    from src.contracts.common.ids import uuid7
    from src.services.lsrag_compiler import LsragContractCompiler

    cli = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, inference=object(), claude_cli=cli, live_inference=True)  # type: ignore[arg-type]
    compiler = LsragContractCompiler()
    clean = "kernel salvage"
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

    async def empty_summaries(_command, *, layered_candidate):
        return layered_candidate, {"status": "succeeded"}

    pipeline._live_layered_summary_generate = empty_summaries  # type: ignore[method-assign]

    async def _noop_persist(*_args, **_kwargs):
        return None

    pipeline._persist_failed_generation_invocation = _noop_persist  # type: ignore[method-assign]
    prompt = Path("data/prompts/summarizer/promptC.summarizer.v1.md")
    _completed, _summaries, invocations, cli_receipt = await pipeline._complete_construct_summaries(
        SimpleNamespace(dispatch_pool="local-inference", task_priority="normal"),  # type: ignore[arg-type]
        {
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
        },
        compiler=compiler,
        projection=projection,
        accepted_layered_candidate=accepted,
        profile=(0,),
    )
    assert invocations == []
    assert cli_receipt is not None
    assert cli_receipt["salvage_error_code"] == "STRUCTURE_SUMMARY_INVALID"
    assert [request.role for request in cli.requests] == ["summarizer"]


@pytest.mark.asyncio
async def test_local_inference_without_cli_does_not_invent_a_second_channel() -> None:
    pipeline = IntakePipeline(None, None, None, inference=object(), live_inference=True)  # type: ignore[arg-type]

    async def boom(_command, *, layered_candidate):
        del layered_candidate
        raise MkbError("INFERENCE_VALIDATION_STRUCTURED", "not json", 502)

    pipeline._live_layered_summary_generate = boom  # type: ignore[method-assign]
    from src.contracts.common.ids import uuid7
    from src.services.lsrag_compiler import LsragContractCompiler

    compiler = LsragContractCompiler()
    accepted = {
        "context_meta": {},
        "layered_content": [
            {
                "block_id": 0,
                "granularity": 0,
                "original_content": {"title": None, "body": "x"},
                "llm_summary": {"title": None, "body": None},
            }
        ],
    }
    _structure, projection = compiler.adopt_layered_json(
        clean_text="x",
        layered_json=accepted,
        generation_artifact_uuid=uuid7(),
        projection_generation_artifact_uuid=uuid7(),
        clean_artifact_uuid=uuid7(),
        granularity_set=(0,),
    )
    with pytest.raises(MkbError) as rejected:
        await pipeline._complete_construct_summaries(
            SimpleNamespace(),  # type: ignore[arg-type]
            {"payload": {"compression_channel": "local-inference"}},
            compiler=compiler,
            projection=projection,
            accepted_layered_candidate=accepted,
            profile=(0,),
        )
    assert rejected.value.code == "INFERENCE_VALIDATION_STRUCTURED"


@pytest.mark.asyncio
async def test_successful_local_inference_does_not_call_cli() -> None:
    from src.contracts.common.ids import uuid7
    from src.services.lsrag_compiler import LsragContractCompiler

    cli = DeterministicNs1Stub()
    pipeline = IntakePipeline(None, None, None, inference=object(), claude_cli=cli, live_inference=True)  # type: ignore[arg-type]
    compiler = LsragContractCompiler()
    clean = "ok source"
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

    async def ok(_command, *, layered_candidate):
        package = {
            **layered_candidate,
            "layered_content": [
                {
                    **block,
                    "llm_summary": {"title": None, "body": block["original_content"]["body"]},
                }
                for block in layered_candidate["layered_content"]
            ],
        }
        return package, {"status": "succeeded"}

    pipeline._live_layered_summary_generate = ok  # type: ignore[method-assign]
    completed, _summaries, invocations, cli_receipt = await pipeline._complete_construct_summaries(
        SimpleNamespace(),  # type: ignore[arg-type]
        {"payload": {"compression_channel": "local-inference"}},
        compiler=compiler,
        projection=projection,
        accepted_layered_candidate=accepted,
        profile=(0,),
    )
    assert cli.requests == []
    assert cli_receipt is None
    assert invocations[0]["transport"] == "api_inference"
    assert completed["layered_content"][0]["llm_summary"]["body"] == clean


@pytest.mark.asyncio
async def test_bootstrap_registers_qwen_as_winner_generate_model(tmp_path: Path) -> None:
    from src.persistence.sqlite_port import SqlitePersistence
    from src.services.registry import RegistryService

    persistence = SqlitePersistence(tmp_path / "qwen.sqlite3", Path("src/persistence/migrations"))
    registry = RegistryService(persistence, Path("data/prompts"))
    try:
        await persistence.migrate()
        await registry.bootstrap()
        async with persistence.transaction() as tx:
            model = await tx.fetchone(
                "SELECT modality,status FROM mkb_model_catalog WHERE model_key=? AND model_version='v1'",
                (SPARK_QWEN_GENERATE_MODEL_KEY,),
            )
            bindings = await tx.fetchall(
                "SELECT capability_key,priority,enabled FROM mkb_adapter_bindings "
                "WHERE model_key=? AND team_uuid IS NULL ORDER BY capability_key",
                (SPARK_QWEN_GENERATE_MODEL_KEY,),
            )
        assert model is not None
        assert model["modality"] == "generate"
        assert model["status"] == "active"
        assert [(row["capability_key"], row["priority"], row["enabled"]) for row in bindings] == [
            ("structured_generate", 5, 1),
            ("text_generate", 5, 1),
        ]
        winners = await registry.active_inference_bindings()
        generate = {item.capability_key: item.model_key for item in winners}
        assert generate["structured_generate"] == SPARK_QWEN_GENERATE_MODEL_KEY
        assert generate["text_generate"] == SPARK_QWEN_GENERATE_MODEL_KEY
    finally:
        await persistence.close()


def test_default_generate_binding_is_qwen_winner() -> None:
    generate = {
        (binding.capability_key, binding.model_key)
        for binding in default_enabled_inference_bindings()
        if binding.capability_key in {"structured_generate", "text_generate"}
    }
    assert generate == {
        ("structured_generate", SPARK_LIGHTNING_GENERATE_MODEL_KEY),
        ("text_generate", SPARK_LIGHTNING_GENERATE_MODEL_KEY),
        ("structured_generate", SPARK_QWEN_GENERATE_MODEL_KEY),
        ("text_generate", SPARK_QWEN_GENERATE_MODEL_KEY),
    }
    winners = {
        capability: model
        for capability, model, _version, priority, enabled in DEFAULT_BINDINGS
        if capability in {"structured_generate", "text_generate"} and enabled and priority == 5
    }
    assert winners == {
        "structured_generate": SPARK_QWEN_GENERATE_MODEL_KEY,
        "text_generate": SPARK_QWEN_GENERATE_MODEL_KEY,
    }
    spares = {
        (capability, model)
        for capability, model, _version, priority, enabled in DEFAULT_BINDINGS
        if capability in {"structured_generate", "text_generate"} and enabled and priority == 10
    }
    assert spares == {
        ("structured_generate", SPARK_LIGHTNING_GENERATE_MODEL_KEY),
        ("text_generate", SPARK_LIGHTNING_GENERATE_MODEL_KEY),
    }
