"""Closed clean-strategy registry and capability bindings."""

from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import Field

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.common.models import StrictModel


class CleanStrategyKey(StrEnum):
    WEB_DETERMINISTIC = "web.deterministic"
    WEB_LLM_REWRITE = "web.llm_rewrite"
    WEB_BROWSER_PRINT_PDF = "web.browser_print_pdf"
    PDF_TEXT_LAYER = "pdf.text_layer"
    PDF_DOCUMENT_UNDERSTANDING = "pdf.document_understanding"
    PDF_OCR = "pdf.ocr"
    DOC_DETERMINISTIC = "doc.deterministic"
    DOC_DOCUMENT_UNDERSTANDING = "doc.document_understanding"
    DOC_OCR = "doc.ocr"
    DOC_VISION = "doc.vision"


class CleanStrategyDefinition(StrictModel):
    strategy_key: CleanStrategyKey
    definition_version: Literal["v1"] = "v1"
    channel: Literal["web", "pdf", "doc"]
    acquire_capabilities: tuple[str, ...]
    clean_capability: str = Field(pattern=r"^clean\.")
    llm_required: bool
    browser_required: bool
    prompt_key: str | None = None
    prompt_version: str | None = None
    max_input_bytes: int = Field(ge=1)

    @property
    def definition_digest(self) -> str:
        return stable_digest(self.model_dump(mode="json"))


_MIB20 = 20 * 1024 * 1024
CLEAN_STRATEGY_DEFINITIONS: tuple[CleanStrategyDefinition, ...] = (
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.WEB_DETERMINISTIC,
        channel="web",
        acquire_capabilities=("intake.acquire.http_static", "intake.acquire.http_browser"),
        clean_capability="clean.extract.web",
        llm_required=False,
        browser_required=False,
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.WEB_LLM_REWRITE,
        channel="web",
        acquire_capabilities=("intake.acquire.http_static", "intake.acquire.http_browser"),
        clean_capability="clean.extract.web_llm",
        llm_required=True,
        browser_required=False,
        prompt_key="promptA.default",
        prompt_version="v1",
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.WEB_BROWSER_PRINT_PDF,
        channel="pdf",
        acquire_capabilities=("intake.acquire.http_browser",),
        clean_capability="clean.extract.pdf_llm",
        llm_required=True,
        browser_required=True,
        prompt_key="promptA.default",
        prompt_version="v1",
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.PDF_TEXT_LAYER,
        channel="pdf",
        acquire_capabilities=("intake.acquire.local_object", "intake.acquire.http_static"),
        clean_capability="clean.extract.pdf_text",
        llm_required=False,
        browser_required=False,
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.PDF_DOCUMENT_UNDERSTANDING,
        channel="pdf",
        acquire_capabilities=("intake.acquire.local_object", "intake.acquire.http_static"),
        clean_capability="clean.extract.pdf_llm",
        llm_required=True,
        browser_required=False,
        prompt_key="promptA.default",
        prompt_version="v1",
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.PDF_OCR,
        channel="pdf",
        acquire_capabilities=("intake.acquire.local_object", "intake.acquire.http_static"),
        clean_capability="clean.ocr.local",
        llm_required=False,
        browser_required=False,
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.DOC_DETERMINISTIC,
        channel="doc",
        acquire_capabilities=("intake.acquire.inline", "intake.acquire.local_object"),
        clean_capability="clean.extract.deterministic",
        llm_required=False,
        browser_required=False,
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.DOC_DOCUMENT_UNDERSTANDING,
        channel="doc",
        acquire_capabilities=("intake.acquire.local_object",),
        clean_capability="clean.extract.doc_llm",
        llm_required=True,
        browser_required=False,
        prompt_key="promptA.default",
        prompt_version="v1",
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.DOC_OCR,
        channel="doc",
        acquire_capabilities=("intake.acquire.local_object",),
        clean_capability="clean.ocr.local",
        llm_required=False,
        browser_required=False,
        max_input_bytes=_MIB20,
    ),
    CleanStrategyDefinition(
        strategy_key=CleanStrategyKey.DOC_VISION,
        channel="doc",
        acquire_capabilities=("intake.acquire.local_object",),
        clean_capability="clean.extract.vision",
        llm_required=True,
        browser_required=False,
        prompt_key="promptA.default",
        prompt_version="v1",
        max_input_bytes=_MIB20,
    ),
)

# M-NH-07: new Tasks freeze this catalog identity. Historical ids remain
# loadable for exact replay of already-sealed snapshots.
CANONICAL_CLEAN_PROMPT_KEY = "promptA.default"
CANONICAL_CLEAN_PROMPT_VERSION = "v1"
HISTORICAL_CLEAN_PROMPT_KEYS = frozenset(
    {"promptA.default", "promptA.clean", "promptA.documentation.default"}
)

_BY_KEY = {definition.strategy_key.value: definition for definition in CLEAN_STRATEGY_DEFINITIONS}

