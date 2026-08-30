"""NH6-T01: real isolated PDF text supply through the default composition root."""

from __future__ import annotations

import asyncio
import inspect
import subprocess
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.intake.acquisition_ingest import IntakeAcquisitionIngestMixin
from src.runtime.intake.types import _extract_pdf_text
from src.runtime.supply.pdf_parser import IsolatedPdfParser, build_compressed_pdf_fixture
from tests.local_runtime import local_mock_settings


def _encrypt_pdf(tmp_path: Path, source: bytes) -> bytes:
    source_path = tmp_path / "source.pdf"
    encrypted_path = tmp_path / "encrypted.pdf"
    source_path.write_bytes(source)
    completed = subprocess.run(
        (
            "/usr/bin/gs",
            "-q",
            "-dBATCH",
            "-dNOPAUSE",
            "-sDEVICE=pdfwrite",
            "-dEncryptionR=3",
            "-dKeyLength=128",
            "-sOwnerPassword=nh6-owner",
            "-sUserPassword=nh6-user",
            f"-sOutputFile={encrypted_path}",
            str(source_path),
        ),
        capture_output=True,
        check=False,
        timeout=15,
    )
    assert completed.returncode == 0, completed.stderr.decode("utf-8", errors="replace")
    return encrypted_path.read_bytes()


def _cid_without_unicode_fixture() -> bytes:
    # A structurally valid Type0/CID declaration with no character content.
    # The contract allows a typed observation when no Unicode mapping exists.
    return build_compressed_pdf_fixture("").replace(
        b"/Subtype /Type1 /BaseFont /Helvetica",
        b"/Subtype /Type0 /BaseFont /Identity-H /Encoding /Identity-H",
    )


def _settings(tmp_path: Path):
    return local_mock_settings(
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        internal_token="nh6-pdf-parser",
    )


def _task(team_uuid: str, task_uuid: str, trace_uuid: str, handle: str) -> dict[str, object]:
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {
            "json_prompt_id": "promptB.json.generic",
            "source": {
                "source_kind": "local_object",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "nh6-real-parser",
                "external_key": "nh6-compressed-pdf",
                "logical_handle": handle,
                "media_type": "application/pdf",
            },
        },
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nh6-t01",
            "created_at": utc_now(),
        },
    }


def _await_terminal(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 30
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def test_compressed_tounicode_extracts_text() -> None:
    parser = IsolatedPdfParser.discover()
    result = asyncio.run(parser.parse(build_compressed_pdf_fixture("NH6 compressed Unicode text")))
    assert result.text_layer == "present"
    assert result.text == "NH6 compressed Unicode text"
    assert result.parser_identity == "pdf.parse.v1"


def test_cid_font_extracts_unicode_or_typed() -> None:
    result = asyncio.run(IsolatedPdfParser.discover().parse(_cid_without_unicode_fixture()))
    assert result.text_layer in {"absent", "corrupt"}
    assert not (result.text_layer == "present" and not result.text.strip())


def test_absent_text_layer_typed_absent() -> None:
    result = asyncio.run(IsolatedPdfParser.discover().parse(build_compressed_pdf_fixture("")))
    assert result.text_layer == "absent"
    assert result.text == ""


def test_encrypted_typed_encrypted(tmp_path: Path) -> None:
    encrypted = _encrypt_pdf(tmp_path, build_compressed_pdf_fixture("protected NH6 text"))
    result = asyncio.run(IsolatedPdfParser.discover().parse(encrypted))
    assert result.text_layer == "encrypted"
    assert result.text == ""


def test_literal_regex_is_not_authority() -> None:
    fixture = build_compressed_pdf_fixture("only inside a compressed stream")
    observed, evidence = _extract_pdf_text(fixture)
    supplied = asyncio.run(IsolatedPdfParser.discover().parse(fixture))
    assert evidence["text_layer"] == "absent"
    assert observed == ""
    assert supplied.text_layer == "present"
    assert "compressed stream" in supplied.text
    assert "_extract_pdf_text" not in inspect.getsource(IntakeAcquisitionIngestMixin._decode)


def test_create_app_parser_extracts_tounicode_without_patch(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    container = app.state.container
    assert isinstance(container.pdf_parser, IsolatedPdfParser)
    assert container.workflow_worker.handler._pdf_parser is container.pdf_parser  # noqa: SLF001
    headers = {"Authorization": "Bearer nh6-pdf-parser"}
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    fixture = build_compressed_pdf_fixture("NH6 default root parser marker")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh6-parser"},
            ).status_code
            == 201
        )
        uploaded = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**headers, "content-type": "application/pdf"},
            content=fixture,
        )
        assert uploaded.status_code == 201, uploaded.text
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task(team_uuid, task_uuid, trace_uuid, uploaded.json()["handle"]),
        )
        assert created.status_code == 201, created.text
        terminal = _await_terminal(client, team_uuid, task_uuid, headers)
        assert terminal["status"] == "succeeded", terminal

        async def inspect_decode() -> dict[str, object] | None:
            async with container.persistence.transaction() as tx:
                return await tx.fetchone(
                    "SELECT f.text_layer,f.capability FROM mkb_representation_facts f "
                    "JOIN mkb_processes p ON p.process_uuid=f.process_uuid "
                    "WHERE p.team_uuid=? AND p.task_uuid=? AND f.fact_kind='decode'",
                    (team_uuid, task_uuid),
                )

        fact = client.portal.call(inspect_decode)
    assert fact == {"text_layer": "present", "capability": "intake.decode.pdf"}
