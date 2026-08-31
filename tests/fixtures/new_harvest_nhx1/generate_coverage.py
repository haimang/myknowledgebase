"""Regenerate the NHX1 denominator from the frozen action-plan tables."""

from __future__ import annotations

import hashlib
import json
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
ACTION_PLAN = ROOT / "docs/plan/new-harvest/AP-NHX1-coherent-debt-retirement-and-governance.md"
QNA = ROOT / "docs/eval/new-harvest/pre-NHX1-qna.md"
OUTPUT = Path(__file__).with_name("coverage.v1.json")
SOURCE_COMMIT = "ba099ee305577cca2281a669afbca364111f200b"


def _split_ids(value: str, pattern: str) -> list[str]:
    return re.findall(pattern, value)


def build_manifest() -> dict[str, object]:
    plan = ACTION_PLAN.read_text(encoding="utf-8")
    qna = QNA.read_text(encoding="utf-8")
    appendix = plan.split("## 附录 A", 1)[1].split("## 附录 B", 1)[0]
    rows = re.findall(r"^\| VF(\d+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", appendix, re.MULTILINE)
    classification_map = {
        "true-bug": "true_bug",
        "partial": "partial_delivery",
        "absorbed deferred": "absorbed_deferred",
        "n/a design guard": "design_guard",
        "stale-rejected guard": "stale_rejected_guard",
    }
    findings: list[dict[str, object]] = []
    for number, raw_classification, raw_owners, raw_tests, objective in rows:
        owners = _split_ids(raw_owners, r"P\d-\d{2}")
        tests = _split_ids(raw_tests, r"NHX1-T\d{2}")
        findings.append(
            {
                "vf_id": f"VF{number}",
                "classification": classification_map[raw_classification.strip()],
                "owner_work_item": owners[0],
                "supporting_work_items": owners[1:],
                "primary_test_id": tests[0],
                "supporting_test_ids": tests[1:],
                "execution_objective": objective.strip(),
            }
        )

    deferred_section = plan.split("## 附录 B", 1)[1].split("## 附录 C", 1)[0]
    deferred_rows = re.findall(r"^\| ([^|]+) \| ([^|]+) \| ([^|]+) \| ([^|]+) \|$", deferred_section, re.MULTILINE)
    deferred = [
        {
            "historical_id": historical_id.strip(" `"),
            "owner_work_items": _split_ids(owner, r"P\d-\d{2}"),
            "test_ids": _split_ids(test_ids, r"NHX1-T\d{2}"),
            "disposition": disposition.strip(),
        }
        for historical_id, owner, test_ids, disposition in deferred_rows
        if historical_id.strip() not in {"历史ID / 集合", "----------------"}
    ]
    truth_ids = [f"T-O-{value}" for value in range(408, 423)]
    assert all(f"`{truth_id}`" in qna for truth_id in truth_ids)
    payload: dict[str, object] = {
        "schema_version": "mkb.nhx1-coverage.v1",
        "source_commit": SOURCE_COMMIT,
        "action_plan": ACTION_PLAN.relative_to(ROOT).as_posix(),
        "truth_source": QNA.relative_to(ROOT).as_posix(),
        "truth_ids": truth_ids,
        "classification_counts": dict(sorted(Counter(row["classification"] for row in findings).items())),
        "findings": findings,
        "historical_deferred": deferred,
    }
    canonical = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    payload["coverage_digest"] = hashlib.sha256(canonical).hexdigest()
    return payload


if __name__ == "__main__":
    OUTPUT.write_text(json.dumps(build_manifest(), ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
