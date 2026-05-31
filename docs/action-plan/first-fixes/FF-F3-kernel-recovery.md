# Nano-Agent 行动计划 — FF-F3 内核恢复与一次性语义

> 服务业务簇: `workflow_core 内核（task_claims / leases / retry / restart / purge / events / graph）`
> 计划对象: `F3 · 内核恢复与一次性语义（lease reap 接线 + 终态归属内核 + 执行器契约 + restart recovery + 副作用幂等）`
> 类型: `refactor`（含 `add` 新契约模块 / `remove` 死代码事件写入器）
> 作者: `Opus 4.8（first-fixes 派生 AP）`
> 时间: `2026-05-31`
> 文件位置:
> - `packages/workflow_core/src/workflow_core/{leases,retry,restart,events,graph,_utils,__init__}.py`
> - `packages/workflow_core/src/workflow_core/executor_contract.py`（新建）
> - `apps/worker/src/smind_worker/main.py`
> - `packages/workflow_clean/src/workflow_clean/service.py`、`packages/workflow_rag/src/workflow_rag/service.py`
> - `tests/integration/p1_kernel_closure/`、`tests/unit/`、`tests/fixtures/`
> 上游前序 / closure:
> - `FF-F1-time-tx-base.md`（**keystone，必须先 keystone**）—— F1-02/03 修 `now_iso` 缺 `%S` 根因（reap/restart 时间比较前提）；**F1-04 autocommit + 多写 helper 包 `BEGIN IMMEDIATE...COMMIT`**，与本 AP F3-02 的多写事务重构**同窗口推进**（共享同一批 `workflow_core` 多写函数）。
> 下游交接:
> - `FF-F6a-cleaners.md` / `FF-F6b-rag-executors.md`（执行器契约 `execute(step,deps)->ExecutorResult` 的**全部真实执行器消费方**，建造基准在本 AP F3-02 交付）
> - `FF-F6c-auth-config.md`（间接：`prompt_versions`/`provider_configs` 接线在 F6，本 AP 仅处理 `workflow_step_links`）
> 关联设计 / 调研文档:
> - `docs/design/first-fixes/initial-planning-by-opus.md`（§6.3 F3 台账、§2.B/§2.C、§4 红线第 2/3 条、§5 DAG 强耦合、§8 capstone D 步、DoD）
> - `docs/eval/first-code-review-plan/part-cr-4.md`（G-CR4-01~13，全部含 file:line 实测）、`part-cr-6.md`（G-CR6-03 clean 侧自提交）、`part-cr-7.md`（G-CR7-06 rag 侧自提交）、`part-cr-8.md`（G-CR8-02 夹具掩盖教训）
> - `docs/refactor/core.sql`（`v_ready_steps`/`v_stale_claims`/`workflow_step_links`/`retry_backoff_seconds`/`workflow_events`）
> 冻结决策来源:
> - `docs/design/first-fixes/owner-gated-qna.md`（[Q4] restart recovery、[Q7] test-first；只读引用，本 AP 不开 Q/A）
> grounding 来源:
> - `eval-reference-anchor` = `part-cr-4.md`（CR 报告已预完成 reference-anchor，每 blocker 带 file:line + legacy 对照 + 实测）；§7 内置锚区据此摘录。
> 关联 reference-anchor:
> - `docs/eval/first-code-review-plan/part-cr-4.md`（真源）；本 AP §7.1 为其与 F3 相关子集摘录。
> 文档状态: `draft`

---

## 0. 执行背景与目标

> CR-4 的总判断是「内核是全系统状态中心，但其 lease 恢复机制是死代码、时间比较被畸形格式打穿、执行器与 claim 终态职责撕裂导致双重执行、restart 路径非确定性失效——内核当前不具备生产可用的可靠性」。F1 已拔掉时间/事务单点根因（`now_iso` 缺 `%S` + autocommit 事务模式），但根因修复本身**不会自动让内核恢复可靠**：reap 仍是死代码（没接线）、终态写入仍在执行器里自提交（双重执行）、restart 仍硬编码从 clean 头重跑。F3 在 F1 稳固的时间/事务基座上，把内核的三大可靠性支柱（**故障恢复 / 一次性语义 / 可恢复重启**）补齐到可证明正确。

> 本 AP 的承重项是 **F3-02 终态归属内核 + 执行器契约**：它把「step 终态 / 下游派生 / run 推进 / commit」从 clean/rag 执行器收归 `succeed_claim`/`fail_claim`，并定义 `execute(step, deps) -> ExecutorResult` 接口——**此契约是 F6 全部真实执行器的建造基准**，若不先立，F6 会逐个复刻 G-CR4-03 的职责撕裂。F3-02 的多写事务重构与 F1-04 的「多写 helper 包 BEGIN IMMEDIATE」触碰**同一批** `workflow_core` 函数，故二者须同窗口推进。

- **服务业务簇**：`workflow_core 内核 + 其执行器调用面（worker / clean / rag）`
- **计划对象**：`F3 · 内核恢复与一次性语义`
- **本次计划解决的问题**：
  - `reap_expired_claims` 全仓零运行时调用（G-CR4-01）：worker 崩溃后 claim 永久 `active`、step 永久卡 `running`，被 `ux_task_claims_active_step` 唯一索引死锁，无人工干预不可恢复。
  - 执行器自提交终态 + main 忽略返回值 + 副作用无幂等键（G-CR4-03 / G-CR6-03 / G-CR7-06）：过期租约竞态下 artifact/chunk/向量/下游 step 重复落盘，at-most-once 被破坏且静默无观测。
  - restart 写畸形 `available_at`（G-CR4-04）：被重启 step 约 40% 概率本分钟内永不就绪，restart 静默失效。
  - restart 无条件从 clean 头重跑、`mode` 死参（G-CR4-05）：rag 阶段失败的 workflow 被整段重跑（浪费 + 可能违反幂等）。
  - 就近债：retry 退避恒 1s（schema `retry_backoff_seconds=60` 从不读，G-CR4-07）、error_code 恒 `EXECUTOR_FAILURE`（G-CR4-08）、重复事件写入器 `graph.write_workflow_event` 死代码（G-CR4-09）、`workflow_step_links` DAG 边表零写入（G-CR2-03 余项）。
- **本次计划的直接产出**：
  - `_run_once` 接线 `reap_expired_claims`，worker 崩溃后 lease 故障可自动回收。
  - `executor_contract.py`：`ExecutorResult` + `execute(step, deps) -> ExecutorResult` 协议；clean/rag 执行器改为只产结果、不写终态/不 commit；`succeed_claim`/`fail_claim` 在确认 claim 仍 active 的同一显式事务内统一落库（含幂等键的下游派生 + 副作用）。
  - restart `available_at` 改 SQL strftime（局部双保险）+ recovery 模式（按 run `current_stage`/失败 step 锚点）。
  - retry 指数退避读 schema 列 + 错误分类透传；删 `graph.write_workflow_event` 死代码统一 `events.append_workflow_event` 并去显式 `created_at`；`workflow_step_links` 接线或显式延后记理由。
  - 先红后绿并发 harness：claim→强制过期→reap→第二 worker 执行→断言 artifact/chunk **无重复**。
- **本计划不重新讨论的设计结论**：
  - `restart 本轮做 recovery 模式（按 current_stage/失败 step 锚点）；force/kickstart 延后；前置必修 F3-04 available_at`（来源：`[Q4]`）。
  - `全 phase 先红后绿铁律；F7 前禁止新增「手写正确数据绕过被测路径」的夹具；CI 加断言强度门禁`（来源：`[Q7]`）。
  - `执行器只产出结果、不写终态、不 commit；终态写入单一归属内核`（来源：planning §4 红线第 2 条，本 AP 落地）。

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用 **「先协议后实现、先底层后上层」** 的执行方式，分 4 个 Phase：先在 F1 稳固的时间/事务基座上接线 reap 并修 restart 时间根因（Phase 1，低风险快赢，验证 F1 修复确实让 reap/restart 命中）；再做承重的终态归属重构 + 执行器契约定义（Phase 2，**与 F1-04 多写 helper 包 BEGIN 同窗口**）；然后做 restart recovery 模式（Phase 3，依赖 Phase 1 的 available_at 修复）；最后做就近捆绑的可靠性债 + 死代码清理 + 并发回归 harness（Phase 4）。每个 Phase 的退出判据是「先红后绿」的有意义测试，而非 `status==200`。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | reap 接线 + restart 时间修复 | S | 接线 `reap_expired_claims`（G-CR4-01）+ restart `available_at` 改 SQL strftime（G-CR4-04），验证 F1 时间修复让 reap/restart 真命中 | F1（F1-02/03 时间根因）|
| Phase 2 | 终态归属内核 + 执行器契约 | **L** | 定义 `execute(step,deps)->ExecutorResult` 契约；终态/下游/run/commit 收归内核；副作用幂等键；main 检查返回值（G-CR4-03/G-CR6-03/G-CR7-06）| F1-04（同窗口）；Phase 1 |
| Phase 3 | restart recovery 模式 | M | 按 run `current_stage`/失败 step 锚点重启（[Q4]），`mode` 不再死参 | Phase 1（F3-04 available_at 必修前置）|
| Phase 4 | 可靠性债收口 + 并发回归 | M | retry 退避/错误分类（G-CR4-07/08）、删重复事件写入器（G-CR4-09）、`workflow_step_links`（G-CR2-03）、并发双重执行回归 harness | Phase 2 |

