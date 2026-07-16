# S02 — Task API & Aggregate Lifecycle

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D2 任务执行 / S02 Task API & Aggregate Lifecycle`
>
> **日期**：`2026-07-16`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted`（S02 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S02-v1.2`
>
> **上游权威输入**：QNA初始基线`D01-v1.0 / S01-v1.1`、冻结的`qna-truth/S02.md v1.3`；正式回流版本`D01-v1.3 / S01-v1.4 / S03-v1.2 / S04-v1.1 / S05-v1.0`
>
> **事实证据**：`legacy-family/` 中 API 发起、Dedicated API scatter、SMCP、Clean/RAG Dispatcher、Console 原子查询与重启实现
>
> **下游消费者**：`S03-S05`、`S08-S10`、`S12`、`S15-S16`、跨系统拓扑 `17`

> **Owner-originated 约束**：Task、Execution、Process 的三层切分来自 owner 主动提出的 D01。S02 不重新设计这三层身份，只完成 Task 的外部 API、聚合生命周期、scatter 投影、人工重启因果与治理查询。

> **校准声明**：D01/S01 冻结的 `tasks + task_audits + executions + processes` 四张核心 Task/运行真相表继续成立。S02 依据 owner 在 Q5/Q6 的补充裁决，新增独立 `task_restarts` 因果账本；因此启用外部人工重启后的最小 durable 业务真相集合为五张。`task_restarts` 不复制或推进 Task status。

> **S04校准声明**：S02原先使用的`Source/Document/DocumentVersion/manifest`是S04冻结前的资源占位词。本版将MKB公共契约校准为`IntakeSource/IntakeSnapshot/IntakeItem/IntakeRevision/IntakeSnapshotMembership/IntakeChangeSet`；`document.*` intents和`document_uuid`不作为兼容别名保留。

> **S05校准声明**：S05-v1.0不增加Task状态。Execution因human gate进入`waiting`时，Task继续投影为`running`并提供bounded`action_required`；gate read/decision以Task-scoped受控subresource表达，不暴露或允许直接修改Execution/Process。Required gate rejection按既有single/scatter all-required规则归约，不增加`reviewing/partially_succeeded`状态。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S02 把外部一次请求稳定地表达为可创建、查询、修改有限描述字段、取消、重试、软删除和追溯的 Task。它向上游提供长期 ACK 与 polling 账本，向下游发送控制意图并消费 Execution 的 durable aggregate；它不是 LS-RAG 工序引擎。

S02 解决四个核心问题：

1. 一个 Task 在并发、崩溃、重放和人工命令下只有一个可解释的聚合状态；
2. API scatter 不再依赖后加补丁，而从第一天拥有 expected set、collect-all、分页原子结果和 durable fan-in 语义；
3. full Task retry与atomic IntakeItem rebuild使用不同身份规则，但进入同一可审计因果账本；
4. Task soft-delete、Process 清理和日志 retention 不会切断历史、重启或结果追溯。

### 1.2 Scope fence

S02 负责：

- Task create/get/list/patch/soft-delete；
- Task result、generation history 与 Task-scoped scatter items 的 polling read model；
- 六态 Task aggregate state machine；
- cancel 与 full retry command 的 admission、CAS、幂等和响应语义；
- atomic IntakeItem rebuild的Task/因果接入要求；
- scatter collect-all、child early publication 和 cancel forward-stop 的 Task 级语义；
- `task_restarts` 的因果/admission 真相、全局 restart list 与 causal lineage query；
- priority、deadline、revision、cursor、filter 和稳定错误码；
- Task 可见性与软删除围栏。

S02 不负责：

| 排除项 | 权威归属 | S02 边界 |
|---|---|---|
| Execution tree、Process registry、workflow phase、lease/fencing、自动 retry | `D01/S03` | 只发 command、消费 aggregate/proof |
| IntakeSource/Snapshot/Item/Revision/Membership/ChangeSet exact schema | `S04-S05` | 只定义Task-scoped投影与canonical Intake link |
| 向量与 filter metadata publication proof 算法 | `S08-S09/S12` | proof 是成功 guard，不在 S02 计算 |
| IntakeArtifact/derived asset locator/backend | `S13` | 只返回受控logical reference |
| queue/outbox/reconciler 的具体实现 | `S03/S12` | 要求 durable state-before-wakeup 和可重建 |
| 日志、trace、event envelope 与具体 retention 时长 | `S15` | 规定不得以其替代 Task/restart truth |
| token 保存、轮换、网络暴露与限流 | `S16` | 继承简单内部 token 与 team-scoped query |
| webhook/callback | — | v1 禁止，首版只 polling |

### 1.3 身份与状态所有权

```text
外部 caller
  └── (team_uuid, task_uuid)         Task：ACK / CRUD / command / aggregate
        ├── immutable Task Audit     上游发起时审查快照
        ├── current generation       当前执行代次
        ├── Task-scoped items        scatter 执行结果投影
        └── task_restarts            人工重启的因果/admission 账本

MKB 内部
  └── root/child execution_uuid      durable workflow run
        └── process_uuid             RAG-specific 工序实例

长期知识资源
  └── IntakeSource/Snapshot/Item/Revision UUID   S04 canonical asset truth
```

普通调用者永远不需要以 `execution_uuid` 或 `process_uuid` 才能知道 Task 的状态、结果、原子 child 或重启因果，也不能用这两个内部 UUID 发命令。

### 1.4 完成定义

S02 在实现层完成必须同时满足：

1. §2 的所有 Truth ID 被 contract、数据库约束和状态 transition service 实现；
2. Task/Audit 创建、full retry、atomic rebuild admission 和 scheduling intent 通过事务故障注入；
3. single/scatter、collect-all、cancel/success race、generation retry 和 early publication 通过集成测试；
4. Get Task、items、result、generations、restart list 与 lineage 在 Process 清理后仍可正确返回；
5. 所有 team-scoped route、复合身份、cursor 和幂等路径通过隔离/重放测试；
6. Task status、restart causation、Intake truth和Execution/Process truth没有双写所有权；
7. §6 的强制验收项全部通过。

---

## 2. 真相层

### 2.1 真相层纪律

本节是 S02 的 SSOT。来源分为：

- `OWNER`：owner 明确提出或确认；
- `OWNER-QNA`：冻结的 S02 Q1–Q9；
- `UPSTREAM`：D01/S01 已接受真相；
- `LEGACY-FACT`：生产实现证明的问题或行为；
- `ACCEPTED-VERDICT`：在上述输入上形成的 S02 正式裁决。

Legacy 只能证明真实需求、失败模式和已有围栏，不能把 Cloudflare Worker、D1、R2、SMCP callback、Dispatcher RPC 或旧 files/job/process 表带入 MKB。

### 2.2 Task 边界与契约真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S02-T001` | Task 是外部 ACK/CRUD/command/aggregate 账本；Execution 是内部 durable run；Process 是 RAG-specific 工序实例。 | `OWNER + D01` | S02 不吸收 workflow phase，S03 不创建外部 Task 替代物。 |
| `S02-T002` | Task 权威身份是 `(team_uuid, task_uuid)`；`task_uuid/trace_uuid` 由上游提供，MKB 内生领域 ID 使用 UUIDv7。 | `S01-T008-T014` | 路由、PK/FK、缓存、锁与日志都携带 team。 |
| `S02-T003` | canonical discriminator 是 `request_intent`；v1 不接受 core 字段 `task_type`。 | `S01-T023-T026` | request intent 不是 clean/RAG process type。 |
| `S02-T004` | Task Create 必须与独立 immutable Task Audit 1:1 原子提交；提交前不得产生可执行工作。 | `S01-T032-T038` | 失败不得留下 Task、Audit、Execution、Process 或 scheduling intent。 |
| `S02-T005` | 上游不能创建、PATCH 或 command Execution/Process；外部 PATCH 只允许 `title/description/payload_extra`，`priority` 仅 queued 可改。 | `S01-T028-T031/T045` | status/result/progress/retry counter 不是 PATCH 字段。 |
| `S02-T006` | v1 结果交付只使用 polling，不提供 webhook/callback。 | `S01-T005` | Task、result、items、generations 与 lineage 必须可稳定查询。 |
| `S02-T007` | `priority` 严格 enum 固定为 `low/normal/high/urgent`，默认 `normal`；`deadline_at` 是可选 create-time UTC 调度约束，创建后不可 PATCH。二者都不新增 Task status。 | `ACCEPTED-VERDICT` | S03 可映射内部 rank/调度策略，但不得改写外部值；到期执行/停止算法由 S03 冻结。 |

