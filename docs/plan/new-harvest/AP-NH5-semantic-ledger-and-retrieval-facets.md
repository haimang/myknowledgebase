# Nano-Agent 行动计划

> 服务业务簇: `MKB / new-harvest / intake-four-channel-live`
> 计划对象: 四通道严格五维权威 + S06 context overlay + `semantic_channel`/`vector_channel` 分名 + facet SQL
> 类型: `upgrade`（扩 S04/S06/S10，不重开 cuts/g0）
> 作者: `Grok workflow new-harvest-nh1-nh5-action-plans`
> 时间: `2026-08-29`
> 文件位置: `docs/plan/new-harvest/AP-NH5-semantic-ledger-and-retrieval-facets.md`
> 上游前序 / closure:
> - `AP-NH1` `stop-or-go.md=GO`（`NH1-T01..T07` 全 PASS）后进入并行窗；证伪 STOP，禁止部分绿。与 `AP-NH2` / `AP-NH4` **互不等**（L3/L4 可用 HEAD 图证语义闸，不把 NH2 kind 图当本 AP 开工闸）
> - 冻结 QNA：`docs/eval/new-harvest/pre-charter-qna.md` v1.0 Q14/Q15 → `T-O-394`/`T-O-395`；`docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-389`/`T-O-386`
> 下游交接:
> - `AP-NH7` 10+3 vertical activation（NH7 前 join；facet/query 面必须可滤）
> - `AP-NH8` exact-clean / metadata intent guard：`NH5-T08-B` process-absence 红灯 → `NH8-T03`（`NH8-03`）转绿；本 AP `NH5-08` 不落地 reclean 旁路（`T-O-407`）
> - Capstone **G**（五维/S06/facet）：本 AP 主责 `NH5-T07`（NH9 只交叉）
> - `M-NH-06` facets；`M-NH-08` retrieval naming/namespace
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.5（本 AP 唯一执行基线）
> - `docs/eval/new-harvest/final-execution-plan.md` §11.A 台账 ID 区间：`NH5-01..08 / NH5-A01..06 / NH5-T01..08`
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-07-semantic-ledger-and-retrieval-facets.md`（RA07 主面）
> - `docs/eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md`（RA08：stub 不得 complete；retrieval 终验边界只消费）
> 冻结决策来源:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 §7.5 A/B/C/D + §4.2 OOS + §6 DAG
> - `docs/eval/new-harvest/pre-charter-qna.md` Q14/Q15/Q26/Q27 → `T-O-394`/`T-O-395`/`T-O-406`/`T-O-407`（只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` Q6/Q9 → `T-O-386`/`T-O-389`
> grounding 来源:
> - `eval-reference-anchor RA07` + HEAD `1221aa1` 实测 + final §7.5 四台账
> 关联 reference-anchor:
> - [`assessment-analysis-07-semantic-ledger-and-retrieval-facets.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-07-semantic-ledger-and-retrieval-facets.md)
> - [`assessment-analysis-08-publication-and-intake-lifecycle.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md)（邻面缺口只消费）
> 文档状态: `executed`

---

## 0. 执行背景与目标

HEAD `1221aa1` 已为 **registered_api** 交付 FilterMeta 五维 + 六元组 + S04 `mkb_intake_revision_semantics` 写入，并用 system-owned g0 钉 `g0.body = admitted clean`。但 **inline / local / http 公开 descriptor 无五维字段**（`src/contracts/api/models.py:107-129`），acceptance 在缺 `filter_meta` 时写 `{"source_kind": ...}` stub 仍可 complete（`src/runtime/intake/acceptance_snapshot.py:591-615`，`T-R-NH-13`/`T-R-NH-27`）。S06 不读 S04：structurize 输入只有 `clean`/`markdown`（`generation_construct.py:330-343`），`overlay_system_g0` 缺 `context_meta` 则塞 `{}`、已有则保留模型值（`generation_assemble.py:59-60`）。公开检索 `_FILTER_KEYS = {intake_item_uuid, source_kind, channel}`，其中 `channel` 闭集为向量 `original|summary`，与 `FilterMeta.channel` 撞名（`src/services/retrieval/models.py:14`；`T-R-NH-14`/`T-R-NH-27`）。facet 表只 upsert `source_kind`（`vector_publish_commit.py:496-518`）。

本 AP 消费已冻结 `T-O-389/394/395/386`，把四通道语义权威、S06 system overlay、公开双键与候选 SQL facet 落成可交付物。不重开 cuts/g0，不把 GPT/Grok 推荐再选一次。`P-semantic-unknown` 已由 final 裁定 `CORRECT`。

**三名分账（本 AP 合同表，执行时必须同时出现在 ingest/retrieval 文档与测试）**：

| 名字 | 层 | 含义 | 取值法 |
|------|----|------|--------|
| `FilterMeta.channel` | S04 业务维 / ingest 合同 | 业务频道（如 `政策法规` / `sold`） | generic：caller 必填、非空、非 `unknown`；API：mapper SSOT |
| `semantic_channel` | 新 public retrieval filter | `FilterMeta.channel` 的公开过滤键 | 登记 facet；eq 进入**候选 SQL** |
| `vector_channel` | 新 public retrieval filter | 向量 dual-channel | 闭集 `original \| summary` |
| `mkb_vector_records.channel` | 内部物理列 | 向量 dual-channel | `T-O-395` 允许暂留物理名，不在本 AP 强制 rename |
| 旧 public `filters.channel` | **仅**旧 schema `mkb.retrieval.v1` | 机械映射为 `vector_channel` | 仅 `original \| summary`；其它值 422；新 schema 出现该键 422 |

- **服务业务簇**：`new-harvest` / `S-NH-F5`
- **计划对象**：四通道严格五维权威 + S06 context overlay + 分名 retrieval facets
- **本次计划解决的问题**：
  - generic 三 kind 无五维入口、API mapper `or "unknown"` 自动填空（`T-O-394`；`P-semantic-unknown CORRECT`）
  - stub 仍 acceptance-complete、S06 空/模型 context 当权威、g0 与过滤账未分清（`T-O-389`/`T-O-386`；`FG-NH-07`）
  - 公开 `channel` 撞名、facet=0、过滤若有也只在 topK 后 Python 滤（`T-O-395`；`M-NH-06`/`M-NH-08`）
- **本次计划的直接产出**：
  - generic ingest 四字段必填 nonunknown；`is_active` 系统派生；API mapper SSOT + 冲突 422 + 逐字段 provenance
  - acceptance 六元组闸：四 kind 各写 6 行；stub 不得 complete；缺义不得 Revision/vector
  - 平行于 g0 的 S06 `context_meta` overlay（读 S04，丢模型权威字段）；g0.body 仍 = clean
  - 新 schema `semantic_channel` + `vector_channel` 同请求共存；旧 schema 窄适配；facet 行 + 候选 SQL
  - metadata 语义切代：继承 clean artifact；六元组/S06/facet 跟随 serving revision；**不调用新 cleaner**（guard 落地交 NH8）
- **本计划不重新讨论的设计结论**：
  - generic 四字段 caller 必填非 `unknown`，API 禁自动 `unknown`（来源：Q14 / `T-O-394`）
  - 新 public schema 只用 `semantic_channel`/`vector_channel`，不按 value 猜轴（来源：Q15 / `T-O-395`）
  - 五维+tags 四通道进 S04、不进 g0；stub 不得 complete（来源：Q9 / `T-O-389`）
  - g0 original = admitted clean body；S06 overlay 不得改 g0（来源：Q6 / `T-O-386`）
  - rebuild/metadata 旁路 acquire/decode/clean 是 NH8（来源：Q27 / `T-O-407`）；本 AP 只保证不调用**新** clean
  - 四层测试不可互换（来源：Q26 / `T-O-406`）；本 AP 最低层以台账 C 为准，T07 为 L4 硬闸

---

## 1. 执行综述

### 1.1 总体执行方式

先协议后实现、先权威账后投影：Phase 1 冻 generic/API 输入合同（含禁 `or "unknown"` 与 provenance），Phase 2 把 acceptance 改成缺六元组 fail-loud 并保证 definition/value/digest/blob 原子，Phase 3 加平行 S06 overlay（不改 g0 切法），Phase 4 分名公开键并让 facet 进入候选 SQL，Phase 5 让 metadata 切代消费同一套六元组。NH1 证伪即 STOP；本 AP 不回退 duplication，不把 spike 写成 NH2/NH6 已交付。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 输入合同 | L | generic 四字段 required nonunknown；`is_active` 派生；API mapper SSOT + 冲突 422 | `stop-or-go.md=GO` 后并行；不等 NH2；不改图/cuts |
| Phase 2 | acceptance 闸 + 原子性 | L | 拒 stub；四 kind 写 6 rows；缺义不得 Revision/vector；definition/value/digest/blob 同源 | Phase 1 合同 |
| Phase 3 | S06 overlay | M | 读 S04 覆盖五维/tags；模型值非权威；g0 digest = clean | Phase 2 权威行已存在 |
| Phase 4 | 命名与投影 | L | 双键 + 旧 schema 窄适配；facet 行；typed SQL filters；unknown key 422 | Phase 2/3；`M-NH-06/08` |
| Phase 5 | metadata 切代 | M | inherit clean；新 six-tuple；S06/facet 切代；不 reclean（guard 交 NH8） | Phase 2–4 |

> 说明：上表 `规模` 是描述性提示，不是开工闸。

### 1.3 Phase 说明

1. **Phase 1 — 输入合同**
   - **核心目标**：caller/mapper 分责写成 typed 合同，消灭自动 `unknown`。
   - **为什么先做**：没有入口字段，acceptance 只能继续 stub（`D-07-F01=0`）。
2. **Phase 2 — acceptance 闸 + 原子性**
   - **核心目标**：六元组成为 acceptance-complete 的硬条件；单键与 blob 同事务同源。
   - **为什么放在这里**：合同已能提交五维后，必须立刻阻断 stub complete（`FG-NH-07`）。
3. **Phase 3 — S06 overlay**
   - **核心目标**：layered `context_meta` 权威 = S04 逐字；g0 仍只含 clean。
   - **为什么放在这里**：overlay 读权威行；权威行不存在时覆盖只会把空对象合法化。
4. **Phase 4 — 命名与投影**
   - **核心目标**：两轴同请求不歧义；facet 进候选 SQL。
   - **为什么放在这里**：无 S04 行则 facet 只能写 `source_kind` 或发明 unknown。
5. **Phase 5 — metadata 切代**
   - **核心目标**：改五维 ⇒ 新 Revision + 同 clean digest + 重投影；不跑新 cleaner。
   - **为什么放在这里**：切代消费 Phase 1–4 的同一套六元组/overlay/facet。

### 1.4 执行策略说明

