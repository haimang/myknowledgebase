"""Structurize/construct stages and reconstruct contracts."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _is_sha256_digest,
    _json,
    _StageMaterial,
)
from src.services.lsrag_compiler import (
    ConstructionDocument,
    DualChannelProjection,
    LsragContractCompiler,
    RetrievalBlockProjection,
    StructureDocument,
    construction_document_digest,
    construction_payload,
    deterministic_summaries,
    dual_channel_payload,
    parse_retrieval_projection_payload,
    parse_structure_payload,
    projection_digest,
    retrieval_projection_payload,
    structure_document_digest,
    structure_payload,
)


class IntakeGenerationConstructMixin:
    """Structurize/construct stages and reconstruct contracts."""

    @staticmethod
    def _layered_profile(state: Mapping[str, Any], *, error_code: str) -> tuple[int, ...]:
        raw = state.get("layered_content_profile", state.get("granularity_set", (0, 1, 2)))
        if not isinstance(raw, list | tuple) or not raw:
            raise MkbError(error_code, "Layered granularity profile is unavailable", 409)
        values = tuple(sorted(set(raw)))
        if any(isinstance(value, bool) or not isinstance(value, int) or value not in {0, 1, 2} for value in values) or 0 not in values:
            raise MkbError(error_code, "Layered granularity profile is invalid", 409)
        return values

    @staticmethod
    def _layered_state_candidate(state: Mapping[str, Any], *, error_code: str) -> Mapping[str, object]:
        candidate = state.get("layered_content_candidate")
        if not isinstance(candidate, Mapping):
            raise MkbError(error_code, "Accepted layered JSON candidate is unavailable", 409)
        return candidate

    async def _reconstruct_metadata_refresh_contract(
            self,
            command: ProcessCommand,
            state: Mapping[str, Any],
        ) -> tuple[LsragContractCompiler, StructureDocument, RetrievalBlockProjection, dict[str, str], dict[str, str]]:
            """Re-prove S06 and copy source summaries for typed metadata refresh.

            The source construction can have an earlier metadata header projection,
            so it is deliberately not reconstructed from a guessed old header map.
            Instead, its immutable S06 bytes, construction binding, validation
            member, and every dual-channel body/digest are verified before the
            exact summary strings are supplied to a *new* construction generation.
            """

            source = await self._assert_metadata_refresh_source(command, state)
            headers = self._metadata_refresh_headers_from_state(state)
            members = source["members"]
            assert isinstance(members, Mapping)
            structure_receipt = members["structure_document"]
            projection_receipt = members["retrieval_block_projection"]
            structure_validation_receipt = members["structure_validation_report"]
            construction_receipt = members["construction_document"]
            dual_receipt = members["dual_channel_projection"]
            construction_validation_receipt = members["construction_validation_report"]
            assert all(
                isinstance(receipt, Mapping)
                for receipt in (
                    structure_receipt,
                    projection_receipt,
                    structure_validation_receipt,
                    construction_receipt,
                    dual_receipt,
                    construction_validation_receipt,
                )
            )
            clean = self._generation_clean_text(state, error_code="METADATA_REFRESH_SOURCE_INVALID")
            compiler = LsragContractCompiler()
            structure_data = await self._read_metadata_refresh_member(
                command, structure_receipt, error_code="METADATA_REFRESH_SOURCE_INVALID"
            )
            projection_data = await self._read_metadata_refresh_member(
                command, projection_receipt, error_code="METADATA_REFRESH_SOURCE_INVALID"
            )
            try:
                structure_payload_value = json.loads(structure_data)
                projection_payload_value = json.loads(projection_data)
                if not isinstance(structure_payload_value, Mapping) or not isinstance(projection_payload_value, Mapping):
                    raise ValueError("generation members must be objects")
                structure = parse_structure_payload(structure_payload_value)
                projection = parse_retrieval_projection_payload(projection_payload_value)
                compiler.validate_structure(
                    document=structure,
                    projection=projection,
                    clean_text=clean,
                    required_granularities=frozenset(block.granularity for block in projection.blocks),
                )
            except (TypeError, ValueError, KeyError, json.JSONDecodeError, MkbError) as exc:
                raise MkbError(
                    "METADATA_REFRESH_SOURCE_INVALID",
                    "Frozen source structure members cannot be re-proven",
                    409,
                ) from exc
            if (
                structure_data != canonical_json(structure_payload(structure))
                or projection_data != canonical_json(retrieval_projection_payload(projection))
            ):
                raise MkbError(
                    "METADATA_REFRESH_SOURCE_INVALID",
                    "Frozen source structure bytes do not bind the inherited clean artifact",
                    409,
                )
            structure_validation_data = await self._read_metadata_refresh_member(
                command, structure_validation_receipt, error_code="METADATA_REFRESH_SOURCE_INVALID"
            )
            expected_structure_validation = canonical_json(
                self._structure_validation_report_payload(
                    validation_artifact_uuid=str(structure_validation_receipt["generation_artifact_uuid"]),
                    structure=structure,
                    projection=projection,
                )
            )
            if structure_validation_data != expected_structure_validation:
                raise MkbError(
                    "METADATA_REFRESH_SOURCE_INVALID",
                    "Frozen source structure validation report is inconsistent",
                    409,
                )

            construction_data = await self._read_metadata_refresh_member(
                command, construction_receipt, error_code="METADATA_REFRESH_SOURCE_INVALID"
            )
            dual_data = await self._read_metadata_refresh_member(
                command, dual_receipt, error_code="METADATA_REFRESH_SOURCE_INVALID"
            )
            construction_validation_data = await self._read_metadata_refresh_member(
                command, construction_validation_receipt, error_code="METADATA_REFRESH_SOURCE_INVALID"
            )
            try:
                source_construction = json.loads(construction_data)
                source_dual = json.loads(dual_data)
                source_construction_validation = json.loads(construction_validation_data)
            except (TypeError, UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise MkbError(
                    "METADATA_REFRESH_SOURCE_INVALID",
                    "Frozen source construction family is not deterministic JSON",
                    409,
                ) from exc
            if not isinstance(source_construction, dict) or not isinstance(source_dual, dict):
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Frozen source construction payload is invalid", 409)
            expected_construction_keys = {
                "schema_version",
                "generation_artifact_uuid",
                "structure_generation_artifact_uuid",
                "projection_generation_artifact_uuid",
                "structure_document_digest",
                "projection_digest",
                "metadata_projection_digest",
                "recipe_version",
                "units",
                "proof_digest",
            }
            if (
                set(source_construction) != expected_construction_keys
                or source_construction.get("schema_version") != "mkb.construction-document.v1"
                or source_construction.get("generation_artifact_uuid") != construction_receipt["generation_artifact_uuid"]
                or source_construction.get("structure_generation_artifact_uuid") != structure.generation_artifact_uuid
                or source_construction.get("projection_generation_artifact_uuid") != projection.generation_artifact_uuid
                or source_construction.get("structure_document_digest") != structure_document_digest(structure)
                or source_construction.get("projection_digest") != projection_digest(projection)
                or source_construction.get("recipe_version") != "content_full.v1"
                or not _is_sha256_digest(source_construction.get("metadata_projection_digest"))
                or not _is_sha256_digest(source_construction.get("proof_digest"))
                or not isinstance(source_construction.get("units"), list)
            ):
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Frozen source construction binding is invalid", 409)
            if (
                set(source_dual) != {"schema_version", "generation_artifact_uuid", "recipe_version", "units"}
                or source_dual.get("schema_version") != "mkb.dual-channel-projection.v1"
                or source_dual.get("generation_artifact_uuid") != dual_receipt["generation_artifact_uuid"]
                or source_dual.get("recipe_version") != "content_full.v1"
                or not isinstance(source_dual.get("units"), list)
                or len(source_construction["units"]) != len(projection.blocks)
                or len(source_dual["units"]) != len(projection.blocks)
            ):
                raise MkbError("METADATA_REFRESH_SOURCE_INVALID", "Frozen source dual-channel family is incomplete", 409)

            summaries: dict[str, str] = {}
            for block, construction_unit, dual_unit in zip(
                projection.blocks,
                source_construction["units"],
                source_dual["units"],
                strict=True,
            ):
                if (
                    not isinstance(construction_unit, Mapping)
                    or set(construction_unit) != {"unit_id", "granularity", "coordinate"}
                    or construction_unit.get("unit_id") != block.block_id
                    or construction_unit.get("granularity") != block.granularity
                    or construction_unit.get("coordinate")
                    != f"{structure.generation_artifact_uuid}:{projection.generation_artifact_uuid}:{block.block_id}"
                    or not isinstance(dual_unit, Mapping)
                    or set(dual_unit) != {
                        "unit_id",
                        "granularity",
                        "original",
                        "summary",
                        "original_digest",
                        "summary_digest",
                    }
                    or dual_unit.get("unit_id") != block.block_id
                    or dual_unit.get("granularity") != block.granularity
                    or dual_unit.get("original") != block.original_text
                    or dual_unit.get("original_digest") != block.original_digest
                    or not isinstance(dual_unit.get("summary"), str)
                    or not dual_unit["summary"].strip()
                    or dual_unit.get("summary_digest") != stable_digest({"text": dual_unit["summary"]})
                ):
                    raise MkbError(
                        "METADATA_REFRESH_SOURCE_INVALID",
                        "Frozen source dual-channel summaries do not align to the source projection",
                        409,
                    )
                summaries[block.block_id] = dual_unit["summary"]

            expected_construction_validation_keys = {
                "schema_version",
                "generation_artifact_uuid",
                "disposition",
                "construction_generation_artifact_uuid",
                "construction_document_digest",
                "dual_channel_generation_artifact_uuid",
                "dual_channel_proof_digest",
                "proof_digest",
            }
            if (
                not isinstance(source_construction_validation, Mapping)
                or set(source_construction_validation) != expected_construction_validation_keys
                or source_construction_validation.get("schema_version") != "mkb.construction-validation-report.v1"
                or source_construction_validation.get("generation_artifact_uuid")
                != construction_validation_receipt["generation_artifact_uuid"]
                or source_construction_validation.get("disposition") != "full_valid"
                or source_construction_validation.get("construction_generation_artifact_uuid")
                != construction_receipt["generation_artifact_uuid"]
                or source_construction_validation.get("dual_channel_generation_artifact_uuid")
                != dual_receipt["generation_artifact_uuid"]
                or any(
                    not _is_sha256_digest(source_construction_validation.get(key))
                    for key in ("construction_document_digest", "dual_channel_proof_digest", "proof_digest")
                )
            ):
                raise MkbError(
                    "METADATA_REFRESH_SOURCE_INVALID",
                    "Frozen source construction validation report is inconsistent",
                    409,
                )
            return compiler, structure, projection, summaries, headers


    async def _reconstruct_construct_contract(
            self,
            command: ProcessCommand,
            state: Mapping[str, Any],
        ) -> tuple[LsragContractCompiler, ConstructionDocument, DualChannelProjection]:
            """Load and re-prove the exact full-valid S07 handoff before S08."""

            if self._construct_mode(state) == "metadata_refresh":
                compiler, structure, projection, summaries, metadata_headers = await self._reconstruct_metadata_refresh_contract(
                    command, state
                )
                required_granularities = frozenset(block.granularity for block in projection.blocks)
            else:
                compiler, structure, projection = await self._reconstruct_structure_contract(command, state)
                accepted = self._layered_state_candidate(state, error_code="CONSTRUCT_TO_VECTORIZE_GATE")
                completed = state.get("layered_content_constructed")
                if not isinstance(completed, Mapping):
                    raise MkbError("CONSTRUCT_TO_VECTORIZE_GATE", "Completed layered summary package is unavailable", 409)
                summaries = compiler.layered_summary_map(
                    layered_json=completed,
                    projection=projection,
                    accepted_layered_json=accepted,
                )
                metadata_headers = None
                required_granularities = frozenset(self._layered_profile(state, error_code="CONSTRUCT_TO_VECTORIZE_GATE"))
            construction_uuid = self._generation_state_text(
                state, "construction_artifact_uuid", "CONSTRUCT_TO_VECTORIZE_GATE"
            )
            dual_uuid = self._generation_state_text(state, "dual_channel_artifact_uuid", "CONSTRUCT_TO_VECTORIZE_GATE")
            construction, dual = compiler.construct(
                structure=structure,
                projection=projection,
                clean_text=self._generation_clean_text(state, error_code="CONSTRUCT_TO_VECTORIZE_GATE"),
                construction_generation_artifact_uuid=construction_uuid,
                dual_channel_generation_artifact_uuid=dual_uuid,
                summaries_by_block_id=summaries,
                metadata_headers=metadata_headers,
                required_granularities=required_granularities,
            )
            construction_data = await self._read_frozen_generation_asset(
                command,
                state,
                artifact_uuid_key="construction_artifact_uuid",
                logical_handle_key="construction_artifact_ref",
                content_digest_key="construction_artifact_content_digest",
                size_bytes_key="construction_artifact_size_bytes",
                error_code="CONSTRUCT_TO_VECTORIZE_GATE",
            )
            dual_data = await self._read_frozen_generation_asset(
                command,
                state,
                artifact_uuid_key="dual_channel_artifact_uuid",
                logical_handle_key="dual_channel_artifact_ref",
                content_digest_key="dual_channel_artifact_content_digest",
                size_bytes_key="dual_channel_artifact_size_bytes",
                error_code="CONSTRUCT_TO_VECTORIZE_GATE",
            )
            if construction_data != canonical_json(construction_payload(construction)) or dual_data != canonical_json(dual_channel_payload(dual)):
                raise MkbError("CONSTRUCT_TO_VECTORIZE_GATE", "Construct bytes do not match the exact full-valid generation", 409)
            if state.get("construction_document_digest") != construction_document_digest(construction):
                raise MkbError("CONSTRUCT_TO_VECTORIZE_GATE", "Construction semantic digest does not match the frozen handoff", 409)
            return compiler, construction, dual


    async def _structurize(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            clean = self._generation_clean_text(state, error_code="STRUCTURE_BINDING_CLEAN_DIGEST")
            clean_artifact_uuid = self._generation_state_text(state, "clean_artifact_uuid", "STRUCTURE_BINDING_CLEAN_ARTIFACT")
            structure_artifact_uuid = uuid7()
            projection_artifact_uuid = uuid7()
            validation_artifact_uuid = uuid7()
            # S11 live profile freezes binding/prompt/schema, calls the facade once,
            # then the kernel admits the returned layered candidate.  There is no
            # clean-text compiler fallback: a missing or malformed candidate is a
            # typed structure failure.
            generation_invocation: dict[str, Any] | None = None
            layered_candidate: Mapping[str, object] | None = None
            if self._live_inference:
                generation_invocation = await self._live_structured_generate(
                    command,
                    stage_key="structurize",
                    input_text=clean,
                    prompt_key="promptB.default",
                    prompt_version="v1",
                    schema_key="lsrag.structure.default",
                    schema_version="v1",
                    input_digest=stable_digest({"clean_digest": state["clean_digest"], "stage": "structurize"}),
                )
                live_candidate = generation_invocation.pop("_structured_output", None)
                if isinstance(live_candidate, Mapping):
                    layered_candidate = live_candidate
            if layered_candidate is None:
                layered_candidate = self._layered_state_candidate(
                    state,
                    error_code="STRUCTURE_CANDIDATE_MISSING",
                )
            profile = self._layered_profile(state, error_code="STRUCTURE_PROFILE_INVALID")
            compiler = LsragContractCompiler()
            accepted_candidate = compiler.normalize_layered_candidate(
                clean_text=clean,
                layered_json=layered_candidate,
                granularity_set=profile,
            )
            structure, projection, adoption_report = compiler.adopt_layered_json_with_report(
                clean_text=clean,
                layered_json=accepted_candidate,
                generation_artifact_uuid=structure_artifact_uuid,
                projection_generation_artifact_uuid=projection_artifact_uuid,
                clean_artifact_uuid=clean_artifact_uuid,
                clean_digest=state["clean_digest"],
                granularity_set=profile,
            )
            structure_semantic_digest = structure_document_digest(structure)
            projection_semantic_digest = projection_digest(projection)
            structure_asset = await self._promote_generation_member(
                command,
                artifact_uuid=structure_artifact_uuid,
                artifact_type="structure_document",
                payload=structure_payload(structure),
            )
            projection_asset = await self._promote_generation_member(
                command,
                artifact_uuid=projection_artifact_uuid,
                artifact_type="retrieval_block_projection",
                payload=retrieval_projection_payload(projection),
            )
            validation_asset = await self._promote_generation_member(
                command,
                artifact_uuid=validation_artifact_uuid,
                artifact_type="structure_validation_report",
                payload=self._structure_validation_report_payload(
                    validation_artifact_uuid=validation_artifact_uuid,
                    structure=structure,
                    projection=projection,
                ),
            )
            next_state = dict(state)
            next_state.update(
                {
                    "structure_artifact_uuid": structure_artifact_uuid,
                    "structure_artifact_ref": structure_asset.stat.handle.value,
                    "structure_artifact_content_digest": structure_asset.stat.sha256,
                    "structure_artifact_size_bytes": structure_asset.stat.size_bytes,
                    "structure_document_digest": structure_semantic_digest,
                    "retrieval_block_projection_artifact_uuid": projection_artifact_uuid,
                    "retrieval_block_projection_ref": projection_asset.stat.handle.value,
                    "retrieval_block_projection_content_digest": projection_asset.stat.sha256,
                    "retrieval_block_projection_size_bytes": projection_asset.stat.size_bytes,
                    "retrieval_block_projection_digest": projection_semantic_digest,
                    "structure_validation_artifact_uuid": validation_artifact_uuid,
                    "structure_validation_artifact_ref": validation_asset.stat.handle.value,
                    "structure_validation_artifact_content_digest": validation_asset.stat.sha256,
                    "structure_validation_artifact_size_bytes": validation_asset.stat.size_bytes,
                    "layered_content_candidate": accepted_candidate,
                    "layered_content_candidate_digest": stable_digest(accepted_candidate),
                    "layered_content_profile": list(profile),
                    "layered_adoption_report": adoption_report,
                }
            )
            if generation_invocation is not None:
                # Body-free receipt only: digests, identity, and token counts.
                next_state["structure_generation_invocation"] = {
                    key: generation_invocation[key]
                    for key in (
                        "invocation_uuid",
                        "invocation_ordinal",
                        "process_attempt",
                        "capability_key",
                        "stage_key",
                        "input_digest",
                        "output_digest",
                        "error_digest",
                        "status",
                        "error_code",
                        "model_key",
                        "model_version",
                        "adapter_kind",
                        "prompt_key",
                        "prompt_version",
                        "prompt_digest",
                        "schema_key",
                        "schema_version",
                        "schema_digest",
                        "request_digest",
                        "latency_ms",
                        "input_tokens",
                        "output_tokens",
                        "total_tokens",
                    )
                    if key in generation_invocation
                }
            material = self._material(
                command,
                next_state,
                {
                    "structure_artifact": {
                        "structure_document": self._generation_asset_receipt(structure_asset, structure_semantic_digest),
                        "retrieval_block_projection": self._generation_asset_receipt(
                            projection_asset, projection_semantic_digest
                        ),
                        "validation_report": self._generation_asset_receipt(validation_asset),
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                schema = await tx.fetchone(
                    "SELECT schema_digest FROM mkb_structure_schema_definitions "
                    "WHERE schema_key='lsrag.structure.default' AND schema_version='v1'"
                )
                if schema is None:
                    raise MkbError("REGISTRY_NOT_FOUND", "Structure schema definition is unavailable", 503)
                if generation_invocation is not None:
                    await self._record_generation_and_inference_invocations(tx, command, generation_invocation)
                for asset in (structure_asset, projection_asset, validation_asset):
                    stored_object_uuid = await self._catalog_generation_object(tx, command.team_uuid, asset.stat)
                    await self._insert_generation_artifact(
                        tx,
                        command=command,
                        artifact_uuid=asset.artifact_uuid,
                        artifact_type=asset.artifact_type,
                        stored_object_uuid=stored_object_uuid,
                        logical_handle=asset.stat.handle.value,
                        content_digest=asset.stat.sha256,
                        size_bytes=asset.stat.size_bytes,
                        intake_item_uuid=state["intake_item_uuid"],
                        intake_revision_uuid=state["intake_revision_uuid"],
                        clean_artifact_uuid=clean_artifact_uuid,
                        clean_artifact_digest=state["clean_digest"],
                        schema_key="lsrag.structure.default",
                        schema_version="v1",
                        schema_digest=schema["schema_digest"],
                        validation_report_ref=validation_asset.stat.handle.value,
                        validation_report_digest=validation_asset.stat.sha256,
                        proof_ref=refs["proof_ref"],
                        proof_digest=refs["proof_digest"],
                    )
                    await self._reference_object(
                        tx,
                        team_uuid=command.team_uuid,
                        stored_object_uuid=stored_object_uuid,
                        purpose="generation_artifact",
                        owner_kind="generation_artifact",
                        owner_uuid=asset.artifact_uuid,
                        digest=asset.stat.sha256,
                        size=asset.stat.size_bytes,
                    )
                for asset in (structure_asset, projection_asset, validation_asset):
                    await self._advance_generation_pointer(
                        tx,
                        command=command,
                        artifact_type=asset.artifact_type,
                        artifact_uuid=asset.artifact_uuid,
                    )

            return material, {}, callback


    async def _construct(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            construct_mode = self._construct_mode(state)
            generation_invocations: list[dict[str, Any]] = []
            completed_layered_candidate: dict[str, object] | None = None
            if construct_mode == "metadata_refresh":
                compiler, structure, projection, summaries, metadata_headers = await self._reconstruct_metadata_refresh_contract(
                    command, state
                )
                required_granularities = frozenset(block.granularity for block in projection.blocks)
            else:
                compiler, structure, projection = await self._reconstruct_structure_contract(command, state)
                accepted_layered_candidate = self._layered_state_candidate(
                    state,
                    error_code="CONSTRUCT_BINDING_CANDIDATE_MISSING",
                )
                profile = self._layered_profile(state, error_code="CONSTRUCT_BINDING_PROFILE_INVALID")
                if self._live_inference:
                    completed_value, receipt = await self._live_layered_summary_generate(
                        command,
                        layered_candidate=accepted_layered_candidate,
                    )
                    if not isinstance(completed_value, Mapping):
                        raise MkbError("CONSTRUCT_KERNEL_SUMMARY_INVALID", "C did not return a layered JSON package", 422)
                    completed_layered_candidate = dict(completed_value)
                    generation_invocations = [receipt]
                else:
                    summaries = deterministic_summaries(projection)
                    completed_layered_candidate = compiler.fill_layered_summaries(
                        accepted_layered_json=accepted_layered_candidate,
                        projection=projection,
                        summaries_by_block_id=summaries,
                    )
                if completed_layered_candidate is None:
                    raise MkbError("CONSTRUCT_KERNEL_SUMMARY_INVALID", "Completed layered JSON package is unavailable", 422)
                summaries = compiler.layered_summary_map(
                    layered_json=completed_layered_candidate,
                    projection=projection,
                    accepted_layered_json=accepted_layered_candidate,
                )
                required_granularities = frozenset(profile)
                metadata_headers = None
            construction_artifact_uuid = uuid7()
            dual_channel_artifact_uuid = uuid7()
            validation_artifact_uuid = uuid7()
            construction, dual = compiler.construct(
                structure=structure,
                projection=projection,
                clean_text=self._generation_clean_text(state, error_code="CONSTRUCT_BINDING_CLEAN_DIGEST"),
                construction_generation_artifact_uuid=construction_artifact_uuid,
                dual_channel_generation_artifact_uuid=dual_channel_artifact_uuid,
                summaries_by_block_id=summaries,
                metadata_headers=metadata_headers,
                required_granularities=required_granularities,
            )
            construction_semantic_digest = construction_document_digest(construction)
            construction_asset = await self._promote_generation_member(
                command,
                artifact_uuid=construction_artifact_uuid,
                artifact_type="construction_document",
                payload=construction_payload(construction),
            )
            dual_asset = await self._promote_generation_member(
                command,
                artifact_uuid=dual_channel_artifact_uuid,
                artifact_type="dual_channel_projection",
                payload=dual_channel_payload(dual),
            )
            validation_asset = await self._promote_generation_member(
                command,
                artifact_uuid=validation_artifact_uuid,
                artifact_type="construction_validation_report",
                payload=self._construction_validation_report_payload(
                    validation_artifact_uuid=validation_artifact_uuid,
                    construction=construction,
                    dual=dual,
                ),
            )
            next_state = dict(state)
            next_state.update(
                {
                    "construct_mode": construct_mode,
                    "construction_artifact_uuid": construction_artifact_uuid,
                    "construction_artifact_ref": construction_asset.stat.handle.value,
                    "construction_artifact_content_digest": construction_asset.stat.sha256,
                    "construction_artifact_size_bytes": construction_asset.stat.size_bytes,
                    "construction_document_digest": construction_semantic_digest,
                    "dual_channel_artifact_uuid": dual_channel_artifact_uuid,
                    "dual_channel_artifact_ref": dual_asset.stat.handle.value,
                    "dual_channel_artifact_content_digest": dual_asset.stat.sha256,
                    "dual_channel_artifact_size_bytes": dual_asset.stat.size_bytes,
                    "construction_validation_artifact_uuid": validation_artifact_uuid,
                    "construction_validation_artifact_ref": validation_asset.stat.handle.value,
                    "construction_validation_artifact_content_digest": validation_asset.stat.sha256,
                    "construction_validation_artifact_size_bytes": validation_asset.stat.size_bytes,
                }
            )
            if completed_layered_candidate is not None:
                next_state.update(
                    {
                        "layered_content_constructed": completed_layered_candidate,
                        "layered_content_constructed_digest": stable_digest(completed_layered_candidate),
                    }
                )
            if generation_invocations:
                next_state["construction_generation_invocations"] = [
                    {
                        key: item[key]
                        for key in (
                            "invocation_uuid",
                            "invocation_ordinal",
                            "process_attempt",
                            "capability_key",
                            "stage_key",
                            "input_digest",
                            "output_digest",
                            "error_digest",
                            "status",
                            "error_code",
                            "model_key",
                            "model_version",
                            "adapter_kind",
                            "prompt_key",
                            "prompt_version",
                            "prompt_digest",
                            "schema_key",
                            "schema_version",
                            "schema_digest",
                            "request_digest",
                            "latency_ms",
                            "input_tokens",
                            "output_tokens",
                            "total_tokens",
                        )
                        if key in item
                    }
                    for item in generation_invocations
                ]
            material = self._material(
                command,
                next_state,
                {
                    "construct_package": {
                        "mode": construct_mode,
                        "content_full": True,
                        "construction_document": self._generation_asset_receipt(
                            construction_asset, construction_semantic_digest
                        ),
                        "dual_channel_projection": self._generation_asset_receipt(dual_asset),
                        "validation_report": self._generation_asset_receipt(validation_asset),
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                schema = await tx.fetchone(
                    "SELECT schema_digest FROM mkb_construction_schema_definitions "
                    "WHERE schema_key='lsrag.construction.default' AND schema_version='v1'"
                )
                if schema is None:
                    raise MkbError("REGISTRY_NOT_FOUND", "Construction schema definition is unavailable", 503)
                for item in generation_invocations:
                    await self._record_generation_and_inference_invocations(tx, command, item)
                for asset in (construction_asset, dual_asset, validation_asset):
                    stored_object_uuid = await self._catalog_generation_object(tx, command.team_uuid, asset.stat)
                    await self._insert_generation_artifact(
                        tx,
                        command=command,
                        artifact_uuid=asset.artifact_uuid,
                        artifact_type=asset.artifact_type,
                        stored_object_uuid=stored_object_uuid,
                        logical_handle=asset.stat.handle.value,
                        content_digest=asset.stat.sha256,
                        size_bytes=asset.stat.size_bytes,
                        intake_item_uuid=state["intake_item_uuid"],
                        intake_revision_uuid=state["intake_revision_uuid"],
                        clean_artifact_uuid=state["clean_artifact_uuid"],
                        clean_artifact_digest=state["clean_digest"],
                        schema_key="lsrag.construction.default",
                        schema_version="v1",
                        schema_digest=schema["schema_digest"],
                        validation_report_ref=validation_asset.stat.handle.value,
                        validation_report_digest=validation_asset.stat.sha256,
                        proof_ref=refs["proof_ref"],
                        proof_digest=refs["proof_digest"],
                    )
                    await self._reference_object(
                        tx,
                        team_uuid=command.team_uuid,
                        stored_object_uuid=stored_object_uuid,
                        purpose="generation_artifact",
                        owner_kind="generation_artifact",
                        owner_uuid=asset.artifact_uuid,
                        digest=asset.stat.sha256,
                        size=asset.stat.size_bytes,
                    )
                for asset in (construction_asset, dual_asset, validation_asset):
                    await self._advance_generation_pointer(
                        tx,
                        command=command,
                        artifact_type=asset.artifact_type,
                        artifact_uuid=asset.artifact_uuid,
                    )
                outbox_payload = {
                    "schema_version": "mkb.vectorize-construct-intent.v1",
                    "team_uuid": command.team_uuid,
                    "task_uuid": command.task_uuid,
                    "execution_uuid": command.execution_uuid,
                    "construction_artifact_uuid": construction_artifact_uuid,
                    "construction_ref": construction_asset.stat.handle.value,
                    "construction_content_digest": construction_asset.stat.sha256,
                    "dual_channel_artifact_uuid": dual_channel_artifact_uuid,
                    "dual_channel_ref": dual_asset.stat.handle.value,
                    "dual_channel_content_digest": dual_asset.stat.sha256,
                    "construction_schema_digest": schema["schema_digest"],
                    "content_full_recipe_version": "content_full.v1",
                }
                now = utc_now()
                await tx.execute(
                    "INSERT OR IGNORE INTO mkb_outbox "
                    "(outbox_id,team_uuid,kind,payload_json,payload_digest,dedupe_key,status,available_at,created_at,updated_at,payload_extra) "
                    "VALUES (?,?,?,?,?,?,'pending',?,?,?,'{}')",
                    (
                        uuid7(),
                        command.team_uuid,
                        "vectorize_construct",
                        _json(outbox_payload),
                        stable_digest(outbox_payload),
                        f"vectorize-construct:{stable_digest(outbox_payload)}",
                        now,
                        now,
                        now,
                    ),
                )

            return material, {}, callback
