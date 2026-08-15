# NS2 第 1 轮跨 Reviewer 统一台账（verified-findings）

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 初步修复方案）。
> **谁写**：**实现者 / 合并人**（不是某一位 reviewer）。
> **何时用**：3 份独立 NS2 审查制品合并去重 + 对照当前真实代码独立复核。

---

> **元信息（置顶 · 必填）**
>
> | 字段 | 值 |
> |------|----|
> | **审查标的** | `NS2 pipeline priority dispatch` |
> | **审查阶段 / 轮次** | `第 1 轮合并` |
> | **合并 / 核查人（实现者）** | `Grok` |
> | **合并日期** | `2026-08-15` |
> | **文档状态** | `resolved` |
>
> **审查来源锚定（被合并的 reviewer 制品 — 必须逐份列全）**：
> - `docs/code-review/new-start/NS2-reviewed-by-GPT.md` — `critical / 8 findings`（R1–R4/R7/R8 blocker）
> - `docs/code-review/new-start/NS2-reviewed-by-grok.md` — `critical / 12 findings`（R1–R7 blocker）
> - `docs/code-review/new-start/NS2-reviewed-by-sonnet.md` — `high / 10 findings`（R1/R2/R4 blocker）
>
> **对照真相（逐条 re-verify 时回看的源）**：
> - `docs/plan/new-start/NS2-pipeline-priority.md`（P1–P6 / T01–T72 / §10 硬闸）
> - `docs/closure/new-start/NS2-pipeline-priority-closure.md`
> - `.adocs/closure.md`
> - 代码根：`src/runtime/workflow/{dispatch,runtime_core,runtime_outcome,runtime_materialize}.py`、`src/runtime/intake/{generation_construct,clean_preflight,vectorize}.py`、`src/services/{config_snapshots,events,billing}.py`、`api/app.py`、`011_process_dispatch_pools.sql`、`tests/{unit,domain,e2e}/**`

---

## 0. 合并方法与核查纪律

- **合并范围**：3 份独立审查全部 finding 平铺（GPT 8 + Grok 12 + Sonnet 10 = 30 条原始 finding）。
- **核查纪律（硬）**：
  1. reviewer 的结论仅作线索。每条判 `valid` 的项，均由实现者亲自 Read / grep 当前真实代码坐实，关键证据带 `file:line`。
  2. 与任一方冲突，以实测为准。
  3. 已纠正的跨-reviewer 误报在 §4.3 带证据列出。
  4. 严重级别取多方最严；同一问题被多方提及合并为一条统一编号。
- **统一编号前缀**：`V`（verified），全文一致。

### 0.1 复核判定（verdict）图例

| verdict | 含义 |
|---------|------|
| `valid` | 属实，需处理 |
| `valid-edge` | 属实但仅边界/条件态触发（happy-path 已绿）|
| `valid-conditional` | 属实但本环境不复现；按防御性处理 |
| `valid-owner-gated` | 属实但归 owner 动作（sign-off / deploy / 复测）|
| `valid-pre-existing` | 属实但 base 即存在，非本阶段引入 |
| `valid-by-design` | 现象属实但为既定设计 |
| `valid(子项 overstated)` | 主项真，个别子断言过度 |
| `stale-rejected` | 不成立：读了陈旧/已删的代码或误解 |
| `INVALID` | 不成立：凭空指控，无代码依据 |

### 0.2 处置（disposition）图例

| 处置 | 含义 |
|------|------|
| `fix` | 本轮修复（必配 falsifiable 测试）|
| `partial-fix` | 部分修复 + 余项 defer |
| `defer-with-rationale` | 有理由后延（带 reopen 触发器 + 承接位置）|
| `deferred-by-owner` | 归 owner session |
| `acknowledge` | 已修 / 无需改动（仅记录）|
| `stale-rejected` | 带证据驳回，不改代码 |

### 0.3 严重级别图例

`critical | high | medium | low | info`（取多方最严）。

### 0.4 Finding 三类归属（class）图例

| 归属类 | 标记 | 本阶段义务 |
|--------|------|------------|
| **真 deferred** | `[true-deferred]` | 登记承接；本阶段不修是诚实的 |
| **真 bug** | `[true-bug]` | 必须本阶段修；不得改写成 deferred |
| **部分交付** | `[partial-delivery]` | 本阶段补齐；剩余切片登记 §5.4 |

---

## 1. 一句话裁定 + 合并统计（TL;DR）

