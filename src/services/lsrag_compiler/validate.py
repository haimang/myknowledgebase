"""Structure and construction validators."""

from __future__ import annotations

from collections.abc import Mapping

from src.services.lsrag_compiler.models import (
    _CHANNELS,
    _NODE_KINDS,
    ConstructionDocument,
    DualChannelProjection,
    RetrievalBlockProjection,
    StructureDocument,
    StructureNode,
    TextSpan,
    _fail,
    _span_text,
    _text_digest,
    content_full,
)
from src.services.lsrag_compiler.payloads import construction_document_digest, structure_document_digest


def validate_structure(
    *,
    document: StructureDocument,
    projection: RetrievalBlockProjection,
    clean_text: str,
    required_granularities: frozenset[int] = frozenset({0, 1, 2}),
) -> None:
    if document.clean_digest != _text_digest(clean_text):
        _fail("STRUCTURE_BINDING_CLEAN_DIGEST", "The structure is not bound to these clean bytes")
    if (
        projection.structure_generation_artifact_uuid != document.generation_artifact_uuid
        or projection.generation_artifact_uuid == document.generation_artifact_uuid
    ):
        _fail("STRUCTURE_BINDING_CROSS_GENERATION", "Structure and projection generations differ")
    if projection.structure_document_digest != structure_document_digest(document):
        _fail("STRUCTURE_BINDING_DIGEST", "Projection does not bind this exact structure document")
    roots = [node for node in document.nodes if node.parent_node_id is None]
    if len(roots) != 1 or roots[0].node_id != document.document_root_node_id or roots[0].node_kind != "document":
        _fail("STRUCTURE_TREE_ROOT", "Structure documents require exactly one document root")
    ids = {node.node_id for node in document.nodes}
    if len(ids) != len(document.nodes):
        _fail("STRUCTURE_TREE_DUPLICATE_NODE", "Structure node identities must be unique")
    if any(node.node_kind not in _NODE_KINDS for node in document.nodes):
        _fail("STRUCTURE_NODE_KIND_INVALID", "Structure node kind is not in the schema closed set")
    if [node.reading_ordinal for node in document.nodes] != list(range(len(document.nodes))):
        _fail("STRUCTURE_ORDER_INVALID", "Structure reading order must be complete and contiguous")
    children: dict[str, list[StructureNode]] = {}
    for node in document.nodes:
        if node.parent_node_id is not None:
            if node.parent_node_id not in ids:
                _fail("STRUCTURE_TREE_PARENT", "Structure node has an unknown parent")
            children.setdefault(node.parent_node_id, []).append(node)
            parent = next(candidate for candidate in document.nodes if candidate.node_id == node.parent_node_id)
            if node.depth != parent.depth + 1:
                _fail("STRUCTURE_TREE_DEPTH", "Structure node depth is inconsistent")
    for members in children.values():
        if sorted(member.sibling_ordinal for member in members) != list(range(len(members))):
            _fail("STRUCTURE_ORDER_INVALID", "Sibling ordinals must be contiguous")
    leaves = [node for node in document.nodes if node.node_id not in children]
    spans: list[TextSpan] = []
    for leaf in leaves:
        if leaf.content_role == "content":
            if leaf.source_anchor is None:
                _fail("STRUCTURE_ANCHOR_MISSING", "Content leaves require exact clean anchors")
            anchored = _span_text(clean_text, leaf.source_anchor.start_byte, leaf.source_anchor.end_byte)
            if leaf.content_digest != _text_digest(anchored):
                _fail("STRUCTURE_ANCHOR_DIGEST", "Content leaf digest does not match its anchor")
            spans.append(leaf.source_anchor)
    # The content leaves are the authoritative partition of the admitted
    # clean bytes.  Checking only min/max would accept a tree that skips
    # or duplicates bytes in the middle, which makes later reattachment
    # ambiguous.  Preserve tree reading order rather than normalising it:
    # an out-of-order candidate is invalid kernel output, not something a
    # worker may silently repair.
    expected_start = 0
    for span in spans:
        _span_text(clean_text, span.start_byte, span.end_byte)
        if span.start_byte != expected_start or span.end_byte <= span.start_byte:
            _fail("STRUCTURE_COVERAGE_INVALID", "Content leaf anchors must be an ordered, gap-free clean-byte partition")
        expected_start = span.end_byte
    if not spans or expected_start != len(clean_text.encode("utf-8")):
        _fail("STRUCTURE_COVERAGE_INVALID", "Content leaf anchors must cover the selected clean artifact")
    block_ids: set[str] = set()
    granularities: set[int] = set()
    for block in projection.blocks:
        if block.block_id in block_ids or block.granularity not in {0, 1, 2} or not block.source_node_refs or not block.ordered_source_spans:
            _fail("STRUCTURE_PROJECTION_INVALID", "Projection block shape is invalid")
        block_ids.add(block.block_id)
        granularities.add(block.granularity)
        if any(node_id not in ids for node_id in block.source_node_refs):
            _fail("STRUCTURE_PROJECTION_NODE", "Projection block references an unknown structure node")
        previous_end = -1
        pieces: list[str] = []
        for span in block.ordered_source_spans:
            if span.start_byte < previous_end or span.end_byte <= span.start_byte:
                _fail("STRUCTURE_PROJECTION_ORDER", "Projection source spans must be ordered and non-overlapping")
            pieces.append(_span_text(clean_text, span.start_byte, span.end_byte))
            previous_end = span.end_byte
        original = "".join(pieces)
        if original != block.original_text or block.original_digest != _text_digest(original):
            _fail("STRUCTURE_PROJECTION_ORIGINAL", "Projection original body is not an anchored clean slice")
    if granularities != set(required_granularities) or not any(
        block.granularity == 0 and block.original_text.strip() for block in projection.blocks
    ):
        _fail("STRUCTURE_PROJECTION_G0_REQUIRED", "Projection granularities do not match the frozen profile")

