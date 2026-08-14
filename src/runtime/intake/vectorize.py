"""S08 vectorize stage, Layer-A profile, and embedding invocation."""

from __future__ import annotations

import math
import re
import struct
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.inference.models import (
    EmbeddingRequest,
    InferenceBinding,
)
from src.contracts.runtime.models import ProcessCommand
from src.contracts.vector.models import EmbeddingModelRef, VectorizeCommand, VectorizeHandoffV1, VectorizeOutcome
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _json,
    _StageMaterial,
)
from src.services.deterministic_embedding import deterministic_embedding


class IntakeVectorizeMixin:
    """S08 vectorize stage, Layer-A profile, and embedding invocation."""

    async def _vectorize(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            explicit_command = self._vectorize_command_from_state(command, state)
            if explicit_command is not None and explicit_command.mode == "purge_generation":
                return await self._purge_vector_generation(command, state, explicit_command)
            return await self._vectorize_from_construct(command, state, explicit_command)


    @staticmethod
    def _vectorize_command_from_state(
            command: ProcessCommand,
            state: Mapping[str, Any],
        ) -> VectorizeCommand | None:
            """Load an optional internal S08 command without accepting a new API surface.

            A purge is a Process/maintenance concern rather than a Task
            ``request_intent``.  Its command is therefore permitted only in an
            already-frozen internal process input (or predecessor state), never in
            a public route selector.  The generic Process digest must bind it.
            """

            raw = state.get("vectorize_command")
            if raw is None:
                payload = state.get("payload")
                raw = payload.get("vectorize_command") if isinstance(payload, Mapping) else None
            if raw is None:
                return None
            if not isinstance(raw, Mapping):
                raise MkbError("VECTORIZE_BINDING_COMMAND_INVALID", "Vectorize command must be a typed object", 422)
            try:
                vectorize_command = VectorizeCommand.model_validate(dict(raw))
            except (TypeError, ValueError) as exc:
                raise MkbError("VECTORIZE_BINDING_COMMAND_INVALID", "Vectorize command is invalid", 422) from exc
            if (
                vectorize_command.team_uuid != command.team_uuid
                or vectorize_command.execution_uuid != command.execution_uuid
                or vectorize_command.command_input_digest != command.command_input_digest
            ):
                raise MkbError("VECTORIZE_BINDING_COMMAND_MISMATCH", "Vectorize command does not match its Process", 409)
            return vectorize_command


    @staticmethod
    def _from_construct_vectorize_command(
            command: ProcessCommand,
            state: Mapping[str, Any],
            *,
            namespace_uuid: str,
            layer_a: Mapping[str, Any],
        ) -> VectorizeCommand:
            """Project the immutable S07 package into the explicit S08 command."""

            try:
                layer_a_ref = EmbeddingModelRef.model_validate(dict(layer_a))
                return VectorizeCommand(
                    mode="from_construct",
                    team_uuid=command.team_uuid,
                    execution_uuid=command.execution_uuid,
                    command_input_digest=command.command_input_digest,
                    construction_artifact_uuid=str(state["construction_artifact_uuid"]),
                    construction_content_digest=str(state["construction_artifact_content_digest"]),
                    dual_channel_generation_artifact_uuid=str(state["dual_channel_artifact_uuid"]),
                    dual_channel_content_digest=str(state["dual_channel_artifact_content_digest"]),
                    content_full_recipe_version="content_full.v1",
                    intake_item_uuid=str(state["intake_item_uuid"]),
                    intake_revision_uuid=str(state["intake_revision_uuid"]),
                    namespace_key="default",
                    namespace_uuid=namespace_uuid,
                    embedding_model_ref=layer_a_ref,
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise MkbError("VECTORIZE_BINDING_COMMAND_INVALID", "Construct handoff cannot form a Vectorize command", 409) from exc


    async def _purge_vector_generation(
            self,
            command: ProcessCommand,
            state: Mapping[str, Any],
            vectorize_command: VectorizeCommand,
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            """Write one S08 generation-scoped logical deletion receipt.

            This path intentionally bypasses construct reconstruction: a purge
            acts on a previously frozen generation coordinate and must not pretend
            to produce a new dual-channel generation or a publication handoff.
            """

            expected_receipt = await self._vector_purger.plan(vectorize_command)
            vectorize_outcome = VectorizeOutcome(
                mode="purge_generation",
                command_input_digest=command.command_input_digest,
                purge_receipt=expected_receipt,
            )
            next_state = {
                "request_intent": state.get("request_intent"),
                "operation_mode": "vector_purge_generation",
                "team_uuid": command.team_uuid,
                "task_uuid": command.task_uuid,
                "trace_uuid": command.trace_uuid,
                "vectorize_command": vectorize_command.model_dump(mode="json"),
                "vectorize_outcome": vectorize_outcome.model_dump(mode="json"),
            }
            material = self._material(
                command,
                next_state,
                {"vectorization_receipt": vectorize_outcome.model_dump(mode="json")},
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                del refs
                actual = await self._vector_purger.purge_tx(tx, vectorize_command, expected=expected_receipt)
                if actual != expected_receipt:
                    raise MkbError("PURGE_REQUIRED_SET_CHANGED", "Purge result diverged from its frozen receipt", 409)

            return material, {"vectorize_outcome": vectorize_outcome.model_dump(mode="json")}, callback


    async def _vectorize_from_construct(
            self,
            command: ProcessCommand,
            state: dict[str, Any],
            explicit_command: VectorizeCommand | None,
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            compiler, construction, dual = await self._reconstruct_construct_contract(command, state)
            await self._assert_construct_to_vectorize_gate(command, state)
            metadata_headers = (
                self._metadata_refresh_headers_from_state(state)
                if self._construct_mode(state) == "metadata_refresh"
                else None
            )
            plan = compiler.vectorization_plan(document=construction, dual=dual, metadata_headers=metadata_headers)
            if not plan.required:
                raise MkbError("CONSTRUCT_TO_VECTORIZE_GATE", "Construct package has no required vector units", 409)
            namespace_uuid, next_generation = await self._namespace_coordinates(command.team_uuid)
            mode, frozen_layer_a = await self._embedding_profile(command)
            vectorize_command = self._from_construct_vectorize_command(
                command,
                state,
                namespace_uuid=namespace_uuid,
                layer_a=frozen_layer_a,
            )
            if explicit_command is not None and explicit_command != vectorize_command:
                raise MkbError(
                    "VECTORIZE_BINDING_COMMAND_MISMATCH",
                    "Frozen vectorize command does not match the construct handoff",
                    409,
                )
            invocation: dict[str, Any] | None = None
            vector_inputs = list(plan.required)
            texts = [item.content_full for item in vector_inputs]
            if mode == "live":
                vectors, layer_a, invocation = await self._live_embeddings(command, texts, frozen_layer_a)
            else:
                vectors = [deterministic_embedding(text, dimension=int(frozen_layer_a["dimension"])) for text in texts]
                layer_a = frozen_layer_a
            if len(vectors) != len(vector_inputs):
                raise MkbError("VECTORIZE_INFERENCE_FAILED", "Embedding response does not cover the required vector set", 503)
            persisted_records: list[dict[str, Any]] = []
            for item, vector in zip(vector_inputs, vectors, strict=True):
                existing_uuid = await self._existing_vector_coordinate_uuid(
                    team_uuid=command.team_uuid,
                    namespace_uuid=namespace_uuid,
                    generation_artifact_uuid=state["dual_channel_artifact_uuid"],
                    unit_id=item.unit_id,
                    channel=item.channel,
                    embedding_model=layer_a["model_key"],
                )
                persisted_records.append(
                    {
                        "vector_record_uuid": existing_uuid or uuid7(),
                        "unit_id": item.unit_id,
                        "granularity": item.granularity,
                        "channel": item.channel,
                        "coordinate": item.coordinate,
                        "content": item.content_full,
                        "content_digest": item.content_full_digest,
                        "embedding": vector,
                    }
                )
            next_state = dict(state)
            next_state["namespace_uuid"] = namespace_uuid
            next_state["index_generation"] = next_generation
            next_state["publication_proof_uuid"] = uuid7()
            next_state["layer_a"] = layer_a
            handoff = VectorizeHandoffV1(
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                command_input_digest=command.command_input_digest,
                generation_artifact_uuid=vectorize_command.dual_channel_generation_artifact_uuid or "",
                generation_content_digest=vectorize_command.dual_channel_content_digest or "",
                content_full_recipe_version=vectorize_command.content_full_recipe_version or "",
                namespace_uuid=namespace_uuid,
                embedding_model_ref=EmbeddingModelRef.model_validate(dict(layer_a)),
                required_units=len(vector_inputs),
                succeeded_units=len(vector_inputs),
                skipped_empty_units=len(plan.skipped),
            )
            vectorize_outcome = VectorizeOutcome(
                mode="from_construct",
                command_input_digest=command.command_input_digest,
                handoff=handoff,
            )
            # These closed, body-free models are the S08→S09 handoff.  The S09
            # Process revalidates them before any publication mutation; a generic
            # workflow route or outbox ACK never substitutes for this receipt.
            next_state["vectorize_command"] = vectorize_command.model_dump(mode="json")
            next_state["vectorize_handoff"] = handoff.model_dump(mode="json")
            next_state["vectorize_outcome"] = vectorize_outcome.model_dump(mode="json")
            if invocation is not None:
                # This is metadata only: no source text, prompt body, or vector
                # coordinate is ever copied into a stage envelope.
                next_state["embedding_invocation"] = invocation
            # Do not embed source text or vectors into a Process outcome.  The
            # direct dual-channel generation object remains the retrieval body;
            # this receipt carries only generation-scoped coordinates and digests.
            next_state["vector_records"] = [
                {
                    "vector_record_uuid": record["vector_record_uuid"],
                    "unit_id": record["unit_id"],
                    "granularity": record["granularity"],
                    "channel": record["channel"],
                    "coordinate": record["coordinate"],
                    "content_digest": record["content_digest"],
                }
                for record in persisted_records
            ]
            material = self._material(
                command,
                next_state,
                {
                    "vectorization_receipt": {
                        "namespace_key": "default",
                        "namespace_uuid": namespace_uuid,
                        "index_generation": next_generation,
                        "expected_count": len(next_state["vector_records"]),
                        "actual_count": len(next_state["vector_records"]),
                        "layer_a": layer_a,
                        "handoff": handoff.model_dump(mode="json"),
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                del refs
                await self._assert_construct_to_vectorize_gate_tx(tx, command, state)
                await self._ensure_namespace(tx, command.team_uuid, namespace_uuid, layer_a)
                if invocation is not None:
                    await self._record_embedding_invocation(tx, command, invocation)
                for record in persisted_records:
                    vector = record["embedding"]
                    blob = struct.pack(f"<{int(layer_a['dimension'])}f", *vector)
                    vector_record_uuid = await self._upsert_vector_record_tx(
                        tx,
                        command=command,
                        state=state,
                        namespace_uuid=namespace_uuid,
                        index_generation=next_generation,
                        layer_a=layer_a,
                        record=record,
                        embedding_blob=blob,
                    )
                    await self._upsert_vector_source_kind_facet_tx(
                        tx,
                        team_uuid=command.team_uuid,
                        vector_record_uuid=vector_record_uuid,
                        source_kind=state["source_kind"],
                    )
                    from src.services.events import DomainEventWriter

                    await DomainEventWriter().write(
                        tx,
                        team_uuid=command.team_uuid,
                        trace_uuid=command.trace_uuid,
                        event_type="vector.upserted",
                        aggregate="vector",
                        summary="Vector record upserted",
                        task_uuid=command.task_uuid,
                        execution_uuid=command.execution_uuid,
                        process_uuid=command.process_uuid,
                        payload={
                            "vector_record_uuid": vector_record_uuid,
                            "generation_artifact_uuid": record.get("generation_artifact_uuid")
                            or state.get("construction_dual_channel_artifact_uuid"),
                            "channel": record["channel"],
                        },
                    )

            return material, {"vectorize_outcome": vectorize_outcome.model_dump(mode="json")}, callback


    async def _embedding_profile(self, command: ProcessCommand) -> tuple[str, dict[str, Any]]:
            """Resolve the exact embedding profile frozen with this Execution.

            Runtime settings are intentionally not consulted here.  A Task may sit
            in a queue while operators change the active profile; its Process must
            still use the L4 binding that was materialized at admission.
            """

            snapshot = await self._load_config_snapshot(command)
            try:
                mode = snapshot["l2"]["inference_mode"]
                raw_binding = snapshot["l1"]["bindings"]["embed"]
            except (KeyError, TypeError) as exc:
                raise MkbError("VECTORIZE_CONFIG_SNAPSHOT_INVALID", "Frozen embed profile is invalid", 503) from exc
            if mode not in {"live", "deterministic"} or not isinstance(raw_binding, dict):
                raise MkbError("VECTORIZE_CONFIG_SNAPSHOT_INVALID", "Frozen embed profile is invalid", 503)
            layer_a = self._validate_layer_a(raw_binding)
            if mode == "deterministic":
                if (
                    layer_a["adapter_kind"] != "deterministic"
                    or layer_a["model_key"] != "deterministic-hash-v1"
                    or layer_a["model_version"] != "v1"
                    or layer_a["dimension"] != self._embedding_dimension
                ):
                    raise MkbError(
                        "VECTORIZE_CONFIG_SNAPSHOT_INVALID",
                        "Frozen deterministic embed profile is not the registered local profile",
                        503,
                    )
            return mode, layer_a


    async def _live_embeddings(
            self,
            command: ProcessCommand,
            texts: list[str],
            layer_a: dict[str, Any],
        ) -> tuple[list[list[float]], dict[str, Any], dict[str, Any]]:
            if self._inference is None:
                raise MkbError("VECTORIZE_INFERENCE_UNAVAILABLE", "Embedding inference is not configured", 503)
            try:
                binding = InferenceBinding(
                    capability_key="embed",
                    adapter_kind=layer_a["adapter_kind"],
                    model_key=layer_a["model_key"],
                    model_version=layer_a["model_version"],
                    binding_digest=str(layer_a["binding_digest"]),
                )
            except (TypeError, ValueError) as exc:
                raise MkbError("VECTORIZE_CONFIG_SNAPSHOT_INVALID", "Frozen live embed binding is invalid", 503) from exc
            request_digest = stable_digest(
                {
                    "capability": "embed",
                    "binding_digest": binding.binding_digest,
                    "text_digests": [stable_digest({"text": text}) for text in texts],
                }
            )
            started = time.monotonic()
            try:
                response = await self._inference.embed(
                    EmbeddingRequest(
                        team_uuid=command.team_uuid,
                        binding=binding,
                        texts=texts,
                        expected_dimension=int(layer_a["dimension"]),
                    )
                )
            except Exception as exc:
                raise MkbError("VECTORIZE_INFERENCE_FAILED", "Embedding inference failed", 503) from exc
            latency_ms = max(0, int((time.monotonic() - started) * 1000))
            if (
                response.model_key != layer_a["model_key"]
                or response.model_version != layer_a["model_version"]
                or response.dimension != layer_a["dimension"]
                or len(response.vectors) != len(texts)
            ):
                raise MkbError(
                    "VECTORIZE_SPACE_LAYER_A_MISMATCH", "Embedding response conflicts with the frozen Layer A", 409
                )
            vectors: list[list[float]] = []
            try:
                for vector in response.vectors:
                    values = [float(value) for value in vector]
                    if len(values) != layer_a["dimension"] or not all(math.isfinite(value) for value in values):
                        raise ValueError("embedding dimensions or values are invalid")
                    vectors.append(values)
            except (TypeError, ValueError) as exc:
                raise MkbError(
                    "VECTORIZE_SPACE_LAYER_A_MISMATCH", "Embedding response conflicts with the frozen Layer A", 409
                ) from exc
            invocation = {
                "invocation_uuid": uuid7(),
                "request_digest": request_digest,
                "adapter_kind": layer_a["adapter_kind"],
                "model_key": layer_a["model_key"],
                "model_version": layer_a["model_version"],
                "binding_digest": binding.binding_digest,
                "vector_count": len(vectors),
                "dimension": layer_a["dimension"],
                "latency_ms": latency_ms,
            }
            return vectors, layer_a, invocation


    @staticmethod
    def _validate_layer_a(raw: Mapping[str, Any]) -> dict[str, Any]:
            try:
                model_key = raw["model_key"]
                model_version = raw["model_version"]
                adapter_kind = raw["adapter_kind"]
                dimension = raw["dimension"]
                binding_digest = raw.get("binding_digest")
            except AttributeError as exc:
                raise MkbError("VECTORIZE_SPACE_LAYER_A_INVALID", "Layer A is invalid", 422) from exc
            if (
                not isinstance(model_key, str)
                or not model_key
                or not isinstance(model_version, str)
                or not model_version
                or not isinstance(adapter_kind, str)
                or not adapter_kind
                or isinstance(dimension, bool)
                or not isinstance(dimension, int)
                or dimension < 1
            ):
                raise MkbError("VECTORIZE_SPACE_LAYER_A_INVALID", "Layer A is invalid", 422)
            result: dict[str, Any] = {
                "model_key": model_key,
                "model_version": model_version,
                "adapter_kind": adapter_kind,
                "dimension": dimension,
            }
            if binding_digest is not None:
                if not isinstance(binding_digest, str) or not re.fullmatch(r"[0-9a-f]{64}", binding_digest):
                    raise MkbError("VECTORIZE_SPACE_LAYER_A_INVALID", "Layer A binding digest is invalid", 422)
                result["binding_digest"] = binding_digest
            return result


    def _layer_a_from_state(self, state: Mapping[str, Any]) -> dict[str, Any]:
            raw = state.get("layer_a")
            if not isinstance(raw, Mapping):
                raise MkbError("PUBLICATION_INPUT_INVALID", "Publication input lacks a frozen Layer A", 422)
            return self._validate_layer_a(raw)


    async def _record_embedding_invocation(
            self,
            tx: UnitOfWork,
            command: ProcessCommand,
            invocation: Mapping[str, Any],
        ) -> None:
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_inference_invocations "
                "(invocation_uuid,team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid,capability_key,adapter_kind,"
                "model_key,model_version,request_digest,status,latency_ms,occurred_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,'embed',?,?,?,?,'succeeded',?,?,?)",
                (
                    invocation["invocation_uuid"],
                    command.team_uuid,
                    command.trace_uuid,
                    command.task_uuid,
                    command.execution_uuid,
                    command.process_uuid,
                    invocation["adapter_kind"],
                    invocation["model_key"],
                    invocation["model_version"],
                    invocation["request_digest"],
                    invocation["latency_ms"],
                    utc_now(),
                    _json(
                        {
                            "binding_digest": invocation["binding_digest"],
                            "vector_count": invocation["vector_count"],
                            "dimension": invocation["dimension"],
                        }
                    ),
                ),
            )

