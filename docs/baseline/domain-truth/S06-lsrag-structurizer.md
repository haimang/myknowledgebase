# S06 — LS-RAG Structurizer

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D5 LS-RAG 构建 / S06 LS-RAG Structurizer`
>
> **日期**：`2026-08-11`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted`（S06 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S06-v1.0`
>
> **上游权威输入**：`D01-v1.4`、`D02-v1.0`、`S01-v1.5`、`S02-v1.3`、`S03-v1.3`、`S04-v1.2`、`S05-v1.1`；冻结的 `qna-truth/S06.md v0.9`（Q1–Q6 / `T-O-77..85`、`T-O-93..96`）
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **事实证据**：`context/legacy-family/` 仅作 production-pitfall / behavior-archeology / design-counterexample `ReferenceAnchor`（Structurizer、Constructor、Recorder、RAG Dispatcher、Contexter Traceback、SMCP v1.6.3）；另有 Docling / Unstructured / LlamaIndex / RAPTOR / JSON Schema 一手资料
>
> **下游消费者**：`S07-S10`、`S11-S15`、跨系统拓扑 `17`、验收冻结 `18`

> **Owner-originated 约束**：S06 是可复验的 **original structure compiler**，不是 generic text chunker、二次 clean、summary worker 或 document editor。v1 生产路径 **全自动**；完整 human-in-the-loop 不在 S06 v1 范围，仅保留上游最小人工入口。

> **跨文档审计声明**：S06 不新增 StateFamily、不复制 S03 Process 八态、不创建 Intake identity、不切 serving pointer。GenerationArtifact / Invocation / per-type current pointer 是正交 typed facts（D02）。StructureSchema 由 S06 拥有业务语义；S12 只承接物理 registry。

> **S12校准声明**：`S12-v1.0` 兑现 Generation accept+pointer CAS（TX-06）、bytes-first artifact 元数据、generation 模块表、StructureSchema 物理 registry 与 readiness；Concurrent Writes 服务并发。S06 业务 contract 不变。

> **S11校准声明**：`S11-v1.0` 提供 `structured_generate` / 本地默认 vLLM；S06 只经 Inference 门面调用模型；调用成功≠Process 成功；generation_invocations 可链 `inference_invocation_uuid`。fallback/换模型政策以 S11 为准（v1 禁 transport 驱动 silent 换模型）。

> **Legacy 边界（T-O-42）**：不继承 SMCP wire、R2 key 成功语义、`file_uuid+block_id+granularity` 裸坐标、flat `layered_content` wire 兼容、模型生成 UUID、Worker 私有 retry 或 Cloudflare 拓扑。

---

> **S13校准声明**：`S13-v1.0` 冻结 v1 本地 `object_root` + `ObjectStorePort`、`mkbobj:v1` handle、team-scoped CAS、bytes-first、同库 catalog/ref/purpose、verify-on-read、周期 GC 与 identity readiness。本文件业务语义不变；对象 I/O 必须经 S13 Port，禁止 path/R2 key 进入契约。

> **S07校准声明**：`S07-v1.0` 消费本域 current structure + 同 generation projection，产出整包 dual-channel construction（projection 1:1）；S06 **仍不**产出权威 summary。S07 整包二元成败与 ConstructionSchema 不 reopen S06 kernel；S06 success 仍不等于 construct/serving success。

## 1. Domain 介绍

### 1.1 Domain 价值

S06 回答：一个已被 S04 接受、已通过 S05 admission 的 exact `IntakeRevision + clean IntakeArtifact`，如何在不改写来源语义的前提下，形成可验证的内容层级、阅读顺序、typed node、source anchor 与稳定 block coordinate，供 S07 构造 original/summary 双通道，并供 S08–S10 溯源与投影。

S06 解决八个核心问题：

1. structure 产物如何全历史、可审计，且每个 Execution 每 artifact type 只有一个 full-valid current；
2. Structure Schema 如何独立版本化，并由 producer/consumer 按 exact digest 共享加载；
3. deterministic kernel 与 governed extension 如何分界，agent 能否修补什么；
4. 生产路径如何默认全自动，input 在何处永久冻结；
5. MKB-native structure 形状如何取代 legacy flat layered 数组，同时保留双通道/共享坐标/全文层的生产语义；
6. retrieval block 如何作为 projection 而非 structure 本体；
7. 失败如何只走 S03 自动 retry 或 Process failed，而不引入用户 generation 精修产品；
8. S06 success 如何明确不等于 Execution / Task / serving success。

### 1.2 在整体拓扑中的位置

```text
S01/S02 Task Contract
  │
  ▼
