"""RW-A / RWA-05: MockLLMProvider — 确定性 mock LLM (legacy 无 mock 层, 净新)。

按 prompt 查预置响应表, 未命中 **fail-loud** (MockResponseMissing, 机器可读 reason,
TR-4)。non-delivery-quality: 仅验使用链/结构, 不冒充真实语义质量 (§8.5 防假绿)。
"""

from __future__ import annotations

import json
from hashlib import sha256
from pathlib import Path
from typing import Any

from .protocols import LLMResult


class MockResponseMissing(RuntimeError):
    """mock LLM 未命中预置响应 — fail-loud (禁止静默返回空冒充成功)。"""

    def __init__(self, key: str, prompt_preview: str) -> None:
        self.key = key
        self.reason = "mock_llm_response_missing"
        super().__init__(
            f"{self.reason}: no preset response for key={key} "
            f"(prompt_preview={prompt_preview!r})"
        )


def prompt_key(prompt: str) -> str:
    """prompt → 稳定短哈希 key (供预置响应表索引)。"""
    return sha256(prompt.encode("utf-8")).hexdigest()[:16]


class MockLLMProvider:
    """确定性 mock LLM。

    命中优先级: prompt 原文 key > prompt sha256 短哈希 key。
    responses: {key 或 prompt 原文 -> 响应文本}; 亦可从 JSON 文件加载。
    """

    name = "mock-llm-v1"

    def __init__(
        self,
        responses: dict[str, str] | None = None,
        *,
        responses_path: str | None = None,
    ) -> None:
        self._responses: dict[str, str] = dict(responses or {})
        if responses_path:
            data = json.loads(Path(responses_path).read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError(f"mock responses file must be a JSON object: {responses_path}")
            self._responses.update({str(k): str(v) for k, v in data.items()})

    def _lookup(self, prompt: str) -> str:
        if prompt in self._responses:
            return self._responses[prompt]
        key = prompt_key(prompt)
        if key in self._responses:
            return self._responses[key]
        raise MockResponseMissing(key, prompt[:80])

    def complete(self, prompt: str, **opts: Any) -> LLMResult:
        text = self._lookup(prompt)
        return LLMResult(text=text, usage={"mock": True, "provider": self.name})

    def complete_json(
        self, prompt: str, schema: dict[str, Any] | None = None, **opts: Any
    ) -> LLMResult:
        text = self._lookup(prompt)
        # 结构层校验: 必须是合法 JSON (未命中或非法 JSON 均 fail-loud); 不校验 schema 语义。
        json.loads(text)
        return LLMResult(text=text, usage={"mock": True, "provider": self.name})
