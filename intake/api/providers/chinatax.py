"""Pure ChinaTax get_articles v1 parser and semantic mapper."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from src.contracts.common.ids import stable_digest
from src.contracts.intake.providers.chinatax import ChinaTaxEnvelope, ChinaTaxParsedMember, ChinaTaxRawMember
from src.contracts.intake.semantics import ContextMeta, FilterMeta, MappedProviderMember, semantic_tuples


def _optional_text(value: object) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def unpack_chinatax_envelope(envelope: ChinaTaxEnvelope) -> list[ChinaTaxRawMember]:
    raw = envelope.searchResultAll.searchTotal
    if raw is None:
        return []
    return list(raw) if isinstance(raw, list) else [raw]


def parse_chinatax_member(raw: ChinaTaxRawMember) -> MappedProviderMember:
    content_id = str(raw.id).strip()
    if not content_id:
        raise ValueError("ChinaTax content id must not be blank")
    parsed = ChinaTaxParsedMember(
        content_id=content_id,
        type=_optional_text(raw.label) or "unknown",
        channel=_optional_text(raw.column) or "unknown",
        title=_optional_text(raw.title),
        description=_optional_text(raw.content),
        link=_optional_text(raw.url),
        publisher=_optional_text(raw.pubName),
        source_name=_optional_text(raw.siteName),
        publish_date=_optional_text(raw.pubDate),
        cwrq_date=_optional_text(raw.cwrq),
        formulated_year=_optional_text(raw.xxgk_formulatedYear),
        effective_status=_optional_text(raw.xxgk_aging),
        effective_description=_optional_text(raw.xxgk_description),
        gov_doc=raw.govDoc,
        appendix=raw.appendix,
    )
    clean_text = "\n\n".join(part for part in (parsed.title, parsed.description) if part)
    filter_meta = FilterMeta(
        realm="tax_china",
        type=parsed.type,
        channel=parsed.channel,
        source_name="chinatax.gov.cn",
        is_active=1 if parsed.effective_status == "全文有效" else 0,
    )
    tags: list[str] = []
    for label, value in (
        ("发布单位", parsed.publisher),
        ("成文日期", parsed.cwrq_date),
        ("发布日期", parsed.publish_date),
        ("文件时效", parsed.effective_status),
    ):
        if value:
            tags.append(f"{label}: {value}")
    context_meta = ContextMeta(
        realm=filter_meta.realm,
        type=filter_meta.type,
        channel=filter_meta.channel,
        source_name=filter_meta.source_name,
        title=parsed.title or "无标题文件",
        tags=tags,
    )
    content_facts: Mapping[str, Any] = {
        "title": parsed.title,
        "description": parsed.description,
        "publisher": parsed.publisher,
        "publish_date": parsed.publish_date,
    }
    meta_facts: Mapping[str, Any] = {
        "effective_status": parsed.effective_status,
        "effective_description": parsed.effective_description,
    }
    return MappedProviderMember(
        provider="chinatax",
        operation="get_articles",
        definition_version="v1",
        external_key=content_id,
        clean_text=clean_text,
        parsed_payload=parsed.model_dump(mode="json"),
        content_digest=stable_digest(content_facts),
        meta_digest=stable_digest(meta_facts),
        filter_meta=filter_meta,
        context_meta=context_meta,
        semantic_tuples=semantic_tuples(filter_meta, context_meta),
        identity_evidence={
            "content_id": content_id,
            "formulated_year": parsed.formulated_year or "0000",
        },
    )


__all__ = ["parse_chinatax_member", "unpack_chinatax_envelope"]
