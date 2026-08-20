# MKB 0820 第 1 轮跨 Reviewer 统一台账（UF → VF）

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 初步修复方案）。
> **谁写**：**实现者 / 合并人**（不是某一位 reviewer）。在收齐**全部** agent 的审查文件后，由实现者把多份独立审查平铺、合并、逐条对当前真实代码独立复核，形成单一权威台账，并给出初步修复方案。
> **为什么独立成文**：过去的做法是把这份「统一 + verified 台账」append 在某位 reviewer 审查文件的底部。现改为**独立文件 track**——一个标的、一轮合并 = 一份 ledger，互不污染各 reviewer 原件，便于跨轮检索与状态推进。

---

> **元信息（置顶 · 必填）**
>
> | 字段 | 值 |
> |------|----|
> | **审查标的** | `MKB 全仓 HEAD @ 0820 first-round` |
> | **审查阶段 / 轮次** | `第 1 轮合并` |
> | **合并 / 核查人（实现者）** | `Grok (0820-review-ledger workflow)` |
> | **合并日期** | `2026-08-20` |
> | **文档状态** | `triaged` |
>
> **审查来源锚定（被合并的 reviewer 制品 — 必须逐份列全）**：
> - `docs/code-review/0820-review/0820-reviewed-by-gemini.md` — `critical / 45 findings`（27 blocker；最高 critical）
> - `docs/code-review/0820-review/0820-reviewed-by-GPT.md` — `critical / 45 findings`（28 blocker；最高 critical）
> - `docs/code-review/0820-review/0820-reviewed-by-grok.md` — `critical / 28 findings`（11 blocker；最高 critical）
> - `docs/code-review/0820-review/0820-reviewed-by-muse.md` — `critical / 36 findings`（21 blocker；最高 critical）
>
> **对照真相（逐条 re-verify 时回看的源）**：
> - `README.md`
> - `docs/baseline/domain-truth/` D01–D08、S01–S16
> - `docs/closure/new-start/deferred-items-ledger.md`
> - 代码根：`api/`、`src/`、`intake/`、`tests/`

---

## 0. 合并方法与核查纪律

> **本节只立规矩，不写结论。** 说明合并了哪几份、用什么纪律复核。

- **合并范围**：`4` 份独立审查全部 finding 平铺（gemini 45 + GPT 45 + grok 28 + muse 36 = **154** 条原始 finding）。未丢 low/info。
- **核查纪律（硬）**：
  1. **reviewer 的结论仅作线索**。每条判 `valid` 的项，均由实现者**亲自 grep / Read 当前真实代码**坐实，关键证据带 `file:line`。
  2. 与任一方冲突，**以实测为准**；自审初稿被推翻处必须在 §4.2 显式 self-correct。
  3. **已纠正的跨-reviewer 误报**必须在 §4.3 带证据列出，不得静默吞掉。
  4. 严重级别**取多方最严**；同一问题被多方提及合并为一条统一编号。
- **统一编号前缀**：本文件 Phase-1 使用 **`UF`（unified-finding）**。Phase-2 起写入 **`VF`（verified-finding）**，且 **`VF-n == UF-n`**（编号一一对应，不重排）。禁止在 Phase-1 填写 VF 判定。

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

> Phase-4 已按当前 HEAD 修正 citation 撞名与 class/disposition 不一致；Phase-5 评审绩效见 §7（最佳 GPT / 最高价值 VF3）；文档状态仍为 `triaged`（本工作流未执行代码修复）。

- **一句话裁定**：4 方 154 条原始 finding → 103 条 VF（VF1–VF103 与 UF 一一对应）；`101` 条属实（含 by-design / overstated 子项），`2` 条 stale-rejected（VF6 executescript 回退；VF92 检索栅栏 tautology/e2e）。本阶段欠账是 **75 [true-bug] + 12 [partial-delivery]**，另 **9 [true-deferred]** 诚实后延。最关键生产缺口：UoW 取消污染唯一连接、Turso CW 探针剧场、sidecar native abort、30s lease 无 heartbeat、live vectorize 静默丢层仍签完整 proof、HTML 抹平换行、重复文本错锚、检索 UUID 截断 1000、单通道 purge 破坏 Proof、非法 outbox 卡住唯一 supervisor、retirement 死循环、假绿测试簇、以及 wheel 缺 migration SQL。
- **合并后统一 finding 数**：`103`（来自 `154` 条原始 finding 去重；VF# = UF#）。
- **按 verdict**：`valid 62` · `valid(子项 overstated) 19` · `valid-edge 8` · `valid-conditional 2` · `valid-owner-gated 1` · `valid-by-design 9` · `INVALID 0` · `stale-rejected 2`。
- **按三类归属 ★**：`[true-bug] 75（VF1 VF3–VF5 VF7–VF19 VF21 VF22 VF24 VF26–VF29 VF31 VF34–VF36 VF38–VF40 VF42–VF45 VF47–VF56 VF58–VF61 VF63–VF65 VF67–VF72 VF75 VF76 VF78 VF80–VF85 VF87 VF94 VF98–VF103）` · `[partial-delivery] 12（VF2 VF30 VF37 VF41 VF46 VF62 VF66 VF73 VF91 VF93 VF95 VF96）` · `[true-deferred] 9（VF23 VF74 VF77 VF79 VF86 VF88–VF90 VF97）` · `n/a 7（VF6 VF20 VF25 VF32 VF33 VF57 VF92）`。
- **按处置**：`fix 81` · `partial-fix 6（VF30 VF37 VF41 VF46 VF66 VF91）` · `defer-with-rationale 7（VF74 VF77 VF79 VF88 VF89 VF90 VF97）` · `deferred-by-owner 2（VF23 VF86）` · `acknowledge 5（VF20 VF25 VF32 VF33 VF57）` · `stale-rejected 2（VF6 VF92）`。
- **blocker 数**：`14`（编号：`VF1 VF2 VF3 VF9 VF10 VF27 VF28 VF29 VF47 VF54 VF61 VF63 VF85 VF93`；均为复核后 `critical` 且本阶段须修的生产/交付缺口）。
- **净增承重盲区（peer 相对彼此）**：Grok 独家钉死非法 outbox 冻住唯一 supervisor（VF61）与指针/向量世代 CAS（VF44/VF55）；GPT 独家钉死 sidecar native abort（VF3）与 wheel 缺 SQL（VF93）；Gemini 独家钉死 HTML 抹平换行 / 重复锚点 / 单通道 purge / retirement 死循环（VF28/VF29/VF54/VF63）；Muse 独家钉死 claim 每轮只 fail 一个过期项、公共 extras 驼峰 secret、以及 constitution 探针被 e2e 豁免（VF70/VF78 子集/VF91）。详见 §4.2。
- **按 verify_shard**：`persist 8` · `infer 18` · `intake 20` · `retrieve 14` · `workflow 14` · `security 10` · `tests 8` · `delivery 11`。

---

## 2. 合并映射（reviewer finding → 统一编号）

> 把每位 reviewer 的原始编号映射到统一 `UF#`。一条统一项可由多方贡献。源 id 格式：`gemini-R#` / `gpt-R#` / `grok-R#` / `muse-R#`。每条原始 R# 恰好出现一次。

### 2.1 映射表

| 来源 finding（reviewer-原编号）| 合并到 | 合并后问题（一句话）|
|------------------------------|--------|---------------------|
| gemini-R2 / gpt-R1 | `UF1` | UoW cancel/`commit()` 异常不 rollback，唯一长连接永久停在未结事务 |
| gemini-R17 / gemini-R18 / gpt-R4 / grok-R7 / muse-R1 | `UF2` | Turso 单连接 + `BEGIN IMMEDIATE` + 无 busy_timeout，CW/native-vector 探针切 journal_mode 后与写路径脱节 |
| gpt-R2 | `UF3` | Turso diagnostic sidecar 并发写触发 pyturso native abort（exit 134） |
| grok-R28 | `UF4` | 全部 CAS 直接读未归一化的 pyturso `cursor.rowcount` |
| muse-R20 | `UF5` | migration ledger 用 `!r` 插值拼进 `executescript`，非参数化 |
| muse-R21 | `UF6` | pyturso 无 `executescript` 时回退 `connection.execute` 多语句脚本，首条 CREATE 即失败 |
| gemini-R41 | `UF7` | 迁移 010 用 `lower(hex(randomblob(16)))` 生成无连字符 32 位 ID，破坏 UUID 校验 |
| gemini-R42 | `UF8` | Python 微秒时间戳与 SQLite 毫秒精度不一致，SQL 时间比较偏差 |
| gemini-R1 / gpt-R7 / grok-R11 / muse-R3 | `UF9` | Claude CLI `wait_for` 超时/取消不 `kill()`/`wait()`，子进程与 FD 泄漏（gpt 兼称输出无上限） |
| gpt-R5 / grok-R16 / muse-R2 | `UF10` | Worker 声称 30s lease 且 handler 期间从不 heartbeat，推理可达 180/900s，必被 reclaim 重复执行 |
| gpt-R8 / grok-R9 | `UF11` | salvage/dispatch_pool 不是真实运输 SSOT：同 Process 内切 Claude，绕开 frozen binding / NI admit / quota |
| gemini-R12 | `UF12` | `_can_salvage_local_inference` 优先级逆变，`urgent`/`high` 无法降级熔断到本地推理 |
| gemini-R11 | `UF13` | `OVER_BUDGET_PROCESS_KEYS` 遗漏 `transcribe` 与 `construct`，生成任务无法溢出分流 |
| gemini-R13 | `UF14` | `_ns1_prompt_file` 在 `state=None` 时直接读本地 prompt 文件，绕过 Snapshot 校验 |
| gemini-R10 | `UF15` | `LocalVllmAdapter` 每次请求局部新建 `httpx.AsyncClient`，连接池无法复用 |
| gpt-R9 | `UF16` | CLI 把知识正文放 argv 并继承完整父进程环境，泄露 secret |
| gpt-R10 | `UF17` | salvage 失败证据放在 supervisor ContextVar，可 flush 到另一 Process/Team；失败 inference ledger 缺失 |
| gpt-R11 | `UF18` | frozen snapshot 省略 schema bytes；live readiness 可在 supply 探针关闭或只查 registry 时仍为 ready |
| grok-R4 | `UF19` | Facade 把最后一次 `INFERENCE_TRANSPORT_RETRYABLE` 改写成 `EXHAUSTED`，generate 变终态失败 |
| muse-R6 | `UF20` | SupplyFence 由全部 `default_enabled` bindings 构建，而非 active winners |
| muse-R7 | `UF21` | `generation_construct` 直接调 Claude CLI，绕过 `InferenceFacade.ConcurrencyGate`，可无界 fork |
| gemini-R44 / gpt-R19 / muse-R24 | `UF22` | Facade 在同一 concurrency lease 内重试/sleep，无 jitter/idempotency，退避期间占满 gate |
| grok-R20 | `UF23` | `DefaultBillingService.has_quota` 恒真，salvage/NI 配额门是空操作 |
| muse-R25 | `UF24` | local_vllm 仅把 429/503/>=500 当 TRANSPORT_RETRYABLE，408/425 被判 validation 不重试 |
| muse-R26 | `UF25` | 裸 `Exception` 变成 `INFERENCE_INTERNAL_UNEXPECTED` 直接 fail-closed，httpx 超时跳过传输重试矩阵 |
| gpt-R18 | `UF26` | PDF/doc LLM 路径丢弃 media type，UTF-8 `errors=replace` 把 blob 当文本 |
| gemini-R6 / gpt-R28 / grok-R2 | `UF27` | live vectorize 把超 16k 的非 g0-summary required units 滤掉后仍按缩水集合签 full-valid publication proof |
| gemini-R5 | `UF28` | HTML 提取末尾 `\s+` 全局替换为空格，抹平此前插入的全部段落与表格换行 |
| gemini-R7 / gpt-R30 | `UF29` | Structurizer `clean.find(normalized_body)` 永远从索引 0 搜索，重复文本后续 block 全部错锚到首次出现 |
| gemini-R23 | `UF30` | 本地 PDF 文本提取在 raw bytes 上正则扫描，压缩 PDF 失败且 UTF-16 乱码 |
| gemini-R24 | `UF31` | ChinaTax/REA Provider 缺 ID 时写成 `"None"` 引发主键冲突，且 HTML 解析压平排版 |
| gemini-R25 | `UF32` | Structurizer 粒度闭集在短文本上硬性报 `GRANULARITY_SET_MISMATCH` |
| gemini-R26 | `UF33` | C 阶段对 Original 内容强行逐字校验，标点或转义微调即可使全包生成失败 |
| gpt-R15 | `UF34` | local/registered/browser acquisition 无界读字节且仍盖 `within_configured_acquisition_budget` 假证明 |
| gpt-R29 | `UF35` | 重复 ingest 总是插入新 Source/Snapshot/Item/Revision UUID，从不按 external/connector/member key resolve |
| gpt-R31 | `UF36` | raw 与 clean Artifact 共享同一 envelope handle/size 却写不同 semantic digest |
| grok-R12 | `UF37` | 默认 `ns1_cli_mode=stub` 把 summary 原样写成 original 并发布；e2e 不断言 `summary != original` |
| gemini-R43 / grok-R21 | `UF38` | `coerce_json_object_text` 从首 `{` 切到末 `}`；vLLM 不传 json schema；空 g0 可被填成 clean |
| grok-R23 / gpt-R40 | `UF39` | live markdown receipt 为 `api_inference`，artifact 元数据却写死 `transport=claude_cli`；stub 不消费 Markdown |
| grok-R17 | `UF40` | accept 插入 `lifecycle_state=active` 之后才 human_review，reject 无法 deactivate 已 admitted item |
| grok-R25 | `UF41` | adopt 的 structure 树是 root+单 paragraph 覆盖全文；空 g0 被填成 clean |
| muse-R16 | `UF42` | vectorize 把任意 `MkbError` 包成 `VECTORIZE_INFERENCE_FAILED`，SPACE_VIOLATION 被当成可恢复重试 |
| muse-R17 | `UF43` | 离线嵌入用 header+body 的 `content_full`，query 侧只 embed `query.strip()`，cosine 系统性偏低 |
| grok-R5 | `UF44` | 指针 UPDATE 只 CAS `pointer_row_revision`，generation 在另一笔只读事务预留，晚到 ingest 可回拨已 cutover 指针 |
| gpt-R37 | `UF45` | 每阶段把完整累计 state 写入 CAS envelope，raw/decoded/clean/markdown/layered 正文成倍放大 |
| gpt-R38 | `UF46` | Python layered validator 主要查字段名/类型，可接受注册 JSON Schema 会拒绝的值 |
| gpt-R26 / grok-R13 / muse-R4 / grok-R26 | `UF47` | 检索候选 `ORDER BY vector_record_uuid LIMIT 1000` 再 Python 打分；`native_ann` 配置是死开关，从未接入 RetrievalService |
| gemini-R8 / gpt-R34 | `UF48` | `_deduplicate` 把 summary 优先级固定高于 original，低分 summary 可置换高分 original |
| gemini-R9 | `UF49` | `_inflate_documents` 继承外部 `query.filters`，`channel=original` 时拓扑寻根必崩 |
| gpt-R32 / grok-R18 | `UF50` | Team deactivate/delete 只改 `mkb_teams.status`；retrieval 不 `require_active`、候选 SQL 不检查 team status |
| gpt-R27 / grok-R8 | `UF51` | `LIVE_INFERENCE=false` 时检索按 namespace dimension 做 deterministic hash，不核对 adapter/model，混入 live 向量空间 |
| muse-R5 | `UF52` | 同 `namespace_key='default'` 上 64↔1024 切换抛 `VECTOR_NAMESPACE_BINDING_CONFLICT`，新活嵌入永不 serving |
| gpt-R33 / muse-R35 | `UF53` | retrieval 对每个 hit 串行两次 `read_verified` 无 batch；10k scatter/team rebuild 无界巨事务 |
| gemini-R4 | `UF54` | `purge_generation` 允许单通道软删除，剩余向量数 < `proof.actual_count`，双重 Fence 阻断该世代全部检索 |
| grok-R6 | `UF55` | `ux_vec_coord_active` 不含 `index_generation`，第二次 vectorize UPDATE 会把正在 serving 的行改成 withdrawn |
| gemini-R36 | `UF56` | Context Packing 对同代多个 Hit 重复填充相同 Document Root，挤爆上下文窗口 |
| muse-R18 | `UF57` | `_sql_batch_eligibility` 只查 item.lifecycle + serving==rev，不镜像完整 S09+S04 谓词 |
| gpt-R35 | `UF58` | 普通 publish 从 namespace `index_generation+1` 分配 item generation，rebuild 却用 pointer `active+1`，代数跳跃/碰撞 |
| gpt-R42 | `UF59` | `vector.upserted` 读不存在的 `generation_artifact_uuid` / `construction_dual_channel_artifact_uuid` |
| gemini-R37 / grok-R15 | `UF60` | Reactivate 后或团队级 resolve 不含 `serving_revision_uuid` 的 item，index.rebuild 准入通过但执行整单失败 |
| grok-R1 | `UF61` | 非法 outbox JSON 在同一 claim 事务里 `attempts+1` 后解析失败整笔回滚，毒丸行永不 dead，`drain_once` 卡住唯一 supervisor |
| gpt-R6 | `UF62` | 唯一 supervisor 串行 `await worker.run_once()`，声称的 2/2/8 pool running cap 不是实际并发 |
| gemini-R3 | `UF63` | IndexGenerationRetirement 遇 deactivated/deleted Item 时 intent 保持 `open`，队头阻塞使全库旧世代向量 GC 停滞 |
| gemini-R15 / muse-R8 | `UF64` | Object GC 在持写锁的 `transaction()` 内物理 unlink：阻塞 claim/create，且事务回滚时对象已不可恢复 |
| gemini-R14 | `UF65` | `LocalObjectStore.delete_if_unreferenced` 未纳入 `_write_lock`，与 `promote()` 并发竞态 |
| gemini-R16 / gpt-R12 | `UF66` | 生产路径从不 release object references；GC 看不见 promote 回滚留下的 filesystem-only orphan，也无磁盘反向扫描 |
| gpt-R13 | `UF67` | GC tombstone 后同一 digest 可在仍 tombstoned 的 `stored_object_uuid` 上再挂新 live reference |
| gemini-R21 / gpt-R14 | `UF68` | `OutcomeArtifactCommitter._pending` 成功/失败/取消后从不 `pop`，进程级泄漏直至 OOM |
| gpt-R36 / muse-R9 | `UF69` | GC/retirement `run_forever` 不捕获 `run_once` 异常，一次 SQLITE_BUSY 即永久停摆且 lifespan 不重启 |
| muse-R10 | `UF70` | `claim_next` 每轮只 fail 一个 deadline 过期行（LIMIT 1 无 ORDER BY）后 `return None`，好任务饿死 |
| gemini-R38 | `UF71` | Process 重试固定 1s 且无 jitter，易引发惊群雪崩 |
| gemini-R39 | `UF72` | 已取消进程仍消费 Gate Decision，Outbox 恶性重试 8 次后进死信 |
| gemini-R40 | `UF73` | Outbox 进入 dead 时不写领域事件也不告警，任务静默死亡 |
| muse-R11 | `UF74` | `claim_token_hash` 写入后 `mark_running`/`accept_outcome` 只查 `fencing_generation`，worker 丢弃 token |
| gemini-R19 / muse-R13 | `UF75` | `request_ip` 只看 `request.client.host`，反向代理后全员像内网，`/internal` 与 `/metrics` 暴露 |
| gemini-R20 / muse-R23 / grok-R27 | `UF76` | FixedWindowRateLimiter 桶超限/异常后 `degraded=True allowed=True` 永久黏住并全局 fail-open；IP 检查在鉴权前 |
| gemini-R22 | `UF77` | HTML Sanitizer 未限制 `href`/`src` 协议，可写入 `javascript:` 造成存储型 XSS |
| gpt-R16 / muse-R14 | `UF78` | 公共 Team/Task extras 可持久化 secret/signed URL；`_SECRET_KEYS` 精确集漏驼峰 `apiKey`/`secretKey`，PATCH 还跳过检查 |
| grok-R22 / muse-R15 | `UF79` | FastAPI 默认 `/docs` `/redoc` `/openapi.json` 无鉴权（grok 兼称 bootstrap `MkbError` 被 `pass`） |
| muse-R19 | `UF80` | `sqlite_backend_permitted()` 仅看 `PYTEST_CURRENT_TEST`，生产 `export PYTEST_CURRENT_TEST=1` 即可绕过 Turso 宪法 |
| gpt-R24 | `UF81` | 钉死 `starlette==0.46.2` 落入 GHSA-86qp-5c8j-p5mr / CVE-2026-48710 Host/`request.url` 范围 |
| grok-R19 | `UF82` | `_restricted` 对 `::ffff:127.0.0.1` 与 mapped RFC1918 的 `is_loopback`/`is_private` 为 False |
| gpt-R43 | `UF83` | denial audit 先 `sampler.decide()` 再写 DB；写失败仍消耗 quota，随后 invalid token 变成无审计 401 |
| muse-R36 | `UF84` | 无 `ContentLengthLimitMiddleware`，10k records + extras 在 422 之前即可把 body 全部缓冲 OOM |
| gemini-R27 / gemini-R28 / gemini-R29 / gemini-R30 / gemini-R31 / gemini-R34 / gpt-R20 / gpt-R21 / grok-R3 / muse-R30 / muse-R31 | `UF85` | 一批测试删掉 SUT 也会绿：`assert ... or True`、自造字典、未实例化 sidecar、串行 soak、缺文件直接 `return`、无 assert、手工 orphan/GC、fail-path 私有 helper |
| gemini-R32 / gpt-R22 / grok-R10 | `UF86` | E2E 在 Turso backend 上用原生 `sqlite3.connect` 打开同一文件（disk I/O / not a database）；固定 5s 轮询假红；local runtime 普遍 waiver 宪法探针 |
| gpt-R23 / gemini-R45 | `UF87` | 当前全量 pytest 非全绿（431–433 passed / 8–10 failed）且 `ruff check` 仍有 9 个 F401/I001/B904/B017/F811/F841 |
| gemini-R33 | `UF88` | E2E 黄金摄取流水线被 `_LiveEmbeddingFixture` 全量 Mock，短路核心模型通信 |
| gemini-R35 | `UF89` | 大量单元测试靠读源码正则扫描伪装行为测试，未走真实调用 |
| muse-R28 | `UF90` | `pyproject.toml` pytest addopts 仅 `-q --tb=short`：无 strict-markers/config、warning-as-error、coverage fail_under、共享 conftest |
| muse-R29 | `UF91` | `local_mock_settings` 关闭 concurrent_writes/native_vector/live_inference，e2e 走 SqlitePersistence + deterministic-hash，三大探针被豁免 |
| muse-R32 | `UF92` | 检索双栅栏测试用空集恒真比较；e2e 只查 succeeded，无 deactivate/delete 后 search==empty 覆盖 |
| gpt-R3 | `UF93` | 构建的 wheel 省略 migration SQL 与 prompt/config/schema assets，安装后的 mkb 无法 migrate/启动 |
| gpt-R25 / muse-R22 | `UF94` | `/ready` 与 `claim_next` 每次跑完整 HealthAggregator（含 journal_mode 切换）并持写锁；idle worker 约每 50ms 一次 |
| gpt-R39 | `UF95` | wire schema 允许 `original_content`/`llm_summary` title，adoption/construct 只留 body，title 永不进入 vector/retrieval |
| muse-R27 | `UF96` | `InferenceFacade.capability_limits` 与 `DispatchCaps` 独立；retrieval.search embed 还绕过编排器，双层背压分叉 |
| gpt-R41 / grok-R14 / muse-R33 | `UF97` | browser/OCR/Vision/doc-LLM/web-LLM 工作流注册为 active，但组合根 `clean_llm=None`/`browser_fetcher=None`，公共 DTO 不可达或 admit 后稳定 503 |
| muse-R34 | `UF98` | registry/workflows bootstrap 与 retention 吞掉 `MkbError`/`Exception` 且无 log/metric |
| grok-R24 | `UF99` | Task 幂等指纹是整份 request JSON 的 `stable_digest`，含 `audit.created_at`，刷新时间戳的合法重试变 identity-conflict |
| gpt-R45 | `UF100` | `str(exc)` 未经统一脱敏写入 Process `error_message` 与 outbox `last_error` |
| gpt-R17 | `UF101` | object readiness 接受非 JSON identity；schema readiness 在 `DROP TABLE` 后仍 true（只比 ledger id/checksum） |
| gpt-R44 | `UF102` | 空 Team `payload_extra={}` 被当成无 mutation，truthiness 保留旧 metadata；与 Task patch 的 `model_fields_set` 不一致 |
| muse-R12 | `UF103` | Task/Team SELECT-then-INSERT 唯一冲突未捕获 `IntegrityError`，并发 PK 走 500 而非 409 identity-conflict |

