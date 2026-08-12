# S03 — Declarative LS-RAG Workflow Engine

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D2 任务执行 / S03 Declarative LS-RAG Workflow Engine`
>
> **日期**：`2026-07-18`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted / D02-state-calibrated`（S03 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S03-v1.3`
>
> **上游权威输入**：`D01-v1.4`、`S01-v1.5`、`S02-v1.3`、`S04-v1.2`、`S05-v1.1`、`S06-v1.0`、冻结的`qna-truth/S03.md v1.0`（Q1–Q9 / `T-O-12..29`）
>
> **事实证据**：`legacy-family/` 中 SMCP、Workflow editor/compiler、Clean/RAG Dispatcher、Process tracking、restart 与 atomic scatter 生产实现
>
> **下游消费者**：`S04-S09`、`S11-S15`、跨系统拓扑 `17`、验收冻结 `18`

> **Owner-gated 约束**：S03 不是 generic workflow SaaS，也不是 legacy Dispatcher 的本地复刻。它必须保留 legacy 的声明式、多平面、Process 解耦优势，同时以 MKB 自己的关系型 Workflow truth、统一 Execution/Process 状态机和本地 durable recovery 消除历史补丁与部署负债。

> **跨文档审计声明**：S03 QNA 已与 D01/S01/S02 完成身份、状态、single/scatter、retry/cancel、proof、queue、recovery 与 cleanup 对账，结论为 `PASS / NO REOPEN REQUIRED`。本文中的 exact state/schema 是上游明确授权 S03 完成的下游精化，不改变 Task 产品语义。

> **S04校准声明**：S03原有`Source/Document/Version/manifest`是S04冻结前的资源占位词。本版将MKB资源binding、fan-out分母、proof target和cleanup cutoff校准为`IntakeSource/IntakeSnapshot/IntakeItem/IntakeRevision/IntakeChangeSet/IntakeArtifact`；Workflow/Execution/Process状态机与七张定义表不变。

> **S05校准声明**：S05-v1.0不改变Workflow七表、Execution/Process exact states或Engine路由权。PreflightValidator作为普通leaf Process capability提交typed Outcome；human review使用Execution既有`waiting`并以`human_review`+exact gate ref作为durable trigger，Process先terminal。Execution额外锁定S05 domain binding；四个crash窗口复用本域transition/repair与S12 outbox，不新增Reconciler。

> **D02状态校准声明**：D02-v1.0已镜像Execution/Process八态、合法边与正交事实，并冻结`T-O-86..92`；本版不改变Workflow七表、retry/cancel/recovery或phase registry。状态、phase、waiting reason、ProcessOutcome、route decision和资产状态严格分账；S05 exact intake capability key取代S03早期coarse intake key作为实际manifest identity。Execution ingress subject与acceptance后exact output的物理字段归S03/S04/S12，embedding与index工序拆分归S08/S09；二者是D02下游移交，不再等待D02裁决。

> **S06校准声明**：`S06-v1.0`冻结`lsrag.structurize`业务contract、ProcessCommand+input digest冻结、GenerationArtifact/pointer（非StateFamily）与仅自动retry收敛。S03继续独占Process八态/claim/fence/max-retries与route；S06 leaf只返回ProcessOutcome+generation refs/proof。phase `structurizing`仍只是业务坐标。meta-only/index rebuild跳过structurize须用typed route与exact structure generation ref，禁止step-name字符串匹配。完整HITL不因S06进入S03新状态。

> **S12校准声明**：`S12-v1.0` 兑现 claim/fence/lease、transactional outbox、先commit后wake、七表+executions/processes 物理存放与单一migration；Concurrent Writes 默认启用服务并发claim。S03仍拥有状态边与recovery语义；S12不定义route。

> **S11校准声明**：`S11-v1.0` 冻结 Inference≠Adapter、transport 有界退避（**不计入** Process `retry_count`）、`INFERENCE_BACKPRESSURE`（retryable，与 claim 正交）、禁 silent 换模型。S03 继续拥有 max-retries/retry_wait 账本与 Outcome `retryability` 消费；工序叶调用模型必须经 `runtime.inference`，不得直连 adapter。

> **D05校准声明（T-O-202/207/208/210）**：S03 继续独占 max-retries 与 Outcome 上卷（D05 **不**另建失败真相）。知识生产链 phase：`cleaning`（**promptA**）→ `structurizing`（**promptB**）→ `constructing`（**promptC**）→ `vectorizing_indexing` → `validating_publication`。Command materialize 须冻结各叶 `PromptRef`（promptA/B/C + hash）入 input digest。`lsrag.vectorize_index` 仍为 coarse placeholder；**不得**在 construct full_valid 前调度 vectorize（T-O-206）。
---

> **S13校准声明**：`S13-v1.0` 冻结 v1 本地 `object_root` + `ObjectStorePort`、`mkbobj:v1` handle、team-scoped CAS、bytes-first、同库 catalog/ref/purpose、verify-on-read、周期 GC 与 identity readiness。本文件业务语义不变；对象 I/O 必须经 S13 Port，禁止 path/R2 key 进入契约。

## 1. Domain 介绍

### 1.1 Domain 价值

S03 是 MKB 单体内部唯一 durable、declarative、future-agent-ready 的 LS-RAG Workflow Engine。它把内部注册的 Workflow Program 编译成可复验计划，把 Task intent 实例化为 Execution tree 与 RAG-specific Processes，并在崩溃、重放、scatter、retry 和 cancel 下维持唯一可解释的运行真相。

S03 解决六个核心问题：

1. Workflow 如何保持声明式、可编程，却不再把所有控制平面塞进 mutable JSON；
2. Workflow Definition、compiled representation、Execution 和 Process 如何拥有清晰且互不重叠的真相边界；
3. Clean、Structurize、Construct、Vectorize/Index、Publication Validation 等工序如何通过统一 command/outcome contract 解耦；
4. Process 如何在本地 queue redelivery、并发 claim、worker crash 和 late Outcome 下只接受一次合法业务提交；
5. single与API scatter如何共用一套Execution/Process engine，并完成Snapshot/ChangeSet-driven fan-out/fan-in；
6. DB/queue/leaf side effect 无法形成单一原子事务时，系统如何用 semantic recovery 自动关闭断点，并在不破坏审计的前提下清理短期 Process projection。

### 1.2 在整体拓扑中的位置

```text
S02 Task API / lifecycle
  │ committed Task + current-generation scheduling intent
  │ cancel/full-retry command
  ▼
S03 Workflow Engine
  ├── Internal Workflow Registry（七张 normalized truth tables）
  ├── Registration Validator + Deterministic Compiler
  ├── Workflow Resolver + immutable Execution binding
  ├── Typed Route/Guard Engine
  ├── Execution Tree Controller
  ├── Process Materializer + Transition Service
  ├── Local Scheduler Contract（claim/lease/fencing）
  └── Semantic Recovery + cleanup eligibility
         │
         ├── ProcessCommand → S05-S09 leaf capabilities
         ├── IntakeSnapshot/ChangeSet decision refs ← S04
         ├── Candidate/Preflight/Gate refs ← S05
         ├── model/prompt refs ← S11/S14
         ├── transaction/outbox/queue/cleanup → S12
         ├── Intake/derived asset handles → S13
         └── event/log/metric/alert → S15

Outcome/proof
  → Process transition
  → Execution summary
  → S02 Task aggregate projection
```

### 1.3 Scope fence

S03 负责：

- 六平面 Workflow Contract；
- 内部 Workflow registration、revision、activation、disable/deprecate 与只读 list/get；
- 七张 normalized Workflow definition/control truth tables；
- versioned `ProcessCapabilityManifest`与typed port registry；
- registration-time graph、binding、control、guard、capability 与安全校验；
- canonical compiled JSON、canonical digest 与 immutable Execution binding；
- typed/guarded/acyclic route graph、deterministic branch、同 Execution Process fan-out/fan-in；
- `ProcessCommand/ProcessOutcome` 本地强契约；
- Execution/Process exact control state、RAG phase、claim/lease/fencing、retry/backoff/timeout；
- single/scatter Execution tree、Snapshot/ChangeSet-driven child materialization、collect-all与cancel convergence；
- Workflow semantic recovery invariant 与 Process projection cleanup eligibility；
- 运行时必须产生的 correlation、route decision、transition 与 proof evidence 语义。

S03 不负责：

| 排除项 | 权威归属 | S03 边界 |
|---|---|---|
| Task HTTP、六态、PATCH、cancel/full retry admission、`task_restarts` | `S02` | 消费 committed command/current generation，发布 aggregate outcome |
| IntakeSource/Snapshot/Item/Revision/Membership/ChangeSet业务真相 | `S04` | 只读取immutable Intake refs/typed decisions |
| Clean、Structurize、Construct、Vectorize 的算法与业务 schema 内容 | `S05-S09` | 只登记 capability/port/contract ref 并验证 Outcome |
| Vector/filter publication proof 的业务计算 | `S08-S09/S12` | 只要求 proof contract 并把 ref/digest 上卷 |
| Model/prompt 内容、fallback 与 registry policy | `S11/S14` | 只绑定 immutable logical ref/version/digest |
| Turso exact DDL、transaction driver、outbox、queue 与物理 cleanup | `S12` | 冻结必须成立的约束、CAS、原子性和 repair semantics |
| IntakeArtifact/derived asset backend、路径、原子写 | `S13` | 只传logical handle/ref/digest；禁止绝对路径进入契约 |
| Event/Log/Trace envelope、retention 时长、告警与 runbook | `S15` | 规定必须产生的 evidence/correlation，不拥有其物理模型 |
| token 保存、网络暴露、内部诊断授权 | `S16` | 只声明 read/write surface 与最小权限要求 |
| agent 直接 author/modify/validate/publish Workflow | future reopen | v1 只保证 schema/interface future-agent-ready |

### 1.4 Domain 完成定义

S03 在实现层完成必须同时满足：

1. §2 全部 Truth ID 被 schema、compiler、transition service 和 contract test 实现；
2. 七张 Workflow truth tables 的 FK/unique/check/immutable boundary 通过 S12 集成测试；
3. 同一 revision 重编译得到 byte-identical canonical JSON 与相同 digest；
4. 任何跨 revision wiring、graph cycle、unreachable required step、port mismatch、自由表达式或 secret/path binding 在 registration 时失败；
5. Process/Execution exact state transition matrix、claim race、stale Outcome、retry/recovery 分账通过并发与故障注入；
6. single/scatter、partial fan-out crash、collect-all、cancel convergence、early publication/no rollback 通过 golden scenario；
7. semantic recovery 重复运行幂等，不重复创建 Process/child Execution 或业务提交；
8. Process cleanup 前后 Execution/Task/result/lineage/proof 查询语义等价；
9. 外部只有 Workflow list/get，无 CUD、无 graph injection、无 Execution/Process 写面；
10. §6 的强制验收矩阵全部通过。

---

## 2. 真相层

### 2.1 真相层纪律

本节是 S03 的 SSOT。来源分为：

- `OWNER-QNA`：冻结的 S03 Q1–Q9 / `T-O-12..29`；
- `UPSTREAM`：D01/S01/S02 已接受真相；
- `LEGACY-FACT`：生产代码证明的真实行为、失败窗口或既有围栏；
- `ACCEPTED-VERDICT`：在上述输入内形成的 S03 正式设计裁决。

Legacy 只能证明需求和失败模式，不能把 Cloudflare Worker/Queue/Durable Object、D1/R2、SMCP 网络 callback、clean/rag 分表或 mutable workflow JSON 带入 MKB。

### 2.2 Workflow 宪法与治理真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S03-T001` | S03 是 MKB 单体内部唯一 LS-RAG Workflow Engine；Task lifecycle 与 Workflow lifecycle 分离。 | `T-O-12 + D01/S01/S02` | 不得创建第二套 Dispatcher/Engine 或把 Task 改成工序状态机。 |
| `S03-T002` | Workflow 是 Resource/Context、Authority/Admission、Process Capability、I/O/Dataflow、Orchestration/Control、Outcome/Evidence/Observation 六平面声明式程序；topology 只是 Control 子平面。 | `T-O-12` | 不得把 Workflow 降级为 step list、DAG JSON 或 generic payload。 |
| `S03-T003` | v1 Workflow 只允许 MKB code/migration/bootstrap 内部注册；外部只有 list/get compiled detail，无 create/update/delete。 | `T-O-13/T-O-14` | Task caller、tool、agent 不得注入或修改 graph/control。 |
| `S03-T004` | v1 不实现 agent authoring/publish；schema/interface 必须 future-agent-ready，未来接入必须 reopen。 | `T-O-13` | 不建设 draft workspace、agent tool loop 或 delegated publish。 |
| `S03-T005` | Workflow 定义/control 的 durable SSOT 是七张 normalized relational tables；core truth 禁止 opaque JSON。 | `T-O-15/T-O-17/T-O-18` | S12 不得用单列 `steps_definition/config_json` 代替。 |
| `S03-T006` | compiled JSON 是可重建、只读、声明式派生物，不是第八张 Workflow truth table。 | `T-O-16/T-O-18` | cache 丢失必须可重建；compiled JSON 不能反向写七表。 |
| `S03-T007` | registry active revision pointer 是当前激活 SSOT；已激活 revision immutable，被 Execution 引用时不得物理删除。 | `T-O-17/T-O-20` | 变化只能新 revision + guarded pointer switch；运行中不热切。 |
| `S03-T008` | Workflow Definition identity 与 D01 runtime identity 分离；Workflow/Revision/Step UUID 不构成 Task/Execution/Process/Attempt。 | `T-O-17 + UPSTREAM` | 七表不保存一次运行的 claim/retry/outcome。 |

