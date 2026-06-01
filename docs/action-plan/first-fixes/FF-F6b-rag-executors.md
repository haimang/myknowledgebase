# Nano-Agent 行动计划 — FF-F6b RAG 执行器去桩

> 服务业务簇: `smind-family · first-fixes · F6（RAG 执行器子簇）`
> 计划对象: `F6b · RAG 执行器去桩（structurize 真实结构化 + construct chunk/summary 双通道 + 拆独立 rag:vectorize step）`
> 类型: `refactor`（去桩 = 用真实实现替换占位实现 + 拆步重构）
> 作者: `Claude（sub-agent / first-fixes 派生）`
> 时间: `2026-05-31`
> 文件位置: `docs/action-plan/first-fixes/FF-F6b-rag-executors.md`
> 上游前序 / closure:
> - `FF-F1-time-tx-base.md`（keystone：单一时间 SSOT + F1-04 autocommit + 多写 helper 包 `BEGIN IMMEDIATE...COMMIT`）
> - `FF-F2-conn-wiring.md`（连接/装配，并行前序）
> - `FF-F3-kernel-recovery.md`（**F3-02 执行器契约 `execute(step,deps)->ExecutorResult` —— 本 AP 的 rag 执行器必须建在此契约上，不自提交终态**）
> - `FF-F4-adapter-safety.md`（**F4-03 rowid 不变量：upsert 复用 `embedding_rowid` 不制造孤儿**）
> - `FF-F5-vector-authenticity.md`（**F5 Embedder：本地 1536 维真实 embedding；F6-06 vectorize step 调本地 1536 embedding**）
> 下游交接:
> - `FF-F7-test-integrity.md`（测试有效性重建 + closure 重定级：本 AP 的先红后绿回归纳入 F7 整合 lane；degraded 项进 closure 定级）
> 关联设计 / 调研文档:
> - `docs/design/first-fixes/initial-planning-by-opus.md`（§6.6 F6 [final] 绑定 F6-04/05/06；§2.C [Q3] 定档增量；§8 capstone E/F 步 + DoD）
> - `docs/design/first-fixes/owner-gated-qna.md`（[Q3] 去桩增量、基础结构化；[Q7] 先红后绿）
> 冻结决策来源:
> - `docs/design/first-fixes/owner-gated-qna.md`（[Q3] / [Q7] 只读引用；本 AP 不开 Q/A）
> grounding 来源:
> - `eval-reference-anchor`：`docs/eval/first-code-review-plan/part-cr-7.md`（G-CR7-03/04/05、R2/R3/R6/R7、parity 矩阵 + file:line）、`part-cr-3.md`（G-CR3-03/04 rowid 触发点）；legacy 只读参照 `legacy-family/smind-skill-rag-{structurizer,constructor}/`
> 关联 reference-anchor:
> - 见 §7 内置锚区（摘自 part-cr-7 / part-cr-3 的 file:line）
> 文档状态: `draft`

---

## 0. 执行背景与目标

CR-7 审查确认 RAG 流水线是「端到端能跑通的极简骨架」：三段 step 链路、artifact 落库、chunk/vec_status 流转、search hydration 视图都真实存在且方向正确，但三个核心业务执行器全是占位实现——`structurize_text` 是 `text.split("\n")` 朴素分段（9 行 vs legacy structurizer 2,897 行，缺 67%）、`build_chunks` 是 350 字符贪心拼接且 summary 通道 + layer-json 完全缺失（22 行 vs legacy constructor 3,887 行，缺 55%）、向量化内联于 construct 而非独立可 claim/重试/重启的 step（G-CR7-05）。本 AP 是 F6 三拆中的 rag 子簇（F6b），承接 final plan §6.6 的 **F6-04 / F6-05 / F6-06** 三项，把这三处占位换成真实但范围受控的实现。

本 AP 的输入来自冻结结论：`[Q3]` 把 F6 去桩定档为**增量**——structurize/construct 做「真实但不追 legacy 全部 AI 策略」的实现；`[Q7]` 把「先红后绿」升为全 phase 铁律。本 AP 严格消费这两条，不重新讨论去桩范围本身。本 AP 不是孤立的：rag 执行器必须建在 **F3-02 执行器契约**（`execute(step,deps)->ExecutorResult`，不自提交终态）之上、新拆的 vectorize step 必须调 **F5 Embedder**（本地 1536 维真实 embedding）、construct 的 upsert 必须遵守 **F4-03 rowid 不变量**（复用 `embedding_rowid` 不制造孤儿）。这三个跨 AP 依赖是本 AP 的硬约束。

本 AP 把 CR-7 的 R2/R3/R6 三个 blocker 与 G-CR7-03/04/05 闭环：structurize 输出结构化 schema（非裸 paragraphs）；construct 产 chunk + summary 双通道；向量化成为独立 `rag:vectorize` step。layer-json 视 [Q3] 增量范围处置——本轮 **degraded**（见 §2.2），避免把 F6b 拖入数周大工程。

- **服务业务簇**：`smind-family · first-fixes · F6（RAG 执行器）`
- **计划对象**：`F6b · structurize 真实结构化 + construct chunk/summary 双通道 + 独立 rag:vectorize step`
- **本次计划解决的问题**：
  - `F6-04 / G-CR7-03 / R2`：structurize 朴素 `\n` 分段，无 schema、无层级结构，下游 construct 无可用 layered 结构可消费。
  - `F6-05 / G-CR7-04 / R3`：construct 仅产 chunk_text 单通道，summary 通道完全缺失，召回面减半；且 upsert 不传 `embedding_rowid` 触发孤儿（G-CR3-03）。
  - `F6-06 / G-CR7-05 / R6`：向量化内联于 construct，违反「每 step 可 claim/重试/重启」内核硬约束，embedding 失败即整 construct step 重跑（重新分块 + 喂养孤儿）。
- **本次计划的直接产出**：
  - structurize 真实结构化器：输出带 schema 的结构化对象（sections + 元数据），非裸 paragraphs 数组。
  - construct 双通道：每 chunk 同时产 original chunk_text + summary 文本，落 chunks 表与 vec 写入侧（summary 作为独立通道记录）。
  - 独立 `rag:vectorize` step：construct 只产 chunk(pending_vectorize)，finalizer 创建 vectorize step；vectorize step 独立 claim/重试/重启，调 F5 Embedder + 复用 rowid upsert。
- **本计划不重新讨论的设计结论**：
  - 去桩范围 = 增量（structurize/construct 真实但不追 legacy 全 AI 策略）（来源：`[Q3]`）。
  - 全 phase 先红后绿铁律（每 blocker 修复以「先红后绿回归」为退出证据）（来源：`[Q7]`）。
  - 执行器不自提交终态、只产 `ExecutorResult`（来源：F3-02 契约 / planning §4 红线第 2 条）。
  - 本地 1536 维 embedding + degraded 暴力 cosine（来源：`[Q1][Q2]` / F5，本 AP 只消费不重定）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用 **「先结构后通道、先拆步后接线、全程先红后绿」** 的执行方式，分 3 个 Phase：先做 structurize 真实结构化（Phase 1，为下游 construct 提供可消费的结构化输入）；再做 construct chunk/summary 双通道并修 rowid 复用（Phase 2，依赖 Phase 1 的结构化输出）；最后拆出独立 `rag:vectorize` step 并把向量化从 construct 内联中剥离（Phase 3，依赖 F3-02 契约 + F5 Embedder + F4-03 rowid）。每个 Phase 的退出判据是「在当前 HEAD FAIL、修复后 PASS」的有意义测试。本节只写执行策略，去桩范围与方法论的论证已在 `[Q3][Q7]` 冻结，不重述。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | structurize 真实结构化 | S | `structurize_text` 输出带 schema 的结构化对象（sections + 元数据），替换朴素 `\n` 分段；下游 construct 可消费 | F3-02 契约（执行器返回 ExecutorResult） |
