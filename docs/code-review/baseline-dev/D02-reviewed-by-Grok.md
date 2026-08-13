# Nano-Agent 代码审查模板

> 审查对象: `MKB baseline runtime — Production State Constitution & Domain State Ledger (D02 域)`
> 审查类型: `code-review`
> 审查时间: `2026-08-13`
> 审查人: `Grok`
> 审查范围:
> - `src/contracts/common/models.py`、`src/contracts/runtime/models.py`、`src/contracts/workflow/models.py`
> - `src/runtime/task/`
> - `src/runtime/workflow/`
> - `src/runtime/intake/`
> - `src/services/intake_lifecycle/`、`src/services/scatter_intake.py`
> - `src/persistence/migrations/001_initial.sql`、`002_index_generation_retirement_grace.sql`、`003_scatter_root_uniqueness.sql`、`004_process_root_and_child_cancelled.sql`
> - `src/workflows/lsrag_definition.py`、`src/workflows/builtin_scatter.py`
> - `api/public/routes.py`
> - `tests/unit/test_workflow_runtime.py`、`tests/unit/test_task_projections.py`、`tests/unit/test_d01_review_fixes.py`
> 对照真相:
> - `docs/baseline/domain-truth/D02-production-state-and-routing.md`（D02-v1.0 / D02-v1.0-cal-s13）
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 先给一句话 verdict。  
> 例如：`该实现主体成立，但当前不应标记为 completed。`  
> 或：`该实现已满足 action-plan / design doc 的收口标准，可以关闭本轮 review。`

- **整体判断**：六族枚举与 DDL CHECK、Process 控制机、proof 向上归约、IntakeItem 三态与四套 SelectionPointer 分账主体成立，但当前实现**不能**标记为已完整对齐 D02；CandidateSet 边塌缩、`payload_extra` 隐式路由、S02 直写 Execution 三处违宪。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. 六 StateFamily 的 **名字与 CHECK** 与 D02 §0.3 逐字一致；写路径却跳过 CandidateSet `open`/`abandoned` 与 Execution `created`——枚举对齐不等于边对齐。
  2. 控制向下 / proof 向上的成功围栏（Process CAS + publication proof + outbox 非成功）成立；但 S02 `cancel` / `decide_gate` 直写 `mkb_executions.status`，违反 D02 §1.3 / §1.7 所有权。
  3. 声明式 Workflow 存在，但 post-Process 路由 SSOT 实际是 `ProcessOutcome.payload_extra.admission_result`，Process `operation_mode` 还会短路图；违反 D02 §0.5.3 / §3.1。

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。  
> 明确你看了哪些文件、跑了哪些命令、核对了哪些计划项 / 设计项 / closure claim。
> 如果引用了其他 reviewer 的结论，必须说明是独立复核、采纳、还是仅作为线索。

- **对照文档**：
  - `docs/baseline/domain-truth/D02-production-state-and-routing.md`（§0.1–0.6、§1.2–1.8、§2.2 DR001/DR004/DR007、§3.1–3.2、§5.3；§4 附录仅作线索）
  - 邻域校准引用（本轮不重开下游全文）：D01-v1.4、S02-v1.3、S03-v1.3、S04-v1.2、S05-v1.1 在 D02 镜像块内的声明
- **核查实现**：
  - `src/contracts/common/models.py`、`src/contracts/runtime/models.py`、`src/contracts/workflow/models.py`
  - `src/runtime/task/{task_create,task_commands,task_projection,task_projections,task_views}.py`
  - `src/runtime/workflow/{runtime_core,runtime_outcome,runtime_materialize,runtime_gates,runtime_scatter,runtime_repair,runtime_outbox,worker}.py`
  - `src/runtime/intake/{core,clean_preflight,acquisition_intents,acquisition_ingest,acceptance_snapshot,acceptance_lifecycle}.py`
  - `src/services/scatter_intake.py`、`src/services/intake_lifecycle/lifecycle_apply.py`、`lifecycle_publish.py`
  - `src/persistence/migrations/001_initial.sql` 及 `002`–`004`
  - `src/workflows/lsrag_definition.py`
- **执行过的验证**：
  - 5 路 read-only explore sub-agent（六族 / Task-Execution-Process 边 / Intake-Candidate-Gate / 正交事实与路由 / schema+durable）
  - 编排侧对全部 finding 做 **file:line 二次复核**（本报告只采纳本轮重读仍成立的行号）
  - `rg` 确认 `src/runtime` 无 `abandoned` 写、无 `reviewing|retrying|vector_ready|latest_unpublished|production_status` 业务字面量
  - 本轮未把全量 pytest 绿作为 D02 对齐证据（D02 是宪法对齐，不是测试绿）