> 说明：上表 `规模` 是描述性提示，非开工前体量判定闸；不改变本模板任何段落取舍。

### 1.3 Phase 说明

1. **Phase 1 — reap 接线 + restart 时间修复**
   - **核心目标**：让 F1 修好的时间格式在内核「真正命中」——reap 从死代码变为 worker 每轮调用、restart 写出的 `available_at` 确定性就绪。
   - **为什么先做**：低风险、快赢，且**先验证 F1 的时间修复确实生效**（CR-4 断点 D：reap 接线前必须先有正确时间格式，否则接线后仍 0 命中）。在动承重的 F3-02 之前先把「能恢复」这条最基础的可靠性立起来。
2. **Phase 2 — 终态归属内核 + 执行器契约**
   - **核心目标**：消除执行器与 claim 函数的终态职责撕裂（双重执行 critical 根因）；定义并交付 `ExecutorResult` 契约作为 F6 全部真实执行器的建造基准。
   - **为什么放在这里**：这是本 AP 最承重、最高风险项，必须在 Phase 1 把「lease 能回收」立稳后再做（否则双重执行场景无法在测试里复现）；且其多写事务重构与 F1-04 触碰同一批函数，**同窗口推进避免两次触碰同组函数**。
3. **Phase 3 — restart recovery 模式**
   - **核心目标**：restart 按失败阶段锚点恢复，`mode` 参数生效（[Q4]=recovery 模式）。
   - **为什么放在这里**：[Q4] 明确「前置必修 F3-04 available_at」——必须先有 Phase 1 的 available_at 修复让 restart 真能生效，再谈精细粒度，否则任何 mode 都不就绪。
4. **Phase 4 — 可靠性债收口 + 并发回归**
   - **核心目标**：就近捆绑同主题 medium 债（退避/错误分类/死代码/边表），并交付并发双重执行回归 harness 作为本 AP 的退出硬闸。
   - **为什么放在这里**：这些债依赖 Phase 2 的终态归属落定（退避/错误分类透传走新契约的 error_code），且并发 harness 要在终态归属修好后才能断言「无重复」转绿。

### 1.4 执行策略说明

- **执行顺序原则**：先底层后上层（reap/restart 时间 → 终态契约 → recovery → 债）；F3-02 与 F1-04 同窗口推进，避免两次重构同一批多写函数。
- **风险控制原则**：承重项 F3-02 拆有序子步，每子步配独立先红后绿测试；改执行器↔内核边界前先冻结契约接口（`executor_contract.py`），clean/rag 同步迁移，main 检查返回值，禁止「执行器自行 commit 终态」残留。
- **测试推进原则**：短途（unit：时间比较/退避/契约边界）→ spike（integration：reap 命中、restart recovery、并发双重执行）→ 并入 capstone D 步（详见 §8）；**reap 测试走真实 `now_iso` 写入路径**（极小 lease_seconds + 冻结时钟），禁止手写 SQL 覆盖 lease（吸取 G-CR8-02 夹具掩盖教训）。
- **文档同步原则**：closure 在 F7 前冻结不得标 ✅；`workflow_step_links` 若延后须在本 AP §2.3 + §9.3 显式记理由。
- **回滚 / 降级原则**：F3-02 若 F6 消费方未就绪，契约接口可先落地、clean/rag 执行器分两批迁移；`workflow_step_links` 可显式延后（degraded 声明）；restart recovery 若锚点定位失败回退到 stage 级重启（不回退到 clean 全量，因 clean 全量已被 recovery 取代）。

### 1.5 本次 action-plan 影响结构图

