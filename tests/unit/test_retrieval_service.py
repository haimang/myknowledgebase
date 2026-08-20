"""S10 focused tests: dual-fence reads, traceback and honest rerank fallback."""

from __future__ import annotations

import struct
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.inference.models import EmbeddingResponse
from src.persistence.sqlite_port import SqlitePersistence
from src.services.retrieval import RetrievalService

TEAM = "123e4567-e89b-42d3-a456-426614174000"
NAMESPACE = "123e4567-e89b-42d3-a456-426614174001"
ITEM = "123e4567-e89b-42d3-a456-426614174002"
REVISION = "123e4567-e89b-42d3-a456-426614174003"
GENERATION = "123e4567-e89b-42d3-a456-426614174004"
PROOF = "123e4567-e89b-42d3-a456-426614174005"
SOURCE = "123e4567-e89b-42d3-a456-426614174006"
NOW = "2026-08-12T00:00:00Z"


class FixtureBodies:
    async def load_retrieval_body(
        self, *, team_uuid: str, generation_artifact_uuid: str, unit_id: str, channel: str
    ) -> dict[str, object] | None:
        del team_uuid, generation_artifact_uuid
        return {
            ("g1:revenue", "summary"): {"content": "summary revenue evidence", "granularity": 1},
            ("g1:revenue", "original"): {"content": "original revenue evidence /tmp/private.txt", "granularity": 1},
            ("g0:root", "original"): {"content": "root document evidence", "granularity": 0},
            ("g0:root", "summary"): {"content": "summary of root document", "granularity": 0},
            ("g1:missing", "summary"): {"content": "summary without original", "granularity": 1},
            ("g1:revenue-alt", "original"): {"content": "second original revenue evidence", "granularity": 1},
        }.get((unit_id, channel))


class BrokenReranker:
    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        del query, documents
        raise RuntimeError("test reranker unavailable")


class FixedReranker:
    async def rerank(self, query: str, documents: list[str]) -> list[float]:
        del query
        return [float(index) for index, _ in enumerate(documents, start=1)]


class RejectingEligibility:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[dict[str, str]]]] = []

    async def filter_retrieval_eligible(self, *, team_uuid: str, candidates: list[dict[str, str]]) -> set[str]:
        self.calls.append((team_uuid, candidates))
        return set()


class WithdrawingPublicationEligibility:
    """Simulate S09 invalidation after the initial candidate scan."""

    def __init__(self, persistence: SqlitePersistence) -> None:
        self._persistence = persistence
        self.calls = 0

    async def filter_retrieval_eligible(self, *, team_uuid: str, candidates: list[dict[str, str]]) -> set[str]:
        del team_uuid
        self.calls += 1
        connection = self._persistence._connect()
        connection.execute("UPDATE mkb_vector_records SET publication_state='withdrawn'")
        connection.execute("UPDATE mkb_index_active_pointers SET lifecycle_state='withdrawn'")
        connection.commit()
        return {candidate["vector_record_uuid"] for candidate in candidates}


class IntegrityFailureBodies:
    async def load_retrieval_body(self, **_: object) -> None:
        raise MkbError("RETRIEVE_BODY_INTEGRITY", "fixture body digest is invalid", 503)


class MissingOriginalBodies(FixtureBodies):
    async def load_retrieval_body(
        self, *, team_uuid: str, generation_artifact_uuid: str, unit_id: str, channel: str
    ) -> dict[str, object] | None:
        if unit_id == "g1:revenue" and channel == "original":
            return None
        return await super().load_retrieval_body(
            team_uuid=team_uuid,
            generation_artifact_uuid=generation_artifact_uuid,
            unit_id=unit_id,
            channel=channel,
        )


class MismatchedEmbedder:
    async def embed(self, request: object) -> EmbeddingResponse:
        del request
        return EmbeddingResponse(vectors=[[1.0]], model_key="other-model", model_version="v1", dimension=1)


class FixedLayerAEmbedder:
    async def embed(self, request: object) -> EmbeddingResponse:
        assert getattr(request, "expected_dimension", None) == 2
        return EmbeddingResponse(vectors=[[1.0, 0.0]], model_key="model", model_version="v1", dimension=2)


