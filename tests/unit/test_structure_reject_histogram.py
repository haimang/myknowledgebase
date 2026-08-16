"""R3-EVD-01: rejected B candidates leave a redacted layer histogram."""

from __future__ import annotations

from src.contracts.common.errors import MkbError
from src.runtime.intake.core import IntakeCoreMixin
from src.runtime.intake.generation_construct import layered_reject_histogram


def test_histogram_counts_layers_and_never_copies_original_text() -> None:
    secret = "THIS-MUST-NOT-LEAK-INTO-EXTRA"
    candidate = {
        "layered_content": [
            {"block_id": 0, "granularity": 0, "original_content": {"title": secret, "body": secret}},
            {"block_id": 1, "granularity": 1, "original_content": {"title": secret, "body": secret}},
            {"block_id": 2, "granularity": 2, "original_content": {"title": secret, "body": secret}},
            {"block_id": 3, "granularity": 2, "original_content": {"title": secret, "body": secret}},
        ]
    }
    histogram = layered_reject_histogram(candidate, (0, 1))
    encoded = str(histogram)
    assert secret not in encoded
    assert histogram["schema"] == "mkb.structure-reject.v1"
    assert histogram["set"] == [0, 1, 2]
    assert histogram["counts"] == {"0": 1, "1": 1, "2": 2}
    assert histogram["has_g0"] is True
    assert histogram["block_count"] == 4
    assert histogram["profile"] == [0, 1]


def test_outcome_extra_no_longer_copies_reject_keys() -> None:
    extra = IntakeCoreMixin._safe_outcome_extra(
        MkbError(
            "STRUCTURE_GRANULARITY_SET_MISMATCH",
            "Candidate granularity set does not match the frozen profile",
            422,
            {
                "structure_reject": {
                    "schema": "mkb.structure-reject.v1",
                    "set": [0, 1, 2],
                    "counts": {"0": 1, "2": 4},
                    "has_g0": True,
                    "block_count": 5,
                    "invalid_granularity_count": 0,
                    "profile": [0, 1],
                },
                "prompt": "forbidden",
                "content": "forbidden",
            },
        )
    )
    assert extra == {}
    assert "structure_reject" not in extra
    assert "prompt" not in extra
    assert "content" not in extra
