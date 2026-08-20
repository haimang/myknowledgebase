# S13 — Artifact & Object Storage

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`F1 数据基础 / S13 Artifact & Object Storage`
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S13 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S13-v1.1`（v1.0 宪法 + **执行台账全面升格**；QNA 细节并入本文）
>
> **上游权威输入**：`D01–D04`、`S01–S07`、`S12`；`qna-truth/S13.md v1.0`（**证据层 / 中间态 only**，非执行 SSOT）
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.1
>
> **事实证据**：legacy R2/`io_manager`/filesystem_store（ReferenceAnchor）；ES-04 草案（候选分母非真相）；CAS/GC 原则
>
> **下游消费者**：`S04–S11`、`S12`（object 模块物理）、`S14–S16`、跨系统拓扑 `17`、验收冻结 `18`

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S13.md` 仅 progressive 证据，**不得**作第二执行真相。Catalog 表物理列以 **D04** 为准；本文钉死 **Port、layout、写/读/GC 步骤、purpose、错误轴、backup 协议**。禁止「细节在 QNA、Spec 只写原则」。

> **Owner 约束**：v1 **权威 backend = 本地 POSIX-like filesystem**；Cloudflare R2 **defer**；HF Xet/Buckets **非 SSOT**。G-11 → local。

> **跨文档**：S13 **不**拥有业务状态机；**不**用对象存在性定义业务成功。S12 拥有 migration/UnitOfWork；S13 拥有 Port/layout/GC 语义。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S13 规定：在单体 leaf-worker 内，如何把 **不可变对象字节** 可靠地写入、校验、引用保护和回收，并与关系主库（S12）以 **bytes-first** 对账——不把 path/bucket 泄漏进业务契约。

### 1.2 拓扑

```text
Domain services
  │ ObjectStorePort only (no pathlib / no absolute path in contracts)
  ▼
S13 LocalFilesystemAdapter
  │ staging / promote / verified read / write gate / fsync
  ▼
object_root/  (team-scoped CAS + staging + quarantine)
  │
  │ bytes-first: promote → digest
  ▼
S12 UnitOfWork
  upsert mkb_stored_objects
  insert mkb_object_references
  insert domain artifact/evidence rows
  commit → usable handle
  │
  ▼
periodic GC scanner (same release unit)
  release → grace → delete fence → unlink → delete_proof
```

### 1.3 Scope fence

**负责**：`ObjectStorePort` 与 local adapter；opaque handle；team-scoped CAS layout；stream write / atomic promote / verify-on-read；catalog **语义**（物理表 S12/D04）；purpose 闭集与 GC/delete fence；object_root identity + readiness；orphan grace 与预算；quiesced backup 协议；typed object 错误轴。

**不负责**：业务状态机；Turso driver/outbox 环（S12）；Intake/Generation identity；cleanup 业务策略（S04）；backup 排程/保留份数（S15）；盘加密密钥（S16）；v1 R2 adapter；公网 upload 产品。

### 1.4 完成定义

1. §2 + §4 E 包可编码；  
2. bytes-first HARD；  
3. crash suite：半写只 orphan 或完整 immutable；  
4. verify-on-read / missing-corrupt fail-closed；  
5. open-gate/serving/current 保护下 GC 不删；  
6. identity drift → readiness=false；  
7. 无公网 object API；architecture 禁 domain path I/O；  
8. 实现无需打开 QNA；  
9. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 全局 T-O（摘要）

| ID | 一句话 |
|---|---|
| T-O-111..116 | 范围、handle 合同、不可变 SHA-256、bytes-first、ref 优先 GC、legacy fence |
| T-O-117..119 | local backend、team CAS layout、stage→promote→ref+grace |
| T-O-120..122 | catalog 三语义、purpose 闭集、staging/read/budget |
| T-O-123..125 | Port+写闸+fsync、GC+readiness、backup+错误+OOS |

### 2.2 域内 S13-T

