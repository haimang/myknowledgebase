# NS1 第 1 轮跨 Reviewer 统一台账（verified-findings）

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 初步修复方案）。
> **谁写**：**实现者 / 合并人**（不是某一位 reviewer）。
> **何时用**：3 份独立 NS1 审查制品合并去重 + 对照当前真实代码独立复核。

---

> **元信息（置顶 · 必填）**
>
> | 字段 | 值 |
> |------|----|
> | **审查标的** | `NS1 non-interactive agentic production path` |
> | **审查阶段 / 轮次** | `第 1 轮合并` |
> | **合并 / 核查人（实现者）** | `Grok` |
> | **合并日期** | `2026-08-14` |
> | **文档状态** | `resolved` |
>
> **审查来源锚定（被合并的 reviewer 制品 — 必须逐份列全）**：
> - `docs/code-review/new-start/NS1-reviewed-by-gemini.md` — `high / 4 findings`（R1 blocker）
> - `docs/code-review/new-start/NS1-reviewed-by-GPT.md` — `critical / 7 findings`（R1/R2 blocker）
> - `docs/code-review/new-start/NS1-reviewed-by-grok.md` — `critical / 8 findings`（R1–R3 blocker）
>
> **对照真相（逐条 re-verify 时回看的源）**：
> - `docs/plan/new-start/NS1-new-pipeline.md`（P1–P5 / T01–T46）
> - `docs/eval/new-start/pre-NS1-qna.md`（`T-O-337..351`，只读）
> - `docs/closure/new-start/NS1-new-pipeline-closure.md`
> - 代码根：`src/services/{registry,config_snapshots,lsrag_compiler}.py`、`src/runtime/intake/**`、`src/runtime/inference/claude_cli.py`、`api/app.py`、`src/persistence/migrations/007_ns1_prompt_catalog.sql`、`data/prompts/**`、`tests/{unit,domain,e2e}/**`

---

## 0. 合并方法与核查纪律

- **合并范围**：3 份独立审查全部 finding 平铺（Gemini 4 + GPT 7 + Grok 8 = 19 条原始 finding）。
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

- **一句话裁定**：3 方第 1 轮共 19 条原始 finding 合并为 11 条统一项；6 条本轮 `fix` 的 `[true-bug]`、4 条本轮 `fix` 的 `[partial-delivery]`、1 条 `[true-deferred]`（Turso inspection harness）；最关键缺口是 catalog 双 active 阻断新 ingest、live/CLI 生产接线未闭合、Markdown 与 clean-anchor 合同互斥。
- **合并后统一 finding 数**：`11`（来自 `19` 条原始 finding 去重）。
- **按 verdict**：`valid 9` · `valid-pre-existing 1` · `valid(子项 overstated) 1` · `stale-rejected 0` · `INVALID 0`。
- **按三类归属 ★**：`[true-bug] 6（V1,V4,V5,V7,V9,V6 主项中的 fail-closed/receipt）` 计为 `V1 V4 V5 V7 V9` 五条纯 bug + `V6` 归 partial（运输账本未做完，不是回归）→ 最终 `[true-bug] 5（V1,V4,V5,V7,V9）` · `[partial-delivery] 5（V2,V3,V6,V8,V10）` · `[true-deferred] 1（V11）` · `n/a 0`。
- **按处置**：`fix 10` · `partial-fix 0` · `defer 1` · `owner-gated 0` · `ack 0`。
- **blocker 数**：`7`（编号：`V1 V2 V3 V4 V5 V7 V8`；V8 中 Turso 子项不升 blocker）。
- **净增承重盲区（peer 相对彼此）**：GPT 独家补了 live CLI 未装配、Markdown/clean 合同互斥、argv E2BIG；Grok 独家补了 scatter child 不继承 `prompt_selection`。Gemini 把 catalog 双 active 钉成唯一 blocker，漏了运输与 scatter 绑定。

---

## 2. 合并映射（reviewer finding → 统一编号）