S03 Workflow / Execution / Process
  │ ProcessCommand: lsrag.structurize
  │ exact input digest + fence + schema/profile/model binding
  ▼
S04 accepted IntakeRevision
  + S05 admitted clean IntakeArtifact + evidence
  │
  ▼
S06 Structurizer
  ├── StructureInputReader
  ├── StructureSchemaResolver (exact key/version/digest)
  ├── StructureGenerator (deterministic and/or model-assisted)
  ├── KernelValidator → optional ExtensionRepairer → FullValidator
  ├── RetrievalBlockProjector
  ├── StructureProofBuilder
  └── GenerationArtifactLedger + CurrentPointer CAS
  │
  │ ProcessOutcome + structure proof + generation refs
  ▼
S07 Constructor (summary / meta fusion / dual-channel units)
  → S08 Embedding → S09 Index → S10 Retrieval/Traceback
```

### 1.3 Canonical contract chain

```text
Task / Execution / Workflow binding                         [S01-S03]
  → accepted IntakeItem + exact IntakeRevision              [S04]
  → exact clean IntakeArtifact + PreflightOutcome           [S05]
  → ProcessCommand: lsrag.structurize                       [S03→S06]
  → immutable structure_document + retrieval_block_projection + proof
  → accepted ProcessOutcome                                 [S06→S03]
  → original/summary construction                           [S07]
