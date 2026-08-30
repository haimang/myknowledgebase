"""PDF document-understanding clean channel."""

from __future__ import annotations

from intake.text import clean_plain_text
from intake.types import CleanLanguageModel, CleanPrompt, CleanResult, DeterministicOcr
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.intake.strategies import CleanStrategyKey, resolve_clean_strategy


async def clean_pdf(
    *,
    decoded_text: str | None = None,
    blob: bytes | None = None,
    capability: str = "clean.extract.pdf_llm",
    strategy: str = CleanStrategyKey.PDF_DOCUMENT_UNDERSTANDING.value,
    llm: CleanLanguageModel | None = None,
    ocr: DeterministicOcr | None = None,
    prompt: CleanPrompt | None = None,
    team_uuid: str | None = None,
) -> CleanResult:
    """Execute one explicit PDF strategy without implicit downgrade."""

    definition = resolve_clean_strategy(strategy)
    if definition.channel != "pdf" or definition.clean_capability != capability:
        raise MkbError("CLEAN_STRATEGY_CAPABILITY_MISMATCH", "PDF strategy does not match the Process capability", 409)
    if blob is not None and len(blob) > definition.max_input_bytes:
        raise MkbError("CLEAN_INPUT_TOO_LARGE", "PDF input exceeds the registered strategy budget", 422)
    if strategy == CleanStrategyKey.PDF_TEXT_LAYER.value:
        text = clean_plain_text(decoded_text or "")
        if not text:
            raise MkbError("CLEAN_PDF_TEXT_LAYER_MISSING", "PDF text-layer strategy found no readable text", 422)
        evidence = {"channel": "pdf", "mode": "text_layer", "producer": "local-text-layer"}
    elif strategy in {
        CleanStrategyKey.PDF_DOCUMENT_UNDERSTANDING.value,
        CleanStrategyKey.WEB_BROWSER_PRINT_PDF.value,
    }:
        if llm is None:
            raise MkbError(
                "CLEAN_LLM_UNAVAILABLE", "PDF document understanding requires an injected language model", 503
            )
        if prompt is None or prompt.key != definition.prompt_key or prompt.version != definition.prompt_version:
            raise MkbError("PROMPT_HASH_MISMATCH", "PDF understanding lacks its frozen prompt pointer", 503)
        if not blob and not decoded_text:
            raise MkbError("CLEAN_PDF_INPUT_MISSING", "PDF document understanding requires bytes or decoded text", 422)
        complete_bound = getattr(llm, "complete_bound", None)
        if callable(complete_bound):
            text = (
                await complete_bound(
                    team_uuid=team_uuid or "mkb-intake-clean",
                    prompt=prompt,
                    text=decoded_text if not blob else None,
                    blob=blob,
                    media_type="application/pdf",
                    purpose="document_understanding",
                )
            ).strip()
            producer = "s11.multimodal" if blob else "s11.text_generate"
        elif blob:
            text = (await llm.complete(prompt=prompt.text, blob=blob, media_type="application/pdf")).strip()
            producer = "injected-llm"
        else:
            text = (await llm.complete(prompt=prompt.text, text=decoded_text, media_type="application/pdf")).strip()
            producer = "injected-llm"
        evidence = {"channel": "pdf", "mode": "document_understanding", "producer": producer}
    elif strategy == CleanStrategyKey.PDF_OCR.value:
        if ocr is None:
            raise MkbError("CLEAN_OCR_CAPABILITY_UNAVAILABLE", "PDF OCR capability is not injected", 503)
        if not blob:
            raise MkbError("CLEAN_PDF_INPUT_MISSING", "PDF OCR requires representation bytes", 422)
        supplied = await ocr.recognize(blob, media_type="application/pdf")
        text = str(getattr(supplied, "text", "")).strip()
        supplied_evidence = getattr(supplied, "evidence", None)
        evidence = {
            "channel": "pdf",
            "mode": "ocr",
            **(supplied_evidence() if callable(supplied_evidence) else {}),
        }
    else:
        raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Clean strategy is not a PDF strategy", 409)
    if not text:
        raise MkbError("CLEAN_EMPTY", "PDF cleaning produced no admissible text", 422)
    return CleanResult(
        text=text,
        capability=capability,
        evidence={
            **evidence,
            "strategy": strategy,
            "definition_version": definition.definition_version,
            "strategy_definition_digest": definition.definition_digest,
            "prompt_key": definition.prompt_key,
            "prompt_version": definition.prompt_version,
            "prompt_content_sha256": prompt.content_sha256 if prompt is not None else None,
            "input_blob_digest": stable_digest({"blob": blob.decode("latin-1")}) if blob is not None else None,
        },
    )


__all__ = ["clean_pdf"]
