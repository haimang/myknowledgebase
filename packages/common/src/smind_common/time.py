from datetime import datetime, timedelta, timezone


def _fmt(dt: datetime) -> str:
    """Format a datetime as the SSOT UTC ISO string: YYYY-MM-DDTHH:MM:SS.mmmZ.

    Length-stable (24 chars), 3-digit milliseconds via ``microsecond // 1000``
    truncation, ``Z`` suffix — lexicographically comparable with SQLite
    ``strftime('%Y-%m-%dT%H:%M:%fZ', 'now')``.
    """
    return dt.strftime("%Y-%m-%dT%H:%M:%S") + f".{dt.microsecond // 1000:03d}Z"


def utc_now_iso() -> str:
    return _fmt(datetime.now(timezone.utc))


def add_seconds_iso(seconds: int) -> str:
    return _fmt(datetime.now(timezone.utc) + timedelta(seconds=seconds))
