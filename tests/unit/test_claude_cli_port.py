"""NS1-T20: Claude CLI argv and structured-output transport contracts."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.runtime.inference.claude_cli import (
    CLAUDE_CLI_ARGV_PROMPT_LIMIT_BYTES,
    ClaudeCliRequest,
    ClaudeCliResult,
    RecordingStub,
    SubprocessClaudeCli,
    _decode_plain_stdout,
    _decode_structured_stdout,
    build_claude_argv,
    prompt_transport_for,
)


def test_build_argv_uses_bare_system_file_tools_and_schema_only_for_structured() -> None:
    plain = build_claude_argv(
        ClaudeCliRequest(user_prompt="clean material", system_prompt_file="data/prompts/clean/prompt.md")
    )
    assert plain[:8] == (
        "claude",
        "-p",
        "clean material",
        "--bare",
        "--system-prompt-file",
        "data/prompts/clean/prompt.md",
        "--tools",
        "",
    )
    assert "--json-schema" not in plain

    structured = build_claude_argv(
        ClaudeCliRequest(
            user_prompt='{"context_meta":{}}',
            system_prompt_file="data/prompts/json/prompt.md",
            json_schema={"type": "object", "additionalProperties": False},
        )
    )
    assert "--output-format" in structured
    assert "json" in structured
    assert "--json-schema" in structured
    assert "--api-key" not in structured
    assert all("secret-token" not in item for item in structured)
    stdin_argv = build_claude_argv(
        ClaudeCliRequest(user_prompt="x" * (CLAUDE_CLI_ARGV_PROMPT_LIMIT_BYTES + 1), system_prompt_file="p.md"),
        prompt_transport="stdin",
    )
    assert stdin_argv[:2] == ("claude", "-p")
    assert "x" * 10 not in stdin_argv
    assert prompt_transport_for("x" * (CLAUDE_CLI_ARGV_PROMPT_LIMIT_BYTES + 1)) == "stdin"


def test_structured_output_has_priority_over_result_string() -> None:
    text, value, session_id, usage, is_error = _decode_structured_stdout(
        '{"is_error":false,"result":"{\\"wrong\\":true}","structured_output":{"ok":true},'
        '"session_id":"session-1","usage":{"output_tokens":3}}'
    )
    assert value == {"ok": True}
    assert text == '{"ok":true}'
    assert session_id == "session-1"
    assert usage == {"output_tokens": 3}
    assert is_error is False


def test_structured_result_string_is_fallback_and_transport_errors_are_typed() -> None:
    _, value, *_ = _decode_structured_stdout(
        '{"is_error":false,"result":"{\\"layered_content\\":[]}"}'
    )
    assert value == {"layered_content": []}
    with pytest.raises(MkbError, match="CLAUDE_CLI_OUTPUT_INVALID"):
        _decode_structured_stdout('{"is_error":false}')
    with pytest.raises(MkbError, match="CLAUDE_CLI_OUTPUT_INVALID"):
        _decode_structured_stdout("not json")


def test_plain_output_accepts_envelope_metadata_and_rejects_error_envelope() -> None:
    text, session_id, usage, is_error = _decode_plain_stdout(
        '{"is_error":false,"result":"# heading","session_id":"session-2","usage":{"output_tokens":4}}'
    )
    assert (text, session_id, usage, is_error) == (
        "# heading",
        "session-2",
        {"output_tokens": 4},
        False,
    )
    text, _, _, is_error = _decode_plain_stdout("plain text")
    assert (text, is_error) == ("plain text", False)
    with pytest.raises(MkbError, match="CLAUDE_CLI_OUTPUT_INVALID"):
        _decode_plain_stdout("")


@pytest.mark.asyncio
async def test_recording_stub_is_injectable_and_preserves_request_metadata() -> None:
    response = ClaudeCliResult("ok", None, 0, session_id="session-1")
    stub = RecordingStub(responses=(response,))
    request = ClaudeCliRequest(user_prompt="material", system_prompt_file="prompt.md")

    assert await stub.run(request) == response
    assert stub.requests == [request]


@pytest.mark.asyncio
async def test_subprocess_cli_transports_large_prompt_on_stdin(tmp_path: Path) -> None:
    helper = tmp_path / "fake_claude.py"
    helper.write_text(
        "#!/usr/bin/env python3\n"
        "import json\n"
        "import sys\n"
        "payload = sys.stdin.read()\n"
        "print(json.dumps({'is_error': False, 'result': payload[:32], 'session_id': 'large'}))\n",
        encoding="utf-8",
    )
    helper.chmod(0o755)
    cli = SubprocessClaudeCli(executable=str(helper))
    material = "Z" * 200_000
    result = await cli.run(ClaudeCliRequest(user_prompt=material, system_prompt_file=str(tmp_path / "prompt.md")))
    assert result.text == "Z" * 32
    assert result.session_id == "large"
