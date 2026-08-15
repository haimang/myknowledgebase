# S07 — LS-RAG Constructor

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D5 LS-RAG 构建 / S07 LS-RAG Constructor`
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S07 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S07-v1.1`（v1.0 宪法 + **执行台账全面升格**；QNA 细节并入本文）
>
> **上游权威输入**：`D01–D04`、`S01–S06`、`S11–S13`；`qna-truth/S07.md v1.0`（**证据层 / 中间态 only**，非执行 SSOT）
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.1
>
> **事实证据**：`context/legacy-family/` 仅作 ReferenceAnchor（Constructor、MetaFuser、Recorder、RAG Dispatcher、Vectorizer、Contexter Traceback）；**禁止** `legacy-specs` / `legacy-python` 作为本域证据源
>
> **下游消费者**：`S08–S11`、`S12–S15`、跨系统拓扑 `17`、验收冻结 `18`、实现与 architecture tests

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S07.md` 仅保留 progressive 形成过程（`T-O-126..140` 冻结轨迹），**不得**被引用为第二执行真相；冲突时 **以本文为准**。禁止「细节在 QNA、Spec 只写原则」。实现 **无需** 打开 QNA 即可编码。

> **Owner-originated 产品模型（T-O-138）**：一次 **Execution = 一份 intake 文档管线**；construct 处理 **整包** Construction schema artifact（内可含多粒度 dual-channel 记录）；摘要按 **整包一次** 填充全部应有 summary；**整包二元成败**（无结构级中间成功）；失败仅 **S03 max-retries**，耗尽后显性 failed 并继续后续任务。

> **对 T-O-133/136 的 v1 收窄（T-O-138）**：取消 `original-only admitted` / `allow_original_only` 作为 full-valid；v1 **不**启用 process-local summary repair 成功路径；`summary_disposition` 仅失败取证，**不**驱动 CAS。旧 T-O 行文保留历史，**以本 Spec 与 T-O-138 为 v1 成功面权威**。

> **跨文档**：不新增 StateFamily；不复制 S03 Process 八态；不创建 Intake identity；不切 serving；不写 vector index。GenerationArtifact / Invocation / per-type current 与 S06 同构。ConstructionSchema 业务语义归 S07；物理 registry/TX 归 S12；对象 bytes 归 S13。S11 提供 summary/structured 路径；S07 **不**直连 adapter。

> **Legacy 边界（T-O-42 / T-O-131）**：不继承 SMCP wire、R2 key 成功语义、`smind_vec_process` 作 SSOT、blind INSERT、step-name meta-only、flat layered wire 兼容。

> **D05校准声明（T-O-202..210 / T-O-352）**：S07 服从 D05。Construct 内 Summarizer 绑定 **`promptC.<variant>.<version>` + content_hash**；**默认双通道根本**；默认粒度语义 **0/1/2** 且 **g=0 summary 必入向量候选**（g=0 original 必须装回在 construct，不进 required-set）；**仅 full_valid dual-channel 完备后** 才 `vectorize_construct`（ConstructToVectorizeGate）；失败 **仅** S03 max_retries（T-O-207）。

> **S08校准声明（2026-08-12）**：`S08-v1.0` 为向量写侧唯一执行 SSOT。S07 outbox `vectorize_construct` 消费方为 Process **`lsrag.vectorize`**（非 `vectorize_index`）；S08 强制 ContentFull 对账、整包 required-set 成败、original 装回 HARD；**不**在 S07 内 embed。Layer B facet 权威仍在 S04；S07 投影 + S08 抄写。publication 归 S09。
---

## 1. Domain 介绍

### 1.1 Domain 价值

S07 规定：在 **不改写** S06 original structure kernel 的前提下，如何把 exact S06 structure + projection 变成 **original/summary 双通道** 的可验证构造产物，并完成 meta 投影、`content_full` 配方与向 S08 的 outbox 交接——使检索侧能以 summary 索引、以 original 回溯，且实现者无需查阅 QNA。

S07 解决十个核心问题：

1. 构造产物相对 S06 projection 如何对齐（1:1 坐标，非二次重切分默认）；
2. 多粒度结构如何封装在 **同一整包 artifact** 内并整包计成败；
3. summary 如何整包生产与校验（非每结构单独 LLM 成败单元）；
4. original 保真与 summary 不得冒充 original；
5. filter/context 权威如何仍在 S04，S07 仅 derived 投影；
6. accepted construct 如何用 per-type current 表达（无 GenerationCommit 身份）；
7. `full_construct` / `metadata_refresh` 模式如何 typed 声明；
8. 与 S08 如何 artifact SSOT + content_full 配方 + outbox 交接；
9. 失败如何只走 S03 max-retries 并显性 failed 后续；
10. readiness、预算、错误轴、scatter、OOS 如何钉死。

### 1.2 在整体拓扑中的位置

```text
S03 Workflow / Execution / Process
  │ ProcessCommand: lsrag.construct
  │ mode + exact structure/projection generation refs + command_input_digest
  ▼
S06 current structure_document + retrieval_block_projection
  + S04 IntakeRevision + S05 clean artifact
  │
  ▼
S07 Constructor
  ├── ConstructionInputBinder (exact digests)
  ├── ConstructionSchemaResolver
  ├── DualChannelAligner (projection 1:1)
  ├── SummaryPlanner + Summarizer (whole-artifact plan / default document_single)
  ├── MetadataProjector (S04 authority → digest-locked projection)
  ├── ContentFullRecipe
  ├── WholeArtifactValidator (binary full-valid)
  ├── S13 promote + S12 multi-pointer CAS (TX-06 同构)
  └── Outbox: vectorize_construct intent
  │
  │ ProcessOutcome + construction proof refs
  ▼