| Phase 2 | construct chunk + summary 双通道 + rowid 复用 | M | construct 产 original + summary 双通道；upsert 复用 `embedding_rowid`（F4-03）；chunk_id 确定性派生（消除孤儿/重复） | Phase 1；F4-03 rowid 不变量 |
| Phase 3 | 拆独立 rag:vectorize step | M | vectorize 从 construct 内联剥离为独立可 claim/重试/重启 step；调 F5 Embedder（本地 1536）；按五步序写跨库 | Phase 2；F3-02 契约；F5 Embedder |

> 说明：`规模` 是描述性提示，不是开工闸，不改变本模板任何段落取舍。

### 1.3 Phase 说明

1. **Phase 1 — structurize 真实结构化**
   - **核心目标**：把 `structurize_text` 从 `text.split("\n")` 升级为输出结构化 schema（sections 列表 + 每 section 的 heading/level/text + 文档级 context_meta 骨架），供 construct 消费。
   - **为什么先做**：construct 的双通道（尤其 summary 与上下文头注入）依赖 structurize 先产出可用的结构化层级；先有结构才能在 construct 做有意义的分块与摘要。
2. **Phase 2 — construct chunk + summary 双通道 + rowid 复用**
   - **核心目标**：construct 对每个 chunk 同时产 original 通道与 summary 通道，并把 chunk_id 改为确定性派生、upsert 复用 `embedding_rowid`，根除 R3 孤儿/重复。
   - **为什么放在这里**：消费 Phase 1 的结构化输出；且 rowid 复用是 construct 调 upsert 的职责（CR-7 R3 触发点在本簇），必须与双通道同窗口修，否则 summary 通道会立即放大孤儿问题。
3. **Phase 3 — 拆独立 rag:vectorize step**
   - **核心目标**：把向量化从 construct 内联剥离为独立 `rag:vectorize` step（construct 只产 chunk+pending_vectorize + 经 ExecutorResult 声明下游 vectorize step），vectorize step 独立 claim/重试/重启，调 F5 Embedder，按五步序写跨库。
   - **为什么放在这里**：依赖 Phase 2 的 chunk 落库与 rowid 复用，且依赖 F3-02 契约（声明下游 step）与 F5 Embedder（真实 1536 维向量）；是结构性最重、跨 AP 依赖最密的一步，放最后。

### 1.4 执行策略说明

- **执行顺序原则**：先结构（structurize）→ 后通道（construct 双通道）→ 后拆步（vectorize），每步消费上一步产出；vectorize 拆步与 F3-02 契约迁移对齐（construct 不再自提交终态，下游 step 经 ExecutorResult 声明）。
- **风险控制原则**：F6-04/05/06 均为净新/高风险，§4 拆有序子步、每子步配独立先红后绿测试；rowid 复用、五步序跨库写入这类「触碰已知 critical 不变量」的子步单独立测；vectorize 拆步前先冻结 step 链契约（construct→vectorize 的 ExecutorResult downstream 声明）。
- **测试推进原则**：短途 unit（structurize schema / build_chunks 双通道 / rowid 复用）随 Phase 提交；spike 集成（construct→vectorize step 链 / 真实 1536 向量语义命中）每 Phase 收口；mega capstone（§8）对齐 planning §8 capstone E/F 步在本 AP 收口；详见 §8 测试台账。
- **文档同步原则**：layer-json 的 degraded 决定写入 §2.2 与 §7.2，并交 F7 closure 定级；degraded 项带机器可读 reason。
- **回滚 / 降级原则**：layer-json 超本轮范围 → 显式 degraded（声明 + 测试 skip/xfail + 不留装成完成的桩）；若 F5 Embedder 未就绪，vectorize step 拆分可先落地、embedding 调用以确定性 mock 占位**并显式标注非交付向量**（不得当真向量）；若 F3-02 契约未就绪，本 AP blocked（rag 执行器无契约可建）。

### 1.5 本次 action-plan 影响结构图

