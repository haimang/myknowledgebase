"""RW-A / RWA-02: provider 工厂 — 按 Settings 选实现, 未知 fail-loud。

复用 `providers_dedicated.ProviderRegistry`(service.py:114-151) 的分发范式 (纯函数,
无全局可变状态)。默认 mock/local-hash/bruteforce → 零配置即离线可跑、不打外网 (TR-5)。
真实 provider adapter (本地 MLX / 外部厂商) 延后至后续 provider charter (Q-RW-2);
工厂在此留 `NotImplementedError` 占位槽 + 机器可读 reason。
"""

from __future__ import annotations

from typing import Any

from rag_vectorizer import Embedder, LocalEmbedder
from smind_config import Settings, load_settings
from vector_sqlite_vec import BruteForceVectorIndex

from .mock_llm import MockLLMProvider
from .protocols import LLMProvider

# 延后至 provider charter 的真实 provider 枚举 (占位槽; RW-C/后续实装)。
_DEFERRED_LLM = {"mlx", "openai", "anthropic", "gemini"}
_DEFERRED_EMBEDDER = {"mlx"}


class UnknownProviderError(ValueError):
    """未知 provider 选型 — fail-loud (⛔ 不静默回退默认)。"""

    def __init__(self, kind: str, value: str) -> None:
        super().__init__(f"unknown {kind} provider: {value!r}")


def _deferred(kind: str, value: str) -> None:
    raise NotImplementedError(
        f"{kind} provider {value!r} deferred to provider charter "
        f"(reason=provider_adapter_deferred_Q-RW-2)"
    )


def make_llm(settings: Settings | None = None, **kwargs: Any) -> LLMProvider:
    """按 settings.llm_provider 返回 LLMProvider。mock=MockLLMProvider; 未知 raise。

    kwargs 透传给 MockLLMProvider (如 responses / responses_path)。
    """
    settings = settings or load_settings()
    provider = settings.llm_provider
    if provider == "mock":
        # real-wiring 路由 mock 侧: 预置响应可由 Settings 文件路径注入 (或 kwargs 直传)。
        if "responses_path" not in kwargs and settings.mock_llm_responses_path:
            kwargs["responses_path"] = settings.mock_llm_responses_path
        return MockLLMProvider(**kwargs)
    if provider in _DEFERRED_LLM:
        _deferred("llm", provider)
    raise UnknownProviderError("llm", provider)


def make_embedder(settings: Settings | None = None) -> Embedder:
    """按 settings.embedder_provider 返回 Embedder。local-hash=LocalEmbedder(1024); 未知 raise。"""
    settings = settings or load_settings()
    provider = settings.embedder_provider
    if provider == "local-hash":
        return LocalEmbedder()
    if provider in _DEFERRED_EMBEDDER:
        _deferred("embedder", provider)
    raise UnknownProviderError("embedder", provider)


def make_vector_index(settings: Settings | None = None) -> Any:
    """按 settings.vector_index 返回 VectorIndex。bruteforce=BruteForceVectorIndex; vec0=RW-D。"""
    settings = settings or load_settings()
    kind = settings.vector_index
    if kind == "bruteforce":
        return BruteForceVectorIndex()
    if kind == "vec0":
        # RW-D 实装 Vec0VectorIndex; 在此前为占位 (sqlite-vec 离线不可用)。
        _deferred("vector_index", kind)
    raise UnknownProviderError("vector_index", kind)
