"""S09 publish handoff fence, namespace, and vector upserts."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.vector.models import VectorizeCommand, VectorizeHandoffV1, VectorizeOutcome
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _digest_bytes,
    _json,
    _StageMaterial,
)
from src.services.intake_lifecycle import IntakePublicationCommand


class IntakeVectorPublishCommitMixin:
    """S09 publish handoff fence, namespace, and vector upserts."""

    async def _publish(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            if self._lifecycle is None:
                raise MkbError("INTAKE_LIFECYCLE_UNAVAILABLE", "Lifecycle publication service is unavailable", 503)
            records = state.get("vector_records")
            if not isinstance(records, list) or not records:
                raise MkbError("PUBLICATION_VECTOR_MISSING", "Vectorization receipt is unavailable", 409)
            required = ("namespace_uuid", "index_generation", "dual_channel_artifact_uuid", "publication_proof_uuid")
            if any(state.get(key) is None for key in required):
                raise MkbError("PUBLICATION_INPUT_INVALID", "Publication input lacks immutable coordinates", 422)
            layer_a = self._layer_a_from_state(state)
            self._assert_vectorize_handoff_for_publication(command, state, records, layer_a)
            required_set_digest = stable_digest(
                sorted((record["vector_record_uuid"], record["content_digest"]) for record in records)
            )
            next_state = dict(state)
            next_state["publication_required_set_digest"] = required_set_digest
            material = self._material(
                command,
                next_state,
                {
                    "publication_proof": {
                        "proof_uuid": state["publication_proof_uuid"],
                        "namespace_uuid": state["namespace_uuid"],
                        "index_generation": state["index_generation"],
                        "required_set_digest": required_set_digest,
                        "expected_count": len(records),
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                ids = tuple(record["vector_record_uuid"] for record in records)
                placeholders = ",".join("?" for _ in ids)
                fetched = await tx.fetchall(
                    "SELECT vector_record_uuid,content_digest,publication_state,index_generation FROM mkb_vector_records "
                    f"WHERE team_uuid=? AND vector_record_uuid IN ({placeholders}) "
                    "ORDER BY vector_record_uuid",
                    (command.team_uuid, *ids),
                )
                if len(fetched) != len(ids) or any(
                    row["publication_state"] != "withdrawn" or row["index_generation"] != state["index_generation"]
                    for row in fetched
                ):
                    raise MkbError("PUBLICATION_VECTOR_FENCE", "Vector record set is not publishable", 409)
                actual_set_digest = stable_digest(
                    sorted((row["vector_record_uuid"], row["content_digest"]) for row in fetched)
                )
                # The required/actual formulas deliberately share only immutable
                # vector identities + digest, avoiding a mutable rank or timestamp.
                expected_actual = stable_digest(
                    sorted((record["vector_record_uuid"], record["content_digest"]) for record in records)
                )
                if actual_set_digest != expected_actual:
                    raise MkbError("PUBLICATION_VECTOR_FENCE", "Vector record content set changed before publication", 409)
                now = utc_now()
                updated = await tx.execute(
                    "UPDATE mkb_vector_records SET publication_state='indexed',updated_at=? "
                    f"WHERE team_uuid=? AND vector_record_uuid IN ({placeholders}) AND publication_state='withdrawn'",
                    (now, command.team_uuid, *ids),
                )
                if updated.rowcount != len(ids):
                    raise MkbError("PUBLICATION_VECTOR_FENCE", "Vector records changed during publication", 409)
                await tx.execute(
                    "INSERT INTO mkb_publication_proofs "
                    "(proof_uuid,team_uuid,intake_item_uuid,intake_revision_uuid,execution_uuid,process_uuid,"
                    "generation_artifact_uuid,generation_artifact_type,namespace_uuid,embedding_model,embedding_model_key,"
                    "embedding_model_version,adapter_kind,dimension,index_generation,expected_count,actual_count,matched_count,"
                    "required_set_digest,actual_set_digest,command_input_digest,layer_a_json,layer_b_keys_echo_json,created_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
                    (
                        state["publication_proof_uuid"],
                        command.team_uuid,
                        state["intake_item_uuid"],
                        state["intake_revision_uuid"],
                        command.execution_uuid,
                        command.process_uuid,
                        state["dual_channel_artifact_uuid"],
                        "dual_channel_projection",
                        state["namespace_uuid"],
                        layer_a["model_key"],
                        layer_a["model_key"],
                        layer_a["model_version"],
                        layer_a["adapter_kind"],
                        layer_a["dimension"],
                        state["index_generation"],
                        len(ids),
                        len(ids),
                        len(ids),
                        required_set_digest,
                        actual_set_digest,
                        command.command_input_digest,
                        _json(layer_a),
                        _json(["source_kind"]),
                        now,
                    ),
                )
                pointer = await tx.fetchone(
                    "SELECT active_index_generation,pointer_row_revision FROM mkb_index_active_pointers "
                    "WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=?",
                    (command.team_uuid, state["intake_item_uuid"], state["namespace_uuid"]),
                )
                if pointer is None:
                    await tx.execute(
                        "INSERT INTO mkb_index_active_pointers "
                        "(team_uuid,intake_item_uuid,namespace_uuid,active_index_generation,pointer_row_revision,lifecycle_state,"
                        "last_proof_uuid,generation_artifact_uuid,updated_at,payload_extra) VALUES (?,?,?, ?,0,'active',?,?,?,'{}')",
                        (
                            command.team_uuid,
                            state["intake_item_uuid"],
                            state["namespace_uuid"],
                            state["index_generation"],
                            state["publication_proof_uuid"],
                            state["dual_channel_artifact_uuid"],
                            now,
                        ),
                    )
                else:
                    changed = await tx.execute(
                        "UPDATE mkb_index_active_pointers SET active_index_generation=?,candidate_index_generation=NULL,"
                        "lifecycle_state='active',last_proof_uuid=?,generation_artifact_uuid=?,pointer_row_revision=pointer_row_revision+1,"
                        "updated_at=? WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=? AND pointer_row_revision=?"
                        " AND active_index_generation < ?",
                        (
                            state["index_generation"],
                            state["publication_proof_uuid"],
                            state["dual_channel_artifact_uuid"],
                            now,
                            command.team_uuid,
                            state["intake_item_uuid"],
                            state["namespace_uuid"],
                            pointer["pointer_row_revision"],
                            state["index_generation"],
                        ),
                    )
                    if changed.rowcount != 1:
                        raise MkbError("PUBLICATION_POINTER_FENCE", "Active index pointer changed concurrently", 409)
                await tx.execute(
                    "UPDATE mkb_vector_namespaces SET index_generation=MAX(index_generation,?),updated_at=? "
                    "WHERE namespace_uuid=? AND team_uuid=? AND status='active'",
                    (state["index_generation"], now, state["namespace_uuid"], command.team_uuid),
                )
                await self._lifecycle.publish_revision_tx(
                    tx,
                    IntakePublicationCommand(
                        team_uuid=command.team_uuid,
                        intake_item_uuid=state["intake_item_uuid"],
                        intake_revision_uuid=state["intake_revision_uuid"],
                        publication_proof_uuid=state["publication_proof_uuid"],
                        namespace_uuid=state["namespace_uuid"],
                        index_generation=state["index_generation"],
                        trace_uuid=command.trace_uuid,
                        idempotency_key=stable_digest(
                            {
                                "process_uuid": command.process_uuid,
                                "fencing_generation": command.fencing_generation,
                                "publication_proof_uuid": state["publication_proof_uuid"],
                            }
                        ),
                        task_uuid=command.task_uuid,
                        execution_uuid=command.execution_uuid,
                        process_uuid=command.process_uuid,
                        proof_ref=refs["proof_ref"],
                        proof_digest=refs["proof_digest"],
                    ),
                )
                if (
                    pointer is not None
                    and self._index_retirement is not None
                    and int(pointer["active_index_generation"]) < int(state["index_generation"])
                ):
                    # A reactivated Item intentionally has no serving revision
                    # until this publication transition.  Record retirement only
                    # after that lifecycle-owned serving CAS, while remaining in
                    # the same Process outcome transaction as the pointer CAS.
                    await self._index_retirement.schedule_retirement_tx(
                        tx,
                        team_uuid=command.team_uuid,
                        intake_item_uuid=state["intake_item_uuid"],
                        namespace_uuid=state["namespace_uuid"],
                        retired_index_generation=int(pointer["active_index_generation"]),
                        successor_index_generation=int(state["index_generation"]),
                        expected_pointer_row_revision=int(pointer["pointer_row_revision"]) + 1,
                        trace_uuid=command.trace_uuid,
                    )

            return material, {}, callback


    @staticmethod
    def _assert_vectorize_handoff_for_publication(
            command: ProcessCommand,
            state: Mapping[str, Any],
            records: list[dict[str, Any]],
            layer_a: Mapping[str, Any],
        ) -> None:
            """Require the typed S08 write proof before S09 can publish it."""

            raw_handoff = state.get("vectorize_handoff")
            raw_outcome = state.get("vectorize_outcome")
            raw_vectorize_command = state.get("vectorize_command")
            if not isinstance(raw_handoff, Mapping) or not isinstance(raw_outcome, Mapping) or not isinstance(
                raw_vectorize_command, Mapping
            ):
                raise MkbError("PUBLICATION_HANDOFF_MISSING", "Publication requires a typed Vectorize handoff", 409)
            try:
                handoff = VectorizeHandoffV1.model_validate(dict(raw_handoff))
                outcome = VectorizeOutcome.model_validate(dict(raw_outcome))
                vectorize_command = VectorizeCommand.model_validate(dict(raw_vectorize_command))
            except (TypeError, ValueError) as exc:
                raise MkbError("PUBLICATION_HANDOFF_INVALID", "Vectorize handoff contracts are invalid", 409) from exc
            if (
                outcome.mode != "from_construct"
                or outcome.handoff != handoff
                or vectorize_command.mode != "from_construct"
                or handoff.team_uuid != command.team_uuid
                or handoff.execution_uuid != command.execution_uuid
                or handoff.command_input_digest != vectorize_command.command_input_digest
                or handoff.generation_artifact_uuid != state.get("dual_channel_artifact_uuid")
                or handoff.generation_content_digest != state.get("dual_channel_artifact_content_digest")
                or handoff.content_full_recipe_version != "content_full.v1"
                or handoff.namespace_uuid != state.get("namespace_uuid")
                or handoff.required_units != len(records)
                or handoff.succeeded_units != len(records)
                or handoff.failed_units != 0
                or vectorize_command.dual_channel_generation_artifact_uuid != handoff.generation_artifact_uuid
                or vectorize_command.dual_channel_content_digest != handoff.generation_content_digest
                or vectorize_command.namespace_uuid != handoff.namespace_uuid
                or vectorize_command.content_full_recipe_version != handoff.content_full_recipe_version
            ):
                raise MkbError("PUBLICATION_HANDOFF_INVALID", "Vectorize handoff does not bind the publishable record set", 409)
            handoff_layer_a = handoff.embedding_model_ref
            if any(
                getattr(handoff_layer_a, key) != layer_a.get(key)
                for key in ("model_key", "model_version", "adapter_kind", "dimension")
            ):
                raise MkbError("PUBLICATION_HANDOFF_INVALID", "Vectorize handoff Layer A differs from the record binding", 409)


    @staticmethod
    def _namespace_key(layer_a: Mapping[str, Any]) -> str:
        return (
            f"{layer_a['model_key']}|{layer_a['model_version']}|"
            f"{layer_a['adapter_kind']}|{layer_a['dimension']}"
        )

    async def _namespace_coordinates(self, team_uuid: str, layer_a: Mapping[str, Any]) -> tuple[str, int]:
            """Read the live namespace for this Layer A; generation is CAS'd in the outcome TX."""

            key = self._namespace_key(layer_a)
            async with self._persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT namespace_uuid,index_generation FROM mkb_vector_namespaces "
                    "WHERE team_uuid=? AND namespace_key=? AND status='active' AND deleted_at IS NULL",
                    (team_uuid, key),
                )
            if row is None:
                return uuid7(), 1
            return row["namespace_uuid"], int(row["index_generation"]) + 1


    async def _ensure_namespace(
            self,
            tx: UnitOfWork,
            team_uuid: str,
            namespace_uuid: str,
            layer_a: Mapping[str, Any],
        ) -> None:
            layer_a = self._validate_layer_a(layer_a)
            key = self._namespace_key(layer_a)
            row = await tx.fetchone(
                "SELECT namespace_uuid,embedding_model_key,embedding_model_version,adapter_kind,dimension "
                "FROM mkb_vector_namespaces WHERE team_uuid=? AND namespace_key=?",
                (team_uuid, key),
            )
            if row is not None:
                if row["namespace_uuid"] != namespace_uuid:
                    raise MkbError("VECTOR_NAMESPACE_BINDING_CONFLICT", "Namespace binding conflicts", 409)
                return
            model = await tx.fetchone(
                "SELECT model_key FROM mkb_model_catalog WHERE model_key=? AND model_version=? AND status='active'",
                (layer_a["model_key"], layer_a["model_version"]),
            )
            if model is None:
                raise MkbError("REGISTRY_NOT_FOUND", "Embedding model registry row is unavailable", 503)
            now = utc_now()
            await tx.execute(
                "INSERT INTO mkb_vector_namespaces "
                "(namespace_uuid,team_uuid,namespace_key,display_name,embedding_model,embedding_model_key,embedding_model_version,"
                "adapter_kind,dimension,distance_metric,status,index_generation,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,? ,?,?,?,?,?,'cosine',"
                "'active',0,?,?,'{}')",
                (
                    namespace_uuid,
                    team_uuid,
                    key,
                    key,
                    layer_a["model_key"],
                    layer_a["model_key"],
                    layer_a["model_version"],
                    layer_a["adapter_kind"],
                    layer_a["dimension"],
                    now,
                    now,
                ),
            )


    async def _existing_vector_coordinate_uuid(
            self,
            *,
            team_uuid: str,
            namespace_uuid: str,
            generation_artifact_uuid: str,
            unit_id: str,
            channel: str,
            embedding_model: str,
            index_generation: int,
        ) -> str | None:
            async with self._persistence.transaction() as tx:
                row = await tx.fetchone(
                    "SELECT vector_record_uuid FROM mkb_vector_records WHERE team_uuid=? AND namespace_uuid=? "
                    "AND generation_artifact_uuid=? AND block_or_unit_id=? AND channel=? AND embedding_model=? "
                    "AND index_generation=? AND publication_state='withdrawn' AND deleted_at IS NULL",
                    (
                        team_uuid,
                        namespace_uuid,
                        generation_artifact_uuid,
                        unit_id,
                        channel,
                        embedding_model,
                        index_generation,
                    ),
                )
            return None if row is None else str(row["vector_record_uuid"])


    async def _upsert_vector_record_tx(
            self,
            tx: UnitOfWork,
            *,
            command: ProcessCommand,
            state: Mapping[str, Any],
            namespace_uuid: str,
            index_generation: int,
            layer_a: Mapping[str, Any],
            record: Mapping[str, Any],
            embedding_blob: bytes,
        ) -> str:
            """Idempotently converge one required S08 coordinate inside the UoW."""

            planned_uuid = record.get("vector_record_uuid")
            unit_id = record.get("unit_id")
            channel = record.get("channel")
            content = record.get("content")
            content_digest = record.get("content_digest")
            if not all(isinstance(value, str) and value for value in (planned_uuid, unit_id, channel, content, content_digest)):
                raise MkbError("VECTORIZE_INPUT_INVALID", "Vectorization record is incomplete", 422)
            if channel not in {"original", "summary"}:
                raise MkbError("VECTORIZE_INPUT_INVALID", "Vectorization channel is invalid", 422)
            if stable_digest({"text": content}) != content_digest:
                raise MkbError("VECTORIZE_CONTENT_MISMATCH", "Vectorization content digest does not match the recomputed recipe", 409)
            artifact_uuid = self._generation_state_text(state, "dual_channel_artifact_uuid", "CONSTRUCT_TO_VECTORIZE_GATE")
            source_handle = self._generation_state_text(state, "dual_channel_artifact_ref", "CONSTRUCT_TO_VECTORIZE_GATE")
            existing = await tx.fetchone(
                "SELECT vector_record_uuid FROM mkb_vector_records WHERE team_uuid=? AND namespace_uuid=? "
                "AND generation_artifact_uuid=? AND block_or_unit_id=? AND channel=? AND embedding_model=? "
                "AND index_generation=? AND publication_state='withdrawn' AND deleted_at IS NULL",
                (
                    command.team_uuid,
                    namespace_uuid,
                    artifact_uuid,
                    unit_id,
                    channel,
                    layer_a["model_key"],
                    index_generation,
                ),
            )
            now = utc_now()
            if existing is not None:
                vector_record_uuid = str(existing["vector_record_uuid"])
                if vector_record_uuid != planned_uuid:
                    raise MkbError("VECTORIZE_COORDINATE_FENCE", "A vector coordinate was claimed by a different replay", 409)
                updated = await tx.execute(
                    "UPDATE mkb_vector_records SET intake_source_uuid=?,intake_item_uuid=?,intake_revision_uuid=?,task_uuid=?,"
                    "execution_uuid=?,content_digest=?,source_handle=?,content_char_length=?,embedding_model_key=?,"
                    "embedding_model_version=?,adapter_kind=?,dimension=?,embedding=?,embedding_digest=?,publication_state='withdrawn',"
                    "index_generation=?,outbox_dedupe_key=?,embedded_at=?,updated_at=? "
                    "WHERE team_uuid=? AND vector_record_uuid=? AND deleted_at IS NULL",
                    (
                        state["intake_source_uuid"],
                        state["intake_item_uuid"],
                        state["intake_revision_uuid"],
                        command.task_uuid,
                        command.execution_uuid,
                        content_digest,
                        source_handle,
                        len(content),
                        layer_a["model_key"],
                        layer_a["model_version"],
                        layer_a["adapter_kind"],
                        layer_a["dimension"],
                        embedding_blob,
                        _digest_bytes(embedding_blob),
                        index_generation,
                        stable_digest(
                            {
                                "generation_artifact_uuid": artifact_uuid,
                                "unit_id": unit_id,
                                "channel": channel,
                                "embedding_model": layer_a["model_key"],
                            }
                        ),
                        now,
                        now,
                        command.team_uuid,
                        vector_record_uuid,
                    ),
                )
                if updated.rowcount != 1:
                    raise MkbError("VECTORIZE_COORDINATE_FENCE", "Vector coordinate changed during its fenced update", 409)
                return vector_record_uuid
            await tx.execute(
                "INSERT INTO mkb_vector_records "
                "(vector_record_uuid,team_uuid,namespace_uuid,generation_artifact_uuid,generation_artifact_type,"
                "block_or_unit_id,channel,intake_source_uuid,intake_item_uuid,intake_revision_uuid,task_uuid,execution_uuid,"
                "content_digest,source_handle,content_char_length,embedding_model,embedding_model_key,embedding_model_version,"
                "adapter_kind,dimension,embedding,embedding_digest,publication_state,index_generation,outbox_dedupe_key,"
                "embedded_at,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'withdrawn',?,?,?,?,?, '{}')",
                (
                    planned_uuid,
                    command.team_uuid,
                    namespace_uuid,
                    artifact_uuid,
                    "dual_channel_projection",
                    unit_id,
                    channel,
                    state["intake_source_uuid"],
                    state["intake_item_uuid"],
                    state["intake_revision_uuid"],
                    command.task_uuid,
                    command.execution_uuid,
                    content_digest,
                    source_handle,
                    len(content),
                    layer_a["model_key"],
                    layer_a["model_key"],
                    layer_a["model_version"],
                    layer_a["adapter_kind"],
                    layer_a["dimension"],
                    embedding_blob,
                    _digest_bytes(embedding_blob),
                    index_generation,
                    stable_digest(
                        {
                            "generation_artifact_uuid": artifact_uuid,
                            "unit_id": unit_id,
                            "channel": channel,
                            "embedding_model": layer_a["model_key"],
                        }
                    ),
                    now,
                    now,
                    now,
                ),
            )
            return planned_uuid


    async def _upsert_vector_source_kind_facet_tx(
            self,
            tx: UnitOfWork,
            *,
            team_uuid: str,
            vector_record_uuid: str,
            source_kind: object,
        ) -> None:
            if not isinstance(source_kind, str) or not source_kind:
                raise MkbError("VECTORIZE_FILTER_BINDING", "Authoritative source kind is unavailable", 409)
            definition_digest = stable_digest({"facet": "source_kind", "version": "v1"})
            existing = await tx.fetchone(
                "SELECT facet_value,definition_version,definition_digest FROM mkb_vector_record_facets "
                "WHERE vector_record_uuid=? AND facet_key='source_kind'",
                (vector_record_uuid,),
            )
            if existing is None:
                await tx.execute(
                    "INSERT INTO mkb_vector_record_facets "
                    "(facet_uuid,vector_record_uuid,team_uuid,facet_key,facet_value,definition_version,definition_digest,"
                    "created_at,payload_extra) VALUES (?,?,?,?,?,'v1',?,?, '{}')",
                    (uuid7(), vector_record_uuid, team_uuid, "source_kind", source_kind, definition_digest, utc_now()),
                )
                return
            if (
                existing["facet_value"] != source_kind
                or existing["definition_version"] != "v1"
                or existing["definition_digest"] != definition_digest
            ):
                raise MkbError("VECTORIZE_FILTER_BINDING", "Authoritative source-kind facet conflicts with the coordinate", 409)

