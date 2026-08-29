"""NH3-T04: a declared browser-print edge records real PDF evidence at L2."""

from __future__ import annotations

import hashlib
import inspect
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.runtime.intake.acquisition_ingest import IntakeAcquisitionIngestMixin
from src.runtime.intake.pipeline import IntakePipeline
from src.runtime.intake.types import BrowserPrintResult
from src.workflows.builtin_lsrag import BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW
from tests.integration.test_nh2_selected_output_control import _seed
from tests.integration.test_nh3_fact_history_uow import _running_process


def _command(ids: dict[str, str], process_uuid: str) -> ProcessCommand:
    digest = stable_digest({"print": process_uuid})
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=ids["team_uuid"],
        task_uuid=ids["task_uuid"],
        trace_uuid=ids["trace_uuid"],
        execution_uuid=ids["execution_uuid"],
        process_uuid=process_uuid,
        step_key="acquire_print",
        process_key="intake.acquire.http_browser",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:input:print",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:config:print",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )


async def _source_definition(persistence) -> None:
    now = utc_now()
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT OR IGNORE INTO mkb_source_kind_definitions "
            "(source_kind,definition_version,definition_digest,descriptor_schema_ref,descriptor_schema_digest,"
            "cardinality,registered_at) VALUES ('http_resource','v1',?,?,?,'single',?)",
            (
                stable_digest({"source": "http_resource"}),
                "mkbtest:schema:http",
                stable_digest({"schema": "http_resource"}),
                now,
            ),
        )


def _state() -> dict[str, object]:
    return {
        "request_intent": "intake.ingest",
        "payload": {
            "source": {
                "source_kind": "http_resource",
                "external_key": "print-example",
                "url": "https://public.example/document",
                "acquisition_mode": "static",
            }
        },
    }


@pytest.mark.asyncio
async def test_print_fact_is_real_pdf_bytes_and_nonconstant_profile(tmp_path: Path) -> None:
    persistence, _, _, identity, ids = await _seed(
        tmp_path, "print-fact", graph=BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW
    )
    profile = "chromium.print_pdf:139.0.7258.154"
    pdf = b"%PDF-1.7\n1 0 obj << /Type /Page >> endobj\n%%EOF"
    pipeline = IntakePipeline(
        persistence,
        None,
        None,
        browser_fetcher=lambda _: BrowserPrintResult(body=pdf, profile_identity=profile),
    )  # type: ignore[arg-type]
    try:
        await _source_definition(persistence)
        process_uuid = await _running_process(
            persistence, identity, ids, step_key="acquire_print", suffix="print"
        )
        material, _, callback = await pipeline._acquire(_command(ids, process_uuid), _state())  # noqa: SLF001
        state = material.envelope["state"]
        assert state["raw_text"].encode("latin-1").startswith(b"%PDF-")
        assert state["acquisition_evidence"]["representation_kind"] == "print_pdf"
        assert state["acquisition_evidence"]["browser_profile"] == profile
        assert state["acquisition_evidence"]["budget_profile"] == "browser-print-pdf.v1"
        async with persistence.transaction() as tx:
            await callback(tx, {})
        async with persistence.transaction() as tx:
            fact = await tx.fetchone(
                "SELECT fact_kind,representation_kind,verified_media_type,profile_identity,raw_byte_digest "
                "FROM mkb_representation_facts WHERE process_uuid=?",
                (process_uuid,),
            )
        assert fact is not None
        assert fact["fact_kind"] == "print"
        assert fact["representation_kind"] == "print_pdf"
        assert fact["verified_media_type"] == "application/pdf"
        assert fact["profile_identity"] == profile
        assert fact["profile_identity"] != "injected-browser-renderer.v1"
        assert fact["raw_byte_digest"] == hashlib.sha256(pdf).hexdigest()
        assert "injected-browser-renderer.v1" not in inspect.getsource(IntakeAcquisitionIngestMixin)
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_missing_browser_typed_fail_does_not_write_rendered(tmp_path: Path) -> None:
    persistence, _, _, identity, ids = await _seed(
        tmp_path, "print-missing", graph=BUILTIN_HTTP_RESOURCE_KIND_WORKFLOW
    )
    pipeline = IntakePipeline(persistence, None, None)  # type: ignore[arg-type]
    try:
        await _source_definition(persistence)
        process_uuid = await _running_process(
            persistence, identity, ids, step_key="acquire_print", suffix="missing"
        )
        with pytest.raises(MkbError) as raised:
            await pipeline._acquire(_command(ids, process_uuid), _state())  # noqa: SLF001
        assert raised.value.code == "ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE"
        assert raised.value.status_code == 503
        async with persistence.transaction() as tx:
            count = await tx.fetchone(
                "SELECT COUNT(*) AS count FROM mkb_representation_facts WHERE process_uuid=?",
                (process_uuid,),
            )
        assert count == {"count": 0}
    finally:
        await persistence.close()