### 2.3 Schema、图与编译真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S03-T009` | 七表固定为 `workflow_registry/revisions/steps/routes/bindings/controls/guards`；职责不得合并回 JSON 或按 Process 类型复制。 | `T-O-17` | exact physical type 可由 S12 调整，职责和约束不可变。 |
| `S03-T010` | 每个 child row 必须显式归属 immutable revision；跨表 wiring 只能发生在同一 revision。 | `T-O-17` | FK/unique + compiler 双围栏阻止跨 revision 引用。 |
| `S03-T011` | v1 route graph 是 typed、guarded、acyclic RAG graph；单 start、typed terminal、required reachability/terminal coverage 必须静态成立。 | `T-O-19` | v1 禁止业务 loop/recursion；retry/cancel 不画 graph self-loop。 |
| `S03-T012` | route 只允许 registered outcome selector、guard/operator/operand 与 deterministic priority；禁止 Python/SQL/自由表达式。 | `T-O-18/T-O-19` | 相同输入/revision 必须得到相同 route decision。 |
| `S03-T013` | 允许 branch、同一 Execution Process fan-out/fan-in、required/optional predecessor 与 typed terminal；expected set 必须先 durable。 | `T-O-19` | API scatter child 仍是 Execution，不得降级成 step/process item。 |
| `S03-T014` | Workflow binding只使用typed logical context/Intake/derived asset/model/prompt refs；禁止absolute path、secret和未校验正文。 | `T-O-17/T-O-21 + S04` | S13/S14 adapter决定物理解析；compiled view不泄密。 |
| `S03-T015` | Process step必须引用versioned `ProcessCapabilityManifest`的`process_key + contract_version`，ports/parameters/proof/idempotency必须静态兼容。 | `T-O-12/T-O-17/T-O-21` | S04-S09提供manifest；S03不解析业务算法。 |
| `S03-T016` | registration 必须先写/校验完整 revision，再 deterministic compile 和 digest；任一检查失败不得激活。 | `T-O-20` | 不允许 partial revision 或“先上线再修”。 |
| `S03-T017` | Execution 创建时 durable 绑定 exact workflow/revision/compiled digest；同 Execution retry/recovery 不热切 revision。 | `T-O-20` | registry disable/deprecate 只影响未来 resolver。 |
| `S03-T018` | full Task retry 创建新 Execution generation但继承来源 root 的 exact revision/digest；新的独立 rebuild/update/delete Task 才按当时 active resolver 重新选择。 | `ACCEPTED-VERDICT + S02 retry semantics` | full retry 保证可复验，不借 retry 偷换程序。 |

### 2.4 Process Contract 与运行边界真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S03-T019` | Engine 解释 compiled plan，只在 step eligible 时 materialize Process；未命中 route 不创建 Process，只保存 route decision evidence。 | `T-O-21/T-O-22` | Process table 不存 future/skipped 假实例。 |
| `S03-T020` | Process row、resolved input/control snapshot/ref、spec digest 与 scheduling intent 必须在 wake-up 前 durable。 | `T-O-20/T-O-21/T-O-23` | queue/in-process call 只是 transport；commit 前不可执行。 |
| `S03-T021` | Process 只消费集中 schema 的 `ProcessCommand` 并返回 `ProcessOutcome`；不找 route、不建下游、不推进 Execution/Task、不选择物理存储。 | `T-O-21` | leaf handler 不依赖完整 Workflow JSON。 |
| `S03-T022` | Outcome 必须通过 identity/revision/spec digest、current fence、contract version、typed output/hash 与 type-specific proof guard 后才可提交。 | `T-O-21/T-O-23` | 函数返回、queue ACK、callback 或日志不构成成功。 |
| `S03-T023` | 所有 Process 类型使用统一 `processes` state model；不得恢复 clean/rag/vector process 分表。 | `D01/S01 + T-O-22` | Vector units 是资产，不是 Process。 |
| `S03-T024` | Process capability至少覆盖IntakeSource resolve/fetch、clean/CandidateSet、preflight validate、Snapshot acceptance、structurize、construct、vectorize/index、publication validate与受控purge/maintenance。 | `D01 + T-O-12 + S04-S05` | exact contract由S04-S09版本化，禁止generic`process_data`。 |
| `S03-T025` | Process I/O只保存logical Intake/asset refs、ChangeSet/digests；IntakeArtifact bytes、vector records、prompt/model内容留在权威下游。 | `UPSTREAM + T-O-21 + S04` | Process cleanup不得级联删除Intake truth或业务资产。 |

### 2.5 Process 状态、并发与 retry 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S03-T026` | Process exact states 只有 `ready/claimed/running/retry_wait/succeeded/failed/cancelling/cancelled`。 | `T-O-22` | 禁止 pending/retrying/completed alias 和隐藏状态。 |
| `S03-T027` | `ready→claimed` 必须 atomic CAS，并产生 claim token、lease owner/expiry 与递增 fencing generation。 | `T-O-23` | 同一 Process 同一时刻最多一个合法 fence。 |
| `S03-T028` | heartbeat、running transition 与 Outcome 只接受 current fence；stale/late Outcome 拒绝，已接受 Outcome 重放 no-op。 | `T-O-23` | leaf side effect 必须使用 process/fence/idempotency key。 |
| `S03-T029` | delivery、lease recovery、business retry 分账：`delivery_count/recovery_count/retry_count` 各自独立。 | `T-O-24` | redelivery/recovery 不消耗业务 retry budget。 |
| `S03-T030` | retryable business failure 才进入 `retry_wait` 并 `retry_count+1`；automatic retry 保持 process_uuid、execution_uuid 与 revision。 | `T-O-24` | 不得创建 Attempt 或新 Execution。 |
| `S03-T031` | non-retryable error、guard/proof failure或 `max_retries` 耗尽进入 failed；`retry_wait→ready` 由 durable due predicate推进。 | `T-O-24` | max-retries 必须止血，不能无限 pending。 |
| `S03-T032` | cancel intent 阻止新 claim/materialization；active Process 进入 cancelling，旧 fence 的 late commit 失效，安全停止/补偿后才 cancelled。 | `T-O-22/T-O-23` | cancel receipt 不等于 Process 已停止。 |
| `S03-T033` | claimed/running lease expiry 只在 contract 可安全重放且 effective `max_recoveries` 未耗尽时 fence 后回 ready；上限耗尽 fail loud 为 `recovery-exhausted`，side effect 不确定或不可幂等时 fail loud 为 `indeterminate-side-effect`。 | `T-O-23/T-O-28 + ACCEPTED-VERDICT` | recovery 不消耗业务 retry，但必须有独立止血上限；不得以“再跑一次”掩盖未知写入结果。 |

### 2.6 Execution、RAG phase 与 scatter 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S03-T034` | Execution exact control states 只有 `created/ready/running/waiting/succeeded/failed/cancelling/cancelled`。 | `T-O-25` | Task enum 与 Execution enum 不混用。 |
| `S03-T035` | RAG phase 与 control status 分列，并从 bound route 与 active Process set 归约。 | `T-O-25` | phase 不进入 Task status，不由 worker 任意写。 |
| `S03-T036` | `waiting` 必须持有 typed reason、durable trigger/ref 和可选 next wake time；无 trigger 的 waiting 是 invariant violation。 | `T-O-25/T-O-28` | 禁止 generic pending 黑洞。 |
| `S03-T037` | `current_process_uuid` 只允许 nullable focus/last pointer；并发 active set 以 `processes` 查询和 Execution counters 为真。 | `T-O-25` | pointer 不承担 fan-out membership SSOT。 |
| `S03-T038` | single使用同一个root Execution贯穿ingress→clean→acceptance→LS-RAG→publication validation；acceptance前绑定创建时已有的Source/input subject，acceptance后各下游Process只消费exact accepted IntakeItem/Revision binding。 | `T-O-26 + UPSTREAM + S04 + D02-CALIBRATION` | 不在Clean/RAG边界重生Execution/job，也不得让下游Process读取“latest”猜target；subject/output exact字段由S03/S04在S12物理schema中冻结并按D02-v1.0回填。 |
| `S03-T039` | scatter使用root controller + accepted IntakeSnapshot/ChangeSet + 0..N child Executions；child identity/required set来自S04 durable truth。 | `T-O-26 + UPSTREAM + S04-T024..T029` | 一个外部Task；禁止child Task。 |
| `S03-T040` | scatter root collect-all：healthy child 不因 sibling failure停止；全部 required terminal 后才归约 root。 | `T-O-26 + S02` | 不提供 partial-success Task terminal。 |
| `S03-T041` | proof-valid child可早发布；parent failure/cancel不隐式回滚；cancel是forward-stop。 | `T-O-26 + S02 + S04` | 可见性依据IntakeItem lifecycle + exact ServingRevision proof，不依据root/Task单一状态。 |
| `S03-T042` | Execution succeeded 必须满足 required routes/children terminal、guards/proof；non-retryable 或 retry-exhausted required path 才 failed；cancel descendants 收敛后才 cancelled。 | `T-O-27` | 终态由 Engine 自下而上归约，Process 不直写。 |
| `S03-T043` | terminal Execution必须保存workflow/digest、route/process/child counts、phase history、retry/recovery、final error、Intake/derived asset/Vector/proof与时间摘要。 | `T-O-27 + S04` | Process清理后仍能解释结果与成功依据。 |

