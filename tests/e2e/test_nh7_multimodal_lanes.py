"""NH7-T07: five multimodal strategies reach namespaced facet retrieval."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.supply.glyph_ocr_worker import render_fixture_pdf, render_fixture_png
from src.runtime.supply.pdf_parser import build_compressed_pdf_fixture
from tests.e2e.nh7_publication import assert_first_publication_closure
from tests.nh6_runtime_support import browser_settings, local_multimodal_server


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer source-capability-token"}


def _wait(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, object]:
    deadline = time.monotonic() + 60
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_headers())
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.05)
    return latest


def _search(client: TestClient, team_uuid: str, namespace: str, query: str, source_name: str):
    return client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers=_headers(),
        json={
            "schema_version": "mkb.retrieval.v2",
            "team_uuid": team_uuid,
            "namespace_key": namespace,
            "query": query,
            "filters": {"realm": "documentation", "source_name": source_name, "vector_channel": "original"},
            "return_k": 20,
            "recall_k": 100,
        },
    )


def _ingest_upload(
    tmp_path: Path,
    *,
    body: bytes,
    media_type: str,
    strategy: str,
    source_name: str,
    query: str,
) -> None:
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with local_multimodal_server() as (base_url, model_key, payloads):
        app = create_app(
            browser_settings(
                tmp_path,
                internal_token="source-capability-token",
                multimodal_enabled=True,
                multimodal_model_key=model_key,
                multimodal_model_version="v1",
                inference_vllm_base_url=base_url,
            )
        )
        if strategy in {"pdf.ocr", "doc.ocr"}:
            assert app.state.container.deterministic_ocr is not None
        if strategy in {"pdf.document_understanding", "doc.document_understanding", "doc.vision"}:
            assert app.state.container.clean_llm is not None
        with TestClient(app, raise_server_exceptions=True) as client:
            assert (
                client.post(
                    "/v1/teams",
                    headers=_headers(),
                    json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": source_name},
                ).status_code
                == 201
            )
            uploaded = client.post(
                f"/v1/teams/{team_uuid}/objects:upload",
                headers={**_headers(), "content-type": media_type},
                content=body,
            )
            assert uploaded.status_code == 201, uploaded.text
            created = client.post(
                f"/v1/teams/{team_uuid}/tasks",
                headers=_headers(),
                json={
                    "schema_version": "mkb.task.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "request_intent": "intake.ingest",
                    "payload": {
                        "json_prompt_id": "promptB.json.generic",
                        "source": {
                            "source_kind": "local_object",
                            "external_key": source_name,
                            "logical_handle": uploaded.json()["handle"],
                            "media_type": media_type,
                            "clean_strategy": strategy,
                            "realm": "documentation",
                            "type": "article",
                            "channel": "general",
                            "source_name": source_name,
                        },
                    },
                    "audit": {
                        "schema_version": "mkb.task-audit.v1",
                        "team_uuid": team_uuid,
                        "task_uuid": task_uuid,
                        "trace_uuid": trace_uuid,
                        "audit_type": "business_review",
                        "audit_status": "not_required",
                        "source": "nh7-t07",
                        "created_at": utc_now(),
                    },
                },
            )
            assert created.status_code == 201, created.text
            terminal = _wait(client, team_uuid, task_uuid)
            assert terminal["status"] == "succeeded", terminal

            async def inspect() -> tuple[str, str | None]:
                async with app.state.container.persistence.transaction() as tx:
                    namespace = await tx.fetchone(
                        "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                        (team_uuid,),
                    )
                    execution = await tx.fetchone(
                        "SELECT actual_clean_strategy FROM mkb_executions WHERE team_uuid=? AND task_uuid=? "
                        "AND parent_execution_uuid IS NULL",
                        (team_uuid, task_uuid),
                    )
                assert namespace is not None
                strategy_key = None if execution is None else execution["actual_clean_strategy"]
                return str(namespace["namespace_key"]), None if strategy_key is None else str(strategy_key)

            namespace, actual = client.portal.call(inspect)
            assert actual == strategy
            found = _search(client, team_uuid, namespace, query, source_name)
            assert found.status_code == 200, found.text
            assert found.json()["results"]
            if strategy in {"pdf.document_understanding", "doc.vision", "doc.document_understanding"}:
                assert payloads, (strategy, "S11 must receive a live request")
            assert_first_publication_closure(app, client, team_uuid, task_uuid)


def test_pdf_document_understanding_query(tmp_path: Path) -> None:
    _ingest_upload(
        tmp_path,
        body=build_compressed_pdf_fixture("NH7 PDF DU sentinel"),
        media_type="application/pdf",
        strategy="pdf.document_understanding",
        source_name="nh7-pdf-du",
        query="PDF INPUT OBSERVED",
    )


def test_pdf_ocr_query(tmp_path: Path) -> None:
    _ingest_upload(
        tmp_path,
        body=render_fixture_pdf("PDF OCR"),
        media_type="application/pdf",
        strategy="pdf.ocr",
        source_name="nh7-pdf-ocr",
        query="PDF OCR",
    )


def test_doc_document_understanding_query(tmp_path: Path) -> None:
    _ingest_upload(
        tmp_path,
        body=b"NH7 doc llm sentinel reaches retrieval",
        media_type="text/plain",
        strategy="doc.document_understanding",
        source_name="nh7-doc-du",
        query="DOC LLM OBSERVED",
    )


def test_doc_ocr_query(tmp_path: Path) -> None:
    _ingest_upload(
        tmp_path,
        body=render_fixture_png("OCR 2026"),
        media_type="image/png",
        strategy="doc.ocr",
        source_name="nh7-doc-ocr",
        query="OCR 2026",
    )


def test_doc_vision_query(tmp_path: Path) -> None:
    _ingest_upload(
        tmp_path,
        body=render_fixture_png("VISION 2026"),
        media_type="image/png",
        strategy="doc.vision",
        source_name="nh7-doc-vision",
        query="VISION 2026",
    )
