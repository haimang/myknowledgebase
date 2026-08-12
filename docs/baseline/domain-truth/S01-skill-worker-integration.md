# S01 — Standalone Leaf-Worker Integration & Future Skill-Worker Adapter

> **项目**：`myknowledgebase`（MKB）
> **Domain / 子系统**：`D1 / S01` 上游集成
> **文档性质**：`specification / domain-truth`
> **文档状态**：`accepted / D01+S02+S04+S05+D02-state-calibrated`（S01域内真相已获owner接受，并已按runtime、Task、Intake、clean/preflight/HITL与状态族边界完成校准；全系统truth layer尚未frozen）
> **Truth 版本**：`S01-v1.5`
> **日期**：`2026-07-18`
> **权威输入**：Owner-gated Q1–Q26、`D01-v1.4`、`S02-v1.3`、`S03-v1.3`、`S04-v1.2`、`S05-v1.1`、`S06-v1.0`、`03-nano/workers/skill-core`代码事实与`legacy-family/` reference anchors
> **上游索引**：`docs/baseline/spec-index.md`
> **上游架构真相**：`docs/baseline/domain-truth/D01-task-execution-process-flow.md`（`D01-v1.4`）
> **下游消费者**：`S02` Task API、`S03` Workflow、`S04` Intake Asset Lifecycle、`S12` Persistence、`S15` Observability、`S16` Security、跨系统拓扑 `17`

> **约束级别**：本文中的“必须 / 禁止 / 仅允许”是后续设计与实现的强制约束；“应当”是默认约束，若要偏离必须 reopen S01；“可以 / 建议”不是冻结的不变量。

> **v1.1 校准声明**：D01 已由 owner 冻结为 Task / Execution / Process 的上游架构真相。本版正式 reopen 并取代 v1.0 中的 `attempt_uuid / task_attempts` 口径；同时把外部字段 `task_type` 校准为 `request_intent`。旧词不再是兼容别名，也不得与新模型并存。历史判断保留在修订记录中，不再具有规范性。

> **v1.2 校准声明**：S02-v1.0 已接受并冻结 Task 六态、scatter 聚合、full retry generation、atomic rebuild 新 Task 与独立 `task_restarts`。本版只回填该下游真相：原四张核心 Task/运行表不变，启用外部人工重启后的最小 durable 业务真相集合更新为五张；Task 仍是运行状态 SSOT。

> **v1.3 校准声明**：S04-v1.0已冻结五类Intake identity与greenfield边界。本版将MKB新契约中的`document.* / document_uuid / Source/Document/Version`校准为`intake.* / intake_item_uuid / IntakeSource/Snapshot/Item/Revision`；legacy代码锚中的原名只作证据，不构成兼容别名。

> **v1.4 校准声明**：S05-v1.0已冻结mandatory preflight与Execution-owned human gate。Task polling必须可表达安全的`action_required`投影，并提供受控gate decision语义面；caller仍不得创建、PATCH或直接寻址Execution/Process。Gate command以team+Task+gate身份和target digest表达，不开放内部状态写面。

> **v1.5 状态校准声明**：本版接收D02-v1.0对既有冻结事实的共有域镜像及`T-O-86..92`校准纪律，不改变S01公共Contract。上游可见状态仍只有S02 Task六态；`action_required`、result readiness、TaskItem outcome、soft-delete visibility、Execution phase/waiting、Process retry与Intake lifecycle全部是正交事实。S01不新增公共状态、URI或权限，也不允许caller利用任一projection反向推进内部状态。

> **S06校准声明**：`S06-v1.0`允许 Task-scoped **只读** generation-artifacts / pointers 投影（`T-O-79`）；不开放 Execution/Process 写面、不开放用户 generation 精修产品路径。Generation 历史不是 Task 状态机。

> **S12校准声明**：`S12-v1.0` 兑现 Task+Audit 原子创建（TX-01）与 team-scoped 持久化；公共 Contract 不暴露 SQL/Turso。

---

> **S13校准声明**：`S13-v1.0` 冻结 v1 本地 `object_root` + `ObjectStorePort`、`mkbobj:v1` handle、team-scoped CAS、bytes-first、同库 catalog/ref/purpose、verify-on-read、周期 GC 与 identity readiness。本文件业务语义不变；对象 I/O 必须经 S13 Port，禁止 path/R2 key 进入契约。
>
> **S15 readiness 校准（S15-v1.1）**：`not ready`（HealthAggregator）时 **禁止** 新 Task Create 入口；须 fail-closed 查 Ready 标志 → HTTP **503**（非 security_audit）。token→schema→team→幂等序 **之前或并列** 增加 readiness gate（S15-T043）。细节权威=`domain-truth/S15-observability-reliability.md`。

## 1. Domain 介绍

### 1.1 Domain 的价值定位

S01 定义 MKB 与所有上游调用者之间的**唯一服务边界**。它解决的不是“如何迎合某个已经存在的 orchestrator 协议”，而是以下问题：

1. MKB 以什么身份存在；
2. 上游必须如何标识 team、task、trace 与 audit；
3. 一项任务在什么条件下才被 MKB 接受；
4. MKB 与上游分别拥有哪部分状态和状态变更权；
5. 未来若 MKB 注册为 skill-worker，适配应发生在哪里；
6. 哪些平台职责不得重新渗入 MKB。

MKB的冻结定位是：**一个单体部署、内部有状态、面向LS-RAG的standalone leaf-worker**。它通过自己的版本化API接收Task，在内部持有Task、Execution、Process、Workflow definition、Intake truth、LS-RAG derived assets、index和event状态；它不拥有用户平台、团队成员关系、计费、UI或上游会话。

按 D01，外部 Task lifecycle 与内部 Workflow lifecycle 必须分开：Task 是 ACK/CRUD/聚合状态边界；Execution 是一次 durable workflow run；Process 是该 Execution 内的具体工序实例。S01 只定义上游如何合法创建和操作 Task，不允许上游借 Task Contract 创建或推进 Execution/Process。

### 1.2 在整体拓扑中的位置

```text
上游调用者（已知调用者：03-nano/orchestrator-core；也允许其他内部 orchestrator）
    │
    │  MKB Contract v1
    │  simple internal token
    │  caller-supplied team_uuid + task_uuid + trace_uuid + immutable audit
    ▼
MKB standalone leaf-worker（单体应用 / 单一发布单元）
    ├── Team Registry（上游 team 的本地投影与接入门）
    ├── Task API（异步任务、轮询、命令）
    ├── Task Audit（上游业务审查快照，独立且不可变）
    ├── Execution / Process / Workflow / Queue（MKB 内部状态）
    ├── LS-RAG engine（知识构建与检索）
    └── Persistence / Storage / Model adapters

未来可选：Skill-Worker Adapter
    上游 skill 协议 ──翻译──> MKB Contract v1
    （适配层服从 MKB；不得反向污染核心契约）
```

### 1.3 Scope fence

本 Domain 覆盖：

- leaf-worker 身份和独立服务边界；
- 上游调用责任与 MKB 责任；
- Team Registry 的最小职责；
- Task Create 的稳定标识、外层 envelope、幂等边界；
- Task 与内部 Execution/Process 的权限边界及身份分离；
- Task Audit 的原子性、独立存储与不可变性；
- 轮询优先的结果交付方式；
- 简单内部 token 的权限口径；
- 未来 skill-worker 接入的防腐边界；
- 下游 spec 必须继承的跨系统不变量。

本 Domain 不负责完整定义：

- Task 的全部状态词汇、取消竞态、retention 和响应体细节（`S02`）；
- Execution tree、workflow process、lease、retry、queue 和 semantic recovery/repair（`S03`）；
- IntakeSource/IntakeSnapshot/IntakeItem/IntakeRevision/IntakeArtifact的完整模型（`S04`、`S13`）；
- Turso DDL、事务驱动和 migration 细节（`S12`）；
- 日志、内部 event 和 trace 的完整 envelope（`S15`）；
- token 的存放、轮换、网络暴露和限流细节（`S16`）；
- 03-nano 当前 NACP/skill-core 协议的兼容实现。

#### 1.3.1 Caller-visible 状态边界

| 对外可见事实 | S01允许的语义 | 权威来源 | 明确禁止 |
|---|---|---|---|
| Task `status` | `queued/running/cancelling/succeeded/failed/cancelled` | S02 | clean/RAG phase、`waiting/retrying/reviewing`别名 |
| result readiness | `not_ready/ready/terminal_failed/terminal_cancelled` | S02 | 用404或Task status猜结果存在性 |
| `action_required` | open ExecutionGate的bounded安全投影 | S02/S05 | 新Task状态、Execution/Process/fence泄漏 |
| TaskItem outcome/counts | scatter generation的分页结果投影 | S02 | IntakeItem lifecycle或child状态SSOT |
| soft-delete | Task查询可见性/tombstone | S02 | 执行状态、Intake delete、物理清理 |

Execution/Process exact状态、phase、waiting reason、PreflightOutcome、Gate状态、Intake lifecycle、CandidateSet staging以及latest/serving/current pointer可以被内部诊断面并列读取，但不属于MKB Contract的Task status字段，也不能由普通caller直接写入。

### 1.4 Domain 的完成定义

S01 只有在下列条件全部成立时才算在实现层完成：

1. Team Registry 与 Task/Audit ingress 按本文契约交付；
2. 所有边界模型执行严格运行时校验；
3. Task + Audit 原子创建、幂等重放和冲突路径通过数据库集成测试；
4. 上游只能表达 request intent，不能越权创建或写内部 Execution/Process 状态；
5. polling 可以完整读取任务状态与结果引用；
6. 无用户、membership、billing、UI 或 03-nano 私有协议泄漏进入核心 domain；
7. single/scatter Task 均能通过 current root Execution 聚合，Process/Execution 未提交 proof 前 Task 不得成功；
8. §6 的强制验收项全部通过。

---

## 2. 真相层

### 2.1 真相层使用纪律

本节是 S01 的 SSOT。真相来源分为三类：

- `OWNER`：owner 已明确裁决，不再作为开放问题；
- `CODE-FACT`：由当前代码直接证明的现状事实；
- `ACCEPTED-VERDICT`：基于代码事实提出、并已被 owner 接受的设计裁决。
- `D01-CALIBRATION`：由 owner-originated `D01-v1.0` 回流并重新冻结到 S01 的架构裁决。

后续 spec 和实现不得把 `CODE-FACT` 中的旧行为直接当作新系统要求；只有下表明确冻结的目标真相才具有规范性。若实现需要偏离任一 `S01-Txxx`，必须提出 change request、列出受影响 spec，并重新取得 owner 裁决。

`S01-v1.1`已正式reopen相关Attempt/task_type段落；v1.0旧口径不得以兼容理由回流。`S01-v1.2`进一步接收S02 restart causal truth；`S01-v1.3`接收S04 Intake vocabulary与resource truth，仍不恢复任何废止identity或wire alias。

