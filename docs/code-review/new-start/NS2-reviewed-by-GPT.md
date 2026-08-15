# Nano-Agent 代码审查

> 审查对象: `MKB new-start / NS2 pipeline priority dispatch`
> 审查类型: `mixed`
> 审查时间: `2026-08-15`
> 审查人: `GPT`
> 审查范围:
> - `docs/plan/new-start/NS2-pipeline-priority.md`、`docs/closure/new-start/NS2-pipeline-priority-closure.md`
> - `src/runtime/workflow/`、`src/runtime/intake/`、`src/services/`、`src/persistence/`、`api/` 与 `tests/`
> 对照真相:
> - `docs/plan/new-start/NS2-pipeline-priority.md`
> - `.adocs/closure.md`、`docs/baseline/domain-truth/S02-task-api.md`、`S03-workflow-engine.md`、`S11-inference-runtime.md`、`D04-turso-physical-schema.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> NS2 已交付 migration、行上 admit/claim 和部分策略单测，但 priority → dispatch pool → 实际模型调用的生产链路没有打通；P6 规定的 e2e 与真实并发 soak 也未交付，因此 action-plan 不应保持 `executed`，closure 的“100% 达成”不能成立。

- **整体判断**：`核心骨架部分成立，但生产调度合同、测试台账和收口证据均未完成。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. `正常/低优先级 Process 可以占用 local-inference 池却实际走 non-interactive CLI；这是资源会计与真实调用通道脱钩，不是单纯的测试缺口。`
  2. `确定性 vectorize、explicit override、超预算和 retry/recovery 容量边界没有被运行时的 admit/claim 链路正确消费。`
  3. `计划指定的 NS2 e2e 和并发 soak 文件不存在，现有“soak”是串行循环；closure 将它们陈述为已验证，属于不实或至少不可支持的收口声明。`

---

## 1. 审查方法与已核实事实

本报告独立依据当前工作树、action-plan、closure 和本地可复跑命令形成；未采用任何既有同事审查报告作为结论或证据。

- **对照文档**：
  - `docs/plan/new-start/NS2-pipeline-priority.md`，特别是 §3、§4、§8、§10。
  - `docs/closure/new-start/NS2-pipeline-priority-closure.md` 与 `.adocs/closure.md`。
- **核查实现**：
  - `src/runtime/workflow/dispatch.py`、`runtime_core.py`、`runtime_outcome.py`、`runtime_materialize.py`。
  - `src/runtime/intake/generation_construct.py`、`vectorize.py`、`core.py`，以及 `src/services/config_snapshots.py`、`events.py`、`src/persistence/migrations/011_process_dispatch_pools.sql`。
  - `src/contracts/api/models.py`、`src/runtime/task/task_commands.py`、`api/app.py` 与所有 `test_dispatch_*`、相关 e2e/domain 测试。
- **执行过的验证**：
  - `uv run pytest tests/unit/test_dispatch_policy.py tests/unit/test_dispatch_claim.py tests/unit/test_dispatch_embed_and_gates.py tests/unit/test_dispatch_generation.py tests/unit/test_dispatch_mega.py tests/unit/test_dispatch_ddl.py tests/unit/test_dispatch_occupancy.py tests/unit/test_compression_channel.py tests/domain/test_architecture.py` → `49 passed`。
  - `uv run ruff check` → `All checks passed!`。
  - `uv run pytest tests/e2e tests/domain tests/unit -x --tb=short` → e2e 在 `tests/e2e/test_index_rebuild.py` 首次失败为 `sqlite3.OperationalError: disk I/O error`；这与 closure 标注的既有 VF V11 相符，不能计为 NS2 功能反证，也不能替代 NS2 的指定验收。
  - `uv run pytest tests/e2e/test_ns2_dispatch_lanes.py -q` → `ERROR: file or directory not found`。
  - `uv run pytest tests/unit tests/domain --collect-only -q` → 收集数 `298`；仅证明 closure 所述 unit/domain 数量可复现，不证明其 e2e 或 soak 声明。
