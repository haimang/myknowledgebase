"""NH3-T03: PDF representation observation is not an OCR capability result."""

from __future__ import annotations

import inspect

import pytest

from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.runtime.models import ProcessCommand
from src.runtime.intake.pipeline import IntakePipeline
from src.runtime.intake.types import _extract_pdf_text


class _ObservedPdf:
    def __init__(self, blob: bytes) -> None:
        self.text, self._evidence = _extract_pdf_text(blob)

    def evidence(self) -> dict[str, object]:
        return dict(self._evidence)


class _RepresentationObserverPort:
    async def parse(self, blob: bytes) -> _ObservedPdf:
        return _ObservedPdf(blob)


@pytest.mark.parametrize(
    ("blob", "expected", "expected_text"),
    [
        (
            b"%PDF-1.4\n1 0 obj << /Type /Page >> stream BT (visible text) Tj ET endstream endobj\n",
            "present",
            "visible text",
        ),
        (b"%PDF-1.4\n1 0 obj << /Type /Page /Subtype /Image >> endobj\n%%EOF", "absent", ""),
        (b"%PDF-1.7\n1 0 obj << /Encrypt 2 0 R >> endobj\n%%EOF", "encrypted", ""),
        (b"not-a-pdf", "corrupt", ""),
        (b"%PDF-broken", "corrupt", ""),
    ],
)
def test_pdf_observation_matrix(blob: bytes, expected: str, expected_text: str) -> None:
    text, evidence = _extract_pdf_text(blob)
    assert evidence["text_layer"] == expected
    assert text == expected_text
    assert evidence["decoder"] == "bounded-pdf-representation-observer.v1"


def _command() -> ProcessCommand:
    digest = "a" * 64
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        step_key="decode_pdf",
        process_key="intake.decode.pdf",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:input",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:config",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )


@pytest.mark.asyncio
async def test_absent_pdf_layer_is_successful_decode_observation() -> None:
    blob = b"%PDF-1.4\n1 0 obj << /Type /Page /Subtype /Image >> endobj\n%%EOF"
    raw_digest = stable_digest({"fixture": "absent"})
    pipeline = IntakePipeline(None, None, None, pdf_parser=_RepresentationObserverPort())  # type: ignore[arg-type]
    material, _, _ = await pipeline._decode(  # noqa: SLF001
        _command(),
        {
            "raw_text": blob.decode("latin-1"),
            "raw_binary_transport": True,
            "raw_byte_digest": raw_digest,
            "raw_byte_size": len(blob),
            "declared_media_type": "application/pdf",
            "detected_media_type": "application/pdf",
            "media_type": "application/pdf",
            "acquisition_evidence": {"representation_kind": "transferred"},
        },
    )
    state = material.envelope["state"]
    assert state["decoded_text"] == ""
    assert state["decode_evidence"]["text_layer"] == "absent"
    assert set(state["representation_fact"]) == {
        "representation_fact_uuid",
        "representation_fact_digest",
    }
    assert "CLEAN_OCR_CAPABILITY_UNAVAILABLE" not in inspect.getsource(_extract_pdf_text)