### 2.3 Task aggregate 状态机真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S02-T008` | Task v1 status 只有 `queued/running/cancelling/succeeded/failed/cancelled`。 | `T-O-1` | 禁止 `accepted/retrying/partially_succeeded/deleted` 和 RAG phase。 |
| `S02-T009` | 基础边只有 queued → running/cancelling、running → succeeded/failed/cancelling、cancelling → cancelled。 | `T-O-1` | 所有转移必须经统一 transition service 与 revision CAS。 |
| `S02-T010` | full retry 是唯一额外回边：只允许显式 command 使 failed/cancelled → queued；active states 拒绝，`succeeded` 必须创建新 rebuild Task。 | `T-O-8` | 普通状态归约不得走回边。 |
| `S02-T011` | `succeeded`必须消费current root的type-specific durable proof；LS-RAG build/rebuild proof必须绑定exact IntakeRevision并证明预期vector/filter metadata已发布校验。 | `D01/S01-T056 + S04-T015/T016` | queue empty、单callback、日志或latest Revision不能使Task成功。 |
| `S02-T012` | `failed` 只表示当前 generation 已耗尽内部自动恢复并按 aggregation policy 终结；临时 Process 失败不直接写 Task failed。 | `T-O-1` | 错误从 Process/Execution 自下而上归约。 |
| `S02-T013` | `cancelled` 只有在 cancel intent 已传播且所有 active descendants 已 fenced/terminal、无 late business commit 可能时成立。 | `T-O-1/T-O-10` | 接收 cancel 不等于 cancelled。 |
| `S02-T014` | cancel 与 success 并发以 Task lifecycle CAS 的 durable first-commit-wins 为唯一线性化点；失败竞争者不得反转赢家。 | `T-O-3` | HTTP 到达、callback 或进程内 flag 均无裁决权。 |
| `S02-T015` | Task status 表示 current generation；旧 generation 的 terminal status、proof、result/error summary 永久不可改写。 | `T-O-8` | 默认 Get Task 返回 current generation，并链接历史 generation。 |

### 2.4 Scatter 与原子 child 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S02-T016` | single 是一个 root Execution；scatter 是一个 root controller 加 0..N child Executions，仍只创建一个外部 Task。 | `D01/S01-T050` | 禁止 child Task 和 Task.current_process_uuid。 |
| `S02-T017` | scatter必须先原子提交accepted IntakeSnapshot/Membership/ChangeSet required set，再产生并行child scheduling intent。 | `LEGACY-FACT + D01 + S04-T024..T029` | 不能从临时Execution count猜fan-in分母。 |
| `S02-T018` | scatter 采用 collect-all：required child 终态失败不取消健康 siblings；仍有 active child 时 Task 保持 running；全部 required terminal 后任一 required failure 使 Task failed。 | `T-O-2` | 不提供 partial-success Task status。 |
| `S02-T019` | 公共读面固定为bounded Get Task + Task-scoped paginated items + canonical IntakeItem/Revision link。 | `T-O-5 + S04-CALIBRATION` | Get Task不内嵌无界child数组；Intake truth仍由S04持有。 |
| `S02-T020` | TaskItem是某IntakeItem/Revision在特定Task generation和IntakeSnapshot/ChangeSet下的结果投影，不是第二个Intake SSOT。 | `T-O-5 + S04-CALIBRATION` | items必须能由Membership/ChangeSet + durable Execution summary重建。 |
| `S02-T021` | child 一旦取得完整 publication proof 即可独立 ready、读取和检索，不等待 root terminal；parent failed 不回滚成功 child。 | `T-O-9` | Task status 与 ready child 可以同时呈现 mixed outcome。 |
| `S02-T022` | scatter cancel是forward-stop/no implicit rollback：停止未完成工作，保留已proof-valid child；撤销IntakeItem必须创建`intake.deactivate/delete` Task。 | `T-O-10 + S04-T021` | cancel不能偷偷purge Intake/Vector。 |
| `S02-T023` | counts至少区分`total/required/active/succeeded/failed/cancelled/skipped`，并与本generation的SnapshotMembership/ChangeSet对账。 | `T-O-2/T-O-5/T-O-10 + S04` | counts不是外部PATCH字段。 |

### 2.5 Retry、rebuild 与因果账本真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S02-T024` | atomic child外部人工重启必须为稳定`intake_item_uuid`创建新的`intake.rebuild` Task；可绑定expected`intake_revision_uuid`，但不创建新IntakeRevision。旧scatter Task/tree不复活、不改写。 | `T-O-6 + S04-T010/T033` | 新Task有新ACK、Audit、root Execution、status与result。 |
| `S02-T025` | full Task retry 保持原 Task identity，但增加 `current_generation`、创建新 root tree；旧 tree terminal immutable。 | `T-O-8` | 默认读 current，history 按 generation 可查。 |
| `S02-T026` | `task_restarts`是所有外部人工重启的durable causation/admission SSOT，scope固定为`atomic_intake_item/full_task`。 | `T-O-7/T-O-8 + S04-CALIBRATION` | 自动Process retry、queue redelivery、lease recovery不写该表。 |
| `S02-T027` | `task_restarts` 不保存可独立推进的 Task status；restart 当前状态必须 LEFT JOIN 目标 Task 获取。 | `T-O-7/T-O-11` | 禁止 restart/status 双真相。 |
| `S02-T028` | atomic rebuild accepted 时，restart row、新 Task、Task Audit 与 durable scheduling intent 同事务提交；任一失败全部回滚。 | `T-O-7` | 未认证或 strict schema 无效请求不写业务真相。 |
| `S02-T029` | full retry accepted 时，restart row、generation/CAS、current root scheduling intent 和 Task `→queued` 必须处于同一原子或由 S12 证明等价的提交边界。 | `T-O-8 + ACCEPTED-VERDICT` | queue wake-up 只能发生在提交后。 |
| `S02-T030` | admission-valid 但被业务规则拒绝的 restart 可保存 immutable rejected row，不创建新 Task/Execution；拒绝码必须稳定。 | `T-O-7` | 安全认证失败和 schema parse 失败只进入安全/拒绝事件面。 |
| `S02-T031` | atomic rebuild 重放由目标 `(team_uuid, task_uuid)` + creation fingerprint 收敛；full retry 重放由 source task/generation + command fingerprint 收敛。 | `T-O-7/T-O-8` | 同身份不同 fingerprint 必须冲突，不得产生双 generation。 |

