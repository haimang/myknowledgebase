"""Integration coverage for the storage-backed S04/S10 retrieval adapters."""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest
from src.persistence.retrieval_access import DUAL_CHANNEL_PROJECTION_SCHEMA, ArtifactRetrievalAccess
from src.persistence.sqlite_port import SqlitePersistence
from src.services.retrieval import RetrievalService
from src.storage.local_store import LocalObjectStore

TEAM = "123e4567-e89b-42d3-a456-426614174100"
OTHER_TEAM = "123e4567-e89b-42d3-a456-426614174101"
NAMESPACE = "123e4567-e89b-42d3-a456-426614174102"
ITEM = "123e4567-e89b-42d3-a456-426614174103"
INACTIVE_ITEM = "123e4567-e89b-42d3-a456-426614174104"
STALE_ITEM = "123e4567-e89b-42d3-a456-426614174105"
REVISION = "123e4567-e89b-42d3-a456-426614174106"
STALE_REVISION = "123e4567-e89b-42d3-a456-426614174107"
GENERATION = "123e4567-e89b-42d3-a456-426614174108"
PROOF = "123e4567-e89b-42d3-a456-426614174109"
SOURCE = "123e4567-e89b-42d3-a456-426614174110"
GOOD_RECORD = "123e4567-e89b-42d3-a456-426614174111"
INACTIVE_RECORD = "123e4567-e89b-42d3-a456-426614174112"
STALE_RECORD = "123e4567-e89b-42d3-a456-426614174113"
OTHER_RECORD = "123e4567-e89b-42d3-a456-426614174114"
SUMMARY_RECORD = "123e4567-e89b-42d3-a456-426614174115"
ORIGINAL_RECORD = "123e4567-e89b-42d3-a456-426614174116"
NOW = "2026-08-12T00:00:00Z"


class RecordingStore:
    """A logical-handle spy around the real local object-store implementation."""

    def __init__(self, inner: LocalObjectStore) -> None:
        self.inner = inner
        self.read_calls: list[tuple[str, str]] = []

    async def promote(self, data: bytes, request: PromoteRequest) -> ObjectStat:
        return await self.inner.promote(data, request)

    async def read_verified(self, team_uuid: str, handle: ObjectHandle) -> bytes:
        self.read_calls.append((team_uuid, handle.value))
        return await self.inner.read_verified(team_uuid, handle)

    async def delete_if_unreferenced(self, team_uuid: str, handle: ObjectHandle) -> bool:
        return await self.inner.delete_if_unreferenced(team_uuid, handle)

    async def readiness(self) -> bool:
        return await self.inner.readiness()


@dataclass(slots=True)
class Environment:
    persistence: SqlitePersistence
    store: RecordingStore
    access: ArtifactRetrievalAccess


@pytest.fixture
async def environment(tmp_path: Path) -> Environment:
    persistence = SqlitePersistence(tmp_path / "mkb.db", Path("src/persistence/migrations"))
    await persistence.migrate()
    connection = persistence._connect()  # fixture-only seed setup
    for team_uuid in (TEAM, OTHER_TEAM):
        connection.execute(
            "INSERT INTO mkb_teams (team_uuid,name,creation_fingerprint,created_at,updated_at) VALUES (?,?,?,?,?)",
            (team_uuid, f"team-{team_uuid[-4:]}", "a" * 64, NOW, NOW),
        )
    connection.commit()
    store = RecordingStore(LocalObjectStore(tmp_path / "objects"))
    yield Environment(persistence, store, ArtifactRetrievalAccess(persistence, store))
    await persistence.close()


def _channel(content: str) -> dict[str, str]:
    return {"content": content, "content_digest": hashlib.sha256(content.encode("utf-8")).hexdigest()}


