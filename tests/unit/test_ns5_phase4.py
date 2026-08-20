"""NS5 Phase 4 serving correctness (T30–T47 subset)."""

from __future__ import annotations

import pytest

from intake.text import extract_html_text
from src.contracts.common.errors import MkbError
from src.runtime.intake.types import _extract_pdf_text
from src.runtime.workflow.dispatch import OVER_BUDGET_PROCESS_KEYS
from src.services.vector_purge import VectorGenerationPurger


def test_html_extract_keeps_paragraph_breaks() -> None:
    text, _meta = extract_html_text("<p>A</p><p>B</p>")
    assert "A" in text and "B" in text
    assert "\n" in text


def test_pdf_rejects_latin1_garbage() -> None:
    blob = b"%PDF-1.4\n(" + bytes(range(0x80, 0xC0)) + b") Tj\n"
    with pytest.raises(MkbError, match="DECODE_PDF_INVALID|CLEAN_OCR"):
        _extract_pdf_text(blob)


def test_partial_channel_purge_is_rejected() -> None:
    from src.contracts.vector.models import VectorizeCommand

    command = VectorizeCommand.model_construct(  # type: ignore[call-arg]
        mode="purge_generation",
        team_uuid="11111111-1111-4111-8111-111111111111",
        channel_filter="original",
        target_generation_artifact_uuids=["11111111-1111-4111-8111-111111111112"],
    )
    with pytest.raises(MkbError, match="PURGE_CHANNEL_FILTER_UNSUPPORTED"):
        VectorGenerationPurger._assert_purge_command(command)


def test_construct_over_budget_key_exists() -> None:
    assert "lsrag.construct" in OVER_BUDGET_PROCESS_KEYS