- **复用 / 对照的既有审查**：
  - `none` — 本报告未读取或采纳既有审查结论。

### 1.0 本轮审查 todo-list 与 DAG

本轮按下列依赖执行，只有上游事实固定后才判断下游 claim；四条检视支线使用相同的一手代码/文档证据，最终结论由本审查者交叉复核。

1. 固定 action-plan 的 S1–S11、Test-ID、hard-gate 和 closure 格式要求。
2. 检查公开 Task/intake 参数、snapshot 派生、Task priority 变更与 Process 物化事实。
3. 检查 admit/claim、三池计数、retry/recovery、DB DDL/索引/事件和运行时配置注入。
4. 反向追踪 `ProcessCommand.dispatch_pool` 到 construct/structurize/vectorize 的真实模型调用。
5. 对照 unit/domain/e2e/soak 测试文件、断言形态和可复跑结果。
6. 将已证实事实与 closure 每项“closed/PASS/100%”陈述逐项比对，形成收口裁定。

```text
公开 API / Task priority ──┐
snapshot / channel_source ─┼─> Process materialize ─> admit + schema ─> claim command
Settings / Billing / budget ┘                                      │
                                                                    v
                              construct / structurize / vectorize 的实际调用通道
                                                                    │
                                                                    v
                              unit + domain + e2e + soak 证据 ─> closure hard-gate
```

### 1.1 已确认的正面事实

- 公开 `Task.priority` 仍是封闭的 `low|normal|high|urgent`，`IntakeIngestPayload.compression_channel` 只接受 `non-interactive|local-inference|None`；`cloud-inference` 未被开放为公开通道。[models.py](/mnt/usb/workspace/myknowledgebase/src/contracts/api/models.py:175) [models.py](/mnt/usb/workspace/myknowledgebase/src/contracts/api/models.py:282)
- migration 011 确实在既有 `mkb_processes` 上新增三个物理列、枚举 CHECK 和 partial index，未建立新的 required 表，也未把派发态写入 `payload_extra`。[011_process_dispatch_pools.sql](/mnt/usb/workspace/myknowledgebase/src/persistence/migrations/011_process_dispatch_pools.sql:6)
- `claim_next` 在同一写事务内先调用 `_admit_waiting_processes_tx`，之后按 `dispatch_admitted=1` 和 pool running cap 选择候选；未 admit 的 Process 不会进入正常 claim 查询。[runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:319) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:334)
- worker 在没有可 claim 行时直接返回 `False`，没有新增等待槽位的 sleep。[worker.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/worker.py:45)
- Qwen 已成为 generate binding 的优先 winner；纯函数 `choose_pool` 也覆盖了四个 priority 的基本边界。这些是局部实现完成，而非端到端派发完成。

### 1.2 已确认的负面事实

