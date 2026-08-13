"""Web fetch + local-browser representation clean channel."""

from __future__ import annotations

import inspect

from intake.text import extract_html_text
from intake.types import BrowserFetch, CleanResult, HttpFetch
from intake.web.sanitize import sanitize_html
from src.contracts.common.errors import MkbError


async def _call_fetch(fetcher: HttpFetch | BrowserFetch, url: str) -> str:
    result = fetcher(url)
    if inspect.isawaitable(result):
        result = await result
    if isinstance(result, bytes):
        return result.decode("utf-8", errors="replace")
    if isinstance(result, str):
        return result
    raise MkbError("CLEAN_WEB_FETCH_INVALID", "Web fetcher did not return text or bytes", 422)


def clean_html_representation(html: str, *, capability: str, representation: str) -> CleanResult:
    sanitized = sanitize_html(html)
    text, evidence = extract_html_text(sanitized)
    if not text:
        raise MkbError("CLEAN_EMPTY", "Web cleaning produced no admissible text", 422)
    evidence = {
        **evidence,
        "channel": "web",
        "representation": representation,
        "sanitizer": "intake.web.sanitize.v1",
    }
    return CleanResult(text=text, capability=capability, evidence=evidence)


async def clean_web(
    *,
    html: str | None = None,
    url: str | None = None,
    representation: str = "static",
    capability: str = "clean.extract.web",
    http_fetch: HttpFetch | None = None,
    browser_fetch: BrowserFetch | None = None,
) -> CleanResult:
    """Clean a web document from acquired HTML or an injected fetch/browser port."""

    body = html
    if body is None:
        if not isinstance(url, str) or not url:
            raise MkbError("CLEAN_WEB_INPUT_INVALID", "Web clean requires HTML bytes or a URL", 422)
        if representation == "rendered":
            if browser_fetch is None:
                raise MkbError("CLEAN_BROWSER_UNAVAILABLE", "Local browser fetch is not injected", 503)
            body = await _call_fetch(browser_fetch, url)
        else:
            if http_fetch is None:
                raise MkbError("CLEAN_HTTP_UNAVAILABLE", "HTTP fetch is not injected", 503)
            body = await _call_fetch(http_fetch, url)
    return clean_html_representation(body, capability=capability, representation=representation)


__all__ = ["clean_html_representation", "clean_web"]
