"""Module-level helpers for TaskService."""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from src.contracts.common.errors import MkbError


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _encode_task_list_cursor(**fields: Any) -> str:
    """Produce an opaque, URL-safe Task-list continuation token."""

    payload = _json(fields).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def _decode_task_list_cursor(cursor: str) -> dict[str, Any]:
    """Decode only the Task-list token shape; callers bind its filters."""

    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        value = json.loads(base64.urlsafe_b64decode(padded.encode("ascii")))
    except (ValueError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError) as exc:
        raise MkbError("cursor-invalid", "Task cursor is invalid", 422) from exc
    if not isinstance(value, dict):
        raise MkbError("cursor-invalid", "Task cursor is invalid", 422)
    return value