- **一句话裁定**：3 方第 1 轮共 30 条原始 finding 合并为 16 条统一项；5 条 `[true-bug]`、10 条 `[partial-delivery]`、1 条 `n/a`（子项已并入）；最关键缺口是 **admit 池与真实生成运输脱节**、**low salvage 可逃到 NI**、以及 **P6 指定 e2e/soak/closure 未按合同落地**。
- **合并后统一 finding 数**：`16`（来自 `30` 条原始 finding 去重）。
- **按 verdict**：`valid 15` · `valid(子项 overstated) 1` · `stale-rejected 0` · `INVALID 0`。
- **按三类归属 ★**：`[true-bug] 5（V1,V2,V4,V5,V13）` · `[partial-delivery] 10（V3,V6,V7,V8,V9,V10,V11,V12,V14,V15）` · `[true-deferred] 0` · `n/a 1（V16 并入 V10）`。
- **按处置**：`fix 14` · `partial-fix 2（V14 schema CHECK 余项、V10 Turso 真机升级）` · `defer 0` · `owner-gated 0` · `ack 0`。
- **blocker 数**：`8`（编号：`V1 V2 V3 V4 V5 V6 V7 V8`）。
- **净增承重盲区（peer 相对彼此）**：GPT 独家补了 retry/recovery 超 cap 与 Task PATCH 留下 stale `priority_rank`；Grok 把 salvage 车道与显式覆盖审计钉成独立 critical/high；Sonnet 把 facade 类内默认 8 与生产 12 的错位单独标出。三方一致的核心是：运输脱节、指定测试文件不存在、closure 过称。

---

## 2. 合并映射（reviewer finding → 统一编号）

### 2.1 映射表

| 来源 finding（reviewer-原编号）| 合并到 | 合并后问题（一句话）|
|------------------------------|--------|---------------------|
| GPT-R1 / Grok-R1 / Grok-R12 | `V1` | `dispatch_pool` 不控制真实生成运输；omit 仍回落 Claude / NI |
| Grok-R3 / Sonnet-R1 | `V2` | salvage 不看 priority/原池/billing；`low` 可升 NI |
| GPT-R2 / Grok-R4 | `V3` | admit 不传 snapshot / `explicit_channel` / `over_budget` |
| GPT-R3（确定性） / Grok-R5 | `V4` | 确定性 vectorize 被当成 embed 占 8+20 |
| GPT-R4 | `V5` | retry_wait / lease recovery 可突破 queued cap |
| GPT-R7 / Grok-R6 / Sonnet-R2 / Sonnet-R3 / Sonnet-R4 | `V6` | P6 指定 e2e/soak/T37/T38 缺失或假绿 |
| GPT-R8 / Grok-R2 / Sonnet-R5 | `V7` | closure / AP `executed` / todo 过称 |
| GPT-R2（审计） / Grok-R7 / Sonnet-R4 | `V8` | 显式 `compression_channel` 覆盖无 security audit |
| GPT-R3（FIFO） / Grok-R8 / Sonnet-R6 | `V9` | embed 与 generate/unpooled 混排，可被饿死 |
| GPT-R6（Settings） / Grok-R9 / Sonnet-R10 / Grok-S9 | `V10` | Settings/facade 不是 admit SSOT；billing 未注入组合根 |
| Grok-R10 / Sonnet-R8 | `V11` | P6-05 真相层窄回填未发生 |
| Grok-R11 / Sonnet-R9 | `V12` | 事件缺 `channel_source`；waiting 计数过宽 |
| GPT-R5 | `V13` | Task 仍 queued 时改 priority 留下 stale `priority_rank` |
| GPT-R6（schema） | `V14` | 011 无状态耦合 CHECK / FIFO covering index / 010→011 夹具 |
| GPT-R7（守卫） / Grok-R6 / Sonnet-R7 | `V15` | T71 无新表 / `payload_extra` 禁 `dispatch_*` 守卫缺失 |
| Sonnet-R10（已并入 V10） | `V16` | Facade 类内默认 8 vs Settings 12（记账并入 V10） |

### 2.2 宽对照表

