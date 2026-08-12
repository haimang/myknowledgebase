# S07 — LS-RAG Constructor

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D5 LS-RAG 构建 / S07 LS-RAG Constructor`
>
> **日期**：`2026-08-11`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted`（S07 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S07-v1.0`
>
> **上游权威输入**：`D01-v1.4`、`D02-v1.0`、`S01-v1.5`、`S02-v1.3`、`S03-v1.3`、`S04-v1.2`、`S05-v1.1`、`S06-v1.0`、`S12-v1.0`、`S13-v1.0`；冻结的 `qna-truth/S07.md v1.0`（Q1–Q9 / `T-O-126..140`）
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **事实证据**：`context/legacy-family/` 仅作 production-pitfall / behavior-archeology / design-counterexample `ReferenceAnchor`（Constructor、MetaFuser、Recorder、RAG Dispatcher、Vectorizer、Contexter Traceback）；**禁止** `legacy-specs` / `legacy-python` 作为本域证据源
>
> **下游消费者**：`S08–S11`、`S12–S15`、跨系统拓扑 `17`、验收冻结 `18`

> **Owner-originated 产品模型（2026-08-11 / T-O-138）**：一次 **Execution = 一份 intake 文档管线**；construct 处理 **整包** Construction schema artifact（内可含多粒度 dual-channel 记录）；摘要按 **整包一次** 填充全部应有 summary；**整包二元成败**（无结构级中间成功）；失败仅 **S03 max-retries**，耗尽后显性 failed 并继续后续任务。

> **跨文档审计声明**：S07 不新增 StateFamily、不复制 S03 Process 八态、不创建 Intake identity、不切 serving pointer、不写 vector index。GenerationArtifact / Invocation / per-type current 与 S06 同构（D02 正交事实）。ConstructionSchema 由 S07 拥有业务语义；S12 承接物理 registry 与 TX。

> **S11校准声明**：`S11-v1.0` 提供 summary/structured 路径的本地 Inference；S07 不直连 adapter；token/usage 经 invocation 账；向量化仍 outbox→S08 而非 S07 内嵌 embed。

> **对 T-O-133/136 的 v1 收窄（T-O-138）**：取消 `original-only admitted` / `allow_original_only` 作为 full-valid；v1 不启用 process-local summary repair 成功路径；disposition 仅失败取证。旧 T-O 行文保留历史，**以本 Spec 与 T-O-138 为 v1 成功面权威**。

> **Legacy 边界（T-O-42 / T-O-131）**：不继承 SMCP wire、R2 key 成功语义、`smind_vec_process` 作 SSOT、blind INSERT、step-name meta-only、flat layered wire 兼容。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S07 回答：在 **不改写** S06 original structure kernel 的前提下，如何把 exact S06 structure + projection 变成 **original/summary 双通道** 的可验证构造产物，并完成 meta 投影、`content_full` 配方与向 S08 的 outbox 交接——使检索侧能以 summary 索引、以 original 回溯。

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

1. §2 Truth 映射到 capability、schema、service、test；
2. bootstrap ConstructionSchema 在 readiness 前注册；
3. 整包 dual-channel full-valid → multi-pointer CAS + outbox；
4. 失败不 CAS；S03 retry 同 digest；max-retries → 显性 failed；
5. S08 仅凭 exact construct generation refs 可枚举通道并对账 content_full；
6. 零 legacy Constructor runtime dependency；
7. §6 验收矩阵通过。

---

## 2. 真相层

> Truth 来自 Owner 对 `qna-truth/S07.md v1.0` 的接受。Legacy 仅为 ReferenceAnchor。

### 2.1 Owner Truth 登记（全局 T-O · S07 段）

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
| `S07-T004` | ProcessCommand materialize 后锁定 `command_input_digest`；retry 同 digest。 | `T-O-139`、`T-O-93` 哲学 | 不可变 binding |
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
| `S07-T024` | OOS：无公网 construct CRUD、无用户 generation 精修、无 S07 内 embed/index/serving。 | `T-O-140`、`T-O-93` | |
| `S07-T025` | 不引入 GenerationCommit 业务身份；accepted = per-type full-valid current。 | `T-O-96/131` | |
| `S07-T026` | S08 必须绑定 exact/new construct generation；禁混代。 | `T-O-134` | |
| `S07-T027` | 幂等：同 `(execution, capability, command_input_digest)` → 同一 logical current 或 conflict。 | `T-O-139` | |
| `S07-T028` | 有 non-empty original 的结构位必须有 grounded summary 才算整包 dual-channel 完备。 | `T-O-138` | 无 original 位不计入应摘要集合 |
| `S07-T029` | grounding 最小：summary `grounds_coordinate` = 本单元 generation-scoped coordinate。 | `T-O-136`（取证） | 失败 report 可用 |
| `S07-T030` | 零结构/空 projection 整包 → fail（不得成功空构造）。 | `T-O-138` | |

### 2.3 继承上游（不重开）

- S03：`lsrag.construct` leaf；claim/fence/max-retries；Outcome 与 status 分账。  
- S06：generation-scoped coords；structure 无权威 summary；consumer 加载 exact schema。  
- S04：filter/context 权威。  
- S12：TX-06 generation accept；bytes-first；outbox。  
- S13：logical handle；`generation_artifact` purpose；禁 path 入契约。  
- D02：不新增 StateFamily。

---

## 3. 总体方案陈述

1. **整包处理**：单文档 Execution → 一次 Process → 一套 Construction 成员 CAS。  
2. **双通道对齐 S06 projection**：1:1 坐标；original 保真；summary 整包填充。  
3. **成功唯一**：full-valid 整包 dual-channel 完备才 CAS；否则失败。  
4. **恢复唯一**：S03 max-retries；无 S07 内摘要软着陆。  
5. **Schema 分账**：ConstructionSchema ≠ StructureSchema；exact digest 绑定。  
6. **元数据**：S04 权威；S07 投影 + content_full 配方。  
7. **交接**：artifact SSOT + outbox intent；S08 可对账重算。  
8. **模式**：`full_construct` 与 `metadata_refresh` typed 化。  
9. **运维**：readiness、预算、typed 错误、per-child scatter、OOS。  
10. **legacy 只作反例**：保留 dual-channel/traceback 语义，删除 wire 与队列 SSOT。

---

## 4. 具体执行方案清单

### 4.1 Process capability 与 Command/Outcome

**对应真相**：`S07-T001..006`、`T-O-139`

```text
ProcessCapabilityManifest
  capability_key: lsrag.construct
  modes: full_construct | metadata_refresh
  input:
    structure_generation_ref+digest
    projection_generation_ref+digest
    intake_revision_ref + clean_artifact ref+digest
    construction_schema_ref (key/version/digest)
    construct_profile_ref
    summary_prompt_ref / summary_model_ref  # may be explicit-null on refresh+reuse
    reuse_summaries: bool
    source_construction_generation_ref?     # when reuse_summaries
  freeze: command_input_digest
  output on full_valid:
    construction_document ref+digest
    dual_channel_projection ref+digest
    validation/report ref+digest
    summary_plan_digest
    invocation set digest/counts
    outbox intent ref (observability only)
  max_retries: S03-owned
