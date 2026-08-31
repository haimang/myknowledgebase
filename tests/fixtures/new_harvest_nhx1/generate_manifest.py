"""Derive the NHX1 closed set from code-owned registries (never hand-shrink it)."""

from __future__ import annotations

import json
from pathlib import Path

from src.contracts.common.ids import stable_digest
from src.runtime.roles import DeploymentRole
from src.runtime.workflow.capability_registry import DEFAULT_PROCESS_CAPABILITY_REGISTRY
from src.services.intake_lifecycle.admission_matrix import INTAKE_INTENT_APPLICABILITY, LIFECYCLE_STATES
from src.workflows.builtin_lsrag import BUILTIN_WORKFLOWS
from src.workflows.builtin_scatter import BUILTIN_SCATTER_WORKFLOWS

ROOT = Path(__file__).resolve().parents[3]
OUTPUT = Path(__file__).with_name("manifest.v1.json")


def build_manifest() -> dict[str, object]:
    workflows = (*BUILTIN_WORKFLOWS, *BUILTIN_SCATTER_WORKFLOWS)
    edge_cells: list[dict[str, object]] = []
    for workflow in sorted(workflows, key=lambda item: (item.workflow_key, item.revision_number)):
        steps = {step.step_key for step in workflow.steps}
        for route in sorted(workflow.routes, key=lambda item: item.route_key):
            edge_cells.append(
                {
                    "cell_id": f"{workflow.workflow_key}:r{workflow.revision_number}:{route.route_key}",
                    "workflow_key": workflow.workflow_key,
                    "revision_number": workflow.revision_number,
                    "from_step": route.from_step_key,
                    "to_step": route.to_step_key,
                    "route_kind": route.route_kind.value,
                    "outcome_selector": route.outcome_selector.value,
                    "declared": route.from_step_key in steps and route.to_step_key in steps,
                    "minimum_layer": "L3",
                    "test_id": "NHX1-T27",
                }
            )
    process_cells = [
        {
            "process_key": item.process_key,
            "contract_version": item.contract_version,
            "definition_digest": item.definition_digest,
            "deployment_roles": list(item.deployment_roles),
            "supply_requirements": list(item.supply_requirements),
            "minimum_layer": "L4",
            "test_id": "NHX1-T27",
        }
        for item in DEFAULT_PROCESS_CAPABILITY_REGISTRY.manifests
    ]
    intent_cells = [
        {
            "intent": intent,
            "lifecycle_state": lifecycle,
            "allowed": lifecycle in INTAKE_INTENT_APPLICABILITY[intent],
            "minimum_layer": "L2",
            "test_id": "NHX1-T27",
        }
        for intent in sorted(INTAKE_INTENT_APPLICABILITY)
        for lifecycle in LIFECYCLE_STATES
    ]
    payload: dict[str, object] = {
        "schema_version": "mkb.nhx1-closed-set.v1",
        "source": {
            "workflow_registry": "src/workflows/builtin_lsrag.py",
            "scatter_registry": "src/workflows/builtin_scatter.py",
            "capability_registry": "src/runtime/workflow/capability_registry.py",
            "intent_registry": "src/services/intake_lifecycle/admission_matrix.py",
        },
        "role_set": [role.value for role in DeploymentRole],
        "workflows": [
            {"workflow_key": item.workflow_key, "revision_number": item.revision_number}
            for item in sorted(workflows, key=lambda item: (item.workflow_key, item.revision_number))
        ],
        "edge_cells": edge_cells,
        "process_cells": process_cells,
        "intent_cells": intent_cells,
    }
    payload["manifest_digest"] = stable_digest(payload)
    return payload


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build_manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