| 统一编号 | 合并后的问题 | GPT | Grok | Sonnet |
|----------|--------------|-----|------|--------|
| `V1` | 运输与 admit 池脱节 | `R1` | `R1`/`R12` | `—` |
| `V2` | low salvage 逃逸 | `—` | `R3` | `R1` |
| `V3` | admit 未消费策略输入 | `R2` | `R4` | `—` |
| `V4` | 确定性 vectorize 入 embed | `R3` | `R5` | `—` |
| `V5` | retry/recovery 超 cap | `R4` | `—` | `—` |
| `V6` | 测试缺口 / 假绿 | `R7` | `R6` | `R2`/`R3`/`R4` |
| `V7` | closure / AP 过称 | `R8` | `R2` | `R5` |
| `V8` | 显式覆盖无审计 | `R2` | `R7` | `R4` |
| `V9` | embed 混排饿死 | `R3` | `R8` | `R6` |
| `V10` | Settings 非 admit SSOT | `R6` | `R9` | `R10` |
| `V11` | 真相窄回填缺失 | `—` | `R10` | `R8` |
| `V12` | 事件 / waiting 漂移 | `—` | `R11` | `R9` |
| `V13` | PATCH 留下 stale rank | `R5` | `—` | `—` |
| `V14` | schema / 升级夹具 | `R6` | `—` | `—` |
| `V15` | T71 守卫不完整 | `R7` | `R6` | `R7` |

---

## 3. verified-findings 台账（逐条独立复核 · 核心）

### 3.1 台账主表

| V# | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据（当前代码 file:line / 命令）| 初步处置（→ §5 细化）|
|----|------|------|------|----------|--------|--------------------------------------|----------------------|
| V1 | `dispatch_pool` 不控制真实生成运输 | `critical` | GPT/Grok | `valid` | `[true-bug]` | `generation_construct.py:92-96` 读 payload，缺省 `DEFAULT_COMPRESSION_CHANNEL=non-interactive`（`prompt_profiles.py:39`）；intake 0 处读 `command.dispatch_pool`；structurize `794` CLI 优先；markdown `423-431` 只走 CLI；`_execution_payload:401` dump 原请求使 omit 仍为 `None`；`models.py:183-185` 仍写 omit=Claude | `fix` |
| V2 | salvage 不按车道，`low` 可升 NI | `critical` | Grok/Sonnet | `valid` | `[true-bug]` | `_can_salvage_local_inference:121-122` 只查错误码 + CLI 存在；salvage 闭集含 `INFERENCE_BACKPRESSURE`（`:50`）；无 priority / pool / billing 检查 | `fix` |
| V3 | admit 不消费 snapshot / explicit / over_budget | `high` | GPT/Grok | `valid` | `[partial-delivery]` | `runtime_core.py:191` `pool_kind(p_key)` 无 snapshot；`:232-239` `choose_pool` 不传 `explicit_channel`/`over_budget`；`DISPATCH_LOCAL_CHAR_BUDGET` 仅定义于 `dispatch.py:17` | `fix` |
| V4 | 确定性 vectorize 被 admit 进 embed | `high` | GPT/Grok | `valid` | `[true-bug]` | `dispatch.py:84-92` 无 snapshot 时 `lsrag.vectorize` 默认 `"embed"`；生产 admit 永不传 snapshot。Settings 默认 `live_inference=false` | `fix` |
| V5 | retry / lease recovery 可突破 queued cap | `high` | GPT | `valid` | `[true-bug]` | occupancy queued 只计 `status='ready' AND admitted=1`（`dispatch.py:37`）；`runtime_outcome.py:137-141` retry_wait 保留 admitted；`:236-239` promote / `:346-349` lease recovery 直接回 ready | `fix` |
| V6 | P6 指定 e2e / 并发 soak / 攻击测试缺失或假绿 | `high` | 三方 | `valid` | `[partial-delivery]` | `tests/e2e/test_ns2_dispatch_lanes.py` 与 `tests/unit/test_dispatch_admit_soak.py` 不存在；`test_dispatch_mega.py:350-355` 串行 `for` 50 次；无 NS2-T37/T38；e2e 0 处断言 `dispatch_pool` | `fix` |
| V7 | closure / AP `executed` / todo 过称 | `critical` | 三方 | `valid` | `[partial-delivery]` | closure §0「100% 达成」；close-type=`close-with-known-issues`；AP 文首 `executed` 且 §10.2 全「未观察」；todo P6-02..05 标 `[x]` | `fix` |
| V8 | 显式通道覆盖无 security audit | `high` | GPT/Grok/Sonnet | `valid` | `[partial-delivery]` | `SecurityAuditWriter` 仅 `write_denied`（`events.py:129`）；成功覆盖只写 L2（`config_snapshots.py:572-573`）；`app.py:246` 未注入 `security_audit` | `fix` |
| V9 | embed 与 generate/unpooled 混排可饿死 | `medium` | GPT/Grok/Sonnet | `valid` | `[partial-delivery]` | claim `ORDER BY CASE embed THEN 0 ELSE priority_rank END DESC`（`runtime_core.py:342-343`）；waiting admit 也按 `priority_rank DESC`（`:184`），embed 可被插队 | `fix` |
| V10 | Settings / facade 不是 admit SSOT | `medium` | GPT/Grok/Sonnet | `valid` | `[partial-delivery]` | admit/claim 用模块常数（`runtime_core.py:25-30,324-326`）；`app.py:273-286` 不传 dispatch / billing；`facade.py:125` 默认 8 vs `config.py:54` 默认 12 | `fix` |
| V11 | P6-05 真相层未窄回填 | `medium` | Grok/Sonnet | `valid` | `[partial-delivery]` | S02/S03/S11/S14/S15/D04 对 `dispatch_pool` / `channel_source` / `dispatch_admitted` 0 命中；`S03:866` 仍写「priority 只影响调度顺序」 | `fix` |
| V12 | 事件 payload 与 waiting 定义漂移 | `low` | Grok/Sonnet | `valid` | `[partial-delivery]` | admit 事件 `{"dispatch_pool","priority"}` 无 `channel_source` / `pool`（`runtime_core.py:207,227,255,272`）；`get_waiting_count:65` 计全部 `ready AND admitted=0` | `fix` |
| V13 | PATCH priority 留下 stale `priority_rank` | `medium` | GPT | `valid` | `[true-bug]` | materialize 复制 rank（`runtime_materialize.py:253-336`）；PATCH 只改 Task（`task_commands.py:146-154`）；admit 读 `t.priority`，排序读 `p.priority_rank` | `fix` |
| V14 | 011 状态耦合 / FIFO 索引 / 010 升级 | `medium` | GPT | `valid` | `[partial-delivery]` | 011 仅列级 CHECK；索引无 `created_at/process_uuid`；T10 只跑 fresh migrate。SQLite 无法廉价加表级 CHECK | `partial-fix` |
| V15 | T71 architecture 守卫不完整 | `medium` | 三方 | `valid` | `[partial-delivery]` | `test_architecture.py` 8 个 `test_*`，无「011 后无新 CREATE TABLE」/「payload_extra 无 dispatch_*」；closure 写成「4 passed」 | `fix` |
| V16 | Facade 默认 8（并入 V10） | `low` | Sonnet | `valid` | `n/a` | 见 V10；不单独计三类 | `n/a` |