```text
F6b · RAG 执行器去桩
├── Phase 1: structurize 真实结构化
│   ├── packages/rag_structurizer/src/rag_structurizer/service.py（structurize_text 重写）
│   └── packages/workflow_rag/src/workflow_rag/service.py（structurize 分支消费结构化 schema）
├── Phase 2: construct chunk + summary 双通道 + rowid 复用
│   ├── packages/rag_constructor/src/rag_constructor/service.py（build_chunks → 双通道）
│   ├── packages/workflow_rag/src/workflow_rag/service.py（construct 分支：双通道落库 + 确定性 chunk_id）
│   └── packages/vector_sqlite_vec/src/vector_sqlite_vec/store.py（upsert 复用 rowid — 与 F4-03 同窗口对齐）
└── Phase 3: 拆独立 rag:vectorize step
    ├── packages/workflow_rag/src/workflow_rag/service.py（新增 rag:vectorize 分支 + construct 剥离向量化）
    ├── packages/rag_vectorizer/src/rag_vectorizer/embedder.py（接 F5 Embedder，删伪向量）
    └── apps/worker/src/smind_worker/main.py（rag:vectorize stage 派发 — 已由 startswith("rag:") 覆盖，确认）
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** F6-04：`structurize_text` 输出结构化 schema（sections + heading/level/text + 文档级 context_meta 骨架），非裸 paragraphs；workflow_rag structurize 分支消费并落 `structured_json` artifact。
- **[S2]** F6-05：construct 产 **chunk + summary 双通道**——每 chunk 产 original chunk_text + summary 文本，summary 作为独立向量通道记录；upsert **复用 `embedding_rowid`**（F4-03）、chunk_id 确定性派生（document_id + chunk_index + channel）。
- **[S3]** F6-06：拆出独立 `rag:vectorize` step——construct 只产 chunk(pending_vectorize)、经 ExecutorResult 声明下游 `rag:vectorize` step；vectorize step 独立 claim/重试/重启，调 F5 Embedder，按五步序写跨库。
- **[S4]** rag 执行器全部遵守 **F3-02 契约**：只产 `ExecutorResult`、不写 step 终态/run/不 commit core；先红后绿回归（[Q7]）。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** **layer-json 产物落库**（legacy `flows/constructor.ts:172` 的 `layered_json_r2_key`）—— **本轮 degraded**：[Q3] 增量范围把 F6 收窄为「真实但不追 legacy 全策略」，layer-json 属下游/前端层级还原的重产物，本轮显式不做（degraded 声明 + 下游 closure 定级 + 不留装成完成的桩）；reason=`out-of-scope-by-Q3-incremental`。
- **[O2]** legacy 全 AI 结构化策略（Gemini 结构化抽取 + 模型策略表 + reasoning/thinkingBudget + retry 循环 + Zod 校验 + sanitize/preprocess）—— [Q3] 明确「不追 legacy 全部 AI 策略」；本轮 structurize 做确定性规则化结构化（heading 识别 + section 切分），不接 LLM。
- **[O3]** legacy summarizer 的 AI 摘要（`services/summarizer.ts` 全 332 行）—— 本轮 summary 通道用确定性摘要（截断/首句/section 标题拼接的规则摘要），不接 LLM；保留通道结构供未来替换为真实 AI 摘要。
- **[O4]** 真实 vec0 / sqlite-vec 扩展加载（[Q1] degraded）、外部 API embedding（[Q2] 本地小模型）、channel 级精细 purge（R10）、search namespace/model 过滤（R8/F5-03）—— 分别归 F5 与 follow-up，本 AP 不重复。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| structurize 结构化 schema（非朴素分段） | `in-scope` | F6-04 / G-CR7-03 / [Q3] 基础结构化 | — |
| construct chunk + summary 双通道 | `in-scope` | F6-05 / G-CR7-04 召回面减半根因 | — |
| 独立 rag:vectorize step | `in-scope` | F6-06 / G-CR7-05 内核硬约束「每 step 可 claim/重试/重启」 | — |
| upsert 复用 embedding_rowid | `in-scope` | F4-03 不变量；R3 触发点在本簇 construct 调用方式 | — |
| layer-json 产物落库 | `defer / depends-on-design` | [Q3] 增量范围外，重产物 | 下一轮去桩或前端需层级还原时 |
| legacy 全 AI 结构化/摘要策略 | `out-of-scope` | [Q3] 不追 legacy 全 AI 策略 | 产品需 AI 质量提升时 |
| 真实 vec0 / 外部 embedding | `out-of-scope` | 归 F5（[Q1][Q2] degraded + 本地 1536） | 生产化阶段 |

---

## 3. 业务工作总表

> 编号沿用 final plan §6.6 的 `F6-NN`（跨态稳定）。三元组（涉及文件 / 收口目标 / 测试映射）齐全；本 AP 三项均净新/高风险，`工作内容` 在 §4 拆有序子步。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| F6-04 | Phase 1 | structurize 真实结构化（schema 化输出） | refactor | `rag_structurizer/src/rag_structurizer/service.py:4-8`（重写）；`workflow_rag/src/workflow_rag/service.py:51-72`（structurize 分支） | `structurize_text` 输出结构化 schema（sections + 元数据），非裸 paragraphs；下游 construct 可消费 | `FF-F6b-T01` `FF-F6b-T02` | **high** |
| F6-05 | Phase 2 | construct chunk + summary 双通道 + rowid 复用 | refactor | `rag_constructor/src/rag_constructor/service.py:4-21`（双通道）；`workflow_rag/src/workflow_rag/service.py:99-179`（construct 分支）；`vector_sqlite_vec/src/vector_sqlite_vec/store.py:32,126-130`（rowid 复用，F4-03 同窗口） | construct 产 original+summary 双通道；upsert 复用 `embedding_rowid` 0 孤儿；chunk_id 确定性派生 | `FF-F6b-T03` `FF-F6b-T04` `FF-F6b-T05` | **high** |
| F6-06 | Phase 3 | 拆独立 rag:vectorize step | refactor | `workflow_rag/src/workflow_rag/service.py:99-219`（剥离向量化 + 新 vectorize 分支）；`rag_vectorizer/src/rag_vectorizer/embedder.py:6-16`（接 F5 Embedder）；`apps/worker/src/smind_worker/main.py:49-50`（确认 rag: 派发） | vectorize 为独立可 claim/重试/重启 step；调 F5 Embedder（1536）；按五步序写跨库 | `FF-F6b-T06` `FF-F6b-T07` `FF-F6b-T08` | **high** |

---

## 4. Phase 业务表格

> `工作内容` 是承重列；本 AP 三项均净新/高风险，拆有序子步（a/b/c…）覆盖核心逻辑 + 边界 + 失败/降级路径。测试细节只在 §8 写一次。

### 4.1 Phase 1 — structurize 真实结构化

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F6-04 | structurize 真实结构化 | **有序子步（净新高风险）：** **a)** 在 `rag_structurizer/service.py` 定义 Python 侧结构化 schema（确定性，非 LLM）：`{"context_meta": {...骨架: title/source_hint}, "sections": [{"heading": str, "level": int, "text": str, "order": int}], "section_count": int, "schema_version": "v1"}`。**b)** 实现 `structurize_text(text) -> dict`：按 heading 启发式（行首 `#`/全大写短行/数字编号）切分 sections，section 内合并连续正文行；无 heading 的正文归入默认 section（level=0）。**c)** 保留向后兼容字段：输出仍含 `paragraphs`（从 sections 扁平展开）+ `paragraph_count`，使 Phase 2 之前的 construct 仍可读（迁移期双供）。**d)** 边界：空输入 → `{sections: [], section_count: 0, paragraphs: []}`；纯空白 → 同空输入；超长单行 → 单 section（不在 structurize 切块，切块归 construct）。**e)** `workflow_rag/service.py:51-72` structurize 分支：调用新 `structurize_text`，`structured_json` artifact 的 metadata 落完整 schema（不止 paragraphs）；该分支按 F3-02 改为返回 `ExecutorResult`（不自插下游 step、不 commit）。**f)** 降级：不接 LLM（[Q3] / O2）；context_meta 仅产骨架（title 从首个 level-1 heading 推断，无则空）。 | `rag_structurizer/src/rag_structurizer/service.py:4-8`；`workflow_rag/src/workflow_rag/service.py:51-72` | structurize 输出结构化 schema（sections + context_meta 骨架），非裸 paragraphs 数组 | `FF-F6b-T01` `FF-F6b-T02` | unit 断言 schema 含 `sections`/`schema_version` 且 section 切分正确；structurize 分支无 core 终态写入/commit；先红后绿 |

### 4.2 Phase 2 — construct chunk + summary 双通道 + rowid 复用

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F6-05 | construct 双通道 + rowid 复用 | **有序子步（净新高风险）：** **a)** `rag_constructor/service.py`：`build_chunks` 改造为消费 sections——按 section 边界优先、max_chars 二次切分，产 `list[Chunk]`，每 `Chunk` 含 `text`（original）+ `section_path`（来自 section heading 层级）。**b)** 新增确定性摘要：`build_summary(chunk) -> str`（规则摘要：section heading + 首句/截断，非 LLM；[Q3]/O3），summary 作为**第二通道**文本。**c)** 上下文头注入：original 通道嵌入文本前缀 `[title/section_path]`（对齐 legacy `buildContentFull` 的语义锚点，规则化版本）。**d)** `workflow_rag/service.py:99-179` construct 分支：对每 chunk 落 **两条** chunk 行/向量记录（channel=`original` 与 channel=`summary`），各自 chunk_id **确定性派生**（`sha256(document_id:chunk_index:channel)` 而非 `uuid4()`）——根除 R3「每次新 chunk_id」。**e)** upsert 复用 rowid（F4-03 同窗口）：upsert 前按 `(document_id, chunk_index, channel, content_hash)` 查既有 `vector_records`，命中则复用其 `embedding_rowid`，否则取新（不复用导致孤儿，禁止裸 `_next_embedding_rowid` 不传 rowid）。**f)** 边界/失败：空 sections → 0 chunk（不报错）；同 run replay → 确定性 chunk_id + 复用 rowid ⇒ 0 重复 chunk / 0 孤儿；summary 为空 → 跳过 summary 通道（不落空向量）。**g)** degraded：layer-json 不产（O1，显式声明）；摘要为规则版（非 AI）。**h)** 本分支按 F3-02 不写 run completed / step succeeded / 不 commit core（终态归内核）。 | `rag_constructor/src/rag_constructor/service.py:4-21`；`workflow_rag/src/workflow_rag/service.py:99-179`；`vector_sqlite_vec/src/vector_sqlite_vec/store.py:32,126-130` | construct 产 original+summary 双通道；重复执行 0 孤儿；chunk_id 确定性 | `FF-F6b-T03` `FF-F6b-T04` `FF-F6b-T05` | unit：双通道产出 + summary 非空；rowid 复用回归（重 upsert 0 孤儿）；construct 分支无 core 终态/commit |

