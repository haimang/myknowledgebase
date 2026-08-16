"""NS4-T27: attack vectors against the evidence plane must fail closed."""

from __future__ import annotations

import pytest

from src.contracts.observability.stage_report import StageReportValidationError, validate_stage_report
from src.runtime.intake.generation_construct import layered_reject_histogram


def test_histogram_never_copies_original_text() -> None:
    secret = "ATTACK-PROMPT-BODY-MUST-NOT-LEAK"
    histogram = layered_reject_histogram(
        {
            "layered_content": [
                {"block_id": 0, "granularity": 0, "original_content": {"title": secret, "body": secret}},
            ]
        },
        (0, 1),
    )
    encoded = str(histogram)
    assert secret not in encoded
    assert histogram["has_g0"] is True


def test_stage_report_rejects_prompt_stdout_original_paths() -> None:
    base = {
        "stage_key": "structurize",
        "disposition": "rejected",
        "error_code": "STRUCTURE_ANCHOR_MISSING",
        "latency_ms": 1,
    }
    for attack in (
        {**base, "prompt": "system you are"},
        {**base, "stdout": "model dumped text"},
        {**base, "original": "clean text"},
        {**base, "layer_counts": {"0": 1, "body": "x"}},
    ):
        with pytest.raises(StageReportValidationError):
            validate_stage_report(attack)
