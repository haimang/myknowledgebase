"""S11/S16 inference facade, audit, and binding-fence contracts."""

from __future__ import annotations

import asyncio
import json
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx
import pytest

from src.contracts.common.errors import MkbError
from src.contracts.inference.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerateRequest,
    GenerateResponse,
    InferenceBinding,
    InferenceInvocationRecord,
    InvocationContext,
    RerankDocument,
    RerankRequest,
    StructuredGenerateRequest,
)
from src.llm_adapters.local_vllm import LocalVllmAdapter
from src.runtime.inference.facade import InferenceFacade
from src.runtime.inference.invocations import SqlInferenceInvocationRecorder
from src.runtime.inference.supply import SupplyBinding, SupplyFence
from src.runtime.metrics import MetricRegistry
from src.runtime.security import SecretResolver
from src.services.registry import SPARK_VL_EMBED_MODEL_KEY

_DIGEST = "a" * 64
_OTHER_DIGEST = "b" * 64


def _binding(
    capability: str = "embed",
    *,
    adapter_kind: str = "local_vllm",
    model_key: str = "embedder",
    model_version: str = "v1",
    digest: str = _DIGEST,
) -> InferenceBinding:
    return InferenceBinding(
        capability_key=capability,
        adapter_kind=adapter_kind,
        model_key=model_key,
        model_version=model_version,
        binding_digest=digest,
    )


def _embedding_request(
    *,
    binding: InferenceBinding | None = None,
    expected_dimension: int | None = None,
) -> EmbeddingRequest:
    return EmbeddingRequest(
        team_uuid="team-a",
        binding=binding or _binding(),
        texts=["private source text"],
        expected_dimension=expected_dimension,
    )


class _Adapter:
    adapter_kind = "local_vllm"

    def __init__(
        self,
        *,
        base_url: str = "https://models.example:8443",
        secret_slot: str | None = None,
        embedding_response: EmbeddingResponse | None = None,
    ) -> None:
        self.base_url = base_url
        self.secret_slot = secret_slot
        self.embedding_response = embedding_response
        self.embed_calls = 0
        self.embed_requests: list[EmbeddingRequest] = []
        self.embed_error: Exception | None = None
        self.generate_response = GenerateResponse(text="ok", model_key="generator", model_version="v1")
        self.rerank_values: list[float] = [0.25, 0.75]

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        self.embed_calls += 1
        self.embed_requests.append(request)
        if self.embed_error is not None:
            raise self.embed_error
        return self.embedding_response or EmbeddingResponse(
            vectors=[[0.25, 0.75]],
            model_key=request.binding.model_key,
            model_version=request.binding.model_version,
            dimension=2,
        )

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        return self.generate_response.model_copy(
            update={
                "model_key": request.binding.model_key,
                "model_version": request.binding.model_version,
            }
        )

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        del query, documents
        return self.rerank_values

    async def probe(self) -> bool:
        return True


@dataclass
class _Recorder:
    records: list[InferenceInvocationRecord] = field(default_factory=list)

    async def record(self, record: InferenceInvocationRecord) -> bool:
        self.records.append(record)
        return True


@pytest.mark.asyncio
async def test_facade_enriches_provenance_and_records_safe_invocation() -> None:
    recorder = _Recorder()
    facade = InferenceFacade(_Adapter(), invocation_recorder=recorder)
    request = _embedding_request()
    request = request.model_copy(
        update={
            "invocation": InvocationContext(
                prompt_content_hash=_DIGEST,
                config_snapshot_digest=_OTHER_DIGEST,
            )
        }
    )

    response = await facade.embed(request)

    assert response.has_complete_provenance()
    assert response.adapter_kind == "local_vllm"
    assert response.model_key == "embedder"
    assert len(recorder.records) == 1
    record = recorder.records[0]
    assert record.status == "succeeded"
    assert record.invocation_uuid == response.invocation_uuid
    assert record.request_digest == response.request_digest
    assert "private source text" not in record.model_dump_json()
    assert record.context is not None
    assert record.context.prompt_content_hash == _DIGEST


@pytest.mark.asyncio
async def test_transport_retries_the_same_frozen_binding_only() -> None:
    adapter = _Adapter()
    attempts = 0

    async def flaky_embed(request: EmbeddingRequest) -> EmbeddingResponse:
        nonlocal attempts
        attempts += 1
        adapter.embed_requests.append(request)
        if attempts < 3:
            raise MkbError("INFERENCE_TRANSPORT_RETRYABLE", "busy", 503)
        return EmbeddingResponse(
            vectors=[[0.25, 0.75]],
            model_key=request.binding.model_key,
            model_version=request.binding.model_version,
            dimension=2,
        )

    adapter.embed = flaky_embed  # type: ignore[method-assign]
    delays: list[float] = []

    async def remember_delay(value: float) -> None:
        delays.append(value)

    facade = InferenceFacade(adapter, max_attempts=3, sleep=remember_delay)
    request = _embedding_request()
    response = await facade.embed(request)

    assert response.has_complete_provenance()
    assert attempts == 3
    assert delays == [1.0, 2.0]
    assert all(item.binding is request.binding for item in adapter.embed_requests)
    assert {item.binding.binding_digest for item in adapter.embed_requests} == {_DIGEST}