### 4.3 Phase 3 — 拆独立 rag:vectorize step

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F6-06 | 拆独立 rag:vectorize step | **有序子步（净新高风险）：** **a)** construct 分支剥离向量化：`workflow_rag/service.py:99-179` 删除内联的 `embed_text` + `upsert_chunk` + `vectorized` 回写；construct 只落 chunk 行（`vec_status='pending_vectorize'`）+ chunk_text artifact + constructed_json。**b)** construct 经 `ExecutorResult.downstream` 声明下游 `rag:vectorize` step（**不自插 step**——F3-02 契约由内核 `succeed_claim` 创建下游）。**c)** 新增 `rag:vectorize` 分支（`process_rag_step` 内 `elif stage == "rag:vectorize"`）：查本 run 全部 `vec_status='pending_vectorize'` 的 chunk（含 original+summary 两通道），逐 chunk 调 **F5 Embedder**（本地 1536 维真实 embedding，删 `embedder.py:6-16` 伪向量）→ `upsert_chunk`（传 content_hash + **复用 embedding_rowid**，F4-03）→ 回写 `vec_status='vectorized'`。**d)** 五步序（CR-7 R5）：先 commit core 的 chunk(pending_vectorize)（已在 construct step）→ vectorize step 内 upsert vec.db → 回写 core vectorized；崩溃后由 replay 依 `vec_status='pending_vectorize'` 重做（幂等：复用 rowid + 确定性 chunk_id）。**e)** vectorize step 按 F3-02 返回 `ExecutorResult`（run 推进至 completed 经内核）；独立 claim → 可单独 retry/restart（对齐内核「每 step 可 claim/重试/重启」）。**f)** worker 派发：`main.py:49` 的 `startswith("rag:")` 已覆盖 `rag:vectorize`，确认无需改派发；step_key/action 命名对齐（`rag.vectorize`）。**g)** 边界/失败：embedding 失败 → 抛异常交内核 fail_claim（不自提交、不留半写），重试只重做未 vectorized 的 chunk；0 pending chunk → vectorize step 空跑成功。**h)** 降级：F5 未就绪时 embedding 以确定性 mock 占位**并显式标注非交付向量**（测试标 xfail，不当真向量）。 | `workflow_rag/src/workflow_rag/service.py:99-219`；`rag_vectorizer/src/rag_vectorizer/embedder.py:6-16`；`apps/worker/src/smind_worker/main.py:49-50` | vectorize 为独立可 claim/重试/重启 step；调 F5 Embedder；五步序 + rowid 复用幂等 | `FF-F6b-T06` `FF-F6b-T07` `FF-F6b-T08` | step 链测试：construct 产 pending → 独立 vectorize step claim 执行 → vectorized；真实 1536 向量语义命中；重试不产重复向量 |

---

## 5. Phase 详情

> 测试不在此展开，每项指向 §8 Test-ID。三项均净新/高风险，`具体功能预期` ≥5 条含边界与失败/降级路径。

### 5.1 Phase 1 — structurize 真实结构化

- **Phase 目标**：`structurize_text` 输出带 schema 的结构化对象（sections + context_meta 骨架），替换 `text.split("\n")` 朴素分段，使 construct 有可消费的层级结构。
- **本 Phase 对应编号**：`F6-04`
- **本 Phase 新增文件**：无（重写既有 `rag_structurizer/service.py`）
- **本 Phase 修改文件**：`rag_structurizer/src/rag_structurizer/service.py:4-8`、`workflow_rag/src/workflow_rag/service.py:51-72`
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. `structurize_text` 返回 dict 含 `sections`（每项 heading/level/text/order）、`context_meta` 骨架、`schema_version="v1"`、`section_count`，**不再是裸 paragraphs 数组**。
  2. heading 启发式正确切分（行首 `#` / 全大写短行 / 数字编号 → section 边界），section 内连续正文合并。
  3. 向后兼容：迁移期仍输出 `paragraphs`/`paragraph_count`（从 sections 扁平展开），Phase 2 完成后可移除。
  4. 边界：空输入/纯空白 → 空 sections（不抛异常）；超长单行 → 单 section（不在 structurize 切块）。
  5. structurize 分支（`service.py:51-72`）落完整 schema 到 `structured_json` artifact metadata；按 F3-02 返回 `ExecutorResult`（不自插 construct step、不 commit core）。
  6. 降级（失败路径）：不接 LLM（[Q3]/O2）；context_meta 仅骨架（title 从首个 level-1 heading 推断，无则空字符串）。
- **对应测试台账项**：`FF-F6b-T01` / `FF-F6b-T02`（详见 §8）
- **收口标准**：unit 断言输出 schema 含 `sections`+`schema_version` 且切分正确（先红：当前输出无 sections）；structurize 分支 grep 确认无 core 终态写入 / `conn.commit()`。
- **本 Phase 风险提醒**：heading 启发式过拟合特定格式 → 用多样本（markdown / 纯文本 / 中文段落）测试覆盖；向后兼容字段须在 Phase 2 完成后清理，避免双供长期残留。

### 5.2 Phase 2 — construct chunk + summary 双通道 + rowid 复用

- **Phase 目标**：construct 对每 chunk 产 original + summary 双通道；chunk_id 确定性派生、upsert 复用 `embedding_rowid`，根除 R3 孤儿/重复。
- **本 Phase 对应编号**：`F6-05`
- **本 Phase 新增 / 修改 / 删除文件**：`rag_constructor/src/rag_constructor/service.py:4-21`（改造 build_chunks + 新增 build_summary）；`workflow_rag/src/workflow_rag/service.py:99-179`（双通道落库 + 确定性 chunk_id）；`vector_sqlite_vec/src/vector_sqlite_vec/store.py:32,126-130`（upsert 复用 rowid，与 F4-03 同窗口对齐）
- **具体功能预期**：
  1. `build_chunks` 消费 sections（section 边界优先 + max_chars 二次切分），每 chunk 含 text + section_path。
  2. `build_summary(chunk)` 产确定性规则摘要（section heading + 首句/截断，非 LLM），作为第二通道；summary 为空时跳过该通道（不落空向量）。
  3. construct 对每 chunk 落两条记录（channel=`original`/`summary`），chunk_id 确定性派生 `sha256(document_id:chunk_index:channel)`，**取代 uuid4()**（R3 根因）。
  4. upsert 复用 rowid：按 `(document_id, chunk_index, channel, content_hash)` 查既有 `vector_records` 命中则复用 `embedding_rowid`；同 run replay ⇒ 0 重复 chunk / 0 孤儿（先红：当前 uuid4 + 不传 rowid 必产孤儿）。
  5. original 通道注入上下文头 `[title/section_path]`（语义锚点，规则化 buildContentFull）。
  6. 边界/降级：空 sections → 0 chunk；layer-json 不产（O1 degraded 声明）；construct 分支按 F3-02 不写 run completed / step succeeded / 不 commit core。
