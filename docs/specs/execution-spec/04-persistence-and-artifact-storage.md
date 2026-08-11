# ES-04 — Persistence and Artifact Storage

> **项目**：myknowledgebase（MKB）
>
> **文件 ID**：ES-04
>
> **文档性质**：execution-spec / implementation authority
>
> **版本 / 日期**：ES-04-v1.0 / 2026-08-10
>
> **文档状态**：ready
>
> **Truth 输入**：OT-01-v1.0、OT-02-v1.0、OT-03-v1.0、OT-04-v1.0
>
> **Baseline 输入**：S01-v1.5、S02-v1.3、S03-v1.3、S04-v1.2、S05-v1.1、D02-v1.0；S12/S13 没有 frozen 文件
>
> **上游 Execution Spec**：ES-01-v1.0、ES-02-v1.0、ES-03-v1.0
>
> **下游 schema mapping输入**：ES-05-v1.0、ES-06-v1.0、ES-07-v1.0、ES-08-v1.0
>
> **上游索引**：docs/specs/index.md

本文件是 MKB v1 关系持久化与 Artifact 字节存储的唯一 Execution Spec。它负责把 ES-01..08 已完成文件的逻辑 schema 和原子性义务映射到 embedded Turso，冻结 transaction/unit-of-work、migration、outbox/inbox、domain event、semantic recovery scan、content-addressed object write/read/reference/GC，以及本地 backup/restore 的内部合同。

本文件不重新定义 Task、Execution、Process、Intake 或 Gate 的业务状态。关系表中的状态列、合法边与唯一 owner 仍由其来源 ES 持有；ES-04 只提供能无损执行这些规则的物理约束和 adapter。对象记录是 Artifact 的物理 substrate，不是第七个 StateFamily、通用文件产品或对外对象 API。

---

## 1. Inherited Truth

### 1.1 权威输入

| 来源 | 本文件直接继承 | 本文件不得改变 |
|---|---|---|
| OT-01-v1.0 | 一个 Python 应用、一个发布单元；Turso 方向；domain 不耦合 driver；knowledge 工具边界 | 不拆数据库服务、对象服务、queue 服务或 Reconciler 部署单元 |
| OT-02-v1.0 | canonical identity、六个且仅六个 StateFamily、SelectionPointer 与 state-vs-fact 宪法 | 不以 storage/upload/migration/delivery 状态创建第七族 |
| OT-03-v1.0 | 上游只能看到受控 logical refs；raw vector 与通用 storage surface OOS | 不公开路径、bucket/key、对象 CRUD、raw vector 或数据库能力 |
| OT-04-v1.0 | canonical truth、Artifact、history、pointer、durable scheduling 与 cleanup 在失败/重放后不丢不重 | 不以 DB commit、object existence、queue wake 或 backup success冒充产品成功 |
| S01-v1.5 | UUID、Turso 方向、payload_extra round-trip、Task/Audit 与 scheduling intent 原子性 | 不导入 legacy Cloudflare/D1/R2 拓扑 |
| S02-v1.3 | Task transition、Audit/Restart、CAS、idempotency 与 polling 历史义务 | 不让 repository 绕过 TaskAggregateOwner |
| S03-v1.3 | Workflow 七表、Execution/Process claim/fence/retry/recovery、state-before-wake、semantic repair | queue/outbox 不成为 runtime truth，不从 wake 推断状态 |
| S04-v1.2 | 十张 canonical Intake 表、support ledgers、one canonical acceptance transaction、bytes-first/orphan/missing-object规则 | 不从文件、日志或物理对象重建 canonical Snapshot/Revision |
| S05-v1.1 | typed evidence、CandidateSet、preflight/Gate exact binding 与 decision 原子性 | 不从 payload_extra 或 object metadata 合成 Gate/decision |
| D02-v1.0 | StateFamily 唯一 owner、typed fact、非法边 fail-closed | ES-04 adapter 不能新增或修复业务状态含义 |

旧 baseline 中 S12/S13 仅是待建槽位，没有 frozen truth 文件。本文件只继承 S01..05 已明确移交给 S12/S13 的义务；不会把旧提案、legacy 行为或未冻结候选升级为 truth。

### 1.2 Truth 到交付物映射

| Truth cluster | 本文件落点 |
|---|---|
| OT01-C004、OD-10 | §4.1 embedded Turso、driver isolation、单进程执行模型 |
| S01/S02 atomic Task obligations | §4.4、§5.4、§6.2 UnitOfWork/outbox/commit ordering |
| S03 claim/fence/recovery | §4.4、§5.3、§5.7、§6.3 transaction/CAS/scanner |
| S04 canonical acceptance/publication | §4.4、§5.3、§6.2 exact transaction profiles |
| S04 Artifact/orphan/missing bytes | §4.7..4.11、§5.6、§6.4..6.7 |
| S05 Gate atomicity/evidence retention | §4.4、§5.3、§6.2/6.3 |
| payload_extra rule | §4.3、§5.2/5.3 schema profile and promotion guard |
| OT04-C005 | §6、§8 failure injection and proof matrix |

### 1.3 唯一 ownership

| Concern | 唯一 owner | ES-04 权限 |
|---|---|---|
| Team/Task/Audit/Restart | ES-01 | 实现 repository/UoW、约束与 outbox；不解释合法状态边 |
| Workflow/Execution/Process | ES-02 | 实现 immutable registry、claim/CAS/lease 与 scanner query；不选 route |
| Intake/Gate/Candidate/Artifact logical truth | ES-03 | 实现 transaction、FK、CAS、object ref；不制造业务 proof |
| Registry/derived/vector tables | ES-05/06/07 | 已提供统一物理 profile与exact mapping；业务语义仍归对应ES |
| Schema migration | ES-04 MigrationOwner | 只改变 physical representation，不重解释历史业务 truth |
| Unit of Work | ES-04 PersistenceLane | 提交 caller owner 已验证的 command；不调用 domain policy |
| Outbox/inbox/domain event | ES-04 DeliveryLedger | 记录交付和因果事实；不是 Workflow/Process 状态 |
| Object bytes/reference/GC | ES-04 ObjectStoreOwner | 写、验、引用、释放、删除 physical substrate；不改变 Artifact lifecycle |
| Backup/restore 与运行 policy | ES-04 contract，ES-08 operator | ES-04 定义一致性协议；ES-08 定义命令、权限、排程与告警 |

### 1.4 决策证据

| 证据 | 可采用事实 | 本文件结论 |
|---|---|---|
| Turso Python quickstart | 本地/embedded Python 推荐 pyturso；remote 使用 libsql client | 主 driver 固定 pyturso，不设计双 driver |
| pyturso package release | 2026-07-14 的 0.7.0 是稳定版本；0.8.0rc1 是预发布 | v1 pin `pyturso==0.7.0`，升级必须重跑 §8 capability suite |
| Turso manual | in-process、WAL production path；当前 multi-process/multi-thread/savepoint 有限制，MVCC/并发模式是实验面 | 单进程、单 persistence lane、WAL、非 MVCC、不用 savepoint |
| Turso SQL reference | 支持 transaction、foreign key/PRAGMA、STRICT/JSON 等 SQLite-compatible surface | 启动 capability probe 后使用最小稳定 SQL 子集 |
| legacy smind-admin queue | DB row 与 async queue send 分离，queue 失败靠后续 status patch | 以 transaction outbox 替代双写窗口 |
| legacy io_manager/R2 | typed slot 与 streaming 可保留，但暴露 R2 key/backend、部分路径全量缓冲 | 保留 typed stream；删除 backend locator 与 unbounded buffer |
| legacy purger/process tables | fake Process、force/reset、随机 fallback identity、runtime/content/vector混表 | 删除 fake workflow 与混义 schema，使用 owner ledger/typed reference |

技术参考：

- https://docs.turso.tech/sdk/python/quickstart
- https://pypi.org/project/pyturso/
- https://github.com/tursodatabase/turso/blob/main/docs/manual.md
- https://docs.turso.tech/sql-reference/data-types
- https://docs.turso.tech/sql-reference/pragmas

---

## 2. Scope / Non-scope

### 2.1 Scope

ES-04 只负责：

1. embedded Turso driver、database file、connection/PRAGMA 与单 persistence lane；
2. 统一 physical type、STRICT table、PK/FK/UNIQUE/CHECK/index 与 payload_extra profile；
3. repository adapter、UnitOfWork、write serialization、CAS 和 transaction retry；
4. forward-only migration、checksum、bootstrap/readiness、bounded backfill 与 schema compatibility；
5. business mutation + outbox、inbox idempotency、domain event 与 semantic recovery scan；
6. 本地 team-scoped content-addressed object store、logical handle、stream write/read 与完整性验证；
7. DB 与 filesystem 的 bytes-first promotion/reference 协议、orphan 回收与 missing-object fail-closed；
8. object reference/release/delete proof、hold/fence 与安全 GC；
9. quiesced local backup/restore 的一致性协议；
10. ES-01..08 全部113张 owner logical tables 的物理映射登记。

### 2.2 Non-scope

- 不使用 Turso Cloud、remote database、embedded replica、remote sync、libSQL server 或双写数据库；
- 不启用 experimental MVCC、multi-process WAL、多进程 writer、多线程共享 connection 或 distributed transaction；
- 不建设独立 database service、object service、queue broker、Reconciler service、migration service 或 storage gateway；
- 不支持 S3/R2/MinIO、任意 filesystem backend、pluggable storage marketplace、bucket browser、signed URL、quota 或 billing；
- 不提供 public object upload/download/list/delete、absolute path、backend key、database query 或 raw-vector storage surface；
- 不建设 legacy schema/API/status/key 兼容、历史 import、dual-read、cutover 或 bootstrap data migration；
- 不在 transaction 内执行 HTTP、模型、OCR、filesystem stream、external vector engine或其他不受数据库控制的 I/O；ES-07 embedded vector BLOB SQL与vector_distance_cos属于同一DB engine受控操作；
- 不从 outbox、event、object、日志、mtime、path 或 digest 猜 canonical domain truth；
- 不在本文件定义业务状态边、Workflow route、Intake acceptance policy、模型 registry、LS-RAG schema 或 vector/index schema；
- 不承诺用户级 HA、online backup、multi-region、cross-device replication 或零停机 migration。

### 2.3 完成定义

ES-04的`ready`是规范状态：以下义务已被完整定义并通过cross-spec audit，不表示它们已在尚未构建的实现上运行。任何实现要声明符合ES-04-v1.0并进入release，必须同时满足：

1. pinned driver 在目标运行环境通过 §8 capability probe；
2. ES-01..08 所有 owner table 均登记物理 mapping，生成 DDL 与逻辑 schema 无损对账；
3. 每个跨表 mutation 都有 named transaction profile、fault injection 和 post-commit evidence；
4. commit-before-wake、inbox idempotency、stale fence、busy/restart 均无重复 business effect；
5. object write 在每个 crash point 只产生可用 immutable object 或可回收 orphan，不产生 canonical missing reference；
6. canonical object missing/corrupt 时 read fail-closed，并产生 typed incident/repair intent；
7. reference ledger/hold/grace 能证明 open Gate、active runtime、current/serving/history/backup 所需 bytes 不被 GC；
8. fresh migration、upgrade、failed migration、backup、restore 和 integrity validation 有自动化证据；
9. architecture tests 证明 domain/application 不导入 driver、path、filesystem 或 delivery implementation；
10. ES-08 对本文件的配置、权限、监控、容量与 runbook 完成最终对账。

### 2.4 核心术语

| 术语 | Exact 含义 |
|---|---|
| Persistence lane | 单体内唯一持有 database connection 与执行 SQL 的有界串行执行通道；不是服务/Process/StateFamily |
| UnitOfWork | 一个 `BEGIN IMMEDIATE ... COMMIT/ROLLBACK` 范围内的 repository command |
| CAS | 以 owner revision/status/fence/expected digest 为 guard 的条件更新；0 row 是 conflict，不是成功 |
| Outbox message | 与 business truth 同事务提交的 durable delivery intent；wake 只作 hint |
| Inbox receipt | consumer 对 message UUID + digest 的 durable去重事实，与 business effect 同事务提交 |
| Domain event | 已提交 transition/decision 的 immutable audit fact；不替代 current row |
| Stored object | content-addressed bytes 的 physical substrate record；不是 IntakeArtifact 或 derived asset |
| Object reference | owner logical artifact 到 exact stored object 的 durable保护边 |
| Write reservation/outcome | transaction 外 stream/promote 的恢复事实；不是 storage lifecycle 状态机 |
| Logical object handle | 不暴露 path/backend 的 opaque internal ref，可在 team/owner guard 后解析 |
| Orphan | 已安全 promote 但尚无 live object reference 的 bytes；可以在 grace 后删除 |
| Missing object | canonical live reference 指向的 bytes 缺失/损坏；是 integrity incident，不得自动伪造 |

---

## 3. Scope Impact Audit

~~~text
Scope Impact Audit
- New product responsibility: no
- New externally visible behavior: no
- New V1 capability: no
- New domain identity or StateFamily: no
- New deployment/runtime unit: no
- New owner-truth file: no
- New execution-spec file: no
- Raises a fixed capacity ceiling: no
- Can be solved inside an existing file and boundary: yes
- Classification: no expansion
~~~

`persistence lane`、migration ledger、outbox/inbox、stored object、reservation、reference 和 integrity incident 都是既有 truth 的物理实现或运行事实，不增加产品 identity、公开能力或 StateFamily。选择 embedded database 与 local CAS 反而明确关闭 cloud、remote sync、多 backend、distributed queue 和对象产品面。后续 ES 只能在本文件的物理 profile 中登记自己的既有表，不能借存储抽象扩大 scope。

---

## 4. Architecture Decisions

### 4.1 数据库与进程模型

固定选择：

| 维度 | v1 决策 | 禁止 |
|---|---|---|
| Python driver | `pyturso==0.7.0` exact pin | unpinned、0.8 prerelease、runtime dual driver |
| Database mode | embedded local database file | remote URL、Cloud、embedded replica、sync |
| Application topology | 一个 Python process、一个 release unit | 多 worker process 共享 DB |
| SQL execution | 一个 bounded persistence executor/lane owns connections | 任意 coroutine/thread 直接持 connection |
| Journal | WAL | experimental MVCC/concurrent WAL |
| Write transaction | `BEGIN IMMEDIATE`，全量串行 | deferred write race、savepoint nesting |
| Read transaction | 同 lane 的 bounded snapshot read；需要一致多表读取时显式 `BEGIN` | 长时间或无界 read transaction |
| Commit boundary | 只包含 SQL 与内存中的纯验证结果 | network/model/filesystem/vector I/O |
| Queue | DB outbox + 单体内 scanner/wake loop | external broker、DB/queue 双写 |

Persistence lane 是 application 内部模块。Async caller 将一个 typed command 和 deadline 提交给有界队列；lane 在自己的执行上下文中打开 connection、执行 UoW 并返回 typed result。队列满或 deadline 已到时在进入 transaction 前失败；不得无限堆积。业务 domain 只依赖 Protocol，不知道 driver、SQL 或 thread。

### 4.2 Startup capability probe 与 PRAGMA profile

