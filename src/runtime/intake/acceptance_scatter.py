"""Registered-API scatter collection acceptance and child binding."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest
from src.runtime.intake.types import (
    _digest_bytes,
)
from src.services.scatter_intake import (
    ScatterChildWorkflowBinding,
    ScatterCollectionAcceptance,
    ScatterCollectionMember,
)
from src.workflows.builtin_scatter import SCATTER_CHILD_WORKFLOW_KEY


class IntakeAcceptanceScatterMixin:
    """Registered-API scatter collection acceptance and child binding."""

    async def _prepare_scatter_collection_acceptance(
            self, command: ProcessCommand, state: Mapping[str, Any]
        ) -> ScatterCollectionAcceptance:
            """Pre-promote child inputs while keeping the acceptance UoW atomic.

            Object promotion intentionally precedes the canonical transaction.
            If a fence rejects that transaction, these bytes are harmless S13
            orphans; no Snapshot, Membership, ChangeSet, child Execution, or wake
            intent becomes visible.
            """

            members = state.get("collection_members")
            source = state.get("source")
            if not isinstance(members, list) or not isinstance(source, dict):
                raise MkbError("SCATTER_STATE_INVALID", "Collection acceptance lacks source members", 422)
            child_workflow, config_snapshot = await self._scatter_child_binding(command)
            child_change_set_digest = stable_digest(
                {
                    "schema_version": "mkb.intake-change-set.v1",
                    "intake_snapshot_uuid": state["intake_snapshot_uuid"],
                    "candidate_root_digest": state["candidate_root_digest"],
                    "members": [
                        {
                            "member_ordinal": member.get("member_ordinal") if isinstance(member, dict) else None,
                            "normalized_external_key": member.get("normalized_external_key") if isinstance(member, dict) else None,
                            "intake_item_uuid": member.get("intake_item_uuid") if isinstance(member, dict) else None,
                            "intake_revision_uuid": member.get("intake_revision_uuid") if isinstance(member, dict) else None,
                            "clean_digest": member.get("clean_digest") if isinstance(member, dict) else None,
                            "required": True,
                        }
                        for member in members
                    ],
                }
            )
            prepared_members: list[ScatterCollectionMember] = []
            for ordinal, raw_member in enumerate(members):
                if not isinstance(raw_member, dict) or raw_member.get("member_ordinal") != ordinal:
                    raise MkbError("SCATTER_MEMBER_ORDER_INVALID", "Collection member order changed before acceptance", 409)
                required_text = (
                    "external_key",
                    "normalized_external_key",
                    "raw_digest",
                    "clean_text",
                    "clean_digest",
                    "intake_item_uuid",
                    "intake_revision_uuid",
                    "clean_artifact_uuid",
                    "child_execution_uuid",
                )
                if any(not isinstance(raw_member.get(key), str) or not raw_member[key] for key in required_text):
                    raise MkbError("SCATTER_MEMBER_INVALID", "Collection member lacks immutable identifiers", 422)
                if (
                    not isinstance(raw_member.get("content_digest"), str)
                    or not isinstance(raw_member.get("meta_digest"), str)
                    or not isinstance(raw_member.get("filter_meta"), dict)
                    or not isinstance(raw_member.get("context_meta"), dict)
                    or not isinstance(raw_member.get("semantic_tuples"), list)
                ):
                    raise MkbError("SCATTER_MEMBER_INVALID", "Collection member lacks provider semantics", 422)
                clean_text = raw_member["clean_text"]
                if stable_digest({"text": clean_text}) != raw_member["clean_digest"]:
                    raise MkbError("SCATTER_MEMBER_INVALID", "Collection member clean content changed before acceptance", 409)
                clean_body = {
                    "schema_version": "mkb.scatter-clean-member.v1",
                    "intake_source_uuid": state["intake_source_uuid"],
                    "intake_snapshot_uuid": state["intake_snapshot_uuid"],
                    "member_ordinal": ordinal,
                    "normalized_external_key": raw_member["normalized_external_key"],
                    "clean_digest": raw_member["clean_digest"],
                    "clean_text": clean_text,
                    "content_digest": raw_member["content_digest"],
                    "meta_digest": raw_member["meta_digest"],
                    "filter_meta": raw_member["filter_meta"],
                    "context_meta": raw_member["context_meta"],
                    "semantic_tuples": raw_member["semantic_tuples"],
                }
                clean_artifact = await self._storage.promote(
                    canonical_json(clean_body),
                    PromoteRequest(team_uuid=command.team_uuid, purpose="intake_revision_artifact", media_type="application/json"),
                )
                child_manifest_body = {
                    "schema_version": "mkb.execution-input-manifest.v1",
                    "team_uuid": command.team_uuid,
                    "task_uuid": command.task_uuid,
                    "trace_uuid": command.trace_uuid,
                    "request_intent": "intake.ingest",
                    # This closed descriptor is contextual evidence only.  The
                    # exact usable member is the immutable scatter_member below;
                    # children never re-enumerate the collection source.
                    "payload": {
                        "source": {
                            "source_kind": "registered_api",
                            "external_key": state["external_key"],
                            "connector_key": source.get("connector_key"),
                            "provider": source.get("provider"),
                            "operation": source.get("operation"),
                            "definition_version": source.get("definition_version"),
                            "representation": "raw",
                            "records": [],
                            "exhaustion_proof": "caller_frozen_records.v1",
                        }
                    },
                    "intent_context": {
                        "schema_version": "mkb.scatter-child-context.v1",
                        "scatter_member": {
                            "intake_source_uuid": state["intake_source_uuid"],
                            "intake_snapshot_uuid": state["intake_snapshot_uuid"],
                            "change_set_uuid": state["change_set_uuid"],
                            "change_set_digest": child_change_set_digest,
                            "member_ordinal": ordinal,
                            "source_kind": "registered_api",
                            "external_key": raw_member["external_key"],
                            "normalized_external_key": raw_member["normalized_external_key"],
                            "intake_item_uuid": raw_member["intake_item_uuid"],
                            "intake_revision_uuid": raw_member["intake_revision_uuid"],
                            "clean_artifact_uuid": raw_member["clean_artifact_uuid"],
                            "clean_digest": raw_member["clean_digest"],
                            "clean_text": clean_text,
                            "provider": state.get("api_provider"),
                            "operation": state.get("api_operation"),
                            "definition_version": state.get("api_definition_version"),
                            "require_human_review": bool(raw_member.get("require_human_review", False)),
                        },
                    },
                }
                child_manifest = await self._storage.promote(
                    canonical_json(child_manifest_body),
                    PromoteRequest(team_uuid=command.team_uuid, purpose="process_io", media_type="application/json"),
                )
                prepared_members.append(
                    ScatterCollectionMember(
                        member_ordinal=ordinal,
                        external_key=raw_member["external_key"],
                        normalized_external_key=raw_member["normalized_external_key"],
                        raw_digest=raw_member["raw_digest"],
                        content_digest=raw_member["content_digest"],
                        meta_digest=raw_member["meta_digest"],
                        clean_text=clean_text,
                        clean_digest=raw_member["clean_digest"],
                        filter_meta=dict(raw_member["filter_meta"]),
                        context_meta=dict(raw_member["context_meta"]),
                        semantic_tuples=tuple(dict(item) for item in raw_member["semantic_tuples"]),
                        require_human_review=bool(raw_member.get("require_human_review", False)),
                        intake_item_uuid=raw_member["intake_item_uuid"],
                        intake_revision_uuid=raw_member["intake_revision_uuid"],
                        clean_artifact_uuid=raw_member["clean_artifact_uuid"],
                        child_execution_uuid=raw_member["child_execution_uuid"],
                        clean_artifact=clean_artifact,
                        child_manifest=child_manifest,
                    )
                )
            provisional = ScatterCollectionAcceptance(
                intake_source_uuid=state["intake_source_uuid"],
                candidate_set_uuid=state["candidate_set_uuid"],
                intake_snapshot_uuid=state["intake_snapshot_uuid"],
                change_set_uuid=state["change_set_uuid"],
                raw_artifact_uuid=state["raw_artifact_uuid"],
                source_kind="registered_api",
                observation_key=state["normalized_external_key"],
                observation_fingerprint=state["raw_digest"],
                raw_digest=state["raw_digest"],
                candidate_root_digest=state["candidate_root_digest"],
                observed_at=state["observed_at"],
                accepted_at=state["accepted_at"],
                admission_result=state["admission_result"],
                members=tuple(prepared_members),
                child_workflow=ScatterChildWorkflowBinding(
                    workflow_uuid=child_workflow["workflow_uuid"],
                    workflow_revision_uuid=child_workflow["workflow_revision_uuid"],
                    compiled_digest=child_workflow["compiled_digest"],
                    config_snapshot=config_snapshot,
                    domain_binding_digest=stable_digest(
                        {
                            "config_snapshot_digest": config_snapshot.sha256,
                            "workflow_compiled_digest": child_workflow["compiled_digest"],
                            "request_intent": "intake.ingest",
                        }
                    ),
                ),
            )
            if self._scatter_change_set_digest(provisional) != child_change_set_digest:
                raise MkbError("SCATTER_CHANGE_SET_INVALID", "Collection ChangeSet digest is not deterministic", 503)
            return provisional


    async def _scatter_child_binding(
            self, command: ProcessCommand
        ) -> tuple[dict[str, Any], ObjectStat]:
            """Resolve the internal child graph and root's frozen L4 object."""

            async with self._persistence.transaction() as tx:
                child = await tx.fetchone(
                    "SELECT r.workflow_uuid,r.active_revision_uuid AS workflow_revision_uuid,v.compiled_digest "
                    "FROM mkb_workflow_registry r JOIN mkb_workflow_revisions v "
                    "ON v.workflow_revision_uuid=r.active_revision_uuid "
                    "WHERE r.workflow_key=? AND r.execution_role='scatter_child' AND r.registry_status='enabled'",
                    (SCATTER_CHILD_WORKFLOW_KEY,),
                )
                root = await tx.fetchone(
                    "SELECT config_snapshot_ref,config_snapshot_digest FROM mkb_executions "
                    "WHERE execution_uuid=? AND team_uuid=?",
                    (command.execution_uuid, command.team_uuid),
                )
            if child is None or root is None:
                raise MkbError("SCATTER_CHILD_WORKFLOW_INVALID", "Registered scatter child workflow is unavailable", 503)
            config_ref = root.get("config_snapshot_ref")
            config_digest = root.get("config_snapshot_digest")
            if not isinstance(config_ref, str) or not isinstance(config_digest, str):
                raise MkbError("SCATTER_CHILD_CONFIG_MISSING", "Scatter root lacks a frozen configuration", 503)
            data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=config_ref))
            if _digest_bytes(data) != config_digest:
                raise MkbError("SCATTER_CHILD_CONFIG_INVALID", "Scatter root configuration failed its digest fence", 503)
            return child, ObjectStat(
                handle=ObjectHandle(value=config_ref),
                sha256=config_digest,
                size_bytes=len(data),
                media_type="application/json",
            )


    @staticmethod
    def _scatter_change_set_digest(acceptance: ScatterCollectionAcceptance) -> str:
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