### 2.2 定位、拓扑与协议真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S01-T001` | MKB 是 standalone leaf-worker 单体应用；“相对平台无状态”不等于内部无状态。 | `OWNER` | `S02-S15` 必须允许 MKB 持有业务执行状态。 |
| `S01-T002` | MKB Contract 是上游接入的权威契约；上游负责映射，MKB 不为 03-nano 当前私有协议扭曲核心模型。 | `OWNER` | 所有 adapter 依赖 domain contract，禁止 domain 依赖上游 DTO。 |
| `S01-T003` | v1 不要求把 MKB 注册为 skill-worker，也不实现主动注册、注销、心跳或 `SkillWorkerManifest` 生命周期。 | `ACCEPTED-VERDICT` | 这些能力不得成为首版启动阻塞项。 |
| `S01-T004` | 未来 skill-worker 对接只能通过防腐 adapter 增量加入；adapter 不得放宽 MKB 的必填字段、不变量和错误语义。 | `ACCEPTED-VERDICT` | `17` 预留 adapter 边界，但核心 API 不感知 NACP。 |
| `S01-T005` | v1 的异步结果交付方式是 polling；不提供 webhook/callback。 | `OWNER` | `S02` 必须提供可轮询状态/结果；`S15-S16` 不为 webhook 建设设施。 |
| `S01-T006` | MKB 不提供 UI，不拥有 user、session、team membership、owner、role、permission、billing 或 plan。 | `OWNER` | 不得创建对应 domain、表或 API。 |
| `S01-T007` | 已知上游是 `03-nano/orchestrator-core`，但它不是 MKB 契约真相的所有者；其他持有效内部 token 的 orchestrator 也可按同一契约接入。 | `OWNER` | API 不得硬编码 caller 为 03-nano。 |

### 2.3 身份与 UUID 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S01-T008` | 所有领域 ID 必须 UUID 化；没有单独 owner 裁决时，禁止自增 ID 和对外暴露的整数主键。 | `OWNER` | `S02-S15` 的领域主键、外键、事件 ID 全部继承。 |
| `S01-T009` | 边界输入只接受 UUID v4 或 v7；MKB 自己生成的领域 UUID 一律使用 v7。 | `OWNER` | 校验器必须检查 UUID version，不能只检查字符串格式。 |
| `S01-T010` | revision、retry count、priority rank、计数器和底层引擎内部 rowid 不是领域 ID，可以使用整数；不得把它们暴露成资源身份。 | `ACCEPTED-VERDICT + D01-CALIBRATION` | 避免将“全部 UUID”错误扩张到非身份数值；不得把 retry counter 误建成 Attempt identity。 |
| `S01-T011` | Task Create 的 `task_uuid` 必须由上游提供；MKB 禁止替上游生成、覆盖或规范成另一个 task ID。 | `OWNER` | 缺失时拒绝请求，不得先建任务后补 ID。 |
| `S01-T012` | `task_uuid` 仅在 team 内唯一；任务权威键是 `(team_uuid, task_uuid)`，不同 team 可以使用相同 `task_uuid`。 | `OWNER` | 路由、表 PK/FK、缓存、锁、日志和查询都必须携带复合身份。 |
| `S01-T013` | 根 `trace_uuid` 必须由上游在 Task Create 时提供，并在任务全生命周期保持不变。 | `ACCEPTED-VERDICT + D01-CALIBRATION` | MKB 不替换 root trace；内部 execution/process/event UUID 使用 v7。 |
| `S01-T014` | 完整 Execution retry 沿用原 `(team_uuid, task_uuid, trace_uuid)`，创建新的内部 UUIDv7 `execution_uuid` 并以 `retry_of_execution_uuid` 保留血缘；自动 Process retry 保持原 `process_uuid` 并递增 retry counter。`attempt_uuid` 已被废止。 | `D01-CALIBRATION`（取代 v1.0） | retry 不是新 Task；不得复活旧 Execution、不得为自动 Process retry 新建 Execution，也不得引入重叠 Attempt identity。 |
| `S01-T015` | `intake.ingest`的五类权威Intake UUID均由MKB生成UUIDv7：single入口建立IntakeSource并解析目标IntakeItem；scatter入口建立/复用IntakeSource，以accepted IntakeSnapshot/IntakeSnapshotMembership为每个source-scoped ExternalKey分配/复用IntakeItem。更新、重建、失活和删除引用MKB Intake ID。 | `ACCEPTED-VERDICT + D01/S04-CALIBRATION` | 上游不得在ingest中指定权威IntakeSource/IntakeSnapshot/IntakeItem/IntakeRevision/IntakeArtifact UUID；S04持有exact identity graph。 |
| `S01-T016` | 上游可提供可选`external_resource_uuid`做非权威关联，但它不是ExternalKey或任一MKB Intake主键；若提供也必须是UUIDv4/v7。 | `ACCEPTED-VERDICT + S04-CALIBRATION` | S04必须分开canonical Intake identity、source-scoped ExternalKey与外部关联ID。 |

### 2.4 Team Registry 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S01-T017` | `team_uuid` 是上游 team 的本地审计、分区、追踪和过滤投影，不代表 MKB 拥有 team。 | `OWNER` | `team_uuid` 不能被解释为身份凭证或 membership。 |
| `S01-T018` | MKB 必须提供最小 Team CRUD：create、get/list、patch、activate、deactivate、soft-delete，以及 deleted 后的显式 restore。 | `OWNER + ACCEPTED-VERDICT` | 只管理接入投影，不增加成员、角色或计费字段。 |
| `S01-T019` | Team Create/注册必须由上游提供 `team_uuid`；MKB 不另造本地 team 身份。 | `ACCEPTED-VERDICT` | 避免上游 team 与本地 team 二次映射。 |
| `S01-T020` | Team 状态只有 `active`、`inactive`、`deleted`；新建后为 `active`，deleted 只能先 restore 到 `inactive`，再显式 activate。 | `ACCEPTED-VERDICT` | activate 不得隐式恢复 deleted team。 |
| `S01-T021` | Task Create只接受已注册且为`active`的team；未知team返回HTTP`404`/`team-not-registered`。 | `OWNER + ACCEPTED-VERDICT + D01-CALIBRATION` | 失败请求不得留下Task、Audit、Execution、Process、scheduling intent或Intake/derived Asset行。 |
| `S01-T022` | `inactive` 和 `deleted` team 禁止创建新任务；历史任务和审计仍可查询，soft-delete 不级联删除历史数据。 | `ACCEPTED-VERDICT` | Team 生命周期是接入门，不是数据销毁指令。 |

### 2.5 Task 与 LS-RAG 入口真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S01-T023` | Task Create envelope 使用固定 `mkb.task.v1` schema，必须包含 `team_uuid`、`task_uuid`、`trace_uuid`、`request_intent`、严格 `payload`、`payload_extra` 和嵌套 `audit`。v1 核心 contract 不接受旧字段 `task_type`。 | `OWNER + ACCEPTED-VERDICT + D01-CALIBRATION`（取代 v1.0 字段名） | 上游任意字段必须先映射；adapter 可在进入 core 前翻译旧 DTO，但 core 不得维护双字段。 |
| `S01-T024` | 首版持久异步request intent固定为：`intake.ingest`、`intake.rebuild`、`intake.update_metadata`、`intake.deactivate`、`intake.delete`、`index.rebuild`。这些值只表达外部资源请求，不是内部RAG Workflow/Process类型。 | `ACCEPTED-VERDICT + D01/S04-CALIBRATION` | 添加intent必须版本化或reopen S01/S02；clean/structurize/construct/vectorize等工序由S03 registry定义。 |
| `S01-T025` | `retrieval.search` 首版是同步查询，不创建持久 Task/Execution/Process；若未来需要异步检索必须另行裁决。 | `ACCEPTED-VERDICT + D01-CALIBRATION` | `S10` 不得默认污染 Task queue 或 Execution/Process runtime。 |
| `S01-T026` | `payload` 必须按 `request_intent` 使用判别式严格模型；它承载外部资源动作的输入，不定义内部 Workflow Definition 或 Process graph。 | `OWNER + ACCEPTED-VERDICT + D01-CALIBRATION` | 具体 payload 字段由 `S02/S04/S05/S09` 冻结且必须 `extra=forbid`；内部业务工序由 S03/S05-S09 冻结。 |
| `S01-T027` | Task、五类Intake identity、Trace、Execution、Process是不同身份；禁止用legacy`job_uuid/file_uuid`或任一UUID同时冒充请求、资源、观察、修订、完整执行、具体工序或trace。 | `ACCEPTED-VERDICT + D01/S04-CALIBRATION` | 所有引用必须使用完整语义字段；Attempt identity不存在。 |
| `S01-T028` | 上游只能提交 request intent、查询 Task 聚合状态、修改允许的描述性字段，以及发送 cancel/retry 命令；不能提供或直接写内部 status、progress、result、execution、process、workflow phase、claim、lease 或 retry counter。 | `OWNER + ACCEPTED-VERDICT + D01-CALIBRATION` | `S02` 独占 Task 聚合状态，`S03` 独占 Execution/Process 状态机；上游不能绕过 Task ingress。 |
| `S01-T029` | Task 原始输入 `payload`、三类外部 UUID、`request_intent`、`schema_version`、creation fingerprint 和 `audit` 在创建后不可变。 | `ACCEPTED-VERDICT + D01-CALIBRATION` | 变更请求输入必须创建新 task_uuid；Execution retry 不能借机改写 Task input。 |
| `S01-T030` | 外部 Task PATCH 只允许修改 `title`、`description`、Task 自身的 `payload_extra`；`priority` 仅在 task 仍为 queued 时可改。 | `ACCEPTED-VERDICT` | 所有 PATCH 必须携带 `expected_revision`。 |
| `S01-T031` | MKB 内部可以根据 current root Execution 的归约结果更新 Task aggregate status、说明、progress、result/error summary 和时间戳；这不构成外部 PATCH 权限，也不允许 Task transition 反向伪造 Process/Execution 状态。 | `OWNER + ACCEPTED-VERDICT + D01-CALIBRATION` | repository 必须区分 external patch、Task aggregate transition 与 Execution/Process transition。 |

