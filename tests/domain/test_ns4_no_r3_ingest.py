"""NS4-T31: this campaign must not launch R3 collect --suffix -r3."""

from __future__ import annotations

from pathlib import Path

RESULTS = Path(".experiment/0815/runs/MKB-0815-R2/results/runs.jsonl")


def test_no_r3_suffix_rows_in_live_jsonl() -> None:
    if not RESULTS.is_file():
        return
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        assert "-r3" not in line
        assert "suffix=-r3" not in line
