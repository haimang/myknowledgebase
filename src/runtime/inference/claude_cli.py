"""Small, injectable Claude CLI transport for the NS1 worker chain.

The port owns command-line transport only.  Prompt identity/hash resolution,
layered-content validation, and S06/S07 admission remain in their respective
domains.  No shell is used and no credential is accepted as an argv field.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from src.contracts.common.errors import MkbError
from src.runtime.inference.facade import ConcurrencyGate

CLAUDE_CLI_ARGV_PROMPT_LIMIT_BYTES = 16_384
CLAUDE_CLI_STDOUT_LIMIT_BYTES = 8 * 1024 * 1024
BJSON_MATERIAL_SCHEMA = "mkb.b-json-material.v1"


@dataclass(frozen=True, slots=True)
class ClaudeCliRequest:
    """One explicit A/B/C CLI invocation material."""

    user_prompt: str
    system_prompt_file: str | Path
    json_schema: Mapping[str, object] | None = None
    model: str | None = None
    timeout_seconds: float = 900.0
    role: Literal["clean", "markdown", "json", "summarizer"] | None = None
    granularity_set: tuple[int, ...] = (0, 1, 2)

    @property
    def structured(self) -> bool:
        return self.json_schema is not None


@dataclass(frozen=True, slots=True)
class ClaudeCliResult:
    """Transport result with safe metadata and transient parsed output."""

    text: str
    structured_output: dict[str, Any] | None
    exit_code: int
    session_id: str | None = None
    usage: Mapping[str, object] | None = None
    is_error: bool = False


class ClaudeCliPort(Protocol):
    """Injectable boundary used by clean/transcribe/structure/construct workers."""

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        """Run one CLI request and return parsed transport output."""


def prompt_transport_for(user_prompt: str) -> Literal["argv", "stdin"]:
    """Business body always travels on stdin so it cannot appear in argv."""

    del user_prompt
    return "stdin"


def clean_text_from_bjson_material(user_prompt: str) -> str:
    """Read the clean SSOT out of a typed B.json package, else the raw prompt."""

    try:
        package = json.loads(user_prompt)
    except json.JSONDecodeError:
        return user_prompt.strip()
    if isinstance(package, dict) and package.get("schema_version") == BJSON_MATERIAL_SCHEMA:
        clean = package.get("clean")
        if isinstance(clean, str) and clean.strip():
            return clean.strip()
    return user_prompt.strip()


def _exact_splits(text: str, delimiter: str) -> list[str]:
    if not text:
        return []
    if not delimiter or delimiter not in text:
        return [text]
    parts = text.split(delimiter)
    chunks: list[str] = []
    for index, part in enumerate(parts):
        chunk = part if index == 0 else f"{delimiter}{part}"
        if chunk:
            chunks.append(chunk)
    return chunks


def _stub_parts_for_granularity(material: str, granularity: int) -> list[str]:
    if granularity == 0:
        return [material]
    delimiters = ("\n## ", "## ") if granularity == 1 else ("\n\n", "\n")
    for delimiter in delimiters:
        parts = [part for part in _exact_splits(material, delimiter) if part]
        if len(parts) >= 2:
            return parts
    midpoint = max(1, len(material) // 2)
    return [part for part in (material[:midpoint], material[midpoint:]) if part] or [material]


# Live Spark VL stays under 8192 tokens at ~16k chars. Long g0 originals are
# kept in construct; the stub summary must still be embeddable.
_STUB_G0_SUMMARY_CHAR_BUDGET = 16_000


def _stub_summary_body(original: str, granularity: int) -> str:
    digest = hashlib.sha256(original.encode("utf-8")).hexdigest()[:16]
    first_line = next((line.strip() for line in original.splitlines() if line.strip()), "document")
    if granularity != 0:
        return f"summary:{digest}:{first_line[:200]}"
    if len(original) <= _STUB_G0_SUMMARY_CHAR_BUDGET:
        return f"Document summary [{digest}]: {first_line[:400]}"
    return f"Document summary [{digest}]: {first_line[:400]}"


def _stub_layered_blocks(material: str, profile: tuple[int, ...]) -> list[dict[str, object]]:
    blocks: list[dict[str, object]] = []
    block_id = 0
    for granularity in profile:
        for body in _stub_parts_for_granularity(material, granularity):
            blocks.append(
                {
                    "block_id": block_id,
                    "granularity": granularity,
                    "original_content": {"title": None, "body": body},
                    "llm_summary": {"title": None, "body": None},
                }
            )
            block_id += 1
    return blocks


def build_claude_argv(
    request: ClaudeCliRequest,
    *,
    executable: str = "claude",
    prompt_transport: Literal["argv", "stdin"] = "argv",
) -> tuple[str, ...]:
    """Build the closed argv contract without a shell or credential flags."""

    if not isinstance(request.user_prompt, str) or not request.user_prompt.strip():
        raise MkbError("CLAUDE_CLI_INPUT_INVALID", "Claude CLI user material must be non-empty", 422)
    prompt_path = Path(request.system_prompt_file)
    if not str(prompt_path) or not prompt_path.name:
        raise MkbError("CLAUDE_CLI_INPUT_INVALID", "Claude CLI system prompt file is required", 422)
    if request.timeout_seconds <= 0:
        raise MkbError("CLAUDE_CLI_INPUT_INVALID", "Claude CLI timeout must be positive", 422)
    argv: list[str] = [executable, "-p"]
    if prompt_transport == "argv":
        argv.append(request.user_prompt)
    argv.extend(
        [
            "--bare",
            "--system-prompt-file",
            str(prompt_path),
            "--tools",
            "",
        ]
    )
    if request.model:
        argv.extend(("--model", request.model))
    if request.json_schema is not None:
        try:
            schema = json.dumps(
                _cli_json_schema(request.json_schema),
                ensure_ascii=False,
                sort_keys=True,
                separators=(",", ":"),
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise MkbError("CLAUDE_CLI_SCHEMA_INVALID", "Claude CLI JSON schema is not deterministic JSON", 422) from exc
        argv.extend(("--output-format", "json", "--json-schema", schema))
    return tuple(argv)


def _cli_json_schema(schema: Mapping[str, object]) -> dict[str, object]:
    """Drop JSON Schema meta-document keys the CLI treats as remote $ref."""

    sanitized = dict(schema)
    sanitized.pop("$schema", None)
    sanitized.pop("$id", None)
    return sanitized


def cli_structured_kind(value: object, *, present: bool) -> str:
    """Closed diagnosis for a non-object structured payload. Never returns the payload."""

    if not present:
        return "missing"
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "bool"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, str):
        return "empty_result" if not value.strip() else "string"
    if isinstance(value, list):
        return "list"
    if isinstance(value, Mapping):
        return "object"
    return "other"


def _decode_structured_stdout(stdout: str) -> tuple[str, dict[str, Any] | None, str | None, Mapping[str, object] | None, bool]:
    try:
        envelope = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Claude CLI structured output is not JSON", 502) from exc
    if not isinstance(envelope, Mapping):
        raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Claude CLI output envelope is invalid", 502)
    is_error = bool(envelope.get("is_error", False))
    session_id = envelope.get("session_id") if isinstance(envelope.get("session_id"), str) else None
    usage = envelope.get("usage") if isinstance(envelope.get("usage"), Mapping) else None
    structured = envelope.get("structured_output")
    if isinstance(structured, Mapping):
        return json.dumps(structured, ensure_ascii=False, sort_keys=True, separators=(",", ":")), dict(structured), session_id, usage, is_error
    result = envelope.get("result")
    if isinstance(result, str) and result.strip():
        try:
            parsed_result = json.loads(result)
        except json.JSONDecodeError as exc:
            kind = cli_structured_kind(result, present=True)
            raise MkbError(
                "CLAUDE_CLI_OUTPUT_INVALID",
                f"Claude CLI structured result is {kind}",
                502,
                {"cli_structured_kind": kind},
            ) from exc
        if isinstance(parsed_result, Mapping):
            return result.strip(), dict(parsed_result), session_id, usage, is_error
        kind = cli_structured_kind(parsed_result, present=True)
        raise MkbError(
            "CLAUDE_CLI_OUTPUT_INVALID",
            f"Claude CLI structured result is {kind}",
            502,
            {"cli_structured_kind": kind},
        )
    if "structured_output" in envelope:
        kind = cli_structured_kind(structured, present=True)
        raise MkbError(
            "CLAUDE_CLI_OUTPUT_INVALID",
            f"Claude CLI structured result is {kind}",
            502,
            {"cli_structured_kind": kind},
        )
    raise MkbError(
        "CLAUDE_CLI_OUTPUT_INVALID",
        "Claude CLI returned no result",
        502,
        {"cli_structured_kind": "empty_result"},
    )


def _decode_plain_stdout(stdout: str) -> tuple[str, str | None, Mapping[str, object] | None, bool]:
    """Decode text mode while accepting Claude's optional JSON envelope."""

    text = stdout.strip()
    if not text:
        raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Claude CLI returned empty text", 502)
    try:
        envelope = json.loads(text)
    except json.JSONDecodeError:
        return text, None, None, False
    if not isinstance(envelope, Mapping):
        return text, None, None, False
    is_error = bool(envelope.get("is_error", False))
    session_id = envelope.get("session_id") if isinstance(envelope.get("session_id"), str) else None
    usage = envelope.get("usage") if isinstance(envelope.get("usage"), Mapping) else None
    result = envelope.get("result")
    if isinstance(result, str) and result.strip():
        return result.strip(), session_id, usage, is_error
    if is_error:
        return "", session_id, usage, True
    # A JSON-looking plain response without the Claude envelope is still text.
    return text, session_id, usage, is_error


