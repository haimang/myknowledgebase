# S09 — Vector Index Lifecycle

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D6 向量资产 / S09 Vector Index Lifecycle`（索引·发布·代数·可服务谓词）
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S09 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S09-v1.0`
>
> **上游权威输入**：`D01–D05`、`S01–S08`、`S11–S13`；`qna-truth/S09.md v1.0`（**证据层 / progressive 中间态 only**，非执行 SSOT）；冻结 Truth `T-O-231..246`
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.6+
>
> **事实证据**：`context/legacy-family/` 仅作 ReferenceAnchor（Vectorizer、Contexter、RAG Dispatcher、Console DDL）；网络 Reference-Check（dual-write / dual-index / ES alias / tombstone）仅作设计对照；**禁止** `legacy-specs` / `legacy-python` 作为本域证据源
>
> **下游消费者**：`S03`、`S04`、`S08`、`S10`、`S12`、`S14–S15`、跨系统拓扑 `17`、验收冻结 `18`、实现与 architecture tests

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S09.md` 仅保留 progressive 形成过程（`T-O-231..246` 冻结轨迹），**不得**被引用为第二执行真相；冲突时 **以本文为准**。禁止「细节在 QNA、Spec 只写原则」。实现 **无需** 打开 QNA 即可编码。

> **★ 约束级别**：「必须 / 禁止 / 仅允许」= 强制；「应当」= 默认，偏离须 reopen S09；「可以 / 建议」= 非冻结不变量。

> **Owner 产品边界**：S09 是 **document-side 索引生命周期与 publication 域**。在 S08 写证明之后，对 required-set 做可发布对账，产出 **PublicationProof**，管理 **IndexGeneration / ActiveIndexPointer**，定义 **可服务谓词** 与 **invalidation**，并钉 **ANN/metric/topk 默认与硬上限**。**不**拥有：向量 body 写编排（S08）；Item lifecycle / serving CAS（S04）；召回 Traceback/Rerank（S10）；Process 八态/`max_retries`（S03/D01）；facet 产品 map（S04）；prompt 正文（D05/S14）；推理 transport（S11）。

> **S08 分账（T-O-230/241）**：`VectorizeHandoffV1` = 写证明 binding；**存在行 ≠ serving**；半写禁 publication。S09 独立 Process `index.validate_publication`。

> **S04 分账（T-O-242/244）**：serving_revision CAS **仅 S04**；S09 提供 type-specific PublicationProof 与投影；dual fence 的关系侧属 S04 `IntakeEligibilityPort`。

> **S10 分账（T-O-244/245）**：必须应用 S09 可服务谓词与 topK hard cap；拥有 score threshold / diversify / channel / rerank 策略。

> **D04/S12 分账**：`mkb_vector_records` / `mkb_vector_namespaces` / ANN **存在性** / VIEW 以 D04 为准；TX/outbox/claim/readiness probe 以 S12 为准；S09 钉 **算法、指针、对账、谓词、写权**；**禁止**第二可写向量库或绕过 D04 表闭集的私有 SSOT（T-O-178）。ActiveIndexPointer / PublicationProof 物理表以实现时 D04 additive migration 落地（见 §4.2）。

> **S11 分账**：Layer A 空间隔离；query embed 与 namespace model/dim 必须匹配。

> **Legacy 边界（T-O-240）**：不继承 CF Vectorize 可写 SSOT、`smind_vec_process`、存在即发布、namespace 只 log、`purge_before_write` 空转、zero-pending/callback=成功。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S09 把 **已写入同库的向量行** 变成 **可证明、可切流、可撤回、可检索资格围栏下的索引资产**，并保证：

1. 半写与 Handoff  alone **不能** 上线；  
2. PublicationProof 可被 S04 serving CAS 消费；  
3. 多 generation 可物理共存但 **仅 active 代数** 进入服务谓词；  
4. deactivate/delete 能 **快速撤回投影** 而不假恢复 serving；  
5. metric/topk 有安全默认与硬上限，且与 S10 分账；  
6. 实现者 **无需** 打开 QNA 即可编码与验收。

### 1.2 在整体拓扑中的位置

```text
S08 lsrag.vectorize full_valid
  │ VectorizeHandoffV1 + mkb_vector_records (may retain half-writes of older runs)
  ▼
S03 Process: index.validate_publication
  │ mode=validate_from_vectorize_handoff
  ▼
