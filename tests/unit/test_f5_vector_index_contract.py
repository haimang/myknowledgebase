"""FF-F5-T04 (F5-02): VectorIndex 接口契约 + BruteForceVectorIndex 实现.

先红后绿 ([Q7]): pre-F5 HEAD 无 VectorIndex/BruteForceVectorIndex → import 即红。
修复后: BruteForceVectorIndex 满足 query 契约, 可被未来 vec0 实现替换。
"""

import logging

from vector_sqlite_vec import BruteForceVectorIndex, VectorIndex


def test_satisfies_protocol() -> None:
    idx = BruteForceVectorIndex()
    assert isinstance(idx, VectorIndex)
    assert idx.backend == "bruteforce-degraded"


def test_query_ranks_by_cosine() -> None:
    idx = BruteForceVectorIndex(distance_metric="cosine")
    q = [1.0, 0.0, 0.0]
    candidates = [
        ("near", [0.9, 0.1, 0.0]),
        ("far", [0.0, 0.0, 1.0]),
        ("mid", [0.6, 0.6, 0.0]),
    ]
    ranked = idx.query(q, candidates, top_k=3)
    assert [cid for cid, _ in ranked] == ["near", "mid", "far"]


def test_top_k_truncates() -> None:
    idx = BruteForceVectorIndex()
    cands = [(f"c{i}", [float(i), 1.0, 0.0]) for i in range(5)]
    assert len(idx.query([1.0, 1.0, 0.0], cands, top_k=2)) == 2


def test_inner_product_metric() -> None:
    idx = BruteForceVectorIndex(distance_metric="inner_product")
    q = [2.0, 0.0]
    ranked = idx.query(q, [("big", [3.0, 0.0]), ("small", [1.0, 0.0])], top_k=2)
    assert ranked[0][0] == "big"


def test_l2_metric() -> None:
    idx = BruteForceVectorIndex(distance_metric="l2")
    q = [0.0, 0.0]
    ranked = idx.query(q, [("close", [0.1, 0.1]), ("distant", [9.0, 9.0])], top_k=2)
    assert ranked[0][0] == "close"


def test_unsupported_metric_degrades_to_cosine_with_warning(caplog) -> None:
    with caplog.at_level(logging.WARNING, logger="vector_sqlite_vec.index"):
        idx = BruteForceVectorIndex(distance_metric="manhattan")
    assert idx.distance_metric == "cosine"
    assert any("unsupported_metric_degraded_to_cosine" in r.getMessage() for r in caplog.records)


def test_empty_candidates() -> None:
    assert BruteForceVectorIndex().query([1.0, 0.0], [], top_k=5) == []
