"""Deterministic, durable single-intake LS-RAG stage implementation.

The workflow graph itself remains declarative in :mod:`src.workflows`.  This
module is the narrow runtime-side implementation for its registered Process
capabilities.  It deliberately receives only a claimed ``ProcessCommand`` and
returns a typed outcome; all durable domain mutations are deferred to
``OutcomeArtifactCommitter`` so they commit atomically with the Process fence.

The deterministic profile is intentional: it provides a complete local proof
path for CI and offline deployments.  A live inference profile can be added at
the facade seam without changing the intake/generation/vector state model.
"""

from __future__ import annotations

import hashlib
import inspect
import json
import math
import re
import struct
import time
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.inference.models import EmbeddingRequest, InferenceBinding
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.contracts.storage.models import ObjectHandle, ObjectStat, PromoteRequest
from src.persistence.ports import PersistencePort, UnitOfWork
from src.runtime.inference.facade import InferenceFacade
from src.runtime.workflow_engine import ProcessStageHandler, canonical_outcome_digest
from src.services.artifacts import OutcomeArtifactCommitter
from src.services.deterministic_embedding import deterministic_embedding
from src.services.index_retirement import IndexGenerationRetirementService
from src.services.intake_lifecycle import IntakeLifecycleCommand, IntakeLifecycleService, IntakePublicationCommand
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
    projection_digest,
    retrieval_projection_payload,
    structure_document_digest,
    structure_payload,
)
from src.services.scatter_intake import (
    ScatterAcceptanceWriter,
    ScatterChildWorkflowBinding,
    ScatterCollectionAcceptance,
    ScatterCollectionMember,
)
from src.storage.ports import ObjectStorePort
from src.workflows.builtin_scatter import SCATTER_CHILD_WORKFLOW_KEY

_SPACE = re.compile(r"\s+")
_HTML = re.compile(r"<[^>]+>")

HttpFetcher = Callable[[str], str | bytes | Awaitable[str | bytes]]


@dataclass(frozen=True, slots=True)
class _StageMaterial:
    """A staged envelope plus the small callback facts it needs."""

    envelope: dict[str, Any]
    output_bytes: bytes
    proof_bytes: bytes


@dataclass(frozen=True, slots=True)
class _GenerationArtifactMaterial:
    """One independently promoted immutable S06/S07 generation member."""

    artifact_uuid: str
    artifact_type: str
    stat: ObjectStat


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _clean_text(value: str) -> str:
    return _SPACE.sub(" ", _HTML.sub(" ", value)).strip()


