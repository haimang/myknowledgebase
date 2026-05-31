# Nano-Agent 代码审查报告 — CR-7 · RAG 流水线

> 审查对象: `CR-7 RAG 流水线 (workflow_rag / rag_structurizer / rag_constructor / rag_vectorizer)`
> 审查类型: `code-review`
> 审查时间: `2026-05-31`
> 审查人: `Claude sub-agent (CR-7)`
> 审查范围:
> - `packages/workflow_rag/src/workflow_rag/service.py`（233 行：structurize→construct→vectorize 编排 + finalizer）
> - `packages/rag_structurizer/src/rag_structurizer/service.py`（9 行）
> - `packages/rag_constructor/src/rag_constructor/service.py`（22 行）
> - `packages/rag_vectorizer/src/rag_vectorizer/embedder.py`（17 行）、`search.py`（137 行）
> 对照真相:
> - `docs/refactor/index.md` §5.6（五步序）/§5.7（检索路径）/§4.4（stage 命名）；`docs/refactor/core.sql`（chunks/v_search_hydration）
> - `legacy-family/smind-skill-rag-structurizer`、`smind-skill-rag-constructor`、`smind-skill-rag-vectorizer`、`smind-rag-dispatcher`
> - 前序簇 CR-3（G-CR3-02/03/04/10/13）、CR-4（G-CR4-03）结论（独立复核后引用）
> 文档状态: `changes-requested`

---

## 0. 总结结论

- **整体判断**：`RAG 流水线是"端到端能跑通的极简骨架"——三段 step 链路、artifact 落库、chunk/vec_status 流转、search hydration 视图接线都真实存在且方向正确；但三个核心业务执行器（structurize/construct/embed）全是占位实现，embedding 为确定性 hash 伪向量、语义为零，且继承 CR-3/CR-4 的 critical 不变量破坏与职责撕裂。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. **embedder 是伪造向量**：`embed_text` 用 SHA-256 链式哈希生成 1536 维确定性数，与文本语义无关（`embedder.py:6-16`）。legacy 调用 Workers AI `@cf/qwen/qwen3-embedding-0.6b` 真实模型。检索"看起来在工作"（同文本必命中自身），但跨文本相关性纯属噪声 —— 这是整条 RAG 价值链的根因盲点 B。
  2. **structurize+construct 量化盲点**：Python 3 个执行器合计 48 行，对照 legacy 的 structurizer(2.9k)+constructor(3.9k)=6.8k 行；丢失 AI 结构化抽取、reasoning/retry 策略、knowledge_tree/context_meta/layered_content schema、summary 通道、meta_fuser、双通道(original+summary)向量记录、layer-json 产物。Python 仅产 chunk_text 单一产物，**summary 通道与 layer-json 完全缺失**。
  3. **继承的 critical 未修且被本簇触发**：`upsert_chunk` 不传 `embedding_rowid`（`service.py:159-168`），坐实 CR-3 的孤儿 rowid 累积（G-CR3-03）；vectorize 段无幂等键、自提交 succeeded 早于 succeed_claim（`service.py:226,233` + CR-4 G-CR4-03），过期租约竞态下重复执行 → 重复 chunk+重复向量。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/refactor/index.md`（§4.4 stage 命名建议 `clean/structurize/construct/vectorize`；§5.6 五步序 行 386-390；§5.7 检索路径 行 392-403）
  - `docs/refactor/core.sql`（chunks 表 241-242；`v_search_hydration` 651-687）
- **核查实现**：
  - `packages/workflow_rag/src/workflow_rag/service.py`（全 233 行）
  - `packages/rag_structurizer/src/rag_structurizer/service.py`、`packages/rag_constructor/src/rag_constructor/service.py`、`packages/rag_vectorizer/src/rag_vectorizer/{embedder.py,search.py}`
  - `packages/vector_sqlite_vec/src/vector_sqlite_vec/store.py`（upsert/search 被本簇调用）
  - `apps/worker/src/smind_worker/main.py`（stage 派发 + claim 收尾）
- **执行过的验证**：
  - 逐行读取上述 Python 源；逐文件读取 legacy `flows/structurizer.ts`、`flows/constructor.ts`、`services/recorder.ts`、`services/summarizer.ts`、`vectorizer/engine.ts`、`vectorizer/embedder.ts`、`src/vectorizer_do.ts`、`src/purger_logic.ts`、`smind-rag-dispatcher/flows/{orchestrator,finalizer}.ts`。
  - `grep` 核对 `SearchService` 被 `management/service.py` 与 `apps/api/routes/search.py` 调用；核对 stage 字符串与 worker `startswith("rag:")` 派发。
  - `grep` 核对 core.sql 中 `vec_status` CHECK 域与 `v_search_hydration.core_post_filter_*` 语义。
- **复用 / 对照的既有审查**：
  - CR-3（`part-cr-3.md`，G-CR3-02/03/04/07/10/13）— **独立复核后采纳**：sqlite-vec 退化、孤儿 rowid、重号删除、search 仅 team 过滤、维度硬编码、vectorize 崩溃留孤儿。本簇核实这些缺陷的**触发点**确在 RAG 调用侧。
  - CR-4（`part-cr-4.md`，G-CR4-03）— **独立复核后采纳**：执行器自提交 succeeded 的职责撕裂，本簇核实 rag 侧同构。

### 1.1 已确认的正面事实