### 2.7 Semantic recovery 与 cleanup 真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S03-T044` | 每个 nonterminal Execution 必须存在 claimable/due Process、typed durable wait、current-fenced lease或 cancelling descendants之一。 | `T-O-28` | 四者皆无即 stranded invariant violation。 |
| `S03-T045` | S03 定义 deterministic/idempotent repair transition；S12 实现 startup/periodic scan、outbox/transaction/wake-up；S15 记录 evidence/metric/alert。 | `T-O-28` | 不要求独立 Reconciler 产品，但不得删除恢复行为。 |
| `S03-T046` | repair 覆盖漏 wake、due retry、expired lease、terminal→next 断点、partial child materialization、join/fan-in、cancel 与 summary 未收口。 | `T-O-28` | 重复扫描 no-op；不能重复创建/提交。 |
| `S03-T047` | revision/digest/route/output/proof 冲突不得自动猜测；必须 failed + integrity quarantine evidence。 | `T-O-28` | quarantine 是 failure disposition，不新增第九个 Process/Execution state。 |
| `S03-T048` | Process cleanup eligibility 必须同时满足 Execution terminal、summary complete、retry/recovery/cancel/compensation/outbox/lease closed、无 dangling pointer。 | `T-O-29` | 任一条件不满足禁止 archive/delete。 |
| `S03-T049` | S03 只定义 cleanup eligibility；S12 物理清理，S15 独立保留 Event/Log；v1 无 S03 operator 写面。 | `T-O-29` | cleanup 不是压缩或 knowledge/vector purge。 |
| `S03-T050` | Workflow revision 只要仍被 Execution/summary/audit 引用就不得物理删除；compiled cache 可随时重建。 | `T-O-17/T-O-20` | registry cleanup 与 Process cleanup 是不同生命周期。 |

### 2.8 S05 Preflight 与 human gate 校准真相

| Truth ID | 冻结真相 | 来源 | 下游约束 |
|---|---|---|---|
| `S03-T051` | `intake.preflight_validate`是versioned ProcessCapabilityManifest；validator只读frozen evidence，正常Outcome为`passed|blocked`，runtime/schema/evidence错误仍走Process retry/failed。 | `S05-T016..18` | Validator不推进route、建gate或写Intake；Engine只消费typed Outcome。 |
| `S03-T052` | 只有需要人工输入时，Engine在Process terminal后创建/引用ExecutionGate，并将Execution CAS为`waiting(reason=human_review, ref=gate_uuid)`。 | `S05-T020..24` | 自动passed路径不建gate；Process不得持claim/lease等待。 |
| `S03-T053` | Execution binding除Workflow exact binding外，还必须引用actual S05 source/acquisition/clean/preflight binding及`s05_binding_digest`；retry/recovery/human resume均不可热切。 | `S05-T025..26` | 旧Task升级走S02 restart/new generation；同version异digest失败隔离。 |
| `S03-T054` | Outcome→route、gate→waiting、decision→outbox与late/stale四窗口调用正常transition service幂等repair；waiting永不自动approve。 | `S05-T029..30` | S03/S12不得从UI/log/storage/payload_extra合成decision，也不建设第二套gate recovery engine。 |

### 2.9 状态族校准矩阵

| 事实族 | Exact vocabulary | 谁推进 | 与Execution/Process status的关系 |
|---|---|---|---|
| Execution status | `created/ready/running/waiting/succeeded/failed/cancelling/cancelled` | Engine transition service | 唯一Execution控制状态 |
| Process status | `ready/claimed/running/retry_wait/succeeded/failed/cancelling/cancelled` | Process transition service | 唯一Process控制状态 |
| Execution phase | §4.9 registry | route/active Process deterministic归约 | 正交；terminal保留last phase，不新增completed |
| waiting reason | `retry_due/process_join/scatter_children/durable_prerequisite/human_review` | Engine CAS | 只在Execution `waiting`时存在，必须带durable ref |
| ProcessOutcome | `succeeded/failed/cancelled` + retryability | leaf提交、Engine验证 | immutable input；验证后才驱动Process状态边 |
| route decision | route key(s)+guard results+decision digest | Engine | immutable evidence；不是状态 |
| Preflight/Gate/Intake facts | S04/S05 exact词汇 | 各owner domain | 只作为typed route/trigger输入，不写入runtime status |

v1禁止新增`pending/retrying/completed/reviewing/partially_succeeded/quarantined`状态别名。`quarantine`只能是failed后的disposition/evidence；`action_required`只由S02投影；`CandidateSet accepted`也不能使Execution直接成功。

---

## 3. 总体方案陈述

1. **以六平面 Contract 保留 Workflow 竞争优势**：Workflow 同时描述资源上下文、权限、能力、I/O、控制和 outcome/evidence，不退化为 node graph。
2. **以七张关系表建立定义 SSOT**：Workflow identity、revision、step、route、binding、control、guard 全部可约束、可审计、可编译；自由 JSON 不再持有真相。
3. **以 internal registration 代替外部 Workflow CRUD**：v1 只由代码/migration/bootstrap 注册；agent authoring 以后通过受控 adapter 接入。
4. **以 deterministic compiler 产生声明式 JSON**：compiled representation 可读、可缓存、可重建；digest 把定义与每个 Execution 锁定。
5. **以ProcessCapabilityManifest约束每个RAG Process**：step必须绑定真实`process_key + contract_version + typed ports + proof kind`，不能使用generic task type。
6. **以 Engine-interpreted plan 保持 leaf 解耦**：Process 只看到自己的 Command/Outcome，不看到完整 Workflow，也不决定下一步。
7. **以 exact Process 状态和 fencing 统一本地执行**：ready/claim/lease/run/retry/terminal 只有一套 transition path；delivery、recovery、retry 分账。
8. **以 Execution control + RAG phase 双字段表达总体运行**：control 回答能否推进，phase 回答业务走到哪里；Task 仍保持六态。
9. **以同一Engine原生支持single/scatter**：single是IntakeItem/Revision root；scatter是IntakeSource/Snapshot root + ChangeSet + child Executions；collect-all是主路径。
10. **以 proof-gated aggregation 定义成功**：Process guard→Execution summary→Task aggregate，向量/filter publication proof 不可跳过。
11. **以 semantic recovery 关闭非原子窗口**：outbox 解决漏投递，Workflow repair 继续解决 lease、route、fan-out/fan-in、cancel 和 summary 断点。
12. **以 summary-before-cleanup 保持 durable 查询**：Process 可以短期化，但 Execution、Task、Audit/restart 与 Event/Log 证据不随之消失。

端到端控制流：

```text
Internal definition rows
  → registration validate
  → immutable revision + active pointer
  → canonical compile/digest
  → resolver binds Execution
  → route/guard eligibility
  → Process ready + scheduling intent committed
  → claim CAS + lease/fence
  → ProcessCommand
  → leaf outcome
  → fence/contract/output/proof validation
  → Process terminal or retry_wait
  → next route / join / child convergence
  → Execution terminal summary
  → Task aggregate CAS
  → recovery maintains invariants
  → Process cleanup when eligible
```

---

## 4. 具体执行方案清单

### 4.1 `S03-E01` — 建立七张 Workflow Definition/Control Truth Tables

#### 4.1.1 逻辑类型约定

本文冻结逻辑类型和约束语义；Turso/SQLite exact column type、deferred FK、trigger/migration 由 S12 冻结。

| 逻辑类型 | 语义 |
|---|---|
| `UUIDv7` | MKB 内生领域身份；边界严格校验 version |
| `UUID` | 上游 v4/v7 或内部 v7，根据字段来源校验 |
| `ENUM` | 数据库 CHECK + application enum 双验证 |
| `DIGEST` | `sha256:<64 lowercase hex>`；比较使用完整值 |
| `UTC_TS` | UTC、单调语义；物理精度由 S12 统一 |
| `LOGICAL_REF` | 权威下游生成的 opaque logical reference；禁止 absolute path/secret |
| `SCHEMA_REF` | versioned contract/schema logical key + digest |

#### 4.1.2 `workflow_registry`

| 列族 | 逻辑字段 | 约束 |
|---|---|---|
| Identity | `workflow_uuid UUIDv7 PK`、`workflow_key TEXT` | `workflow_key` 全局唯一、创建后不可改、不得复用 |
| Classification | `domain_key`、`purpose_key`、`execution_role`、`selector_key`、`selector_priority` | `domain_key=ls_rag`；purpose 对齐 registered request intent；selector 只允许内部 allowlist |
| Read/Governance | `read_exposure`、`registry_status` | exposure=`internal/readable`；status=`enabled/disabled/deprecated` |
| Active pointer | `active_revision_uuid nullable` | 必须引用同一 workflow 的有效 revision；`enabled` 时非空 |
| Description | `display_name`、`description` | 只读展示，不参与运行 digest |
| Audit | `created_at/updated_at`、`created_by_origin` | origin是code/migration/bootstrap provenance，不是IntakeSource或user identity |

Registry lifecycle：

```text
disabled ↔ enabled
    │          │
    └──────────┴──→ deprecated

deprecated 不再允许未来 binding；历史 Execution/revision 可读。
```

激活使用 guarded pointer switch；`workflow_revisions` 不保存第二个 `is_active`。

#### 4.1.3 `workflow_revisions`

| 列族 | 逻辑字段 | 约束 |
|---|---|---|
| Identity | `workflow_revision_uuid UUIDv7 PK`、`workflow_uuid FK`、`revision_number INT` | `(workflow_uuid, revision_number)` 唯一、number 单调 |
| Schema | `schema_version`、`capability_registry_digest` | 注册时必须受支持；capability digest 锁定编译依赖 |
| Provenance | `registration_source_kind`、`registration_module`、`source_commit_digest`、`migration_key`、`registration_fingerprint` | 至少一个可复验注册来源；fingerprint幂等 |
| Digests | `canonical_definition_digest`、`compiled_digest` | 完整跨七表canonicalization后生成；格式为DIGEST |
| Evidence | `registered_at`、`activated_at nullable`、`registration_trace_uuid` | activated_at 是历史证据，不是 active SSOT |

已激活 revision 的所有定义 child rows、digest 与 provenance immutable。未激活 revision 只可在同一 registration transaction 内建立；事务结束后不得作为长期 mutable draft 使用。

#### 4.1.4 `workflow_steps`

| 列族 | 逻辑字段 | 约束 |
|---|---|---|
| Identity | `workflow_step_uuid UUIDv7 PK`、`workflow_revision_uuid FK`、`step_key` | `(revision, step_key)` 唯一 |
| Kind | `step_kind` | `start/process/control/join/terminal` |
| Capability | `process_key nullable`、`process_contract_version nullable` | `process` 时必填且 registry 中存在；其他 kind 必须空 |
| Phase | `phase_key nullable` | process/control 可填；必须命中 v1 phase registry |
| Requiredness | `requiredness` | `required/optional`；start/terminal 固定 required |
| Terminal | `terminal_kind nullable` | terminal 时为 `success/failure/cancelled/noop` |
| Ordering | `order_hint INT`、`display_name` | 只作 deterministic serialization/diagnostic，不替代 route |

每个 revision 恰好一个 start，至少一个 terminal。step row 不能保存 Process status/claim/retry 或业务算法实现。

#### 4.1.5 `workflow_routes`

| 列族 | 逻辑字段 | 约束 |
|---|---|---|
| Identity | `workflow_route_uuid UUIDv7 PK`、revision FK、`route_key` | `(revision, route_key)` 唯一 |
| Edge | `from_step_uuid/to_step_uuid` | 两端必须同 revision；禁止 self-edge |
| Semantics | `route_kind`、`outcome_selector` | kind=`normal/branch/fan_out/join/terminal`；selector=`always/succeeded/failed/cancelled/skipped` |
| Decision | `priority INT`、`guard_group_key nullable` | 同 from-step/selector priority 唯一；数字越小优先级越高 |
| Join | `join_mode`、`predecessor_requiredness` | `none/all_required/all_terminal`；非 join route 必须 none |

Compiler必须验证无环、可达性、terminal coverage、deterministic priority、fan-out expected-set provenance与join compatibility。retry、lease recovery、cancel不允许画回边。

#### 4.1.6 `workflow_bindings`

