"""Capability-oriented inference facade with fences, provenance and bounded load.

The facade never resolves a second model after a transport error.  It receives
an already frozen binding, verifies it against the adapter and optional S16
SupplyFence, and retries only that exact callable while holding a bounded
process-local concurrency gate.
"""

from __future__ import annotations

import asyncio
import json
import math
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any, TypeVar

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.inference.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerateRequest,
    GenerateResponse,
    InferenceBinding,
    InferenceCapability,
    InferenceInvocationRecord,
    InferenceRequest,
    InferenceResult,
    InferenceUsage,
    RerankRequest,
    RerankResponse,
    RerankScore,
    StructuredGenerateRequest,
    StructuredGenerateResponse,
    TextGenerateRequest,
    TextGenerateResponse,
)
from src.llm_adapters.base import InferenceAdapter
from src.runtime.inference.invocations import InferenceInvocationRecorder
from src.runtime.inference.supply import SupplyFence
from src.runtime.metrics import MetricRegistry

_T = TypeVar("_T", bound=InferenceResult)
_V = TypeVar("_V")


def coerce_json_object_text(text: str) -> str:
    """Accept a raw model string, optional fences, and return one JSON object text.

    Extra top-level objects/arrays after the first value are rejected.  A
    first-to-last brace slice would otherwise swallow ``see {a} or {b}``.
    """

    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        stripped = "\n".join(lines).strip()
    if not stripped:
        return stripped
    start = 0 if stripped.startswith("{") else stripped.find("{")
    if start < 0:
        return stripped
    decoder = json.JSONDecoder()
    try:
        _, end = decoder.raw_decode(stripped, start)
    except json.JSONDecodeError as exc:
        raise MkbError("INFERENCE_VALIDATION_STRUCTURED", "Structured model response is not a JSON object", 502) from exc
    rest = stripped[end:].lstrip()
    extra_start = -1
    if rest.startswith("{") or rest.startswith("["):
        extra_start = 0
    else:
        brace = rest.find("{")
        bracket = rest.find("[")
        candidates = [index for index in (brace, bracket) if index >= 0]
        extra_start = min(candidates) if candidates else -1
    if extra_start >= 0:
        try:
            decoder.raw_decode(rest, extra_start)
        except json.JSONDecodeError:
            extra_start = -1
        else:
            raise MkbError(
                "INFERENCE_VALIDATION_STRUCTURED",
                "Structured model response contains multiple top-level values",
                502,
            )
    return stripped[start:end]


@dataclass(frozen=True, slots=True)
class _GateLease:
    capability: str


class ConcurrencyGate:
    """Non-waiting global/per-capability admission gate.

    ``asyncio.Semaphore`` does not expose a safe non-blocking acquire.  A
    short mutex-protected counter makes the backpressure decision atomic while
    retaining the S11 requirement that a full gate performs zero model calls.
    """

    def __init__(self, global_max_in_flight: int, *, capability_limits: Mapping[str, int] | None = None) -> None:
        if not 1 <= global_max_in_flight <= 4_096:
            raise ValueError("global_max_in_flight must be between 1 and 4096")
        normalized = dict(capability_limits or {})
        if any(not isinstance(key, str) or not key or not 1 <= value <= global_max_in_flight for key, value in normalized.items()):
            raise ValueError("capability limits must be positive and bounded by the global limit")
        self._global_max = global_max_in_flight
        self._capability_limits = normalized
        self._global_in_flight = 0
        self._by_capability: dict[str, int] = {}
        self._lock = asyncio.Lock()

    async def try_acquire(self, capability: str) -> _GateLease | None:
        async with self._lock:
            capability_count = self._by_capability.get(capability, 0)
            capability_max = self._capability_limits.get(capability)
            if self._global_in_flight >= self._global_max or (
                capability_max is not None and capability_count >= capability_max
            ):
                return None
            self._global_in_flight += 1
            self._by_capability[capability] = capability_count + 1
            return _GateLease(capability)

    async def release(self, lease: _GateLease) -> None:
        async with self._lock:
            count = self._by_capability.get(lease.capability, 0)
            if self._global_in_flight < 1 or count < 1:
                raise RuntimeError("inference concurrency gate release is unbalanced")
            self._global_in_flight -= 1
            if count == 1:
                self._by_capability.pop(lease.capability, None)
            else:
                self._by_capability[lease.capability] = count - 1

    def in_flight(self, capability: str | None = None) -> int:
        if capability is None:
            return self._global_in_flight
        return self._by_capability.get(capability, 0)


