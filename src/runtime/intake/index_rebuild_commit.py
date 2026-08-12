"""Index rebuild commit, projection catalog, and vector clone."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import ObjectStat
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _json,
)


class IntakeIndexRebuildCommitMixin:
    """Index rebuild commit, projection catalog, and vector clone."""

    async def _commit_index_rebuild(
            self,
            tx: UnitOfWork,
            *,
            command: ProcessCommand,
            plans: list[Mapping[str, Any]],
            rebuilt_projection_stats: Mapping[str, ObjectStat],
            refs: Mapping[str, str],
        ) -> None:
            if not plans:
                return
            action = await tx.fetchone(
                "SELECT definition_version FROM mkb_intake_action_definitions "
                "WHERE action_key='index_rebuild' AND definition_version='v1'",
            )
            if action is None:
                raise MkbError("INTAKE_ACTION_UNREGISTERED", "Index rebuild action is not registered", 503)
            for plan in plans:
                rebuilt_stat = rebuilt_projection_stats.get(str(plan["generation_artifact_uuid"]))
                if rebuilt_stat is None:
                    raise MkbError("INDEX_REBUILD_OUTPUT_MISSING", "Candidate projection bytes were not promoted", 409)
                item, pointer, artifact, proof, records = await self._revalidate_index_rebuild_plan_tx(
                    tx, command=command, plan=plan
                )
                now = utc_now()
                rebuilt_stored_object_uuid = await self._catalog_rebuilt_projection_object(
                    tx,
                    team_uuid=command.team_uuid,
                    stat=rebuilt_stat,
                    now=now,
                )
                await self._insert_rebuilt_generation_artifact(
                    tx,
                    command=command,
                    plan=plan,
                    artifact=artifact,
                    rebuilt_stat=rebuilt_stat,
                    rebuilt_stored_object_uuid=rebuilt_stored_object_uuid,
                    refs=refs,
                    now=now,
                )
                new_record_pairs, facet_keys = await self._clone_rebuilt_vector_records_tx(
                    tx,
                    command=command,
                    plan=plan,
                    records=records,
                    now=now,
                )
                actual_set_digest = stable_digest(sorted(new_record_pairs))
                await tx.execute(
                    "INSERT INTO mkb_publication_proofs "
                    "(proof_uuid,team_uuid,intake_item_uuid,intake_revision_uuid,execution_uuid,process_uuid,"
                    "generation_artifact_uuid,generation_artifact_type,namespace_uuid,embedding_model,embedding_model_key,"
                    "embedding_model_version,adapter_kind,dimension,index_generation,expected_count,actual_count,matched_count,"
                    "required_set_digest,actual_set_digest,command_input_digest,layer_a_json,layer_b_keys_echo_json,created_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'{}')",
                    (
                        plan["publication_proof_uuid"],
                        command.team_uuid,
                        plan["intake_item_uuid"],
                        plan["intake_revision_uuid"],
                        command.execution_uuid,
                        command.process_uuid,
                        plan["generation_artifact_uuid"],
                        "dual_channel_projection",
                        plan["namespace_uuid"],
                        plan["layer_a"]["model_key"],
                        plan["layer_a"]["model_key"],
                        plan["layer_a"]["model_version"],
                        plan["layer_a"]["adapter_kind"],
                        plan["layer_a"]["dimension"],
                        plan["next_index_generation"],
                        len(records),
                        len(records),
                        len(records),
                        actual_set_digest,
                        actual_set_digest,
                        command.command_input_digest,
                        _json(plan["layer_a"]),
                        _json(sorted(facet_keys)),
                        now,
                    ),
                )
                changed = await tx.execute(
                    "UPDATE mkb_index_active_pointers SET active_index_generation=?,candidate_index_generation=NULL,"
                    "lifecycle_state='active',last_proof_uuid=?,generation_artifact_uuid=?,"
                    "pointer_row_revision=pointer_row_revision+1,updated_at=? "
                    "WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=? AND lifecycle_state='active' "
                    "AND pointer_row_revision=? AND active_index_generation=? AND last_proof_uuid=? "
                    "AND generation_artifact_uuid=?",
                    (
                        plan["next_index_generation"],
                        plan["publication_proof_uuid"],
                        plan["generation_artifact_uuid"],
                        now,
                        command.team_uuid,
                        plan["intake_item_uuid"],
                        plan["namespace_uuid"],
                        plan["pointer_row_revision"],
                        plan["old_index_generation"],
                        plan["source_proof_uuid"],
                        plan["source_generation_artifact_uuid"],
                    ),
                )
                if changed.rowcount != 1:
                    raise MkbError("INDEX_REBUILD_POINTER_FENCE", "Active index pointer changed before promotion", 409)
                namespace = await tx.execute(
                    "UPDATE mkb_vector_namespaces SET index_generation=MAX(index_generation,?),updated_at=? "
                    "WHERE team_uuid=? AND namespace_uuid=? AND status='active' AND deleted_at IS NULL "
                    "AND embedding_model_key=? AND embedding_model_version=? AND adapter_kind=? AND dimension=?",
                    (
                        plan["next_index_generation"],
                        now,
                        command.team_uuid,
                        plan["namespace_uuid"],
                        plan["layer_a"]["model_key"],
                        plan["layer_a"]["model_version"],
                        plan["layer_a"]["adapter_kind"],
                        plan["layer_a"]["dimension"],
                    ),
                )
                if namespace.rowcount != 1:
                    raise MkbError("INDEX_REBUILD_NAMESPACE_FENCE", "Index namespace changed before promotion", 409)
                if self._index_retirement is not None:
                    # The old projection can only become removable after the
                    # pointer's compare-and-set has succeeded.  Recording its
                    # immutable grace deadline in this same transaction prevents
                    # a crash window between serving cutover and retirement.
                    await self._index_retirement.schedule_retirement_tx(
                        tx,
                        team_uuid=command.team_uuid,
                        intake_item_uuid=plan["intake_item_uuid"],
                        namespace_uuid=plan["namespace_uuid"],
                        retired_index_generation=int(plan["old_index_generation"]),
                        successor_index_generation=int(plan["next_index_generation"]),
                        expected_pointer_row_revision=int(plan["pointer_row_revision"]) + 1,
                        trace_uuid=command.trace_uuid,
                    )
                await tx.execute(
                    "INSERT INTO mkb_intake_item_transitions "
                    "(transition_uuid,team_uuid,intake_item_uuid,action_key,action_version,before_lifecycle,after_lifecycle,"
                    "before_latest_revision_uuid,after_latest_revision_uuid,before_serving_revision_uuid,after_serving_revision_uuid,"
                    "item_revision_before,item_revision_after,causation_task_uuid,causation_execution_uuid,causation_process_uuid,"
                    "proof_ref,proof_digest,transition_fence,occurred_at,payload_extra) "
                    "VALUES (?,?,?,'index_rebuild',?,'active','active',?,?,?, ?,?,?,?,?,?,?,?,?,?,'{}')",
                    (
                        uuid7(),
                        command.team_uuid,
                        plan["intake_item_uuid"],
                        action["definition_version"],
                        plan["intake_revision_uuid"],
                        plan["intake_revision_uuid"],
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
                            {
                                "index_rebuild_process": command.process_uuid,
                                "fencing_generation": command.fencing_generation,
                                "from_generation": plan["old_index_generation"],
                                "to_generation": plan["next_index_generation"],
                            }
                        ),
                        now,
                    ),
                )


    async def _revalidate_index_rebuild_plan_tx(
            self,
            tx: UnitOfWork,
            *,
            command: ProcessCommand,
            plan: Mapping[str, Any],
        ) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
            item = await tx.fetchone(
                "SELECT row_revision,lifecycle_state,latest_revision_uuid,serving_revision_uuid "
                "FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
                (command.team_uuid, plan["intake_item_uuid"]),
            )
            if (
                item is None
                or item["row_revision"] != plan["item_row_revision"]
                or item["lifecycle_state"] != "active"
                or item["latest_revision_uuid"] != plan["intake_revision_uuid"]
                or item["serving_revision_uuid"] != plan["intake_revision_uuid"]
            ):
                raise MkbError("INDEX_REBUILD_TARGET_STALE", "Frozen index rebuild target changed before promotion", 409)
            pointer = await tx.fetchone(
                "SELECT p.namespace_uuid,p.active_index_generation,p.pointer_row_revision,p.lifecycle_state,p.last_proof_uuid,"
                "p.generation_artifact_uuid,n.embedding_model,n.embedding_model_key,n.embedding_model_version,n.adapter_kind,"
                "n.dimension,n.status,n.deleted_at FROM mkb_index_active_pointers AS p JOIN mkb_vector_namespaces AS n "
                "ON n.namespace_uuid=p.namespace_uuid AND n.team_uuid=p.team_uuid "
                "WHERE p.team_uuid=? AND p.intake_item_uuid=? AND p.namespace_uuid=?",
                (command.team_uuid, plan["intake_item_uuid"], plan["namespace_uuid"]),
            )
            layer_a = plan["layer_a"]
            if (
                pointer is None
                or pointer["lifecycle_state"] != "active"
                or pointer["active_index_generation"] != plan["old_index_generation"]
                or pointer["pointer_row_revision"] != plan["pointer_row_revision"]
                or pointer["last_proof_uuid"] != plan["source_proof_uuid"]
                or pointer["generation_artifact_uuid"] != plan["source_generation_artifact_uuid"]
                or pointer["status"] != "active"
                or pointer["deleted_at"] is not None
                or pointer["embedding_model"] != layer_a["model_key"]
                or pointer["embedding_model_key"] != layer_a["model_key"]
                or pointer["embedding_model_version"] != layer_a["model_version"]
                or pointer["adapter_kind"] != layer_a["adapter_kind"]
                or pointer["dimension"] != layer_a["dimension"]
            ):
                raise MkbError("INDEX_REBUILD_POINTER_FENCE", "Active index pointer changed before promotion", 409)
            proof = await tx.fetchone(
                "SELECT * FROM mkb_publication_proofs WHERE proof_uuid=? AND team_uuid=? AND intake_item_uuid=? "
                "AND intake_revision_uuid=? AND namespace_uuid=? AND index_generation=? AND generation_artifact_uuid=?",
                (
                    plan["source_proof_uuid"],
                    command.team_uuid,
                    plan["intake_item_uuid"],
                    plan["intake_revision_uuid"],
                    plan["namespace_uuid"],
                    plan["old_index_generation"],
                    plan["source_generation_artifact_uuid"],
                ),
            )
            if proof is None:
                raise MkbError("INDEX_REBUILD_SOURCE_PROOF_MISSING", "Active publication proof changed before promotion", 409)
            artifact = await tx.fetchone(
                "SELECT * FROM mkb_generation_artifacts WHERE team_uuid=? AND generation_artifact_uuid=? "
                "AND artifact_type='dual_channel_projection' AND validation_disposition='full_valid'",
                (command.team_uuid, plan["source_generation_artifact_uuid"]),
            )
            if (
                artifact is None
                or artifact["intake_item_uuid"] != plan["intake_item_uuid"]
                or artifact["intake_revision_uuid"] != plan["intake_revision_uuid"]
                or stable_digest(
                    {
                        "generation_artifact_uuid": artifact["generation_artifact_uuid"],
                        "content_digest": artifact["content_digest"],
                        "size_bytes": artifact["size_bytes"],
                    }
                )
                != plan["source_artifact_digest"]
            ):
                raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection artifact changed before promotion", 409)
            records = await self._index_rebuild_records_tx(
                tx,
                team_uuid=command.team_uuid,
                item_uuid=plan["intake_item_uuid"],
                revision_uuid=plan["intake_revision_uuid"],
                namespace_uuid=plan["namespace_uuid"],
                generation_artifact_uuid=plan["source_generation_artifact_uuid"],
                index_generation=plan["old_index_generation"],
            )
            self._validate_index_rebuild_source_records(records, proof=proof, layer_a=layer_a)
            if (
                len(records) != plan["source_record_count"]
                or self._publication_record_set_digest(records) != plan["source_publication_set_digest"]
                or self._index_record_integrity_digest(records) != plan["source_record_integrity_digest"]
            ):
                raise MkbError("INDEX_REBUILD_SOURCE_RECORDS_CHANGED", "Source vector set changed before promotion", 409)
            return item, pointer, artifact, proof, records


    async def _catalog_rebuilt_projection_object(
            self,
            tx: UnitOfWork,
            *,
            team_uuid: str,
            stat: ObjectStat,
            now: str,
        ) -> str:
            """Make a bytes-first rebuild projection durable in the S13 catalog."""

            existing = await tx.fetchone(
                "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=? AND size_bytes=?",
                (team_uuid, stat.sha256, stat.size_bytes),
            )
            if existing is not None:
                return str(existing["stored_object_uuid"])
            stored_object_uuid = uuid7()
            await tx.execute(
                "INSERT INTO mkb_stored_objects "
                "(stored_object_uuid,team_uuid,digest_algorithm,content_digest,size_bytes,media_type,storage_backend,"
                "created_at,payload_extra) VALUES (?,?, 'sha256',?,?,?,?,?,'{}')",
                (
                    stored_object_uuid,
                    team_uuid,
                    stat.sha256,
                    stat.size_bytes,
                    stat.media_type,
                    "local_fs",
                    now,
                ),
            )
            return stored_object_uuid


    async def _insert_rebuilt_generation_artifact(
            self,
            tx: UnitOfWork,
            *,
            command: ProcessCommand,
            plan: Mapping[str, Any],
            artifact: Mapping[str, Any],
            rebuilt_stat: ObjectStat,
            rebuilt_stored_object_uuid: str,
            refs: Mapping[str, str],
            now: str,
        ) -> None:
            columns = (
                "generation_artifact_uuid",
                "team_uuid",
                "artifact_type",
                "artifact_ordinal",
                "task_uuid",
                "execution_uuid",
                "process_uuid",
                "process_attempt",
                "intake_item_uuid",
                "intake_revision_uuid",
                "clean_artifact_uuid",
                "clean_artifact_digest",
                "schema_key",
                "schema_version",
                "schema_digest",
                "profile_key",
                "profile_version",
                "profile_digest",
                "model_key",
                "model_version",
                "prompt_key",
                "prompt_version",
                "prompt_digest",
                "process_fence",
                "logical_handle",
                "media_type",
                "size_bytes",
                "digest_algorithm",
                "content_digest",
                "stored_object_uuid",
                "validation_disposition",
                "validation_report_ref",
                "validation_report_digest",
                "proof_ref",
                "proof_digest",
                "predecessor_generation_artifact_uuid",
                "repair_causation_ref",
                "created_at",
                "payload_extra",
            )
            values = (
                plan["generation_artifact_uuid"],
                command.team_uuid,
                "dual_channel_projection",
                artifact["artifact_ordinal"],
                command.task_uuid,
                command.execution_uuid,
                command.process_uuid,
                command.fencing_generation,
                plan["intake_item_uuid"],
                plan["intake_revision_uuid"],
                artifact["clean_artifact_uuid"],
                artifact["clean_artifact_digest"],
                artifact["schema_key"],
                artifact["schema_version"],
                artifact["schema_digest"],
                artifact["profile_key"],
                artifact["profile_version"],
                artifact["profile_digest"],
                artifact["model_key"],
                artifact["model_version"],
                artifact["prompt_key"],
                artifact["prompt_version"],
                artifact["prompt_digest"],
                stable_digest({"process_uuid": command.process_uuid, "fence": command.fencing_generation}),
                rebuilt_stat.handle.value,
                rebuilt_stat.media_type or "application/json",
                rebuilt_stat.size_bytes,
                "sha256",
                rebuilt_stat.sha256,
                rebuilt_stored_object_uuid,
                "full_valid",
                artifact["validation_report_ref"],
                artifact["validation_report_digest"],
                refs["proof_ref"],
                refs["proof_digest"],
                artifact["generation_artifact_uuid"],
                f"index-rebuild:{command.process_uuid}",
                now,
                "{}",
            )
            await tx.execute(
                f"INSERT INTO mkb_generation_artifacts ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                values,
            )
            await self._reference_object(
                tx,
                team_uuid=command.team_uuid,
                stored_object_uuid=rebuilt_stored_object_uuid,
                purpose="generation_artifact",
                owner_kind="generation_artifact",
                owner_uuid=plan["generation_artifact_uuid"],
                digest=rebuilt_stat.sha256,
                size=rebuilt_stat.size_bytes,
            )


    async def _clone_rebuilt_vector_records_tx(
            self,
            tx: UnitOfWork,
            *,
            command: ProcessCommand,
            plan: Mapping[str, Any],
            records: list[Mapping[str, Any]],
            now: str,
        ) -> tuple[list[tuple[str, str]], set[str]]:
            columns = (
                "vector_record_uuid",
                "team_uuid",
                "namespace_uuid",
                "generation_artifact_uuid",
                "generation_artifact_type",
                "block_or_unit_id",
                "channel",
                "intake_source_uuid",
                "intake_item_uuid",
                "intake_revision_uuid",
                "task_uuid",
                "execution_uuid",
                "industry_domain",
                "content_digest_algorithm",
                "content_digest",
                "source_handle",
                "content_char_length",
                "embedding_model",
                "embedding_model_key",
                "embedding_model_version",
                "adapter_kind",
                "dimension",
                "embedding",
                "embedding_digest",
                "publication_state",
                "index_generation",
                "deleted_at",
                "outbox_dedupe_key",
                "embedded_at",
                "created_at",
                "updated_at",
                "payload_extra",
            )
            source_to_new: dict[str, str] = {}
            pairs: list[tuple[str, str]] = []
            for record in records:
                new_uuid = uuid7()
                source_to_new[str(record["vector_record_uuid"])] = new_uuid
                pairs.append((new_uuid, str(record["content_digest"])))
                await tx.execute(
                    f"INSERT INTO mkb_vector_records ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
                    (
                        new_uuid,
                        command.team_uuid,
                        plan["namespace_uuid"],
                        plan["generation_artifact_uuid"],
                        "dual_channel_projection",
                        record["block_or_unit_id"],
                        record["channel"],
                        record["intake_source_uuid"],
                        plan["intake_item_uuid"],
                        plan["intake_revision_uuid"],
                        command.task_uuid,
                        command.execution_uuid,
                        record["industry_domain"],
                        record["content_digest_algorithm"],
                        record["content_digest"],
                        record["source_handle"],
                        record["content_char_length"],
                        record["embedding_model"],
                        record["embedding_model_key"],
                        record["embedding_model_version"],
                        record["adapter_kind"],
                        record["dimension"],
                        record["embedding"],
                        record["embedding_digest"],
                        "indexed",
                        plan["next_index_generation"],
                        None,
                        None,
                        now,
                        now,
                        now,
                        _json({"rebuild_source_vector_record_uuid": record["vector_record_uuid"]}),
                    ),
                )
            placeholders = ",".join("?" for _ in source_to_new)
            facets = await tx.fetchall(
                "SELECT vector_record_uuid,facet_key,facet_value,definition_version,definition_digest "
                f"FROM mkb_vector_record_facets WHERE team_uuid=? AND vector_record_uuid IN ({placeholders}) "
                "ORDER BY vector_record_uuid,facet_key",
                (command.team_uuid, *source_to_new),
            )
            facet_keys: set[str] = set()
            for facet in facets:
                facet_keys.add(str(facet["facet_key"]))
                await tx.execute(
                    "INSERT INTO mkb_vector_record_facets "
                    "(facet_uuid,vector_record_uuid,team_uuid,facet_key,facet_value,definition_version,definition_digest,"
                    "created_at,payload_extra) VALUES (?,?,?,?,?,?,?,?, '{}')",
                    (
                        uuid7(),
                        source_to_new[str(facet["vector_record_uuid"])],
                        command.team_uuid,
                        facet["facet_key"],
                        facet["facet_value"],
                        facet["definition_version"],
                        facet["definition_digest"],
                        now,
                    ),
                )
            return pairs, facet_keys

