"""Admit a bound S07 construction through the existing compiler kernel."""

from __future__ import annotations

from src.services.lsrag_compiler import ConstructionDocument, DualChannelProjection, LsragContractCompiler
from src.services.lsrag_construct.binder import ConstructBinding


def admit_construct(
    binding: ConstructBinding,
    *,
    compiler: LsragContractCompiler | None = None,
) -> tuple[ConstructionDocument, DualChannelProjection]:
    kernel = compiler or LsragContractCompiler()
    return kernel.construct(
        structure=binding.structure,
        projection=binding.projection,
        clean_text=binding.clean_text,
        construction_generation_artifact_uuid=binding.construction_artifact_uuid,
        dual_channel_generation_artifact_uuid=binding.dual_channel_artifact_uuid,
        summaries_by_block_id=binding.summaries_by_block_id,
        metadata_headers=binding.metadata_headers,
        required_granularities=binding.required_granularities,
    )
