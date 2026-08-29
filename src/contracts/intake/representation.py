"""Typed representation route projection; durable row ownership lands in AP-NH3."""

from __future__ import annotations

from typing import Literal, Protocol, runtime_checkable

from pydantic import Field

from src.contracts.common.models import StrictModel

MainTextPresence = Literal["present", "absent", "unknown"]
RepresentationMediaFamily = Literal["text", "pdf", "image", "opaque"]
SelectedCleanStrategy = Literal[
    "web.deterministic",
    "web.llm_rewrite",
    "web.browser_print_pdf",
    "pdf.text_layer",
    "pdf.document_understanding",
    "pdf.ocr",
    "doc.deterministic",
    "doc.document_understanding",
    "doc.ocr",
    "doc.vision",
]


class RepresentationRouteFacts(StrictModel):
    main_text_presence: MainTextPresence
    observer_key: str = Field(min_length=1, max_length=128)
    observer_version: str = Field(min_length=1, max_length=64)
    fact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_family: RepresentationMediaFamily | None = None
    selected_clean_strategy: SelectedCleanStrategy | None = None


@runtime_checkable
class RepresentationFactReader(Protocol):
    async def read_route_facts(self, *, team_uuid: str, execution_uuid: str) -> RepresentationRouteFacts | None: ...


__all__ = [
    "MainTextPresence",
    "RepresentationFactReader",
    "RepresentationMediaFamily",
    "RepresentationRouteFacts",
    "SelectedCleanStrategy",
]
