# S12 — Turso Persistence

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`F1 数据基础 / S12 Turso Persistence`
>
> **日期**：`2026-08-11`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted`（S12 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S12-v1.0`
>
> **上游权威输入**：`D01-v1.4`、`D02-v1.0`、`S01-v1.5`、`S02-v1.3`、`S03-v1.3`、`S04-v1.2`、`S05-v1.1`、`S06-v1.0`；冻结的 `qna-truth/S12.md v1.0`（Q1–Q9 / `T-O-97..110`）
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **事实证据**：Turso Concurrent Writes / Native Vector / Embedded Replicas / Sync 线上资料；`context/legacy-family/` D1/DO/索引模式；`context/legacy-python/` core/vec 双库、claim、VIEW（仅 ReferenceAnchor）
>
> **下游消费者**：`S07-S11`、`S13-S16`、跨系统拓扑 `17`、验收冻结 `18`、全部 domain repository 实现

> **Owner-originated 约束**：选用 **Turso**（含 beta/experimental 能力）作为关系持久化方向；**默认启用 Concurrent Writes 与 Native Vector**（vector 是选 Turso 主因；v1 **不**采用 PostgreSQL 等重量级数据库）。v1 **单主库设计够用**；本地轻量队列 + DB fork 等扩写 **defer**。

> **跨文档审计声明**：S12 **不**拥有 Task/Execution/Process/Intake/Generation 状态机语义，只兑现 S01–S06 已冻合同的物理事务、CAS、outbox、migration 与派生向量存放。业务状态名与合法边以各 domain Spec 为准；冲突时不得用“库做不到”静默改状态机，必须 fail-closed 或显式 reopen。

> **Legacy 边界（T-O-42 / T-O-101）**：不继承 D1/DO/Vectorize 拓扑、`smind_*` 表名、混态 file_status、callback/queue SSOT、无对账双库。

---

> **S13校准声明**：`S13-v1.0` 兑现 object 模块物理表语义（`mkb_stored_objects` / `mkb_object_references` / `mkb_object_delete_proofs`）、bytes-first TX 接合、identity readiness 与 G-11=local。S12 继续拥有 migration/UnitOfWork；S13 拥有 Port/layout/GC 语义。R2 adapter 仍 defer。

> **S07校准声明**：`S07-v1.0` 将 `construction_document` / `dual_channel_projection` / construction validation 面纳入 generation 模块 artifact_type 集合（与 structure 类型并列）；TX-06 multi-pointer CAS 同 UoW 覆盖 S07 成员；ConstructionSchema 进 registry 模块；`vectorize_construct` 类 outbox intent 载荷仅为 exact construct generation refs。S12 不拥有 construct 业务状态机。

> **D04校准声明**：`D04-v1.1`（`T-O-160..179` + S11 reopen）冻结 **物理表闭集（55 required）、列/索引/VIEW、可观测三表、model/inference 三表、最终向量 F32+ANN、单 outbox、双层 filter**。S12 继续拥有 Ports/TX/migration/readiness/outbox 投递环；**表名与物理唯一性以 D04 为准**。

> **S11校准声明**：`S11-v1.0` 消费 catalog/bindings/invocations 与 vectorize outbox 路径；S12 不定义推理策略；vectorize 幂等 upsert 在 TX 内由 domain+S11 编排、S12 兑现。

## 1. Domain 介绍

### 1.1 Domain 价值

S12 回答：在单体 leaf-worker 内，如何用 **一份 Turso 业务主库** 可靠承载已冻业务真相的写入、CAS、claim、outbox、迁移与就绪，并与对象字节（S13）及派生向量（同库 native vector / S09）对账——而不把 driver 细节泄漏进 domain 代码。

S12 解决九个核心问题：

1. 业务代码如何只依赖 Persistence Ports；
2. 单主库 + 同进程拓扑下如何并发写（Concurrent Writes）；
3. 哪些状态变更必须原子（TX 矩阵）；
4. 如何先 durable commit 再 wake（outbox）；
5. Process 如何原子 claim 与 fence；
6. 空库如何确定性 bootstrap，drift 如何挡流量；
7. 对象 bytes 与关系行如何 bytes-first 登记；
8. Native Vector 同库如何存且不冒充业务状态；
9. schema 如何模块化仍保持单一 SSOT 与单一 migration 链。