### 2.6 查询、删除与治理真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S02-T032` | 所有Task、items、restart和lineage查询强制team-scoped；不得按裸task/Intake UUID跨team查询。 | `S01 + T-O-11 + S04` | 即使token具全局能力，team_uuid仍是数据隔离键。 |
| `S02-T033` | list/items/restarts/lineage 使用 opaque stable cursor；排序包含唯一 tie-breaker，翻页不得依赖可变 offset。 | `T-O-5/T-O-11` | 精确编码由 OpenAPI/实现统一，不允许 route 各自发明。 |
| `S02-T034` | 提供team-scoped global restart list和causal lineage query；可从restart/task/IntakeItem入口追溯source Task/Item→restart→target Task→generation summaries。 | `T-O-11 + S04-CALIBRATION` | 普通返回只包含稳定Task/Intake identity与durable summary。 |
| `S02-T035` | Process cleanup、日志 retention 和 Task soft-delete 不得断开 Audit、restart causation、generation terminal summary 或 lineage。 | `T-O-7/T-O-11` | lineage 对软删除 Task 返回 tombstone identity 与最后 summary。 |
| `S02-T036` | Task delete只是受控soft-delete/可见性操作，不是执行状态，也不物理级联删除资源或证据。 | `S01 + T-O-11` | active Task必须先cancel/terminal；Task delete不等于IntakeItem delete。 |
| `S02-T037` | Task result endpoint 必须明确区分 `not_ready`、terminal failure/cancel 与 ready success；不能用 404 混淆未完成。 | `S01-E07 + ACCEPTED-VERDICT` | polling caller 不依赖日志解释结果。 |
| `S02-T038` | 外部错误使用稳定 machine code；内部 stack、绝对路径、token、Process payload 和驱动错误不得泄漏。 | `S01/S16 boundary` | 诊断详情进入受控内部 observability。 |
| `S02-T039` | Execution有open human gate时Task仍为`running`；aggregate另有bounded`action_required`投影，至少含gate count/kind、安全summary与Task-scoped links。 | `S05-T020..24 + S01-T059..60` | 不增加Task状态，不把durable waiting伪装为无进展。 |
| `S02-T040` | Gate read/decision是Task-scoped control subresource，不是Execution/Process public CRUD；普通Task响应不得泄漏内部execution/process/fence。 | `S01-T061 + S05-T021..24` | 服务端以exact ReviewTarget/generation/fence校验，caller只持安全gate ref/revision/target digest。 |
| `S02-T041` | Gate decision必须携带expected gate revision、target digest、action、idempotency与actor evidence；append decision、CAS gate/Execution和outbox成功后才返回committed result。 | `S05-T023..24` | stale/conflict返回409；HTTP接收、UI点击或queue send不能提前release。 |
| `S02-T042` | single required gate rejected最终使当前Execution/Task failed；scatter required child rejection参与collect-all，健康siblings继续，全部required terminal后root/Task failed。 | `S02-T018 + S05-T022..24` | 不增加partial-success terminal；已proof-valid sibling不回滚。 |

### 2.7 最小业务真相表结论

启用 S02 外部人工重启后，从 Task ingress 到 runtime/restart governance 的最小 durable 业务真相集合是：

```text
tasks
+ task_audits
+ task_restarts
+ executions
+ processes
= five business truth tables
```

- 四张原有核心表的职责和所有权不变；
- `task_restarts` 是第五张因果/admission 表，不是第四层执行身份；
- Task-scoped items是SnapshotMembership/ChangeSet + durable Execution summary的read model，不新增scatter patch表；
- generation 是 Task/Execution/restart lineage 的字段，不新增 `task_generations` 双真相表；
- S04十张Intake canonical tables与supporting ledgers、events/logs、outbox/queue、derived asset和Vector表归各自Domain，不计入上述五张runtime/restart最小集合。

---

## 3. 总体方案陈述

1. **以Task做唯一外部聚合根**：所有持久异步request intent都先创建Task + Audit；上游只操作Task或稳定IntakeItem，不操作运行内部身份。
2. **以六态状态机做 polling SSOT**：Task status 只描述 current generation 的等待、执行、取消收敛与终局，不复制 RAG 阶段。
3. **以 lifecycle CAS 统一线性化**：cancel、success、failure、full retry 和 soft-delete admission 共享 revision/guard；不存在 worker 直写终态的旁路。
4. **以 generation 保存 full retry 历史**：full retry 保持 Task ACK，创建新 root generation；旧 Execution tree 与 result/proof 保持 immutable。
5. **以新Task表达atomic rebuild**：单个IntakeItem重建是新的外部工作请求，拥有自己的Task/Audit；来源scatter只作为immutable cause，rebuild不创建IntakeRevision。
6. **以 `task_restarts` 统一人工重启因果**：full/atomic 两类 scope 共用 durable ledger，但运行状态只从 Task join。
7. **从第一天原生支持scatter**：accepted Snapshot/Membership/ChangeSet required set、durable scheduling intent、collect-all、counts、items、fan-in和recovery是主路径。
8. **以 child publication proof 做可见性围栏**：健康 child 可早发布；parent failed/cancelled 不自动回滚已验证知识。
9. **以forward-stop区分取消与删除**：cancel停止未来工作；`intake.deactivate/delete`才改变Intake lifecycle，两者各有Task/Audit/因果。
10. **以三段式读面控制边界**：Get Task有界、items可分页、IntakeItem/Revision长期canonical；内部诊断与业务API分层。
11. **以 durable summary 支撑治理**：Process 可在围栏后清理，但 Task polling、generation history、restart list 和 lineage 仍完整。
12. **以本地事务状态先于队列唤醒**：吸收 legacy 的可靠性经验，删除 `waitUntil`、callback 和跨 Worker RPC 成为真相的拓扑。

Task 状态图：

```text
queued ───────────────→ running ───────────────→ succeeded
  │                       │  └─────────────────→ failed
  └────→ cancelling ←─────┘
              │
              └───────────────────────────────→ cancelled

failed ──────── full retry command/CAS ───────→ queued
cancelled ───── full retry command/CAS ───────→ queued

succeeded ───── no retry back-edge；new rebuild Task only
```

---

## 4. 具体执行方案清单

### 4.1 `S02-E01` — 冻结 Task HTTP surface 与公共 envelope

**说明**：URI 以 team + Task 复合身份为主轴；command 使用显式 action，不伪装成 PATCH。

**真相层对应编号**：`S02-T001`–`S02-T007`、`S02-T019`、`S02-T032`–`S02-T038`

**执行台账**：

