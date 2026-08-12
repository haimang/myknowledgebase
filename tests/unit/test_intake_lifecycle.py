"""S04 lifecycle command and frozen Task-intent target tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import pytest

from src.contracts.api.models import (
    IndexRebuildPayload,
    IntakeLifecyclePayload,
    IntakeRebuildPayload,
    IntakeUpdateMetadataPayload,
    TeamCreateRequest,
)
from src.contracts.common.errors import ConflictError, MkbError, NotFoundError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.sqlite_port import SqlitePersistence
from src.services.events import DomainEventWriter
from src.services.intake_lifecycle import IntakeLifecycleCommand, IntakeLifecycleService, IntakeTargetResolver
from src.services.registry import RegistryService
from src.services.teams import TeamService


@dataclass(frozen=True, slots=True)
class SeededIntake:
    persistence: SqlitePersistence
    team_uuid: str
    source_uuid: str
    item_uuid: str
    revision_uuid: str
    trace_uuid: str
    namespace_uuid: str


@pytest.fixture
async def seeded_intake(tmp_path: Path) -> SeededIntake:
    persistence = SqlitePersistence(tmp_path / "lifecycle.sqlite", Path("src/persistence/migrations"))
    await persistence.migrate()
    await RegistryService(persistence, Path("data/prompts")).bootstrap()
    teams = TeamService(persistence)
    team_uuid = uuid7()
    await teams.create(TeamCreateRequest(schema_version="mkb.team.v1", team_uuid=team_uuid, name="lifecycle"))
    source_uuid, item_uuid, revision_uuid, snapshot_uuid = uuid7(), uuid7(), uuid7(), uuid7()
    artifact_uuid, generation_uuid, namespace_uuid = uuid7(), uuid7(), uuid7()
    now = utc_now()
    source_descriptor_digest = stable_digest({"source_kind": "inline_payload", "external_key": "lifecycle"})
    async with persistence.transaction() as tx:
        await tx.execute(
            "INSERT INTO mkb_intake_sources "
            "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
            "source_descriptor_ref,source_descriptor_digest,created_at,updated_at,payload_extra) "
            "VALUES (?,?,'inline_payload','v1',?,'mkbobj:v1:source',?,?,?,'{}')",
            (
                team_uuid,
                source_uuid,
                stable_digest({"source": "inline_payload", "version": "v1"}),
                source_descriptor_digest,
                now,
                now,
            ),
        )
        # Use the registered definition digest rather than duplicating the
        # registry's implementation detail in this fixture.
        source_definition = await tx.fetchone(
            "SELECT definition_digest FROM mkb_source_kind_definitions "
            "WHERE source_kind='inline_payload' AND definition_version='v1'"
        )
        assert source_definition is not None
        await tx.execute(
            "UPDATE mkb_intake_sources SET source_kind_definition_digest=? WHERE team_uuid=? AND intake_source_uuid=?",
            (source_definition["definition_digest"], team_uuid, source_uuid),
        )
        await tx.execute(
            "INSERT INTO mkb_intake_snapshots "
            "(team_uuid,intake_snapshot_uuid,intake_source_uuid,observation_key,observation_fingerprint,candidate_root_digest,"
            "completeness,observed_at,accepted_at,payload_extra) VALUES (?,?,?,?,?,?, 'complete',?,?, '{}')",
            (
                team_uuid,
                snapshot_uuid,
                source_uuid,
                "lifecycle-key",
                stable_digest({"observation": 1}),
                stable_digest({"candidate": 1}),
                now,
                now,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_intake_items "
            "(team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,latest_revision_uuid,"
            "serving_revision_uuid,row_revision,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,'lifecycle-key','active',?,?,0,?,?, '{}')",
            (team_uuid, item_uuid, source_uuid, revision_uuid, revision_uuid, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_intake_revisions "
            "(team_uuid,intake_revision_uuid,intake_item_uuid,revision_ordinal,revision_fingerprint,creation_action_key,"
            "creation_action_version,source_snapshot_uuid,created_at,payload_extra) "
            "VALUES (?,?,?,1,?,'ingest','v1',?,?, '{}')",
            (team_uuid, revision_uuid, item_uuid, stable_digest({"revision": 1}), snapshot_uuid, now),
        )
        await tx.execute(
            "INSERT INTO mkb_intake_artifacts "
            "(team_uuid,intake_artifact_uuid,owner_snapshot_uuid,owner_revision_uuid,artifact_role,media_type,content_digest,"
            "size_bytes,logical_handle,created_at,payload_extra) "
            "VALUES (?,?,NULL,?,'clean_text','text/plain',?,12,'mkbobj:v1:clean',?,'{}')",
            (team_uuid, artifact_uuid, revision_uuid, stable_digest({"clean": "lifecycle"}), now),
        )
        await tx.execute(
            "INSERT INTO mkb_vector_namespaces "
            "(namespace_uuid,team_uuid,namespace_key,embedding_model,embedding_model_key,embedding_model_version,adapter_kind,"
            "dimension,index_generation,created_at,updated_at,payload_extra) "
            "VALUES (?,?,'default','qwen-vl-2b','qwen-vl-2b','v1','local_vllm',64,1,?,?, '{}')",
            (namespace_uuid, team_uuid, now, now),
        )
        await tx.execute(
            "INSERT INTO mkb_generation_artifacts "
            "(generation_artifact_uuid,team_uuid,artifact_type,intake_item_uuid,intake_revision_uuid,logical_handle,media_type,"
            "size_bytes,content_digest,validation_disposition,created_at,payload_extra) "
            "VALUES (?,?, 'dual_channel_projection',?,?, 'mkbobj:v1:generation','application/json',2,?,'full_valid',?,'{}')",
            (generation_uuid, team_uuid, item_uuid, revision_uuid, stable_digest({"generation": 1}), now),
        )
        await tx.execute(
            "INSERT INTO mkb_vector_records "
            "(vector_record_uuid,team_uuid,namespace_uuid,generation_artifact_uuid,generation_artifact_type,block_or_unit_id,"
            "channel,intake_source_uuid,intake_item_uuid,intake_revision_uuid,content_digest,embedding_model,embedding_model_key,"
            "embedding_model_version,adapter_kind,dimension,embedding,publication_state,index_generation,embedded_at,created_at,"
            "updated_at,payload_extra) "
            "VALUES (?, ?, ?, ?, 'dual_channel_projection','u0','original',?,?,?,?, 'qwen-vl-2b','qwen-vl-2b','v1',"
            "'local_vllm',64,?,'indexed',1,?,?,?,'{}')",
            (
                uuid7(),
                team_uuid,
                namespace_uuid,
                generation_uuid,
                source_uuid,
                item_uuid,
                revision_uuid,
                stable_digest({"vector": 1}),
                b"\x00" * (64 * 4),
                now,
                now,
                now,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_index_active_pointers "
            "(team_uuid,intake_item_uuid,namespace_uuid,active_index_generation,pointer_row_revision,lifecycle_state,"
            "generation_artifact_uuid,updated_at,payload_extra) VALUES (?,?,?,1,0,'active',?,?,'{}')",
            (team_uuid, item_uuid, namespace_uuid, generation_uuid, now),
        )
    yield SeededIntake(persistence, team_uuid, source_uuid, item_uuid, revision_uuid, uuid7(), namespace_uuid)
    await persistence.close()


@pytest.mark.asyncio
async def test_deactivate_is_logical_first_atomic_and_idempotent(seeded_intake: SeededIntake) -> None:
    service = IntakeLifecycleService(seeded_intake.persistence, DomainEventWriter())
    command = IntakeLifecycleCommand(
        team_uuid=seeded_intake.team_uuid,
        intake_item_uuid=seeded_intake.item_uuid,
        action="deactivate",
        trace_uuid=seeded_intake.trace_uuid,
        idempotency_key="deactivate-once",
        expected_item_revision=0,
        task_uuid=uuid7(),
        execution_uuid=uuid7(),
        process_uuid=uuid7(),
    )
    result = await service.apply(command)
    replay = await service.apply(command)

    assert result.applied is True
    assert result.before_lifecycle == "active"
    assert result.lifecycle_state == "deactivated"
    assert result.serving_revision_cleared is True
    assert replay.applied is False
    assert replay.transition_fence == result.transition_fence
    async with seeded_intake.persistence.transaction() as tx:
        item = await tx.fetchone(
            "SELECT lifecycle_state,serving_revision_uuid,row_revision FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (seeded_intake.team_uuid, seeded_intake.item_uuid),
        )
        pointer = await tx.fetchone(
            "SELECT lifecycle_state FROM mkb_index_active_pointers WHERE team_uuid=? AND intake_item_uuid=?",
            (seeded_intake.team_uuid, seeded_intake.item_uuid),
        )
        vector = await tx.fetchone(
            "SELECT publication_state FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=?",
            (seeded_intake.team_uuid, seeded_intake.item_uuid),
        )
        transitions = await tx.fetchall(
            "SELECT before_lifecycle,after_lifecycle,action_key,transition_fence FROM mkb_intake_item_transitions "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (seeded_intake.team_uuid, seeded_intake.item_uuid),
        )
        event = await tx.fetchone(
            "SELECT event_type,payload_json FROM mkb_domain_events WHERE team_uuid=? AND event_type='intake.item_transitioned'",
            (seeded_intake.team_uuid,),
        )
        outbox = await tx.fetchone(
            "SELECT kind,payload_json,status FROM mkb_outbox WHERE team_uuid=? AND kind='wake_execution'",
            (seeded_intake.team_uuid,),
        )
    assert item == {"lifecycle_state": "deactivated", "serving_revision_uuid": None, "row_revision": 1}
    assert pointer == {"lifecycle_state": "withdrawn"}
    assert vector == {"publication_state": "withdrawn"}
    assert transitions == [
        {
            "before_lifecycle": "active",
            "after_lifecycle": "deactivated",
            "action_key": "deactivate",
            "transition_fence": result.transition_fence,
        }
    ]
    assert event is not None and json.loads(event["payload_json"])["after_lifecycle"] == "deactivated"
    assert outbox is not None and outbox["kind"] == "wake_execution" and outbox["status"] == "pending"
    with pytest.raises(ConflictError, match="revision is stale"):
        await service.apply(
            IntakeLifecycleCommand(
                team_uuid=seeded_intake.team_uuid,
                intake_item_uuid=seeded_intake.item_uuid,
                action="deactivate",
                trace_uuid=seeded_intake.trace_uuid,
                idempotency_key="different-command-with-stale-cas",
                expected_item_revision=0,
            )
        )


@pytest.mark.asyncio
async def test_apply_tx_joins_the_callers_outcome_transaction(seeded_intake: SeededIntake) -> None:
    """A Process outcome callback can roll lifecycle truth back as one UoW."""

    service = IntakeLifecycleService(seeded_intake.persistence, DomainEventWriter())
    command = IntakeLifecycleCommand(
        team_uuid=seeded_intake.team_uuid,
        intake_item_uuid=seeded_intake.item_uuid,
        action="deactivate",
        trace_uuid=seeded_intake.trace_uuid,
        idempotency_key="outcome-callback-transaction",
    )

    class AbortOutcomeCommit(RuntimeError):
        pass

    with pytest.raises(AbortOutcomeCommit):
        async with seeded_intake.persistence.transaction() as tx:
            staged = await service.apply_tx(tx, command)
            assert staged.applied is True
            raise AbortOutcomeCommit()
    async with seeded_intake.persistence.transaction() as tx:
        item_after_rollback = await tx.fetchone(
            "SELECT lifecycle_state,serving_revision_uuid,row_revision FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (seeded_intake.team_uuid, seeded_intake.item_uuid),
        )
        transition_count = await tx.fetchone(
            "SELECT COUNT(*) AS count FROM mkb_intake_item_transitions WHERE team_uuid=? AND intake_item_uuid=?",
            (seeded_intake.team_uuid, seeded_intake.item_uuid),
        )
    assert item_after_rollback == {
        "lifecycle_state": "active",
        "serving_revision_uuid": seeded_intake.revision_uuid,
        "row_revision": 0,
    }
    assert transition_count == {"count": 0}

    async with seeded_intake.persistence.transaction() as tx:
        committed = await service.apply_tx(tx, command)
        assert committed.applied is True
    async with seeded_intake.persistence.transaction() as tx:
        item_after_commit = await tx.fetchone(
            "SELECT lifecycle_state,serving_revision_uuid,row_revision FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (seeded_intake.team_uuid, seeded_intake.item_uuid),
        )
    assert item_after_commit == {"lifecycle_state": "deactivated", "serving_revision_uuid": None, "row_revision": 1}


@pytest.mark.asyncio
async def test_delete_creates_one_cleanup_intent_and_never_restores_tombstone(seeded_intake: SeededIntake) -> None:
    service = IntakeLifecycleService(seeded_intake.persistence, DomainEventWriter())
    deactivate = IntakeLifecycleCommand(
        team_uuid=seeded_intake.team_uuid,
        intake_item_uuid=seeded_intake.item_uuid,
        action="deactivate",
        trace_uuid=seeded_intake.trace_uuid,
        idempotency_key="before-delete",
    )
    await service.apply(deactivate)
    delete = IntakeLifecycleCommand(
        team_uuid=seeded_intake.team_uuid,
        intake_item_uuid=seeded_intake.item_uuid,
        action="delete",
        trace_uuid=seeded_intake.trace_uuid,
        idempotency_key="delete-once",
        expected_item_revision=1,
    )
    result = await service.apply(delete)
    replay = await service.apply(delete)
    assert result.applied is True
    assert result.lifecycle_state == "deleted"
    assert result.cleanup_intent_uuid is not None
    assert replay.applied is False
    assert replay.cleanup_intent_uuid == result.cleanup_intent_uuid

    resolver = IntakeTargetResolver(seeded_intake.persistence)
    with pytest.raises(ConflictError, match="Deleted Intake"):
        await resolver.resolve_rebuild(
            seeded_intake.team_uuid,
            IntakeRebuildPayload(intake_item_uuid=seeded_intake.item_uuid),
        )
    with pytest.raises(ConflictError, match="Deleted Intake"):
        await service.apply(
            IntakeLifecycleCommand(
                team_uuid=seeded_intake.team_uuid,
                intake_item_uuid=seeded_intake.item_uuid,
                action="deactivate",
                trace_uuid=seeded_intake.trace_uuid,
                idempotency_key="illegal-after-delete",
            )
        )
    async with seeded_intake.persistence.transaction() as tx:
        cleanup = await tx.fetchall(
            "SELECT intent_uuid,target_kind,target_ref,status FROM mkb_intake_cleanup_intents WHERE team_uuid=?",
            (seeded_intake.team_uuid,),
        )
        item = await tx.fetchone(
            "SELECT lifecycle_state,serving_revision_uuid,deleted_at,row_revision FROM mkb_intake_items "
            "WHERE team_uuid=? AND intake_item_uuid=?",
            (seeded_intake.team_uuid, seeded_intake.item_uuid),
        )
    assert cleanup == [
        {
            "intent_uuid": result.cleanup_intent_uuid,
            "target_kind": "intake_item",
            "target_ref": f"intake_item:{seeded_intake.item_uuid}",
            "status": "open",
        }
    ]
    assert item is not None
    assert item["lifecycle_state"] == "deleted"
    assert item["serving_revision_uuid"] is None
    assert item["deleted_at"] is not None
    assert item["row_revision"] == 2


@pytest.mark.asyncio
async def test_target_resolver_freezes_rebuild_metadata_and_controlled_index_scope(seeded_intake: SeededIntake) -> None:
    resolver = IntakeTargetResolver(seeded_intake.persistence)
    target = await resolver.resolve_rebuild(
        seeded_intake.team_uuid,
        IntakeRebuildPayload(
            intake_item_uuid=seeded_intake.item_uuid,
            expected_intake_revision_uuid=seeded_intake.revision_uuid,
        ),
    )
    manifest = target.as_manifest()
    assert manifest["intake_revision_uuid"] == seeded_intake.revision_uuid
    assert manifest["item_revision"] == 0
    assert manifest["clean_artifact"] is not None
    assert "secret_ref" not in json.dumps(manifest)
    lifecycle_target = await resolver.resolve_lifecycle_target(
        seeded_intake.team_uuid, IntakeLifecyclePayload(intake_item_uuid=seeded_intake.item_uuid)
    )
    assert lifecycle_target.item_revision == 0

    metadata = await resolver.resolve_metadata_update(
        seeded_intake.team_uuid,
        IntakeUpdateMetadataPayload(
            intake_item_uuid=seeded_intake.item_uuid,
            expected_intake_revision_uuid=seeded_intake.revision_uuid,
            semantics={"content_length": 42},
        ),
    )
    assert metadata.target.intake_revision_uuid == seeded_intake.revision_uuid
    assert metadata.semantics[0].semantic_key == "content_length"
    assert metadata.semantics[0].value == 42
    with pytest.raises(MkbError, match="not registered"):
        await resolver.resolve_metadata_update(
            seeded_intake.team_uuid,
            IntakeUpdateMetadataPayload(
                intake_item_uuid=seeded_intake.item_uuid,
                semantics={"unregistered": "nope"},
            ),
        )
    with pytest.raises(MkbError, match="does not match"):
        await resolver.resolve_metadata_update(
            seeded_intake.team_uuid,
            IntakeUpdateMetadataPayload(
                intake_item_uuid=seeded_intake.item_uuid,
                semantics={"content_length": "forty-two"},
            ),
        )

    scope = await resolver.resolve_index_rebuild(seeded_intake.team_uuid, IndexRebuildPayload(scope="team"))
    assert scope.targets == ((seeded_intake.item_uuid, seeded_intake.revision_uuid),)
    assert scope.target_set_digest == stable_digest(
        {
            "schema_version": "mkb.index-rebuild-target-set.v1",
            "team_uuid": seeded_intake.team_uuid,
            "scope": "team",
            "targets": scope.targets,
        }
    )
    with pytest.raises(NotFoundError):
        await resolver.resolve_rebuild(uuid7(), IntakeRebuildPayload(intake_item_uuid=seeded_intake.item_uuid))

    lifecycle = IntakeLifecycleService(seeded_intake.persistence, DomainEventWriter())
    await lifecycle.apply(
        IntakeLifecycleCommand(
            team_uuid=seeded_intake.team_uuid,
            intake_item_uuid=seeded_intake.item_uuid,
            action="deactivate",
            trace_uuid=seeded_intake.trace_uuid,
            idempotency_key="exclude-from-index-scope",
        )
    )
    inactive_scope = await resolver.resolve_index_rebuild(seeded_intake.team_uuid, IndexRebuildPayload(scope="team"))
    assert inactive_scope.targets == ()
    with pytest.raises(ConflictError, match="cannot make an inactive"):
        await resolver.resolve_index_rebuild(
            seeded_intake.team_uuid,
            IndexRebuildPayload(scope="intake_item", intake_item_uuid=seeded_intake.item_uuid),
        )
