"""Closed local-CAS handle identity shared by storage and catalog services."""

from __future__ import annotations

import re

from src.contracts.common.errors import MkbError
from src.contracts.storage.models import ObjectHandle

_HANDLE_ID = re.compile(r"^mkbobj:v1:([0-9a-f-]{36}):([0-9a-f]{64})$")


def object_handle(team_uuid: str, digest: str) -> ObjectHandle:
    return ObjectHandle(value=f"mkbobj:v1:{team_uuid}:{digest}")


def digest_from_handle(team_uuid: str, handle: ObjectHandle) -> str:
    match = _HANDLE_ID.fullmatch(handle.value)
    if match is None:
        raise MkbError("SEC_PATH_REJECTED", "Object handle is invalid", 422)
    if match.group(1) != team_uuid:
        raise MkbError("OBJECT_AUTH_TEAM_MISMATCH", "Object handle belongs to a different Team", 403)
    return match.group(2)


__all__ = ["digest_from_handle", "object_handle"]