### 2.2 宽对照表

| 统一编号 | 合并后的问题 | gemini | gpt | grok | muse |
|----------|--------------|--------|-----|------|------|
| `UF1` | UoW cancel/commit 不 rollback | `R2` | `R1` | — | — |
| `UF2` | Turso 单写者 + CW 探针剧场 | `R17`/`R18` | `R4` | `R7` | `R1` |
| `UF3` | sidecar native abort | — | `R2` | — | — |
| `UF4` | pyturso rowcount 未归一化 | — | — | `R28` | — |
| `UF5` | migration ledger `!r` 插值 | — | — | — | `R20` |
| `UF6` | executescript 回退多语句失败 | — | — | — | `R21` |
| `UF7` | 迁移 010 32 位 hex ID | `R41` | — | — | — |
| `UF8` | 时间戳 us vs ms | `R42` | — | — | — |
| `UF9` | Claude CLI 超时不杀子进程 | `R1` | `R7` | `R11` | `R3` |
| `UF10` | 30s lease 无 heartbeat | — | `R5` | `R16` | `R2` |
| `UF11` | salvage/dispatch_pool 非运输 SSOT | — | `R8` | `R9` | — |
| `UF12` | salvage 优先级逆变 | `R12` | — | — | — |
| `UF13` | OVER_BUDGET 键遗漏 | `R11` | — | — | — |
| `UF14` | prompt file 绕过 Snapshot | `R13` | — | — | — |
| `UF15` | vLLM 每请求新建 AsyncClient | `R10` | — | — | — |
| `UF16` | CLI argv/env 泄密 | — | `R9` | — | — |
| `UF17` | salvage 证据 ContextVar 串台 | — | `R10` | — | — |
| `UF18` | schema 未冻结 / readiness 假 ready | — | `R11` | — | — |
| `UF19` | EXHAUSTED 改写终态失败 | — | — | `R4` | — |
| `UF20` | SupplyFence 过宽 | — | — | — | `R6` |
| `UF21` | CLI 无并发门限 | — | — | — | `R7` |
| `UF22` | Facade 重试占满 gate | `R44` | `R19` | — | `R24` |
| `UF23` | Billing 恒真 | — | — | `R20` | — |
| `UF24` | 408/425 不重试 | — | — | — | `R25` |
| `UF25` | INTERNAL_UNEXPECTED 不按矩阵重试 | — | — | — | `R26` |
| `UF26` | PDF/doc LLM 二进制替换解码 | — | `R18` | — | — |
| `UF27` | vectorize 静默丢层仍签完整 proof | `R6` | `R28` | `R2` | — |
| `UF28` | HTML `\s+` 抹平换行 | `R5` | — | — | — |
| `UF29` | find(body) 永远首次出现 | `R7` | `R30` | — | — |
| `UF30` | PDF raw-bytes 正则提取 | `R23` | — | — | — |
| `UF31` | ChinaTax/REA `"None"` 主键 | `R24` | — | — | — |
| `UF32` | 短文本 GRANULARITY_SET_MISMATCH | `R25` | — | — | — |
| `UF33` | Construct Original 逐字过敏 | `R26` | — | — | — |
| `UF34` | acquisition 绕过预算 | — | `R15` | — | — |
| `UF35` | 重复 ingest 总建新 Item | — | `R29` | — | — |
| `UF36` | Artifact handle/digest/size 不一致 | — | `R31` | — | — |
| `UF37` | stub 把 summary 写成 original | — | — | `R12` | — |
| `UF38` | JSON 贪婪切片 / schema 未交给 vLLM | `R43` | — | `R21` | — |
| `UF39` | markdown transport 写死 claude_cli | — | `R40` | `R23` | — |
| `UF40` | 人工 gate 在 item 已 active 之后 | — | — | `R17` | — |
| `UF41` | adopt 两节点树 / 空 g0 填充 | — | — | `R25` | — |
| `UF42` | VECTORIZE 包错误重试 | — | — | — | `R16` |
| `UF43` | content_full header vs query 裸嵌入 | — | — | — | `R17` |
| `UF44` | 指针 CAS 不单调 | — | — | `R5` | — |
| `UF45` | 每阶段复制完整 state | — | `R37` | — | — |
| `UF46` | Python validator ≠ JSON Schema | — | `R38` | — | — |
| `UF47` | UUID LIMIT 1000 / ANN 未接线 | — | `R26` | `R13`/`R26` | `R4` |
| `UF48` | dedup summary-first | `R8` | `R34` | — | — |
| `UF49` | inflate 继承 channel filter | `R9` | — | — | — |
| `UF50` | Team inactive 仍可检索 | — | `R32` | `R18` | — |
| `UF51` | offline hash 混入 live 空间 | — | `R27` | `R8` | — |
| `UF52` | 64↔1024 维度 schism | — | — | — | `R5` |
| `UF53` | hydration N+1 / 巨事务 | — | `R33` | — | `R35` |
| `UF54` | 单通道 purge 破坏 Proof | `R4` | — | — | — |
| `UF55` | 向量唯一键不含 generation | — | — | `R6` | — |
| `UF56` | packing 重复填充 Root | `R36` | — | — | — |
| `UF57` | 第二重 eligibility 栅栏不完整 | — | — | — | `R18` |
| `UF58` | publish 用 namespace 计数分配 generation | — | `R35` | — | — |
| `UF59` | vector.upserted 丢 artifact UUID | — | `R42` | — | — |
| `UF60` | rebuild 被未 serving item 毒死 | `R37` | — | `R15` | — |
| `UF61` | outbox 毒丸卡住 supervisor | — | — | `R1` | — |
| `UF62` | supervisor 串行假并发 | — | `R6` | — | — |
| `UF63` | retirement 失效 intent 死循环 | `R3` | — | — | — |
| `UF64` | GC 事务内 unlink | `R15` | — | — | `R8` |
| `UF65` | delete_if_unreferenced 无锁 | `R14` | — | — | — |
| `UF66` | object release / orphan GC 未实现 | `R16` | `R12` | — | — |
| `UF67` | tombstone digest 复用 live ref | — | `R13` | — | — |
| `UF68` | `_pending` 永不清理 | `R21` | `R14` | — | — |
| `UF69` | scanner 一次异常永久退出 | — | `R36` | — | `R9` |
| `UF70` | claim_next 只 fail 一个过期项 | — | — | — | `R10` |
| `UF71` | Process 重试固定 1s 无 jitter | `R38` | — | — | — |
| `UF72` | 取消后仍消费 Gate Decision | `R39` | — | — | — |
| `UF73` | outbox dead 无事件/告警 | `R40` | — | — | — |
| `UF74` | fencing token 从未校验 | — | — | — | `R11` |
| `UF75` | 代理后 request_ip 内网绕过 | `R19` | — | — | `R13` |
| `UF76` | 限流桶超限 / degraded fail-open | `R20` | — | `R27` | `R23` |
| `UF77` | HTML href/src 任意协议 XSS | `R22` | — | — | — |
| `UF78` | payload_extra 可存 secret / 漏驼峰 | — | `R16` | — | `R14` |
| `UF79` | /docs 无鉴权 | — | — | `R22` | `R15` |
| `UF80` | PYTEST_CURRENT_TEST sqlite 后门 | — | — | — | `R19` |
| `UF81` | Starlette 0.46.2 CVE | — | `R24` | — | — |
| `UF82` | IPv6-mapped 未当 loopback/私网 | — | — | `R19` | — |
| `UF83` | audit 写失败消耗 sampler | — | `R43` | — | — |
| `UF84` | 无全局 body size 限 | — | — | — | `R36` |
| `UF85` | 测试删 SUT 也会绿 | `R27`/`R28`/`R29`/`R30`/`R31`/`R34` | `R20`/`R21` | `R3` | `R30`/`R31` |
| `UF86` | e2e sqlite3 打开 Turso 文件 | `R32` | `R22` | `R10` | — |
| `UF87` | 全量 pytest / ruff 不绿 | `R45` | `R23` | — | — |
| `UF88` | LiveEmbeddingFixture 全量 Mock | `R33` | — | — | — |
| `UF89` | 源码正则扫描伪装行为测试 | `R35` | — | — | — |
| `UF90` | pytest 配置宽松无 coverage/conftest | — | — | — | `R28` |
| `UF91` | local_mock 豁免三大探针 | — | — | — | `R29` |
| `UF92` | 检索栅栏无 deactivate e2e | — | — | — | `R32` |
| `UF93` | wheel 缺 migration SQL | — | `R3` | — | — |
| `UF94` | /ready 持写锁 + 50ms 全量探活 | — | `R25` | — | `R22` |
| `UF95` | schema title 静默丢失 | — | `R39` | — | — |
| `UF96` | Facade gate 与 DispatchCaps 分叉 | — | — | — | `R27` |
| `UF97` | LLM-clean/browser/OCR 未注入 | — | `R41` | `R14` | `R33` |
| `UF98` | bootstrap/retention 静默 pass | — | — | — | `R34` |
| `UF99` | Task 指纹含 created_at | — | — | `R24` | — |
| `UF100` | raw exception 未脱敏落盘 | — | `R45` | — | — |
| `UF101` | object/schema readiness 假 ready | — | `R17` | — | — |
| `UF102` | Team payload_extra 无法清空 | — | `R44` | — | — |
| `UF103` | Task/Team PK 冲突走 500 | — | — | — | `R12` |

### 2.3 unified-findings 平铺台账

> 本节是 Phase-1 问题汇聚台账。`最严严重级` = 来源中最严者。`verdict` / `class` / `disposition` 一律 `pending-phase-2`，不在本表展开。