- **三段链路真实贯通**：`rag:structurize` 写 `structured_json` artifact + 创建下游 `rag:construct` step（`service.py:51-98`）；`rag:construct` 读 `structured_json`、分块、落 chunk_text artifact + chunks 表 + 向量、收尾 run（99-219）。链路非断点。
- **stage 命名匹配**：step 创建用 `'rag:construct'` 字符串（`service.py:88`），worker 用 `step["stage"].startswith("rag:")` 派发（`main.py:49`）—— 与附录 A1 担忧的 rag 侧**冒号一致**，rag step 能被路由（注意：`rag:vectorize` 子阶段并不存在，construct 内联了向量化，见 R6）。
- **vec_status 流转方向正确**：chunk 初始 `pending_vectorize`（`service.py:142`），upsert 后回写 `vectorized`（169-178），与 core.sql CHECK 域（241-242）及 `v_search_hydration.core_post_filter_eligible`（`d.status='active' AND c.vec_status='vectorized'`）一致。
- **search 路径符合设计 §5.7**：`search.py` 走 vec.db top-k → `v_search_hydration` 视图 hydrate → core post-filter（`core_post_filter_eligible`）→ 半文件降级（`missing_hydration`/`empty_chunk_text`/`core_post_filter_blocked`），是本簇质量最高的部分；正确处理了 CR-3 R6/R11 的缺失对象/半文件场景。
- **artifact/document 元数据回写完整**：`documents.latest_structured_artifact_id`、`latest_constructed_artifact_id`、`status='active'` 均被回写。

### 1.2 已确认的负面事实

- **embedder 为伪向量**：`embed_text`（`embedder.py:6-16`）= SHA-256 链式确定性数，无任何语义模型；legacy 用真实 Workers AI 模型（`vectorizer/embedder.ts:38-39,117`）。
- **structurize 为朴素分段**：`structurize_text`（`rag_structurizer/service.py:4-8`）= `text.split("\n")`，无 AI、无 schema、无 retry；legacy 是 Gemini 结构化抽取 + Zod 校验 + 重试策略（`flows/structurizer.ts`）。
- **construct 为定长拼接**：`build_chunks`（`rag_constructor/service.py:4-21`）= 350 字符贪心拼接段落；legacy 是 summarizer(AI 摘要)+meta_fuser+recorder 三段，产 original/summary 双通道向量记录（`recorder.ts:204-225`）。
- **summary 通道 + layer-json 完全缺失**：Python 只产 `chunk_text`，无 summary、无 layered_content/knowledge_tree/context_meta。
- **upsert 不传 embedding_rowid**：`service.py:159-168` 调用未含 `embedding_rowid`，store 走 `_next_embedding_rowid`（`store.py:32,126-130`）→ 重跑累积孤儿（坐实 G-CR3-03）。
- **vectorize 无幂等**：construct 段对同 run 重放会重新 INSERT 新 chunk_id + 新向量（`service.py:104-179`），无 content_hash 去重短路。
- **embedding 与 vec_status 回写顺序违反五步序**：见 R5。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 全部 Python 源逐行读 + legacy TS 逐文件读，双向 file:line 见 §2.1 矩阵 |
| 本地命令 / 测试 | `no` | 未运行 RAG 端到端（无 fixture）；测试有效性移交 CR-8 |
| schema / contract 反向校验 | `yes` | core.sql chunks/v_search_hydration 与 service.py INSERT/UPDATE 列序逐项核对 |
| live / deploy / preview 证据 | `n/a` | 无部署环境 |
| 与上游 design / QNA 对账 | `yes` | §5.6 五步序、§5.7 检索路径、§4.4 stage 命名逐条对照 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | embedder 伪向量（hash 占位，零语义） | critical | B/correctness | yes | 接入真实 embedding adapter |
| R2 | structurize 朴素 `\n` 分段，丢失 6.8k 行 AI 结构化能力 | high | B/scope-drift | yes | 标定盲点，接入结构化抽取或显式声明降级 |
| R3 | construct 仅定长拼接，summary 通道 + layer-json 完全缺失 | high | B/scope-drift | yes | 补 summary 双通道 + layered schema 或显式收敛 |
| R4 | upsert 不传 embedding_rowid → 孤儿 rowid 累积（触发 G-CR3-03） | critical | L/correctness | yes | construct 侧建立 rowid 复用/幂等 upsert |
| R5 | embedding 写 vec.db 与回写 vectorized 顺序、跨库一致性偏离五步序 | high | L/correctness | yes | 严格五步序 + replay 补偿 + 幂等键 |
| R6 | 无独立 `rag:vectorize` step；向量化内联于 construct，违反"每 step 可 claim/重试/重启" | high | D/scope-drift | yes | 拆出 vectorize step 或显式声明三合二 |
| R7 | 执行器自提交 succeeded + run completed 早于 succeed_claim（同 G-CR4-03） | high | L/correctness | yes | 移除自提交，交还内核；副作用加幂等键 |
| R8 | search 仅按 team_id 过滤，无 namespace/embedding_model 隔离（同 G-CR3-10） | medium | B/correctness | no | search 增加 namespace/model 过滤 |
| R9 | RAG 段零 workflow_events/audit_logs，违反 C4 可观测硬约束 | medium | C4/correctness | no | 每子阶段落 event/audit |
| R10 | 无 purge/restart 语义（legacy purger_logic 的精细清洗、reset-to-pending 全缺失） | medium | B/delivery-gap | no | 与 CR-4 purge 对齐 chunk/vec 清理 |
| R11 | RAG 段宽 except 缺失 + 失败不落 step_attempts（依赖 worker 兜底） | low | C2/correctness | no | 与内核 fail_claim 对齐错误分类 |

