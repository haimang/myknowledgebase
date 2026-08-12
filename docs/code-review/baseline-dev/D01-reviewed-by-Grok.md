# Nano-Agent 代码审查模板

> 审查对象: `MKB baseline runtime — Task / Execution / Process (D01 域)`
> 审查类型: `code-review`
> 审查时间: `2026-08-12`
> 审查人: `Grok`
> 审查范围:
> - `src/runtime/task/`
> - `src/runtime/workflow/`
> - `src/runtime/intake/`
> - `src/persistence/migrations/001_initial.sql`、`003_scatter_root_uniqueness.sql`
> - `src/contracts/common/models.py`、`src/contracts/api/models.py`
> - `src/workflows/lsrag_definition.py`、`src/workflows/builtin_scatter.py`
> - `src/services/scatter_intake.py`
> - `api/public/routes.py`
> - `tests/e2e/test_single_intake_pipeline.py`、`tests/e2e/test_registered_api_scatter.py`、`tests/e2e/test_human_review_gate.py`、`tests/unit/test_workflow_runtime.py`、`tests/unit/test_task_projections.py`
> 对照真相:
> - `docs/baseline/domain-truth/D01-task-execution-process-flow.md`（D01-v1.4）
> 文档状态: `reviewed`

---

## 0. 总结结论

> 先给一句话 verdict。  
> 例如：`该实现主体成立，但当前不应标记为 completed。`  
> 或：`该实现已满足 action-plan / design doc 的收口标准，可以关闭本轮 review。`

- **整体判断**：D01 三层运行身份与 durable 控制路径主体已在代码与 schema 中落地，无结构性 P0 偏离；仍有若干 non-blocking residual（retry 分类、Task 投影多写点、schema 软指针与列族缺口）。
- **结论等级**：`approve-with-followups`
- **是否允许关闭本轮 review**：`yes`
- **本轮最关键的 1-3 个判断**：
  1. Task / Execution / Process 三表、三套状态枚举、root/parent/retry 血缘与 `current_root_execution_uuid` 指针符合 D01-T001–T014 / §5。
  2. 统一 `accept_outcome` + publication proof 成功围栏 + scatter Snapshot/ChangeSet fan-in 符合 D01-T024–T026 / E04 / E06。
  3. 最大业务 residual 是 intake 阶段几乎不发 `retryable_failure`（T027/E05 引擎齐、分类偏薄），以及 Task 投影写路径未收敛到单一 transition 服务。

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。  
> 明确你看了哪些文件、跑了哪些命令、核对了哪些计划项 / 设计项 / closure claim。
> 如果引用了其他 reviewer 的结论，必须说明是独立复核、采纳、还是仅作为线索。

- **对照文档**：
  - `docs/baseline/domain-truth/D01-task-execution-process-flow.md`（§1.2–1.6、§2.2–2.7、§3、§4、§5、§6 E01–E07）
  - 邻域校准引用：`S02/S03/S04/S05/S08/S09/S12` 在 D01 文内声明（本轮不展开邻域全文）
- **核查实现**：
  - `src/runtime/task/{task_create,task_commands,task_views,task_projections,service}.py`
  - `src/runtime/workflow/{runtime_core,runtime_outcome,runtime_scatter,runtime_repair,runtime_outbox,runtime_materialize,worker,types,constants}.py`
  - `src/runtime/intake/core.py` 与 stage mixins
  - `src/persistence/migrations/001_initial.sql`、`003_scatter_root_uniqueness.sql`
  - `src/contracts/common/models.py`
  - 相关 e2e/unit 测试（见审查范围）
- **执行过的验证**：
  - 5 路 read-only explore sub-agent（identity / status / durable-TX / topology / schema）
  - 编排侧 `rg` / `read_file` 对关键路径做 **file:line 二次复核**（本报告仅采纳已复核行号）
  - 未在本轮重跑全量 pytest（以源码/schema 静态审计为主）
- **复用 / 对照的既有审查**：
  - 会话内 D01 舰队审查结论 — 作为线索；**本报告对关键 finding 做了独立 file:line 复核**，未盲从未标注行号的叙述

### 1.1 已确认的正面事实

