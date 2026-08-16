"""NS4-T26: 0815 jsonl journal cannot carry reject shapes."""

from __future__ import annotations

from pathlib import Path

COLLECT = Path(".experiment/0815/runs/MKB-0815-R2/collect.py")


def test_journal_row_strips_reject_shapes() -> None:
    text = COLLECT.read_text(encoding="utf-8")
    assert "_JOURNAL_FORBIDDEN" in text
    assert "structure_reject" in text
    assert "def _journal_row" in text
    assert "_journal_row(row)" in text
