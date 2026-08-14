"""OpenAI-compatible local-vLLM adapter with a binding-only transport seam."""

from __future__ import annotations

import math
from typing import Any, Protocol, runtime_checkable
from urllib.parse import urlsplit

import httpx
from pydantic import ValidationError

from src.contracts.common.errors import MkbError
from src.contracts.inference.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerateRequest,
    GenerateResponse,
    InferenceBinding,
    InferenceUsage,
)


@runtime_checkable
class SecretValueResolver(Protocol):
    """Structural port shared with S16's logical-slot SecretResolver."""

    def resolve(self, slot: str) -> str: ...


def _normalize_base_url(value: str) -> str:
    """Accept only a configured HTTP(S) origin/path, never userinfo or query."""

    try:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in {"http", "https"}
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("invalid URL")
        port = parsed.port
    except (TypeError, ValueError) as exc:
        raise ValueError("base_url must be a configured http(s) origin") from exc
    authority = parsed.hostname.lower()
    if ":" in authority:
        authority = f"[{authority}]"
    if port is not None:
        authority = f"{authority}:{port}"
    return f"{parsed.scheme.lower()}://{authority}{parsed.path.rstrip('/')}"


class LocalVllmAdapter:
    """Use one configured endpoint and the exact request binding only.

    secret_slot is a logical name.  The token value is resolved just before
    transport use and is never kept on the adapter, included in a request
    contract, or represented in provenance.
    """

    adapter_kind = "local_vllm"

    def __init__(
        self,
        base_url: str,
        *,
        secret_slot: str | None = None,
        secret_resolver: SecretValueResolver | None = None,
        timeout_seconds: float = 30,
        transport: httpx.AsyncBaseTransport | None = None,
        bearer_token: str | None = None,
    ) -> None:
        if bearer_token is not None:
            raise ValueError("raw bearer_token is not supported; configure secret_slot and secret_resolver")
        if not isinstance(secret_slot, str | type(None)) or (secret_slot is not None and not secret_slot.strip()):
            raise ValueError("secret_slot must be a non-empty logical slot or None")
        if secret_slot is not None and secret_resolver is None:
            raise ValueError("secret_resolver is required when secret_slot is configured")
        if not isinstance(timeout_seconds, int | float) or isinstance(timeout_seconds, bool) or timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.base_url = _normalize_base_url(base_url)
        self.secret_slot = secret_slot
        self._secret_resolver = secret_resolver
        self.timeout_seconds = float(timeout_seconds)
        self._transport = transport

    def _headers(self) -> dict[str, str]:
        if self.secret_slot is None:
            return {}
        assert self._secret_resolver is not None
        token = self._secret_resolver.resolve(self.secret_slot)
        if not isinstance(token, str) or not token:
            raise MkbError("SEC_SECRET_UNRESOLVED", "Model secret cannot be resolved", 503)
        return {"Authorization": f"Bearer {token}"}

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self._assert_binding(request.binding)
        payload: dict[str, Any] = {
            "model": request.binding.model_key,
            "input": request.texts,
        }
        if request.expected_dimension is not None:
            payload["dimensions"] = request.expected_dimension
        response = await self._request("/v1/embeddings", payload)
        self._assert_provider_model(response, request.binding)
        raw_data = response.get("data")
        if not isinstance(raw_data, list) or len(raw_data) != len(request.texts):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Embedding response is malformed", 502)
        try:
            vectors = [
                [float(value) for value in entry["embedding"]]
                for entry in raw_data
                if isinstance(entry, dict) and isinstance(entry.get("embedding"), list)
            ]
        except (KeyError, TypeError, ValueError) as exc:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Embedding response is malformed", 502) from exc
        if len(vectors) != len(request.texts) or not vectors:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Embedding response is malformed", 502)
        dimension = len(vectors[0])
        if dimension == 0 or any(len(vector) != dimension or not all(math.isfinite(value) for value in vector) for vector in vectors):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Embedding response is malformed", 502)
        try:
            return EmbeddingResponse(
                vectors=vectors,
                model_key=request.binding.model_key,
                model_version=request.binding.model_version,
                dimension=dimension,
                usage=self._usage(response),
            )
        except ValidationError as exc:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Embedding response is malformed", 502) from exc

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        self._assert_binding(request.binding)
        payload = {
            "model": request.binding.model_key,
            "messages": [{"role": "user", "content": request.input_text}],
            "stream": False,
        }
        response = await self._request("/v1/chat/completions", payload)
        self._assert_provider_model(response, request.binding)
        try:
            text = response["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Generation response is malformed", 502) from exc
        if not isinstance(text, str):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Generation response is malformed", 502)
        try:
            return GenerateResponse(
                text=text,
                model_key=request.binding.model_key,
                model_version=request.binding.model_version,
                usage=self._usage(response),
            )
        except ValidationError as exc:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Generation response is malformed", 502) from exc

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        # The deployed local vLLM profile may not expose a rerank endpoint.  It
        # must report this honestly; the facade will never manufacture scores
        # or swap to a different binding.
        del query, documents
        raise MkbError("INFERENCE_CONFIG_RERANK_UNAVAILABLE", "Reranking is not bound", 503)

    async def probe(self) -> bool:
        try:
            async with httpx.AsyncClient(
                timeout=min(self.timeout_seconds, 5),
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                response = await client.get(f"{self.base_url}/v1/models", headers=self._headers())
                return 200 <= response.status_code < 400
        except (MkbError, httpx.HTTPError):
            return False

    async def _request(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        try:
            async with httpx.AsyncClient(
                timeout=self.timeout_seconds,
                transport=self._transport,
                follow_redirects=False,
            ) as client:
                response = await client.post(f"{self.base_url}{path}", json=payload, headers=self._headers())
        except MkbError:
            raise
        except httpx.RequestError as exc:
            raise MkbError("INFERENCE_TRANSPORT_RETRYABLE", "Inference transport failed", 503) from exc

        if response.status_code in {429, 503} or response.status_code >= 500:
            raise MkbError("INFERENCE_TRANSPORT_RETRYABLE", "Inference service is unavailable", 503)
        if not 200 <= response.status_code < 300:
            raise MkbError("INFERENCE_VALIDATION_REMOTE", "Inference request was rejected", 502)
        try:
            result = response.json()
        except (TypeError, ValueError) as exc:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Inference response is malformed", 502) from exc
        if not isinstance(result, dict):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Inference response is malformed", 502)
        return result

    @classmethod
    def _assert_binding(cls, binding: InferenceBinding) -> None:
        if binding.adapter_kind != cls.adapter_kind:
            raise MkbError("SEC_SUPPLY_UNBOUND", "Inference binding is not registered for this adapter", 503)

    @staticmethod
    def _assert_provider_model(response: dict[str, Any], binding: InferenceBinding) -> None:
        reported_model = response.get("model")
        if reported_model is not None and (
            not isinstance(reported_model, str) or reported_model != binding.model_key
        ):
            raise MkbError("INFERENCE_SPACE_VIOLATION", "Inference response conflicts with the frozen binding", 422)

    @staticmethod
    def _usage(response: dict[str, Any]) -> InferenceUsage | None:
        raw_usage = response.get("usage")
        if raw_usage is None:
            return None
        if not isinstance(raw_usage, dict):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Inference usage is malformed", 502)

        def token_value(*keys: str) -> int | None:
            for key in keys:
                if key not in raw_usage:
                    continue
                value = raw_usage[key]
                if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                    raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Inference usage is malformed", 502)
                return value
            return None

        return InferenceUsage(
            input_tokens=token_value("input_tokens", "prompt_tokens"),
            output_tokens=token_value("output_tokens", "completion_tokens"),
            total_tokens=token_value("total_tokens"),
        )


__all__ = ["LocalVllmAdapter", "SecretValueResolver"]
