# [FF-F6b / RAG 执行器去桩] Closure

> 阶段: `first-fixes/FF-F6b — RAG 执行器去桩`
> 范围: `structurize 结构化 schema + construct chunk/summary 双通道 + 独立 rag:vectorize step（F6-04/05/06）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md（§6.6 F6-04/05/06）`
> 关联 design: `N/A（消费冻结 [Q3][Q7] + F3-02/F4-03/F5）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F6b-rag-executors.md（§11 已回填）`
> 关联 evidence: `inline §2 + AP §11.3 四元组表`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-7.md（G-CR7-03/04/05）+ part-cr-3.md（R3/R4 rowid）`

---

## 0. 一句话 verdict

> F6b 收口：structurize 输出结构化 schema（sections + context_meta + schema_version，heading 启发式切分，替朴素 `\n` 分段）；construct 产 original + summary 双通道（确定性规则摘要 + 上下文头注入）、chunk_id 确定性派生（`sha256(doc:index:channel)` 取代 uuid4）、upsert 复用 rowid（F4-03）；向量化拆为独立 `rag:vectorize` step（construct 经 ExecutorResult 声明下游、vectorize 独立 claim/重试/重启调 F5 Embedder 1536 维、五步序 + replay 幂等）；rag 执行器全遵 F3-02（无自提交）；先红后绿 14 用例，全量 161→**175 passed**（exit 0）；close-type=closed-with-explicit-deferrals。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. structurize/construct 为**确定性规则化（非 LLM）**，summary 是规则摘要——legacy 全 AI 结构化/摘要为 [Q3] 显式 OOS。
> 2. layer-json 产物 [Q3] degraded（O1）；端到端语义命中独立 capstone 步交 F7。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| F6-04 structurize 结构化 schema（非裸 paragraphs） | ✅ | `36af537 + test_rag_structurize(6) + 2026-06-01 04:01 UTC` |
| F6-05 construct chunk+summary 双通道 + 确定性 chunk_id + rowid 复用 | ✅ | `36af537 + test_rag_construct_channels(5) + test_rag_step_chain(双通道+重放幂等) + 2026-06-01 04:01 UTC` |
| F6-06 独立 rag:vectorize step（F5 Embedder + 五步序 + 幂等） | ✅ | `36af537 + test_rag_step_chain(独立 step + 重放幂等) + 2026-06-01 04:01 UTC` |
| rag 执行器 F3-02 契约（无自提交终态） | ✅ | `36af537 + test_rag_step_chain::test_construct_vectorize_contract_no_self_commit + 2026-06-01 04:01 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| structurize schema | `pytest tests/unit/test_rag_structurize.py` | `6 passed`；sections/schema_version/context_meta/heading 切分/title/默认 section/兼容 paragraphs/空 | structurize_text |
| construct 双通道 | `pytest tests/unit/test_rag_construct_channels.py` | `5 passed`；section_path/summary 非空用 heading/空摘要空/上下文头/max_chars 二次切分 | build_section_chunks/build_summary/with_context_header |
| 独立 vectorize step + 双通道 + completed | `test_rag_step_chain::test_independent_vectorize_step_and_dual_channel` | rag:vectorize step succeeded（独立于 construct）；artifacts channel 含 original+summary；全 vectorized；run completed | 全链 file→...→vectorize |
| 重放幂等 | `test_rag_step_chain::test_replay_idempotent_no_duplicate_chunks` | 再驱动 worker → chunk 数 + vector_records 数不变（确定性 chunk_id + INSERT OR IGNORE + 复用 rowid） | construct/vectorize replay |
| 执行器契约 | `test_rag_step_chain::test_construct_vectorize_contract_no_self_commit` | rag service 源码无 `conn.commit()`/`status='succeeded'` | F3-02 |
| 真实 1536 语义命中（T07） | p5 全链 + F5 `test_f5_vector_authenticity` | rag 链真实喂 F5 embedding；search 命中（p5 175 全绿） | url→rag→search |
| 全量回归 | `python3 -m pytest tests/` | `175 passed`（exit 0；161+14） | 全仓 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| structurize 结构化 schema 非裸 paragraphs | sections/schema_version + 切分正确 | T01 绿 | ✅ PASS |
| construct chunk+summary 双通道 | original+summary 两通道 + summary 非空 | T03 + chain 双通道 绿 | ✅ PASS |
| 独立 rag:vectorize step 可 claim/重试/重启 | 独立 step succeeded + replay 幂等 | T06/T08 绿 | ✅ PASS |
| 调 F5 Embedder 真实 1536 语义命中 | 相关 query 命中目标 chunk | p5 全链 + F5 spike 绿 | ✅ PASS（经 p5/F5 覆盖） |
| rag 执行器无自提交（F3-02） | grep 0 命中 | T02/T05 绿 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| layer-json 产物落库（O1） | A（[Q3] degraded OOS） | 未产；reason=out-of-scope-by-Q3 | 下一轮去桩 / 前端需层级还原 | 下一轮 |
| legacy 全 AI 结构化策略（O2） | A（[Q3] OOS） | 确定性规则化 heading 切分（非 LLM） | 产品需 AI 质量提升 | 下一轮 |
| legacy AI 摘要（O3） | A（[Q3] OOS） | 规则摘要（heading+首句），保留通道结构 | 替换为真实 AI 摘要时 | 下一轮 |
| 真实 vec0 / 外部 embedding / search 过滤 / channel 级 purge（O4） | A/C | F5 已交付 1536 本地 embedding + namespace/model 过滤；vec0/外部/精细 purge 延后 | F5 已部分；其余下一轮 | F5/下一轮 |
| T07 端到端语义命中独立 capstone 步 | C（handoff） | 由 p5 全链 + F5 spike 覆盖；独立 capstone 步未建 | `FF-F7` capstone E/F 步 | F7 |
| vectorize replay race 长稳 soak（T08 ×N） | C（handoff） | 单次重放幂等已验；×N race soak 未做 | `FF-F7` / 退出硬闸 | F7 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ — §1 全部 **verified**（commit + test + run-time 四元组齐全，先红后绿可证；T07 经 p5/F5 全链覆盖标 verified-via-integration） |
| ✅ 证据为四元组，无裸 file:line | ✅ |
| scope diff 守卫（仅改 in-scope 文件，无越界） | ✅ — 改 rag_structurizer/rag_constructor/workflow_rag，均在 §3 工作总表 + §7.1 锚表内 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ — §4 六项均标 A/B/C + 承接位置 |
| owner-test 项未经复测标 ⏸ | N/A — 无 owner-test 项 |

> **诚实附注**：
> 1. **确定性规则化，非神经/AI**：structurize（heading 启发式）、construct summary（heading+首句规则摘要）均非 LLM——[Q3]/O2/O3 显式定档；保留通道/schema 结构供未来接 AI。不冒充 AI 质量。
> 2. **T07 真实 1536 语义命中经集成覆盖**：未建独立 F6b 语义 spike，而由 p5 全链（现真实经 dual-channel + 独立 vectorize + F5 embedder）+ F5 `test_f5_vector_authenticity` 覆盖；如实标注覆盖路径，不另造重复 spike。
> 3. **双通道唯一约束处理**：chunks `UNIQUE(document_id,chunk_index)` + `UNIQUE(document_id,content_hash)` 通过"全局 row_index 作 chunk_index + channel 入 content_hash + 确定性 chunk_id(logical index:channel)"同时满足，replay 幂等（test_replay_idempotent 实测 chunk/vec 数不变）。
> 4. 全量 175 passed 含 F1-F6a 既有 161 用例无回归（p3/p4/p5 全链经新 dual-channel + split-vectorize 管道通过）。
