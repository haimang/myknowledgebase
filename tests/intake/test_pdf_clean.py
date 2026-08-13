"""Per-domain tests for intake/pdf document-understanding clean."""

from __future__ import annotations

import pytest

from intake.pdf import clean_pdf
from src.contracts.common.errors import MkbError


class _PdfLLM:
    async def complete(self, *, prompt: str, text: str | None = None, blob: bytes | None = None, media_type: str | None = None) -> str:
        del prompt, text, media_type
        assert blob is not None and blob.startswith(b"%PDF-")
        return "Understood PDF section one.\nUnderstood PDF section two."


@pytest.mark.asyncio
async def test_pdf_llm_understands_injected_bytes() -> None:
    result = await clean_pdf(blob=b"%PDF-1.4 fixture", llm=_PdfLLM())
    assert "Understood PDF section one" in result.text
    assert result.evidence["mode"] == "document_understanding"


@pytest.mark.asyncio
async def test_pdf_without_llm_or_text_fails_closed() -> None:
    with pytest.raises(MkbError) as raised:
        await clean_pdf(blob=b"%PDF-1.4 fixture")
    assert raised.value.code == "CLEAN_LLM_UNAVAILABLE"


@pytest.mark.asyncio
async def test_pdf_uses_decoded_text_layer_when_present() -> None:
    result = await clean_pdf(decoded_text="  Local   text layer  ")
    assert result.text == "Local text layer"
    assert result.evidence["mode"] == "decoded_text_layer"