def validate_construction(
    *,
    document: ConstructionDocument,
    dual: DualChannelProjection,
    metadata_headers: Mapping[str, str] | None = None,
) -> None:
    if (
        document.generation_artifact_uuid != dual.construction_generation_artifact_uuid
        or document.generation_artifact_uuid == dual.generation_artifact_uuid
        or document.structure_generation_artifact_uuid == document.projection_generation_artifact_uuid
        or dual.construction_document_digest != construction_document_digest(document)
    ):
        _fail("CONSTRUCT_BINDING_DIGEST", "Dual-channel projection does not bind this construction document")
    if not document.units or tuple(unit.unit_id for unit in document.units) != tuple(unit.unit_id for unit in dual.units):
        _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "Construction and dual-channel units must align 1:1")
    g0_original = False
    for unit in dual.units:
        if unit.original.channel != "original" or unit.summary.channel != "summary" or not unit.coordinate:
            _fail("CONSTRUCT_KERNEL_ALIGNMENT_INVALID", "Construction unit channel identities are invalid")
        for channel in (unit.original, unit.summary):
            if channel.channel not in _CHANNELS or channel.grounds_coordinate != unit.coordinate or not channel.body.strip():
                _fail("CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE", "Construction channels must be non-empty and grounded")
            recomputed = content_full(body=channel.body, metadata_headers=metadata_headers, recipe_version=document.content_full_recipe_version)
            if recomputed != channel.content_full or channel.content_full_digest != _text_digest(recomputed):
                _fail("CONSTRUCT_CONTENT_MISMATCH", "A content_full recipe digest does not match its channel body")
        if unit.granularity == 0 and unit.original.body.strip() and unit.original.reattach_status in {"reattached", "native_full"}:
            g0_original = True
    if not g0_original:
        _fail("CONSTRUCT_G0_ORIGINAL_REQUIRED", "Full-valid construction requires a reattached g0 original")
