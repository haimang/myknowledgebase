"""Structural HTML sanitizer with a closed tag/attribute policy."""

from __future__ import annotations

from html import escape
from html.parser import HTMLParser
from typing import Any

from src.contracts.common.errors import MkbError

_DROP_ELEMENTS = frozenset(
    {"script", "style", "svg", "noscript", "iframe", "object", "embed", "nav", "footer", "header", "aside", "form", "template"}
)
_ALLOWED_ATTRIBUTES = frozenset({"href", "src", "alt", "title", "colspan", "rowspan", "lang", "datetime"})
_VOID_ELEMENTS = frozenset({"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "source", "track", "wbr"})


class _Sanitizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.dropped_depth = 0
        self.dropped_elements: dict[str, int] = {}
        self.dropped_attributes: dict[str, int] = {}

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        if normalized in _DROP_ELEMENTS:
            self.dropped_elements[normalized] = self.dropped_elements.get(normalized, 0) + 1
            self.dropped_depth += 1
            return
        if self.dropped_depth:
            return
        selected: list[str] = []
        for name, value in attrs:
            attribute = name.casefold()
            if attribute not in _ALLOWED_ATTRIBUTES:
                self.dropped_attributes[attribute] = self.dropped_attributes.get(attribute, 0) + 1
                continue
            if value is None:
                selected.append(attribute)
            else:
                selected.append(f'{attribute}="{escape(value, quote=True)}"')
        suffix = f" {' '.join(selected)}" if selected else ""
        self.parts.append(f"<{normalized}{suffix}>")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        normalized = tag.casefold()
        if normalized in _DROP_ELEMENTS:
            self.dropped_elements[normalized] = self.dropped_elements.get(normalized, 0) + 1
            return
        self.handle_starttag(normalized, attrs)
        if not self.dropped_depth and normalized not in _VOID_ELEMENTS:
            self.parts.append(f"</{normalized}>")

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.casefold()
        if normalized in _DROP_ELEMENTS:
            if self.dropped_depth:
                self.dropped_depth -= 1
            return
        if not self.dropped_depth and normalized not in _VOID_ELEMENTS:
            self.parts.append(f"</{normalized}>")

    def handle_data(self, data: str) -> None:
        if not self.dropped_depth:
            self.parts.append(escape(data, quote=False))

    def handle_entityref(self, name: str) -> None:
        if not self.dropped_depth:
            self.parts.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        if not self.dropped_depth:
            self.parts.append(f"&#{name};")


def sanitize_html_document(html: str) -> tuple[str, dict[str, Any]]:
    sanitizer = _Sanitizer()
    try:
        sanitizer.feed(html)
        sanitizer.close()
    except Exception as exc:
        raise MkbError("CLEAN_HTML_INVALID", "HTML representation could not be structurally sanitized", 422) from exc
    return "".join(sanitizer.parts), {
        "sanitizer": "stdlib.html-sanitizer.v1",
        "dropped_element_counts": dict(sorted(sanitizer.dropped_elements.items())),
        "dropped_attribute_counts": dict(sorted(sanitizer.dropped_attributes.items())),
        "allowed_attributes": sorted(_ALLOWED_ATTRIBUTES),
    }


def sanitize_html(html: str) -> str:
    return sanitize_html_document(html)[0]


__all__ = ["sanitize_html", "sanitize_html_document"]
