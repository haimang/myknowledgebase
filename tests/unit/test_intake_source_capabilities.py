"""Focused S05 source/decode/clean capability witnesses."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import ObjectHandle
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.http_acquisition import HttpAcquirer, HttpAcquisitionResult, redacted_url_identity
from src.runtime.intake_pipeline import IntakePipeline
from src.runtime.security import EgressPolicy
from src.services.config_snapshots import ConfigSnapshotService
from src.services.workflow_registry import WorkflowRegistryService
from src.workflows.builtin_lsrag import SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS


class _ObjectFixture:
    def __init__(self, values: dict[str, bytes]) -> None:
        self.values = values

    async def read_verified(self, team_uuid: str, handle: ObjectHandle) -> bytes:
        del team_uuid
        return self.values[handle.value]


def _command(process_key: str = "intake.acquire.inline") -> ProcessCommand:
    digest = "0" * 64
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=uuid7(),
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        process_key=process_key,
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbobj:v1:input",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbobj:v1:config",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )


@pytest.mark.asyncio
async def test_http_acquirer_returns_redacted_final_representation_evidence() -> None:
    request_url = "https://public.example/path?credential=never-durable"

    def resolver(hostname: str, port: int) -> list[str]:
        assert hostname == "public.example"
        assert port == 443
        return ["8.8.8.8"]

    acquirer = HttpAcquirer(
        EgressPolicy(resolver=resolver),
        transport=httpx.MockTransport(
            lambda request: httpx.Response(
                200,
                content=b"response bytes",
                headers={"content-type": "Text/HTML; charset=UTF-8"},
                request=request,
            )
        ),
    )
    result = await acquirer.acquire(request_url)
    evidence = result.evidence()

    assert evidence["request_url_identity"] == redacted_url_identity(request_url)
    assert evidence["final_url_identity"] == redacted_url_identity(request_url)
    assert result.response_media_type == "text/html"
    assert evidence["raw_byte_digest"] == hashlib.sha256(b"response bytes").hexdigest()
    assert evidence["raw_byte_size"] == len(b"response bytes")
    assert "credential=never-durable" not in json.dumps(evidence)


def test_redacted_url_identity_uses_the_canonical_uri_minimum() -> None:
    canonical = "https://example.test/path?scope=public"
    assert redacted_url_identity("HTTPS://EXAMPLE.TEST:443/path?scope=public#ignored") == redacted_url_identity(canonical)
    # Userinfo is not an identity coordinate and never becomes part of a
    # durable witness (the egress policy rejects it before any real request).
    assert redacted_url_identity("https://secret@example.test/path?scope=public") == redacted_url_identity(canonical)


@pytest.mark.asyncio
async def test_local_object_html_uses_structural_clean_and_nfc_lf_decode() -> None:
    handle = "mkbobj:v1:local-html"
    raw = b"<main>Hello\r\nCafe\xcc\x81<script>ignore me</script><p>world</p></main>"
    pipeline = IntakePipeline(None, _ObjectFixture({handle: raw}), None)  # type: ignore[arg-type]
    command = _command()

    acquired = await pipeline._acquire_content(
        command,
        {
            "source_kind": "local_object",
            "external_key": "local-html",
            "logical_handle": handle,
            "media_type": "text/html",
        },
    )
    assert acquired.media_type == "text/html"
    assert acquired.evidence["acquisition_capability"] == "intake.acquire.local_object"
    assert acquired.evidence["detected_media_type"] == "text/html"

    state: dict[str, Any] = {
        "raw_text": acquired.raw_text,
        "raw_binary_transport": acquired.is_binary,
        "raw_byte_digest": acquired.evidence["raw_byte_digest"],
        "media_type": acquired.media_type,
    }
    decoded, _, _ = await pipeline._decode(_command("intake.decode.text_json_html"), state)
    decoded_state = decoded.envelope["state"]
    assert decoded_state["decoded_text"] == "<main>Hello\nCafé<script>ignore me</script><p>world</p></main>"
    cleaned, _, _ = await pipeline._clean(_command("clean.extract.deterministic"), decoded_state)
    assert cleaned.envelope["state"]["clean_text"] == "Hello Café world"
    assert cleaned.envelope["state"]["clean_evidence"]["removed_tag_counts"] == {"script": 1}


@pytest.mark.asyncio
async def test_http_static_browser_and_pdf_profiles_have_distinct_evidence() -> None:
    static_response = HttpAcquisitionResult(
        body=b'<html><body><h1>static</h1></body></html>',
        initial_url_identity="a" * 64,
        final_url_identity="b" * 64,
        response_media_type="text/html",
        status_code=200,
        redirect_count=1,
    )
    pdf = b"%PDF-1.4\n1 0 obj << /Type /Page >>\nstream\nBT (PDF source text) Tj ET\nendstream\nendobj\n"
    pipeline = IntakePipeline(
        None,
        _ObjectFixture({}),
        None,
        http_fetcher=lambda _: static_response,
        browser_fetcher=lambda _: "<main>browser rendered text</main>",
    )  # type: ignore[arg-type]
    command = _command()

    static = await pipeline._acquire_content(
        command,
        {"source_kind": "http_resource", "external_key": "s", "url": "https://example.test/s", "acquisition_mode": "static"},
    )
    assert static.evidence["acquisition_capability"] == "intake.acquire.http_static"
    assert static.evidence["request_url_identity"] == "a" * 64
    assert static.evidence["final_url_identity"] == "b" * 64
    assert static.evidence["response_media_type"] == "text/html"
    assert static.evidence["raw_byte_digest"] == hashlib.sha256(static_response.body).hexdigest()

    browser = await pipeline._acquire_content(
        command,
        {"source_kind": "http_resource", "external_key": "b", "url": "https://example.test/b", "acquisition_mode": "browser"},
    )
    assert browser.evidence["acquisition_capability"] == "intake.acquire.http_browser"
    assert browser.evidence["representation_kind"] == "rendered"
    assert browser.evidence["browser_profile"] == "injected-browser-renderer.v1"

    pipeline._http_fetcher = lambda _: pdf
    acquired_pdf = await pipeline._acquire_content(
        command,
        {"source_kind": "http_resource", "external_key": "p", "url": "https://example.test/p", "acquisition_mode": "pdf"},
    )
    assert acquired_pdf.media_type == "application/pdf"
    assert acquired_pdf.evidence["acquisition_capability"] == "intake.acquire.http_static"
    decoded, _, _ = await pipeline._decode(
        _command("intake.decode.pdf"),
        {
            "raw_text": acquired_pdf.raw_text,
            "raw_binary_transport": True,
            "raw_byte_digest": acquired_pdf.evidence["raw_byte_digest"],
            "media_type": acquired_pdf.media_type,
        },
    )
    assert decoded.envelope["state"]["decoded_text"] == "PDF source text"
    assert decoded.envelope["state"]["decode_evidence"]["decode_capability"] == "intake.decode.pdf"


@pytest.mark.asyncio
async def test_browser_ocr_and_vision_are_explicit_controlled_capability_failures() -> None:
    pipeline = IntakePipeline(None, _ObjectFixture({}), None, http_fetcher=lambda _: b"image")  # type: ignore[arg-type]
    with pytest.raises(MkbError) as browser:
        await pipeline._acquire_content(
            _command(),
            {"source_kind": "http_resource", "external_key": "b", "url": "https://example.test/b", "acquisition_mode": "browser"},
        )
    assert browser.value.code == "ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE"

    with pytest.raises(MkbError) as ocr:
        await pipeline._clean(
            _command("clean.ocr.local"),
            {"decoded_text": "", "media_type": "image/png"},
        )
    assert ocr.value.code == "CLEAN_OCR_CAPABILITY_UNAVAILABLE"
    with pytest.raises(MkbError) as vision:
        await pipeline._clean(
            _command("clean.extract.vision"),
            {"decoded_text": "", "media_type": "image/png"},
        )
    assert vision.value.code == "CLEAN_VISION_CAPABILITY_UNAVAILABLE"


def test_preflight_requires_frozen_capability_and_lineage_evidence() -> None:
    clean_digest = stable_digest({"text": "clean"})
    decoded_digest = stable_digest(
        {"canonicalizer": "intake.decode.text_json_html", "media_type": "text/plain", "text": "clean"}
    )
    candidate_root_digest = stable_digest({"external_key": "inline", "clean_digest": clean_digest})
    valid = {
        "source_kind": "inline_payload",
        "source": {"source_kind": "inline_payload"},
        "normalized_external_key": "inline",
        "media_type": "text/plain",
        "decoded_text": "clean",
        "decoded_digest": decoded_digest,
        "clean_text": "clean",
        "candidate_root_digest": candidate_root_digest,
        "acquisition_evidence": {
            "schema_version": "mkb.acquisition-evidence.v1",
            "source_kind": "inline_payload",
            "acquisition_capability": "intake.acquire.inline",
            "raw_byte_digest": "d" * 64,
            "raw_byte_size": 5,
            "verified_media_type": "text/plain",
        },
        "decode_evidence": {"decode_capability": "intake.decode.text_json_html"},
        "clean_evidence": {"clean_capability": "clean.extract.deterministic", "input_decoded_digest": decoded_digest},
        "clean_digest": clean_digest,
    }
    checks = IntakePipeline._validate_single_preflight_evidence(valid)
    assert [check["result"] for check in checks] == ["passed"] * 4

    invalid = {**valid, "acquisition_evidence": {**valid["acquisition_evidence"], "raw_byte_size": 0}}
    with pytest.raises(MkbError) as error:
        IntakePipeline._validate_single_preflight_evidence(invalid)
    assert error.value.code == "PREFLIGHT_EVIDENCE_INVALID"

    tampered_lineage = {**valid, "clean_digest": "e" * 64}
    with pytest.raises(MkbError) as lineage_error:
        IntakePipeline._validate_single_preflight_evidence(tampered_lineage)
    assert lineage_error.value.code == "PREFLIGHT_EVIDENCE_INVALID"


@pytest.mark.asyncio
async def test_source_profiles_resolve_to_distinct_executable_workflow_capabilities(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "source-profile-workflows.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    registry = WorkflowRegistryService(persistence)
    try:
        await registry.bootstrap()
        cases = {
            "inline_payload": (
                "inline_payload",
                None,
                ("intake.acquire.inline", "intake.decode.text_json_html", "clean.extract.deterministic"),
            ),
            "local_object": (
                "local_object",
                "local_object",
                ("intake.acquire.local_object", "intake.decode.text_json_html", "clean.extract.deterministic"),
            ),
            "local_pdf": (
                "local_object",
                "local_object.pdf",
                ("intake.acquire.local_object", "intake.decode.pdf", "clean.extract.pdf_text"),
            ),
            "http_static": (
                "http_resource",
                "http_resource.static",
                ("intake.acquire.http_static", "intake.decode.text_json_html", "clean.extract.web"),
            ),
            "http_browser": (
                "http_resource",
                "http_resource.browser",
                ("intake.acquire.http_browser", "intake.decode.text_json_html", "clean.extract.web"),
            ),
            "http_pdf": (
                "http_resource",
                "http_resource.pdf",
                ("intake.acquire.http_static", "intake.decode.pdf", "clean.extract.pdf_text"),
            ),
            "local_ocr": (
                "local_object",
                "local_object.image",
                ("intake.acquire.local_object", "intake.decode.text_json_html", "clean.ocr.local"),
            ),
        }
        for profile, (kind, explicit_profile, expected_keys) in cases.items():
            identity = await registry.resolve_for_source("intake.ingest", kind, explicit_profile)
            expected_key = SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.get(explicit_profile or kind)
            assert identity.workflow_key == expected_key, profile
            async with persistence.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT process_key FROM mkb_workflow_steps WHERE workflow_revision_uuid=? "
                    "AND step_kind='process' ORDER BY order_hint",
                    (identity.workflow_revision_uuid,),
                )
            process_keys = [row["process_key"] for row in rows]
            for expected in expected_keys:
                assert expected in process_keys, (profile, expected)

        for workflow_key, clean_key in (
            ("intake.ingest.single.vision-rejected.lsrag.v1", "clean.extract.vision"),
            ("intake.ingest.single.doc-llm.lsrag.v1", "clean.extract.doc_llm"),
        ):
            identity = await registry.resolve_by_key(workflow_key)
            async with persistence.transaction() as tx:
                steps = await tx.fetchall(
                    "SELECT process_key FROM mkb_workflow_steps WHERE workflow_revision_uuid=? AND step_kind='process'",
                    (identity.workflow_revision_uuid,),
                )
            assert clean_key in [row["process_key"] for row in steps]
    finally:
        await persistence.close()


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ({"source_kind": "inline_payload", "external_key": "inline", "content": "body"}, "inline_payload"),
        (
            {
                "source_kind": "local_object",
                "external_key": "local",
                "logical_handle": "mkbobj:v1:local",
                "media_type": "text/html",
            },
            "local_object",
        ),
        (
            {
                "source_kind": "local_object",
                "external_key": "pdf",
                "logical_handle": "mkbobj:v1:pdf",
                "media_type": "application/pdf",
            },
            "local_object.pdf",
        ),
        (
            {
                "source_kind": "local_object",
                "external_key": "image",
                "logical_handle": "mkbobj:v1:image",
                "media_type": "image/png",
            },
            "local_object.image",
        ),
        (
            {
                "source_kind": "http_resource",
                "external_key": "web",
                "url": "https://public.example/web",
                "acquisition_mode": "browser",
            },
            "http_resource.browser",
        ),
        (
            {
                "source_kind": "http_resource",
                "external_key": "pdf-web",
                "url": "https://public.example/document.pdf",
                "acquisition_mode": "pdf",
            },
            "http_resource.pdf",
        ),
    ],
)
def test_config_snapshot_profile_selector_is_descriptor_bounded(source: dict[str, object], expected: str) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    from src.contracts.api.models import TaskCreateRequest

    request = TaskCreateRequest.model_validate(
        {
            "schema_version": "mkb.task.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "request_intent": "intake.ingest",
            "payload": {"source": source},
            "audit": {
                "schema_version": "mkb.task-audit.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit_type": "business_review",
                "audit_status": "not_required",
                "source": "test",
                "created_at": "2026-01-01T00:00:00Z",
            },
        }
    )
    assert ConfigSnapshotService._source_profile(request) == expected
