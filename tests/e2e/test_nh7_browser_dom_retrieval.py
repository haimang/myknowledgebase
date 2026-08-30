"""NH7-T05: declared browser reacquire of an empty SPA reaches retrieval."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.storage.models import ObjectHandle
from src.runtime.inference.claude_cli import DeterministicNs1Stub
from src.runtime.supply.browser import HardenedBrowserRuntime
from tests.e2e.nh7_publication import assert_first_publication_closure
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


def _ingest(
    client: TestClient,
    *,
    team_uuid: str,
    name: str,
    source: dict[str, object],
    audit_source: str = "nh7-t05",
) -> tuple[str, dict[str, object]]:
    task_uuid, trace_uuid = uuid7(), uuid7()
    assert (
        client.post(
            "/v1/teams",
            headers=_headers(),
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": name},
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
            "payload": {"json_prompt_id": "promptB.json.generic", "source": source},
            "audit": {
                "schema_version": "mkb.task-audit.v1",
                "team_uuid": team_uuid,
                "task_uuid": task_uuid,
                "trace_uuid": trace_uuid,
                "audit_type": "business_review",
                "audit_status": "not_required",
                "source": audit_source,
                "created_at": utc_now(),
            },
        },
    )
    assert created.status_code == 201, created.text
    return task_uuid, _wait(client, team_uuid, task_uuid)


def _search(
    client: TestClient,
    team_uuid: str,
    namespace: str,
    query: str,
    filters: dict[str, str],
):
    return client.post(
        f"/v1/teams/{team_uuid}/retrieval:search",
        headers=_headers(),
        json={
            "schema_version": "mkb.retrieval.v2",
            "team_uuid": team_uuid,
            "namespace_key": namespace,
            "query": query,
            "filters": filters,
            "return_k": 20,
            "recall_k": 100,
        },
    )


def test_absent_main_text_declared_browser_dom_query(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    assert isinstance(app.state.container.browser_runtime, HardenedBrowserRuntime)
    team_uuid = uuid7()
    with local_spa_server() as (origin, marker), TestClient(app, raise_server_exceptions=True) as client:
        task_uuid, terminal = _ingest(
            client,
            team_uuid=team_uuid,
            name="nh7-browser",
            source={
                "source_kind": "http_resource",
                "external_key": "nh7-empty-spa",
                "url": f"{origin}/empty-spa",
                "acquisition_mode": "static",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "nh7-browser-source",
            },
        )
        assert terminal["status"] == "succeeded", terminal

        async def inspect() -> tuple[str, int, str | None, str | None]:
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
                fact = await tx.fetchone(
                    "SELECT representation_kind,profile_identity FROM mkb_representation_facts "
                    "WHERE team_uuid=? AND representation_kind='rendered' LIMIT 1",
                    (team_uuid,),
                )
            assert namespace is not None and browser_rows is not None
            kind = None if fact is None else str(fact["representation_kind"])
            profile = None if fact is None else fact["profile_identity"]
            return str(namespace["namespace_key"]), int(browser_rows["n"]), kind, None if profile is None else str(profile)

        namespace, browser_ok, kind, profile = client.portal.call(inspect)
        assert browser_ok == 1
        assert kind == "rendered"
        assert profile is not None and profile != "injected-browser-renderer.v1"
        found = _search(
            client,
            team_uuid,
            namespace,
            marker,
            {"realm": "documentation", "source_name": "nh7-browser-source", "vector_channel": "original"},
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"]
        excluded = _search(
            client,
            team_uuid,
            namespace,
            marker,
            {"realm": "legislation", "vector_channel": "original"},
        )
        assert excluded.status_code == 200, excluded.text
        assert excluded.json()["results"] == []
        assert_first_publication_closure(app, client, team_uuid, task_uuid)


def test_present_or_unknown_does_not_materialize_browser(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    team_uuid = uuid7()
    with local_spa_server() as (origin, _marker), TestClient(app, raise_server_exceptions=True) as client:
        task_uuid, terminal = _ingest(
            client,
            team_uuid=team_uuid,
            name="nh7-static-present",
            source={
                "source_kind": "http_resource",
                "external_key": "nh7-present-html",
                "url": f"{origin}/static",
                "acquisition_mode": "static",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "nh7-present-source",
            },
        )
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


def test_web_llm_rewrite_namespace_hit(tmp_path: Path) -> None:
    app = create_app(_settings(tmp_path))
    assert isinstance(app.state.container.browser_runtime, HardenedBrowserRuntime)
    cli = app.state.container.workflow_worker.handler._claude_cli  # noqa: SLF001
    assert isinstance(cli, DeterministicNs1Stub)
    team_uuid = uuid7()
    with local_spa_server() as (origin, marker), TestClient(app, raise_server_exceptions=True) as client:
        task_uuid, terminal = _ingest(
            client,
            team_uuid=team_uuid,
            name="nh7-web-llm",
            source={
                "source_kind": "http_resource",
                "external_key": "nh7-empty-spa-llm",
                "url": f"{origin}/empty-spa",
                "acquisition_mode": "static",
                "clean_strategy": "web.llm_rewrite",
                "realm": "documentation",
                "type": "article",
                "channel": "general",
                "source_name": "nh7-web-llm-source",
            },
        )
        assert terminal["status"] == "succeeded", terminal
        assert sum(1 for request in cli.requests if request.role == "clean") >= 1

        async def inspect() -> tuple[str, str | None, dict[str, object]]:
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
                process = await tx.fetchone(
                    "SELECT output_manifest_ref FROM mkb_processes WHERE team_uuid=? AND task_uuid=? "
                    "AND process_key='clean.extract.web_llm' AND status='succeeded'",
                    (team_uuid, task_uuid),
                )
            assert namespace is not None and process is not None
            blob = await app.state.container.storage.read_verified(
                team_uuid, ObjectHandle(value=str(process["output_manifest_ref"]))
            )
            output = json.loads(blob.decode())
            evidence = output["output"]["clean_candidate"]["evidence"]
            strategy = None if execution is None else execution["actual_clean_strategy"]
            return str(namespace["namespace_key"]), None if strategy is None else str(strategy), evidence

        namespace, strategy, evidence = client.portal.call(inspect)
        assert strategy == "web.llm_rewrite"
        assert evidence["prompt_key"] == "promptA.default"
        assert evidence["prompt_version"] == "v1"
        assert isinstance(evidence.get("prompt_content_sha256"), str) and len(str(evidence["prompt_content_sha256"])) == 64
        found = _search(
            client,
            team_uuid,
            namespace,
            marker,
            {"realm": "documentation", "source_name": "nh7-web-llm-source", "vector_channel": "original"},
        )
        assert found.status_code == 200, found.text
        assert found.json()["results"]
        excluded = _search(
            client,
            team_uuid,
            namespace,
            marker,
            {"realm": "legislation", "vector_channel": "original"},
        )
        assert excluded.status_code == 200, excluded.text
        assert excluded.json()["results"] == []
        assert_first_publication_closure(app, client, team_uuid, task_uuid)
