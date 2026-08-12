"""Deterministic, durable single-intake LS-RAG stage implementation.

The workflow graph itself remains declarative in :mod:`src.workflows`.  This
module is the narrow runtime-side implementation for its registered Process
capabilities.  It deliberately receives only a claimed ``ProcessCommand`` and
returns a typed outcome; all durable domain mutations are deferred to
``OutcomeArtifactCommitter`` so they commit atomically with the Process fence.

The deterministic profile is intentional: it provides a complete local proof
path for CI and offline deployments.  A live inference profile can be added at
the facade seam without changing the intake/generation/vector state model.
"""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from html.parser import HTMLParser
from typing import Any, Literal

from src.contracts.common.errors import MkbError
from src.contracts.inference.models import (
    InferenceBinding,
)
from src.contracts.storage.models import ObjectStat
from src.runtime.http_acquisition import HttpAcquisitionResult

_SPACE = re.compile(r"\s+")
_HTML_HINT = re.compile(r"<\s*(?:!doctype|html|head|body|article|main|div|p|h[1-6]|table|ul|ol|section)\b", re.I)
_PDF_TEXT = re.compile(rb"\((?:\\.|[^\\()])*\)\s*(?:Tj|')")
_PDF_ARRAY_TEXT = re.compile(rb"\[(.*?)\]\s*TJ", re.S)
_PDF_LITERAL = re.compile(rb"\((?:\\.|[^\\()])*\)")

HttpFetcher = Callable[[str], str | bytes | HttpAcquisitionResult | Awaitable[str | bytes | HttpAcquisitionResult]]
BrowserFetcher = HttpFetcher

# S07 has two explicit construction modes.  Metadata refresh is intentionally
# a closed v1 profile: it may reuse only a frozen, full-valid summary package;
# a future summary regeneration profile must add a new typed value rather than
# silently falling back to the regular construct path.
ConstructMode = Literal["full_construct", "metadata_refresh"]
MetadataRefreshMode = Literal["reuse_summaries"]
_METADATA_REFRESH_REUSE_SUMMARIES: MetadataRefreshMode = "reuse_summaries"
_METADATA_REFRESH_SOURCE_TYPES = (
    "structure_document",
    "retrieval_block_projection",
    "structure_validation_report",
    "construction_document",
    "dual_channel_projection",
    "construction_validation_report",
)


@dataclass(frozen=True, slots=True)
class _AcquiredContent:
    """Immediate source representation plus safe acquisition evidence.

    Stage envelopes are JSON-only, so binary representations are carried as a
    lossless latin-1 transport string until the decode capability consumes
    them.  The ``raw_byte_*`` values remain the authoritative byte witness.
    """

    raw_text: str
    is_binary: bool
    media_type: str
    evidence: dict[str, Any]


class _DeterministicHtmlTextExtractor(HTMLParser):
    """Small structural HTML extractor; never use regex tag stripping."""

    _IGNORED = frozenset({"script", "style", "template", "noscript", "svg", "canvas"})
    _BLOCK = frozenset(
        {
            "address",
            "article",
            "aside",
            "blockquote",
            "br",
            "div",
            "dl",
            "dt",
            "dd",
            "figcaption",
            "figure",
            "footer",
            "h1",
            "h2",
            "h3",
            "h4",
            "h5",
            "h6",
            "header",
            "hr",
            "li",
            "main",
            "nav",
            "ol",
            "p",
            "pre",
            "section",
            "table",
            "td",
            "th",
            "tr",
            "ul",
        }
    )

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._ignored_depth = 0
        self.removed_tags: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        del attrs
        normalized = tag.lower()
        if normalized in self._IGNORED:
            self._ignored_depth += 1
            self.removed_tags[normalized] = self.removed_tags.get(normalized, 0) + 1
            return
        if not self._ignored_depth and normalized in self._BLOCK:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)
        self.handle_endtag(tag)

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in self._IGNORED:
            if self._ignored_depth:
                self._ignored_depth -= 1
            return
        if not self._ignored_depth and normalized in self._BLOCK:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._ignored_depth:
            self.parts.append(data)


