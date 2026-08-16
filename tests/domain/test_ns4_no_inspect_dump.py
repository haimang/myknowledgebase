"""NS4-T25: collect no longer shells inspect_dump."""

from __future__ import annotations

from pathlib import Path

COLLECT = Path(".experiment/0815/runs/MKB-0815-R2/collect.py")


def test_collect_does_not_spawn_inspect_dump() -> None:
    text = COLLECT.read_text(encoding="utf-8")
    assert "inspect_dump.py" not in text
    assert "inspect_dump" not in text
