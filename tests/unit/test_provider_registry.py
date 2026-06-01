"""FF-F6a-T07/T08 (F6-03): provider registry + chinatax 真实 ETL.

先红后绿 ([Q7]): pre-F6a `maybe_clean_with_provider` 只加 `[provider:chinatax]`
字符串前缀、不发请求 → 无真发请求/解析、无 registry。新实现真发请求(可注入)+解析。
"""

import json

import providers_dedicated.service as svc
import pytest
from providers_dedicated import (
    ApiRequestError,
    ProviderDegradedError,
    build_provider_registry,
    chinatax_etl,
)

_RESP = json.dumps(
    {
        "items": [
            {"title": "Article A", "description": "desc a", "publisher": "STA", "date": "2026-01-01"},
            {"title": "Article B", "summary": "sum b"},
            {"description": "no title -> skipped"},
        ]
    }
)


def test_chinatax_etl_parses_structured_items() -> None:
    out = chinatax_etl("https://chinatax.gov.cn/x", fetch=lambda url, **kw: _RESP)
    assert "Article A" in out and "desc a" in out
    assert "STA" in out and "2026-01-01" in out
    assert "Article B" in out
    # 无 title 的条目被跳过, 无字符串前缀桩残留。
    assert "[provider:chinatax]" not in out


def test_chinatax_etl_fetch_error_classified() -> None:
    def boom(url, **kw):
        raise ApiRequestError("non-2xx status 500")

    with pytest.raises(ApiRequestError):
        chinatax_etl("https://chinatax.gov.cn/x", fetch=boom)


def test_chinatax_etl_empty_result_no_crash() -> None:
    out = chinatax_etl("https://chinatax.gov.cn/x", fetch=lambda url, **kw: "[]")
    assert out == ""


def test_registry_routes_chinatax_and_degraded() -> None:
    reg = build_provider_registry()
    h = reg.handler_for_uri("https://chinatax.gov.cn/policy")
    assert h is not None
    # domain/realestate degraded handler 抛错。
    dg = reg.handler_for_uri("https://domain.example/x")
    with pytest.raises(ProviderDegradedError):
        dg("https://domain.example/x")
    # 未注册 host → None (回退 universal)。
    assert reg.handler_for_uri("https://other.example/x") is None


def test_maybe_clean_with_provider_real_etl(monkeypatch) -> None:
    monkeypatch.setattr(svc, "fetch_api", lambda url, **kw: _RESP)
    out = svc.maybe_clean_with_provider("https://chinatax.gov.cn/p", "ignored-payload")
    assert out is not None and "Article A" in out
    assert svc.maybe_clean_with_provider("https://nothing.example", "x") is None
