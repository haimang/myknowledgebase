# Nano-Agent 代码审查

> 审查对象: `MKB / NS2 — Pipeline Priority & Dispatch Capacity Orchestration`
> 审查类型: `code-review`
> 审查时间: `2026-08-15`
> 审查人: `Claude Sonnet 4.6 (Thinking)`
> 审查范围:
> - `src/runtime/workflow/dispatch.py`
> - `src/runtime/workflow/runtime_core.py`
> - `src/runtime/workflow/runtime_materialize.py`
> - `src/runtime/workflow/worker.py`
> - `src/runtime/intake/generation_construct.py`
> - `src/runtime/intake/vectorize.py`
> - `src/runtime/inference/facade.py`
> - `src/services/billing.py`
> - `src/services/config_snapshots.py`
> - `src/services/events.py`
> - `src/services/registry.py`
> - `src/persistence/migrations/011_process_dispatch_pools.sql`
> - `src/contracts/api/models.py`
> - `tests/unit/test_dispatch_policy.py`
> - `tests/unit/test_dispatch_claim.py`
> - `tests/unit/test_dispatch_ddl.py`
> - `tests/unit/test_dispatch_occupancy.py`
> - `tests/unit/test_dispatch_generation.py`
> - `tests/unit/test_dispatch_embed_and_gates.py`
> - `tests/unit/test_dispatch_mega.py`
> - `tests/unit/test_compression_channel.py`
> - `tests/domain/test_architecture.py`
> - `tests/e2e/` (全目录扫描)
> 对照真相:
> - `docs/plan/new-start/NS2-pipeline-priority.md`（action-plan）
> - `docs/closure/new-start/NS2-pipeline-priority-closure.md`
> - `docs/baseline/domain-truth/S03-workflow-engine.md`
> - `docs/baseline/domain-truth/S11-inference-runtime.md`
> - `docs/baseline/domain-truth/D04-turso-physical-schema.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> NS2 的核心调度机制（admit 事务原子性、三池容量界、FIFO 排序、未 admit 不可 claim）在代码层面整体正确，但存在一个高严重级别的生产正确性 Bug（低优先级 salvage 未拦截）、两个高严重级别的测试缺口（e2e 文件完全缺失、soak 并发假绿），以及 closure 文档本身与 action-plan 收口标准的实质性偏差。当前不应标记为 executed / closed。

- **整体判断**：`核心调度骨架实现正确，但存在一个可被利用的安全性 Bug 未被测试捕获，且多个 hard-gate 对应测试存在假绿或缺失，closure 文件格式与 AP 要求不符`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. `low` 优先级任务在 local-inference 失败时会 salvage 到 Claude `-p`（NI 通道），违反 T-O-355 / P4-04，且对应测试 NS2-T37 根本不存在——这是一个可被调用方利用的 NI 配额逃逸路径
  2. `tests/e2e/test_ns2_dispatch_lanes.py` 完全不存在，NS2-T60 / T62（行上 DB 可观察的四车道 e2e 测试）从未实现，closure 对此的 PASS 声明是虚假陈述
  3. "soak 浸泡测试"使用串行 `for` 循环，不具备任何并发性，NS2-T70（并发 admit 不超卖）的 PASS 声明等价于未测试

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/plan/new-start/NS2-pipeline-priority.md`（全文阅读，935 行）
  - `docs/closure/new-start/NS2-pipeline-priority-closure.md`（全文阅读，74 行）
  - `.adocs/code-review.md`（模板）
- **核查实现**：
  - `src/runtime/workflow/dispatch.py`（163 行，全文阅读）
  - `src/runtime/workflow/runtime_core.py`（838 行，阅读 L1–L420，关注 admit/claim 事务）
  - `src/runtime/intake/generation_construct.py`（1258 行，阅读 L1–L250，关注 salvage 路径）
  - `src/persistence/migrations/011_process_dispatch_pools.sql`（19 行，全文）
  - `src/runtime/inference/facade.py`（关注 `max_in_flight` 默认值与 `try_acquire`）
  - `api/app.py`（L230–L245，Facade 组合）
  - `src/runtime/config.py`（L54，`inference_max_in_flight` 配置）
  - `tests/unit/test_dispatch_claim.py`（512 行，全文阅读）
  - `tests/unit/test_dispatch_generation.py`（260 行，全文阅读）
  - `tests/unit/test_dispatch_embed_and_gates.py`（300 行，全文阅读）
  - `tests/unit/test_dispatch_mega.py`（368 行，全文阅读）
  - `tests/domain/test_architecture.py`（扫描）
  - `docs/baseline/domain-truth/S03/S11/D04/S14`（搜索 NS2 回填痕迹）
