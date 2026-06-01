"""FF-F5-T05 (F5-03): search 增 namespace_id/embedding_model 过滤 + distance_metric 生效.

先红后绿 ([Q7]): pre-F5 HEAD store.search 仅 deleted_at + team_id 过滤 (G-CR3-10),
跨 namespace/model 混算 cosine; 且 distance_metric 硬编码 cosine。
修复后: 按 namespace_id/embedding_model 过滤候选集, distance_metric 读 namespace 配置。
"""

from tests.fixtures.sqlite_kernel import make_kernel_dbs
from vector_sqlite_vec import VectorStore

_EMB = [0.1, 0.9, 0.0, 0.0]


def _seed_ns(vec_conn, ns_id, team_id, model, metric="cosine") -> None:
    vec_conn.execute(
        """
        INSERT INTO vector_namespaces (
          id, team_id, namespace_key, embedding_model, embedding_dimension,
          distance_metric, status
        ) VALUES (?, ?, ?, ?, 1536, ?, 'active')
        """,
        (ns_id, team_id, ns_id, model, metric),
    )
    vec_conn.commit()


def test_embedding_model_filter_no_cross_model_mix() -> None:
    _, vec_conn = make_kernel_dbs()
    store = VectorStore(vec_conn, workspace_key="team_x")
    _seed_ns(vec_conn, "ns_a", "team_x", "model-a")
    _seed_ns(vec_conn, "ns_b", "team_x", "model-b")
    store.upsert_chunk(chunk_id="a1", team_id="team_x", namespace_id="ns_a",
                       embedding_model="model-a", embedding=_EMB)
    store.upsert_chunk(chunk_id="b1", team_id="team_x", namespace_id="ns_b",
                       embedding_model="model-b", embedding=_EMB)

    only_a = store.search(embedding=_EMB, team_id="team_x", embedding_model="model-a")
    assert {h["chunk_id"] for h in only_a} == {"a1"}, only_a
    # 不传 model → team-wide (向后兼容), 两个都在。
    both = store.search(embedding=_EMB, team_id="team_x")
    assert {h["chunk_id"] for h in both} == {"a1", "b1"}


def test_namespace_filter() -> None:
    _, vec_conn = make_kernel_dbs()
    store = VectorStore(vec_conn, workspace_key="team_x")
    _seed_ns(vec_conn, "ns_a", "team_x", "model-a")
    _seed_ns(vec_conn, "ns_b", "team_x", "model-a")
    store.upsert_chunk(chunk_id="a1", team_id="team_x", namespace_id="ns_a",
                       embedding_model="model-a", embedding=_EMB)
    store.upsert_chunk(chunk_id="b1", team_id="team_x", namespace_id="ns_b",
                       embedding_model="model-a", embedding=_EMB)
    hits = store.search(embedding=_EMB, team_id="team_x", namespace_id="ns_a")
    assert {h["chunk_id"] for h in hits} == {"a1"}


def test_distance_metric_read_from_namespace_config() -> None:
    """namespace 配置 inner_product → _resolve_metric 读出并生效 (非硬编码 cosine)。"""
    _, vec_conn = make_kernel_dbs()
    store = VectorStore(vec_conn, workspace_key="team_x")
    _seed_ns(vec_conn, "ns_ip", "team_x", "model-a", metric="inner_product")
    assert store._resolve_metric("ns_ip") == "inner_product"
    assert store._resolve_metric(None) == "cosine"
    # inner_product 下未归一长向量得分更高 (cosine 会归一抹除幅度差)。
    store.upsert_chunk(chunk_id="big", team_id="team_x", namespace_id="ns_ip",
                       embedding_model="model-a", embedding=[10.0, 0.0, 0.0, 0.0])
    store.upsert_chunk(chunk_id="small", team_id="team_x", namespace_id="ns_ip",
                       embedding_model="model-a", embedding=[1.0, 0.0, 0.0, 0.0])
    hits = store.search(embedding=[1.0, 0.0, 0.0, 0.0], team_id="team_x", namespace_id="ns_ip")
    assert hits[0]["chunk_id"] == "big", hits
