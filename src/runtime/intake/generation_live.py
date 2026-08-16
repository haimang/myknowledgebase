"""Live structured/text generation and dual invocation ledgers."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Mapping
from pathlib import Path
from typing import Any, Literal

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.inference.models import (
    InferenceBinding,
    InvocationContext,
    StructuredGenerateRequest,
)
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import ObjectHandle
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _digest_bytes,
    _FrozenGenerationConfig,
    _json,
)


class IntakeGenerationLiveMixin:
    """Live structured/text generation and dual invocation ledgers."""

    async def _load_config_snapshot(self, command: ProcessCommand) -> dict[str, Any]:
            """Read and verify the immutable L4 snapshot frozen at Execution create."""

            try:
                data = await self._storage.read_verified(
                    command.team_uuid, ObjectHandle(value=command.config_snapshot_ref)
                )
            except Exception as exc:
                raise MkbError(
                    "VECTORIZE_CONFIG_SNAPSHOT_UNAVAILABLE", "Frozen config snapshot is unavailable", 503
                ) from exc
            if _digest_bytes(data) != command.config_snapshot_digest:
                raise MkbError("OBJECT_INTEGRITY_DIGEST", "Frozen config snapshot failed its declared digest", 503)
            try:
                snapshot = json.loads(data)
            except json.JSONDecodeError as exc:
                raise MkbError("VECTORIZE_CONFIG_SNAPSHOT_INVALID", "Frozen config snapshot is invalid", 503) from exc
            if not isinstance(snapshot, dict):
                raise MkbError("VECTORIZE_CONFIG_SNAPSHOT_INVALID", "Frozen config snapshot is invalid", 503)
            return snapshot


    async def _resolve_frozen_generation_config(
            self,
            command: ProcessCommand,
            *,
            capability_key: Literal["structured_generate", "text_generate"],
            prompt_key: str,
            prompt_version: str,
            prompt_role: str | None = None,
            schema_key: str,
            schema_version: str,
        ) -> _FrozenGenerationConfig:
            """Materialize exact L4/prompt/schema coordinates for one S06/S07 call.

            Prompt bodies stay transient.  Only the prompt identity and content
            digest enter either invocation ledger.
            """

            snapshot = await self._load_config_snapshot(command)
            try:
                raw_binding = snapshot["l1"]["bindings"][capability_key]
                mode = snapshot["l2"]["inference_mode"]
                prompts = snapshot["l1"]["prompts"]
            except (KeyError, TypeError) as exc:
                raise MkbError("GENERATION_CONFIG_SNAPSHOT_INVALID", "Frozen generation binding is invalid", 503) from exc
            if mode != "live" or not isinstance(raw_binding, dict) or not isinstance(prompts, list):
                raise MkbError("GENERATION_CONFIG_SNAPSHOT_INVALID", "Live generation binding is unavailable", 503)
            if prompt_role is not None:
                try:
                    selected_prompts = snapshot["l1"]["selected_prompts"]
                    selected = selected_prompts[prompt_role]
                except (KeyError, TypeError) as exc:
                    raise MkbError("PROMPT_SELECTION_INVALID", "Frozen prompt role selection is unavailable", 503) from exc
                if not isinstance(selected, dict):
                    raise MkbError("PROMPT_SELECTION_INVALID", "Frozen prompt role selection is invalid", 503)
                selected_id = selected.get("prompt_id")
                selected_version = selected.get("version")
                selected_role = selected.get("role")
                if (
                    not isinstance(selected_id, str)
                    or not isinstance(selected_version, str)
                    or selected_role != prompt_role
                ):
                    raise MkbError("PROMPT_SELECTION_INVALID", "Frozen prompt role selection is invalid", 503)
                prompt_key = selected_id
                prompt_version = selected_version
            pointer = next(
                (
                    row
                    for row in prompts
                    if isinstance(row, dict)
                    and (row.get("prompt_id") or row.get("prompt_key")) == prompt_key
                    and row.get("prompt_version") == prompt_version
                ),
                None,
            )
            if pointer is None:
                raise MkbError("PROMPT_HASH_MISMATCH", "Frozen prompt pointer is unavailable", 503)
            if prompt_role is not None and pointer.get("role") != prompt_role:
                raise MkbError("PROMPT_ROLE_MISMATCH", "Frozen prompt role does not match its catalog pointer", 503)
            relative_path = pointer.get("git_relative_path")
            expected_sha = pointer.get("content_sha256")
            if not isinstance(relative_path, str) or not isinstance(expected_sha, str):
                raise MkbError("PROMPT_HASH_MISMATCH", "Frozen prompt pointer is invalid", 503)
            # Prompt files are code-owned; reject traversal and absolute paths.
            if Path(relative_path).is_absolute() or ".." in Path(relative_path).parts:
                raise MkbError("PROMPT_HASH_MISMATCH", "Frozen prompt path is invalid", 503)
            prompt_path = (self._prompt_root / relative_path).resolve()
            try:
                prompt_path.relative_to(self._prompt_root)
            except ValueError as exc:
                raise MkbError("PROMPT_HASH_MISMATCH", "Frozen prompt path is outside the prompt root", 503) from exc
            try:
                prompt_bytes = prompt_path.read_bytes()
            except OSError as exc:
                raise MkbError("PROMPT_HASH_MISMATCH", "Frozen prompt bytes are unavailable", 503) from exc
            prompt_digest = hashlib.sha256(prompt_bytes).hexdigest()
            if prompt_digest != expected_sha:
                raise MkbError("PROMPT_HASH_MISMATCH", "Prompt bytes do not match the frozen pointer", 503)
            async with self._persistence.transaction() as tx:
                if capability_key == "structured_generate":
                    schema_row = await tx.fetchone(
                        "SELECT schema_digest FROM mkb_structure_schema_definitions "
                        "WHERE schema_key=? AND schema_version=?",
                        (schema_key, schema_version),
                    )
                else:
                    schema_row = await tx.fetchone(
                        "SELECT schema_digest FROM mkb_construction_schema_definitions "
                        "WHERE schema_key=? AND schema_version=?",
                        (schema_key, schema_version),
                    )
            if schema_row is None or not schema_row["schema_digest"]:
                raise MkbError("REGISTRY_NOT_FOUND", "Generation schema definition is unavailable", 503)
            try:
                binding = InferenceBinding(
                    capability_key=capability_key,
                    adapter_kind=raw_binding["adapter_kind"],
                    model_key=raw_binding["model_key"],
                    model_version=raw_binding["model_version"],
                    binding_digest=str(raw_binding["binding_digest"]),
                )
            except (KeyError, TypeError, ValueError) as exc:
                raise MkbError("GENERATION_CONFIG_SNAPSHOT_INVALID", "Frozen generation binding is invalid", 503) from exc
            return _FrozenGenerationConfig(
                capability_key=capability_key,
                binding=binding,
                prompt_key=prompt_key,
                prompt_version=prompt_version,
                prompt_digest=prompt_digest,
                prompt_text=prompt_bytes.decode("utf-8"),
                schema_key=schema_key,
                schema_version=schema_version,
                schema_digest=str(schema_row["schema_digest"]),
            )


    async def _live_structured_generate(
            self,
            command: ProcessCommand,
            *,
            stage_key: str,
            input_text: str,
            prompt_key: str,
            prompt_version: str,
            prompt_role: str | None = None,
            schema_key: str,
            schema_version: str,
            input_digest: str,
            invocation_ordinal: int = 0,
        ) -> dict[str, Any]:
            """Call ``structured_generate`` with a frozen binding and safe digests only."""

            if self._inference is None:
                raise MkbError("GENERATION_INFERENCE_UNAVAILABLE", "Structured generation is not configured", 503)
            config = await self._resolve_frozen_generation_config(
                command,
                capability_key="structured_generate",
                prompt_key=prompt_key,
                prompt_version=prompt_version,
                prompt_role=prompt_role,
                schema_key=schema_key,
                schema_version=schema_version,
            )
            generation_uuid = uuid7()
            request = StructuredGenerateRequest(
                team_uuid=command.team_uuid,
                binding=config.binding,
                prompt_ref=config.prompt_ref,
                prompt_digest=config.prompt_digest,
                input_text=input_text,
                system_text=config.prompt_text,
                json_schema_ref=config.schema_ref,
                json_schema_digest=config.schema_digest,
                invocation=InvocationContext(
                    trace_uuid=command.trace_uuid,
                    task_uuid=command.task_uuid,
                    execution_uuid=command.execution_uuid,
                    process_uuid=command.process_uuid,
                    generation_invocation_uuid=generation_uuid,
                    prompt_content_hash=config.prompt_digest,
                    schema_content_digest=config.schema_digest,
                    config_snapshot_digest=command.config_snapshot_digest,
                ),
            )
            started = time.monotonic()
            request_digest = stable_digest(
                {
                    "capability": "structured_generate",
                    "binding_digest": config.binding.binding_digest,
                    "prompt_digest": config.prompt_digest,
                    "schema_digest": config.schema_digest,
                    "input_digest": input_digest,
                }
            )
            base_receipt: dict[str, Any] = {
                "invocation_uuid": generation_uuid,
                "inference_invocation_uuid": uuid7(),
                "invocation_ordinal": invocation_ordinal,
                "process_attempt": command.fencing_generation,
                "capability_key": "structured_generate",
                "stage_key": stage_key,
                "input_digest": input_digest,
                "output_digest": None,
                "error_digest": None,
                "status": "succeeded",
                "error_code": None,
                "model_key": config.binding.model_key,
                "model_version": config.binding.model_version,
                "adapter_kind": config.binding.adapter_kind,
                "binding_digest": config.binding.binding_digest,
                "prompt_key": config.prompt_key,
                "prompt_version": config.prompt_version,
                "prompt_digest": config.prompt_digest,
                "schema_key": config.schema_key,
                "schema_version": config.schema_version,
                "schema_digest": config.schema_digest,
                "request_digest": request_digest,
                "latency_ms": 0,
                "input_tokens": None,
                "output_tokens": None,
                "total_tokens": None,
            }
            try:
                response, _typed = await self._inference.structured_generate(request)
            except MkbError as exc:
                base_receipt.update(
                    {
                        "status": "failed",
                        "error_code": exc.code,
                        "error_digest": stable_digest({"error_code": exc.code, "message": exc.message}),
                        "latency_ms": max(0, int((time.monotonic() - started) * 1000)),
                    }
                )
                await self._persist_failed_generation_invocation(command, base_receipt)
                raise
            except Exception as exc:
                base_receipt.update(
                    {
                        "status": "failed",
                        "error_code": "GENERATION_INFERENCE_FAILED",
                        "error_digest": stable_digest(
                            {"error_code": "GENERATION_INFERENCE_FAILED", "exc_type": type(exc).__name__}
                        ),
                        "latency_ms": max(0, int((time.monotonic() - started) * 1000)),
                    }
                )
                await self._persist_failed_generation_invocation(command, base_receipt)
                raise MkbError("GENERATION_INFERENCE_FAILED", "Structured generation failed", 503) from exc
            usage = response.usage
            base_receipt.update(
                {
                    "inference_invocation_uuid": response.invocation_uuid or base_receipt["inference_invocation_uuid"],
                    "output_digest": stable_digest({"value": response.value, "text": response.text}),
                    "request_digest": response.request_digest or request_digest,
                    "latency_ms": response.latency_ms
                    if response.latency_ms is not None
                    else max(0, int((time.monotonic() - started) * 1000)),
                    "input_tokens": None if usage is None else usage.input_tokens,
                    "output_tokens": None if usage is None else usage.output_tokens,
                    "total_tokens": None if usage is None else usage.total_tokens,
                }
            )
            # The value is a transient handoff to the kernel caller.  The
            # durable invocation receipt remains body-free because callers
            # select only the ledger fields below when building stage state.
            base_receipt["_structured_output"] = response.value
            return base_receipt


    async def _live_layered_summary_generate(
            self,
            command: ProcessCommand,
            *,
            layered_candidate: Mapping[str, object],
        ) -> tuple[dict[str, object], dict[str, Any]]:
            """Run C once for the complete adopted layered package."""

            receipt = await self._live_structured_generate(
                command,
                stage_key="construct",
                input_text=_json(layered_candidate),
                prompt_key="promptC.default",
                prompt_version="v1",
                prompt_role="summarizer",
                schema_key="lsrag.layered_content.default",
                schema_version="v1",
                input_digest=stable_digest({"layered_candidate": layered_candidate, "stage": "construct"}),
            )
            output = receipt.pop("_structured_output", None)
            if not isinstance(output, dict):
                raise MkbError("CONSTRUCT_KERNEL_SUMMARY_INVALID", "C did not return a layered JSON package", 422)
            return output, receipt


    async def _persist_failed_generation_invocation(
            self, command: ProcessCommand, invocation: Mapping[str, Any]
        ) -> None:
            """Stash a failed invocation for the Process Outcome transaction."""

            from src.runtime.intake.generation_evidence import record_pending_generation_evidence

            payload = dict(invocation)
            payload.setdefault("status", "failed")
            record_pending_generation_evidence(invocation=payload)


    async def _record_generation_and_inference_invocations(
            self,
            tx: UnitOfWork,
            command: ProcessCommand,
            invocation: Mapping[str, Any],
        ) -> None:
            """Persist linked S06/S07 generation + S11 inference ledgers (no bodies)."""

            now = utc_now()
            from src.contracts.observability.stage_report import evidence_stage_key

            status = invocation.get("status") or "succeeded"
            stage_key = evidence_stage_key(invocation.get("stage_key") or "structurize")
            adapter_kind = invocation.get("adapter_kind") or "local_inference"
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_generation_invocations "
                "(invocation_uuid,team_uuid,execution_uuid,process_uuid,process_attempt,invocation_ordinal,"
                "invocation_kind,model_key,model_version,prompt_key,prompt_version,prompt_digest,"
                "schema_key,schema_version,schema_digest,input_digest,output_digest,error_digest,"
                "input_tokens,output_tokens,total_tokens,occurred_at,payload_extra,"
                "status,stage_key,error_code,adapter_kind,cli_structured_kind) "
                "VALUES (?,?,?,?,?,?,'generation',?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    invocation["invocation_uuid"],
                    command.team_uuid,
                    command.execution_uuid,
                    command.process_uuid,
                    int(invocation["process_attempt"]),
                    int(invocation["invocation_ordinal"]),
                    invocation.get("model_key"),
                    invocation.get("model_version"),
                    invocation.get("prompt_key"),
                    invocation.get("prompt_version"),
                    invocation.get("prompt_digest"),
                    invocation.get("schema_key"),
                    invocation.get("schema_version"),
                    invocation.get("schema_digest"),
                    invocation["input_digest"],
                    invocation.get("output_digest"),
                    invocation.get("error_digest"),
                    invocation.get("input_tokens"),
                    invocation.get("output_tokens"),
                    invocation.get("total_tokens"),
                    now,
                    _json(
                        {
                            "capability_key": invocation.get("capability_key"),
                            "binding_digest": invocation.get("binding_digest"),
                            "request_digest": invocation.get("request_digest"),
                            "latency_ms": invocation.get("latency_ms"),
                        }
                    ),
                    status,
                    stage_key,
                    invocation.get("error_code"),
                    adapter_kind,
                    invocation.get("cli_structured_kind"),
                ),
            )
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_inference_invocations "
                "(invocation_uuid,team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid,capability_key,adapter_kind,"
                "model_key,model_version,request_digest,status,error_code,input_tokens,output_tokens,total_tokens,latency_ms,"
                "generation_invocation_uuid,occurred_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    invocation.get("inference_invocation_uuid") or uuid7(),
                    command.team_uuid,
                    command.trace_uuid,
                    command.task_uuid,
                    command.execution_uuid,
                    command.process_uuid,
                    invocation["capability_key"],
                    invocation.get("adapter_kind"),
                    invocation.get("model_key"),
                    invocation.get("model_version"),
                    invocation.get("request_digest") or invocation["input_digest"],
                    invocation.get("status") or "succeeded",
                    invocation.get("error_code"),
                    invocation.get("input_tokens"),
                    invocation.get("output_tokens"),
                    invocation.get("total_tokens"),
                    invocation.get("latency_ms"),
                    invocation["invocation_uuid"],
                    now,
                    _json(
                        {
                            "prompt_content_hash": invocation.get("prompt_digest"),
                            "schema_content_digest": invocation.get("schema_digest"),
                            "config_snapshot_digest": command.config_snapshot_digest,
                            "stage_key": invocation.get("stage_key"),
                        }
                    ),
                ),
            )
            from src.services.events import DomainEventWriter

            await DomainEventWriter().write(
                tx,
                team_uuid=command.team_uuid,
                trace_uuid=command.trace_uuid,
                event_type="generation.invocation_recorded",
                aggregate="generation",
                summary="Generation invocation recorded",
                task_uuid=command.task_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                payload={"invocation_uuid": invocation["invocation_uuid"]},
            )

    async def _record_stage_report(
            self,
            tx: UnitOfWork,
            command: ProcessCommand,
            report: Mapping[str, Any],
        ) -> None:
            from src.contracts.common.ids import uuid7
            from src.contracts.common.time import utc_now
            from src.contracts.observability.stage_report import validate_stage_report

            projected = validate_stage_report(report)
            has_g0 = projected.get("has_g0")
            counts = projected.get("layer_counts") or {}
            await tx.execute(
                "INSERT INTO mkb_generation_stage_reports "
                "(report_uuid,team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid,stage_key,"
                "disposition,error_code,cli_structured_kind,has_g0,block_count,granularity_set,"
                "layer_counts,latency_ms,schema_digest,occurred_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (
                    uuid7(),
                    command.team_uuid,
                    command.trace_uuid,
                    command.task_uuid,
                    command.execution_uuid,
                    command.process_uuid,
                    projected["stage_key"],
                    projected["disposition"],
                    projected.get("error_code"),
                    projected.get("cli_structured_kind"),
                    None if has_g0 is None else int(has_g0),
                    projected.get("block_count"),
                    projected.get("granularity_set"),
                    _json(counts) if counts else None,
                    int(projected["latency_ms"]),
                    projected["schema_digest"],
                    utc_now(),
                    "{}",
                ),
            )

    async def _flush_pending_generation_evidence(self, tx: UnitOfWork, command: ProcessCommand) -> None:
            from src.runtime.intake.generation_evidence import take_pending_generation_evidence

            for item in take_pending_generation_evidence():
                invocation = item.get("invocation")
                if isinstance(invocation, Mapping):
                    await self._record_generation_and_inference_invocations(tx, command, invocation)
                report = item.get("report")
                if isinstance(report, Mapping):
                    await self._record_stage_report(tx, command, report)
