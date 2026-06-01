"""RW-B / RWB-08: prompt SSOT + 语义链去桩 先红后绿 ([Q7]).

覆盖 RWB-02 渲染+digest 对账 / RWB-03 seed+SSOT / RWB-04 structurize LLM 模式 /
RWB-05 summary LLM 模式 / RWB-06 clean geminiUnderstanding LLM 模式。

先红依据 (pre-RW-B HEAD): 无 smind_config.render_prompt/seed_prompt_version → import 红;
structurize_via_llm/summarize_via_llm 不存在; build_default_registry 不接受 llm 参数。
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from provider_runtime import MockLLMProvider
from rag_constructor import Chunk, summarize_via_llm
from rag_structurizer import structurize_via_llm
from smind_config import (
    PromptError,
    compute_digest,
    render_prompt,
    seed_prompt_version,
    sync_prompts_dir,
)
from smind_config.prompt_renderer import _resolve_template_path  # noqa: F401  (path helper)
from workflow_clean.action_registry import (
    CleanContext,
    DegradedActionError,
    build_default_registry,
)

from tests.fixtures.sqlite_kernel import make_kernel_dbs

PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


# --- RWB-02/03: seed + 渲染 + digest 对账 ---

def test_seed_and_render_roundtrip() -> None:
    core, _vec = make_kernel_dbs()
    digest = seed_prompt_version(
        core, prompt_key="structurize", template_path="structurize.md", prompts_dir=PROMPTS_DIR
    )
    assert digest == compute_digest((PROMPTS_DIR / "structurize.md").read_text(encoding="utf-8"))
    rendered = render_prompt(
        core, None, "structurize", {"input_text": "HELLO BODY"}, prompts_dir=PROMPTS_DIR
    )
    assert "HELLO BODY" in rendered
    assert "{{input_text}}" not in rendered  # 变量已注入


def test_render_unregistered_fail_loud() -> None:
    core, _vec = make_kernel_dbs()
    with pytest.raises(PromptError) as exc:
        render_prompt(core, None, "nope", {}, prompts_dir=PROMPTS_DIR)
    assert exc.value.reason == "prompt_not_registered"


def test_render_digest_mismatch_fail_loud() -> None:
    """文件↔SQLite digest 不一致 (文件改了未重 seed) → fail-loud, 不静默用文件。"""
    core, _vec = make_kernel_dbs()
    # 注册一个错误 digest (模拟文件被改但 SSOT 未更新)。
    core.execute(
        """
        INSERT INTO prompt_versions (id, team_id, prompt_key, version, template_path,
            template_digest, status, activated_at)
        VALUES ('pv_x', NULL, 'structurize', 'v1', 'structurize.md', 'deadbeef', 'active',
            strftime('%Y-%m-%dT%H:%M:%fZ','now'))
        """
    )
    core.commit()
    with pytest.raises(PromptError) as exc:
        render_prompt(core, None, "structurize", {"input_text": "x"}, prompts_dir=PROMPTS_DIR)
    assert exc.value.reason == "prompt_digest_mismatch"


def test_render_missing_variable_fail_loud() -> None:
    core, _vec = make_kernel_dbs()
    seed_prompt_version(
        core, prompt_key="summarize", template_path="summarize.md", prompts_dir=PROMPTS_DIR
    )
    with pytest.raises(PromptError) as exc:
        render_prompt(core, None, "summarize", {"section_path": "x"}, prompts_dir=PROMPTS_DIR)
    assert exc.value.reason == "prompt_missing_variables"  # chunk_text 缺


def test_sync_prompts_dir_seeds_all() -> None:
    core, _vec = make_kernel_dbs()
    digests = sync_prompts_dir(
        core,
        {"structurize": "structurize.md", "summarize": "summarize.md"},
        prompts_dir=PROMPTS_DIR,
    )
    assert set(digests) == {"structurize", "summarize"}


# --- RWB-04: structurize LLM 模式 ---

def _structured_json(text: str) -> str:
    return json.dumps(
        {
            "schema_version": "v1",
            "context_meta": {"title": "T", "source_hint": ""},
            "sections": [{"heading": "H", "level": 1, "text": text, "order": 0}],
        }
    )


def test_structurize_via_llm_valid() -> None:
    prompt = "render(input)"
    m = MockLLMProvider({prompt: _structured_json("body text here")})
    out = structurize_via_llm("body text here", m, prompt)
    assert out["produced_by"] == "llm"
    assert out["sections"][0]["text"] == "body text here"
    assert out["section_count"] == 1
    assert out["paragraphs"]  # 回填


def test_structurize_via_llm_invalid_json_fail_loud() -> None:
    prompt = "p"
    m = MockLLMProvider({prompt: "not json"})
    with pytest.raises(ValueError, match="invalid_json"):
        structurize_via_llm("x", m, prompt)


def test_structurize_via_llm_backfills_missing_sections() -> None:
    prompt = "p"
    m = MockLLMProvider({prompt: json.dumps({"schema_version": "v1"})})  # 无 sections
    out = structurize_via_llm("fallback body", m, prompt)
    assert out["sections"][0]["text"] == "fallback body"  # 用 source_text 回填


# --- RWB-05: summary LLM 模式 ---

def test_summarize_via_llm_returns_truncated() -> None:
    prompt = "p"
    m = MockLLMProvider({prompt: "a concise tax summary sentence"})
    s = summarize_via_llm(Chunk(text="t", section_path="S", index=0), m, prompt, max_chars=160)
    assert s == "a concise tax summary sentence"


def test_summarize_via_llm_empty_falls_back_to_rule() -> None:
    prompt = "p"
    m = MockLLMProvider({prompt: "   "})  # 空响应
    chunk = Chunk(text="First sentence. Second.", section_path="Sec", index=0)
    s = summarize_via_llm(chunk, m, prompt)
    assert "Sec" in s and "First sentence" in s  # 回落规则摘要


# --- RWB-06: clean geminiUnderstanding LLM 模式 vs degraded ---

def test_clean_registry_gemini_understanding_llm_mode() -> None:
    m = MockLLMProvider({"P:raw input": "cleaned output"})
    reg = build_default_registry(
        llm=m, render_clean_prompt=lambda raw: f"P:{raw}"
    )
    handler = reg.get_handler("geminiUnderstanding")
    out = handler(CleanContext(source_kind="file", source_uri="u", raw_text="raw input"))
    assert out == "cleaned output"
    assert not reg._specs["geminiUnderstanding"].degraded


def test_clean_registry_gemini_understanding_degraded_default() -> None:
    reg = build_default_registry()  # 无 llm → degraded fallback
    handler = reg.get_handler("geminiUnderstanding")
    with pytest.raises(DegradedActionError):
        handler(CleanContext(source_kind="file", source_uri="u", raw_text="x"))


# --- RWB-04 路由: executor 级 mock↔real-wiring 路由通道 (Settings→dispatch→render→factory mock) ---

def test_structurize_dispatch_routes_rule_vs_llm(tmp_path) -> None:  # noqa: ANN001
    from smind_config import Settings
    from workflow_rag.service import _structurize_dispatch

    core, _vec = make_kernel_dbs()
    seed_prompt_version(
        core, prompt_key="structurize", template_path="structurize.md", prompts_dir=PROMPTS_DIR
    )
    text = "VAT FILING\nValue added tax invoice filing body."

    # rule 模式 (默认): 规则化, 无 produced_by。
    rule_out = _structurize_dispatch(core, None, text, settings=Settings())
    assert "produced_by" not in rule_out

    # llm 模式: 经工厂 mock provider (从文件载预置响应) 走 prompt→render→provider。
    prompt = render_prompt(
        core, None, "structurize", {"input_text": text}, prompts_dir=PROMPTS_DIR
    )
    resp_file = tmp_path / "resp.json"
    resp_file.write_text(json.dumps({prompt: _structured_json(text)}), encoding="utf-8")
    settings = Settings(
        semantic_mode="llm",
        llm_provider="mock",
        mock_llm_responses_path=str(resp_file),
        prompts_dir=str(PROMPTS_DIR),
    )
    llm_out = _structurize_dispatch(core, None, text, settings=settings)
    assert llm_out["produced_by"] == "llm"
    assert llm_out["sections"][0]["text"] == text
