# Nano-Agent 代码审查模板

> 审查对象: `MKB / NS2 pipeline priority dispatch`
> 审查类型: `mixed`
> 审查时间: `2026-08-15`
> 审查人: `Grok`
> 审查范围:
> - `docs/plan/new-start/NS2-pipeline-priority.md`
> - `docs/closure/new-start/NS2-pipeline-priority-closure.md`
> - `src/runtime/workflow/dispatch.py`
> - `src/runtime/workflow/runtime_core.py`
> - `src/runtime/intake/generation_construct.py`
> - `src/contracts/api/models.py`
> - `src/services/config_snapshots.py`
> - `src/persistence/migrations/011_process_dispatch_pools.sql`
> - `tests/unit/test_dispatch_*.py`
> - `tests/e2e/`（核对 NS2 车道旅程是否存在）
> 对照真相:
> - `docs/plan/new-start/NS2-pipeline-priority.md`（§2–§10 工作项 / 台账 / 硬闸）
> - `docs/closure/new-start/NS2-pipeline-priority-closure.md`
> - `.adocs/closure.md`（阶段 final 必含节与 close-type taxonomy）
> - `T-O-353..361` / `T-O-173` / `T-O-200`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 该实现把三池调度的**会计骨架**落进了 `mkb_processes` 列与 `claim_next` 同事务 admit，但生产路径上的生成运输仍按 NS1 的 CLI / omit=NI 运行；closure 把未接线、未测到的合同改写成了「100% 达成」。当前不应把 NS2 标为 completed，也不应关闭本轮 review。

- **整体判断**：orchestrator 占用会计主体成立，但 priority 双用未打通到 intake 执行层；closure 存在系统性虚假陈述与台账重映射。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. 生产默认 `omit compression_channel + priority=normal` 在 live GPU 打开时会 **admit 进 local 池占 GPU 槽，handler 却因 payload 缺字段回落到 `DEFAULT_COMPRESSION_CHANNEL=non-interactive` 打 Claude**；structurize / markdown / llm-clean 更是 CLI 优先，完全不读 `dispatch_pool`。
  2. salvage 不看 priority / 原池 / billing；`low` 失败仍可升 NI。这直接打穿 `T-O-355`「low 锁 GPU、禁止偷套餐」。
  3. closure / §11 执行日志把 P4–P6 工作项 ID 重映射后宣称全绿；AP 要求的 e2e 车道文件与并发 soak 文件不存在，mega「soak」是串行 `claim_next`。按 AP §10.4，不得标 `executed`。

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。

- **对照文档**：
  - `docs/plan/new-start/NS2-pipeline-priority.md`（全文，含 §2 In/Out、§3–§5 工作项、§8 台账、§10 硬闸、§11 执行日志）
  - `docs/closure/new-start/NS2-pipeline-priority-closure.md`
  - `docs/plan/new-start/NS2-pipeline-priority.todo.md`
  - `.adocs/closure.md`、`.adocs/code-review.md`
  - `docs/baseline/domain-truth/S02-task-api.md` / `S03-workflow-engine.md` / `S11-inference-runtime.md` / `S14-config-prompt-model-registry.md` / `S15-observability-reliability.md` / `D04-turso-physical-schema.md`（核对 P6-05 窄回填）
- **核查实现**：
  - `src/runtime/workflow/dispatch.py`、`runtime_core.py`、`runtime_materialize.py`、`worker.py`、`constants.py`
  - `src/runtime/intake/generation_construct.py`、`clean_preflight.py`、`core.py`、`vectorize.py`、`acceptance_scatter.py`
  - `src/services/config_snapshots.py`、`billing.py`、`prompt_profiles.py`、`registry.py`、`events.py`
  - `src/contracts/api/models.py`、`src/contracts/runtime/models.py`
  - `src/runtime/config.py`、`api/app.py`、`data/config/default.toml`
  - `src/persistence/migrations/001_initial.sql`、`011_process_dispatch_pools.sql`
  - `src/runtime/inference/facade.py`、`src/llm_adapters/local_vllm.py`
- **执行过的验证**：
  - `ls tests/e2e/test_ns2_dispatch_lanes.py tests/unit/test_dispatch_admit_soak.py` → 两文件均不存在
  - `rg "api-inference" src/` → 生产源码 0 命中
  - `rg "sleep\\(" src/runtime/workflow/worker.py src/runtime/workflow/dispatch.py src/runtime/intake/generation_construct.py` → 无等槽 sleep
  - `rg "NS2|dispatch_pool|channel_source|dispatch_admitted" docs/baseline/domain-truth/` → 无 NS2 窄回填命中
  - `git log --oneline` 核实 closure 引用的 `2f90a35` / `5b1e9ed` / `ff6b3e6` / `2e4d073` / `8604fc5` / `a1be4d0` / `9dc2357` / `d1d716d` / `a3d7355` 均在 `main` 历史上
  - `uv run pytest tests/unit/test_dispatch_policy.py tests/unit/test_dispatch_ddl.py tests/unit/test_dispatch_occupancy.py tests/unit/test_dispatch_claim.py tests/unit/test_dispatch_generation.py tests/unit/test_dispatch_embed_and_gates.py tests/unit/test_dispatch_mega.py tests/domain/test_architecture.py --tb=no` → `34 passed in 1.79s`（2026-08-15，本审查机）
  - `uv run pytest tests/unit tests/domain --tb=no -q` → 本审查机复现 closure 所称 unit/domain 全绿（约 298 项，17.85s）。这只证明**现有测试通过**，不证明 AP §8 场景已被那些测试覆盖。
