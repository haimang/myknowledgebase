# S12 — Turso Persistence

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`F1 数据基础 / S12 Turso Persistence`
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S12 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S12-v1.1`（v1.0 宪法 + **执行台账全面升格**；QNA 细节并入本文）
>
> **上游权威输入**：`D01–D04`、`S01–S07`、`S11`、`S13`；`qna-truth/S12.md v1.0`（**证据层 / 中间态 only**，非执行 SSOT）
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.1
>
> **事实证据**：Turso Concurrent Writes / Native Vector / Embedded Replicas（能力前提）；`legacy-family` D1/DO/索引模式；`legacy-python` claim/VIEW（仅 ReferenceAnchor）
>
> **下游消费者**：全部 domain repository 实现、`S07–S11`、`S13–S16`、跨系统拓扑 `17`、验收冻结 `18`

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件** 与 **D04 物理 DDL**。`qna-truth/S12.md` 仅 progressive 证据，**不得**作第二执行真相。表名/列/索引以 **D04** 为准；本文钉死 **Ports、TX 语义、outbox/claim 步骤、migration/readiness、模块职责**。禁止「细节在 QNA、Spec 只写原则」。

> **Owner 约束**：选用 **Turso**；**默认启用 Concurrent Writes 与 Native Vector**；v1 **单主库**；拒 PostgreSQL；队列+DB fork 扩写 **defer**。

> **跨文档**：S12 **不**拥有业务状态机；只兑现已冻合同的物理事务。冲突时 fail-closed 或 reopen，禁止用“库做不到”静默改状态机。S13 拥有 object Port/layout/GC；S12 拥有 catalog 表 migration 与 bytes-first TX 接合。S11 消费 catalog/bindings/invocations 与 vectorize 路径。

> **D05校准声明（T-O-206）**：`vectorize_construct` outbox 意图仅在 S07 ConstructToVectorizeGate 通过后入队；S12 兑现 outbox/TX，不裁决业务门闩。prompt 正文不在 S12。

> **S08校准声明（2026-08-12）**：`S08-v1.0` 拥有 vectorize 业务编排与 Outcome；S12 继续兑现 outbox claim/upsert TX 与 D04 unique。v1 **禁止** 将 `vectorize_structure` 作为可消费 kind 实现成功路径（D04 可保留名）。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S12 规定：在单体 leaf-worker 内，如何用 **一份 Turso 业务主库** 可靠承载已冻业务真相的写入、CAS、claim、outbox、迁移与就绪，并与对象字节（S13）及派生向量对账——domain 代码只依赖 Ports，不泄漏 driver。

### 1.2 拓扑

```text
Domain services (S01–S11, …)
  │ Persistence Ports only
  ▼
S12 UnitOfWork / Repositories / Migration / Readiness / Outbox / Claim
  │ Turso adapter (driver isolated)
  ▼
┌─────────────────────────────────────────────┐
│ Single Turso primary DB (mkb_primary)         │
│  runtime | intake | generation | registry     │
│  vector (derived) | object catalog | ops      │
└─────────────────────────────────────────────┘
        │ after commit: outbox dispatcher
        ▼
 in-process / lightweight transport
        ├── handlers (vectorize, child spawn, …)
        └── S13 object bytes (external substrate)
