"""NH5-T02/T03: all four source kinds persist the same six-key authority."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.http_acquisition import HttpAcquisitionResult, redacted_url_identity
from tests.e2e.test_source_capability_paths import _settings

SEMANTICS = {
    "realm": "documentation",
    "type": "article",
    "channel": "general",
    "source_name": "nh5-four-kind",
    "context_tags": ["phase:nh5"],
}


def _body(team_uuid: str, source: dict) -> dict:
    task_uuid, trace_uuid = uuid7(), uuid7()
    return {
        "schema_version": "mkb.task.v1",
        "team_uuid": team_uuid,
        "task_uuid": task_uuid,
        "trace_uuid": trace_uuid,
        "request_intent": "intake.ingest",
        "payload": {"json_prompt_id": "promptB.json.generic", "source": source},
        "audit": {
            "schema_version": "mkb.task-audit.v1",
            "team_uuid": team_uuid,
            "task_uuid": task_uuid,
            "trace_uuid": trace_uuid,
            "audit_type": "business_review",
            "audit_status": "not_required",
            "source": "nh5-four-kind",
            "created_at": utc_now(),
        },
    }


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str]) -> dict:
    deadline = time.monotonic() + 30
    latest = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def test_four_kinds_persist_nonstub_six_tuple_with_provenance(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer source-capability-token"}

    def static_fetch(url: str) -> HttpAcquisitionResult:
        body = b"<article>NH5 HTTP semantic body</article>"
        identity = redacted_url_identity(url)
        return HttpAcquisitionResult(
            body=body,
            initial_url_identity=identity,
            final_url_identity=identity,
            response_media_type="text/html",
            status_code=200,
            redirect_count=0,
        )

    app.state.container.workflow_worker.handler._http_fetcher = static_fetch  # type: ignore[attr-defined]
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh5-four-kind"},
        ).status_code == 201
        uploaded = client.post(
            f"/v1/teams/{team_uuid}/objects:upload",
            headers={**headers, "content-type": "text/plain"},
            content=b"NH5 local semantic body",
        )
        assert uploaded.status_code == 201, uploaded.text
        sources = [
            {
                "source_kind": "inline_payload",
                "external_key": "nh5-inline",
                "content": "NH5 inline semantic body",
                **SEMANTICS,
            },
            {
                "source_kind": "local_object",
                "external_key": "nh5-local",
                "logical_handle": uploaded.json()["handle"],
                "media_type": "text/plain",
                **SEMANTICS,
            },
            {
                "source_kind": "http_resource",
                "external_key": "nh5-http",
                "url": "https://public.example/nh5",
                "acquisition_mode": "static",
                **SEMANTICS,
            },
            {
                "source_kind": "registered_api",
                "external_key": "nh5-api",
                "connector_key": "nh5.fixture",
                "provider": "chinatax",
                "operation": "get_articles",
                "definition_version": "v1",
                "records": [
                    {
                        "id": "nh5-tax",
                        "label": "公告",
                        "column": "政策法规",
                        "title": "NH5 tax semantic title",
                        "content": "NH5 tax semantic body",
                        "xxgk_aging": "全文有效",
                    }
                ],
                "exhaustion_proof": "caller_frozen_records.v1",
            },
        ]
        for source in sources:
            request = _body(team_uuid, source)
            created = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=request)
            assert created.status_code == 201, created.text
            terminal = _wait(client, team_uuid, request["task_uuid"], headers)
            assert terminal["status"] == "succeeded", (source["source_kind"], terminal)

        async def semantics() -> list[dict]:
            async with app.state.container.persistence.transaction() as tx:
                return await tx.fetchall(
                    "SELECT s.source_kind,v.semantic_key,v.value_text,v.value_int,v.value_provenance "
                    "FROM mkb_intake_revision_semantics v "
                    "JOIN mkb_intake_revisions r ON r.team_uuid=v.team_uuid "
                    "AND r.intake_revision_uuid=v.intake_revision_uuid "
                    "JOIN mkb_intake_items i ON i.team_uuid=r.team_uuid AND i.intake_item_uuid=r.intake_item_uuid "
                    "JOIN mkb_intake_sources s ON s.team_uuid=i.team_uuid AND s.intake_source_uuid=i.intake_source_uuid "
                    "WHERE v.team_uuid=? ORDER BY s.source_kind,v.semantic_key",
                    (team_uuid,),
                )

        rows = client.portal.call(semantics)
    six = {"realm", "type", "channel", "source_name", "is_active", "context_tags"}
    for kind in ("inline_payload", "local_object", "http_resource", "registered_api"):
        selected = [row for row in rows if row["source_kind"] == kind]
        keys = {row["semantic_key"] for row in selected}
        assert six <= keys
        filter_blob = next(row["value_text"] for row in selected if row["semantic_key"] == "filter_metadata")
        assert filter_blob != f'{{"source_kind":"{kind}"}}'
        by_key = {row["semantic_key"]: row for row in selected}
        if kind == "registered_api":
            assert all(by_key[key]["value_provenance"] == "mapper" for key in six)
        else:
            assert by_key["realm"]["value_provenance"] == "caller"
            assert by_key["is_active"]["value_provenance"] == "system"


def test_public_generic_missing_semantics_rejected_without_task(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    headers = {"Authorization": "Bearer source-capability-token"}
    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh5-reject"},
        ).status_code == 201
        request = _body(
            team_uuid,
            {"source_kind": "inline_payload", "external_key": "missing-semantics", "content": "body"},
        )
        response = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=request)
        assert response.status_code == 422

        async def count() -> dict:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_tasks WHERE team_uuid=?", (team_uuid,))
            assert row is not None
            return row

        assert client.portal.call(count) == {"count": 0}