| 列族 | 逻辑字段 | 约束 |
|---|---|---|
| Identity | `workflow_binding_uuid UUIDv7 PK`、revision/step FK | step 必须同 revision |
| Target | `binding_kind`、`slot_name` | kind=`context/input/output/parameter`；`(step, kind, slot)` 唯一 |
| Type | `value_type`、`schema_ref nullable`、`required`、`multiplicity` | 必须与 capability port 完全兼容；multiplicity=`one/many` |
| Binding source | `binding_source_kind`、`binding_source_step_uuid/port nullable`、`binding_source_ref_key nullable` | kind=`execution_context/intake_snapshot/prior_output/control_value/registry_ref/literal` |
| Typed literal | `value_bool/value_int/value_real/value_text/value_uuid/value_ref` | literal 时恰好一个与 value_type 匹配；非 literal 全空 |

禁止存储绝对路径、token/secret、IntakeArtifact/derived asset正文、任意JSON。prior output必须引用同revision的predecessor output port。

#### 4.1.7 `workflow_controls`

| 列族 | 逻辑字段 | 约束 |
|---|---|---|
| Identity/scope | `workflow_control_uuid UUIDv7 PK`、revision FK、`scope_type`、可选 step/route FK | scope=`revision/step/route`，必须且只能命中一个合法层级 |
| Time | `timeout_ms`、`lease_duration_ms`、`heartbeat_interval_ms` | 正整数；heartbeat < lease；timeout 与 lease 不混为一值 |
| Retry | `max_retries`、`retry_policy`、`backoff_kind`、`backoff_initial_ms/max_ms`、`backoff_multiplier`、`jitter_pct` | retry policy=`none/transient_only/contract_allowlist`；范围 DB CHECK |
| Recovery | `max_recoveries nullable`、`indeterminate_side_effect_policy` | nullable 仅表示本 scope 继承上层/default；解析后的 Process 必须获得非空上限；policy=`fail/verify_then_retry`；不消耗 retry_count |
| Cancel | `cancel_mode`、`cancel_grace_ms` | mode=`cooperative/fence_only/compensate` |
| Business control | `case_mode`、`purge_mode`、`failure_policy` | 固定 allowlist；不得自由 JSON |
| Concurrency | `concurrency_limit`、`fan_out_limit` | 正整数；runtime 取最严格有效值 |
| Deadline | `deadline_mode` | v1 固定 `latest_claim_time`；不得隐式当作 knowledge delete |

Controls resolution precedence：`Engine safe default < revision < step < selected route < Task runtime priority/deadline`。Task runtime 只能缩紧 deadline/priority，不得改变 proof、retry identity、route 或业务参数。

#### 4.1.8 `workflow_guards`

| 列族 | 逻辑字段 | 约束 |
|---|---|---|
| Identity/scope | `workflow_guard_uuid UUIDv7 PK`、revision FK、`scope_type`、`scope_key` | scope=`route/terminal/proof`；引用必须同 revision |
| Group | `guard_group_key`、`group_mode`、`order_index` | mode=`all/any`；同 group 内 order 唯一；禁止嵌套 group |
| Predicate | `predicate_type`、`operand_kind`、`operand_ref`、`operator` | 全部命中 allowlist，可静态解析/类型检查 |
| Expected | `expected_type` + typed expected columns | 恰好一个 typed value；不得表达脚本 |
| Failure | `failure_code`、`failure_disposition` | disposition=`route_false/process_failed/execution_failed` |

v1 operator allowlist 至少包含：`eq/ne/lt/lte/gt/gte/exists/not_exists/in_registered_set/digest_eq/schema_valid/proof_valid`。`in_registered_set` 的集合必须来自 versioned registry ref，不允许行内 JSON array。

### 4.2 `S03-E02` — 建立 Code-Owned Process Capability Registry

七表只保存Workflow program；`ProcessCapabilityManifest`在v1由MKB code registry持有，不新增第八张Workflow truth table。

`ProcessCapabilityManifest v1` 必须包含：

| 字段 | 语义 |
|---|---|
| `process_key` | 稳定 RAG-specific key |
| `contract_version` | 单调/语义版本；与 schema digest 一起解析 |
| `handler_key` | 本地 handler adapter key；不是 queue/host/path |
| `allowed_phase_keys` | step 可声明的 phase allowlist |
| `input_ports/output_ports` | name、value type、schema ref/digest、required、multiplicity |
| `parameter_specs` | typed scalar/ref、范围、required/default；无 opaque JSON |
| `outcome_schema_ref/digest` | ProcessOutcome 中业务 output 的严格 schema |
| `proof_kind/schema_ref` | completion guard 所需 proof 类型 |
| `side_effect_class` | `pure/idempotent_by_key/transactional_sink/non_replayable` |
| `idempotency_key_recipe` | 至少含 process_uuid + fencing generation 或业务 publication key |
| `retry_error_policy` | process-specific error code → retryable/non-retryable allowlist |
| `resource_access` | 允许读写的logical Intake/derived asset kind |

首版 capability coverage。S05-v1.1已经冻结的key是实际`process_key`；`resolve/fetch/universal_extract/api_scatter`只保留为历史coarse family说明，不注册兼容alias：

| Exact process key / downstream placeholder | 业务边界 | 典型成功 guard |
|---|---|---|
| `intake.acquire.inline` | 获取inline staged representation | AcquisitionEvidence、digest/media/size/budget有效 |
| `intake.acquire.local_object` | 获取本地logical object | stream/digest/media/encoding/budget有效 |
| `intake.acquire.http_static` / `intake.acquire.http_browser` | 获取HTTP raw/rendered representation | redirect/status/budget/profile/lineage完整 |
| `intake.acquire.registered_api` | 获取registered API single/collection pages | envelope/page/cursor/scope evidence完整 |
| `intake.decode.text_json_html` / `intake.decode.pdf` | 确定性解码与canonicalization | exact schema/canonicalizer/digest/loss evidence通过 |
| `clean.extract.deterministic` / `clean.ocr.local` / `clean.extract.vision` | 产生clean candidate | typed CleanArtifactCandidate、anchor/quality/producer evidence完整 |
| `clean.map.registered_api` | provider member→ExternalKey/semantic/clean candidate | schema、ExternalKey、semantic tuples、rejection evidence完整 |
| `intake.collection.seal` | single/scatter CandidateSet完整性封口 | stable order、page/root digest、counts、scope/completeness/exhaustion proof通过 |
| `intake.preflight_validate` | 以exact PreflightValidator只读校验frozen acquisition/collection/clean evidence | `passed|blocked` Outcome、ordered check evidence与binding digest完整；runtime错误不伪装blocked |
| `intake.accept_snapshot` | 调用S04 acceptance提交Snapshot/Membership/ChangeSet | accepted Snapshot/required set durable，可重放；truth仍归S04 |
| `lsrag.structurize` | 结构化/逻辑分块 | exact S06 schema、coverage/coordinates 合法 |
| `lsrag.construct` | 整包 original/summary 双通道构造（S07；**promptC**） | 整包 dual-channel full-valid + generation refs/proof；mode=`full_construct`\|`metadata_refresh`；合法后才可 enqueue vectorize（D05 T-O-206） |
| `lsrag.vectorize_index`（coarse downstream placeholder） | 覆盖embedding与index写入需求 | **仅**消费 construct 合法原料；失败 retry 归 S03 max-retries（D05 T-O-207）；embedding成功不能代替index publication |
| `index.validate_publication` | 独立验证发布集合 | expected/actual、filter、检索 proof 一致 |
| `intake.update_metadata` | 更新Intake semantic metadata/filter | versioned semantic/proof完整，必要时追加IntakeRevision |
| `intake.physical_purge` | 受控清理eligible派生数据 | retention/hold/substrate cleanup proofs完成 |
| `index.rebuild` | 重建受控 index scope | 新 index generation proof + cutover evidence |

S04-S09可新增/升级ProcessCapabilityManifest，但必须保持RAG-specific、versioned、typed、proof-gated；增加process key不需要改Task request intent，改变状态/身份语义则必须reopen S03/S04。

### 4.3 `S03-E03` — 实施 Internal Registration 与 Deterministic Compiler

Registration pipeline：

```text
load internal definition rows
  → strict field/schema validation
  → same-revision FK/reference validation
  → capability/port/parameter validation
  → graph acyclic/reachability/terminal validation
  → control range/inheritance validation
  → guard type/operator/reference validation
  → security scan（secret/path/free expression）
  → canonical sort/serialization
  → canonical_definition_digest + compiled_digest
  → write immutable revision rows
  → guarded active_revision pointer switch
  → commit
```

必须满足：

- registration fingerprint 相同的重放返回同一 revision，不新增重复 revision；
- 相同 `(workflow, revision_number)` 不同 fingerprint 返回 conflict；
- 任一 child row/校验/digest/pointer switch 失败时全部回滚；
- canonical sort key 固定：table kind → stable key/UUID-independent semantic key → order/priority；
- canonical JSON 采用 UTF-8、稳定 object key order、无 insignificant whitespace、数值规范化、UTC timestamp 规范化；
- digest 使用 SHA-256，覆盖全部运行语义，不覆盖 display-only description；
- compiler 版本和 capability registry digest 必须进入 compiled metadata；
- compiled digest mismatch 时 fail loud，不允许“按当前表继续跑”。

### 4.4 `S03-E04` — 冻结 Compiled Workflow JSON 与只读 API

Canonical compiled representation：

```json
{
  "schema_version": "mkb.workflow-compiled.v1",
  "workflow": {
    "workflow_key": "intake.ingest.single.v1",
    "workflow_uuid": "<uuidv7>",
    "workflow_revision_uuid": "<uuidv7>",
    "revision_number": 1,
    "compiled_digest": "sha256:<hex>",
    "compiler_version": "<version>",
    "capability_registry_digest": "sha256:<hex>"
  },
  "steps": [],
  "routes": [],
  "bindings": [],
  "controls": [],
  "guards": []
}
```

Compiled JSON：

- 包含运行所需的 semantic keys、typed bindings、controls、guards 与 contract refs；
- 不包含Task/Execution/Process UUID、actual authority、claim/lease、retry count、secret、绝对路径或Intake/derived asset正文；
- 由 Engine 解释，不整包交给 leaf Process；
- 可缓存，但 cache key 必须含 revision UUID + compiled digest；
- 可从七表完全重建，cache 删除不改变 truth。

只读 surface：

| Method | Route | 语义 |
|---|---|---|
| `GET` | `/v1/workflows` | bounded list；按 status/purpose/role/read exposure filter；stable cursor |
| `GET` | `/v1/workflows/{workflow_key}` | registry summary + active revision compiled detail |
| `GET` | `/v1/workflows/{workflow_key}/revisions/{revision_number}` | 仅内部诊断可读的历史 compiled detail |

所有 POST/PUT/PATCH/DELETE Workflow route 在 v1 必须不存在或返回稳定 method-not-allowed；Task create payload 不能携带 workflow key/revision/graph override。

### 4.5 `S03-E05` — 建立 Workflow Resolver 与 Immutable Execution Binding

Resolver 输入仅来自已提交事实：

- Task `request_intent`、priority、deadline 与 current generation；
- canonical Intake target/resource role；
- S04提供的immutable IntakeSource/Snapshot/ChangeSet decision ref，以及S05 source/acquisition/clean/preflight exact binding；
- internally registered resolver allowlist；
- registry status + active revision pointer。

Resolver 输出：`workflow_uuid + workflow_revision_uuid + compiled_digest + resolver_decision_digest`。Caller 不得提供这些值。

选择规则：

1. registry 必须 enabled，purpose/role 与 intent/target 匹配；
2. selector priority 确定性排序，tie 是 configuration error；
3. binding 与 Execution 创建/scheduling intent 同一事务或 S12 证明等价；
4. automatic Process retry/lease recovery/human resume沿用同一Workflow binding与S05 binding；
5. full Task retry 新 generation 复制来源 root exact binding；
6. 新atomic`intake.rebuild` Task、新ingest/update/delete/index Task按接受时active resolver选择；
7. disabled/deprecated 只阻止未来新独立 binding，不中断已绑定 Execution；
8. revision/digest 不可读或不一致时 Execution 不进入 ready。

