"""NS4-T15 / T18 / T19: pending evidence is typed and flushed as SQL, not extra."""

from __future__ import annotations

from src.contracts.observability.stage_report import validate_stage_report
from src.runtime.intake.generation_evidence import (
    record_pending_generation_evidence,
    take_pending_generation_evidence,
)

_PROCESS = "00000000-0000-4000-8000-0000000000ab"


def test_pending_cli_failure_stashes_kind_and_transport_report() -> None:
    take_pending_generation_evidence(_PROCESS)
    report = validate_stage_report(
        {
            "stage_key": "structurize",
            "disposition": "transport_failed",
            "error_code": "CLAUDE_CLI_OUTPUT_INVALID",
            "cli_structured_kind": "list",
            "latency_ms": 0,
        }
    )
    record_pending_generation_evidence(
        invocation={
            "invocation_uuid": "00000000-0000-4000-8000-000000000001",
            "status": "failed",
            "stage_key": "structurize",
            "error_code": "CLAUDE_CLI_OUTPUT_INVALID",
            "adapter_kind": "claude_cli",
            "cli_structured_kind": "list",
            "input_digest": "0" * 64,
            "process_attempt": 1,
            "invocation_ordinal": 0,
        },
        report=report,
        process_uuid=_PROCESS,
    )
    items = take_pending_generation_evidence(_PROCESS)
    assert len(items) == 1
    assert items[0]["invocation"]["status"] == "failed"
    assert items[0]["report"]["cli_structured_kind"] == "list"
    assert take_pending_generation_evidence(_PROCESS) == []


def test_pending_admit_mismatch_stashes_histogram_fields() -> None:
    take_pending_generation_evidence(_PROCESS)
    record_pending_generation_evidence(
        process_uuid=_PROCESS,
        report=validate_stage_report(
            {
                "stage_key": "structurize",
                "disposition": "rejected",
                "error_code": "STRUCTURE_GRANULARITY_SET_MISMATCH",
                "has_g0": True,
                "block_count": 3,
                "granularity_set": "0,1,2",
                "layer_counts": {"0": 1, "1": 1, "2": 1},
                "latency_ms": 0,
            }
        )
    )
    items = take_pending_generation_evidence(_PROCESS)
    assert items[0]["report"]["has_g0"] is True
    assert items[0]["report"]["layer_counts"]["2"] == 1


def test_pending_admit_reject_can_carry_failed_invocation() -> None:
    take_pending_generation_evidence(_PROCESS)
    record_pending_generation_evidence(
        process_uuid=_PROCESS,
        invocation={
            "invocation_uuid": "00000000-0000-4000-8000-0000000000ad",
            "status": "failed",
            "stage_key": "structurize",
            "error_code": "STRUCTURE_ANCHOR_MISSING",
            "adapter_kind": "claude_cli",
            "input_digest": "c" * 64,
            "process_attempt": 1,
            "invocation_ordinal": 0,
        },
        report=validate_stage_report(
            {
                "stage_key": "structurize",
                "disposition": "rejected",
                "error_code": "STRUCTURE_ANCHOR_MISSING",
                "has_g0": True,
                "block_count": 9,
                "granularity_set": "0,1",
                "layer_counts": {"0": 1, "1": 8},
                "latency_ms": 12,
            }
        ),
    )
    items = take_pending_generation_evidence(_PROCESS)
    assert items[0]["invocation"]["status"] == "failed"
    assert items[0]["invocation"]["error_code"] == "STRUCTURE_ANCHOR_MISSING"
    assert items[0]["report"]["disposition"] == "rejected"
    assert items[0]["report"]["latency_ms"] == 12