class AdapterMismatchedEmbedder:
    async def embed(self, request: object) -> object:
        del request

        class Response:
            vectors = [[1.0, 0.0]]
            model_key = "model"
            model_version = "v1"
            dimension = 2
            adapter_kind = "remote_gemini"

        return Response()


@pytest.fixture
async def retrieval_db(tmp_path: Path) -> SqlitePersistence:
    persistence = SqlitePersistence(tmp_path / "mkb.db", Path("src/persistence/migrations"))
    await persistence.migrate()
    connection = persistence._connect()  # test fixture setup only
    connection.execute("PRAGMA foreign_keys = OFF")
    connection.execute(
        """INSERT INTO mkb_vector_namespaces
        (namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,
         embedding_model_version,adapter_kind,dimension,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (NAMESPACE, TEAM, "default", "model", "model", "v1", "deterministic", 2, NOW, NOW),
    )
    connection.execute(
        """INSERT INTO mkb_intake_items
        (team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,
         latest_revision_uuid,serving_revision_uuid,row_revision,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (TEAM, ITEM, SOURCE, "fixture-key", "active", REVISION, REVISION, 0, NOW, NOW),
    )
    connection.execute(
        """INSERT INTO mkb_generation_artifacts
        (generation_artifact_uuid,team_uuid,artifact_type,logical_handle,media_type,size_bytes,
         content_digest,validation_disposition,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            GENERATION,
            TEAM,
            "dual_channel_projection",
            "mkbobj:v1:g",
            "application/json",
            1,
            "a" * 64,
            "full_valid",
            NOW,
        ),
    )
    for record_uuid, unit_id, channel in (
        ("123e4567-e89b-42d3-a456-426614174010", "g1:revenue", "summary"),
        ("123e4567-e89b-42d3-a456-426614174011", "g1:revenue", "original"),
        ("123e4567-e89b-42d3-a456-426614174012", "g0:root", "original"),
        ("123e4567-e89b-42d3-a456-426614174013", "g1:missing", "summary"),
        ("123e4567-e89b-42d3-a456-426614174014", "g1:revenue-alt", "original"),
    ):
        connection.execute(
            """INSERT INTO mkb_vector_records
            (vector_record_uuid,team_uuid,namespace_uuid,generation_artifact_uuid,generation_artifact_type,
             block_or_unit_id,channel,intake_source_uuid,intake_item_uuid,intake_revision_uuid,
             content_digest,source_handle,embedding_model,embedding_model_key,embedding_model_version,
             adapter_kind,dimension,embedding,publication_state,index_generation,embedded_at,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
            (
                record_uuid,
                TEAM,
                NAMESPACE,
                GENERATION,
                "dual_channel_projection",
                unit_id,
                channel,
                SOURCE,
                ITEM,
                REVISION,
                "b" * 64,
                "mkbobj:v1:body",
                "model",
                "model",
                "v1",
                "deterministic",
                2,
                struct.pack("<2f", 0.1, 0.2),
                "indexed",
                1,
                NOW,
                NOW,
                NOW,
            ),
        )
    connection.execute(
        """INSERT INTO mkb_publication_proofs
        (proof_uuid,team_uuid,intake_item_uuid,intake_revision_uuid,generation_artifact_uuid,
         generation_artifact_type,namespace_uuid,embedding_model,embedding_model_key,
         embedding_model_version,adapter_kind,dimension,index_generation,expected_count,actual_count,
         matched_count,required_set_digest,actual_set_digest,command_input_digest,created_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            PROOF,
            TEAM,
            ITEM,
            REVISION,
            GENERATION,
            "dual_channel_projection",
            NAMESPACE,
            "model",
            "model",
            "v1",
            "deterministic",
            2,
            1,
            5,
            5,
            5,
            "c" * 64,
            "d" * 64,
            "e" * 64,
            NOW,
        ),
    )
    connection.execute(
        """INSERT INTO mkb_index_active_pointers
        (team_uuid,intake_item_uuid,namespace_uuid,active_index_generation,lifecycle_state,
         last_proof_uuid,generation_artifact_uuid,updated_at)
        VALUES (?,?,?,?,?,?,?,?)""",
        (TEAM, ITEM, NAMESPACE, 1, "active", PROOF, GENERATION, NOW),
    )
    connection.commit()
    yield persistence
    await persistence.close()


async def test_blank_query_is_empty_without_database_read(retrieval_db: SqlitePersistence) -> None:
    result = await RetrievalService(retrieval_db).search({"team_uuid": TEAM, "namespace_key": "default", "query": " \t "})

    assert result["disposition"] == "empty"
    assert result["results"] == []
    assert result["diagnostics"]["empty_reason"] == "blank_query"


async def test_search_applies_fences_traceback_redaction_and_honest_rerank_fallback(
    retrieval_db: SqlitePersistence,
) -> None:
    connection = retrieval_db._connect()
    counts_before = {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("mkb_tasks", "mkb_task_audits", "mkb_executions", "mkb_processes")
    }
    result = await RetrievalService(retrieval_db, BrokenReranker(), body_port=FixtureBodies()).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue", "return_k": 10}
    )
    counts_after = {
        table: connection.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        for table in ("mkb_tasks", "mkb_task_audits", "mkb_executions", "mkb_processes")
    }

    assert counts_after == counts_before
    assert result["disposition"] == "ok"
    assert result["diagnostics"]["rerank_status"] == "failed"
    assert all(item["score"] == item["ann_score"] for item in result["results"])
    assert [item["ann_score"] for item in result["results"]] == sorted(
        (item["ann_score"] for item in result["results"]), reverse=True
    )
    assert all(item["rerank_score"] is None for item in result["results"])
    summary = next(item for item in result["results"] if item["hit_channel"] == "summary")
    assert summary["traceback_status"] == "resolved"
    assert summary["payload_content"] == "original revenue evidence [redacted-path]"
    assert summary["inflation_status"] in {"attached", "truncated"}
    units = [item["coordinate"]["unit_id"] for item in result["results"]]
    assert len(units) == len(set(units))
    assert units.count("g1:revenue") == 1
    assert "answer" not in result
    assert "embedding" not in str(result)
    assert "/tmp/" not in str(result)


async def test_g0_summary_tracebacks_to_construct_original_without_original_vector(
    retrieval_db: SqlitePersistence,
) -> None:
    connection = retrieval_db._connect()
    connection.execute("UPDATE mkb_vector_records SET channel='summary' WHERE block_or_unit_id='g0:root'")
    connection.commit()

    result = await RetrievalService(retrieval_db, body_port=FixtureBodies()).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "root", "return_k": 10}
    )

    g0 = next(item for item in result["results"] if item["coordinate"]["unit_id"] == "g0:root")
    assert g0["hit_channel"] == "summary"
    assert g0["traceback_status"] == "resolved"
    assert g0["payload_content"] == "root document evidence"
    assert g0["hit_content"] == "summary of root document"


async def test_summary_without_original_is_not_claimed_as_original(retrieval_db: SqlitePersistence) -> None:
    result = await RetrievalService(retrieval_db, body_port=FixtureBodies()).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "missing", "return_k": 10}
    )

    missing = next(item for item in result["results"] if item["coordinate"]["unit_id"] == "g1:missing")
    assert missing["traceback_status"] in {"failed", "degraded"}
    assert missing["payload_content"] == "summary without original"
    assert missing["hit_channel"] == "summary"


async def test_dual_fence_rejects_withdrawn_pointer_and_non_serving_revision(retrieval_db: SqlitePersistence) -> None:
    connection = retrieval_db._connect()
    connection.execute("UPDATE mkb_vector_records SET publication_state='withdrawn'")
    connection.commit()
    withdrawn = await RetrievalService(retrieval_db).search({"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"})
    assert withdrawn["disposition"] == "empty"
    assert withdrawn["diagnostics"]["empty_reason"] == "no_hit"

    connection.execute("UPDATE mkb_vector_records SET publication_state='indexed'")
    connection.execute("UPDATE mkb_intake_items SET lifecycle_state='deactivated', serving_revision_uuid=NULL")
    connection.commit()
    inactive = await RetrievalService(retrieval_db).search({"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"})
    assert inactive["disposition"] == "empty"
    assert inactive["diagnostics"]["empty_reason"] == "no_hit"

    connection.execute("UPDATE mkb_intake_items SET lifecycle_state='active', serving_revision_uuid=?", (REVISION,))
    connection.execute("UPDATE mkb_vector_records SET deleted_at=?", (NOW,))
    connection.commit()
    soft_deleted = await RetrievalService(retrieval_db).search({"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"})
    assert soft_deleted["disposition"] == "empty"


async def test_dual_fence_requires_named_proof_and_active_pointer(retrieval_db: SqlitePersistence) -> None:
    connection = retrieval_db._connect()
    connection.execute("UPDATE mkb_index_active_pointers SET last_proof_uuid=NULL")
    connection.commit()
    missing_pointer_proof = await RetrievalService(retrieval_db).search({"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"})
    assert missing_pointer_proof["disposition"] == "empty"

    connection.execute("UPDATE mkb_index_active_pointers SET last_proof_uuid=?", (PROOF,))
    connection.execute("UPDATE mkb_publication_proofs SET matched_count=4 WHERE proof_uuid=?", (PROOF,))
    connection.commit()
    incomplete_proof = await RetrievalService(retrieval_db).search({"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"})
    assert incomplete_proof["disposition"] == "empty"


async def test_dual_fence_rejects_an_incomplete_or_injected_proof_record_set(
    retrieval_db: SqlitePersistence,
) -> None:
    """A proof count must describe the live set, not just be self-consistent."""

    connection = retrieval_db._connect()
    connection.execute(
        """INSERT INTO mkb_vector_records
        (vector_record_uuid,team_uuid,namespace_uuid,generation_artifact_uuid,generation_artifact_type,
         block_or_unit_id,channel,intake_source_uuid,intake_item_uuid,intake_revision_uuid,
         content_digest,source_handle,embedding_model,embedding_model_key,embedding_model_version,
         adapter_kind,dimension,embedding,publication_state,index_generation,embedded_at,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            "123e4567-e89b-42d3-a456-426614174019",
            TEAM,
            NAMESPACE,
            GENERATION,
            "dual_channel_projection",
            "g1:unproven",
            "original",
            SOURCE,
            ITEM,
            REVISION,
            "b" * 64,
            "mkbobj:v1:body",
            "model",
            "model",
            "v1",
            "deterministic",
            2,
            struct.pack("<2f", 0.1, 0.2),
            "indexed",
            1,
            NOW,
            NOW,
            NOW,
        ),
    )
    connection.commit()

    result = await RetrievalService(retrieval_db).search({"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"})

    assert result["disposition"] == "empty"
    assert result["diagnostics"]["empty_reason"] == "no_hit"


async def test_injected_eligibility_port_is_batched_and_fail_closed(retrieval_db: SqlitePersistence) -> None:
    eligibility = RejectingEligibility()
    result = await RetrievalService(retrieval_db, eligibility_port=eligibility).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"}
    )

    assert result["disposition"] == "empty"
    assert result["diagnostics"]["empty_reason"] == "all_filtered"
    assert len(eligibility.calls) == 1
    assert eligibility.calls[0][0] == TEAM
    assert len(eligibility.calls[0][1]) >= 2


async def test_post_ranking_publication_revalidation_rejects_a_withdrawal(
    retrieval_db: SqlitePersistence,
) -> None:
    eligibility = WithdrawingPublicationEligibility(retrieval_db)

    result = await RetrievalService(retrieval_db, eligibility_port=eligibility).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"}
    )

    assert eligibility.calls == 1
    assert result["disposition"] == "empty"
    assert result["diagnostics"]["empty_reason"] == "all_filtered"


