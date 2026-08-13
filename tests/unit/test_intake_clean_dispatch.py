"""Runtime clean step must forward to shipped intake/ entry points."""

from __future__ import annotations

import inspect

import pytest

from intake import dispatch_clean
from src.contracts.common.ids import uuid7
from src.contracts.runtime.models import ProcessCommand
from src.runtime.intake.clean_preflight import IntakeCleanPreflightMixin
from src.runtime.intake.pipeline import IntakePipeline
from src.workflows.lsrag_definition import (
    BUILTIN_DOC_LLM_INTAKE_WORKFLOW,
    BUILTIN_HTTP_BROWSER_INTAKE_WORKFLOW,
    BUILTIN_HTTP_PDF_INTAKE_WORKFLOW,
    BUILTIN_HTTP_STATIC_INTAKE_WORKFLOW,
    BUILTIN_LOCAL_PDF_INTAKE_WORKFLOW,
)


def _command(process_key: str) -> ProcessCommand:
    return ProcessCommand.model_validate(
        {
            "schema_version": "mkb.process-command.v1",
            "team_uuid": uuid7(),
            "task_uuid": uuid7(),
            "trace_uuid": uuid7(),
            "execution_uuid": uuid7(),
            "process_uuid": uuid7(),
            "process_key": process_key,
            "process_contract_version": "v1",
            "fencing_generation": 1,
            "command_input_digest": "c" * 64,
            "input_manifest_ref": "mkbtest:input:x",
            "input_manifest_digest": "a" * 64,
            "config_snapshot_ref": "mkbtest:config:x",
            "config_snapshot_digest": "b" * 64,
            "binding_digest": "d" * 64,
        }
    )


@pytest.mark.asyncio
async def test_dispatch_clean_html_uses_web_channel() -> None:
    result = await dispatch_clean(
        "clean.extract.web",
        text="<article><p>Pipeline web text</p></article>",
        media_type="text/html",
        source_kind="http_resource",
    )
    assert "Pipeline web text" in result.text
    assert result.evidence["channel"] == "web"


@pytest.mark.asyncio
async def test_runtime_clean_step_delegates_to_intake() -> None:
    source = inspect.getsource(IntakeCleanPreflightMixin._clean)
    assert "dispatch_clean" in source
    assert "DeterministicHtmlTextExtractor" not in source
    assert "CLEAN_OCR_CAPABILITY_UNAVAILABLE" not in source
    import src.runtime.intake.types as runtime_intake_types

    assert not hasattr(runtime_intake_types, "_DeterministicHtmlTextExtractor")
    assert not hasattr(runtime_intake_types, "_extract_html_text")
    assert not hasattr(runtime_intake_types, "_clean_text")

    pipeline = IntakePipeline(None, None, None)  # type: ignore[arg-type]
    command = _command("clean.extract.deterministic")
    state = {
        "decoded_text": "<p>Delegated clean</p>",
        "decoded_digest": "e" * 64,
        "media_type": "text/html",
        "source_kind": "inline_payload",
    }
    material, extra, callback = await pipeline._clean(command, state)
    await callback(None, {})  # type: ignore[arg-type]
    assert extra == {}
    assert "Delegated clean" in material.envelope["state"]["clean_text"]
    assert material.envelope["state"]["clean_evidence"]["channel"] in {"web", "doc"}


@pytest.mark.asyncio
async def test_runtime_ocr_uses_injected_intake_llm() -> None:
    class _LLM:
        async def complete(self, **kwargs: object) -> str:
            del kwargs
            return "recognized letters"

    pipeline = IntakePipeline(None, None, None, clean_llm=_LLM())  # type: ignore[arg-type]
    command = _command("clean.ocr.local")
    state = {
        "decoded_text": "",
        "decoded_digest": "f" * 64,
        "media_type": "image/png",
        "source_kind": "local_object",
        "raw_binary_transport": True,
        "raw_text": b"\x89PNG\r\n\x1a\nxx".decode("latin-1"),
    }
    material, _extra, _callback = await pipeline._clean(command, state)
    assert material.envelope["state"]["clean_text"] == "recognized letters"
    assert material.envelope["state"]["clean_evidence"]["channel"] == "doc"