### 1.2 在整体拓扑中的位置

```text
Domain services (S01–S06, …)
  │ Persistence Ports only
  ▼
S12 UnitOfWork / Repositories / Migration / Readiness
  │ Turso adapter (driver isolated)
  ▼
┌─────────────────────────────────────────────┐
│ Single Turso primary DB (mkb_primary)         │
│  runtime | intake | generation | registry     │
│  vector (derived) | ops                       │
└─────────────────────────────────────────────┘
        │ outbox after commit
        ▼
 in-process / lightweight transport queue
        │
        ├── S13 object bytes (external substrate)
        └── vectorize workers (derived upsert into vector module)
```

### 1.3 Scope fence

**S12 负责：**

- Persistence Ports 与 adapter；
- 单主库部署拓扑与进程写权威；
- 强制事务矩阵 TX-01..08 的物理兑现；
- transactional outbox 与 claim/fence/lease 原语；
- 单一 migration 链、bootstrap、readiness；
- 逻辑 schema 模块与表前缀；
- 同库 native vector 的 **存放/引用/对账** 最小合同；
- 与 S13 的 handle 登记时序（bytes-first）；
- Concurrent Writes / Native Vector 默认启用与 fail-loud。

**S12 不负责：**

| 排除项 | 归属 |
|---|---|
| 业务状态机与合法边 | S02–S06 / D02 |
| Artifact 字节 backend 选型 | `S13-v1.0`：v1 本地盘；G-11 closed；R2 defer |
| Embedding 模型、ANN 算法、容量 benchmark | S08–S09 |
| 检索 API / rerank | S10 |
| 推理 provider | S11 |
| Prompt/model 业务 registry 语义 | S14（S12 只存表） |
| 告警/runbook 数值 | S15 |
| 密钥与威胁模型 | S16 |
| queue+DB fork 扩写 | future reopen |

### 1.4 Domain 完成定义

1. §2 Truth 可映射到 ports、DDL 模块、测试；
2. TX-01..08 集成测试通过；
3. outbox 崩溃注入：不丢、可重放、幂等；
4. claim fence 过期与 stale outcome 拒绝通过；
5. migration drift / 缺 registry / 缺 CW·vector 能力 → readiness=false；
6. bytes-first：无 digest 不得登记成功 handle；
7. vector 行无 generation 引用不得可服务；存在≠serving；
8. 零 legacy runtime dependency；无 PG 依赖；
9. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O）

| Truth-ID | 摘要 |
|---|---|
| `T-O-97` | S12=关系业务持久化/事务域；不拥有业务状态机 |
| `T-O-98` | 选用 Turso；允许 beta；须写清开关与失败语义 |
| `T-O-99` | Domain 只经 Persistence Ports；禁直连 driver |
| `T-O-100` | 关系 durable 表是 SSOT；queue/文件/向量/view 不是 |
| `T-O-101` | legacy 仅 ReferenceAnchor |
| `T-O-102` | 单发布单元 + 单主库；team 行级隔离；默认同进程；禁无协调多进程写；副本非第二可写 SSOT |
| `T-O-103` | 关系 SSOT；对象外置 S13；向量派生可对账；VIEW 只读 |
| `T-O-104` | TX-01..08 强制原子；先 commit 后副作用；CAS fail-loud |
| `T-O-105` | transactional outbox + 原子 claim/fence；queue 仅传输 |
| `T-O-106` | 单 migration 链 + checksum；bootstrap；drift→readiness=false |
| `T-O-107` | **默认启用 Concurrent Writes + Native Vector**；bytes-first；扩写 defer；拒 PG |
| `T-O-108` | 单库逻辑模块 + 单 migration 链；`mkb_` 前缀 |
| `T-O-109` | outbox polling 投递环 + claim lease recovery |
| `T-O-110` | 同库 vector 最小引用合同；算法归 S09 |

### 2.2 域内 Truth（S12-T）

