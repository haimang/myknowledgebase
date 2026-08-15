# S15 — Observability & Reliability

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`F3 运行基础 / S15 Observability & Reliability`（事件保留·指标导出·告警 runbook·ready/live·trace 关联·dead-letter 可观测·repair evidence·operator 只读面）
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Grok workflow domain-truth-s14-s16`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S15 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S15-v1.1`
>
> **上游权威输入**：`D01–D05`、`S01–S14` accepted（含 `S12-v1.1` / `S13-v1.1` / `S14-v1.0`）；`qna-truth/S15.md v1.0-qna-locked`（**证据层 / progressive 中间态 only**，非执行 SSOT）；冻结 Truth `T-O-287..311`；`spec-index` §3.15 / **G-02 closed polling** / **G-19 recovery cutoff** / G-11 local object / OD-01 leaf-worker
>
> **词汇权威**：`docs/baseline/spec-glossary.md`（`DomainEventLedger` / `OpsDiagnosticLog` / `SecurityAuditEvent` / `Readiness` / `Outbox` / `DeterministicRecovery` 等）
>
> **事实证据**：`context/legacy-family/` 仅作 ReferenceAnchor（log/dispatcher/console/vectorizer/purge 行为考古）；网络 Reference-Check（Prometheus cardinality、K8s probes、W3C Trace Context、SRE golden signals、outbox/DLQ、RFC 9457、OWASP logging）**仅作设计对照**；**禁止** `legacy-specs` / `legacy-python` / `legacy-python-2` 作为本域证据源
>
> **下游消费者**：`S01`、`S02`、`S03`、`S09–S14`、`S16`、跨系统拓扑 `17`、验收冻结 `18`、实现与 architecture tests

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S15.md` 仅保留 progressive 形成过程（`T-O-287..311` 冻结轨迹），**不得**被引用为第二执行真相；冲突时 **以本文为准**。禁止「细节在 QNA、Spec 只写原则」。实现 **无需** 打开 QNA 即可编码。

> **★ 约束级别**：「必须 / 禁止 / 仅允许」= 强制；「应当」= 默认，偏离须 reopen S15；「可以 / 建议」= 非冻结不变量。

> **Owner 产品边界**：S15 是 MKB **Observability & Reliability** 域。它回答：事件/诊断/安全审计 **如何保留与归档**、**导出哪些低基数 metric**、**哪些症状必须告警**、**ready/live 如何导出**、**trace 如何贯穿**、**data-repair 权限如何分账**、**运维如何只读排障**。  
> **关键不变量**：`team_uuid` / `task_uuid` / `trace_uuid` 贯穿业务域事件；**失败不能只存在于日志字符串**；业务成功/失败以关系表 CAS / Outcome / pointer 为准。  
> **D04 分账**：物理表名闭集已冻 `mkb_domain_events` / `mkb_ops_diagnostic_logs` / `mkb_security_audit_events`；S15 **拥有** retention 数值、告警阈值、export（Prometheus/OTLP）、runbook 语义——**不**另起第二套表名。  
> **不**拥有：业务状态机与 CAS（S02/S03/D01）；物理表 DDL/索引闭集（D04）；outbox 投递环实现（S12）；ANN/publication 算法（S09）；对象 GC 协议（S13）；密钥生命周期与 trust model 主责（S16）；Task Audit 上游快照（S01/S02）；完整 APM SaaS / 公网 metrics marketplace / console 运营中台。

> **邻域分账（入口）**：
>
> | 邻域 | S15 边界 |
> |---|---|
> | **D04** | 可观测 **三表物理 DDL/索引** 已冻；S15 **不**改表名闭集；拥有 retention/alert/export/runbook |
> | **D01/S03** | Process 事件与 repair **语义** 归 D01/S03；S15 记录 evidence/metric/alert，**无**独立 Reconciler 产品 |
> | **S02** | 上游 **polling** 状态/结果；**非** event 推送交付；S15 不为 webhook 建设默认设施 |
> | **S12** | TX+outbox/claim/lease 物理兑现；dead outbox → S15 告警；readiness probe 与 S15 health 导出协作 |
> | **S09/S10** | readiness 业务谓词 / publication；S15 导出 metric，**不**定义 ANN 算法 |
> | **S13** | GC/backup **协议** 归 S13；**排程/保留份数/metric** 归 S15 |
> | **S14** | config/registry **域**钩子逻辑名 + 映射表；**跨域默认命名权在消费域+S15 目录**；export/retention 归 S15 |
> | **S16** | security_audit **写语义**；sec metric 钩子名；`sec_token_loaded` 谓词；S15 收录 export 目录 + alert + retention/query |
> | **S01** | Task Audit（上游）与 MKB Event/Log **分表分义**；reject 不写业务行时仍须可审计 |
> | **S11** | invocation 表非 diagnostic_logs 替代；指标/retention 数值归 S15 |

> **Legacy 边界（T-O-301 / T-O-42）**：不继承 `smind_logs` 作跨 Worker 隐式 SSOT、console `files/debug/*` UI 运营面、`/health` 恒 ok 伪探针、queue ACK 当业务成功、log 写失败静默、team 仅塞 payload_extra 无一等列、trace 断裂时生成新 ID、compensating restarter 当完整 reconciler 宣传。

> **S16 邻域合同（`S16-v1.0` accepted · 强制消费）**：operator/repair 的 token 形状/轮换/网络暴露 **服从** `S16-v1.0` **T-O-327..329 / S16-T017/T026..T028/T048**（Bearer 主路径、EndpointClass 矩阵、repair 必 token）。security_audit **写入/威胁模型** 主责 S16（T-O-316/S16-T005/T052..T055）；S15 主责 retention/export/alert 与 **ObservabilityReadPort 查询**。readiness 组件 `sec_token_loaded` 谓词权威=S16，导出/聚合=S15。redaction 字段闭集权威=**S16-T056**（S15 执行路径服从，禁平行改表）。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S15 把 **可观察性与可靠性运维面** 变成 **可编码、可验收、与业务 CAS 严格分账的执行事实**，并保证：

1. 业务变迁事件与业务 **同 TX** 写入 `mkb_domain_events`；插入失败 → 整 TX 失败；  
2. 诊断日志可 best-effort，但 **必须** metric/stderr 兜底，不得静默丢尽；  
3. 安全/admission 拒绝进 `mkb_security_audit_events`，**不**并入业务时间线表；  
4. 三表有 **分层 retention** 与整段归档 DELETE；与 Process cleanup **分账不级联**；  
5. Metric 为 **低基数闭集** + Prometheus 主导出；**禁止** uuid 高基数 label 与业务库时序表；  
6. 必告警闭集覆盖 dead outbox / readiness false / repair fail 等 **症状**；  
7. `/live` ≠ `/ready`；live 硬禁外部依赖探测；  
8. root `trace_uuid` 全生命周期不替换；关联靠列，不靠 log 字符串；  
9. data-repair **无外部业务写面**；S03 语义 + S12 扫描 + S15 evidence；  
10. 实现者 **无需** 打开 QNA 即可编码与验收。

### 1.2 在整体拓扑中的位置

```text
业务 TX (S12 UnitOfWork)
  ├── CAS tasks/executions/processes/...   ← 唯一业务成功/失败 SSOT
  ├── mkb_outbox (intent)
  └── mkb_domain_events  (同 TX · append-only · 非 SSOT)
         │
         ▼
S15 ObservabilityPort
  ├── DiagnosticSink (best-effort → mkb_ops_diagnostic_logs)
  ├── MetricRegistry (low-card · RED/USE/Golden)
  ├── AlertEvaluator (symptom-first 闭集)
  ├── HealthExport (/live · /ready · readiness gauges)
  ├── TraceContext (root immutable · correlation columns)
  ├── RetentionJob (90d / 14d / 180d 整段 DELETE)
  ├── DeadLetterView (outbox status=dead 可查+告警)
  └── ObservabilityReadPort (by-trace/by-task timeline · 只读)
         │
         ├── GET /metrics  (Prometheus scrape · 主)
         ├── GET /live     (liveness · 无外部依赖)
         ├── GET /ready    (聚合各域谓词 · 503=not ready)
         └── optional OTLP metrics/traces (默认关/极低采样)
         │
S16 ── security_audit write semantics / token
S03 ── repair transition semantics
S12 ── outbox/claim/lease/migration physical
S13 ── backup protocol execution (schedule owned by S15)
S14 ── logical metric hook names / ops knobs
```

**数据面 vs 控制面（本域）**：

```text
数据面（关系库 · D04 表）
  domain_events / diagnostic_logs / security_audit  → 保留、查询、归档
控制面（进程内 · 非业务 SSOT）
  in-memory metrics · alert state · readiness cache  → scrape/导出
禁止：把 metrics 时序写回业务库作 SSOT
```

### 1.3 Scope fence

**S15 负责：**

- 三表 **retention 默认天数、归档 job、可选 pre-delete offline export 非 SSOT**；  
- S13 backup **排程 / 默认保留份数 / backup metric**（协议执行仍 S13）；  
- Metric **闭集目录、label 白名单、cardinality 丢弃、Prometheus/OTLP export**；  
- Alert **必告警闭集、默认阈值意图、抑制、runbook 最小字段、ops 通知分键**；  
- Ready/Live **HTTP 形状、聚合导出、obs_tables 组件、JSON 安全围栏**；  
- Trace **传播不变量、关联强制、OTLP 采样默认、禁静默重生**；  
- Repair **evidence/metric/alert 与权限分账陈述**（不定义 transition 语义）；  
- Operator **只读 Port / 可选 CLI**（内网+token）；  
- Dead-letter **可观测与 runbook**（redrive 协议执行在 S12）；  
- 可观测错误轴 `OBS_*` 与 diagnostic 失败策略；  
- 安全脱敏围栏与 v1 OOS 闭包；  
- 与各域 **ownership 分账表** 及配置键（ops knobs）登记。

**S15 不负责：**

| 排除项 | 归属 |
|---|---|
| Task/Execution/Process 状态机与 max_retries | D01 / S03 / S02 |
| 三表物理 DDL / 索引 / 表名闭集 | **D04** |
| Outbox 投递环 / claim / lease 扫描实现 | **S12** |
| Repair transition 语义 / 四窗口 | **S03** |
| ANN / PublicationProof / ActiveIndexPointer | **S09** |
| 对象 GC 语义 / backup 协议步骤 | **S13** |
| 逻辑 metric 钩子 **命名** 登记 | **S14**（export 归 S15） |
| 密钥签发/轮换/token 生命周期 | **S16** |
| security_audit **写入语义 / 威胁模型主责** | **S16**（S15 协作 retention/export） |
| Task Audit 上游快照 | **S01/S02** |
| 完整 APM SaaS / metrics marketplace / console UI | **OOS v1** |
| 业务 webhook / callback 默认交付 | **G-02 / OOS** |
| 独立通用 Reconciler 产品 | **G-19 / OOS** |

### 1.4 身份与关键对象

| 对象 | 定义 | 非定义 |
|---|---|---|
| **DomainEventLedger** | `mkb_domain_events` 行；与业务同 TX 的 append-only 时间线 | 非业务状态 SSOT；非上游推送总线 |
| **OpsDiagnosticLog** | `mkb_ops_diagnostic_logs` 行；诊断级 | 非 proof / route / 唯一终态 |
| **SecurityAuditEvent** | `mkb_security_audit_events` 行；admission/安全面 | 非 Task Audit；非 domain_events 子集 |
| **MetricSample** | 低基数时序点（进程内 registry） | 非业务表行；非 uuid 级 series |
| **AlertBinding** | alert_id + 条件 + 抑制 + runbook 字段 | 非 Task 完成回调；非 APM 规则引擎产品 |
| **LivenessProbe** | 进程存活探测 | 非依赖健康；非业务就绪 |
| **ReadinessProbe** | 可接新业务流量的聚合门 | 非业务状态机；谓词所有权在各域 |
| **TraceRoot** | 上游/创建时确定的 `trace_uuid` | 不可静默重生的关联根 |
| **ObservabilityReadPort** | 只读时间线/dead/health/metrics 查询面 | 非写面；非 console UI |
| **RetentionPolicy** | 三表天数 + 归档 DELETE 规则 | 非 Process cleanup；非 per-team 套餐产品 |
| **DeadLetterView** | outbox `status=dead` 可观测投影 | 非第二业务队列 SSOT |
| **OBS_* Error** | 可观测域 typed 错误码 | 非业务 CAS 错误主轴 |

### 1.5 完成定义

1. §2 全部 Truth 被 contracts / ports / jobs 实现；  
2. domain_events 与业务同 TX；失败则整 TX 失败；  
3. diagnostic 失败不回滚业务但 `mkb_diagnostic_drop_total` + stderr 可见；  
4. retention job 按默认天数整段 DELETE，幂等，失败可告警；  
5. `/metrics` 仅低基数；uuid 作 label 被拒绝并计数；  
6. `/live` 不查 DB；`/ready` 聚合组件且 not ready → 503 拒新业务；  
7. dead outbox 可查询且 `ALERT_OUTBOX_DEAD` 可触发；  
8. 无外部 operator 业务状态写面；内部 repair 仅 S03+S12+evidence；  
9. 零 legacy log-as-SSOT / 恒 ok health / console 运营中台依赖；  
10. 实现 **无需** 打开 QNA；§6 验收矩阵可通过。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O · S15 段 · 执行摘要）

| Truth-ID | 子类型 | 摘要 | 本域强制 |
|---|---|---|---|
| `T-O-287` | fence / scope | S15 = Observability & Reliability；不吞状态机/DDL/outbox/ANN/GC/密钥 | scope |
| `T-O-288` | fence / physical-tables | 三表闭集 required；metrics 时序不进业务库；禁第二套表名 | tables |
| `T-O-289` | fence / log-not-ssot | 业务成功以 CAS/Outcome 为准；失败不可仅存日志字符串 | ssot |
| `T-O-290` | fence / correlation-ids | 业务事件强制 team+trace；适用 task/execution/process | correlate |
| `T-O-291` | fence / domain-events-same-tx | domain_events 同 TX；失败整 TX 失败；append-only | tx |
| `T-O-292` | fence / diagnostic-best-effort | diagnostic 可 BE；失败不回滚业务；须 metric/stderr | diag |
| `T-O-293` | fence / security-audit-split | security_audit 分表；denied 必写；与 Task Audit 分义 | audit |
| `T-O-294` | fence / recovery-no-reconciler | repair 语义 S03；扫描 S12；S15 evidence；禁 Reconciler 产品 | recovery |
| `T-O-295` | fence / ready-vs-live | Readiness ≠ Liveness；S15 导出不改谓词所有权 | health |
| `T-O-296` | fence / polling-no-webhook | v1 结果=polling；不为业务 webhook 建默认设施 | delivery |
| `T-O-297` | fence / retention-split | Event/Log retention 与 Process cleanup 分账不级联 | retention |
| `T-O-298` | fence / outbox-dead-alert | dead 可告警/可查；ACK≠业务成功 | dlq |
| `T-O-299` | fence / ops-surfaces-split | backup 排程/份数/metric 归 S15；export 归 S15 | ops-split |
| `T-O-300` | fence / non-goals | 禁 APM SaaS、marketplace、log 替 CAS、UI 中台、Reconciler、库内 metrics 表 | non-goals |
| `T-O-301` | fence / evidence | 仅 legacy-family；不继承 N 反模式 | evidence |
| `T-O-302` | execution / retention-policy | 90d/14d/180d + 整段 DELETE + backup 7 份 | E02 |
| `T-O-303` | execution / metric-catalog-export | 低基数闭集 + Prometheus 主 + OTLP 可选 | E03 |
| `T-O-304` | execution / alert-runbook | 必告警闭集 + symptom-first + runbook | E04 |
| `T-O-305` | execution / ready-live-export | `/live` vs `/ready`；live 禁依赖 | E05 |
| `T-O-306` | execution / trace-propagation | root 不替换；无强制 span 树；OTLP 默认关/低 | E06 |
| `T-O-307` | execution / repair-authority | 无外部写面；S03+S12+S15 分账 | E07 |
| `T-O-308` | execution / operator-read-surface | 只读 Port；内网+token | E08 |
| `T-O-309` | execution / dead-letter-runbook | dead 可查+告警；S12 显式 redrive | E09 |
| `T-O-310` | execution / obs-error-taxonomy | typed OBS_*；events fail-closed；diag BE | E10 |
| `T-O-311` | execution / security-obs-oos | 脱敏 + OOS 闭包 | E11 |

### 2.2 域内 Truth 编号（S15-T）

> 域内 `S15-Txxx` 为本文引用别名，**映射**全局 T-O；**不**构成第二编号空间的改写权。变更须显式 reopen 并 append 新 T-O。

#### 2.2.1 Fence 映射（S15-T001..T015 ↔ T-O-287..301）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S15-T001` | S15 拥有 retention/alert/export/runbook/ready-live 导出/trace 约定/dead 可观测/repair evidence/operator 只读面；不拥有状态机、DDL 表名、outbox 环、ANN、GC 协议、密钥主责、Task Audit。 | T-O-287 | scope architecture |
| `S15-T002` | 可观测物理表闭集 required：`mkb_domain_events`、`mkb_ops_diagnostic_logs`、`mkb_security_audit_events`。禁止另起第二套表名/平行事件库。metrics 时序不进业务主库。 | T-O-288 | D04-P13 对齐 |
| `S15-T003` | 业务成功/失败以关系表 CAS/Outcome/pointer 为准；三表均非业务 SSOT。禁止只写日志当终态；禁止凭 log 字符串恢复状态而不读业务表。失败须在 Process/Execution/Task（或 security_audit for admission deny）可查询。 | T-O-289 | log≠SSOT |
| `S15-T004` | 业务域事件强制 `team_uuid` + `trace_uuid`（NOT NULL）+ 适用时 `task_uuid`/`execution_uuid`/`process_uuid`。系统/ops 可用 sentinel team `00000000-0000-0000-0000-000000000000`。禁止无 team 的租户业务事件默认可写。 | T-O-290 | correlation |
| `S15-T005` | `mkb_domain_events` 与触发业务同事务；插入失败 → 整 TX 失败。append-only；禁止 UPDATE 业务列；允许 retention 整段 DELETE。payload bounded；禁 secret/正文/唯一 proof。 | T-O-291 | same-TX |
| `S15-T006` | `mkb_ops_diagnostic_logs`：优先同 TX；纯诊断允许 commit 后 best-effort；写失败不回滚业务，须 stderr+metrics。禁止 diagnostic 承载唯一状态/proof/route。 | T-O-292 | diag BE |
| `S15-T007` | `mkb_security_audit_events`：admission/安全拒绝与「未进业务表的拒绝」。**「必写」= metric 全量 + audit 至少采样/聚合行，禁止 silent**（消费 S16-T052/T055：invalid-token/rate-limit/egress 高 QPS 可采样）。`ALERT_SECURITY_DENY_SPIKE` **以 `mkb_sec_auth_total` 等 metric 为权威计数**；audit 采样不定义「未写明细=未拒绝」。与 Task Audit 分表。S16 写语义；S15 retention/export/alert + `list_security_audit` 查询。禁止 security 并入 domain_events。 | T-O-293 | audit split |
| `S15-T008` | repair 语义 = S03；scan/outbox/claim = S12；evidence/metric/alert = S15。禁止 v1 独立通用 Reconciler 产品作第二状态推进引擎。repair 不得从 log/UI/storage 合成 decision。 | T-O-294 | G-19 |
| `S15-T009` | Readiness ≠ Liveness。S15 负责导出/探针约定与告警；不改各域 readiness 谓词所有权。进程活但 readiness=false 时拒绝新业务流量。 | T-O-295 | probes |
| `S15-T010` | v1 异步结果交付 = polling。S15/S16 不为 webhook/callback 建设默认设施。domain_events 不是对上游的推送总线。 | T-O-296 | G-02 |
| `S15-T011` | Process cleanup eligibility（S03）与 Event/Log retention（S15）分账；cleanup 禁止级联删除 Task Audit、Execution summary、S15 Event/Log。数值天数归 S15，不得被 S03 硬编码。 | T-O-297 | cleanup fence |
| `S15-T012` | S12 outbox 毒消息 → `status=dead` + S15 必须可告警/可查询。ACK ≠ 业务成功。dead-letter 不是独立第二业务队列 SSOT。 | T-O-298 | dead alert |
| `S15-T013` | S13：backup 协议、GC 语义；S15：backup 排程/保留份数、GC/backup metric。S14：逻辑钩子名；S15：export 实现。S09/S10/S11：域事件种类与 readiness 条件；S15：保留策略与告警。 | T-O-299 | ops split |
| `S15-T014` | v1 非目标：完整 APM SaaS；公网 metrics marketplace；log/event 替换 CAS；平台 UI 运营中台；webhook 默认推送；独立 Reconciler 服务作状态 SSOT；业务库内 metrics 时序表。 | T-O-300 | non-goals |
| `S15-T015` | 唯一 legacy 证据树 = `context/legacy-family/`。不继承 N-01..N-15 反模式清单（§5）。 | T-O-301 | evidence |

#### 2.2.2 Execution 映射（S15-T016..T025 ↔ T-O-302..311）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S15-T016` | 分层默认 retention：events **90d**；diagnostic **14d**；security_audit **180d hot 默认**（非合规天花板；可 ops 上调并写 `ops.retention_policy_changed`）。批 DELETE by `occurred_at`；禁 UPDATE 业务列；与 Process cleanup 分账不级联。**timeline 在 retention 窗外不保证**；lineage/status SSOT 仍在 Task/Execution/summary 表；查询须返回 empty/truncated，**禁止**从部分 events 合成终态。若配置了 pre-delete export：export 失败 → **禁止 DELETE** + `ALERT_RETENTION_JOB_FAIL`（或专用 fail metric）；export 本身非业务 SSOT。legal-hold 产品 **OOS**（残差见 S16 TM-10 runbook）。S13 backup：S15 唯一 cron 调 S13 协议。 | T-O-302 | E02 |
| `S15-T017` | v1 低基数 metric **闭集目录 SSOT=本文 §4.3**；主 export=`GET /metrics`。邻域钩子：S14 仅 **config/registry 域**逻辑名（须映射 `mkb_*`）；S16 **sec_*** 钩子名由 S16 冻、**必须**在 S15 目录收录后才可 export；S09/S12 同。**禁止**邻域单独冻 export 名而不更新 S15。新增 series = code registry + 本文 change-request。label 纪律同前。 | T-O-303 | E03 |
| `S15-T018` | 必告警：`ALERT_OUTBOX_DEAD`、`ALERT_READINESS_FALSE`、`ALERT_REPAIR_FAIL`、`ALERT_DIAG_DROP`、`ALERT_LEASE_STUCK`、`ALERT_RETENTION_JOB_FAIL`；**安全必告警**：`ALERT_SECURITY_DENY_SPIKE`（默认开；阈=`obs.alert.security_deny_spike_per_min` 默认 **100**/min，消费 `mkb_sec_auth_total`）、`ALERT_SEC_RATE_LIMITER_DEGRADED`、`ALERT_SEC_TOKEN_RELOAD_FAIL`、`ALERT_SEC_AUDIT_WRITE_FAIL`（owner_domain=S16）。主通道 metric+`ops.alert_raised`+stderr。禁止 Task webhook 混用。 | T-O-304 | E04 |
| `S15-T019` | `GET /live`（兼容 `/healthz`）= 进程存活；**硬禁** 查 DB/vector/object_root/registry/外部依赖。`GET /ready` = 可安全接新业务流量；聚合组件闭集；谓词所有权在各域。not ready → HTTP **503** 且拒绝新业务入口。JSON 禁 secret/token/绝对 path。metric `mkb_readiness{component}`。禁止单一恒 ok `/health` 混充 ready。 | T-O-305 | E05 |
| `S15-T020` | root `trace_uuid` 由上游 Task Create 确定后全生命周期不替换；已持久化业务 root 禁止静默重生；W3C restart 不适用于 MKB 内部 recovery。`mkb_domain_events.trace_uuid` 强制 NOT NULL。业务事件强制 team + 适用主体 UUID。v1 不强制完整 OTel span 树/APM。可选 W3C 透传（主变 parent-id/sampled）与 **默认关或 ≤1%** OTLP traces。trace 头/字段禁 PII。禁止用 log 字符串代替关联列。 | T-O-306 | E06 |
| `S15-T021` | v1 **无**外部 operator 业务状态写面。repair 语义=S03；scan/outbox/lease=S12；evidence/metric/alert=S15。禁止独立 Reconciler 产品；禁止从 log/UI/storage/payload_extra 合成 decision。可选受控内部 `repair_scan_once` hook 必须写 security_audit + domain_event 且禁公网。一切状态变更仍 CAS + 同 TX domain_events；重复扫描 no-op。 | T-O-307 | E07 |
| `S15-T022` | 最小只读 Observability Port：by-trace/by-task 时间线、dead 列表、health、metrics；可选本地 CLI。默认 **内网 + 内部 token（S16）** + team **过滤**。禁止匿名公网、console UI 运营中台、metrics marketplace、只读面变写面、JWT 多租户运营中台、file-debug 任意读盘。`team_uuid` ≠ 授权凭证。 | T-O-308 | E08 |
| `S15-T023` | outbox `status=dead` 可查询 + 必 metric/alert（存在/增量 + 可选 oldest age）。可选低频 `outbox.dead` ops 事件（bounded，禁 secret）。重放仅经 S12 显式 requeue/reset attempts 且可审计。禁止未修根因自动循环 redrive、silent drop、无审计 dead→done、独立 DLQ 第二业务 SSOT。ACK ≠ 业务成功。 | T-O-309 | E09 |
| `S15-T024` | typed `OBS_*` 闭集至少含：`OBS_EVENT_APPEND_FAIL` / `OBS_EVENT_PAYLOAD_INVALID` / `OBS_DIAG_APPEND_FAIL` / `OBS_METRIC_EXPORT_FAIL` / `OBS_RETENTION_JOB_FAIL` / `OBS_CARDINALITY_DROP` / `OBS_TIMELINE_QUERY_FAIL` / `OBS_READY_COMPONENT_FAIL`。domain_events 失败 → 整 TX 失败；diagnostic 失败 → 不回滚 + drop metric + stderr。对外可映射 RFC 9457 风格。禁止 silent swallow 与 domain_events best-effort。 | T-O-310 | E10 |
| `S15-T025` | Redaction **字段闭集权威 = S16-T056**（// sync-from S16；变更仅 S16 change-request）；S15 执行路径必须服从。`team_uuid`≠auth。security_audit 分表。v1 OOS 见 E11。 | T-O-311 | E11 |