- **复用 / 对照的既有审查**：
  - `docs/code-review/baseline-dev/D01-reviewed-by-Grok.md` — 仅作 D01 三层 runtime 线索；**D02 所有权/六族/路由条款独立复核**，不把 D01 的 `approve-with-followups` 或 success-wins 选择自动升级为 D02 合规

### 1.1 已确认的正面事实

- 六个 `StrEnum` 与 D02 §0.3 exact 集合一致：`src/contracts/common/models.py:47-95`（Task / Execution / Process / IntakeLifecycle / CandidateSetState / GateStatus）。
- 六族 DDL CHECK 与同一集合一致：`001_initial.sql:152-153`（Task）、`:251-252`（Execution）、`:322-323`（Process）、`:949-950`（IntakeItem `lifecycle_state`）、`:1136-1137`（CandidateSet `staging_state`）、`:398-399`（Gate）。
- `src/` 无 `reviewing` / `retrying` / `vector_ready` / `latest_unpublished` / `production_status` 业务状态字面量。`vector_ready` 仅出现在 `src/persistence/sqlite_port.py` 部署探针变量。
- Task create→`queued`：`src/runtime/task/task_create.py:92-96`。succeeded 禁止原地 retry：`src/runtime/task/task_commands.py:237-238`。full retry 新 generation/root：同文件 `:239-303`。
- Task result readiness 是查询事实而非第七族：`not_ready/ready/terminal_failed/terminal_cancelled` 于 `src/runtime/task/task_commands.py:325-339`。
- 公开 Task 投影的人工动作是 bounded `action_required`，不是 Task `reviewing`：`src/runtime/task/task_views.py:40-60,81`。
- Process 成功要求 output+proof，否则 integrity fail：`src/runtime/workflow/runtime_outcome.py:53-67`。成功 CAS 仅接受 `status='running'`：同文件 `:90-93`。
- Execution 成功要求 source Process + `proof_ref`：`src/runtime/workflow/runtime_outcome.py:492-507`。Task 成功要求 `proof_ref`：`src/runtime/task/task_projection.py:51-52`。
- Worker 路径为 claim → mark_running → handler → `accept_outcome`：`src/runtime/workflow/worker.py:45-62`。queue ACK 不写业务成功。
- `claim_next` 要求 `e.status IN ('ready','running')` 且 `t.status IN ('queued','running')`：`src/runtime/workflow/runtime_core.py:166-173`。human wait 的 Execution 不会被 claim，故不持 Process lease。
- waiting 行必须有 reason+ref：`001_initial.sql:288`。已写入的 reason：`human_review`（`runtime_materialize.py:542`）、`scatter_children`（`runtime_scatter.py:108`）、`durable_prerequisite`（`runtime_scatter.py:213-221`）、`retry_due`（`runtime_outcome.py:157`）。
- 自动路径不建伪 Gate：缺少 `admission_result==human_review_required` 则 fail-closed：`src/runtime/workflow/runtime_materialize.py:448-453`。
- IntakeItem 三态由 S04 `lifecycle_apply` CAS 推进：`src/services/intake_lifecycle/lifecycle_apply.py:108-110`。deactivate/delete 清空 serving：同语句 `serving_revision_uuid=NULL`。非 active 禁止 serving：`001_initial.sql:961`。
- `UPDATE mkb_intake_items SET lifecycle_state` 的生产写点不在 Task cancel / Execution fail 路径。Task cancel 只写 Task+root Execution+outbox：`src/runtime/task/task_commands.py:183-198`。
- latest / serving / S06 current / S09 active 分列分表：`001_initial.sql:951-952`、`:1333-1346`、`:1583-1606`。
- S08/S09 分 Process：`lsrag.vectorize` 与 `index.validate_publication` 注册于 `src/workflows/lsrag_definition.py:186-194,541-542` 与 `src/runtime/intake/core.py:299-300`。`vectorizing_indexing` 只是 `WorkflowPhaseKey`：`src/contracts/workflow/models.py:78`。
- handler 返回 `disposition="waiting"` 被引擎拒绝：`src/runtime/workflow/runtime_outcome.py:208-215`。
- 同 Process UUID 的 `retryable_failure` → `retry_wait` → promote `ready`：`runtime_outcome.py:128-142,236-248`。delivery/recovery/retry 分计数，不另造 Attempt 表。

### 1.2 已确认的负面事实

