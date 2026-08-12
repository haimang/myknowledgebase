"""UUID and digest primitives.

External callers may provide UUIDv4 or UUIDv7. MKB-generated identities are
UUIDv7 so that every durable domain identity is opaque yet time-sortable.
"""

from __future__ import annotations

import hashlib
import json
import secrets
import threading
import time
import uuid
from typing import Any

from src.contracts.common.errors import MkbError

_uuid7_lock = threading.Lock()
_last_millis = -1
_sequence = 0


def uuid7() -> str:
    """Return a RFC 9562 UUIDv7 without relying on a Python-version-specific API."""

    global _last_millis, _sequence
    with _uuid7_lock:
        millis = time.time_ns() // 1_000_000
        if millis <= _last_millis:
            millis = _last_millis
            _sequence = (_sequence + 1) & 0xFFF
        else:
            _last_millis = millis
            _sequence = secrets.randbits(12)
        # 48 bits timestamp | 4 bit version | 12 random/monotonic bits |
        # RFC 4122 variant | 62 random bits.
        high = (millis << 16) | (0x7 << 12) | _sequence
        low = (0b10 << 62) | secrets.randbits(62)
        return str(uuid.UUID(int=(high << 64) | low))


def validate_external_uuid(value: str, *, field: str = "uuid") -> str:
    try:
        parsed = uuid.UUID(str(value))
    except (TypeError, ValueError, AttributeError) as exc:
        raise MkbError("invalid-uuid", f"{field} must be a UUIDv4 or UUIDv7", 422) from exc
    if parsed.int == 0 or parsed.version not in (4, 7):
        raise MkbError("invalid-uuid-version", f"{field} must be a UUIDv4 or UUIDv7", 422)
    return str(parsed)


def validate_uuid7(value: str, *, field: str = "uuid") -> str:
    canonical = validate_external_uuid(value, field=field)
    if uuid.UUID(canonical).version != 7:
        raise MkbError("invalid-internal-uuid", f"{field} must be UUIDv7", 422)
    return canonical


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def canonical_json(value: Any) -> bytes:
    """Canonical JSON used for stable task/outbox/definition fingerprints."""

    return json.dumps(
        value,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def stable_digest(value: Any) -> str:
    return sha256_bytes(canonical_json(value))
