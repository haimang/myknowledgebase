"""NH7-T05: declared browser reacquire of an empty SPA reaches retrieval."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.supply.browser import HardenedBrowserRuntime
from tests.e2e.test_source_capability_paths import _settings
from tests.nh6_runtime_support import local_spa_server


def _headers() -> dict[str, str]:
    return {"Authorization": "Bearer source-capability-token"}


def _wait(client: TestClient, team_uuid: str, task_uuid: str) -> dict[str, object]:
    deadline = time.monotonic() + 50
    latest: dict[str, object] = {}
    while time.monotonic() < deadline:
        response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=_headers())
        assert response.status_code == 200, response.text
        latest = response.json()
        if latest["status"] in {"succeeded", "failed", "cancelled"}:
            return latest
        time.sleep(0.05)
    return latest


def test_absent_main_text_declared_browser_dom_query(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    assert isinstance(app.state.container.browser_runtime, HardenedBrowserRuntime)
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with local_spa_server() as (origin, marker), TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_headers(),
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-browser"},
            ).status_code
            == 201
        )
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
                        "external_key": "nh7-empty-spa",
                        "url": f"{origin}/empty-spa",
                        "acquisition_mode": "static",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-browser-source",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t05",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal

        async def inspect() -> tuple[str, int]:
            async with app.state.container.persistence.transaction() as tx:
                namespace = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
                browser_rows = await tx.fetchone(
                    "SELECT COUNT(*) AS n FROM mkb_processes WHERE team_uuid=? AND task_uuid=? "
                    "AND process_key='intake.acquire.http_browser' AND status='succeeded'",
                    (team_uuid, task_uuid),
                )
            assert namespace is not None and browser_rows is not None
            return str(namespace["namespace_key"]), int(browser_rows["n"])

        namespace, browser_ok = client.portal.call(inspect)
        assert browser_ok == 1
        found = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=_headers(),
            json={
                "schema_version": "mkb.retrieval.v2",
                "team_uuid": team_uuid,
                "namespace_key": namespace,
                "query": marker,
                "filters": {"source_name": "nh7-browser-source", "vector_channel": "original"},
                "return_k": 20,
                "recall_k": 100,
            },
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"]


def test_present_or_unknown_does_not_materialize_browser(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with local_spa_server() as (origin, _marker), TestClient(app, raise_server_exceptions=True) as client:
        assert (
            client.post(
                "/v1/teams",
                headers=_headers(),
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-static-present"},
            ).status_code
            == 201
        )
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
                        "external_key": "nh7-present-html",
                        "url": f"{origin}/static",
                        "acquisition_mode": "static",
                        "realm": "documentation",
                        "type": "article",
                        "channel": "general",
                        "source_name": "nh7-present-source",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh7-t05",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        terminal = _wait(client, team_uuid, task_uuid)
        assert terminal["status"] == "succeeded", terminal

        async def browser_count() -> int:
            async with app.state.container.persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT COUNT(*) AS n FROM mkb_processes WHERE team_uuid=? AND task_uuid=? "
                    "AND process_key='intake.acquire.http_browser'",
                    (team_uuid, task_uuid),
                )
            return int(row["n"]) if row is not None else -1

        assert client.portal.call(browser_count) == 0
