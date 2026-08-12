"""Index rebuild planning, scope freeze, and source record validation."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest, uuid7
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _digest_bytes,
    _StageMaterial,
)


class IntakeIndexRebuildPlanMixin:
    """Index rebuild planning, scope freeze, and source record validation."""

    async def _index_rebuild(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            """Build and atomically promote a fresh S09 generation for a frozen scope.

            The rebuild deliberately copies only the already validated vector
            projection.  It does not invent an IntakeRevision, re-read mutable
            source content, or silently switch Layer A.  The callback re-reads and
            CASes every Item/pointer/proof coordinate before writing a new
            generation, so a stale scoped command can only fail closed.
            """

            scope = self._frozen_index_rebuild_scope(state, command.team_uuid)
            plans = await self._plan_index_rebuild(command.team_uuid, scope)
            # A generation artifact is a generation-scoped retrieval coordinate,
            # not just a catalog alias for the prior construct output.  Reusing
            # the old bytes would leave its embedded artifact UUID pointing at the
            # retired generation, which S10 correctly refuses to hydrate.  Build
            # and promote a fresh, direct projection document for every candidate
            # generation before the Process outcome is staged.  The callback only
            # catalogs/references those already-promoted immutable bytes together
            # with the pointer CAS, preserving the bytes-first S12/S13 boundary.
            rebuilt_projection_stats = await self._promote_rebuilt_projections(command.team_uuid, plans)
            next_state = {
                "request_intent": "index.rebuild",
                "operation_mode": "index_rebuild_noop" if not plans else "index_rebuild",
                "index_scope": scope,
                "index_rebuild_plans": plans,
                "team_uuid": command.team_uuid,
                "task_uuid": command.task_uuid,
                "trace_uuid": command.trace_uuid,
            }
            material = self._material(
                command,
                next_state,
                {
                    "index_rebuild_receipt": {
                        "scope": scope["scope"],
                        "target_count": len(scope["targets"]),
                        "rebuild_count": len(plans),
                        "target_set_digest": scope["target_set_digest"],
                        "promotions": [
                            {
                                "intake_item_uuid": plan["intake_item_uuid"],
                                "namespace_uuid": plan["namespace_uuid"],
                                "from_generation": plan["old_index_generation"],
                                "to_generation": plan["next_index_generation"],
                            }
                            for plan in plans
                        ],
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                await self._commit_index_rebuild(
                    tx,
                    command=command,
                    plans=plans,
                    rebuilt_projection_stats=rebuilt_projection_stats,
                    refs=refs,
                )

            return material, {}, callback


    async def _promote_rebuilt_projections(
            self,
            team_uuid: str,
            plans: list[Mapping[str, Any]],
        ) -> dict[str, ObjectStat]:
            """Materialize an exact-coordinate projection for each new generation.

            Existing generation artifacts may be either the legacy construct stage
            envelope or a direct projection emitted by an earlier rebuild.  Both
            forms are normalized to the direct, self-describing projection format
            whose embedded UUID is the newly allocated generation coordinate.
            """

            promoted: dict[str, ObjectStat] = {}
            for plan in plans:
                source_handle = plan.get("source_artifact_handle")
                source_digest = plan.get("source_artifact_content_digest")
                source_size = plan.get("source_artifact_size_bytes")
                source_generation = plan.get("source_generation_artifact_uuid")
                next_generation = plan.get("generation_artifact_uuid")
                if not all(isinstance(value, str) and value for value in (source_handle, source_digest, source_generation, next_generation)):
                    raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection coordinate is unavailable", 409)
                if isinstance(source_size, bool) or not isinstance(source_size, int) or source_size < 0:
                    raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection size is invalid", 409)
                try:
                    source_bytes = await self._storage.read_verified(team_uuid, ObjectHandle(value=source_handle))
                except (TypeError, ValueError) as exc:
                    raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection handle is invalid", 409) from exc
                if len(source_bytes) != source_size or _digest_bytes(source_bytes) != source_digest:
                    raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection bytes do not match the ledger", 409)
                projection = self._rebuild_projection_from_source(
                    source_bytes,
                    source_generation_artifact_uuid=source_generation,
                )
                rebuilt_bytes = canonical_json(
                    {
                        "schema_version": "mkb.dual-channel-projection.v1",
                        "generation_artifact_uuid": next_generation,
                        "recipe_version": "content_full.v1",
                        "units": projection["units"],
                    }
                )
                promoted[next_generation] = await self._storage.promote(
                    rebuilt_bytes,
                    PromoteRequest(
                        team_uuid=team_uuid,
                        purpose="generation_artifact",
                        media_type="application/json",
                    ),
                )
            return promoted


    @staticmethod
    def _rebuild_projection_from_source(
            source_bytes: bytes,
            *,
            source_generation_artifact_uuid: str,
        ) -> dict[str, Any]:
            """Extract the immutable dual-channel payload without weakening S10.

            This accepts only the two artifact shapes which S10 itself recognizes.
            It intentionally does not copy a stage envelope, because its state
            coordinate necessarily names the source generation rather than the
            candidate generation being rebuilt.
            """

            try:
                document = json.loads(source_bytes)
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection is not valid JSON", 409) from exc
            if not isinstance(document, dict):
                raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection has an invalid shape", 409)
            projection: object
            if document.get("schema_version") == "mkb.dual-channel-projection.v1":
                if (
                    document.get("generation_artifact_uuid") != source_generation_artifact_uuid
                    or document.get("recipe_version") != "content_full.v1"
                ):
                    raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection coordinate is invalid", 409)
                projection = document
            elif document.get("schema_version") == "mkb.stage-output.v1":
                state = document.get("state")
                output = document.get("output")
                if (
                    document.get("process_key") != "lsrag.construct"
                    or not isinstance(state, dict)
                    or state.get("dual_channel_artifact_uuid") != source_generation_artifact_uuid
                    or not isinstance(output, dict)
                ):
                    raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source construct envelope is invalid", 409)
                package = output.get("construct_package")
                if not isinstance(package, dict) or package.get("content_full") is not True:
                    raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source construct package is incomplete", 409)
                projection = package.get("dual_channel")
                if projection != state.get("dual_channel"):
                    raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source construct package is inconsistent", 409)
            else:
                raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection schema is unsupported", 409)
            if (
                not isinstance(projection, dict)
                or projection.get("schema_version") != "mkb.dual-channel-projection.v1"
                or not isinstance(projection.get("units"), list)
            ):
                raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Source projection content is invalid", 409)
            # The exact channel/unit validation remains enforced at S10 hydration;
            # this check makes malformed source plans fail before pointer mutation.
            return {"units": projection["units"]}


    @staticmethod
    def _frozen_index_rebuild_scope(state: Mapping[str, Any], team_uuid: str) -> dict[str, Any]:
            context = state.get("intent_context")
            scope = context.get("scope") if isinstance(context, Mapping) else None
            if (
                not isinstance(scope, Mapping)
                or scope.get("schema_version") != "mkb.frozen-index-rebuild-scope.v1"
                or scope.get("team_uuid") != team_uuid
                or scope.get("scope") not in {"team", "intake_item"}
                or not isinstance(scope.get("target_set_digest"), str)
            ):
                raise MkbError("INDEX_REBUILD_SCOPE_INVALID", "Frozen index rebuild scope is unavailable", 422)
            raw_targets = scope.get("targets")
            if not isinstance(raw_targets, list):
                raise MkbError("INDEX_REBUILD_SCOPE_INVALID", "Frozen index rebuild scope is invalid", 422)
            targets: list[tuple[str, str]] = []
            for target in raw_targets:
                if not isinstance(target, Mapping):
                    raise MkbError("INDEX_REBUILD_SCOPE_INVALID", "Frozen index rebuild target is invalid", 422)
                item_uuid = target.get("intake_item_uuid")
                revision_uuid = target.get("intake_revision_uuid")
                if not all(isinstance(value, str) and value for value in (item_uuid, revision_uuid)):
                    raise MkbError("INDEX_REBUILD_SCOPE_INVALID", "Frozen index rebuild target is invalid", 422)
                targets.append((item_uuid, revision_uuid))
            if targets != sorted(set(targets)):
                raise MkbError("INDEX_REBUILD_SCOPE_INVALID", "Frozen index rebuild targets are not canonical", 422)
            expected = stable_digest(
                {
                    "schema_version": "mkb.index-rebuild-target-set.v1",
                    "team_uuid": team_uuid,
                    "scope": scope["scope"],
                    "targets": tuple(targets),
                }
            )
            if scope["target_set_digest"] != expected:
                raise MkbError("INDEX_REBUILD_SCOPE_INVALID", "Frozen index rebuild scope digest is invalid", 422)
            return {
                "scope": scope["scope"],
                "targets": [
                    {"intake_item_uuid": item_uuid, "intake_revision_uuid": revision_uuid}
                    for item_uuid, revision_uuid in targets
                ],
                "target_set_digest": expected,
            }


    async def _plan_index_rebuild(self, team_uuid: str, scope: Mapping[str, Any]) -> list[dict[str, Any]]:
            """Read a bounded immutable plan; the callback repeats every fence."""

            plans: list[dict[str, Any]] = []
            async with self._persistence.transaction() as tx:
                for target in scope["targets"]:
                    item_uuid = target["intake_item_uuid"]
                    revision_uuid = target["intake_revision_uuid"]
                    item = await tx.fetchone(
                        "SELECT row_revision,lifecycle_state,latest_revision_uuid,serving_revision_uuid "
                        "FROM mkb_intake_items WHERE team_uuid=? AND intake_item_uuid=?",
                        (team_uuid, item_uuid),
                    )
                    if (
                        item is None
                        or item["lifecycle_state"] != "active"
                        or item["latest_revision_uuid"] != revision_uuid
                        or item["serving_revision_uuid"] != revision_uuid
                    ):
                        raise MkbError("INDEX_REBUILD_TARGET_STALE", "Frozen index rebuild target is no longer serving", 409)
                    pointers = await tx.fetchall(
                        "SELECT p.namespace_uuid,p.active_index_generation,p.pointer_row_revision,p.lifecycle_state,"
                        "p.last_proof_uuid,p.generation_artifact_uuid,n.embedding_model,n.embedding_model_key,"
                        "n.embedding_model_version,n.adapter_kind,n.dimension,n.status,n.deleted_at "
                        "FROM mkb_index_active_pointers AS p JOIN mkb_vector_namespaces AS n "
                        "ON n.namespace_uuid=p.namespace_uuid AND n.team_uuid=p.team_uuid "
                        "WHERE p.team_uuid=? AND p.intake_item_uuid=? AND p.lifecycle_state='active' "
                        "AND n.status='active' AND n.deleted_at IS NULL ORDER BY p.namespace_uuid",
                        (team_uuid, item_uuid),
                    )
                    if not pointers:
                        raise MkbError("INDEX_REBUILD_POINTER_MISSING", "Serving Intake item has no active index pointer", 409)
                    for pointer in pointers:
                        source = await self._index_rebuild_source_plan_tx(
                            tx,
                            team_uuid=team_uuid,
                            item_uuid=item_uuid,
                            revision_uuid=revision_uuid,
                            item=item,
                            pointer=pointer,
                        )
                        plans.append(source)
            return plans


    async def _index_rebuild_source_plan_tx(
            self,
            tx: UnitOfWork,
            *,
            team_uuid: str,
            item_uuid: str,
            revision_uuid: str,
            item: Mapping[str, Any],
            pointer: Mapping[str, Any],
        ) -> dict[str, Any]:
            proof = await tx.fetchone(
                "SELECT proof_uuid,generation_artifact_uuid,generation_artifact_type,embedding_model,embedding_model_key,"
                "embedding_model_version,adapter_kind,dimension,index_generation,expected_count,actual_count,matched_count,"
                "required_set_digest,actual_set_digest FROM mkb_publication_proofs "
                "WHERE proof_uuid=? AND team_uuid=? AND intake_item_uuid=? AND intake_revision_uuid=?",
                (pointer["last_proof_uuid"], team_uuid, item_uuid, revision_uuid),
            )
            if proof is None:
                raise MkbError("INDEX_REBUILD_SOURCE_PROOF_MISSING", "Active index pointer has no matching publication proof", 409)
            layer_a = {
                "model_key": pointer["embedding_model_key"],
                "model_version": pointer["embedding_model_version"],
                "adapter_kind": pointer["adapter_kind"],
                "dimension": pointer["dimension"],
            }
            if (
                pointer["generation_artifact_uuid"] is None
                or proof["generation_artifact_uuid"] != pointer["generation_artifact_uuid"]
                or proof["index_generation"] != pointer["active_index_generation"]
                or proof["generation_artifact_type"] != "dual_channel_projection"
                or any(
                    proof[key] != expected
                    for key, expected in (
                        ("embedding_model", pointer["embedding_model"]),
                        ("embedding_model_key", layer_a["model_key"]),
                        ("embedding_model_version", layer_a["model_version"]),
                        ("adapter_kind", layer_a["adapter_kind"]),
                        ("dimension", layer_a["dimension"]),
                    )
                )
            ):
                raise MkbError("INDEX_REBUILD_SOURCE_PROOF_INVALID", "Active publication proof does not match its pointer", 409)
            artifact = await tx.fetchone(
                "SELECT generation_artifact_uuid,artifact_type,intake_item_uuid,intake_revision_uuid,logical_handle,"
                "content_digest,size_bytes "
                "FROM mkb_generation_artifacts WHERE team_uuid=? AND generation_artifact_uuid=? "
                "AND artifact_type='dual_channel_projection' AND validation_disposition='full_valid'",
                (team_uuid, pointer["generation_artifact_uuid"]),
            )
            if (
                artifact is None
                or artifact["intake_item_uuid"] != item_uuid
                or artifact["intake_revision_uuid"] != revision_uuid
            ):
                raise MkbError("INDEX_REBUILD_SOURCE_ARTIFACT_INVALID", "Active projection artifact is unavailable", 409)
            records = await self._index_rebuild_records_tx(
                tx,
                team_uuid=team_uuid,
                item_uuid=item_uuid,
                revision_uuid=revision_uuid,
                namespace_uuid=pointer["namespace_uuid"],
                generation_artifact_uuid=pointer["generation_artifact_uuid"],
                index_generation=pointer["active_index_generation"],
            )
            self._validate_index_rebuild_source_records(records, proof=proof, layer_a=layer_a)
            return {
                "intake_item_uuid": item_uuid,
                "intake_revision_uuid": revision_uuid,
                "item_row_revision": item["row_revision"],
                "namespace_uuid": pointer["namespace_uuid"],
                "old_index_generation": pointer["active_index_generation"],
                "next_index_generation": int(pointer["active_index_generation"]) + 1,
                "pointer_row_revision": pointer["pointer_row_revision"],
                "source_proof_uuid": pointer["last_proof_uuid"],
                "source_generation_artifact_uuid": pointer["generation_artifact_uuid"],
                "source_artifact_handle": artifact["logical_handle"],
                "source_artifact_content_digest": artifact["content_digest"],
                "source_artifact_size_bytes": artifact["size_bytes"],
                "source_artifact_digest": stable_digest(
                    {
                        "generation_artifact_uuid": artifact["generation_artifact_uuid"],
                        "content_digest": artifact["content_digest"],
                        "size_bytes": artifact["size_bytes"],
                    }
                ),
                "source_record_count": len(records),
                "source_publication_set_digest": self._publication_record_set_digest(records),
                "source_record_integrity_digest": self._index_record_integrity_digest(records),
                "layer_a": layer_a,
                "generation_artifact_uuid": uuid7(),
                "publication_proof_uuid": uuid7(),
            }


    async def _index_rebuild_records_tx(
            self,
            tx: UnitOfWork,
            *,
            team_uuid: str,
            item_uuid: str,
            revision_uuid: str,
            namespace_uuid: str,
            generation_artifact_uuid: str,
            index_generation: int,
        ) -> list[dict[str, Any]]:
            return await tx.fetchall(
                "SELECT * FROM mkb_vector_records WHERE team_uuid=? AND intake_item_uuid=? AND intake_revision_uuid=? "
                "AND namespace_uuid=? AND generation_artifact_uuid=? AND index_generation=? "
                "AND publication_state='indexed' AND deleted_at IS NULL ORDER BY vector_record_uuid",
                (
                    team_uuid,
                    item_uuid,
                    revision_uuid,
                    namespace_uuid,
                    generation_artifact_uuid,
                    index_generation,
                ),
            )


    @staticmethod
    def _publication_record_set_digest(records: list[Mapping[str, Any]]) -> str:
            return stable_digest(sorted((str(row["vector_record_uuid"]), str(row["content_digest"])) for row in records))


    @staticmethod
    def _index_record_integrity_digest(records: list[Mapping[str, Any]]) -> str:
            return stable_digest(
                [
                    (
                        str(row["vector_record_uuid"]),
                        str(row["content_digest"]),
                        str(row.get("embedding_digest") or ""),
                        str(row["block_or_unit_id"]),
                        str(row["channel"]),
                        str(row["embedding_model_key"]),
                        str(row["embedding_model_version"]),
                        str(row["adapter_kind"]),
                        int(row["dimension"]),
                    )
                    for row in records
                ]
            )


    def _validate_index_rebuild_source_records(
            self,
            records: list[Mapping[str, Any]],
            *,
            proof: Mapping[str, Any],
            layer_a: Mapping[str, Any],
        ) -> None:
            if not records:
                raise MkbError("INDEX_REBUILD_SOURCE_RECORDS_MISSING", "Active index generation has no indexed vectors", 409)
            if any(
                row["generation_artifact_type"] != "dual_channel_projection"
                or row["embedding_model"] != layer_a["model_key"]
                or row["embedding_model_key"] != layer_a["model_key"]
                or row["embedding_model_version"] != layer_a["model_version"]
                or row["adapter_kind"] != layer_a["adapter_kind"]
                or row["dimension"] != layer_a["dimension"]
                for row in records
            ):
                raise MkbError("INDEX_REBUILD_SOURCE_LAYER_A_INVALID", "Active vector records drifted from their namespace", 409)
            actual_set = self._publication_record_set_digest(records)
            if (
                proof["expected_count"] != len(records)
                or proof["actual_count"] != len(records)
                or proof["matched_count"] != len(records)
                or proof["required_set_digest"] != actual_set
                or proof["actual_set_digest"] != actual_set
            ):
                raise MkbError("INDEX_REBUILD_SOURCE_PROOF_INVALID", "Active vector set no longer matches its publication proof", 409)