- **执行顺序原则**：合同 → 闸 → overlay → 检索投影 → metadata 消费者。禁止先改 retrieval 再让空 stub 可滤。
- **风险控制原则**：`R-F08` unknown 回流用 schema nonunknown + mapper 源扫描；`R-F09` channel 双义用 versioned adapter 而非 value-guess；facet 禁止 topK 后 Python 过滤（pgvector/Supabase 后过滤失败法，RA07 WEB 🔶）。
- **测试推进原则**：L1 合同矩阵（T01/T02/T05）→ L2 UoW 六元组与 overlay（T03/T04）→ L3 默认根双键（T05/T06）→ L4 facet mega（T07 硬闸）→ T08 digest + process-absence 交接。层不可互换（`T-O-406`）。
- **文档同步原则**：公开 ingest/retrieval 字段表、三名分账、旧 schema 弃用信号写入 API 说明；evidence pack 目录预登记，不伪造 SHA。
- **回滚 / 降级原则**：公开合同加键可向前兼容；新 schema 禁旧键不可静默回退到猜轴。若 `stop-or-go.md≠GO`，本 AP **不得**进入执行、**不得**合并生产语义，也不得宣称 default-root L3/L4 已绿。metadata 旁路 clean 失败必须红灯交 `NH8-T03`，禁止改期待值（`FG-NH-17`）。

### 1.5 本次 action-plan 影响结构图

```text
AP-NH5 semantic ledger + retrieval facets
├── Phase 1: 输入合同
│   ├── public SourceDescriptor (inline/local/http) + extra=forbid
│   ├── FilterMeta / semantic_tuples 六元组
│   └── intake/api/providers/{chinatax,domain,realestate} mapper SSOT
├── Phase 2: acceptance 闸
│   ├── _initial_semantics_tx 拒 stub
│   ├── mkb_intake_revision_semantics 6 rows + blob 同源
│   └── scatter API regression（六键仍在）
├── Phase 3: S06 overlay
│   ├── overlay_system_g0 保持 body=clean
│   ├── overlay_system_context_meta 覆盖五维/tags
│   └── structurize 输入仍不把五维写入 clean/g0
├── Phase 4: 命名与投影
│   ├── RetrievalFilter / _FILTER_KEYS 双键
│   ├── mkb_vector_record_facets 五维+tags
│   └── _fetch_candidate_rows 候选 SQL JOIN + WHERE
└── Phase 5: metadata 切代
    ├── update_metadata 六元组原子 + 继承 clean artifact
    ├── S06/facet 跟随 serving revision
    └── acquire/clean Process 缺席断言 → NH8
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `S-NH-F5`：strict semantic authority、S06 overlay、facet/query naming（`T-O-389/394/395`）。
- **[S2]** generic inline/local/http：`realm/type/channel/source_name` required、非空、非 `unknown`；`is_active` 系统派生；`payload_extra` 不得成为权威（`T-O-394`）。
- **[S3]** registered_api：mapper 为 SSOT；caller 重复提交须逐字段相等否则 422；禁止 `or "unknown"`；仅 registry 明列的可选字段可从 frozen record **显式字面**携带 `unknown`。
- **[S4]** acceptance：四 kind 写六元组；stub/`source_kind` blob 不得 complete；缺义不得出 Revision/vector（`T-O-389`；`FG-NH-07`）。
- **[S5]** S06：system overlay 读 S04 五维+tags；模型/CLI `context_meta` 非权威；g0.body digest = clean（`T-O-386/389`）。
- **[S6]** 新 public schema 双键；旧 `mkb.retrieval.v1` `filters.channel` 仅 `original|summary` 机械映射为 `vector_channel` 并弃用；其它值与新 schema 旧键 422（`T-O-395`；`M-NH-08`）。
- **[S7]** facet 投影到 `mkb_vector_record_facets`（五维+tags+definition digest+serving revision）；typed SQL 过滤；unknown key 422；禁止 post-topK Python filter（`M-NH-06`）。
- **[S8]** metadata：新 six-tuple、指纹变则新 Revision、继承 clean stored object、重投影 S06/facet；本 AP 保证不调用**新** cleaner；intent guard 交 NH8（`T-O-394/407`）。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `O-NH-01`：live connector/cookie/tunnel、第五 kind、caller `workflow_key`、`action_branch`。
- **[O2]** `O-NH-02`：cuts/g0 算法重开、按通道复制 tail、前端/answer generation。
- **[O3]** `O-NH-03`：existing-object new-cleaner/validator upgrade（`T-O-401`）。
- **[O4]** `O-NH-04`：raw object GET/list/presign/browser（`T-O-396`）。
- **[O5]** `O-NH-05`：experiment 发车/评分；骨架非 DoD（`T-O-380`）。
- **[O6]** `O-NH-06`：通用 Workflow JOIN/DSL/自由表达式/loader；云 OCR/CF/R2/SMCP runtime。
- **[O7]** NH6–NH9 live 供给 / 10+3 激活 / 七意图收口 / campaign mega（本 AP 只提供 facet 面给 NH7 消费）。
- **[O8]** rebuild/metadata **intent guard 旁路** acquire/decode/clean Process（NH8 / `T-O-407`）。本 AP 不得把 no-op cleaner 或改测试期待值当成旁路。
- **[O9]** 内部向量列 `mkb_vector_records.channel` 物理 rename；外部向量 DB（Qdrant/pgvector/OS/ES/CF Vectorize）。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 四通道 S04 六元组 + 拒 stub | `in-scope` | `S-NH-F5`；`T-O-389/394` | 无 |
| S06 context overlay 读 S04、不改 g0 | `in-scope` | `T-O-386/389` | 无 |
| `semantic_channel`/`vector_channel` + 旧 schema 窄映射 | `in-scope` | `T-O-395`；`M-NH-08` | 无 |
| facet 行 + 候选 SQL | `in-scope` | `M-NH-06`；RA07 WEB 后过滤失败法 | 无 |
| metadata 六元组切代 + inherit clean | `in-scope` | `T-O-394`；RA07 `NH-C-66` 本面拥有五维/新 Revision | NH8 关闭 process-absence |
| rebuild/metadata 旁路 clean Process | `out-of-scope` | 本 AP `[O8]`；`T-O-407`；台账 A `NH5-08.d` 交 NH8 | NH8 guard 落地后 T08-B 转绿 |
| cuts/g0 切法 | `out-of-scope` | `O-NH-02`；`T-O-389` 不重开 cuts | 新 owner-gate |
| 第五 kind / workflow_key / CF/R2 | `out-of-scope` | `O-NH-01`/`O-NH-06` | 新 owner-gate |
| existing-object upgrade | `out-of-scope` | `O-NH-03`；`T-O-401` | 新 owner-gate |
| 只测 API 宣称四通道 | `out-of-scope`（反例） | `FG-NH-14` | 无 |

---

## 3. 业务工作总表

> 编号列使用 final 台账 A 的 `NH5-nn`。每个工作项含不可约三元组：`file:line` / 收口目标 / Test-ID。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| `NH5-01` | Phase 1 | Strict semantic input | add | `src/contracts/api/models.py:107-143`；`src/contracts/intake/semantics.py:12-63`；`intake/api/providers/chinatax.py:31-55`；`domain.py:50-78`；`realestate.py:102-108`；`intake/api/registry.py:36-104` | generic 四字段 required 且字面 ≠ `unknown`；`is_active` 非 caller；API mapper 无 `or "unknown"`；冲突 422；逐字段 provenance | `NH5-T01` `NH5-T02` | high |
| `NH5-02` | Phase 2 | Six-tuple gate | update | `src/runtime/intake/acceptance_snapshot.py:576-641`；`src/runtime/intake/acceptance_scatter.py:80-98`；`tests/e2e/test_registered_api_scatter.py:287-296` | 四 kind 各写 6 semantic rows；`filter_metadata` 不是 `{"source_kind":...}`；stub 不得 complete；缺义不得 Revision/vector | `NH5-T02` `NH5-T03` | high |
| `NH5-03` | Phase 2 | Semantic atomicity | update | `src/runtime/intake/acceptance_snapshot.py:645-710`；`src/runtime/intake/acceptance_lifecycle.py:360-380`；`src/persistence/migrations/001_initial.sql:1045-1078` | 同 UoW 写入 definition/value/digest；单键与 `filter_metadata`/`context_metadata` blob 同源；metadata CAS；fingerprint 只吃 participation=true | `NH5-T03` | high |
| `NH5-04` | Phase 3 | System context overlay | update | `src/runtime/intake/generation_assemble.py:17-62,171-174`；`src/runtime/intake/generation_construct.py:330-343,1214-1218`；`src/contracts/lsrag/layered_content.py:16-28,117-127` | `context_meta.{realm,type,channel,source_name,tags}` 逐字 = S04；模型 realm 被丢弃；g0.body digest = clean；五维不进 g0 | `NH5-T04` | high |
| `NH5-05` | Phase 4 | Channel split | update | `src/services/retrieval/models.py:14-34`；`src/services/retrieval/retrieval_request.py:261-361`；`src/contracts/api/models.py:408-435` | 新 schema 可同请求带 `semantic_channel`+`vector_channel`；旧 schema `channel` 仅 `original\|summary`；其它/新 schema 旧键 422 | `NH5-T05` `NH5-T06` | high |
| `NH5-06` | Phase 4 | Facet rows | update | `src/runtime/intake/vector_publish_commit.py:496-525`；`src/runtime/intake/vectorize.py:319-324`；`src/persistence/migrations/001_initial.sql:1503-1522` | serving revision 的五维+tags 写入 facet，带 definition digest；source_kind 可保留但不得冒充 FilterMeta；无六元组则不得发明 unknown facet | `NH5-T07` | high |
| `NH5-07` | Phase 4 | Typed SQL filters | update | `src/services/retrieval/retrieval_rank.py:80-137`；`src/services/retrieval/retrieval_request.py:324-361`；`tests/unit/test_retrieval_service.py:456-460` | 登记键进入 `_fetch_candidate_rows` WHERE；unknown 422；零 Python post-topK 语义过滤；namespace 仍必填 | `NH5-T07` | high |
| `NH5-08` | Phase 5 | Semantic refresh | update | `src/runtime/intake/acceptance_lifecycle.py:213-278,378-409`；`src/runtime/intake/acquisition_intents.py:115-233`；`tests/e2e/test_intake_rebuild_metadata.py:100-291` | 指纹变 ⇒ 新 Revision；clean digest/object 不变；S06/facet 切代；不调用新 cleaner（process-absence 交 NH8，禁止 xfail） | `NH5-T08` | high |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 输入合同

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH5-01` | Strict semantic input | a) 在 `InlineSourceDescriptor`/`LocalObjectSourceDescriptor`/`HttpSourceDescriptor` 增加 `realm/type/channel/source_name`（`Field(min_length=1)`），`context_tags` 可选默认 `[]`；`extra=forbid` 保持；`payload_extra` 不得解析为 FilterMeta。b) 拒绝 caller 提交 `is_active`（出现即 422）；系统在 admission 派生（v1 新 ingest = `1`，生命周期下架不在本 AP）。c) 字面 `unknown`/`Unknown`（casefold 后等于 `unknown`）对 generic 四字段一律 422，空串/空白同。d) API：`ProviderOperationDefinition` 增加闭集 `optional_unknown_fields`（v1 **默认空**）；三 mapper 删除 `or "unknown"` / `or "Unknown"` / `property_type or "Unknown"` / `or "Unknown Agency"`；缺必填字段 422。仅当字段 ∈ 该 operation 明列集合 **且** frozen record **显式**携带该字面时才写入 `unknown`。e) API descriptor 若重复提交四字段，必须与 mapper 逐字段相等，否则 422。f) 每键 provenance ∈ `{caller,mapper,system}` 与值同 UoW 持久化，不参与 fingerprint。g) `FilterMeta.channel` 是业务维，不校验 `original\|summary`。 | `src/contracts/api/models.py:107-143`；`src/contracts/intake/semantics.py:12-63`；`src/contracts/common/models.py:1-21`；`intake/api/providers/chinatax.py:33-34,49-55`；`intake/api/providers/domain.py:50-78`；`intake/api/providers/realestate.py:102-108`；`intake/api/registry.py:36-72,73-104` | 无五维的 generic 请求无法通过 public model；HEAD 三处 `or "unknown"` 消失；chinatax 固定 `realm=tax_china` 等既有 mapper 字面回归仍绿 | `NH5-T01` `NH5-T02` | generic 无 unknown；API 无自动填空；冲突 422 |

