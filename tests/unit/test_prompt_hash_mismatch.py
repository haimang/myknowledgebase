"""D07-E2E-14 / S14-A01: prompt file drift fails closed with PROMPT_HASH_MISMATCH.

Drives the shipped RegistryService.load_prompt and readiness path after the
pointer is frozen by bootstrap; does not re-implement the hash check.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.persistence.sqlite_port import SqlitePersistence
from src.services.registry import RegistryService


@pytest.mark.asyncio
async def test_prompt_byte_drift_after_bootstrap_is_prompt_hash_mismatch(tmp_path: Path) -> None:
    source_prompts = Path(__file__).resolve().parents[2] / "data" / "prompts"
    prompt_root = tmp_path / "prompts"
    shutil.copytree(source_prompts, prompt_root)
    db = tmp_path / "prompt.sqlite3"
    persistence = SqlitePersistence(db, Path("src/persistence/migrations"))
    registry = RegistryService(persistence, prompt_root)
    try:
        await persistence.migrate()
        await registry.bootstrap()
        body, digest = await registry.load_prompt("promptB.default", "v1")
        assert body
        assert len(digest) == 64
        assert await registry.readiness() is True

        target = prompt_root / "prompt-b-structure-v1.md"
        original = target.read_text(encoding="utf-8")
        target.write_text(original + "\n# drifted without pointer update\n", encoding="utf-8")

        with pytest.raises(MkbError) as exc_info:
            await registry.load_prompt("promptB.default", "v1")
        assert exc_info.value.code == "PROMPT_HASH_MISMATCH"
        assert await registry.readiness() is False
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_live_generation_config_fails_on_prompt_hash_mismatch(tmp_path: Path) -> None:
    """IntakePipeline frozen L4 prompt check uses the same fail-closed code."""

    import json

    from src.contracts.common.ids import stable_digest, uuid7
    from src.contracts.runtime.models import ProcessCommand
    from src.contracts.storage.models import ObjectHandle, PromoteRequest
    from src.persistence.sqlite_port import SqlitePersistence
    from src.runtime.intake_pipeline import IntakePipeline
    from src.services.artifacts import OutcomeArtifactCommitter
    from src.services.registry import RegistryService
    from src.services.workflow_registry import WorkflowRegistryService
    from src.storage.local_store import LocalObjectStore
    from src.workflows.builtin_lsrag import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW

    source_prompts = Path(__file__).resolve().parents[2] / "data" / "prompts"
    prompt_root = tmp_path / "prompts"
    shutil.copytree(source_prompts, prompt_root)
    persistence = SqlitePersistence(tmp_path / "live.sqlite3", Path("src/persistence/migrations"))
    storage = LocalObjectStore(tmp_path / "objects")
    registry = RegistryService(persistence, prompt_root)
    workflows = WorkflowRegistryService(persistence)
    try:
        await persistence.migrate()
        await registry.bootstrap()
        await workflows.bootstrap()
        await workflows.register(BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW)

        # Build a minimal L4 snapshot with live mode + real prompt pointer digests.
        async with persistence.transaction() as tx:
            prompts = await tx.fetchall(
                "SELECT prompt_key,prompt_version,git_relative_path,content_sha256 FROM mkb_prompt_hash_pointers"
            )
            models = await tx.fetchall(
                "SELECT model_key,model_version,modality,default_dimension,definition_digest FROM mkb_model_catalog "
                "WHERE status='active'"
            )
            bindings = await tx.fetchall(
                "SELECT capability_key,adapter_kind,model_key,model_version,priority,binding_digest,team_uuid "
                "FROM mkb_adapter_bindings WHERE enabled=1"
            )
        selected = {}
        for capability in ("embed", "structured_generate", "text_generate"):
            row = next(r for r in bindings if r["capability_key"] == capability and r["team_uuid"] is None)
            selected[capability] = {
                "adapter_kind": row["adapter_kind"],
                "model_key": row["model_key"],
                "model_version": row["model_version"],
                "binding_digest": row["binding_digest"],
            }
        materials = {
            "schema_version": "mkb.config-snapshot.v1",
            "l0": {},
            "l1": {"prompts": prompts, "models": models, "bindings": selected},
            "l2": {"inference_mode": "live", "inference_vllm_base_url": "http://127.0.0.1:668"},
            "l3": {"overrides": {}, "override_digest": None},
            "flag_bundle": {},
            "flag_bundle_digest": "0" * 64,
            "semantic_knobs": {},
            "workflow": {"workflow_key": "x", "compiled_digest": "1" * 64},
        }
        team = uuid7()
        snapshot = await storage.promote(
            json.dumps(materials, sort_keys=True, separators=(",", ":")).encode(),
            PromoteRequest(team_uuid=team, purpose="process_io", media_type="application/json"),
        )
        # Drift the prompt file after the pointer was frozen into L4.
        (prompt_root / "prompt-b-structure-v1.md").write_text("tampered prompt bytes\n", encoding="utf-8")

        pipeline = IntakePipeline(
            persistence,
            storage,
            OutcomeArtifactCommitter(storage),
            live_inference=True,
            prompt_root=prompt_root,
        )
        command = ProcessCommand(
            schema_version="mkb.process-command.v1",
            team_uuid=team,
            task_uuid=uuid7(),
            trace_uuid=uuid7(),
            execution_uuid=uuid7(),
            process_uuid=uuid7(),
            process_key="lsrag.structurize",
            process_contract_version="v1",
            fencing_generation=1,
            command_input_digest=stable_digest({"x": 1}),
            input_manifest_ref="mkbobj:v1:unused",
            input_manifest_digest="a" * 64,
            config_snapshot_ref=snapshot.handle.value,
            config_snapshot_digest=snapshot.sha256,
            binding_digest="b" * 64,
        )
        with pytest.raises(MkbError) as exc_info:
            await pipeline._resolve_frozen_generation_config(
                command,
                capability_key="structured_generate",
                prompt_key="promptB.default",
                prompt_version="v1",
                schema_key="lsrag.structure.default",
                schema_version="v1",
            )
        assert exc_info.value.code == "PROMPT_HASH_MISMATCH"
        # The object handle is only used for identity; keep the import used.
        assert isinstance(ObjectHandle(value=snapshot.handle.value).value, str)
    finally:
        await persistence.close()