S08 Embedding → S09 Index → S10 Retrieval/Traceback
```

### 1.3 Canonical contract chain

```text
Task / Execution (single document / content child)            [S01-S03]
  → accepted IntakeRevision + clean IntakeArtifact           [S04-S05]
  → lsrag.structurize → structure + projection current         [S06]
  → ProcessCommand: lsrag.construct                            [S03→S07]
       mode + exact structure/projection refs + schema/profile
  → whole-artifact dual-channel construction                   [S07]
       construction_document + dual_channel_projection + proof
  → full-valid → multi-pointer CAS + outbox                    [S12/S13]
  → ProcessOutcome                                             [S07→S03]
  → vectorize / index / retrieve                               [S08-S10]
```

### 1.4 工作平面

| 平面 | S07 v1 负责 | 状态/证据 | 明确不负责 |
|---|---|---|---|
| Binding | exact S06 structure/projection + clean/revision + ConstructionSchema/profile/prompt/model | ProcessCommand + `command_input_digest` | latest / 跨 generation 拼装 |
| Dual-channel product | projection-aligned units；Original + Summary 通道 | GenerationArtifact 成员 + digests | S06 tree 改写 |
| Summary production | 整包 plan + 摘要生成 + Invocation | plan digest + invocations | 结构级独立成功单元 |
| Metadata | S04 权威 → digest-locked 投影；content_full 配方 | projection bytes + digests | filter SSOT 篡夺 |
| Accept / handoff | per-type current CAS；outbox intent | pointers + outbox | vector write / serving |
| Runtime | S03 leaf；max-retries only | Process 八态 | S07 私有 job/retry 机 |

### 1.5 Single 与 scatter

- **single**：一个内容型 Execution 对一份文档运行一次整包 construct；
- **scatter**：每个内容型 **child Execution 独立** 整包 `lsrag.construct`（`T-O-140`）；root **不**跨 Item 合成大包；
- child 失败按 S02/S03 loss policy 汇总；S07 不静默吞 required failure。

### 1.6 Scope fence

**S07 负责：**

- `lsrag.construct` Process capability 业务 contract；
- ConstructionSchema 业务语义（物理 registry 归 S12）；
- construction_document / dual_channel_projection / validation proof 逻辑形状；
- 整包 dual-channel 生产、校验、accept；
- meta 投影与 content_full 确定性配方；
- `full_construct` / `metadata_refresh` 模式语义；
- 向 S08 的 outbox intent 载荷形状（exact generation refs）；
- construct typed 错误轴与 readiness 业务条件。

**S07 不负责：**

| 排除项 | 归属 |
|---|---|
| structure tree / structure schema kernel | S06 |
| Task/Execution/Process 状态机与 max-retries 引擎 | S02/S03 |
| Intake identity / filter 权威源 | S04 |
| embedding / vector index / serving publication | S08–S09 |
| traceback 算法与结果契约 | S10 |
| model/provider runtime | S11 |
| DDL / TX / outbox 投递环物理 | S12 |
| object path / GC 数值 | S13 |
| prompt/model 物理 registry 表 | S14 |
| metric 告警 runbook | S15 |
| 公网 construct API / 用户 generation 精修 | **OOS**（`T-O-93/140`） |

### 1.7 Domain 完成定义

1. §2 Truth 与 §4 E 包可映射到代码与测试；
2. bootstrap ConstructionSchema 在 readiness 前注册；
3. 整包 dual-channel full-valid → multi-pointer CAS + outbox；
4. 失败不 CAS；S03 retry 同 digest；max-retries → 显性 failed；
5. S08 仅凭 exact construct generation refs 可枚举通道并对账 content_full；
6. 零 legacy Constructor runtime dependency；
7. 实现 **无需** 打开 QNA；
8. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O · S07 段 · 执行摘要）

| Truth-ID | 摘要 | 本域强制 |
|---|---|---|
| `T-O-126` | S07 = Constructor 域；不 structurize / 不 embed / 不 serving | scope fence |
| `T-O-127` | exact S06 current structure+projection+schema；禁 latest/跨代拼装 | input freeze |
| `T-O-128` | dual-channel 共享 generation-scoped 坐标；summary 可 traceback original | 禁第二坐标系 |
| `T-O-129` | original 仅 verified clean/structure 切片；禁模型写 original | kernel |
| `T-O-130` | `lsrag.construct` 叶；无私有 retry；success ≠ Task/serving | S03 only |
| `T-O-131` | legacy-family only 证据；per-type current；无 GenerationCommit 身份 | greenfield |
| `T-O-132` | Projection-aligned dual-channel units；1:1 projection；Construction artifact(s) | 禁 flat wire |
| `T-O-133` | governed summary；禁 silent coerce（**成功面被 T-O-138 收窄**） | 见 T-O-138 |
| `T-O-134` | S04 filter 权威；per-type current；typed rebuild；S08 绑新 generation | meta/accept |
| `T-O-135` | construction_document + dual_channel_projection + proof；ConstructionSchema | multi-pointer CAS |
| `T-O-136` | plan-first；disposition 闭集（**成功面被 T-O-138 收窄**） | 见 T-O-138 |
| `T-O-137` | content_full 配方；artifact SSOT；outbox；full_construct/metadata_refresh | handoff |
| `T-O-138` | 单文档 Execution；整包二元成败；整包 summary；S03 retry；显性失败后续；收窄 133/136 | **v1 成败权威** |
| `T-O-139` | Typed Command/Outcome；command_input_digest；full_valid only | wire contract |
| `T-O-140` | readiness；budget fail-loud；typed errors；per-child scatter；OOS | ops fence |

### 2.2 域内 Truth 编号（S07-T）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S07-T001` | 唯一 Process capability key：`lsrag.construct`（versioned manifest）。 | `T-O-130/139` | 无第二 construct job 状态机 |
| `S07-T002` | 一次内容型 Execution 对应一份 intake 文档整包 construct。 | `T-O-138` | 非 N 次结构级 Process |
| `S07-T003` | 输入必须 exact：current structure_document + 同 generation projection/proof + revision/clean + ConstructionSchema ref。 | `T-O-127` | 禁 latest |
| `S07-T004` | ProcessCommand materialize 后锁定 `command_input_digest`；retry 同 digest。 | `T-O-139` | 不可变 binding |
| `S07-T005` | mode ∈ {`full_construct`, `metadata_refresh`}（扩展须 schema/version）。 | `T-O-137/139` | 禁 step-name |
| `S07-T006` | `metadata_refresh`：structure generation ref 不变；可 `reuse_summaries` + exact source construction generation；仍须重算 meta 投影与 content_full；新 construct generation + CAS。 | `T-O-134/137` | reuse 后仍须整包 dual-channel 完备 |
| `S07-T007` | 构造单元与 S06 projection **1:1 对齐**（或 Spec 声明的 deterministic 映射）；不反向改 structure tree。 | `T-O-132` | 禁二次重切默认为 v1 |
| `S07-T008` | 多粒度/多结构记录封装在 **同一整包** Construction 契约内。 | `T-O-138` | 内部数据 ≠ 独立成败 |
| `S07-T009` | 每单元：generation-scoped coordinate + OriginalChannel + SummaryChannel 槽位。 | `T-O-128/132` | 共享坐标 |
| `S07-T010` | Original payload 仅 verified clean/structure 切片 + digest 可复验。 | `T-O-129` | 禁模型写 original |
| `S07-T011` | Summary 整包生产（默认 document_single plan 模式）；非“每结构单独 LLM 成功单元”。 | `T-O-136/138` | plan digest 可复验 |
| `S07-T012` | **唯一成功态** = 整包 dual-channel full-valid + multi-pointer CAS；禁止 partial / original-only 成功。 | `T-O-138` | 收窄 133/136 |
| `S07-T013` | 失败：不 CAS current；无 process-local summary repair；仅 S03 max-retries。 | `T-O-130/138` | |
| `S07-T014` | max-retries 耗尽 → Process 显性 failed + 可审计记录；后续任务按 loss policy 继续。 | `T-O-138` | 不抹账、不半包下传 |
| `S07-T015` | v1 artifact_type 最小集：`construction_document`、`dual_channel_projection`、validation/report 面（独立 type 或并入 document 强制子面）。 | `T-O-135` | 同 UoW multi-pointer CAS |
| `S07-T016` | S07 拥有 ConstructionSchema（key/version/digest）；独立于 StructureSchema。 | `T-O-135` | readiness 前注册 |
| `S07-T017` | Filter/canonical metadata 权威在 S04；S07 只读投影 digest 锁定。 | `T-O-134` | 模型不得发明 filter |
| `S07-T018` | 确定性 `content_full` 配方（body + S04 投影 meta 闭集头 + 可选 unit title）；S08 可重算对账。 | `T-O-137` | 非 identity |
| `S07-T019` | SSOT = artifacts + current；交接 = S12 outbox intent（exact construct generation refs，不塞全文）。 | `T-O-137` | 禁 pending 表 SSOT |
| `S07-T020` | Typed Command/Outcome；Outcome 无正文/path；`disposition=full_valid` only on success。 | `T-O-139` | |
| `S07-T021` | ConstructionSchema readiness + structure schema range 交集 + S12/S13 ready。 | `T-O-140` | readiness≠liveness |
| `S07-T022` | 预算超限 fail-loud；typed `CONSTRUCT_*` 错误轴。 | `T-O-140` | 禁截断冒充成功 |
| `S07-T023` | scatter = per content child 整包 construct；无跨 Item 大包。 | `T-O-140` | |
| `S07-T024` | OOS：无公网 construct CRUD、无用户 generation 精修、无 S07 内 embed/index/serving。 | `T-O-140` | |
| `S07-T025` | 不引入 GenerationCommit 业务身份；accepted = per-type full-valid current。 | `T-O-96/131` | |
| `S07-T026` | S08 必须绑定 exact/new construct generation；禁混代。 | `T-O-134` | |
| `S07-T027` | 幂等：同 `(execution, capability, command_input_digest)` → 同一 logical current 或 conflict。 | `T-O-139` | |
| `S07-T028` | 有 non-empty original 的结构位必须有 grounded summary 才算整包 dual-channel 完备。 | `T-O-138` | 无 original 位不计入应摘要集合 |
| `S07-T029` | grounding 最小：summary `grounds_coordinate` = 本单元 generation-scoped coordinate。 | `T-O-136`（取证） | 失败 report 可用 |
| `S07-T030` | 零结构/空 projection 整包 → fail（不得成功空构造）。 | `T-O-138` | |
| `S07-T031` | summary_disposition 闭集（取证）：`present_grounded` / `omitted_by_profile` / `empty_model_output` / `failed_extension` / `not_applicable`；v1 **不**用其驱动 CAS 成功。 | `T-O-136`+`T-O-138` | |
| `S07-T032` | plan-first：先确定性 summary_plan（units 有序 + batch 分组 + plan digest）再模型调用。 | `T-O-136` | 禁无 plan 盲调 |
| `S07-T033` | profile 可声明 plan 模式：`document_single`（v1 默认）/ `per_unit` / `sized_batches`；模式属 profile，非第二 Truth。 | `T-O-136` | |
| `S07-T034` | 每 model call 必须记 GenerationInvocation（binding/token/因果）。 | `T-O-136`、S11 | 经 S11 facade |
| `S07-T035` | Prompt/model 缺失 = fail-fast（`CONSTRUCT_BINDING_*` / schema）。 | `T-O-133` | 禁静默换 key |