### 2.6 Task / Execution / Process 边界真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S01-T047` | Task lifecycle 与 Workflow lifecycle 必须分开：Task 是外部 ACK/CRUD/command/aggregate status 边界；Execution 是内部 durable workflow run；Process 是 Execution 内的具体工序实例。 | `D01-T001/T002/T007` | `S02` 不定义 RAG 工序，`S03` 不把 Execution/Process 变成 caller-created resources。 |
| `S01-T048` | 任一合法入口都只由外部 Task 开始；`execution_uuid` 和 `process_uuid` 由 MKB 生成且只在内部流转。Task 必须在内部保存 current root Execution 指针或语义等价引用，但外部调用者不依赖该内部 UUID 才能轮询终态。 | `D01-T003/T004/T009` | Task Create/Retry/PATCH 禁止 caller-supplied execution/process identity；Task API 返回聚合 read model。 |
| `S01-T049` | 一个 Task 可以保留多个历史 root Executions，但任一时刻最多一个 current/active root；一个 Process 必须且只能属于一个 Execution。 | `D01-T010/T014` | `tasks.current_root_execution_uuid` 由内部 CAS 更新；完整 retry 创建新 root，旧 Execution 终态不可复活。 |
| `S01-T050` | single Intake入口使用一个root Execution贯穿clean→LS-RAG→publication；API scatter使用一个root controller加0..N child Executions，每个required child绑定exact IntakeItem/Revision运行自己的Processes。 | `D01-T005/T011/T012/T026 + S04-T007/T008` | Task:Execution必须1:N；fan-in分母来自accepted Snapshot/ChangeSet，禁止扁平job或Task singular Process。 |
| `S01-T051` | `process_uuid` 是工序实例 UUID，不是工序分类；Process 必须另有 RAG-specific `process_type/process_key`，至少能表达 clean、structurize、construct、vectorize/index 与 publication validation。 | `D01-T013/T022/T023` | 禁止 generic 内部 task type 取代 RAG process registry；exact workflow/process schema 由 S03/S05-S09 冻结。 |
| `S01-T052` | 运行状态只允许自下而上归约：`Process/child Execution → Execution → Task`；control intent 自上而下传播：`Task command → root/child Execution → active Process`。 | `D01-T019/T020/T030` | worker/queue 不得直接写 Task 成功；收到 cancel command 不等于 active Process 已停止。 |
| `S01-T053` | Process 是活跃期精确运行真相，可在所属 Execution 终结、retry/recovery/cancel/outbox窗口关闭、durable summary 上卷且无 dangling pointer 后清理；Execution 必须比 Process 更 durable。 | `D01-T017/T031/T032` | Process retention 与 Event/Log retention 分离；Task polling 不得因 Process cleanup 失真。 |
| `S01-T054` | D01运行状态只使用`tasks/executions/processes`三张核心业务表；加上`task_audits/task_restarts`后，Task ingress/runtime/restart最小集合为五张。S04十张canonical Intake表与S05 supporting ledgers是资产/acceptance/control truth，不是新增runtime identity。 | `D01-v1.4 / S02-v1.3 / S04-v1.2 / S05-v1.1` | 不得因Intake/preflight/gate表增加Attempt、领域Process分表或scatter运行补丁表。 |
| `S01-T055` | 本地轻量 queue 只是 scheduling/transport mechanism，不是状态 SSOT；只有已提交的 Execution/Process 或 durable scheduling record 才能变成可 claim 工作。 | `D01-T018/T036` | Task/Audit 提交前不可见；queue ack、callback 或日志文本不能决定业务成功。 |
| `S01-T056` | Task成功必须消费current root Execution的durable success proof。LS-RAG proof至少绑定exact IntakeRevision并证明预期vector/filter metadata已发布验证；其他intent使用type-specific proof。 | `D01-T024/T025/T026 + S04-T015/T016` | S02只聚合proof；禁止以pending_count、callback、latest Revision或单vector ACK代替。 |
| `S01-T057` | 外部人工重启分两类：full retry保持Task identity并创建新generation；atomic IntakeItem rebuild创建新Task且不创建IntakeRevision。两类均写`task_restarts`因果/admission truth，状态只从Task获取。 | `S02-T024-T031 + S04-T010/T033` | 上游不得选择stage/process recovery；rebuild target使用`intake_item_uuid`/可选expected revision。 |
| `S01-T058` | S05 PreflightValidator是内部Process capability；allowlist不能绕过validation，validator runtime错误仍由S03 retry/failed处理。 | `S05-T014..19` | Task caller不得提交validator代码、check结果、passed/blocked Outcome或route override。 |
| `S01-T059` | Human review是既有Execution的durable gate，不是Task/Execution/Process/Intake新身份；Task在gate open期间保持非终态。 | `S05-T020..24` | Process不持lease等人，Intake无review state，Task六态不增加`waiting/reviewing`。 |
| `S01-T060` | Polling read model必须在不泄漏内部Execution/Process身份的前提下表达`action_required`、gate kind、安全review summary、gate ref/revision和decision affordance。 | `S05-T021/T023..24` | 不得把waiting伪装成stuck；exact ReviewTarget/fence由服务端持有并验证。 |
| `S01-T061` | v1必须存在受控gate decision语义面；它以team+Task+gate ref、expected gate revision、target digest、action、idempotency与actor evidence提交，不能直接PATCH Execution/Process。 | `S05-T023..24 + S16 cutoff` | exact URI/envelope与authority由S02/S16校准；decision必须append+CAS+outbox，HTTP响应不等于release。 |

### 2.7 Audit 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S01-T032` | 每个 Task Create 必须携带且仅携带一个 Audit v1；Task 与 Audit 是 1:1。 | `ACCEPTED-VERDICT` | 无 audit 的任务不存在合法创建路径。 |
| `S01-T033` | Audit 存入独立 `task_audits` 业务表，不设 `audit_uuid`；其 PK/FK 均使用 `(team_uuid, task_uuid)`。 | `OWNER + ACCEPTED-VERDICT` | 禁止把 audit 塞进 task JSON 列作为唯一持久真相。 |
| `S01-T034` | Task 与 Audit 必须在同一数据库事务中原子创建；任何校验、team gate 或写入失败都必须使二者同时不存在。 | `OWNER + ACCEPTED-VERDICT + D01-CALIBRATION` | Execution、Process、queue work 或 workflow scheduling intent 不得在该事务提交前可见。 |
| `S01-T035` | Audit 是上游发起的业务审查快照；log/event 是 MKB 内部运行记录。两者不得共表、互相替代或共享可变语义。 | `OWNER` | `S15` 不能把内部日志命名为 Task Audit。 |
| `S01-T036` | Audit 创建后永久不可修改；MKB 不提供 audit PATCH/PUT，也不得因 Task PATCH、retry、cancel 或 soft-delete 改写原 Audit。 | `OWNER` | 后续审查变化需要新的 Task 或未来独立版本化机制，不能覆盖 v1。 |
| `S01-T037` | MKB 只严格校验并保存 Audit snapshot，不解释 `audit_status`，也不根据 approved/rejected/pending 决定是否执行任务。 | `ACCEPTED-VERDICT` | 业务审批控制属于上游；上游只应在希望执行时提交 Task。 |
| `S01-T038` | Audit 内重复的 `team_uuid`、`task_uuid`、`trace_uuid` 必须与 Task envelope 完全一致，否则整个请求拒绝。 | `ACCEPTED-VERDICT` | 禁止出现无法归属的审计行。 |

### 2.8 校验、扩展、时间与一致性真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S01-T039` | 所有对外 contract 使用 Pydantic v2 strict models 做运行时验证；未知字段默认拒绝。内部不可变值对象应使用 frozen/slots dataclass 或等价不可变模型。 | `OWNER + ACCEPTED-VERDICT` | 原始 dict 不得越过 application boundary。 |
| `S01-T040` | 每一个由 MKB 定义和拥有的持久业务表都必须有 `payload_extra`，存为非空 JSON object，默认 `{}`；仅验证 JSON 可序列化结构，不解释其业务内容。 | `OWNER + ACCEPTED-VERDICT` | `payload_extra` 不能替代一等字段或绕过 schema version。 |
| `S01-T041` | migration bookkeeping、Turso/SQLite 引擎内部表、虚拟向量表、FTS shadow 表和第三方组件私有表不受 `payload_extra` 规则约束。 | `ACCEPTED-VERDICT` | “所有表”仅指 MKB 业务真相表。 |
| `S01-T042` | 时间使用 RFC 3339 / ISO 8601，必须带时区；持久化和输出统一为 UTC `Z`，至少毫秒精度，MKB 生成值优先微秒精度。 | `ACCEPTED-VERDICT` | 禁止 naive datetime 和本地时区持久化。 |
| `S01-T043` | 上游 Audit `created_at` 与 MKB `received_at` 是两个不同事实；MKB 不覆盖上游时间，只另行写入 server-received time。 | `ACCEPTED-VERDICT` | 两个时间都必须可查询。 |
| `S01-T044` | 同 `(team_uuid, task_uuid)` 且 creation fingerprint 相同的重放幂等返回既有任务；fingerprint 不同返回 HTTP `409 task-identity-conflict`，禁止覆盖。 | `OWNER + ACCEPTED-VERDICT` | 必须持久化首次创建 fingerprint。 |
| `S01-T045` | Task/Team 可变操作采用整数 `revision` 做 optimistic concurrency；调用者必须提供 `expected_revision`，不匹配返回 `409 revision-conflict`。 | `ACCEPTED-VERDICT` | revision 不是领域 ID。 |
| `S01-T046` | 简单内部 token 是调用权证明；任一有效 token 可操作全部 Team/Task API，不做 team 级 RBAC。`team_uuid` 本身绝不是授权凭证。 | `OWNER` | `S16` 只实现最小内部信任边界，不重建平台权限。 |

### 2.9 冻结 Contract v1

#### 2.9.1 Task Create envelope

```json
{
  "schema_version": "mkb.task.v1",
  "team_uuid": "UUIDv4-or-v7",
  "task_uuid": "UUIDv4-or-v7",
  "trace_uuid": "UUIDv4-or-v7",
  "request_intent": "intake.ingest",
  "title": "optional human-readable title",
  "description": "optional human-readable description",
  "priority": "normal",
  "payload": {},
  "payload_extra": {},
  "audit": {
    "schema_version": "mkb.task-audit.v1",
    "team_uuid": "same UUID as task.team_uuid",
    "task_uuid": "same UUID as task.task_uuid",
    "trace_uuid": "same UUID as task.trace_uuid",
    "audit_type": "business_review",
    "audit_status": "approved",
    "source": "upstream-orchestrator",
    "source_version": "optional",
    "actor_uuid": "optional UUIDv4-or-v7",
    "parent_task_uuid": "optional UUIDv4-or-v7",
    "created_at": "2026-07-15T00:00:00.000Z",
    "reviewed_at": "optional RFC3339 timestamp",
    "expires_at": "optional RFC3339 timestamp",
    "reason": "optional business reason",
    "payload_extra": {}
  }
}
```

冻结规则：

- `schema_version`、三个外部 UUID、`request_intent`、`payload`、`payload_extra`、`audit` 必填；
- `title`、`description` 可选；`priority` 可省略并使用 `S02` 冻结的默认值 `normal`；
- `priority` 必须是 `S02` 冻结的严格 enum，不能接受任意字符串；
- `payload` 的结构由 `request_intent` 判别，不允许额外未知字段；
- `payload_extra` 顶层必须是 JSON object；其中键和值不做领域解释；
- `audit` 在请求中嵌套只是为了保证一次提交，持久化时必须拆入独立表；
- `task_type`、`execution_uuid`、`process_uuid`、workflow/process 状态与任何 claim/lease 字段均不是 v1 输入；出现时 strict reject；
- MKB 生成的 `received_at`、`created_at`、`updated_at`、`revision`、aggregate status 与内部 UUID 不由调用者传入；
- token、HTTP header、server receive time 不参与业务 payload。

#### 2.9.2 Audit v1 固定字段

