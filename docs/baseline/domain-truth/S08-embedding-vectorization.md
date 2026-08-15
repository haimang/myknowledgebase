# S08 — Embedding & Vectorization

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D6 向量资产 / S08 Embedding & Vectorization`（写侧）
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S08 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S08-v1.0`
>
> **上游权威输入**：`D01–D05`、`S01–S07`、`S11–S13`；`qna-truth/S08.md v1.0`（**证据层 / progressive 中间态 only**，非执行 SSOT）；冻结 Truth `T-O-211..230`
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.5+
>
> **事实证据**：`context/legacy-family/` 仅作 ReferenceAnchor（Vectorizer、Constructor recorder、RAG Dispatcher、Contexter、Console DDL）；**禁止** `legacy-specs` / `legacy-python` 作为本域证据源
>
> **下游消费者**：`S09–S10`、`S12`、`S15`、跨系统拓扑 `17`、验收冻结 `18`、实现与 architecture tests

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S08.md` 仅保留 progressive 形成过程（`T-O-211..230` 冻结轨迹），**不得**被引用为第二执行真相；冲突时 **以本文为准**。禁止「细节在 QNA、Spec 只写原则」。实现 **无需** 打开 QNA 即可编码。

> **★ 约束级别**：「必须 / 禁止 / 仅允许」= 强制；「应当」= 默认，偏离须 reopen S08；「可以 / 建议」= 非冻结不变量。

> **Owner 产品边界**：S08 是 **document-side 向量化写侧**。在 ConstructToVectorizeGate 之后，将 dual-channel 合法原料展开为 VectorizationUnit，经 S11 `embed` 生成向量，幂等 upsert 到同库 `mkb_vector_records`。**不**拥有：serving/PublicationProof（S09）；召回/Traceback/Rerank（S10）；Process 八态/`max_retries`（S03/D01）；filter/facet **产品**定义与 wire map（**S04**）；promptA/B/C（D05/S14）；推理 transport 细节（S11）。

> **D05 校准（T-O-202..210 / T-O-352）**：默认双通道；粒度 0/1/2；g=0 **summary** 必入向量候选；g=0 original 留在 construct 不进 required-set；construct 合法后才 vectorize；失败只引 D01/S03；vectorize **无**第四生产 Prompt。

> **S04 分账（T-O-229 HARD）**：filter/facet 权威 **只在 S04**。S08 **仅**执行写面：把已解析 facet **抄写**到向量行；**禁止**在 S08 内 map `industry-type` 等 wire 键或发明 domain。

> **S07 分账**：S07 交付 dual-channel full_valid + outbox `vectorize_construct`；ContentFullRecipe 权威配方；S08 必须可重算对账。

> **S09 分账**：存在向量行 **≠** serving；publication 独立 Process。**`S09-v1.0` accepted**（`T-O-231..246`）：消费 Handoff；PublicationProof；ActiveIndexPointer；可服务谓词。

> **S11 分账**：只经 Inference `embed`；Layer A 校验；transport 退避 **不计入** Process `retry_count`；幂等写路径与 S11-E09 对齐。

> **D04/S12 分账**：物理表/列/索引以 D04 为准；TX/outbox/claim 以 S12 为准；本文钉 **写语义与执行步骤**。

> **Legacy 边界（T-O-42 / T-O-220）**：不继承 SMCP callback 成功、`smind_vec_process` SSOT、content_full 列、CF Vectorize 可写 SSOT、DO WAL 必选、zero-pending=成功、裸跨代坐标。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S08 把 **已构造完备的 dual-channel 知识** 变成 **可检索的同库原生向量行**，并保证：

1. 只有 construct 合法原料可进入向量化（ConstructToVectorizeGate）；
2. original/summary 在 generation-scoped 坐标上可索引且可对账；
3. g=0 FullDocument 不被 skip 掏空；
4. 失败可恢复（S03 max-retries + 幂等 upsert），半写不可服务；
5. 业务 filter 与空间隔离分账，且不抢 S04 权威；
6. 实现者 **无需** 打开 QNA 即可编码与验收。

### 1.2 在整体拓扑中的位置

```text
S07 lsrag.construct full_valid
  │ multi-pointer CAS + outbox kind=vectorize_construct (同 TX)
  ▼
S03 Process: lsrag.vectorize  mode=from_construct
  │ ProcessCommand + command_input_digest freeze
  ▼