```text
F3 内核恢复与一次性语义
├── Phase 1: reap 接线 + restart 时间修复
│   ├── apps/worker/.../main.py:_run_once（接线 reap_expired_claims）
│   └── workflow_core/restart.py:79,88（available_at 改 SQL strftime）
├── Phase 2: 终态归属内核 + 执行器契约【承重】
│   ├── workflow_core/executor_contract.py（🆕 ExecutorResult + execute 协议）
│   ├── workflow_core/retry.py:succeed_claim/fail_claim（统一落库 + 幂等派生）
│   ├── workflow_clean/service.py:process_clean_step（去自提交，只产结果）
│   ├── workflow_rag/service.py:process_rag_step（去自提交，只产结果）
│   └── apps/worker/.../main.py（执行器返回 ExecutorResult；检查 succeed/fail 返回值）
├── Phase 3: restart recovery 模式
│   └── workflow_core/restart.py:process_restart_requests（按 current_stage/失败 step 锚点）
└── Phase 4: 可靠性债收口 + 并发回归
    ├── workflow_core/retry.py（退避读 schema 列 + 指数；error_code 透传）
    ├── workflow_core/{graph,events,__init__}.py（删 graph.write_workflow_event；去显式 created_at）
    ├── workflow_core/graph.py（workflow_step_links 接线 或 显式延后）
    └── tests/integration/p1_kernel_closure/（并发双重执行 harness）
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** F3-01 worker `_run_once` 接线 `reap_expired_claims`（restart/purge 后、claim 前）。
- **[S2]** F3-02 定义执行器契约 `execute(step,deps)->ExecutorResult` + 终态/下游/run/commit 归内核 `succeed_claim`/`fail_claim`（同一显式事务，确认 claim active）。
- **[S3]** F3-03 副作用幂等键（artifact/下游 step 用确定性 key 非 `uuid4`）；main 检查 `succeed_claim`/`fail_claim` 返回值。
- **[S4]** F3-04 restart `available_at` 改 SQL strftime（局部双保险）。
- **[S5]** F3-05 restart recovery 模式（按 `current_stage`/失败 step 锚点）；`mode` 生效。
- **[S6]** F3-06 retry 退避读 schema `retry_backoff_seconds` + 指数（G-CR4-07）、错误分类透传（G-CR4-08）。
- **[S7]** F3-07 删 `graph.write_workflow_event` 死代码，统一 `events.append_workflow_event` 去显式 `created_at`（G-CR4-09）。
- **[S8]** F3-08 `workflow_step_links` 接线 **或** 显式延后并记理由（G-CR2-03 余项）。
- **[S9]** F3-09 并发 harness：claim→强制过期→reap→第二 worker→断言 artifact/chunk 无重复（先红后绿）。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** restart `force`/`kickstart` 全量重启面（[Q4] 明确延后；本轮仅 recovery）。
- **[O2]** clean/rag 执行器的**真实业务能力去桩**（htmlCrawl/structurize/construct 真实算法）—— 归 F6；本 AP 只改执行器↔内核的**职责边界与契约**，不改业务算法。
- **[O3]** R6 二次 restart PK 冲突可重入（`request_id` 随机化/ON CONFLICT，G-CR4-R6）—— non-blocker，归 management/requests，本 AP 不含（restart recovery 不引入新 PK 冲突即可）。
- **[O4]** R11 `step_attempts` id 改 `(step_id, attempt_number)`、R12 per-request 事务、R13 失败/中间态补 event —— non-blocker followup，延后。
- **[O5]** `prompt_versions`/`provider_configs` 两张零访问表接线（G-CR2-03 的另两项）—— 归 F6c（F6 真实 cleaner/structurizer 配置载体）。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 终态归属 + 执行器契约（F3-02）| `in-scope` | 双重执行 critical 根因；F6 全部真实执行器的建造基准必须先立 | — |
| 执行器真实业务算法去桩 | `out-of-scope` | 属 F6 能力补全；本 AP 只动职责边界 | F6 启动 |
| restart recovery（F3-05）| `in-scope` | [Q4] 裁决本轮做 recovery 模式 | — |
| restart force/kickstart | `defer / depends-on-design` | [Q4] 明确延后 | 产品需要全量重启场景 |
| `workflow_step_links` 接线（F3-08）| `in-scope（接线 or 显式延后）` | G-CR2-03 余项；当前 graph 只写 events 不写 links，DAG 边不可达 | 若本 AP 无下游消费 links 的读路径，则显式延后并在 §9.3 记理由 |
| 二次 restart 可重入（R6）| `out-of-scope` | non-blocker；recovery 复用同一 step（ON CONFLICT 已存在）不必引入随机 request_id | management 面统一修窗口 |

---

## 3. 业务工作总表

> 编号沿用 final plan §6.3 的 `F3-NN`（跨态稳定）。三元组（涉及文件 / 收口目标 / 测试映射）齐全；承重/高风险项 F3-02/F3-03/F3-05/F3-09 的 `工作内容` 在 §4 拆有序子步。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID）| 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| F3-01 | Phase 1 | worker `_run_once` 接线 `reap_expired_claims` | update | `apps/worker/src/smind_worker/main.py:35-37`（`_run_once` restart/purge 后、claim 前）| worker 每轮调 reap；崩溃 step 的 active claim 被回收、step 退回 retry_wait/failed | `FF-F3-T01` `FF-F3-T02` | low |
| F3-04 | Phase 1 | restart `available_at` 改 SQL strftime | update | `workflow_core/restart.py:79,88`（ON CONFLICT `available_at=?` 绑定畸形 `now_iso()`）| restart 写出的 `available_at` 与 `v_ready_steps`（core.sql:535）同源，被重启 step 确定性就绪 | `FF-F3-T03` | low |
| F3-02 | Phase 2 | 终态归属内核 + 定义执行器契约 `execute(step,deps)->ExecutorResult` | add + refactor | `workflow_core/executor_contract.py`（🆕）；`workflow_core/retry.py:7-65`（succeed_claim）`:68-168`（fail_claim）；`workflow_clean/service.py:67-129`（去自提交）；`workflow_rag/service.py:35-233`（去自提交）；`apps/worker/.../main.py:46-57` | 执行器只产 `ExecutorResult`、不写 step 终态/下游/run、不 commit；终态+派生+推进+commit 仅由 succeed/fail 在确认 claim active 的同一显式事务内完成 | `FF-F3-T04` `FF-F3-T05` `FF-F3-T06` | **high** |
| F3-03 | Phase 2 | 副作用幂等键 + main 检查返回值 | refactor | `workflow_clean/service.py:83,109,113`（uuid4 artifact/step_key）；`workflow_rag/service.py:55,95,106-108`（uuid4 chunk/artifact）；`apps/worker/.../main.py:53,56` | artifact/下游 step/chunk 用确定性 key（如 `rag-struct:{clean_step_id}`、`chunk:{document_id}:{chunk_index}`）；INSERT ON CONFLICT DO NOTHING；main 对 succeed/fail 返回 False 告警 | `FF-F3-T07` `FF-F3-T08` | medium |
| F3-05 | Phase 3 | restart recovery 模式（按 current_stage/失败 step 锚点）| refactor | `workflow_core/restart.py:29-139`（无条件 clean:init 重置 + mode 死参）| recovery 按 run `current_stage`/最后失败 step 决定重启锚点；`mode` 不再仅写 audit | `FF-F3-T09` `FF-F3-T10` | medium |
| F3-06 | Phase 4 | retry 指数退避读 schema 列 + 错误分类透传 | update | `workflow_core/retry.py:74`（`retry_backoff_seconds=1` 默认）`:88-118`（fail_claim）；`workflow_core/leases.py:76`（reap 退避 0s）；`apps/worker/.../main.py:56` | fail_claim 从 `ws.retry_backoff_seconds`（core.sql:270 DEFAULT 60）读 + `backoff*2^(attempt-1)`；执行器领域异常带 error_code，main 透传 | `FF-F3-T11` | low |
| F3-07 | Phase 4 | 删重复事件写入器 + 去显式 created_at | remove + update | `workflow_core/graph.py:9-35`（死代码 `write_workflow_event`）；`workflow_core/__init__.py:2,6,16`（导出）；`workflow_core/events.py:24,34`（显式 `created_at=now_iso()`）；`audit_logs` 同处 `:55,66` | 删 graph.py 的死代码写入器；events 去掉 8 列里的显式 `created_at`，交 DDL DEFAULT（core.sql:343）| `FF-F3-T12` | low |
| F3-08 | Phase 4 | `workflow_step_links` DAG 边表接线 或 显式延后 | add / defer | `workflow_core/graph.py`；`docs/refactor/core.sql:321-332`（表 + UNIQUE）| 创建下游 step 时写 from→to `next` 边 **或** 显式延后并在 §9.3 记理由（当前 graph 只写 events 不写 links）| `FF-F3-T13` | medium |
| F3-09 | Phase 4 | 并发双重执行回归 harness | add（test）| `tests/integration/p1_kernel_closure/test_kernel_recovery.py`（🆕）；`tests/fixtures/`（并发原语）| claim→真实 now_iso 写 lease→强制过期→reap→第二 worker 执行→断言 artifact/chunk 无重复 | `FF-F3-T14` | medium |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — reap 接线 + restart 时间修复

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line）| 预期结果 | 测试映射（Test-ID）| 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F3-01 | 接线 reap | 在 `_run_once` 开头（`process_restart_requests`/`process_purge_requests` 之后、`scheduler.claim_one()` 之前）插入 `reap_expired_claims(core_conn)`；reap 返回回收数，>0 时 logger.info 记录。**依赖 F1：** 必须 F1-02/03 修好 `now_iso` 缺 `%S` 后才命中（CR-4 断点 D：reap 接线前比较仍 0 命中）。| `apps/worker/.../main.py:35-37`（`_run_once` 体）| worker 每轮回收过期 claim；崩溃后 step 退 retry_wait（可重 claim）或 failed（超 max_attempts）| `FF-F3-T01` `FF-F3-T02` | reap 在 worker 运行路径被调用（非仅测试孤立调用）；过期 claim 被回收且 step 可被第二 worker reclaim |
| F3-04 | restart available_at SQL 化 | restart ON CONFLICT 的 `available_at` 与 fresh/retry step 同源——直接用 SQL `strftime('%Y-%m-%dT%H:%M:%fZ','now')` 而非 Python `now_iso()`（即便 F1 已修根因，此处做局部双保险，与 `v_ready_steps`（core.sql:535）比较表达式同源）| `workflow_core/restart.py:79,88`（`available_at=?` 绑定 `updated_at=now_iso()`）| 被重启 step 的 `available_at` 确定性 `<= now`，本分钟内即就绪，restart 不再约 40% 概率静默失效 | `FF-F3-T03` | 重启 step 在 restart 后立即出现在 `v_ready_steps` 并可被 claim |

### 4.2 Phase 2 — 终态归属内核 + 执行器契约【承重】

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line）| 预期结果 | 测试映射（Test-ID）| 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F3-02 | 终态归属 + 执行器契约 | **有序子步（净新高风险）：** **a)** 在 `executor_contract.py` 定义 `ExecutorResult`（dataclass：`artifacts: list[ArtifactSpec]`、`downstream: list[DownstreamStepSpec]`、`run_advance: RunAdvanceSpec \| None`、`error_code: str \| None`）+ 协议 `execute(step: Row, deps: ExecutorDeps) -> ExecutorResult`（`deps` 封 object_store/vec_conn/app_env，**不含可写 core_conn 的终态权限**）。**b)** clean 执行器（`workflow_clean/service.py:67-129`）改造：保留 `_load_raw_payload` + clean 算法，**删除** `:117-120`（UPDATE step succeeded）`:121-128`（UPDATE run）`:129`（commit）`:101-116`（自插下游 rag step），改为返回 `ExecutorResult(artifacts=[cleaned_text], downstream=[rag:structurize], run_advance=(running,rag))`。**c)** rag 执行器（`workflow_rag/service.py:35-233`）同构改造：删 `:223-233`（UPDATE step succeeded + commit）`:209-219`（run completed）`:82-98`（自插下游 construct step），改为返回 `ExecutorResult`；construct 分支的 vec 跨库写入按五步序保留在执行器内（vec 是 vec_conn，不属 core 终态），但 **core 侧 chunk 行的终态/run 推进交内核**。**d)** `succeed_claim`（`retry.py:7-65`）扩参 `result: ExecutorResult`：在确认 claim active 的同一显式事务内（与 F1-04 BEGIN IMMEDIATE 同窗口）顺序落：写 result.artifacts → 写 result.downstream（幂等，见 F3-03）→ UPDATE step succeeded → UPDATE run（result.run_advance）→ 记 step_attempt → append_workflow_event → 末 commit。**e)** worker（`main.py:46-57`）改为：`result = process_clean_step(...)` / `process_rag_step(...)` 返回 `ExecutorResult`，再 `ok = succeed_claim(core_conn, token, result=result)`。**f)** 边界/失败路径：执行器抛异常时**不得有任何 core 副作用残留**（无自 commit）；fail_claim 路径不写 result。**g)** 降级：F6 消费方未就绪时，契约接口先落地、clean/rag 分两批迁移（先 clean 后 rag），但**禁止保留任一执行器的自 commit**。| `workflow_core/executor_contract.py`（🆕）；`workflow_core/retry.py:7-65`；`workflow_clean/service.py:67-129`；`workflow_rag/service.py:35-233`；`apps/worker/.../main.py:46-57` | 执行器无 core 终态写入与 commit；终态单一归属内核；契约为 F6 建造基准 | `FF-F3-T04` `FF-F3-T05` `FF-F3-T06` | grep 确认 clean/rag service 内无 `status='succeeded'`/`conn.commit()`/`CURRENT_TIMESTAMP`（core 侧）残留；succeed_claim 单事务落全部副作用；契约接口被 worker 消费 |
| F3-03 | 幂等键 + 检查返回值 | **有序子步：** **a)** 下游 step 的 `step_key` 由确定性派生（clean→`rag-struct:{clean_step_id}`，struct→`rag-construct:{struct_step_id}`），替换 `f"rag-struct-{uuid4().hex}"`（service.py:113）。**b)** artifact id / chunk id 由 `(workflow_run_id, artifact_type, source_id[, chunk_index])` 确定性派生（替换 `str(uuid4())`，service.py:83,109 / rag:55,106-108）。**c)** 下游 step INSERT 改 `ON CONFLICT(workflow_run_id, step_key) DO NOTHING`；artifact/chunk INSERT 同样幂等（先查或 ON CONFLICT）。**d)** chunk vec upsert 用 `chunk_id` 幂等（配合 F4 rowid，本 AP 仅保证 core 侧 key 确定性）。**e)** main：`ok = succeed_claim(...)`/`fail_claim(...)`，`if not ok: logger.warning("claim no longer active,副作用已由内核幂等保护")`（main.py:53,56）。| `workflow_clean/service.py:83,109,113`；`workflow_rag/service.py:55,95,106-108`；`apps/worker/.../main.py:53,56` | 重放安全：同一 step 重复执行不产生重复 artifact/step/chunk；main 不再静默忽略 False | `FF-F3-T07` `FF-F3-T08` | 重复调用 succeed_claim/重复执行器：artifact/下游 step/chunk 计数不增；False 返回被 main 观测 |

### 4.3 Phase 3 — restart recovery 模式

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line）| 预期结果 | 测试映射（Test-ID）| 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F3-05 | restart recovery | **有序子步（[Q4] recovery）：** **a)** 读 run 当前状态：`current_stage` + 查该 run 最后失败 step（`status='failed'` ORDER BY updated_at DESC）。**b)** mode 分流：`mode='recovery'`（默认）→ 锚点 = 失败 step 所属 stage（无失败 step 则用 current_stage）；不再无条件 `clean:init`。**c)** 按锚点重置：把锚点 stage 的 step 置 `pending` + `available_at=SQL strftime`（复用 F3-04），run 置 `pending` + `current_stage=锚点 stage`（替换硬编码 `current_stage='clean'`，restart.py:95）。**d)** 边界：锚点定位失败（无 failed step 且 current_stage 异常）→ 回退 stage 级、记 warning（不回退 clean 全量）。**e)** 失败路径：run 不存在仍走 `:48-70` failed 分支。**f)** `mode` 写入 event/audit payload 之外**真实影响锚点**（消除死参，restart.py:125,135）。force/kickstart 入参本轮拒绝/标 degraded（[Q4] 延后）。| `workflow_core/restart.py:29-139`（`process_restart_requests`）| rag 阶段失败的 workflow 从 rag 锚点恢复，不重跑已成功的 clean | `FF-F3-T09` `FF-F3-T10` | restart 一个 rag 阶段失败的 run，clean step 不被重置、rag 锚点 step 就绪；`mode` 影响行为 |

### 4.4 Phase 4 — 可靠性债收口 + 并发回归

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line）| 预期结果 | 测试映射（Test-ID）| 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F3-06 | 退避 + 错误分类 | fail_claim 从 `ws.retry_backoff_seconds` 读（不再默认 1s）+ 指数 `backoff*2^(attempt_count-1)`；reap 退避同（leases.py:76 当前 `'now'`=0s）。执行器领域异常携 `error_code`，main `except` 透传到 fail_claim（不再恒 EXECUTOR_FAILURE）；据 error_code 决定 retryable。| `workflow_core/retry.py:74,88-118`；`workflow_core/leases.py:76`；`apps/worker/.../main.py:54-56` | 退避按 schema 列指数增长；错误分类透传 | `FF-F3-T11` | retry 退避值 = schema 列 × 指数；不可重试 error_code 不再无脑重试到上限 |
| F3-07 | 删重复事件写入器 | 删 `graph.py` 的 `write_workflow_event`（死代码，0 内部调用，self-commit 是 BEGIN IMMEDIATE 内的潜在地雷）；从 `__init__.py:2,6,16` 移除导出；统一用 `events.append_workflow_event`，并去掉其显式 `created_at=now_iso()`（events.py:24,34），交 DDL DEFAULT（core.sql:343 `strftime` 正确格式）；`audit_logs` 同处（events.py:55,66）。| `workflow_core/{graph,events,__init__}.py` | 单一事件写入器；event/audit `created_at` 走 DDL（消除该处时间 bug，与 F1 同源）| `FF-F3-T12` | grep 无 `graph.write_workflow_event` 调用；event created_at 为正确 SQL 格式 |
| F3-08 | workflow_step_links | **接线**：创建下游 step 时（succeed_claim 落 downstream）写 `workflow_step_links(from_step_id, to_step_id, link_type='next')`（core.sql:321-332，UNIQUE(from,to,type)）；**或显式延后**：若本 AP 无消费 links 的读路径，则在 §9.3 记理由 + degraded 声明（不留装成完成的桩）。| `workflow_core/graph.py`；`workflow_core/retry.py:succeed_claim`（downstream 落库处）| DAG 边可达（接线）或显式记账延后 | `FF-F3-T13` | 接线：每条 next 派生写一条 link；延后：§9.3 有理由 + 测试 xfail/skip |
| F3-09 | 并发双重执行 harness | **有序子步（先红后绿 race）：** **a)** fixture：建 run + clean step；worker-A `claim_next_step(lease_seconds=1)`（**真实 now_iso 写 lease，禁止手写 SQL 覆盖**——吸取 G-CR8-02 教训）。**b)** 冻结/推进时钟使 lease 过期（不手写 lease_expires_at）。**c)** 调 `reap_expired_claims` → step 退 retry_wait。**d)** worker-B `claim_next_step`（attempt 2）→ 执行器跑完 → succeed_claim。**e)** worker-A「迟到恢复」尝试 succeed_claim(token-A)：claim 已非 active → 返回 False（main 告警）。**f)** 断言：artifact 表该 run 的 cleaned_text 仅 1 条、下游 rag step 仅 1 条、chunk/向量无重复（确定性 key 保护）。**g)** 失败变体：worker-A 执行器中途崩溃（无自 commit）→ 无残留副作用。| `tests/integration/p1_kernel_closure/test_kernel_recovery.py`（🆕）；`tests/fixtures/`（冻结时钟 + 双 worker 原语）| 过期租约竞态下 at-most-once 成立 | `FF-F3-T14` | 修复前红（重复落盘）、修复后绿（计数=1）；走真实 now_iso 写入路径 |

---

## 5. Phase 详情

### 5.1 Phase 1 — reap 接线 + restart 时间修复

- **Phase 目标**：让 F1 的时间修复在内核真正命中——reap 从死代码到每轮调用、restart available_at 确定性就绪。
- **本 Phase 对应编号**：`F3-01` / `F3-04`
- **本 Phase 新增文件**：无
- **本 Phase 修改文件**：`apps/worker/.../main.py:35-37`、`workflow_core/restart.py:79,88`
- **具体功能预期**：
  1. `_run_once` 在 restart/purge 处理后、claim 前调用 `reap_expired_claims(core_conn)`；返回 >0 时 logger.info。
  2. reap 命中**依赖 F1**：F1-02/03 修好 `now_iso` 缺 `%S` 后，`task_claims.lease_expires_at`（claim.py:64 写）与 reap/`v_stale_claims` 的 SQL strftime 比较（leases.py:34 / core.sql:713）才一致；F1 未到位时此 Phase 测试应红。
  3. 过期 claim 被置 `expired`，step 退 `retry_wait`（attempt < max）或 `failed`（≥ max），可被第二 worker reclaim。
  4. restart 写出的 `available_at` 用 SQL strftime（与 v_ready_steps:535 同源），被重启 step 本分钟内即就绪，不再约 40% 概率静默失效。
  5. **边界**：reap 在无过期 claim 时返回 0、不报错；restart 对已存在的 `clean:init` step 走 ON CONFLICT 路径，available_at 仍正确。
- **对应测试台账项**：`FF-F3-T01` / `FF-F3-T02` / `FF-F3-T03`（详见 §8）
- **收口标准**：reap 在 worker 运行路径被调用且命中；restart 后 step 确定性就绪。
- **本 Phase 风险提醒**：CR-4 断点 D——reap 必须在 F1 时间修复后接线，否则比较 0 命中；本 Phase 测试必须验证「在 F1 修复后」才转绿（防 F1↔F3 耦合被掩盖）。

### 5.2 Phase 2 — 终态归属内核 + 执行器契约【承重】

- **Phase 目标**：消除执行器与 claim 的终态职责撕裂（双重执行 critical 根因）；定义 `ExecutorResult` 契约作为 F6 全部真实执行器的建造基准。
- **本 Phase 对应编号**：`F3-02` / `F3-03`
- **本 Phase 新增文件**：`packages/workflow_core/src/workflow_core/executor_contract.py`
- **本 Phase 修改文件**：`workflow_core/retry.py:7-65,68-168`、`workflow_clean/service.py:67-129`、`workflow_rag/service.py:35-233`、`apps/worker/.../main.py:46-57`
- **具体功能预期**（净新高风险，≥5 条含边界/失败/降级/竞态）：
  1. `ExecutorResult` + `execute(step, deps) -> ExecutorResult` 协议定义清晰：执行器只声明「产物 + 下游意图 + run 推进意图 + 错误码」，**不持有写 core 终态的能力**。
  2. clean/rag 执行器删除全部 core 终态写入（`status='succeeded'`、UPDATE run、自插下游 step）与 `conn.commit()`/`CURRENT_TIMESTAMP`（core 侧）；只产 `ExecutorResult`。
  3. `succeed_claim` 在**确认 claim 仍 active 的同一显式事务内**（与 F1-04 BEGIN IMMEDIATE 同窗口）统一落：artifacts → downstream（幂等）→ step succeeded → run advance → step_attempt → event → commit。
  4. **过期租约竞态（核心边界）**：worker-A 迟到调 succeed_claim(token-A) 时 claim 已非 active → succeed_claim 返回 False，**不写任何副作用**；worker-B 的副作用因确定性 key 不被重复。这是双重执行被堵死的关键路径。
  5. **失败/降级路径**：执行器抛异常 → main 走 fail_claim，执行器无任何 core 残留（无自 commit）；F6 消费方未就绪时契约先落地、clean→rag 分两批迁移，但**任一执行器不得保留自 commit**。
  6. **契约边界**：`deps` 不暴露可写终态的 core_conn 权限（执行器即便想写终态也无接口），从类型层面杜绝职责回流。
- **对应测试台账项**：`FF-F3-T04` / `FF-F3-T05` / `FF-F3-T06` / `FF-F3-T07` / `FF-F3-T08`（详见 §8）
- **收口标准**：clean/rag service 内 0 个 core 终态写入与 commit；succeed_claim 单事务落全部副作用；过期租约竞态下无重复。
- **本 Phase 风险提醒**：改执行器↔内核边界影响面大、F6 依赖；**与 F1-04 同窗口**（共享 succeed/fail/claim 多写函数，避免两次触碰）；先冻结契约接口再迁移；先红后绿覆盖竞态而非仅 happy-path。

### 5.3 Phase 3 — restart recovery 模式

- **Phase 目标**：restart 按失败阶段锚点恢复，`mode` 生效（[Q4]）。
- **本 Phase 对应编号**：`F3-05`
- **本 Phase 修改文件**：`workflow_core/restart.py:29-139`
- **具体功能预期**（高风险，含边界/降级）：
  1. recovery 模式按 run `current_stage`/最后失败 step 决定重启锚点，不再无条件 `clean:init`。
  2. rag 阶段失败的 workflow 从 rag 锚点恢复，已成功的 clean 阶段不被重跑（避免浪费 + 潜在幂等违反）。
  3. `mode` 真实影响行为（消除死参，restart.py:125,135）。
  4. **前置依赖**：[Q4] 明确「前置必修 F3-04 available_at」——Phase 3 复用 Phase 1 的 SQL strftime available_at，否则任何 mode 都不就绪。
  5. **边界/降级**：锚点定位失败回退 stage 级（不回退 clean 全量）；force/kickstart 入参本轮拒绝/标 degraded（[Q4] 延后）；run 不存在仍走 failed 分支。
- **对应测试台账项**：`FF-F3-T09` / `FF-F3-T10`（详见 §8）
- **收口标准**：rag 阶段失败 run restart 后 clean step 不被重置、rag 锚点就绪；mode 影响行为。
- **本 Phase 风险提醒**：依赖 Phase 1 available_at 修复；recovery 锚点定位逻辑需覆盖多阶段失败矩阵。

### 5.4 Phase 4 — 可靠性债收口 + 并发回归

- **Phase 目标**：就近捆绑同主题 medium 债 + 交付并发双重执行回归 harness（退出硬闸）。
- **本 Phase 对应编号**：`F3-06` / `F3-07` / `F3-08` / `F3-09`
- **本 Phase 新增文件**：`tests/integration/p1_kernel_closure/test_kernel_recovery.py`、`tests/fixtures/`（冻结时钟 + 双 worker 原语）
- **本 Phase 修改文件**：`workflow_core/{retry,leases,graph,events,__init__}.py`、`apps/worker/.../main.py`
- **本 Phase 删除文件**：`workflow_core/graph.py` 的 `write_workflow_event`（死代码函数删除；若 graph.py 仅此一函数则整文件删）
- **具体功能预期**（含竞态/降级）：
  1. retry 退避读 schema 列 + 指数；reap 退避同（不再 0s）。
  2. 错误分类透传：执行器领域异常带 error_code，main 透传，据类型决定 retryable。
  3. 删 `graph.write_workflow_event` 死代码；统一 `events.append_workflow_event` 去显式 created_at 交 DDL DEFAULT。
  4. `workflow_step_links` 接线（写 next 边）或显式延后记理由。
  5. **并发竞态 harness**：claim→真实 now_iso 写 lease→强制过期→reap→第二 worker→断言 artifact/chunk 无重复（修复前红、修复后绿）；**走真实 now_iso 写入路径，禁止手写 SQL 覆盖 lease**（吸取 G-CR8-02）。
- **对应测试台账项**：`FF-F3-T11` / `FF-F3-T12` / `FF-F3-T13` / `FF-F3-T14`（详见 §8）
- **收口标准**：退避/错误分类按设计；单一事件写入器；step_links 接线或记账；并发 harness 转绿。
- **本 Phase 风险提醒**：F3-09 是退出硬闸，依赖 Phase 2 终态归属落定才能转绿；harness 必须走真实写入路径否则重蹈夹具掩盖。

---

## 6. 依赖的冻结设计决策（只读引用）

> 不在本节填写新 Q/A；只引 register 的 Q 编号。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[Q4]` restart recovery 模式 | `docs/design/first-fixes/owner-gated-qna.md` Q4 | F3-05 做 recovery（按 current_stage/失败 step 锚点）；force/kickstart 延后（§2.2 O1）；**前置必修 F3-04 available_at** | 若 [Q4] 被推翻→F3-05 blocked，回退到「仅修 available_at + 声明只支持全量」（Q4 子选项 B）|
| `[Q7]` 全 phase 先红后绿 | `docs/design/first-fixes/owner-gated-qna.md` Q7 | 全 phase 退出以「先红后绿回归测试」为证据（§8）；F7 前禁止新增手写正确数据绕过被测路径的夹具（直接约束 F3-09 走真实 now_iso）；CI 断言强度门禁 | 若不成立→本 AP 仍按 §8 四元组收口（test-first 是本 AP 自有纪律的下限）|
| `终态写入单一归属内核 + 执行器契约`（planning §4 红线第 2 条）| `docs/design/first-fixes/initial-planning-by-opus.md` §4 | F3-02 落地：执行器只产 ExecutorResult、不写终态/不 commit | 红线，非 Q；不成立则 F6 复刻双重执行，本 AP 不得标 executed |
| `事务原子性显式化`（planning §4 红线第 3 条 / F1-04）| `docs/design/first-fixes/initial-planning-by-opus.md` §4 §5 DAG | F3-02 多写事务重构与 F1-04 包 BEGIN IMMEDIATE 同窗口（共享 succeed/fail/claim）| F1-04 未到位→F3-02 的「同一事务内统一落库」无原子性，blocked，回退到 F1 |