### 4.6 `S03-E06` — 冻结 `executions` 与 `processes` 逻辑 Schema

#### 4.6.1 `executions` 最小列族

> **Downstream implementation hold**：D02-v1.0已冻结immutable subject与accepted output必须分账，但不替S03/S04/S12设计物理字段。`target_kind/target_ref`当前只能理解为逻辑列族，不得直接冻结为一个同时承担ingress subject与acceptance后Item/Revision output的封闭enum；single ingest在acceptance前可能尚无Item/Revision。该下游schema hold不改变一个root Execution贯穿single链路的冻结事实，也不构成D02未完成。

| 列族 | 逻辑字段 |
|---|---|
| Identity | `execution_uuid UUIDv7 PK`、`team_uuid/task_uuid`、`trace_uuid`、`generation` |
| Tree/lineage | `root_execution_uuid`、`parent_execution_uuid nullable`、`retry_of_execution_uuid nullable`、`execution_role` |
| Target | `target_kind`、`target_uuid/ref`、`intake_snapshot_ref/digest` |
| Workflow/domain binding | `workflow_uuid`、`workflow_revision_uuid`、`compiled_digest`、`resolver_decision_digest`；`domain_binding_ref/digest`，S05 Execution必须含exact`s05_binding_digest` |
| Control | `status`、`revision CAS`、`phase_key`、`waiting_reason/ref`、`next_wake_at` |
| Process focus | `current_process_uuid nullable FK`；可指向同 Execution 当前 focus 或尚未清理的 last Process；终态 summary 保存 final process key/identity scalar，不要求永久 FK |
| Scatter | `manifest_ref/revision/digest nullable`、expected/required/skipped counts |
| Aggregates | active/succeeded/failed/cancelled process counts、child counts、retry/recovery totals |
| Cancel | `cancel_requested_at`、`cancel_command_revision`、`cancel_converged_at` |
| Result/error | `result_ref/digest`、`publication_proof_ref/digest`、`final_error_class/code/message/details_ref` |
| Summary | `terminal_summary_digest`、`summary_completed_at`、`phase_history_ref` |
| Time | `created_at/ready_at/started_at/completed_at/updated_at` |

关键约束：

- 每个 Task generation 恰好一个 root；任一时刻最多一个 current active root；
- child 的 task/generation/root/parent 必须一致；
- `(root_execution_uuid, manifest_revision, target_uuid)` 对 required child 唯一；
- terminal Execution 的 status、Workflow binding、target、result/error 与 proof 等业务事实不可反转或覆写；允许以 CAS 单调补齐 terminal summary、清理 pointer 与追加 cleanup evidence；
- status=waiting 时 waiting_reason/ref 必须完整；非 waiting 时清空；
- status=succeeded 时 publication proof/summary 必须满足 intent-specific guard；
- `current_process_uuid` 只引用同 Execution 的 focus/last Process；它可暂时指向尚未清理的 terminal Process，并发集合不由它决定，Process cleanup 前必须先清空。

#### 4.6.2 `processes` 最小列族

| 列族 | 逻辑字段 |
|---|---|
| Identity | `process_uuid UUIDv7 PK`、`execution_uuid FK`、`workflow_step_uuid/key`、`process_key/contract_version` |
| Materialization | `materialization_key DIGEST`、`route_decision_digest`、`fan_out_item_key nullable`、`requiredness` |
| Immutable spec | `process_spec_digest`、`input_manifest_ref/digest`、`control_snapshot_ref/digest`、`proof_kind` |
| State/CAS | `status`、`revision`、`available_at`、`priority_rank`、`deadline_at` |
| Claim | `claim_token_hash nullable`、`lease_owner nullable`、`lease_expires_at nullable`、`fencing_generation`、`heartbeat_at` |
| Counters | `delivery_count`、`recovery_count`、`retry_count`、`max_retries`、`max_recoveries`；两个 max 均为 materialization 时解析并固化的非空 effective 值 |
| Retry | `next_retry_at nullable`、`last_failure_retryability`、`backoff_policy_snapshot` |
| Outcome | `accepted_outcome_digest nullable`、`output_manifest_ref/digest`、`proof_ref/digest` |
| Error | `error_class/code/message/details_ref`、`failure_disposition` |
| Cleanup | `cleanup_eligible_at nullable`、`cleanup_fence_digest nullable` |
| Time | `created_at/claimed_at/started_at/completed_at/updated_at` |

关键约束：

- `(execution_uuid, workflow_step_uuid, materialization_key)` 唯一，防止 route/recovery 重复物化；
- claim fields 只在 claimed/running/cancelling 合法；terminal/retry_wait/ready 不持有有效 lease；
- `retry_count <= max_retries`、`recovery_count <= max_recoveries`；三个 counters 不互相代替；
- succeeded 必须有 accepted outcome/output/proof（按 capability 要求）；
- failed 必须有结构化 error；cancelled 必须有 cancel convergence evidence；
- terminal Process 的 status、accepted Outcome、output/proof 与 failure facts 不再回 ready或被覆写；允许追加 cleanup eligibility/fence evidence；automatic retry 必须在进入 failed 前经 retry_wait 实现；
- cleanup_eligible_at 只能由统一 cleanup eligibility evaluator 写入。

`events/outbox/asset records/vector records`是各自职责表，不是新的Workflow/Execution/Process identity，也不改变D01三张runtime state tables；S04 canonical/supporting tables同样不是runtime identity。

### 4.7 `S03-E07` — 冻结 ProcessCommand / ProcessOutcome Contract

#### 4.7.1 ProcessCommand

`mkb.process-command.v1` 必须包含：

- identity/correlation：team、task、trace、root/execution/process UUID；
- workflow：workflow/revision/digest、step key、process key/contract version、phase；
- resource：target IntakeSource/Snapshot/Item/Revision/ChangeSet logical refs + digests；
- authority：MKB runtime authority snapshot，不含平台 role/billing；
- I/O：按 capability ports 渲染的 typed input handles；
- parameters：严格 typed scalar/ref；
- control：timeout、retry policy、deadline、case/purge/cancel instruction；
- claim：delivery UUID（非执行身份）、claim token、fencing generation、lease expiry；
- integrity：process spec digest、command envelope digest、issued_at。

ProcessCommand 是从 durable Process spec + current lease 派生的 transport envelope。它可以 JSON 序列化，但 JSON 不是 truth；runner 必须在执行前验证 schema、spec digest、claim/fence 和 deadline。

#### 4.7.2 ProcessOutcome

`mkb.process-outcome.v1` 必须包含：

- 相同 identity/workflow/process contract correlation；
- claim token + fencing generation；
- `outcome_status=succeeded/failed/cancelled`；
- typed output handles、schema/hash/digest；
- completion proof ref/digest；
- failure 时的 `retryability=retryable/non_retryable/indeterminate` 与 structured error；
- started/completed time、bounded metrics summary；
- outcome digest/idempotency key。

Outcome 禁止携带 next step、Task status、Execution terminal、物理路径或任意 route override。Engine 接受 Outcome 的线性化事务必须完成：

1. identity/revision/spec/outcome digest 验证；
2. current fence CAS；
3. capability output/proof guard；
4. Process transition；
5. route decision/Execution aggregate 更新；
6. 必要的下一 Process/child scheduling intent；
7. transition event/outbox；
8. commit 后 wake-up。

### 4.8 `S03-E08` — 实施 Process Exact State Machine

```text
materialize
  → ready
      ├── cancel → cancelling → cancelled
      └── claim CAS → claimed
                       ├── lease expires before run → fenced recovery → ready | failed
                       ├── cancel → cancelling → cancelled
                       └── running
                            ├── valid success Outcome → succeeded
                            ├── retryable failure + budget → retry_wait
                            │                                 └── due → ready
                            ├── non-retryable / exhausted / invalid proof → failed
                            ├── lease expiry → fenced verify → ready | failed
                            └── cancel → cancelling → cancelled
```

Transition matrix：

| From | To | 必要 guard/副作用 |
|---|---|---|
| — | ready | step eligible；materialization unique；spec/intent committed |
| ready | claimed | status/revision/available/deadline CAS；new token/fence/lease |
| claimed | running | current fence；runner started evidence |
| claimed/running | ready | expired lease；fence++；contract safe replay；`recovery_count < max_recoveries`；recovery_count++ |
| claimed/running | failed | expired lease且 side effect indeterminate/non-replayable，或 `recovery_count >= max_recoveries`；分别记录 `indeterminate-side-effect` / `recovery-exhausted` |
| running | retry_wait | current fence；retryable failure；retry_count < max；retry_count++；next_retry_at |
| retry_wait | ready | durable due predicate；无 cancel；lease empty |
| running | succeeded | current fence + accepted Outcome + output/proof guard |
| running | failed | non-retryable、contract/proof invalid、retry exhausted |
| ready/claimed/running/retry_wait | cancelling | accepted cancel intent；禁止新 claim/outcome commit |
| cancelling | cancelled | no active side effect/lease；stop/compensation evidence complete |

禁止边：terminal→任何非 terminal、ready→succeeded、queue ACK→succeeded、stale fence→任意 mutation、retry_wait→running（必须重新 claim）。

### 4.9 `S03-E09` — 实施 Execution Exact State 与 RAG Phase

```text
created → ready → running ↔ waiting
   │         │        │         │
   ├─────────┴────────┴─────────┼──→ failed
   └─────────┬────────┬─────────┴──→ cancelling → cancelled
             │        └────────────→ succeeded
             └─ initial work must become durable before progression
```

合法语义：

| Status | 进入条件 | 离开条件 |
|---|---|---|
| created | identity/tree/workflow binding 建立中 | binding、initial route、首个 intent 完整→ready；integrity fail→failed |
| ready | 至少一个初始 Process ready 或已提交 root child scheduling intent | first claim→running；typed wait→waiting；cancel→cancelling |
| running | 有 current/active work 或正在推进 route | 无立即工作但有 durable wait→waiting；全部 guards满足→terminal |
| waiting | typed reason + trigger/ref 存在 | trigger满足/claim→running；fan-in归约→terminal；cancel→cancelling |
| cancelling | control 已传播，仍有 descendant/Process 待停止 | 全部安全收敛→cancelled |
| succeeded | required work/proof全部满足 | immutable |
| failed | required non-retryable/retry-exhausted/integrity failure | immutable；full retry由 S02 新 generation |
| cancelled | descendants terminal/fenced | immutable；full retry由 S02 |

v1 canonical phase registry：

```text
resolving_source
cleaning
scattering
preflight_admission
awaiting_human_review
structurizing
constructing
vectorizing_indexing
validating_publication
fan_in
updating_metadata
deactivating
deleting
purging
rebuilding_index
```

Phase 由 active Process set/route priority 归约；同一 Execution 并行多 phase 时，保存 deterministic focus phase，同时 phase history/active set 由 summary/evidence 表达。terminal 后保留 last phase，不新增 completed phase。

Waiting reason registry：`retry_due/process_join/scatter_children/durable_prerequisite/human_review`。每个reason必须携带对应`wait_ref`；`human_review`的ref必须是current-fenced open ExecutionGate，retry_due还必须有`next_wake_at`。无reason/ref、terminal/stale gate或Process仍持lease等待human均为invariant violation。

`vectorizing_indexing`只冻结为当前Execution focus phase，不证明embedding生成、index generation写入与publication validation必须由一个Process完成。S08/S09冻结exact capability前，禁止从该phase反推`lsrag.vectorize_index`的事务或retry边界。

### 4.10 `S03-E10` — 实施 Typed Route/Guard Engine

