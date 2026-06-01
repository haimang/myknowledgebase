"""F6-04: structurize 真实结构化 (确定性规则化, 非 LLM — [Q3]/O2)。

输出带 schema 的结构化对象 (sections + context_meta 骨架 + schema_version), 替换
`text.split("\\n")` 朴素分段, 供 construct 消费层级结构。保留 `paragraphs` 兼容字段。
heading 启发式: markdown `#` / 数字编号 / 全大写短行 → section 边界。
"""

from __future__ import annotations

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
