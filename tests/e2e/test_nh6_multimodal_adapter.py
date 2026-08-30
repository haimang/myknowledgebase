"""NH6-T06 L3: default-root adapter reaches a real local media endpoint."""

from __future__ import annotations

import asyncio
import hashlib
import inspect
from pathlib import Path

import pytest

from api.app import create_app
from intake.types import CleanPrompt
from src.contracts.common.errors import MkbError
from src.runtime.inference.claude_cli import ClaudeCliCleanLanguageModel
from src.runtime.inference.multimodal import S11CleanLanguageModel
from src.runtime.supply.glyph_ocr_worker import render_fixture_png
from src.runtime.supply.pdf_parser import build_compressed_pdf_fixture
from tests.local_runtime import local_mock_settings
from tests.nh6_runtime_support import local_multimodal_server


def test_adapter_transports_media_not_string_content(tmp_path: Path) -> None:
    with local_multimodal_server() as (base_url, model_key, payloads):
        settings = local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            inference_vllm_base_url=base_url,
            multimodal_enabled=True,
            multimodal_model_key=model_key,
            multimodal_model_version="v1",
            internal_token="nh6-multimodal",
        )
        app = create_app(settings)
        model = app.state.container.clean_llm
        assert isinstance(model, S11CleanLanguageModel)
        assert app.state.container.workflow_worker.handler._clean_llm is model  # noqa: SLF001
        prompt_text = "Read the visible glyphs and return only their text."
        prompt = CleanPrompt(
            key="promptA.default",
            version="v1",
            text=prompt_text,
            content_sha256=hashlib.sha256(prompt_text.encode()).hexdigest(),
        )
        result = asyncio.run(
            model.complete_bound(
                team_uuid="nh6-team",
                prompt=prompt,
                blob=render_fixture_png("VISION 2026"),
                media_type="image/png",
                purpose="vision",
            )
        )
        pdf_result = asyncio.run(
            model.complete_bound(
                team_uuid="nh6-team",
                prompt=prompt,
                blob=build_compressed_pdf_fixture("PDF multimodal bytes"),
                media_type="application/pdf",
                purpose="document_understanding",
            )
        )
    assert result == "VISION 2026"
    assert pdf_result == "PDF INPUT OBSERVED"
    assert len(payloads) == 2
    user_content = payloads[0]["messages"][-1]["content"]  # type: ignore[index]
    assert isinstance(user_content, list)
    assert any(part.get("type") == "image_url" for part in user_content)
    pdf_content = payloads[1]["messages"][-1]["content"]  # type: ignore[index]
    assert any(
        part.get("image_url", {}).get("url", "").startswith("data:application/pdf;base64,") for part in pdf_content
    )
    source = inspect.getsource(__import__(__name__, fromlist=["*"]))
    assert "_clean" + "_llm =" not in source


@pytest.mark.asyncio
async def test_cli_still_rejects_binary() -> None:
    model = ClaudeCliCleanLanguageModel(cli=None, system_prompt_file=Path("prompt.md"))  # type: ignore[arg-type]
    with pytest.raises(MkbError) as raised:
        await model.complete(prompt="x", blob=b"%PDF-1.7", media_type="application/pdf")
    assert raised.value.code == "CLEAN_MEDIA_UNSUPPORTED"
