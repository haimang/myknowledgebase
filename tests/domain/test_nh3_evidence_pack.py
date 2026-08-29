"""NH3 evidence pack contract consumed by NH6/NH7/NH8/NH9."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("docs/evidence/new-harvest/AP-NH3")


def test_nh3_pack_has_every_required_artifact() -> None:
    required = {
        "manifest.json",
        "tests.txt",
        "queries/representation-path.json",
        "queries/actual-propagation.json",
        "migrations/M-NH-01-actual-s05.md",
        "migrations/M-NH-02-representation-history.md",
        "security/redline-scan.txt",
        "closure.md",
    }
    observed = {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file()}
    assert observed == required


def test_nh3_manifest_covers_frozen_work_and_tests() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "executed"
    assert manifest["work_ids"] == [f"NH3-{ordinal:02d}" for ordinal in range(1, 11)]
    assert manifest["test_ids"] == [f"NH3-T{ordinal:02d}" for ordinal in range(1, 9)]
    assert manifest["frozen_test_result"] == {"passed": 36, "failed": 0, "level": "L1/L2/F"}
    assert manifest["repository_diagnostic"] == {
        "collected": 678,
        "passed": 672,
        "successor_owned_failed": 6,
    }


def test_nh3_path_and_actual_evidence_close_the_expected_invariants() -> None:
    path = json.loads((ROOT / "queries/representation-path.json").read_text(encoding="utf-8"))
    actual = json.loads((ROOT / "queries/actual-propagation.json").read_text(encoding="utf-8"))
    assert path["same_path_stable"] is True
    assert path["different_path_distinct"] is True
    assert path["static_browser_path_digest"] == path["same_path_replay_digest"]
    assert path["static_browser_path_digest"] != path["different_browser_bytes_path_digest"]
    assert actual["all_projection_digests_equal_root"] is True
    assert actual["root_actual_differs_from_domain_policy"] is True
    assert actual["root"]["actual_binding_state"] == "sealed"
    assert actual["root"]["seal_generation"] == 1
