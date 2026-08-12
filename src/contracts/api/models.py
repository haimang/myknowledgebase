"""Strict public Task, Team, gate, and retrieval contracts (S01/S02/S10)."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Annotated, Any, Literal

from pydantic import Field, ValidationError, field_validator, model_validator

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import validate_external_uuid
from src.contracts.common.models import (
    ErrorEnvelope,
    PayloadExtraModel,
    StrictModel,
    TaskStatus,
    assert_safe_public_data,
)
from src.contracts.common.time import normalize_rfc3339


def _uuid(value: str, field: str) -> str:
    try:
        return validate_external_uuid(value, field=field)
    except Exception as exc:
        raise ValueError(str(exc)) from exc


class TeamCreateRequest(PayloadExtraModel):
    schema_version: Literal["mkb.team.v1"]
    team_uuid: str
    name: Annotated[str, Field(min_length=1, max_length=256)]
    description: Annotated[str | None, Field(max_length=4096)] = None

    @field_validator("team_uuid")
    @classmethod
    def validate_team_uuid(cls, value: str) -> str:
        return _uuid(value, "team_uuid")


class TeamPatchRequest(PayloadExtraModel):
    expected_revision: Annotated[int, Field(ge=0)]
    name: Annotated[str | None, Field(min_length=1, max_length=256)] = None
    description: Annotated[str | None, Field(max_length=4096)] = None

    @model_validator(mode="after")
    def require_change(self) -> TeamPatchRequest:
        if self.name is None and self.description is None and not self.payload_extra:
            raise ValueError("at least one mutable Team field is required")
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
        return None if value is None else normalize_rfc3339(value, field=info.field_name)


class InlineSourceDescriptor(PayloadExtraModel):
    source_kind: Literal["inline_payload"]
    external_key: Annotated[str, Field(min_length=1, max_length=1024)]
    content: Annotated[str, Field(min_length=1, max_length=8 * 1024 * 1024)]
    media_type: Annotated[str, Field(min_length=1, max_length=255)] = "text/plain"
    title: Annotated[str | None, Field(max_length=1024)] = None
    require_human_review: bool = False


class LocalObjectSourceDescriptor(PayloadExtraModel):
    source_kind: Literal["local_object"]
    external_key: Annotated[str, Field(min_length=1, max_length=1024)]
    logical_handle: Annotated[str, Field(pattern=r"^mkbobj:v1:[a-zA-Z0-9._:-]+$")]
    media_type: Annotated[str | None, Field(max_length=255)] = None
    require_human_review: bool = False


class HttpSourceDescriptor(PayloadExtraModel):
    source_kind: Literal["http_resource"]
    external_key: Annotated[str, Field(min_length=1, max_length=1024)]
    url: Annotated[str, Field(min_length=8, max_length=4096)]
    acquisition_mode: Literal["static", "browser", "pdf"] = "static"
    require_human_review: bool = False


class RegisteredApiSourceDescriptor(PayloadExtraModel):
    source_kind: Literal["registered_api"]
    external_key: Annotated[str, Field(min_length=1, max_length=1024)]
    connector_key: Annotated[str, Field(pattern=r"^[a-z][a-z0-9_.-]{0,127}$")]
    records: list[dict[str, Any]] | None = Field(default=None, max_length=10_000)
    pagination_key: Annotated[str | None, Field(max_length=1024)] = None
    require_human_review: bool = False


SourceDescriptor = Annotated[
    InlineSourceDescriptor | LocalObjectSourceDescriptor | HttpSourceDescriptor | RegisteredApiSourceDescriptor,
    Field(discriminator="source_kind"),
]


class IntakeIngestPayload(StrictModel):
    source: SourceDescriptor
    preflight_profile_key: Annotated[str, Field(min_length=1, max_length=128)] = "default"


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
        "intake.delete",
        "index.rebuild",
    ]
    title: Annotated[str | None, Field(max_length=1024)] = None
    description: Annotated[str | None, Field(max_length=8192)] = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    payload: TaskPayload
    audit: TaskAudit

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
        if self.title is None and self.description is None and self.priority is None and not self.payload_extra:
            raise ValueError("at least one mutable Task field is required")
        return self


class RetryRequest(ExpectedRevisionRequest):
    reason: Annotated[str, Field(min_length=1, max_length=1024)]


class GateDecisionRequest(PayloadExtraModel):
    expected_gate_revision: Annotated[int, Field(ge=0)]
    target_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    action: Literal["approve", "reject", "reclean"]
    idempotency_key: Annotated[str, Field(min_length=1, max_length=256)]
    reason: Annotated[str | None, Field(max_length=2048)] = None


class RetrievalFilter(StrictModel):
    intake_item_uuid: str | None = None
    source_kind: Literal["inline_payload", "local_object", "http_resource", "registered_api"] | None = None
    channel: Literal["original", "summary"] | None = None

    @field_validator("intake_item_uuid")
    @classmethod
    def validate_item_uuid(cls, value: str | None) -> str | None:
        return None if value is None else _uuid(value, "intake_item_uuid")


class RetrievalRequest(StrictModel):
    schema_version: Literal["mkb.retrieval.v1"] = "mkb.retrieval.v1"
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
    filters: RetrievalFilter | dict[str, str] | None = None

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

    try:
        return RetrievalRequest.model_validate(payload)
    except ValidationError as exc:
        raise _retrieval_validation_error(exc) from exc


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
    status: TaskStatus
    revision: int
    current_generation: int
    title: str | None = None
    description: str | None = None
    priority: str
    payload_extra: dict[str, Any]
    received_at: str
    started_at: str | None = None
    completed_at: str | None = None
    result_ref: str | None = None
    proof_ref: str | None = None
    error: dict[str, str] | None = None
    action_required: dict[str, Any] | None = None
    links: dict[str, str]


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
    "TeamCreateRequest",
    "TeamPatchRequest",
]
