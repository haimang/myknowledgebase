"""NS6-T17–T20: salvage occupancy, evidence isolation, lease, CLI bounds."""

from __future__ import annotations

import asyncio
import stat
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.contracts.inference.models import GenerateRequest, InferenceBinding
from src.runtime.inference.claude_cli import ClaudeCliRequest, SubprocessClaudeCli, _cli_child_env, _terminate_process
from src.runtime.inference.facade import ConcurrencyGate, InferenceFacade
from src.runtime.intake.generation_construct import (
    _API_INFERENCE_SALVAGE_CODES,
    IntakeGenerationConstructMixin,
)
from src.runtime.intake.generation_evidence import (
    record_pending_generation_evidence,
    take_pending_generation_evidence,
    write_pending_generation_evidence_tx,
)
from tests.unit.test_ns5_phase3 import _command


@pytest.mark.asyncio
async def test_salvage_occupies_ni_and_skips_backpressure(tmp_path: Path) -> None:
    assert "INFERENCE_BACKPRESSURE" not in _API_INFERENCE_SALVAGE_CODES
    mixin = IntakeGenerationConstructMixin()
    gate = ConcurrencyGate(1, capability_limits={"cli": 1})
    hang = tmp_path / "echo"
    hang.write_text("#!/bin/sh\nprintf '{}'\n", encoding="utf-8")
    hang.chmod(hang.stat().st_mode | stat.S_IEXEC)
    cli = SubprocessClaudeCli(executable=str(hang), concurrency_gate=gate)
    mixin._claude_cli = cli  # type: ignore[attr-defined]
    urgent = _command(dispatch_pool="local-inference", task_priority="urgent")
    assert mixin._can_salvage_local_inference(MkbError("INFERENCE_BACKPRESSURE", "full", 503), urgent) is False
    assert mixin._can_salvage_local_inference(MkbError("INFERENCE_TRANSPORT_RETRYABLE", "retry", 503), urgent) is True
    held = await gate.try_acquire("cli")
    assert held is not None
    assert gate.in_flight("cli") == 1
    with pytest.raises(MkbError, match="INFERENCE_BACKPRESSURE"):
        await cli.run(ClaudeCliRequest(user_prompt="hello", system_prompt_file="p.md", timeout_seconds=1))
    salvage_calls = {"n": 0}

    async def occupy_cli(**kwargs: object) -> tuple[dict[str, object], dict[str, object]]:
        del kwargs
        salvage_calls["n"] += 1
        await cli.run(ClaudeCliRequest(user_prompt="hello", system_prompt_file="p.md", timeout_seconds=1))
        return {}, {}

    mixin._cli_layered_summary = occupy_cli  # type: ignore[method-assign]
    with pytest.raises(MkbError, match="INFERENCE_BACKPRESSURE"):
        await mixin._salvage_summary_via_cli(
            layered_candidate={"ok": True},
            profile=(0,),
            state=None,
            salvage_error=MkbError("INFERENCE_TRANSPORT_RETRYABLE", "retry", 503),
        )
    assert salvage_calls["n"] == 1
    await gate.release(held)


@pytest.mark.asyncio
async def test_omitted_process_uuid_is_not_flushed_to_other_process() -> None:
    process_a = uuid7()
    process_b = uuid7()
    record_pending_generation_evidence(
        invocation={"status": "failed", "error_code": "orphan", "input_digest": "a" * 64},
        process_uuid=None,
    )
    record_pending_generation_evidence(
        invocation={"status": "failed", "error_code": "b-only", "input_digest": "a" * 64},
        process_uuid=process_b,
    )
    assert take_pending_generation_evidence(process_a) == []
    taken_b = take_pending_generation_evidence(process_b)
    assert len(taken_b) == 1
    assert taken_b[0]["invocation"]["error_code"] == "b-only"
    record_pending_generation_evidence(
        invocation={"status": "failed", "error_code": "still-orphan", "input_digest": "a" * 64}
    )
    process = {
        "team_uuid": uuid7(),
        "execution_uuid": uuid7(),
        "process_uuid": process_b,
        "task_uuid": uuid7(),
        "trace_uuid": uuid7(),
    }

    class _Tx:
        def __init__(self) -> None:
            self.writes: list[tuple[str, tuple[object, ...]]] = []

        async def execute(self, sql: str, params: tuple[object, ...] = ()) -> None:
            self.writes.append((sql, params))

    tx = _Tx()
    await write_pending_generation_evidence_tx(tx, process)
    assert tx.writes == []


@pytest.mark.asyncio
async def test_retry_cancel_and_full_gate_do_not_double_release() -> None:
    class _RetryAdapter:
        adapter_kind = "local_vllm"

        async def generate(self, request: GenerateRequest) -> object:
            del request
            raise MkbError("INFERENCE_TRANSPORT_RETRYABLE", "retry", 503)

    request = GenerateRequest(
        team_uuid="team-a",
        binding=InferenceBinding(
            capability_key="text_generate",
            adapter_kind="local_vllm",
            model_key="generator",
            model_version="v1",
            binding_digest="a" * 64,
        ),
        prompt_ref="mkbtest:prompt",
        prompt_digest="a" * 64,
        input_text="hello",
    )
    facade = InferenceFacade(_RetryAdapter(), max_attempts=3, initial_delay_seconds=30, max_delay_seconds=30)
    task = asyncio.create_task(facade.generate(request))
    await asyncio.sleep(0.05)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    async def instant_sleep(_delay: float) -> None:
        return None

    gate = ConcurrencyGate(1, capability_limits={"text_generate": 1})
    held = await gate.try_acquire("text_generate")
    assert held is not None
    full = InferenceFacade(
        _RetryAdapter(),
        max_attempts=2,
        initial_delay_seconds=0,
        max_delay_seconds=0,
        gate=gate,
        sleep=instant_sleep,
    )
    with pytest.raises(MkbError, match="INFERENCE_BACKPRESSURE"):
        await full.generate(request)
    await gate.release(held)


@pytest.mark.asyncio
async def test_cli_env_allowlist_stdout_cap_and_cancel_sets_returncode(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AWS_SECRET_ACCESS_KEY", "aws-secret")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "claude-ok")
    env = _cli_child_env(None)
    assert "AWS_SECRET_ACCESS_KEY" not in env
    assert env["ANTHROPIC_API_KEY"] == "claude-ok"

    writer = tmp_path / "writer"
    writer.write_text("#!/bin/sh\ndd if=/dev/zero bs=1048576 count=9 2>/dev/null\n", encoding="utf-8")
    writer.chmod(writer.stat().st_mode | stat.S_IEXEC)
    cli = SubprocessClaudeCli(executable=str(writer))
    with pytest.raises(MkbError, match="CLAUDE_CLI_OUTPUT_INVALID"):
        await cli.run(ClaudeCliRequest(user_prompt="hello", system_prompt_file="p.md", timeout_seconds=5))

    hang = tmp_path / "hang"
    hang.write_text("#!/bin/sh\nexec sleep 60\n", encoding="utf-8")
    hang.chmod(hang.stat().st_mode | stat.S_IEXEC)
    process = await asyncio.create_subprocess_exec(
        str(hang), stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
    )
    terminate = asyncio.create_task(_terminate_process(process))
    await asyncio.sleep(0)
    terminate.cancel()
    try:
        await terminate
    except asyncio.CancelledError:
        await asyncio.shield(_terminate_process(process))
    assert process.returncode is not None
