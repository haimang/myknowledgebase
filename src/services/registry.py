"""S14 bootstrap and immutable prompt/model/binding registry operations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.inference.models import InferenceBinding
from src.persistence.ports import PersistencePort


@dataclass(frozen=True, slots=True)
class PromptPointer:
    prompt_key: str
    prompt_version: str
    relative_path: str
    content_sha256: str


DEFAULT_PROMPTS = (
    # The durable identity is rendered as ``promptA.default.v1`` from the
    # explicit key/version pair; the database never stores prompt bodies.
    ("promptA.default", "v1", "prompt-a-clean-v1.md"),
    ("promptB.default", "v1", "prompt-b-structure-v1.md"),
    ("promptC.default", "v1", "prompt-c-summary-v1.md"),
)


DEFAULT_MODELS = (
    ("deterministic-hash-v1", "v1", "embed", 64),
    ("qwen-vl-2b", "v1", "embed", 64),
    ("qwen35-a3b", "v1", "generate", None),
    ("qwen-rerank-2b", "v1", "rerank", None),
)


DEFAULT_BINDINGS = (
    ("embed", "qwen-vl-2b", "v1", 10, True),
    ("structured_generate", "qwen35-a3b", "v1", 10, True),
    ("text_generate", "qwen35-a3b", "v1", 10, True),
    # Rerank is intentionally disabled by default. Retrieval reports an honest
    # ANN fallback rather than inventing a score.
    ("rerank", "qwen-rerank-2b", "v1", 10, False),
)


def default_enabled_inference_bindings() -> tuple[InferenceBinding, ...]:
    """Return the exact L1 defaults that the composition may transport.

    Registry bootstrap and the S16 supply fence deliberately share this one
    digest recipe.  A later database-side binding change is allowed to make
    admission/readiness fail closed; it must never silently repoint a live
    adapter to a model that the composition did not register.
    """

    return tuple(
        InferenceBinding(
            capability_key=capability,
            adapter_kind="local_vllm",
            model_key=key,
            model_version=version,
            binding_digest=stable_digest(
                {
                    "capability": capability,
                    "adapter_kind": "local_vllm",
                    "model_key": key,
                    "model_version": version,
                }
            ),
        )
        for capability, key, version, _priority, enabled in DEFAULT_BINDINGS
        if enabled
    )


# These are immutable registry *definitions*, not a second runtime workflow
# configuration.  Intake/generation callbacks copy their resolved digests into
# durable facts so a later bootstrap cannot silently reinterpret history.
DEFAULT_SOURCE_KINDS = (
    ("inline_payload", "single"),
    ("local_object", "single"),
    ("http_resource", "single"),
    ("registered_api", "collection"),
)

DEFAULT_ACTIONS = (
    # S04's minimum immutable transition vocabulary.  These are domain
    # definitions, not caller-selectable process names; pipeline callbacks
    # bind the exact version into Revision/transition facts.
    ("accept_revision", "active|deactivated", "create_revision"),
    ("publish_revision", "active", "advance_serving"),
    ("deactivate", "active", "deactivate"),
    ("reactivate", "deactivated", "reactivate"),
    ("delete", "active|deactivated", "delete"),
    ("absence_deactivate", "active", "deactivate"),
    ("rebuild", "active", "rebuild_generation"),
    ("index_rebuild", "active", "rebuild_generation"),
    ("no_change", "active|deactivated", "no_change"),
    # A metadata change is an explicit canonical Revision append.  Keeping it
    # separate from acceptance makes its ledger intent queryable without
    # inventing a mutable semantic side channel.
    ("update_metadata", "active|deactivated", "create_revision"),
)

DEFAULT_SEMANTICS = (
    ("source_representation", "text"),
    ("canonical_content", "text"),
    ("context_metadata", "text"),
    ("filter_metadata", "text"),
)


class RegistryService:
    def __init__(self, persistence: PersistencePort, prompt_root: Path) -> None:
        self.persistence = persistence
        self.prompt_root = prompt_root.resolve()

    def _pointer(self, key: str, version: str, relative_path: str) -> PromptPointer:
        path = (self.prompt_root / relative_path).resolve()
        if self.prompt_root not in path.parents or not path.is_file():
            raise MkbError("PROMPT_NOT_REGISTERED", "Prompt path is unavailable", 503)
        return PromptPointer(key, version, relative_path, hashlib.sha256(path.read_bytes()).hexdigest())

    async def bootstrap(self) -> None:
        pointers = [self._pointer(*definition) for definition in DEFAULT_PROMPTS]
        async with self.persistence.transaction() as tx:
            for pointer in pointers:
                row = await tx.fetchone(
                    "SELECT content_sha256, git_relative_path FROM mkb_prompt_hash_pointers "
                    "WHERE prompt_key=? AND prompt_version=?",
                    (pointer.prompt_key, pointer.prompt_version),
                )
                if row and (
                    row["content_sha256"] != pointer.content_sha256 or row["git_relative_path"] != pointer.relative_path
                ):
                    raise MkbError("REGISTRY_DIGEST_MISMATCH", "Prompt pointer digest conflicts", 503)
                if not row:
                    await tx.execute(
                        "INSERT INTO mkb_prompt_hash_pointers "
                        "(prompt_key,prompt_version,git_relative_path,content_sha256,registered_at,payload_extra) "
                        "VALUES (?,?,?,?,?, '{}')",
                        (
                            pointer.prompt_key,
                            pointer.prompt_version,
                            pointer.relative_path,
                            pointer.content_sha256,
                            utc_now(),
                        ),
                    )
            for key, version, modality, dimension in DEFAULT_MODELS:
                definition_digest = stable_digest(
                    {"model_key": key, "model_version": version, "modality": modality, "dimension": dimension}
                )
                row = await tx.fetchone(
                    "SELECT definition_digest FROM mkb_model_catalog WHERE model_key=? AND model_version=?",
                    (key, version),
                )
                if row and row["definition_digest"] != definition_digest:
                    raise MkbError("REGISTRY_DIGEST_MISMATCH", "Model definition conflicts", 503)
                if not row:
                    await tx.execute(
                        "INSERT INTO mkb_model_catalog "
                        "(model_uuid,model_key,model_version,modality,provider_family,default_dimension,"
                        "definition_digest,status,display_name,registered_at,payload_extra) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?, '{}')",
                        (
                            uuid7(),
                            key,
                            version,
                            modality,
                            "vllm_local",
                            dimension,
                            definition_digest,
                            "active",
                            key,
                            utc_now(),
                        ),
                    )
            for capability, key, version, priority, enabled in DEFAULT_BINDINGS:
                binding_digest = stable_digest(
                    {
                        "capability": capability,
                        "adapter_kind": "local_vllm",
                        "model_key": key,
                        "model_version": version,
                    }
                )
                row = await tx.fetchone(
                    "SELECT binding_digest FROM mkb_adapter_bindings "
                    "WHERE capability_key=? AND adapter_kind='local_vllm' AND model_key=? "
                    "AND model_version=? AND team_uuid IS NULL",
                    (capability, key, version),
                )
                if row and row["binding_digest"] != binding_digest:
                    raise MkbError("REGISTRY_DIGEST_MISMATCH", "Adapter binding conflicts", 503)
                if not row:
                    await tx.execute(
                        "INSERT INTO mkb_adapter_bindings "
                        "(binding_uuid,capability_key,adapter_kind,model_key,model_version,priority,team_uuid,"
                        "enabled,binding_digest,created_at,updated_at,payload_extra) "
                        "VALUES (?,?,?,?,?,?,NULL,?,?,?, ?, '{}')",
                        (
                            uuid7(),
                            capability,
                            "local_vllm",
                            key,
                            version,
                            priority,
                            int(enabled),
                            binding_digest,
                            utc_now(),
                            utc_now(),
                        ),
                    )
            await self._bootstrap_domain_definitions(tx)

    async def active_inference_bindings(self) -> tuple[InferenceBinding, ...]:
        """Resolve the global L1 winners used by newly frozen executions.

        This is a readiness/audit read, not a dynamic adapter resolver.  The
        application supply fence remains a separately compiled allow-list, so
        a registry change can only make readiness fail closed until a reviewed
        deployment updates that allow-list.
        """

        async with self.persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT capability_key,adapter_kind,model_key,model_version,binding_digest,priority,binding_uuid "
                "FROM mkb_adapter_bindings WHERE enabled=1 AND team_uuid IS NULL "
                "ORDER BY capability_key,priority,binding_uuid"
            )
        expected = {binding.capability_key for binding in default_enabled_inference_bindings()}
        selected: list[InferenceBinding] = []
        for capability in sorted(expected):
            candidates = [row for row in rows if row["capability_key"] == capability]
            if not candidates:
                raise MkbError("REGISTRY_NOT_FOUND", f"No enabled binding for {capability}", 503)
            if len(candidates) > 1 and candidates[1]["priority"] == candidates[0]["priority"]:
                raise MkbError("CONFIG_CONFLICT", f"Binding priority is ambiguous for {capability}", 503)
            try:
                selected.append(
                    InferenceBinding.model_validate(
                        {
                            key: candidates[0][key]
                            for key in ("capability_key", "adapter_kind", "model_key", "model_version", "binding_digest")
                        }
                    )
                )
            except Exception as exc:
                raise MkbError("CONFIG_CONFLICT", f"Binding for {capability} is invalid", 503) from exc
        return tuple(selected)

    async def _bootstrap_domain_definitions(self, tx: object) -> None:
        """Install the small immutable definition set consumed by S04--S09.

        ``tx`` is intentionally structural here rather than a concrete SQLite
        type: RegistryService remains persistence-adapter neutral like the rest
        of the services layer.
        """

        # UnitOfWork is imported lazily to keep the public surface focused on
        # S14's registry operations and to avoid a circular type-only import.
        from src.persistence.ports import UnitOfWork

        if not isinstance(tx, UnitOfWork):
            raise MkbError("REGISTRY_TX_INVALID", "Registry bootstrap transaction is invalid", 503)
        now = utc_now()
        for source_kind, cardinality in DEFAULT_SOURCE_KINDS:
            body = {
                "source_kind": source_kind,
                "version": "v1",
                "cardinality": cardinality,
                "descriptor_schema": "mkb.intake.source-descriptor.v1",
                "preflight_profile_key": "default",
            }
            digest = stable_digest(body)
            row = await tx.fetchone(
                "SELECT definition_digest FROM mkb_source_kind_definitions WHERE source_kind=? AND definition_version='v1'",
                (source_kind,),
            )
            if row is not None and row["definition_digest"] != digest:
                raise MkbError("REGISTRY_DIGEST_MISMATCH", "Source kind definition conflicts", 503)
            if row is None:
                await tx.execute(
                    "INSERT INTO mkb_source_kind_definitions "
                    "(source_kind,definition_version,definition_digest,status,descriptor_schema_ref,descriptor_schema_digest,"
                    "cardinality,acquisition_capability_digest,decode_capability_digest,clean_capability_digest,"
                    "external_key_normalizer_ref,external_key_normalizer_version,preflight_profile_key,eligibility_digest,"
                    "definition_body_json,registered_at,payload_extra) "
                    "VALUES (?,'v1',?,'active','mkb.intake.source-descriptor.v1',?,?, ?,?,?,"
                    "'mkb.normalizer.external-key','v1','default',?,?,?,'{}')",
                    (
                        source_kind,
                        digest,
                        stable_digest({"schema": "mkb.intake.source-descriptor.v1"}),
                        cardinality,
                        stable_digest({"source": source_kind, "capability": "acquire"}),
                        stable_digest({"source": source_kind, "capability": "decode"}),
                        stable_digest({"source": source_kind, "capability": "clean"}),
                        stable_digest({"source": source_kind, "eligibility": "v1"}),
                        __import__("json").dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        now,
                    ),
                )
        for action_key, allowed_from, effect in DEFAULT_ACTIONS:
            body = {"action_key": action_key, "version": "v1", "allowed_from": allowed_from, "effect": effect}
            digest = stable_digest(body)
            row = await tx.fetchone(
                "SELECT definition_digest FROM mkb_intake_action_definitions WHERE action_key=? AND definition_version='v1'",
                (action_key,),
            )
            if row is not None and row["definition_digest"] != digest:
                raise MkbError("REGISTRY_DIGEST_MISMATCH", "Intake action definition conflicts", 503)
            if row is None:
                await tx.execute(
                    "INSERT INTO mkb_intake_action_definitions "
                    "(action_key,definition_version,allowed_from_mask,required_proof_kind,precondition_class,core_effect_mask,"
                    "idempotency_scope,definition_digest,definition_body_json,registered_at,payload_extra) "
                    "VALUES (?,'v1',?,NULL,'registered_precondition',?,'item_revision',?,?,?,'{}')",
                    (
                        action_key,
                        allowed_from,
                        effect,
                        digest,
                        __import__("json").dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        now,
                    ),
                )
        for semantic_key, value_kind in DEFAULT_SEMANTICS:
            body = {"semantic_key": semantic_key, "version": "v1", "value_kind": value_kind}
            digest = stable_digest(body)
            row = await tx.fetchone(
                "SELECT definition_digest FROM mkb_intake_semantic_definitions WHERE semantic_key=? AND definition_version='v1'",
                (semantic_key,),
            )
            if row is not None and row["definition_digest"] != digest:
                raise MkbError("REGISTRY_DIGEST_MISMATCH", "Intake semantic definition conflicts", 503)
            if row is None:
                await tx.execute(
                    "INSERT INTO mkb_intake_semantic_definitions "
                    "(semantic_key,definition_version,value_kind,fingerprint_participation,definition_digest,definition_body_json,"
                    "registered_at,payload_extra) VALUES (?,'v1',?,1,?,?,?,'{}')",
                    (
                        semantic_key,
                        value_kind,
                        digest,
                        __import__("json").dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")),
                        now,
                    ),
                )
        await self._ensure_preflight_schema_definitions(tx, now)

    async def _ensure_preflight_schema_definitions(self, tx: object, now: str) -> None:
        """Register the immutable S05/S06/S07 schema coordinates."""

        from src.persistence.ports import UnitOfWork

        if not isinstance(tx, UnitOfWork):
            raise MkbError("REGISTRY_TX_INVALID", "Registry bootstrap transaction is invalid", 503)
        preflight_body = {"profile_key": "default", "version": "v1", "checks": ["nonempty", "bounded"]}
        preflight_digest = stable_digest(preflight_body)
        row = await tx.fetchone(
            "SELECT definition_digest FROM mkb_preflight_profile_definitions WHERE profile_key='default' AND definition_version='v1'"
        )
        if row is not None and row["definition_digest"] != preflight_digest:
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Preflight definition conflicts", 503)
        if row is None:
            await tx.execute(
                "INSERT INTO mkb_preflight_profile_definitions "
                "(profile_key,definition_version,check_set_digest,definition_digest,definition_body_json,registered_at,payload_extra) "
                "VALUES ('default','v1',?,?,?,?, '{}')",
                (
                    stable_digest(preflight_body["checks"]),
                    preflight_digest,
                    __import__("json").dumps(preflight_body, sort_keys=True, separators=(",", ":")),
                    now,
                ),
            )
        structure_body = {"schema_key": "lsrag.structure.default", "version": "v1", "artifact": "structure_document"}
        structure_digest = stable_digest(structure_body)
        row = await tx.fetchone(
            "SELECT schema_digest FROM mkb_structure_schema_definitions "
            "WHERE schema_key='lsrag.structure.default' AND schema_version='v1'"
        )
        if row is not None and row["schema_digest"] != structure_digest:
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Structure schema definition conflicts", 503)
        if row is None:
            await tx.execute(
                "INSERT INTO mkb_structure_schema_definitions "
                "(schema_key,schema_version,schema_digest,schema_dialect,deterministic_kernel_schema_digest,"
                "semantic_invariant_manifest_digest,artifact_type,media_contracts_digest,registration_origin,"
                "definition_body_json,registered_at,payload_extra) "
                "VALUES ('lsrag.structure.default','v1',?,'json',?,?, 'structure_document',?,'code_bootstrap',?,?,'{}')",
                (
                    structure_digest,
                    stable_digest({"kernel": "lsrag.structure.default.v1"}),
                    stable_digest({"invariants": "structure.v1"}),
                    stable_digest({"media": "application/json"}),
                    __import__("json").dumps(structure_body, sort_keys=True, separators=(",", ":")),
                    now,
                ),
            )
        construction_body = {
            "schema_key": "lsrag.construction.default",
            "version": "v1",
            "artifact": "dual_channel_projection",
        }
        construction_digest = stable_digest(construction_body)
        row = await tx.fetchone(
            "SELECT schema_digest FROM mkb_construction_schema_definitions "
            "WHERE schema_key='lsrag.construction.default' AND schema_version='v1'"
        )
        if row is not None and row["schema_digest"] != construction_digest:
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Construction schema definition conflicts", 503)
        if row is None:
            await tx.execute(
                "INSERT INTO mkb_construction_schema_definitions "
                "(schema_key,schema_version,schema_digest,structure_schema_range,content_full_recipe_version,"
                "channel_contracts_digest,semantic_invariant_manifest_digest,media_contracts_digest,registration_origin,"
                "definition_body_json,registered_at,payload_extra) "
                "VALUES ('lsrag.construction.default','v1',?,'lsrag.structure.default@v1','content_full.v1',?,?,?,"
                "'code_bootstrap',?,?,'{}')",
                (
                    construction_digest,
                    stable_digest({"channels": ["original", "summary"]}),
                    stable_digest({"invariants": "construction.v1"}),
                    stable_digest({"media": "application/json"}),
                    __import__("json").dumps(construction_body, sort_keys=True, separators=(",", ":")),
                    now,
                ),
            )

    async def load_prompt(self, prompt_key: str, prompt_version: str) -> tuple[str, str]:
        async with self.persistence.transaction() as tx:
            pointer = await tx.fetchone(
                "SELECT git_relative_path, content_sha256 FROM mkb_prompt_hash_pointers "
                "WHERE prompt_key=? AND prompt_version=?",
                (prompt_key, prompt_version),
            )
        if pointer is None:
            raise MkbError("PROMPT_NOT_REGISTERED", "Prompt is not registered", 503)
        path = (self.prompt_root / pointer["git_relative_path"]).resolve()
        if self.prompt_root not in path.parents or not path.is_file():
            raise MkbError("PROMPT_HASH_MISMATCH", "Prompt bytes are unavailable", 503)
        contents = path.read_text(encoding="utf-8")
        if hashlib.sha256(contents.encode("utf-8")).hexdigest() != pointer["content_sha256"]:
            raise MkbError("PROMPT_HASH_MISMATCH", "Prompt bytes no longer match the registered digest", 503)
        return contents, pointer["content_sha256"]

    async def readiness(self) -> bool:
        try:
            async with self.persistence.transaction() as tx:
                prompt_rows = await tx.fetchall("SELECT prompt_key,prompt_version FROM mkb_prompt_hash_pointers")
                model_count = await tx.fetchone("SELECT COUNT(*) AS count FROM mkb_model_catalog WHERE status='active'")
                bindings = await tx.fetchall(
                    "SELECT capability_key FROM mkb_adapter_bindings WHERE enabled=1 AND adapter_kind='local_vllm'"
                )
            expected = {(item[0], item[1]) for item in DEFAULT_PROMPTS}
            if {(row["prompt_key"], row["prompt_version"]) for row in prompt_rows} < expected:
                return False
            for key, version, _ in DEFAULT_PROMPTS:
                await self.load_prompt(key, version)
            required = {"embed", "structured_generate", "text_generate"}
            bound = {row["capability_key"] for row in bindings}
            return bool(model_count and model_count["count"] >= 2 and required <= bound)
        except Exception:
            return False