| Method / Route | 语义 | 成功响应 |
|---|---|---|
| `POST /v1/teams/{team_uuid}/tasks` | 原子创建Task + Audit；atomic rebuild causation随严格`intake.rebuild` payload进入 | `201`；同fingerprint重放`200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}` | 读取 bounded current aggregate | `200` |
| `GET /v1/teams/{team_uuid}/tasks` | team-scoped cursor list | `200` |
| `PATCH /v1/teams/{team_uuid}/tasks/{task_uuid}` | 白名单字段 + `expected_revision` | `200` |
| `DELETE /v1/teams/{team_uuid}/tasks/{task_uuid}` | terminal Task soft-delete + CAS | `200` tombstone summary |
| `POST /v1/teams/{team_uuid}/tasks/{task_uuid}:cancel` | 接受 cancel intent | `202` cancelling；已终局 `200` no-op/current truth |
| `POST /v1/teams/{team_uuid}/tasks/{task_uuid}:retry` | full Task retry，产生新 generation | `202` queued current generation |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/result` | polling result readiness | `202` not_ready；终态 `200` |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/items` | 当前或指定 generation 的 scatter item projection | `200` cursor page |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/generations` | durable generation summaries | `200` cursor page |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/gates` | 当前/历史gate的bounded cursor projection；默认open | `200` cursor page |
| `GET /v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate_uuid}` | 安全ReviewTarget、evidence/artifact摘要与allowed actions | `200`；stale/terminal仍返回当前truth |
| `POST /v1/teams/{team_uuid}/tasks/{task_uuid}/gates/{gate_uuid}:decide` | exact revision/target digest的approve/reject/reclean decision | `200` committed/idempotent；`409` stale/conflict |
| `GET /v1/teams/{team_uuid}/task-restarts` | global restart list/filter | `200` cursor page |
| `GET /v1/teams/{team_uuid}/task-restarts/{restart_uuid}` | 单条 restart + joined Task summary | `200` |
| `GET /v1/teams/{team_uuid}/task-lineage` | 以一个restart/task/intake-item seed查询因果图 | `200` bounded/cursor page |

Get Task 最小稳定响应族：

| 列族 | 内容 |
|---|---|
| Identity | `team_uuid/task_uuid/trace_uuid/schema_version/request_intent` |
| Description | `title/description/payload_extra/priority/deadline_at` |
| Lifecycle | `status/revision/current_generation/received_at/started_at/completed_at/deleted_at` |
| Aggregate | progress summary、scatter counts、IntakeSnapshot/ChangeSet ref、result/error summary；open gate时`action_required` bounded summary |
| Links | self、result、items、generations、restart lineage、conditional gates；适用时canonical IntakeSource/Item/Revision |

Task list 至少支持 `status/request_intent/priority/created_at range/updated_at range/include_deleted` 过滤，默认按 `created_at desc, task_uuid desc` 或等价唯一顺序。`priority` 只接受 `low/normal/high/urgent`，省略为 `normal`；`deadline_at` 若提供必须为严格 RFC 3339 UTC 时间且晚于接收时刻。

普通响应和gate surface不得返回root/child`execution_uuid`、`process_uuid`、fencing/lease token、内部stage、secret或绝对storage path。Gate以opaque `gate_uuid`、revision、target digest及安全evidence projection工作；服务端内部再校验exact Execution/ReviewTarget。内部运维诊断可在独立受控surface使用内部身份，但不属于S02 public contract。

**小结**：公共API围绕Task、canonical Intake identity与Restart组织，不围绕内部worker/step组织。

### 4.2 `S02-E02` — 实施 Task projection 与 lifecycle CAS

**说明**：所有 Task lifecycle 写入走同一个 application transition service。

**真相层对应编号**：`S02-T008`–`S02-T015`

**执行台账**：

| Transition | 必要 guard | 同事务 effect |
|---|---|---|
| create → `queued` | team active；identity/fingerprint admissible；Audit valid | Task/Audit/scheduling intent commit，revision 初始化 |
| `queued→running` | current generation root 已 durable/claimable；无 cancel intent | started_at、revision、aggregate summary |
| queued/running → cancelling | cancel command expected_revision 命中；尚未 terminal | durable cancel intent、revision；发 stop scheduling intent |
| `running→succeeded` | 无 cancel intent；root required set 与 type-specific proof valid | terminal result/proof summary、completed_at、revision |
| `running→failed` | current generation 已终结；无 active internal recovery；aggregation guard valid | terminal error/count summary、completed_at、revision |
| `cancelling→cancelled` | all active descendants fenced/terminal；late commit 不可能 | terminal cancel/count summary、completed_at、revision |
| failed/cancelled → queued | full retry command；expected_revision；admission valid | new generation + restart truth + scheduling intent + revision |

CAS 失败必须返回 current safe summary 和 current revision。Transition service 必须同时验证 `from status + expected_revision + current_generation + cancel/retry guard`，不能先读后无条件写。

**小结**：六态不靠约定维护，而由一个可线性化、可重放、可对账的写路径维护。

### 4.3 `S02-E03` — 实施 bounded Task、result 与 soft-delete 语义

**说明**：Task 主资源保持有界；结果 readiness 和删除可见性不能污染执行 status。

**真相层对应编号**：`S02-T015`、`S02-T035`–`S02-T038`

**执行台账**：

- Get Task 默认返回 current generation；历史通过 generations link 获取；
- `queued/running/cancelling` 的 result 返回 HTTP `202` 与 `readiness=not_ready`，同时携带可安全轮询的 Task summary；
- `succeeded` 返回 `readiness=ready`、canonical result/proof/artifact refs；
- `failed/cancelled` 返回 HTTP `200` 的 terminal envelope，分别使用 `terminal_failed/terminal_cancelled`，不得伪造 success result；
- DELETE 只接受 terminal Task 和 expected revision；active Task 返回 `409 task-active` 并要求先 cancel；
- soft-deleted Task 从默认 list 隐藏；精确 Get 返回 `410 task-deleted` 的安全 tombstone；lineage/restart query 仍返回 identity、last terminal summary 与 deleted_at；
- soft-delete不删除Audit、restart row、Execution terminal summary、IntakeItem/Revision或向量资产。

**小结**：执行终局、结果 readiness 和资源可见性是三个正交事实。

### 4.4 `S02-E04` — 实施 scatter Task-scoped items 与 collect-all aggregate

**说明**：scatter child必须可原子检索，但Task不复制IntakeItem/Revision truth。

**真相层对应编号**：`S02-T016`–`S02-T023`

**执行台账**：

1. accepted IntakeSnapshot/ChangeSet冻结`(team_uuid, task_uuid, generation, intake_snapshot_uuid, change_set_digest)`的membership与required/skipped决策；
2. items cursor必须绑定上述snapshot与稳定排序键；generation/ChangeSet变化不得让同一cursor漂移；
3. item至少返回`intake_item_uuid`、`intake_revision_uuid?`、安全的ExternalKey projection、`required`、`outcome=active|succeeded|failed|cancelled|skipped`、`publication_ready`、result/error summary和canonical links；
4. `publication_ready=true` 只由完整 child proof 产生，可在 parent running/failed/cancelled 时保持；
5. aggregate counts由SnapshotMembership/ChangeSet + durable child summaries计算/缓存，可重建；不允许外部PATCH；
6. 只要 required child 仍 active，且 cancel 未赢，Task 保持 running；全部 required terminal 后：全成功才 succeeded，任一 failed/非取消型缺失则 failed；cancel 赢则等 fencing 后 cancelled；
7. projection 漂移由 reconciler 重建并写事件，不能通过插入 patch child 或手工改 count 修复。

**小结**：Task aggregate解释“这一批请求怎样了”，IntakeItem/Revision解释“摄入业务项及其当前语义事实是什么”；是否成为Knowledge不属于S02/S04 v1。

### 4.5 `S02-E05` — 实施 cancel 的 forward-stop/no-rollback

**说明**：cancel 只停止未来执行，不隐式删除已发布知识。

**真相层对应编号**：`S02-T013`–`S02-T014`、`S02-T021`–`S02-T022`

**执行台账**：