```

**小结**：单一 capability + mode 字段；禁止 catchall payload 与 latest 取数。

### 4.2 Construction 产物与 Schema

**对应真相**：`S07-T007..010`、`S07-T015..016`、`T-O-135`

1. **construction_document**：envelope — S06 refs、schema digests、有序结构单元清单、metadata 投影 digest、summary plan 摘要、alignment proof。  
2. **dual_channel_projection**：按 coordinate 的 Original/Summary 通道记录（payload handle+digest、channel、content_full digest/配方 digest）。  
3. **validation/report 面**：full-valid 证明或失败 findings（失败时可不 CAS current）。  
4. **ConstructionSchema**：`schema_key + version + digest`；bootstrap 例：`mkb.construction_document@1`（拼写 Spec 可微调，readiness 前必须注册）。

**小结**：多成员 immutable + multi-pointer CAS；S08 可枚举通道。

### 4.3 整包 summary 与 dual-channel 完备

**对应真相**：`S07-T011..014`、`S07-T028..030`、`T-O-138`

```text
materialize summary_plan (digest locked)
  → whole-artifact summary generation (default document_single)
  → record invocations
  → validate whole package:
       binding + alignment + original digests
       + every non-empty-original structure has grounded summary
  → full-valid ? multi-pointer CAS + outbox
              : no CAS; Process failed → S03 retry
