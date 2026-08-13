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
from intake.types import BrowserFetch, CleanLanguageModel, CleanMember, CleanResult, HttpFetch
from intake.web import clean_web
from src.contracts.common.errors import MkbError

_REGISTERED_CLEAN = {
    "clean.extract.deterministic",
    "clean.extract.web",
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
    llm: CleanLanguageModel | None = None,
    http_fetch: HttpFetch | None = None,
    browser_fetch: BrowserFetch | None = None,
) -> CleanResult | list[CleanMember]:
    """Route one Process capability to the owning intake channel."""

    if capability not in _REGISTERED_CLEAN:
        raise MkbError("CLEAN_CAPABILITY_UNSUPPORTED", "Clean capability is not owned by intake", 409)
    if capability == "clean.map.registered_api":
        if members is None:
            raise MkbError("SCATTER_STATE_INVALID", "Registered API clean map lacks members", 422)
        return clean_registered_api_members(members, provider=provider, capability=capability)
    # PDF / image / doc-LLM must win over source_kind==http_resource so an
    # HTTP-acquired PDF is not sanitized as HTML (live http_resource.pdf).
    if capability == "clean.extract.pdf_llm" or media_type == "application/pdf":
        return await clean_pdf(
            decoded_text=text,
            blob=blob,
            capability="clean.extract.pdf_llm" if capability == "clean.extract.pdf_llm" else capability,
            llm=llm,
        )
    if capability in {"clean.ocr.local", "clean.extract.vision", "clean.extract.doc_llm"} or (
        isinstance(media_type, str) and media_type.startswith("image/")
    ):
        return await clean_document(
            text=text,
            blob=blob,
            media_type=media_type,
            capability=capability,
            llm=llm,
        )
    if capability == "clean.extract.web" or (
        capability == "clean.extract.deterministic"
        and source_kind == "http_resource"
        and media_type != "application/pdf"
    ):
        kind = "rendered" if representation == "rendered" else "static"
        return await clean_web(
            html=text,
            url=url,
            representation=kind,
            capability="clean.extract.web" if capability == "clean.extract.web" else capability,
            http_fetch=http_fetch,
            browser_fetch=browser_fetch,
        )
    if not isinstance(text, str):
        raise MkbError("PIPELINE_INPUT_INVALID", "Decoded representation is unavailable", 422)
    return clean_deterministic(text, media_type=media_type, capability=capability)


__all__ = [
    "CleanLanguageModel",
    "CleanMember",
    "CleanResult",
    "clean_deterministic",
    "clean_document",
    "clean_pdf",
    "clean_registered_api_members",
    "clean_web",
    "dispatch_clean",
]
