# MKB 0820 第 2 轮跨 Reviewer 统一台账（UF → VF）

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 初步修复方案）。
> **谁写**：**实现者 / 合并人**（不是某一位 reviewer）。在收齐**全部** agent 的审查文件后，由实现者把多份独立审查平铺、合并、逐条对当前真实代码独立复核，形成单一权威台账，并给出初步修复方案。
> **为什么独立成文**：过去的做法是把这份「统一 + verified 台账」append 在某位 reviewer 审查文件的底部。现改为**独立文件 track**——一个标的、一轮合并 = 一份 ledger，互不污染各 reviewer 原件，便于跨轮检索与状态推进。

---

> **元信息（置顶 · 必填）**
>
> | 字段 | 值 |
> |------|----|
> | **审查标的** | `MKB 全仓 HEAD @ 8cb2cb4 / NS5-0820-bug-fixes 落地后 2nd-pass` |
> | **审查阶段 / 轮次** | `第 2 轮合并 / 2nd-pass` |
> | **合并 / 核查人（实现者）** | `Grok (0820-2nd-pass-ledger workflow)` |
> | **合并日期** | `2026-08-20` |
> | **文档状态** | `triaged` |
>
> **审查来源锚定（被合并的 reviewer 制品 — 必须逐份列全）**：
> - `docs/code-review/0820-review/0820-2nd-pass-reviewed-by-gemini.md` — `critical / 16 findings`（10 blocker；最高 critical）
> - `docs/code-review/0820-review/0820-2nd-pass-reviewed-by-grok.md` — `critical / 20 findings`（8 blocker；最高 critical）
> - `docs/code-review/0820-review/0820-2nd-pass-reviewed-by-luna.md` — `critical / 21 findings`（20 blocker；最高 critical）
> - `docs/code-review/0820-review/0820-2nd-pass-reviewed-by-muse.md` — `critical / 15 findings`（7 blocker；最高 critical）
>
> **对照真相（逐条 re-verify 时回看的源）**：
> - `README.md`
> - `docs/baseline/domain-truth/` D01–D08、S01–S16
> - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md`（第 1 轮 UF1–UF103 / VF1–VF103；本轮只作 claimed-fix 谱系，**不沿用其编号**）
> - `docs/plan/new-start/NS5-0820-bug-fixes.md`（claimed-fix 地图，非证据）
> - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`（claimed-fix 地图，非证据）
> - `docs/closure/new-start/deferred-items-ledger.md`
> - 代码根：`api/`、`src/`、`intake/`、`tests/`

---

## 0. 合并方法与核查纪律

> **本节只立规矩，不写结论。** 说明合并了哪几份、用什么纪律复核。

- **合并范围**：`4` 份独立审查全部 finding 平铺（gemini 16 + grok 20 + luna 21 + muse 15 = **72** 条原始 finding）。未丢 low/info。Extractor JSON 仅作 HINT；reviewer 文件是权威。即使 extractor 漏掉 R#，本表仍收录。
- **核查纪律（硬）**：
  1. **reviewer 的结论仅作线索**。每条判 `valid` 的项，均由实现者**亲自 grep / Read 当前真实代码**坐实，关键证据带 `file:line`。
  2. 与任一方冲突，**以实测为准**；自审初稿被推翻处必须在 §4.2 显式 self-correct。
  3. **已纠正的跨-reviewer 误报**必须在 §4.3 带证据列出，不得静默吞掉。
  4. 严重级别**取多方最严**；同一问题被多方提及合并为一条统一编号。
- **统一编号前缀**：本文件 Phase-1 使用 **`UF`（unified-finding）**。Phase-2 起写入 **`VF`（verified-finding）**，且 **`VF-n == UF-n`**（编号一一对应，不重排）。禁止在 Phase-1 填写 VF 判定。
- **编号独立声明**：本轮 `UF1…UFn` / 后续 `VF1…VFn` **独立于第 1 轮 VF1–VF103**。第 1 轮 VF 编号只可在「claimed-fix 谱系」栏引用，不得把本轮 UF-n 当成旧 VF-n。

### 0.1 复核判定（verdict）图例

| verdict | 含义 |
|---------|------|
| `valid` | 属实，需处理 |
| `valid-edge` | 属实但仅边界/条件态触发（happy-path 已绿）|
| `valid-conditional` | 属实但本环境不复现；按防御性处理 |
| `valid-owner-gated` | 属实但归 owner 动作（sign-off / deploy / 复测）|
| `valid-pre-existing` | 属实但 base 即存在，非本阶段引入 |
| `valid-by-design` | 现象属实但为既定设计（如 session-scope）|
| `valid(子项 overstated)` | 主项真，个别子断言过度（须指明哪句过度）|
| `stale-rejected` | 不成立：reviewer 读了陈旧/已删的代码或误解 |
| `INVALID` | 不成立：凭空指控，无代码依据 |

### 0.2 处置（disposition）图例

| 处置 | 含义 |
|------|------|
| `fix` | 本轮修复（必配 falsifiable 测试或被既有/新增测试覆盖）|
| `partial-fix` | 部分修复 + 余项 defer（须写清切分）|
| `defer-with-rationale` | 有理由后延（带 reopen 触发器 + 承接位置）|
| `deferred-by-owner` | 归 owner session（sign-off / deploy / 复测）|
| `acknowledge` | 已修 / 无需改动（仅记录）|
| `stale-rejected` | 带证据驳回，不改代码 |

### 0.3 严重级别图例

`critical | high | medium | low | info`（取多方最严；`(nb)` = 非 blocker，`(子项)` = 仅子断言达该级）。

### 0.4 Finding 三类归属（class）图例 ★

> **目的**：对每条**经复核成立（`valid*`）且代表未了结缺口**的 finding，按它**相对本阶段计划的归属**强制三选一。这是与 `verdict`（真不真）/ `disposition`（怎么处理）**正交的问责轴**——它回答「这个缺口归谁、本阶段是否欠了账」。`stale-rejected` / `INVALID` / 已修的 `acknowledge` 不进三类，标 `n/a`。

| 归属类 | 标记 | 精确含义 | 本阶段义务 | 典型 disposition |
|--------|------|----------|------------|------------------|
| **真 deferred** | `[true-deferred]` | 该缺口**本阶段从未承诺交付**，合法属于后续阶段 / owner session 才更新或修复。含：by-design 的未来发散、owner-gated 动作（sign-off / deploy / 复测）、需 migration 而本阶段冻结 migration 的项、未在本阶段 scope 内的 pre-existing 缺陷。 | **登记承接**：带 reopen 触发器 + 承接位置（§5.4）；本阶段不修是**诚实**的。 | `defer-with-rationale` / `deferred-by-owner` |
| **真 bug** | `[true-bug]` | 该缺口是**本阶段引入的回归**，**或**本阶段计划 / 职责范围内**该修却漏修 / 修错**的内容。**本阶段欠的账。** | **必须本阶段修**（默认 `fix`）。若确实修不动，必须**显式升级为 blocker 交 owner 裁决**，**严禁**降级成 `[true-deferred]` 规避（见硬规则）。 | `fix` / 极少数 `partial-fix` |
| **部分交付** | `[partial-delivery]` | 该 item **本阶段已规划并已动手**，但**未完成 / 仅完成部分**。承诺了、做了一半。 | **本阶段补齐**（默认 `fix`）；若本轮只能完成部分，**剩余切片必须显式切分**并作为 `[true-deferred]` 子项登记 §5.4 带触发器，不许笼统留白。 | `fix` / `partial-fix` |

**三类判定决策树**（agent 逐条走）：

```text
这条 finding 代表的缺口，相对本阶段计划归谁？
├─ 复核不成立 / 已修 ───────────────────────────▶ n/a（不进三类）
├─ 本阶段从未承诺、合法属未来阶段或 owner ───────▶ [true-deferred]
├─ 本阶段已规划、动了手但没做完 ────────────────▶ [partial-delivery]
└─ 本阶段引入的回归 / 计划内该修却漏修或修错 ────▶ [true-bug]
```

**硬规则（诚实闸 · 反 no-free-defer 规避）**：
1. **`[true-bug]` 不得被改写成 `[true-deferred]`** 来回避本阶段修复。本阶段引入或本阶段欠的账，要么修、要么显式升级 blocker 由 owner 裁决，二者必居其一。
2. **`valid-pre-existing` 不自动等于 `[true-deferred]`**：base 即存在、但**本阶段计划承诺要修**它 → 仍是 `[true-bug]`；本阶段未承诺修 → `[true-deferred]`。
3. **`[partial-delivery]` 的未完成切片**必须落 §5.4 承接表并标「来源 = 某 partial item 的剩余切片」，使「做了一半」不被静默当成「做完了」。
4. 三类计数必须在 §1 TL;DR 与 §4.1-A 双向对齐（同一组 V# 不重复计、不漏计）。

---

## 1. 一句话裁定 + 合并统计（TL;DR）

> Phase-3 已按当前 HEAD 逐条复核并注入 VF；文档状态仍为 `triaged`（本工作流未执行代码修复）。VF-n == UF-n，编号独立于第 1 轮 VF1–VF103。

- **一句话裁定**：4 方 72 条原始 finding → 38 条 VF（VF1–VF38 与 UF 一一对应）；`37` 条属实（含 edge / conditional / owner-gated / pre-existing / 子项 overstated），`1` 条 stale-rejected（VF19：水合缓存已由 `search()` 激活）。本阶段欠账是 **8 [true-bug] + 26 [partial-delivery]**，另 **3 [true-deferred]** 诚实后延。最关键生产缺口：UoW `BEGIN` 取消毒化单例连接、默认 Turso `/ready` 与 `claim_next` 永 503、readiness 探针把活库切成 `mvcc` 且不 restore、vLLM 共享 client 被 probe 5s 冻结、vectorize upsert 改写 serving `indexed` 行、`external_key` 非原子且 `revision_ordinal=1`、GC `TX1→unlink→TX2` 窗口丢字节。
- **合并后统一 finding 数**：`38`（来自 `72` 条原始 finding 去重；VF# = UF#）。
- **按 verdict**：`valid 14` · `valid(子项 overstated) 16` · `valid-edge 4` · `valid-conditional 1` · `valid-owner-gated 1` · `valid-pre-existing 1` · `INVALID 0` · `stale-rejected 1`。
- **按三类归属 ★**：`[true-bug] 8（VF3 VF7 VF10 VF15 VF18 VF24 VF27 VF28）` · `[partial-delivery] 26（VF1 VF2 VF4 VF5 VF8 VF9 VF11 VF12 VF13 VF14 VF16 VF17 VF21 VF22 VF23 VF25 VF26 VF29 VF30 VF31 VF33 VF34 VF35 VF36 VF37 VF38）` · `[true-deferred] 3（VF6 VF20 VF32）` · `n/a 1（VF19）`。
- **按处置**：`fix 32` · `partial-fix 2（VF35 VF38）` · `defer-with-rationale 2（VF6 VF20）` · `deferred-by-owner 1（VF32）` · `stale-rejected 1（VF19）` · `acknowledge 0`。
- **blocker 数**：`7`（编号：`VF1 VF2 VF3 VF7 VF12 VF15 VF25`；均为复核后 `critical` 且本阶段须修的生产缺口）。
- **按 verify_shard**：`persist 6` · `infer 5` · `intake 6` · `retrieve 3` · `workflow 8` · `security 6` · `tests 1` · `delivery 3`（UF18 只计 `retrieve`，与 §2.3 一致；不在 intake 双计）。
- **净增承重盲区（peer 相对彼此）**：Luna 独家钉死活库 `journal_mode=mvcc`（VF3）与 `external_key` 非原子+`revision_ordinal=1`（VF15）；Grok 独家钉死 salvage 非运输 SSOT（VF8）与 Task cancel 不栅栏 Execution（VF28）；Gemini 独家钉死 worker 不取消 `handler_task`（VF21）与 retirement 剩余 POINTER_UNAVAILABLE 队头（VF26）；Muse 独家钉死 generation 预留跨 UoW（VF17）与 overflow undo 错桶（VF33）。Gemini 的 VF19 被代码反证驳回。详见 §4.2。
- **AGENT 评审绩效**：见 §7。最佳 Luna（总分 7.7）；最高价值 Finding 为 VF3 readiness probe 改活库 `journal_mode`（`luna-R11`）。

---

## 2. 合并映射（reviewer finding → 统一编号）

> 把每位 reviewer 的原始编号映射到统一 `UF#`。一条统一项可由多方贡献。源 id 格式：`gemini-R#` / `grok-R#` / `luna-R#` / `muse-R#`。每条原始 R# 恰好出现一次。luna-R17 按簇拆分纪律归入 CLI 边界（UF11）；其 vLLM timeout 切片与 gemini-R3 / grok-R9 / muse-R8 同根，但源 id 只记一次故不重复挂到 UF7。

### 2.1 映射表