| UF# | 标题 | 最严严重级 | 来源 | verify_shard | 合并后问题（一句话）| reviewer 声称的 file:line |
|-----|------|------------|------|--------------|---------------------|---------------------------|
| UF1 | UoW cancel/commit 未 rollback 污染唯一连接 | `critical` | gemini/gpt | persist | `transaction()` 只捕 `Exception`，`commit()` 在 `else`；CancelledError/commit 失败不 rollback，单例连接永久 `in_transaction` | `src/persistence/sqlite_port.py:83-95`；`src/persistence/turso/port.py:87-99` |
| UF2 | Turso 单连接 + BEGIN IMMEDIATE + CW 探针剧场 | `critical` | gemini/gpt/grok/muse | persist | 生产 UoW 单连接写锁 + IMMEDIATE、无 busy_timeout；readiness 在业务连接上切 MVCC/`BEGIN CONCURRENT` 再还原，FK PRAGMA 可被吞 | `src/persistence/turso/port.py:63-99`；`src/persistence/engine.py:13-40`；`src/persistence/sqlite_port.py:69-71`；`src/persistence/turso/sidecar.py:23-37` |
| UF3 | sidecar 并发触发 native abort | `critical` | gpt | persist | 每条诊断新建连接、切 MVCC、`BEGIN CONCURRENT`，4 线程复现 pyturso panic exit 134 | `src/persistence/turso/sidecar.py:23-57`；`src/services/observability.py:158-171`；`api/app.py:309-314` |
| UF4 | CAS 依赖未归一化 pyturso rowcount | `high` | grok | persist | claim/heartbeat/pointer/vector fence 用 `cursor.rowcount != 1`；Turso port 不包装 `changes()`；CAS 单测只跑 SqlitePersistence | `src/runtime/workflow/runtime_core.py:462-477`；`src/persistence/turso/port.py` |
| UF5 | migration ledger `!r` 插值 | `high` | muse | persist | ledger SQL 把 `migration_id/checksum/utc_now` 用 `!r` 拼进 `executescript` | `src/persistence/migration_runner.py:132-138` |
| UF6 | Turso executescript 回退多语句失败 | `high` | muse | persist | 无 `executescript` 时 `connection.execute` 整段 DDL，首个 CREATE 即 syntax error，生产首次 migrate 永不 ready | `src/persistence/migration_runner.py:65-72` |
| UF7 | 迁移 010 生成 32 位非 UUID | `medium` | gemini | persist | `lower(hex(randomblob(16)))` 无 8-4-4-4-12 连字符，破坏 UUID 校验 | （gemini 汇总表未给精确行号；标题指向迁移 010） |
| UF8 | 时间戳微秒 vs 毫秒 | `medium` | gemini | persist | Python 微秒时间戳与 SQLite 毫秒精度不一致，SQL 比较偏差 | （gemini 汇总表未给精确行号） |
| UF9 | Claude CLI 超时不杀子进程 | `critical` | gemini/gpt/grok/muse | infer | `asyncio.wait_for(communicate)` 超时/取消只取消等待，不 terminate/kill/wait；gpt 兼称 stdout 无上限 | `src/runtime/inference/claude_cli.py:288-304`；`src/contracts/inference/models.py:156-165` |
| UF10 | 30s lease 无 heartbeat | `critical` | gpt/grok/muse | infer | `WorkflowWorker` claim 30s 后 `await handler.run` 从不 heartbeat；vLLM 180s × retries、CLI 900s，repair 会 fence 并重复执行 | `src/runtime/workflow/worker.py:45-53`；`src/runtime/workflow/runtime_core.py:546-558`；`src/runtime/config.py:46`；`src/runtime/inference/claude_cli.py:31,148` |
| UF11 | salvage/dispatch_pool 不是运输 SSOT | `high` | gpt/grok | infer | 同 local Process 内切 Claude，不重新 choose_pool/NI occupancy；snapshot/handler/salvage/billing 可讲四个故事 | `src/runtime/intake/generation_construct.py:81-180,270-284`；`src/runtime/workflow/runtime_core.py:304-315`；`src/services/config_snapshots.py:184-202,573-581`；`src/services/billing.py:16-21` |
| UF12 | salvage 优先级逆变 | `high` | gemini | infer | `_can_salvage_local_inference` 把 urgent/high 排除在可 salvage 之外，无法降级熔断 | （gemini 汇总表未给精确行号；标题指向 `_can_salvage_local_inference`） |
| UF13 | OVER_BUDGET 键遗漏 transcribe/construct | `high` | gemini | infer | over-budget 集合不含这两类生成任务，无法溢出分流，有 OOM 风险 | （gemini 汇总表未给精确行号；标题指向 `OVER_BUDGET_PROCESS_KEYS`） |
| UF14 | prompt file 在 state=None 时绕过 Snapshot | `high` | gemini | infer | `_ns1_prompt_file` 缺 state 时直接读本地文件 | （gemini 汇总表未给精确行号；标题指向 `_ns1_prompt_file`） |
| UF15 | LocalVllmAdapter 每请求新建 AsyncClient | `high` | gemini | infer | 局部 `httpx.AsyncClient` 使连接池无法复用 | （gemini 汇总表未给精确行号；标题指向 `LocalVllmAdapter`） |
| UF16 | CLI 泄露正文与父进程环境 | `high` | gpt | infer | <16KiB 业务正文进 argv；`SubprocessClaudeCli(env=None)` 继承全部父环境；Settings token 可 repr/dump | `src/runtime/inference/claude_cli.py:59-62,149-152,281-298`；`api/app.py:304-308` |
| UF17 | salvage 失败证据可串台 | `high` | gpt | infer | evidence 放 ContextVar，失败 flush 用“当前”Process 身份；失败 inference ledger 不写 | `src/runtime/intake/generation_live.py:257-281,329-338`；`src/runtime/intake/generation_evidence.py:10-33,45-98`；`src/runtime/workflow/runtime_outcome.py:460-463` |
| UF18 | schema 未冻结 / live readiness 假 ready | `high` | gpt | infer | snapshot 无 schema bytes；vLLM 只发 `json_object`；`inference_probe_enabled` 默认 false，3xx 可算健康 | `src/services/config_snapshots.py:191-220`；`src/runtime/intake/generation_live.py:133-168`；`src/llm_adapters/local_vllm.py:161-166`；`api/app.py:180-189` |
| UF19 | 运输耗尽变成终态失败 | `high` | grok | infer | 最后一次 RETRYABLE 改写 EXHAUSTED，该码不在 process-retryable；generate 三次后终态失败 | `src/runtime/inference/facade.py:332-342`；`src/runtime/intake/core.py:176-186`；`src/runtime/intake/generation_live.py:257-269` |
| UF20 | SupplyFence 允许集过大 | `high` | muse | infer | fence 由全部 enabled bindings（5）而非 `active_inference_bindings()` winners（3）构建 | `api/app.py:231-240`；`src/services/registry.py:126-136`；`src/runtime/inference/facade.py:375` |
| UF21 | Claude CLI 无并发门限 | `high` | muse | infer | construct 直接 `claude_cli.run`，不经 Facade ConcurrencyGate | `src/runtime/inference/claude_cli.py:281`；`src/runtime/intake/generation_construct.py:164` |
| UF22 | Facade 重试占满 gate 且无 jitter | `medium` | gemini/gpt/muse | infer | 同一 lease 内最多 3 次重试，sleep 不释放 slot；无 jitter/Retry-After/idempotency key；中间尝试不记 InvocationRecord | `src/runtime/inference/facade.py:262-349,486-487`；`src/llm_adapters/local_vllm.py:152-167` |
| UF23 | Billing 恒真 | `medium` | grok | infer | `has_quota` 永远 true；组合根注入两份独立实例；salvage/NI 把它当真门 | `src/services/billing.py:16-21`；`api/app.py:293,325` |
| UF24 | 408/425 被判 validation | `medium` | muse | infer | local_vllm 只映射 429/503/>=500 为 TRANSPORT_RETRYABLE | `src/llm_adapters/local_vllm.py:212` |
| UF25 | INTERNAL_UNEXPECTED 不重试 | `medium` | muse | infer | `except Exception` → 503 INTERNAL 后 record_failure+raise，httpx 超时可能跳过传输重试 | `src/runtime/inference/facade.py:343` |
| UF26 | PDF/doc LLM 二进制替换解码 | `high` | gpt | infer | 丢弃 media type，blob UTF-8 `errors=replace` 成文本后仍可能返回成功 clean | `src/runtime/inference/claude_cli.py:371-386` |
| UF27 | live vectorize 静默丢层仍签完整 proof | `critical` | gemini/gpt/grok | intake | 超 16k 的 g1/g2 等从 embeddable 过滤，`required_units==succeeded_units` 按缩水集合签名；读路径不查 required_set_digest | `src/runtime/intake/vectorize.py:183-205,238-250`；`src/runtime/intake/vector_publish_commit.py:111-114`；`src/services/lsrag_compiler/construct.py:108-131` |
| UF28 | HTML 提取器抹平全部换行 | `critical` | gemini | intake | `_SPACE.sub(" ", ...)` 把已插入的 `\n` 全部压成单空格 | `intake/text.py:102-113` |
| UF29 | 重复文本 anchor 永远第一次出现 | `critical` | gemini/gpt | intake | `clean.find(normalized_body)` 从 0 搜索；occurrence count 被记录但不消歧 | `src/services/lsrag_compiler/adopt.py:224-255` |
| UF30 | PDF raw bytes 正则扫描 | `high` | gemini | intake | 本地 PDF 提取对压缩流/UTF-16 在 raw bytes 上正则，失败或乱码 | （gemini 汇总表未给精确行号；标题指向本地 PDF 提取器） |
| UF31 | ChinaTax/REA 外部键与 HTML 解析缺陷 | `high` | gemini | intake | 缺 ID 写成 `"None"` 主键冲突；HTML 解析压平排版 | （gemini 汇总表未给精确行号；标题指向 ChinaTax/REA Provider） |
| UF32 | 短文本粒度闭集硬报错 | `high` | gemini | intake | 凑不齐 g1/g2 闭集时硬性 `GRANULARITY_SET_MISMATCH` | （gemini 汇总表未给精确行号） |
| UF33 | Construct 对 Original 逐字过敏 | `high` | gemini | intake | 标点/转义微调即可使全包生成失败 | （gemini 汇总表未给精确行号） |
| UF34 | acquisition 绕过预算并写假 proof | `high` | gpt | intake | `Path.read_bytes()` / 无界 records/browser bytes；统一盖 `within_configured_acquisition_budget` | `src/runtime/intake/acquisition_ingest.py:358-369,456-499`；`src/storage/local_store.py:103-118` |
| UF35 | 重复 ingest 总是新建 Source/Item | `high` | gpt | intake | acquire/accept 无条件新 UUID；external/connector/member key 不用于 resolve | `src/runtime/intake/acquisition_ingest.py:91-97,207-211,266-270`；`src/runtime/intake/acceptance_snapshot.py:98-128`；`src/services/scatter_intake.py:389-428` |
| UF36 | Artifact handle/digest/size 不是同一 bytes | `high` | gpt | intake | raw/clean 共用 envelope handle/size，却写不同 semantic digest | `src/runtime/intake/acceptance_snapshot.py:63-70,132-178`；`src/runtime/intake/core.py:462-474` |
| UF37 | 默认 stub 把 summary 写成 original | `high` | grok | intake | `ns1_cli_mode` 默认 stub，C 在预算内原样复制 original；validate 只要求 summary 非空 | `src/runtime/config.py:44`；`src/runtime/inference/claude_cli.py:110-115,401-421`；`src/services/lsrag_compiler/validate.py:129-131`；`tests/e2e/test_generation_pipeline_contracts.py:160-173` |
| UF38 | JSON 贪婪切片 / schema 未交给 vLLM | `medium` | gemini/grok | intake | `find('{')`+`rfind('}')`；vLLM 仅 `json_object`；空 g0 填 clean | `src/runtime/inference/facade.py:49-66`；`src/llm_adapters/local_vllm.py:161-162`；`src/services/lsrag_compiler/adopt.py:66-67` |
| UF39 | markdown transport 写死 claude_cli | `medium` | grok/gpt | intake | receipt `api_inference` vs artifact `"transport":"claude_cli"`；stub 只读 clean_text | `src/runtime/intake/generation_construct.py:544-554,615-624`；`src/runtime/inference/claude_cli.py:65-76,417-421` |
| UF40 | 人工 gate 在 item 已 active 之后 | `medium` | grok | intake | accept 插入 `lifecycle_state=active`；reject 不 deactivate | `src/runtime/intake/acceptance_snapshot.py` |
| UF41 | adopt 两节点覆盖 / 空 g0 填 clean | `medium` | grok | intake | 树为 root+单 paragraph 跨全文；空 g0→clean；历史 `structurize()` 测试不是生产 adopt | `src/services/lsrag_compiler/adopt.py:66-67,176-227` |
| UF42 | VECTORIZE 包错抹掉原始 code | `medium` | muse | intake | 任意 MkbError 改写成 `VECTORIZE_INFERENCE_FAILED`（该码可恢复），space violation 被重试 | `src/runtime/intake/vectorize.py:376`；`src/runtime/intake/core.py` `_RECOVERABLE_ERROR_CODES` |
| UF43 | content_full header vs query 裸嵌入 | `medium` | muse | intake | 离线 `content_full = header+body`；query 侧 `deterministic_embedding(query.strip())` 无 header 投影 | `src/services/lsrag_compiler/construct.py:59`；`src/runtime/intake/vectorize.py:206-208`；`src/services/retrieval/retrieval_rank.py:194-216` |
| UF44 | 活跃指针 CAS 不单调 | `high` | grok | intake | `_namespace_coordinates` 只读事务 `index_generation+1`；指针 UPDATE 无 `active_index_generation < excluded` | `src/runtime/intake/vector_publish_commit.py:144-160,263-279`；对比 `src/runtime/intake/index_rebuild_commit.py` |
| UF45 | 每阶段复制完整累计 state | `medium` | gpt | intake | 每 stage envelope 复制 raw/decoded/clean/markdown/layered 正文 | `src/runtime/intake/core.py:373-398`；`src/runtime/intake/generation_construct.py:607-614,1339-1375`；`src/runtime/intake/vectorize.py:233-279` |
| UF46 | Python layered validator ≠ JSON Schema | `medium` | gpt | intake | 运行时主要查字段名/string；可接受 schema 会拒的数组-当-字符串等 | `src/contracts/lsrag/layered_content.py:82-96` |
| UF47 | Retrieval UUID 截断 1000 / native ANN 未接线 | `critical` | gpt/grok/muse | retrieve | `ORDER BY vector_record_uuid LIMIT 1000` 再 Python cosine；`native_ann` 不传 Turso、RetrievalService 无 VectorSearchPort | `src/services/retrieval/retrieval_rank.py:100-130,132-191`；`src/services/retrieval/retrieval_request.py:46-77,52`；`src/runtime/config.py:26-27`；`src/persistence/factory.py:53-58`；`api/app.py:257-264` |
| UF48 | dedup 固定 summary-first | `high` | gemini/gpt | retrieve | resolved summary priority 0、original 1，在 ANN score 之前比较 | `src/services/retrieval/retrieval_pack.py:260-273` |
| UF49 | inflate 继承 query.filters | `high` | gemini | retrieve | 内部拓扑寻根带着外部 `channel` 过滤，`channel=original` 时寻根失败 | （gemini 汇总表未给精确行号；标题指向 `_inflate_documents`） |
| UF50 | Team inactive/deleted 后仍可检索 | `high` | gpt/grok | retrieve | 只更新 `mkb_teams.status`；检索路由不 `require_active`；候选 SQL 无 `teams.status` | `src/services/teams.py:110-148`；`src/services/retrieval/retrieval_request.py:343-359`；`api/public/routes.py:452-469` |
| UF51 | offline 查询混用 live embedding 空间 | `high` | gpt/grok | retrieve | 仅看进程级 `_live_inference`；false 时按 namespace dimension hash，不看 adapter_kind | `src/services/retrieval/retrieval_request.py:96-99`；`src/services/retrieval/retrieval_rank.py:145-149`；`tests/unit/test_retrieval_service.py:130-135` |
| UF52 | 64↔1024 维度 schism | `high` | muse | retrieve | 同 `namespace_key='default'` 维度冲突 409，新活模型向量永不晋升 serving | `src/runtime/intake/core.py:56`；`src/services/config_snapshots.py:723`；`src/runtime/intake/vectorize.py:366`；`src/runtime/intake/vector_publish_commit.py:289-304` |
| UF53 | hydration N+1 与无界 rebuild 巨事务 | `high` | gpt/muse | retrieve | 每 hit 串行两次 load/read_verified/hash/parse；scatter 10k 与 team rebuild 单写事务无界 | `src/services/retrieval/retrieval_request.py:138-141`；`src/services/retrieval/retrieval_pack.py:34-116,188-259`；`src/persistence/retrieval_access.py:168-215,260-291`；`src/contracts/api/models.py:134` |
| UF54 | 单通道 purge 破坏 Proof 完整性 | `critical` | gemini | retrieve | `channel_filter` 只软删一通道后 `COUNT(*)` < `proof.actual_count`，该世代检索全灭 | `src/services/vector_purge.py:58-65`；`src/services/retrieval/models.py:59-75` |
| UF55 | 向量唯一键不含 generation | `high` | grok | retrieve | `ux_vec_coord_active` 无 `index_generation`；同 coordinate UPDATE 把 serving 行改 withdrawn | `src/persistence/migrations/001_initial.sql:1871-1874`；`src/runtime/intake/vector_publish_commit.py:390-395` |
| UF56 | packing 重复填充 Document Root | `medium` | gemini | retrieve | 同代多 Hit 不去做重，重复填充同一 Root 挤爆窗口 | （gemini 汇总表未给精确行号；标题指向 Context Packing） |
| UF57 | 第二重 eligibility 栅栏不完整 | `medium` | muse | retrieve | 注入 EligibilityPort 时只信其返回；SQL 回退不镜像完整 S09+S04 谓词 | `src/services/retrieval/retrieval_rank.py:279-322` |
| UF58 | 普通 publish 用 namespace 计数分配 generation | `medium` | gpt | retrieve | ordinary publish=`namespace.index_generation+1`，rebuild=`pointer.active+1` | `src/runtime/intake/vector_publish_commit.py:263-279`；`src/runtime/intake/index_rebuild_plan.py:355-362` |
| UF59 | vector.upserted 丢 generation artifact UUID | `low` | gpt | retrieve | 读缺失字段而非已验证的 `dual_channel_artifact_uuid` | `src/runtime/intake/vectorize.py:333-337` |
| UF60 | index.rebuild 被未 serving item 毒死 | `high` | gemini/grok | retrieve | 团队 resolve 收集 active+latest 不要求 serving；执行期一条 stale 使整 Task 失败；reactivate 恢复 lifecycle 不恢复 serving | `src/services/intake_lifecycle/targets.py`；`src/runtime/intake/index_rebuild_plan.py:258-264` |
| UF61 | 非法 outbox 行永久卡住唯一 supervisor | `critical` | grok | workflow | 同一事务 `attempts+1` 后 `json.loads` 失败整笔回滚；`drain_once` 先耗 outbox，抛错则不 claim Process / repair | `src/runtime/workflow/runtime_outbox.py:38-59,77-104`；`src/runtime/workflow_supervisor.py:39-51` |
| UF62 | 唯一 supervisor 串行，pool cap 是假并发 | `high` | gpt | workflow | 循环逐个 `await worker.run_once()`，没有 per-pool worker task | `src/runtime/workflow_supervisor.py:43-50`；`src/runtime/workflow/dispatch.py:12-18` |
| UF63 | retirement 遇失效知识死循环阻塞 GC | `critical` | gemini | workflow | deactivated/deleted 时 `_active_pointer_tx` 空，soft_purge 返回但 intent 保持 `open`，占满队头 LIMIT 100 | `src/services/index_retirement.py:320-327,402-406,497-518` |
| UF64 | GC 在事务内 unlink 并持写锁 | `high` | gemini/muse | workflow | `persistence.transaction()` 内 `unlink` + 写 proof；回滚时物理对象已无；慢盘阻塞全部写路径 | `src/services/object_gc.py:145-162,198-269`；`src/storage/local_store.py:34` |
| UF65 | delete_if_unreferenced 未加锁 | `high` | gemini | workflow | 物理删除不在 `self._write_lock` 内，与 `promote()` 竞态 | （gemini 汇总表未给精确行号；标题指向 `LocalObjectStore.delete_if_unreferenced`） |
| UF66 | 对象 release 与真实 orphan GC 未实现 | `high` | gemini/gpt | workflow | 生产无 `released_at`；FS-only orphan 无 catalog 行；无 CAS 目录反向扫描；intake.delete 只建 open intent | `src/services/object_gc.py:145-162`；`src/services/intake_lifecycle/lifecycle_apply.py:270-300`；`tests/unit/test_object_gc.py:169-177` |
| UF67 | tombstoned digest 可被新 live ref 复用 | `high` | gpt | workflow | lookup 不滤 `tombstoned_at IS NULL`；tombstone 后同 digest 新 live ref 挂旧 uuid | `src/services/artifacts.py:131-149`；`src/services/config_snapshots.py:330-365`；`src/runtime/intake/generation_artifacts.py:554-589`；`src/runtime/intake/index_rebuild_commit.py:304-325` |
| UF68 | OutcomeArtifactCommitter 永不清理 `_pending` | `high` | gemini/gpt | workflow | 进程级 dict 成功/失败/取消都不 pop；callback 捕获完整 state | `src/services/artifacts.py:44-50,63-81,89-120`；`src/runtime/intake/core.py:127-139` |
| UF69 | GC/retirement scanner 一次异常永久退出 | `high` | gpt/muse | workflow | `run_forever` 无 try/except；lifespan 只 suppress CancelledError，不重启 | `src/runtime/object_gc.py:42-50`；`src/runtime/index_retirement.py:40-46`；`api/app.py:442-446,519-523` |
| UF70 | claim_next 每轮只 fail 一个过期项 | `high` | muse | workflow | `deadline_at < ? LIMIT 1` 无 ORDER BY，fail 后直接 `return None`，不继续 admit/claim | `src/runtime/workflow/runtime_core.py:353-379`；`src/runtime/workflow/worker.py:48` |
| UF71 | Process 重试固定 1s 无 jitter | `medium` | gemini | workflow | 固定 1s 重试易惊群 | （gemini 汇总表未给精确行号） |
| UF72 | 取消后仍消费 Gate Decision | `medium` | gemini | workflow | 已取消进程仍消费 Gate，Outbox 重试 8 次进死信 | （gemini 汇总表未给精确行号） |
| UF73 | Outbox dead 无事件/告警 | `medium` | gemini | workflow | dead 转换不同事务写 `outbox.dead` 领域事件，也不递增指标 | （gemini 汇总表未给精确行号） |
| UF74 | fencing token 哈希从未校验 | `medium` | muse | workflow | 写入 `claim_token_hash` 但 mark_running/accept 只查 generation；worker 丢弃 token | `src/runtime/workflow/runtime_core.py:350-476,494-543`；`src/runtime/workflow/worker.py:51` |
| UF75 | 反向代理下 request_ip 恒为私网 | `high` | gemini/muse | security | 只用 `request.client.host`；Nginx/Envoy 后全员 `is_internal_ip`，`/internal` 与 `/metrics` 变公网可达 | `src/runtime/security.py:463-481`；`api/dependencies.py:150-165` |
| UF76 | 限流桶超限 / degraded 全局 fail-open | `high` | gemini/grok/muse | security | 超 4096 桶或任意异常 → `degraded=True allowed=True` 不复位；`check_ip` 在 `authenticate` 前 | `src/runtime/security.py:104-106,185-215`；`api/dependencies.py:104-116,105,146` |
| UF77 | HTML href/src 任意协议 XSS | `high` | gemini | security | Sanitizer 未白名单 URL scheme，可写入 `javascript:` | （gemini 汇总表未给精确行号；标题指向 HTML Sanitizer） |
| UF78 | 公共 extras 可持久化 secret | `high` | gpt/muse | security | PayloadExtra 只查 JSON/64KiB；`_SECRET_KEYS` 精确集漏驼峰；Team/Task PATCH 跳过；signed URL/NaN/百万字符 records 可进库 | `src/contracts/common/models.py:24-36,111-119`；`src/runtime/security.py:420-423`；`src/services/config_snapshots.py:427-463`；`src/contracts/api/models.py:44,343,357` |
| UF79 | /docs /redoc /openapi.json 默认开放 | `medium` | grok/muse | security | FastAPI 默认 docs 无 dependencies；grok 兼称 bootstrap `MkbError: pass` | `api/app.py:407-414,450-451` |
| UF80 | PYTEST_CURRENT_TEST sqlite 后门 | `high` | muse | security | `sqlite_backend_permitted()` = 环境变量真值，生产可伪造绕过 Turso 要求 | `src/persistence/factory.py:12-16`；`src/runtime/config.py:23` |
| UF81 | Starlette 0.46.2 Host/request.url CVE | `medium` | gpt | security | 钉死 0.46.2 落入 GHSA-86qp-5c8j-p5mr；应用读 `request.url.path` 且无 TrustedHost | `api/app.py:117-119` |
| UF82 | IPv6-mapped 未当 loopback/私网 | `medium` | grok | security | `IPv6Address('::ffff:127.0.0.1').is_loopback` 为 False；mapped RFC1918/metadata 同样 | `src/runtime/security.py:335-344` |
| UF83 | denial audit 写失败消耗 sampler | `medium` | gpt | security | `decide()` 先推进 detail/summary；写失败抛错但不回滚，达上限后 disposition=DROP 直接 401 无审计行 | `api/dependencies.py:63-97`；`tests/unit/test_security_boundary.py:207-230` |
| UF84 | 入站无全局 body size 限 | `medium` | muse | security | 无 ContentLengthLimitMiddleware；10k records 在 Pydantic 422 前全缓冲 | `api/app.py:451`；`src/contracts/api/models.py:129`；`api/app.py:464` |
| UF85 | 一批测试删掉 SUT 也会绿 | `critical` | gemini/gpt/grok/muse | tests | `assert ... or True`；ReadPort `__new__` 后断言自造 dict；sidecar 未实例化只断言局部 MkbError；CW soak 8 次串行且断言孤立变量；缺文件 `return`；无 assert；GC 手工插 orphan；fail-path 私有 helper / 永远成功 facade | `tests/unit/test_turso_driver.py:99,112-128`；`tests/unit/test_ns4_readport_reports.py:8-23`；`tests/unit/test_ns4_diagnostic_sidecar.py:15-28`；`tests/integration/test_ns4_cw_soak.py:50-58`；`tests/domain/test_ns4_no_r3_ingest.py:13-14`；`tests/unit/test_ns4_sink_required.py`；`tests/unit/test_object_gc.py:33-63,169-177`；`tests/e2e/test_ns4_fail_path_turso.py:31-69`；`tests/e2e/test_single_intake_pipeline.py:173-323`；`tests/unit/test_dispatch_mega.py:350-365`；`tests/unit/test_ns4_jsonl_journal.py:10-15`；`tests/domain/test_r4_launch_lock.py:26` |
| UF86 | E2E sqlite3.connect Turso 文件 / 固定轮询 | `high` | gemini/gpt/grok | tests | `persistence_backend=turso` 后 `sqlite3.connect` 触发 disk I/O；5s/20ms 轮询顺序依赖；local_runtime 关闭 CW/native-vector 宪法探针 | `tests/e2e/test_index_rebuild.py:18-27,120`；`tests/e2e/test_generation_pipeline_contracts.py:29-38,83-110`；`tests/local_runtime.py:17-25` |
| UF87 | 全量 pytest 与 Ruff 均不绿 | `high` | gpt/gemini | tests | 本轮记录 431–433 passed / 8–10 failed；`ruff check` 9 errors（F401/I001/B904/B017/F811/F841） | `uv run pytest`；`uv run ruff check .` |
| UF88 | 黄金摄取 E2E 被 LiveEmbeddingFixture Mock | `high` | gemini | tests | `_LiveEmbeddingFixture` 全量替换核心模型通信 | （gemini 汇总表未给精确行号；标题指向 `_LiveEmbeddingFixture`） |
| UF89 | 源码正则扫描伪装行为测试 | `medium` | gemini | tests | 单元测试大量读源码做文本扫描，未走真实调用 | （gemini 汇总表未给精确行号） |
| UF90 | pytest 配置宽松 | `high` | muse | tests | addopts 仅 `-q --tb=short`；无 strict-markers/config、`-W error`、coverage fail_under、顶层 conftest | `pyproject.toml:38-41` |
| UF91 | local_mock 豁免三大探针 | `high` | muse | tests | e2e 复用 `concurrent_writes_required=False, native_vector_required=False, live_inference=False`；Turso 文件缺失则 skipIf | `tests/local_runtime.py:21-25`；`tests/unit/test_turso_driver.py:87`；`tests/integration/test_r3_turso_evidence_ready.py:12` |
| UF92 | 检索栅栏无 deactivate→empty e2e | `medium` | muse | tests | 空集恒真比较；e2e 只断言 succeeded，无停用后检索为空 | `tests/unit/test_retrieval_service.py:279,315-335`；`tests/e2e/test_single_intake_pipeline.py:148`；`tests/e2e/test_source_capability_paths.py:71-145` |
| UF93 | wheel 缺 migration SQL，安装无法启动 | `critical` | gpt | delivery | `pyproject.toml` 无 package-data；干净 wheel 的 migrations 只有 `__init__.py`，无 `.sql`/prompts/schemas | `pyproject.toml:32-35`；`src/runtime/config.py:109-111`；`api/app.py:402-404` |
| UF94 | /ready 持写锁 + idle 50ms 全量探活 | `medium` | gpt/muse | delivery | Turso `readiness()` 在 `_write_lock` 内 verify+probe；claim 每次完整 HealthAggregator，含 journal_mode 切换与 vector SQL | `src/persistence/turso/port.py:100-130`；`src/runtime/workflow/runtime_core.py:337-346`；`src/runtime/workflow_supervisor.py:47-49,68-72`；`api/app.py:166-197`；`api/dependencies.py:191-194` |
| UF95 | schema title 在 adopt/construct 静默丢失 | `medium` | gpt | delivery | wire 允许 title；adopt/construct/projection 只留 body | `src/services/lsrag_compiler/adopt.py:216-245,307-324`；`src/services/lsrag_compiler/construct.py:54-68`；`src/services/lsrag_compiler/payloads.py:170-184` |
| UF96 | 双层背压分叉 | `high` | muse | delivery | Facade limits 与 DispatchCaps 独立；retrieval.search embed 直连 facade 绕过编排 | `api/app.py:245-250`；`DispatchCaps.from_settings` |
| UF97 | browser/OCR/Vision/LLM-clean 已注册未注入 | `high` | gpt/grok/muse | delivery | 定义 active 且 process_key 可 dispatch，但 `IntakePipeline(..., clean_llm=None, browser_fetcher=None)`；公共 profile map 不产生这些 selector | `src/workflows/lsrag_definition.py:882-1070,929-940`；`api/app.py:315-330`；`src/runtime/intake/clean_preflight.py:76-85`；`src/runtime/intake/core.py:342-367`；`src/services/config_snapshots.py:490-514` |
| UF98 | bootstrap/retention 静默 pass | `medium` | muse | delivery | `except MkbError: pass` / `except Exception: pass` 无 log/metric | `api/app.py:407-413,523`；`src/persistence/engine.py:33,40` |
| UF99 | Task 幂等指纹含 audit.created_at | `medium` | grok | delivery | `stable_digest(request.model_dump())` 含审计时间戳，合法重试变 conflict | `src/runtime/task/task_create.py:53-71` |
| UF100 | raw exception 未脱敏写入 Process/Outbox | `medium` | gpt | delivery | `str(exc)` 进 `error_message`/`last_error`，无统一 redaction | `src/runtime/workflow/worker.py:52-60`；`src/runtime/workflow/runtime_outcome.py:443-452`；`src/runtime/workflow/runtime_outbox.py:102-104,331-341` |
| UF101 | object/schema readiness 假 ready | `high` | gpt | delivery | identity 存在即 ready，即使非 JSON；schema 只比 ledger checksum，`DROP TABLE mkb_tasks` 后仍 true | `src/storage/local_store.py:41-49,134-139`；`src/persistence/migration_runner.py:147-155` |
| UF102 | Team payload_extra 无法清空 | `low` | gpt | delivery | 空 `{}` 当无 mutation；truthiness 保留旧值；Task patch 已用 `model_fields_set` | `src/contracts/api/models.py:45-53`；`src/services/teams.py:91-103` |
| UF103 | Task/Team 并发 PK 冲突走 500 | `high` | muse | delivery | SELECT-then-INSERT 遇 `IntegrityError` 未映射为 409 identity-conflict | `src/runtime/task/task_create.py:59-91`；`src/services/teams.py:45-58` |

---

## 3. verified-findings 台账（逐条独立复核 · 核心）

> 每条 UF 对应恰好一条 VF。证据均为本轮打开的当前 HEAD `file:line`。Phase-2 JSON 为线索；薄证据已抽查。

### 3.1 台账主表

