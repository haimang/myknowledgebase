"""NS6-T21–T27: serving immutability, HITL, digest, idempotency, namespace."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import PromoteRequest
from src.persistence.sqlite_port import SqlitePersistence
from src.runtime.intake.core import IntakeCoreMixin
from src.runtime.intake.pipeline import IntakePipeline
from src.runtime.intake.vector_publish_commit import IntakeVectorPublishCommitMixin
from src.services.lsrag_construct.binder import bind_construct
from src.storage.local_store import LocalObjectStore


def _command(team_uuid: str) -> ProcessCommand:
    digest = "a" * 64
    return ProcessCommand(
        schema_version="mkb.process-command.v1",
        team_uuid=team_uuid,
        task_uuid=uuid7(),
        trace_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
        process_key="lsrag.vectorize",
        process_contract_version="v1",
        fencing_generation=1,
        command_input_digest=digest,
        input_manifest_ref="mkbtest:in",
        input_manifest_digest=digest,
        config_snapshot_ref="mkbtest:cfg",
        config_snapshot_digest=digest,
        binding_digest=digest,
    )


def _layer_a(*, dimension: int = 2) -> dict[str, object]:
    return {"model_key": "m", "model_version": "v1", "adapter_kind": "local", "dimension": dimension}


async def _seed_team_namespace(
    persistence: SqlitePersistence,
    *,
    team: str,
    namespace: str,
    generation: int = 0,
    dimension: int = 2,
) -> None:
    now = utc_now()
    key = IntakeVectorPublishCommitMixin._namespace_key(_layer_a(dimension=dimension))
    connection = persistence._connect()
    connection.execute("PRAGMA foreign_keys = OFF")
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team, "vec", "a" * 64, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_model_catalog "
            "(model_uuid,model_key,model_version,modality,provider_family,default_dimension,definition_digest,status,registered_at) "
            "VALUES (?,?,?,'embed','local',?,?,'active',?)",
            (uuid7(), "m", "v1", dimension, "b" * 64, now),
        )
        await tx.execute(
            "INSERT INTO mkb_vector_namespaces "
            "(namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,embedding_model_version,"
            "adapter_kind,dimension,index_generation,status,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,'active',?,?)",
            (namespace, team, key, "m", "m", "v1", "local", dimension, generation, now, now),
        )


@pytest.mark.asyncio
async def test_upsert_does_not_update_indexed_rows(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "vec.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    mixin = IntakePipeline.__new__(IntakePipeline)
    mixin._persistence = persistence  # type: ignore[attr-defined]
    team = uuid7()
    namespace = uuid7()
    artifact = uuid7()
    record_uuid = uuid7()
    now = utc_now()
    await _seed_team_namespace(persistence, team=team, namespace=namespace, generation=1)
    connection = persistence._connect()
    connection.execute("PRAGMA foreign_keys = OFF")
    async with persistence.transaction() as tx:
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
    command = _command(team)
    state = {
        "dual_channel_artifact_uuid": artifact,
        "dual_channel_artifact_ref": "mkbobj:v1:vec",
        "intake_source_uuid": uuid7(),
        "intake_item_uuid": uuid7(),
        "intake_revision_uuid": uuid7(),
    }
    content = "body-text"
    async with persistence.transaction() as tx:
        await mixin._upsert_vector_record_tx(
            tx,
            command=command,
            state=state,
            namespace_uuid=namespace,
            index_generation=2,
            layer_a=_layer_a(),
            record={
                "vector_record_uuid": uuid7(),
                "unit_id": "u1",
                "channel": "original",
                "content": content,
                "content_digest": stable_digest({"text": content}),
            },
            embedding_blob=b"\x00" * 8,
        )
    async with persistence.transaction() as tx:
        indexed = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_vector_records "
            "WHERE publication_state='indexed' AND index_generation=1 AND vector_record_uuid=?",
            (record_uuid,),
        )
        next_gen = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_vector_records "
            "WHERE index_generation=2 AND publication_state='withdrawn'",
        )
    assert indexed == {"count": 1}
    assert next_gen == {"count": 1}
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
    persistence = SqlitePersistence(tmp_path / "ns.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    mixin = IntakePipeline.__new__(IntakePipeline)
    mixin._persistence = persistence  # type: ignore[attr-defined]
    team = uuid7()
    now = utc_now()
    connection = persistence._connect()
    connection.execute("PRAGMA foreign_keys = OFF")
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team, "ns", "a" * 64, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_model_catalog "
            "(model_uuid,model_key,model_version,modality,provider_family,default_dimension,definition_digest,status,registered_at) "
            "VALUES (?,?,?,'embed','local',64,?,'active',?)",
            (uuid7(), "m", "v1", "b" * 64, now),
        )
        await mixin._ensure_namespace(tx, team, uuid7(), _layer_a(dimension=64))
        await mixin._ensure_namespace(tx, team, uuid7(), _layer_a(dimension=1024))
        rows = await tx.fetchall(
            "SELECT namespace_key, dimension FROM mkb_vector_namespaces WHERE team_uuid=? ORDER BY dimension",
            (team,),
        )
    keys = {row["namespace_key"] for row in rows}
    assert len(keys) == 2
    assert IntakeVectorPublishCommitMixin._namespace_key(_layer_a(dimension=64)) in keys
    assert IntakeVectorPublishCommitMixin._namespace_key(_layer_a(dimension=1024)) in keys
    await persistence.close()


@pytest.mark.asyncio
async def test_migration_016_adds_source_external_key_unique(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "src.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    team = uuid7()
    now = utc_now()
    first = uuid7()
    second = uuid7()
    connection = persistence._connect()
    connection.execute("PRAGMA foreign_keys = OFF")
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_teams(team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team, "src", "a" * 64, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_intake_sources "
            "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
            "source_descriptor_ref,source_descriptor_digest,accepts_new_snapshots,created_at,updated_at,"
            "normalized_external_key) VALUES (?,?,?,'v1',?,?,?,1,?,?,?)",
            (team, first, "inline_payload", "d" * 64, "mkbtest:a", "e" * 64, now, now, "same-key"),
        )
        await tx.execute(
            "INSERT OR IGNORE INTO mkb_intake_sources "
            "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
            "source_descriptor_ref,source_descriptor_digest,accepts_new_snapshots,created_at,updated_at,"
            "normalized_external_key) VALUES (?,?,?,'v1',?,?,?,1,?,?,?)",
            (team, second, "inline_payload", "d" * 64, "mkbtest:b", "f" * 64, now, now, "same-key"),
        )
        count = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_intake_sources WHERE team_uuid=? AND normalized_external_key='same-key'",
            (team,),
        )
        stored = await tx.fetchone(
            "SELECT intake_source_uuid FROM mkb_intake_sources WHERE team_uuid=? AND normalized_external_key='same-key'",
            (team,),
        )
    assert count == {"count": 1}
    assert stored == {"intake_source_uuid": first}
    await persistence.close()


@pytest.mark.asyncio
async def test_raw_clean_cas_digests_are_sha256_of_bytes(tmp_path: Path) -> None:
    store = LocalObjectStore(tmp_path / "objects")
    team = uuid7()
    raw = b'{"text":"would-be-peeled"}'
    clean = b"clean-text"
    raw_stat = await store.promote(raw, PromoteRequest(team_uuid=team, purpose="process_io", media_type="text/plain"))
    clean_stat = await store.promote(
        clean, PromoteRequest(team_uuid=team, purpose="process_io", media_type="text/plain")
    )
    raw_bytes = await store.read_verified(team, raw_stat.handle)
    clean_bytes = await store.read_verified(team, clean_stat.handle)
    assert hashlib.sha256(raw_bytes).hexdigest() == raw_stat.sha256
    assert hashlib.sha256(clean_bytes).hexdigest() == clean_stat.sha256
    assert len(raw_bytes) == raw_stat.size_bytes
    assert len(clean_bytes) == clean_stat.size_bytes
    mixin = IntakeCoreMixin.__new__(IntakeCoreMixin)
    mixin._storage = store  # type: ignore[attr-defined]
    decoded = await mixin._read_frozen_clean_text(
        _command(team),
        {
            "clean_artifact": {
                "logical_handle": clean_stat.handle.value,
                "content_digest": clean_stat.sha256,
                "intake_artifact_uuid": uuid7(),
            }
        },
    )
    assert decoded == "clean-text"
    json_looking = await mixin._read_frozen_clean_text(
        _command(team),
        {
            "clean_artifact": {
                "logical_handle": raw_stat.handle.value,
                "content_digest": raw_stat.sha256,
                "intake_artifact_uuid": uuid7(),
            }
        },
    )
    assert json_looking == '{"text":"would-be-peeled"}'


@pytest.mark.asyncio
async def test_overlapping_vectorize_generation_cas(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "gen.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    mixin = IntakePipeline.__new__(IntakePipeline)
    mixin._persistence = persistence  # type: ignore[attr-defined]
    team = uuid7()
    namespace = uuid7()
    artifact = uuid7()
    await _seed_team_namespace(persistence, team=team, namespace=namespace, generation=0)
    command = _command(team)
    state = {
        "dual_channel_artifact_uuid": artifact,
        "dual_channel_artifact_ref": "mkbobj:v1:vec",
        "intake_source_uuid": uuid7(),
        "intake_item_uuid": uuid7(),
        "intake_revision_uuid": uuid7(),
    }
    content = "overlap-body"

    async def _write_generation(index_generation: int) -> int:
        async with persistence.transaction() as tx:
            claimed = await tx.execute(
                "UPDATE mkb_vector_namespaces SET index_generation=?,updated_at=? "
                "WHERE namespace_uuid=? AND team_uuid=? AND status='active' AND index_generation=?",
                (index_generation, utc_now(), namespace, team, index_generation - 1),
            )
            if claimed.rowcount != 1:
                return 0
            await mixin._upsert_vector_record_tx(
                tx,
                command=command,
                state=state,
                namespace_uuid=namespace,
                index_generation=index_generation,
                layer_a=_layer_a(),
                record={
                    "vector_record_uuid": uuid7(),
                    "unit_id": "u1",
                    "channel": "original",
                    "content": content,
                    "content_digest": stable_digest({"text": content}),
                },
                embedding_blob=b"\x00" * 8,
            )
            return 1

    assert await _write_generation(1) == 1
    assert await _write_generation(1) == 0
    async with persistence.transaction() as tx:
        rows = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_vector_records WHERE team_uuid=? AND index_generation=1",
            (team,),
        )
        pointer = await tx.fetchone(
            "SELECT index_generation FROM mkb_vector_namespaces WHERE namespace_uuid=?",
            (namespace,),
        )
    assert rows == {"count": 1}
    assert pointer == {"index_generation": 1}
    await persistence.close()
