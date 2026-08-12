# D01 — Task / Execution / Process Flow

> **项目**：`myknowledgebase`（MKB）
> **Domain / 子系统**：跨 `D2 / S02-S03` 的任务与执行基础模型
> **文档性质**：`specification / domain-truth / cross-domain decision`
> **文档状态**：`accepted architecture direction / S02-S06+D02-state-calibrated`（三层切分由 owner 主动提出；Task lifecycle/API、Intake truth、clean/preflight/HITL、S06 generation与跨域状态族已回流）
> **Truth 版本**：`D01-v1.4`
> **日期**：`2026-08-11`
> **作者归属**：`MKB owner` 主动提出切分；`Codex` 负责代码复核、规范化表达与 architecture verdict
> **形成初稿的权威输入**：Owner 对 `task_uuid / execution_uuid / process_uuid` 的直接裁决、`S01-v1.3`、`S02-v1.1`、`S03-v1.1`、`S04-v1.0`、`S05-v1.0`、`legacy-family/` 的 reference-anchor 生产事实；当前回流版本见D02状态校准声明与修订历史
> **上游索引**：`docs/baseline/spec-index.md`
> **上游真相**：`docs/baseline/domain-truth/S01-skill-worker-integration.md`
> **下游消费者**：`S02` Task API、`S03` Workflow Engine、`S04-S06` Intake/Scatter/Structurizer、`S07-S09` LS-RAG/Vector、`S12` Persistence、`S15` Observability、跨系统拓扑 `17`

> **Origin 声明**：`Task / Execution / Process` 三层切分不是 Codex 从 legacy-family 推导出的命名，也不是对 legacy `job/process` 表的改名复制。它是 **MKB owner 在 S02 讨论中主动提出的重构方案**。本文只负责把 owner 原始裁决整理为可实现、可验收、可回填的 Domain Truth，并以 legacy 的生产代码验证该方案是否覆盖真实故障面。

> **S02 回流声明**：`S02-v1.0` 没有改变 Task/Execution/Process 三层运行身份或三张核心运行状态表；它按 owner 裁决增加了独立 `task_restarts` 因果/admission 表。四张原有 Task/运行真相表继续成立，启用外部人工重启后的最小 durable 业务真相集合更新为五张。

> **S04 回流声明**：`S04-v1.0` 没有增加第四层运行身份。D01 原先宽泛的 `Source/Document/DocumentVersion/manifest` 资源口径现校准为 `IntakeSource/IntakeSnapshot/IntakeItem/IntakeRevision/IntakeSnapshotMembership`；`Artifact` 在 Intake 语境中必须写为 `IntakeArtifact`。Execution tree 与 Intake identity graph 仍是两个独立事实面。

> **S05 回流声明**：`S05-v1.0`没有增加preflight/review运行身份或第二套状态机。Preflight是S03 Process capability；human review是clean后、RAG前的Execution `waiting` durable gate，Process先terminal且不持lease。Execution锁定exact S05 binding，retry/recovery/resume不得热切；gate/outcome/decision只是supporting truth，不改变D01三张核心运行状态表。

> **D02 状态校准声明**：D02-v1.0将已经由S02-S05冻结的状态事实镜像为共有域ledger，并冻结`T-O-86..92`，不改变D01三层运行语义。Task/Execution/Process分别继续拥有S02六态、S03 Execution八态与S03 Process八态；phase、Outcome、waiting reason、Task result readiness、TaskItem outcome、Intake lifecycle、CandidateSet staging和ExecutionGate不得合并为第四套runtime状态。S03-v1.3已依据S05-v1.1确认exact capability key是唯一manifest identity；Execution subject/accepted output物理字段归S03/S04/S12，S08/S09 vector/index职责归S08/S09，均为D02-v1.0下游移交而非D02开放门。

> **S06 回流声明**：`S06-v1.0` 不增加第四层运行身份。GenerationArtifact / Invocation / per-type current pointer 是 Execution 作用域内的派生 generation 事实，不是 Task/Execution/Process 状态机。`lsrag.structurize` 仍是 Process capability；S06 success 不单独决定 Task 或 serving。structure rebuild 不制造 IntakeRevision，也不复活终态 Execution。

> **S12 回流声明**：`S12-v1.0` 不增加运行身份。Task/Execution/Process 状态机语义仍由 D01/S02/S03 拥有；S12 仅兑现单主库事务、claim/fence、outbox 后置 wake 与 TX 矩阵。queue/文件/向量均不得成为执行 SSOT。

> **约束级别**：本文中的“必须 / 禁止 / 仅允许”是后续设计与实现的强制约束；“应当”是 D01 verdict 的默认约束，若要偏离必须 reopen D01；“建议 / 可以”不冻结具体实现。本文明确标为“交由 S02/S03 冻结”的状态名、字段名或算法，不得被误读为已定 DDL。

---

> **S13校准声明**：`S13-v1.0` 冻结 v1 本地 `object_root` + `ObjectStorePort`、`mkbobj:v1` handle、team-scoped CAS、bytes-first、同库 catalog/ref/purpose、verify-on-read、周期 GC 与 identity readiness。本文件业务语义不变；对象 I/O 必须经 S13 Port，禁止 path/R2 key 进入契约。

> **S08校准声明（2026-08-12）**：`S08-v1.0` 冻结 exact ProcessCapability **`lsrag.vectorize`**（mode=`from_construct`|`purge_generation`）与 **S09** 独立 `index.validate_publication`。本文件拓扑与 `D01-T023` 中的 coarse **`lsrag.vectorize_index` placeholder 废止为生产键**（仅历史叙述可引用）；向量单元仍 **不是** Process identity（`D01-T035`）。Publication proof 仍归 S09；embedding 成功 ≠ index publication。

## 1. Domain 介绍

### 1.1 本决策要解决的问题

MKB 需要同时面对三种生命周期，但此前的讨论反复把它们压进同一个 `Task` 概念：

1. 上游提交一个请求、获得 ACK、轮询总状态并发出 CRUD/command；
2. MKB 为一个具体目标运行一次完整的 clean / LS-RAG / index 业务流程；
3. 某个具体工序被排队、claim、执行、失败、重试、成功或取消。

这三种生命周期的身份、保留时间、状态粒度和读写权限不同。继续用一个 UUID 或一张表承载，会直接导致：

- 外部 API 状态泄漏内部 RAG 工序；
- 散射任务无法用一个“当前 job”指针准确表达；
- retry 到底是重试整个请求、某次执行还是某个工序无法判断；
- 短期 process 记录被清理后，Task 失去 durable 结果；
- 一次 API 获取散射出 N 个 IntakeItem 时，外部请求与 N 个执行相互覆盖。

Owner 因此主动将运行模型切分为：

| 层级 | 权威身份 | 生命周期定位 | 核心一句话 |
|---|---|---|---|
| Task | `task_uuid`（与 `team_uuid` 组成外部权威键） | 外部 API / ACK / CRUD / 聚合状态 | “上游要求 MKB 完成什么” |
| Execution | `execution_uuid` | 内部 durable workflow run | “MKB 正在对哪个具体目标执行哪一次业务流程” |
| Process | `process_uuid` | 一个工序实例，可在 retention 后清理 | “这次执行中的某个具体步骤当前发生了什么” |

### 1.2 Task lifecycle 与 Workflow lifecycle 必须分开

本文冻结以下概念边界：

- **Task lifecycle** 由外部请求创建开始，以调用者可轮询的聚合终态结束；它不等于 RAG pipeline。
- **Workflow lifecycle** 由 `Execution` 承载。Execution 选择一个已版本化的 Workflow Definition，并驱动其中的 Processes。
- **Workflow Definition** 是“如何运行”的不可变/版本化模板，不是第四个运行实例身份；Execution 必须记录自己采用的 definition/version。
- **Process lifecycle** 是 Workflow Definition 中一个工序被实例化后的运行生命周期。

#### 1.2.1 状态、阶段、结果与资产生命周期分账

| 事实族 | 唯一 owner | D01中的作用 | 禁止混入 |
|---|---|---|---|
| Task aggregate status | S02 | 对外current generation六态 | RAG phase、human waiting、soft-delete |
| Execution control status | S03 | 一次durable workflow run八态 | Intake lifecycle、Process retry_wait |
| Process control status | S03 | claim/lease/retry/terminal八态 | queue delivery、业务phase |
| Execution phase/wait reason | S03 | 当前RAG焦点与durable trigger | 独立生命周期或Task状态 |
| ProcessOutcome/proof | S03 + capability owner | 驱动受guard的状态边和上卷 | current status本身 |
| Intake/Candidate/Gate state | S04/S05 | 长期资产、staging与人工准入事实 | 第四层runtime identity |
| readiness/current/serving | S02/S04/S06-S09 | 结果或版本选择 | 通用`status`字段 |

三层运行状态仍只允许自下而上归约，控制命令仍只允许自上而下传播。任何查询投影可以并列展示这些事实，但不能反向写入或制造一个笛卡尔积式`production_status`。

因此，Task 可以保持稳定、通用的 ACK/CRUD 语义；RAG 的业务专属性必须下沉到 Execution 的 workflow/target/mode 与 Process 的 `process_type / process_key / action_branch`，而不能丢失。

### 1.3 在整体运行拓扑中的位置

```text
外部调用者
  │
  │ POST Task / GET Task / cancel / retry / soft-delete
  ▼
Task  (team_uuid, task_uuid)
  │  外部 ACK + immutable request intent + aggregate projection
  │  current_root_execution_uuid
  ▼
Root Execution  (execution_uuid, durable)
  │
  ├── single Intake 入口
  │     ├── Processes: exact S05 acquire → decode/clean → seal/preflight → accept
  │     ├── Process: lsrag.structurize
  │     ├── Process: lsrag.construct
  │     ├── Process: lsrag.vectorize          # S08-v1.0 exact；mode=from_construct|purge_generation
  │     └── Process: index.validate_publication  # S09；独立于 vectorize
  │
  └── API 散射入口
        ├── Process: intake.acquire.registered_api
        ├── Process: clean.map.registered_api
        ├── Process: intake.collection.seal / intake.preflight_validate
        ├── Process: intake.accept_snapshot
        ├── Child Execution A (IntakeItem A)
        │     └── Processes: clean? → structurize → construct → vectorize → validate
        ├── Child Execution B (IntakeItem B)
        │     └── Processes: clean? → structurize → construct → vectorize → validate
        └── ... Child Execution N

状态归约方向：Process → Execution → Task
控制传播方向：Task command → Root Execution → Child Execution → active Process
查询身份方向：外部只依赖 Task；内部用 durable execution_uuid；诊断工序用 process_uuid
```