### 4.2 Phase 2 — acceptance 闸 + 原子性

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH5-02` | Six-tuple gate | a) `_initial_semantics_tx`：**禁止** `filter_metadata = {"source_kind": source_kind}` 兜底。`filter_meta` 必须是完整 Mapping，含 `realm/type/channel/source_name` 非空非 unknown（generic）以及合法 `is_active` ∈ `{0,1}`。b) 无论 kind，展开并写入六键：`realm,type,channel,source_name,is_active,context_tags`。c) 缺任一键或 blob 仍为 source_kind stub ⇒ typed 422（建议码 `INTAKE_SEMANTICS_INCOMPLETE` 或沿用 `INTAKE_SEMANTICS_INPUT_INVALID`），`admission_result` 不得 complete，不得 insert 可服务 Revision，不得进入 vectorize 成功路径。d) API scatter 路径继续从 member `filter_meta` 写入，回归 `test_registered_api_scatter.py:287-296` 六键 ⊆ revision_semantics。e) 非 API runtime 必须把 descriptor 五维放进 state（今日 grep 仅 snapshot/scatter/API preflight）。 | `src/runtime/intake/acceptance_snapshot.py:576-641`；`src/runtime/intake/acceptance_scatter.py:80-98,188`；`src/runtime/intake/clean_preflight.py:288,832` | `D-18` 从 0 变为四 kind 均可写六键；stub 路径红 | `NH5-T02` `NH5-T03` | 四 kind 六元组非 stub；缺义不得 complete |
| `NH5-03` | Semantic atomicity | a) 每键：登记 `definition_version/digest` + typed value + `value_digest=H(key,version,definition_digest,value)`（沿用 `:645-658`）。b) 同事务重算 `filter_metadata`/`context_metadata` blob，使 blob 与单键同源；禁止只写五维留下陈旧 blob（反例 `acceptance_lifecycle.py:378-380` key-wise merge）。c) fingerprint 仍只吃 `fingerprint_participation=true`（`:662-679`）；provenance 不进 fingerprint。d) metadata 路径 CAS：合并后指纹变化才新 Revision；并发 `METADATA_TARGET_STALE` 409。e) 若增加 `value_provenance` 列则 forward-only migration；不得用 `payload_extra` 控状态（只可作非路由审计）。 | `src/runtime/intake/acceptance_snapshot.py:645-710`；`src/runtime/intake/acceptance_lifecycle.py:360-409`；`src/services/intake_lifecycle/targets.py:47-64,203-248`；`src/persistence/migrations/001_initial.sql:1045-1078` | 单键改 realm 必同时改 blob；指纹稳定可重放 | `NH5-T03` | definition/value/digest/blob 原子 |

### 4.3 Phase 3 — S06 overlay

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH5-04` | System context overlay | a) 保持 `overlay_system_g0`：丢所有模型 g0，插入唯一 system g0，`original_content.body = normalize(clean)`（`:17-47`）。b) 新增平行 `overlay_system_context_meta`：从该 Revision 的 S04 六键覆盖 `context_meta.realm/type/channel/source_name/tags`；`title` 可保留模型/descriptor 非权威候选但不得回写 S04。c) 模型已返回的 realm 等权威字段必须被覆盖，不得「已有 Mapping 则原样保留」（今日 `:59-60` 反例）。d) cuts 装配若拷贝 pack `context_meta`（`:171-174`），随后仍走同一 overlay。e) `_bjson_user_material` **继续**只序列化 clean/markdown（`:330-337`），禁止把 FilterMeta 塞进 structurize 用户材料或 g0。f) CLI stub `context_meta: {}` 不得在 admit 后存活。 | `src/runtime/intake/generation_assemble.py:17-62,169-174`；`src/runtime/intake/generation_construct.py:330-343,1112,1214-1218`；`src/contracts/lsrag/layered_content.py:117-127` | structure artifact 的 context 与 S04 diff 为空；g0 不含五维 JSON | `NH5-T04` | context 逐字 = S04；g0 = clean |

### 4.4 Phase 4 — 命名与投影

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH5-05` | Channel split | a) 新 public schema（执行名建议 `mkb.retrieval.v2`，以 HEAD `mkb.retrieval.v1` 为旧 schema；此为 `T-O-395` 落地而非新 gate）：`RetrievalFilter` 含 `semantic_channel`、`vector_channel`，**禁止**键 `channel`。b) `_FILTER_KEYS` 扩为闭集：`intake_item_uuid, source_kind, semantic_channel, vector_channel` 以及登记的 FilterMeta facet（至少 `realm`；`type`/`source_name`/`is_active`/`context_tags` 按同法登记）。c) 旧 schema `mkb.retrieval.v1`：`filters.channel` ∈ `{original,summary}` ⇒ 映射 `vector_channel` + 弃用信号（响应/诊断字段，不改变结果语义）；其它值（如 `web`/`sold`/`summary` 当业务维）422。d) 新 schema 出现 `channel` ⇒ 422，**不**按 value 猜轴。e) 内部 SQL 仍可读 `r.channel` 物理列，服务层把 `vector_channel` 绑到该列。 | `src/contracts/api/models.py:408-435`；`src/services/retrieval/models.py:14-34`；`src/services/retrieval/retrieval_request.py:261-361` | 同请求可表达 `semantic_channel=sold` 且 `vector_channel=summary`；`channel=web` 422 | `NH5-T05` `NH5-T06` | 双键共存；旧键仅原枚举 |
| `NH5-06` | Facet rows | a) vectorize 对 serving revision 的 S04 五维+`context_tags` upsert `mkb_vector_record_facets`，每行带 `definition_version`/`definition_digest`（沿用表注释「resolved by S04」）。b) `source_kind` facet 可继续写，但 **不是** FilterMeta 五维，不得在文档/测试里把它算作五维 facet。c) facet value 必须等于该 serving revision 的 S04 同行（`NH-C-65`）。d) 无六元组的历史行：**禁止** backfill `unknown`；保持不可按 realm 命中，直到 metadata 切代。有六元组的 API 历史行可按 S04 backfill（`M-NH-06`）。 | `src/runtime/intake/vector_publish_commit.py:496-525`；`src/runtime/intake/vectorize.py:319-324`；`src/persistence/migrations/001_initial.sql:1503-1522` | `D-19` FilterMeta facet key 从 0 变为 ≥5；definition digest 可核对 | `NH5-T07` | facet 与 S04 同源 |
| `NH5-07` | Typed SQL filters | a) `_normalise_filters`：未知键继续 `RETRIEVE_FILTER_INVALID` 422（`:333-340` 正例扩展）。b) `_fetch_candidate_rows` 对 `semantic_channel`/`realm`/其它登记键 **JOIN** `mkb_vector_record_facets` 和/或 `mkb_intake_revision_semantics`（serving revision），谓词进 WHERE，在 `LIMIT`/`rank` 之前。c) `vector_channel` 继续过滤 `r.channel`。d) 禁止在 `_rank_ann_candidates` 或 pack 之后用 Python 按 realm 丢行。e) namespace_key/uuid 仍必填（`:265-270`）；本 AP L4 **不得**再省略（反例 `tests/e2e/test_single_intake_pipeline.py:121-130`）。 | `src/services/retrieval/retrieval_rank.py:26-137`；`src/services/retrieval/retrieval_request.py:263-361` | 候选计数在 SQL 层已排除非命中 realm；unknown key 422 | `NH5-T07` | SQL 层过滤；无 namespace 不得 200 |

### 4.5 Phase 5 — metadata 切代

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH5-08` | Semantic refresh | a) `IntakeUpdateMetadataPayload.semantics` 可含五维+tags；改参与指纹的键 ⇒ 新 Revision `creation_action_key=update_metadata`（沿用 `:230-252`）。b) 继承前序 `clean_text` 的同一 `stored_object_uuid` 与 `content_digest`（`:253-278`）。c) 同事务重写六元组与 blob（修 `:378-380` 只改单键）。d) metadata_refresh 重跑 S06 overlay 与 facet 投影，使 serving revision 可按新 realm 命中/排除。e) **不**调用新 cleaner、不改 strategy；本 AP 不改图上 intent guard。f) T08 必须断言 acquire/decode/clean Process 计数 = 0；HEAD 仍经 `_acquire_rebuild`（`acquisition_intents.py:207-214`）+ `dispatch_clean`（`clean_preflight.py:28-127`）时该断言 **红灯交 NH8**。禁止 `pytest.xfail`、禁止改期待值掩盖（`FG-NH-17`）。 | `src/runtime/intake/acceptance_lifecycle.py:213-278,378-409`；`src/runtime/intake/acquisition_intents.py:115-233`；`src/contracts/api/models.py:220-228`；`src/runtime/intake/clean_preflight.py:28-127`（只读交接） | 新 Revision 语义切代；clean digest 不变；process-absence 在 NH8 前保持红 | `NH5-T08` | 切代可证；不 reclean 不假装已绿 |

---

## 5. Phase 详情

### 5.1 Phase 1 — 输入合同

- **Phase 目标**：generic 与 API 的五维权威入口可测；自动 `unknown` 从源码消失。
- **本 Phase 对应编号**：`NH5-01`
- **本 Phase 新增文件**：无生产新模块亦可；允许 `src/contracts/intake/semantic_authority.py`（nonunknown/provenance 校验）若避免把规则散落三 mapper。
- **本 Phase 修改文件**：`src/contracts/api/models.py:107-143`；`src/contracts/intake/semantics.py:12-63`；`intake/api/providers/chinatax.py:31-55`；`intake/api/providers/domain.py:50-78`；`intake/api/providers/realestate.py:102-108`；`intake/api/registry.py:36-104`
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. generic 三 descriptor 缺 `realm` 或任一四字段 → public model 422，且不得靠 `payload_extra` 绕过（`common/models.py:1-5,20-21`）。
  2. 四字段值为 `unknown`/`Unknown`/`  unknown  ` → 422。
  3. generic 请求带 `is_active` → 422（系统派生，caller 乱填失败）。
  4. chinatax 缺 `label`/`column` **不再**写成 `"unknown"`（HEAD `:33-34`）；未列入 `optional_unknown_fields` 则 mapper 失败，collection 不得用假六键 complete。
  5. domain `FilterMeta.channel = parsed.property_type or "Unknown"`（HEAD `:72`）与 realestate `channel=parsed.channel or "unknown"`、`source_name=... or "Unknown Agency"`（HEAD `:105-106`）删除自动填空。
  6. API caller 重复四字段与 mapper 不等 → 422；相等 → 以 mapper 为 SSOT 写入。
  7. 失败路径：registry 未列字段被 mapper 填入 → 架构扫描/单测失败；未登记第五 kind → 仍 422。
