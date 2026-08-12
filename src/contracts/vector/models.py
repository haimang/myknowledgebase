"""Generation-scoped vector and context-only retrieval contracts."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, model_validator

from src.contracts.common.models import PayloadExtraModel, StrictModel


class GenerationScopedCoordinate(StrictModel):
    generation_artifact_uuid: str
    unit_id: Annotated[str, Field(min_length=1, max_length=512)]
    granularity: Literal[0, 1, 2]
    channel: Literal["original", "summary"]


class VectorizeIntent(PayloadExtraModel):
    schema_version: Literal["mkb.vectorize-intent.v1"]
    team_uuid: str
    execution_uuid: str
    construction_artifact_uuid: str
    construction_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    namespace_key: Annotated[str, Field(min_length=1, max_length=256)] = "default"
    embedding_model: Annotated[str, Field(min_length=1, max_length=256)]
    coordinates: list[GenerationScopedCoordinate] = Field(min_length=1)


class RetrievalHit(StrictModel):
    intake_item_uuid: str
    intake_revision_uuid: str
    generation_artifact_uuid: str
    unit_id: str
    channel: Literal["original", "summary"]
    granularity: Literal[0, 1, 2]
    score: float
    context: str
    original_context: str | None = None
    traceback_status: Literal["original", "degraded", "unavailable"]
    source_ref: str


class RetrievalResponse(StrictModel):
    schema_version: Literal["mkb.retrieval-result.v1"] = "mkb.retrieval-result.v1"
    team_uuid: str
    query_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    hits: list[RetrievalHit]
    empty: bool
    rerank_status: Literal["not_requested", "applied", "unavailable"]

    @model_validator(mode="after")
    def empty_matches_hits(self) -> RetrievalResponse:
        if self.empty != (len(self.hits) == 0):
            raise ValueError("empty must exactly reflect hits")
        return self
