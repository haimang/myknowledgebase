"""NS1-T02..T07/T46: four-role prompt catalog and hash gate."""

from __future__ import annotations

from pathlib import Path

import pytest

from src.contracts.common.errors import MkbError
from src.persistence.sqlite_port import SqlitePersistence
from src.services.registry import RegistryService


@pytest.mark.asyncio
async def test_bootstrap_registers_four_roles_and_json_closed_sets(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "catalog.sqlite3", Path("src/persistence/migrations"))
    registry = RegistryService(persistence, Path("data/prompts"))
    try:
        await persistence.migrate()
        await registry.bootstrap()
        entries = await registry.list_prompt_catalog()
        assert {entry.role for entry in entries} == {"clean", "markdown", "json", "summarizer"}
        json_entries = [entry for entry in entries if entry.role == "json"]
        assert json_entries
        assert all(entry.granularity_set for entry in json_entries)
        assert all(entry.content_sha256 and len(entry.content_sha256) == 64 for entry in entries)
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_catalog_update_is_new_version_and_path_attacks_fail_closed(tmp_path: Path) -> None:
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    prompt_file = prompt_root / "prompt.md"
    prompt_file.write_text("version one\n", encoding="utf-8")
    new_file = prompt_root / "prompt-v2.md"
    new_file.write_text("version two\n", encoding="utf-8")
    persistence = SqlitePersistence(tmp_path / "catalog.sqlite3", Path("src/persistence/migrations"))
    registry = RegistryService(persistence, prompt_root)
    try:
        await persistence.migrate()
        created = await registry.register_prompt(
            prompt_id="promptB.json.test",
            prompt_version="v1",
            relative_path="prompt.md",
            role="json",
            granularity_set=[0, 1, 2],
        )
        updated = await registry.register_prompt(
            prompt_id="promptB.json.test",
            prompt_version="v2",
            relative_path="prompt-v2.md",
            role="json",
            granularity_set=[0, 1, 2],
        )
        assert created.content_sha256 != updated.content_sha256
        assert (await registry.resolve_prompt("promptB.json.test")).prompt_version == "v2"
        with pytest.raises(MkbError, match="PROMPT_CATALOG_PATH_INVALID"):
            await registry.register_prompt(
                prompt_id="promptB.json.bad",
                prompt_version="v1",
                relative_path="../escape.md",
                role="json",
                granularity_set=[0, 1, 2],
            )
        with pytest.raises(MkbError, match="PROMPT_CATALOG_GRANULARITY_INVALID"):
            await registry.register_prompt(
                prompt_id="promptB.json.bad",
                prompt_version="v1",
                relative_path="prompt.md",
                role="json",
                granularity_set=None,
            )
    finally:
        await persistence.close()


@pytest.mark.asyncio
async def test_catalog_hash_drift_is_fail_closed_and_retire_keeps_history(tmp_path: Path) -> None:
    prompt_root = tmp_path / "prompts"
    prompt_root.mkdir()
    prompt_file = prompt_root / "prompt.md"
    prompt_file.write_text("immutable bytes\n", encoding="utf-8")
    persistence = SqlitePersistence(tmp_path / "catalog.sqlite3", Path("src/persistence/migrations"))
    registry = RegistryService(persistence, prompt_root)
    try:
        await persistence.migrate()
        await registry.register_prompt(
            prompt_id="promptA.test",
            prompt_version="v1",
            relative_path="prompt.md",
            role="clean",
        )
        prompt_file.write_text("tampered bytes\n", encoding="utf-8")
        with pytest.raises(MkbError) as error:
            await registry.resolve_prompt("promptA.test")
        assert error.value.code == "PROMPT_HASH_MISMATCH"
        prompt_file.write_text("immutable bytes\n", encoding="utf-8")
        retired = await registry.retire_prompt("promptA.test")
        assert retired.status == "retired"
        assert await registry.list_prompt_catalog(status="retired")
        with pytest.raises(MkbError, match="PROMPT_NOT_REGISTERED"):
            await registry.resolve_prompt("promptA.test")
    finally:
        await persistence.close()
