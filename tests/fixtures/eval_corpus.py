"""RW-A / RWA-06: eval corpus 装载器 + 精简可提交样本集。

- `COMMITTED_CORPUS`: 进仓的精简语料 (≤数 KB), 供 mock capstone (RW-B) 端到端用。
  每条带 `query` + `expected_fragment`: 用该 query 检索应命中本文 (LocalEmbedder 词面
  重叠语义 → query 与目标文共词、与干扰文不共词)。
- `load_eval_corpus(tmp_dir)`: 合并 committed + 可选 `.tmp/eval-fixtures/*.json`
  (大样本 git-ignored, 缺失则仅返回 committed; 不 fail)。
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class EvalDoc:
    doc_id: str
    source_type: str  # "url" | "file"
    title: str
    text: str
    query: str
    expected_fragment: str


COMMITTED_CORPUS: list[EvalDoc] = [
    EvalDoc(
        doc_id="eval_tax_vat",
        source_type="url",
        title="Value Added Tax Invoice Filing",
        text=(
            "Value added tax invoice filing for enterprises follows a monthly cycle. "
            "Enterprises must submit the tax invoice filing declaration before the "
            "fifteenth day. Late value added tax filing incurs a penalty. The invoice "
            "filing rules require matching input and output invoices."
        ),
        query="tax invoice filing rules for enterprises",
        expected_fragment="invoice filing",
    ),
    EvalDoc(
        doc_id="eval_pet_dog",
        source_type="file",
        title="Golden Retriever Care",
        text=(
            "A golden retriever puppy playing in the park needs daily exercise. "
            "The dog enjoys fetching a ball and swimming in the lake. Grooming the "
            "golden retriever coat weekly keeps the fur healthy."
        ),
        query="golden retriever puppy park exercise",
        expected_fragment="golden retriever",
    ),
]


def load_eval_corpus(tmp_dir: str | Path = ".tmp/eval-fixtures") -> list[EvalDoc]:
    """返回 committed 语料 + 可选 .tmp 扩充集 (缺失则仅 committed, 不 fail)。"""
    docs = list(COMMITTED_CORPUS)
    base = Path(tmp_dir)
    if not base.is_dir():
        return docs
    for path in sorted(base.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        items = data if isinstance(data, list) else [data]
        for item in items:
            docs.append(
                EvalDoc(
                    doc_id=str(item["doc_id"]),
                    source_type=str(item.get("source_type", "file")),
                    title=str(item.get("title", "")),
                    text=str(item["text"]),
                    query=str(item.get("query", "")),
                    expected_fragment=str(item.get("expected_fragment", "")),
                )
            )
    return docs
