# S13 — Artifact & Object Storage

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`F1 数据基础 / S13 Artifact & Object Storage`
>
> **日期**：`2026-08-11`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted`（S13 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S13-v1.0`
>
> **上游权威输入**：`D01-v1.4`、`D02-v1.0`、`S01-v1.5`、`S02-v1.3`、`S03-v1.3`、`S04-v1.2`、`S05-v1.1`、`S06-v1.0`、`S12-v1.0`；冻结的 `qna-truth/S13.md v1.0`（Q1–Q9 / `T-O-111..125`）
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **事实证据**：legacy R2/`io_manager`/filesystem_store（ReferenceAnchor）；ES-04 草案（候选分母非真相）；LLVM CAS / Bazel CAS / object GC 原则
>
> **下游消费者**：`S07–S11`、`S12`（object 模块物理）、`S14–S16`、跨系统拓扑 `17`、验收冻结 `18`

> **Owner-originated 约束（2026-08-11）**：v1 **权威对象 backend = 本地 POSIX-like filesystem**；Cloudflare R2 因免费额度/计费 **defer**（未来 adapter，不 reopen 业务契约）；Hugging Face Xet/Storage Buckets **不作 SSOT**。

> **跨文档审计声明**：S13 **不**拥有 Task/Execution/Process/Intake/Generation 状态机；**不**用对象存在性定义业务成功。Catalog 元数据落在 Turso（S12 物理/TX）；S13 拥有 Port、layout、write/read/GC 语义与 backup 一致性协议。

> **Legacy 边界（T-O-42 / T-O-116）**：不继承 R2 key wire、presign 公网上传、SMCP slot path、平台 quota/UI。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S13 回答：在单体 leaf-worker 内，如何把 **不可变对象字节** 可靠地写入、校验、引用保护和回收，并与关系主库（S12）以 **bytes-first** 对账——而不把 path/bucket 泄漏进业务契约，也不把文件存在性冒充 Artifact/Process 成功。

S13 解决十个核心问题：

1. 字节 substrate 与业务 SSOT 如何分账；
2. 契约如何只传 opaque handle + digest + size；
3. v1 用什么 backend（本地盘）及如何 Port 隔离；
4. 物理布局如何 team-scoped content-addressed；
5. 写路径如何 stream → promote → TX 登记；
6. live reference 如何保护 open-gate/serving/current；
7. orphan 与 missing 如何二分及 GC 如何跑；
8. 读路径如何 verify-on-read 与容量预算；
9. object_root 如何 readiness 与 identity 绑定；
10. backup 协议与 typed 错误、对外 OOS 如何钉死。

### 1.2 在整体拓扑中的位置

```text
S03/S04/S05/S06 domain services
  │ ObjectStorePort only (no pathlib / no absolute path)
  ▼
S13 LocalFilesystemAdapter
  │ staging / promote / verified read / write gate / fsync
  ▼
object_root/  (team-scoped CAS + staging + quarantine)
  │
  │ bytes-first: promote → digest
  ▼
S12 UnitOfWork (same mkb_primary)
  insert/upsert mkb_stored_objects
  insert mkb_object_references
  insert domain artifact/evidence rows
  commit → usable handle
  │
  ▼
periodic GC scanner (same release unit)
  release → grace → delete fence → unlink → delete_proof
```

### 1.3 Scope fence

**S13 负责：**

- `ObjectStorePort` 与 local filesystem adapter；
- opaque handle 语法与解析纪律；
- team-scoped CAS layout、staging、quarantine；
- stream write、atomic promote、verify-on-read；
- catalog **语义**（stored_object / object_reference / delete_proof）——物理表在 S12 migration；
- purpose 闭集与 GC/delete fence 规则；
- object_root `identity.json` 与 readiness 探针；
- orphan grace、预算、incident；
- quiesced backup/restore **一致性协议**；
- typed object 错误轴。

**S13 不负责：**