### 2.3 继承上游（不重开）

- S03：`lsrag.construct` leaf；claim/fence/max-retries；Outcome 与 status 分账。  
- S06：generation-scoped coords；structure 无权威 summary；consumer 加载 exact schema。  
- S04：filter/context 权威。  
- S11：structured/text generate；调用成功 ≠ construct 成功。  
- S12：TX-06 generation accept；bytes-first；outbox。  
- S13：logical handle；`generation_artifact` purpose；禁 path 入契约。  
- D02：不新增 StateFamily。  
- D04：generation/registry 物理表以 D04 为准；本文钉写语义与执行步骤。

---

## 3. 总体方案陈述

1. **整包处理**：单文档 Execution → 一次 Process → 一套 Construction 成员 CAS。  
2. **双通道对齐 S06 projection**：1:1 坐标；original 保真；summary 整包填充。  
3. **成功唯一**：full-valid 整包 dual-channel 完备才 CAS；否则失败。  
4. **恢复唯一**：S03 max-retries；无 S07 内摘要软着陆 / process-local repair。  
5. **Schema 分账**：ConstructionSchema ≠ StructureSchema；exact digest 绑定。  
6. **元数据**：S04 权威；S07 投影 + content_full 配方。  
7. **交接**：artifact SSOT + outbox intent；S08 可对账重算。  
8. **模式**：`full_construct` 与 `metadata_refresh` typed 化。  
9. **运维**：readiness、预算、typed 错误、per-child scatter、OOS。  
10. **QNA 零依赖**：执行细节全部在本文 §4 E 包。

