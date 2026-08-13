"""S05 application-level source profile coverage with controlled transports."""

from __future__ import annotations

import asyncio
import json
import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.models import ObjectHandle, PromoteRequest
from src.runtime.config import Settings
from src.runtime.http_acquisition import HttpAcquisitionResult, redacted_url_identity
from src.storage.local_store import LocalObjectStore


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="source-capability-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        live_inference=False,
        rate_limit_ip_per_min=1_000,
        rate_limit_token_per_min=2_000,
    )


def _task(team_uuid: str, task_uuid: str, trace_uuid: str, source: dict[str, object]) -> dict[str, object]:
    return {
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
            "source": "s05-source-e2e",
            "created_at": utc_now(),
        },
    }


def _await_terminal(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict[str, object]:
    deadline = time.monotonic() + 8
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def test_local_static_browser_and_pdf_sources_produce_distinct_frozen_acquisition_evidence(tmp_path: Path) -> None:
    token = "source-capability-token"
    team_uuid = uuid7()
    app = create_app(_settings(tmp_path))
    container = app.state.container

    local = asyncio.run(
        container.storage.promote(
            b"<article>local capability text</article>",
            PromoteRequest(team_uuid=team_uuid, purpose="process_io", media_type="text/html"),
        )
    )
    static_url = "https://public.example/static?opaque=not-persisted"
    static_bytes = b"<main>static capability text</main>"
    pdf_bytes = b"%PDF-1.4\n1 0 obj << /Type /Page >>\nstream\nBT (pdf capability text) Tj ET\nendstream\nendobj\n"

    def static_fetcher(url: str) -> HttpAcquisitionResult | bytes:
        if url.endswith("/document.pdf"):
            return pdf_bytes
        return HttpAcquisitionResult(
            body=static_bytes,
            initial_url_identity=redacted_url_identity(url),
            final_url_identity=redacted_url_identity(url),
            response_media_type="text/html; charset=utf-8",
            status_code=200,
            redirect_count=0,
        )

    pipeline = container.workflow_worker.handler
    pipeline._http_fetcher = static_fetcher  # type: ignore[attr-defined]
    pipeline._browser_fetcher = lambda _: "<main>browser capability text</main>"  # type: ignore[attr-defined]
    headers = {"Authorization": f"Bearer {token}"}
    cases = [
        (
            "local",
            {
                "source_kind": "local_object",
                "external_key": "source-local",
                "logical_handle": local.handle.value,
                "media_type": "text/html",
            },
            "intake.acquire.local_object",
        ),
        (
            "static",
            {
                "source_kind": "http_resource",
                "external_key": "source-static",
                "url": static_url,
                "acquisition_mode": "static",
            },
            "intake.acquire.http_static",
        ),
        (
            "browser",
            {
                "source_kind": "http_resource",
                "external_key": "source-browser",
                "url": "https://public.example/browser",
                "acquisition_mode": "browser",
            },
            "intake.acquire.http_browser",
        ),
        (
            "pdf",
            {
                "source_kind": "http_resource",
                "external_key": "source-pdf",
                "url": "https://public.example/document.pdf",
                "acquisition_mode": "pdf",
            },
            "intake.acquire.http_static",
        ),
    ]
    task_ids: dict[str, str] = {}

    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.get("/ready").status_code == 200
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "source-paths"},
            ).status_code
            == 201
        )
        for name, source, _capability in cases:
            task_uuid, trace_uuid = uuid7(), uuid7()
            task_ids[name] = task_uuid
            created = client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=headers,
                json=_task(team_uuid, task_uuid, trace_uuid, source),
            )
            assert created.status_code == 201, created.text
        for name, task_uuid in task_ids.items():
            terminal = _await_terminal(client, team_uuid, task_uuid, headers)
            assert terminal["status"] == "succeeded", (name, terminal)

    output_refs: dict[str, str] = {}
    clean_refs: dict[str, tuple[str, str]] = {}
    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        for name, task_uuid in task_ids.items():
            row = connection.execute(
                "SELECT output_manifest_ref FROM mkb_processes "
                "WHERE team_uuid=? AND task_uuid=? AND step_key='acquire' AND status='succeeded'",
                (team_uuid, task_uuid),
            ).fetchone()
            assert row is not None, name
            output_refs[name] = row["output_manifest_ref"]
            clean = connection.execute(
                "SELECT process_key,output_manifest_ref FROM mkb_processes "
                "WHERE team_uuid=? AND task_uuid=? AND step_key='clean' AND status='succeeded'",
                (team_uuid, task_uuid),
            ).fetchone()
            assert clean is not None, name
            clean_refs[name] = (clean["process_key"], clean["output_manifest_ref"])

    store = LocalObjectStore(tmp_path / "objects")
    evidence: dict[str, dict[str, object]] = {}
    for name, output_ref in output_refs.items():
        document = json.loads(
            asyncio.run(store.read_verified(team_uuid, ObjectHandle(value=output_ref))).decode("utf-8")
        )
        evidence[name] = document["output"]["acquisition_evidence"]["evidence"]

    assert evidence["local"]["acquisition_capability"] == "intake.acquire.local_object"
    assert evidence["static"]["acquisition_capability"] == "intake.acquire.http_static"
    assert evidence["browser"]["acquisition_capability"] == "intake.acquire.http_browser"
    assert evidence["browser"]["representation_kind"] == "rendered"
    assert evidence["pdf"]["verified_media_type"] == "application/pdf"
    rendered = json.dumps(evidence["static"])
    assert static_url not in rendered
    assert "opaque=not-persisted" not in rendered

    clean_evidence: dict[str, dict[str, object]] = {}
    for name, (process_key, output_ref) in clean_refs.items():
        document = json.loads(
            asyncio.run(store.read_verified(team_uuid, ObjectHandle(value=output_ref))).decode("utf-8")
        )
        clean_evidence[name] = document["output"]["clean_candidate"]["evidence"]
        assert clean_evidence[name]["clean_capability"] == process_key
    assert clean_refs["static"][0] == "clean.extract.web"
    assert clean_evidence["static"]["strategy"] == "web.deterministic"
    assert clean_refs["pdf"][0] == "clean.extract.pdf_text"
    assert clean_evidence["pdf"]["strategy"] == "pdf.text_layer"


