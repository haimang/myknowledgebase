"""RW-A / RWA-01: provider 协议层 (LLMProvider)。

照 HEAD 既有 `Embedder`(rag_vectorizer.embedder:29) / `VectorIndex`
(vector_sqlite_vec.vector_index:23) 的 Protocol 范式新增 `LLMProvider`。
借 legacy IAiProvider 双方法形状 (ai_schemas.ts:170-179): generateText/generateJson
→ {responseText, usage}; 不借 TS `Env` 注入风格 (TR-1 接口隔离, 工厂注入)。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class LLMResult:
    """LLM 调用结果: 文本 + 用量 (provider 无关形状)。"""

    text: str
    usage: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class LLMProvider(Protocol):
    """mock/live 同协议 (TR-1)。complete=自由文本; complete_json=结构化 JSON。"""

    name: str

    def complete(self, prompt: str, **opts: Any) -> LLMResult: ...

    def complete_json(
        self, prompt: str, schema: dict[str, Any] | None = None, **opts: Any
    ) -> LLMResult: ...
