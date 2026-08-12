"""Focused S09 old-generation grace and soft-delete regressions."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.persistence.sqlite_port import SqlitePersistence
from src.services.index_retirement import (
    RETIREMENT_POLICY_REF,
    IndexGenerationRetirementDisposition,
    IndexGenerationRetirementService,
)

TEAM = "123e4567-e89b-42d3-a456-426614174000"
NAMESPACE = "123e4567-e89b-42d3-a456-426614174001"
ITEM = "123e4567-e89b-42d3-a456-426614174002"
REVISION = "123e4567-e89b-42d3-a456-426614174003"
OLD_ARTIFACT = "123e4567-e89b-42d3-a456-426614174004"
NEW_ARTIFACT = "123e4567-e89b-42d3-a456-426614174005"
SOURCE = "123e4567-e89b-42d3-a456-426614174006"
PROOF = "123e4567-e89b-42d3-a456-426614174007"
CUTOVER = datetime(2026, 8, 12, tzinfo=UTC)


@dataclass
class MutableClock:
    now: datetime

    def __call__(self) -> datetime:
        return self.now


def _timestamp(value: datetime) -> str:
    return value.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


async def _seed_retired_generation(persistence: SqlitePersistence) -> None:
    """Install one item with g=1 retired and g=2 serving through the pointer."""

    connection = persistence._connect()  # focused fixture setup only
    connection.execute("PRAGMA foreign_keys = OFF")
    now = _timestamp(CUTOVER)
    connection.execute(
        "INSERT INTO mkb_vector_namespaces "
        "(namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,embedding_model_version,"
        "adapter_kind,dimension,created_at,updated_at) VALUES (?,?,?,?,?,?,?,?,?,?)",
        (NAMESPACE, TEAM, "default", "model", "model", "v1", "local", 2, now, now),
    )
    connection.execute(
        "INSERT INTO mkb_intake_items "
        "(team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,"
        "latest_revision_uuid,serving_revision_uuid,row_revision,created_at,updated_at) "
        "VALUES (?,?,?,?,?,?,?,?,?,?)",
        (TEAM, ITEM, SOURCE, "retirement-fixture", "active", REVISION, REVISION, 0, now, now),
    )
    for artifact_uuid, digest in ((OLD_ARTIFACT, "a" * 64), (NEW_ARTIFACT, "b" * 64)):
        connection.execute(
            "INSERT INTO mkb_generation_artifacts "
            "(generation_artifact_uuid,team_uuid,artifact_type,logical_handle,media_type,size_bytes,content_digest,"
            "validation_disposition,created_at) VALUES (?,?,?,?,?,?,?,?,?)",
            (
                artifact_uuid,
                TEAM,
                "dual_channel_projection",
                f"mkbobj:v1:{artifact_uuid}",
                "application/json",
                1,
                digest,
                "full_valid",
                now,
            ),
        )
    for record_uuid, artifact_uuid, generation, unit in (
        ("123e4567-e89b-42d3-a456-426614174010", OLD_ARTIFACT, 1, "old:original"),
        ("123e4567-e89b-42d3-a456-426614174011", OLD_ARTIFACT, 1, "old:summary"),
        ("123e4567-e89b-42d3-a456-426614174012", NEW_ARTIFACT, 2, "new:original"),
    ):
        connection.execute(
            "INSERT INTO mkb_vector_records "
            "(vector_record_uuid,team_uuid,namespace_uuid,generation_artifact_uuid,generation_artifact_type,"
            "block_or_unit_id,channel,intake_source_uuid,intake_item_uuid,intake_revision_uuid,content_digest,"
            "embedding_model,embedding_model_key,embedding_model_version,adapter_kind,dimension,embedding,"
            "publication_state,index_generation,embedded_at,created_at,updated_at) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                record_uuid,
                TEAM,
                NAMESPACE,
                artifact_uuid,
                "dual_channel_projection",
                unit,
                "original",
                SOURCE,
                ITEM,
                REVISION,
                "c" * 64,
                "model",
                "model",
                "v1",
                "local",
                2,
                b"\x00" * 8,
                "indexed",
                generation,
                now,
                now,
                now,
            ),
        )
    connection.execute(
        "INSERT INTO mkb_publication_proofs "
        "(proof_uuid,team_uuid,intake_item_uuid,intake_revision_uuid,generation_artifact_uuid,"
        "generation_artifact_type,namespace_uuid,embedding_model,embedding_model_key,embedding_model_version,"
        "adapter_kind,dimension,index_generation,expected_count,actual_count,matched_count,required_set_digest,"
        "actual_set_digest,command_input_digest,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            PROOF,
            TEAM,
            ITEM,
            REVISION,
            NEW_ARTIFACT,
            "dual_channel_projection",
            NAMESPACE,
            "model",
            "model",
            "v1",
            "local",
            2,
            2,
            1,
            1,
            1,
            "d" * 64,
            "e" * 64,
            "f" * 64,
            now,
        ),
    )
    connection.execute(
        "INSERT INTO mkb_index_active_pointers "
        "(team_uuid,intake_item_uuid,namespace_uuid,active_index_generation,pointer_row_revision,lifecycle_state,"
        "last_proof_uuid,generation_artifact_uuid,updated_at) VALUES (?,?,?,?,?,?,?,?,?)",
        (TEAM, ITEM, NAMESPACE, 2, 1, "active", PROOF, NEW_ARTIFACT, now),
    )
    connection.commit()


@pytest.fixture
async def retirement_db(tmp_path: Path) -> SqlitePersistence:
    persistence = SqlitePersistence(tmp_path / "retirement.sqlite3", Path("src/persistence/migrations"))
    await persistence.migrate()
    await _seed_retired_generation(persistence)
    yield persistence
    await persistence.close()


async def test_scanner_freezes_grace_then_soft_deletes_only_retired_generation(
    retirement_db: SqlitePersistence,
) -> None:
    clock = MutableClock(CUTOVER + timedelta(minutes=30))
    service = IndexGenerationRetirementService(retirement_db, grace=timedelta(hours=1), clock=clock)

    before_grace = await service.scan_once()
    assert before_grace.discovered_count == 1
    assert before_grace.results == ()

    connection = retirement_db._connect()
    intent = connection.execute(
        "SELECT policy_ref,target_kind,status,eligible_at FROM mkb_intake_cleanup_intents"
    ).fetchone()
    assert tuple(intent) == (
        RETIREMENT_POLICY_REF,
        "index_generation",
        "open",
        _timestamp(CUTOVER + timedelta(hours=1)),
    )
    assert connection.execute(
        "SELECT COUNT(*) FROM mkb_vector_records WHERE index_generation=1 AND deleted_at IS NULL"
    ).fetchone()[0] == 2
    # S09 serving isolation takes effect at the active-pointer cutover, not at
    # physical cleanup: the still-live old rows are already absent from the
    # read view during the rollback grace window.
    assert [row[0] for row in connection.execute("SELECT index_generation FROM mkb_v_vectors_active")] == [2]

    clock.now = CUTOVER + timedelta(hours=1)
    after_grace = await service.scan_once()
    assert after_grace.discovered_count == 0
    assert [(result.disposition, result.soft_deleted_count) for result in after_grace.results] == [
        (IndexGenerationRetirementDisposition.SOFT_PURGED, 2)
    ]
    assert connection.execute(
        "SELECT COUNT(*) FROM mkb_vector_records WHERE index_generation=1 AND deleted_at IS NULL"
    ).fetchone()[0] == 0
    assert connection.execute(
        "SELECT COUNT(*) FROM mkb_vector_records WHERE index_generation=2 AND deleted_at IS NULL"
    ).fetchone()[0] == 1
    assert [row[0] for row in connection.execute("SELECT index_generation FROM mkb_v_vectors_active")] == [2]
    assert connection.execute(
        "SELECT status,completed_at,completion_projection_ref FROM mkb_intake_cleanup_intents"
    ).fetchone()[0] == "completed"
    proof = connection.execute(
        "SELECT substrate_kind,proof_kind FROM mkb_intake_cleanup_proofs"
    ).fetchone()
    assert tuple(proof) == ("vector_projection", "index_generation_soft_delete.v1")


async def test_due_retirement_defers_when_recovery_routes_back_to_old_generation(
    retirement_db: SqlitePersistence,
) -> None:
    clock = MutableClock(CUTOVER + timedelta(hours=2))
    service = IndexGenerationRetirementService(retirement_db, grace=timedelta(hours=1), clock=clock)
    assert await service.discover_retirements() == 1

    connection = retirement_db._connect()
    connection.execute(
        "UPDATE mkb_index_active_pointers SET active_index_generation=1,pointer_row_revision=2,"
        "generation_artifact_uuid=? WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=?",
        (OLD_ARTIFACT, TEAM, ITEM, NAMESPACE),
    )
    connection.commit()

    while_recovered = await service.scan_once()
    assert [result.disposition for result in while_recovered.results] == [
        IndexGenerationRetirementDisposition.ACTIVE_GENERATION
    ]
    assert connection.execute(
        "SELECT COUNT(*) FROM mkb_vector_records WHERE index_generation=1 AND deleted_at IS NULL"
    ).fetchone()[0] == 2
    assert connection.execute("SELECT status FROM mkb_intake_cleanup_intents").fetchone()[0] == "open"

    connection.execute(
        "UPDATE mkb_index_active_pointers SET active_index_generation=2,pointer_row_revision=3,"
        "generation_artifact_uuid=? WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=?",
        (NEW_ARTIFACT, TEAM, ITEM, NAMESPACE),
    )
    connection.commit()
    resumed = await service.scan_once()
    assert [result.disposition for result in resumed.results] == [IndexGenerationRetirementDisposition.SOFT_PURGED]
    assert connection.execute(
        "SELECT COUNT(*) FROM mkb_vector_records WHERE index_generation=1 AND deleted_at IS NULL"
    ).fetchone()[0] == 0


async def test_schedule_requires_the_post_cutover_pointer_fence_and_keeps_first_deadline(
    retirement_db: SqlitePersistence,
) -> None:
    clock = MutableClock(CUTOVER)
    service = IndexGenerationRetirementService(retirement_db, grace=timedelta(hours=1), clock=clock)

    with pytest.raises(MkbError, match="INDEX_RETIREMENT_POINTER_FENCE"):
        await service.schedule_retirement(
            team_uuid=TEAM,
            intake_item_uuid=ITEM,
            namespace_uuid=NAMESPACE,
            retired_index_generation=1,
            successor_index_generation=2,
            expected_pointer_row_revision=0,
        )

    first = await service.schedule_retirement(
        team_uuid=TEAM,
        intake_item_uuid=ITEM,
        namespace_uuid=NAMESPACE,
        retired_index_generation=1,
        successor_index_generation=2,
        expected_pointer_row_revision=1,
    )
    clock.now = CUTOVER + timedelta(hours=5)
    replay = await service.schedule_retirement(
        team_uuid=TEAM,
        intake_item_uuid=ITEM,
        namespace_uuid=NAMESPACE,
        retired_index_generation=1,
        successor_index_generation=2,
        expected_pointer_row_revision=1,
        cutover_at=clock.now,
    )
    assert replay.intent_uuid == first.intent_uuid
    assert replay.eligible_at == first.eligible_at == _timestamp(CUTOVER + timedelta(hours=1))
