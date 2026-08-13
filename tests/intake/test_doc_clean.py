"""Per-domain tests for intake/doc deterministic + LLM document clean."""

from __future__ import annotations

import pytest

from intake.doc import clean_deterministic, clean_document
from src.contracts.common.errors import MkbError


class _DocLLM:
    async def complete(self, *, prompt: str, text: str | None = None, blob: bytes | None = None, media_type: str | None = None) -> str:
        del prompt
        if blob:
            return f"OCR:{media_type}:{len(blob)}"
        return f"DOC:{text}"


def test_doc_deterministic_html_extracts_text() -> None:
    result = clean_deterministic("<p>Hello <b>docs</b></p>", media_type="text/html", capability="clean.extract.deterministic")
    assert "Hello" in result.text
    assert "docs" in result.text


@pytest.mark.asyncio
async def test_doc_llm_cleans_general_document() -> None:
    result = await clean_document(text=" messy  notes ", capability="clean.extract.doc_llm", llm=_DocLLM())
    assert result.text.startswith("DOC:")
    assert result.evidence["mode"] == "document_llm"


@pytest.mark.asyncio
async def test_ocr_succeeds_when_llm_is_injected() -> None:
    result = await clean_document(
        blob=b"\x89PNG\r\n\x1a\nxx",
        media_type="image/png",
        capability="clean.ocr.local",
        llm=_DocLLM(),
    )
    assert result.text.startswith("OCR:image/png:")
    assert result.capability == "clean.ocr.local"


@pytest.mark.asyncio
async def test_ocr_without_injection_fails_closed() -> None:
    with pytest.raises(MkbError) as raised:
        await clean_document(blob=b"\x89PNG\r\n\x1a\nxx", media_type="image/png", capability="clean.ocr.local")
    assert raised.value.code == "CLEAN_OCR_CAPABILITY_UNAVAILABLE"
