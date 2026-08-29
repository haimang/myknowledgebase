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
RepresentationFactKind = Literal["acquire", "decode", "print"]
TextLayerObservation = Literal["present", "absent", "encrypted", "corrupt", "not_applicable", "unknown"]


class RepresentationObservation(StrictModel):
    schema_version: Literal["mkb.representation-observation.v1"] = "mkb.representation-observation.v1"
    team_uuid: str = Field(min_length=1, max_length=128)
    execution_uuid: str = Field(min_length=1, max_length=128)
    process_uuid: str = Field(min_length=1, max_length=128)
    step_key: str = Field(min_length=1, max_length=128)
    fact_kind: RepresentationFactKind
    capability: str = Field(min_length=1, max_length=128)
    representation_kind: str = Field(min_length=1, max_length=128)
    declared_media_type: str | None = Field(default=None, max_length=255)
    detected_media_type: str | None = Field(default=None, max_length=255)
    verified_media_type: str = Field(min_length=1, max_length=255)
    raw_byte_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    raw_byte_size: int = Field(ge=0)
    text_layer: TextLayerObservation = "not_applicable"
    main_text_presence: MainTextPresence = "unknown"
    canonicalizer_key: str = Field(min_length=1, max_length=128)
    canonicalizer_version: str = Field(min_length=1, max_length=64)
    observer_key: str = Field(min_length=1, max_length=128)
    observer_version: str = Field(min_length=1, max_length=64)
    profile_identity: str | None = Field(default=None, max_length=256)


class RepresentationRouteFacts(StrictModel):
    main_text_presence: MainTextPresence
    observer_key: str = Field(min_length=1, max_length=128)
    observer_version: str = Field(min_length=1, max_length=64)
    fact_digest: str = Field(pattern=r"^[0-9a-f]{64}$")
    media_family: RepresentationMediaFamily | None = None
    selected_clean_strategy: SelectedCleanStrategy | None = None


@runtime_checkable
class RepresentationFactReader(Protocol):
    async def read_route_facts(
        self,
        *,
        tx: object,
        team_uuid: str,
        execution_uuid: str,
    ) -> RepresentationRouteFacts | None: ...


__all__ = [
    "MainTextPresence",
    "RepresentationFactReader",
    "RepresentationFactKind",
    "RepresentationMediaFamily",
    "RepresentationObservation",
    "RepresentationRouteFacts",
    "SelectedCleanStrategy",
    "TextLayerObservation",
]
