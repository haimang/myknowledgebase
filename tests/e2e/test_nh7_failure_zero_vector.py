"""NH7-T10 L3/L4: failed clean paths leave zero indexed vectors."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.supply.glyph_ocr_worker import render_fixture_png
from tests.e2e.test_registered_api_scatter import _create_team, _task_body
from tests.e2e.test_registered_api_scatter import _settings as _scatter_settings
from tests.e2e.test_source_capability_paths import _settings
from tests.nh6_runtime_support import browser_settings, local_multimodal_server


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer source-capability-token"}


def _wait(client: TestClient, team_uuid: str, task_uuid: str, headers: dict[str, str] | None = None) -> dict[str, object]:
    auth = headers or _headers()
    deadline = time.monotonic() + 40
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=auth)
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.02)
    return latest


def _indexed(app, team_uuid: str, client: TestClient) -> int:
    async def inspect() -> int:
        async with app.state.container.persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT COUNT(*) AS n FROM mkb_vector_records WHERE team_uuid=?",
                (team_uuid,),
            )
        return int(row["n"]) if row is not None else -1

    return client.portal.call(inspect)


def _namespace(app, team_uuid: str, client: TestClient) -> str:
    async def inspect() -> str:
        async with app.state.container.persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                (team_uuid,),
            )
        assert row is not None
        return str(row["namespace_key"])

    return client.portal.call(inspect)


def _seed_legal(client: TestClient, team_uuid: str) -> None:
    task_uuid, trace_uuid = uuid7(), uuid7()
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
                    "source_kind": "inline_payload",
                    "external_key": "nh7-t10-control",
                    "content": "NH7 failure-path control sentinel",
                    "realm": "documentation",
                    "type": "article",
                    "channel": "general",
                    "source_name": "nh7-t10-control",
                },
            },
            "audit": {
                "schema_version": "mkb.task-audit.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit_type": "business_review",
                "audit_status": "not_required",
                "source": "nh7-t10",
                "created_at": utc_now(),
            },
        },
    )
    assert created.status_code == 201, created.text
    assert _wait(client, team_uuid, task_uuid)["status"] == "succeeded"


def test_clean_empty_zero_vector_query(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_headers(),
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-t10-empty"},
            ).status_code
            == 201
        )
        _seed_legal(client, team_uuid)
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
                        "source_kind": "inline_payload",
                        "external_key": "nh7-t10-empty",
                        "content": "   \n\t  ",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-t10-empty",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t10",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "failed", terminal
        namespace = _namespace(app, team_uuid, client)
        empty = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_headers(),
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": namespace,
                "query": "nh7-t10-empty",
                "filters": {"source_name": "nh7-t10-empty", "vector_channel": "original"},
                "return_k": 10,
                "recall_k": 20,
            },
        )
        assert empty.status_code == 200, empty.text
        assert empty.json()["results"] == []
        control = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_headers(),
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": namespace,
                "query": "NH7 failure-path control sentinel",
                "filters": {"realm": "documentation", "vector_channel": "original"},
                "return_k": 10,
                "recall_k": 20,
            },
        )
        assert control.status_code == 200, control.text
        assert control.json()["results"]


def test_empty_member_batch_fail_zero_vector(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer scatter-token"}
    app = create_app(_scatter_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=headers)
        body = _task_body(
            team_uuid=team_uuid,
            task_uuid=uuid7(),
            trace_uuid=uuid7(),
            records=[{"id": "empty-one", "label": "公告", "column": "政策法规", "xxgk_aging": "全文有效"}],
        )
        rejected = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=body)
        assert rejected.status_code == 422, rejected.text
        assert _indexed(app, team_uuid, client) == 0


def test_bad_member_schema_zero_vector(tmp_path: Path) -> None:
    headers = {"Authorization": "Bearer scatter-token"}
    app = create_app(_scatter_settings(tmp_path))
    team_uuid = uuid7()
    with TestClient(app, raise_server_exceptions=True) as client:
        _create_team(client, team_uuid=team_uuid, headers=headers)
        body = _task_body(
            team_uuid=team_uuid,
            task_uuid=uuid7(),
            trace_uuid=uuid7(),
            records=[{"label": "missing-id"}],
        )
        rejected = client.post(f"/v1/teams/{team_uuid}/tasks", headers=headers, json=body)
        assert rejected.status_code == 422, rejected.text
        assert _indexed(app, team_uuid, client) == 0


def test_worker_failure_after_bind_zero_vector(tmp_path: Path) -> None:
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with local_multimodal_server() as (base_url, model_key, _payloads):
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
        with TestClient(app, raise_server_exceptions=True) as client:
            assert (
                client.post(
                    "/v1/teams",
                    headers=_headers(),
                    json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-t10-ocr"},
                ).status_code
                == 201
            )
            uploaded = client.post(
                f"/v1/teams/{team_uuid}/objects:upload",
                headers={**_headers(), "content-type": "image/png"},
                content=render_fixture_png(" "),
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
                            "external_key": "nh7-t10-ocr-empty",
                            "logical_handle": uploaded.json()["handle"],
                            "media_type": "image/png",
                            "clean_strategy": "doc.ocr",
                            "realm": "documentation",
                            "type": "article",
                            "channel": "general",
                            "source_name": "nh7-t10-ocr-empty",
                        },
                    },
                    "audit": {
                        "schema_version": "mkb.task-audit.v1",
                        "team_uuid": team_uuid,
                        "task_uuid": task_uuid,
                        "trace_uuid": trace_uuid,
                        "audit_type": "business_review",
                        "audit_status": "not_required",
                        "source": "nh7-t10",
                        "created_at": utc_now(),
                    },
                },
            )
            assert created.status_code == 201, created.text
            terminal = _wait(client, team_uuid, task_uuid)
            assert terminal["status"] == "failed", terminal
            assert _indexed(app, team_uuid, client) == 0