- **对应测试台账项**：`NH5-T01` / `NH5-T02`（详见 §8）
- **收口标准**：源扫描无 `or "unknown"`（三 provider）；generic 合同矩阵全红负例 + 一组合法四字段绿。
- **本 Phase 风险提醒**：`R-F08` unknown 回流；复制 API「缺字段就 unknown」到 generic 是本 Phase 禁止项。

### 5.2 Phase 2 — acceptance 闸 + 原子性

- **Phase 目标**：acceptance-complete ⇔ 六键非 stub；UoW 原子。
- **本 Phase 对应编号**：`NH5-02` / `NH5-03`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `acceptance_snapshot.py:576-710`、`acceptance_scatter.py:80-98`、`acceptance_lifecycle.py:360-380`；可能新增 forward-only provenance migration。无删除。
- **具体功能预期**：
  1. 四 kind 合法 ingest 后，`mkb_intake_revision_semantics` 含六键，经 PersistencePort/UoW 可读。
  2. `filter_metadata` JSON **不是** `{"source_kind": "<kind>"}`。
  3. 缺 `filter_meta` 或缺维 → 422，无新 serving revision，无新 vector_record indexed。
  4. API 三 operation 回归六键（`test_registered_api_scatter.py:296` 形状保持）。
  5. 只改 `realm` 的 metadata merge 必须重写 `filter_metadata` blob，否则 422/内部错误而非分叉成功。
  6. 失败路径：definition 表缺键 → `REGISTRY_NOT_FOUND` 503 仅用于登记缺失，不得用 stub 顶替。
- **对应测试台账项**：`NH5-T02` / `NH5-T03`
- **收口标准**：T03 四 kind × 6 rows；stub 负例不得 complete。
- **本 Phase 风险提醒**：`FG-NH-07`；只测 API 宣称四通道 = `FG-NH-14`。

### 5.3 Phase 3 — S06 overlay

- **Phase 目标**：S06 过滤账权威化，g0 正文账不变。
- **本 Phase 对应编号**：`NH5-04`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `generation_assemble.py:17-62,171-174`；`generation_construct.py` 调用点保持 overlay 顺序：先 g0 再 context（或同一函数内顺序明确）。无删除。不改 cuts 算法。
- **具体功能预期**：
  1. overlay 后唯一 g0，`body` = `normalize(clean)`。
  2. `context_meta.realm/type/channel/source_name` == S04 同行字符串。
  3. `context_meta.tags` == S04 `context_tags` 拆行（空 tags 允许，但是 S04 行存在）。
  4. 模型 candidate 带 `realm=hallucinated` → overlay 后被 S04 覆盖。
  5. g0.body / clean_text 不含 FilterMeta JSON 序列。
  6. 失败路径：S04 缺六键时 overlay 不得塞 `{}` 当成功，应在 structurize 前 fail-loud（与 Phase 2 闸一致）。
- **对应测试台账项**：`NH5-T04`
- **收口标准**：structure artifact diff：context=S04，g0 digest=clean digest。
- **本 Phase 风险提醒**：空 `context_meta={}` 当 overlay 成功是 `FG-NH-07`。

### 5.4 Phase 4 — 命名与投影

- **Phase 目标**：两轴同请求；facet 在 SQL 候选集生效。
- **本 Phase 对应编号**：`NH5-05` / `NH5-06` / `NH5-07`
- **本 Phase 新增 / 修改 / 删除文件**：修改 retrieval models/request/rank、API RetrievalFilter、vectorize facet upsert；允许 `src/services/retrieval/facet_keys.py` 闭集登记。无删除。不引入外部向量库。
- **具体功能预期**：
  1. 新 schema 请求可同时含 `filters.semantic_channel` 与 `filters.vector_channel` 且 2xx 路径不歧义。
  2. 旧 schema `channel=original|summary` 映射为 vector_channel；`channel=web` 422。
  3. 新 schema 带 `filters.channel` 422，即使值是 `original`。
  4. 未知 filter key 422 `RETRIEVE_FILTER_INVALID`。
  5. 两篇不同 realm 的已发布文档，按 `realm`/`semantic_channel` 过滤时，排除项即使用很大 `recall_k` 也不出现（SQL 层排除）。
  6. 无 namespace 的 search 422（`RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`），不得 200（`FG-NH-05`）。
  7. 失败路径：只 JOIN 不写 WHERE、或 rank 后再 `if facet !=` 丢弃 → T07 失败。
- **对应测试台账项**：`NH5-T05` / `NH5-T06` / `NH5-T07`
- **收口标准**：T07 L4 mega PASS；channel compatibility gate PASS。
- **本 Phase 风险提醒**：`R-F09`；`FG-NH-03/04` Task/`publication_ready` 顶替 query。

### 5.5 Phase 5 — metadata 切代

- **Phase 目标**：语义切代可检索；clean 字节身份不变；不假装 skip-clean 已落地。
- **本 Phase 对应编号**：`NH5-08`
- **本 Phase 新增 / 修改 / 删除文件**：修改 metadata merge 同源；🔱 `tests/e2e/test_intake_rebuild_metadata.py`。不修改 `clean_preflight.py` 旁路（NH8）。
- **具体功能预期**：
  1. 改 `realm` 后新 Revision，ordinal+1，`creation_action_key=update_metadata`。
  2. 新 Revision `clean_text` artifact 的 `content_digest` 与 `stored_object_uuid` 等于前序。
  3. 六键与 blob 一致；S06 overlay 与 facet 跟随 serving revision。
  4. 用新 realm 可 SQL 命中，旧 realm 排除。
  5. 指纹不变 → `no_change`，不追加 Revision（沿用 HEAD）。
  6. acquire/decode/clean `process_key` 计数 = 0。HEAD 现状使该条红；**保持红、交 NH8**。
- **对应测试台账项**：`NH5-T08`
- **收口标准**：T08-A（digest/facet/S06 切代）必须绿才可宣称 NH5 语义切代完成。T08-B process-absence 是 `NH5-08.d` → NH8 的 **handoff 红灯**，**不是** NH5 executed 硬闸。禁止 xfail / 禁止改期待值。
- **本 Phase 风险提醒**：`R-F11` rebuild 偷 reclean；既有 e2e 用 `sqlite3.connect`（`:138`）违反 `FG-NH-12`，本 AP 新断言必须走 Port/UoW。

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 Q 编号与 T-O-ID，不复制业主长文、不改口、不开新 Q/A。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| Q14 / `T-O-394` / `G-NH-05` CLOSED | `pre-charter-qna.md` §Q14 / §5 | Phase 1–2 合同与闸；禁自动 unknown | 不得执行 NH5；回退 QNA |
| Q15 / `T-O-395` / `G-NH-06` CLOSED | `pre-charter-qna.md` §Q15 / §5 | Phase 4 双键与旧 schema 窄适配 | 不得猜轴上线 |
| Q9 / `T-O-389` | `pre-initial-planning-qna.md` §Q9 / 真相表 | 四通道六元组进 S04、不进 g0；stub 不得 complete | 不得把 API 样板缩回三 provider |
| Q6 / `T-O-386` | `pre-initial-planning-qna.md` §Q6 / 真相表 | g0=admitted clean；overlay 不得改 g0 | 不得把五维写入 clean_text |
| Q26 / `T-O-406` | `pre-charter-qna.md` | T07 不得用 L1 顶替 L4；waiver 只延期 | 不得标 executed |
| Q27 / `T-O-407` / `G-NH-19` CLOSED | `pre-charter-qna.md` §Q27 | NH5-08 不落地 guard；T08-B 交 NH8 | 禁止 no-op cleaner |
| `P-semantic-unknown` = `CORRECT` | `final-execution-plan.md` §3 | generic nonunknown + API 禁自动 unknown | 不得再选宽松 unknown |
| `T-R-NH-13/14/27` | `final-execution-plan.md` §2.1–2.2 | HEAD 缺口：stub complete、S06 不读 S04、facet=0 | 以 HEAD 实测为准，不把 QNA 当已实现 |
| `T-O-376/381` | `pre-initial-planning-qna.md` | 四通道可检索终态；本 AP 提供过滤面，live matrix 仍归 NH7 | 不得用 503 当 DoD |
| `T-O-377` | `pre-initial-planning-qna.md` | 四 kind；禁 CF/SMCP/`action_branch` | OOS 硬围栏 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