def _projection_document(*, include_generation: bool = True) -> bytes:
    body: dict[str, object] = {
        "schema_version": DUAL_CHANNEL_PROJECTION_SCHEMA,
        "units": [
            {
                "unit_id": "g0:root",
                "granularity": 0,
                "channels": {"original": _channel("full source document")},
            },
            {
                "unit_id": "g1:revenue",
                "granularity": 1,
                "channels": {
                    "original": _channel("original revenue evidence"),
                    "summary": _channel("summary revenue evidence"),
                },
            },
        ],
    }
    if include_generation:
        body["generation_artifact_uuid"] = GENERATION
    return json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _construct_stage_output_document(*, artifact_uuid: str = GENERATION) -> bytes:
    """The exact immutable envelope currently stored for construct artifacts."""

    original = "original revenue evidence"
    summary = "summary revenue evidence"
    projection = {
        "schema_version": DUAL_CHANNEL_PROJECTION_SCHEMA,
        "recipe_version": "content_full.v1",
        "units": [
            {
                "unit_id": "g1:revenue",
                "granularity": 1,
                "original": original,
                "summary": summary,
                "original_digest": stable_digest({"text": original}),
                "summary_digest": stable_digest({"text": summary}),
            }
        ],
    }
    envelope = {
        "schema_version": "mkb.stage-output.v1",
        "process_key": "lsrag.construct",
        "process_uuid": "123e4567-e89b-42d3-a456-426614174117",
        "fencing_generation": 1,
        "state": {"dual_channel_artifact_uuid": artifact_uuid, "dual_channel": projection},
        "output": {"construct_package": {"content_full": True, "dual_channel": projection}},
    }
    return json.dumps(envelope, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


async def _seed_generation(environment: Environment, *, document: bytes | None = None) -> ObjectStat:
    data = document if document is not None else _projection_document()
    stat = await environment.store.promote(
        data,
        PromoteRequest(team_uuid=TEAM, purpose="generation_artifact", media_type="application/json"),
    )
    connection = environment.persistence._connect()  # fixture-only seed setup
    connection.execute(
        """INSERT INTO mkb_generation_artifacts
        (generation_artifact_uuid,team_uuid,artifact_type,logical_handle,media_type,size_bytes,
         content_digest,validation_disposition,created_at)
        VALUES (?,?,?,?,?,?,?,?,?)""",
        (
            GENERATION,
            TEAM,
            "dual_channel_projection",
            stat.handle.value,
            "application/json",
            stat.size_bytes,
            stat.sha256,
            "full_valid",
            NOW,
        ),
    )
    connection.commit()
    return stat


def _disable_foreign_keys(environment: Environment) -> None:
    # The adapter tests isolate the projected facts they consume.  Full end-to-
    # end admission later writes the same graph through normal S04/S08 flows.
    environment.persistence._connect().execute("PRAGMA foreign_keys = OFF")


def _insert_item(
    environment: Environment,
    *,
    team_uuid: str,
    item_uuid: str,
    lifecycle: str,
    serving_revision_uuid: str | None,
) -> None:
    environment.persistence._connect().execute(
        """INSERT INTO mkb_intake_items
        (team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,
         latest_revision_uuid,serving_revision_uuid,row_revision,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (
            team_uuid,
            item_uuid,
            SOURCE,
            f"key-{item_uuid[-4:]}",
            lifecycle,
            REVISION,
            serving_revision_uuid,
            0,
            NOW,
            NOW,
        ),
    )


def _insert_record(
    environment: Environment,
    *,
    record_uuid: str,
    team_uuid: str,
    item_uuid: str,
    revision_uuid: str,
    channel: str = "original",
    unit_id: str = "g1:revenue",
) -> None:
    environment.persistence._connect().execute(
        """INSERT INTO mkb_vector_records
        (vector_record_uuid,team_uuid,namespace_uuid,generation_artifact_uuid,generation_artifact_type,
         block_or_unit_id,channel,intake_source_uuid,intake_item_uuid,intake_revision_uuid,
         content_digest,embedding_model,embedding_model_key,embedding_model_version,
         adapter_kind,dimension,embedding,publication_state,index_generation,embedded_at,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            record_uuid,
            team_uuid,
            NAMESPACE,
            GENERATION,
            "dual_channel_projection",
            unit_id,
            channel,
            SOURCE,
            item_uuid,
            revision_uuid,
            "b" * 64,
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


async def test_body_access_reads_verified_logical_handle_and_parses_channels(environment: Environment) -> None:
    stat = await _seed_generation(environment)

    summary = await environment.access.load_retrieval_body(
        team_uuid=TEAM,
        generation_artifact_uuid=GENERATION,
        unit_id="g1:revenue",
        channel="summary",
    )
    original = await environment.access.load_retrieval_body(
        team_uuid=TEAM,
        generation_artifact_uuid=GENERATION,
        unit_id="g1:revenue",
        channel="original",
    )

    assert summary == {"content": "summary revenue evidence", "granularity": 1}
    assert original == {"content": "original revenue evidence", "granularity": 1}
    assert environment.store.read_calls == [(TEAM, stat.handle.value), (TEAM, stat.handle.value)]
    assert "/" not in summary["content"]
    assert (
        await environment.access.load_retrieval_body(
            team_uuid=TEAM,
            generation_artifact_uuid=GENERATION,
            unit_id="g1:unknown",
            channel="original",
        )
        is None
    )


async def test_body_access_fails_closed_when_generation_ledger_digest_changes(environment: Environment) -> None:
    await _seed_generation(environment)
    connection = environment.persistence._connect()
    connection.execute("UPDATE mkb_generation_artifacts SET content_digest=?", ("c" * 64,))
    connection.commit()

    with pytest.raises(MkbError) as error:
        await environment.access.load_retrieval_body(
            team_uuid=TEAM,
            generation_artifact_uuid=GENERATION,
            unit_id="g1:revenue",
            channel="summary",
        )
    assert error.value.code == "RETRIEVE_BODY_INTEGRITY"


async def test_body_access_accepts_current_construct_stage_envelope(environment: Environment) -> None:
    await _seed_generation(environment, document=_construct_stage_output_document())

    summary = await environment.access.load_retrieval_body(
        team_uuid=TEAM,
        generation_artifact_uuid=GENERATION,
        unit_id="g1:revenue",
        channel="summary",
    )
    original = await environment.access.load_retrieval_body(
        team_uuid=TEAM,
        generation_artifact_uuid=GENERATION,
        unit_id="g1:revenue",
        channel="original",
    )

    assert summary == {"content": "summary revenue evidence", "granularity": 1}
    assert original == {"content": "original revenue evidence", "granularity": 1}


async def test_body_access_rejects_construct_envelope_with_mismatched_artifact_coordinate(
    environment: Environment,
) -> None:
    await _seed_generation(environment, document=_construct_stage_output_document(artifact_uuid=STALE_REVISION))

    with pytest.raises(MkbError) as error:
        await environment.access.load_retrieval_body(
            team_uuid=TEAM,
            generation_artifact_uuid=GENERATION,
            unit_id="g1:revenue",
            channel="summary",
        )
    assert error.value.code == "RETRIEVE_BODY_DOCUMENT_INVALID"


async def test_batch_eligibility_enforces_team_lifecycle_and_exact_serving_revision(environment: Environment) -> None:
    _disable_foreign_keys(environment)
    _insert_item(environment, team_uuid=TEAM, item_uuid=ITEM, lifecycle="active", serving_revision_uuid=REVISION)
    _insert_item(
        environment, team_uuid=TEAM, item_uuid=INACTIVE_ITEM, lifecycle="deactivated", serving_revision_uuid=None
    )
    _insert_item(
        environment, team_uuid=TEAM, item_uuid=STALE_ITEM, lifecycle="active", serving_revision_uuid=STALE_REVISION
    )
    _insert_item(environment, team_uuid=OTHER_TEAM, item_uuid=ITEM, lifecycle="active", serving_revision_uuid=REVISION)
    _insert_record(environment, record_uuid=GOOD_RECORD, team_uuid=TEAM, item_uuid=ITEM, revision_uuid=REVISION)
    _insert_record(
        environment,
        record_uuid=INACTIVE_RECORD,
        team_uuid=TEAM,
        item_uuid=INACTIVE_ITEM,
        revision_uuid=REVISION,
        unit_id="g1:inactive",
    )
    _insert_record(
        environment,
        record_uuid=STALE_RECORD,
        team_uuid=TEAM,
        item_uuid=STALE_ITEM,
        revision_uuid=REVISION,
        unit_id="g1:stale",
    )
    _insert_record(environment, record_uuid=OTHER_RECORD, team_uuid=OTHER_TEAM, item_uuid=ITEM, revision_uuid=REVISION)
    environment.persistence._connect().commit()

    # A deliberately tiny chunk size proves that the port keeps the same
    # fence when its input spans several SQL batches.
    access = ArtifactRetrievalAccess(environment.persistence, environment.store, candidate_chunk_size=1)
    approved = await access.filter_retrieval_eligible(
        team_uuid=TEAM,
        candidates=[
            {"vector_record_uuid": GOOD_RECORD, "intake_item_uuid": ITEM, "intake_revision_uuid": REVISION},
            {
                "vector_record_uuid": INACTIVE_RECORD,
                "intake_item_uuid": INACTIVE_ITEM,
                "intake_revision_uuid": REVISION,
            },
            {"vector_record_uuid": STALE_RECORD, "intake_item_uuid": STALE_ITEM, "intake_revision_uuid": REVISION},
            {"vector_record_uuid": OTHER_RECORD, "intake_item_uuid": ITEM, "intake_revision_uuid": REVISION},
            {"vector_record_uuid": "", "intake_item_uuid": ITEM, "intake_revision_uuid": REVISION},
        ],
    )

    assert approved == {GOOD_RECORD}
    conflicting = await access.filter_retrieval_eligible(
        team_uuid=TEAM,
        candidates=[
            {"vector_record_uuid": GOOD_RECORD, "intake_item_uuid": ITEM, "intake_revision_uuid": REVISION},
            {
                "vector_record_uuid": GOOD_RECORD,
                "intake_item_uuid": ITEM,
                "intake_revision_uuid": STALE_REVISION,
            },
        ],
    )
    assert conflicting == set()


async def test_access_ports_supply_traceback_material_to_retrieval_service(environment: Environment) -> None:
    await _seed_generation(environment)
    _disable_foreign_keys(environment)
    connection = environment.persistence._connect()
    connection.execute(
        """INSERT INTO mkb_vector_namespaces
        (namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,
         embedding_model_version,adapter_kind,dimension,created_at,updated_at)
        VALUES (?,?,?,?,?,?,?,?,?,?)""",
        (NAMESPACE, TEAM, "default", "model", "model", "v1", "deterministic", 2, NOW, NOW),
    )
    _insert_item(environment, team_uuid=TEAM, item_uuid=ITEM, lifecycle="active", serving_revision_uuid=REVISION)
    _insert_record(
        environment,
        record_uuid=SUMMARY_RECORD,
        team_uuid=TEAM,
        item_uuid=ITEM,
        revision_uuid=REVISION,
        channel="summary",
    )
    _insert_record(
        environment,
        record_uuid=ORIGINAL_RECORD,
        team_uuid=TEAM,
        item_uuid=ITEM,
        revision_uuid=REVISION,
        channel="original",
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
            2,
            2,
            2,
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

    result = await RetrievalService(
        environment.persistence,
        body_port=environment.access,
        eligibility_port=environment.access,
    ).search({"team_uuid": TEAM, "namespace_key": "default", "query": "revenue", "include_pack": False})

    assert result["disposition"] == "ok"
    hit = result["results"][0]
    assert hit["hit_channel"] == "summary"
    assert hit["hit_content"] == "summary revenue evidence"
    assert hit["payload_content"] == "original revenue evidence"
    assert hit["traceback_status"] == "resolved"
