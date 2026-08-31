"""NHX1-T30: assurance evidence joins every Test-ID and owner gate honestly."""

from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
EVIDENCE = ROOT / "docs/evidence/new-harvest/AP-NHX1"


def test_all_thirty_test_ids_have_execution_records() -> None:
    tests_text = (EVIDENCE / "tests.txt").read_text(encoding="utf-8")
    manifest = json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))
    expected = {f"NHX1-T{number:02d}" for number in range(1, 31)}
    assert set(manifest["test_ids"]) == expected
    assert all(test_id in tests_text for test_id in expected)


def test_closed_set_has_no_unexplained_cells_or_owner_gate_claim() -> None:
    closed = json.loads((ROOT / "tests/fixtures/new_harvest_nhx1/manifest.v1.json").read_text(encoding="utf-8"))
    for key in ("edge_cells", "process_cells", "intent_cells"):
        assert closed[key]
        assert all(cell["test_id"] == "NHX1-T27" for cell in closed[key])
    evidence = json.loads((EVIDENCE / "manifest.json").read_text(encoding="utf-8"))
    assert evidence["phase_sequence"][5]["status"] == "ready_for_owner_gate"
    assert evidence["phase_sequence"][-1]["status"] in {"in_progress", "blocked_by_phase_8_and_t22_o"}
