"""F5-02: VectorIndex 接口抽象 + 退化暴力实现。

[Q1] 裁决=选项 A: vec0 本轮 **显式 degraded**——保留暴力 cosine 全表扫描,
但把相似度计算收敛到 `VectorIndex` 接口下, 使未来接真实 sqlite-vec 仅为局部
替换 (新增一个 Vec0VectorIndex 实现), 不影响上层 store/search。

本轮交付实现 = `BruteForceVectorIndex`: 在候选集上逐个算距离再排序, 性能随
数据量线性劣化 (接受的显式技术债, 见 FF-F5-closure §4)。
"""

from __future__ import annotations

import logging
import math
from typing import Protocol, runtime_checkable

logger = logging.getLogger("vector_sqlite_vec.index")

SUPPORTED_METRICS = ("cosine", "l2", "inner_product")


@runtime_checkable
class VectorIndex(Protocol):
    """向量相似度子层契约。real vec0 实现可整体替换本接口。"""

    backend: str

    def query(
        self,
        embedding: list[float],
        candidates: list[tuple[str, list[float]]],
        top_k: int,
    ) -> list[tuple[str, float]]:
        """对候选 (chunk_id, embedding) 按距离度量排序, 返回前 top_k 的 (chunk_id, score)。"""
        ...


def _cosine(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    limit = min(len(a), len(b))
    dot = sum(a[i] * b[i] for i in range(limit))
    norm_a = math.sqrt(sum(a[i] * a[i] for i in range(limit)))
    norm_b = math.sqrt(sum(b[i] * b[i] for i in range(limit)))
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return dot / (norm_a * norm_b)


def _inner_product(a: list[float], b: list[float]) -> float:
    if not a or not b:
        return 0.0
    limit = min(len(a), len(b))
    return sum(a[i] * b[i] for i in range(limit))


def _neg_l2(a: list[float], b: list[float]) -> float:
    # 返回 -欧氏距离: 越大越近, 与 cosine/inner_product 的"大=相似"语义一致, 便于统一排序。
    if not a or not b:
        return 0.0
    limit = min(len(a), len(b))
    return -math.sqrt(sum((a[i] - b[i]) ** 2 for i in range(limit)))


class BruteForceVectorIndex:
    """退化暴力相似度实现 ([Q1] degraded)。"""

    backend = "bruteforce-degraded"

    def __init__(self, distance_metric: str = "cosine") -> None:
        if distance_metric not in SUPPORTED_METRICS:
            # 未知 metric 显式 degraded 回退 cosine (不静默, ⛔1)。
            logger.warning(
                "vector_index degraded: unsupported distance_metric=%r "
                "reason=unsupported_metric_degraded_to_cosine",
                distance_metric,
            )
            distance_metric = "cosine"
        self.distance_metric = distance_metric

    def _score(self, a: list[float], b: list[float]) -> float:
        if self.distance_metric == "inner_product":
            return _inner_product(a, b)
        if self.distance_metric == "l2":
            return _neg_l2(a, b)
        return _cosine(a, b)

    def query(
        self,
        embedding: list[float],
        candidates: list[tuple[str, list[float]]],
        top_k: int,
    ) -> list[tuple[str, float]]:
        scored = [(chunk_id, self._score(embedding, emb)) for chunk_id, emb in candidates]
        scored.sort(key=lambda item: item[1], reverse=True)
        return scored[: max(top_k, 0)]