| 排除项 | 归属 |
|---|---|
| 业务状态机与合法边 | S02–S06 / D02 |
| Turso driver、TX 矩阵、outbox 投递环 | S12 |
| Intake/Generation 业务 identity | S04/S06 |
| cleanup intent 业务策略 | S04 |
| backup 排程、保留份数、告警 runbook | S15 |
| 磁盘加密密钥与威胁模型 | S16 / 部署 |
| R2/S3 adapter 实现（v1） | future reopen |
| 公网 upload/download 产品 | **OOS** |

### 1.4 Domain 完成定义

1. §2 Truth 映射到 Port、layout、表语义、测试；
2. bytes-first：无 digest 不得登记 usable handle；
3. crash suite：半写只产生 orphan 或完整 immutable object；
4. verify-on-read 与 missing/corrupt fail-closed；
5. open-gate / serving / current 保护下 GC 不删；
6. object_root identity drift → readiness=false；
7. 无公网 object API；architecture test 禁 domain path I/O；
8. 零 legacy R2/SMCP storage runtime；
9. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O）

| Truth-ID | 摘要 |
|---|---|
| `T-O-111` | S13=对象字节 substrate；存在≠业务成功 |
| `T-O-112` | 契约仅 opaque handle+digest+size；禁 path/bucket |
| `T-O-113` | 默认不可变；SHA-256；missing/corrupt fail-closed |
| `T-O-114` | bytes-first；orphan≠missing |
| `T-O-115` | 引用保护优先 GC；release≠立即删 |
| `T-O-116` | legacy 仅 ReferenceAnchor |
| `T-O-117` | v1 backend=本地盘+Port；R2/HF defer/非 SSOT；关 G-11→local |
| `T-O-118` | team-scoped CAS；opaque handle；禁跨 team dedup |
| `T-O-119` | stream→promote→TX ref；grace 24h；强制 live-ref 账本 |
| `T-O-120` | 同库 catalog 三语义；S13 语义/S12 物理；reservation 表 defer |
| `T-O-121` | purpose 闭集；owner 域 release；禁容量自动 release |
| `T-O-122` | verify-on-read；staging TTL；256MiB 级预算；无 app crypto |
| `T-O-123` | `mkbobj:v1`；窄 Port；写闸；强制 fsync |
| `T-O-124` | 周期 GC+delete fence；identity readiness；catalog tombstone |
| `T-O-125` | backup 协议/S15 排程；六类错误；无公网 object API |

### 2.2 域内 Truth（S13-T）