---

## 4. 具体执行方案清单

### 4.1 `S07-E01` — 目录、capability 与 architecture 围栏

**真相**：S07-T001/T024；T-O-126/130

**执行台账 — 路径与职责**：

| 路径（逻辑） | 职责 |
|---|---|
| `src/services/lsrag_construct/` 或等价 domain service | Command binder、aligner、planner、validator、accept 编排 |
| `src/contracts/lsrag/construct/` | ProcessCommand/Outcome、ConstructionSchema shapes、error codes |
| `src/contracts/lsrag/construct/schemas/` | bootstrap ConstructionSchema definition digests |
| 经 `runtime.inference`（S11） | summary structured/text generate；**禁** services→llm_adapters |
| 经 S12 ports | generation artifacts / pointers / outbox / UoW |
| 经 S13 ObjectStorePort | promote construction bytes |

| 规则 | 验收 |
|---|---|
| 无 S07 私有 job/status 表 | architecture / schema test |
| 无 public construct HTTP CRUD | surface test |
| 禁 import legacy constructor/SMCP | 扫描零命中 |
| 禁 domain 内 pathlib 写 object_root | architecture test |

**小结**：construct 是 leaf service，不是平台与私有调度器。

---

### 4.2 `S07-E02` — ProcessCommand 字段合同与 input freeze

**真相**：S07-T003..T006、T027、T035；T-O-127/139

**执行台账 — ProcessCommand 最小必选字段**：

| 字段 | 约束 |
|---|---|
| `mode` | 闭集：`full_construct` \| `metadata_refresh` |
| `structure_generation_ref` + `structure_generation_digest` | 必须指向该 Execution 的 current structure（materialize 时校验） |
| `projection_generation_ref` + `projection_generation_digest` | 必须与 structure **同 generation**；可验证 |
| `structure_schema_ref` | key/version/digest exact |
| `intake_revision_ref` | S04 权威 |
| `clean_artifact_ref` + `clean_artifact_digest` | original 复验 |
| `construction_schema_ref` | key/version/digest exact |
| `construct_profile_ref` | profile（含 plan 模式、预算引用、是否允许某 disposition 仅取证） |
| `summary_prompt_ref` | **`PromptRef` → `promptC.*` + content_hash**（D05 T-O-208）；full_construct 必填；`metadata_refresh`+`reuse_summaries=true` 可 **显式 null** |
| `summary_model_ref` / binding | 经 S11 binding 解析 |
| `reuse_summaries` | bool；仅 `metadata_refresh` 有意义；`full_construct` 必须 false 或忽略为 false |
| `source_construction_generation_ref?` | `reuse_summaries=true` 时必填；exact 上一代 construct |
| `command_input_digest` | materialize 后计算并 **持久冻结**；canonical 序列化上述字段 |

**冻结规则**：

1. S03 materialize 后 `command_input_digest` **不可变**；  
2. retry / recovery **必须** 重放同 digest；  
3. 禁止运行时 `latest` structure/projection/clean/schema；  
4. 跨 generation 拼装 structure 与 projection → `CONSTRUCT_BINDING_CROSS_GENERATION`。

**小结**：无 catchall payload；无 step-name 模式。

---

### 4.3 `S07-E03` — ProcessOutcome 字段合同与幂等

**真相**：S07-T012/T020/T027；T-O-138/139

**成功路径 Outcome（唯一）**：

| 字段 | 约束 |
|---|---|
| `disposition` | **必须** `full_valid`（无 original-only / partial） |
| `construction_document_ref` + digest | current 成员 |
| `dual_channel_projection_ref` + digest | current 成员 |
| `validation_report_ref` + digest | 独立 type 或 document 强制 proof 子面；成功时必有 |
| `summary_plan_digest` | 与 plan 物化一致 |
| `invocation_set_digest` 或 counts | 可对账 |
| `dual_channel_completeness` | 结构位/通道统计（**不是**中间成功态） |
| `outbox_intent_ref?` | 可观测已 enqueue；**intent 存在 ≠ 二次定义 success** |
| `command_input_digest` | 回显 |

