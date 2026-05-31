"""F1-05 unit tests for the SSOT time helpers (T01-T03)."""

import re
import sqlite3
from datetime import datetime, timezone

from smind_common.time import add_seconds_iso, utc_now_iso

ISO_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$")


def test_t01_now_iso_round_trip() -> None:
    """T01: utc_now_iso()/add_seconds_iso() parse back via fromisoformat."""
    for s in (utc_now_iso(), add_seconds_iso(60)):
        # Z -> +00:00 so fromisoformat accepts it on Python < 3.11 too.
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        assert dt.tzinfo is not None
        assert dt.utcoffset() == timezone.utc.utcoffset(None)


def test_t02_seconds_regex() -> None:
    """T02: format is length-stable YYYY-MM-DDTHH:MM:SS.mmmZ (24 chars)."""
    now = utc_now_iso()
    later = add_seconds_iso(60)
    assert ISO_RE.match(now), f"format drift: {now!r}"
    assert ISO_RE.match(later), f"format drift: {later!r}"
    assert len(now) == 24
    assert len(later) == 24
    # add_seconds_iso(60) is lexicographically later than now.
    assert later > now


def test_t03_py_sql_comparable() -> None:
    """T03: PY utc_now_iso() and SQLite strftime share a comparable format.

    Same shape (24-char .mmmZ), same minute prefix for "now", and
    lexicographic order == chronological order across both producers.
    """
    conn = sqlite3.connect(":memory:")
    sql_now = conn.execute(
        "SELECT strftime('%Y-%m-%dT%H:%M:%fZ', 'now')"
    ).fetchone()[0]
    conn.close()

    assert ISO_RE.match(sql_now), f"SQLite shape: {sql_now!r}"

    py_now = utc_now_iso()
    # Same minute prefix (YYYY-MM-DDTHH:MM, 16 chars) for "now" on both sides.
    assert py_now[:16] == sql_now[:16]

    # Lexicographic == chronological across the two producers.
    past = add_seconds_iso(-3600)
    future = add_seconds_iso(3600)
    assert past < py_now < future
    assert past < sql_now < future