```text
cancel request + expected_revision
  → lifecycle CAS wins
  → Task=cancelling + durable cancel intent
  → stop new fan-out/claim
  → propagate to root/children/processes
  → fence late commits
  → wait until all active descendants terminal/fenced
  → Task=cancelled
```

- success 先提交：cancel 返回当前 `succeeded`，不回滚；
- cancel 先提交：后到 success commit 被 CAS/guard 拒绝；
- queued cancel 也先进入 cancelling，再确认没有 claim 后 cancelled；
- 已 proof-valid child 保持 ready；未开始 child 可记 `skipped`，active child 收敛为 cancelled/failed；
- 撤销ready child必须另建`intake.deactivate`或`intake.delete` Task。

**小结**：运行控制与知识生命周期不共享一个危险的“取消即删除”按钮。

### 4.6 `S02-E06` — 实施 full Task retry generation

**说明**：整批重跑保留原 Task ACK，通过新 generation 保留不可变历史。

**真相层对应编号**：`S02-T010`、`S02-T015`、`S02-T025`–`S02-T031`

**执行台账**：

1. request 必须包含 `expected_revision`、reason，并形成确定性 command fingerprint；
2. 仅 failed/cancelled 可接受；queued/running/cancelling 返回 `409 task-active`，succeeded 返回 `409 retry-not-allowed` 并指向新 rebuild Task 语义；
3. accepted transaction 创建 `task_restarts(scope=full_task)`，记录 source generation/root 与 target generation；Task `current_generation+1`、`status=queued`、清空 current result projection、切换/预留新 root scheduling intent、revision+1；
4. 旧 generation 的 root tree、proof、result/error、counts 与时间永久只读；
5. source/restart task UUID 相同，但 source/target generation 与 root Execution 不同；
6. 同 source generation + 相同 fingerprint 的网络重放返回同一 restart/generation；不同 fingerprint 或 revision 冲突不得创建第二棵 current root；
7. histories 默认按 generation 降序，单个 generation summary 可在 Process compaction 后读取。

**小结**：retry 复用的是外部 ACK，不复活旧执行事实。

### 4.7 `S02-E07` — 实施 atomic IntakeItem rebuild 与因果原子提交

**说明**：原子 child 重启是新外部请求，不是在旧 scatter tree 中做 stage/step recovery。

**真相层对应编号**：`S02-T024`、`S02-T026`–`S02-T031`

**执行台账**：

```text
POST new Task(request_intent=intake.rebuild)
  → validate active team/token/strict payload
  → validate intake_item_uuid + optional expected intake_revision_uuid + source task/item causation
  → resolve target Task creation fingerprint
  → begin transaction
      insert task_restarts(scope=atomic_intake_item, accepted)
      insert new Task queued
      insert immutable Task Audit
      insert durable scheduling intent
    commit
  → wake local queue/reconciler
```

- 新 Task 使用 caller-supplied 新 `task_uuid/trace_uuid`，MKB 不替 caller 生成 Task identity；
- 旧scatter Task、source child Execution、Snapshot/ChangeSet item与终态只读；
- 新Task自己创建root Execution/Processes；target IntakeItem/Revision保持不变，是否复用IntakeArtifact/派生generation由S03-S09决定；
- public payload 不接受 `stage/process_uuid/force-step`；内部 step recovery 不写 `task_restarts`；
- 因果链至少能从新Task反查source Task + IntakeItem/Revision，也能从source Task/IntakeItem枚举后续rebuild Tasks。

**小结**：atomic rebuild 的独立 Task/Audit 让每次人工动作都可单独轮询、授权、追责和重放。

### 4.8 `S02-E08` — 建立 `tasks` 与 `task_restarts` 语义 schema

**说明**：S02 冻结列族、不变量和索引语义；Turso/SQLite exact DDL 与 migration 由 S12 交付。

**真相层对应编号**：`S02-T002`、`S02-T008`–`S02-T015`、`S02-T023`–`S02-T035`

**执行台账**：

`tasks` 最小责任列族：

| 列族 | 最小字段语义 |
|---|---|
| Identity | `team_uuid/task_uuid/trace_uuid`，复合 PK；schema version、request intent、creation fingerprint |
| Immutable input | strict payload、Task Audit 复合引用、create-time deadline |
| Mutable description | title、description、payload_extra、priority |
| Lifecycle | status、revision、current_generation、current root internal pointer、cancel intent |
| Scatter projection | IntakeSnapshot/ChangeSet ref、total/required/active/succeeded/failed/cancelled/skipped counts |
| Durable summary | current progress、result/error/proof refs；generation history由 Execution/restart durable truth支持 |
| Time/visibility | received/started/completed/updated/deleted timestamps、deleted actor/reason |

`task_restarts` 最小责任列族：

| 列族 | 最小字段语义 |
|---|---|
| Identity | `restart_uuid` UUIDv7、`team_uuid`、restart scope = atomic_intake_item/full_task |
| Cause | `source_task_uuid`、source generation/root/child refs、`intake_item_uuid`/`intake_revision_uuid?`、causation trace |
| Target | `restart_task_uuid`；target generation/root ref；atomic 时为新 Task，full 时与 source Task 相同 |
| Admission | request/command fingerprint、reason、requested_at、accepted/rejected、稳定 decision/error code |
| Governance | created/decided timestamps、payload_extra；causal/admission fields 提交后 immutable |

最低约束/索引语义：

```text
PK (restart_uuid)
INDEX (team_uuid, source_task_uuid, requested_at, restart_uuid)
INDEX (team_uuid, restart_task_uuid, requested_at, restart_uuid)
INDEX (team_uuid, intake_item_uuid, requested_at, restart_uuid)
INDEX (team_uuid, restart_scope, admission_outcome, requested_at, restart_uuid)
INDEX (causation_trace_uuid)

atomic_intake_item accepted:
  UNIQUE (team_uuid, restart_task_uuid, restart_scope)

full_task accepted:
  UNIQUE (team_uuid, source_task_uuid, source_generation, restart_scope)
  UNIQUE (team_uuid, source_task_uuid, target_generation, restart_scope)
```

Rejected row 的 target Task/root 可以为空；accepted atomic row 必须能 FK/逻辑约束到新 Task，accepted full row 必须约束 source/restart Task 相同且 target generation = source generation + 1。状态只能从 Task join，不设 restart status writer。

**小结**：第五张表补的是“为什么发生这次人工重启”，不是再造一个执行状态机。

### 4.9 `S02-E09` — 实施 global restart list 与 causal lineage

**说明**：治理查询必须来自 durable relational truth，不是日志检索包装。

**真相层对应编号**：`S02-T027`、`S02-T032`–`S02-T035`

**执行台账**：

- restart list支持`restart_uuid/source_task_uuid/restart_task_uuid/intake_item_uuid/restart_scope/admission_outcome/current_task_status/time range`；
- `current_task_status/result/error` 从 LEFT JOIN Task 获得；软删除时返回 tombstone + last summary；rejected row 无 Task 时返回 admission result；
- lineage query必须且只能提供一个seed：`restart_uuid`、`task_uuid`或`intake_item_uuid`；
- 返回`nodes + directed edges`，至少覆盖source Task/IntakeItem→restart record→restart Task→generation summaries；
- 普通 node 不暴露 Execution/Process UUID；generation 只返回 stable number、status、counts、result/error/proof summary 和时间；
- cursor 固定 `requested_at/restart_uuid` 或等价唯一顺序；所有 join 都带 team_uuid；
- Process compaction 后由 Execution terminal summary支撑 generation node，不能退化为“详情已删除”。