### 1.4 四个事实平面如何落位

| 平面 | Task | Execution | Process |
|---|---|---|---|
| Intake/资源属性平面 | 只保存请求目标与聚合结果引用；不保存散射明细 | 持有一个具体 IntakeSource/Snapshot/Item/Revision target；父子 Execution 只表达本次运行树 | 通过受控 input/output reference 读取或产生 IntakeArtifact/派生资产；不拥有 Intake 身份 |
| 观测平面 | 对外总状态、进度、错误/结果摘要、revision | durable 阶段、当前 process 指针、fan-out/fan-in 计数、最终证明摘要 | 精确状态、attempt/retry、claim/lease、耗时、结构化错误与验证结果 |
| I/O 平面 | 不传递主机绝对路径 | 固定本次运行的 IntakeArtifact namespace/Snapshot/ChangeSet 与最终结果引用 | 只消费/产生逻辑 I/O slot；首版 locator 由本地 filesystem adapter 解析 |
| 编排/控制平面 | 接收 cancel/retry 等外部 intent；不直接改内部步骤 | 解释 workflow definition，负责分支、fan-out/fan-in、取消传播与总体失败归约 | 负责可 claim 工作、worker 执行、自动 retry、max_retries 与 type-specific completion guard |

### 1.5 Scope fence

本文负责冻结：

- 三个运行身份的语义、责任和基数；
- Task 与 Workflow 生命周期分离；
- single Intake 与 API scatter 入口的 Execution 拓扑；
- retry、cancel、状态归约和 Process 清理的层级边界；
- D01 直接需要的业务状态表数量与表间关系；
- 对 legacy 生产经验的保留、改写与删除 verdict；
- 对 `S01` 既有 `attempt_uuid / task_type` 口径的回填要求。

本文不负责完整冻结：

- Task 对外精确 status enum、URI、HTTP error envelope、分页与 retention（`S02`）；
- Workflow Definition schema、Process 精确状态 enum、claim/lease、backoff 与 semantic recovery/repair 规则（`S03`）；
- IntakeSource/Snapshot/Item/Revision/Membership 的 exact DDL 与 S05 adapter contract（`S04-S05`）；
- IntakeArtifact bytes/backend 与本地路径布局（`S13`）；
- Vector record、filter metadata 和 publication proof 的完整 schema（`S08-S09/S12`）；
- append-only event/log envelope 与保留周期（`S15`）。

### 1.6 Domain 的完成定义

D01 在实现层完成，至少要求：

1. 任一 Task、Execution、Process 都不能互相复用 UUID；
2. 单文件入口形成一棵仅含 root Execution 的运行树；
3. 散射入口形成一个 root Execution 加 N 个 child Executions，并可按 Task/root 查询完整集合；
4. 每个 Process 必须且只能属于一个 Execution；
5. Task 状态只能从 Execution 聚合，Execution 状态只能从 Process/child Execution 聚合；
6. 自动工序 retry 与整次 Execution retry 不混用身份；
7. Process 清理不破坏 Execution/Task 的 durable 查询、错误摘要和结果证明；
8. 成功必须以经校验的向量 + filter metadata publication proof 为 guard；
9. 核心状态只需三张 D01 业务表承载，不复制 legacy 的 clean/rag/vec process 分表；
10. §6 的验收场景全部具备可重复的测试证据。

---

## 2. 真相层

### 2.1 真相层使用纪律

本节是 D01 的 SSOT。来源分为三类：

- `OWNER-ORIGINATED`：owner 在 S02 讨论中主动提出并直接确定的切分；
- `CODE-FACT`：legacy-family 当前生产代码直接证明的事实，只作为设计分母；
- `D01-VERDICT`：在 owner 切分与代码事实基础上形成的规范化裁决；后续若要偏离必须 reopen D01。

`CODE-FACT` 不自动成为 MKB 目标。本文尤其禁止把 Cloudflare Worker、D1、R2、Queue callback、Durable Object 或 legacy 表名复制为新系统要求。

### 2.2 Owner-originated 基础真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `D01-T001` | `Task / Execution / Process` 三层切分由 MKB owner 主动提出，不是 assistant 自行创造的新 task 词汇，也不是 legacy 表结构翻译。 | `OWNER-ORIGINATED` | 后续文档必须保留 origin 声明，禁止把该方案归因为 legacy 或 Codex。 |
| `D01-T002` | Task lifecycle 与 Workflow lifecycle 必须分开；Task 从具体 RAG pipeline 抽离，作为 ACK、CRUD、外部总状态与命令边界。 | `OWNER-ORIGINATED` | `S02` 只拥有外部 Task contract，不定义 clean/structurize/construct/vectorize 的内部工序状态。 |
| `D01-T003` | `task_uuid` 面向外部 API；无论 single Intake 还是 scatter 入口，都以 Task 作为唯一请求起点。 | `OWNER-ORIGINATED + S04-CALIBRATION` | 上游不得创建 `execution_uuid` 或 `process_uuid` 来绕过 Task ingress。 |
| `D01-T004` | `execution_uuid` 只在 MKB 内部产生和流转，必须 durable；它是执行阶段唯一稳定的内部查询 UUID。 | `OWNER-ORIGINATED` | 进程重启、队列 redelivery、工序 retry 不得替换当前 Execution 身份。 |
| `D01-T005` | 散射 Task 可以产生多个 `execution_uuid`；每个 Execution 持有具体执行状态与业务流转总体控制。 | `OWNER-ORIGINATED` | Task:Execution 是 1:N，禁止 schema 假设“一 Task 永远只有一个 Execution”。 |
| `D01-T006` | `process_uuid` 承载具体业务项下某个工序实例的状态细节；Process 不是外部资源，满足S03 terminal-summary与cleanup-eligibility围栏后可按retention清理。 | `OWNER-ORIGINATED + S03-CALIBRATION` | `S03/S12/S15` 必须先把 durable 摘要上卷到 Execution、关闭全部控制围栏，再允许清理。 |
| `D01-T007` | 具体是 clean 还是 RAG、采用哪些工序、每个工序如何流转，必须由下游 Workflow/Process 定义，不由 Task type 冒充。 | `OWNER-ORIGINATED` | RAG 专属性必须存在于 workflow/process schema；不得再提出可用于任意业务域的空泛内部 task type。 |

### 2.3 身份、基数与血缘真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `D01-T008` | Task 的权威键继续继承 S01：`(team_uuid, task_uuid)`；`task_uuid` 不能脱离 team 裸查。 | `S01-T011/T012 + D01-VERDICT` | Execution/Process 均必须可追溯到同一 team/task，不能只靠跨表推算租户归属。 |
| `D01-T009` | Task 必须保存 `current_root_execution_uuid` 或语义等价的当前 root 指针；不得保存一个声称代表整个散射任务的 singular `current_process_uuid`。 | `D01-VERDICT` | 单一 current process 指针只属于某个 Execution；Task 用 root + 聚合计数表达 1:N。 |
| `D01-T010` | 每个 Execution 必须属于一个 Task；每个 Task 可保留多个历史 root Executions，但任一时刻最多只能有一个 current/active root。 | `D01-VERDICT` | retry 不覆盖历史执行；数据库需要 current pointer/CAS 或等价唯一约束。 |
| `D01-T011` | 每个 Execution 必须记录 `root_execution_uuid`；root 的该字段等于自身，child 同时记录 `parent_execution_uuid`。 | `D01-VERDICT` | 不需要额外 Task-Execution join 表或 scatter-execution relation 表即可表达树与高效查询。 |
| `D01-T012` | scatter child 的 `parent_execution_uuid` 指向本次 fan-out root；长期集合与资产血缘由 IntakeSource/Snapshot/Membership/Item/Revision 表达，不能用 Execution 血缘替代。 | `D01-VERDICT + S04-T001..T008` | Execution tree 与 Intake identity graph 是两个事实面，允许显式关联但禁止共用 relation row。 |
| `D01-T013` | `process_uuid` 是工序**实例身份**，不是工序分类；必须另设 `process_type/process_key`，并记录 workflow rank/action branch 或等价定义快照。 | `D01-VERDICT + CODE-FACT` | 不能出现 `process_uuid='structurize'` 或仅凭 UUID 猜步骤类型。 |
| `D01-T014` | 一个 Process 必须且只能属于一个 Execution；Execution 可以拥有顺序、分支或并发的多个 Processes。 | `D01-VERDICT` | Process FK 直接指向 execution；跨 Execution 复用 process row 被禁止。 |
| `D01-T015` | MKB 内生的 `execution_uuid` 与 `process_uuid` 使用 UUIDv7；它们与 Task、Trace、五类 Intake UUID、Vector identity 相互独立。 | `S01-T008/T009 + D01-VERDICT + S04-T001` | 任一 identity 都不能因“方便关联”复用另一个 identity。 |

### 2.4 三层责任与状态所有权真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `D01-T016` | Task 只拥有外部 intent、ACK/CRUD、aggregate status、current root 指针、result/error summary、revision 与命令接收状态。 | `OWNER-ORIGINATED + D01-VERDICT` | Task 不拥有 workflow step、claim、lease、step retry、Intake lifecycle或中间资产的权威状态。 |
| `D01-T017` | Execution 拥有一次具体目标执行的 durable 总体控制：target、workflow/version、mode、tree lineage、phase、当前 process、fan-out/fan-in、取消传播、最终结果/错误/证明摘要。 | `OWNER-ORIGINATED + D01-VERDICT` | Process 清理后 Execution 仍必须独立解释这次执行发生了什么。 |
| `D01-T018` | Process 拥有工序运行真相：type/key、input/output refs、queue/claim/lease、status、retry/max_retries、时间、结构化 error 与 type-specific validation。 | `OWNER-ORIGINATED + CODE-FACT + D01-VERDICT` | 所有 worker 执行和自动恢复必须通过统一 Process transition path。 |
| `D01-T019` | 状态只允许自下而上归约：`Process/child Execution → Execution → Task`；上层不得直接伪造下层成功。 | `D01-VERDICT` | Task `succeeded` 不能绕过 Execution proof；Execution `succeeded` 不能绕过 required Process guards。 |
| `D01-T020` | 控制 intent 自上而下传播：Task command → current root → descendants → active Process；每层记录自己是否已接受、传播和收敛。 | `D01-VERDICT` | “收到 cancel HTTP”与“Process 已停止”必须是不同事实。 |
| `D01-T021` | 对外 Task status 应保持少量稳定聚合状态；RAG 业务阶段通过 Execution phase 与 Process type 暴露给内部观测，不扩张 Task enum。 | `OWNER-ORIGINATED + D01-VERDICT` | S02/S03 分别冻结两套词汇，不能共享一个含混 enum。 |

