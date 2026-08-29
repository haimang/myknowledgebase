"""D07-E2E-01 / G13: HTTP admission through grounded retrieval."""

from __future__ import annotations

import json
import time
from pathlib import Path

from fastapi.testclient import TestClient

from api.app import create_app
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.inference.models import (
    EmbeddingRequest,
    EmbeddingResponse,
    StructuredGenerateRequest,
    StructuredGenerateResponse,
    TextGenerateRequest,
    TextGenerateResponse,
)
from src.runtime.config import Settings
from src.services.registry import (
    SPARK_QWEN_GENERATE_MODEL_KEY,
    SPARK_VL_EMBED_MODEL_KEY,
)
from tests.local_runtime import local_mock_settings


def _settings(tmp_path: Path) -> Settings:
    return local_mock_settings(
        database_path=tmp_path / "mkb.sqlite3",
        object_root=tmp_path / "objects",
        internal_token="integration-token",
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
                    "json_prompt_id": "promptB.json.generic",
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

        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "namespace_key": namespace_key,
                "query": "semantic golden workflow",
                "filters": {"channel": "summary"},
                "return_k": 3,
                "recall_k": 5,
            },
        )
        assert search.status_code == 200, search.text
        result = search.json()
        assert result["disposition"] == "ok"
        assert result["results"]
        hit = result["results"][0]
        source_content = "MKB workflow retrieval semantic golden document"
        assert hit["payload_content"]
        assert hit["payload_content"] in source_content
        assert "semantic golden document" in hit["payload_content"]
        assert hit["traceback_status"] == "resolved"
        # S10 remains context-only and S01/S03 internals are never public.
        rendered = str(result)
        assert "answer" not in result
        assert "execution_uuid" not in rendered
        assert "process_uuid" not in rendered

        client.portal.call(_assert_d04_full_chain, persistence)


async def _assert_d04_full_chain(persistence: object) -> None:
    async with persistence.transaction() as tx:  # type: ignore[attr-defined]
        changesets = await tx.fetchall("SELECT change_set_uuid FROM mkb_intake_change_sets")
        facts = await tx.fetchall("SELECT fact_uuid FROM mkb_intake_change_set_facts")
        event_rows = await tx.fetchall("SELECT event_type FROM mkb_domain_events")
        stored = await tx.fetchall("SELECT stored_object_uuid FROM mkb_stored_objects")
        vectors = await tx.fetchall(
            "SELECT embedding, dimension FROM mkb_vector_records WHERE deleted_at IS NULL"
        )
    events = {row["event_type"] for row in event_rows}
    assert changesets, "single-item TX-05 must persist a ChangeSet"
    assert facts, "single-item TX-05 must persist ChangeSet facts"
    assert "task.created" in events
    assert "intake.snapshot_accepted" in events
    assert "generation.artifact_accepted" in events
    assert "vector.upserted" in events
    assert stored, "object catalog must land"
    assert vectors, "vector records must land"
    assert all(row["embedding"] is not None and len(row["embedding"]) == row["dimension"] * 4 for row in vectors)