---

## 7. 内置 Reference-Anchor 锚区

> §7.1 摘自 `part-cr-4.md`（真源）与实际源码核行号；与本 AP 工作项一一对应。

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `apps/worker/src/smind_worker/main.py:35-57` | `_run_once`：restart→purge→claim→heartbeat→执行器→succeed/fail；**无 reap**、忽略返回值 | F3-01 接线 reap；F3-02/F3-03 执行器返回 ExecutorResult + 检查返回值 | `✅ 复用` | 接线点在 :36-37 后；返回值检查在 :53,56 |
| A-2 | `packages/workflow_core/src/workflow_core/leases.py:27-106` | `reap_expired_claims`：定义完整但**0 运行时调用**（死代码）；:34 用 SQL strftime 比较（正确）；:76 reap 退避 0s | F3-01 接线（reap 本身正确，缺调用）；F3-06 退避 | `✅ 复用` | 已建好别重写，只接线；F1 修 now_iso 后 :34 比较才命中 |
| A-3 | `packages/workflow_core/src/workflow_core/retry.py:7-65` | `succeed_claim`：UPDATE step succeeded + step_attempt + event；**与执行器自提交撕裂** | F3-02 扩参 `result: ExecutorResult`，统一落 artifacts/downstream/run advance | `♻️ 重 substrate` | 与 F1-04 同窗口包 BEGIN IMMEDIATE |
| A-4 | `packages/workflow_core/src/workflow_core/retry.py:68-168` | `fail_claim`：默认 `retry_backoff_seconds=1`（:74）、error_code 恒 EXECUTOR_FAILURE | F3-06 读 schema 列 + 指数；error_code 透传 | `✅ 复用` | :98-100 退避 SQL 表达式正确，只缺接线值 |
| A-5 | `workflow_clean/service.py:117-129` | clean 执行器**自提交** step succeeded（:118）+ UPDATE run（:124）+ commit（:129）+ 自插下游 rag step（:101-116，uuid4 key）| F3-02 删自提交、返回 ExecutorResult；F3-03 确定性 step_key | `♻️ 重 substrate` | G-CR6-03 落点；:118 用 CURRENT_TIMESTAMP（第三时间格式，顺带消除）|
| A-6 | `workflow_rag/service.py:223-233`、`:209-219`、`:82-98` | rag 执行器**自提交** step succeeded + commit（:233）+ run completed（:209-219）+ 自插下游 construct step | F3-02 删自提交、返回 ExecutorResult；F3-03 确定性 chunk/step key（:55,95,106-108）| `♻️ 重 substrate` | G-CR7-06 落点；construct vec 五步序（vec_conn）保留在执行器，core 终态交内核 |
| A-7 | `packages/workflow_core/src/workflow_core/restart.py:72-99` | `process_restart_requests`：无条件 INSERT/重置 `clean:init`（:76）、available_at 绑定畸形 now_iso（:79,88）、`mode` 死参（:125,135）| F3-04 available_at SQL 化；F3-05 recovery 锚点；mode 生效 | `♻️ 重 substrate` | core.sql:396-401 保留 mode/target_step_id/scope_json |
| A-8 | `packages/workflow_core/src/workflow_core/graph.py:9-35` | `write_workflow_event`：死代码（0 内部调用），self-commit（:35），7 列不传 created_at | F3-07 删除该函数 + 移除导出 | `✅ 复用`（删除） | __init__.py:2,6,16 导出 |
| A-9 | `packages/workflow_core/src/workflow_core/events.py:9-36` | `append_workflow_event`：内核实用，8 列**显式 created_at=now_iso()**（:24,34，畸形）；audit 同（:55,66）| F3-07 去显式 created_at 交 DDL DEFAULT | `✅ 复用` | core.sql:343 DDL DEFAULT strftime（正确）|
| A-10 | `docs/refactor/core.sql:321-332` | `workflow_step_links` DAG 边表：UNIQUE(from,to,type)，当前**零写入** | F3-08 接线 next 边 或 显式延后 | `🆕 净新`（写入路径）| 表已建好，缺写入器 |
| A-11 | `docs/refactor/core.sql:535`、`:713` | `v_ready_steps`/`v_stale_claims`：`available_at`/`lease_expires_at <= strftime('%Y-%m-%dT%H:%M:%fZ','now')` | F3-04 同源比较；F3-01 reap 命中前提 | `✅ 复用`（读不改）| 已建好别重写——写入侧对齐它 |
| A-12 | `packages/workflow_core/src/workflow_core/executor_contract.py` | 将新建：`ExecutorResult` + `execute` 协议 + `ExecutorDeps` | F3-02 契约定义（F6 建造基准）| `🆕 净新` | F6a/F6b 消费方依赖此接口 |
| A-13 | `tests/integration/p1_kernel_closure/test_kernel_flow.py:75-83` | 现有 reap 测试**手写 SQL 覆盖 lease_expires_at**（绕过 now_iso）| F3-09 反例参照：新 harness 必须走真实 now_iso，**不复制此手写覆盖** | `⛔ 反例`（见 §7.2 ⛔2）| G-CR8-02 夹具掩盖确凿证据 |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | **执行器自行 commit 终态**（clean:118-129 / rag:223-233 的 `status='succeeded'` + `conn.commit()`）| 终态归属内核（planning §4 红线第 2 条 / G-CR4-03）；执行器自提交导致与 succeed_claim 双写同一 step 终态、过期租约竞态下双重执行落盘。F3-02 后**严禁任一执行器保留自 commit**。|
| ⛔2 | **夹具手写正确时间绕过 now_iso**（test_kernel_flow.py:75-83 用 SQL strftime 覆盖 lease_expires_at）| G-CR8-02：该夹具同时掩盖 reap 死代码 + now_iso 缺秒 + 双重执行三个 blocker，证明的是「若格式正确且有人调 reap 则有效」而非「系统会自动回收」。F3-09 harness 必须用真实 `now_iso()` + 极小 lease_seconds + 冻结时钟，禁止手写覆盖。|
| ⛔3 | F3-02 改 `succeed_claim` 多写却不包显式 `BEGIN IMMEDIATE`（autocommit 下每写即提交）| F1-04 / planning §4 红线第 3 条：autocommit 后裸多写丧失原子性（末尾 commit 成 no-op）；F3-02 的「同一事务内统一落库」必须与 F1-04 同窗口、显式事务包裹。|
| ⛔4 | reap 在 F1 时间修复前接线 | CR-4 断点 D：`now_iso` 缺 `%S` 时 reap 比较 0 命中；接线但不命中=假修。Phase 1 测试须验证「F1 修复后」才转绿。|
| ⛔5 | `workflow_step_links` 留装成完成的桩（声明写了实际没写）| [Q7] 横切纪律：不留装成完成的桩；F3-08 要么真接线、要么显式延后 + degraded 声明 + 测试 skip/xfail。|

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/first-code-review-plan/part-cr-4.md`（真源；R1~R15 含 file:line + legacy 对照 + 实测）、`part-cr-6.md`（G-CR6-03 clean 侧自提交）、`part-cr-7.md`（G-CR7-06 rag 侧自提交 + 五步序）、`part-cr-8.md`（G-CR8-02 夹具掩盖）。§7.1 是其与本 AP 相关子集摘录；完整借鉴台账（含 ✅借/🔶部分借/⛔反例/🆕净新 verdict）见真源。
- **安全 / 信任边界类工作项的威胁模型锚**：本 AP **无路径遍历/认证等经典信任边界项**（归 F4/F6）。但 F3-02/F3-03/F3-09 的「一次性语义（at-most-once）」是**数据完整性边界**——威胁向量 = 过期租约竞态下的双重执行（artifact/chunk/向量重复落盘）。威胁模型落点：`part-cr-4.md` R3「为什么重要（场景推演）」（worker-A claim→lease 过期→reap→worker-B claim→worker-A 恢复 commit→重复落盘）+ `part-cr-7.md` R5 五步序跨库一致性。F3-09 的攻击向量用例（§8.5）即对此威胁建模，不得只测 happy-path。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `FF-F3-T01` | reap 在 worker `_run_once` 运行路径被调用（非仅测试孤立调用）；过期 claim 被回收 | spike | 集成 | `🆕 新增 tests/integration/p1_kernel_closure/test_kernel_recovery.py::test_worker_loop_reaps` | F3-01 → reap 接线于运行路径 | `commit {sha} + test_worker_loop_reaps PASS + {YYYY-MM-DD HH:MM UTC}` |
| `FF-F3-T02` | 过期 claim 回收后 step 退 retry_wait、可被第二 worker reclaim（**走真实 now_iso 写 lease**）| spike | 集成 | `🔱 fork test_kernel_flow.py::test_reap + 真实 now_iso 写入断言（去掉手写 SQL 覆盖）` | F3-01 → 故障恢复成立 | `commit + test_reap_via_real_now_iso PASS + run-time` |
| `FF-F3-T03` | restart 后被重启 step 的 available_at 确定性 `<= now`、出现在 v_ready_steps | spike | 集成 | `🆕 新增 ...::test_restart_step_ready` | F3-04 → restart 不静默失效 | `commit + test_restart_step_ready PASS + run-time` |
| `FF-F3-T04` | 契约边界：`ExecutorResult` 字段完整；`deps` 不暴露写终态 core_conn 权限 | 短途 | unit | `🆕 新增 tests/unit/test_executor_contract.py` | F3-02 → 契约定义清晰 | `commit + test_executor_contract PASS + run-time` |
| `FF-F3-T05` | clean/rag service 内 0 个 core 终态写入与 commit（grep + 行为）| 短途 | 契约（drift gate）| `🆕 新增 tests/unit/test_no_executor_self_commit.py（grep status='succeeded'/conn.commit/CURRENT_TIMESTAMP）` | F3-02 → 执行器只产结果 | `commit + gate 0 命中 + run-time` |
| `FF-F3-T06` | succeed_claim 在单事务内统一落 artifacts/downstream/step/run；happy-path 端到端 | spike | 集成 | `🆕 新增 ...::test_succeed_claim_persists_result` | F3-02 → 终态单一归属 | `commit + test_succeed_claim_persists_result PASS + run-time` |
| `FF-F3-T07` | 重复执行同一 step：artifact/下游 step/chunk 计数不增（确定性 key 幂等）| spike | 集成 | `🆕 新增 ...::test_idempotent_replay` | F3-03 → 重放安全 | `commit + test_idempotent_replay PASS + run-time` |
| `FF-F3-T08` | succeed/fail 返回 False 时 main 告警（不静默忽略）| 短途 | unit | `🆕 新增 tests/unit/test_worker_checks_return.py` | F3-03 → main 检查返回值 | `commit + test PASS + run-time` |
| `FF-F3-T09` | rag 阶段失败 run restart：clean step **不**被重置、rag 锚点 step 就绪 | spike | 集成 | `🆕 新增 ...::test_restart_recovery_anchor` | F3-05 → recovery 锚点 | `commit + test_restart_recovery_anchor PASS + run-time` |
| `FF-F3-T10` | `mode` 真实影响行为（recovery vs 默认锚点）；force/kickstart 拒绝/degraded | 短途 | unit | `🆕 新增 tests/unit/test_restart_mode.py` | F3-05 → mode 非死参 | `commit + test_restart_mode PASS + run-time` |
| `FF-F3-T11` | retry 退避 = schema `retry_backoff_seconds` × 指数；不可重试 error_code 不重试 | 短途 | unit | `🆕 新增 tests/unit/test_retry_backoff.py` | F3-06 → 退避/错误分类 | `commit + test_retry_backoff PASS + run-time` |
| `FF-F3-T12` | 无 `graph.write_workflow_event` 调用；event created_at 为正确 SQL 格式 | 短途 | 契约（drift gate）| `🆕 新增 tests/unit/test_single_event_writer.py（grep + created_at 正则）` | F3-07 → 单一事件写入器 | `commit + gate 0 命中 + run-time` |
| `FF-F3-T13` | step_links：每条 next 派生写一条 link（接线）**或** xfail + §9.3 理由（延后）| 短途 | 集成/回归 | `🆕 新增 ...::test_step_links（接线）或 xfail` | F3-08 → 边表接线/记账 | `commit + test PASS 或 xfail-with-reason + run-time` |
| `FF-F3-T14` | **并发双重执行回归**：claim→真实 now_iso→强制过期→reap→第二 worker→artifact/chunk 无重复 | soak | live(D1 forensic) | `🆕 新增 ...::test_concurrent_no_double_execution（race × N deterministic）` | F3-09 → at-most-once（退出硬闸）| `commit + soak log + 副作用计数=1 × N + run-time` |

**列定义遵循模板 §8.1**（类型/层/来源/PASS 四元组）。

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/integration/p1_kernel_closure/test_kernel_flow.py::test_reap`（:73-87）| `🔱 fork → test_reap_via_real_now_iso`（FF-F3-T02）| **删除** :75-83 手写 SQL 覆盖 lease；改用真实 `now_iso()` + lease_seconds=1 + 冻结时钟 | 已存在，PASS（但**结构性假绿**：手写时间绕过 now_iso bug，G-CR8-02）|
| `tests/integration/p1_kernel_closure/test_kernel_flow.py`（其余 claim/succeed 用例）| `♻️ 沿用` | 0 改动（F3-02 后断言 succeed_claim 落 result）| 已存在，纳入回归 |
| `tests/integration/p3_clean_pipeline/test_clean_pipeline.py`、`p4_rag_pipeline/test_rag_pipeline.py` | `♻️ 沿用 + 适配` | F3-02 后执行器返回 ExecutorResult，调用侧改经 succeed_claim 落库 | 已存在，纳入回归（随 F3-02 适配）|

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·契约（drift gate）·回归 | 开发中持续（T04/05/08/10/11/12/13）|
| spike | journey 用例 | 集成·live | 每 Phase 收口（T01/02/03/06/07/09）|
| mega | 长程整合（capstone D 步）| live 全链 | **本 AP 收口**（并入 §8 capstone）|
| soak | deterministic × N（race）| live(D1) | **退出硬闸**（T14）|

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 `执行器真实业务算法的语义命中`（htmlCrawl/structurize 真实输出质量）→ 交 `FF-F6a/F6b`（本 AP 只测职责边界/契约/幂等，不测算法质量）。
- 不覆盖 `二次 restart PK 冲突可重入（R6）`→ 延后（§2.2 O3）；不在本 AP 假装覆盖。
- 不覆盖 `向量真实性（相关 chunk 排序）`→ 交 `FF-F5`（F3-09 只断言 chunk/向量「无重复」即数量不变，不断言语义）。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组证据；计数 ≠ 价值。
- `degraded` 必带机器可读 `reason`：F3-08 若延后 → step_links 测试 xfail 带 reason；force/kickstart 拒绝带 degraded 声明。
- **数据完整性边界（at-most-once）的测试必须含攻击向量用例**：FF-F3-T14 必须复现 §7.3 威胁模型——过期租约竞态下 worker-A 迟到恢复，断言 artifact/chunk/向量计数=1（不得只测单 worker happy-path）。
- **F3-09 / FF-F3-T02 必须走真实 `now_iso()` 写入路径**（吸取 G-CR8-02）：禁止手写 SQL 覆盖 lease_expires_at；harness 用极小 lease_seconds + 冻结时钟推进，证明「系统会自动回收」而非「若格式正确且有人调 reap 则有效」。
- **先红后绿强制**：每项在「F1 修复后、F3 修复前」的 HEAD 上必须 FAIL（reap 0 命中 / 双重执行重复落盘 / restart 不就绪），修复后 PASS（[Q7]）。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| **F1↔F3 耦合（reap）** | F3-01 reap 命中依赖 F1-02/03 修 `now_iso` 缺 `%S`；F1 未到位则接线后 0 命中（假修）| high | F3-01 排在 F1 之后；Phase 1 测试验证「F1 修复后」转绿（⛔4）|
| **F1↔F3 耦合（事务）** | F3-02 多写事务重构与 F1-04 包 BEGIN IMMEDIATE 触碰同一批 succeed/fail/claim 函数 | high | **F3-02 与 F1-04 同窗口推进**（planning §5 DAG 强耦合）；避免两次触碰同组函数 |
| F3-02 终态重构影响面大 | 改执行器↔内核边界，F6 依赖此契约 | high | 先冻结契约接口（executor_contract.py）再迁移；clean→rag 分两批；先红后绿覆盖竞态 |
| F6 消费方未就绪 | 契约定义好但 F6 真实执行器未建 | medium | 契约接口可先落地、桩执行器先适配契约（不留自 commit）；F6 建造时直接消费 |
| restart recovery 锚点定位 | 多阶段失败矩阵的锚点逻辑复杂 | medium | 边界回退 stage 级（不回退 clean 全量）；测试覆盖失败矩阵 |
| `workflow_step_links` 接线 vs 延后 | 当前无消费 links 的读路径 | medium | 接线（写 next 边）成本低则接；否则显式延后 + §9.3 理由 + xfail（⛔5）|