### 3.2 簇子表（V6 / V7 展开）

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `tests/e2e/` 无 `test_ns2_dispatch_lanes.py` | P6-02 / T60/T62 交付物不存在 | `valid` | 新增文件，行上断言 pool/admitted |
| `tests/unit/` 无 `test_dispatch_admit_soak.py` | P6-03 / T70 交付物不存在 | `valid` | 新增 `asyncio.gather` 32×32 |
| `test_dispatch_mega.py:350-355` | 串行 50 次 `claim_next`，标 T61 | `valid` | 保留矩阵；soak 改到指定文件 |
| `test_dispatch_generation.py` 仅 4 测 | 无 T37/T38；T30–T34 ID 被挪用 | `valid` | 补攻击向量；不再挪用车道 ID |
| `tests/e2e/` 0 命中 `dispatch_pool` | 全仓 e2e 无行上调度断言 | `valid` | lanes e2e 读 DB 列 |
| `NS2-pipeline-priority-closure.md:4-17` | close-type 错；写 100% | `valid` | 按 `.adocs/closure.md` 重写 |
| `NS2-pipeline-priority.md:27` | 文首 `executed`，§10.2 未观察 | `valid` | 修复后按硬闸回填，不得假 executed |
| `NS2-pipeline-priority.todo.md:129-133` | P6-02..05 `[x]` | `valid` | 与仓库事实对齐 |

---

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

**A. 按三类归属（问责视图 · ★主视图）**

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | `5` | `V1 V2 V4 V5 V13` | §5.2 本阶段**必修** |
| `[partial-delivery]` | `10` | `V3 V6 V7 V8 V9 V10 V11 V12 V14 V15` | §5.2 补齐 + 剩余切片登记 §5.4 |
| `[true-deferred]` | `0` | — | 本轮无「本阶段从未承诺」的独立 V#；OOS 项见 deferred ledger |
| `n/a`（rejected / 已修 / 并入）| `1` | `V16` | 并入 V10 |

