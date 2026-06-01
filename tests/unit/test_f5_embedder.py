"""FF-F5-T02 (F5-01): Embedder 维度约束 + 伪向量降级 fixture + 语义性质.

先红后绿 ([Q7]): pre-F5 HEAD 只有 SHA-256 `embed_text` (伪向量)、无 LocalEmbedder/
embed_text_fake/维度校验 → 本文件 import 即红。修复后: embed_text 委托本地小模型、
维度!=1024 raise、伪向量显式命名为 embed_text_fake、共词文本余弦更高。
(RWA-09: 维度由 1536 经 Q-RW-1 覆盖为 1024。)
"""

import math

import pytest

from rag_vectorizer import (
    DIMENSION,
    Embedder,
    LocalEmbedder,
    default_embedder,
    embed_text,
    embed_text_fake,
)


def _cos(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na and nb else 0.0


def test_dimension_is_1024() -> None:
    emb = embed_text("hello world")
    assert len(emb) == DIMENSION == 1024


def test_dimension_enforced_raises_on_mismatch() -> None:
    with pytest.raises(ValueError):
        embed_text("hello", dims=512)


def test_local_embedder_satisfies_protocol() -> None:
    le = LocalEmbedder()
    assert isinstance(le, Embedder)
    assert le.dimension == 1024
    assert le.name == "local-bow-hash-v1"
    assert len(le.embed("hello")) == 1024


def test_default_embedder_is_singleton() -> None:
    assert default_embedder() is default_embedder()


def test_deterministic() -> None:
    assert embed_text("the quick brown fox") == embed_text("the quick brown fox")


def test_l2_normalized() -> None:
    norm = math.sqrt(sum(v * v for v in embed_text("some content here")))
    assert abs(norm - 1.0) < 1e-9


def test_empty_text_zero_vector_no_crash() -> None:
    emb = embed_text("")
    assert len(emb) == 1024
    assert all(v == 0.0 for v in emb)


def test_semantic_shared_words_closer_than_unrelated() -> None:
    """语义性质: 共词文本余弦显著高于无关文本 (非 SHA 噪声)。"""
    base = embed_text("value added tax invoice filing for enterprises")
    related = embed_text("tax invoice filing rules")
    unrelated = embed_text("golden retriever puppy playing in the park")
    assert _cos(base, related) > _cos(base, unrelated) + 0.1


def test_embed_text_fake_is_pseudo_and_uncorrelated() -> None:
    """embed_text_fake 显式命名为非交付向量; 其语义性质应不成立 (SHA 噪声)。"""
    base = embed_text_fake("value added tax invoice filing")
    related = embed_text_fake("tax invoice filing rules")
    unrelated = embed_text_fake("golden retriever puppy park")
    # SHA 伪向量: related 不会显著高于 unrelated (与文本语义零关联)。
    assert not (_cos(base, related) > _cos(base, unrelated) + 0.1)
    assert len(base) == 1024
