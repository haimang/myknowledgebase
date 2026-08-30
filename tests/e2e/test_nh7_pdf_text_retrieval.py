"""NH7-T04: real PDF text-layer ingest reaches namespaced retrieval."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.supply.pdf_parser import IsolatedPdfParser, build_compressed_pdf_fixture
from tests.e2e.nh7_publication import assert_first_publication_closure
from tests.e2e.test_source_capability_paths import _settings
from tests.nh6_runtime_support import local_spa_server


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer source-capability-token"}


def _wait(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, object]:
    deadline = time.monotonic() + 40
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_headers())
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def test_http_pdf_text_layer_namespace_hit(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    assert isinstance(app.state.container.pdf_parser, IsolatedPdfParser)
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    marker = "NH7 PDF text-layer sentinel"
    with local_spa_server() as (origin, _spa), TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_headers(),
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-pdf"},
            ).status_code
            == 201
        )
        # The fixture server serves a compressed PDF at /document.pdf.
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
                        "source_kind": "http_resource",
                        "external_key": "nh7-http-pdf",
                        "url": f"{origin}/document.pdf",
                        "acquisition_mode": "pdf",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-pdf-http",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t04",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal

        async def namespace_key() -> str:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["namespace_key"])

        namespace = client.portal.call(namespace_key)
        found = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_headers(),
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": namespace,
                "query": "pdf capability text",
                "filters": {"source_name": "nh7-pdf-http", "vector_channel": "original"},
                "return_k": 20,
                "recall_k": 100,
            },
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"]
        assert_first_publication_closure(app, client, team_uuid, task_uuid)
        del marker


def test_local_upload_pdf_text_layer_namespace_hit(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    fixture = build_compressed_pdf_fixture("NH7 uploaded PDF sentinel")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_headers(),
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-pdf-upload"},
            ).status_code
            == 201
        )
        uploaded = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**_headers(), "content-type": "application/pdf"},
            content=fixture,
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
                        "external_key": "nh7-local-pdf",
                        "logical_handle": uploaded.json()["handle"],
                        "media_type": "application/pdf",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-pdf-local",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t04",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal

        async def namespace_key() -> str:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["namespace_key"])

        namespace = client.portal.call(namespace_key)
        found = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_headers(),
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": namespace,
                "query": "NH7 uploaded PDF sentinel",
                "filters": {"source_name": "nh7-pdf-local", "vector_channel": "original"},
                "return_k": 20,
                "recall_k": 100,
            },
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"]
        assert_first_publication_closure(app, client, team_uuid, task_uuid)


def test_absent_text_layer_zero_vector(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    fixture = build_compressed_pdf_fixture("")
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_headers(),
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-pdf-absent"},
            ).status_code
            == 201
        )
        uploaded = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**_headers(), "content-type": "application/pdf"},
            content=fixture,
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
                        "external_key": "nh7-absent-pdf",
                        "logical_handle": uploaded.json()["handle"],
                        "media_type": "application/pdf",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-pdf-absent",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t04",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "failed", terminal

        async def vector_count() -> int:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=?",
                    (team_uuid,),
                )
            return int(row["n"]) if row is not None else -1

        assert client.portal.call(vector_count) == 0