@pytest.mark.asyncio
async def test_full_gate_rejects_before_a_second_model_call() -> None:
    adapter = _Adapter()
    started = asyncio.Event()
    release = asyncio.Event()

    async def blocking_embed(request: EmbeddingRequest) -> EmbeddingResponse:
        adapter.embed_calls += 1
        started.set()
        await release.wait()
        return EmbeddingResponse(
            vectors=[[0.25, 0.75]],
            model_key=request.binding.model_key,
            model_version=request.binding.model_version,
            dimension=2,
        )

    adapter.embed = blocking_embed  # type: ignore[method-assign]
    facade = InferenceFacade(adapter, max_in_flight=1)
    first = asyncio.create_task(facade.embed(_embedding_request()))
    await started.wait()
    with pytest.raises(MkbError) as rejected:
        await facade.embed(_embedding_request())
    assert rejected.value.code == "INFERENCE_BACKPRESSURE"
    assert adapter.embed_calls == 1
    release.set()
    await first


@pytest.mark.asyncio
async def test_layer_a_dimension_mismatch_is_fail_closed() -> None:
    adapter = _Adapter(
        embedding_response=EmbeddingResponse(
            vectors=[[0.25, 0.75]],
            model_key="embedder",
            model_version="v1",
            dimension=2,
        )
    )
    facade = InferenceFacade(adapter)

    with pytest.raises(MkbError) as rejected:
        await facade.embed(_embedding_request(expected_dimension=3))

    assert rejected.value.code == "INFERENCE_SPACE_VIOLATION"
    assert adapter.embed_calls == 1


@pytest.mark.asyncio
async def test_typed_rerank_returns_ordered_provenance_complete_result() -> None:
    adapter = _Adapter()
    adapter.rerank_values = [0.1, 0.9]
    facade = InferenceFacade(adapter)
    request = RerankRequest(
        team_uuid="team-a",
        binding=_binding("rerank", model_key="reranker"),
        query="private query",
        documents=[
            RerankDocument(document_id="first", text="first private document"),
            RerankDocument(document_id="second", text="second private document"),
        ],
        top_n=1,
    )

    response = await facade.rerank_typed(request)

    assert response.has_complete_provenance()
    assert [item.document_id for item in response.results] == ["second"]
    assert response.results[0].score == 0.9


@pytest.mark.asyncio
async def test_structured_validation_happens_before_success_audit() -> None:
    adapter = _Adapter()
    adapter.generate_response = GenerateResponse(text="not-json", model_key="generator", model_version="v1")
    recorder = _Recorder()
    facade = InferenceFacade(adapter, invocation_recorder=recorder)
    request = StructuredGenerateRequest(
        team_uuid="team-a",
        binding=_binding("structured_generate", model_key="generator"),
        prompt_ref="prompt",
        prompt_digest=_DIGEST,
        input_text="private prompt",
        json_schema_ref="schema",
        json_schema_digest=_OTHER_DIGEST,
    )

    with pytest.raises(MkbError) as rejected:
        await facade.structured_generate(request)

    assert rejected.value.code == "INFERENCE_VALIDATION_STRUCTURED"
    assert len(recorder.records) == 1
    assert recorder.records[0].status == "failed"
    assert recorder.records[0].error_code == "INFERENCE_VALIDATION_STRUCTURED"


@pytest.mark.asyncio
async def test_supply_fence_rejects_shadow_endpoint_without_calling_adapter() -> None:
    binding = _binding()
    adapter = _Adapter(base_url="https://shadow.example:8443")
    metrics = MetricRegistry()
    fence = SupplyFence(
        [SupplyBinding.from_binding(binding, base_url="https://approved.example:8443", secret_slot=None)]
    )
    facade = InferenceFacade(adapter, supply_fence=fence, metrics=metrics)

    with pytest.raises(MkbError) as rejected:
        await facade.embed(_embedding_request(binding=binding))

    assert rejected.value.code == "SEC_MODEL_ENDPOINT_REJECTED"
    assert adapter.embed_calls == 0
    assert 'mkb_sec_supply_reject_total{code="SEC_MODEL_ENDPOINT_REJECTED"} 1.0' in metrics.render()