Migration 命令和正常启动都必须先验证 exact driver/runtime capability；正常启动不自动迁移。

固定 PRAGMA：

~~~sql
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;
PRAGMA synchronous = FULL;
PRAGMA busy_timeout = 5000;
PRAGMA temp_store = MEMORY;
~~~

每个新 connection 都重新设置并读取校验 `foreign_keys`、`journal_mode`、`synchronous` 和 `busy_timeout`。启动 probe 在独立 scratch database 验证：

1. `BEGIN IMMEDIATE`、rollback、commit 与 writer exclusion；
2. FK/UNIQUE/CHECK/STRICT rejection；
3. required JSON type/function 与 canonical object round-trip；
4. WAL reopen、crash recovery 和 `PRAGMA quick_check`；
5. parameter binding、row count、generated constraint error classification；
6. large integer、UTC text、64-hex digest 与 binary-free row round-trip；
7. driver exception 不泄漏 SQL parameter、secret 或 path；
8. migration lock 和 process-local ownership guard。

任一 required capability 不成立则 readiness false、normal service 不接收请求。不得自动降级为 SQLite、libsql remote、弱同步、无 FK、无 STRICT 或 JSON text loose mode。

### 4.3 统一 physical schema profile

#### 4.3.1 类型映射

| Logical type | Physical Turso type/constraint |
|---|---|
| UUID | `TEXT NOT NULL`；application 写前校验 canonical lower-case RFC 4122 string，业务 UUID 只允许 v4/v7 |
| UTC timestamp | `TEXT NOT NULL`；canonical RFC3339 UTC microsecond form，lexical order = time order |
| SHA-256 digest | `TEXT NOT NULL CHECK(length(x)=64 AND x NOT GLOB '*[^0-9a-f]*')`；protocol envelope可写 `sha256:<hex>`，落库 digest 列只保存64位 lower hex |
| enum/key/version | `TEXT` + explicit CHECK 或 immutable definition FK；禁止 free-form status |
| boolean | `INTEGER NOT NULL CHECK(x IN (0,1))` |
| counter/size/revision | `INTEGER` + `CHECK(x >= 0)`；需要正数时 `> 0` |
| bounded string | `TEXT` + application schema length + DB CHECK |
| JSON object | `TEXT NOT NULL` + `CHECK(json_valid(x) AND json_type(x)='object')`；写入 canonical UTF-8 JSON |
| nullable ref | `TEXT NULL` + FK；pair/triple existence 用 CHECK |
| bytes | 禁止存入 business table；转为 logical object handle/digest/size |

所有 MKB-owned business tables 使用 STRICT mode。除 `schema_migrations`、Turso engine/private/shadow table 和不可控第三方 virtual table 外，每张 owner table 都有 `payload_extra` canonical JSON object。核心 identity、state、owner、route、proof、pointer、capability binding、secret/path不得只存在 `payload_extra`。

Payload promotion 规则：一旦 production read/guard/query/index 依赖某 key，就必须通过 forward migration 晋升 typed column、backfill、validate、switch read 后才可作为逻辑输入；未晋升 key 只能 round-trip，不能影响行为。

#### 4.3.2 约束与删除

- 每个 identity table 使用其 exact UUID 作 primary key；association/immutable ledger 使用来源 ES 定义的 composite uniqueness；
- 所有跨 owner 引用都带 `team_uuid`，用 composite FK 或同事务 owner check 阻止跨 Team 关联；
- 所有 FK 默认 `ON DELETE RESTRICT`；v1 不使用 cascade 删除 business truth；
- root-only/active-only uniqueness 不依赖未经 probe 的 partial index：用 nullable slot column，例如 root row 为 `root_slot=1`、非 root 为 null，再建 UNIQUE；
- immutable ledger 禁止 UPDATE/DELETE repository method；current row mutation必须携带 `expected_revision` 或 exact expected fence；
- status CHECK 只是最后防线，合法 transition 仍由唯一 domain owner + guarded UPDATE 执行；
- 不用 trigger 决定业务状态、route、pointer或 event；原子 effect 在 named UoW 显式写入并验 row count；
- 不用 view 隐藏 owner truth；只读 projection 可由 query adapter构造，不能成为 SSOT。

#### 4.3.3 Index profile

每张表只有已知 query/guard 所需 index：

1. identity PK 和 natural idempotency UNIQUE；
2. composite team-scoped owner FK index；
3. Task polling `(team_uuid, created_at, task_uuid)`；
4. Process claim `(status, next_attempt_at, priority, created_at, process_uuid)` 与 lease recovery；
5. outbox due scan `(delivered_at, dead_lettered_at, available_at, next_delivery_at, message_uuid)`；
6. object reference `(team_uuid, stored_object_uuid, released_at)` 与 owner reverse lookup；
7. orphan/GC `(reference_count, promoted_at, delete_after, stored_object_uuid)`；
8. source/snapshot/item/revision/gate exact guards由 ES-03 mapping登记。

禁止 speculative secondary index。ES-08 benchmark 证明 query 超预算后，才能在相同表和既有 contract 内增加 index；这不是 owner问题。

### 4.4 Transaction 与 UnitOfWork

#### 4.4.1 固定协议

~~~text
caller validates syntax/auth and builds typed command
  → submit(command, deadline, idempotency/correlation) to persistence lane
  → BEGIN IMMEDIATE
  → load exact owner rows
  → owner domain service validates state/guard in memory
  → guarded SQL writes; every expected row count checked
  → append audit/domain event/outbox required by transaction profile
  → invariant query/check
  → COMMIT
  → return committed receipt
  → best-effort local wake; scanner guarantees eventual pickup
~~~

任何 SQL/constraint/invariant/serialization failure执行 whole transaction rollback。v1 不用 savepoint，不在 UoW 内捕获局部错误后继续提交，也不将 rollback 后对象当作成功。

#### 4.4.2 Error 与 retry

| 类别 | 处理 |
|---|---|
| business CAS conflict / stale revision/fence | rollback，返回 typed conflict；不自动重放 command |
| duplicate same idempotency key + same request digest | 返回已提交 receipt/result；不重复 effect |
| duplicate same key + different digest | rollback，typed idempotency conflict |
| busy/temporary transaction acquisition | transaction 外 bounded retry，默认最多 3 次、20/50/100ms + deterministic task-derived jitter |
| constraint violation | rollback，映射 typed integrity/business error；不 retry |
| driver I/O/corruption/quick_check failure | stop writes/readiness false，产生受控 incident；不得自动建新 DB |
| caller cancellation before begin | 不开 transaction |
| caller cancellation after begin | lane 必须完成 rollback/commit decision；不能中断在未知态 |
| deadline crossed in transaction | rollback；若 COMMIT 已返回则结果仍 committed，通过 idempotency readback确认 |

Retry 重建 connection 前必须重新应用 PRAGMA 与 capability guard。禁止重试一个包含 non-idempotent external side effect 的 closure；UoW closure 只能执行 SQL 与纯内存逻辑。

### 4.5 Migration 与 schema lifecycle

#### 4.5.1 命令边界

同一 application artifact 提供显式、operator-only 的 `migrate` mode；它不是新部署单元。Normal `serve` mode只读取 schema metadata并校验 exact compatible head：

~~~text
migrate:
  exclusive process lock
  → backup prerequisite check for non-fresh DB
  → capability probe
  → current migration/checksum audit
  → apply forward migrations in order
  → validate constraints/FK/quick_check/backfill proofs
  → record checksum + artifact build
  → close cleanly

serve:
  process ownership lock
  → capability + schema head/checksum audit
  → object root/DB identity audit
  → start persistence lane/scanners
  → readiness true
~~~

#### 4.5.2 Migration rules

- migration ID 是单调四位整数加稳定名称；SQL/transform checksum immutable；
- 每个 migration 只能 apply 一次；已记录 ID 的 checksum mismatch 必须 fail-loud；
- fresh database 从 migration 0001 建立，不装 legacy schema 或 seed business data；
- compatible change 用 expand → bounded keyset backfill → validate → application switch → later contract；
- table rebuild 必须在独占 migration mode完成，并验证 row count、canonical digest、FK 与 indexes；
- 不修改 historical enum/semantic definition 的含义；新 version 新 row，不原位重解释；
- failed migration rollback 时 schema head不前进；不能原子 rollback 的 DDL 必须用 shadow-new/copy/validate/rename 的可恢复 step ledger；
- migration 不发 domain event、Task、Execution、Process 或 product notification；只留 migration evidence；
- downgrade/rollback migration、online migration、legacy import均不支持；恢复使用 verified backup 到 empty target。

### 4.6 Outbox、inbox 与 event architecture

#### 4.6.1 Outbox

所有需要 transaction 后运行的工作，以 `outbox_messages` 与 business mutation 同事务创建。Commit 后 local wake 只降低延迟；periodic keyset scanner 才是恢复保证。Delivery 是 at-least-once，consumer 必须用 inbox或其 owner-defined idempotency guard。

~~~text
business UoW commits message
  → wake hint or periodic due scan
  → claim message with lease_token_hash + fencing_generation
  → decode exact schema/digest
  → deliver to in-process consumer
  → consumer inbox + business effect commits atomically
  → mark outbox delivered with matching claim fence
~~~

Outbox 不代替 Process ready/retry_wait、Gate decision、Intake scheduling intent 或 cleanup intent。它只投递 exact 已提交事实；扫描器可以由 owner truth重建缺失 wake，但不能从 payload猜业务状态。

Payload使用object handle时，同一UoW必须建立`outbox_payload` object reference；只有delivery terminal、消费证据和消息retention同时满足后才能由cleanup owner释放。Domain event使用object payload时同理建立`domain_event_payload` reference，历史retention未到前不得释放。

#### 4.6.2 Inbox 与 domain event

Inbox key 是 `(consumer_key, message_uuid)`。同 UUID + 同 digest 返回 original receipt；同 UUID + 不同 digest 是 integrity conflict。Consumer effect 与 inbox receipt必须同一 UoW；只写 inbox 后再异步写业务 effect 被禁止。

Domain event 记录已提交 owner transition 的 before/after revision、causation/correlation、safe typed payload digest与proof ref。Event 不能执行 event sourcing replay来重建 v1 current tables，也不能被 caller查询为产品 API；它服务审计、debug与一致性核对。

### 4.7 Local content-addressed object store

#### 4.7.1 Backend 与 layout

固定 backend 是与 embedded DB 同一部署挂载中的本地 POSIX-like filesystem。它必须支持同 filesystem 原子 rename、exclusive create、fsync file与directory、no-follow open和权限隔离。

~~~text
<object_root>/
  identity.json
  objects/<team_uuid>/sha256/<hex[0:2]>/<hex[2:4]>/<64-hex-digest>
  staging/<team_uuid>/<reservation_uuid>.tmp
  quarantine/<team_uuid>/<incident_uuid>.bin
  backups/<backup_uuid>.tmp/
  backups/<backup_uuid>/
~~~

`identity.json` 绑定 deployment/database identity 与 format version，只能由 bootstrap/migration command创建。DB 只保存 opaque handle、team、digest、size、media与owner reference；任何业务 wire、event、Process payload或日志都不得保存绝对路径。

内容寻址范围固定为 Team：相同 Team + 相同 digest/size 复用 bytes；不同 Team 即使 digest相同也使用独立目录与 `stored_objects` row，避免跨 Team existence/timing 泄漏。v1 不做 application-level compression/encryption；at-rest volume protection归ES-08。

#### 4.7.2 Logical handle

Exact handle grammar：

~~~text
mkbobj:v1:<team_uuid>:<stored_object_uuid>
~~~

Handle 是内部 typed ref；解析必须同时取得 authenticated Team、owner kind/UUID、live reference与expected digest/size。只持 handle 不能绕过 Team 或 owner authority。Handle 不含 path、digest、media、revision、secret或backend。

### 4.8 Object write / promote protocol

写入是 transaction 外 streaming operation，固定顺序：

1. UoW 创建 `object_write_reservations`，冻结 team、owner intent、expected digest/size/media、budget、idempotency、expiry；
2. writer 以 exclusive create 打开同 filesystem staging path，并以 bounded chunks stream；不全量缓冲；
3. 边写边计算 SHA-256、size，执行 budget/media checks；失败关闭并记录 failed outcome，temp可立即或scanner清理；
4. `fsync(temp file)`，比较 expected/actual digest/size；不一致不得 promote；
5. 建立 final parent directories，以 no-follow/containment guard 验证 root；
6. 若 final 不存在，原子 promote 到 final；若已存在，读取并验证 exact digest/size 后复用，禁止覆盖不同 bytes；
7. `fsync(final parent directories)` 后 UoW append `object_write_outcomes(promoted)`；
8. 业务 owner 的独立 canonical UoW 创建或复用 `stored_objects`，append `object_references` 和 logical Artifact/proof；
9. 若第8步失败，final bytes 是 unreferenced orphan，保留 grace后由GC处理；不得删除一个可能被并发 UoW引用的 object；
10. caller只在 canonical UoW commit 后收到 usable logical handle/Artifact result。

文件系统没有 portable no-clobber rename时，实现必须使用 exclusive final create + verified copy/fsync + atomic visibility protocol，并通过 §8 crash suite；不得用普通 overwrite rename制造 concurrent digest race。

### 4.9 Object read / verification protocol

~~~text
authenticated/internal caller presents owner ref
  → DB snapshot resolves owner → live object_reference → stored_object
  → verify team/owner/purpose/expected digest+size
  → construct path only from validated team+digest under configured root
  → open no-follow; verify regular file and containment
  → stream bounded chunks while hashing/counting
  → only after EOF digest+size match return verified completion
~~~

Streaming consumer可以在读取中产生 transaction 外临时结果，但不能提交 canonical output/publication proof，直到 object reader给出 verified completion。文件 absent时先重新读取reference/object revision：若其在解析后被合法release/delete，返回stale-reference conflict；若live reference仍存在才记录missing incident。Symlink、non-regular、size mismatch、digest mismatch或未授权/released owner ref一律 fail-closed；live integrity failure记录 `object_integrity_incidents` 并提交 source domain 的 typed repair intent。禁止返回partial bytes为成功、创建空文件、从备份静默代替或更新 expected digest。

### 4.10 Reference、retention 与 GC

所有 canonical/历史/运行中需要的对象都以 immutable `object_references` 保护。Reference purpose 固定 registry，由 owner ES 选择，例如：

- intake_snapshot_artifact、intake_revision_artifact；
- candidate_or_preflight_evidence、open_gate_evidence；
- process_input、process_output、runtime_recovery；
- generation_artifact、generation_invocation_evidence；
- vector_or_index_build_input、publication_proof；
- backup_hold、legal_or_operator_hold。

Release 不是删除 reference row，而是 append `object_reference_releases` 并 CAS 设置 `released_at/release_reason/ref_revision`。历史必须保留到来源 domain retention明确允许释放；soft delete、Process cleanup、Task terminal或 latest/current切换本身不自动释放。

GC eligibility 必须同时满足：