| VF# | 对应UF | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据（当前代码 file:line）| 初步处置 |
|-----|--------|------|------|------|----------|--------|------------------------------|----------|
| VF1 | UF1 | UoW cancel/commit 未 rollback 污染唯一连接 | `critical` | gemini/gpt | `valid` | `[true-bug]` | `sqlite_port.py:88-94` / `turso/port.py:92-98`：`except Exception` + `else commit`；单例连接 `sqlite_port.py:62-73` / `turso/port.py:64-77`；py312 `CancelledError` 是 `BaseException` | `fix` |
| VF2 | UF2 | Turso 单连接 + BEGIN IMMEDIATE + CW 探针剧场 | `critical` | gemini/gpt/grok/muse | `valid(子项 overstated)` | `[partial-delivery]` | 见 §3.2.2。Gemini「破坏生产库 MVCC」过称：`connect()` 从不粘滞 MVCC | `fix` |
| VF3 | UF3 | sidecar 并发触发 native abort | `critical` | gpt | `valid` | `[true-bug]` | `sidecar.py:23-57` 每 insert 新 `turso.connect` + `journal_mode=mvcc` + `BEGIN CONCURRENT`；`observability.py:158-161` `to_thread(sidecar.insert)`；`api/app.py:309-314` 生产启用；soak `test_ns4_cw_soak.py:53-56` 自承并发会 abort | `fix` |
| VF4 | UF4 | CAS 依赖未归一化 pyturso rowcount | `medium` | grok | `valid(子项 overstated)` | `[true-bug]` | `turso/port.py:24-25` 返回 raw cursor；`runtime_core.py:462-477,553-558` 读 `rowcount`；Turso CAS 无单测。Grok「恒 1/恒 -1 则 fence 失效」无实测：pyturso 0.7.2 对非 RETURNING DML 填 `rows_changed` | `fix` |
| VF5 | UF5 | migration ledger `!r` 插值 | `medium` | muse | `valid(子项 overstated)` | `[true-bug]` | `migration_runner.py:132-138` f-string `VALUES ({id!r},{checksum!r},{utc_now()!r},'mkb')` 拼进 `executescript`。供应链注入过称：id 来自 glob `83-88` | `fix` |
| VF6 | UF6 | Turso executescript 回退多语句失败 | `high` | muse | `stale-rejected` | `n/a` | 回退枝 `migration_runner.py:65-71` 对当前 pyturso 死代码；`tests/unit/test_turso_driver.py:29-63` 与 `test_d04_write_paths.py:231-247` 已绿证明 migrate 链落地 | `stale-rejected` |
| VF7 | UF7 | 迁移 010 生成 32 位非 UUID | `medium` | gemini | `valid-edge` | `[true-bug]` | `010_spark_vl_embed_model_key.sql:12` `lower(hex(randomblob(16)))`；`ids.py:43-50` 要求连字符 v4/v7。仅 upgrade 有 `qwen-vl-2b` 时触发；`model_uuid` 非公共 path 参数 | `fix` |
| VF8 | UF8 | 时间戳微秒 vs 毫秒 | `medium` | gemini | `valid-edge` | `[true-bug]` | `time.py:10-12` us vs `:23` ms；`artifacts.py:140,148` SQLite `%f`=ms；claim 路径 `runtime_core.py:348-473` 两侧都是 Python us。Gemini「通用 SQL 比较偏差」过称 | `fix` |
| VF9 | UF9 | Claude CLI 超时不杀子进程 | `critical` | gemini/gpt/grok/muse | `valid` | `[true-bug]` | `claude_cli.py:288-304` 只 `wait_for(communicate)`，超时抛 `CLAUDE_CLI_TIMEOUT` 无 kill；`intake/core.py:176-186` 该码可 process-retry。Gemini「主机级 DoS 羊群」过称：supervisor 串行（UF62） | `fix` |
| VF10 | UF10 | 30s lease 无 heartbeat | `critical` | gpt/grok/muse | `valid-conditional` | `[true-bug]` | `worker.py:45-53` claim 30s 后 `await handler.run` 零 heartbeat；heartbeat 存在于 `runtime_core.py:546-558` 无生产调用；generate 180s / CLI 900s。`valid-conditional` 只说明单 supervisor 运行中不会 reclaim；crash/第二副本仍会重复执行，故保持 muse-R2 最严 `critical`，本阶段须修 | `fix` |
| VF11 | UF11 | salvage/dispatch_pool 不是运输 SSOT | `high` | gpt/grok | `valid` | `[true-bug]` | admit `runtime_core.py:304-315` 看 `live_inference`；snapshot omit+normal 写 local 不看 live（`config_snapshots.py:573-591`）；salvage 同 Process 调 Claude（`generation_construct.py:168-180,270-284`）无再 admit | `fix` |
| VF12 | UF12 | salvage 优先级逆变 | `medium` | gemini | `valid-edge` | `[true-bug]` | `_can_salvage_local_inference` `generation_construct.py:168-176` 要求 `task_priority=='normal'`。标题「无法降级到本地」方向反了：默认 urgent/high 本就走 NI；真缺口是显式 local+urgent 失败后不能 salvage | `fix` |
| VF13 | UF13 | OVER_BUDGET 键遗漏 transcribe/construct | `high` | gemini | `valid` | `[true-bug]` | `dispatch.py:20-36` GENERATE 含 transcribe/construct，OVER_BUDGET 只有 structurize + 三个 clean.*_llm；admit `runtime_core.py:300-312` 只读该集合 | `fix` |
| VF14 | UF14 | prompt file 在 state=None 时绕过 Snapshot | `medium` | gemini | `valid-edge` | `[true-bug]` | `_ns1_prompt_file` `generation_construct.py:351-370`：无 role 则读磁盘哈希 live bytes。生产 structurize/transcribe 传 state；单测 `test_ns1_generation_cli.py:23-28` 走 bypass | `fix` |
| VF15 | UF15 | LocalVllmAdapter 每请求新建 AsyncClient | `high` | gemini | `valid` | `[true-bug]` | `local_vllm.py:66-98` 只存 `_transport`；`probe:187-195` 与 `_request:199-206` 每次 `async with httpx.AsyncClient`；`api/app.py:225-230` 不注入共享 client | `fix` |
| VF16 | UF16 | CLI 泄露正文与父进程环境 | `high` | gpt | `valid` | `[true-bug]` | `prompt_transport_for` `<16KiB` 走 argv（`claude_cli.py:59-62,149-151`）；`SubprocessClaudeCli` `env=None` 继承父环境（`284-297`）；README §9.5 声称 stdin-only。`internal_token` 是 plain str（`config.py:15-17`） | `fix` |
| VF17 | UF17 | salvage 失败证据可串台 | `high` | gpt | `valid` | `[true-bug]` | ContextVar `generation_evidence.py:10-33`；flush 用当时 Process 身份（`:36-98`）；生产 flush 仅 `_fail_process_tx`（`runtime_outcome.py:460-463`）；salvage 成功不 take/flush | `fix` |
| VF18 | UF18 | schema 未冻结 / live readiness 假 ready | `high` | gpt | `valid` | `[true-bug]` | snapshot `config_snapshots.py:191-221` 无 schema bytes；generate 再读 DB digest（`generation_live.py:133-168`）；vLLM 只发 `{type:json_object}`（`local_vllm.py:161-166`）；`inference_probe_enabled` 默认 False（`config.py:38`），probe 把 3xx 当健康（`187-195`） | `fix` |
| VF19 | UF19 | 运输耗尽变成终态失败 | `high` | grok | `valid` | `[true-bug]` | facade `332-342` 把最后一次 RETRYABLE 改写 EXHAUSTED；`_RECOVERABLE_ERROR_CODES` `intake/core.py:176-186` 含 RETRYABLE 不含 EXHAUSTED；`test_d01_review_fixes.py:60-68` 锁的是 facade 不再发出的码 | `fix` |
| VF20 | UF20 | SupplyFence 允许集过大 | `medium` | muse | `valid-by-design` | `n/a` | `api/app.py:231-239` 用 `default_enabled_inference_bindings()` 五条；winners 三条（`registry.py:550-578`）。docstring `139-146,552-557` 明确 fence 是 composition allow-list 而非 L1 winners。Muse「伪造备用模型过 fence」无公共 raw-binding 路径；无需改动，不进三类 | `acknowledge` |
| VF21 | UF21 | Claude CLI 无并发门限 | `high` | muse | `valid` | `[true-bug]` | construct json/summarizer/markdown 直接 `cli.run`（`generation_construct.py:401-408,454-461,584-590`）；CLI-clean 走 `ClaudeCliCleanLanguageModel` → `src/runtime/inference/claude_cli.py:381`；`clean_preflight.py:107-108` 只包装该模型。`:164-165` 是 transport picker 返回 `'claude_cli'`，不是 `cli.run`。ConcurrencyGate 只包 facade `_invoke`（`facade.py:313-349`）。当前串行 supervisor 挡住 live fork bomb | `fix` |
| VF22 | UF22 | Facade 重试占满 gate 且无 jitter | `medium` | gemini/gpt/muse | `valid` | `[true-bug]` | `facade.py:313-349` 持 lease 循环 sleep；`_retry_delay:486-487` 无 jitter；`api/app.py:241-252` recorder=None。Gemini「级联 503」需重叠 generate+embed | `fix` |
| VF23 | UF23 | Billing 恒真 | `medium` | grok | `valid-by-design` | `[true-deferred]` | `billing.py:16-21` 恒 True；admit/salvage 当真门（`runtime_core.py:310`；`generation_construct.py:178-179`）。README K10 / NS2-O1 本阶段只承诺 always-permit port | `deferred-by-owner` |
| VF24 | UF24 | 408/425 被判 validation | `medium` | muse | `valid` | `[true-bug]` | `local_vllm.py:212-215` 仅 `{429,503}` 或 `>=500` → RETRYABLE，其余非 2xx → VALIDATION_REMOTE | `fix` |
| VF25 | UF25 | INTERNAL_UNEXPECTED 不重试 | `medium` | muse | `valid-by-design` | `n/a` | facade `343-346` 裸 Exception → INTERNAL 不循环，这是正确默认（无需改动）。子断言「httpx 超时跳过重试」假：adapter `209-210` 已把 `RequestError` 映射 RETRYABLE | `acknowledge` |
| VF26 | UF26 | PDF/doc LLM 二进制替换解码 | `high` | gpt | `valid` | `[true-bug]` | `claude_cli.py:371-386` `del media_type` + `blob.decode(..., errors='replace')`；NI LLM-clean 走此包装（`clean_preflight.py:86-119`） | `fix` |
| VF27 | UF27 | live vectorize 静默丢层仍签完整 proof | `critical` | gemini/gpt/grok | `valid` | `[true-bug]` | `vectorize.py:185-204` 滤掉超 16k 非 g0-summary 后重绑 `vector_inputs`；`:247-248` `required_units=succeeded_units=len(vector_inputs)`；retrieval proof 只比 COUNT（`retrieval/models.py:59-75`） | `fix` |
| VF28 | UF28 | HTML 提取器抹平全部换行 | `critical` | gemini | `valid` | `[true-bug]` | `intake/text.py:12,17-72` 在 block 边界插入 `\\n`；`:102-109` `extract_html_text` 用 `_SPACE.sub(' ', ...)` 再压平。`clean_plain_text:96-99` 已有正确配方但未用 | `fix` |
| VF29 | UF29 | 重复文本 anchor 永远第一次出现 | `critical` | gemini/gpt | `valid` | `[true-bug]` | `adopt.py:224-235` `clean.find(normalized_body)` 从 0；occurrence_count 只记账不消歧。S06-T022 视重复/乱序为 kernel fail | `fix` |
| VF30 | UF30 | PDF raw bytes 正则扫描 | `high` | gemini | `valid` | `[partial-delivery]` | `src/runtime/intake/types.py:32-34,144-171` raw bytes 扫 `(literal)Tj`；无 BOM 的 UTF-16 走 latin-1。`intake/types.py` 是 78 行 clean-port 模块，无 `:144-171`。压缩 PDF 空 literals → 422 OCR-unavailable（诚实 fail-closed，不是静默乱码） | `partial-fix` |
| VF31 | UF31 | ChinaTax/REA 外部键与 HTML 解析缺陷 | `high` | gemini | `valid(子项 overstated)` | `[true-bug]` | REA HTML 走 `extract_html_text`（同 VF28）。「缺 ID 写成 None 主键」不可达：`src/contracts/intake/providers/chinatax.py:33`（`id: str \| int` 必填）与 `src/contracts/intake/providers/realestate.py:103`（`listingId: str \| int` 必填）。`intake/api/providers/chinatax.py:32-33` 是 `content_id=content_id`；`intake/api/providers/realestate.py:102-103` 是 `FilterMeta` 构造 | `fix` |
| VF32 | UF32 | 短文本粒度闭集硬报错 | `high` | gemini | `valid-by-design` | `n/a` | `adopt.py:25-28,45-47` 闭集 mismatch 是 S06 不变量。自适应降级从未承诺 | `acknowledge` |
| VF33 | UF33 | Construct 对 Original 逐字过敏 | `high` | gemini | `valid-by-design` | `n/a` | `adopt.py:311-320` original 不等 → `CONSTRUCT_KERNEL_ORIGINAL_MUTATION`；S07 不改写 S06 original。`test_adopt_layered_json.py:173` 锁死此 fail-closed | `acknowledge` |
| VF34 | UF34 | acquisition 绕过预算并写假 proof | `high` | gpt | `valid(子项 overstated)` | `[true-bug]` | `acquisition_ingest.py:358-370` local_object 无字节预算；`:456-496` 一律盖 `within_configured_acquisition_budget`。HTTP static 实际有 cap（`http_acquisition.py:194,262-270`）—「全部无界」过称 | `fix` |
| VF35 | UF35 | 重复 ingest 总是新建 Source/Item | `high` | gpt | `valid` | `[true-bug]` | `acquisition_ingest.py:91-97` 单文档总 `uuid7()`；`acceptance_snapshot.py:98-112` INSERT active 无按 key SELECT。UNIQUE `(team, source_uuid, key)` 因每次新 source 而空转 | `fix` |
| VF36 | UF36 | Artifact handle/digest/size 不是同一 bytes | `high` | gpt | `valid` | `[true-bug]` | `acceptance_snapshot.py:63-70,132-167` raw/clean 共享 `output_ref`/`output_size` 却写不同 semantic digest。rebuild 特例读 `envelope['state']['clean_text']`（`core.py:462-474`） | `fix` |
| VF37 | UF37 | 默认 stub 把 summary 写成 original | `high` | grok | `valid` | `[partial-delivery]` | `config.py:44` 默认 `ns1_cli_mode='stub'`；`claude_cli.py:110-115,401-421` 预算内 summary=original。e2e 不断言 `summary!=original`。`MKB_NS1_CLI_MODE=subprocess` 时不是静默生产 summarizer bug | `partial-fix` |
| VF38 | UF38 | JSON 贪婪切片 / schema 未交给 vLLM | `medium` | gemini/grok | `valid(子项 overstated)` | `[true-bug]` | `facade.py:49-66` `find('{')`+`rfind('}')`；vLLM 仅 `json_object`（`local_vllm.py:161-162`）。空 g0→clean 是 kernel invention（`adopt.py:66-67`），不是切片缺陷。不 crash，抛 VALIDATION_STRUCTURED | `fix` |
| VF39 | UF39 | markdown transport 写死 claude_cli | `medium` | grok/gpt | `valid` | `[true-bug]` | live receipt `generation_construct.py:544-554` `transport=api_inference`；artifact `:615-623` 写死 `claude_cli`。stub json 只读 `package['clean']`（`claude_cli.py:65-76,416-423`） | `fix` |
| VF40 | UF40 | 人工 gate 在 item 已 active 之后 | `medium` | grok | `valid` | `[true-bug]` | `acceptance_snapshot.py:98-112` INSERT `lifecycle_state='active'`；reject（`runtime_gates.py:122-138`）不 UPDATE item。检索仍要 serving_revision，故非 serving 泄漏，是生命周期泄漏 | `fix` |
| VF41 | UF41 | adopt 两节点覆盖 / 空 g0 填 clean | `medium` | grok | `valid` | `[partial-delivery]` | `adopt.py:176-210` 生产 adopt 总是 root+单 paragraph 跨全文；空 g0→clean 是声明的唯一 invention（`:37,66-67`） | `partial-fix` |
| VF42 | UF42 | VECTORIZE 包错抹掉原始 code | `medium` | muse | `valid` | `[true-bug]` | `vectorize.py:402-430` `except MkbError` 一律改写 `VECTORIZE_INFERENCE_FAILED` 503；该码在 `_RECOVERABLE_ERROR_CODES`。SPACE_VIOLATION 在 embed try 内会被包；`:438-440` 的 LAYER_A mismatch 在 try 外 | `fix` |
| VF43 | UF43 | content_full header vs query 裸嵌入 | `medium` | muse | `valid-edge` | `[true-bug]` | `vectorize.py:161-168,206-208` 仅 `metadata_refresh` 给 headers；query 裸 embed 是 `retrieval_request.py:401-412`（`_embed_query` `texts=[query.query]`）。`:96-99` 是 live-inference 门；`:273` 是 `_normalise_request` 把 `query.strip()` 写入 `_SearchInput`。默认 `full_construct` 对齐。muse 所引 `retrieval_rank.py:194-216` 现已是 `_decode_embedding` | `fix` |
| VF44 | UF44 | 活跃指针 CAS 不单调 | `high` | grok | `valid` | `[true-bug]` | `vector_publish_commit.py:263-279` 只读事务 `index_generation+1`；指针 UPDATE `:144-160` 只 CAS `pointer_row_revision`，无 `active < excluded`。rebuild 有更严 fence（`index_rebuild_commit.py:105-124`） | `fix` |
| VF45 | UF45 | 每阶段复制完整累计 state | `medium` | gpt | `valid` | `[true-bug]` | `core.py:373-387` 整份 state JSON 进 envelope；construct `607-614,1339-1375` / vectorize `233-268` 继续复制。vector_records 去 body 但 inherited state 仍有 raw/clean/markdown | `fix` |
| VF46 | UF46 | Python layered validator ≠ JSON Schema | `medium` | gpt | `valid` | `[partial-delivery]` | `layered_content.py:79-118` 只查键与 string/null；schema `lsrag.layered_content.v1.json` 要求 date-time / UUID array / uri | `partial-fix` |
| VF47 | UF47 | Retrieval UUID 截断 1000 / native ANN 未接线 | `critical` | gpt/grok/muse | `valid(子项 overstated)` | `[true-bug]` | 见 §3.2.3。`native_ann` 当生产 ANN 合同过称：README/config 已标明是 scan profile | `fix` |
| VF48 | UF48 | dedup 固定 summary-first | `high` | gemini/gpt | `valid` | `[true-bug]` | `retrieval_pack.py:260-273` `_dedup_key` 先比 resolved=0 vs original `not_needed`=1，再比 `-ann_score`。不丢 original 文本（payload 仍 traceback），丢高分 original hit 身份 | `fix` |
| VF49 | UF49 | inflate 继承 query.filters | `high` | gemini | `valid(子项 overstated)` | `[true-bug]` | `_inflate_documents:187-204` 不 `force_channel`；`retrieval_rank.py:86-89` `channel = force_channel or query.filters.channel`。g0 original 不向量化（`construct.py:116-121`）。不崩：`:205-211` 标 `missing` | `fix` |
| VF50 | UF50 | Team inactive/deleted 后仍可检索 | `high` | gpt/grok | `valid` | `[true-bug]` | `teams.py:110-148` `require_active` 全仓仅定义处；`api/public/routes.py:452-469` 检索只比 token/team_uuid；候选 SQL 无 `mkb_teams.status`。非跨租户泄漏 | `fix` |
| VF51 | UF51 | offline 查询混用 live embedding 空间 | `high` | gpt/grok | `valid` | `[true-bug]` | `retrieval_request.py:69,97-99` 只看进程 `_live_inference`；false 时按 namespace dimension hash（`retrieval_rank.py:145-149`），不核对 adapter/model。写路径冻 Layer A，读路径忽略 | `fix` |
| VF52 | UF52 | 64↔1024 维度 schism | `high` | muse | `valid-edge` | `[true-bug]` | `_ensure_namespace` `vector_publish_commit.py:289-303` 对硬编码 `namespace_key='default'` 任一 Layer-A mismatch 409。不静默混空间（那是 VF51）；缺陷是设置切换无 cutover 路径 | `fix` |
| VF53 | UF53 | hydration N+1 与无界 rebuild 巨事务 | `high` | gpt/muse | `valid(子项 overstated)` | `[true-bug]` | 每 hit 独立 tx+`read_verified`+hash+JSON（`retrieval_access.py:168-215`；pack `:64,:74,:231`）。10k scatter 是 intake DTO 界，不是 S10 I/O | `fix` |
| VF54 | UF54 | 单通道 purge 破坏 Proof 完整性 | `critical` | gemini | `valid` | `[true-bug]` | `vector_purge.py:86-93` `channel_filter!='all'` 只软删一通道；S09 `_PROOF_COMPLETE_SET_PREDICATE` 要求 `actual_count==COUNT(*)`（`retrieval/models.py:59-75`）。e2e 用 `channel_filter='original'` | `fix` |
| VF55 | UF55 | 向量唯一键不含 generation | `high` | grok | `valid` | `[true-bug]` | `001_initial.sql:1871-1874` `ux_vec_coord_active` 无 `index_generation`；`vector_publish_commit.py:379-395` 同 coordinate UPDATE 成 withdrawn。检索要求 `p.active_index_generation=r.index_generation` | `fix` |
| VF56 | UF56 | packing 重复填充 Document Root | `medium` | gemini | `valid` | `[true-bug]` | inflate 把同一 root 挂到同代每个非 g0 hit（`retrieval_pack.py:219-258`）；`_pack:328-350` 每 hit 再 append 一份 `document_root`，无 root 去重。`pack_max_chars=12000` | `fix` |
| VF57 | UF57 | 第二重 eligibility 栅栏不完整 | `medium` | muse | `valid-by-design` | `n/a` | `_apply_batch_eligibility:279-322` 故意 S04-only 然后 `_revalidate_publication_fence`。脏 EligibilityPort 不能重新放行 withdrawn 行 | `acknowledge` |
| VF58 | UF58 | 普通 publish 用 namespace 计数分配 generation | `medium` | gpt | `valid` | `[true-bug]` | ordinary：`_namespace_coordinates` `index_generation+1`（`vector_publish_commit.py:263-279`）；rebuild：`pointer.active+1`（`index_rebuild_plan.py:360-361`）。伤害是 per-item 非单调，不是全局 unique clash | `fix` |
| VF59 | UF59 | vector.upserted 丢 generation artifact UUID | `low` | gpt | `valid` | `[true-bug]` | persisted_records `vectorize.py:221-232` 无 `generation_artifact_uuid`；事件 `:333-336` 读不存在的 `construction_dual_channel_artifact_uuid`。真 key 是 `dual_channel_artifact_uuid`（`:97,216`） | `fix` |
| VF60 | UF60 | index.rebuild 被未 serving item 毒死 | `high` | gemini/grok | `valid` | `[true-bug]` | team scope SELECT active+latest，无 serving 谓词（`targets.py:113-120`）；execute 遇 stale 整 Task 409（`index_rebuild_plan.py:253-264`）。单条非 serving 仍应 409；bug 是 team 准入把毒行冻进集合 | `fix` |
| VF61 | UF61 | 非法 outbox 行永久卡住唯一 supervisor | `critical` | grok | `valid` | `[true-bug]` | `src/runtime/workflow/runtime_outbox.py:38-59` `claim_outbox` 同 TX `attempts+1` 后 `json.loads`，失败回滚（不是 `drain_once`）；`src/runtime/workflow_supervisor.py:39-51` `drain_once` 先耗 outbox，抛错则不 claim/repair。supervisor `run()` 吞 Exception，冻的是 drain 而非进程退出 | `fix` |
| VF62 | UF62 | 唯一 supervisor 串行，pool cap 是假并发 | `high` | gpt | `valid` | `[partial-delivery]` | `workflow_supervisor.py:39-51` `await worker.run_once()`；`worker.py:45-53` 同协程 claim+run。queued cap 仍闸 admit；谎的是 running 并发 | `fix` |
| VF63 | UF63 | retirement 遇失效知识死循环阻塞 GC | `critical` | gemini | `valid` | `[true-bug]` | `src/services/index_retirement.py:314-327` `collect_due` open ORDER BY eligible_at LIMIT 100；`:396-406` `soft_purge` pointer None 返回 POINTER_UNAVAILABLE 不更新 intent。`src/runtime/index_retirement.py` 是 50 行 scanner，无这些行号。≥100 条 stuck 才完全堵死，但更早占满 batch | `fix` |
| VF64 | UF64 | GC 在事务内 unlink 并持写锁 | `high` | gemini/muse | `valid` | `[true-bug]` | `src/services/object_gc.py:190-269` `transaction()` 内 unlink 再 proof/tombstone；注释承认 rollback 留下缺字节。`src/runtime/object_gc.py` 是 54 行 scanner，无 `:190-269`。阻塞时长磁盘相关；正确性洞是 unlink/rollback 分裂 | `fix` |
| VF65 | UF65 | delete_if_unreferenced 未加锁 | `high` | gemini | `valid` | `[true-bug]` | `local_store.py:67-74` promote 持 `_write_lock`；`:120-132` delete 无锁。GC scanner 是 lifespan 兄弟任务（`api/app.py:417-419`） | `fix` |
| VF66 | UF66 | 对象 release 与真实 orphan GC 未实现 | `high` | gemini/gpt | `valid` | `[partial-delivery]` | `src/services/object_gc.py:145-162` 只收 catalogued 无 live ref（与 VF64 同样勿与 `src/runtime/object_gc.py` 撞名）；生产无 `released_at`（唯一 UPDATE 在 `test_object_gc.py:169-177`）；intake.delete 只建 open intent（`lifecycle_apply.py:270-300`）。「GC 完全未实现」过强：手工 orphan 路径能扫。本轮切片见 §5.2，目录 SSOT 余项 VF66.r | `partial-fix` |
| VF67 | UF67 | tombstoned digest 可被新 live ref 复用 | `high` | gpt | `valid` | `[true-bug]` | UNIQUE `(team, digest, size)` 非部分（`001_initial.sql:1800-1801`）；lookup 不滤 `tombstoned_at IS NULL`（`artifacts.py:131-149` 及 snapshots/generation_artifacts/index_rebuild_commit 同形） | `fix` |
| VF68 | UF68 | OutcomeArtifactCommitter 永不清理 `_pending` | `high` | gemini/gpt | `valid` | `[true-bug]` | `artifacts.py:44-50,63-81,89-120` 只 get 不 pop；`core.py:127-139` callback 捕获 state。OOM 是寿命×吞吐，成功路径也无条件泄漏 | `fix` |
| VF69 | UF69 | GC/retirement scanner 一次异常永久退出 | `high` | gpt/muse | `valid` | `[true-bug]` | `src/runtime/object_gc.py:42-50` / `src/runtime/index_retirement.py:40-46` `run_forever` 无 try；lifespan 不重启（`api/app.py:417-446`）。retention 循环相反有 `except Exception: pass`（`api/app.py:509-523`） | `fix` |
| VF70 | UF70 | claim_next 每轮只 fail 一个过期项 | `high` | muse | `valid` | `[true-bug]` | `runtime_core.py:353-379` `deadline_at < now LIMIT 1` 无 ORDER BY，fail 后 `return None`。下一 tick 50ms/1ms 后还会跑，但是 O(N) tick 才能领活任务 | `fix` |
| VF71 | UF71 | Process 重试固定 1s 无 jitter | `medium` | gemini | `valid(子项 overstated)` | `[true-bug]` | `runtime_core.py:62,80` `retry_delay_seconds=1`；`runtime_outcome.py:137-151` `now+1s`；registry 已存 exponential+jitter（`workflow_registry.py:334-337`）未用。「惊群雪崩」对单 worker 过称 | `fix` |
| VF72 | UF72 | 取消后仍消费 Gate Decision | `medium` | gemini | `valid(子项 overstated)` | `[true-bug]` | 终态 cancelled → `consume_gate_decision` 返回 False（`runtime_gates.py:186-187` 只判断 terminal execution）；ACK 在 `src/runtime/workflow/runtime_outbox.py:90-105`（调用 `consume_gate_decision` 后仍 `_complete_outbox`）。cancelling 非 terminal → ConflictError → 8 次后 dead（`runtime_outbox.py:331-341`）。「已取消仍恶性重试 8 次」把两条路径捏在一起 | `fix` |
| VF73 | UF73 | Outbox dead 无事件/告警 | `medium` | gemini | `valid` | `[partial-delivery]` | `_release_outbox:331-341` 设 status=dead，无 DomainEventWriter / `metrics.increment`；`events.py:58-59` allowlist 有 `outbox.dead`；`mkb_outbox_dead_total` 已注册从未 increment。operator GET dead 行仍可见 | `fix` |
| VF74 | UF74 | fencing token 哈希从未校验 | `medium` | muse | `valid-by-design` | `[true-deferred]` | token 写入 `runtime_core.py:350-351,462-491`；`mark_running:494-506` / `accept_outcome` 只 CAS `fencing_generation`。S03 最低要求一条 current fence；不是「fencing 不成立」 | `defer-with-rationale` |
| VF75 | UF75 | 反向代理下 request_ip 恒为私网 | `high` | gemini/muse | `valid-conditional` | `[true-bug]` | `security.py:463-481` 只用 `request.client.host`；默认 bind `127.0.0.1`（`api/app.py:536`）。bypass 条件于 `0.0.0.0` + 代理不改写 ASGI client。README 9.1 拒绝盲信 XFF，但缺 trusted-proxy CIDR | `fix` |
| VF76 | UF76 | 限流桶超限 / degraded 全局 fail-open | `high` | gemini/muse/grok | `valid(子项 overstated)` | `[true-bug]` | `_allow:189-215` 超 `max_buckets=4096` 抛 RuntimeError；`_check` except 永久 `degraded=True allowed=True`。IP-before-auth 与时钟 fail-open 是 S16 设计；Grok HMAC short-circuit 错（`compare_digest` 两边都跑） | `fix` |
| VF77 | UF77 | HTML href/src 任意协议 XSS | `low`（high→low：剩余 href/src 原样复制，生产消费者立刻剥属性只留文本，不可达存储型 XSS / 非 browser BFF） | gemini | `valid(子项 overstated)` | `[true-deferred]` | `intake/web/sanitize.py:14,35-43` 原样复制 href/src。生产消费者立刻剥属性只留文本（`intake/web/__init__.py:25-37`；`text.py:64-65`）。非存储型 XSS；MKB 不是 browser BFF | `defer-with-rationale` |
| VF78 | UF78 | 公共 extras 可持久化 secret | `high` | gpt/muse | `valid` | `[true-bug]` | `PayloadExtraModel` 只 JSON/64KiB（`src/contracts/common/models.py:24-36`）；`_SECRET_KEYS` 精确小写集漏 `apiKey`（`:111-119`）。TeamCreate/Patch 无 `assert_safe_public_data`（`src/contracts/api/models.py:33-54`）；TaskPatch `:357-372` 同样无。`:343-355` 是 `TaskCreate.validate_identity_and_payload`，`:353` 会调用 `assert_safe_public_data` | `fix` |
| VF79 | UF79 | /docs /redoc /openapi.json 默认开放 | `medium` | grok/muse | `valid-by-design` | `[true-deferred]` | `api/app.py:450-451` FastAPI 默认 docs 无 dependencies。README K9/9.2 已记为内网残留。grok 兼称的 bootstrap `pass` 是 VF98 | `defer-with-rationale` |
| VF80 | UF80 | PYTEST_CURRENT_TEST sqlite 后门 | `medium` | muse | `valid(子项 overstated)` | `[true-bug]` | `factory.py:12-16,39-41` 仅看 `PYTEST_CURRENT_TEST`。Muse「export 该变量即可绕过」过称：还要 `persistence_backend=sqlite` | `fix` |
| VF81 | UF81 | Starlette 0.46.2 Host/request.url CVE | `medium` | gpt | `valid(子项 overstated)` | `[true-bug]` | `pyproject.toml:14` fastapi==0.115.12；`uv.lock:342-343` starlette 0.46.2 ∈ GHSA-86qp-5c8j-p5mr。`request.url.path` 仅用于错误码 taxonomy（`api/app.py:125-130`），非 auth bypass | `fix` |
| VF82 | UF82 | IPv6-mapped 未当 loopback/私网 | `medium` | grok | `valid-edge` | `[true-bug]` | `_restricted:334-344` / `is_internal_ip:472-481` 不 unwrap `ipv4_mapped`。默认 `allow_literal_ip=False` 已拒 literal mapped URL；洞在恶意/怪异 resolver 或 `allow_literal_ip=True` | `fix` |
| VF83 | UF83 | denial audit 写失败消耗 sampler | `medium` | gpt | `valid` | `[true-bug]` | `_audit_denial` `api/dependencies.py:63-97` 先 `sampler.decide()` 再写；写失败不回滚桶。鉴权仍拒绝，是审计不变量破，不是准入绕过 | `fix` |
| VF84 | UF84 | 入站无全局 body size 限 | `medium` | muse | `valid` | `[true-bug]` | `create_app` 无 size middleware；`records max_length=10_000` 无字节帽（`api/models.py:134`）；ChinaTax `content/govDoc` 无 `max_length`。默认 127.0.0.1+边缘限仍可能挡住；进程内无边缘则成立 | `fix` |
| VF85 | UF85 | 一批测试删掉 SUT 也会绿 | `critical` | gemini/gpt/grok/muse | `valid(子项 overstated)` | `[true-bug]` | 见 §3.2.1。GC/dispatch_mega/sink fail-path/fail-path e2e 不是 tautology | `fix` |
| VF86 | UF86 | E2E sqlite3.connect Turso 文件 / 固定轮询 | `high` | gemini/gpt/grok | `valid-owner-gated` | `[true-deferred]` | `test_index_rebuild.py:18-27,120` 等 `sqlite3.connect(turso file)`；owner 冻结 NS1-V11。CW waiver 是 UF91 而非第二条 sqlite3 bug | `deferred-by-owner` |
| VF87 | UF87 | 全量 pytest 与 Ruff 均不绿 | `high` | gpt/gemini | `valid(子项 overstated)` | `[true-bug]` | README:15,479-480 记录 433/8 与 ruff 9 errors。现仍见 `test_ns4_migration_013.py:99` B017、`test_ns4_readport_reports.py:8-9` F841、`test_ns4_diagnostic_sidecar.py:7` F401、`claude_cli.py:224-231` B904。pytest 8–10 红主要是 UF86 harness 噪声 | `fix` |
| VF88 | UF88 | 黄金摄取 E2E 被 LiveEmbeddingFixture Mock | `high` | gemini | `valid-by-design` | `[true-deferred]` | `_LiveEmbeddingFixture` `test_single_intake_pipeline.py:173-323` 有意替换 facade；docstring 写明 transport stays local。live GPU soak 已是 NS2-GPU `[true-deferred]`。默认 golden 离线用例不是此 fixture | `defer-with-rationale` |
| VF89 | UF89 | 源码正则扫描伪装行为测试 | `medium` | gemini | `valid(子项 overstated)` | `[true-deferred]` | `test_architecture.py` 是显式 D03 守卫。真缺口是单元 `inspect.getsource` / journal 字符串（`test_d01_review_fixes.py:487-491`；`test_ns4_jsonl_journal.py:10-15`）。全仓禁止 regex guard 从未承诺 | `defer-with-rationale` |
| VF90 | UF90 | pytest 配置宽松 | `high` | muse | `valid` | `[true-deferred]` | `pyproject.toml:37-41` 仅 `-q --tb=short`；无 coverage/conftest。这是工程成熟度，不是生产路径缺陷；0820 未承诺 fail_under | `defer-with-rationale` |
| VF91 | UF91 | local_mock 豁免三大探针 | `high` | muse | `valid` | `[partial-delivery]` | `local_runtime.py:17-25` 关 CW/native_vector/live_inference；多份 e2e 复制。`test_turso_readiness_reports_honest_cw_and_vector:112-127` 只断言两字段相等，可同为 False 仍绿 | `partial-fix` |
| VF92 | UF92 | 检索栅栏无 deactivate→empty e2e | `medium` | muse | `stale-rejected` | `n/a` | 所引空集恒真 `set==set` 不在树中（`test_retrieval_service.py:279` 是 units 去重，`:315-335` 已测 withdrawn/deactivated 空结果）；`test_intake_reactivate.py:153-166` **已有** deactivate→search `[]`。其余 e2e 只断言 succeeded 是普通分层覆盖，不是缺失的 dual-fence oracle | `stale-rejected` |
| VF93 | UF93 | wheel 缺 migration SQL，安装无法启动 | `critical` | gpt | `valid` | `[partial-delivery]` | `pyproject.toml:32-35` 无 package-data；`discover_migrations` glob `*.sql` 空则 503（`migration_runner.py:81-93`）；lifespan 必 `migrate()`（`api/app.py:402-404`）。data/prompts 缺失 README 已披露；未承认的是 `*.sql` | `fix` |
| VF94 | UF94 | /ready 持写锁 + idle 50ms 全量探活 | `medium` | gpt/muse | `valid` | `[true-bug]` | Turso `readiness:100-107` 持 `_write_lock` 跑 verify+CW+vector；CW 探针切 journal_mode（`engine.py:13-40`）；supervisor idle 0.05s（`workflow_supervisor.py:26,68`）约 20Hz。持锁本身对单连接是故意的；缺陷是热路径无缓存的变异探针 | `fix` |
| VF95 | UF95 | schema title 在 adopt/construct 静默丢失 | `medium` | gpt | `valid` | `[partial-delivery]` | schema 要求 title+body（`lsrag.layered_content.v1.json:70-77`）；adopt 规范化 title 后只锚 body（`adopt.py:61-65,216-245`）；`content_full` 无 title 参数（`models.py:168-189`） | `fix` |
| VF96 | UF96 | 双层背压分叉 | `high` | muse | `valid` | `[partial-delivery]` | Facade `capability_limits` 与 `DispatchCaps` 两套计数器（`api/app.py:241-251,294`）；retrieval.search embed 直连 facade（`retrieval_request.py:97-99`）。Settings 数字同源，不是两份配置漂移 | `fix` |
| VF97 | UF97 | browser/OCR/Vision/LLM-clean 已注册未注入 | `high` | gpt/grok/muse | `valid` | `[true-deferred]` | `api/app.py:315-329` 不注入 `browser_fetcher`/`clean_llm`；README 已标未接线。0820 指令视 browser/OCR 为 `[true-deferred]`。http_resource.browser / local_object.image **可选然后 503**，并非全部 DTO 不可达 | `defer-with-rationale` |
| VF98 | UF98 | bootstrap/retention 静默 pass | `medium` | muse | `valid(子项 overstated)` | `[true-bug]` | `api/app.py:405-414` bootstrap `except MkbError: pass` 无 log/metric；retention `:517-523` 同。不使应用「静默可用」：`/ready` 含 `registry_bootstrap`。`engine.py:29-40` 是探针清理，不是 bootstrap | `fix` |
| VF99 | UF99 | Task 幂等指纹含 audit.created_at | `medium` | grok | `valid` | `[true-bug]` | `task_create.py:53-71` `stable_digest(request.model_dump())`；`TaskAudit.created_at` 必填（`api/models.py:62-73,267-286`）。业务 payload 不同仍应 conflict | `fix` |
| VF100 | UF100 | raw exception 未脱敏写入 Process/Outbox | `medium` | gpt | `valid` | `[true-bug]` | `worker.py:54-60` / `runtime_outbox.py:102-104,331-341` `str(exc)[:512]`；`MkbError._safe_text` 存在但未用于这些写入。公共 Task `final_error_message` 多为泛化 message | `fix` |
| VF101 | UF101 | object/schema readiness 假 ready | `high` | gpt | `valid` | `[true-bug]` | `local_store.py:41-49,134-139` identity 存在+W_OK 即 ready，从不 parse；`verify_migrations:147-155` 只比 ledger id/checksum。obs_tables 会抓缺事件表；洞在核心业务表与 identity JSON | `fix` |
| VF102 | UF102 | Team payload_extra 无法清空 | `low` | gpt | `valid` | `[true-bug]` | `TeamPatchRequest.require_change` 把 `not payload_extra` 当无变更（`api/models.py:45-54`）；`teams.py:91-93` `if request.payload_extra else old`。Task patch 已用 `model_fields_set` | `fix` |
| VF103 | UF103 | Task/Team 并发 PK 冲突走 500 | `high` | muse | `valid-edge` | `[true-bug]` | `task_create.py:59-114` / `teams.py:39-58` SELECT-then-INSERT 无 IntegrityError。生产 UoW `BEGIN IMMEDIATE` + `_write_lock` 把默认路径藏住；跨进程/未来 CONCURRENT 会打中。muse「真实部署必现」过称 | `fix` |