- **复用 / 对照的既有审查**：
  - `none` — 本轮不读取、不采纳 `docs/code-review/new-start/NS1-reviewed-by-*.md` 或任何其他同事的分析报告。并行子代理只做文件与测试证据采集；以下判断全部由本审查人独立对源码与计划对账后写出。

### 1.1 已确认的正面事实

- `COMPRESSION_CHANNELS` 生产枚举已切到 `non-interactive` / `local-inference`；公开 `IntakeIngestPayload.compression_channel` 拒绝 `api-inference` / `cloud-inference` / `spark`。`src/` 中无 `api-inference` 字符串。
- `src/runtime/workflow/dispatch.py` 存在无 IO 的 `choose_pool` / `pool_kind`，四车道表与 `T-O-355` 在纯函数层一致：`urgent`/`high`→NI，`normal` 先 local 再溢 NI，`low` 永不返回 NI（除非 `explicit_channel`）。
- `011_process_dispatch_pools.sql` 给 `mkb_processes` 晋升了 `dispatch_pool` / `dispatch_admitted` / `dispatch_enqueued_at` 与部分索引，CHECK 拒绝 `cloud-inference`；无新 `CREATE TABLE`；物化 INSERT 不写这三列，依赖 DEFAULT `admitted=0`。
- `claim_next` 在同一写事务里先跑 `_admit_waiting_processes_tx` 再按 `dispatch_admitted=1` 领取；local queued 6 / running 2、embed queued 20 / running 8 在单测夹具上可观察到。
- embed 两行之间的领取序按 `available_at` 先到先得，不受 `priority_rank` 插队（`test_embed_fifo_claim_ignores_priority_rank`）。
- `admitted=0` 过 `deadline_at` 会以 `deadline-exceeded-before-start` 失败。
- `worker.run_once` 在 `claim_next is None` 时立即返回 `False`，workflow 内核无等槽 `sleep(`。
- Qwen `unsloth/Qwen3.8-27B-NVFP4` 在 `DEFAULT_BINDINGS` 中 `structured_generate` / `text_generate` 的 `priority=5`，Lightning 为 10。
- Settings 默认三池常数与 facade `max_in_flight=12` 已写入 `config.py` / `api/app.py`；`default.toml` 注明 facade 是末闸。
- `BillingPort` / `DefaultBillingService` 已存在且恒 `True`；`process.dispatch_admitted` 已登记进 `ALLOWED_TYPES`。
- `ProcessCommand.dispatch_pool` 字段存在，claim 时从行上拷出。
- 未实现真实 billing 扣减、未实现 `cloud-inference` 路由、未新建 required 表、未改 Task.priority 封闭集。这些 OOS 边被守住。

### 1.2 已确认的负面事实

