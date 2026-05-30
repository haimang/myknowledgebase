from __future__ import annotations


def structurize_text(text: str) -> dict:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    if not paragraphs and text.strip():
        paragraphs = [text.strip()]
    return {"paragraphs": paragraphs, "paragraph_count": len(paragraphs)}

