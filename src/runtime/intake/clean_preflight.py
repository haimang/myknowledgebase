"""Clean, seal, and preflight validation stages."""

from __future__ import annotations

import hashlib
from collections.abc import Awaitable, Callable, Mapping
from pathlib import Path
from typing import Any

from intake import dispatch_clean
from intake.types import CleanLanguageModel, CleanMember, CleanPrompt, CleanResult
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.common.time import utc_now
from src.contracts.intake.strategies import CleanStrategyKey, resolve_clean_strategy
from src.contracts.runtime.models import ProcessCommand
from src.persistence.ports import UnitOfWork
from src.runtime.inference.claude_cli import ClaudeCliCleanLanguageModel
from src.runtime.intake.types import (
    _digest_bytes,
    _StageMaterial,
)


class IntakeCleanPreflightMixin:
    """Clean, seal, and preflight validation stages."""

    async def _clean(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            media_type = state.get("media_type")
            if command.process_key == "clean.extract.vision" and (
                not isinstance(media_type, str) or not media_type.startswith("image/")
            ):
                raise MkbError("CLEAN_CAPABILITY_MISMATCH", "Vision clean capability requires image evidence", 409)
            if command.process_key == "clean.ocr.local" and (
                not isinstance(media_type, str)
                or (not media_type.startswith("image/") and media_type != "application/pdf")
            ):
                raise MkbError("CLEAN_CAPABILITY_MISMATCH", "OCR clean capability requires image or PDF evidence", 409)
            if command.process_key == "clean.extract.deterministic" and isinstance(media_type, str) and media_type.startswith("image/"):
                raise MkbError("CLEAN_CAPABILITY_MISMATCH", "Image representation requires an image clean capability", 409)
            decoded = state.get("decoded_text")
            if command.process_key not in {"clean.ocr.local", "clean.extract.vision"} and not isinstance(decoded, str):
                raise MkbError("PIPELINE_INPUT_INVALID", "Decoded representation is unavailable", 422)
            representation_kind = (state.get("acquisition_evidence") or {}).get("representation_kind")
            representation = (
                "print_pdf"
                if representation_kind == "print_pdf"
                else "rendered"
                if representation_kind == "rendered"
                else "static"
            )
            strategy = {
                "clean.extract.deterministic": CleanStrategyKey.DOC_DETERMINISTIC.value,
                "clean.extract.web": CleanStrategyKey.WEB_DETERMINISTIC.value,
                "clean.extract.web_llm": CleanStrategyKey.WEB_LLM_REWRITE.value,
                "clean.extract.pdf_text": CleanStrategyKey.PDF_TEXT_LAYER.value,
                "clean.extract.pdf_llm": (
                    CleanStrategyKey.WEB_BROWSER_PRINT_PDF.value
                    if representation == "print_pdf"
                    else CleanStrategyKey.PDF_DOCUMENT_UNDERSTANDING.value
                ),
                "clean.extract.doc_llm": CleanStrategyKey.DOC_DOCUMENT_UNDERSTANDING.value,
                "clean.ocr.local": (
                    CleanStrategyKey.PDF_OCR.value
                    if media_type == "application/pdf"
                    else CleanStrategyKey.DOC_OCR.value
                ),
                "clean.extract.vision": CleanStrategyKey.DOC_VISION.value,
            }.get(command.process_key)
            if strategy is None:
                raise MkbError("CLEAN_STRATEGY_UNSUPPORTED", "Process has no registered clean strategy", 409)
            prompt = await self._clean_prompt_material(command, strategy, state=state)
            llm = self._clean_language_model()
            cli_clean_supported = command.process_key not in {"clean.ocr.local", "clean.extract.vision"}
            channel = None
            if command.dispatch_pool in {"local-inference", "non-interactive"}:
                channel = command.dispatch_pool
            if channel == "local-inference" and llm is None:
                raise MkbError(
                    "COMPRESSION_CHANNEL_UNAVAILABLE",
                    "local-inference clean requires an injected language model",
                    503,
                )
            if (
                llm is None
                and channel != "local-inference"
                and cli_clean_supported
                and resolve_clean_strategy(strategy).llm_required
                and getattr(self, "_claude_cli", None) is not None
            ):
                if prompt is None:
                    raise MkbError("PROMPT_HASH_MISMATCH", "CLI clean path lacks its frozen prompt pointer", 503)
                payload = state.get("payload")
                has_selection = isinstance(payload, Mapping) and isinstance(payload.get("prompt_selection"), Mapping)
                if has_selection:
                    prompt_path, _ = self._frozen_prompt_file(state, role="clean")
                else:
                    prompt_path = (self._prompt_root / "prompt-a-clean-v1.md").resolve()
                try:
                    prompt_digest = hashlib.sha256(prompt_path.read_bytes()).hexdigest()
                except OSError as exc:
                    raise MkbError("PROMPT_HASH_MISMATCH", "CLI clean prompt bytes are unavailable", 503) from exc
                if prompt_digest != prompt.content_sha256:
                    raise MkbError("PROMPT_HASH_MISMATCH", "CLI clean prompt bytes do not match the frozen pointer", 503)
                llm = ClaudeCliCleanLanguageModel(self._claude_cli, system_prompt_file=prompt_path)
            result = await dispatch_clean(
                command.process_key,
                text=decoded if isinstance(decoded, str) else None,
                blob=self._clean_blob(state),
                media_type=media_type if isinstance(media_type, str) else None,
                source_kind=state.get("source_kind") if isinstance(state.get("source_kind"), str) else None,
                url=self._clean_source_url(state),
                representation=representation,
                strategy=strategy,
                llm=llm,
                prompt=prompt,
                http_fetch=self._http_fetcher,
                browser_fetch=self._browser_fetcher,
            )
            if not isinstance(result, CleanResult):
                raise MkbError("CLEAN_RESULT_INVALID", "Single-document clean did not return a text artifact", 500)
            next_state = dict(state)
            next_state["clean_text"] = result.text
            next_state["clean_digest"] = stable_digest({"text": result.text})
            next_state["clean_evidence"] = {
                "clean_capability": result.capability,
                "input_decoded_digest": state.get("decoded_digest"),
                **result.evidence,
            }
            material = self._material(
                command,
                next_state,
                {
                    "clean_candidate": {
                        "content_digest": next_state["clean_digest"],
                        "char_count": len(result.text),
                        "evidence": next_state["clean_evidence"],
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                del tx, refs

            return material, {}, callback

    def _clean_language_model(self) -> CleanLanguageModel | None:
        injected = getattr(self, "_clean_llm", None)
        return injected if injected is not None else None

    async def _clean_prompt_material(
        self,
        command: ProcessCommand,
        strategy: str,
        *,
        state: Mapping[str, Any] | None = None,
    ) -> CleanPrompt | None:
        definition = resolve_clean_strategy(strategy)
        if not definition.llm_required or (
            self._clean_language_model() is None and getattr(self, "_claude_cli", None) is None
        ):
            return None
        injected = getattr(self, "_clean_prompt", None)
        if injected is not None:
            if (
                not isinstance(injected, CleanPrompt)
                or injected.key != definition.prompt_key
                or injected.version != definition.prompt_version
            ):
                raise MkbError("PROMPT_HASH_MISMATCH", "Injected clean prompt does not match the strategy", 503)
            return injected
        if state is not None and isinstance(state.get("payload"), Mapping):
            prompt_selection = state["payload"].get("prompt_selection")
            if isinstance(prompt_selection, Mapping) and prompt_selection.get("clean") is not None:
                path, pointer = self._frozen_prompt_file(state, role="clean")
                try:
                    prompt_bytes = path.read_bytes()
                    prompt_text = prompt_bytes.decode("utf-8")
                except (OSError, UnicodeDecodeError) as exc:
                    raise MkbError("PROMPT_HASH_MISMATCH", "Frozen clean prompt bytes are unavailable", 503) from exc
                return CleanPrompt(
                    key=str(pointer.get("prompt_id")),
                    version=str(pointer.get("version")),
                    text=prompt_text,
                    content_sha256=str(pointer.get("content_sha256")),
                )
        snapshot = await self._load_config_snapshot(command)
        prompts = (snapshot.get("l1") or {}).get("prompts")
        if not isinstance(prompts, list):
            raise MkbError("PROMPT_HASH_MISMATCH", "Frozen clean prompt registry is unavailable", 503)
        pointer = next(
            (
                item
                for item in prompts
                if isinstance(item, Mapping)
                and item.get("prompt_key") == definition.prompt_key
                and item.get("prompt_version") == definition.prompt_version
            ),
            None,
        )
        if not isinstance(pointer, Mapping):
            raise MkbError("PROMPT_HASH_MISMATCH", "Frozen clean prompt pointer is unavailable", 503)
        relative_path = pointer.get("git_relative_path")
        expected_sha = pointer.get("content_sha256")
        if not isinstance(relative_path, str) or not isinstance(expected_sha, str):
            raise MkbError("PROMPT_HASH_MISMATCH", "Frozen clean prompt pointer is invalid", 503)
        path_fragment = Path(relative_path)
        if path_fragment.is_absolute() or ".." in path_fragment.parts:
            raise MkbError("PROMPT_HASH_MISMATCH", "Frozen clean prompt path is invalid", 503)
        prompt_path = (self._prompt_root / path_fragment).resolve()
        try:
            prompt_path.relative_to(self._prompt_root)
            prompt_bytes = prompt_path.read_bytes()
            prompt_text = prompt_bytes.decode("utf-8")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise MkbError("PROMPT_HASH_MISMATCH", "Frozen clean prompt bytes are unavailable", 503) from exc
        actual_sha = hashlib.sha256(prompt_bytes).hexdigest()
        if actual_sha != expected_sha:
            raise MkbError("PROMPT_HASH_MISMATCH", "Clean prompt bytes do not match the frozen pointer", 503)
        return CleanPrompt(
            key=definition.prompt_key or "",
            version=definition.prompt_version or "",
            text=prompt_text,
            content_sha256=actual_sha,
        )

    @staticmethod
    def _clean_blob(state: Mapping[str, Any]) -> bytes | None:
        raw = state.get("raw_text")
        if isinstance(raw, str) and state.get("raw_binary_transport"):
            return raw.encode("latin-1")
        return None

    @staticmethod
    def _clean_source_url(state: Mapping[str, Any]) -> str | None:
        source = state.get("source")
        if isinstance(source, Mapping):
            url = source.get("url")
            if isinstance(url, str) and url:
                return url
        evidence = state.get("acquisition_evidence")
        if isinstance(evidence, Mapping):
            url = evidence.get("request_url") or evidence.get("final_url")
            if isinstance(url, str) and url:
                return url
        return None

    async def _clean_registered_api(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            """Map every acquired API member into an independently clean candidate."""

            if state.get("operation_mode") != "scatter_root" or state.get("source_kind") != "registered_api":
                raise MkbError("SCATTER_STATE_INVALID", "Registered API clean map lacks a collection root", 409)
            raw_members = state.get("collection_members")
            if not isinstance(raw_members, list):
                raise MkbError("SCATTER_STATE_INVALID", "Registered API member list is unavailable", 422)
            mapped = await dispatch_clean(
                command.process_key,
                members=raw_members,
                provider=state.get("api_provider") if isinstance(state.get("api_provider"), str) else None,
                operation=state.get("api_operation") if isinstance(state.get("api_operation"), str) else None,
                definition_version=(
                    state.get("api_definition_version")
                    if isinstance(state.get("api_definition_version"), str)
                    else None
                ),
            )
            if not isinstance(mapped, list):
                raise MkbError("CLEAN_RESULT_INVALID", "Registered API clean did not return members", 500)
            clean_members: list[dict[str, Any]] = []
            for item in mapped:
                if not isinstance(item, CleanMember):
                    raise MkbError("CLEAN_RESULT_INVALID", "Registered API clean member is invalid", 500)
                member = dict(raw_members[item.ordinal])
                member["member_ordinal"] = item.ordinal
                member["external_key"] = item.external_key
                member["normalized_external_key"] = item.normalized_external_key
                member["raw_digest"] = item.raw_digest
                member["content_digest"] = item.content_digest
                member["meta_digest"] = item.meta_digest
                member["clean_text"] = item.clean_text
                member["clean_digest"] = stable_digest({"text": item.clean_text})
                member["clean_evidence"] = item.evidence
                member["parsed_payload"] = item.payload
                member["filter_meta"] = item.filter_meta
                member["context_meta"] = item.context_meta
                member["semantic_tuples"] = list(item.semantic_tuples)
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
                            "content_digest": member["content_digest"],
                            "meta_digest": member["meta_digest"],
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
            next_state["collection_clean_evidence"] = {
                "clean_capability": command.process_key,
                "provider": state.get("api_provider"),
                "operation": state.get("api_operation"),
                "definition_version": state.get("api_definition_version"),
                "member_count": len(clean_members),
            }
            material = self._material(
                command,
                next_state,
                {
                    "clean_collection": {
                        "candidate_root_digest": candidate_root_digest,
                        "member_count": len(clean_members),
                        "clean_digest": next_state["collection_clean_digest"],
                        "evidence": next_state["collection_clean_evidence"],
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
                        stable_digest(
                            {
                                "process_key": state.get("acquisition_capability", "intake.acquire.inline"),
                                "evidence": state.get("raw_byte_digest"),
                            }
                        ),
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
                        "open",
                        None,
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
            if state.get("collection_exhaustion_proof") != "caller_frozen_records.v1":
                raise MkbError(
                    "SCATTER_EXHAUSTION_PROOF_REQUIRED",
                    "Registered API collection cannot seal complete without exhaustion proof",
                    422,
                )
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
                        stable_digest(
                            {
                                "process_key": state.get("acquisition_capability", "intake.acquire.registered_api"),
                                "evidence": state.get("raw_digest"),
                            }
                        ),
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
                        "open",
                        None,
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
            if state.get("operation_mode") in {"rebuild", "metadata_update"}:
                checks = self._validate_rebuild_preflight_evidence(state)
            else:
                checks = self._validate_single_preflight_evidence(state)
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
                        "validator_key": "mkb.intake.preflight.deterministic",
                        "validator_version": "v1",
                        "check_set_version": "s05-evidence-completeness.v1",
                        "admission_result": admission,
                        "reason": reason,
                        "candidate_root_digest": state.get("candidate_root_digest"),
                        "checks": checks,
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                await self._seal_open_candidate_set_tx(
                    tx,
                    team_uuid=command.team_uuid,
                    candidate_set_uuid=state["candidate_set_uuid"],
                    preflight_ref=refs["output_ref"],
                    preflight_digest=refs["output_digest"],
                    admission_result=admission,
                    fence_message="Preflight could not seal the open candidate set",
                )

            return material, {}, callback

    @staticmethod
    async def _seal_open_candidate_set_tx(
        tx: UnitOfWork,
        *,
        team_uuid: str,
        candidate_set_uuid: str,
        preflight_ref: str,
        preflight_digest: str,
        admission_result: str,
        fence_message: str,
    ) -> None:
        """CAS open→sealed and bind validator refs on that seal edge (D02 R1)."""

        now = utc_now()
        updated = await tx.execute(
            "UPDATE mkb_intake_candidate_sets SET staging_state='sealed',seal_at=COALESCE(seal_at,?),"
            "preflight_outcome_ref=?,preflight_outcome_digest=?,admission_result=?,"
            "row_revision=row_revision+1,updated_at=? "
            "WHERE candidate_set_uuid=? AND team_uuid=? AND staging_state='open'",
            (
                now,
                preflight_ref,
                preflight_digest,
                admission_result,
                now,
                candidate_set_uuid,
                team_uuid,
            ),
        )
        if updated.rowcount != 1:
            raise MkbError("CANDIDATE_SET_FENCE", fence_message, 409)

    @staticmethod
    def _validate_single_preflight_evidence(state: Mapping[str, Any]) -> list[dict[str, str]]:
            """Validate frozen evidence only; this must never acquire or clean."""

            source = state.get("source")
            evidence = state.get("acquisition_evidence")
            decode = state.get("decode_evidence")
            clean = state.get("clean_evidence")
            source_kind = state.get("source_kind")
            if not isinstance(source, Mapping) or not isinstance(evidence, Mapping):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Acquisition evidence is unavailable", 422)
            mode = source.get("acquisition_mode", "staged_inline") if source_kind == "http_resource" else None
            expected_capability = {
                "inline_payload": "intake.acquire.inline",
                "local_object": "intake.acquire.local_object",
                "http_resource": "intake.acquire.http_browser" if mode == "browser" else "intake.acquire.http_static",
            }.get(source_kind)
            if expected_capability is None or evidence.get("acquisition_capability") != expected_capability:
                raise MkbError("PREFLIGHT_BINDING_INVALID", "Frozen acquisition capability does not match the source profile", 409)
            digest = evidence.get("raw_byte_digest")
            size = evidence.get("raw_byte_size")
            if (
                evidence.get("schema_version") != "mkb.acquisition-evidence.v1"
                or evidence.get("source_kind") != source_kind
                or not isinstance(digest, str)
                or len(digest) != 64
                or isinstance(size, bool)
                or not isinstance(size, int)
                or size < 1
                or evidence.get("verified_media_type") != state.get("media_type")
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Frozen acquisition representation evidence is incomplete", 422)
            if source_kind == "http_resource":
                if not all(isinstance(evidence.get(key), str) and evidence[key] for key in ("request_url_identity", "final_url_identity")):
                    raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "HTTP acquisition identity evidence is incomplete", 422)
                if mode == "browser" and (
                    evidence.get("representation_kind") != "rendered"
                    or not isinstance(evidence.get("browser_profile"), str)
                ):
                    raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Browser acquisition lacks rendered evidence", 422)
            expected_decode = "intake.decode.pdf" if state.get("media_type") == "application/pdf" else "intake.decode.text_json_html"
            if not isinstance(decode, Mapping) or decode.get("decode_capability") != expected_decode:
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Decode evidence is unavailable", 422)
            decoded = state.get("decoded_text")
            decoded_digest = state.get("decoded_digest")
            if (
                not isinstance(decoded, str)
                or not isinstance(decoded_digest, str)
                or decoded_digest
                != stable_digest(
                    {
                        "canonicalizer": expected_decode,
                        "media_type": state.get("media_type"),
                        "text": decoded,
                    }
                )
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Decoded representation failed its frozen digest fence", 409)
            if not isinstance(clean, Mapping) or not str(clean.get("clean_capability") or "").startswith("clean."):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Clean evidence is unavailable", 422)
            clean_text = state.get("clean_text")
            clean_digest = state.get("clean_digest")
            if (
                clean.get("input_decoded_digest") != decoded_digest
                or not isinstance(clean_text, str)
                or not isinstance(clean_digest, str)
                or clean_digest != stable_digest({"text": clean_text})
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Clean evidence does not bind the decoded representation", 409)
            root_digest = state.get("candidate_root_digest")
            if (
                not isinstance(root_digest, str)
                or root_digest
                != stable_digest(
                    {
                        "external_key": state.get("normalized_external_key"),
                        "clean_digest": clean_digest,
                    }
                )
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Candidate set is not sealed", 422)
            return [
                {"key": "binding_matches_source_profile", "result": "passed"},
                {"key": "acquisition_representation_complete", "result": "passed"},
                {"key": "decode_clean_lineage_complete", "result": "passed"},
                {"key": "candidate_set_complete", "result": "passed"},
            ]

    @staticmethod
    def _validate_rebuild_preflight_evidence(state: Mapping[str, Any]) -> list[dict[str, str]]:
            """Validate a rebuild's immutable accepted-clean input without refetching.

            ``intake.rebuild`` and a semantic metadata update may replay only the
            clean Artifact frozen with their target Revision.  Treating that input
            as a new inline/local/HTTP acquisition would both misstate provenance
            and let a mutable descriptor influence a rebuild.  This branch keeps
            the mandatory preflight while checking the stronger closed lineage.
            """

            target = state.get("frozen_target")
            evidence = state.get("rebuild_input_evidence")
            if not isinstance(target, Mapping) or not isinstance(evidence, Mapping):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Frozen rebuild input evidence is unavailable", 422)
            clean_artifact = target.get("clean_artifact")
            required_target = (
                "team_uuid",
                "intake_source_uuid",
                "intake_item_uuid",
                "intake_revision_uuid",
                "source_snapshot_uuid",
                "source_kind",
                "normalized_external_key",
            )
            if (
                target.get("schema_version") != "mkb.frozen-intake-target.v1"
                or any(not isinstance(target.get(key), str) or not target[key] for key in required_target)
                or not isinstance(clean_artifact, Mapping)
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Frozen rebuild target is incomplete", 422)
            if target["team_uuid"] != state.get("team_uuid"):
                raise MkbError("PREFLIGHT_BINDING_INVALID", "Frozen rebuild target belongs to another Team", 409)
            if any(
                state.get(key) != target[key]
                for key in ("intake_source_uuid", "intake_item_uuid", "intake_revision_uuid", "source_kind", "normalized_external_key")
            ):
                raise MkbError("PREFLIGHT_BINDING_INVALID", "Rebuild state does not match its frozen target", 409)
            required_clean = ("logical_handle", "content_digest", "intake_artifact_uuid")
            if any(not isinstance(clean_artifact.get(key), str) or not clean_artifact[key] for key in required_clean):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Frozen rebuild clean Artifact is incomplete", 422)
            if (
                evidence.get("schema_version") != "mkb.rebuild-clean-input-evidence.v1"
                or evidence.get("input_kind") != "accepted_clean_artifact"
                or any(evidence.get(key) != target[key] for key in required_target)
                or evidence.get("clean_artifact_uuid") != clean_artifact["intake_artifact_uuid"]
                or evidence.get("clean_content_digest") != clean_artifact["content_digest"]
                or evidence.get("clean_handle_digest") != stable_digest({"handle": clean_artifact["logical_handle"]})
            ):
                raise MkbError("PREFLIGHT_BINDING_INVALID", "Frozen rebuild input is not bound to the accepted clean Artifact", 409)
            raw = state.get("raw_text")
            clean_text = state.get("clean_text")
            clean_digest = state.get("clean_digest")
            if (
                not isinstance(raw, str)
                or not isinstance(clean_text, str)
                or evidence.get("clean_text_digest") != stable_digest({"text": raw})
                or clean_digest != clean_artifact["content_digest"]
                or clean_digest != stable_digest({"text": clean_text})
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Rebuild clean representation failed its digest fence", 409)
            if (
                state.get("media_type") != "text/plain"
                or state.get("raw_byte_digest") != _digest_bytes(raw.encode("utf-8"))
                or state.get("raw_byte_size") != len(raw.encode("utf-8"))
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Rebuild representation evidence is incomplete", 422)
            decode = state.get("decode_evidence")
            decoded = state.get("decoded_text")
            decoded_digest = state.get("decoded_digest")
            if (
                not isinstance(decode, Mapping)
                or decode.get("decode_capability") != "intake.decode.text_json_html"
                or decode.get("input_raw_byte_digest") != state.get("raw_byte_digest")
                or not isinstance(decoded, str)
                or decoded_digest
                != stable_digest(
                    {
                        "canonicalizer": "intake.decode.text_json_html",
                        "media_type": "text/plain",
                        "text": decoded,
                    }
                )
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Rebuild decode evidence is unavailable", 422)
            clean = state.get("clean_evidence")
            if (
                not isinstance(clean, Mapping)
                or not str(clean.get("clean_capability") or "").startswith("clean.")
                or clean.get("input_decoded_digest") != decoded_digest
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Rebuild clean evidence is unavailable", 422)
            root_digest = state.get("candidate_root_digest")
            if root_digest != stable_digest({"external_key": target["normalized_external_key"], "clean_digest": clean_digest}):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Rebuild candidate set is not sealed", 422)
            return [
                {"key": "frozen_clean_artifact_binding", "result": "passed"},
                {"key": "rebuild_representation_complete", "result": "passed"},
                {"key": "rebuild_decode_clean_lineage_complete", "result": "passed"},
                {"key": "candidate_set_complete", "result": "passed"},
            ]

    async def _preflight_registered_api_collection(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            members = state.get("collection_members")
            evidence = state.get("acquisition_evidence")
            if not isinstance(members, list) or not isinstance(state.get("candidate_root_digest"), str):
                raise MkbError("SCATTER_STATE_INVALID", "Collection preflight lacks a sealed candidate set", 422)
            if (
                not isinstance(evidence, Mapping)
                or evidence.get("acquisition_capability") != "intake.acquire.registered_api"
                or evidence.get("completeness_evidence") != "caller_frozen_records.v1"
                or evidence.get("member_count") != len(members)
                or evidence.get("provider") != state.get("api_provider")
                or evidence.get("operation") != state.get("api_operation")
                or evidence.get("definition_version") != state.get("api_definition_version")
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Registered API acquisition evidence is incomplete", 422)
            if any(
                not isinstance(member, Mapping)
                or member.get("member_ordinal") != ordinal
                or not isinstance(member.get("clean_text"), str)
                or not isinstance(member.get("clean_digest"), str)
                or not isinstance(member.get("content_digest"), str)
                or not isinstance(member.get("meta_digest"), str)
                or not isinstance(member.get("filter_meta"), Mapping)
                or not isinstance(member.get("context_meta"), Mapping)
                or not isinstance(member.get("semantic_tuples"), list)
                for ordinal, member in enumerate(members)
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Registered API member evidence is incomplete", 422)
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
                        "validator_key": "mkb.intake.preflight.deterministic",
                        "validator_version": "v1",
                        "check_set_version": "s05-evidence-completeness.v1",
                        "admission_result": admission,
                        "reason": reason,
                        "candidate_root_digest": state["candidate_root_digest"],
                        "member_count": len(members),
                        "checks": [
                            {"key": "registered_api_binding", "result": "passed"},
                            {"key": "registered_api_completeness", "result": "passed"},
                            {"key": "registered_api_member_lineage", "result": "passed"},
                        ],
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                await self._seal_open_candidate_set_tx(
                    tx,
                    team_uuid=command.team_uuid,
                    candidate_set_uuid=state["candidate_set_uuid"],
                    preflight_ref=refs["output_ref"],
                    preflight_digest=refs["output_digest"],
                    admission_result=admission,
                    fence_message="Preflight could not seal the open collection",
                )

            return material, {}, callback
