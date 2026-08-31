"""NHX1-T27: compiler/registry-derived closed-set manifest is complete."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from src.contracts.common.ids import stable_digest
from src.runtime.workflow.capability_registry import DEFAULT_PROCESS_CAPABILITY_REGISTRY
from src.services.intake_lifecycle.admission_matrix import INTAKE_INTENT_APPLICABILITY, LIFECYCLE_STATES
from src.workflows.builtin_lsrag import BUILTIN_WORKFLOWS
from src.workflows.builtin_scatter import BUILTIN_SCATTER_WORKFLOWS

ROOT = Path(__file__).resolve().parents[2]
MANIFEST = ROOT / "tests/fixtures/new_harvest_nhx1/manifest.v1.json"
GENERATOR = ROOT / "tests/fixtures/new_harvest_nhx1/generate_manifest.py"


def _load() -> dict[str, object]:
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def test_generated_closed_set_is_byte_stable_and_registry_derived() -> None:
    before = MANIFEST.read_bytes()
    completed = subprocess.run((sys.executable, str(GENERATOR)), cwd=ROOT, capture_output=True, check=False)
    assert completed.returncode == 0, completed.stderr.decode()
    assert MANIFEST.read_bytes() == before
    payload = _load()
    assert payload["manifest_digest"] == stable_digest({key: value for key, value in payload.items() if key != "manifest_digest"})

    workflows = (*BUILTIN_WORKFLOWS, *BUILTIN_SCATTER_WORKFLOWS)
    expected_edges = sum(len(workflow.routes) for workflow in workflows)
    edge_cells = payload["edge_cells"]
    process_cells = payload["process_cells"]
    intent_cells = payload["intent_cells"]
    assert isinstance(edge_cells, list) and len(edge_cells) == expected_edges
    assert isinstance(process_cells, list)
    assert {item["process_key"] for item in process_cells} == {
        item.process_key for item in DEFAULT_PROCESS_CAPABILITY_REGISTRY.manifests
    }
    assert isinstance(intent_cells, list) and len(intent_cells) == len(INTAKE_INTENT_APPLICABILITY) * len(LIFECYCLE_STATES)
    assert {item["test_id"] for item in edge_cells + process_cells + intent_cells} == {"NHX1-T27"}


def test_closed_set_contains_positive_and_negative_intent_cells() -> None:
    payload = _load()
    cells = payload["intent_cells"]
    assert any(item["allowed"] for item in cells)
    assert any(not item["allowed"] for item in cells)
    assert {item["minimum_layer"] for item in cells} == {"L2"}
