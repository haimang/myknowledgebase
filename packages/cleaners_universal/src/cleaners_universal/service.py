"""F6-02: universal htmlCrawl 真实抓取清洗 (替正则桩 + 删 URL-当正文兜底)。

`fetch_url` 为模块级函数 (测试可 monkeypatch 注入真实响应样本, 不打外网, ⛔6);
htmlCrawl 失败按错误分类抛 `UrlFetchError` 交内核 fail_claim, 绝不回退把 URL
字符串当正文 (⛔3 / CR-6 R1)。
"""

from __future__ import annotations

import urllib.error
import urllib.request

from browser_runtime import extract_text

_USER_AGENT = "SourceMindBot/1.0 (+https://sourcemind.local)"


class UrlFetchError(RuntimeError):
    """url 抓取失败 (非 2xx / 连接 / 超时), 可重试分类 (对齐 legacy URL_FETCH_FAILED)。"""


def fetch_url(url: str, *, timeout: float = 10.0, user_agent: str = _USER_AGENT) -> str:
    if not url:
        raise UrlFetchError("empty url")
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status = getattr(response, "status", None) or response.getcode()
            if status is None or not (200 <= int(status) < 300):
                raise UrlFetchError(f"non-2xx status {status} for {url}")
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="ignore")
    except UrlFetchError:
        raise
    except urllib.error.HTTPError as exc:
        raise UrlFetchError(f"http error {exc.code} for {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise UrlFetchError(f"fetch failed for {url}: {exc}") from exc


def html_crawl(url: str) -> str:
    """抓取 url → 去标签保正文。失败 fail-loud (不回退把 URL 当正文)。"""
    html = fetch_url(url)
    text = extract_text(html)
    if not text.strip():
        raise UrlFetchError(f"empty content after extraction for {url}")
    return text


def clean_payload(source_kind: str, payload: str) -> str:
    """文本 branch (file/static/api): 直接 strip (非 HTML 源不去标签)。"""
    return (payload or "").strip()
