"""Top-level intake clean SSOT.

Runtime may only claim, fence, and commit Process outcomes.  Every clean
transform for web / api / pdf / doc is executed here.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from intake.api import clean_registered_api_members
from intake.doc import clean_deterministic, clean_document
from intake.pdf import clean_pdf
from intake.types import BrowserFetch, CleanLanguageModel, CleanMember, CleanPrompt, CleanResult, HttpFetch
from intake.web import clean_web
from src.contracts.common.errors import MkbError
from src.contracts.intake.strategies import CleanStrategyKey

_REGISTERED_CLEAN = {
    "clean.extract.deterministic",
    "clean.extract.web",
    "clean.extract.web_llm",
    "clean.extract.pdf_text",
    "clean.extract.pdf_llm",
    "clean.extract.doc_llm",
    "clean.ocr.local",
    "clean.extract.vision",
    "clean.map.registered_api",
}


async def dispatch_clean(
    capability: str,
    *,
    text: str | None = None,
    blob: bytes | None = None,
    media_type: str | None = None,
    source_kind: str | None = None,
    url: str | None = None,
    representation: str = "static",
    members: Sequence[Mapping[str, Any]] | None = None,
    provider: str | None = None,
    operation: str | None = None,
    definition_version: str | None = None,
    strategy: str | None = None,
    llm: CleanLanguageModel | None = None,
    http_fetch: HttpFetch | None = None,
    browser_fetch: BrowserFetch | None = None,
    prompt: CleanPrompt | None = None,
) -> CleanResult | list[CleanMember]:
    """Route one Process capability to the owning intake channel."""

    if capability not in _REGISTERED_CLEAN:
        raise MkbError("CLEAN_CAPABILITY_UNSUPPORTED", "Clean capability is not owned by intake", 409)
    if capability == "clean.map.registered_api":
        if members is None:
            raise MkbError("SCATTER_STATE_INVALID", "Registered API clean map lacks members", 422)
        if not all(isinstance(value, str) and value for value in (provider, operation, definition_version)):
            raise MkbError("CLEAN_PROVIDER_OPERATION_REQUIRED", "Registered API clean requires an exact provider binding", 422)
        return clean_registered_api_members(
            members,
            provider=provider,
            operation=operation,
            definition_version=definition_version,
            capability=capability,
        )
    # PDF / image / doc-LLM must win over source_kind==http_resource so an
    # HTTP-acquired PDF is not sanitized as HTML (live http_resource.pdf).
    if capability in {"clean.extract.pdf_llm", "clean.extract.pdf_text"} or media_type == "application/pdf":
        pdf_strategy = strategy
        if pdf_strategy is None:
            if capability == "clean.extract.pdf_text":
                pdf_strategy = CleanStrategyKey.PDF_TEXT_LAYER.value
            elif capability == "clean.ocr.local":
                pdf_strategy = CleanStrategyKey.PDF_OCR.value
            else:
                pdf_strategy = (
                    CleanStrategyKey.WEB_BROWSER_PRINT_PDF.value
                    if representation == "print_pdf"
                    else CleanStrategyKey.PDF_DOCUMENT_UNDERSTANDING.value
                )
        return await clean_pdf(
            decoded_text=text,
            blob=blob,
            capability=capability,
            strategy=pdf_strategy,
            llm=llm,
            prompt=prompt,
        )
    if capability in {"clean.ocr.local", "clean.extract.vision", "clean.extract.doc_llm"} or (
        isinstance(media_type, str) and media_type.startswith("image/")
    ):
        document_strategy = strategy or {
            "clean.extract.doc_llm": CleanStrategyKey.DOC_DOCUMENT_UNDERSTANDING.value,
            "clean.ocr.local": CleanStrategyKey.DOC_OCR.value,
            "clean.extract.vision": CleanStrategyKey.DOC_VISION.value,
        }.get(capability)
        if document_strategy is None:
            raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Document strategy is not registered", 409)
        return await clean_document(
            text=text,
            blob=blob,
            media_type=media_type,
            capability=capability,
            strategy=document_strategy,
            llm=llm,
            prompt=prompt,
        )
    if capability in {"clean.extract.web", "clean.extract.web_llm"}:
        kind = "rendered" if representation == "rendered" else "static"
        return await clean_web(
            html=text,
            url=url,
            representation=kind,
            strategy=strategy
            or (
                CleanStrategyKey.WEB_LLM_REWRITE.value
                if capability == "clean.extract.web_llm"
                else CleanStrategyKey.WEB_DETERMINISTIC.value
            ),
            capability=capability,
            llm=llm,
            prompt=prompt,
            http_fetch=http_fetch,
            browser_fetch=browser_fetch,
        )
    if not isinstance(text, str):
        raise MkbError("PIPELINE_INPUT_INVALID", "Decoded representation is unavailable", 422)
    if strategy not in {None, CleanStrategyKey.DOC_DETERMINISTIC.value}:
        raise MkbError("CLEAN_STRATEGY_CAPABILITY_MISMATCH", "Deterministic strategy does not match the Process capability", 409)
    return clean_deterministic(text, media_type=media_type, capability=capability)


__all__ = [
    "CleanLanguageModel",
    "CleanMember",
    "CleanPrompt",
    "CleanResult",
    "clean_deterministic",
    "clean_document",
    "clean_pdf",
    "clean_registered_api_members",
    "clean_web",
    "dispatch_clean",
]