> `处置`：`✅ 复用` / `♻️ 重 substrate` / `🆕 净新`。⛔ 反例只在 §7.2。台账 B 正例入本表；反例见 §7.2。`NH5-A06` 机制真源仍见 §7.3。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| `NH5-A01` | `src/contracts/intake/semantics.py:12-63` | FilterMeta 五维 + `semantic_tuples()` 恰好 6；`MappedProviderMember.semantic_tuples` min 6 | `NH5-01` 扩到四通道；generic 复用字段名与 min_length | `✅ 复用` | API 样板；不把「仅三 provider」当范围。HEAD 行号与 ledger 一致 |
| `NH5-A06` | RA07 WEB payload/index/filter | facet/query 机制：过滤字段显式索引、过滤推进 SQL、未索引 fail-fast、系统/业务字段分名 | `NH5-06/07` 落地 = 已有 `mkb_vector_record_facets` sidecar + parameterized SQL JOIN | `🔶参考` | **不借** Qdrant/pgvector/OpenSearch/ES/CF Vectorize / 自由 JSON payload / JSONB `@>`；真源 §7.3 |
| `NH5-A03` | `src/runtime/intake/generation_assemble.py:17-62` | `overlay_system_g0` 丢模型 g0，`body=clean`；`:59-60` 仍把缺 meta 写成 `{}` | `NH5-04` 保持 g0；平行 context overlay | `♻️ 重 substrate` | 不改 cuts。实测函数 `:17-62` 与 ledger 一致 |
| `NH5-A03b` | `src/runtime/intake/generation_construct.py:1214-1218` | 非 cuts 路径调用 `overlay_system_g0` | `NH5-04` overlay 调用点 | `✅ 复用` | 已建好，别重写切法 |
| `NH5-A07` | `src/services/retrieval/retrieval_request.py:265-270` | namespace 必填 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED` | `NH5-07` 围栏；L4 不得省略 | `✅ 复用` | 正例。PROMPT 写 265-269；实测 raise 块 `:265-270` |
| `NH5-A08` | `src/services/retrieval/retrieval_request.py:333-340` | unknown filter key 422 | `NH5-07` 扩到新 facet keys | `✅ 复用` | 正例 fail-closed |
| `NH5-A09` | `src/persistence/migrations/001_initial.sql:1045-1078` | `mkb_intake_revision_semantics` typed 账 | `NH5-02/03` 权威表 | `✅ 复用` | 登记≠写入 |
| `NH5-A10` | `src/persistence/migrations/001_initial.sql:1503-1522` | `mkb_vector_record_facets` sidecar | `NH5-06` 投影落点 | `♻️ 重 substrate` | 表形态可复用；今日只写 source_kind |
| `NH5-A11` | `src/runtime/intake/acceptance_lifecycle.py:253-278` | metadata 新 Revision 继承 clean stored object | `NH5-08` inherit clean | `✅ 复用` | 不宣称 HEAD 已 skip clean Process |
| `NH5-A12` | `src/services/registry.py:229-239` | `DEFAULT_SEMANTICS` 10 键含五维+tags | `NH5-02` 定义已对全部 intake 登记 | `✅ 复用` | `D-16=10`；勿重登记另一套键名 |
| `NH5-A13` | `intake/api/providers/chinatax.py:49-94` 等 | API mapper 写六元组 | `NH5-01` 回归保持；generic 不得抄 unknown 缺省 | `✅ 复用` | 既有字面 `realm=tax_china` 等保持 |
| `NH5-A14` | `tests/unit/test_retrieval_api_validation.py:77-85` | 省略 namespace → 422 | `NH5-05/07` 回归 | `✅ 复用` | L1 围栏 |
| `NH5-A15` | `tests/e2e/test_registered_api_scatter.py:287-296` | API e2e 六键 ⊆ revision_semantics | `NH5-02.c` 回归 | `✅ 复用` | 不得把 Task succeeded 当可检索 |

**行号漂移备注（HEAD `1221aa1` 独立 `read_file`）**：ledger `acceptance_snapshot.py:589-615` 含 `filter_meta = state.get`（`:589`）与 stub（`:591-615`）；函数始于 `:576`。`api/models.py` ingest 描述符止于 `:143`（RegisteredApi 到 `:173`）。`retrieval/models.py:14-34` 含 `_FILTER_KEYS` 与 `_REQUEST_KEYS`。

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| `NH5-A02` | `src/runtime/intake/acceptance_snapshot.py:591-615` 无 Mapping 时 `filter_metadata={"source_kind": source_kind}` 仍 complete | `T-O-389`；`T-R-NH-13/27`；`FG-NH-07`；RA07 `NH-RA07-B02`。本 AP `NH5-02` 必须拆掉该兜底 |
| `NH5-A04` | `src/runtime/intake/generation_construct.py:330-343` structurize 输入只有 clean/markdown；assemble `:59-60` 空 `{}` 或保留模型 context | `T-O-389` S06 必须读 S04；模型 realm 非权威。`NH5-04` overlay，**不**把五维塞进 user material |
| `NH5-A05` | `src/services/retrieval/models.py:14` `_FILTER_KEYS={intake_item_uuid,source_kind,channel}`；`retrieval_request.py:354-355` `channel∈{original,summary}` | `T-R-NH-27`；`T-O-395`。撞名吞掉 `FilterMeta.channel` |
| ⛔4 | `intake/api/providers/chinatax.py:33-34`；`domain.py:50-52,72`；`realestate.py:105-106` `or "unknown"` / `"Unknown"` / `"Unknown Agency"` | `T-O-394` 禁自动 unknown；`P-semantic-unknown CORRECT`。必须点名删除 |
| ⛔5 | `src/contracts/api/models.py:107-129` generic descriptor 无 FilterMeta 字段；`payload_extra` 控状态 | RA07 `NH-RA07-B01`；`common/models.py:1-5` |
| ⛔6 | `src/runtime/intake/vector_publish_commit.py:496-518` 只 upsert `facet_key=source_kind` | `D-07-F02=1`；source_kind ≠ 五维 |
| ⛔7 | `src/services/retrieval/retrieval_rank.py:80-122` 不 JOIN semantics/facets；若在 rank 后 Python 滤 realm | RA07 WEB pgvector/Supabase 后过滤失败法；`NH5-07` 禁止 |
| ⛔8 | `tests/e2e/test_single_intake_pipeline.py:121-130` search 无 namespace 却断言 200 | RA08 `NH-RA08-B02`；`FG-NH-05`。本 AP L4 禁止复制 |
| ⛔9 | `tests/e2e/test_intake_rebuild_metadata.py:138,229-241` sqlite3 直读 + search 无 namespace | `FG-NH-12`/`FG-NH-05`。T08 新断言走 Port；search 必带 namespace |
| ⛔10 | legacy `meta_fuser.ts` JSON 列当 SSOT；`recorder.ts` 把 realm 拼进 embedding 正文 | RA07 ⛔；`T-O-389`/`T-O-377` |
| ⛔11 | 按 value 猜 `summary`→向量、其它→业务 | `T-O-395` |
| ⛔12 | 复制 13 profile / 第五 kind / CF Vectorize payload | `O-NH-01/06`；`FG-NH-09` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：[`assessment-analysis-07-semantic-ledger-and-retrieval-facets.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-07-semantic-ledger-and-retrieval-facets.md) —— §7.1/7.2 是与本 AP 相关子集。完整借鉴台账见 RA07 §3/§7。
- **邻面消费（不改写）**：RA08 裁定「stub 不得 pretend publication-complete」；「可检索」= proof/pointer/serving **加上** 带 namespace 的 `retrieval:search` 命中；`publication_ready` / Task succeeded 不是终验（`NH-RA08-B02/B03`）。本 AP T07 必须遵守该边界。
- **`NH5-A06` RA07 WEB payload/index/filter**：🔶 借「过滤字段显式索引 / 过滤推进 SQL / 未索引可 fail-fast / 系统字段与业务字段分名 / ANN 后过滤 recall 塌缩」。**不借** Qdrant/pgvector/OpenSearch/ES/CF Vectorize 栈，不借自由 JSON payload，不借 JSONB `@>`。落地 = 已有 `mkb_vector_record_facets` + parameterized SQL JOIN。
- **安全 / 信任边界类工作项的威胁模型锚**（不得留空；对应 `NH5-01/05/07/08`）：

| 威胁 ID | 边界 | 攻击 / 失败 | 控制 | 测试 |
|---------|------|-------------|------|------|
| `T-NH5-SEC-01` | public ingest | `payload_extra` 注入五维绕过 typed 字段 | `extra=forbid`；payload_extra never controls state（`common/models.py:1-5`） | T01 负例 |
| `T-NH5-SEC-02` | retrieval filters | 自由键 / 表达式注入 | 闭集 `_FILTER_KEYS`；unknown 422；参数化 SQL | T07 |
| `T-NH5-SEC-03` | namespace | 缺 namespace 扫到 default Layer-A | `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED` | T07/T05；禁复制 121-130 |
| `T-NH5-SEC-04` | API mapper vs caller | caller 伪造 realm 覆盖 registry | mapper SSOT；不等 422 | T02 |
| `T-NH5-SEC-05` | SQL facet | 拼接用户字符串 | bound parameters only | T07 L2 SQL 形状 |
| `T-NH5-SEC-06` | metadata CAS | TOCTOU 换语义 | `METADATA_TARGET_STALE` 409（HEAD `:204`） | T08 |
| `T-NH5-SEC-07` | 跨团队 | 他队 facet 命中 | 既有 `r.team_uuid=?` 围栏保持 | T07 回归 |
| `T-NH5-SEC-08` | 供应链/栈 | 引入 CF/R2/外部向量 DB | `T-O-377`；OOS | 架构扫描 |

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH5-T01` | generic 必填/nonunknown；`is_active` 拒 caller | 短途 | L1 | `🆕 tests/unit/test_nh5_generic_semantic_contract.py` | `NH5-01` → generic 无 unknown | `commit SHA + pytest node PASS + Q14/T-O-394 + UTC` |
| `NH5-T02` | API 禁自动 unknown/冲突；未列字段不得填 | 短途 | L1/L2 | `🔱 tests/unit/test_intake_provider_registry.py` + 🆕 mapper negatives | `NH5-01/02` → API 无自动填空 | `commit SHA + mapper negatives PASS + Q14 + UTC` |
| `NH5-T03` | 四 kind 写 6 rows；stub 不得 complete | 短途/集成 | L2 | `🆕 tests/integration/test_nh5_acceptance_six_tuple.py` | `NH5-02/03` → 六元组非 stub | `commit SHA + DB rows via Port PASS + T-O-389 + UTC` |
| `NH5-T04` | S06 context=S04 且 g0=clean；模型 realm 丢弃 | 短途 | L2 | `♻️ tests/unit/test_r5_assemble.py` + 🆕 `tests/integration/test_nh5_s04_overlay.py` | `NH5-04` → 分账 | `commit SHA + overlay PASS + Q14/T-O-386 + UTC` |
| `NH5-T05` | 新双 channel 同请求 | 短途 | L1/L3 | `🆕 tests/unit/test_nh5_channel_split_schema.py` + 🆕 `tests/e2e/test_nh5_channel_split.py` | `NH5-05` → 双键共存 | `commit SHA + API PASS + Q15 + UTC` |
| `NH5-T06` | 旧 `channel` 窄迁移；other 422；新 schema 旧键 422 | compat | L1/L3 | `🆕 tests/e2e/test_nh5_legacy_channel_compat.py` | `NH5-05` → 旧键仅原枚举 | `commit SHA + legacy schema PASS + Q15 + UTC` |
| `NH5-T07` | facet 命中/排除/unknown；SQL 层过滤；namespace | mega | L2/L4 | `🆕 tests/e2e/test_nh5_facet_retrieval.py` | `NH5-06/07` → SQL 可滤 | `commit SHA + query PASS + T-O-395 + UTC` |
| `NH5-T08` | metadata 切代 clean 不变；facet/S06 变 | 集成 | L2/L4 | 🆕 `tests/e2e/test_nh5_metadata_semantic_refresh.py`（T08-A PASS）+ 🔱 `tests/e2e/test_intake_rebuild_metadata.py`（仅当 sqlite3 已删且 search 带 namespace） | `NH5-08` → 切代 ∧ inherit | `commit SHA + digest/facet PASS + Q27 + UTC` |

#### `NH5-T01`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh5_generic_semantic_contract.py` · `test_generic_descriptor_requires_nonunknown_four_fields` · `test_generic_unknown_and_blank_rejected` · `test_generic_caller_is_active_rejected` · `test_payload_extra_cannot_supply_filter_meta` |
| 用途 | 证明 `NH5-01`；`FG-NH-07` 入口侧；`T-NH5-SEC-01` |
| 前置 | 无 DB；直接 `model_validate` 三 descriptor；不启 app |
| 步骤 | a) 合法四字段+缺 `is_active` 通过。b) 缺 `realm`/`type`/`channel`/`source_name` 各一次。c) 值为 `unknown`/`Unknown`/`""`。d) 带 `is_active: 1`。e) 只把五维放进 `payload_extra`。 |
| 断言细节 | b–e HTTP/Validation 失败（public ingest 路径 422 或 ValidationError）；error 不回显秘密；成功样例 `is_active` 不在 dump 的 caller 字段中 |
| 负例 | `realm="unknown"`；`channel="original"` **允许**（业务维可叫 original）；`payload_extra={"realm":"x"}` 不得使 state 有 FilterMeta |
| 跑法 | `uv run pytest tests/unit/test_nh5_generic_semantic_contract.py -q` |
| 层与来源 | L1；`🆕` |

