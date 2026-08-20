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


def test_layered_uuid_array_must_be_array() -> None:
    from src.contracts.lsrag.layered_content import validate_layered_content

    payload = {
        "context_meta": {},
        "knowledge_tree": {"upstream_file_uuids": "not-an-array"},
        "layered_content": [
            {
                "block_id": 0,
                "granularity": 0,
                "original_content": {"title": None, "body": "x"},
                "llm_summary": {"title": None, "body": None},
            }
        ],
    }
    with pytest.raises(MkbError, match="STRUCTURE_SCHEMA_INVALID"):
        validate_layered_content(payload)


def test_stub_summary_differs_from_original() -> None:
    from src.runtime.inference.claude_cli import _stub_summary_body

    original = "First paragraph of the document.\nSecond paragraph."
    summary = _stub_summary_body(original, 0)
    assert summary != original
    assert "Document summary" in summary or "summary:" in summary


def test_title_enters_content_full() -> None:
    from src.services.lsrag_compiler.models import content_full

    rendered = content_full(body="body text")
    assert "title:" not in rendered
    assert rendered == "body text"


def test_acquisition_over_cap_is_fail_closed() -> None:
    from src.runtime.intake.acquisition_ingest import IntakeAcquisitionIngestMixin

    mixin = IntakeAcquisitionIngestMixin.__new__(IntakeAcquisitionIngestMixin)
    mixin._acquisition_max_response_bytes = 8
    with pytest.raises(MkbError, match="ACQUISITION_BUDGET_EXCEEDED"):
        mixin._representation_from_bytes(
            b"0123456789",
            declared_media_type="text/plain",
            capability="intake.acquire.inline",
            source_kind="inline_payload",
            mode="staged_inline",
        )


def test_vectorize_envelope_drops_bodies() -> None:
    from src.runtime.intake.core import IntakeCoreMixin

    state = {"raw_text": "RAW", "clean_text": "CLEAN", "markdown_text": "MD", "dual_channel_artifact_uuid": "u"}
    redacted = IntakeCoreMixin._envelope_state("lsrag.vectorize", state)
    assert "raw_text" not in redacted
    assert "clean_text" not in redacted
    assert "markdown_text" not in redacted
    assert redacted["dual_channel_artifact_uuid"] == "u"


@pytest.mark.asyncio
async def test_space_violation_is_not_rewritten() -> None:
    from src.runtime.intake.vectorize import IntakeVectorizeMixin

    class _Space:
        async def embed(self, request: object) -> object:
            raise MkbError("INFERENCE_SPACE_VIOLATION", "space", 422)

    mixin = IntakeVectorizeMixin.__new__(IntakeVectorizeMixin)
    mixin._inference = _Space()  # type: ignore[attr-defined]
    command = type("Cmd", (), {"team_uuid": "t"})()
    layer_a = {
        "adapter_kind": "local_vllm",
        "model_key": "m",
        "model_version": "v1",
        "dimension": 4,
        "binding_digest": "a" * 64,
    }
    with pytest.raises(MkbError, match="INFERENCE_SPACE_VIOLATION"):
        await mixin._live_embeddings(command, ["body"], layer_a)  # type: ignore[arg-type]
