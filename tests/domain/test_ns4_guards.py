"""NS4-P0 architecture ratchets: extra is not an evidence plane.

Current extra-key writes in intake are a documented P0→P1 allowlist.
P1 must empty it. New files may not join the list.
"""

from __future__ import annotations

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[2]

# P1 deletes these writes. Adding a path here is an NS4 stop-ship.
NS4_EXTRA_EVIDENCE_ALLOWLIST = frozenset()

_EXTRA_EVIDENCE = re.compile(
    r"""payload_extra|extra\[['\"]structure_reject['\"]\]|extra\[['\"]cli_structured_kind['\"]\]"""
    r"""|\[['\"]structure_reject['\"]\]\s*=|\[['\"]cli_structured_kind['\"]\]\s*="""
)
_ASSIGN_EVIDENCE_KEY = re.compile(
    r"""extra\[['\"](?:structure_reject|cli_structured_kind)['\"]\]\s*="""
    r"""|payload_extra\[.['\"](?:structure_reject|cli_structured_kind)"""
)


def test_ns4_extra_evidence_keys_are_not_introduced_outside_p1_allowlist() -> None:
    hits: list[str] = []
    for root in ("src", "api"):
        for path in (REPOSITORY_ROOT / root).rglob("*.py"):
            relative = str(path.relative_to(REPOSITORY_ROOT))
            text = path.read_text(encoding="utf-8")
            if not _ASSIGN_EVIDENCE_KEY.search(text):
                continue
            if relative not in NS4_EXTRA_EVIDENCE_ALLOWLIST:
                hits.append(relative)
    assert hits == [], "NS4 forbids new extra evidence keys:\n" + "\n".join(hits)


def test_ns4_extra_evidence_allowlist_is_empty_after_p1() -> None:
    assert NS4_EXTRA_EVIDENCE_ALLOWLIST == frozenset()


def test_ns4_src_has_no_dual_sqlite_turso_read_surface() -> None:
    forbidden = re.compile(r"dual[_-]?read|sqlite\s*\+\s*turso|read_sqlite_and_turso", re.I)
    hits: list[str] = []
    for path in (REPOSITORY_ROOT / "src").rglob("*.py"):
        text = path.read_text(encoding="utf-8")
        if forbidden.search(text):
            hits.append(str(path.relative_to(REPOSITORY_ROOT)))
    assert hits == [], "NS4 forbids a dual sqlite+turso read API:\n" + "\n".join(hits)
