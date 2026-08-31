"""Strict public Task, Team, gate, and retrieval contracts (S01/S02/S10)."""

from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import validate_external_uuid
from src.contracts.common.models import (
    ErrorEnvelope,
    PayloadExtraModel,
    StrictModel,
    assert_safe_public_data,
)
from src.contracts.common.time import normalize_rfc3339


def _uuid(value: str, field: str) -> str:
    try:
        return validate_external_uuid(value, field=field)
    except Exception as exc:
        raise ValueError(str(exc)) from exc


def _semantic_text(value: str, field: str) -> str:
    normalized = value.strip()
    if not normalized or normalized.casefold() == "unknown":
        raise ValueError(f"{field} must be non-empty and cannot be unknown")
    return normalized


class GenericSemanticSource(PayloadExtraModel):
    observation_key: Annotated[str | None, Field(min_length=1, max_length=1024)] = None
    retry_failed_observation: bool = False
    expected_observation_attempt_generation: Annotated[int | None, Field(ge=1)] = None
    realm: Annotated[str, Field(min_length=1, max_length=256)]
    type: Annotated[str, Field(min_length=1, max_length=256)]
    channel: Annotated[str, Field(min_length=1, max_length=256)]
    source_name: Annotated[str, Field(min_length=1, max_length=512)]
    clean_strategy: (
        Literal[
            "web.deterministic",
            "web.llm_rewrite",
            "web.browser_print_pdf",
            "pdf.text_layer",
            "pdf.document_understanding",
            "pdf.ocr",
            "doc.deterministic",
            "doc.document_understanding",
            "doc.ocr",
            "doc.vision",
        ]
        | None
    ) = None
    context_tags: list[Annotated[str, Field(min_length=1, max_length=512)]] = Field(
        default_factory=list,
        max_length=256,
    )

    @field_validator("realm", "type", "channel", "source_name")
    @classmethod
    def validate_semantic_text(cls, value: str, info: Any) -> str:
        return _semantic_text(value, info.field_name)

    @field_validator("context_tags")
    @classmethod
    def normalize_context_tags(cls, value: list[str]) -> list[str]:
        normalized = [item.strip() for item in value]
        if any(not item for item in normalized):
            raise ValueError("context_tags cannot contain blank values")
        return normalized

    @model_validator(mode="after")
    def validate_observation_retry(self) -> GenericSemanticSource:
        if self.retry_failed_observation:
            if self.observation_key is None or self.expected_observation_attempt_generation is None:
                raise ValueError("failed observation retry requires an explicit key and expected attempt generation")
        elif self.expected_observation_attempt_generation is not None:
            raise ValueError("expected observation attempt generation is only valid for a typed retry")
        return self


_UTC_RFC3339 = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?(?:Z|\+00:00)$")


class TeamCreateRequest(PayloadExtraModel):
    schema_version: Literal["mkb.team.v1"]
    team_uuid: str
    name: Annotated[str, Field(min_length=1, max_length=256)]
    description: Annotated[str | None, Field(max_length=4096)] = None

    @field_validator("team_uuid")
    @classmethod
    def validate_team_uuid(cls, value: str) -> str:
        return _uuid(value, "team_uuid")

    @model_validator(mode="after")
    def reject_secret_extras(self) -> TeamCreateRequest:
        assert_safe_public_data(self.payload_extra)
        return self


class TeamPatchRequest(PayloadExtraModel):
    expected_revision: Annotated[int, Field(ge=0)]
    name: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    description: Annotated[str | None, Field(max_length=4096)] = None

    @model_validator(mode="after")
    def require_change(self) -> TeamPatchRequest:
        if self.name is None and self.description is None and "payload_extra" not in self.model_fields_set:
            raise ValueError("at least one mutable Team field is required")
        assert_safe_public_data(self.payload_extra)
        return self


class ExpectedRevisionRequest(StrictModel):
    expected_revision: Annotated[int, Field(ge=0)]
    reason: Annotated[str | None, Field(max_length=1024)] = None