### 2.5 RAG 工序与成功边界真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `D01-T022` | 标准 LS-RAG 的业务工序至少要能表达 intake resolve/fetch/accept、clean、structurize、construct、vectorize/index与publication validate；具体是否跳过clean由IntakeSource capability与versioned Workflow决定。 | `CODE-FACT + OWNER direction + S04` | `S03/S05-S09` 必须用RAG-specific process keys，而不是generic `process_data`。 |
| `D01-T023` | Process必须以唯一versioned manifest identity承载RAG-specific业务边界：Intake/Clean使用S05 exact capability keys；LS-RAG 生产链 exact keys 至少含 `lsrag.structurize`、`lsrag.construct`、**`lsrag.vectorize`（S08-v1.0）**、`index.validate_publication`（S09）。历史 coarse **`lsrag.vectorize_index` 不得作为生产 process key**。它们都不是Task type。 | `D01-VERDICT + S03/S05 + S08-v1.0` | 禁止用 embedding 成功代替 publication；禁止 vec unit 冒充 Process。 |
| `D01-T024` | Process 成功必须由 type-specific completion guard 判定；仅收到 callback、队列为空或 `pending_count=0` 都不等于成功。 | `OWNER direction + CODE-FACT + D01-VERDICT` | 每个 Process type 需要明确 output schema、validation proof 与失败语义。 |
| `D01-T025` | 单个IntakeItem Execution的业务成功终点是预期向量及filter metadata写入目标vector store并校验通过；proof必须绑定exact IntakeRevision并持久化到Execution summary。 | `OWNER-ORIGINATED + S04-T015/T016` | Process清理后仍能审计成功依据；latest不能冒充serving。 |
| `D01-T026` | scatter root Execution的成功还要求accepted IntakeSnapshot/ChangeSet required set已提交，且其中所有required child Executions满足各自成功guard。 | `D01-VERDICT + S04-T024..T029` | fan-in以持久membership/required set为准，不能以当前child count猜分母。 |

### 2.6 Retry、取消与保留真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `D01-T027` | 队列 redelivery 与同一工序的自动 retry 继续使用原 `process_uuid`；自动 retry 递增 retry counter，受 `max_retries` 止血约束。 | `CODE-FACT principle + D01-VERDICT` | redelivery 不得制造重复 Process 或重复业务写入。 |
| `D01-T028` | 对一次已终结 Execution 的人工/命令级整次 retry 必须创建新的 `execution_uuid`，用 `retry_of_execution_uuid` 保留血缘，并产生新的 Process 实例。 | `OWNER model + D01-VERDICT` | 旧 Execution/Process 不得被复活或覆盖；Task identity 不变。 |
| `D01-T029` | `execution_uuid` 吸收 S01 中“完整执行尝试”的 `attempt_uuid` 语义；MKB 不应同时保留两个职责重叠的 durable 执行身份。 | `D01-VERDICT` | 必须 reopen/回填 `S01-T014` 及其 Attempt 表述。 |
| `D01-T030` | cancel 的接收属于 Task，传播与收敛属于 Execution，停止/补偿属于 Process；最终 Task 状态只能在 current root 收敛后归约。 | `D01-VERDICT` | S02 冻结 API race；S03 冻结 cooperative cancel、lease fencing 与补偿。 |
| `D01-T031` | Process 只能在所属 Execution 已终结、retry/recovery/cancel/outbox控制窗口关闭、durable summary 已上卷且不存在 dangling pointer 后清理。 | `OWNER-ORIGINATED + D01-VERDICT` | `executions.current_process_uuid` 清空或转为 final_process_uuid 后才允许物理清理。 |
| `D01-T032` | Process retention 与 Event/Log retention 是不同策略；删除 process projection 不授权删除 append-only 运行证据。 | `D01-VERDICT` | `S15` 单独冻结 event/log 归档与删除。 |

### 2.7 本地化与 legacy 借鉴边界真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `D01-T033` | MKB 保留 legacy 的身份分面、步骤状态、输入输出、结构化错误、retry/max_retries、fan-out/fan-in 和日志证据原则。 | `OWNER direction + CODE-FACT` | 这些能力必须在本地单体中完整实现。 |
| `D01-T034` | MKB 不复制 legacy 的 clean_job/rag_job 身份断裂；一次具体 IntakeItem/Revision 的 clean → RAG 由同一 Execution 贯穿，工序边界由 Process 表达。 | `D01-VERDICT + S04-CALIBRATION` | 不因 action_domain 切换而无理由生成新 Execution。 |
| `D01-T035` | MKB 不复制 `smind_clean_process / smind_rag_process / smind_vec_process` 三张历史业务表；统一 Process 控制模型，Vector record 归向量资产域。 | `D01-VERDICT` | `S08/S09` 自己持有 vector asset，不把每个 vec unit 冒充 Process。 |
| `D01-T036` | 本地轻量队列是 transport/scheduling mechanism，不是状态 SSOT；可 claim 工作必须来自已提交的 Process/scheduling record。 | `OWNER direction + D01-VERDICT` | 日志“已发送”或内存 queue item 不能代替 durable Process。 |
| `D01-T037` | IntakeArtifact与派生资产首版使用本地I/O adapter；Task/Execution/Process只保存logical reference/relative locator/digest，不保存R2 binding，也不把绝对路径当API identity。 | `OWNER-ORIGINATED + S04-T006` | `S13`可替换backend而不改变runtime或Intake identity。 |
| `D01-T039` | S04五类Intake identity是长期业务真相，不是第四层runtime identity；Task/Execution/Process retention不得级联删除其IntakeRevision/IntakeArtifact或tombstone/audit skeleton。 | `S04-v1.0 / T-O-30..48` | D01三层状态表数量不变；长期资产与运行投影分别治理。 |
| `D01-T038` | S02 增加 `task_restarts` 作为外部人工重启的 durable causation/admission SSOT；它不是第四层运行身份，也不复制 Task status。 | `S02-v1.0 / OWNER-QNA` | 四张核心 Task/运行表保持，外部重启启用后的最小 durable 业务真相集合为五张。 |
| `D01-T040` | PreflightValidator是S03统一Process状态机下的RAG-specific leaf capability，只读本Execution冻结的S05 evidence并返回typed Outcome。 | `S05-v1.0 / T-O-70..71` | 不新增preflight job identity/table/state machine；runtime错误走同一Process retry/failed。 |
| `D01-T041` | Human review是Execution-owned durable gate：Process先terminal，Execution以typed gate ref进入`waiting`，decision后恢复同一execution_uuid。 | `S05-v1.0 / T-O-54..58/T-O-75` | Gate/Target/Decision不是第四层runtime identity，Intake不保存review state。 |
| `D01-T042` | Execution必须锁定actual source/acquisition/clean/preflight refs与`s05_binding_digest`；retry/recovery/human resume不得热切active版本。 | `S05-v1.0 / T-O-73` | 已有Task升级只能走S02 causal restart/new Execution generation。 |
| `D01-T043` | `passed+allowlisted`不创建gate；只有确实等待人工时建立四态gate。Outcome→transition、gate→waiting、decision→outbox与late/stale恢复复用S03/S12。 | `S05-v1.0 / T-O-71/T-O-75..76` | 不建设S05 Reconciler、自动approve或固定九表拓扑。 |

---

## 3. 三层模型的详细责任

### 3.1 Task：外部请求与 ACK/CRUD 聚合

#### 3.1.1 Task 必须承担

| 责任 | 具体含义 |
|---|---|
| External identity | 接受 caller-supplied `(team_uuid, task_uuid)`，保持幂等和 team-local uniqueness |
| ACK | Task + Audit 原子提交后返回稳定 Task identity、初始 aggregate status、revision 与 poll location |
| Immutable request intent | 保存外部请求要完成的资源动作及严格 payload；创建后不允许改写执行输入 |
| CRUD/read model | 提供 get/list、描述性 PATCH、soft-delete/tombstone；不提供内部步骤 mutation |
| Command boundary | 接收 cancel/retry 等命令 intent，并用 revision/CAS 处理并发 |
| Aggregate projection | 汇总 current root 及 required child Executions 的状态、进度、错误和结果 |
| Execution pointer | 保存 `current_root_execution_uuid`；历史 Executions 通过 task FK 查询 |
| Stable result | 保存最终 IntakeItem/Revision/result/publication proof引用摘要，使 Process 清理后仍可 polling |

#### 3.1.2 Task 明确不承担

- 不决定下一步是 clean、structurize、construct 还是 vectorize；
- 不保存 queue claim、lease owner、worker heartbeat 或 step retry counter；
- 不把散射 child 直接塞进 Task status JSON 作为唯一真相；
- 不用 `task_type` 代替 workflow definition/process type；
- 不因某个 Process callback 成功就直接进入 Task 成功终态；
- 不向外部开放写 `status/progress/result/error/current_execution_uuid` 的能力。

#### 3.1.3 Task 状态的语义要求

精确 enum 由 S02 冻结，但必须能表达以下不可省略的语义阶段：

```text
原子接受/ACK
  → 等待 current root 可运行
  → current root 或其 children 正在运行
  → 成功（全部 required executions + proof）
     或失败（已无内部自动恢复路径）
     或取消收敛（cancel intent 已传播并停止 active work）
```

Task status 是投影而非第二套执行真相。Task 表可以缓存 counters 和摘要以加快 polling，但必须能由 durable Execution 集合重建/对账。