| 来源 finding（reviewer-原编号）| 合并到 | 合并后问题（一句话）|
|------------------------------|--------|---------------------|
| gemini-R1 / grok-R17 / luna-R1 / muse-R1 | `UF1` | `immediate_transaction` 的 `BEGIN IMMEDIATE` 在 `try` 外，取消可使单例连接永久 `in_transaction` |
| gemini-R2 / grok-R1 / luna-R10 / muse-R2 | `UF2` | 默认 `concurrent_writes_required=True` 与 Turso 串行 UoW 强制 `concurrent_writes=False` 冲突，`/ready` 与 `claim_next` 永久 503 |
| luna-R11 | `UF3` | `probe_concurrent_writes` 在生产主库执行 `PRAGMA journal_mode=mvcc` 且 `restore_journal_mode=False`，把可见模式从 wal 改成 mvcc |
| grok-R12 / luna-R12 | `UF4` | `verify_migrations` 在 checksum 后只探 `mkb_tasks`，DROP 其它核心表仍报 schema ready |
| luna-R9 | `UF5` | 迁移 014 的 live unique 落地后，多条 lookup 仍返回 tombstoned `stored_object_uuid` |
| muse-R15 | `UF6` | migration 014 对存量重复 live 对象建 `UNIQUE … WHERE tombstoned_at IS NULL` 失败不自愈 |
| gemini-R3 / grok-R9 / muse-R8 | `UF7` | `LocalVllmAdapter` 共享 httpx client 被 probe 5s 固化，后续 `generate` 未按请求覆盖 timeout（grok 兼称无 `aclose` / `trust_env=True`） |
| grok-R4 | `UF8` | salvage 仍在同一 local Process 上调 Claude，不 admit NI Process，绕过运输 SSOT |
| grok-R5 / luna-R7 | `UF9` | generation evidence 仍是进程内 dict，缺 `process_uuid` 时回退 `"_"`，失败可串 Process |
| grok-R20 / luna-R2 | `UF10` | Facade RETRYABLE 先 `release(lease)` 再 sleep/再获取，`finally` 无条件 release 导致 double-release 或 `release(None)` |
| gemini-R16 / grok-R19 / luna-R17 | `UF11` | CLI 子进程继承父环境、stdout 帽在 `communicate()` 之后、取消路径 terminate 未 shield / 未杀进程组 |
| gemini-R4 / grok-R3 / muse-R4 | `UF12` | vector upsert SELECT 不含 `index_generation`/`publication_state`，可就地 UPDATE 在线 `indexed` 行 |
| grok-R2 / luna-R4 | `UF13` | HITL Item 以 `deactivated` 插入；公共 approve/`consume_gate_decision` 不激活，publication 被 SERVING_FENCE 挡住 |
| grok-R13 / luna-R13 | `UF14` | raw/clean 共用 acceptance envelope handle/size，`content_digest ≠ sha256(bytes)`，rebuild 已依赖该谎言 |
| luna-R3 | `UF15` | `external_key` 解析/写入非原子且 `revision_ordinal` 固定为 1，重试返回 201 后失败而非 replay |
| luna-R14 | `UF16` | namespace 仍 `default`、维度切换 409；generation 预留非耐久；purge API/runtime/测试对 partial vs full 合同不一致 |
| muse-R11 | `UF17` | `_namespace_coordinates` 在单独只读事务预留 `index_generation+1`，并发 publish 可预同号 409 |
| grok-R14 | `UF18` | title 进入 `content_full` headers 被 embed，查询侧只 embed 裸 query，cosine 系统性偏移 |
| gemini-R14 | `UF19` | `_HYDRATION_CACHE` 存在但 `RetrievalService` 从不 `begin_request_cache()`，每 hit 重复读盘解析 |
| muse-R9 | `UF20` | 检索 S04/S09 只读 fence 走 `BEGIN IMMEDIATE` 写锁，放大 Turso 单写者 BUSY→503 |
| gemini-R10 | `UF21` | `WorkflowWorker` 外部取消只停 heartbeat，不取消 `handler_task` 且可能不 discard `_pending` |
| grok-R11 / luna-R5 | `UF22` | heartbeat 循环只捕 `CancelledError`，其它异常静默停跳而 handler 继续，租约可被偷 |
| gemini-R9 / grok-R18 | `UF23` | `WorkflowRuntime` 未注入 `metrics`，`outbox.dead` 不递增 `mkb_outbox_dead_total` 且 `trace_uuid` 被换成新 uuid7 |
| luna-R6 | `UF24` | outbox dead/complete/release UPDATE 不检查 `rowcount`，过期后 stale owner 仍可写事件/指标 |
| gemini-R8 / luna-R8 / muse-R10 | `UF25` | ObjectGC `TX1→unlink→TX2` 窗口内新 reference 可留下活目录项 + 已删字节（luna 兼称 promote-crash orphan 不在 catalog 扫描内） |
| gemini-R7 | `UF26` | `IndexGenerationRetirement` 对 namespace 停用 / 空 serving revision / 非 active pointer 不 `abandoned`，队头永久阻塞 |
| gemini-R11 | `UF27` | `_fail_process_tx` UPDATE 缺少 `fencing_generation` CAS，lease recovery 可把新世代 running process 标 failed |
| grok-R10 | `UF28` | Task cancel 同 TX 只 CAS Task `cancelling` + outbox，不栅栏当前 Execution/Process，handler 仍可 success-win |
| gemini-R5 / grok-R6 / luna-R15 / muse-R5 | `UF29` | 空 `trusted_proxy_cidrs` 仍把私网 peer 当反代并信任 XFF，可伪造 `127.0.0.1` 穿透内网闸与限流 |
| gemini-R6 / grok-R7 / luna-R18 / muse-R6 | `UF30` | `TeamPatchRequest`/`TaskPatchRequest` 跳过 `assert_safe_public_data`；luna 兼称 source descriptor / signed URL 可写入 durable state |
| gemini-R12 / grok-R8 / luna-R16 / muse-R7 | `UF31` | `reject_oversize_body` 只看 `Content-Length`，chunked / 缺长度 body 全缓冲可 OOM |
| grok-R16 | `UF32` | FastAPI 默认 `/docs` `/redoc` `/openapi.json` 匿名，可枚举 `/internal` 写面 |
| muse-R13 | `UF33` | `DenialAuditSampler.decide` 溢出用 `overflow` 桶，`undo` 仍按 `hash(remote_ip)` 算 key，配额永不退 |
| muse-R14 | `UF34` | 空 CIDR 限流桶按伪造 XFF 分桶；`_is_private_peer` 不递归 `ipv4_mapped`，`::ffff:*` 与 egress 行为分裂 |
| grok-R15 / luna-R20 | `UF35` | NS5 短途测试靠源码扫描 / 恒真 / 未调用对象 / 未跨过 lease 假绿；e2e 仍 `sqlite3.connect` 打开 Turso 文件 |
| gemini-R13 / muse-R3 / luna-R19 | `UF36` | `HealthAggregator.ttl_seconds` 从未读取（仅 in-flight coalesce），`readiness()` 持写锁；luna 兼称 sidecar 无真实队列/close、失败折叠为布尔 gate |
| gemini-R15 / muse-R12 | `UF37` | `TeamService.create` 并发 PK 未捕 `IntegrityError`，走 HTTP 500 而非 409 |
| luna-R21 | `UF38` | 指定 VRX5 closure 路径缺失；closure/ledger 把若干 partial/deferred 叙述成可收口 |

### 2.2 宽对照表

| 统一编号 | 合并后的问题 | gemini | grok | luna | muse |
|----------|--------------|--------|------|------|------|
| `UF1` | UoW BEGIN 在 try 外 | `R1` | `R17` | `R1` | `R1` |
| `UF2` | 默认 Turso `/ready` 永久 503 | `R2` | `R1` | `R10` | `R2` |
| `UF3` | readiness probe 改 journal_mode | — | — | `R11` | — |
| `UF4` | schema readiness 只探 `mkb_tasks` | — | `R12` | `R12` | — |
| `UF5` | tombstoned stored object 被 lookup 复用 | — | — | `R9` | — |
| `UF6` | migration 014 存量脏 unique 不自愈 | — | — | — | `R15` |
| `UF7` | vLLM 单例 5s timeout 冻结 | `R3` | `R9` | — | `R8` |
| `UF8` | salvage 仍不是运输 SSOT | — | `R4` | — | — |
| `UF9` | generation evidence `"_"` 回退 | — | `R5` | `R7` | — |
| `UF10` | Facade retry lease double-release / `release(None)` | — | `R20` | `R2` | — |
| `UF11` | CLI env / stdout cap / terminate 边界 | `R16` | `R19` | `R17` | — |
| `UF12` | vectorize UPDATE 已 serving 坐标 | `R4` | `R3` | — | `R4` |
| `UF13` | HITL approve 不激活 Item | — | `R2` | `R4` | — |
| `UF14` | raw/clean 共用 envelope，digest≠bytes | — | `R13` | `R13` | — |
| `UF15` | external_key 非原子且 revision=1 | — | — | `R3` | — |
| `UF16` | namespace/维度/generation/purge 合同未闭合 | — | — | `R14` | — |
| `UF17` | generation 预留不在同一 UoW | — | — | — | `R11` |
| `UF18` | title 进入 embed，查询侧不带 header | — | `R14` | — | — |
| `UF19` | hydration cache 未被 RetrievalService 激活 | `R14` | — | — | — |
| `UF20` | 检索只读 fence 持 BEGIN IMMEDIATE | — | — | — | `R9` |
| `UF21` | worker 取消遗漏 `handler_task` / `_pending` | `R10` | — | — | — |
| `UF22` | heartbeat 非取消异常静默停跳 | — | `R11` | `R5` | — |
| `UF23` | `outbox.dead` 无 metrics、trace 被替换 | `R9` | `R18` | — | — |
| `UF24` | outbox stale-owner UPDATE 不检查 rowcount | — | — | `R6` | — |
| `UF25` | GC TX1-unlink-TX2 TOCTOU | `R8` | — | `R8` | `R10` |
| `UF26` | retirement 不可用 Intent 队头阻塞 | `R7` | — | — | — |
| `UF27` | `_fail_process_tx` 缺 fencing_generation CAS | `R11` | — | — | — |
| `UF28` | Task cancel 不在同 TX 栅栏 Execution | — | `R10` | — | — |
| `UF29` | 空 CIDR 仍信任私网 XFF | `R5` | `R6` | `R15` | `R5` |
| `UF30` | Team/Task PATCH extras 跳过拒密 | `R6` | `R7` | `R18` | `R6` |
| `UF31` | body cap 只看 Content-Length | `R12` | `R8` | `R16` | `R7` |
| `UF32` | `/docs` `/openapi.json` 匿名 | — | `R16` | — | — |
| `UF33` | DenialAuditSampler overflow undo 错桶 | — | — | — | `R13` |
| `UF34` | 限流桶按伪造 XFF；ipv4_mapped 分裂 | — | — | — | `R14` |
| `UF35` | NS5 假绿测试 + sqlite3-on-Turso | — | `R15` | `R20` | — |
| `UF36` | HealthAggregator TTL 死代码 + 持写锁 | `R13` | — | `R19` | `R3` |
| `UF37` | Team.create 并发 PK 走 500 | `R15` | — | — | `R12` |
| `UF38` | closure/ledger 路径与可收口叙述 | — | — | `R21` | — |

### 2.3 unified-findings 平铺台账

> 本节是 Phase-1 问题汇聚台账。`最严严重级` = 来源中最严者。`verdict` / `class` / `disposition` 一律 `pending-phase-2`，不在本表展开。`reviewer 声称的 file:line` 是各方自称证据，**不是** Phase-2 实测。