- **执行过的验证**：
  - `uv run pytest tests/unit/test_dispatch_*.py tests/unit/test_compression_channel.py -v` → 41 passed in 1.49s
  - `uv run pytest tests/unit/ tests/domain/ -v` → 298 passed in 16.19s
  - `ls tests/e2e/test_ns2*` → NOT FOUND
  - `ls tests/unit/test_dispatch_admit_soak*` → NOT FOUND
  - `grep -n "max_in_flight" src/runtime/inference/facade.py` → L125: `max_in_flight: int = 8`（类内默认值）；config.py 生产默认 12
  - `grep -n "low\|salvage\|priority" src/runtime/intake/generation_construct.py` → salvage 函数无优先级检查
  - `grep -n "dispatch_pool\|local-inference\|011\|admit" docs/baseline/domain-truth/S03-workflow-engine.md` → 0 条 NS2 相关命中
- **复用 / 对照的既有审查**：
  - 无——本轮审查完全独立，所有结论来自本人代码阅读和命令执行，不参考其他 reviewer（grok / GPT / sonnet prior）的分析

### 1.1 已确认的正面事实

- `choose_pool()` 纯函数逻辑正确：`urgent`/`high` 锁 NI，`normal` 先 local 溢 NI，`low` 锁 local，`over_budget=True` 对 `normal` 正确触发 NI 溢流，`low` 忽略 `over_budget`（永不 NI）。`dispatch.py:L97–L162`
- `_admit_waiting_processes_tx` 在 `claim_next` 同一写事务内调用（`runtime_core.py:L290, L320`），admit 前于 claim SELECT（L320 < L328），满足 T-O-359 同事务原子性要求
- claim_next 的 WHERE 子句硬性要求 `dispatch_admitted = 1`（`runtime_core.py:L334`），彻底切断"未 admit 行被领取"路径，T-O-361 contractual boundary 成立
- embed FIFO 在同池竞争中正确实现：`CASE WHEN dispatch_pool='embed' THEN 0 ELSE priority_rank END DESC` 使同是 embed 的行第一键相等（均为 0），由 `available_at ASC` 决定领取序，无优先级权重渗入。`runtime_core.py:L342–L346`
- `deadline-exceeded-before-start` 错误码在 claim 事务开头、admit 之前即处理过期进程（`runtime_core.py:L292–L317`），且不过滤 `dispatch_admitted`，waiting 状态下过期的进程也能被正确失败
- DDL 011 的 CHECK 约束正确拒绝 `cloud-inference`（`011_process_dispatch_pools.sql:L6–L7`）；`dispatch_admitted NOT NULL DEFAULT 0` 正确；部分索引 `IF NOT EXISTS` 可重复执行
- `worker.run_once()` 无任何 `sleep` 调用，池满时立即返回 `False`（`worker.py:L48–L50`），T-O-359 "禁止 claim-then-sleep" 成立
- `InferenceFacade` 在生产组合（`app.py:L234–L245`）中 `max_in_flight` 传入 `settings.inference_max_in_flight`（config.py 默认 12），`capability_limits` 按三池 running cap 拆分（embed=8, structured_generate=2, text_generate=2），生产配置符合 P1-06
- Qwen 在 `DEFAULT_BINDINGS` 中 `priority=5`，Lightning `priority=10`（`registry.py:L128–L132`），查询 `ORDER BY priority ASC` 使 Qwen 自然胜出，P1-05 正确
- `pool_kind("lsrag.vectorize", {"l2": {"inference_mode": "deterministic"}})` 返回 `"unpooled"`，动态分类基于 snapshot 正确实现（`dispatch.py:L84–L92`）
- `IntakeIngestPayload.compression_channel` 类型为 `Literal["non-interactive", "local-inference"] | None`，隐式拒绝 `api-inference` / `cloud-inference` / `spark`；架构守卫测试 `test_no_api_inference_in_production_or_test_sources` 存在且通过