#### `NH5-T02`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 `tests/unit/test_intake_provider_registry.py` 保持闭集；🆕 `tests/unit/test_nh5_api_mapper_unknown.py` · `test_chinatax_missing_label_does_not_write_unknown` · `test_domain_does_not_default_unknown_channel` · `test_realestate_does_not_default_unknown_agency` · `test_caller_conflict_with_mapper_422` · `test_optional_unknown_only_when_registry_and_frozen_literal` |
| 用途 | `NH5-01/02`；点名修 HEAD `chinatax.py:33-34`、`domain.py:50-52,72`、`realestate.py:105-106` |
| 前置 | frozen records fixture；registry 真实 `REGISTERED_PROVIDER_OPERATIONS`；禁止 monkeypatch mapper 为恒 unknown |
| 步骤 | a) 缺可选字面且未登记 → mapper/parse 422，不产生 `FilterMeta.channel=="unknown"`。b) 完整 chinatax 记录回归 `tests/intake/test_api_chinatax.py:47-62` 五维字面。c) caller 重复 realm 与 mapper 不等 → 422。d) 若测试临时把字段列入 `optional_unknown_fields` 且 record 显式 `"unknown"` → 允许写入并 provenance=mapper。e) 未列字段即使 record 缺值也不得填。 |
| 断言细节 | 源扫描：三 provider 文件无 `or "unknown"` 赋给 FilterMeta；冲突码稳定（422 `INTAKE_SEMANTIC_CONFLICT` 或现有 taxonomy）；chinatax `is_active` 仍由 `全文有效` 规则派生 |
| 负例 | `saleMode` 缺失却写出 `type=unknown`；registry 未列字段被填 |
| 跑法 | `uv run pytest tests/unit/test_intake_provider_registry.py tests/unit/test_nh5_api_mapper_unknown.py tests/intake/test_api_chinatax.py -q` |
| 层与来源 | L1/L2；`🔱` + `🆕` |

#### `NH5-T03`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/integration/test_nh5_acceptance_six_tuple.py` · `test_four_kinds_persist_six_semantic_rows` · `test_source_kind_stub_cannot_complete` |
| 用途 | `NH5-02/03`；`FG-NH-07`；`FG-NH-14`（必须四 kind，不只 API） |
| 前置 | 真实 UoW/PersistencePort；Turso/sqlite 测试配置经 app/port；**禁止** `sqlite3.connect` 当证明；四 kind 最小合法 payload（http/local 可用 fixture 对象/URL，不要求 NH6 live browser） |
| 步骤 | a) 每 kind 一次合法 admission。b) Port `fetchall` revision_semantics。c) 构造缺 `filter_meta` 或只给 source_kind 的内部 state 调 `_initial_semantics_tx`（或 public ingest 缺字段）。d) 断言无 complete、无 indexed vector。 |
| 断言细节 | 六键集合 `== {realm,type,channel,source_name,is_active,context_tags}`；`filter_metadata` JSON 不是 `{"source_kind": ...}`；value_digest 长度 64；四 kind 各至少 1 revision。负例 HTTP 422，Item/vector 计数 0 |
| 负例 | stub blob complete；只插入四条 bootstrap 无五维仍标 complete |
| 跑法 | `uv run pytest tests/integration/test_nh5_acceptance_six_tuple.py -q` |
| 层与来源 | L2；`🆕` |

#### `NH5-T04`

| 字段 | 要求 |
|---|---|
| 测试位置 | ♻️ `tests/unit/test_r5_assemble.py::test_overlay_drops_fragment_g0_and_admits` 保持 g0 夹具；🆕 同文件 `test_overlay_context_meta_equals_s04_and_drops_model_realm` · `test_g0_body_digest_equals_clean`。**L2 强制** 🆕 `tests/integration/test_nh5_s04_overlay.py::test_overlay_consumes_committed_s04_six_tuple` |
| 用途 | `NH5-04`；`FG-NH-07` 空 context；`FG-NH-13`（unit 不得顶 L2）；`T-O-386` |
| 前置 | L1 夹具可用合成 dict。L2：经 PersistencePort 写入并 **commit** `mkb_intake_revision_semantics` 六键，再跑 overlay/construct；禁止只对内存 fixture 关闭 T04 |
| 步骤 | a) unit overlay g0+context（夹具）。b) L2：Port 读已 commit 的六键，跑 overlay。c) 计算 g0.body 与 admitted clean 的 digest。d) 对比 `context_meta` 与 DB 行。e) cuts 路径同样覆盖。 |
| 断言细节 | `context_meta.*` 与 DB S04 行逐字相等且 ≠ `"hallucinated"`；g0 唯一；`g0` digest = admitted clean；`normalize(g0.body)==normalize(clean)`；g0.body 不含 `"realm"` JSON 块；HEAD `generation_assemble.py:59-60` 缺 meta 写 `{}` 不得在 admit 后存活 |
| 负例 | overlay 后 `context_meta=={}` 当成功；模型 realm 胜出；仅 unit 合成 fixture 绿宣称 T04 PASS |
| 跑法 | `uv run pytest tests/unit/test_r5_assemble.py tests/integration/test_nh5_s04_overlay.py::test_overlay_consumes_committed_s04_six_tuple -q` |
| 层与来源 | L2；`♻️` unit 夹具 + `🆕` L2；unit 不得单独当 T04 PASS |

#### `NH5-T05`

| 字段 | 要求 |
|---|---|
| 测试位置 | L1 🆕 `tests/unit/test_nh5_channel_split_schema.py::test_new_schema_accepts_semantic_and_vector_channel_together`。**L3 强制独立 id** 🆕 `tests/e2e/test_nh5_channel_split.py::test_new_schema_dual_channel_same_request`（不得「可放」；不得并入 T07 schema 段顶替） |
| 用途 | `NH5-05`；`T-O-395`；`R-F09`；`FG-NH-13`（L1 不可顶 L3） |
| 前置 | 新 schema_version；`create_app()` default-root；Bearer；**必填** namespace |
| 步骤 | a) L1：新 schema filters 同时设 `semantic_channel` 与 `vector_channel=summary`。b) 归一化后内部 `vector_channel` 绑 `r.channel`，`semantic_channel` 绑 facet。c) L3：default-root POST `/v1/teams/{t}/retrieval:search` 同时带 `semantic_channel`+`vector_channel` + namespace。 |
| 断言细节 | 归一化 dict 含两键；L3 HTTP 非 422；旧键缺席 |
| 负例 | 新 schema 同时靠 value 推断轴；只跑 unit schema 关闭 T05 |
| 跑法 | `uv run pytest tests/unit/test_nh5_channel_split_schema.py::test_new_schema_accepts_semantic_and_vector_channel_together tests/e2e/test_nh5_channel_split.py::test_new_schema_dual_channel_same_request -q` |
| 层与来源 | L1/L3；`🆕`；L1 schema 不能单独关闭 T05 |

#### `NH5-T06`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh5_legacy_channel_compat.py` · `test_v1_channel_original_maps_to_vector_channel` · `test_v1_channel_web_422` · `test_new_schema_legacy_channel_key_422` |
| 用途 | `NH5-05` 兼容；禁止猜轴 |
| 前置 | `create_app()` 默认根；auth token；namespace 必填 |
| 步骤 | a) `schema_version=mkb.retrieval.v1` + `filters.channel=original` → 视为 `vector_channel`。b) `channel=web` / `sold` / `summary` 当业务维 → 422。c) 新 schema + `filters.channel=original` → 422。 |
| 断言细节 | a) 200 或检索 taxonomy 成功码，且诊断/弃用信号存在（若实现暴露）；b/c) 422，`RETRIEVE_FILTER_INVALID` 或稳定兼容码；body 不按 value 改写为 semantic |
| 负例 | `channel=sold` 被当成 FilterMeta.channel |
| 跑法 | `uv run pytest tests/e2e/test_nh5_legacy_channel_compat.py -q` |
| 层与来源 | L1/L3；`🆕` |

#### `NH5-T07`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh5_facet_retrieval.py` · `test_namespace_required` · `test_unknown_filter_key_422` · `test_realm_or_semantic_channel_hit_and_exclude_at_sql` · L2 伴生 `tests/unit/test_nh5_facet_sql_not_postfilter.py` |
| 用途 | `NH5-06/07`；本 AP **L4 硬闸**；`FG-NH-03/04/05/06/07/13`；RA08 检索终验边界 |
| 前置 | default-root `create_app()`；**必须** `namespace_key` 或 `namespace_uuid`；真实 search POST；禁止 monkeypatch fetcher/LLM；禁止 Task succeeded 当命中；禁止直接 INSERT `mkb_vector_records` / facets 作为 L4 成功路径 |
| 步骤 | a) default-root **两次合法 ingest**（不同 `realm`/`semantic_channel`）。b) 断言 admitted `clean_text` **非空**（`FG-NH-06`）。c) 等待 publication proof/pointer/serving。d) **然后** namespaced search：无 namespace → 422。e) `filters={"forbidden":...}` → 422。f) 过滤 realm=A（或 semantic_channel=A），`recall_k` 足够大。g) L2 伴生：捕获 `_fetch_candidate_rows` SQL，断言 WHERE/JOIN 含 facet 或 revision_semantics 参数，且 rank/pack 路径无 Python 按该键丢弃。h) 增大 `recall_k` 后排除 realm 仍不出现。 |
| 断言细节 | HTTP 200 + `disposition=ok`；命中 payload 属于 A；B 的 `intake_item_uuid` 不在 results；候选行计数（经 Port 或 SQL 捕获）在 rank 前已排除 B；unknown key `RETRIEVE_FILTER_INVALID` 422。L2 SQL 形状测试可并行，**不得顶替** L4 |
| 负例 | 无 namespace 200（`test_single_intake_pipeline.py:121-130` 形状）；只断言 `publication_ready`；post-filter 靠 Python；从「已 indexed」种植行后直接 POST search；空 clean 向量当命中 |
| 跑法 | `uv run pytest tests/e2e/test_nh5_facet_retrieval.py tests/unit/test_nh5_facet_sql_not_postfilter.py -q` |
| 层与来源 | L2/L4；`🆕`；**不可降层** |

#### `NH5-T08`