### 3.2 Execution：一次具体目标的 durable Workflow Run

#### 3.2.1 Execution 必须承担

| 责任 | 具体含义 |
|---|---|
| Internal durable identity | `execution_uuid` 跨进程重启、队列 redelivery 和 Process retry 保持不变 |
| Concrete target | 明确本次运行针对 IntakeSource、Snapshot、Item、Revision 或受控 index/cleanup scope |
| Workflow snapshot | 记录 workflow key、definition UUID/version、config/model/prompt version 或可复验 digest |
| Execution role | 区分 root controller、single-Intake root、scatter child 等角色 |
| Lineage | 记录 task、root、parent、retry-of；能复原执行树和 retry 历史 |
| Overall control | 按定义创建 Process、推进阶段、分支、fan-out、fan-in、传播 cancel |
| Durable phase | 保存当前业务阶段与 `current_process_uuid`，供内部稳定查询 |
| Aggregate status | 根据 required Processes/children 归约自身状态，而非由 worker 任意写终态 |
| Durable summary | 终态时保存步骤计数、retry、final error、artifact/vector refs、publication proof 与版本信息 |

#### 3.2.2 Execution 明确不承担

- 不成为外部 caller 创建的 API resource；
- 不替代 IntakeItem/IntakeRevision 的业务身份；
- 不把每一次自动 Process retry 变成新的 Execution；
- 不用 parent_execution_uuid 代替 IntakeSnapshotMembership 或 Intake provenance；
- 不把所有中间 output 大对象复制进自身 row；只保存受控摘要与 reference；
- 不在 clean → RAG 的领域交接处像 legacy 一样无条件更换 job identity。

#### 3.2.3 Execution 状态与 phase 必须分开

Execution 的**控制状态**已由S03冻结为`created/ready/running/waiting/succeeded/failed/cancelling/cancelled`。Execution没有`retrying`状态；automatic retry由同一Process的`retry_wait`与计数表达。

Execution 的**业务 phase**必须是 RAG-specific，并来自当前 Process/Workflow Definition，例如：

```text
source_acquisition
  → cleaning_or_scattering
  → preflight_admission
  → awaiting_human_review (conditional; control status=waiting)
  → structurizing
  → constructing
  → vectorizing_and_indexing
  → validating_publication
  → fan_in (scatter root only)
```

不能为了避免“generic”而把所有业务 phase 扩入 Task status；也不能为了保持 Execution status 简洁而删除 RAG phase。二者是不同字段、不同查询目的。

### 3.3 Process：一个具体业务工序实例

#### 3.3.1 Process 必须承担

| 责任 | 具体含义 |
|---|---|
| Instance identity | 每次由 Workflow Definition 实例化工序时生成新的 `process_uuid` |
| Business classification | 保存唯一exact `process_key/contract_version`、requiredness、Workflow step/ref与process spec digest；family/phase只作正交分类 |
| I/O contract | 保存严格input/output schema version、IntakeArtifact/derived asset refs、digest与validation result |
| Scheduling | 保存 queue/scheduling state、available_at、priority 或等价 claim 条件 |
| Concurrency control | 保存 claim token、lease owner、lease expiry、fencing generation |
| Runtime status | 只记录 `ready/claimed/running/retry_wait/succeeded/failed/cancelling/cancelled` |
| Retry control | 保存 retry_count、max_retries、last_error_class、next_retry_at |
| Observability | 保存 started/completed/heartbeat 时间、error code/message/details ref、metrics summary |
| Completion guard | 按 process type 校验输出；校验失败必须是失败，不能伪装 completed |

#### 3.3.2 Process 类型必须与 RAG 实际业务对齐

首版至少应覆盖以下业务能力。S05已冻结的exact capability key优先于D01早期coarse示例；coarse family不再作为兼容`process_key`进入registry：

| Exact capability key / downstream placeholder | 业务职责 | 成功 guard 示例 |
|---|---|---|
| `intake.acquire.inline` / `intake.acquire.local_object` / `intake.acquire.http_static` / `intake.acquire.http_browser` / `intake.acquire.registered_api` | 按exact SourceKindDefinition获取representation | typed AcquisitionEvidence、media/encoding/budget和logical handle完整 |
| `intake.decode.text_json_html` / `intake.decode.pdf` | 确定性解码与canonicalization | exact schema/canonicalizer/digest与loss evidence通过 |
| `clean.extract.deterministic` / `clean.ocr.local` / `clean.extract.vision` / `clean.map.registered_api` | 产生typed clean/member候选 | CleanArtifactCandidate、ExternalKey/semantic/anchor/quality evidence完整 |
| `intake.collection.seal` | 对single/scatter CandidateSet执行完整性封口 | page/root digest、count、dedupe、scope/completeness与exhaustion proof通过 |
| `intake.preflight_validate` | 以exact code-owned validator只读校验frozen acquisition/collection/clean evidence | typed`passed|blocked` Outcome与ordered check evidence已提交；runtime错误走Process retry/failed |
| `intake.accept_snapshot` | 接受sealed CandidateSet并原子提交Snapshot/Membership/ChangeSet与child intent | accepted Snapshot/required set已提交，可重放 |
| `lsrag.structurize` | 生成目录/逻辑分块/structured representation | structured schema、块坐标与 source coverage 校验通过 |
| `lsrag.construct` | 单文档整包 original/summary 双通道构造（S07-v1.0） | 整包 dual-channel full-valid + construction generation refs/proof；非结构级独立成功 |
| `lsrag.vectorize`（S08-v1.0 exact） | embedding + upsert `mkb_vector_records`；mode=`from_construct`\|`purge_generation` | 不能以embedding成功代替 index publication proof（S09） |
| ~~`lsrag.vectorize_index`~~ | **废止生产键**（原 coarse placeholder） | 不得注册为兼容 alias |
| `index.validate_publication` | 独立验证本次发布集合 | expected/actual 集合、filter metadata、可检索性证明一致 |
| `intake.physical_purge` | delete/retention后受控清理eligible派生数据 | scope内required substrate cleanup proofs完成 |

`process_uuid` 永远是上述类型的一次运行实例。相同 `process_key` 可在不同 Execution 中出现，也可以因整次 Execution retry 产生新的 Process UUID。

#### 3.3.3 Process 的 exact 状态语义

S03-v1.3承接的Process exact enum保持不变，本版不再保留`pending/scheduled/completed/retrying`占位别名：

```text
materialize
  → ready
  → claimed (持有 lease/fencing token)
  → running
     ├── succeeded (type-specific guard 通过)
     ├── retry_wait → ready（retry_count < max_retries且due）
     ├── failed（不可重试或预算耗尽）
     └── cancelling → cancelled

lease 过期：claimed/running → fenced recovery → ready | failed
queue redelivery：若状态/claim token 不允许执行，则幂等 no-op
```

Process 状态与消息意图不能混为一个字段。`STEP_START/STEP_RESTART` 在 legacy 是通信动词；MKB 本地模型需要 command/event 与 current process state 分开。

### 3.4 三层对照总表

| 维度 | Task | Execution | Process |
|---|---|---|---|
| 谁创建 | 外部 caller 提供 Task UUID；MKB 原子接收 | MKB scheduler/orchestrator 创建 | MKB workflow engine 创建 |
| 主要读者 | 外部 orchestrator、polling client | 内部 orchestrator、semantic recovery scanner、运维诊断 | worker runner、queue adapter、transition/repair service、调试工具 |
| 基数 | 每个外部请求一个 Task | 每 Task 1:N；含历史 root 与 scatter children | 每 Execution 1:N |
| 稳定期 | API retention 期内 durable | durable，至少不短于 Task/业务审计需要 | projection可清理，但受终态summary与cleanup-eligibility fence约束 |
| 状态粒度 | 总状态 | 一次目标执行总体状态 + RAG phase | 一个工序的精确运行状态 |
| retry 身份 | Task 不变 | 整次 retry 新 Execution | 自动 retry 保持 Process |
| scatter 角色 | 聚合一棵执行树 | root fan-out + N child runs | root/child Execution 内各自工序 |
| 成功依据 | current root 汇总 | required processes/children + proof | type-specific output validation |
| 允许外部写 | create、白名单 patch、command | 无外部直接状态写 | 无外部直接状态写 |
| 可否软删/清理 | soft-delete，不破坏 Audit | durable/tombstone/归档策略 | cleanup-eligible 后可 archive/delete |

---

## 4. 单一文件与散射入口

### 4.1 单一文件入口

#### 4.1.1 身份形状

```text
Task T
  └── Root Execution E1
        ingress subject = IntakeSource/new input（ingest）或exact IntakeItem/Revision（rebuild）
        accepted output binding = IntakeItem/Revision I1（只在S04 acceptance后存在）
        root_execution_uuid = E1
        parent_execution_uuid = null
        ├── Processes P1..n: exact S05 acquire/decode/clean/seal capabilities
        ├── Process P-preflight: intake.preflight_validate
        ├── Process P-accept: intake.accept_snapshot（ingest）
        ├── ExecutionGate G1 (conditional; no Process lease)
        ├── Process P3: lsrag.structurize
        ├── Process P4: lsrag.construct
        ├── Process P5: lsrag.vectorize
        └── Process P6: index.validate_publication
```

这是 `1 Task : 1 current root Execution : N Processes`。若IntakeSource输入已经是严格schema验证的canonical text，versioned Workflow可以省略/替换clean工序；不能因此省略Execution。

#### 4.1.2 建议提交顺序

```text
1. 外部提交 Task + Audit
2. 同一 ingress transaction：team gate + idempotency + Task/Audit + durable scheduling intent
3. commit 后创建/激活 Root Execution，并 CAS 写 Task.current_root_execution_uuid
4. 按 workflow version 创建第一个 Process
5. Process 通过本地轻量 queue 被 claim；执行、校验、写 outcome/event
6. Orchestrator 根据成功 outcome 创建/激活下一个 Process；clean后运行mandatory preflight
7. allowlisted+passed直接推进；需要人工时Process先terminal、Execution以exact gate ref进入waiting，decision后恢复同一Execution
8. vectorize/index 与 publication validation 均通过
9. Execution 写 durable proof/summary → succeeded
10. Task 从 Execution 归约 aggregate result → succeeded
```

