"""UTC-only timestamp helpers for durable contracts."""

from __future__ import annotations

from datetime import UTC, datetime

from src.contracts.common.errors import MkbError


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")


def normalize_rfc3339(value: str, *, field: str = "timestamp") -> str:
    if not isinstance(value, str):
        raise MkbError("invalid-timestamp", f"{field} must be RFC3339", 422)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise MkbError("invalid-timestamp", f"{field} must be RFC3339", 422) from exc
    if parsed.tzinfo is None:
        raise MkbError("invalid-timestamp", f"{field} must include a timezone", 422)
    return parsed.astimezone(UTC).isoformat(timespec="milliseconds").replace("+00:00", "Z")