**小结**：全局审计链可拉取、可分页、可对账，同时不把内部执行控制面暴露给上游。

### 4.10 `S02-E10` — 冻结错误、幂等与并发响应

**说明**：错误码必须让 caller 能区分身份冲突、状态冲突、重放和暂未完成。

**真相层对应编号**：`S02-T002`–`S02-T005`、`S02-T010`、`S02-T014`、`S02-T028`–`S02-T038`

**执行台账**：

| HTTP | Machine code | 语义 |
|---:|---|---|
| `401` | `invalid-internal-token` | 未认证；不创建业务 truth |
| `404` | `team-not-registered` | Team 不存在；不创建 Task/Audit |
| `409` | `team-not-active` | Team inactive/deleted |
| `409` | `task-identity-conflict` | 同复合 Task identity，不同 creation fingerprint |
| `409` | `revision-conflict` | expected revision 不匹配，返回安全 current summary |
| `409` | `task-active` | active Task 不允许 retry/delete |
| `409` | `retry-not-allowed` | succeeded 或其他非允许来源状态发 full retry |
| `409` | `restart-causation-conflict` | source Task/IntakeItem/Revision/generation与事实不匹配 |
| `410` | `task-deleted` | 精确读取 soft-deleted Task 的 tombstone |
| `422` | `task-schema-invalid` | strict envelope/payload 无效 |
| `422` | `task-transition-invalid` | 合法身份上的非法 lifecycle command |
| `202` | `task-result-not-ready` | polling 正常未完成，不是错误/404 |

每个 error envelope 至少包含 `code/message/trace_uuid/request_id`；仅在安全时包含 team/task/revision summary。绝不返回 stack、SQL、绝对路径、token 或 Process input/output。

**小结**：caller 可以确定是重试同一请求、刷新 revision、等待、创建新 Task，还是修正输入。

### 4.11 `S02-E11` — 建立对账、观测与 retention 围栏

**说明**：Task 是投影 SSOT，但投影必须能从更细 durable truth 验证和恢复。

**真相层对应编号**：`S02-T011`–`S02-T015`、`S02-T017`–`S02-T023`、`S02-T029`、`S02-T035`

**执行台账**：

- recovery对账Task current generation/root、SnapshotMembership/ChangeSet、counts、terminal proof、restart target generation和scheduling intent；
- 任一 mismatch 先写 domain event/告警，再以受控 repair transition 重建 projection；不得 worker 直接 UPDATE Task；
- 指标至少覆盖各 Task status、status age、cancel convergence、scatter active/failed counts、generation retries、restart admission、projection mismatch 和 lineage query failure；
- Task/Audit/restart/generation terminal summary 的最低 retention 不短于其任何可查询因果链；确切时长由 S12/S15 冻结；
- Process只有在Execution summary已包含workflow/config/model、counts、retry、final error、Intake/derived asset/proof refs和时间后才能清理；
- queue wake-up 丢失、重复或延迟不得改变已提交工作事实，reconciler 必须可补发。

**小结**：运行可清理，但外部承诺、终局证据和因果链不可随短期控制行一起消失。

---

## 5. 事实反例 + 风险台账

### 5.1 Legacy 事实吸收台账

| Evidence | 已验证事实 | MKB verdict |
|---|---|---|
| Admin API ingestion | 单一 API 请求先注册父/root，再触发 clean | 保留单 Task/root 与提交后调度；删除平台 plan/R2/Worker |
| Dedicated API processor | array scatter、atomic key、content/meta双hash、并行candidate | 保留stable key/digest/schema原理；IntakeItem UUID在S04 acceptance transaction分配/复用 |
| SMCP reporter/schema | 完整child_files与结构化callback；另有first-child atomic_hint补丁 | 将集合证据升级为Snapshot/Membership/ChangeSet；删除首child hint与消息态真相 |
| Clean Dispatcher | 先建 process 再唤醒；diff/register 后并行 fan-out | 保留 durable state-before-wakeup；统一 Process 表和本地 queue adapter |
| RAG finalizer | child ready/rag_failed 独立更新，父状态不动 | 保留 child 独立结果；新增 expected-set collect-all fan-in |
| Console list/artifact/timeline | child可稳定寻址、独立查询 | 重建为TaskItems + canonical IntakeItem/Revision + 内部diagnostics |
| Console/Restarter | child可按stage/process恢复，带retry guard | public改为新`intake.rebuild` Task；内部recovery归S03 |

### 5.2 事实反例

| Counterexample ID | 错误做法 | S02 订正 |
|---|---|---|
| `S02-C01` | Task status 使用 clean/structurize/vectorize/retrying | 这些属于 Execution/Process；Task 只有六态。 |
| `S02-C02` | scatter每个child创建Task | 一个入口一个Task；child是IntakeItem/Revision + child Execution + TaskItem。 |
| `S02-C03` | Get Task 内嵌所有 children | 主资源必须有界；children 使用 cursor items。 |
| `S02-C04` | 一个 child 失败就立即 failed 并停止 siblings | collect-all；仍有 required active 时 Task running。 |
| `S02-C05` | parent failed/cancelled 就回滚已发布 child | child proof 决定可见性；撤销需要显式资源 Task。 |
| `S02-C06` | cancel receipt 直接写 cancelled | 先 cancelling，直到 descendants fenced/terminal。 |
| `S02-C07` | 原子重启复活旧scatter Task或允许caller选stage/process | 创建新`intake.rebuild` Task；内部recovery不进public API。 |
| `S02-C08` | full retry 覆盖旧 result/tree | 创建新 generation，旧 tree terminal immutable。 |
| `S02-C09` | restart row 独立维护 queued/running/status | Task 是状态 SSOT；restart 只存因果/admission。 |
| `S02-C10` | queue send/Promise.all/callback成功就是durable fan-out/completion | committed Snapshot/ChangeSet/scheduling intent和proof才是事实。 |
| `S02-C11` | Process 清理后 lineage 可以断链 | Execution summary、Audit、Task/restart 必须长期支撑查询。 |
| `S02-C12` | 用裸task_uuid/intake_item_uuid全局检索 | 所有业务查询必须team-scoped。 |

### 5.3 风险台账

| Risk ID | 风险 | 严重度 | 强制围栏 |
|---|---|---:|---|
| `S02-R01` | Task 与 root/children 状态漂移 | P0 | 单 transition service、event、reconciler、projection rebuild test |
| `S02-R02` | cancel/success 双终局 | P0 | revision CAS + cancel intent guard + fault/race test |
| `S02-R03` | Snapshot/ChangeSet已提交但child漏投递/重复投递 | P0 | transactional outbox + intent uniqueness + deterministic recovery |
| `S02-R04` | full retry 网络重放创建双 generation | P0 | source generation/fingerprint unique + expected revision CAS |
| `S02-R05` | atomic rebuild 新 Task 存在但 causal row/Audit 缺失 | P0 | 四项同事务提交，故障注入逐点验证 |
| `S02-R06` | restart 表复制 status 后与 Task 漂移 | P0 | schema 不设 writable current status；查询强制 join Task |
| `S02-R07` | early publication 后 parent cancel 误删知识 | P0 | cancel/deactivate/delete command 分离与权限测试 |
| `S02-R08` | Get Task无界或cursor漂移 | P1 | bounded envelope、Snapshot/ChangeSet-bound cursor、唯一tie-breaker |
| `S02-R09` | soft-delete/Process cleanup 断开审计链 | P0 | tombstone + FK/逻辑 retention fence + lineage acceptance test |
| `S02-R10` | 内部 UUID/路径/错误泄漏 | P1 | response allowlist、error sanitizer、security contract test |
| `S02-R11` | counts只数已创建child，遗漏expected child | P0 | counts/fan-in对照accepted Snapshot/ChangeSet required set |
| `S02-R12` | ready child被Task failed从检索层错误过滤 | P0 | retrieval visibility依据IntakeItem lifecycle + exact ServingRevision proof，不依据parent Task terminal status |

