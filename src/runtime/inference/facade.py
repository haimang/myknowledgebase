"""Capability-oriented inference facade with bounded retries and no silent swap."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable

from src.contracts.common.errors import MkbError
from src.contracts.inference.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerateRequest,
    GenerateResponse,
)
from src.llm_adapters.base import InferenceAdapter


class InferenceFacade:
    def __init__(self, adapter: InferenceAdapter, *, max_in_flight: int = 8, max_attempts: int = 3) -> None:
        self._adapter = adapter
        self._semaphore = asyncio.Semaphore(max_in_flight)
        self._max_attempts = max_attempts

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        return await self._call(lambda: self._adapter.embed(request))

    async def generate(self, request: GenerateRequest) -> GenerateResponse:
        return await self._call(lambda: self._adapter.generate(request))

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        return await self._call(lambda: self._adapter.rerank(query, documents))

    async def probe(self) -> bool:
        return await self._adapter.probe()

    async def _call(self, operation: Callable[[], Awaitable[object]]) -> object:
        if self._semaphore.locked() and self._semaphore._value <= 0:  # noqa: SLF001 - no wait policy
            raise MkbError("INFERENCE_BACKPRESSURE", "Inference concurrency gate is full", 503)
        acquired = False
        try:
            await self._semaphore.acquire()
            acquired = True
            last_error: MkbError | None = None
            for attempt in range(self._max_attempts):
                try:
                    return await operation()
                except MkbError as exc:
                    last_error = exc
                    if exc.code != "INFERENCE_TRANSPORT_RETRYABLE" or attempt + 1 == self._max_attempts:
                        raise
                    await asyncio.sleep(min(0.1 * (2**attempt), 2.0))
            raise MkbError("INFERENCE_TRANSPORT_EXHAUSTED", "Inference transport was exhausted", 503) from last_error
        except MkbError as exc:
            if exc.code == "INFERENCE_TRANSPORT_RETRYABLE":
                raise MkbError("INFERENCE_TRANSPORT_EXHAUSTED", "Inference transport was exhausted", 503) from exc
            raise
        finally:
            if acquired:
                self._semaphore.release()
