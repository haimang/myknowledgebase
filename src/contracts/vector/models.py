"""Generation-scoped vector and context-only retrieval contracts.

The vector record itself deliberately contains only an embedding and provenance.
Retrieval bodies are referenced through immutable generation artifacts; they are
never copied into a public response as a raw vector or a local filesystem path.
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field, field_validator, model_validator

from src.contracts.common.models import PayloadExtraModel, StrictModel, assert_safe_public_data

VectorizeMode = Literal["from_construct", "purge_generation"]
VectorizeChannelFilter = Literal["all"]


class EmbeddingModelRef(StrictModel):
    """The frozen Layer-A identity carried by an S08 write handoff.

    This is deliberately an identity/binding record, not an adapter request:
    a vectorize contract must never carry a provider token, endpoint, prompt,
    body text, or vector payload.
    """

    model_key: Annotated[str, Field(min_length=1, max_length=256)]
    model_version: Annotated[str, Field(min_length=1, max_length=256)]
    adapter_kind: Annotated[str, Field(min_length=1, max_length=128)]
    dimension: Annotated[int, Field(ge=1, le=65_536)]
    binding_digest: Annotated[str | None, Field(pattern=r"^[0-9a-f]{64}$")] = None

    @model_validator(mode="after")
    def safe_layer_a_identity(self) -> EmbeddingModelRef:
        assert_safe_public_data(self.model_dump())
        return self


class VectorizeCommand(StrictModel):
    """Frozen S08 command material for the single ``lsrag.vectorize`` leaf.

    ``command_input_digest`` is the enclosing S03 Process digest.  The engine
    freezes the immutable input manifest before a Process is materialized, so
    carrying that value here makes a retried S08 command explicitly bound to
    exactly the same process input rather than to a mutable "latest" lookup.
    """

    schema_version: Literal["mkb.vectorize-command.v1"] = "mkb.vectorize-command.v1"
    mode: VectorizeMode
    team_uuid: Annotated[str, Field(min_length=1, max_length=128)]
    execution_uuid: Annotated[str, Field(min_length=1, max_length=128)]
    command_input_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]

    # ``from_construct`` frozen package.
    construction_artifact_uuid: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    construction_content_digest: Annotated[str | None, Field(pattern=r"^[0-9a-f]{64}$")] = None
    dual_channel_generation_artifact_uuid: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    dual_channel_content_digest: Annotated[str | None, Field(pattern=r"^[0-9a-f]{64}$")] = None
    content_full_recipe_version: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    intake_item_uuid: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    intake_revision_uuid: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    namespace_key: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    namespace_uuid: Annotated[str | None, Field(min_length=1, max_length=128)] = None
    embedding_model_ref: EmbeddingModelRef | None = None

    # ``purge_generation`` frozen target set.  The target is a generation
    # coordinate, never a free-form database selector or a source path.
    target_generation_artifact_uuids: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(
        default_factory=list,
        max_length=10_000,
    )
    channel_filter: VectorizeChannelFilter = "all"

    @model_validator(mode="after")
    def enforce_mode_specific_closed_shape(self) -> VectorizeCommand:
        common = {
            "team_uuid": self.team_uuid,
            "execution_uuid": self.execution_uuid,
            "command_input_digest": self.command_input_digest,
        }
        assert_safe_public_data(common)
        construct_fields = (
            self.construction_artifact_uuid,
            self.construction_content_digest,
            self.dual_channel_generation_artifact_uuid,
            self.dual_channel_content_digest,
            self.content_full_recipe_version,
            self.intake_item_uuid,
            self.intake_revision_uuid,
            self.namespace_key,
            self.namespace_uuid,
            self.embedding_model_ref,
        )
        if self.mode == "from_construct":
            if any(value is None for value in construct_fields):
                raise ValueError("from_construct requires a complete frozen construct and Layer-A binding")
            if self.target_generation_artifact_uuids:
                raise ValueError("from_construct cannot carry purge targets")
            if self.channel_filter != "all":
                raise ValueError("from_construct cannot carry a channel filter")
        else:
            if not self.target_generation_artifact_uuids:
                raise ValueError("purge_generation requires at least one target generation")
            if any(value is not None for value in construct_fields):
                raise ValueError("purge_generation cannot carry a construct write package")
            if len(set(self.target_generation_artifact_uuids)) != len(self.target_generation_artifact_uuids):
                raise ValueError("purge_generation targets must be unique")
            if self.target_generation_artifact_uuids != sorted(self.target_generation_artifact_uuids):
                raise ValueError("purge_generation targets must be canonically ordered")
        assert_safe_public_data(self.target_generation_artifact_uuids)
        return self


class VectorizeHandoffV1(StrictModel):
    """S08's write-proof handoff to S09; explicitly not a publication proof."""

    schema_version: Literal["mkb.vectorize-handoff.v1"] = "mkb.vectorize-handoff.v1"
    disposition: Literal["full_valid"] = "full_valid"
    team_uuid: Annotated[str, Field(min_length=1, max_length=128)]
    execution_uuid: Annotated[str, Field(min_length=1, max_length=128)]
    command_input_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    generation_artifact_uuid: Annotated[str, Field(min_length=1, max_length=128)]
    generation_artifact_type: Literal["dual_channel_projection"] = "dual_channel_projection"
    generation_content_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    content_full_recipe_version: Annotated[str, Field(min_length=1, max_length=128)]
    namespace_uuid: Annotated[str, Field(min_length=1, max_length=128)]
    embedding_model_ref: EmbeddingModelRef
    required_units: Annotated[int, Field(ge=1)]
    succeeded_units: Annotated[int, Field(ge=0)]
    skipped_empty_units: Annotated[int, Field(ge=0)] = 0
    failed_units: Annotated[int, Field(ge=0)] = 0

    @model_validator(mode="after")
    def enforce_complete_write_proof(self) -> VectorizeHandoffV1:
        if self.succeeded_units != self.required_units or self.failed_units != 0:
            raise ValueError("a full-valid vector handoff requires every required unit to succeed")
        assert_safe_public_data(self.model_dump())
        return self