```

### 1.4 六个工作平面

| 平面 | S06 v1 负责 | 状态/证据表达 | 明确不负责 |
|---|---|---|---|
| Binding | 锁定 exact Revision、clean Artifact、schema、profile、model/prompt | ProcessCommand + input digest | Workflow route、active latest 热切 |
| Structural semantic | typed ordered tree、root、node_kind、order | immutable `structure_document` | summary tree、Knowledge graph |
| Coordinate / projection | generation-local node/block coordinates、structure-aware blocks | `retrieval_block_projection` | vector UUID、ranking |
| Grounding / fidelity | exact clean anchors、coverage/order proof | anchor ledger + validation report | 重新 clean、模型补写缺失原文 |
| I/O / artifact | logical handles、GenerationArtifact/Invocation 账 | S13 logical refs + digests | R2 key、物理 GC 策略数值 |
| Runtime / control | S03 leaf Process、Command/Outcome | S03 八态 / claim / fence / retry | S06 私有 job 表、用户精修闭环 |

### 1.5 Single 与 scatter

- **single**：一个内容型 Execution 对 exact IntakeRevision 运行 S06；
- **scatter**：S06 默认在每个 required **child** Execution 内独立运行；root 仅在自身拥有可结构化 Revision/Artifact 时运行 S06；
- 禁止把多个 child 拼成一棵跨 Item 文档树；
- optional member discard / required failure 归约由 Workflow requiredness/loss policy 决定；S06 只返回 typed success/failure，不得静默跳过 required。

### 1.6 Scope fence

**S06 负责：**

- `lsrag.structurize` Process capability 的业务 contract；
- GenerationArtifact / Invocation / per-type current pointer / transition 账本语义；
- StructureSchemaDefinition 业务语义与 semantic invariants（物理 registry 归 S12）；
- structure_document / retrieval_block_projection / validation proof 逻辑形状；
- kernel/extension/repair/full-validation 闭环；
- automatic production path 下的 exact input freeze；
- large-input 的 fail-loud 业务要求（数值 budget 可由 profile 声明，driver 归 S11/S15）；
- 对 S07–S10 的 coordinate / lineage / acceptance 输入合同。

**S06 不负责：**

| 排除项 | 权威归属 |
|---|---|
| Task API / 六态 / restart ledger | S02 |
| Workflow graph / Process 八态 / claim/retry engine | S03 |
| Intake identity / Revision / serving | S04 |
| acquire/clean/preflight/完整 HITL 产品 | S05（v1 不因 S06 扩展完整 curation 管线） |
| summary / meta fusion / dual-channel construction units | S07 |
| embedding / vector index / publication | S08–S09 |
| retrieval ranking / answer generation | S10 |
| provider runtime / fallback | S11 |
| exact DDL / 跨介质事务 driver | S12 |
| object backend layout / GC 数值 | S13 |
| prompt/model registry 物理表 | S14 |
| metric/alert/retention 数值 | S15 |
| 完整 human-in-the-loop 生产管线 | **v1 out-of-scope**（`T-O-93`）；仅保留上游最小入口 |

### 1.7 Domain 完成定义

1. §2 全部 Truth 可映射到 contract、schema、service 与 test；
2. 至少一份 bootstrap `StructureSchemaDefinition`（exact key/version/digest）在 readiness 前注册；
3. single/scatter、input freeze、retry 同 digest、invalid 不切 pointer 的测试通过；
4. tree/anchor/coverage/coordinate 的 golden + 反例通过；
5. kernel 失败不可 agent 修、extension repair 新 artifact 全量复验通过；
6. max-retries → Process failed，且历史/token 可查；
7. 零 legacy runtime dependency 扫描通过；
8. §6 强制验收矩阵全部通过。

---

## 2. 真相层

> Truth 来自 Owner 对 `qna-truth/S06.md` 的接受。Legacy/Web 仅为 ReferenceAnchor。

### 2.1 Owner Truth 登记（全局 T-O）

| Truth-ID | 摘要 | 本域强制 |
|---|---|---|
| `T-O-77` | 每次 generation/repair/retry 输出 → immutable GenerationArtifact；每次模型调用 → Invocation/token 账 | 禁止只靠日志 |
| `T-O-78` | `(team, execution, artifact_type)` 唯一 CAS current；只指 full-valid logical file | 禁止 mtime/latest 猜 current |
| `T-O-79` | Task-scoped list/get/current 只读；Create 仅 fenced Process；无普通 Delete | 非 Intake/runtime/serving 身份 |
| `T-O-80` | StructureSchema 内部注册、immutable key/version/digest | 外部无 Schema CUD |
| `T-O-81` | Execution/Artifact 锁 exact schema；consumer 主动加载；禁 latest | digest drift fail-loud |
| `T-O-82` | shape + kernel + extension + semantic invariants 同 definition | JSON shape 不够 |
| `T-O-83` | kernel 不可 agent 修；fidelity/proof/coordinate 属 kernel | 不得塞 payload_extra |
| `T-O-84` | repair → 新 artifact + 全量复验后才可 CAS pointer | 禁止原位改 |
| `T-O-85` | 无 S06 私有 retry 机；S03 max-retries；禁 generic fallback | success ≠ Task/serving |
| `T-O-93` | v1 全自动生产路径；Command+input digest freeze；HITL 完整管线 out-of-scope | retry 禁读 latest clean |
| `T-O-94` | structure_document 树 + anchors + generation-local coords + 分账 projection | 禁 flat 裸坐标 / blocks-only |
| `T-O-95` | QNA 冻 logical contract；首份 concrete schema 在 Spec/bootstrap；readiness 前必须注册 | 开放 kind 不得进 runtime |
| `T-O-96` | 每 Execution 一套 accepted 结果（per-type pointers）；仅自动 retry；用户精修 defer | 禁 promote / GenerationCommit 身份 |

### 2.2 域内 Truth 编号（S06-T）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S06-T001` | S06 唯一首版 Process capability key 为 `lsrag.structurize`（versioned manifest）。 | `T-O-85`、S03 | 无第二套 structurizer job 状态机 |
| `S06-T002` | 输入必须同时绑定 exact IntakeRevision 与 revision-owned clean IntakeArtifact handle/digest；缺失 fail-closed。 | `T-O-93`、S04/S05 | 无 bare text 入口 |
| `S06-T003` | ProcessCommand durable materialize 后，selected clean/schema/profile/model/prompt binding 与 input digest 永久冻结；retry/recovery 只重放同一 digest。 | `T-O-93` | 禁止 latest clean/schema |
| `S06-T004` | v1 生产主路径全自动；不实现 clean curation 命令面、inspection 编辑台、RAG 内 patch、用户 generation 精修产品。 | `T-O-93` | 验收场景不以 HITL 为主路径 |
| `S06-T005` | 每次形成输出文件的 generation/repair/retry 创建 immutable GenerationArtifactRecord。 | `T-O-77` | 无覆盖写 |
| `S06-T006` | 每次模型调用（无论是否形成 artifact）创建 GenerationInvocationRecord（binding、digest、token、causation）。 | `T-O-77` | 日志不可替代 |
| `S06-T007` | `(team_uuid, execution_uuid, artifact_type)` 唯一 current pointer；仅 full-valid；变更 append transition。 | `T-O-78` | invalid 不切 pointer |
| `S06-T008` | v1 最小 artifact_type 集合：`structure_document`、`retrieval_block_projection`、`structure_validation_report`（或等价 proof 证据类型）。 | `T-O-94` | 可扩展注册，但跨 type 拼装须 binding 一致 |
| `S06-T009` | GenerationArtifact 不是 Intake identity、不是第四层 runtime identity、不是 serving pointer。 | `T-O-79` | S06 success 不切 serving |
| `S06-T010` | Task-scoped GET：generation-artifacts list/get、pointers current；强校验 Task→Execution→artifact。 | `T-O-79` | 无 Execution 写面 |
| `S06-T011` | StructureSchemaDefinition 由 S06 拥有；identity=`schema_key+version+digest`；同 version 异 digest fail readiness。 | `T-O-80` | 演进只增 version |
| `S06-T012` | 每个 Execution 与每个 GenerationArtifact 锁定 exact schema ref/digest；S07–S10 manifest 声明 supported range；S03 compile/readiness 预检。 | `T-O-81` | 禁 latest |
| `S06-T013` | Schema definition 必须含：strict shape、deterministic_kernel、governed_extension、semantic_invariant_manifest、artifact media contract。 | `T-O-82` | 下游加载完整 contract |
| `S06-T014` | kernel 至少含：identity/binding、tree topology/order/coordinates、source anchors/fidelity、artifact handle/digest、proof refs。 | `T-O-83` | kernel 失败 → S03 retry evidence |
| `S06-T015` | extension 仅 schema 声明的 non-authoritative 字段；影响 route/filter/auth/coordinate/fidelity 的必须晋升 kernel。 | `T-O-83` | 禁 payload_extra 藏 truth |
| `S06-T016` | agent repair 仅 extension + policy 允许；新 artifact + 从零全量校验后才可 CAS。 | `T-O-84` | 禁局部复验 |
| `S06-T017` | 达到 S03 max-retries → Process failed；保留全部 artifact/report/token；禁 schema 放宽与 generic block fallback。 | `T-O-85` | 与 S03 单一 retry 账 |
| `S06-T018` | `structure_document` 恰有一个 `document_root`；nodes 以 flat ordered ledger 表达不可变树。 | `T-O-94` | 禁多 root |
| `S06-T019` | `node_id` 由 Engine 分配（generation-local）；禁止模型生成权威 identity。 | `T-O-94`、legacy UUID 幻觉 | golden |
| `S06-T020` | `node_kind` 在 exact Schema version 内 closed union；禁 runtime 任意字符串与 unknown 静默兜底。 | `T-O-94`、`T-O-95` | 新 kind → 新 schema version |
| `S06-T021` | content-bearing leaf 必须 exact anchor 到 **本次** selected clean Artifact；v1 anchor 形态至少支持 `text_span`（UTF-8 byte half-open）与/或 `element_span`（clean-element identity），由 schema version 声明。 | `T-O-94` | 无 anchor = kernel fail |
| `S06-T022` | coverage/order：leaf anchors 按 reading order 覆盖 required-content manifest；遗漏/重复/乱序 = kernel fail。 | `T-O-94` | semantic validator |
| `S06-T023` | node coordinate=`(team_uuid, structure_generation_artifact_uuid, node_id)`；block coordinate 另含 projection generation。仅 generation-local。 | `T-O-94` | 禁跨代 node map |
| `S06-T024` | `retrieval_block_projection` 引用 exact structure_document ref/digest；不得反向修改 tree。 | `T-O-94` | 分账 |
| `S06-T025` | 下游 accepted 消费：current structure_document + binding 一致的 projection/proof；禁止跨 generation 拼装。 | `T-O-96` | S07 合同 |
| `S06-T026` | 不引入 GenerationCommit 业务身份；唯一 accepted 由 per-type current pointers 表达。 | `T-O-96` | 实现可用事务原子切多 pointer |
| `S06-T027` | 配置/schema/model/prompt/clean 变更 → 新 Execution 或既有 S02 rebuild/retry generation；禁止旧 Execution 热切 accepted 族。 | `T-O-96` | |
| `S06-T028` | structure/model/prompt rebuild **不**制造 IntakeRevision；S06 不写 Intake lifecycle。 | S04、`T-O-79` | |
| `S06-T029` | S06 **不**产出权威 summary；`llm_summary` 不进入 structure kernel。Summary 归 S07。 | legacy 分界、`T-O-94` | |
| `S06-T030` | 首份 concrete StructureSchemaDefinition 作为本 Spec §3 草案 + bootstrap 输入交付；未注册前不得 readiness。 | `T-O-95` | |
| `S06-T031` | large-input：必须有显式 budget/window 策略或 fail-loud disposition；禁止依赖 provider 隐式截断当成功。 | legacy 整文单次调用 | profile 声明 |
| `S06-T032` | payload_extra 可用于非权威扩展，但 identity/state/proof/route/auth/正文/anchor/coordinate 禁止进入。 | S01-T040 继承 | |