| ID | 冻结内容 | 来源 |
|---|---|---|
| `S12-T001` | Persistence Ports 最小集合：`UnitOfWork`、按域 Repository、`MigrationPort`、`ReadinessPort`、`OutboxPort`、`ClaimPort`。 | T-O-97/99 |
| `S12-T002` | Adapter 是唯一允许持有 driver/连接/SQL 方言的层。 | T-O-99 |
| `S12-T003` | 业务主库逻辑名 `mkb_primary`；一发布单元一写权威。 | T-O-102 |
| `S12-T004` | 所有业务表含 `team_uuid NOT NULL`；查询/写必须 team-scoped。 | T-O-102/101 |
| `S12-T005` | 默认启用 Concurrent Writes（`BEGIN CONCURRENT`/MVCC 能力面）；不可用→readiness fail-loud（默认不静默降级）。 | T-O-107 |
| `S12-T006` | 默认启用 Native Vector 类型/索引能力；不可用→readiness fail-loud。 | T-O-107 |
| `S12-T007` | 对象字节永不作为业务状态 SSOT；关系库只存 handle+digest+size+media+lineage。 | T-O-103 |
| `S12-T008` | bytes-first：S13 不可变写成功并得 digest 后，才可在 TX 内登记 artifact 元数据。 | T-O-107 |
| `S12-T009` | TX-01 Task 创建：`tasks`+`task_audits`（及规范要求的 root Execution 行）同事务。 | T-O-104 |
| `S12-T010` | TX-02 Task 状态 CAS：期望旧状态/generation 条件更新。 | T-O-104 |
| `S12-T011` | TX-03 Process claim：状态→claimed + fence + lease + worker 同事务。 | T-O-104/105 |
| `S12-T012` | TX-04 Process 推进：fence 校验 + 状态 + Outcome 引用同事务。 | T-O-104 |
| `S12-T013` | TX-05 CandidateSet accept：S04 规定集合 + outbox child intents 同事务；禁 partial Snapshot。 | T-O-104 |
| `S12-T014` | TX-06 Generation accept：artifact 元数据 + per-type pointer CAS + transition（+ proof 引用）同事务。 | T-O-104/S06 |
| `S12-T015` | TX-07 业务变更 + outbox 行同事务。 | T-O-104/105 |
| `S12-T016` | TX-08 Gate decision append + gate CAS + waiting 投影行 + outbox 同事务。 | T-O-104/S05 |
| `S12-T017` | Outbox 逻辑字段：id、team_uuid、kind/topic、payload、dedupe_key、available_at、attempts、status∈{pending,in_flight,done,dead}。 | T-O-105/109 |
| `S12-T018` | Outbox 投递 at-least-once；消费幂等；ACK 不定义业务成功。 | T-O-105/109 |
| `S12-T019` | Claim fence 不匹配的 Outcome **必须拒绝**；lease 过期 recovery 按 S03 规则 CAS。 | T-O-105/109 |
| `S12-T020` | 单一线性 migration：id、checksum、applied_at；已应用不可改写。 | T-O-106 |
| `S12-T021` | Empty-DB bootstrap：全量 migration + code-owned registry 行（同 digest 幂等）。 | T-O-106 |
| `S12-T022` | Readiness=false：迁移未完、checksum drift、强制 registry/schema digest 缺失/不匹配、CW/vector 能力与声明不匹配。 | T-O-106/107 |
| `S12-T023` | 逻辑模块：runtime / intake / generation / registry / vector / ops。 | T-O-108 |
| `S12-T024` | 表前缀 `mkb_`；禁止 `smind_*`。 | T-O-108/101 |
| `S12-T025` | payload_extra 非空默认 `{}`；禁止承载 identity/state/proof/route/auth。 | S01 继承 |
| `S12-T026` | Vector 行必含 team_uuid、immutable generation/block 坐标、content/embedding digest、model、dimension。 | T-O-110 |
| `S12-T027` | Vector 写入：业务 proof 后 outbox → 幂等 upsert；存在≠serving。 | T-O-110 |
| `S12-T028` | SQL VIEW 只读；不得作为写路径或 SSOT。 | T-O-103 |
| `S12-T029` | 索引四类最低要求：team 列表、状态/队列、主体反查、幂等/唯一（含 partial unique 按需）。 | legacy 证据升级 |
| `S12-T030` | v1 不做：DB-per-team、无协调多进程写、PG、Sync 作可写 SSOT、queue+DB fork 强制架构。 | T-O-102/107 |