```

**小结**：包内多结构；包外一次成败。

### 4.4 Metadata、content_full、modes、handoff

**对应真相**：`S07-T017..019`、`S07-T006`、`T-O-134/137`

1. 从 S04 复制 filter/context **引用/投影**（digest 锁）；禁 parent/child 机会主义 merge 作 SSOT。  
2. `content_full` = 确定性配方（可选头字段闭集 + body）。  
3. outbox `vectorize_construct`（名可微调）：仅 exact construct generation refs + schema digests。  
4. `metadata_refresh`：reuse 或重算 summary 规则由 command 声明；成功仍须整包 dual-channel 完备。

### 4.5 Readiness / 预算 / 错误 / scatter / OOS

**对应真相**：`S07-T021..024`、`T-O-140`

见 §2.2 与 §6 验收矩阵。

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

### 5.4 实施切片（非排期）

1. ConstructionSchema bootstrap + readiness；  
2. `lsrag.construct` handler + Command digest；  
3. dual-channel align + whole-artifact validator；  
4. summary plan + S11 Invocation；  
5. S13 promote + multi-pointer CAS + outbox；  
6. golden dual-channel fixtures + 失败/重试验收。

---

## 6. 强制验收矩阵

| ID | HARD 场景 | 证据 |
|---|---|---|
| `S07-A01` | 缺 structure/projection 或 digest 不匹配 | fail-closed；无 CAS |
| `S07-A02` | 跨 generation 拼装 structure 与 projection | fail-closed |
| `S07-A03` | 模型改写 original | kernel fail |
| `S07-A04` | 应有 summary 缺失/空 → 整包失败 | 无 CAS；非 partial success |
| `S07-A05` | full-valid 成功 | 三成员/证明一致 current；outbox 可观测 |
| `S07-A06` | 同 command_input_digest 重试 | 同 digest；幂等或 conflict |
| `S07-A07` | max-retries 耗尽 | Process failed；无 usable current；历史可查 |
| `S07-A08` | metadata_refresh + reuse_summaries | 新 generation；meta/content_full 更新；dual-channel 仍完备 |
| `S07-A09` | filter 模型发明键 | reject |
| `S07-A10` | content_full 重算 digest 不匹配 | S08 对账失败路径 |
| `S07-A11` | 无 ConstructionSchema 注册启动 | readiness false |
| `S07-A12` | 超预算 | CONSTRUCT_BUDGET_*；无截断成功 |
| `S07-A13` | scatter child 独立 construct | 无跨 Item 大包 |
| `S07-A14` | Outcome 无 path/R2/正文 | architecture/contract test |
| `S07-A15` | 零 legacy constructor/SMCP 依赖 | 扫描零命中 |
| `S07-A16` | S07 success 不切 serving/index | serving 仍旧 |
| `S07-A17` | 无公网 construct API | surface 测试 |
| `S07-A18` | pending 队列表不作为 SSOT | 设计/架构测试 |

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

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO`**：S07 作为 LS-RAG Constructor 的 foundation、整包 dual-channel 成败心智、ConstructionSchema/产物成员、Command/Outcome、S08 handoff 与运维围栏已闭合，可进入 formal 实现规划与跨文档校准。

### 8.2 强制结论

1. 单文档 Execution；整包 artifact；一次 summary 全部应有粒度；  
2. 唯一成功 = 整包 dual-channel full-valid + per-type current CAS；  
3. 失败 = 不 CAS + 仅 S03 retry + 耗尽显性 failed + 后续任务可继续；  
4. original 保真；S04 filter 权威；content_full 配方；outbox 交接；  
5. 无 GenerationCommit 身份；无公网 construct；无 S07 内向量；  
6. legacy 仅 ReferenceAnchor。

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

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| `S07-v1.0` | `2026-08-11` | `accepted` | 冻结 QNA `T-O-126..140`；整包 dual-channel Constructor；Round 4 waived |