每次route evaluation必须输入：bound WorkflowRevision/digest、current step/outcome、IntakeSnapshot/ChangeSet immutable decisions、Execution control、registered guard values。输出必须是：

- selected route key(s)；
- guard group逐项结果；
- decision input digest；
- expected fan-out/join set ref；
- next eligible step(s) 或 terminal；
- route decision digest/evidence。

规则：

1. outcome selector 先过滤，再按 priority 评估 guard；
2. branch 默认只选第一个满足的 deterministic route；fan_out 可选择多个显式 fan-out routes；
3. required route 没有匹配且无 failure terminal 是 configuration/integrity error；
4. guard 只读 immutable refs，不调用非确定外部服务；业务 decision 必须先由 S04-S09 持久化；
5. skipped/unselected step 不建 Process；route evidence 记录原因；
6. join readiness 以 committed expected set + terminal Process/child facts判定，不以 queue emptiness判定；
7. route evaluation 与 next materialization/scheduling intent 必须同一事务或严格可对账。

### 4.11 `S03-E11` — 实施 Single Intake Workflow

```text
Task(intake.ingest/rebuild)
  → root Execution（ingest初始subject为Source/input；rebuild为exact Item/Revision）
      → exact intake.acquire.*
      → exact intake.decode.* / clean.*（按IntakeSource capability可受控skip）
      → intake.collection.seal
      → intake.preflight_validate
      → intake.accept_snapshot（ingest路径）
           bind exact accepted Item/Revision output for downstream Processes
      → admission route
           passed+allowlisted → continue（无gate）
           review needed → waiting(human_review, exact accepted target/gate ref)
                            → fenced decision → same Execution resumes
      → lsrag.structurize
      → lsrag.construct
      → lsrag.vectorize_index
      → index.validate_publication
      → Execution succeeded + proof summary
      → Task succeeded
```

约束：

- 同一 Execution 贯穿 clean→RAG，不生成 clean_job/rag_job；
- skip clean 必须由 registered resource capability guard 决定并留下 evidence；
- preflight runtime/schema/evidence错误走Process retry/failed；只有typed business Outcome可参与route；
- human waiting前preflight/clean Process必须terminal；release不得热切Workflow/S05 binding；
- previous output 只通过 typed binding/ref 传递；Process 不读取完整上游 row；
- publication validation 是独立 required guard/Process，不以 vectorizer 返回成功替代；
- optional Process 失败按 workflow failure policy 归约，required Process 失败按 retry/non-retryable 规则终结；
- result/proof 上卷 Execution 后，S02 才可归约 Task succeeded。

### 4.12 `S03-E12` — 实施 API Scatter Workflow

```text
Task(intake.ingest, API IntakeSource)
  → root controller Execution
      → intake.acquire.registered_api
      → clean.map.registered_api
      → intake.collection.seal
      → intake.preflight_validate（root frozen evidence）
      → intake.accept_snapshot
           commit IntakeSnapshot / Membership / ChangeSet required set
      → optional root waiting(human_review, gate ref)；release前不创建RAG children
      → idempotently create N child Executions
           child_i → clean/preflight → optional own gate → RAG Processes
      → root waiting(reason=scatter_children, ref=IntakeSnapshot/ChangeSet)
      → collect-all fan_in
      → root succeeded | failed | cancelled
      → Task aggregate
```

Snapshot/ChangeSet fan-out fence：

1. S05生成validated/sealed CandidateSet；S04原子提交IntakeSnapshot、Membership、Item/Revision decisions、ChangeSet与child intents；
2. root保存IntakeSnapshot/ChangeSet ref/digest与expected counts；
3. child uniqueness使用`(root_execution_uuid, change_set_digest, intake_item_uuid, intake_revision_uuid)`；
4. commit后wake可批次执行，但recovery必须从ChangeSet required set补齐，不能按已创建child数猜分母；
5. zero-member/zero-required Snapshot是合法业务结果：root仍需typed terminal/proof，不能假成功；
6. child 各自拥有独立 Process claim/retry/proof；healthy siblings 不 fail-fast；
7. all required terminal 后：任一 failed→root failed；全部 succeeded/skipped policy满足→root succeeded；cancel path按 descendants 收敛→cancelled；
8. proof-valid child可在root运行时按S04 serving fence被S10读取；root failure/cancel不回滚；
9. root summary保存Snapshot/ChangeSet、counts、failed child summary refs与成功proofs；TaskItems由Membership/ChangeSet + child summaries投影。

### 4.13 `S03-E13` — 实施 Retry、Priority、Deadline 与 Cancel Control

#### Retry/backoff

| 场景 | Identity | Counter | Workflow binding |
|---|---|---|---|
| queue redelivery | 全不变 | delivery_count++ | 不变 |
| lease recovery | 全不变 | recovery_count++ | 不变 |
| automatic business retry | process/execution/task不变 | retry_count++ | 不变 |
| full Task retry | Task不变，新 root/children/Processes | 新 generation | 复制来源 root exact revision/digest |
| atomic IntakeItem rebuild | 新Task/root/Processes；IntakeRevision不变 | 新因果链 | 解析当前active WorkflowRevision |

Backoff formula：

- fixed：`initial_ms`；
- linear：`min(max_ms, initial_ms * retry_count)`；
- exponential：`min(max_ms, initial_ms * multiplier^(retry_count-1))`；
- jitter 在 `[0, jitter_pct]` 内以 `process_uuid + retry_count` deterministic seed 产生，确保 recovery 重算一致；
- exact numeric values 来自 resolved workflow_controls，禁止 handler 自行 sleep/retry。

#### Priority

Task priority 单调映射：`urgent=400/high=300/normal=200/low=100`。claim 排序：

```text
priority_rank DESC
→ available_at ASC
→ non-null deadline_at ASC
→ created_at ASC
→ process_uuid ASC
```

priority 只影响调度顺序，不绕过 dependency/claim/concurrency/tenant isolation，也不改变成功语义。

#### Deadline/timeout

- `deadline_at` 的 v1 语义是 latest claim time；ready Process 在 deadline 后不得新 claim，转 failed `deadline-exceeded-before-start`；
- 已 running Process 不因 Task deadline 被非安全强杀；由 process timeout + cancel/compensation policy控制；
- process timeout 是一次业务运行的时间上限，timeout Outcome按 capability retry policy分类；
- deadline/timeout 均不允许隐式 purge 或把 proof-valid child 回滚。

#### Cancel

```text
S02 accepts cancel by Task CAS
  → root cancelling
  → no new route/materialization/claim
  → propagate child Executions
  → Process cancelling + current fence invalidation/stop
  → wait descendants terminal
  → root cancelled
  → S02 Task cancelled
```

如果 Process/Execution success 在 cancel CAS 前已合法提交，则 first-commit-wins；失败竞争者不得反转。已发布知识保留，撤销必须由独立 deactivate/delete Task 表达。

### 4.14 `S03-E14` — 实施 Workflow Semantic Recovery

Progress invariant：每个 nonterminal Execution 必须至少满足一项：

```text
exists ready/due Process
OR exists current-fenced claimed/running Process
OR exists typed waiting reason + durable trigger/ref
OR status=cancelling and exists nonterminal descendants
```

Repair matrix：

| 检测事实 | S03 semantic decision | S12 action | 禁止行为 |
|---|---|---|---|
| Process ready/due，无有效 wake/outbox | state 仍是可执行 truth | 幂等补建/重发 wake | 新建 Process或增加 retry_count |
| retry_wait 已到期 | 合法 `retry_wait→ready` | CAS + outbox | 直接 running |
| lease 过期 | fence旧 runner；按 side-effect class 与 effective max_recoveries 决定 ready/failed | 未耗尽时 CAS、recovery_count++、必要 wake；耗尽时 `recovery-exhausted` | 接受旧 Outcome或绕过止血上限 |
| terminal Process 后无 route advance | 以 bound revision/outcome 重算 deterministic decision | 同 transition service补 next intent | 热切 revision/猜 route |
| PreflightOutcome已提交、admission transition缺失 | 以Workflow+S05 exact binding和Outcome重算route | 幂等补自动route或human gate intent | 重跑validator、热切binding或伪造released gate |
| open ExecutionGate存在、Execution未waiting | gate是durable trigger truth | CAS补`waiting(reason=human_review, ref=gate)`与outbox | 创建duplicate gate或让Process继续持lease |
| gate decision/terminal CAS已提交、outbox缺失 | decision是已提交因果 | 幂等重放resume/terminal outbox | 重写decision或创建新Execution |
| late/stale gate decision | revision/fence/target不匹配 | 拒绝并记录typed conflict/audit | last-write-wins或恢复旧target |
| Snapshot/ChangeSet committed、child缺失 | 对required set做uniqueness diff | 幂等补齐child/intent | 以现有child count改分母 |
| Process join/children 已满足 | 合法推进 waiting→running/terminal | CAS + summary/event | 永久 waiting |
| cancelling descendants 未收敛 | 继续 fence/stop/compensation | 扫描 active descendants | 直接写 cancelled |
| terminal summary/pointer未收口 | 从 terminal facts重建 summary，清 current pointer | CAS + evidence | 清理 Process前跳过 summary |
| revision/digest/proof冲突 | integrity failure/quarantine disposition | failed + alert/event | 自动换 revision/伪造 proof |

所有 repair 必须：

- 调用与正常路径同一个 transition service；
- 使用 expected revision/fencing/uniqueness CAS；
- 产生 deterministic decision digest；
- 重复执行 no-op；
- 不新增外部 operator 写 API；
- 不把日志/queue/cache当 truth。

### 4.15 `S03-E15` — 实施 Terminal Summary 与 Process Cleanup Eligibility

Execution terminal summary 至少保存：

- workflow key/UUID/revision/digest、capability registry digest；
- route decision summary/digest、required/optional/skipped counts；
- Process/child expected、succeeded、failed、cancelled counts；
- retry/recovery/delivery totals、exhausted process keys；
- phase history ref、final phase/process key；
- final error class/code/message/details ref；
- input/output Intake/derived asset refs/digests；
- Vector/filter publication proof ref/digest；
- IntakeSnapshot/ChangeSet ref/digest（scatter）；
- started/completed/latency summary。

Cleanup predicate：

```text
execution.status IN terminal
AND execution.summary_completed_at IS NOT NULL
AND terminal_summary_digest/proof requirements valid
AND no process in ready/claimed/running/retry_wait/cancelling
AND no unexpired lease
AND no pending retry/recovery/cancel/compensation
AND no pending outbox/scheduling intent for execution
AND execution.current_process_uuid IS NULL
AND retention/recovery window elapsed
```

资格满足后，S03可标记`cleanup_eligible_at/fence_digest`；S12再按retention执行archive/delete。禁止级联删除Execution、Task、Audit、restart、Intake truth、derived assets、Vector或S15 Event/Log。WorkflowRevision删除资格另受历史引用围栏，不与Process cleanup合并。

### 4.16 `S03-E16` — 建立内部模块与依赖方向

建议模块边界：

```text
workflow/domain
  registry models + enums + graph rules

workflow/application
  register_workflow
  compile_workflow
  resolve_workflow
  create_execution
  evaluate_route
  materialize_process
  transition_process
  aggregate_execution
  propagate_cancel
  repair_invariants
  evaluate_cleanup_eligibility

workflow/runtime
  capability registry
  command renderer
  outcome validator
  scheduler ports

workflow/adapters
  turso repositories/outbox (S12)
  local queue runner (S12)
  Intake/derived-asset/model/vector ports (S04-S14)
  event sink (S15)
  readonly API
```

依赖规则：domain不导入HTTP/queue/Turso/storage backend；leaf handlers不导入route engine/Task repository；S02不导入Process handler；S12 adapter实现S03 ports，但不能定义业务状态边。

