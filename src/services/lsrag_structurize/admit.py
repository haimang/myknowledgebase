"""Admit a bound S06 candidate through the existing compiler kernel."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass

from src.services.lsrag_compiler import (
    LsragContractCompiler,
    RetrievalBlockProjection,
    StructureDocument,
)
from src.services.lsrag_structurize.binder import StructurizeBinding


@dataclass(frozen=True, slots=True)
class StructurizeAdmitResult:
    accepted_candidate: dict[str, object]
    structure: StructureDocument
    projection: RetrievalBlockProjection
    adoption_report: Mapping[str, object]


def admit_structurize(
    binding: StructurizeBinding,
    *,
    compiler: LsragContractCompiler | None = None,
) -> StructurizeAdmitResult:
    """Preserve the current Mixin sequence: normalize, then adopt-with-report.

    ``adopt_layered_json_with_report`` already calls ``validate_structure``.
    """

    kernel = compiler or LsragContractCompiler()
    accepted_candidate = kernel.normalize_layered_candidate(
        clean_text=binding.clean_text,
        layered_json=binding.layered_candidate,
        granularity_set=binding.granularity_set,
    )
    structure, projection, adoption_report = kernel.adopt_layered_json_with_report(
        clean_text=binding.clean_text,
        layered_json=accepted_candidate,
        generation_artifact_uuid=binding.structure_artifact_uuid,
        projection_generation_artifact_uuid=binding.projection_artifact_uuid,
        clean_artifact_uuid=binding.clean_artifact_uuid,
        clean_digest=binding.clean_digest,
        granularity_set=binding.granularity_set,
    )
    return StructurizeAdmitResult(
        accepted_candidate=accepted_candidate,
        structure=structure,
        projection=projection,
        adoption_report=adoption_report,
    )
