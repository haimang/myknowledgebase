"""FF-F6a-T04 (F6-02): HTML→text 去标签保正文 (stdlib html.parser).

先红后绿 ([Q7]): pre-F6a 的 3 正则桩把全文压成单行 (丢段落结构) 且不解码实体
(&amp; 残留) → 下列"保段落 + 实体解码"断言对桩为红, 对新实现为绿。
"""

from browser_runtime import extract_text

_HTML = (
    "<html><head><title>T</title><style>.x{color:red}</style></head><body>"
    "<h1>Heading One</h1>"
    "<p>First paragraph with <b>bold</b> &amp; entities.</p>"
    "<script>var leak='SHOULD_NOT_APPEAR';</script>"
    "<div>Second <span>nested</span> block.</div>"
    "</body></html>"
)


def test_no_residual_tags() -> None:
    out = extract_text(_HTML)
    assert "<" not in out and ">" not in out


def test_non_empty_and_drops_script_style() -> None:
    out = extract_text(_HTML)
    assert out.strip()
    assert "SHOULD_NOT_APPEAR" not in out
    assert "color:red" not in out


def test_entities_decoded() -> None:
    out = extract_text(_HTML)
    assert "&" in out and "&amp;" not in out


def test_preserves_paragraph_structure() -> None:
    out = extract_text(_HTML)
    # 多个块级元素 → 多段落 (换行分隔), 非压成单行。
    lines = [ln for ln in out.split("\n") if ln.strip()]
    assert len(lines) >= 3, lines
    assert any("First paragraph" in ln for ln in lines)
    assert any("Second" in ln and "nested" in ln for ln in lines)


def test_empty_input() -> None:
    assert extract_text("") == ""