### 2.3 强制事务矩阵（规范）

| ID | 原子单元 | 同事务必须包含 |
|---|---|---|
| `TX-01` | Task 创建 | tasks + task_audits (+ root execution 若契约要求) |
| `TX-02` | Task 状态 CAS | tasks 条件更新 |
| `TX-03` | Process claim | processes 状态+fence+lease+worker |
| `TX-04` | Process 推进 | processes + fence + outcome ref |
| `TX-05` | Candidate accept | S04 规定行集 + outbox intents |
| `TX-06` | Generation accept | generation artifacts meta + pointers + transitions |
| `TX-07` | 任意需 wake 的业务变更 | 业务行 + outbox |
| `TX-08` | Gate decision | decision + gate CAS + execution projection + outbox |

**总规则**：UnitOfWork 提交成功 → 才允许 outbox 投递 / 外部 IO / 向量计算；CAS 冲突 → 显式错误。

---

## 3. Contract schema 与逻辑结构

### 3.1 Persistence Ports（逻辑）

```text
UnitOfWork
  begin() / commit() / rollback()
  # 支持 Concurrent Writes 会话语义（adapter 内部）

OutboxPort
  enqueue(same_tx, OutboxRecord)
  claim_batch_for_dispatch(...)
  mark_done / mark_retry / mark_dead

ClaimPort
  claim_process(expected_status, lease, worker, fence) -> CAS
  validate_fence(process_id, fence)
  recover_expired_leases(...)  # 按 S03 规则

MigrationPort
  applied_versions() / apply_pending() / verify_checksums()

ReadinessPort
  evaluate() -> Ready | NotReady(reasons[])

Repository ports
  TaskRepository, ExecutionRepository, ProcessRepository,
  Intake*Repository, GenerationRepository, RegistryRepository,
  VectorRecordRepository (derived), ...
```

Domain **只**依赖上述接口，不依赖 SQL。

### 3.2 逻辑模块与表示例（非最终列清单）

> 列级 DDL 可在实现 migration 中细化，但 **职责与唯一性** 必须满足上游 Spec + 本节。

#### runtime

| 逻辑表 | 职责 | 关键约束 |
|---|---|---|
| `mkb_tasks` | Task 聚合 | PK `(team_uuid, task_uuid)` 或 uuid+unique(team,task) |
| `mkb_task_audits` | 1:1 immutable audit | FK/同事务 TX-01 |
| `mkb_task_restarts` | restart 因果 | S02 |
| `mkb_executions` | Execution 八态 | team+execution unique |
| `mkb_processes` | Process 八态 + 可选 fence 列 | capability key；队列索引 |
| `mkb_process_claims` | 可选附属 claim 表 | 与 processes 语义唯一 |
| `mkb_process_outcomes` | Outcome 引用/摘要 | fence 校验 |
| `mkb_outbox` | transactional outbox | dedupe_key；status 机 |
| `mkb_execution_gates` / decisions | S05 supporting | TX-08 |

#### intake

| 逻辑表 | 职责 |
|---|---|
| source/snapshot/item/revision/artifact/membership/changeset/staging… | 对齐 S04/S05 十表+supporting；S12 兑现 CAS 与 accept 事务 |

#### generation

| 逻辑表 | 职责 |
|---|---|
| `mkb_generation_artifacts` | immutable 元数据+handle+digest |
| `mkb_generation_invocations` | token/因果 |
| `mkb_generation_pointers` | unique(team, execution, artifact_type) |
| `mkb_generation_pointer_transitions` | append-only |

#### registry

| 逻辑表 | 职责 |
|---|---|
| workflow 七表 + structure/construction/source/preflight definitions… | S03/S05/S06/S07 registry；digest 幂等 |

#### vector

| 逻辑表 | 职责 |
|---|---|
| `mkb_vector_records`（名可变） | 派生向量元数据 + native vector 列/索引引用 |
| native vector index | Turso/libSQL vector index |

必填逻辑字段：`team_uuid`、generation/block 坐标、digests、`embedding_model`、`dimension`。

#### ops

