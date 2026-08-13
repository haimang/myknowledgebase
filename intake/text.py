"""Deterministic text/HTML clean primitives used by every intake channel."""

from __future__ import annotations

import re
import unicodedata
from html.parser import HTMLParser
from typing import Any

from src.contracts.common.errors import MkbError

_SPACE = re.compile(r"\s+")


class DeterministicHtmlTextExtractor(HTMLParser):
    """Structural HTML extractor; never use regex tag stripping as the SSOT."""

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


def canonical_text(value: str) -> str:
    return unicodedata.normalize("NFC", value.replace("\r\n", "\n").replace("\r", "\n"))


def clean_plain_text(value: str) -> str:
    return _SPACE.sub(" ", canonical_text(value)).strip()


def extract_html_text(value: str) -> tuple[str, dict[str, Any]]:
    extractor = DeterministicHtmlTextExtractor()
    try:
        extractor.feed(value)
        extractor.close()
    except Exception as exc:  # HTMLParser has a deliberately small error surface.
        raise MkbError("CLEAN_HTML_INVALID", "HTML representation could not be structurally parsed", 422) from exc
    clean = _SPACE.sub(" ", canonical_text("".join(extractor.parts))).strip()
    return clean, {
        "parser": "stdlib.html-parser.v1",
        "removed_tag_counts": dict(sorted(extractor.removed_tags.items())),
    }
