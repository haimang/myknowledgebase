"""NS5 self-audit remainder: real-red tests for previously thin slices."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.lsrag.layered_content import layered_schema_sha256, load_layered_json_schema
from src.runtime.intake.generation_construct import _title_from_layered
from src.runtime.intake.generation_live import assert_frozen_schema_matches


def test_schema_freeze_fails_closed_on_missing_or_drifted_digest() -> None:
    digest = "a" * 64
    snapshot = {
        "l4": {
            "schemas": {"lsrag.structure.default@v1": {"schema_digest": digest}},
            "layered_schema_sha256": layered_schema_sha256(),
        }
    }
    assert_frozen_schema_matches(
        snapshot, schema_key="lsrag.structure.default", schema_version="v1", registry_digest=digest
    )
    with pytest.raises(MkbError, match="GENERATION_SCHEMA_DRIFT"):
        assert_frozen_schema_matches({}, schema_key="lsrag.structure.default", schema_version="v1", registry_digest=digest)
    with pytest.raises(MkbError, match="GENERATION_SCHEMA_DRIFT"):
        assert_frozen_schema_matches(
            snapshot, schema_key="lsrag.structure.default", schema_version="v1", registry_digest="b" * 64
        )
    drifted = {
        "l4": {
            "schemas": {"lsrag.structure.default@v1": {"schema_digest": digest}},
            "layered_schema_sha256": "c" * 64,
        }
    }
    with pytest.raises(MkbError, match="GENERATION_SCHEMA_DRIFT"):
        assert_frozen_schema_matches(
            drifted, schema_key="lsrag.structure.default", schema_version="v1", registry_digest=digest
        )


def test_structured_schema_is_not_dummy_object() -> None:
    schema = load_layered_json_schema()
    assert schema.get("additionalProperties") is False
    assert schema != {"type": "object"}
    from src.contracts.inference.models import InferenceBinding, StructuredGenerateRequest
    from src.llm_adapters.local_vllm import _structured_json_schema

    request = StructuredGenerateRequest(
        team_uuid="team-a",
        binding=InferenceBinding(
            capability_key="structured_generate",
            adapter_kind="local_vllm",
            model_key="m",
            model_version="v1",
            binding_digest="a" * 64,
        ),
        prompt_ref="prompt",
        prompt_digest="a" * 64,
        input_text="{}",
        json_schema_ref="lsrag.layered_content.default@v1",
        json_schema_digest="b" * 64,
    )
    sent = _structured_json_schema(request)
    assert sent == schema


def test_title_from_layered_context_meta() -> None:
    assert _title_from_layered({"context_meta": {"title": "Notice"}}) == "Notice"
    assert _title_from_layered({"context_meta": {}, "layered_content": []}) is None


def test_pack_dedups_same_generation_root() -> None:
    from src.contracts.vector.models import GenerationScopedCoordinate, RetrievalGenerationRefs, RetrievalResult
    from src.services.retrieval.retrieval_pack import RetrievalPackMixin

    def _result(unit_id: str) -> RetrievalResult:
        gen = "11111111-1111-4111-8111-111111111111"
        root = GenerationScopedCoordinate(
            generation_artifact_uuid=gen, unit_id="g0:b0000", granularity=0, channel="original"
        )
        return RetrievalResult(
            score=0.99,
            ann_score=0.99,
            hit_channel="original",
            payload_content="focus",
            coordinate=GenerationScopedCoordinate(
                generation_artifact_uuid=gen, unit_id=unit_id, granularity=1, channel="original"
            ),
            granularity=1,
            generation_refs=RetrievalGenerationRefs(
                intake_item_uuid="item-1",
                intake_revision_uuid="rev-1",
                generation_artifact_uuid=gen,
                generation_artifact_type="dual_channel_projection",
                namespace_uuid="ns-1",
                publication_proof_uuid="proof-1",
            ),
            traceback_status="not_needed",
            context_tier="focus_fragment",
            filters_echo={},
            inflation_root_content="ROOT",
            inflation_root_coordinate=root,
            inflation_status="attached",
        )

    mixin = RetrievalPackMixin.__new__(RetrievalPackMixin)
    mixin._pack_max_hits = 10
    mixin._pack_max_chars = 10_000
    packed = mixin._pack([_result("g1:b0001"), _result("g1:b0002")])
    root_segments = [segment for segment in packed.segments if segment.tier == "document_root"]
    assert len(root_segments) == 1


def test_dedup_keeps_high_score_original_over_resolved_summary() -> None:
    from src.contracts.vector.models import GenerationScopedCoordinate, RetrievalGenerationRefs, RetrievalResult
    from src.services.retrieval.models import _Candidate, _ResultWork
    from src.services.retrieval.retrieval_pack import RetrievalPackMixin

    gen = "11111111-1111-4111-8111-111111111111"
    unit = "g1:b0001"

    def work(channel: str, score: float, traceback: str) -> _ResultWork:
        result = RetrievalResult(
            score=score,
            ann_score=score,
            hit_channel=channel,  # type: ignore[arg-type]
            payload_content=channel,
            coordinate=GenerationScopedCoordinate(
                generation_artifact_uuid=gen, unit_id=unit, granularity=1, channel=channel  # type: ignore[arg-type]
            ),
            granularity=1,
            generation_refs=RetrievalGenerationRefs(
                intake_item_uuid="item-1",
                intake_revision_uuid="rev-1",
                generation_artifact_uuid=gen,
                generation_artifact_type="dual_channel_projection",
                namespace_uuid="ns-1",
                publication_proof_uuid="proof-1",
            ),
            traceback_status=traceback,  # type: ignore[arg-type]
            context_tier="focus_fragment",
            filters_echo={},
        )
        candidate = _Candidate(
            row={
                "vector_record_uuid": f"{channel}-vec",
                "generation_artifact_uuid": gen,
                "block_or_unit_id": unit,
                "channel": channel,
            },
            ann_score=score,
            granularity=1,
        )
        return _ResultWork(candidate=candidate, result=result)

    kept = RetrievalPackMixin._deduplicate(
        [work("summary", 0.10, "resolved"), work("original", 0.99, "not_needed")]
    )
    assert len(kept) == 1
    assert kept[0].result.hit_channel == "original"
    assert kept[0].result.ann_score == 0.99


@pytest.mark.asyncio
async def test_offline_rank_rejects_live_namespace() -> None:
    from src.services.retrieval.models import _SearchInput
    from src.services.retrieval.retrieval_rank import RetrievalRankMixin

    mixin = RetrievalRankMixin.__new__(RetrievalRankMixin)
    mixin._candidate_scorer = None
    query = _SearchInput(
        team_uuid="11111111-1111-4111-8111-111111111111",
        query="hello",
        namespace_key="default",
        namespace_uuid=None,
        return_k=5,
        recall_k=20,
        threshold=0.0,
        filters={},
        include_pack=False,
    )
    with pytest.raises(MkbError, match="RETRIEVE_SPACE_LAYER_A_MISMATCH"):
        await mixin._rank_ann_candidates(
            query,
            {"adapter_kind": "local_vllm", "dimension": 4},
            [],
            None,
        )


def test_retry_delay_uses_full_jitter() -> None:
    from src.contracts.inference.models import EmbeddingRequest, EmbeddingResponse
    from src.runtime.inference.facade import InferenceFacade

    class _Adapter:
        adapter_kind = "local_vllm"

        async def embed(self, request: EmbeddingRequest) -> EmbeddingResponse:
            return EmbeddingResponse(
                vectors=[[0.0]],
                model_key=request.binding.model_key,
                model_version=request.binding.model_version,
                dimension=1,
            )

    facade = InferenceFacade(_Adapter(), max_in_flight=1)  # type: ignore[arg-type]
    delays = {facade._retry_delay(3) for _ in range(30)}
    assert len(delays) > 1
    assert max(delays) <= facade._max_delay_seconds


def test_turso_factory_rejects_unbound_native_ann(tmp_path: Path) -> None:
    from src.persistence.factory import build_persistence

    with pytest.raises(ValueError, match="native_ann"):
        build_persistence(
            tmp_path / "x.db",
            Path("src/persistence/migrations"),
            backend="turso",
            vector_backend="native_ann",
        )


def test_forged_sqlite_env_without_pytest_module_is_rejected() -> None:
    script = (
        "import os, sys\n"
        "os.environ['PYTEST_CURRENT_TEST'] = 'forged::test'\n"
        "os.environ['MKB_ALLOW_SQLITE'] = '1'\n"
        "sys.modules.pop('pytest', None)\n"
        "from src.persistence.factory import sqlite_backend_permitted, build_persistence\n"
        "from pathlib import Path\n"
        "assert sqlite_backend_permitted() is False\n"
        "try:\n"
        "    build_persistence(Path('x.db'), Path('src/persistence/migrations'), backend='sqlite')\n"
        "except ValueError as exc:\n"
        "    assert 'test-only' in str(exc)\n"
        "else:\n"
        "    raise SystemExit('sqlite factory opened without pytest')\n"
    )
    result = subprocess.run([sys.executable, "-c", script], cwd=str(Path.cwd()), capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr
