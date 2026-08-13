"""ChinaTax get_articles v1 request, envelope, and member schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import Field

from src.contracts.common.models import StrictModel

EffectLevel = Literal[
    "文字政策解读",
    "法律",
    "行政法规",
    "国务院文件",
    "税务部门规章",
    "税务规范性文件",
    "财税文件",
    "其他文件",
    "工作通知",
    "政策指引",
]


class ChinaTaxGetArticlesRequest(StrictModel):
    pageSize: int = Field(default=10, ge=10)
    pageNum: int = Field(default=0, ge=0)
    xxgkEffectLevel: EffectLevel | None = None
    orderBy: Literal[4] = 4


class ChinaTaxRawMember(StrictModel):
    id: str | int
    label: str | None = None
    column: str | None = None
    title: str | None = None
    content: str | None = None
    url: str | None = None
    pubName: str | None = None
    siteName: str | None = None
    pubDate: str | None = None
    cwrq: str | None = None
    xxgk_formulatedYear: str | int | None = None
    xxgk_aging: str | None = None
    xxgk_description: str | None = None
    govDoc: dict[str, Any] | None = None
    appendix: list[Any] | None = None


class ChinaTaxSearchResult(StrictModel):
    searchTotal: ChinaTaxRawMember | list[ChinaTaxRawMember] | None = None


class ChinaTaxEnvelope(StrictModel):
    searchResultAll: ChinaTaxSearchResult


class ChinaTaxParsedMember(StrictModel):
    content_id: str = Field(min_length=1)
    type: str
    channel: str
    title: str | None
    description: str | None
    link: str | None
    publisher: str | None
    source_name: str | None
    publish_date: str | None
    cwrq_date: str | None
    formulated_year: str | None
    effective_status: str | None
    effective_description: str | None
    gov_doc: dict[str, Any] | None
    appendix: list[Any] | None


__all__ = ["ChinaTaxEnvelope", "ChinaTaxGetArticlesRequest", "ChinaTaxParsedMember", "ChinaTaxRawMember"]