def _canonical_text(value: str) -> str:
    """The v1 text coordinate: UTF-8 decoded, LF and NFC normalized."""

    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def _is_sha256_digest(value: object) -> bool:
    return isinstance(value, str) and len(value) == 64 and all(char in "0123456789abcdef" for char in value)


def _canonical_json_text(value: str) -> str:
    """Strict I-JSON-shaped deterministic serialization used as v1 JCS.

    The implementation deliberately rejects non-finite JSON constants rather
    than silently accepting Python's extensions.  JSON numbers are emitted by
    CPython's deterministic encoder; the capability/version evidence makes
    that concrete implementation part of the historical interpretation.
    """

    def reject_constant(_: str) -> object:
        raise ValueError("non-finite JSON constants are not permitted")

    try:
        parsed = json.loads(value, parse_constant=reject_constant)
        return json.dumps(parsed, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError, json.JSONDecodeError) as exc:
        raise MkbError("DECODE_JSON_INVALID", "JSON representation is not canonicalizable", 422) from exc


def _extract_html_text(value: str) -> tuple[str, dict[str, Any]]:
    extractor = _DeterministicHtmlTextExtractor()
    try:
        extractor.feed(value)
        extractor.close()
    except Exception as exc:  # HTMLParser has a deliberately small error surface.
        raise MkbError("CLEAN_HTML_INVALID", "HTML representation could not be structurally parsed", 422) from exc
    clean = _SPACE.sub(" ", _canonical_text("".join(extractor.parts))).strip()
    return clean, {
        "parser": "stdlib.html-parser.v1",
        "removed_tag_counts": dict(sorted(extractor.removed_tags.items())),
    }


def _pdf_literal_bytes(value: bytes) -> bytes:
    """Decode the limited PDF literal-string subset used by local v1 text.

    It is intentionally not a permissive PDF renderer.  Encrypted, malformed
    or image-only PDFs therefore reach the explicit local-OCR capability
    refusal instead of being misreported as an empty successful document.
    """

    output = bytearray()
    index = 0
    while index < len(value):
        byte = value[index]
        if byte != 0x5C:  # backslash
            output.append(byte)
            index += 1
            continue
        index += 1
        if index >= len(value):
            break
        escaped = value[index]
        mapping = {ord("n"): 0x0A, ord("r"): 0x0D, ord("t"): 0x09, ord("b"): 0x08, ord("f"): 0x0C}
        if escaped in mapping:
            output.append(mapping[escaped])
            index += 1
            continue
        if 0x30 <= escaped <= 0x37:
            digits = bytearray([escaped])
            index += 1
            while index < len(value) and len(digits) < 3 and 0x30 <= value[index] <= 0x37:
                digits.append(value[index])
                index += 1
            output.append(int(digits.decode("ascii"), 8) & 0xFF)
            continue
        if escaped in {0x0A, 0x0D}:
            # PDF line continuation consumes an optional paired newline.
            if escaped == 0x0D and index + 1 < len(value) and value[index + 1] == 0x0A:
                index += 1
            index += 1
            continue
        output.append(escaped)
        index += 1
    return bytes(output)


def _extract_pdf_text(value: bytes) -> tuple[str, dict[str, Any]]:
    if not value.startswith(b"%PDF-"):
        raise MkbError("DECODE_PDF_INVALID", "PDF acquisition did not contain a PDF signature", 422)
    literals: list[bytes] = []
    for match in _PDF_TEXT.finditer(value):
        literals.append(_pdf_literal_bytes(match.group(0)[1 : match.group(0).rfind(b")")]))
    for array_match in _PDF_ARRAY_TEXT.finditer(value):
        for literal in _PDF_LITERAL.finditer(array_match.group(1)):
            literals.append(_pdf_literal_bytes(literal.group(0)[1:-1]))
    joined = b"\n".join(part for part in literals if part)
    if not joined:
        raise MkbError(
            "CLEAN_OCR_CAPABILITY_UNAVAILABLE",
            "PDF has no extractable local text layer; local OCR is not configured",
            422,
        )
    try:
        if joined.startswith((b"\xfe\xff", b"\xff\xfe")):
            text = joined.decode("utf-16")
        else:
            text = joined.decode("utf-8")
    except UnicodeDecodeError:
        text = joined.decode("latin-1")
    return _canonical_text(text), {
        "decoder": "local-pdf-literal-text.v1",
        "page_count_hint": len(re.findall(rb"/Type\s*/Page\b", value)),
        "text_layer": "present",
    }