1. 没有未释放 reference；
2. 没有有效 hold、open Gate、nonterminal runtime、current/serving/index pointer或未完成 backup依赖；
3. promoted/outcome 已过 orphan grace；
4. reservation/outcome 已终结且无并发 canonical UoW fence；
5. owner-specific cleanup intent/proof要求已满足；
6. scanner以 observed reference ledger revision 建立 delete fence，删除前再次 CAS/recheck；
7. bytes删除与parent fsync完成后 append `object_delete_proofs`，保留 stored object tombstone/metadata；
8. 删除失败可安全重试；missing-at-delete区分已验证不存在与未知 I/O failure。

GC 从不删除 database business rows。无 reference 的 orphan只能在默认 24 小时 grace 后候选；有 history/hold 的对象无自动时限。ES-08 可在实测容量内调大 grace，不能调成 0 或绕过 fences。

### 4.11 Backup / restore consistency protocol

v1 只支持显式 quiesced local backup：

~~~text
stop new admissions and delivery claims
  → drain current UoW/object promotions
  → acquire maintenance fence
  → checkpoint WAL and close persistence connections
  → enumerate exact DB + all live/held object refs
  → copy DB and referenced objects into backup_uuid.tmp
  → build canonical manifest with size/digest/schema head/object-root identity
  → verify copied DB quick_check/FK and every object digest
  → fsync files/directories
  → atomic rename backup_uuid.tmp → backup_uuid
  → release maintenance fence and reopen service
~~~

Backup manifest是运维文件合同，不是 domain identity。Backup失败只删除/隔离 `.tmp`，不得标记完整或影响 active data。

Restore只能写入明确 empty target：先验证manifest、application/schema compatibility、DB `quick_check`/FK、row/object reference closure和全部digest，再启动一次 read-only smoke audit；通过后由operator切换部署路径。禁止原位覆盖 active DB/object root、merge两个backup、从不完整manifest恢复或自动降级schema。Retention、排程、密钥、权限与演练频率归ES-08。

---

## 5. Contracts and Data

### 5.1 Schema composition 与命名

完整 physical schema 由两部分共同构成：

1. owner ES 的 exact logical columns、业务 CHECK、合法 enum、immutability、uniqueness 与 query；
2. 本文件 §4.3 的 physical type/FK/index/profile，以及 §5.4..5.6 的 infrastructure tables。

两部分都是 normative。Migration renderer 必须从 versioned table manifest 生成实际 SQL，并在 CI 输出 column/constraint/index diff；不得手写一份语义不同的“运行 DDL”。Owner ES 改列时，必须同时更新本节 inventory 和 migration，最终 cross-spec audit 前不得把 ES-04 标记 ready。

命名固定规则：

- 表/列/index/constraint 使用 lower_snake_case；
- PK index `pk_<table>`，unique `uq_<table>__<meaning>`，FK `fk_<table>__<target>`，check `ck_<table>__<meaning>`，普通 index `ix_<table>__<query>`；
- 所有显式 constraint name稳定，便于 error mapper；
- reserved SQL keyword不得用作无引号 identifier；
- engine/private tables以 `_turso_`/`sqlite_` 等保留 prefix识别，不进入业务 schema；
- table manifest为 `mkb.persistence-table-manifest.v1`，按 table name排序后计算 bundle digest。

### 5.2 上游 owner table physical inventory

#### 5.2.1 ES-01 Service / Task：4 tables

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| teams | team_uuid | creation fingerprint uniqueness；status/time scan；revision CAS | owner-current，soft lifecycle |
| tasks | team_uuid+task_uuid | intent/idempotency、six-state CHECK、root/generation fence、poll/claim/trace indexes | owner-current + immutable input |
| task_audits | team_uuid+task_uuid FK tasks | one-to-one；trace equal guard；no update/delete adapter | immutable ledger |
| task_restarts | restart_uuid；team/source Task owner | command idempotency；atomic/full scope XOR；source/target/generation indexes | immutable decision ledger |

Exact columns与业务 constraints引用 ES-01 §5.2..5.5。额外物理约束：

- `teams`同时提供 `UNIQUE(team_uuid, revision)` target，使 team-scoped owner CAS可被复合引用；
- `tasks`提供 `UNIQUE(team_uuid, task_uuid, current_generation)` 和 `UNIQUE(team_uuid, task_uuid, revision)` target；
- `current_root_execution_uuid` 的闭环 FK 因 tasks 与 executions 建表互引，migration先建 nullable column，再在 manifest validator执行 same team/task/generation invariant；repository只能经 ES-01 owner设置；
- `task_restarts`为 accepted/rejected 两类事实，用 CHECK 保证 accepted target必填、rejected target为空；不得增加 restart status。

#### 5.2.2 ES-02 Workflow Runtime：9 tables

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| workflow_registry | workflow_uuid | global workflow_key unique；selector index；active revision same workflow | owner-current pointer |
| workflow_revisions | workflow_revision_uuid | workflow+revision unique；registration fingerprint/digest guard | immutable after registration |
| workflow_steps | workflow_step_uuid | revision+step_key unique；same-revision composite FK | immutable child |
| workflow_routes | workflow_route_uuid | revision+route_key/from-selector unique；same-revision from/to | immutable child |
| workflow_bindings | workflow_binding_uuid | step+kind+slot unique；typed-value XOR | immutable child |
| workflow_controls | workflow_control_uuid | exact scope XOR；heartbeat<lease；nonnegative budgets | immutable child |
| workflow_guards | workflow_guard_uuid | exact scope/order unique；typed expected XOR | immutable child |
| executions | execution_uuid；Task/generation owner | root slot uniqueness、tree FK、status/wake/subject indexes、revision CAS | StateFamily owner-current + append-only facts |
| processes | process_uuid；Execution owner | materialization unique、claim/due/lease indexes、fence/retry constraints | StateFamily owner-current + immutable outcome |

Exact columns与业务 constraints引用 ES-02 §5.2..5.5。物理 spelling：

- `executions.root_slot INTEGER NULL CHECK(root_slot IS NULL OR root_slot=1)`；root必须1、child必须null，`UNIQUE(team_uuid,task_uuid,generation,root_slot)`；
- tree FK 使用 `(team_uuid,task_uuid,generation,execution_uuid)` composite candidate key，禁止跨 Task/generation parent/root/retry link；
- `processes`提供 `(execution_uuid,process_uuid)` candidate key，`executions.current_process_uuid`通过同 owner query/CAS验证；
- claim transaction读取eligible row并以 `status/revision/fencing_generation/available_at/lease` guarded update；不依赖 `SELECT FOR UPDATE`、savepoint或 trigger；
- Workflow registry activation与完整 revision+children registration在一个 UoW；active children无 update/delete repository。

#### 5.2.3 ES-03 Intake / Cleaning：34 tables

Canonical 10表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| intake_sources | team_uuid+intake_source_uuid | source identity/external resource unique；row revision CAS | owner-current admission fact |
| intake_snapshots | team_uuid+intake_snapshot_uuid | source observation/fingerprint uniqueness；completeness proof CHECK | immutable canonical truth |
| intake_items | team_uuid+intake_item_uuid | source+external key unique；same-item latest/serving FK；row revision CAS | Item StateFamily owner |
| intake_revisions | team_uuid+intake_revision_uuid | item+ordinal/fingerprint unique；same-item predecessor | immutable canonical truth |
| intake_artifacts | team_uuid+intake_artifact_uuid | snapshot XOR revision owner；logical object ref/digest/size | immutable logical Artifact |
| intake_snapshot_memberships | team_uuid+snapshot+ordinal | snapshot+external key unique；decision ref XOR | immutable collection SSOT |
| intake_semantic_definitions | semantic_key+definition_version | same version/digest idempotency；registry digest | immutable registry |
| intake_revision_semantics | team_uuid+revision+semantic_key | exact definition FK；typed value XOR | immutable semantic ledger |
| intake_action_definitions | action_key+definition_version | closed effect mask；same version/digest guard | immutable registry |
| intake_item_transitions | transition_uuid；team/item owner | transition fence unique；before/after revision continuity | immutable transition ledger |

Source/evidence/staging 10表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| intake_source_kind_definitions | source_kind_key+definition_version | four-key CHECK；digest guard | immutable registry |
| intake_execution_bindings | team_uuid+execution_uuid | same team Execution/Source；exact binding digest | immutable binding |
| intake_acquisition_evidence | team_uuid+evidence_uuid | Process/fence/evidence digest unique；result payload CHECK | immutable fact |
| intake_clean_artifact_candidates | team_uuid+clean_candidate_uuid | producer fence；remediation ordinal 0/1 | immutable fact |
| intake_candidate_sets | team_uuid+candidate_set_uuid | observation uniqueness；four-state CHECK；row revision CAS | CandidateSet StateFamily owner |
| intake_candidate_pages | team_uuid+set+page_ordinal | range/count/digest checks；same page replay unique | immutable page ledger |
| intake_candidate_members | team_uuid+candidate_member_uuid | set+ordinal and set+normalized key unique | immutable member ledger |
| intake_candidate_semantics | team_uuid+member+semantic_key | exact definition FK；typed value XOR | immutable staging fact |
| intake_candidate_artifact_refs | team_uuid+member+role+ordinal | stored handle/digest/size exact guard | immutable staging ref |
| intake_candidate_anomalies | team_uuid+anomaly_uuid | candidate/member/page scoped XOR；typed kind CHECK | immutable anomaly fact |

Preflight/Gate 7表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| preflight_validator_manifests | validator_key+validator_version | manifest digest/handler/check-set exact binding | immutable registry |
| preflight_allowlist_bindings | binding_key+binding_version | selector unique；exact validator/policy refs | immutable registry |
| preflight_outcomes | team_uuid+outcome_uuid | exact input uniqueness；scope/ref XOR；result CHECK | immutable outcome |
| preflight_check_evidence | team_uuid+outcome+check_ordinal | outcome/check ordering unique | immutable evidence |
| execution_review_targets | team_uuid+review_target_uuid | same Task/Execution/generation/target digest | immutable target |
| execution_gates | team_uuid+gate_uuid | target uniqueness；four-state/terminal evidence CHECK；revision CAS | Gate StateFamily owner |
| execution_gate_decisions | team_uuid+decision_uuid | gate+idempotency unique；fingerprint conflict guard | immutable decision |

Change/repair/cleanup 7表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| intake_change_sets | team_uuid+change_set_uuid | snapshot/candidate one-to-one；digest/count checks | immutable aggregate fact |
| intake_change_facts | team_uuid+set+fact_ordinal | typed fact enum/ref CHECK | immutable fact |
| intake_source_transitions | source_transition_uuid；team/source owner | fence unique；revision continuity | immutable transition ledger |
| intake_scheduling_intents | scheduling_intent_uuid；root owner | root+materialization unique；typed ChangeSet FK | durable business intent + delivery projection |
| intake_repair_intents | repair_intent_uuid；team/target owner | allowed repair enum；monotonic resolution CAS | immutable request + completion fact |
| intake_cleanup_intents | cleanup_intent_uuid；team/target owner | proof counts/hold snapshot/completion CHECK | immutable request + completion fact |
| intake_cleanup_proofs | team_uuid+intent+substrate+target_ref | exact intent/target/digest uniqueness | immutable proof |

Exact columns与业务 constraints引用 ES-03 §5.3..5.6。额外物理约束：

- 所有 team-owned definitions/refs通过 team复合 key或owner query fence；global code registry不得含 Team data；
- ES-03 中逻辑 partial unique 均映射为 nullable slot或 full unique，不依赖 trigger；
- `intake_artifacts.logical_locator`、candidate staged handle及 evidence ref若指 object，必须以 §5.6 reference ledger闭合；仅保存 handle不算 live reference；
- CandidateSet accepted、Snapshot/Membership/ChangeSet、Item/Revision/Transition、typed scheduling intent与generic outbox在同一个 `intake_acceptance_v1` UoW；
- Gate decision、Gate CAS、Execution CAS、domain event与outbox在同一个 `gate_resolution_v1` UoW；
- `intake_scheduling_intents`保留独立 typed business row；generic outbox用 `aggregate_kind=intake_scheduling_intent`引用它，不合并丢列。

#### 5.2.4 ES-05 Inference / Registry：18 tables

Capability 6表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| process_capability_manifests | process_key+contract_version | manifest digest/handler/schema/proof/idempotency exact guard | immutable definition + governance projection |
| process_capability_phases | capability+phase_key | phase ordinal unique；ES-02 finite phase FK/check | immutable child |
| process_capability_ports | capability+direction+port_name | direction ordinal unique；exact schema FK | immutable child |
| process_capability_parameters | capability+parameter_name | typed default XOR/range/allowed set | immutable child |
| process_capability_error_policies | capability+error class+code | retryability/replay/recovery exact enum | immutable child |
| process_capability_resource_access | capability+access ordinal | resource/operation/purpose unique | immutable child |

Schema/Model/Prompt/Profile 8表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| schema_definitions | schema_key+schema_version | content/definition digest；kind/dialect/limit checks | immutable definition + governance projection |
| schema_definition_components | schema+role+ordinal | component key/version/digest unique；role closure | immutable child |
| schema_consumer_support | consumer+schema+mode | exact schema digest/support mode | immutable compatibility fact |
| model_definitions | model_key+model_version | local/external XOR；adapter/model/binary/limit/policy digest | immutable definition + governance projection |
| model_capabilities | model+capability+modalities | finite capability/modality checks | immutable child |
| prompt_definitions | prompt_key+prompt_version | template/schema/process/purpose/evaluation exact refs | immutable definition + governance projection |
| prompt_variables | prompt+variable_name | ordinal unique；typed/render-context checks | immutable child |
| inference_profiles | profile_key+profile_version | exact model/prompt/schema/validator/budget tuple | immutable definition + governance projection |

Invocation 4表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| generation_invocations | team_uuid+invocation_uuid | Process/fence/ordinal unique；request/binding immutable；dispatch CAS | immutable request + dispatch fact |
| generation_invocation_inputs | team_uuid+invocation+input ordinal | live object ref、same Team、ordered digest | immutable input ledger |
| generation_invocation_outputs | team_uuid+invocation+output ordinal | role unique、live object ref、schema/digest/size | immutable output ledger |
| generation_invocation_outcomes | team_uuid+invocation | one outcome；output-set/usage/error XOR | immutable terminal fact |

Exact columns与业务constraints引用ES-05 §5.2..5.7。额外物理约束：

- Global definition tables不得出现team/secret value；all child FK使用完整key+version；
- Definition semantic columns与children无update/delete repository；governance status/time只经guarded current projection + domain event UoW；
- Registry bundle install同时写definitions、children、object references、registry bundle manifest与event；任一失败whole rollback；
- Invocation reserve同时写request、ordered inputs、input object references；commit失败禁止adapter call；
- Invocation outcome同时写output rows、output object references、one outcome与event；same digest重放，different digest conflict；
- `dispatch_started_at`只允许null→timestamp CAS；outcome存在后不可修改；no-outcome recovery只能appendfailed/indeterminate outcome；
- Definition/Invocation logical handles均由ES-04 reference ledger保护，不能仅凭handle视为有效。

#### 5.2.5 ES-06 LS-RAG Build：21 tables