**禁止出现在 Outcome**：summary/original 全文、path、R2 key、可写回 S04/S06 的补丁。

**失败路径 Outcome**：

| 字段 | 约束 |
|---|---|
| `disposition` | 非 `full_valid`（或不设） |
| `error_code` | `CONSTRUCT_*` 轴 |
| `error_details?` | 有界安全摘要 |
| `invalid_artifact_refs?` | 若已落盘历史 |
| **不得** CAS current | 强制 |

**幂等**：

```text
key = (team_uuid, execution_uuid, capability=lsrag.construct, command_input_digest)
at-least-once → 同一 logical current 或显式 conflict
禁止双 current / last-write-wins
```

**小结**：Outcome 是 proof 投影，不是 payload 总线。

---

### 4.4 `S07-E04` — ConstructionSchema 与 artifact 成员

**真相**：S07-T015/T016/T021；T-O-135

**执行台账 — ConstructionSchema**：

| 项 | 规范 |
|---|---|
| identity | `schema_key` + `version` + `digest` |
| 与 StructureSchema | **分账**；禁止把 summary 写回 S06 schema |
| bootstrap 例 | `mkb.construction_document@1`（拼写可微调；**readiness 前必须注册**） |
| 同 version 同 digest | 幂等 bootstrap |
| 同 version 异 digest | readiness=false |
| 内容 | strict shape + dual-channel invariants + content_full 配方 version + 语义 validator 合同 |

**artifact_type 最小集（accept 时 multi-pointer CAS）**：

| artifact_type | 内容职责 |
|---|---|
| `construction_document` | envelope：S06 refs、schema digests、有序单元清单、metadata 投影 digest、summary plan 摘要、alignment proof |
| `dual_channel_projection` | 按 coordinate 的 Original/Summary 通道记录（payload handle+digest、channel、content_full digest、配方 digest、grounds_coordinate） |
| `construction_validation_report`（或并入 document 强制 proof 子面） | full-valid 证明或失败 findings |

各成员独立 digest；accept 时 **同 UoW** 全部 S07 current pointers CAS（对齐 S12 TX-06）。

**禁止**：

- 通道队列表（`smind_vec_process` 类）作 construction SSOT；  
- 在 S06 projection 原地扩写 summary；  
- flat 单 blob 作为唯一不可枚举通道面。

**小结**：多成员 immutable + multi-pointer；S08 可枚举通道。

---

### 4.5 `S07-E05` — Dual-channel 对齐与 original 保真

**真相**：S07-T007..T010、T028..T030；T-O-128/129/132

**执行台账 — 对齐**：

1. 加载 exact structure_document + retrieval_block_projection（同 generation）；  
2. 对每个 projection block（或 Spec 声明的 deterministic map）创建 **ConstructionUnit**；  
3. unit 绑定 **generation-scoped coordinate**（继承 S06；禁止裸 `file_uuid+block_id+granularity` 跨代 identity）；  
4. **OriginalChannel**：payload = verified clean/structure 切片；digest 可复验；  
5. **SummaryChannel**：槽位预留；正文仅来自 summary 生产（E06），不得填 original。

**kernel 失败（不可 agent 修）**：

| 条件 | 错误 |
|---|---|
| 对齐失败 / 坐标缺失 | `CONSTRUCT_KERNEL_ALIGNMENT_*` |
| original digest 不匹配 | `CONSTRUCT_KERNEL_ORIGINAL_*` |
| 模型改写 original / summary 冒充 original | `CONSTRUCT_KERNEL_ORIGINAL_*` |
| 零 unit / 空 projection | `CONSTRUCT_KERNEL_EMPTY` |
| 反向改 structure tree | 禁止；检测则 kernel fail |

**小结**：坐标权威在 S06；S07 不另造坐标系。

---

### 4.6 `S07-E06` — Summary plan、整包生产与 disposition 取证

**真相**：S07-T011/T028/T029/T031..T035；T-O-136/138

**执行台账 — plan-first**：

```text
1. materialize summary_plan:
     ordered units + batch grouping + plan_mode(from profile)
     plan_digest = H(canonical plan)
2. execute plan (default plan_mode=document_single):
     whole-artifact model call(s) via S11 structured_generate / text_generate
     each call → GenerationInvocation (S11 + generation ledger)
3. map model outputs → SummaryChannel per unit
4. record summary_disposition per unit (forensics only)
5. NO process-local repair loop (T-O-138)
```

**plan_mode（profile，非第二 Truth）**：

| mode | 含义 |
|---|---|
| `document_single` | **v1 默认**：整文一次（或整包一次）填全部应有 summary |
| `per_unit` | 每 unit 一次调用（仍属整包 plan；成败仍整包） |
| `sized_batches` | 有界 batch；仍属整包 plan |

**summary_disposition 闭集（取证，不驱动 CAS）**：

| 值 | 含义 |
|---|---|
| `present_grounded` | 非空 summary 且 `grounds_coordinate` = 本 unit coordinate |
| `omitted_by_profile` | profile 声明跳过（v1 默认 profile **不应**对 non-empty original 使用） |
| `empty_model_output` | 模型空输出 |
| `failed_extension` | 摘要质量/schema 失败 |
| `not_applicable` | 无 original / 不适用 |

**v1 整包 dual-channel 完备（成功前提）**：