### 2.3 与上游 Gate 的继承（不重开）

继承 S06 QNA `U-S06-01..14`：Task/Execution/Process 分层；Process 只收 Command 回 Outcome；八态与 claim/fence 唯一；Revision 不可被 structure 覆盖；Artifact logical handle；latest≠serving；S05 loss/quality 继承；team-scoped；legacy reference-only；phase `structurizing` 不替代 Process proof。

---

## 3. Contract schema 与数据不变量

### 3.1 Process capability

```text
ProcessCapabilityManifest
  capability_key: lsrag.structurize
  version + digest
  input_ports:
    - clean_artifact (logical handle + digest + media)
    - intake_revision binding
    - structure_schema (key/version/digest)
    - structure_profile / projection_profile
    - optional model/prompt refs
  output_ports:
    - structure_document generation artifact
    - retrieval_block_projection generation artifact
    - structure_validation_report / proof
  proof_contract: full-valid kernel + semantic + coverage
  max_retries: owned by S03 Process spec (frozen on Execution)
  repair_budget: optional, from profile (0 = no agent repair)
```

### 3.2 Generation 账本（逻辑，非 DDL）

```text
GenerationArtifactRecord          [immutable]
  generation_artifact_uuid
  team_uuid, artifact_type, artifact_ordinal
  task_uuid, execution_uuid, process_uuid, process_attempt
  intake_item_uuid, intake_revision_uuid
  clean_artifact_uuid + digest
  schema/profile/model/prompt refs + digests
  process fence
  logical_handle + media + size + digest
  validation_disposition + report/proof refs
  predecessor/repair causation refs
  invocation refs, created_at, payload_extra

ExecutionGenerationArtifactPointer  [CAS]
  unique (team_uuid, execution_uuid, artifact_type)
  current_generation_artifact_uuid
  pointer_revision
  expected fence

GenerationArtifactPointerTransition [append-only]
  before/after, expected/actual revision, causation, occurred_at

GenerationInvocationRecord        [append-only]
  execution/process/attempt, invocation_ordinal
  generation | repair
  model/prompt/schema/profile refs
  input/output/error digests
  token usage, causation, occurred_at
```

