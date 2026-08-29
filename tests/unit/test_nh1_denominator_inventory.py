"""NH1-T01: freeze new-harvest denominators and promptA migration inputs."""

from __future__ import annotations

import hashlib
from pathlib import Path

from intake import _REGISTERED_CLEAN
from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS
from src.runtime.workflow.helpers import _compiled_workflow_digest
from src.services.registry import DEFAULT_CATALOG_PROMPTS, DEFAULT_SOURCE_KINDS
from src.workflows.builtin_lsrag import BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS
from src.workflows.builtin_scatter import BUILTIN_SCATTER_WORKFLOWS
from src.workflows.lsrag_definition import (
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    BUILTIN_SOURCE_PROFILE_WORKFLOWS,
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
)

EXPECTED_DENOMINATORS = {
    "source_kinds": 4,
    "clean_strategies": 10,
    "clean_process_capabilities": 9,
    "registered_api_operations": 3,
    "single_root_identities": 13,
    "public_selector_keys": 7,
    "unselectable_single_identities": 6,
    "scatter_identities": 2,
    "compatibility_plans": 16,
}

PROMPT_A_SOURCES = {
    "promptA.default": {
        "relative_path": "prompt-a-clean-v1.md",
        "readers": ["src/contracts/intake/strategies.py", "src/services/registry.py"],
    },
    "promptA.clean": {
        "relative_path": "clean/promptA.clean.v1.md",
        "readers": ["src/services/config_snapshots.py", "src/services/registry.py"],
    },
    "promptA.documentation.default": {
        "relative_path": "clean/promptA.documentation.default.v1.md",
        "readers": ["src/services/prompt_profiles.py", "src/services/registry.py"],
    },
}


def denominator_inventory() -> dict[str, object]:
    single = (BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, *BUILTIN_SOURCE_PROFILE_WORKFLOWS)
    public = set(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.values())
    counts = {
        "source_kinds": len(DEFAULT_SOURCE_KINDS),
        "clean_strategies": len(CLEAN_STRATEGY_DEFINITIONS),
        "clean_process_capabilities": len(_REGISTERED_CLEAN),
        "registered_api_operations": len(REGISTERED_PROVIDER_OPERATIONS),
        "single_root_identities": len(single),
        "public_selector_keys": len(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS),
        "unselectable_single_identities": sum(definition.workflow_key not in public for definition in single),
        "scatter_identities": len(BUILTIN_SCATTER_WORKFLOWS),
        "compatibility_plans": len(BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS),
    }
    compatibility = [
        {
            "workflow_key": definition.workflow_key,
            "revision_number": definition.revision_number,
            "compiled_digest": _compiled_workflow_digest(definition),
        }
        for definition in BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS
    ]
    return {"counts": counts, "compatibility": compatibility}


def prompt_a_inventory() -> dict[str, object]:
    catalog = {
        key: (version, relative_path)
        for key, version, relative_path, role, _ in DEFAULT_CATALOG_PROMPTS
        if role == "clean" and key in PROMPT_A_SOURCES
    }
    prompts = []
    for prompt_id, expected in PROMPT_A_SOURCES.items():
        version, relative_path = catalog[prompt_id]
        assert relative_path == expected["relative_path"]
        path = Path("data/prompts") / relative_path
        prompts.append(
            {
                "prompt_id": prompt_id,
                "prompt_version": version,
                "relative_path": relative_path,
                "content_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                "readers": expected["readers"],
            }
        )
    return {
        "prompts": prompts,
        "migration": "M-NH-07",
        "compatibility_law": "old snapshot prompt refs remain addressable; NH7 chooses canonical future defaults",
    }


def test_frozen_denominators_match_reference_anchor() -> None:
    inventory = denominator_inventory()
    assert inventory["counts"] == EXPECTED_DENOMINATORS


def test_compat_inventory_has_16_reviewed_plans() -> None:
    compatibility = denominator_inventory()["compatibility"]
    assert isinstance(compatibility, list)
    assert len(compatibility) == 16
    coordinates = {(row["workflow_key"], row["revision_number"]) for row in compatibility}
    assert len(coordinates) == 16
    assert all(len(str(row["compiled_digest"])) == 64 for row in compatibility)


def test_prompt_a_inventory_has_three_distinct_ids_hashes_and_readers() -> None:
    inventory = prompt_a_inventory()
    prompts = inventory["prompts"]
    assert isinstance(prompts, list)
    assert {row["prompt_id"] for row in prompts} == set(PROMPT_A_SOURCES)
    assert len({row["content_sha256"] for row in prompts}) == 3
    for row in prompts:
        assert len(row["content_sha256"]) == 64
        for reader in row["readers"]:
            assert row["prompt_id"] in Path(reader).read_text(encoding="utf-8")