- CandidateSet 生产 INSERT 写 `staging_state='sealed'`，跳过 `open`：`src/runtime/intake/clean_preflight.py:186-221`（`:221` 字面 `"sealed"`）。
- 元数据 no-change 路径 INSERT `staging_state='accepted'`：`src/runtime/intake/acquisition_intents.py:190-221`（`:221` 字面 `"accepted"`）。
- `src/runtime` 内无任何 `abandoned` 写点（`rg abandoned src/runtime` 零命中）。`abandoned` 仅存在于 enum 与 CHECK。
- sealed 行在 seal 之后仍被 UPDATE preflight refs：`src/runtime/intake/clean_preflight.py:382,641`（`WHERE staging_state='sealed'`）。
- Root Execution INSERT 直接 `'ready'`，跳过 `created`：`src/runtime/task/task_create.py:319-324`。
- Scatter child Execution 由 `scatter_intake` INSERT `ready|waiting`：`src/services/scatter_intake.py:560-572`。
- Task cancel 直写 Execution `cancelling`：`src/runtime/task/task_commands.py:188-191`。
- `decide_gate` 直写 Execution `waiting→running` 并 CAS Gate terminal：`src/runtime/task/task_projections.py:370-394`。引擎注释把该投影宣称为 Task 所有：`src/runtime/workflow/runtime_gates.py:159-164`。
- `WorkflowGatesMixin.resolve_gate`（`runtime_gates.py:24`）在生产调用图中无引用；活路径是 `decide_gate` + outbox + `consume_gate_decision`。
- 成功后路由把 `outcome.payload_extra` 交给 `_route_after_terminal_process_tx`：`src/runtime/workflow/runtime_outcome.py:120-126`。Guard 从该 context 读 `admission_result`：`src/runtime/workflow/runtime_materialize.py:84-93`。
- intake 把 `admission_result` 写入 Outcome `payload_extra`：`src/runtime/intake/core.py:103-116`；passthrough 再复制：`:357-362`。
- `operation_mode ∈ {lifecycle,index_rebuild,index_rebuild_noop,metadata_no_change}` 时非 acquire/rebuild 的 capability 走 `_passthrough`：`src/runtime/intake/core.py:278-281`。
- `_acquire` 按 `request_intent` 再分叉，含 `index.rebuild`：`src/runtime/intake/acquisition_ingest.py:35-46`。
- Task 投影允许 `queued→failed` 与 `cancelling→succeeded`：`src/runtime/task/task_projection.py:58-64`。
- 未 claim 的 deadline 从 `ready` 失败 Process：`src/runtime/workflow/runtime_core.py:186-193`。
- 下步物化把非终态 Execution 写成 `ready`（含 running→ready）：`src/runtime/workflow/runtime_materialize.py:297-300`。
- Membership `decision_kind` 无 CHECK：`001_initial.sql:1030`。写值为 `'accepted'`：`acceptance_snapshot.py:181`、`scatter_intake.py:460`。
- ProcessOutcome 使用 `disposition` 而非 D02 的 `outcome_status` + `retryability`：`src/contracts/runtime/models.py:43`。DB `last_failure_retryability IN (0,1)`：`001_initial.sql:339`。
- `waiting_reason` / `phase_key` 无闭集 CHECK：`001_initial.sql:254-255`。`process_join` 无生产写点。
- Execution `target_kind/target_uuid` 与 snapshot 列共用一个账户：`001_initial.sql:237-240`。scatter child 把 `intake_revision_uuid` 放进 `payload_extra`：`scatter_intake.py:544-552`。
- `payload_extra` 的契约注释写明「never controls state transitions」：`src/contracts/common/models.py:3-5`；与上述路由读 extra 并存。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 全部 finding 与对齐项绑定本轮重读的 `path:line`；舰队叙述未复核者不采纳 |
| 本地命令 / 测试 | `yes` | `rg` / `read_file` 静态复核；未把全量 pytest 绿当作 D02 对齐证据 |
| schema / contract 反向校验 | `yes` | `001_initial.sql` CHECK 与 `models.py` 六族对账；并核对非六族 `status` 列 |
| live / deploy / preview 证据 | `n/a` | D02 为共有域状态宪法，不依赖 live GPU |
| 与上游 design / QNA 对账 | `yes` | 直接对账 D02-v1.0 规范正文 §0–§3 / §5；§4 附录不作验收 SSOT |

---

## 2. 审查发现

