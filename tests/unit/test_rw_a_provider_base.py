"""RW-A / RWA-08: provider 基座先红后绿 ([Q7]).

覆盖 RWA-01 协议 / RWA-02 工厂 / RWA-03 Settings / RWA-05 mock / RWA-09 维度 1024 /
RWA-04 装配注入 / RWA-06 corpus / RWA-07 使用链原语。

先红依据 (pre-RW-A HEAD): 无 provider_runtime 包 → import 即红; DIMENSION==1536;
SearchService 无 embedder 注入参数; Settings 无 provider 字段。
"""

from __future__ import annotations

import pytest

from provider_runtime import (
    LLMProvider,
    MockLLMProvider,
    MockResponseMissing,
    UnknownProviderError,
    make_embedder,
    make_llm,
    make_vector_index,
    prompt_key,
)
from rag_vectorizer import DIMENSION, LocalEmbedder, SearchService
from smind_config import Settings
from vector_sqlite_vec import BruteForceVectorIndex, VectorStore
from vector_sqlite_vec.store import EMBEDDING_DIMENSION

from tests.fixtures.eval_corpus import load_eval_corpus
from tests.fixtures.primitives import SpyEmbedder, SpyLLMProvider, assert_used_real_chain
from tests.fixtures.sqlite_kernel import make_kernel_dbs


# --- RWA-09: 维度 1024 全库一致 (跨包不变量) ---

def test_dimension_locked_1024_cross_package() -> None:
    assert DIMENSION == 1024
    assert EMBEDDING_DIMENSION == 1024
    assert DIMENSION == EMBEDDING_DIMENSION  # 跨包不变量: 写侧守卫与 embedder 维度必须一致


def test_write_side_dimension_guard_fail_loud() -> None:
    core_conn, vec_conn = make_kernel_dbs()
    store = VectorStore(vec_conn)
    with pytest.raises(ValueError, match="dimension"):
        store.upsert_chunk(chunk_id="c1", team_id="t1", embedding=[0.1, 0.2])  # 非 1024
    # 正确维度通过
    store.upsert_chunk(chunk_id="c2", team_id="t1", embedding=[0.0] * 1024)


# --- RWA-01: LLMProvider 协议 ---

def test_mock_satisfies_llm_provider_protocol() -> None:
    assert isinstance(MockLLMProvider({}), LLMProvider)


# --- RWA-05: MockLLMProvider 命中 / 未命中 fail-loud ---

def test_mock_llm_hit_by_raw_prompt() -> None:
    m = MockLLMProvider({"hello": "world"})
    assert m.complete("hello").text == "world"


def test_mock_llm_hit_by_hash_key() -> None:
    key = prompt_key("some long prompt text")
    m = MockLLMProvider({key: "resp"})
    assert m.complete("some long prompt text").text == "resp"


def test_mock_llm_miss_fail_loud() -> None:
    m = MockLLMProvider({})
    with pytest.raises(MockResponseMissing) as exc:
        m.complete("unseen prompt")
    assert exc.value.reason == "mock_llm_response_missing"


def test_mock_llm_complete_json_validates_json() -> None:
    m = MockLLMProvider({"p": '{"a": 1}'})
    assert m.complete_json("p").text == '{"a": 1}'
    bad = MockLLMProvider({"p": "not json"})
    with pytest.raises(ValueError):
        bad.complete_json("p")


# --- RWA-03: Settings 默认 mock/local/bruteforce ---

def test_settings_defaults_offline_mock() -> None:
    s = Settings()
    assert s.llm_provider == "mock"
    assert s.embedder_provider == "local-hash"
    assert s.vector_index == "bruteforce"
    assert s.llm_api_key is None  # key 预留备而不填 (Q-RW-7)


# --- RWA-02: 工厂选型 + 未知 fail-loud + 延后占位 ---

def test_factory_make_embedder_default_local() -> None:
    emb = make_embedder(Settings())
    assert isinstance(emb, LocalEmbedder)
    assert emb.dimension == 1024


def test_factory_make_llm_default_mock() -> None:
    assert isinstance(make_llm(Settings()), MockLLMProvider)


def test_factory_make_vector_index_default_bruteforce() -> None:
    assert isinstance(make_vector_index(Settings()), BruteForceVectorIndex)


def test_factory_unknown_provider_fail_loud() -> None:
    with pytest.raises(UnknownProviderError):
        make_embedder(Settings(embedder_provider="nope"))
    with pytest.raises(UnknownProviderError):
        make_llm(Settings(llm_provider="nope"))


def test_factory_deferred_mlx_not_implemented() -> None:
    with pytest.raises(NotImplementedError, match="provider charter"):
        make_embedder(Settings(embedder_provider="mlx"))
    with pytest.raises(NotImplementedError, match="provider charter"):
        make_llm(Settings(llm_provider="mlx"))


# --- RWA-04: 装配注入 — SearchService 接受注入的 embedder ---

def test_search_service_accepts_injected_embedder() -> None:
    core_conn, vec_conn = make_kernel_dbs()
    from storage_objects import FileSystemObjectStore
    import tempfile

    store = SearchService(
        core_conn,
        vec_conn,
        workspace_key="t1",
        object_store=FileSystemObjectStore(tempfile.mkdtemp()),
        embedder=make_embedder(Settings()),
    )
    assert store.embedder.name == "local-bow-hash-v1"
    # 写/查同 provider name (⛔3): 工厂 embedder 与默认 embedder 同名
    assert store.embedder.name == LocalEmbedder().name


# --- RWA-06: eval corpus 装载器 ---

def test_eval_corpus_loads_committed() -> None:
    docs = load_eval_corpus(tmp_dir=".tmp/does-not-exist")
    assert len(docs) >= 2
    ids = {d.doc_id for d in docs}
    assert "eval_tax_vat" in ids and "eval_pet_dog" in ids
    for d in docs:
        assert d.text and d.query and d.expected_fragment


# --- RWA-07: 使用链原语 (spy) 正/负例 ---

def test_assert_used_real_chain_positive_and_negative() -> None:
    spy_emb = SpyEmbedder(LocalEmbedder())
    spy_emb.embed("x")
    assert_used_real_chain(spy_emb)  # 调过 → 通过

    spy_llm = SpyLLMProvider(MockLLMProvider({"p": "r"}))
    with pytest.raises(AssertionError, match="假绿|did not"):
        assert_used_real_chain(spy_llm)  # 未调 → fail
    spy_llm.complete("p")
    assert_used_real_chain(spy_llm)  # 调过 → 通过