S09 Publication
  ├── Bind Handoff digests (binding ≠ proof)
  ├── Scan mkb_vector_records → actual set
  ├── Required-set reconcile (whole-package)
  ├── Write PublicationProofV1 + publication_state projection
  ├── CAS ActiveIndexPointer (candidate → active) [when cutover]
  └── ProcessOutcome full_valid + proof_ref
  │
  ▼
S04 serving CAS (consumes PublicationProof; never written by S09)
  │
  ▼
S10 retrieve
  ├── Layer A space match
  ├── ANN top_k (≤ max_topk)
  ├── S09 publication-valid predicate
  └── S04 IntakeEligibilityPort
```

### 1.3 Scope fence

**S09 负责：**

- ProcessCapability `index.validate_publication` 与 `index.rebuild` 执行合同；  
- ProcessCommand / ProcessOutcome / `command_input_digest`；  
- Handoff 绑定 + required-set 对账算法；  
- PublicationProofV1 形态与写权；  
- `publication_state` 投影语义（仍 ≠ serving）；  
- IndexGeneration / ActiveIndexPointer CAS 与 lifecycle；  
- rebuild 五段协议（对齐 S04-T034）；  
- 可服务谓词与 invalidation/withdraw；  
- distance_metric 默认、topK default/hard cap、ANN 默认路径；  
- 错误码 / readiness / 最小容量 / OOS；  
- 与 S04 CleanupProof 的 vector substrate 配合。

**S09 不负责：**

| 排除项 | 归属 |
|---|---|
| Task/Execution/Process 状态机与 max_retries 账本 | D01 / S03 |
| 向量 embed / upsert / ContentFull 对账 | S08 |
| filter/facet 产品定义与 wire map | **S04** |
| Item lifecycle / serving_revision CAS | **S04** |
| Traceback / Rerank / ContextTier / answer | S10 |
| DDL 表闭集最终枚举（additive 须回填 D04） | D04 |
| outbox/claim/TX 引擎 | S12 |
| embed transport | S11 |
| retention 天数 / alert 阈值 | S15 |
| prompt 正文 | D03 / S14 |

### 1.4 身份与关键对象

| 对象 | 定义 | 非定义 |
|---|---|---|
| **VectorizeHandoffV1** | S08 Outcome 写证明；S09 **binding** 输入 | **非** PublicationProof |
| **PublicationProofV1** | 类型化上线证据；S04 CAS 输入 | 非 queue ACK；非单 vector 存在 |
| **IndexGeneration** | `(team, item, namespace)` 单调投影代数 | 非 IntakeRevision；非 S06 current |
| **ActiveIndexPointer** | CAS 保护的 active 代数路由（≈ read alias） | 非 `serving_revision` |
| **Publication-valid predicate** | 索引侧可进入 S10 的最小关系谓词 | 非完整业务 eligibility |
| **FinalVectorBody** | 仍为 `mkb_vector_records.embedding`（D04） | 非外置索引 SSOT |

### 1.5 完成定义

1. §2 全部 Truth 被 contracts、迁移与 transition 实现；  
2. 无 Proof / 半包 **不可** 被 S10 当可服务；  
3. ActiveIndexPointer CAS 与 multi-gen grace 可验收；  
4. invalidation 使 deactivate 后 dual fence 拒绝返回；  
5. topK 硬上限与 cosine 默认可配置可测；  
6. 零 legacy vectorize 发布语义依赖；  
7. 实现 **无需** 打开 QNA；  
8. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O · S09 段 · 执行摘要）

| Truth-ID | 摘要 | 本域强制 |
|---|---|---|
| `T-O-231` | S09 = 索引生命周期域；不吞 S08/S04/S10 | scope |
| `T-O-232` | `index.validate_publication` 独立；禁 vectorize_index 生产键 | capability |
| `T-O-233` | 存在 ≠ serving ≠ Proof；Handoff ≠ Proof | fence |
| `T-O-234` | D04 substrate only；禁外置可写 SSOT | physical |
| `T-O-235` | 双围栏；禁仅 ANN 返回 | fence path |
| `T-O-236` | soft-delete 排除；半写禁 publication | set |
| `T-O-237` | Layer A/B；S09 不 map facet | filter |
| `T-O-238` | 成功仅 Outcome(+Proof) | success |
| `T-O-239` | ActiveIndexPointer 独立 SelectionPointer | pointer |
| `T-O-240` | legacy-family only；greenfield | evidence |
| `T-O-241` | Handoff binding + records 整包对账 + 三元组 | validate |
| `T-O-242` | PublicationProofV1 + 投影；禁写 serving | proof |
| `T-O-243` | ActiveIndexPointer + 多代 grace + rebuild 五段 | generation |
| `T-O-244` | 可服务谓词 + invalidation | serve/invalidate |
| `T-O-245` | cosine；topK default/cap vs S10 | metric/topk |
| `T-O-246` | 错误/readiness/容量/OOS；R3 waived | ops/closure |

### 2.2 域内 Truth 编号（S09-T）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S09-T001` | 生产 ProcessCapability：`index.validate_publication`；独立于 `lsrag.vectorize`。 | T-O-232 | registry exact key |
| `S09-T002` | 受控 ProcessCapability：`index.rebuild`；scope 由 Command 闭集表达。 | T-O-232/243 | 非 Task type |
| `S09-T003` | 禁止生产键 `lsrag.vectorize_index`；phase 名不是 Process。 | T-O-232 | |
| `S09-T004` | v1 主 mode：`validate_from_vectorize_handoff`。 | T-O-241 | |
| `S09-T005` | Handoff 是 binding 非 proof；必须校验 disposition/generation/namespace/model digests。 | T-O-241/233 | |
| `S09-T006` | Actual = 扫 `mkb_vector_records`（`deleted_at IS NULL` + Layer A）。 | T-O-241 | |
| `S09-T007` | required-set 与 S08 同构；整包全部 matched 才成功。 | T-O-241/222 | |
| `S09-T008` | Outcome 必报 `expected_count/actual_count/matched_count`。 | T-O-241 | |
| `S09-T009` | 禁止：partial success；Handoff-only；ANN 抽样代替对账；补偿删半写。 | T-O-241 | |
| `S09-T010` | materialize 后 `command_input_digest` 冻结（含 mode+handoff+generation+model+namespace+index_generation 目标）。 | T-O-241 | |
| `S09-T011` | 成功必须 durable **PublicationProofV1**（`index.publication.v1`）。 | T-O-242 | |
| `S09-T012` | Proof 最小字段：见 §4.4；禁 embedding 正文/path/serving 新值。 | T-O-242 | |
| `S09-T013` | S09 可写：Proof + 本集 `publication_state` 投影。 | T-O-242 | |
| `S09-T014` | **禁止** S09 写 `intake_items.serving_revision_uuid`。 | T-O-242 | architecture |
| `S09-T015` | 时序：validate+Proof → S04 CAS serving → S10。 | T-O-242 | |
| `S09-T016` | S04 CAS 失败：保留 Proof 与旧 serving；不自动删 candidate。 | T-O-242 | |
| `S09-T017` | `publication_state` / `mkb_v_vectors_active` **≠** serving 资格。 | T-O-233/242 | |
| `S09-T018` | IndexGeneration 粒度：`(team_uuid, intake_item_uuid, namespace_uuid)`。 | T-O-243 | |
| `S09-T019` | ActiveIndexPointer CAS 为 item×namespace 路由 SSOT。 | T-O-243/239 | |
| `S09-T020` | records.`index_generation` = 投影代数；namespaces.`index_generation` = 空间级重建。 | T-O-243 | |
| `S09-T021` | lifecycle：`building→validating→ready_candidate→active→retiring→soft_purged`（v1 可折叠 building+validating）。 | T-O-243 | |
| `S09-T022` | 首发 0→1 或无 active→1；其后 candidate=active+1。 | T-O-243 | |
| `S09-T023` | cutover：CAS active → grace → soft-delete 旧代；失败 active 不变。 | T-O-243 | |
| `S09-T024` | rebuild 五段：build→validate→CAS→grace→purge old；不创建 IntakeRevision。 | T-O-243；S04-T034 | |
| `S09-T025` | S08 `purge_generation` 与 S09 旧 index 代 purge intent **不合并**。 | T-O-243 | |
| `S09-T026` | 禁止：无代数全可搜；写成功自动 purge 旧代；Revision 冒充 index gen；cutover 后立刻物理删旧。 | T-O-243 | |
| `S09-T027` | Publication-valid 谓词：§4.7 B1 全集；S10 必须应用。 | T-O-244 | |
| `S09-T028` | 禁止仅凭 ANN 命中返回业务结果。 | T-O-235/244 | |
| `S09-T029` | invalidation 表：§4.7；不反向恢复 serving；不默认同步 hard-delete。 | T-O-244 | |
| `S09-T030` | validating 中 CLEAR_SERVING → 中止/fail promote。 | T-O-244 | |
| `S09-T031` | 默认 `distance_metric=cosine`；变更 controlled。 | T-O-245 | |
| `S09-T032` | ANN 默认检索路径；exact 默认关。 | T-O-245 | |
| `S09-T033` | default topK=10；max_topk 配置化（建议默认 100）。 | T-O-245 | |
| `S09-T034` | S10 可 override topK≤cap 与 threshold/rerank；禁客户端换 metric。 | T-O-245 | |
| `S09-T035` | 错误前缀闭集 §4.9；S03 只消费 retryability。 | T-O-246 | |
| `S09-T036` | readiness 条件 §4.9；≠ liveness。 | T-O-246 | |
| `S09-T037` | 容量 soft/hard 配置化；hard fail-loud。 | T-O-246 | |
| `S09-T038` | OOS 清单 §4.9。 | T-O-246 | |
| `S09-T039` | 成功 **仅** Outcome + Proof（当域要求）；禁 outbox done/callback/zero-pending。 | T-O-238 | |
| `S09-T040` | 不新增 StateFamily；publication 是 phase/capability 不是第七状态。 | D02 | |
| `S09-T041` | 幂等：同 `(execution, capability, command_input_digest)` 收敛同一逻辑结果或 conflict。 | T-O-241 | |
| `S09-T042` | 进度事件非 SSOT。 | — | |
| `S09-T043` | scatter = 每内容 child 独立 publication；root 不跨 Item 合包 proof。 | 继承 S02/S07 | |
| `S09-T044` | Final body 仍 D04 records；S09 不改落点。 | T-O-234 | |
| `S09-T045` | 域事件种类：`index.publication_succeeded`、`index.withdrawn`、`index.generation_promoted`、`index.generation_retired`、`index.cleanup_proof_submitted`、`index.rebuild_started`（低基数；S15 保留策略）。 | T-O-244/246 | |