class TaskAudit(PayloadExtraModel):
    schema_version: Literal["mkb.task-audit.v1"]
    team_uuid: str
    task_uuid: str
    trace_uuid: str
    audit_type: Literal["business_review"]
    audit_status: Literal["pending", "approved", "rejected", "waived", "not_required"]
    source: Annotated[str, Field(min_length=1, max_length=256)]
    source_version: Annotated[str | None, Field(max_length=128)] = None
    actor_uuid: str | None = None
    parent_task_uuid: str | None = None
    created_at: str
    reviewed_at: str | None = None
    expires_at: str | None = None
    reason: Annotated[str | None, Field(max_length=4096)] = None

    @field_validator("team_uuid", "task_uuid", "trace_uuid")
    @classmethod
    def validate_required_uuid(cls, value: str, info: Any) -> str:
        return _uuid(value, info.field_name)

    @field_validator("actor_uuid", "parent_task_uuid")
    @classmethod
    def validate_optional_uuid(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _uuid(value, info.field_name)

    @field_validator("created_at", "reviewed_at", "expires_at")
    @classmethod
    def normalize_time(cls, value: str | None, info: Any) -> str | None:
        if value is None:
            return None
        try:
            return normalize_rfc3339(value, field=info.field_name)
        except MkbError as exc:
            # Boundary model validators must raise validation errors rather
            # than leak a lower-layer exception family through FastAPI.
            raise ValueError(f"{info.field_name} must be RFC3339") from exc


class InlineSourceDescriptor(GenericSemanticSource):
    source_kind: Literal["inline_payload"]
    external_key: Annotated[str, Field(min_length=1, max_length=1024)]
    content: Annotated[str, Field(min_length=1, max_length=8 * 1024 * 1024)]
    media_type: Annotated[str, Field(min_length=1, max_length=255)] = "text/plain"
    title: Annotated[str | None, Field(max_length=1024)] = None
    require_human_review: bool = False


class LocalObjectSourceDescriptor(GenericSemanticSource):
    source_kind: Literal["local_object"]
    external_key: Annotated[str, Field(min_length=1, max_length=1024)]
    logical_handle: Annotated[str, Field(pattern=r"^mkbobj:v1:[a-zA-Z0-9._:-]+$")]
    media_type: Annotated[str | None, Field(max_length=255)] = None
    require_human_review: bool = False


class HttpSourceDescriptor(GenericSemanticSource):
    source_kind: Literal["http_resource"]
    external_key: Annotated[str, Field(min_length=1, max_length=1024)]
    url: Annotated[str, Field(min_length=8, max_length=4096)]
    acquisition_mode: Literal["static", "browser", "pdf"] = "static"
    require_human_review: bool = False


class RegisteredApiSourceDescriptor(PayloadExtraModel):
    source_kind: Literal["registered_api"]
    observation_key: Annotated[str | None, Field(min_length=1, max_length=1024)] = None
    retry_failed_observation: bool = False
    expected_observation_attempt_generation: Annotated[int | None, Field(ge=1)] = None
    external_key: Annotated[str, Field(min_length=1, max_length=1024)]
    connector_key: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]{0,127}$")]
    provider: Literal["chinatax", "domain", "realestate"]
    operation: Literal["get_articles", "get_agency_listings", "get_listings"]
    definition_version: Literal["v1"]
    representation: Literal["raw"] = "raw"
    records: list[dict[str, Any]] = Field(max_length=10_000)
    exhaustion_proof: Literal["caller_frozen_records.v1"] | None = None
    pagination_key: Annotated[str | None, Field(max_length=1024)] = None
    require_human_review: bool = False
    realm: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    type: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    channel: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    source_name: Annotated[str | None, Field(min_length=1, max_length=512)] = None

    @field_validator("realm", "type", "channel", "source_name")
    @classmethod
    def validate_optional_semantic_text(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _semantic_text(value, info.field_name)

    @model_validator(mode="after")
    def validate_member_keys(self) -> RegisteredApiSourceDescriptor:
        from intake.api.registry import assert_declared_provider_semantics, parse_registered_api_member
        from src.contracts.intake.providers import ChinaTaxRawMember, DomainRawMember, RealestateRawMember

        binding = (self.provider, self.operation, self.definition_version)
        definitions = {
            ("chinatax", "get_articles", "v1"): (ChinaTaxRawMember, "id"),
            ("domain", "get_agency_listings", "v1"): (DomainRawMember, "id"),
            ("realestate", "get_listings", "v1"): (RealestateRawMember, "listingId"),
        }
        selected = definitions.get(binding)
        if selected is None:
            raise ValueError("registered_api provider/operation/version binding is unsupported")
        model, identity_field = selected
        validated: list[dict[str, Any]] = []
        keys: list[str] = []
        for raw in self.records:
            try:
                member = model.model_validate(raw)
            except ValidationError as exc:
                raise ValueError("registered_api record failed its versioned raw member schema") from exc
            dumped = member.model_dump(mode="json", by_alias=True)
            try:
                mapped = parse_registered_api_member(
                    dumped,
                    provider=self.provider,
                    operation=self.operation,
                    definition_version=self.definition_version,
                )
                assert_declared_provider_semantics(self.model_dump(exclude={"records"}), mapped)
            except MkbError as exc:
                raise ValueError("registered_api semantic duplicate or mapped authority is invalid") from exc
            validated.append(dumped)
            keys.append(str(dumped[identity_field]).strip().casefold())
        self.records = validated
        if self.retry_failed_observation:
            if self.observation_key is None or self.expected_observation_attempt_generation is None:
                raise ValueError("failed observation retry requires an explicit key and expected attempt generation")
        elif self.expected_observation_attempt_generation is not None:
            raise ValueError("expected observation attempt generation is only valid for a typed retry")
        if len(keys) != len(set(keys)):
            raise ValueError("registered_api records must have unique provider external keys")
        return self


SourceDescriptor = Annotated[
    InlineSourceDescriptor | LocalObjectSourceDescriptor | HttpSourceDescriptor | RegisteredApiSourceDescriptor,
    Field(discriminator="source_kind"),
]


class IntakeIngestPayload(StrictModel):
    source: SourceDescriptor
    preflight_profile_key: Annotated[str, Field(min_length=1, max_length=128)] = "default"
    # Optional closed selectors that resolve to catalog identities.  They are
    # not prompt bodies, paths, or a free-form role guess.
    domain: Literal["documentation"] | None = None
    flavor: Literal["qna", "eval", "closure", "plan", "code-review"] | None = None
    granularity: Literal["g0", "g1", "g2"] | None = None
    # C/summarizer transport only.  Omit derives from Task.priority:
    # normal/low → local-inference first; urgent/high → non-interactive.
    # Explicit values force that pool and must be audited.
    compression_channel: Literal["non-interactive", "local-inference"] | None = None
    # Prompt selection is an identity-only public surface.  The catalog row
    # supplies version/hash/path at materialization; callers may not provide
    # prompt bodies, filesystem paths, or a free-form role guess.
    json_prompt_id: Annotated[str | None, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")] = None
    markdown_prompt_id: Annotated[str | None, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")] = None
    clean_prompt_id: Annotated[str | None, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")] = None
    summarizer_prompt_id: Annotated[str | None, Field(pattern=r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")] = None

    @model_validator(mode="after")
    def require_json_identity_or_domain_default(self) -> IntakeIngestPayload:
        if self.flavor is not None and self.domain is None:
            raise ValueError("flavor requires domain")
        if self.json_prompt_id is None and self.domain is None and self.granularity is None:
            raise ValueError("json_prompt_id is required unless domain or granularity selects a json template")
        return self


class IntakeRebuildPayload(StrictModel):
    intake_item_uuid: str
    expected_intake_revision_uuid: str | None = None

    @field_validator("intake_item_uuid", "expected_intake_revision_uuid")
    @classmethod
    def validate_uuids(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _uuid(value, info.field_name)


class IntakeUpdateMetadataPayload(StrictModel):
    intake_item_uuid: str
    expected_intake_revision_uuid: str | None = None
    semantics: dict[str, Any] = Field(min_length=1)

    @field_validator("intake_item_uuid", "expected_intake_revision_uuid")
    @classmethod
    def validate_uuids(cls, value: str | None, info: Any) -> str | None:
        return None if value is None else _uuid(value, info.field_name)


class IntakeLifecyclePayload(StrictModel):
    intake_item_uuid: str

    @field_validator("intake_item_uuid")
    @classmethod
    def validate_item_uuid(cls, value: str) -> str:
        return _uuid(value, "intake_item_uuid")


class IndexRebuildPayload(StrictModel):
    scope: Literal["team", "intake_item"] = "team"
    intake_item_uuid: str | None = None

    @model_validator(mode="after")
    def validate_scope(self) -> IndexRebuildPayload:
        if self.scope == "intake_item" and self.intake_item_uuid is None:
            raise ValueError("intake_item_uuid is required for intake_item scope")
        if self.intake_item_uuid is not None:
            self.intake_item_uuid = _uuid(self.intake_item_uuid, "intake_item_uuid")
        return self


TaskPayload = (
    IntakeIngestPayload
    | IntakeRebuildPayload
    | IntakeUpdateMetadataPayload
    | IntakeLifecyclePayload
    | IndexRebuildPayload
)


_PAYLOAD_MODEL: dict[str, type[StrictModel]] = {
    "intake.ingest": IntakeIngestPayload,
    "intake.rebuild": IntakeRebuildPayload,
    "intake.update_metadata": IntakeUpdateMetadataPayload,
    "intake.deactivate": IntakeLifecyclePayload,
    "intake.reactivate": IntakeLifecyclePayload,
    "intake.delete": IntakeLifecyclePayload,
    "index.rebuild": IndexRebuildPayload,
}


class TaskCreateRequest(PayloadExtraModel):
    schema_version: Literal["mkb.task.v1"]
    team_uuid: str
    task_uuid: str
    trace_uuid: str
    request_intent: Literal[
        "intake.ingest",
        "intake.rebuild",
        "intake.update_metadata",
        "intake.deactivate",
        "intake.reactivate",
        "intake.delete",
        "index.rebuild",
    ]
    title: Annotated[str | None, Field(max_length=1024)] = None
    description: Annotated[str | None, Field(max_length=8192)] = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    deadline_at: str | None = None
    payload: TaskPayload
    audit: TaskAudit
    # Explicit L3 wire bag (not payload_extra).  Shape is deliberately a plain
    # mapping so allowlist/forbidden-key denials raise CONFIG_OVERRIDE_REJECTED
    # with a security audit in ConfigSnapshotService, rather than a generic
    # task-schema-invalid from extra=forbid (S14-A07/A08/T017).
    overrides: dict[str, Any] | None = None

    @field_validator("deadline_at")
    @classmethod
    def normalize_deadline_at(cls, value: str | None) -> str | None:
        """Keep the create-only scheduling fence in one UTC wire form."""

        if value is None:
            return None
        if not _UTC_RFC3339.fullmatch(value):
            raise ValueError("deadline_at must be RFC3339 UTC")
        return normalize_rfc3339(value, field="deadline_at")

    @field_validator("overrides")
    @classmethod
    def validate_overrides_bag(cls, value: dict[str, Any] | None) -> dict[str, Any] | None:
        """Accept only a JSON object; key policy is owned by S14 materialize."""

        if value is None:
            return None
        if not isinstance(value, dict) or not all(isinstance(key, str) and key for key in value):
            raise ValueError("overrides must be a JSON object with string keys")
        try:
            encoded = __import__("json").dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("overrides must contain JSON values") from exc
        if len(encoded.encode("utf-8")) > 16 * 1024:
            raise ValueError("overrides exceeds 16KiB")
        return value

    @model_validator(mode="before")
    @classmethod
    def parse_intent_payload(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values
        intent = values.get("request_intent")
        model = _PAYLOAD_MODEL.get(intent)
        if model is None:
            return values
        raw = values.get("payload")
        # Let Pydantic produce a field-scoped validation error for malformed input.
        parsed = model.model_validate(raw)
        copied = dict(values)
        copied["payload"] = parsed
        return copied

    @field_validator("team_uuid", "task_uuid", "trace_uuid")
    @classmethod
    def validate_ids(cls, value: str, info: Any) -> str:
        return _uuid(value, info.field_name)

    @model_validator(mode="after")
    def validate_identity_and_payload(self) -> TaskCreateRequest:
        if (
            self.audit.team_uuid != self.team_uuid
            or self.audit.task_uuid != self.task_uuid
            or self.audit.trace_uuid != self.trace_uuid
        ):
            raise ValueError("Task and Audit identities must match")
        expected_model = _PAYLOAD_MODEL[self.request_intent]
        if not isinstance(self.payload, expected_model):
            raise ValueError("payload does not match request_intent")
        assert_safe_public_data(self.payload_extra)
        return self


class TaskPatchRequest(PayloadExtraModel):
    expected_revision: Annotated[int, Field(ge=0)]
    title: Annotated[str | None, Field(max_length=1024)] = None
    description: Annotated[str | None, Field(max_length=8192)] = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None

    @model_validator(mode="after")
    def require_mutation(self) -> TaskPatchRequest:
        if (
            self.title is None
            and self.description is None
            and self.priority is None
            and "payload_extra" not in self.model_fields_set
        ):
            raise ValueError("at least one mutable Task field is required")
        assert_safe_public_data(self.payload_extra)
        return self


class RetryRequest(ExpectedRevisionRequest):
    reason: Annotated[str, Field(min_length=1, max_length=1024)]


class GateDecisionRequest(PayloadExtraModel):
    expected_gate_revision: Annotated[int, Field(ge=0)]
    target_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    action: Literal["approve", "reject", "reclean"]
    idempotency_key: Annotated[str, Field(min_length=1, max_length=256)]
    reason: Annotated[str | None, Field(max_length=2048)] = None

    @model_validator(mode="after")
    def validate_safe_decision_evidence(self) -> GateDecisionRequest:
        """Keep optional human evidence safe to persist and echo nowhere by default.

        The authenticated token is the v1 actor evidence.  ``payload_extra``
        may carry non-authoritative supporting evidence, but it must never
        become a route, identity, secret, or host-path side channel.
        """

        assert_safe_public_data(self.payload_extra)
        if self.reason is not None:
            assert_safe_public_data(self.reason)
        return self


class LegacyRetrievalFilter(StrictModel):
    intake_item_uuid: str | None = None
    source_kind: Literal["inline_payload", "local_object", "http_resource", "registered_api"] | None = None
    channel: Literal["original", "summary"] | None = None

    @field_validator("intake_item_uuid")
    @classmethod
    def validate_item_uuid(cls, value: str | None) -> str | None:
        return None if value is None else _uuid(value, "intake_item_uuid")


class RetrievalFilter(StrictModel):
    intake_item_uuid: str | None = None
    source_kind: Literal["inline_payload", "local_object", "http_resource", "registered_api"] | None = None
    realm: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    type: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    semantic_channel: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    vector_channel: Literal["original", "summary"] | None = None
    source_name: Annotated[str | None, Field(min_length=1, max_length=512)] = None
    is_active: Literal[0, 1] | None = None
    context_tags: Annotated[str | None, Field(min_length=1, max_length=8192)] = None

    @field_validator("intake_item_uuid")
    @classmethod
    def validate_item_uuid(cls, value: str | None) -> str | None:
        return None if value is None else _uuid(value, "intake_item_uuid")


class RetrievalRequest(StrictModel):
    schema_version: Literal["mkb.retrieval.v1", "mkb.retrieval.v2"] = "mkb.retrieval.v1"
    team_uuid: str
    query: Annotated[str, Field(max_length=8192)]
    namespace_key: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    namespace_uuid: str | None = None
    return_k: Annotated[int | None, Field(ge=1, le=100)] = None
    recall_k: Annotated[int | None, Field(ge=1, le=100)] = None
    score_threshold: float | None = None
    include_pack: bool = True
    # ``top_k`` is accepted only as a short-lived wire compatibility alias.
    # S10's public contract names the output bound ``return_k``.
    top_k: Annotated[int | None, Field(ge=1, le=100)] = None
    # A mapping alternative intentionally lets the service emit the required
    # RETRIEVE_FILTER_INVALID code for an unregistered key, rather than letting
    # FastAPI turn it into an untyped validation response before S10 runs.
    filters: RetrievalFilter | LegacyRetrievalFilter | dict[str, Any] | None = None

    @field_validator("team_uuid")
    @classmethod
    def validate_team_uuid(cls, value: str) -> str:
        return _uuid(value, "team_uuid")

    @field_validator("namespace_uuid")
    @classmethod
    def validate_namespace_uuid(cls, value: str | None) -> str | None:
        return None if value is None else _uuid(value, "namespace_uuid")

    @model_validator(mode="after")
    def validate_retrieval_selector(self) -> RetrievalRequest:
        if self.namespace_key is not None and self.namespace_uuid is not None:
            raise ValueError("only one namespace selector may be supplied")
        if self.return_k is not None and self.top_k is not None:
            raise ValueError("use return_k instead of top_k")
        if self.filters is not None:
            values = self.filters.model_dump(exclude_none=True) if isinstance(self.filters, BaseModel) else self.filters
            keys = set(values)
            legacy = {"intake_item_uuid", "source_kind", "channel"}
            current = set(RetrievalFilter.model_fields)
            allowed = legacy if self.schema_version == "mkb.retrieval.v1" else current
            if keys - allowed:
                raise ValueError("retrieval filter key is not available in this schema version")
        return self


# The public request is deliberately parsed at the API boundary rather than by
# FastAPI's automatic model dependency.  Otherwise ``extra='forbid'`` is
# transformed into its generic validation envelope before S10 can tell a
# caller that a client-controlled index/vector/model field was rejected.  Keep
# this closed set adjacent to the contract; services must still defend their
# direct-call mapping seam independently.
_RETRIEVAL_FORBIDDEN_FIELDS = frozenset(
    {
        "index_generation",
        "raw_query_vector",
        "query_embedding",
        "distance_metric",
        "embedding_model",
        "model_override",
        "include_answer",
        "stream",
    }
)


def parse_retrieval_request(payload: object) -> RetrievalRequest:
    """Validate an HTTP JSON value with stable, non-echoing S10 errors.

    The function intentionally exposes neither a rejected field value nor a
    Pydantic error representation.  This prevents raw vectors, model override
    payloads, or malformed query text from becoming an error-body side channel.
    """

    if not isinstance(payload, Mapping):
        raise MkbError("RETRIEVE_SCHEMA_INVALID", "Retrieval request must be a JSON object", 422)
    if not all(isinstance(key, str) for key in payload):
        raise MkbError("RETRIEVE_SCHEMA_INVALID", "Retrieval request field names are invalid", 422)

    supplied_keys = set(payload)
    if supplied_keys & _RETRIEVAL_FORBIDDEN_FIELDS:
        raise MkbError(
            "RETRIEVE_SCHEMA_FORBIDDEN_FIELD",
            "v1 retrieval does not allow client index/model/vector/answer overrides",
            422,
        )

    unknown = supplied_keys - set(RetrievalRequest.model_fields)
    if unknown:
        raise MkbError("RETRIEVE_SCHEMA_UNKNOWN_FIELD", "Unknown retrieval request field", 422)
    schema_version = payload.get("schema_version", "mkb.retrieval.v1")
    raw_filters = payload.get("filters")
    if isinstance(raw_filters, Mapping):
        allowed_filters = (
            {"intake_item_uuid", "source_kind", "channel"}
            if schema_version == "mkb.retrieval.v1"
            else set(RetrievalFilter.model_fields)
            if schema_version == "mkb.retrieval.v2"
            else set()
        )
        if set(raw_filters) - allowed_filters:
            raise MkbError("RETRIEVE_FILTER_INVALID", "Retrieval filters are invalid for this schema", 422)

    try:
        request = RetrievalRequest.model_validate(payload)
    except ValidationError as exc:
        raise _retrieval_validation_error(exc) from exc
    if request.namespace_key is None and request.namespace_uuid is None:
        raise MkbError(
            "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED",
            "retrieval requires namespace_key or namespace_uuid; default is not a Layer-A space",
            422,
        )
    return request


def _retrieval_validation_error(exc: ValidationError) -> MkbError:
    """Map typed-contract violations without reflecting body contents."""

    locations = {
        str(error["loc"][0])
        for error in exc.errors()
        if isinstance(error.get("loc"), tuple) and error["loc"]
    }
    if "filters" in locations:
        return MkbError("RETRIEVE_FILTER_INVALID", "Retrieval filters are invalid", 422)
    if locations & {"return_k", "recall_k", "top_k"}:
        return MkbError("RETRIEVE_TOPK_INVALID", "Retrieval rank bounds are invalid", 422)
    if "score_threshold" in locations:
        return MkbError("RETRIEVE_SCHEMA_THRESHOLD_INVALID", "Retrieval score threshold is invalid", 422)
    if "include_pack" in locations:
        return MkbError("RETRIEVE_SCHEMA_PACK_INVALID", "Retrieval pack option is invalid", 422)
    if locations & {"namespace_key", "namespace_uuid"}:
        return MkbError("RETRIEVE_SCHEMA_NAMESPACE_INVALID", "Retrieval namespace selector is invalid", 422)
    if "team_uuid" in locations:
        return MkbError("RETRIEVE_SCHEMA_TEAM_REQUIRED", "team_uuid is required for retrieval", 422)
    return MkbError("RETRIEVE_SCHEMA_INVALID", "Retrieval request does not satisfy the v1 contract", 422)


class TaskView(StrictModel):
    team_uuid: str
    task_uuid: str
    trace_uuid: str
    schema_version: str
    request_intent: str
    status: Literal["queued", "running", "cancelling", "succeeded", "failed", "cancelled"]
    revision: int
    current_generation: int
    title: str | None = None
    description: str | None = None
    priority: str
    deadline_at: str | None = None
    payload_extra: dict[str, Any]
    received_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result_ref: str | None = None
    proof_ref: str | None = None
    result_disposition: str | None = None
    error: dict[str, str] | None = None
    action_required: dict[str, Any] | None = None
    deleted_at: str | None = None
    counts: dict[str, int]
    source_kind: str | None = None
    observation_uuid: str | None = None
    observation_key: str | None = None
    workflow_revision_uuid: str | None = None
    actual_binding: dict[str, str] | None = None
    intake_snapshot_uuid: str | None = None
    intake_item_uuid: str | None = None
    intake_revision_uuid: str | None = None
    phase: str | None = None
    waiting_reason: str | None = None
    retryable: bool = False
    links: dict[str, str]


class CapabilityCatalogView(StrictModel):
    process_key: str
    contract_version: str
    definition_digest: str
    handler_key: str
    deployment_roles: list[str]
    supply_requirements: list[str]
    available: bool
    missing_supplies: list[str]


class WorkflowCatalogView(StrictModel):
    workflow_key: str
    workflow_uuid: str
    workflow_revision_uuid: str
    revision_number: int
    purpose_key: str
    execution_role: str
    compiled_digest: str
    required_process_keys: list[str]
    availability: str


class SourceKindCatalogView(StrictModel):
    source_kind: str
    definition_version: str
    definition_digest: str
    cardinality: str
    acquisition_capabilities: list[str]
    decode_capabilities: list[str]
    clean_capabilities: list[str]


class CatalogView(StrictModel):
    schema_version: Literal["mkb.catalog.v1"] = "mkb.catalog.v1"
    deployment_role: str
    capability_manifest_digest: str
    workflows: list[WorkflowCatalogView]
    capabilities: list[CapabilityCatalogView]
    source_kinds: list[SourceKindCatalogView]


class TaskListView(StrictModel):
    items: list[TaskView]
    next_cursor: str | None = None


class CommandReceiptView(StrictModel):
    command_receipt_uuid: str
    command_kind: str
    target_kind: str
    target_uuid: str
    disposition: Literal["applied", "replayed", "noop", "rejected"]
    expected_generation: int | None = None
    observed_generation: int | None = None
    retryable: bool = False
    error_code: str | None = None
    result_ref: str | None = None
    outbox_id: str | None = None
    cleanup_job_uuid: str | None = None
    decided_at: str


class OutboxRequeueRequest(StrictModel):
    expected_generation: int = Field(ge=1)
    idempotency_key: str = Field(min_length=1, max_length=256)


class CleanupResumeRequest(StrictModel):
    expected_revision: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=256)


class GenerationControlRequest(StrictModel):
    expected_generation: int = Field(ge=0)
    idempotency_key: str = Field(min_length=1, max_length=256)


class CutoverRevisionRequest(StrictModel):
    expected_revision: int = Field(ge=0)


class CutoverStateView(StrictModel):
    cutover_key: str
    writer_mode: str
    reader_mode: str
    admission_enabled: bool
    expected_migration_revision: int
    row_revision: int


class CutoverInventoryView(StrictModel):
    rev1_pins: int
    pending_outbox: int
    open_restarts: int
    live_object_refs: int
    open_cleanup_jobs: int
    legacy_evidence: int
    unresolved_shadow: int


class ProcessDebugView(StrictModel):
    process_uuid: str
    team_uuid: str
    execution_uuid: str
    task_uuid: str
    step_key: str
    process_key: str
    process_contract_version: str
    status: str
    row_revision: int
    fencing_generation: int
    lease_owner: str | None = None
    delivery_count: int
    retry_count: int
    max_retries: int
    error_class: str | None = None
    error_code: str | None = None
    failure_disposition: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str
    proof_ref: str | None = None
    proof_digest: str | None = None


class ExecutionDebugView(StrictModel):
    execution_uuid: str
    team_uuid: str
    task_uuid: str
    generation: int
    execution_role: str
    target_kind: str
    target_uuid: str | None = None
    status: str
    workflow_uuid: str
    workflow_revision_uuid: str
    compiled_digest: str
    actual_binding_state: str | None = None
    actual_binding_digest: str | None = None
    phase_key: str | None = None
    waiting_reason: str | None = None
    current_process_uuid: str | None = None
    total_process_count: int
    active_process_count: int
    succeeded_process_count: int
    failed_process_count: int
    cancelled_process_count: int
    result_ref: str | None = None
    publication_proof_ref: str | None = None
    final_error_code: str | None = None
    created_at: str
    started_at: str | None = None
    completed_at: str | None = None
    updated_at: str


class CleanupStepDebugView(StrictModel):
    substrate_kind: str
    state: str
    proof_uuid: str | None = None
    blocked_reason: str | None = None


class CleanupJobDebugView(StrictModel):
    cleanup_job_uuid: str
    intent_uuid: str
    team_uuid: str
    intake_item_uuid: str
    item_epoch: int
    required_substrate_set_digest: str
    retention_until: str
    state: str
    blocked_reason: str | None = None
    created_at: str
    updated_at: str
    steps: list[CleanupStepDebugView]


class NamespaceView(StrictModel):
    namespace_uuid: str
    namespace_key: str
    model_key: str
    model_version: str
    dimension: int
    status: str


class IntakeItemView(StrictModel):
    intake_item_uuid: str
    external_key: str
    source_kind: str
    lifecycle_state: str
    row_revision: int
    latest_revision_uuid: str | None = None
    serving_revision_uuid: str | None = None
    created_at: str
    updated_at: str


class IntakeItemListView(StrictModel):
    items: list[IntakeItemView]
    next_cursor: str | None = None


class NamespaceListView(StrictModel):
    items: list[NamespaceView]
    next_cursor: str | None = None


class PageEnvelope(StrictModel):
    items: list[dict[str, Any]]
    next_cursor: str | None = None


__all__ = [
    "ErrorEnvelope",
    "ExpectedRevisionRequest",
    "GateDecisionRequest",
    "parse_retrieval_request",
    "RetrievalRequest",
    "TaskCreateRequest",
    "TaskPatchRequest",
    "TaskView",
    "TaskListView",
    "IntakeItemListView",
    "NamespaceListView",
    "CapabilityCatalogView",
    "WorkflowCatalogView",
    "SourceKindCatalogView",
    "CatalogView",
    "CommandReceiptView",
    "OutboxRequeueRequest",
    "CleanupResumeRequest",
    "GenerationControlRequest",
    "CutoverRevisionRequest",
    "CutoverStateView",
    "CutoverInventoryView",
    "ProcessDebugView",
    "ExecutionDebugView",
    "CleanupStepDebugView",
    "CleanupJobDebugView",
    "NamespaceView",
    "IntakeItemView",
    "TeamCreateRequest",
    "TeamPatchRequest",
]
