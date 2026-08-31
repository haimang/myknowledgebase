"""Primary ingest acquisition and decode (inline/HTTP/local/API)."""

from __future__ import annotations

import inspect
from collections.abc import Awaitable, Callable, Mapping
from typing import Any

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.intake.representation import RepresentationObservation
from src.contracts.intake.semantics import generic_semantic_authority
from src.contracts.runtime.models import ProcessCommand
from src.contracts.storage.handles import digest_from_handle
from src.contracts.storage.models import ObjectHandle
from src.persistence.ports import UnitOfWork
from src.runtime.http_acquisition import HttpAcquisitionResult, redacted_url_identity
from src.runtime.intake.representation_history import (
    append_representation_tx,
    observe_main_text,
    prepare_representation_append,
)
from src.runtime.intake.types import (
    BrowserPrintResult,
    BrowserRenderResult,
    _AcquiredContent,
    _canonical_json_text,
    _canonical_text,
    _digest_bytes,
    _normalized_media_type,
    _sniff_media_type,
    _StageMaterial,
    _verified_media_type,
)
from src.services.observation_reservations import ObservationReservationService


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
        async with self._persistence.read_snapshot() as identity_tx:
            admitted_observation = await ObservationReservationService.identity_for_execution_tx(
                identity_tx,
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
            )
        if admitted_observation is not None and self._is_full_retry(admitted_observation):
            return await self._acquire_frozen_observation(command, state, admitted_observation, descriptor)
        if source_kind == "registered_api":
            return await self._acquire_registered_api_collection(
                command,
                descriptor,
                payload=payload,
                admitted_observation=admitted_observation,
            )
        expected_capability = (
            "intake.acquire.http_browser"
            if command.step_key in {"acquire_browser", "acquire_browser_reacquire", "acquire_print"}
            else self._expected_acquisition_capability(descriptor)
        )
        if command.process_key != expected_capability:
            raise MkbError(
                "ACQUISITION_CAPABILITY_MISMATCH", "Source kind does not match the bound acquisition capability", 409
            )
        try:
            acquired = await self._acquire_content(command, descriptor)
        except Exception as exc:
            await ObservationReservationService().mark_failed_for_execution(
                self._persistence,
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                error_code=exc.code if isinstance(exc, MkbError) else "ACQUISITION_FAILED",
            )
            raise
        if not acquired.is_binary and not acquired.raw_text.strip():
            raise MkbError("ACQUISITION_EMPTY", "Source acquisition returned no content", 422)
        now = utc_now()
        generic_semantics = (
            generic_semantic_authority(descriptor)
            if source_kind in {"inline_payload", "local_object", "http_resource"}
            else None
        )
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
            "source_stored_object_uuid": acquired.evidence.get("source_stored_object_uuid"),
            "filter_meta": (generic_semantics[0].model_dump(mode="json") if generic_semantics is not None else None),
            "context_meta": (generic_semantics[1].model_dump(mode="json") if generic_semantics is not None else None),
            "semantic_tuples": (
                [item.model_dump(mode="json") for item in generic_semantics[2]]
                if generic_semantics is not None
                else None
            ),
        }
        if admitted_observation is not None:
            next_state.update(
                {
                    "intake_source_uuid": admitted_observation["intake_source_uuid"],
                    "observation_uuid": admitted_observation["observation_uuid"],
                    "observation_key": admitted_observation["observation_key"],
                    "observation_fingerprint": admitted_observation["observation_fingerprint"],
                    "observation_attempt_generation": admitted_observation["current_attempt_generation"],
                    "expected_item_epoch": admitted_observation["expected_item_epoch"],
                }
            )
            if admitted_observation.get("intake_item_uuid"):
                next_state["intake_item_uuid"] = admitted_observation["intake_item_uuid"]
        else:
            existing = await self._resolve_existing_intake_identity(
                command.team_uuid, source_kind, next_state["normalized_external_key"]
            )
            if existing is not None:
                next_state["intake_source_uuid"] = existing["intake_source_uuid"]
                if existing.get("intake_item_uuid"):
                    next_state["intake_item_uuid"] = existing["intake_item_uuid"]
                if existing.get("intake_snapshot_uuid"):
                    next_state["intake_snapshot_uuid"] = existing["intake_snapshot_uuid"]
        representation_kind = str(acquired.evidence.get("representation_kind") or "transferred")
        acquire_fact = prepare_representation_append(
            RepresentationObservation(
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                step_key=command.step_key or command.process_key,
                fact_kind="print" if representation_kind == "print_pdf" else "acquire",
                capability=str(acquired.evidence["acquisition_capability"]),
                representation_kind=representation_kind,
                declared_media_type=acquired.evidence.get("declared_media_type"),
                detected_media_type=acquired.evidence.get("detected_media_type"),
                verified_media_type=acquired.media_type,
                raw_byte_digest=str(acquired.evidence["raw_byte_digest"]),
                raw_byte_size=int(acquired.evidence["raw_byte_size"]),
                text_layer="unknown" if acquired.media_type == "application/pdf" else "not_applicable",
                main_text_presence="unknown",
                canonicalizer_key="raw-byte-identity",
                canonicalizer_version="v1",
                observer_key="media-signature-sniffer",
                observer_version="v1",
                profile_identity=(
                    acquired.evidence.get("browser_profile") or acquired.evidence.get("transport_profile")
                ),
            )
        )
        next_state["representation_fact"] = acquire_fact.reference
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
            definition = await tx.fetchone(
                "SELECT definition_digest FROM mkb_source_kind_definitions "
                "WHERE source_kind=? AND definition_version='v1' AND status='active'",
                (source_kind,),
            )
            if definition is None:
                raise MkbError("REGISTRY_NOT_FOUND", "Source kind definition is unavailable", 503)
            if admitted_observation is None:
                existing = await self._resolve_existing_intake_identity_tx(
                    tx, command.team_uuid, source_kind, str(next_state["normalized_external_key"])
                )
                if existing is not None:
                    next_state["intake_source_uuid"] = existing["intake_source_uuid"]
                    if existing.get("intake_item_uuid"):
                        next_state["intake_item_uuid"] = existing["intake_item_uuid"]
                    if existing.get("intake_snapshot_uuid"):
                        next_state["intake_snapshot_uuid"] = existing["intake_snapshot_uuid"]
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_intake_sources "
                "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
                "source_descriptor_ref,source_descriptor_digest,accepts_new_snapshots,created_at,updated_at,payload_extra,"
                "normalized_external_key) "
                "VALUES (?,?,?,'v1',?,?,?,1,?,?, '{}',?)",
                (
                    command.team_uuid,
                    next_state["intake_source_uuid"],
                    source_kind,
                    definition["definition_digest"],
                    command.input_manifest_ref,
                    stable_digest(descriptor),
                    now,
                    now,
                    next_state["normalized_external_key"],
                ),
            )
            stored = await tx.fetchone(
                "SELECT intake_source_uuid FROM mkb_intake_sources "
                "WHERE team_uuid=? AND source_kind=? AND normalized_external_key=?",
                (command.team_uuid, source_kind, next_state["normalized_external_key"]),
            )
            if stored is not None:
                next_state["intake_source_uuid"] = stored["intake_source_uuid"]
            await append_representation_tx(tx, acquire_fact)
            await ObservationReservationService().mark_acquired_tx(
                tx,
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                artifact_ref=refs.get("output_manifest_ref"),
                artifact_digest=refs.get("output_manifest_digest"),
            )

        return material, {}, callback

    async def _resolve_existing_intake_identity(
        self, team_uuid: str, source_kind: str, normalized_external_key: str
    ) -> dict[str, Any] | None:
        async with self._persistence.transaction() as tx:
            return await self._resolve_existing_intake_identity_tx(tx, team_uuid, source_kind, normalized_external_key)

    async def _resolve_existing_intake_identity_tx(
        self, tx: UnitOfWork, team_uuid: str, source_kind: str, normalized_external_key: str
    ) -> dict[str, Any] | None:
        row = await tx.fetchone(
            "SELECT s.intake_source_uuid, i.intake_item_uuid "
            "FROM mkb_intake_items AS i "
            "JOIN mkb_intake_sources AS s "
            "ON s.team_uuid=i.team_uuid AND s.intake_source_uuid=i.intake_source_uuid "
            "WHERE i.team_uuid=? AND s.source_kind=? AND i.normalized_external_key=? "
            "AND i.deleted_at IS NULL ORDER BY i.created_at ASC LIMIT 1",
            (team_uuid, source_kind, normalized_external_key),
        )
        if row is None:
            source = await tx.fetchone(
                "SELECT intake_source_uuid FROM mkb_intake_sources "
                "WHERE team_uuid=? AND source_kind=? AND normalized_external_key=?",
                (team_uuid, source_kind, normalized_external_key),
            )
            if source is None:
                return None
            row = {"intake_source_uuid": source["intake_source_uuid"], "intake_item_uuid": None}
        snapshot = await tx.fetchone(
            "SELECT intake_snapshot_uuid FROM mkb_intake_snapshots "
            "WHERE team_uuid=? AND intake_source_uuid=? AND observation_key=?",
            (team_uuid, row["intake_source_uuid"], normalized_external_key),
        )
        result = dict(row)
        if snapshot is not None:
            result["intake_snapshot_uuid"] = snapshot["intake_snapshot_uuid"]
        return result

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
        raise MkbError(
            "ACQUISITION_CAPABILITY_MISMATCH", "Source profile has no registered acquisition capability", 409
        )

    async def _acquire_registered_api_collection(
        self,
        command: ProcessCommand,
        descriptor: Mapping[str, Any],
        *,
        payload: Mapping[str, Any],
        admitted_observation: Mapping[str, Any] | None = None,
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        """Acquire an ordered typed API collection without flattening members.

        Each input record already passed its provider-specific strict public
        contract.  Acquisition freezes raw records only; the sole provider
        parser remains behind ``intake.dispatch_clean``.
        """

        if command.process_key != "intake.acquire.registered_api":
            raise MkbError(
                "ACQUISITION_CAPABILITY_MISMATCH", "Registered API requires its scatter acquisition capability", 409
            )
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
        collection_bytes = canonical_json(records)
        raw_digest = _digest_bytes(collection_bytes)
        collection_byte_count = len(collection_bytes)
        observation_digest = stable_digest(
            {
                "source_external_key": root_external_key.casefold(),
                "records_digest": raw_digest,
            }
        )
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
            "representation_kind": "transferred",
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
            "observation_digest": observation_digest,
            "raw_byte_digest": raw_digest,
            "raw_byte_size": collection_byte_count,
            "declared_media_type": "application/json",
            "detected_media_type": "application/json",
            "media_type": "application/json",
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
        if admitted_observation is not None:
            next_state.update(
                {
                    "intake_source_uuid": admitted_observation["intake_source_uuid"],
                    "observation_uuid": admitted_observation["observation_uuid"],
                    "observation_key": admitted_observation["observation_key"],
                    "observation_fingerprint": admitted_observation["observation_fingerprint"],
                    "observation_attempt_generation": admitted_observation["current_attempt_generation"],
                    "expected_item_epoch": admitted_observation["expected_item_epoch"],
                }
            )
        acquire_fact = prepare_representation_append(
            RepresentationObservation(
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                step_key=command.step_key or command.process_key,
                fact_kind="acquire",
                capability="intake.acquire.registered_api",
                representation_kind="transferred",
                declared_media_type="application/json",
                detected_media_type="application/json",
                verified_media_type="application/json",
                raw_byte_digest=raw_digest,
                raw_byte_size=collection_byte_count,
                text_layer="not_applicable",
                main_text_presence="unknown",
                canonicalizer_key="registered-api-record-set",
                canonicalizer_version="v1",
                observer_key="registered-api-contract",
                observer_version=str(definition_version),
                profile_identity=f"{provider}:{operation}:{definition_version}",
            )
        )
        next_state["representation_fact"] = acquire_fact.reference
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
            definition = await tx.fetchone(
                "SELECT definition_digest FROM mkb_source_kind_definitions "
                "WHERE source_kind='registered_api' AND definition_version='v1' AND status='active'"
            )
            if definition is None:
                raise MkbError("REGISTRY_NOT_FOUND", "Source kind definition is unavailable", 503)
            if admitted_observation is None:
                existing = await self._resolve_existing_intake_identity_tx(
                    tx, command.team_uuid, "registered_api", str(next_state["normalized_external_key"])
                )
                if existing is not None:
                    next_state["intake_source_uuid"] = existing["intake_source_uuid"]
                    if existing.get("intake_item_uuid"):
                        next_state["intake_item_uuid"] = existing["intake_item_uuid"]
                    if existing.get("intake_snapshot_uuid"):
                        next_state["intake_snapshot_uuid"] = existing["intake_snapshot_uuid"]
            await tx.execute(
                "INSERT OR IGNORE INTO mkb_intake_sources "
                "(team_uuid,intake_source_uuid,source_kind,source_kind_definition_version,source_kind_definition_digest,"
                "source_descriptor_ref,source_descriptor_digest,accepts_new_snapshots,created_at,updated_at,payload_extra,"
                "normalized_external_key) "
                "VALUES (?,?,?,'v1',?,?,?,1,?,?, '{}',?)",
                (
                    command.team_uuid,
                    next_state["intake_source_uuid"],
                    "registered_api",
                    definition["definition_digest"],
                    command.input_manifest_ref,
                    stable_digest(descriptor),
                    now,
                    now,
                    next_state["normalized_external_key"],
                ),
            )
            stored = await tx.fetchone(
                "SELECT intake_source_uuid FROM mkb_intake_sources "
                "WHERE team_uuid=? AND source_kind='registered_api' AND normalized_external_key=?",
                (command.team_uuid, next_state["normalized_external_key"]),
            )
            if stored is not None:
                next_state["intake_source_uuid"] = stored["intake_source_uuid"]
            await append_representation_tx(tx, acquire_fact)
            await ObservationReservationService().mark_acquired_tx(
                tx,
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                artifact_ref=refs.get("output_manifest_ref"),
                artifact_digest=refs.get("output_manifest_digest"),
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
            object_handle = ObjectHandle(value=handle)
            stored = await self._live_local_object(command.team_uuid, object_handle)
            data = await self._storage.read_verified(command.team_uuid, object_handle)
            if len(data) != int(stored["size_bytes"]):
                raise MkbError("OBJECT_INTEGRITY_DIGEST", "Catalogued object size failed verification", 503)
            return self._representation_from_bytes(
                data,
                declared_media_type=_normalized_media_type(descriptor.get("media_type")),
                capability="intake.acquire.local_object",
                source_kind="local_object",
                mode="logical_object",
                extra_evidence={
                    "logical_handle_digest": stable_digest({"handle": handle}),
                    "source_stored_object_uuid": stored["stored_object_uuid"],
                },
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
        requested_mode = descriptor.get("acquisition_mode", "static")
        mode = (
            "print_pdf"
            if command.step_key == "acquire_print"
            else "browser"
            if command.step_key in {"acquire_browser", "acquire_browser_reacquire"}
            else requested_mode
        )
        if requested_mode not in {"static", "browser", "pdf"}:
            raise MkbError("ACQUISITION_MODE_INVALID", "HTTP acquisition mode is not registered", 422)
        if mode in {"browser", "print_pdf"}:
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
        if mode == "print_pdf" and callable(getattr(fetcher, "print_pdf", None)):
            result = fetcher.print_pdf(url)
        elif mode == "browser" and callable(getattr(fetcher, "render", None)):
            result = fetcher.render(url)
        else:
            acquire = getattr(fetcher, "acquire", None)
            result = acquire(url) if callable(acquire) else fetcher(url)
        if inspect.isawaitable(result):
            result = await result
        http_evidence: dict[str, Any]
        if isinstance(result, BrowserPrintResult):
            if mode != "print_pdf":
                raise MkbError(
                    "ACQUISITION_RESPONSE_INVALID",
                    "A print result cannot satisfy a browser-render acquisition",
                    502,
                )
            if not result.profile_identity.strip():
                raise MkbError("ACQUISITION_PRINT_PROFILE_INVALID", "Browser print profile is unavailable", 502)
            data = result.body
            declared = "application/pdf"
            http_evidence = {
                **result.source_evidence,
                "request_url_identity": result.source_evidence.get("request_url_identity", redacted_url_identity(url)),
                "final_url_identity": result.source_evidence.get("final_url_identity", redacted_url_identity(url)),
                "response_media_type": "application/pdf",
                "http_status": result.source_evidence.get("http_status"),
                "redirect_count": result.source_evidence.get("redirect_count"),
                "transport_profile": result.profile_identity,
                "browser_profile": result.profile_identity,
                "browser_runtime_uid": result.runtime_uid,
                "browser_timeout_seconds": result.timeout_seconds,
                "browser_output_limit_bytes": result.output_limit_bytes,
            }
        elif isinstance(result, BrowserRenderResult):
            if mode != "browser":
                raise MkbError(
                    "ACQUISITION_RESPONSE_INVALID",
                    "A render result cannot satisfy a browser-print acquisition",
                    502,
                )
            if not result.profile_identity.strip() or not result.body.strip():
                raise MkbError("ACQUISITION_BROWSER_PROFILE_INVALID", "Browser render evidence is unavailable", 502)
            data = result.body.encode("utf-8")
            declared = "text/html"
            http_evidence = {
                **result.source_evidence,
                "request_url_identity": result.source_evidence.get("request_url_identity", redacted_url_identity(url)),
                "final_url_identity": result.source_evidence.get("final_url_identity", redacted_url_identity(url)),
                "response_media_type": "text/html",
                "http_status": result.source_evidence.get("http_status"),
                "redirect_count": result.source_evidence.get("redirect_count"),
                "transport_profile": result.profile_identity,
                "browser_profile": result.profile_identity,
                "browser_runtime_uid": result.runtime_uid,
                "browser_timeout_seconds": result.timeout_seconds,
                "browser_output_limit_bytes": result.output_limit_bytes,
            }
        elif mode == "print_pdf":
            raise MkbError(
                "ACQUISITION_PRINT_RESULT_INVALID",
                "Browser print capability must return typed PDF bytes and profile identity",
                502,
            )
        elif isinstance(result, HttpAcquisitionResult):
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
                "representation_kind": (
                    "print_pdf" if mode == "print_pdf" else "rendered" if mode == "browser" else "transferred"
                ),
                "browser_profile": (
                    http_evidence.get("browser_profile")
                    if mode == "print_pdf"
                    else http_evidence.get("transport_profile")
                    if mode == "browser"
                    else None
                ),
            },
        )

    @staticmethod
    def _is_full_retry(identity: Mapping[str, Any]) -> bool:
        raw = identity.get("execution_payload_extra")
        if isinstance(raw, str):
            try:
                import json

                raw = json.loads(raw)
            except (TypeError, ValueError, json.JSONDecodeError):
                return False
        return isinstance(raw, dict) and raw.get("full_retry") is True

    async def _acquire_frozen_observation(
        self,
        command: ProcessCommand,
        state: Mapping[str, Any],
        identity: Mapping[str, Any],
        descriptor: Mapping[str, Any],
    ) -> tuple[_StageMaterial, dict[str, Any], Callable[[UnitOfWork, Mapping[str, str]], Awaitable[None]]]:
        """Resume a full retry from the accepted raw artifact, never the source."""

        snapshot_uuid = identity.get("intake_snapshot_uuid")
        if not isinstance(snapshot_uuid, str) or not snapshot_uuid:
            async with self._persistence.read_snapshot() as tx:
                observation = await tx.fetchone(
                    "SELECT accepted_snapshot_uuid FROM mkb_intake_observations "
                    "WHERE team_uuid=? AND observation_uuid=? AND state='accepted'",
                    (command.team_uuid, identity["observation_uuid"]),
                )
            snapshot_uuid = None if observation is None else observation.get("accepted_snapshot_uuid")
        if not isinstance(snapshot_uuid, str) or not snapshot_uuid:
            raise MkbError(
                "FULL_REPLAY_INPUT_UNAVAILABLE",
                "Full retry requires a durably accepted Observation artifact",
                409,
            )
        async with self._persistence.read_snapshot() as tx:
            artifact = await tx.fetchone(
                "SELECT intake_artifact_uuid,logical_handle,content_digest,size_bytes,media_type "
                "FROM mkb_intake_artifacts WHERE team_uuid=? AND owner_snapshot_uuid=? "
                "AND artifact_role='raw_acquisition' ORDER BY created_at ASC LIMIT 1",
                (command.team_uuid, snapshot_uuid),
            )
            item = await tx.fetchone(
                "SELECT intake_item_uuid,latest_revision_uuid,row_revision,lifecycle_state "
                "FROM mkb_intake_items WHERE team_uuid=? AND intake_source_uuid=? "
                "AND normalized_external_key=?",
                (command.team_uuid, identity["intake_source_uuid"], str(descriptor.get("external_key", "")).casefold()),
            )
        if artifact is None:
            raise MkbError("FULL_REPLAY_INPUT_UNAVAILABLE", "Frozen raw artifact is unavailable", 409)
        data = await self._storage.read_verified(command.team_uuid, ObjectHandle(value=artifact["logical_handle"]))
        if len(data) != int(artifact["size_bytes"]) or _digest_bytes(data) != artifact["content_digest"]:
            raise MkbError("FULL_REPLAY_INPUT_UNAVAILABLE", "Frozen raw artifact failed its digest fence", 409)
        acquired = self._representation_from_bytes(
            data,
            declared_media_type=artifact.get("media_type"),
            capability={
                "inline_payload": "intake.acquire.inline",
                "local_object": "intake.acquire.local_object",
                "http_resource": "intake.acquire.http_static",
                "registered_api": "intake.acquire.registered_api",
            }.get(str(descriptor.get("source_kind")), "intake.acquire.inline"),
            source_kind=str(descriptor.get("source_kind") or "inline_payload"),
            mode="frozen_replay",
            extra_evidence={
                "source_artifact_uuid": artifact["intake_artifact_uuid"],
                "request_url_identity": redacted_url_identity(str(descriptor.get("url") or "frozen")),
                "final_url_identity": redacted_url_identity(str(descriptor.get("url") or "frozen")),
                "transport_profile": "frozen-observation.v1",
            },
        )
        raw_digest = stable_digest({"media_type": acquired.media_type, "text": acquired.raw_text})
        next_state = {
            "request_intent": "intake.ingest",
            "full_retry": True,
            "team_uuid": command.team_uuid,
            "task_uuid": command.task_uuid,
            "trace_uuid": command.trace_uuid,
            "source": dict(descriptor),
            "source_kind": descriptor.get("source_kind"),
            "external_key": descriptor.get("external_key"),
            "normalized_external_key": str(descriptor.get("external_key", "")).casefold(),
            "observation_uuid": identity["observation_uuid"],
            "observation_key": identity["observation_key"],
            "observation_fingerprint": identity["observation_fingerprint"],
            "observation_attempt_generation": identity["current_attempt_generation"],
            "expected_item_epoch": identity.get("expected_item_epoch"),
            "intake_source_uuid": identity["intake_source_uuid"],
            "intake_snapshot_uuid": snapshot_uuid,
            "intake_item_uuid": None if item is None else item.get("intake_item_uuid"),
            "intake_revision_uuid": None if item is None else item.get("latest_revision_uuid"),
            "raw_artifact_uuid": artifact["intake_artifact_uuid"],
            "candidate_set_uuid": uuid7(),
            "clean_artifact_uuid": uuid7(),
            "raw_text": acquired.raw_text,
            "raw_binary_transport": acquired.is_binary,
            "raw_digest": raw_digest,
            "raw_byte_digest": acquired.evidence["raw_byte_digest"],
            "raw_byte_size": acquired.evidence["raw_byte_size"],
            "declared_media_type": acquired.evidence["declared_media_type"],
            "detected_media_type": acquired.evidence["detected_media_type"],
            "media_type": acquired.media_type,
            "acquisition_capability": acquired.evidence["acquisition_capability"],
            "acquisition_evidence": acquired.evidence,
            "observed_at": utc_now(),
            "payload": state.get("payload") or {},
        }
        acquire_fact = prepare_representation_append(
            RepresentationObservation(
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                step_key=command.step_key or command.process_key,
                fact_kind="acquire",
                capability={
                    "inline_payload": "intake.acquire.inline",
                    "local_object": "intake.acquire.local_object",
                    "http_resource": "intake.acquire.http_static",
                    "registered_api": "intake.acquire.registered_api",
                }.get(str(descriptor.get("source_kind")), "intake.acquire.inline"),
                representation_kind="frozen_replay",
                declared_media_type=acquired.evidence.get("declared_media_type"),
                detected_media_type=acquired.evidence.get("detected_media_type"),
                verified_media_type=acquired.media_type,
                raw_byte_digest=acquired.evidence["raw_byte_digest"],
                raw_byte_size=acquired.evidence["raw_byte_size"],
                text_layer="unknown",
                main_text_presence="unknown",
                canonicalizer_key="frozen-observation-artifact",
                canonicalizer_version="v1",
                observer_key="full-replay",
                observer_version="v1",
                profile_identity="frozen-observation.v1",
            )
        )
        next_state["representation_fact"] = acquire_fact.reference
        material = self._material(
            command,
            next_state,
            {"acquisition_evidence": {"mode": "frozen_observation_replay", "artifact_uuid": artifact["intake_artifact_uuid"]}},
        )

        async def callback(tx: UnitOfWork, refs: Mapping[str, str]) -> None:
            del refs
            await append_representation_tx(tx, acquire_fact)

        return material, {}, callback

    async def _live_local_object(self, team_uuid: str, handle: ObjectHandle) -> dict[str, Any]:
        digest = digest_from_handle(team_uuid, handle)
        async with self._persistence.transaction() as tx:
            row = await tx.fetchone(
                "SELECT stored_object_uuid,size_bytes FROM mkb_stored_objects "
                "WHERE team_uuid=? AND content_digest=? AND tombstoned_at IS NULL "
                "ORDER BY created_at DESC LIMIT 1",
                (team_uuid, digest),
            )
            if row is None:
                raise MkbError(
                    "OBJECT_CATALOG_REQUIRED",
                    "Local object is not present in the live Team catalog",
                    409,
                )
            reference = await tx.fetchone(
                "SELECT reference_uuid FROM mkb_object_references WHERE team_uuid=? AND stored_object_uuid=? "
                "AND released_at IS NULL LIMIT 1",
                (team_uuid, row["stored_object_uuid"]),
            )
            if reference is None:
                raise MkbError(
                    "OBJECT_REFERENCE_REQUIRED",
                    "Local object has no live upload or business reference",
                    409,
                )
        return row

    def _representation_from_bytes(
        self,
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
        binary = not (verified.startswith("text/") or verified == "application/json")
        if binary:
            raw_text = data.decode("latin-1")
            encoding = {"label": "binary", "bom": False, "replacement_count": 0}
        else:
            try:
                raw_text = data.decode("utf-8-sig")
            except UnicodeDecodeError as exc:
                raise MkbError(
                    "ACQUISITION_DECODE_UNSUPPORTED", "Representation is not supported UTF-8 text", 422
                ) from exc
            encoding = {
                "label": "utf-8",
                "bom": data.startswith(b"\xef\xbb\xbf"),
                "replacement_count": 0,
            }
        limit = int(
            getattr(self, "_print_max_response_bytes", 16 * 1024 * 1024)
            if mode == "print_pdf"
            else getattr(self, "_acquisition_max_response_bytes", 8 * 1024 * 1024)
        )
        observed = len(data)
        if observed > limit:
            raise MkbError(
                "ACQUISITION_BUDGET_EXCEEDED",
                "Acquisition exceeded the configured response budget",
                413,
                {"limit": limit, "observed": observed},
            )
        evidence = {
            "schema_version": "mkb.acquisition-evidence.v1",
            "source_kind": source_kind,
            "acquisition_capability": capability,
            "acquisition_mode": mode,
            "declared_media_type": declared,
            "detected_media_type": detected,
            "verified_media_type": verified,
            "raw_byte_digest": _digest_bytes(data),
            "raw_byte_size": observed,
            "encoding": encoding,
            "budget_verdict": "within_configured_acquisition_budget",
            "budget": {"limit": limit, "observed": observed},
            "budget_profile": "browser-print-pdf.v1" if mode == "print_pdf" else "acquisition.v1",
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
                parser = self._pdf_parser
                if parser is None or not callable(getattr(parser, "parse", None)):
                    raise MkbError(
                        "PDF_PARSE_CAPABILITY_UNAVAILABLE",
                        "Isolated PDF parser is not configured for this deployment",
                        503,
                    )
                parsed = await parser.parse(raw_bytes)
                decoded = parsed.text
                decode_evidence = parsed.evidence()
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
        text_layer = str(decode_evidence.get("text_layer") or "not_applicable")
        decode_fact = prepare_representation_append(
            RepresentationObservation(
                team_uuid=command.team_uuid,
                execution_uuid=command.execution_uuid,
                process_uuid=command.process_uuid,
                step_key=command.step_key or command.process_key,
                fact_kind="decode",
                capability=str(decode_evidence["decode_capability"]),
                representation_kind=str(
                    decode_evidence.get("representation_kind")
                    or (state.get("acquisition_evidence") or {}).get("representation_kind")
                    or "transferred"
                ),
                declared_media_type=(
                    state.get("declared_media_type") if isinstance(state.get("declared_media_type"), str) else None
                ),
                detected_media_type=(
                    state.get("detected_media_type") if isinstance(state.get("detected_media_type"), str) else None
                ),
                verified_media_type=media_type,
                raw_byte_digest=str(state.get("raw_byte_digest")),
                raw_byte_size=int(state.get("raw_byte_size") or 0),
                text_layer=text_layer,  # type: ignore[arg-type]
                main_text_presence=observe_main_text(decoded, media_type=media_type, text_layer=text_layer),  # type: ignore[arg-type]
                canonicalizer_key=str(decode_evidence.get("canonicalizer") or decode_evidence["decode_capability"]),
                canonicalizer_version="v1",
                observer_key=str(decode_evidence.get("decoder") or "deterministic-text-decoder"),
                observer_version="v1",
                profile_identity=None,
            )
        )
        next_state["representation_fact"] = decode_fact.reference
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
            del refs
            await append_representation_tx(tx, decode_fact)

        return material, {}, callback