```

### 1.3 Scope fence

**负责**：Persistence Ports；单主库拓扑；TX-01..08 物理兑现；transactional outbox；claim/fence/lease；单一 migration 链与 readiness；逻辑模块与 `mkb_` 前缀；同库 native vector 存放/引用/对账最小合同；与 S13 的 bytes-first 登记时序；CW/vector 默认启用与 fail-loud。

**不负责**：业务状态机（S02–S07）；对象 backend 选型（S13）；ANN 算法（S09）；推理策略（S11）；密钥（S16）；metric runbook（S15）；DB-per-team / PG / 无协调多进程写。

### 1.4 完成定义

1. §2 Truth + §4 E 包可映射到代码与测试；  
2. TX-01..08 集成测试通过；  
3. outbox 崩溃注入：不丢、可重放、幂等；  
4. claim fence 过期与 stale outcome 拒绝；  
5. migration drift / 缺 registry / 缺 CW·vector → readiness=false；  
6. bytes-first：无 digest 不得登记成功 handle；  
7. vector 存在≠serving；  
8. 实现无需打开 QNA；  
9. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 全局 T-O（摘要）

| ID | 一句话 |
|---|---|
| T-O-97..101 | 范围、Turso、Ports、关系 SSOT、legacy fence |
| T-O-102..104 | 单主库拓扑、substrate 分账、TX-01..08 |
| T-O-105..107 | outbox+claim、migration/readiness、CW+vector+bytes-first |
| T-O-108..110 | 逻辑模块、outbox 投递环+lease、native vector 最小合同 |

### 2.2 域内 S12-T

| ID | 内容 |
|---|---|
| S12-T001 | Ports：UnitOfWork、Repositories、Migration、Readiness、Outbox、Claim |
| S12-T002 | Adapter 唯一持有 driver/SQL |
| S12-T003 | 逻辑主库名 `mkb_primary`；一发布单元一写权威 |
| S12-T004 | 业务表 `team_uuid NOT NULL`；读写 team-scoped |
| S12-T005 | 默认 Concurrent Writes；不可用→readiness fail-loud |
| S12-T006 | 默认 Native Vector；不可用→readiness fail-loud |
| S12-T007 | 对象字节非业务 SSOT；库只存 handle+digest+size+media+lineage |
| S12-T008 | bytes-first：S13 promote 得 digest 后才 TX 登记 |
| S12-T009..016 | TX-01..08（见 §2.3） |
| S12-T017 | Outbox 字段：id、team、kind、payload、dedupe_key、available_at、attempts、status |
| S12-T018 | Outbox at-least-once；消费幂等；ACK≠业务成功 |
| S12-T019 | fence 不匹配 Outcome 必须拒绝；lease 过期 recovery 按 S03 |
| S12-T020 | 单一线性 migration：id+checksum+applied_at；已应用不可改 |
| S12-T021 | Empty-DB bootstrap：migration + code-owned registry 幂等 |
| S12-T022 | Readiness=false：迁移未完、checksum drift、强制 registry 缺、CW/vector 不匹配 |
| S12-T023 | 模块：runtime/intake/generation/registry/vector/object/ops |
| S12-T024 | 表前缀 `mkb_`；禁 `smind_*` |
| S12-T025 | payload_extra 默认 `{}`；禁承载 identity/state/proof/route/auth |
| S12-T026 | Vector 行：team、generation 坐标、digests、model、dimension |
| S12-T027 | Vector：proof 后 outbox→幂等 upsert；存在≠serving |
| S12-T028 | VIEW 只读；非写路径/SSOT |
| S12-T029 | 索引四类：team 列表、状态队列、主体反查、幂等/唯一 |
| S12-T030 | v1 不做：DB-per-team、无协调多写、PG、Sync 可写 SSOT、queue+DB fork 强制架构 |
| S12-T031 | 物理表闭集与列以 **D04** 为准（55+ required 族） |
| S12-T032 | 单 outbox 表；不建第二业务队列 SSOT |
| S12-T033 | model catalog / adapter_bindings / inference_invocations 写语义归 S11；S12 兑现表与 TX |

### 2.3 强制事务矩阵

| ID | 原子单元 | 同事务必须包含 |
|---|---|---|
| TX-01 | Task 创建 | tasks + task_audits (+ root execution 若契约要求) |
| TX-02 | Task 状态 CAS | tasks 条件更新（expected status/revision/generation） |
| TX-03 | Process claim | processes：状态→claimed + fence + lease + worker |
| TX-04 | Process 推进 | processes + fence 校验 + outcome ref |
| TX-05 | Candidate accept | S04 规定行集 + outbox child intents；禁 partial Snapshot |
| TX-06 | Generation accept | generation artifacts meta + per-type pointers CAS + transitions（+ proof refs） |
| TX-07 | 需 wake 的业务变更 | 业务行 + outbox 行 |
| TX-08 | Gate decision | decision + gate CAS + waiting 投影 + outbox |

**总规则**：UoW commit 成功 → 才允许 outbox 投递 / 外部 IO / 向量计算；CAS 冲突 → 显式错误。

---

## 3. 总体方案陈述

1. **Ports-first**：domain 零 SQL。  
2. **单主库**：`mkb_primary` + team 行级隔离。  
3. **TX 白名单**：TX-01..08 不可拆。  
4. **先 commit 后副作用**：transactional outbox。  
5. **Claim/fence**：原子 claim；stale 拒绝。  
6. **Migration + readiness**：单链 + checksum + bootstrap registries。  
7. **默认 CW + Native Vector**：fail-loud。  
8. **Bytes-first / vector 派生**：对象与向量不冒充业务成功。  
9. **DDL 在 D04**：本文是执行语义 SSOT。  
10. **QNA 零依赖**。

---

## 4. 具体执行方案清单

### 4.1 `S12-E01` — 目录、Ports 与 architecture 围栏

**真相**：S12-T001/T002

**执行台账 — 逻辑路径**：

| 路径 | 职责 |
|---|---|
| `src/runtime/persistence/` 或 `src/persistence/` | UnitOfWork、ports、adapters |
| `src/persistence/ports/` | 接口定义（domain 依赖） |
| `src/persistence/turso/` | 唯一 driver/连接/SQL 方言层 |
| `src/persistence/migrations/` | 单一有序 migration 文件链 |
| `src/contracts/persistence/` | 错误码、OutboxRecord、ClaimToken 等 typed shapes |

**Ports 最小方法面**：

```text
UnitOfWork
  begin() / commit() / rollback()
  # adapter 内 BEGIN CONCURRENT / 等价 CW 会话

