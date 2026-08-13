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
        llm_required=True,
        browser_required=False,
        prompt_key="promptA.default",
        prompt_version="v1",
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
        llm_required=True,
        browser_required=False,
        prompt_key="promptA.default",
        prompt_version="v1",
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

_BY_KEY = {definition.strategy_key.value: definition for definition in CLEAN_STRATEGY_DEFINITIONS}


def resolve_clean_strategy(strategy_key: str) -> CleanStrategyDefinition:
    definition = _BY_KEY.get(strategy_key)
    if definition is None:
        raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Clean strategy is not registered", 409)
    return definition


def clean_strategy_manifest_digest() -> str:
    return stable_digest([definition.model_dump(mode="json") for definition in CLEAN_STRATEGY_DEFINITIONS])


__all__ = [
    "CLEAN_STRATEGY_DEFINITIONS",
    "CleanStrategyDefinition",
    "CleanStrategyKey",
    "clean_strategy_manifest_digest",
    "resolve_clean_strategy",
]
