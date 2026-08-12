"""Stable, redactable domain errors shared by HTTP and runtime boundaries."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True)
class MkbError(Exception):
    """An expected error that is safe to expose through the public envelope."""

    code: str
    message: str
    status_code: int = 400
    details: dict[str, Any] | None = None

    def as_dict(self, request_id: str | None = None) -> dict[str, Any]:
        error: dict[str, Any] = {"code": self.code, "message": self.message}
        if self.details:
            error["details"] = self.details
        result: dict[str, Any] = {"error": error}
        if request_id:
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
