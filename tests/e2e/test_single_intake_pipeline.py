"""D07-E2E-01 / G13: HTTP admission through grounded retrieval."""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import uuid7
from src.contracts.common.time import utc_now
from src.contracts.inference.models import EmbeddingRequest, EmbeddingResponse
from src.runtime.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        internal_token="integration-token",
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        inference_probe_enabled=False,
        # The offline profile intentionally shares its deterministic vector
        # transform between vectorization and query retrieval, so this test
        # proves the semantic golden without a GPU or a live model endpoint.
        live_inference=False,
        # Polling intentionally exercises the durable supervisor at a much
        # tighter interval than a deployed caller.  Keep production S16
        # defaults intact while ensuring this semantic test tests workflow,
        # not a fixed-window ceiling.
        rate_limit_ip_per_min=1_000,
        rate_limit_token_per_min=2_000,
    )


def test_single_intake_publishes_grounded_retrieval_context(tmp_path: Path) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    headers = {"Authorization": "Bearer integration-token"}
    app = create_app(_settings(tmp_path))

    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.get("/ready").status_code == 200
        team = client.post(
            "/v1/teams",
            headers=headers,
            json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "semantic-golden"},
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
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "semantic-golden-document",
                        "content": "MKB workflow retrieval semantic golden document",
                        "media_type": "text/plain",
                    }
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "e2e",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text

        deadline = time.monotonic() + 5
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
        # S02 counts are a Task-scoped projection over the accepted
        # Snapshot/Membership set, not an incidental count of the ten internal
        # workflow Processes.  A normal single intake has exactly one required
        # member and it is publication-ready when the Task succeeds.
        assert task["counts"] == {
            "total": 1,
            "required": 1,
            "active": 0,
            "succeeded": 1,
            "failed": 0,
            "cancelled": 0,
            "skipped": 0,
        }

        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "query": "semantic golden workflow",
                "return_k": 3,
                "recall_k": 5,
            },
        )
        assert search.status_code == 200, search.text
        result = search.json()
        assert result["disposition"] == "ok"
        assert result["results"]
        hit = result["results"][0]
        assert hit["payload_content"] == "MKB workflow retrieval semantic golden document"
        assert hit["traceback_status"] == "resolved"
        # S10 remains context-only and S01/S03 internals are never public.
        rendered = str(result)
        assert "answer" not in result
        assert "execution_uuid" not in rendered
        assert "process_uuid" not in rendered


class _LiveEmbeddingFixture:
    """A binding-observant 64-D embedder used to prove frozen live Layer A."""

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        binding = request.binding
        texts = request.texts
        assert binding.adapter_kind == "local_vllm"
        assert binding.model_key == "qwen-vl-2b"
        assert binding.model_version == "v1"
        vectors = [[1.0, *([0.0] * 63)] for _ in texts]
        return EmbeddingResponse(vectors=vectors, model_key="qwen-vl-2b", model_version="v1", dimension=64)

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        del query
        return [float(len(documents) - ordinal) for ordinal, _ in enumerate(documents)]

    async def probe(self) -> bool:
        return True


def test_live_profile_uses_frozen_binding_for_vector_write_and_query(tmp_path: Path) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    token = "live-integration-token"
    app = create_app(
        Settings(
            internal_token=token,
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            inference_probe_enabled=False,
            live_inference=True,
            rate_limit_ip_per_min=1_000,
            rate_limit_token_per_min=2_000,
        )
    )
    fixture = _LiveEmbeddingFixture()
    # This is a composition-level seam: production keeps the registered
    # facade, while the semantic golden keeps all transport local and still
    # asserts the exact frozen binding sent to it.
    app.state.container.workflow_worker.handler._inference = fixture  # type: ignore[attr-defined]
    app.state.container.retrieval._inference = fixture  # type: ignore[attr-defined]
    headers = {"Authorization": f"Bearer {token}"}

    with TestClient(app, raise_server_exceptions=True) as client:
        assert client.get("/ready").status_code == 200
        assert (
            client.post(
                "/v1/teams",
                headers=headers,
                json={"schema_version": "mkb.team.v1", "team_uuid": team_uuid, "name": "live-binding"},
            ).status_code
            == 201
        )
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
                    "source": {
                        "source_kind": "inline_payload",
                        "external_key": "live-vector-document",
                        "content": "Live embedding preserves the frozen binding.",
                    }
                },
                "audit": {
                    "schema_version": "mkb.task-audit.v1",
                    "team_uuid": team_uuid,
                    "task_uuid": task_uuid,
                    "trace_uuid": trace_uuid,
                    "audit_type": "business_review",
                    "audit_status": "not_required",
                    "source": "e2e",
                    "created_at": utc_now(),
                },
            },
        )
        assert created.status_code == 201, created.text
        deadline = time.monotonic() + 5
        task: dict[str, object] = {}
        while time.monotonic() < deadline:
            response = client.get(f"/v1/teams/{team_uuid}/tasks/{task_uuid}", headers=headers)
            assert response.status_code == 200, response.text
            task = response.json()
            if task["status"] in {"succeeded", "failed", "cancelled"}:
                break
            time.sleep(0.02)
        assert task["status"] == "succeeded", task

        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "query": "frozen binding",
                "return_k": 1,
                "recall_k": 2,
            },
        )
        assert search.status_code == 200, search.text
        assert search.json()["disposition"] == "ok"


    # The application-owned async SQLite connection is bound to TestClient's
    # event loop and is closed with its lifespan.  Inspect the private proof
    # rows only after that lifecycle with an independent read-only connection.
    database_uri = f"file:{tmp_path / 'mkb.sqlite3'}?mode=ro"
    with sqlite3.connect(database_uri, uri=True) as connection:
        connection.row_factory = sqlite3.Row
        namespace_row = connection.execute(
            "SELECT embedding_model_key,embedding_model_version,adapter_kind,dimension FROM mkb_vector_namespaces"
        ).fetchone()
        proof_row = connection.execute(
            "SELECT embedding_model_key,embedding_model_version,adapter_kind,dimension FROM mkb_publication_proofs"
        ).fetchone()
        invocation_row = connection.execute(
            "SELECT capability_key,model_key,model_version,status FROM mkb_inference_invocations"
        ).fetchone()

    assert namespace_row is not None and proof_row is not None and invocation_row is not None
    namespace = dict(namespace_row)
    proof = dict(proof_row)
    invocation = dict(invocation_row)
    expected = {
        "embedding_model_key": "qwen-vl-2b",
        "embedding_model_version": "v1",
        "adapter_kind": "local_vllm",
        "dimension": 64,
    }
    assert namespace == expected
    assert proof == expected
    assert invocation == {
        "capability_key": "embed",
        "model_key": "qwen-vl-2b",
        "model_version": "v1",
        "status": "succeeded",
    }
