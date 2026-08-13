"""Per-domain tests for intake/pdf document-understanding clean."""

from __future__ import annotations

import hashlib

import pytest

from intake.pdf import clean_pdf
from intake.types import CleanPrompt
from src.contracts.common.errors import MkbError

_PROMPT_TEXT = "verified prompt"
_PROMPT = CleanPrompt(
    key="promptA.default",
    version="v1",
    text=_PROMPT_TEXT,
    content_sha256=hashlib.sha256(_PROMPT_TEXT.encode()).hexdigest(),
)


class _PdfLLM:
    async def complete(self, *, prompt: str, text: str | None = None, blob: bytes | None = None, media_type: str | None = None) -> str:
        del prompt, text, media_type
        assert blob is not None and blob.startswith(b"%PDF-")
        return "Understood PDF section one.\nUnderstood PDF section two."


@pytest.mark.asyncio
async def test_pdf_llm_understands_injected_bytes() -> None:
    result = await clean_pdf(
        blob=b"%PDF-1.4 fixture",
        llm=_PdfLLM(),
        prompt=_PROMPT,
        strategy="pdf.document_understanding",
    )
    assert "Understood PDF section one" in result.text
    assert result.evidence["mode"] == "document_understanding"


@pytest.mark.asyncio
async def test_pdf_without_llm_or_text_fails_closed() -> None:
    with pytest.raises(MkbError) as raised:
        await clean_pdf(blob=b"%PDF-1.4 fixture")
    assert raised.value.code == "CLEAN_LLM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_pdf_uses_decoded_text_layer_when_present() -> None:
    result = await clean_pdf(
        decoded_text="  Local   text layer  ",
        capability="clean.extract.pdf_text",
        strategy="pdf.text_layer",
    )
    assert result.text == "Local text layer"
    assert result.evidence["mode"] == "text_layer"


@pytest.mark.asyncio
async def test_pdf_text_layer_cannot_succeed_empty_and_understanding_cannot_downgrade() -> None:
    with pytest.raises(MkbError) as empty:
        await clean_pdf(decoded_text="  ", capability="clean.extract.pdf_text", strategy="pdf.text_layer")
    assert empty.value.code == "CLEAN_PDF_TEXT_LAYER_MISSING"
    with pytest.raises(MkbError) as unavailable:
        await clean_pdf(decoded_text="available layer", strategy="pdf.document_understanding")
    assert unavailable.value.code == "CLEAN_LLM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_pdf_ocr_is_a_distinct_explicit_strategy() -> None:
    result = await clean_pdf(
        blob=b"%PDF-1.4 scanned fixture",
        capability="clean.ocr.local",
        strategy="pdf.ocr",
        llm=_PdfLLM(),
        prompt=_PROMPT,
    )
    assert result.evidence["channel"] == "pdf"
    assert result.evidence["mode"] == "ocr"
    assert result.evidence["strategy"] == "pdf.ocr"