- **对应测试台账项**：`FF-F6b-T03` / `FF-F6b-T04` / `FF-F6b-T05`（详见 §8）
- **收口标准**：unit 双通道产出 + summary 非空（T03）；rowid 复用回归（重 upsert 0 孤儿，T04，对齐 part-cr-3 实测复跑）；construct 分支无 core 终态/commit（T05）。
- **本 Phase 风险提醒**：rowid 复用须与 F4-03 store 侧修复同窗口（否则 store 仍 `_next_embedding_rowid` 重号）；双通道使向量记录翻倍，summary 通道空摘要必须跳过否则污染检索；确定性 chunk_id 与 F4 软硬删一致性联动（删通道时按 chunk_id 幂等）。

### 5.3 Phase 3 — 拆独立 rag:vectorize step

- **Phase 目标**：把向量化从 construct 内联剥离为独立 `rag:vectorize` step（可 claim/重试/重启），调 F5 Embedder（本地 1536），按五步序写跨库。
- **本 Phase 对应编号**：`F6-06`
- **本 Phase 新增 / 修改 / 删除文件**：`workflow_rag/src/workflow_rag/service.py:99-219`（construct 剥离向量化 + 新增 `rag:vectorize` 分支）；`rag_vectorizer/src/rag_vectorizer/embedder.py:6-16`（接 F5 Embedder，删 SHA-256 伪向量）；`apps/worker/src/smind_worker/main.py:49-50`（确认 `startswith("rag:")` 覆盖 vectorize）
- **具体功能预期**：
  1. construct 只产 chunk(`pending_vectorize`) + artifact + constructed_json，**不再内联 embed/upsert/vectorized 回写**。
  2. construct 经 `ExecutorResult.downstream` 声明下游 `rag:vectorize` step（不自插，内核 succeed_claim 创建）。
  3. 新增 `rag:vectorize` 分支：查本 run `pending_vectorize` 全部 chunk（original+summary）→ 调 F5 Embedder（1536）→ upsert（复用 rowid，传 content_hash）→ 回写 `vectorized`。
  4. 五步序（R5）：core chunk(pending) 已 commit → vectorize step upsert vec.db → 回写 core vectorized；崩溃 replay 依 `vec_status='pending_vectorize'` 幂等重做（复用 rowid + 确定性 chunk_id，0 重复向量）。
  5. vectorize step 独立 claim → 单独可 retry/restart；embedding 失败抛异常交内核 fail_claim（不自提交、不留半写）；0 pending → 空跑成功。
  6. 降级（失败路径）：F5 未就绪 → embedding 用确定性 mock 占位**并显式标注非交付向量**（测试 xfail，不当真向量）；vectorize 分支按 F3-02 返回 `ExecutorResult`（run 推进经内核）。
- **对应测试台账项**：`FF-F6b-T06` / `FF-F6b-T07` / `FF-F6b-T08`（详见 §8）
- **收口标准**：step 链测试 construct→独立 vectorize step claim→vectorized（T06）；真实 1536 向量语义命中（目标 chunk 排第一 + 分差显著，T07）；vectorize 重试不产重复向量（T08，依赖 rowid 复用 + 确定性 chunk_id）。
- **本 Phase 风险提醒**：拆步触碰执行器↔内核边界（F3-02 契约必须先就绪，否则 blocked）；F5 Embedder 是硬依赖（伪向量删除后若 F5 未就绪则 vectorize 无真实向量 → 降级 mock 须显式标注，不得当真）；五步序跨库一致性是 CR-7 R5 高风险点，崩溃窗口测试必须覆盖。

---

## 6. 依赖的冻结设计决策（只读引用）