#### 2.2.3 派生执行 Truth（S15-T026..T060 · 可编码细则）

| ID | 冻结内容 | 来源 |
|---|---|---|
| `S15-T026` | Retention 配置键（ops knobs，不进 binding_digest）：`obs.retention.domain_events_days` 默认 **90**；`obs.retention.diagnostic_logs_days` 默认 **14**；`obs.retention.security_audit_days` 默认 **180**；`obs.retention.batch_size` 默认 **1000**；`obs.retention.job_interval_seconds` 默认 **3600**。 | T-O-302 |
| `S15-T027` | Retention job 伪算法：按表 `DELETE FROM <table> WHERE occurred_at < now() - interval days LIMIT batch` 循环直至本轮 0 行或预算耗尽；记录 `mkb_retention_delete_rows_total{table}` 与 last_success gauge；失败 → `OBS_RETENTION_JOB_FAIL` + `ALERT_RETENTION_JOB_FAIL`。 | T-O-302 |
| `S15-T028` | 变更 retention 天数必须写 `ops.retention_policy_changed` domain_event（ops/system actor；bounded payload：old/new days、table、actor_fingerprint）；禁止静默改全局默认。 | T-O-302 |
| `S15-T029` | Pre-delete offline export（可选）：导出到 ops 目录或对象 handle；**明确非** 业务 SSOT / 非第二事件库；格式不进入业务 contracts 作为恢复权威。 | T-O-302 |
| `S15-T030` | S13 backup 排程默认：`obs.backup.schedule_cron` 默认 **每日一次**（部署可覆盖字面量）；`obs.backup.retain_copies` 默认 **7**；metric `mkb_backup_last_success_unixtime`、`mkb_backup_fail_total`；协议步骤执行归 S13。 | T-O-302/299 |
| `S15-T031` | Metric 名字前缀默认 `mkb_`；族闭集见 §4.3 目录表。新增 metric 须 code registry + 本文 change-request；禁止运行时任意注册高基数 series。 | T-O-303 |
| `S15-T032` | Label 白名单全局：仅闭集 enum、固定 component 名、outbox kind 闭集、capability 闭集、table 三表名、result∈{success,conflict,error,ok,noop,fail}、device 有界枚举或 `none`。 | T-O-303 |
| `S15-T033` | Cardinality 硬拒绝：任何 label key ∈ {`task_uuid`,`trace_uuid`,`execution_uuid`,`process_uuid`,`user_id`,`path`,`url`} 或值长度/熵超阈 → 丢弃样本 + `mkb_metric_cardinality_drop_total{reason}`。 | T-O-303 |
| `S15-T034` | `GET /metrics` 默认路径；`obs.metrics.scrape_path` / `obs.metrics.enable` 为 ops knobs。scrape 失败 → `OBS_METRIC_EXPORT_FAIL`（不改业务）。 | T-O-303 |
| `S15-T035` | OTLP metrics exporter 默认 **OFF**（`obs.otlp.metrics_enabled=false`）；OTLP traces 默认 **OFF** 或采样率 ≤ **0.01**（`obs.otlp.traces_sample_ratio`）。 | T-O-303/306 |
| `S15-T036` | 告警默认阈值表见 §4.4；阈值均为 ops knobs，可调，**不**进 binding_digest。 | T-O-304 |
| `S15-T037` | Runbook 最小字段闭集：`alert_id`、`severity`∈{page,ticket,info}、`first_seen`、`related_metric`、`suggested_action`、`owner_domain`、`suppressed_until?`。 | T-O-304 |
| `S15-T038` | `ops.alert_raised` 事件：aggregate=`ops`；payload 仅 alert_id/severity/related_metric/component/kind 等低基数；禁 secret。 | T-O-304 |
| `S15-T039` | Ops-only 通知通道（email/webhook URL）与 Task 业务回调 **分配置键**；默认 `obs.alert.notify_enabled=false`。 | T-O-304/296 |
| `S15-T040` | Readiness 组件闭集 v1：`schema_migration`、`registry_bootstrap`、`db_primary`、`concurrent_writes`、`native_vector`、`object_root`、`inference_binding`、`obs_tables`、**`sec_token_loaded`**（谓词权威=S16；ActiveTokenSet 空 → not ready / `/ready` 503）。扩展须 change-request。 | T-O-305 |
| `S15-T041` | `obs_tables` 组件谓词（S15 所有）：三表存在且 migration 已应用；缺任一 → readiness false + `OBS_READY_COMPONENT_FAIL`。 | T-O-305 |
| `S15-T042` | `/ready` 响应 JSON 字段闭集意图：`status`∈{ready,not_ready}、`live` bool、`components[]`{name,ok,code?}、可选 `checked_at`。禁 secret/token/绝对 path/连接串。 | T-O-305 |
| `S15-T043` | not ready 时拒绝：**新** Task Create / **新** process claim。**交接**：S01 Create 与 S03/S12 claim 路径 **必须** fail-closed 查询 HealthAggregator/`Ready` 标志；HTTP **503** + 业务/OBS ready 码；**不**写 security_audit（非 admission deny）。既有 in-flight 靠 lease。 | T-O-305 |
| `S15-T044` | Trace：`DomainEventWriter` 拒绝 `trace_uuid` 空；业务 `team_uuid` 空（非 sentinel ops）拒绝。 | T-O-306 |
| `S15-T045` | 诊断无 trace 比例：`mkb_diagnostic_missing_trace_ratio` gauge；强烈推荐填 trace。 | T-O-306 |
| `S15-T046` | 内部 recovery/restarter **禁止** `uuid4()` 新 root 替换已持久化业务 `trace_uuid`；失败 fail-loud + 审计。 | T-O-306 |
| `S15-T047` | repair evidence 事件类型：`ops.repair_applied`（outcome∈ok\|noop\|fail）；metric `mkb_repair_applied_total{outcome}`。 | T-O-307 |
| `S15-T048` | 内部 hook `repair_scan_once`（可选）：仅 localhost/内网 + token；写 security_audit（action=`ops.repair_scan`）+ domain_event；**不**暴露公网 HTTP。 | T-O-307/308 |
| `S15-T049` | ObservabilityReadPort 方法闭集：`get_timeline_by_trace(**team**, trace_uuid, limit, cursor?)`（**team 必填**；省略/错配 → `SEC_TEAM_SCOPE_VIOLATION` / OBS deny）、`get_timeline_by_task(team, task_uuid, …)`、`list_outbox_dead(**team**, filter, limit, cursor?)`（**team 必填**；仅返回该 team 或 ops-scoped 行）、`list_security_audit(team?, time_range, action?, denial_code?, limit, cursor?)`（token+内网；跨 team 无显式 ops 模式则 deny；payload redacted）、`get_health_snapshot()`、`get_metrics_text()`。跨 team 枚举 **禁止**。 | T-O-308 |
| `S15-T050` | Timeline 投影字段：event_uuid、occurred_at、event_type、aggregate、severity、subject_*、summary、trace_uuid、task/execution/process uuid、payload_digest；**默认不**返回完整 payload_json 除非 debug 门控且仍脱敏。 | T-O-308/311 |
| `S15-T051` | 分页：默认 limit **50**；硬 cap **200**；cursor 基于 (occurred_at, event_uuid)。 | T-O-308 |
| `S15-T052` | Dead 列表投影：outbox_id、team_uuid、kind、attempts、status、updated_at、error_code?、oldest_age_seconds?；禁 payload 明文 secret。 | T-O-309 |
| `S15-T053` | Dead metric：`mkb_outbox_dead_total`（counter 或 gauge 深度）、`mkb_outbox_dead_oldest_age_seconds`（可选 gauge）。 | T-O-309 |
| `S15-T054` | Redrive：仅调用 S12 OutboxPort **`requeue_dead(outbox_id)` / `reset_attempts(outbox_id)`**（S12-v1.x 必补；CAS dead→pending、审计事件、禁 silent dead→done）；S15 只记录审计与 metric，**禁止** raw SQL 旁路。 | T-O-309 |
| `S15-T055` | `OBS_*` 完整闭集见 §4.10；对外 HTTP 映射 RFC 9457：`type`/`title`/`detail` + 扩展 `error_code`/`trace_uuid`；禁 stack/path/token。 | T-O-310 |
| `S15-T056` | DomainEventWriter / DiagnosticSink / MetricRegistry / AlertEvaluator / HealthAggregator / RetentionJob / ObservabilityReadPort 为建议代码边界（Port 名可微调，语义不可丢）。 | T-O-287+ |
| `S15-T057` | 脱敏 allowlist：event/log payload 仅允许 handle、digest、枚举 code、有界 id、截断 summary；secret 类字段 schema 级拒绝。 | T-O-311 |
| `S15-T058` | GC metric（消费 S13）：`mkb_gc_orphans_deleted_total`、`mkb_gc_fail_total` 等低基数；阈值告警可后续 ops 加，v1 不强制 page。 | T-O-299 |
| `S15-T059` | 实现无需打开 QNA；本文为唯一执行 SSOT。 | SSOT |
| `S15-T060` | contracts 落点建议：`src/contracts/observability/`（DomainEventPayload 对齐 D04、DiagnosticEntry、AlertBinding、HealthSnapshot、ObsError、TimelineView、RetentionPolicy）。 | D03 |