| ID | 冻结内容 | 来源 |
|---|---|---|
| `S13-T001` | S13 不定义 Task/Execution/Process/Intake lifecycle 成功。 | T-O-111 |
| `S13-T002` | 跨域只传 `mkbobj:v1:<team_uuid>:<stored_object_uuid>` + digest + size（+media 声明）。 | T-O-112/123 |
| `S13-T003` | Handle 解析必须 team 与 catalog 一致；只持 handle 不能绕过 owner 权威。 | T-O-112 |
| `S13-T004` | 权威完整性算法 SHA-256；同 handle 不得覆盖不同 bytes。 | T-O-113 |
| `S13-T005` | promote 成功并得 digest 后，才可在 S12 TX 登记 catalog+ref+业务 meta。 | T-O-114/119 |
| `S13-T006` | Orphan=无 live ref 的 promoted bytes；Missing=live ref 指向缺失/损坏。 | T-O-114/119 |
| `S13-T007` | v1 唯一 readiness backend = local filesystem under `object_root`。 | T-O-117 |
| `S13-T008` | R2/S3/HF 不进 v1 readiness；未来 adapter 不得改 domain 契约。 | T-O-117 |
| `S13-T009` | Final path：`objects/<team_uuid>/sha256/<aa>/<bb>/<64hex>`。 | T-O-118 |
| `S13-T010` | Dedup 仅同 team+digest+size；跨 team 禁止复用。 | T-O-118 |
| `S13-T011` | Staging 路径 UUID tmp；永不作为 durable identity 或 live ref 目标。 | T-O-118/122 |
| `S13-T012` | 写：exclusive stage → bounded stream → SHA-256 → fsync → atomic promote 或 verify-reuse。 | T-O-119/123 |
| `S13-T013` | 同 UoW：upsert `mkb_stored_objects` + insert live `mkb_object_references` + 业务行。 | T-O-120 |
| `S13-T014` | Catalog 表由 S12 migration 承载；S13 拥有语义与 Port。 | T-O-120 |
| `S13-T015` | Write reservation **表** defer；staging 文件+scanner 足够。 | T-O-120 |
| `S13-T016` | purpose 闭集见 §3.4；扩展须 code registry/migration。 | T-O-121 |
| `S13-T017` | open `gate_evidence`、serving/current 保护、operator/backup hold 下禁止 release/GC。 | T-O-121/115 |
| `S13-T018` | S13 永不因磁盘紧自动 release reference。 | T-O-121 |
| `S13-T019` | 完整 read 必须 verify digest+size；partial 非业务成功。 | T-O-122 |
| `S13-T020` | 默认单对象 max **256 MiB**（可配）；有界 chunk；free-space floor；超限 `OBJECT_BUDGET_*`。 | T-O-122 |
| `S13-T021` | v1 无应用层压缩/加密；盘级加密归部署。 | T-O-122 |
| `S13-T022` | Port 方法闭集：open_write_stream、finalize_write、promote、open_verified_read、stat、exists_bytes。 | T-O-123 |
| `S13-T023` | 有界写闸；禁无协调多进程写同一 object_root。 | T-O-123 |
| `S13-T024` | 生产 promote 强制 fsync(file+dir)；关 durability 禁止生产 readiness。 | T-O-123 |
| `S13-T025` | 同发布单元周期 GC scanner + delete fence + delete_proof。 | T-O-124 |
| `S13-T026` | orphan grace 默认 **24h**，可上调，禁止 0。 | T-O-119 |
| `S13-T027` | catalog 删除默认 **tombstone** 保留 digest 元数据。 | T-O-124 |
| `S13-T028` | readiness 依赖 object_root 可写 + identity.json 与 DB binding 一致 + capability probe。 | T-O-124 |
| `S13-T029` | Backup：quiesced 协议在 S13；排程/保留在 S15；restore 仅 empty target。 | T-O-125 |
| `S13-T030` | 错误轴：BUDGET/INTEGRITY/MISSING/CONFLICT/AUTH/UNAVAILABLE。 | T-O-125 |
| `S13-T031` | v1 禁止 public object CRUD、presign、bucket browser。 | T-O-125 |
| `S13-T032` | payload_extra 可用于 catalog 非核心扩展；禁 path/secret/state。 | S01 继承 |

### 2.3 强制时序

```text
# Write / accept
open_write_stream → stream chunks → finalize_write(digest,size)
  → promote (fsync + CAS path | verify-reuse)
  → UnitOfWork:
       upsert stored_objects
       insert object_references (live)
       insert domain rows (IntakeArtifact / GenerationArtifact / evidence…)
  → commit → caller usable handle
  → (optional) outbox wake

# Read
resolve handle+team → require policy (live ref unless repair)
  → stream + SHA-256 → EOF match catalog → success
  else INTEGRITY/MISSING + incident

# Release / GC
domain owner release_reference (released_at)
  → grace elapsed ∧ no live refs ∧ no holds
  → delete fence recheck
  → unlink bytes → delete_proof → catalog tombstone
```

---

## 3. 总体方案陈述

1. **Port-first**：domain 只依赖 `ObjectStorePort`；local adapter 是 v1 唯一实现。  
2. **CAS-first layout**：final bytes 按 team+sha256 布局；role 只在元数据。  
3. **Bytes-first registration**：先 promote 得 digest，再 TX 登记。  
4. **Reference-first GC**：purpose 闭集 + live ref；S13 不解释业务状态机。  
5. **Verify-on-read**：不信任“写时算过哈希就永远对”。  
6. **Identity-bound root**：`identity.json` 防错挂盘。  
7. **Ops split**：S13 协议 / S15 排程；无公网对象面。  
8. **Future cloud**：R2 仅未来 adapter；不进 v1。

---