### 2.1 映射表

| 来源 finding（reviewer-原编号）| 合并到 | 合并后问题（一句话）|
|------------------------------|--------|---------------------|
| Gemini-R1 / GPT-R3 / Grok-R1 | `V1` | Catalog PATCH 产生多条 active，snapshot 要求恰好 1 条；lexical `v10 < v9` |
| Gemini-R2 / GPT-R4 / Grok-R4 | `V2` | 未交付 `json.legal`/`json.realestate`；默认 A/C 仍指 legacy 文件；DDL profile 约束偏软 |
| GPT-R1 / Grok-R2 | `V3` | `live_inference=True` 不装配 CLI；live B.json 固定 clean + `promptB.default` |
| GPT-R2 | `V4` | 真实 Markdown 转写无法同时满足 clean 精确锚定 |
| GPT-R5 | `V5` | CLI 把整段物料放进单一 argv，API 允许的大物料会 E2BIG |
| GPT-R6 / Grok-R7 | `V6` | receipt 写死 generic 路径；缺 selection 不 fail-closed；CLI 错误不进 retry 闭集；invocation 账不完整 |
| Grok-R3（含 `_layered_profile` 静默 `{0,1,2}`） | `V7` | scatter child manifest 不继承冻结 `prompt_selection` |
| GPT-R7 / Grok-R6 / Gemini-R4 | `V8` | T34 / 真 legal T42 / T06 无 token / T46 非 drift / adopt 失败未穿过 kernel |
| Gemini-R3 / Grok-R5 | `V9` | `_live_summaries` 按块循环仍留在生产 mixin |
| Grok-R8 / GPT-1.2 | `V10` | closure 把残差收成「只有 pyturso」；action-plan 文首仍 `executing` 却标 P1–P5 全 closed |
| GPT-R7 全量 e2e / Grok-R8 pyturso 子项 / Gemini 1.2 | `V11` | 6 个 e2e 用 `sqlite3.connect` 读 pyturso 文件失败（harness residual） |

### 2.2 宽对照表

| 统一编号 | 合并后的问题 | Gemini | GPT | Grok |
|----------|--------------|--------|-----|------|
| `V1` | Catalog 双 active / version 排序 | `R1` | `R3` | `R1` |
| `V2` | legal/realestate 资产与 DDL | `R2` | `R4` | `R4` |
| `V3` | live 未走 CLI / 忽略 markdown | `—` | `R1` | `R2` |
| `V4` | Markdown vs clean-anchor | `—` | `R2` | `—` |
| `V5` | CLI 大物料 argv | `—` | `R5` | `—` |
| `V6` | receipt / audit / fallback | `—` | `R6` | `R7` |
| `V7` | scatter 不继承 selection | `—` | `—` | `R3` |
| `V8` | 测试假绿 / 缺口 | `R4` | `R7` | `R6` |
| `V9` | `_live_summaries` 死代码 | `R3` | `—` | `R5` |
| `V10` | closure / AP 过称 | `—` | `§1.2` | `R8` |
| `V11` | Turso inspection residual | `§1.2` | `R7` | `R8` |

---

## 3. verified-findings 台账（逐条独立复核 · 核心）

### 3.1 台账主表

