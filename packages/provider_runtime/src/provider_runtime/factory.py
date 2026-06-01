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
from vector_sqlite_vec import BruteForceVectorIndex, Vec0VectorIndex

from .mock_llm import MockLLMProvider
from .protocols import LLMProvider
from .real_provider import RealMLXEmbedder, RealMLXLLMProvider

# 外部厂商 (非本项目本地 MLX 方向): 构造即 fail-loud (本轮不接外部)。
_DEFERRED_VENDOR_LLM = {"openai", "anthropic", "gemini"}


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
    if provider == "mlx":
        # RWC-01: 本地 MLX 占位槽 — 构造 ok (路由已接), 推理延后 (调用时 fail-loud)。
        # 密钥构造注入 (非模块级全局, ⛔ gemini.ts:96-132 反例规避)。
        keys = [settings.llm_api_key] if settings.llm_api_key else None
        return RealMLXLLMProvider(model=settings.llm_model, api_keys=keys)
    if provider in _DEFERRED_VENDOR_LLM:
        _deferred("llm", provider)
    raise UnknownProviderError("llm", provider)


def make_embedder(settings: Settings | None = None) -> Embedder:
    """按 settings.embedder_provider 返回 Embedder。local-hash=LocalEmbedder(1024); 未知 raise。"""
    settings = settings or load_settings()
    provider = settings.embedder_provider
    if provider == "local-hash":
        return LocalEmbedder()
    if provider == "mlx":
        # RWC-02: 本地 MLX embedding 占位槽 (维度锁 1024); 推理延后, 调用时 fail-loud。
        return RealMLXEmbedder(model=settings.embedder_model)
    raise UnknownProviderError("embedder", provider)


def make_vector_index(settings: Settings | None = None) -> Any:
    """按 settings.vector_index 返回 VectorIndex。bruteforce=BruteForceVectorIndex; vec0=RW-D。"""
    settings = settings or load_settings()
    kind = settings.vector_index
    if kind == "bruteforce":
        return BruteForceVectorIndex()
    if kind == "vec0":
        # RWD-04: 真实 sqlite-vec 实现 (扩展不可载时其 query fail-loud; 离线 Linux 真跑在 macOS)。
        return Vec0VectorIndex()
    raise UnknownProviderError("vector_index", kind)