Generation artifact ledger 5表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| generation_artifacts | team_uuid+generation_artifact_uuid | execution/type/ordinal unique；five-type/disposition CHECK；same-team source/process/schema；live object ref | immutable derived ledger |
| generation_artifact_inputs | artifact+input_ordinal | input kind CHECK；ordered set digest；same-Team/global-schema owner closure | immutable child |
| generation_artifact_invocations | artifact+invocation_ordinal | ES-05 invocation same Team/Process/binding；relationship CHECK | immutable causation child |
| generation_validation_reports | team_uuid+validation_report_uuid | report artifact unique；artifact/artifact-set subject XOR；stage/overall closure | immutable proof |
| generation_validation_findings | report+finding_ordinal | stable order；stage/severity/repair-classification CHECK；pointer digest | immutable proof child |

Current selection/commit 4表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| generation_artifact_current_pointers | team_uuid+execution_uuid+artifact_type | target same execution/type/full-valid/commit；pointer revision CAS | owner-current SelectionPointer |
| generation_artifact_pointer_transitions | team_uuid+pointer_transition_uuid | execution/type/revision continuity；transition digest replay | append-only transition |
| generation_commits | team_uuid+generation_commit_uuid | Process/input/commit digest unique；same source/schema/build coordinate | immutable accepted bundle fact |
| generation_commit_artifacts | commit+artifact_type | exact five types/ordinals；member full-valid/same binding；set digest | immutable membership child |

Structure 5表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| structure_documents | team_uuid+structure_document_uuid | artifact one-to-one；root/count/coverage/digest closure | immutable normalized artifact |
| structure_source_elements | document+source_element_key | manifest same artifact；ordinal/coordinate unique；role/span/digest/reason XOR | immutable source child |
| structure_nodes | document+node_key | parent same document；preorder/leaf reading/source unique；closed class/kind | immutable tree child |
| structure_source_anchors | document+anchor_key | kind-specific coordinate XOR/range；element ordinal unique；same source | immutable grounding child |
| structure_node_anchor_bindings | document+node_key+anchor_key | leaf-only direct binding；binding ordinal unique | immutable relation |

Construction 3表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| construction_documents | team_uuid+construction_document_uuid | artifact one-to-one；exact structure/recipe/profile；count/digest closure | immutable normalized artifact |
| construction_units | document+unit_key | unit ordinal/pair unique；ordered non-overlap range；size CHECK；metadata authority | immutable partition child |
| construction_unit_nodes | document+unit_key+member_ordinal | leaf same structure；each leaf unique across units；ordered membership | immutable relation |

Retrieval projection 3表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| retrieval_block_projections | team_uuid+projection_uuid | artifact one-to-one；exact construction/structure；count/digest closure | immutable normalized artifact |
| retrieval_blocks | projection+block_key | ordinal/coordinate unique；kind/channel matrix；original/summary XOR invocation | immutable projection child |
| retrieval_block_anchor_bindings | projection+block+binding_ordinal | anchor same structure；coverage/citation/support role CHECK | immutable traceback relation |

Repair 1表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| generation_repair_changes | repaired_artifact+change_ordinal | extension pointer unique；source/repair invocation same binding；before/after digest | immutable repair ledger |

Exact columns与业务constraints引用ES-06 §5.1..5.7。额外物理约束：

- All cross-table FKs使用`team_uuid`复合键；GenerationArtifact、normalized artifact、commit和Invocation不得跨Team/Execution/source/schema；
- ValidationReport以`artifact|artifact_set` subject XOR消除Report↔Commit循环FK；Commit后引用report，report不反向依赖未存在commit；
- Tree parent composite FK同document；跨row single-root/acyclic/order/coverage由ES-06 validator在同UoW前证明，DB counts/digests/uniques再作防线；
- Five current pointers与five transitions、commit/members、ES-02 Process outcome/next outbox使用一个write transaction；任一row count/CAS失败whole rollback；
- Original block object ref必须resolve exact clean byte slice digest；summary block必须resolve exact ES-05 Invocation和citation rows；
- Owner tables均无delete repository；只有current pointer按expected revision CAS，所有其他语义行immutable。

#### 5.2.6 ES-07 Vector and Retrieval：24 tables

Registry 2表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| embedding_spaces | space_key+space_version / ES-07 semantic、ES-05 registry | exact model/recipe/schema FKs；dimension/scalar/metric/limit CHECK；definition digest unique | immutable code-owned registry |
| retrieval_policy_definitions | policy_key+policy_version / ES-07 | exact space/schema refs；finite score/budget CHECK；definition digest unique | immutable code-owned registry |

Embedding invocation 3表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| embedding_invocations | team_uuid+invocation_uuid / ES-07 | owner process/request XOR；reservation key unique；space/model exact；missing-outcome deadline index | immutable reservation |
| embedding_invocation_inputs | invocation+input_ordinal | ordinal/count closure；document block vs query XOR；digest/length only | immutable child |
| embedding_invocation_outcomes | team_uuid+invocation_uuid one-to-one | terminal disposition CHECK；success shape/count/dimension；safe evidence only | immutable terminal fact |

Vector build 4表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| vector_records | team_uuid+vector_record_uuid / ES-07 | projection/block/space unique；dimension=768 profile；digest/norm/size CHECK；block/space indexes | immutable semantic metadata |
| vector_record_payloads | team_uuid+vector_record_uuid FK | one live float32 BLOB；length/digest exact；payload presence index | physical payload insert / proof-gated delete |
| vector_build_manifests | team_uuid+manifest_uuid | process/fence/projection/space unique；block/vector count/set closure | immutable complete fact |
| vector_build_members | manifest+member_ordinal | continuous ordinal；block/vector each unique；same Team/projection/space | immutable relation |

Index/filter 4表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| index_generations | team_uuid+generation_uuid / ES-07 | Item+generation digest unique；input kind CHECK；target/source Revision、commit/projection/space FKs | immutable candidate |
| index_generation_inputs | team_uuid+generation_uuid one-to-one | full_embed vs filter/rebuild reuse XOR；manifest/predecessor exact | immutable lineage |
| index_generation_memberships | generation+membership_ordinal | block/vector unique；coordinate exact；generation/stratum search indexes | immutable relation |
| index_generation_filter_values | generation+path+value_ordinal | type-tag/typed-column XOR；canonical path/value digest；Team+path+type+value+generation indexes | immutable filter snapshot |

Validation/publication/pointer 5表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| index_validation_reports | team_uuid+report_uuid / ES-07 | generation+validator implementation unique；valid/invalid CHECK；count/digest closure | immutable report |
| index_validation_findings | report+finding_ordinal | severity/subject CHECK；safe digest evidence；error count closure | immutable child |
| publication_proofs | team_uuid+proof_uuid / ES-07 | exact Item/Revision/commit/projection/manifest/generation/report；publish-mode transition XOR | immutable proof |
| active_index_generation_pointers | team_uuid+item_uuid / ES-07 | target generation+Revision both-null/non-null；proof kind XOR；pointer revision CAS | mutable SelectionPointer |
| active_index_generation_transitions | team_uuid+transition_uuid | before/after pair CHECK；revision +1；proof-ref unique | immutable transition |

Withdrawal/cleanup/rebuild 4表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| index_withdrawal_proofs | team_uuid+proof_uuid / ES-07 | lifecycle/serving-null/pointer transition exact；no physical-delete claim | immutable proof |
| vector_cleanup_proofs | team_uuid+proof_uuid / ES-07 | closed subject kind；eligibility/hold/grace digests；delete counts | immutable proof |
| index_rebuild_plans | team_uuid+plan_uuid / ES-07 | scope closed union；target space/policy exact；ordered set digest | immutable plan |
| index_rebuild_plan_items | plan+item_ordinal | Item unique；route reuse/reembed CHECK；source/target/pointer fences | immutable plan member |

Retrieval evidence 2表：

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| retrieval_query_receipts | team_uuid+request_uuid / ES-07 | request values only digest/length；hits/empty/error XOR；snapshot fields nullable only pre-snapshot error | immutable 30d；proof-gated retention delete |
| retrieval_query_hits | request+hit_rank | continuous rank；snapshot provenance exact；finite scores；no text/vector columns | immutable 30d；group retention delete |

Exact columns与业务constraints引用ES-07 §5.1..5.10。额外物理约束：

- vector_records semantic row与vector_record_payloads物理BLOB分表；cleanup只删除payload并同事务写VectorCleanupProof，永不改写record lineage；
- Active/grace/live-plan引用存在时payload DELETE受owner guard阻断；active membership缺payload使readiness/query fail；
- vector_record_payloads.vector_blob只允许内部VectorRepository/DistanceSearchAdapter读取，不进入generic row dump、event、outbox、log或HTTP projection；
- startup capability probe必须证明vector32 encode/decode、vector_distance_cos、dimension、self distance、ordering、tie和backup/restore；失败readiness false；
- V1没有virtual/ANN/FTS table、shadow table、trigger或第二vector backend；schema manifest的engine-private exception set为空；
- ActiveIndexPointer non-null target必须FK到同Team Item/generation/Revision，PublicationProof有效性由owner validator与same-UoW row-count guard共同证明；
- intake_publication_v1按IntakeItem→ActiveIndexPointer固定锁序更新Item serving、index pointer与两类transition，same-Revision reindex也递增Item row revision；
- retrieval exact scan的covering indexes至少包含active pointer Team/Item、generation target/space、membership generation/stratum、filter typed value与vector payload PK；
- Query receipt/error不保存query/filter原值；retrieval_query_hits不保存正文、anchor坐标或vector，只保存authority refs/digests；
- 24表全部进入quiesced backup；restore后vector/pointer/proof/traceback完整性验证通过前不ready。

#### 5.2.7 ES-08 Operations, Security and Deployment：3 tables

| Table | PK / owner | Physical guard 与 required index | Mutation class |
|---|---|---|---|
| operational_runs | operational_run_uuid / ES-08 | closed operation kind；kind+idempotency unique；request/build/dependency/config digests；previous-run FK | immutable reservation |
| operational_run_steps | run+step_ordinal / ES-08 | continuous ordinal；run+step key unique；closed disposition/evidence kind；no append after terminal | immutable ordered evidence |
| operational_run_outcomes | operational_run_uuid one-to-one / ES-08 | succeeded/failed/indeterminate CHECK；required-step count/set digest closure；one evidence manifest | immutable terminal fact |

Exact columns与业务constraints引用ES-08 §5.1..5.4。额外物理约束：

- 三表均为global operational fact，不带Team authorization、business state、generic subject或public CRUD；
- operational_run只有0..1 outcome；outcome存在后step insert与run mutation全部拒绝；
- same operation kind/idempotency key + same request digest返回original run/outcome，different digest conflict；
- step ordinal从0连续增长；`succeeded` outcome必须重算required step count/set digest且不存在blocking finding；
- operational run/step/outcome全部保留deployment lifetime；V1无update/delete repository；
- physical manifest、backup/restore与readiness必须包含三表；它们不能代替owner event/proof或从operation outcome推进六StateFamily。

#### 5.2.8 Inventory completeness

截至 ES-04-v1.0：ES-01 4表 + ES-02 9表 + ES-03 34表 + ES-05 18表 + ES-06 21表 + ES-07 24表 + ES-08 3表 = 113张 owner tables，均已登记。加上ES-04自身13张infrastructure tables，physical manifest共有126张project-owned tables；engine内部catalog不计owner表且V1无ANN/FTS shadow表。任何新增/缺失/改名都使manifest diff与readiness失败。

### 5.3 Named transaction profiles