OutboxPort
  enqueue(same_tx, OutboxRecord)
  claim_batch_for_dispatch(limit, worker) -> rows  # CAS pending→in_flight
  mark_done / mark_retry(available_at) / mark_dead
  requeue_dead(outbox_id) -> ok | conflict   # CAS dead→pending；审计/事件；禁 silent dead→done
  reset_attempts(outbox_id) -> ok | conflict # 显式清 attempts 后可再 claim；须审计

ClaimPort
  claim_process(expected_status, lease, worker) -> fence | conflict
  validate_fence(process_id, fence) -> ok | reject
  recover_expired_leases(now) -> n  # 按 S03 规则

MigrationPort
  applied_versions() / apply_pending() / verify_checksums()

ReadinessPort
  evaluate() -> Ready | NotReady(reasons[])

Repository ports (按域拆分)
  Task / Execution / Process / Intake* / Generation /
  Registry / VectorRecord / ObjectCatalog / Inference* ...
```

| 规则 | 验收 |
|---|---|
| services 禁止 import turso/libsql driver | architecture test |
| 禁止第二可写业务库配置 | 启动拒绝 |
| 禁止 `smind_*` 表 | migration/扫描 |

**小结**：依赖方向可机械测试。

---

### 4.2 `S12-E02` — 单主库拓扑与引擎能力

**真相**：S12-T003..T006、T030

| 项 | 规范 |
|---|---|
| 逻辑名 | `mkb_primary` |
| 租户 | `team_uuid` 行级；**不做** DB-per-team |
| 进程 | 默认同进程多协程写；**禁止**无协调多 OS 进程写同一文件 |
| Concurrent Writes | **默认启用**；配置声明；不可用 → readiness=false（默认不静默降级） |
| Native Vector | **默认启用**；不可用 → readiness=false |
| Embedded Replica / Sync | 可选附件；**不得**成为第二可写 SSOT |
| PostgreSQL | v1 **不存在** 必选路径 |
| 扩写（queue+DB fork） | **defer**；不阻塞 v1 |

**小结**：Turso 单写权威 + 能力面 fail-loud。

---

### 4.3 `S12-E03` — 逻辑模块与 D04 映射

**真相**：S12-T023/T024/T031；D04

| 逻辑模块 | 职责摘要 | 物理权威 |
|---|---|---|
| runtime | tasks/audits/restarts、executions、processes、outcomes、outbox、gates | D04 runtime 表 |
| intake | sources/items/revisions/artifacts/snapshots/memberships/candidates… | D04 intake |
| generation | artifacts、invocations、pointers、transitions | D04 generation |
| registry | workflow、structure/construction schema、source/preflight、model catalog… | D04 registry |
| vector | `mkb_vector_records` + native vector index | D04 vector |
| object | `mkb_stored_objects` / `mkb_object_references` / `mkb_object_delete_proofs` | D04 object（语义 S13） |
| ops | `mkb_schema_migrations`、readiness 辅助 | D04 ops |
| inference 可观测 | catalog/bindings/invocations | D04 + S11 写语义 |

**索引四类最低要求**（S12-T029）：

1. team 列表：`(team_uuid, …time/status)`  
2. 工作队列：`(status, available_at, priority)` 类  
3. 主体反查：task/execution/process/item/generation  
4. 幂等/唯一：fingerprint、dedupe_key、`(team, execution, artifact_type)` current 等  

**VIEW**：只读投影（如 active filters）；**禁止** UPDATE/INSERT 业务状态。

**小结**：模块化组织，单一 migration 链，DDL 不另开真相。

---

### 4.4 `S12-E04` — UnitOfWork 与 TX-01..08 执行步骤

**真相**：S12-T009..016；T-O-104

**通式**：

```text
domain command
  → uow.begin()
  → repository CAS/insert (exact TX-*)
  → outbox.enqueue (if wake needed)
  → uow.commit()
  → (after commit) dispatcher may deliver
