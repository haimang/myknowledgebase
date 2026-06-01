# [RW-A / provider 基座] Closure

> 阶段: `real-wire/RW-A — provider 基座 + mock + 路由 + 1024 维迁移`
> 范围: `RWA-01..09（协议 / 工厂 / Settings / MockLLM / 1024 迁移 / 装配注入 / eval corpus / 测试原语 / 先红后绿）`
> Close-type: `full-close`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/eval/real-wire/final-execution-plan-by-opus.md`（§6.A）
> 关联 design: `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 A）
> 关联 action-plan: `docs/action-plan/real-wire/RW-A-provider-base.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline（独立审查 → §5）`

---

## 0. 一句话 verdict

> RW-A keystone 全部 9 项 verified：维度全库迁至 1024（含运行时 SSOT `docs/refactor/vec.sql`）、`LLMProvider` 协议 + `MockLLMProvider`（未命中 fail-loud）、provider 工厂（按 Settings 选、未知 fail-loud、mlx 占位）、装配注入（写查同 provider）就位；全量 250 passed + 1 xfailed，断言强度门禁 0 弱；真实 MLX provider 按冻结裁决延后至 provider charter（工厂占位槽已留）。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. 真实 embedding/LLM 仍为 mock/local-hash —— 真实语义质量未交付（RW-C/provider charter）；mock 已标 non-delivery-quality。
> 2. `vec0` 路线在工厂为占位（`NotImplementedError`）—— 真实 vec0 在 RW-D。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| RWA-09 维度 1536→1024 全库迁移 + 写侧守卫 | ✅ | commit `4bdc30f` + `test_rw_a_provider_base.py::test_dimension_locked_1024_cross_package`/`test_write_side_dimension_guard_fail_loud` + grep `1536`=0(非注释) + 2026-06-01 10:24 UTC |
| RWA-01 `LLMProvider` 协议 | ✅ | `…::test_mock_satisfies_llm_provider_protocol` PASS |
| RWA-05 MockLLMProvider（未命中 fail-loud） | ✅ | `…::test_mock_llm_miss_fail_loud`/`_hit_by_raw_prompt`/`_hit_by_hash_key`/`_complete_json_validates_json` PASS |
| RWA-03 Settings 默认 mock/local/bruteforce + key 预留 | ✅ | `…::test_settings_defaults_offline_mock` PASS |
| RWA-02 工厂（选型 + 未知 fail-loud + mlx 占位） | ✅ | `…::test_factory_*`（default/unknown/deferred_mlx）PASS |
| RWA-04 装配注入（写查同 provider） | ✅ | `…::test_search_service_accepts_injected_embedder` + grep 业务码 0 直调 + 250 全量回归 PASS |
| RWA-06 eval corpus 装载器 | ✅ | `…::test_eval_corpus_loads_committed` PASS |
| RWA-07 使用链原语 `assert_used_real_chain` | ✅ | `…::test_assert_used_real_chain_positive_and_negative` PASS |
| RWA-08 先红后绿全绿 | ✅ | 全量 `250 passed, 1 xfailed`（基线 234）+ 门禁 0 弱 + 2026-06-01 10:24 UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 全量回归 | `python3 -m pytest` | `250 passed, 1 xfailed` | 全仓 |
| RW-A 新测 | `python3 -m pytest tests/unit/test_rw_a_provider_base.py` | `16 passed` | RWA-01..09 |
| 维度残留 | `grep -rn 1536 packages apps tests --include=*.py --include=*.sql` | 仅迁移历史注释，0 个生效字面 | 维度迁移 |
| 断言强度门禁 | `python3 tools/scripts/check_assert_strength.py` | `48 文件 0 弱` | 防假绿 |
| import 无循环 | `python3 -c "import management.service, workflow_rag.service, rag_vectorizer.search, provider_runtime"` | `imports OK` | 装配层 |
| 工厂路由 | `make_embedder/make_llm/make_vector_index(Settings())` | `local-bow-hash-v1(1024) / mock-llm-v1 / BruteForceVectorIndex` | RWA-02 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 维度全库 1024 | grep 1536 生效字面=0 + 跨包不变量 `DIMENSION==EMBEDDING_DIMENSION==1024` | 通过 | ✅ PASS |
| 默认零外网零计费 | Settings 默认 mock/local/bruteforce；无外部调用 | `test_settings_defaults_offline_mock` PASS | ✅ PASS |
| 写/查同 embedder（⛔3 TR-3） | 写(workflow_rag)/查(management→search) 均经 `make_embedder` → 同 name | 注入测 + 全量回归 PASS | ✅ PASS |
| 不回归（234 基线） | 全量 pytest 不降 | 250 passed（+16）+ 1 xfailed | ✅ PASS |
| degraded/未知 fail-loud（TR-4） | 未知 provider raise；mock 未命中 raise；fallback 0 匹配 raise | 对应测试 PASS | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 真实 MLX LLM/embedding 客户端 | C | 工厂 `mlx` 占位 `NotImplementedError` | 后续 provider charter（Q-RW-2） | owner + 下游 |
| 真实 vec0（工厂 `vector_index="vec0"`） | C | 占位 | RW-D（RWD-04） | RW-D |
| prompt 链消费 mock LLM | C | 工厂/Mock 就位，未接消费 | RW-B（structurize/summary/clean 去桩） | RW-B |
| 外部厂商 key 注入（`llm_api_key` 字段） | B | 字段预留 None，未落注入逻辑 | provider charter / RW-C（Q-RW-7） | owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ —— 全部 9 项为 **verified**（commit + 具名 test + run-time 四元组，本地 short/unit/集成层）。**无** live 项（真实模型按裁决延后，未在 RW-A scope）。 |
| ✅ 证据为四元组 | ✅ —— §1/§2 均 commit `4bdc30f` + 具名 test + 2026-06-01 10:24 UTC |
| scope diff 守卫 | ✅ —— 改动落在 provider_runtime（新包）/config/rag_vectorizer/vector_sqlite_vec/workflow_rag/management/tests + docs/refactor/vec.sql（运行时 SSOT，必须同步）；无越界 |
| deferred 已三分类且有承接位置 | ✅ —— §4 全为 C（handoff）/B（主动 defer），均带承接位置 |
| owner-test 项未复测标 ⏸ | N/A —— RW-A 无 owner-test/live 项（全本地可验） |