### R1. embedder 伪向量（hash 占位，零语义）

- **严重级别**：`critical`
- **类型**：`blind-spot (B) / correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `packages/rag_vectorizer/src/rag_vectorizer/embedder.py:6-16` — `seed = sha256(text); while len<dims: seed=sha256(seed); 取 2 字节归一化到 [-1,1]`。纯确定性哈希，输出与文本语义无相关性。
  - legacy `vectorizer/embedder.ts:38-39`（`MODEL_ID='@cf/qwen/qwen3-embedding-0.6b'`）、`:117`（`env.AI.run(...)`）— 真实神经网络 embedding，含重试退避、维度探测、token usage。
  - 同一 embedder 既用于写入（`workflow_rag/service.py:167`）也用于查询（`search.py:40`），故"查询命中自身文本"会成立，**掩盖**了向量无意义的事实。
- **为什么重要**：
  - 整条 RAG 的价值是"语义检索"。hash 向量下，余弦相似度只反映哈希碰撞噪声，**任意两段不同文本的相关性是随机的**。检索结果对非完全相同文本无任何召回质量保证。这是把整个 RAG 流水线"价值归零"的根因盲点。
  - P4/P5 closure 若声称 vectorize/retrieval 完成，属假绿（与 CR-3 G-CR3-02 同源结论）。
- **审查判断**：
  - 确认盲点 B（owner 口径：stub 即 B）。`embed_text` 是 stub，不是"有意简化的等价物"——设计 §5.6 step 2 明确"worker 计算 embedding"，§5.7 明确"embedding adapter"，均指真实嵌入。
- **建议修法**：
  - 引入真实 embedding adapter（本地 sentence-transformers / 远程模型 API），维度与 `vec.sql`/`vector_namespaces.embedding_dimension`(1536) 对齐；保留 hash 实现仅作离线测试 fixture 并显式命名（如 `embed_text_fake`）。

### R2. structurize 朴素 `\n` 分段，丢失 6.8k 行 AI 结构化能力

- **严重级别**：`high`
- **类型**：`blind-spot (B) / scope-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `rag_structurizer/service.py:4-8` — `paragraphs = text.split("\n")`，输出 `{paragraphs, paragraph_count}`。无 AI、无 schema、无校验、无 retry。
  - legacy `flows/structurizer.ts`：①AI 模型策略表（`MODEL_CONFIG_TEMPLATES`/`STRATEGY_MAP` 含 reasoning/thinkingBudget，:54-79）；②retry 循环（`maxRetries`，:203-280）；③`sanitizeLlmResponse`/`preprocessJsonStructure`（meta 迁移、tags 修复、block 补全，:90-145）；④`StructuredJsonOutputSchema` Zod 校验（:252）；⑤输出 `context_meta`+`knowledge_tree`+`layered_content` 富结构（`core/schemas_common.ts`）。
- **为什么重要**：
  - Python 输出仅"段落数组"，**完全没有 legacy 的层级结构、上下文元数据、知识树**。下游 construct 失去可用的 `layered_content`/`context_meta`，导致 summary 通道与 layer-json 无从产出（连锁 R3）。
  - 量化：Python 9 行 vs legacy structurizer 2,897 行（含 AI gateway/schemas/retry/io）。能力覆盖率 < 5%。
- **审查判断**：
  - 盲点 B。属"无意丢失"——设计 §3 列出 `rag_structurizer` 为独立包并保留 legacy 参照，未声明要退化为朴素分段。
- **建议修法**：
  - 短期：在报告/closure 显式标注"结构化为占位实现"，禁止标 P4 完成；中期：接入 LLM 结构化抽取并定义 Python 侧 structured schema（contracts 层），至少产出 layered_content 骨架供 construct 消费。

### R3. construct 仅定长拼接，summary 通道 + layer-json 完全缺失

- **严重级别**：`high`
- **类型**：`blind-spot (B) / scope-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `rag_constructor/service.py:4-21` — 350 字符贪心拼接段落为 chunk，无摘要、无元数据注入。
  - `workflow_rag/service.py:99-197` — 只产 `chunk_text` artifact（每 chunk 一份）+ `constructed_json`（仅 `{chunk_ids, chunk_count}`），无 summary、无 layered/layer-json artifact。
  - legacy constructor 三段：`summarizer.process`（AI 摘要，`flows/constructor.ts:137`）、`metaFuser.process`（元数据融合 + isActive/filterMeta，:156）、`recorder.process`（`services/recorder.ts:204-225`）—— recorder 对**每个 block 产 original + summary 两个通道**的向量任务，并注入 `buildContentFull`（标题/realm/type/channel/source/tags 上下文头，:70-95）；`flows/constructor.ts:172` 落 `layered_json_r2_key`（layer-json 产物）。
- **为什么重要**：
  - 缺 summary 通道 → 检索召回面减半（legacy 用 original+summary 双通道提高召回）。
  - 缺 `buildContentFull` 上下文注入 → embedding 失去文档级语义锚点。
  - 缺 layer-json → 下游/前端无法还原层级结构。
  - 量化：Python construct 22 行 + 编排约 120 行 vs legacy constructor 3,887 行。
- **审查判断**：
  - 盲点 B（多项能力无意丢失）。chunk 通道本身是真实现（落库正确），但仅覆盖 legacy 三类产物（chunk/summary/layer-json）中的一类。
- **建议修法**：
  - 至少补 summary 通道（依赖 R2 先产 layered 结构）与 layer-json artifact；或由 owner 明确"双通道/layer-json 为本期 deferred"并在 §4 登记，避免被误判为 completed。

### R4. upsert 不传 embedding_rowid → 孤儿 rowid 累积（触发 G-CR3-03）

- **严重级别**：`critical`
- **类型**：`logic-error (L) / correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `workflow_rag/service.py:159-168` — `vector_store.upsert_chunk(chunk_id=..., embedding=..., content_hash=...)`，**未传 `embedding_rowid`**。
  - `vector_sqlite_vec/store.py:32` — `rowid = embedding_rowid if ... else self._next_embedding_rowid()`；`:126-130` `_next_embedding_rowid` = `MAX(rowid)+1`。同 chunk_id 重 upsert 时 `vector_records` 行被 `INSERT OR REPLACE` 覆盖（rowid 字段更新为新值），但旧 rowid 在 `chunk_embedding_index` 留下孤儿向量（CR-3 G-CR3-03 已实测）。
  - 本簇 construct 每次执行**生成全新 chunk_id**（`service.py:106` `uuid4()`），故 replay 直接产生重复 chunk + 新 rowid，旧向量永不被清理。