### 2.3 继承上游（不重开）

- **D04**：三表 DDL、同 TX 规则、event_type/aggregate 闭集、索引 `ix_de_trace` 等；`T-O-166..178`；S15 不改表名。  
- **D02-DR007**：物理事实不得成业务状态 SSOT；retention/runbook 本 Spec 收口。  
- **S03-T045..T049/T054**：repair 语义、cleanup 不级联 Event/Log、无 operator 写面、禁 log 合成 decision。  
- **S12-E05/E07**：outbox dead、ACK≠成功、migration/readiness 谓词。  
- **S13-T028/T029**：object_root readiness；backup 协议 vs 排程分账。  
- **S14-T030/T051**：ops knobs（scrape interval 等）；逻辑 metric 钩子名。  
- **S01-T005/T013/T035**：polling；root trace 不变；Audit 与 log 分表。  
- **S02-T035/T038**：lineage 不断；安全 error envelope。  
- **S09-T036/T045**：readiness ≠ liveness；域事件种类低基数，保留归 S15。  
- **G-02 / G-19 / OD-01 / OD-04 / OD-05**：polling、无 Reconciler 产品、无平台 UI、team≠auth、简单内部 token。

### 2.4 所有权分账总表（S15 owns vs consumes）

| 主题 | S15 owns | S15 consumes | 禁止 |
|---|---|---|---|
| 三表 DDL/表名 | — | **D04** | 第二套表名 |
| domain_events 写入时机 | 同 TX 纪律复述 + writer 端口 | 业务服务经 UoW 插入 | BE 冒充业务事件 |
| diagnostic 写入策略 | BE 规则 + drop metric | 各模块 log_code | 当 proof/SSOT |
| security_audit 写入语义 | retention/export/alert 查询 | **S16** 主责 | 并入 domain_events |
| Retention 天数/job | **是** | D04 表 | cleanup 级联删 |
| Process cleanup eligibility | — | **S03** | 混算天数 |
| Metric 逻辑钩子名 | 导出实现 | **S14**/S09/S12 名 | 高基数 uuid label |
| Metric 时序存储 | 进程内 + scrape | — | 业务库时序表 |
| Alert 阈值/runbook | **是** | S12 dead 行、各域 ready 谓词 | 业务 webhook 混用 |
| Repair transition | evidence only | **S03** 语义 | Reconciler 产品 |
| Outbox 投递/redrive | 可观测/告警 | **S12** 协议 | silent drop / 无审计 done |
| Readiness 谓词 | obs_tables + 聚合导出 | S12/S13/S09/S11/S14 | 改邻域谓词 |
| Liveness | **是**（进程探针） | — | live 查 DB |
| Trace root 策略 | 贯穿/不替换纪律 | **S01** 创建策略 | 静默重生 |
| Backup 协议步骤 | 排程/份数/metric | **S13** 执行 | 双写 runbook 矛盾 |
| Operator 写业务状态 | — | 无 | 外部写面 |
| Operator 只读排障 | **是** | S16 token | 匿名公网 / UI 中台 |
| 密钥/token 生命周期 | 形状要求 | **S16** | 自建 session 平台 |

