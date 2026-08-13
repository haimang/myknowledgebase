"""Per-domain tests for intake/web fetch + local-browser clean."""

from __future__ import annotations

import hashlib

import pytest

from intake.types import CleanPrompt
from intake.web import clean_web
from intake.web.sanitize import sanitize_html
from src.contracts.common.errors import MkbError

_PROMPT_TEXT = "verified prompt"
_PROMPT = CleanPrompt(
    key="promptA.default",
    version="v1",
    text=_PROMPT_TEXT,
    content_sha256=hashlib.sha256(_PROMPT_TEXT.encode()).hexdigest(),
)


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
    assert result.evidence["strategy"] == "web.deterministic"


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
    with pytest.raises(MkbError) as raised:
        await clean_web(url="https://example.test/app", representation="rendered")
    assert raised.value.code == "CLEAN_BROWSER_UNAVAILABLE"


def test_web_sanitizer_drops_closed_elements_and_non_allowlisted_attributes() -> None:
    sanitized = sanitize_html(
        '<header>chrome</header><main class="layout" lang="zh"><a href="/ok" onclick="bad()">Body</a>'
        '<iframe src="/bad">nested</iframe><img src="/image" data-secret="x"></main>'
    )
    assert "chrome" not in sanitized
    assert "iframe" not in sanitized
    assert "class=" not in sanitized
    assert "onclick=" not in sanitized
    assert "data-secret=" not in sanitized
    assert 'lang="zh"' in sanitized
    assert 'href="/ok"' in sanitized
    assert 'src="/image"' in sanitized


@pytest.mark.asyncio
async def test_web_llm_rewrite_sanitizes_before_injected_model_and_missing_model_fails() -> None:
    class _LLM:
        def __init__(self) -> None:
            self.text: str | None = None

        async def complete(self, *, prompt: str, text: str | None = None, **_kwargs: object) -> str:
            assert prompt == _PROMPT_TEXT
            self.text = text
            return f"rewritten: {text}"

    html = "<nav>skip</nav><article><script>bad()</script>Keep this</article>"
    llm = _LLM()
    result = await clean_web(
        html=html,
        strategy="web.llm_rewrite",
        capability="clean.extract.web_llm",
        llm=llm,
        prompt=_PROMPT,
    )
    assert llm.text == "Keep this"
    assert result.text == "rewritten: Keep this"
    assert result.evidence["strategy"] == "web.llm_rewrite"
    with pytest.raises(MkbError) as raised:
        await clean_web(html=html, strategy="web.llm_rewrite", capability="clean.extract.web_llm")
    assert raised.value.code == "CLEAN_LLM_UNAVAILABLE"