def _sniff_media_type(value: bytes) -> str:
    if value.startswith(b"%PDF-"):
        return "application/pdf"
    if value.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if value.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if value.startswith((b"GIF87a", b"GIF89a")):
        return "image/gif"
    if value.startswith(b"RIFF") and value[8:12] == b"WEBP":
        return "image/webp"
    try:
        text = value.decode("utf-8-sig")
    except UnicodeDecodeError:
        return "application/octet-stream"
    stripped = text.lstrip()
    if stripped.startswith(("{", "[")):
        try:
            _canonical_json_text(text)
        except MkbError:
            pass
        else:
            return "application/json"
    if _HTML_HINT.search(stripped):
        return "text/html"
    return "text/plain"


def _normalized_media_type(value: object) -> str | None:
    if not isinstance(value, str):
        return None
    media_type = value.split(";", 1)[0].strip().lower()
    return media_type or None


def _verified_media_type(*, declared: str | None, detected: str, mode: str | None = None) -> str:
    """Choose a versioned verified type while failing closed on critical lies."""

    if mode == "pdf" and detected != "application/pdf":
        raise MkbError("ACQUISITION_MEDIA_MISMATCH", "PDF mode did not return a PDF representation", 422)
    if declared == "application/pdf" and detected != "application/pdf":
        raise MkbError("ACQUISITION_MEDIA_MISMATCH", "Declared PDF representation did not verify", 422)
    if declared and declared.startswith("image/") and declared != detected:
        raise MkbError("ACQUISITION_MEDIA_MISMATCH", "Declared image representation did not verify", 422)
    if detected != "application/octet-stream":
        return detected
    return declared or detected


def _clean_text(value: str) -> str:
    return _SPACE.sub(" ", _canonical_text(value)).strip()


@dataclass(frozen=True, slots=True)
class _StageMaterial:
    """A staged envelope plus the small callback facts it needs."""

    envelope: dict[str, Any]
    output_bytes: bytes
    proof_bytes: bytes


@dataclass(frozen=True, slots=True)
class _GenerationArtifactMaterial:
    """One independently promoted immutable S06/S07 generation member."""

    artifact_uuid: str
    artifact_type: str
    stat: ObjectStat


@dataclass(frozen=True, slots=True)
class _FrozenGenerationConfig:
    """Exact L4/registry coordinates for one live S06 or S07 model call.

    Prompt bytes remain transient caller input.  The durable ledgers retain
    only the prompt identity and content digest carried here.
    """

    capability_key: Literal["structured_generate", "text_generate"]
    binding: InferenceBinding
    prompt_key: str
    prompt_version: str
    prompt_digest: str
    prompt_text: str
    schema_key: str
    schema_version: str
    schema_digest: str

    @property
    def prompt_ref(self) -> str:
        return f"{self.prompt_key}.{self.prompt_version}"

    @property
    def schema_ref(self) -> str:
        return f"{self.schema_key}@{self.schema_version}"


@dataclass(frozen=True, slots=True)
class _GenerationInvocation:
    """The durable S06/S07 call identity allocated before inference starts."""

    invocation_uuid: str
    invocation_ordinal: int
    process_attempt: int
    input_digest: str
    capability_key: Literal["structured_generate", "text_generate"]
    stage_key: str


def _json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def _digest_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