- `generation_construct._compression_channel` 读的是 `state.payload.compression_channel`；omit 时回落到 `DEFAULT_COMPRESSION_CHANNEL = "non-interactive"`。handler **不读** `command.dispatch_pool`，也 **不读** snapshot L2。
- `_execution_payload` 把请求 payload 原样 dump；omit 后执行清单里通道为 `null`，与 L2 派生的 `local-inference` 脱节。
- `lsrag.structurize` 在 `_claude_cli` 存在时（生产默认 stub/subprocess）无条件走 CLI；`lsrag.transcribe_markdown` 只走 CLI；llm-clean 在无注入 llm 时走 CLI。三者都不看池或 priority。
- `_can_salvage_local_inference` 只检查错误码 + CLI 是否存在，不检查 priority、原池、billing。`INFERENCE_BACKPRESSURE` 在 salvage 闭集里。
- `_admit_waiting_processes_tx` 调用 `choose_pool` 时不传 `over_budget`、`explicit_channel`；`pool_kind(p_key)` 不传 snapshot。`DISPATCH_LOCAL_CHAR_BUDGET` 在生产 admit 路径上从未使用。
- `tests/e2e/test_ns2_dispatch_lanes.py` 与 `tests/unit/test_dispatch_admit_soak.py` 不存在。`test_dispatch_mega.py` 的「soak」是 `for worker_idx in range(50)` 串行 `claim_next`。
- closure `Close-type: close-with-known-issues`，缺 `.adocs/closure.md` 阶段 final 必含的 §4 Deferred A/B/C、§5 五态、§6 下游合同、§7 不可动清单；硬闸集合被换成另一套；证据无 run-time 时间戳。
- AP 要求的 S02/S03/S11/S14/S15/D04 窄回填未发生。`S03:866` 仍写「priority 只影响调度顺序」。
- `test_architecture.py` 没有 T71（无新 required 表 / `payload_extra` 禁 `dispatch_` 键）。该文件有 8 个 `test_*`，closure 写成「4 passed」。
- `api/app.py` 组装 `WorkflowRuntime` 时未注入 `billing=`，生产恒走 `DefaultBillingService`。
- admit/claim 使用 `dispatch.py` 模块常数，不读 `Settings.dispatch_*`。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 计划、closure、dispatch/admit/handler/DDL/测试/真相层均按文件读过 |
| 本地命令 / 测试 | `yes` | 本审查机复跑 NS2 相关 34 项全绿；全量 unit/domain 作为旁证另记 |
| schema / contract 反向校验 | `yes` | 011 SQL、001 CREATE、公开 Literal、occupancy SQL、claim ORDER BY 对照 |
| live / deploy / preview 证据 | `n/a` | 本轮不涉及部署；AP 也把真机 GPU 争用列为 defer |
| 与上游 design / QNA 对账 | `yes` | 对照 AP 内置冻结 `T-O-353..361` 与 S03/S11/D04 既有句，不重开 Q |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 生成运输与 admit 池脱节，默认路径占 GPU 打 Claude | `critical` | `correctness` | `yes` | 执行层必须以 `dispatch_pool`（或与之同步的派生通道）为运输 SSOT |
| R2 | closure / 执行日志系统性重映射并夸大收口 | `critical` | `docs-gap` | `yes` | 按 AP 原 ID 重写 closure，未完成项不得标 closed |
| R3 | salvage 不按车道，low 可升 NI | `critical` | `security` | `yes` | salvage 必须检查 priority=normal 且原池=local |
| R4 | 策略函数的 explicit / over_budget / snapshot 未进入 admit | `high` | `correctness` | `yes` | admit 必须消费与 `choose_pool` 合同一致的输入 |
| R5 | 确定性 vectorize 被当成 embed 占 8+20 | `high` | `correctness` | `yes` | `pool_kind` 必须带 snapshot；确定性路径 unpooled |
| R6 | 台账 T31–T38 / T51 / T60 / T70 / T71 未按合同落地，存在假绿 | `high` | `test-gap` | `yes` | 补 e2e 车道、并发 soak、攻击向量；禁止用纯函数冒充 e2e |
| R7 | 显式通道覆盖无安全审计 | `high` | `security` | `yes` | 显式 `compression_channel` 必须写 security audit，测试缺事件即失败 |
| R8 | embed 与 generate/unpooled 混在同一 ORDER BY，可被饿死 | `medium` | `correctness` | `no` | embed 独立选择器，或至少保证有 running 空位时不被 unpooled 无限插队 |
| R9 | Settings 三池常数不是 admit SSOT | `medium` | `platform-fitness` | `no` | admit/claim 读 Settings，或删除会误导运维的 settings 字段 |
| R10 | 真相层 P6-05 未窄回填 | `medium` | `docs-gap` | `no` | 按 AP §9.3 回填 S02/S03/S11/S14/S15/D04 |
| R11 | 事件 payload 与 occupancy waiting 定义漂移 | `low` | `protocol-drift` | `no` | 补 `channel_source`；waiting 只计需要池的行 |
| R12 | 公开注释与 DEFAULT 仍把 omit 写成 Claude 默认 | `low` | `docs-gap` | `no` | 与 R1 一并改合同文案 |