### 9.2 约束与前提

- **技术前提**：F1（keystone）已完成——`now_iso` 含 `%S`、engine autocommit + 多写 helper 包 BEGIN IMMEDIATE；`smind_common.time` 单一时间 SSOT 可用。
- **运行时前提**：P 阶段无生产数据；SQLite WAL（engine.py:15）；core/vec 双连接（worker main.py:25-26）。
- **组织协作前提**：F3-02 契约接口需与 F6a/F6b 实现者对齐字段（ExecutorResult/ExecutorDeps）；同窗口与 F1-04 实现者协调。
- **上线 / 合并前提**：F3-09 退出硬闸（soak race × N）PASS 且四元组齐全；clean/rag service 无 core 自 commit 残留（drift gate FF-F3-T05 0 命中）。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/design/first-fixes/initial-planning-by-opus.md` §6.3（F3-05 由 refine 落档为 recovery 已在 §2.C；本 AP 回填 F3-08 接线/延后裁定）。
- 需要同步更新的说明文档 / README：`executor_contract.py` 的 docstring 作为 F6 建造基准的接口契约说明（下游 F6a/F6b 引用）。
- 需要同步更新的测试说明：`tests/fixtures/` 新增冻结时钟 + 双 worker 并发原语（供 F5/F7 复用，对齐 planning §4 meaningful-test inventory）。
- **F3-08 若延后**：在本节显式记理由（如「本 AP 无消费 step_links 的读路径，DAG 边表延后至有 DAG 可视化/重放消费方时接线」）+ degraded 声明 + FF-F3-T13 标 xfail-with-reason。

### 9.4 完成后的预期状态

1. worker 崩溃后过期 lease 被 `_run_once` 每轮自动回收，step 不再永久卡 `running`（reap 从死代码变运行路径，G-CR4-01 闭环）。
2. step 终态/下游派生/run 推进/commit 单一归属内核 `succeed_claim`/`fail_claim`（同一显式事务）；clean/rag 执行器只产 `ExecutorResult`、无自 commit；过期租约竞态下 at-most-once 成立（G-CR4-03/G-CR6-03/G-CR7-06 闭环）。
3. `executor_contract.py` 交付，作为 F6 全部真实执行器的建造基准（F6a/F6b 直接消费）。
4. restart 写出确定性就绪的 available_at + recovery 模式按失败阶段锚点恢复，`mode` 生效（G-CR4-04/05 闭环，[Q4]）。
5. retry 指数退避读 schema 列 + 错误分类透传；单一事件写入器（删 graph 死代码）；`workflow_step_links` 接线或显式记账（G-CR4-07/08/09、G-CR2-03 余项闭环）；并发双重执行回归 harness 走真实 now_iso 路径纳入退出硬闸。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有 `soak + 契约 drift gate + 退出层` 测试项必须 **PASS 且四元组证据齐全**：

1. **过期租约竞态下 at-most-once 成立**：artifact/chunk/向量计数=1 × N deterministic（由 `FF-F3-T14` 证明；走真实 now_iso 路径）。
2. **clean/rag service 内 0 个 core 终态自 commit**（由 `FF-F3-T05` drift gate 0 命中证明）。
3. **reap 在 worker 运行路径命中**（非测试孤立调用；由 `FF-F3-T01` 证明）。
4. **restart recovery 不重跑已成功 stage**（由 `FF-F3-T09` 证明）。
5. **单一事件写入器 + event created_at 正确格式**（由 `FF-F3-T12` drift gate 证明）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| reap 接线于运行路径、故障恢复成立 | F3-01 | FF-F3-T01 / T02 | `commit + test + run-time` | `未观察`（draft）|
| restart step 确定性就绪 | F3-04 | FF-F3-T03 | `commit + test + run-time` | `未观察` |
| 终态单一归属 + 执行器契约 | F3-02 | FF-F3-T04 / T05 / T06 | `commit + test/gate + run-time` | `未观察` |
| 重放安全 + main 检查返回值 | F3-03 | FF-F3-T07 / T08 | `commit + test + run-time` | `未观察` |
| restart recovery 锚点 + mode 生效 | F3-05 | FF-F3-T09 / T10 | `commit + test + run-time` | `未观察` |
| 退避/错误分类 | F3-06 | FF-F3-T11 | `commit + test + run-time` | `未观察` |
| 单一事件写入器 | F3-07 | FF-F3-T12 | `commit + gate + run-time` | `未观察` |
| step_links 接线/记账 | F3-08 | FF-F3-T13 | `commit + test/xfail + run-time` | `未观察` |
| at-most-once（退出硬闸）| F3-09 | FF-F3-T14 | `commit + soak log + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | reap 接线命中；终态归属内核 + 执行器契约交付；restart recovery + available_at 修复；退避/错误分类/单一事件写入器/step_links 落定 |
| 测试 | §8 测试台账全 PASS（退出硬闸 FF-F3-T14 soak + drift gate FF-F3-T05/T12 四元组齐全）|
| 文档 | `executor_contract.py` 接口说明交付给 F6a/F6b；F3-08 接线/延后裁定回填 §9.3 |
| 风险收敛 | F1↔F3 耦合（reap 命中 + 事务同窗口）已处理；双重执行 critical 关闭 |
| 可交付性 | clean/rag service 无 core 自 commit 残留；契约为 F6 建造基准可消费 |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**；按 closure 五态如实归类 + handoff。特别地：若 F3-09 走的不是真实 now_iso 路径（手写 SQL 覆盖 lease），即便「绿」也判 `未观察`（重蹈 G-CR8-02 夹具掩盖）；若 F3-02 后任一执行器残留自 commit，判 `partial` 并 handoff，不 silent overclaim。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态非 `executed`，本节省略（draft）。

