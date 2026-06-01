"""F6-03: dedicated provider registry + chinatax 真实 ETL (替字符串前缀桩)。

chinatax handler 真发 HTTP 请求 (模块级 `fetch_api`, 测试可 monkeypatch 注入,
⛔6) → 解析为结构化 items → 合并为 cleaned 正文。非 2xx 抛 `ApiRequestError`
(对齐 legacy API_REQUEST_FAILED)。多 item 散射成多文档源属 scatter, 本轮合并
单 artifact (多文档散射 degraded, 见 workflow_clean F6-08)。domain/realestate
显式 degraded。
"""

from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request
from dataclasses import dataclass

logger = logging.getLogger("providers_dedicated")

_USER_AGENT = "SourceMindBot/1.0 (+https://sourcemind.local)"


class ApiRequestError(RuntimeError):
    """provider API 请求失败 (非 2xx / 连接 / 超时), 可重试分类。"""


class ProviderDegradedError(RuntimeError):
    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def fetch_api(url: str, *, timeout: float = 10.0) -> str:
    if not url:
        raise ApiRequestError("empty url")
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
            status = getattr(response, "status", None) or response.getcode()
            if status is None or not (200 <= int(status) < 300):
                raise ApiRequestError(f"non-2xx status {status} for {url}")
            charset = response.headers.get_content_charset() or "utf-8"
            return response.read().decode(charset, errors="ignore")
    except ApiRequestError:
        raise
    except urllib.error.HTTPError as exc:
        raise ApiRequestError(f"http error {exc.code} for {url}") from exc
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        raise ApiRequestError(f"api request failed for {url}: {exc}") from exc


def _parse_chinatax_items(raw: str) -> list[dict]:
    """解析 chinatax 响应 (JSON 列表/对象) → 结构化 items; 逐条失败跳过 + warning。"""
    items: list[dict] = []
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return items
    records = data if isinstance(data, list) else data.get("items") or data.get("data") or []
    if not isinstance(records, list):
        return items
    for rec in records:
        if not isinstance(rec, dict):
            logger.warning("chinatax skip non-dict item")
            continue
        title = (rec.get("title") or "").strip()
        if not title:
            logger.warning("chinatax skip item missing title")
            continue
        items.append(
            {
                "title": title,
                "description": (rec.get("description") or rec.get("summary") or "").strip(),
                "publisher": (rec.get("publisher") or "").strip(),
                "publish_date": (rec.get("publish_date") or rec.get("date") or "").strip(),
            }
        )
    return items


def chinatax_etl(url: str, *, fetch=None) -> str:  # noqa: ANN001
    """真发请求 → 解析 → 合并为 cleaned 正文 (单 artifact, scatter degraded)。"""
    raw = (fetch or fetch_api)(url)
    items = _parse_chinatax_items(raw)
    if not items:
        # 对齐 legacy ALERT: 空结果记 warning (不整体崩)。
        logger.warning("chinatax empty result ALERT url=%s reason=no_parsable_items", url)
    blocks: list[str] = []
    for it in items:
        block = it["title"]
        if it["description"]:
            block += "\n" + it["description"]
        meta = " · ".join(v for v in (it["publisher"], it["publish_date"]) if v)
        if meta:
            block += "\n(" + meta + ")"
        blocks.append(block)
    return "\n\n".join(blocks)


@dataclass
class ProviderSpec:
    name: str
    degraded: bool


class ProviderRegistry:
    """host → provider handler。可扩展; 未注册 host 返回 None (回退 universal)。"""

    def __init__(self) -> None:
        self._by_host: dict[str, object] = {}
        self._degraded: dict[str, str] = {}

    def register(self, host: str, handler) -> None:  # noqa: ANN001
        self._by_host[host] = handler

    def register_degraded(self, host: str, reason: str) -> None:
        self._degraded[host] = reason

    def handler_for_uri(self, canonical_uri: str):  # noqa: ANN001
        uri = canonical_uri or ""
        for host, reason in self._degraded.items():
            if host in uri:
                def _degraded(_uri, _r=reason):  # noqa: ANN001
                    raise ProviderDegradedError(_r)
                return _degraded
        for host, handler in self._by_host.items():
            if host in uri:
                return handler
        return None

    def list_providers(self) -> list[ProviderSpec]:
        specs = [ProviderSpec(name=h, degraded=False) for h in self._by_host]
        specs += [ProviderSpec(name=h, degraded=True) for h in self._degraded]
        return specs


def build_provider_registry() -> ProviderRegistry:
    reg = ProviderRegistry()
    reg.register("chinatax.gov.cn", lambda uri: chinatax_etl(uri))
    # [Q3] 多 provider 显式 degraded。
    reg.register_degraded("domain.example", "domain provider not supported this round")
    reg.register_degraded("realestate.example", "realestate provider not supported this round")
    return reg


_REGISTRY = build_provider_registry()


def maybe_clean_with_provider(canonical_uri: str, payload: str) -> str | None:
    """向后兼容入口: 命中 dedicated provider 则真 ETL, 否则 None (回退 universal)。

    真实 provider (chinatax) 忽略 payload, 自行真发请求。
    """
    handler = _REGISTRY.handler_for_uri(canonical_uri)
    if handler is None:
        return None
    return handler(canonical_uri)
