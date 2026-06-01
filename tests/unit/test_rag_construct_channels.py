"""FF-F6b-T03 (F6-05): construct chunk + summary 双通道 + 上下文头注入.

先红后绿 ([Q7]): pre-F6b 只有 `build_chunks(paragraphs)->list[str]` 单通道, 无
summary/section_chunks/context_header → import 即红。
"""

from rag_constructor import (
    Chunk,
    build_section_chunks,
    build_summary,
    with_context_header,
)


def _sections():
    return [
        {"heading": "Filing", "level": 2,
         "text": "Enterprises file monthly. Returns are due by the 15th.", "order": 0},
        {"heading": "", "level": 0, "text": "General note about deductions.", "order": 1},
    ]


def test_section_chunks_carry_section_path() -> None:
    chunks = build_section_chunks(_sections(), max_chars=500)
    assert chunks
    assert any(c.section_path == "Filing" for c in chunks)
    assert all(isinstance(c, Chunk) for c in chunks)


def test_summary_non_empty_and_uses_heading() -> None:
    chunks = build_section_chunks(_sections(), max_chars=500)
    filing = next(c for c in chunks if c.section_path == "Filing")
    summary = build_summary(filing)
    assert summary
    assert "Filing" in summary


def test_summary_empty_chunk_empty() -> None:
    assert build_summary(Chunk(text="", section_path="", index=0)) == ""


def test_context_header_injection() -> None:
    ch = Chunk(text="body content", section_path="Filing", index=0)
    out = with_context_header(ch, title="Tax Guide")
    assert out.startswith("[Tax Guide / Filing]")
    assert "body content" in out


def test_max_chars_secondary_split() -> None:
    long = " ".join(f"Sentence number {i} here." for i in range(40))
    chunks = build_section_chunks([{"heading": "S", "level": 1, "text": long, "order": 0}], max_chars=100)
    assert len(chunks) >= 2
    assert all(len(c.text) <= 160 for c in chunks)