| 字段 | 必填 | 约束 | 可变性 |
|---|---:|---|---|
| `schema_version` | 是 | 必须等于 `mkb.task-audit.v1` | immutable |
| `team_uuid` | 是 | UUIDv4/v7；等于 Task | immutable |
| `task_uuid` | 是 | UUIDv4/v7；等于 Task | immutable |
| `trace_uuid` | 是 | UUIDv4/v7；等于 Task | immutable |
| `audit_type` | 是 | v1 仅允许 `business_review` | immutable |
| `audit_status` | 是 | `pending / approved / rejected / waived / not_required` | immutable；MKB 不解释 |
| `source` | 是 | 非空上游来源名称 | immutable |
| `source_version` | 否 | 上游审查 contract/version | immutable |
| `actor_uuid` | 否 | UUIDv4/v7 | immutable |
| `parent_task_uuid` | 否 | UUIDv4/v7；只做审计关联，不自动建立 workflow 依赖 | immutable |
| `created_at` | 是 | 上游产生时间，RFC3339、带时区 | immutable |
| `reviewed_at` | 否 | RFC3339、带时区 | immutable |
| `expires_at` | 否 | RFC3339、带时区；不触发 MKB token/task 过期逻辑 | immutable |
| `reason` | 否 | 上游业务说明 | immutable |
| `payload_extra` | 是 | JSON object；默认可显式传 `{}` | immutable |
| `received_at` | server | MKB 在接收事务内生成的 UTC 时间 | immutable |

#### 2.9.3 Team v1 最小模型

| 字段 | 责任与约束 |
|---|---|
| `schema_version` | `mkb.team.v1` |
| `team_uuid` | 上游提供的 UUIDv4/v7；PK；immutable |
| `name` | 必填显示名称；不承载权限语义 |
| `description` | optional |
| `status` | `active / inactive / deleted` |
| `created_at` | MKB UTC server time |
| `updated_at` | MKB UTC server time |
| `deactivated_at` | optional MKB UTC server time |
| `deleted_at` | optional MKB UTC server time |
| `revision` | optimistic concurrency counter |
| `payload_extra` | JSON object，默认 `{}` |

禁止加入：`owner_uuid`、membership、role、plan、credit、billing、quota ownership、password、user profile 或平台 permission。

#### 2.9.4 首版 Request Intent 与内部执行边界

| `request_intent` | 外部入口语义 | 核心资源要求 | 内部执行边界 / Legacy 语义关系 |
|---|---|---|---|
| `intake.ingest` | 接受新外部输入，建立/复用IntakeSource并产生accepted Snapshot/Items/Revisions | caller不提供五类canonical Intake UUID；可带非权威`external_resource_uuid`和strict IntakeSource descriptor | single/scatter由Snapshot/Membership与root/child Executions表达 |
| `intake.rebuild` | 对既有IntakeItem/Revision重新执行LS-RAG派生构建 | 必须提供MKB`intake_item_uuid`，可带expected`intake_revision_uuid` | 创建新Task/Execution/build generation；不复活旧执行、不创建IntakeRevision |
| `intake.update_metadata` | 提交受控metadata semantic change并触发必要派生更新 | 必须提供`intake_item_uuid`和strict semantic payload | canonical semantics变化时追加IntakeRevision；route由WorkflowRevision决定 |
| `intake.deactivate` | 使IntakeItem不再参与正常检索 | 必须提供`intake_item_uuid` | logical-first clear serving；Task不内嵌physical invalidation状态 |
| `intake.delete` | 使IntakeItem进入deleted tombstone与cleanup lifecycle | 必须提供`intake_item_uuid` | logical-first；各substrate cleanup proof收敛，不等同legacy deactivate |
| `index.rebuild` | 重建指定 scope 的向量/检索索引 | scope 由 `S09` 冻结 | 新 contract；由 index Execution/Processes 与 publication proof 承接 |
| `retrieval.search` | 同步 LS-RAG 查询 | 不创建 Task | 由 `S10` 单独冻结；不创建 Execution/Process |

冻结解释：

- `request_intent` 只回答“上游希望对哪个业务资源做什么”，不回答“内部由哪些工序完成”；
- clean、scatter、structurize、construct、vectorize、validate、purge 是 Workflow/Process 词汇，不得进入 `request_intent` enum；
- single与API scatter可以使用相同`intake.ingest` intent，差异由strict IntakeSource descriptor、root Execution role、Snapshot/Membership/ChangeSet与child Executions表达；
- 因 v1.0 contract 尚未实现，本次直接更正 canonical 字段，不保留 `task_type` alias；未来兼容旧 caller 只能在防腐 adapter 中单向翻译。

---

## 3. 总体方案陈述

1. **S01-P01 — Standalone first**：先交付独立 MKB API，不把 03-nano 注册或 `SkillWorkerManifest` 作为启动依赖。
2. **S01-P02 — Canonical contract**：建立 MKB 自有、版本化、严格验证的 Team/Task/Audit contract；所有上游自行适配。
3. **S01-P03 — UUID identity law**：用UUIDv4/v7输入、UUIDv7内生、复合Task主键统一全域身份，并严格分离Task/Trace/Intake identities/Execution/Process/Event。
4. **S01-P04 — Team as projection**：用最小 Team Registry 管理接入和审计分区，不承接平台 team ownership。
5. **S01-P05 — Atomic Task ingress**：在一次事务中完成 team gate、幂等判断、Task 和 immutable Audit 创建。
6. **S01-P06 — Task/Execution/Process separation**：上游只表达 request intent；Task 持有外部聚合状态，Execution 持有 durable workflow run，Process 持有具体工序与 retry/claim 状态。
7. **S01-P07 — Polling delivery**：首版以 Task CRUD/status/result polling 形成闭环，明确排除 callback/webhook。
8. **S01-P08 — Strict core, flexible edge**：一等字段严格校验，所有 MKB 业务表保留 `payload_extra` 扩展袋，但扩展袋不能改变核心语义。
9. **S01-P09 — Minimal trust**：一个简单内部 token 保护业务接口；有效 token 具有全部功能，不建立 RBAC。
10. **S01-P10 — Future anti-corruption adapter**：未来 skill-worker 接入只做协议翻译，不改变 MKB Contract v1。
11. **S01-P11 — Single/scatter one ingress**：单一文件和 API 散射均从一个 Task 进入；内部用一个 current root 与 0..N child Executions 表达差异，不增加第二套外部 API。

---

## 4. 具体执行方案清单

### 4.1 `S01-E01` — 建立 standalone service boundary

**说明**：MKB 必须可在完全没有 03-nano 的环境中启动、接受合法任务、执行并供调用者轮询。核心 application/domain 不导入 03-nano/NACP DTO、binding 或 `SkillWorkerManifest` 类型。

**真相层对应编号**：`S01-T001`–`S01-T007`

**执行台账**：

| 执行项 | 强制要求 | 交付证据 |
|---|---|---|
| 发布边界 | 一个 Python 应用、一个发布单元、一个权威 API surface | standalone integration test |
| Contract 版本 | Task/Team/Audit 分别使用显式 `schema_version` | schema tests |
| 上游中立 | 不硬编码 `orchestrator-core` caller 名称 | dependency/import gate |
| 平台职能隔离 | 无 user/session/membership/billing/UI route、table、service | architecture test / schema audit |
| 能力报告 | 可提供版本化 capability read model，至少声明 API 版本、request intents、polling 与健康状态；不得冒充 `SkillWorkerManifest`，也不得把内部 Process registry 当外部 intent enum | contract snapshot |
| 启动依赖 | 03-nano 不可达时 MKB 仍能 ready；MKB 自身持久层/模型依赖按各自 readiness 判断 | isolated boot test |

**小结**：MKB 的可运行性由自身依赖决定，不由未来 skill registry 决定。

### 4.2 `S01-E02` — 实施全域 UUID identity law

**说明**：在 API、domain、repository、queue、artifact metadata、log/event 和缓存键中统一身份语义。

**真相层对应编号**：`S01-T008`–`S01-T016`

**执行台账**：

| 执行项 | 强制要求 | 失败语义 |
|---|---|---|
| 输入 UUID | parse 后检查 version ∈ `{4, 7}`；拒绝 nil、非 UUID 与其他 version | `422 invalid-uuid` / `invalid-uuid-version` |
| MKB 内生 UUID | 五类Intake identity、Execution、Process、Event等均由统一UUIDv7 generator产生 | generator failure不得fallback自增ID |
| Task identity | 所有方法和 repository 以 `(team_uuid, task_uuid)` 寻址 | 禁止仅凭 task_uuid 查询/更新 |
| Trace identity | Task Create 必填 root trace；内部 spans/events 引用它 | 缺失返回 validation error |
| Retry identity | 完整 retry 新建 `execution_uuid` 并保留 task/trace/retry-of；自动工序 retry 保持 `process_uuid` | 禁止 Attempt identity、禁止覆盖/复活旧 Execution |
| Resource identity | single ingest建立IntakeSource并解析IntakeItem；scatter在IntakeSource namespace内按stable ExternalKey分配/复用IntakeItems，IntakeSnapshot/IntakeRevision/IntakeArtifact各自独立UUID | 禁止重放/重扫无条件生成第二套identity |
| 外部关联 | `external_resource_uuid`单独存储和索引，不替代ExternalKey或Intake UUID | 冲突策略由`S04`冻结 |

建议持久键形状：

```text
teams:          PK (team_uuid)
tasks:          PK (team_uuid, task_uuid)
task_audits:    PK/FK (team_uuid, task_uuid)
executions:     PK (execution_uuid), FK (team_uuid, task_uuid), self-FK root/parent/retry-of
processes:      PK (process_uuid), FK (execution_uuid)
intake_sources: PK (team_uuid, intake_source_uuid)
intake_items:   PK (team_uuid, intake_item_uuid), source-scoped external key unique
```

**小结**：UUID 是身份，不是随意的字符串；Task 的 team-local uniqueness 必须贯穿所有层。

### 4.3 `S01-E03` — 建立最小 Team Registry

**说明**：Team Registry 是上游 team 的本地投影和任务接入门。它不验证调用者是否“属于”某 team；token 已代表内部调用权。

**真相层对应编号**：`S01-T017`–`S01-T022`、`S01-T045`–`S01-T046`

**执行台账**：

| 语义操作 | 输入/前置条件 | 结果/状态转移 |
|---|---|---|
| Create/Register | caller 提供 UUIDv4/v7、name、`payload_extra` | 不存在 → `active`；同 ID 同 creation fingerprint 幂等，差异冲突 |
| Get/List | 有效 token | 返回投影和 lifecycle 时间；支持按 status 过滤 |
| Patch | `expected_revision`；非 deleted | 只改 name、description、payload_extra；revision + 1 |
| Deactivate | active + expected revision | `active → inactive`，写 `deactivated_at` |
| Activate | inactive + expected revision | `inactive → active`；不得作用于 deleted |
| Soft-delete | active/inactive + expected revision | `→ deleted`，写 `deleted_at`；历史不级联 |
| Restore | deleted + expected revision | `deleted → inactive`；清除/保留历史 deleted_at 的策略由 event 记录，随后需单独 activate |