| UF# | 标题 | 最严严重级 | 来源 | verify_shard | 合并后问题（一句话）| reviewer 声称的 file:line |
|-----|------|------------|------|--------------|---------------------|---------------------------|
| UF1 | `immediate_transaction` 的 BEGIN 在 try 外 | `critical` | gemini/grok/luna/muse | persist | `BEGIN IMMEDIATE` 的 `to_thread` 在 `try` 外；取消可使单例连接永久 `in_transaction`，后续写全部失败 | `src/persistence/uow.py:26-46`；muse 兼指 `WorkflowWorker._heartbeat_loop:151` |
| UF2 | 默认 Turso 画像下 `/ready` 与 claim 永久 503 | `critical` | gemini/grok/luna/muse | persist | `concurrent_writes_required=True` 时 Turso 强制 `gates[concurrent_writes]=False`，`HealthAggregator.REQUIRED` 含该项 → `/ready` 与 `claim_next` 永 503；测试画像 waiver | `src/persistence/turso/port.py:171-177`；`src/runtime/health.py:14-24`；`api/app.py:291-294`；`src/runtime/config.py:24`；`data/config/default.toml:7`；`tests/local_runtime.py:21`；`engine.py:97-99` |
| UF3 | readiness probe 修改生产库 journal_mode | `critical` | luna | persist | `probe_concurrent_writes` 执行 `PRAGMA journal_mode=mvcc` 且 `restore_journal_mode=False`，外部连接看到 wal→mvcc | `src/persistence/engine.py:24-42`；`src/persistence/turso/port.py:152-157` |
| UF4 | schema readiness 只探 `mkb_tasks` | `high` | grok/luna | persist | checksum 之后只要求 `mkb_tasks` 存在；DROP processes/outbox/vector_records 等仍 schema ready | `src/persistence/migration_runner.py:148-163`；`api/app.py:174-179` |
| UF5 | tombstoned stored object 可被多路径复用 | `high` | luna | persist | 014 live unique 已过滤 tombstone，但 generation/config/rebuild/scatter/task 的 lookup 仍可能返回已墓碑 uuid | `generation_artifacts.py:562`；`config_snapshots.py:333`；`index_rebuild_commit.py:305`；`scatter_intake.py:682`；`task_create.py:400`；对照 `services/artifacts.py:142` |
| UF6 | migration 014 对存量重复 live 对象不自愈 | `medium` | muse | persist | `UNIQUE … WHERE tombstoned_at IS NULL` 遇存量重复直接失败，ledger 永不前进，`schema_migration` 永久 False | `src/persistence/migrations/014_ns5_uuid_and_tombstone.sql:17-20`；`src/persistence/migration_runner.py:121-145` |
| UF7 | vLLM 共享 client 被 probe 5s 固化 | `critical` | gemini/grok/muse | infer | 首次 `probe()` 以 `min(timeout,5)` 建 `_shared_client`；后续 `generate(180s)` 复用且 `client.post` 不传 per-request timeout（grok 兼称 lifespan 不 `aclose`、`trust_env=True`） | `src/llm_adapters/local_vllm.py:206-215,223-226,242-245`；`api/app.py:183-191,458-464`；`src/runtime/config.py` `generate_timeout_seconds` default 180 |
| UF8 | salvage 仍不是运输 SSOT | `high` | grok | infer | salvage 在同一 local Process 上 `cli.run`，不 materialize/admit NI Process；`has_quota` 恒真；BACKPRESSURE 可被翻译成另一次模型调用 | `src/runtime/intake/generation_construct.py:192-226,106-122`；`src/services/billing.py` |
| UF9 | generation evidence 默认 `"_"` 桶可串 Process | `high` | grok/luna | infer | 进程内 `_pending` dict；`process_uuid or "_"`；flush 空则 `take()` 默认桶；崩溃丢失，无关 process 可偷走证据 | `src/runtime/intake/generation_evidence.py:9-52`；`generation_construct.py:287-290,1002-1035`；`runtime_outcome.py:471-474` |
| UF10 | Facade retry 退避导致 gate double-release / `release(None)` | `high` | grok/luna | infer | RETRYABLE 先 release 再 sleep；再获取失败时 `lease=None`；`finally` 仍 `release(lease)` → AttributeError 或 unbalanced double-release | `src/runtime/inference/facade.py:385-409` |
| UF11 | CLI 环境 / 子进程 / stdout 帽 / terminate 边界 | `high` | gemini/grok/luna | infer | env 仅滤 MKB_*（父进程 AWS/Anthropic secret 进入 child）；stdout 上限在 `communicate()` 之后才检查；取消路径 `_terminate_process` 未 shield、不杀进程组 | `src/runtime/inference/claude_cli.py:320-340,377-379,382-406` |
| UF12 | 向量 upsert 可就地篡改在线 indexed 行 | `critical` | gemini/grok/muse | intake | SELECT 按坐标且不含 `index_generation`/`publication_state`；命中后 `UPDATE publication_state='withdrawn'` 并改写 generation，打穿当前 serving COUNT | `src/runtime/intake/vector_publish_commit.py:346-350,381-427`；`src/runtime/intake/vectorize.py:203-213`；`015_vec_coord_generation.sql:7-10` |
| UF13 | HITL approve 不激活 Item；`resolve_gate` 死代码 | `high` | grok/luna | intake | `require_human_review` 插入 `deactivated`；激活写在无人调用的 `resolve_gate`；公共 `consume_gate_decision` 不改 lifecycle；approve 200 后仍不可发布 | `src/runtime/intake/acceptance_snapshot.py:106-123`；`src/runtime/workflow/runtime_gates.py:101,127,164-195,197-285`；`src/services/intake_lifecycle/lifecycle_publish.py:75-77`；`src/runtime/task/task_projections.py:378-389`；`001_initial.sql:961` |
| UF14 | raw/clean 共用 envelope，digest≠bytes | `high` | grok/luna | intake | raw 与 clean 行共用 `output_ref`/size，digest 却是语义 digest；`sha256(read(handle)) != content_digest`；rebuild 已按 envelope 私货读 `clean_text` | `src/runtime/intake/acceptance_snapshot.py:63-64,133-185`；`src/runtime/intake/acquisition_ingest.py:77-84`；`src/runtime/intake/core.py:494-507` |
| UF15 | external_key 解析/写入非原子且 revision=1 | `critical` | luna | intake | 先发新 UUID 再独立读事务 resolve；source/item/revision 无原子幂等栅栏；`revision_ordinal` 写死 1；同 key 第二次 201 后任务 failed | `src/runtime/intake/acquisition_ingest.py:91-178,240-307`；`src/runtime/intake/acceptance_snapshot.py:133-145` |
| UF16 | namespace/维度切换与 generation/purge 合同未闭合 | `high` | luna | intake | 仍 `namespace_key=default`，维切换 `VECTOR_NAMESPACE_BINDING_CONFLICT`；generation 预留不在同一 TX；purge API 只接受 `all` 而测试仍覆盖 partial | `src/runtime/intake/vectorize.py:99-104,265-305`；`src/runtime/intake/vector_publish_commit.py:265-305`；`src/services/vector_purge.py:69-76`；`tests/e2e/test_vector_purge_generation.py` |
| UF17 | `_namespace_coordinates` 单独事务预留 generation | `medium` | muse | intake | 只读事务取 `index_generation+1`，publish 回调里才 CAS 指针；并发 vectorize 可预同号，后者 409 抖动 | `src/runtime/intake/vector_publish_commit.py:272-281,136-167`；`src/runtime/intake/vectorize.py:169,286-330` |
| UF18 | 标题进入 embed，查询侧不带 header | `medium` | grok | retrieve | title 进入 `content_full` headers 走主路径 embed；query embed 用裸 `query`；VF43 与 VF95 在主路径互相拆台 | `generation_construct.py:1324-1338`；`vectorize.py:161-197,461-472`；`retrieval_request.py` |
| UF19 | 检索水合缓存未被上层激活 | `medium` | gemini | retrieve | `_HYDRATION_CACHE` 实现在，但 `RetrievalService.retrieve()` 从不 `begin_request_cache()`/`begin_hydration_cache()` | `src/persistence/retrieval_access.py:45-120` |
| UF20 | 检索 S04/S09 重检读 fence 持写锁 | `high` | muse | retrieve | `filter_retrieval_eligible` / `load_retrieval_body` / `_sql_batch_eligibility` 均 `transaction()` → `BEGIN IMMEDIATE`，只读路径放大单写者竞争 | `src/persistence/retrieval_access.py:136,194`；`src/services/retrieval/retrieval_rank.py:465`；`src/persistence/turso/port.py:140-144` |
| UF21 | Worker 取消遗漏 `handler_task` 与 `_pending` | `high` | gemini | workflow | `run_once` 被取消时 `finally` 只取消 heartbeat；handler 成孤儿；`accept_outcome` 前取消可不 `_discard_pending`，打满 `OBJECT_PENDING_OUTPUT_LIMIT` | `src/runtime/workflow/worker.py:66-138`；`src/services/artifacts.py:50-84` |
| UF22 | heartbeat 非取消异常不能 fencing | `high` | grok/luna | workflow | 心跳循环只捕 `CancelledError`；adapter/DB 异常使心跳停跳，handler 继续 accept outcome，lease 可被 reclaim 双写 | `src/runtime/workflow/worker.py:139-162,134-137` |
| UF23 | `outbox.dead` 无指标且 trace 被替换 | `high` | gemini/grok | workflow | `getattr(self, "metrics", None)` 恒 None；`api/app.py` 构造 `WorkflowRuntime` 未传 metrics；dead 事件 `trace_uuid=uuid7()` 新根 | `src/runtime/workflow/runtime_outbox.py:357-377`；`src/runtime/workflow/runtime_core.py:48-85`；`api/app.py:296` |
| UF24 | outbox stale owner 状态写入不检查 rowcount | `high` | luna | workflow | dead/complete/release 带 owner 条件 UPDATE 后不看 `rowcount==1` 仍写事件/指标；outbox 无长处理 heartbeat | `src/runtime/workflow/runtime_outbox.py:343-355,379-406,41-128`；`src/runtime/workflow/runtime_repair.py:40-61` |
| UF25 | ObjectGC 两阶段 unlink 的 TOCTOU 丢字节 | `critical` | gemini/luna/muse | workflow | TX1 无引用提交 → 事务外 unlink → TX2 复核；窗口内新 reference 提交后文件已被删，TX2 409 也无法恢复（luna 兼称 promote-crash orphan 不在 catalog 扫描） | `src/services/object_gc.py:132-159,188-272`；`src/services/artifacts.py:52-84,131-149`；`src/storage/local_store.py:27-29,120-133` |
| UF26 | retirement 漏判不可用场景队头阻塞 | `high` | gemini | workflow | namespace 停用、item active 但 `serving_revision_uuid IS NULL`、pointer 非 active 时 Intent 保持 `open`，`ORDER BY eligible_at LIMIT 100` 永久队头阻塞 | `src/services/index_retirement.py:320-328,507-551,561-573` |
| UF27 | `_fail_process_tx` 缺少 fencing_generation CAS | `medium` | gemini | workflow | fail UPDATE 只排除终态，无 `AND fencing_generation=?`；lease recovery 可把新世代 running process 标 failed | `src/runtime/workflow/runtime_outcome.py:454-470` |
| UF28 | Task cancel 不在同 TX 栅栏 Execution | `high` | grok | workflow | cancel 只 CAS Task `cancelling` + 入 `cancel_execution` outbox；supervisor 先跑完当前 handler 再 drain；`accept_outcome` 不看 Task，可 `cancelling → succeeded` | `src/runtime/task/task_commands.py:193-205`；`workflow_supervisor.py:46-64`；`runtime_outcome.py` success path；`project_task_status_tx` |
| UF29 | 空 CIDR 仍信任私网 peer 的 XFF | `high` | gemini/grok/luna/muse | security | `trusted_proxy_cidrs=""` 且 `_is_private_peer(peer)` 时返回 XFF 左值；伪造 `127.0.0.1` 可过 `/internal` `/metrics` 并打穿限流桶 | `src/runtime/security.py:476-499,492-498`；`src/runtime/config.py:25`；`api/dependencies.py:162,176-194`；`api/app.py:518-525` |
| UF30 | Team/Task PATCH extras 跳过拒密 | `high` | gemini/grok/luna/muse | security | Create 有 `assert_safe_public_data`，Patch 没有；`apiKey`/`secretKey`/signed URL 可 PATCH 入库并 GET 回显。luna 兼称 HTTP source descriptor / signed URL 进入 durable stage state；gemini 兼称 `_SECRET_KEY_PATTERN` 漏 `_REDACT_KEY` 词 | `src/contracts/api/models.py:50-60,362-377`；`src/services/teams.py:80-112,93-105`；`src/runtime/task/task_commands.py:158-177`；`task_views.py:61-93`；`src/services/config_snapshots.py:403-426`；`acquisition_ingest.py:68-89` |
| UF31 | body cap 只检查 Content-Length，chunked 可绕过 | `high` | gemini/grok/luna/muse | security | 无 CL / 非数字 / `Transfer-Encoding: chunked` 直接 `call_next`；10k records JSON 在 422 前全缓冲可 OOM | `api/app.py:527-539`；`api/public/routes.py:452-464`；`src/contracts/api/models.py:139` |
| UF32 | `/docs` `/openapi.json` 匿名 | `medium` | grok | security | `FastAPI(...)` 未关 `docs_url`/`openapi_url`；`main()` 绑 loopback 但 `create_app` 不强制，可枚举 `/internal` 写面 | `api/app.py:469,572` |
| UF33 | DenialAuditSampler overflow undo 错桶 | `medium` | muse | security | `decide` 溢出时 key 改为 overflow 桶；`undo` 仍以 `hash(remote_ip)` 重算，配额永不退 | `src/runtime/security.py:259-264`；`api/dependencies.py:96-101` |
| UF34 | 限流桶按伪造 XFF 分桶且 ipv4_mapped 分裂 | `medium` | muse | security | 空 CIDR 时限流键取自 `request_ip`（伪造 XFF）；`_is_private_peer` 不递归 mapped，`::ffff:*` 与 `_restricted`/`is_internal_ip` 行为分裂 | `src/runtime/security.py:185-213,345-350,502-507,536-537` |
| UF35 | NS5 短途测试假绿与 e2e sqlite3-on-Turso | `high` | grok/luna | tests | 源码扫描、TTL 只测 coalesce、heartbeat 未跨过 lease、未调用局部对象、stub ingest 冒充主链；多个 e2e 在 Turso backend 上 `sqlite3.connect` 报 file is not a database | `tests/unit/test_ns5_phase1_runtime.py`；`test_ns5_phase2.py:96-111`；`test_ns5_phase3.py`；`test_ns5_phase4.py`；`test_ns4_readport_reports.py`；`test_ns4_diagnostic_sidecar.py:24-33`；`test_ns4_jsonl_journal.py`；`test_ns4_cw_soak.py`；`tests/integration/test_ns5_turso_mainchain.py`；e2e `human_review_gate` / `generation_pipeline_contracts` / `intake_reactivate` / `index_rebuild` / `inline_ingress_staging` |
| UF36 | HealthAggregator TTL 死代码 + readiness 持写锁 | `high` | gemini/muse/luna | delivery | `_ttl_seconds` 赋值从不读，`ready()` 仅 in-flight coalesce；`TursoPersistence.readiness()` 持 `_write_lock` 跑 verify+probe。luna 兼称 sidecar 独立连接无真实队列/close，失败折叠为布尔 gate | `src/runtime/health.py:26-45`；`src/persistence/turso/port.py:146-164`；`src/persistence/turso/sidecar.py:62-78` |
| UF37 | `TeamService.create` 并发 PK 走 500 | `medium` | gemini/muse | delivery | SELECT-then-INSERT 未捕 `IntegrityError`；对照 `task_create.py` 已映射 409 | `src/services/teams.py:35-62`；对照 `src/runtime/task/task_create.py:130-141` |
| UF38 | closure/ledger 路径缺失且 partial 被叙述成可收口 | `medium` | luna | delivery | 指定 `docs/issue/v3-ready/VRX5-bounded-execution-activation-closure.md` 不存在；closure 承认 VF36/52/62/40.r/85 等 partial 却仍按可关闭叙述 | `docs/issue/v3-ready/VRX5-bounded-execution-activation-closure.md`（missing）；`docs/code-review/0820-review/VF-ledger-0820-1st-review.md`；`docs/closure/0820-review/NS5-0820-bug-fixes-closure.md` |

---

## 3. verified-findings 台账（逐条独立复核 · 核心）

> 每条 UF 对应恰好一条 VF。证据均为本轮打开的当前 HEAD `file:line`。Phase-2 JSON 为线索；薄证据已抽查。UF18 的 verify_shard **只计** `retrieve`（与 §2.3 / §1 的 intake 6 · retrieve 3 对齐，禁止双 shard 计数）。两份 Phase-2 shard 包并存时取更强 `file:line`（`binder.py:50-51`）的 `valid(子项 overstated)`，class 取更保守的 `[true-bug]`。

### 3.1 台账主表

