"""RW-D / RWD-04+05: 真实 vec0 (sqlite-vec) 先红后绿 ([Q7]).

owner 裁决: vec0 本轮真做 (写代码 + fake/skip 测); sqlite-vec 扩展在离线 Linux 装不上 →
真实 KNN 真跑在 owner macOS。本环境验: 不可用 fail-loud / 分数转换 / metric 降级 / 工厂槽;
RWD-05 vec0↔暴力 cosine 一致性回归用 skipif(扩展不可用) gate, 在 macOS 跑。

PDF (RWD-01/02/03) 本轮延后 (Q-RW-4; owner 后续 charter 指定 parser 库)。

先红依据: pre-RW-D 无 Vec0VectorIndex / sqlite_vec_available。
"""

from __future__ import annotations

import pytest

from provider_runtime import make_vector_index
from smind_config import Settings
from vector_sqlite_vec import (
    BruteForceVectorIndex,
    Vec0VectorIndex,
    sqlite_vec_available,
)
from vector_sqlite_vec.vector_index import VectorIndex

_VEC0 = sqlite_vec_available()


# --- RWD-04: 接口/工厂/分数转换/降级 (本环境可验, 不需扩展) ---

def test_vec0_satisfies_protocol() -> None:
    assert isinstance(Vec0VectorIndex(), VectorIndex)
    assert Vec0VectorIndex().backend == "vec0"


def test_factory_vec0_slot() -> None:
    idx = make_vector_index(Settings(vector_index="vec0"))
    assert isinstance(idx, Vec0VectorIndex)


def test_vec0_distance_to_score_cosine_and_l2() -> None:
    cos = Vec0VectorIndex("cosine")
    assert cos._distance_to_score(0.0) == pytest.approx(1.0)  # 完全相似
    assert cos._distance_to_score(1.0) == pytest.approx(0.0)
    l2 = Vec0VectorIndex("l2")
    assert l2._distance_to_score(2.5) == pytest.approx(-2.5)  # 越近(小d)分越高


def test_vec0_metric_degrade_to_cosine() -> None:
    # inner_product 非 vec0 原生 → 降级 cosine (不静默, 与 BruteForce 降级纪律一致)。
    idx = Vec0VectorIndex("inner_product")
    assert idx.distance_metric == "cosine"


def test_vec0_unavailable_fail_loud_on_offline() -> None:
    """离线 Linux: 扩展不可载 → query fail-loud (不静默退化; 退化由 schema.py [Q1] 决定)。"""
    if _VEC0:
        pytest.skip("sqlite-vec available (macOS): 不验 unavailable 路径")
    idx = Vec0VectorIndex()
    with pytest.raises(RuntimeError, match="sqlite_vec_unavailable"):
        idx.query([0.1] * 1024, [("a", [0.1] * 1024)], top_k=1)


# --- RWD-05: vec0 ↔ 暴力 cosine 一致性回归 (macOS gate; 离线 skip) ---

@pytest.mark.skipif(not _VEC0, reason="sqlite-vec 扩展不可载 (离线 Linux); 在 owner macOS 跑")
def test_vec0_bruteforce_parity_cosine() -> None:
    import random

    rng = random.Random(42)
    candidates = [
        (f"c{i}", [rng.uniform(-1, 1) for _ in range(1024)]) for i in range(20)
    ]
    query = [rng.uniform(-1, 1) for _ in range(1024)]
    bf = BruteForceVectorIndex("cosine").query(query, candidates, top_k=5)
    v0 = Vec0VectorIndex("cosine").query(query, candidates, top_k=5)
    # 一致性: top-k chunk_id 顺序一致 (换索引不串味)。
    assert [c for c, _ in bf] == [c for c, _ in v0]


@pytest.mark.skipif(not _VEC0, reason="sqlite-vec 扩展不可载 (离线 Linux); 在 owner macOS 跑")
def test_vec0_empty_candidates() -> None:
    assert Vec0VectorIndex().query([0.1] * 1024, [], top_k=5) == []