### 3.2 簇子表

#### 3.2.1 VF85 假绿测试簇

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `tests/unit/test_turso_driver.py:99` | `assert ... or True` tautology | `valid` | 删除 `or True` |
| `tests/unit/test_ns4_readport_reports.py:8-22` | `__new__` 后断言自造 dict，从不调 `service` | `valid` | 走真实 ObservabilityReadService |
| `tests/unit/test_ns4_diagnostic_sidecar.py:7,23-28` | 未实例化 sidecar；构造局部 MkbError | `valid` | 实例化 sidecar，断言 insert 失败不改 product code |
| `tests/integration/test_ns4_cw_soak.py:53-57` | 串行 soak；`product` 从不传入 insert | `valid` | 并发 ThreadPool + 行数预言 |
| `tests/domain/test_ns4_no_r3_ingest.py:13-14` / `test_r4_launch_lock.py:26-27` | 缺文件 `return` | `valid` | `pytest.fail` 或显式 skip marker |
| `tests/unit/test_ns4_jsonl_journal.py:10-15` | 源码字符串 grep | `valid` | 调 `_journal_row` 行为 |
| `tests/unit/test_object_gc.py:33-63` | 手工插 orphan 后真调 `scan_once` | **非 tautology**（弱预言） | 保留；另补真实 promote-rollback orphan |
| `tests/unit/test_dispatch_mega.py:350-365` | 串行 `claim_next` 仍断言 occupancy | **非 tautology** | 并发重叠改到 VF62 测试 |
| `tests/e2e/test_ns4_fail_path_turso.py:31-68` | 私有 helper + FK off | 弱预言，非 tautology | 走公共 Task/worker 失败 |

#### 3.2.2 VF2 Turso 单写者 / CW 探针

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `turso/port.py:63-77` | 单例 connect；FK PRAGMA `except: pass`；无 busy_timeout/journal_mode | `valid` | `_connect` 设 busy_timeout，校验 FK=1，journal_mode 一次设稳 |
| `turso/port.py:88-91` | UoW `BEGIN IMMEDIATE` + asyncio.Lock | `valid` | 要么 `BEGIN CONCURRENT`+BUSY retry，要么 readiness 报 `concurrent_writes=false` |
| `sqlite_port.py:69-71` | 对照：WAL + busy_timeout=5000 | `valid` | Turso 对齐超时 |
| `engine.py:21-40` | 探针在**业务连接**上切 `journal_mode=mvcc` 再 restore | `valid` | 禁止在 live 业务连接上切 mode |
| `sidecar.py:29-37` | sidecar 也每条设 mvcc/CONCURRENT | `valid` | 并入 VF3 |
| `config.py:24` / README §1.1 | `concurrent_writes_required=True`；声称 CW 已落地 | `valid` | 与真实写路径对齐文案 |
| Gemini R18「破坏生产库 MVCC」 | `connect()` 从不粘滞 MVCC，restore 不是毁掉已配置 MVCC | **overstated** | 不按「毁库」修 |

#### 3.2.3 VF47 检索截断 / native_ann

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `retrieval_rank.py:100-130` | `ORDER BY r.vector_record_uuid LIMIT ?` | `valid`（true-bug） | 超限 fail-closed 或扫全 fenced set |
| `retrieval_request.py:52` | 默认 `candidate_scan_limit=1000` | `valid` | 同上 |
| `config.py:26-27` | `vector_backend=native_ann` 默认 deterministic_exact | 配置面存在 | 未接线前拒绝 native_ann |
| `factory.py:53-58` | TursoPersistence 不传 vector_backend | `valid` | 接 VectorSearchPort 或删除可选项 |
| `api/app.py:258-264` | RetrievalService 无 ANN port | `valid` | 同上 |
| README.md:514 | 已声明名字不是 ANN 证明 | 故「未交付 ANN」过称 | 修截断；文案保持诚实 |

---

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

**A. 按三类归属（问责视图 · ★主视图）**

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | `75` | `VF1 VF3 VF4 VF5 VF7 VF8 VF9 VF10 VF11 VF12 VF13 VF14 VF15 VF16 VF17 VF18 VF19 VF21 VF22 VF24 VF26 VF27 VF28 VF29 VF31 VF34 VF35 VF36 VF38 VF39 VF40 VF42 VF43 VF44 VF45 VF47 VF48 VF49 VF50 VF51 VF52 VF53 VF54 VF55 VF56 VF58 VF59 VF60 VF61 VF63 VF64 VF65 VF67 VF68 VF69 VF70 VF71 VF72 VF75 VF76 VF78 VF80 VF81 VF82 VF83 VF84 VF85 VF87 VF94 VF98 VF99 VF100 VF101 VF102 VF103` | §5.2 本阶段**必修** |
| `[partial-delivery]` | `12` | `VF2 VF30 VF37 VF41 VF46 VF62 VF66 VF73 VF91 VF93 VF95 VF96` | §5.2 补齐；剩余切片 §5.4 |
| `[true-deferred]` | `9` | `VF23 VF74 VF77 VF79 VF86 VF88 VF89 VF90 VF97` | §5.4 承接（带 reopen 触发器） |
| `n/a`（rejected / 无需改）| `7` | `VF6 VF20 VF25 VF32 VF33 VF57 VF92` | 不进三类 |

> 三类合计（不含 `n/a`）= `75+12+9 = 96` = 全部未了结 valid 缺口；`n/a 7` + 96 = 103。与 §1 一致。

**B. 按处置（disposition 视图）**：

- **`fix`（本会话修）**：`VF1 VF2 VF3 VF4 VF5 VF7 VF8 VF9 VF10 VF11 VF12 VF13 VF14 VF15 VF16 VF17 VF18 VF19 VF21 VF22 VF24 VF26 VF27 VF28 VF29 VF31 VF34 VF35 VF36 VF38 VF39 VF40 VF42 VF43 VF44 VF45 VF47 VF48 VF49 VF50 VF51 VF52 VF53 VF54 VF55 VF56 VF58 VF59 VF60 VF61 VF62 VF63 VF64 VF65 VF67 VF68 VF69 VF70 VF71 VF72 VF73 VF75 VF76 VF78 VF80 VF81 VF82 VF83 VF84 VF85 VF87 VF93 VF94 VF95 VF96 VF98 VF99 VF100 VF101 VF102 VF103` = **81 项**
- **`partial-fix`**：`VF30 VF37 VF41 VF46 VF66 VF91` = **6**
- **`defer-with-rationale`**：`VF74 VF77 VF79 VF88 VF89 VF90 VF97` = **7**
- **`deferred-by-owner`**：`VF23 VF86` = **2**
- **`acknowledge`**：`VF20 VF25 VF32 VF33 VF57` = **5**
- **`stale-rejected`**：`VF6 VF92` = **2**

> 81+6+7+2+5+2 = 103，与 §1 一致。

### 4.2 净增承重盲区（peer-vs-peer）

本合成人不是四位 reviewer 之一；下列是**彼此漏报的最高价值独家项**（多方重叠的核心簇不记「净增」）。

- **Grok 独家高价值**：`VF61` 非法 outbox 冻住唯一 supervisor；`VF19` EXHAUSTED 改写终态失败；`VF44`/`VF55`/`VF58` 世代分配与指针非单调；`VF4` rowcount 适配器洞（子项过称）。若只听 Gemini/GPT，runtime 会在毒丸 JSON 上 livelock。
- **GPT 独家高价值**：`VF3` sidecar native abort；`VF93` wheel 缺 SQL（安装无法启动）；`VF16`/`VF17` CLI 泄密与 salvage 证据串台；`VF35`/`VF36` ingest 身份与 artifact digest 分裂。若只听 Grok/Muse，会漏掉包装与诊断路径的进程级 abort。
- **Gemini 独家高价值**：`VF28`/`VF29` 清洁/锚点正确性（critical）；`VF54` 单通道 purge 灭 serving；`VF63` retirement 死循环；`VF12`/`VF13` salvage/OVER_BUDGET 车道。检索/结构内核的「看起来能搜」假象主要靠 Gemini。
- **Muse 独家高价值**：`VF70` claim 每轮只处理一个过期行；`VF5` migration `!r`；`VF80` sqlite 测试后门；`VF84` 无 body size；`VF91` e2e 豁免宪法探针；`VF103` PK 500。治理与测试豁免面主要靠 Muse。
- **四方重叠的承重核**（非净增，但是本轮必修中心）：`VF1` UoW、`VF2` CW 剧场、`VF9` CLI 僵尸、`VF27` vectorize 丢层、`VF47` UUID 截断、`VF85` 假绿测试。

### 4.3 带证据驳回的跨-reviewer 误报

| V# | 误报方 | 误报内容 | 反证（file:line）| 结论 |
|----|--------|----------|-------------------|------|
| VF6 | muse-R21 | pyturso 通常无 `executescript`，首个 CREATE 即 syntax error，生产首次 migrate 永不 ready | 回退枝 `migration_runner.py:65-71`；生产驱动有 `executescript`；`tests/unit/test_turso_driver.py:29-63` 与 `test_d04_write_paths.py:231-247` 已 GREEN | `stale-rejected` |
| VF92 | muse-R32 | 检索双栅栏测试用空集恒真比较；e2e 无 deactivate/delete 后 search==empty | 所引 `set==set` 不在树中（`test_retrieval_service.py:279` 是 units 去重；`:315-335` 已测 withdrawn/deactivated 空结果）；`test_intake_reactivate.py:153-166` 已有 deactivate→search `[]` | `stale-rejected` |

> 其余「子项 overstated」**整条仍成立**，过称句写在对应 VF 行（如 VF2 Gemini R18 MVCC 毁库、VF4 恒 1/-1 fence、VF10 单 supervisor 必重复执行、VF12 降级方向反了、VF31 None 主键、VF47 native ANN 合同、VF49 必崩、VF85 全部测试都是 tautology）。不升格为整条驳回。

---

## 5. 初步修复方案（preliminary fix plan）

### 5.1 修复策略

先封**进程/数据不可恢复洞**（UoW 污染、sidecar abort、CLI 僵尸、outbox 冻 supervisor、GC unlink/rollback、retirement 死循环），再修**serving 正确性**（vectorize 丢层、HTML/锚点、UUID 截断、purge proof、指针 CAS），然后补**车道/证据/安全**（salvage SSOT、lease heartbeat、secret extras、限流 degraded），最后拆**假绿测试与包装**（VF85/VF87/VF93）。`[true-bug]` 本轮全部进 §5.2，禁止改写成 deferred。`[partial-delivery]` 本轮补齐合同；PDF 解析器、默认 stub 配置面、S06 全树、schema 驱动 admission、constitution e2e 作为剩余切片进 §5.4。`[true-deferred]` 只登记 reopen 触发器。每条 code fix 必须先有会红的断言。

不变量：单例连接在 cancel/commit 失败后必须可再 `BEGIN`；publication proof 的 required set 不得在 live 路径被静默缩小；S09 complete-set 不得被单通道 purge 打破；唯一 supervisor 不得被一条坏 outbox 挡住 claim/repair；检索不得按 uuid7 前缀丢掉新知识。

### 5.2 逐项修复计划表