---

## 3. 总体方案陈述

1. **三表分账、事件同 TX**：业务变迁时间线与 CAS 同命运；诊断降维；安全审计独立。  
2. **log/event 永不替代 CAS**：可观测是证据层，不是成功定义层。  
3. **分层 retention + 整段 DELETE**：90/14/180 天默认；cleanup 不级联。  
4. **低基数 metric + Prometheus 主路径**：uuid 只进事件查询，不进 label。  
5. **symptom-first 必告警闭集**：dead / not-ready / repair-fail 可见且可行动。  
6. **Ready ≠ Live**：live 轻量；ready 聚合各域门；503 拒新流量。  
7. **Trace 列优先于 span 产品**：root 不替换；v1 无强制 APM 树。  
8. **Repair 三方分账**：S03 语义 / S12 物理 / S15 证据；无外部写状态面。  
9. **Operator 只读 + 内网 token**：时间线可查，不建设 console 中台。  
10. **Dead 可查可告可显式 redrive**：非第二 SSOT；ACK≠成功。  
11. **Typed OBS_* 错误轴**：事件 fail-closed；诊断 BE 但可见。  
12. **QNA 零依赖**：全部执行细节在本文 §4。

---

## 4. 具体执行方案清单

### 4.1 `S15-E01` — 范围、非目标、三表纪律与邻域分账

**编号与说明**：建立 Observability 模块边界、硬非目标、与 D04/S03/S12/S13/S14/S16 的依赖方向。

**真相层对应**：S15-T001..T015；T-O-287..301

| 项 | 规范 |
|---|---|
| 域身份 | F3 / S15 Observability & Reliability |
| 代码落点（建议） | `src/services/observability/` 或 `src/obs/`；`src/contracts/observability/` |
| 公共 surface | `/live` `/ready` `/metrics`；内部 ObservabilityReadPort；可选 CLI |
| 非能力 | 不是 Process capability；不创建/推进 Task/Execution/Process |
| 硬非目标 | APM SaaS、marketplace、log 替 CAS、console UI、业务 webhook 默认、Reconciler 产品、库内 metrics 时序表 |

**执行台账**

1. Architecture 测试：业务 services 不得 raw SQL `INSERT` 平行事件表 / 三表绕过 Writer。  
2. DomainEventWriter **仅**经 UnitOfWork 同 TX 提交；**未登记 event_type → `OBS_EVENT_PAYLOAD_INVALID`**。  
3. 分账表（§2.4）进入允许依赖列表；禁止 obs 模块调用邻域私有状态机写路径。  
4. 登记 `obs_tables` readiness 检查进 HealthAggregator。  
5. 文档/code comment 声明：三表非 SSOT。

**最小 producer 矩阵（强制经 DomainEventWriter.append）**

