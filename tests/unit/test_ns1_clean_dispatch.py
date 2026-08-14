"""NS1-T21: only LLM clean strategies use the CLI port."""

from __future__ import annotations

import hashlib

import pytest

from intake import dispatch_clean
from intake.types import CleanPrompt
from src.runtime.inference.claude_cli import ClaudeCliCleanLanguageModel, ClaudeCliResult, RecordingStub


@pytest.mark.asyncio
async def test_llm_clean_uses_cli_and_deterministic_clean_does_not() -> None:
    prompt_text = "clean prompt"
    prompt = CleanPrompt(
        key="promptA.default",
        version="v1",
        text=prompt_text,
        content_sha256=hashlib.sha256(prompt_text.encode()).hexdigest(),
    )
    cli = RecordingStub(responses=(ClaudeCliResult("cleaned text", None, 0, session_id="clean-1"),))
    llm = ClaudeCliCleanLanguageModel(cli, system_prompt_file="prompt-a-clean-v1.md")

    result = await dispatch_clean(
        "clean.extract.web_llm",
        text="<p>raw</p>",
        media_type="text/html",
        strategy="web.llm_rewrite",
        llm=llm,
        prompt=prompt,
    )
    assert result.text == "cleaned text"
    assert len(cli.requests) == 1
    assert cli.requests[0].role == "clean"

    await dispatch_clean(
        "clean.extract.web",
        text="<p>deterministic</p>",
        media_type="text/html",
        strategy="web.deterministic",
        llm=llm,
    )
    assert len(cli.requests) == 1
