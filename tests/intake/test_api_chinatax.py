"""D08 ChinaTax operation witnesses through the real intake/API entry."""

from __future__ import annotations

from intake.api import clean_registered_api_members
from intake.api.registry import unpack_registered_api_envelope


def _raw() -> dict[str, object]:
    return {
        "id": "tax-2026-1",
        "label": "税务规范性文件",
        "column": "政策法规",
        "title": "增值税公告",
        "content": "纳税人应当依法申报。",
        "url": "https://example.test/tax-2026-1",
        "pubName": "国家税务总局",
        "pubDate": "2026-08-01",
        "cwrq": "2026-07-30",
        "xxgk_formulatedYear": "2026",
        "xxgk_aging": "全文有效",
        "xxgk_description": "现行有效",
        "govDoc": {"docNo": "1"},
        "appendix": [],
    }


def test_chinatax_raw_fixture_maps_fields_semantics_and_stable_dual_digest() -> None:
    raw = _raw()
    envelope = {"searchResultAll": {"searchTotal": [raw]}}
    unpacked = unpack_registered_api_envelope(
        envelope, provider="chinatax", operation="get_articles", definition_version="v1"
    )
    first = clean_registered_api_members(
        unpacked, provider="chinatax", operation="get_articles", definition_version="v1"
    )[0]
    repeated = clean_registered_api_members(
        [raw], provider="chinatax", operation="get_articles", definition_version="v1"
    )[0]

    assert first.external_key == "tax-2026-1"
    assert first.payload["content_id"] == "tax-2026-1"
    assert first.payload["type"] == "税务规范性文件"
    assert first.payload["channel"] == "政策法规"
    assert first.payload["description"] == "纳税人应当依法申报。"
    assert first.payload["effective_status"] == "全文有效"
    assert first.filter_meta == {
        "realm": "tax_china",
        "type": "税务规范性文件",
        "channel": "政策法规",
        "source_name": "chinatax.gov.cn",
        "is_active": 1,
    }
    assert "文件时效: 全文有效" in first.context_meta["tags"]
    assert {item["semantic_key"] for item in first.semantic_tuples} == {
        "realm",
        "type",
        "channel",
        "source_name",
        "is_active",
        "context_tags",
    }
    assert (first.external_key, first.content_digest, first.meta_digest) == (
        repeated.external_key,
        repeated.content_digest,
        repeated.meta_digest,
    )
