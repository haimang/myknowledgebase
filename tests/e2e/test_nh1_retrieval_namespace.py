"""NH1-T03: namespace omission fails and the same document queries with Layer A."""

from __future__ import annotations

import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from tests.local_runtime import local_mock_settings


def test_namespace_is_required_then_real_layer_a_key_hits(tmp_path: Path) -> None:
    token = "nh1-namespace-token"
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    source_content = "NH1 Layer A namespace golden document has durable grounded evidence."
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            internal_token=token,
            rate_limit_ip_per_min=1_000,
            rate_limit_token_per_min=2_000,
        )
    )
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app, raise_server_exceptions=True) as client:
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "nh1 namespace"},
        )
        assert team.status_code == 201, team.text
        created = client.post(
            f"/v1/teams/{team_uuid}/tasks",
            headers=headers,
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
                        "external_key": "nh1-layer-a-golden",
                        "content": source_content,
                        "media_type": "text/plain",
                    },
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "nh1-t03",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text

        deadline = time.monotonic() + 8
        task: dict[str, object] = {}
        while time.monotonic() < deadline:
            response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
            assert response.status_code == 200, response.text
            task = response.json()
            if task["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.02)
        assert task["status"] == "succeeded", task
        assert task["proof_ref"]

        request = {
            "schema_version": "mkb.retrieval.v1",
            "team_uuid": team_uuid,
            "query": "Layer A durable evidence",
            "filters": {"channel": "summary"},
            "return_k": 3,
            "recall_k": 5,
        }
        omitted = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json=request,
        )
        assert omitted.status_code == 422, omitted.text
        assert omitted.json()["error"]["code"] == "RETRIEVE_SCHEMA_NAMESPACE_REQUIRED"

        persistence = app.state.container.persistence

        async def active_namespace_key() -> str:
            async with persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["namespace_key"])

        namespace_key = client.portal.call(active_namespace_key)
        found = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={**request, "namespace_key": namespace_key},
        )
        assert found.status_code == 200, found.text
        body = found.json()
        assert body["disposition"] == "ok"
        assert body["results"]
        hit = body["results"][0]
        assert hit["payload_content"]
        assert hit["payload_content"] in source_content
        assert hit["traceback_status"] == "resolved"


def test_nh1_namespace_proofs_forbid_driver_bypass() -> None:
    forbidden = ("import " + "sqlite3", "sqlite3" + ".connect")
    for path in (
        Path("tests/e2e/test_single_intake_pipeline.py"),
        Path("tests/e2e/test_nh1_retrieval_namespace.py"),
    ):
        source = path.read_text(encoding="utf-8")
        assert all(token not in source for token in forbidden)