class VectorizePurgeReceiptV1(StrictModel):
    """A durable S08 receipt for a generation-scoped logical vector purge."""

    schema_version: Literal["mkb.vectorize-purge-receipt.v1"] = "mkb.vectorize-purge-receipt.v1"
    disposition: Literal["full_valid"] = "full_valid"
    mode: Literal["purge_generation"] = "purge_generation"
    team_uuid: Annotated[str, Field(min_length=1, max_length=128)]
    execution_uuid: Annotated[str, Field(min_length=1, max_length=128)]
    command_input_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    target_generation_artifact_uuids: list[Annotated[str, Field(min_length=1, max_length=128)]] = Field(min_length=1)
    channel_filter: VectorizeChannelFilter
    matched_records: Annotated[int, Field(ge=0)]
    soft_deleted_records: Annotated[int, Field(ge=0)]

    @model_validator(mode="after")
    def enforce_exact_soft_delete_receipt(self) -> VectorizePurgeReceiptV1:
        if self.target_generation_artifact_uuids != sorted(set(self.target_generation_artifact_uuids)):
            raise ValueError("purge receipt targets must be unique and canonically ordered")
        if self.soft_deleted_records != self.matched_records:
            raise ValueError("a full-valid purge receipt must soft-delete its entire matched set")
        assert_safe_public_data(self.model_dump())
        return self


class VectorizeOutcome(StrictModel):
    """The typed S08 outcome payload carried by the generic Process outcome."""

    schema_version: Literal["mkb.vectorize-outcome.v1"] = "mkb.vectorize-outcome.v1"
    disposition: Literal["full_valid"] = "full_valid"
    mode: VectorizeMode
    command_input_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    handoff: VectorizeHandoffV1 | None = None
    purge_receipt: VectorizePurgeReceiptV1 | None = None

    @model_validator(mode="after")
    def enforce_mode_specific_outcome(self) -> VectorizeOutcome:
        if self.mode == "from_construct":
            if self.handoff is None or self.purge_receipt is not None:
                raise ValueError("from_construct requires one VectorizeHandoffV1 and no purge receipt")
            if self.handoff.command_input_digest != self.command_input_digest:
                raise ValueError("handoff command digest does not match the vectorize outcome")
        elif self.purge_receipt is None or self.handoff is not None:
            raise ValueError("purge_generation requires one purge receipt and no S09 handoff")
        elif self.purge_receipt.command_input_digest != self.command_input_digest:
            raise ValueError("purge receipt command digest does not match the vectorize outcome")
        return self


# The formal S08 ledger names the v1 wire shape explicitly while the glossary
# uses the shorter domain nouns.  Keep both spellings as aliases for callers
# that bind contracts by their versioned name.
VectorizeCommandV1 = VectorizeCommand
VectorizeOutcomeV1 = VectorizeOutcome