- 计划要求的 `tests/e2e/test_ns2_dispatch_lanes.py` 与 `tests/unit/test_dispatch_admit_soak.py` 在 HEAD 中都不存在；T60/T62/T70 无法声称 PASS。[NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:301) [NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:312)
- `ProcessCommand` 虽带有 `dispatch_pool`，但 intake handler 不读取它；实际 construct transport 仍由原始 state payload 的 `compression_channel` 决定。[runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:799) [generation_construct.py](/mnt/usb/workspace/myknowledgebase/src/runtime/intake/generation_construct.py:92)
- snapshot 对 omit+normal 已派生 `local-inference`，但 execution payload 只是原始 payload 的序列化，省略值仍为 `None`；运行时因此回退到 `DEFAULT_COMPRESSION_CHANNEL=non-interactive`。[config_snapshots.py](/mnt/usb/workspace/myknowledgebase/src/services/config_snapshots.py:569) [config_snapshots.py](/mnt/usb/workspace/myknowledgebase/src/services/config_snapshots.py:401) [prompt_profiles.py](/mnt/usb/workspace/myknowledgebase/src/services/prompt_profiles.py:37)
- admission 不传 snapshot、`explicit_channel` 或 `over_budget` 给策略函数；Settings 的 capacity/budget 也没有注入 orchestrator 实际使用的硬编码常量。[runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:191) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:231) [dispatch.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/dispatch.py:11)
- closure 自己引用的 action-plan 收口映射仍把全部证据标成“未观察”，而该计划明确规定任一 hard-gate 未观察时不得标记 `executed`。[NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:761) [NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:795)

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 已沿 API → snapshot → Process → admit/claim → handler → outcome 的数据流反向核查。 |
| 本地命令 / 测试 | `yes` | dispatch 相关 49 项和 ruff 均通过；指定 NS2 e2e 文件不存在；全 e2e 运行遇已知 I/O 问题后停止。 |
| schema / contract 反向校验 | `yes` | 核查 011、migration runner、占用 SQL、retry/recovery 状态变迁与公开 Literal。 |
| live / deploy / preview 证据 | `no` | 没有提供任何 live/D1/deploy 证据；故不把本地绿测试表述为生产已验证。 |
| 与上游 design / QNA 对账 | `yes` | 以 NS2 action-plan 的冻结车道、Test-ID、Definition of Done 与 closure template 为准。 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | `dispatch_pool` 没有控制真实生成通道 | `critical` | `correctness` | `yes` | 让 immutable dispatch 决策成为 handler 唯一运行时通道真源，并做端到端断言。 |
| R2 | admission 未消费冻结 snapshot、显式覆盖、预算和覆盖审计 | `high` | `protocol-drift` | `yes` | 物化/持久化必要事实，接入 admit，补显式覆盖审计与事件字段。 |
| R3 | deterministic embed 与受限队列 FIFO 在真实 admission 中失效 | `high` | `correctness` | `yes` | 按冻结 inference mode 分类，且从 admission 起按 embed FIFO。 |
| R4 | retry / lease recovery 可突破 queued capacity | `high` | `correctness` | `yes` | retry/recovery 必须重新 admit 或持续计入保留容量。 |
| R5 | Task 仍 queued 时改 priority 会留下 stale `priority_rank` | `medium` | `correctness` | `no` | 禁止 Process 物化后改 priority，或 CAS 更新全部未领取 Process 与 admission。 |
| R6 | schema 与 Settings 未形成可配置、可约束的生产会计合同 | `medium` | `platform-fitness` | `no` | 注入 settings、补状态耦合约束/索引，并测试 010 升级。 |
| R7 | P6 指定 e2e、真实并发 soak、domain/closure guards 缺失 | `high` | `test-gap` | `yes` | 新增指定测试文件和攻击/恢复/跨池组合覆盖后才重跑台账。 |
| R8 | closure 与 action-plan 的 completed/PASS 叙述不受证据支持 | `high` | `docs-gap` | `yes` | 撤回 executed/完成断言，按 closure 模板记录真实五态与 deferred，修复后重写。 |

### R1. `dispatch_pool` 没有控制真实生成通道

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - claim 时把行上 `dispatch_pool` 写入 `ProcessCommand`，但该字段在 intake 执行路径中没有被消费。[runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:810) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:826)
  - construct 只从 state 的原始 `payload.compression_channel` 取通道；缺失值即使用 `DEFAULT_COMPRESSION_CHANNEL`，即 `non-interactive`。[generation_construct.py](/mnt/usb/workspace/myknowledgebase/src/runtime/intake/generation_construct.py:92) [generation_construct.py](/mnt/usb/workspace/myknowledgebase/src/runtime/intake/generation_construct.py:101) [prompt_profiles.py](/mnt/usb/workspace/myknowledgebase/src/services/prompt_profiles.py:37)
  - snapshot 对 omit+normal/low 派生 local，但 `_execution_payload` 没有把该派生值放入 stage state。[config_snapshots.py](/mnt/usb/workspace/myknowledgebase/src/services/config_snapshots.py:569) [config_snapshots.py](/mnt/usb/workspace/myknowledgebase/src/services/config_snapshots.py:401)
  - `structurize` 在 CLI 存在时优先走 CLI，也没有依据 command pool 选择执行器。[generation_construct.py](/mnt/usb/workspace/myknowledgebase/src/runtime/intake/generation_construct.py:794)
