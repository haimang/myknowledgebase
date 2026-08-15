"""Deterministic digest, payload, and parse helpers for compiler IR."""

from __future__ import annotations

from collections.abc import Mapping

from src.contracts.common.ids import stable_digest
from src.services.lsrag_compiler.models import (
    ConstructionDocument,
    DualChannelProjection,
    RetrievalBlock,
    RetrievalBlockProjection,
    StructureDocument,
    StructureNode,
    SummaryPlan,
    TextSpan,
    _fail,
)


def structure_document_digest(document: StructureDocument) -> str:
    return stable_digest(
        {
            "generation": document.generation_artifact_uuid,
            "clean_artifact": document.clean_artifact_uuid,
            "clean_digest": document.clean_digest,
            "root": document.document_root_node_id,
            "nodes": [
                {
                    "id": node.node_id,
                    "kind": node.node_kind,
                    "parent": node.parent_node_id,
                    "sibling": node.sibling_ordinal,
                    "depth": node.depth,
                    "reading": node.reading_ordinal,
                    "role": node.content_role,
                    "span": None if node.source_anchor is None else (node.source_anchor.start_byte, node.source_anchor.end_byte),
                    "content": node.content_digest,
                    "subtree": node.subtree_digest,
                }
                for node in document.nodes
            ],
            "proof": document.proof_digest,
        }
    )


def projection_digest(projection: RetrievalBlockProjection) -> str:
    return stable_digest(
        {
            "generation": projection.generation_artifact_uuid,
            "structure_generation": projection.structure_generation_artifact_uuid,
            "structure_digest": projection.structure_document_digest,
            "blocks": [
                {
                    "id": block.block_id,
                    "g": block.granularity,
                    "nodes": block.source_node_refs,
                    "spans": [(span.start_byte, span.end_byte) for span in block.ordered_source_spans],
                    "original": block.original_digest,
                }
                for block in projection.blocks
            ],
            "proof": projection.proof_digest,
        }
    )

def construction_document_digest(document: ConstructionDocument) -> str:
    return stable_digest(
        {
            "generation": document.generation_artifact_uuid,
            "structure_generation": document.structure_generation_artifact_uuid,
            "projection_generation": document.projection_generation_artifact_uuid,
            "structure_digest": document.structure_document_digest,
            "projection_digest": document.projection_digest,
            "units": [
                (unit.unit_id, unit.granularity, unit.coordinate, unit.original.content_full_digest, unit.summary.content_full_digest)
                for unit in document.units
            ],
            "metadata": document.metadata_projection_digest,
            "recipe": document.content_full_recipe_version,
            "proof": document.proof_digest,
        }
    )


def structure_payload(document: StructureDocument) -> dict[str, object]:
    """Return deterministic JSON-ready bytes shape for a structure artifact."""

    return {
        "schema_version": "mkb.structure-document.v1",
        "generation_artifact_uuid": document.generation_artifact_uuid,
        "clean_artifact_uuid": document.clean_artifact_uuid,
        "clean_digest": document.clean_digest,
        "document_root_node_id": document.document_root_node_id,
        "nodes": [
            {
                "node_id": node.node_id,
                "node_kind": node.node_kind,
                "parent_node_id": node.parent_node_id,
                "sibling_ordinal": node.sibling_ordinal,
                "depth": node.depth,
                "reading_ordinal": node.reading_ordinal,
                "content_role": node.content_role,
                "source_anchor": None
                if node.source_anchor is None
                else {"kind": "text_span", "start_byte": node.source_anchor.start_byte, "end_byte": node.source_anchor.end_byte},
                "content_digest": node.content_digest,
                "subtree_digest": node.subtree_digest,
            }
            for node in document.nodes
        ],
        "proof_digest": document.proof_digest,
    }


