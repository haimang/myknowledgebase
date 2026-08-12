"""Clean, seal, and preflight validation stages."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.persistence.ports import UnitOfWork
from src.runtime.intake.types import (
    _clean_text,
    _digest_bytes,
    _extract_html_text,
    _StageMaterial,
)


class IntakeCleanPreflightMixin:
    """Clean, seal, and preflight validation stages."""

    async def _clean(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            media_type = state.get("media_type")
            if command.process_key in {"clean.ocr.local", "clean.extract.vision"} and (
                not isinstance(media_type, str) or not media_type.startswith("image/")
            ):
                raise MkbError("CLEAN_CAPABILITY_MISMATCH", "Image clean capability requires image evidence", 409)
            if command.process_key == "clean.extract.deterministic" and isinstance(media_type, str) and media_type.startswith("image/"):
                raise MkbError("CLEAN_CAPABILITY_MISMATCH", "Image representation requires an image clean capability", 409)
            if command.process_key == "clean.ocr.local":
                raise MkbError(
                    "CLEAN_OCR_CAPABILITY_UNAVAILABLE",
                    "Local OCR is not configured for this deployment",
                    503,
                )
            if command.process_key == "clean.extract.vision":
                raise MkbError(
                    "CLEAN_VISION_CAPABILITY_UNAVAILABLE",
                    "Vision clean is not configured for this deployment",
                    503,
                )
            decoded = state.get("decoded_text")
            if not isinstance(decoded, str):
                raise MkbError("PIPELINE_INPUT_INVALID", "Decoded representation is unavailable", 422)
            if media_type == "text/html":
                clean, clean_evidence = _extract_html_text(decoded)
            else:
                clean = _clean_text(decoded)
                clean_evidence = {"parser": "deterministic-text-normalizer.v1", "removed_tag_counts": {}}
            if not clean:
                raise MkbError("CLEAN_EMPTY", "Cleaning produced no admissible text", 422)
            next_state = dict(state)
            next_state["clean_text"] = clean
            next_state["clean_digest"] = stable_digest({"text": clean})
            next_state["clean_evidence"] = {
                "clean_capability": "clean.extract.deterministic",
                "input_decoded_digest": state.get("decoded_digest"),
                **clean_evidence,
            }
            material = self._material(
                command,
                next_state,
                {
                    "clean_candidate": {
                        "content_digest": next_state["clean_digest"],
                        "char_count": len(clean),
                        "evidence": next_state["clean_evidence"],
                    }
                },
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
                if raw_member.get("media_type") == "text/html":
                    clean_text, clean_evidence = _extract_html_text(raw_text)
                else:
                    clean_text = _clean_text(raw_text)
                    clean_evidence = {"parser": "deterministic-text-normalizer.v1", "removed_tag_counts": {}}
                if not clean_text:
                    raise MkbError("CLEAN_EMPTY", "Registered API member cleaning produced no admissible text", 422)
                member = dict(raw_member)
                member["clean_text"] = clean_text
                member["clean_digest"] = stable_digest({"text": clean_text})
                member["clean_evidence"] = {
                    "clean_capability": "clean.map.registered_api",
                    "input_raw_digest": member["raw_digest"],
                    **clean_evidence,
                }
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
            if not isinstance(clean, Mapping) or clean.get("clean_capability") != "clean.extract.deterministic":
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
                or clean.get("clean_capability") != "clean.extract.deterministic"
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
            ):
                raise MkbError("PREFLIGHT_EVIDENCE_INVALID", "Registered API acquisition evidence is incomplete", 422)
            if any(
                not isinstance(member, Mapping)
                or member.get("member_ordinal") != ordinal
                or not isinstance(member.get("clean_text"), str)
                or not isinstance(member.get("clean_digest"), str)
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