### 2.3 继承上游（不重开）

- **D01/S03**：Process 八态、claim/fence、max_retries、Outcome 上卷。  
- **S08**：Handoff、半写纪律、soft-delete、Layer B 抄写结果。  
- **S04**：serving CAS、四意图、CleanupPort、dual fence 关系侧。  
- **D04/S12**：vector 表、ANN 存在、outbox、TX、引擎 readiness。  
- **S11**：Layer A。  
- **D02**：SelectionPointer 分账。  
- **D05**：ConstructToVectorizeGate 上游合法原料（S09 不接受 structure 直通 handoff）。

---

## 3. 总体方案陈述

1. **写与发布分离**：S08 写行；S09 证明可发布。  
2. **Handoff 绑定 + 库扫对账**：不信单侧成功标志（dual-write 纪律）。  
3. **整包 required-set**：与 S08 full_valid 同构。  
4. **Durable Proof + 投影**：控制面 promote 记录；业务 serving 归 S04。  
5. **Active 指针 ≈ alias**：多代共存 + grace 回滚。  
6. **谓词闭合**：S10 不得跳过 publication-valid 与 eligibility。  
7. **Invalidation 快路径投影**：withdrawn/soft-delete；非默认同步 hard-delete。  
8. **参数分账**：S09 默认与硬上限；S10 查询策略。  
9. **失败归 S03**：无私有 max_retries。  
10. **QNA 零依赖**：执行细节全部在本文 §4 E 包。