| V# | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据（当前代码 file:line / 命令）| 初步处置（→ §5 细化）|
|----|------|------|------|----------|--------|--------------------------------------|----------------------|
| V1 | Catalog PATCH 双 active + lexical version | `critical` | Gemini/GPT/Grok | `valid` | `[true-bug]` | `registry.py:469-485` INSERT `status='active'` 不 retire；`config_snapshots.py:582-584` `len(candidates)!=1` → 503；`registry.py:411-415` `ORDER BY prompt_version DESC` 字符串排序 | `fix` |
| V2 | 领域闭集资产 / 默认 A/C / DDL invariant | `high` | Gemini/GPT/Grok | `valid` | `[partial-delivery]` | `registry.py:66-72` 无 legal/realestate；`data/prompts/json/` 仅 generic；`007_ns1_prompt_catalog.sql:13-14` 只检查 length；默认 A/C 仍 `prompt-a-clean-v1.md` / `prompt-c-summary-v1.md` | `fix` |
| V3 | live 组合未装配 CLI，且 live B.json 忽略 markdown | `critical` | GPT/Grok | `valid` | `[partial-delivery]` | `api/app.py:280-285` 仅 `not live_inference` 才建 CLI；`generation_construct.py:552-563` live 分支 `input_text=clean` + `prompt_key="promptB.default"` | `fix` |
| V4 | Markdown 转写与 clean-anchor 不可同时满足 | `critical` | GPT | `valid` | `[true-bug]` | `generation_construct.py:568-571` 把 `markdown_text` 当 B.json `-p`；`lsrag_compiler.py:494-497` 要求 g0==完整 clean；`promptB.markdown.legal.v1.md:5-8` 要求输出 Markdown 标记；stub 原样回显掩盖此矛盾 | `fix` |
| V5 | CLI argv 无法运输 API 允许的大物料 | `high` | GPT | `valid` | `[true-bug]` | `claude_cli.py:66-75` 整段 `-p` argv；`:146-153` `stdin=DEVNULL`；`models.py:104` inline 上限 8 MiB | `fix` |
| V6 | CLI receipt / 缺 selection fallback / retry 未闭环 | `medium` | GPT/Grok | `valid` | `[partial-delivery]` | `generation_construct.py:110-137` 无 frozen json 时回落 generic 路径；receipt `:137` 写死相对路径；`core.py:172-179` 无 `CLAUDE_CLI_*`；CLI receipt 只进 stage state | `fix` |
| V7 | scatter child 不继承冻结 prompt_selection | `high` | Grok | `valid` | `[true-bug]` | `acceptance_scatter.py:115-127` child payload 只有 source；`core.py:289-291` child state 用该 payload；`generation_construct.py:53-59` 缺 json 行则默 `(0,1,2)` | `fix` |
| V8 | 关键机制测试假绿 / 缺口 | `high` | 三方 | `valid(子项 overstated)` | `[partial-delivery]` | T42 e2e 仍绑 `promptB.json.generic`+`{0,1,2}`（`test_ns1_pipeline.py:34-36,128`）；T34 无 PATCH→retry；T06 全局 mock token（`test_ns1_prompt_routes.py:30`）；T46 只 soak 未 drift。GPT「无任何 fixtures」略过称：schema 测有 inline fixture，但无 `tests/fixtures/ns1/` 金样 | `fix` |
| V9 | `_live_summaries` 残留生产 mixin | `medium` | Gemini/Grok | `valid` | `[true-bug]` | `generation_live.py:474-505` 仍按 projection block 循环 `text_generate`；全库仅定义、无调用。P2-03 明确要求删除 | `fix` |
| V10 | closure / action-plan 过称 | `medium` | Grok/GPT | `valid` | `[partial-delivery]` | closure §0「唯一残差 pyturso」；AP 文首 `executing` 且 §11 标 P1–P5 `✅ done`。与 V1–V7 实测不符 | `fix` |
| V11 | 全量 e2e Turso/`sqlite3` inspection residual | `high` | 三方 | `valid-pre-existing` | `[true-deferred]` | 6 个 e2e 用标准 `sqlite3.connect` 读 `persistence_backend="turso"` 文件。baseline harness 问题，非 NS1 引入；owner 禁止 live migration。本轮不修 harness | `defer-with-rationale` |

### 3.2 簇子表（V2 / V8 展开）

