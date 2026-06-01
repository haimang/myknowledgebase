"""F6-05: construct chunk + summary 双通道 (确定性规则化, 非 LLM — [Q3]/O3)。

`build_section_chunks` 消费 structurize 的 sections (section 边界优先 + max_chars 二次
切分), 每 chunk 带 section_path; `build_summary` 产规则摘要 (heading + 首句/截断)。
保留 `build_chunks(paragraphs)` 向后兼容。layer-json 不产 (O1 degraded)。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

_SENT_SPLIT = re.compile(r"(?<=[.!?。！？])\s+")


@dataclass
class Chunk:
    text: str
    section_path: str
    index: int


def build_chunks(paragraphs: list[str], max_chars: int = 350) -> list[str]:
    """向后兼容: 段落贪心拼接 (≤ max_chars)。"""
    chunks: list[str] = []
    current: list[str] = []
    current_size = 0
    for paragraph in paragraphs:
        p = paragraph.strip()
        if not p:
            continue
        size = len(p) + 1
        if current and current_size + size > max_chars:
            chunks.append("\n".join(current))
            current = []
            current_size = 0
        current.append(p)
        current_size += size
    if current:
        chunks.append("\n".join(current))
    return chunks


def _split_body(body: str, max_chars: int) -> list[str]:
    """按句子边界聚合到 ≤ max_chars 的片段。"""
    body = body.strip()
    if not body:
        return []
    sentences = [s.strip() for s in _SENT_SPLIT.split(body) if s.strip()] or [body]
    pieces: list[str] = []
    cur: list[str] = []
    size = 0
    for sent in sentences:
        if cur and size + len(sent) + 1 > max_chars:
            pieces.append(" ".join(cur))
            cur, size = [], 0
        cur.append(sent)
        size += len(sent) + 1
    if cur:
        pieces.append(" ".join(cur))
    return pieces


def build_section_chunks(sections: list[dict], max_chars: int = 350) -> list[Chunk]:
    """section 边界优先 + max_chars 二次切分; 每 chunk 带 section_path。"""
    chunks: list[Chunk] = []
    idx = 0
    for sec in sections:
        path = (sec.get("heading") or "").strip()
        pieces = _split_body(sec.get("text") or "", max_chars)
        if not pieces and path:
            # 仅有标题、无正文 → 仍产一个以标题为内容的 chunk。
            pieces = [path]
        for piece in pieces:
            chunks.append(Chunk(text=piece, section_path=path, index=idx))
            idx += 1
    return chunks


def build_summary(chunk: Chunk, *, max_chars: int = 160) -> str:
    """规则摘要 (非 LLM): section_path + 首句/截断。"""
    body = chunk.text.strip()
    first = _SENT_SPLIT.split(body, maxsplit=1)[0].strip() if body else ""
    if chunk.section_path:
        summary = f"{chunk.section_path}: {first}".strip()
    else:
        summary = first
    return summary[:max_chars].strip()


def summarize_via_llm(chunk: Chunk, provider, rendered_prompt: str, *, max_chars: int = 160) -> str:  # noqa: ANN001
    """RWB-05 LLM 模式: prompt(已渲染)→provider.complete→截断。

    空响应回落规则摘要 (build_summary), 不产空串掩盖 (fail-soft 到规则, 非静默成功)。
    provider 须满足 LLMProvider 协议 (本轮 MockLLMProvider)。
    """
    result = provider.complete(rendered_prompt)
    text = (result.text or "").strip()
    if not text:
        return build_summary(chunk, max_chars=max_chars)
    return text[:max_chars].strip()


def with_context_header(chunk: Chunk, *, title: str = "") -> str:
    """original 通道上下文头注入 (语义锚点, 规则化 buildContentFull)。"""
    anchor = " / ".join(p for p in (title, chunk.section_path) if p)
    if anchor:
        return f"[{anchor}]\n{chunk.text}"
    return chunk.text