| ID | 内容 |
|---|---|
| S13-T001 | 不定义业务 lifecycle 成功 |
| S13-T002 | 契约只传 `mkbobj:v1:<team_uuid>:<stored_object_uuid>` + digest + size（+media） |
| S13-T003 | Handle 解析 team 与 catalog 一致；只持 handle 不能绕过 owner 权威 |
| S13-T004 | 权威完整性 SHA-256；同 handle 不得覆盖不同 bytes |
| S13-T005 | promote 得 digest 后才可 TX 登记 catalog+ref+业务 meta |
| S13-T006 | Orphan=无 live ref 的 promoted bytes；Missing=live ref 指向缺失/损坏 |
| S13-T007 | v1 唯一 readiness backend = local filesystem under `object_root` |
| S13-T008 | R2/S3/HF 不进 v1 readiness；未来 adapter 不改 domain 契约 |
| S13-T009 | Final path：`objects/<team_uuid>/sha256/<aa>/<bb>/<64hex>` |
| S13-T010 | Dedup 仅同 team+digest+size；禁跨 team |
| S13-T011 | Staging UUID tmp；永不作 durable identity / live ref 目标 |
| S13-T012 | 写：exclusive stage → bounded stream → SHA-256 → fsync → atomic promote 或 verify-reuse |
| S13-T013 | 同 UoW：upsert stored_objects + insert live refs + 业务行 |
| S13-T014 | Catalog 表 S12 migration；S13 语义与 Port |
| S13-T015 | write reservation **表** defer |
| S13-T016 | purpose 闭集见 E04；扩展须 code registry |
| S13-T017 | open gate_evidence / serving / current / hold 下禁 release/GC |
| S13-T018 | S13 永不因磁盘紧自动 release |
| S13-T019 | 完整 read 必须 verify digest+size |
| S13-T020 | 默认单对象 max **256 MiB**；有界 chunk；free-space floor |
| S13-T021 | v1 无应用层压缩/加密 |
| S13-T022 | Port 方法闭集：open_write_stream、finalize_write、promote、open_verified_read、stat、exists_bytes |
| S13-T023 | 有界写闸；禁无协调多进程写同一 object_root |
| S13-T024 | 生产 promote 强制 fsync(file+dir) |
| S13-T025 | 周期 GC + delete fence + delete_proof |
| S13-T026 | orphan grace 默认 **24h**，可上调，禁止 0 |
| S13-T027 | catalog 删除默认 tombstone |
| S13-T028 | readiness：object_root 可写 + identity.json 与 DB 一致 + probe |
| S13-T029 | Backup 协议在 S13；排程在 S15；restore 仅 empty target |
| S13-T030 | 错误轴：BUDGET/INTEGRITY/MISSING/CONFLICT/AUTH/UNAVAILABLE |
| S13-T031 | 禁止 public object CRUD/presign/browser |
| S13-T032 | payload_extra 禁 path/secret/state |

### 2.3 强制时序（摘要）

```text
Write:  open_write_stream → stream → finalize_write → promote → S12 UoW catalog+ref+domain → commit
Read:   resolve handle → policy → stream + SHA-256 → match catalog
Release/GC: owner release → grace → fence recheck → unlink → delete_proof → tombstone
```

---

## 3. 总体方案陈述

1. Port-first；local adapter v1 唯一实现。  
2. Team-scoped CAS layout。  
3. Bytes-first registration。  
4. Reference-first GC + purpose 闭集。  
5. Verify-on-read。  
6. Identity-bound object_root。  
7. Ops split：S13 协议 / S15 排程。  
8. Future cloud 只扩 adapter。  
9. QNA 零依赖。

---

## 4. 具体执行方案清单

### 4.1 `S13-E01` — 目录、Port 与 architecture 围栏

**真相**：S13-T022/T023/T031

| 路径 | 职责 |
|---|---|
| `src/runtime/object_store/` 或 `src/object_store/` | Port + LocalFilesystemAdapter |
| `src/contracts/object_store/` | handle、errors、stat shapes |
| GC scanner | 同发布单元后台任务（非 domain Port） |

**ObjectStorePort 方法闭集**：

| 方法 | 语义 |
|---|---|
| `open_write_stream(team, media?, budget?)` | exclusive staging session |
| `finalize_write(session)` | 关流；返回 digest、size；超 budget 失败 |
| `promote(session)` | fsync + atomic CAS path 或 verify-reuse；返回 stored_object_uuid 候选 |
| `open_verified_read(handle, team)` | 流式读 + 边校验 |
| `stat(handle, team)` | 来自 catalog |
| `exists_bytes(team, digest, size)` | 同 team 探测 |

**不进 Port**：register/release reference（S12 UoW）、GC、backup、public HTTP。

| 规则 | 验收 |
|---|---|
| domain 禁 pathlib 写 object_root | architecture test |
| 禁绝对 path 进 contracts/Outcome | contract test |
| 无 public object route | surface test |

**小结**：窄表面 + 强语法。

---

### 4.2 `S13-E02` — Handle 语法与解析

**真相**：S13-T002/T003