> 不在本节填写新 Q/A；只引 register 的 Q 编号与红线/前序 AP，不复制内容。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[Q3]` 去桩增量（structurize/construct 真实但不追 legacy 全 AI 策略） | `docs/design/first-fixes/owner-gated-qna.md` Q3 / planning §2.C §6.6 | F6-04/05 做规则化真实结构化 + 规则摘要（非 LLM）；layer-json degraded（§2.2 O1） | 范围若被推翻须回 qna register，本 AP 保持 draft（blocked） |
| `[Q7]` 全 phase 先红后绿铁律 | `owner-gated-qna.md` Q7 / planning §4 | 每工作项以「先红后绿回归」为退出证据（§8 全项标先红后绿） | 不成立则退出判据失据，本 AP 不得标 executed |
| `F3-02` 执行器契约 `execute(step,deps)->ExecutorResult`（不自提交终态） | `FF-F3-kernel-recovery.md` F3-02 / planning §4 红线第 2 条 | rag 全部执行器（structurize/construct/vectorize）只产 ExecutorResult、不写终态/run/不 commit core；下游 step 经 downstream 声明由内核创建 | F3-02 未就绪 → 本 AP blocked（rag 执行器无契约可建），回退等 F3 |
| `F4-03` rowid 不变量（upsert 复用 embedding_rowid 不制造孤儿） | `FF-F4-adapter-safety.md` F4-03 / part-cr-3 G-CR3-03/04 | construct/vectorize 的 upsert 必须复用 rowid + 确定性 chunk_id（F6-05 e / F6-06 c）；store 侧修复同窗口 | F4-03 store 仍 `_next_embedding_rowid` 重号 → 本 AP rowid 复用无物理基底，blocked 待 F4 |
| `[Q1][Q2]` / F5 Embedder（本地 1536 维 + degraded 暴力 cosine） | `owner-gated-qna.md` Q1/Q2 / `FF-F5-vector-authenticity.md` | F6-06 vectorize step 调 F5 Embedder（1536 维真实 embedding，删伪向量） | F5 未就绪 → vectorize embedding 用 mock 占位**显式标注非交付**（测试 xfail），不当真向量 |

---

## 7. 内置 Reference-Anchor 锚区

> §7.1 摘自 `part-cr-7.md` / `part-cr-3.md` 的 file:line（真源见 §7.3）；本 AP 工作项落点就地钉住，实现时 0 跳转。

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `rag_structurizer/src/rag_structurizer/service.py:4-8` | `structurize_text` = `text.split("\n")` 朴素分段（9 行，缺 67%，G-CR7-03/R2） | F6-04 替换点：重写为结构化 schema 输出 | `🆕 净新` | 占位实现，本 AP 主替换点之一 |
| A-2 | `rag_constructor/src/rag_constructor/service.py:4-21` | `build_chunks` = 350 字符贪心拼接（22 行，缺 55%，G-CR7-04/R3）；无 summary | F6-05 替换点：消费 sections + 双通道 + build_summary | `🆕 净新` | 占位实现，本 AP 主替换点之一 |
| A-3 | `workflow_rag/src/workflow_rag/service.py:99-219` | construct 分支内联 chunk+embed+upsert+vectorized 回写 + 自提交 run/step（R6/R7） | F6-05/F6-06：剥离向量化、双通道落库、改返回 ExecutorResult | `♻️ 重 substrate` | 在既有 construct 编排上重建；删 `:209-233` 自提交 |
| A-4 | `workflow_rag/src/workflow_rag/service.py:159-168` | `upsert_chunk` 调用**未传 embedding_rowid** + `:106` chunk_id=`uuid4()`（R3/R4 触发点） | F6-05 e：改确定性 chunk_id + 复用 rowid | `✅ 复用` | CR-3/CR-7 实测孤儿触发点；改调用方式 |
| A-5 | `rag_vectorizer/src/rag_vectorizer/embedder.py:6-16` | `embed_text` = SHA-256 链式伪向量（17 行，零语义，G-CR7-01/R1） | F6-06 c：删伪向量，接 F5 Embedder（1536） | `🆕 净新` | 真实 embedding 归 F5；本 AP 在 vectorize step 接入 |
| A-6 | `vector_sqlite_vec/src/vector_sqlite_vec/store.py:32,126-130` | `rowid = embedding_rowid if ... else _next_embedding_rowid()`（MAX+1） | F6-05 e / F6-06 c：upsert 复用 rowid（与 F4-03 同窗口） | `✅ 复用` | store 物理修复归 F4-03；本 AP 维持调用侧不变量 |
| A-7 | `apps/worker/src/smind_worker/main.py:49-50` | `step["stage"].startswith("rag:")` → `process_rag_step`（已覆盖 rag:vectorize） | F6-06 f：确认派发覆盖新 stage，无需改 | `✅ 复用` | 已建好，别重写；仅确认 |
| A-8 | `workflow_rag/src/workflow_rag/service.py:82-98` | structurize 分支自插下游 `rag:construct` step | F6-04 / F3-02：删自插，改 ExecutorResult.downstream 声明 | `♻️ 重 substrate` | 下游 step 创建归内核 succeed_claim |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 执行器自 `conn.commit()` / 写 `status='succeeded'` / 写 run completed（违 F3-02） | `service.py:209-233` 现状即此；终态归内核 succeed_claim，执行器只产 ExecutorResult（planning §4 红线第 2 条 / G-CR4-03/R7） |
| ⛔2 | upsert 不传 `embedding_rowid` + chunk_id 用 `uuid4()`（违 F4-03，制造孤儿） | `service.py:106,159-168` 现状即此；part-cr-3 实测同 chunk 重 upsert → 孤儿 `[1,2]`、replay 无界累积（G-CR3-03/R3） |
| ⛔3 | 把向量化继续内联在 construct（违 G-CR7-05 内核硬约束） | 向量化无独立 step ⇒ 不能单独 retry/restart/purge，embedding 失败即整 construct 重跑喂养孤儿（R6） |
| ⛔4 | 为追 legacy 全 AI 结构化/摘要而接 LLM（违 [Q3]） | [Q3] 明确「真实但不追 legacy 全部 AI 策略」；本轮做确定性规则化，避免范围爆炸（数周） |
| ⛔5 | 把 layer-json 装成完成的桩 / 不声明 degraded | [Q3] 横切要求：不支持必须显式 degraded 声明 + 测试 skip/xfail + 不留装成完成的桩（§2.2 O1） |
| ⛔6 | vec.db 先 commit、core chunk 后 commit 的旧时序（违五步序，留 vec 孤儿） | part-cr-7 R5：崩溃窗口 vec 有向量 core 无 chunk；五步序 = core(pending) 先持久 → vec upsert → 回写 core vectorized |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：本 AP grounding 真源为 `docs/eval/first-code-review-plan/part-cr-7.md`（§2.1 Finding 表 R1-R11、§2.2 parity 矩阵含 file:line、§3.2 stub 标定表）与 `part-cr-3.md`（R3/R4 rowid 实测复跑）；§7.1 是其与本 AP 工作项相关子集的摘录，完整 legacy 对照（structurizer 2.9k / constructor 3.9k 行）见真源。
- **安全 / 信任边界类工作项的威胁模型锚**：本 AP 无新增安全/信任边界工作项（路径遍历 / object_key 校验归 F4，API key 归 F6c）。本 AP 的数据完整性约束（rowid 不变量 / 五步序）锚在 §7.1 A-4/A-6 + part-cr-3 R3/R4 实测、part-cr-7 R5 —— 不留空。

---

## 8. 测试台账

> 先红后绿（[Q7]）：每项先在当前 HEAD FAIL、修复后 PASS。词表用仓内真实用语。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `FF-F6b-T01` | structurize 输出结构化 schema（含 `sections`/`schema_version`/`context_meta`），**非裸 paragraphs**；heading 切分正确 | 短途 | unit | `🆕 新增 tests/unit/test_rag_structurize.py` | `F6-04 → structurize 输出结构化 schema 非裸 paragraphs` | `commit {sha} + test_rag_structurize PASS + {YYYY-MM-DD HH:MM UTC}` |
| `FF-F6b-T02` | structurize 分支无 core 终态写入 / `conn.commit()`（遵 F3-02），返回 ExecutorResult | 短途 | 契约 | `🆕 新增 tests/unit/test_rag_executor_contract.py` | `F6-04 → 执行器不自提交终态` | `commit + test + run-time` |
| `FF-F6b-T03` | construct 产 **original + summary 双通道**，summary 非空（空摘要通道跳过）；上下文头注入 | 短途 | unit | `🆕 新增 tests/unit/test_rag_construct_channels.py` | `F6-05 → 产 chunk+summary，不止 chunk_text` | `commit + test + run-time` |
| `FF-F6b-T04` | construct→upsert 复用 `embedding_rowid` + 确定性 chunk_id：**同 run replay 0 孤儿 / 0 重复 chunk** | 短途 | 集成 | `🔱 fork part-cr-3 R3 复跑断言（同 chunk upsert×3 验孤儿）+ 加 construct 调用侧断言` | `F6-05 → upsert 复用 rowid 0 孤儿（F4-03）` | `commit + test + run-time` |
| `FF-F6b-T05` | construct 分支无 core 终态 / run completed / commit（遵 F3-02） | 短途 | 契约 | `♻️ 沿用 tests/unit/test_rag_executor_contract.py（扩 construct 断言）` | `F6-05 → 执行器不自提交终态` | `commit + test + run-time` |
| `FF-F6b-T06` | 独立 `rag:vectorize` step：construct 产 `pending_vectorize` → 内核创建下游 vectorize step → 独立 claim 执行 → `vectorized`；可单独 retry | spike | 集成 | `🆕 新增 tests/integration/test_rag_step_chain.py` | `F6-06 → vectorize 是独立可重试 step` | `commit + spike PASS + run-time` |
| `FF-F6b-T07` | 真实 1536 维 embedding 语义命中：相关 query 的目标 chunk 排第一且分差显著（伪向量删除/标桩） | spike | live | `🔱 fork F5 向量真实性 spike + 加 rag 端到端 chunk 命中断言` | `F6-06 → 调 F5 Embedder 真实向量` | `commit + spike PASS + run-time` |
| `FF-F6b-T08` | vectorize 五步序 + 重试幂等：崩溃/重跑后 0 重复向量、0 vec 孤儿（依 rowid 复用 + 确定性 chunk_id） | soak | live(D1) | `🆕 新增 tests/integration/test_rag_vectorize_replay.spike.test`（race / 长稳 ×N） | `F6-06 → 重试不产重复向量（五步序 + 幂等）` | `commit + soak log + run-time` |

**列定义（填法约束）**：
- **类型**：`短途`（每 PR 快测）/ `spike`（阶段性 journey 验证）/ `mega`（长程整合，本 AP 入 §8 capstone E/F 步）/ `soak`（race / 长稳 deterministic × N）。
- **层**：`unit` / `集成` / `契约`（seam）/ `回归` / `e2e` / `live`。
- **来源**：`🆕 新增` 点名新建 `tests/...`；`♻️ 沿用` 点名既有用例；`🔱 fork` 点名 base + 加的断言。
- **PASS 证据**：四元组 `commit + 测试/查询名 + run-time(UTC)`（防假绿见 §8.5）。

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `part-cr-3.md` R3 实测复跑（同 chunk upsert×3 验孤儿 `[1,2]`） | `🔱 fork → tests/integration（construct 调用侧）` | `+ construct 确定性 chunk_id + 复用 rowid 后 0 孤儿断言` | 已在 part-cr-3 实测复现（当前红） |
| `FF-F5-vector-authenticity.md` 向量真实性 spike（目标 chunk 排第一 + 分差） | `🔱 fork → tests/integration/test_rag_step_chain` | `+ rag 端到端 chunk 命中断言` | F5 交付后 PASS，本 AP 接入 rag 链 |
| `tests/unit/test_rag_executor_contract.py`（T02 建） | `♻️ 沿用（T05 扩 construct 断言）` | `+ construct 分支无终态断言` | T02 建后 PASS，纳入回归 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·契约·集成 | 开发中持续（T01-T05） |
| spike | journey 用例 | 集成·live | 每 Phase 收口（T06 Phase 3 / T07 Phase 3） |
| mega | 长程整合全链（capstone E/F 步） | live 全链 | **本 AP 收口**（纳入 planning §8 capstone） |
| soak | deterministic × N（vectorize replay race） | live(D1) | **退出硬闸**（T08） |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 layer-json 产物（理由：[Q3] degraded，O1）→ 交后继去桩轮；**不在本 AP 假装覆盖**，测试对 layer-json 标 `xfail`/`skip`（机器可读 reason=`out-of-scope-by-Q3`）。
- 不覆盖真实 vec0 KNN / 外部 API embedding（理由：归 F5 [Q1][Q2] degraded）→ 交 F5 / 生产化轮。
- 不覆盖 search namespace/model 过滤（R8/F5-03）、channel 级精细 purge（R10）→ 交 F5 / follow-up。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带**四元组**证据；**计数 ≠ 价值**（对齐 closure 诚实收口）。
- `degraded` 必带机器可读 `reason`：layer-json = `out-of-scope-by-Q3`；F5 未就绪时 embedding mock = `f5-embedder-pending-not-delivery-vector`。
- 伪向量 `embed_text`（embedder.py:6-16）删除或显式重命名为测试桩（如 `embed_text_fake`），**禁止**在交付路径作为真向量（对齐 part-cr-7 R1 建议）。
- 数据完整性项（rowid 不变量 T04 / 五步序 T08）必须含**重跑/崩溃窗口**用例（对应 §7.3 part-cr-3 R3/R4 + part-cr-7 R5），不得只测 happy-path。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| F3-02 执行器契约未就绪 | rag 执行器无 `ExecutorResult` 契约可建，下游 step 创建无归属 | high | 本 AP 前序硬依赖；F3-02 未就绪则 blocked，不强行自插 step/自提交 |
| F4-03 rowid 不变量未就绪 | store 仍 `_next_embedding_rowid` 重号，construct 复用 rowid 无物理基底 | high | 与 F4-03 同窗口；store 侧修复未到位则 T04 红，blocked 待 F4 |
| F5 Embedder 未就绪 | vectorize step 删伪向量后无真实 1536 向量 | medium | 降级：mock 占位 + 显式标注非交付（reason=`f5-embedder-pending`），测试 xfail，不当真向量 |
| 五步序跨库一致性 | vectorize 崩溃窗口留 vec 孤儿（R5） | high | 五步序 + replay 依 pending_vectorize 幂等重做（复用 rowid + 确定性 chunk_id）；soak T08 覆盖 |
| heading 启发式过拟合 | structurize 规则对非常规格式切分失真 | medium | 多样本测试（md/纯文本/中文）；规则保守，无 heading 归默认 section |
| 双通道使向量记录翻倍 | summary 通道放大孤儿/检索污染风险 | medium | 空摘要跳过通道；rowid 复用 + 确定性 chunk_id 控制；T04/T08 验证 |
| layer-json degraded 被误判完成 | 装成完成的桩重蹈假绿 | low | 显式 degraded 声明 + 测试 xfail（reason）+ 交 F7 closure 定级 |

### 9.2 约束与前提

- **技术前提**：F3-02 契约（`ExecutorResult`）、F4-03 rowid 修复、F5 Embedder 三者就绪或同窗口推进；F1-04 autocommit + 多写包 BEGIN 已 keystone。
- **运行时前提**：本地 1536 维 embedding 模型可加载（F5）；向量索引 degraded 暴力 cosine（[Q1]，数据量小时正确）。
- **组织协作前提**：rowid 复用与 F4-03 store 修复需同窗口协调，避免两次触碰 store。
- **上线 / 合并前提**：三 Phase 先红后绿全 PASS；layer-json degraded 显式记账；伪向量删除/标桩。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/design/first-fixes/initial-planning-by-opus.md`（§6.6 F6-04/05/06 状态回填，executed 时）。
- 需要同步更新的说明文档 / README：RAG 包 README（structurize schema / 双通道 / vectorize step 说明，如有）。
- 需要同步更新的测试说明：`FF-F7-test-integrity.md`（本 AP 先红后绿回归纳入 F7 整合 lane；layer-json degraded 进 closure 定级）。