---

## 4. 具体执行方案清单

### 4.1 `S09-E01` — Capability、mode 与目录落点

**真相**：S09-T001..T004；T-O-232

| 项 | 规范 |
|---|---|
| capability | `index.validate_publication`（生产主路径） |
| capability | `index.rebuild`（受控 rebuild） |
| mode（validate） | `validate_from_vectorize_handoff`（v1 必选主路径） |
| 禁止 | 生产 `lsrag.vectorize_index`；把 publication 并进 S08 Outcome |
| 代码落点 | `src/services/` 内 index/publication handler；编排 `src/runtime/` |
| contracts | `src/contracts/index/`：Command、Outcome、PublicationProof、ActiveIndexPointer、SearchDefaults、Error |

**小结**：单点 capability 身份，与 S08 对称。

---

### 4.2 `S09-E02` — 物理存放与 D04 接合

**真相**：S09-T019/T011/T044；T-O-234/178

**已冻 D04（只消费）**

- `mkb_vector_namespaces`、`mkb_vector_records`、`vec_idx_*`、`mkb_v_vectors_active`  
- `publication_state`、`index_generation` 列语义

**S09 逻辑 SSOT → 物理落地（实现义务）**

| 逻辑对象 | 物理策略 |
|---|---|
| ActiveIndexPointer | **required** 表 `mkb_index_active_pointers`（D04 vector 模块 **additive** migration；并回填 D04 闭集版本） |
| PublicationProofV1 | **required** 表 `mkb_publication_proofs` **或** 等价 durable proof store（同库；ref 进 Outcome/S04）；禁止仅日志 |
| domain_events | 已有 `mkb_domain_events`；写入种类见 S09-T045 |