| Transaction key | Owner command | Required atomic writes | Required guard/result |
|---|---|---|---|
| team_create_v1 | ES-01 | Team row | creation fingerprint idempotency |
| task_create_v1 | ES-01 | Task + Audit + domain event + start outbox | same task fingerprint replay；different conflict |
| task_transition_v1 | ES-01 | Task CAS + summary/proof + event + needed outbox | exact status edge/revision/proof |
| task_cancel_v1 | ES-01 | cancel fact + Task CAS + event + cancel outbox | command UUID/fingerprint winner |
| task_full_retry_v1 | ES-01 | Restart + Task generation CAS + Audit evidence + root scheduling intent/outbox | no partial generation switch |
| atomic_item_rebuild_v1 | ES-01/03 | accepted Restart + new Task/Audit + rebuild scheduling intent/outbox | old Task/Item/Revision immutable |
| workflow_register_v1 | ES-02 | Workflow revision + seven child sets + activation CAS + registry bundle evidence | compiled/canonical digest exact |
| execution_start_v1 | ES-02 | root/child Execution + first Process or wait fact + outbox/event | subject/binding immutable |
| process_materialize_v1 | ES-02 | Process ready + route evidence + outbox | materialization unique |
| process_claim_v1 | ES-02 | guarded Process ready/retry_wait→claimed + new fence/lease | one claimant, row count=1 |
| process_start_heartbeat_v1 | ES-02 | guarded claimed/running CAS | current token hash+fence |
| process_outcome_v1 | ES-02 | Outcome acceptance + Process edge + route + Execution aggregate + next rows/outbox/event | exact manifest/proof/fence |
| process_recovery_v1 | ES-02 | lease/fence recovery edge + counters + outbox/event | stale worker fenced |
| execution_cancel_converge_v1 | ES-02 | descendant CAS/summary + Execution/Task proposal outbox | all descendants closed |
| intake_source_resolve_v1 | ES-03 | Source create/reuse or admission CAS + transition/event | identity/definition digest exact |
| candidate_open_append_v1 | ES-03 | Candidate CAS + page/members/semantics/artifact refs/anomalies | same page digest replay |
| candidate_preflight_v1 | ES-03 | PreflightOutcome + check evidence + Candidate binding CAS | exact root/item input uniqueness |
| intake_acceptance_v1 | ES-03 | Candidate sealed→accepted + Snapshot/Membership/ChangeSet/Facts + Item/Revision/Artifact/Transition + intents/outbox/event + object refs | entire canonical commit or rollback |
| intake_item_action_v1 | ES-03 | Item CAS + transition + event + needed outbox | exact ActionDefinition/proof |
| intake_publication_v1 | ES-03/07 | index report/findings + PublicationProof + active index pointer/transition + Item serving CAS/transition + Process Outcome/outbox | exact dual fence；old serving/index remain until whole commit |
| gate_open_v1 | ES-03/02 | ReviewTarget + Gate open + Execution waiting CAS + event/outbox | target/fence exact；no active lease |
| gate_resolution_v1 | ES-03/02 | Decision + Gate terminal CAS + Execution resume/fail CAS + event/outbox | expected gate revision+target digest |
| registry_bundle_install_v1 | ES-05 | definitions/children + definition object refs + bundle manifest + event | same version/digest no-op；different drift |
| registry_governance_change_v1 | ES-05 | exact definition status/time CAS + event | enabled→deprecated/disabled或deprecated→disabled only |
| invocation_reserve_v1 | ES-05 | Invocation request + ordered inputs + input object refs + event | Process current fence + request digest；commit before call |
| invocation_dispatch_v1 | ES-05 | dispatch_started_at CAS + event | null→timestamp once；current Process fence |
| invocation_outcome_v1 | ES-05 | output rows/refs + one outcome + event | same Invocation/binding/request；one outcome digest |
| lsrag_artifact_finalize_v1 | ES-06 | GenerationArtifact+inputs+Invocation links+validation report/findings+object refs+event | current fence/proven causation；same immutable digest replay |
| lsrag_structurize_finish_v1 | ES-06/02 | source/structure normalized rows+artifacts/reports/refs + Process Outcome/construct materialization/outbox | full-valid structure、current fence、no partial next step |
| lsrag_generation_accept_v1 | ES-06/02 | construction/projection rows+final artifacts/report+commit/5 members+5 pointers/transitions + Process Outcome/vector materialization/outbox/events | exact coherent set、all pointer CAS、whole rollback |
| lsrag_candidate_failure_v1 | ES-06/02 | invalid artifacts/reports/repair changes/refs + failed Process Outcome/event | history durable before runtime failure acceptance |
| embedding_invocation_reserve_v1 | ES-07 | EmbeddingInvocation + ordered input digests | reservation unique；commit before provider call |
| embedding_invocation_complete_v1 | ES-07 | terminal outcome + document VectorRecord metadata/payloads | one outcome；output count/dimension/digest exact |
| vector_build_finalize_v1 | ES-07/02 | VectorBuildManifest/members + Process Outcome/next wake | projection/block/vector set exact |
| index_generation_stage_v1 | ES-07/02 | generation/input/memberships/filters + Process Outcome/next wake | full set or rollback；same digest replay |
| index_withdraw_v1 | ES-07/02 | WithdrawalProof + active pointer null transition + Process Outcome/outbox | Item serving-null fence already exact |
| index_rebuild_plan_v1 | ES-07/02 | rebuild plan/items + Process Outcome/fan-out wake | frozen ordered set exact |
| retrieval_receipt_finalize_v1 | ES-07 | terminal receipt + ordered hit evidence | no partial hit set；noquery/vector body |
| vector_cleanup_finalize_v1 | ES-07/02 | eligible payload deletes + CleanupProof + Process Outcome/outbox | reference/hold/grace snapshot exact |
| operational_run_reserve_v1 | ES-08 | one immutable operational run reservation | closed kind/key/request digest idempotency；exact build/config |
| operational_step_append_v1 | ES-08 | exact next ordered immutable step | run has no terminal outcome；ordinal/key unique |
| operational_run_complete_v1 | ES-08 | one immutable terminal outcome | required step count/set digest closure |
| process_detail_retention_v1 | ES-08/02 | eligible terminal Process rows delete + operation step | 90d、ES-02 cleanup fence、summary equivalence |
| retrieval_evidence_retention_v1 | ES-08/07 | bounded receipt/hit delete + operation step | 30d、no hold/incident、Team batch digest |
| delivery_ledger_retention_v1 | ES-08/04 | delivered outbox/inbox delete + operation step | both terminal≥30d、business effect/event retained |
| repair_resolve_v1 | owner ES | owner-approved repair effect + intent completion + event/outbox | no synthesized truth |
| cleanup_complete_v1 | owner ES | proofs + intent completion + reference releases/outbox | all required proofs verified |
| outbox_claim_v1 | ES-04 | message lease/fence/delivery_count | due+not terminal |
| outbox_finish_v1 | ES-04 | delivered/dead-letter/next-delivery fact | current lease/fence |
| inbox_consume_v1 | consumer owner | inbox receipt + exact business effect/event/outbox | UUID+digest idempotency |
| object_reserve_v1 | ES-04 | write reservation | team+idempotency+request digest |
| object_promote_outcome_v1 | ES-04 | outcome + stored object upsert/touch | actual digest/size verified |
| object_reference_v1 | artifact owner | logical Artifact/proof + object reference | owner/digest/size/team exact |
| object_release_v1 | artifact owner | release ledger + reference CAS | expected reference revision/live |
| object_delete_proof_v1 | ES-04 | delete proof + stored object tombstone | no live ref/hold + delete fence |

Transaction profile registry是 code-owned closed enum；增加profile只能服务既有 owner command。它不是 Workflow、Process key或公开 capability。每个 UoW test必须在每条 SQL 后注入异常并证明 all-or-nothing。

### 5.4 Persistence infrastructure tables

#### 5.4.1 schema_migrations

~~~text
migration_id INTEGER PK
migration_key TEXT UNIQUE NOT NULL
migration_checksum TEXT(64 lower hex) NOT NULL
schema_manifest_before_digest TEXT(64 lower hex) nullable only 0001
schema_manifest_after_digest TEXT(64 lower hex) NOT NULL
application_build_digest TEXT(64 lower hex) NOT NULL
applied_at TEXT UTC NOT NULL
duration_ms INTEGER >=0 NOT NULL
execution_evidence_json TEXT canonical object NOT NULL
~~~

该表是唯一 `payload_extra` 例外。Row immutable；同 migration ID/key不同 checksum 或当前 manifest不等于 recorded head时 fail-loud。

#### 5.4.2 schema_backfill_batches

~~~text
migration_id INTEGER
backfill_key TEXT
batch_ordinal INTEGER >=0
range_start_key TEXT nullable
range_end_key TEXT nullable
input_row_count INTEGER >=0
updated_row_count INTEGER >=0
validation_digest TEXT(64 lower hex)
completed_at TEXT UTC
payload_extra TEXT canonical object
PK(migration_id, backfill_key, batch_ordinal)
UNIQUE(migration_id, backfill_key, range_start_key, range_end_key)
~~~

Backfill按稳定 PK keyset推进；每批独立 transaction、可幂等重放。它只记录 physical migration进度，不表达业务对象状态。

Backfill batch可以先于该migration的完成row存在，因此`migration_id`在物理上不设FK；MigrationOwner只接受embedded manifest中已知但尚未完成的ID，并在最终validation后才append `schema_migrations`。Serve发现未完成batch且schema head不匹配时保持readiness false。

#### 5.4.3 registry_bundle_manifests

~~~text
bundle_key TEXT
bundle_version TEXT
bundle_digest TEXT(64 lower hex)
schema_head_migration_id INTEGER FK schema_migrations
application_build_digest TEXT(64 lower hex)
member_count INTEGER >=0
member_manifest_ref TEXT logical object ref nullable
member_manifest_digest TEXT(64 lower hex)
installed_at TEXT UTC
registration_origin TEXT CHECK(code|migration|bootstrap)
payload_extra TEXT canonical object
PK(bundle_key, bundle_version)
UNIQUE(bundle_key, bundle_digest)
~~~

该表证明一次 code-owned registry bundle 的 exact set；具体 Workflow/semantic/model/prompt/schema definitions仍归 owner ES 表。相同 version异digest拒绝。

#### 5.4.4 outbox_messages

| Column group | Exact columns / constraints |
|---|---|
| Identity | message_uuid PK；message_type、message_schema_version、delivery_key、message_digest |
| Aggregate | aggregate_kind、team_uuid nullable only global registry、aggregate_uuid/ref、aggregate_revision nullable |
| Causation | trace_uuid、correlation_uuid、causation_uuid、producer_event_uuid nullable |
| Payload | payload_json XOR payload_object_handle；payload_digest、payload_size_bytes；strict schema |
| Scheduling | created_at、available_at、next_delivery_at；priority_rank bounded |
| Claim | lease_token_hash、fencing_generation、lease_expires_at、lease_owner；all-null or all-present |
| Delivery | delivery_count、last_attempt_at、delivered_at、dead_lettered_at；delivered XOR dead-letter |
| Error | last_error_class/code/message_safe/details_ref nullable；无secret/path/body |
| Extension | payload_extra canonical object |

Constraints/indexes：

~~~text
UNIQUE(message_type, aggregate_kind, aggregate_uuid, delivery_key)
CHECK(delivery_count >= 0 AND fencing_generation >= 0)
CHECK(NOT(delivered_at IS NOT NULL AND dead_lettered_at IS NOT NULL))
CHECK(terminal => claim columns all null)
INDEX(delivered_at, dead_lettered_at, available_at, next_delivery_at, priority_rank, message_uuid)
INDEX(lease_expires_at, message_uuid)
INDEX(team_uuid, aggregate_kind, aggregate_uuid, created_at, message_uuid)
~~~

没有 `status` 列；pending/claimed/delivered/dead-letter均从事实列派生，不创建 StateFamily。Dead-letter只在有限delivery budget耗尽或non-retryable contract failure后写入，并触发 owner repair/alert；不能使 business truth回滚。

#### 5.4.5 inbox_receipts

~~~text
consumer_key TEXT
message_uuid UUID
message_type TEXT
message_schema_version TEXT
message_digest TEXT(64 lower hex)
team_uuid UUID nullable only global registry
business_effect_kind TEXT
business_effect_ref TEXT
business_effect_digest TEXT(64 lower hex)
received_at TEXT UTC
committed_at TEXT UTC
payload_extra TEXT canonical object
PK(consumer_key, message_uuid)
UNIQUE(consumer_key, message_uuid, message_digest)
~~~

Receipt与effect在同一 UoW。PK冲突后读取 digest：相同返回既有effect，不同报 integrity conflict。

#### 5.4.6 domain_events

~~~text
event_uuid UUIDv7 PK
event_type TEXT
event_schema_version TEXT
team_uuid UUID nullable only global registry
aggregate_kind TEXT
aggregate_uuid TEXT
aggregate_revision_before INTEGER nullable
aggregate_revision_after INTEGER nullable
event_payload_json TEXT canonical object nullable
event_payload_object_handle TEXT nullable
event_payload_digest TEXT(64 lower hex)
trace_uuid UUID
correlation_uuid UUID
causation_uuid UUID
producer_task_uuid UUID nullable
producer_execution_uuid UUID nullable
producer_process_uuid UUID nullable
occurred_at TEXT UTC
committed_at TEXT UTC
payload_extra TEXT canonical object
~~~

`event_payload_json XOR event_payload_object_handle`，`UNIQUE(aggregate_kind,aggregate_uuid,aggregate_revision_after,event_type,event_payload_digest)`。Events append-only、team-scoped、bounded；不是通用 event bus或event-sourced SSOT。

### 5.5 Delivery protocol contracts

#### 5.5.1 OutboxEnvelopeV1

~~~json
{
  "schema_version": "mkb.outbox-envelope.v1",
  "message_uuid": "...",
  "message_type": "process.wake-requested.v1",
  "message_schema_version": "v1",
  "delivery_key": "process:<uuid>:ready-revision:4",
  "team_uuid": "...",
  "aggregate": {"kind": "process", "ref": "...", "revision": 4},
  "causation": {"trace_uuid": "...", "correlation_uuid": "...", "causation_uuid": "..."},
  "payload_ref": {"kind": "inline_json", "digest": "...", "size_bytes": 123},
  "delivery": {"fencing_generation": 2, "lease_expires_at": "..."}
}
~~~

Envelope不携带 claim secret hash、absolute path、DB row、raw bytes、caller token或任意 Python object。Consumer先按 message type解析 exact schema，再比对 DB digest/lease fence；unknown version不 ack，写 safe error后按 policy dead-letter。

#### 5.5.2 Scanner protocol

Scanner每次按 `(due timestamp, priority_rank, message_uuid)` keyset读取有界 batch，逐条短 transaction claim；不保持跨 delivery transaction。默认：batch 64、lease 30秒、scan interval 1秒、max delivery 12、backoff 1s起指数到5分钟并加 deterministic jitter。ES-08可依据测量下调吞吐/上调间隔，但不能关闭periodic scan或依赖进程内 wake。

Scanner同样检查：

- expired outbox lease；
- Process ready/due无wake、retry_wait到期、expired Process lease；
- committed Gate decision/open Gate与Execution projection差异；
- sealed CandidateSet未accept、committed scheduling intent未delivery；
- object reservation/outcome/orphan/reference/delete fence；
- migration/schema/object integrity readiness。

每类差异调用对应 owner 的 typed semantic recovery port；scanner自身不能 UPDATE business tables。

### 5.6 Object storage tables

#### 5.6.1 stored_objects

~~~text
team_uuid UUID
stored_object_uuid UUIDv7
logical_handle TEXT
digest_algorithm TEXT CHECK(sha256)
content_digest TEXT(64 lower hex)
size_bytes INTEGER >=0
media_type TEXT
format_version TEXT CHECK(mkb-object-v1)
first_reservation_uuid UUID
promoted_at TEXT UTC
verified_at TEXT UTC
delete_after TEXT UTC nullable
deleted_at TEXT UTC nullable
delete_proof_uuid UUID nullable
live_slot INTEGER nullable, live=1 and deleted=null
row_revision INTEGER >=1
payload_extra TEXT canonical object
PK(team_uuid, stored_object_uuid)
UNIQUE(logical_handle)
UNIQUE(team_uuid, digest_algorithm, content_digest, size_bytes, live_slot)
CHECK((deleted_at IS NULL AND delete_proof_uuid IS NULL AND live_slot=1) OR
      (deleted_at IS NOT NULL AND delete_proof_uuid IS NOT NULL AND live_slot IS NULL))
~~~

Row是physical substrate/tombstone。Bytes immutable；media_type仅描述，不参与dedupe identity。删除后 row不复活；相同digest后续写必须创建新 stored_object_uuid，`live_slot`使同一Team同一digest同时最多一个live row，同时允许保留旧tombstone。

#### 5.6.2 object_write_reservations

~~~text
team_uuid UUID
reservation_uuid UUIDv7
idempotency_key TEXT
request_digest TEXT(64 lower hex)
owner_kind TEXT
owner_ref TEXT
purpose_key TEXT
expected_digest_algorithm TEXT nullable only unknown-at-stream-start
expected_content_digest TEXT nullable
expected_size_bytes INTEGER >=0 nullable
declared_media_type TEXT
budget_profile_ref TEXT
budget_profile_digest TEXT(64 lower hex)
producer_task_uuid UUID nullable
producer_execution_uuid UUID nullable
producer_process_uuid UUID nullable
producer_fence_digest TEXT(64 lower hex) nullable
reserved_at TEXT UTC
expires_at TEXT UTC
payload_extra TEXT canonical object
PK(team_uuid, reservation_uuid)
UNIQUE(team_uuid, owner_kind, owner_ref, purpose_key, idempotency_key)
~~~

同 idempotency key + request digest返回同 reservation；异digest冲突。Reservation immutable；是否有outcome从outcome row派生，不设状态列。

#### 5.6.3 object_write_outcomes

~~~text
team_uuid UUID
reservation_uuid UUID
outcome_kind TEXT CHECK(promoted|reused|rejected|failed)
stored_object_uuid UUID nullable
actual_digest_algorithm TEXT nullable
actual_content_digest TEXT nullable
actual_size_bytes INTEGER >=0 nullable
verified_media_type TEXT nullable
error_class TEXT nullable
error_code TEXT nullable
error_message_safe TEXT nullable
error_evidence_ref TEXT nullable
completed_at TEXT UTC
payload_extra TEXT canonical object
PK(team_uuid, reservation_uuid)
FK reservation
CHECK(promoted/reused => stored_object/digest/size nonnull and error null)
CHECK(rejected/failed => stored_object null and typed error nonnull)
~~~

Outcome append-only。Promoted与reused均证明 exact bytes可读，不证明 canonical Artifact/reference已提交。