S08 Vectorize
  ├── ConstructToVectorizeGate re-check
  ├── ContentFullRecipe recompute + digest assert
  ├── Original reattach HARD (g=0)
  ├── Expand required VectorizationUnits
  ├── S11.embed (Layer A) + bounded batch / bisect
  ├── UPSERT mkb_vector_records (Layer A/B 抄写)
  └── ProcessOutcome full_valid + VectorizeHandoffV1
  │
  ▼
S09 index.validate_publication  →  S10 retrieve
```

### 1.3 Scope fence

**S08 负责：**

- ProcessCapability `lsrag.vectorize` 与 mode 闭集；
- ProcessCommand / ProcessOutcome / command_input_digest 合同；
- outbox `vectorize_construct` 消费语义（at-least-once + 幂等）；
- required VectorizationUnit 展开与整包二元成败；
- ContentFullRecipe 重算与对账；
- 有界 batch、渐进幂等 upsert、最终 gate；
- `purge_generation` 逻辑 soft-delete；
- metadata_refresh 后 digest 变/短路策略（消费侧）；
- original 装回 HARD 校验；
- Layer B **执行抄写**；
- 错误码 / readiness / OOS；
- 向 S09 的 VectorizeHandoff。

**S08 不负责：**

| 排除项 | 归属 |
|---|---|
| Task/Execution/Process 状态机与 max_retries 账本 | D01 / S03 |
| dual-channel 生产与 ConstructToVectorizeGate 生产侧 CAS | S07 |
| filter/facet 产品定义、wire map、unknown 策略 | **S04**（+S14 版本） |
| embed transport / 并发闸 / catalog 写语义 | S11 |
| DDL 表闭集 / ANN 索引存在性 | D04 / S12 |
| PublicationProof / serving / metric / topk | **S09** |
| Traceback / Rerank / ContextTier | S10 |
| prompt 正文 | D03 / S14 |
| 对象 bytes GC | S13 |
| retention/alert 数值 | S15 |

### 1.4 身份与关键对象

| 对象 | 定义 | 非定义 |
|---|---|---|
| **VectorizationUnit** | team × GenerationScopedCoordinate × channel × content_full_digest × Layer A/B 元数据意图 | 非 Process 行；非 `smind_vec_process` |
| **GenerationScopedCoordinate** | generation_artifact + unit_id（+ 可解析 granularity） | 非裸 file+block+granularity 跨代 |
| **ContentFull** | ContentFullRecipe 输出的 embed 输入文本 | 非 identity；非向量表列 |
| **FinalVectorBody** | `mkb_vector_records.embedding` native F32 | 非外置 Vectorize SSOT |
| **VectorizeHandoffV1** | Outcome 中可观测写证明 | 非 PublicationProof |

### 1.5 完成定义

1. §2 全部 Truth 被 contracts、迁移与 transition 实现；
2. construct 门闩前无法进入成功 vectorize；
3. dual-channel required-set 整包成败 + g=0 **summary** 强制可验收；
4. ContentFull 对账失败 fail-loud；
5. 渐进 upsert + 最终 gate + 半写不可 publication；
6. Layer B 只抄写 S04 权威；
7. 零 legacy vectorizer runtime dependency；
8. 实现 **无需** 打开 QNA；
9. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O · S08 段 · 执行摘要）

| Truth-ID | 摘要 | 本域强制 |
|---|---|---|
| `T-O-211` | S08 = 向量写侧域；不吞 S09/S10/S04 产品 | scope fence |
| `T-O-212` | ConstructToVectorizeGate；禁 structure 直通 | gate |
| `T-O-213` | 双通道 + g0/1/2；g=0 **summary** 必候选（`T-O-352`） | expand |
| `T-O-214` | 最终本体 = records.embedding；禁 content_full 列 / 外置 SSOT / vec_process | physical |
| `T-O-215` | 单 outbox；payload 无全文 | queue |
| `T-O-216` | 失败只引 D01/S03；transport 内环分账 | retry |
| `T-O-217` | recipe 重算对账；向量已写 ≠ S07/Task 成功 | handoff |
| `T-O-218` | 只经 S11 embed；Layer A fail-closed | inference |
| `T-O-219` | 存在 ≠ serving | publication fence |
| `T-O-220` | legacy-family only 证据 | greenfield |
| `T-O-221` | `lsrag.vectorize` + mode；v1 仅 from_construct；S09 publication | capability |
| `T-O-222` | required-set 整包二元成败；g=0 **summary** 不可 skip 消灭（`T-O-352`） | outcome |
| `T-O-223` | I1 recipe；T1 fail-loud 预算；G1 不自动 purge 旧代；P1 不强制 granularity 列 | write contract |
| `T-O-224` | original detach/reattach；S08 original 只吃装回后文本 | fidelity |
| `T-O-225` | Command/Outcome/outbox at-least-once；digest 含 model/namespace | command |
| `T-O-226` | 有界 batch + 渐进幂等 upsert + 最终 gate；失败不补偿删 | batch |
| `T-O-227` | purge soft-delete；refresh digest 短路；construct g=0 original HARD（不进 required） | purge/refresh |
| `T-O-228` | 错误码闭集 + readiness + OOS | ops |
| `T-O-229` | Layer B **只抄写** S04；零 map | filter write |
| `T-O-230` | VectorizeHandoff；S09 独立；Round 4 waived | closure |

### 2.2 域内 Truth 编号（S08-T）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S08-T001` | 唯一 ProcessCapability：`lsrag.vectorize`（废弃生产键 `lsrag.vectorize_index` 混称）。 | T-O-221 | registry exact key |
| `S08-T002` | mode ∈ {`from_construct`, `purge_generation`}；扩展须 schema/version。 | T-O-221/225 | 禁 step-name |
| `S08-T003` | `from_structure` / 消费 `vectorize_structure`：**v1 forbid**。 | T-O-221 | fail-closed |
| `S08-T004` | 仅 ConstructToVectorizeGate 后可 `from_construct` 成功路径。 | T-O-212 | 重检 current pointers |
| `S08-T005` | 输入 exact：dual_channel generation refs+digests + revision/item + recipe version + model/namespace binding。 | T-O-217/225 | 禁 latest |
| `S08-T006` | materialize 后 `command_input_digest` 冻结（含 mode+generation+recipe+model+namespace）；retry 同 digest。 | T-O-225 | 不可热切 |
| `S08-T007` | outbox `vectorize_construct` 与 construct CAS 同 TX 入队；投递 at-least-once；S08 claim 对齐 digests。 | T-O-215/225 | Transactional Outbox |
| `S08-T008` | 成功 **仅** Outcome `disposition=full_valid`；禁 outbox done/ACK/path/正文。 | T-O-225/230 | |
| `S08-T009` | required unit = trim 后 content_full/body 非空的 unit×channel，**排除** g=0 original；g=0 summary（non-empty）强制 required。 | T-O-213/222/352 | |
| `S08-T010` | 整包二元：全部 required upsert 成功才 full_valid；禁止 partial success。 | T-O-222 | |
| `S08-T011` | 空配方 skip 可观测；**不得**用 skip 消灭 g=0 summary。g=0 original 不是 vector unit，不记 empty-skip。 | T-O-222/352 | |
| `S08-T012` | ContentFullRecipe **强制重算**；有 digest 则 `H(recomputed)==digest` 否则 `CONTENT_MISMATCH`。 | T-O-223/217 | |
| `S08-T013` | 超预算 fail-loud（`BUDGET_*`）；禁静默截断冒充成功。 | T-O-223 | |
| `S08-T014` | 稳定 unit 序 `(granularity, unit_id, channel)`；有界 batch；provider 拒绝可 bisect。 | T-O-226 | |
| `S08-T015` | 渐进幂等 upsert；最终 `succeeded==required` gate。 | T-O-226 | |
| `S08-T016` | 失败保留已写行；**禁止**补偿删除本 run 半写；同键重试覆盖。 | T-O-226 | |
| `S08-T017` | 半写 **禁止** publication（T-O-219）。 | T-O-226/219 | |
| `S08-T018` | 同 unique 且 content_digest+model 已匹配 → 可 skip re-embed 仍计完成。 | T-O-226 | |
| `S08-T019` | 幂等键继承 D04：`(team, namespace, generation_artifact, unit_id, channel, embedding_model)` partial unique。 | T-O-214/223 | |
| `S08-T020` | Final body = `mkb_vector_records.embedding` F32；禁 content_full/content_text 列；禁外置 Vectorize v1 可写 SSOT；禁 `mkb_vec_process`。 | T-O-214 | |
| `S08-T021` | `from_construct` 只写 command 绑定的 **新** construct generation；不自动 purge 旧代。 | T-O-223 G1 | |
| `S08-T022` | `purge_generation`：按 generation soft-delete；可选 channel_filter；≠ 物理销毁。 | T-O-227 | |
| `S08-T023` | refresh 后：content_full 相关 digest 变 → 必须新 vectorize；未变且 model/ns 未变可短路。 | T-O-227 | |
| `S08-T024` | construct 中 g=0 original HARD：非空 + reattach/native_full；禁 detach 中间态。该通道不进入 required-set。 | T-O-224/227/352 | |
| `S08-T025` | 只经 S11 embed；Layer A fail-closed；禁 silent 跨 model。 | T-O-218 | |
| `S08-T026` | Layer B **只抄写** S04 已解析 facet；S08 零 wire map。 | T-O-229 | |
| `S08-T027` | 强制写 team/item/revision/generation/unit/channel + Layer A。 | T-O-229 | |
| `S08-T028` | 权威 facet 有值必须可索引落点；无值则空；禁 payload_extra 当 filter SSOT。 | T-O-229/198 | |
| `S08-T029` | VectorizeHandoffV1 最小字段集；无 serving/ANN/PublicationProof。 | T-O-230 | |
| `S08-T030` | Workflow 后继 publication 归 S09 独立 Process。 | T-O-230/221 | |
| `S08-T031` | 错误码前缀闭集见 §4.11；S03 只消费 retryability。 | T-O-228 | |
| `S08-T032` | readiness 条件见 §4.11；readiness ≠ liveness。 | T-O-228 | |
| `S08-T033` | OOS 清单见 §4.11。 | T-O-228 | |
| `S08-T034` | 幂等：同 `(execution, capability, command_input_digest)` 收敛同一逻辑结果或 conflict。 | T-O-225 | |
| `S08-T035` | 进度事件非 SSOT。 | T-O-226 | |
| `S08-T036` | scatter = 每内容 child Execution 独立 vectorize；root 不跨 Item 合包。 | 继承 S07 | |
| `S08-T037` | 不新增 StateFamily；vectorize 阶段是 phase 坐标，不是第七状态。 | D02 | |
| `S08-T038` | v1 不强制 D04 reopen `granularity` 列；unit_id 合同可解析 granularity。 | T-O-223 P1 | |

