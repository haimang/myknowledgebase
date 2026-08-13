"""General-document and image LLM clean channel."""

from __future__ import annotations

from intake.text import clean_plain_text, extract_html_text
from intake.types import CleanLanguageModel, CleanResult
from src.contracts.common.errors import MkbError

_DOC_PROMPT = "Normalize this document into plain text. Do not add facts."
_IMAGE_PROMPT = "Transcribe all visible text from this image. Do not invent words."


def clean_deterministic(text: str, *, media_type: str | None, capability: str) -> CleanResult:
    if media_type == "text/html":
        cleaned, evidence = extract_html_text(text)
    else:
        cleaned = clean_plain_text(text)
        evidence = {"parser": "deterministic-text-normalizer.v1"}
    if not cleaned:
        raise MkbError("CLEAN_EMPTY", "Cleaning produced no admissible text", 422)
    evidence = {**evidence, "channel": "doc", "mode": "deterministic"}
    return CleanResult(text=cleaned, capability=capability, evidence=evidence)


async def clean_document(
    *,
    text: str | None = None,
    blob: bytes | None = None,
    media_type: str | None = None,
    capability: str = "clean.extract.doc_llm",
    llm: CleanLanguageModel | None = None,
) -> CleanResult:
    """LLM document clean; falls back to deterministic text when no blob/LLM needed."""

    if capability in {"clean.ocr.local", "clean.extract.vision"} or (media_type or "").startswith("image/"):
        if llm is None:
            code = "CLEAN_OCR_CAPABILITY_UNAVAILABLE" if capability == "clean.ocr.local" else "CLEAN_VISION_CAPABILITY_UNAVAILABLE"
            if capability == "clean.extract.vision":
                code = "CLEAN_VISION_CAPABILITY_UNAVAILABLE"
            elif capability != "clean.ocr.local":
                code = "CLEAN_LLM_UNAVAILABLE"
            raise MkbError(code, "Image/document understanding is not injected", 503)
        if not blob:
            raise MkbError("CLEAN_IMAGE_MISSING", "Image clean requires representation bytes", 422)
        cleaned = (await llm.complete(prompt=_IMAGE_PROMPT, blob=blob, media_type=media_type)).strip()
        if not cleaned:
            raise MkbError("CLEAN_EMPTY", "Image cleaning produced no admissible text", 422)
        return CleanResult(
            text=cleaned,
            capability=capability,
            evidence={"channel": "doc", "mode": "image_understanding", "producer": "injected-llm"},
        )
    if llm is not None and (text or blob):
        cleaned = (
            await llm.complete(prompt=_DOC_PROMPT, text=text, blob=blob, media_type=media_type)
        ).strip()
        if not cleaned:
            raise MkbError("CLEAN_EMPTY", "Document LLM cleaning produced no admissible text", 422)
        return CleanResult(
            text=cleaned,
            capability=capability,
            evidence={"channel": "doc", "mode": "document_llm", "producer": "injected-llm"},
        )
    if text:
        return clean_deterministic(text, media_type=media_type, capability=capability)
    raise MkbError("CLEAN_LLM_UNAVAILABLE", "Document LLM clean is not injected and no text was supplied", 503)


__all__ = ["clean_deterministic", "clean_document"]