- 对每个 **non-empty original** unit：必须有 `present_grounded` summary；  
- 任一应有 summary 缺失/空/未 grounding → **整包失败**，不 CAS；  
- 禁止 partial structure success；  
- 禁止 original-only admitted 成功。

**Prompt/model 缺失**：fail-fast，无静默换 key。

**小结**：整包一次生产；包内多结构是数据，不是 N 次独立成败。

---

### 4.7 `S07-E07` — Metadata 投影与 content_full 配方

**真相**：S07-T017/T018；T-O-134/137

**执行台账 — MetadataProjector**：

| 规则 | 规范 |
|---|---|
| filter/canonical 权威 | **仅** S04 IntakeRevision（及登记 refs） |
| S07 动作 | 只读投影 → digest 锁定的 metadata projection bytes |
| 模型 | **禁止**发明/覆盖权威 filter 键 |
| scatter/atomic | child filter 权威来自 **该 child** Item/Revision；禁止 parent∪child 机会主义 merge 作 SSOT |
| context 叙事字段 | 可投影为 content_full 头；与 filter 分账（借鉴 MetaFuser 分账语义，删除 wire） |

**content_full 确定性配方（v1）**：

```text
content_full = recipe_vN(
  optional_header: closed_set(S04 projection meta + optional unit title),
  body: channel_body  # original body OR summary body by channel
)
recipe_version ∈ ConstructionSchema / construct_profile
content_full_digest = H(content_full bytes)
```

| 义务 | 说明 |
|---|---|
| 可物化 | S07 可写 digest/bytes（object 或 inline 有界字段） |
| S08 可重算 | 同配方 + 同输入 → 同 digest；对账失败 → vectorize fail-loud |
| 非 identity | content_full **不是** unit identity；identity = generation-scoped coordinate + channel |

**小结**：filter 权威在 S04；content_full 是 derived embed 文本。

---

### 4.8 `S07-E08` — 整包校验与 binary accept 主路径

**真相**：S07-T012..T014；T-O-138

**执行台账 — full_construct 逐步**：

| 步 | 动作 | 失败 |
|---|---|---|
| 1 | claim Process + fence（S03/S12） | claim 失败 |
| 2 | load Command；校验 `command_input_digest` | BINDING |
| 3 | load exact structure/projection/clean/revision；同 generation | BINDING |
| 4 | resolve ConstructionSchema + profile | SCHEMA |
| 5 | DualChannelAligner + original digests（E05） | KERNEL |
| 6 | budget precheck units/payload（E11） | BUDGET |
| 7 | MetadataProjector（E07） | BINDING / KERNEL |
| 8 | 加载 **promptC**（hash 校验）→ Summary plan + production（E06）via S11 | EXTENSION / DEPENDENCY / KERNEL / PROMPT |
| 9 | ContentFullRecipe 全 unit×channel（E07） | KERNEL / BUDGET |
| 10 | WholeArtifactValidator：binding + alignment + dual-channel 完备 | 非整包完备 → fail |
| 11 | S13 promote construction members bytes | DEPENDENCY / S13 errors |
| 12 | **仅当 full-valid 且 dual-channel 完备且 g=0 在场**（D05 T-O-205/206）：S12 UoW TX-06 multi-pointer CAS + outbox `vectorize_construct` | CAS conflict fail-loud；缺 g=0 / 不完备 → 不 enqueue |
| 13 | ProcessOutcome succeeded / failed | 见 E03 |
| 14 | **禁止** 在失败路径 CAS current | HARD |

**失败恢复**：

```text
fail → no CAS current
     → typed Outcome failed
     → S03 max-retries (same command_input_digest)
     → exhausted → Process failed (durable)
     → Workflow 按 loss policy 继续后续步骤（不卡死抹账）
```

**v1 禁止**：S07 进程内「再修一轮摘要」成功路径；original-only CAS。

**小结**：要么整包 full-valid 并 CAS，要么失败。

---

### 4.9 `S07-E09` — `metadata_refresh` 模式

**真相**：S07-T005/T006；T-O-134/137

**执行台账**：

| 条件 | 规范 |
|---|---|
| mode | `metadata_refresh` |
| structure generation ref | **不变**（与 Command 声明一致） |
| re-structurize | **不**执行（S06 不重跑） |
| `reuse_summaries=true` | 必须带 exact `source_construction_generation_ref`；复制 summary 通道（digest 锁定） |
| `reuse_summaries=false` | 必须提供 summary prompt/model；重新整包 summary（仍整包成败） |
| meta 投影 | **必须**重算（S04 当前权威投影） |
| content_full | **必须**按配方重算 |
| 成功 | 新 construct generation + multi-pointer CAS + 新 outbox；仍须整包 dual-channel 完备 |
| 失败 | 不 CAS；同 E08 恢复 |

**非法**：

- step-name 子串匹配跳过 structurizer/constructor；  
- 盲插 pending 行当成功；  
- reuse 时缺 source generation。

**小结**：typed meta-only；结构可复用；construct 世代仍可审计替换 current。

---

### 4.10 `S07-E10` — S08 handoff 与 outbox intent

**真相**：S07-T019/T026；T-O-137

**执行台账 — outbox kind（逻辑名，D04/S12 钉物理）**：

| 字段 | 约束 |
|---|---|
| `kind` | `vectorize_construct`（名可微调；语义不变） |
| `payload` | exact construct generation refs + digests；construction_schema digests；team/execution；**不塞全文** |
| 同 TX | 与 multi-pointer CAS 同 UoW（TX-07/TX-06 接合） |
| 消费 | S08 绑定 **新** construct generation；禁混代 |
| 禁止 | 以 pending 队列表行存在定义 construct 成功 |

**S08 义务（消费合同，本文强制）**：