**`mkb_index_active_pointers` 最小列**

```text
team_uuid, intake_item_uuid, namespace_uuid
active_index_generation INTEGER NOT NULL
pointer_row_revision INTEGER NOT NULL   -- CAS
lifecycle_state TEXT  -- building|validating|ready_candidate|active|retiring|...
candidate_index_generation INTEGER NULL
last_proof_uuid TEXT NULL
updated_at TEXT NOT NULL
UNIQUE(team_uuid, intake_item_uuid, namespace_uuid)
```

**`mkb_publication_proofs` 最小列**

```text
proof_uuid PK
proof_type = 'index.publication.v1'
proof_version, team_uuid
intake_item_uuid, intake_revision_uuid
execution_uuid, process_uuid
generation_artifact_uuid, generation_artifact_type
namespace_uuid, embedding_model, dimension
index_generation
expected_count, actual_count, matched_count
required_set_digest, actual_set_digest
command_input_digest
layer_a_json, layer_b_keys_echo_json
created_at
payload_extra DEFAULT '{}'
```

**小结**：算法 SSOT 在 S09；表名进入 D04 闭集的 additive 回填是实现门禁，不是「可省略」。

---

### 4.3 `S09-E03` — ProcessCommand 与 command_input_digest

**真相**：S09-T005/T010；T-O-241

**`index.validate_publication` Command 最低闭集**

```text
mode: validate_from_vectorize_handoff
team_uuid, execution_uuid, process_uuid
intake_item_uuid, intake_revision_uuid
dual_channel_generation_ref + digests
namespace_uuid, embedding_model, dimension
handoff_snapshot: VectorizeHandoffV1 fields
target_index_generation: integer   # candidate 代数
# 禁止：正文、path、ANN 调参、直接写 serving_revision
```

**`index.rebuild` Command 最低闭集**

```text
scope: intake_item_uuid + namespace_uuid
optional: intake_revision_uuid pin, channel_filter, generation_artifact_uuid
policy: grace_duration_ref, purge_old=true|false
# 不创建 IntakeRevision
```

materialize 后冻结 `command_input_digest`；retry 同 digest。

---

### 4.4 `S09-E04` — 对账算法（validate）

**真相**：S09-T005..T009；T-O-241

**步骤**

```text
1. Load & verify Handoff binding (disposition, digests, model, namespace, required_units)
2. Enumerate expected required-set (S08-isomorphic; g=0 **summary** required, g=0 original excluded; T-O-352)
3. Scan actual rows:
     deleted_at IS NULL
     generation_artifact_uuid / namespace / model match
     optional candidate index_generation filter
4. For each required coordinate×channel:
     exists ∧ digest match ∧ Layer A ∧ mandatory Layer B pins
5. If all matched:
     TX: insert PublicationProofV1
         update matched rows publication_state='indexed' (if needed)
         optional pointer lifecycle → ready_candidate
     Outcome full_valid + proof_ref + triples
6. Else:
     Outcome failed + PUBLISH_* + partial_stats?
     NO promotion; NO compensatory delete of half-writes
```

**禁止**

- Handoff-only success  
- topK probe as sole proof  
- partial publication success  

---

### 4.5 `S09-E05` — PublicationProof 与写权

**真相**：S09-T011..T017；T-O-242

| 写目标 | Owner | 规则 |
|---|---|---|
| PublicationProof 行 | S09 | 成功路径必须 |
| records.publication_state | S09 投影 | 成功 indexed；withdraw 路径 withdrawn |
| ActiveIndexPointer | S09 | cutover/rebuild |
| serving_revision | **S04 only** | S09 禁止 |
| Task/Execution status | S03 | 收 Outcome |

**S04 时序**

```text
S09 Outcome full_valid + proof_ref
  → Engine/Workflow hands proof to S04 publication action
  → S04 validates proof type/version/target/expected pointers
  → CAS serving_revision (fail → old serving kept)
```

---

### 4.6 `S09-E06` — IndexGeneration 与 rebuild

