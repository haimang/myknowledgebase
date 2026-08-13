"""Atomic S04 acceptance writer for registered-API collection intake.

This module owns the collection linearization point only.  It does not route
Processes or decide fan-in; it receives a sealed, preflight-admitted member
set and writes the immutable Snapshot/Membership/ChangeSet truth together
with the initial child Execution intents in one transaction.
"""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import ObjectStat
from src.persistence.ports import UnitOfWork


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True, slots=True)
class ScatterChildWorkflowBinding:
    """Frozen child workflow/L4 coordinates selected before acceptance."""

    workflow_uuid: str
    workflow_revision_uuid: str
    compiled_digest: str
    config_snapshot: ObjectStat
    domain_binding_digest: str


@dataclass(frozen=True, slots=True)
class ScatterCollectionMember:
    """One accepted, required collection member and its pre-promoted bytes."""

    member_ordinal: int
    external_key: str
    normalized_external_key: str
    raw_digest: str
    content_digest: str
    meta_digest: str
    clean_text: str
    clean_digest: str
    filter_meta: dict[str, Any]
    context_meta: dict[str, Any]
    semantic_tuples: tuple[dict[str, Any], ...]
    require_human_review: bool
    intake_item_uuid: str
    intake_revision_uuid: str
    clean_artifact_uuid: str
    child_execution_uuid: str
    clean_artifact: ObjectStat
    child_manifest: ObjectStat


@dataclass(frozen=True, slots=True)
class ScatterCollectionAcceptance:
    """The complete sealed collection facts needed by the one acceptance UoW."""

    intake_source_uuid: str
    candidate_set_uuid: str
    intake_snapshot_uuid: str
    change_set_uuid: str
    raw_artifact_uuid: str
    source_kind: str
    observation_key: str
    observation_fingerprint: str
    raw_digest: str
    candidate_root_digest: str
    observed_at: str
    accepted_at: str
    admission_result: str
    members: tuple[ScatterCollectionMember, ...]
    child_workflow: ScatterChildWorkflowBinding


InitialSemantics = Callable[[UnitOfWork, Mapping[str, Any]], Awaitable[list[dict[str, Any]]]]
SemanticFingerprint = Callable[[list[dict[str, Any]]], str]
InsertSemantic = Callable[[UnitOfWork, str, str, Mapping[str, Any], str], Awaitable[None]]


