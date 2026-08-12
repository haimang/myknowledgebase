"""Provider-neutral facade contracts. Adapters do not leak into services."""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from src.contracts.common.models import PayloadExtraModel, StrictModel


class InferenceBinding(StrictModel):
    capability_key: Literal["embed", "rerank", "structured_generate", "text_generate"]
    adapter_kind: Literal["local_vllm", "remote_gemini"]
    model_key: Annotated[str, Field(min_length=1, max_length=256)]
    model_version: Annotated[str, Field(min_length=1, max_length=256)]
    binding_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class EmbeddingRequest(PayloadExtraModel):
    team_uuid: str
    binding: InferenceBinding
    texts: list[Annotated[str, Field(min_length=1, max_length=100_000)]] = Field(min_length=1, max_length=128)


class EmbeddingResponse(StrictModel):
    vectors: list[list[float]]
    model_key: str
    model_version: str
    dimension: Annotated[int, Field(gt=0)]


class GenerateRequest(PayloadExtraModel):
    team_uuid: str
    binding: InferenceBinding
    prompt_ref: str
    prompt_digest: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    input_text: Annotated[str, Field(max_length=1_000_000)]


class GenerateResponse(StrictModel):
    text: str
    model_key: str
    model_version: str