Task Create 的 gate 顺序必须是：token 校验 → strict schema → team lookup/active check → 幂等/事务创建。未知 team 的安全拒绝可以记录内部 rejection event，但绝不能创建 Task/Audit/Execution/Process 业务行。

**小结**：MKB 知道“这个 team 是否获准向本实例投递任务”，但不知道也不关心“谁拥有这个 team”。

### 4.4 `S01-E04` — 固化 Task Create boundary models

**说明**：Task envelope 和每个 task payload 都必须是编译期可见、运行时严格校验的模型；`payload_extra` 是唯一自由扩展面。

**真相层对应编号**：`S01-T023`–`S01-T031`、`S01-T039`–`S01-T043`

**执行台账**：

| 层 | 模型要求 | 禁止事项 |
|---|---|---|
| HTTP/RPC ingress | Pydantic v2 `strict=True`、`extra='forbid'`、显式 schema version | 自动 coercion、静默丢未知字段 |
| Task envelope | 固定字段 + discriminated `payload` union | `dict[str, Any]` 作为核心 task input |
| Audit | frozen strict model | 接收后 mutation |
| Domain value object | frozen/slots dataclass 或等价不可变对象 | 把 request dict 贯穿 workflow |
| Persistence DTO | 明确 JSON encode/decode 与 schema version | 将 JSON 文本当作已校验对象 |
| `payload_extra` | 顶层object；内容只做JSON-valid校验 | 在其中藏status、request_intent、Intake UUID、execution/process identity等一等字段 |

每个 request intent 的 payload 详细字段由后续 domain 冻结，但必须遵守：

1. `intake.ingest`不接受caller-defined Intake UUID；
   - single与API scatter均适用；scatter IntakeItem UUID由MKB按IntakeSource-scoped ExternalKey分配/复用；
2. rebuild/update/deactivate/delete必须引用MKB`intake_item_uuid`，需要固定输入时同时给expected`intake_revision_uuid`；
3. `index.rebuild` 必须使用受控 scope，不能接受任意 SQL/index path；
4. 所有IntakeSource descriptor、IntakeArtifact input和model override都必须是显式字段或受控子模型；
5. 未识别 `request_intent`、旧 `task_type` 字段、caller-supplied execution/process 字段或 payload mismatch 一律 fail-loud；
6. source kind 可以决定 single/scatter workflow，但 caller 不提交 root/child Execution topology。

**小结**：灵活性集中在明确命名的扩展袋，执行语义本身始终严格。

### 4.5 `S01-E05` — 实施 Task + Audit 原子接收事务

**说明**：Task 和上游 Audit 是一个接收动作中的两个独立真相面，必须 all-or-nothing。

**真相层对应编号**：`S01-T032`–`S01-T038`、`S01-T043`

**执行台账**：

```text
validate token
  → parse strict Task/Audit models
  → validate UUID versions and Task/Audit identity equality
  → begin transaction
      → read Team and require active
      → resolve idempotency by (team_uuid, task_uuid, creation_fingerprint)
      → insert Task
      → insert immutable Task Audit
      → allocate/store stable top-level ingest resource UUID when applicable
      → create durable scheduling intent/outbox record when S03/S12 require it
    commit
  → only after commit may a root Execution/Process be created or become claimable
```

| 不变量 | 数据库/应用要求 |
|---|---|
| 1:1 | `task_audits` 使用与 Task 相同复合 PK，并 FK 到 Task |
| immutable | 无 audit update repository；数据库权限/trigger 应提供 defense-in-depth（能力由 `S12` 冻结） |
| identity equality | Task/Audit 三 UUID 在进入事务前比较，数据库复合 FK 再次约束 |
| server time | transaction 内写 `received_at`；不得改写 caller `created_at` |
| no partial row | 任一 insert、constraint、serialization 失败必须 rollback |
| no early dispatch | queue/claim 不得看到未提交 Task；Execution/Process 或 durable scheduling record 必须先提交；推荐 transactional outbox，最终由 `S03/S12` 裁决 |

Audit status 仅作为被保存的上游事实。即使值为 `rejected`，MKB 也不自行充当审批引擎；是否应提交这种 Task 是上游责任。

**小结**：Audit 不是一段附加日志，而是与 Task 同时诞生、永久保留的业务证据。

### 4.6 `S01-E06` — 实施幂等、fingerprint 与 optimistic concurrency

**说明**：网络重试必须收敛到同一 Task；真正不同的请求不得借同一 task UUID 覆盖历史。

**真相层对应编号**：`S01-T029`–`S01-T031`、`S01-T044`–`S01-T045`

**执行台账**：

| 机制 | 强制规则 |
|---|---|
| Canonicalization | 对通过strict model后的首次完整Task Create envelope做确定性JSON canonicalization；排除token/header与MKB server-generated字段 |
| Digest | 持久化 SHA-256 creation fingerprint；算法和 canonicalization version 必须可追溯 |
| Same replay | 复合键存在且fingerprint相同→返回既有Task与top-level Intake identity，并标记idempotent replay；不新增Task/runtime/Intake truth |
| Conflict replay | 复合键存在且 fingerprint 不同 → `409 task-identity-conflict`；不得自动 PATCH |
| Later PATCH | 修改当前可变字段不会改写首次 creation fingerprint |
| Revision | Team/Task PATCH 和 lifecycle command 接受 `expected_revision`；CAS 成功后 revision + 1 |
| Conflict | revision 不匹配 → `409 revision-conflict`，返回 current revision 的安全摘要 |

外部 Task PATCH 白名单：

- 全生命周期可改：`title`、`description`、Task 自身 `payload_extra`；
- 仅 queued 可改：`priority`；
- 永不可改：IDs、schema version、request intent、input payload、Audit、creation fingerprint、server timestamps；
- 外部永不可直接改：status、progress、execution/process、workflow phase、claim/lease、retry counter、result、error；
- cancel/retry 必须是显式 command，不伪装成 status PATCH。

**小结**：幂等解决“同一创建被重复送达”，revision 解决“同一可变资源被并发修改”，两者不能混用。

### 4.7 `S01-E07` — 冻结 polling-first Task surface

**说明**：首版上游通过CRUD、command和polling完成闭环。S01冻结语义面；Task/gate URI、分页envelope和完整状态机已由S02-v1.3定稿。

**真相层对应编号**：`S01-T005`、`S01-T023`–`S01-T031`、`S01-T059`–`S01-T061`

**执行台账**：

| Surface | v1 是否必须 | 语义 |
|---|---:|---|
| Create Task | 是 | 原子创建 Task + Audit，返回复合 identity、初始 status、revision、poll location |
| Get Task | 是 | 按 `(team_uuid, task_uuid)` 返回当前状态、描述、进度、结果/artifact引用、错误摘要；open gate时包含安全`action_required`投影 |
| List Tasks | 是 | team-scoped 分页查询；task_uuid 不能跨 team 裸查 |
| Patch Task | 是 | 仅白名单字段 + expected revision |
| Cancel command | 是 | 表达取消 intent；竞态语义归 S02/S03 |
| Retry command | 是 | 表达完整执行 retry intent；Task identity 不变，由 MKB 创建新 current root `execution_uuid` 与新 Processes，并保留 retry-of 血缘 |
| Delete Task | 是 | 只允许受控 soft-delete/tombstone；不得物理删除 immutable Audit，细节归 S02 |
| Poll Result | 是 | 可通过 Get Task 或明确 result subresource 获取；必须能区分 not-ready、terminal failure 与 ready |
| Read review gate | 条件必须 | 仅当Task存在open gate时读取安全review summary、artifact/evidence projection、gate revision与target digest；内部Execution/Process/fence不直接暴露 |
| Submit gate decision | 条件必须 | 以team+Task+gate、expected revision、target digest、action与idempotency提交受控decision；不是Task PATCH或Execution/Process mutation |
| Webhook/Callback | 否 | v1 禁止；未来通过 reopen 增加 |
| `retrieval.search` | 同步独立 surface | 不创建 Task/Audit/Execution/Process 行 |

**小结**：上游无需被动接收回调，也无需 MKB 感知 user Durable Object；稳定资源查询即是首版集成协议。

### 4.8 `S01-E08` — 区分 Task、Execution、Process、Gate、Audit、Restart、Event、Log 与 Trace

**说明**：不同记录服务不同目的，必须从schema、写权限、retention和查询面上分开。ExecutionGate/ReviewTarget/Decision是supporting control truth，不是新的runtime identity；D01运行投影不得被Gate/Audit/Restart/Log/Event替代。

**真相层对应编号**：`S01-T013`–`S01-T014`、`S01-T032`–`S01-T038`、`S01-T047`–`S01-T061`

**执行台账**：

| 记录 | 生产者 | 可变性 | 作用 | 权威键 |
|---|---|---|---|---|
| Task Audit | 上游提供、MKB 原子保存 | immutable | 业务审查快照 | `(team_uuid, task_uuid)` |
| Task | 上游创建、MKB 状态机推进 | revisioned | 工作意图和聚合状态 | `(team_uuid, task_uuid)` |
| Task Restart | 上游人工命令触发、MKB原子保存 | causal/admission immutable | full/atomic人工重启因果、admission与全局追溯 | `restart_uuid` + team/task/intake causation |
| Execution | MKB | durable、terminal immutable | 一次具体 target 的完整 workflow run、tree/retry 血缘与最终 proof summary | `execution_uuid` + task identity |
| Process | MKB workflow engine | revisioned；满足terminal-summary与cleanup-eligibility fence后可清理projection | 一个 RAG-specific 工序的 claim/retry/I/O/error 状态 | `process_uuid` + execution identity |
| Execution Gate / ReviewTarget | MKB workflow/admission control | gate revisioned；target immutable | clean后/RAG前的durable wait与exact审核对象 | `execution_gate_uuid` + execution generation/fence |
| Gate Decision | 受控human/policy command，MKB验证并提交 | append-only | exact target的批准/拒绝/reclean因果；与gate/Execution CAS/outbox原子 | `gate_decision_uuid` + idempotency/target digest |
| Domain Event | MKB | append-only | 可恢复状态转移、对账 | `event_uuid` + task/execution/process correlation |
| Operational Log | MKB/runtime | append-only/按 retention | 诊断，不作业务 SSOT | trace/task/execution/process correlation |
| Trace/Span | 上游 root + MKB child spans | append-only | 调用链与性能 | root `trace_uuid` + internal span IDs |

任何失败都不能只写日志而不反映到对应 Process/Execution/Event 与 Task aggregate；任何日志也不能修改或补写上游 Audit。Process 清理前必须先把 durable summary 上卷到 Execution，Event/Log 的 retention 另行处理。

**小结**：Audit 回答“上游以什么业务审查背景提交”，Event 回答“MKB 发生了什么”，Log 回答“如何诊断”。

### 4.9 `S01-E09` — 实施最小内部 token 边界

**说明**：S01 冻结权限口径，S16 冻结 token 载体、存储、轮换、网络和防滥用细节。

