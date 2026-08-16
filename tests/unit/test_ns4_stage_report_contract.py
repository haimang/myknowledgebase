"""NS4-T03 / T20 / T27: stage-report contract rejects bodies and accepts counts."""

from __future__ import annotations

import pytest

from src.contracts.observability.stage_report import (
    STAGE_REPORT_SCHEMA,
    StageReportValidationError,
    evidence_stage_key,
    validate_layer_counts,
    validate_stage_report,
)


def _valid_report(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "schema": STAGE_REPORT_SCHEMA,
        "stage_key": "structurize",
        "disposition": "rejected",
        "error_code": "STRUCTURE_GRANULARITY_SET_MISMATCH",
        "has_g0": True,
        "block_count": 3,
        "granularity_set": "0,1,2",
        "layer_counts": {"0": 1, "1": 1, "2": 1},
        "latency_ms": 12,
    }
    payload.update(overrides)
    return payload


def test_valid_report_projects_digest_and_counts() -> None:
    projected = validate_stage_report(_valid_report())
    assert projected["schema"] == STAGE_REPORT_SCHEMA
    assert projected["layer_counts"] == {"0": 1, "1": 1, "2": 1}
    assert isinstance(projected["schema_digest"], str)
    assert len(projected["schema_digest"]) == 64


def test_layer_counts_reject_non_granularity_keys() -> None:
    with pytest.raises(StageReportValidationError):
        validate_layer_counts({"title": 1})


def test_report_rejects_original_body_key() -> None:
    with pytest.raises(StageReportValidationError):
        validate_stage_report(_valid_report(original="THIS-MUST-NOT-LEAK"))


def test_report_rejects_nested_prompt() -> None:
    with pytest.raises(StageReportValidationError):
        validate_stage_report(_valid_report(layer_counts={"0": 1, "prompt": "secret"}))


def test_report_rejects_stdout_and_content_aliases() -> None:
    for forbidden in ({"stdout": "x"}, {"content": "x"}, {"original_content": {"body": "x"}}):
        with pytest.raises(StageReportValidationError):
            validate_stage_report(_valid_report(**forbidden))


def test_rejected_disposition_requires_error_code() -> None:
    with pytest.raises(StageReportValidationError):
        validate_stage_report(_valid_report(error_code=None))


def test_unknown_stage_key_is_rejected() -> None:
    with pytest.raises(StageReportValidationError):
        validate_stage_report(_valid_report(stage_key="vectorize"))


def test_evidence_stage_key_maps_transcribe_markdown() -> None:
    assert evidence_stage_key("transcribe_markdown") == "markdown"
    assert evidence_stage_key("markdown") == "markdown"
    assert evidence_stage_key("structurize") == "structurize"
    assert evidence_stage_key("construct") == "construct"
    projected = validate_stage_report(_valid_report(stage_key="transcribe_markdown"))
    assert projected["stage_key"] == "markdown"
    with pytest.raises(StageReportValidationError):
        evidence_stage_key("lsrag.transcribe_markdown")