> 三类合计（不含 `n/a`）= 15 = 全部 valid 缺口数，与 §1 TL;DR 一致。

**B. 按处置（disposition 视图）**：

- **`fix`（本会话修）**：`V1 V2 V3 V4 V5 V6 V7 V8 V9 V10 V11 V12 V13 V15` = **14 项**
- **`partial-fix`**：`V14` = 1（012 FIFO 索引 + 010→011 sqlite 夹具；表级 CHECK 与 Turso 真机升级为剩余切片）
- **`defer-with-rationale`（登记承接）**：无独立 V#；OOS 见 §5.4 / deferred ledger
- **`deferred-by-owner`**：无
- **`stale-rejected`（带证据驳回）**：无
- **`acknowledge`（已修/无操作）**：无

### 4.2 净增承重盲区 + 与自审初稿的差异（self-correction）

本轮实现者=合并人，不另有自审初稿。净增来自三方交叉：

- **V5**（GPT 独家）：retry/recovery 会计漏洞。若只修 admit/handler，queued 硬闸仍会被状态机绕开。
- **V13**（GPT 独家）：priority 双用后，queued PATCH 使 admit 与排序读两套事实。
- **V2**（Grok/Sonnet）：salvage 是独立安全合同，不能被 V1「修好运输后再说」吞掉。
- **V8**（Grok 钉死）：L2 `channel_source=explicit` ≠ security audit。

### 4.3 带证据驳回的跨-reviewer 误报

| V# | 误报方 | 误报内容 | 反证（file:line）| 结论 |
|----|--------|----------|-------------------|------|
| — | Sonnet S6 / S8 | 将 S6「确定性向量化不入池」、S8「超预算」标 `done` | 生产 admit 不传 snapshot / `over_budget`（`runtime_core.py:191,232-239`） | 对齐项 overstated，已并入 V3/V4；**不是** finding 误报 |
| — | GPT O6 / 三方 | 全量 e2e `disk I/O` 当作 NS2 功能红 | 既有 NS1 VF V11；AP O7 明确不修 | 不升为本轮 V# |

无整条 `stale-rejected` / `INVALID`。

---

## 5. 初步修复方案（preliminary fix plan）

### 5.1 修复策略

安全 / 正确性（V1/V2/V4/V5）先于策略接线（V3/V8/V9/V10/V12/V13），再补测试台账（V6/V15）与治理收口（V7/V11）。每条 code fix 必须先有会红的断言再转绿。`[true-bug]` 全部本轮修完；`[partial-delivery]` 本轮补齐合同，V14 的 SQLite 表级 CHECK 与 Turso 真机升级作为剩余切片登记。

不变量：handler 以 `command.dispatch_pool` 为生成运输 SSOT；admit 消费冻结通道/模式/预算；retry/recovery 不得在不清空 admission 的情况下绕开 queued cap；`low` 永不 salvage 到 NI。

### 5.2 逐项修复计划表