内部诊断 read service 可提供 `getExecution/listExecutionsByTask/getProcess/listProcessesByExecution/explainRouteDecision`，但必须经 S16 权限控制、只读、team-scoped；普通外部 Task API 不暴露这些 UUID 作为命令边界。

---

## 5. 事实反例 + 风险台账

### 5.1 Legacy 事实吸收台账

| Evidence | 已验证事实 | MKB verdict |
|---|---|---|
| SMCP schemas | identity/authority/workflow/I/O/control/outcome/error/correlation 多平面强契约 | 保留语义平面；集中为本地 ProcessCommand/Outcome；删除多份网络 DTO |
| Workflow editor/converter | 声明式 graph、I/O mapping、registry preset、agent draft tool | 保留可编程 schema；v1 内部注册；agent authoring deferred |
| Clean Dispatcher | pending row先于正常 queue、callback后推进、Clean→RAG、scatter relation+并发 | 保留 durable-before-wake/outcome progression；统一 Execution/Process |
| RAG Dispatcher | case mode跳步、atomic child hydration、Process tracking、child passive terminal | 保留typed route/child独立结果；增加S04 Snapshot/ChangeSet root collect-all |
| Restarters | same-step retry、max-retries、stuck-pending补偿函数 | 保留 same Process retry/max；补偿函数未接通，不宣称已有通用 reconciler |
| DO/queue error paths | DB-first与queue-first双写窗口、异步失败难回写 | 用 outbox + semantic recovery + fencing 全局升级 |
| Process history | 供 history/restart 查询，未发现 cleanup实现 | 先上卷 Execution summary，再按资格清理；不复制“compaction”伪事实 |

### 5.2 事实反例

| Counterexample ID | 错误做法 | S03 订正 |
|---|---|---|
| `S03-C01` | Workflow 只有 node/edge JSON | 六平面 relational truth；compiled JSON 仅派生。 |
| `S03-C02` | 外部/agent 可直接 CRUD Workflow | v1 内部注册；外部只读。 |
| `S03-C03` | active revision 原地修改 | 新 revision + guarded pointer switch；Execution binding immutable。 |
| `S03-C04` | Process 收到完整 Workflow 后自行找下一步 | Engine interpret；Process 只消费本工序 Command。 |
| `S03-C05` | 为所有未来/skip step 预建 pending Process | 只 materialize eligible step；route evidence 表达 skip。 |
| `S03-C06` | queue message/ACK 是 Process truth | committed Process/spec/intent 是 truth；queue 只是 wake。 |
| `S03-C07` | redelivery/lease expiry 都增加 retry_count | delivery/recovery/retry 三账分离。 |
| `S03-C08` | late Outcome 覆盖新 runner 结果 | claim token + fencing generation stale reject。 |
| `S03-C09` | automatic retry 新建 Process/Attempt/Execution | 同 process_uuid retry_wait；full retry 才新 Execution。 |
| `S03-C10` | Execution status 使用 clean/vectorizing/retrying | control status 与 RAG phase 分列；retry在 Process。 |
| `S03-C11` | current_process_uuid 是并发 active set | 仅 focus/last pointer；Process rows/summary 为真。 |
| `S03-C12` | scatter child是Workflow step或child Task | child是独立Execution，required set来自accepted Snapshot/ChangeSet。 |
| `S03-C13` | 一个 child 失败立即停止 siblings/root failed | collect-all；全部 required terminal 后归约。 |
| `S03-C14` | cancel parent 就 purge已发布 child | forward-stop；deactivate/delete独立 Task。 |
| `S03-C15` | 独立 Reconciler 任意修 status | semantic recovery只调用统一 transition service。 |
| `S03-C16` | 无 generic Reconciler 就不需要恢复 | 组件名可省，progress invariant/repair behavior不可省。 |
| `S03-C17` | Process compaction=压缩/知识清理 | 仅 summary-before-projection-cleanup；Vector/IntakeArtifact不受影响。 |

### 5.3 风险台账

| Risk ID | 风险 | 严重度 | 强制围栏 |
|---|---|---:|---|
| `S03-R01` | 七表跨 revision wiring | P0 | composite FK/compiler same-revision validation |
| `S03-R02` | compiled digest不稳定 | P0 | canonical serialization golden/property tests |
| `S03-R03` | registry pointer与revision状态双真相 | P0 | active pointer only；无 revision is_active |
| `S03-R04` | capability port/contract drift | P0 | ProcessCapabilityManifest digest + registration validation + Execution binding |
| `S03-R05` | DB commit后漏 wake | P0 | outbox + ready-state recovery |
| `S03-R06` | 双 claim/late Outcome重复业务写 | P0 | CAS + lease/fence + sink idempotency key |
| `S03-R07` | retry/recovery计数混淆导致提前耗尽或无限跑 | P0 | 三 counter、exact transition tests、max-retries |
| `S03-R08` | waiting没有触发源永久卡死 | P0 | typed reason/ref CHECK + progress invariant scan |
| `S03-R09` | partial scatter fan-out遗漏/重复child | P0 | Snapshot/ChangeSet uniqueness + idempotent recovery |
| `S03-R10` | cancel/success双终局 | P0 | S02 CAS + descendant fence + transition race test |
| `S03-R11` | proof-invalid仍被标 succeeded | P0 | capability proof guard + terminal CHECK |
| `S03-R12` | Process过早清理破坏查询/lineage | P0 | hard cleanup predicate + before/after equivalence tests |
| `S03-R13` | recovery猜 route/换 revision | P0 | exact binding + deterministic decision digest + integrity fail |
| `S03-R14` | compiled/read API泄漏 path/secret/runtime UUID | P1 | field allowlist + security scan |
| `S03-R15` | generic controls继续膨胀成 JSON | P1 | fixed columns + typed capability extension + reopen gate |

### 5.4 明确禁止的实现方向

- 禁止 mutable `steps_definition/config_json` 作为 Workflow SSOT；
- 禁止第八张自由扩展 Workflow JSON truth table；
- 禁止 external/agent Workflow CUD；
- 禁止业务 loop/recursion、任意脚本/SQL guard；
- 禁止 Process 解释完整 Workflow、推进 Task 或选择物理存储；
- 禁止 Attempt、clean/rag/vector Process 分表、child Task；
- 禁止 queue/callback/log/compiled cache 充当状态或成功真相；
- 禁止无 fencing 的 lease recovery 和 late Outcome commit；
- 禁止把 recovery_count 算作 retry_count；
- 禁止 Process 直接写 Execution/Task terminal；
- 禁止 fail-fast 停健康 scatter sibling；
- 禁止 cancel 隐式 rollback/purge proof-valid knowledge；
- 禁止 recovery 直接 PATCH 任意 status/proof/revision；
- 禁止 cleanup 在 summary/outbox/lease/pointer fence 未闭合时执行；
- 禁止复制 Cloudflare Worker/DO/D1/R2/SMCP callback 部署拓扑。

---

## 6. 测试与验收台账

### 6.1 强制验收矩阵

| Acceptance ID | 场景 | 通过条件 |
|---|---|---|
| `S03-A01` | 内部注册合法 Workflow | 七表原子提交、revision immutable、pointer正确 |
| `S03-A02` | registration 任一点失败 | revision child/pointer/cache均不留 partial truth |
| `S03-A03` | 相同 fingerprint重放 | 返回同 revision，行数不增加 |
| `S03-A04` | 同 revision number不同内容 | conflict，active pointer不变 |
| `S03-A05` | 跨 revision step/route/binding/control/guard | DB/compiler reject |
| `S03-A06` | graph cycle/self-edge/unreachable required step | registration reject |
| `S03-A07` | 无 terminal/terminal coverage缺失 | registration reject |
| `S03-A08` | route priority tie/free expression/SQL guard | registration reject |
| `S03-A09` | capability key/version不存在 | registration reject |
| `S03-A10` | binding port/type/multiplicity不匹配 | registration reject |
| `S03-A11` | binding 含绝对路径/secret/opaque JSON | registration/security reject |
| `S03-A12` | 同 revision重复 compile 1,000次 | canonical bytes/digest完全相同 |
| `S03-A13` | compiled cache删除 | 从七表重建同 digest |
| `S03-A14` | registry新 revision激活 | 旧 Execution binding不变，新 Execution使用新 revision |
| `S03-A15` | full Task retry | 新 root复制来源 exact revision/digest |
| `S03-A16` | 新 atomic rebuild Task | 解析当前 active revision，不复活旧 child |
| `S03-A17` | 未命中 route | 不建 Process；decision evidence存在 |
| `S03-A18` | eligible materialization崩溃注入 | Process/spec/intent全有或全无；commit前无 wake |
| `S03-A19` | 100并发 claim同 Process | 恰好一个 claim/fence成功 |
| `S03-A20` | queue重复 delivery | 不新增 Process/业务写；delivery diagnostics可增 |
| `S03-A21` | stale token/generation Outcome | reject且truth不变 |
| `S03-A22` | accepted Outcome重放 | idempotent no-op |
| `S03-A23` | retryable failure | same process进入retry_wait，retry_count+1 |
| `S03-A24` | due retry_wait | CAS回ready，重新claim使用新 fence |
| `S03-A25` | lease expiry可安全重放（含 recovery 上限边界） | 未耗尽时 recovery_count+1、retry_count不变、旧Outcome失效；已耗尽时 failed `recovery-exhausted`且不再唤醒 |
| `S03-A26` | lease expiry side effect不确定 | failed indeterminate-side-effect，不自动重跑 |
| `S03-A27` | max-retries耗尽 | Process failed，Execution可归约而非永久waiting |
| `S03-A28` | proof/output schema无效 | Process/Execution不得 succeeded |
| `S03-A29` | single完整流程 | 同一 Execution贯穿所有RAG phases，最终proof上卷 |
| `S03-A30` | controlled clean skip | guard/evidence存在，无假Process |
| `S03-A31` | scatter ChangeSet N required children | 恰好N个本ChangeSet child，root waiting/fan_in |
| `S03-A32` | Snapshot/ChangeSet commit后partial child crash | recovery补齐，不重复已有child |
| `S03-A33` | scatter child失败且siblings active | root waiting/Task running，siblings继续 |
| `S03-A34` | required children全终态含失败 | root failed，成功child仍ready可检索 |
| `S03-A35` | children全部proof-valid | root/Task succeeded，counts与manifest一致 |
| `S03-A36` | zero-required Snapshot/ChangeSet | typed terminal policy执行，不依赖queue empty |
| `S03-A37` | cancel/success竞态1,000次 | durable first-commit-wins，无双终局 |
| `S03-A38` | cancel后late Outcome | fence拒绝；descendants收敛后cancelled |
| `S03-A39` | cancel含已发布child | child保留；未完成work停止；无implicit purge |
| `S03-A40` | Task deadline过期前未claim | Process failed deadline-exceeded-before-start |
| `S03-A41` | ready wake丢失 | recovery补wake，不新建Process |
| `S03-A42` | terminal→next崩溃 | recovery按相同decision补materialization |
| `S03-A43` | waiting无reason/ref故障注入 | invariant检测、failed/quarantine evidence |
| `S03-A44` | revision/proof冲突 | fail loud，不热切/猜测/伪造 |
| `S03-A45` | recovery重复运行100次 | 行数/Outcome/child/业务提交不增加 |
| `S03-A46` | cleanup任一 fence未闭合 | 不设置eligible、不删除 |
| `S03-A47` | cleanup全部满足 | current pointer清空、summary完整、S12可删除Process |
| `S03-A48` | Process cleanup前后查询 | Execution/Task/items/restart/lineage/proof语义等价 |
| `S03-A49` | Workflow API CUD/Task graph override | strict reject；registry/runtime不变 |
| `S03-A50` | compiled/command/outcome泄漏扫描 | 无secret、绝对路径、平台plan、非必要runtime payload |
| `S03-A51` | allowlisted+preflight passed | Outcome后直接materialize next route，无gate/decision |
| `S03-A52` | human review required | Process terminal；Execution waiting+exact gate ref，无active lease |
| `S03-A53` | gate released | append+CAS+outbox后same Execution恢复，Workflow/S05 binding不变 |
| `S03-A54` | Preflight runtime/schema/evidence错误 | same Process retry/failed，不创建human gate |
| `S03-A55` | Outcome/gate/decision crash四窗口 | repair幂等；无duplicate gate/route/decision/Execution |
| `S03-A56` | stale gate/target/fence decision | typed conflict；current Execution/gate不变 |