### R1. 生成运输与 admit 池脱节，默认路径占 GPU 打 Claude

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/generation_construct.py:92-119`：`_compression_channel` 在 payload 缺字段时返回 `DEFAULT_COMPRESSION_CHANNEL`；`_summary_transport` 据此选 CLI / live / deterministic。全程不读 `command.dispatch_pool`。
  - `src/services/prompt_profiles.py:37-39`：`DEFAULT_COMPRESSION_CHANNEL = "non-interactive"`。
  - `src/services/config_snapshots.py:393-420, 569-577, 188-190`：L2 对 omit+normal 派生 `local-inference` / `channel_source=priority`，但执行清单 dump 的是请求原字段（omit → `null`）。
  - `src/runtime/workflow/runtime_core.py:232-239`：admit 只看 `task.priority` + `live_inference` + billing，把 normal+live 送进 `local-inference`。
  - `src/runtime/intake/generation_construct.py:794-813, 423-431`：structurize 在 CLI 存在时无条件走 Claude；transcribe_markdown 只走 CLI。
  - `src/runtime/intake/clean_preflight.py:75-97`：llm-clean 在无注入 llm 时走 CLI。
  - `src/contracts/api/models.py:183-185` 注释仍写「None means the closed default: Claude `-p`」。
  - `tests/unit/test_compression_channel.py:82-86, 106` 把「omit → Claude」锁成回归。
- **为什么重要**：
  - NS2 的产品合同是 `priority` 双用：默认 normal 先 GPU（Qwen），满或不可用再 NI。如果执行层仍按 NS1 默认 Claude，则三池会计只是占槽，不调度模型。
  - live GPU 打开时，normal/low 生成步会占用 local running=2 的 GPU 配额，实际流量却打到 NI 套餐。这是配额与账单同时被击穿的形态。
- **审查判断**：
  - 这不是「注释过时」，而是三条权威（L2 / admit 池 / handler 运输）互相矛盾。`ProcessCommand.dispatch_pool` 已透传到 command，却是死字段。
  - 离线 `live_inference=false` 时，admit 会把 normal 溢到 NI，handler 也默认 NI，**碰巧一致**。这解释了为什么 NS1 e2e 仍能绿，但不能证明 dual-use 成立。
- **建议修法**：
  - handler 以 `command.dispatch_pool` 为运输 SSOT；omit 时不得再回落 NI。
  - 或把派生通道写回执行 payload，并删除 `DEFAULT_COMPRESSION_CHANNEL=non-interactive`。
  - structurize / markdown / llm-clean 必须按池选择 CLI vs local，禁止「有 CLI 就先 Claude」。
  - 改掉把 omit=Claude 锁死的单测，换成 omit+normal+live → local 的行上断言。

### R2. closure / 执行日志系统性重映射并夸大收口

- **严重级别**：`critical`
- **类型**：`docs-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - AP 预期 close-type：`closed-with-explicit-deferrals`（`NS2-pipeline-priority.md:742`）。closure 使用 `close-with-known-issues`，并在 §0 写「100% 达成」。
  - AP P4-01..P4-07 是分类 / 车道 / 超预算 / 按车道 salvage / 覆盖审计 / 改名 / 离线溢流。closure §1 与 AP §11.4 把 P4-01..P4-04 改写成 construct 接线、`ProcessCommand.dispatch_pool`、Qwen JSON 参数、16k 预算；P4-05..P4-07 从收口表消失。
  - AP P6-02 要求 `tests/e2e/test_ns2_dispatch_lanes.py`；P6-03 要求 `tests/unit/test_dispatch_admit_soak.py`（32 协程 × 32 轮）。两文件不存在。closure 把 P6 写成 mega 矩阵 + 串行 soak + 298 回归。
  - closure §3 硬闸被换成「无 api-inference / 同事务 admit / 容量 / FIFO / 零 sleep / salvage 一次 / facade 12」。AP §10.1 的 T61（NS1 金样）、T70（并发不超卖）、T71（无新表/extra）、T37（low 禁 NI）、T72（五态+A/B/C）被拿掉。
  - 阶段 final 缺 §4 Deferred A/B/C、§5 诚实五态、§6 下游合同、§7 ⛔ 清单。证据无四元组中的 run-time。
  - `todo.md` 将 P6-02/P6-03/P6-04/P6-05 标 `[x]`，与仓库事实不符。
  - closure 写 architecture「4 passed」；`tests/domain/test_architecture.py` 实际有 8 个 `test_*`。
- **为什么重要**：
  - AP §10.4 写明：退出硬闸 `degraded / 未观察` 不得标 `executed`；把 defer 写成 verified = 假绿。
  - owner 若只读 closure，会以为四车道、e2e、并发 soak、按车道 salvage 都已钉死。
- **审查判断**：
  - 这不是「close-type 选错一个词」的文档风格问题。工作项 ID、硬闸集合、测试文件名、完成态被一起改写，属于虚假陈述。
  - 骨架代码确实存在，但不能用「存在部分实现」为「全部 6 个 Phase 100% 达成」辩护。
- **建议修法**：
  - 按 AP 原 P1–P6 ID 重写 closure；未接线 / 未按场景测试的项标 `partial` 或 `missing`。
  - close-type 回到 `closed-with-explicit-deferrals` 或在实现补齐前不要标阶段收口。
  - 补齐五态、A/B/C defer、四元组 run-time。AP frontmatter / §11.7 的 `executed` 应降回 `executing` 直到硬闸按原定义可观察。

### R3. salvage 不按车道，low 可升 NI

- **严重级别**：`critical`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - AP P4-04 / T37 / §7.3.2：仅 `normal` 且原池 local 且错误 ∈ 闭集且 NI 可用且 billing 真；`low` 直接 fail-closed。
  - `generation_construct.py:121-123, 211-218`：`_can_salvage_local_inference` = 错误码 ∈ `_API_INFERENCE_SALVAGE_CODES` 且 `_claude_cli is not None`。
  - 同一闭集包含 `INFERENCE_BACKPRESSURE`（`:50`）。P3-05 明确 BACKPRESSURE 不得被 `low` salvage 成 NI。
  - 无测试以 `priority=low` 断言 CLI 调用次数为 0。现有 salvage 单测都不设 priority。
- **为什么重要**：
  - `low` 的产品含义是「只许用本地 GPU」。salvage 到 Claude 等于用低优先级任务消耗线上套餐。这是 AP 自己写的攻击向量。
- **审查判断**：
  - 在 R1 的默认 omit 路径上，handler 往往根本不走 local，salvage 较少被触发。但一旦客户端显式 `local-inference`，或 R1 被修成按池运输，这条就会在生产打穿。
  - 合同已经写明，测试台账也要求攻击向量。未实现就是缺口，不是「以后再收窄」。
- **建议修法**：
  - salvage 条件加上：task/command 的 priority 必须是 `normal`，`command.dispatch_pool` 必须是 `local-inference`，billing 必须为真，且尚未 salvage 过。
  - 增加 T37：low + local 失败 → CLI 0 次，错误码保持原 local 错误。

