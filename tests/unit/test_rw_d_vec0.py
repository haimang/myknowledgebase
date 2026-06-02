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


# -----------------------------------------------------------------------------
# 复审回应 R1 / R2: VectorStore 接 Settings.vector_index + 持久 vec0 错配地雷守卫。
# -----------------------------------------------------------------------------

from vector_sqlite_vec import VectorStore  # noqa: E402

from tests.fixtures.sqlite_kernel import make_kernel_dbs  # noqa: E402


def _upsert(store: VectorStore, chunk_id: str, vec: list[float]) -> None:
    store.upsert_chunk(
        chunk_id=chunk_id,
        team_id="team_x",
        document_id="doc_x",
        namespace_id="ns_team_x",
        embedding_model="local-bow-hash-v1",
        embedding=vec,
    )


def test_store_default_bruteforce_search_works() -> None:
    """R1 回归: 默认 vector_index=bruteforce, 写查路径不变 (零回归)。"""
    _core, vec = make_kernel_dbs()
    store = VectorStore(vec, workspace_key="team_x")  # 默认 bruteforce
    _upsert(store, "a", [1.0] + [0.0] * 1023)
    _upsert(store, "b", [0.0, 1.0] + [0.0] * 1022)
    hits = store.search(
        embedding=[1.0] + [0.0] * 1023,
        team_id="team_x",
        namespace_id="ns_team_x",
        embedding_model="local-bow-hash-v1",
        top_k=2,
    )
    assert hits and hits[0]["chunk_id"] == "a"


def test_store_honors_vector_index_vec0_setting() -> None:
    """R1 核心: Settings.vector_index='vec0' 现在**真的生效**于 store.search。

    离线 Linux (无扩展): 选 vec0 → 候选式 Vec0VectorIndex.query → fail-loud
    (sqlite_vec_unavailable), 而非旧行为『静默用 BruteForce』(死配置)。
    macOS (有扩展): 真实 KNN, 返回命中。
    """
    _core, vec = make_kernel_dbs()
    store = VectorStore(vec, workspace_key="team_x", vector_index="vec0")
    _upsert(store, "a", [1.0] + [0.0] * 1023)
    if _VEC0:
        hits = store.search(
            embedding=[1.0] + [0.0] * 1023,
            team_id="team_x",
            namespace_id="ns_team_x",
            embedding_model="local-bow-hash-v1",
            top_k=1,
        )
        assert hits and hits[0]["chunk_id"] == "a"
    else:
        with pytest.raises(RuntimeError, match="sqlite_vec_unavailable"):
            store.search(
                embedding=[1.0] + [0.0] * 1023,
                team_id="team_x",
                namespace_id="ns_team_x",
                embedding_model="local-bow-hash-v1",
                top_k=1,
            )


def test_store_fail_loud_when_index_is_native_vec0_table() -> None:
    """R2 核心: 持久 chunk_embedding_index 若为真实 vec0 虚表, JSON 读写与之不兼容,

    须 fail-loud (不静默写坏/读崩)。本环境无扩展不能真建 vec0 虚表, 故用一张
    sqlite_master.sql 含 'vec0' 字面的表模拟探测命中 (等价于扩展被载入后的错配态)。
    """
    _core, vec = make_kernel_dbs()
    store = VectorStore(vec, workspace_key="team_x")
    vec.execute("DROP TABLE chunk_embedding_index")
    # 模拟真实 vec0 虚表的 sqlite_master.sql 特征 (含 'vec0'); 不需真扩展即可触发探测。
    vec.execute(
        "CREATE TABLE chunk_embedding_index "
        "(rowid INTEGER PRIMARY KEY, embedding BLOB, _marker TEXT DEFAULT 'using vec0')"
    )
    vec.commit()
    assert store._embedding_index_is_native_vec0() is True
    with pytest.raises(RuntimeError, match="vec0_native_store_unimplemented"):
        _upsert(store, "a", [0.1] * 1024)
