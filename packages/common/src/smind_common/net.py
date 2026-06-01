"""共享 SSRF 守卫 (F6 follow-up: htmlCrawl/chinatax 外部抓取防内网穿透)。

仅允许 http/https; 拒绝 loopback / 私有 / 链路本地 / 元数据 主机 (基于主机名,
不做 DNS 解析 — 离线确定性, 拦住最常见 SSRF 目标)。供 cleaners_universal.fetch_url
与 providers_dedicated.fetch_api 调用。
"""

from __future__ import annotations

import ipaddress
from urllib.parse import urlsplit

_ALLOWED_SCHEMES = {"http", "https"}
_BLOCKED_HOSTNAMES = {"localhost", "metadata.google.internal", ""}


class UnsafeUrlError(ValueError):
    """url 指向不允许的 scheme 或内网/loopback 主机 (SSRF 防护)。"""


def assert_safe_url(url: str) -> None:
    parts = urlsplit(url or "")
    if parts.scheme.lower() not in _ALLOWED_SCHEMES:
        raise UnsafeUrlError(f"unsafe url scheme: {parts.scheme!r} (only http/https)")
    host = (parts.hostname or "").lower()
    if host in _BLOCKED_HOSTNAMES:
        raise UnsafeUrlError(f"unsafe url host: {host!r}")
    # 主机若是 IP 字面量, 拒绝私有/loopback/链路本地/保留段。
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        ip = None
    if ip is not None and (
        ip.is_private
        or ip.is_loopback
        or ip.is_link_local
        or ip.is_reserved
        or ip.is_unspecified
        or ip.is_multicast
    ):
        raise UnsafeUrlError(f"unsafe url host (internal ip): {host!r}")
