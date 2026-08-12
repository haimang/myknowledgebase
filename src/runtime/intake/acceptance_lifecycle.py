"""Rebuild/metadata revision acceptance and semantic merge."""

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
    _is_sha256_digest,
    _StageMaterial,
)


class IntakeAcceptanceLifecycleMixin:
    """Rebuild/metadata revision acceptance and semantic merge."""

    async def _accept_rebuild(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            target = state.get("frozen_target")
            if not isinstance(target, dict):
                raise MkbError("REBUILD_TARGET_INVALID", "Frozen Intake rebuild target is unavailable", 422)
            required = ("intake_item_uuid", "intake_revision_uuid", "source_snapshot_uuid", "item_revision")
            if any(target.get(key) is None for key in required):
                raise MkbError("REBUILD_TARGET_INVALID", "Frozen Intake rebuild target is invalid", 422)
            next_state = dict(state)
            next_state["accepted_at"] = utc_now()
            material = self._material(
                command,
                next_state,
                {
                    "rebuild_admission": {
                        "intake_item_uuid": target["intake_item_uuid"],
                        "intake_revision_uuid": target["intake_revision_uuid"],
                        "source_snapshot_uuid": target["source_snapshot_uuid"],
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
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
                    raise MkbError("REBUILD_TARGET_STALE", "Frozen Intake rebuild target changed before admission", 409)
                candidate = await tx.fetchone(
                    "SELECT staging_state FROM mkb_intake_candidate_sets WHERE team_uuid=? AND candidate_set_uuid=?",
                    (command.team_uuid, state["candidate_set_uuid"]),
                )
                if candidate is None or candidate["staging_state"] != "sealed":
                    raise MkbError("REBUILD_CANDIDATE_FENCE", "Rebuild candidate evidence is unavailable", 409)
                updated = await tx.execute(
                    "UPDATE mkb_intake_candidate_sets SET staging_state='accepted',accepted_member_count=1,"
                    "accepted_snapshot_uuid=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE team_uuid=? AND candidate_set_uuid=? AND staging_state='sealed'",
                    (
                        target["source_snapshot_uuid"],
                        next_state["accepted_at"],
                        command.team_uuid,
                        state["candidate_set_uuid"],
                    ),
                )
                if updated.rowcount != 1:
                    raise MkbError("REBUILD_CANDIDATE_FENCE", "Rebuild candidate evidence changed before admission", 409)
                await tx.execute(
                    "INSERT INTO mkb_intake_item_transitions "
                    "(transition_uuid,team_uuid,intake_item_uuid,action_key,action_version,before_lifecycle,after_lifecycle,"
                    "before_latest_revision_uuid,after_latest_revision_uuid,before_serving_revision_uuid,after_serving_revision_uuid,"
                    "item_revision_before,item_revision_after,causation_task_uuid,causation_execution_uuid,causation_process_uuid,"
                    "proof_ref,proof_digest,transition_fence,occurred_at,payload_extra) "
                    "VALUES (?,?,?,'rebuild','v1','active','active',?,?,?, ?,?,?,?,?,?,?,?,?,?,'{}')",
                    (
                        uuid7(),
                        command.team_uuid,
                        target["intake_item_uuid"],
                        target["intake_revision_uuid"],
                        target["intake_revision_uuid"],
                        item["serving_revision_uuid"],
                        item["serving_revision_uuid"],
                        item["row_revision"],
                        item["row_revision"],
                        command.task_uuid,
                        command.execution_uuid,
                        command.process_uuid,
                        refs["proof_ref"],
                        refs["proof_digest"],
                        stable_digest(
                            {"rebuild_process": command.process_uuid, "fencing_generation": command.fencing_generation}
                        ),
                        next_state["accepted_at"],
                    ),
                )

            return material, {"admission_result": "auto_admitted"}, callback


    async def _accept_metadata_update(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            target = state.get("frozen_target")
            base_semantics = state.get("metadata_base_semantics")
            semantics = state.get("metadata_semantics")
            if (
                not isinstance(target, dict)
                or not isinstance(base_semantics, list)
                or not isinstance(semantics, list)
                or not semantics
            ):
                raise MkbError("METADATA_TARGET_INVALID", "Frozen metadata update is unavailable", 422)
            merged, fingerprint = await self._merged_metadata_semantics(
                command.team_uuid,
                target.get("intake_revision_uuid"),
                semantics,
                base_semantics,
            )
            no_change = fingerprint == target.get("revision_fingerprint")
            next_state = dict(state)
            next_state["accepted_at"] = utc_now()
            next_state["metadata_revision_uuid"] = None if no_change else uuid7()
            next_state["metadata_fingerprint"] = fingerprint
            if no_change:
                # A no-change command is still auditable, but it must not make a
                # synthetic Revision or derived generation.  The static workflow
                # carries that fact through bounded passthrough stages.
                next_state["operation_mode"] = "metadata_no_change"
                next_state["metadata_no_change"] = True
                next_state["intake_revision_uuid"] = target["intake_revision_uuid"]
            else:
                assert isinstance(next_state["metadata_revision_uuid"], str)
                if state.get("metadata_refresh_mode") != _METADATA_REFRESH_REUSE_SUMMARIES:
                    raise MkbError(
                        "METADATA_REFRESH_MODE_INVALID",
                        "Metadata revision acceptance lacks a supported S07 refresh mode",
                        409,
                    )
                if not isinstance(state.get("metadata_refresh_source"), Mapping):
                    raise MkbError(
                        "METADATA_REFRESH_SOURCE_MISSING",
                        "Metadata revision acceptance lacks a frozen source construction",
                        409,
                    )
                # The retained clean content is immutable but each semantic
                # Revision owns its own logical artifact row.  That makes a later
                # rebuild resolve its target from the latest Revision without
                # reaching through a mutable predecessor alias.
                next_state["clean_artifact_uuid"] = uuid7()
                next_state["intake_revision_uuid"] = next_state["metadata_revision_uuid"]
                next_state["construct_mode"] = "metadata_refresh"
                next_state["metadata_merged_semantics"] = merged
                next_state["metadata_refresh_headers"] = self._metadata_refresh_headers(merged, fingerprint)
            material = self._material(
                command,
                next_state,
                {
                    "metadata_admission": {
                        "intake_item_uuid": target.get("intake_item_uuid"),
                        "predecessor_revision_uuid": target.get("intake_revision_uuid"),
                        "semantic_count": len(semantics),
                        "disposition": "no_change" if no_change else "revision_appended",
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                item = await tx.fetchone(
                    "SELECT row_revision,lifecycle_state,latest_revision_uuid,serving_revision_uuid FROM mkb_intake_items "
                    "WHERE team_uuid=? AND intake_item_uuid=?",
                    (command.team_uuid, target.get("intake_item_uuid")),
                )
                if (
                    item is None
                    or item["row_revision"] != target.get("item_revision")
                    or item["lifecycle_state"] != "active"
                    or item["latest_revision_uuid"] != target.get("intake_revision_uuid")
                ):
                    raise MkbError("METADATA_TARGET_STALE", "Frozen metadata target changed before admission", 409)
                action = await tx.fetchone(
                    "SELECT definition_version FROM mkb_intake_action_definitions "
                    "WHERE action_key='update_metadata' AND definition_version='v1'"
                )
                if action is None:
                    raise MkbError("INTAKE_ACTION_UNREGISTERED", "Metadata action is not registered", 503)
                current_merged, current_fingerprint = await self._merged_metadata_semantics_tx(
                    tx,
                    command.team_uuid,
                    target["intake_revision_uuid"],
                    semantics,
                    base_semantics,
                )
                if current_fingerprint != fingerprint or current_merged != merged:
                    raise MkbError("METADATA_TARGET_STALE", "Frozen metadata inputs changed before admission", 409)
                candidate = await tx.execute(
                    "UPDATE mkb_intake_candidate_sets SET staging_state='accepted',accepted_member_count=1,"
                    "accepted_snapshot_uuid=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE team_uuid=? AND candidate_set_uuid=? AND staging_state='sealed'",
                    (target["source_snapshot_uuid"], next_state["accepted_at"], command.team_uuid, state["candidate_set_uuid"]),
                )
                if candidate.rowcount != 1:
                    raise MkbError("METADATA_CANDIDATE_FENCE", "Metadata candidate evidence changed before admission", 409)
                if no_change:
                    await self._insert_no_change_transition(
                        tx,
                        command=command,
                        item=item,
                        target=target,
                        refs=refs,
                        now=next_state["accepted_at"],
                    )
                    return
                ordinal_row = await tx.fetchone(
                    "SELECT MAX(revision_ordinal) AS highest FROM mkb_intake_revisions "
                    "WHERE team_uuid=? AND intake_item_uuid=?",
                    (command.team_uuid, target["intake_item_uuid"]),
                )
                ordinal = int(ordinal_row["highest"] or 0) + 1
                now = next_state["accepted_at"]
                await tx.execute(
                    "INSERT INTO mkb_intake_revisions "
                    "(team_uuid,intake_revision_uuid,intake_item_uuid,revision_ordinal,predecessor_revision_uuid,revision_fingerprint,"
                    "creation_action_key,creation_action_version,source_snapshot_uuid,created_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                    (
                        command.team_uuid,
                        next_state["metadata_revision_uuid"],
                        target["intake_item_uuid"],
                        ordinal,
                        target["intake_revision_uuid"],
                        fingerprint,
                        "update_metadata",
                        action["definition_version"],
                        target["source_snapshot_uuid"],
                        now,
                        "{}",
                    ),
                )
                metadata_revision_uuid = next_state["metadata_revision_uuid"]
                assert isinstance(metadata_revision_uuid, str)
                for entry in merged.values():
                    await self._insert_revision_semantic(tx, command.team_uuid, metadata_revision_uuid, entry, now)
                inherited_clean = await tx.fetchone(
                    "SELECT media_type,content_digest,size_bytes,logical_handle,stored_object_uuid "
                    "FROM mkb_intake_artifacts WHERE team_uuid=? AND intake_artifact_uuid=? "
                    "AND owner_revision_uuid=? AND artifact_role='clean_text'",
                    (command.team_uuid, target["clean_artifact"]["intake_artifact_uuid"], target["intake_revision_uuid"]),
                )
                if inherited_clean is None or not inherited_clean["stored_object_uuid"]:
                    raise MkbError("METADATA_CLEAN_ARTIFACT_MISSING", "Retained clean artifact is unavailable", 409)
                await tx.execute(
                    "INSERT INTO mkb_intake_artifacts "
                    "(team_uuid,intake_artifact_uuid,owner_snapshot_uuid,owner_revision_uuid,artifact_role,media_type,"
                    "content_digest,size_bytes,logical_handle,stored_object_uuid,producer_execution_uuid,producer_process_uuid,"
                    "created_at,payload_extra) VALUES (?,?,NULL,?,'clean_text',?,?,?,?,?,?,?,?,'{}')",
                    (
                        command.team_uuid,
                        next_state["clean_artifact_uuid"],
                        metadata_revision_uuid,
                        inherited_clean["media_type"],
                        inherited_clean["content_digest"],
                        inherited_clean["size_bytes"],
                        inherited_clean["logical_handle"],
                        inherited_clean["stored_object_uuid"],
                        command.execution_uuid,
                        command.process_uuid,
                        now,
                    ),
                )
                await self._reference_object(
                    tx,
                    team_uuid=command.team_uuid,
                    stored_object_uuid=inherited_clean["stored_object_uuid"],
                    purpose="intake_revision_artifact",
                    owner_kind="intake_revision",
                    owner_uuid=metadata_revision_uuid,
                    digest=inherited_clean["content_digest"],
                    size=inherited_clean["size_bytes"],
                )
                changed = await tx.execute(
                    "UPDATE mkb_intake_items SET latest_revision_uuid=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE team_uuid=? AND intake_item_uuid=? AND row_revision=? AND latest_revision_uuid=?",
                    (
                        metadata_revision_uuid,
                        now,
                        command.team_uuid,
                        target["intake_item_uuid"],
                        item["row_revision"],
                        target["intake_revision_uuid"],
                    ),
                )
                if changed.rowcount != 1:
                    raise MkbError("METADATA_TARGET_STALE", "Frozen metadata target changed before admission", 409)
                await tx.execute(
                    "INSERT INTO mkb_intake_item_transitions "
                    "(transition_uuid,team_uuid,intake_item_uuid,action_key,action_version,before_lifecycle,after_lifecycle,"
                    "before_latest_revision_uuid,after_latest_revision_uuid,before_serving_revision_uuid,after_serving_revision_uuid,"
                    "item_revision_before,item_revision_after,causation_task_uuid,causation_execution_uuid,causation_process_uuid,"
                    "proof_ref,proof_digest,transition_fence,occurred_at,payload_extra) "
                    "VALUES (?,?,?,'update_metadata',?,'active','active',?,?,?, ?,?,?,?,?,?,?,?,?,?,'{}')",
                    (
                        uuid7(),
                        command.team_uuid,
                        target["intake_item_uuid"],
                        action["definition_version"],
                        target["intake_revision_uuid"],
                        metadata_revision_uuid,
                        item["serving_revision_uuid"],
                        item["serving_revision_uuid"],
                        item["row_revision"],
                        item["row_revision"] + 1,
                        command.task_uuid,
                        command.execution_uuid,
                        command.process_uuid,
                        refs["proof_ref"],
                        refs["proof_digest"],
                        stable_digest({"metadata_process": command.process_uuid, "fencing_generation": command.fencing_generation}),
                        now,
                    ),
                )

            return material, {
                "admission_result": "auto_admitted",
                "request_intent": "intake.update_metadata",
            }, callback


    async def _merged_metadata_semantics(
            self,
            team_uuid: str,
            revision_uuid: object,
            replacements: list[Any],
            base_semantics: list[Any],
        ) -> tuple[dict[str, dict[str, Any]], str]:
            if not isinstance(revision_uuid, str) or not revision_uuid:
                raise MkbError("METADATA_TARGET_INVALID", "Frozen metadata predecessor is invalid", 422)
            async with self._persistence.transaction() as tx:
                return await self._merged_metadata_semantics_tx(tx, team_uuid, revision_uuid, replacements, base_semantics)


    async def _merged_metadata_semantics_tx(
            self,
            tx: UnitOfWork,
            team_uuid: str,
            revision_uuid: str,
            replacements: list[Any],
            base_semantics: list[Any],
        ) -> tuple[dict[str, dict[str, Any]], str]:
            del revision_uuid
            base: dict[str, dict[str, Any]] = {}
            for entry in base_semantics:
                if not isinstance(entry, dict) or not isinstance(entry.get("semantic_key"), str):
                    raise MkbError("METADATA_SEMANTICS_INVALID", "Frozen predecessor semantic values are invalid", 422)
                key = entry["semantic_key"]
                if key in base:
                    raise MkbError("METADATA_SEMANTICS_INVALID", "Frozen predecessor semantic keys repeat", 422)
                await self._validate_metadata_entry_tx(tx, team_uuid, entry)
                base[key] = dict(entry)
            replacement: dict[str, dict[str, Any]] = {}
            for entry in replacements:
                if not isinstance(entry, dict) or not isinstance(entry.get("semantic_key"), str):
                    raise MkbError("METADATA_SEMANTICS_INVALID", "Frozen metadata semantic values are invalid", 422)
                key = entry["semantic_key"]
                if key in replacement:
                    raise MkbError("METADATA_SEMANTICS_INVALID", "Frozen metadata semantic keys repeat", 422)
                await self._validate_metadata_entry_tx(tx, team_uuid, entry)
                replacement[key] = dict(entry)
            merged = dict(base)
            merged.update(replacement)
            return merged, self._semantic_fingerprint(list(merged.values()))


    @staticmethod
    def _metadata_refresh_headers(
            merged: Mapping[str, Mapping[str, Any]],
            fingerprint: str,
        ) -> dict[str, str]:
            """Project only closed S04 digest facts into the S07 text recipe.

            Context/filter values remain authoritative only in S04.  S07 carries
            their locked digests (never caller text) plus the full revision
            fingerprint, so every participating metadata change has a deterministic
            projection without opening an arbitrary-header or filter side channel.
            """

            if not _is_sha256_digest(fingerprint):
                raise MkbError("METADATA_PROJECTION_INVALID", "Metadata fingerprint is invalid", 409)
            headers = {"s04.metadata_fingerprint": fingerprint}
            for semantic_key in ("context_metadata", "filter_metadata"):
                entry = merged.get(semantic_key)
                value_digest = entry.get("value_digest") if isinstance(entry, Mapping) else None
                if not _is_sha256_digest(value_digest):
                    raise MkbError(
                        "METADATA_PROJECTION_INVALID",
                        "Metadata projection lacks a registered semantic digest",
                        409,
                    )
                headers[f"s04.{semantic_key}_digest"] = value_digest
            return headers


    async def _validate_metadata_entry_tx(
            self, tx: UnitOfWork, team_uuid: str, entry: Mapping[str, Any]
        ) -> None:
            required = (
                "semantic_key",
                "definition_version",
                "definition_digest",
                "value_kind",
                "fingerprint_participation",
                "value",
                "value_digest",
            )
            if any(key not in entry for key in required):
                raise MkbError("METADATA_SEMANTICS_INVALID", "Frozen metadata semantic value is incomplete", 422)
            definition = await tx.fetchone(
                "SELECT definition_digest,value_kind FROM mkb_intake_semantic_definitions "
                "WHERE semantic_key=? AND definition_version=?",
                (entry["semantic_key"], entry["definition_version"]),
            )
            if (
                definition is None
                or definition["definition_digest"] != entry["definition_digest"]
                or definition["value_kind"] != entry["value_kind"]
                or type(entry["fingerprint_participation"]) is not bool
            ):
                raise MkbError("METADATA_SEMANTIC_DEFINITION_DRIFT", "Metadata semantic definition drifted", 409)
            expected = self._semantic_value_digest(
                str(entry["semantic_key"]),
                str(entry["definition_version"]),
                str(entry["definition_digest"]),
                entry["value"],
            )
            if entry["value_digest"] != expected:
                raise MkbError("METADATA_SEMANTICS_INVALID", "Metadata semantic value digest is invalid", 422)
            # Validate the actual scalar shape before it reaches the immutable
            # Revision table.  Logical ``ref`` values are a narrow public surface:
            # they must name an already-retained IntakeArtifact in this Team, never
            # a path, handle, or unowned opaque identifier.
            self._semantic_scalar(entry["value_kind"], entry["value"])
            if entry["value_kind"] == "ref":
                artifact = await tx.fetchone(
                    "SELECT intake_artifact_uuid FROM mkb_intake_artifacts "
                    "WHERE team_uuid=? AND intake_artifact_uuid=?",
                    (team_uuid, entry["value"]),
                )
                if artifact is None:
                    raise MkbError(
                        "METADATA_SEMANTIC_REF_UNAVAILABLE",
                        "Metadata reference is not an available Intake artifact",
                        409,
                    )


    @staticmethod
    def _semantic_scalar(kind: Any, value: Any) -> dict[str, Any]:
            values = {"value_bool": None, "value_int": None, "value_real": None, "value_text": None, "value_artifact_uuid": None}
            if kind == "bool" and type(value) is bool:
                values["value_bool"] = int(value)
            elif kind == "int" and type(value) is int:
                values["value_int"] = value
            elif kind == "real" and type(value) in {int, float}:
                values["value_real"] = float(value)
            elif kind == "text" and isinstance(value, str):
                values["value_text"] = value
            elif kind == "ref" and isinstance(value, str) and value:
                values["value_artifact_uuid"] = value
            else:
                raise MkbError("METADATA_SEMANTICS_INVALID", "Metadata semantic value is invalid", 422)
            return values


    @staticmethod
    def _semantic_storage_kind(kind: Any) -> str:
            if kind == "ref":
                return "artifact_ref"
            if kind in {"bool", "int", "real", "text"}:
                return kind
            raise MkbError("METADATA_SEMANTICS_INVALID", "Metadata semantic value is invalid", 422)


    async def _insert_no_change_transition(
            self,
            tx: UnitOfWork,
            *,
            command: ProcessCommand,
            item: Mapping[str, Any],
            target: Mapping[str, Any],
            refs: Mapping[str, str],
            now: str,
        ) -> None:
            action = await tx.fetchone(
                "SELECT definition_version FROM mkb_intake_action_definitions "
                "WHERE action_key='no_change' AND definition_version='v1'"
            )
            if action is None:
                raise MkbError("INTAKE_ACTION_UNREGISTERED", "No-change action is not registered", 503)
            await tx.execute(
                "INSERT INTO mkb_intake_item_transitions "
                "(transition_uuid,team_uuid,intake_item_uuid,action_key,action_version,before_lifecycle,after_lifecycle,"
                "before_latest_revision_uuid,after_latest_revision_uuid,before_serving_revision_uuid,after_serving_revision_uuid,"
                "item_revision_before,item_revision_after,causation_task_uuid,causation_execution_uuid,causation_process_uuid,"
                "proof_ref,proof_digest,transition_fence,occurred_at,payload_extra) "
                "VALUES (?,?,?,'no_change',?,'active','active',?,?,?, ?,?,?,?,?,?,?,?,?,?,'{}')",
                (
                    uuid7(),
                    command.team_uuid,
                    target["intake_item_uuid"],
                    action["definition_version"],
                    target["intake_revision_uuid"],
                    target["intake_revision_uuid"],
                    item["serving_revision_uuid"],
                    item["serving_revision_uuid"],
                    item["row_revision"],
                    item["row_revision"],
                    command.task_uuid,
                    command.execution_uuid,
                    command.process_uuid,
                    refs["proof_ref"],
                    refs["proof_digest"],
                    stable_digest({"metadata_no_change_process": command.process_uuid, "fencing_generation": command.fencing_generation}),
                    now,
                ),
            )