**真相层对应编号**：`S01-T006`–`S01-T007`、`S01-T017`、`S01-T046`

**执行台账**：

| 执行项 | 强制规则 |
|---|---|
| Business endpoints | Team、Task、result、command、review gate/decision 和 capability 的业务数据面必须验证内部 token |
| Authorization model | token 只有 valid/invalid；valid token 可执行全部功能 |
| Team scope | 请求中的 team_uuid 只用于寻址/审计，不从 token claim 推导权限 |
| Invalid token | 在读取 team/task 是否存在前拒绝，避免资源枚举 |
| No platform auth | 不实现 login、session、refresh token、user claim、role、billing gate |
| Probe exposure | live/ready 是否免 token 由 S16 按部署网络边界冻结 |

**小结**：简单 token 是有意缩小信任模型，不是取消输入校验、网络边界和审计。

### 4.10 `S01-E10` — 预留未来 Skill-Worker 防腐 adapter

**说明**：只有当上游 skill-worker 协议稳定且确有接入需求时才实现。首版只冻结隔离原则，不实现虚假的注册能力。

**真相层对应编号**：`S01-T002`–`S01-T005`、`S01-T007`

**执行台账**：

| Adapter 责任 | 必须做到 | 禁止做到 |
|---|---|---|
| Identity mapping | 将上游 invocation/request identity 映射成 caller-supplied MKB `(team_uuid, task_uuid, trace_uuid)`，映射状态由上游或明确 adapter 持有 | 让 MKB 自动生成缺失 task_uuid，或让 caller 提供 execution/process UUID |
| Audit mapping | 构造完整 `mkb.task-audit.v1` | 用 opaque `input` 冒充 Audit |
| Capability projection | 将 MKB task/capability read model 投影为未来 `SkillWorkerManifest` | 把 `SkillWorkerManifest` 变成 MKB domain SSOT |
| Result mapping | polling MKB 后翻译为上游结果 envelope | 要求 MKB 回调当前 03-nano 私有入口 |
| Error mapping | 保留 MKB stable error identity，并做显式翻译 | 吞掉 conflict/validation 变成 generic success |
| Versioning | adapter 自己声明兼容矩阵 | 在 MKB core 中散落 caller/version if-else |

Adapter 若接收旧 caller 的 `task_type`，必须在防腐边界单向映射为 core `request_intent`；MKB core model、持久表与 OpenAPI 不得同时暴露两个字段。未来 skill 协议的 invocation/step 身份也不得映射为 caller-owned Execution/Process。

当前 03-nano 的 `request_uuid`、`invocation_uuid` 和 skill invoke body 不能直接当 MKB Task Contract：当前实现由 skill-core 生成 invocation UUID，且 invoke body 只有 `skill_key/input/session_uuid/variant`。未来接入必须由上游新增映射，不得放宽本文 contract。

**小结**：Skill-worker 是未来的一种接入外观，不是 MKB 的本体。

---

## 5. 事实反例 + 风险台账

### 5.1 事实反例台账

| Counterexample ID | 错误叙事/做法 | 代码事实或真相 | 必须采取的订正 |
|---|---|---|---|
| `S01-C01` | “03-nano orchestrator-core 已经可以直接 invoke/register 任意外部 skill-worker。” | 当前 orchestrator 直连的是只读 discovery face，invoke/register 物理缺席。 | 不以现状协议为 MKB 首版 contract；未来另做 adapter。 |
| `S01-C02` | “`execution.target=service` 已是通用远程 worker 接口。” | 当前仅允许硬编码 `SKILL_RUNNER`，输入必须 `{code}`；代码还明确 richer remote semantics 是 wave-2。 | 禁止把 MKB 冒充 SKILL_RUNNER 或塞入 code-exec 通道。 |
| `S01-C03` | “03-nano request_uuid 就等于 MKB task_uuid。” | skill-core 自己生成 `invocation_uuid`；DB 中 request_uuid 普通、非唯一。 | 上游必须显式生成并持有 MKB task_uuid，或在 adapter 内维护明确映射。 |
| `S01-C04` | “legacy job_uuid 是可直接复用的外部 Task 或 MKB Execution 主键。” | legacy 在创建/确认 File 后内部生成 job_uuid，并在 clean→rag 时可能再次生成；它既不稳定覆盖外部请求，也不贯穿一个目标的完整流程。 | 外部使用 Task；MKB 用自己的 durable Execution 贯穿一次目标运行，不继承 legacy job 生命周期。 |
| `S01-C05` | “保留 team_uuid 就必须迁回用户、membership、plan 和 billing。” | legacy Team/ingestion 将这些平台字段耦合在一起；owner 已明确删除平台职责。 | 只保留最小 Team projection 与 task partition/audit。 |
| `S01-C06` | “Audit 就是日志里的 audit event。” | owner 已将 Audit 定义为上游业务审查快照，并要求独立表和原子创建。 | Task Audit 与 MKB log/event 分开建模。 |
| `S01-C07` | “所有表必须有 payload_extra，所以 migration 和向量虚表也要强行加列。” | owner 的目标是所有 MKB 业务表；引擎私表不可控且不承载该扩展语义。 | 仅对 MKB-owned business tables 做 schema gate。 |
| `S01-C08` | “外部可以 PATCH status，因为 Task 详情允许修改。” | status 是 MKB 内部业务流转状态；owner 接受 intent/state 分离。 | 外部使用 cancel/retry command；状态只由内部 transition 更新。 |
| `S01-C09` | “`task_type` 可以继续同时表示外部资源动作和内部 RAG 工序。” | D01 已分离 Task lifecycle 与 Workflow lifecycle；clean/structurize/construct/vectorize 是 Process 分类。 | core 字段改为 `request_intent`；内部使用 versioned Workflow/Process registry。 |
| `S01-C10` | “保留 Attempt 再加 Execution 更完整。” | Attempt 与 Execution 都会表示一次完整 retry run，形成身份、状态、retention 和查询双真相。 | 废止 Attempt；完整 retry 新建 Execution，自动工序 retry 留在 Process。 |
| `S01-C11` | “一个Task只需要一个execution_uuid，scatter children作为JSON明细即可。” | API单点观察可产生N个各自处于不同工序/失败状态的IntakeItem。 | Task指向current root；root下使用0..N durable child Executions，集合分母来自S04。 |
| `S01-C12` | “Task 轮询应直接暴露并让上游操作 current process。” | `execution_uuid/process_uuid` 只在内部流转；散射时也不存在一个可代表所有 children 的 singular Process。 | 对外返回聚合状态/进度/结果；内部 pointer 与诊断 API 不扩大上游状态写权限。 |

### 5.2 风险台账

| Risk ID | 风险 | 严重度 | 预防/围栏 | 验收关联 |
|---|---|---:|---|---|
| `S01-R01` | 只用 task_uuid 查询导致跨 team 碰撞或误更新 | P0 | 所有 route/repository/lock key 强制复合身份 | `S01-A06/A07` |
| `S01-R02` | Audit 写入失败但 Task 已入队，产生无审计任务 | P0 | 单事务 + commit 后可 claim + fault injection | `S01-A12/A13` |
| `S01-R03` | 重放请求覆盖原输入，或生成第二套Intake identity与Execution tree | P0 | creation fingerprint + S04 observation/ExternalKey fences + current root idempotency | `S01-A14/A15` |
| `S01-R04` | `payload_extra` 成为绕过 strict schema 的后门 | P0 | 禁止保留字段名；domain 不读取它来决定核心状态机 | `S01-A22` |
| `S01-R05` | Team Registry 再次长成权限/计费平台 | P0 | schema allowlist 与禁用字段 architecture gate | `S01-A03` |
| `S01-R06` | Audit `approved/rejected` 被 MKB 误解释，造成隐藏审批逻辑 | P1 | 只验证 enum/保存，不参与 admission/scheduling | `S01-A18` |
| `S01-R07` | valid token 被误当 team-scoped token，出现两套授权真相 | P1 | token only valid/invalid；team_uuid 只寻址 | `S01-A02/A24` |
| `S01-R08` | callback/webhook 偷偷进入首版并扩大可靠性/安全面 | P1 | API inventory 明确禁用；契约测试保证无 callback config | `S01-A20` |
| `S01-R09` | 未来 03 adapter 反向污染 core models | P0 | dependency rule：adapter → application port，domain 禁止依赖 adapter DTO | `S01-A25` |
| `S01-R10` | 把全 UUID 误解为禁止 revision/counter/engine rowid | P2 | 明确 identity 与非 identity 数值的边界 | schema review |
| `S01-R11` | caller `created_at` 与 server `received_at` 混写，无法证明传输延迟或审计时序 | P1 | 两列分存、UTC normalize、不可覆盖 | `S01-A17` |
| `S01-R12` | Task PATCH 与首次 fingerprint 相互覆盖，破坏重放判断 | P1 | fingerprint 永久保存首次 canonical create；PATCH 只改 current projection | `S01-A14/A19` |
| `S01-R13` | core 同时接受 `task_type` 与 `request_intent`，canonical fingerprint 和 discriminator 出现双语义 | P0 | v1.1 core 只接受 `request_intent`；旧 caller 仅在 adapter 预翻译 | `S01-A23/A31` |
| `S01-R14` | `attempt_uuid` 与 `execution_uuid` 并存，retry 产生两套 current state | P0 | schema/import gate 禁止 Attempt identity/table；Execution 是唯一完整运行身份 | `S01-A28/A32` |
| `S01-R15` | Task 保存 singular current Process，散射时错误覆盖 child 进度 | P0 | Task 只存 current root + aggregate；current Process 属于每个 Execution | `S01-A33/A34` |
| `S01-R16` | queue/callback 直接把 Task 标为成功，绕过 vector/filter proof | P0 | Process guard → Execution proof → Task aggregation；semantic repair对账 | `S01-A35/A36` |

### 5.3 明确禁止的实现方向

1. 禁止复制 `legacy-family` 的 Cloudflare 多 Worker、Queue callback 和平台 auth 拓扑。
2. 禁止复制 03-nano `skill-core` 的 registry、grant、billing 或 invocation 表作为 MKB 核心模型。
3. 禁止为“看起来兼容”而允许缺失 task UUID、team UUID、trace UUID 或 Audit。
4. 禁止将 `team_uuid` 放进 token 后建立隐式 team RBAC。
5. 禁止使用自增Task/Intake/Execution/Process/Event ID。
6. 禁止用一个全局唯一约束覆盖 `(team_uuid, task_uuid)` 的 team-local 语义。
7. 禁止提供 Audit 更新接口或用 Task PATCH 顺带更新 Audit。
8. 禁止让外部 PATCH 直接写 status/progress/result/error。
9. 禁止以 callback/webhook 作为首版结果交付的隐藏依赖。
10. 禁止把 `payload_extra` 当作未版本化的第二套 API。
11. 禁止在 core Contract、模型或持久表中继续使用 `task_type`；adapter 只能单向翻译为 `request_intent`。
12. 禁止创建 `attempt_uuid`、`task_attempts` 或其他与 Execution 重叠的完整执行身份。
13. 禁止让外部 caller 提供、PATCH 或以命令直接寻址 `execution_uuid/process_uuid`。
14. 禁止把 Task 限制为单一 flat Execution；scatter 必须允许 current root + N child Executions。
15. 禁止让 Task 保存 singular `current_process_uuid`，或用 Task status enum 承载 clean/structurize/construct/vectorize 工序状态。
16. 禁止复制 clean/rag Process 分表；统一 `processes` 记录工序控制状态，向量资产归 S08/S09。