### R4. 策略函数的 explicit / over_budget / snapshot 未进入 admit

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `dispatch.py:97-162` 的 `choose_pool` 支持 `over_budget` 与 `explicit_channel`。
  - `runtime_core.py:191, 232-239`：`kind = pool_kind(p_key)`（无 snapshot）；`choose_pool(priority, "generate", local_queued=..., ni_queued=..., local_available=live_inference, ni_quota=billing.has_quota(...))`。
  - 全仓 `src/` 中，`over_budget=` 只出现在 `choose_pool` 定义与测试里。admit / construct / clean 入口没有正文长度与 `dispatch_local_char_budget` 的比较。
  - 显式 `compression_channel` 只进 L2，不进 admit。`low` + 显式 NI：admit 仍按 low 进 local（或等待），handler 却按 payload 打 NI（与 R1/R7 叠加）。
- **为什么重要**：
  - AP 把 `choose_pool` 定为后面一切 SQL / claim / handler 的唯一纯函数入口。如果 admit 不传关键参数，单测绿只证明「函数在真空里正确」。
  - 超预算溢流是防止长 json 堵死 2 路 Qwen 的合同。未接线则 `normal` 长文仍进 local。
- **审查判断**：
  - 策略模块本身写得清楚，问题在接线。把 P4-03 改写成「Qwen 参数守卫」不能覆盖这个缺口——adapter 的 `json_object` / 禁 `max_tokens` 是另一件事，而且 AP 原文 P4-03 根本不是它。
- **建议修法**：
  - admit 读取 L2 `compression_channel` / `channel_source` 作为 `explicit_channel`。
  - 在 structurize / llm-clean 分类入口按即将吐出的字符数设置 `over_budget`；C/markdown 不因输入长溢流。
  - 单测必须经过 `claim_next` 读 DB 行，而不是只调 `choose_pool`。

### R5. 确定性 vectorize 被当成 embed 占 8+20

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `dispatch.py:84-92`：无 snapshot 时 `lsrag.vectorize` 默认 `"embed"`；仅当 `l2.inference_mode == "deterministic"` 才 unpooled。
  - `runtime_core.py:191`：`kind = pool_kind(p_key)`，不传 snapshot。
  - Settings 默认 `live_inference=false`，snapshot 会写 `inference_mode=deterministic`，handler `vectorize.py:185-208` 走 `deterministic_embedding`。但行上已被 admit 进 embed。
  - `purge_generation` 共用 `process_key=lsrag.vectorize`，同样会被当成 embed。
  - AP P5-03 / T52：确定性向量化不占 8+20，离线应立即按 unpooled 领取。
- **为什么重要**：
  - 离线 / CI 默认路径会把本该立刻跑完的 hash embed 推进 8 running + 20 queued 的 GPU 会计。embed 池会被假负载占满，真 live embed 反而等待。
- **审查判断**：
  - 分类函数已经知道 snapshot 语义，admit 不用它。这是接线遗漏，不是「设计未定」。
- **建议修法**：
  - admit 读该 Process 的 config snapshot（或至少 `inference_mode`）再调 `pool_kind`。
  - 增加行上测试：`live_inference=false` 的 vectorize `dispatch_pool IS NULL` 且可被 unpooled 立即 claim。

### R6. 台账未按合同落地，存在假绿

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - 本审查机：NS2 相关 34 项全绿。绿的是现有文件，不是 AP §8 的场景集合。
  - `test_dispatch_mega.py:216` 标 NS2-T60，实际是纯 `choose_pool` 矩阵。AP T60 要求 e2e 创建四条 ingest，轮询 `mkb_processes`。
  - `test_dispatch_mega.py:260` 标 T61 / 被当 T70 用：50 次**串行** `claim_next`，种子是 4+8+6+12+5，不是 32 协程 × 20 local + 10 NI + 30 embed × 32 轮。
  - `test_dispatch_generation.py` 把 T30–T34 用在 construct 运输 / salvage / Qwen HTTP 形状上；AP 这几个 ID 是车道领取。
  - `test_dispatch_embed_and_gates.py` 把 T51 用在 20/8 容量上；AP T51 是「3 个 batch，occupancy running 最大=1」。T52/T53 被用在内存 `ConcurrencyGate` 上。
  - T07（BillingPort False → urgent 不 admit）、T37、T38、T54、T62、T71 无对应测试。
  - `tests/e2e/` 无任何 `dispatch_pool` / `dispatch_admitted` 断言。
- **为什么重要**：
  - AP §8.5：占用断言必须读 DB 行；禁止只断言内存 mock；soak 失败=超卖，不得用重试到绿掩盖；T37/T38 必须走攻击向量。
  - 当前测试能证明「策略函数」和「在手工插入的 Process 行上 admit/claim 大致守容量」。不能证明生产 intake 旅程按车道工作。
- **审查判断**：
  - 短途策略 / DDL / 部分 claim 单测是有价值的。把它们改名为 mega / soak / e2e 是假绿。
- **建议修法**：
  - 按 §8.6 原文补文件与场景，尤其 T37/T38/T60/T70/T71。
  - 测试名与 Test-ID 必须 1:1；禁止在注释里挪用 ID。