- **为什么重要**：
  - 一个 omit+normal 或 low 任务可在 DB 中占 `local-inference` 的 2+6 资源，却实际调用 CLI/NI。反过来，normal overflow、urgent explicit local、low explicit NI 也可发生“持有 A 池、调用 B 通道”。容量、billing、low 禁 NI、receipt 和运行时可观测性同时失真。
  - 这直接违反 P1-03、P4-01/P4-02/P4-04/P4-07，以及 §10 “默认 normal 先 GPU、low 锁 GPU”的交付定义。
- **审查判断**：
  - `ProcessCommand.dispatch_pool` 目前只是未使用的传递字段。closure 对“生成端点/ProcessCommand.dispatch_pool/车道接线完成”的判断不成立。
- **建议修法**：
  - 将 admission 形成的 immutable dispatch 决策作为 handler 的唯一执行真源；所有 generate step 必须以它选择 local facade 或 NI CLI。
  - 保留显式覆盖的来源/审计事实，但禁止 handler 再从原始 payload 重新选择与已占用 pool 不同的通道。为每个 generate step 添加“DB pool、command pool、实际 adapter/receipt channel 一致”的 e2e 断言。

### R2. admission 未消费冻结 snapshot、显式覆盖、预算和覆盖审计

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `pool_kind` 仅在调用者传入 snapshot 时才识别 deterministic vectorize；admit 调用只传 `process_key`。[dispatch.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/dispatch.py:71) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:188)
  - `choose_pool` 具备 `explicit_channel`、`over_budget` 参数，但唯一生产 admit 调用只传 priority、queued、`live_inference`、billing。[dispatch.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/dispatch.py:97) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:231)
  - `dispatch_local_char_budget` 和 `DISPATCH_LOCAL_CHAR_BUDGET` 除定义/测试外没有生产调用点。[config.py](/mnt/usb/workspace/myknowledgebase/src/runtime/config.py:47) [dispatch.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/dispatch.py:17)
  - 成功的 `compression_channel` 覆盖没有 security audit；现有 `SecurityAuditWriter` 调用只记录被拒绝的 `request.overrides`。admit event payload 也没有计划要求的 `channel_source`。[config_snapshots.py](/mnt/usb/workspace/myknowledgebase/src/services/config_snapshots.py:820) [task_create.py](/mnt/usb/workspace/myknowledgebase/src/runtime/task/task_create.py:187) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:200)
- **为什么重要**：
  - P4-03 的 normal 超预算溢 NI、P4-05 的显式强制池/低优先级审计、P4-07 的冻结离线行为均只存在于纯函数，运行时不可能按该合同做决定。
  - 显式 low→NI 同时缺少审计和正确的 pool 会计，是计划威胁模型中特意要求防护的套餐绕过路径。
- **审查判断**：
  - 这是“策略函数已写但没有生产输入”的实现，而非对 P4 完成度的充分实现。
- **建议修法**：
  - 在不使用 `payload_extra` 的前提下，设计可从冻结 snapshot 可靠获得或在 Process 行上显式保存的调度输入：inference mode、channel source/explicit channel、预算分类等；admit 只消费这些 immutable 事实。
  - 对 explicit channel 写入安全/领域审计（含来源且不含正文），并让 `process.dispatch_admitted` payload 含计划要求的 `pool`、`priority`、`channel_source`。补 T07/T35/T38/T40 的真实 DB→handler 测试。