class SubprocessClaudeCli:
    """Production port using ``claude`` argv without shell interpolation."""

    def __init__(
        self,
        *,
        executable: str = "claude",
        env: Mapping[str, str] | None = None,
        concurrency_gate: ConcurrencyGate | None = None,
    ) -> None:
        self._executable = executable
        self._env = _cli_child_env(env)
        self._gate = concurrency_gate

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        lease = None
        if self._gate is not None:
            lease = await self._gate.try_acquire("cli")
            if lease is None:
                raise MkbError("INFERENCE_BACKPRESSURE", "Claude CLI concurrency gate is full", 503)
        try:
            return await self._run_transport(request)
        finally:
            if lease is not None:
                await self._gate.release(lease)

    async def _run_transport(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        transport = prompt_transport_for(request.user_prompt)
        argv = build_claude_argv(request, executable=self._executable, prompt_transport=transport)
        process: asyncio.subprocess.Process | None = None
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE if transport == "stdin" else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env,
            )
            payload = request.user_prompt.encode("utf-8") if transport == "stdin" else None
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                _bounded_communicate(process, payload, CLAUDE_CLI_STDOUT_LIMIT_BYTES),
                request.timeout_seconds,
            )
        except MkbError:
            await asyncio.shield(_terminate_process(process))
            raise
        except TimeoutError as exc:
            await asyncio.shield(_terminate_process(process))
            raise MkbError("CLAUDE_CLI_TIMEOUT", "Claude CLI invocation timed out", 503) from exc
        except asyncio.CancelledError:
            await asyncio.shield(_terminate_process(process))
            raise
        except OSError as exc:
            await asyncio.shield(_terminate_process(process))
            raise MkbError("CLAUDE_CLI_TRANSPORT_FAILED", "Claude CLI could not be started", 503) from exc
        stdout = stdout_bytes.decode("utf-8", errors="replace")
        stderr = stderr_bytes.decode("utf-8", errors="replace")
        exit_code = process.returncode if process.returncode is not None else -1
        if exit_code != 0:
            raise MkbError(
                "CLAUDE_CLI_TRANSPORT_FAILED",
                "Claude CLI exited unsuccessfully",
                503,
                {"exit_code": exit_code, "stderr_digest": _digest_text(stderr)},
            )
        if request.structured:
            text, structured, session_id, usage, is_error = _decode_structured_stdout(stdout)
            if is_error:
                raise MkbError("CLAUDE_CLI_TRANSPORT_FAILED", "Claude CLI reported an error", 503)
            if structured is None:
                raise MkbError(
                    "CLAUDE_CLI_OUTPUT_INVALID",
                    "Claude CLI structured result is not an object",
                    502,
                    {"cli_structured_kind": "missing"},
                )
            return ClaudeCliResult(text, structured, exit_code, session_id, usage, is_error)
        text, session_id, usage, is_error = _decode_plain_stdout(stdout)
        if is_error:
            raise MkbError("CLAUDE_CLI_TRANSPORT_FAILED", "Claude CLI reported an error", 503)
        if not text:
            raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Claude CLI returned empty text", 502)
        return ClaudeCliResult(text, None, exit_code, session_id, usage, is_error)


