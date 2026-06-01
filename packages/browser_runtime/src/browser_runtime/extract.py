"""F6-02: 健壮 HTML→text 去标签保正文 (替换 3 条正则桩)。

用 stdlib `html.parser`（不引入重依赖、无本地化障碍）: 丢弃 script/style/head 等
非正文节点, 在块级标签边界切段落, `convert_charrefs=True` 自动解码实体 (&amp;→&),
保留段落结构。正则桩对嵌套/属性/实体处理脆弱且把全文压成单行 (丢段落)。
"""

from __future__ import annotations

import re
from html.parser import HTMLParser

# 完全跳过其文本内容的节点。
_SKIP_TAGS = {"script", "style", "head", "noscript", "template", "svg", "title"}
# 块级标签: 其边界视为段落分隔。
_BLOCK_TAGS = {
    "p", "div", "br", "li", "ul", "ol", "tr", "table", "section", "article",
    "header", "footer", "nav", "aside", "blockquote", "pre", "hr",
    "h1", "h2", "h3", "h4", "h5", "h6",
}


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str | None] = []  # str=文本 token, None=段落分隔
        self._skip_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:  # noqa: ANN001
        if tag in _SKIP_TAGS:
            self._skip_depth += 1
        elif tag in _BLOCK_TAGS and self._skip_depth == 0:
            self.parts.append(None)

    def handle_endtag(self, tag: str) -> None:
        if tag in _SKIP_TAGS and self._skip_depth > 0:
            self._skip_depth -= 1
        elif tag in _BLOCK_TAGS and self._skip_depth == 0:
            self.parts.append(None)

    def handle_data(self, data: str) -> None:
        if self._skip_depth == 0:
            stripped = data.strip()
            if stripped:
                self.parts.append(stripped)


def extract_text(payload: str) -> str:
    parser = _TextExtractor()
    parser.feed(payload or "")
    parser.close()
    paragraphs: list[str] = []
    current: list[str] = []
    for tok in parser.parts:
        if tok is None:
            if current:
                paragraphs.append(" ".join(current))
                current = []
        else:
            current.append(tok)
    if current:
        paragraphs.append(" ".join(current))
    cleaned = (re.sub(r"[ \t]+", " ", p).strip() for p in paragraphs)
    return "\n".join(p for p in cleaned if p)