### R3. deterministic embed 与受限队列 FIFO 在真实 admission 中失效

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - deterministic vectorize 只有手工传入 snapshot 才会被判为 unpooled；真实 admit 永远调用 `pool_kind(p_key)`，因此默认 `live_inference=false` 的 vectorize 仍进 embed 池。[dispatch.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/dispatch.py:84) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:191)
  - 所有 waiting 行在 admission 前按 `priority_rank DESC` 排列；embed 分支只是在该迭代顺序中取前 20 个。[runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:176) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:211)
  - claim SQL 虽把已经 admitted 的 embed 行按时间优先，但无法修复第 21 个之前已经发生的 priority 插队。[runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:342)
- **为什么重要**：
  - deterministic vectorize 错占 8+20 容量，会阻塞本应无池立即执行的离线流程。
  - 当 embed 队列接近 20 时，后到 urgent 可在 admission 阶段抢占先到 low 的唯一位置，违反“embed 不看 priority”的端到端定义；当前两行、未饱和的 FIFO 单测不能证明该不变量。
- **审查判断**：
  - P5-01/P5-03/P5-04 与 Gate 4 只能判 `partial`，closure 的完整 FIFO/独立池 PASS 不成立。
- **建议修法**：
  - admission 要基于该 Process 冻结的 inference mode；deterministic vectorize 直接 unpooled。
  - 将 waiting select 拆分为 generate priority 分支、embed FIFO 分支和 unpooled 分支；embed admission 和 claim 都固定 `available_at, created_at, process_uuid`，并增加队列满时“先 low、后 urgent”测试。

### R4. retry / lease recovery 可突破 queued capacity

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - occupancy 的 queued 仅计 `status='ready' AND dispatch_admitted=1`；`retry_wait` 不计入 reserve。[dispatch.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/dispatch.py:33)
  - retryable failure 将行改为 `retry_wait`，却保留 `dispatch_pool/dispatch_admitted`；在此期间 admit 可把 ready 队列补满。[runtime_outcome.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_outcome.py:137)
  - `promote_due_retries` 直接把该已 admitted 行回写为 ready，不重新竞争队列上限；lease recovery 同样直接把 claimed/running 行回写 ready。[runtime_outcome.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_outcome.py:237) [runtime_outcome.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_outcome.py:347)
- **为什么重要**：
  - 一个运行中、已 admitted 的 local 行进入 retry_wait 后，其他行可把 local queued 补到 6；该 retry 后回到 ready 时形成 queued=7。NI/embed 同理。故“queued 永不超 cap”的 hard-gate 不成立。
- **审查判断**：
  - P3/P5 的 normal 成功路径有容量骨架，但状态机边界绕开了会计，不可用于生产。
- **建议修法**：
  - 二选一并形成单一不变量：retry_wait 继续占用 reserved queue；或在 retry/recovery 时原子清空 admission/pool，promotion 后重新走 admit。对三池各自新增 retry、lease recovery、并发 claim 后的 queued/running 断言。

### R5. Task 仍 queued 时改 priority 会留下 stale `priority_rank`

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - materialize 时将 Task priority 复制为 Process `priority_rank`。[runtime_materialize.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_materialize.py:253) [runtime_materialize.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_materialize.py:305)
  - public PATCH 在 Task status 仍为 `queued` 时允许修改 priority，但只更新 Task 行，并不更新已物化 Process。[task_commands.py](/mnt/usb/workspace/myknowledgebase/src/runtime/task/task_commands.py:138) [task_commands.py](/mnt/usb/workspace/myknowledgebase/src/runtime/task/task_commands.py:152)
  - admit 的车道选择读取当前 `t.priority`，但 waiting/claim 排序读取旧的 `p.priority_rank`。[runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:178) [runtime_core.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py:184)
- **为什么重要**：
  - priority 从 normal 改 urgent 时可进入 NI 却仍按 normal 排队；反向修改也会遗留不应有的排序优势。它破坏 priority 双用的“同一事实”要求。
- **审查判断**：
  - 现有“Task 非 running 可改”的 API 与“Process 物化时冻结 rank”语义未收敛。
