"""Primary ingest acquisition and decode (inline/HTTP/local/API)."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.models import ObjectHandle
from src.persistence.ports import UnitOfWork
from src.runtime.http_acquisition import HttpAcquisitionResult, redacted_url_identity
from src.runtime.intake.types import (
    _AcquiredContent,
    _canonical_json_text,
    _canonical_text,
    _digest_bytes,
    _extract_pdf_text,
    _normalized_media_type,
    _sniff_media_type,
    _StageMaterial,
    _verified_media_type,
)


class IntakeAcquisitionIngestMixin:
    """Primary ingest acquisition and decode (inline/HTTP/local/API)."""

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
                return await self._acquire_registered_api_collection(command, descriptor, payload=payload)
            expected_capability = self._expected_acquisition_capability(descriptor)
            if command.process_key != expected_capability:
                raise MkbError("ACQUISITION_CAPABILITY_MISMATCH", "Source kind does not match the bound acquisition capability", 409)
            acquired = await self._acquire_content(command, descriptor)
            if not acquired.is_binary and not acquired.raw_text.strip():
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
                "raw_text": acquired.raw_text,
                "raw_binary_transport": acquired.is_binary,
                # Existing Intake/S04 artifact coordinates use this representation
                # digest.  Preserve it for historical workflow compatibility while
                # retaining the independently auditable raw-byte digest below.
                "raw_digest": stable_digest({"media_type": acquired.media_type, "text": acquired.raw_text}),
                "raw_byte_digest": acquired.evidence["raw_byte_digest"],
                "raw_byte_size": acquired.evidence["raw_byte_size"],
                "declared_media_type": acquired.evidence["declared_media_type"],
                "detected_media_type": acquired.evidence["detected_media_type"],
                "media_type": acquired.media_type,
                "acquisition_capability": acquired.evidence["acquisition_capability"],
                "acquisition_evidence": acquired.evidence,
                "require_human_review": bool(descriptor.get("require_human_review", False)),
                "intake_source_uuid": uuid7(),
                "candidate_set_uuid": uuid7(),
                "intake_snapshot_uuid": uuid7(),
                "intake_item_uuid": uuid7(),
                "intake_revision_uuid": uuid7(),
                "raw_artifact_uuid": uuid7(),
                "clean_artifact_uuid": uuid7(),
                "observed_at": now,
                "payload": payload,
            }
            material = self._material(
                command,
                next_state,
                {
                    "acquisition_evidence": {
                        "source_kind": source_kind,
                        "acquisition_capability": acquired.evidence["acquisition_capability"],
                        "declared_media_type": acquired.evidence["declared_media_type"],
                        "detected_media_type": acquired.evidence["detected_media_type"],
                        "verified_media_type": acquired.media_type,
                        "content_digest": next_state["raw_digest"],
                        "byte_count": acquired.evidence["raw_byte_size"],
                        "evidence": acquired.evidence,
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


    @staticmethod
    def _expected_acquisition_capability(descriptor: Mapping[str, Any]) -> str:
            source_kind = descriptor.get("source_kind")
            if source_kind == "inline_payload":
                return "intake.acquire.inline"
            if source_kind == "local_object":
                return "intake.acquire.local_object"
            if source_kind == "http_resource":
                mode = descriptor.get("acquisition_mode", "static")
                if mode == "browser":
                    return "intake.acquire.http_browser"
                if mode in {"static", "pdf"}:
                    return "intake.acquire.http_static"
            raise MkbError("ACQUISITION_CAPABILITY_MISMATCH", "Source profile has no registered acquisition capability", 409)


    async def _acquire_registered_api_collection(
            self,
            command: ProcessCommand,
            descriptor: Mapping[str, Any],
            *,
            payload: Mapping[str, Any],
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            """Acquire an ordered typed API collection without flattening members.

            Each input record already passed its provider-specific strict public
            contract.  Acquisition freezes raw records only; the sole provider
            parser remains behind ``intake.dispatch_clean``.
            """

            if command.process_key != "intake.acquire.registered_api":
                raise MkbError("ACQUISITION_CAPABILITY_MISMATCH", "Registered API requires its scatter acquisition capability", 409)
            external_key = descriptor.get("external_key")
            records = descriptor.get("records")
            provider = descriptor.get("provider")
            operation = descriptor.get("operation")
            definition_version = descriptor.get("definition_version")
            if not isinstance(external_key, str) or not external_key.strip() or not isinstance(records, list):
                raise MkbError("ACQUISITION_RECORDS_REQUIRED", "Registered API records are required", 422)
            if not all(isinstance(value, str) and value for value in (provider, operation, definition_version)):
                raise MkbError("CLEAN_PROVIDER_OPERATION_REQUIRED", "Registered API provider binding is required", 422)
            members: list[dict[str, Any]] = []
            for ordinal, record in enumerate(records):
                if not isinstance(record, dict):
                    raise MkbError("ACQUISITION_RECORD_INVALID", "Registered API record must be an object", 422)
                canonical_record = dict(record)
                raw_member_digest = stable_digest(
                    {
                        "provider": provider,
                        "operation": operation,
                        "definition_version": definition_version,
                        "raw": canonical_record,
                    }
                )
                members.append(
                    {
                        "member_ordinal": ordinal,
                        "raw_record": canonical_record,
                        "raw_digest": raw_member_digest,
                        "require_human_review": False,
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
                            "raw_digest": member["raw_digest"],
                        }
                        for member in members
                    ],
                }
            )
            collection_byte_count = sum(len(canonical_json(member["raw_record"])) for member in members)
            exhaustion_proof = descriptor.get("exhaustion_proof")
            acquisition_evidence = {
                "schema_version": "mkb.acquisition-evidence.v1",
                "source_kind": "registered_api",
                "acquisition_capability": "intake.acquire.registered_api",
                "acquisition_mode": "registered_api",
                "member_count": len(members),
                "raw_byte_digest": raw_digest,
                "raw_byte_size": collection_byte_count,
                "declared_media_type": "application/json",
                "detected_media_type": "application/json",
                "verified_media_type": "application/json",
                "provider": provider,
                "operation": operation,
                "definition_version": definition_version,
                "representation": descriptor.get("representation"),
                "completeness_evidence": exhaustion_proof,
                "budget_verdict": "within_registered_api_member_budget",
            }
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
                "api_provider": provider,
                "api_operation": operation,
                "api_definition_version": definition_version,
                "collection_exhaustion_proof": exhaustion_proof,
                "raw_digest": raw_digest,
                "acquisition_capability": "intake.acquire.registered_api",
                "acquisition_evidence": acquisition_evidence,
                "require_human_review": bool(descriptor.get("require_human_review", False)),
                "intake_source_uuid": uuid7(),
                "candidate_set_uuid": uuid7(),
                "intake_snapshot_uuid": uuid7(),
                "change_set_uuid": uuid7(),
                "raw_artifact_uuid": uuid7(),
                "observed_at": now,
                "payload": dict(payload),
            }
            material = self._material(
                command,
                next_state,
                {
                    "acquisition_evidence": {
                        "source_kind": "registered_api",
                        "acquisition_capability": "intake.acquire.registered_api",
                        "member_count": len(members),
                        "content_digest": raw_digest,
                        "byte_count": collection_byte_count,
                        "completeness": "complete" if exhaustion_proof == "caller_frozen_records.v1" else "unproven",
                        "evidence": acquisition_evidence,
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


    async def _acquire_content(self, command: ProcessCommand, descriptor: Mapping[str, Any]) -> _AcquiredContent:
            """Acquire one representation with immutable, redaction-safe evidence.

            The source descriptor chooses only a registered kind/profile.  It can
            never inject headers, paths, browser options, or an OCR/Vision model.
            The returned evidence is deliberately compact enough for a stage
            envelope, while raw bytes remain behind the object/HTTP boundary.
            """

            source_kind = descriptor.get("source_kind")
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
                return self._representation_from_bytes(
                    data,
                    declared_media_type=_normalized_media_type(descriptor.get("media_type")) or "text/plain",
                    capability="intake.acquire.inline",
                    source_kind="inline_payload",
                    mode="staged_inline",
                    extra_evidence={"logical_handle_digest": stable_digest({"handle": handle})},
                )
            if source_kind == "local_object":
                handle = descriptor.get("logical_handle")
                if not isinstance(handle, str):
                    raise MkbError("ACQUISITION_HANDLE_INVALID", "Local object handle is required", 422)
                data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=handle))
                return self._representation_from_bytes(
                    data,
                    declared_media_type=_normalized_media_type(descriptor.get("media_type")),
                    capability="intake.acquire.local_object",
                    source_kind="local_object",
                    mode="logical_object",
                    extra_evidence={"logical_handle_digest": stable_digest({"handle": handle})},
                )
            if source_kind == "registered_api":
                records = descriptor.get("records")
                if not isinstance(records, list):
                    raise MkbError("ACQUISITION_RECORDS_REQUIRED", "Registered API records are required", 422)
                data = canonical_json(records)
                return self._representation_from_bytes(
                    data,
                    declared_media_type="application/json",
                    capability="intake.acquire.registered_api",
                    source_kind="registered_api",
                    mode="registered_api",
                    extra_evidence={"member_count": len(records), "exhaustion_proof": descriptor.get("exhaustion_proof")},
                )
            if source_kind != "http_resource":
                raise MkbError("SOURCE_KIND_INVALID", "Source kind is not registered", 422)
            url = descriptor.get("url")
            if not isinstance(url, str) or not url.strip():
                raise MkbError("ACQUISITION_URL_INVALID", "HTTP source URL is required", 422)
            mode = descriptor.get("acquisition_mode", "static")
            if mode not in {"static", "browser", "pdf"}:
                raise MkbError("ACQUISITION_MODE_INVALID", "HTTP acquisition mode is not registered", 422)
            if mode == "browser":
                fetcher = self._browser_fetcher
                capability = "intake.acquire.http_browser"
                if fetcher is None:
                    raise MkbError(
                        "ACQUISITION_BROWSER_CAPABILITY_UNAVAILABLE",
                        "Browser acquisition is not configured for this deployment",
                        503,
                    )
            else:
                fetcher = self._http_fetcher
                capability = "intake.acquire.http_static"
                if fetcher is None:
                    raise MkbError("ACQUISITION_HTTP_UNAVAILABLE", "HTTP acquisition is not configured", 503)
            # ``HttpAcquirer`` exposes its evidence-aware method without making
            # that transport type a public descriptor dependency.  Narrow mocked
            # callables retain the simple callable seam used by focused tests.
            acquire = getattr(fetcher, "acquire", None)
            result = acquire(url) if callable(acquire) else fetcher(url)
            if inspect.isawaitable(result):
                result = await result
            http_evidence: dict[str, Any]
            if isinstance(result, HttpAcquisitionResult):
                data = result.body
                http_evidence = result.evidence()
                declared = result.response_media_type
            elif isinstance(result, str):
                data = result.encode("utf-8")
                declared = None
                http_evidence = {
                    "request_url_identity": redacted_url_identity(url),
                    "final_url_identity": redacted_url_identity(url),
                    "response_media_type": None,
                    "http_status": None,
                    "redirect_count": None,
                    "transport_profile": "injected-fetcher.v1",
                }
            elif isinstance(result, bytes):
                data = result
                declared = None
                http_evidence = {
                    "request_url_identity": redacted_url_identity(url),
                    "final_url_identity": redacted_url_identity(url),
                    "response_media_type": None,
                    "http_status": None,
                    "redirect_count": None,
                    "transport_profile": "injected-fetcher.v1",
                }
            else:
                raise MkbError("ACQUISITION_RESPONSE_INVALID", "HTTP acquisition returned invalid content", 502)
            return self._representation_from_bytes(
                data,
                declared_media_type=declared,
                capability=capability,
                source_kind="http_resource",
                mode=mode,
                extra_evidence={
                    **http_evidence,
                    "representation_kind": "rendered" if mode == "browser" else "transferred",
                    "browser_profile": "injected-browser-renderer.v1" if mode == "browser" else None,
                },
            )


    @staticmethod
    def _representation_from_bytes(
            data: bytes,
            *,
            declared_media_type: str | None,
            capability: str,
            source_kind: str,
            mode: str,
            extra_evidence: Mapping[str, Any] | None = None,
        ) -> _AcquiredContent:
            """Classify bounded bytes without pretending media metadata is truth."""

            declared = _normalized_media_type(declared_media_type)
            detected = _sniff_media_type(data)
            verified = _verified_media_type(declared=declared, detected=detected, mode=mode)
            binary = verified == "application/pdf" or verified.startswith("image/")
            if binary:
                raw_text = data.decode("latin-1")
                encoding = {"label": "binary", "bom": False, "replacement_count": 0}
            else:
                try:
                    raw_text = data.decode("utf-8-sig")
                except UnicodeDecodeError as exc:
                    raise MkbError("ACQUISITION_DECODE_UNSUPPORTED", "Representation is not supported UTF-8 text", 422) from exc
                encoding = {
                    "label": "utf-8",
                    "bom": data.startswith(b"\xef\xbb\xbf"),
                    "replacement_count": 0,
                }
            evidence = {
                "schema_version": "mkb.acquisition-evidence.v1",
                "source_kind": source_kind,
                "acquisition_capability": capability,
                "acquisition_mode": mode,
                "declared_media_type": declared,
                "detected_media_type": detected,
                "verified_media_type": verified,
                "raw_byte_digest": _digest_bytes(data),
                "raw_byte_size": len(data),
                "encoding": encoding,
                "budget_verdict": "within_configured_acquisition_budget",
                **dict(extra_evidence or {}),
            }
            return _AcquiredContent(raw_text=raw_text, is_binary=binary, media_type=verified, evidence=evidence)


    async def _decode(
            self, command: ProcessCommand, state: dict[str, Any]
        ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
            raw = state.get("raw_text")
            if not isinstance(raw, str):
                raise MkbError("PIPELINE_INPUT_INVALID", "Acquisition evidence has no textual payload", 422)
            media_type = state.get("media_type")
            if not isinstance(media_type, str) or not media_type:
                raise MkbError("ACQUISITION_EVIDENCE_INVALID", "Verified media type is unavailable", 422)
            expected_decode = "intake.decode.pdf" if media_type == "application/pdf" else "intake.decode.text_json_html"
            if command.process_key != expected_decode:
                raise MkbError("DECODE_CAPABILITY_MISMATCH", "Source representation does not match the bound decoder", 409)
            binary = bool(state.get("raw_binary_transport"))
            decode_evidence: dict[str, Any]
            if binary:
                raw_bytes = raw.encode("latin-1")
                if media_type == "application/pdf":
                    decoded, decode_evidence = _extract_pdf_text(raw_bytes)
                    decode_evidence = {
                        **decode_evidence,
                        "decode_capability": "intake.decode.pdf",
                        "input_raw_byte_digest": state.get("raw_byte_digest"),
                    }
                elif media_type.startswith("image/"):
                    # There is intentionally no text manufactured from image
                    # bytes.  The OCR/Vision profile needs only this bounded
                    # image-evidence coordinate before its exact clean Process
                    # runs and reports its configured/unavailable disposition.
                    decoded = ""
                    decode_evidence = {
                        "decode_capability": "intake.decode.text_json_html",
                        "canonicalizer": "binary-image-evidence.v1",
                        "input_raw_byte_digest": state.get("raw_byte_digest"),
                        "representation_kind": "image_evidence",
                        "verified_media_type": media_type,
                    }
                else:
                    raise MkbError("ACQUISITION_DECODE_UNSUPPORTED", "Binary representation has no registered decoder", 422)
            elif media_type == "application/json":
                decoded = _canonical_json_text(raw)
                decode_evidence = {
                    "decode_capability": "intake.decode.text_json_html",
                    "canonicalizer": "jcs.i-json.v1",
                    "input_raw_byte_digest": state.get("raw_byte_digest"),
                }
            elif media_type in {"text/plain", "text/html"} or media_type.startswith("text/"):
                decoded = _canonical_text(raw)
                decode_evidence = {
                    "decode_capability": "intake.decode.text_json_html",
                    "canonicalizer": "utf8-lf-nfc.v1",
                    "input_raw_byte_digest": state.get("raw_byte_digest"),
                }
            else:
                raise MkbError("ACQUISITION_DECODE_UNSUPPORTED", "Verified media type has no registered decoder", 422)
            next_state = dict(state)
            next_state["decoded_text"] = decoded
            next_state["decoded_digest"] = stable_digest(
                {
                    "canonicalizer": decode_evidence["decode_capability"],
                    "media_type": media_type,
                    "text": decoded,
                }
            )
            next_state["decode_evidence"] = decode_evidence
            material = self._material(
                command,
                next_state,
                {
                    "decoded_representation": {
                        "content_digest": next_state["decoded_digest"],
                        "media_type": media_type,
                        "evidence": decode_evidence,
                    }
                },
            )

            async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
                del tx, refs

            return material, {}, callback
