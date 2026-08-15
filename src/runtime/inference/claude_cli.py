"""Small, injectable Claude CLI transport for the NS1 worker chain.

The port owns command-line transport only.  Prompt identity/hash resolution,
layered-content validation, and S06/S07 admission remain in their respective
domains.  No shell is used and no credential is accepted as an argv field.
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Awaitable, Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from src.contracts.common.errors import MkbError

CLAUDE_CLI_ARGV_PROMPT_LIMIT_BYTES = 16_384
BJSON_MATERIAL_SCHEMA = "mkb.b-json-material.v1"


@dataclass(frozen=True, slots=True)
class ClaudeCliRequest:
    """One explicit A/B/C CLI invocation material."""

    user_prompt: str
    system_prompt_file: str | Path
    json_schema: Mapping[str, object] | None = None
    model: str | None = None
    timeout_seconds: float = 120.0
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
    """Keep small prompts on argv; large material must not hit E2BIG."""

    return "stdin" if len(user_prompt.encode("utf-8")) > CLAUDE_CLI_ARGV_PROMPT_LIMIT_BYTES else "argv"


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
    if granularity != 0 or len(original) <= _STUB_G0_SUMMARY_CHAR_BUDGET:
        return original
    first_line = next((line.strip() for line in original.splitlines() if line.strip()), "document")
    return f"Document summary: {first_line[:400]}"


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
            schema = json.dumps(request.json_schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise MkbError("CLAUDE_CLI_SCHEMA_INVALID", "Claude CLI JSON schema is not deterministic JSON", 422) from exc
        argv.extend(("--output-format", "json", "--json-schema", schema))
    return tuple(argv)


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
    if not isinstance(result, str) or not result.strip():
        raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Claude CLI returned no result", 502)
    try:
        parsed_result = json.loads(result)
    except json.JSONDecodeError:
        return result.strip(), None, session_id, usage, is_error
    if isinstance(parsed_result, Mapping):
        return result.strip(), dict(parsed_result), session_id, usage, is_error
    return result.strip(), None, session_id, usage, is_error


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

    def __init__(self, *, executable: str = "claude", env: Mapping[str, str] | None = None) -> None:
        self._executable = executable
        self._env = dict(env) if env is not None else None

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
        transport = prompt_transport_for(request.user_prompt)
        argv = build_claude_argv(request, executable=self._executable, prompt_transport=transport)
        try:
            process = await asyncio.create_subprocess_exec(
                *argv,
                stdin=asyncio.subprocess.PIPE if transport == "stdin" else asyncio.subprocess.DEVNULL,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=self._env,
            )
            payload = request.user_prompt.encode("utf-8") if transport == "stdin" else None
            stdout_bytes, stderr_bytes = await asyncio.wait_for(process.communicate(payload), request.timeout_seconds)
        except TimeoutError as exc:
            raise MkbError("CLAUDE_CLI_TIMEOUT", "Claude CLI invocation timed out", 503) from exc
        except OSError as exc:
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
                raise MkbError("CLAUDE_CLI_OUTPUT_INVALID", "Claude CLI structured result is not an object", 502)
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


ResponseFactory = Callable[[ClaudeCliRequest], ClaudeCliResult | Awaitable[ClaudeCliResult]]


@dataclass(slots=True)
class RecordingStub:
    """No-network test port that records every exact request."""

    responses: Sequence[ClaudeCliResult] = field(default_factory=tuple)
    response_factory: ResponseFactory | None = None
    requests: list[ClaudeCliRequest] = field(default_factory=list)

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
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
        del media_type
        material = text if isinstance(text, str) else blob.decode("utf-8", errors="replace") if blob is not None else ""
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

    def __init__(self) -> None:
        self.requests: list[ClaudeCliRequest] = []

    async def run(self, request: ClaudeCliRequest) -> ClaudeCliResult:
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
