"""Pure S07 construct input binding.  No I/O."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Literal

from src.contracts.common.errors import MkbError
from src.services.lsrag_compiler import RetrievalBlockProjection, StructureDocument

ConstructMode = Literal["full_construct", "metadata_refresh"]


@dataclass(frozen=True, slots=True)
class ConstructBinding:
    mode: ConstructMode
    clean_text: str
    structure: StructureDocument
    projection: RetrievalBlockProjection
    summaries_by_block_id: Mapping[str, str]
    construction_artifact_uuid: str
    dual_channel_artifact_uuid: str
    metadata_headers: Mapping[str, str] | None
    required_granularities: frozenset[int]


def bind_construct(
    *,
    mode: str,
    clean_text: str,
    structure: StructureDocument,
    projection: RetrievalBlockProjection,
    summaries_by_block_id: Mapping[str, str] | None,
    construction_artifact_uuid: str,
    dual_channel_artifact_uuid: str,
    metadata_headers: Mapping[str, str] | None = None,
    required_granularities: frozenset[int] | None = None,
) -> ConstructBinding:
    if mode not in {"full_construct", "metadata_refresh"}:
        raise MkbError("CONSTRUCT_MODE_INVALID", "Construction mode is not registered", 409)
    if not isinstance(clean_text, str) or not clean_text.strip():
        raise MkbError("CONSTRUCT_BINDING_CLEAN_DIGEST", "A construction requires non-empty clean text", 422)
    if not construction_artifact_uuid or not dual_channel_artifact_uuid:
        raise MkbError("CONSTRUCT_BINDING_INVALID", "Construction generation identity is required", 422)
    if construction_artifact_uuid == dual_channel_artifact_uuid:
        raise MkbError("CONSTRUCT_BINDING_INVALID", "Construction and dual-channel artifact identities must be distinct", 422)
    if not isinstance(summaries_by_block_id, Mapping) or not summaries_by_block_id:
        raise MkbError("CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE", "Every non-empty original projection block needs a grounded summary", 422)
    if mode == "full_construct" and metadata_headers is not None:
        raise MkbError("CONSTRUCT_MODE_INVALID", "full_construct does not take metadata headers", 409)
    granularities = required_granularities or frozenset(block.granularity for block in projection.blocks)
    return ConstructBinding(
        mode=mode,  # type: ignore[arg-type]
        clean_text=clean_text,
        structure=structure,
        projection=projection,
        summaries_by_block_id=summaries_by_block_id,
        construction_artifact_uuid=construction_artifact_uuid,
        dual_channel_artifact_uuid=dual_channel_artifact_uuid,
        metadata_headers=None if mode == "full_construct" else metadata_headers,
        required_granularities=granularities,
    )