| 项 | 规范 |
|---|---|
| 语法 | `mkbobj:v1:<team_uuid>:<stored_object_uuid>` |
| 含 | version 前缀、team、opaque uuid |
| **不含** | path、digest、bucket、backend 名 |
| 解析 | 必须匹配 caller team；查 catalog；team 不一致 → `OBJECT_AUTH_*` |
| 权限 | 只持 handle **不能**绕过 owner domain 的 release/read 策略 |

**小结**：opaque 身份；catalog 是解析权威。

---

### 4.3 `S13-E03` — Layout、staging、quarantine

**真相**：S13-T007..T011

```text
<object_root>/
  identity.json
  objects/<team_uuid>/sha256/<hex[0:2]>/<hex[2:4]/<64-hex-digest>
  staging/<team_uuid>/<write_id>.tmp
  quarantine/<team_uuid>/...
```

| 规则 | 规范 |
|---|---|
| Final identity | `(team_uuid, sha256, size)` content-addressed |
| Dedup | 仅同 team；**禁止跨 team 复用 path/row** |
| Staging | exclusive create；TTL 默认 24h 量级；**永不** live ref 目标 |
| 沙箱 | 拒 `..`、绝对路径、反斜杠逃逸 |
| Role/purpose | 只在元数据；**不进 path** |
| 同 digest 不同内容 | `OBJECT_CONFLICT_*`；禁止覆盖 |

**identity.json（逻辑）**：绑定 instance/db binding id；与 S12 readiness 联合校验；防错挂盘。

**小结**：team-scoped CAS；staging 非身份。

---

### 4.4 `S13-E04` — 写路径：stream → promote → TX

**真相**：S13-T012..T015/T024

**逐步**：

| 步 | 动作 | 失败 |
|---|---|---|
| 1 | 写闸 try_acquire | `OBJECT_UNAVAILABLE_*` / backpressure |
| 2 | exclusive open staging tmp | CONFLICT / IO |
| 3 | bounded stream chunks；边算 SHA-256；enforce max size | `OBJECT_BUDGET_*` |
| 4 | finalize_write：关闭流；得 digest+size | BUDGET / IO |
| 5 | free-space floor 检查 | BUDGET |
| 6 | fsync(file) + fsync(parent dir) | UNAVAILABLE；**生产禁止关 durability** |
| 7 | atomic promote 到 CAS path **或** verify-reuse 已有同 digest | CONFLICT if mismatch |
| 8 | 返回 (stored_object_uuid candidate, digest, size) | — |
| 9 | caller 开 S12 UoW：upsert catalog + live ref + domain rows | TX fail → orphan ok |
| 10 | commit → **usable** handle | — |
| 11 | 写闸 release（finally） | — |

| 规则 | 说明 |
|---|---|
| bytes-first | 步骤 7 前不得宣称 usable |
| 无 TX 内无界 stream | HARD |
| 半写崩溃 | 仅 orphan staging/promoted 无 ref；可 GC |
| 多进程 | v1 **禁止**无协调共享 object_root 写 |

**小结**：durable promote 再登记。

---

### 4.5 `S13-E05` — Catalog 语义与 purpose 闭集

**真相**：S13-T013..T018；D04 object 表

| 逻辑表 | 职责 | 关键约束 |
|---|---|---|
| `mkb_stored_objects` | immutable catalog | unique `(team_uuid, sha256, size)`；`stored_object_uuid` PK |
| `mkb_object_references` | live-ref 账本 | purpose、owner_kind/uuid、expected_digest/size；`released_at` NULL=live |
| `mkb_object_delete_proofs` | 物理删除证据 | intent/fence/digest/time |

**purpose 闭集（v1）**：

| purpose | 典型 owner | 释放前必须 |
|---|---|---|
| `intake_snapshot_artifact` | S04 Snapshot | cleanup 允许且无依赖 |
| `intake_revision_artifact` | S04 Revision | 非 serving 目标 |
| `clean_candidate` | S05 candidate | set terminal/abandoned 规则 |
| `gate_evidence` | S05 Gate | Gate **terminal** |
| `generation_artifact` | S06/S07 Generation | 非 current（pointer 保护） |
| `process_io` | S03 Process I/O | Process terminal + eligibility |
| `operator_hold` | ops | 显式解除 |
| `backup_hold` | backup | 备份完成/解除 |

| 规则 | 说明 |
|---|---|
| 创建 ref 的 domain owner | 语义允许时 release |
| S13 | **只**在无 live ref 且无 hold 后 GC |
| 禁止 | 磁盘紧自动 release；按 Task/Process 状态猜 release |
| release | durable 标记；非静默抹历史 |

