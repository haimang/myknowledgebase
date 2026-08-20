"""NS4-T26: 0815 jsonl journal cannot carry reject shapes."""

from __future__ import annotations

import sys
from pathlib import Path

COLLECT = Path(".experiment/0815/runs/MKB-0815-R2/collect.py")


def test_journal_row_strips_reject_shapes() -> None:
    sys.path.insert(0, str(COLLECT.resolve().parent))
    import collect as collect_mod  # type: ignore[import-not-found]

    journal_row = collect_mod._journal_row
    cleaned = journal_row({"ok": True, "structure_reject": {"counts": 1}, "keep": 2})
    assert cleaned == {"ok": True, "keep": 2}
    assert "structure_reject" not in cleaned
