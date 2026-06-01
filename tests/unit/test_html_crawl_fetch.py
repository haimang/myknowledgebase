"""FF-F6a-T05 (F6-02): htmlCrawl 抓取 — UA/状态码/错误分类, 不回退把 URL 当正文.

先红后绿 ([Q7]): pre-F6a url 抓取裸 urlopen 且失败 `return source_uri` (⛔3) →
无错误分类、把 URL 当正文。新实现失败抛 UrlFetchError。
"""

import cleaners_universal.service as svc
import pytest
from cleaners_universal import UrlFetchError, html_crawl


def test_html_crawl_extracts_injected_html(monkeypatch) -> None:
    monkeypatch.setattr(
        svc, "fetch_url", lambda url, **kw: "<html><body><p>Hello World</p></body></html>"
    )
    assert html_crawl("https://x.example/doc") == "Hello World"


def test_html_crawl_propagates_fetch_error(monkeypatch) -> None:
    def boom(url, **kw):
        raise UrlFetchError(f"non-2xx status 404 for {url}")

    monkeypatch.setattr(svc, "fetch_url", boom)
    with pytest.raises(UrlFetchError):
        html_crawl("https://x.example/missing")


def test_html_crawl_no_url_as_payload_fallback(monkeypatch) -> None:
    """抓取失败绝不返回 URL 字符串当正文 (⛔3)。"""
    def boom(url, **kw):
        raise UrlFetchError("conn refused")

    monkeypatch.setattr(svc, "fetch_url", boom)
    with pytest.raises(UrlFetchError):
        result = html_crawl("https://internal.host/secret")
        assert "internal.host" not in (result or "")  # never reached


def test_html_crawl_empty_extraction_raises(monkeypatch) -> None:
    monkeypatch.setattr(svc, "fetch_url", lambda url, **kw: "<html><body></body></html>")
    with pytest.raises(UrlFetchError):
        html_crawl("https://x.example/empty")