第 3–4 步的精确事务边界由 S03/S12 冻结，但必须满足：Task 已提交前不可执行；Execution/Process 已 durable 前不可让 queue 成为唯一工作证据。

#### 4.1.3 失败与 retry

- Process 可重试错误：同一 `process_uuid` 进入 retry_wait，增加 retry_count，再次 claim；
- Process 不可重试/预算耗尽：Process failed，Execution 根据 workflow policy failed 或进入受控补偿；
- 整次 retry command：Task 不变，创建新的 root Execution E2，`retry_of_execution_uuid=E1`，重新实例化 Processes；
- E1 永久保留终态摘要，不允许把 failed 改回 running。

### 4.2 API 散射入口

#### 4.2.1 为什么不能让 Task 直接指向一个“当前 Process”

一次API观察可能并发产生多个IntakeItem。scatter后，A可能在structurize、B在vectorize、C正在retry，不存在一个能代表整体真实进度的singular process指针。

因此：

- Task 指向 current root Execution；
- root Execution 保存 expected child set/fan-out summary；
- 每个 child Execution 保存自己的 current process；
- Task 通过 root 的 child counters/aggregate projection 对外表达总状态。

#### 4.2.2 身份形状

```text
Task T
  └── Root Execution E-root
        ingress subject = IntakeSource S1
        ├── Process P-fetch: intake.acquire.registered_api
        ├── Process P-map: clean.map.registered_api
        ├── Process P-seal: intake.collection.seal
        ├── Process P-preflight: intake.preflight_validate
        ├── Process P-accept: intake.accept_snapshot
        ├── Child Execution E-A → target IntakeItem/Revision A → RAG Processes...
        ├── Child Execution E-B → target IntakeItem/Revision B → RAG Processes...
        └── Child Execution E-N → target IntakeItem/Revision N → RAG Processes...
```

Root Execution是本次API fetch/scatter/fan-in的durable controller。每个child Execution针对一个exact IntakeItem/Revision。并发发生在child Executions之间，也可以发生在允许并行的Processes之间。

#### 4.2.3 散射执行顺序

```text
1. Task ingress 原子提交
2. 创建 E-root，执行 `intake.acquire.registered_api`
3. `clean.map.registered_api` 输出stable ordered CandidateSet pages、typed rejection/gap evidence与clean Artifact candidates
4. mandatory root preflight只读frozen acquisition/collection/clean evidence；required异常产生blocked Outcome：不可保存/不可审核者fail，可信candidate可按contract seal并由S04接受后进入受控human path
5. seal验证page/root digest、count/bytes、ExternalKey、Artifact与source-exhaustion proof
6. S04以source-scoped ExternalKey解析/复用IntakeItem、计算versioned semantics，并单事务提交accepted Snapshot、Membership、Revision decision、ChangeSet与fan-out intents
7. 若root需要人工审核，先以exact ReviewTarget gate等待；release后才为required set创建durable child Executions
8. 轻量队列并发运行child的clean/preflight/RAG Processes；真正需要人工判断的child使用各自ExecutionGate
9. E-root按Snapshot/ChangeSet的required set与durable gate/child outcome做fan-in，不按临时查询结果猜数量
10. 全部 required children 成功且各自 publication proof 有效 → E-root succeeded；任一 required child最终失败则默认Task/Root failed
```

“默认 all-required”是 D01 verdict。若未来业务需要允许 partial success，S02/S03/S04 必须共同 reopen：明确 required/optional child、对外状态、结果 envelope、检索可见性和 retry 语义；不得只新增一个 `partially_succeeded` 字符串。

#### 4.2.4 增量散射

IntakeSource的后续Snapshot可能得到新增、semantic变化、无变化或authoritative absence：

- Snapshot/Membership/Revision decision属于S04长期真相；S05只生成typed CandidateSet、PreflightOutcome与Execution-owned gate/decision supporting truth；
- 本次no-change的member可以不创建新Execution，但必须在Membership/ChangeSet中有证据；
- 需要 rebuild/update/purge 的 child 创建新的 child Execution；
- “本次不需要执行”与“执行成功”是两个不同事实；
- root fan-in的expected set是本次accepted IntakeChangeSet required executions，不是IntakeSource历史上所有IntakeItems。

### 4.3 单文件与散射对照

| 维度 | 单一文件 | API 散射 |
|---|---|---|
| Task 数 | 1 | 1 |
| Root Execution | 1，兼作single IntakeItem execution | 1，作为IntakeSource fetch/scatter/fan-in controller |
| Child Execution | 0 | 0..N，按本次 required child set 创建 |
| 当前工序表达 | root.current_process_uuid | 每个 child 各自 current_process；root 保存 fan-in phase/counters |
| 并发位置 | workflow 允许的 Process 并发 | child Executions 并发 + 各自内部 Process 调度 |
| 成功 guard | exact IntakeRevision publication proof | Snapshot/ChangeSet commit + 所有required child proofs |
| 结果形状 | 单Item/Revision result summary | root Snapshot/ChangeSet summary + child result summaries |
| retry | 新 root Execution | 自动 step retry 原地；整 Task retry 新 root tree；内部 child step retry不换 child Execution |

---

## 5. 数据表 verdict

### 5.1 D01 直接需要三张核心业务状态表

**明确结论：Task / Execution / Process 业务状态由且仅由三张 D01 核心表承接：**

1. `tasks`
2. `executions`
3. `processes`

这三张表是三层运行身份的一对一映射。不得再创建 `clean_tasks`、`rag_tasks`、`clean_executions`、`rag_executions`、`smind_clean_process`、`smind_rag_process` 等按领域复制的平行状态表。

S01 已另外冻结独立的 `task_audits`；S02 又按 owner 裁决冻结独立的 `task_restarts`。因此若统计“从外部 Task ingress 到内部执行与人工重启治理”的**业务真相表总数**，当前最小集合是五张：

```text
tasks + task_audits + task_restarts + executions + processes
```

其中 `task_audits` 不属于三层运行状态表，也不能合并回 `tasks`；`task_restarts` 只保存人工重启因果/admission，不是 Execution/Process 替代物，也不独立推进 Task status。

### 5.2 不计入三张核心表的其他数据

| 数据类别 | 是否另有表 | 为什么不计入 D01 三表 |
|---|---:|---|
| Team Registry | 是，S01 已冻结 | 接入投影，不是一次任务执行状态 |
| Task Audit | 是，`task_audits` | immutable 上游业务审查，不是运行状态 |
| Task Restart | 是，`task_restarts`，S02 已冻结 | 外部人工重启的 immutable 因果/admission 账本，不是运行状态；status 从 Task join |
| IntakeSource/Snapshot/Item/Revision/Membership | 是，由S04冻结 | 摄入资产与集合血缘，不是Execution tree |
| IntakeArtifact/derived asset inventory | 是/可能，由S04/S13冻结 | 资产I/O生命周期，不是Process row |
| Vector records/filter metadata | 是，由 S08/S09/S12 冻结 | 最终知识资产；不能塞进 processes 作为唯一真相 |
| Domain events/logs | 是，由 S15 冻结 | append-only 证据；不替代 current projection |
| Queue/outbox records | 视本地队列实现，由 S03/S12 冻结 | transport/reliability mechanism；不能成为第四个执行身份 |
| 第三方 queue 私有表 | 可能 | 非 MKB 业务 schema，不受三层表数量约束 |

因此，“三张表”回答的是承接 `Task / Execution / Process` 三层业务状态所需的表数，不声称整个 MKB 只有三张表。

### 5.3 `tasks` 表的最小责任列族

| 列族 | 最小内容 |
|---|---|
| Identity | `team_uuid`, `task_uuid`, `trace_uuid`；复合 PK `(team_uuid, task_uuid)` |
| Intent | schema version、外部 `request_intent`、strict payload/fingerprint |
| API projection | aggregate status、progress summary、result/error summary |
| Execution pointer | `current_root_execution_uuid` nullable；不得设 singular current process |
| Scatter counters | expected/running/succeeded/failed/cancelled execution counts 或可等价重建的摘要 |
| Commands/concurrency | cancel/retry intent summary、revision |
| Lifecycle | received/created/updated/completed/deleted timestamps |
| Extension | `payload_extra` non-null JSON object |

关键约束：

- `current_root_execution_uuid` 由 MKB 内部 CAS 更新，外部不能传入或 PATCH；
- Task status/result 必须与 current root 的 durable truth 可对账；
- soft-delete 不级联物理删除 Audit、Execution 或运行证据。

### 5.4 `executions` 表的最小责任列族

| 列族 | 最小内容 |
|---|---|
| Identity | `execution_uuid` PK（UUIDv7） |
| Task ownership | `team_uuid`, `task_uuid` composite FK |
| Tree lineage | `root_execution_uuid`, `parent_execution_uuid` nullable, `retry_of_execution_uuid` nullable |
| Role/target | execution role、target type、target UUID/version/scope |
| Workflow | workflow key/definition UUID/version/digest、execution mode/case mode |
| Control state | status、phase、cancel intent/propagation state、revision/fencing generation |
| Current pointer | `current_process_uuid` nullable；终态后可转为 `final_process_uuid`/summary |
| Fan-out/fan-in | IntakeSnapshot/ChangeSet ref、expected/active/succeeded/failed child counts |
| Durable summary | process counts、retry totals、last/final error、artifact refs、vector publication proof |
| Lifecycle | created/started/updated/completed timestamps |
| Extension | `payload_extra` non-null JSON object |

建议索引/约束：

```text
PK (execution_uuid)
FK (team_uuid, task_uuid) -> tasks
FK parent_execution_uuid -> executions
FK root_execution_uuid -> executions
FK retry_of_execution_uuid -> executions
INDEX (team_uuid, task_uuid, created_at)
INDEX (root_execution_uuid, parent_execution_uuid)
INDEX (status, updated_at)
INDEX (target_type, target_uuid)
```

“每 Task 最多一个 active/current root”可以用 Task 的 current pointer + CAS 保证，或用 SQLite/Turso 支持的 partial unique index/active generation 设计保证；精确 DDL 由 S12 冻结。

### 5.5 `processes` 表的最小责任列族