| 生产者 | 示例 event_type | 规则 |
|---|---|---|
| S02/S03 | task.*/execution.*/process.* | 状态变更同 TX |
| S04/S05 | intake.* | 同 TX |
| S12 | outbox.enqueued / outbox.dead? | 同 TX 或采样策略 |
| S14 | registry.* / config.* | 见登记表 |
| S15 | ops.alert_raised / ops.retention_policy_changed / ops.readiness_changed | ops |
| S03/S12 repair | ops.repair_applied | 同 TX evidence |
| **禁止** | security.* 家族 | → security_audit only（S16） |

**v1 event_type 扩展登记表（S15 拥有 ops/registry/config 注册；D04 §3.1.3 同步为物理合同 SSOT）**

| event_type | aggregate | 写入方 | payload 允许键（有界） |
|---|---|---|---|
| `ops.repair_applied` | ops | S15/S12 | repair_id, outcome, component |
| `ops.readiness_changed` | ops | S15 | status, components_digest |
| `ops.alert_raised` | ops | S15 | alert_id, severity, related_metric, component |
| `ops.retention_policy_changed` | ops | S15 | table, days, actor |
| `outbox.dead` | outbox | S12/S15 | outbox_id, kind, error_code（可选低频） |
| `registry.bootstrap_completed` | registry | S14 | digest, counts |
| `registry.digest_mismatch` | registry | S14 | key, version |
| `config.ops_reload` | ops | S14 | result |
| `config.override_applied` | ops | S14 | OverrideAuditPayload v1 |

**小结**：S15 是运维与证据门面，不是第二状态机或第二 schema。

---

### 4.2 `S15-E02` — Retention 数值与归档 job

**编号与说明**：钉死三表默认天数、DELETE 策略、与 cleanup/backup 分账。

**真相层对应**：S15-T011/T016/T026..T030；T-O-302/297/299

**默认策略表**

| 表 | 默认 hot 天数 | 删除谓词 | 级联 |
|---|---|---|---|
| `mkb_domain_events` | **90** | `occurred_at < now-90d` 批 DELETE | **不**被 Process cleanup 删除 |
| `mkb_ops_diagnostic_logs` | **14** | 同上 | 最短；可丢 |
| `mkb_security_audit_events` | **180**（hot 默认） | 同上 | 可 ops 上调；写审计事件 |

**Backup（S13 协作）**

| 键 | 默认 | 所有者 |
|---|---|---|
| `obs.backup.retain_copies` | **7** | S15 配置 |
| `obs.backup.schedule_cron` | 每日一次（字面量部署可改） | S15 配置 |
| backup 步骤 / restore empty-target | — | **S13** |
| backup metric | last_success / fail_total | S15 导出 |

**执行台账**

1. 实现 `RetentionJob` 周期任务；幂等；可手动触发（内网+token）。  
2. Metric：`mkb_retention_delete_rows_total{table}`、`mkb_retention_job_success`、`mkb_retention_job_fail_total`。  
3. 失败 → `OBS_RETENTION_JOB_FAIL` + `ALERT_RETENTION_JOB_FAIL`。  
4. 变更天数 → `ops.retention_policy_changed` 事件。  
5. 可选 pre-delete export 文档化为 **非 SSOT**。  
6. 验收：Process cleanup 后 Event/Log 行仍在（直至 retention）。  
7. 禁止：UPDATE 改写 `summary`/`payload_json` 当「归档」；per-team 商业化套餐产品。

**小结**：分层保留 + 整段删除；证据窗口可预期，不与 cleanup 打架。

---

### 4.3 `S15-E03` — Metric 目录、cardinality 与 export

**编号与说明**：闭集低基数目录、label 纪律、Prometheus 主路径。

**真相层对应**：S15-T017/T031..T035；T-O-303

**v1 Metric 目录（逻辑名 · 可微调字面量前缀但语义冻结）**

| 族 | 逻辑名 | 类型意图 | 允许 labels | 信号族 |
|---|---|---|---|---|
| process/claim | `mkb_process_claim_total` | counter | `result`∈success\|conflict\|error | RED |
| process | `mkb_process_running` | gauge | — 或 worker 有界 | USE sat |
| outbox | `mkb_outbox_depth` | gauge | `kind` 闭集 | Golden sat |
| outbox | `mkb_outbox_dead_total` | counter/gauge | `kind` | errors |
| outbox | `mkb_outbox_dead_oldest_age_seconds` | gauge | `kind`? | sat |
| readiness | `mkb_readiness` | gauge 0/1 | `component` 闭集 | Golden |
| repair | `mkb_repair_applied_total` | counter | `outcome`∈ok\|noop\|fail | RED |
| diagnostic | `mkb_diagnostic_drop_total` | counter | `reason` 短闭集 | errors |
| diagnostic | `mkb_diagnostic_missing_trace_ratio` | gauge | — | quality |
| inference | `mkb_inference_requests_total` | counter | `capability`,`result` | RED |
| inference | `mkb_inference_duration_seconds` | histogram/summary | `capability` | RED duration |
| vector | `mkb_vector_upsert_total` | counter | `result` | RED |
| index | `mkb_index_generation_active` | gauge | `status` 低基数 | sat |
| queue | `mkb_worker_queue_lag_seconds` | gauge | — | USE sat |
| gpu | `mkb_gpu_util_ratio` | gauge | `device` 有界或省略 | USE |
| registry | `mkb_registry_resolve_total` | counter | `result` | RED（S14） |
| registry | `mkb_prompt_hash_mismatch_total` | counter | — | errors |
| registry | `mkb_registry_bootstrap_fail_total` | counter | — | errors（S14） |
| config | `mkb_config_override_rejected_total` | counter | — | errors（S14） |
| config | `mkb_config_ops_reload_total` | counter | `result`∈ok\|fail | ops（S14；默认不 page） |
| security | `mkb_sec_auth_total` | counter | `result`∈missing\|invalid\|ok | RED（S16-T060） |
| security | `mkb_sec_rate_limited_total` | counter | `dim`∈token\|ip | errors |
| security | `mkb_sec_rate_limiter_degraded` | gauge 0/1 | — | sat |
| security | `mkb_sec_egress_denied_total` | counter | `reason` 短闭集 | errors |
| security | `mkb_sec_secret_unresolved_total` | counter | — | errors |
| security | `mkb_sec_audit_write_fail_total` | counter | — | errors |
| security | `mkb_sec_token_reload_total` | counter | `result`∈ok\|fail\|last_good | ops |
| security | `mkb_sec_supply_reject_total` | counter | `code` 短闭集 | errors |
| retention | `mkb_retention_delete_rows_total` | counter | `table` 三表 | ops |
| cardinality | `mkb_metric_cardinality_drop_total` | counter | `reason` | errors |
| backup | `mkb_backup_last_success_unixtime` | gauge | — | ops |
| backup | `mkb_backup_fail_total` | counter | — | errors |
| alert | `mkb_alert_raised_total` | counter | `alert_id` | ops |
| lease | `mkb_lease_recover_total` | counter | `outcome` | RED |
| gc | `mkb_gc_orphans_deleted_total` | counter | — | ops |

**Cardinality 硬顶**

| 规则 | 规范 |
|---|---|
| 禁止 labels | `task_uuid` `trace_uuid` `execution_uuid` `process_uuid` 自由 path/URL user 输入 |
| team | **默认不**导出为 Prometheus label；team 过滤走事件查询 |
| 超标 | 丢弃样本 + `mkb_metric_cardinality_drop_total`；**不**崩进程 |
| 单位 | 优先 Prometheus base units：`seconds`、`ratio`（0–1） |

**Export**

| 路径 | 规范 |
|---|---|
| 主 | `GET /metrics` Prometheus text exposition |
| 可选 | OTLP metrics（`obs.otlp.metrics_enabled` 默认 false） |
| 禁止 | 业务库 metrics 时序表；公网未鉴权 marketplace |

**执行台账**

1. 实现 `MetricRegistry` 与白名单校验。  
2. 各域在代码中调用登记钩子（S14 逻辑名 **必须**映射到上表 `mkb_*`；S16 sec_* 已收录）。  
3. Architecture 测试：禁止 uuid label；**security middleware 挂载时 sec_* series 必须存在**；禁止注册未收录名。  
4. scrape path/enable 为 ops knobs。  
5. GPU 指标：无设备则 **省略** series（非伪造 0 当硬件存在）。

**小结**：可 scrape、可预算、不炸 cardinality。

---

### 4.4 `S15-E04` — Alert 闭集与 runbook

**编号与说明**：必告警、默认阈值意图、抑制、通道分账。

**真相层对应**：S15-T018/T036..T039；T-O-304

**必告警闭集**

| Alert ID | 默认条件意图 | 抑制默认 | severity | owner_domain | suggested_action |
|---|---|---|---|---|---|
| `ALERT_OUTBOX_DEAD` | dead 行存在 **或** dead 增量 > 0；可选 oldest age > **1h** | 15m 同 kind 合并 | page | S12 | 查 dead 列表 → 修根因 → S12 redrive |
| `ALERT_READINESS_FALSE` | 任一 required component ready=0 持续 ≥ **60s** | 5m | page | multi | 查 `/ready` components |
| `ALERT_REPAIR_FAIL` | repair fail ≥ **3 / 15m** 或连续 fail 模式 | 15m | page | S03/S12 | 查 repair events + CAS |
| `ALERT_DIAG_DROP` | drop 率 > **1% / 5m** 或绝对 N≥**50**/5m | 15m | ticket | S15 | 查 DB 写失败/背压 |
| `ALERT_LEASE_STUCK` | lease recover 失败上升或 stuck 计数升 | 15m | ticket | S12/S03 | 查 claim/lease scanner |
| `ALERT_RETENTION_JOB_FAIL` | retention job 失败 **或** 已配置 pre-delete export 失败仍将删 | 30m | ticket | S15 | 查磁盘/锁/export |
| `ALERT_SECURITY_DENY_SPIKE` | `mkb_sec_auth_total{result!=ok}` 速率 ≥ `obs.alert.security_deny_spike_per_min`（默认 **100**） | 10m | ticket | S16 | metric 权威；audit 可采样 |
| `ALERT_SEC_RATE_LIMITER_DEGRADED` | `mkb_sec_rate_limiter_degraded==1` 或 rate_limit.enabled=false | 5m | page | S16 | 保护降级 |
| `ALERT_SEC_TOKEN_RELOAD_FAIL` | `mkb_sec_token_reload_total{result=fail}` 上升 | 15m | ticket | S16 | last-good 仍在用 |
| `ALERT_SEC_AUDIT_WRITE_FAIL` | `mkb_sec_audit_write_fail_total` 上升 | 5m | page | S16 | admission fail-closed |