### 2.3 继承上游（不重开）

- **D01/S03**：Process 八态、claim/fence、max_retries、Outcome 上卷。
- **D05**：双通道/g0/门闩/失败引用/无第四 Prompt。
- **S07**：dual_channel full_valid、recipe、outbox 同 TX。
- **S04**：filter/facet 权威与 map。
- **S11**：embed Port、transport、闸、Layer A。
- **D04/S12**：records/namespaces/outbox/TX。
- **S13**：object handle（若 content 字节经对象存）。
- **D02**：六 StateFamily；pointer/proof 分账。

---

## 3. 总体方案陈述

1. **门闩在前**：无 construct full_valid + dual-channel 完备 + g=0，不得成功 vectorize。
2. **单 capability + mode**：与 S07 同构；publication 外置 S09。
3. **整包 required-set 二元成败**：与 S07 T-O-138 同构。
4. **配方可对账**：ContentFull 派生；禁向量表存全文。
5. **有界批 + 渐进幂等写 + 最终 gate**：半写可留、不可服务。
6. **失败归 S03**：无 S08 私有状态机；transport 内环分账。
7. **世代显式**：新 generation 只写新；旧代 soft-delete 显式 purge。
8. **原文保真**：只索引装回后 original。
9. **Layer B 抄写**：S04 权威，S08 零 map。
10. **QNA 零依赖**：执行细节全部在本文 §4 E 包。