- **建议修法**：
  - 在任何 Process 物化后锁定 priority，或在同一 CAS 事务中更新所有未 claim Process 的 rank、清理/重算未 admit dispatch 决策；为 patch-before/after-materialize/admit/claim 的边界补测试。

### R6. schema 与 Settings 未形成可配置、可约束的生产会计合同

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - Settings 暴露六个 pool cap 和预算字段，但 runtime 调度直接使用模块硬编码常量；composition 仅传入 `live_inference`，不传 dispatch 配置。[config.py](/mnt/usb/workspace/myknowledgebase/src/runtime/config.py:47) [dispatch.py](/mnt/usb/workspace/myknowledgebase/src/runtime/workflow/dispatch.py:11) [app.py](/mnt/usb/workspace/myknowledgebase/api/app.py:273)
  - 011 只检查 pool 值与 admitted 的 0/1，允许 `dispatch_pool IS NOT NULL AND dispatch_admitted=0` 或未 admit 却已有 enqueue timestamp 等非法组合；现有 DDL 测试还将前一种组合视作合法插入。[011_process_dispatch_pools.sql](/mnt/usb/workspace/myknowledgebase/src/persistence/migrations/011_process_dispatch_pools.sql:6) [test_dispatch_ddl.py](/mnt/usb/workspace/myknowledgebase/tests/unit/test_dispatch_ddl.py:79)
  - plan 指出 embed FIFO 需按 `available_at, created_at` 支撑，但 011 的唯一新 index 没有 `created_at/process_uuid`；`dispatch_enqueued_at` 也只写不读。[011_process_dispatch_pools.sql](/mnt/usb/workspace/myknowledgebase/src/persistence/migrations/011_process_dispatch_pools.sql:14)
  - T10 测试从 fresh DB 运行全部 migration，未验证已到 010 的库升级、重复 migrate 或 Turso 升级。
- **为什么重要**：
  - 运维通过 `MKB_DISPATCH_*` 修改容量不会影响 scheduler；数据库 SSOT 也不能拒绝明显不一致的排队状态。长期队列在 FIFO 查询上会产生无必要排序负担。
- **审查判断**：
  - DDL 列晋升本身成立，但“可配置且可审计的生产 schema”仅完成一部分。
- **建议修法**：
  - 将 dispatch policy/capacity 以 Settings 实例注入 runtime，而不是同名硬编码常量。补最小状态耦合 CHECK 或集中受控写入约束，补 FIFO covering index；以真实 010 fixture、二次 migrate 和 Turso backend 覆盖 T10。

### R7. P6 指定 e2e、真实并发 soak、domain/closure guards 缺失

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - P6 要求的 lanes e2e 与 admit soak 文件不存在；现有 e2e 目录无 `test_ns2_dispatch_lanes.py`，unit 目录无 `test_dispatch_admit_soak.py`。[NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:301) [NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:312)
  - 所谓 soak 是 `for` 循环逐次 `await runtime.claim_next`，没有 `asyncio.gather`、barrier、多连接，也未做计划规定的 32 轮；只检查最终 running，不检查 queued。[test_dispatch_mega.py](/mnt/usb/workspace/myknowledgebase/tests/unit/test_dispatch_mega.py:350) [test_dispatch_mega.py](/mnt/usb/workspace/myknowledgebase/tests/unit/test_dispatch_mega.py:357)
  - generation 测试把 command pool 与 state channel 人为写成相同，无法发现 R1 的冲突路径。[test_dispatch_generation.py](/mnt/usb/workspace/myknowledgebase/tests/unit/test_dispatch_generation.py:89) [test_dispatch_generation.py](/mnt/usb/workspace/myknowledgebase/tests/unit/test_dispatch_generation.py:123)
  - domain architecture guard 只保护旧字符串，并未检查 `dispatch_*` 不进入 extra、无新表或 closure 的五态格式。[test_architecture.py](/mnt/usb/workspace/myknowledgebase/tests/domain/test_architecture.py:430)
