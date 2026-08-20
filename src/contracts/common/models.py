"""The non-domain-specific typed protocol foundation.

Every public or cross-layer model inherits this strict base. ``payload_extra``
is deliberately the sole extensibility bag; it is JSON-only and never controls
state transitions.
"""

from __future__ import annotations

import json
import re
from enum import StrEnum
from typing import Any, ClassVar

from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.contracts.common.ids import validate_external_uuid


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, populate_by_name=True)


class PayloadExtraModel(StrictModel):
    payload_extra: dict[str, Any] = Field(default_factory=dict)

    @field_validator("payload_extra")
    @classmethod
    def _ensure_json_object(cls, value: dict[str, Any]) -> dict[str, Any]:
        try:
            encoded = json.dumps(value, ensure_ascii=False, allow_nan=False)
        except (TypeError, ValueError) as exc:
            raise ValueError("payload_extra must contain JSON values") from exc
        if len(encoded.encode("utf-8")) > 64 * 1024:
            raise ValueError("payload_extra exceeds 64KiB")
        return value


class ExternalUuidFields:
    """Mix-in helpers kept out of model inheritance to avoid hidden fields."""

    @classmethod
    def validate_uuid(cls, value: str, field: str) -> str:
        return validate_external_uuid(value, field=field)


class TaskStatus(StrEnum):
    QUEUED = "queued"
    RUNNING = "running"
    CANCELLING = "cancelling"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ExecutionStatus(StrEnum):
    CREATED = "created"
    READY = "ready"
    RUNNING = "running"
    WAITING = "waiting"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class ProcessStatus(StrEnum):
    READY = "ready"
    CLAIMED = "claimed"
    RUNNING = "running"
    RETRY_WAIT = "retry_wait"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLING = "cancelling"
    CANCELLED = "cancelled"


class IntakeLifecycle(StrEnum):
    ACTIVE = "active"
    DEACTIVATED = "deactivated"
    DELETED = "deleted"


class CandidateSetState(StrEnum):
    OPEN = "open"
    SEALED = "sealed"
    ACCEPTED = "accepted"
    ABANDONED = "abandoned"


class GateStatus(StrEnum):
    OPEN = "open"
    RELEASED = "released"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


class ErrorBody(StrictModel):
    code: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=512)
    details: dict[str, Any] | None = None


class ErrorEnvelope(StrictModel):
    error: ErrorBody
    trace_uuid: str | None = None
    request_id: str | None = None


_ABSOLUTE_PATH = re.compile(r"(?:^|\s)(?:/[\w.-]+)+")
_SECRET_KEYS: ClassVar[set[str]] = {
    "authorization",
    "token",
    "password",
    "secret",
    "api_key",
    "apikey",
    "secretkey",
    "access_key",
    "accesskey",
    "private_key",
    "privatekey",
}
_SECRET_KEY_PATTERN = re.compile(r"(api[_-]?key|secret|token|password|authorization)", re.IGNORECASE)
_SIGNED_URL = re.compile(r"(X-Amz-Signature|X-Amz-Credential|Signature=|sig=)", re.IGNORECASE)


def assert_safe_public_data(value: Any) -> None:
    """Reject values that would leak secrets or host paths through public contracts."""

    if isinstance(value, dict):
        for key, item in value.items():
            folded = str(key).lower().replace("-", "")
            if folded in _SECRET_KEYS or _SECRET_KEY_PATTERN.search(str(key)):
                raise ValueError(f"unsafe key {key!r} in public payload")
            assert_safe_public_data(item)
    elif isinstance(value, list):
        for item in value:
            assert_safe_public_data(item)
    elif isinstance(value, str):
        if _ABSOLUTE_PATH.search(value):
            raise ValueError("absolute paths are not permitted in public payloads")
        if _SIGNED_URL.search(value):
            raise ValueError("signed URLs are not permitted in public payloads")