| 位点（file:line）| 事实 | 复核 | 修法 |
|------------------|------|------|------|
| `registry.py:66-72` | `DEFAULT_CATALOG_PROMPTS` 无 `promptB.json.legal` / `promptB.json.realestate` | `valid` | bootstrap 两行 + 正文 |
| `data/prompts/json/` | 仅 `promptB.json.generic.v1.md` | `valid` | 新增 legal/realestate md |
| `registry.py:67,71` + `config_snapshots.py:50-53` | 默认 A/C 仍指向 legacy 根目录文件 | `valid` | 新增 `promptA.clean` / `promptC.summarizer` 并切换 default id；legacy 行保留以免破坏已冻 v1 |
| `007_ns1_prompt_catalog.sql:13-14` | `granularity_set` 只有 length CHECK | `valid` | 008 trigger：json 必填 JSON array；non-json 禁止 profile；一 prompt_id 仅一行 active |
| `data/schemas/lsrag.layered_content.v1.json` | 不强制「至少一个 g=0」 | `valid-edge` | schema `contains` g=0；kernel 已 fail-closed |
| `tests/e2e/test_ns1_pipeline.py:34,128` | 「legal」旅程仍 generic `{0,1,2}` | `valid` | 改绑 `promptB.json.legal` 并断言 `{0,1}` |
| `tests/unit/test_ns1_prompt_routes.py:30` | 全局 override operator token | `valid` | 追加无 mock 的 401 / 403 |
| `tests/unit/test_ns1_prompt_catalog.py:110-129` | 32×4 未变更 bytes | `valid` | soak 后追加一次真实 hash drift |
| `tests/e2e/test_registered_api_scatter.py:470-481` | 注入失败绕过 adopt | `valid` | 补 adopt 失败直穿 kernel 的单测；scatter fan-in 既有测保留 |

---

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

**A. 按三类归属（问责视图 · ★主视图）**

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | `5` | `V1 V4 V5 V7 V9` | §5.2 本阶段必修 |
| `[partial-delivery]` | `5` | `V2 V3 V6 V8 V10` | §5.2 补齐；无剩余切片则不进 §5.4 |
| `[true-deferred]` | `1` | `V11` | §5.4 承接 |
| `n/a`（rejected / 已修）| `0` | — | — |

> 三类合计（不含 `n/a`）= 11，与 §1 一致。

**B. 按处置（disposition 视图）**：

- **`fix`（本会话修）**：`V1 V2 V3 V4 V5 V6 V7 V8 V9 V10` = **10 项**
- **`partial-fix`**：无
- **`defer-with-rationale`（登记承接）**：`V11` = 1
- **`deferred-by-owner`**：无
- **`stale-rejected`**：无
- **`acknowledge`**：无

### 4.2 净增承重盲区 + 与自审初稿的差异（self-correction）

本合并人不是这 3 份审查的原作者；无「本人自审初稿」可推翻。跨 reviewer 净增价值：

- **V3 / V4 / V5（GPT 独家或主导）**：Gemini 把 P3 CLI 判 `done`，未核对 `live_inference` 组合根与 Markdown/clean 合同。
- **V7（Grok 独家）**：Gemini/GPT 未读 scatter child manifest 绑定。
- **V1（三方一致）**：这是唯一被三方同时钉死的 blocker，证据完全吻合。

### 4.3 带证据驳回的跨-reviewer 误报

| V# | 误报方 | 误报内容 | 反证（file:line）| 结论 |
|----|--------|----------|-------------------|------|
| V8 子项 | GPT | `rg --files tests/fixtures \| rg ns1\|layered` 无结果 ⇒ 完全没有金样 | `tests/unit/test_layered_schema.py:23-28` 与 `test_adopt_layered_json.py` 使用 inline fixture；kernel 金样以单测形式存在。缺的是 checked-in `tests/fixtures/ns1/` 文件，不是「没有任何金样」 | 主项 `valid`；该子句 overstated |
| V3 子项 | GPT | 把「未做 live vendor 验证」与「未装配 CLI」绑在一起作为同一缺口 | owner 禁止 live vendor；`api/app.py:280-285` 的缺口是**本地可静态证明的组合根**，本轮修组合根，不声称 vendor 验证 | 组合根 `valid`；vendor 验证归 V11 同类 owner-gated，不并进 V3 必修 |
| — | Gemini S5/S6 | 将 CLI 四跳与 Markdown 跳判 `done` | 与 GPT-R1/R2、Grok-R2 及 `generation_construct.py:552-574` 实测冲突 | 不单独立 V#；并入 V3/V4 为 Gemini 漏报 |
| — | Grok 1.2 | `LsragContractCompiler.structurize` 仍可调用视为负面 | P2-01 明文「fixture-only」；`tests/domain/test_ns1_guards.py:10-21` 已禁生产调用 | `valid-by-design`，不进统一缺口 |