> 使用稳定编号：`R1 / R2 / R3 ...`。
> 每条 finding 都应包含：严重级别、类型、事实依据、为什么重要、审查判断、建议修法。
> 只写真正影响 correctness / security / scope / delivery / test evidence 的问题，不写纯样式意见。

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | CandidateSet 合法边塌缩：无 `open`/`abandoned`，一处直写 `accepted` | `high` | `protocol-drift` | `yes` | 恢复 `open→sealed→accepted`；禁止 INSERT-as-accepted；补 abandon |
| R2 | `payload_extra` + Process `operation_mode` 成为隐式 router | `high` | `protocol-drift` | `yes` | 路由只读 typed fact / Task 列；删除 handler 短路 |
| R3 | S02 直写 Execution（cancel / Gate resume） | `high` | `protocol-drift` | `yes` | Task 只发 command；S03 独占 Execution 转移 |
| R4 | Execution `created` 从未写入；child 由 S04 committer 直插 | `medium` | `protocol-drift` | `no` | INSERT `created`；child 物化收口 S03 |
| R5 | 字面非法边：`queued→failed`、`cancelling→succeeded`、`ready→failed` | `medium` | `correctness` | `no` | 改边或回填 D02/S02/S03 镜像（含 D01 success-wins 冲突） |
| R6 | Membership `decision_kind='accepted'` 且无 CHECK | `medium` | `delivery-gap` | `no` | 冻结 S04 spelling + CHECK；此前 fail-closed |
| R7 | Execution `target_*` 万能账户 + revision 进 `payload_extra` | `medium` | `delivery-gap` | `no` | 按 DR001 分账 subject / output / pointer |
| R8 | ProcessOutcome 契约 ≠ `outcome_status` + `retryability` | `medium` | `protocol-drift` | `no` | 拆字段；去掉 `waiting` disposition |
| R9 | `waiting_reason`/`phase_key` 无闭集；`process_join` 死 | `low` | `delivery-gap` | `no` | CHECK 或从镜像删除未用 reason；ready 必写 phase |
| R10 | S09 pointer `lifecycle_state` 六值机 / 命名碰撞 | `low` | `docs-gap` | `no` | 保持为 SelectionPointer；避免称 lifecycle/status |

### R1. CandidateSet 合法边塌缩：无 `open`/`abandoned`，一处直写 `accepted`

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - D02 §1.6：`create→open`；`open→sealed/abandoned`；`sealed→accepted`；open 不得 accept；S05 只写 open pages 并请求 seal；abandoned 不得建 Snapshot。
  - `src/runtime/intake/clean_preflight.py:186-221`：single ingest `INSERT … staging_state` 字面 `"sealed"`（`:221`）。scatter seal 同形：`:282-318`。
  - `src/runtime/intake/acquisition_intents.py:190-221`：no-change 元数据路径 `INSERT` 字面 `"accepted"`（`:221`），跳过 open 与 sealed。
  - `src/runtime` 无 `abandoned` 写点。schema 仍声明四态：`001_initial.sql:1136-1137`。
  - sealed 之后仍 UPDATE preflight outcome refs：`clean_preflight.py:382,641`。D02：「sealed 不得热切 validator」。
  - accept CAS 要求已是 sealed：`acceptance_snapshot.py:193-195`、`scatter_intake.py:262-264`——合法 `sealed→accepted` 边存在，但上游从未经过 `open`。
- **为什么重要**：
  - CandidateSet 是 D02 六个 StateFamily 之一。跳过 `open` 使 S05 producer / S04 acceptance 线性化点无法按宪法观测。
  - S05 直写 `accepted` 抢了 S04 canonical acceptance 所有权。
  - cancel/fail 不能 abandon 未接受集合，留下永久 `sealed` 孤儿。
- **审查判断**：
  - schema/enum **对齐**；写路径 **塌缩为 sealed/accepted 两态**。这是 D02 对齐的 blocker，不是「实现捷径可忽略」。
- **建议修法**：
  - 生产 INSERT 先写 `open`（可含 pages），同一 UoW 再 CAS `open→sealed`，并把 preflight refs 绑在 seal 边而不是事后热切。
  - 删除 `acquisition_intents.py` 的 INSERT-as-accepted。no-change 用 S04 Membership `no-change` fact / item transition，不伪造 CandidateSet 终态。
  - 对未 accept 的 sealed set，在 Execution/Process 取消或超时时走 `abandoned`；abandoned 禁止建 Snapshot。
  - 补 unit：open→sealed→accepted；open→abandoned；禁止 open accept；禁止 S05 写 accepted。