| VF# | 对应UF | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据（当前代码 file:line）| 初步处置 |
|-----|--------|------|------|------|----------|--------|------------------------------|----------|
| VF1 | UF1 | `immediate_transaction` BEGIN 在 try 外 | `critical` | gemini/grok/luna/muse | `valid` | `[partial-delivery]` | `uow.py:26` `BEGIN` 在 `try` 外；`:28-46` 仅 body/commit 走 `BaseException` rollback。取消 `to_thread(BEGIN)` 使 `__aexit__` 不跑；单例 `turso/port.py:80-81,139-144` / `sqlite_port.py:94-98` 下次 `BEGIN` 毒化至进程重启。NS5-T01 只取消 INSERT 后 body | `fix` |
| VF2 | UF2 | 默认 Turso `/ready` 与 claim 永久 503 | `critical` | gemini/grok/luna/muse | `valid` | `[partial-delivery]` | `turso/port.py:171-177` `required=True` 强制 `concurrent_writes=False`；`health.py:14-24` REQUIRED 含该 bit；`api/app.py:209,291-294` 默认 Settings + `workflow_claim_readiness`；`config.py:23-24` / `default.toml:7` 默认 True；`local_runtime.py:21` 与 `engine.py:97-99` waiver 把测试藏绿 | `fix` |
| VF3 | UF3 | readiness probe 改活库 journal_mode 且不 restore | `critical` | luna | `valid` | `[true-bug]` | `engine.py:24-42` `PRAGMA journal_mode=mvcc`；restore 仅当 `restore_journal_mode and previous!=mvcc`。`turso/port.py:152-156` / `sqlite_port.py:119-120` 探针旁路仍打生产路径且 `restore=False`。`sidecar.py:5-6` 声称永不切 live journal_mode。库存 sqlite 多因 mvcc 切换失败幸免 | `fix` |
| VF4 | UF4 | schema readiness 只探 `mkb_tasks` | `high` | grok/luna | `valid(子项 overstated)` | `[partial-delivery]` | `migration_runner.py:148-163` checksum 后 `return "mkb_tasks" in tables`；`api/app.py:174-179` obs 只查三张观测表。`test_ns5_phase2.py:123-130` 只 DROP `mkb_tasks`。过称切片：D04 55 表闭集不是 NS5-T19 验收谓词 | `fix` |
| VF5 | UF5 | 多路径 lookup 复用 tombstoned stored_object_uuid | `high` | luna | `valid` | `[partial-delivery]` | 见 §3.2.1。014 部分 unique 只拦新 INSERT；lookup 命中墓碑 uuid 后永不 INSERT 新 live 行 | `fix` |
| VF6 | UF6 | migration 014 脏 live 重复 fail-closed 不自愈 | `medium` | muse | `valid-edge` | `[true-deferred]` | `014_ns5_uuid_and_tombstone.sql:17-20` 部分 unique；`migration_runner.py:127-145` 异常 rollback ledger 不前进。`001_initial.sql:1800-1801` 已有全行 unique，正常升级碰不到双 live。NS5 从未承诺 auto-dedup | `defer-with-rationale` |
| VF7 | UF7 | vLLM 共享 client 被 probe 5s 冻结 | `critical` | gemini/grok/muse | `valid` | `[true-bug]` | `local_vllm.py:206-215` 首个 AsyncClient 忽略后续 timeout；`:223-226` probe `min(timeout,5)` 创建；`:182-186,242-245` generate 传 180s 但 `post()` 无 per-request timeout。`api/app.py:183-191` live/probe-first；`:227-232` 默认 180s；`:456-464` lifespan 不 `adapter.aclose()`。`trust_env` 未关是次要洞 | `fix` |
| VF8 | UF8 | salvage 仍同一 Process CLI，非运输 SSOT | `high` | grok | `valid(子项 overstated)` | `[partial-delivery]` | `generation_construct.py:106-122` salvage 含 BACKPRESSURE/EXHAUSTED；`:192-226` 只查 code/CLI/pool/priority/quota 后 `_cli_layered_summary`；`:294-308` 失败后 salvage 不 materialize/admit。`billing.py:16-21` `has_quota` 恒真（NS5 O3/VF23 always-permit，不升本轮 true-bug） | `fix` |
| VF9 | UF9 | generation evidence `"_"` 回退可串 Process | `high` | grok/luna | `valid(子项 overstated)` | `[partial-delivery]` | `generation_evidence.py:9-32` `process_uuid or "_"`；`:50-52` 空 keyed take 再 `take()` 默认桶。`generation_construct.py:287-289` kernel-fail `record` 省略 uuid。过称：本阶段不要求把 pending 改成耐久表；跨 talk 无需重叠 `run_once` | `fix` |
| VF10 | UF10 | Facade retry release-then-finally 双释放 / `release(None)` | `high` | grok/luna | `valid(子项 overstated)` | `[true-bug]` | `facade.py:385-394` RETRYABLE 先 `release` 再 sleep 再 acquire；`:408-409` finally 无条件 `release(lease)`。`ConcurrencyGate.release:134-138` 无 None 守卫，二次 release `RuntimeError`，`lease=None` → `AttributeError`。过称：finally 错误不会被改写成 `INFERENCE_INTERNAL_UNEXPECTED` | `fix` |
| VF11 | UF11 | CLI env 黑名单、stdout 帽在 communicate 后、terminate 未 shield | `high` | gemini/grok/luna | `valid(子项 overstated)` | `[partial-delivery]` | `claude_cli.py:377-379` 只剥 `MKB_*`；`:320-326` 无 `start_new_session`；`:328,338-340` 全缓冲后再比 8MiB；`:332-334,382-406` CancelledError 在 `wait_for` 未捕则跳过 `kill`。过称：`ANTHROPIC_API_KEY` 属 CLI 必需；进程组杀孙进程非 P1-03「child pid gone」谓词；900s 默认不取 Settings 出验收 | `fix` |
| VF12 | UF12 | vectorize upsert SELECT 省略 generation/state 并 UPDATE serving 行 | `critical` | gemini/grok/muse | `valid` | `[partial-delivery]` | `vector_publish_commit.py:334-351` SELECT 无 `index_generation`/`publication_state`；`:381-429` 命中后 `UPDATE publication_state='withdrawn', index_generation=?` 无 indexed fence。`015_vec_coord_generation.sql:7-10` unique 含 generation，拦 INSERT 不拦 UPDATE。过称：rebuild 换 `generation_artifact_uuid` 会走 INSERT | `fix` |
| VF13 | UF13 | HITL approve 不激活 Item；`resolve_gate` 死代码 | `high` | grok/luna | `valid` | `[partial-delivery]` | `acceptance_snapshot.py:106-123` HITL 插入 `deactivated`。`runtime_gates.py:100-103,126-128` activate 只在 `resolve_gate`；全仓 `resolve_gate(` 仅定义。`:197-285` `consume_gate_decision` 只 resume Execution。`lifecycle_publish.py:75-76` 非 active → `PUBLICATION_SERVING_FENCE`。reject SQL 只更新 `lifecycle_state='active'` 行 | `fix` |
| VF14 | UF14 | raw/clean 共用 envelope handle/size，digest≠sha256(bytes) | `high` | grok/luna | `valid` | `[partial-delivery]` | `core.py:388-413` envelope 序列化；`acceptance_snapshot.py:63-64,149-185` 两角色共用 `output_ref`/`output_size` 却写语义 digest。`acquisition_ingest.py:77-84` `raw_digest` 是 `stable_digest({media_type,text})`。`core.py:494-507` rebuild 拆 JSON envelope 读 `state.clean_text`。过称：污染审计/检索宽于当前 rebuild 特例 | `fix` |
| VF15 | UF15 | external_key resolve/write 非原子且 revision_ordinal=1 | `critical` | luna | `valid` | `[true-bug]` | `acquisition_ingest.py:91-108` 先 mint UUID 再独立读 TX resolve；`:135-150` source `INSERT OR IGNORE` 仅 PK uuid，无 kind+key unique；`acceptance_snapshot.py:108-145` item `INSERT OR IGNORE` 后 `revision_ordinal` 字面 1。`001_initial.sql:979` `UNIQUE (team_uuid, intake_item_uuid, revision_ordinal)`。`acquisition_ingest.py:240-247` registered_api 成员 mint 新 uuid 且不 resolve | `fix` |
| VF16 | UF16 | namespace 钉 default、维切换 409、generation 非耐久、purge 合同分裂 | `high` | luna | `valid(子项 overstated)` | `[partial-delivery]` | `vectorize.py:102` `namespace_key='default'`；`vector_publish_commit.py:265-305` 默认 ns + 维 mismatch 409。`vector/models.py:17` `VectorizeChannelFilter` 仍允许 original/summary；`vector_purge.py:68-76` runtime 拒非 `all`；`test_vector_purge_generation.py:105` 构造 `channel_filter="original"`（`:79` 只是 command digest 字段）；`:200-229` 断言 partial original 成功（`:204` `purge_receipt["channel_filter"]=="original"`；`:227-229` original 已删 / summary 仍 live）。过称：无公共 purge HTTP API；generation 预留与 VF17 同根 | `fix` |
| VF17 | UF17 | `_namespace_coordinates` 在单独读 UoW 预留 generation+1 | `medium` | muse | `valid-edge` | `[partial-delivery]` | `vector_publish_commit.py:265-281` 事务关闭后才 `index_generation+1`；`vectorize.py:169` embed 前捕获。指针 CAS `:143-162` 已拒回拨。同 item 重叠才 409；不同 item 共享代数不互 409。非 serving 丢数（那是 VF12） | `fix` |
| VF18 | UF18 | 标题进入 embed，查询侧不带 header | `medium` | grok | `valid(子项 overstated)` | `[true-bug]` | `generation_construct.py:1324-1338` full_construct 传 `metadata_headers`；`binder.py:50-51` full_construct 有 headers 即 `CONSTRUCT_MODE_INVALID`。`vectorize.py:161-166,461-472` 仅 metadata_refresh 剥 prefix；`retrieval_request.py:423-427` 裸 query。过称：主路径 cosine 偏移——titled 文档在 binder 409，根本走不到 embed。真缺口是 VF95 接线与 VF43 binder 互相拆台 | `fix` |
| VF19 | UF19 | 检索水合缓存未被上层激活 | `medium` | gemini | `stale-rejected` | `n/a` | `retrieval_request.py:86-94` `search()` 已 `begin_request_cache`/`end_request_cache`；`retrieval_access.py:113-119` 即 `begin_hydration_cache()`。无 `RetrievalService.retrieve()`。Gemini 只读 access 模块推断 ContextVar 恒 None | `stale-rejected` |
| VF20 | UF20 | 检索 S04/S09 读 fence 持 BEGIN IMMEDIATE 写锁 | `high` | muse | `valid-pre-existing` | `[true-deferred]` | `retrieval_access.py:136,194` 与 `retrieval_rank.py:424,465` 均 `persistence.transaction()` → `turso/port.py:140-144` `_write_lock`+`BEGIN IMMEDIATE`。NS5 VF53 承诺的是 request-scoped cache（已有），不是 `read_transaction` API | `defer-with-rationale` |
| VF21 | UF21 | Worker 取消遗漏 handler_task 与 `_pending` | `high` | gemini | `valid(子项 overstated)` | `[partial-delivery]` | `worker.py:66-75` `create_task(handler)`；`:134-137` finally 只取消 heartbeat。`:79-89` 非 fenced CancelledError **会** `_discard_pending` 再 raise，但不 cancel handler。孤儿后续 `stage()` 可再填满 cap。过称：「accept_outcome 前取消从不 discard」 | `fix` |
| VF22 | UF22 | heartbeat 非取消异常不能 fencing | `high` | grok/luna | `valid` | `[partial-delivery]` | `worker.py:149-162` 循环只在 `heartbeat() is False` 时 fence，只捕 `CancelledError`。`runtime_core.py:539-551` heartbeat 写 TX 可抛。T04 `test_ns5_phase1_runtime.py:61-76` 在 lease 到期前 recover；`:80-100` stub 返回 False 从不 raise | `fix` |
| VF23 | UF23 | outbox.dead 无指标且 trace 被替换 | `high` | gemini/grok | `valid` | `[partial-delivery]` | `runtime_outbox.py:357-377` `trace_uuid=uuid7()` 后 `getattr(self,"metrics",None)`。`runtime_core.py:48-64` 无 metrics 参数；`api/app.py:296-311` 构造不传。S15 禁止替换业务 trace 根 | `fix` |
| VF24 | UF24 | outbox stale owner 状态写入不检查 rowcount | `high` | luna | `valid(子项 overstated)` | `[true-bug]` | `_mark_outbox_dead:343-355` UPDATE 后只要 SELECT 行非空就写 dead 事件；`_release_outbox:400-406` 同。`_complete_outbox:382-386` 无事件（「complete 仍写事件」过称）。`runtime_repair.py:46-52` SELECT 无 status 过滤；`workflow_supervisor.py:51-54` 异常仍 `progressed+=1` | `fix` |
| VF25 | UF25 | ObjectGC 两阶段 unlink 的 TOCTOU 丢字节 | `critical` | gemini/luna/muse | `valid(子项 overstated)` | `[partial-delivery]` | `object_gc.py:196-217` TX1 提交后 `:215` 事务外 unlink；`:219-238` TX2 409 不恢复字节。窗口内同 digest promote+reference 可留下 live catalog 指向已删文件。过称：promote-crash 未编目 orphan 是第 1 轮 VF66.r，不是本 TOCTOU | `fix` |
| VF26 | UF26 | retirement 漏判不可用场景队头阻塞 | `high` | gemini | `valid` | `[partial-delivery]` | `index_retirement.py:320-328` `ORDER BY eligible_at LIMIT 100`。`_active_pointer_tx:561-573` namespace 非 active / serving NULL / pointer 非 active → None。`_close_unavailable_intent_tx:518-529` 只在 item missing/deleted/deactivated 时 abandon。NS5-T06 只种 deactivated | `fix` |
| VF27 | UF27 | `_fail_process_tx` 缺少 fencing_generation CAS | `medium` | gemini | `valid-conditional` | `[true-bug]` | `runtime_outcome.py:454-459` fail UPDATE 无 `fencing_generation`；对照 success/retry/cancelling-lease 均 CAS。今日 BEGIN IMMEDIATE 单写者 + `accept_outcome` 先 identity-check，跨代偷跑不复现；缺 CAS 本身仍是 fencing 洞 | `fix` |
| VF28 | UF28 | Task cancel 不在同 TX 栅栏 Execution | `high` | grok | `valid(子项 overstated)` | `[true-bug]` | `task_commands.py:193-205` 只 CAS Task `cancelling` + enqueue `cancel_execution`。`task_projection.py:3-6,58-61` 显式允许 `cancelling→succeeded`。`workflow_supervisor.py:46-59` **先 outbox 再 run_once**（「先 run_once 再 drain」过称）。真窗口是 in-flight `run_once` 挡住下一 tick 的 cancel outbox | `fix` |
| VF29 | UF29 | 空 CIDR 仍信任私网 peer 的 XFF | `high` | gemini/grok/luna/muse | `valid` | `[partial-delivery]` | `security.py:476-499` 空 cidrs + `_is_private_peer` → XFF 左值。`config.py:25` 默认 `""`。`config.py:62` `metrics_require_token: bool = False`；`api/app.py:518-520` `/metrics` 走 `require_metrics_access`；`api/dependencies.py:185-197` 先 `is_internal_ip(request_ip)` 再可选 token，故伪造 `127.0.0.1` 可过 `/metrics`。`api/dependencies.py:158-174` `/internal` 仍要 operator token（「未认证写」过称） | `fix` |
| VF30 | UF30 | Team/Task PATCH extras 跳过拒密 | `high` | gemini/grok/luna/muse | `valid(子项 overstated)` | `[partial-delivery]` | `api/models.py:44-47` Create 调 `assert_safe_public_data`；`:50-59` / `:362-377` Patch 只要求 mutation。`teams.py:80-112` 与 `task_commands.py:138-177` JSON 入库且 GET 回显。过称：HTTP source URL 是 acquisition locator，不是 PATCH extras 洞；`_SECRET_KEY_PATTERN` vs `_REDACT_KEY` 是更窄的 Create 也有的漏词 | `fix` |
| VF31 | UF31 | body cap 只检查 Content-Length，chunked 可绕过 | `high` | gemini/grok/luna/muse | `valid` | `[partial-delivery]` | `api/app.py:527-539` 仅 `int(Content-Length)>cap` 否则 `call_next`。无 CL / 非数字 / chunked 全缓冲。套件无 `REQUEST_BODY_TOO_LARGE` 用例。诚实 CL>cap 确已 413 | `fix` |
| VF32 | UF32 | `/docs` `/openapi.json` 匿名 | `medium` | grok | `valid-owner-gated` | `[true-deferred]` | `api/app.py:467-469` FastAPI 默认 docs/openapi。NS5 O3 已把第 1 轮 VF79 标 `[true-deferred]`。执行仍要 operator token + 内网闸，属侦察面。`main()` 绑 127.0.0.1 | `deferred-by-owner` |
| VF33 | UF33 | DenialAuditSampler overflow undo 错桶 | `medium` | muse | `valid-edge` | `[partial-delivery]` | `security.py:251-277` decide 满桶改写 `(category,'overflow',bucket)`；`:279-289` undo 仍用 `source_identity` 重算。伤害是 overflow 见证配额丢失，不是准入绕过。新窗口会新桶（「下一分钟合法 DROP」过称） | `fix` |
| VF34 | UF34 | 限流桶按伪造 XFF 分桶且 ipv4_mapped 分裂 | `medium` | muse | `valid(子项 overstated)` | `[partial-delivery]` | `security.py:215-216` `check_ip()` 对调用方传入的 identity 做 hash，本身不提 `request_ip`；接线是 `api/dependencies.py:112` `container.rate_limiter.check_ip(request_ip(request))`（同 VF29）。`:502-507` `_is_private_peer` 不递归 `ipv4_mapped`，对照 `:524-537` `is_internal_ip` 会。过称：mapped 私网不信 XFF 是 P5-01 要的 fail-closed 方向；分桶根因是 VF29 | `fix` |
| VF35 | UF35 | NS5 短途测试假绿与 e2e sqlite3-on-Turso | `high` | grok/luna | `valid(子项 overstated)` | `[partial-delivery]` | 见 §3.2.2。过称：sqlite3-on-Turso 是 owner-gated NS1-V11 / 第 1 轮 VF86，不是本阶段新 true-bug；并非所有 phase3 测试都假 | `partial-fix` |
| VF36 | UF36 | HealthAggregator TTL 死代码 + readiness 持写锁 | `high` | gemini/muse/luna | `valid(子项 overstated)` | `[partial-delivery]` | 见 §3.2.3。过称：sidecar 无真实 queue/close 与布尔 gate 折叠是捆绑 extras；进程内是 `asyncio.Lock` 串行而非 5s SQLite BUSY | `fix` |
| VF37 | UF37 | TeamService.create 并发 PK 走 HTTP 500 非 409 | `medium` | gemini/muse | `valid-edge` | `[partial-delivery]` | `teams.py:35-61` SELECT-then-INSERT 无 IntegrityError 处理。对照 `task_create.py:29-31,130-141` 已映射 409。默认 IMMEDIATE+`_write_lock` 使同进程 waiter SELECT 通常看到已提交行。「双 Pod 必 500」过称 | `fix` |
| VF38 | UF38 | closure/ledger 路径缺失且 partial 被叙述成可收口 | `medium` | luna | `valid(子项 overstated)` | `[partial-delivery]` | `docs/issue/v3-ready/VRX5-…` 不存在；权威是 `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`。P2-05/P2-07 标 ✅（closure:45-47）但对 VF36 TTL 死代码 / VF37 Team PK。过称：缺 VRX5 不是 NS5 承诺制品，也不是代码 blocker | `partial-fix` |

### 3.2 簇子表

#### 3.2.1 VF5 tombstoned catalog lookup

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `generation_artifacts.py:561-565` | SELECT digest/size 无 `tombstoned_at IS NULL` | `valid` | 走 live helper |
| `config_snapshots.py:332-335` | 同上 | `valid` | 同上 |
| `index_rebuild_commit.py:304-309` | 同上 | `valid` | 同上 |
| `scatter_intake.py:669-686` | `_require_catalogued_object` 过滤；`_catalog_stat` 不过滤 | `valid` | `_catalog_stat` 对齐 live |
| `task_create.py:399-403` | `ORDER BY created_at ASC LIMIT 1` 无墓碑过滤，偏爱最旧（墓碑）行 | `valid` | live-only + 未命中则新 uuid |
| `artifacts.py:141-143` | 正确 live lookup | 对照 GREEN | 抽成共享 helper |

#### 3.2.2 VF35 假绿测试簇

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `test_ns5_phase2.py:96-111` | 名含 TTL，只 `gather` 两次并发 `ready()`；顺序 `both()` 从未调用 | `valid` | 顺序两次 `ready()` 断言 probe==1，或删死参数 |
| `src/runtime/health.py:26-44` | `_ttl_seconds` 只赋值不读 | `valid` | 并入 VF36 |
| `test_ns5_phase1_runtime.py:47-57` | CLI timeout 断言 `hang.exists()` 非 child pid/returncode | `valid` | 断言 pid 消失 |
| `test_ns5_phase1_runtime.py:61-75` | `lease_seconds=1` 在 0.8s recover，心跳未跨过到期 | `valid` | recover 在 lease 后仍 running |
| `test_ns4_readport_reports.py:10-13` | `inspect.getsource` | `valid` | 实例化 ReadService 查询 |
| `test_ns4_diagnostic_sidecar.py:24-33` | 局部 MkbError 从不 insert | `valid` | 实例化 sidecar |
| `test_ns4_jsonl_journal.py:10-14` | 读 collect.py 文本 | `valid` | 调 `_journal_row` |
| `test_ns4_cw_soak.py:30-57` | ThreadPool 后断言未用 product.code | `valid` | SELECT COUNT |
| `tests/integration/test_ns5_turso_mainchain.py:16-81,85-105` | 真实 HTTP `intake.ingest` 经 `create_app`/`TestClient` 跑到 `succeeded`；inspect 只看 generation artifacts + intake items，从不查 `mkb_vector_records` 或 retrieval（非 stub ingest） | `valid` | 经 PersistencePort 走 vectorize+retrieval |
| e2e `generation_pipeline_contracts.py:36` vs `:93` 等 | `:36-37` 仅 Turso Settings waiver；`sqlite3.connect` 在 `:93`。同分裂：`test_human_review_gate.py:37` vs `:116`，`test_index_rebuild.py:25` vs `:120`，`test_intake_reactivate.py:25` vs `:146`，`test_inline_ingress_staging.py:29` vs `:101` | `valid-owner-gated` | 第 1 轮 VF86 / NS1-V11 → §5.4 |
| `tests/local_runtime.py:21` | `concurrent_writes_required=False` | 显式 waiver，非恒真 | 生产 503 归 VF2 |