### 6.2 必须留存的验收证据

1. 七表 logical→physical DDL mapping、FK/unique/check/trigger report；
2. registration/compiler static validation matrix；
3. canonical JSON/digest golden fixtures 与 deterministic property report；
4. ProcessCapabilityManifest/port compatibility snapshots；
5. Process/Execution transition exhaustive/property test report；
6. claim/lease/fencing、retry/recovery/cancel 并发故障注入报告；
7. single/scatter golden Workflow fixtures、Snapshot/ChangeSet fan-in/proof report；
8. semantic recovery repair matrix fault injection与幂等报告；
9. Process cleanup前后 polling/lineage/proof等价报告；
10. API/compiled/command/outcome security leak scan；
11. legacy 对照报告：durable step、Clean→RAG、scatter、restart/stuck pending、DO/queue crash windows 如何被 MKB 继承/升级/删除。

---

## 7. Reference-anchor 台账

### 7.1 权威文档锚

| Reference | 使用方式 |
|---|---|
| `docs/baseline/domain-truth/D01-task-execution-process-flow.md` | Task/Execution/Process、single/scatter、retry层级、summary/cleanup与运行表职责 |
| `docs/baseline/domain-truth/S01-skill-worker-integration.md` | standalone边界、UUID、Task caller权限、queue非SSOT、proof成功边界 |
| `docs/baseline/domain-truth/S02-task-api.md` | Task六态、generation、scatter collect-all、early publication、cancel/full/atomic restart |
| `docs/baseline/qna-truth/S03.md v1.0` | Q1–Q9 owner回答、`T-O-12..29`、双Dispatcher reference anchors与冲突审计 |
| `docs/baseline/spec-index.md` | S03定位、依赖、gate与下游回填纪律 |

### 7.2 Legacy 代码事实锚

| Ref ID | 文件锚 | 证明的事实 |
|---|---|---|
| `S03-REF-L01` | `legacy-family/smind-rag-dispatcher/core/schemas_smcp.ts:6-29,80-280` | SMCP多平面宪法、Start/Restart/Callback强契约 |
| `S03-REF-L02` | `legacy-family/smind-clean-dispatcher/services/mapper.ts:51-249`; `legacy-family/smind-clean-dispatcher/services/io_renderer.ts:31-170` | Workflow + context编译为具体step I/O/command |
| `S03-REF-L03` | `legacy-family/smind-rag-dispatcher/services/mapper.ts:127-280`; `legacy-family/smind-rag-dispatcher/services/io_renderer.ts:31-259` | RAG control/atomic/I/O renderer与Process解耦 |
| `S03-REF-L04` | `legacy-family/smind-console/src/pages/workflow/lib/converter/index.ts:25-73`; `legacy-family/smind-console/src/pages/workflow/lib/converter/injector.ts:1-134` | 声明式graph、I/O mapping与editor compiler事实 |
| `S03-REF-L05` | `legacy-family/smind-console/src/pages/workflow/features/tools/tool-definitions.ts:8-44` | agent只修改editor draft，未形成完整publish治理 |
| `S03-REF-L06` | `legacy-family/smind-clean-dispatcher/flows/orchestrator.ts:39-209` | eligible step逐步物化、DB-first dispatch、callback progression |
| `S03-REF-L07` | `legacy-family/smind-clean-dispatcher/flows/finalizer.ts:96-304` | Clean completion、single handoff、scatter relation+parallel fan-out |
| `S03-REF-L08` | `legacy-family/smind-rag-dispatcher/flows/processor.ts:113-277` | single/atomic child hydration、relation fallback、control context |
| `S03-REF-L09` | `legacy-family/smind-rag-dispatcher/flows/orchestrator.ts:36-304` | case route、pending process、queue/DO dispatch、DO timeout缺口 |
| `S03-REF-L10` | `legacy-family/smind-rag-dispatcher/flows/finalizer.ts:61-168` | child ready/rag_failed、parent untouched、无root fan-in |
| `S03-REF-L11` | `legacy-family/smind-clean-dispatcher/services/restarter.ts:169-293,684-935` | stuck-pending补偿函数、same-step retry/max、queue-first窗口 |
| `S03-REF-L12` | `legacy-family/smind-rag-dispatcher/services/restarter.ts:65-205,620-869` | 同类补偿/restart与重复处理风险 |
| `S03-REF-L13` | `legacy-family/smind-clean-dispatcher/src/index.ts:32-160`; `legacy-family/smind-rag-dispatcher/src/index.ts:36-199` | 补偿扫描函数没有被dispatcher入口/cron接通 |
| `S03-REF-L14` | `legacy-family/smind-clean-dispatcher/core/schemas_common.ts:173-196`; `legacy-family/smind-rag-dispatcher/core/schemas_common.ts:161-186` | legacy七态声明与实际主流程状态覆盖不足 |

### 7.3 证据使用判定

- **保留原理**：声明式多平面 Workflow、typed I/O、Process解耦、durable row先于正常wake、outcome-driven progression、same-step retry/max-retries、atomic child identity与结构化错误；
- **全局升级**：七表relational SSOT、immutable revision/compiler digest、统一Execution/Process、claim/lease/fencing、Snapshot/ChangeSet collect-all、semantic recovery、summary-before-cleanup；
- **删除负债**：mutable JSON、rank-only runtime、跨Dispatcher job rebirth、clean/rag分表、R2/D1/DO/Worker绑定、callback/queue作为truth、parent-untouched fan-in、未接通补偿函数被误称完整reconciler；
- **明确无证据**：legacy没有完整通用 reconciler，也没有 Process projection compaction/cleanup实现；MKB recovery/cleanup来自真实崩溃窗口与owner D01要求。

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO`**：S03 的六平面 Workflow Contract、内部注册、七表 relational SSOT、canonical compiled JSON、typed acyclic route graph、Process capability/command/outcome、Execution/Process exact states、claim/lease/fencing、single/scatter collect-all、retry/cancel、semantic recovery 与 Process cleanup eligibility 已全部完成 owner-gate并进入正式候选真相。

### 8.2 强制结论

1. Workflow 必须继续是声明式、可编程的 LS-RAG 程序，但 v1 不开放 authoring/CUD；
2. 七张 definition tables 与 D01 三张 runtime tables 职责互斥，compiled JSON 不是 truth；
3. Process 必须 RAG-specific 且 leaf-only，Engine 是唯一 route/Execution 推进者；
4. Process/Execution exact states 与 RAG phase 已冻结，不再使用 legacy pending/completed 或 generic Task phase；
5. claim/lease/fencing 和 sink idempotency 是本地并发/恢复的 P0 围栏；
6. single/scatter 共用一个 Engine，scatter expected set/collect-all从第一天进入主路径；
7. success 只来自 typed outcome/proof 自下而上归约；queue/callback/log无成功权；
8. semantic recovery行为不可删除，但不要求独立Reconciler产品；
9. Process cleanup只有在完整summary和全部控制围栏关闭后成立，Event/Log与知识资产不随之删除；
10. agent authoring、exact Turso DDL、业务算法/schema、Intake/derived asset/Vector/Model/Event细节按scope留给未来或下游，不得反向破坏本文真相。

### 8.3 下游必须继续冻结的边界

| 下游 | 必须承接，但不由 S03 冒充冻结的内容 |
|---|---|
| `S04` | IntakeSource/Snapshot/Item/Revision/Membership/ChangeSet exact schema、semantic diff与canonical acceptance |
| `S05` | 已冻结ExternalKey、candidate/clean/preflight contracts、S05 binding与ExecutionGate/ReviewTarget/Decision；S03负责typed route/wait/repair，不复制其业务schema |
| `S06-S09` | 每个后续 capability 的input/output schema、算法、error code、proof生产/验证细节 |
| `S08-S10` | vector/filter publication、ready可见性、检索一致性与index cutover |
| `S11/S14` | model/prompt/version/fallback/registry policy；必须提供 immutable refs/digests |
| `S12` | 七表+executions/processes、S05四组supporting职责的exact DDL、partial/composite FK、transaction/outbox/queue/scanner/cleanup实现 |
| `S13` | logical Intake/derived asset ref、local path adapter、atomic write与retention |
| `S15` | transition/route/recovery event envelope、metrics/alerts、Event/Log retention与runbook |
| `S16` | Workflow read与内部Execution/Process diagnostics的授权、token/network/rate limit |

上述细节若只实现本文冻结接口和不变量，无需 reopen S03；若要增加业务 loop、外部/agent Workflow写面、第四层运行身份、新状态或改变proof/cancel/retry语义，必须显式 reopen。

### 8.4 一句话结论

S03 将 legacy 已验证的声明式 Workflow 与 Process 解耦原理，重建为一个以关系型定义真相、不可变编译绑定、fenced Execution/Process 状态机和可恢复 single/scatter 流程为核心的本地 LS-RAG Engine。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `S03-v1.0` | `2026-07-15` | `MKB owner + Codex` | `accepted` | 吸收冻结 Q1–Q9 与 `T-O-12..29`；正式冻结六平面 Workflow 宪法、内部注册、七表 schema、compiled JSON、capability registry、typed route/compiler、ProcessCommand/Outcome、Execution/Process exact states、claim/fencing/retry、single/scatter/cancel、semantic recovery、cleanup eligibility、验收与 legacy reference anchors。 |
| `S03-v1.1` | `2026-07-15` | `MKB owner + Codex` | `accepted / S04-calibrated` | 接收S04-v1.0：resource bindings与single/scatter targets改为Intake identities；fan-out/fan-in改以Snapshot/ChangeSet为分母；publication/cleanup绑定ServingRevision与Intake asset fence；ProcessCapabilityManifest和BindingSource词义去歧义。 |
| `S03-v1.2` | `2026-07-16` | `MKB owner + Codex` | `accepted / S05-calibrated` | 接收S05-v1.0：增加preflight leaf capability；Execution waiting reason登记human_review+gate ref；锁定S05 domain binding且resume不热切；single/scatter加入preflight/gate顺序；四个crash窗口纳入统一semantic repair，Workflow七表与runtime exact states不变。 |
| `S03-v1.3` | `2026-07-18` | `MKB owner + Codex` | `accepted / D02-state-calibrated` | 保持Workflow七表、Execution/Process八态与合法边不变；明确status/phase/wait reason/Outcome/route evidence分账；以S05 exact intake capability keys取代早期coarse process key；校准single ingress subject与acceptance后exact binding叙事，target字段与S08/S09 process粒度按D02-v1.0移交对应下游。 |
| `S03-v1.3-cal` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S06-v1.0：`lsrag.structurize` leaf contract、input digest冻结、generation非状态机、仅自动retry；typed route跳过structurize须用generation ref。 |
| `S03-v1.3-cal-s12` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S12-v1.0：outbox/claim/TX物理兑现；状态机与七表职责不变。 |
| `S03-v1.3-cal-s13` | `2026-08-11` | `MKB owner + Codex` | `accepted / S13-calibrated` | 接收S13-v1.0：binding 仅 logical handle；禁 absolute path。 |
| `S03-v1.3-cal-d05` | `2026-08-12` | `MKB owner + Codex` | `accepted / D05-calibrated` | 接收 D05-v1.0：max-retries 独占；promptA/B/C 入 Command digest；construct 前禁 vectorize（T-O-206/207/208）。 |
