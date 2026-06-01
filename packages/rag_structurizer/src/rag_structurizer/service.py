"""F6-04: structurize 真实结构化 (确定性规则化, 非 LLM — [Q3]/O2)。

输出带 schema 的结构化对象 (sections + context_meta 骨架 + schema_version), 替换
`text.split("\\n")` 朴素分段, 供 construct 消费层级结构。保留 `paragraphs` 兼容字段。
heading 启发式: markdown `#` / 数字编号 / 全大写短行 → section 边界。
"""

from __future__ import annotations

import json
import re

_MD_HEADING = re.compile(r"^(#{1,6})\s+(.*)$")
_NUM_HEADING = re.compile(r"^(\d+[.、)]\s+)(.+)$")


def _heading(line: str) -> tuple[int, str] | None:
    """返回 (level, heading_text) 或 None (非 heading)。"""
    md = _MD_HEADING.match(line)
    if md:
        return min(len(md.group(1)), 6), md.group(2).strip()
    num = _NUM_HEADING.match(line)
    if num:
        return 2, num.group(2).strip()
    # 全大写短行 (拉丁) 视为标题。
    if 0 < len(line) <= 60 and line == line.upper() and any(c.isalpha() for c in line):
        return 1, line.strip()
    return None


def structurize_text(text: str) -> dict:
    sections: list[dict] = []
    cur_heading, cur_level, cur_body = "", 0, []
    order = 0

    def flush() -> None:
        nonlocal order
        body = "\n".join(cur_body).strip()
        if cur_heading or body:
            sections.append(
                {"heading": cur_heading, "level": cur_level, "text": body, "order": order}
            )
            order += 1

    for raw in (text or "").split("\n"):
        line = raw.strip()
        if not line:
            continue
        head = _heading(line)
        if head is not None:
            flush()
            cur_heading, cur_level, cur_body = head[1], head[0], []
        else:
            cur_body.append(line)
    flush()

    # 兼容字段: paragraphs (从 sections 扁平展开)。
    paragraphs: list[str] = []
    for sec in sections:
        if sec["heading"]:
            paragraphs.append(sec["heading"])
        paragraphs.extend(p.strip() for p in sec["text"].split("\n") if p.strip())

    title = next((s["heading"] for s in sections if s["level"] == 1), "")
    return {
        "schema_version": "v1",
        "context_meta": {"title": title, "source_hint": ""},
        "sections": sections,
        "section_count": len(sections),
        "paragraphs": paragraphs,
        "paragraph_count": len(paragraphs),
    }


def _normalize_structured(data: dict, *, source_text: str) -> dict:
    """RWB-04: 把 LLM 返回的结构对象规整到 structurize 契约 (防御性回填漏返字段)。

    借 legacy summarizer.ts:260 的「响应漏返则用输入回填」思路。下游 construct 依赖
    sections/paragraphs/context_meta 形状, 故缺失字段必须补齐, 而非传播半成品。
    """
    sections = data.get("sections")
    if not isinstance(sections, list) or not sections:
        # LLM 未给 sections → 回填为单 section (source_text), 不丢内容。
        sections = [{"heading": "", "level": 0, "text": source_text.strip(), "order": 0}]
    norm_sections: list[dict] = []
    for i, sec in enumerate(sections):
        sec = sec if isinstance(sec, dict) else {}
        norm_sections.append(
            {
                "heading": str(sec.get("heading", "")),
                "level": int(sec.get("level", 0) or 0),
                "text": str(sec.get("text", "")),
                "order": int(sec.get("order", i) if str(sec.get("order", i)).lstrip("-").isdigit() else i),
            }
        )
    paragraphs = data.get("paragraphs")
    if not isinstance(paragraphs, list) or not paragraphs:
        paragraphs = []
        for sec in norm_sections:
            if sec["heading"]:
                paragraphs.append(sec["heading"])
            paragraphs.extend(p.strip() for p in sec["text"].split("\n") if p.strip())
    cmeta = data.get("context_meta")
    if not isinstance(cmeta, dict):
        cmeta = {}
    title = str(cmeta.get("title") or next((s["heading"] for s in norm_sections if s["level"] == 1), ""))
    return {
        "schema_version": str(data.get("schema_version", "v1")),
        "context_meta": {"title": title, "source_hint": str(cmeta.get("source_hint", ""))},
        "sections": norm_sections,
        "section_count": len(norm_sections),
        "paragraphs": [str(p) for p in paragraphs],
        "paragraph_count": len(paragraphs),
        "produced_by": "llm",
    }


def structurize_via_llm(text: str, provider, rendered_prompt: str) -> dict:  # noqa: ANN001
    """RWB-04 LLM 模式: prompt(已渲染)→provider.complete_json→解析→契约规整。

    非法 JSON / 空响应 → fail-loud (ValueError); 漏返字段经 _normalize_structured 防御性回填。
    provider 须满足 LLMProvider 协议 (mock 或真实, 本轮走 MockLLMProvider)。
    """
    try:
        result = provider.complete_json(rendered_prompt, schema=None)
        data = json.loads(result.text)
    except (json.JSONDecodeError, TypeError) as exc:
        raise ValueError(f"structurize_llm_invalid_json: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("structurize_llm_not_object")
    return _normalize_structured(data, source_text=text)
