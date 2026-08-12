"""S14 bootstrap and immutable prompt/model/binding registry operations."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from src.contracts.common.errors import MkbError
from src.contracts.common.ids import stable_digest, uuid7
from src.contracts.common.time import utc_now
from src.persistence.ports import PersistencePort


@dataclass(frozen=True, slots=True)
class PromptPointer:
    prompt_key: str
    prompt_version: str
    relative_path: str
    content_sha256: str


DEFAULT_PROMPTS = (
    ("promptA.default", "v1", "prompt-a-clean-v1.md"),
    ("promptB.default", "v1", "prompt-b-structure-v1.md"),
    ("promptC.default", "v1", "prompt-c-summary-v1.md"),
)


DEFAULT_MODELS = (
    ("qwen-vl-2b", "v1", "embed", 64),
    ("qwen35-a3b", "v1", "generate", None),
    ("qwen-rerank-2b", "v1", "rerank", None),
)


DEFAULT_BINDINGS = (
    ("embed", "qwen-vl-2b", "v1", 10),
    ("structured_generate", "qwen35-a3b", "v1", 10),
    ("text_generate", "qwen35-a3b", "v1", 10),
    # Rerank is intentionally disabled by default. Retrieval reports an honest
    # ANN fallback rather than inventing a score.
    ("rerank", "qwen-rerank-2b", "v1", 10),
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
            for capability, key, version, priority in DEFAULT_BINDINGS:
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
                        "VALUES (?,?,?,?,?,?,NULL,1,?,?,?, '{}')",
                        (
                            uuid7(),
                            capability,
                            "local_vllm",
                            key,
                            version,
                            priority,
                            binding_digest,
                            utc_now(),
                            utc_now(),
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
                bindings = await tx.fetchone(
                    "SELECT COUNT(*) AS count FROM mkb_adapter_bindings WHERE enabled=1 AND adapter_kind='local_vllm'"
                )
            expected = {(item[0], item[1]) for item in DEFAULT_PROMPTS}
            if {(row["prompt_key"], row["prompt_version"]) for row in prompt_rows} < expected:
                return False
            for key, version, _ in DEFAULT_PROMPTS:
                await self.load_prompt(key, version)
            return bool(model_count and model_count["count"] >= 2 and bindings and bindings["count"] >= 2)
        except Exception:
            return False