> **诚实说明（非假绿）**：RW-A 交付的是「可被真实接线的 mock 骨架 + 1024 基座」，**不含真实语义质量**。MockLLMProvider 与 LocalEmbedder(哈希) 均标 non-delivery-quality；真实质量须待 RW-C/provider charter 接入真实 MLX 模型后才成立。本 closure 不宣称「RAG 语义已交付」。

---

## 6. Handoff / 下阶段（RW-B）entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| `LLMProvider` 协议 + `MockLLMProvider` 可用 | ✅ | `provider_runtime` 已装、可 import |
| `make_llm`/`make_embedder` 工厂就位 | ✅ | 默认 mock/local-hash |
| 维度 1024 全库一致 | ✅ | RW-B capstone 的 embed 走 1024 |
| eval corpus + 使用链原语就位 | ✅ | RW-B mock capstone 直接复用 |
| `prompt_versions` 表 + `get_active_prompt` 读取器存在 | ✅ | RW-B 接消费侧（F6c 0 消费方待消除） |

**下阶段 kickoff checklist**：
- [ ] 引用本 closure 作为 single truth anchor
- [ ] RW-B 去桩走 `MockLLMProvider`（经 `make_llm`），embed 走 `make_embedder`（1024）
- [ ] prompt 正文落本地文件 + `prompt_versions` seed（path+digest），渲染期 digest 对账 fail-loud

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 向量维度 = 1024（全库 + 跨包） | ✅ 保持 | `DIMENSION==EMBEDDING_DIMENSION==1024`；vec.sql×2 CHECK=1024；grep 0 生效 1536 |
| 写/查同 embedder（TR-3 ⛔3） | ✅ 保持 | 写查均经 `make_embedder` → 同 name `local-bow-hash-v1` |
| 默认 mock 不打外网（TR-5） | ✅ 保持 | Settings 默认 mock/local/bruteforce |
| degraded/未知 fail-loud + 机器可读 reason（TR-4） | ✅ 保持 | 未知 provider / mock 未命中 / fallback 0 匹配 均 raise |
| 接口隔离 mock/live 同协议（TR-1） | ✅ 保持 | `MockLLMProvider` isinstance `LLMProvider`；真实 provider 走同协议占位槽 |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| r1 | 2026-06-01 | Opus 4.8 | RW-A 初闭合（full-close，250 passed） |
