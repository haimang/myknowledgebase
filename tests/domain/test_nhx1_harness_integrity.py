"""NHX1-T03: adapter-aware inspection and known-RED honesty guards."""

from __future__ import annotations

import ast
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RED_LEDGER = ROOT / "tests/fixtures/new_harvest_nhx1/known-red.v1.json"


def test_e2e_does_not_open_adapter_paths_with_sqlite() -> None:
    violations: list[str] = []
    for path in sorted((ROOT / "tests/e2e").glob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        aliases: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                aliases.update(alias.asname or alias.name for alias in node.names if alias.name == "sqlite3")
            if isinstance(node, ast.ImportFrom) and node.module == "sqlite3":
                aliases.update(alias.asname or alias.name for alias in node.names)
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id in aliases and node.func.attr == "connect":
                    violations.append(f"{path.relative_to(ROOT)}:{node.lineno}")
    assert violations == []


def test_known_red_keeps_original_assertion_and_no_degraded_marker() -> None:
    record = json.loads(RED_LEDGER.read_text(encoding="utf-8"))
    assert record["node_id"].endswith("test_stale_fencing_fail_does_not_kill_new_generation")
    assert record["source_commit"] == "ba099ee305577cca2281a669afbca364111f200b"
    assert record["expected_exception"] == "src.contracts.common.errors.ConflictError"
    assert record["failure_signature"] == "stale-process-fence"
    source = (ROOT / "tests/unit/test_ns6_phase2.py").read_text(encoding="utf-8")
    node_source = source.split("async def test_stale_fencing_fail_does_not_kill_new_generation", 1)[1].split(
        "async def test_cancel_prevents_succeeded_task", 1
    )[0]
    assert "assert current[\"status\"] == \"running\"" in node_source
    assert "pytest.mark.xfail" not in node_source
    assert "pytest.mark.skip" not in node_source