**真相**：S09-T018..T026；T-O-243

**正常 cutover**

```text
candidate = active+1 (or first publish → 1)
vectorize writes rows tagged candidate gen (or gen assigned at validate)
validate_publication on candidate
CAS ActiveIndexPointer: expected=old → active=candidate
grace window (config)
soft-delete rows where index_generation < active (or = old)
lifecycle: active / retiring / soft_purged
```

**rebuild 五段**（S04-T034）

1. build（触发/等待 S08 路径产出 candidate）  
2. validate（本域）  
3. CAS active  
4. grace  
5. purge old（soft-delete + CleanupProof 若需要）  

fail → active 不变。

**与 S08 purge**

| Intent | 键 | Owner |
|---|---|---|
| purge_generation | generation_artifact_uuid | S08 |
| retire old index gen | index_generation | S09 |
| physical_purge | S04 eligibility | S04/S15 |

---

### 4.7 `S09-E07` — 可服务谓词与 invalidation

**真相**：S09-T027..T030；T-O-244

**Publication-valid 最小谓词（强制）**

```text
team_uuid = :team
AND deleted_at IS NULL
AND publication_state = 'indexed'
AND namespace.status = 'active'
AND embedding_model / dimension match query Layer A
AND index_generation = ActiveIndexPointer.active
AND intake_item_uuid / intake_revision_uuid pins (as provided)
-- THEN S04 IntakeEligibilityPort(lifecycle, serving_revision, team)
-- FORBIDDEN: return on ANN hit alone
```

**Invalidation**

| S04 意图 | S09 |
|---|---|
| CLEAR_SERVING / deactivate | `publication_state→withdrawn`（本 item 相关可服务集）；可选 grace soft-delete |
| delete + tombstone | withdrawn + CleanupIntent；soft-delete；提交 CleanupProof |
| rebuild | §4.6 |
| physical_purge | 仅 eligibility 后；默认非同步 hard-delete |

**并发**：validating + CLEAR → fail/abort promote（`PUBLISH_WITHDRAWN_*` / pointer CAS fail）。

---

### 4.8 `S09-E08` — Metric / topK / 检索端口默认

**真相**：S09-T031..T034；T-O-245

| 参数 | 默认 | Owner |
|---|---|---|
| distance_metric | `cosine` | S09 / namespace 行 |
| ANN path | on | S09 |
| exact/brute | off | ops switch |
| default top_k | 10 | S09 |
| max_topk | 100（可配置） | S09 hard cap |
| score threshold | — | **S10** |
| rerank | — | **S10** |
| ef/lists | engine safe default | config / S14 可版本化 |

**VectorSearchRequest（索引端口；S10 调用）**

```text
team_uuid
namespace_uuid | namespace_key
query_embedding (dim match)
top_k: 1..max_topk
filters: Layer B pins (team forced)
index_generation?: default active
# 禁止：client distance_metric override
# 禁止：skip publication-valid predicate
```

---

### 4.9 `S09-E09` — Outcome、错误、Readiness、容量、OOS

**真相**：S09-T035..T039；T-O-246

**成功 Outcome 最小**

```text
disposition: full_valid
expected_count, actual_count, matched_count
publication_proof_ref, proof_digest
namespace_uuid, embedding_model, dimension
index_generation (promoted or validated candidate)
generation_refs
# 禁止：serving_revision 写入、ANN raw dumps as sole proof
```

**错误前缀**

| 前缀 | 默认 retryability |
|---|---|
| `PUBLISH_BINDING_*` | non_retryable |
| `PUBLISH_HANDOFF_INVALID` | non_retryable / dependency |
| `PUBLISH_MISSING_UNIT` | retryable |
| `PUBLISH_DIGEST_MISMATCH` | non_retryable |
| `PUBLISH_SPACE_*` | non_retryable |
| `PUBLISH_FILTER_*` | non_retryable |
| `PUBLISH_PARTIAL_REQUIRED` | retryable |
| `PUBLISH_PROOF_*` | retryable |
| `PUBLISH_POINTER_CAS_*` | retryable |
| `PUBLISH_WITHDRAWN_*` | non_retryable |
| `REBUILD_*` | 按子码 |
| `INDEX_CAPACITY_*` | non_retryable 或 deferred |
| `INDEX_DEPENDENCY_*` | dependency |

**Readiness=false 当**

1. S12 native vector / ANN probe 失败；  
2. publication/rebuild contracts 未注册；  
3. ActiveIndexPointer 表/策略缺失且配置强制；  
4. namespace bootstrap 缺失且配置强制；  
5. hard capacity 突破且策略 fail-closed。

