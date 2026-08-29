"""NH5 evidence pack contract consumed by NH7/NH8/NH9."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path("docs/evidence/new-harvest/AP-NH5")


def test_nh5_pack_has_every_required_artifact() -> None:
    required = {
        "manifest.json",
        "tests.txt",
        "queries/generic-contract.json",
        "queries/six-tuple-four-kinds.json",
        "queries/overlay-diff.json",
        "queries/channel-split.json",
        "queries/facet-sql.json",
        "queries/metadata-lineage.json",
        "migrations/M-NH-06-semantic-provenance.md",
        "security/semantic-redlines.md",
        "closure.md",
    }
    observed = {str(path.relative_to(ROOT)) for path in ROOT.rglob("*") if path.is_file()}
    assert observed == required


def test_nh5_manifest_covers_hard_gates_and_red_handoff() -> None:
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "executed"
    assert manifest["work_ids"] == [f"NH5-{ordinal:02d}" for ordinal in range(1, 9)]
    assert manifest["test_ids"] == [f"NH5-T{ordinal:02d}" for ordinal in range(1, 9)]
    assert manifest["hard_gate_result"] == {"passed": 39, "failed": 0, "level": "L1/L2/L3/L4"}
    assert manifest["t08_b_handoff"] == {
        "forbidden_process_count": 3,
        "target": "NH8-T03/NH8-03",
        "status": "red-handoff",
    }


def test_nh5_queries_prove_authority_facets_and_metadata_lineage() -> None:
    six = json.loads((ROOT / "queries/six-tuple-four-kinds.json").read_text(encoding="utf-8"))
    facet = json.loads((ROOT / "queries/facet-sql.json").read_text(encoding="utf-8"))
    metadata = json.loads((ROOT / "queries/metadata-lineage.json").read_text(encoding="utf-8"))
    assert all(value["distinct_keys"] == 6 for value in six["source_kinds"].values())
    assert facet["candidate_sql_uses_exists_before_limit"] is True
    assert facet["python_semantic_postfilter"] is False
    assert metadata["clean_content_digest_exact_copy"] is True
    assert metadata["clean_stored_object_uuid_exact_copy"] is True
    assert metadata["t08_b_forbidden_process_count"] == 3
