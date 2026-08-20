"""NS6-T04: probe's 5s timeout must not freeze later generate() calls."""

from __future__ import annotations

import asyncio

import httpx
import pytest

from src.contracts.inference.models import GenerateRequest, InferenceBinding
from src.llm_adapters.local_vllm import LocalVllmAdapter

_DIGEST = "a" * 64


class _TimeoutAwareTransport(httpx.AsyncBaseTransport):
    async def handle_async_request(self, request: httpx.Request) -> httpx.Response:
        if request.method == "GET":
            return httpx.Response(200, json={"data": [{"id": "qwen-generate"}]})
        await asyncio.sleep(6)
        return httpx.Response(
            200,
            json={
                "model": "qwen-generate",
                "choices": [{"message": {"content": "ok", "role": "assistant"}}],
                "usage": {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 2},
            },
        )


@pytest.mark.asyncio
async def test_probe_does_not_freeze_generate_timeout() -> None:
    transport = _TimeoutAwareTransport()
    adapter = LocalVllmAdapter(
        "http://127.0.0.1:668",
        timeout_seconds=30,
        generate_timeout_seconds=180,
        transport=transport,
    )
    assert await adapter.probe("qwen-generate") is True
    client = adapter._shared_client()
    original_post = client.post
    post_timeouts: list[object] = []

    async def tracking_post(*args: object, **kwargs: object) -> httpx.Response:
        post_timeouts.append(kwargs.get("timeout"))
        return await original_post(*args, **kwargs)

    client.post = tracking_post  # type: ignore[method-assign]
    response = await adapter.generate(
        GenerateRequest(
            team_uuid="team-a",
            binding=InferenceBinding(
                capability_key="text_generate",
                adapter_kind="local_vllm",
                model_key="qwen-generate",
                model_version="v1",
                binding_digest=_DIGEST,
            ),
            prompt_ref="mkbtest:prompt",
            prompt_digest=_DIGEST,
            input_text="hello",
        )
    )
    assert response.text == "ok"
    assert post_timeouts == [180.0]
    await adapter.aclose()