async def test_body_integrity_failure_fails_closed(retrieval_db: SqlitePersistence) -> None:
    with pytest.raises(MkbError) as error:
        await RetrievalService(retrieval_db, body_port=IntegrityFailureBodies()).search(
            {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"}
        )

    assert error.value.code == "RETRIEVE_BODY_INTEGRITY"


async def test_missing_original_body_degrades_traceback_without_claiming_resolution(
    retrieval_db: SqlitePersistence,
) -> None:
    result = await RetrievalService(retrieval_db, body_port=MissingOriginalBodies()).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"}
    )

    summary = next(item for item in result["results"] if item["hit_channel"] == "summary")
    assert summary["coordinate"]["unit_id"] == "g1:revenue"
    assert summary["traceback_status"] == "degraded"
    assert summary["payload_content"] == "summary revenue evidence"


async def test_missing_configured_reranker_is_failed_not_skipped(retrieval_db: SqlitePersistence) -> None:
    result = await RetrievalService(retrieval_db, body_port=FixtureBodies()).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"}
    )

    assert len(result["results"]) > 1
    assert result["diagnostics"]["rerank_status"] == "failed"


async def test_unknown_filter_and_invalid_rank_policy_fail_loudly(retrieval_db: SqlitePersistence) -> None:
    service = RetrievalService(retrieval_db)
    with pytest.raises(MkbError, match="unknown retrieval filter key") as unknown:
        await service.search({"team_uuid": TEAM, "namespace_key": "default", "query": "x", "filters": {"forbidden": "x"}})
    assert unknown.value.code == "RETRIEVE_FILTER_INVALID"

    with pytest.raises(MkbError) as invalid:
        await service.search({"team_uuid": TEAM, "namespace_key": "default", "query": "x", "return_k": 20, "recall_k": 10})
    assert invalid.value.code == "RETRIEVE_TOPK_INVALID"

    with pytest.raises(MkbError) as forbidden:
        await service.search({"team_uuid": TEAM, "namespace_key": "default", "query": "x", "index_generation": 999})
    assert forbidden.value.code == "RETRIEVE_SCHEMA_FORBIDDEN_FIELD"

    with pytest.raises(MkbError) as malformed_schema:
        await service.search({"schema_version": "mkb.retrieval.v0", "team_uuid": TEAM, "namespace_key": "default", "query": "x"})
    assert malformed_schema.value.code == "RETRIEVE_SCHEMA_INVALID"

    with pytest.raises(MkbError) as invalid_source_kind:
        await service.search({"team_uuid": TEAM, "namespace_key": "default", "query": "x", "filters": {"source_kind": "unregistered"}})
    assert invalid_source_kind.value.code == "RETRIEVE_FILTER_INVALID"