1. 按 exact generation 枚举 dual-channel 单元；  
2. 按同 content_full 配方重算并对账 digest；  
3. 调用 S11 embed；遵守 S11 Layer A/B 与 vectorize 幂等（S11-E09）；  
4. 不得把「向量已写」反推 S07/Task success。

**小结**：artifact + current 是 SSOT；outbox 只是 wake。

---

### 4.11 `S07-E11` — Readiness、预算、错误轴、scatter、OOS

**真相**：S07-T021..T024；T-O-140

**Readiness=false 当（逻辑或）**：

1. v1 ConstructionSchema 未注册或 digest 漂移；  
2. S07 声明支持的 S06 structure schema range 与已注册 structure schema **无交集**；  
3. S12/S13 readiness 未通过；  
4.（可选联合）S11 默认 local binding 不可用且 construct profile 需要 summary。

Readiness ≠ liveness；禁止 silent 修 schema。

**容量预算（配置化；下列为安全默认量级，可调高，不可默认无界）**：

| 预算键 | 默认量级 | 超限 |
|---|---|---|
| `construct.max_units_per_artifact` | 10_000 | `CONSTRUCT_BUDGET_UNITS` |
| `construct.max_channel_payload_bytes` | 8 MiB / unit channel | `CONSTRUCT_BUDGET_PAYLOAD` |
| `construct.max_content_full_bytes` | 8 MiB | `CONSTRUCT_BUDGET_CONTENT_FULL` |
| `construct.max_plan_batches` | 256 | `CONSTRUCT_BUDGET_PLAN` |
| `construct.max_summary_output_chars` | profile 声明 | `CONSTRUCT_BUDGET_*` |

超限 → **fail-loud**；禁止截断冒充成功。

**Typed 错误轴（闭集骨架，可增不可静默字符串化）**：

| 前缀 | 条件 |
|---|---|
| `CONSTRUCT_BINDING_*` | 缺 ref、digest 不匹配、跨 generation、缺 prompt/model |
| `CONSTRUCT_SCHEMA_*` | 未知 version、digest drift、consumer range |
| `CONSTRUCT_KERNEL_*` | 对齐失败、original 不匹配、零 unit、坐标非法 |
| `CONSTRUCT_EXTENSION_*` | summary 质量/disposition 取证失败导致整包不完备 |
| `CONSTRUCT_BUDGET_*` | 超预算 |
| `CONSTRUCT_MODE_*` | 非法 mode、refresh 缺 source、reuse 冲突 |
| `CONSTRUCT_DEPENDENCY_*` | S11/S12/S13 不可用 |

**Scatter**：每个内容型 child Execution **独立**整包 construct；root 不跨 Item 合成。  
**OOS**：无公网 construct CRUD/浏览器；无用户 generation 精修 API；无 S07 内 embed/index/serving。  
**可观测钩子（低基数，细节 S15）**：mode、成败、channel 计数、budget 拒绝；无 repair-success 计数（v1 无该路径）。

**小结**：leaf-worker 运维合同，非平台。

---

### 4.12 `S07-E12` — 与 S03/S06/S08/S11/S12/S13 交接

| 对方 | 合同 |
|---|---|
| S03 | 只消费 Outcome；max-retries 属 S03；lease 须覆盖或 heartbeat；success ≠ Task success |
| S06 | exact structure+projection+coords；禁写回 structure kernel |
| S04 | filter 权威；S07 只投影 |
| S11 | 只经 runtime.inference；invocation 账；transport/闸错误映射为 DEPENDENCY/EXTENSION |
| S12 | TX-06 multi-pointer；outbox；registry bootstrap |
| S13 | promote + `generation_artifact` purpose；handle only |
| S08 | exact generation；content_full 重算；禁混代 |
| S10 | summary→original traceback；generation-scoped coords |
| S14 | prompt/model registry 物理；binding refs 逻辑 |
| S15 | 指标与 retention 数值 |

---

## 5. 事实反例、风险与实施切片

### 5.1 Legacy 反例 → MKB 禁令

| Legacy 事实 | MKB 禁令 |
|---|---|
| success = R2 key / callback | proof + digests + current CAS |
| `smind_vec_process` 盲插 SSOT | artifact + outbox |
| 空 summary 仍成功 | 整包 dual-channel 完备才成功 |
| step-name skip structurizer | typed mode + exact generation ref |
| silent context_meta 回填 | 禁 coerce |
| flat layered 双包 schema 复制 | ConstructionSchema 独立 |
| 每块登记当独立成功语义 | 整包成败 |
| QNA 当实现说明书 | 禁止；以本文 E 包为准 |

### 5.2 保留的生产语义（非 wire）

- original/summary **双通道**；  
- **共享坐标** + summary→original traceback；  
- **整文一次** 填全部应有 summary；  
- context vs filter **分账**（filter 升为 S04 权威）；  
- meta-only 刷新语义 → `metadata_refresh`；  
- `content_full` 头增强。

### 5.3 风险台账

| 风险 | 缓解 |
|---|---|
| 整包重试 token 成本 | Owner 接受；调 prompt/model/max-retries |
| multi-pointer CAS 复杂度 | S12 TX-06 同构 |
| reuse_summaries 陈旧 | report 标记来源；仍须完备 dual-channel |
| ConstructionSchema 未 bootstrap | readiness false |
| S08 混代 | S07-T026 + outbox exact refs |
| S11 背压/429 | 映射 DEPENDENCY；S03 retry；不换模型 |

### 5.4 实施切片（非排期）