- Task 六态 / Execution 八态 / Process 八态在 contracts 与 DDL CHECK 中一致（`src/contracts/common/models.py:47-75`；`001_initial.sql` tasks/executions/processes status CHECK）。
- 公开 Task 投影不含 `execution_uuid` / `process_uuid` 主键字段（`src/runtime/task/task_views.py:61-93`）。
- 生产 process key 含 `lsrag.vectorize` 与 `index.validate_publication`，dispatch 与定义对齐（`src/runtime/intake/core.py:241-261`）；`src/**/*.py` 无 `lsrag.vectorize_index` 生产注册。
- Worker 仅 `claim_next` → `mark_running` → `handler.run` → `accept_outcome`（`src/runtime/workflow/worker.py:48-92` 一带）；intake 对 `MkbError` 返回 outcome，不直写 Process 行。
- Execution 成功强制 source Process + `proof_ref`（`src/runtime/workflow/runtime_outcome.py:492-505`）。
- 全量 Task retry 新 root `execution_uuid` 并写 `retry_of_execution_uuid`（`src/runtime/task/task_commands.py:239-302`）。
- Cancel：Task `cancelling` + root 同步 + outbox `cancel_execution`；`claim_next` 要求 `t.status IN ('queued','running')`（`src/runtime/workflow/runtime_core.py:173`）。
- Cleanup eligibility 要求终态摘要、无活跃 Process、成功时 `publication_proof_ref` 等（`src/runtime/workflow/runtime_repair.py:254-302` 一带）。
- 三张核心运行表 + `task_audits` + `task_restarts` 存在；禁止的 join/attempts/分表 process 控制表未出现（`001_initial.sql:140-366`）。
- Scatter root 唯一性由 migration `003` 将 `ux_mkb_exec_one_root` 扩至 `root|scatter_root`（`003_scatter_root_uniqueness.sql:8-12`）。

### 1.2 已确认的负面事实

- Intake 统一错误路径将 `MkbError` 映射为 `disposition="failed"`，非 `retryable_failure`（`src/runtime/intake/core.py:119-137`）。
- `TaskCommandsMixin.transition_from_runtime` 仅定义于 `src/runtime/task/task_commands.py:372`；`rg` 显示 **无其他生产调用方**。
- Cancel 树中 `ready`/`retry_wait` Process 直接写 `cancelled`，不经 `cancelling`（`src/runtime/workflow/runtime_outcome.py:673-677`）。
- Generation 投影 `counts.cancelled` 使用 `cancelled_process_count`（`src/runtime/task/task_views.py:225-230`），与 sibling 的 child 计数轴不一致。
- `mkb_processes` 无 `root_execution_uuid` 列（`001_initial.sql:301-360` 列清单）；`tasks.current_root_execution_uuid` 无 FK 到 executions。
- 物理删除 Process 投影未在 cleanup eligibility 路径中实现（仅 `cleanup_eligible_at` / `cleanup_fence_digest` 标记）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 本报告 finding 与对齐项均绑定 `path:line` 或 SQL 片段 |
| 本地命令 / 测试 | `yes` | 本轮以 `rg`/`read_file` 静态复核为主；未重跑全量 pytest 作为本文件硬证据 |
| schema / contract 反向校验 | `yes` | `001_initial.sql` / `003_*.sql` vs D01 §5 列族与禁止表 |
| live / deploy / preview 证据 | `n/a` | D01 为运行模型真相，不依赖 live GPU |
| 与上游 design / QNA 对账 | `yes` | 直接对账 D01-v1.4；QNA 不作为执行 SSOT |

---

## 2. 审查发现

> 使用稳定编号：`R1 / R2 / R3 ...`。
> 每条 finding 都应包含：严重级别、类型、事实依据、为什么重要、审查判断、建议修法。
> 只写真正影响 correctness / security / scope / delivery / test evidence 的问题，不写纯样式意见。

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | Intake 阶段错误几乎不发 `retryable_failure` | `medium` | `correctness` | `no` | 对瞬时/可恢复错误映射 `retryable_failure` |
| R2 | Task 状态投影多写点 + 死路径 `transition_from_runtime` | `medium` | `protocol-drift` | `no` | 统一写入口或删除死 API |
| R3 | Generation 公开 counts 的 cancelled 轴混用 process 计数 | `low` | `correctness` | `no` | 改字段源或改名避免误读 |
| R4 | idle Process cancel 直转 `cancelled`，边表与 S03 字面不完全一致 | `low` | `protocol-drift` | `no` | 文档校准或补中间态 |
| R5 | Process 缺 `root_execution_uuid` 冗余；Task/Execution 软指针无 FK | `low` | `delivery-gap` | `no` | 可选列/FK 或应用级断言 |
| R6 | Cancel 全树收敛 / success-vs-cancel 竞态测试偏弱 | `low` | `test-gap` | `no` | 补 e2e/unit |
| R7 | Cleanup 仅 eligibility 标记、无物理删 | `low` | `delivery-gap` | `no` | 按 S12/S15 后续实现（D01 允许分阶段） |

