"""Compiler IR dataclasses and shared kernel helpers."""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest

_NODE_KINDS = frozenset({"document", "section", "paragraph", "list", "list_item", "table", "table_row", "table_cell", "code", "quote", "media_ref", "heading"})
_CHANNELS = frozenset({"original", "summary"})
_HEADER_KEY = re.compile(r"^[a-z][a-z0-9_.-]{0,63}$")
_SENTENCE = re.compile(r"\S(?:.*?)(?:[.!?。！？](?=\s|$)|$)", re.DOTALL)
_ADOPTED_BLOCK_ID = re.compile(r"^g[0-2]:b(\d{4})$")


def _fail(code: str, message: str) -> None:
    raise MkbError(code, message, 422)


def _text_digest(value: str) -> str:
    """Fingerprint UTF-8 text through the project canonical digest primitive."""

    # Keep the existing artifact/vector text-digest recipe so the compiler can
    # validate current persisted S05/S06 values without a migration shim.
    return stable_digest({"text": value})


def _span_text(value: str, start_byte: int, end_byte: int) -> str:
    encoded = value.encode("utf-8")
    if start_byte < 0 or end_byte < start_byte or end_byte > len(encoded):
        _fail("STRUCTURE_ANCHOR_INVALID", "A source anchor is outside the selected clean artifact")
    try:
        return encoded[start_byte:end_byte].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise MkbError("STRUCTURE_ANCHOR_INVALID", "A source anchor splits a UTF-8 code point", 422) from exc


def _byte_offset(value: str, char_offset: int) -> int:
    return len(value[:char_offset].encode("utf-8"))


def _block_number(block_id: str) -> int:
    match = _ADOPTED_BLOCK_ID.fullmatch(block_id)
    if match is None:
        _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "Projection block identity is not an adopted layered block")
    return int(match.group(1))


@dataclass(frozen=True, slots=True)
class TextSpan:
    start_byte: int
    end_byte: int


@dataclass(frozen=True, slots=True)
class StructureNode:
    node_id: str
    node_kind: str
    parent_node_id: str | None
    sibling_ordinal: int
    depth: int
    reading_ordinal: int
    content_role: str
    source_anchor: TextSpan | None
    content_digest: str | None
    subtree_digest: str


@dataclass(frozen=True, slots=True)
class StructureDocument:
    generation_artifact_uuid: str
    clean_artifact_uuid: str
    clean_digest: str
    document_root_node_id: str
    nodes: tuple[StructureNode, ...]
    proof_digest: str


@dataclass(frozen=True, slots=True)
class RetrievalBlock:
    block_id: str
    granularity: int
    source_node_refs: tuple[str, ...]
    ordered_source_spans: tuple[TextSpan, ...]
    original_text: str
    original_digest: str


@dataclass(frozen=True, slots=True)
class RetrievalBlockProjection:
    generation_artifact_uuid: str
    structure_generation_artifact_uuid: str
    structure_document_digest: str
    blocks: tuple[RetrievalBlock, ...]
    proof_digest: str


@dataclass(frozen=True, slots=True)
class ChannelRecord:
    channel: str
    body: str
    body_digest: str
    content_full: str
    content_full_digest: str
    grounds_coordinate: str
    reattach_status: str


@dataclass(frozen=True, slots=True)
class ConstructionUnit:
    unit_id: str
    granularity: int
    coordinate: str
    original: ChannelRecord
    summary: ChannelRecord


@dataclass(frozen=True, slots=True)
class ConstructionDocument:
    generation_artifact_uuid: str
    structure_generation_artifact_uuid: str
    projection_generation_artifact_uuid: str
    structure_document_digest: str
    projection_digest: str
    units: tuple[ConstructionUnit, ...]
    metadata_projection_digest: str
    content_full_recipe_version: str
    proof_digest: str


@dataclass(frozen=True, slots=True)
class DualChannelProjection:
    generation_artifact_uuid: str
    construction_generation_artifact_uuid: str
    construction_document_digest: str
    units: tuple[ConstructionUnit, ...]
    proof_digest: str


@dataclass(frozen=True, slots=True)
class VectorizationUnit:
    unit_id: str
    granularity: int
    channel: str
    coordinate: str
    content_full: str
    content_full_digest: str


@dataclass(frozen=True, slots=True)
class VectorizationPlan:
    required: tuple[VectorizationUnit, ...]
    skipped: tuple[str, ...]
    required_digest: str


@dataclass(frozen=True, slots=True)
class SummaryPlan:
    """Deterministic ordered summary workset for a projection generation."""

    block_ids: tuple[str, ...]
    plan_digest: str


def content_full(*, body: str, metadata_headers: Mapping[str, str] | None = None, recipe_version: str = "content_full.v1") -> str:
    """Materialize the S07/S08 re-computable text recipe.

    Only a closed, caller-projected metadata mapping is accepted.  This helper
    does not treat metadata as filter authority; it only deterministically
    renders already-authorized display context.
    """

    if recipe_version != "content_full.v1":
        _fail("CONSTRUCT_RECIPE_UNSUPPORTED", "The content_full recipe version is unsupported")
    if not isinstance(body, str):
        _fail("CONSTRUCT_KERNEL_BODY_INVALID", "Channel body must be UTF-8 text")
    headers = metadata_headers or {}
    lines: list[str] = []
    for key in sorted(headers):
        value = headers[key]
        if not _HEADER_KEY.fullmatch(key) or not isinstance(value, str) or "\x00" in value or "\n" in value or "\r" in value:
            _fail("CONSTRUCT_METADATA_PROJECTION_INVALID", "Content header projection is invalid")
        lines.append(f"{key}: {value}")
    if not lines:
        return body
    header = "\n".join(lines)
    return f"{header}\n\n{body}"