### R2. `payload_extra` + Process `operation_mode` 成为隐式 router

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - D02 §0.5.3 / §0.6 / §3.1：queue、HTTP、projection、`payload_extra` 与 Process 均不得成为隐式 router；正交 fact 必须 typed + owner。
  - 契约自述 extra「never controls state transitions」：`src/contracts/common/models.py:3-5`。
  - 成功路由：`runtime_outcome.py:120-126` 把 `outcome.payload_extra` 传入 `_route_after_terminal_process_tx`。
  - Guard 映射 `registered_admission_result` → context `admission_result`：`runtime_materialize.py:84-93`。human Gate 也读 `route_context["admission_result"]`：`:448`。
  - intake 成功 Outcome 携带 `payload_extra=route_extra`：`src/runtime/intake/core.py:116`。passthrough 再塞 `admission_result` / `request_intent`：`:357-362`。
  - `operation_mode` 短路声明图：`core.py:278-281`。
  - `_acquire` 按 intent 再路由，含 `index.rebuild` 兼容分叉：`acquisition_ingest.py:35-46`。
- **为什么重要**：
  - 路由真相活在可变 bag，而不是 CandidateSet.`preflight_outcome_*` 或 Task.`request_intent`。
  - 同一 Workflow 图被 Process 内部 mode 绕过，D02 要求「下游 Truth 决定 route，冻结后回填」，而不是 handler 当 router。
- **审查判断**：
  - 声明式 route/guard **存在**；**生效输入**却是 extra。这是宪法级 SSOT 漂移，不是缺图。
- **建议修法**：
  - Guard 只读：Task.`request_intent`、CandidateSet.`preflight_outcome_digest` / 已提交的 typed PreflightOutcome、GateDecision。禁止从 `payload_extra` 读控制键。
  - 删除 `operation_mode` passthrough；lifecycle / rebuild / no-change 用独立 start route 或独立 Process key。
  - `admission_result` 收敛为 PreflightOutcome `passed/blocked` + 独立「需要 Gate」fact，不再用 `auto_admitted/human_review_required` 当 combo status。
  - 补 unit：缺少 extra 时若 typed fact 在仍能正确分支；只有 extra、没有 typed fact 时 fail-closed。

### R3. S02 直写 Execution（cancel / Gate resume）

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - D02 §1.3：Execution 所有权在 S03；「leaf Process、Task API 与 Gate handler 均不得直写」。
  - D02 §1.7：S03 拥有 waiting/resume；S02 只投影 `action_required` 并提供 Task-scoped command。
  - `src/runtime/task/task_commands.py:183-198`：同一 TX 写 Task `cancelling` **并且** `UPDATE mkb_executions SET status='cancelling'`，再 enqueue `cancel_execution`。
  - `src/runtime/task/task_projections.py:370-394`：`decide_gate` CAS Gate `released/rejected`，并把 Execution `waiting→running`。
  - `src/runtime/workflow/runtime_gates.py:159-164` 文档化「Task service owns … waiting-to-running projection」。
  - 引擎侧 `resolve_gate`（`:24-104`，waiting→`ready` + 当场 route）生产无调用；`consume_gate_decision`（`:158`）假定投影已完成。
- **为什么重要**：
  - 双写：Task API 已改 Execution，outbox 再让 S03 解释。所有权与 resume 边（running vs ready）分叉。
  - outbox 延迟时 Execution 已是 `running` 但下一 Process 可能尚未物化。
- **审查判断**：
  - 功能可走通（e2e Gate 依赖此投影），但 **违宪**。S03 调用 `project_task_status_tx` 是调用 S02 helper，**不**构成本条；反向（S02 写 Execution）才是。
- **建议修法**：
  - cancel：只 CAS Task `cancelling` + outbox；由 `request_cancellation` / `_cancel_execution_tree_tx` 独占 Execution 树。
  - Gate：S02 只 append Decision + outbox；S03 consume 时做 waiting→ready（或文档化 waiting↔running）并 apply routes。删除或合并死路径 `resolve_gate`。
  - 补 unit：cancel / decide 的同一 TX 内 `mkb_executions.status` 尚未变；消费 outbox 后才变。

### R4. Execution `created` 从未写入；child 由 S04 committer 直插

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - D02 §1.3：`create→created`；`created→ready/failed/cancelling`。
  - DDL default 是 `created`：`001_initial.sql:251-252`。
  - Root INSERT 字面 `'ready'`：`src/runtime/task/task_create.py:319-324`。
  - Child INSERT `ready|waiting`：`src/services/scatter_intake.py:560-572`（S04 acceptance UoW）。
  - `created` 只在 repair 扫描中出现：`src/runtime/workflow/runtime_repair.py:100`。
- **为什么重要**：
  - `created` 成为死状态；S04 committer 物化 child Execution 越过 S03 transition service。
- **审查判断**：
  - 运行上 root 以 `ready` 可被 materialize/claim，**功能可工作**；边表与所有权 **PARTIAL**。