@pytest.mark.asyncio
async def test_local_adapter_uses_logical_secret_slot_and_classifies_http_errors() -> None:
    seen_headers: dict[str, str] = {}

    def success_handler(request: httpx.Request) -> httpx.Response:
        seen_headers.update(request.headers)
        assert request.url == "https://models.example:8443/v1/embeddings"
        body = json.loads(request.content)
        assert body["model"] == "embedder"
        return httpx.Response(
            200,
            json={
                "model": "embedder",
                "data": [{"embedding": [0.25, 0.75]}],
                "usage": {"prompt_tokens": 2, "completion_tokens": 0, "total_tokens": 2},
            },
        )

    resolver = SecretResolver({"MODEL_API_KEY": "very-secret-value"})
    adapter = LocalVllmAdapter(
        "https://models.example:8443/",
        secret_slot="MODEL_API_KEY",
        secret_resolver=resolver,
        transport=httpx.MockTransport(success_handler),
    )
    response = await adapter.embed(_embedding_request())

    assert response.usage is not None
    assert response.usage.total_tokens == 2
    assert seen_headers["authorization"] == "Bearer very-secret-value"
    assert not hasattr(adapter, "bearer_token")
    with pytest.raises(ValueError):
        LocalVllmAdapter("https://models.example", bearer_token="very-secret-value")

    rejected = LocalVllmAdapter(
        "https://models.example:8443",
        transport=httpx.MockTransport(lambda request: httpx.Response(400, json={"error": "invalid"})),
    )
    with pytest.raises(MkbError) as invalid:
        await rejected.embed(_embedding_request())
    assert invalid.value.code == "INFERENCE_VALIDATION_REMOTE"

    overloaded = LocalVllmAdapter(
        "https://models.example:8443",
        transport=httpx.MockTransport(lambda request: httpx.Response(429, json={"error": "busy"})),
    )
    with pytest.raises(MkbError) as retryable:
        await overloaded.embed(_embedding_request())
    assert retryable.value.code == "INFERENCE_TRANSPORT_RETRYABLE"


@pytest.mark.asyncio
async def test_local_adapter_sends_catalog_model_and_mrl_dimensions() -> None:
    captured: dict[str, object] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        captured["url"] = str(request.url)
        captured["body"] = json.loads(request.content)
        return httpx.Response(
            200,
            json={
                "model": "LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4",
                "data": [{"embedding": [0.5] * 1024}],
            },
        )

    adapter = LocalVllmAdapter(
        "https://models.example:8443/",
        transport=httpx.MockTransport(handler),
    )
    response = await adapter.embed(
        _embedding_request(
            binding=_binding(model_key=SPARK_VL_EMBED_MODEL_KEY),
            expected_dimension=1024,
        )
    )

    assert captured["url"] == "https://models.example:8443/v1/embeddings"
    assert captured["body"] == {
        "model": SPARK_VL_EMBED_MODEL_KEY,
        "input": ["private source text"],
        "dimensions": 1024,
    }
    assert response.model_key == SPARK_VL_EMBED_MODEL_KEY
    assert response.dimension == 1024


def test_env_inference_token_composes_a_logical_slot(tmp_path) -> None:
    from pydantic import SecretStr

    from api.app import _INFERENCE_VLLM_TOKEN_SLOT, _model_secret_resolver
    from src.runtime.config import Settings

    settings = Settings(
        inference_vllm_token=SecretStr("spark-token"),
        database_path=tmp_path / "unused.sqlite3",
    )
    slot, resolver = _model_secret_resolver(settings)
    assert slot == _INFERENCE_VLLM_TOKEN_SLOT
    assert resolver is not None
    assert resolver.resolve(slot) == "spark-token"
    assert "spark-token" not in repr(resolver)


class _CaptureUnitOfWork:
    def __init__(self) -> None:
        self.sql: str | None = None
        self.params: tuple[Any, ...] | None = None

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        self.sql = sql
        self.params = params


class _CapturePersistence:
    def __init__(self) -> None:
        self.unit_of_work = _CaptureUnitOfWork()

    @asynccontextmanager
    async def transaction(self) -> Any:
        yield self.unit_of_work

    async def readiness(self) -> dict[str, bool]:
        return {"db_primary": True}


@pytest.mark.asyncio
async def test_sql_invocation_recorder_only_persists_allowlisted_provenance() -> None:
    persistence = _CapturePersistence()
    recorder = SqlInferenceInvocationRecorder(persistence)
    stored = await recorder.record(
        InferenceInvocationRecord(
            invocation_uuid="invocation-a",
            team_uuid="team-a",
            capability_key="embed",
            adapter_kind="local_vllm",
            model_key="embedder",
            model_version="v1",
            request_digest=_DIGEST,
            status="succeeded",
            context=InvocationContext(
                prompt_content_hash=_DIGEST,
                schema_content_digest=_OTHER_DIGEST,
            ),
        )
    )

    assert stored is True
    assert persistence.unit_of_work.sql is not None
    assert "mkb_inference_invocations" in persistence.unit_of_work.sql
    assert persistence.unit_of_work.params is not None
    payload_extra = json.loads(persistence.unit_of_work.params[19])
    assert payload_extra == {
        "prompt_content_hash": _DIGEST,
        "schema_content_digest": _OTHER_DIGEST,
    }