### 1.2 已确认的负面事实

- **`generation_construct.py` 的 `_can_salvage_local_inference` 方法不检查 task priority**，只检查错误码是否在 salvage 集合中（`generation_construct.py:L121–L122`）。`low` 优先级任务在 local-inference 失败时会无条件 salvage 到 Claude `-p`（NI 通道）
- **`tests/e2e/test_ns2_dispatch_lanes.py` 文件不存在**，`ls tests/e2e/test_ns2*` 输出 `NOT FOUND`。NS2-T60 和 NS2-T62 从未实现
- **`tests/unit/test_dispatch_admit_soak.py` 文件不存在**。AP 明确列出此文件名（§3 P6-03），实际 soak 内联于 `test_dispatch_mega.py`，且使用串行 `for` 循环（`test_dispatch_mega.py:L352`），不具并发性
- **NS2-T37（low 失败不 salvage）和 NS2-T38（覆盖必有审计事件）测试均不存在**：`test_dispatch_generation.py` 仅有 4 个测试，无一覆盖这两个安全性验证项
- **domain-truth 窄回填（P6-05）未完成**：`grep` 扫描 S03 / S11 / D04 / S14 均无任何 NS2 相关内容（dispatch_pool、local-inference、channel_source、011 等关键词）命中
- **closure 的 close-type 与 AP §10.5 要求不符**：closure 写的是 `close-with-known-issues`，AP §10.5 明确要求 `closed-with-explicit-deferrals`；closure 完全没有 Deferred ledger（A/B/C 分类）章节
- **域架构守卫测试缺少两项 NS2-T71 要求的守卫**：`test_architecture.py` 缺失"无新 CREATE TABLE"检查和"payload_extra 无 dispatch_* 键"检查
- **`get_waiting_count()` 语义不准确**：`dispatch.py:L65` 统计 `status='ready' AND dispatch_admitted=0` 的所有行，不区分"需要池但未获准入"与"刚物化尚未经过 admit 循环的 unpooled 进程"，会造成 waiting 计数偏大

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 直接阅读所有关键实现文件，逐行确认 salvage 路径、admit 事务序列、claim WHERE 子句、ORDER BY 逻辑 |
| 本地命令 / 测试 | `yes` | 实际运行全量 unit+domain（298 passed），验证 test 文件存在性，grep 搜索 salvage 逻辑和 domain-truth 回填 |
| schema / contract 反向校验 | `yes` | 验证 011 DDL 的 CHECK 约束、IntakeIngestPayload Literal 类型、events ALLOWED_TYPES |
| live / deploy / preview 证据 | `no` | 无真实 GPU 环境，仅静态代码审查 + 本地 SQLite 测试 |
| 与上游 design / QNA 对账 | `yes` | 与 T-O-353..361 冻结决策逐一核对；与 AP §8 测试台账逐项比对 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | `low` 优先级 salvage 未拦截——NI 配额逃逸路径 | `high` | `correctness` + `security` | `yes` | 在 salvage 判断中加 priority 检查，补 NS2-T37 |
| R2 | `tests/e2e/test_ns2_dispatch_lanes.py` 完全缺失 | `high` | `delivery-gap` | `yes` | 实现 e2e 测试，或在 closure 中诚实 defer |
| R3 | Soak 测试串行执行——并发竞态从未被测试 | `high` | `test-gap` | `no` | 改为 `asyncio.gather` 并发，N≥32 |
| R4 | NS2-T37 / T38 测试缺失——两个安全性测试项 | `high` | `test-gap` | `yes` | 补全 low 拦截测试和显式通道审计测试 |
| R5 | closure close-type 错误 + Deferred ledger 缺失 | `medium` | `delivery-gap` + `docs-gap` | `no` | 改为 `closed-with-explicit-deferrals`，补 §4 A/B/C |
| R6 | embed 进程在混合竞争中被 generate 长期饿死的风险 | `medium` | `correctness` | `no` | 评估影响，必要时独立 embed worker 或轮询权重 |
| R7 | 域架构守卫（NS2-T71）覆盖不完整 | `medium` | `test-gap` | `no` | 补充无新表和 payload_extra 无 dispatch_* 守卫 |
| R8 | domain-truth 窄回填（P6-05）未完成 | `medium` | `delivery-gap` + `docs-gap` | `no` | 完成 S03/S11/D04/S14/S15 附录条目 |
| R9 | `get_waiting_count()` 语义不准 | `low` | `correctness` | `no` | 限定为 pooled 进程或补充注释说明 |
| R10 | `InferenceFacade` 类内默认值与生产配置不一致 | `low` | `platform-fitness` | `no` | 统一 facade.py 默认值为 12 |