class GenerationScopedCoordinate(StrictModel):
    """A unit identity which is meaningful only inside its generation."""

    generation_artifact_uuid: str
    unit_id: Annotated[str, Field(min_length=1, max_length=512)]
    granularity: Literal[0, 1, 2]
    channel: Literal["original", "summary"]

    @field_validator("generation_artifact_uuid", "unit_id")
    @classmethod
    def reject_unsafe_coordinate_strings(cls, value: str) -> str:
        assert_safe_public_data(value)
        return value


class VectorizeIntent(PayloadExtraModel):
    schema_version: Literal["mkb.vectorize-intent.v1"]
    team_uuid: str
    execution_uuid: str
    construction_artifact_uuid: str
    construction_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    namespace_key: Annotated[str, Field(min_length=1, max_length=256)] = "default"
    embedding_model: Annotated[str, Field(min_length=1, max_length=256)]
    coordinates: list[GenerationScopedCoordinate] = Field(min_length=1)


class RetrievalBody(StrictModel):
    """Hydrated channel material supplied by a persistence-side body port.

    ``content`` is optional because a deployment may intentionally return an
    opaque logical object reference.  A body port must never return an absolute
    host path.  ``granularity`` lets an artifact implementation supply the
    authoritative, parseable unit granularity when it is not otherwise needed
    as a physical vector column.
    """

    content: Annotated[str | None, Field(max_length=8 * 1024 * 1024)] = None
    content_ref: Annotated[str | None, Field(max_length=2048)] = None
    granularity: Literal[0, 1, 2] | None = None

    @model_validator(mode="after")
    def require_material(self) -> RetrievalBody:
        if self.content is None and self.content_ref is None:
            raise ValueError("a retrieval body requires content or content_ref")
        return self

    @field_validator("content_ref")
    @classmethod
    def reject_absolute_body_ref(cls, value: str | None) -> str | None:
        if value is not None:
            assert_safe_public_data(value)
        return value


class RetrievalGenerationRefs(StrictModel):
    """Minimal auditable lineage attached to each result."""

    intake_item_uuid: str
    intake_revision_uuid: str
    generation_artifact_uuid: str
    generation_artifact_type: str
    namespace_uuid: str
    publication_proof_uuid: str

    @field_validator(
        "intake_item_uuid",
        "intake_revision_uuid",
        "generation_artifact_uuid",
        "generation_artifact_type",
        "namespace_uuid",
        "publication_proof_uuid",
    )
    @classmethod
    def reject_unsafe_reference_strings(cls, value: str) -> str:
        assert_safe_public_data(value)
        return value


class RetrievalResult(StrictModel):
    """A grounded hit/payload record.  It intentionally has no answer/vector."""

    score: float
    ann_score: float
    rerank_score: float | None = None
    hit_channel: Literal["original", "summary"]
    hit_content: str | None = None
    hit_content_ref: str | None = None
    payload_content: str | None = None
    payload_content_ref: str | None = None
    coordinate: GenerationScopedCoordinate
    granularity: Literal[0, 1, 2]
    generation_refs: RetrievalGenerationRefs
    traceback_status: Literal["not_needed", "resolved", "failed", "degraded"]
    context_tier: Literal["focus_fragment", "document_root"]
    filters_echo: dict[str, str]
    inflation_root_content: str | None = None
    inflation_root_content_ref: str | None = None
    # An inflated parent/root is a separate, generation-scoped evidence
    # coordinate.  Reusing the focus coordinate here would falsely label a
    # document root as the matched fragment in a packed context.
    inflation_root_coordinate: GenerationScopedCoordinate | None = None
    inflation_status: Literal["not_requested", "attached", "missing", "truncated", "skipped"] = "not_requested"

    @model_validator(mode="after")
    def require_safe_public_result(self) -> RetrievalResult:
        # The service also redacts body text defensively.  Keeping this model
        # guard makes accidental raw paths/secret-shaped metadata fail closed.
        assert_safe_public_data(
            {
                "hit_content": self.hit_content,
                "hit_content_ref": self.hit_content_ref,
                "payload_content": self.payload_content,
                "payload_content_ref": self.payload_content_ref,
                "inflation_root_content": self.inflation_root_content,
                "inflation_root_content_ref": self.inflation_root_content_ref,
                "inflation_root_coordinate": (
                    None if self.inflation_root_coordinate is None else self.inflation_root_coordinate.model_dump()
                ),
                "coordinate": self.coordinate.model_dump(),
                "generation_refs": self.generation_refs.model_dump(),
                "filters_echo": self.filters_echo,
            }
        )
        if self.inflation_status in {"attached", "truncated"}:
            if self.inflation_root_coordinate is None:
                raise ValueError("an attached inflation root requires its coordinate")
            if (
                self.inflation_root_coordinate.granularity != 0
                or self.inflation_root_coordinate.channel != "original"
            ):
                raise ValueError("an inflation root must be a g=0 original coordinate")
        return self