```

**逐步验收要点**：

| TX | 关键 CAS / 约束 |
|---|---|
| TX-01 | Task 与 Audit 不可分拆提交 |
| TX-02 | `WHERE status=? AND revision=?`（或等价 generation） |
| TX-03 | `ready→claimed` 单行原子；写入 fence、lease_expires_at、worker_id |
| TX-04 | 所有推进校验 fence；写 outcome ref |
| TX-05 | 禁止 partial accept；失败全回滚 |
| TX-06 | multi-pointer 同事务；任一层失败全回滚 |
| TX-07 | 业务行与 outbox 同行提交 |
| TX-08 | gate decision 与 waiting 投影原子 |

**禁止**：

- commit 前发 queue / 调外部 HTTP 当成功；  
- 先 queue 后写库；  
- 无条件 UPDATE 状态。

**小结**：白名单事务是 HARD。

---

### 4.5 `S12-E05` — Transactional outbox 投递环

**真相**：S12-T017/T018/T032；T-O-105/109

**OutboxRecord 逻辑字段**：

| 字段 | 说明 |
|---|---|
| `outbox_id` | UUID |
| `team_uuid` | 必填 |
| `kind` / topic | 如 `vectorize_construct`、`spawn_child`… |
| `payload` | 有界 JSON；**不塞**全文/大对象 |
| `dedupe_key` | 消费幂等键 |
| `available_at` | 退避用 |
| `attempts` | 递增 |
| `status` | `pending` → `in_flight` → `done`；或 `pending` 重试；或 `dead` |
| `created_at` / `updated_at` | 审计 |

**投递环逐步**：

| 步 | 动作 |
|---|---|
| 1 | 业务 TX 插入 `pending` 行（同 TX） |
| 2 | commit |
| 3 | dispatcher 周期/唤醒：`claim_batch` CAS `pending→in_flight`（且 `available_at<=now`） |
| 4 | 投递到进程内 handler 或轻量传输 |
| 5 | 成功 → `done`；失败 → attempts++、`available_at` 退避、`pending`；耗尽 → `dead` |
| 6 | 消费端按 `dedupe_key` 幂等 |

| 规则 | 说明 |
|---|---|
| at-least-once | 崩溃可重放 |
| ACK ≠ 业务成功 | 业务成功已在步骤 1 的 TX |
| 禁止 | 仅用内存 channel 替代 outbox 作跨崩溃意图 |
| 毒消息 | dead + S15 告警 |

**小结**：durable polling 环；queue 仅传输。

---

### 4.6 `S12-E06` — Claim / fence / lease recovery

**真相**：S12-T019；T-O-105/109

```text
claim:
  CAS process status ready → claimed
  set fence = new_token
  set lease_expires_at = now + lease_duration
  set worker_id