**通道**

1. **主**：metric 信号 + `ops.alert_raised`（bounded）+ stderr JSON 一行。  
2. **可选**：ops-only notify（默认关；与 Task webhook **分键**）。  
3. **禁止**：把告警当 Task 完成回调；全量 APM 规则引擎产品。

**执行台账**

1. `AlertEvaluator` 周期评估 + 抑制状态（内存可；重启后以 metric 现状重建）。  
2. 每 alert 绑定 §2.2.3 runbook 字段。  
3. symptom-first：优先 page ready/dead/repair 症状，少堆「原因」类噪音告警。  
4. 率类阈值可用多窗思想（短窗+长窗）控 fatigue；绝对 dead>0 可硬告警。

**小结**：毒消息与半残进程必须吵；噪音可控。

---

### 4.5 `S15-E05` — Ready / Live 探针导出

**编号与说明**：分探针 HTTP、组件聚合、安全 JSON。

**真相层对应**：S15-T009/T019/T040..T043；T-O-305

| 探针 | 路径 | 语义 | HTTP | 允许探测 |
|---|---|---|---|---|
| Liveness | `GET /live`（兼容 `GET /healthz`） | 进程/事件循环存活 | 200=活 | **仅**进程内；**禁** DB/vector/object/registry/外部 HTTP |
| Readiness | `GET /ready` | 可接 **新** 业务流量 | 200=ready；**503**=not_ready | 聚合各域谓词 |

**组件 × 谓词权威**

| component | 谓词权威 | ready=false 示例 | 非重叠说明 |
|---|---|---|---|
| `schema_migration` | S12 | drift / 未应用 | DDL |
| `registry_bootstrap` | **S14 only** | prompt 指针/catalog 行/digest 冲突 | **不含** transport |
| `db_primary` | S12 | 主库不可用 | |
| `concurrent_writes` | S12 | 声明启用但不可用 | |
| `native_vector` | S12/S09 | vector/ANN 能力缺口 | |
| `object_root` | S13 | root 不可写 / identity 漂移 | |
| `inference_binding` | **S11 only** | required capability 无 enabled **或** local transport 不可探 | binding 存在+可探 |
| `obs_tables` | **S15** | 三表缺失 / migration 未含 | |
| `sec_token_loaded` | **S16 only** | ActiveTokenSet 空 | 不阻塞 /live |

**响应与副作用**

- JSON：`status`/`live`/`components[]`；禁 secret/token/绝对 path。  
- metric：`mkb_readiness{component="..."}`。  
- not ready → 拒绝新 Task Create / 新 claim：**S01/S03/S12 必须查 Ready 标志**（S15-T043）；HTTP 503。  
- empty ActiveTokenSet ⇒ `sec_token_loaded=0` ⇒ `/ready` **503**。  
- **禁止**：单一恒 ok `/health` 混充 ready（legacy N-05）。

**执行台账**

1. `HealthAggregator` 收集 Port 式 `probe()` 自各域（**单组件单权威**）。  
2. `/live` 单元测试断言 **零** DB 调用。  
3. readiness false 持续 ≥60s 触发 `ALERT_READINESS_FALSE`。  
4. 组件扩展须 reopen 本文闭集（本版已显式追加 `sec_token_loaded`）。

**小结**：编排器可安全探活/接流；无级联误杀。

---

### 4.6 `S15-E06` — Trace 传播与关联

**编号与说明**：root 不变量、列强制、采样默认。

**真相层对应**：S15-T004/T020/T044..T046；T-O-306/290

**规范**

| 规则 | 必须 |
|---|---|
| Root | Task Create 确定后 **永不替换**（S01-T013） |
| domain_events | `trace_uuid` NOT NULL；业务 `team_uuid` 强制 |
| 主体列 | 适用时写 task/execution/process uuid |
| diagnostic | 强烈推荐 trace；缺失可见 ratio metric |
| W3C | 可选映射；允许变 parent-id/sampled；**禁**改已持久化 root |
| OTLP traces | 默认 OFF 或 sample ≤1% |
| 恢复 | 内部 recovery **禁** 新 root 静默替换 |
| PII | trace 头/字段禁 PII |
| 禁止 | 用 log 字符串代替关联列 |

**执行台账**

1. `TraceContext` 中间件：入站提取/校验；出站可选 W3C。  
2. DomainEventWriter 校验失败 → `OBS_EVENT_PAYLOAD_INVALID` / append fail。  
3. Architecture 测试：restarter 路径无 `uuid4()` 覆盖 root。  
4. 时间线查询依赖 `ix_de_trace`（D04）。

**小结**：排障靠列关联；不靠 APM SaaS。

---

### 4.7 `S15-E07` — Data-repair 权限与 evidence

**编号与说明**：回答「谁能修数据」；钉死无外部写面。

**真相层对应**：S15-T008/T021/T047/T048；T-O-307/294

| 角色 | 允许 | 禁止 |
|---|---|---|
| S03 | 定义幂等 repair transition | 从 UI/log 合成 gate decision |
| S12 | lease 回收、outbox 重试/dead、物理 cleanup | ACK=业务成功 |
| S15 | `ops.repair_applied` evidence；metric/alert；只读查询 | 第二状态推进引擎；无审计改行 |
| 外部/上游 | polling 读状态；只读 ops 面 | 公开 repair 按钮改 CAS |
| 内部 hook | `repair_scan_once`（token+审计） | 公网暴露；任意 SQL 改 outcome |

**原则**：fail-closed；状态变更 = **CAS + 同 TX domain_events**；重复扫描 no-op。

**执行台账**

1. 不实现独立 Reconciler 微服务/产品面。  
2. repair 成功/失败路径写 metric + 可选 event。  
3. 可选 hook 服从 S16-T028/T048：localhost/内网 + Bearer token + security_audit + domain_event。  
4. 验收：从 log 字符串「猜状态」路径不存在。

**小结**：恢复是确定性补齐，不是运维改库艺术。

---

### 4.8 `S15-E08` — Operator 只读 Port

**编号与说明**：最小可运维只读面；禁 UI 中台。

**真相层对应**：S15-T022/T049..T051；T-O-308

| 能力 | 接口 | 约束 |
|---|---|---|
| 事件时间线 | `get_timeline_by_trace(team, trace, …)` | **team 必填**；bounded；脱敏 |
| 任务时间线 | `get_timeline_by_task(team, task, …)` | team+task 强制 |
| dead 列表 | `list_outbox_dead(team, filter, …)` | **team 必填**；无 secret |
| 安全审计查询 | `list_security_audit(…)` | token+内网；redacted；默认 team 围栏 |
| 健康 | `/live` `/ready` | E05 |
| 指标 | `/metrics` | E03；网络边界见 S16-T031 |
| CLI | `mkb-ops timeline --team … --trace …` | 同 Port；禁省略 team |

**鉴权**：内网 + 内部 token（S16-T017/T027）；`team_uuid` **仅过滤非凭证**。team 省略/错配 → `SEC_TEAM_SCOPE_VIOLATION`。  
**禁止**：匿名公网、跨 tenant 枚举、console 中台、只读变写、file-debug。

**执行台账**

1. 实现 Port + 可选 thin HTTP 适配。  
2. 默认 limit 50 / cap 200 + cursor。  
3. 集成测试：无 token → 401；**省略 team → deny**；跨 team 不泄漏。  
4. 不实现 smind-console 级 UI。

**小结**：可按 trace 排障；不建设平台。

---

### 4.9 `S15-E09` — Dead-letter / outbox-dead runbook

**编号与说明**：毒消息可见、可告警、可显式重放。

**真相层对应**：S15-T012/T023/T052..T054；T-O-309/298

**闭环**

```text
S12: attempts 耗尽 → status=dead
S15: list_outbox_dead 可查
S15: mkb_outbox_dead_* metric + ALERT_OUTBOX_DEAD (+ oldest age)
可选: outbox.dead / ops 事件（低频；bounded）
人工/内部: 修根因 → S12 OutboxPort.requeue_dead / reset_attempts（可审计；S12 必实现）
禁止: 自动循环 redrive 未清毒；silent drop；无审计 dead→done
```

**Runbook 步骤（运维）**

1. 确认 `ALERT_OUTBOX_DEAD` / metric。  
2. `list_outbox_dead` 取 kind/error_code/age。  
3. 关联 process/execution/task（业务表 + timeline）。  
4. 修根因（binding/数据/代码）。  
5. 经 S12 显式 redrive；确认 CAS/Outcome，**非** 仅 outbox done。  
6. ACK 历史 **从不** 定义业务成功。

**执行台账**

1. Dead 投影与 metric 挂钩 S12 表只读查询。  
2. Redrive **只**经 S12 Port；S15 写审计。  
3. 告警含 depth/age 信号。  
4. 禁止独立 DLQ 业务表作第二 SSOT。

**小结**：毒消息吵且可治；不造第二队列真相。

---

### 4.10 `S15-E10` — OBS 错误轴与 diagnostic 失败策略

**编号与说明**：typed 错误、事件 fail-closed、诊断 BE 可见。

**真相层对应**：S15-T024/T055；T-O-310/291/292

| code | 含义 | 业务影响 | HTTP 意图 |
|---|---|---|---|
| `OBS_EVENT_APPEND_FAIL` | domain_events 插入失败 | **整 TX 失败** | 5xx / 映射业务失败 |
| `OBS_EVENT_PAYLOAD_INVALID` | contracts 校验失败 | 整 TX 失败 | 4xx/5xx 按入口 |
| `OBS_DIAG_APPEND_FAIL` | diagnostic 写失败 | **不**回滚业务；drop metric+stderr | 通常不对外 |
| `OBS_METRIC_EXPORT_FAIL` | scrape/export 失败 | 不改业务 | ops |
| `OBS_RETENTION_JOB_FAIL` | 归档失败 | 不改 CAS；alert | ops |
| `OBS_CARDINALITY_DROP` | 样本丢弃 | 不改业务；metric | ops |
| `OBS_TIMELINE_QUERY_FAIL` | 只读 Port 失败 | 无副作用 | 5xx typed |
| `OBS_READY_COMPONENT_FAIL` | 组件探测失败 | readiness false | `/ready` 503 |

**对外映射（RFC 9457 风格）**

```text
{
  "type": "about:blank" | "https://mkb.local/errors/obs/...",
  "title": "...",
  "detail": "bounded safe message",
  "error_code": "OBS_*",
  "trace_uuid": "..."
}
```