`failed`只用于能够证明final object未出现的I/O失败；final是否出现无法判定时不写Outcome，而是记录`io_indeterminate` incident，由recovery重新hash并最终写promoted/reused或safe failed，避免terminal fact自相矛盾。

#### 5.6.4 object_references

~~~text
team_uuid UUID
object_reference_uuid UUIDv7
stored_object_uuid UUID
owner_kind TEXT
owner_uuid_or_ref TEXT
owner_revision_or_digest TEXT
purpose_key TEXT
expected_content_digest TEXT(64 lower hex)
expected_size_bytes INTEGER >=0
retention_class_ref TEXT
hold_until TEXT nullable
reference_fence_digest TEXT(64 lower hex)
created_at TEXT UTC
released_at TEXT UTC nullable
release_uuid UUID nullable
row_revision INTEGER >=1
payload_extra TEXT canonical object
PK(team_uuid, object_reference_uuid)
UNIQUE(team_uuid, owner_kind, owner_uuid_or_ref, purpose_key, reference_fence_digest)
FK(team_uuid, stored_object_uuid) -> stored_objects
INDEX(team_uuid, stored_object_uuid, released_at, hold_until)
INDEX(team_uuid, owner_kind, owner_uuid_or_ref, released_at)
~~~

Reference owner必须是 closed registry中的既有 logical identity/fact。Owner UUID/ref、object、expected digest/size与team全部一致后才能写。`released_at/release_uuid/row_revision`是release ledger的当前投影，不是状态。

#### 5.6.5 object_reference_releases

~~~text
team_uuid UUID
release_uuid UUIDv7
object_reference_uuid UUID
expected_reference_revision INTEGER >=1
release_reason_code TEXT
causation_uuid UUID
cleanup_intent_uuid UUID nullable
release_evidence_ref TEXT
release_evidence_digest TEXT(64 lower hex)
released_at TEXT UTC
payload_extra TEXT canonical object
PK(team_uuid, release_uuid)
UNIQUE(team_uuid, object_reference_uuid)
~~~

Release append-only并与 reference CAS 同一 UoW；重复相同evidence返回原release，异evidence冲突。

#### 5.6.6 object_delete_proofs

~~~text
team_uuid UUID
delete_proof_uuid UUIDv7
stored_object_uuid UUID
observed_object_revision INTEGER >=1
reference_snapshot_digest TEXT(64 lower hex)
delete_fence_digest TEXT(64 lower hex)
deletion_result TEXT CHECK(deleted|already_absent_verified)
path_derivation_version TEXT
bytes_size INTEGER >=0
content_digest TEXT(64 lower hex)
deleted_at TEXT UTC
directory_fsync_at TEXT UTC
producer_scan_uuid UUID
payload_extra TEXT canonical object
PK(team_uuid, delete_proof_uuid)
UNIQUE(team_uuid, stored_object_uuid)
~~~

Proof与 stored object tombstone同一 UoW，且只在filesystem delete/fsync成功后写。Database rollback会使无proof missing object成为incident；scanner不会仅凭不存在补写proof，除非同一delete fence有durable operation evidence并验证无reference。

#### 5.6.7 object_integrity_incidents

~~~text
team_uuid UUID
incident_uuid UUIDv7
stored_object_uuid UUID nullable
object_reference_uuid UUID nullable
owner_kind TEXT nullable
owner_ref TEXT nullable
incident_kind TEXT CHECK(missing|size_mismatch|digest_mismatch|unsafe_path|non_regular|unexpected_existing_bytes|io_indeterminate)
expected_digest TEXT nullable
observed_digest TEXT nullable
expected_size_bytes INTEGER nullable
observed_size_bytes INTEGER nullable
observation_evidence_ref TEXT
observation_evidence_digest TEXT(64 lower hex)
first_observed_at TEXT UTC
last_observed_at TEXT UTC
observation_count INTEGER >=1
resolved_at TEXT nullable
resolution_evidence_ref TEXT nullable
resolution_evidence_digest TEXT nullable
row_revision INTEGER >=1
payload_extra TEXT canonical object
PK(team_uuid, incident_uuid)
UNIQUE(team_uuid, stored_object_uuid, object_reference_uuid, incident_kind, observation_evidence_digest)
~~~

Incident是monotonic integrity fact：重复观察CAS增加count/time；resolution只能引用verified restore/rewrite-by-owner/false-positive evidence。它不自动更改 Artifact、Task、Execution、Item serving或StateFamily。

### 5.7 Application ports

~~~python
class PersistenceLanePort(Protocol):
    async def execute(self, command: UnitOfWorkCommandV1) -> CommittedReceiptV1: ...
    async def query(self, query: SnapshotQueryV1) -> QueryResultV1: ...

class UnitOfWorkPort(Protocol):
    def repository(self, owner_key: str) -> OwnerRepository: ...
    def append_event(self, event: DomainEventDraftV1) -> UUID: ...
    def enqueue(self, message: OutboxMessageDraftV1) -> UUID: ...

class MigrationPort(Protocol):
    def inspect(self) -> SchemaHeadV1: ...
    def migrate(self, target_migration_id: int) -> MigrationReportV1: ...
    def validate(self) -> SchemaValidationReportV1: ...

class OutboxPort(Protocol):
    async def claim_due(self, request: OutboxClaimRequestV1) -> list[ClaimedMessageV1]: ...
    async def finish(self, outcome: DeliveryOutcomeV1) -> DeliveryReceiptV1: ...

class InboxConsumerPort(Protocol):
    async def consume(self, envelope: OutboxEnvelopeV1) -> ConsumerReceiptV1: ...

class SemanticRecoveryScanPort(Protocol):
    async def scan(self, request: RecoveryScanRequestV1) -> RecoveryScanReportV1: ...

class ObjectWritePort(Protocol):
    async def reserve(self, command: ObjectWriteReservationV1) -> WriteReservationV1: ...
    async def write(self, reservation: WriteReservationV1, chunks: AsyncIterator[bytes]) -> ObjectWriteOutcomeV1: ...

class ObjectReferencePort(Protocol):
    async def attach(self, command: AttachObjectReferenceV1) -> ObjectReferenceV1: ...
    async def release(self, command: ReleaseObjectReferenceV1) -> ReleaseReceiptV1: ...

class ObjectReadPort(Protocol):
    async def open_verified(self, request: ObjectReadRequestV1) -> VerifiedObjectStreamV1: ...

class ObjectGcPort(Protocol):
    async def scan(self, request: ObjectGcScanRequestV1) -> ObjectGcReportV1: ...

class BackupPort(Protocol):
    async def create_quiesced(self, request: BackupRequestV1) -> BackupManifestV1: ...
    async def verify_restore_target(self, request: RestoreVerifyRequestV1) -> RestoreReportV1: ...
~~~

Repository interfaces按 owner domain拆分；不存在 generic `save(table,row)`、raw SQL、arbitrary transaction callback、path resolver或untyped JSON repository。Domain service可以传 typed mutation plan，但只有ES-04 adapter翻译SQL。

### 5.8 Internal protocol schemas

#### 5.8.1 UnitOfWorkCommandV1

~~~text
schema_version = mkb.uow-command.v1
transaction_profile_key
command_uuid, command_digest, idempotency_key
team_uuid nullable only registry/migration
aggregate_kind/ref, expected_revision/fence nullable by profile
trace_uuid, correlation_uuid, causation_uuid
deadline_at
typed_payload with exact profile schema
~~~

Command不接受 SQL、table/column name、Python callable、filesystem path、secret value或arbitrary event/message。CommittedReceipt包含 transaction UUID、commit timestamp、aggregate revision、created refs和outbox/event UUIDs；不返回driver row或SQL。

#### 5.8.2 ObjectWriteReservationV1

~~~json
{
  "schema_version": "mkb.object-write-reservation.v1",
  "team_uuid": "...",
  "idempotency_key": "...",
  "owner": {"kind": "intake_revision_candidate", "ref": "..."},
  "purpose_key": "clean_derived",
  "expected": {"algorithm": "sha256", "digest": null, "size_bytes": null, "media_type": "text/plain"},
  "budget": {"profile_ref": "artifact-clean-v1", "digest": "..."},
  "producer": {"task_uuid": "...", "execution_uuid": "...", "process_uuid": "...", "fence_digest": "..."}
}
~~~

Owner kind/purpose必须从 code-owned closed registry解析。Reservation response只有reservation UUID、expiry和bounded chunk limit；不返回 staging/final path。

#### 5.8.3 ObjectReadRequest / VerifiedObjectStream

ObjectReadRequest包含 team、owner kind/ref、purpose、expected logical handle/digest/size、consumer Process fence与byte/time budget。Stream每chunk只有bytes+ordinal；terminal `VerifiedObjectCompletion`包含actual digest/size、reference UUID、verified_at。Consumer若未收到terminal completion，必须丢弃临时输出并返回retryable/typed failure。

#### 5.8.4 BackupManifestV1

~~~text
schema_version = mkb.backup-manifest.v1
backup_uuid, created_at, application_build_digest
database_identity, schema_migration_id, schema_manifest_digest
database_relative_path, database_size_bytes, database_digest
object_root_identity, object_count, total_object_bytes
ordered objects[{team_uuid, stored_object_uuid, relative_path, digest, size_bytes}]
reference_snapshot_digest, domain_table_count_digest
verification_tool_version, completed_at, manifest_digest
~~~

Manifest自身用 canonical JSON + SHA-256，relative path必须通过 containment validator；不含 token、secret、absolute path或payload正文。

---

## 6. State / Consistency / Failure

### 6.1 StateFamily boundary 与 factual automata

ES-04 不拥有新的 domain StateFamily。Task、Execution、Process、IntakeItem、CandidateSet、ExecutionGate 的状态仍由 ES-01..03 owner控制。以下只是由 timestamp/ledger presence 推导的物理事实自动机；数据库中不增加 generic `status`：

#### 6.1.1 Outbox delivery facts

~~~text
committed, no lease, no terminal timestamp
  ──guarded claim──> active lease(fence n)
active lease(fence n)
  ├──consumer committed + guarded ack──> delivered_at
  ├──retryable failure──> no lease + next_delivery_at
  ├──budget/nonretryable──> dead_lettered_at
  └──lease expiry──> new guarded claim(fence n+1)

delivered_at / dead_lettered_at are terminal delivery facts
~~~

Stale lease token/fence不能 ack、reschedule或dead-letter。Delivery terminal不等于 aggregate成功；dead-letter也不回滚已提交业务 truth。

#### 6.1.2 Object write facts

~~~text
reservation row, no outcome
  ├──verified promote/reuse──> one immutable promoted|reused outcome
  └──validation/I-O failure──> one immutable rejected|failed outcome

promoted bytes + no live reference = orphan candidate after grace
live reference = GC protected
all references released + fences/grace satisfied
  ──filesystem delete + DB CAS──> immutable delete proof + stored-object tombstone
~~~

Outcome不存在表示未知/待恢复事实，不是 `uploading` 状态。Object outcome terminal也不等于 Artifact、Revision、Generation或Task成功。

#### 6.1.3 Incident 与 migration facts

- Integrity incident由 first/last observed、count、resolved evidence单调表达，不定义 open/resolved StateFamily；
- Migration是否完成只由 checksummed migration row + current schema manifest验证；没有 running migration业务状态；
- Backup是否完整只由 atomic final directory + verified manifest判断；`.tmp` 永不算备份。

### 6.2 全局 consistency invariants

1. 任何 business owner mutation 只经一个 named UoW和一个唯一 owner执行。
2. Business row、required audit/event和required outbox要么全部 commit，要么全部不存在。
3. Wake、delivery、HTTP response或process memory丢失不能删除 committed truth；scanner从owner truth恢复。
4. Same idempotency key + same digest最多一个business effect；same key + different digest永远conflict。
5. CAS 0 row永不被当作成功；adapter必须返回 current revision/fence的safe conflict projection。
6. Driver busy retry不跨已知 commit boundary；COMMIT结果未知时先按idempotency/readback确认，不盲目重执行。
7. 每个 team-owned FK/lookup/reference都验证相同 Team；不存在cross-team dedupe或handle解析。
8. Domain status只能经 owner合法边；ES-04 scanner/repository没有绕过owner的“修表”接口。
9. 已激活 registry revision、immutable evidence/history/event/outcome/decision/proof无 update/delete路径。
10. Latest/serving/current/active-index pointer各自 CAS；对象复用/删除不得切换任何 pointer。
11. DB reference到 bytes只在 bytes fsync/promote/verify之后创建；DB rollback最多留下orphan。
12. Live reference对应 bytes missing/corrupt是P0 integrity failure；禁止自动删reference或制造替代truth。
13. Object delete只在 reference/hold/runtime/pointer/backup fences全部闭合后发生，并保留delete proof/tombstone。
14. Migration、backup、GC、repair不能重解释或覆盖历史业务truth。
15. Normal serve只能运行在exact compatible schema head、healthy DB、matching object-root identity上。

### 6.3 Canonical transaction linearization points

| Operation | 唯一 linearization point | Commit 前不可见 | Commit 后恢复依据 |
|---|---|---|---|
| Task create | task_create_v1 COMMIT | Task/Audit/outbox均不可见 | Task+outbox |
| Full retry/rebuild admission | restart UoW COMMIT | 新generation/Task不可见 | Restart+Task generation+outbox |
| Workflow activation | workflow_register_v1 COMMIT | revision children不可active | active_revision pointer+bundle digest |
| Process claim | guarded claim COMMIT | worker无有效token/fence | Process lease/fence |
| Process Outcome | process_outcome_v1 COMMIT | route/next/aggregate均不接受 | Process accepted digest+route/event/outbox |
| Intake collection acceptance | intake_acceptance_v1 COMMIT | Snapshot/Revision/Item/ChangeSet均不存在 | Candidate accepted refs+canonical rows+outbox |
| Item publication | intake_publication_v1 COMMIT | 新serving不可读 | Item pointer revision+PublicationProof |
| Gate decision | gate_resolution_v1 COMMIT | Gate/Execution保持旧truth | Decision+Gate/Execution revision+outbox |
| Inbox consumption | inbox_consume_v1 COMMIT | receipt/effect均不存在 | receipt+effect digest |
| Artifact attach | object_reference_v1 COMMIT | promoted object仍只是orphan | Artifact/proof + object reference |
| Object release | object_release_v1 COMMIT | reference仍保护bytes | release ledger+reference projection |
| Object deletion | file delete/fsync后 object_delete_proof_v1 COMMIT | DB仍视为live physical record | delete proof/tombstone；失败进入incident |

### 6.4 Transaction / outbox crash matrix

