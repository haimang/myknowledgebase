"""NS4-T31 closed: R3 live is owner-gated. After launch, only frozen cells may carry -r3."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

RESULTS = Path(".experiment/0815/runs/MKB-0815-R2/results/runs.jsonl")
FROZEN = {"N-A5", "N-A3", "N-A6", "N-A2", "Q-A5"}


def test_r3_jsonl_rows_stay_on_frozen_cells() -> None:
    if not RESULTS.is_file():
        pytest.fail(f"missing experiment journal {RESULTS}")
    for line in RESULTS.read_text(encoding="utf-8").splitlines():
        if not line.strip() or "-r3" not in line:
            continue
        row = json.loads(line)
        cell = row.get("cell_id")
        assert cell in FROZEN, cell
        assert cell not in {"N-A1", "N-A4", "N-A5g2", "Q-A5g2", "Q-A3"}