### 3.3 StructureSchemaDefinition（逻辑）

```text
StructureSchemaDefinition
  schema_key / schema_version / schema_digest
  schema_dialect
  deterministic_kernel_schema
  governed_extension_schema
  semantic_invariant_manifest + validator refs
  artifact_type + media contracts
  compatibility declaration
  registration origin / created_at / payload_extra
```

规则：internal register；list/get/resolve 只读；外部无 CUD；同 version 同 digest 幂等；异 digest fail readiness。

### 3.4 structure_document（logical envelope）

```text
structure_document
  envelope:
    generation_artifact_uuid
    schema_key/version/digest
    input_bindings (revision, clean_artifact+digest, profiles, fence)
  document_root_node_id
  nodes[]:
    node_id
    node_kind                 # closed by schema version
    parent_node_id?
    sibling_ordinal
    depth
    reading_ordinal
    content_role
    source_anchor_refs[]
    content_digest
    subtree_digest
    governed_extension_values?
    payload_extra
  proofs:
    tree_proof (single-root, acyclic, parent/order)
    coverage_proof
    coordinate_uniqueness_proof
```

### 3.5 Source anchors

```text
SourceAnchor
  anchor_id
  kind: text_span | element_span | (schema-versioned extensions)
  text_span?: { start_byte, end_byte }   # UTF-8 half-open on clean artifact bytes
  element_span?: { element_id, ... }    # stable clean-element identity from S05
  clean_artifact_uuid + digest
  resolution: exact | honest_approx (approx 仅 schema 允许时)
```

### 3.6 retrieval_block_projection

```text
retrieval_block_projection
  envelope:
    generation_artifact_uuid
    structure_document_ref + digest
    projection_schema/profile ref + digest
  blocks[]:
    block_id
    source_node_refs[]
    ordered_source_spans[]
    original_content_ref + digest
    ancestor_heading_refs[]
    token_estimate / char_estimate
  proofs:
    projection_coverage_order_proof
```

### 3.7 v1 StructureSchema 草稿：`mkb.structure_document.v1`

> 本小节满足 `T-O-95`：首份 concrete schema 随正式 Spec 交付。实现 bootstrap 时计算 digest；下列为 **normative 形状与闭集**，非 JSON Schema 全文序列化（可用同等 shape 实现）。