#### 3.2.3 VF36 TTL / 写锁 / sidecar extras

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `health.py:26-44` | `_ttl_seconds` 死代码；`ready()` 只 coalesce `_inflight`，结束后清空 | `valid` | 实现 TTL 或删除参数 |
| `turso/port.py:146-164` | readiness 持 `_write_lock` 跑 `verify_migrations`+探针 | `valid` | 探针改旁路连接；schema_ok 可缓存 |
| `sqlite_port.py:105-124` | 同模式；注释称锁是故意的 | `valid` | 锁可保留；缺陷是热路径无缓存 |
| `sidecar.py:33-78` | `max_queue` 无队列；无 `close()`；`api/app.py:456-464` lifespan 不关 sidecar | **bundled extra** | 可选 close；勿假装有界队列 |
| closure P2-05 ✅ | 以误名 coalesce 测试收口 | `valid` | 翻 🟡（VF38） |

---

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

**A. 按三类归属（问责视图 · ★主视图）**

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | `8` | `VF3 VF7 VF10 VF15 VF18 VF24 VF27 VF28` | §5.2 本阶段**必修** |
| `[partial-delivery]` | `26` | `VF1 VF2 VF4 VF5 VF8 VF9 VF11 VF12 VF13 VF14 VF16 VF17 VF21 VF22 VF23 VF25 VF26 VF29 VF30 VF31 VF33 VF34 VF35 VF36 VF37 VF38` | §5.2 补齐；剩余切片 §5.4 |
| `[true-deferred]` | `3` | `VF6 VF20 VF32` | §5.4 承接（带 reopen 触发器） |
| `n/a`（rejected / 无需改）| `1` | `VF19` | 不进三类 |

> 三类合计（不含 `n/a`）= `8+26+3 = 37` = 全部未了结 valid 缺口；`n/a 1` + 37 = 38。与 §1 一致。

**B. 按处置（disposition 视图）**：

- **`fix`（本会话修）**：`VF1 VF2 VF3 VF4 VF5 VF7 VF8 VF9 VF10 VF11 VF12 VF13 VF14 VF15 VF16 VF17 VF18 VF21 VF22 VF23 VF24 VF25 VF26 VF27 VF28 VF29 VF30 VF31 VF33 VF34 VF36 VF37` = **32 项**
- **`partial-fix`**：`VF35 VF38` = **2**
- **`defer-with-rationale`**：`VF6 VF20` = **2**
- **`deferred-by-owner`**：`VF32` = **1**
- **`stale-rejected`**：`VF19` = **1**
- **`acknowledge`**：无 = **0**

> 32+2+2+1+1+0 = 38，与 §1 一致。

### 4.2 净增承重盲区（peer-vs-peer）

本合成人不是四位 reviewer 之一；下列是**彼此漏报的最高价值独家项**（多方重叠的核心簇不记「净增」）。

- **Luna 独家高价值**：`VF3` 活库 `journal_mode=mvcc` 且不 restore（critical，其它三方完全未报）；`VF15` ingest `external_key` 非原子 + `revision_ordinal=1`（critical）；`VF5` tombstone lookup；`VF24` outbox stale-owner 无 rowcount；`VF38` closure 过关叙述。若只听 Gemini/Grok/Muse，生产库耐久设置会被探针改写且无人追究。
- **Grok 独家高价值**：`VF8` salvage 仍同 Process CLI（运输 SSOT 半交付）；`VF28` Task cancel 不栅栏 Execution（与 S02-T009 冲突）；`VF18` VF43/VF95 互相拆台（cosine 子项过称，409 主项真）。若只听 Luna/Gemini，会漏掉 cancel→succeeded 与 salvage 占错池。
- **Gemini 独家高价值**：`VF21` 取消不杀 `handler_task`；`VF26` retirement 剩余 POINTER_UNAVAILABLE 队头；`VF27` fail 缺 fencing CAS。VF19 独家但被驳回。
- **Muse 独家高价值**：`VF17` generation 跨 UoW 预留；`VF20` 检索持写锁（合法 defer）；`VF33` overflow undo 错桶；`VF6` 014 脏 unique（合法 defer）；`VF34` XFF 分桶（根因并入 VF29）。
- **四方/三方重叠的承重核**（非净增，但是本轮必修中心）：`VF1` UoW BEGIN、`VF2` 默认 `/ready` 503、`VF7` vLLM 5s、`VF12` serving UPDATE、`VF25` GC TOCTOU、`VF29`/`VF31` 空 CIDR XFF 与 chunked body。

### 4.3 带证据驳回的跨-reviewer 误报

| V# | 误报方 | 误报内容 | 反证（file:line）| 结论 |
|----|--------|----------|-------------------|------|
| VF19 | gemini-R14 | `_HYDRATION_CACHE` 存在但 `RetrievalService` 从不 `begin_request_cache()`，每 hit 重复读盘 | `retrieval_request.py:86-94` `search()` 已 begin/end；`retrieval_access.py:113-119` 即 hydration cache；无 `RetrievalService.retrieve()` | `stale-rejected` |

> 其余「子项 overstated」**整条仍成立**，过称句写在对应 VF 行（如 VF4 的 55 表闭集、VF8 billing 恒真、VF10 BACKPRESSURE 被改写成 INTERNAL、VF11 ANTHROPIC 泄漏、VF16 公共 purge HTTP、VF18 主路径 cosine、VF21 从不 discard、VF24 complete 仍写事件、VF25 promote-crash orphan、VF28 supervisor 循环顺序、VF29 `/internal` 未认证写、VF32 未认证写面、VF35 全部测试假绿、VF36 5s BUSY、VF38 缺 VRX5 是代码 blocker）。不升格为整条驳回。

---

## 5. 初步修复方案（preliminary fix plan）

### 5.1 修复策略

先封**进程/数据不可恢复洞**（UoW BEGIN 取消毒化、journal_mode 活库突变、vLLM 5s 冻结、GC TX1-unlink-TX2、vectorize UPDATE serving、ingest 非原子 identity），再修**准入与车道**（默认 Turso `/ready`、HITL activate、salvage 运输 SSOT、lease heartbeat/cancel、outbox rowcount/metrics），然后补**安全边界**（空 CIDR 不信 XFF、PATCH 拒密、chunked body cap、CLI env/stdout/kill），最后拆**假绿测试与 closure 过关叙述**。`[true-bug]` 本轮全部进 §5.2，禁止改写成 deferred。`[partial-delivery]` 本轮补齐合同；D04 全表清单、sqlite3-on-Turso harness、`/docs`、014 自愈、检索 `read_transaction` 作为剩余切片进 §5.4。每条 code fix 必须先有会红的断言。

不变量：单例连接在 BEGIN 取消后必须可再 `BEGIN`；默认 Turso 叶 worker `/ready` 必须为 ready 且 `claim_next` 不被 CW 门挡住；readiness 不得把生产文件的 `journal_mode` 从 wal 切成 mvcc；probe 不得把 generate timeout 冻在 5s；同坐标再 vectorize 不得把 serving `indexed` COUNT 打到 0；同 `external_key` 不得插入第二 item / 因 `revision_ordinal=1` 失败。

### 5.2 逐项修复计划表

