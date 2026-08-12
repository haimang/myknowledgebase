"""Stable, redactable domain errors shared by HTTP and runtime boundaries."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any

_SENSITIVE_KEY = re.compile(
    r"(authorization|x[-_]?mkb[-_]?internal[-_]?token|token|password|secret|api[_-]?key|access[_-]?key|"
    r"private[_-]?key|credential|cookie|prompt|content|vector|stack|sql|connection|dsn)",
    re.IGNORECASE,
)
_SECRET_VALUE = re.compile(
    r"\b(?:authorization|x[-_]?mkb[-_]?internal[-_]?token|api[_-]?key|access[_-]?key|token|password)"
    r"\s*[:=]\s*(?:bearer\s+)?[^\s,;]+",
    re.IGNORECASE,
)
_BEARER_VALUE = re.compile(r"\bbearer\s+[A-Za-z0-9._~+/=-]+", re.IGNORECASE)
_CONNECTION_URL = re.compile(
    r"\b(?:postgres(?:ql)?|mysql|redis|mongodb(?:\+srv)?|amqp|file)://[^\s'\"<>]+", re.IGNORECASE
)
_ABS_PATH = re.compile(r"(?<![:A-Za-z0-9_])/(?:[A-Za-z0-9_.-]+/)*[A-Za-z0-9_.-]+")
_REQUEST_ID = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")


def _safe_text(value: str) -> str:
    value = _CONNECTION_URL.sub("[REDACTED_CONNECTION]", value)
    value = _SECRET_VALUE.sub("[REDACTED]", value)
    value = _BEARER_VALUE.sub("Bearer [REDACTED]", value)
    return _ABS_PATH.sub("[REDACTED_PATH]", value)


def _safe_detail(value: Any) -> Any:
    """Keep contracts pure while applying the minimum public-error allowlist."""

    if isinstance(value, dict):
        return {
            str(key): "[REDACTED]" if _SENSITIVE_KEY.search(str(key)) else _safe_detail(item)
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [_safe_detail(item) for item in value]
    if isinstance(value, tuple):
        return [_safe_detail(item) for item in value]
    if isinstance(value, str):
        return _safe_text(value)
    if value is None or isinstance(value, bool | int | float):
        return value
    # Unexpected driver objects should never be serialized into the public
    # envelope, even when a caller mistakenly passes them as error details.
    return "[REDACTED]"


@dataclass(slots=True)
class MkbError(Exception):
    """An expected error that is safe to expose through the public envelope."""

    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None

    def as_dict(self, request_id: str | None = None) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code[:128], "message": _safe_text(self.message)[:512]}
        if self.details:
            safe_details = _safe_detail(self.details)
            if isinstance(safe_details, dict):
                error["details"] = safe_details
        result: dict[str, Any] = {"error": error}
        if request_id and _REQUEST_ID.fullmatch(request_id):
            result["request_id"] = request_id
        return result


class ConflictError(MkbError):
    def __init__(self, code: str, message: str, details: dict[str, Any] | None = None) -> None:
        super().__init__(code, message, 409, details)


class NotFoundError(MkbError):
    def __init__(self, code: str, message: str = "Resource was not found") -> None:
        super().__init__(code, message, 404)


class NotReadyError(MkbError):
    def __init__(self, code: str = "not-ready", message: str = "Service is not ready") -> None:
        super().__init__(code, message, 503)


class UnauthorizedError(MkbError):
    def __init__(self, code: str, message: str = "Internal token is invalid") -> None:
        super().__init__(code, message, 401)