---

## 5. 初步修复方案（preliminary fix plan）

### 5.1 修复策略

正确性与生产接线优先：先修 catalog 双 active（否则任何新 ingest 在第一次 PATCH 后死亡），再补领域资产与 scatter/CLI 绑定，再收 Markdown/clean 双物料合同与大物料运输，最后补测试与诚实文档。`[true-bug]` 全部本轮修；`[partial-delivery]` 全部本轮补齐；`[true-deferred]` 仅 V11 Turso harness（及 live vendor 验证）进 deferred ledger。每条 code fix 配 falsifiable 测试，断言只增不减。

**T-O-350 与 T-O-346 的执行解释（V4）**：不重开 QNA。B.json 的 user material 改为有类型的 `mkb.b-json-material.v1` 包（`clean` 必填，`markdown` 可空）。`original_content.body` 必须逐字来自 `clean`；markdown 只作结构提示。这使「有 markdown 则 B.json 看得到 markdown」与「锚定 SSOT 仍是 clean」同时成立。

### 5.2 逐项修复计划表

| V# | 计划修法 | 目标文件 | falsifiable 验证（修前应 RED）| 需 migration / owner-gate? | 依赖 / 批次 |
|----|----------|----------|-------------------------------|----------------------------|-------------|
| V1 | PATCH/register 同事务 retire 旧 active；`prompt_version_sort_key` 数值序；snapshot 按 latest active 选一行；008 唯一索引 | `registry.py`；`config_snapshots.py`；`008_ns1_prompt_catalog_invariants.sql` | PATCH v1→v2 后再 `_resolve_prompt_selection` 必须成功；`v10` 新于 `v9` | `yes`（008，本地 sqlite/turso 可迁） | 批次 1 |
| V2 | 正文 + bootstrap `json.legal {0,1}` / `json.realestate {0}`；新增 `promptA.clean` / `promptC.summarizer` 作 default；legacy 行保留；schema `contains` g=0；金样落盘；008 trigger | `data/prompts/json/*`；`registry.py`；`config_snapshots.py`；schema；`tests/fixtures/ns1/` | bootstrap 后 catalog 含 legal/realestate；缺 g=0 schema 拒 | `yes`（008） | 批次 1 |
| V3 | `ns1_cli_mode` 与 `live_inference` 解耦；A/B.md/B.json/C 优先 CLI；live fallback 用 markdown-or-clean + 冻结 json 选择 | `api/app.py`；`generation_construct.py` | `live_inference=True` + `ns1_cli_mode=stub` 注入 CLI；live 分支看到 markdown | `no` | 批次 2 |
| V4 | B.json user material 改为双物料包；stub 用 `clean` 编 body；三份 json prompt 写明 original 只从 clean 复制 | `generation_construct.py`；`claude_cli.py` stub；`data/prompts/json/*` | 转写后的 markdown + 不同 clean 仍 adopt 成功；markdown 标记不得进 g0 | `no` | 批次 2 |
| V5 | 超限物料改走 stdin；小物料保留 argv 以保持既有合同 | `claude_cli.py` | 200_000-byte user prompt 不再 `CLAUDE_CLI_TRANSPORT_FAILED` | `no` | 批次 2 |
| V6 | 无冻结 json/summarizer 指针 fail-closed；receipt 写实际相对路径；`CLAUDE_CLI_TIMEOUT`/`CLAUDE_CLI_TRANSPORT_FAILED` 进 recoverable；CLI receipt 落 generation/inference 账 | `generation_construct.py`；`core.py` | 无 selection → `PROMPT_NOT_REGISTERED`；receipt path == frozen path | `no` | 批次 2 |
| V7 | child manifest 复制父 Execution 冻结 `prompt_selection` 与 `*_prompt_id`；`_layered_profile` 禁止静默 `{0,1,2}` | `acceptance_scatter.py`；`generation_construct.py` | child payload 含 json 指针；缺 profile 409 | `no` | 批次 2 |
| V8 | T34 lifecycle；真 legal e2e；无 token/外网 CRUD；soak 后 drift；adopt 失败单测；composition 测 | `tests/unit/**`；`tests/e2e/test_ns1_pipeline.py` | 对应新测先红后绿 | `no` | 批次 3 |
| V9 | 删除 `_live_summaries`；domain 守卫禁止回归 | `generation_live.py`；`test_ns1_guards.py` | 守卫扫描无该方法 | `no` | 批次 1 |
| V10 | 回写 closure / AP 状态与本台账一致；剩余只指向 V11 | `NS1-new-pipeline-closure.md`；AP 文首 | 文档不再写「唯一残差 pyturso」且不再把未修项标 closed | `no` | 批次 4 |
| V11 | （defer）登记 Turso inspection + live vendor | `docs/closure/new-start/deferred-items-ledger.md` | — | `owner harness charter` | 承接 |

