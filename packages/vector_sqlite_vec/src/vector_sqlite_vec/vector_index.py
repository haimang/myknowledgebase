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


# -----------------------------------------------------------------------------
# RW-D / RWD-04: 真实 vec0 (sqlite-vec) 实现 — BruteForce 的"反向" (扩展可载即用)。
# 接口不变 (同 VectorIndex.query 候选式契约): 用 sqlite-vec 在内存 vec0 虚表上做 KNN,
# distance→score 转换对齐 BruteForce 排序语义 (larger=better) → RWD-05 一致性回归。
# 离线 Linux 无 sqlite-vec 扩展 → 不可载即 fail-loud; 真实 KNN 真跑在 owner macOS。
# -----------------------------------------------------------------------------

_VEC0_METRICS = ("cosine", "l2")  # vec0 原生; inner_product 不在本轮 vec0 覆盖 (用 bruteforce)


def sqlite_vec_available() -> bool:
    """探测 sqlite-vec 扩展是否可载 (离线 Linux 通常 False; macOS 装后 True)。"""
    try:
        import sqlite3

        import sqlite_vec  # type: ignore
    except ImportError:
        return False
    try:
        conn = sqlite3.connect(":memory:")
        conn.enable_load_extension(True)
        sqlite_vec.load(conn)
        conn.close()
        return True
    except Exception:  # noqa: BLE001 — 扩展不可载 (平台/编译) → 视为不可用
        return False


class Vec0VectorIndex:
    """真实 sqlite-vec (vec0) KNN 实现 (RWD-04)。接口与 BruteForceVectorIndex 一致。

    候选式契约下: 建内存 vec0 虚表 → 插候选 → `embedding MATCH ? ORDER BY distance LIMIT k`
    → distance 转 score (cosine: 1-d; l2: -d) 对齐 BruteForce 排序。扩展不可载即 fail-loud
    (不静默退化; 退化由上层 schema.py [Q1] 决定回 BruteForce)。
    """

    backend = "vec0"

    def __init__(self, distance_metric: str = "cosine") -> None:
        if distance_metric not in _VEC0_METRICS:
            logger.warning(
                "vec0 index: metric=%r not natively supported, degrading to cosine "
                "reason=vec0_metric_degraded_to_cosine",
                distance_metric,
            )
            distance_metric = "cosine"
        self.distance_metric = distance_metric

    def _distance_to_score(self, distance: float) -> float:
        # 对齐 BruteForce: larger=better。cosine distance=1-sim → score=1-d=sim; l2 → -d。
        if self.distance_metric == "l2":
            return -distance
        return 1.0 - distance

    def query(
        self,
        embedding: list[float],
        candidates: list[tuple[str, list[float]]],
        top_k: int,
    ) -> list[tuple[str, float]]:
        import sqlite3

        if not sqlite_vec_available():  # 离线 Linux: 扩展不可导入/不可载 → fail-loud
            raise RuntimeError(
                "vec0 unavailable: sqlite_vec extension not loadable "
                "(reason=sqlite_vec_unavailable; real KNN runs on macOS)"
            )
        import sqlite_vec  # type: ignore

        if not candidates or top_k <= 0:
            return []
        dim = len(embedding)
        conn = sqlite3.connect(":memory:")
        try:
            conn.enable_load_extension(True)
            sqlite_vec.load(conn)
            conn.enable_load_extension(False)
            conn.execute(
                f"CREATE VIRTUAL TABLE knn USING vec0("
                f"embedding float[{dim}] distance_metric={self.distance_metric})"
            )
            id_by_rowid: dict[int, str] = {}
            for i, (chunk_id, emb) in enumerate(candidates):
                id_by_rowid[i] = chunk_id
                conn.execute(
                    "INSERT INTO knn(rowid, embedding) VALUES (?, ?)",
                    (i, sqlite_vec.serialize_float32(emb)),
                )
            rows = conn.execute(
                "SELECT rowid, distance FROM knn WHERE embedding MATCH ? "
                "ORDER BY distance LIMIT ?",
                (sqlite_vec.serialize_float32(embedding), top_k),
            ).fetchall()
            return [(id_by_rowid[r[0]], self._distance_to_score(r[1])) for r in rows]
        finally:
            conn.close()
