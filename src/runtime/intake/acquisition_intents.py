"""Rebuild/metadata/lifecycle acquisition and frozen source freeze."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _METADATA_REFRESH_REUSE_SUMMARIES,
    _METADATA_REFRESH_SOURCE_TYPES,
    _digest_bytes,
    _StageMaterial,
)
from src.services.intake_lifecycle import IntakeLifecycleCommand


class IntakeAcquisitionIntentsMixin:
    """Rebuild/metadata/lifecycle acquisition and frozen source freeze."""

    async def _acquire_rebuild(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            target = self._frozen_target(state)
            clean_text = await self._read_frozen_clean_text(command, target)
            now = utc_now()
            clean = target["clean_artifact"]
            assert isinstance(clean, dict)
            # A rebuild deliberately begins with the immutable clean Artifact of
            # the frozen accepted Revision.  It is not a second acquisition of
            # the external source, so do not forge an S05 source-acquisition
            # record for it.  Preserve a closed provenance object instead; the
            # dedicated preflight branch below verifies every coordinate before
            # this replay can enter the derived-generation path.
            clean_bytes = clean_text.encode("utf-8")
            rebuild_input_evidence = {
                "schema_version": "mkb.rebuild-clean-input-evidence.v1",
                "input_kind": "accepted_clean_artifact",
                "team_uuid": command.team_uuid,
                "intake_source_uuid": target["intake_source_uuid"],
                "intake_item_uuid": target["intake_item_uuid"],
                "intake_revision_uuid": target["intake_revision_uuid"],
                "source_snapshot_uuid": target["source_snapshot_uuid"],
                "source_kind": target["source_kind"],
                "normalized_external_key": target["normalized_external_key"],
                "clean_artifact_uuid": clean["intake_artifact_uuid"],
                "clean_content_digest": clean["content_digest"],
                "clean_handle_digest": stable_digest({"handle": clean["logical_handle"]}),
                "clean_text_digest": stable_digest({"text": clean_text}),
            }
            next_state = {
                "request_intent": "intake.rebuild",
                "operation_mode": "rebuild",
                "frozen_target": target,
                "team_uuid": command.team_uuid,
                "task_uuid": command.task_uuid,
                "trace_uuid": command.trace_uuid,
                "source_kind": target["source_kind"],
                "external_key": target["normalized_external_key"],
                "normalized_external_key": target["normalized_external_key"],
                "raw_text": clean_text,
                "raw_digest": stable_digest({"media_type": "text/plain", "text": clean_text}),
                "raw_byte_digest": _digest_bytes(clean_bytes),
                "raw_byte_size": len(clean_bytes),
                "raw_binary_transport": False,
                "media_type": "text/plain",
                "decoded_text": clean_text,
                "decoded_digest": stable_digest({"text": clean_text, "media_type": "text/plain"}),
                "clean_text": clean_text,
                "clean_digest": clean["content_digest"],
                "rebuild_input_evidence": rebuild_input_evidence,
                "rebuild_input_kind": "accepted_clean_artifact",
                "require_human_review": False,
                "intake_source_uuid": target["intake_source_uuid"],
                "candidate_set_uuid": uuid7(),
                "intake_snapshot_uuid": target["source_snapshot_uuid"],
                "intake_item_uuid": target["intake_item_uuid"],
                "intake_revision_uuid": target["intake_revision_uuid"],
                "clean_artifact_uuid": clean["intake_artifact_uuid"],
                "observed_at": now,
            }
            material = self._material(
                command,
                next_state,
                {
                    "acquisition_evidence": {
                        "mode": "rebuild_from_accepted_clean_artifact",
                        "rebuild_input": rebuild_input_evidence,
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                del refs
                item = await tx.fetchone(
                    "SELECT row_revision,lifecycle_state,latest_revision_uuid,serving_revision_uuid FROM mkb_intake_items "
                    "WHERE team_uuid=? AND intake_item_uuid=?",
                    (command.team_uuid, target["intake_item_uuid"]),
                )
                if (
                    item is None
                    or item["row_revision"] != target["item_revision"]
                    or item["lifecycle_state"] != "active"
                    or item["latest_revision_uuid"] != target["intake_revision_uuid"]
                ):
                    raise MkbError("REBUILD_TARGET_STALE", "Frozen Intake rebuild target changed before execution", 409)

            return material, {}, callback


    async def _acquire_metadata_update(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            context = state.get("intent_context")
            if not isinstance(context, dict) or not isinstance(context.get("target"), dict):
                raise MkbError("METADATA_TARGET_INVALID", "Frozen metadata target is unavailable", 422)
            semantics = context.get("semantics")
            base_semantics = context.get("base_semantics")
            if not isinstance(semantics, list) or not semantics or not isinstance(base_semantics, list):
                raise MkbError("METADATA_SEMANTICS_EMPTY", "Frozen metadata semantic values are unavailable", 422)
            target = context["target"]
            if not isinstance(target, dict):
                raise MkbError("METADATA_TARGET_INVALID", "Frozen metadata target is unavailable", 422)
            # Resolve the actual immutable semantic delta before choosing the
            # static graph mode.  A no-change command must never fabricate a
            # candidate or re-run LS-RAG purely because its Task was admitted.
            _merged, fingerprint = await self._merged_metadata_semantics(
                command.team_uuid,
                target.get("intake_revision_uuid"),
                semantics,
                base_semantics,
            )
            if fingerprint == target.get("revision_fingerprint"):
                now = utc_now()
                next_state = {
                    "request_intent": "intake.update_metadata",
                    "operation_mode": "metadata_no_change",
                    "metadata_no_change": True,
                    "frozen_target": target,
                    "metadata_base_semantics": base_semantics,
                    "metadata_semantics": semantics,
                    "intake_item_uuid": target["intake_item_uuid"],
                    "intake_revision_uuid": target["intake_revision_uuid"],
                    "intake_snapshot_uuid": target["source_snapshot_uuid"],
                    "team_uuid": command.team_uuid,
                    "task_uuid": command.task_uuid,
                    "trace_uuid": command.trace_uuid,
                    "admission_result": "auto_admitted",
                    "accepted_at": now,
                }
                material = self._material(
                    command,
                    next_state,
                    {
                        "metadata_admission": {
                            "intake_item_uuid": target["intake_item_uuid"],
                            "predecessor_revision_uuid": target["intake_revision_uuid"],
                            "semantic_count": len(semantics),
                            "disposition": "no_change",
                        }
                    },
                )

                async def no_change_callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                    item = await tx.fetchone(
                        "SELECT row_revision,lifecycle_state,latest_revision_uuid,serving_revision_uuid FROM mkb_intake_items "
                        "WHERE team_uuid=? AND intake_item_uuid=?",
                        (command.team_uuid, target["intake_item_uuid"]),
                    )
                    if (
                        item is None
                        or item["row_revision"] != target["item_revision"]
                        or item["lifecycle_state"] != "active"
                        or item["latest_revision_uuid"] != target["intake_revision_uuid"]
                    ):
                        raise MkbError("METADATA_TARGET_STALE", "Frozen metadata target changed before admission", 409)
                    current_merged, current_fingerprint = await self._merged_metadata_semantics_tx(
                        tx,
                        command.team_uuid,
                        target["intake_revision_uuid"],
                        semantics,
                        base_semantics,
                    )
                    if current_fingerprint != fingerprint or current_merged != _merged:
                        raise MkbError("METADATA_TARGET_STALE", "Frozen metadata inputs changed before admission", 409)
                    candidate = await tx.execute(
                        "INSERT OR IGNORE INTO mkb_intake_candidate_sets "
                        "(candidate_set_uuid,team_uuid,intake_source_uuid,producer_execution_uuid,producer_process_uuid,"
                        "producer_fencing_generation,source_kind_definition_digest,acquisition_capability_digest,s05_binding_digest,"
                        "observation_key,observation_fingerprint,completeness,expected_member_count,observed_member_count,"
                        "accepted_member_count,rejected_member_count,duplicate_member_count,expected_page_count,observed_page_count,"
                        "expected_bytes,observed_bytes,root_digest,staging_state,seal_at,created_at,updated_at,payload_extra) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, '{}')",
                        (
                            uuid7(),
                            command.team_uuid,
                            target["intake_source_uuid"],
                            command.execution_uuid,
                            command.process_uuid,
                            command.fencing_generation,
                            target["source_kind_definition_digest"],
                            stable_digest({"process_key": "intake.update_metadata.no_change"}),
                            command.binding_digest,
                            target["normalized_external_key"],
                            fingerprint,
                            "complete",
                            1,
                            1,
                            1,
                            0,
                            0,
                            1,
                            1,
                            0,
                            0,
                            fingerprint,
                            "accepted",
                            now,
                            now,
                            now,
                        ),
                    )
                    del candidate
                    await self._insert_no_change_transition(
                        tx,
                        command=command,
                        item=item,
                        target=target,
                        refs=refs,
                        now=now,
                    )

                return material, {"admission_result": "auto_admitted"}, no_change_callback

            # Freeze an exact, already full-valid S06/S07 family before this
            # metadata Task enters its replay stages.  The later S07 handler may
            # reuse its summaries only through these immutable receipts; it must
            # never discover a floating "latest" construction while running.
            metadata_refresh_source = await self._freeze_metadata_refresh_source(command, target)
            metadata_refresh_headers = self._metadata_refresh_headers(_merged, fingerprint)
            rebuilt = await self._acquire_rebuild(
                command,
                {**state, "intent_context": {"target": target}},
            )
            material, _route_extra, callback = rebuilt
            next_state = dict(material.envelope["state"])
            next_state["request_intent"] = "intake.update_metadata"
            next_state["operation_mode"] = "metadata_update"
            next_state["metadata_base_semantics"] = base_semantics
            next_state["metadata_semantics"] = semantics
            next_state["metadata_merged_semantics"] = _merged
            next_state["metadata_refresh_mode"] = _METADATA_REFRESH_REUSE_SUMMARIES
            next_state["metadata_refresh_source"] = metadata_refresh_source
            next_state["metadata_refresh_headers"] = metadata_refresh_headers
            updated = self._material(
                command,
                next_state,
                {
                    "acquisition_evidence": {
                        "mode": "metadata_update",
                        "intake_item_uuid": next_state["intake_item_uuid"],
                        "intake_revision_uuid": next_state["intake_revision_uuid"],
                        "semantic_count": len(semantics),
                    }
                },
            )
            return updated, {}, callback


    async def _freeze_metadata_refresh_source(
            self,
            command: ProcessCommand,
            target: Mapping[str, Any],
        ) -> dict[str, Any]:
            """Freeze one complete, current source family for S07 reuse mode.

            A metadata refresh inherits accepted clean bytes, but it must not
            manufacture S06 or summaries again.  Select one *single source
            Execution* whose six current members are all full-valid and bind to the
            predecessor Revision/clean Artifact.  The resulting receipts are
            copied into the immutable stage state and rechecked before use.
            """

            clean = target.get("clean_artifact")
            required_target = (
                "intake_item_uuid",
                "intake_revision_uuid",
            )
            if (
                any(not isinstance(target.get(key), str) or not target[key] for key in required_target)
                or not isinstance(clean, Mapping)
                or not isinstance(clean.get("intake_artifact_uuid"), str)
                or not isinstance(clean.get("content_digest"), str)
            ):
                raise MkbError(
                    "METADATA_REFRESH_SOURCE_MISSING",
                    "Metadata refresh requires a retained predecessor clean artifact",
                    409,
                )
            source_clean_artifact_uuid = str(clean["intake_artifact_uuid"])
            source_clean_digest = str(clean["content_digest"])
            async with self._persistence.transaction() as tx:
                rows = await tx.fetchall(
                    "SELECT p.execution_uuid AS pointer_execution_uuid,a.execution_uuid,a.task_uuid,a.artifact_type,"
                    "a.generation_artifact_uuid,a.logical_handle,a.content_digest,a.size_bytes,a.clean_artifact_uuid,"
                    "a.clean_artifact_digest,a.created_at FROM mkb_generation_pointers AS p "
                    "JOIN mkb_generation_artifacts AS a ON a.team_uuid=p.team_uuid "
                    "AND a.generation_artifact_uuid=p.current_generation_artifact_uuid "
                    "WHERE p.team_uuid=? AND a.intake_item_uuid=? AND a.intake_revision_uuid=? "
                    "AND a.execution_uuid=p.execution_uuid AND a.artifact_type=p.artifact_type "
                    "AND a.validation_disposition='full_valid' "
                    "AND p.artifact_type IN ('structure_document','retrieval_block_projection','structure_validation_report',"
                    "'construction_document','dual_channel_projection','construction_validation_report') "
                    "ORDER BY a.created_at DESC,a.generation_artifact_uuid DESC",
                    (command.team_uuid, target["intake_item_uuid"], target["intake_revision_uuid"]),
                )

            by_execution: dict[str, dict[str, dict[str, Any]]] = {}
            for row in rows:
                execution_uuid = row.get("execution_uuid")
                artifact_type = row.get("artifact_type")
                if (
                    not isinstance(execution_uuid, str)
                    or not execution_uuid
                    or row.get("pointer_execution_uuid") != execution_uuid
                    or not isinstance(artifact_type, str)
                    or artifact_type not in _METADATA_REFRESH_SOURCE_TYPES
                ):
                    continue
                family = by_execution.setdefault(execution_uuid, {})
                # A current pointer is unique by type; retaining the first row
                # makes an unexpected duplicate incapable of influencing which
                # receipt is selected.
                family.setdefault(artifact_type, row)

            candidates: list[tuple[str, str, str, dict[str, dict[str, Any]]]] = []
            for execution_uuid, members in by_execution.items():
                if set(members) != set(_METADATA_REFRESH_SOURCE_TYPES):
                    continue
                task_uuid = members["construction_document"].get("task_uuid")
                if not isinstance(task_uuid, str) or not task_uuid:
                    continue
                if any(
                    member.get("task_uuid") != task_uuid
                    or member.get("clean_artifact_uuid") != source_clean_artifact_uuid
                    or member.get("clean_artifact_digest") != source_clean_digest
                    or not isinstance(member.get("generation_artifact_uuid"), str)
                    or not isinstance(member.get("logical_handle"), str)
                    or not isinstance(member.get("content_digest"), str)
                    or isinstance(member.get("size_bytes"), bool)
                    or not isinstance(member.get("size_bytes"), int)
                    or int(member["size_bytes"]) < 0
                    for member in members.values()
                ):
                    continue
                created_at = max(str(member.get("created_at") or "") for member in members.values())
                candidates.append((created_at, execution_uuid, task_uuid, members))
            if not candidates:
                raise MkbError(
                    "METADATA_REFRESH_SOURCE_MISSING",
                    "Metadata refresh requires one current full-valid source construction family",
                    409,
                )
            _created_at, source_execution_uuid, source_task_uuid, members = max(candidates, key=lambda item: item[:2])
            receipts = {
                artifact_type: {
                    "generation_artifact_uuid": member["generation_artifact_uuid"],
                    "logical_handle": member["logical_handle"],
                    "content_digest": member["content_digest"],
                    "size_bytes": member["size_bytes"],
                }
                for artifact_type, member in members.items()
            }
            return {
                "schema_version": "mkb.metadata-refresh-source.v1",
                "source_execution_uuid": source_execution_uuid,
                "source_task_uuid": source_task_uuid,
                "source_intake_revision_uuid": target["intake_revision_uuid"],
                "source_clean_artifact_uuid": source_clean_artifact_uuid,
                "source_clean_digest": source_clean_digest,
                "source_construction_generation_artifact_uuid": receipts["construction_document"][
                    "generation_artifact_uuid"
                ],
                "members": receipts,
            }


    async def _acquire_lifecycle(
            self,
            command: ProcessCommand,
            state: dict[str, Any],
            intent: str,
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            target = self._frozen_target(state, require_clean=False)
            if self._lifecycle is None:
                raise MkbError("INTAKE_LIFECYCLE_UNAVAILABLE", "Lifecycle transition service is unavailable", 503)
            if intent == "intake.deactivate":
                action = "deactivate"
            elif intent == "intake.reactivate":
                action = "reactivate"
            elif intent == "intake.delete":
                action = "delete"
            else:
                raise MkbError("INTAKE_LIFECYCLE_ACTION_INVALID", "Lifecycle action is invalid", 422)
            next_state = {
                "request_intent": intent,
                "operation_mode": "lifecycle",
                "lifecycle_action": action,
                "frozen_target": target,
                "team_uuid": command.team_uuid,
                "task_uuid": command.task_uuid,
                "trace_uuid": command.trace_uuid,
                "admission_result": "auto_admitted",
            }
            material = self._material(
                command,
                next_state,
                {
                    "lifecycle_command": {
                        "action": action,
                        "intake_item_uuid": target["intake_item_uuid"],
                        "expected_item_revision": target["item_revision"],
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                await self._lifecycle.apply_tx(
                    tx,
                    IntakeLifecycleCommand(
                        team_uuid=command.team_uuid,
                        intake_item_uuid=target["intake_item_uuid"],
                        action=action,
                        trace_uuid=command.trace_uuid,
                        idempotency_key=stable_digest(
                            {
                                "process_uuid": command.process_uuid,
                                "fencing_generation": command.fencing_generation,
                                "action": action,
                            }
                        ),
                        expected_item_revision=target["item_revision"],
                        task_uuid=command.task_uuid,
                        execution_uuid=command.execution_uuid,
                        process_uuid=command.process_uuid,
                        proof_ref=refs["proof_ref"],
                        proof_digest=refs["proof_digest"],
                    ),
                )

            return material, {}, callback