### 5.3 批次 / 依赖

- **批次 1（catalog + 死代码）**：`V1 V2 V9` — 先恢复可运营 catalog，删除会误导的入口。
- **批次 2（运输与绑定）**：`V3 V4 V5 V6 V7` — 依赖批次 1 的 frozen pointer / 领域行。
- **批次 3（测试补真）**：`V8` — 覆盖批次 1–2。
- **批次 4（文档诚实化）**：`V10 V11` — 测试绿后再改 closure / deferred ledger。

### 5.4 承接登记（`[true-deferred]` + `[partial-delivery]` 剩余切片）

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接位置（doc / phase / charter / issue）|
|----|--------------|------|----------|----------------|-------------------------------------------|
| V11 | `[true-deferred]` | `defer-with-rationale` | 6 个 e2e 失败是 pyturso 文件被标准 `sqlite3.connect` 打开的 harness 固有问题，baseline 即存在，非 NS1 机制；owner 本轮禁止改测试引擎/发版 | successor test-harness/adapter charter 落地后，无排除重跑 `tests/e2e` | `docs/closure/new-start/deferred-items-ledger.md` |
| V5.r | `[partial-delivery] 剩余切片` | `defer-with-rationale` | 本轮实现 stdin 运输并在本地用假 executable 证明不再 E2BIG；**未**对真实 `claude` 二进制做 vendor 验证（owner 禁止） | owner 授权 live Claude 验证窗口 | 同上，`Live Claude stdin/file transport vendor verification` |

---

## 6. 处置执行回填（fixes 落地后 · append-only）

> 本节在代码与测试落地后 append。§0–§5 冻结。

### 6.1 对本轮审查的回应

> 执行者: `Grok`
> 执行时间: `2026-08-14`
> 回应范围: `V1–V11`
> 对应审查文件: `docs/code-review/new-start/NS1-reviewed-by-{gemini,GPT,grok}.md`

- **总体回应**：三方 19 条 finding 合并为 11 条；10 条本轮修完，V11 与 V5 的 vendor 切片登记 deferred ledger。
- **本轮修改策略**：catalog 可运营面 → CLI/live/scatter 绑定与双物料合同 → 测试补真 → 文档诚实化。
- **实现者自评状态**：`ready-for-rereview`

### 6.2 逐项处置结果表

