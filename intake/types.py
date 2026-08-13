"""Typed clean ports and results owned by the top-level intake package."""

from __future__ import annotations

import hashlib
import re
from collections.abc import Awaitable, Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol


@dataclass(frozen=True, slots=True)
class CleanResult:
    """One cleaned text artifact plus typed evidence."""

    text: str
    capability: str
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CleanMember:
    """One scatter/collection member after provider-shaped mapping."""

    ordinal: int
    external_key: str
    normalized_external_key: str
    raw_digest: str
    content_digest: str
    meta_digest: str
    clean_text: str
    media_type: str
    filter_meta: dict[str, Any]
    context_meta: dict[str, Any]
    semantic_tuples: tuple[dict[str, Any], ...]
    payload: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CleanPrompt:
    """Verified prompt material resolved from a frozen ConfigSnapshot pointer."""

    key: str
    version: str
    text: str
    content_sha256: str

    def __post_init__(self) -> None:
        if not self.key or not self.version or not self.text:
            raise ValueError("clean prompt coordinate and text must be non-empty")
        if re.fullmatch(r"[0-9a-f]{64}", self.content_sha256) is None:
            raise ValueError("clean prompt SHA-256 is invalid")
        actual_sha256 = hashlib.sha256(self.text.encode("utf-8")).hexdigest()
        if actual_sha256 != self.content_sha256:
            raise ValueError("clean prompt text does not match its SHA-256")


class CleanLanguageModel(Protocol):
    """Injectable document / text cleaner used by PDF, docs, OCR, and Vision."""

    async def complete(
        self,
        *,
        prompt: str,
        text: str | None = None,
        blob: bytes | None = None,
        media_type: str | None = None,
    ) -> str: ...


HttpFetch = Callable[[str], str | bytes | Awaitable[str | bytes]]
BrowserFetch = HttpFetch


def as_mapping(value: object) -> Mapping[str, Any] | None:
    return value if isinstance(value, Mapping) else None
