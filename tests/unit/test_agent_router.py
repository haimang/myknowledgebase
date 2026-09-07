"""NS1 provider routing, fallback, and bounded concurrency contracts."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass

import pytest

from src.contracts.common.errors import MkbError
from src.runtime.inference.agent_router import AgentCliRouter
from src.runtime.inference.claude_cli import ClaudeCliRequest, ClaudeCliResult


def _request() -> ClaudeCliRequest:
    return ClaudeCliRequest(
        user_prompt="material",
        system_prompt_file="prompt.md",
        role="markdown",
    )


@dataclass
class _FakeProvider:
    provider: str
    result: ClaudeCliResult | None = None
    error: MkbError | None = None
    calls: int = 0

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        self.calls += 1
        if self.error is not None:
            raise self.error
        assert self.result is not None
        return self.result


@pytest.mark.asyncio
async def test_claude_is_primary_and_receives_minimax_model() -> None:
    provider = _FakeProvider("claude", ClaudeCliResult("ok", None, 0))
    router = AgentCliRouter({"claude": provider})

    result = await router.run(_request())

    assert result.provider == "claude"
    assert result.model == "minimax-m3"
    assert provider.calls == 1


@pytest.mark.asyncio
async def test_capacity_or_transport_error_falls_through_to_rotating_agents() -> None:
    claude = _FakeProvider("claude", error=MkbError("CLAUDE_CLI_TIMEOUT", "timeout", 503))
    agy = _FakeProvider("agy", error=MkbError("INFERENCE_BACKPRESSURE", "full", 503))
    cursor = _FakeProvider("cursor-agent", ClaudeCliResult("cursor", None, 0))
    grok = _FakeProvider("grok", ClaudeCliResult("grok", None, 0))
    router = AgentCliRouter(
        {"claude": claude, "agy": agy, "cursor-agent": cursor, "grok": grok},
        provider_plan=("claude", "agy", "cursor-agent", "grok"),
    )

    first = await router.run(_request())
    second = await router.run(_request())

    assert first.provider == "cursor-agent"
    assert first.fallback_reason == "INFERENCE_BACKPRESSURE"
    assert second.provider == "grok"
    assert cursor.calls == 1
    assert grok.calls == 1


@pytest.mark.asyncio
async def test_schema_error_does_not_switch_provider() -> None:
    claude = _FakeProvider(
        "claude",
        error=MkbError("CLAUDE_CLI_OUTPUT_INVALID", "bad output", 502),
    )
    agy = _FakeProvider("agy", ClaudeCliResult("agy", None, 0))
    router = AgentCliRouter({"claude": claude, "agy": agy})

    with pytest.raises(MkbError) as raised:
        await router.run(_request())

    assert raised.value.code == "CLAUDE_CLI_OUTPUT_INVALID"
    assert agy.calls == 0


@pytest.mark.asyncio
async def test_global_cli_gate_is_eight_and_provider_gate_is_bounded() -> None:
    started = asyncio.Event()
    release = asyncio.Event()

    class BlockingProvider:
        provider = "claude"

        async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
            del request
            started.set()
            await release.wait()
            return ClaudeCliResult("ok", None, 0)

    router = AgentCliRouter(
        {"claude": BlockingProvider()},
        provider_limits={"claude": 3, "agy": 2, "cursor-agent": 3, "grok": 3},
    )
    tasks = [asyncio.create_task(router.run(_request())) for _ in range(4)]
    await started.wait()
    await asyncio.sleep(0)

    assert router.gate.in_flight("claude") == 3
    release.set()
    await asyncio.gather(*tasks[:3])
    with pytest.raises(MkbError) as fourth:
        await tasks[3]
    assert fourth.value.code in {"INFERENCE_BACKPRESSURE", "CLAUDE_CLI_TRANSPORT_FAILED"}