1. ConstructionSchema bootstrap + readiness；  
2. contracts Command/Outcome + error codes；  
3. InputBinder + DualChannelAligner + validator；  
4. Summary plan + S11 Invocation；  
5. MetadataProjector + ContentFullRecipe；  
6. S13 promote + multi-pointer CAS + outbox；  
7. metadata_refresh 路径；  
8. golden dual-channel fixtures + 失败/重试验收；  
9. architecture：无 QNA 依赖审查（文档自包含）。

---

## 6. 强制验收矩阵

| ID | HARD 场景 | 期望 |
|---|---|---|
| `S07-A01` | 缺 structure/projection 或 digest 不匹配 | fail-closed；无 CAS |
| `S07-A02` | 跨 generation 拼装 structure 与 projection | `CONSTRUCT_BINDING_CROSS_GENERATION` |
| `S07-A03` | 模型改写 original | kernel fail |
| `S07-A04` | 应有 summary 缺失/空 → 整包失败 | 无 CAS；非 partial success |
| `S07-A05` | full-valid 成功 | 成员 current 一致；outbox 可观测 |
| `S07-A06` | 同 command_input_digest 重试 | 同 digest；幂等或 conflict |
| `S07-A07` | max-retries 耗尽 | Process failed；无 usable current；历史可查 |
| `S07-A08` | metadata_refresh + reuse_summaries | 新 generation；meta/content_full 更新；dual-channel 仍完备 |
| `S07-A09` | filter 模型发明键 | reject |
| `S07-A10` | content_full 重算 digest 不匹配 | S08 对账失败路径 |
| `S07-A11` | 无 ConstructionSchema 注册启动 | readiness false |
| `S07-A12` | 超预算 | `CONSTRUCT_BUDGET_*`；无截断成功 |
| `S07-A13` | scatter child 独立 construct | 无跨 Item 大包 |
| `S07-A14` | Outcome 无 path/R2/正文 | contract test |
| `S07-A15` | 零 legacy constructor/SMCP 依赖 | 扫描零命中 |
| `S07-A16` | S07 success 不切 serving/index | serving 仍旧 |
| `S07-A17` | 无公网 construct API | surface 测试 |
| `S07-A18` | pending 队列表不作为 SSOT | 架构测试 |
| `S07-A19` | original-only 尝试 CAS | 禁止 |
| `S07-A20` | process-local summary repair 成功路径 | v1 不存在 |
| `S07-A21` | 无 plan 盲调模型 | 禁止 |
| `S07-A22` | 实现可不打开 QNA | 文档自包含审查 |

---

## 7. Reference-anchor 台账

| Anchor | 路径/符号 | 用途 | 裁决 |
|---|---|---|---|
| Constructor flow | `smind-skill-rag-constructor/flows/constructor.ts` | 管线分路 | **保留** 摘要+meta+输出分账；**删除** callback 成功 |
| Summarizer | `services/summarizer.ts` | 整文 summary | **保留** 整包一次；**删除** silent 回填 |
| MetaFuser | `services/meta_fuser.ts` | filter/context 分账 | **升级** 为 S04 权威 + 投影 |
| Recorder | `services/recorder.ts` | 双通道扇出 / content_full | **保留** 语义；**删除** 盲插 SSOT |
| Schemas | `core/schemas_common.ts` | dual fields / channel enum | **升级** generation-scoped；**删除** flat wire |
| Dispatcher meta-only | `smind-rag-dispatcher/.../orchestrator.ts` | structure 可复用 | **升级** typed mode |
| Vectorizer | 读 pending 行 | 交接形状 | **升级** outbox + artifact |
| Contexter traceback | summary→original | 共享坐标 | **保留** 语义 |
| Console `smind_vec_process` | DDL | 通道列 | **删除** 作 construction SSOT |

**QNA**：`qna-truth/S07.md` = 形成过程证据；**非**执行 SSOT。

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO / execution-complete for v1.1`**：S07 作为 **唯一执行真相** 已含 E01–E12 台账；实现不得外挂 QNA。

### 8.2 强制结论

1. domain-truth only；  
2. 单文档 Execution；整包 artifact；一次 summary 全部应有粒度；  
3. 唯一成功 = 整包 dual-channel full-valid + per-type current CAS；  
4. 失败 = 不 CAS + 仅 S03 retry + 耗尽显性 failed + 后续任务可继续；  
5. original 保真；S04 filter 权威；content_full 配方；outbox 交接；  
6. 无 GenerationCommit 身份；无公网 construct；无 S07 内向量；  
7. legacy 仅 ReferenceAnchor。

### 8.3 下游约束

| 下游 | 承接 |
|---|---|
| `S08` | 读 exact construct generation；content_full 可重算；禁混代 |
| `S09` | publication 仍独立 proof |
| `S10` | summary 命中 → original traceback；generation-scoped 坐标 |
| `S11/S14` | summary model/prompt binding + Invocation |
| `S12` | construction/schema DDL；multi-pointer CAS；outbox |
| `S13` | generation_artifact purpose；handles |
| `S03` | mode 路由；max-retries；Outcome 校验 |

### 8.4 一句话

S07-v1.1 把 Constructor 从「原则」升格为 **可编码执行台账**，并独占执行真相层。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| `S07-v1.0` | `2026-08-11` | `accepted` | 冻结 QNA `T-O-126..140`；整包 dual-channel Constructor；Round 4 waived |
| `S07-v1.1` | `2026-08-12` | `accepted` | **执行 SSOT 强制**；QNA 细节并入 E01–E12；禁止执行依赖 QNA |
| `S07-v1.1-cal-d05` | `2026-08-12` | `accepted / D05-calibrated` | 接收 D05-v1.0：`promptC`、双通道根本、g=0 必向量、ConstructToVectorizeGate（T-O-203..206/208） |