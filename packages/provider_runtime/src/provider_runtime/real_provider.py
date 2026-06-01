"""RW-C / RWC-01..03: 真实 provider 占位槽 + 密钥构造注入脚手架。

本轮 (reframe): 只铺**可被真实接线的占位槽 + 路由通道**, 真实 MLX 推理延后至
provider charter (Q-RW-2)。占位 provider:
  - 构造**成功** (slot 已接入工厂路由, 可被 make_llm/make_embedder 返回);
  - 调用 (`complete`/`embed`) **fail-loud** `ProviderDeferredError` (机器可读 reason)。
密钥经**构造注入** (`api_keys`), 不用 legacy `gemini.ts:96-132` 的模块级全局轮转 (⛔);
`__repr__` 脱敏 (key 不入日志/repr, Q-RW-7/TR-5)。
"""

from __future__ import annotations

from typing import Any

from rag_vectorizer import DIMENSION

from .protocols import LLMResult


class ProviderDeferredError(NotImplementedError):
    """真实 provider 推理延后至 provider charter (调用时 fail-loud)。"""

    def __init__(self, what: str) -> None:
        self.reason = "provider_adapter_deferred_Q-RW-2"
        super().__init__(f"{what} deferred to provider charter (reason={self.reason})")


def redact_secret(value: str | None) -> str:
    """密钥脱敏 (日志/repr 安全): 仅留前 3 后 0 字符 + 掩码。"""
    if not value:
        return "<none>"
    return f"{value[:3]}***({len(value)} chars)"


class RealMLXLLMProvider:
    """本地 MLX LLM 占位槽 (Q-RW-2 方向=全本地 MLX; 实装延后)。

    构造注入 model + api_keys (本地 MLX 通常无需 key, 字段为厂商兼容预留)。
    """

    def __init__(
        self, *, model: str | None = None, api_keys: list[str] | None = None, **opts: Any
    ) -> None:
        self.name = f"mlx:{model}" if model else "mlx-llm"
        self._model = model
        self._api_keys = list(api_keys or [])  # 实例内持有, 非模块级全局 (⛔ 反例规避)
        self._opts = opts

    def __repr__(self) -> str:
        keys = ",".join(redact_secret(k) for k in self._api_keys) or "<none>"
        return f"RealMLXLLMProvider(model={self._model!r}, api_keys=[{keys}])"

    def complete(self, prompt: str, **opts: Any) -> LLMResult:
        raise ProviderDeferredError("real MLX LLM complete")

    def complete_json(
        self, prompt: str, schema: dict[str, Any] | None = None, **opts: Any
    ) -> LLMResult:
        raise ProviderDeferredError("real MLX LLM complete_json")


class RealMLXEmbedder:
    """本地 MLX embedding 占位槽 (维度锁 1024, Q-RW-1; 实装延后)。"""

    def __init__(self, *, model: str | None = None, dimension: int = DIMENSION) -> None:
        self.name = f"mlx:{model}" if model else "mlx-embedder"
        self.dimension = dimension
        self._model = model

    def __repr__(self) -> str:
        return f"RealMLXEmbedder(model={self._model!r}, dimension={self.dimension})"

    def embed(self, text: str) -> list[float]:
        raise ProviderDeferredError("real MLX embedding")