---

## 4. 具体执行方案清单

### 4.1 `S08-E01` — Capability、mode 与目录落点

**真相**：S08-T001..T003；T-O-221；D03

**执行台账**

| 项 | 规范 |
|---|---|
| capability | `lsrag.vectorize` |
| modes | `from_construct`（v1 生产主路径）、`purge_generation` |
| 禁止 | `from_structure`；生产依赖 `lsrag.vectorize_index` 混称 |
| 代码落点 | `src/services/` 内 vectorize handler（原子 Process capability）；编排在 `src/runtime/` |
| contracts | `src/contracts/vector/`：Command、Outcome、Handoff、Unit、Error |
| 依赖 | 经 S11 Inference facade；经 S12 ports；禁直连 driver / path |

**小结**：单键 + mode；architecture 可测。

---

### 4.2 `S08-E02` — ProcessCommand 与 command_input_digest

**真相**：S08-T005/T006；T-O-225

**执行台账 — VectorizeCommandV1 最低字段**

```text
mode: from_construct | purge_generation
team_uuid, execution_uuid
# from_construct:
dual_channel_generation_ref + digests
construction_schema_ref? + digests?
content_full_recipe_version
intake_item_uuid, intake_revision_uuid
namespace_key | namespace_uuid
embedding_model_ref { model_key, model_version }  # 进 digest
# purge_generation:
target_generation_artifact_uuid(s)
channel_filter?: all | original | summary   # default all
command_input_digest  # materialize 后冻结
```

