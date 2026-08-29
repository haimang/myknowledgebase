"""NH5-T03: ten semantic entries are coherent, typed, and provenance-bound."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.intake.semantics import generic_semantic_authority
from src.persistence.factory import build_persistence
from src.runtime.intake.pipeline import IntakePipeline
from src.services.registry import RegistryService


async def _fixture(tmp_path: Path):
    persistence = build_persistence(
        tmp_path / "semantics.sqlite3",
        Path("src/persistence/migrations"),
        backend="turso",
        concurrent_writes_required=False,
        native_vector_required=False,
    )
    await persistence.migrate()
    await RegistryService(persistence, Path("data/prompts")).bootstrap()
    return persistence, IntakePipeline(persistence, None, None)  # type: ignore[arg-type]


def _state() -> dict:
    descriptor = {
        "realm": "documentation",
        "type": "article",
        "channel": "policy",
        "source_name": "owner-source",
        "context_tags": ["tag:a", "tag:b"],
        "title": "Semantic title",
    }
    filter_meta, context_meta, tuples = generic_semantic_authority(descriptor)
    return {
        "source_kind": "inline_payload",
        "realm": "documentation",
        "type": "article",
        "channel": "general",
        "source_name": "test-fixture",
"clean_digest": stable_digest({"clean": "semantic body"}),
        "filter_meta": filter_meta.model_dump(mode="json"),
        "context_meta": context_meta.model_dump(mode="json"),
        "semantic_tuples": [item.model_dump(mode="json") for item in tuples],
    }


@pytest.mark.asyncio
async def test_generic_ten_entries_blobs_and_provenance_share_one_source(tmp_path: Path) -> None:
    persistence, pipeline = await _fixture(tmp_path)
    try:
        async with persistence.transaction() as tx:
            entries = await pipeline._initial_semantics_tx(tx, _state())  # noqa: SLF001
        assert {entry["semantic_key"] for entry in entries} == {
            "source_representation",
            "canonical_content",
            "context_metadata",
            "filter_metadata",
            "realm",
            "type",
            "channel",
            "source_name",
            "is_active",
            "context_tags",
        }
        by_key = {entry["semantic_key"]: entry for entry in entries}
        assert json.loads(by_key["filter_metadata"]["value"]) == _state()["filter_meta"]
        assert json.loads(by_key["context_metadata"]["value"]) == _state()["context_meta"]
        assert by_key["realm"]["value"] == "documentation"
        assert by_key["context_tags"]["value"] == "tag:a\ntag:b"
        assert by_key["is_active"]["value"] == 1
        assert by_key["is_active"]["value_provenance"] == "system"
        assert by_key["realm"]["value_provenance"] == "caller"
        assert by_key["filter_metadata"]["value_provenance"] == "system"
        assert pipeline._semantic_fingerprint(entries) == pipeline._semantic_fingerprint(  # noqa: SLF001
            [{**entry, "value_provenance": "mapper"} for entry in entries]
        )
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_stub_or_missing_six_tuple_cannot_become_complete(tmp_path: Path) -> None:
    persistence, pipeline = await _fixture(tmp_path)
    try:
        state = {
            "source_kind": "inline_payload",
            "realm": "documentation",
            "type": "article",
            "channel": "general",
            "source_name": "test-fixture",
"clean_digest": stable_digest({"clean": "body"}),
            "filter_meta": {"source_kind": "inline_payload"},
            "context_meta": {},
        }
        with pytest.raises(MkbError) as raised:
            async with persistence.transaction() as tx:
                await pipeline._initial_semantics_tx(tx, state)  # noqa: SLF001
        assert raised.value.code == "INTAKE_SEMANTICS_INCOMPLETE"
        async with persistence.transaction() as tx:
            revisions = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_intake_revisions")
            vectors = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_vector_records")
        assert revisions == vectors == {"count": 0}
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_tuple_blob_conflict_fails_before_revision_write(tmp_path: Path) -> None:
    persistence, pipeline = await _fixture(tmp_path)
    try:
        state = _state()
        state["semantic_tuples"][0]["value"] = "conflicting-realm"
        with pytest.raises(MkbError) as raised:
            async with persistence.transaction() as tx:
                await pipeline._initial_semantics_tx(tx, state)  # noqa: SLF001
        assert raised.value.code == "INTAKE_SEMANTICS_CONFLICT"
    finally:
        await persistence.close()