### 5.4 禁止方向

- 禁止 `attempt_uuid/task_attempts`；
- 禁止 child Task、scatter patch table、clean/rag Task/Process 分表；
- 禁止 Task singular `current_process_uuid`；
- 禁止 public `stage/process_uuid/force-step` 重启；
- 禁止 Task status 使用 RAG phase 或 partial success；
- 禁止 callback/queue/log 充当 Task 或 restart SSOT；
- 禁止为human review新增Task状态、child Task或直接Execution/Process写API；
- 禁止Task polling隐藏open gate，或仅靠UI/HTTP响应宣告release；
- 禁止cancel隐式执行IntakeItem/Vector purge；
- 禁止 physical delete Audit/restart/generation terminal evidence；
- 禁止复制 Worker/D1/R2/SMCP/Dispatcher 部署拓扑。

---

## 6. 测试与验收台账

### 6.1 强制验收矩阵

| Acceptance ID | 场景 | 通过条件 |
|---|---|---|
| `S02-A01` | Task/Audit 正常创建 | 同事务提交，首态 queued，返回 poll links |
| `S02-A02` | Task/Audit 任一点失败 | Task、Audit、scheduling intent 全不存在 |
| `S02-A03` | 同 fingerprint 创建重放 | 返回同一 Task，行数不增加 |
| `S02-A04` | 同 Task identity 不同 fingerprint | `409 task-identity-conflict`，原数据不变 |
| `S02-A05` | 跨 team 使用相同 task_uuid | 两个 Task 隔离；查询/命令不串租户 |
| `S02-A06` | 外部 PATCH 内部字段 | strict reject；status/result/root/process 不变 |
| `S02-A07` | 六态合法/非法边穷举 | 只允许 §2.3 状态图与 retry-only 回边 |
| `S02-A08` | queued/running result polling | `202 task-result-not-ready`，不是 404 |
| `S02-A09` | success proof 缺失 | Task 不得 succeeded |
| `S02-A10` | cancel/success 竞态 1,000 次 | 每次只有一个 durable 赢家，无双终局 |
| `S02-A11` | queued cancel | cancelling 后 fenced 收敛 cancelled，无工作偷跑 |
| `S02-A12` | cancel 后 late worker commit | 被 generation/fencing/CAS 拒绝 |
| `S02-A13` | scatter 一个 child 失败、siblings active | Task running 且 failed_count 正确 |
| `S02-A14` | scatter required 全终态含失败 | Task failed；成功 child 保持 ready |
| `S02-A15` | scatter required全部proof-valid | root/Task succeeded，counts与Snapshot/ChangeSet一致 |
| `S02-A16` | child proof早于root terminal | child可按IntakeItem/ServingRevision读取/检索，Task仍running |
| `S02-A17` | parent failed 后 ready child | ready/检索可见性不被回滚 |
| `S02-A18` | scatter cancel 含已发布 child | Task cancelled；ready child 保留；未完成工作停止 |
| `S02-A19` | items 大集合分页 | Get Task 有界；items 无重复/遗漏；cursor 稳定 |
| `S02-A20` | counts projection被故障注入破坏 | recovery从SnapshotMembership/ChangeSet/summary重建并告警 |
| `S02-A21` | failed Task full retry | 同 Task 新 generation queued，旧 generation immutable |
| `S02-A22` | cancelled Task full retry | 同 Task 新 generation queued，cancel summary 保留 |
| `S02-A23` | active/succeeded full retry | 分别返回 active/retry-not-allowed，不建 generation |
| `S02-A24` | full retry 网络重放 | 同一 restart_uuid/target generation，不建双 root |
| `S02-A25` | atomic child rebuild | 创建新 Task/Audit/restart row，旧 scatter 不变 |
| `S02-A26` | atomic rebuild 事务逐点失败 | restart/Task/Audit/intent 全部回滚 |
| `S02-A27` | restart admission rejected | 可有 immutable rejected row；无 Task/Execution |
| `S02-A28` | restart status 拉取 | status/result 来自 Task join，无第二 writer |
| `S02-A29` | restart list 全过滤组合 | team 隔离、稳定 cursor、正确 current status |
| `S02-A30` | task/intake-item/restart三种lineage seed | 返回同一因果图语义且无内部UUID泄漏 |
| `S02-A31` | Task soft-delete 后 lineage | 返回 tombstone + last summary，因果不断链 |
| `S02-A32` | Process compaction 后查询 | Task/items/generations/restart/lineage 结果仍完整 |
| `S02-A33` | queue wake-up 丢失/重复 | reconciler 补发；只产生一份业务执行事实 |
| `S02-A34` | response/error 泄漏扫描 | 无 token、stack、SQL、绝对路径、Process payload |
| `S02-A35` | IntakeItem deactivate/delete | 独立新Task/Audit；logical-first且不伪装为parent cancel |
| `S02-A36` | single Execution open gate | Task保持running；Get Task有bounded action_required，result仍not_ready |
| `S02-A37` | gate detail安全读取 | 返回gate kind/revision/target digest/evidence摘要；不泄漏Execution/Process/fence/secret/path |
| `S02-A38` | exact approve decision | append+CAS+outbox提交后same Execution恢复；重放幂等 |
| `S02-A39` | stale/double/conflicting decision | `409`且current gate/Task/Execution不被反转 |
| `S02-A40` | required child gate rejected | siblings继续；collect-all后root/Task failed，ready siblings不回滚 |

### 6.2 必须留存的验收证据

1. OpenAPI/strict model schema snapshot；
2. Task transition matrix 与 property-based transition report；
3. Turso/SQLite transaction、unique constraint 与 crash fault-injection report；
4. cancel/success、retry replay、fan-out recovery 并发测试报告；
5. scatter golden Snapshot/Membership/ChangeSet/counts/items/result fixtures；
6. Process compaction/soft-delete 前后 lineage 等价报告；
7. tenant isolation 与 response data-leak scan；
8. human gate OpenAPI、target/fence、idempotency与decision crash report；
9. legacy 对照场景：发起 → scatter → register → parallel wake-up → child proof → collect-all → atomic rebuild。

---

## 7. Reference-anchor 台账

### 7.1 权威文档锚

| Reference | 使用方式 |
|---|---|
| `docs/baseline/domain-truth/D01-task-execution-process-flow.md` | Task/Execution/Process 身份、single/scatter、状态归约、Process cleanup 与运行表职责 |
| `docs/baseline/domain-truth/S01-skill-worker-integration.md` | leaf-worker contract、Team、UUID、request_intent、Task/Audit、polling、PATCH/幂等/权限边界 |
| `docs/baseline/qna-truth/S02.md v1.3` | Q1–Q9 owner 回答与 `T-O-1..11` 的冻结来源 |
| `docs/baseline/spec-index.md` | 九段式结构、依赖顺序、状态与跨 spec 回填纪律 |

