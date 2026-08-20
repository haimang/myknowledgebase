"""Snapshot acceptance and initial semantic fingerprinting."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import PromoteRequest
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _digest_bytes,
    _json,
    _StageMaterial,
)
from src.services.events import DomainEventWriter


class IntakeAcceptanceSnapshotMixin:
    """Snapshot acceptance and initial semantic fingerprinting."""

    async def _accept_snapshot(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            if state.get("operation_mode") == "scatter_root":
                return await self._accept_registered_api_collection(command, state)
            if state.get("operation_mode") == "rebuild":
                return await self._accept_rebuild(command, state)
            if state.get("operation_mode") == "metadata_update":
                return await self._accept_metadata_update(command, state)
            admission = state.get("admission_result")
            if admission not in {"auto_admitted", "human_review_required"}:
                raise MkbError("PREFLIGHT_REJECTED", "Preflight did not admit this candidate set", 409)
            required = (
                "intake_source_uuid",
                "candidate_set_uuid",
                "intake_snapshot_uuid",
                "intake_item_uuid",
                "intake_revision_uuid",
                "raw_artifact_uuid",
                "clean_artifact_uuid",
                "candidate_root_digest",
                "clean_digest",
            )
            if any(not state.get(key) for key in required):
                raise MkbError("PIPELINE_INPUT_INVALID", "Accepted snapshot is missing immutable intake coordinates", 422)
            next_state = dict(state)
            next_state["accepted_at"] = utc_now()
            raw_bytes = str(state.get("raw_text") or "").encode("utf-8")
            clean_bytes = str(state.get("clean_text") or "").encode("utf-8")
            raw_stat = await self._storage.promote(
                raw_bytes,
                PromoteRequest(team_uuid=command.team_uuid, purpose="process_io", media_type="text/plain"),
            )
            clean_stat = await self._storage.promote(
                clean_bytes,
                PromoteRequest(team_uuid=command.team_uuid, purpose="process_io", media_type="text/plain"),
            )
            next_state["raw_cas_digest"] = raw_stat.sha256
            next_state["raw_cas_size"] = raw_stat.size_bytes
            next_state["raw_cas_handle"] = raw_stat.handle.value
            next_state["clean_cas_digest"] = clean_stat.sha256
            next_state["clean_cas_size"] = clean_stat.size_bytes
            next_state["clean_cas_handle"] = clean_stat.handle.value
            material = self._material(
                command,
                next_state,
                {
                    "accepted_intake_revision": {
                        "intake_item_uuid": state["intake_item_uuid"],
                        "intake_revision_uuid": state["intake_revision_uuid"],
                        "intake_snapshot_uuid": state["intake_snapshot_uuid"],
                        "admission_result": admission,
                    }
                },
            )
            output_digest = _digest_bytes(material.output_bytes)
            output_size = len(material.output_bytes)

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                now = next_state["accepted_at"]
                stored_object_uuid = await self._stored_object_uuid(tx, command.team_uuid, output_digest, output_size)
                if stored_object_uuid is None:
                    raise MkbError("OBJECT_CATALOGUE_MISSING", "Accepted stage output was not catalogued", 503)
                raw_object_uuid = await self._catalog_cas_object_tx(
                    tx,
                    command.team_uuid,
                    digest=str(next_state["raw_cas_digest"]),
                    size=int(next_state["raw_cas_size"]),
                    media_type="text/plain",
                    now=now,
                )
                clean_object_uuid = await self._catalog_cas_object_tx(
                    tx,
                    command.team_uuid,
                    digest=str(next_state["clean_cas_digest"]),
                    size=int(next_state["clean_cas_size"]),
                    media_type="text/plain",
                    now=now,
                )
                action = await tx.fetchone(
                    "SELECT action_key,definition_version FROM mkb_intake_action_definitions "
                    "WHERE action_key='accept_revision' AND definition_version='v1'"
                )
                if action is None:
                    raise MkbError("REGISTRY_NOT_FOUND", "Intake acceptance action is unavailable", 503)
                existing_snap = await tx.fetchone(
                    "SELECT intake_snapshot_uuid FROM mkb_intake_snapshots "
                    "WHERE team_uuid=? AND intake_source_uuid=? AND observation_key=?",
                    (command.team_uuid, state["intake_source_uuid"], state["normalized_external_key"]),
                )
                if existing_snap is not None:
                    state["intake_snapshot_uuid"] = existing_snap["intake_snapshot_uuid"]
                else:
                    await tx.execute(
                        "INSERT INTO mkb_intake_snapshots "
                        "(team_uuid,intake_snapshot_uuid,intake_source_uuid,observation_key,observation_fingerprint,candidate_root_digest,"
                        "completeness,preflight_outcome_ref,preflight_outcome_digest,s05_binding_digest,observed_at,accepted_at,"
                        "producer_execution_uuid,raw_artifact_uuid,payload_extra) VALUES (?,?,?,?,?,?, 'complete',?,?,?,?,?,?,?,'{}')",
                        (
                            command.team_uuid,
                            state["intake_snapshot_uuid"],
                            state["intake_source_uuid"],
                            state["normalized_external_key"],
                            state["raw_digest"],
                            state["candidate_root_digest"],
                            command.input_manifest_ref,
                            command.input_manifest_digest,
                            command.binding_digest,
                            state["observed_at"],
                            now,
                            command.execution_uuid,
                            state["raw_artifact_uuid"],
                        ),
                    )
                lifecycle = "deactivated" if state.get("require_human_review") else "active"
                deactivated_at = now if lifecycle == "deactivated" else None
                await tx.execute(
                    "INSERT OR IGNORE INTO mkb_intake_items "
                    "(team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,latest_revision_uuid,"
                    "serving_revision_uuid,row_revision,created_at,updated_at,deactivated_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,NULL,0,?,?,?,'{}')",
                    (
                        command.team_uuid,
                        state["intake_item_uuid"],
                        state["intake_source_uuid"],
                        state["normalized_external_key"],
                        lifecycle,
                        state["intake_revision_uuid"],
                        now,
                        now,
                        deactivated_at,
                    ),
                )
                await tx.execute(
                    "UPDATE mkb_intake_items SET latest_revision_uuid=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE team_uuid=? AND intake_item_uuid=?",
                    (state["intake_revision_uuid"], now, command.team_uuid, state["intake_item_uuid"]),
                )
                initial_semantics = await self._initial_semantics_tx(tx, state)
                fingerprint = self._semantic_fingerprint(initial_semantics)
                max_ordinal = await tx.fetchone(
                    "SELECT MAX(revision_ordinal) AS ordinal FROM mkb_intake_revisions "
                    "WHERE team_uuid=? AND intake_item_uuid=?",
                    (command.team_uuid, state["intake_item_uuid"]),
                )
                revision_ordinal = int(max_ordinal["ordinal"] or 0) + 1 if max_ordinal is not None else 1
                predecessor = await tx.fetchone(
                    "SELECT intake_revision_uuid FROM mkb_intake_revisions "
                    "WHERE team_uuid=? AND intake_item_uuid=? AND revision_ordinal=?",
                    (command.team_uuid, state["intake_item_uuid"], revision_ordinal - 1),
                )
                await tx.execute(
                    "INSERT INTO mkb_intake_revisions "
                    "(team_uuid,intake_revision_uuid,intake_item_uuid,revision_ordinal,predecessor_revision_uuid,"
                    "revision_fingerprint,creation_action_key,"
                    "creation_action_version,source_snapshot_uuid,created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,'{}')",
                    (
                        command.team_uuid,
                        state["intake_revision_uuid"],
                        state["intake_item_uuid"],
                        revision_ordinal,
                        None if predecessor is None else predecessor["intake_revision_uuid"],
                        fingerprint,
                        action["action_key"],
                        action["definition_version"],
                        state["intake_snapshot_uuid"],
                        now,
                    ),
                )
                for entry in initial_semantics:
                    await self._insert_revision_semantic(tx, command.team_uuid, state["intake_revision_uuid"], entry, now)
                for artifact_uuid, owner_snapshot, owner_revision, role, digest, size, handle, object_uuid in (
                    (
                        state["raw_artifact_uuid"],
                        state["intake_snapshot_uuid"],
                        None,
                        "raw_acquisition",
                        next_state["raw_cas_digest"],
                        next_state["raw_cas_size"],
                        next_state["raw_cas_handle"],
                        raw_object_uuid,
                    ),
                    (
                        state["clean_artifact_uuid"],
                        None,
                        state["intake_revision_uuid"],
                        "clean_text",
                        next_state["clean_cas_digest"],
                        next_state["clean_cas_size"],
                        next_state["clean_cas_handle"],
                        clean_object_uuid,
                    ),
                ):
                    await tx.execute(
                        "INSERT INTO mkb_intake_artifacts "
                        "(team_uuid,intake_artifact_uuid,owner_snapshot_uuid,owner_revision_uuid,artifact_role,media_type,"
                        "content_digest,size_bytes,logical_handle,stored_object_uuid,producer_execution_uuid,producer_process_uuid,"
                        "created_at,payload_extra) VALUES (?,?,?,?,?,?,?, ?,?,?,?,?,?,'{}')",
                        (
                            command.team_uuid,
                            artifact_uuid,
                            owner_snapshot,
                            owner_revision,
                            role,
                            "text/plain",
                            digest,
                            size,
                            handle,
                            object_uuid,
                            command.execution_uuid,
                            command.process_uuid,
                            now,
                        ),
                    )
                await self._reference_object(
                    tx,
                    team_uuid=command.team_uuid,
                    stored_object_uuid=raw_object_uuid,
                    purpose="intake_snapshot_artifact",
                    owner_kind="intake_snapshot",
                    owner_uuid=state["intake_snapshot_uuid"],
                    digest=str(next_state["raw_cas_digest"]),
                    size=int(next_state["raw_cas_size"]),
                )
                await self._reference_object(
                    tx,
                    team_uuid=command.team_uuid,
                    stored_object_uuid=clean_object_uuid,
                    purpose="intake_revision_artifact",
                    owner_kind="intake_revision",
                    owner_uuid=state["intake_revision_uuid"],
                    digest=str(next_state["clean_cas_digest"]),
                    size=int(next_state["clean_cas_size"]),
                )
                await self._reference_object(
                    tx,
                    team_uuid=command.team_uuid,
                    stored_object_uuid=stored_object_uuid,
                    purpose="intake_revision_artifact",
                    owner_kind="intake_revision",
                    owner_uuid=state["intake_revision_uuid"],
                    digest=output_digest,
                    size=output_size,
                )
                await tx.execute(
                    "INSERT INTO mkb_intake_snapshot_memberships "
                    "(team_uuid,intake_snapshot_uuid,member_ordinal,normalized_external_key,intake_item_uuid,observed_revision_uuid,"
                    "decision_kind,required,decision_digest,created_at,payload_extra) VALUES (?,?,0,?,?,?,'accepted',1,?,?,'{}')",
                    (
                        command.team_uuid,
                        state["intake_snapshot_uuid"],
                        state["normalized_external_key"],
                        state["intake_item_uuid"],
                        state["intake_revision_uuid"],
                        stable_digest({"admission": admission, "revision": state["intake_revision_uuid"]}),
                        now,
                    ),
                )
                accepted = await tx.execute(
                    "UPDATE mkb_intake_candidate_sets SET staging_state='accepted',accepted_member_count=1,"
                    "accepted_snapshot_uuid=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE candidate_set_uuid=? AND team_uuid=? AND staging_state='sealed'",
                    (state["intake_snapshot_uuid"], now, state["candidate_set_uuid"], command.team_uuid),
                )
                if accepted.rowcount != 1:
                    raise MkbError("CANDIDATE_SET_FENCE", "Candidate set changed before acceptance", 409)
                # The scatter projection belongs to the accepted Snapshot rather
                # than a Process.  Persist the same immutable coordinate on the
                # root Execution/Task so public `/items` never has to infer it
                # from an incidental latest row.
                execution_updated = await tx.execute(
                    "UPDATE mkb_executions SET intake_snapshot_uuid=?,intake_snapshot_digest=?,"
                    "row_revision=row_revision+1,updated_at=? WHERE execution_uuid=? AND team_uuid=? "
                    "AND intake_snapshot_uuid IS NULL",
                    (
                        state["intake_snapshot_uuid"],
                        stable_digest(
                            {
                                "intake_snapshot_uuid": state["intake_snapshot_uuid"],
                                "candidate_root_digest": state["candidate_root_digest"],
                            }
                        ),
                        now,
                        command.execution_uuid,
                        command.team_uuid,
                    ),
                )
                if execution_updated.rowcount != 1:
                    raise MkbError("INTAKE_SNAPSHOT_EXECUTION_FENCE", "Execution snapshot coordinate changed before acceptance", 409)
                change_set_uuid = uuid7()
                change_set_digest = stable_digest(
                    {
                        "schema_version": "mkb.intake-change-set.v1",
                        "intake_snapshot_uuid": state["intake_snapshot_uuid"],
                        "candidate_root_digest": state["candidate_root_digest"],
                        "members": [
                            {
                                "member_ordinal": 0,
                                "intake_item_uuid": state["intake_item_uuid"],
                                "intake_revision_uuid": state["intake_revision_uuid"],
                                "required": True,
                            }
                        ],
                    }
                )
                await tx.execute(
                    "INSERT INTO mkb_intake_change_sets "
                    "(change_set_uuid,team_uuid,intake_snapshot_uuid,change_set_digest,created_at,payload_extra) "
                    "VALUES (?,?,?,?,?,'{}')",
                    (
                        change_set_uuid,
                        command.team_uuid,
                        state["intake_snapshot_uuid"],
                        change_set_digest,
                        now,
                    ),
                )
                fact = {
                    "kind": "accept_revision",
                    "member_ordinal": 0,
                    "intake_item_uuid": state["intake_item_uuid"],
                    "intake_revision_uuid": state["intake_revision_uuid"],
                }
                await tx.execute(
                    "INSERT INTO mkb_intake_change_set_facts "
                    "(fact_uuid,change_set_uuid,team_uuid,fact_kind,fact_ordinal,intake_item_uuid,intake_revision_uuid,"
                    "semantic_key,semantic_definition_version,absence_key,fact_digest,created_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,?,NULL,NULL,NULL,?,?,'{}')",
                    (
                        uuid7(),
                        change_set_uuid,
                        command.team_uuid,
                        "accept_revision",
                        0,
                        state["intake_item_uuid"],
                        state["intake_revision_uuid"],
                        stable_digest(fact),
                        now,
                    ),
                )
                task_updated = await tx.execute(
                    "UPDATE mkb_tasks SET intake_snapshot_uuid=?,change_set_uuid=?,row_revision=row_revision+1,updated_at=? "
                    "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=? AND intake_snapshot_uuid IS NULL",
                    (
                        state["intake_snapshot_uuid"],
                        change_set_uuid,
                        now,
                        command.team_uuid,
                        command.task_uuid,
                        command.execution_uuid,
                    ),
                )
                if task_updated.rowcount != 1:
                    raise MkbError("INTAKE_SNAPSHOT_TASK_FENCE", "Task snapshot coordinate changed before acceptance", 409)
                events = DomainEventWriter()
                event_payload = {
                    "intake_snapshot_uuid": state["intake_snapshot_uuid"],
                    "intake_item_uuid": state["intake_item_uuid"],
                    "intake_revision_uuid": state["intake_revision_uuid"],
                    "change_set_uuid": change_set_uuid,
                    "candidate_set_uuid": state["candidate_set_uuid"],
                }
                await events.write(
                    tx,
                    team_uuid=command.team_uuid,
                    trace_uuid=command.trace_uuid,
                    event_type="intake.snapshot_accepted",
                    aggregate="intake",
                    summary="Intake snapshot accepted",
                    task_uuid=command.task_uuid,
                    execution_uuid=command.execution_uuid,
                    process_uuid=command.process_uuid,
                    payload=event_payload,
                )
                await events.write(
                    tx,
                    team_uuid=command.team_uuid,
                    trace_uuid=command.trace_uuid,
                    event_type="intake.candidate_accepted",
                    aggregate="intake",
                    summary="Intake candidate accepted",
                    task_uuid=command.task_uuid,
                    execution_uuid=command.execution_uuid,
                    process_uuid=command.process_uuid,
                    payload=event_payload,
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
                        state["intake_item_uuid"],
                        state["intake_revision_uuid"],
                        command.task_uuid,
                        command.execution_uuid,
                        command.process_uuid,
                        refs["proof_ref"],
                        refs["proof_digest"],
                        stable_digest({"process": command.process_uuid, "fence": command.fencing_generation}),
                        now,
                    ),
                )
                await events.write(
                    tx,
                    team_uuid=command.team_uuid,
                    trace_uuid=command.trace_uuid,
                    event_type="intake.item_transitioned",
                    aggregate="intake",
                    summary="Intake item accepted a new revision",
                    task_uuid=command.task_uuid,
                    execution_uuid=command.execution_uuid,
                    process_uuid=command.process_uuid,
                    payload=event_payload,
                    status_before="active",
                    status_after="active",
                )

            return material, {"admission_result": admission}, callback


    async def _catalog_cas_object_tx(
            self,
            tx: UnitOfWork,
            team_uuid: str,
            *,
            digest: str,
            size: int,
            media_type: str,
            now: str,
        ) -> str:
            from src.services.artifacts import live_stored_object_uuid

            existing = await live_stored_object_uuid(tx, team_uuid, digest, size)
            if existing is not None:
                return existing
            stored_object_uuid = uuid7()
            await tx.execute(
                "INSERT INTO mkb_stored_objects "
                "(stored_object_uuid,team_uuid,digest_algorithm,content_digest,size_bytes,media_type,storage_backend,"
                "created_at,payload_extra) VALUES (?,?, 'sha256',?,?,?,?,?,'{}')",
                (stored_object_uuid, team_uuid, digest, size, media_type, "local_fs", now),
            )
            return stored_object_uuid

    async def _accept_registered_api_collection(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            """Accept a sealed collection and fan out child intents in one UoW."""

            admission = state.get("admission_result")
            members = state.get("collection_members")
            required = (
                "intake_source_uuid",
                "candidate_set_uuid",
                "intake_snapshot_uuid",
                "change_set_uuid",
                "raw_artifact_uuid",
                "candidate_root_digest",
                "raw_digest",
                "observed_at",
            )
            if admission not in {"auto_admitted", "human_review_required"}:
                raise MkbError("PREFLIGHT_REJECTED", "Preflight did not admit this collection", 409)
            if any(not state.get(key) for key in required) or not isinstance(members, list):
                raise MkbError("SCATTER_STATE_INVALID", "Accepted collection lacks immutable coordinates", 422)
            next_state = dict(state)
            next_state["accepted_at"] = utc_now()
            acceptance = await self._prepare_scatter_collection_acceptance(command, next_state)
            material = self._material(
                command,
                next_state,
                {
                    "accepted_collection": {
                        "intake_source_uuid": acceptance.intake_source_uuid,
                        "intake_snapshot_uuid": acceptance.intake_snapshot_uuid,
                        "change_set_uuid": acceptance.change_set_uuid,
                        "change_set_digest": self._scatter_change_set_digest(acceptance),
                        "required_member_count": len(acceptance.members),
                        "admission_result": acceptance.admission_result,
                    }
                },
            )
            output_digest = _digest_bytes(material.output_bytes)
            output_size = len(material.output_bytes)

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                await self._scatter_acceptance.commit(
                    tx,
                    command=command,
                    acceptance=acceptance,
                    stage_output_ref=refs["output_ref"],
                    stage_output_digest=output_digest,
                    stage_output_size=output_size,
                    stage_proof_ref=refs["proof_ref"],
                    stage_proof_digest=refs["proof_digest"],
                    initial_semantics=self._initial_semantics_tx,
                    semantic_fingerprint=self._semantic_fingerprint,
                    insert_semantic=self._insert_revision_semantic,
                )

            return material, {"admission_result": admission}, callback


    async def _initial_semantics_tx(self, tx: UnitOfWork, state: Mapping[str, Any]) -> list[dict[str, Any]]:
            """Resolve the four S04 bootstrap semantics for an accepted Revision.

            The source descriptor itself remains an immutable S05 artifact.  The
            Revision keeps only compact, typed canonical values that participate
            in its business fingerprint, so rebuild/model/index work cannot
            manufacture a new business revision merely by changing runtime data.
            """

            source_kind = state.get("source_kind")
            clean_digest = state.get("clean_digest")
            if not isinstance(source_kind, str) or not source_kind or not isinstance(clean_digest, str) or not clean_digest:
                raise MkbError("INTAKE_SEMANTICS_INPUT_INVALID", "Accepted intake lacks canonical semantic inputs", 422)
            filter_meta = state.get("filter_meta")
            context_meta = state.get("context_meta")
            values: list[tuple[str, str, bool | int | float | str]] = [
                ("source_representation", "text", source_kind),
                ("canonical_content", "text", clean_digest),
                ("context_metadata", "text", _json(context_meta) if isinstance(context_meta, Mapping) else "{}"),
                (
                    "filter_metadata",
                    "text",
                    _json(filter_meta) if isinstance(filter_meta, Mapping) else _json({"source_kind": source_kind}),
                ),
            ]
            if isinstance(filter_meta, Mapping):
                for semantic_key in ("realm", "type", "channel", "source_name"):
                    value = filter_meta.get(semantic_key)
                    if not isinstance(value, str) or not value:
                        raise MkbError("INTAKE_SEMANTICS_INPUT_INVALID", "Provider filter semantics are incomplete", 422)
                    values.append((semantic_key, "text", value))
                is_active = filter_meta.get("is_active")
                if isinstance(is_active, bool) or is_active not in {0, 1}:
                    raise MkbError("INTAKE_SEMANTICS_INPUT_INVALID", "Provider active semantic is invalid", 422)
                values.append(("is_active", "int", is_active))
                tags = context_meta.get("tags") if isinstance(context_meta, Mapping) else None
                if not isinstance(tags, list) or any(not isinstance(tag, str) for tag in tags):
                    raise MkbError("INTAKE_SEMANTICS_INPUT_INVALID", "Provider context tags are invalid", 422)
                values.append(("context_tags", "text", "\n".join(tags)))
            entries: list[dict[str, Any]] = []
            for semantic_key, value_kind, value in values:
                definition = await tx.fetchone(
                    "SELECT definition_version,definition_digest,value_kind,fingerprint_participation "
                    "FROM mkb_intake_semantic_definitions "
                    "WHERE semantic_key=? AND definition_version='v1'",
                    (semantic_key,),
                )
                if definition is None or definition["value_kind"] != value_kind:
                    raise MkbError("REGISTRY_NOT_FOUND", "Required intake semantic definition is unavailable", 503)
                entries.append(
                    {
                        "semantic_key": semantic_key,
                        "definition_version": definition["definition_version"],
                        "definition_digest": definition["definition_digest"],
                        "value_kind": value_kind,
                        "fingerprint_participation": bool(definition["fingerprint_participation"]),
                        "value": value,
                        "value_digest": self._semantic_value_digest(
                            semantic_key,
                            definition["definition_version"],
                            definition["definition_digest"],
                            value,
                        ),
                    }
                )
            return entries


    @staticmethod
    def _semantic_value_digest(
            semantic_key: str,
            definition_version: str,
            definition_digest: str,
            value: bool | int | float | str,
        ) -> str:
            return stable_digest(
                {
                    "semantic_key": semantic_key,
                    "definition_version": definition_version,
                    "definition_digest": definition_digest,
                    "value": value,
                }
            )


    @staticmethod
    def _semantic_fingerprint(entries: list[Mapping[str, Any]] | tuple[Mapping[str, Any], ...]) -> str:
            participating: list[Mapping[str, Any]] = []
            for entry in entries:
                participation = entry.get("fingerprint_participation")
                if type(participation) is not bool:
                    raise MkbError(
                        "METADATA_SEMANTICS_INVALID",
                        "Semantic fingerprint participation is unavailable",
                        422,
                    )
                if participation:
                    participating.append(entry)
            return stable_digest(
                [
                    (str(entry["semantic_key"]), str(entry["definition_version"]), str(entry["value_digest"]))
                    for entry in sorted(participating, key=lambda item: str(item["semantic_key"]))
                ]
            )


    async def _insert_revision_semantic(
            self,
            tx: UnitOfWork,
            team_uuid: str,
            revision_uuid: str,
            entry: Mapping[str, Any],
            now: str,
        ) -> None:
            kind = entry.get("value_kind")
            values = self._semantic_scalar(kind, entry.get("value"))
            storage_kind = self._semantic_storage_kind(kind)
            await tx.execute(
                "INSERT INTO mkb_intake_revision_semantics "
                "(team_uuid,intake_revision_uuid,semantic_key,definition_version,value_digest,value_kind,value_bool,value_int,"
                "value_real,value_text,value_artifact_uuid,created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?,?,?,?, '{}')",
                (
                    team_uuid,
                    revision_uuid,
                    entry["semantic_key"],
                    entry["definition_version"],
                    entry["value_digest"],
                    storage_kind,
                    values["value_bool"],
                    values["value_int"],
                    values["value_real"],
                    values["value_text"],
                    values["value_artifact_uuid"],
                    now,
                ),
            )