| V# | 计划修法 | 目标文件 | falsifiable 验证（修前应 RED）| 需 migration / owner-gate? | 依赖 / 批次 |
|----|----------|----------|-------------------------------|----------------------------|-------------|
| V1 | handler 以 `dispatch_pool` 选 CLI vs local；派生通道写入 execution payload；structurize/markdown/llm-clean 按池运输；改 omit=Claude 文案与锁死单测 | `generation_construct.py` `clean_preflight.py` `config_snapshots.py` `models.py` `prompt_profiles.py` | T30 冲突路径：pool=local 且 payload omit → 必须走 local；omit+normal+live 不再 DEFAULT NI | `no` | 批次 1 |
| V2 | salvage 要求 priority=`normal` 且原池=`local-inference` 且 billing 真 | `generation_construct.py` `ProcessCommand` | T37：low + salvage 码 → CLI 0 次 | `no` | 批次 1 |
| V3 | admit 读 task audit / runtime live flag / 正文长度，传入 `choose_pool` | `runtime_core.py` `dispatch.py` | 显式 NI 行上 pool=NI；超预算 normal → NI | `no` | 批次 2 |
| V4 | `pool_kind(..., snapshot)`；无 snapshot 时用 `live_inference` 合成 L2 | `runtime_core.py` `dispatch.py` | live=false 的 vectorize `dispatch_pool IS NULL` 且可立即 claim | `no` | 批次 2 |
| V5 | retry_wait / lease recovery 清空 `dispatch_admitted/pool/enqueued_at`，promote 后重新 admit | `runtime_outcome.py` | retry 后 queued 仍 ≤ cap | `no` | 批次 2 |
| V8 | `SecurityAuditWriter.write_allowed`；显式通道成功写 `config.compression_channel_override` | `events.py` `config_snapshots.py` `task_create.py` `app.py` | T38：low+显式 NI 缺审计行即失败 | `no` | 批次 2 |
| V9 | admit 拆 generate / embed / unpooled；claim 独立选 embed FIFO 与 generate，再按 `available_at` 二选一 | `runtime_core.py` | T54：local running=2 仍能领 embed；满队列先 low 后 urgent 不插队 | `no` | 批次 2 |
| V10 | `DispatchCaps.from_settings` 注入 runtime；facade 默认改 12；组合根注入 billing | `dispatch.py` `runtime_core.py` `app.py` `facade.py` | 改 Settings cap 改变 admit；T07 Billing False → urgent 不进 NI | `no` | 批次 2 |
| V12 | 事件 payload=`pool/priority/channel_source`；waiting 只计需要池的 process_key | `runtime_core.py` `dispatch.py` | T12 payload 键；waiting 不含 unpooled | `no` | 批次 2 |
| V13 | 任一 Process 物化后禁止 PATCH priority | `task_commands.py` | patch-after-materialize → `task-priority-locked` | `no` | 批次 2 |
| V6 | 新增指定 e2e/soak 文件；T37/T38/T07/T52/T54；修正 ID 挪用 | `tests/e2e/test_ns2_dispatch_lanes.py` `tests/unit/test_dispatch_admit_soak.py` 既有 dispatch 测 | 指定路径可收集且断言行上事实 | `no` | 批次 3 |
| V15 | architecture：011 后无新 required 表；写 `payload_extra` 不含 `dispatch_` | `test_architecture.py` | T71 红→绿 | `no` | 批次 3 |
| V14 | 012 增加 embed FIFO covering index；T10 增加 010→011 sqlite 升级夹具 | `012_*.sql` `test_dispatch_ddl.py` | 新 index 存在；010 fixture 可升到 011 | `migration 012` | 批次 3 |
| V11 | S02/S03/S11/S14/S15/D04 附录级一句 | 对应 domain-truth | grep `dispatch_pool`/`channel_source` 命中 | `no` | 批次 4 |
| V7 | 按 AP §10.5 重写 closure；回填硬闸五态；todo/AP 与仓库对齐 | closure / AP / todo | close-type 合法；无「100%」假陈述 | `no` | 批次 4 |

### 5.3 批次 / 依赖

- **批次 1（运输 + salvage）**：`V1 V2` — 先打通 handler SSOT，否则后续 e2e 无法证明车道。
- **批次 2（admit/claim/会计）**：`V3 V4 V5 V8 V9 V10 V12 V13` — 依赖批次 1 的 command 字段。
- **批次 3（测试与 schema）**：`V6 V14 V15` — 依赖批次 1+2 的行为。
- **批次 4（文档收口）**：`V7 V11` — 必须在测试转绿之后写，避免再次过称。

### 5.4 承接登记（`[true-deferred]` + `[partial-delivery]` 剩余切片）

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接位置（doc / phase / charter / issue）|
|----|--------------|------|----------|----------------|-------------------------------------------|
| `V14.r` | `[partial-delivery] 剩余切片` | `defer-with-rationale` | SQLite `ALTER TABLE` 无法廉价加表级状态耦合 CHECK；Turso 真机 010→011 无本环境 harness | 需要表级 CHECK 或授权 Turso 升级窗口 | `docs/closure/new-start/deferred-items-ledger.md` |
| `NS2-O1` | `[true-deferred]`（AP O1） | `defer-with-rationale` | 真实 billing 扣减本阶段从未承诺 | billing AP 立项 | AP `T-O-357` |
| `NS2-O2` | `[true-deferred]`（AP O2） | `defer-with-rationale` | `cloud-inference` 路由本阶段禁止 | cloud AP | AP `T-O-358` |
| `NS2-O3` | `[true-deferred]`（AP O3） | `defer-with-rationale` | MiniMax 换绑不在 NS2 | 模型选型 charter | AP O3 |
| `NS2-O4` | `[true-deferred]`（AP O4） | `defer-with-rationale` | urgent 老化本阶段不做 | 若 high 被饿死 | AP O4 |
| `NS2-O7` | `[true-deferred]`（AP O7 / NS1-V11） | `defer-with-rationale` | pyturso inspection harness 非 NS2 引入 | harness charter | `NS1-V11` |
| `NS2-GPU` | `[true-deferred]`（AP §8.4） | `deferred-by-owner` | 真机 GPU 争用无稳定 CI | owner 手工 soak | owner |