**digest 材料必须包含**：mode、generation refs/digests、recipe version、model_key+version、namespace、purge targets（若有）。

**禁止**：latest 隐式取数；Command 内嵌全文/path/R2 key。

**小结**：可重放、可对账、防热切模型。

---

### 4.3 `S08-E03` — Outbox 消费（Transactional Outbox）

**真相**：S08-T007/T008；T-O-215/225

**执行台账**

```text
S07 TX: CAS construction currents + insert outbox(kind=vectorize_construct, dedupe_key, payload=exact refs)
  → commit
S03: materialize/claim lsrag.vectorize Process (Command 与 outbox digests 对齐)
S08: 处理 → Outcome
outbox mark done 可与成功 TX 同事务或严格后置；done ≠ 业务成功定义
```

| 规则 | 规范 |
|---|---|
| 投递 | **at-least-once** |
| 消费幂等 | command_input_digest + D04 unique upsert |
| 成功定义 | Outcome full_valid **only** |
| 禁止 | outbox done / queue ACK 冒充成功 |

**小结**：可靠唤醒 + 幂等收敛。

---

### 4.4 `S08-E04` — ConstructToVectorizeGate 再检与 required 展开

**真相**：S08-T004/T009..T011；T-O-212/213/222

**执行台账 — from_construct 逐步（展开前）**

| 步 | 动作 | 失败 |
|---|---|---|
| 1 | claim Process + fence | claim fail |
| 2 | 校验 command_input_digest | BINDING |
| 3 | load exact dual_channel current + digests | BINDING |
| 4 | 确认 S07 full_valid 语义仍成立（current 指针、完备证明） | BINDING / DEPENDENCY |
| 5 | Construct g=0 original HARD（E07；不进 required） | ORIGINAL_NOT_REATTACHED |
| 6 | 枚举 unit×channel；算 ContentFull（E05）；形成 required 集；**排除** g=0 original | CONTENT_MISMATCH / BUDGET |
| 7 | 断言 g=0 **summary** 在 required | G0_SUMMARY_REQUIRED |

**应索引谓词**：trim 后 body/content_full **非空**，且不是 g=0 original。
**g=0**：non-empty **summary** 必须 required；缺失 → fail。g=0 original 必须已装回在 construct，但不形成 VectorizationUnit。

**小结**：门闩可复验；闭包完整。

---

### 4.5 `S08-E05` — ContentFullRecipe 重算与预算

**真相**：S08-T012/T013；T-O-223/217

**执行台账**

```text
content_full = recipe_vN(
  optional_header: closed_set(S04 projection meta + optional unit title),
  body: channel_body
)
content_full_digest = H(content_full bytes)
if provided_digest and provided_digest != content_full_digest:
  fail VECTORIZE_CONTENT_MISMATCH
if over budget:
  fail VECTORIZE_BUDGET_*
```

| 规则 | 规范 |
|---|---|
| 重算 | **强制**（I1） |
| 截断 | **禁止**静默 substring 冒充成功（T1） |
| 非 identity | content_full 不进 unique 键（digest 可进列） |

**小结**：索引输入可审计。

---

### 4.6 `S08-E06` — 有界 batch、渐进 upsert、最终 gate

**真相**：S08-T014..T018；T-O-226

**执行台账 — 主循环**