---

### R1. `low` 优先级 salvage 未拦截——NI 配额逃逸路径

- **严重级别**：`high`
- **类型**：`correctness` + `security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `generation_construct.py:L121–L122`：`_can_salvage_local_inference` 方法体为 `return exc.code in _API_INFERENCE_SALVAGE_CODES and getattr(self, "_claude_cli", None) is not None`，**无任何 priority 检查**
  - `generation_construct.py:L211–L225`：`_complete_construct_summaries` 的 except 块仅凭上述函数决定是否 salvage，路径中不读取 `command.dispatch_pool` 或 task priority
  - `tests/unit/test_dispatch_generation.py`：全部 4 个测试均无 low 优先级场景；NS2-T37 对应测试文件和函数根本不存在
  - AP §4.4 P4-04："`low` 直接 fail-closed"；AP §7.3 安全威胁模型第 2 条："low salvage 到 NI / 上 cloud → 攻击：偷套餐"
- **为什么重要**：
  - 调用方可以通过将文档标记为 `low` 优先级等待 local-inference 自然失败来消耗 NI（Claude `-p`）配额，绕过"low 锁 GPU"的配额策略。这是 §7.3 安全威胁模型第 2 条的直接变体，不需要显式设置 `compression_channel=non-interactive`，只需等待 local 报错即可穿越通道边界
  - Closure Gate 6（"salvage once & receipt"）的验证测试使用默认（normal）优先级，对 low 的行为完全未验证；Gate 声明 PASS 但实际 low 场景没有测试钉桩
- **审查判断**：
  - 确认为生产安全性 Bug，且对应测试（NS2-T37）从未实现。Closure 对 Hard-gate 的 PASS 声明在 low 场景下是无效的
- **建议修法**：
  - 在 `_can_salvage_local_inference` 中增加 priority 感知：通过 command.dispatch_pool 或从 state 读取优先级，`low` 直接返回 `False`
  - 补充 NS2-T37 测试：low priority + SALVAGE_CODES 错误码 → 断言 `cli.requests == []`（CLI 未被调用），且 MkbError 被重新抛出

---

### R2. `tests/e2e/test_ns2_dispatch_lanes.py` 文件完全缺失

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `ls tests/e2e/test_ns2*` → `NOT FOUND`（直接命令验证）
  - AP §3 P6-02 明确要求："🆕 `tests/e2e/test_ns2_dispatch_lanes.py`"；§8 台账 NS2-T60（四车道行上 pool/admitted 可见）和 NS2-T62 均标注来源为此文件
  - closure §1 工作项收口表将 P6-01..P6-03 归入 `tests/unit/test_dispatch_mega.py 2 passed`，将四车道 e2e 包含在内——但该 unit 文件没有任何 e2e DB 行查询
  - AP §8.5 测试保真："占用断言必须读 DB 行（`dispatch_pool` / `dispatch_admitted` / status），禁止只断言内存 mock 返回值就算 e2e"
- **为什么重要**：
  - NS2-T60 要求的是行上可观察性——通过真实 DB 查询确认 `dispatch_pool` / `dispatch_admitted` 列的状态流转。这是整个 NS2 最重要的集成正确性证明。缺少这个测试，admit→claim→running 的状态链在端到端层面未被证明
  - Closure 对 P6-02 标记 `✅ closed` 是虚假陈述，对应交付物不存在
- **审查判断**：
  - Delivery 缺口，同时是 closure 诚实性问题。不应允许关闭
- **建议修法**：
  - 要么按 AP §8.6 NS2-T60 实现 e2e 测试（注入慢 fake generate，4 优先级 ingest，轮询 DB 验证列状态）
  - 要么在 closure 中将 P6-02 诚实标为 `deferred`，撤回 `✅ closed` 声明，移入下一迭代

---

### R3. Soak 测试串行执行——并发竞态从未被测试

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `test_dispatch_mega.py:L350–L355`：
    ```python
    claimed_processes = []
    for worker_idx in range(50):
        claimed = await runtime.claim_next(f"soak-worker-{worker_idx}")
    ```
    这是纯串行的 `for` 循环，每次 `await` 完成后才执行下一次，不存在任何并发
  - AP §8.6 NS2-T70："32 个 coroutine 同时 `claim_next`"，§4.6 P6-03："并发 `claim_next` × N"
  - AP §9.1 风险项："多 worker 超卖 → 计数不准会导致 GPU/套餐打穿"，评级 `high`
- **为什么重要**：
  - SQLite 写事务在单协程串行执行时不存在竞态。这个测试仅证明"串行逻辑正确"，不证明"并发时不超卖"。真实生产是多个 worker 进程并发调用 `claim_next`，SQLite 写锁竞争是需要验证的核心风险
  - Closure Gate 2（"同事务原子 admit"）和 Gate 3（"Pool capacity bounds"）的 PASS 声明建立在串行测试上，对真实并发场景保证力度为零
- **建议修法**：
  - 将 `test_soak_mixed_concurrent_claims` 改为 `asyncio.gather(*[runtime.claim_next(f"soak-worker-{i}") for i in range(32)])`
  - 在 gather 之后断言各池 running ≤ caps，且无任何一次超卖时成功的 claim

---

### R4. NS2-T37 / NS2-T38 测试缺失——两个安全性测试项

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`yes`（与 R1 联动）
- **事实依据**：
  - `test_dispatch_generation.py` 全文共 4 个测试函数，均无 low 优先级或 explicit 通道审计场景
  - AP §8 台账 NS2-T37："low 失败不 salvage（攻击：偷套餐）"；NS2-T38："显式通道覆盖必有审计事件"；两者均为 `high` 风险
  - AP §8.5 测试保真："安全项 NS2-T37 / T38 必须走攻击向量（low salvage、无审计覆盖）"
- **为什么重要**：
  - NS2-T37 的缺失是 R1 Bug 能在 CI 中存活的直接原因。这两项是 §7.3 安全威胁模型的核心钉桩，缺少它们意味着安全合同完全无测试保障
- **建议修法**：
  - 补 NS2-T37：低优先级 + local-inference 失败 → 断言 CLI 调用次数=0
  - 补 NS2-T38：explicit `compression_channel="non-interactive"` + low priority → 断言 `channel_source="explicit"` 且 security audit 事件存在

---

### R5. closure close-type 错误 + Deferred ledger 缺失

- **严重级别**：`medium`
- **类型**：`delivery-gap` + `docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `NS2-pipeline-priority-closure.md:L5`：`Close-type: close-with-known-issues`
  - AP §10.5 要求：`close-type=closed-with-explicit-deferrals`；AP §10.4："不得标 full-close"且必须使用 `closed-with-explicit-deferrals`
  - AP §10.5 closure 必含 §4 Deferred ledger（A=OOS；B=本阶段主动；C=handoff）；实际 closure 仅有 Known Issues 一条 VF V11，billing / cloud / true-GPU soak / urgent 老化等 deferred 项完全未登记