class ScatterAcceptanceWriter:
    """Write collection truth and durable child wakes without a split window."""

    async def commit(
        self,
        tx: UnitOfWork,
        *,
        command: ProcessCommand,
        acceptance: ScatterCollectionAcceptance,
        stage_output_ref: str,
        stage_output_digest: str,
        stage_output_size: int,
        stage_proof_ref: str,
        stage_proof_digest: str,
        initial_semantics: InitialSemantics,
        semantic_fingerprint: SemanticFingerprint,
        insert_semantic: InsertSemantic,
    ) -> None:
        """Commit the accepted set and every required child intent atomically."""

        if acceptance.admission_result not in {"auto_admitted", "human_review_required"}:
            raise MkbError("PREFLIGHT_REJECTED", "Preflight did not admit this collection", 409)
        if any(member.member_ordinal != ordinal for ordinal, member in enumerate(acceptance.members)):
            raise MkbError("SCATTER_MEMBER_ORDER_INVALID", "Collection member ordinals must be stable and contiguous", 422)
        if len({member.normalized_external_key for member in acceptance.members}) != len(acceptance.members):
            raise MkbError("SCATTER_MEMBER_KEY_DUPLICATE", "Collection member external keys are not unique", 422)

        now = acceptance.accepted_at
        output_object_uuid = await self._require_catalogued_object(
            tx, command.team_uuid, stage_output_digest, stage_output_size
        )
        candidate = await tx.fetchone(
            "SELECT staging_state,preflight_outcome_ref,preflight_outcome_digest FROM mkb_intake_candidate_sets "
            "WHERE candidate_set_uuid=? AND team_uuid=?",
            (acceptance.candidate_set_uuid, command.team_uuid),
        )
        if (
            candidate is None
            or candidate["staging_state"] != "sealed"
            or candidate["preflight_outcome_ref"] != command.input_manifest_ref
            or candidate["preflight_outcome_digest"] != command.input_manifest_digest
        ):
            raise MkbError("CANDIDATE_SET_FENCE", "Candidate set changed before collection acceptance", 409)
        action = await tx.fetchone(
            "SELECT action_key,definition_version FROM mkb_intake_action_definitions "
            "WHERE action_key='accept_revision' AND definition_version='v1'"
        )
        if action is None:
            raise MkbError("REGISTRY_NOT_FOUND", "Intake acceptance action is unavailable", 503)
        root = await tx.fetchone(
            "SELECT execution_uuid,generation,trace_uuid,intake_snapshot_uuid,status,config_snapshot_ref,config_snapshot_digest "
            "FROM mkb_executions WHERE execution_uuid=? AND team_uuid=?",
            (command.execution_uuid, command.team_uuid),
        )
        if root is None or root["status"] in {"failed", "cancelled", "cancelling", "succeeded"}:
            raise MkbError("SCATTER_ROOT_FENCE", "Scatter root is not available for acceptance", 409)
        if root["intake_snapshot_uuid"] is not None:
            raise MkbError("INTAKE_SNAPSHOT_EXECUTION_FENCE", "Root already has an accepted Snapshot", 409)
        if root["config_snapshot_ref"] is None or root["config_snapshot_digest"] is None:
            raise MkbError("SCATTER_CHILD_CONFIG_MISSING", "Scatter root lacks a frozen configuration", 503)
        await self._assert_child_workflow(tx, acceptance.child_workflow)

        change_set_digest = self._change_set_digest(acceptance)
        snapshot_digest = stable_digest(
            {
                "intake_snapshot_uuid": acceptance.intake_snapshot_uuid,
                "candidate_root_digest": acceptance.candidate_root_digest,
                "change_set_digest": change_set_digest,
            }
        )
        await tx.execute(
            "INSERT INTO mkb_intake_snapshots "
            "(team_uuid,intake_snapshot_uuid,intake_source_uuid,observation_key,observation_fingerprint,candidate_root_digest,"
            "completeness,preflight_outcome_ref,preflight_outcome_digest,s05_binding_digest,observed_at,accepted_at,"
            "producer_execution_uuid,raw_artifact_uuid,payload_extra) VALUES (?,?,?,?,?,?, 'complete',?,?,?,?,?,?,?,'{}')",
            (
                command.team_uuid,
                acceptance.intake_snapshot_uuid,
                acceptance.intake_source_uuid,
                acceptance.observation_key,
                acceptance.observation_fingerprint,
                acceptance.candidate_root_digest,
                command.input_manifest_ref,
                command.input_manifest_digest,
                command.binding_digest,
                acceptance.observed_at,
                now,
                command.execution_uuid,
                acceptance.raw_artifact_uuid,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_intake_artifacts "
            "(team_uuid,intake_artifact_uuid,owner_snapshot_uuid,owner_revision_uuid,artifact_role,media_type,"
            "content_digest,size_bytes,logical_handle,stored_object_uuid,producer_execution_uuid,producer_process_uuid,"
            "created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
            (
                command.team_uuid,
                acceptance.raw_artifact_uuid,
                acceptance.intake_snapshot_uuid,
                None,
                "raw_acquisition",
                "application/json",
                acceptance.raw_digest,
                stage_output_size,
                stage_output_ref,
                output_object_uuid,
                command.execution_uuid,
                command.process_uuid,
                now,
            ),
        )
        await self._reference_object(
            tx,
            team_uuid=command.team_uuid,
            stored_object_uuid=output_object_uuid,
            purpose="intake_snapshot_artifact",
            owner_kind="intake_snapshot",
            owner_uuid=acceptance.intake_snapshot_uuid,
            digest=stage_output_digest,
            size=stage_output_size,
        )

        for member in acceptance.members:
            await self._insert_member(
                tx,
                command=command,
                acceptance=acceptance,
                member=member,
                action=action,
                now=now,
                stage_proof_ref=stage_proof_ref,
                stage_proof_digest=stage_proof_digest,
                initial_semantics=initial_semantics,
                semantic_fingerprint=semantic_fingerprint,
                insert_semantic=insert_semantic,
            )

        await tx.execute(
            "INSERT INTO mkb_intake_change_sets "
            "(change_set_uuid,team_uuid,intake_snapshot_uuid,change_set_digest,created_at,payload_extra) "
            "VALUES (?,?,?,?,?,'{}')",
            (
                acceptance.change_set_uuid,
                command.team_uuid,
                acceptance.intake_snapshot_uuid,
                change_set_digest,
                now,
            ),
        )
        for member in acceptance.members:
            fact = {
                "kind": "accept_revision",
                "member_ordinal": member.member_ordinal,
                "intake_item_uuid": member.intake_item_uuid,
                "intake_revision_uuid": member.intake_revision_uuid,
                "clean_digest": member.clean_digest,
                "required": True,
            }
            await tx.execute(
                "INSERT INTO mkb_intake_change_set_facts "
                "(fact_uuid,change_set_uuid,team_uuid,fact_kind,fact_ordinal,intake_item_uuid,intake_revision_uuid,"
                "semantic_key,semantic_definition_version,absence_key,fact_digest,created_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,?,?,'{}')",
                (
                    uuid7(),
                    acceptance.change_set_uuid,
                    command.team_uuid,
                    "accept_revision",
                    member.member_ordinal,
                    member.intake_item_uuid,
                    member.intake_revision_uuid,
                    stable_digest(fact),
                    now,
                ),
            )

        accepted = await tx.execute(
            "UPDATE mkb_intake_candidate_sets SET staging_state='accepted',accepted_member_count=?,"
            "accepted_snapshot_uuid=?,row_revision=row_revision+1,updated_at=? "
            "WHERE candidate_set_uuid=? AND team_uuid=? AND staging_state='sealed'",
            (
                len(acceptance.members),
                acceptance.intake_snapshot_uuid,
                now,
                acceptance.candidate_set_uuid,
                command.team_uuid,
            ),
        )
        if accepted.rowcount != 1:
            raise MkbError("CANDIDATE_SET_FENCE", "Candidate set changed before collection acceptance", 409)
        root_payload = _json(
            {
                "schema_version": "mkb.scatter-root-binding.v1",
                "intake_source_uuid": acceptance.intake_source_uuid,
                "intake_snapshot_uuid": acceptance.intake_snapshot_uuid,
                "intake_snapshot_digest": snapshot_digest,
                "change_set_uuid": acceptance.change_set_uuid,
                "change_set_digest": change_set_digest,
                "required_member_count": len(acceptance.members),
            }
        )
        execution_updated = await tx.execute(
            "UPDATE mkb_executions SET target_kind='intake_source',target_uuid=?,intake_snapshot_uuid=?,"
            "intake_snapshot_digest=?,manifest_revision=manifest_revision+1,total_child_count=?,active_child_count=?,"
            "succeeded_child_count=0,failed_child_count=0,payload_extra=?,row_revision=row_revision+1,updated_at=? "
            "WHERE execution_uuid=? AND team_uuid=? "
            "AND intake_snapshot_uuid IS NULL",
            (
                acceptance.intake_source_uuid,
                acceptance.intake_snapshot_uuid,
                snapshot_digest,
                len(acceptance.members),
                len(acceptance.members),
                root_payload,
                now,
                command.execution_uuid,
                command.team_uuid,
            ),
        )
        if execution_updated.rowcount != 1:
            raise MkbError("INTAKE_SNAPSHOT_EXECUTION_FENCE", "Root Snapshot coordinate changed before acceptance", 409)
        task_updated = await tx.execute(
            "UPDATE mkb_tasks SET intake_snapshot_uuid=?,change_set_uuid=?,cnt_total=?,cnt_required=?,cnt_active=?,"
            "cnt_succeeded=0,cnt_failed=0,cnt_cancelled=0,cnt_skipped=0,row_revision=row_revision+1,updated_at=? "
            "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=? "
            "AND intake_snapshot_uuid IS NULL AND change_set_uuid IS NULL",
            (
                acceptance.intake_snapshot_uuid,
                acceptance.change_set_uuid,
                len(acceptance.members),
                len(acceptance.members),
                len(acceptance.members),
                now,
                command.team_uuid,
                command.task_uuid,
                command.execution_uuid,
            ),
        )
        if task_updated.rowcount != 1:
            raise MkbError("INTAKE_SNAPSHOT_TASK_FENCE", "Task Snapshot coordinate changed before acceptance", 409)

        # Root manifest_revision is advanced above as the durable fan-out
        # epoch.  Its value is now fixed at 1 for the first accepted set and
        # gives the physical child uniqueness index a stable collection fence.
        root_manifest = await tx.fetchone(
            "SELECT manifest_revision FROM mkb_executions WHERE execution_uuid=?", (command.execution_uuid,)
        )
        if root_manifest is None:
            raise MkbError("SCATTER_ROOT_FENCE", "Scatter root disappeared during acceptance", 409)
        for member in acceptance.members:
            await self._insert_child_execution(
                tx,
                command=command,
                root=root,
                root_manifest_revision=int(root_manifest["manifest_revision"]),
                acceptance=acceptance,
                change_set_digest=change_set_digest,
                snapshot_digest=snapshot_digest,
                member=member,
                now=now,
                activate_now=acceptance.admission_result == "auto_admitted",
            )

    @staticmethod
    def _change_set_digest(acceptance: ScatterCollectionAcceptance) -> str:
        return stable_digest(
            {
                "schema_version": "mkb.intake-change-set.v1",
                "intake_snapshot_uuid": acceptance.intake_snapshot_uuid,
                "candidate_root_digest": acceptance.candidate_root_digest,
                "members": [
                    {
                        "member_ordinal": member.member_ordinal,
                        "normalized_external_key": member.normalized_external_key,
                        "intake_item_uuid": member.intake_item_uuid,
                        "intake_revision_uuid": member.intake_revision_uuid,
                        "clean_digest": member.clean_digest,
                        "required": True,
                    }
                    for member in acceptance.members
                ],
            }
        )

    async def _insert_member(
        self,
        tx: UnitOfWork,
        *,
        command: ProcessCommand,
        acceptance: ScatterCollectionAcceptance,
        member: ScatterCollectionMember,
        action: Mapping[str, Any],
        now: str,
        stage_proof_ref: str,
        stage_proof_digest: str,
        initial_semantics: InitialSemantics,
        semantic_fingerprint: SemanticFingerprint,
        insert_semantic: InsertSemantic,
    ) -> None:
        await tx.execute(
            "INSERT INTO mkb_intake_items "
            "(team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,latest_revision_uuid,"
            "serving_revision_uuid,row_revision,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?, 'active',?,NULL,0,?,?,'{}')",
            (
                command.team_uuid,
                member.intake_item_uuid,
                acceptance.intake_source_uuid,
                member.normalized_external_key,
                member.intake_revision_uuid,
                now,
                now,
            ),
        )
        semantic_state = {
            "source_kind": acceptance.source_kind,
            "clean_digest": member.clean_digest,
            "content_digest": member.content_digest,
            "meta_digest": member.meta_digest,
            "filter_meta": member.filter_meta,
            "context_meta": member.context_meta,
            "semantic_tuples": list(member.semantic_tuples),
        }
        semantics = await initial_semantics(tx, semantic_state)
        fingerprint = semantic_fingerprint(semantics)
        await tx.execute(
            "INSERT INTO mkb_intake_revisions "
            "(team_uuid,intake_revision_uuid,intake_item_uuid,revision_ordinal,revision_fingerprint,creation_action_key,"
            "creation_action_version,source_snapshot_uuid,created_at,payload_extra) VALUES (?,?,?,1,?,?,?,?,?,'{}')",
            (
                command.team_uuid,
                member.intake_revision_uuid,
                member.intake_item_uuid,
                fingerprint,
                action["action_key"],
                action["definition_version"],
                acceptance.intake_snapshot_uuid,
                now,
            ),
        )
        for entry in semantics:
            await insert_semantic(tx, command.team_uuid, member.intake_revision_uuid, entry, now)
        clean_object_uuid = await self._catalog_stat(tx, command.team_uuid, member.clean_artifact)
        await tx.execute(
            "INSERT INTO mkb_intake_artifacts "
            "(team_uuid,intake_artifact_uuid,owner_snapshot_uuid,owner_revision_uuid,artifact_role,media_type,"
            "content_digest,size_bytes,logical_handle,stored_object_uuid,producer_execution_uuid,producer_process_uuid,"
            "created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
            (
                command.team_uuid,
                member.clean_artifact_uuid,
                None,
                member.intake_revision_uuid,
                "clean_text",
                member.clean_artifact.media_type or "application/json",
                member.clean_digest,
                member.clean_artifact.size_bytes,
                member.clean_artifact.handle.value,
                clean_object_uuid,
                command.execution_uuid,
                command.process_uuid,
                now,
            ),
        )
        await self._reference_object(
            tx,
            team_uuid=command.team_uuid,
            stored_object_uuid=clean_object_uuid,
            purpose="intake_revision_artifact",
            owner_kind="intake_revision",
            owner_uuid=member.intake_revision_uuid,
            digest=member.clean_artifact.sha256,
            size=member.clean_artifact.size_bytes,
        )
        decision = {
            "admission": acceptance.admission_result,
            "member_ordinal": member.member_ordinal,
            "intake_revision_uuid": member.intake_revision_uuid,
            "clean_digest": member.clean_digest,
        }
        await tx.execute(
            "INSERT INTO mkb_intake_snapshot_memberships "
            "(team_uuid,intake_snapshot_uuid,member_ordinal,normalized_external_key,intake_item_uuid,observed_revision_uuid,"
            "decision_kind,required,decision_digest,created_at,payload_extra) VALUES (?,?,?, ?,?,?,'accepted',1,?,?,'{}')",
            (
                command.team_uuid,
                acceptance.intake_snapshot_uuid,
                member.member_ordinal,
                member.normalized_external_key,
                member.intake_item_uuid,
                member.intake_revision_uuid,
                stable_digest(decision),
                now,
            ),
        )
        await tx.execute(
            "INSERT INTO mkb_intake_item_transitions "
            "(transition_uuid,team_uuid,intake_item_uuid,action_key,action_version,before_lifecycle,after_lifecycle,"
            "before_latest_revision_uuid,after_latest_revision_uuid,before_serving_revision_uuid,after_serving_revision_uuid,"
            "item_revision_before,item_revision_after,causation_task_uuid,causation_execution_uuid,causation_process_uuid,"
            "proof_ref,proof_digest,transition_fence,occurred_at,payload_extra) "
            "VALUES (?,?,?,'accept_revision','v1','active','active',NULL,?,NULL,NULL,0,0,?,?,?,?,?,?,?,'{}')",
            (
                uuid7(),
                command.team_uuid,
                member.intake_item_uuid,
                member.intake_revision_uuid,
                command.task_uuid,
                command.execution_uuid,
                command.process_uuid,
                stage_proof_ref,
                stage_proof_digest,
                stable_digest(
                    {"process": command.process_uuid, "fence": command.fencing_generation, "member": member.member_ordinal}
                ),
                now,
            ),
        )

    async def _insert_child_execution(
        self,
        tx: UnitOfWork,
        *,
        command: ProcessCommand,
        root: Mapping[str, Any],
        root_manifest_revision: int,
        acceptance: ScatterCollectionAcceptance,
        change_set_digest: str,
        snapshot_digest: str,
        member: ScatterCollectionMember,
        now: str,
        activate_now: bool,
    ) -> None:
        config_object_uuid = await self._catalog_stat(tx, command.team_uuid, acceptance.child_workflow.config_snapshot)
        manifest_object_uuid = await self._catalog_stat(tx, command.team_uuid, member.child_manifest)
        await self._reference_object(
            tx,
            team_uuid=command.team_uuid,
            stored_object_uuid=config_object_uuid,
            purpose="process_io",
            owner_kind="execution_config_snapshot",
            owner_uuid=member.child_execution_uuid,
            digest=acceptance.child_workflow.config_snapshot.sha256,
            size=acceptance.child_workflow.config_snapshot.size_bytes,
        )
        await self._reference_object(
            tx,
            team_uuid=command.team_uuid,
            stored_object_uuid=manifest_object_uuid,
            purpose="process_io",
            owner_kind="execution_input_manifest",
            owner_uuid=member.child_execution_uuid,
            digest=member.child_manifest.sha256,
            size=member.child_manifest.size_bytes,
        )
        resolver_decision_digest = stable_digest(
            {
                "schema_version": "mkb.scatter-child-resolution.v1",
                "root_execution_uuid": command.execution_uuid,
                "change_set_uuid": acceptance.change_set_uuid,
                "change_set_digest": change_set_digest,
                "intake_snapshot_uuid": acceptance.intake_snapshot_uuid,
                "member_ordinal": member.member_ordinal,
                "intake_item_uuid": member.intake_item_uuid,
                "intake_revision_uuid": member.intake_revision_uuid,
            }
        )
        payload_extra = _json(
            {
                "schema_version": "mkb.scatter-child-binding.v1",
                "change_set_uuid": acceptance.change_set_uuid,
                "change_set_digest": change_set_digest,
                "member_ordinal": member.member_ordinal,
                "intake_revision_uuid": member.intake_revision_uuid,
            }
        )
        # A human-review admission deliberately persists the complete child
        # intent set *before* the reviewer acts, but it must not make any
        # child runnable.  ``durable_prerequisite`` is released only by the
        # root's declared scatter join after an approved Gate route.  This is
        # stronger than withholding an outbox row: a replay or a direct wake
        # cannot materialize work while the durable execution state is still
        # waiting.
        child_status = "ready" if activate_now else "waiting"
        child_phase = None if activate_now else "fan_out"
        waiting_reason = None if activate_now else "durable_prerequisite"
        waiting_ref = None if activate_now else acceptance.change_set_uuid
        await tx.execute(
            "INSERT INTO mkb_executions "
            "(execution_uuid,team_uuid,task_uuid,trace_uuid,generation,root_execution_uuid,parent_execution_uuid,"
            "retry_of_execution_uuid,execution_role,requiredness,target_kind,target_uuid,intake_snapshot_uuid,"
            "intake_snapshot_digest,workflow_uuid,workflow_revision_uuid,compiled_digest,resolver_decision_digest,"
            "domain_binding_digest,s05_binding_digest,config_snapshot_ref,config_snapshot_digest,status,phase_key,"
            "waiting_reason,waiting_ref,row_revision,"
            "manifest_ref,manifest_digest,manifest_revision,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,?,NULL,'scatter_child','required','intake_item',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,0,?,?,?,?,?,?)",
            (
                member.child_execution_uuid,
                command.team_uuid,
                command.task_uuid,
                root["trace_uuid"],
                root["generation"],
                command.execution_uuid,
                command.execution_uuid,
                member.intake_item_uuid,
                acceptance.intake_snapshot_uuid,
                snapshot_digest,
                acceptance.child_workflow.workflow_uuid,
                acceptance.child_workflow.workflow_revision_uuid,
                acceptance.child_workflow.compiled_digest,
                resolver_decision_digest,
                acceptance.child_workflow.domain_binding_digest,
                command.binding_digest,
                acceptance.child_workflow.config_snapshot.handle.value,
                acceptance.child_workflow.config_snapshot.sha256,
                child_status,
                child_phase,
                waiting_reason,
                waiting_ref,
                member.child_manifest.handle.value,
                member.child_manifest.sha256,
                root_manifest_revision,
                now,
                now,
                payload_extra,
            ),
        )
        if not activate_now:
            return
        await tx.execute(
            "INSERT OR IGNORE INTO mkb_outbox "
            "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
            "VALUES (?,?,?,?,?,?,'pending',?,?,?,'{}')",
            (
                uuid7(),
                command.team_uuid,
                "wake_execution",
                _json(
                    {
                        "execution_uuid": member.child_execution_uuid,
                        "task_uuid": command.task_uuid,
                        "generation": root["generation"],
                    }
                ),
                stable_digest(
                    {
                        "execution_uuid": member.child_execution_uuid,
                        "task_uuid": command.task_uuid,
                        "generation": root["generation"],
                    }
                ),
                f"wake-execution:{member.child_execution_uuid}",
                now,
                now,
                now,
            ),
        )

    @staticmethod
    async def _assert_child_workflow(tx: UnitOfWork, binding: ScatterChildWorkflowBinding) -> None:
        row = await tx.fetchone(
            "SELECT r.workflow_uuid,r.workflow_revision_uuid,r.compiled_digest,w.workflow_key,w.execution_role "
            "FROM mkb_workflow_revisions r JOIN mkb_workflow_registry w ON w.workflow_uuid=r.workflow_uuid "
            "WHERE r.workflow_revision_uuid=?",
            (binding.workflow_revision_uuid,),
        )
        if (
            row is None
            or row["workflow_uuid"] != binding.workflow_uuid
            or row["compiled_digest"] != binding.compiled_digest
            or row["execution_role"] != "scatter_child"
        ):
            raise MkbError("SCATTER_CHILD_WORKFLOW_INVALID", "Frozen child workflow is unavailable", 503)

    @staticmethod
    async def _require_catalogued_object(tx: UnitOfWork, team_uuid: str, digest: str, size: int) -> str:
        row = await tx.fetchone(
            "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=? AND size_bytes=? "
            "AND tombstoned_at IS NULL",
            (team_uuid, digest, size),
        )
        if row is None:
            raise MkbError("OBJECT_CATALOGUE_MISSING", "Required immutable object was not catalogued", 503)
        return str(row["stored_object_uuid"])

    @staticmethod
    async def _catalog_stat(tx: UnitOfWork, team_uuid: str, stat: ObjectStat) -> str:
        existing = await tx.fetchone(
            "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=? AND size_bytes=?",
            (team_uuid, stat.sha256, stat.size_bytes),
        )
        if existing is not None:
            return str(existing["stored_object_uuid"])
        stored_object_uuid = uuid7()
        await tx.execute(
            "INSERT INTO mkb_stored_objects "
            "(stored_object_uuid,team_uuid,digest_algorithm,content_digest,size_bytes,media_type,storage_backend,created_at,payload_extra) "
            "VALUES (?,?, 'sha256',?,?,?,?,?,'{}')",
            (
                stored_object_uuid,
                team_uuid,
                stat.sha256,
                stat.size_bytes,
                stat.media_type,
                "local_fs",
                utc_now(),
            ),
        )
        return stored_object_uuid

    @staticmethod
    async def _reference_object(
        tx: UnitOfWork,
        *,
        team_uuid: str,
        stored_object_uuid: str,
        purpose: str,
        owner_kind: str,
        owner_uuid: str,
        digest: str,
        size: int,
    ) -> None:
        existing = await tx.fetchone(
            "SELECT reference_uuid FROM mkb_object_references WHERE team_uuid=? AND stored_object_uuid=? "
            "AND purpose=? AND owner_kind=? AND owner_uuid=? AND released_at IS NULL",
            (team_uuid, stored_object_uuid, purpose, owner_kind, owner_uuid),
        )
        if existing is not None:
            return
        await tx.execute(
            "INSERT INTO mkb_object_references "
            "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
            "created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,'{}')",
            (uuid7(), team_uuid, stored_object_uuid, purpose, owner_kind, owner_uuid, digest, size, utc_now()),
        )


__all__ = [
    "ScatterAcceptanceWriter",
    "ScatterChildWorkflowBinding",
    "ScatterCollectionAcceptance",
    "ScatterCollectionMember",
]