| V# | 计划修法 | 目标文件 | falsifiable 验证（修前应 RED）| migration / owner-gate? | 批次 |
|----|----------|----------|-------------------------------|-------------------------|------|
| VF1 | `BEGIN` 放进与 commit 同一 `try/except BaseException`；非成功退出 shield rollback，不确定则 `discard()` | `uow.py` `turso/port.py` `sqlite_port.py` `test_ns5_uow_cancel.py` | patch `execute` 阻塞 BEGIN，取消等待协程后再 `transaction()` INSERT；第二 BEGIN 不得 `within a transaction` | no | 1 |
| VF2 | 保留 `concurrent_writes_probe` 为 MVCC 测量；`HealthAggregator.REQUIRED` 改 `write_path_ready`（串行 IMMEDIATE 足够），或默认 Turso 叶 `concurrent_writes_required=False` 并文档化。禁止只在 waiver 下证 ready | `turso/port.py` `health.py` `config.py` `api/app.py` `test_turso_driver.py` `test_readiness_composition.py` | 默认 Settings(turso, required=True) migrate+bootstrap 后 `health.ready()['status']=='ready'` 且 claim 非 NotReadyError | no | 1 |
| VF3 | 禁止对生产文件做突变 journal_mode 探针。改 temp clone / boot scratch 缓存布尔；若必须活文件探针则 `restore_journal_mode=True` 并断言第二连接仍见探针前 mode | `engine.py` `turso/port.py` `sqlite_port.py` `test_turso_driver.py` | 连接 A 记 journal_mode；`readiness()` 后连接 B 不得从 wal 变成 mvcc | no | 1 |
| VF4 | `verify_migrations` 扩小闭集：`mkb_tasks/processes/executions/outbox/stored_objects/object_references/vector_records/publication_proofs/intake_items`；checksum drift 仍 fail-closed | `migration_runner.py` `test_ns5_phase2.py` | DROP `mkb_outbox`（或 processes/vector_records）后 `schema_migration` 仍 True 则 RED | no | 2 |
| VF5 | 抽 `get_live_stored_object(team,digest,size)`（`tombstoned_at IS NULL`），generation/config/rebuild/scatter `_catalog_stat`/task_create 全改用；未命中 INSERT 新 uuid | 见 §3.2.1 + `artifacts.py` | GC/tombstone 后再 catalog 同 digest → 新 live `stored_object_uuid` 且有 live reference | no | 2 |
| VF6 | 本轮不生产自愈。可选后续：CREATE UNIQUE 前 `GROUP BY HAVING COUNT(*)>1` 抛带 id 的 MkbError | `014_*.sql` `migration_runner.py` | 去 001 unique 后种两 live 同行再 apply 014 → 迁移失败且 schema_migration false（**期望** fail-closed） | 仅当真实升级 DB 在 UNIQUE 上挂 | 5.4 |
| VF7 | `client.get/post` 传 per-request timeout（或独立 probe client 并 aclose）；共享池只复用连接。lifespan `await adapter.aclose()`。`trust_env=False` | `local_vllm.py` `api/app.py` `test_ns5_phase3.py` | probe() 再 generate()，MockTransport 睡 6s，`generate_timeout_seconds=180` 不得 `INFERENCE_TRANSPORT_RETRYABLE` | no | 1 |
| VF8 | salvage 时 materialize/admit durable NI Process（或再 admit 到 NI 池）；NI 满/CLI 未绑 fail-closed。从 salvage set 去掉 `INFERENCE_BACKPRESSURE` | `generation_construct.py` `runtime_core.py` `test_ns5_phase3.py` | salvage 必须增加 NI occupancy/dispatch_pool；BACKPRESSURE 不得调 `cli.run` | billing 仍 always-permit | 3 |
| VF9 | 删除 `_DEFAULT_EVIDENCE_KEY` 与空 take 回退。record/take 强制 `process_uuid`。`generation_construct.py:289/1011/1100` 传入 `command.process_uuid` | `generation_evidence.py` `generation_construct.py` `test_ns5_phase3.py` | `record(..., process_uuid=None)` 后 process B 的 `write_pending` 对该 invocation 插 0 行 | no | 3 |
| VF10 | `release(lease)` 后 `lease=None` 再 sleep；只赋新 acquire。`finally: if lease is not None: release` | `facade.py` `test_inference_runtime.py` | (1) RETRYABLE + sleep 中取消 → `CancelledError` 无 RuntimeError；(2) reacquire None → `INFERENCE_BACKPRESSURE` 无 AttributeError | no | 3 |
| VF11 | `_cli_child_env` 改 allowlist（PATH/LANG/HOME/ANTHROPIC_*/CLAUDE_*）。stdout 流式字节帽，溢出即 kill。cancel 路径 shield `_terminate_process`，terminate 内捕 CancelledError 仍 kill | `claude_cli.py` `test_ns5_phase3.py` `test_ns5_phase1_runtime.py` | 子 env 无 `AWS_SECRET_ACCESS_KEY`；>8MiB writer 在 communicate 返回该缓冲前被杀；terminate 中取消后 `returncode is not None` | 进程组杀孙 → 5.4 | 3 |
| VF12 | `_existing_vector_coordinate_uuid` / `_upsert_vector_record_tx` 加 `AND index_generation=? AND publication_state='withdrawn'`（或拒绝 `indexed`）。新世代必须 INSERT 新 `vector_record_uuid`。保留 pointer CAS | `vector_publish_commit.py` `vectorize.py` P4-10 测试 | publish G=N indexed 后同 dual-channel 再 vectorize；旧 serving gen indexed COUNT 不得变 0 | no | 4 |
| VF13 | `consume_gate_decision` 在 approve/reject 调 `_apply_human_review_item_lifecycle_tx`。reject SQL 须处理已 deactivated HITL 插入。`resolve_gate` 删除或保持死代码 | `runtime_gates.py` `acceptance_snapshot.py` `test_human_review_gate.py` | `require_human_review` + approve 后 `lifecycle_state='active'` 且 publication 成功；reject 保持非 active | no | 4 |
| VF14 | raw bytes 与 clean UTF-8 分两个 CAS 对象（各自 digest/size/handle/media_type）。acceptance envelope 只当元数据。rebuild `read_verified(clean_handle)` 且 `sha256(bytes)==content_digest`，禁止 JSON peeling | `acceptance_snapshot.py` `core.py` `acquisition_ingest.py` | accept 后 raw/clean 两行 `sha256(storage.read(handle))==content_digest` 且 `size_bytes==len(bytes)` | no | 4 |
| VF15 | 加耐久 unique `(team_uuid, source_kind, normalized_external_key)`；source/item/revision 与 resolve 同一 UoW。同指纹 replay；内容变则 `MAX(ordinal)+1` + predecessor CAS。registered_api scatter 同样栅栏 | `acquisition_ingest.py` `acceptance_snapshot.py` `001_initial.sql` 或后续 migration | 两次相同 key ingest：第二不得 201+Task failed；并发 COUNT(items)=1 | **migration** | 4 |
| VF16 | namespace 按 (model_key, version, adapter, dimension) 键或显式 rebuild；409 仅用于原地改 active default。generation 预留并入 VF17。收窄 `VectorizeChannelFilter` 为 `all` 并改写 e2e，或实现带新 proof+pointer CAS 的 partial purge | `vectorize.py` `vector_publish_commit.py` `vector_purge.py` `vector/models.py` `test_vector_purge_generation.py` | 已有 default ns 的 team 改 embed 维 → 新 namespace 而非 409。`test_vector_purge_generation` 对 `_assert_purge_command` 今日 RED | no | 4 |
| VF17 | 废 early read；在 vectorize outcome TX 内 `UPDATE mkb_vector_namespaces SET index_generation=index_generation+1 RETURNING`（或记录先 NULL generation，publish 时填） | `vector_publish_commit.py` `vectorize.py` | 两重叠同 item vectorize 不得都写 N+1；败者不得留下 stranded N+1 withdrawn 行且 409 | no | 4 |
| VF18 | 选定单一配方并同时用于写与查询：(a) full_construct 去掉 `_title_from_layered`，title 只当 facet；或 (b) 允许 headers、持久化，且 `_embed_query` 用同一 `content_full()` 前缀。禁止 construct 接线而 binder 禁止。替换 `test_title_enters_content_full` 为 admit+embed 路径测 | `generation_construct.py` `binder.py` `vectorize.py` `retrieval_request.py` `lsrag_compiler/models.py` | 带 `context_meta.title='Notice'` 的 layered `bind_construct(full_construct, headers=…)` 今日 RED `CONSTRUCT_MODE_INVALID`；修后要么 body-only embed，要么 query 带同一 prefix | no | 4 |
| VF20 | 推迟。reopen：ingest 期间 Turso 检索 503。然后 `PersistencePort.read_transaction()`（独立读连接，BEGIN/READONLY，无 `_write_lock`），检索 SELECT 改走它 | `ports.py` `turso/port.py` `sqlite_port.py` retrieval_* | 持写 TX 时 eligibility SELECT 今日阻塞/可 503；修后不得取 `_write_lock` | reopen 见 §5.4 | 5.4 |
| VF21 | `worker.py` finally：handler 未 done 则 cancel+suppress await，再 `_discard_pending`。外部 CancelledError 对齐 fenced 路径（retryable_failure）或 await 取消后的 handler 再 discard | `worker.py` `artifacts.py` | 取消 `run_once` 于 handler.sleep：`handler_task.cancelled()` 且 `_pending=={}` | no | 1 |
| VF22 | `_heartbeat_loop except Exception: fenced.set(); handler_task.cancel(); return`。T04：lease 过期后才 recover；加 raising-heartbeat 测 | `worker.py` `test_ns5_phase1_runtime.py` | patch heartbeat raise RuntimeError；2s handler + lease=1s → handler 取消且 recover 见 expired/fenced，不得成功 accept | no | 1 |
| VF23 | `WorkflowCoreMixin.__init__` 加 `metrics: MetricRegistry | None`；`api/app.py:296` 传入。`_record_outbox_dead_tx` 查 owning task/execution trace 而非 uuid7()。仅 `rowcount==1` 后 increment（绑 VF24） | `runtime_outbox.py` `runtime_core.py` `api/app.py` | create_app 容器强制 JSON-poison outbox 后 GET `/metrics` 的 `mkb_outbox_dead_total` 不得为 0；dead 事件 `trace_uuid` 等于 Task 的 | no | 2 |
| VF24 | 每个 owner-conditioned UPDATE 要求 `rowcount==1` 才 `_record_outbox_dead_tx`/metrics；0 则 return。repair SELECT 过滤 `status IN ('pending','in_flight')`。supervisor 异常不 `progressed+=1` | `runtime_outbox.py` `runtime_repair.py` `workflow_supervisor.py` | 租约过期被第二 owner claim 后，stale owner `_mark_outbox_dead` 不得插入 `outbox.dead` | no | 2 |
| VF25 | TX1 CAS `deleting/pending_delete` 使新 reference 无法挂上；或 unlink 改 rename 到隔离路径，仅 TX2 tombstone 后不可恢复删除。TX2 见新 live ref 则 restore。禁止把 missing-live 当新 reference 后的可接受 fail-closed | `object_gc.py` `local_store.py` `artifacts.py` | TX1 commit 与 unlink 之间交错 `validate_and_commit` 同 digest：不得 TX2 409 且 `read_verified` `OBJECT_MISSING` 而 `mkb_object_references.released_at IS NULL` | 目录 SSOT → 5.4 | 1 |
| VF26 | 每个 `_active_pointer_tx` None 当不可用：namespace inactive/deleted、item 无 serving、pointer 非 active 则 abandon（并软删 retired gen），除非文档化的 rollback 必须留 intent | `index_retirement.py` `test_ns5_retirement_stuck.py` | 100 条 namespace 停用 open intent + 1 条健康 due；`scan_once(limit=100)` 两次后健康 intent 必须出现 | no | 2 |
| VF27 | `_fail_process_tx` 加 `AND fencing_generation=?`；仅 `rowcount==1` 写 evidence/events。recover / `_fail_expired_ready_tx` 同一 CAS | `runtime_outcome.py` | 测试 TX 内抬 fencing_generation 并 status=running，用旧 process dict `_fail_process_tx` → 新世代不得 failed | no | 2 |
| VF28 | Task.cancel 同 UoW CAS 当前 root Execution 为 cancelling 并 bump claimed/running Process `fencing_generation`（复用 `_cancel_execution_tree_tx`）。`accept_outcome` 在 Task `cancelling` 时拒 succeeded，或去掉 success-wins 使 cancelling 只到 cancelled | `task_commands.py` `task_projection.py` `runtime_outcome.py` `workflow_supervisor.py` | 长 handler 中途 POST cancel；handler 返回 succeeded → Task 不得 ended succeeded（或 Execution 在 accept 前必须已 cancelling 且 outcome 被拒） | no | 2 |
| VF29 | 删除 `elif peer and _is_private_peer: return presented`。空 CIDR 永远返回 ASGI peer。仅当 cidrs 非空且 `_ip_in_cidrs(peer, cidrs)` 才抄 XFF | `security.py` `dependencies.py` `test_security_boundary.py` `test_ns5_phase5.py` | peer `10.0.0.1` + 空 CIDR + XFF `127.0.0.1` → `request_ip=='10.0.0.1'`；该 XFF 不得让无 token `/metrics` 200 | no | 5 |
| VF30 | `TeamPatchRequest`/`TaskPatchRequest` `model_validator(mode='after')` 调 `assert_safe_public_data(self.payload_extra)`。可选服务层再拦。写时拒绝而非 GET 静默 redact | `api/models.py` `teams.py` `task_commands.py` `test_ns5_phase5.py` | `TeamPatchRequest(expected_revision=0, payload_extra={'apiKey':'sk-live'})` 必须 ValidationError；库无 sk-live | no | 5 |
| VF31 | ASGI receive 包装累计 `len(body)`，超 cap 立即 `REQUEST_BODY_TOO_LARGE` 413；保留 CL 快拒 | `api/app.py` `test_ns5_phase5.py` | 无 CL 的 chunked `max_request_bytes+1` POST `/v1/teams` → 413，不得落到 handler/422 | no | 5 |
| VF32 | Owner session：`FastAPI(..., docs_url=None, redoc_url=None, openapi_url=None)` 或挂 `require_operator_token`。可选 internal router `include_in_schema=False` | `api/app.py` `api/internal/routes.py` | 今日 `TestClient.get('/openapi.json')` 200；关闭后 404 或 401/403 | **owner** | 5.4 |
| VF33 | `decide` 返回 `(disposition, effective_key)` 并传入 `undo`；或 sampler 记住 overflow rewrite | `security.py` `dependencies.py` `test_security_boundary.py` | `max_buckets=1`；decide 第二 IP（overflow）后 undo，第三 IP 仍应 DETAIL | no | 5 |
| VF34 | 先修 VF29（空 CIDR 身份=peer）。`_is_private_peer`/`_ip_in_cidrs` 递归 `ipv4_mapped` 对齐 `is_internal_ip`，**不要**用该递归重开空 CIDR XFF 信任 | `security.py` `test_ns5_phase5.py` `test_security_boundary.py` | 空 CIDR + peer 10.0.0.1 + 循环 XFF 1.1.1.{n} 必须共用一个 IP 桶。`::ffff:127.0.0.1` 在 `_is_private_peer` 与 `is_internal_ip` 同类 | no | 5 |
| VF35 | 本阶段：重写 TTL/heartbeat/CLI/ReadPort/sidecar/journal 测试使谓词真红。P6-05：`test_ns5_turso_mainchain` 经 PersistencePort 走 vectorize+retrieval。**不**新增 sqlite3-on-Turso 检查 | 见 §3.2.2 | no-op heartbeat + 立刻返回的 `_terminate_process` + 未读 TTL：所列三测今日仍 PASS。空 ReadService 方法体 `test_ns4_readport_reports` 仍 PASS | sqlite3-on-Turso → 5.4 | 6 |
| VF36 | 实现 TTL 缓存（inflight coalesce + 过期前返回 `_last_result`，token/bootstrap 变更失效）或删除 `ttl_seconds` 并改测试名。verify/probes 移到既有 bypass 连接。sidecar `close()` 可选 | `health.py` `turso/port.py` `sqlite_port.py` `sidecar.py` `test_ns5_phase2.py` `api/app.py` | `HealthAggregator(ttl_seconds=5)` 两次顺序 `ready()` → probe count==1（今日 2） | sidecar 真队列未承诺 | 1 |
| VF37 | Team INSERT 对齐 TaskCreateMixin：`IntegrityError` + `_is_unique_conflict` → 同指纹 replay / 不同指纹 ConflictError 409。共享 matcher | `teams.py` `task_create.py` `test_ns5_phase2.py` | stub INSERT raise `UNIQUE constraint failed: mkb_teams.team_uuid` → 409/replay 而非裸 IntegrityError | no | 2 |
| VF38 | 保持 `NS5-0820-bug-fixes-closure.md` 为唯一 closure SSOT。P2-05/P2-07 从 ✅ 翻 🟡 并引用 VF36/VF37。§7 在 VF14/VF16（第 1 轮 VF36/VF52）修完或 owner 升级前停止声称 no-free-defer。不发明 VRX5 | closure + NS5 plan + 第 1 轮 ledger | grep closure P2-05/P2-07 ✅ 而 VF36 顺序 TTL 与 VF37 IntegrityError 仍 RED | 不建 VRX5 文件 | 6 |
| VF19 | 无代码变更。可选 ratchet：断言 `search()` 调 `begin_request_cache` 且同 generation 两次 `load_retrieval_body` 只读存储一次 | `retrieval_request.py` `test_retrieval_access.py` | patch `begin_request_cache` raise 会失败——今日不失败，因为已调用 | n/a | ack |

### 5.3 批次 / 依赖

- **批次 1（进程存活 / 准入 / 耐久设置）**：`VF1 VF2 VF3 VF7 VF21 VF22 VF25 VF36` — 不修则叶进程写路径、/ready、lease、对象字节都不可信。
- **批次 2（CAS / schema / outbox / team）**：`VF4 VF5 VF23 VF24 VF26 VF27 VF28 VF37` — 依赖批次 1 的 UoW 不再被 cancel 毒化。
- **批次 3（推理车道）**：`VF8 VF9 VF10 VF11` — 依赖批次 1 的 vLLM timeout 与 worker cancel。
- **批次 4（intake / 向量 / 检索写路径）**：`VF12 VF13 VF14 VF15 VF16 VF17 VF18` — VF16 namespace 与 VF17 预留同一批做完；VF12 必须在任何再 vectorize 测试之前。
- **批次 5（安全）**：`VF29 VF30 VF31 VF33 VF34` — VF34 依赖 VF29。
- **批次 6（测试与治理）**：`VF35 VF38` — 假绿测试改完才能证明批次 1–5。
- **承接**：`VF6 VF20 VF32` 与 VF4.r / VF11.r / VF25.r / VF35.r / VF36.r / VF38.r。

### 5.4 承接登记（`[true-deferred]` + `[partial-delivery]` 剩余切片）

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接位置 |
|----|--------------|------|----------|----------------|----------|
| VF6 | `[true-deferred]` | `defer-with-rationale` | 001 全行 unique 已禁止正常升级出现双 live；NS5 未承诺 migration 自愈；fail-closed 正确 | 真实升级 DB 在 014 报 `UNIQUE constraint failed` | `deferred-items-ledger`；可选 loud duplicate-live MkbError |
| VF20 | `[true-deferred]` | `defer-with-rationale` | NS5 VF53 交付的是 hydration cache+chunking（已有），不是 `read_transaction` API；naive BEGIN 无锁不安全 | `RETRIEVE_DEPENDENCY_ELIGIBILITY`/`VECTOR` 503 与 `claim_next` 或 `/ready` 同时出现 | PersistencePort.read_transaction charter |
| VF32 | `[true-deferred]` | `deferred-by-owner` | NS5 O3 已把第 1 轮 VF79 `/docs` 标 true-deferred；执行面仍 token+IP 闸 | 公网/`0.0.0.0` bind 或 TrustedHost 放宽 | owner session；`NS5-0820-bug-fixes.md` O3 |
| VF4.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮只补核心业务表小闭集，不枚举 D04 55+ 表 | 新核心表加入 serving/claim 热路径却不在 verify 闭集 | D04 schema 清单同步 |
| VF11.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮保证 child pid 在 cancel/timeout/overflow 后 `returncode is not None`；进程组/孙进程不在 P1-03 谓词 | CLI 挂起带 grandchild 的 hang fixture | CLI 边界 charter |
| VF25.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮修 TX1-unlink-TX2 live-ref 丢字节；promote-crash 未编目 orphan / 目录 SSOT 仍是第 1 轮 VF66.r | GC `scan_once` 收不到 filesystem-only orphan | 第 1 轮 VF66.r / directory CAS SSOT |
| VF35.r | `[partial-delivery]` 剩余切片 | `deferred-by-owner` | sqlite3.connect(Turso file) 是 NS1-V11 / 第 1 轮 VF86；本轮不新增 sqlite3 检查 | 重写 e2e harness 时 | owner freeze；查询只走 PersistencePort |
| VF36.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮修 TTL 死代码+热路径写锁；sidecar `max_queue` 真有界队列从未承诺 | sidecar 在诊断洪泛下丢行且无 drop-receipt | sidecar bounded-queue charter |
| VF38.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮只把 P2-05/P2-07 翻 🟡 并禁止发明 VRX5；closure §7 no-free-defer 要等 VF14/VF16（第 1 轮 VF36/VF52）代码修完才能诚实 | 那两条代码 VF 仍 🟡 却把 closure 标 implementation-complete | NS5 closure 下一轮回填 |

---

## 6. 处置执行回填（fixes 落地后 · append-only）

> NS6 执行回填 `2026-08-20`。不改写 §0–§5。

| VF | 处置 | 落地 | 验证 |
|----|------|------|------|
| VF1 | fix | `uow.py` BEGIN 入 try | `test_ns6_uow_begin_cancel` |
| VF2 | fix | REQUIRED=`write_path_ready` | `test_ns6_default_ready` |
| VF3 | fix | scratch CW probe | `test_ns6_journal_mode_restore` |
| VF7 | fix | per-request vLLM timeout | `test_ns6_vllm_timeout` |
| VF12 | fix | 不 UPDATE indexed | `test_upsert_does_not_update_indexed_rows` |
| VF15 | fix | 016 unique + 同 TX | migration 016 |
| VF24 | fix | outbox rowcount CAS | `test_stale_owner_cannot_insert_outbox_dead` |
| VF27 | fix | fail fencing | `test_stale_fencing_fail_does_not_kill_new_generation` |
| VF28 | fix | cancel 非 succeeded | `test_cancel_prevents_succeeded_task` |
| VF29 | fix | 空 CIDR 不信 XFF | `test_empty_cidr_ignores_private_xff` |
| VF35 | fix | 假绿短途改成真调用 | `test_ns4_readport_reports` / sidecar insert / journal `_journal_row` |
| VF38 | fix | NS5 closure P2-05/P2-07 翻 🟡 | `NS5-0820-bug-fixes-closure.md` |
| VF6/20/32/86 | deferred | 未改 class | deferred-items-ledger NS6 |

> **NS6 自我审核 ↔ 修复循环回填 `2026-08-20`（append-only；不改 §0–§5 class）**。