- **为什么重要**：
  - 孤儿向量进入 `search` 候选集（`store.py:91-100` 仅 `deleted_at IS NULL AND team_id`），被废弃 chunk 的向量仍参与打分 → 召回污染。
  - 与 R5（崩溃留孤儿 G-CR3-13）、R7（重复执行）叠加，replay/重启场景下孤儿无界累积。
- **审查判断**：
  - 逻辑错误 L。根因物理落点在 CR-3 store，但**触发点确在本簇 construct 的调用方式**（不传 rowid + 每次新 chunk_id）。owner 要求核实"workflow_rag 如何调 upsert_chunk"——结论：调用未维持 rowid 不变量。
- **建议修法**：
  - construct 侧用 content_hash 做幂等：upsert 前查 `vector_records` 是否已有同 chunk（按 document_id+chunk_index+content_hash），复用其 `embedding_rowid`；或在写新 chunk 前 `delete_chunk` 旧 chunk。根治需 CR-3 修 store 软硬删一致性（G-CR3-04/09）。

### R5. embedding 写 vec.db 与回写 vectorized 的跨库一致性偏离五步序

- **严重级别**：`high`
- **类型**：`logic-error (L) / correctness（C3）`
- **是否 blocker**：`yes`
- **事实依据**：
  - 设计 §5.6（`index.md:386-390`）：1 core 建 vectorize step → 2 计算 embedding → 3 写 vec.db → 4 成功后回写 core `vectorized` → 5 失败靠 retry/purge/replay。
  - 实际 `workflow_rag/service.py`：chunk 先以 `pending_vectorize` INSERT（:132-158，**在 core 事务内但未 commit**）→ `vector_store.upsert_chunk` 内部 **`self.conn.commit()`**（`store.py:67`，立即提交 vec.db）→ 再 UPDATE core `vectorized`（:169-178，仍未 commit）→ 全部 chunk 完后 `conn.commit()`（:233）。
  - 故 vec.db 在每个 chunk upsert 后**已持久**，而 core.db 的 chunk 行 + vectorized 状态要到整个 step 末尾才 commit。若在 chunk 循环中途崩溃：vec.db 已有 N 条向量，core.db 整事务回滚（chunk 行全消失）→ **vec 孤儿向量，core 无对应 chunk**（坐实 CR-3 G-CR3-13）。
  - 此外 vec.db 先于 core.db 提交，违反"成功后再回写 core vectorized"的时序意图（step 4 应在 step 3 之后，但这里 step 3 是硬提交、step 4 仍在未提交事务里）。
- **为什么重要**：
  - C3 硬约束是"靠状态机而非跨库事务保证一致性"，但当前实现的崩溃窗口产生的 vec 孤儿**无补偿者**：search 读路径靠 hydration post-filter（`search.py:75-84` `missing_hydration`）能过滤掉无 core 元数据的孤儿，故**读安全**；但孤儿向量永久占用 vec.db 且无 purge 清理（R10）。
- **审查判断**：
  - 逻辑错误 L（一致性）。读路径 post-filter 使其非数据正确性 critical，但孤儿无界 + 违反五步序时序，判 high blocker。
- **建议修法**：
  - 按五步序：先 commit core 的 chunk(pending_vectorize) → upsert vec → commit core(vectorized)；崩溃后由 replay 依据 `vec_status='pending_vectorize'` 重做；vec.db 写入用 chunk_id 幂等（配合 R4）。purge 时清 vec 孤儿。

### R6. 无独立 `rag:vectorize` step；向量化内联于 construct