**小结**：reference ledger 强制；purpose 可测。

---

### 4.6 `S13-E06` — 读路径与 verify-on-read

**真相**：S13-T019

```text
1. parse handle + team guard
2. load catalog row; require live ref policy (unless repair/admin path)
3. open final path under object_root (sandbox)
4. stream + SHA-256; EOF size match catalog
5. match → success stream
6. mismatch/missing → OBJECT_INTEGRITY_* / OBJECT_MISSING_* + incident
7. partial read ≠ 业务成功
```

可疑文件可入 quarantine；**不**改 catalog digest。

**小结**：不信任“写时算过哈希就永远对”。

---

### 4.7 `S13-E07` — GC scanner、grace、delete fence

**真相**：S13-T025..T027；T-O-119/124

**GC 逐步**：

| 步 | 动作 |
|---|---|
| 1 | 周期 scanner（建议 5–15min 配置）或 release 后触发 |
| 2 | 候选：promoted bytes **无 live ref** 且过 **orphan grace** 且无 hold |
| 3 | **delete fence recheck**：删前再查 live ref / hold；新 ref 插入则中止 |
| 4 | unlink bytes |
| 5 | insert `delete_proof` |
| 6 | catalog **tombstone**（默认保留 digest 元数据；不硬抹历史） |

| 配置 | 默认 | 约束 |
|---|---|---|
| `object.orphan_grace` | **24h** | 可上调；**禁止 0** |
| `object.staging_ttl` | 24h 量级 | 独立清理规则 |
| `object.gc_interval` | 5–15min | 非 Truth 硬秒数 |

| 禁止 | 说明 |
|---|---|
| GC 删业务行 | 只删 bytes + proof |
| live ref 下 unlink | HARD |
| open gate_evidence / serving / current 保护下 release/GC | HARD |
| Process terminal 级联硬删对象 | HARD |

**小结**：grace + recheck 防活读被抢删。

---

### 4.8 `S13-E08` — 预算、写闸、concurrency

**真相**：S13-T020/T023

| 预算/闸 | 默认 | 超限 |
|---|---|---|
| 单对象 max size | **256 MiB**（可配上调） | `OBJECT_BUDGET_SIZE` |
| chunk 大小 | 有界（实现钉，如 1–8 MiB） | — |
| volume free-space floor | 配置 | `OBJECT_BUDGET_SPACE` |
| 写闸 max in-flight promotes | 配置 | `OBJECT_UNAVAILABLE_*` |
| 多协程读 | 允许 | — |
| 多 OS 进程写同 root | **禁止**（v1） | 配置/启动拒绝 |

v1 **不做**应用层压缩/加密；盘级加密归部署/S16。

**小结**：有界；fail-closed。

---

### 4.9 `S13-E09` — Readiness 与 identity

**真相**：S13-T028

**Readiness=false 当**：

1. `object_root` 缺失或不可写；  
2. `identity.json` 缺失（非 empty bootstrap）或与 DB binding 不一致；  
3. atomic rename / fsync probe 失败；  
4. 生产配置关闭 durability fsync；  
5. grace=0 等非法配置。

Empty root：与 S12 bootstrap 协调创建 identity + 目录骨架。

Readiness ≠ liveness。

**小结**：错挂盘不可上业务流量。

---

### 4.10 `S13-E10` — Backup / restore 协议

**真相**：S13-T029；T-O-125

```text
1. maintenance fence / quiesce new promotes
2. S12 checkpoint / consistent snapshot point
3. copy DB + object_root (or ref-closure of live objects)
4. write manifest: schema head, identity, counts, sample digests
5. verify manifest
6. atomic rename to backup_uuid
7. release fence
Restore:
  empty target only → restore DB + object_root → verify → smoke → operator switch
```

| 分账 | 归属 |
|---|---|
| 一致性协议 | **S13**（本文） |
| 排程、保留份数、远程拷贝、权限 | **S15** |
| 加密密钥 | S16 / 部署 |

**小结**：协议强制存在；排程可后置。

---

### 4.11 `S13-E11` — 错误轴、OOS、交接

**错误码表**：

| code 前缀 | 条件 | 典型 retryability |
|---|---|---|
| `OBJECT_BUDGET_*` | size/free-space | non_retryable 或调配置后重试 |
| `OBJECT_INTEGRITY_*` | digest/size mismatch、非 regular file | non_retryable / incident |
| `OBJECT_MISSING_*` | live ref 无 bytes | incident；非静默 orphan 清 |
| `OBJECT_CONFLICT_*` | CAS 冲突、delete fence 中止 | retryable 或 conflict |
| `OBJECT_AUTH_*` | team/handle 不匹配 | non_retryable |
| `OBJECT_UNAVAILABLE_*` | readiness/root 只读/写闸满 | retryable |