class _RecordingLLM:
    def __init__(self, text: str) -> None:
        self.text = text
        self.calls: list[dict[str, object]] = []

    async def complete(self, **kwargs: object) -> str:
        self.calls.append(kwargs)
        return self.text


@pytest.mark.asyncio
async def test_http_pdf_uses_pdf_channel_and_injected_llm() -> None:
    llm = _RecordingLLM("HTTP PDF understood via LLM")
    result = await dispatch_clean(
        "clean.extract.deterministic",
        text="decoded layer ignored when llm+blob present",
        blob=b"%PDF-1.4 http-acquired",
        media_type="application/pdf",
        source_kind="http_resource",
        llm=llm,
    )
    assert result.evidence["channel"] == "pdf"
    assert result.text == "HTTP PDF understood via LLM"
    assert llm.calls and llm.calls[0].get("blob") == b"%PDF-1.4 http-acquired"

    pipeline = IntakePipeline(None, None, None, clean_llm=llm)  # type: ignore[arg-type]
    material, _extra, _callback = await pipeline._clean(
        _command("clean.extract.deterministic"),
        {
            "decoded_text": "layer",
            "decoded_digest": "1" * 64,
            "media_type": "application/pdf",
            "source_kind": "http_resource",
            "raw_binary_transport": True,
            "raw_text": b"%PDF-1.4 http-acquired".decode("latin-1"),
        },
    )
    assert material.envelope["state"]["clean_evidence"]["channel"] == "pdf"
    assert material.envelope["state"]["clean_text"] == "HTTP PDF understood via LLM"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("process_key", "state", "expect_channel", "expect_text"),
    [
        (
            "clean.extract.web",
            {
                "decoded_text": "<p>Live web process</p>",
                "decoded_digest": "2" * 64,
                "media_type": "text/html",
                "source_kind": "http_resource",
            },
            "web",
            "Live web process",
        ),
        (
            "clean.extract.pdf_llm",
            {
                "decoded_text": "pdf layer",
                "decoded_digest": "3" * 64,
                "media_type": "application/pdf",
                "source_kind": "http_resource",
                "raw_binary_transport": True,
                "raw_text": b"%PDF-1.4 x".decode("latin-1"),
            },
            "pdf",
            "doc-or-pdf-llm",
        ),
        (
            "clean.extract.doc_llm",
            {
                "decoded_text": "general notes",
                "decoded_digest": "4" * 64,
                "media_type": "text/plain",
                "source_kind": "local_object",
            },
            "doc",
            "doc-or-pdf-llm",
        ),
    ],
)
async def test_live_process_keys_reach_dispatch_clean(
    process_key: str,
    state: dict[str, object],
    expect_channel: str,
    expect_text: str,
) -> None:
    llm = _RecordingLLM("doc-or-pdf-llm")
    pipeline = IntakePipeline(None, None, None, clean_llm=llm)  # type: ignore[arg-type]
    material, extra, callback = await pipeline._clean(_command(process_key), state)
    await callback(None, {})  # type: ignore[arg-type]
    assert extra == {}
    cleaned = material.envelope["state"]["clean_text"]
    assert expect_text in cleaned
    assert material.envelope["state"]["clean_evidence"]["channel"] == expect_channel
    assert material.envelope["output"]["clean_candidate"]["evidence"]["channel"] == expect_channel


def test_live_source_profiles_declare_channel_clean_keys() -> None:
    assert "clean.extract.web" in BUILTIN_HTTP_STATIC_INTAKE_WORKFLOW.required_process_keys
    assert "clean.extract.web" in BUILTIN_HTTP_BROWSER_INTAKE_WORKFLOW.required_process_keys
    assert "clean.extract.pdf_llm" in BUILTIN_HTTP_PDF_INTAKE_WORKFLOW.required_process_keys
    assert "clean.extract.pdf_llm" in BUILTIN_LOCAL_PDF_INTAKE_WORKFLOW.required_process_keys
    assert "clean.extract.doc_llm" in BUILTIN_DOC_LLM_INTAKE_WORKFLOW.required_process_keys