class PackSegment(StrictModel):
    tier: Literal["focus_fragment", "document_root"]
    coordinate: GenerationScopedCoordinate
    content: str | None = None
    content_ref: str | None = None

    @model_validator(mode="after")
    def require_pack_material(self) -> PackSegment:
        if self.content is None and self.content_ref is None:
            raise ValueError("a pack segment requires content or content_ref")
        assert_safe_public_data(
            {"content": self.content, "content_ref": self.content_ref, "coordinate": self.coordinate.model_dump()}
        )
        return self


class PackView(StrictModel):
    text: str | None = None
    segments: list[PackSegment] = Field(default_factory=list)
    pack_hit_count: Annotated[int, Field(ge=0)]
    pack_char_count: Annotated[int, Field(ge=0)]
    truncated: bool


class RetrievalDiagnostics(StrictModel):
    recall_k: Annotated[int, Field(ge=1)]
    return_k: Annotated[int, Field(ge=1)]
    threshold_applied: float
    ann_hit_count: Annotated[int, Field(ge=0)]
    eligible_count: Annotated[int, Field(ge=0)]
    filtered_count: Annotated[int, Field(ge=0)]
    # ``failed`` is intentionally distinct from ``skipped``: a configured
    # reranker that cannot complete must remain observable while preserving the
    # already-ranked ANN ordering.  ``skipped`` is reserved for a pool too
    # small to rerank.
    rerank_status: Literal["applied", "failed", "skipped", "not_requested"]
    pack_truncated: bool = False
    inflation_truncated: bool = False
    empty_reason: Literal["no_hit", "all_filtered", "below_threshold", "blank_query"] | None = None
    filters_echo: dict[str, str] = Field(default_factory=dict)

    @field_validator("filters_echo")
    @classmethod
    def safe_filters_echo(cls, value: dict[str, str]) -> dict[str, str]:
        assert_safe_public_data(value)
        return value


class RetrievalBundle(StrictModel):
    """The only S10 v1 public result: grounded context, never an answer."""

    schema_version: Literal["mkb.retrieval-result.v1"] = "mkb.retrieval-result.v1"
    disposition: Literal["ok", "empty"]
    team_uuid: str
    query_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    results: list[RetrievalResult] = Field(default_factory=list)
    pack: PackView | None = None
    diagnostics: RetrievalDiagnostics

    @model_validator(mode="after")
    def enforce_bundle_disposition(self) -> RetrievalBundle:
        if self.disposition == "empty" and self.results:
            raise ValueError("an empty retrieval bundle cannot contain results")
        assert_safe_public_data(
            {"team_uuid": self.team_uuid, "pack": None if self.pack is None else self.pack.model_dump()}
        )
        return self


# Compatibility schemas retained for callers that still deserialize the early
# provisional shape.  New S10 code returns ``RetrievalBundle`` above.
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
    traceback_status: Literal["original", "failed", "degraded"]
    source_ref: str

    @model_validator(mode="after")
    def legacy_hit_is_still_safe_public_data(self) -> RetrievalHit:
        assert_safe_public_data(self.model_dump())
        return self


class RetrievalResponse(StrictModel):
    schema_version: Literal["mkb.retrieval-result.v1"] = "mkb.retrieval-result.v1"
    team_uuid: str
    query_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    hits: list[RetrievalHit]
    empty: bool
    rerank_status: Literal["not_requested", "applied", "failed", "skipped"]

    @model_validator(mode="after")
    def empty_matches_hits(self) -> RetrievalResponse:
        if self.empty != (len(self.hits) == 0):
            raise ValueError("empty must exactly reflect hits")
        return self


__all__ = [
    "EmbeddingModelRef",
    "GenerationScopedCoordinate",
    "PackSegment",
    "PackView",
    "RetrievalBody",
    "RetrievalBundle",
    "RetrievalDiagnostics",
    "RetrievalGenerationRefs",
    "RetrievalHit",
    "RetrievalResponse",
    "RetrievalResult",
    "VectorizeIntent",
    "VectorizeChannelFilter",
    "VectorizeCommand",
    "VectorizeCommandV1",
    "VectorizeHandoffV1",
    "VectorizeMode",
    "VectorizeOutcome",
    "VectorizeOutcomeV1",
    "VectorizePurgeReceiptV1",
]