#### 3.7.1 Identity

| 字段 | 值 |
|---|---|
| `schema_key` | `mkb.structure_document` |
| `schema_version` | `1` |
| `artifact_types` | `structure_document`, `retrieval_block_projection`, `structure_validation_report` |

#### 3.7.2 node_kind 闭集（v1）

```text
document
section
paragraph
list
list_item
table
table_row
table_cell
code
quote
media_ref
heading
```

新增 kind → **新 schema_version**（或 schema 声明的 namespaced extension branch），禁止运行时自由字符串。

#### 3.7.3 Deterministic kernel（不可 agent 修）

- envelope bindings 与 digests；
- document_root 唯一；
- nodes 集合：parent 存在性、sibling_ordinal 连续、reading_ordinal 全序、无环；
- node_id uniqueness；
- node_kind ∈ closed set；
- 每个 content-bearing leaf 的 source_anchor_refs 非空且可解析到 selected clean digest；
- coverage/order proofs 通过；
- coordinates 可从 envelope+nodes 确定性派生；
- 不含 summary 正文、不含权威 filter meta、不含跨系统 UUID 身份。

#### 3.7.4 Governed extension（可 schema 声明 repair）

示例（须在 definition 中显式列出 JSON pointers）：

- optional display labels / non-authoritative classification tags；
- namespaced annotation objects；
- 不得包含 route/auth/coordinate/anchor/body。

#### 3.7.5 Semantic invariants（必须与 shape 同注册）

1. exactly one root with `node_kind=document`（或 schema 声明的 root kind）；
2. parent/child 一致且 acyclic；
3. reading_ordinal 在文档内唯一且递增；
4. leaf coverage 并集覆盖 required-content manifest（由 profile/schema 定义 full-document 或 selected ranges）；
5. 无未解析 anchor；无重复计入的 container 双计 coverage；
6. projection 每个 block 的 source_node_refs 均存在于 structure_document；
7. projection 不得引入 structure 中不存在的 original 正文。

#### 3.7.6 Projection profile（逻辑默认）

v1 默认 profile 必须能从 structure 生成：

- 至少一个 full-document / root-level retrieval block（承接 legacy granularity=0 全文语义）；
- 可选 section/paragraph 级 blocks（profile 配置）；
- 每个 block 可回溯 original via structure anchors（承接 dual-channel 的 original 侧）。

### 3.8 状态与正交事实（D02 对齐）

| 对象 | 是 StateFamily？ | Owner |
|---|---|---|
| Process 八态 | 是 | S03 |
| Generation current pointer | **否**（typed selection fact） | S06 |
| validation disposition | 否 | S06 |
| phase `structurizing` | 否（Execution 业务坐标） | S03 |

禁止：`structuring`/`vector_ready` 等伪 status；禁止第七 StateFamily。

---

## 4. 业务流转与接口 Contract

### 4.1 全自动主路径

```text
S05 admitted clean (+ 既有 Gate 仅当上游已触发)
  → S03 materialize ProcessCommand(lsrag.structurize) + input digest
  → claim/fence Process
  → read clean artifact bytes/elements
  → resolve exact StructureSchema
  → generate candidate structure_document (+ invocation)
  → kernel validate
       fail → report + S03 retry (same digest)
  → extension validate
       fail + repair_allowed → repair new artifact → full revalidate
  → project retrieval_block_projection
  → full proof
  → CAS current pointers (structure, projection, report)
  → ProcessOutcome succeeded
  → S03 route → S07
```

### 4.2 Input freeze 之后的非法操作

- 替换 selected clean Artifact；
- 解析 active/latest schema 或 latest clean；
- RAG 内编辑 node/block；
- 人工 promote 历史 candidate；
- 用户产品化 “再生成一次” 精修（defer）。

### 4.3 失败与 rebuild

| 情形 | 行为 |
|---|---|
| AI/schema/kernel/provider 失败 | typed evidence → S03 retry_wait / failed |
| max-retries | Process failed；历史全留 |
| 换 schema/model/profile/clean | 新 Execution 或 S02 rebuild/full-retry generation |
| terminal 后业务重做 | 既有 S02 causal 机制；不复活旧 tree 多轮 accepted |

### 4.4 Task-scoped 只读 API（语义）

```text
GET /v1/tasks/{task_uuid}/generation-artifacts
GET /v1/tasks/{task_uuid}/generation-artifacts/{generation_artifact_uuid}
GET /v1/tasks/{task_uuid}/generation-artifact-pointers
```

服务端校验 team + Task→Execution→artifact。无 POST/PATCH/DELETE 普通写面。

