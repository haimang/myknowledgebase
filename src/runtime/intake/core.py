"""Core Process dispatch, envelopes, and frozen-target helpers."""

from __future__ import annotations

import json
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from intake.types import CleanPrompt
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest
from src.contracts.runtime.models import ProcessCommand, ProcessOutcome
from src.contracts.storage.models import ObjectHandle
from src.persistence.ports import PersistencePort, UnitOfWork
from src.runtime.inference.facade import InferenceFacade
from src.runtime.intake.types import (
    BrowserFetcher,
    HttpFetcher,
    _digest_bytes,
    _StageMaterial,
)
from src.runtime.workflow_engine import canonical_outcome_digest
from src.services.artifacts import OutcomeArtifactCommitter
from src.services.index_retirement import IndexGenerationRetirementService
from src.services.intake_lifecycle import IntakeLifecycleService
from src.services.scatter_intake import (
    ScatterAcceptanceWriter,
)
from src.services.vector_purge import VectorGenerationPurger
from src.storage.ports import ObjectStorePort


class IntakeCoreMixin:
    """Core Process dispatch, envelopes, and frozen-target helpers."""

    def __init__(
            self,
            persistence: PersistencePort,
            storage: ObjectStorePort,
            committer: OutcomeArtifactCommitter,
            *,
            http_fetcher: HttpFetcher | None = None,
            browser_fetcher: BrowserFetcher | None = None,
            inference: InferenceFacade | None = None,
            live_inference: bool = False,
            clean_llm: object | None = None,
            clean_prompt: CleanPrompt | None = None,
            lifecycle: IntakeLifecycleService | None = None,
            scatter_acceptance: ScatterAcceptanceWriter | None = None,
            index_retirement: IndexGenerationRetirementService | None = None,
            embedding_dimension: int = 64,
            prompt_root: Path | None = None,
        ) -> None:
            if embedding_dimension < 1:
                raise ValueError("embedding_dimension must be positive")
            self._persistence = persistence
            self._storage = storage
            self._committer = committer
            self._http_fetcher = http_fetcher
            # Browser rendering is intentionally a distinct injected capability.
            # Falling back to the static HTTP fetcher would fabricate rendered
            # provenance and hide a missing browser profile from preflight.
            self._browser_fetcher = browser_fetcher
            self._inference = inference
            self._live_inference = live_inference
            self._clean_llm = clean_llm
            self._clean_prompt = clean_prompt
            self._lifecycle = lifecycle
            self._scatter_acceptance = scatter_acceptance or ScatterAcceptanceWriter()
            # This is optional only for focused unit compositions that never make
            # an index pointer cutover.  The application composition always
            # supplies it, so a real S09 promotion records its grace intent in the
            # same transaction as the pointer CAS.
            self._index_retirement = index_retirement
            self._embedding_dimension = embedding_dimension
            # Prompt bytes are code-owned source assets.  A deployment can mount a
            # reviewed alternate git checkout through composition, but they never
            # enter L4/output manifests or either invocation ledger.
            self._prompt_root = (prompt_root or Path(__file__).resolve().parents[3] / "data" / "prompts").resolve()
            self._vector_purger = VectorGenerationPurger(persistence)

    async def run(self, command: ProcessCommand) -> ProcessOutcome:
            """Run one Process with no direct Task/Execution/Process mutation."""

            try:
                state = await self._load_state(command)
                material, _route_extra, callback = await self._material_for(command, state)
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
                    # Route facts live on Task / CandidateSet / transitions.
                    # Outcome extra must never be the admission/intent SSOT.
                    payload_extra={},
                )
                return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})
            except MkbError as exc:
                return self._outcome_from_error(command, exc)
            except (TypeError, ValueError, json.JSONDecodeError):
                return self._failed(command, "PIPELINE_INPUT_INVALID", "Stage input is invalid")

    # Transient transport / capacity failures may auto-retry the same Process.
    # Closed code set only. Permanent capability / config gaps stay terminal
    # ``failed`` (e.g. *_INFERENCE_UNAVAILABLE = "not configured", OCR missing,
    # registry absent) so max_retries is not exhausted on a misconfiguration
    # (D01-T027). Do not classify by HTTP status alone.
    _RECOVERABLE_ERROR_CODES = frozenset(
        {
            "VECTORIZE_INFERENCE_FAILED",
            "GENERATION_INFERENCE_FAILED",
            "VECTORIZE_CONFIG_SNAPSHOT_UNAVAILABLE",
            "INFERENCE_TRANSPORT_RETRYABLE",
            "not-ready",
        }
    )

    @classmethod
    def _is_recoverable_error(cls, exc: MkbError) -> bool:
        return exc.code in cls._RECOVERABLE_ERROR_CODES

    @classmethod
    def _outcome_from_error(cls, command: ProcessCommand, exc: MkbError) -> ProcessOutcome:
        if cls._is_recoverable_error(exc):
            return cls._retryable_failure(command, exc.code, exc.message)
        return cls._failed(command, exc.code, exc.message)

    @staticmethod
    def _retryable_failure(command: ProcessCommand, code: str, message: str) -> ProcessOutcome:
        provisional = ProcessOutcome(
            schema_version="mkb.process-outcome.v1",
            team_uuid=command.team_uuid,
            task_uuid=command.task_uuid,
            execution_uuid=command.execution_uuid,
            process_uuid=command.process_uuid,
            fencing_generation=command.fencing_generation,
            disposition="retryable_failure",
            outcome_digest="0" * 64,
            error_code=code[:128],
            error_message=message[:512],
        )
        return provisional.model_copy(update={"outcome_digest": canonical_outcome_digest(provisional)})

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
            dispatch = {
                "intake.acquire.inline": self._acquire,
                "intake.acquire.local_object": self._acquire,
                "intake.acquire.http_static": self._acquire,
                "intake.acquire.http_browser": self._acquire,
                "intake.acquire.registered_api": self._acquire,
                "intake.decode.text_json_html": self._decode,
                "intake.decode.pdf": self._decode,
                "clean.extract.deterministic": self._clean,
                "clean.extract.web": self._clean,
                "clean.extract.web_llm": self._clean,
                "clean.extract.pdf_text": self._clean,
                "clean.extract.pdf_llm": self._clean,
                "clean.extract.doc_llm": self._clean,
                "clean.ocr.local": self._clean,
                "clean.extract.vision": self._clean,
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
            request_intent = state.get("request_intent")
            if isinstance(request_intent, str):
                route_extra["request_intent"] = request_intent
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
