"""S07 construct leaf facade.  No I/O, no adapters."""

from __future__ import annotations

from collections.abc import Mapping

from src.services.lsrag_compiler import (
    ConstructionDocument,
    DualChannelProjection,
    LsragContractCompiler,
    RetrievalBlockProjection,
    StructureDocument,
)
from src.services.lsrag_construct.admit import admit_construct
from src.services.lsrag_construct.binder import ConstructBinding
from src.services.lsrag_construct.reconstruct import (
    assert_construction_contract_bytes,
    assert_structure_contract_bytes,
    reprove_structure_from_candidate,
    reprove_structure_from_stored_payloads,
)


class LsragConstructService:
    """Re-prove S06 handoff and admit S07 construction packages."""

    def __init__(self, compiler: LsragContractCompiler | None = None) -> None:
        self._compiler = compiler or LsragContractCompiler()

    def admit(self, binding: ConstructBinding) -> tuple[ConstructionDocument, DualChannelProjection]:
        return admit_construct(binding, compiler=self._compiler)

    def reprove_structure_from_candidate(
        self,
        *,
        clean_text: str,
        layered_candidate: Mapping[str, object],
        granularity_set: tuple[int, ...] | list[int],
        structure_artifact_uuid: str,
        projection_artifact_uuid: str,
        clean_artifact_uuid: str,
        clean_digest: str,
    ) -> tuple[LsragContractCompiler, StructureDocument, RetrievalBlockProjection]:
        return reprove_structure_from_candidate(
            clean_text=clean_text,
            layered_candidate=layered_candidate,
            granularity_set=granularity_set,
            structure_artifact_uuid=structure_artifact_uuid,
            projection_artifact_uuid=projection_artifact_uuid,
            clean_artifact_uuid=clean_artifact_uuid,
            clean_digest=clean_digest,
            compiler=self._compiler,
        )

    def reprove_structure_from_stored_payloads(
        self,
        *,
        clean_text: str,
        structure_data: str | bytes,
        projection_data: str | bytes,
        error_code: str = "METADATA_REFRESH_SOURCE_INVALID",
    ) -> tuple[LsragContractCompiler, StructureDocument, RetrievalBlockProjection]:
        return reprove_structure_from_stored_payloads(
            clean_text=clean_text,
            structure_data=structure_data,
            projection_data=projection_data,
            compiler=self._compiler,
            error_code=error_code,
        )

    def assert_structure_bytes(
        self,
        *,
        structure: StructureDocument,
        projection: RetrievalBlockProjection,
        structure_data: str | bytes,
        projection_data: str | bytes,
        structure_digest: str | None,
        projection_digest_value: str | None,
        mismatch_code: str = "CONSTRUCT_BINDING_DIGEST",
    ) -> None:
        assert_structure_contract_bytes(
            structure=structure,
            projection=projection,
            structure_data=structure_data,
            projection_data=projection_data,
            structure_digest=structure_digest,
            projection_digest_value=projection_digest_value,
            mismatch_code=mismatch_code,
        )

    def assert_construction_bytes(
        self,
        *,
        construction: ConstructionDocument,
        dual: DualChannelProjection,
        construction_data: str | bytes,
        dual_data: str | bytes,
        construction_digest: str | None = None,
        mismatch_code: str = "CONSTRUCT_TO_VECTORIZE_GATE",
    ) -> None:
        assert_construction_contract_bytes(
            construction=construction,
            dual=dual,
            construction_data=construction_data,
            dual_data=dual_data,
            construction_digest=construction_digest,
            mismatch_code=mismatch_code,
        )
