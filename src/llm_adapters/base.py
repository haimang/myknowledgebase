"""Only this adapter package may know provider HTTP details."""

from __future__ import annotations

from typing import Protocol, runtime_checkable

from src.contracts.inference.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    GenerateRequest,
    GenerateResponse,
)


@runtime_checkable
class InferenceAdapter(Protocol):
    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse: ...

    async def generate(self, request: GenerateRequest) -> GenerateResponse: ...

    async def rerank(self, query: str, documents: list[str]) -> list[float]: ...

    async def probe(self) -> bool: ...
