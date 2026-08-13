"""Legacy-inspired HTML sanitizer used before web text extraction."""

from __future__ import annotations

import re

_STYLE = re.compile(r"<style[^>]*>[\s\S]*?</style>", re.I)
_SCRIPT = re.compile(r"<script[^>]*>[\s\S]*?</script>", re.I)
_NOSCRIPT = re.compile(r"<noscript[^>]*>[\s\S]*?</noscript>", re.I)
_COMMENT = re.compile(r"<!--.*?-->", re.S)
_NAV = re.compile(r"<(?:nav|aside|footer|header)[^>]*>[\s\S]*?</(?:nav|aside|footer|header)>", re.I)


def sanitize_html(html: str) -> str:
    """Drop scripts, styles, and chrome before structural extraction."""

    cleaned = _COMMENT.sub("", html)
    cleaned = _STYLE.sub("", cleaned)
    cleaned = _SCRIPT.sub("", cleaned)
    cleaned = _NOSCRIPT.sub("", cleaned)
    cleaned = _NAV.sub("", cleaned)
    return cleaned