work:
  every mutation carries fence F
  Outcome / status advance: validate_fence(F) or REJECT

success/fail terminal:
  TX with valid F → terminal status + outcome ref + optional outbox

expire recovery:
  scanner: claimed ∧ lease_expires_at < now
  → CAS to ready | failed per S03 rules
  → 不得无 fence 抢写

stale F:
  reject with conflict; 不静默覆盖
```

| 配置（默认建议，可配） | 量级 |
|---|---|
| `process.lease_default_seconds` | 60–300s 起步 |
| 长模型调用 | heartbeat 续租 **或** 事务外 IO + 状态靠 fence |
| 禁止 | 无限 lease；无 recovery 扫描仪 |

**小结**：fencing 是唯一防 stale writer 机制。

---

### 4.7 `S12-E07` — Migration、bootstrap、readiness

**真相**：S12-T020..T022；T-O-106

**Migration 链**：

| 规则 | 规范 |
|---|---|
| 线性 versioned | 全局有序 id |
| checksum | 内容哈希；已应用行不可改写 |
| multi-head | **禁止** |
| 文件 | 可分文件，版本号全局有序 |

**Empty-DB bootstrap 顺序**：

```text
1. open engine; probe Concurrent Writes + Native Vector
2. apply_pending migrations
3. verify_checksums
4. upsert code-owned registries (same digest 幂等; 异 digest FAIL):
     StructureSchema, ConstructionSchema, workflow manifests,
     model catalog + adapter_bindings (S11), …
5. readiness = all ok
```

**Readiness=false 当**：

- 迁移未完成 / checksum drift；  
- 强制 registry/schema digest 缺失或不匹配；  
- 二进制声明要求 CW/vector 但引擎不具备；  
- （联合）S13 object_root identity 失败。

Readiness ≠ liveness（进程活着但拒绝业务流量）。

**小结**：确定性 bootstrap；漂移挡流量。

---

### 4.8 `S12-E08` — Bytes-first 与 object catalog TX 接合

**真相**：S12-T007/T008；S13

```text
S13: stream → promote → (digest, size, stored_object_uuid)
S12 UnitOfWork:
  upsert mkb_stored_objects (team, sha256, size, handle…)
  insert mkb_object_references (live, purpose, owner…)
  insert domain rows (IntakeArtifact / GenerationArtifact / …)
commit → usable handle for domain
```

| 规则 | 说明 |
|---|---|
| 无 digest | 不得登记 usable handle |
| TX 失败 | 可留 orphan bytes → S13 GC；**禁止** 当业务成功 |
| 禁止 | TX 内无界 stream；path 进业务契约 |

**小结**：对象存在 ≠ Artifact/Process 成功。

---

### 4.9 `S12-E09` — Vector 写入、幂等与 serving 分账

**真相**：S12-T026/T027；T-O-110；S11-E09

```text
business proof/pointer committed
  → outbox kind ∈ {vectorize_construct, …}  # v1 禁消费 vectorize_structure
  → handler: S11.embed + upsert mkb_vector_records (+ native index)
  → mark outbox done