```text
order units stably
for batch in bounded_batches(units):
  try:
    vectors = S11.embed(texts)
  except provider_limit:
    bisect batch and retry within S11 transport policy
  for each unit in batch:
    UPSERT mkb_vector_records (unique key)
    optional domain_event vector.unit_upserted (non-SSOT)
if succeeded_count == required_count:
  Outcome full_valid + Handoff
else:
  Outcome failed PARTIAL_REQUIRED (retryable)
```

| 规则 | 规范 |
|---|---|
| 失败半写 | **保留**；禁止补偿删 |
| 重试 | 同 digest 覆盖 upsert |
| skip re-embed | 同 unique + 同 content_digest+model 可跳过仍计完成 |
| 事件 | 非成功 SSOT |
| lease | 长跑 heartbeat（S03） |

**小结**：可扩展、可恢复、半写不可服务。

---

### 4.7 `S08-E07` — Original 装回 HARD

**真相**：S08-T024；T-O-224/227

**执行台账**

| 检查 | 失败 |
|---|---|
| construct 中 g=0 original unit 存在且已装回 | ORIGINAL_NOT_REATTACHED |
| body/content_full 非空（construct 侧） | 同上 |
| proof `reattach_status` ∈ {`reattached`,`native_full`}（若字段存在） | 同上 |
| 标记 detached / stripped | 禁止进入 vectorize |
| g=0 original **不**进入 required-set | — |
| g=0 summary 在 required | G0_SUMMARY_REQUIRED |

**禁止**：S08 从 clean Artifact 重切 original 充当权威（O-c）；全信标签不校验（O-b）。

**小结**：窗口剥离不得泄漏进向量。

---

### 4.8 `S08-E08` — Layer A 写路径

**真相**：S08-T019/T020/T025；T-O-218/214

**执行台账**

| 步 | 规范 |
|---|---|
| ensure namespace | team active namespace；model+dim 与 binding 一致 |
| embed | S11 only |
| upsert | embedding F32 + embedding_model + dimension + digests |
| 混模 | **拒绝** SPACE_*；禁 silent fallback |

**物理**：`mkb_vector_records.embedding`；禁 content_full 列；禁外置 Vectorize 作 v1 可写 SSOT。

**小结**：空间围栏 fail-closed。

---

### 4.9 `S08-E09` — Layer B 执行抄写（不覆盖 S04）

**真相**：S08-T026..T028；T-O-229；T-O-198

**分账 HARD**

```text
S04 = wire map / FacetDefinition / unknown 策略 / filter 权威
S08 = 抄写已解析值到可索引字段；零 map
```

**强制列族（每 record）**

| 字段 | 来源 |
|---|---|
| team_uuid | Command |
| intake_item_uuid | Command / S04 |
| intake_revision_uuid | Command / S04 |
| generation_artifact_uuid + type | dual_channel gen |
| block_or_unit_id | unit |
| channel | original \| summary |
| Layer A 字段 | E08 |

**Facet 抄写**

1. S04 权威有 `industry_domain`（等）→ **必须**写入可索引落点（列或 typed 结构；DDL 以 D04 为准）。
2. 权威无该键 → NULL；**不**读 Task wire；**不**发明。
3. 配置要求强制有值而缺失 → `FILTER_PROJECTION_*` / BINDING。
4. 禁止 payload_extra 当 filter SSOT；禁止模型发明键。

**industry-type 示例（引用 S04，非本域产品定义）**

```text
上游 industry-type=finance
  --(S04 FacetMap)--> industry_domain=finance @ Revision
  --(S08 抄写)------> mkb_vector_records 可过滤字段
  --(S10)----------> WHERE industry_domain = 'finance'
```

**小结**：检索可滤；权威不双源。

---

### 4.10 `S08-E10` — purge_generation 与 refresh 短路

**真相**：S08-T021..T023；T-O-227

**purge_generation**

| 规则 | 规范 |
|---|---|
| 范围 | command 指定 generation_artifact_uuid |
| 动作 | `deleted_at` soft-delete |
| channel_filter | all \| original \| summary |
| 不 | 删 S06/S07 artifact；改 Task/Intake lifecycle；drop namespace；默认物理 DELETE |

**refresh 后再向量化**

| 条件 | 行为 |
|---|---|
| 新 construct generation 且 content_full 相关 digest **变** | 必须新 outbox + from_construct |
| digest **未变** 且 model/namespace 未变 | 可 skip 全量 re-embed（或仅 Layer B 补丁） |
| 禁 | silent 混 embedding 空间；写成功自动 purge 全 item 历史 |