---

## 6. 处置执行回填（fixes 落地后 · append-only）

> 执行者: `Grok`
> 执行时间: `2026-08-15`
> 回应范围: `V1–V16`
> 对应审查文件: `docs/code-review/new-start/NS2-reviewed-by-{GPT,grok,sonnet}.md`

- **总体回应**：16 条统一项中，14 条本轮完全修复，V14 做了 012 索引 + sqlite 010 升级夹具并将表级 CHECK / Turso 真机升级切出为剩余切片；V16 并入 V10。
- **本轮修改策略**：先打通 `dispatch_pool` 运输与 salvage 车道，再把 snapshot/explicit/budget/容量注入 admit，最后补指定测试与诚实 closure。
- **实现者自评状态**：`ready-for-rereview`

### 6.1 逐项处置结果表

| V# | 处理结果 | 处理方式 | 修改文件 | 独立复核状态 |
|----|----------|----------|----------|--------------|
| V1 | `fixed` | handler 以 `command.dispatch_pool` 为运输 SSOT；execution payload 写入派生通道；structurize/markdown/llm-clean 按池选择 CLI vs local；去掉 omit=Claude 文案与锁死单测 | `generation_construct.py` `clean_preflight.py` `config_snapshots.py` `models.py` `prompt_profiles.py` | `independently-verified` |
| V2 | `fixed` | salvage 要求 `task_priority=normal` 且原池 `local-inference` 且 billing 真；补 T37 | `generation_construct.py` `models.py` `test_dispatch_generation.py` | `independently-verified` |
| V3 | `fixed` | admit 从 task audit 恢复 explicit/size_bytes，传入 `choose_pool`；`DispatchCaps` 提供预算 | `runtime_core.py` `dispatch.py` | `independently-verified` |
| V4 | `fixed` | `pool_kind` 带合成 L2（`live_inference`）；T52 行上 `dispatch_pool IS NULL` | `runtime_core.py` `test_dispatch_claim.py` | `independently-verified` |
| V5 | `fixed` | retry_wait / lease recovery 清空 `dispatch_admitted/pool/enqueued_at`，promote 后重新 admit | `runtime_outcome.py` | `independently-verified` |
| V6 | `fixed` | 新增指定 e2e/soak 文件；T07/T37/T38/T52/T54；不再用串行 mega 冒充 T70 | `test_ns2_dispatch_lanes.py` `test_dispatch_admit_soak.py` 既有 dispatch 测 | `independently-verified` |
| V7 | `fixed` | 按 AP §10.5 重写 closure；§10.2 回填已观察；todo 与仓库对齐 | `NS2-pipeline-priority-closure.md` `NS2-pipeline-priority.md` | `self-claimed-only` |
| V8 | `fixed` | `write_allowed` + Task 创建 UoW 写 `config.compression_channel_override`；T38 查审计表 | `events.py` `config_snapshots.py` `task_create.py` `app.py` | `independently-verified` |
| V9 | `fixed` | admit 拆 generate/embed/unpooled；claim 独立 FIFO 后按 `available_at` 二选一；T54 | `runtime_core.py` `test_dispatch_claim.py` | `independently-verified` |
| V10 | `fixed` | `DispatchCaps.from_settings` 注入 runtime；facade 默认 12；组合根注入 billing | `dispatch.py` `runtime_core.py` `app.py` `facade.py` | `independently-verified` |
| V11 | `fixed` | S02/S03/S11/S14/S15/D04 附录级窄回填 | 对应 domain-truth | `self-claimed-only` |
| V12 | `fixed` | 事件 payload=`pool/priority/channel_source`；waiting 只计需要池的 process_key | `runtime_core.py` `dispatch.py` | `independently-verified` |
| V13 | `fixed` | 任一 Process 物化后 PATCH priority → `task-priority-locked` | `task_commands.py` | `self-claimed-only` |
| V14 | `partially-fixed` | 012 embed FIFO covering index + T10 010→011 sqlite 升级；表级 CHECK / Turso 真机升级见 V14.r | `012_dispatch_embed_fifo_index.sql` `test_dispatch_ddl.py` | `independently-verified` |
| V15 | `fixed` | T71：011 后无新 required 表；payload_extra 无 `dispatch_` | `test_architecture.py` | `independently-verified` |
| V16 | `fixed` | 并入 V10：facade 默认改为 12 | `facade.py` | `independently-verified` |