**容量**

- soft_limit → 事件/指标（S15）  
- hard_limit → `INDEX_CAPACITY_*` fail-loud  
- 精确商业 SLO 数字 **不** 在本 Spec 写死  

**OOS**

- 公网 vector CRUD  
- 外置可写向量 SSOT  
- v1 强制 shadow/canary 平台  
- S09 内 Traceback/Rerank/answer  
- facet wire map  
- process-local max_retries  
- deactivate 默认同步 hard-delete  

---

### 4.10 `S09-E10` — 与邻域交接

| 邻域 | 合同 |
|---|---|
| S08 | 消费 Handoff；过滤 soft-deleted；不写向量 body |
| S03 | Outcome + retryability；lease 覆盖长对账 |
| S04 | Proof 输入 CAS；CleanupProof；eligibility |
| S10 | 谓词 + max_topk + 默认 topK；策略归 S10 |
| S11 | Layer A 匹配 |
| S12 | TX、proof/pointer 表 migration、ANN probe |
| S15 | 事件/容量指标；非 SSOT |
| S14 | 可选版本化 max_topk / grace / ANN knobs |

---

## 5. 事实反例 + 风险台账

### 5.1 反例（禁止方向）

| 反例 | 订正 |
|---|---|
| 有向量即可搜 | T-O-233/244 |
| Handoff 当 Proof | T-O-241/242 |
| S08/S09 合并 Process | T-O-232 |
| S09 写 serving_revision | T-O-242 |
| 无代数全可搜 / 僵尸向量 | T-O-243 |
| purge_before_write 空转 | T-O-240/243 |
| 只数 pending=成功 | T-O-238 |
| 客户端任意 metric | T-O-245 |
| 仅 ANN 返回 | T-O-244 |
| 私有 max_retries | T-O-246 |
| 外置 Vectorize 可写 SSOT | T-O-234 |
| partial cutover | T-O-241 |

### 5.2 风险与围栏

| 风险 | 围栏 |
|---|---|
| 默认 publication_state=indexed 误放行 | 对账重验 + 谓词 + active gen |
| 三义 index_generation | T-O-243 分账 |
| S04 CAS 与 pointer 竞态 | 有序时序；CAS expected |
| 半写残留 | 禁 publication；谓词排除 |
| topK 双源 | S09 cap / S10 策略 |
| D04 缺 pointer 表 | E02 additive migration 门禁 |

### 5.3 容量（默认量级，可配置，不可默认无界）

| 项 | 建议默认（非商业 SLO） |
|---|---|
| max_topk | 100 |
| default top_k | 10 |
| grace | 配置化（如小时级） |
| soft/hard vector count | 部署配置 |

---

## 6. 测试与验收台账

| ID | 场景 | 类型 |
|---|---|---|
| S09-A01 | Handoff full_valid + 全量行 → Proof + triples | 集成 |
| S09-A02 | 缺 unit → PUBLISH_MISSING_UNIT；无 Proof 提升 | 故障 |
| S09-A03 | Handoff 与库 digest 漂移 → fail | 故障 |
| S09-A04 | 半写 generation 不可 publication | 故障 |
| S09-A05 | S09 不写 serving_revision | architecture |
| S09-A06 | S04 CAS 失败保留旧 serving + Proof 仍在 | 集成 |
| S09-A07 | candidate CAS active 后谓词只见新 gen | 集成 |
| S09-A08 | grace 前旧 gen 不可服务；后 soft-deleted | 集成 |
| S09-A09 | rebuild 失败 active 不变 | 故障 |
| S09-A10 | deactivate → withdrawn；S10 双围栏拒绝 | 集成 |
| S09-A11 | top_k > max_topk 拒绝 | 合同 |
| S09-A12 | 客户端 metric override 拒绝 | 合同 |
| S09-A13 | soft-deleted 不计入 actual | 单元 |
| S09-A14 | Layer A 不匹配 fail | 单元 |
| S09-A15 | 幂等同 digest 重放 | 集成 |
| S09-A16 | ANN 缺失 readiness=false | readiness |
| S09-A17 | hard capacity fail-loud | 容量 |
| S09-A18 | 禁仅 ANN 命中返回（缺谓词） | architecture |
| S09-A19 | S08 purge vs S09 retire intent 分离 | 集成 |
| S09-A20 | scatter 子 Execution 独立 proof | 集成 |