### 4.5 ProcessOutcome 最小字段（逻辑）

```text
outcome_status: succeeded | failed | cancelled
retryability: ...
structure_document_ref + digest?
projection_ref + digest?
validation_report_ref + digest?
schema_key/version/digest
input_digest
token_summary?
error_code/details?
```

### 4.6 对 S07–S10 的强制消费合同

1. 必须加载 artifact 声明的 exact schema version/digest；
2. 必须携带 generation-scoped coordinates；
3. summary 通道必须能 traceback 到 original（经 structure/projection）；
4. 不得用 file_uuid+int 裸坐标作为跨代 identity；
5. structure success 后的 serving/index 仍需各自 publication proof。

---

## 5. 事实反例、风险与实施切片

### 5.1 Legacy 反例 → MKB 禁令

| Legacy 事实 | MKB 禁令 |
|---|---|
| SMCP 成功 = R2 key | 必须 proof + digests + pointer CAS |
| flat block_id+granularity 无 parent/order/anchor | 必须树 + anchors + proofs |
| 模型 UUID / knowledge_tree 幻觉 | Engine 分配 identity；禁模型权威 UUID |
| preprocess 补 llm_summary/coerce ID | kernel 失败不 silent fix |
| 整文单次 userContent | budget/window 或 fail-loud |
| Worker 内不可见 AI retry | 计入 S03 + Invocation |
| Constructor 同形 schema 内嵌 summary | S06 不含 summary kernel |
| Contexter 无 generation fence | generation-scoped coordinates |

### 5.2 保留的生产语义（非 wire）

- original/summary **双通道**（summary 在 S07）；
- **共享坐标** 贯穿 construct→vector→traceback；
- **全文/root 层** 可膨胀（projection full-document block）；
- structure 与 meta-only rebuild **解耦**（typed route + generation ref）；
- 声明式 typed I/O ports。

### 5.3 风险台账

| 风险 | 缓解 |
|---|---|
| 全历史存储膨胀 | S13/S15 retention；audit skeleton 不可抹 |
| schema 版本矩阵 | v1 少 version；readiness 预检 |
| kernel 严格导致失败率 | profile/model 治理；非 HITL 回退 |
| 推迟 concrete schema 细节 | `T-O-95` + bootstrap 门；无注册不 readiness |
| large-input | S06-T031 + profile budget |

### 5.4 实施切片（非排期）

1. Generation ledger + pointer CAS ports；
2. Schema registry bootstrap `mkb.structure_document@1`；
3. `lsrag.structurize` handler + validators + projector；
4. S03 manifest 绑定与 Outcome；
5. Task-scoped read projection；
6. Golden structure fixtures + adversarial cases。

---

## 6. 强制验收矩阵

| ID | HARD 场景 | 证据 |
|---|---|---|
| `S06-A01` | 缺 clean artifact / digest 不匹配 | fail-closed，无 Process success |
| `S06-A02` | Command materialize 后替换 clean 再 retry | 仍用原 digest；或 conflict |
| `S06-A03` | 生成 invalid tree（多 root/环） | kernel fail；pointer 不变；Invocation 有账 |
| `S06-A04` | leaf 无 anchor | kernel fail |
| `S06-A05` | coverage 遗漏/乱序 | kernel fail |
| `S06-A06` | extension repair 成功 | 新 artifact；全量复验；pointer 更新 transition |
| `S06-A07` | repair 触碰 kernel | invalid；不 CAS |
| `S06-A08` | max-retries 耗尽 | Process failed；历史完整 |
| `S06-A09` | full-valid success | structure+projection+report current 一致 |
| `S06-A10` | 下游拼装跨 generation projection | 拒绝 / fail-loud |
| `S06-A11` | schema version 异 digest bootstrap | readiness false |
| `S06-A12` | 无注册 schema 启动 | readiness false |
| `S06-A13` | scatter child 独立 structure | 无跨 Item 大树 |
| `S06-A14` | required child structure fail | 按 Workflow loss policy 归约；S06 不静默丢 |
| `S06-A15` | Task-scoped read 跨 Task 访问 | 403/deny |
| `S06-A16` | S06 success 后 serving 未自动切换 | serving 仍旧直至 S09 proof |
| `S06-A17` | 禁止用户 generation 精修 API 作为 v1 必过 | 无该 surface 或明确 defer |
| `S06-A18` | legacy package import / SMCP 依赖扫描 | 零命中 |
| `S06-A19` | large-input 超 budget | fail-loud 或 profile 声明的合法 disposition，非截断冒充成功 |
| `S06-A20` | model 返回 summary 字段 | 忽略或 invalid（不得进入 kernel truth） |