### R1. Intake 阶段错误几乎不发 `retryable_failure`

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/intake/core.py:119-137`：`MkbError` / 输入异常均走 `_failed`，`disposition="failed"`。
  - `src/runtime/workflow/runtime_outcome.py:128` 一带：引擎完整支持 `retryable_failure` → `retry_wait` + `retry_count+1`。
  - `src/runtime/workflow/worker.py:54-62`：仅 **未捕获异常** 包装为 `retryable_failure`。
- **为什么重要**：
  - D01-T027 / E05 要求自动工序 retry 与 max_retries 成为真实控制路径；若业务瞬时失败（HTTP/embed 等）一律 terminal `failed`，则三层 retry 矩阵在 **产品分类层** 未兑现。
- **审查判断**：
  - 控制机能力 **存在**；intake 错误分类 **偏薄**。非“不能 retry”，而是“几乎不进入自动 retry”。
- **建议修法**：
  - 为可恢复错误码闭集（如 transport/503 类）返回 `ProcessOutcome(disposition="retryable_failure", ...)`。
  - 保持校验/契约失败为 `failed`。
  - 增加 unit：模拟瞬时失败 → `retry_wait` → 再次 claim 成功。

### R2. Task 状态投影多写点 + 死路径 `transition_from_runtime`

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - 生产写 Task status 的路径包括：`src/runtime/workflow/runtime_core.py:257` 一带（running）；`src/runtime/task/task_commands.py:184-185`（cancelling）；`src/runtime/workflow/runtime_outcome.py:580` 一带（terminal）；`src/runtime/workflow/runtime_repair.py` 修复投影。
  - 带 proof 门禁的 `transition_from_runtime`：`src/runtime/task/task_commands.py:372-411`（要求 `SUCCEEDED` 必须有 `proof_ref`）。
  - 全仓 `rg transition_from_runtime`：**仅定义处命中**，无 runtime 调用方。
  - 实际 terminal 投影走 `_project_root_task_tx`：`src/runtime/workflow/runtime_outcome.py:562-587`，且 root-only：`571-572`。
- **为什么重要**：
  - D01-E04 / S02 期望可审计的统一转移；多写点提高未来边规则漂移风险。
  - 死路径携带更严的 cancelling→succeeded 规则（`task_commands.py:392-393` 返回 False），与 live `_project_root_task_tx` 行为可能不一致。
- **审查判断**：
  - 当前 **功能可工作**；协议收敛 **未完成**。不构成“worker 乱写 Task”的 P0。
- **建议修法**：
  - 选项 A：runtime terminal/running 投影改调 `transition_from_runtime`（或共享 helper）。
  - 选项 B：删除/降级未使用 API，并在 `_project_root_task_tx` 文档化唯一投影契约。
  - 对齐 cancelling 与 success 竞态规则（明确 S02 success-wins 或 fail-closed）。

### R3. Generation 公开 counts 的 cancelled 轴混用 process 计数

- **严重级别**：`low`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/task/task_views.py:225-230`：`total/active/succeeded/failed` 来自 **child** 计数字段，`cancelled` 来自 `cancelled_process_count`。
  - `001_initial.sql` executions 子计数列族为 total/active/succeeded/failed child（无对称的 `cancelled_child_count` 命名证据见 schema 审计）。
- **为什么重要**：
  - 对外 generation 投影可能误导 scatter 取消语义（Process cancelled 数 ≠ child Execution cancelled 数）。
- **审查判断**：
  - **投影语义漂移**，非控制状态机错误。
- **建议修法**：
  - 增加 `cancelled_child_count` 并由 scatter 刷新；或把 public 字段改名为 `cancelled_processes` 并文档化。
  - 补 unit 断言 generation counts 轴一致。

### R4. idle Process cancel 直转 `cancelled`

