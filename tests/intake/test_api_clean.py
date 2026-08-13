"""Per-domain tests for intake/api provider mapping + scatter."""

from __future__ import annotations

from intake.api import clean_registered_api_members


def test_api_provider_maps_chinatax_shaped_records_into_scatter_members() -> None:
    members = [
        {
            "member_ordinal": 0,
            "external_key": "tax-1",
            "normalized_external_key": "tax-1",
            "raw_digest": "a" * 64,
            "raw_text": "ignored when body present",
            "title": "增值税公告",
            "body": "纳税人应当依法申报。",
            "type": "公告",
            "channel": "政策法规",
            "effective_status": "全文有效",
            "media_type": "text/plain",
        },
        {
            "member_ordinal": 1,
            "external_key": "tax-2",
            "normalized_external_key": "tax-2",
            "raw_digest": "b" * 64,
            "title": "废止通知",
            "content": "本文件已废止。",
            "effective_status": "全文失效",
            "media_type": "text/plain",
        },
    ]
    cleaned = clean_registered_api_members(members, provider="chinatax")
    assert len(cleaned) == 2
    assert "增值税公告" in cleaned[0].clean_text
    assert "纳税人应当依法申报" in cleaned[0].clean_text
    assert cleaned[0].evidence["provider"] == "chinatax"
    assert cleaned[0].evidence["is_active"] == 1
    assert cleaned[1].evidence["is_active"] == 0
    assert cleaned[1].ordinal == 1
