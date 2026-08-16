"""NS4-T04: P0 reopen draft lists every T-O-369 required column and table."""

from __future__ import annotations

from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]
REOPEN = REPOSITORY_ROOT / "docs/plan/new-start/NS4-d04-s15-reopen.md"

REQUIRED_PHRASES = (
    "mkb_generation_invocations",
    "mkb_generation_stage_reports",
    "status",
    "stage_key",
    "error_code",
    "adapter_kind",
    "cli_structured_kind",
    "disposition",
    "has_g0",
    "block_count",
    "granularity_set",
    "layer_counts",
    "latency_ms",
    "schema_digest",
    "timeline_by_task",
    "ObservabilityReadPort",
)


def test_ns4_reopen_draft_lists_t_o_369_closed_set() -> None:
    assert REOPEN.is_file()
    text = REOPEN.read_text(encoding="utf-8")
    missing = [phrase for phrase in REQUIRED_PHRASES if phrase not in text]
    assert missing == [], "reopen draft missing T-O-369 inventory:\n" + "\n".join(missing)
    assert "55 → **56**" in text or "55 → 56" in text
    assert "structure_reject" in text
    assert "payload_extra" in text