- **为什么重要**：
  - 当前绿色测试正是漏过 R1–R4 的原因；不能作为 P6 或 hard-gate 通过的证据。
- **审查判断**：
  - T01/T02、纯函数策略、部分 DB admit/claim、Qwen winner 和 facade gate 有局部有效测试；但 T07、T13、T22、T31–T40、T50–T54、T60–T62、T70–T72 没有按台账要求充分覆盖，P6 应判 `missing`。
- **建议修法**：
  - 新增计划命名的 e2e/soak 文件，并将 Test-ID 作为测试名或参数 ID；在真实 app/runtime 组合中断言 Process 行、snapshot、command pool、实际 adapter/CLI receipt 和 audit event。
  - soak 必须使用独立连接/worker 的真正并发、重复轮次，并同时断言三池 `running` 与 `queued`。补 retry/recovery、满队列 embed FIFO、explicit low→NI 审计、default normal/离线、超预算、priority PATCH 的反例。

### R8. closure 与 action-plan 的 completed/PASS 叙述不受证据支持

- **严重级别**：`high`
- **类型**：`docs-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - closure 宣称全部 Phase “完整交付并严格验证通过”、调度功能“100% 达成”，也把 e2e/50 并发 soak 列为已完成。[NS2-pipeline-priority-closure.md](/mnt/usb/workspace/myknowledgebase/docs/closure/new-start/NS2-pipeline-priority-closure.md:17) [NS2-pipeline-priority-closure.md](/mnt/usb/workspace/myknowledgebase/docs/closure/new-start/NS2-pipeline-priority-closure.md:43) [NS2-pipeline-priority-closure.md](/mnt/usb/workspace/myknowledgebase/docs/closure/new-start/NS2-pipeline-priority-closure.md:73)
  - 上述 e2e/soak 文件并不存在，现有代码还存在 R1–R4 的明确反例；因此这些不是“证据不够漂亮”，而是与当前代码事实冲突。
  - action-plan §10.2 保留所有目标为“未观察”，§10.4 明确说任一退出 hard-gate 未观察不得标 `executed`；却在文件头标记 `executed`。[NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:761) [NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:797)
  - stage-final closure 应使用 `closed-with-explicit-deferrals`、§0–§7、A/B/C ledger、五态、handoff 与不可动清单；当前文件为 `close-with-known-issues`、仅到 §5，缺少要求章节和五态归类。[NS2-pipeline-priority.md](/mnt/usb/workspace/myknowledgebase/docs/plan/new-start/NS2-pipeline-priority.md:801) [NS2-pipeline-priority-closure.md](/mnt/usb/workspace/myknowledgebase/docs/closure/new-start/NS2-pipeline-priority-closure.md:5)
- **为什么重要**：
  - closure 是下游的信任锚。把不存在的测试、串行测试和未接通的运行时行为写为 PASS，会使后续阶段按错误前提施工。
- **审查判断**：
  - closure 中“011 列存在”“同事务 admit 骨架存在”“局部 unit/domain 298 与 ruff 通过”等窄事实可保留；“全部完成、端到端、并发 soak、100% 达成”必须撤回。action-plan 也应恢复非 `executed` 状态或新增明确的返工 action-plan。
- **建议修法**：
  - 先按本报告 blocker 完成修复与测试，再以 `.adocs/closure.md` 阶段 final 模板重写 closure。每个 ✅ 必须有可复跑四元组并归类为五态；billing/cloud/VF V11 等 deferred 必须 A/B/C 分类，未执行项不得改写成 PASS。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | 通道改名、公开闭集、priority 双用入口 | `partial` | 公开 Literal 与旧名守卫完成；派生通道没有支配实际执行。 |
| S2 | 纯策略、三池分类、注入单位 | `partial` | 纯函数存在；production admission 未提供 snapshot/override/budget 输入。 |
| S3 | 011 三列、索引、会计 | `partial` | 三列和枚举 CHECK 已落地；状态耦合、FIFO 索引、旧库升级与生产约束不足。 |
| S4 | 同事务 admit、分池 claim、embed FIFO | `partial` | 同事务与未 admit 禁领成立；retry/recovery 超 cap，embed admission 可按 priority 插队。 |
| S5 | 生成步入池与实际通道接线 | `partial` | 行可分配入池，但 handler 不使用 command pool，真实调用不受该决定约束。 |
| S6 | live embed 入池、deterministic skip、独立会计 | `partial` | live/embed 计数骨架存在；deterministic 真实路径错误入 embed。 |
| S7 | salvage、显式覆盖与审计 | `missing` | low 禁 salvage、显式强制池、成功覆盖审计和事件 `channel_source` 未实现/未证实。 |
| S8 | normal 超预算和 local offline 溢流 | `missing` | 参数只在纯函数；admit 未计算或传入 over-budget，默认执行通道又与 pool 脱节。 |
| S9 | BillingPort 与 facade 末闸 | `partial` | 恒真端口和 facade=12 存在；scheduler capacities 不接受 Settings，Billing False 未走真实 admit 测试。 |
| S10 | Qwen local generate winner | `done` | registry binding 与相应单测支持 Qwen priority=5、Lightning 保留。 |
| S11 | 全测试台账、truth 回填、closure | `missing` | 指定 e2e/soak/domain/closure guard 缺失；S02/S03/S11/D04/S14/S15 窄回填无 NS2 实施证据；closure 不合格。 |

### 3.1 对齐结论

- **done**: `1`
- **partial**: `7`
- **missing**: `3`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

这更像“DDL 与 scheduler 骨架完成、生产通道接线和验收未完成”的状态，而不是 action-plan 所定义的 `executed`。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 真实 billing 套餐计量/扣减 | `遵守` | 仅有恒真 `BillingPort`；本报告未将真实扣费缺失作为 blocker。 |
| O2 | cloud-inference adapter/路由 | `遵守` | cloud 仅在内部 reserved 集合，公开 API 拒绝该值；未发现池满泄洪到 cloud。 |
| O3 | MiniMax 替换 Claude `-p` | `遵守` | 未将模型替换要求误判为 NS2 blocker。 |
| O4 | urgent 老化 | `遵守` | 未见新增老化策略；本轮不要求实现。 |
| O5 | 新 required 表 / `payload_extra` 承载派发态 | `遵守` | 011 为既有表加列；未发现以 extra 保存 dispatch state。 |
| O6 | VF V11 pyturso I/O harness | `误报风险` | 全量 e2e 首次的 disk I/O 失败按既有残差记录，不计作本报告的 NS2 功能 finding。 |
| O7 | 新公开 `inference_lane` 字段 | `遵守` | 公共 Task API 继续使用既有 priority 和嵌套 compression_channel。 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested — NS2 不满足 action-plan 的 Definition of Done；当前 closure 的完整完成结论应撤回。`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. 修通 snapshot/priority/explicit override → admission → durable pool → `ProcessCommand` → generate/embed executor 的单一事实链；确保 low 不会占 local 池却走 NI，且 normal/urgent/explicit/离线/超预算都与实际 receipt 一致。
  2. 修复 deterministic embed、饱和队列下的 admission FIFO、retry/recovery capacity 会计，并覆盖三池 `queued/running` 上限。
  3. 交付 T60/T62 的 e2e lanes、T70 的真实并发 soak、T71/T72 guards 和所有缺失安全/边界测试；之后以真实结果重写 truth 回填、action-plan 状态与 closure。
- **可以后续跟进的 non-blocking follow-up**：
  1. 将 dispatch capacity/budget 从硬编码常量改为受 Settings 注入的 policy，并补数据库状态耦合 CHECK 与 FIFO index。
  2. 补已到 010 的 SQLite/Turso migration upgrade、重复 migrate 与性能执行计划测试。
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