### R7. 显式通道覆盖无安全审计

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - AP P4-05 / T38 / §7.3.2：显式 `compression_channel` 强制该池，`channel_source=explicit`，必须写 `mkb_security_audit_events`（或已有 override 审计通道）；`low`+显式 NI 允许但必审计；无审计事件则测试失败。
  - `config_snapshots.py:572-573` 只写 L2 `channel_source=explicit`。`SecurityAuditWriter` 仅有 `write_denied`（`events.py:129+`），通道覆盖成功路径不调用。
  - `create_container` 构造 `ConfigSnapshotService` 时未注入应用级 `security_audit`（`api/app.py:246`）。
  - 公开面同一 business token 即可提交 `priority=low` + `compression_channel=non-interactive`。无额外授权。
  - 不存在查询审计表的 T38 测试。
- **为什么重要**：
  - 显式通道是调试覆盖，也是套餐逃逸口。没有审计就无法在生产中发现谁在用 `low` 打线上。
- **审查判断**：
  - 即便决定「本轮只记 L2 字段、审计留给后继」，也必须在 closure 里显式 defer，不能把 P4-05 从收口表抹掉还标 closed。
- **建议修法**：
  - 成功的显式覆盖写 security audit（action 例如 `config.compression_channel_override`），payload 只含 channel / priority / source，禁正文。
  - T38：low + 显式 NI，缺审计行即失败。

### R8. embed 与 generate/unpooled 混排，可被饿死

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `runtime_core.py:342-347`：单条 SQL，`ORDER BY CASE WHEN dispatch_pool='embed' THEN 0 ELSE priority_rank END DESC, available_at, deadline, created_at, process_uuid`。
  - unpooled / generate 的 `priority_rank` 为 100–400，embed 被压成 0，因此**任何可领取的 unpooled/generate 都先于所有 embed**。
  - unpooled 无 running cap。持续到达的 unpooled 会使 embed 有空位也领不到。
  - AP P3-02/P3-03：embed 除外走独立 FIFO。T-O-356：embed 不受 priority，独立会计。
- **为什么重要**：
  - 会计上 embed 与 generate 独立（local running=2 时 embed 仍可在谓词里被选中），但选择器把 embed 放在全局队尾。摄入高峰时向量化会被确定性步饿死。
- **审查判断**：
  - 两行 embed 之间的 FIFO 单测是对的，覆盖不了「与 generate 共存时的独立性」。
  - 标 medium 而非 blocker：空闲时功能可用；满载时公平性破坏，但不是「完全不能跑」。
- **建议修法**：
  - 分两段选择：先看哪几个池有 running 空位，embed 用自己的 FIFO，generate/unpooled 用 S03 序；或对 embed 使用独立 `LIMIT 1` 再与 generate 按稳定规则二选一（例如 round-robin / 有空位就先填 embed）。
  - 补 T54：local running=2 时下一次 claim 仍能领到已 admit 的 embed。

### R9. Settings 三池常数不是 admit SSOT

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `config.py:47-54` 暴露 `dispatch_*` 与 `inference_max_in_flight=12`。
  - `runtime_core.py` / `dispatch.py` 使用模块级 `DISPATCH_*` 常数。
  - `api/app.py:234-242` 把 Settings 传给 facade `capability_limits`，不传给 `WorkflowRuntime` admit。
  - 改 env `MKB_DISPATCH_EMBED_RUNNING` 只放松/收紧 facade，不改变 DB 占用。
- **为什么重要**：
  - 运维会以为改 Settings 就是改三池。实际 SSOT 在代码常数里。双闸还可能让 orchestrator 放行、facade 立刻 BACKPRESSURE（再触发 R3 salvage）。
- **审查判断**：
  - 默认值对齐，所以「开箱数字」没错。错的是可配置幻觉。
- **建议修法**：
  - admit/claim 读 Settings；或删除 Settings 上这些字段，避免两套数字。

### R10. 真相层 P6-05 未窄回填

- **严重级别**：`medium`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - AP P6-05 / §9.3 要求 S02 写 priority 双用、S03 Priority 节补生成池选择、S11 写 orchestrator=配额 SSOT / facade=末闸、D04 记 011 列、S14 记 L2 `channel_source`、S15 记新事件。
  - 对上述文件检索 `NS2` / `dispatch_pool` / `channel_source` / `dispatch_admitted`：无命中。
  - `S03-workflow-engine.md:866` 仍是「priority 只影响调度顺序」。
  - `D04` `mkb_processes` 节未列三列与 `ix_mkb_proc_dispatch_ready`。
- **为什么重要**：
  - 下游作者会继续按「priority 只排序」施工。这正是 AP 要求窄回填的原因。
- **审查判断**：
  - 不挡代码合并的正确性，但挡「阶段 final 文档收口」。todo 标 `[x]` 是假完成。
- **建议修法**：
  - 按 AP 只加附录级一句，不重写产品句、不重开 QNA。

### R11. 事件 payload 与 occupancy waiting 定义漂移