| 列族 | 最小内容 |
|---|---|
| Identity | `process_uuid` PK（UUIDv7） |
| Execution ownership | `execution_uuid` FK，并冗余 `team_uuid/task_uuid/root_execution_uuid` 供隔离与运维查询 |
| Workflow position | process key/type、rank、action branch、definition/version ref |
| I/O | input refs/schema/hash、output refs/schema/hash、validation proof/ref |
| State | status、revision/fencing generation、available_at |
| Claim/lease | claim token、lease owner、lease expires at、heartbeat at |
| Retry | retry_count、max_retries、next_retry_at、retry reason/class |
| Error | stable error code、message、details/ref、retryable classification |
| Lifecycle | created/claimed/started/updated/completed timestamps |
| Extension | `payload_extra` non-null JSON object |

建议索引/约束：

```text
PK (process_uuid)
FK execution_uuid -> executions
INDEX (execution_uuid, rank, created_at)
INDEX (status, available_at)
INDEX (lease_expires_at, status)
INDEX (team_uuid, task_uuid)
INDEX (process_type, status)
CHECK retry_count >= 0 AND max_retries >= 0
```

Process 表保存**工序控制状态**，不保存每一个 vector unit 作为 Process row。一个 vectorize Process 可以对应一批 vector records；vector records 的主键、内容、embedding 和 filter metadata 由向量资产表持有。

### 5.6 为什么不需要更多关系表

| 候选表 | Verdict | 理由 |
|---|---|---|
| `task_executions` join table | 禁止首版创建 | Execution 已有 `(team_uuid, task_uuid)` FK；关系是 1:N，不是 M:N |
| `execution_relations` | 禁止首版创建 | root/parent/retry 三个自引用足以表达当前树；真正 DAG 需求出现前不预建 |
| `scatter_executions` | 禁止 | scatter是Execution role + parent/root lineage；集合truth归S04 Snapshot/Membership/ChangeSet |
| `attempts` | 禁止与 executions 并存 | `execution_uuid` 已承接完整执行尝试；双身份会产生歧义 |
| `clean_processes/rag_processes` | 禁止 | process type/workflow version 已表达业务分类；分表会重建 legacy 漂移 |
| `vec_processes` | 禁止作为运行控制表 | vector unit 是向量资产/批处理数据，不是三层中的 Process identity |
| `task_restarts` | **允许且必需** | S02-v1.0 经 owner 确认的人工重启 causation/admission SSOT；不构成新运行身份，不复制 Task status |

---

## 6. 具体执行方案清单

### 6.1 `D01-E01` — 建立三层 domain modules 与依赖方向

```text
Task application/API
    ↓ command / query ports
Execution orchestrator
    ↓ instantiate / transition
Process runner + local queue adapter

向上只发布 outcome/summary；向下只发布 command/control。
```

强制 dependency rule：Task domain 不导入 worker/queue DTO；Process runner 不直接改 Task row；所有跨层更新通过 application transition service 和同一持久事务/可对账事件完成。

### 6.2 `D01-E02` — 将 Task 建成外部稳定投影

- 保留 S01 的 composite identity、Audit、idempotency、revision、polling 与 command authority；
- 将 S01 的 `task_type` 严格解释为**外部 request intent**，不能作为内部 workflow/process classification；
- 添加 current root 指针与可重建的 execution aggregate；
- Task response 可以包含 execution summary/counts，但不得要求外部用 execution_uuid 才能知道请求终态；
- 内部诊断可以按 execution_uuid 查询，仍不把其变成 caller-created resource。

### 6.3 `D01-E03` — 建立 durable Execution tree

- single root同时是IntakeItem/Revision execution；
- scatter root是IntakeSource/Snapshot controller，child是Item/Revision execution；
- 所有 children 在创建时固定 task/root/parent/target/workflow version；
- fan-out scheduling与Snapshot/ChangeSet required set必须来自同一已提交acceptance边界；
- root child counters是projection，必须能从Execution rows + SnapshotMembership/ChangeSet对账；
- manual full retry 新建 root tree，不重写旧 tree。

### 6.4 `D01-E04` — 建立统一 Process transition path

每次 Process transition 至少需要原子或可严格对账地完成：

1. 校验 expected revision/fencing token；
2. 校验合法有向边与 type-specific guard；
3. 更新 Process current projection；
4. 写 append-only event/error evidence；
5. 必要时更新 Execution summary/current pointer；
6. 必要时产生下一 Process/fan-out scheduling intent；
7. commit 后才允许 queue adapter 唤醒新工作。

禁止 worker 直接更新 Task 成功；禁止 queue send 成功日志充当 transition commit。

### 6.5 `D01-E05` — 实施三层 retry 语义

| 场景 | Task UUID | Execution UUID | Process UUID | 计数/血缘 |
|---|---|---|---|---|
| queue redelivery | 不变 | 不变 | 不变 | delivery count 可记录，但不等同 retry |
| lease expiry recovery | 不变 | 不变 | 不变 | fencing generation 递增；旧 runner 失效 |
| automatic process retry | 不变 | 不变 | 不变 | `retry_count + 1`，受 max_retries |
| manual full execution retry | 不变 | 新 root/必要 children | 全新 | `retry_of_execution_uuid` 指向旧执行 |
| 新的外部业务请求 | 新 task_uuid | 新 | 新 | 不与 retry 混用 |

### 6.6 `D01-E06` — 实施散射 fan-out/fan-in fence

- child candidate 必须先经过 schema、stable key 与 hash 校验；
- accepted Snapshot/ChangeSet必须明确本次expected/required/skipped/absence集合；
- 每个 required child 至多创建一个本 generation 的 active Execution；
- fan-in查询必须带root_execution_uuid + intake_snapshot_uuid/change_set_digest；
- root 进入成功前重新验证 required count、terminal states 和 publication proofs；
- crash发生在Snapshot/ChangeSet/outbox commit后、queue wake-up前时，recovery必须可补发；
- crash 发生在部分 child 创建后时，幂等 uniqueness 必须补齐而非重复创建。

### 6.7 `D01-E07` — 实施 Process terminal-summary / cleanup-eligibility fence

建议清理流程：

```text
Execution terminal
  → semantic recovery/grace window elapsed
  → verify no retry/cancel/compensation command pending
  → complete and validate durable Execution terminal summary
  → clear/replace dangling current_process_uuid
  → archive or delete eligible Process projections
  → retain Event/Log according to S15 policy
```

Execution durable summary 至少包含：

- workflow/config/model/prompt versions or digests；
- required/succeeded/failed/cancelled process counts；
- total retry count 与 exhausted process key；
- final process/phase；
- final error code/message/details reference；
- input/output IntakeArtifact/derived asset references and digests；
- vector/filter publication proof reference；
- started/completed time 与主要 latency metrics。

### 6.8 `D01-E08` — 回填 S01 与 spec-index

D01 不在本文中静默修改已 accepted 的 S01；但后续 truth freeze 必须显式 reopen 以下口径：

| S01 位点 | 当前口径 | D01 回填 verdict |
|---|---|---|
| `S01-T014` | retry 产生新 `attempt_uuid` | 用新 `execution_uuid` 承接整次执行 retry；删除重叠 Attempt identity |
| `S01-T023/T024/T026` | 外部字段/集合名为 `task_type` | wire compatibility 可暂留字段名，但语义应改称 `request_intent`；它不定义 RAG 工序 |
| `S01-T027` | Task/IntakeItem/Trace/Attempt 分离 | 改为 Task/Intake identities/Trace/Execution/Process 分离 |
| `S01-E02/E07` | `task_attempts` / retry command 生成 Attempt | 改为 executions 与 retry lineage |
| `spec-index S02/S03` | Task API 与 Workflow Engine 顺序依赖 | D01 作为两者共同前置；S02 拥有 Task，S03 拥有 Execution/Process |

在 S01 被正式 reopen 前，任何实现不得同时创建 `task_attempts` 和 `executions` 两套表来“兼容两边”；应先完成 truth change record。

---

## 7. 事实反例与风险台账

### 7.1 事实反例台账

| Counterexample ID | 错误叙事/做法 | 事实与 D01 订正 |
|---|---|---|
| `D01-C01` | “Task 必须直接包含 clean/rag/structurize/vectorize 状态，否则不够 RAG-specific。” | Owner 已将 Task 明确抽离为 ACK/CRUD；RAG specificity 属于 Execution phase 与 Process type。 |
| `D01-C02` | “一个 Task 只有一个 current execution_uuid 就足够表达散射。” | Task 可以有一个 current **root**，但 root 下必须有 N child Executions；不能把 N 个运行覆盖成一个 job。 |
| `D01-C03` | “process_uuid 就是 structurize/vectorize 之类的分类。” | UUID 是实例；分类必须另设 process key/type。 |
| `D01-C04` | “clean 完成后像 legacy 一样生成新的 RAG Execution。” | legacy 因跨 dispatcher/job 边界重生 job UUID；MKB 单体用同一 Execution 贯穿一个目标，Process 表达领域工序。 |
| `D01-C05` | “复制三张 legacy process 表最安全，因为已经生产验证。” | 三表体现历史增量演进：clean/rag step control 与 vec unit queue 职责不同。MKB 应统一控制表、分离向量资产。 |
| `D01-C06` | “Process 可定期清理，所以它不是状态真相。” | 活跃期 Process 是精确控制真相；只有Execution terminal summary完整且全部retry/recovery/cancel/outbox围栏关闭后才可清理。 |
| `D01-C07` | “pending_count=0 或收到成功 callback 就能完成 Task。” | legacy 此检查存在盲区；MKB 必须验证 expected vector set、failed/in-progress、filter metadata 与 publication proof。 |
| `D01-C08` | “本地 queue item 就是 task/process。” | Queue 是 transport；durable Process 才是 claim、retry 和恢复 SSOT。 |
| `D01-C09` | “Execution parent-child 可以替代Intake集合/资产关系。” | Execution tree描述一次运行；SnapshotMembership与Item/Revision描述长期集合和资产血缘，生命周期不同。 |
| `D01-C10` | “为了查询方便，Task 应直接保存 current_process_uuid。” | 散射并发时有多个 current processes；Task 只能保存 current root 和 aggregate，current process 属于每个 Execution。 |

### 7.2 风险台账

