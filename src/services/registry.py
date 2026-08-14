"""S14 bootstrap and immutable prompt/model/binding registry operations."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal

from intake.api.registry import registered_provider_manifest_digest
from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.contracts.inference.models import InferenceBinding
from src.contracts.intake.strategies import clean_strategy_manifest_digest
from src.persistence.ports import PersistencePort


@dataclass(frozen=True, slots=True)
class PromptPointer:
    prompt_key: str
    prompt_version: str
    relative_path: str
    content_sha256: str


@dataclass(frozen=True, slots=True)
class PromptCatalogEntry:
    prompt_id: str
    prompt_key: str
    prompt_version: str
    relative_path: str
    content_sha256: str
    role: Literal["clean", "markdown", "json", "summarizer"]
    status: Literal["active", "retired"]
    granularity_set: tuple[int, ...] | None

    def as_dict(self) -> dict[str, Any]:
        return {
            "prompt_id": self.prompt_id,
            "prompt_key": self.prompt_key,
            "prompt_version": self.prompt_version,
            "git_relative_path": self.relative_path,
            "content_sha256": self.content_sha256,
            "role": self.role,
            "status": self.status,
            "granularity_set": None if self.granularity_set is None else list(self.granularity_set),
        }


DEFAULT_PROMPTS = (
    # The durable identity is rendered as ``promptA.default.v1`` from the
    # explicit key/version pair; the database never stores prompt bodies.
    ("promptA.default", "v1", "prompt-a-clean-v1.md"),
    ("promptB.default", "v1", "prompt-b-structure-v1.md"),
    ("promptC.default", "v1", "prompt-c-summary-v1.md"),
)


# The legacy-compatible promptA/B/C rows remain addressable so already-frozen
# v1 pointers stay valid.  New callers resolve the four-role defaults below;
# no row contains prompt body text.
DEFAULT_CATALOG_PROMPTS = (
    ("promptA.clean", "v1", "clean/promptA.clean.v1.md", "clean", None),
    ("promptA.default", "v1", "prompt-a-clean-v1.md", "clean", None),
    ("promptB.markdown.legal", "v1", "markdown/promptB.markdown.legal.v1.md", "markdown", None),
    ("promptB.json.generic", "v1", "json/promptB.json.generic.v1.md", "json", (0, 1, 2)),
    ("promptB.json.legal", "v1", "json/promptB.json.legal.v1.md", "json", (0, 1)),
    ("promptB.json.realestate", "v1", "json/promptB.json.realestate.v1.md", "json", (0,)),
    ("promptB.default", "v1", "prompt-b-structure-v1.md", "json", (0, 1, 2)),
    ("promptC.summarizer", "v1", "summarizer/promptC.summarizer.v1.md", "summarizer", None),
    ("promptC.default", "v1", "prompt-c-summary-v1.md", "summarizer", None),
)

_PROMPT_ID = re.compile(r"^[A-Za-z][A-Za-z0-9_.-]{0,127}$")
_PROMPT_VERSION = re.compile(r"^v[0-9]+(?:[.-][A-Za-z0-9_.-]+)?$")
_PROMPT_ROLES = frozenset({"clean", "markdown", "json", "summarizer"})


def prompt_version_sort_key(version: str) -> tuple[int, str]:
    """Order ``v10`` after ``v9``. Lexical DESC would put ``v9`` first."""

    match = re.fullmatch(r"v(\d+)(.*)", version or "")
    if match is None:
        return (-1, version or "")
    return (int(match.group(1)), match.group(2))


def select_latest_catalog_row(rows: list[Mapping[str, Any]]) -> Mapping[str, Any]:
    """Pick the numerically latest catalog row from an already-filtered set."""

    return max(rows, key=lambda row: prompt_version_sort_key(str(row.get("prompt_version") or "")))


SPARK_VL_EMBED_MODEL_KEY = "LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4"

DEFAULT_MODELS = (
    ("deterministic-hash-v1", "v1", "embed", 64),
    (SPARK_VL_EMBED_MODEL_KEY, "v1", "embed", 1024),
    ("qwen35-a3b", "v1", "generate", None),
    ("qwen-rerank-2b", "v1", "rerank", None),
)


DEFAULT_BINDINGS = (
    ("embed", SPARK_VL_EMBED_MODEL_KEY, "v1", 10, True),
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
DEFAULT_SOURCE_KINDS = {
    "inline_payload": {
        "cardinality": "single",
        "acquire": ("intake.acquire.inline",),
        "decode": ("intake.decode.text_json_html",),
        "clean": ("clean.extract.deterministic",),
    },
    "local_object": {
        "cardinality": "single",
        "acquire": ("intake.acquire.local_object",),
        "decode": ("intake.decode.text_json_html", "intake.decode.pdf"),
        "clean": (
            "clean.extract.deterministic",
            "clean.extract.pdf_text",
            "clean.extract.pdf_llm",
            "clean.extract.doc_llm",
            "clean.ocr.local",
            "clean.extract.vision",
        ),
    },
    "http_resource": {
        "cardinality": "single",
        "acquire": ("intake.acquire.http_static", "intake.acquire.http_browser"),
        "decode": ("intake.decode.text_json_html", "intake.decode.pdf"),
        "clean": (
            "clean.extract.web",
            "clean.extract.web_llm",
            "clean.extract.pdf_text",
            "clean.extract.pdf_llm",
        ),
    },
    "registered_api": {
        "cardinality": "collection",
        "acquire": ("intake.acquire.registered_api",),
        "decode": (),
        "clean": ("clean.map.registered_api",),
    },
}

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
    ("realm", "text"),
    ("type", "text"),
    ("channel", "text"),
    ("source_name", "text"),
    ("is_active", "int"),
    ("context_tags", "text"),
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
        pointers = [
            (self._pointer(prompt_id, version, relative_path), role, granularity_set)
            for prompt_id, version, relative_path, role, granularity_set in DEFAULT_CATALOG_PROMPTS
        ]
        async with self.persistence.transaction() as tx:
            for pointer, role, granularity_set in pointers:
                row = await tx.fetchone(
                    "SELECT content_sha256, git_relative_path, role, status, granularity_set FROM mkb_prompt_hash_pointers "
                    "WHERE prompt_id=? AND prompt_version=?",
                    (pointer.prompt_key, pointer.prompt_version),
                )
                if row and (
                    row["content_sha256"] != pointer.content_sha256
                    or row["git_relative_path"] != pointer.relative_path
                    or row["role"] != role
                    or row["status"] != "active"
                    or self._decode_granularity_set(row["granularity_set"]) != granularity_set
                ):
                    raise MkbError("REGISTRY_DIGEST_MISMATCH", "Prompt pointer digest conflicts", 503)
                if not row:
                    await tx.execute(
                        "INSERT INTO mkb_prompt_hash_pointers "
                        "(prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,"
                        "granularity_set,registered_at,payload_extra) VALUES (?,?,?,?,?,?,?,?,?, '{}')",
                        (
                            pointer.prompt_key,
                            pointer.prompt_key,
                            pointer.prompt_version,
                            pointer.relative_path,
                            pointer.content_sha256,
                            role,
                            "active",
                            None if granularity_set is None else json.dumps(granularity_set, separators=(",", ":")),
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

    @staticmethod
    def _decode_granularity_set(value: object) -> tuple[int, ...] | None:
        if value is None:
            return None
        try:
            parsed = json.loads(str(value))
        except (TypeError, ValueError, json.JSONDecodeError) as exc:
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Prompt granularity set is invalid", 503) from exc
        if not isinstance(parsed, list) or any(isinstance(item, bool) or not isinstance(item, int) for item in parsed):
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Prompt granularity set is invalid", 503)
        normalized = tuple(sorted(set(parsed)))
        if list(normalized) != parsed or any(item not in {0, 1, 2} for item in normalized):
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Prompt granularity set is invalid", 503)
        return normalized

    @classmethod
    def _validate_catalog_input(
        cls,
        *,
        prompt_id: str,
        prompt_version: str,
        relative_path: str,
        role: str,
        granularity_set: list[int] | tuple[int, ...] | None,
    ) -> tuple[str, str, str, str, tuple[int, ...] | None]:
        if not _PROMPT_ID.fullmatch(prompt_id) or not _PROMPT_VERSION.fullmatch(prompt_version):
            raise MkbError("PROMPT_CATALOG_INVALID", "Prompt id/version is invalid", 422)
        if role not in _PROMPT_ROLES:
            raise MkbError("PROMPT_CATALOG_INVALID", "Prompt role is invalid", 422)
        path = Path(relative_path)
        if path.is_absolute() or not relative_path or ".." in path.parts or path.suffix != ".md":
            raise MkbError("PROMPT_CATALOG_PATH_INVALID", "Prompt path must be a relative Markdown path", 422)
        if granularity_set is None:
            normalized = None
        else:
            if role != "json" or any(isinstance(item, bool) or not isinstance(item, int) for item in granularity_set):
                raise MkbError("PROMPT_CATALOG_GRANULARITY_INVALID", "Only json prompts may declare granularity_set", 422)
            normalized = tuple(sorted(set(granularity_set)))
            if not normalized or list(normalized) != list(granularity_set) or any(item not in {0, 1, 2} for item in normalized):
                raise MkbError("PROMPT_CATALOG_GRANULARITY_INVALID", "granularity_set must be sorted and closed", 422)
        if role == "json" and normalized is None:
            raise MkbError("PROMPT_CATALOG_GRANULARITY_INVALID", "json prompts require granularity_set", 422)
        return prompt_id, prompt_version, path.as_posix(), role, normalized

    def _catalog_entry(self, row: Mapping[str, Any]) -> PromptCatalogEntry:
        role = row.get("role")
        status = row.get("status")
        if role not in _PROMPT_ROLES or status not in {"active", "retired"}:
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Prompt catalog row is invalid", 503)
        return PromptCatalogEntry(
            prompt_id=str(row["prompt_id"] or row["prompt_key"]),
            prompt_key=str(row["prompt_key"]),
            prompt_version=str(row["prompt_version"]),
            relative_path=str(row["git_relative_path"]),
            content_sha256=str(row["content_sha256"]),
            role=role,
            status=status,
            granularity_set=self._decode_granularity_set(row.get("granularity_set")),
        )

    async def list_prompt_catalog(
        self, *, prompt_id: str | None = None, role: str | None = None, status: str | None = "active"
    ) -> list[PromptCatalogEntry]:
        clauses: list[str] = []
        params: list[Any] = []
        if prompt_id is not None:
            if not _PROMPT_ID.fullmatch(prompt_id):
                raise MkbError("PROMPT_CATALOG_INVALID", "Prompt id is invalid", 422)
            clauses.append("prompt_id=?")
            params.append(prompt_id)
        if role is not None:
            if role not in _PROMPT_ROLES:
                raise MkbError("PROMPT_CATALOG_INVALID", "Prompt role is invalid", 422)
            clauses.append("role=?")
            params.append(role)
        if status is not None:
            if status not in {"active", "retired"}:
                raise MkbError("PROMPT_CATALOG_INVALID", "Prompt status is invalid", 422)
            clauses.append("status=?")
            params.append(status)
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        async with self.persistence.transaction() as tx:
            rows = await tx.fetchall(
                "SELECT prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,granularity_set "
                "FROM mkb_prompt_hash_pointers" + where + " ORDER BY prompt_id,prompt_version",
                tuple(params),
            )
        return [self._catalog_entry(row) for row in rows]

    async def resolve_prompt(self, prompt_id: str, *, version: str | None = None) -> PromptCatalogEntry:
        if not _PROMPT_ID.fullmatch(prompt_id):
            raise MkbError("PROMPT_CATALOG_INVALID", "Prompt id is invalid", 422)
        if version is not None and not _PROMPT_VERSION.fullmatch(version):
            raise MkbError("PROMPT_CATALOG_INVALID", "Prompt version is invalid", 422)
        async with self.persistence.transaction() as tx:
            if version is None:
                rows = await tx.fetchall(
                    "SELECT prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,granularity_set "
                    "FROM mkb_prompt_hash_pointers WHERE prompt_id=? AND status='active'",
                    (prompt_id,),
                )
                row = select_latest_catalog_row(rows) if rows else None
            else:
                row = await tx.fetchone(
                    "SELECT prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,granularity_set "
                    "FROM mkb_prompt_hash_pointers WHERE prompt_id=? AND prompt_version=? AND status='active'",
                    (prompt_id, version),
                )
        if row is None:
            raise MkbError("PROMPT_NOT_REGISTERED", "Prompt is not registered or active", 503)
        entry = self._catalog_entry(row)
        self._assert_prompt_bytes(entry)
        return entry

    def _assert_prompt_bytes(self, entry: PromptCatalogEntry) -> bytes:
        path = (self.prompt_root / entry.relative_path).resolve()
        try:
            path.relative_to(self.prompt_root)
            contents = path.read_bytes()
        except (OSError, ValueError) as exc:
            raise MkbError("PROMPT_HASH_MISMATCH", "Prompt bytes are unavailable", 503) from exc
        if hashlib.sha256(contents).hexdigest() != entry.content_sha256:
            raise MkbError("PROMPT_HASH_MISMATCH", "Prompt bytes do not match the registered digest", 503)
        return contents

    async def register_prompt(
        self,
        *,
        prompt_id: str,
        prompt_version: str,
        relative_path: str,
        role: str,
        granularity_set: list[int] | tuple[int, ...] | None = None,
    ) -> PromptCatalogEntry:
        prompt_id, prompt_version, relative_path, role, granularity = self._validate_catalog_input(
            prompt_id=prompt_id,
            prompt_version=prompt_version,
            relative_path=relative_path,
            role=role,
            granularity_set=granularity_set,
        )
        pointer = self._pointer(prompt_id, prompt_version, relative_path)
        async with self.persistence.transaction() as tx:
            existing = await tx.fetchone(
                "SELECT prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,granularity_set "
                "FROM mkb_prompt_hash_pointers WHERE prompt_id=? AND prompt_version=?",
                (prompt_id, prompt_version),
            )
            if existing is not None:
                entry = self._catalog_entry(existing)
                if entry.content_sha256 != pointer.content_sha256 or entry.relative_path != relative_path or entry.role != role:
                    raise MkbError("PROMPT_VERSION_EXISTS", "Prompt version already points to different bytes", 409)
                return entry
            await tx.execute(
                "UPDATE mkb_prompt_hash_pointers SET status='retired' "
                "WHERE prompt_id=? AND status='active'",
                (prompt_id,),
            )
            await tx.execute(
                "INSERT INTO mkb_prompt_hash_pointers "
                "(prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,granularity_set,registered_at,payload_extra) "
                "VALUES (?,?,?,?,?,?,?,?,?, '{}')",
                (
                    prompt_id,
                    prompt_id,
                    prompt_version,
                    relative_path,
                    pointer.content_sha256,
                    role,
                    "active",
                    None if granularity is None else json.dumps(granularity, separators=(",", ":")),
                    utc_now(),
                ),
            )
        return PromptCatalogEntry(prompt_id, prompt_id, prompt_version, relative_path, pointer.content_sha256, role, "active", granularity)

    async def retire_prompt(self, prompt_id: str, *, version: str | None = None) -> PromptCatalogEntry:
        entry = await self.resolve_prompt(prompt_id, version=version)
        async with self.persistence.transaction() as tx:
            await tx.execute(
                "UPDATE mkb_prompt_hash_pointers SET status='retired' WHERE prompt_id=? AND prompt_version=?",
                (entry.prompt_id, entry.prompt_version),
            )
        return PromptCatalogEntry(
            entry.prompt_id,
            entry.prompt_key,
            entry.prompt_version,
            entry.relative_path,
            entry.content_sha256,
            entry.role,
            "retired",
            entry.granularity_set,
        )

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
        for source_kind, capability_set in DEFAULT_SOURCE_KINDS.items():
            cardinality = capability_set["cardinality"]
            provider_manifest_digest = (
                registered_provider_manifest_digest() if source_kind == "registered_api" else None
            )
            body = {
                "source_kind": source_kind,
                "version": "v1",
                "cardinality": cardinality,
                "descriptor_schema": "mkb.intake.source-descriptor.v1",
                "preflight_profile_key": "default",
                "acquire_capabilities": list(capability_set["acquire"]),
                "decode_capabilities": list(capability_set["decode"]),
                "clean_capabilities": list(capability_set["clean"]),
                "clean_strategy_manifest_digest": clean_strategy_manifest_digest(),
                "provider_operation_manifest_digest": provider_manifest_digest,
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
                        stable_digest(list(capability_set["acquire"])),
                        stable_digest(list(capability_set["decode"])),
                        stable_digest(list(capability_set["clean"])),
                        stable_digest(
                            {
                                "source_kind": source_kind,
                                "acquire": list(capability_set["acquire"]),
                                "decode": list(capability_set["decode"]),
                                "clean": list(capability_set["clean"]),
                                "strategy_manifest": clean_strategy_manifest_digest(),
                                "provider_manifest": provider_manifest_digest,
                            }
                        ),
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
        layered_body = {
            "schema_key": "lsrag.layered_content.default",
            "version": "v1",
            "artifact": "layered_content",
        }
        layered_digest = stable_digest(layered_body)
        row = await tx.fetchone(
            "SELECT schema_digest FROM mkb_structure_schema_definitions "
            "WHERE schema_key='lsrag.layered_content.default' AND schema_version='v1'"
        )
        if row is not None and row["schema_digest"] != layered_digest:
            raise MkbError("REGISTRY_DIGEST_MISMATCH", "Layered content schema definition conflicts", 503)
        if row is None:
            await tx.execute(
                "INSERT INTO mkb_structure_schema_definitions "
                "(schema_key,schema_version,schema_digest,schema_dialect,deterministic_kernel_schema_digest,"
                "semantic_invariant_manifest_digest,artifact_type,media_contracts_digest,registration_origin,"
                "definition_body_json,registered_at,payload_extra) "
                "VALUES ('lsrag.layered_content.default','v1',?,'json',?,?, 'layered_content',?,'code_bootstrap',?,?,'{}')",
                (
                    layered_digest,
                    stable_digest({"kernel": "lsrag.layered_content.v1"}),
                    stable_digest({"invariants": "layered_content.v1"}),
                    stable_digest({"media": "application/json"}),
                    __import__("json").dumps(layered_body, sort_keys=True, separators=(",", ":")),
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
        try:
            path.relative_to(self.prompt_root)
            contents = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise MkbError("PROMPT_HASH_MISMATCH", "Prompt bytes are unavailable", 503) from exc
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