### 9.4 完成后的预期状态

1. structurize 输出结构化 schema（sections + context_meta 骨架），下游 construct 可消费层级结构，不再是裸 paragraphs。
2. construct 产 original + summary 双通道，召回面恢复；chunk_id 确定性派生、upsert 复用 rowid，重复执行 0 孤儿（R3 闭环）。
3. 向量化成为独立 `rag:vectorize` step，可单独 claim/重试/重启；调 F5 Embedder（真实 1536 向量），按五步序写跨库（R5/R6 闭环）。
4. rag 全部执行器遵守 F3-02 契约（不自提交终态），G-CR4-03/R7 在 rag 侧闭环。
5. layer-json 显式 degraded 记账（不留装成完成的桩），交下一轮；全 AP 先红后绿回归纳入 F7。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

> 收口 = §8 测试台账逐项 PASS，且每项映射回 §3 工作项收口目标。

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 测试项必须 **PASS 且四元组证据齐全**：

1. 真实 1536 向量语义命中（相关 chunk 排第一 + 分差显著）（由 `FF-F6b-T07` 证明）。
2. 独立 `rag:vectorize` step 可 claim/重试/重启（由 `FF-F6b-T06` 证明）。
3. vectorize replay 0 重复向量 / 0 孤儿（五步序 + rowid 复用幂等）（由 `FF-F6b-T08` soak 证明）。
4. capstone E/F 步（rag structurize 结构化 + construct chunk+summary + 独立 vectorize + 1536 向量）通过（纳入 planning §8 capstone，degraded layer-json 步标 xfail）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| structurize 输出结构化 schema 非裸 paragraphs | `F6-04` | `FF-F6b-T01` | `commit + test_rag_structurize + run-time` | `未观察`（draft） |
| structurize 执行器不自提交终态 | `F6-04` | `FF-F6b-T02` | `commit + test + run-time` | `未观察` |
| construct 产 chunk+summary 双通道 | `F6-05` | `FF-F6b-T03` | `commit + test + run-time` | `未观察` |
| upsert 复用 rowid 0 孤儿（F4-03） | `F6-05` | `FF-F6b-T04` | `commit + test + run-time` | `未观察` |
| construct 执行器不自提交终态 | `F6-05` | `FF-F6b-T05` | `commit + test + run-time` | `未观察` |
| vectorize 是独立可重试 step | `F6-06` | `FF-F6b-T06` | `commit + spike + run-time` | `未观察` |
| 调 F5 Embedder 真实 1536 向量命中 | `F6-06` | `FF-F6b-T07` | `commit + spike + run-time` | `未观察` |
| vectorize 重试不产重复向量（五步序+幂等） | `F6-06` | `FF-F6b-T08` | `commit + soak log + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | structurize 结构化 schema + construct 双通道 + 独立 rag:vectorize step（调 F5 1536 向量）三项落地，遵 F3-02 契约 + F4-03 rowid |
| 测试 | §8 测试台账全 PASS（退出硬闸 T06/T07/T08 四元组齐全） |
| 文档 | layer-json degraded 显式记账（reason）；planning §6.6 状态回填；交 F7 closure 定级 |
| 风险收敛 | R3 孤儿 / R5 五步序 / R6 内联向量化 / R7 自提交在 rag 侧闭环 |
| 可交付性 | 伪向量删除/标桩；degraded 项不留装成完成的桩 |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**；按 closure 五态（`verified / observed-OK-at-closure / partial / 未观察 / deferred`）如实归类 + handoff，不 silent overclaim。F5 未就绪导致 T07 用 mock ⇒ 该项标 `partial`（reason=`f5-embedder-pending`）+ handoff，不当真向量绿。

---

## 11. 执行日志回填（`executed` — 2026-06-01）

> 文档状态: `draft → executed`。执行人 Opus 4.8（主轨直接执行，未用收尾子代理）。提交 `36af537`。前序 F1-F5（含 F3-02 契约/F4-03 rowid/F5 Embedder）已收口。全量 `python3 -m pytest tests/` → **175 passed**（exit 0；F6b 前 161 → 新增 14 用例）。

### 11.1 环境
- 系统 python3，无外网。structurize/construct 均**确定性规则化（非 LLM，[Q3]/O2/O3）**：heading 启发式 + 句子边界切分 + 规则摘要。F5 Embedder 已就位，vectorize 调 `default_embedder()`（本地 1536）。

### 11.2 逐工作项
- **F6-04 structurize schema**：`rag_structurizer/service.py` 重写——`structurize_text` 返回 `{schema_version:"v1", context_meta:{title,source_hint}, sections:[{heading,level,text,order}], section_count, paragraphs(兼容), paragraph_count}`。heading 启发式：markdown `#{1,6}`、数字编号 `\d+[.、)]`、全大写短行（≤60，拉丁）。leading body→默认 section(level 0)。title 取首个 level-1 heading。
- **F6-05 construct 双通道 + 确定性 chunk_id**：`rag_constructor` 增 `build_section_chunks`(消费 sections，section 边界优先 + 句子边界 max_chars 二次切分，带 section_path) + `build_summary`(规则摘要：section_path + 首句/截断，非 LLM) + `with_context_header`(原文注入 `[title/section_path]` 锚点)；保留 `build_chunks` 兼容。`workflow_rag` construct：每 chunk 产 **original + summary 双通道**，`chunk_id=sha256(document_id:index:channel)`（取代 uuid4，replay 幂等），`content_hash=sha256(channel:text)`（满足 `UNIQUE(document_id,content_hash)`），chunk_index 用全局 row_index（满足 `UNIQUE(document_id,chunk_index)`），双通道各落 chunk_text artifact(object_store) + chunks(pending_vectorize)。upsert rowid 复用由 F4-03 store 按 chunk_id 自动保证。
- **F6-06 拆独立 rag:vectorize step**：construct **删内联 embed/upsert/vectorized 回写**，仅落 chunk(pending_vectorize) + artifact + constructed_json，经 `ExecutorResult.downstream` 声明 `rag:vectorize` step（内核 succeed_claim 创建）+ run_advance running/rag:vectorize。新增 `rag:vectorize` 分支：查本 run `vec_status='pending_vectorize'` chunk（含双通道）→ 从 content_artifact object_key 取文本 → `default_embedder().embed`（1536）→ `upsert_chunk`（content_hash + F4-03 复用 rowid）→ 回写 vectorized → run_advance completed。五步序（CR-7 R5）：core chunk(pending) 由 construct step 持久 → vectorize upsert vec → 回写 core vectorized；崩溃 replay 依 pending_vectorize 幂等重做。worker `startswith("rag:")` 已覆盖（A-7 确认，无需改派发）。

