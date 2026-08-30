"""NH7-T10 L1: empty LLM rewrites cannot admit clean text."""

from __future__ import annotations

import hashlib

import pytest

from intake.doc import clean_document
from intake.pdf import clean_pdf
from intake.types import CleanPrompt
from intake.web import clean_web
from src.contracts.common.errors import MkbError

_PROMPT = CleanPrompt(
    key="promptA.default",
    version="v1",
    text="verified prompt",
    content_sha256=hashlib.sha256(b"verified prompt").hexdigest(),
)


class _EmptyLLM:
    async def complete(self, **_kwargs: object) -> str:
        return "   \n"


@pytest.mark.asyncio
async def test_web_doc_pdf_llm_raise_clean_empty() -> None:
    with pytest.raises(MkbError) as web:
        await clean_web(
            html="<article>Keep this</article>",
            strategy="web.llm_rewrite",
            capability="clean.extract.web_llm",
            llm=_EmptyLLM(),
            prompt=_PROMPT,
        )
    assert web.value.code == "CLEAN_EMPTY"
    with pytest.raises(MkbError) as doc:
        await clean_document(
            text="Keep this document",
            media_type="text/plain",
            strategy="doc.document_understanding",
            capability="clean.extract.doc_llm",
            llm=_EmptyLLM(),
            prompt=_PROMPT,
        )
    assert doc.value.code == "CLEAN_EMPTY"
    with pytest.raises(MkbError) as pdf:
        await clean_pdf(
            blob=b"%PDF-1.4 fixture",
            strategy="pdf.document_understanding",
            llm=_EmptyLLM(),
            prompt=_PROMPT,
        )
    assert pdf.value.code == "CLEAN_EMPTY"