**小结**：世代显式；省成本短路可验收。

---

### 4.11 `S08-E11` — Outcome、Handoff、错误、Readiness、OOS

**真相**：S08-T008/T029..T033；T-O-228/230

**成功 Outcome / Handoff**

```text
disposition: full_valid
required_units, succeeded_units, skipped_empty_units
failed_units: []
namespace_uuid, embedding_model, dimension
generation_refs, content_full_recipe_version
outbox_dedupe_key?
# 可选：facet_keys_echo[] 非权威
# 禁止：正文、path、serving、PublicationProof、ANN params
```

**失败 Outcome**：typed error_code + retryability + partial_stats? + failed_units[]

**错误码**（§2 与 Q7 表；可增子码）见 S08-T031。

**Readiness=false 当**（S08-T032）：

1. 默认 local embed binding/catalog 不可用；
2. vector migration / native vector / ANN 能力缺失（D04/S12）；
3. namespace bootstrap 策略缺失且配置强制；
4. Vectorize contracts 未注册。

**OOS（S08-T033）**：无公网 vector CRUD；无 S08 内 ANN/serving；无 silent 跨 model；无 unit 微 Process；无 from_structure；无默认物理 hard-delete；无 S08 内 facet 产品 map。

**小结**：可编码运维合同。

---

### 4.12 `S08-E12` — 与邻域交接

| 邻域 | 合同 |
|---|---|
| S03 | 只消费 Outcome retryability；max_retries 属 S03；lease 覆盖长跑 |
| S07 | exact dual_channel + recipe；gate 原料 |
| S04 | filter 权威；S08 只抄写 |
| S11 | 只调 embed；E05/E09 |
| S12 | upsert TX、outbox claim、unique |
| S09 | Handoff → validate_publication；禁 S08 写 serving |
| S10 | 消费 records + Layer B；不在本域 |
| S15 | 低基数事件/指标；非 SSOT |

---

## 5. 事实反例 + 风险台账

### 5.1 反例（禁止方向）

| 反例 | 订正 |
|---|---|
| structurize 后直接 vectorize | T-O-212 门闩 |
| `smind_vec_process` / pending 表作 SSOT | artifact + outbox + records |
| content_full 进向量表 | digest + recipe |
| CF Vectorize / 独立 vec.db 作 v1 可写 SSOT | mkb_vector_records |
| zero-pending / callback / outbox done = 成功 | Outcome full_valid |
| partial unit 成功当 Process 成功 | T-O-222 |
| 静默截断 / skip 掉 g=0 | T1 + g=0 强制 |
| 失败补偿删半写 | 幂等保留 |
| 半写即可检索服务 | T-O-219 + S09 |
| S08 map industry-type | T-O-229；S04 |
| 模型发明 filter | S04 权威 |
| 换 embedding 模拟业务分区 | Layer A/B |
| S08 写 PublicationProof | S09 |
| process-local max_retries 账本 | S03 |

### 5.2 风险与围栏

| 风险 | 围栏 |
|---|---|
| 大文档 OOM/lease | 有界 batch + heartbeat |
| digest 短路误判 stale | digest 集合含 recipe+各 unit content_full+model |
| soft-delete 物理残留 | 声明 ≠ GDPR hard erase；S04/S15 |
| S09 延期导致半写误用 | publication 门闩；active view 过滤 |
| D04 缺 facet 列 | change-request；暂 typed 结构不破抄写合同 |

### 5.3 容量（默认量级，可配置，不可默认无界）

| 键 | 默认量级 | 超限 |
|---|---|---|
| `vectorize.max_units_per_process` | 50_000 | BUDGET |
| `vectorize.max_embed_batch_items` | 与 S11 对齐（保守） | 拆批 |
| `vectorize.max_content_full_bytes` | 与 S07 content_full 预算对齐 | BUDGET |

---

## 6. 测试与验收台账