- **建议修法**：
  - 所有 Execution INSERT 用 `created`；S03 `materialize_root` / child 激活再推 `ready`。
  - S04 只提交 child binding fact；由 S03 插 Execution 行。

### R5. 字面非法边：`queued→failed`、`cancelling→succeeded`、`ready→failed`

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - D02 §1.2 Task 边：queued→running/cancelling；running→succeeded/failed/cancelling；cancelling→cancelled。无 queued→failed，无 cancelling→succeeded。
  - D02 §1.4 Process 边：无 ready→failed。
  - `src/runtime/task/task_projection.py:58-61`：success-wins，允许 `cancelling→succeeded`。`:62-64`：允许 `queued→failed`。
  - `src/runtime/workflow/runtime_core.py:186-193`：未 claim 的 deadline 调用 `_fail_process_tx`（Process 仍为 `ready`）。
  - 另：`runtime_materialize.py:297-300` 把非终态（含 `running`）写成 `ready`；retry/scatter 有 `waiting→ready`。D02 字面是 running↔waiting，无 running→ready。
- **为什么重要**：
  - D01 审查明确选择 success-wins；D02 边表是 `cancelling→cancelled`。两份 frozen Truth 不能同时当 SSOT。
  - queued→failed 覆盖「首 Process 未 mark_running 就 integrity fail」；合法表达应先 queued→running 或失败停在 Execution 层。
- **审查判断**：
  - 不是「状态写飞」；是 **边表未校准**。实现已按 D01 residual 固化。
- **建议修法**：
  - 任选其一并同一校准单元回填：改 `project_task_status_tx` 拒绝 cancelling→succeeded / queued→failed；或 reopen S02/D02 镜像显式允许这些边（及工序间 running→ready、deadline-before-claim）。
  - 在冲突关闭前，新分支按 D02 字面 fail-closed（T-O-92）。

### R6. Membership `decision_kind='accepted'` 且无 CHECK

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - D02 §1.8 / DR004：语义族 `seen/new-revision/no-change/absence`；exact spelling 归 S04；不得从散文猜 DDL。
  - `001_initial.sql:1030`：`decision_kind TEXT NOT NULL`，无 CHECK。
  - 写入 `'accepted'`：`src/runtime/intake/acceptance_snapshot.py:181`；`src/services/scatter_intake.py:460`。
  - 读者按 `'accepted'` join：`src/runtime/workflow/runtime_scatter.py` / `runtime_gates.py`（`decision_kind='accepted'`）。
- **为什么重要**：
  - 把 CandidateSet/Snapshot 语言写进 Membership 列，无法表达 no-change/absence。
  - DR004 未冻 spelling 时，正确行为是 fail-closed，而不是提前冻结错误词。
- **审查判断**：
  - **非**第七 StateFamily。是正交 fact 拼写未冻却已当 SSOT。
- **建议修法**：
  - 冻结 S04 enum + CHECK + 与 nullable refs 的组合约束；迁移现有 `'accepted'` 到 `seen`/`new-revision` 等。
  - 在冻结前，未知 spelling fail-closed，不要再扩散 `'accepted'` 读路径。

### R7. Execution `target_*` 万能账户 + revision 进 `payload_extra`

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - D02-DR001：subject、output 与 pointer 必须分账；不得热切一个万能 target。状态 `deferred / non-blocking`。
  - `001_initial.sql:237-240`：`target_kind` / `target_uuid` / `intake_snapshot_uuid` / `intake_snapshot_digest`。
  - Root create：`target_kind='task'`（`task_create.py:319-334`）。
  - Scatter child：`target_kind='intake_item'`，`intake_revision_uuid` 进入 `payload_extra`：`scatter_intake.py:544-572`。
- **为什么重要**：
  - 运行后 accepted output 与 ingress subject 共用一列，后续 route/proof 只能从 extra 取 revision。
- **审查判断**：
  - D02 **未要求本轮做完 DDL**；但实现已按「未分账」落地，属于 deferred 项的提前固化。
- **建议修法**：
  - 拆 subject_ref / accepted_output_ref / pointer；revision 进 typed 列。S04 提交 fact，S03 写 Execution 列。

### R8. ProcessOutcome 契约 ≠ `outcome_status` + `retryability`

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - D02 §1.4 / §1.8：`outcome_status=succeeded/failed/cancelled` + `retryability=retryable/non_retryable/indeterminate`，是 immutable 结果事实，不是 Process current state。
  - `src/contracts/runtime/models.py:43`：`disposition: Literal["succeeded", "failed", "retryable_failure", "waiting"]`。
  - 引擎拒绝 `waiting`：`runtime_outcome.py:208-215`。
  - DB 将 retryability 压成 `last_failure_retryability IN (0, 1)`：`001_initial.sql:339`。