def test_local_image_reaches_the_exact_ocr_workflow_then_fails_closed_when_unconfigured(tmp_path: Path) -> None:
    token = "source-capability-token"
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    app = create_app(_settings(tmp_path))
    image = asyncio.run(
        app.state.container.storage.promote(
            b"\x89PNG\r\n\x1a\nminimal-image-fixture",
            PromoteRequest(team_uuid=team_uuid, purpose="process_io", media_type="image/png"),
        )
    )
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "ocr-refusal"},
            ).status_code
            == 201
        )
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
            json=_task(
                team_uuid,
                task_uuid,
                trace_uuid,
                {
                    "source_kind": "local_object",
                    "external_key": "local-image",
                    "logical_handle": image.handle.value,
                    "media_type": "image/png",
                },
            ),
        )
        assert created.status_code == 201, created.text
        terminal = _await_terminal(client, team_uuid, task_uuid, headers)
        assert terminal["status"] == "failed", terminal

    with sqlite3.connect(tmp_path / "mkb.sqlite3") as connection:
        connection.row_factory = sqlite3.Row
        clean = connection.execute(
            "SELECT process_key,status,error_code FROM mkb_processes "
            "WHERE team_uuid=? AND task_uuid=? AND step_key='clean'",
            (team_uuid, task_uuid),
        ).fetchone()
    assert clean is not None
    assert dict(clean) == {
        "process_key": "clean.ocr.local",
        "status": "failed",
        "error_code": "CLEAN_OCR_CAPABILITY_UNAVAILABLE",
    }