### 6.2 Blocker / Follow-up 状态汇总

| 分类 | 数量 | 编号 | 说明 |
|------|------|------|------|
| 已完全修复 | `14` | `V1–V13 V15`（V16 并入 V10） | 运输、salvage、admit 输入、确定性 embed、retry 会计、测试、closure、审计、embed 选择器、Settings、真相回填、事件/waiting、priority 锁、T71 |
| 部分修复，需二审 | `1` | `V14` | 索引与 sqlite 升级已做；表级 CHECK / Turso 真机升级为剩余切片 |
| 有理由 deferred | `1` | `V14.r` + AP OOS | 见 §5.4 / deferred-items-ledger |
| 拒绝 / stale-rejected | `0` | — | — |
| 仍 blocked | `0` | — | — |
| acknowledge（无需改）| `0` | — | — |

> **三类对账**：全部 `[true-bug]`（V1 V2 V4 V5 V13）落「已完全修复」，无 bug→defer。全部 `[partial-delivery]` 落「已完全修复」或「部分修复」；V14 剩余切片已登记 §5.4。

### 6.3 变更文件清单

- **产品代码**：`src/runtime/workflow/dispatch.py` `runtime_core.py` `runtime_outcome.py`；`src/runtime/intake/generation_construct.py` `clean_preflight.py` `core.py`；`src/services/config_snapshots.py` `events.py` `prompt_profiles.py`；`src/runtime/task/task_commands.py` `task_create.py`；`src/runtime/inference/facade.py`；`src/contracts/runtime/models.py` `src/contracts/api/models.py`；`api/app.py`；`012_dispatch_embed_fifo_index.sql`
- **测试**：`tests/unit/test_dispatch_*.py` `test_compression_channel.py` `test_dispatch_admit_soak.py` `test_dispatch_ddl.py` `test_d04_write_paths.py` `test_ns1_generation_cli.py`；`tests/domain/test_architecture.py`；`tests/e2e/test_ns2_dispatch_lanes.py`
- **docs**：VF ledger；NS2 closure；AP §10.2；deferred ledger；S02/S03/S11/S14/S15/D04 附录

### 6.4 验证结果

| 验证项 | 命令 / 证据 | 结果 | 覆盖的 V# |
|--------|-------------|------|-----------|
| dispatch 短途 + soak + architecture | `uv run pytest tests/unit/test_dispatch_*.py tests/unit/test_compression_channel.py tests/unit/test_dispatch_admit_soak.py tests/domain/test_architecture.py` | `pass` | V1–V6 V8–V10 V12 V14 V15 |
| unit + domain 回归 | `uv run pytest tests/unit tests/domain` | `pass` | 全量短途 |
| e2e 四车道 + NS1 金样 | `uv run pytest tests/e2e/test_ns2_dispatch_lanes.py tests/e2e/test_ns1_pipeline.py` | `pass` | V1 V4 V6 V7 |
| ruff | `uv run ruff check src tests api` | `pass` | 全仓 |

```text
uv run pytest tests/unit tests/domain → all passed (2026-08-15)
uv run pytest tests/e2e/test_ns2_dispatch_lanes.py tests/e2e/test_ns1_pipeline.py tests/unit/test_dispatch_admit_soak.py → passed
uv run ruff check src tests api → All checks passed!
```

### 6.5 残留与下一轮 entry

- **本轮自评状态**：`ready-for-rereview`
- **是否请求二次审查**：`yes`（范围：`all`，重点 V1/V2/V5/V6/V7）
- **承接到下一轮 / charter / owner session 的项**：`V14.r`、`NS2-O1..O4`、`NS2-O7`、`NS2-GPU` → `docs/closure/new-start/deferred-items-ledger.md`

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | `2026-08-15` | `Grok` | 初次合并：3 方 30 finding → 16 统一项；triaged |
| `v0.2` | `2026-08-15` | `Grok` | §6 回填执行结果；状态 → `resolved` |
