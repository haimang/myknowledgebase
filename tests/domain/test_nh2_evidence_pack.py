"""NH2 evidence pack contract consumed by NH3/NH7/NH8."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("docs/evidence/new-harvest/AP-NH2")


def test_nh2_pack_has_frozen_files() -> None:
    required = {
        "manifest.json",
        "tests.txt",
        "queries/resolver-kind-only.json",
        "queries/compiled-tail-digest.json",
        "queries/old-pin-process-sequence.json",
        "security/redline-scan.txt",
        "migrations/M-NH-03-control.md",
        "migrations/M-NH-04-kind-compat.md",
        "closure.md",
    }
    observed = {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file()}
    assert required == observed


def test_nh2_manifest_covers_all_frozen_ids() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "executed"
    assert manifest["work_ids"] == [f"NH2-{ordinal:02d}" for ordinal in range(1, 9)]
    assert manifest["test_ids"] == [f"NH2-T{ordinal:02d}" for ordinal in range(1, 8)]
    assert manifest["kind_graph_count"] == 3
    assert manifest["legacy_compat_plan_count"] == 16


def test_nh2_tail_and_resolver_evidence_agree() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    tail = json.loads((ROOT / "queries/compiled-tail-digest.json").read_text(encoding="utf-8"))
    resolver = json.loads((ROOT / "queries/resolver-kind-only.json").read_text(encoding="utf-8"))
    assert manifest["shared_tail_digest"] == tail["shared_tail_digest"]
    assert tail["tail_digest_cardinality"] == 1
    assert tail["join_steps"] == 0
    assert len(resolver["source_kind_workflow_keys"]) == 4
    assert resolver["mode_media_change_workflow_key"] is False
