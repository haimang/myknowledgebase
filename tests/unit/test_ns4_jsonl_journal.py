"""NS4-T26: 0815 jsonl journal cannot carry reject shapes."""

from __future__ import annotations

from pathlib import Path

COLLECT = Path(".experiment/0815/runs/MKB-0815-R2/collect.py")


def test_journal_row_strips_reject_shapes() -> None:
    text = COLLECT.read_text(encoding="utf-8")
    start = text.index("def _journal_row")
    end = text.index("\n\ndef ", start)
    namespace: dict[str, object] = {}
    forbidden_start = text.index("_JOURNAL_FORBIDDEN")
    forbidden_end = text.index("\n\n", forbidden_start)
    exec(compile(text[forbidden_start:forbidden_end] + "\n" + text[start:end], str(COLLECT), "exec"), namespace)
    journal_row = namespace["_journal_row"]
    assert callable(journal_row)
    cleaned = journal_row({"ok": True, "structure_reject": {"counts": 1}, "keep": 2})
    assert cleaned == {"ok": True, "keep": 2}
    assert "structure_reject" not in cleaned