| V# | 计划修法 | 目标文件 | falsifiable 验证（修前应 RED）| migration / owner-gate? | 批次 |
|----|----------|----------|-------------------------------|-------------------------|------|
| VF1 | `transaction()` 捕 `BaseException`；commit 进 try；不确定 commit/cancel 丢弃单例连接；抽 cancellation-safe UoW | `sqlite_port.py` `turso/port.py` | 取消 body 后再 `BEGIN IMMEDIATE` 不得 `cannot start a transaction` | no | 1 |
| VF2 | Turso `_connect` 设 busy_timeout + 校验 FK；journal_mode 一次设稳；UoW 用 CONCURRENT+BUSY retry **或** readiness 诚实报 false；探针勿改业务连接 | `turso/port.py` `engine.py` `sqlite_port.py` `sidecar.py` `config.py` | migrate+ready 后 `concurrent_writes` 真则下一 UoW SQL 不是 IMMEDIATE（或 flags 为 false） | no | 1 |
| VF3 | sidecar 单连接串行队列，禁止每条切 journal_mode；补并发 insert 子进程测 | `sidecar.py` `observability.py` `api/app.py` | 4 线程×20 insert 进程不得 exit 134 | no | 1 |
| VF4 | `TursoUnitOfWork.execute` 归一化 `rowcount>=0` else `changes()`；补 Turso CAS 测 | `turso/port.py` `runtime_core.py` | stale UPDATE `rowcount==0`；匹配 CAS `==1` | no | 2 |
| VF5 | ledger INSERT 参数化，DDL 仍 executescript | `migration_runner.py` | monkeypatch `utc_now` 含引号仍入库；执行 SQL 无 f-string VALUES | no | 2 |
| VF7 | 不改 010 checksum；加 014 把 32-hex 改写连字符 UUID | `migrations/014_*.sql` | seed qwen-vl-2b 升到 014 后 `model_uuid` 匹配 RFC UUID | **migration 014** | 2 |
| VF8 | `utc_now`/`normalize_rfc3339` 同一 timespec；artifacts 改传 Python `utc_now()` | `time.py` `artifacts.py` `task_commands.py` `object_gc.py` | `%f` 写入的 created_at 不得被 us cutoff 字典序排除 | no | 2 |
| VF9 | Timeout/Cancelled/finally：terminate→wait→kill→wait；限制 stdout；补假挂起可执行测 | `claude_cli.py` `test_claude_cli_port.py` | timeout 后 child pid 不在 | no | 1 |
| VF10 | `run_once` 启 heartbeat（lease/3）；heartbeat CAS 失败取消 handler；generate/CLI `safe_replay=false` 或抬 lease | `worker.py` `runtime_materialize.py` `test_workflow_runtime.py` | 两 runtime：lease=1s handler sleep 2s → 败者 fenced，运输取消 | no | 3 |
| VF11 | salvage 新开 durable NI Process 或再 admit；NI 满/CLI 未绑 fail-closed；snapshot 冻 admit-time pool | `generation_construct.py` `config_snapshots.py` `runtime_core.py` | local construct 失败后 salvage 须占 NI occupancy 或闭；snapshot.l2 == command.dispatch_pool | no | 3 |
| VF12 | 去掉 `task_priority=='normal'`；保留 low 不 salvage（若仍是政策） | `generation_construct.py` `test_compression_channel.py` | 显式 local+urgent + VALIDATION_RESPONSE 可 salvage | no | 3 |
| VF13 | transcribe/construct 加入 OVER_BUDGET（或 GENERATE minus embed） | `dispatch.py` `test_dispatch_policy.py` | 16k+ construct + live_inference → NI 而非 local | no | 3 |
| VF14 | `_ns1_prompt_file` 强制 state+role；缺则 `PROMPT_NOT_REGISTERED` | `generation_construct.py` `test_ns1_generation_cli.py` | `state=None` 必须 raise | no | 3 |
| VF15 | adapter 持有一个 `httpx.AsyncClient`，lifespan aclose | `local_vllm.py` `api/app.py` `test_inference_runtime.py` | 两次 embed 不得构造两个 AsyncClient | no | 3 |
| VF16 | 业务正文永远 stdin；argv 不含 prompt；env allowlist 去掉 MKB_*；`internal_token` SecretStr | `claude_cli.py` `api/app.py` `config.py` | 100-byte prompt 不在 `process.args`；子环境无 `MKB_INTERNAL_TOKEN` | no | 3 |
| VF17 | 废 ContextVar；证据绑 process_uuid；成功/失败同 UoW flush；双写 generation+inference | `generation_evidence.py` `generation_live.py` `runtime_outcome.py` `api/app.py` | salvage 成功后再失败第二 Process，不得把第一次失败写成第二 process_uuid | no | 3 |
| VF18 | L4 物化 schema SHA 并在 generate 复核；vLLM 传 json_schema；live_inference 时强制 probe，仅 2xx+精确模型健康 | `config_snapshots.py` `generation_live.py` `local_vllm.py` `api/app.py` `config.py` | freeze 后改 schema digest → generate fail-closed；vLLM 302 → ready.inference_binding false | no | 3 |
| VF19 | EXHAUSTED/BACKPRESSURE 进 `_RECOVERABLE_ERROR_CODES`（或停止改写最后一次 RETRYABLE） | `intake/core.py` `facade.py` `test_d01_review_fixes.py` | 三次 RETRYABLE → ProcessOutcome `retryable_failure` 而非终态 failed | no | 3 |
| VF20 | 本轮不改。fence=enabled-set 是故意 composition allow-list。若 owner 要 winner-only fence，从 `active_inference_bindings()` 构建 | `api/app.py` `registry.py` | N/A（acknowledge）；政策测试：Lightning structured_generate 今日过 fence | no | ack |
| VF21 | CLI 加 ConcurrencyGate（ni_running 或 local+ni）；salvage 必须占门 | `claude_cli.py` `generation_construct.py` `clean_preflight.py` `api/app.py` | max=1 时第二次 `cli.run` → BACKPRESSURE | no | 3 |
| VF22 | sleep 前放 lease 再获取；full jitter；有 recorder 时记录每次 attempt | `facade.py` `local_vllm.py` `test_inference_runtime.py` | cap=2 的 RETRYABLE sleep 期间第三次 generate 不得见满门 | no | 3 |
| VF23 | 本轮不实现计费。billing AP 落地时 fail-closed + 单例 | `billing.py` `api/app.py` | N/A until billing AP：`has_quota(NI)==False` 必须挡住 admit/salvage | **owner** | 5.4 |
| VF24 | 408/425（可选带 Retry-After 的 409）→ RETRYABLE | `local_vllm.py` `test_inference_runtime.py` | FakeTransport 408 → RETRYABLE 而非 VALIDATION_REMOTE | no | 3 |
| VF25 | 文档化 INTERNAL 不可重试。可选：仅映射泄漏的 TimeoutError/HTTPError，不重试任意 Exception | `facade.py` `local_vllm.py` | mock `httpx.TimeoutException` **今日已是 RETRYABLE**（GREEN 证明过称半边） | no | ack |
| VF26 | 非 `text/*` media_type 拒绝 `CLEAN_MEDIA_UNSUPPORTED`；禁止 `errors='replace'` | `claude_cli.py` `clean_preflight.py` `test_ns1_clean_dispatch.py` | PDF header blob 不得返回成功替换文本 | no | 3 |
| VF27 | `len(embeddable)!=len(plan.required)` 则 `VECTORIZE_BUDGET_CONTENT_FULL`，不改写 required_units、不 publish | `vectorize.py` `vector_publish_commit.py` `retrieval/models.py` | g1 original>16000 live vectorize 必须 422，不得 `succeeded==required` 于过滤列表 | no | 4 |
| VF28 | 停止对 HTML 输出 `_SPACE.sub`；复用 `clean_plain_text` | `intake/text.py` | `extract_html_text('<p>A</p><p>B</p>')` 含换行 | no | 4 |
| VF29 | 单调 cursor `find(body, cursor)`；不可消歧则 STRUCTURE_ANCHOR_MISSING | `adopt.py` | `clean='same\\nsame'` 两 g1 → 第二 span 在第一之后，或 kernel fail | no | 4 |
| VF30 | 压缩/加密/纯图保持 fail-closed；去掉 latin-1 回退。本轮不引入完整 PDF 库 | `src/runtime/intake/types.py` `acquisition_ingest.py` `intake/pdf/__init__.py` | UTF-16 无 BOM 不得返回 latin-1 垃圾；Flate 无 Tj 仍 422 | 完整解析器 → 5.4 | 4 |
| VF31 | 随 VF28 修 HTML。可选拒绝字面 `'None'`/`'null'` id。不改已校验路径的 PK 强制 | `realestate.py` `text.py` `chinatax.py` | 无 id → 已 422；REA `'<p>A</p><p>B</p>'` 修后含换行 | no | 4 |
| VF32 | 不改闭集。短文档案用 `{0}`/`{0,1}` json prompt | `adopt.py` | 仅 g0 + declared (0,1,2) 必须继续 mismatch | no | ack |
| VF33 | 不放宽 equality。若 JSON escape 咬人，两侧同用 `normalize_layered_text` 仍要求 body 相等 | `adopt.py` | original 改写仍 CONSTRUCT_KERNEL_ORIGINAL_MUTATION | no | ack |
| VF34 | 在物化 bytes 前套 `acquisition_max_response_bytes`；budget_verdict 带 `{limit, observed}`；local_object 要求 live catalog 行 | `acquisition_ingest.py` `local_store.py` `http_acquisition.py` | 256MiB 以下、8MiB 以上 local_object 不得 `within_configured...` | no | 4 |
| VF35 | 按 (team, source_kind, key) resolve Source，再 CAS Item；同指纹 no-change，变则 append Revision | `acquisition_ingest.py` `acceptance_snapshot.py` `scatter_intake.py` | 同一 inline external_key 两次 → items COUNT=1 | no | 4 |
| VF36 | raw bytes 与 clean text 分对象 promote；artifact (handle,size,digest) 描述那些 bytes | `acceptance_snapshot.py` `intake/core.py` | accept 后 `sha256(read_verified(clean.handle))==clean.content_digest` | no | 4 |
| VF37 | stub 仍可离线，但须派生 summary（prefix/hash）使双通道不等；e2e 断言 `summary!=original`；默认 live 部署不得 silent stub | `claude_cli.py` `config.py` `test_generation_pipeline_contracts.py` | 短 g0 dual units summary!=original | 默认 profile → 5.4 | 4 |
| VF38 | 用 decoder/栈匹配，拒绝多个顶层对象；structured_generate 传冻结 json_schema | `facade.py` `local_vllm.py` | `'see {"a":1} or {"b":2}'` 不得吞成一个对象 | no | 4 |
| VF39 | artifact.transport 写 receipt['transport']；stub json 消费 `package['markdown']` | `generation_construct.py` `claude_cli.py` | live markdown artifact.transport==api_inference | no | 4 |
| VF40 | Item 在 approve 前 pending/reviewing（或跳过 insert）；reject 同 UoW deactivate/delete | `acceptance_snapshot.py` `runtime_gates.py` `lsrag_definition.py` | require_human_review+reject 后 lifecycle 不是 active | no | 4 |
| VF41 | 保持 g0 tunnel。若 S06 树在范围内，按 g1/g2 发 section 节点；否则在 S06 标明 v1 两节点限制 | `adopt.py` | 3 节文档 `len(nodes)==2` 今日 RED（拓扑测） | 全树 → 5.4 | 4 |
| VF42 | 4xx/SPACE_VIOLATION 原样上抛；仅 TRANSPORT/BACKPRESSURE/timeout 包成 VECTORIZE_INFERENCE_FAILED | `vectorize.py` `intake/core.py` | embed 抛 SPACE_VIOLATION → 结果码仍 SPACE_VIOLATION 且不重试 | no | 4 |
| VF43 | 只 embed body、headers 当 facets；或 query 侧同一 header 配方 | `models.py` `vectorize.py` `retrieval_request.py` | metadata_refresh + headers 后搜 body，offline cosine 不得系统性低于 body-only | no | 4 |
| VF44 | 在 vectorize/publish UoW 内 `UPDATE index_generation=index_generation+1 RETURNING`；指针要求 `active < excluded` | `vector_publish_commit.py` | 预留 gen=1，rebuild 到 2，延迟 publish 不得把 active 写回 1 | no | 4 |
| VF45 | 后期 envelope 只带 receipts/handles/digests；body 从 owning artifact verify-on-read | `intake/core.py` `generation_construct.py` `vectorize.py` | vectorize output JSON 无 raw_text/clean_text/markdown_text | no | 4 |
| VF46 | 用注册 schema 驱动 admission，或补 UUID/array/date-time/URI 检查 | `layered_content.py` schema json | `upstream_file_uuids` 为字符串时 Python validator 必须失败 | 全 schema 驱动 → 5.4 | 4 |
| VF47 | 超 scan_limit fail-closed 或扫全 fenced set；native_ann 在无 VectorSearchPort 前拒绝 | `retrieval_rank.py` `retrieval_request.py` `config.py` `factory.py` `api/app.py` | 1001 条 uuid7，高 cosine 在最后 → search(recall_k=20) 命中或显式错误 | no | 4 |
| VF48 | 先按 `-ann_score`；resolved 与 not_needed 同等，traceback 仅 tie-break | `retrieval_pack.py` | 同 unit original 0.99 vs summary 0.10 → 保留 original | no | 4 |
| VF49 | inflate 扫描 `force_channel=None` 并剥 `filters.channel`；优先 g0 summary 再 hydrate original | `retrieval_pack.py` `retrieval_rank.py` | dual-channel + `filters.channel=original` + include_pack → inflation_status 非 missing | no | 4 |
| VF50 | `retrieval_search` 调 `require_active`；候选 SQL 加 `teams.status='active' AND deleted_at IS NULL` | `routes.py` `teams.py` `retrieval_request.py` `retrieval_rank.py` | deactivate 后同 token search → 409 或空+team-inactive | no | 4 |
| VF51 | query embed 跟 namespace Layer A；非 deterministic-hash-v1 必须 live-embed 或 `RETRIEVE_SPACE_LAYER_A_MISMATCH` | `retrieval_request.py` `retrieval_rank.py` `test_retrieval_service.py` | local_vllm ns + live_inference=false → 503/422 而非 200 hash cosine | no | 4 |
| VF52 | namespace 按 (model, version, adapter, dim) 分键，或显式 rebuild 插入新 namespace 并 CAS 指针 | `vector_publish_commit.py` `config_snapshots.py` `intake/core.py` | 64-d 发布后切 live_inference 再 vectorize 须新 namespace/generation serving | no | 4 |
| VF53 | request-scoped cache `(team, generation_artifact_uuid)`；批量 SELECT artifacts | `retrieval_request.py` `retrieval_pack.py` `retrieval_access.py` | 20 个同代 summary hits → 每 generation 一次 verified read | no | 4 |
| VF54 | 拒绝 `channel_filter!='all'`，或部分 purge 后铸新 Proof 并 CAS 指针 | `vector_purge.py` `retrieval/models.py` `vector/models.py` | 只 purge original 后 search 要么命中 summary，要么显式整代 purge，不得空 serving | no | 4 |
| VF55 | active unique 含 `index_generation`（或部分 unique on indexed）；禁止 UPDATE indexed 行 | `001_initial.sql` 或后续 migration `vector_publish_commit.py` | 同 dual-channel 再 upsert 不得把 serving COUNT 打到 0 | **migration** | 4 |
| VF56 | `_pack` 对 root coordinate 去重，每代只附一次 document_root | `retrieval_pack.py` | 两 g1 同 5000 字 root、pack_max=12000 → root 只出现一次 | no | 4 |
| VF57 | 不修 serving。可选 metric 拆 S04 vs S09 丢弃 | `retrieval_rank.py` | 脏 port 批准 withdrawn → search 仍过滤（已 GREEN） | no | ack |
| VF58 | 从 per-item pointer `UPDATE active=active+1` 分配；namespace 计数只作 watermark | `vector_publish_commit.py` `index_rebuild_plan.py` | 与 VF44 同：item A 只 1→2→3 | no | 4 |
| VF59 | payload 用已校验的 `state['dual_channel_artifact_uuid']` | `vectorize.py` | 事件 generation_artifact_uuid 非空且等于 dual_channel | no | 4 |
| VF60 | resolve 要求 `serving_revision_uuid IS NOT NULL AND = latest`；team scope 跳过非 serving | `targets.py` `index_rebuild_plan.py` | 一 serving + 一 reactivated 非 serving → team rebuild 只重建 serving | no | 4 |
| VF61 | 先提交 in_flight CAS 再 parse；JSON/digest 失败新 TX 标 dead；`drain_once` 捕获 dispatch 错误后仍 claim+repair | `runtime_outbox.py` `workflow_supervisor.py` tests | payload=`not-json` 后该行 dead，同 tick 仍能 claim 第二条 Process | no | 1 |
| VF62 | 有界 per-pool worker 集（或 semaphore + 并发 `run_once`），共享 fence/shutdown/heartbeat | `workflow_supervisor.py` `worker.py` `dispatch.py` | 两 ready local Process sleep 2s，drain 2s 内运行时间戳重叠 | no | 1 |
| VF63 | POINTER_UNAVAILABLE 且 item 已 deactivate/delete/missing：软删仍活的 retired gen，CAS intent completed/abandoned | `src/services/index_retirement.py` tests | 100 条 stuck + 1 条健康更晚 due → 第二次 scan 能收集健康 intent | no | 1 |
| VF64 | 两阶段：TX1 再检查 blockers；unlink 在写锁外；TX2 再检查后 proof+tombstone | `src/services/object_gc.py` `local_store.py` ports | tombstone UPDATE 在 unlink 后 raise → 文件可缺但须有 missing-live 信号；claim 不等待 unlink | no | 1 |
| VF65 | `delete_if_unreferenced` 取 `_write_lock`（勿跨 persistence TX 长持） | `local_store.py` `object_gc.py` | 交错 promote(D) 与 delete(D) 无 FileNotFound，tombstone digest 无残字节 | no | 1 |
| VF66 | 域所有 `released_at` CAS；item-delete cleanup consumer；journal promote 或 grace 后对账未编目 CAS（目录不作 SSOT） | `src/services/object_gc.py` `artifacts.py` `lifecycle_apply.py` `intake/core.py` | promote 后 rollback catalog，超 grace `scan_once` 必须能收文件 | 目录 SSOT → 5.4 | 1 |
| VF67 | lookup `tombstoned_at IS NULL`；live 行部分 unique；禁止往 tombstoned uuid 插 live ref | `artifacts.py` snapshots generation_artifacts index_rebuild_commit migrations | GC 后再 catalog 同 bytes → 新 stored_object_uuid，旧 tombstone 无新 live ref | **migration** | 1 |
| VF68 | `validate_and_commit` finally pop；失败/取消也 pop；限制 map 大小 | `artifacts.py` `intake/core.py` `worker.py` | 一成功 Process 后 `_pending` 空；N 次 retry 新 fencing_generation 后仍空 | no | 1 |
| VF69 | `run_once` 包 `except Exception`（不捕 CancelledError），metric+backoff 继续；对齐 retention 循环 | `src/runtime/object_gc.py` `src/runtime/index_retirement.py` `api/app.py` | `scan_once` 抛一次 OperationalError 后 task 仍 running | no | 1 |
| VF70 | 同 UoW 循环 fail-expired（有界）直到没有，再 admit/claim；deadline fail 后不得 return None 除非 claim 集空 | `runtime_core.py` `worker.py` | 3 过期 + 1 活 ready → 一次 claim_next 领到活 Process | no | 1 |
| VF71 | 用 revision backoff 列或 retry_count full jitter | `runtime_core.py` `runtime_outcome.py` `workflow_registry.py` | 两次 retryable_failure 的 next_retry_at 不同且随 retry_count 增长 | no | 2 |
| VF72 | execution cancelling/cancelled 时 gate_decision outbox 直接 done/noop，不 ConflictError | `runtime_gates.py` `runtime_outbox.py` | cancelling + 8 次 dispatch → 行 done 且无新 Process | no | 2 |
| VF73 | 同 UoW 写 `outbox.dead` 并 increment `mkb_outbox_dead_total{kind}`；scrape 填 oldest_age | `runtime_outbox.py` `metrics.py` `events.py` `observability.py` | attempts>=8 → domain_events 有 outbox.dead 且 /metrics 含 mkb_outbox_dead_total | no | 2 |
| VF74 | 推迟：删 token 写入以免双因子错觉，或以后 CAS `claim_token_hash`。多 worker 副本时 reopen | `runtime_core.py` `runtime_outcome.py` `worker.py` | 错误 token + 正确 generation 今日仍成功 — 不把该 RED 当现生产 bug | 多副本 | 5.4 |
| VF75 | `MKB_TRUSTED_PROXY_CIDRS`；仅当 peer ∈ 集合才解析 XFF；默认空 | `security.py` `dependencies.py` `config.py` `test_security_boundary.py` | ASGI 10.0.0.1 + XFF 8.8.8.8 对 /metrics /internal 403，直到 CIDR 配置 | no | 5 |
| VF76 | 容量击中并入 overflow 身份并限流该桶；不为预期 overflow 设 degraded；成功 `_allow` 后复位 | `security.py` `dependencies.py` `test_security_boundary.py` | max_buckets=2 后第三 IP 不得使后续 `check_ip` 永远 allowed | no | 5 |
| VF77 | 除非开始存 HTML artifact，否则 defer。若保留：href/src 仅 http/https/mailto/相对 | `intake/web/sanitize.py` | `javascript:` href 今日仍在；extract_html_text 已只得文本 `x` | HTML 存储 | 5.4 |
| VF78 | 所有公共 PayloadExtra 用 `_REDACT_KEY`；拒绝 presigned URL；GET 脱敏 | `models.py` `api/models.py` `teams.py` `task_commands.py` `task_views.py` `config_snapshots.py` | TeamCreate `{apiKey:sk-live}` 与 TaskPatch `{token:x}` → 422 且库无 secret | no | 5 |
| VF79 | 边缘硬化时 `docs_url=None` 或挂 `require_operator_token`。公网/0.0.0.0 bind 时 reopen | `api/app.py` README | 未认证 GET /openapi.json 今日 200 | 公网 bind | 5.4 |
| VF80 | sqlite 仅当 PYTEST_CURRENT_TEST **且**（sys.modules 有 pytest 或 `MKB_ALLOW_SQLITE=1`） | `factory.py` `test_ns4_factory_sqlite_test_only.py` | 生产环境仅 PYTEST_CURRENT_TEST+backend=sqlite 必须 raise | no | 5 |
| VF81 | 升级 FastAPI 到依赖 starlette>=1.0.1；TrustedHostMiddleware；CI pip-audit。禁止在 0.115.12 下强钉 1.0.1 | `pyproject.toml` `uv.lock` `api/app.py` | `starlette.__version__ >= 1.0.1` 且 GHSA 不再匹配 | dep bump | 5 |
| VF82 | 若 `address.ipv4_mapped` 则对 v4 递归 `_restricted`/`is_internal_ip` | `security.py` `test_security_boundary.py` | resolver 返回 `::ffff:127.0.0.1` + allow_literal_ip 必须 SEC_EGRESS_DENIED | no | 5 |
| VF83 | decide() 当 reservation：写成功才 commit sampler；写失败不推进桶；invalid-token 在 store 宕机时保持 SEC_AUDIT_WRITE_FAIL | `dependencies.py` `security.py` `test_security_boundary.py` | BrokenAudit limit=1：第 2 次 invalid token 仍 503 而非无审计 401 | no | 5 |
| VF84 | ASGI middleware 在缓冲前按 Settings cap 413；限制 ChinaTax 自由字符串；可选 records 总字节 | `api/app.py` `config.py` `api/models.py` `chinatax.py` | Content-Length>cap → 413 before JSON parse | no | 5 |
| VF85 | 删 tautology；驱动真实 SUT；缺文件 fail；并发 soak 带行数预言 | 见 §3.2.1 | 删 sidecar.insert / ReadPort helper 后对应测试必须 RED | no | 6 |
| VF86 | 后继 harness charter：关 app 后用 TursoPersistence/ReadPort 检查；条件驱动 drain 替代 5s poll。NS1-V11 冻结 | e2e + `local_runtime.py` deferred ledger | 今日 pytest 这些 e2e 期望 disk I/O / 仍 running | **owner freeze** | 5.4 |
| VF87 | 本轮 `ruff check --fix` 再手修 B904/B017/F841。全绿 pytest 堵在 VF86，不得声称 441/441 | README `pyproject.toml` 所列 ruff 位点 | `uv run ruff check .` 必须先 RED（9 errors） | pytest 全绿依赖 VF86 | 6 |
| VF88 | 保留 fixture 作离线 binding golden。owner 开 live 窗口时加标记测打 LocalVllmAdapter，不换 facade 对象 | `test_single_intake_pipeline.py` | 今日 live_profile 在替换 `_inference` 后仍绿 | live GPU | 5.4 |
| VF89 | 留 `test_architecture.py`。最差单元 grep（journal、native-vector docstring、d01/d02 getsource）改成调用 | 所列 unit 文件 | 删 `_journal_row` 后新测试必须 RED | 全仓 grep 禁令未承诺 | 5.4 |
| VF90 | 后期工程：`--strict-markers --strict-config`；conftest 清 ContextVar。coverage fail_under 仅在 tautology 消失后 | `pyproject.toml` `tests/` | `pytest-cov` 未装 | 工程 pass | 5.4 |
| VF91 | 保留 local_mock 给语义金样。改 unit 断言 CW **True** 而非相等。加一份必跑 e2e `concurrent_writes_required=True` 且 ready 字段 True 或 error | `local_runtime.py` e2e `test_turso_driver.py` | 两 CW 字段同为 False 今日 GREEN | 真机 CW e2e → 5.4 | 6 |
| VF92 | 不修。deactivate→empty e2e 与 dual-fence unit 已存在；所引 tautology 不在树中 | `test_intake_reactivate.py` 已是 oracle | deactivate→empty 已存在（harness sqlite3 另计） | no | rejected |
| VF93 | `[tool.setuptools.package-data]` 含 `src/persistence/migrations/*.sql`；CI：uv build → 干净 venv migrate smoke | `pyproject.toml` `config.py` `migration_runner.py` `api/app.py` | `unzip -l dist/*.whl` 今日无 `migrations/*.sql` | packaging | 6 |
| VF94 | HealthAggregator 短 TTL + in-flight coalesce；CW/vector 探针旁路连接或 boot/interval，claim 不切 journal_mode | `turso/port.py` `sqlite_port.py` `engine.py` `health.py` `api/app.py` `workflow_supervisor.py` | idle supervisor 1s 不得 ~20 次 `PRAGMA journal_mode=mvcc` | no | 2 |
| VF95 | 把 title 投进 ChannelRecord/content_full/dual payload **或** 从 schema/validator/prompt 删除该字段 | adopt/construct/payloads/models + schema | title='Article 1' 且 distinct body → dual/content_full 含 Article 1（或 schema 不再接受 title） | no | 4 |
| VF96 | 同一 DispatchCaps 注入 WorkflowRuntime 与 Facade；retrieval embed 计入 embed pool；structured+text 不得超过 local+ni running | `api/app.py` `facade.py` `dispatch.py` `retrieval_request.py` | 占满 facade embed=8 必须让 DispatchCaps.embed_running 也满 | no | 3 |
| VF97 | 保持 deferred。reopen：注入 BrowserFetcher/OCR/Vision + readiness 组件；额外 LLM/Vision keys 可先从 BUILTIN map 拿掉以免误读 | `api/app.py` intake workflows snapshots README | stock create_app + acquisition_mode=browser → 503 ACQUISITION_BROWSER...（保持 RED 直到注入） | capability charter | 5.4 |
| VF98 | bootstrap MkbError increment `mkb_registry_bootstrap_fail_total` / workflow 对应 + diagnostic 再 pass；retention 同样 `mkb_retention_fail_total` | `api/app.py` `registry.py` `workflow_registry.py` | 强制 PROMPT_NOT_REGISTERED → /ready 仍 503 **且** 计数器增加 | no | 2 |
| VF99 | 指纹只哈希 durable command 字段，排除 audit.created_at/reviewed_at/expires_at | `task_create.py` `api/models.py` | 仅 created_at +1s 的重放 → 200 replay 同 creation_fingerprint | no | 2 |
| VF100 | 只持久化稳定 error_code + 预声明安全消息；`str(exc)` 经 `_safe_text` | `worker.py` `runtime_outcome.py` `runtime_outbox.py` `errors.py` | handler `token=sk-live-abc /var/mkb/db.sqlite` → error_message 无 token/绝对路径 | no | 2 |
| VF101 | parse identity.json 为含 UUID 的对象；verify_migrations/probe `sqlite_master` 必选表（含 mkb_tasks）；OSError/JSON fail-closed | `local_store.py` `migration_runner.py` `api/app.py` `health.py` | DROP TABLE mkb_tasks 后 schema_migration 必须 false；identity='not-json' storage ready false | no | 2 |
| VF102 | 对齐 Task：`require_change` 用 `'payload_extra' in model_fields_set`；字段被 set 时包括 `{}` 都写入 | `api/models.py` `teams.py` | PATCH `{payload_extra:{}}` 后存储 extras 为 `{}` | no | 2 |
| VF103 | INSERT 周围捕 IntegrityError / pyturso unique abort，重读行 → ConflictError 或 replay | `task_create.py` `teams.py` `api/app.py` | 无进程写锁时并发同 task_uuid → 409 而非 500 | no | 2 |
| VF6 | 不修生产。可选：缺 executescript 时拆 statement 而非 execute(整段) | `migration_runner.py` | 既有 Turso migrate 测保持 GREEN | no | rejected |

