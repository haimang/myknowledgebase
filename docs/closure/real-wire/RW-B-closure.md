# [RW-B / prompt 本地文件+SQLite-SSOT 语义链] Closure

> 阶段: `real-wire/RW-B — prompt 本地文件 + SQLite-SSOT + 三段去桩（mock 下）`
> 范围: `RWB-01..08（prompt 正文 / 渲染+digest 对账 / seed+SSOT / structurize·summary·clean LLM 模式去桩 / mock capstone / 防假绿）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/eval/real-wire/final-execution-plan-by-opus.md`（§6.B）
> 关联 design: `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 B）
> 关联 action-plan: `docs/action-plan/real-wire/RW-B-prompt-ssot-chain.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline（独立审查 → §5）`

---

## 0. 一句话 verdict

> RW-B 全部 8 项 verified（mock 下）：prompt 正文落本地文件 + SQLite-SSOT（path+digest，无 schema 改）+ 文件↔SQLite digest 对账 fail-loud；structurize/summary/clean 三段去桩为 prompt→render→provider（默认 rule fallback，零回归）；mock capstone 证明「文档→prompt→MockLLM→embed(1024)→search 命中」使用链真实发生；265 passed + 1 xfailed，门禁 0 弱。真实 LLM 质量延后至 provider charter（mock 标 non-delivery-quality）。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. LLM 输出质量为 **mock 占位**（`MockLLMProvider`）——使用链真实但语义质量未交付；真实 MLX provider 在 RW-C/provider charter。
> 2. 语义链默认 `semantic_mode=rule`（规则化）——llm 模式需显式开启 + provider 配置（real 延后）。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| RWB-01 本地 prompt 正文 | ✅ | commit `1dcf5b3` + `prompts/*.md` 存在 + `test_seed_and_render_roundtrip` PASS |
| RWB-02 渲染引擎 + digest 对账 fail-loud | ✅ | `test_rw_b_prompt_ssot.py::test_render_digest_mismatch_fail_loud`/`_missing_variable_fail_loud`/`_unregistered_fail_loud` PASS |
| RWB-03 seed + 接 get_active_prompt 消费侧 | ✅ | `…::test_seed_and_render_roundtrip`/`test_sync_prompts_dir_seeds_all` PASS（SQLite-SSOT，无 schema 改） |
| RWB-04 structurize 去桩（LLM 模式 + 规则 fallback） | ✅ | `…::test_structurize_via_llm_valid`/`_invalid_json_fail_loud`/`_backfills_missing_sections` PASS |
| RWB-05 summary 去桩 | ✅ | `…::test_summarize_via_llm_returns_truncated`/`_empty_falls_back_to_rule` PASS |
| RWB-06 clean geminiUnderstanding LLM 模式（live 接入） | ✅ | `…::test_clean_registry_gemini_understanding_llm_mode`/`_degraded_default` PASS + `process_clean_step` semantic_mode 感知 |
| RWB-07 mock capstone（文档→…→search 命中 + 使用链证据） | ✅ | `tests/e2e/test_real_wire_mock_capstone.py::test_mock_capstone_document_to_search_hit`/`_embedding_is_1024` PASS |
| RWB-08 防假绿（标 non-delivery-quality） | ✅ | `assert_used_real_chain`(min_calls=2) + 门禁 50 文件 0 弱 + 2026-06-01 10:37 UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| RW-B 单测 | `python3 -m pytest tests/unit/test_rw_b_prompt_ssot.py` | `13 passed` | RWB-02..06 + 路由 |
| mock capstone | `python3 -m pytest tests/e2e/test_real_wire_mock_capstone.py` | `2 passed` | RWB-07/08 |
| 全量回归 | `python3 -m pytest` | `265 passed, 1 xfailed`（基线 250） | 全仓 |
| 断言强度门禁 | `python3 tools/scripts/check_assert_strength.py` | `50 文件 0 弱` | 防假绿 |
| import 无循环 | `python3 -c "import workflow_clean.service, workflow_rag.service, management.service, provider_runtime, smind_config"` | OK | 装配层 |
| 路由通道（executor 级） | `test_structurize_dispatch_routes_rule_vs_llm` | rule→规则 / llm→`produced_by=llm`（经工厂 mock 从文件载响应） | RWB-04 路由 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| prompt SSOT + 文件↔DB digest 对账 fail-loud | 不一致即 raise，不静默用文件 | `test_render_digest_mismatch_fail_loud` PASS | ✅ PASS |
| mock capstone 语义命中 + 使用链证据 | search top∈目标文 + provider/embedder 真调 | capstone PASS | ✅ PASS |
| 默认零回归 | `semantic_mode=rule` 默认，既有 e2e 全绿 | 265 passed（含既有 first-fixes capstone） | ✅ PASS |
| 去桩契约不变 | structurize LLM 输出经 `_normalize_structured` 兼容下游 construct | 全量回归 PASS | ✅ PASS |
| 防假绿（non-delivery-quality） | Spy 真调 + 命中目标文（非仅非空）+ 门禁 | 门禁 0 弱 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 真实 LLM 输出质量 | C | mock 占位（`MockLLMProvider`），使用链真实但质量未交付 | RW-C / provider charter（真实 MLX provider 替 mock） | owner + 下游 |
| `semantic_mode=llm` 默认开启 | B | 默认 `rule`（零回归）；llm 需显式开 + provider | provider charter 定 provider 后评估默认值 | owner |
| executor pipeline 全链 llm 模式 e2e | B | 路由已通（dispatch 测），但端到端 executor llm 跑依赖真实/seeded provider | RW-C live | RW-C |
| KV 正文导出对照 | A | 不做（legacy KV 不可达，正文本地原创） | —（Q-RW-3 已裁决） | — |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ —— 全部 8 项为 **verified**（mock 下，commit + 具名 test + run-time）。**无** live/真实-LLM 项（按裁决延后）。 |
| ✅ 证据为四元组 | ✅ —— commit `1dcf5b3` + 具名 test + 2026-06-01 10:37 UTC |
| scope diff 守卫 | ✅ —— 改动落在 prompts/、config(prompt_renderer/settings)、rag_structurizer、rag_constructor、workflow_clean、workflow_rag、tests、.gitignore/.env.example；无越界 |
| deferred 已三分类且有承接位置 | ✅ —— §4 标 A/B/C，均带承接位置 |
| owner-test 项未复测标 ⏸ | N/A —— RW-B 全 mock 本地可验，无 owner-test/live 项 |

> **诚实说明（防假绿核心）**：RW-B 证明的是 prompt 语义链的**使用链真实发生 + 结构/检索命中**，**不是真实语义质量**。`MockLLMProvider` 返回 capstone 作者预置的响应、`LocalEmbedder` 是哈希词袋——两者均 **non-delivery-quality**。本 closure 不宣称「RAG 语义已交付」；真实质量须 RW-C 接入真实 MLX 模型后才成立。

---

## 6. Handoff / 下阶段（RW-C）entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| prompt SSOT + 渲染 + 对账机制就位 | ✅ | RW-C 真实 provider 直接复用同一 render→provider 链 |
| 语义链 dispatch（rule/llm 路由）就位 | ✅ | RW-C 把 `make_llm` 的 mlx 占位换真实即生效 |
| mock↔real-wiring 路由通道就位 | ✅ | `semantic_mode`/`llm_provider`/`mock_llm_responses_path` |
| 维度 1024 贯穿 capstone | ✅ | embed 1024 |
| 真实 provider adapter | ⏸ | 延后至 provider charter（RW-C 阻塞项） |

**下阶段 kickoff checklist**：
- [ ] 引用本 closure + RW-A closure 作为 truth anchor
- [ ] RW-C 真实 provider 实现 `LLMProvider`/`Embedder`，接工厂 `mlx` 槽
- [ ] live 质量验证替代 mock（capstone 在 live 模式结构一致）

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| SQLite = prompt SSOT（替代 Cloudflare KV，无 KV） | ✅ 保持 | `render_prompt` 经 `get_active_prompt` 读 SQLite；正文文件经 digest 受 SSOT 校验 |
| 文件↔SQLite digest 一致性（防篡改静默生效） | ✅ 保持 | digest 不一致 fail-loud |
| 默认 mock/rule 不打外网（TR-5） | ✅ 保持 | `semantic_mode=rule` + `llm_provider=mock` 默认 |
| 去桩保留规则化 fallback（TR-4/[Q3]） | ✅ 保持 | structurize_text/build_summary/degraded registry 均留 |
| 维度 1024 贯穿（RWA-09 继承） | ✅ 保持 | capstone embed 1024 |
| 密钥不进仓（Q-RW-7/TR-5） | ✅ 保持 | `.env`/`.tmp` git-ignored + `.env.example` 占位 |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| r1 | 2026-06-01 | Opus 4.8 | RW-B 初闭合（closed-with-explicit-deferrals，265 passed；真实 LLM 质量 deferred 至 provider charter） |
