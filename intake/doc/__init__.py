"""General-document and image LLM clean channel."""

from __future__ import annotations

from intake.text import clean_plain_text, extract_html_text
from intake.types import CleanLanguageModel, CleanPrompt, CleanResult, DeterministicOcr
from src.contracts.common.errors import MkbError
from src.contracts.intake.strategies import CleanStrategyKey, resolve_clean_strategy


def clean_deterministic(text: str, *, media_type: str | None, capability: str) -> CleanResult:
    if isinstance(media_type, str) and media_type.startswith("image/"):
        raise MkbError("CLEAN_CAPABILITY_MISMATCH", "Image media cannot use deterministic document cleaning", 409)
    if media_type == "text/html":
        cleaned, evidence = extract_html_text(text)
    else:
        cleaned = clean_plain_text(text)
        evidence = {"parser": "deterministic-text-normalizer.v1"}
    if not cleaned:
        raise MkbError("CLEAN_EMPTY", "Cleaning produced no admissible text", 422)
    definition = resolve_clean_strategy(CleanStrategyKey.DOC_DETERMINISTIC.value)
    evidence = {
        **evidence,
        "channel": "doc",
        "mode": "deterministic",
        "strategy": CleanStrategyKey.DOC_DETERMINISTIC.value,
        "definition_version": definition.definition_version,
        "strategy_definition_digest": definition.definition_digest,
    }
    return CleanResult(text=cleaned, capability=capability, evidence=evidence)


async def clean_document(
    *,
    text: str | None = None,
    blob: bytes | None = None,
    media_type: str | None = None,
    capability: str = "clean.extract.doc_llm",
    strategy: str | None = None,
    llm: CleanLanguageModel | None = None,
    ocr: DeterministicOcr | None = None,
    prompt: CleanPrompt | None = None,
    team_uuid: str | None = None,
) -> CleanResult:
    """Execute one explicit document/OCR/Vision strategy."""

    selected_strategy = strategy or {
        "clean.extract.doc_llm": CleanStrategyKey.DOC_DOCUMENT_UNDERSTANDING.value,
        "clean.ocr.local": CleanStrategyKey.DOC_OCR.value,
        "clean.extract.vision": CleanStrategyKey.DOC_VISION.value,
    }.get(capability)
    if selected_strategy is None:
        raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Process has no registered document strategy", 409)
    strategy = selected_strategy
    definition = resolve_clean_strategy(strategy)
    if definition.channel != "doc" or definition.clean_capability != capability:
        raise MkbError(
            "CLEAN_STRATEGY_CAPABILITY_MISMATCH", "Document strategy does not match the Process capability", 409
        )
    if blob is not None and len(blob) > definition.max_input_bytes:
        raise MkbError("CLEAN_INPUT_TOO_LARGE", "Document input exceeds the registered strategy budget", 422)
    if strategy in {CleanStrategyKey.DOC_OCR.value, CleanStrategyKey.DOC_VISION.value}:
        if not (media_type or "").startswith("image/"):
            raise MkbError("CLEAN_CAPABILITY_MISMATCH", "OCR/Vision strategy requires image media", 409)
        if strategy == CleanStrategyKey.DOC_OCR.value:
            if ocr is None:
                raise MkbError("CLEAN_OCR_CAPABILITY_UNAVAILABLE", "Image OCR capability is not injected", 503)
            if not blob:
                raise MkbError("CLEAN_IMAGE_MISSING", "Image clean requires representation bytes", 422)
            supplied = await ocr.recognize(blob, media_type=media_type or "")
            cleaned = str(getattr(supplied, "text", "")).strip()
            supplied_evidence = getattr(supplied, "evidence", None)
            producer_evidence = supplied_evidence() if callable(supplied_evidence) else {}
        else:
            if llm is None:
                raise MkbError("CLEAN_VISION_CAPABILITY_UNAVAILABLE", "Image Vision capability is not injected", 503)
            if not blob:
                raise MkbError("CLEAN_IMAGE_MISSING", "Image clean requires representation bytes", 422)
            if prompt is None or prompt.key != definition.prompt_key or prompt.version != definition.prompt_version:
                raise MkbError("PROMPT_HASH_MISMATCH", "Vision lacks its frozen prompt pointer", 503)
            complete_bound = getattr(llm, "complete_bound", None)
            if callable(complete_bound):
                cleaned = (
                    await complete_bound(
                        team_uuid=team_uuid or "mkb-intake-clean",
                        prompt=prompt,
                        blob=blob,
                        media_type=media_type,
                        purpose="vision",
                    )
                ).strip()
            else:
                cleaned = (await llm.complete(prompt=prompt.text, blob=blob, media_type=media_type)).strip()
            producer_evidence = {"producer": "s11.multimodal"}
        if not cleaned:
            raise MkbError("CLEAN_EMPTY", "Image cleaning produced no admissible text", 422)
        return CleanResult(
            text=cleaned,
            capability=capability,
            evidence={
                "channel": "doc",
                "mode": "ocr" if strategy == CleanStrategyKey.DOC_OCR.value else "vision",
                "strategy": strategy,
                "definition_version": definition.definition_version,
                "strategy_definition_digest": definition.definition_digest,
                **producer_evidence,
                "prompt_key": prompt.key if prompt is not None else None,
                "prompt_version": prompt.version if prompt is not None else None,
                "prompt_content_sha256": prompt.content_sha256 if prompt is not None else None,
            },
        )
    if strategy != CleanStrategyKey.DOC_DOCUMENT_UNDERSTANDING.value:
        raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Clean strategy is not a document strategy", 409)
    if llm is not None and (text or blob):
        if prompt is None or prompt.key != definition.prompt_key or prompt.version != definition.prompt_version:
            raise MkbError("PROMPT_HASH_MISMATCH", "Document understanding lacks its frozen prompt pointer", 503)
        multimodal_media = isinstance(media_type, str) and (
            media_type == "application/pdf" or media_type.startswith("image/")
        )
        bound_blob = blob if multimodal_media else None
        complete_bound = getattr(llm, "complete_bound", None)
        if callable(complete_bound):
            cleaned = (
                await complete_bound(
                    team_uuid=team_uuid or "mkb-intake-clean",
                    prompt=prompt,
                    text=text,
                    blob=bound_blob,
                    media_type=media_type if bound_blob is not None else None,
                    purpose="document_understanding",
                )
            ).strip()
            producer = "s11.multimodal" if bound_blob is not None else "s11.text_generate"
        else:
            cleaned = (
                await llm.complete(
                    prompt=prompt.text,
                    text=text,
                    blob=bound_blob,
                    media_type=media_type if bound_blob is not None else None,
                )
            ).strip()
            producer = "injected-llm"
        if not cleaned:
            raise MkbError("CLEAN_EMPTY", "Document LLM cleaning produced no admissible text", 422)
        return CleanResult(
            text=cleaned,
            capability=capability,
            evidence={
                "channel": "doc",
                "mode": "document_understanding",
                "strategy": strategy,
                "definition_version": definition.definition_version,
                "strategy_definition_digest": definition.definition_digest,
                "producer": producer,
                "prompt_key": definition.prompt_key,
                "prompt_version": definition.prompt_version,
                "prompt_content_sha256": prompt.content_sha256,
            },
        )
    raise MkbError("CLEAN_LLM_UNAVAILABLE", "Document understanding requires an injected language model", 503)


__all__ = ["clean_deterministic", "clean_document"]