- **严重级别**：`low`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - P2-03：payload 为 `pool` / `priority` / `channel_source`。实现写 `{"dispatch_pool": ..., "priority": ...}`（`runtime_core.py:207,227,255,272`），无 `channel_source`。
  - P2-02 waiting = 分类需要池且 `admitted=0` 且 `ready`。`get_waiting_count`（`dispatch.py:58-68`）计所有 `ready AND admitted=0`，含尚未 admit 的 unpooled。`PoolOccupancy.waiting` 从未被查询填充。
  - `dispatch_enqueued_at` 只写不读；FIFO 用 `available_at` / `created_at`。
- **为什么重要**：
  - 观测与合同字段对不上，后继 billing / 看板会接错键。waiting 计数会把 unpooled 算进「等槽」。
- **审查判断**：
  - 不影响当前 admit 正确性（admit 不用 `get_waiting_count`）。属于合同漂移。
- **建议修法**：
  - 事件补 `channel_source`；waiting SQL 加上 `pool_kind` 需要池的谓词，或只计 `process_key` 属于 generate/embed 且 live 的行。

### R12. 公开注释与 DEFAULT 仍把 omit 写成 Claude 默认

- **严重级别**：`low`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `models.py:183-185`、`prompt_profiles.py:19-22, 39`。
  - 与 P1-03「无显式字段时不要再默认 NI」直接相反。
- **为什么重要**：
  - 调用方与后续作者会按注释传参。R1 的实现也在执行这些注释，而不是执行 AP。
- **审查判断**：
  - 单独看是文案；和 R1 一起看，说明默认通道合同根本没切过去。
- **建议修法**：
  - 与 R1 同一补丁改文案与 DEFAULT。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | `api-inference` → `local-inference` 硬切；预留 cloud 不路由 | `done` | 公开 Literal 与 `src/` 字符串已切；cloud 只在内部预留集合 |
| S2 | 纯函数占用 / 车道 / 分类 | `partial` | 函数在；admit 未消费 explicit/over_budget/snapshot |
| S3 | `mkb_processes` 三列 + 索引 | `done` | 011 存在且 fresh migrate 可观察到；001 CREATE 未回写但不挡 migrate 路径 |
| S4 | 同事务 admit + 分池 claim（生成看 priority，embed FIFO） | `partial` | 同事务与容量成立；embed 非独立选择器；确定性 vectorize 误入 embed |
| S5 | 生成步入池：md / structurize / construct / LLM clean | `partial` | 分类进 generate 池；执行仍 CLI 优先，不按池运输 |
| S6 | live vectorize 整段入 embed；确定性不入池 | `partial` | live 会计整段占 1 槽；确定性在 admit 侧仍入 embed |
| S7 | salvage 按车道；显式通道覆盖 + 审计 | `missing` | salvage 无车道；覆盖无审计 |
| S8 | normal json/clean 超预算溢 NI；local 不可用 normal 溢 NI | `partial` | 纯函数有；生产未算长度。offline normal 溢 NI 仅在 admit 层成立 |
| S9 | BillingPort 恒真；facade 升为末闸 | `partial` | 端口恒真但未注入可替换实例到组合根；facade 12 已接。T07 未做 admit 注入 |
| S10 | Qwen winner，Lightning 留 catalog | `done` | binding priority 5/10 与 bootstrap 断言成立 |
| S11 | 测试台账 + 真相窄回填 + NS2 closure | `partial` | 短途部分绿；e2e/soak/攻击向量/窄回填/合规 closure 未完成 |
| P1-01 | 枚举硬切 | `done` | T01/T02 主体成立 |
| P1-02 | 策略模块 | `done` | 纯函数可单测 |
| P1-03 | snapshot 派生通道 | `partial` | L2 已派生；执行 payload 未同步；T06 三场景未测全 |
| P1-04 | BillingPort | `partial` | 端口在；admit 会调用；False 注入无运行时测试 |
| P1-05 | Qwen winner | `done` | T08 成立 |
| P1-06 | 常数 / 末闸 | `partial` | 默认数字对；admit 不读 Settings |
| P2-01 | migration 011 | `partial` | fresh OK；无 010→011 夹具 |
| P2-02 | occupancy | `partial` | running/queued 对；waiting 定义过宽 |
| P2-03 | 事件登记 | `partial` | 类型已登记；payload 缺 `channel_source` |
| P2-04 | 物化未 admit | `done` | 默认 0 / digest 不含 pool |
| P3-01 | 同事务 admit 封顶 | `partial` | local 6/2 有测；NI 4/2 无独立测；over_budget/explicit 未进 |
| P3-02 | 分池 claim / 未 admit 不领 | `partial` | SELECT 要求 admitted=1；T23 不是「跳过 admit」原场景 |
| P3-03 | embed FIFO | `partial` | embed 之间 FIFO；与 generate 混排 |
| P3-04 | waiting deadline | `done` | 码与路径正确。副作用：一条过期使本次 `claim_next` 整次返回 None |
| P3-05 | 禁止 claim-then-sleep | `partial` | worker 不睡；无 `run_once` 静态扫描测试；BACKPRESSURE 仍可 salvage |
| P4-01 | process_key 分类 | `partial` | generate 集合对；确定性 C 仍 generate；T05 用了虚构 key |
| P4-02 | 车道表 | `partial` | 纯函数是；行上 T31–T34 未按原文落地 |
| P4-03 | 超预算 | `missing` | 仅纯函数；生产未比较字符数 |
| P4-04 | salvage 按车道 | `missing` | 见 R3 |
| P4-05 | 显式覆盖 + 审计 | `missing` | 见 R7 |
| P4-06 | receipt 改名 | `done` | hyphen `api-inference` 已离场；`salvage_from=local-inference` |
| P4-07 | local 不可用时 normal 溢 NI | `partial` | admit 层对；handler 对 omit 的「溢流」其实是旧默认 NI，不是按池溢流 |
| P5-01 | live vectorize 分类 | `partial` | 函数知道 live/det；admit 不用 snapshot |
| P5-02 | 整段占槽 | `partial` | 一 Process 一 orchestrator 槽；内部 batch 不再申请第二 orchestrator 槽。T51 原文（3 batch occupancy=1）未测。`retry_wait` 会提前释放槽 |
| P5-03 | 确定性跳过 | `missing` | 见 R5 |
| P5-04 | embed 独立、满员不溢 | `partial` | 会计独立、不溢 NI；选择器不独立。T54 缺失 |
| P6-01 | 短途台账 T01–T54 | `partial` | 一部分短途在；ID 大量挪用 |
| P6-02 | e2e 四车道 | `missing` | 文件不存在 |
| P6-03 | soak 竞态 | `missing` | 指定文件不存在；现有 soak 串行 |
| P6-04 | domain 守卫 T71 | `missing` | 无新表/extra 守卫 |
| P6-05 | 真相窄回填 | `missing` | 见 R10 |
| P6-06 | 合规 closure | `partial` | 文件在；类型/章节/硬闸/证据不合规 |
| CL-0 | 「6 个 Phase 完整交付、100% 达成」 | `stale` | 与仓库事实矛盾 |
| CL-P4 | `P4-01..P4-04` 按 AP 生成合同 closed | `stale` | 收口文本是重映射后的另一组工作 |
| CL-P6 | Mega/Soak/全量回归即 P6 完成 | `stale` | 不是 AP 的 P6 |

