"""Generation artifact promote/catalog/assert helpers (S06/S07 shared)."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _METADATA_REFRESH_REUSE_SUMMARIES,
    _METADATA_REFRESH_SOURCE_TYPES,
    ConstructMode,
    _digest_bytes,
    _GenerationArtifactMaterial,
    _is_sha256_digest,
)
from src.services.lsrag_compiler import (
    ConstructionDocument,
    DualChannelProjection,
    LsragContractCompiler,
    RetrievalBlockProjection,
    StructureDocument,
    construction_document_digest,
    projection_digest,
    structure_document_digest,
)
from src.services.lsrag_construct import LsragConstructService


class IntakeGenerationArtifactsMixin:
    """Generation artifact promote/catalog/assert helpers (S06/S07 shared)."""

    @staticmethod
    def _generation_state_text(state: Mapping[str, Any], key: str, error_code: str) -> str:
            value = state.get(key)
            if not isinstance(value, str) or not value:
                raise MkbError(error_code, f"Generation state is missing {key}", 409)
            return value


    def _generation_clean_text(self, state: Mapping[str, Any], *, error_code: str) -> str:
            clean = self._generation_state_text(state, "clean_text", error_code)
            declared = self._generation_state_text(state, "clean_digest", error_code)
            if stable_digest({"text": clean}) != declared:
                raise MkbError(error_code, "Selected clean text no longer matches its frozen digest", 409)
            return clean


    async def _promote_generation_member(
            self,
            command: ProcessCommand,
            *,
            artifact_uuid: str,
            artifact_type: str,
            payload: Mapping[str, Any],
        ) -> _GenerationArtifactMaterial:
            """Promote one generation member before the outcome transaction.

            Each S06/S07 artifact has its own bytes and own ledger row.  Promotion
            can therefore leave a harmless orphan when a later process fence loses;
            only the callback below makes a member business-visible.
            """

            declared_uuid = payload.get("generation_artifact_uuid")
            if declared_uuid != artifact_uuid:
                raise MkbError("GENERATION_ARTIFACT_BINDING", "Generation payload identity does not match its ledger key", 422)
            stat = await self._storage.promote(
                canonical_json(dict(payload)),
                PromoteRequest(team_uuid=command.team_uuid, purpose="generation_artifact", media_type="application/json"),
            )
            return _GenerationArtifactMaterial(artifact_uuid=artifact_uuid, artifact_type=artifact_type, stat=stat)


    @staticmethod
    def _generation_asset_receipt(
            asset: _GenerationArtifactMaterial,
            semantic_digest: str | None = None,
        ) -> dict[str, Any]:
            receipt: dict[str, Any] = {
                "generation_artifact_uuid": asset.artifact_uuid,
                "artifact_type": asset.artifact_type,
                "logical_handle": asset.stat.handle.value,
                "content_digest": asset.stat.sha256,
                "size_bytes": asset.stat.size_bytes,
            }
            if semantic_digest is not None:
                receipt["semantic_digest"] = semantic_digest
            return receipt


    @staticmethod
    def _structure_validation_report_payload(
            *,
            validation_artifact_uuid: str,
            structure: StructureDocument,
            projection: RetrievalBlockProjection,
        ) -> dict[str, Any]:
            structure_digest = structure_document_digest(structure)
            projection_value_digest = projection_digest(projection)
            return {
                "schema_version": "mkb.structure-validation-report.v1",
                "generation_artifact_uuid": validation_artifact_uuid,
                "disposition": "full_valid",
                "structure_generation_artifact_uuid": structure.generation_artifact_uuid,
                "structure_document_digest": structure_digest,
                "retrieval_block_projection_generation_artifact_uuid": projection.generation_artifact_uuid,
                "retrieval_block_projection_digest": projection_value_digest,
                "proof_digest": stable_digest(
                    {
                        "structure_document_digest": structure_digest,
                        "retrieval_block_projection_digest": projection_value_digest,
                        "disposition": "full_valid",
                    }
                ),
            }


    @staticmethod
    def _construction_validation_report_payload(
            *,
            validation_artifact_uuid: str,
            construction: ConstructionDocument,
            dual: DualChannelProjection,
        ) -> dict[str, Any]:
            construction_digest = construction_document_digest(construction)
            return {
                "schema_version": "mkb.construction-validation-report.v1",
                "generation_artifact_uuid": validation_artifact_uuid,
                "disposition": "full_valid",
                "construction_generation_artifact_uuid": construction.generation_artifact_uuid,
                "construction_document_digest": construction_digest,
                "dual_channel_generation_artifact_uuid": dual.generation_artifact_uuid,
                "dual_channel_proof_digest": dual.proof_digest,
                "proof_digest": stable_digest(
                    {
                        "construction_document_digest": construction_digest,
                        "dual_channel_generation_artifact_uuid": dual.generation_artifact_uuid,
                        "dual_channel_proof_digest": dual.proof_digest,
                        "disposition": "full_valid",
                    }
                ),
            }


    async def _read_frozen_generation_asset(
            self,
            command: ProcessCommand,
            state: Mapping[str, Any],
            *,
            artifact_uuid_key: str,
            logical_handle_key: str,
            content_digest_key: str,
            size_bytes_key: str,
            error_code: str,
        ) -> bytes:
            artifact_uuid = self._generation_state_text(state, artifact_uuid_key, error_code)
            logical_handle = self._generation_state_text(state, logical_handle_key, error_code)
            digest = self._generation_state_text(state, content_digest_key, error_code)
            size = state.get(size_bytes_key)
            if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                raise MkbError(error_code, "Generation artifact has an invalid declared size", 409)
            try:
                data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=logical_handle))
            except (TypeError, ValueError) as exc:
                raise MkbError(error_code, "Generation artifact handle is invalid", 409) from exc
            if len(data) != size or _digest_bytes(data) != digest:
                raise MkbError(error_code, "Generation artifact bytes no longer match their frozen receipt", 409)
            # The UUID is checked here as an inexpensive binder before a caller
            # compares the full canonical payload it expects from the compiler.
            try:
                decoded = json.loads(data)
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise MkbError(error_code, "Generation artifact is not deterministic JSON", 409) from exc
            if not isinstance(decoded, dict) or decoded.get("generation_artifact_uuid") != artifact_uuid:
                raise MkbError(error_code, "Generation artifact identity does not match its frozen receipt", 409)
            return data


    @staticmethod
    def _construct_mode(state: Mapping[str, Any]) -> ConstructMode:
            mode = state.get("construct_mode")
            if mode is None:
                # Pre-refresh executions and the normal S06→S07 path retain their
                # historical full-construct interpretation.
                return "full_construct"
            if mode in {"full_construct", "metadata_refresh"}:
                return mode
            raise MkbError("CONSTRUCT_MODE_INVALID", "Construction mode is not registered", 409)


    def _metadata_refresh_headers_from_state(self, state: Mapping[str, Any]) -> dict[str, str]:
            if self._construct_mode(state) != "metadata_refresh":
                raise MkbError("METADATA_REFRESH_MODE_INVALID", "Construction is not in metadata refresh mode", 409)
            if state.get("metadata_refresh_mode") != _METADATA_REFRESH_REUSE_SUMMARIES:
                raise MkbError("METADATA_REFRESH_MODE_INVALID", "Metadata refresh summary behavior is not registered", 409)
            fingerprint = state.get("metadata_fingerprint")
            merged = state.get("metadata_merged_semantics")
            declared = state.get("metadata_refresh_headers")
            if not isinstance(fingerprint, str) or not isinstance(merged, Mapping) or not isinstance(declared, Mapping):
                raise MkbError("METADATA_PROJECTION_INVALID", "Metadata projection state is incomplete", 409)
            expected = self._metadata_refresh_headers(merged, fingerprint)
            if dict(declared) != expected:
                raise MkbError("METADATA_PROJECTION_INVALID", "Metadata projection does not match the accepted revision", 409)
            return expected


    @staticmethod
    def _metadata_refresh_source_state(state: Mapping[str, Any]) -> dict[str, Any]:
            source = state.get("metadata_refresh_source")
            if not isinstance(source, Mapping) or source.get("schema_version") != "mkb.metadata-refresh-source.v1":
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Frozen metadata refresh source is unavailable", 409)
            required = (
                "source_execution_uuid",
                "source_task_uuid",
                "source_intake_revision_uuid",
                "source_clean_artifact_uuid",
                "source_clean_digest",
                "source_construction_generation_artifact_uuid",
            )
            if any(not isinstance(source.get(key), str) or not source[key] for key in required):
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Frozen metadata refresh source is incomplete", 409)
            members = source.get("members")
            if not isinstance(members, Mapping) or set(members) != set(_METADATA_REFRESH_SOURCE_TYPES):
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Frozen metadata refresh family is incomplete", 409)
            for artifact_type in _METADATA_REFRESH_SOURCE_TYPES:
                receipt = members.get(artifact_type)
                if (
                    not isinstance(receipt, Mapping)
                    or not isinstance(receipt.get("generation_artifact_uuid"), str)
                    or not receipt["generation_artifact_uuid"]
                    or not isinstance(receipt.get("logical_handle"), str)
                    or not receipt["logical_handle"]
                    or not _is_sha256_digest(receipt.get("content_digest"))
                    or isinstance(receipt.get("size_bytes"), bool)
                    or not isinstance(receipt.get("size_bytes"), int)
                    or receipt["size_bytes"] < 0
                ):
                    raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Frozen generation receipt is invalid", 409)
            construction = members["construction_document"]
            assert isinstance(construction, Mapping)
            if source["source_construction_generation_artifact_uuid"] != construction["generation_artifact_uuid"]:
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Source construction identity is inconsistent", 409)
            return dict(source)


    async def _read_metadata_refresh_member(
            self,
            command: ProcessCommand,
            receipt: Mapping[str, Any],
            *,
            error_code: str,
        ) -> bytes:
            """Read one nested frozen receipt through the common object fence."""

            return await self._read_frozen_generation_asset(
                command,
                {
                    "artifact_uuid": receipt.get("generation_artifact_uuid"),
                    "logical_handle": receipt.get("logical_handle"),
                    "content_digest": receipt.get("content_digest"),
                    "size_bytes": receipt.get("size_bytes"),
                },
                artifact_uuid_key="artifact_uuid",
                logical_handle_key="logical_handle",
                content_digest_key="content_digest",
                size_bytes_key="size_bytes",
                error_code=error_code,
            )


    async def _assert_metadata_refresh_source(
            self,
            command: ProcessCommand,
            state: Mapping[str, Any],
        ) -> dict[str, Any]:
            """Recheck the exact source family before reusing any summaries."""

            source = self._metadata_refresh_source_state(state)
            target = state.get("frozen_target")
            if not isinstance(target, Mapping) or not isinstance(target.get("clean_artifact"), Mapping):
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Metadata refresh target is unavailable", 409)
            source_revision_uuid = source["source_intake_revision_uuid"]
            source_clean_artifact_uuid = source["source_clean_artifact_uuid"]
            source_clean_digest = source["source_clean_digest"]
            if (
                target.get("intake_revision_uuid") != source_revision_uuid
                or target["clean_artifact"].get("intake_artifact_uuid") != source_clean_artifact_uuid
                or target["clean_artifact"].get("content_digest") != source_clean_digest
                or state.get("intake_item_uuid") != target.get("intake_item_uuid")
                or state.get("clean_digest") != source_clean_digest
            ):
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Metadata refresh source does not bind the selected clean revision", 409)
            members = source["members"]
            assert isinstance(members, Mapping)
            async with self._persistence.transaction() as tx:
                for artifact_type in _METADATA_REFRESH_SOURCE_TYPES:
                    receipt = members[artifact_type]
                    assert isinstance(receipt, Mapping)
                    artifact = await tx.fetchone(
                        "SELECT logical_handle,content_digest,size_bytes,validation_disposition,execution_uuid,task_uuid,"
                        "intake_item_uuid,intake_revision_uuid,clean_artifact_uuid,clean_artifact_digest "
                        "FROM mkb_generation_artifacts WHERE team_uuid=? AND generation_artifact_uuid=? AND artifact_type=?",
                        (command.team_uuid, receipt["generation_artifact_uuid"], artifact_type),
                    )
                    if (
                        artifact is None
                        or artifact["logical_handle"] != receipt["logical_handle"]
                        or artifact["content_digest"] != receipt["content_digest"]
                        or artifact["size_bytes"] != receipt["size_bytes"]
                        or artifact["validation_disposition"] != "full_valid"
                        or artifact["execution_uuid"] != source["source_execution_uuid"]
                        or artifact["task_uuid"] != source["source_task_uuid"]
                        or artifact["intake_item_uuid"] != target.get("intake_item_uuid")
                        or artifact["intake_revision_uuid"] != source_revision_uuid
                        or artifact["clean_artifact_uuid"] != source_clean_artifact_uuid
                        or artifact["clean_artifact_digest"] != source_clean_digest
                    ):
                        raise MkbError(
                            "METADATA_REFRESH_SOURCE_INVALID",
                            "Source generation ledger no longer matches the frozen metadata refresh receipt",
                            409,
                        )
                    pointer = await tx.fetchone(
                        "SELECT current_generation_artifact_uuid FROM mkb_generation_pointers "
                        "WHERE team_uuid=? AND execution_uuid=? AND artifact_type=?",
                        (command.team_uuid, source["source_execution_uuid"], artifact_type),
                    )
                    if pointer is None or pointer["current_generation_artifact_uuid"] != receipt["generation_artifact_uuid"]:
                        raise MkbError(
                            "METADATA_REFRESH_SOURCE_INVALID",
                            "Source generation member is no longer its accepted current artifact",
                            409,
                        )
            return source


    async def _assert_generation_members(
            self,
            command: ProcessCommand,
            state: Mapping[str, Any],
            members: tuple[tuple[str, str, str, str, str], ...],
            *,
            error_code: str,
        ) -> None:
            async with self._persistence.transaction() as tx:
                await self._assert_generation_members_tx(tx, command, state, members, error_code=error_code)


    async def _assert_generation_members_tx(
            self,
            tx: UnitOfWork,
            command: ProcessCommand,
            state: Mapping[str, Any],
            members: tuple[tuple[str, str, str, str, str], ...],
            *,
            error_code: str,
        ) -> None:
            """Recheck exact current artifacts, not merely a stage-envelope hint."""

            for artifact_type, uuid_key, handle_key, digest_key, size_key in members:
                artifact_uuid = self._generation_state_text(state, uuid_key, error_code)
                handle = self._generation_state_text(state, handle_key, error_code)
                digest = self._generation_state_text(state, digest_key, error_code)
                size = state.get(size_key)
                if isinstance(size, bool) or not isinstance(size, int) or size < 0:
                    raise MkbError(error_code, "Generation artifact size receipt is invalid", 409)
                artifact = await tx.fetchone(
                    "SELECT logical_handle,content_digest,size_bytes,validation_disposition,execution_uuid,task_uuid "
                    "FROM mkb_generation_artifacts WHERE team_uuid=? AND generation_artifact_uuid=? AND artifact_type=?",
                    (command.team_uuid, artifact_uuid, artifact_type),
                )
                if (
                    artifact is None
                    or artifact["logical_handle"] != handle
                    or artifact["content_digest"] != digest
                    or artifact["size_bytes"] != size
                    or artifact["validation_disposition"] != "full_valid"
                    or artifact["execution_uuid"] != command.execution_uuid
                    or artifact["task_uuid"] != command.task_uuid
                ):
                    raise MkbError(error_code, "Generation artifact ledger no longer matches the frozen handoff", 409)
                pointer = await tx.fetchone(
                    "SELECT current_generation_artifact_uuid FROM mkb_generation_pointers "
                    "WHERE team_uuid=? AND execution_uuid=? AND artifact_type=?",
                    (command.team_uuid, command.execution_uuid, artifact_type),
                )
                if pointer is None or pointer["current_generation_artifact_uuid"] != artifact_uuid:
                    raise MkbError(error_code, "Generation artifact is no longer the accepted current member", 409)


    async def _reconstruct_structure_contract(
            self,
            command: ProcessCommand,
            state: Mapping[str, Any],
        ) -> tuple[LsragContractCompiler, StructureDocument, RetrievalBlockProjection]:
            """Load and re-prove the exact S06 handoff before construction."""

            clean = self._generation_clean_text(state, error_code="CONSTRUCT_BINDING_CLEAN_DIGEST")
            clean_artifact_uuid = self._generation_state_text(state, "clean_artifact_uuid", "CONSTRUCT_BINDING_CLEAN_ARTIFACT")
            structure_uuid = self._generation_state_text(state, "structure_artifact_uuid", "CONSTRUCT_BINDING_STRUCTURE_MISSING")
            projection_uuid = self._generation_state_text(
                state, "retrieval_block_projection_artifact_uuid", "CONSTRUCT_BINDING_PROJECTION_MISSING"
            )
            layered_candidate = self._layered_state_candidate(state, error_code="CONSTRUCT_BINDING_CANDIDATE_MISSING")
            profile = self._layered_profile(state, error_code="CONSTRUCT_BINDING_PROFILE_INVALID")
            construct_service = LsragConstructService()
            compiler, structure, projection = construct_service.reprove_structure_from_candidate(
                clean_text=clean,
                layered_candidate=layered_candidate,
                granularity_set=profile,
                structure_artifact_uuid=structure_uuid,
                projection_artifact_uuid=projection_uuid,
                clean_artifact_uuid=clean_artifact_uuid,
                clean_digest=state["clean_digest"],
            )
            structure_data = await self._read_frozen_generation_asset(
                command,
                state,
                artifact_uuid_key="structure_artifact_uuid",
                logical_handle_key="structure_artifact_ref",
                content_digest_key="structure_artifact_content_digest",
                size_bytes_key="structure_artifact_size_bytes",
                error_code="CONSTRUCT_BINDING_STRUCTURE_DIGEST",
            )
            projection_data = await self._read_frozen_generation_asset(
                command,
                state,
                artifact_uuid_key="retrieval_block_projection_artifact_uuid",
                logical_handle_key="retrieval_block_projection_ref",
                content_digest_key="retrieval_block_projection_content_digest",
                size_bytes_key="retrieval_block_projection_size_bytes",
                error_code="CONSTRUCT_BINDING_PROJECTION_DIGEST",
            )
            construct_service.assert_structure_bytes(
                structure=structure,
                projection=projection,
                structure_data=structure_data,
                projection_data=projection_data,
                structure_digest=state.get("structure_document_digest")
                if isinstance(state.get("structure_document_digest"), str)
                else None,
                projection_digest_value=state.get("retrieval_block_projection_digest")
                if isinstance(state.get("retrieval_block_projection_digest"), str)
                else None,
            )
            await self._assert_generation_members(
                command,
                state,
                self._structure_generation_members(),
                error_code="CONSTRUCT_BINDING_CURRENT",
            )
            return compiler, structure, projection


    @staticmethod
    def _structure_generation_members() -> tuple[tuple[str, str, str, str, str], ...]:
            return (
                (
                    "structure_document",
                    "structure_artifact_uuid",
                    "structure_artifact_ref",
                    "structure_artifact_content_digest",
                    "structure_artifact_size_bytes",
                ),
                (
                    "retrieval_block_projection",
                    "retrieval_block_projection_artifact_uuid",
                    "retrieval_block_projection_ref",
                    "retrieval_block_projection_content_digest",
                    "retrieval_block_projection_size_bytes",
                ),
                (
                    "structure_validation_report",
                    "structure_validation_artifact_uuid",
                    "structure_validation_artifact_ref",
                    "structure_validation_artifact_content_digest",
                    "structure_validation_artifact_size_bytes",
                ),
            )


    @classmethod
    def _construction_generation_members(cls) -> tuple[tuple[str, str, str, str, str], ...]:
            return cls._structure_generation_members() + cls._construction_output_members()


    @staticmethod
    def _construction_output_members() -> tuple[tuple[str, str, str, str, str], ...]:
            return (
                (
                    "construction_document",
                    "construction_artifact_uuid",
                    "construction_artifact_ref",
                    "construction_artifact_content_digest",
                    "construction_artifact_size_bytes",
                ),
                (
                    "dual_channel_projection",
                    "dual_channel_artifact_uuid",
                    "dual_channel_artifact_ref",
                    "dual_channel_artifact_content_digest",
                    "dual_channel_artifact_size_bytes",
                ),
                (
                    "construction_validation_report",
                    "construction_validation_artifact_uuid",
                    "construction_validation_artifact_ref",
                    "construction_validation_artifact_content_digest",
                    "construction_validation_artifact_size_bytes",
                ),
            )


    async def _assert_construct_to_vectorize_gate(self, command: ProcessCommand, state: Mapping[str, Any]) -> None:
            members = (
                self._construction_output_members()
                if self._construct_mode(state) == "metadata_refresh"
                else self._construction_generation_members()
            )
            await self._assert_generation_members(
                command,
                state,
                members,
                error_code="CONSTRUCT_TO_VECTORIZE_GATE",
            )


    async def _assert_construct_to_vectorize_gate_tx(
            self,
            tx: UnitOfWork,
            command: ProcessCommand,
            state: Mapping[str, Any],
        ) -> None:
            members = (
                self._construction_output_members()
                if self._construct_mode(state) == "metadata_refresh"
                else self._construction_generation_members()
            )
            await self._assert_generation_members_tx(
                tx,
                command,
                state,
                members,
                error_code="CONSTRUCT_TO_VECTORIZE_GATE",
            )


    async def _stored_object_uuid(
            self,
            tx: UnitOfWork,
            team_uuid: str,
            digest: str,
            size: int,
        ) -> str | None:
            row = await tx.fetchone(
                "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=? AND size_bytes=?",
                (team_uuid, digest, size),
            )
            return None if row is None else str(row["stored_object_uuid"])


    async def _catalog_generation_object(self, tx: UnitOfWork, team_uuid: str, stat: ObjectStat) -> str:
            """Catalog a pre-promoted S13 generation object inside the outcome UoW."""

            existing = await self._stored_object_uuid(tx, team_uuid, stat.sha256, stat.size_bytes)
            if existing is not None:
                return existing
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
                    stat.media_type or "application/json",
                    "local_fs",
                    utc_now(),
                ),
            )
            return stored_object_uuid


    async def _require_stored_object(self, tx: UnitOfWork, team_uuid: str, digest: str, size: int) -> str:
            stored_object_uuid = await self._stored_object_uuid(tx, team_uuid, digest, size)
            if stored_object_uuid is None:
                raise MkbError("OBJECT_CATALOGUE_MISSING", "Stage output was not catalogued", 503)
            return stored_object_uuid


    async def _reference_object(
            self,
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


    async def _insert_generation_artifact(
            self,
            tx: UnitOfWork,
            *,
            command: ProcessCommand,
            artifact_uuid: str,
            artifact_type: str,
            stored_object_uuid: str,
            logical_handle: str,
            content_digest: str,
            size_bytes: int,
            intake_item_uuid: str,
            intake_revision_uuid: str,
            clean_artifact_uuid: str,
            clean_artifact_digest: str,
            schema_key: str,
            schema_version: str,
            schema_digest: str,
            validation_report_ref: str | None,
            validation_report_digest: str | None,
            proof_ref: str,
            proof_digest: str,
            ordinal: int = 0,
        ) -> None:
            await tx.execute(
                "INSERT INTO mkb_generation_artifacts "
                "(generation_artifact_uuid,team_uuid,artifact_type,artifact_ordinal,task_uuid,execution_uuid,process_uuid,"
                "process_attempt,intake_item_uuid,intake_revision_uuid,clean_artifact_uuid,clean_artifact_digest,schema_key,"
                "schema_version,schema_digest,process_fence,logical_handle,media_type,size_bytes,content_digest,stored_object_uuid,"
                "validation_disposition,validation_report_ref,validation_report_digest,proof_ref,proof_digest,created_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,'full_valid',?,?,?,?,?,'{}')",
                (
                    artifact_uuid,
                    command.team_uuid,
                    artifact_type,
                    ordinal,
                    command.task_uuid,
                    command.execution_uuid,
                    command.process_uuid,
                    command.fencing_generation,
                    intake_item_uuid,
                    intake_revision_uuid,
                    clean_artifact_uuid,
                    clean_artifact_digest,
                    schema_key,
                    schema_version,
                    schema_digest,
                    stable_digest({"process_uuid": command.process_uuid, "fence": command.fencing_generation}),
                    logical_handle,
                    "application/json",
                    size_bytes,
                    content_digest,
                    stored_object_uuid,
                    validation_report_ref,
                    validation_report_digest,
                    proof_ref,
                    proof_digest,
                    utc_now(),
                ),
            )
            from src.services.events import DomainEventWriter

            await DomainEventWriter().write(
                tx,
                team_uuid=command.team_uuid,
                trace_uuid=command.trace_uuid,
                event_type="generation.artifact_accepted",
                aggregate="generation",
                summary=f"Generation artifact {artifact_type} accepted",
                task_uuid=command.task_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                payload={"generation_artifact_uuid": artifact_uuid, "artifact_type": artifact_type},
            )


    async def _advance_generation_pointer(
            self,
            tx: UnitOfWork,
            *,
            command: ProcessCommand,
            artifact_type: str,
            artifact_uuid: str,
        ) -> None:
            existing = await tx.fetchone(
                "SELECT current_generation_artifact_uuid,pointer_revision FROM mkb_generation_pointers "
                "WHERE team_uuid=? AND execution_uuid=? AND artifact_type=?",
                (command.team_uuid, command.execution_uuid, artifact_type),
            )
            now = utc_now()
            if existing is None:
                await tx.execute(
                    "INSERT INTO mkb_generation_pointers "
                    "(team_uuid,execution_uuid,artifact_type,current_generation_artifact_uuid,pointer_revision,updated_at,payload_extra) "
                    "VALUES (?,?,?,?,0,?,'{}')",
                    (command.team_uuid, command.execution_uuid, artifact_type, artifact_uuid, now),
                )
                before = None
                actual_revision = 0
            else:
                changed = await tx.execute(
                    "UPDATE mkb_generation_pointers SET current_generation_artifact_uuid=?,pointer_revision=pointer_revision+1,updated_at=? "
                    "WHERE team_uuid=? AND execution_uuid=? AND artifact_type=? AND pointer_revision=?",
                    (
                        artifact_uuid,
                        now,
                        command.team_uuid,
                        command.execution_uuid,
                        artifact_type,
                        existing["pointer_revision"],
                    ),
                )
                if changed.rowcount != 1:
                    raise MkbError("GENERATION_POINTER_FENCE", "Generation pointer changed concurrently", 409)
                before = existing["current_generation_artifact_uuid"]
                actual_revision = int(existing["pointer_revision"]) + 1
            await tx.execute(
                "INSERT INTO mkb_generation_pointer_transitions "
                "(transition_uuid,team_uuid,execution_uuid,artifact_type,before_artifact_uuid,after_artifact_uuid,"
                "expected_pointer_revision,actual_pointer_revision,causation_process_uuid,causation_task_uuid,occurred_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,'{}')",
                (
                    uuid7(),
                    command.team_uuid,
                    command.execution_uuid,
                    artifact_type,
                    before,
                    artifact_uuid,
                    0 if existing is None else existing["pointer_revision"],
                    actual_revision,
                    command.process_uuid,
                    command.task_uuid,
                    now,
                ),
            )
            from src.services.events import DomainEventWriter

            await DomainEventWriter().write(
                tx,
                team_uuid=command.team_uuid,
                trace_uuid=command.trace_uuid,
                event_type="generation.pointer_cas",
                aggregate="generation",
                summary=f"Generation pointer advanced for {artifact_type}",
                task_uuid=command.task_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                payload={
                    "artifact_type": artifact_type,
                    "after_artifact_uuid": artifact_uuid,
                    "pointer_revision": actual_revision,
                },
            )
