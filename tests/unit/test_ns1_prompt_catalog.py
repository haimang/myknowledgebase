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
        json_by_id = {entry.prompt_id: entry for entry in entries if entry.role == "json" and entry.status == "active"}
        assert json_by_id["promptB.json.generic"].granularity_set == (0, 1, 2)
        assert json_by_id["promptB.json.legal"].granularity_set == (0, 1)
        assert json_by_id["promptB.json.realestate"].granularity_set == (0,)
        assert json_by_id["promptB.documentation.default"].granularity_set == (0, 1, 2)
        assert json_by_id["promptB.documentation.g0"].granularity_set == (0,)
        assert json_by_id["promptB.documentation.g1"].granularity_set == (0, 1)
        assert json_by_id["promptB.documentation.g1"].prompt_version == "v2"
        assert json_by_id["promptB.documentation.g1"].relative_path.endswith("g1.v2.md")
        assert json_by_id["promptB.documentation.g2"].granularity_set == (0, 1, 2)
        assert json_by_id["promptB.documentation.g2"].prompt_version == "v2"
        assert json_by_id["promptB.json.g0"].granularity_set == (0,)
        assert json_by_id["promptB.json.g1"].granularity_set == (0, 1)
        assert json_by_id["promptB.json.g2"].granularity_set == (0, 1, 2)
        assert {entry.prompt_id for entry in entries if entry.role == "clean"} >= {
            "promptA.clean",
            "promptA.default",
            "promptA.documentation.default",
        }
        markdown_ids = {entry.prompt_id for entry in entries if entry.role == "markdown" and entry.status == "active"}
        assert markdown_ids >= {
            "promptB.markdown.legal",
            "promptB.documentation.qna",
            "promptB.documentation.eval",
            "promptB.documentation.closure",
            "promptB.documentation.plan",
            "promptB.documentation.code-review",
        }
        summarizer = {entry.prompt_id: entry for entry in entries if entry.role == "summarizer" and entry.status == "active"}
        assert summarizer["promptC.documentation.default"].prompt_version == "v2"
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
        latest = await registry.resolve_prompt("promptB.json.test")
        assert latest.prompt_version == "v2"
        active = [entry for entry in await registry.list_prompt_catalog(prompt_id="promptB.json.test") if entry.status == "active"]
        assert [entry.prompt_version for entry in active] == ["v2"]
        retired = await registry.list_prompt_catalog(prompt_id="promptB.json.test", status="retired")
        assert [entry.prompt_version for entry in retired] == ["v1"]
        tenth = prompt_root / "prompt-v10.md"
        tenth.write_text("version ten\n", encoding="utf-8")
        await registry.register_prompt(
            prompt_id="promptB.json.test",
            prompt_version="v10",
            relative_path="prompt-v10.md",
            role="json",
            granularity_set=[0, 1, 2],
        )
        assert (await registry.resolve_prompt("promptB.json.test")).prompt_version == "v10"
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


@pytest.mark.asyncio
async def test_catalog_hash_resolve_soak_is_stable(tmp_path: Path) -> None:
    persistence = SqlitePersistence(tmp_path / "catalog-soak.sqlite3", Path("src/persistence/migrations"))
    registry = RegistryService(persistence, Path("data/prompts"))
    prompt_ids = (
        "promptA.clean",
        "promptB.markdown.legal",
        "promptB.json.generic",
        "promptB.json.legal",
        "promptC.summarizer",
        "promptA.documentation.default",
        "promptB.documentation.default",
        "promptB.documentation.g1",
        "promptB.documentation.qna",
        "promptC.documentation.default",
    )
    try:
        await persistence.migrate()
        await registry.bootstrap()
        expected: dict[str, tuple[str, str]] = {}
        for prompt_id in prompt_ids:
            entry = await registry.resolve_prompt(prompt_id)
            expected[prompt_id] = (entry.prompt_version, entry.content_sha256)
        for _ in range(32):
            for prompt_id in prompt_ids:
                resolved = await registry.resolve_prompt(prompt_id)
                assert (resolved.prompt_version, resolved.content_sha256) == expected[prompt_id]
        generic = Path("data/prompts/json/promptB.json.generic.v1.md")
        original = generic.read_bytes()
        try:
            generic.write_bytes(original + b"\n# drift\n")
            with pytest.raises(MkbError) as error:
                await registry.resolve_prompt("promptB.json.generic")
            assert error.value.code == "PROMPT_HASH_MISMATCH"
        finally:
            generic.write_bytes(original)
    finally:
        await persistence.close()