# Graph step_key is the binding identity. One process_key may serve two strategies.
CLEAN_STEP_STRATEGIES: dict[str, str] = {
    "clean": CleanStrategyKey.DOC_DETERMINISTIC.value,
    "clean_deterministic": CleanStrategyKey.DOC_DETERMINISTIC.value,
    "clean_doc_llm": CleanStrategyKey.DOC_DOCUMENT_UNDERSTANDING.value,
    "clean_doc_ocr": CleanStrategyKey.DOC_OCR.value,
    "clean_vision": CleanStrategyKey.DOC_VISION.value,
    "clean_pdf_text": CleanStrategyKey.PDF_TEXT_LAYER.value,
    "clean_pdf_llm": CleanStrategyKey.PDF_DOCUMENT_UNDERSTANDING.value,
    "clean_pdf_ocr": CleanStrategyKey.PDF_OCR.value,
    "clean_print_pdf": CleanStrategyKey.WEB_BROWSER_PRINT_PDF.value,
    "clean_web_static": CleanStrategyKey.WEB_DETERMINISTIC.value,
    "clean_web_browser": CleanStrategyKey.WEB_DETERMINISTIC.value,
    "clean_web_reacquire": CleanStrategyKey.WEB_DETERMINISTIC.value,
    "clean_web_llm_static": CleanStrategyKey.WEB_LLM_REWRITE.value,
    "clean_web_llm_browser": CleanStrategyKey.WEB_LLM_REWRITE.value,
    "clean_web_llm_reacquire": CleanStrategyKey.WEB_LLM_REWRITE.value,
}

SOURCE_KIND_ACQUIRE_CAPABILITIES: dict[str, frozenset[str]] = {
    "inline_payload": frozenset({"intake.acquire.inline"}),
    "local_object": frozenset({"intake.acquire.local_object"}),
    "http_resource": frozenset({"intake.acquire.http_static", "intake.acquire.http_browser"}),
    "registered_api": frozenset({"intake.acquire.registered_api"}),
}


def resolve_clean_strategy(strategy_key: str) -> CleanStrategyDefinition:
    definition = _BY_KEY.get(strategy_key)
    if definition is None:
        raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Clean strategy is not registered", 409)
    return definition


def assert_clean_strategy_applicable(source_kind: str, strategy_key: str | None) -> None:
    """Reject kind×strategy combinations that can never reach a declared worker."""

    if strategy_key is None:
        return
    definition = resolve_clean_strategy(strategy_key)
    allowed = SOURCE_KIND_ACQUIRE_CAPABILITIES.get(source_kind)
    if allowed is None:
        raise MkbError("SOURCE_KIND_INVALID", "Source kind is not registered", 422)
    if allowed.isdisjoint(definition.acquire_capabilities):
        raise MkbError(
            "CLEAN_STRATEGY_KIND_INCOMPATIBLE",
            "Declared clean strategy is not applicable to this source kind",
            422,
            {"source_kind": source_kind, "clean_strategy": strategy_key},
        )


def clean_strategy_manifest_digest() -> str:
    return stable_digest([definition.model_dump(mode="json") for definition in CLEAN_STRATEGY_DEFINITIONS])


def resolve_bound_clean_strategy(*, step_key: str | None, process_key: str) -> CleanStrategyDefinition:
    """Resolve strategy from the compiled graph step, not process_key reverse inference."""

    if not step_key:
        raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Clean step has no bound strategy identity", 409)
    strategy_key = CLEAN_STEP_STRATEGIES.get(step_key)
    if strategy_key is None:
        raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Clean step is not a registered strategy binding", 409)
    definition = resolve_clean_strategy(strategy_key)
    if definition.clean_capability != process_key:
        raise MkbError("CLEAN_STRATEGY_CAPABILITY_MISMATCH", "Bound clean strategy does not match the Process", 409)
    return definition


def derive_selected_clean_strategy(
    *,
    media_family: str | None,
    text_layer: str | None,
    representation_kind: str | None,
    declared: str | None = None,
) -> str | None:
    if declared:
        resolve_clean_strategy(declared)
        return declared
    if representation_kind == "print_pdf":
        return CleanStrategyKey.WEB_BROWSER_PRINT_PDF.value
    if media_family == "pdf":
        if text_layer == "present":
            return CleanStrategyKey.PDF_TEXT_LAYER.value
        if text_layer in {"absent", "encrypted"}:
            return CleanStrategyKey.PDF_OCR.value
        return CleanStrategyKey.PDF_TEXT_LAYER.value
    if media_family == "image":
        return CleanStrategyKey.DOC_OCR.value
    if representation_kind == "rendered":
        return CleanStrategyKey.WEB_DETERMINISTIC.value
    if media_family == "text":
        return None
    return None


__all__ = [
    "CANONICAL_CLEAN_PROMPT_KEY",
    "CANONICAL_CLEAN_PROMPT_VERSION",
    "CLEAN_STEP_STRATEGIES",
    "CLEAN_STRATEGY_DEFINITIONS",
    "SOURCE_KIND_ACQUIRE_CAPABILITIES",
    "assert_clean_strategy_applicable",
    "CleanStrategyDefinition",
    "CleanStrategyKey",
    "HISTORICAL_CLEAN_PROMPT_KEYS",
    "clean_strategy_manifest_digest",
    "derive_selected_clean_strategy",
    "resolve_bound_clean_strategy",
    "resolve_clean_strategy",
]