```

**向量行最小逻辑字段**：

| 字段 | 要求 |
|---|---|
| `team_uuid` | 强制 |
| generation/block 坐标 | immutable generation-scoped |
| content / embedding-input digest | 对账 |
| `embedding_model` / `model_version` | Layer A |
| `dimension` | Layer A |
| `adapter_kind` | 与 binding 一致 |
| vector blob / native type | F32 等；D04 钉类型 |
| filter facets | Layer B（team + intake + 业务 facet） |

| 规则 | 说明 |
|---|---|
| 幂等 upsert | 同坐标/digest 重放无双冲突行 |
| 存在 ≠ serving | publication 归 S09/S04 lifecycle |
| 无 generation 引用 | 拒绝可服务写入 |
| 禁 | 向量表第二状态机；无 team 全表扫描当 API |

**小结**：派生可对账存储，非 lifecycle SSOT。

---

### 4.10 `S12-E10` — 错误、配置与显式 defer

**错误轴（逻辑，可映射 HTTP/内部码）**：

| 类 | 条件 |
|---|---|
| `PERSISTENCE_CAS_CONFLICT` | TX CAS 失败 |
| `PERSISTENCE_FENCE_MISMATCH` | stale fence |
| `PERSISTENCE_TX_RULE` | 拆白名单事务 |
| `PERSISTENCE_NOT_READY` | readiness false |
| `PERSISTENCE_MIGRATION_*` | checksum/apply 失败 |
| `PERSISTENCE_TEAM_SCOPE` | 跨 team |
| `PERSISTENCE_INTERNAL_*` | 驱动/连接 |

**配置键（逻辑）**：

| 键 | 含义 |
|---|---|
| `turso.url` / 本地 path | 连接（秘密不进 git） |
| `turso.concurrent_writes` | 默认 true |
| `turso.native_vector` | 默认 true |
| `outbox.poll_interval_ms` / batch | 投递环 |
| `outbox.max_attempts` | dead 阈值 |
| `process.lease_default_seconds` | claim |
| `process.lease_recovery_interval` | recovery |

**显式 defer**：多进程共享写文件、DB-per-team、Embedded Replica 可写 SSOT、queue+DB fork 强制架构、PostgreSQL。

---

### 4.11 `S12-E11` — 与各 domain 交接

| 对方 | 合同 |
|---|---|
| S02/S03 | TX-01..04、claim、outbox wake |
| S04/S05 | TX-05/TX-08、intake 表 |
| S06/S07 | TX-06 multi-pointer、generation/registry |
| S08/S09 | vector 模块 + outbox vectorize |
| S11 | inference 三表写语义；vectorize 幂等 |
| S13 | object 三表 + bytes-first |
| D04 | 物理 DDL SSOT |
| S15 | dead outbox、scan 指标 |
| 17 | 进程与库拓扑图 |

---

## 5. 事实反例、风险与实施切片

### 5.1 反例 → 禁令

| Legacy/错误 | MKB |
|---|---|
| queue/callback 成功 | outbox 后置；关系 commit 为准 |
| clean/rag 双 process 表 | 统一 processes + capability |
| file 超级 status | 六 StateFamily 分账 |
| D1 + Vectorize 脱节 | generation 引用 + outbox |
| IF NOT EXISTS 隐式进化 | versioned migration + readiness |
| smind_* | mkb_* |
| QNA 当实现说明书 | 禁止 |

### 5.2 风险

| 风险 | 缓解 |
|---|---|
| CW/vector 引擎缺口 | readiness fail-loud |
| TX-05 过大 | S04 size fence；禁 partial |
| outbox 毒消息 | attempts + dead + S15 |
| orphan bytes | S13 GC |
| 向量与 serving 混淆 | E09 验收 |

### 5.3 实施切片

1. adapter + UoW + migrations 骨架；  
2. runtime + outbox/claim；  
3. TX 矩阵测试；  
4. intake/generation/object；  
5. vector 模块；  
6. readiness + bootstrap registries；  
7. architecture tests E01。

---

## 6. 强制验收矩阵

| ID | 场景 | 期望 |
|---|---|---|
| S12-A01 | domain import driver | 架构失败 |
| S12-A02 | 双可写库 | 拒绝 |
| S12-A03 | Task 创建缺 audit | TX 失败 |
| S12-A04 | claim 无 fence 写 outcome | 拒绝 |
| S12-A05 | stale fence | 拒绝 |
| S12-A06 | lease 过期 recovery | CAS 回 ready/failed |
| S12-A07 | commit 前发 queue | 禁止 |
| S12-A08 | 崩溃 outbox pending | 重启后投递 |
| S12-A09 | 重复投递 | 幂等 |
| S12-A10 | Candidate partial accept | 失败 |
| S12-A11 | pointer CAS 冲突 | fail-loud |
| S12-A12 | 无 bytes 登记 handle | 禁止 success |
| S12-A13 | migration checksum drift | readiness false |
| S12-A14 | 缺 StructureSchema | readiness false |
| S12-A15 | CW 缺失（默认） | readiness false |
| S12-A16 | vector 能力缺失（默认） | readiness false |
| S12-A17 | vector 无 team/generation | 拒绝 |
| S12-A18 | 仅有向量行 | 不自动 serving/Task success |
| S12-A19 | 跨 team 读 | 拒绝 |
| S12-A20 | legacy smind 依赖 | 零命中 |
| S12-A21 | PG 必选路径 | 不存在 |
| S12-A22 | VIEW 上 UPDATE | 禁止 |
| S12-A23 | 实现可不打开 QNA | 文档自包含 |

---

## 7. Reference-anchor 台账

| Anchor | 裁决 |
|---|---|
| Turso Concurrent Writes | 启用 + fail-loud |
| Turso Native Vector | 默认开；算法归 S09 |
| Embedded Replicas | 可选；非可写 SSOT |
| legacy indexes / claim | 升级模式 |
| legacy 双 process 表 / Vectorize 分裂 | 删除拓扑 |
| QNA S12 | 证据 only；非 SSOT |

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO / execution-complete for v1.1`**：S12 作为关系持久化 **唯一执行真相**（语义层）已含 E01–E11；物理列以 D04 为准；实现不得外挂 QNA。

