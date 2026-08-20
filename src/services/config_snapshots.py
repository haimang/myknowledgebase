"""S14 L4 configuration materialization for new Executions only.

The materialized JSON is promoted to the object store before the Task UoW and
catalogued inside that UoW.  Therefore a failed Task transaction leaves, at
worst, an unreferenced CAS object that S13 GC can collect; it never leaves a
partially visible Execution or mutable configuration alias.
"""

from __future__ import annotations

import hashlib
import json
import tomllib
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from src.contracts.api.models import (
    IndexRebuildPayload,
    InlineSourceDescriptor,
    IntakeIngestPayload,
    IntakeLifecyclePayload,
    IntakeRebuildPayload,
    IntakeUpdateMetadataPayload,
    TaskCreateRequest,
)
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import canonical_json, sha256_bytes, stable_digest, uuid7
from src.contracts.storage.models import ObjectStat, PromoteRequest
from src.persistence.ports import PersistencePort, UnitOfWork
from src.runtime.config import Settings
from src.services.events import SecurityAuditWriter
from src.services.intake_lifecycle import IntakeTargetResolver
from src.services.prompt_profiles import (
    DEFAULT_COMPRESSION_CHANNEL,
    GRANULARITY_LEVELS,
    default_prompt_ids,
)
from src.services.registry import select_latest_catalog_row
from src.services.workflow_registry import WorkflowIdentity, WorkflowRegistryService
from src.storage.ports import ObjectStorePort

# Caps re-checked at materialize time (S14-A10).  The DTO bounds are the first
# fence; these are the product caps frozen into L4 digests.
_OVERRIDE_CAPS: dict[str, int] = {
    "batch_size": 64,
    "top_k": 50,
    "return_k": 50,
    "recall_k": 100,
    "pack_budget": 32_000,
}
_REGISTERED_PROFILES = frozenset({"clean.web.v1", "clean.document.v1", "clean.default.v1"})
_DEFAULT_PROMPT_IDS = {
    "clean": "promptA.clean",
    "summarizer": "promptC.summarizer",
}
# Keys that must never be accepted even if a future DTO loosens extra=forbid.
_FORBIDDEN_OVERRIDE_KEYS = frozenset(
    {
        "model_key",
        "model_version",
        "prompt_key",
        "prompt_version",
        "schema_key",
        "schema_version",
        "adapter_kind",
        "dimension",
        "workflow_key",
        "workflow_revision_uuid",
        "secret",
        "api_key",
        "token",
        "absolute_path",
        "path",
        "flag",
        "feature_flag",
        "feature_flags",
    }
)


@dataclass(frozen=True, slots=True)
class PreparedExecutionInputs:
    """Immutable bytes and resolved coordinates awaiting the Task UoW."""

    workflow: WorkflowIdentity
    config_snapshot: ObjectStat
    config_snapshot_digest: str
    input_manifest: ObjectStat
    input_manifest_digest: str
    domain_binding_digest: str
    # Inline request text is deliberately promoted before any Task-facing
    # durable document exists.  The manifest/audit carry this opaque stat, not
    # the caller's body, and the reference is created in the Task UoW.
    inline_ingress: ObjectStat | None
    audit_envelope: dict[str, Any]
    intent_context: dict[str, Any] | None = None
    # Body-free S14 override audit payload for the Task create UoW event.
    override_applied: dict[str, Any] | None = None

    @property
    def config_snapshot_ref(self) -> str:
        return self.config_snapshot.handle.value

    @property
    def input_manifest_ref(self) -> str:
        return self.input_manifest.handle.value