- **严重级别**：`high`
- **类型**：`breakpoint (D) / scope-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `service.py` 只识别两个 stage：`rag:structurize`、`rag:construct`（:51,99），else 抛错（:220）。**不存在 `rag:vectorize`**。
  - construct 段内联完成 chunk + embedding + upsert + vectorized 回写（:104-178），并直接把 run 置 `completed`（:209-219）。
  - 设计 §4.4（`index.md:223`）stage 枚举含独立 `vectorize`；§5.6 step 1 "先在 core.db 创建 vectorize step"；legacy 中 vectorizer 是**独立 DO + 独立 step**（`vectorizer_do.ts`，由 dispatcher orchestrator 作为独立 workflow step 分发，`orchestrator.ts:76-84` 线性 next-step）。
- **为什么重要**：
  - 内核硬约束（`index.md:70`）："所有 step 必须可 claim、可重试、可重启"。向量化内联于 construct 后，**向量化无独立 step**，不能被单独 retry/restart/purge —— 一旦 embedding 失败，整个 construct step 失败重跑，重新分块 + 重新落 chunk（喂养 R4 孤儿）。
  - legacy vectorizer 是耦合最高、能力最重的模块（3.1k 行：批处理、WAL buffer、flush、stranded task release、cool-down 循环、purge mutex），全部丢失。
- **审查判断**：
  - 断点 D + scope-drift。三段设计被压成两段，vectorize 阶段不可独立调度。
- **建议修法**：
  - 拆出 `rag:vectorize` step（construct 只产 chunk + pending_vectorize，finalizer 创建 vectorize step）；vectorize step 独立 claim、独立 retry/purge，与 §5.6/§4.4 对齐。

### R7. 执行器自提交 succeeded + run completed 早于 succeed_claim

- **严重级别**：`high`
- **类型**：`logic-error (L) / correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `service.py:223-233` — step UPDATE `status='succeeded'` + `conn.commit()`；construct 分支额外 `workflow_runs status='completed'`（:209-219）。
  - `apps/worker/src/smind_worker/main.py:50-53` — 先 `process_rag_step(...)` 再 `succeed_claim(...)`；`process_rag_step` 内部已 commit succeeded，**早于** `succeed_claim`。CR-4 G-CR4-03 已就 clean 侧（`workflow_clean/service.py:118,129`）确认同构问题。
  - 副作用（chunk INSERT、vec upsert、document/run 状态）**无幂等键**。
- **为什么重要**：
  - 过期租约竞态（CR-4 G-CR4-01 reap 死代码 + G-CR4-02 lease 时间畸形）下，两个 worker 可能各执行一次 construct：因每次生成新 chunk_id（R4），结果是**重复 chunk + 重复向量 + 重复 artifact**，且都标 vectorized。run 被任一方提前置 completed，另一方仍在写。
  - step 在执行器内自标 succeeded，使内核的 `succeed_claim`/attempt 记账失去单一事实源（职责撕裂）。
- **审查判断**：
  - 逻辑错误 L。本簇与 CR-4 G-CR4-03 同根；rag 侧后果更重（重复向量直接污染检索）。
- **建议修法**：
  - 执行器只产副作用，状态转移交还内核 `succeed_claim`（在 claim 事务内统一置 succeeded + 创建下游 step + 记 attempt）；副作用加幂等键（chunk_id 由 document_id+chunk_index 确定性派生）。

### R8. search 仅按 team_id 过滤，无 namespace/embedding_model 隔离

- **严重级别**：`medium`
- **类型**：`blind-spot (B) / correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `store.py:91-100` `search` WHERE 仅 `deleted_at IS NULL AND team_id = ?`，不按 `namespace_id`/`embedding_model`/`embedding_dimension` 过滤。
  - `service.py:164-165` 写入用 `namespace_id=f"ns_{team_id}"` + `embedding_model='local-sim'`，但检索侧（`search.py:41-45`）未传 namespace/model。
- **为什么重要**：
  - 同 team 若存在多模型/多维度向量，会被跨模型混打分（CR-3 G-CR3-10 同结论）。当前全系统单模型 `local-sim`，问题潜伏未爆发。
- **审查判断**：
  - 盲点 B（潜伏）。当前单模型掩盖，但属正确性缺口。
- **建议修法**：
  - search 增加 namespace_id + embedding_model 过滤参数，与写入侧命名空间对齐。

### R9. RAG 段零 workflow_events/audit_logs（违反 C4）

- **严重级别**：`medium`
- **类型**：`C4 / correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - 通读 `service.py` 全 233 行，无任何 `workflow_events` / `audit_logs` 写入；仅 artifact/chunk/document/run/step 表操作。
  - 设计硬约束（`index.md:69`）："所有 workflow step 必须可观测"。legacy 每阶段 callbacker + Logger 持久化（`structurizer/services/callbacker.ts`、`vectorizer_do.ts:331` sendSuccessCallback）。
- **为什么重要**：
  - structurize/construct/vectorize 三阶段对运维不可见；失败定位、重启决策缺乏事件轨迹。注：内核 `succeed_claim`/`fail_claim` 可能写主状态 event（CR-4 R12 指出失败转移只写 audit 不写 event），但 RAG 子阶段语义事件全缺。
- **审查判断**：
  - C4 fail（RAG 段）。
- **建议修法**：
  - 每子阶段（structurize 完成 / 每批 vectorize / construct 完成）落 workflow_events，与内核事件写入器统一（注意 CR-4 G-CR4-09 的双写入器错位需先收敛）。

### R10. 无 purge/restart 语义