| 逻辑表 | 职责 |
|---|---|
| `mkb_schema_migrations` | id, checksum, applied_at |
| readiness 辅助 | 可选 |

### 3.3 Outbox 状态（逻辑）

```text
pending → in_flight → done
                 ↘ pending (retry/backoff)
                 ↘ dead
```

### 3.4 Claim / lease（逻辑）

```text
claim: CAS ready→claimed; set fence F; lease_expires_at; worker_id
work:  all mutations carry F
success: TX with F → terminal + outbox
expire: recovery CAS claimed∧expired → ready|failed (S03)
stale F: reject
```

**默认建议**（可配置，非 Truth 秒数）：lease 默认覆盖单 Process 合理上限（实现可选 60–300s 级起步）；超长模型调用应 heartbeat 或拆事务外 IO（状态仍靠 fence）。

### 3.5 Bytes-first 时序

```text
S13.put_immutable(bytes) -> handle, size, digest
UnitOfWork:
  insert artifact meta(handle, digest, ...)
  optional pointer CAS / process proof
commit
outbox downstream
```

失败 TX 可留 orphan bytes → GC；**禁止** 解释为 success。

### 3.6 Vector 写入时序

```text
business proof/pointer committed
  → outbox kind=vectorize
  → embed (S08/S11)
  → idempotent upsert mkb_vector_records + native index
```

Serving/eligibility：S04 lifecycle + S09 publication——**不是** 向量行存在。

### 3.7 Migration / Readiness

```text
boot:
  verify engine features (CW, native vector)
  apply pending migrations (single chain)
  verify checksums
  ensure mandatory registries (incl. structure schema)
  readiness = all ok
```

---

## 4. 业务流转与运行合同

### 4.1 写路径通式

```text
domain command
  → open UnitOfWork
  → repositories CAS/insert (TX-*)
  → enqueue outbox (same TX)
  → commit
  → dispatcher delivers outbox
  → handlers (idempotent)
```

### 4.2 读路径

- 全部 team-scoped；
- 列表/队列使用 §2.2 S12-T029 索引类；
- VIEW 可选用于 active 过滤，只读。

### 4.3 与 S13

- S12 不实现对象存储；
- 只强制 bytes-first 与 meta 行合同；
- backend 本地盘/S3 归 S13。

### 4.4 与 S09

- S12 提供同库 native vector 存放与引用；
- S09：metric、topk、index generation、容量、是否多 space；
- 禁止 S09 再引入 PG 作为 v1 必选。

### 4.5 显式 defer

| 项 | 状态 |
|---|---|
| 多进程共享写文件 | 禁止 unless reopen 单写网关 |
| DB-per-team | defer |
| Embedded Replica 作可写 SSOT | 禁止 |
| 本地 queue + DB fork 扩写 | defer（业主：v1 够用） |
| PostgreSQL | 不做 |

---

## 5. 事实反例、风险与实施切片

### 5.1 Legacy 反例 → 禁令

| Legacy | MKB |
|---|---|
| queue/callback 成功 | outbox 后置；关系 commit 为准 |
| clean/rag 双 process 表 | 统一 processes + capability |
| file 超级 status | 六 StateFamily 分账 |
| D1 + 外部 Vectorize 脱节 | generation 引用 + outbox vectorize |
| IF NOT EXISTS 隐式进化 | versioned migration + readiness |
| smind_* 表名 | mkb_* greenfield |

### 5.2 风险

| 风险 | 缓解 |
|---|---|
| CW/vector 引擎缺口 | readiness fail-loud；Spec 记启用方式 |
| TX-05 过大 | 遵守 S04 sealed size fence；禁止拆 partial accept |
| outbox 毒消息 | attempts + dead + S15 |
| orphan bytes 膨胀 | S13 GC + 无引用扫描 |
| 向量与 serving 混淆 | T-O-110 验收 |

### 5.3 实施切片

1. adapter + UnitOfWork + migrations 骨架；  
2. runtime 表 + outbox/claim；  
3. TX 矩阵测试；  
4. intake/generation 表；  
5. vector 模块 + 引用约束；  
6. readiness 探针；  
7. bootstrap registry。

---

## 6. 强制验收矩阵