def _digest_text(value: str) -> str:
    import hashlib

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


_CLI_ENV_KEYS = frozenset({"PATH", "LANG", "HOME", "LC_ALL", "LC_CTYPE", "TERM"})
_CLI_ENV_PREFIXES = ("ANTHROPIC_", "CLAUDE_")


def _cli_child_env(env: Mapping[str, str] | None) -> dict[str, str]:
    source = dict(env) if env is not None else dict(os.environ)
    return {
        key: value
        for key, value in source.items()
        if key in _CLI_ENV_KEYS or key.startswith(_CLI_ENV_PREFIXES)
    }


async def _bounded_communicate(
    process: asyncio.subprocess.Process,
    payload: bytes | None,
    limit: int,
) -> tuple[bytes, bytes]:
    if process.stdin is not None:
        if payload is not None:
            process.stdin.write(payload)
            await process.stdin.drain()
        process.stdin.close()
    stdout = bytearray()
    stderr = bytearray()

    async def _read(stream: asyncio.StreamReader | None, bucket: bytearray) -> None:
        if stream is None:
            return
        while True:
            chunk = await stream.read(65_536)
            if not chunk:
                return
            bucket.extend(chunk)
            if len(bucket) > limit:
                await _terminate_process(process)
                raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Claude CLI output exceeded the bounded stdout cap", 502)

    await asyncio.gather(_read(process.stdout, stdout), _read(process.stderr, stderr))
    await process.wait()
    return bytes(stdout), bytes(stderr)