| 字段 | 要求 |
|---|---|
| 测试位置 | **T08-A PASS** 🆕 `tests/e2e/test_nh5_metadata_semantic_refresh.py::test_metadata_refresh_inherits_clean_and_projects_facets`。🔱 `tests/e2e/test_intake_rebuild_metadata.py::test_rebuild_and_metadata_lifecycle_paths_complete_through_public_http` **仅当**已删除 `import sqlite3`/`sqlite3.connect`、search 必带 namespace（省略 → 422）、命中以 search body 为准（不以 Task `succeeded` 为 PASS），并列入跑法；否则从 T08 PASS 位置去掉该 HEAD 节点，§8.2 标 ⛔。T08-B 补充 node：`::test_metadata_refresh_process_absence_handoff_to_nh8`（handoff 红灯，不是 executed 硬闸） |
| 用途 | `NH5-08`；T08-A = NH5 语义切代（final PASS = digest/facet）；T08-B = `NH5-08.d` → **`NH8-T03`/`NH8-03`** exact-clean **handoff 红灯**；`FG-NH-03/05/12/17` |
| 前置 | 先合法 ingest 带六元组；经 Port 读 clean digest/object；metadata 改 `realm`；search **带 namespace**。T08-A 只经 Port 证明 digest/object 不变。禁止 sqlite3 直读 |
| 步骤 | a) ingest。b) `intake.update_metadata` 改 realm。c) Port 读新旧 revision、clean artifact、semantics、facets。d) namespaced search 按新 realm 命中、旧 realm 排除。e) T08-B：计该 Task `mkb_processes.process_key` 中 acquire/decode/clean 出现次数（HEAD 预期 ≠0，记 handoff，禁止 xfail）。 |
| 断言细节 | **T08-A**（本 AP PASS）：新 `intake_revision_uuid`；`clean content_digest` 与 `stored_object_uuid` 不变；六键+blob 同源；S06 context 与 facet = 新 S04。**T08-B**：acquire/decode/clean process 计数 = 0 才算旁路落地；HEAD 现状必须红 → 交接 **`NH8-T03`/`NH8-03`**，**不得**作为 NH5 executed 硬闸。 |
| 负例 | 用 sqlite3 直读当 L2 证明；把 T08-B 改成 xfail 或删断言使全绿；search 无 namespace 200；以 Task `succeeded` 当检索证明；「避开」同时 🔱 未改造 HEAD 节点 |
| 跑法 | T08-A PASS：`uv run pytest tests/e2e/test_nh5_metadata_semantic_refresh.py::test_metadata_refresh_inherits_clean_and_projects_facets -q`。T08-B handoff **另跑** `::test_metadata_refresh_process_absence_handoff_to_nh8`（HEAD 预期红，记 evidence，**不**并入 T08 PASS 命令）。若选择改造 HEAD 节点则追加 `tests/e2e/test_intake_rebuild_metadata.py::test_rebuild_and_metadata_lifecycle_paths_complete_through_public_http` |
| 层与来源 | L2/L4；T08-A `🆕`；HEAD 文件未清 sqlite3 则 ⛔ 不得 🔱。**xfail 禁止** |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_intake_provider_registry.py` | `🔱 fork` 断言 + 🆕 mapper 负例文件 | + 禁 unknown / 冲突 | 已存在；本 AP 加负例 |
| `tests/intake/test_api_chinatax.py:47-62` | `♻️ 沿用` | 0 或仅保证不回退五维字面 | 已存在 PASS 形状 |
| `tests/e2e/test_registered_api_scatter.py:287-296` | `♻️ 沿用` | 0；六键回归 | 已存在；**无** search 终验（交 NH7/RA08） |
| `tests/unit/test_r5_assemble.py` | `♻️ 沿用 g0` + 🆕 context overlay | + S04 覆盖断言 | g0 正例已存在 |
| `tests/unit/test_retrieval_service.py:456-460` | `♻️ 沿用` unknown key | 扩 key 后回归 forbidden 仍 422 | 已存在 PASS |
| `tests/unit/test_retrieval_api_validation.py:77-85` | `♻️ 沿用` namespace | 0 | 已存在 PASS |
| `tests/unit/test_metadata_semantics.py` | `♻️ 沿用` CAS/definition freeze | 六元组同源可加断言 | 已存在 |
| `tests/e2e/test_intake_rebuild_metadata.py` | 未删 `sqlite3.connect`、未补 namespace 前 = **⛔ 反例**（不得 🔱）。改造后（无 sqlite3、search 带 namespace、命中以 search body 为准）才可 🔱 列入 T08 跑法 | 禁止「避开」同时 🔱 | HEAD `:6` import sqlite3、`:26` turso、`:138+` 直读、`:229-241` 无 namespace 却 200 |
| `tests/e2e/test_single_intake_pipeline.py:121-130` | **不沿用为 L4 正例** | 本 AP 不得复制无 namespace | 反例（RA08） |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest` 本 AP L1/L2 节点 | unit·集成·契约 | 每 PR |
| spike/集成 | T03 UoW 六元组；T04 L2 `tests/integration/test_nh5_s04_overlay.py` | L2 | Phase 2/3 收口 |
| default-root | T05 `tests/e2e/test_nh5_channel_split.py::test_new_schema_dual_channel_same_request` + T06 `create_app()` | L3 | Phase 4 收口 |
| mega | T07 namespace+facet SQL | L4 | **本 AP 退出硬闸** |
| soak | 无本 AP 专属 soak | — | 交 NH9 race；不在本 AP 假装覆盖 |

测试分层遵守 `T-O-406`：L1 unit / L2 integration·UoW / L3 default-root e2e / L4 retrieval-facet。fault/race/security 是标签不是替代层。本 AP 台账 C 最低层：T07 L4、T05/T06 含 L3、T08 含 L2/L4，不得自行降层。

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 10 strategy + 3 operation live-to-vector 全矩阵（理由：`S-NH-F7` / NH7）→ `AP-NH7`。
- 不覆盖七意图非法格与 rebuild intent guard 旁路（理由：`T-O-405/407`）→ `AP-NH8`。`NH5-T08-B` process-absence 红灯交 `NH8-T03`/`NH8-03` 转绿，不是 NH5 假绿。
- 不覆盖 closed-set / crash / campaign mega（理由：`S-NH-F9`）→ `AP-NH9`。
- 不覆盖 browser/OCR 真实供给（理由：`S-NH-F6`）→ `AP-NH6`；本 AP http/local 可用最小 fixture 证语义闸，不宣称 capability live。
- 不覆盖 raw GET / upload（理由：`S-NH-F4`）→ `AP-NH4`。
- **不在本 AP 假装覆盖** API scatter 的 retrieval 终验（RA08：该文件零 `retrieval:search`）。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组：`commit SHA + pytest node PASS + Truth/Q + UTC`。计数 ≠ 价值。
- 本 AP 适用 FG（必须在对应测试点名）：
  - `FG-NH-03/04`：T07 禁止 Task succeeded / `publication_ready` 顶替 hit。
  - `FG-NH-05`：T05/T07/T08 无 namespace 不得 200。
  - `FG-NH-06`：T07 种植路径必须非空 admitted clean。
  - `FG-NH-07`：T01–T04 stub/空 context/`unknown` 填空。
  - `FG-NH-12`：T03/T07/T08 禁止 sqlite3 直读 Turso。
  - `FG-NH-13`：T04 不得用 unit overlay 顶 L2；T05 不得用 L1 顶 L3；T07 不得降成 L1。
  - `FG-NH-14`：T03 必须四 kind。
  - `FG-NH-17`：T08-B 禁止改期待值/xfail 掩盖 S1。
- `degraded` 必带机器可读 reason；T08-B HEAD 红灯记为 **handoff to NH8**，不是 NH5 executed 硬闸，也不是 pre-existing 可忽略。
- 安全项 T01/T02/T07 含攻击向量：payload_extra、冲突伪造、unknown filter key、无 namespace。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| DAG：NH1 GO | `stop-or-go.md≠GO` 则并行窗不得开工 | high（外部） | STOP/reopen；禁止部分绿；不得静默换 duplication |
| `R-F08` unknown 回流 | mapper/caller 再填 unknown | high | T01/T02 源扫描 + schema |
| `R-F09` channel 双义 | 同 schema 按 value 猜 | high | versioned adapter；T05/T06 |
| `R-F11` 偷 reclean | metadata 再跑 deterministic clean | high | T08-B 红灯交 NH8；禁 no-op worker |
| `R-F13/14` 层顶替 | L1 或 Task 顶 L4 | high | T07 硬闸；`T-O-406` |
| NH7 join | facet 未就绪则 vertical 不可滤 | medium | 本 AP T07 为 join 条件之一 |
| 旧检索客户端 | `mkb.retrieval.v1` `channel` | medium | 窄映射 + 弃用；other 422 |
| 历史 stub 行 | 无六元组不可 backfill | medium | 禁止 unknown backfill；需 metadata 切代 |

### 9.2 约束与前提

- **技术前提**：HEAD `1221aa1` S04 表、system g0、unknown filter fail-closed、facet 表、metadata inherit clean 骨架均在；NH1 证明 chosen substrate 可用。
- **运行时前提**：L3/L4 使用 `create_app()` 默认根；namespace 必填；不把 503 当 DoD。
- **组织协作前提**：不重开 Q14/Q15；不新增 owner-gate；NH8 以 `NH8-T03` 接收 T08-B。
- **上线 / 合并前提**：`NH5-T01..T08` 全 PASS（T08 = T08-A digest/facet）。T08-B 红灯交接 NH8，**不得**作为本 AP executed 硬闸。禁止 xfail / 禁止改期待值。

### 9.3 文档同步要求

- 需要同步更新的设计文档：公开 ingest/retrieval 字段说明（执行时，不在本轮改 QNA/final）
- 需要同步更新的说明文档 / README：retrieval schema 版本与弃用 `filters.channel`
- 需要同步更新的测试说明：evidence pack `docs/evidence/new-harvest/AP-NH5/` 文件名见 §10

### 9.4 完成后的预期状态

1. 四 kind admission 都有非 stub 六元组；generic 无 `unknown`；API 无 `or "unknown"`。
2. S06 `context_meta` 与 S04 逐字相等；g0 仍等于 admitted clean。
3. 公开检索新 schema 双键共存；旧 schema 仅 original/summary；facet 在候选 SQL 可命中/排除。
4. metadata 改五维产生新 Revision 且 clean digest/object 不变。
5. T08-B 在 NH8 前如实红灯；RA08 检索终验边界被 T07 遵守（有 namespace 的真实 search）。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有退出层测试项必须 **PASS 且四元组证据齐全**。T08 PASS = T08-A（digest/facet/S06 切代）。T08-B 是 handoff 红灯，不是本表硬闸：

1. 四 kind 六元组非 stub；generic 无 unknown；API 无自动填空（`NH5-T01`..`NH5-T03`）。
2. S06 context 逐字等于 S04，g0 digest 等于 clean（`NH5-T04`）。
3. 新双键共存；旧键仅原枚举；other 与新 schema 旧键 422（`NH5-T05`/`NH5-T06`）。
4. realm/`semantic_channel` 可在**候选 SQL** 命中/排除；unknown key 失败；无 namespace 不得 200（`NH5-T07`，L4）。
5. 新 Revision 语义切代，clean digest/object 不变（`NH5-T08` T08-A）。
6. `FG-NH-07` 与 channel compatibility gate 通过（final §7.5 DoD）。
7. T08-B process-absence 映射 `NH5-08.d` → NH8：**handoff 红灯**，禁止 xfail / 禁止改期待值；**不得**作为 NH5 executed 硬闸。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| 四 kind 六元组非 stub；generic 无 unknown；API 无自动填空 | `NH5-01` `NH5-02` `NH5-03` | `NH5-T01` `NH5-T02` `NH5-T03` | `commit SHA + schema matrix/DB rows PASS + Q14/T-O-389 + UTC` | `未观察` |
| context 逐字等于 S04，g0 digest 等于 clean | `NH5-04` | `NH5-T04` | `commit SHA + overlay PASS + Q14/T-O-386 + UTC` | `未观察` |
| 新双键共存，旧键仅原枚举，other 422 | `NH5-05` | `NH5-T05` `NH5-T06` | `commit SHA + API PASS + Q15 + UTC` | `未观察` |
| realm 等可在候选 SQL 命中/排除，unknown key 失败 | `NH5-06` `NH5-07` | `NH5-T07` | `commit SHA + query plan/results PASS + T-O-395 + UTC` | `未观察` |
| new Revision 语义切代，clean digest/object 不变 | `NH5-08` | `NH5-T08`（T08-A） | `commit SHA + digest/facet PASS + Q27 + UTC` | `未观察` |
| metadata Task 无 acquire/decode/clean Process | `NH5-08.d` → NH8 | `NH5-T08`（T08-B） | `commit SHA + process count PASS + T-O-407 + UTC` | `deferred`（HEAD 预期红；禁止 silent pass） |

