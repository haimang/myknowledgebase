"""NH6-T06 L2: explicit media contract and OpenAI-compatible parts encoding."""

from __future__ import annotations

import hashlib

import httpx
import pytest
from pydantic import ValidationError

from src.contracts.inference.models import MultimodalGenerateRequest
from src.llm_adapters.local_vllm import LocalVllmAdapter
from src.runtime.inference.multimodal import configured_multimodal_binding
from src.runtime.supply.glyph_ocr_worker import render_fixture_png


def _request(*, media_bytes: bytes | None = None, object_handle: str | None = None) -> MultimodalGenerateRequest:
    digest_source = media_bytes or render_fixture_png("HANDLE")
    return MultimodalGenerateRequest(
        team_uuid="nh6-team",
        binding=configured_multimodal_binding(model_key="mkb/glyph-vision-5x7", model_version="v1"),
        prompt_ref="promptA.default@v1",
        prompt_digest="a" * 64,
        prompt_text="Read the visible glyphs.",
        input_text="Return text only.",
        media_type="image/png",
        media_digest=hashlib.sha256(digest_source).hexdigest(),
        media_bytes=media_bytes,
        object_handle=object_handle,
        purpose="vision",
    )


@pytest.mark.asyncio
async def test_bytes_and_handle_plus_promptref() -> None:
    pixels = render_fixture_png("BYTES")
    captured: list[dict[str, object]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        payload = __import__("json").loads(request.content)
        captured.append(payload)
        return httpx.Response(
            200,
            json={
                "model": payload["model"],
                "choices": [{"message": {"content": "BYTES"}}],
            },
        )

    adapter = LocalVllmAdapter("http://127.0.0.1:668", transport=httpx.MockTransport(handler))
    try:
        response = await adapter.multimodal_generate(_request(media_bytes=pixels))
    finally:
        await adapter.aclose()
    assert response.text == "BYTES"
    assert captured
    user_content = captured[0]["messages"][-1]["content"]  # type: ignore[index]
    assert isinstance(user_content, list)
    assert {part["type"] for part in user_content} == {"text", "image_url"}
    assert user_content[-1]["image_url"]["url"].startswith("data:image/png;base64,")

    class _Resolver:
        async def resolve_media(self, team_uuid: str, object_handle: str) -> bytes:
            assert team_uuid == "nh6-team"
            assert object_handle == "mkbobj:v1:nh6-team:fixture"
            return render_fixture_png("HANDLE")

    adapter = LocalVllmAdapter(
        "http://127.0.0.1:668",
        transport=httpx.MockTransport(handler),
        media_resolver=_Resolver(),
    )
    try:
        response = await adapter.multimodal_generate(_request(object_handle="mkbobj:v1:nh6-team:fixture"))
    finally:
        await adapter.aclose()
    assert response.text == "BYTES"


def test_rejects_input_text_only_for_vision() -> None:
    with pytest.raises(ValidationError):
        MultimodalGenerateRequest.model_validate(
            {
                "team_uuid": "nh6-team",
                "binding": configured_multimodal_binding(model_key="mkb/glyph-vision-5x7", model_version="v1"),
                "prompt_ref": "promptA.default@v1",
                "prompt_digest": "a" * 64,
                "prompt_text": "Read the image.",
                "input_text": "base64-looking-text-is-not-media",
                "media_type": "image/png",
                "media_digest": "b" * 64,
                "purpose": "vision",
            }
        )


def test_payload_extra_cannot_smuggle_media() -> None:
    pixels = render_fixture_png("MEDIA")
    with pytest.raises(ValidationError):
        MultimodalGenerateRequest(
            **_request(media_bytes=pixels).model_dump(exclude={"payload_extra"}),
            payload_extra={"content": "data:image/png;base64,hidden"},
        )