- **严重级别**：`medium`
- **类型**：`blind-spot (B) / delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - 本簇 4 个包无任何 purge/restart 代码；chunk 清理依赖 `workflow_core/purge.py` + `VectorStore.delete_chunks`（CR-3/CR-4 范围）。
  - legacy `purger_logic.ts`：`summary_channel_only` 精细清洗、`resetFileTasksToPending`、force 模式、批量 deleteByIds、WAL 清理 —— 全部无 Python 对应。
- **为什么重要**：
  - 精细化 purge（仅清 summary 通道、按 channel reset）能力丢失；当前 purge 只能整 chunk 删除（且依赖 CR-3 G-CR3-05 对象存储无 delete 的缺口）。
- **审查判断**：
  - 盲点 B。多为有意收敛到内核 purge，但 channel 级精细清洗确属丢失。
- **建议修法**：
  - 与 CR-4 purge 对齐；若 channel 级精细清洗本期不做，在 §4 登记为 deferred。

### R11. RAG 段宽 except 缺失 + 失败不落 step_attempts

- **严重级别**：`low`
- **类型**：`C2 / correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `service.py` 无 try/except，任何异常直接上抛给 worker `_run_once` 的宽 `except Exception`（`main.py:54-56`），`fail_claim` 用恒定 `EXECUTOR_FAILURE`（CR-4 G-CR4-08）。
  - legacy 有细粒度错误码（`AI_RESPONSE_JSON_PARSE_FAILED`/`EMBEDDING_API_ERROR`/`VECTOR_DB_UPSERT_FAILED`）+ 可重试判定（`embedder.ts:73-79` `isRetryableError`）。
- **为什么重要**：
  - RAG 失败无分类，retry 决策失据；但这主要是内核侧缺陷（CR-4 G-CR4-07/08），本簇仅"未提供分类信息"。
- **审查判断**：
  - C2（轻）。本簇执行器抛裸异常本身可接受（交内核处理），缺的是错误分类协议。
- **建议修法**：
  - 定义 RAG 错误码并在抛出时携带，配合内核 fail_claim 的错误分类（依赖 CR-4 修复）。

---

### 2.2 RAG 阶段完整 parity 矩阵（owner 强制 #2）

> 状态图例：`等价` / `有意简化` / `盲点B` / `断点D` / `逻辑错误L`

#### 阶段一 · structurize（legacy 2,897 行 → Python 9 行）

| legacy 能力 | legacy file:line | Python 实现状态 | Python file:line | 裁决 |
|---|---|---|---|---|
| 读 raw_text（IoManager） | `structurizer/services/io_manager.ts` | 读 cleaned_text artifact | `workflow_rag/service.py:52-54` | 等价 |
| AI 模型策略表（std/reasoning, thinkingBudget） | `flows/structurizer.ts:54-79` | 无 | — | 盲点B |
| Prompt 检索（KV, designated_prompt） | `:194-196` | 无 | — | 盲点B |
| Gemini 生成结构化 JSON | `:216-229` | `text.split("\n")` | `rag_structurizer/service.py:5` | 盲点B |
| sanitize/preprocess（meta 迁移/tags/block 补全） | `:90-145` | 无 | — | 盲点B |
| retry 循环（maxRetries 可重试判定） | `:203-280` | 无 | — | 盲点B |
| Zod schema 校验（context_meta/knowledge_tree/layered_content） | `:252` | 无（仅 paragraphs 数组） | `service.py:8` | 盲点B |
| 输出 structured_json 落库 | `:288` | artifact structured_json | `workflow_rag/service.py:55-72` | 等价 |
| 成功回调透传 context | `:293-304` callbacker | 创建下游 construct step | `service.py:82-98` | 有意简化（queue→DB step） |

#### 阶段二 · construct（legacy 3,887 行 → Python 22 行 + 编排）

| legacy 能力 | legacy file:line | Python 实现状态 | Python file:line | 裁决 |
|---|---|---|---|---|
| 读 structured/layered JSON + Zod 校验 | `flows/constructor.ts:103-113` | 读 structured artifact（无校验） | `service.py:100-102` | 盲点B（无校验） |
| case_mode 分支（context_meta_update 跳 summarizer） | `:118-149` | 无 | — | 盲点B |
| summarizer（AI 摘要生成） | `services/summarizer.ts` 全 | 无 | — | 盲点B |
| meta_fuser（元数据融合/isActive/filterMeta） | `:156-167` | 无（document status 硬置 active） | `service.py:201` | 盲点B |
| layer-json 产物落库 | `:172` | 无（仅 constructed_json={chunk_ids}） | `service.py:180-197` | 盲点B |
| recorder：original 通道向量任务 | `recorder.ts:206-214` | chunk_text 分块 | `service.py:104-179` | 有意简化（chunk 替代 block） |
| recorder：summary 通道向量任务 | `recorder.ts:216-224` | 无 | — | 盲点B |
| buildContentFull 上下文头注入 | `recorder.ts:70-95` | 无（裸 chunk 文本嵌入） | — | 盲点B |
| 分块策略 | （legacy 按 block 粒度，非定长） | 350 字符贪心拼接 | `rag_constructor/service.py:4-21` | 有意简化（语义偏差） |
| chunk 落 chunks 表 + vec_status | （D1 smind_vec_process） | chunks 表 pending_vectorize | `service.py:132-158` | 等价（表语义不同但对齐 core.sql） |
| 批量 insert vec_process（BATCH_SIZE=50） | `recorder.ts:230-235` | 逐 chunk INSERT（无批） | `service.py:111-178` | 有意简化 |

#### 阶段三 · vectorize（legacy 3,095 行 → Python 17 行 embedder + 内联编排）

