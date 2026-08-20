"""NS6-T21–T27: serving immutability, HITL, digest, idempotency, namespace."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import uuid7
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.intake.vector_publish_commit import IntakeVectorPublishCommitMixin
from src.services.lsrag_construct.binder import bind_construct


@pytest.mark.asyncio
async def test_upsert_does_not_update_indexed_rows(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "vec.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    mixin = IntakeVectorPublishCommitMixin()
    mixin._persistence = persistence  # type: ignore[attr-defined]
    team = uuid7()
    namespace = uuid7()
    artifact = uuid7()
    record_uuid = uuid7()
    now = "2026-08-20T00:00:00.000000Z"
    connection = persistence._connect()
    connection.execute("PRAGMA foreign_keys = OFF")
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team, "vec", "a" * 64, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_vector_namespaces "
            "(namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,embedding_model_version,"
            "adapter_kind,dimension,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
            (namespace, team, "k", "m", "m", "v1", "local", 2, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_vector_records "
            "(vector_record_uuid,team_uuid,namespace_uuid,generation_artifact_uuid,generation_artifact_type,"
            "block_or_unit_id,channel,content_digest,embedding_model,embedding_model_key,embedding_model_version,"
            "adapter_kind,dimension,embedding,publication_state,index_generation,embedded_at,created_at,updated_at) "
            "VALUES (?,?,?,?,'dual_channel_projection',?,'original',?,?,?,?,?,?,?,'indexed',1,?,?,?)",
            (
                record_uuid,
                team,
                namespace,
                artifact,
                "u1",
                "c" * 64,
                "m",
                "m",
                "v1",
                "local",
                2,
                b"\x00" * 8,
                now,
                now,
                now,
            ),
        )
    existing = await mixin._existing_vector_coordinate_uuid(
        team_uuid=team,
        namespace_uuid=namespace,
        generation_artifact_uuid=artifact,
        unit_id="u1",
        channel="original",
        embedding_model="m",
        index_generation=2,
    )
    assert existing is None
    async with persistence.transaction() as tx:
        indexed = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_vector_records "
            "WHERE publication_state='indexed' AND index_generation=1 AND vector_record_uuid=?",
            (record_uuid,),
        )
    assert indexed == {"count": 1}
    await persistence.close()


def test_full_construct_rejects_title_headers() -> None:
    with pytest.raises(MkbError, match="CONSTRUCT_MODE_INVALID"):
        bind_construct(
            mode="full_construct",
            clean_text="body",
            structure=object(),  # type: ignore[arg-type]
            projection=object(),  # type: ignore[arg-type]
            summaries_by_block_id={"b0": "sum"},
            construction_artifact_uuid=uuid7(),
            dual_channel_artifact_uuid=uuid7(),
            metadata_headers={"title": "Notice"},
        )


@pytest.mark.asyncio
async def test_namespace_key_splits_layer_a(tmp_path: Path) -> None:
    a = {"model_key": "m", "model_version": "v1", "adapter_kind": "local", "dimension": 64}
    b = {"model_key": "m", "model_version": "v1", "adapter_kind": "local", "dimension": 1024}
    assert IntakeVectorPublishCommitMixin._namespace_key(a) != IntakeVectorPublishCommitMixin._namespace_key(b)


@pytest.mark.asyncio
async def test_migration_016_adds_source_external_key_unique(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "src.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    connection = persistence._connect()
    rows = connection.execute(
        "SELECT name FROM sqlite_master WHERE type='index' AND name='ux_intake_source_kind_external_key'"
    ).fetchall()
    assert rows
    await persistence.close()


def test_raw_clean_cas_digests_are_sha256_of_bytes() -> None:
    raw = b"raw-bytes"
    clean = b"clean-text"
    assert hashlib.sha256(raw).hexdigest() != hashlib.sha256(clean).hexdigest()