class IntakePipeline(ProcessStageHandler):
    """Concrete handler for the built-in single-intake workflow.

    ``http_fetcher`` is injectable because egress transport belongs at a
    separately-audited acquisition boundary.  The default fails closed rather
    than allowing a stage to make an unreviewed outbound request.
    """

    def __init__(
        self,
        persistence: PersistencePort,
        storage: ObjectStorePort,
        committer: OutcomeArtifactCommitter,
        *,
        http_fetcher: HttpFetcher | None = None,
        inference: InferenceFacade | None = None,
        live_inference: bool = False,
        lifecycle: IntakeLifecycleService | None = None,
        scatter_acceptance: ScatterAcceptanceWriter | None = None,
        index_retirement: IndexGenerationRetirementService | None = None,
        embedding_dimension: int = 64,
    ) -> None:
        if embedding_dimension < 1:
            raise ValueError("embedding_dimension must be positive")
        self._persistence = persistence
        self._storage = storage
        self._committer = committer
        self._http_fetcher = http_fetcher
        self._inference = inference
        self._live_inference = live_inference
        self._lifecycle = lifecycle
        self._scatter_acceptance = scatter_acceptance or ScatterAcceptanceWriter()
        # This is optional only for focused unit compositions that never make
        # an index pointer cutover.  The application composition always
        # supplies it, so a real S09 promotion records its grace intent in the
        # same transaction as the pointer CAS.
        self._index_retirement = index_retirement
        self._embedding_dimension = embedding_dimension

    async def run(self, command: ProcessCommand) -> ProcessOutcome:
        """Run one Process with no direct Task/Execution/Process mutation."""

        try:
            state = await self._load_state(command)
            material, route_extra, callback = await self._material_for(command, state)
            refs: dict[str, str] = {}

            async def commit(tx: UnitOfWork) -> None:
                await callback(tx, refs)

            staged = await self._committer.stage(
                command,
                output_bytes=material.output_bytes,
                proof_bytes=material.proof_bytes,
                callback=commit,
            )
            refs.update(
                {
                    "output_ref": staged.output_ref,
                    "output_digest": staged.output_digest,
                    "proof_ref": staged.proof_ref,
                    "proof_digest": staged.proof_digest,
                }
            )
            provisional = ProcessOutcome(
                schema_version="mkb.process-outcome.v1",
                team_uuid=command.team_uuid,
                task_uuid=command.task_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                fencing_generation=command.fencing_generation,
                disposition="succeeded",
                outcome_digest="0" * 64,
                output_manifest_ref=staged.output_ref,
                output_manifest_digest=staged.output_digest,
                proof_ref=staged.proof_ref,
                proof_digest=staged.proof_digest,
                payload_extra=route_extra,
            )
            return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})
        except MkbError as exc:
            return self._failed(command, exc.code, exc.message)
        except (TypeError, ValueError, json.JSONDecodeError):
            return self._failed(command, "PIPELINE_INPUT_INVALID", "Stage input is invalid")

    @staticmethod
    def _failed(command: ProcessCommand, code: str, message: str) -> ProcessOutcome:
        provisional = ProcessOutcome(
            schema_version="mkb.process-outcome.v1",
            team_uuid=command.team_uuid,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            process_uuid=command.process_uuid,
            fencing_generation=command.fencing_generation,
            disposition="failed",
            outcome_digest="0" * 64,
            error_code=code[:128],
            error_message=message[:512],
        )
        return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})

    async def _load_state(self, command: ProcessCommand) -> dict[str, Any]:
        """Load either the root execution input or a predecessor envelope."""

        data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=command.input_manifest_ref))
        if _digest_bytes(data) != command.input_manifest_digest:
            raise MkbError("OBJECT_INTEGRITY_DIGEST", "Process input bytes failed their declared digest", 503)
        decoded = json.loads(data)
        if not isinstance(decoded, dict):
            raise MkbError("PIPELINE_INPUT_INVALID", "Process input must be a JSON object", 422)
        if decoded.get("schema_version") == "mkb.execution-input-manifest.v1":
            payload = decoded.get("payload")
            if not isinstance(payload, dict):
                raise MkbError("PIPELINE_INPUT_INVALID", "Execution payload is unavailable", 422)
            intent_context = decoded.get("intent_context")
            scatter_member = intent_context.get("scatter_member") if isinstance(intent_context, dict) else None
            if isinstance(scatter_member, dict):
                return self._scatter_child_state(decoded, payload, scatter_member)
            return {
                "request_intent": decoded.get("request_intent"),
                "payload": payload,
                "intent_context": intent_context,
                "team_uuid": decoded.get("team_uuid"),
                "task_uuid": decoded.get("task_uuid"),
                "trace_uuid": decoded.get("trace_uuid"),
            }
        if decoded.get("schema_version") != "mkb.stage-output.v1" or not isinstance(decoded.get("state"), dict):
            raise MkbError("PIPELINE_INPUT_INVALID", "Process input is not an immutable stage envelope", 422)
        state = dict(decoded["state"])
        state.setdefault("predecessor_ref", command.input_manifest_ref)
        state.setdefault("predecessor_digest", command.input_manifest_digest)
        return state

    @staticmethod
    def _scatter_child_state(
        manifest: Mapping[str, Any], payload: Mapping[str, Any], member: Mapping[str, Any]
    ) -> dict[str, Any]:
        """Hydrate the exact accepted collection member for a child execution.

        The root acceptance transaction promotes this immutable input before it
        creates the child row.  No child reads a mutable source collection or
        reconstructs membership from a current API response.
        """

        required_text = (
            "intake_source_uuid",
            "intake_snapshot_uuid",
            "change_set_uuid",
            "change_set_digest",
            "intake_item_uuid",
            "intake_revision_uuid",
            "clean_artifact_uuid",
            "clean_digest",
            "clean_text",
            "source_kind",
            "normalized_external_key",
        )
        if any(not isinstance(member.get(key), str) or not member[key] for key in required_text):
            raise MkbError("SCATTER_CHILD_MANIFEST_INVALID", "Scatter child manifest lacks an exact accepted member", 422)
        clean_text = member["clean_text"]
        if stable_digest({"text": clean_text}) != member["clean_digest"]:
            raise MkbError("SCATTER_CHILD_MANIFEST_INVALID", "Scatter child clean content failed its digest fence", 409)
        ordinal = member.get("member_ordinal")
        if isinstance(ordinal, bool) or not isinstance(ordinal, int) or ordinal < 0:
            raise MkbError("SCATTER_CHILD_MANIFEST_INVALID", "Scatter child member ordinal is invalid", 422)
        return {
            "request_intent": manifest.get("request_intent"),
            "operation_mode": "scatter_child",
            "payload": dict(payload),
            "intent_context": manifest.get("intent_context"),
            "team_uuid": manifest.get("team_uuid"),
            "task_uuid": manifest.get("task_uuid"),
            "trace_uuid": manifest.get("trace_uuid"),
            "intake_source_uuid": member["intake_source_uuid"],
            "intake_snapshot_uuid": member["intake_snapshot_uuid"],
            "change_set_uuid": member["change_set_uuid"],
            "change_set_digest": member["change_set_digest"],
            "member_ordinal": ordinal,
            "source_kind": member["source_kind"],
            "external_key": member.get("external_key") or member["normalized_external_key"],
            "normalized_external_key": member["normalized_external_key"],
            "intake_item_uuid": member["intake_item_uuid"],
            "intake_revision_uuid": member["intake_revision_uuid"],
            "clean_artifact_uuid": member["clean_artifact_uuid"],
            "clean_digest": member["clean_digest"],
            "clean_text": clean_text,
            "require_human_review": bool(member.get("require_human_review", False)),
        }

    async def _material_for(
        self,
        command: ProcessCommand,
        state: dict[str, Any],
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        # Lifecycle commands have one durable mutation at acquisition.  The
        # declarative v1 skeleton then records its bounded terminal evidence
        # without pretending that clean/construct/vector stages changed an
        # already withdrawn Item.
        if state.get("operation_mode") in {"lifecycle", "index_rebuild", "index_rebuild_noop", "metadata_no_change"} and (
            command.process_key not in {"intake.acquire.inline", "index.rebuild"}
        ):
            return await self._passthrough(command, state)
        dispatch = {
            "intake.acquire.inline": self._acquire,
            "intake.acquire.registered_api": self._acquire,
            "intake.decode.text_json_html": self._decode,
            "clean.extract.deterministic": self._clean,
            "clean.map.registered_api": self._clean_registered_api,
            "intake.collection.seal": self._seal,
            "intake.preflight_validate": self._preflight,
            "intake.accept_snapshot": self._accept_snapshot,
            "lsrag.structurize": self._structurize,
            "lsrag.construct": self._construct,
            "lsrag.vectorize": self._vectorize,
            "index.validate_publication": self._publish,
            "index.rebuild": self._index_rebuild,
        }
        handler = dispatch.get(command.process_key)
        if handler is None:
            raise MkbError("PIPELINE_CAPABILITY_UNSUPPORTED", "Workflow Process capability is not implemented", 409)
        return await handler(command, state)

    def _material(
        self,
        command: ProcessCommand,
        state: dict[str, Any],
        output: Mapping[str, Any],
    ) -> _StageMaterial:
        envelope = {
            "schema_version": "mkb.stage-output.v1",
            "process_key": command.process_key,
            "process_uuid": command.process_uuid,
            "fencing_generation": command.fencing_generation,
            "state": state,
            "output": dict(output),
        }
        output_bytes = canonical_json(envelope)
        proof_bytes = canonical_json(
            {
                "schema_version": "mkb.stage-proof.v1",
                "process_key": command.process_key,
                "process_uuid": command.process_uuid,
                "fencing_generation": command.fencing_generation,
                "command_input_digest": command.command_input_digest,
                "output_digest": _digest_bytes(output_bytes),
            }
        )
        return _StageMaterial(envelope=envelope, output_bytes=output_bytes, proof_bytes=proof_bytes)

    async def _acquire(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        intent = state.get("request_intent")
        if intent == "intake.rebuild":
            return await self._acquire_rebuild(command, state)
        if intent == "intake.update_metadata":
            return await self._acquire_metadata_update(command, state)
        if intent in {"intake.deactivate", "intake.reactivate", "intake.delete"}:
            return await self._acquire_lifecycle(command, state, intent)
        if intent == "index.rebuild":
            # Compatibility for a still-pinned v1 workflow revision.  Newly
            # admitted index Tasks are selected directly into the dedicated
            # S09 capability by the static workflow's bounded start guard.
            return await self._index_rebuild(command, state)
        if intent != "intake.ingest":
            raise MkbError("INTAKE_INTENT_UNSUPPORTED", "This pipeline does not recognize the frozen Task intent", 422)
        payload = state.get("payload")
        if not isinstance(payload, dict) or not isinstance(payload.get("source"), dict):
            raise MkbError("PIPELINE_INPUT_INVALID", "Intake source descriptor is required", 422)
        descriptor = dict(payload["source"])
        source_kind = descriptor.get("source_kind")
        external_key = descriptor.get("external_key")
        if source_kind not in {"inline_payload", "local_object", "http_resource", "registered_api"}:
            raise MkbError("SOURCE_KIND_INVALID", "Source kind is not registered", 422)
        if not isinstance(external_key, str) or not external_key.strip():
            raise MkbError("SOURCE_EXTERNAL_KEY_INVALID", "Source external_key is required", 422)
        if source_kind == "registered_api":
            return await self._acquire_registered_api_collection(command, descriptor)
        if command.process_key != "intake.acquire.inline":
            raise MkbError("ACQUISITION_CAPABILITY_MISMATCH", "Source kind does not match the bound acquisition capability", 409)
        raw_text, media_type = await self._acquire_content(command, descriptor)
        if not raw_text.strip():
            raise MkbError("ACQUISITION_EMPTY", "Source acquisition returned no content", 422)
        now = utc_now()
        next_state = {
            "request_intent": "intake.ingest",
            "team_uuid": command.team_uuid,
            "task_uuid": command.task_uuid,
            "trace_uuid": command.trace_uuid,
            "source": descriptor,
            "source_kind": source_kind,
            "external_key": external_key.strip(),
            "normalized_external_key": external_key.strip().casefold(),
            "raw_text": raw_text,
            "raw_digest": stable_digest({"media_type": media_type, "text": raw_text}),
            "media_type": media_type,
            "require_human_review": bool(descriptor.get("require_human_review", False)),
            "intake_source_uuid": uuid7(),
            "candidate_set_uuid": uuid7(),
            "intake_snapshot_uuid": uuid7(),
            "intake_item_uuid": uuid7(),
            "intake_revision_uuid": uuid7(),
            "raw_artifact_uuid": uuid7(),
            "clean_artifact_uuid": uuid7(),
            "observed_at": now,
        }
        material = self._material(
            command,
            next_state,
            {
                "acquisition_evidence": {
                    "source_kind": source_kind,
                    "media_type": media_type,
                    "content_digest": next_state["raw_digest"],
                    "byte_count": len(raw_text.encode("utf-8")),
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            del refs
            definition = await tx.fetchone(
                "SELECT definition_digest FROM mkb_source_kind_definitions "
                "WHERE source_kind=? AND definition_version='v1' AND status='active'",
                (source_kind,),
            )
            if definition is None:
                raise MkbError("REGISTRY_NOT_FOUND", "Source kind definition is unavailable", 503)
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_intake_sources "
                "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
                "source_descriptor_ref,source_descriptor_digest,accepts_new_snapshots,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,'v1',?,?,?,1,?,?, '{}')",
                (
                    command.team_uuid,
                    next_state["intake_source_uuid"],
                    source_kind,
                    definition["definition_digest"],
                    command.input_manifest_ref,
                    stable_digest(descriptor),
                    now,
                    now,
                ),
            )

        return material, {}, callback

    async def _acquire_registered_api_collection(
        self, command: ProcessCommand, descriptor: Mapping[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        """Acquire an ordered typed API collection without flattening members.

        Each input record already passed the strict public contract, but this
        boundary validates its durable identity again before a collection can
        become a CandidateSet.  The root descriptor names the source namespace;
        member external keys name the individual IntakeItems.
        """

        if command.process_key != "intake.acquire.registered_api":
            raise MkbError("ACQUISITION_CAPABILITY_MISMATCH", "Registered API requires its scatter acquisition capability", 409)
        external_key = descriptor.get("external_key")
        records = descriptor.get("records")
        if not isinstance(external_key, str) or not external_key.strip() or not isinstance(records, list):
            raise MkbError("ACQUISITION_RECORDS_REQUIRED", "Registered API records are required", 422)
        members: list[dict[str, Any]] = []
        seen_keys: set[str] = set()
        for ordinal, record in enumerate(records):
            if not isinstance(record, dict):
                raise MkbError("ACQUISITION_RECORD_INVALID", "Registered API record must be an object", 422)
            member_key = record.get("external_key")
            content = record.get("content")
            media_type = record.get("media_type", "text/plain")
            if (
                not isinstance(member_key, str)
                or not member_key.strip()
                or not isinstance(content, str)
                or not content
                or not isinstance(media_type, str)
                or not media_type.strip()
            ):
                raise MkbError("ACQUISITION_RECORD_INVALID", "Registered API record lacks typed member content", 422)
            normalized_key = member_key.strip().casefold()
            if normalized_key in seen_keys:
                raise MkbError("ACQUISITION_RECORD_DUPLICATE", "Registered API member external_key is duplicated", 422)
            seen_keys.add(normalized_key)
            members.append(
                {
                    "member_ordinal": ordinal,
                    "external_key": member_key.strip(),
                    "normalized_external_key": normalized_key,
                    "raw_text": content,
                    "raw_digest": stable_digest({"media_type": media_type.strip(), "text": content}),
                    "media_type": media_type.strip(),
                    "title": record.get("title") if isinstance(record.get("title"), str) else None,
                    "require_human_review": bool(record.get("require_human_review", False)),
                    "intake_item_uuid": uuid7(),
                    "intake_revision_uuid": uuid7(),
                    "clean_artifact_uuid": uuid7(),
                    "child_execution_uuid": uuid7(),
                }
            )
        now = utc_now()
        root_external_key = external_key.strip()
        raw_digest = stable_digest(
            {
                "source_external_key": root_external_key.casefold(),
                "records": [
                    {
                        "member_ordinal": member["member_ordinal"],
                        "normalized_external_key": member["normalized_external_key"],
                        "raw_digest": member["raw_digest"],
                    }
                    for member in members
                ],
            }
        )
        next_state = {
            "request_intent": "intake.ingest",
            "operation_mode": "scatter_root",
            "team_uuid": command.team_uuid,
            "task_uuid": command.task_uuid,
            "trace_uuid": command.trace_uuid,
            "source": dict(descriptor),
            "source_kind": "registered_api",
            "external_key": root_external_key,
            "normalized_external_key": root_external_key.casefold(),
            "collection_members": members,
            "raw_digest": raw_digest,
            "require_human_review": bool(descriptor.get("require_human_review", False))
            or any(member["require_human_review"] for member in members),
            "intake_source_uuid": uuid7(),
            "candidate_set_uuid": uuid7(),
            "intake_snapshot_uuid": uuid7(),
            "change_set_uuid": uuid7(),
            "raw_artifact_uuid": uuid7(),
            "observed_at": now,
        }
        material = self._material(
            command,
            next_state,
            {
                "acquisition_evidence": {
                    "source_kind": "registered_api",
                    "member_count": len(members),
                    "content_digest": raw_digest,
                    "byte_count": sum(len(member["raw_text"].encode("utf-8")) for member in members),
                    "completeness": "complete",
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            del refs
            definition = await tx.fetchone(
                "SELECT definition_digest FROM mkb_source_kind_definitions "
                "WHERE source_kind='registered_api' AND definition_version='v1' AND status='active'"
            )
            if definition is None:
                raise MkbError("REGISTRY_NOT_FOUND", "Source kind definition is unavailable", 503)
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_intake_sources "
                "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
                "source_descriptor_ref,source_descriptor_digest,accepts_new_snapshots,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,'v1',?,?,?,1,?,?, '{}')",
                (
                    command.team_uuid,
                    next_state["intake_source_uuid"],
                    "registered_api",
                    definition["definition_digest"],
                    command.input_manifest_ref,
                    stable_digest(descriptor),
                    now,
                    now,
                ),
            )

        return material, {}, callback

    async def _acquire_rebuild(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        target = self._frozen_target(state)
        clean_text = await self._read_frozen_clean_text(command, target)
        now = utc_now()
        clean = target["clean_artifact"]
        assert isinstance(clean, dict)
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
            "media_type": "text/plain",
            "decoded_text": clean_text,
            "decoded_digest": stable_digest({"text": clean_text, "media_type": "text/plain"}),
            "clean_text": clean_text,
            "clean_digest": clean["content_digest"],
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
                    "mode": "rebuild",
                    "intake_item_uuid": target["intake_item_uuid"],
                    "intake_revision_uuid": target["intake_revision_uuid"],
                    "clean_digest": clean["content_digest"],
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

    async def _passthrough(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        material = self._material(
            command,
            dict(state),
            {
                "command_progress": {
                    "request_intent": state.get("request_intent"),
                    "operation_mode": state.get("operation_mode"),
                    "stage": command.process_key,
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            del tx, refs

        # The declarative graph still routes through ``accept_snapshot`` for
        # bounded lifecycle/no-op operations.  Preserve its already-frozen
        # admission fact so that route selection remains deterministic rather
        # than treating a bypassed business stage as an unguarded success.
        admission = state.get("admission_result")
        route_extra = {"admission_result": admission} if isinstance(admission, str) else {}
        return material, route_extra, callback

    @staticmethod
    def _frozen_target(state: Mapping[str, Any], *, require_clean: bool = True) -> dict[str, Any]:
        context = state.get("intent_context")
        target = context.get("target") if isinstance(context, dict) else None
        if not isinstance(target, dict) or target.get("schema_version") != "mkb.frozen-intake-target.v1":
            raise MkbError("INTAKE_TARGET_INVALID", "Frozen Intake target is unavailable", 422)
        required = (
            "team_uuid",
            "intake_item_uuid",
            "intake_source_uuid",
            "intake_revision_uuid",
            "source_snapshot_uuid",
            "source_kind",
            "normalized_external_key",
            "item_revision",
        )
        if (
            any(not isinstance(target.get(key), str) or not target[key] for key in required if key != "item_revision")
            or isinstance(target.get("item_revision"), bool)
            or not isinstance(target.get("item_revision"), int)
            or target["item_revision"] < 0
        ):
            raise MkbError("INTAKE_TARGET_INVALID", "Frozen Intake target is invalid", 422)
        clean = target.get("clean_artifact")
        if require_clean and (
            not isinstance(clean, dict)
            or not isinstance(clean.get("logical_handle"), str)
            or not isinstance(clean.get("content_digest"), str)
            or not isinstance(clean.get("intake_artifact_uuid"), str)
        ):
            raise MkbError("INTAKE_REBUILD_INPUT_MISSING", "Frozen Intake target lacks a clean artifact", 409)
        return target

    async def _read_frozen_clean_text(self, command: ProcessCommand, target: Mapping[str, Any]) -> str:
        from src.contracts.storage.models import ObjectHandle

        clean = target.get("clean_artifact")
        assert isinstance(clean, dict)
        try:
            data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=clean["logical_handle"]))
            envelope = json.loads(data)
            text = envelope["state"]["clean_text"]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError, MkbError) as exc:
            raise MkbError("INTAKE_REBUILD_INPUT_MISSING", "Frozen clean artifact is unavailable", 409) from exc
        if not isinstance(text, str) or stable_digest({"text": text}) != clean.get("content_digest"):
            raise MkbError("INTAKE_REBUILD_INPUT_INVALID", "Frozen clean artifact failed its digest fence", 409)
        return text

    async def _acquire_content(self, command: ProcessCommand, descriptor: Mapping[str, Any]) -> tuple[str, str]:
        source_kind = descriptor["source_kind"]
        if source_kind == "inline_payload":
            # The public inline body was staged at Task admission.  A Process
            # must never recover it from an Audit or immutable input manifest;
            # it gets only the Team-scoped object handle and independent byte
            # fences frozen by ConfigSnapshotService.
            handle = descriptor.get("logical_handle")
            content_digest = descriptor.get("content_digest")
            size_bytes = descriptor.get("size_bytes")
            if not isinstance(handle, str):
                raise MkbError("ACQUISITION_HANDLE_INVALID", "Inline ingress handle is required", 422)
            if (
                not isinstance(content_digest, str)
                or len(content_digest) != 64
                or any(char not in "0123456789abcdef" for char in content_digest)
                or isinstance(size_bytes, bool)
                or not isinstance(size_bytes, int)
                or size_bytes < 1
            ):
                raise MkbError("ACQUISITION_INGRESS_FENCE_INVALID", "Inline ingress fence is invalid", 422)
            data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=handle))
            if len(data) != size_bytes or _digest_bytes(data) != content_digest:
                raise MkbError("ACQUISITION_INGRESS_FENCE", "Inline ingress bytes failed their frozen fence", 409)
            try:
                return data.decode("utf-8"), str(descriptor.get("media_type") or "text/plain")
            except UnicodeDecodeError as exc:
                # ConfigSnapshotService only stages UTF-8 text, but retain a
                # typed fence so an object-store corruption cannot become an
                # opaque worker exception.
                raise MkbError("ACQUISITION_DECODE_UNSUPPORTED", "Inline ingress is not UTF-8 text", 422) from exc
        if source_kind == "local_object":
            handle = descriptor.get("logical_handle")
            if not isinstance(handle, str):
                raise MkbError("ACQUISITION_HANDLE_INVALID", "Local object handle is required", 422)
            data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=handle))
            try:
                return data.decode("utf-8"), str(descriptor.get("media_type") or "text/plain")
            except UnicodeDecodeError as exc:
                raise MkbError("ACQUISITION_DECODE_UNSUPPORTED", "Local object is not UTF-8 text", 422) from exc
        if source_kind == "registered_api":
            records = descriptor.get("records")
            if not isinstance(records, list):
                raise MkbError("ACQUISITION_RECORDS_REQUIRED", "Registered API records are required", 422)
            return "\n".join(_json(record) for record in records), "application/json"
        if self._http_fetcher is None:
            raise MkbError("ACQUISITION_HTTP_UNAVAILABLE", "HTTP acquisition is not configured", 503)
        url = descriptor.get("url")
        if not isinstance(url, str):
            raise MkbError("ACQUISITION_URL_INVALID", "HTTP source URL is required", 422)
        result = self._http_fetcher(url)
        if inspect.isawaitable(result):
            result = await result
        if isinstance(result, bytes):
            try:
                result = result.decode("utf-8")
            except UnicodeDecodeError as exc:
                raise MkbError("ACQUISITION_DECODE_UNSUPPORTED", "HTTP response is not UTF-8 text", 422) from exc
        if not isinstance(result, str):
            raise MkbError("ACQUISITION_RESPONSE_INVALID", "HTTP acquisition returned invalid content", 502)
        return result, "text/html" if descriptor.get("acquisition_mode") == "browser" else "text/plain"

    async def _decode(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        raw = state.get("raw_text")
        if not isinstance(raw, str):
            raise MkbError("PIPELINE_INPUT_INVALID", "Acquisition evidence has no textual payload", 422)
        decoded = raw
        if state.get("media_type") == "application/json":
            try:
                decoded = json.dumps(json.loads(raw), ensure_ascii=False, sort_keys=True)
            except json.JSONDecodeError:
                # A registered source can legally provide text-shaped JSON
                # records; preservation is safer than silently discarding it.
                decoded = raw
        next_state = dict(state)
        next_state["decoded_text"] = decoded
        next_state["decoded_digest"] = stable_digest({"text": decoded, "media_type": state.get("media_type")})
        material = self._material(
            command,
            next_state,
            {
                "decoded_representation": {
                    "content_digest": next_state["decoded_digest"],
                    "media_type": state.get("media_type"),
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            del tx, refs

        return material, {}, callback

    async def _clean(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        decoded = state.get("decoded_text")
        if not isinstance(decoded, str):
            raise MkbError("PIPELINE_INPUT_INVALID", "Decoded representation is unavailable", 422)
        clean = _clean_text(decoded)
        if not clean:
            raise MkbError("CLEAN_EMPTY", "Cleaning produced no admissible text", 422)
        next_state = dict(state)
        next_state["clean_text"] = clean
        next_state["clean_digest"] = stable_digest({"text": clean})
        material = self._material(
            command,
            next_state,
            {"clean_candidate": {"content_digest": next_state["clean_digest"], "char_count": len(clean)}},
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            del tx, refs

        return material, {}, callback

    async def _clean_registered_api(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        """Map every acquired API member into an independently clean candidate."""

        if state.get("operation_mode") != "scatter_root" or state.get("source_kind") != "registered_api":
            raise MkbError("SCATTER_STATE_INVALID", "Registered API clean map lacks a collection root", 409)
        raw_members = state.get("collection_members")
        if not isinstance(raw_members, list):
            raise MkbError("SCATTER_STATE_INVALID", "Registered API member list is unavailable", 422)
        clean_members: list[dict[str, Any]] = []
        for ordinal, raw_member in enumerate(raw_members):
            if not isinstance(raw_member, dict) or raw_member.get("member_ordinal") != ordinal:
                raise MkbError("SCATTER_MEMBER_ORDER_INVALID", "Registered API member order is invalid", 422)
            raw_text = raw_member.get("raw_text")
            if not isinstance(raw_text, str):
                raise MkbError("SCATTER_MEMBER_INVALID", "Registered API member content is unavailable", 422)
            clean_text = _clean_text(raw_text)
            if not clean_text:
                raise MkbError("CLEAN_EMPTY", "Registered API member cleaning produced no admissible text", 422)
            member = dict(raw_member)
            member["clean_text"] = clean_text
            member["clean_digest"] = stable_digest({"text": clean_text})
            clean_members.append(member)
        candidate_root_digest = stable_digest(
            {
                "source_kind": "registered_api",
                "source_external_key": state.get("normalized_external_key"),
                "members": [
                    {
                        "member_ordinal": member["member_ordinal"],
                        "normalized_external_key": member["normalized_external_key"],
                        "raw_digest": member["raw_digest"],
                        "clean_digest": member["clean_digest"],
                    }
                    for member in clean_members
                ],
            }
        )
        next_state = dict(state)
        next_state["collection_members"] = clean_members
        next_state["candidate_root_digest"] = candidate_root_digest
        next_state["collection_clean_digest"] = stable_digest(
            [member["clean_digest"] for member in clean_members]
        )
        material = self._material(
            command,
            next_state,
            {
                "clean_collection": {
                    "candidate_root_digest": candidate_root_digest,
                    "member_count": len(clean_members),
                    "clean_digest": next_state["collection_clean_digest"],
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            del tx, refs

        return material, {}, callback

    async def _seal(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        if state.get("operation_mode") == "scatter_root":
            return await self._seal_registered_api_collection(command, state)
        clean = state.get("clean_text")
        if not isinstance(clean, str) or not clean:
            raise MkbError("PIPELINE_INPUT_INVALID", "Clean candidate is unavailable", 422)
        next_state = dict(state)
        root_digest = stable_digest(
            {"external_key": state.get("normalized_external_key"), "clean_digest": state.get("clean_digest")}
        )
        next_state["candidate_root_digest"] = root_digest
        now = utc_now()
        material = self._material(
            command,
            next_state,
            {
                "candidate_set_seal": {
                    "candidate_root_digest": root_digest,
                    "member_count": 1,
                    "completeness": "complete",
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            source = await tx.fetchone(
                "SELECT source_kind_definition_digest FROM mkb_intake_sources WHERE team_uuid=? AND intake_source_uuid=?",
                (command.team_uuid, state["intake_source_uuid"]),
            )
            if source is None:
                raise MkbError("INTAKE_SOURCE_MISSING", "Candidate set has no durable IntakeSource", 409)
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_intake_candidate_sets "
                "(candidate_set_uuid,team_uuid,intake_source_uuid,producer_execution_uuid,producer_process_uuid,"
                "producer_fencing_generation,source_kind_definition_digest,acquisition_capability_digest,s05_binding_digest,"
                "observation_key,observation_fingerprint,completeness,expected_member_count,observed_member_count,"
                "accepted_member_count,rejected_member_count,duplicate_member_count,expected_page_count,observed_page_count,"
                "expected_bytes,observed_bytes,root_digest,staging_state,seal_at,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, '{}')",
                (
                    state["candidate_set_uuid"],
                    command.team_uuid,
                    state["intake_source_uuid"],
                    command.execution_uuid,
                    command.process_uuid,
                    command.fencing_generation,
                    source["source_kind_definition_digest"],
                    stable_digest({"process_key": "intake.acquire.inline"}),
                    stable_digest({"binding": command.binding_digest}),
                    state["normalized_external_key"],
                    state["raw_digest"],
                    "complete",
                    1,
                    1,
                    0,
                    0,
                    0,
                    1,
                    1,
                    len(clean.encode("utf-8")),
                    len(clean.encode("utf-8")),
                    root_digest,
                    "sealed",
                    now,
                    now,
                    now,
                ),
            )
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_intake_candidate_pages "
                "(candidate_set_uuid,page_ordinal,team_uuid,member_first_ordinal,member_last_ordinal,page_digest,"
                "sealed_payload_ref,created_at,payload_extra) VALUES (?,0,?,0,0,?,?,?,'{}')",
                (
                    state["candidate_set_uuid"],
                    command.team_uuid,
                    root_digest,
                    refs["output_ref"],
                    now,
                ),
            )

        return material, {}, callback

    async def _seal_registered_api_collection(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        if command.process_key != "intake.collection.seal":
            raise MkbError("SCATTER_CAPABILITY_MISMATCH", "Collection sealing requires the registered seal capability", 409)
        members = state.get("collection_members")
        root_digest = state.get("candidate_root_digest")
        if not isinstance(members, list) or not isinstance(root_digest, str) or not root_digest:
            raise MkbError("SCATTER_STATE_INVALID", "Collection candidates are unavailable for sealing", 422)
        if any(
            not isinstance(member, dict)
            or member.get("member_ordinal") != ordinal
            or not isinstance(member.get("clean_digest"), str)
            or not isinstance(member.get("clean_text"), str)
            for ordinal, member in enumerate(members)
        ):
            raise MkbError("SCATTER_MEMBER_INVALID", "Collection candidates are not sealed member records", 422)
        next_state = dict(state)
        member_count = len(members)
        observed_bytes = sum(len(member["clean_text"].encode("utf-8")) for member in members)
        now = utc_now()
        material = self._material(
            command,
            next_state,
            {
                "candidate_set_seal": {
                    "candidate_root_digest": root_digest,
                    "member_count": member_count,
                    "completeness": "complete",
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            source = await tx.fetchone(
                "SELECT source_kind_definition_digest FROM mkb_intake_sources WHERE team_uuid=? AND intake_source_uuid=?",
                (command.team_uuid, state["intake_source_uuid"]),
            )
            if source is None:
                raise MkbError("INTAKE_SOURCE_MISSING", "Candidate set has no durable IntakeSource", 409)
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_intake_candidate_sets "
                "(candidate_set_uuid,team_uuid,intake_source_uuid,producer_execution_uuid,producer_process_uuid,"
                "producer_fencing_generation,source_kind_definition_digest,acquisition_capability_digest,s05_binding_digest,"
                "observation_key,observation_fingerprint,completeness,expected_member_count,observed_member_count,"
                "accepted_member_count,rejected_member_count,duplicate_member_count,expected_page_count,observed_page_count,"
                "expected_bytes,observed_bytes,root_digest,staging_state,seal_at,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?, '{}')",
                (
                    state["candidate_set_uuid"],
                    command.team_uuid,
                    state["intake_source_uuid"],
                    command.execution_uuid,
                    command.process_uuid,
                    command.fencing_generation,
                    source["source_kind_definition_digest"],
                    stable_digest({"process_key": "intake.acquire.registered_api"}),
                    stable_digest({"binding": command.binding_digest}),
                    state["normalized_external_key"],
                    state["raw_digest"],
                    "complete",
                    member_count,
                    member_count,
                    0,
                    0,
                    0,
                    1 if member_count else 0,
                    1 if member_count else 0,
                    observed_bytes,
                    observed_bytes,
                    root_digest,
                    "sealed",
                    now,
                    now,
                    now,
                ),
            )
            if member_count:
                await tx.execute(
                    "INSERT OR IGNORE INTO mkb_intake_candidate_pages "
                    "(candidate_set_uuid,page_ordinal,team_uuid,member_first_ordinal,member_last_ordinal,page_digest,"
                    "sealed_payload_ref,created_at,payload_extra) VALUES (?,0,?,0,?,?,?,?,'{}')",
                    (
                        state["candidate_set_uuid"],
                        command.team_uuid,
                        member_count - 1,
                        root_digest,
                        refs["output_ref"],
                        now,
                    ),
                )

        return material, {}, callback

    async def _preflight(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        if state.get("operation_mode") == "scatter_root":
            return await self._preflight_registered_api_collection(command, state)
        clean = state.get("clean_text")
        if not isinstance(clean, str) or not clean.strip():
            admission = "rejected"
            reason = "clean_candidate_empty"
        elif bool(state.get("require_human_review")):
            admission = "human_review_required"
            reason = "source_requires_human_review"
        else:
            admission = "auto_admitted"
            reason = "deterministic_preflight_passed"
        next_state = dict(state)
        next_state["admission_result"] = admission
        next_state["preflight_reason"] = reason
        material = self._material(
            command,
            next_state,
            {
                "preflight_outcome": {
                    "admission_result": admission,
                    "reason": reason,
                    "candidate_root_digest": state.get("candidate_root_digest"),
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            updated = await tx.execute(
                "UPDATE mkb_intake_candidate_sets SET preflight_outcome_ref=?,preflight_outcome_digest=?,"
                "row_revision=row_revision+1,updated_at=? WHERE candidate_set_uuid=? AND team_uuid=? AND staging_state='sealed'",
                (
                    refs["output_ref"],
                    refs["output_digest"],
                    utc_now(),
                    state["candidate_set_uuid"],
                    command.team_uuid,
                ),
            )
            if updated.rowcount != 1:
                raise MkbError("CANDIDATE_SET_FENCE", "Preflight could not update the sealed candidate set", 409)

        return material, {"admission_result": admission}, callback

    async def _preflight_registered_api_collection(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        members = state.get("collection_members")
        if not isinstance(members, list) or not isinstance(state.get("candidate_root_digest"), str):
            raise MkbError("SCATTER_STATE_INVALID", "Collection preflight lacks a sealed candidate set", 422)
        if bool(state.get("require_human_review")):
            admission = "human_review_required"
            reason = "source_or_member_requires_human_review"
        else:
            admission = "auto_admitted"
            reason = "deterministic_collection_preflight_passed"
        next_state = dict(state)
        next_state["admission_result"] = admission
        next_state["preflight_reason"] = reason
        material = self._material(
            command,
            next_state,
            {
                "preflight_outcome": {
                    "admission_result": admission,
                    "reason": reason,
                    "candidate_root_digest": state["candidate_root_digest"],
                    "member_count": len(members),
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            updated = await tx.execute(
                "UPDATE mkb_intake_candidate_sets SET preflight_outcome_ref=?,preflight_outcome_digest=?,"
                "row_revision=row_revision+1,updated_at=? WHERE candidate_set_uuid=? AND team_uuid=? AND staging_state='sealed'",
                (
                    refs["output_ref"],
                    refs["output_digest"],
                    utc_now(),
                    state["candidate_set_uuid"],
                    command.team_uuid,
                ),
            )
            if updated.rowcount != 1:
                raise MkbError("CANDIDATE_SET_FENCE", "Preflight could not update the sealed collection", 409)

        return material, {"admission_result": admission}, callback

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
            action = await tx.fetchone(
                "SELECT action_key,definition_version FROM mkb_intake_action_definitions "
                "WHERE action_key='accept_revision' AND definition_version='v1'"
            )
            if action is None:
                raise MkbError("REGISTRY_NOT_FOUND", "Intake acceptance action is unavailable", 503)
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
            await tx.execute(
                "INSERT INTO mkb_intake_items "
                "(team_uuid,intake_item_uuid,intake_source_uuid,normalized_external_key,lifecycle_state,latest_revision_uuid,"
                "serving_revision_uuid,row_revision,created_at,updated_at,payload_extra) "
                "VALUES (?,?,?,?, 'active',?,NULL,0,?,?,'{}')",
                (
                    command.team_uuid,
                    state["intake_item_uuid"],
                    state["intake_source_uuid"],
                    state["normalized_external_key"],
                    state["intake_revision_uuid"],
                    now,
                    now,
                ),
            )
            initial_semantics = await self._initial_semantics_tx(tx, state)
            fingerprint = self._semantic_fingerprint(initial_semantics)
            await tx.execute(
                "INSERT INTO mkb_intake_revisions "
                "(team_uuid,intake_revision_uuid,intake_item_uuid,revision_ordinal,revision_fingerprint,creation_action_key,"
                "creation_action_version,source_snapshot_uuid,created_at,payload_extra) VALUES (?,?,?,1,?,?,?,?,?,'{}')",
                (
                    command.team_uuid,
                    state["intake_revision_uuid"],
                    state["intake_item_uuid"],
                    fingerprint,
                    action["action_key"],
                    action["definition_version"],
                    state["intake_snapshot_uuid"],
                    now,
                ),
            )
            for entry in initial_semantics:
                await self._insert_revision_semantic(tx, command.team_uuid, state["intake_revision_uuid"], entry, now)
            for artifact_uuid, owner_snapshot, owner_revision, role, digest in (
                (
                    state["raw_artifact_uuid"],
                    state["intake_snapshot_uuid"],
                    None,
                    "raw_acquisition",
                    state["raw_digest"],
                ),
                (
                    state["clean_artifact_uuid"],
                    None,
                    state["intake_revision_uuid"],
                    "clean_text",
                    state["clean_digest"],
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
                        "application/json",
                        digest,
                        output_size,
                        refs["output_ref"],
                        stored_object_uuid,
                        command.execution_uuid,
                        command.process_uuid,
                        now,
                    ),
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
            task_updated = await tx.execute(
                "UPDATE mkb_tasks SET intake_snapshot_uuid=?,row_revision=row_revision+1,updated_at=? "
                "WHERE team_uuid=? AND task_uuid=? AND current_root_execution_uuid=? AND intake_snapshot_uuid IS NULL",
                (state["intake_snapshot_uuid"], now, command.team_uuid, command.task_uuid, command.execution_uuid),
            )
            if task_updated.rowcount != 1:
                raise MkbError("INTAKE_SNAPSHOT_TASK_FENCE", "Task snapshot coordinate changed before acceptance", 409)
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

        return material, {"admission_result": admission}, callback

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
                        "records": [],
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
                    clean_text=clean_text,
                    clean_digest=raw_member["clean_digest"],
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
        values = (
            ("source_representation", source_kind),
            ("canonical_content", clean_digest),
            ("context_metadata", "{}"),
            ("filter_metadata", _json({"source_kind": source_kind})),
        )
        entries: list[dict[str, Any]] = []
        for semantic_key, value in values:
            definition = await tx.fetchone(
                "SELECT definition_version,definition_digest,value_kind,fingerprint_participation "
                "FROM mkb_intake_semantic_definitions "
                "WHERE semantic_key=? AND definition_version='v1'",
                (semantic_key,),
            )
            if definition is None or definition["value_kind"] != "text":
                raise MkbError("REGISTRY_NOT_FOUND", "Required intake semantic definition is unavailable", 503)
            entries.append(
                {
                    "semantic_key": semantic_key,
                    "definition_version": definition["definition_version"],
                    "definition_digest": definition["definition_digest"],
                    "value_kind": "text",
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
            # The retained clean content is immutable but each semantic
            # Revision owns its own logical artifact row.  That makes a later
            # rebuild resolve its target from the latest Revision without
            # reaching through a mutable predecessor alias.
            next_state["clean_artifact_uuid"] = uuid7()
            next_state["intake_revision_uuid"] = next_state["metadata_revision_uuid"]
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

        return material, {"admission_result": "auto_admitted"}, callback

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
        compiler = LsragContractCompiler()
        structure, projection = compiler.structurize(
            clean_text=clean,
            generation_artifact_uuid=structure_uuid,
            projection_generation_artifact_uuid=projection_uuid,
            clean_artifact_uuid=clean_artifact_uuid,
            clean_digest=state["clean_digest"],
        )
        expected_structure = canonical_json(structure_payload(structure))
        expected_projection = canonical_json(retrieval_projection_payload(projection))
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
        if structure_data != expected_structure or projection_data != expected_projection:
            raise MkbError("CONSTRUCT_BINDING_DIGEST", "Structure/projection bytes do not match their generation-local contract", 409)
        if (
            state.get("structure_document_digest") != structure_document_digest(structure)
            or state.get("retrieval_block_projection_digest") != projection_digest(projection)
        ):
            raise MkbError("CONSTRUCT_BINDING_DIGEST", "Structure/projection semantic digests do not match the frozen handoff", 409)
        await self._assert_generation_members(
            command,
            state,
            self._structure_generation_members(),
            error_code="CONSTRUCT_BINDING_CURRENT",
        )
        return compiler, structure, projection

    async def _reconstruct_construct_contract(
        self,
        command: ProcessCommand,
        state: Mapping[str, Any],
    ) -> tuple[LsragContractCompiler, ConstructionDocument, DualChannelProjection]:
        """Load and re-prove the exact full-valid S07 handoff before S08."""

        compiler, structure, projection = await self._reconstruct_structure_contract(command, state)
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
            summaries_by_block_id=deterministic_summaries(projection),
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
        return cls._structure_generation_members() + (
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
        await self._assert_generation_members(
            command,
            state,
            self._construction_generation_members(),
            error_code="CONSTRUCT_TO_VECTORIZE_GATE",
        )

    async def _assert_construct_to_vectorize_gate_tx(
        self,
        tx: UnitOfWork,
        command: ProcessCommand,
        state: Mapping[str, Any],
    ) -> None:
        await self._assert_generation_members_tx(
            tx,
            command,
            state,
            self._construction_generation_members(),
            error_code="CONSTRUCT_TO_VECTORIZE_GATE",
        )

    async def _structurize(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        clean = self._generation_clean_text(state, error_code="STRUCTURE_BINDING_CLEAN_DIGEST")
        clean_artifact_uuid = self._generation_state_text(state, "clean_artifact_uuid", "STRUCTURE_BINDING_CLEAN_ARTIFACT")
        structure_artifact_uuid = uuid7()
        projection_artifact_uuid = uuid7()
        validation_artifact_uuid = uuid7()
        compiler = LsragContractCompiler()
        structure, projection = compiler.structurize(
            clean_text=clean,
            generation_artifact_uuid=structure_artifact_uuid,
            projection_generation_artifact_uuid=projection_artifact_uuid,
            clean_artifact_uuid=clean_artifact_uuid,
            clean_digest=state["clean_digest"],
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
            }
        )
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
        compiler, structure, projection = await self._reconstruct_structure_contract(command, state)
        construction_artifact_uuid = uuid7()
        dual_channel_artifact_uuid = uuid7()
        validation_artifact_uuid = uuid7()
        construction, dual = compiler.construct(
            structure=structure,
            projection=projection,
            clean_text=self._generation_clean_text(state, error_code="CONSTRUCT_BINDING_CLEAN_DIGEST"),
            construction_generation_artifact_uuid=construction_artifact_uuid,
            dual_channel_generation_artifact_uuid=dual_channel_artifact_uuid,
            summaries_by_block_id=deterministic_summaries(projection),
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
        material = self._material(
            command,
            next_state,
            {
                "construct_package": {
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

    async def _vectorize(
        self, command: ProcessCommand, state: dict[str, Any]
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        compiler, construction, dual = await self._reconstruct_construct_contract(command, state)
        await self._assert_construct_to_vectorize_gate(command, state)
        plan = compiler.vectorization_plan(document=construction, dual=dual)
        if not plan.required:
            raise MkbError("CONSTRUCT_TO_VECTORIZE_GATE", "Construct package has no required vector units", 409)
        namespace_uuid, next_generation = await self._namespace_coordinates(command.team_uuid)
        mode, frozen_layer_a = await self._embedding_profile(command)
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

        return material, {}, callback

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
                    "updated_at=? WHERE team_uuid=? AND intake_item_uuid=? AND namespace_uuid=? AND pointer_row_revision=?",
                    (
                        state["index_generation"],
                        state["publication_proof_uuid"],
                        state["dual_channel_artifact_uuid"],
                        now,
                        command.team_uuid,
                        state["intake_item_uuid"],
                        state["namespace_uuid"],
                        pointer["pointer_row_revision"],
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

    async def _embedding_profile(self, command: ProcessCommand) -> tuple[str, dict[str, Any]]:
        """Resolve the exact embedding profile frozen with this Execution.

        Runtime settings are intentionally not consulted here.  A Task may sit
        in a queue while operators change the active profile; its Process must
        still use the L4 binding that was materialized at admission.
        """

        from src.contracts.storage.models import ObjectHandle

        try:
            data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=command.config_snapshot_ref))
        except Exception as exc:
            raise MkbError(
                "VECTORIZE_CONFIG_SNAPSHOT_UNAVAILABLE", "Frozen config snapshot is unavailable", 503
            ) from exc
        if _digest_bytes(data) != command.config_snapshot_digest:
            raise MkbError("OBJECT_INTEGRITY_DIGEST", "Frozen config snapshot failed its declared digest", 503)
        try:
            snapshot = json.loads(data)
            mode = snapshot["l2"]["inference_mode"]
            raw_binding = snapshot["l1"]["bindings"]["embed"]
        except (KeyError, TypeError, json.JSONDecodeError) as exc:
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
                EmbeddingRequest(team_uuid=command.team_uuid, binding=binding, texts=texts)
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

    async def _namespace_coordinates(self, team_uuid: str) -> tuple[str, int]:
        """Reserve a logical default namespace coordinate for one Process.

        The publish callback still performs the durable row CAS.  This early
        read exists solely so the vectorization receipt and its later
        publication proof freeze the same explicit generation coordinate.
        """

        async with self._persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT namespace_uuid,index_generation FROM mkb_vector_namespaces "
                "WHERE team_uuid=? AND namespace_key='default' AND status='active' AND deleted_at IS NULL",
                (team_uuid,),
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
        row = await tx.fetchone(
            "SELECT namespace_uuid,embedding_model_key,embedding_model_version,adapter_kind,dimension "
            "FROM mkb_vector_namespaces WHERE team_uuid=? AND namespace_key='default'",
            (team_uuid,),
        )
        if row is not None:
            if (
                row["namespace_uuid"] != namespace_uuid
                or row["embedding_model_key"] != layer_a["model_key"]
                or row["embedding_model_version"] != layer_a["model_version"]
                or row["adapter_kind"] != layer_a["adapter_kind"]
                or row["dimension"] != layer_a["dimension"]
            ):
                raise MkbError("VECTOR_NAMESPACE_BINDING_CONFLICT", "Default namespace binding conflicts", 409)
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
            "VALUES (?,?, 'default','Default retrieval namespace',?,?,?,?,?,'cosine',"
            "'active',0,?,?,'{}')",
            (
                namespace_uuid,
                team_uuid,
                layer_a["model_key"],
                layer_a["model_key"],
                layer_a["model_version"],
                layer_a["adapter_kind"],
                layer_a["dimension"],
                now,
                now,
            ),
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

    async def _existing_vector_coordinate_uuid(
        self,
        *,
        team_uuid: str,
        namespace_uuid: str,
        generation_artifact_uuid: str,
        unit_id: str,
        channel: str,
        embedding_model: str,
    ) -> str | None:
        async with self._persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT vector_record_uuid FROM mkb_vector_records WHERE team_uuid=? AND namespace_uuid=? "
                "AND generation_artifact_uuid=? AND block_or_unit_id=? AND channel=? AND embedding_model=? "
                "AND deleted_at IS NULL",
                (team_uuid, namespace_uuid, generation_artifact_uuid, unit_id, channel, embedding_model),
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
            "AND deleted_at IS NULL",
            (command.team_uuid, namespace_uuid, artifact_uuid, unit_id, channel, layer_a["model_key"]),
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


__all__ = ["HttpFetcher", "IntakePipeline"]