| V# | 处理结果 | 处理方式 | 修改文件 | 独立复核状态 |
|----|----------|----------|----------|--------------|
| V1 | `fixed` | PATCH/register 先 retire 旧 active 再 INSERT；`prompt_version_sort_key` 数值序；snapshot 取 latest active；008 唯一索引 | `src/services/registry.py`；`src/services/config_snapshots.py`；`008_ns1_prompt_catalog_invariants.sql` | `self-claimed-only` |
| V2 | `fixed` | 正文+bootstrap `json.legal {0,1}` / `json.realestate {0}`；新增 `promptA.clean` / `promptC.summarizer` 作 default；legacy 行保留；schema/validator 强制 g0；金样落盘；008 trigger | `data/prompts/json/*`；`registry.py`；`config_snapshots.py`；`layered_content.v1.json`；`layered_content.py`；`tests/fixtures/ns1/` | `self-claimed-only` |
| V3 | `fixed` | `ns1_cli_mode` 与 `live_inference` 解耦；A/B.md/B.json/C 优先 CLI；live fallback 使用双物料 + 冻结 json 选择；acquire 把 `payload` 带进后续 state | `api/app.py`；`generation_construct.py`；`acquisition_ingest.py`；`config.py` | `self-claimed-only` |
| V4 | `fixed` | B.json user material 改为 `mkb.b-json-material.v1`（clean SSOT + 可选 markdown 提示）；stub 只用 clean 编 body；三份 json prompt 写明 original 只从 clean 复制 | `generation_construct.py`；`claude_cli.py`；`data/prompts/json/*` | `self-claimed-only` |
| V5 | `partially-fixed` | 超限物料改走 stdin；16KiB 以下保留 argv。本地假 executable 证明 200KB 不再 E2BIG。真实 claude vendor 验证见 V5.r | `claude_cli.py`；`tests/unit/test_claude_cli_port.py` | `self-claimed-only` |
| V6 | `fixed` | 无冻结 json/summarizer/markdown 指针 fail-closed；receipt 写实际相对路径；`CLAUDE_CLI_TIMEOUT`/`CLAUDE_CLI_TRANSPORT_FAILED` 进 recoverable；CLI receipt 落 generation/inference 账 | `generation_construct.py`；`core.py` | `self-claimed-only` |
| V7 | `fixed` | child manifest 复制父冻结 `prompt_selection` 与 `*_prompt_id`；`_layered_profile` 禁止静默 `{0,1,2}` | `acceptance_scatter.py`；`generation_construct.py`；`acquisition_ingest.py` | `self-claimed-only` |
| V8 | `fixed` | T34 latest-vs-frozen；真 legal e2e `{0,1}`；无 mock 401/403；soak 后真实 drift；g0 schema；金样 adopt；CLI 无 selection fail-closed；composition live+CLI | 见下方测试清单 | `self-claimed-only` |
| V9 | `fixed` | 删除 `_live_summaries` 与已无调用的 `_live_text_generate`；domain 守卫禁止回归 | `generation_live.py`；`test_ns1_guards.py` | `self-claimed-only` |
| V10 | `fixed` | AP 文首 `executed`；closure 不再写「唯一残差 pyturso」；指向本台账与 deferred ledger | `NS1-new-pipeline.md`；`NS1-new-pipeline-closure.md` | `self-claimed-only` |
| V11 | `deferred-with-rationale` | 不改 harness；登记承接 | `docs/closure/new-start/deferred-items-ledger.md` | `deferred-by-owner/charter` |

### 6.3 Blocker / Follow-up 状态汇总

| 分类 | 数量 | 编号 | 说明 |
|------|------|------|------|
| 已完全修复 | `9` | `V1 V2 V3 V4 V6 V7 V8 V9 V10` | catalog、接线、双物料、测试、文档 |
| 部分修复，需二审 | `1` | `V5` | stdin 运输已落地；真实 claude vendor 未跑 |
| 有理由 deferred | `1` | `V11`（+ `V5.r`） | Turso inspection harness；live vendor |
| 拒绝 / stale-rejected | `0` | — | — |
| 仍 blocked | `0` | — | — |
| acknowledge（无需改）| `0` | — | — |