async def test_successful_rerank_retains_ann_score(retrieval_db: SqlitePersistence) -> None:
    result = await RetrievalService(retrieval_db, FixedReranker(), body_port=FixtureBodies()).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue", "return_k": 10}
    )

    assert result["diagnostics"]["rerank_status"] == "applied"
    assert all(item["rerank_score"] is not None for item in result["results"])
    assert all(item["score"] == item["rerank_score"] for item in result["results"])


async def test_live_embed_layer_a_mismatch_fails_closed(retrieval_db: SqlitePersistence) -> None:
    connection = retrieval_db._connect()
    connection.execute(
        """INSERT INTO mkb_adapter_bindings
        (binding_uuid,capability_key,adapter_kind,model_key,model_version,priority,enabled,binding_digest,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            "123e4567-e89b-42d3-a456-426614174020",
            "embed",
            "deterministic",
            "model",
            "v1",
            10,
            1,
            "f" * 64,
            NOW,
            NOW,
        ),
    )
    connection.commit()

    with pytest.raises(MkbError) as mismatch:
        await RetrievalService(retrieval_db, MismatchedEmbedder(), live_inference=True).search(
            {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"}
        )
    assert mismatch.value.code == "RETRIEVE_SPACE_LAYER_A_MISMATCH"


async def test_live_embed_adapter_layer_a_mismatch_fails_closed(retrieval_db: SqlitePersistence) -> None:
    connection = retrieval_db._connect()
    connection.execute(
        """INSERT INTO mkb_adapter_bindings
        (binding_uuid,capability_key,adapter_kind,model_key,model_version,priority,enabled,binding_digest,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            "123e4567-e89b-42d3-a456-426614174022",
            "embed",
            "deterministic",
            "model",
            "v1",
            10,
            1,
            "f" * 64,
            NOW,
            NOW,
        ),
    )
    connection.commit()

    with pytest.raises(MkbError) as mismatch:
        await RetrievalService(retrieval_db, AdapterMismatchedEmbedder(), live_inference=True).search(
            {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue"}
        )
    assert mismatch.value.code == "RETRIEVE_SPACE_LAYER_A_MISMATCH"


async def test_local_exact_search_respects_the_controlled_namespace_metric(retrieval_db: SqlitePersistence) -> None:
    """The local profile must not silently use cosine for an l2 namespace."""

    connection = retrieval_db._connect()
    connection.execute("UPDATE mkb_vector_namespaces SET distance_metric='l2' WHERE namespace_uuid=?", (NAMESPACE,))
    connection.execute(
        "UPDATE mkb_vector_records SET embedding=? WHERE vector_record_uuid=?",
        (struct.pack("<2f", 10.0, 0.0), "123e4567-e89b-42d3-a456-426614174011"),
    )
    connection.execute(
        "UPDATE mkb_vector_records SET embedding=? WHERE vector_record_uuid=?",
        (struct.pack("<2f", 0.5, 0.5), "123e4567-e89b-42d3-a456-426614174014"),
    )
    connection.execute(
        """INSERT INTO mkb_adapter_bindings
        (binding_uuid,capability_key,adapter_kind,model_key,model_version,priority,enabled,binding_digest,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            "123e4567-e89b-42d3-a456-426614174021",
            "embed",
            "deterministic",
            "model",
            "v1",
            10,
            1,
            "f" * 64,
            NOW,
            NOW,
        ),
    )
    connection.commit()

    result = await RetrievalService(
        retrieval_db,
        FixedLayerAEmbedder(),
        live_inference=True,
        rerank_enabled=False,
    ).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue", "filters": {"channel": "original"}, "return_k": 1, "recall_k": 3}
    )

    assert result["disposition"] == "ok"
    # Cosine would prefer [10, 0]; controlled l2 correctly prefers [0.5, .5].
    assert result["results"][0]["coordinate"]["unit_id"] == "g1:revenue-alt"
    assert result["results"][0]["ann_score"] > 0.5


async def test_pack_is_bounded_and_marks_truncation(retrieval_db: SqlitePersistence) -> None:
    result = await RetrievalService(retrieval_db, body_port=FixtureBodies(), pack_max_hits=1).search(
        {"team_uuid": TEAM, "namespace_key": "default", "query": "revenue", "include_pack": True}
    )

    assert result["pack"]["pack_hit_count"] == 1
    assert result["pack"]["truncated"] is True
    assert result["diagnostics"]["pack_truncated"] is True
    assert result["results"][0]["inflation_root_coordinate"]["unit_id"] == "g0:root"
    root_segment = next(segment for segment in result["pack"]["segments"] if segment["tier"] == "document_root")
    assert root_segment["coordinate"]["generation_artifact_uuid"] == GENERATION
    assert root_segment["coordinate"]["unit_id"] == "g0:root"


async def test_g0_result_packs_as_a_document_root(retrieval_db: SqlitePersistence) -> None:
    def root_only_scorer(**kwargs: object) -> dict[str, float]:
        rows = kwargs["candidates"]
        assert isinstance(rows, list)
        return {
            str(row["vector_record_uuid"]): 1.0
            for row in rows
            if row["block_or_unit_id"] == "g0:root"
        }

    result = await RetrievalService(
        retrieval_db,
        candidate_scorer=root_only_scorer,
        body_port=FixtureBodies(),
        rerank_enabled=False,
    ).search({"team_uuid": TEAM, "namespace_key": "default", "query": "revenue", "return_k": 1, "recall_k": 1})

    assert result["results"][0]["granularity"] == 0
    assert result["pack"]["segments"][0]["tier"] == "document_root"
