"""Typed clean ports and results owned by the top-level intake package."""

from __future__ import annotations

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
    clean_text: str
    media_type: str
    payload: dict[str, Any] = field(default_factory=dict)
    evidence: dict[str, Any] = field(default_factory=dict)


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
