"""Construction and vectorization plan helpers."""

from __future__ import annotations

from collections.abc import Mapping

from src.contracts.common.ids import stable_digest
from src.services.lsrag_compiler.models import (
    ChannelRecord,
    ConstructionDocument,
    ConstructionUnit,
    DualChannelProjection,
    RetrievalBlockProjection,
    StructureDocument,
    VectorizationPlan,
    VectorizationUnit,
    _fail,
    _text_digest,
    content_full,
)
from src.services.lsrag_compiler.payloads import (
    construction_document_digest,
    projection_digest,
    structure_document_digest,
)
from src.services.lsrag_compiler.validate import validate_construction, validate_structure


def construct(
    *,
    structure: StructureDocument,
    projection: RetrievalBlockProjection,
    clean_text: str,
    construction_generation_artifact_uuid: str,
    dual_channel_generation_artifact_uuid: str | None = None,
    summaries_by_block_id: Mapping[str, str],
    metadata_headers: Mapping[str, str] | None = None,
    recipe_version: str = "content_full.v1",
    required_granularities: frozenset[int] | None = None,
) -> tuple[ConstructionDocument, DualChannelProjection]:
    expected_granularities = required_granularities or frozenset(block.granularity for block in projection.blocks)
    validate_structure(
        document=structure,
        projection=projection,
        clean_text=clean_text,
        required_granularities=expected_granularities,
    )
    dual_channel_generation_artifact_uuid = dual_channel_generation_artifact_uuid or f"{construction_generation_artifact_uuid}:dual"
    if not construction_generation_artifact_uuid or not dual_channel_generation_artifact_uuid:
        _fail("CONSTRUCT_BINDING_INVALID", "Construction generation identity is required")
    if dual_channel_generation_artifact_uuid == construction_generation_artifact_uuid:
        _fail("CONSTRUCT_BINDING_INVALID", "Construction and dual-channel artifact identities must be distinct")
    units: list[ConstructionUnit] = []
    for block in projection.blocks:
        summary = summaries_by_block_id.get(block.block_id)
        if not isinstance(summary, str) or not summary.strip():
            _fail("CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE", "Every non-empty original projection block needs a grounded summary")
        coordinate = f"{structure.generation_artifact_uuid}:{projection.generation_artifact_uuid}:{block.block_id}"
        original_full = content_full(body=block.original_text, metadata_headers=metadata_headers, recipe_version=recipe_version)
        summary_full = content_full(body=summary, metadata_headers=metadata_headers, recipe_version=recipe_version)
        units.append(
            ConstructionUnit(
                block.block_id,
                block.granularity,
                coordinate,
                ChannelRecord("original", block.original_text, block.original_digest, original_full, _text_digest(original_full), coordinate, "native_full" if block.granularity == 0 else "reattached"),
                ChannelRecord("summary", summary, _text_digest(summary), summary_full, _text_digest(summary_full), coordinate, "not_applicable"),
            )
        )
    metadata_digest = stable_digest(dict(sorted((metadata_headers or {}).items())))
    provisional = ConstructionDocument(
        construction_generation_artifact_uuid,
        structure.generation_artifact_uuid,
        projection.generation_artifact_uuid,
        structure_document_digest(structure),
        projection_digest(projection),
        tuple(units),
        metadata_digest,
        recipe_version,
        "",
    )
    proof = stable_digest({"alignment": [(unit.unit_id, unit.coordinate) for unit in units], "full_valid": True, "g0": True})
    document = ConstructionDocument(
        provisional.generation_artifact_uuid, provisional.structure_generation_artifact_uuid, provisional.projection_generation_artifact_uuid,
        provisional.structure_document_digest, provisional.projection_digest, provisional.units, provisional.metadata_projection_digest,
        provisional.content_full_recipe_version, proof,
    )
    dual = DualChannelProjection(
        dual_channel_generation_artifact_uuid,
        construction_generation_artifact_uuid,
        construction_document_digest(document),
        tuple(units),
        stable_digest({"units": [(unit.unit_id, unit.original.content_full_digest, unit.summary.content_full_digest) for unit in units]}),
    )
    validate_construction(document=document, dual=dual, metadata_headers=metadata_headers)
    return document, dual

def vectorization_plan(
    *,
    document: ConstructionDocument,
    dual: DualChannelProjection,
    metadata_headers: Mapping[str, str] | None = None,
    max_content_full_bytes: int = 8 * 1024 * 1024,
) -> VectorizationPlan:
    validate_construction(document=document, dual=dual, metadata_headers=metadata_headers)
    if max_content_full_bytes < 1:
        _fail("VECTORIZE_BUDGET_INVALID", "Vectorization byte budget must be positive")
    required: list[VectorizationUnit] = []
    skipped: list[str] = []
    g0_original_ready = False
    for unit in dual.units:
        for channel in (unit.original, unit.summary):
            recomputed = content_full(body=channel.body, metadata_headers=metadata_headers, recipe_version=document.content_full_recipe_version)
            if channel.content_full_digest != _text_digest(recomputed) or channel.content_full != recomputed:
                _fail("VECTORIZE_CONTENT_MISMATCH", "Vectorization must recompute and verify content_full")
            if unit.granularity == 0 and channel.channel == "original":
                if recomputed.strip() and unit.original.reattach_status in {"reattached", "native_full"}:
                    g0_original_ready = True
                continue
            if not recomputed.strip():
                skipped.append(f"{unit.unit_id}:{channel.channel}")
                continue
            if len(recomputed.encode("utf-8")) > max_content_full_bytes:
                _fail("VECTORIZE_BUDGET_CONTENT_FULL", "A vectorization input exceeds the configured byte budget")
            required.append(VectorizationUnit(unit.unit_id, unit.granularity, channel.channel, unit.coordinate, recomputed, _text_digest(recomputed)))
    required.sort(key=lambda item: (item.granularity, item.unit_id, item.channel))
    if not g0_original_ready:
        _fail("ORIGINAL_NOT_REATTACHED", "Vectorize requires a reattached non-empty g0 original in construct; that channel is not a vector unit")
    if not any(item.granularity == 0 and item.channel == "summary" and item.content_full.strip() for item in required):
        _fail("G0_SUMMARY_REQUIRED", "Non-empty g0 summary must remain a required vectorization unit")
    return VectorizationPlan(tuple(required), tuple(sorted(skipped)), stable_digest([item.content_full_digest for item in required]))