禁 stack / 绝对 path / token / secret。

**执行台账**

1. 统一 `ObsError` 类型；与 S02 envelope 协作。  
2. DiagnosticSink：失败路径 **必须** 递增 drop metric + stderr。  
3. DomainEventWriter：**禁止** catch-and-continue 吞掉 append 失败。  
4. 单元测试覆盖 events fail-closed vs diag BE 分叉。

**小结**：该硬的硬、该软的软且可见。

---

### 4.11 `S15-E11` — 安全围栏与 v1 OOS 闭包

**编号与说明**：脱敏、team 过滤、OOS 清单可验收。

**真相层对应**：S15-T007/T014/T025/T057；T-O-311/293/300

**安全围栏**

| 规则 | 必须 |
|---|---|
| 禁入字段闭集 | **权威 = S16-T056**（// sync-from S16；含 Authorization 与 `X-MKB-Internal-Token` 头值等）；S15 **不得**平行维护可漂移表 |
| 允许 | fingerprint、handle、digest、枚举 code、有界 uuid 列（非 metric label） |
| team | 过滤/分区 ID **≠** 授权凭证 |
| security_audit | 分表；metric 全量 + audit 采样语义见 S16-T055；S16 写入 |
| 对外错误 | 服从 S02 安全 envelope |

**v1 OOS 闭包（明确不做）**

1. 完整 APM / 分布式追踪 SaaS 与 UI 瀑布图产品  
2. 公网 metrics/log marketplace 与多租户计费仪表盘  
3. 用 log/event **替换** 业务 CAS  
4. 平台 console 运营中台（file-debug/audit-log UI）  
5. **业务** webhook/callback 默认交付  
6. 独立通用 Reconciler 服务作状态 SSOT  
7. 业务库内 metrics 时序表  
8. Agent 运营控制台（G-12）  
9. Answer-generation 质量 APM 默认产品（G-07）  
10. Per-team 商业化差异 retention 套餐  
11. 无鉴权公网 timeline API  

**执行台账**

1. Schema 级拒绝 secret 字段进入 payload。  
2. Architecture 测试：无 console debug UI 依赖。  
3. OOS 列表写入验收「负向用例」清单。  
4. S16 交叉：消费 S16-v1.0 token/endpoint/audit/redaction SSOT。

**小结**：leaf-worker 可观测，不膨胀成安全/运营平台。

---

### 4.12 配置键台账（ops knobs · 不进 binding_digest）

| 键 | 默认 | 说明 | Truth |
|---|---|---|---|
| `obs.retention.domain_events_days` | 90 | events hot | T-O-302 |
| `obs.retention.diagnostic_logs_days` | 14 | diagnostic | T-O-302 |
| `obs.retention.security_audit_days` | 180 | audit hot 默认 | T-O-302 |
| `obs.retention.batch_size` | 1000 | DELETE 批 | T-O-302 |
| `obs.retention.job_interval_seconds` | 3600 | job 周期 | T-O-302 |
| `obs.backup.retain_copies` | 7 | S13 协作 | T-O-302 |
| `obs.backup.schedule_cron` | daily | 字面量可部署覆盖 | T-O-302 |
| `obs.metrics.enable` | true | scrape 面 | T-O-303 |
| `obs.metrics.scrape_path` | `/metrics` | 路径 | T-O-303 |
| `obs.metrics.export_team_label` | false | team 作 label 默认关 | T-O-303 |
| `obs.otlp.metrics_enabled` | false | 可选 | T-O-303 |
| `obs.otlp.traces_enabled` | false | 可选 | T-O-306 |
| `obs.otlp.traces_sample_ratio` | 0 或 ≤0.01 | 采样 | T-O-306 |
| `obs.alert.notify_enabled` | false | ops-only 通知 | T-O-304 |
| `obs.alert.readiness_false_seconds` | 60 | 阈值 | T-O-304 |
| `obs.alert.repair_fail_threshold` | 3/15m | 阈值 | T-O-304 |
| `obs.alert.diag_drop_rate` | 0.01/5m | 阈值 | T-O-304 |
| `obs.alert.security_deny_spike_per_min` | **100** | deny spike；**S15 拥有键**；消费 S16 metric（不读 `security.alert.*` 作阈值 SSOT） | T-O-304 |
| `obs.timeline.default_limit` | 50 | 分页 | T-O-308 |
| `obs.timeline.max_limit` | 200 | 硬 cap | T-O-308 |

> 上述键类为 **Ops-only**（S14-T030 对齐）；变更不改 binding_digest；敏感 notify URL 走 S16 secret 引用，不进 git。

---

### 4.13 错误族与邻域交接（速查）

| 场景 | 主导错误 | 邻域 |
|---|---|---|
| 事件 append 失败 | `OBS_EVENT_APPEND_FAIL` → TX abort | S12 UoW |
| 业务 CAS 冲突 | 业务码（非 OBS） | S03/S12 |
| admission deny | security_audit + S02 envelope | S16/S02 |
| readiness false | `PERSISTENCE_NOT_READY` / domain ready codes + OBS ready | S12/S13/… |
| outbox dead | 无业务成功；S15 alert | S12 |
| registry digest | `REGISTRY_*` | S14 |
| transport | S11 错误 | S11 |

---

## 5. 事实反例 + 风险台账

### 5.1 Legacy 反模式 → 禁令（必须删除/改写）

| ID | 反模式（legacy-family） | MKB 禁令 | Truth |
|---|---|---|---|
| N-01 | Log 写失败仅 console.error，业务无感 | domain_events 同 TX 失败则整 TX 失败；diag BE 须 metric | T-O-291/292 |
| N-02 | waitUntil 异步写 log 当唯一证据 | 业务变迁事件禁止纯 fire-and-forget 唯一证据 | T-O-291 |
| N-03 | smind_logs 无模块化 DDL 却被依赖 | 三表 required 进 migration + readiness | T-O-288 |
| N-04 | team 仅 payload_extra | `team_uuid` 一等列；业务强制 team | T-O-290 |
| N-05 | `/health` 恒 ok | 分 `/live` `/ready`；live 禁依赖 | T-O-305 |
| N-06 | Trace 恢复失败生成新 ID | root 禁止静默重生 | T-O-306 |
| N-07 | compensating restarter 当完整 reconciler | 无 Reconciler 产品；S03+S12+S15 | T-O-294/307 |
| N-08 | Console debug UI 运营面 | 无 console 中台；只读 Port | T-O-300/308 |
| N-09 | process 表与 logs 双轨当真相 | 状态在 processes；时间线 events；诊断 logs | T-O-289 |
| N-10 | purge 失败只靠 log | proof + event；非 log-only | T-O-289 |
| N-11 | queue ACK 当成功 / drop batch | outbox dead + 告警；ACK≠成功 | T-O-298/309 |
| N-12 | 多 Worker 复制 log.ts 漂移 | 统一 observability 端口 | T-O-287 |
| N-13 | payload 塞完整业务/callback/secret | bounded + 脱敏 | T-O-311 |
| N-14 | UI 打印内部 debug_context | 对外安全 envelope | T-O-311 |
| N-15 | 无 metric/alert 一等机制 | 目录+export+alert 闭集 | T-O-303/304 |

### 5.2 正向原型（升级吸收）

| ID | 原型 | 升级 |
|---|---|---|
| P-01 | 稳定 log_code + level + module | → diagnostic_logs 列 |
| P-02 | trace 进几乎所有日志 | → domain_events 强制 trace |
| P-03 | team 上下文 | → 一等列 |
| P-04/P-05 | 有界 message/stack | → D04 有界列 |
| P-06 | 按 trace 拉时间线 | → ObservabilityReadPort + ix_de_trace |
| P-08 | stuck 检测 log | → lease metric/alert + S12 scanner |
| P-10 | Zod 校验再写 | → contracts DomainEventPayload |

### 5.3 风险台账

| 风险 | 等级 | 缓解 |
|---|---|---|
| retention 过短丢排障窗口 | M | 90/180 默认；ops 可上调+审计 |
| retention 过长库膨胀 | M | job + batch + metric |
| 高基数 label 回归 | H | 白名单 + architecture test + drop metric |
| alert fatigue | M | 闭集 + 抑制 + symptom-first |
| live 探针查 DB 导致重启雪崩 | H | 硬禁 + 测试 |
| 只读面变写面 | H | Port 无写方法；审计 hook 分离 |
| 把 offline export 当第二 SSOT | M | 文档+验收禁恢复权威 |
| S16 交接漂移 | L | 已消费 S16-v1.0；目录同步 sec_* |
| security_audit 与 domain_events 混表 | H | 分表 + 代码路径测试 |
| dead 自动 redrive 循环 | H | 仅显式 S12 redrive |

### 5.4 硬禁令速记（验收）

1. **禁止** log/event 替代 CAS 成功（T-O-289）。  
2. **禁止** domain_events 与业务不同 TX（T-O-291）。  
3. **禁止** `/health` 恒 ok 混充 ready（T-O-305）。  
4. **禁止** 高基数 uuid label 默认导出（T-O-303）。  
5. **禁止** 外部 operator 写业务状态 / 独立 Reconciler 产品（T-O-307）。  
6. **禁止** console 运营中台与业务 webhook 默认（T-O-296/300/308）。  
7. **禁止** 业务库 metrics 时序表 SSOT（T-O-288/300）。  
8. **禁止** trace root 静默重生（T-O-306）。  
9. **禁止** 另起第二套可观测表名闭集（T-O-288）。  
10. **禁止** 无审计 dead→done / 自动循环 redrive（T-O-309）。

---

## 6. 测试与验收台账

> **纪律**：下列为 **HARD invariants + required evidence**；**不**伪造「已交付测试绿」。实现阶段须补齐自动化。

### 6.1 HARD invariants