class ConfigSnapshotService:
    """Resolve L0/L1/L2/L3 into one deterministic, object-backed L4 snapshot."""

    REQUIRED_CAPABILITIES = ("embed", "structured_generate", "text_generate")

    def __init__(
        self,
        persistence: PersistencePort,
        storage: ObjectStorePort,
        workflows: WorkflowRegistryService,
        settings: Settings,
        targets: IntakeTargetResolver | None = None,
        security_audit: SecurityAuditWriter | None = None,
    ) -> None:
        self.persistence = persistence
        self.storage = storage
        self.workflows = workflows
        self.settings = settings
        self.targets = targets or IntakeTargetResolver(persistence)
        self.security_audit = security_audit or SecurityAuditWriter()

    async def prepare(self, request: TaskCreateRequest) -> PreparedExecutionInputs:
        """Resolve only for a new execution; callers must avoid replay work first."""

        source_kind = request.payload.source.source_kind if isinstance(request.payload, IntakeIngestPayload) else None
        source_profile = self._source_profile(request)
        workflow = await self.workflows.resolve_for_source(
            self._workflow_purpose(request.request_intent),
            source_kind,
            source_profile,
        )
        # This is the S05 admission boundary.  Do it before materializing
        # configuration or input manifests so the caller-owned body never
        # reaches a Task audit, an Execution manifest, or an outbox payload.
        # A later DB rollback can leave only an unreferenced CAS object, which
        # S13 is explicitly allowed to collect.
        inline_ingress = await self._stage_inline_ingress(request)
        l0 = self._load_l0()
        l1 = await self._load_l1()
        prompt_selection = self._resolve_prompt_selection(l1["prompts"], request)
        bindings = self._resolve_bindings(l1["bindings"])
        # The local/offline profile is a first-class, frozen binding rather
        # than hash vectors labelled as a production model.  Once promoted,
        # this survives any later Settings/profile change for the Execution.
        if not self.settings.live_inference:
            bindings["embed"] = self._deterministic_embed_binding()
        else:
            embed = bindings["embed"]
            model = next(
                (
                    row
                    for row in l1["models"]
                    if row["model_key"] == embed["model_key"]
                    and row["model_version"] == embed["model_version"]
                    and row["modality"] in {"embed", "multimodal_embed"}
                ),
                None,
            )
            if model is None or not isinstance(model.get("default_dimension"), int) or model["default_dimension"] < 1:
                raise MkbError("CONFIG_CONFLICT", "Live embed binding has no valid registered dimension", 503)
            bindings["embed"] = {**embed, "dimension": model["default_dimension"]}
        flag_bundle, flag_bundle_digest = self._load_flag_bundle()
        compression_channel, channel_source = self._require_compression_channel(request)
        try:
            semantic_overrides, ops_overrides, override_digest, semantic_knobs = self._resolve_overrides(
                request.overrides
            )
        except MkbError as exc:
            if exc.code == "CONFIG_OVERRIDE_REJECTED":
                await self._audit_override_rejected(request, exc)
            raise
        l2: dict[str, Any] = {
            "inference_vllm_base_url": self.settings.inference_vllm_base_url,
            "inference_mode": "live" if self.settings.live_inference else "deterministic",
        }
        if isinstance(request.payload, IntakeIngestPayload):
            l2["compression_channel"] = compression_channel
            l2["channel_source"] = channel_source
        materials = {
            "schema_version": "mkb.config-snapshot.v1",
            "l0": l0,
            "l1": {
                "prompts": l1["prompts"],
                "selected_prompts": prompt_selection,
                "models": l1["models"],
                "bindings": bindings,
            },
            # L2 is deliberately topology-only. No token, secret, absolute
            # path, or prompt body can enter a frozen snapshot.
            "l2": l2,
            # L3 semantic overrides only.  Ops-only knobs (dry_run/debug_trace)
            # must not enter materials hashed into config_snapshot_digest /
            # domain_binding_digest (S14-A17); they are audit-only.
            "l3": {
                "overrides": semantic_overrides,
                "override_digest": override_digest,
            },
            "l4": await self._load_l4_schema_freeze(),
            "flag_bundle": flag_bundle,
            "flag_bundle_digest": flag_bundle_digest,
            "semantic_knobs": semantic_knobs,
            "workflow": {
                "workflow_key": workflow.workflow_key,
                "workflow_uuid": workflow.workflow_uuid,
                "workflow_revision_uuid": workflow.workflow_revision_uuid,
                "compiled_digest": workflow.compiled_digest,
                "registration_fingerprint": workflow.registration_fingerprint,
                "execution_role": workflow.execution_role,
            },
        }
        config_bytes = canonical_json(materials)
        config_snapshot = await self.storage.promote(
            config_bytes,
            PromoteRequest(team_uuid=request.team_uuid, purpose="process_io", media_type="application/json"),
        )
        if config_snapshot.sha256 != stable_digest(materials):
            raise MkbError("SNAPSHOT_INCONSISTENT", "Config snapshot digest is inconsistent", 503)

        intent_context = await self._resolve_intent_context(request)
        execution_payload = self._execution_payload(request, inline_ingress, prompt_selection)
        audit_envelope = self.redacted_request_envelope(request, inline_ingress)
        input_manifest_body = {
            "schema_version": "mkb.execution-input-manifest.v1",
            "team_uuid": request.team_uuid,
            "task_uuid": request.task_uuid,
            "trace_uuid": request.trace_uuid,
            "request_intent": request.request_intent,
            "payload": execution_payload,
        }
        if intent_context is not None:
            input_manifest_body["intent_context"] = intent_context
        input_bytes = canonical_json(input_manifest_body)
        input_manifest = await self.storage.promote(
            input_bytes,
            PromoteRequest(team_uuid=request.team_uuid, purpose="process_io", media_type="application/json"),
        )
        if input_manifest.sha256 != stable_digest(input_manifest_body):
            raise MkbError("SNAPSHOT_INCONSISTENT", "Input manifest digest is inconsistent", 503)
        # Semantic knobs + override_digest enter the binding identity; ops-only
        # security.*/obs.* knobs never do (S14-T019 / T030).
        domain_binding_digest = stable_digest(
            {
                "config_snapshot_digest": config_snapshot.sha256,
                "workflow_compiled_digest": workflow.compiled_digest,
                "request_intent": request.request_intent,
                "override_digest": override_digest,
                "semantic_knobs": semantic_knobs,
                "flag_bundle_digest": flag_bundle_digest,
            }
        )
        override_applied = None
        if semantic_overrides or ops_overrides:
            # Audit records both semantic and ops keys; only semantic keys
            # participated in override_digest / L4 materials above.
            override_applied = {
                "override_keys": sorted({*semantic_overrides, *ops_overrides}),
                "override_digest": override_digest,
                "ops_override_keys": sorted(ops_overrides),
                "actor_origin": "task.create",
                "team_uuid": request.team_uuid,
                "task_uuid": request.task_uuid,
                "result": "applied",
            }
        return PreparedExecutionInputs(
            workflow=workflow,
            config_snapshot=config_snapshot,
            config_snapshot_digest=config_snapshot.sha256,
            input_manifest=input_manifest,
            input_manifest_digest=input_manifest.sha256,
            domain_binding_digest=domain_binding_digest,
            inline_ingress=inline_ingress,
            audit_envelope=audit_envelope,
            intent_context=intent_context,
            override_applied=override_applied,
        )

    async def catalog_for_execution(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        execution_uuid: str,
        prepared: PreparedExecutionInputs,
    ) -> None:
        """Catalog the already-promoted L4 and input bytes in the Task UoW."""

        await self._catalog_object(
            tx,
            team_uuid=team_uuid,
            stat=prepared.config_snapshot,
            owner_kind="execution_config_snapshot",
            owner_uuid=execution_uuid,
        )
        if prepared.inline_ingress is not None:
            await self._catalog_object(
                tx,
                team_uuid=team_uuid,
                stat=prepared.inline_ingress,
                owner_kind="execution_inline_ingress",
                owner_uuid=execution_uuid,
            )
        await self._catalog_object(
            tx,
            team_uuid=team_uuid,
            stat=prepared.input_manifest,
            owner_kind="execution_input_manifest",
            owner_uuid=execution_uuid,
        )

    async def _catalog_object(
        self,
        tx: UnitOfWork,
        *,
        team_uuid: str,
        stat: ObjectStat,
        owner_kind: str,
        owner_uuid: str,
    ) -> str:
        row = await tx.fetchone(
            "SELECT stored_object_uuid FROM mkb_stored_objects WHERE team_uuid=? AND content_digest=? AND size_bytes=?",
            (team_uuid, stat.sha256, stat.size_bytes),
        )
        if row is None:
            stored_object_uuid = uuid7()
            await tx.execute(
                "INSERT INTO mkb_stored_objects "
                "(stored_object_uuid,team_uuid,digest_algorithm,content_digest,size_bytes,media_type,storage_backend,"
                "created_at,payload_extra) VALUES (?,?, 'sha256',?,?,?,?,?, '{}')",
                (
                    stored_object_uuid,
                    team_uuid,
                    stat.sha256,
                    stat.size_bytes,
                    stat.media_type,
                    "local_fs",
                    self._now(),
                ),
            )
        else:
            stored_object_uuid = row["stored_object_uuid"]
        await tx.execute(
            "INSERT INTO mkb_object_references "
            "(reference_uuid,team_uuid,stored_object_uuid,purpose,owner_kind,owner_uuid,expected_digest,expected_size,"
            "created_at,payload_extra) VALUES (?,?,?,'process_io',?,?,?,?,?, '{}')",
            (
                uuid7(),
                team_uuid,
                stored_object_uuid,
                owner_kind,
                owner_uuid,
                stat.sha256,
                stat.size_bytes,
                self._now(),
            ),
        )
        return stored_object_uuid

    async def _stage_inline_ingress(self, request: TaskCreateRequest) -> ObjectStat | None:
        """Promote a canonical inline body before any task-facing persistence.

        The public descriptor is intentionally short-lived: once admitted, an
        inline source is represented exclusively by a Team-scoped logical
        handle plus the independently declared digest and byte count.
        """

        if not isinstance(request.payload, IntakeIngestPayload) or not isinstance(
            request.payload.source, InlineSourceDescriptor
        ):
            return None
        source = request.payload.source
        text = self.canonicalize_inline_text(source.content)
        return await self.storage.promote(
            text.encode("utf-8"),
            PromoteRequest(
                team_uuid=request.team_uuid,
                purpose="process_io",
                media_type=source.media_type,
            ),
        )

    @classmethod
    def _execution_payload(
        cls,
        request: TaskCreateRequest,
        inline_ingress: ObjectStat | None,
        prompt_selection: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Return the only payload shape a Process is allowed to receive."""

        payload = request.payload.model_dump(mode="json")
        if prompt_selection:
            payload["prompt_selection"] = prompt_selection
        if isinstance(request.payload, IntakeIngestPayload) and payload.get("compression_channel") is None:
            channel, source = cls._resolve_compression_channel(request)
            payload["compression_channel"] = channel
            payload["channel_source"] = source
        if inline_ingress is None:
            return payload
        source = payload.get("source")
        if not isinstance(source, dict) or source.get("source_kind") != "inline_payload":
            raise MkbError("INGRESS_STAGE_INVALID", "Inline ingress does not match the request payload", 503)
        # ``pop`` is intentionally unconditional.  A future caller of this
        # helper must not be able to accidentally preserve a raw body in an
        # immutable Process input by adding another inline field.
        source.pop("content", None)
        source.update(
            {
                "logical_handle": inline_ingress.handle.value,
                "content_digest": inline_ingress.sha256,
                "size_bytes": inline_ingress.size_bytes,
            }
        )
        return payload

    @classmethod
    def redacted_request_envelope(
        cls,
        request: TaskCreateRequest,
        inline_ingress: ObjectStat | None,
    ) -> dict[str, Any]:
        """Build an audit-safe task envelope without changing idempotency.

        ``TaskService`` still fingerprints the original validated request, so
        a replay has the exact legacy identity semantics.  This method changes
        only what is persisted for later audit/projection inspection.
        """

        envelope = request.model_dump(mode="json")
        if not isinstance(request.payload, IntakeIngestPayload) or not isinstance(
            request.payload.source, InlineSourceDescriptor
        ):
            return envelope
        source = envelope.get("payload", {}).get("source")
        if not isinstance(source, dict):
            raise MkbError("INGRESS_STAGE_INVALID", "Inline audit source is unavailable", 503)
        raw = source.pop("content", None)
        if not isinstance(raw, str):
            raise MkbError("INGRESS_STAGE_INVALID", "Inline audit source content is unavailable", 503)
        if inline_ingress is None:
            # Isolated aggregate tests may intentionally omit the composition
            # service.  They still must never persist an inline body.
            canonical = cls.canonicalize_inline_text(raw).encode("utf-8")
            source.update({"content_digest": sha256_bytes(canonical), "size_bytes": len(canonical)})
        else:
            source.update(
                {
                    "logical_handle": inline_ingress.handle.value,
                    "content_digest": inline_ingress.sha256,
                    "size_bytes": inline_ingress.size_bytes,
                }
            )
        return envelope

    @staticmethod
    def canonicalize_inline_text(value: str) -> str:
        """Canonical text bytes for deterministic ingestion (UTF-8/NFC/LF)."""

        return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))

    @staticmethod
    def _workflow_purpose(request_intent: str) -> str:
        # v1 has one code-owned durable skeleton.  Each external intent is
        # still frozen into L4 and dispatched by typed pipeline handling; this
        # does not turn an intent into a process name or allow a caller to
        # select graph internals.
        if request_intent not in {
            "intake.ingest",
            "intake.rebuild",
            "intake.update_metadata",
            "intake.deactivate",
            "intake.reactivate",
            "intake.delete",
            "index.rebuild",
        }:
            raise MkbError("workflow-intent-not-supported", "No workflow is registered for this Task intent", 422)
        return "intake.ingest"

    @staticmethod
    def _source_profile(request: TaskCreateRequest) -> str | None:
        """Resolve a bounded code-owned S05 profile before freezing L4.

        Callers choose only the strict descriptor's source kind/mode/media
        declaration.  They cannot name a workflow or a clean capability; this
        function maps that small typed surface to the reviewed registry key.
        """

        if not isinstance(request.payload, IntakeIngestPayload):
            return None
        source = request.payload.source.model_dump(mode="json")
        source_kind = source.get("source_kind")
        if source_kind == "http_resource":
            mode = source.get("acquisition_mode", "static")
            return f"http_resource.{mode}" if mode in {"static", "browser", "pdf"} else None
        if source_kind == "local_object":
            media_type = source.get("media_type")
            if isinstance(media_type, str):
                normalized_media_type = media_type.split(";", 1)[0].strip().lower()
                if normalized_media_type == "application/pdf":
                    return "local_object.pdf"
                if normalized_media_type.startswith("image/"):
                    return "local_object.image"
            return "local_object"
        return source_kind if isinstance(source_kind, str) else None

    async def _resolve_intent_context(self, request: TaskCreateRequest) -> dict[str, Any] | None:
        """Freeze all pre-existing Intake targets before a new Task UoW.

        The resolver never copies mutable aliases, raw paths, or connector
        credentials into an Execution input.  Later Process callbacks compare
        the frozen Item revision before changing canonical truth.
        """

        if request.request_intent == "intake.ingest":
            return None
        if request.request_intent == "intake.rebuild":
            assert isinstance(request.payload, IntakeRebuildPayload)
            return {"target": (await self.targets.resolve_rebuild(request.team_uuid, request.payload)).as_manifest()}
        if request.request_intent == "intake.update_metadata":
            assert isinstance(request.payload, IntakeUpdateMetadataPayload)
            return (await self.targets.resolve_metadata_update(request.team_uuid, request.payload)).as_manifest()
        if request.request_intent in {"intake.deactivate", "intake.reactivate", "intake.delete"}:
            assert isinstance(request.payload, IntakeLifecyclePayload)
            return {
                "target": (await self.targets.resolve_lifecycle_target(request.team_uuid, request.payload)).as_manifest()
            }
        if request.request_intent == "index.rebuild":
            assert isinstance(request.payload, IndexRebuildPayload)
            return {"scope": (await self.targets.resolve_index_rebuild(request.team_uuid, request.payload)).as_manifest()}
        raise MkbError("workflow-intent-not-supported", "No workflow is registered for this Task intent", 422)

    def _load_l0(self) -> dict[str, Any]:
        path = self.settings.config_root / "default.toml"
        try:
            raw = tomllib.loads(path.read_text(encoding="utf-8"))
        except (OSError, tomllib.TOMLDecodeError) as exc:
            raise MkbError("CONFIG_MISSING", "The checked-in default configuration is unavailable", 503) from exc
        if not isinstance(raw, dict):
            raise MkbError("CONFIG_CONFLICT", "Default configuration must be a TOML object", 503)
        return raw

    async def _load_l1(self) -> dict[str, list[dict[str, Any]]]:
        async with self.persistence.transaction() as tx:
            prompts = await tx.fetchall(
                "SELECT prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,granularity_set "
                "FROM mkb_prompt_hash_pointers "
                "ORDER BY prompt_key,prompt_version"
            )
            models = await tx.fetchall(
                "SELECT model_key,model_version,modality,default_dimension,definition_digest FROM mkb_model_catalog "
                "WHERE status='active' ORDER BY model_key,model_version"
            )
            bindings = await tx.fetchall(
                "SELECT capability_key,adapter_kind,model_key,model_version,priority,binding_digest,team_uuid "
                "FROM mkb_adapter_bindings WHERE enabled=1 ORDER BY capability_key,"
                "CASE WHEN team_uuid IS NULL THEN 1 ELSE 0 END,priority,binding_uuid"
            )
        if not prompts or not models:
            raise MkbError("REGISTRY_NOT_FOUND", "Registry bootstrap rows are unavailable", 503)
        return {"prompts": prompts, "models": models, "bindings": bindings}

    async def _load_l4_schema_freeze(self) -> dict[str, Any]:
        """Freeze registry schema SHA plus the checked-in layered JSON schema file."""

        async with self.persistence.transaction() as tx:
            structure_rows = await tx.fetchall(
                "SELECT schema_key,schema_version,schema_digest FROM mkb_structure_schema_definitions "
                "ORDER BY schema_key,schema_version"
            )
            construction_rows = await tx.fetchall(
                "SELECT schema_key,schema_version,schema_digest FROM mkb_construction_schema_definitions "
                "ORDER BY schema_key,schema_version"
            )
        schemas = {
            f"{row['schema_key']}@{row['schema_version']}": {
                "schema_key": row["schema_key"],
                "schema_version": row["schema_version"],
                "schema_digest": row["schema_digest"],
            }
            for row in (*structure_rows, *construction_rows)
        }
        layered_path = Path("data/schemas/lsrag.layered_content.v1.json")
        layered_sha = hashlib.sha256(layered_path.read_bytes()).hexdigest() if layered_path.is_file() else None
        return {"schemas": schemas, "layered_schema_sha256": layered_sha}

    @staticmethod
    def _resolve_compression_channel(request: TaskCreateRequest) -> tuple[str, str]:
        if not isinstance(request.payload, IntakeIngestPayload):
            return DEFAULT_COMPRESSION_CHANNEL, "default"
        if request.payload.compression_channel is not None:
            return request.payload.compression_channel, "explicit"
        priority = request.priority or "normal"
        if priority in {"urgent", "high"}:
            return "non-interactive", "priority"
        return "local-inference", "priority"

    def _require_compression_channel(self, request: TaskCreateRequest) -> tuple[str, str]:
        channel, channel_source = self._resolve_compression_channel(request)
        if channel_source == "explicit" and channel == "local-inference" and not self.settings.live_inference:
            raise MkbError(
                "COMPRESSION_CHANNEL_UNAVAILABLE",
                "local-inference compression requires live inference",
                503,
            )
        return channel, channel_source

    def _resolve_prompt_selection(
        self,
        prompt_rows: list[dict[str, Any]],
        request: TaskCreateRequest,
    ) -> dict[str, Any]:
        """Resolve the four role identities into one immutable input object."""

        if not isinstance(request.payload, IntakeIngestPayload):
            return {}
        try:
            domain_defaults = default_prompt_ids(
                domain=request.payload.domain,
                flavor=request.payload.flavor,
                granularity=request.payload.granularity,
            )
        except ValueError as exc:
            raise MkbError("PROMPT_PROFILE_INVALID", str(exc), 422) from exc
        requested = {
            "clean": request.payload.clean_prompt_id or domain_defaults.get("clean") or _DEFAULT_PROMPT_IDS["clean"],
            "markdown": request.payload.markdown_prompt_id or domain_defaults.get("markdown"),
            "json": request.payload.json_prompt_id or domain_defaults.get("json"),
            "summarizer": request.payload.summarizer_prompt_id
            or domain_defaults.get("summarizer")
            or _DEFAULT_PROMPT_IDS["summarizer"],
        }
        if not requested["json"]:
            raise MkbError("PROMPT_NOT_REGISTERED", "json prompt is required", 422)
        by_id: dict[str, list[dict[str, Any]]] = {}
        for row in prompt_rows:
            prompt_id = row.get("prompt_id") or row.get("prompt_key")
            if isinstance(prompt_id, str):
                by_id.setdefault(prompt_id, []).append(row)
        selected: dict[str, Any] = {}
        for role, prompt_id in requested.items():
            if prompt_id is None:
                selected[role] = None
                continue
            candidates = [row for row in by_id.get(prompt_id, []) if row.get("status") == "active"]
            if not candidates:
                raise MkbError("PROMPT_NOT_REGISTERED", f"Active {role} prompt is unavailable", 503)
            row = select_latest_catalog_row(candidates)
            if row.get("role") != role:
                raise MkbError("PROMPT_ROLE_MISMATCH", f"Prompt id is not registered for role {role}", 422)
            relative_path = row.get("git_relative_path")
            expected_sha = row.get("content_sha256")
            version = row.get("prompt_version")
            if not isinstance(relative_path, str) or not isinstance(expected_sha, str) or not isinstance(version, str):
                raise MkbError("PROMPT_CATALOG_INVALID", "Prompt catalog identity is incomplete", 503)
            path_fragment = Path(relative_path)
            if path_fragment.is_absolute() or ".." in path_fragment.parts:
                raise MkbError("PROMPT_CATALOG_PATH_INVALID", "Prompt catalog path is invalid", 503)
            path = (self.settings.prompt_root / path_fragment).resolve()
            try:
                path.relative_to(self.settings.prompt_root.resolve())
                prompt_bytes = path.read_bytes()
            except (OSError, ValueError) as exc:
                raise MkbError("PROMPT_HASH_MISMATCH", "Prompt bytes are unavailable", 503) from exc
            actual_sha = hashlib.sha256(prompt_bytes).hexdigest()
            if actual_sha != expected_sha:
                raise MkbError("PROMPT_HASH_MISMATCH", "Prompt bytes do not match the catalog pointer", 503)
            granularity_set = row.get("granularity_set")
            if role == "json":
                if not isinstance(granularity_set, str):
                    raise MkbError("PROMPT_CATALOG_GRANULARITY_INVALID", "json prompt profile is unavailable", 503)
                try:
                    parsed_profile = json.loads(granularity_set)
                except json.JSONDecodeError as exc:
                    raise MkbError("PROMPT_CATALOG_GRANULARITY_INVALID", "json prompt profile is invalid", 503) from exc
                if (
                    not isinstance(parsed_profile, list)
                    or not parsed_profile
                    or any(isinstance(item, bool) or not isinstance(item, int) for item in parsed_profile)
                    or tuple(parsed_profile) != tuple(sorted(set(parsed_profile)))
                    or any(item not in {0, 1, 2} for item in parsed_profile)
                ):
                    raise MkbError("PROMPT_CATALOG_GRANULARITY_INVALID", "json prompt profile is invalid", 503)
                normalized_profile: list[int] | None = parsed_profile
            elif granularity_set is not None:
                raise MkbError("PROMPT_CATALOG_GRANULARITY_INVALID", "non-json prompt has a profile", 503)
            else:
                normalized_profile = None
            selected[role] = {
                "prompt_id": str(row.get("prompt_id") or row.get("prompt_key")),
                "version": version,
                "content_sha256": expected_sha,
                "git_relative_path": relative_path,
                "role": role,
                "granularity_set": normalized_profile,
            }
        requested_level = request.payload.granularity
        if requested_level is not None:
            json_selection = selected.get("json")
            actual = json_selection.get("granularity_set") if isinstance(json_selection, dict) else None
            if actual != list(GRANULARITY_LEVELS[requested_level]):
                raise MkbError(
                    "PROMPT_GRANULARITY_MISMATCH",
                    "json prompt granularity_set does not match the requested granularity level",
                    422,
                )
        return selected

    def _resolve_bindings(self, rows: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        selected: dict[str, dict[str, Any]] = {}
        for capability in self.REQUIRED_CAPABILITIES:
            candidates = [row for row in rows if row["capability_key"] == capability and row["team_uuid"] is None]
            if not candidates:
                raise MkbError("REGISTRY_NOT_FOUND", f"No enabled binding for {capability}", 503)
            first = candidates[0]
            if len(candidates) > 1 and candidates[1]["priority"] == first["priority"]:
                raise MkbError("CONFIG_CONFLICT", f"Binding priority is ambiguous for {capability}", 503)
            selected[capability] = {
                "adapter_kind": first["adapter_kind"],
                "model_key": first["model_key"],
                "model_version": first["model_version"],
                "binding_digest": first["binding_digest"],
            }
        return selected

    @staticmethod
    def _deterministic_embed_binding() -> dict[str, Any]:
        body = {
            "capability": "embed",
            "adapter_kind": "deterministic",
            "model_key": "deterministic-hash-v1",
            "model_version": "v1",
        }
        return {
            "adapter_kind": body["adapter_kind"],
            "model_key": body["model_key"],
            "model_version": body["model_version"],
            "dimension": 64,
            "binding_digest": stable_digest(body),
        }

    def _load_flag_bundle(self) -> tuple[dict[str, bool], str]:
        """Load the checked-in default-OFF feature flag bundle (S14-T037)."""

        path = self.settings.config_root / "feature_flags.yaml"
        try:
            raw_bytes = path.read_bytes()
            raw = yaml.safe_load(raw_bytes.decode("utf-8"))
        except (OSError, UnicodeDecodeError, yaml.YAMLError) as exc:
            raise MkbError("CONFIG_MISSING", "Feature flag bundle is unavailable", 503) from exc
        if not isinstance(raw, dict):
            raise MkbError("CONFIG_CONFLICT", "Feature flag bundle must be a mapping", 503)
        flags_raw = raw.get("flags", {})
        if not isinstance(flags_raw, dict):
            raise MkbError("CONFIG_CONFLICT", "Feature flag bundle flags must be a mapping", 503)
        flags: dict[str, bool] = {}
        for key, value in flags_raw.items():
            if not isinstance(key, str) or not key:
                raise MkbError("CONFIG_CONFLICT", "Feature flag names must be non-empty strings", 503)
            if not isinstance(value, bool):
                raise MkbError("CONFIG_CONFLICT", "Feature flag values must be booleans", 503)
            flags[key] = value
        # Default-OFF product rule: materialize fails closed if any checked-in
        # flag is unexpectedly true without an explicit owner ceremony.
        if any(flags.values()):
            raise MkbError("CONFIG_CONFLICT", "v1 feature flags must default OFF", 503)
        digest = hashlib.sha256(raw_bytes).hexdigest()
        return flags, digest

    def _resolve_overrides(
        self, overrides: dict[str, Any] | None
    ) -> tuple[dict[str, Any], dict[str, Any], str | None, dict[str, Any]]:
        """Apply the S14 allowlist, caps, and semantic/ops split.

        Returns ``(semantic_overrides, ops_overrides, override_digest, semantic_knobs)``.
        Ops-only keys never enter ``override_digest`` (S14-A17).
        """

        if overrides is None:
            return {}, {}, None, self._default_semantic_knobs()
        if not isinstance(overrides, dict):
            raise MkbError("CONFIG_OVERRIDE_REJECTED", "Override bag must be a JSON object", 422)
        raw = {str(key): value for key, value in overrides.items() if value is not None}
        for key in raw:
            if key in _FORBIDDEN_OVERRIDE_KEYS or key.startswith("security.") or key.startswith("obs."):
                raise MkbError("CONFIG_OVERRIDE_REJECTED", f"Override key is not allowlisted: {key}", 422)
        semantic_applied: dict[str, Any] = {}
        ops_applied: dict[str, Any] = {}
        if "profile_id" in raw:
            profile_id = raw["profile_id"]
            if not isinstance(profile_id, str) or profile_id not in _REGISTERED_PROFILES:
                raise MkbError("CONFIG_OVERRIDE_REJECTED", "profile_id is not registered", 422)
            semantic_applied["profile_id"] = profile_id
        for key, cap in _OVERRIDE_CAPS.items():
            if key not in raw:
                continue
            value = raw[key]
            if not isinstance(value, int) or isinstance(value, bool) or value < 1 or value > cap:
                raise MkbError("CONFIG_OVERRIDE_REJECTED", f"Override {key} exceeds cap or is invalid", 422)
            semantic_applied[key] = value
        for key in ("dry_run", "debug_trace"):
            if key in raw:
                if not isinstance(raw[key], bool):
                    raise MkbError("CONFIG_OVERRIDE_REJECTED", f"Override {key} must be boolean", 422)
                ops_applied[key] = raw[key]
        allowed = set(_OVERRIDE_CAPS) | {"profile_id", "dry_run", "debug_trace"}
        unknown = set(raw) - allowed
        if unknown:
            raise MkbError(
                "CONFIG_OVERRIDE_REJECTED",
                f"Override key is not allowlisted: {sorted(unknown)[0]}",
                422,
            )
        # Semantic-only digest: ops knobs must not change binding identity.
        override_digest = stable_digest(semantic_applied) if semantic_applied else None
        semantic = self._default_semantic_knobs()
        for key in ("profile_id", "batch_size", "top_k", "return_k", "recall_k", "pack_budget"):
            if key in semantic_applied:
                semantic[key] = semantic_applied[key]
        return semantic_applied, ops_applied, override_digest, semantic

    @staticmethod
    def _default_semantic_knobs() -> dict[str, Any]:
        return {
            "profile_id": "clean.default.v1",
            "batch_size": 16,
            "top_k": 20,
            "return_k": 10,
            "recall_k": 40,
            "pack_budget": 8_000,
        }

    async def audit_explicit_channel(self, tx: UnitOfWork, request: TaskCreateRequest) -> None:
        """Record a successful explicit compression_channel override (NS2-T38)."""

        if not isinstance(request.payload, IntakeIngestPayload) or request.payload.compression_channel is None:
            return
        channel, source = self._resolve_compression_channel(request)
        if source != "explicit":
            return
        try:
            await self.security_audit.write_allowed(
                tx,
                action="config.compression_channel_override",
                summary="Explicit compression channel override accepted",
                http_status=200,
                actor_kind="internal_token",
                team_uuid=request.team_uuid,
                trace_uuid=request.trace_uuid,
                target_kind="task",
                target_uuid=request.task_uuid,
                payload={
                    "channel": channel,
                    "channel_source": source,
                    "priority": request.priority or "normal",
                    "actor_origin": "task.create",
                    "result": "allowed",
                },
            )
        except MkbError:
            raise
        except Exception as exc:
            raise MkbError("SEC_AUDIT_WRITE_FAIL", "Security audit could not record channel override", 500) from exc

    async def _audit_override_rejected(self, request: TaskCreateRequest, exc: MkbError) -> None:
        """Write the sole security-audit sink for an L3 denial (S14-T017)."""

        override_keys: list[str] = []
        if request.overrides is not None:
            override_keys = sorted(str(key) for key in request.overrides if request.overrides[key] is not None)
        try:
            async with self.persistence.transaction() as tx:
                await self.security_audit.write_denied(
                    tx,
                    action="config.override_denied",
                    denial_code="CONFIG_OVERRIDE_REJECTED",
                    summary="Task override rejected by allowlist",
                    http_status=422,
                    actor_kind="internal_token",
                    team_uuid=request.team_uuid,
                    trace_uuid=request.trace_uuid,
                    target_kind="task",
                    target_uuid=request.task_uuid,
                    payload={
                        "override_keys": override_keys,
                        "override_digest": stable_digest({"keys": override_keys}),
                        "actor_origin": "task.create",
                        "result": "rejected",
                        "error_code": exc.code,
                    },
                )
        except Exception:
            # Admission path audit failure is itself a hard fail-closed signal.
            raise MkbError("SEC_AUDIT_WRITE_FAIL", "Security audit could not record override denial", 500) from exc

    @staticmethod
    def _now() -> str:
        # Local import keeps the service's visible dependencies strictly ports,
        # contracts, storage protocol, and S14 resolver concerns.
        from src.contracts.common.time import utc_now

        return utc_now()


__all__ = ["ConfigSnapshotService", "PreparedExecutionInputs"]
