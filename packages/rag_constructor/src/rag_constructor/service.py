from __future__ import annotations


def build_chunks(paragraphs: list[str], max_chars: int = 350) -> list[str]:
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

