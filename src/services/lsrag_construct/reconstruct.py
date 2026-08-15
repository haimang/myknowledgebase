"""Re-prove frozen S06/S07 bytes without I/O."""

from __future__ import annotations

import json
from collections.abc import Mapping

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json
from src.services.lsrag_compiler import (
    ConstructionDocument,
    DualChannelProjection,
    LsragContractCompiler,
    RetrievalBlockProjection,
    StructureDocument,
    construction_document_digest,
    construction_payload,
    dual_channel_payload,
    parse_retrieval_projection_payload,
    parse_structure_payload,
    projection_digest,
    retrieval_projection_payload,
    structure_document_digest,
    structure_payload,
)


def reprove_structure_from_candidate(
    *,
    clean_text: str,
    layered_candidate: Mapping[str, object],
    granularity_set: tuple[int, ...] | list[int],
    structure_artifact_uuid: str,
    projection_artifact_uuid: str,
    clean_artifact_uuid: str,
    clean_digest: str,
    compiler: LsragContractCompiler | None = None,
) -> tuple[LsragContractCompiler, StructureDocument, RetrievalBlockProjection]:
    kernel = compiler or LsragContractCompiler()
    structure, projection = kernel.adopt_layered_json(
        clean_text=clean_text,
        layered_json=layered_candidate,
        generation_artifact_uuid=structure_artifact_uuid,
        projection_generation_artifact_uuid=projection_artifact_uuid,
        clean_artifact_uuid=clean_artifact_uuid,
        clean_digest=clean_digest,
        granularity_set=granularity_set,
    )
    return kernel, structure, projection


def assert_structure_contract_bytes(
    *,
    structure: StructureDocument,
    projection: RetrievalBlockProjection,
    structure_data: str | bytes,
    projection_data: str | bytes,
    structure_digest: str | None,
    projection_digest_value: str | None,
    mismatch_code: str = "CONSTRUCT_BINDING_DIGEST",
) -> None:
    expected_structure = canonical_json(structure_payload(structure))
    expected_projection = canonical_json(retrieval_projection_payload(projection))
    if structure_data != expected_structure or projection_data != expected_projection:
        raise MkbError(mismatch_code, "Structure/projection bytes do not match their generation-local contract", 409)
    if (
        structure_digest is not None
        and structure_digest != structure_document_digest(structure)
    ) or (
        projection_digest_value is not None
        and projection_digest_value != projection_digest(projection)
    ):
        raise MkbError(mismatch_code, "Structure/projection semantic digests do not match the frozen handoff", 409)


def reprove_structure_from_stored_payloads(
    *,
    clean_text: str,
    structure_data: str | bytes,
    projection_data: str | bytes,
    compiler: LsragContractCompiler | None = None,
    error_code: str = "METADATA_REFRESH_SOURCE_INVALID",
) -> tuple[LsragContractCompiler, StructureDocument, RetrievalBlockProjection]:
    kernel = compiler or LsragContractCompiler()
    try:
        structure_payload_value = json.loads(structure_data)
        projection_payload_value = json.loads(projection_data)
        if not isinstance(structure_payload_value, Mapping) or not isinstance(projection_payload_value, Mapping):
            raise ValueError("generation members must be objects")
        structure = parse_structure_payload(structure_payload_value)
        projection = parse_retrieval_projection_payload(projection_payload_value)
        kernel.validate_structure(
            document=structure,
            projection=projection,
            clean_text=clean_text,
            required_granularities=frozenset(block.granularity for block in projection.blocks),
        )
    except (TypeError, ValueError, KeyError, json.JSONDecodeError, MkbError) as exc:
        raise MkbError(error_code, "Frozen source structure members cannot be re-proven", 409) from exc
    if (
        structure_data != canonical_json(structure_payload(structure))
        or projection_data != canonical_json(retrieval_projection_payload(projection))
    ):
        raise MkbError(
            error_code,
            "Frozen source structure bytes do not bind the inherited clean artifact",
            409,
        )
    return kernel, structure, projection


def assert_construction_contract_bytes(
    *,
    construction: ConstructionDocument,
    dual: DualChannelProjection,
    construction_data: str | bytes,
    dual_data: str | bytes,
    construction_digest: str | None = None,
    mismatch_code: str = "CONSTRUCT_TO_VECTORIZE_GATE",
) -> None:
    if construction_data != canonical_json(construction_payload(construction)) or dual_data != canonical_json(
        dual_channel_payload(dual)
    ):
        raise MkbError(mismatch_code, "Construct bytes do not match the exact full-valid generation", 409)
    if construction_digest is not None and construction_digest != construction_document_digest(construction):
        raise MkbError(mismatch_code, "Construction semantic digest does not match the frozen handoff", 409)