async def _terminate_process(process: asyncio.subprocess.Process | None) -> None:
    """terminate → wait → kill → wait so a timed-out child cannot linger."""

    if process is None or process.returncode is not None:
        return
    try:
        process.terminate()
    except ProcessLookupError:
        return
    try:
        await asyncio.wait_for(process.wait(), timeout=2.0)
        return
    except (TimeoutError, asyncio.CancelledError):
        pass
    except ProcessLookupError:
        return
    try:
        process.kill()
    except ProcessLookupError:
        return
    try:
        await process.wait()
    except ProcessLookupError:
        return
    except asyncio.CancelledError:
        try:
            process.kill()
        except ProcessLookupError:
            return


ResponseFactory = Callable[[ClaudeCliRequest], ClaudeCliResult | Awaitable[ClaudeCliResult]]


@dataclass(slots=True)
class RecordingStub:
    """No-network test port that records every exact request."""

    responses: Sequence[ClaudeCliResult] = field(default_factory=tuple)
    response_factory: ResponseFactory | None = None
    requests: list[ClaudeCliRequest] = field(default_factory=list)
    concurrency_gate: ConcurrencyGate | None = None

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        lease = None
        if self.concurrency_gate is not None:
            lease = await self.concurrency_gate.try_acquire("cli")
            if lease is None:
                raise MkbError("INFERENCE_BACKPRESSURE", "Claude CLI concurrency gate is full", 503)
        try:
            return await self._run_recorded(request)
        finally:
            if lease is not None:
                await self.concurrency_gate.release(lease)

    async def _run_recorded(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        self.requests.append(request)
        if self.response_factory is not None:
            response = self.response_factory(request)
            if hasattr(response, "__await__"):
                return await response  # type: ignore[misc]
            return response
        if not self.responses:
            raise MkbError("CLAUDE_CLI_STUB_EMPTY", "RecordingStub has no configured response", 503)
        return self.responses[0] if len(self.requests) == 1 else self.responses[min(len(self.requests) - 1, len(self.responses) - 1)]


class ClaudeCliCleanLanguageModel:
    """Adapt the CLI port to the existing intake clean-language-model port."""

    def __init__(self, cli: ClaudeCliPort, *, system_prompt_file: str | Path) -> None:
        self._cli = cli
        self._system_prompt_file = system_prompt_file

    async def complete(
        self,
        *,
        prompt: str,
        text: str | None = None,
        blob: bytes | None = None,
        media_type: str | None = None,
    ) -> str:
        if media_type is not None and not str(media_type).startswith("text/"):
            raise MkbError("CLEAN_MEDIA_UNSUPPORTED", "Non-text media cannot be decoded as CLI clean input", 422)
        if blob is not None and text is None:
            raise MkbError("CLEAN_MEDIA_UNSUPPORTED", "Binary clean input is not supported on the CLI path", 422)
        material = text if isinstance(text, str) else ""
        result = await self._cli.run(
            ClaudeCliRequest(
                user_prompt=material,
                system_prompt_file=self._system_prompt_file,
                role="clean",
            )
        )
        if not isinstance(result.text, str) or not result.text.strip():
            raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Claude CLI clean result is empty", 502)
        return result.text.strip()


class DeterministicNs1Stub:
    """No-network local worker used by offline app tests and local proofs."""

    def __init__(self, *, concurrency_gate: ConcurrencyGate | None = None) -> None:
        self.requests: list[ClaudeCliRequest] = []
        self._gate = concurrency_gate

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        lease = None
        if self._gate is not None:
            lease = await self._gate.try_acquire("cli")
            if lease is None:
                raise MkbError("INFERENCE_BACKPRESSURE", "Claude CLI concurrency gate is full", 503)
        try:
            return await self._run_stub(request)
        finally:
            if lease is not None:
                await self._gate.release(lease)

    async def _run_stub(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        self.requests.append(request)
        if request.role == "summarizer":
            try:
                package = json.loads(request.user_prompt)
            except json.JSONDecodeError as exc:
                raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Stub summarizer input is not JSON", 422) from exc
            if not isinstance(package, dict) or not isinstance(package.get("layered_content"), list):
                raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Stub summarizer input is not layered JSON", 422)
            for block in package["layered_content"]:
                if isinstance(block, dict) and isinstance(block.get("original_content"), dict):
                    original = block["original_content"].get("body")
                    if isinstance(block.get("llm_summary"), dict) and isinstance(original, str):
                        granularity = block.get("granularity")
                        gran = granularity if isinstance(granularity, int) else 0
                        block["llm_summary"]["body"] = _stub_summary_body(original, gran)
            value = package
        elif request.role == "json":
            material = clean_text_from_bjson_material(request.user_prompt)
            value = {
                "context_meta": {},
                "layered_content": _stub_layered_blocks(material, request.granularity_set),
            }
        else:
            return ClaudeCliResult(request.user_prompt.strip(), None, 0, session_id=f"stub-{len(self.requests)}")
        encoded = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        return ClaudeCliResult(
            encoded,
            value,
            0,
            session_id=f"stub-{len(self.requests)}",
            usage={"input_tokens": len(request.user_prompt), "output_tokens": len(encoded)},
        )


__all__ = [
    "ClaudeCliPort",
    "ClaudeCliRequest",
    "ClaudeCliResult",
    "ClaudeCliCleanLanguageModel",
    "DeterministicNs1Stub",
    "RecordingStub",
    "SubprocessClaudeCli",
    "build_claude_argv",
    "clean_text_from_bjson_material",
    "prompt_transport_for",
    "BJSON_MATERIAL_SCHEMA",
    "CLAUDE_CLI_ARGV_PROMPT_LIMIT_BYTES",
]