**OOS**：无 public object CRUD、presigned upload/download、bucket list、对象浏览器。

**交接**：

| 对方 | 合同 |
|---|---|
| S04/S05/S06/S07 | 只消费 handle+digest；purpose 正确 |
| S12 | object 三表 + bytes-first TX |
| S11 | 不经 object store 存向量全文 |
| S15 | GC/backup 排程与 metric |
| S16 | 盘加密与 secret |
| 未来 R2 | 仅 adapter；契约不变 |

---

## 5. 事实反例、风险与实施切片

| 反例 / 风险 | 围栏 |
|---|---|
| legacy `r2_key` 进 wire | handle only |
| 对象存在=Process success | T-O-111；bytes-first |
| 无 ref 扫盘误删 open gate | purpose + live ref |
| TX 内无界 stream | 事务外 I/O |
| 双写 local+R2 | v1 禁止 |
| 错挂 object_root | identity readiness |
| 256MiB 不够大 PDF | 配置上调；禁默认无界 |
| QNA 当说明书 | 禁止 |

**实施切片**：Port+layout → promote/fsync → catalog TX 接合 → verified read → GC → readiness → backup 协议骨架 → architecture tests。

---

## 6. 强制验收矩阵

| ID | HARD | 期望 |
|---|---|---|
| S13-A01 | promote 后崩溃再 TX 回滚 | orphan 可 GC；无业务 success |
| S13-A02 | 同 team 同 digest 并发 promote | 复用；无不同内容覆盖 |
| S13-A03 | 跨 team 同 digest | 不复用 |
| S13-A04 | open gate_evidence | GC 不删 |
| S13-A05 | serving/current 保护 | 不 release/GC |
| S13-A06 | 篡改文件 verify | INTEGRITY + incident |
| S13-A07 | live ref 删文件 | MISSING 非静默清 |
| S13-A08 | 超 256MiB 默认 | BUDGET |
| S13-A09 | path `..` | 拒绝 |
| S13-A10 | identity mismatch | readiness false |
| S13-A11 | domain pathlib 写 root | arch fail |
| S13-A12 | public object HTTP | 不存在 |
| S13-A13 | delete fence 竞态 | 中止删 |
| S13-A14 | grace=0 | 拒绝/readiness fail |
| S13-A15 | backup verify 失败 | 不标记完整 |
| S13-A16 | handle team 不符 | AUTH |
| S13-A17 | staging 过期 | 可清且无 live ref |
| S13-A18 | Process terminal | 不级联硬删对象 |
| S13-A19 | crash suite fsync | 完整或可回收 |
| S13-A20 | zero legacy r2/SMCP storage | 扫描零命中 |
| S13-A21 | 实现可不打开 QNA | 文档自包含 |

---

## 7. Reference-anchor 台账

| Anchor | 裁决 |
|---|---|
| admin `r2.ts` / skill io_manager | 删除 presign/wire key；保留 Port 思想 |
| filesystem_store.py | 保留沙箱/atomic rename；升级 fsync/digest |
| ES-04 object 草案 | 吸收 CAS+ref；reservation 表 defer |
| QNA S13 | 证据 only |

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO / execution-complete for v1.1`**：S13 作为对象存储 **唯一执行真相** 已含 E01–E11；实现不得外挂 QNA。

### 8.2 强制结论

1. domain-truth only；local Port/CAS/bytes-first；  
2. catalog+ref+purpose；GC grace+fence；  
3. verify-on-read；identity readiness；  
4. backup 协议；无公网 object 面；  
5. G-11 closed → v1 local；R2 未来只扩 adapter。

### 8.3 一句话

S13-v1.1 把对象存储从「宪法」升格为 **可编码执行台账**，并独占对象层执行真相。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| S13-v1.0 | 2026-08-11 | accepted | T-O-111..125；local/CAS/GC；关 G-11 |
| S13-v1.1 | 2026-08-12 | accepted | **执行 SSOT 强制**；E01–E11；禁止执行依赖 QNA |
| S13-v1.1-ns6-note | 2026-08-20 | change-request | 物理 GC 删除 = TX1 fence → 将 CAS 字节 **rename** 到 `quarantine/<team_uuid>/` → TX2 proof/tombstone → destroy；TX2 见 live ref 则 restore。缺 quarantine API 必须 fail-closed，禁止回退 `unlink`。 |