| Risk ID | 风险 | 严重度 | 预防/围栏 |
|---|---|---:|---|
| `D01-R01` | `attempt_uuid` 与 `execution_uuid` 并存导致 retry 双真相 | P0 | reopen S01；只保留 Execution durable identity |
| `D01-R02` | Task status 与 Execution 集合漂移 | P0 | transition service + semantic repair + projection rebuild test |
| `D01-R03` | Snapshot/ChangeSet与child scheduling非原子，漏任务或重复任务 | P0 | S04 canonical acceptance transaction + outbox/fence |
| `D01-R04` | Process 清理留下 dangling current pointer | P0 | cleanup FK/precondition + terminal-summary completion transaction |
| `D01-R05` | 只聚合已创建 child，漏掉应创建但未创建的 child | P0 | fan-in 对照 persisted expected set，不以 count query 猜测 |
| `D01-R06` | 旧 lease holder 在恢复后继续写，产生双执行 | P0 | fencing generation/token，所有完成提交校验 token |
| `D01-R07` | Process type 过度 generic，RAG 业务验证再次丢失 | P0 | versioned RAG-specific process registry + output schema/guard |
| `D01-R08` | 将 vector units 全塞入 processes，导致表膨胀且 retention 冲突 | P1 | Process 记录批次/工序；Vector domain 持有资产明细 |
| `D01-R09` | Task 对外暴露内部 UUID 后，上游开始编排 Process | P1 | execution/process 仅 internal read/diagnostic；外部命令仍以 Task 为边界 |
| `D01-R10` | single 与 scatter 使用两套 engine，行为漂移 | P1 | 同一 Execution/Process engine；差异只在 root role 和 child fan-out |
| `D01-R11` | all-required fan-in 遇到部分失败后永久卡 running | P0 | terminal aggregation policy + retry exhaustion + durable repair trigger |
| `D01-R12` | local filesystem locator泄漏绝对路径进API/DB identity | P1 | logical Intake/derived asset ref + relative locator + storage adapter |

### 7.3 明确禁止的实现方向

1. 禁止把 Task、Execution、Process 合并为一张多态表。
2. 禁止让外部 caller 指定或推进 execution/process status。
3. 禁止把一个 Task 限制为只能有一个 Execution row。
4. 禁止用 Task 的 singular current process 表达散射并发。
5. 禁止同时引入 Attempt 与 Execution 两个完整执行身份。
6. 禁止按 clean/rag/vectorizer 复制多套 Process 状态表。
7. 禁止让 queue ack、HTTP callback 或日志文本直接决定业务成功。
8. 禁止在 publication proof 前把 Execution/Task 标为成功。
9. 禁止在 Execution 终态摘要完成前清理 Processes。
10. 禁止用Execution parent/child取代IntakeSnapshotMembership或Item/Revision provenance。
11. 禁止把 R2 key、Cloudflare binding 或 Durable Object ID 写成 MKB 核心身份。
12. 禁止把 `payload_extra` 用来隐藏 process type、status、retry budget 或 publication proof。

---

## 8. 测试与验收台账

> 本节描述实现必须交付的测试；本文不声称这些实现当前已经存在。

| Acceptance ID | 层级 | 场景 | HARD 断言 |
|---|---|---|---|
| `D01-A01` | Contract | 外部 Task Create 携带 execution_uuid/process_uuid/status | strict reject；无业务行 |
| `D01-A02` | Identity | 创建 Task 后内部生成 Execution/Process | 三类 UUID 全部不同；内部均 UUIDv7；task 仍按 team 复合寻址 |
| `D01-A03` | Single flow | 单IntakeItem/Revision完整运行 | 1 Task、1 current root、0 child、N Processes；最终proof上卷 |
| `D01-A04` | Scatter | API 产生 N 个 required children | 1 Task、1 root、N child Executions；每 child 有独立 current Process |
| `D01-A05` | Scatter zero | API合法产生0 memberships | accepted Snapshot required=0；按S04/Workflow policy明确终态，不得永远running |
| `D01-A06` | Fan-out crash | Snapshot/ChangeSet commit后、部分child创建时crash | recovery补齐到恰好N；不重复child Execution |
| `D01-A07` | Fan-in | 一个 required child 仍 running，其余成功 | root/Task 不得成功 |
| `D01-A08` | Fan-in proof | children 状态均 success，但一个 publication proof 缺失/无效 | root/Task 不得成功；对账报错 |
| `D01-A09` | Auto retry | Process 可重试失败后再次执行 | process_uuid/execution_uuid/task 不变；retry_count 增加 |
| `D01-A10` | Queue redelivery | 同一 queue message 重复送达 | 最多一个合法 claim；不新增 Process，不重复业务提交 |
| `D01-A11` | Lease fencing | lease 过期后新 runner claim，旧 runner 后到提交 | 旧 fencing token 被拒绝；新 runner 独占推进 |
| `D01-A12` | Retry exhaustion | retry_count 达 max_retries | 不再 claim；Process terminal failed；Execution 可归约而非卡住 |
| `D01-A13` | Full retry | 对 terminal failed Execution 执行整次 retry | Task 不变；新 Execution/Processes；retry_of 指向旧 Execution |
| `D01-A14` | No dual identity | schema/migration 扫描 | 不存在与 Execution 同义的 `task_attempts/attempt_uuid` 业务身份 |
| `D01-A15` | Cancel | scatter 运行中取消 Task | cancel 传播 root/children/active Processes；无新 claim；收敛后才 Task cancelled |
| `D01-A16` | Process cleanup | terminal Execution 过 retention | 先完成并验证terminal summary；无 dangling current_process FK；Task/Execution 仍可完整查询摘要 |
| `D01-A17` | Event retention | Process projection 被清理 | 按 S15 策略保留的 event/log 不被隐式级联删除 |
| `D01-A18` | Projection repair | 故意篡改 Task counters 后运行semantic recovery scanner | 从 Executions 重建正确 projection，并留下修复事件 |
| `D01-A19` | Resource/runtime split | 同一IntakeItem/Revision多次rebuild | Intake identity不变且不新增Revision；每次full run有新Execution lineage |
| `D01-A20` | Table architecture | D01 schema review | 核心状态恰为 tasks/executions/processes；无 clean/rag 分表、无 relation/join 冗余表 |
| `D01-A21` | RAG specificity | Process registry/schema scan | 存在 clean/structurize/construct/vectorize/validate 业务类型和各自 guard |
| `D01-A22` | Vector separation | 一个 vectorize Process 产生 M 个 vectors | Process row 不膨胀为 M 个假 Process；M 个向量由向量资产域承接 |
| `D01-A23` | Local I/O | Process 输入输出持久化 | 只保存 logical refs/relative locators/hash；无 R2 binding、DO ID、绝对路径 API identity |
| `D01-A24` | S01 migration | truth/schema gate | S01 Attempt 口径已 reopen 或 implementation gate 阻止双模型落地 |

### 8.1 验收证据要求

每个 HARD 断言至少提供：

- Turso/SQLite integration test；
- 状态转移前后行快照；
- queue redelivery/crash/fault injection 证据；
- event/log correlation（team/task/trace/execution/process）；
- single 与 scatter 两套 golden scenario；
- schema/architecture gate，阻止 banned tables/fields；
- Process cleanup 前后 Task/Execution polling snapshot。

---

## 9. Reference-anchor 台账

> Anchor 是亲验事实，不是迁移代码清单。`保留`表示保留业务原理，`改写`表示以 MKB 三层模型重构，`删除`表示不得带入新系统。

| Anchor ID | `file:line` | 亲验事实 | D01 verdict |
|---|---|---|---|
| `D01-RA01` | `legacy-family/smind-contexter/core/schemas_smcp.ts:103-166` | SMCP 明确分离 workflow start、step start/restart/callback，并携带 job/process-step、workflow、input/output/error。 | 保留信息分面；改写为 Execution/Process 本地 contract，删除跨 Worker callback SSOT。 |
| `D01-RA02` | `legacy-family/smind-contexter/core/schemas_smcp.ts:249-277` | v1.4 后补 STEP_RESTART、retry_count 与 max retry 止血，证明恢复是生产必需。 | 保留 retry/max_retries；自动 retry 落 Process，整次 retry 落 Execution。 |
| `D01-RA03` | `legacy-family/smind-contexter/core/schemas_smcp.ts:282-359` | Clean workflow 把异构输入变为纯文本，并通过 config 链接 RAG workflow。 | 保留 clean → RAG 工序链；同一目标由一个 Execution 贯穿。 |
| `D01-RA04` | `legacy-family/smind-contexter/core/schemas_smcp.ts:444-470` | legacy Clean 完成后创建新的 RAG job_uuid，体现跨 dispatcher 的历史身份断裂。 | 删除 job 重生；MKB 用 Process phase 切换，必要 retry 才新建 Execution。 |
| `D01-RA05` | `legacy-family/smind-contexter/core/schemas_smcp.ts:565-676` | 权威 LS-RAG workflow 是 Structurizer → Constructor → Vectorizer/Index，并通过 rank/input/output 串接。 | 保留为 RAG-specific Process types 与 versioned Workflow Definition。 |
| `D01-RA06` | `legacy-family/smind-contexter/core/schemas_smcp.ts:692-768` | 每步output成为下一步input，constructor一进多出layered与vector-ready artifacts。 | 保留声明式I/O与outcome；本地logical asset refs替代R2 keys。 |
| `D01-RA07` | `legacy-family/smind-console/db/06-process-tracking.sql:21-80` | clean process 保存 job/file/workflow/step、输入输出、状态、retry、时间与结构化错误。 | 保留列族原则；统一进入 processes。 |
| `D01-RA08` | `legacy-family/smind-console/db/06-process-tracking.sql:110-170` | rag process 结构对齐 clean，并后补 is_child_file/parent_file_uuid。 | 保留 child 生产需求；运行血缘改为 Execution tree，资源血缘交 S04。 |
| `D01-RA09` | `legacy-family/smind-console/db/06-process-tracking.sql:192-258` | vec process 同时是 vector unit 数据、队列状态和 filter metadata 载体。 | 拆分：Process 记录 vectorize 工序控制，Vector domain 保存 unit/embedding/filter 资产。 |
| `D01-RA10` | `legacy-family/smind-clean-dispatcher/flows/finalizer.ts:96-165` | Clean finalizer识别scatter、计算diff并持久化parent/child relations。 | 将集合/diff/fan-out原理升级为S04 Snapshot/Membership/ChangeSet；删除后补双文件表形态。 |
| `D01-RA11` | `legacy-family/smind-clean-dispatcher/flows/finalizer.ts:195-269` | scatter targets 通过 Promise.all 并发，每 child 新建 RAG job_uuid 并携带 parent/hydration/control。 | 保留并发 child execution；每 child 新 Execution，root 统一 fan-in。 |
| `D01-RA12` | `legacy-family/smind-rag-dispatcher/flows/orchestrator.ts:96-156` | dispatcher 在发送前先创建 pending RAG process step，记录 child/parent、input、retry 与 error 列。 | 保留 durable-before-dispatch 原则；改写为统一 Process transition/outbox。 |
| `D01-RA13` | `legacy-family/smind-rag-dispatcher/flows/orchestrator.ts:268-304` | callback 完成时更新当前 step，并按 workflow definition 找下一步；失败写结构化错误。 | 保留 outcome 驱动编排；本地 runner/outcome 取代跨 Worker callback。 |
| `D01-RA14` | `legacy-family/smind-skill-rag-structurizer/flows/processor.ts:47-99` | Worker 将 STEP_START/STEP_RESTART 统一解析为 `ConsumableTask`，说明 legacy task 实际是一个 step work item。 | 证明术语不可照搬；MKB 外部 Task 与内部 Process 必须分开。 |