| Crash / ambiguity window | Durable truth | Recovery | 禁止 |
|---|---|---|---|
| BEGIN前 | none | caller按同idempotency重试 | 创建补偿row |
| business writes中、COMMIT前 | rollback journal/WAL恢复为none | 同command安全重试 | 从日志拼回partial rows |
| COMMIT调用结果未知 | 可能all committed | 以idempotency+aggregate revision readback；只在不存在时重试 | 盲目执行第二次 |
| business+outbox commit后、wake前 | both committed | periodic scanner claim outbox | 回滚business或新建duplicate Process |
| outbox claim后、consumer前 | active lease | expiry后fence+1重投 | stale claimant ack |
| consumer effect commit后、ack前 | inbox+effect committed，outbox未ack | redelivery读inbox返回original receipt，再ack | 重做effect |
| ack COMMIT结果未知 | delivered可能已写 | claim fence/idempotency readback | delivery_count推断业务效果 |
| delivery budget耗尽 | business truth仍存在 | dead-letter + typed repair/alert | 将aggregate自动failed，除非owner transition明确如此 |
| ready Process无outbox | Process是truth | semantic scanner经owner port幂等补outbox | scanner直写Process状态 |
| Gate decision commit、resume wake丢失 | Decision/Gate/Execution为truth | replay exact outbox/owner recovery | 新Gate、新Decision、自动approve |

### 6.5 Object write crash matrix

| Crash point | Filesystem / DB result | Recovery |
|---|---|---|
| reservation前 | 无row、无temp | caller可重试 |
| reservation后、temp前 | reservation无outcome | expiry scanner写safe failed outcome或允许same writer resume from zero |
| streaming中 | partial temp | 永不读取；expiry删除temp并写failed outcome |
| temp fsync前 | temp durability未知 | 删除/隔离，不能promote |
| temp fsync后、digest compare前 | verified status未知 | recovery重新完整hash temp |
| digest mismatch | temp + rejected outcome | 删除temp；不得创建stored object |
| final promote前 | durable temp | recovery按reservation继续promote |
| final出现但directory fsync/outcome前 | final durability/owner未知 | fsync+完整hash；若exact则写promoted outcome，否则incident/quarantine |
| concurrent final已存在 | existing final | 完整hash/size相同则reused；不同则P0 incident，绝不覆盖 |
| outcome commit后、Artifact ref前 | stored bytes/outcome，无live ref | orphan grace；owner可按same reservation/digest继续attach |
| Artifact/ref UoW rollback | immutable bytes orphan | grace后GC；不产生canonical Artifact |
| Artifact/ref commit后、response前 | canonical ref完整 | idempotency readback返回original result |
| read streaming中断 | no verified completion | consumer丢弃partial result，按Process policy retry |
| live reference bytes missing/corrupt | DB truth + incident | fail-closed，owner repair；旧serving不得指向伪造bytes |

### 6.6 GC / delete crash matrix

| Window | Recovery rule |
|---|---|
| eligibility scan后新reference并发创建 | delete前observed revision/fence CAS失败；不得删除 |
| delete fence后、filesystem delete前 | recheck live refs/holds；若不再eligible取消本轮 |
| file delete失败/未知 | 不写delete proof；retry或incident，stored object仍nondeleted |
| file deleted、DB proof前crash | scanner发现missing但须匹配durable delete operation fence；验证仍无ref后写already_absent_verified proof，否则P0 incident |
| delete proof commit后response前 | idempotent readback；不重复业务release |
| directory cleanup失败 | bytes已删除且proof完整；empty directory best-effort cleanup，不影响truth |

### 6.7 Execution chains

#### 6.7.1 Service startup

~~~text
acquire single-process ownership lock
  → validate configured paths are absolute/config-owned but never persisted
  → read object-root identity
  → open embedded DB in persistence lane
  → apply/read PRAGMAs and run capability probe
  → verify migration checksum + exact schema manifest + registry bundles
  → quick_check/FK/object reference sample/full policy check
  → start bounded outbox/recovery/object-GC loops
  → readiness true
~~~

任何 step失败，liveness可以保持、readiness必须false；禁止自动创建空数据库替代无法打开的configured DB。

#### 6.7.2 Intake bytes to canonical truth

~~~text
ES-03 handler reserves and streams object
  → ES-04 verifies/promotes bytes and records outcome
  → ES-03 builds/seals/preflights CandidateSet using logical handle+digest
  → intake_acceptance_v1 begins
  → verify every required handle through stored object/reference eligibility
  → create Snapshot/Membership/Item/Revision/IntakeArtifact/ChangeSet
  → attach object references + intents/outbox/events
  → COMMIT
  → wake runner
~~~

若canonical UoW失败，不存在Snapshot/Revision/Artifact；已promote bytes仅为orphan。

#### 6.7.3 Process dispatch and completion

~~~text
Process ready + outbox commit
  → scanner claims outbox
  → runtime consumer inbox + claim Process fence commits
  → leaf streams verified inputs, performs external work outside DB transaction
  → leaf persists any output bytes first
  → submits typed Outcome
  → ES-02 process_outcome_v1 validates output/proof and atomically routes/materializes
  → outbox delivery ack
~~~

Outbox lease与Process claim是不同 fences；一个不能代替另一个。Leaf外部工作永远不持DB transaction。

#### 6.7.4 Publication replacement

~~~text
new generation/index proof fully validated
  → owner publication UoW loads old serving/current pointer
  → validate new proof + all live object/index refs
  → CAS pointer to new exact generation/revision
  → append transition/event/invalidation outbox
  → COMMIT
  → old serving references remain until retention owner later releases
~~~

因此publication失败或crash不会造成serving空窗；GC永远晚于pointer commit与独立release。

### 6.8 Concurrency、backpressure 与 shutdown

- Persistence command queue默认上限256；不同优先级仍使用公平bounded scheduling，migration/maintenance独占；
- Write UoW默认目标50ms、硬deadline 2s；大scatter在ES-03 seal前受member/byte/statement预算，超限fail-loud而非拆成partial canonical commits；
- Read query默认目标100ms，stream bytes不在DB read transaction内；先解析 immutable ref再关闭transaction；
- Object writer并发默认4、单对象chunk 256KiB；同team/digest promotion以final exclusive create消除覆盖；
- Outbox claim batch64，consumer执行不占 persistence lane；consumer每次effect用短UoW；
- Graceful shutdown先readiness false/停止admission，再停新claims，等待bounded UoW/object promotion，释放未commit lease给expiry恢复，最后checkpoint/close DB；
- 强杀后WAL、outbox、reservation/outcome和scanner必须自动收敛；不依赖process memory。

### 6.9 Integrity failure disposition

| Failure | Immediate behavior | Durable evidence / recovery |
|---|---|---|
| schema checksum/head drift | readiness false，拒绝写 | migration validation report；operator修正artifact/restore |
| FK/quick_check failure | stop all writes；safe reads也默认关闭 | P0 incident + verified restore |
| object-root identity mismatch | readiness false | deployment/config incident；不得改identity迁就目录 |
| canonical object missing/corrupt | exact read fail-closed | object incident + owner repair intent；禁止virtual object |
| orphan temp/final | 不影响canonical reads | grace scanner删除并留outcome/delete evidence |
| outbox dead-letter | aggregate truth保留 | safe error、alert、typed repair/replay |
| inbox digest conflict | consumer effect不执行 | integrity event/alert |
| stale CAS/fence | no mutation | conflict response/metric；正常并发不报警，异常频率告警 |
| disk full/read-only | current transaction rollback、readiness false for writes | capacity incident；释放非受保护orphan需owner policy |
| backup verification fail | active service truth不变 | incomplete backup quarantine/delete；不能标记complete |

---

## 7. Legacy Retain / Rewrite / Drop

| Legacy evidence | Retain | Rewrite in MKB | Drop |
|---|---|---|---|
| smind-admin ingestion API | DB-first identity和显式失败可审计的意图 | Task/business mutation与outbox同一Turso transaction；scanner恢复wake | create row后异步queue send、queue失败再patch status |
| smind-admin queue helpers | schema-validated typed message | exact version/digest envelope、lease/fence、inbox idempotency | `waitUntil(queue.send())`作为durability或success |
| smind-skill-clean-universal IO manager | typed input/output slot、streaming接口 | opaque logical handle、team/owner guard、bounded verified stream | R2 bucket/key进入contract、backend分支、unbounded full-buffer read |
| smind-console file/process SQL | UUID、created/updated evidence、必要索引的经验 | owner-separated 47 tables + infrastructure ledgers | File/Document万能row、runtime/content/vector/platform uploader混表 |
| artifact reverse lookup route | 从producer追溯artifact的使用需求 | explicit immutable object reference + typed lineage | 扫Process payload/log、virtual artifact、path猜测 |
| purger implementation | cleanup必须可重放且留proof的需求 | owner cleanup intent + reference release + fenced GC/delete proof | fake Process、force/reset、随机 Workflow/Team fallback、直接跨service调用 |
| D1/R2/Workers topology | 无 | 一个Python单体内repository/outbox/object adapters | Cloudflare binding、Durable Object、R2、callback、multi-worker topology |
| legacy identifiers/status/storage keys | 无 | fresh UUID/schema/enum/handle | compatibility、import、dual-read、cutover、bootstrap data |

保留项只是行为证据，不授权复制 legacy code、wire、DDL、路径或依赖。任何 legacy locator进入新DB/wire的测试都必须失败。

---

## 8. Acceptance Evidence

所有标为 HARD 的验收都必须自动化；fault injection需要在真实 pinned driver + 临时本地filesystem上运行，不得只用mock。每项产出test ID、application build、driver version、schema manifest digest与evidence digest。

### 8.1 Driver / topology / startup

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES04-A001 | HARD | exact driver pin | runtime仅加载pyturso 0.7.0；版本漂移readiness false |
| ES04-A002 | HARD | embedded-only config | remote URL/sync/libsql/cloud配置被strict拒绝 |
| ES04-A003 | HARD | single process lock | 第二进程不能打开正常serve写面 |
| ES04-A004 | HARD | persistence lane ownership | architecture/runtime guard证明非lane不能持connection/执行SQL |
| ES04-A005 | HARD | PRAGMA round-trip | 每connection foreign_keys/WAL/FULL/busy_timeout exact |
| ES04-A006 | HARD | capability probe | transaction/FK/CHECK/STRICT/JSON/WAL/error mapping全通过 |
| ES04-A007 | HARD | forbidden experimental mode | MVCC/concurrent/multiprocess/savepoint未启用且无代码依赖 |
| ES04-A008 | HARD | missing DB path | 配置目标不可开时不创建旁路空DB，readiness false |
| ES04-A009 | HARD | object-root identity | DB/deployment/root mismatch fail-closed |
| ES04-A010 | HARD | graceful restart | drain/close/reopen后quick_check和truth digest一致 |

### 8.2 Physical schema / migration

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES04-A011 | HARD | current owner-table inventory | ES-01..03/05/06/07/08共113张logical table与ES-04 manifest exact相等 |
| ES04-A012 | HARD | column/constraint diff | 每张owner表列、null/default/CHECK/UNIQUE/FK/index无损映射 |
| ES04-A013 | HARD | type round-trip | UUID/time/digest/boolean/counter/canonical object边界通过 |
| ES04-A014 | HARD | bad digest/json | uppercase/长度/非hex、非object/invalid JSON被拒绝 |
| ES04-A015 | HARD | payload_extra presence | 全部适用owner表存在object列且round-trip无行为依赖 |
| ES04-A016 | HARD | payload promotion | 未晋升key参与read/guard/index的静态检查失败 |
| ES04-A017 | HARD | cross-Team FK | 每类跨Team owner/reference写入均失败且外部按not-found |
| ES04-A018 | HARD | delete restriction | parent有历史/引用时DELETE失败，无business cascade |
| ES04-A019 | HARD | immutable repository | registry/history/evidence/event/outcome无update/delete方法与SQL |
| ES04-A020 | HARD | fresh migration | empty target从0001到head，manifest/quick_check/FK通过 |
| ES04-A021 | HARD | checksum drift | 已应用migration内容变化时migrate/serve均fail-loud |
| ES04-A022 | HARD | failed migration | 每step fault后head不假前进，重跑安全收敛 |
| ES04-A023 | HARD | bounded backfill | keyset batches无skip/duplicate，validation digest稳定 |
| ES04-A024 | HARD | table rebuild | row count、canonical data digest、FK/index前后一致 |
| ES04-A025 | HARD | serve without migrate | schema behind/ahead/incompatible时不自动修改且readiness false |

### 8.3 UnitOfWork / CAS / outbox

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES04-A026 | HARD | named profile completeness | §5.3每profile都有typed command、SQL plan与fault suite |
| ES04-A027 | HARD | statement fault injection | 每条SQL后异常均whole rollback，无partial owner/event/outbox |
| ES04-A028 | HARD | commit ambiguity | readback准确区分committed/not committed且effect至多一次 |
| ES04-A029 | HARD | same idempotency replay | same key/digest返回original receipt，无新rows/events/messages |
| ES04-A030 | HARD | idempotency conflict | same key/different digest rollback并返回typed conflict |
| ES04-A031 | HARD | stale aggregate CAS | zero-row update不返回success且不自动重放 |
| ES04-A032 | HARD | busy retry | 最多3次transaction外retry；无external effect/duplicate commit |
| ES04-A033 | HARD | caller cancellation | begin前无write；begin后明确commit或rollback，无unknown partial |
| ES04-A034 | HARD | no I/O in transaction | trace/architecture test无HTTP/model/filesystem/vector await |
| ES04-A035 | HARD | Task create atomicity | Task+Audit+event+outbox全有或全无 |
| ES04-A036 | HARD | full retry atomicity | Restart+generation/root intent全有或全无，旧历史不变 |
| ES04-A037 | HARD | Process Outcome atomicity | Process/route/Execution/next/outbox/event全有或全无 |
| ES04-A038 | HARD | Intake acceptance atomicity | Candidate/Snapshot/Membership/Item/Revision/Artifact/ChangeSet/intents全有或全无 |
| ES04-A039 | HARD | publication no-gap | failure前后old serving/index保持；new proof同commit才双pointer一次切换 |
| ES04-A040 | HARD | Gate decision atomicity | Decision/Gate/Execution/outbox全有或全无，无duplicate terminal |
| ES04-A041 | HARD | commit-before-wake | wake消费者永远看不到未commit Process/message |
| ES04-A042 | HARD | lost wake | commit后不发wake，scanner仍发现并只执行一次business effect |
| ES04-A043 | HARD | outbox stale fence | expired claimant不能ack/reschedule/dead-letter |
| ES04-A044 | HARD | consumer crash after effect | inbox+effect已commit、ack未commit时重投不重复effect |
| ES04-A045 | HARD | inbox digest conflict | same UUID/different digest拒绝且原effect不变 |
| ES04-A046 | HARD | delivery exhaustion | dead-letter保留business truth并产生typed repair/alert evidence |
| ES04-A047 | HARD | semantic scan owner boundary | scanner只调owner port，不直接改Task/Execution/Process/Gate/Intake |
| ES04-A048 | HARD | ready without outbox | owner repair补exact wake，不新建Process或改变retry count |

