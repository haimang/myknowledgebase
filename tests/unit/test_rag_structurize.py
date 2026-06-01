"""FF-F6b-T01 (F6-04): structurize 输出结构化 schema (非裸 paragraphs).

先红后绿 ([Q7]): pre-F6b `structurize_text` 返回 `{paragraphs, paragraph_count}`
(无 sections/schema_version) → 下列 schema 断言红。
"""

from rag_structurizer import structurize_text


def test_returns_schema_not_bare_paragraphs() -> None:
    out = structurize_text("# Title\nbody line one\n## Sub\nmore body")
    assert out["schema_version"] == "v1"
    assert "sections" in out and "context_meta" in out
    assert out["section_count"] == len(out["sections"])


def test_heading_split() -> None:
    out = structurize_text("# Tax Guide\nintro text\n## Filing\nfile monthly")
    headings = [(s["heading"], s["level"]) for s in out["sections"]]
    assert ("Tax Guide", 1) in headings
    assert ("Filing", 2) in headings
    filing = next(s for s in out["sections"] if s["heading"] == "Filing")
    assert "file monthly" in filing["text"]


def test_context_meta_title_from_h1() -> None:
    out = structurize_text("# Main Title\nbody")
    assert out["context_meta"]["title"] == "Main Title"


def test_leading_body_before_heading_default_section() -> None:
    out = structurize_text("intro paragraph\n# H1\nbody")
    assert out["sections"][0]["level"] == 0
    assert "intro paragraph" in out["sections"][0]["text"]


def test_backward_compat_paragraphs_present() -> None:
    out = structurize_text("# H\nline")
    assert "paragraphs" in out and out["paragraph_count"] == len(out["paragraphs"])


def test_empty_input() -> None:
    out = structurize_text("")
    assert out["sections"] == [] and out["section_count"] == 0