- **为什么重要**：
  - `waiting` 是 Execution 状态名，出现在 Outcome 契约上制造双轴。
  - 丢失 `cancelled` outcome 与 `indeterminate` retryability。
- **审查判断**：
  - 运行时仍把 Outcome 当 fact（CAS 进 Process status），**形状漂移**，不是「Outcome 当了 Process 状态」。
- **建议修法**：
  - 拆 `outcome_status` + `retryability`；handler 禁止发 `waiting`；`cancelled` 仍由引擎写 Process 状态并可记 outcome fact。
  - DB 用三值 retryability 或保留 indeterminate 的独立列。

### R9. `waiting_reason`/`phase_key` 无闭集；`process_join` 死

- **严重级别**：`low`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - D02 §1.3：冻结 waiting reason 五元组含 `process_join`；ready/running/waiting 的 `phase_key` 必须确定。
  - `001_initial.sql:254-255`：两列无 CHECK。`:288` 只强制 waiting 时非空。
  - 四 reason 有写点（见 §1.1）；`process_join` 无生产写。
  - root/child `ready` INSERT 常 `phase_key=NULL`：`task_create.py:319-324`；`scatter_intake.py:561`（activate_now 时 `child_phase = None`）。
- **为什么重要**：
  - 未冻 spelling 的 reason 可入库；repair 对未知 reason fail-closed（`runtime_repair.py` 等待扫描），形成「能写入、恢复不认」的断点。
- **审查判断**：
  - 已实现的四 reason + waiting CHECK **部分对齐**；闭集与 phase 确定性未完成。
- **建议修法**：
  - 给 `waiting_reason` 加五值 CHECK，或从 D02 镜像删除 `process_join` 并双向校准。
  - materialize/create 在进入 ready/running/waiting 时写入确定 `phase_key`。

### R10. S09 pointer `lifecycle_state` 六值机 / 命名碰撞

- **严重级别**：`low`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - D02 §0.4 / §1.8：ActiveIndexPointer 是 SelectionPointer，**不是** StateFamily；禁止把 pointer 进度命名成通用 status / 第七族。
  - `001_initial.sql:1589-1591`：`lifecycle_state IN ('building','validating','ready_candidate','active','retiring','withdrawn')`。
  - 运行时 deactivate 写 `'withdrawn'`：`lifecycle_apply.py:125-127`。publish/rebuild 路径主要落 `active`。
- **为什么重要**：
  - `lifecycle_state` 与 IntakeItem lifecycle 撞名；`ready_candidate` 邻近禁止词 `vector_ready`。
- **审查判断**：
  - **不是**第七生产 StateFamily（无 Task/Execution 式控制边，S09 拥有指针账户）。误报风险见 O5。词汇污染成立。
- **建议修法**：
  - 保持为 pointer 列；文档与 API 禁止称 status。若 S09 需要机，用 `pointer_phase` 等非 lifecycle 名，并与 `soft_purged` 等 S09 词对齐。

---

## 3. In-Scope 逐项对齐审核