---

## 11. 执行日志回填（`executed` — 2026-05-31）

> 文档状态: `draft → executed`。执行人 Opus 4.8（主轨直接执行，未用收尾子代理）。提交 `2d289e9`。

### 11.1 环境
- 系统 python3 含 fastapi/pydantic/starlette/httpx；缺 numpy/uvicorn/bs4/lxml/requests/sentence_transformers/sqlite_vec（无外网，F3 不依赖）。
- 测试：`python3 -m pytest tests/ -q` → **65 passed**（含 F1/F2 + 新增 F3 7 用例）。

### 11.2 逐工作项
- **F3-01 reap 接线**：`apps/worker/main.py:_run_once` 开头调 `reap_expired_claims`（restart/purge 前），返回 >0 记日志。grep reap 命中 2 处。
- **F3-02 终态归属内核 + 执行器契约**：新增 `workflow_core/executors.py`（`ExecutorResult{downstream,run_advance}` / `DownstreamStep` / `deterministic_artifact_id` / `deterministic_step_id` / `apply_executor_result`）。`succeed_claim(conn, token, result=None)` 在重查 claim active 后、同一 `BEGIN IMMEDIATE` 事务内落 step 终态 + 下游 step + step_links 边 + run 推进。`workflow_clean.process_clean_step` / `workflow_rag.process_rag_step` 改为只产 `ExecutorResult` + 确定性 id 数据写入，**0 处 `conn.commit` / 0 处 `status='succeeded'`**（grep 核验）。worker 改为 `result=process_x(); ok=succeed_claim(conn,token,result)`。
- **F3-03 幂等键 + 检查返回值**：artifact/chunk/下游 step 用确定性 id（`deterministic_artifact_id(step,suffix)` / `chunk_id=f"{run}:{idx}"` / `deterministic_step_id`）+ `INSERT OR IGNORE` / `ON CONFLICT DO NOTHING`；worker 检查 succeed/fail 返回 False 并告警。
- **F3-04 restart available_at**：recovery 重置用 SQL `strftime('%Y-%m-%dT%H:%M:%fZ','now')`（与 v_ready_steps 同源）。
- **F3-05 restart recovery**：`process_restart_requests` 按"最后 failed/retry_wait step 的 stage"锚点，仅重置失败 step（已成功步骤不动），run.current_stage=锚点 stage；`force_recovery`/`kickstart` 显式置 `failed` + error_message（[Q4] 本轮仅 recovery）。
- **F3-06 退避**：`fail_claim` 读 schema `retry_backoff_seconds` 列 + `base * 2**(attempt-1)`（修复早期 None 注入 SQL 致 NOT NULL 崩溃的中间 bug）。
- **F3-07 删重复事件写入器**：删 `graph.write_workflow_event`（grep `def write_workflow_event` = 0），`__init__` 移除导出；`events.append_workflow_event` / `append_audit_log` 去显式 `created_at`，交 DDL DEFAULT（T12 正则校验格式）。
- **F3-08 step_links**：接线——`apply_executor_result` 每条 downstream 写一条 `next` 边（`ON CONFLICT(from,to,type) DO NOTHING`）。T06 断言 1 条边。
- **F3-09 并发回归**：`tests/integration/p1_kernel_closure/test_kernel_recovery.py`。

