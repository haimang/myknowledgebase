"""NH7-T02: deterministic/API paths never call the language model."""

from __future__ import annotations

import hashlib

import pytest

from intake import dispatch_clean
from intake.types import CleanPrompt
from src.contracts.intake.strategies import CANONICAL_CLEAN_PROMPT_KEY, CleanStrategyKey
from src.runtime.supply.pdf_parser import build_compressed_pdf_fixture
from src.services.prompt_profiles import default_prompt_ids


class _RecordingLlm:
    def __init__(self) -> None:
        self.complete_calls = 0

    async def complete(self, **kwargs: object) -> str:
        self.complete_calls += 1
        return "LLM rewrite body"


@pytest.mark.asyncio
async def test_deterministic_and_api_map_zero_complete_calls() -> None:
    llm = _RecordingLlm()
    web = await dispatch_clean(
        "clean.extract.web",
        text="<p>deterministic web</p>",
        media_type="text/html",
        strategy=CleanStrategyKey.WEB_DETERMINISTIC.value,
        llm=llm,
    )
    assert "deterministic web" in web.text
    pdf = await dispatch_clean(
        "clean.extract.pdf_text",
        text="PDF layer body",
        media_type="application/pdf",
        blob=build_compressed_pdf_fixture("PDF layer body"),
        strategy=CleanStrategyKey.PDF_TEXT_LAYER.value,
        llm=llm,
    )
    assert "PDF layer body" in pdf.text
    doc = await dispatch_clean(
        "clean.extract.deterministic",
        text="inline document body",
        media_type="text/plain",
        strategy=CleanStrategyKey.DOC_DETERMINISTIC.value,
        llm=llm,
    )
    assert "inline document body" in doc.text
    assert llm.complete_calls == 0


@pytest.mark.asyncio
async def test_llm_required_strategy_invokes_complete() -> None:
    llm = _RecordingLlm()
    prompt_text = "rewrite this"
    prompt = CleanPrompt(
        key="promptA.default",
        version="v1",
        text=prompt_text,
        content_sha256=hashlib.sha256(prompt_text.encode()).hexdigest(),
    )
    result = await dispatch_clean(
        "clean.extract.web_llm",
        text="<p>source html</p>",
        media_type="text/html",
        strategy=CleanStrategyKey.WEB_LLM_REWRITE.value,
        llm=llm,
        prompt=prompt,
    )
    assert result.text == "LLM rewrite body"
    assert llm.complete_calls == 1


def test_new_tasks_pin_canonical_promptA_default() -> None:
    assert default_prompt_ids(domain="documentation", flavor="qna")["clean"] == CANONICAL_CLEAN_PROMPT_KEY
    assert default_prompt_ids(domain=None, flavor=None).get("clean") is None
