"""Provider-neutral, provenance-complete inference contracts.

Adapters may construct the response models without provenance while decoding a
provider response.  :class:`src.runtime.inference.facade.InferenceFacade` is
the only public runtime boundary and fills the mandatory provenance fields
before handing a result to a domain service.
"""

from __future__ import annotations

import json
from typing import Annotated, Any, Literal

from pydantic import Field, field_validator

from src.contracts.common.models import PayloadExtraModel, StrictModel

InferenceCapability = Literal["embed", "rerank", "structured_generate", "text_generate"]
InferenceAdapterKind = Literal["local_vllm", "remote_gemini", "deterministic"]
Digest = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
BoundedIdentifier = Annotated[str, Field(min_length=1, max_length=256)]


class InferenceBinding(StrictModel):
    """The immutable model identity supplied by L4/Process binding.

    A request never supplies an endpoint.  The runtime checks this identity
    against a registered SupplyFence before it may reach an adapter transport.
    """

    capability_key: InferenceCapability
    adapter_kind: InferenceAdapterKind
    model_key: BoundedIdentifier
    model_version: BoundedIdentifier
    binding_digest: Digest


class InferenceUsage(StrictModel):
    input_tokens: int | None = Field(default=None, ge=0)
    output_tokens: int | None = Field(default=None, ge=0)
    total_tokens: int | None = Field(default=None, ge=0)


class InvocationContext(StrictModel):
    """Bounded correlation/provenance references, never prompt or vector bytes."""

    trace_uuid: str | None = Field(default=None, min_length=1, max_length=128)
    task_uuid: str | None = Field(default=None, min_length=1, max_length=128)
    execution_uuid: str | None = Field(default=None, min_length=1, max_length=128)
    process_uuid: str | None = Field(default=None, min_length=1, max_length=128)
    generation_invocation_uuid: str | None = Field(default=None, min_length=1, max_length=128)
    prompt_content_hash: Digest | None = None
    schema_content_digest: Digest | None = None
    params_digest: Digest | None = None
    config_snapshot_digest: Digest | None = None


class InferenceRequest(PayloadExtraModel):
    team_uuid: BoundedIdentifier
    binding: InferenceBinding
    invocation: InvocationContext | None = None

    @field_validator("payload_extra")
    @classmethod
    def _payload_extra_is_not_a_hidden_prompt_or_secret(cls, value: dict[str, Any]) -> dict[str, Any]:
        # ``payload_extra`` is an extension seam, not a way to bypass the
        # explicit request fields or sneak material into invocation evidence.
        forbidden = {"authorization", "token", "password", "secret", "api_key", "prompt", "content", "vector"}
        if any(str(key).casefold() in forbidden for key in value):
            raise ValueError("inference payload_extra contains a forbidden key")
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("inference payload_extra must be JSON") from exc
        return value


class EmbeddingRequest(InferenceRequest):
    texts: list[Annotated[str, Field(min_length=1, max_length=100_000)]] = Field(min_length=1, max_length=128)
    # Namespace/Layer-A owners supply this when the dimension is already
    # frozen.  The facade then rejects a model result before it can reach S08.
    expected_dimension: int | None = Field(default=None, gt=0, le=32_768)


class RerankDocument(StrictModel):
    document_id: BoundedIdentifier
    text: Annotated[str, Field(min_length=1, max_length=100_000)]


class RerankRequest(InferenceRequest):
    query: Annotated[str, Field(min_length=1, max_length=100_000)]
    documents: list[RerankDocument] = Field(min_length=1, max_length=256)
    top_n: int | None = Field(default=None, ge=1, le=256)


class GenerateRequest(InferenceRequest):
    """Legacy-compatible generic generation input.

    New domain code should use :class:`TextGenerateRequest` or
    :class:`StructuredGenerateRequest`; retaining this shape avoids making an
    adapter implementation itself a source of workflow migration churn.
    """

    prompt_ref: BoundedIdentifier
    prompt_digest: Digest
    input_text: Annotated[str, Field(max_length=1_000_000)]


class TextGenerateRequest(GenerateRequest):
    pass


class StructuredGenerateRequest(GenerateRequest):
    json_schema_ref: BoundedIdentifier
    json_schema_digest: Digest


class InferenceResult(StrictModel):
    """Common result appendix populated by the facade, not by a provider."""

    model_key: BoundedIdentifier
    model_version: BoundedIdentifier
    adapter_kind: InferenceAdapterKind | None = None
    usage: InferenceUsage | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    request_digest: Digest | None = None
    invocation_uuid: str | None = Field(default=None, min_length=1, max_length=128)

    def has_complete_provenance(self) -> bool:
        return all(
            (
                self.adapter_kind is not None,
                self.latency_ms is not None,
                self.request_digest is not None,
                self.invocation_uuid is not None,
            )
        )


class EmbeddingResponse(InferenceResult):
    vectors: list[list[float]]
    dimension: Annotated[int, Field(gt=0, le=32_768)]


class RerankScore(StrictModel):
    document_id: BoundedIdentifier
    score: float


class RerankResponse(InferenceResult):
    results: list[RerankScore]


class GenerateResponse(InferenceResult):
    text: str


class TextGenerateResponse(GenerateResponse):
    pass


class StructuredGenerateResponse(GenerateResponse):
    value: dict[str, Any]

    @field_validator("value")
    @classmethod
    def _value_is_json(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("structured response must be JSON") from exc
        return value


class InferenceInvocationRecord(StrictModel):
    """The safe, D04-shaped subset written by an injectable invocation sink."""

    invocation_uuid: str = Field(min_length=1, max_length=128)
    team_uuid: BoundedIdentifier
    capability_key: InferenceCapability
    adapter_kind: InferenceAdapterKind
    model_key: BoundedIdentifier
    model_version: BoundedIdentifier
    request_digest: Digest
    status: Literal["succeeded", "failed", "cancelled"]
    error_code: str | None = Field(default=None, min_length=1, max_length=128)
    usage: InferenceUsage | None = None
    latency_ms: int | None = Field(default=None, ge=0)
    context: InvocationContext | None = None


__all__ = [
    "Digest",
    "EmbeddingRequest",
    "EmbeddingResponse",
    "GenerateRequest",
    "GenerateResponse",
    "InferenceAdapterKind",
    "InferenceBinding",
    "InferenceCapability",
    "InferenceInvocationRecord",
    "InferenceRequest",
    "InferenceResult",
    "InferenceUsage",
    "InvocationContext",
    "RerankDocument",
    "RerankRequest",
    "RerankResponse",
    "RerankScore",
    "StructuredGenerateRequest",
    "StructuredGenerateResponse",
    "TextGenerateRequest",
    "TextGenerateResponse",
]