> 如果存在 action-plan / design doc / closure claim，就必须有这一节。
> 结论统一使用：`done | partial | missing | stale | out-of-scope-by-design`。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | T-O-88：v1 仅六个 StateFamily，exact 状态集合 | `partial` | 六族 enum+CHECK 逐字对齐；CandidateSet/Execution 写路径跳过部分 exact 状态 |
| S2 | §1.2 Task aggregate 合法边与所有权 | `partial` | 六态、retry/rebuild、readiness 分账成立；cancel 抢写 Execution；存在 queued→failed / success-wins |
| S3 | §1.3 Execution 合法边、waiting reason、phase、所有权 | `partial` | 八态 CHECK 与四 reason 落地；`created` 死；S02/S04 直写；`process_join` 缺；phase 可空 |
| S4 | §1.4 Process 合法边、fence、Outcome 分账 | `partial` | 边/fence/同 UUID retry/分计数成立；Outcome 形状漂移；多一条 ready→failed |
| S5 | §1.5 IntakeItem lifecycle 与 latest/serving | `done` | 三态 CAS、cancel 不偷 lifecycle、serving 仅 active、四指针分账 |
| S6 | §1.6 IntakeCandidateSet 合法边与 S04/S05 cutoff | `missing` | 无 `open`/`abandoned` 写；一处 S05 直写 `accepted`；sealed 热切 preflight |
| S7 | §1.7 ExecutionGate 边、不建伪 gate、S03 resume | `partial` | 四态与 evidence/fail-closed 成立；Gate+resume 写在 TaskService |
| S8 | §1.8 正交事实不得当状态机 | `partial` | readiness/TaskItem/S06 pointer/proof 分账；Membership/admission_result 被当路由状态 |
| S9 | §0.5 控制向下、proof 向上、terminal 不复活 | `partial` | proof 围栏与 retry/rebuild 成立；控制向下在 cancel/Gate/extra 路由处泄漏 |
| S10 | §0.6 共有非法行为（第七族、alias、extra 当 Truth） | `partial` | 无 reviewing 等业务状态；extra 当 router 与 Membership `accepted` 违规 |
| S11 | §3.1 Process/queue/API/projection 不得成为隐式 router | `missing` | 声明图存在，生效路由走 extra + `operation_mode` + `_acquire` intent 分叉 |
| S12 | §0.5.3 成功证明不是 queue/HTTP/文件 | `done` | 成功要求 Process/Execution/Task proof；outbox `done` 不升业务成功 |
| S13 | human wait 不持 active Process lease | `done` | `claim_next` 排除 waiting；Gate 在 accept Process 已 succeeded 之后打开 |
| S14 | S08=`lsrag.vectorize`；publication=`index.validate_publication`；phase 可 `vectorizing_indexing` | `done` | 定义、dispatch、phase enum 一致 |
| S15 | DR007：物理事实不是业务 SSOT；恢复依赖 durable/fence/outbox | `done` | cleanup 仅 eligibility；向量/文件不决定 serving；repair 扫 DB/outbox |

### 3.1 对齐结论

- **done**: `5`（S5、S12、S13、S14、S15）
- **partial**: `8`（S1–S4、S7–S10）
- **missing**: `2`（S6、S11）
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像「六族骨架与 proof 围栏完成，但 CandidateSet 边、跨域写 Execution、extra 路由仍未收口」，而不是 D02 completed。

---

## 4. Out-of-Scope 核查

> 本节用于检查实现是否越界，也用于确认 reviewer 是否把已冻结的 deferred 项误判为 blocker。

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | D02 不拥有下游 route 算法、exact kind、API、DDL（§0.1 / §3.1） | `部分违反` | reviewer 未要求 D02 冻结算法；但实现用 extra/Process 当隐式 router，越过「由下游 Truth 声明 route」 |
| O2 | DR001 Execution subject/output exact 字段 deferred | `部分违反` | 未把缺列当本轮 blocker（R7 非 blocker）；实现已用万能 `target_*` + extra 固化 |
| O3 | DR004 Membership/Gate action exact CHECK deferred | `部分违反` | 未把缺 CHECK 当 blocker（R6 非 blocker）；实现已猜 `'accepted'` 并当 join SSOT |
| O4 | §4 Appendix 不得生成 enum/route/DDL/验收断言 | `遵守` | 本审查不以 A.2/A.4 作裁决；仅作理解线索 |
| O5 | S09 pointer 内部机 / `soft_purged` 归 S09，不是 D02 第七族 | `误报风险` | R10 仅作命名/分类 follow-up，不升 P0「第七 StateFamily」 |
| O6 | S12–S15 物理表、retention 数值、运营平台（DR007 余量） | `遵守` | 未要求物理删 Process 或 R2 数值；eligibility fence 仍在 |
| O7 | D01 success-wins（cancelling→succeeded） | `误报风险` | 相对 D01 是已选规则；相对 D02 是边冲突。R5 要求校准，不把 D01 实现本身当回归 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：D02 六族名字、Process 控制机、proof 向上与 IntakeItem/指针分账成立，但 CandidateSet 边、隐式路由、S02 直写 Execution 使本轮不能关闭。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. R1：CandidateSet 恢复 `open→sealed→accepted`；删除 INSERT-as-accepted；为未接受集合提供 `abandoned`。
  2. R2：post-Process 路由离开 `payload_extra`；删除 `operation_mode` 对声明图的短路。
  3. R3：Task cancel / Gate decide 不再 `UPDATE mkb_executions.status`；S03 独占 Execution 转移。
- **可以后续跟进的 non-blocking follow-up**：
  1. R4 Execution `created` + child 物化收口 S03。
  2. R5 与 D01 success-wins / 工序间 ready / deadline-before-claim 的双向校准。
  3. R6/R7 在 S04/S03 冻结单元内收 DR004/DR001（先 fail-closed，再迁 spelling/分账）。
  4. R8 ProcessOutcome 拆 `outcome_status` + `retryability`。
  5. R9 waiting_reason/phase CHECK；R10 指针列改名或文档去 lifecycle。
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