**必须留存证据**：contract schema、migration SQL、对账 golden fixtures、CAS 并发报告、谓词 SQL/计划、错误码表。

---

## 7. Reference-anchor 台账

### 7.1 权威文档锚

- `qna-truth/S09.md` v1.0（`T-O-231..246` 轨迹）  
- `S08-v1.0`、`S04` serving/proof、`D04` vector 模块、`S12` readiness  
- `spec-glossary` PublicationProof / VectorizeHandoffV1 / IndexGeneration  

### 7.2 Legacy 代码事实锚（ReferenceAnchor only）

| 组件 | 用途 |
|---|---|
| Vectorizer engine/WAL/upsert | 写路径反例（存在即发布） |
| Contexter topK/hydrate | 读路径无 status 门闩反例 |
| Dispatcher purge/restart | purge_before_write 空转反例 |
| Console `smind_vec_process` | 禁 vec_process SSOT |

### 7.3 网络对照（非 Truth，设计验证）

| ID | 主题 | URL |
|---|---|---|
| W1 | Dual-write / outbox | https://www.confluent.io/blog/dual-write-problem/ |
| W2 | Dual-index migration | https://agentengineeringdigest.com/knowledge-base/retrieval-and-rag/dual-index-migration-pattern-for-embedding-model-changes/ |
| W3 | Embedding versioning | https://agentengineeringdigest.com/knowledge-base/retrieval-and-rag/embedding-versioning-for-vector-databases/ |
| W4 | ES zero-downtime reindex | https://tuleism.github.io/blog/2021/elasticsearch-zero-downtime-reindex/ |
| W5 | ES alias | https://discuss.elastic.co/t/zero-downtime-reindexing/15885 |
| W6 | Tombstone / soft-delete | https://www.profitec-ai.com/blog/rag-right-to-erasure |
| W7 | Delete fast-path | https://datavidhya.com/learn/ai-for-data-engineering/ai-de-system-design/design-enterprise-rag-system/ |
| W8 | Qdrant collections | https://qdrant.tech/documentation/manage-data/collections/ |
| W9 | SRE canary | https://sre.google/workbook/canarying-releases/ |
| W10 | Azure Search metrics | https://learn.microsoft.com/en-us/azure/search/monitor-azure-cognitive-search-data-reference |

### 7.4 证据使用判定

- legacy / 网络 **不得** 成为运行时依赖或兼容目标。  
- 仅用于正/反例与验收启发。

---

## 8. Domain verdict

### 8.1 最终评价

S09-v1.0 将 progressive `T-O-231..246` 升格为 **唯一可编码执行真相**：对账、Proof、代数切流、可服务谓词、invalidation、metric/topk、错误/readiness/OOS 均已闭包。与 S01/S02 同构的九段式可验收结构，并采用 S08 级 E 包执行台账密度。

**`ACCEPTED / GO`**

### 8.2 未解决边界（明确移交，非本域 blocker）

| 主题 | 归属 |
|---|---|
| Traceback / Rerank / ContextTier | **S10-v1.0 accepted** |
| Facet wire map | S04 |
| ActiveIndexPointer 表并入 D04 闭集版本号 bump | D04 calibrate |
| 精确容量商业 SLO / 告警阈值 | S15 |
| shadow 流量评测平台 | 可选后续 / OOS |
| ANN ef 细调运维手册 | S14/S15 |

### 8.3 对下游约束

- **S03**：注册 `index.validate_publication` / `index.rebuild`；phase 不合并 Process。  
- **S04**：消费 `index.publication.v1`；eligibility 联合 active gen。  
- **S08**：Handoff 字段稳定；不写 Proof/serving。  
- **S10**：强制谓词 + max_topk。  
- **S12/D04**：pointer/proof additive migration + ANN readiness。  
- **G-09**：同库 ANN 参数策略由本 Spec 收口起步；benchmark 曲线可与 S15 共治。

### 8.4 完成状态

| 项 | 状态 |
|---|---|
| QNA progressive | **locked / Round 3 waived** |
| Formal Spec | **S09-v1.0 accepted** |
| 执行 SSOT | **本文 only** |

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 变更 |
|---|---|---|---|---|
| `S09-v1.0` | `2026-08-12` | `MKB owner + Codex` | `accepted` | 自 `qna-truth/S09.md v1.0`（`T-O-231..246`）升格唯一执行 SSOT；九段式 + E01–E10；对账/Proof/代数/谓词/metric/运维闭包；Round 3 waived |