class InferenceFacade:
    """The sole provider-neutral model-call boundary for domain code."""

    def __init__(
        self,
        adapter: InferenceAdapter,
        *,
        max_in_flight: int = 12,
        max_attempts: int = 3,
        capability_limits: Mapping[str, int] | None = None,
        initial_delay_seconds: float = 1.0,
        max_delay_seconds: float = 30.0,
        sleep: Callable[[float], Awaitable[None]] = asyncio.sleep,
        supply_fence: SupplyFence | None = None,
        invocation_recorder: InferenceInvocationRecorder | None = None,
        metrics: MetricRegistry | None = None,
        dispatch_caps: Any | None = None,
        gate: ConcurrencyGate | None = None,
    ) -> None:
        if not 1 <= max_attempts <= 10:
            raise ValueError("max_attempts must be between 1 and 10")
        if initial_delay_seconds < 0 or max_delay_seconds < initial_delay_seconds:
            raise ValueError("inference retry delays are invalid")
        self._adapter = adapter
        self.dispatch_caps = dispatch_caps
        self._gate = gate or ConcurrencyGate(max_in_flight, capability_limits=capability_limits)
        self._max_attempts = max_attempts
        self._initial_delay_seconds = initial_delay_seconds
        self._max_delay_seconds = max_delay_seconds
        self._sleep = sleep
        self._supply_fence = supply_fence
        self._invocation_recorder = invocation_recorder
        self._metrics = metrics

    async def aclose(self) -> None:
        closer = getattr(self._adapter, "aclose", None)
        if closer is not None:
            await closer()

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        response = await self._invoke(
            capability="embed",
            request=request,
            operation=lambda: self._adapter.embed(request),
            validator=lambda raw: self._validate_embedding(request, raw),
        )
        assert isinstance(response, EmbeddingResponse)
        return response

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        """Compatibility generic-generation method; new code chooses a subtype."""

        capability = request.binding.capability_key
        if capability not in {"structured_generate", "text_generate"}:
            raise MkbError("INFERENCE_CONFIG_CAPABILITY", "Generation binding has an unsupported capability", 503)
        response = await self._invoke(
            capability=capability,
            request=request,
            operation=lambda: self._adapter.generate(request),
            validator=self._validate_generation,
        )
        assert isinstance(response, GenerateResponse)
        return response

    async def text_generate(self, request: TextGenerateRequest) -> TextGenerateResponse:
        if request.binding.capability_key != "text_generate":
            raise MkbError("INFERENCE_CONFIG_CAPABILITY", "Text generation requires a text binding", 503)
        response = await self._invoke(
            capability="text_generate",
            request=request,
            operation=lambda: self._adapter.generate(request),
            validator=self._validate_text_generation,
        )
        assert isinstance(response, TextGenerateResponse)
        return response

    async def structured_generate(
        self,
        request: StructuredGenerateRequest,
        *,
        validator: Callable[[dict[str, Any]], _V] | None = None,
    ) -> tuple[StructuredGenerateResponse, _V | None]:
        """Generate JSON and validate it before returning it to a domain caller."""

        if request.binding.capability_key != "structured_generate":
            raise MkbError("INFERENCE_CONFIG_CAPABILITY", "Structured generation requires a structured binding", 503)
        typed_value: _V | None = None

        def validate_structured(raw: InferenceResult) -> StructuredGenerateResponse:
            nonlocal typed_value
            response = self._validate_generation(raw)
            try:
                value = json.loads(coerce_json_object_text(response.text))
            except (TypeError, ValueError) as exc:
                raise MkbError("INFERENCE_VALIDATION_STRUCTURED", "Structured model response is invalid", 502) from exc
            if not isinstance(value, dict):
                raise MkbError("INFERENCE_VALIDATION_STRUCTURED", "Structured model response is invalid", 502)
            try:
                typed_value = validator(value) if validator is not None else None
            except Exception as exc:
                raise MkbError("INFERENCE_VALIDATION_STRUCTURED", "Structured model response is invalid", 502) from exc
            return StructuredGenerateResponse.model_validate(
                {**response.model_dump(mode="python"), "value": value}
            )

        response = await self._invoke(
            capability="structured_generate",
            request=request,
            operation=lambda: self._adapter.generate(request),
            validator=validate_structured,
        )
        assert isinstance(response, StructuredGenerateResponse)
        return response, typed_value

    async def rerank_typed(self, request: RerankRequest) -> RerankResponse:
        if request.binding.capability_key != "rerank":
            raise MkbError("INFERENCE_CONFIG_CAPABILITY", "Rerank requires a rerank binding", 503)

        async def operation() -> RerankResponse:
            scores = await self._adapter.rerank(
                request.query,
                [document.text for document in request.documents],
            )
            if not isinstance(scores, list) or len(scores) != len(request.documents):
                raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Rerank response is malformed", 502)
            try:
                values = [
                    RerankScore(document_id=document.document_id, score=float(score))
                    for document, score in zip(request.documents, scores, strict=True)
                ]
            except (TypeError, ValueError) as exc:
                raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Rerank response is malformed", 502) from exc
            if not all(math.isfinite(item.score) for item in values):
                raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Rerank response is malformed", 502)
            values.sort(key=lambda item: (-item.score, item.document_id))
            if request.top_n is not None:
                values = values[: request.top_n]
            return RerankResponse(
                results=values,
                model_key=request.binding.model_key,
                model_version=request.binding.model_version,
            )

        response = await self._invoke(
            capability="rerank",
            request=request,
            operation=operation,
            validator=self._validate_rerank,
        )
        assert isinstance(response, RerankResponse)
        return response

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        """Legacy score-only seam retained for S10's disabled-by-default reranker.

        A fence-enabled deployment must migrate to ``rerank_typed`` so an exact
        binding and invocation provenance can be supplied.
        """

        if self._supply_fence is not None:
            raise MkbError("INFERENCE_CONFIG_TYPED_RERANK_REQUIRED", "Rerank requires a frozen binding", 503)
        value = await self._legacy_call("rerank", lambda: self._adapter.rerank(query, documents))
        if not isinstance(value, list):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Rerank response is malformed", 502)
        try:
            scores = [float(score) for score in value]
        except (TypeError, ValueError) as exc:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Rerank response is malformed", 502) from exc
        if not all(math.isfinite(score) for score in scores):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Rerank response is malformed", 502)
        return scores

    async def probe(self) -> bool:
        try:
            return bool(await self._adapter.probe())
        except Exception:
            return False

    async def probe_binding(self, binding: InferenceBinding) -> bool:
        """Check an exact binding/fence and then the adapter's bounded probe."""

        try:
            self._preflight(binding.capability_key, binding)
        except MkbError:
            return False
        probe = getattr(self._adapter, "probe", None)
        if probe is None:
            return await self.probe()
        try:
            result = probe(model_key=binding.model_key)
            if hasattr(result, "__await__"):
                result = await result
            return bool(result)
        except TypeError:
            return await self.probe()
        except Exception:
            return False

    async def _invoke(
        self,
        *,
        capability: InferenceCapability,
        request: InferenceRequest,
        operation: Callable[[], Awaitable[InferenceResult]],
        validator: Callable[[InferenceResult], _T],
    ) -> _T:
        invocation_uuid = uuid7()
        request_digest = self._request_digest(capability, request)
        started = time.monotonic()
        try:
            self._preflight(capability, request.binding)
        except MkbError as exc:
            await self._record_failure(invocation_uuid, request_digest, capability, request, exc.code, started)
            raise
        lease = await self._gate.try_acquire(capability)
        if lease is None:
            error = MkbError("INFERENCE_BACKPRESSURE", "Inference concurrency gate is full", 503)
            await self._record_failure(invocation_uuid, request_digest, capability, request, error.code, started)
            raise error
        try:
            for attempt in range(self._max_attempts):
                try:
                    raw = await operation()
                    validated = validator(raw)
                    result = self._with_provenance(
                        validated,
                        binding=request.binding,
                        invocation_uuid=invocation_uuid,
                        request_digest=request_digest,
                        started=started,
                    )
                    await self._record_success(capability, request, result)
                    return result
                except MkbError as exc:
                    if exc.code == "INFERENCE_SPACE_VIOLATION":
                        await self._record_failure(
                            invocation_uuid, request_digest, capability, request, exc.code, started
                        )
                        raise
                    if exc.code == "INFERENCE_TRANSPORT_RETRYABLE" and attempt + 1 < self._max_attempts:
                        await self._gate.release(lease)
                        await self._sleep(self._retry_delay(attempt))
                        lease = await self._gate.try_acquire(capability)
                        if lease is None:
                            error = MkbError("INFERENCE_BACKPRESSURE", "Inference concurrency gate is full", 503)
                            await self._record_failure(
                                invocation_uuid, request_digest, capability, request, error.code, started
                            )
                            raise error from None
                        continue
                    error = (
                        MkbError("INFERENCE_TRANSPORT_EXHAUSTED", "Inference transport was exhausted", 503)
                        if exc.code == "INFERENCE_TRANSPORT_RETRYABLE"
                        else exc
                    )
                    await self._record_failure(invocation_uuid, request_digest, capability, request, error.code, started)
                    raise error from exc
                except Exception as exc:
                    error = MkbError("INFERENCE_INTERNAL_UNEXPECTED", "Inference invocation failed", 503)
                    await self._record_failure(invocation_uuid, request_digest, capability, request, error.code, started)
                    raise error from exc
            raise AssertionError("bounded inference loop should always return or raise")
        finally:
            await self._gate.release(lease)

    async def _legacy_call(self, capability: InferenceCapability, operation: Callable[[], Awaitable[Any]]) -> Any:
        lease = await self._gate.try_acquire(capability)
        if lease is None:
            raise MkbError("INFERENCE_BACKPRESSURE", "Inference concurrency gate is full", 503)
        try:
            for attempt in range(self._max_attempts):
                try:
                    return await operation()
                except MkbError as exc:
                    if exc.code != "INFERENCE_TRANSPORT_RETRYABLE" or attempt + 1 == self._max_attempts:
                        if exc.code == "INFERENCE_TRANSPORT_RETRYABLE":
                            raise MkbError("INFERENCE_TRANSPORT_EXHAUSTED", "Inference transport was exhausted", 503) from exc
                        raise
                    await self._sleep(self._retry_delay(attempt))
            raise AssertionError("bounded inference loop should always return or raise")
        finally:
            await self._gate.release(lease)

    def _preflight(self, capability: InferenceCapability, binding: InferenceBinding) -> None:
        if binding.capability_key != capability:
            raise MkbError("INFERENCE_CONFIG_CAPABILITY", "Inference binding capability does not match the request", 503)
        if getattr(self._adapter, "adapter_kind", None) != binding.adapter_kind:
            self._record_supply_reject("SEC_SUPPLY_UNBOUND")
            raise MkbError("SEC_SUPPLY_UNBOUND", "Inference adapter does not match the frozen binding", 503)
        if self._supply_fence is not None:
            try:
                self._supply_fence.validate(binding, self._adapter)
            except MkbError as exc:
                self._record_supply_reject(exc.code)
                raise

    def _record_supply_reject(self, code: str) -> None:
        if self._metrics is not None:
            self._metrics.increment("mkb_sec_supply_reject_total", code=code)

    @staticmethod
    def _request_digest(capability: InferenceCapability, request: InferenceRequest) -> str:
        material: dict[str, Any] = {
            "capability": capability,
            "team_uuid": request.team_uuid,
            "binding_digest": request.binding.binding_digest,
            "model_key": request.binding.model_key,
            "model_version": request.binding.model_version,
            "adapter_kind": request.binding.adapter_kind,
        }
        if isinstance(request, EmbeddingRequest):
            material["text_digests"] = [stable_digest({"text": text}) for text in request.texts]
            material["expected_dimension"] = request.expected_dimension
        elif isinstance(request, RerankRequest):
            material["query_digest"] = stable_digest({"query": request.query})
            material["documents"] = [
                {"document_id": document.document_id, "text_digest": stable_digest({"text": document.text})}
                for document in request.documents
            ]
            material["top_n"] = request.top_n
        elif isinstance(request, GenerateRequest):
            material["prompt_ref"] = request.prompt_ref
            material["prompt_digest"] = request.prompt_digest
            material["input_digest"] = stable_digest({"input": request.input_text})
            if isinstance(request, StructuredGenerateRequest):
                material["json_schema_ref"] = request.json_schema_ref
                material["json_schema_digest"] = request.json_schema_digest
        return stable_digest(material)

    @staticmethod
    def _validate_embedding(request: EmbeddingRequest, raw: InferenceResult) -> EmbeddingResponse:
        if not isinstance(raw, EmbeddingResponse):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Embedding response is malformed", 502)
        if (
            raw.model_key != request.binding.model_key
            or raw.model_version != request.binding.model_version
            or (raw.adapter_kind is not None and raw.adapter_kind != request.binding.adapter_kind)
            or len(raw.vectors) != len(request.texts)
            or (request.expected_dimension is not None and raw.dimension != request.expected_dimension)
        ):
            raise MkbError("INFERENCE_SPACE_VIOLATION", "Embedding response conflicts with the frozen Layer A", 422)
        try:
            if any(len(vector) != raw.dimension or not all(math.isfinite(float(value)) for value in vector) for vector in raw.vectors):
                raise ValueError("invalid vector")
        except (TypeError, ValueError) as exc:
            raise MkbError("INFERENCE_SPACE_VIOLATION", "Embedding response conflicts with the frozen Layer A", 422) from exc
        return raw

    @staticmethod
    def _validate_generation(raw: InferenceResult) -> GenerateResponse:
        if not isinstance(raw, GenerateResponse) or not isinstance(raw.text, str):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Generation response is malformed", 502)
        return raw

    @classmethod
    def _validate_text_generation(cls, raw: InferenceResult) -> TextGenerateResponse:
        response = cls._validate_generation(raw)
        return TextGenerateResponse.model_validate(response.model_dump(mode="python"))

    @staticmethod
    def _validate_rerank(raw: InferenceResult) -> RerankResponse:
        if not isinstance(raw, RerankResponse) or not raw.results:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Rerank response is malformed", 502)
        if not all(math.isfinite(item.score) for item in raw.results):
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Rerank response is malformed", 502)
        return raw

    @staticmethod
    def _validate_usage(usage: InferenceUsage | None) -> None:
        if usage is None or usage.total_tokens is None:
            return
        known = sum(value or 0 for value in (usage.input_tokens, usage.output_tokens))
        if known > usage.total_tokens:
            raise MkbError("INFERENCE_VALIDATION_RESPONSE", "Inference usage is malformed", 502)

    def _with_provenance(
        self,
        result: _T,
        *,
        binding: InferenceBinding,
        invocation_uuid: str,
        request_digest: str,
        started: float,
    ) -> _T:
        self._validate_usage(result.usage)
        if (
            result.model_key != binding.model_key
            or result.model_version != binding.model_version
            or (result.adapter_kind is not None and result.adapter_kind != binding.adapter_kind)
        ):
            raise MkbError("INFERENCE_SPACE_VIOLATION", "Inference result conflicts with the frozen binding", 422)
        return result.model_copy(
            update={
                "adapter_kind": binding.adapter_kind,
                "latency_ms": max(0, int((time.monotonic() - started) * 1000)),
                "request_digest": request_digest,
                "invocation_uuid": invocation_uuid,
            }
        )

    def _retry_delay(self, attempt: int) -> float:
        import random

        ceiling = min(self._initial_delay_seconds * (2**attempt), self._max_delay_seconds)
        return random.random() * ceiling

    async def _record_success(
        self,
        capability: InferenceCapability,
        request: InferenceRequest,
        result: InferenceResult,
    ) -> None:
        if result.invocation_uuid is None or result.request_digest is None:
            return
        await self._record(
            InferenceInvocationRecord(
                invocation_uuid=result.invocation_uuid,
                team_uuid=request.team_uuid,
                capability_key=capability,
                adapter_kind=request.binding.adapter_kind,
                model_key=request.binding.model_key,
                model_version=request.binding.model_version,
                request_digest=result.request_digest,
                status="succeeded",
                usage=result.usage,
                latency_ms=result.latency_ms,
                context=request.invocation,
            )
        )

    async def _record_failure(
        self,
        invocation_uuid: str,
        request_digest: str,
        capability: InferenceCapability,
        request: InferenceRequest,
        error_code: str,
        started: float,
    ) -> None:
        await self._record(
            InferenceInvocationRecord(
                invocation_uuid=invocation_uuid,
                team_uuid=request.team_uuid,
                capability_key=capability,
                adapter_kind=request.binding.adapter_kind,
                model_key=request.binding.model_key,
                model_version=request.binding.model_version,
                request_digest=request_digest,
                status="failed",
                error_code=error_code,
                latency_ms=max(0, int((time.monotonic() - started) * 1000)),
                context=request.invocation,
            )
        )

    async def _record(self, record: InferenceInvocationRecord) -> None:
        if self._invocation_recorder is None:
            return
        try:
            await self._invocation_recorder.record(record)
        except Exception:
            # A recorder implementation must itself be best-effort.  The
            # facade protects the business caller even if an injected custom
            # recorder violates that contract.
            return


__all__ = ["ConcurrencyGate", "InferenceFacade", "coerce_json_object_text"]