- **严重级别**：`low`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/workflow/runtime_outcome.py:673-677`：`status IN ('ready','retry_wait')` → 直接 `cancelled`。
  - 同函数 `679-683`：`claimed`/`running` → `cancelling` + fence++。
  - D01/S03 叙述通常期望 idle 也可经 cancelling 再 cancelled（字面边表）。
- **为什么重要**：
  - 观测/审计若假设“必经 cancelling”，会漏事件；对无 lease 的 idle Process 直 cancelled **语义安全**。
- **审查判断**：
  - 可接受的实现捷径；与字面边表 **PARTIAL**。
- **建议修法**：
  - 在 S03/D01 实现注记中显式允许 idle 短路；或改为 `cancelling` 并在同一 TX 立即 converge。

### R5. Process 缺 root 冗余列；软指针无 FK

- **严重级别**：`low`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `mkb_processes` 列为 `process_uuid, team_uuid, execution_uuid, task_uuid, ...`，**无** `root_execution_uuid`（`001_initial.sql:301-310`）。
  - `mkb_tasks.current_root_execution_uuid` 存在（`001_initial.sql:156`）但无指向 executions 的 FOREIGN KEY。
  - D01 §5.5 将 Process 上 `root_execution_uuid` 列为最小责任列族之一。
- **为什么重要**：
  - 运维按 root 查 Process 需 join；软指针在手工 DB 操作下可悬空。
- **审查判断**：
  - **列族 PARTIAL**，不破坏 1:N 基数与运行正确性（正常写路径由应用维护）。
- **建议修法**：
  - materialize 时写入 denorm `root_execution_uuid`（可空迁移）；cleanup TX 强制清空 `current_process_uuid`；可选 deferred FK。

### R6. Cancel 全树收敛与竞态测试偏弱

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - Cancel 实现完整：`task_commands.py:184-198`；树取消 `runtime_outcome.py:640-734`。
  - `claim_next` 在 Task `cancelling` 时不再 claim（`runtime_core.py:173`）。
  - 命名 suite 中缺少“多 child + 进行中 claim + cancel → 全部 fence 后 Task cancelled”的专用 e2e 断言（静态审查未找到对称于 scatter success 的 cancel 全树测试强度）。
- **为什么重要**：
  - D01-T030 多层事实依赖异步 outbox；缺测试时回归难以及早发现。
- **审查判断**：
  - 实现 **看起来正确**；证据链 **测试偏弱**。
- **建议修法**：
  - 增加 e2e：scatter 运行中 cancel → Task `cancelling` → 最终 `cancelled`，子 Process 无残留 lease。
  - 可选：success 与 cancel 竞态单测（固定 S02 规则）。

### R7. Cleanup 仅 eligibility 标记

- **严重级别**：`low`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `runtime_repair.py:300-302`：`UPDATE ... cleanup_eligible_at=?, cleanup_fence_digest=?`。
  - 无 `DELETE FROM mkb_processes` 的 cleanup 业务路径（D01-E07 允许先 fence 再 archive/delete）。
- **为什么重要**：
  - T031 要求 eligibility 后再清理；物理清理归 S12/S15 分阶段合理。
- **审查判断**：
  - **符合 D01 分阶段**；不可标为“违反 cleanup 真相”。
- **建议修法**：
  - 在 S12/S15 实现中消费 `cleanup_eligible_at` 做物理删除/归档，并保留 Execution 摘要与 events。

---

## 3. In-Scope 逐项对齐审核

> 如果存在 action-plan / design doc / closure claim，就必须有这一节。
> 结论统一使用：`done | partial | missing | stale | out-of-scope-by-design`。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | D01-T001–T007 三层切分与 Task/Workflow 分离 | `done` | 独立模块/表/枚举；`request_intent` 非 process 分类（`task_views.py:66`；`process_key` 在 `001_initial.sql:308`） |
| S2 | D01-T008–T014 身份、1:N、root/parent/retry、process 单属 Execution | `done` | FK 与 CHECK：`001_initial.sql:231-233,289-298,362-365`；retry 新 root：`task_commands.py:239-286` |
| S3 | D01-T016–T021 状态所有权与自下而上归约 | `partial` | 枚举对齐；归约成立（`runtime_outcome.py:571-572,546`）；Task 写点分散见 R2 |
| S4 | D01-T022–T025 / T023 exact process keys | `done` | `core.py:256-259`；无生产 `vectorize_index`；success 要 proof：`runtime_outcome.py:500-505` |
| S5 | D01-T026 / E06 scatter fan-out/fan-in | `done` | child `required` + parent/root：`scatter_intake.py:566-572`；fan-in 用 accepted set：`runtime_scatter.py` expected members |
| S6 | D01-T027–T028 / E05 三层 retry | `partial` | 引擎 retry_wait 与 manual new execution 齐；intake 错误分类见 R1 |
| S7 | D01-T030 cancel 多层事实 | `done` | Task cancelling：`task_commands.py:184`；claim 门：`runtime_core.py:173`；树取消：`runtime_outcome.py:640+` |
| S8 | D01-T031 / E07 cleanup eligibility | `partial` | 标记路径存在：`runtime_repair.py:300-302`；物理删除未做（R7，分阶段可接受） |
| S9 | D01-T036 queue 非 SSOT | `done` | claim 扫 Process：`runtime_core.py:150-173`；worker 不直写 Task |
| S10 | D01-T038 / §5.1 `task_restarts` | `done` | 表：`001_initial.sql:198`；full retry 写入：`task_commands.py:247+` |
| S11 | D01-T040–T043 preflight Process + HITL waiting gate | `done` | preflight 在 dispatch：`core.py:254`；HITL 为 CONTROL + Execution waiting（gate 路径与 e2e 存在） |
| S12 | D01 §5 三表 + 禁止平行控制表 | `done` | 三表存在；禁止表未创建；`003` 修 scatter root 唯一 |
| S13 | D01 §5.3–5.5 最小列族完整度 | `partial` | 主体齐；Process root 冗余缺失、软指针无 FK（R5） |
| S14 | D01 §1.6 完成定义 1–10 | `partial` | 1–5,8–9 强；6/7/10 因 R1/R7/测试缺口略弱 |
| S15 | 公开 API 不要求 caller 持有 execution/process 作为主身份 | `done` | `_view` 无 execution/process uuid：`task_views.py:61-93` |

### 3.1 对齐结论

- **done**: `10`
- **partial**: `5`
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像 **“D01 控制骨架与 durable 路径已闭环，retry 分类与投影/schema 硬度仍有 follow-up”**，而不是“未实现三层模型”。

---

## 4. Out-of-Scope 核查

> 本节用于检查实现是否越界，也用于确认 reviewer 是否把已冻结的 deferred 项误判为 blocker。

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | D01 不冻结完整 Task HTTP enum 细节（交 S02） | `遵守` | 本审查只核对六态与投影边界，不要求 S02 全文 HTTP 矩阵 |
| O2 | D01 不冻结完整 claim/backoff 算法细节（交 S03） | `遵守` | 已实现 fencing/lease/retry_wait；细 backoff 属 S03 |
| O3 | Process 物理删除 / 长期 retention（交 S12/S15） | `遵守` | 仅 eligibility 标记（R7）；未误判为 D01 blocker |
| O4 | Intake/vector 完整资产 DDL（交 S04/S08/S09） | `遵守` | 只查 publication proof 作为成功围栏，不要求向量业务全文 |
| O5 | 将 generation artifact 当作第四运行身份 | `遵守` | generation 表为派生事实；控制状态仍三层 |
| O6 | 用 live GPU 证明 D01 | `误报风险` | D01 为身份/控制真相，非推理平面；不得要求 live endpoint |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`approve-with-followups` — D01 三层运行模型与 durable 主路径已在代码/schema 对齐；无 critical 结构性违规；R1–R7 为 follow-up。
- **是否允许关闭本轮 review**：`yes`
- **关闭前必须完成的 blocker**：
  1. （无）本轮 **无 critical/high blocker**；不阻塞关闭 D01 对齐 review。
- **可以后续跟进的 non-blocking follow-up**：
  1. R1：intake 瞬时错误 → `retryable_failure` + 单测。
  2. R2：收敛 Task 投影写路径 / 处理 `transition_from_runtime` 死代码。
  3. R3–R6：generation counts、cancel 边文档或实现、软指针/root 冗余、cancel e2e。
  4. R7：S12/S15 消费 cleanup eligibility。
- **建议的二次审查方式**：`same reviewer rereview`（若实现 R1/R2）；纯文档跟进则 `no rereview needed`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 D01 对齐 review **可以收口为 approve-with-followups**。若实现者承诺处理 R1/R2，建议在修复后 append §6 并请求 rereview。

---

## 6. 实现者回应区

> （空。实现者按 `docs/templates/code-review-respond.md` / `.adocs/code-review-respond.md` 在此 append，勿改写 §0–§5。）