---

## 6. 测试与验收台账

> 本节描述实现必须交付的测试。本文是 specification，不声称这些测试或功能当前已经存在。

| Acceptance ID | 层级 | 场景 | HARD 断言 |
|---|---|---|---|
| `S01-A01` | API | 无/错误 token 调用业务 endpoint | 在任何资源读取前返回 `401`；无 side effect |
| `S01-A02` | API | 任一有效 token 操作任意已注册 team | 不做 membership/RBAC gate；按资源状态正常处理 |
| `S01-A03` | Schema | Team 模型或 DDL 出现 owner/member/role/plan/billing 字段 | architecture/schema gate 失败 |
| `S01-A04` | Contract | 输入 UUIDv4 | 接受并 round-trip 保持 identity |
| `S01-A05` | Contract | 输入 UUIDv7 | 接受并 round-trip 保持 identity |
| `S01-A06` | Contract | nil、UUIDv1/v3/v5/v6/v8 或仅“像 UUID”的字符串 | `422`，不得落库 |
| `S01-A07` | Persistence | 两个 team 使用相同 task_uuid | 两行可同时存在且互不覆盖 |
| `S01-A08` | API | 未注册 team 创建 Task | `404 team-not-registered`；Task/Audit/Execution/Process/scheduling intent 全部 0 行 |
| `S01-A09` | API | inactive/deleted team 创建 Task | 明确非 active 错误；无业务行 |
| `S01-A10` | Team lifecycle | deleted team 直接 activate | 拒绝；restore 后状态为 inactive，再 activate 才 active |
| `S01-A11` | Contract | Task/Audit 任一 UUID 不一致 | 整体拒绝；无行 |
| `S01-A12` | Persistence | Audit insert constraint/fault injection 失败 | Task insert rollback；无 scheduling intent |
| `S01-A13` | Persistence | Task insert 成功但 commit 前 executor 轮询 | executor 不可 claim 未提交任务 |
| `S01-A14` | Idempotency | 同复合键+同canonical create重放 | 返回同Task、同top-level Intake identity、同Audit；不创建第二current root；已accepted Snapshot/Item identity不重复 |
| `S01-A15` | Idempotency | 同复合键 + 不同 payload/audit/metadata 重放 | `409 task-identity-conflict`；原记录不变 |
| `S01-A16` | Audit | 尝试 PUT/PATCH Audit 或通过 Task PATCH 携带 audit | route 不存在或 strict reject；Audit bytes/fields 不变 |
| `S01-A17` | Time | 上游 created_at 非 UTC offset 输入 | 合法时接受并 normalize 查询输出；另存 MKB received_at，不覆盖原事实 |
| `S01-A18` | Audit | audit_status 分别为 pending/approved/rejected/waived/not_required | 均只按 schema 保存；Task admission 不因 status 分支 |
| `S01-A19` | Concurrency | stale expected_revision PATCH | `409 revision-conflict`；current state 不变 |
| `S01-A20` | Surface | 首版 API/配置扫描 | 无 webhook URL、callback secret、callback retry worker |
| `S01-A21` | Task authority | 外部 PATCH status/progress/result/payload | strict reject；只能使用允许字段或 command |
| `S01-A22` | Contract | payload_extra 含合法嵌套 JSON | round-trip；核心执行不读取保留键改变状态机；非 object 拒绝 |
| `S01-A23` | Request intents | 未知 request_intent 或 payload 与 discriminator 不匹配 | fail-loud，不入库 |
| `S01-A24` | Retrieval | 同步 retrieval.search | 不创建 Task/Audit/Execution/Process 行 |
| `S01-A25` | Architecture | domain/application import 03-nano/NACP adapter DTO | dependency gate 失败 |
| `S01-A26` | Standalone | 03-nano 完全不可达时启动和执行合法 Task | MKB 可独立完成；未来 adapter health 不影响 core readiness |
| `S01-A27` | UUID generator | 批量生成内部Intake/Execution/Process/Event ID | 全部为UUIDv7，无碰撞；时间排序只作优化，不作正确性前提 |
| `S01-A28` | Task lifecycle | 对已失败 Task 发出完整 retry command | task_uuid/trace_uuid 不变；产生新 UUIDv7 current root execution_uuid 与新 Processes；retry-of 指向旧 Execution，旧 Execution 保持终态 |
| `S01-A29` | Soft delete | 删除 Team 或 Task | 历史 Audit 与 durable Execution summaries 仍存在且可查询；不级联物理删除；Process retention 只按 D01/S03/S15 fence 执行 |
| `S01-A30` | Polling | Task 分别处于 not-ready/succeeded/failed/cancelled | 调用者能稳定区分状态；成功时得到 result/artifact 引用，失败时得到结构化错误 |
| `S01-A31` | Contract migration | Task Create 携带旧 `task_type`、execution_uuid、process_uuid 或内部 status | strict reject；adapter 外的 core 无兼容 alias；无业务行 |
| `S01-A32` | Architecture | schema/model/import 扫描 | 不存在 Attempt identity、`attempt_uuid`、`task_attempts`；Execution 是唯一完整运行身份 |
| `S01-A33` | Single ingress | single`intake.ingest` | 一个Task、一个current root；accepted Snapshot通常一个membership；内部clean→LS-RAG→publication；外部只轮询Task |
| `S01-A34` | Scatter ingress | IntakeSource一次accepted Snapshot产生N required Items | 一个Task、一个current root、N child Executions；Task无singular current_process；counts与Snapshot/ChangeSet对账 |
| `S01-A35` | Authority | caller 尝试以 execution/process UUID 触发、取消、retry 或改状态 | public Task Contract 不提供该写面；只能按 Task command 表达 intent |
| `S01-A36` | Completion guard | queue 为空/callback 成功，但向量或 filter metadata proof 缺失 | Execution/Task 不得成功；polling 返回未完成或结构化失败 |
| `S01-A37` | Human gate polling | clean完成且Execution有open gate | Task保持`running`；Get Task返回bounded`action_required`与安全gate link，不返回execution/process/fence |
| `S01-A38` | Gate authority | caller直接PATCH Execution/Process或提交stale target/gate revision | direct route不存在；stale decision冲突且无状态变化 |
| `S01-A39` | Gate decision | authorized exact decision重复送达 | same idempotency/target/action幂等；append+CAS+outbox后恢复same Execution |

### 6.1 验收证据要求

S01 实现验收包至少包含：

1. OpenAPI/JSON Schema snapshot；
2. Pydantic strict/frozen model unit tests；
3. Turso 实际驱动下的原子事务与并发测试，而非仅 mock；
4. API integration tests；
5. idempotency 和 revision race tests；
6. dependency/import architecture test；
7. DDL inspection，证明复合 PK、Audit FK、`tasks/executions/processes` 三层核心表、独立 `task_restarts` 因果表、无 Attempt identity，以及业务表 `payload_extra`；
8. failure injection evidence；
9. standalone single journey：register team → create task+audit → root Execution → RAG Processes → proof → poll terminal/result；
10. standalone scatter journey：one Task → root controller → N child Executions → fan-in → aggregate polling；
11. 反例测试：03-nano 不可用、callback 不存在、旧 `task_type` 被拒绝、外部 execution/process/status patch 被拒绝。

### 6.2 跨 Domain 回填要求

| 下游 Spec | 必须继承/进一步冻结的内容 |
|---|---|
| `S02` | **已由S02-v1.3冻结并完成状态族校准**：Task六态、request_intent、priority、URI/response/error、soft-delete、cancel/retry、scatter/generation/restart及running+action_required/gate subresource；不得吸收内部Process状态或改变identity/audit/patch权限 |
| `S03` | commit 后可 claim；Execution tree、current root、Process registry、UUIDv7、root trace、retry-of、claim/lease/fencing与semantic recovery；禁止 Attempt identity与独立通用Reconciler产品 |
| `S04` | **已由S04-v1.2承接**：五类Intake UUID、ExternalKey/team fence、Snapshot/Membership、Revision、typed CandidateSet acceptance、serving/delete/rebuild/purge；Intake graph不得与Execution tree或review gate混用 |
| `S05` | **已由S05-v1.1承接**：四类source kind、strict descriptor、typed acquisition/candidate/clean、single/scatter seal、mandatory preflight、ExecutionGate与S05 binding；caller不提交adapter/validator/Outcome/Execution topology |
| `S08/S09` | index.rebuild strict scope、vector/filter publication proof；同步 retrieval 不落 Task/Execution/Process |
| `S12` | Team/Task/Audit/TaskRestart/Execution/Process DDL、三层 FK/self-FK、restart causation、事务、fingerprint、revision、payload_extra schema gate；禁止 task_attempts 与 clean/rag process 分表 |
| `S15` | Audit 与 Event/Log 分离；team/task/trace/execution/process correlation；Process cleanup 与 Event/Log retention 分开；reject event 不创建业务行 |
| `S16` | simple token 实现、network boundary、rotation、limits；不得引入 team RBAC |
| `17` | standalone topology + optional future adapter，不把 03-nano 作为 core runtime dependency |

---

## 7. Reference-anchor 台账

> Anchor 是事实证据，不是待迁移代码清单。`保留`表示保留业务语义，`改写`表示只借鉴意图，`删除`表示不得进入新系统。