### 11.3 先红后绿（test_kernel_recovery.py，7 passed）
- `test_t14_concurrent_no_double_execution`：worker-A 负 lease claim（真实 now_iso 写入，**无手写 SQL 覆盖 lease**）→ process → reap → worker-B 重 claim+succeed → worker-A 迟到 succeed 返回 False → 断言 cleaned artifact=1、rag:structurize step=1（at-most-once）。
- `test_t06`：succeed_claim 应用下游 + run.current_stage=rag + step_links=1（内核归属）。
- `test_t07`：同 step 执行两次 → cleaned artifact 仍=1（确定性 id 幂等）。
- `test_t09`：rag 阶段失败 run recovery → clean(succeeded) 不动、rag(failed) 回 pending+ready、run running。
- `test_t10`：force_recovery → restart_requests.status=failed（本轮拒绝）。
- `test_t11`：fail_claim 无显式退避 → 读 schema 列 120s、available_at 未来 >60s。
- `test_t12`：`graph.write_workflow_event` 不存在；event created_at 匹配 `...SS.mmmZ`。
- 全量回归：`python3 -m pytest tests/` → **65 passed**（F1 16 + F2 27 + p3-p7 + F3 7 等）。

### 11.4 偏差与 handoff
- 执行器**数据**副作用（artifact/chunk/vec/object）由执行器直接写但用确定性幂等 id；**终态/下游/run 推进**归内核——比 AP 设想的"全部经 ExecutorResult"更贴合既有丰富逻辑，且满足"终态单一归属 + 反双重执行"红线。
- 跨库 vec 写仍非 core 事务覆盖（注释标明）→ handoff FF-F4。
- F6 真实执行器去桩在此契约上建造（下游 FF-F6a/b）。