### 8.2 强制结论

1. domain-truth + D04 only；  
2. 单 Turso 主库、ports 隔离；  
3. TX-01..08 + outbox + claim/fence；  
4. migration + readiness；默认 CW + Native Vector；拒 PG；  
5. bytes-first；vector 派生；不改写业务状态机。

### 8.3 一句话

S12-v1.1 把持久化从「宪法」升格为 **可编码执行台账**，与 D04 共同独占关系层真相。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| S12-v1.0 | 2026-08-11 | accepted | T-O-97..110；TX/outbox/CW+vector |
| S12-v1.0-cal-* | 2026-08-11 | calibrated | S13/D04/S07 校准注 |
| S12-v1.1 | 2026-08-12 | accepted | **执行 SSOT 强制**；E01–E11；禁止执行依赖 QNA |
| S12-v1.1-ns6-note | 2026-08-20 | change-request | 叶工人准入 ≠ constitution 探针：`/ready` 合取 `write_path_ready`（serial `BEGIN IMMEDIATE`）；`concurrent_writes_probe` 只在空 scratch 上探测，**不得**改写生产 `journal_mode`，也不得在 UoW 仍为 IMMEDIATE 时把门控 `/ready`。S12-T005 fail-loud 保留为探针语义；待业务 UoW 真切 CONCURRENT 后再并回 REQUIRED。 |