| VF | 处置 | 落地 | 验证 |
|----|------|------|------|
| VF12 | fix 补强 | 017 把 `ux_vec_coord_active_layer_a` 纳入 `index_generation`；T21 真跑 `_upsert_vector_record_tx` | `test_upsert_does_not_update_indexed_rows` COUNT indexed gen=1 且 gen=2 INSERT |
| VF13 | fix 补测 | `consume_gate_decision` 经公共 approve；PersistencePort 读 `lifecycle_state` | `test_human_review_approve_activates_item_via_port` |
| VF14 | fix 补测 | accept 后 `read_verified` sha256；rebuild 不 JSON peel | `test_raw_clean_cas_digests_are_sha256_of_bytes` + HTTP `test_accept_cas_digests_match_read_verified_bytes` |
| VF15 | fix 补强 | registered_api 同 TX resolve+`normalized_external_key`；accept 同指纹 replay revision/change_set | `test_migration_016_adds_source_external_key_unique` COUNT=1；`test_second_same_external_key_is_replay_not_failed` items=1 + accept succeeded |
| VF16 | fix 补强 | purge 合同收窄 `channel_filter=all`；e2e 改 PersistencePort、去掉 sqlite3-on-Turso | `test_purge_generation_soft_deletes_only_the_requested_generation`；`test_namespace_key_splits_layer_a` |
| VF17 | fix 补测 | 两 TX generation CAS，败者 rowcount=0 且无 stranded N+1 | `test_overlapping_vectorize_generation_cas` |
| VF18 | fix 补测 | body-only 配方；helper 不再把 title 当绿 | `test_full_construct_rejects_title_headers`；`test_title_enters_content_full` body-only |
| VF25 | fix 补强 | 缺 quarantine API fail-closed；path `quarantine/<team>/` | `test_missing_quarantine_api_is_fail_closed`；`test_ns6_gc_toctou` |
| VF35 | fix 补强 | journal 真 import `_journal_row`；CLI timeout 断言 pid 已死；sidecar 查库 | `test_ns4_jsonl_journal` / `test_cli_timeout_kills_child` / `test_sidecar_inserts_into_migrated_turso` |
| VF2 mega | fix 补强 | 默认 Settings（无 CW/NV waiver）ingest→vector COUNT→retrieval | `test_generation_mainchain_is_inspected_via_turso_port` |
| VF29 | fix 补测 | 空 CIDR + 公网 peer 的 XFF 不得放行 `/metrics` | `test_empty_cidr_does_not_admit_metrics_via_xff` |
| VF8 | 维持 substrate-fit | salvage 走同一 CLI gate；满门 BACKPRESSURE | `test_salvage_occupies_ni_and_skips_backpressure` 调 `_salvage_summary_via_cli` |
| VF6/20/32/86 | deferred | 未改 class；(a) sqlite3-on-Turso harness 仍 NS1-V11 | deferred-items-ledger |

---

## 7. AGENT 评审绩效（0820 第 2 轮）

> 评价对象: Gemini / Grok / Luna / Muse Spark on MKB 0820 second-pass
> 评价人: Grok (0820-2nd-pass-ledger workflow)
> 评价时间: 2026-08-20
>
> 本节消费 §3/§4 已复核台账，不重开 VF 判定。文档状态仍为 `triaged`（§6 未回填，不写 close-type）。

### 0. 评价结论

- **一句话评价**：四审 72 条仅 Gemini VF19 被整条驳回；Luna 独家钉死活库 `journal_mode` 突变与 `external_key` 非原子两个 critical `[true-bug]`，是本轮最佳主审。Grok 零误报并钉死 salvage/cancel；Muse 证据最密但净增全是 medium/edge；Gemini 把四方承重核钉到 file:line，却贡献了本轮唯一 stale，并漏掉 Luna 的两处独家 critical。
- **最佳AGENT**：Luna（总分 7.7；§4.3 零驳回；独家两个 7-blocker：VF3 / VF15）
- **最高价值 Finding**：VF3 readiness probe 改活库 `journal_mode` 且不 restore（`luna-R11`；生产探针把可见模式从 wal 切成 mvcc，其它三方打开过 `engine.py` / turso probe 仍未报）

**评分校准（相对 §3/§4，独立核对）**：

- 六维均值与 §2 评分表一致（顺序：证据链 / 判断严谨 / 修法 / 协作 / 覆盖面 / 严重级）：Gemini `(8.0+6.0+8.0+8.0+7.0+6.5)/6=7.25→7.3`；Grok `(8.0+7.5+8.5+8.0+7.5+6.0)/6=7.58→7.6`；Luna `(8.5+7.5+8.0+7.5+8.5+6.0)/6=7.67→7.7`；Muse `(8.4+8.0+8.3+8.4+6.2+6.5)/6=7.63→7.6`。以评分表为准；v0.4 校准段曾把 Luna/Muse 若干维对调，本版已纠正，**未改总分**。
- 未发现「stale-rejected 被标 true-positive」类矛盾。`gemini-R14=VF19` 标 `stale`，与 §4.3 唯一驳回行一致。其余 71 条均落入 `valid*` VF。
- `luna-R17` 按簇只挂 VF11（源 id 不重复计），文内点到的 vLLM 5s 冻结不获 VF7 源 id——与 §2 映射纪律一致，不把 Luna 算进 VF7 覆盖。
- 7-blocker 覆盖（独立点名 `VF1 VF2 VF3 VF7 VF12 VF15 VF25`）：Gemini 5/7（漏 VF3/VF15）；Grok 4/7（漏 VF3/VF15/VF25）；Luna 5/7（漏 VF7 单列与 VF12）；Muse 5/7（漏 VF3/VF15）。覆盖分与此同向：Luna 因两处独家 critical 仍最高，Grok 因漏三方同报的 VF25 低于 Gemini/Muse 的 blocker 命中，但总 finding 面更宽。
- `partial` 对应 ledger `valid(子项 overstated)` 的过称切片，不把整条降成驳回。`missed-by-others` 仅用于 §2.2 无 peer 源 id 的项（含合法 `[true-deferred]` 独家侦察，如 VF6/VF20/VF32）。

### 1. Findings 质量清点

事后判定小计（72 条原始 finding 全列；不丢任一方）：

| AGENT | 条数 | true-positive | missed-by-others | partial | false-positive | stale |
|-------|------|---------------|------------------|---------|----------------|-------|
| Gemini | 16 | 10 | 3 | 2 | 0 | 1 |
| Grok | 20 | 16 | 4 | 0 | 0 | 0 |
| Luna | 21 | 8 | 6 | 7 | 0 | 0 |
| Muse | 15 | 9 | 5 | 1 | 0 | 0 |

| AGENT | 问题编号 | 原始严重程度 | 事后判定 | Finding 质量 | 分析与说明 |
|---------|----------|--------------|----------|--------------|------------|
| Gemini | `R1→VF1` | `critical` | `true-positive` | `excellent` | 四方重叠的 critical 真阳性；BEGIN 在 try 外、单例连接永久 `in_transaction`、补丁形状均准确 |
| Gemini | `R2→VF2` | `critical` | `true-positive` | `excellent` | 默认 `concurrent_writes_required=True` 与 Turso 强制 False 导致 `/ready` 与 claim 永 503；证据与级别正确 |
| Gemini | `R3→VF7` | `critical` | `true-positive` | `excellent` | probe 5s 固化共享 client 且 post 不传 timeout；修法可直接落地。aclose/trust_env 由 grok 补，不伤主项 |
| Gemini | `R4→VF12` | `critical` | `true-positive` | `excellent` | SELECT 漏 `index_generation`/`publication_state`，就地 UPDATE 打穿 serving indexed；与 VF12 完全对齐 |
| Gemini | `R5→VF29` | `high` | `true-positive` | `good` | 空 CIDR 仍信私网 XFF 主项成立；叙述里突破 `/internal` 偏过（仍需 operator token，过的是 `/metrics` 内网闸） |
| Gemini | `R6→VF30` | `high` | `partial` | `mixed` | PATCH 跳过 `assert_safe_public_data` 为真；把 `_SECRET_KEY_PATTERN` 对 `_REDACT_KEY` 漏词写成主危害属过称（Create 同样漏） |
| Gemini | `R7→VF26` | `high` | `missed-by-others` | `excellent` | 独家有效。namespace 停用/空 serving/非 active pointer 不 abandoned，`ORDER BY eligible_at LIMIT 100` 永久队头阻塞 |
| Gemini | `R8→VF25` | `high` | `true-positive` | `good` | TX1→unlink→TX2 TOCTOU 丢字节主项成立；原评 high 而台账 critical。promote-crash orphan 过称是 luna 的，非 Gemini |
| Gemini | `R9→VF23` | `high` | `true-positive` | `good` | WorkflowRuntime 未注入 metrics、dead 计数静默为真；同簇 grok 还钉了 `trace_uuid=uuid7()` 替换，Gemini 未覆盖 |
| Gemini | `R10→VF21` | `high` | `missed-by-others` | `mixed` | 独家有效核心：finally 只取消 heartbeat、handler 成孤儿。「accept_outcome 前取消从不 discard」过称——非 fenced CancelledError 会 discard |
| Gemini | `R11→VF27` | `medium` | `missed-by-others` | `good` | 独家 true-bug：`_fail_process_tx` 缺 `fencing_generation` CAS。未标明今日单写者+identity-check 使跨代偷跑不复现（valid-conditional） |
| Gemini | `R12→VF31` | `medium` | `true-positive` | `good` | 仅看 Content-Length、chunked/缺 CL 全缓冲为真；原评 medium 而台账 high，且标非 blocker |
| Gemini | `R13→VF36` | `medium` | `true-positive` | `good` | `ttl_seconds` 死代码、每次 ready 打库为真；原评 medium 而台账 high。sidecar 无队列是 luna extras，非 Gemini 过称 |
| Gemini | `R14→VF19` | `medium` | `stale` | `weak` | 本轮唯一 stale-rejected。`search()` 已 begin/end_request_cache；无 `RetrievalService.retrieve()`。只读 access 模块就发明未激活 |
| Gemini | `R15→VF37` | `medium` | `true-positive` | `good` | Team.create 未捕 IntegrityError 为真，但属 valid-edge：同进程 IMMEDIATE+_write_lock 下后到者通常看到已提交行 |
| Gemini | `R16→VF11` | `low` | `partial` | `mixed` | 只抓住 terminate 未 shield 一片且标 low；UF11 的 env 黑名单与 stdout 帽在 communicate 之后由 grok/luna 补齐。S16 还把 env 白名单标成 done |
| Grok | `R1→VF2` | `critical` | `true-positive` | `excellent` | 四方同报的默认 Turso `/ready` 永 503；waiver 与 `engine.py` 反向假绿都坐实，严重级正确 |
| Grok | `R2→VF13` | `high` | `true-positive` | `excellent` | 与 Luna 同钉 `resolve_gate` 死代码 + `consume_gate_decision` 不激活；reject SQL 空操作也写清 |
| Grok | `R3→VF12` | `high` | `true-positive` | `good` | UPDATE serving 行属实且为 blocker 簇；原级 high 低于台账 critical |
| Grok | `R4→VF8` | `high` | `missed-by-others` | `good` | 独家：salvage 仍占 local Process/CLI。billing `has_quota` 恒真是 NS5 O3 后延，不构成本轮 true-bug |
| Grok | `R5→VF9` | `high` | `true-positive` | `good` | 与 Luna 同报 `"_"` 回退；重叠 `run_once` 会必现属过称，本阶段未要求耐久 pending 表 |
| Grok | `R6→VF29` | `high` | `true-positive` | `excellent` | 四方同报空 CIDR 信 XFF；Grok 正确落到 `/metrics` 默认无 token，未把 `/internal` 写成未认证写 |
| Grok | `R7→VF30` | `high` | `true-positive` | `good` | PATCH extras 跳过拒密属实；范围比 Luna 的 source-descriptor 兼称更准 |
| Grok | `R8→VF31` | `high` | `true-positive` | `good` | 四方同报 chunked/缺 CL 绕过；有 CL 的 413 路径也承认，判断克制 |
| Grok | `R9→VF7` | `high` | `true-positive` | `good` | probe 5s 冻 generate 属实，兼 aclose/`trust_env`；原级 high 低于台账 critical，且未标 blocker |
| Grok | `R10→VF28` | `high` | `missed-by-others` | `mixed` | 独家 true-bug：cancel 不同 TX 栅栏 Execution，`cancelling→succeeded` 真。但把 supervisor 写成先 `run_once` 再 drain，实测是先 outbox；真窗口是 in-flight `run_once` |
| Grok | `R11→VF22` | `high` | `true-positive` | `excellent` | 与 Luna 同报心跳只捕 CancelledError；额外拆穿 T04 在 lease 到期前 recover 的假绿 |
| Grok | `R12→VF4` | `high` | `true-positive` | `mixed` | 只探 `mkb_tasks` 属实；把 D04 55 表闭集当成 NS5-T19 谓词过称 |
| Grok | `R13→VF14` | `high` | `true-positive` | `good` | 与 Luna 同报 raw/clean 共用 envelope 且 digest≠bytes；rebuild 已吃私货。污染审计/检索略宽于当前特例 |
| Grok | `R14→VF18` | `medium` | `missed-by-others` | `mixed` | 独家 true-bug：VF95 接线与 VF43 binder 互拆。主路径 cosine 偏移过称——titled `full_construct` 在 binder 已 409，走不到 embed |
| Grok | `R15→VF35` | `high` | `true-positive` | `mixed` | 与 Luna 同报 TTL/heartbeat/源码扫描假绿。误把 `turso_mainchain` 写成 stub ingest（实为真实 HTTP ingest）；sqlite3-on-Turso 是 VF86/owner-gated 而非本阶段新 true-bug |
| Grok | `R16→VF32` | `medium` | `missed-by-others` | `good` | 独家有效侦察面；台账判 `valid-owner-gated` / NS5 O3 已后延。Grok 主张本轮顺手关，不升宪法冲突，协作上可接受 |
| Grok | `R17→VF1` | `medium` | `true-positive` | `good` | BEGIN 在 try 外属实且为 critical blocker；Grok 标 medium 且非 blocker，是本轮最大的严重级误判 |
| Grok | `R18→VF23` | `medium` | `true-positive` | `good` | 与 Gemini 同报 dead 无 metrics + trace 被 uuid7 替换；修法已点到 rowcount，原级低于台账 high |
| Grok | `R19→VF11` | `medium` | `true-positive` | `good` | stdout 帽在 communicate 后 + terminate 未 shield 属实；env allowlist/进程组切片在对齐表而非 finding，原级低于 high |
| Grok | `R20→VF10` | `medium` | `true-positive` | `mixed` | 与 Luna 同报的 true-bug：finally `release(None)`。过称 finally 错误会被改写成 `INFERENCE_INTERNAL_UNEXPECTED`；原级 medium 偏低 |
| Luna | `R1→VF1` | `high` | `true-positive` | `good` | 四方同报；BEGIN 在 try 外属实、建议 discard 可执行。标 high 低于复核 critical，且误写连接池（实为单例连接毒化） |
| Luna | `R2→VF10` | `high` | `true-positive` | `excellent` | 与 grok 同报的 `[true-bug]`；本地复现 unbalanced release，修法 `lease=None` 与 §5.2 一致 |
| Luna | `R3→VF15` | `critical` | `missed-by-others` | `excellent` | 独家 critical `[true-bug]`；同 key 二次 201 后任务 failed 已本地复现，`ordinal=1` 与 `registered_api` 分路均钉到行号 |
| Luna | `R4→VF13` | `high` | `true-positive` | `excellent` | 与 grok 同报；本地 public approve 200 后 item 仍 deactivated，activate 只在无人调用的 `resolve_gate` |
| Luna | `R5→VF22` | `high` | `true-positive` | `good` | 与 grok 同报；准确区分 `heartbeat=False` 与非取消异常两条路径，修法指向共享 fence |
| Luna | `R6→VF24` | `high` | `missed-by-others` | `good` | 独家 `[true-bug]`；owner 条件 UPDATE 不看 rowcount 属实。子项过称：complete 路径并不写事件 |
| Luna | `R7→VF9` | `high` | `partial` | `mixed` | 与 grok 同报；`process_uuid or '_'` 与默认桶属实，但把内存 dict 升格为必须耐久表超出本阶段合同 |
| Luna | `R8→VF25` | `critical` | `partial` | `mixed` | 与 gemini/muse 同报的 critical TOCTOU 属实。捆绑 promote-crash 未编目 orphan，ledger 明确记为第 1 轮 VF66.r 过称 |
| Luna | `R9→VF5` | `high` | `missed-by-others` | `excellent` | 独家；014 live unique 与五条 lookup 未滤 tombstone 的对照表与 §3.2.1 逐点对齐，并给出 live helper 修法 |
| Luna | `R10→VF2` | `critical` | `true-positive` | `excellent` | 四方同报；默认 `required=True` 与 Turso 强制 `concurrent_writes=False` 冲突写清，并指出测试画像 waiver 藏绿 |
| Luna | `R11→VF3` | `critical` | `missed-by-others` | `excellent` | 本轮最高净值独家 `[true-bug]`；probe 打 `PRAGMA journal_mode=mvcc` 且 `restore=False`，外部连接 wal→mvcc 已本地复现 |
| Luna | `R12→VF4` | `high` | `partial` | `mixed` | 与 grok 同报；checksum 后只探 `mkb_tasks` 属实。建议版本化全 schema manifest 把验收扩到 D04 闭集，属过称切片 |
| Luna | `R13→VF14` | `high` | `true-positive` | `good` | 与 grok 同报；raw/clean 共用 envelope 而 digest≠sha256(bytes) 属实，独立制品修法可执行 |
| Luna | `R14→VF16` | `high` | `missed-by-others` | `mixed` | 独家 namespace/维切换 409 与 purge 合同分裂属实。捆绑 generation 跨 UoW 预留（实为 VF17）并暗示公共 purge HTTP，子项过称 |
| Luna | `R15→VF29` | `high` | `true-positive` | `good` | 四方同报；peer=`10.0.0.1` 空 CIDR + XFF=`127.0.0.1` 已本地复现。`/internal` 未认证写略过称（仍要 operator token） |
| Luna | `R16→VF31` | `high` | `true-positive` | `good` | 四方同报；无 CL/chunked 直接 `call_next` 属实，ASGI receive 累计 413 修法与 §5.2 一致 |
| Luna | `R17→VF11` | `high` | `partial` | `mixed` | 按簇只挂 VF11（gemini/grok 同报）。env 黑名单/communicate 后帽/terminate 未 shield 属实；ANTHROPIC 泄漏、进程组杀孙、900s 过称。文内点到 vLLM 5s 冻结（UF7）但未获源 id |
| Luna | `R18→VF30` | `high` | `partial` | `mixed` | 四方同报的 PATCH extras 跳过拒密属实。兼称 HTTP source descriptor/signed URL 落库被 ledger 点名为过称捆绑 |
| Luna | `R19→VF36` | `medium` | `partial` | `good` | 与 gemini/muse 同报；`ttl_seconds` 两次 ready 双探针已本地复现。sidecar 无队列/close 为 bundled extra；标 medium 低于复核 high |
| Luna | `R20→VF35` | `high` | `partial` | `good` | 与 grok 同报；source-grep/吞异常/弱断言属实。sqlite3-on-Turso 是 owner-gated 第 1 轮 VF86，不是本阶段新 true-bug |
| Luna | `R21→VF38` | `medium` | `missed-by-others` | `mixed` | 独家文档治理；closure 把 partial 叙述成可收口属实。缺 VRX5 不是 NS5 承诺制品，却标 blocker=yes，子项过称 |
| Muse | `R1→VF1` | `critical` | `true-positive` | `excellent` | BEGIN 在 try 外、取消毒化单例连接；严重级与修法（shield rollback+discard）与 ledger 一致。四方重叠承重核 |
| Muse | `R2→VF2` | `critical` | `true-positive` | `excellent` | `required=True` 强制 `concurrent_writes=False` 却进 REQUIRED，默认画像 `/ready` 与 claim 永 503；二选一修法贴 ledger |
| Muse | `R3→VF36` | `high` | `partial` | `mixed` | `ttl_seconds` 死代码 + readiness 持写锁属实；5s SQLite BUSY 过称（进程内是 `asyncio.Lock`），且误标 blocker。sidecar extras 非本条 |
| Muse | `R4→VF12` | `critical` | `true-positive` | `excellent` | SELECT 无 generation/state，UPDATE 可改 serving indexed 行；P4-10 残留分析精确。与 gemini/grok 共享 critical |
| Muse | `R5→VF29` | `high` | `true-positive` | `mixed` | 空 CIDR 盲信私网 XFF 属实，可伪 `127.0.0.1` 过 `/metrics`；过称未认证写 `/internal`（仍要 operator token）。误标 blocker |
| Muse | `R6→VF30` | `high` | `true-positive` | `good` | Patch 跳过 `assert_safe_public_data`、Create 已拦，核心成立。未叠 luna 的 HTTP source extras。blocker 旗标过重 |
| Muse | `R7→VF31` | `high` | `true-positive` | `good` | 仅查 Content-Length，chunked/缺长可全缓冲 OOM；ASGI receive 流式计数修法贴 ledger。high 准，blocker 过 ledger |
| Muse | `R8→VF7` | `medium` | `true-positive` | `mixed` | probe `min(timeout,5)` 固化共享 client、generate 180s 无 per-request timeout 属实且为 `[true-bug]`；标 medium/非 blocker 严重低估。未提 aclose/`trust_env` |
| Muse | `R9→VF20` | `high` | `missed-by-others` | `good` | 独家：S04/S09 只读 fence 走 BEGIN IMMEDIATE。`valid-pre-existing` / `[true-deferred]`（NS5 交的是 hydration cache 非 `read_transaction`）。建议 fix 略越权 |
| Muse | `R10→VF25` | `high` | `true-positive` | `mixed` | TX1→unlink→TX2 活引用丢字节属实；标 high+defer-with-rational，ledger 为 critical+本轮 fix。与 VF66.r 目录 SSOT 捆在一起 |
| Muse | `R11→VF17` | `medium` | `missed-by-others` | `excellent` | 本审最高价值独家：只读事务预留 `generation+1`，publish 才 CAS。valid-edge（同 item 重叠才 409）。UPDATE RETURNING 修法即 ledger |
| Muse | `R12→VF37` | `medium` | `true-positive` | `good` | Team SELECT-then-INSERT 未捕 IntegrityError，对照 `task_create` 409。valid-edge；「双 Pod 必 500」在 IMMEDIATE+_write_lock 下过称 |
| Muse | `R13→VF33` | `medium` | `missed-by-others` | `good` | 独家：decide 改 overflow 桶、undo 仍按 `hash(ip)`。`effective_key` 修法贴 ledger。valid-edge；「下一分钟合法 DROP」过称（新窗口新桶） |
| Muse | `R14→VF34` | `medium` | `missed-by-others` | `mixed` | 独家但子项过称：限流键来自 `dependencies.request_ip` 接线（同 VF29），`check_ip` 自身不提 IP；mapped 私网不信 XFF 是 P5-01 fail-closed 方向 |
| Muse | `R15→VF6` | `medium` | `missed-by-others` | `good` | 独家：014 部分 unique 遇双 live 失败且 ledger 不前进。valid-edge / `[true-deferred]`（001 全行 unique 已拦正常升级；NS5 未承诺自愈）。建议 fix 越权 |

