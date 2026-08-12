"""OpenAI-compatible `ai-mkb` adapter. It never changes a resolved binding."""

from __future__ import annotations

from typing import Any

import httpx

from src.contracts.common.errors import MkbError
from src.contracts.inference.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerateRequest,
    GenerateResponse,
)


class LocalVllmAdapter:
    def __init__(self, base_url: str, *, bearer_token: str | None = None, timeout_seconds: float = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.bearer_token = bearer_token
        self.timeout_seconds = timeout_seconds

    def _headers(self) -> dict[str, str]:
        return {} if not self.bearer_token else {"Authorization": f"Bearer {self.bearer_token}"}

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        payload = {"model": request.binding.model_key, "input": request.texts}
        response = await self._request("/v1/embeddings", payload)
        vectors = [entry.get("embedding") for entry in response.get("data", [])]
        if len(vectors) != len(request.texts) or not all(isinstance(item, list) for item in vectors):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Embedding response is malformed", 502)
        dimension = len(vectors[0]) if vectors else 0
        if dimension == 0 or any(len(vector) != dimension for vector in vectors):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Embedding dimensions are inconsistent", 502)
        return EmbeddingResponse(
            vectors=vectors,
            model_key=request.binding.model_key,
            model_version=request.binding.model_version,
            dimension=dimension,
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        payload = {
            "model": request.binding.model_key,
            "messages": [{"role": "user", "content": request.input_text}],
            "stream": False,
        }
        response = await self._request("/v1/chat/completions", payload)
        try:
            text = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Generation response is malformed", 502) from exc
        if not isinstance(text, str):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Generation response is malformed", 502)
        return GenerateResponse(
            text=text,
            model_key=request.binding.model_key,
            model_version=request.binding.model_version,
        )

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        # The deployed local vLLM profile may not expose a rerank endpoint. This
        # method deliberately reports unavailability rather than manufacturing a
        # dummy score or switching models.
        raise MkbError("INFERENCE_CONFIG_RERANK_UNAVAILABLE", "Reranking is not bound", 503)

    async def probe(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=min(self.timeout_seconds, 5)) as client:
                response = await client.get(f"{self.base_url}/v1/models", headers=self._headers())
                return response.status_code < 500
        except httpx.HTTPError:
            return False

    async def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
                response = await client.post(f"{self.base_url}{path}", json=payload, headers=self._headers())
                if response.status_code in (429, 503):
                    raise MkbError("INFERENCE_TRANSPORT_RETRYABLE", "Inference service is busy", 503)
                response.raise_for_status()
                result = response.json()
        except MkbError:
            raise
        except httpx.HTTPError as exc:
            raise MkbError("INFERENCE_TRANSPORT_RETRYABLE", "Inference transport failed", 503) from exc
        if not isinstance(result, dict):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Inference response is malformed", 502)
        return result