| Anchor ID | `file:line` | 亲验事实 | 新系统裁决 |
|---|---|---|---|
| `S01-RA01` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/lib/rpc-meta.ts:4` | main skill-core RPC 的合法入边只有 agent-core；注释明确 orchestrator-core 主 face 未接线。 | 证明不能假设 orchestrator 已可直接调用任意 skill-worker；`删除`兼容前提。 |
| `S01-RA02` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/lib/rpc-meta.ts:28` | main face allowlist 只有 `agent-core`。 | MKB core 不复用该 caller gate；`删除`。 |
| `S01-RA03` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/lib/rpc-meta.ts:81` | orchestrator-core 只在独立 discovery whitelist 中被允许。 | 未来 adapter 可参考分面思想；`改写`。 |
| `S01-RA04` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/worker-entry-discovery.ts:5` | discovery face 只读，invoke/cancel/register/publish 等写方法物理缺席。 | 证伪“已存在通用调用入口”；`删除`兼容声称。 |
| `S01-RA05` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/worker-entry-discovery.ts:36` | 暴露方法是 health、version、listSkills、getSkill。 | 能力 read model 可借鉴；不是 MKB Task API；`改写`。 |
| `S01-RA06` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/service-target.ts:2` | service target 被描述为转发到 skill-runner，而非通用业务 worker。 | 禁止把 MKB 塞进该现状通道；`删除`。 |
| `S01-RA07` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/service-target.ts:32` | 唯一允许 binding 是 `SKILL_RUNNER`。 | 证伪任意外部 service binding；`删除`。 |
| `S01-RA08` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/service-target.ts:68` | service 输入必须 `{code}`，未知 binding/缺 code 直接失败。 | 与 LS-RAG Task Contract 不兼容；`删除`。 |
| `S01-RA09` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/dispatch-schemas.ts:50` | 当前 invoke body 仅 `skill_key/input/session_uuid/variant`，cancel 使用 invocation_uuid。 | 上游必须另做 task/audit 映射；`改写`。 |
| `S01-RA10` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/dispatch/invoke.ts:60` | skill invoke 从 authority 取 team，并解析当前私有 invoke schema。 | team 下传思想可保留，authority/private DTO 删除；`改写`。 |
| `S01-RA11` | `/mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/dispatch/invoke.ts:92` | skill-core 在收到请求后自己生成 `invocationUuid`，同时保存上游 requestUuid/traceUuid。 | invocation_uuid 不能直接充当 caller-owned MKB task_uuid；`删除`身份等价。 |
| `S01-RA12` | `/mnt/usb/web-dev/03-nano/workers/orchestrator-core/migrations/014-skill-registry.sql:76` | `invocation_uuid` 是 PK，`request_uuid` 只是普通 nullable 列；状态模型是 skill invocation。 | 不复用该表；MKB 使用 team-local Task 复合 PK；`删除`。 |
| `S01-RA13` | `legacy-family/smind-admin/ingestion/files.ts:528` | 文件确认后才内部生成 job UUID，并把 trace/file/job/workflow/team 一起发往 dispatcher。 | 保留 identity 分离与 team/trace 贯穿；job 生成时机/队列拓扑 `改写`。 |
| `S01-RA14` | `legacy-family/smind-admin/ingestion/urls.ts:127` | URL File 已创建后再生成 job UUID 并 enqueue。 | 证伪 legacy job 是外部稳定 Task ID；`改写`。 |
| `S01-RA15` | `legacy-family/smind-admin/ingestion/apis.ts:135` | API ingestion 同样内部生成 job UUID，且 authority 带 user/team plan。 | 任务语义可借，user/plan authority `删除`。 |
| `S01-RA16` | `legacy-family/smind-clean-dispatcher/core/schemas_smcp.ts:102` | case mode 定义 first_insert/full_update/context_meta_update/deactivate 与 purge hint。 | 仅映射为外部 request intents / Execution mode 输入；不得成为内部 generic task type；`保留并重命名`。 |
| `S01-RA17` | `legacy-family/smind-clean-dispatcher/core/schemas_smcp.ts:174` | Workflow Start 明确分离 trace/file/job/workflow、authority/control/extra 和 send_at。 | 保留身份、控制/扩展分面与时间；用 D01 Execution/Process 重构 job/step，删除 worker starter/domain 拓扑；`改写`。 |
| `S01-RA18` | `legacy-family/smind-admin/core/schemas_common.ts:96` | legacy Team 同时包含 credit、paid plan、created_by_user 等平台字段。 | 作为反例；新 Team Registry 明确 `删除`这些字段。 |
| `S01-RA19` | `legacy-family/smind-admin/services/team.ts:71` | legacy Team Create 检查 user membership，并事务绑定 user owner、初始化 balance/plan。 | 整段平台 ownership 行为不迁移；`删除`。 |
| `S01-RA20` | `legacy-family/smind-admin/ingestion/apis.ts:82` | legacy ingestion 用 team plan 和 phone verification gate workflow。 | 属于上游平台责任；MKB 只校验内部 token + registered active team；`删除`。 |

### 7.1 Reference 复验命令

```bash
nl -ba /mnt/usb/web-dev/03-nano/workers/skill-core/src/lib/rpc-meta.ts | sed -n '1,145p'
nl -ba /mnt/usb/web-dev/03-nano/workers/skill-core/src/worker-entry-discovery.ts | sed -n '1,80p'
nl -ba /mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/service-target.ts | sed -n '1,130p'
nl -ba /mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/dispatch-schemas.ts | sed -n '50,75p'
nl -ba /mnt/usb/web-dev/03-nano/workers/skill-core/src/runtime/dispatch/invoke.ts | sed -n '50,125p'
nl -ba /mnt/usb/web-dev/03-nano/workers/orchestrator-core/migrations/014-skill-registry.sql | sed -n '76,112p'
nl -ba legacy-family/smind-admin/ingestion/files.ts | sed -n '528,560p'
nl -ba legacy-family/smind-admin/ingestion/urls.ts | sed -n '127,167p'
nl -ba legacy-family/smind-admin/ingestion/apis.ts | sed -n '82,165p'
nl -ba legacy-family/smind-clean-dispatcher/core/schemas_smcp.ts | sed -n '102,192p'
nl -ba legacy-family/smind-admin/core/schemas_common.ts | sed -n '96,110p'
nl -ba legacy-family/smind-admin/services/team.ts | sed -n '71,135p'
```

---

## 8. Domain verdict

### 8.1 最终评价

**Verdict：`GO — accepted boundary truth`。**

MKB 不需要等待 03-nano skill-worker 机制定型，也不应该以当前 skill-core 的 invoke/registry 形状作为重构地基。当前最稳健、也最符合 owner 目标的路径，是先交付一个拥有自洽 Team/Task/Audit 契约、并以内部分层 Execution/Process 执行的 standalone leaf-worker，再由未来上游负责映射。

S01 已冻结以下承重结论：

1. MKB Contract 优先于任何当前上游私有协议；
2. Task 由上游以 `(team_uuid, task_uuid)` 创建，并携带 root trace 和 immutable Audit；
3. Team 是本地接入投影，不是平台 ownership；
4. Task + Audit 原子落库，Audit 独立且永不可改；
5. 上游只能表达 `request_intent`；Task 聚合、Execution workflow run 与 Process 工序状态属于 MKB；
6. 首版 polling，不做 webhook；
7. 所有领域 ID UUID 化，外部 v4/v7、内部 v7；
8. 所有 MKB 业务表具备 `payload_extra`，但核心字段继续严格；
9. 简单 token 提供全功能内部访问，不重建 RBAC；
10. future skill-worker 只是 adapter，不是 MKB 本体；
11. Task lifecycle 与 Workflow lifecycle 已分离：Task 是 ACK/CRUD 边界，Execution 是 durable run，Process 是具体工序；
12. Attempt identity 已废止；完整 retry 创建新 Execution，自动工序 retry 保持 Process；
13. single Intake使用一个root Execution，API scatter使用一个root controller + N child Executions；
14. `task_type` 已更名并收敛为外部 `request_intent`，不得承担 RAG process 分类；
15. Task 成功必须来自 current root 的 durable completion proof，LS-RAG build/rebuild 必须验证向量与 filter metadata publication。
16. Task 六态、scatter collect-all、cancel CAS、full retry generation 与 atomic rebuild 新 Task 已由 S02 冻结；所有人工重启因果进入 `task_restarts`，状态仍归 Task。

### 8.2 当前仍未被 S01 声称为已解决的事项

S01 的 contract 已接受，但实现尚未开始；下列事项仍需对应 spec 冻结：

- Task/restart具体retention时长（聚合状态机、priority、cancel/retry/delete、HTTP error、action_required与lineage已由S02-v1.3冻结）；
- Execution/Process 精确状态机、workflow definition、queue/outbox/claim/lease/fencing 与 crash recovery（S03/S12）；
- `intake.ingest`完整source descriptor字段已由S05冻结；仍待S02/OpenAPI固化exact wire，gate decision exact URI/envelope与authority待S02/S16承接；
- vector/filter publication proof 的 exact schema 和验证算法（S08/S09/S12）；
- token rotation、network exposure 和 rate limit（S16）；
- capability 细节与健康/readiness 指标（S11/S15）；
- future 03-nano adapter 的实际协议（上游稳定后另开 gate）。

这些未决项不得反向改变 S01 已冻结的 Task/Execution/Process identity split、atomic audit、team projection、request-intent/process-type separation、single/scatter 基数、polling 和 authority 边界；如确需改变，必须 reopen 本文与 D01。

### 8.3 一句话结论

> **上游只创建可轮询的 Task；MKB 用 durable Execution 和 RAG-specific Processes 完成 single/scatter 工作并提交可验证结果——未来是谁来编排，只决定 adapter，不决定这条核心真相。**

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `S01-v0.1` | `2026-07-15` | `MKB owner + Codex` | `owner-gate` | 汇总 03-nano 与 legacy-family 事实，提出 Q1–Q26。 |
| `S01-v1.0` | `2026-07-15` | `MKB owner + Codex` | `accepted` | Owner 接受全部判断；冻结 standalone boundary、UUID law、Team Registry、Task/Audit 原子契约、polling、token 与 future adapter 边界。 |
| `S01-v1.1` | `2026-07-15` | `MKB owner + Codex` | `accepted / D01-calibrated` | 按 owner-originated D01 全面校准：废止 Attempt，采用 Task/Execution/Process；`task_type` 改为 `request_intent`；补入 single/scatter、三表状态架构、retry、proof、权限与验收约束。 |
| `S01-v1.2` | `2026-07-15` | `MKB owner + Codex` | `accepted / D01+S02-calibrated` | 接收 S02-v1.0：回填六态/散射/retry generation/atomic rebuild 边界；新增独立 `task_restarts` 因果/admission truth，将最小 durable 业务真相集合校准为五张。 |
| `S01-v1.3` | `2026-07-15` | `MKB owner + Codex` | `accepted / D01+S02+S04-calibrated` | 接收S04-v1.0：将document.* intents/document_uuid与Source/Document/Version资源口径校准为intake.*、intake_item_uuid和五类Intake identities；single/scatter改以Snapshot/Membership/ChangeSet表达，rebuild不创建IntakeRevision。 |
| `S01-v1.4` | `2026-07-16` | `MKB owner + Codex` | `accepted / D01+S02+S04+S05-calibrated` | 接收S05-v1.0：登记mandatory preflight为内部Process capability；human review为Execution-owned gate；Task polling增加bounded action_required/read/decision语义面但继续禁止外部Execution/Process写；补充gate supporting truth、authority和验收边界。 |
| `S01-v1.5` | `2026-07-18` | `MKB owner + Codex` | `accepted / D02-state-calibrated` | 不改变MKB Contract或状态enum；明确Task status、result readiness、TaskItem outcome、action_required与soft-delete正交，继续禁止caller把Execution/Process/phase/Gate/Intake状态写回公共Task面。 |
| `S01-v1.5-cal` | `2026-08-11` | `MKB owner + Codex` | `accepted / S06-calibrated` | 接收S06-v1.0：Task-scoped generation只读投影；无generation写面/精修产品。 |
| `S01-v1.5-cal-s12` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S12-v1.0：Task+Audit原子与team持久化由S12兑现。 |
| `S01-cal-s13` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S13-v1.0：无公网 object API；payload 禁正文/path。 |
