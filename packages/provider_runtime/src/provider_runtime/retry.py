"""RW-C / RWC-01: provider 无关的退避/重试 + 错误分类 (借算法, 非 Cloudflare binding)。

借 legacy `rag-vectorizer/vectorizer/embedder.ts:40-42,115-164` 的指数退避
(MAX_RETRIES=3 / INITIAL_DELAY=1s / BACKOFF=2) 与 `:73-79` 的 `isRetryableError`
启发式 (429/timeout/overload/connection→可重试; 401/422/auth→不可重试)。
provider 无关、纯算法, 真实/mock client 均可复用。`sleep` 可注入 (测试零等待)。
"""

from __future__ import annotations

import time
from typing import Callable, TypeVar

T = TypeVar("T")

MAX_RETRIES = 3
INITIAL_DELAY = 1.0
BACKOFF = 2.0

# 可重试 / 不可重试标记 (借 isRetryableError 启发式; 真实 client 可按 status_code 精确化)。
_RETRYABLE_MARKERS = ("429", "timeout", "timed out", "overload", "connection", "503", "502")
_NON_RETRYABLE_MARKERS = ("401", "403", "422", "invalid api key", "unauthorized", "bad request")


def is_retryable_error(exc: BaseException) -> bool:
    """错误分类: 优先看 status_code 属性, 否则按消息启发式。默认**不**可重试 (保守)。"""
    status = getattr(exc, "status_code", None)
    if isinstance(status, int):
        if status in (401, 403, 422, 400):
            return False
        if status == 429 or 500 <= status < 600:
            return True
    msg = str(exc).lower()
    if any(m in msg for m in _NON_RETRYABLE_MARKERS):
        return False
    return any(m in msg for m in _RETRYABLE_MARKERS)


def retry_with_backoff(
    fn: Callable[[], T],
    *,
    max_retries: int = MAX_RETRIES,
    initial_delay: float = INITIAL_DELAY,
    backoff: float = BACKOFF,
    is_retryable: Callable[[BaseException], bool] = is_retryable_error,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """指数退避重试。可重试错误重试至 max_retries; 不可重试错误立即抛 (fail-fast)。

    末次仍失败则抛原异常。`sleep` 注入便于测试 (传 lambda _: None 零等待)。
    """
    delay = initial_delay
    last_exc: BaseException | None = None
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except BaseException as exc:  # noqa: BLE001 — 由 is_retryable 决定去留
            last_exc = exc
            if attempt >= max_retries or not is_retryable(exc):
                raise
            sleep(delay)
            delay *= backoff
    assert last_exc is not None  # 不可达 (循环必 return 或 raise)
    raise last_exc