### 8.4 Object write / read / reference

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES04-A049 | HARD | handle opacity | DB/wire/log无absolute path、bucket/key；handle grammar exact |
| ES04-A050 | HARD | Team-scoped dedupe | same team+digest复用；cross-Team产生独立row/path且无existence leak |
| ES04-A051 | HARD | bounded streaming | 大对象以bounded chunk处理，memory不随size线性全量增长 |
| ES04-A052 | HARD | expected digest/size mismatch | rejected outcome，无stored object/reference/canonical Artifact |
| ES04-A053 | HARD | media/budget violation | typed rejected outcome，temp安全清理 |
| ES04-A054 | HARD | temp crash sweep | 每个stream/fsync crash point不产生可读partial final |
| ES04-A055 | HARD | promote crash sweep | final出现/outcome前crash经full hash安全收敛 |
| ES04-A056 | HARD | concurrent same bytes | 一个final，所有successful outcomes指exact bytes，无overwrite |
| ES04-A057 | HARD | conflicting existing bytes | 不覆盖，P0 incident/quarantine，canonical UoW被阻断 |
| ES04-A058 | HARD | DB attach rollback | bytes成为orphan，Snapshot/Revision/Artifact/reference均不存在 |
| ES04-A059 | HARD | attach commit response loss | idempotency readback返回same Artifact/reference，无duplicate |
| ES04-A060 | HARD | owner/team guard | 仅handle、跨Team、错误owner/purpose均不能读 |
| ES04-A061 | HARD | symlink/path traversal | no-follow/containment拒绝并记录safe incident |
| ES04-A062 | HARD | verified read completion | consumer只有EOF digest/size通过后可提交output |
| ES04-A063 | HARD | interrupted read | partial downstream temp丢弃，无Process success/proof |
| ES04-A064 | HARD | live missing bytes | read fail-closed + incident/repair；不创建空/virtual Artifact |
| ES04-A065 | HARD | live corrupt bytes | digest mismatch阻断publication/retrieval且expected truth不被改写 |
| ES04-A066 | HARD | reference attach atomicity | logical Artifact/proof与object reference同commit |
| ES04-A067 | HARD | release CAS/idempotency | exactly one release ledger，stale revision不解除保护 |
| ES04-A068 | HARD | open Gate protection | Gate evidence object直到Gate terminal+retention release前不eligible |
| ES04-A069 | HARD | runtime/current/serving protection | 任一live pointer/Process/backup hold使GC拒绝 |
| ES04-A070 | HARD | orphan grace | 无ref promoted bytes在24h前保留，之后fenced删除留proof |
| ES04-A071 | HARD | GC reference race | eligibility后新reference使delete CAS失败且bytes保留 |
| ES04-A072 | HARD | delete crash sweep | delete/fsync/proof每窗口收敛为valid object或verified tombstone |
| ES04-A073 | HARD | delete retry | failure不伪造proof；same fence重试最多一delete proof |
| ES04-A074 | HARD | cleanup does not delete truth | GC只删bytes，不删Task/Artifact/Revision/event/transition/tombstone |

### 8.5 Backup / recovery / architecture

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES04-A075 | HARD | quiesced backup | admission/claims停止、UoW/promotions排空、manifest原子完成 |
| ES04-A076 | HARD | incomplete backup | `.tmp`不被列为complete，active data不变 |
| ES04-A077 | HARD | backup closure | manifest覆盖全部live/held refs，object count/digest可复算 |
| ES04-A078 | HARD | restore empty-only | nonempty/active target被拒绝，无原位覆盖 |
| ES04-A079 | HARD | restore verification | schema/quick_check/FK/all object digests/smoke audit通过才可切换 |
| ES04-A080 | HARD | corrupt backup | 任一DB/object/manifest byte变化阻断restore |
| ES04-A081 | HARD | hard kill recovery | WAL/outbox/reservation/orphan/lease scanner自动收敛，无memory truth |
| ES04-A082 | HARD | disk full/read-only | transaction rollback、writes unready、old verified reads不伪变 |
| ES04-A083 | HARD | domain isolation | domain/application无pyturso/path/filesystem/outbox implementation import |
| ES04-A084 | HARD | no generic escape hatch | 无raw SQL/generic save/arbitrary transaction callback/public object API |
| ES04-A085 | HARD | zero legacy dependency | runtime/migration/schema无D1/R2/Worker/legacy table/status/key/import |
| ES04-A086 | HARD | secret-safe evidence | SQL args、token、path、body不进入errors/events/outbox/log/test artifact |
| ES04-A087 | HARD | ES-06 physical mapping | 21张logical table列/constraint/index与ES-06 exact diff为零 |
| ES04-A088 | HARD | validation subject insertion | artifact/artifact-set XOR无Report↔Commit循环FK且无弱化 |
| ES04-A089 | HARD | tree/anchor composite fence | cross-Team/document parent、anchor、unit、block引用全部失败 |
| ES04-A090 | HARD | five-pointer atomicity | commit UoW任一statement fault均无partial member/pointer/Outcome |
| ES04-A091 | HARD | current pointer race | expected revision+Process fence只允许same digest replay或单winner |
| ES04-A092 | HARD | original/summary object refs | original exact clean slice；summary exactInvocation；均被live ref保护 |
| ES04-A093 | HARD | invalid artifact retention | invalid无current但ledger/report/Invocation/causation完整 |
| ES04-A094 | HARD | S06 cleanup fence | current/ES-07 lineage/hold任一存在时bytes不可GC |

### 8.6 ES-07 vector/retrieval physical closure

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES04-A095 | HARD | ES-07 physical mapping | 24张logical table列/constraint/index与ES-07 exact diff为零 |
| ES04-A096 | HARD | vector metadata/payload split | immutable record+live payload one-to-one；dimension/length/digest exact |
| ES04-A097 | HARD | embedding reserve/complete | network前reservation；outcome/records全有或全无 |
| ES04-A098 | HARD | vector manifest/generation UoW | member/filter set任一fault均无partial manifest/generation |
| ES04-A099 | HARD | dual publication UoW | report/proof/index pointer/Item serving/Process/outbox全有或全无 |
| ES04-A100 | HARD | filter reuse mapping | newgeneration复用payload，target Revision filter rows exact，无BLOB复制 |
| ES04-A101 | HARD | retrieval read snapshot | pointer/filter/distance/hydrate/traceback同一snapshot，无拼接代际 |
| ES04-A102 | HARD | query receipt atomicity | receipt+ordered hits全有或全无，DB无query/filter正文/vector |
| ES04-A103 | HARD | vector cleanup/backup | payload delete+proof atomic；live vectors全部进入backup/restore digest |
| ES04-A104 | HARD | no hidden vector substrate | manifest无ANN/FTS/virtual/shadow/第二DB表且无public raw-vector repository |

### 8.7 ES-08 operational/retention physical closure

| ID | Level | Scenario | Required evidence |
|---|---|---|---|
| ES04-A105 | HARD | ES-08 physical mapping | 3张operational logical table列/constraint/index与ES-08 exact diff为零 |
| ES04-A106 | HARD | operational run idempotency | same key/digest original replay；different digest conflict；one reservation |
| ES04-A107 | HARD | operational step/outcome closure | ordered immutable steps；terminal后不可append；success重算full set digest |
| ES04-A108 | HARD | operation crash ambiguity | owner effect readback后补step；prior session只能由exclusive next owner写indeterminate |
| ES04-A109 | HARD | Process detail retention UoW | 90d+cleanup fence+summary equivalence，fault时no partial causal break |
| ES04-A110 | HARD | retrieval evidence retention UoW | 30d bounded Team batch；active/held/incident rows不删 |
| ES04-A111 | HARD | delivery ledger retention UoW | delivered+matching inbox≥30d且effect/event retained；dead-letter/lease不删 |
| ES04-A112 | HARD | final physical inventory | 113 owner +13 infrastructure =126 exact，backup/restore/readiness manifest diff为零 |

### 8.8 Evidence bundle

ES-04 evidence bundle固定包含：

1. driver/version/capability/PRAGMA report；
2. 113张owner-table full manifest、DDL digest、logical-schema diff及21张ES-06/24张ES-07/3张ES-08 mapping report；
3. migration fresh/upgrade/failure/backfill reports；
4. named UoW statement-by-statement fault matrix，含四个LS-RAG、八个ES-07、六个ES-08 UoW与dual-pointer CAS；
5. outbox/inbox/semantic scanner crash/replay report；
6. object stream/promote/read/reference/GC crash matrix；
7. backup/restore/corruption drill report；
8. relation/filter/exact-vector query plan、snapshot与capacity benchmark；
9. architecture dependency and secret/path leak scan；
10. cross-spec acceptance mapping to OT04-C005/C009/C010/C013。

---

## 9. Remaining Technical Decisions and Defaults

### 9.1 已裁决 defaults

| Topic | v1 default | 改变默认值所需技术证据 |
|---|---|---|
| Driver | pyturso 0.7.0 exact pin | 新稳定版本通过全部A001..A112与driver diff；不改变product contract |
| Process model | one Python process + one persistence lane | 当前driver正式支持并通过多线程/进程crash/locking suite；不得增加部署单元 |
| Journal/sync | WAL + FULL | measured durability与OT04底线仍满足；不可静默降级 |
| Write begin | BEGIN IMMEDIATE | driver正式提供等价严格serial write proof |
| Transaction retry | 3次，20/50/100ms+jitter | contention benchmark显示更安全bounded值 |
| Busy timeout | 5000ms | capacity/failure-injection报告 |
| Persistence queue | 256 | ES-08 measured memory/latency/backpressure envelope |
| Outbox | DB table + in-process periodic scanner | v1边界内没有采用外部broker的理由；改变会触及拓扑，不在本轮 |
| Outbox batch/lease | 64 / 30s | delivery/runtime benchmark + stale-fence suite |
| Object backend | same-deployment local POSIX-like filesystem | v1不接受新backend；未来变更需foundational scope review |
| Dedupe | Team-scoped SHA-256+size | cryptographic/security review；禁止cross-Team visibility |
| Chunk | 256KiB | memory/throughput benchmark且仍bounded |
| Orphan grace | 24h | crash/retry最长窗口与capacity证据；不得为0 |
| Compression | none | format/version/migration/read compatibility + benchmark |
| App encryption | none；volume protection归ES-08 | security threat model要求且不泄漏/破坏dedupe时另行版本化 |
| Backup | quiesced verified local snapshot | online方案只有正式driver支持和完整consistency proof后可替代 |

### 9.2 既有下游输入状态

| Input / status | Owner file | 本文件处理 |
|---|---|---|
| Model/Prompt/Schema/Capability registry exact tables / `closed` | ES-05 | 18张tables已登记并由v0.2继续复用 |
| GenerationArtifact/LS-RAG derived tables / `closed` | ES-06 | 21张tables、generation object references与4个named UoW已登记 |
| Embedding/Vector/Index/Retrieval tables / closed | ES-07 | 24张tables、8个新增UoW、exact vector payload/backup规则已登记 |
| Runtime operations/retention/config/limits / `closed` | ES-08 | 3张tables、6个新增UoW、126表manifest与backup/readiness规则已登记 |

ES-05/06/07/08 schema输入均已闭合。ES-08只把已冻结的permissions/config/limits/backup schedule运维化；不会新增ES-04文件、服务、StateFamily、backend或public能力。

### 9.3 Rejected alternatives

| Alternative | Rejection |
|---|---|
| Turso Cloud/remote sync/embedded replica | 增加外部运行依赖、网络一致性与运维面；V1无必要 |
| 多进程/多线程共享数据库 | 当前driver约束与单体最小拓扑下风险高，无产品收益 |
| Experimental MVCC/concurrent WAL | critical truth不使用实验能力 |
| SQLite fallback或双driver | 产生两套语义/测试矩阵并掩盖capability drift |
| External queue broker | 新运行依赖/交付面；DB outbox已满足durability |
| S3/R2/MinIO abstraction | 扩大backend与凭证/网络/一致性范围，违反固定容量 |
| DB BLOB存全部Artifact | 放大transaction/WAL/backup，破坏bounded streaming |
| Filesystem-only metadata | 无法与owner truth、Team、reference和proof原子对账 |
| DB-first object reference | crash可产生canonical missing bytes |
| Hard delete/timestamp GC | 无reference/hold/pointer fence，可能删除live history |
| Trigger-driven domain transitions | owner逻辑分散且难fault-test/port；违反唯一owner |
| Generic repository/raw SQL escape | 绕过typed contract、Team/fence/state guard |
| Auto-migrate on serve | startup意外改变truth且失败边界不受operator控制 |
| Online/merge restore | V1无一致性证明，可能覆盖active truth |

### 9.4 Closure

ES-04 没有需要 owner 回答的问题。Driver、process model、transaction、outbox、filesystem/vector payload backend、GC与backup均是 OT01-C004/OT03-C015 明确下沉的 executional选择；本文件已经给出有限默认、反例与验证条件。ES-01/02/03/05/06/07/08全部owner-table mapping与最终cross-spec audit均已闭合。

---

## 10. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| ES-04-v0.1 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 冻结 embedded pyturso 0.7.0、单进程单persistence lane、WAL/FULL/BEGIN IMMEDIATE、统一STRICT schema profile、forward-only migration、named UoW、DB outbox/inbox/event、local team-scoped CAS object store、bytes-first/reference/GC、quiesced backup/restore；物理登记ES-01..03共47张owner表，新增13张ES-04 infrastructure tables，提供factual automata、完整failure matrix、ports/protocols与86项HARD acceptance。无新产品责任、公开能力、domain identity、StateFamily、部署单元、backend或spec文件。 |
| ES-04-v0.2 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 接收ES-05-v0.1下游schema mapping：新增登记6张capability、3张schema、2张model、2张Prompt、1张profile与4张Invocation表，使owner-table inventory从47增至65；补充registry bundle/governance与Invocation reserve/dispatch/outcome named UoW并校准inventory acceptance。未改变driver、backend、StateFamily、部署拓扑或产品能力。 |
| ES-04-v0.3 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 接收ES-06-v0.1下游schema mapping：新增登记5张Generation ledger、4张current/commit、5张Structure、3张Construction、3张Projection与1张Repair表，使owner-table inventory从65增至86；补充4个LS-RAG named UoW及8项physical/atomicity acceptance。未新增driver、backend、StateFamily、部署拓扑或产品能力。 |
| ES-04-v0.4 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 接收ES-07-v0.1下游schema mapping：新增登记2张registry、3张embedding invocation、4张vector build/payload、4张index/filter、5张validation/publication/pointer、4张withdraw/cleanup/rebuild与2张retrieval表，使owner-table inventory从86增至110、project-owned physical inventory达到123；补充8个ES-07 named UoW、dual-pointer publication与10项acceptance。未新增driver、第二DB、ANN/FTS、public raw-vector、StateFamily、服务或spec。 |
| ES-04-v0.5 | 2026-08-10 | internally-consistent / awaiting cross-spec audit | 接收ES-08-v0.1下游schema/retention mapping：登记3张operational evidence表，使owner-table inventory从110增至113、project-owned physical inventory达到126；补充operational reserve/step/outcome及Process/retrieval/delivery retention共6个named UoW与8项acceptance。未新增业务StateFamily、数据库/backend、服务、deployment unit、operator产品或public能力。 |
| ES-04-v1.0 | 2026-08-10 | ready | 完成全项目schema/UoW/retention对账；113张owner tables与13张infrastructure tables一一映射为126张physical tables，55个named UoW无重名或孤儿，112项HARD acceptance连续。未新增driver、backend、状态族、服务或spec文件。 |
