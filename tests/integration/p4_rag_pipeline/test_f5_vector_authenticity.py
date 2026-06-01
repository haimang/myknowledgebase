"""FF-F5-T01 (F5-01): 向量真实性 spike — 相关 query 目标 chunk 排第一且分差显著.

先红后绿 ([Q7]): pre-F5 HEAD 用 SHA-256 伪向量, 实测 3 对样本目标 chunk 均
未排第一 (margin ~0.02 噪声, 见 closure §2 红基线); 接本地小模型后全部排第一
且 margin ≥ 阈值。写/查共用同一 Embedder (⛔3)。
"""

from rag_vectorizer import default_embedder, embed_text, embed_text_fake
from tests.fixtures.sqlite_kernel import make_kernel_dbs
from vector_sqlite_vec import VectorStore

# 三组主题互斥的 chunk + 各自相关 query (词面相关, 非自命中)。
CHUNKS = {
    "tax": "value added tax invoice rules for enterprises filing monthly returns",
    "dog": "the golden retriever puppy played happily in the green park all afternoon",
    "code": "python list comprehension iterates over a sequence building a new list",
}
PAIRS = [
    ("tax", "how to file a tax invoice return"),
    ("dog", "a puppy playing in the park"),
    ("code", "iterate over a sequence to build a new list in python"),
]
MARGIN = 0.1


def _seed_store():
    _, vec_conn = make_kernel_dbs()
    store = VectorStore(vec_conn, workspace_key="team_x")
    for cid, text in CHUNKS.items():
        # 写入侧用交付 embedder (与查询侧一致)。
        store.upsert_chunk(
            chunk_id=cid,
            team_id="team_x",
            namespace_id="ns_team_x",
            embedding_model=default_embedder().name,
            embedding=embed_text(text),
        )
    return store


def test_relevant_chunk_ranks_first_with_margin() -> None:
    store = _seed_store()
    for target, query in PAIRS:
        hits = store.search(
            embedding=embed_text(query),
            team_id="team_x",
            embedding_model=default_embedder().name,
        )
        assert hits[0]["chunk_id"] == target, f"{query!r} -> {hits}"
        margin = hits[0]["score"] - hits[1]["score"]
        assert margin >= MARGIN, f"{query!r} margin {margin:.3f} < {MARGIN}"


def test_fake_embedding_does_not_rank_all_first() -> None:
    """对照 (先红依据): SHA 伪向量做查询向量无法让全部目标排第一。"""
    store = _seed_store()  # 写入仍是真实向量
    all_first = True
    for target, query in PAIRS:
        # 查询侧故意用伪向量 → 写/查实现不一致, 命中退化为噪声。
        hits = store.search(
            embedding=embed_text_fake(query),
            team_id="team_x",
            embedding_model=default_embedder().name,
        )
        all_first &= hits[0]["chunk_id"] == target
    assert not all_first, "fake-embedding query unexpectedly ranked all targets first"
