"""Provider-neutral NS1 CLI routing with bounded fallback and concurrency.

The embedding path remains in ``InferenceFacade``.  This module owns only
text/structured generation transports used by the A/B/C and clean workers.
Every provider receives the same typed request, bounded stdin/stdout contract,
and an independent provider identity in the returned receipt.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import replace
from pathlib import Path
from typing import Protocol

from src.contracts.common.errors import MkbError
from src.runtime.inference.claude_cli import (
    CLAUDE_CLI_STDOUT_LIMIT_BYTES,
    ClaudeCliRequest,
    ClaudeCliResult,
    _bounded_communicate,
    _cli_child_env,
    _decode_plain_stdout,
    _decode_structured_stdout,
    _digest_text,
    _terminate_process,
    prompt_transport_for,
)
from src.runtime.inference.facade import ConcurrencyGate

AGENT_PROVIDERS = ("claude", "agy", "cursor-agent", "grok")
PRIMARY_AGENT_PROVIDER = "claude"
FALLBACK_AGENT_PROVIDERS = ("cursor-agent", "grok")
FALLBACKABLE_AGENT_ERRORS = frozenset(
    {
        "INFERENCE_BACKPRESSURE",
        "INFERENCE_TRANSPORT_RETRYABLE",
        "INFERENCE_TRANSPORT_EXHAUSTED",
        "CLAUDE_CLI_TIMEOUT",
        "CLAUDE_CLI_TRANSPORT_FAILED",
    }
)


class AgentCliPort(Protocol):
    """One provider-specific generation transport."""

    provider: str

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        """Run one bounded generation request."""


def _agent_argv(
    request: ClaudeCliRequest,
    *,
    provider: str,
    executable: str,
) -> tuple[str, ...]:
    """Build a conservative argv for providers with Claude-compatible ``-p``.

    Claude's richer flags are intentionally retained for the primary provider.
    The other configured agents receive the same prompt/schema material through
    their documented ``-p``/stdin boundary, without shell interpolation or
    credential flags.
    """

    if not isinstance(request.user_prompt, str) or not request.user_prompt.strip():
        raise MkbError("CLAUDE_CLI_INPUT_INVALID", "CLI user material must be non-empty", 422)
    prompt_path = Path(request.system_prompt_file)
    if not prompt_path.name:
        raise MkbError("CLAUDE_CLI_INPUT_INVALID", "CLI system prompt file is required", 422)
    if request.timeout_seconds <= 0:
        raise MkbError("CLAUDE_CLI_INPUT_INVALID", "CLI timeout must be positive", 422)

    argv: list[str] = [executable, "-p", "--system-prompt-file", str(prompt_path)]
    if provider == "claude":
        argv.extend(("--bare", "--tools", ""))
        if request.model:
            argv.extend(("--model", request.model))
    if request.json_schema is not None:
        try:
            from src.runtime.inference.claude_cli import _cli_json_schema

            schema = json.dumps(
                _cli_json_schema(request.json_schema),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise MkbError("CLAUDE_CLI_SCHEMA_INVALID", "CLI JSON schema is not deterministic JSON", 422) from exc
        argv.extend(("--output-format", "json", "--json-schema", schema))
    return tuple(argv)


def _decode_agent_structured_stdout(
    stdout: str,
) -> tuple[str, dict[str, object] | None, str | None, Mapping[str, object] | None, bool]:
    """Accept the Claude envelope and a strict direct JSON-object response."""

    try:
        return _decode_structured_stdout(stdout)
    except MkbError as envelope_error:
        try:
            value = json.loads(stdout)
        except (TypeError, json.JSONDecodeError):
            raise envelope_error from None
        if isinstance(value, Mapping):
            projected = dict(value)
            return (
                json.dumps(projected, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                projected,
                None,
                None,
                False,
            )
        raise envelope_error


class SubprocessAgentCli:
    """Run one configured agent executable without a shell."""

    def __init__(
        self,
        *,
        provider: str,
        executable: str,
        model: str | None = None,
        env: Mapping[str, str] | None = None,
    ) -> None:
        if provider not in AGENT_PROVIDERS:
            raise ValueError("unknown NS1 agent provider")
        if not executable or any(char in executable for char in "\x00\n\r"):
            raise ValueError("agent executable must be a safe non-empty value")
        self.provider = provider
        self._executable = executable
        self._model = model
        self._env = _cli_child_env(env)

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        effective = request
        if self.provider == "claude" and not effective.model:
            effective = replace(effective, model=self._model)
        transport = prompt_transport_for(effective.user_prompt)
        argv = _agent_argv(
            effective,
            provider=self.provider,
            executable=self._executable,
        )
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE if transport == "stdin" else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env,
            )
            payload = effective.user_prompt.encode("utf-8") if transport == "stdin" else None
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                _bounded_communicate(process, payload, CLAUDE_CLI_STDOUT_LIMIT_BYTES),
                effective.timeout_seconds,
            )
        except MkbError:
            await asyncio.shield(_terminate_process(process))
            raise
        except TimeoutError as exc:
            await asyncio.shield(_terminate_process(process))
            raise MkbError("CLAUDE_CLI_TIMEOUT", "CLI invocation timed out", 503) from exc
        except asyncio.CancelledError:
            await asyncio.shield(_terminate_process(process))
            raise
        except OSError as exc:
            await asyncio.shield(_terminate_process(process))
            raise MkbError("CLAUDE_CLI_TRANSPORT_FAILED", "CLI could not be started", 503) from exc

        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = process.returncode if process.returncode is not None else -1
        if exit_code != 0:
            raise MkbError(
                "CLAUDE_CLI_TRANSPORT_FAILED",
                "CLI exited unsuccessfully",
                503,
                {"provider": self.provider, "exit_code": exit_code, "stderr_digest": _digest_text(stderr)},
            )
        try:
            if effective.structured:
                text, structured, session_id, usage, is_error = _decode_agent_structured_stdout(stdout)
                if is_error:
                    raise MkbError("CLAUDE_CLI_TRANSPORT_FAILED", "CLI reported an error", 503)
                if structured is None:
                    raise MkbError(
                        "CLAUDE_CLI_OUTPUT_INVALID",
                        "CLI structured result is not an object",
                        502,
                        {"cli_structured_kind": "missing"},
                    )
                return ClaudeCliResult(
                    text,
                    structured,
                    exit_code,
                    session_id,
                    usage,
                    is_error,
                    provider=self.provider,
                    model=effective.model,
                )
            text, session_id, usage, is_error = _decode_plain_stdout(stdout)
            if is_error:
                raise MkbError("CLAUDE_CLI_TRANSPORT_FAILED", "CLI reported an error", 503)
            if not text:
                raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "CLI returned empty text", 502)
            return ClaudeCliResult(
                text,
                None,
                exit_code,
                session_id,
                usage,
                is_error,
                provider=self.provider,
                model=effective.model,
            )
        except MkbError as exc:
            if isinstance(exc.details, dict) and "provider" not in exc.details:
                exc.details["provider"] = self.provider
            raise


class AgentCliRouter:
    """Primary/backup/fallback router with a global eight-call ceiling."""

    def __init__(
        self,
        providers: Mapping[str, AgentCliPort],
        *,
        primary_model: str = "minimax-m3",
        provider_plan: tuple[str, ...] = AGENT_PROVIDERS,
        max_concurrency: int = 8,
        provider_limits: Mapping[str, int] | None = None,
        gate: ConcurrencyGate | None = None,
        fallback_cursor: Callable[[], int] | None = None,
    ) -> None:
        if not primary_model.strip():
            raise ValueError("primary model is required")
        normalized_plan = tuple(dict.fromkeys(provider_plan))
        if not normalized_plan or any(provider not in AGENT_PROVIDERS for provider in normalized_plan):
            raise ValueError("provider plan contains an unknown provider")
        if PRIMARY_AGENT_PROVIDER not in normalized_plan:
            raise ValueError("provider plan must contain the primary Claude provider")
        self.providers = dict(providers)
        self.primary_model = primary_model
        self.provider_plan = normalized_plan
        limits = dict(provider_limits or {"claude": 3, "agy": 2, "cursor-agent": 3, "grok": 3})
        self._gate = gate or ConcurrencyGate(max_concurrency, capability_limits=limits)
        self._fallback_cursor = fallback_cursor
        self._fallback_index = 0
        self._fallback_lock = asyncio.Lock()

    @property
    def gate(self) -> ConcurrencyGate:
        return self._gate

    async def _next_fallback_order(self, plan: tuple[str, ...]) -> tuple[str, ...]:
        tail = [provider for provider in plan if provider in FALLBACK_AGENT_PROVIDERS]
        if len(tail) <= 1:
            return tuple(tail)
        if self._fallback_cursor is not None:
            start = int(self._fallback_cursor()) % len(tail)
        else:
            async with self._fallback_lock:
                start = self._fallback_index % len(tail)
                self._fallback_index += 1
        return tuple(tail[start:] + tail[:start])

    async def _attempt_order(self, request: ClaudeCliRequest) -> tuple[str, ...]:
        plan = tuple(request.provider_plan or self.provider_plan)
        primary = tuple(provider for provider in plan if provider in {"claude", "agy"})
        fallback = await self._next_fallback_order(plan)
        return tuple(dict.fromkeys((*primary, *fallback)))

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        last_error: MkbError | None = None
        fallback_reason: str | None = None
        order = await self._attempt_order(request)
        for ordinal, provider in enumerate(order):
            transport = self.providers.get(provider)
            if transport is None:
                last_error = MkbError(
                    "CLAUDE_CLI_TRANSPORT_FAILED",
                    "Configured CLI provider is unavailable",
                    503,
                    {"provider": provider},
                )
                continue
            lease = await self._gate.try_acquire(provider)
            if lease is None:
                last_error = MkbError(
                    "INFERENCE_BACKPRESSURE",
                    "CLI provider capacity is full",
                    503,
                    {"provider": provider},
                )
                continue
            effective = request
            if provider == "claude" and not effective.model:
                effective = replace(effective, model=self.primary_model)
            elif provider != "claude" and effective.model:
                effective = replace(effective, model=None)
            try:
                result = await transport.run(effective)
                return replace(
                    result,
                    provider=provider,
                    model=result.model or effective.model,
                    attempt_ordinal=ordinal,
                    fallback_from=None if ordinal == 0 else order[ordinal - 1],
                    fallback_reason=fallback_reason,
                )
            except MkbError as exc:
                last_error = exc
                if exc.code not in FALLBACKABLE_AGENT_ERRORS:
                    raise
                fallback_reason = exc.code
            finally:
                await self._gate.release(lease)
        if last_error is not None:
            raise last_error
        raise MkbError("CLAUDE_CLI_TRANSPORT_FAILED", "No CLI provider is configured", 503)

    async def aclose(self) -> None:
        for provider in self.providers.values():
            closer = getattr(provider, "aclose", None)
            if callable(closer):
                result = closer()
                if isinstance(result, Awaitable):
                    await result


__all__ = [
    "AGENT_PROVIDERS",
    "AgentCliPort",
    "AgentCliRouter",
    "SubprocessAgentCli",
]
