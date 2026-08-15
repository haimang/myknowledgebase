"""Pure deterministic compiler facade for the accepted S06--S08 artifact shapes."""

from __future__ import annotations

from collections.abc import Mapping

from src.services.lsrag_compiler.adopt import (
    adopt_layered_json as _adopt_layered_json,
)
from src.services.lsrag_compiler.adopt import (
    adopt_layered_json_with_report as _adopt_layered_json_with_report,
)
from src.services.lsrag_compiler.adopt import declared_granularities, project_blocks
from src.services.lsrag_compiler.adopt import fill_layered_summaries as _fill_layered_summaries
from src.services.lsrag_compiler.adopt import layered_summary_map as _layered_summary_map
from src.services.lsrag_compiler.adopt import (
    normalize_layered_candidate as _normalize_layered_candidate,
)
from src.services.lsrag_compiler.adopt import structurize as _structurize
from src.services.lsrag_compiler.construct import construct as _construct
from src.services.lsrag_compiler.construct import vectorization_plan as _vectorization_plan
from src.services.lsrag_compiler.models import (
    ConstructionDocument,
    DualChannelProjection,
    RetrievalBlockProjection,
    StructureDocument,
    VectorizationPlan,
)
from src.services.lsrag_compiler.validate import validate_construction, validate_structure


class LsragContractCompiler:
    """Pure deterministic compiler for the accepted S06--S08 artifact shapes."""

    @staticmethod
    def _declared_granularities(granularity_set: tuple[int, ...] | list[int] | None) -> tuple[int, ...]:
        return declared_granularities(granularity_set)

    def normalize_layered_candidate(
        self,
        *,
        clean_text: str,
        layered_json: Mapping[str, object],
        granularity_set: tuple[int, ...] | list[int] | None = None,
    ) -> dict[str, object]:
        return _normalize_layered_candidate(
            clean_text=clean_text,
            layered_json=layered_json,
            granularity_set=granularity_set,
        )

    def structurize(
        self,
        *,
        clean_text: str,
        generation_artifact_uuid: str,
        projection_generation_artifact_uuid: str | None = None,
        clean_artifact_uuid: str,
        clean_digest: str | None = None,
    ) -> tuple[StructureDocument, RetrievalBlockProjection]:
        return _structurize(
            clean_text=clean_text,
            generation_artifact_uuid=generation_artifact_uuid,
            projection_generation_artifact_uuid=projection_generation_artifact_uuid,
            clean_artifact_uuid=clean_artifact_uuid,
            clean_digest=clean_digest,
        )

    def adopt_layered_json(
        self,
        *,
        clean_text: str,
        layered_json: Mapping[str, object],
        generation_artifact_uuid: str,
        projection_generation_artifact_uuid: str | None = None,
        clean_artifact_uuid: str,
        clean_digest: str | None = None,
        granularity_set: tuple[int, ...] | list[int] | None = None,
    ) -> tuple[StructureDocument, RetrievalBlockProjection]:
        return _adopt_layered_json(
            clean_text=clean_text,
            layered_json=layered_json,
            generation_artifact_uuid=generation_artifact_uuid,
            projection_generation_artifact_uuid=projection_generation_artifact_uuid,
            clean_artifact_uuid=clean_artifact_uuid,
            clean_digest=clean_digest,
            granularity_set=granularity_set,
        )

    def adopt_layered_json_with_report(
        self,
        *,
        clean_text: str,
        layered_json: Mapping[str, object],
        generation_artifact_uuid: str,
        projection_generation_artifact_uuid: str | None = None,
        clean_artifact_uuid: str,
        clean_digest: str | None = None,
        granularity_set: tuple[int, ...] | list[int] | None = None,
    ) -> tuple[StructureDocument, RetrievalBlockProjection, dict[str, object]]:
        return _adopt_layered_json_with_report(
            clean_text=clean_text,
            layered_json=layered_json,
            generation_artifact_uuid=generation_artifact_uuid,
            projection_generation_artifact_uuid=projection_generation_artifact_uuid,
            clean_artifact_uuid=clean_artifact_uuid,
            clean_digest=clean_digest,
            granularity_set=granularity_set,
        )

    @staticmethod
    def layered_summary_map(
        *,
        layered_json: Mapping[str, object],
        projection: RetrievalBlockProjection,
        accepted_layered_json: Mapping[str, object] | None = None,
    ) -> dict[str, str]:
        return _layered_summary_map(
            layered_json=layered_json,
            projection=projection,
            accepted_layered_json=accepted_layered_json,
        )

    @staticmethod
    def fill_layered_summaries(
        *,
        accepted_layered_json: Mapping[str, object],
        projection: RetrievalBlockProjection,
        summaries_by_block_id: Mapping[str, str],
    ) -> dict[str, object]:
        return _fill_layered_summaries(
            accepted_layered_json=accepted_layered_json,
            projection=projection,
            summaries_by_block_id=summaries_by_block_id,
        )

    def _project_blocks(self, *, clean_text: str, generation_artifact_uuid: str, leaf_id: str):
        return project_blocks(
            clean_text=clean_text,
            generation_artifact_uuid=generation_artifact_uuid,
            leaf_id=leaf_id,
        )

    def validate_structure(
        self,
        *,
        document: StructureDocument,
        projection: RetrievalBlockProjection,
        clean_text: str,
        required_granularities: frozenset[int] = frozenset({0, 1, 2}),
    ) -> None:
        validate_structure(
            document=document,
            projection=projection,
            clean_text=clean_text,
            required_granularities=required_granularities,
        )

    def validate_construction(
        self,
        *,
        document: ConstructionDocument,
        dual: DualChannelProjection,
        metadata_headers: Mapping[str, str] | None = None,
    ) -> None:
        validate_construction(document=document, dual=dual, metadata_headers=metadata_headers)

    def construct(
        self,
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
        return _construct(
            structure=structure,
            projection=projection,
            clean_text=clean_text,
            construction_generation_artifact_uuid=construction_generation_artifact_uuid,
            dual_channel_generation_artifact_uuid=dual_channel_generation_artifact_uuid,
            summaries_by_block_id=summaries_by_block_id,
            metadata_headers=metadata_headers,
            recipe_version=recipe_version,
            required_granularities=required_granularities,
        )

    def vectorization_plan(
        self,
        *,
        document: ConstructionDocument,
        dual: DualChannelProjection,
        metadata_headers: Mapping[str, str] | None = None,
        max_content_full_bytes: int = 8 * 1024 * 1024,
    ) -> VectorizationPlan:
        return _vectorization_plan(
            document=document,
            dual=dual,
            metadata_headers=metadata_headers,
            max_content_full_bytes=max_content_full_bytes,
        )
