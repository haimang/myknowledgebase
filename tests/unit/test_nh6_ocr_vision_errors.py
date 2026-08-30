"""NH6-T07 L1: deterministic/model-bound classification and typed faults."""

from __future__ import annotations

import inspect
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

from src.contracts.common.errors import MkbError
from src.runtime.config import Settings
from src.runtime.inference.facade import ConcurrencyGate
from src.runtime.supply.deterministic_ocr import IsolatedDeterministicOcr, render_fixture_png


class _SleepingOcr(IsolatedDeterministicOcr):
    def command(self, media_type: str) -> tuple[str, ...]:
        del media_type
        return (sys.executable, "-I", "-c", "import time; time.sleep(30)")


def _ocr(*, timeout: float = 10) -> IsolatedDeterministicOcr:
    return IsolatedDeterministicOcr.discover(
        gate=ConcurrencyGate(4, capability_limits={"ocr.deterministic": 2}),
        timeout_seconds=timeout,
    )


@pytest.mark.asyncio
async def test_empty_output_typed_fail() -> None:
    with pytest.raises(MkbError) as raised:
        await _ocr().recognize(render_fixture_png(" "), media_type="image/png")
    assert raised.value.code == "OCR_EMPTY"


@pytest.mark.asyncio
async def test_bad_bytes_typed_fail() -> None:
    with pytest.raises(MkbError) as raised:
        await _ocr().recognize(b"not-an-image", media_type="image/png")
    assert raised.value.code == "OCR_INPUT_INVALID"


@pytest.mark.asyncio
async def test_timeout_typed_fail() -> None:
    discovered = _ocr(timeout=0.1)
    ocr = _SleepingOcr(
        python_binary=discovered.python_binary,
        worker_path=discovered.worker_path,
        pdftoppm_binary=discovered.pdftoppm_binary,
        unshare_binary=discovered.unshare_binary,
        prlimit_binary=discovered.prlimit_binary,
        setpriv_binary=discovered.setpriv_binary,
        gate=ConcurrencyGate(2, capability_limits={"ocr.deterministic": 1}),
        timeout_seconds=0.1,
    )
    with pytest.raises(MkbError) as raised:
        await ocr.recognize(render_fixture_png("TIMEOUT"), media_type="image/png")
    assert raised.value.code == "OCR_TIMEOUT"
    assert ocr.active_pids == set()
    assert ocr.last_pid is not None and not Path(f"/proc/{ocr.last_pid}").exists()


def test_forbids_cloud_ocr_and_latest_float() -> None:
    with pytest.raises(ValidationError):
        Settings(multimodal_model_version="latest")
    with pytest.raises(ValidationError):
        Settings(multimodal_model_key="vendor:model:latest")
    settings = Settings()
    assert settings.inference_vllm_base_url.startswith("http://127.0.0.1:")
    source = Path("src/runtime/supply/deterministic_ocr.py").read_text(encoding="utf-8").casefold()
    assert all(value not in source for value in ("googleapis.com", "api.openai.com", "cloudflare.com"))


@pytest.mark.asyncio
async def test_deterministic_ocr_has_no_promptref() -> None:
    ocr = _ocr()
    result = await ocr.recognize(render_fixture_png("NO PROMPT"), media_type="image/png")
    assert result.text == "NO PROMPT"
    assert result.evidence()["prompt_ref"] is None
    assert "prompt" not in inspect.signature(ocr.recognize).parameters