| ID | HARD 不变量 | 证据类型 |
|---|---|---|
| S08-A01 | construct 未 full_valid 不能 full_valid vectorize | 集成 / 门闩单测 |
| S08-A02 | dual-channel required 缺一失败 | 集成 |
| S08-A03 | construct 中 g=0 original 缺失/stripped → fail；g=0 original 不在 required；缺 g=0 summary → fail | 单测 |
| S08-A04 | ContentFull 错 digest → CONTENT_MISMATCH | 单测 |
| S08-A05 | 同 command_input_digest 重放幂等 | 集成 |
| S08-A06 | 半写后失败 → 无 publication；重试覆盖成功 | 故障注入 |
| S08-A07 | outbox 重复投递不双成功分裂 | 集成 |
| S08-A08 | Layer A 混模拒绝 | 单测 |
| S08-A09 | 权威 industry_domain 有值则 record 可滤 | 集成 |
| S08-A10 | S08 不写 serving pointer | architecture / 集成 |
| S08-A11 | transport 429 不增加 process.retry_count 直至耗尽 | 与 S11 联测 |
| S08-A12 | purge_generation 只 soft-delete 指定 generation | 集成 |
| S08-A13 | services 不 import llm_adapters / db driver | architecture |
| S08-A14 | 零 smind_vec_process / content_full 列 | schema 扫描 |
| S08-A15 | 实现路径不读 qna-truth 作 SSOT | 文档/代码审查 |

**禁止**：用未来测试冒充已交付；用日志字符串当唯一失败证明。

---

## 7. Reference-anchor 台账

| Anchor | 路径（约） | 裁决 |
|---|---|---|
| VecProcess schema / 双通道行 | `smind-skill-rag-vectorizer/core/schemas_common.ts`；constructor `VecProcessSchema` | **删除** 表 SSOT；**保留** channel 枚举思想 |
| content_full 配方 | constructor `recorder.ts` buildContentFull | **升级** 为 ContentFullRecipe + 禁列表 |
| embedder 退避 | vectorizer `embedder.ts` | **升级** 归 S11；删 CF model |
| prepare batch/截断 | `prepare.ts` | **升级** 有界批；**删除** 静默截断成功 |
| engine claim/upsert/成功=zero pending | `engine.ts` / DO | **删除** 成功定义；**保留** upsert 幂等 |
| Vectorize upsert | `vector_db.ts` | **删除** CF 落点；**保留** upsert 语义 |
| Console DDL smind_vec_process | `smind-console/db/06-process-tracking.sql` | **删除** |
| Summarizer stash/reattach g=0 | constructor `summarizer.ts` | **升级** T-O-224/S08-E07 |
| Contexter traceback | contexter topK/db_d1 | **约束** 写侧坐标/channel（消费归 S10） |
| 业内 Outbox | microservices.io transactional-outbox | **保留** 模式 |
| 业内幂等向量写 | Qdrant points idempotence；Meltwater re-homing | **保留** 模式 |

---

## 8. Domain verdict

### 8.1 最终评价

S08-v1.0 将 progressive `T-O-211..230` 升格为 **唯一可编码执行真相**：门闩、整包成败、配方对账、有界幂等写、世代 soft-delete、原文装回、Layer B 抄写、错误/readiness、S09 handoff 均已闭包。与 S01/S02 同构的九段式可验收结构，并采用 S07/S11 级 E 包执行台账密度。

### 8.2 未解决边界（明确移交，非本域 blocker）

| 项 | 归属 |
|---|---|
| FacetDefinition / wire map / unknown 策略 | S04（+S14） |
| industry_domain 物理列 vs 子表 | D04 change-request（若缺） |
| ANN metric / topk / PublicationProof 算法 | S09 / G-09 |
| 查询 filter 入参 map | S10 |
| retention / 告警数值 | S15 |

### 8.3 对下游约束

- **S03**：注册 `lsrag.vectorize`；phase 可保留 `vectorizing_indexing` 但不包办 publication。
- **S07**：继续同 TX outbox；Handoff 消费面稳定。
- **S04**：facet map 产品 formal 可独立推进；S08 不 reopen。
- **S09**：必须消费 Handoff；过滤 soft-deleted。
- **S10**：Layer B 过滤依赖 S08 抄写完整性。
- **实现**：只读本文 + contracts + D04 DDL。

### 8.4 完成状态

**`accepted / S08-v1.0`** · progressive QNA **Round 4 waived** · 全系统 truth layer 仍待其余域闭合后统一 frozen。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 说明 |
|---|---|---|---|---|
| `S08-v1.0` | `2026-08-12` | `MKB owner + Codex` | `accepted` | 自 `qna-truth/S08.md v1.0`（`T-O-211..230`）升格唯一执行 SSOT；九段式 + E01–E12；Q8 执行写面不覆盖 S04；S09 handoff；Round 4 waived |