## 4. 具体执行方案清单

### 4.1 ObjectStorePort 与 handle

**真相层对应**：S13-T002/003/022/023/024

**执行台账**：

| 项 | 规范 |
|---|---|
| Handle | `mkbobj:v1:<team_uuid>:<stored_object_uuid>` |
| open_write_stream | team、budget、media? → staging session |
| finalize_write | 关闭流；返回 digest、size；超 budget 失败 |
| promote | atomic 入 CAS 或 verify-reuse；fsync |
| open_verified_read | 流式读+校验 |
| stat | 来自 catalog |
| exists_bytes | 同 team digest+size 探测 |
| 写闸 | 有界；同 digest 并发 → reuse |
| 多进程 | v1 禁止无协调共享 root |

**小结**：窄表面 + 强语法 + 强 durability。

### 4.2 Layout 与 local adapter

**真相层对应**：S13-T007/009/010/011

```text
<object_root>/
  identity.json
  objects/<team_uuid>/sha256/<hex[0:2]>/<hex[2:4]/<64-hex-digest>
  staging/<team_uuid>/<write_id>.tmp
  quarantine/<team_uuid>/...
```

- path 沙箱：拒 `..`、绝对路径、反斜杠逃逸（继承 legacy-python 教训，升级为 bytes）。  
- 同 digest 不同内容 → `OBJECT_CONFLICT_*`，禁止覆盖。

### 4.3 Catalog 与 S12 接合

**真相层对应**：S13-T013/014/015

| 逻辑表 | 职责 | 关键约束 |
|---|---|---|
| `mkb_stored_objects` | immutable catalog | unique `(team_uuid, sha256, size)`；`stored_object_uuid` PK |
| `mkb_object_references` | live-ref 账本 | purpose、owner_kind/uuid、expected_digest/size；`released_at` NULL=live |
| `mkb_object_delete_proofs` | 物理删除证据 | intent/fence/digest/time |

逻辑模块：S12 `object`（或并入 `ops`）；**单一 migration 链**。

### 4.4 Reference purpose 闭集

**真相层对应**：S13-T016/017/018

| purpose | 典型 owner | 释放前必须 |
|---|---|---|
| `intake_snapshot_artifact` | S04 Snapshot Artifact | cleanup 允许且无依赖 |
| `intake_revision_artifact` | S04 Revision Artifact | 非 serving 目标 |
| `clean_candidate` | S05 candidate | set terminal/abandoned 规则 |
| `gate_evidence` | S05 Gate | Gate **terminal** |
| `generation_artifact` | S06 Generation | 非 current（若仍被 pointer 保护） |
| `process_io` | S03 Process I/O | Process terminal + eligibility |
| `operator_hold` | ops | 显式解除 |
| `backup_hold` | backup | 备份完成/解除 |

### 4.5 GC scanner 与 readiness

**真相层对应**：S13-T025..028

- interval 配置（建议 5–15 min，非 Truth 硬秒数）。  
- staging TTL 默认 24h 量级。  
- readiness 与 S12 联合：DB ready ∧ object store ready。

### 4.6 Backup 协议

**真相层对应**：S13-T029

```text
maintenance fence / quiesce promotes
  → S12 checkpoint
  → copy DB + object_root (or ref-closure)
  → manifest (schema head, identity, counts, digests)
  → verify → atomic rename backup_uuid
  → release fence
Restore → empty target only → verify → smoke → operator switch
```

### 4.7 错误轴

**真相层对应**：S13-T030

| 前缀 | 含义 |
|---|---|
| `OBJECT_BUDGET_*` | size/free-space |
| `OBJECT_INTEGRITY_*` | digest/size mismatch、非 regular |
| `OBJECT_MISSING_*` | live ref 无 bytes |
| `OBJECT_CONFLICT_*` | CAS 冲突、delete fence 中止 |
| `OBJECT_AUTH_*` | team/handle 不匹配 |
| `OBJECT_UNAVAILABLE_*` | readiness/root 只读 |

---

## 5. 事实反例 + 风险台账