> **三类对账**：全部 `[true-bug]`（V1 V4 V5 V7 V9）已修或（V5）本阶段可静态证明的运输缺口已修、vendor 切片显式切出为 V5.r `[true-deferred]`；无 `[true-bug] → deferred` 静默改类。全部 `[partial-delivery]` 已修或剩余切片在 §5.4 / deferred ledger。

### 6.4 变更文件清单

- **产品代码**：`api/app.py`（V3）；`src/services/registry.py`（V1/V2）；`src/services/config_snapshots.py`（V1/V2）；`src/runtime/inference/claude_cli.py`（V4/V5）；`src/runtime/intake/generation_construct.py`（V3/V4/V6）；`src/runtime/intake/generation_live.py`（V9）；`src/runtime/intake/acceptance_scatter.py`（V7）；`src/runtime/intake/acquisition_ingest.py`（V3/V7）；`src/runtime/intake/core.py`（V6）；`src/runtime/config.py`（V3）；`src/contracts/lsrag/layered_content.py`（V2）；`src/persistence/migrations/008_ns1_prompt_catalog_invariants.sql`（V1/V2）；`data/prompts/json/*`（V2/V4）；`data/schemas/lsrag.layered_content.v1.json`（V2）
- **测试**：`tests/unit/test_ns1_*.py`、`test_adopt_layered_json.py`、`test_claude_cli_port.py`、`test_layered_schema.py`、`test_d04_write_paths.py`、`tests/domain/test_ns1_guards.py`、`tests/e2e/test_ns1_pipeline.py`、`tests/e2e/test_single_intake_pipeline.py`、`tests/fixtures/ns1/*`（V8）
- **docs**：`docs/code-review/new-start/NS1-review-VF-ledger.md`；`docs/closure/new-start/NS1-new-pipeline-closure.md`（V10）；`docs/closure/new-start/deferred-items-ledger.md`（V11）；`docs/plan/new-start/NS1-new-pipeline.md`（V10）

### 6.5 验证结果

| 验证项 | 命令 / 证据 | 结果 | 覆盖的 V# |
|--------|-------------|------|-----------|
| unit + domain | `.venv/bin/python -m pytest -q tests/unit tests/domain` | `pass` | V1–V9 |
| NS1 / intake e2e（排除已知 Turso 5 例） | `.venv/bin/python -m pytest -q tests/e2e -k 'not …turso residuals…'` | `pass`（12 passed） | V3 V4 V7 V8 |
| 静态门 | `ruff check .`；`compileall -q api src tests`；`git diff --check` | `pass` | 全部 |
| 全量 e2e 无排除 | 未重跑为成功证据 | `skipped-with-rationale`（V11） | V11 |

```text
tests/unit + tests/domain: PASS
tests/e2e excluding 5 known Turso inspection cases: 12 passed
ruff / compileall / git diff --check: PASS
```

### 6.6 未解决事项与承接

| 编号 | 状态 | 不在本轮完成的原因 | 承接位置 |
|------|------|--------------------|----------|
| V11 | `deferred` | pyturso / `sqlite3.connect` harness residual，非 NS1 机制 | `docs/closure/new-start/deferred-items-ledger.md` (`NS1-V11`) |
| V5.r | `deferred` | owner 禁止 live vendor 验证 | 同上 (`NS1-V5.r`) |

### 6.7 Ready-for-rereview gate

- **是否请求二次审查**：`yes`
- **请求复核的范围**：`only V1–V7 and V8 tests`
- **实现者认为可以关闭的前提**：
  1. 独立 reviewer 复核 catalog 单 active、live CLI 组合、双物料 adopt、scatter 继承。
  2. V11 / V5.r 保持在 deferred ledger，不把全量 e2e 或 live Claude 标成已验证。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | `2026-08-14` | `Grok` | 初次合并：3 方 19 finding → 11 统一项；triaged |
| `v0.2` | `2026-08-14` | `Grok` | §6 回填执行结果；状态 → `resolved` |
