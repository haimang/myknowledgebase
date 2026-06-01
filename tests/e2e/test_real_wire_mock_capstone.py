"""RW-B / RWB-07: mock capstone — 文档→prompt→LLM(mock)→embed(1024)→search 语义命中.

证明 prompt 语义链**使用链真实发生** (assert_used_real_chain spy provider/embedder),
而非 fixture 短路。RWB-08 防假绿: mock 仅验「使用链发生 + 检索命中目标文」,
**non-delivery-quality** — 不断言语义质量等同真实 (MockLLM/LocalEmbedder 皆占位质量)。

真实质量须待 RW-C/provider charter 接入真实 MLX 模型; 本 capstone 不宣称 RAG 语义已交付。
"""

from __future__ import annotations

import json
from pathlib import Path

from provider_runtime import MockLLMProvider
from rag_constructor import build_section_chunks, summarize_via_llm, with_context_header
from rag_structurizer import structurize_via_llm
from rag_vectorizer import LocalEmbedder
from smind_config import render_prompt, sync_prompts_dir
from vector_sqlite_vec import VectorStore

from tests.fixtures.eval_corpus import load_eval_corpus
from tests.fixtures.primitives import SpyEmbedder, SpyLLMProvider, assert_used_real_chain
from tests.fixtures.sqlite_kernel import make_kernel_dbs

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def _authored_structured(doc) -> dict:  # noqa: ANN001
    """capstone 作者编写的 mock LLM 结构化响应 (单 section = 原文, 保留检索词)。"""
    return {
        "schema_version": "v1",
        "context_meta": {"title": doc.title, "source_hint": ""},
        "sections": [{"heading": doc.title, "level": 1, "text": doc.text, "order": 0}],
    }


def test_mock_capstone_document_to_search_hit() -> None:
    core, vec = make_kernel_dbs()
    sync_prompts_dir(
        core,
        {"structurize": "structurize.md", "summarize": "summarize.md"},
        prompts_dir=PROMPTS_DIR,
    )
    docs = load_eval_corpus(tmp_dir=".tmp/does-not-exist")
    target = next(d for d in docs if d.doc_id == "eval_tax_vat")

    # Pass 1: 预渲染 prompt + 作者 mock 响应 (structurize + 每 chunk summarize)。
    responses: dict[str, str] = {}
    for doc in docs:
        p_struct = render_prompt(
            core, None, "structurize", {"input_text": doc.text}, prompts_dir=PROMPTS_DIR
        )
        responses[p_struct] = json.dumps(_authored_structured(doc))
        for ch in build_section_chunks(_authored_structured(doc)["sections"]):
            p_sum = render_prompt(
                core,
                None,
                "summarize",
                {"section_path": ch.section_path, "chunk_text": ch.text},
                prompts_dir=PROMPTS_DIR,
            )
            responses[p_sum] = f"summary: {ch.text[:120]}"

    provider = SpyLLMProvider(MockLLMProvider(responses))
    embedder = SpyEmbedder(LocalEmbedder())
    store = VectorStore(vec, workspace_key="team_x")

    # Pass 2: 真实跑链路 (structurize_via_llm → chunk → summarize_via_llm → embed → upsert)。
    target_chunk_ids: set[str] = set()
    for doc in docs:
        p_struct = render_prompt(
            core, None, "structurize", {"input_text": doc.text}, prompts_dir=PROMPTS_DIR
        )
        structured = structurize_via_llm(doc.text, provider, p_struct)
        assert structured["produced_by"] == "llm"
        for ch in build_section_chunks(structured["sections"]):
            p_sum = render_prompt(
                core,
                None,
                "summarize",
                {"section_path": ch.section_path, "chunk_text": ch.text},
                prompts_dir=PROMPTS_DIR,
            )
            summary = summarize_via_llm(ch, provider, p_sum)
            channels = [
                ("original", with_context_header(ch, title=doc.title)),
                ("summary", summary),
            ]
            for channel, ctext in channels:
                cid = f"{doc.doc_id}:{ch.index}:{channel}"
                store.upsert_chunk(
                    chunk_id=cid,
                    team_id="team_x",
                    document_id=doc.doc_id,
                    namespace_id="ns_team_x",
                    embedding_model=embedder.name,
                    embedding=embedder.embed(ctext),
                )
                if doc.doc_id == target.doc_id:
                    target_chunk_ids.add(cid)

    # 检索: 用目标文的 query, top 命中必须属于目标文 (与干扰文 pet_dog 区分)。
    hits = store.search(
        embedding=embedder.embed(target.query),
        team_id="team_x",
        namespace_id="ns_team_x",
        embedding_model=embedder.name,
        top_k=5,
    )
    assert hits, "search returned no hits"
    assert hits[0]["chunk_id"] in target_chunk_ids, (
        f"top hit {hits[0]['chunk_id']} not in target doc chunks {target_chunk_ids}"
    )

    # RWB-08 防假绿: 证明 provider 与 embedder 被真实调用 (非 fixture 短路)。
    assert_used_real_chain(provider, embedder, min_calls=2)


def test_mock_capstone_embedding_is_1024() -> None:
    """capstone 链路的 embedding 维度锁 1024 (RWA-09 贯穿)。"""
    emb = LocalEmbedder()
    assert emb.dimension == 1024
    assert len(emb.embed("value added tax invoice")) == 1024