### 5.3 批次 / 依赖

- **批次 1（运行时安全 / 不可恢复 IO）**：`VF1 VF2 VF3 VF9 VF61 VF62 VF63 VF64 VF65 VF66 VF67 VF68 VF69 VF70` — 不先修这些，后续正确性测试会在坏连接/冻 supervisor/GC 丢字节上抖动。
- **批次 2（持久化诚实与平台卫生）**：`VF4 VF5 VF7 VF8 VF71 VF72 VF73 VF94 VF98 VF99 VF100 VF101 VF102 VF103` — 依赖批次 1 的 UoW。
- **批次 3（推理 / 车道 / 证据）**：`VF10–VF19 VF21 VF22 VF24 VF26 VF96` — 依赖可取消的 CLI 与可滚动的 UoW。
- **批次 4（摄取 / 结构 / 检索 serving）**：`VF27–VF31 VF34–VF56 VF58–VF60 VF95` — 依赖批次 1–2 的 CAS/时间戳。
- **批次 5（安全边界）**：`VF75 VF76 VF78 VF80 VF81 VF82 VF83 VF84`。
- **批次 6（测试与包装）**：`VF85 VF87 VF91 VF93` — 假绿不拆则批次 1–5 的回归不可信；wheel SQL 不打则安装路径无法证明。
- **ack / 5.4**：`VF20 VF23 VF25 VF32 VF33 VF57 VF74 VF77 VF79 VF86 VF88–VF90 VF97` 不进本轮代码批次。`VF6 VF92` 为 stale-rejected，见 §5.2 rejected。

### 5.4 承接登记（`[true-deferred]` + `[partial-delivery]` 剩余切片）

> **`[true-bug]` 不得出现在此表。**

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接位置 |
|----|--------------|------|----------|----------------|----------|
| VF23 | `[true-deferred]` | `deferred-by-owner` | 本阶段只承诺 always-permit BillingPort（README K10 / NS2-O1） | billing AP 立项；`has_quota(NI)==false` 必须挡住 admit/salvage | `docs/closure/new-start/deferred-items-ledger.md` NS2-O1 |
| VF74 | `[true-deferred]` | `defer-with-rationale` | 现 fence 是 fencing_generation；token 是未完成第二因子，单 worker 拓扑足够 | 多 worker 副本 / 跨进程 claim | S03 hardening |
| VF77 | `[true-deferred]` | `defer-with-rationale` | sanitized HTML 不持久、不服务浏览器；D08 未要求 scheme 政策 | 开始存储/返回 HTML artifact | intake/web sanitize |
| VF79 | `[true-deferred]` | `defer-with-rationale` | README 已承认内网 docs 残留；默认 bind loopback | 公网或 `0.0.0.0` bind / 浏览器客户端 | README K9 / 边缘硬化 |
| VF86 | `[true-deferred]` | `deferred-by-owner` | owner 冻结本阶段测试引擎（NS1-V11） | harness charter：Turso port 检查 + 条件 drain | `deferred-items-ledger.md` NS1-V11 |
| VF88 | `[true-deferred]` | `defer-with-rationale` | live_profile fixture 是离线 binding golden；真 GPU soak 已承认 | owner 开 live-inference 窗口 | NS2-GPU |
| VF89 | `[true-deferred]` | `defer-with-rationale` | architecture 源扫描是 D03 守卫；全仓禁 grep 从未承诺 | 重写最差 unit grep 时 | 工程债 |
| VF90 | `[true-deferred]` | `defer-with-rationale` | coverage/strict pytest 非 0820 charter；在 tautology 消失前 fail_under 是剧场 | VF85 清完后工程 pass | `pyproject.toml` |
| VF97 | `[true-deferred]` | `defer-with-rationale` | README 已标 browser/OCR/Vision 未接线；0820 指令视为 true-deferred | 注入 BrowserFetcher/OCR/Vision + readiness 组件 | README 未接线合同 |
| VF30.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮去掉 latin-1 并保持压缩 PDF fail-closed；不引入完整 PDF 库 | 需要真实 text-layer 解析时 | PDF charter |
| VF37.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮让 stub 通道可区分；默认 live 部署切出 stub 需显式 offline profile 旗标 | 生产默认不得 silent stub | config / deploy profile |
| VF41.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 保持 g0 tunnel 与 v1 两节点树；完整 parented section 树若在 S06 范围再做 | S06 拓扑被列为交付 | S06 domain-truth |
| VF46.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮补 UUID/array/date-time/URI 差；全程 jsonschema 驱动可后置 | 注册 schema 成为唯一 admission SSOT | S06/S07 schema |
| VF66.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮做 released_at + item-delete consumer + promote journal；目录当 SSOT / reservation table 已显式 defer（T-O-120） | 授权磁盘 SSOT 扫描 | S13 T-O-120 |
| VF91.r | `[partial-delivery]` 剩余切片 | `defer-with-rationale` | 本轮修 unit「两字段皆 False 仍绿」；必跑 constitution e2e（CW+native_vector True）依赖真机/稳定 Turso | CI 有稳定 Turso MVCC | NS4 constitution e2e |

---

## 6. 处置执行回填（fixes 落地后 · append-only）

> Phase-4 前占位。本节只允许后续 append，**不改写 §0–§5**。本 Phase-3 工作流未执行修复。

### 6.1 逐项处置结果表

（空 · 待 Phase-4 append）

### 6.2 Blocker / Follow-up 状态汇总

（空 · 待 Phase-4 append）

### 6.3 变更文件清单

（空 · 待 Phase-4 append）

### 6.4 验证结果

（空 · 待 Phase-4 append）

### 6.5 残留与下一轮 entry

（空 · 待 Phase-4 append）

---

## 7. AGENT 评审绩效（0820 第 1 轮）

> 评价对象: Gemini / GPT / Grok / Muse Spark on MKB 0820 first-round
> 评价人: Grok (0820-review-ledger workflow)
> 评价时间: 2026-08-20
>
> 本节消费 §3/§4 已复核台账，不重开 VF 判定。文档状态仍为 `triaged`（§6 未回填，不写 close-type）。

### 0. 评价结论

- **一句话评价**：四审 154 条全部落入台账；GPT 零误报、证据链最完整且独家钉死 sidecar native abort 与 wheel 缺 SQL，是本轮最佳主审。Gemini 覆盖面与独特 critical 最强但把两处 by-design fail-closed 写成缺陷；Grok 证据纪律最好并钉死 outbox 毒丸；Muse 独家面广但贡献了本轮仅有的两条 stale。
- **最佳AGENT**：GPT（总分 8.5；§4.3 零驳回；独家两个 14-blocker：VF3 / VF93）
- **最高价值 Finding**：VF3 sidecar 并发触发 native abort（`gpt-R2`；生产默认启用，4 线程稳定 pyturso panic exit 134）

**评分校准（相对 §3/§4，独立核对）**：

- 六维均值与所给总分一致：Gemini `(7.5+6.5+8.0+7.5+8.5+6.0)/6=7.3`；GPT `(9.0+9.0+8.0+8.0+9.0+8.0)/6=8.5`；Grok `(8.7+8.0+8.4+8.8+7.3+7.2)/6=8.07→8.1`；Muse `(8.5+6.8+8.3+8.2+7.3+6.5)/6=7.6`。数字未改。
- 未发现「stale-rejected 被标 true-positive」类矛盾。`muse-R21=VF6`、`muse-R32=VF92` 均标 `stale`，与 §4.3 一致。
- `gemini-R25/R26`（VF32/VF33）与 `muse-R26`（VF25）标 `false-positive`：ledger 是 `valid-by-design` / `acknowledge`（现象存在，缺陷主张不成立）。保留 `false-positive` 作为评审判定，不把 VF 改成 `INVALID`。
- `gemini-R7=VF29` 因 `gpt-R30` 同 UF，不标 `missed-by-others`，与 §2.2 一致。
- 14-blocker 覆盖（独立点名）：GPT 10/14（漏 VF28/VF54/VF61/VF63）；Gemini 9/14（漏 VF3/VF10/VF47/VF61/VF93）；Grok 7/14（漏 VF1/VF3/VF28/VF29/VF54/VF63/VF93）；Muse 5/14（漏 VF1/VF3/VF27/VF28/VF29/VF54/VF61/VF63/VF93）。覆盖分与此同向。

### 1. Findings 质量清点

事后判定小计（154 条原始 finding 全列；不丢任一方）：

| AGENT | 条数 | true-positive | missed-by-others | partial | false-positive | stale |
|-------|------|---------------|------------------|---------|----------------|-------|
| Gemini | 45 | 22 | 12 | 9 | 2 | 0 |
| GPT | 45 | 24 | 21 | 0 | 0 | 0 |
| Grok | 28 | 15 | 11 | 2 | 0 | 0 |
| Muse | 36 | 14 | 14 | 5 | 1 | 2 |

