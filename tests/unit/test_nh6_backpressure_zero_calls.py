"""NH6-T08 L1: each named supply gate rejects before binary/model calls."""

from __future__ import annotations

import hashlib

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.inference.models import MultimodalGenerateRequest, MultimodalGenerateResponse
from src.runtime.http_acquisition import HttpAcquisitionResult
from src.runtime.inference.facade import ConcurrencyGate, InferenceFacade
from src.runtime.inference.multimodal import configured_multimodal_binding
from src.runtime.supply.browser import HardenedBrowserRuntime
from src.runtime.supply.glyph_ocr_worker import render_fixture_png
from src.runtime.supply.pdf_parser import IsolatedPdfParser, build_compressed_pdf_fixture


@pytest.mark.asyncio
async def test_full_gate_zero_parser_calls() -> None:
    gate = ConcurrencyGate(4, capability_limits={"pdf.parse": 1})
    parser = IsolatedPdfParser.discover(gate=gate)
    held = await gate.try_acquire("pdf.parse")
    assert held is not None
    before = parser.subprocess_call_count
    try:
        with pytest.raises(MkbError) as raised:
            await parser.parse(build_compressed_pdf_fixture("must not spawn"))
    finally:
        await gate.release(held)
    assert raised.value.code == "INFERENCE_BACKPRESSURE"
    assert parser.subprocess_call_count == before


class _Acquirer:
    calls = 0

    async def acquire(self, _url: str) -> HttpAcquisitionResult:
        self.calls += 1
        return HttpAcquisitionResult(
            body=b"<!doctype html><main>bounded</main>",
            initial_url_identity="a" * 64,
            final_url_identity="a" * 64,
            response_media_type="text/html",
            status_code=200,
            redirect_count=0,
        )


@pytest.mark.asyncio
async def test_full_gate_zero_browser_render_and_print_calls() -> None:
    gate = ConcurrencyGate(
        4,
        capability_limits={"browser.render": 1, "browser.print_pdf": 1},
    )
    runtime = HardenedBrowserRuntime.discover(acquirer=_Acquirer(), gate=gate)  # type: ignore[arg-type]
    for capability, operation in (
        ("browser.render", runtime.render),
        ("browser.print_pdf", runtime.print_pdf),
    ):
        held = await gate.try_acquire(capability)
        assert held is not None
        before = dict(runtime.invocation_counts)
        try:
            with pytest.raises(MkbError) as raised:
                await operation("https://public.example/")
        finally:
            await gate.release(held)
        assert raised.value.code == "INFERENCE_BACKPRESSURE"
        assert runtime.invocation_counts == before


class _MultimodalAdapter:
    adapter_kind = "local_vllm"
    base_url = "http://127.0.0.1:668"
    secret_slot = None

    def __init__(self) -> None:
        self.calls = 0

    async def multimodal_generate(self, request: MultimodalGenerateRequest) -> MultimodalGenerateResponse:
        self.calls += 1
        return MultimodalGenerateResponse(
            text="unexpected",
            model_key=request.binding.model_key,
            model_version=request.binding.model_version,
        )


@pytest.mark.asyncio
async def test_full_gate_zero_multimodal_adapter_calls() -> None:
    gate = ConcurrencyGate(4, capability_limits={"s11.multimodal": 1})
    adapter = _MultimodalAdapter()
    facade = InferenceFacade(adapter, gate=gate)  # type: ignore[arg-type]
    media = render_fixture_png("GATED")
    request = MultimodalGenerateRequest(
        team_uuid="nh6-team",
        binding=configured_multimodal_binding(model_key="mkb/glyph-vision-5x7", model_version="v1"),
        prompt_ref="promptA.default@v1",
        prompt_digest="a" * 64,
        prompt_text="Read the glyphs.",
        media_type="image/png",
        media_digest=hashlib.sha256(media).hexdigest(),
        media_bytes=media,
        purpose="vision",
    )
    held = await gate.try_acquire("s11.multimodal")
    assert held is not None
    try:
        with pytest.raises(MkbError) as raised:
            await facade.multimodal_generate(request)
    finally:
        await gate.release(held)
    assert raised.value.code == "INFERENCE_BACKPRESSURE"
    assert adapter.calls == 0