| ID | 不变量 | 证据类型 | Truth |
|---|---|---|---|
| S15-A01 | 业务 TX 含 domain_events 插入失败 → 整 TX 回滚 | unit/integration | T-O-291 |
| S15-A02 | 业务成功行存在时必有对应 event（适用 TX-01..08） | integration | T-O-291/289 |
| S15-A03 | diagnostic 写失败不回滚业务且 drop metric>0 | unit | T-O-292 |
| S15-A04 | 业务事件缺 team 或 trace 被拒 | unit | T-O-290 |
| S15-A05 | retention job 删除仅发生在过期窗；未过期保留 | integration | T-O-302 |
| S15-A06 | Process cleanup 后 events 仍在（未过 retention） | integration | T-O-297 |
| S15-A07 | metric 注册含 task_uuid label → 拒绝/drop | unit | T-O-303 |
| S15-A08 | `/metrics` 返回 Prometheus text 且无 uuid label 泄漏 | integration | T-O-303 |
| S15-A09 | `/live` 路径零 DB 调用 | unit | T-O-305 |
| S15-A10 | obs_tables 缺失 → `/ready` 503 | integration | T-O-305 |
| S15-A11 | readiness false 持续触发 alert 信号 | integration | T-O-304 |
| S15-A12 | 已持久化 trace 在 recovery 路径不被替换 | unit | T-O-306 |
| S15-A13 | 无外部 HTTP 可写 process CAS 的 repair API | architecture | T-O-307 |
| S15-A14 | timeline 无 token → 拒绝 | integration | T-O-308 |
| S15-A15 | dead 行可 list 且 metric 可见 | integration | T-O-309 |
| S15-A16 | redrive 仅经 S12 Port 审计路径 | architecture | T-O-309 |
| S15-A17 | payload 含 secret 字段 schema 拒绝 | unit | T-O-311 |
| S15-A18 | security_audit 与 domain_events 无混写路径 | architecture | T-O-293 |
| S15-A19 | 无业务库 metrics 时序表 migration | architecture | T-O-288 |
| S15-A20 | 实现模块可在不打开 QNA 条件下对照本文编码 | review | SSOT |

### 6.2 负向验收（OOS / 禁令）

| ID | 断言 |
|---|---|
| S15-N01 | 仓库无 smind-console 级 file-debug 产品依赖作为 MKB v1 交付 |
| S15-N02 | 无「业务完成 webhook」默认配置键与 Task 共用 |
| S15-N03 | 无 Reconciler 微服务进程作为状态 SSOT |
| S15-N04 | 无 per-team retention 套餐产品 API |

### 6.3 证据清单（交付时）

- contracts 校验样例（合法/非法 payload）。  
- TX 回滚与 BE 分叉测试日志。  
- `/live` `/ready` `/metrics` 响应样例（脱敏）。  
- alert 触发/抑制样例。  
- retention dry-run 统计。  
- architecture 测试列表勾选 A01–A20。

---

## 7. Reference-anchor 台账

### 7.1 legacy-family 锚点

| 锚点路径（相对 `context/legacy-family/`） | 用途 | 处置 |
|---|---|---|
| `*/core/log.ts`（dispatcher/admin/skills/contexter/vectorizer） | 结构化 log 原型 + 静默失败反例 | **rewrite** → unified Port |
| `smind-rag-dispatcher/core/db.ts` `createLog` / waitUntil | 异步写 log 反例 | **delete** 作为业务证据路径 |
| `smind-rag-dispatcher/flows/processor.ts` | trace 贯穿 | **retain** 思想 |
| `smind-rag-dispatcher/services/restarter.ts` | stuck 检测 / 新 trace 反例 | **rewrite** 分账 S12+S15 |
| `smind-skill-rag-vectorizer/src/index.ts` `/health` | 恒 ok 反例 | **delete** |
| `smind-skill-rag-vectorizer/src/purger_logic.ts` | purge 仅 log | **rewrite** proof+event |
| `smind-console/functions/api/files/debug/*` | UI 运营中台反例 | **delete** 产品面 |
| `smind-rag-dispatcher/src/index.ts` queue handler | ACK/成功耦合风险 | **rewrite** outbox |
| `smind-console/db/*.sql` 无 logs DDL | 文档真空反例 | **rewrite** D04 三表 required |

### 7.2 Web Reference-Check（design contrast only · 访问日 2026-08-12）

> **不**覆盖 Owner/D\*/S\* freeze。完整 URL 表见 `qna-truth/S15.md` §7 XR-01..33。

| 主题 | 对照结论 | 代表 XR |
|---|---|---|
| 分层 retention / audit 更长 | 支持 14/90/180 默认 | XR-01..04 |
| Prometheus 禁高基数 label | 支持 uuid 禁 label | XR-07/08/11 |
| Golden Signals / RED/USE | 支持目录族划分 | XR-09 |
| Prom 主 + OTel 可选 | 支持双路径非互斥 | XR-10 |
| symptom-first 告警 | 支持闭集+抑制 | XR-09/12/13 |
| K8s live/ready 分账 | 支持 live 禁依赖 | XR-15/16 |
| W3C root 稳定 / 采样 | 支持不强制 APM | XR-18..20 |
| Outbox / dual-write | 支持同 TX 事件 | XR-23/24 |
| DLQ depth/age + 显式 redrive | 支持 dead runbook | XR-27/28 |
| RFC 9457 | 支持 OBS 对外映射 | XR-29 |
| OWASP logging/A09 | 支持脱敏+append-only | XR-30..32 |

**明确拒绝外链方向**（与 §5.4 一致）：永久热保留全部、强制 OTLP-only collector、完整 multi-burn 值班 SaaS 产品面、live/ready 混 endpoint、默认全采样 span 树、通用 Reconciler 微服务、公网 marketplace、事件 best-effort。

---

## 8. Domain verdict

### 8.1 GO / ACCEPTED 判定

| 条件 | 状态 |
|---|---|
| fence `T-O-287..301` 映射完整 | **pass** |
| execution `T-O-302..311` 映射完整 + E02..E11 可编码 | **pass** |
| 与 D04 三表/同 TX 无冲突（不改表名） | **pass** |
| 与 S03 repair / S12 outbox·ready / S13 backup / S14 hooks 分账清晰 | **pass** |
| 关键不变量可测试（§6） | **pass**（实现待补） |
| QNA 非执行 SSOT 声明 | **pass** |
| second-opinion | **waived**（workflow-frozen） |

**域裁决**：**`accepted / GO`（S15-v1.1）** — 本文件为 S15 **唯一执行 SSOT**。

### 8.2 Residual OOS / defer

| 项 | 处置 |
|---|---|
| S16 token 轮换/存放/Bearer 矩阵 | **消费 S16-v1.0/v1.1** T-O-327..329 / E03–E05 |
| security_audit 写失败/采样/action 闭集 | **消费 S16-T052..T055 / E12** |
| redaction 字段闭集 | **消费 S16-T056**；S15 不平行改 |
| 告警多窗 burn 精确数字微调 | ops knob；闭集冻结 |
| GPU 设备路径枚举 | 部署有界或省略 series |
| OTLP collector 拓扑 | OOS 强制；可选开启 |
| legal-hold / 合规导出产品 | **OOS**；pre-delete export 失败挡 DELETE |
| 完整 APM/UI/marketplace/Reconciler | **OOS** |
| Per-team retention 套餐 | **OOS** |
| Progressive Round 3+ / second-opinion | **waived** |

### 8.3 下游约束

| 下游 | 必须服从 |
|---|---|
| 实现 / architecture tests | 仅本文 + D04 表物理；禁引用 QNA 当 SSOT |
| S16 | 已 accepted：token/audit 写/sec metric/`sec_token_loaded`；S15 聚合 export；不 reopen retention 所有权 |
| 拓扑 `17` / 验收 `18` | 纳入 `/live` `/ready` `/metrics` 与 HARD A01–A20 |
| S03/S12 | cleanup 不级联 Event/Log；dead 可观测；repair 无外部写面；**OutboxPort.requeue_dead** |
| S01 | Create 入口 fail-closed 查 Ready（S15-T043） |
| S13 | 仅被 S15 BackupScheduler 调起 backup 协议 |
| S14 | 钩子映射进 S15-E03；未收录禁 export |
| 各业务域 | 状态变迁写 domain_events 经 DomainEventWriter；不得 BE 冒充 |

### 8.4 与 S14/S16 正式邻域合同（accepted）

- **S14-v1.1**：`obs.*` Ops-only（S14-T030 分类）；registry/config 钩子映射进 S15-E03；事件 type 经本文+D04 登记表。  
- **S16-v1.0**：token/endpoint/audit/redaction/sec metrics/`sec_token_loaded` 全量消费；阈值 `obs.alert.security_deny_spike_per_min` 归 S15；metric 权威计数。  
- 形状级冲突 → 显式 change-request 双向校准（D* > S*）。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 说明 |
|---|---|---|---|---|
| `S15-v1.1` | `2026-08-12` | `MKB owner + Grok workflow domain-truth-s14-s16` | **`accepted`** | 对抗评审：`sec_token_loaded`；sec/S14 metrics 目录；team 必填 operator 面；event_type 登记；S16 正式合同；security alerts；BackupScheduler；redaction sync-from S16 |
| `S15-v1.0` | `2026-08-12` | `MKB owner + Grok workflow domain-truth-s14-s16` | **`accepted`** | 自 `qna-truth/S15.md v1.0-qna-locked`（`T-O-287..311`，Q1–Q10 全 B + RC Δ1–Δ8）升格唯一执行 SSOT；九段式 + E01–E11；S15-T001..T060；retention/metric/alert/ready-live/trace/repair/operator/dlq/OBS/OOS 闭包；second-opinion waived |

---

## 附录 · NS2 窄回填：`process.dispatch_admitted`

`ALLOWED_TYPES` 登记 `process.dispatch_admitted`。payload 只含 `pool` / `priority` / `channel_source`，禁止 prompt / 正文 / token。显式通道覆盖另走 `mkb_security_audit_events`（`config.compression_channel_override`）。

---

## 附录 A · Domain-local ↔ Global Truth 速查

| S15-T | T-O | 主题 |
|---|---|---|
| T001..T015 | 287..301 | fence |
| T016 | 302 | retention |
| T017 | 303 | metrics |
| T018 | 304 | alerts |
| T019 | 305 | ready/live |
| T020 | 306 | trace |
| T021 | 307 | repair |
| T022 | 308 | operator |
| T023 | 309 | dead-letter |
| T024 | 310 | OBS errors |
| T025 | 311 | security/OOS |
| T026..T060 | 派生 | 可编码细则 |

**全局下一可用 Truth-ID**：`T-O-337`（S15 占 `287..311`；S16 占 `312..336`；本战役审计 **不** 新分配全局 T-O）。

---

## 附录 B · 实现禁令海报（可贴 PR 模板）

```text
[ ] domain_events same TX as business mutation
[ ] no log-as-SSOT / no event-as-CAS
[ ] /live no DB; /ready aggregates; 503 blocks new traffic
[ ] no uuid labels on metrics
[ ] no external repair write API
[ ] no console ops UI / no business webhook default
[ ] no metrics timeseries tables in primary DB
[ ] no silent trace root regen
[ ] no second observability table set
[ ] dead redrive only via S12 + audit
```
