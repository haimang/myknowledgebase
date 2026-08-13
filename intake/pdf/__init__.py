"""PDF document-understanding clean channel."""

from __future__ import annotations

from intake.text import clean_plain_text
from intake.types import CleanLanguageModel, CleanResult
from src.contracts.common.errors import MkbError

_PDF_PROMPT = (
    "Extract the full readable document text from this PDF. "
    "Do not invent citations. Preserve section order."
)


async def clean_pdf(
    *,
    decoded_text: str | None = None,
    blob: bytes | None = None,
    capability: str = "clean.extract.pdf_llm",
    llm: CleanLanguageModel | None = None,
) -> CleanResult:
    """Understand a PDF via injected LLM, or use a decoded text layer when present."""

    if llm is not None and blob:
        text = (await llm.complete(prompt=_PDF_PROMPT, blob=blob, media_type="application/pdf")).strip()
        evidence = {"channel": "pdf", "mode": "document_understanding", "producer": "injected-llm"}
    elif llm is not None and decoded_text:
        text = (await llm.complete(prompt=_PDF_PROMPT, text=decoded_text, media_type="application/pdf")).strip()
        evidence = {"channel": "pdf", "mode": "document_understanding_text", "producer": "injected-llm"}
    elif decoded_text:
        text = clean_plain_text(decoded_text)
        evidence = {"channel": "pdf", "mode": "decoded_text_layer", "producer": "local-text-layer"}
    else:
        raise MkbError(
            "CLEAN_LLM_UNAVAILABLE",
            "PDF document understanding requires an injected language model or a decoded text layer",
            503,
        )
    if not text:
        raise MkbError("CLEAN_EMPTY", "PDF cleaning produced no admissible text", 422)
    return CleanResult(text=text, capability=capability, evidence=evidence)


__all__ = ["clean_pdf"]
