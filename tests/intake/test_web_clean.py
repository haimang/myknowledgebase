"""Per-domain tests for intake/web fetch + local-browser clean."""

from __future__ import annotations

import pytest

from intake.web import clean_web


@pytest.mark.asyncio
async def test_web_static_fetch_strips_chrome_and_returns_text() -> None:
    html = (
        "<html><head><script>alert(1)</script><style>p{color:red}</style></head>"
        "<body><nav>skip</nav><article><h1>Title</h1><p>Hello web.</p></article></body></html>"
    )

    async def fetch(_url: str) -> str:
        return html

    result = await clean_web(url="https://example.test/page", http_fetch=fetch, representation="static")
    assert "Hello web" in result.text
    assert "alert" not in result.text
    assert result.evidence["channel"] == "web"
    assert result.evidence["representation"] == "static"


@pytest.mark.asyncio
async def test_web_browser_path_uses_injected_renderer() -> None:
    async def browser(_url: str) -> str:
        return "<html><body><main>Rendered body</main></body></html>"

    result = await clean_web(
        url="https://example.test/app",
        representation="rendered",
        browser_fetch=browser,
    )
    assert "Rendered body" in result.text
    assert result.evidence["representation"] == "rendered"


@pytest.mark.asyncio
async def test_web_browser_without_injection_fails_closed() -> None:
    from src.contracts.common.errors import MkbError

    with pytest.raises(MkbError) as raised:
        await clean_web(url="https://example.test/app", representation="rendered")
    assert raised.value.code == "CLEAN_BROWSER_UNAVAILABLE"