| legacy 能力 | legacy file:line | Python 实现状态 | Python file:line | 裁决 |
|---|---|---|---|---|
| 独立 vectorize step/DO | `vectorizer_do.ts` 全 | 无独立 step（内联 construct） | `service.py:99-219` | 断点D（R6） |
| 真实 AI embedding（qwen3-0.6b） | `embedder.ts:38-39,117` | SHA-256 hash 伪向量 | `embedder.py:6-16` | 盲点B（R1） |
| embedding 重试退避 | `embedder.ts:115-163` | 无 | — | 盲点B |
| prepare（估算 token/过滤空文本） | `vectorizer/prepare.ts` | 无 | — | 盲点B |
| batch 处理 + stranded task release | `engine.ts:50-156` | 逐 chunk 同步 | `service.py:105-179` | 有意简化 |
| WAL buffer + flush + cool-down 循环 | `engine.ts:166-273`, `vectorizer_do.ts:273-323` | 无（直接 upsert） | `service.py:159-168` | 有意简化（DO→同步） |
| upsert 维持 rowid 不变量 | （Vectorize id=vec_uuid） | 不传 embedding_rowid→孤儿 | `service.py:159-168`+`store.py:32` | 逻辑错误L（R4） |
| 五步序跨库一致性 | （DO 状态机） | vec 先 commit/core 后 commit | `service.py:159-178,233` | 逻辑错误L（R5） |
| 回写 vectorized 状态 | `db.finalizeTaskStatus` | UPDATE chunks vectorized | `service.py:169-178` | 等价 |
| purge orchestrator（channel 级/reset） | `purger_logic.ts` 全 | 无 | — | 盲点B（R10） |
| 成功/失败 callback | `callbacker.ts`, `vectorizer_do.ts:331,252` | 自提交 succeeded（早于 claim） | `service.py:223-233` | 逻辑错误L（R7） |

#### 编排 · dispatcher（legacy 4,564 行 → Python 内联于 worker + service）

| legacy 能力 | legacy file:line | Python 实现状态 | Python file:line | 裁决 |
|---|---|---|---|---|
| orchestrator 线性 step 推进（next-step） | `orchestrator.ts:76-84,285-291` | finalizer：structurize→construct 创建下游 step | `service.py:82-98` | 等价（部分） |
| case_mode 跳步（meta_update→constructor） | `orchestrator.ts:49-67` | 无 | — | 盲点B |
| 父文件状态幂等推进 | `orchestrator.ts:244-251` | document status active | `service.py:201` | 有意简化 |
| 步骤回调合并 output_payload | `finalizer.ts:91-102` | 无（artifact 直接落库） | — | 有意简化 |
| workflow 失败处理 + 状态守卫 | `finalizer.ts:117-168` | 依赖 worker fail_claim | `main.py:54-56` | 有意简化（弱于 legacy） |
| restarter（按 step/阶段精细重启） | `smind-rag-dispatcher/services/restarter.ts`(936) | 无（CR-4 restart 总从 clean） | （CR-4 G-CR4-05） | 盲点B |
| purger（向量+任务清理编排） | `services/purger.ts`(357) | 无（CR-4 purge） | （CR-3/CR-4） | 盲点B（R10） |

**parity 覆盖率（按 legacy 能力条目计）**：structurize 9 条中 等价/有意简化 3、盲点B 6（缺失 67%）；construct 11 条中 等价/有意简化 5、盲点B 6（缺失 55%）；vectorize 11 条中 等价/有意简化 4、盲点B 4 + 逻辑错误L 3（缺失/错误 64%）；编排 7 条中 等价/有意简化 5、盲点B 2。**综合：核心能力等价/有意简化约 1/3，盲点B + 逻辑错误L 约 2/3。**

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | structurize→construct→vectorize 三段链路 | partial | 链路通，但 vectorize 无独立 step（内联 construct），三段压成两段（R6） |
| S2 | structure 抽取（AI/reasoning/retry/schema） | missing | 朴素 `\n` 分段，6.8k 行能力缺失（R2） |
| S3 | construct 产 chunk/summary/layer-json 三类 | partial | 仅 chunk；summary 通道 + layer-json 缺失（R3） |
| S4 | chunk 落 chunks 表 + vec_status 流转 | done | INSERT pending_vectorize → UPDATE vectorized，列序/CHECK 域核对正确 |
| S5 | embedding 真实生成 | missing | hash 伪向量，零语义（R1） |
| S6 | C3 五步序（core→embed→vec→回写 vectorized） | partial | 顺序与跨库提交时序偏离，崩溃留 vec 孤儿（R5） |
| S7 | upsert 维持 rowid 一一对应不变量 | missing | 不传 embedding_rowid，孤儿累积（R4） |
| S8 | finalizer 创建下游 step / 收尾 run | done | structurize 建 construct step；construct 收尾 run completed（但与 claim 职责撕裂，R7） |
| S9 | search 走 vec→hydration→core post-filter（§5.7） | done | `v_search_hydration` + post-filter + 半文件降级，本簇最完整部分 |
| S10 | search namespace/team 过滤正确 | partial | 仅 team_id，无 namespace/model（R8） |
| S11 | RAG step 可观测（C4 event/audit） | missing | RAG 段零 event/audit（R9） |
| S12 | purge/restart 语义 | missing | 本簇无 purge/restart（R10），依赖内核且 channel 级精细清洗缺失 |
| S13 | stage 命名匹配 worker 派发 | done | `rag:` 前缀一致，可路由（但无 `rag:vectorize`，见 R6） |

### 3.1 对齐结论