- **建议修法**：
  - 将 `close-type` 改为 `closed-with-explicit-deferrals`
  - 补充 §4 Deferred ledger：A=`cloud-inference 路由`, `MiniMax 换绑`, `urgent 老化`；C=`T-O-357 billing AP`, `真机 GPU soak（交业主）`, `VF V11 harness（交 NS1 charter）`

---

### R6. embed 进程在混合竞争中被 generate 长期饿死的风险

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `runtime_core.py:L342–L346` ORDER BY：`CASE WHEN p.dispatch_pool = 'embed' THEN 0 ELSE p.priority_rank END DESC`
  - 当 `embed_can_run=1` 且 `local_can_run=1` 同时成立时，一个 normal generate（priority_rank=200）和一个 embed 进程同时进入候选集，ORDER BY 第一键：generate=200 > embed=0，generate 先被领取
  - `test_dispatch_embed_and_gates.py::test_embed_pool_concurrency_bounds_and_fifo` 仅测试纯 embed 场景（无 generate 竞争），未覆盖混合竞争
- **为什么重要**：
  - AP §5.5："embed 不和生成抢会计"——会计层面独立，但 ORDER BY 的竞争优先级使 embed 在请求层面仍被 generate 抑制。在持续高 generate 负载下，embed 进程可能被持续延迟