def retrieval_projection_payload(projection: RetrievalBlockProjection) -> dict[str, object]:
    """Return deterministic JSON-ready bytes shape for a S06 projection artifact."""

    return {
        "schema_version": "mkb.retrieval-block-projection.v1",
        "generation_artifact_uuid": projection.generation_artifact_uuid,
        "structure_generation_artifact_uuid": projection.structure_generation_artifact_uuid,
        "structure_document_digest": projection.structure_document_digest,
        "blocks": [
            {
                "block_id": block.block_id,
                "granularity": block.granularity,
                "source_node_refs": list(block.source_node_refs),
                "ordered_source_spans": [
                    {"start_byte": span.start_byte, "end_byte": span.end_byte} for span in block.ordered_source_spans
                ],
                "original": block.original_text,
                "original_digest": block.original_digest,
            }
            for block in projection.blocks
        ],
        "proof_digest": projection.proof_digest,
    }


def construction_payload(document: ConstructionDocument) -> dict[str, object]:
    """Return deterministic JSON-ready envelope for the S07 document member."""

    return {
        "schema_version": "mkb.construction-document.v1",
        "generation_artifact_uuid": document.generation_artifact_uuid,
        "structure_generation_artifact_uuid": document.structure_generation_artifact_uuid,
        "projection_generation_artifact_uuid": document.projection_generation_artifact_uuid,
        "structure_document_digest": document.structure_document_digest,
        "projection_digest": document.projection_digest,
        "metadata_projection_digest": document.metadata_projection_digest,
        "recipe_version": document.content_full_recipe_version,
        "units": [
            {"unit_id": unit.unit_id, "granularity": unit.granularity, "coordinate": unit.coordinate}
            for unit in document.units
        ],
        "proof_digest": document.proof_digest,
    }


def dual_channel_payload(dual: DualChannelProjection) -> dict[str, object]:
    """Return the strict direct-channel shape accepted by retrieval access.

    This intentionally avoids embedding generated ``content_full`` strings in
    the retrieval hydration contract.  The vector worker receives those only
    through the typed compiler plan and verifies their recipe digest again.
    """

    return {
        "schema_version": "mkb.dual-channel-projection.v1",
        "generation_artifact_uuid": dual.generation_artifact_uuid,
        "recipe_version": "content_full.v1",
        "units": [
            {
                "unit_id": unit.unit_id,
                "granularity": unit.granularity,
                "original": unit.original.body,
                "summary": unit.summary.body,
                "original_digest": unit.original.body_digest,
                "summary_digest": unit.summary.body_digest,
            }
            for unit in dual.units
        ],
    }


def parse_structure_payload(payload: Mapping[str, object]) -> StructureDocument:
    """Parse an immutable S06 structure member without rebuilding a tree."""

    expected_keys = {
        "schema_version",
        "generation_artifact_uuid",
        "clean_artifact_uuid",
        "clean_digest",
        "document_root_node_id",
        "nodes",
        "proof_digest",
    }
    if set(payload) != expected_keys or payload.get("schema_version") != "mkb.structure-document.v1":
        _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen structure payload shape is invalid")
    nodes_raw = payload.get("nodes")
    if not isinstance(nodes_raw, list):
        _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen structure nodes are invalid")
    nodes: list[StructureNode] = []
    node_keys = {
        "node_id",
        "node_kind",
        "parent_node_id",
        "sibling_ordinal",
        "depth",
        "reading_ordinal",
        "content_role",
        "source_anchor",
        "content_digest",
        "subtree_digest",
    }
    for raw in nodes_raw:
        if not isinstance(raw, Mapping) or set(raw) != node_keys:
            _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen structure node shape is invalid")
        span_raw = raw["source_anchor"]
        span: TextSpan | None
        if span_raw is None:
            span = None
        elif isinstance(span_raw, Mapping) and set(span_raw) == {"kind", "start_byte", "end_byte"} and span_raw["kind"] == "text_span":
            span = TextSpan(int(span_raw["start_byte"]), int(span_raw["end_byte"]))
        else:
            _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen structure source anchor is invalid")
        nodes.append(
            StructureNode(
                str(raw["node_id"]),
                str(raw["node_kind"]),
                None if raw["parent_node_id"] is None else str(raw["parent_node_id"]),
                int(raw["sibling_ordinal"]),
                int(raw["depth"]),
                int(raw["reading_ordinal"]),
                str(raw["content_role"]),
                span,
                None if raw["content_digest"] is None else str(raw["content_digest"]),
                str(raw["subtree_digest"]),
            )
        )
    return StructureDocument(
        str(payload["generation_artifact_uuid"]),
        str(payload["clean_artifact_uuid"]),
        str(payload["clean_digest"]),
        str(payload["document_root_node_id"]),
        tuple(nodes),
        str(payload["proof_digest"]),
    )