**谓词形态（判定句，禁止「测试通过」空话）**：

- **semantic authority**：对 `inline_payload`/`local_object`/`http_resource`/`registered_api` 各至少一次成功 admission 后，经 PersistencePort 查询 `mkb_intake_revision_semantics`，键集等于六元组且 `filter_metadata` JSON 不等于 `{"source_kind": <kind>}`；generic 任一四字段缺失/`unknown`/空串的 public ingest 返回 422；三 provider 源文件不存在把缺值写成 `"unknown"` 的 FilterMeta 赋值。
- **S06/g0 分账**：同一 Revision 的 layered artifact 中 `context_meta.{realm,type,channel,source_name}` 与 S04 同行字符串相等，`g0.original_content.body` 的 digest 等于 admitted clean digest，且 g0 正文不包含 FilterMeta 序列化。
- **channel contract**：新 schema 单请求同时接受 `semantic_channel` 与 `vector_channel` 且不 422；`mkb.retrieval.v1` 的 `filters.channel=original|summary` 机械映射为 `vector_channel`；`filters.channel=web`（及其它非原枚举）422；新 schema 出现键 `channel` 422。
- **facets**：两篇不同 realm 的 indexed 文档，带 namespace 的 search 在候选 SQL 层排除非目标 realm（增大 `recall_k` 仍排除）；未登记 filter key 422。
- **metadata**：`intake.update_metadata` 改参与指纹的五维后，新 `intake_revision_uuid` 存在，新 clean artifact 的 `content_digest` 与 `stored_object_uuid` 等于前序，facet/S06 跟随新 serving revision。

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | §10.2 五条谓词成立；三名分账出现在公开合同 |
| 测试 | `NH5-T01`..`NH5-T08` 全 PASS（T08 = T08-A digest/facet）；T08-B 显式 handoff（红灯）交 NH8，禁止 xfail / 禁止改期待值 |
| 文档 | 本 AP 仍 `draft` 直至执行回填；evidence pack 文件存在且 SHA 真实 |
| 风险收敛 | `R-F08/09` 由 T01–T06 关闭；`R-F11` 不在本 AP 假装关闭 |
| 可交付性 | NH7 可消费 facet 键；NH8 接收 T08-B |

**Evidence pack 目录**（final §9.3；本 AP 只规定文件名，不伪造 SHA）：`docs/evidence/new-harvest/AP-NH5/`

1. `manifest.json`：commit、Truth/Q（Q14/Q15/`T-O-389/394/395`）、work `NH5-01..08`、test `NH5-T01..08`、UTC
2. `tests.txt`：node IDs、exit code、duration、environment
3. `queries/generic-contract.json`、`queries/six-tuple-four-kinds.json`、`queries/overlay-diff.json`、`queries/channel-split.json`、`queries/facet-sql.json`、`queries/metadata-lineage.json`
4. `migrations/`：facet backfill/provenance 若有；before/after；禁止 unknown backfill 证明
5. `security/`：payload_extra 负例、unknown filter、namespace 422、mapper 冲突
6. `closure.md`：台账 D 逐目标 PASS/FAIL 与 NOT-success 扫描

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。

下列任一成立即 **NOT-成功**（抄 final §7.5 并补本 AP 假绿）：

1. `source_kind` stub 仍 acceptance-complete（`FG-NH-07`）
2. 空 `context_meta={}` 当 overlay 成功
3. 模型 realm 当权威
4. topK 后 Python post-filter 冒充 facet
5. 按 value 猜 axis（`channel=summary` vs 业务维）
6. API/generic `or "unknown"` 自动填空
7. 无 namespace 的 retrieval 200（`FG-NH-05`）
8. 只测 API 宣称四通道（`FG-NH-14`）
9. Task `succeeded` / `publication_ready` 当可检索（`FG-NH-03/04`）
10. sqlite3 直读 Turso 当 UoW 证明（`FG-NH-12`）
11. T08-B xfail / 改期待值掩盖仍跑 clean（`FG-NH-17`；`R-F11`）
12. 503 / monkeypatch 当 L3 成功
13. 用 `source_kind` facet 冒充五维 facet
14. `payload_extra` 成为 FilterMeta SSOT

---

## 11. 执行日志回填（仅 `executed` 状态使用）

原 draft 占位已由文末 append-only `§12` 厚版执行日志取代；T08-B 保持红灯交 NH8。

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-29` | Grok workflow | 由 final §7 派生 |
| `v0.2` | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：T04 强制 L2 读已 commit S04；T05 钉死 L3 node 并列入跑法；T07 必须经 ingest→非空 admitted clean→publication 再 search；T08 PASS=T08-A，T08-B 仅 NH8 handoff；HEAD metadata e2e 未清 sqlite3 不得 🔱 |
| `v0.3` | `2026-08-29` | Grok recon-fix | 开工闸改为 `stop-or-go.md=GO` 且与 NH2 互不等；`NH5-T08-B`→`NH8-T03`；§7.1 补 `NH5-A06`；头部自承 Capstone G=`NH5-T07` |

---

## 12. 执行日志回填（append-only）

> 执行者：`Codex`
> 执行时间：`2026-08-30`（evidence UTC `2026-08-29T21:38:33Z`）
> 文档状态：`draft → executing → executed`
> 代码改动统计：实现提交 `76f233b`（70 files；production migration `1`）

- **实际执行摘要**：
  - Phase 1（`NH5-01`）：generic descriptor 强制四维 nonunknown + tags；is_active 系统派生；三 provider 删除 unknown fallback；API 重复维度成为 mapper equality fence。
  - Phase 2（`NH5-02/03`）：acceptance 只接受完整六元组，四 kind 均写 10-entry semantic set；blob/scalar/digest/provenance 同源，stub 无法建 Revision/vector。
  - Phase 3（`NH5-04`）：structurize 从 committed S04 读六元组并覆盖模型 context；StructureDocument 新产物携 context；g0 正文仍只等于 admitted clean。
  - Phase 4（`NH5-05/06/07`）：新增 `mkb.retrieval.v2` 双 channel；v1 窄映射；vectorize 写六 facet；retrieval 用 correlated EXISTS 在 LIMIT/rank 前过滤。
  - Phase 5（`NH5-08`）：metadata 合并重建两个 blob，新 Revision 继承 exact clean object，复制新 context-aware structure family并重投影 facet；新/旧 realm namespaced search 切代。
- **Phase 偏差（计划 vs 实际）**：
  - `NH5-V01 (compatibility)`：`ProviderOperationDefinition.optional_unknown_fields` 在空集合时不进入 manifest canonical bytes，保持 NH1 3-op digest；未来非空才显式改变 definition digest。
  - `NH5-V02 (schema)`：provenance migration 使用 collision-safe `022`；旧行标 `legacy_unverifiable`，禁止猜 caller/mapper。
  - `NH5-V03 (S06 payload)`：StructureDocument 的 `context_meta` 仅在非空时进入 payload/digest；旧无 context payload 仍可 parse 且旧 digest 不漂移。
  - `NH5-V04 (metadata substrate-fit)`：metadata refresh 不只改 construction header，而是生成同 execution 的新 structure/projection/validation 三件套，避免 serving revision 指向旧 S06 context。
  - `NH5-V05 (fixture migration)`：57 个 generic source 测试 fixture 机械加入合法四维；未在 production 添加默认值或 test-only bypass。
- **阻塞与处理**：NH5 hard gates 无 blocker。T08-B 实测 acquire/decode/clean count=3，按设计保留为 NH8 红灯；未 xfail、未把期望改成 3。
- **测试发现**：NH5 hard suite `39 passed`；全仓 `753 collected / 748 passed / 5 successor-owned failed`；realestate newline 既有失败随 provider normalization 关闭。
- **后续 handoff**：NH7 消费 v2 facets；NH8 关闭 T08-B 与四个 namespace/rebuild failure；NH9 复核 semantic replay/closed-set。

### 12.1 逐工作项状态

| 工作项 | 状态 | PR / commit | 实际落点 | 备注 |
|--------|------|-------------|----------|------|
| `NH5-01` | `✅ done` | `76f233b` | API models; semantics; provider registry/mappers | strict authority |
| `NH5-02` | `✅ done` | `76f233b` | `acceptance_snapshot.py`; scatter path | six-tuple gate |
| `NH5-03` | `✅ done` | `76f233b` | migration 022; semantic insert/merge | atomic/provenance |
| `NH5-04` | `✅ done` | `76f233b` | generation overlay + compiler payload | S04-owned context |
| `NH5-05` | `✅ done` | `76f233b` | retrieval v1/v2 contracts | channel split |
| `NH5-06` | `✅ done` | `76f233b` | vector facet projection | six facet keys |
| `NH5-07` | `✅ done` | `76f233b` | retrieval candidate SQL | pre-rank filter |
| `NH5-08` T08-A | `✅ done` | `76f233b` | metadata merge/structure/facet | exact clean cutover |
| `NH5-08.d` T08-B | `❌ OOS handoff` | `-` | evidence process count=3 | `NH8-T03/NH8-03` |

### 12.2 关键指标演进

| 指标 | NH4 baseline | NH5 | Δ |
|------|--------------|-----|---|
| non-API six-tuple kinds | `0` | `3` + API = all 4 | `closed` |
| FilterMeta facet keys | `0` | `6` | `+6` |
| retrieval public channel axes | overloaded `channel` | semantic + vector | `split` |
| StructureDocument context authority | absent/model | S04 system overlay | `closed` |
| provider realestate newline failure | red | green | `-1 repository failure` |
| NH5 hard gates | `0` | `39 passed` | `+39` |

### 12.3 红灯 / successor-owned failures

| 项 | 证据 | 判断 |
|----|------|------|
| T08-B metadata acquire/decode/clean = 3 | `queries/metadata-lineage.json`; no xfail | `C handoff → NH8-T03` |
| index/reactivate namespace（4） | post-NH5 full suite same 422 | `C handoff → NH8` |
| rebuild structure profile（1） | current graph still reclean/structurize | `C handoff → NH8 exact-clean` |

### 12.4 文档状态

`draft → executing → executed（2026-08-30）`。
