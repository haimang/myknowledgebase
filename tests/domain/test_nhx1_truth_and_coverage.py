"""NHX1-T01: frozen denominator and semantic owner coverage."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from tests.fixtures.new_harvest_nhx1.generate_coverage import build_manifest

ROOT = Path(__file__).resolve().parents[2]
FIXTURE = ROOT / "tests/fixtures/new_harvest_nhx1/coverage.v1.json"
PLAN = ROOT / "docs/plan/new-harvest/AP-NHX1-coherent-debt-retirement-and-governance.md"
QNA = ROOT / "docs/eval/new-harvest/pre-NHX1-qna.md"
LEDGER = ROOT / "docs/code-review/new-harvest/NH1-NH9-2nd-pass-review-VF-ledger.md"


def _manifest() -> dict[str, object]:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def test_all_vf_and_deferred_have_one_owner() -> None:
    manifest = _manifest()
    findings = manifest["findings"]
    assert isinstance(findings, list)
    assert [row["vf_id"] for row in findings] == [f"VF{number}" for number in range(1, 53)]
    assert len({row["vf_id"] for row in findings}) == 52
    assert all(re.fullmatch(r"P\d-\d{2}", row["owner_work_item"]) for row in findings)
    assert all(re.fullmatch(r"NHX1-T\d{2}", row["primary_test_id"]) for row in findings)
    counts = Counter(row["classification"] for row in findings)
    assert counts == {
        "true_bug": 15,
        "partial_delivery": 18,
        "absorbed_deferred": 17,
        "design_guard": 1,
        "stale_rejected_guard": 1,
    }
    ledger = LEDGER.read_text(encoding="utf-8")
    assert all(re.search(rf"^\| VF{number} \|", ledger, re.MULTILINE) for number in range(1, 53))
    deferred = manifest["historical_deferred"]
    assert isinstance(deferred, list) and deferred
    assert all(row["owner_work_items"] and row["test_ids"] for row in deferred if row["historical_id"] != "experiment")


def test_truth_ids_frozen_and_unique() -> None:
    manifest = _manifest()
    truth_ids = manifest["truth_ids"]
    assert truth_ids == [f"T-O-{number}" for number in range(408, 423)]
    qna = QNA.read_text(encoding="utf-8")
    for truth_id in truth_ids:
        assert len(re.findall(rf"^\| `{truth_id}` \|", qna, re.MULTILINE)) == 1
    assert "文档状态**：`frozen`" in qna


def test_each_work_item_has_test_and_fixture_is_reproducible() -> None:
    manifest = _manifest()
    plan = PLAN.read_text(encoding="utf-8")
    work_items = set(re.findall(r"\bP[1-9]-\d{2}\b", plan.split("## 3. 业务工作总表", 1)[1]))
    test_ids = set(re.findall(r"\bNHX1-T\d{2}\b", plan))
    for row in manifest["findings"]:
        assert row["owner_work_item"] in work_items
        assert row["primary_test_id"] in test_ids
        assert set(row["supporting_work_items"]) <= work_items
        assert set(row["supporting_test_ids"]) <= test_ids
    assert build_manifest() == manifest
    payload = dict(manifest)
    digest = payload.pop("coverage_digest")
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    assert hashlib.sha256(canonical).hexdigest() == digest