def parse_retrieval_projection_payload(payload: Mapping[str, object]) -> RetrievalBlockProjection:
    """Parse an immutable S06 projection member without sentence inference."""

    expected_keys = {
        "schema_version",
        "generation_artifact_uuid",
        "structure_generation_artifact_uuid",
        "structure_document_digest",
        "blocks",
        "proof_digest",
    }
    if set(payload) != expected_keys or payload.get("schema_version") != "mkb.retrieval-block-projection.v1":
        _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection payload shape is invalid")
    blocks_raw = payload.get("blocks")
    if not isinstance(blocks_raw, list):
        _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection blocks are invalid")
    blocks: list[RetrievalBlock] = []
    block_keys = {"block_id", "granularity", "source_node_refs", "ordered_source_spans", "original", "original_digest"}
    for raw in blocks_raw:
        if not isinstance(raw, Mapping) or set(raw) != block_keys:
            _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection block shape is invalid")
        refs = raw["source_node_refs"]
        spans_raw = raw["ordered_source_spans"]
        if not isinstance(refs, list) or not all(isinstance(ref, str) for ref in refs) or not isinstance(spans_raw, list):
            _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection references are invalid")
        spans: list[TextSpan] = []
        for span_raw in spans_raw:
            if not isinstance(span_raw, Mapping) or set(span_raw) != {"start_byte", "end_byte"}:
                _fail("STRUCTURE_ARTIFACT_INVALID", "Frozen projection span shape is invalid")
            spans.append(TextSpan(int(span_raw["start_byte"]), int(span_raw["end_byte"])))
        blocks.append(
            RetrievalBlock(
                str(raw["block_id"]),
                int(raw["granularity"]),
                tuple(refs),
                tuple(spans),
                str(raw["original"]),
                str(raw["original_digest"]),
            )
        )
    return RetrievalBlockProjection(
        str(payload["generation_artifact_uuid"]),
        str(payload["structure_generation_artifact_uuid"]),
        str(payload["structure_document_digest"]),
        tuple(blocks),
        str(payload["proof_digest"]),
    )


def summary_plan(projection: RetrievalBlockProjection) -> SummaryPlan:
    """Freeze an ordered S07 plan before an inference caller fills summaries."""

    block_ids = tuple(block.block_id for block in sorted(projection.blocks, key=lambda item: (item.granularity, item.block_id)))
    if not block_ids:
        _fail("CONSTRUCT_KERNEL_EMPTY", "A summary plan requires projection blocks")
    return SummaryPlan(block_ids, stable_digest({"projection": projection_digest(projection), "blocks": block_ids}))


def deterministic_summaries(projection: RetrievalBlockProjection, *, max_chars: int = 480) -> dict[str, str]:
    """Offline deterministic summary implementation for the local profile.

    A production S07 worker normally substitutes an S11 result after freezing
    :func:`summary_plan`; this bounded fallback keeps tests and local operation
    grounded without introducing a hidden fourth prompt.
    """

    if max_chars < 1:
        _fail("CONSTRUCT_BUDGET_INVALID", "Summary character budget must be positive")
    return {
        block.block_id: block.original_text if len(block.original_text) <= max_chars else f"{block.original_text[: max_chars - 1].rstrip()}…"
        for block in projection.blocks
    }
