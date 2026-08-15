"""Structurize/construct stages and reconstruct contracts."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.inference.models import InferenceBinding, InvocationContext, TextGenerateRequest
from src.contracts.runtime.models import ProcessCommand
from src.persistence.ports import UnitOfWork
from src.runtime.inference.claude_cli import BJSON_MATERIAL_SCHEMA, ClaudeCliRequest
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
    projection_digest,
    retrieval_projection_payload,
    structure_document_digest,
    structure_payload,
)
from src.services.lsrag_construct import LsragConstructService, bind_construct
from src.services.lsrag_structurize import LsragStructurizeService, bind_structurize
from src.services.prompt_profiles import COMPRESSION_CHANNELS, DEFAULT_COMPRESSION_CHANNEL

# Lightning returned no usable C result.  One explicit non-interactive salvage
# is allowed.  Config/fence gaps stay fail-closed and never switch channels.
_API_INFERENCE_SALVAGE_CODES = frozenset(
    {
        "INFERENCE_VALIDATION_RESPONSE",
        "INFERENCE_VALIDATION_STRUCTURED",
        "INFERENCE_VALIDATION_REMOTE",
        "INFERENCE_TRANSPORT_RETRYABLE",
        "INFERENCE_TRANSPORT_EXHAUSTED",
        "INFERENCE_BACKPRESSURE",
        "INFERENCE_INTERNAL_UNEXPECTED",
        "GENERATION_INFERENCE_FAILED",
        "CONSTRUCT_KERNEL_SUMMARY_INVALID",
        "CONSTRUCT_KERNEL_SUMMARY_INCOMPLETE",
        "CONSTRUCT_KERNEL_ALIGNMENT_INVALID",
        "CONSTRUCT_KERNEL_ORIGINAL_MUTATION",
        "STRUCTURE_SUMMARY_INVALID",
        "STRUCTURE_SCHEMA_INVALID",
    }
)


class IntakeGenerationConstructMixin:
    """Structurize/construct stages and reconstruct contracts."""

    @staticmethod
    def _has_frozen_prompt_selection(state: Mapping[str, Any] | None, role: str) -> bool:
        if state is None:
            return False
        payload = state.get("payload")
        selection = payload.get("prompt_selection") if isinstance(payload, Mapping) else None
        return isinstance(selection, Mapping) and isinstance(selection.get(role), Mapping)

    @staticmethod
    def _layered_profile(state: Mapping[str, Any], *, error_code: str) -> tuple[int, ...]:
        raw = state.get("layered_content_profile")
        if raw is None:
            raw = state.get("granularity_set")
        payload = state.get("payload")
        prompt_selection = payload.get("prompt_selection") if isinstance(payload, Mapping) else None
        json_prompt = prompt_selection.get("json") if isinstance(prompt_selection, Mapping) else None
        if raw is None and isinstance(json_prompt, Mapping):
            raw = json_prompt.get("granularity_set")
        if not isinstance(raw, list | tuple) or not raw:
            raise MkbError(error_code, "Layered granularity profile is unavailable", 409)
        values = tuple(sorted(set(raw)))
        if any(isinstance(value, bool) or not isinstance(value, int) or value not in {0, 1, 2} for value in values) or 0 not in values:
            raise MkbError(error_code, "Layered granularity profile is invalid", 409)
        return values

    @staticmethod
    def _compression_channel(state: Mapping[str, Any], command: ProcessCommand | None = None) -> str:
        """Resolve the generate transport channel.

        ``ProcessCommand.dispatch_pool`` is the immutable SSOT after admit.
        Payload / DEFAULT are only used when no generate pool was assigned.
        """

        assigned = getattr(command, "dispatch_pool", None) if command is not None else None
        if assigned in COMPRESSION_CHANNELS:
            return assigned
        payload = state.get("payload")
        raw = payload.get("compression_channel") if isinstance(payload, Mapping) else None
        if raw is None:
            return DEFAULT_COMPRESSION_CHANNEL
        if not isinstance(raw, str) or raw not in COMPRESSION_CHANNELS:
            raise MkbError("COMPRESSION_CHANNEL_INVALID", "Compression channel is not registered", 422)
        return raw

    def _summary_transport(self, state: Mapping[str, Any], command: ProcessCommand | None = None) -> str:
        """Choose C transport from the admitted dispatch pool (or frozen payload).

        ``local-inference`` is Local vLLM generate via the facade.  ``non-interactive``
        keeps Claude ``-p`` when a CLI is wired; otherwise it stays deterministic.
        """

        channel = self._compression_channel(state, command)
        if channel == "local-inference":
            if not getattr(self, "_live_inference", False) or getattr(self, "_inference", None) is None:
                raise MkbError(
                    "COMPRESSION_CHANNEL_UNAVAILABLE",
                    "local-inference compression requires live inference",
                    503,
                )
            return "api_inference"
        if getattr(self, "_claude_cli", None) is not None:
            return "claude_cli"
        return "deterministic"

    def _can_salvage_local_inference(self, exc: MkbError, command: ProcessCommand | None = None) -> bool:
        if exc.code not in _API_INFERENCE_SALVAGE_CODES:
            return False
        if getattr(self, "_claude_cli", None) is None:
            return False
        if command is None or getattr(command, "dispatch_pool", None) != "local-inference":
            return False
        if getattr(command, "task_priority", None) != "normal":
            return False
        billing = getattr(self, "_billing", None)
        if billing is not None and not billing.has_quota("non-interactive"):
            return False
        return True

    def _can_salvage_api_inference(self, exc: MkbError, command: ProcessCommand | None = None) -> bool:
        return self._can_salvage_local_inference(exc, command)

    async def _salvage_summary_via_cli(
        self,
        *,
        layered_candidate: Mapping[str, object],
        profile: tuple[int, ...],
        state: Mapping[str, Any] | None,
        salvage_error: MkbError,
    ) -> tuple[dict[str, object], dict[str, object]]:
        completed, receipt = await self._cli_layered_summary(
            layered_candidate=layered_candidate,
            profile=profile,
            state=state,
        )
        receipt["transport"] = "claude_cli"
        receipt["compression_channel"] = "non-interactive"
        receipt["salvage_from"] = "local-inference"
        receipt["salvage_error_code"] = salvage_error.code
        return completed, receipt

    async def _complete_construct_summaries(
        self,
        command: ProcessCommand,
        state: Mapping[str, Any],
        *,
        compiler: LsragContractCompiler,
        projection: RetrievalBlockProjection,
        accepted_layered_candidate: Mapping[str, object],
        profile: tuple[int, ...],
    ) -> tuple[dict[str, object], dict[str, str], list[dict[str, Any]], dict[str, object] | None]:
        """Fill C summaries. local-inference may salvage once via Claude ``-p``."""

        transport = self._summary_transport(state, command)
        if transport == "claude_cli":
            completed, receipt = await self._cli_layered_summary(
                layered_candidate=accepted_layered_candidate,
                profile=profile,
                state=state,
            )
            summaries = compiler.layered_summary_map(
                layered_json=completed,
                projection=projection,
                accepted_layered_json=accepted_layered_candidate,
            )
            return completed, summaries, [], receipt
        if transport != "api_inference":
            summaries = deterministic_summaries(projection)
            completed = compiler.fill_layered_summaries(
                accepted_layered_json=accepted_layered_candidate,
                projection=projection,
                summaries_by_block_id=summaries,
            )
            return completed, summaries, [], None

        try:
            completed_value, receipt = await self._live_layered_summary_generate(
                command,
                layered_candidate=accepted_layered_candidate,
            )
            if not isinstance(completed_value, Mapping):
                raise MkbError("CONSTRUCT_KERNEL_SUMMARY_INVALID", "C did not return a layered JSON package", 422)
            completed = dict(completed_value)
            try:
                summaries = compiler.layered_summary_map(
                    layered_json=completed,
                    projection=projection,
                    accepted_layered_json=accepted_layered_candidate,
                )
            except MkbError as kernel_exc:
                receipt.update(
                    {
                        "status": "failed",
                        "error_code": kernel_exc.code,
                        "error_digest": stable_digest({"error_code": kernel_exc.code}),
                        "transport": "api_inference",
                        "compression_channel": "local-inference",
                    }
                )
                persist = getattr(self, "_persist_failed_generation_invocation", None)
                if persist is not None:
                    await persist(command, receipt)
                raise
            receipt["transport"] = "api_inference"
            receipt["compression_channel"] = "local-inference"
            return completed, summaries, [receipt], None
        except MkbError as exc:
            if not self._can_salvage_local_inference(exc, command):
                raise
            completed, cli_receipt = await self._salvage_summary_via_cli(
                layered_candidate=accepted_layered_candidate,
                profile=profile,
                state=state,
                salvage_error=exc,
            )
            summaries = compiler.layered_summary_map(
                layered_json=completed,
                projection=projection,
                accepted_layered_json=accepted_layered_candidate,
            )
            return completed, summaries, [], cli_receipt

    @staticmethod
    def _bjson_user_material(*, clean_text: str, markdown_text: str | None) -> str:
        markdown = markdown_text if isinstance(markdown_text, str) and markdown_text.strip() else None
        return json.dumps(
            {"schema_version": BJSON_MATERIAL_SCHEMA, "clean": clean_text, "markdown": markdown},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )

    @classmethod
    def _structurize_input_text(cls, state: Mapping[str, Any], clean_text: str) -> str:
        markdown = state.get("markdown_text")
        markdown_text = markdown if isinstance(markdown, str) and markdown.strip() else None
        return cls._bjson_user_material(clean_text=clean_text, markdown_text=markdown_text)

    def _prompt_relative_path(self, prompt_path: Path) -> str:
        try:
            return prompt_path.relative_to(self._prompt_root).as_posix()
        except ValueError:
            return prompt_path.name

    def _cli_invocation_from_receipt(
        self,
        command: ProcessCommand,
        receipt: Mapping[str, object],
        *,
        stage_key: str,
        capability_key: str,
        input_digest: str,
    ) -> dict[str, Any]:
        usage = receipt.get("usage") if isinstance(receipt.get("usage"), Mapping) else {}
        return {
            "invocation_uuid": uuid7(),
            "inference_invocation_uuid": uuid7(),
            "invocation_ordinal": 0,
            "process_attempt": command.fencing_generation,
            "capability_key": capability_key,
            "stage_key": stage_key,
            "input_digest": input_digest,
            "output_digest": receipt.get("output_digest"),
            "status": "succeeded",
            "adapter_kind": "claude_cli",
            "prompt_key": receipt.get("prompt_relative_path"),
            "prompt_version": receipt.get("prompt_version"),
            "prompt_digest": receipt.get("prompt_sha256"),
            "schema_key": "lsrag.layered_content.default" if receipt.get("schema_relative_path") else None,
            "schema_version": "v1" if receipt.get("schema_relative_path") else None,
            "request_digest": stable_digest(
                {"transport": "claude_cli", "role": receipt.get("role"), "input_digest": input_digest}
            ),
            "input_tokens": usage.get("input_tokens") if isinstance(usage, Mapping) else None,
            "output_tokens": usage.get("output_tokens") if isinstance(usage, Mapping) else None,
            "total_tokens": usage.get("total_tokens") if isinstance(usage, Mapping) else None,
        }

    @staticmethod
    def _layered_state_candidate(state: Mapping[str, Any], *, error_code: str) -> Mapping[str, object]:
        candidate = state.get("layered_content_candidate")
        if not isinstance(candidate, Mapping):
            raise MkbError(error_code, "Accepted layered JSON candidate is unavailable", 409)
        return candidate

    def _ns1_prompt_file(
        self,
        relative_path: str,
        *,
        error_code: str,
        state: Mapping[str, Any] | None = None,
        role: str | None = None,
    ) -> tuple[Path, str]:
        if role is not None:
            if state is None:
                raise MkbError(error_code, f"Frozen {role} prompt state is unavailable", 503)
            path, pointer = self._frozen_prompt_file(state, role=role, error_code=error_code)
            return path, str(pointer["content_sha256"])
        path = (self._prompt_root / relative_path).resolve()
        try:
            path.relative_to(self._prompt_root)
            data = path.read_bytes()
        except (OSError, ValueError) as exc:
            raise MkbError(error_code, "NS1 prompt bytes are unavailable", 503) from exc
        return path, hashlib.sha256(data).hexdigest()

    @staticmethod
    def _ns1_schema_path() -> Path:
        return Path(__file__).resolve().parents[3] / "data" / "schemas" / "lsrag.layered_content.v1.json"

    async def _cli_layered_candidate(
        self,
        *,
        clean_text: str,
        input_text: str | None = None,
        profile: tuple[int, ...],
        state: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, object], dict[str, object]]:
        cli = getattr(self, "_claude_cli", None)
        if cli is None:
            raise MkbError("STRUCTURE_CANDIDATE_MISSING", "No layered candidate worker is configured", 503)
        if state is not None and not self._has_frozen_prompt_selection(state, "json"):
            raise MkbError("PROMPT_NOT_REGISTERED", "Frozen json prompt pointer is unavailable", 503)
        prompt_path, prompt_digest = self._ns1_prompt_file(
            "json/promptB.json.generic.v1.md",
            error_code="PROMPT_HASH_MISMATCH",
            state=state,
            role="json" if state is not None else None,
        )
        try:
            schema = json.loads(self._ns1_schema_path().read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MkbError("STRUCTURE_SCHEMA_UNAVAILABLE", "Layered content schema bytes are unavailable", 503) from exc
        if not isinstance(schema, Mapping):
            raise MkbError("STRUCTURE_SCHEMA_UNAVAILABLE", "Layered content schema is invalid", 503)
        result = await cli.run(
            ClaudeCliRequest(
                user_prompt=clean_text if input_text is None else input_text,
                system_prompt_file=prompt_path,
                json_schema=schema,
                role="json",
                granularity_set=profile,
            )
        )
        if not isinstance(result.structured_output, Mapping):
            raise MkbError("STRUCTURE_CANDIDATE_INVALID", "B.json worker did not return structured output", 422)
        candidate = dict(result.structured_output)
        pointer = None
        if state is not None:
            _, pointer = self._frozen_prompt_file(state, role="json", error_code="PROMPT_HASH_MISMATCH")
        receipt: dict[str, object] = {
            "transport": "claude_cli",
            "role": "json",
            "prompt_relative_path": self._prompt_relative_path(prompt_path),
            "prompt_version": None if pointer is None else pointer.get("version") or pointer.get("prompt_version"),
            "prompt_sha256": prompt_digest,
            "schema_relative_path": "data/schemas/lsrag.layered_content.v1.json",
            "session_id": result.session_id,
            "usage": None if result.usage is None else dict(result.usage),
            "exit_code": result.exit_code,
            "output_digest": stable_digest(candidate),
        }
        return candidate, receipt

    async def _cli_layered_summary(
        self,
        *,
        layered_candidate: Mapping[str, object],
        profile: tuple[int, ...],
        state: Mapping[str, Any] | None = None,
    ) -> tuple[dict[str, object], dict[str, object]]:
        cli = getattr(self, "_claude_cli", None)
        if cli is None:
            raise MkbError("CONSTRUCT_KERNEL_SUMMARY_INVALID", "No layered summary worker is configured", 503)
        if state is not None and not self._has_frozen_prompt_selection(state, "summarizer"):
            raise MkbError("PROMPT_NOT_REGISTERED", "Frozen summarizer prompt pointer is unavailable", 503)
        prompt_path, prompt_digest = self._ns1_prompt_file(
            "summarizer/promptC.summarizer.v1.md",
            error_code="PROMPT_HASH_MISMATCH",
            state=state,
            role="summarizer" if state is not None else None,
        )
        try:
            schema = json.loads(self._ns1_schema_path().read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise MkbError("CONSTRUCT_SCHEMA_UNAVAILABLE", "Layered content schema bytes are unavailable", 503) from exc
        if not isinstance(schema, Mapping):
            raise MkbError("CONSTRUCT_SCHEMA_UNAVAILABLE", "Layered content schema is invalid", 503)
        result = await cli.run(
            ClaudeCliRequest(
                user_prompt=_json(layered_candidate),
                system_prompt_file=prompt_path,
                json_schema=schema,
                role="summarizer",
                granularity_set=profile,
            )
        )
        if not isinstance(result.structured_output, Mapping):
            raise MkbError("CONSTRUCT_KERNEL_SUMMARY_INVALID", "C worker did not return structured output", 422)
        completed = dict(result.structured_output)
        pointer = None
        if state is not None:
            _, pointer = self._frozen_prompt_file(state, role="summarizer", error_code="PROMPT_HASH_MISMATCH")
        receipt: dict[str, object] = {
            "transport": "claude_cli",
            "compression_channel": "non-interactive",
            "role": "summarizer",
            "prompt_relative_path": self._prompt_relative_path(prompt_path),
            "prompt_version": None if pointer is None else pointer.get("version") or pointer.get("prompt_version"),
            "prompt_sha256": prompt_digest,
            "schema_relative_path": "data/schemas/lsrag.layered_content.v1.json",
            "session_id": result.session_id,
            "usage": None if result.usage is None else dict(result.usage),
            "exit_code": result.exit_code,
            "output_digest": stable_digest(completed),
        }
        return completed, receipt

    async def _live_markdown_text(
        self,
        command: ProcessCommand,
        *,
        clean_text: str,
        prompt_path: Path,
        prompt_digest: str,
        state: Mapping[str, Any],
    ) -> tuple[str, dict[str, object]]:
        if not getattr(self, "_live_inference", False) or getattr(self, "_inference", None) is None:
            raise MkbError(
                "COMPRESSION_CHANNEL_UNAVAILABLE",
                "local-inference compression requires live inference",
                503,
            )
        snapshot = await self._load_config_snapshot(command)
        try:
            raw_binding = snapshot["l1"]["bindings"]["text_generate"]
        except (KeyError, TypeError) as exc:
            raise MkbError("GENERATION_CONFIG_SNAPSHOT_INVALID", "Frozen text_generate binding is invalid", 503) from exc
        if not isinstance(raw_binding, dict):
            raise MkbError("GENERATION_CONFIG_SNAPSHOT_INVALID", "Frozen text_generate binding is invalid", 503)
        try:
            binding = InferenceBinding(
                capability_key="text_generate",
                adapter_kind=raw_binding["adapter_kind"],
                model_key=raw_binding["model_key"],
                model_version=raw_binding["model_version"],
                binding_digest=str(raw_binding["binding_digest"]),
            )
        except (KeyError, TypeError, ValueError) as exc:
            raise MkbError("GENERATION_CONFIG_SNAPSHOT_INVALID", "Frozen text_generate binding is invalid", 503) from exc
        try:
            system_text = prompt_path.read_text(encoding="utf-8")
        except OSError as exc:
            raise MkbError("PROMPT_HASH_MISMATCH", "Frozen markdown prompt bytes are unavailable", 503) from exc
        _, pointer = self._frozen_prompt_file(state, role="markdown", error_code="PROMPT_HASH_MISMATCH")
        generation_uuid = uuid7()
        response = await self._inference.text_generate(
            TextGenerateRequest(
                team_uuid=command.team_uuid,
                binding=binding,
                prompt_ref=str(pointer.get("prompt_id") or "promptB.markdown"),
                prompt_digest=prompt_digest,
                input_text=clean_text,
                system_text=system_text,
                invocation=InvocationContext(
                    trace_uuid=command.trace_uuid,
                    task_uuid=command.task_uuid,
                    execution_uuid=command.execution_uuid,
                    process_uuid=command.process_uuid,
                    generation_invocation_uuid=generation_uuid,
                    prompt_content_hash=prompt_digest,
                    config_snapshot_digest=command.config_snapshot_digest,
                ),
            )
        )
        markdown = (response.text or "").strip()
        if not markdown:
            raise MkbError("MARKDOWN_OUTPUT_INVALID", "Markdown worker returned empty output", 422)
        return markdown, {
            "transport": "api_inference",
            "role": "markdown",
            "prompt_relative_path": self._prompt_relative_path(prompt_path),
            "prompt_version": pointer.get("version") or pointer.get("prompt_version"),
            "prompt_sha256": prompt_digest,
            "session_id": None,
            "usage": None if response.usage is None else dict(response.usage),
            "exit_code": 0,
            "output_digest": stable_digest({"text": markdown}),
            "compression_channel": "local-inference",
        }

    async def _transcribe_markdown(
        self,
        command: ProcessCommand,
        state: dict[str, Any],
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        clean = self._generation_clean_text(state, error_code="MARKDOWN_INPUT_INVALID")
        channel = self._compression_channel(state, command)
        if not self._has_frozen_prompt_selection(state, "markdown"):
            raise MkbError("PROMPT_NOT_REGISTERED", "Frozen markdown prompt pointer is unavailable", 503)
        prompt_path, prompt_digest = self._ns1_prompt_file(
            "markdown/promptB.markdown.legal.v1.md",
            error_code="PROMPT_HASH_MISMATCH",
            state=state,
            role="markdown",
        )
        if channel == "local-inference":
            markdown, receipt = await self._live_markdown_text(
                command,
                clean_text=clean,
                prompt_path=prompt_path,
                prompt_digest=prompt_digest,
                state=state,
            )
        else:
            cli = getattr(self, "_claude_cli", None)
            if cli is None:
                raise MkbError("MARKDOWN_WORKER_UNAVAILABLE", "Markdown worker is not configured", 503)
            result = await cli.run(
                ClaudeCliRequest(
                    user_prompt=clean,
                    system_prompt_file=prompt_path,
                    role="markdown",
                )
            )
            markdown = result.text.strip()
            if not markdown:
                raise MkbError("MARKDOWN_OUTPUT_INVALID", "Markdown worker returned empty output", 422)
            _, pointer = self._frozen_prompt_file(state, role="markdown", error_code="PROMPT_HASH_MISMATCH")
            receipt = {
                "transport": "claude_cli",
                "role": "markdown",
                "prompt_relative_path": self._prompt_relative_path(prompt_path),
                "prompt_version": pointer.get("version") or pointer.get("prompt_version"),
                "prompt_sha256": prompt_digest,
                "session_id": result.session_id,
                "usage": None if result.usage is None else dict(result.usage),
                "exit_code": result.exit_code,
                "output_digest": stable_digest({"text": markdown}),
                "compression_channel": "non-interactive",
            }
        next_state = dict(state)
        next_state.update(
            {
                "markdown_text": markdown,
                "markdown_digest": stable_digest({"text": markdown}),
                "markdown_cli_receipt": receipt,
            }
        )
        material = self._material(
            command,
            next_state,
            {
                "markdown_artifact": {
                    "content_digest": next_state["markdown_digest"],
                    "char_count": len(markdown),
                    "transport": "claude_cli",
                }
            },
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            del refs
            invocation = self._cli_invocation_from_receipt(
                command,
                receipt,
                stage_key="transcribe_markdown",
                capability_key="text_generate",
                input_digest=state["clean_digest"],
            )
            await self._record_generation_and_inference_invocations(tx, command, invocation)

        return material, {}, callback

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
            structure_data = await self._read_metadata_refresh_member(
                command, structure_receipt, error_code="METADATA_REFRESH_SOURCE_INVALID"
            )
            projection_data = await self._read_metadata_refresh_member(
                command, projection_receipt, error_code="METADATA_REFRESH_SOURCE_INVALID"
            )
            compiler, structure, projection = LsragConstructService().reprove_structure_from_stored_payloads(
                clean_text=clean,
                structure_data=structure_data,
                projection_data=projection_data,
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
            construct_service = LsragConstructService(compiler)
            construction, dual = construct_service.admit(
                bind_construct(
                    mode=self._construct_mode(state),
                    clean_text=self._generation_clean_text(state, error_code="CONSTRUCT_TO_VECTORIZE_GATE"),
                    structure=structure,
                    projection=projection,
                    summaries_by_block_id=summaries,
                    construction_artifact_uuid=construction_uuid,
                    dual_channel_artifact_uuid=dual_uuid,
                    metadata_headers=metadata_headers,
                    required_granularities=required_granularities,
                )
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
            construct_service.assert_construction_bytes(
                construction=construction,
                dual=dual,
                construction_data=construction_data,
                dual_data=dual_data,
                construction_digest=state.get("construction_document_digest")
                if isinstance(state.get("construction_document_digest"), str)
                else None,
            )
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
            cli_receipt: dict[str, object] | None = None
            layered_candidate: Mapping[str, object] | None = None
            profile = self._layered_profile(state, error_code="STRUCTURE_PROFILE_INVALID")
            structurize_input = self._structurize_input_text(state, clean)
            channel = self._compression_channel(state, command)
            if state.get("layered_content_candidate") is None and channel == "local-inference":
                generation_invocation = await self._live_structured_generate(
                    command,
                    stage_key="structurize",
                    input_text=structurize_input,
                    prompt_key="promptB.json.generic",
                    prompt_version="v1",
                    prompt_role="json",
                    schema_key="lsrag.layered_content.default",
                    schema_version="v1",
                    input_digest=stable_digest({"clean_digest": state["clean_digest"], "stage": "structurize"}),
                )
                live_candidate = generation_invocation.pop("_structured_output", None)
                if isinstance(live_candidate, Mapping):
                    layered_candidate = live_candidate
            elif (
                state.get("layered_content_candidate") is None
                and channel == "non-interactive"
                and getattr(self, "_claude_cli", None) is not None
            ):
                generated_candidate, cli_receipt = await self._cli_layered_candidate(
                    clean_text=clean,
                    input_text=structurize_input,
                    profile=profile,
                    state=state,
                )
                layered_candidate = generated_candidate
            if layered_candidate is None:
                layered_candidate = self._layered_state_candidate(
                    state,
                    error_code="STRUCTURE_CANDIDATE_MISSING",
                )
            profile = self._layered_profile(state, error_code="STRUCTURE_PROFILE_INVALID")
            admitted = LsragStructurizeService().admit(
                bind_structurize(
                    clean_text=clean,
                    clean_artifact_uuid=clean_artifact_uuid,
                    clean_digest=state["clean_digest"],
                    layered_candidate=layered_candidate,
                    granularity_set=profile,
                    structure_artifact_uuid=structure_artifact_uuid,
                    projection_artifact_uuid=projection_artifact_uuid,
                )
            )
            accepted_candidate = admitted.accepted_candidate
            structure = admitted.structure
            projection = admitted.projection
            adoption_report = admitted.adoption_report
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
            if cli_receipt is not None:
                next_state["structure_cli_receipt"] = cli_receipt
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
                elif cli_receipt is not None:
                    await self._record_generation_and_inference_invocations(
                        tx,
                        command,
                        self._cli_invocation_from_receipt(
                            command,
                            cli_receipt,
                            stage_key="structurize",
                            capability_key="structured_generate",
                            input_digest=stable_digest({"clean_digest": state["clean_digest"], "stage": "structurize"}),
                        ),
                    )
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
            cli_receipt: dict[str, object] | None = None
            completed_layered_candidate: dict[str, object] | None = None
            accepted_layered_candidate: Mapping[str, object] | None = None
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
                (
                    completed_layered_candidate,
                    summaries,
                    generation_invocations,
                    cli_receipt,
                ) = await self._complete_construct_summaries(
                    command,
                    state,
                    compiler=compiler,
                    projection=projection,
                    accepted_layered_candidate=accepted_layered_candidate,
                    profile=profile,
                )
                if completed_layered_candidate is None:
                    raise MkbError("CONSTRUCT_KERNEL_SUMMARY_INVALID", "Completed layered JSON package is unavailable", 422)
                required_granularities = frozenset(profile)
                metadata_headers = None
            construction_artifact_uuid = uuid7()
            dual_channel_artifact_uuid = uuid7()
            validation_artifact_uuid = uuid7()
            construction, dual = LsragConstructService(compiler).admit(
                bind_construct(
                    mode=construct_mode,
                    clean_text=self._generation_clean_text(state, error_code="CONSTRUCT_BINDING_CLEAN_DIGEST"),
                    structure=structure,
                    projection=projection,
                    summaries_by_block_id=summaries,
                    construction_artifact_uuid=construction_artifact_uuid,
                    dual_channel_artifact_uuid=dual_channel_artifact_uuid,
                    metadata_headers=metadata_headers,
                    required_granularities=required_granularities,
                )
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
                    "compression_channel": self._compression_channel(state, command),
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
            if cli_receipt is not None:
                next_state["construct_cli_receipt"] = cli_receipt
                if cli_receipt.get("salvage_from") == "local-inference":
                    next_state["compression_salvage"] = {
                        "from": "local-inference",
                        "to": "non-interactive",
                        "error_code": cli_receipt.get("salvage_error_code"),
                    }
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
                            "transport",
                            "compression_channel",
                            "salvage_from",
                            "salvage_error_code",
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
                if cli_receipt is not None:
                    await self._record_generation_and_inference_invocations(
                        tx,
                        command,
                        self._cli_invocation_from_receipt(
                            command,
                            cli_receipt,
                            stage_key="construct",
                            capability_key="structured_generate",
                            input_digest=(
                                stable_digest(accepted_layered_candidate)
                                if accepted_layered_candidate is not None
                                else stable_digest({"construct_mode": construct_mode})
                            ),
                        ),
                    )
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
