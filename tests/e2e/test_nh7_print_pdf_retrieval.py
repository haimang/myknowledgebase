"""NH7-T06: declared print_pdf acquire is cleaned as PDF, not HTML."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.runtime.supply.browser import HardenedBrowserRuntime
from tests.nh6_runtime_support import browser_settings, local_multimodal_server, local_spa_server


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


def test_print_fact_pdf_clean_namespace_hit(tmp_path: Path) -> None:
    team_uuid = uuid7()
    task_uuid, trace_uuid = uuid7(), uuid7()
    with (
        local_multimodal_server() as (base_url, model_key, _payloads),
        local_spa_server() as (origin, _marker),
    ):
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
        assert isinstance(app.state.container.browser_runtime, HardenedBrowserRuntime)
        with TestClient(app, raise_server_exceptions=True) as client:
            assert (
                client.post(
                    "/v1/teams",
                    headers=_headers(),
                    json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh7-print"},
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
                            "external_key": "nh7-print",
                            "url": f"{origin}/spa",
                            "acquisition_mode": "static",
                            "clean_strategy": "web.browser_print_pdf",
                            "realm": "documentation",
                            "type": "article",
                            "channel": "general",
                            "source_name": "nh7-print-source",
                        },
                    },
                    "audit": {
                        "schema_version": "mkb.task-audit.v1",
                        "team_uuid": team_uuid,
                        "task_uuid": task_uuid,
                        "trace_uuid": trace_uuid,
                        "audit_type": "business_review",
                        "audit_status": "not_required",
                        "source": "nh7-t06",
                        "created_at": utc_now(),
                    },
                },
            )
            assert created.status_code == 201, created.text
            terminal = _wait(client, team_uuid, task_uuid)

            async def failures() -> list[dict[str, object]]:
                async with app.state.container.persistence.transaction() as tx:
                    return await tx.fetchall(
                        "SELECT process_key,status,error_code,error_message FROM mkb_processes "
                        "WHERE team_uuid=? AND task_uuid=? AND status!='succeeded' ORDER BY created_at",
                        (team_uuid, task_uuid),
                    )

            assert terminal["status"] == "succeeded", client.portal.call(failures)

            async def inspect() -> tuple[str, str | None]:
                async with app.state.container.persistence.transaction() as tx:
                    namespace = await tx.fetchone(
                        "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                        (team_uuid,),
                    )
                    fact = await tx.fetchone(
                        "SELECT representation_kind FROM mkb_representation_facts "
                        "WHERE team_uuid=? AND execution_uuid IN "
                        "(SELECT execution_uuid FROM mkb_executions WHERE team_uuid=? AND task_uuid=?) "
                        "AND representation_kind='print_pdf' LIMIT 1",
                        (team_uuid, team_uuid, task_uuid),
                    )
                assert namespace is not None
                return str(namespace["namespace_key"]), None if fact is None else str(fact["representation_kind"])

            namespace, kind = client.portal.call(inspect)
            assert kind == "print_pdf"
            found = client.post(
                f"/v1/teams/{team_uuid}/retrieval:search",
                headers=_headers(),
                json={
                    "schema_version": "mkb.retrieval.v2",
                    "team_uuid": team_uuid,
                    "namespace_key": namespace,
                    "query": "PDF INPUT OBSERVED",
                    "filters": {"source_name": "nh7-print-source", "vector_channel": "original"},
                    "return_k": 20,
                    "recall_k": 100,
                },
            )
            assert found.status_code == 200, found.text
            assert found.json()["results"]