- **建议修法**：
  - 短期：补充混合场景测试，量化 embed 延迟行为
  - 长期：评估是否需要独立 embed worker 路径或轮询权重防止系统性饿死

---

### R7. 域架构守卫（NS2-T71）覆盖不完整

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - AP §3 P6-04："守卫：派发列存在；payload_extra 无 dispatch_*；无新 CREATE TABLE"
  - `test_architecture.py` 仅验证无 `api-inference` 字符串；无"无新 CREATE TABLE"断言，无"payload_extra 键名不含 dispatch_"断言
- **建议修法**：
  - 在 `test_architecture.py` 新增：解析所有 migration SQL，统计 `CREATE TABLE` 语句，断言 011 后业务表数量不增加
  - 新增：扫描所有写入 `payload_extra` 的代码路径，断言键名不含 `dispatch_` 前缀

---

### R8. domain-truth 窄回填（P6-05）未完成

- **严重级别**：`medium`
- **类型**：`delivery-gap` + `docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `grep "dispatch_pool\|local-inference\|channel_source\|011\|admit" docs/baseline/domain-truth/S03-workflow-engine.md` → 0 条 NS2 相关命中
  - 同样搜索 S11、D04、S14 → 同样 0 条 NS2 命中
  - AP §3 P6-05 要求 S03/S11/S02/D04/S14/S15 都有附录级回填；Closure 对 P6-05 未提及
- **建议修法**：
  - S03 Priority 节补"生成池选择"一句；S11 补 orchestrator 为配额 SSOT、facade 为末闸；D04 附录登记 011 三列；S14 记录 L2 `channel_source`；S15 记录新事件 `process.dispatch_admitted`

---

### R9. `get_waiting_count()` 语义不准

- **严重级别**：`low`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `dispatch.py:L65`：`WHERE status = 'ready' AND dispatch_admitted = 0`——包含了刚物化但尚未经过 admit 循环的 unpooled 进程，它们下一次 claim_next 即会立即被 admit=1，实际上不"等待"
- **建议修法**：
  - 将查询限定为"需要池的 waiting 进程"，增加 process_key 范围过滤；或在注释中明确说明这是包含 unpooled 瞬态的宽松定义

---

### R10. `InferenceFacade` 类内默认值与生产配置不一致

- **严重级别**：`low`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `facade.py:L125`：`max_in_flight: int = 8`（类内默认）
  - `config.py:L54`：`inference_max_in_flight: int = Field(default=12, ...)`（生产配置默认）
  - 生产路径（`app.py:L236`）通过 settings 正确传入 12，实际行为正确；但直接实例化 `InferenceFacade()` 的单元测试会使用 8 而非 12
- **建议修法**：
  - 将 `facade.py:L125` 默认值从 `8` 改为 `12`，或删除默认值强制调用方显式传入

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | `api-inference` → `local-inference` 硬切；cloud 枚举预留不路由 | `done` | models.py Literal 正确；架构守卫通过；COMPRESSION_CHANNELS 正确 |
| S2 | 纯函数：占用函数、车道表、注入单位、process_key 分类 | `done` | dispatch.py 实现完整，策略单测 7 项覆盖四车道边界 |
| S3 | `mkb_processes` 列晋升三列 + 索引 | `done` | 011 DDL 正确；CHECK 约束正确；部分索引存在 |
| S4 | 同事务 orchestrator admit + 分池 claim（生成看 priority，embed FIFO） | `done` | `_admit_waiting_processes_tx` 在同一写事务内；claim WHERE 强制 admitted=1；embed ORDER BY 正确 |
| S5 | 生成步入池：transcribe / structurize / construct / LLM clean | `done` | pool_kind() 分类表正确包含所有 LLM 步 |
| S6 | live vectorize 整段入 embed 池；确定性向量化不入池 | `done` | 动态分类正确；vectorize.py 不在 batch 层重申请槽 |
| S7 | salvage 按车道重写；显式通道覆盖 + 审计 | `partial` | salvage 存在 low-priority 逃逸 Bug（R1）；显式通道 channel_source 写入正确，但审计事件写入未经测试验证（R4） |
| S8 | `normal` json/clean 超预算 → NI；`low` 仍 local | `done` | choose_pool(over_budget=True) 逻辑正确 |
| S9 | BillingPort 恒真；全局 facade 闸上调为末闸 | `done` | billing.py 存在；末闸逻辑正确 |
| S10 | Qwen 升 winner；Lightning 留 catalog | `done` | registry.py priority 顺序正确 |
| S11 | 测试台账 + domain-truth 窄回填 + closure | `partial` | 测试台账有多项缺失（R2/R3/R4）；domain-truth 窄回填完全缺失（R8）；closure 格式不符（R5） |

### 3.1 对齐结论

- **done**: `8`
- **partial**: `2`（S7：salvage 安全合同存在 Bug；S11：测试缺失 + 文档缺失 + closure 格式错误）
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像"核心调度合同与 DDL 骨架完成，但 salvage 安全合同存在 Bug 且无测试钉桩，e2e 交付物与 closure 声明存在实质性偏差"，而不是一个可以标记为 `executed` 的完成状态。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 真实 billing 接口 / 套餐计量 / 扣减 | `遵守` | billing.py 仅实现 BillingPort 协议恒真 |
| O2 | `cloud-inference` 适配器、路由、密钥 | `遵守` | CHECK 约束拒绝 cloud-inference 写入；代码中无 cloud 路由 |
| O3 | MiniMax M3 替换 Claude `-p` | `遵守` | NI 通道仍是 Claude -p CLI，无 MiniMax 接线 |
| O4 | urgent 插队老化 | `遵守` | priority_rank DESC 提供队头语义，无老化实现 |
| O5 | 重开 NS1 kernel / prompt 簇 | `遵守` | 无相关改动 |
| O6 | 新建 required 物理表；分布式跨进程锁 | `遵守` | 011 是列晋升，无新 CREATE TABLE |
| O7 | 修 NS1 遗留 pyturso disk I/O | `遵守` | VF V11 在 closure Known Issues 中标注为 pre-existing |
| O8 | 整份 intake 当一个槽 | `遵守` | 仅 generate 步（Process 单位）入池 |
| O9 | 修改 Task.priority 封闭集或公开新 lane 字段 | `遵守` | priority 四值集合未变，无新字段 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`NS2 调度合同的核心机制（admit 原子性、三池会计、未 admit 硬隔离、embed FIFO）代码层面实现正确，但存在一个可被调用方利用的安全性 Bug（R1），两个 closure 声称 PASS 但交付物不存在或从未真正测试的 hard-gate 项（R2/R3），以及多项测试和文档缺失。当前不满足 AP §10 Definition of Done 的收口标准`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**：修复 `generation_construct.py` 中 `low` 优先级 salvage 未拦截 Bug，在 salvage 判断中加入 priority 检查，`low` 直接 fail-closed
  2. **R2**：要么实现 `tests/e2e/test_ns2_dispatch_lanes.py`（NS2-T60/T62 DB 行可观察 e2e 测试），要么在 closure 中将 P6-02 诚实标为 `deferred` 并撤回 `✅ closed` 声明
  3. **R4**：补充 NS2-T37（low 禁 salvage）+ NS2-T38（explicit 覆盖必有审计事件）测试，这两项是安全合同的钉桩
- **可以后续跟进的 non-blocking follow-up**：
  1. **R3**：将 soak 测试改为真实并发（`asyncio.gather`，N=32），消除串行假绿
  2. **R5**：修正 closure close-type 为 `closed-with-explicit-deferrals`，补充 Deferred ledger A/B/C 章节
  3. **R6**：评估 embed 在高 generate 负载下的饿死风险，决策是否需要独立 embed worker
  4. **R7**：在 `test_architecture.py` 补充无新表和 payload_extra 无 dispatch_* 两项守卫
  5. **R8**：完成 S03/S11/D04/S14/S15 domain-truth 窄回填
  6. **R9**：修正或注释 `get_waiting_count()` 语义
  7. **R10**：统一 `InferenceFacade` 类内默认值与 config 默认值
- **建议的二次审查方式**：`same reviewer rereview`（针对 R1 修复和 R2 交付物验证）
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并更新代码与测试。R1（low salvage 逃逸）为最高优先级，建议优先修复并补充 NS2-T37 测试，随后补充 R2 的 e2e 交付物或诚实 defer。