| 反例 / 风险 | 围栏 |
|---|---|
| legacy `r2_key` 进 wire | handle only；architecture test |
| 对象存在=Process success | T-O-111；bytes-first |
| 无 ref 扫盘 GC 误删 open gate | purpose + live ref |
| TX 内无界 stream | 事务外 I/O |
| 双写 local+R2 | v1 禁止 |
| 错挂 object_root | identity.json readiness |
| 无 backup | S13 协议强制存在 |
| 256MiB 对大 PDF 不够 | 配置上调；禁默认无界 |
| 无 app 加密 | S16/部署盘加密 |

---

## 6. 测试与验收台账

| ID | HARD 不变量 | 证据类型 |
|---|---|---|
| `S13-A01` | promote 后崩溃再 TX 回滚 → orphan 可 GC，无业务 success | crash inject |
| `S13-A02` | 同 team 同 digest 并发 promote → 复用且无不同内容覆盖 | concurrency |
| `S13-A03` | 跨 team 同 digest 不复用 path/row | isolation |
| `S13-A04` | open gate_evidence 存在时 GC 不删 bytes | ref protection |
| `S13-A05` | serving/current 保护下不 release/GC | ref protection |
| `S13-A06` | verify-on-read 篡改文件 → INTEGRITY + incident | integrity |
| `S13-A07` | live ref 删文件 → MISSING 非 orphan 静默清 | missing |
| `S13-A08` | 超 256MiB 默认预算 fail BUDGET | budget |
| `S13-A09` | path `..` 逃逸拒绝 | sandbox |
| `S13-A10` | identity mismatch → readiness false | readiness |
| `S13-A11` | domain 包无 pathlib 写 object_root | arch test |
| `S13-A12` | 无 public object HTTP route | surface |
| `S13-A13` | delete fence：删前新 ref 插入则中止删 | GC race |
| `S13-A14` | grace=0 配置拒绝或 readiness fail | config |
| `S13-A15` | backup manifest verify 失败不标记完整 | backup |
| `S13-A16` | handle 语法非法 / team 不符 → AUTH | auth |
| `S13-A17` | staging 过期被清且无 live ref | staging GC |
| `S13-A18` | Process terminal 不级联硬删对象 | no cascade |
| `S13-A19` | fsync 路径在 crash suite 后文件完整或可回收 | durability |
| `S13-A20` | zero legacy r2_key/SMCP storage import | legacy fence |

---

## 7. Reference-anchor 台账

| Anchor | 用途 | 裁决 |
|---|---|---|
| `smind-admin/core/r2.ts` | 对象分账、presign 反例 | 删除公网 presign；保留分账思想 |
| skill `io_manager.ts` typed slots | Port 思想 | 升级为 handle；删 r2_key wire |
| `storage_objects/filesystem_store.py` | path 沙箱、atomic rename | 保留并升级 bytes/fsync/digest |
| ES-04 object 章节 | CAS/reservation/GC 草案 | 吸收 CAS+ref；reservation 表 defer |
| LLVM/Bazel CAS | content-address immutability | 借鉴原则非代码 |

---

## 8. Domain verdict

**`ACCEPTED / GO`**：S13 对象存储宪法（local backend、CAS、bytes-first、catalog/ref/purpose、Port、GC/readiness、backup 协议、错误轴、OOS 面）已闭合。

对下游约束：

1. S07–S10 只消费 logical handle+digest；  
2. S12 必须交付 object 模块三表 + bytes-first TX；  
3. S15 承接 GC/backup 排程与 metric；  
4. S16 承接盘加密与 secret；  
5. R2 未来只扩 adapter；  
6. **G-11 closed** → v1 local。

未解决边界（不阻塞 accepted）：R2 实现、app crypto、reservation 表、精确 interval/保留份数。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 说明 |
|---|---|---|---|---|
| `S13-v1.0` | `2026-08-11` | `MKB owner + Codex` | `accepted` | 吸收 Q1–Q9 / `T-O-111..125`；冻结 local Port/CAS/bytes-first/catalog/purpose/GC/readiness/backup/errors；关闭 G-11 |
