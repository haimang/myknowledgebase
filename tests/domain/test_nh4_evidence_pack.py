"""NH4 evidence pack contract consumed by NH7 and NH9."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("docs/evidence/new-harvest/AP-NH4")


def test_nh4_pack_has_every_required_artifact() -> None:
    required = {
        "manifest.json",
        "tests.txt",
        "queries/public-upload.json",
        "queries/upload-ingest-handoff.json",
        "queries/gc-lifecycle.json",
        "migrations/M-NH-05-upload-pending.md",
        "security/upload-negative-matrix.md",
        "closure.md",
    }
    observed = {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file()}
    assert observed == required


def test_nh4_manifest_covers_frozen_work_and_tests() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "executed"
    assert manifest["work_ids"] == [f"NH4-{ordinal:02d}" for ordinal in range(1, 9)]
    assert manifest["test_ids"] == [f"NH4-T{ordinal:02d}" for ordinal in range(1, 8)]
    assert manifest["public_raw_object_routes"] == 0
    assert manifest["frozen_and_regression_result"] == {
        "passed": 42,
        "failed": 0,
        "level": "L1/L2/L3/L4/F/R",
    }


def test_nh4_queries_prove_identity_handoff_and_gc() -> None:
    public = json.loads((ROOT / "queries/public-upload.json").read_text(encoding="utf-8"))
    handoff = json.loads((ROOT / "queries/upload-ingest-handoff.json").read_text(encoding="utf-8"))
    gc = json.loads((ROOT / "queries/gc-lifecycle.json").read_text(encoding="utf-8"))
    assert public["intake_counts_after_upload"] == {"sources": 0, "items": 0, "revisions": 0}
    assert public["pending"]["released_at"] is None
    assert handoff["search_before_ingest_contains_sentinel"] is False
    assert handoff["search_after_ingest_contains_sentinel"] is True
    assert handoff["upload_pending"]["released_at_nonnull"] is True
    assert gc["pending_before_ttl_is_gc_candidate"] is False
    assert gc["pending_release_starts_grace"] is True
    assert gc["delete_proof_count"] == 1