### 2. 多维度评分 - 单向总分10分
选手清单: Gemini 3.7 Flash, GPT-5.6-luna, Grok 4.6, Muse Spark 1.2

| AGENT  | 总分 | 证据链完整度 | 判断严谨性 | 修法建议可执行性 | 协作友好度 | 找到问题的覆盖面 | 严重级别准确度 |
|--------|-----|------|------|------|------|------|------|
| Gemini | 7.3 | 8.0 | 6.0 | 8.0 | 8.0 | 7.0 | 6.5 |
| Grok   | 7.6 | 8.0 | 7.5 | 8.5 | 8.0 | 7.5 | 6.0 |
| Luna   | 7.7 | 8.5 | 7.5 | 8.0 | 7.5 | 8.5 | 6.0 |
| Muse   | 7.6 | 8.4 | 8.0 | 8.3 | 8.4 | 6.2 | 6.5 |

- **Gemini（7.3）**：共享 P0 钉得很死，并独家抓住 retirement 队头与 worker 不杀 handler；但 R14 是本轮唯一整条误报，且漏掉 `journal_mode` / `external_key` 两个独家 critical。Gemini 把四方承重核（VF1 UoW BEGIN 取消毒化、VF2 默认 `/ready` 503、VF7 vLLM 5s、VF12 serving UPDATE）钉到 file:line 与可落地补丁，并净增 VF21 handler 不取消、VF26 POINTER_UNAVAILABLE 队头、VF27 fail 缺 CAS。证据链与修法整体强（8/8），协作结构完整。硬扣在判断严谨性：VF19 是 72 条里唯一 stale-rejected（只读 access 模块就断言 RetrievalService 未激活缓存，`search()` 早已 begin/end）。覆盖面中上（16 条、5/7 blocker），但漏 Luna 独家 critical VF3/VF15 与 Grok 的 salvage/cancel-fence。严重级别把 GC TOCTOU 写成 high、CLI 取消写成 low，并把 6 条 high 升成 blocker。
- **Grok（7.6）**：覆盖面宽、修法可执行，并独家钉死 salvage/cancel/title 三处真缺口，但把 UoW BEGIN 降成 medium 且漏报 `journal_mode`、ingest 原子性与 GC TOCTOU，严重级系统性偏低。Grok 20 条全部成立、零误报，证据几乎都带 file:line，修法可落地，对齐表也诚实标出 15 项 done。独家贡献是 VF8 运输 SSOT 半交付、VF28 `cancelling→succeeded` 真 bug、VF18 binder/embed 互拆（cosine 过称）。减分来自三处机制写反（supervisor 循环顺序、mainchain 被写成 stub ingest、主路径 cosine），以及把 VF1/VF7/VF12 这类生产毒化从 critical 降成 high/medium，同时把 HITL/salvage/假绿测升成 blocker，优先级会带偏实现者。相对 Luna 的 VF3/VF15 独家 critical，Grok 的净增是高价值但非最高承重；7-blocker 只打到 4/7（漏 VF25）。
- **Luna（7.7 · 最佳）**：独家钉死 VF3 活库 `journal_mode` 突变与 VF15 `external_key` 非原子两个 critical true-bug，本地复现扎实，但 20/21 标 blocker、多项子断言过宽，且漏掉三方同报的 VF12 serving UPDATE。Luna 21 条全部入账且零 stale/INVALID，净增承重是 VF3/VF15 两个 `[true-bug]` critical（另有独家 VF5/VF24/VF16/VF38）。证据链含多处本地复现（wal→mvcc、同 key 201 后 failed、approve 后仍 deactivated、gate unbalanced release、空 CIDR 伪造 XFF），修法大多可直接对照 ledger §5.2。短板是严重级校准（20/21 blocker vs 复核 7 个）以及 R8/R12/R14/R17/R18 厨房水槽捆绑导致子项 overstated；覆盖面上完全漏报三方同报的 VF12，并把 VF7 的 5s 冻结埋进 R17 而未单列。若只听 Gemini/Grok/Muse，生产库耐久设置会被探针改写且无人追究——这是本轮选 Luna 的决定性权重，而不是因为 21 条最长。
- **Muse Spark（7.6）**：零误报、证据密、修法可贴 ledger，独家钉死 VF17 跨 UoW 预留与 VF33 overflow undo，但漏 VF3/VF15 两个独家 critical，并把 vLLM 5s 与 GC TOCTOU 降成非 blocker。15/15 落入 valid* VF、§4.3 零驳回，file:line 与修法（BEGIN 进 try、`write_path_ready`、SELECT 加 generation/state、`effective_key`、UPDATE RETURNING）几乎逐条可执行，正面事实与 blocker/follow-up 分层也比 Luna 的 20 blocker 克制。扣分在比较权重：5 条独家全是 medium/edge/deferred（VF6/17/20/33/34），没有一条独特 critical；读过 `engine.py`/turso probe 却未报活库 `journal_mode`（VF3），也未报 `external_key` 非原子（VF15），8 个 `[true-bug]` 只打到 VF7。严重级两头偏：VF7 标 medium、VF25 标 high 且建议 defer（ledger 均为 critical+fix），同时把 VF29/30/31/36 升为 blocker。R3 的 5s BUSY、R5 的 `/internal` 未认证写、R14 把限流键算进 `security.py` 而非 dependencies 接线，是主要过称。严谨性 8.0 为本轮最高，覆盖面 6.2 为本轮最低。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | `2026-08-20` | `Grok (0820-2nd-pass-ledger workflow)` | Phase-1 UF merge only：4 方 72 条原始 finding → 38 条 UF（UF1–UF38）；状态 `triaged`；未填 VF 判定 |
| `v0.2` | `2026-08-20` | `Grok (0820-2nd-pass-ledger workflow)` | Phase-3 VF inject：§3/§4/§5 回填；VF-n==UF-n；状态仍 `triaged`（本工作流未执行代码修复） |
| `v0.3` | `2026-08-20` | `Grok (0820-2nd-pass-ledger workflow)` | Phase-4 consistency：§1 verify_shard 改为 intake 6 / retrieve 3（UF18 只计 retrieve，去掉双 shard 计数）；§2.2 UF14 标题改为 raw/clean 共用 envelope，digest≠bytes（去掉第 1 轮 VF36 残留）；§2.2 UF28 改为「不在同 TX 栅栏 Execution」。证据纠偏：VF16 purge 断言改引 `test_vector_purge_generation.py:105,200-229`；VF34 limiter 改引 `security.py:215-216` `check_ip` + `dependencies.py:112`；VF35 mainchain 改引真实 HTTP ingest `:16-81,85-105`（非 stub）；VF29 补 `config.py:62` / `dependencies.py:158-174,185-197` / `app.py:518-520`；VF35 e2e 把 Turso waiver 与 `sqlite3.connect` 分行；VF15 UNIQUE 改引 `001_initial.sql:979` 并钉 `acquisition_ingest.py:240-247`。未改 class/verdict/disposition，未丢 VF。 |
| `v0.4` | `2026-08-20` | `Grok (0820-2nd-pass-ledger workflow)` | Phase-5 agent eval：§7 由占位换成完整 AGENT 评审绩效（Gemini/Grok/Luna/Muse Spark）；最佳 Luna、最高价值 VF3（`luna-R11`）；§1 TL;DR 加一行指针。独立核对六维均值与 §3/§4 映射（7-blocker 覆盖 Gemini/Luna/Muse 5/7、Grok 4/7；唯一 stale 为 `gemini-R14=VF19`），未改分数、未把子项过称升格 INVALID。文档状态仍 `triaged`；§0–§5 除 TL;DR 指针外未改写；§6 仍空 |
| `v0.5` | `2026-08-20` | `Grok (parent QA after workflow)` | 抽查：72 条 R# 全映射、UF1–UF38 ↔ VF1–VF38 1:1、§1/§4.1 计数对齐；坐实 VF1 `uow.py:26`、VF2 `turso/port.py:171-177`、VF3 `restore_journal_mode=False`、VF7 `local_vllm.py:206-245` `post()` 无 per-request timeout、VF15 `revision_ordinal` 字面 1、VF19 `search()` 已 `begin_request_cache`。修正 §7 校准段维顺序（与评分表对齐，总分不变）。 |
| `v0.6` | `2026-08-20` | `Grok (NS6 self-audit cycle)` | §6 append：自我审核后补强 VF12/15/16/25/35 与 T21–T26/T35 谓词；不改 §0–§5 class。 |