- **done**: `5`（S4/S8/S9/S13 + S8）→ 实际 done 5 项（S4/S8/S9/S13 计 4，S 列中 done 标记为 S4/S8/S9/S13 共 4 项）
- **partial**: `4`（S1/S3/S6/S10）
- **missing**: `4`（S2/S5/S7/S11；另 S12 missing）→ missing 实为 5 项（S2/S5/S7/S11/S12）
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 修正计数：done 4（S4/S8/S9/S13），partial 4（S1/S3/S6/S10），missing 5（S2/S5/S7/S11/S12）。
> 状态判定：这更像"**端到端能跑通的极简骨架 + 一个相对完整的 search 读路径**"，而非 completed 的 RAG 流水线。三个核心执行器（structurize/construct/embed）是占位，且继承 CR-3/CR-4 的 critical 不变量破坏。

### 3.2 stub / 真实现标定表（owner 必交项）

| 包 | 公开符号 | 标定 | 依据 |
|---|---|---|---|
| `rag_structurizer` | `structurize_text` | **stub（盲点B）** | `\n` 分段，无 AI/schema/retry（service.py:4-8） |
| `rag_constructor` | `build_chunks` | **stub（盲点B）** | 350 字符定长拼接，无 summary/meta（service.py:4-21） |
| `rag_vectorizer` | `embed_text` | **stub（盲点B）** | SHA-256 hash 伪向量，零语义（embedder.py:6-16） |
| `rag_vectorizer` | `SearchService.search` | **真实现** | 完整 hydration + post-filter（search.py:24-25,39-121） |
| `rag_vectorizer` | `SearchService.search_debug` | **真实现** | 暴露候选/hydrated/filtered 计数（search.py:27-37） |
| `rag_vectorizer` | `SearchService._load_chunk_text` | **真实现** | 对象存储优先 + metadata 回退（search.py:123-137） |
| `workflow_rag` | `process_rag_step`（structurize 分支） | **真实现（部分）** | 真落 artifact + 建下游 step；但执行体调 stub structurize（service.py:51-98） |
| `workflow_rag` | `process_rag_step`（construct 分支） | **部分** | 真落 chunk/artifact/vec/回写；但调 stub build_chunks/embed_text + R4/R5/R7 缺陷（service.py:99-219） |
| `workflow_rag` | `process_rag_step`（vectorize 分支） | **缺失** | 无 `rag:vectorize` stage（R6） |
| `workflow_rag` | `_latest_artifact` / `_artifact_payload` | **真实现** | 正确按 type+created_at 取最新 artifact（service.py:15-32） |

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | sqlite-vec/vec0 退化为暴力 cosine（G-CR3-02） | 误报风险（归 CR-3） | 物理落点在 vector_sqlite_vec，本簇仅消费；不重复登记为 CR-7 blocker，但 R1 伪向量 + 暴力 cosine 叠加放大检索失真 |
| O2 | 孤儿 rowid（G-CR3-03）/ 重号删除（G-CR3-04） | 部分违反（触发点在本簇） | 物理 bug 归 CR-3，但**触发方式**（不传 rowid + 每次新 chunk_id）是本簇职责，登记为 R4 |
| O3 | 执行器自提交 succeeded（G-CR4-03） | 部分违反（rag 侧同构） | CR-4 已就 clean 侧登记，本簇核实 rag 侧同样存在且后果更重（重复向量），登记为 R7 |
| O4 | 时间格式 bug（G-CR1-01/G-CR4-02） | 遵守（不污染本簇） | 本簇所有时间戳用 SQL 内联 `strftime('%Y-%m-%dT%H:%M:%fZ','now')`（service.py:77,173,203...），不经 Python `_utils.now_iso`，故 lease/available_at 畸形不经 RAG 写入路径污染 |
| O5 | 对象存储无 delete/二进制（G-CR3-05/08） | 遵守（归 CR-3） | chunk_text 为纯文本，put_text 适用；purge 清对象缺口归 CR-3 |
| O6 | restart 总从 clean 重跑（G-CR4-05） | 遵守（归 CR-4） | RAG 无独立 restart 入口，依赖内核；本簇不越界 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`（实质接近 blocked：核心价值链 embedding 为伪造）
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1** — embedder 接入真实 embedding 模型（hash 伪向量使整条 RAG 价值归零）。
  2. **R4** — construct→upsert 维持 embedding_rowid 不变量 / 幂等 upsert（孤儿向量污染检索）。
  3. **R5** — 按 §5.6 五步序修复跨库提交时序 + replay 补偿（崩溃留 vec 孤儿）。
  4. **R6** — 拆出独立 `rag:vectorize` step，使向量化可 claim/重试/重启。
  5. **R7** — 移除执行器自提交 succeeded，状态转移交还内核 + 副作用幂等键（重复执行→重复向量）。
  6. **R2 / R3** — structurize/construct 盲点：补 AI 结构化 + summary 通道 + layer-json，或由 owner 显式声明本期 deferred 并在 closure 标注，禁止标 P4 完成。
- **可以后续跟进的 non-blocking follow-up**：
  1. R8（search namespace/model 过滤）、R9（C4 RAG 段可观测）、R10（channel 级 purge）、R11（错误分类）。
- **建议的二次审查方式**：`same reviewer rereview`（embedder + vectorize step 拆分 + rowid 幂等是结构性改动，需复核五步序与 search 召回质量）
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口。RAG 流水线骨架与 search 读路径成立，但三个核心执行器为占位、embedding 伪造、并继承 CR-3/CR-4 的 critical 不变量破坏与职责撕裂，等待实现者按 §6 响应并再次更新代码。