| ID | HARD 场景 | 期望 |
|---|---|---|
| `S12-A01` | domain 直接 import driver | 架构测试失败 |
| `S12-A02` | 双可写库配置 | 拒绝 / 不支持 |
| `S12-A03` | Task 创建缺 audit | TX 失败 |
| `S12-A04` | claim 无 fence 写 outcome | 拒绝 |
| `S12-A05` | stale fence | 拒绝 |
| `S12-A06` | lease 过期 recovery | 可 CAS 回 ready/failed |
| `S12-A07` | commit 前发 queue | 禁止（测试探针） |
| `S12-A08` | 崩溃：outbox pending 未投递 | 重启后投递 |
| `S12-A09` | 重复投递 | 幂等无双写业务 |
| `S12-A10` | Candidate partial accept | 失败；无 partial Snapshot |
| `S12-A11` | pointer CAS 冲突 | fail-loud |
| `S12-A12` | 无 bytes 登记 handle | 禁止 success |
| `S12-A13` | migration checksum drift | readiness=false |
| `S12-A14` | 缺 StructureSchema registry | readiness=false |
| `S12-A15` | CW 能力缺失（默认配置） | readiness=false |
| `S12-A16` | vector 能力缺失（默认配置） | readiness=false |
| `S12-A17` | vector 行无 team/generation | 拒绝写入 |
| `S12-A18` | 仅有向量行 | 不自动 serving/Task success |
| `S12-A19` | 跨 team 读 | 拒绝 |
| `S12-A20` | legacy smind 表/依赖扫描 | 零命中 |
| `S12-A21` | PG 驱动作为 v1 必选路径 | 不存在 |
| `S12-A22` | VIEW 上 UPDATE | 禁止或失败 |

---

## 7. Reference-anchor 台账

| Anchor | 用途 | 裁决 |
|---|---|---|
| Turso Concurrent Writes 博文/文档 | CW 设计前提 | 启用 + fail-loud |
| Turso Native Vector 文档 | 同库向量 | 默认开；算法归 S09 |
| Embedded Replicas 文档 | 副本非默认 SSOT | 可选附件 |
| legacy console DDL + indexes | team/队列/主体索引 | 升级模式 |
| legacy process 双表 | 反例 | 删除 |
| legacy Vectorize 分裂 | 反例 | outbox+引用 |
| python task_claims / vec views | claim 与只读 view | 升级 |

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO`**：S12 持久化宪法（拓扑、TX、outbox/claim、migration、CW+vector、模块、vector 最小合同）已闭合，可作为实现与 S09/S13 交接的权威真相。

### 8.2 强制结论

1. 单 Turso 主库、同发布单元、ports 隔离；  
2. 关系 SSOT；对象外置；向量派生同库；  
3. TX-01..08 + 先 commit 后副作用；  
4. outbox + claim/fence 必备；  
5. migration 链 + readiness；  
6. 默认 CW + Native Vector；拒 PG；  
7. bytes-first；  
8. 扩写 defer；  
9. 不改写 S01–S06 状态机。

### 8.3 下游

| 下游 | 承接 |
|---|---|
| S09 | 检索/ANN/容量/index generation |
| S13 | 对象 backend 与 GC 数值 |
| S15 | dead outbox 告警、scan 指标 |
| 17 | 进程与库拓扑图 |

### 8.4 一句话

S12 用单库 Turso（默认并发写与原生向量）把已冻业务合同落成可验收的事务、outbox、迁移与派生存储，而不引入 PG 或第二套状态真相。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `S12-v1.0` | `2026-08-11` | `MKB owner + Codex` | `accepted` | 吸收 Q1–Q9 / `T-O-97..110`；冻结单主库拓扑、TX 矩阵、outbox/claim、migration/readiness、CW+vector 默认启用、逻辑模块、vector 最小合同、bytes-first、验收矩阵与 legacy 裁决。 |
| `S12-v1.0-cal-s13` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S13-v1.0：object 三表、local backend、G-11 closed；S12 事务宪法不变。 |
| `S12-v1.0-cal-d04` | `2026-08-11` | `MKB owner + Codex` | `accepted / D04-calibrated` | 接收D04-v1.0：物理表闭集/索引/可观测/向量落点以 D04 为准；S12 Ports/TX/migration 不变。 |
