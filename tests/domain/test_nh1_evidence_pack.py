"""NH1 foundation-pack contract before successor APs consume it."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("docs/evidence/new-harvest/AP-NH1")


def test_nh1_go_pack_has_every_required_artifact() -> None:
    required = {
        "manifest.json",
        "tests.txt",
        "stop-or-go.md",
        "queries/inventory.json",
        "queries/matrix-legal.json",
        "queries/matrix-illegal.json",
        "queries/promptA-inventory.json",
        "queries/namespace-search.json",
        "migrations/s05-spike-before-after.md",
        "security/runtime-smoke-sbom.md",
        "security/isolation-license-cve.md",
        "closure.md",
    }
    observed = {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file()}
    assert required <= observed
    assert "security/runtime-infeasible.md" not in observed
    assert "Verdict: `GO`" in (ROOT / "stop-or-go.md").read_text(encoding="utf-8")


def test_nh1_interfaces_are_versioned_and_pass_their_upgrade_gates() -> None:
    interfaces = sorted((ROOT / "interfaces").glob("*.json"))
    assert len(interfaces) == 7
    required_keys = {
        "version",
        "owner_ap",
        "consumers",
        "input",
        "output",
        "errors",
        "truth_cite",
        "spike_status",
        "upgrade_gate",
    }
    for path in interfaces:
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert set(payload) == required_keys
        assert payload["owner_ap"] == "AP-NH1"
        assert payload["spike_status"] == "pass"
        assert payload["consumers"] and payload["truth_cite"] and payload["upgrade_gate"]
        assert all({"code", "http", "when"} <= set(error) for error in payload["errors"])


def test_nh1_manifest_and_matrix_digest_are_consistent() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    frozen = json.loads(Path("tests/fixtures/new_harvest/closed_set_manifest.v1.json").read_text(encoding="utf-8"))
    legal = json.loads((ROOT / "queries/matrix-legal.json").read_text(encoding="utf-8"))
    illegal = json.loads((ROOT / "queries/matrix-illegal.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "go"
    assert manifest["matrix_digest"] == frozen["digest"] == legal["digest"] == illegal["digest"]
    assert manifest["work_ids"] == [f"NH1-{ordinal:02d}" for ordinal in range(1, 10)]
    assert manifest["test_ids"] == [f"NH1-T{ordinal:02d}" for ordinal in range(1, 8)]