### 3.1 对齐结论

- **done**: 10
- **partial**: 24
- **missing**: 10
- **stale**: 3
- **out-of-scope-by-design**: 0（本表只列 in-scope）

> 这更像「调度会计骨架可运行，生成/embed 执行合同与测试台账未收口」，而不是 completed。离线 stub 下 NS1 旅程仍能走通，不能用来证明 NS2 车道已生产就绪。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 真实 billing / 套餐扣减 | `遵守` | 仅恒真端口；组合根甚至未注入可替换实例 |
| O2 | `cloud-inference` 适配器 / 路由 / 密钥 | `遵守` | 公开 Literal 拒绝；CHECK 拒绝写入 `dispatch_pool` |
| O3 | MiniMax 替换 Claude `-p` | `遵守` | NI 仍是 Claude CLI |
| O4 | urgent 插队老化；NI 为 overflow 保留位 | `遵守` | 未实现老化 |
| O5 | 重开 NS1 kernel / g0 向量 | `遵守` | 未见 g0 合同重开 |
| O6 | 新建 required 表；分布式锁 | `遵守` | 011 只 ALTER + INDEX |
| O7 | 修 NS1 VF V11 pyturso I/O | `遵守` | closure 仅记录，未当 NS2 回归红 |
| O8 | 整份 intake 占一槽；每 embed HTTP batch 占一槽 | `遵守` | orchestrator 按 Process 占槽；batch 不再申请第二 orchestrator 槽 |
| O9 | 修改 Task.priority 封闭集或公开新 lane 字段 | `遵守` | 公开仍是四值 priority + 可选 compression_channel |
| — | 把 VF V11 / 真机 GPU / billing 真接口写成已验证 | `误报风险` | closure 把 VF V11 列为 known issue 是对的；风险在于把**未完成的 in-scope** 也写成 verified |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：NS2 交付了可查询的三池列、同事务 admit 与一组短途单测，但 **priority 双用没有成为生产执行合同**；closure 不能作为「阶段已完成」的证据。本轮 review 不收口。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**：所有 generate 步（construct C、structurize、markdown、llm-clean）按 `dispatch_pool` 运输；omit+normal+live 必须走 local，而不是 DEFAULT NI。用行上 e2e 证明，而不是只改纯函数。
  2. **R3 + R7**：salvage 按车道（low 禁 NI）；显式通道覆盖写审计并补 T37/T38 攻击测试。
  3. **R4 + R5**：admit 传入 `explicit_channel` / `over_budget` / snapshot；确定性 vectorize 不再占 embed。
  4. **R2 + R6**：按 AP 原文补 `test_ns2_dispatch_lanes.py` 与并发 soak；重写 closure，撤销 100% / executed 表述。
- **可以后续跟进的 non-blocking follow-up**：
  1. R8 embed 独立选择器，避免被 unpooled 饿死。
  2. R9 Settings 与模块常数并成单一 SSOT。
  3. R10 真相层窄回填；R11 事件字段与 waiting 定义；R12 文案。
  4. `claim_next` 遇到一条 deadline 失败后仍应继续领取下一条，而不是整次返回 None。
  5. 010→011 升级夹具；`process_spec_digest` 在改 pool 后保持不变的显式断言。
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