### 11.3 先红后绿（14 新用例，全 PASS · 四元组证据）
| Test-ID | 文件::用例 | 红基线 | PASS 证据 |
|---------|-----------|--------|-----------|
| FF-F6b-T01 | `test_rag_structurize.py`（schema 非裸 paragraphs/heading 切分/title/默认 section/兼容/空，6 用例） | 旧返回 `{paragraphs}` 无 sections（红） | `36af537 + test_rag_structurize(6) + 2026-06-01 04:01 UTC` |
| FF-F6b-T03 | `test_rag_construct_channels.py`（section_path/summary 非空用 heading/空摘要/上下文头/二次切分，5 用例） | 无 build_section_chunks/build_summary（import 红） | `36af537 + test_rag_construct_channels(5) + 2026-06-01 04:01 UTC` |
| FF-F6b-T02/T04/T05/T06/T08 | `test_rag_step_chain.py`（独立 vectorize step 成功 + construct/vectorize 分立 + 双通道 original+summary + 全 vectorized + run completed；重放 0 重复 chunk/vec；契约无自提交，3 用例） | 向量化内联无独立 step + uuid4 replay 重复（红） | `36af537 + test_rag_step_chain(3) + 2026-06-01 04:01 UTC` |

- **FF-F6b-T07（真实 1536 语义命中）**：由 p5 全链（url→clean htmlCrawl→structurize→construct 双通道→独立 vectorize→F5 embed→search 按 model 过滤命中）+ F5 `test_f5_vector_authenticity` 共同覆盖；rag 链现真实喂 F5 embedding。
- 全量回归：`python3 -m pytest tests/` → **175 passed**（exit 0；161 + 14）。

### 11.4 偏差与 handoff
- **双通道 chunk_index 编码**：chunks 有 `UNIQUE(document_id, chunk_index)` + `UNIQUE(document_id, content_hash)`；original/summary 用全局递增 row_index 作 chunk_index、channel 入 content_hash，确定性 chunk_id 用 logical index+channel——既满足两个唯一约束又保 replay 幂等。
- **structurize/construct 为确定性规则化（非 LLM）**：[Q3]/O2/O3 明确不追 legacy 全 AI 策略；summary 是规则摘要（heading+首句），保留通道结构供未来替换真实 AI 摘要。如实记账，不冒充 AI。
- **deferred（A/B/C）**：layer-json 产物（O1, A→下一轮）、legacy 全 AI 结构化/摘要（O2/O3, A）、真实 vec0/外部 embedding/search 过滤/channel 级 purge（O4, A/C→F5 已部分、其余下一轮）。
- **handoff**：T07 端到端语义命中的独立 capstone 步交 F7；soak（vectorize replay race 长稳 T08 的 ×N 版）交 F7/退出硬闸（本 AP 已覆盖单次重放幂等）。FF-F6c 共用本 AP 的执行器契约。