| AGENT | 问题编号 | 原始严重程度 | 事后判定 | Finding 质量 | 分析与说明 |
|---------|----------|--------------|----------|--------------|------------|
| Gemini | `R1→VF9` | `critical` | `true-positive` | `good` | 超时不 kill/wait 属实且四方重叠；主机级 DoS 过称（supervisor 串行 UF62） |
| Gemini | `R2→VF1` | `critical` | `true-positive` | `excellent` | `commit()` 在 else、失败不 rollback 分析精确；与 gpt 共享，Gemini 抓住 commit 路径 |
| Gemini | `R3→VF63` | `critical` | `missed-by-others` | `excellent` | 独家 critical：POINTER_UNAVAILABLE 不更新 open intent，LIMIT 100 队头阻塞全库 GC |
| Gemini | `R4→VF54` | `critical` | `missed-by-others` | `excellent` | 独家 critical：单通道 purge 打破 Proof COUNT 谓词，该世代检索全灭 |
| Gemini | `R5→VF28` | `critical` | `missed-by-others` | `excellent` | 独家 critical 且 Gemini 本评最高价值：`_SPACE.sub` 抹平已插入换行；修法可执行 |
| Gemini | `R6→VF27` | `critical` | `true-positive` | `excellent` | 超 16k 过滤后重写 `required_units=succeeded_units` 并签完整 proof；与 gpt/grok 重叠 |
| Gemini | `R7→VF29` | `critical` | `true-positive` | `excellent` | `clean.find` 从 0 错锚属实；gpt-R30 同 UF，故非独家 |
| Gemini | `R8→VF48` | `high` | `true-positive` | `good` | summary-first 优先于 ANN 分属实；不丢 original 文本，丢的是 hit 身份 |
| Gemini | `R9→VF49` | `high` | `partial` | `mixed` | inflate 继承 channel filter 属实且独家，但标 missing 而非必崩 |
| Gemini | `R10→VF15` | `high` | `missed-by-others` | `good` | 独家：每请求新建 AsyncClient；写作为标题级，缺展开行号 |
| Gemini | `R11→VF13` | `high` | `missed-by-others` | `good` | 独家真洞：OVER_BUDGET 只有 structurize/clean.*_llm，漏 transcribe/construct |
| Gemini | `R12→VF12` | `high` | `partial` | `mixed` | 仅 normal 可 salvage 属实，但「urgent/high 无法降级到本地」方向写反；ledger high→medium |
| Gemini | `R13→VF14` | `high` | `partial` | `mixed` | `state=None` 读盘路径存在，生产 structurize/transcribe 传 state；当生产安全绕过过称 |
| Gemini | `R14→VF65` | `high` | `missed-by-others` | `good` | 独家：`delete_if_unreferenced` 不在 `_write_lock` 内，与 promote 竞态 |
| Gemini | `R15→VF64` | `high` | `true-positive` | `good` | 事务内 unlink 回滚不可恢复属实；与 muse 共享 |
| Gemini | `R16→VF66` | `high` | `true-positive` | `mixed` | 无磁盘反向扫描/生产不 release 属实；「GC 完全未实现」过强（partial-delivery） |
| Gemini | `R17→VF2` | `high` | `true-positive` | `good` | 无 busy_timeout + 单连接 IMMEDIATE 属实；四方重叠簇的有效子项 |
| Gemini | `R18→VF2` | `high` | `partial` | `mixed` | 探针在业务连接切 journal_mode 属实；「破坏生产库 MVCC」过称（connect 不粘滞） |
| Gemini | `R19→VF75` | `high` | `true-positive` | `good` | 只读 `client.host` 属实；bypass 条件于 0.0.0.0+代理（valid-conditional） |
| Gemini | `R20→VF76` | `high` | `true-positive` | `good` | 桶超限永久 degraded fail-open 属实；IP-before-auth 是 S16 设计 |
| Gemini | `R21→VF68` | `high` | `true-positive` | `good` | `_pending` 成功/失败都不 pop 属实；与 gpt 共享 |
| Gemini | `R22→VF77` | `high` | `partial` | `mixed` | href/src 原样复制属实，但生产立刻剥属性；非存储型 XSS，high→low |
| Gemini | `R23→VF30` | `high` | `missed-by-others` | `mixed` | 独家 raw-bytes 正则扫描属实；压缩 PDF 是诚实 422 而非静默乱码 |
| Gemini | `R24→VF31` | `high` | `partial` | `mixed` | REA HTML 压平并入 VF28；缺 ID 写成 None 主键不可达（id/listingId 必填） |
| Gemini | `R25→VF32` | `high` | `false-positive` | `weak` | GRANULARITY_SET_MISMATCH 是 S06 闭集不变量，自适应降级从未承诺；ledger `acknowledge` |
| Gemini | `R26→VF33` | `high` | `false-positive` | `weak` | Original 逐字失败是 S07 fail-closed，单测锁死；发明缺陷；ledger `acknowledge` |
| Gemini | `R27→VF85` | `high` | `true-positive` | `good` | `assert ... or True` 恒真属实；假绿簇与 gpt/grok/muse 重叠 |
| Gemini | `R28→VF85` | `critical` | `true-positive` | `excellent` | `__new__` 后断言自造 dict、从不调 service；簇内写得最清楚的 tautology |
| Gemini | `R29→VF85` | `critical` | `true-positive` | `excellent` | 只构造局部 MkbError，未实例化 sidecar |
| Gemini | `R30→VF85` | `critical` | `true-positive` | `excellent` | 8 次串行 soak 且断言未传入的 product；注释自承并发会崩 |
| Gemini | `R31→VF85` | `high` | `true-positive` | `good` | 缺文件直接 return 假绿属实 |
| Gemini | `R32→VF86` | `high` | `true-positive` | `good` | e2e `sqlite3.connect` Turso 文件属实；owner 冻结 NS1-V11，非误报 |
| Gemini | `R33→VF88` | `high` | `partial` | `weak` | fixture 确替换 facade，但是有意的本地 golden；live GPU 已 true-deferred |
| Gemini | `R34→VF85` | `medium` | `true-positive` | `good` | `test_ns4_sink_required` 无 assert 属假绿簇真子项 |
| Gemini | `R35→VF89` | `medium` | `partial` | `mixed` | architecture 正则是 D03 守卫；真缺口是部分 unit `inspect.getsource` |
| Gemini | `R36→VF56` | `medium` | `missed-by-others` | `good` | 独家：同代多 hit 重复填充同一 document_root，无去重 |
| Gemini | `R37→VF60` | `medium` | `true-positive` | `mixed` | team rebuild 冻入非 serving 行属实；级别低估（ledger high），与 grok 共享 |
| Gemini | `R38→VF71` | `medium` | `missed-by-others` | `mixed` | 独家：固定 1s 且 registry jitter 未用；单 worker「惊群雪崩」过称 |
| Gemini | `R39→VF72` | `medium` | `partial` | `mixed` | cancelled 会 ACK；恶性 8 次重试发生在 cancelling 非终态路径，两条捏在一起 |
| Gemini | `R40→VF73` | `medium` | `missed-by-others` | `good` | 独家：dead 不写 outbox.dead 事件/指标；operator GET 仍可见（partial-delivery） |
| Gemini | `R41→VF7` | `medium` | `missed-by-others` | `good` | 独家 valid-edge：010 `hex(randomblob)` 无连字符；仅 upgrade 含 qwen-vl-2b 触发 |
| Gemini | `R42→VF8` | `medium` | `missed-by-others` | `mixed` | 独家 us vs ms 分裂属实；claim 路径两侧已是 Python us，「通用 SQL 偏差」过称 |
| Gemini | `R43→VF38` | `medium` | `true-positive` | `mixed` | 首{到末}贪婪切片属实；不 crash 而是 VALIDATION_STRUCTURED；空 g0 非切片洞 |
| Gemini | `R44→VF22` | `medium` | `true-positive` | `good` | 持 lease sleep 无 jitter 属实；级联 503 需 generate+embed 重叠 |
| Gemini | `R45→VF87` | `medium` | `true-positive` | `mixed` | ruff 9 errors 属实；pytest 8–10 红主要是 UF86 harness 噪声 |
| GPT | `R1→VF1` | `critical` | `true-positive` | `excellent` | 与 gemini 重叠的 UoW cancel/commit 洞；CancelledError 是 BaseException + else-commit，临时库复现 in_transaction 污染 |
| GPT | `R2→VF3` | `critical` | `missed-by-others` | `excellent` | 本轮最高价值独家：sidecar 每条日志新连接+MVCC+BEGIN CONCURRENT，4 线程稳定 pyturso panic exit 134；生产默认启用 |
| GPT | `R3→VF93` | `critical` | `missed-by-others` | `excellent` | 独家交付 blocker：干净 wheel 无 `*.sql`/prompts；属 partial-delivery 但安装无法 migrate 属实。未承认的是 SQL |
| GPT | `R4→VF2` | `high` | `true-positive` | `good` | 四方重叠的 CW 剧场；单连接+IMMEDIATE+多实例锁失败属实。严重级低估为 high（VF=critical） |
| GPT | `R5→VF10` | `high` | `true-positive` | `excellent` | 30s lease 无生产 heartbeat，180/900s 推理可被 reclaim。valid-conditional：单 supervisor 运行中不自抢。标 high 低于 VF critical |
| GPT | `R6→VF62` | `high` | `missed-by-others` | `excellent` | 独家：唯一 supervisor 串行 `await run_once`，2/2/8 只是 admit 上限。谎的是 running 并发 |
| GPT | `R7→VF9` | `high` | `true-positive` | `good` | 四方重叠的 CLI 超时不 kill；兼称 stdout 无上限。事实成立，严重级低估为 high（VF=critical） |
| GPT | `R8→VF11` | `high` | `true-positive` | `good` | 与 grok 重叠：同 Process 内 salvage 切 Claude，绕开 choose_pool/NI/quota |
| GPT | `R9→VF16` | `high` | `missed-by-others` | `excellent` | 独家：&lt;16KiB 正文进 argv、`env=None` 继承父进程、Settings token 可 repr/dump；对上 README stdin-only 声称 |
| GPT | `R10→VF17` | `high` | `missed-by-others` | `excellent` | 独家：salvage 失败证据放 supervisor ContextVar，flush 用当时 Process 身份，可串 Team |
| GPT | `R11→VF18` | `high` | `missed-by-others` | `excellent` | 独家：snapshot 无 schema bytes、vLLM 只发 json_object、probe 默认关且 3xx 算健康 |
| GPT | `R12→VF66` | `high` | `true-positive` | `good` | 与 gemini 重叠：生产无 released_at、FS-only orphan 不可见。手工 orphan 路径能扫，不宜写成 GC 完全不存在 |
| GPT | `R13→VF67` | `high` | `missed-by-others` | `excellent` | 独家：lookup 不滤 tombstoned_at，同 digest 新 live ref 挂旧 uuid；有真实复现 |
| GPT | `R14→VF68` | `high` | `true-positive` | `good` | 与 gemini 重叠：`_pending` 成功/失败/取消均不 pop，进程级泄漏 |
| GPT | `R15→VF34` | `high` | `missed-by-others` | `good` | 独家：local/registered/browser 无预算却盖 within_budget。子项过称是「全部无界」——HTTP static 实际有 cap |
| GPT | `R16→VF78` | `high` | `true-positive` | `excellent` | 与 muse 重叠：extras/signed URL/百万字符/NaN→null。GPT 贡献的是 secret URL 与总量 |
| GPT | `R17→VF101` | `high` | `missed-by-others` | `excellent` | 独家：identity 非 JSON 仍 ready；DROP TABLE mkb_tasks 后 schema readiness 仍 true |
| GPT | `R18→VF26` | `high` | `missed-by-others` | `good` | 独家：丢 media_type + UTF-8 `errors=replace` 把 blob 当文本，NI LLM-clean 走此包装 |
| GPT | `R19→VF22` | `medium` | `true-positive` | `good` | 与 gemini/muse 重叠：同一 lease 内 sleep 重试、无 jitter/idempotency |
| GPT | `R20→VF85` | `critical` | `true-positive` | `mixed` | 四方假绿簇，or True/sidecar 未调用/串行 soak 成立；把 object_gc 手工 orphan 写成 tautology 过称（ledger：GC 不是永真） |
| GPT | `R21→VF85` | `high` | `true-positive` | `mixed` | ReadPort 自造 dict 成立；fail-path 私有 helper 与 live fixture 被 ledger 标为非 tautology |
| GPT | `R22→VF86` | `medium` | `true-positive` | `good` | 与 gemini/grok 重叠：sqlite3 打开 Turso 文件 + 5s 轮询。valid-owner-gated。标 medium 低于 VF high |
| GPT | `R23→VF87` | `high` | `true-positive` | `mixed` | pytest/ruff 不绿属实；8–10 failed 主要是 UF86 harness 噪声，GPT 已声明并行负载，但仍当 blocker |
| GPT | `R24→VF81` | `medium` | `missed-by-others` | `good` | 独家钉死 starlette 0.46.2 ∈ GHSA-86qp-5c8j-p5mr。自限「非 auth、非本轮 blocker」，与子项 overstated 一致 |
| GPT | `R25→VF94` | `medium` | `true-positive` | `good` | 与 muse 重叠：idle ~50ms 全量 HealthAggregator + journal_mode 切换 |
| GPT | `R26→VF47` | `critical` | `true-positive` | `good` | 与 grok/muse 重叠的召回截断，严重级正确。把 native_ann 读成生产 ANN 合同过称：README/config 已标 scan profile |
| GPT | `R27→VF51` | `high` | `true-positive` | `good` | 与 grok 重叠：offline 仅看进程开关按维数 hash，混入 live 空间 |
| GPT | `R28→VF27` | `high` | `true-positive` | `good` | 与 gemini/grok 重叠：滤掉 required units 后按缩水集合签 full-valid。标 high 低于 VF critical |
| GPT | `R29→VF35` | `high` | `missed-by-others` | `excellent` | 独家：重复 ingest 总 uuid7 新 Source/Item，external/connector/member key 不 resolve |
| GPT | `R30→VF29` | `high` | `true-positive` | `good` | 与 gemini 重叠：`find()` 从 0 搜索。标 high 低于 VF critical |
| GPT | `R31→VF36` | `high` | `missed-by-others` | `excellent` | 独家：raw/clean 共享 envelope handle/size 却写不同 semantic digest |
| GPT | `R32→VF50` | `high` | `true-positive` | `excellent` | 与 grok 重叠：Team deactivate/delete 后 retrieval 不 require_active。非跨租户泄漏 |
| GPT | `R33→VF53` | `high` | `true-positive` | `mixed` | 与 muse 重叠的 N+1 hydration 成立；把 10k scatter 写成 S10 I/O 巨事务过称 |
| GPT | `R34→VF48` | `medium` | `true-positive` | `good` | 与 gemini 重叠：summary-first 在 ANN score 之前。标 medium 低于 VF high |
| GPT | `R35→VF58` | `high` | `missed-by-others` | `good` | 独家：普通 publish 用 namespace.index_generation+1，rebuild 用 pointer.active+1。伤害是 per-item 非单调 |
| GPT | `R36→VF69` | `medium` | `true-positive` | `good` | 与 muse 重叠：GC/retirement `run_forever` 一次异常永停。标 medium 低于 VF high |
| GPT | `R37→VF45` | `medium` | `missed-by-others` | `good` | 独家：每 stage envelope 复制完整累计 state，所谓 body-free vector outcome 仍继承 raw/clean |
| GPT | `R38→VF46` | `medium` | `missed-by-others` | `good` | 独家：Python layered validator ≠ 注册 JSON Schema。partial-delivery |
| GPT | `R39→VF95` | `medium` | `missed-by-others` | `good` | 独家：schema 允许 title，adopt/construct 只留 body。partial-delivery |
| GPT | `R40→VF39` | `medium` | `true-positive` | `good` | 与 grok 重叠：live receipt=api_inference，artifact 写死 claude_cli；stub 不消费 markdown |
| GPT | `R41→VF97` | `medium` | `true-positive` | `good` | 与 grok/muse 重叠：active 定义未注入。GPT 承认 README 已披露，标 medium 非 blocker，与 true-deferred 一致 |
| GPT | `R42→VF59` | `low` | `missed-by-others` | `good` | 独家低严重：vector.upserted 读不存在的 generation_artifact_uuid，真 key 是 dual_channel_artifact_uuid |
| GPT | `R43→VF83` | `medium` | `missed-by-others` | `excellent` | 独家：denial audit 先 sampler.decide 再写库，写失败仍耗配额，之后无审计 401。正确限定为不变量破而非准入绕过 |
| GPT | `R44→VF102` | `low` | `missed-by-others` | `good` | 独家：空 `payload_extra={}` 当无 mutation，truthiness 保留旧值；与 Task patch 的 model_fields_set 不一致 |
| GPT | `R45→VF100` | `medium` | `missed-by-others` | `good` | 独家：`str(exc)` 进 Process/Outbox，无统一 redaction；公共 Task 消息多为泛化，洞在落盘面 |
| Grok | `R1→VF61` | `critical` | `missed-by-others` | `excellent` | 独家 critical：claim 同 TX 解析失败回滚 + drain_once 先耗 outbox，修法可执行。ledger 点名若无此条 runtime 会在毒丸 JSON 上 livelock |
| Grok | `R2→VF27` | `critical` | `true-positive` | `excellent` | 与 gemini/gpt 重叠的承重核；缩水 required set 仍签完整 proof，行号与 fail-closed 修法准确 |
| Grok | `R3→VF85` | `critical` | `true-positive` | `mixed` | or True / ReadPort 自造 dict / sidecar 未实例化 / 缺文件 return 为真 tautology；dispatch_mega 串行 soak 被 ledger 判非 tautology |
| Grok | `R4→VF19` | `high` | `missed-by-others` | `excellent` | 独家：最后一次 RETRYABLE 改写 EXHAUSTED，generate 变终态；并指出 test_d01 锁的是 facade 不再发出的码 |
| Grok | `R5→VF44` | `high` | `missed-by-others` | `excellent` | 独家指针非单调 CAS；只读事务预留 generation 的机制也碰到 VF58，但本 R# 映射到 VF44 |
| Grok | `R6→VF55` | `high` | `missed-by-others` | `excellent` | 独家：`ux_vec_coord_active` 无 index_generation，同 coordinate UPDATE 撤回 serving 行 |
| Grok | `R7→VF2` | `high` | `true-positive` | `good` | 四方重叠的 CW 探针剧场 + FK 吞异常；内容正确但 orig high 低于 VF critical。未犯 Gemini「毁 MVCC」过称 |
| Grok | `R8→VF51` | `high` | `true-positive` | `good` | 与 gpt 重叠：LIVE_INFERENCE=false 时按 namespace 维 hash 打进 live 空间，读路径忽略 adapter_kind |
| Grok | `R9→VF11` | `high` | `true-positive` | `good` | 与 gpt 重叠的 salvage/pool SSOT；附带 clean_llm 未注入（R14/VF97）但不抢主映射 |
| Grok | `R10→VF86` | `high` | `true-positive` | `mixed` | sqlite3 打开 Turso 文件属实且与 gemini/gpt 重叠；把 CW waiver 捆进来（实为 VF91），并在 owner 已冻 NS1-V11 后仍标 blocker |
| Grok | `R11→VF9` | `high` | `true-positive` | `good` | 四方重叠的 CLI 超时不杀进程；证据准，orig high 低于 VF critical |
| Grok | `R12→VF37` | `high` | `missed-by-others` | `good` | 独家 stub 把 summary 写成 original；ledger 降为 partial-delivery（subprocess 模式不是静默 summarizer bug） |
| Grok | `R13→VF47` | `high` | `true-positive` | `good` | UUID LIMIT 1000 再 Python 打分，与 gpt/muse 重叠；orig high 低于 VF critical |
| Grok | `R14→VF97` | `high` | `true-positive` | `mixed` | clean_llm 未注入导致 admit-then-fail 属实，但 README 已标未接线，VF 为 true-deferred |
| Grok | `R15→VF60` | `high` | `true-positive` | `good` | 与 gemini 重叠：团队 rebuild resolve 不含 serving，一条 reactivate 未 ingest 的 item 毒死整单 |
| Grok | `R16→VF10` | `medium` | `true-positive` | `excellent` | 与 gpt/muse 重叠；主动因单 supervisor 拓扑降为 medium 比「运行中必双跑」更严谨，ledger 仍取最严 critical |
| Grok | `R17→VF40` | `medium` | `missed-by-others` | `good` | 独家：accept 已 active 后才 human_review，reject 不 deactivate。证据略薄但成立 |
| Grok | `R18→VF50` | `medium` | `true-positive` | `good` | 与 gpt 重叠的停用 Team 仍可检索；正确排除跨租户读，orig medium 低于 VF high |
| Grok | `R19→VF82` | `medium` | `missed-by-others` | `good` | 独家 valid-edge：mapped IPv6 不走 is_loopback/is_private；未跑 ipaddress 但 CPython 语义稳定 |
| Grok | `R20→VF23` | `medium` | `missed-by-others` | `mixed` | 独家现象属实（has_quota 恒真被 salvage 当真门），但 README K10/NS2-O1 已承诺 always-permit，VF 为 by-design deferred |
| Grok | `R21→VF38` | `medium` | `true-positive` | `mixed` | 与 gemini 重叠的贪婪 JSON 切片 + 不传 schema 成立；把空 g0 填 clean 算进切片缺陷，ledger 标子项过称 |
| Grok | `R22→VF79` | `medium` | `partial` | `mixed` | /docs 无鉴权是 valid-by-design（K9）；bootstrap `MkbError:pass` 是 VF98（muse 主映射），两条捆成一条 security |
| Grok | `R23→VF39` | `medium` | `true-positive` | `good` | 与 gpt 重叠：live markdown receipt=api_inference，artifact 写死 claude_cli |
| Grok | `R24→VF99` | `medium` | `missed-by-others` | `good` | 独家：Task 幂等指纹含 audit.created_at，合法重试变 identity-conflict |
| Grok | `R25→VF41` | `medium` | `missed-by-others` | `good` | 独家 adopt 两节点树 / 空 g0→clean；与 R21 有交叉，ledger 定为 partial-delivery |
| Grok | `R26→VF47` | `low` | `true-positive` | `good` | native_ann 死开关是 VF47 子项；标 low 比把「未交付 ANN」写成生产合同更诚实 |
| Grok | `R27→VF76` | `medium` | `partial` | `mixed` | degraded fail-open + IP-before-auth 成立（gemini/muse 重叠）；HMAC 短路子断言为假，compare_digest 两边都跑 |
| Grok | `R28→VF4` | `high` | `missed-by-others` | `mixed` | 独家适配器洞成立（raw cursor.rowcount、无 Turso CAS 测），但「恒 1/恒 -1 则 fence 失效」无实测；orig high+blocker，VF 降 medium |
| Muse | `R1→VF2` | `critical` | `true-positive` | `excellent` | Turso 单连接+IMMEDIATE+无 busy_timeout 与 CW 探针脱节坐实；未犯 Gemini「毁生产 MVCC」过称 |
| Muse | `R2→VF10` | `critical` | `true-positive` | `excellent` | heartbeat 存在但生产从未调用，180s×3+CLI 900s vs 30s lease；ledger 因本条保持 critical |
| Muse | `R3→VF9` | `high` | `true-positive` | `good` | wait_for 超时不 kill/wait 正确；未升 critical，也未覆盖 stdout 无上限 |
| Muse | `R4→VF47` | `high` | `true-positive` | `good` | ORDER BY uuid LIMIT 1000 再打分正确；把 native ANN 当生产合同略过 README 已声明的 scan profile |
| Muse | `R5→VF52` | `high` | `missed-by-others` | `good` | 同 default namespace 64↔1024 无 cutover 走 409；未误判为静默混空间（那是 VF51） |
| Muse | `R6→VF20` | `high` | `partial` | `mixed` | fence 由 enabled 五条而非 winners 三条属实，但是 composition allow-list；伪造备用模型无公共路径，ledger acknowledge |
| Muse | `R7→VF21` | `high` | `missed-by-others` | `mixed` | construct/CLI-clean 确绕过 ConcurrencyGate；所引 :164 是 transport picker 非 cli.run，fork bomb 被串行 supervisor 挡住 |
| Muse | `R8→VF64` | `high` | `true-positive` | `good` | services/object_gc 事务内 unlink+持写锁正确；正确性洞是 unlink 与 rollback 分裂，非秒级必堵 |
| Muse | `R9→VF69` | `high` | `true-positive` | `excellent` | GC/retirement run_forever 无 try，lifespan 不重启；与 retention except pass 对照清楚 |
| Muse | `R10→VF70` | `high` | `missed-by-others` | `excellent` | deadline LIMIT 1 无 ORDER BY、fail 后 return None，O(N) tick 才领活任务；Muse 本轮最高价值独家项 |
| Muse | `R11→VF74` | `medium` | `partial` | `mixed` | claim_token_hash 写入后未校验属实，但作者已承认 S03 单 fence 达标；dead code 而非 fencing 失效，true-deferred |
| Muse | `R12→VF103` | `high` | `missed-by-others` | `mixed` | SELECT-then-INSERT 未捕 IntegrityError 属实；IMMEDIATE+_write_lock 下「真实部署必现」过称 |
| Muse | `R13→VF75` | `high` | `true-positive` | `good` | 仅看 client.host；自注 loopback 无害，bypass 条件于 0.0.0.0+代理。gemini 同簇 |
| Muse | `R14→VF78` | `high` | `true-positive` | `good` | 驼峰 apiKey 漏检 + Team/Task PATCH 跳过是本条对 UF78 的增量；gpt 同簇 |
| Muse | `R15→VF79` | `medium` | `partial` | `mixed` | 默认 /docs 无鉴权属实，README K9 已记内网残留；blocker=yes 过重，true-deferred |
| Muse | `R16→VF42` | `medium` | `missed-by-others` | `good` | 任意 MkbError 改写 VECTORIZE_INFERENCE_FAILED，SPACE_VIOLATION 被当成可恢复 |
| Muse | `R17→VF43` | `medium` | `missed-by-others` | `mixed` | content_full header vs 裸 query 方向对；所引 retrieval_rank.py:194-216 现为 decode，真点在 `_embed_query` |
| Muse | `R18→VF57` | `medium` | `partial` | `mixed` | SQL 回退确只查 S04，但第二重 publication fence 仍挡住脏 EligibilityPort；ledger by-design/acknowledge |
| Muse | `R19→VF80` | `high` | `missed-by-others` | `mixed` | sqlite 许可仅看 PYTEST_CURRENT_TEST 属实；「export 即可绕过」忽略还需 persistence_backend=sqlite。high→medium |
| Muse | `R20→VF5` | `high` | `missed-by-others` | `mixed` | ledger `!r` 插值属实；id 来自 glob，供应链注入过称。high→medium |
| Muse | `R21→VF6` | `high` | `stale` | `weak` | executescript 回退对当前 pyturso 死代码；migrate 单测已绿。本轮两条 stale-rejected 之一（§4.3） |
| Muse | `R22→VF94` | `medium` | `true-positive` | `good` | readiness 持写锁跑 verify+探针；持锁对单连接是故意的，缺的是热路径缓存。gpt 同簇 |
| Muse | `R23→VF76` | `medium` | `true-positive` | `good` | degraded 永久黏住+桶满 fail-open 正确；ledger 取 high，本条略低估 |
| Muse | `R24→VF22` | `low` | `partial` | `mixed` | 只打到无 jitter/中间尝试不审计；UF22 主洞是持 lease sleep，gemini/gpt 已覆盖。orig low 偏低 |
| Muse | `R25→VF24` | `medium` | `missed-by-others` | `good` | local_vllm 仅 429/503/&gt;=500→RETRYABLE，408/425 被判 validation |
| Muse | `R26→VF25` | `medium` | `false-positive` | `weak` | INTERNAL 不重试是正确默认；adapter 已把 httpx.RequestError 映射 RETRYABLE，子断言假；ledger acknowledge |
| Muse | `R27→VF96` | `high` | `missed-by-others` | `good` | Facade limits 与 DispatchCaps 两套计数器+retrieval embed 直连；Settings 数字同源，非两份配置漂移 |
| Muse | `R28→VF90` | `high` | `missed-by-others` | `mixed` | addopts 仅 `-q --tb=short` 属实，但是工程成熟度 true-deferred，不应作生产 blocker |
| Muse | `R29→VF91` | `high` | `missed-by-others` | `excellent` | local_mock 关 CW/native_vector/live，e2e 永走 sqlite+hash；独家钉死假绿根因 |
| Muse | `R30→VF85` | `high` | `true-positive` | `good` | grep 栅栏、缺文件 return、&gt;= 宽松是 VF85 真点；未把整簇说成 tautology |
| Muse | `R31→VF85` | `medium` | `true-positive` | `good` | 串行 soak 与全局 buffer 污染落入同一假绿簇 |
| Muse | `R32→VF92` | `medium` | `stale` | `weak` | 所引 set==set 不在树中；`test_intake_reactivate` 已有 deactivate→search []。本轮两条 stale-rejected 之二（§4.3） |
| Muse | `R33→VF97` | `high` | `true-positive` | `mixed` | browser/OCR/Vision 注册未注入属实；README 已标未接线且本阶段 true-deferred，blocker=yes 过重 |
| Muse | `R34→VF98` | `medium` | `missed-by-others` | `mixed` | bootstrap/retention 吞异常无 log 属实；/ready 仍含 registry_bootstrap，「静默可用」过称 |
| Muse | `R35→VF53` | `medium` | `true-positive` | `good` | 每 hit 串行两次 read_verified 正确；10k scatter 巨事务是 GPT 增量，orig medium 偏低 |
| Muse | `R36→VF84` | `medium` | `missed-by-others` | `good` | 无全局 body cap，10k records 在 Pydantic 422 前全缓冲 |

### 2. 多维度评分 - 单向总分10分
选手清单: Gemini 3.7 Flash, GPT-5.6-sol, Grok 4.6, Muse Spark 1.2

| AGENT | 总分 | 证据链完整度 | 判断严谨性 | 修法建议可执行性 | 协作友好度 | 找到问题的覆盖面 | 严重级别准确度 |
|---------|------|------|------|------|------|------|------|
| Gemini | 7.3 | 7.5 | 6.5 | 8.0 | 7.5 | 8.5 | 6.0 |
| GPT | 8.5 | 9.0 | 9.0 | 8.0 | 8.0 | 9.0 | 8.0 |
| Grok | 8.1 | 8.7 | 8.0 | 8.4 | 8.8 | 7.3 | 7.2 |
| Muse | 7.6 | 8.5 | 6.8 | 8.3 | 8.2 | 7.3 | 6.5 |

- **Gemini（7.3）**：覆盖面极广并独家钉死 HTML 抹平 / 单通道 purge / retirement 死循环三处 critical，但严重级别系统性偏高，且把两处 by-design fail-closed 写成缺陷。相对 GPT/Grok/Muse，Gemini 在检索/结构内核上净增最多：VF28（唯一 critical，证据链完整）、VF54 单通道 purge 灭 serving、VF63 retirement 队头阻塞，外加 VF13 OVER_BUDGET 与 VF15 连接池等独家 high。四方重叠核（VF1 UoW、VF9 CLI 僵尸、VF27 丢层、VF85 假绿）也写得清楚。扣分来自严谨性与级别：R25/R26 把 S06/S07 不变量当 high bug；R12 把 salvage 方向写反；R18/R9/R22/R24 分别过称毁 MVCC、inflate 必崩、存储型 XSS、None 主键；长尾约 20 条只有标题无行号。未碰到的对等承重盲区是 VF3 sidecar abort、VF10 lease、VF47 UUID 截断、VF61 outbox 毒丸、VF93 wheel 缺 SQL。独特 critical 拉高覆盖面，过称与两处发明缺陷把总分压在 7.3。
- **GPT（8.5 · 最佳）**：零误报、证据链最完整的广谱主审：独家钉死 sidecar native abort 与 wheel 缺 SQL，但若干 critical 被标成 high，且未打到 outbox 毒丸 / HTML 抹平 / retirement 死循环。45 条全部落入 valid VF、§4.3 零驳回，是本轮判断最干净的一方。独家 21 条含两个 14-blocker（VF3 进程 abort、VF93 安装无法启动），另有 VF16/17/35/36 等别人没打到的身份/证据/制品洞，独特 critical 的权重明显高于四方重复的 medium。证据含子进程 exit 134、干净 wheel 解包、取消污染临时库，修法大多可执行。扣分来自：① 把 VF2/9/10/27/29 等 shared critical 写成 high（保守而非夸大）；② R20/R21 把非永真的 GC/fail-path 塞进假绿簇，R26 把 native_ann 读成生产 ANN 合同；③ 未覆盖 VF61/VF28/VF54/VF63 等 peer 独家 blocker。协作上先列正面事实、自限 live/GPU 未验，28 条 blocker 偏满但结构清楚。
- **Grok（8.1）**：证据链与修法都很硬，独家钉死 outbox 毒丸和世代 CAS；漏了同文件的 UoW 取消污染，并把未实测 rowcount / 错误 HMAC 短路写得过满。28 条全部落在 valid* VF、0 条进 §4.3 驳回表，file:line 与「未跑 pytest / 未测 pyturso」的诚实边界是本轮最干净的证据纪律。净增价值远高于重复的 medium：VF61 是唯一能冻住单 supervisor 的 critical，VF19/VF44/VF55 也只有他钉死。覆盖面被 VF1/VF3/VF28/VF29/VF54/VF63/VF93 这些他没写的承重洞拉低——尤其 `turso/port.py` 已打开却漏掉 cancel 不 rollback。判断上 R16 因单进程拓扑主动降到 medium 很严谨，但 R28 在无 live 证据时标 high+blocker、R27 发明 HMAC 短路，分别打了严重级别与严谨性。协作分最高（8.8）：11 个 blocker 在四方中最克制。
- **Muse Spark（7.6）**：证据密、修法具体、独家面广（claim 饿死 / 探针豁免 / CLI 无门限），但两则唯一 stale 与多项 by-design 当 blocker，严重级偏胀。证据链普遍带 file:line 与调用链，SQLite 对照和 S 文档对账完整，仅 R17 行号漂移、R7 :164 误指、R21/R32 未核实现树。判断上 34/36 能映射到真实 VF，且独家钉死 VF70/VF91/VF21/VF52/VF42 等，但本轮仅有的两条 stale-rejected 全是 Muse（R21 生产首次 migrate 永不 ready、R32 不存在的 set==set），再加 R26 把正确的 INTERNAL fail-closed 写成重试洞，严谨性被明显拉低。修法几乎条条可落地（heartbeat loop、kill+wait、IntegrityError→409、两阶段 GC、trusted-proxy CIDR）。协作上有正面事实、blocker/follow-up 分层和回应入口，但 21 个 blocker 含 by-design/deferred（R6/R15/R28/R33）偏压迫。覆盖宽到 persist/infer/retrieve/workflow/security/tests，却漏 VF1 UoW、VF3 sidecar abort、VF27 丢层、VF28/29 清洁锚点、VF54 purge、VF61 毒丸 outbox、VF63 retirement、VF93 wheel SQL 等本轮最贵 critical。严重级：R2/R1 准，R19/R20/R6 安全项 high 过胀，R21/R28/R33 把 stale 或 deferred 标成 blocker，R3/R4/R24 对共享 critical/medium 又略低估。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | `2026-08-20` | `Grok (0820-review-ledger workflow)` | Phase-1 UF merge only：4 方 154 条原始 finding → 103 条 UF1–UF103；状态 `triaged`；不填 VF 判定 |
| `v0.2` | `2026-08-20` | `Grok (0820-review-ledger workflow)` | Phase-3 VF inject：UF1–UF103 → VF1–VF103；填 §3/§4/§5 并更新 §1 计数；状态仍 `triaged`；§6/§7 留空 |
| `v0.3` | `2026-08-20` | `Grok (0820-review-ledger workflow)` | Phase-4 consistency：补全/改正 VF21/30/31/43/61/63/64/66/72/78 的 file:line（撞名模块与错行）；VF6 verdict 对齐 `stale-rejected`；VF20 class=`n/a` 并移出 §5.4；VF10 恢复 `critical` 并入 14-blocker；VF66 disposition=`partial-fix`；VF77 严重格注明 high→low；VF25 verdict=`valid-by-design`；VF92 整条 `stale-rejected`；UF52 标题统一为「维度 schism」。§1/§4.1 重算：属实 101 / overstated 19 / by-design 9 / stale-rejected 2 / n/a 7 / true-deferred 9 / fix 81 / partial-fix 6 / acknowledge 5。§6/§7 仍空 |
| `v0.4` | `2026-08-20` | `Grok (0820-review-ledger workflow)` | Phase-5 agent eval：§7 由占位「收口意见」换成完整 AGENT 评审绩效（Gemini/GPT/Grok/Muse Spark）；最佳 GPT、最高价值 VF3；§1 TL;DR 加一行指针。独立核对六维均值与 §3/§4 映射，未改分数、未把 by-design 升格 INVALID。文档状态仍 `triaged`；§0–§5 除 TL;DR 指针外未改写；§6 仍空 |