### 7.2 Legacy 代码事实锚

| Ref ID | 文件锚 | 证明的事实 |
|---|---|---|
| `S02-REF-L01` | `legacy-family/smind-admin/ingestion/apis.ts:62-175` | API 发起、父级注册、commit 后 workflow start |
| `S02-REF-L02` | `legacy-family/smind-skill-clean-dedicated-apis/providers/domain/processor.ts:135-241` | array scatter、atomic key、双 hash、并行候选 |
| `S02-REF-L03` | `legacy-family/smind-skill-clean-dedicated-apis/flows/reporter.ts:47-109,119-164` | 完整 child callback、失败回报与 first-child hint 债务 |
| `S02-REF-L04` | `legacy-family/smind-skill-clean-dedicated-apis/core/schemas_smcp.ts:80-169,172-264` | SMCP 身份、I/O、控制与观测字段 |
| `S02-REF-L05` | `legacy-family/smind-clean-dispatcher/flows/processor.ts:55-66,264-359` | workflow/callback 消费和 durable step registration |
| `S02-REF-L06` | `legacy-family/smind-clean-dispatcher/flows/orchestrator.ts:61-210` | 先建 process 再 wake-up、step transition |
| `S02-REF-L07` | `legacy-family/smind-clean-dispatcher/services/differ.ts:86-220` | stable atomic diff、content/meta/no-op 决策 |
| `S02-REF-L08` | `legacy-family/smind-clean-dispatcher/flows/finalizer.ts:106-269` | 完整 relation register 后并行 child fan-out |
| `S02-REF-L09` | `legacy-family/smind-clean-dispatcher/core/db.ts:170-377` | relation UPSERT 与 identity/constraint 漂移证据 |
| `S02-REF-L10` | `legacy-family/smind-clean-dispatcher/core/queues.ts:46-68` | `waitUntil(queue.send)` 不是 durable fan-out barrier |
| `S02-REF-L11` | `legacy-family/smind-rag-dispatcher/flows/finalizer.ts:66-168` | child ready/rag_failed 与 parent-untouched passive completion |
| `S02-REF-L12` | `legacy-family/smind-console/functions/api/files/list.ts:65-170` | 父/子扁平 list 与原子寻址 |
| `S02-REF-L13` | `legacy-family/smind-console/functions/api/files/[uuid]/artifacts.ts:55-159` | atomic artifact query |
| `S02-REF-L14` | `legacy-family/smind-console/functions/api/files/debug/pipeline/[uuid].ts:49-169` | atomic clean/RAG timeline |
| `S02-REF-L15` | `legacy-family/smind-console/functions/api/files/restart.ts:43-128` | team-scoped resource restart surface |
| `S02-REF-L16` | `legacy-family/smind-clean-dispatcher/services/restarter.ts:382-570,684-870` | stage recovery、failed/force/max-retry guard 与非原子 wake-up 债务 |
| `S02-REF-L17` | `legacy-family/smind-console/db/05-files.sql:197-257` | relation baseline DDL 缺少代码假设的 `(team_uuid, atomic_id)` 唯一约束 |

### 7.3 证据使用判定

- **保留原理**：稳定原子 key、双 hash、完整 child set、先注册后投递、siblings 并行、结构化 error、原子查询和人工重启需求；
- **重写机制**：SMCP callback→本地durable transition/event，D1→Turso-compatible relational truth，R2→logical local asset ref，Dispatcher queue→local queue/outbox/recovery；
- **删除拓扑**：Cloudflare Worker/Durable Object/RPC、platform auth/plan/phone、跨 Worker job/file identity、first-child hint、parent-untouched completion 和 stage/process public restart。

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO`**：S02 的 Task API、六态聚合状态机、scatter collect-all、三段式原子读面、proof-gated early publication、forward-stop cancel、full retry generation、atomic rebuild 新 Task、独立 `task_restarts` 因果账本以及全局 lineage 查询全部完成 owner-gate 并进入正式候选真相。

### 8.2 强制结论

1. Task 继续保持 RAG-agnostic 的 ACK/CRUD/aggregate；RAG specificity 必须在 S03 Process registry 与 S05-S09 proof 中实现；
2. API scatter 是首版主路径，不能再以后加 relation/route/hotfix 的方式实现；
3. `task_restarts` 使最小 durable 业务真相集合从四张扩展为五张，但不改变 Task/Execution/Process 三层运行身份；
4. full retry 与 atomic rebuild 不得合并：前者同 Task 新 generation，后者新 Task；
5. Task failed/cancelled 与 ready child 可以同时成立，监控、查询与检索不得用 Task 单一 status 推导 child 可见性；
6. Task soft-delete、Process cleanup 和日志 retention 不得破坏 Audit、generation、restart 或 lineage。
7. Human review不增加Task状态：open gate时Task保持running并显式投影action_required；decision只能通过Task-scoped gate command提交。

### 8.3 下游必须继续冻结的边界

| 下游 | 必须承接，但不由 S02 冒充冻结的内容 |
|---|---|
| `S03` | Execution/Process exact state、workflow definition、claim/lease/fencing、automatic retry、cancel propagation、human_review wait reason与semantic repair |
| `S04` | IntakeSource/Snapshot/Item/Revision/Membership/ChangeSet exact schema、rebuild/deactivate/delete semantics |
| `S05` | 已冻结source-scoped ExternalKey、PreflightOutcome、ExecutionGate/ReviewTarget/Decision与same-Execution resume；S02只投影并接收受控decision |
| `S08-S10` | publication proof、ready visibility、retrieval filter 与 version replacement |
| `S12` | Turso exact DDL、partial unique/transaction 能力、outbox 和 migration |
| `S15` | event/log/trace、retention 数值、告警与 projection repair 运行手册 |
| `S16` | token storage/rotation、network exposure、rate limit、review actor evidence/authority和内部诊断授权 |

上述未决实现细节不是 S02 owner-gate；任何下游方案若改变本文件 Truth ID 的产品语义，必须显式 reopen S02。

### 8.4 一句话结论

S02 将 Task 固定为可轮询、可线性化、可散射聚合且可完整追溯的外部请求账本，并以独立因果账本承接人工重启，而把具体 LS-RAG 执行继续留在 Execution/Process 层。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `S02-v1.0` | `2026-07-15` | `MKB owner + Codex` | `accepted` | 吸收冻结 Q1–Q9 与 `T-O-1..11`；正式冻结 Task 六态/CAS、scatter collect-all/items/early publication/cancel、full retry generation、atomic rebuild 新 Task、`task_restarts`、global restart/lineage、HTTP/error surface、验收与 legacy 证据台账；S02 QNA campaign 关闭。 |
| `S02-v1.1` | `2026-07-15` | `MKB owner + Codex` | `accepted / S04-calibrated` | 接收S04-v1.0：TaskItems与fan-in绑定SnapshotMembership/ChangeSet；canonical link改为IntakeItem/Revision；atomic scope改为`atomic_intake_item`与`intake.rebuild`；cancel/deactivate/delete、serving proof与lineage词汇对齐。 |
| `S02-v1.2` | `2026-07-16` | `MKB owner + Codex` | `accepted / S05-calibrated` | 接收S05-v1.0：Task六态不变；Execution waiting投影为running+action_required；新增Task-scoped gate list/get/decide语义、safe ReviewTarget projection、stale/idempotency边界与required rejection collect-all归约。 |