class _LiveEmbeddingFixture:
    """A binding-observant facade stub for live S06/S07/S08 paths.

    The production composition keeps ``InferenceFacade``; this fixture is
    injected only for offline golden tests so transport stays local while the
    exact frozen binding and dual invocation ledgers are still exercised.
    """

    def __init__(self) -> None:
        self.structured_calls = 0
        self.text_calls = 0
        self.embed_calls = 0

    async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
        binding = request.binding
        texts = request.texts
        assert binding.adapter_kind == "local_vllm"
        assert binding.model_key == SPARK_VL_EMBED_MODEL_KEY
        assert binding.model_version == "v1"
        self.embed_calls += 1
        dimension = request.expected_dimension or 1024
        vectors = [[1.0, *([0.0] * (dimension - 1))] for _ in texts]
        return EmbeddingResponse(
            vectors=vectors,
            model_key=SPARK_VL_EMBED_MODEL_KEY,
            model_version="v1",
            dimension=dimension,
            adapter_kind="local_vllm",
            latency_ms=1,
            request_digest=stable_digest({"capability": "embed", "n": len(texts)}),
            invocation_uuid=uuid7(),
        )

    async def structured_generate(
        self, request: StructuredGenerateRequest, *, validator=None
    ) -> tuple[StructuredGenerateResponse, object | None]:
        del validator
        assert request.binding.capability_key == "structured_generate"
        assert request.binding.model_key == SPARK_QWEN_GENERATE_MODEL_KEY
        assert request.prompt_digest
        assert request.json_schema_digest
        assert request.system_text
        assert request.invocation is not None
        assert request.invocation.generation_invocation_uuid
        self.structured_calls += 1
        try:
            submitted = json.loads(request.input_text)
        except json.JSONDecodeError:
            submitted = None
        if isinstance(submitted, dict) and isinstance(submitted.get("layered_content"), list):
            value = {
                **submitted,
                "layered_content": [
                    {
                        **block,
                        "llm_summary": {
                            "title": block["original_content"].get("title"),
                            "body": block["original_content"].get("body"),
                        },
                    }
                    for block in submitted["layered_content"]
                ],
            }
        else:
            from src.runtime.inference.claude_cli import clean_text_from_bjson_material

            clean = clean_text_from_bjson_material(request.input_text)
            midpoint = max(1, len(clean) // 2)
            value = {
                "context_meta": {},
                "layered_content": [
                    {
                        "block_id": 0,
                        "granularity": 0,
                        "original_content": {"title": None, "body": clean},
                        "llm_summary": {"title": None, "body": None},
                    },
                    {
                        "block_id": 1,
                        "granularity": 1,
                        "original_content": {"title": None, "body": clean[:midpoint]},
                        "llm_summary": {"title": None, "body": None},
                    },
                    {
                        "block_id": 2,
                        "granularity": 2,
                        "original_content": {"title": None, "body": clean[midpoint:] or clean},
                        "llm_summary": {"title": None, "body": None},
                    },
                ],
            }
        response = StructuredGenerateResponse(
            text=json.dumps(value, ensure_ascii=False, sort_keys=True),
            value=value,
            model_key=request.binding.model_key,
            model_version=request.binding.model_version,
            adapter_kind=request.binding.adapter_kind,
            latency_ms=2,
            request_digest=stable_digest({"capability": "structured_generate", "prompt": request.prompt_digest}),
            invocation_uuid=uuid7(),
        )
        return response, value

    async def text_generate(self, request: TextGenerateRequest) -> TextGenerateResponse:
        assert request.binding.capability_key == "text_generate"
        assert request.binding.model_key == SPARK_QWEN_GENERATE_MODEL_KEY
        assert request.prompt_digest
        assert request.invocation is not None
        assert request.invocation.generation_invocation_uuid
        self.text_calls += 1
        # Echo a bounded summary of the original block so construction remains grounded.
        text = request.input_text if len(request.input_text) <= 480 else f"{request.input_text[:479].rstrip()}…"
        return TextGenerateResponse(
            text=text,
            model_key=request.binding.model_key,
            model_version=request.binding.model_version,
            adapter_kind=request.binding.adapter_kind,
            latency_ms=2,
            request_digest=stable_digest({"capability": "text_generate", "prompt": request.prompt_digest}),
            invocation_uuid=uuid7(),
        )

    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        del query
        return [float(len(documents) - ordinal) for ordinal, _ in enumerate(documents)]

    async def probe(self) -> bool:
        return True

    async def probe_binding(self, binding: object) -> bool:
        """Readiness follows the same explicit offline adapter as execution."""

        return getattr(binding, "model_key", None) in {
            SPARK_QWEN_GENERATE_MODEL_KEY,
            SPARK_VL_EMBED_MODEL_KEY,
        }


def test_live_profile_uses_frozen_binding_for_vector_write_and_query(tmp_path: Path) -> None:
    team_uuid, task_uuid, trace_uuid = uuid7(), uuid7(), uuid7()
    token = "live-integration-token"
    app = create_app(
        local_mock_settings(
            database_path=tmp_path / "mkb.sqlite3",
            object_root=tmp_path / "objects",
            internal_token=token,
            inference_probe_enabled=False,
            live_inference=True,
            ns1_cli_mode="disabled",
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
    app.state.container.inference = fixture  # type: ignore[assignment]
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
                    "json_prompt_id": "promptB.json.generic",
                    "compression_channel": "local-inference",
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
        # NS1 uses one structured B.json call and one whole-package C call;
        # construction no longer fans out through the legacy text channel.
        assert fixture.structured_calls >= 2
        assert fixture.embed_calls >= 1

        persistence = app.state.container.persistence

        async def active_namespace_key() -> str:
            async with persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT namespace_key FROM mkb_vector_namespaces WHERE team_uuid=? AND status='active'",
                    (team_uuid,),
                )
            assert row is not None
            return str(row["namespace_key"])

        search = client.post(
            f"/v1/teams/{team_uuid}/retrieval:search",
            headers=headers,
            json={
                "schema_version": "mkb.retrieval.v1",
                "team_uuid": team_uuid,
                "namespace_key": client.portal.call(active_namespace_key),
                "query": "frozen binding",
                "return_k": 1,
                "recall_k": 2,
            },
        )
        assert search.status_code == 200, search.text
        assert search.json()["disposition"] == "ok"

        async def inspect_ledgers() -> tuple[
            dict[str, object] | None,
            dict[str, object] | None,
            list[dict[str, object]],
            list[dict[str, object]],
        ]:
            async with persistence.transaction() as tx:
                namespace_row = await tx.fetchone(
                    "SELECT embedding_model_key,embedding_model_version,adapter_kind,dimension "
                    "FROM mkb_vector_namespaces"
                )
                proof_row = await tx.fetchone(
                    "SELECT embedding_model_key,embedding_model_version,adapter_kind,dimension "
                    "FROM mkb_publication_proofs"
                )
                inv_rows = await tx.fetchall(
                    "SELECT capability_key,model_key,model_version,status,generation_invocation_uuid "
                    "FROM mkb_inference_invocations ORDER BY capability_key, model_key"
                )
                gen_rows = await tx.fetchall(
                    "SELECT invocation_uuid,model_key,prompt_key,schema_key,input_digest,output_digest "
                    "FROM mkb_generation_invocations ORDER BY prompt_key, invocation_ordinal"
                )
            return namespace_row, proof_row, inv_rows, gen_rows

        namespace_row, proof_row, inv_rows, gen_rows = client.portal.call(inspect_ledgers)

    assert namespace_row is not None and proof_row is not None and inv_rows
    namespace = namespace_row
    proof = proof_row
    expected = {
        "embedding_model_key": SPARK_VL_EMBED_MODEL_KEY,
        "embedding_model_version": "v1",
        "adapter_kind": "local_vllm",
        "dimension": 1024,
    }
    assert namespace == expected
    assert proof == expected
    capabilities = {row["capability_key"] for row in inv_rows}
    assert "embed" in capabilities
    assert "structured_generate" in capabilities
    assert all(row["status"] == "succeeded" for row in inv_rows)
    assert gen_rows, "S11 live path must write generation_invocations"
    assert all(row["output_digest"] for row in gen_rows)
    assert all(row["input_digest"] for row in gen_rows)
    # Linked ledgers: every generation row has a matching inference row.
    gen_ids = {row["invocation_uuid"] for row in gen_rows}
    linked = {
        row["generation_invocation_uuid"]
        for row in inv_rows
        if row["generation_invocation_uuid"] is not None
    }
    assert gen_ids <= linked
    # No prompt bodies or source text in the durable ledgers.
    rendered = str(inv_rows + gen_rows)
    assert "Live embedding preserves" not in rendered
    assert "prompt-b-structure" not in rendered