### 9.1 Reference 复验命令

```bash
nl -ba legacy-family/smind-contexter/core/schemas_smcp.ts | sed -n '103,180p;240,470p;565,768p'
nl -ba legacy-family/smind-console/db/06-process-tracking.sql | sed -n '1,285p'
nl -ba legacy-family/smind-clean-dispatcher/flows/finalizer.ts | sed -n '96,270p'
nl -ba legacy-family/smind-rag-dispatcher/flows/orchestrator.ts | sed -n '90,320p'
nl -ba legacy-family/smind-skill-rag-structurizer/flows/processor.ts | sed -n '40,110p'
```

---

## 10. Domain verdict

### 10.1 最终评价

**Verdict：`GO — adopt the owner-originated Task / Execution / Process split as MKB's runtime backbone`。**

这套切分是正确的，而且比复制 legacy-family 的 job/process 形态更适合 MKB。它同时解决了外部契约稳定性、单文件执行、API 散射、durable 内部查询、工序级重试和短期 Process 清理六个互相冲突的需求。

详细评价如下：

| 评价面 | Verdict | 理由 |
|---|---|---|
| 领域内聚 | `PASS` | Task 只负责 API/ACK，Execution 只负责一次完整业务运行，Process 只负责具体工序，状态所有权清晰。 |
| RAG 专属性 | `PASS with condition` | Task 可以通用，但 Execution phase、Workflow Definition、Process type/guard 必须明确 clean/LS-RAG/vector/index；若下游继续 generic，则本方案实现失败。 |
| 单文件适配 | `PASS` | 一个 root Execution 即可贯穿 clean → RAG → publication validation。 |
| 散射适配 | `PASS` | 一个 root controller + N child Executions 原生表达 fan-out/fan-in，不再给单一 job 指针打补丁。 |
| Retry/恢复 | `PASS` | 自动 retry 留在 Process，整次 retry 新建 Execution，Task 不变；身份与预算层级不再混淆。 |
| Durable 查询 | `PASS` | execution_uuid 是内部稳定查询锚点，Process 清理后仍保留执行摘要与证明。 |
| 本地化适配 | `PASS` | 三层模型与 Cloudflare topology 无关，可由 Turso + local filesystem + lightweight queue 实现。 |
| 数据表复杂度 | `PASS` | 三张核心状态表足够；既避免单表多态，也避免 legacy 按领域分表漂移。 |
| 与 S01 一致性 | `PASS` | S01-v1.5已废止Attempt并将`task_type`替换为external `request_intent`；D02校准继续禁止旧alias回流。 |
| 实施风险 | `MANAGEABLE / P0 fences required` | 主要风险集中在Snapshot acceptance原子性、lease fencing、投影对账、publication proof与Process cleanup。 |

### 10.2 Verdict 的关键理由

1. **它承认外部请求与内部执行不是同一件事。** 外部 Task 可以稳定轮询，而内部 RAG 流程可以演进、分支、重试。
2. **它给散射提供了正确的基数。** 一次API请求仍是一个Task，但每个required IntakeItem/Revision有自己的durable Execution，分母来自accepted Snapshot/ChangeSet。
3. **它让 retry 有明确层级。** Process retry 解决短暂工序失败；Execution retry 解决一次完整运行失败；新 Task 代表新的外部业务请求。
4. **它保留了 legacy 的生产经验，而没有继承平台负债。** 状态、I/O、控制、错误、retry、max_retries、fan-out/fan-in 都被保留；Worker callback、D1/R2/DO 与 clean/rag job 断裂被删除。
5. **它允许 Process 清理但不牺牲审计。** 精细运行明细只能在terminal summary与cleanup eligibility成立后按策略归档/清理；Execution仍是durable内部执行账本，Task仍是稳定外部账本。
6. **它把 RAG 的成功边界放在正确层级。** Vector/filter publication 由 Process 验证、Execution 保存 proof、Task 聚合，而不是由 Task 自己猜测内部是否成功。

### 10.3 GO 的强制条件

本 Verdict 的 `GO` 不是无条件通过。实现前必须满足：

1. S01已废止`attempt_uuid/task_type`双义；实现gate必须持续禁止Attempt身份与旧alias回流；
2. S02 只冻结 Task API/lifecycle/aggregate，不再次吞入 Process 状态；
3. S03 必须明确 Execution tree、Process registry、state machines、claim/lease/fencing/retry/recovery；
4. S04必须提供durable IntakeSnapshot/Membership/ChangeSet acceptance truth；S05提供typed CandidateSet、mandatory preflight、ExecutionGate与exact binding；
5. S08/S09/S12 必须定义可机器验证的 vector + filter metadata publication proof；
6. S15 必须定义 Process projection 与 Event/Log 的不同 retention；
7. 任何 Process 物理清理实现都必须先通过 `D01-A16/A17`；
8. table architecture gate 必须阻止 Attempt 表、clean/rag process 分表和 Task current_process 指针回流。

### 10.4 当前仍未被 D01 声称为已解决的事项

S02-S05已经关闭Task、Workflow、Intake与clean/preflight/HITL语义；仍由后续Spec冻结的是：

- 每个S06-S09 process capability的exact input/output/proof与retryable error matrix；
- root/child Execution、S05四组durable职责、CandidateSet与outbox的exact Turso DDL/index/transaction（S12）；
- local queue具体选型、wake driver与capacity benchmark（S12/17）；
- logical handle、atomic write、staging/orphan/reference-protected GC（S13）；
- model/prompt/provider exact registry与fallback（S11/S14）；
- Process/Event/Log/gate evidence retention数值、waiting SLA/timeout/alerts/runbook（S15）；
- secret/egress/allowlist/review decision authority（S16）；
- scatter partial-success未来是否开放；v1继续all-required且无Task partial-success状态。

这些事项不得推翻D01三层身份、责任归属、1:N散射、状态归约方向和三张核心运行状态表，也不得删除S02 restart causal truth或把S05 gate改为第四层runtime identity。

### 10.5 一句话结论

> **Task是上游看见的请求账本，Execution是MKB内部durable的一次业务运行账本，Process是可执行、可重试、可清理的工序账本；single Intake是一棵单根执行，API scatter是一棵root + N children执行树，而长期集合与资产真相由S04 Intake graph独立持有。**

---

## 11. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `D01-v1.0` | `2026-07-15` | `MKB owner + Codex` | `accepted architecture direction` | 固化 owner 主动提出的 Task/Execution/Process 三层切分；完成 single/scatter、retry/cleanup、三表架构、legacy evidence 与 GO verdict。 |
| `D01-v1.1` | `2026-07-15` | `MKB owner + Codex` | `accepted / S02-calibrated` | 接收 S02-v1.0 回流：三张核心运行表不变；新增 `task_restarts` 因果/admission truth，将 Task ingress/runtime/restart 最小 durable 业务真相集合由四张校准为五张。 |
| `D01-v1.2` | `2026-07-15` | `MKB owner + Codex` | `accepted / S02+S04-calibrated` | 接收S04-v1.0：将Source/Document/Version/manifest资源口径校准为IntakeSource/Snapshot/Item/Revision/Membership；确认Intake不是第四层runtime identity，single/scatter fan-in改以accepted Snapshot/ChangeSet为分母，rebuild不创建Revision。 |
| `D01-v1.3` | `2026-07-16` | `MKB owner + Codex` | `accepted / S02+S04+S05-calibrated` | 接收S05-v1.0：Preflight归统一Process capability；human review归Execution waiting gate且不新增runtime identity；Execution锁定S05 binding；single/scatter加入preflight、gate和same-Execution resume；修正Execution无retrying状态并更新未决下游边界。 |
| `D01-v1.4` | `2026-07-18` | `MKB owner + Codex` | `accepted / D02-state-calibrated` | 依据S02-S05已冻结事实完成状态族校准：Task/Execution/Process exact states与phase/outcome/readiness/Intake/Gate分账；以S05 exact capability keys取代早期coarse intake process示例；将Process compaction旧词校准为terminal-summary/cleanup-eligibility；Execution target与S08/S09职责按D02-v1.0明确移交对应下游，不扩大v1。 |
| `D01-v1.4-cal` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S06-v1.0：GenerationArtifact非第四层runtime；structurize仍为Process capability；structure rebuild不改三层身份与Task/serving语义。 |
| `D01-v1.4-cal-s12` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S12-v1.0：持久化兑现三层模型；不改状态机；outbox/claim为物理机制。 |
| `D01-v1.4-cal-s13` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S13-v1.0：确认本地 I/O adapter 与 logical ref；G-11 closed。 |
| `D01-v1.4-cal-s08` | `2026-08-12` | `MKB owner + Codex` | `accepted / S08-calibrated` | 接收S08-v1.0：exact `lsrag.vectorize` 取代 coarse `lsrag.vectorize_index`；publication 仍独立 S09；拓扑/T023/工序表回填。 |