---

## 7. Reference-anchor 台账

| Anchor | 路径/符号 | 用途 | 裁决 |
|---|---|---|---|
| SMCP 消息与 io/control | `smind-skill-rag-structurizer/core/schemas_smcp.ts` | 声明式 I/O、STEP 生命周期 | **保留原理**；**删除** wire/R2 |
| Structurizer I/O 契约 | `.../services/io_manager.ts` slots `raw_text`/`structured_json` | typed ports | 升级为 logical handles |
| Flat layered schema | `.../core/schemas_common.ts` `StructuredJsonOutputSchema` | 生产外形与债务 | **删除** wire；**保留** 双通道意图 |
| preprocess 修补 | `.../flows/structurizer.ts` `preprocessJsonStructure` | silent fix 反例 | **删除** |
| 整文单次 AI | `structurizer.ts` userContent=plainText | large-input 风险 | **升级** budget |
| 成功=R2 key | callback `structured_json_r2_key` | 成功语义债务 | **删除** |
| Constructor 同形消费 | `smind-skill-rag-constructor` schemas + constructor flow | S06/S07 分界 | **保留** 分界；summary 归 S07 |
| Recorder 双通道 | `.../services/recorder.ts` original/summary | 坐标消费 | **升级** generation-scoped |
| Traceback | `smind-contexter` topK / internal_retrieve | 共享坐标+全文层 | **保留语义** |
| Meta-only skip | `smind-rag-dispatcher/flows/orchestrator.ts` case_mode | structure 可复用 | **升级** typed route |
| Web | Docling/Unstructured/LlamaIndex/RAPTOR/JSON Schema | hierarchy 先于 chunk；summary≠structure | 支持分母 |

**证据使用判定：**

- **继承语义**：双通道、共享坐标、全文层、声明式 ports、structure 与 meta rebuild 解耦；
- **全局升级**：typed tree、anchors、generation fence、schema registry、proof、S03 retry；
- **删除**：SMCP/R2/flat 兼容、模型 UUID、silent preprocess、私有 retry、callback 成功。

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO`**：S06 作为 original structure compiler 的 foundation、自动生产路径、logical structure contract、generation 账本、schema 机制与首版 `mkb.structure_document@1` 草稿已闭合；下游 **S07-v1.0** 已 accepted 并校准本域消费合同。

### 8.2 强制结论

1. S06 不是 chunker / 二次 clean / summary worker / HITL 编辑器；
2. 产物全历史 + per-type full-valid current；
3. Schema 独立版本化；readiness 前必须注册首版；
4. kernel 不可 agent 修；repair 新 artifact 全量复验；
5. ProcessCommand input digest 后输入冻结；retry 同 digest；
6. structure_document 树 + anchors + generation-local coordinates；projection 分账；
7. 唯一 accepted 由 pointers 表达；无 GenerationCommit 身份；无用户精修产品；
8. success ≠ Execution/Task/serving；
9. legacy 仅 reference-anchor。

### 8.3 下游必须继续冻结的边界

| 下游 | 承接 |
|---|---|
| `S07` | summary、meta fusion、dual-channel units、共享 coordinate 消费 |
| `S08-S09` | embedding space、index generation、publication proof |
| `S10` | traceback/expand/rerank 算法与结果契约 |
| `S11/S14` | model/prompt 实现与 fallback |
| `S12` | generation/schema 表 DDL、CAS 事务、outbox |
| `S13` | logical file 持久化与 orphan GC |
| `S15` | token/quality metrics、retention 数值 |

### 8.4 一句话结论

S06 把 admitted clean 内容编译为可证明的 generation-scoped original structure 与检索投影，用自动路径、冻结输入、版本化 schema 与统一 Process 失败收敛，为 LS-RAG 双通道与溯源提供唯一可信结构地基。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `S06-v1.0` | `2026-08-11` | `MKB owner + Codex` | `accepted` | 吸收 Q1–Q6 与 `T-O-77..85`、`T-O-93..96`；冻结自动生产路径、generation 账本、StructureSchema 机制、logical structure/projection contract、首版 `mkb.structure_document@1` 草稿、验收矩阵与 legacy reference-anchor 裁决。 |
| `S06-v1.0-cal-s12` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S12-v1.0：TX-06/bytes-first/registry readiness；S06语义不变。 |
| `S06-v1.0-cal-s13` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S13-v1.0：logical handle/CAS/GC；S06 generation 语义不变。 |
