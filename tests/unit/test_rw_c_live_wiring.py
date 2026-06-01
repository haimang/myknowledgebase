"""RW-C / RWC-01..04: live 接线脚手架 先红后绿 ([Q7]).

本轮 (reframe) 仅铺**可被真实接线的脚手架**: 退避/分类 (RWC-01) + 真实 provider 占位槽
(构造 ok / 推理延后) + 密钥构造注入脱敏 (RWC-03) + mock↔live 路由一致性 (RWC-04)。
真实 MLX 推理延后至 provider charter 且本离线 Linux 环境不可跑 → 占位调用 fail-loud。

先红依据: pre-RW-C 无 provider_runtime.retry / real_provider。
"""

from __future__ import annotations

import json

import pytest

from provider_runtime import (
    LLMProvider,
    LLMResult,
    MockLLMProvider,
    ProviderDeferredError,
    RealMLXEmbedder,
    RealMLXLLMProvider,
    is_retryable_error,
    make_embedder,
    make_llm,
    redact_secret,
    retry_with_backoff,
)
from rag_structurizer import structurize_via_llm
from smind_config import Settings


# --- RWC-01: 退避/重试 + 错误分类 ---

class _Status(Exception):
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code
        super().__init__(f"http {status_code}")


def test_is_retryable_classification() -> None:
    assert is_retryable_error(_Status(429)) is True
    assert is_retryable_error(_Status(503)) is True
    assert is_retryable_error(_Status(401)) is False
    assert is_retryable_error(_Status(422)) is False
    assert is_retryable_error(Exception("connection reset")) is True
    assert is_retryable_error(Exception("invalid api key")) is False
    assert is_retryable_error(Exception("some unknown error")) is False  # 保守默认不重试


def test_retry_recovers_after_transient() -> None:
    calls = {"n": 0}

    def flaky() -> str:
        calls["n"] += 1
        if calls["n"] < 3:
            raise _Status(429)
        return "ok"

    out = retry_with_backoff(flaky, sleep=lambda _d: None)
    assert out == "ok"
    assert calls["n"] == 3


def test_retry_non_retryable_immediate_raise() -> None:
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        raise _Status(401)

    with pytest.raises(_Status):
        retry_with_backoff(fn, sleep=lambda _d: None)
    assert calls["n"] == 1  # 不可重试 → 不重试


def test_retry_exhausts_and_raises() -> None:
    calls = {"n": 0}

    def fn() -> str:
        calls["n"] += 1
        raise _Status(503)

    with pytest.raises(_Status):
        retry_with_backoff(fn, max_retries=2, sleep=lambda _d: None)
    assert calls["n"] == 3  # 初次 + 2 重试


# --- RWC-01/02: 真实 provider 占位槽 (构造 ok / 推理延后) ---

def test_real_mlx_llm_constructs_defers_on_call() -> None:
    p = RealMLXLLMProvider(model="qwen2.5", api_keys=["sk-secret-123"])
    assert isinstance(p, LLMProvider)
    with pytest.raises(ProviderDeferredError) as exc:
        p.complete("x")
    assert exc.value.reason == "provider_adapter_deferred_Q-RW-2"


def test_real_mlx_embedder_dimension_locked_1024() -> None:
    e = RealMLXEmbedder(model="bge-large")
    assert e.dimension == 1024
    with pytest.raises(ProviderDeferredError):
        e.embed("x")


# --- RWC-03: 密钥构造注入 + 脱敏 (key 不入 repr/日志, Q-RW-7/TR-5) ---

def test_key_redacted_in_repr() -> None:
    secret = "sk-supersecret-abcdef"
    p = RealMLXLLMProvider(model="m", api_keys=[secret])
    assert secret not in repr(p)  # 攻击向量: 原始 key 不得出现在 repr/日志
    assert "***" in repr(p)
    assert redact_secret(secret).endswith("chars)")
    assert secret not in redact_secret(secret)


def test_factory_injects_key_via_constructor_not_global() -> None:
    # 构造注入 (非模块级全局轮转 ⛔ gemini.ts:96-132): key 经 Settings → 构造函数。
    p = make_llm(Settings(llm_provider="mlx", llm_api_key="sk-xyz", llm_model="m"))
    assert isinstance(p, RealMLXLLMProvider)
    assert "sk-xyz" not in repr(p)  # 不泄漏


# --- RWC-04: mock↔live 路由一致性 (FakeLive 替身证契约, 非真实质量) ---

class _FakeLiveProvider:
    """live 替身 (真实 MLX 不可在离线 Linux 跑): 实现 LLMProvider 协议, 返确定性结构化 JSON。

    仅证 mock↔live 在**契约/结构**上一致, 不代表真实语义质量 (non-delivery)。
    """

    name = "fake-live"

    def complete(self, prompt: str, **opts) -> LLMResult:  # noqa: ANN003
        return LLMResult(text="live summary", usage={"live": True})

    def complete_json(self, prompt, schema=None, **opts) -> LLMResult:  # noqa: ANN001, ANN003
        return LLMResult(
            text=json.dumps(
                {"schema_version": "v1", "sections": [{"heading": "H", "level": 1,
                 "text": "live body", "order": 0}]}
            ),
            usage={"live": True},
        )


def test_mock_live_structural_parity() -> None:
    prompt = "p"
    mock = MockLLMProvider(
        {prompt: json.dumps({"schema_version": "v1",
         "sections": [{"heading": "H", "level": 1, "text": "mock body", "order": 0}]})}
    )
    live = _FakeLiveProvider()
    assert isinstance(live, LLMProvider)
    out_mock = structurize_via_llm("src", mock, prompt)
    out_live = structurize_via_llm("src", live, prompt)
    # 结构一致 (键集 + section 形状), 文本内容不同 (质量层不比较)。
    assert out_mock.keys() == out_live.keys()
    assert out_mock["produced_by"] == out_live["produced_by"] == "llm"
    assert set(out_mock["sections"][0]) == set(out_live["sections"][0])
