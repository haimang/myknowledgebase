# MKB new-harvest NH1–NH9 第 2 轮跨 Reviewer 统一台账（UF → VF）

> **文档性质**：`review-findings-ledger`（跨 reviewer 合并 + verified-findings 复核 + 初步修复方案）。
> **谁写**：**实现者 / 合并人**（不是某一位 reviewer）。在收齐**全部** agent 的审查文件后，由实现者把多份独立审查平铺、合并、逐条对当前真实代码独立复核，形成单一权威台账。
> **为什么独立成文**：四份独立审查互不污染；本文件是本轮合并、复核与评价的单一权威台账。不改写各 reviewer 原件。
> **本文件推进纪律（硬）**：必须逐级落盘。Step-1 只写 UF 汇聚；Step-2 起才做独立核实；Step-3 注入 VF；Step-4 文档一致性审查；Step-5 AGENT 评价。禁止把后步结论提前写进前步。

---

> **元信息（置顶 · 必填）**
>
> | 字段 | 值 |
> |------|----|
> | **审查标的** | `MKB new-harvest NH1–NH9（4 通道接线 / kind-family workflows / 竞态幂等 / leaf-worker 读面 / 可观测性）HEAD @ ba099ee` |
> | **审查阶段 / 轮次** | `第 2 轮合并 / 2nd-pass` |
> | **合并 / 核查人（实现者）** | `Grok` |
> | **合并日期** | `2026-08-31` |
> | **文档状态** | `triaged`（Step-1…5 完成：UF 汇聚 + VF 核实 + 一致性审查 + AGENT 评价；未执行代码修复） |
>
> **审查来源锚定（被合并的 reviewer 制品 — 必须逐份列全）**：
> - `docs/code-review/new-harvest/NH1-NH9-2nd-pass-reviewed-by-GPT.md` — `critical / 17 findings`（R1–R4/R16 等标 blocker；最高 critical）
> - `docs/code-review/new-harvest/NH1-NH9-2nd-pass-reviewed-by-grok.md` — `high / 16 findings`（R1–R6 标 blocker；最高 high）
> - `docs/code-review/new-harvest/NH1-NH9-2nd-pass-reviewed-by-v4f.md` — `critical / 32 findings`（R1/R2/R3/R4/R6/R8/R10 标 blocker；最高 critical）
> - `docs/code-review/new-harvest/NH1-NH9-2nd-pass-reviewed-by-GLM53f.md` — `high / 21 findings`（R1/R2 标 blocker；最高 high）
>
> **对照真相（Step-2 起逐条 re-verify 时回看的源；本步不采信为已核实）**：
> - `docs/eval/new-harvest/final-execution-plan.md`（T-O-376..407）
> - `docs/eval/new-harvest/pre-charter-qna.md` / `pre-initial-planning-qna.md`
> - `docs/plan/new-harvest/AP-NH1..AP-NH9` 与 `todo-list.md`
> - `docs/closure/new-harvest/` 九份 AP + `CROSS-NH-campaign.md`（被审 claim，不是证明）
> - `docs/code-review/new-harvest/NH1-NH9-review-VF-ledger.md`（第 1 轮 42 条 UF/VF；**仅作 claimed-fix 谱系，本轮编号独立**）
> - `docs/closure/new-start/deferred-items-ledger.md`（NH-review-1 承接段）
> - 代码根：`src/`、`intake/`、`api/`、`tests/`、`src/persistence/migrations/018..024`
>
> **命名约定**：本文件为 `{TARGET}-2nd-pass-review-VF-ledger.md`。本轮 `UF1…UFn` / 后续 `VF1…VFn` **独立于第 1 轮 VF1–VF42**。第 1 轮 VF 编号只可在「claimed-fix 谱系」栏引用。

---

## 0. 合并方法与核查纪律

> **本节只立规矩，不写结论。** 说明合并了哪几份、用什么纪律复核。

- **合并范围**：`4` 份独立第 2 轮审查全部 finding 平铺（GPT 17 + Grok 16 + v4f 32 + GLM53f 21 = **86** 条原始 finding）。未丢 low / `[未验证]`。reviewer 原件是权威；本步不改写原件。
- **核查纪律（硬）**：
  1. **reviewer 的结论仅作线索**。每条判 `valid*` 的项，均由实现者**亲自 grep / Read 当前真实代码**坐实，关键证据带 `file:line`。**本 Step-1 不做该判定。**
  2. 与任一方（含第 1 轮台账的 `fixed` 标签）冲突，**以 Step-2 实测为准**；第 1 轮 `fully-fixed` 被推翻处必须在后续 §4.2 显式写出。
  3. **已纠正的跨-reviewer 误报**必须在后续 §4.3 带证据列出，不得静默吞掉。
  4. 严重级别**取多方最严**；同一根因 / 同一代码位点合并为一条统一编号。标题不同但机制相同 = 一条 UF。
- **统一编号前缀**：本文件 Step-1 使用 **`UF`（unified-finding）**。Step-2/3 写入 **`VF`（verified-finding）**，且 **`VF-n == UF-n`**（编号一一对应，驳回也不重排）。禁止在 Step-1 填写 VF 判定、class、disposition。
- **编号独立声明**：本轮 `UF1…UF52` / 后续 `VF1…VF52` **独立于第 1 轮 VF1–VF42**。正文若写「第 1 轮 VF19」，一律加「第 1 轮」前缀。
- **拆分纪律**：一条 reviewer R# 含两个可独立复现的根因时，拆到两条 UF，并在 §2.1 注明 `SPLIT`。同根因的「并发触发」不另开编号（例：GLM-R13 归入 UF5，不另开）。
- **verify_shard**（供 Step-2 分域核实，每条 UF 恰好一个）：`intake | workflow | persist | security | delivery | tests`。

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
| `pending-step-2` | Step-1 占位；尚未独立核实 |

### 0.2 处置（disposition）图例

| 处置 | 含义 |
|------|------|
| `fix` | 本轮修复（必配 falsifiable 测试或被既有/新增测试覆盖）|
| `partial-fix` | 部分修复 + 余项 defer（须写清切分）|
| `defer-with-rationale` | 有理由后延（带 reopen 触发器 + 承接位置）|
| `deferred-by-owner` | 归 owner session（sign-off / deploy / 复测）|
| `acknowledge` | 已修 / 无需改动（仅记录）|
| `stale-rejected` | 带证据驳回，不改代码 |
| `pending-step-3` | Step-1 占位 |

### 0.3 严重级别图例

`critical | high | medium | low | info`（取多方最严；`(nb)` = 非 blocker，`(子项)` = 仅子断言达该级）。Step-1 的严重级 = **reviewer 声称最严**，不是实现者复核后的级别。

### 0.4 Finding 三类归属（class）图例 ★

> **目的**：对每条**经复核成立（`valid*`）且代表未了结缺口**的 finding，按它**相对本阶段计划的归属**强制三选一。这是与 `verdict`（真不真）/ `disposition`（怎么处理）**正交的问责轴**。`stale-rejected` / `INVALID` / 已修的 `acknowledge` 不进三类，标 `n/a`。**本 Step-1 全部 class = `pending-step-2`。**

| 归属类 | 标记 | 精确含义 | 本阶段义务 | 典型 disposition |
|--------|------|----------|------------|------------------|
| **真 deferred** | `[true-deferred]` | 该缺口**本阶段从未承诺交付**，合法属于后续阶段 / owner session。 | **登记承接** | `defer-with-rationale` / `deferred-by-owner` |
| **真 bug** | `[true-bug]` | 本阶段引入的回归，**或**计划内该修却漏修 / 修错。 | **必须修**；严禁改写成 deferred | `fix` / 极少数 `partial-fix` |
| **部分交付** | `[partial-delivery]` | 本阶段已规划并已动手，但未完成 / 仅完成部分。 | **补齐**；剩余切片登记 §5.4 | `fix` / `partial-fix` |

---

## 1. 一句话裁定 + 合并统计（TL;DR）

> Step-3 已按 HEAD `ba099ee` 逐条复核并注入 VF。`VF-n == UF-n`。本工作流**未执行代码修复**；文档状态仍为 `triaged`。

- **一句话裁定**：4 方 86 条原始 finding → 52 条 VF。`51` 条属实（含 edge / by-design / owner-gated / pre-existing / 子项 overstated），`1` 条 stale-rejected（VF52：请求体上限存在于 `reject_oversize_body`）。本阶段欠账是 **15 [true-bug] + 18 [partial-delivery]**，另 **17 [true-deferred]** 诚实后延、`2` n/a。最关键生产缺口：单通道不同观察压进同一 Snapshot 并悬挂 change-set（VF1）、终态 Execution 仍接受迟到 Outcome（VF13）、kind rev1 原位 digest 导致升级 503（VF17）、HTTP `full_task` 在旧 actual 下重抓（VF6）、scatter identity 晚于信封冻结（VF5）。第 1 轮声称-fixed 被坐实为名义修复的是 VF18（原 VF19）、VF16 执法过宽（本轮 VF16）、VF12 hold 释放（本轮 VF22）、VF7 观察非原子（本轮 VF3）。v4f 把缺 GET `/workflows` 升 critical **过称**（T-O-379 / S01-T003）；GPT 把已披露 stub 与 `concurrent_writes` 历史张力升 blocker **过称**。
- **合并后统一 finding 数**：`52`（来自 `86` 条原始 finding 去重；VF# = UF#）。
- **按 reviewer 原始条数**：GPT `17` · Grok `16` · v4f `32` · GLM53f `21`。
- **按复核后严重级**：`critical 4`（VF1 / VF6 / VF13 / VF17）· `high 23` · `medium 20` · `low 5`。
- **按 verify_shard**：`intake 13` · `workflow 16` · `persist 6` · `security 3` · `delivery 12` · `tests 2`。
- **按 verdict**：`valid 33` · `valid-edge 4` · `valid-owner-gated 1` · `valid-pre-existing 4` · `valid-by-design 4` · `valid(子项 overstated) 5` · `stale-rejected 1` · `INVALID 0`。
- **按三类归属 ★**：`[true-bug] 15（VF1 VF2 VF5 VF7 VF8 VF10 VF13 VF15 VF16 VF17 VF18 VF28 VF31 VF36 VF49）` · `[partial-delivery] 18（VF3 VF4 VF6 VF9 VF11 VF12 VF19 VF20 VF21 VF22 VF23 VF24 VF26 VF34 VF38 VF43 VF45 VF50）` · `[true-deferred] 17（VF14 VF25 VF29 VF30 VF32 VF33 VF35 VF37 VF39 VF40 VF41 VF42 VF44 VF46 VF47 VF48 VF51）` · `n/a 2（VF27 VF52）`。
- **按处置**：`fix 25` · `partial-fix 5` · `defer-with-rationale 19` · `deferred-by-owner 1` · `acknowledge 1` · `stale-rejected 1`。
- **blocker 数（复核后）**：`4`（`VF1 VF6 VF13 VF17`；均为 `critical` 且本阶段须修的生产/升级缺口）。自称 blocker 被降级的典型：v4f-R8 目录 API、GPT-R12 concurrent_writes、GPT-R13 10+3 live、GPT-R16 全量 legal-edge。
- **净增承重盲区（peer 相对第 1 轮台账）**：GPT 独家钉死终态 Outcome（VF13）与 upgrade 503 现已可复现（VF17）；Grok 独家钉死 HTTP reacquire 过宽（VF16）与 tombstone 后再 ingest（VF8）；GLM 独家钉死 scatter 信封时序（VF5）与失败后观察永久 409（VF4）；v4f 独家钉死悬挂 change-set（VF1 的 change-set 切片）与 `latest_revision` LWW（VF2）。详见 §4.2。
- **SPLIT 清单（与 Step-1 相同）**：`GPT-R4` → UF5/UF6；`GPT-R10` → UF18/UF19；`GPT-R14` → UF11/UF38/UF43；`GLM-R21` 主挂 UF44。

---

## 2. 合并映射（reviewer finding → 统一编号）

> 把每位 reviewer 的原始编号映射到统一 `UF#`。一条统一项可由多方贡献。源 id 格式：`GPT-R#` / `Grok-R#` / `v4f-R#` / `GLM-R#`。

### 2.0 原始 finding 平铺（86 条，合并前）

| 源 | 原编号 | 声称严重级 | 标题（压缩）|
|----|--------|------------|-------------|
| GPT | R1 | critical | terminal Execution 仍接受迟到 Outcome 并推进 |
| GPT | R2 | critical | inline kind rev1 原位变化导致升级 503 |
| GPT | R3 | critical | 不同 observation 被压到同一 Snapshot |
| GPT | R4 | critical | full_task 在旧 actual 下重抓 HTTP；API retry 失败 |
| GPT | R5 | high | caller 点名 clean strategy，非法组合可永久 running |
| GPT | R6 | high | registered_api observation 无 in-flight reservation |
| GPT | R7 | high | Workflow read API / ProcessCapabilityManifest / strict response 缺失 |
| GPT | R8 | high | upload/Task pre-catalog 失败留下永久不可见 CAS |
| GPT | R9 | medium | upload replay/cancel 缺 session identity |
| GPT | R10 | high | selection fact 失实且 evidence plane 可普通 SQL 改写 |
| GPT | R11 | high | nested payload/URL/raw state 可把秘密与正文复制进 audit/stage |
| GPT | R12 | high | `concurrent_writes_required` 未进入 readiness |
| GPT | R13 | high | 10+3 的 model/OCR/browser production proof 未闭 |
| GPT | R14 | medium | 状态/错误/调试/控制 surface 仍 partial |
| GPT | R15 | medium | quarantine 对账仍漏 post-tombstone 与双 scanner 窗 |
| GPT | R16 | medium | NH9 legal-set/crash/evidence 强度不足 |
| GPT | R17 | high | Item 生命周期缺少跨 Task epoch |
| Grok | R1 | high | HTTP reacquire 按整图有守卫执法，盖住已声明 clean 边 |
| Grok | R2 | high | delete 后同 key 再 ingest：lookup 跳过墓碑，UNIQUE 仍占槽 |
| Grok | R3 | high | 第 1 轮 VF7 观察查重不在 Task UoW，且零测试 |
| Grok | R4 | high | 第 1 轮 VF12 cancel/ingest 仍不按会话 hold 隔离 |
| Grok | R5 | high | public GET 看不到实际绑边 |
| Grok | R6 | high | 七意图非法格未停在 admission |
| Grok | R7 | high | Task 投影允许 `cancelling→failed` / `queued→failed` |
| Grok | R8 | high | `full_task` retry 丢掉 `metadata_disposition` |
| Grok | R9 | medium | GET `/items` 对 single 恒 `outcome=active` |
| Grok | R10 | medium | 第 1 轮 VF19 用 manifest digest 冒充 representation fact |
| Grok | R11 | medium | 第 1 轮 VF25 只修了四意图 |
| Grok | R12 | medium | 第 1 轮 VF4 indexed `content_digest` trigger 可被改 state 后绕过 |
| Grok | R13 | medium | local_object acquire 不要求 public upload hold |
| Grok | R14 | low | 第 1 轮 VF16 session no-sandbox 扫描是对字面量的空转 |
| Grok | R15 | medium | index.rebuild 规划期对 stale 目标 `continue`，可 SUCCESS 空转 |
| Grok | R16 | low | admission 能力求交粗于图边 |
| v4f | R1 | critical | 单通道内容变更重摄入：悬挂 change_set + fact 丢失 + 陈旧 fingerprint |
| v4f | R2 | high | `latest_revision_uuid` 无 CAS 的 last-writer-wins |
| v4f | R3 | high | 第 1 轮 VF19 名义修复：fact digest 值域错配 + CONTROL 双公式 |
| v4f | R4 | high | 第 1 轮 VF1 未闭环：registered_api 能力闭集无 consumer + `registered_api.map` 泄漏 |
| v4f | R5 | high | local_object 源引用 / delete artifact 字节永不释放 |
| v4f | R6 | high | deactivated 项同 key 再 ingest：全流程白跑 + 假账 active→active |
| v4f | R7 | high | 策略可达性全部晚期检查（201 后 409） |
| v4f | R8 | critical | 无分类/目录接口 |
| v4f | R9 | high | 列表维残缺 |
| v4f | R10 | high | timeline 剥离 payload，无 per-process 事件查询 |
| v4f | R11 | high | DiagnosticSink 死代码 |
| v4f | R12 | high | metrics 目录死系列 |
| v4f | R13 | medium | admission 422/409 零记录 |
| v4f | R14 | high | 无 stage/process 级读取面 |
| v4f | R15 | high | 无 team 级 intake 总览 / observation_key 查询 / delete 结果不暴露 |
| v4f | R16 | high | outbox 死信不可重投、repair 不可手动、无 kill/restart |
| v4f | R17 | medium | registered_api observation 查重 TOCTOU |
| v4f | R18 | medium | GC tombstone 后 destroy 前崩溃：quarantine 字节永久滞留 |
| v4f | R19 | low | pending TTL 与排队 Task 竞态 |
| v4f | R20 | low | admission 大 records 哈希与请求体上限 [未验证] |
| v4f | R21 | medium | 无 stage_report 读取接口 |
| v4f | R22 | medium | stale-process-fence 抛异常回滚失败事件 |
| v4f | R23 | medium | retry/cancel/delete 幂等对前端不可区分 |
| v4f | R24 | low | payload_extra 全线 `'{}'` 空置 |
| v4f | R25 | medium | path digest 公式变更与离线冻结物漂移风险 |
| v4f | R26 | medium | rebuild 对 inactive 项 admission 姿态不一致 |
| v4f | R27 | medium | supply 缺件默认全开门 + 无能力查询接口 |
| v4f | R28 | medium | 「leaf-worker 模式」在系统内无实体 |
| v4f | R29 | low | reacquire 死路回旋：错误码失真 |
| v4f | R30 | low | 二次 delete 静默 no-op 与 deactivate/reactivate 409 不对称 |
| v4f | R31 | low | index.rebuild noop / exhausted_zero 状态对前端不可见 |
| v4f | R32 | low | TTL/cancel 静默；outbox.enqueued 事件无调用方 |
| GLM | R1 | high | 通道④ retry 死路：identity 采纳晚于信封冻结 |
| GLM | R2 | high | 通道④ observation 快照永久 409，失败采集无法同 key 补齐 |
| GLM | R3 | high | 第 1 轮 VF19 假修复：output_manifest_digest 冒充 representation_fact_digest |
| GLM | R4 | high | 失败原因不可通过任何接口回答 |
| GLM | R5 | high | 封闭 metrics 目录约 2/3 零 emit，ALERT 永不触发 |
| GLM | R6 | medium | 第 1 轮 VF16 假修复：no-sandbox 扫描是死代码 |
| GLM | R7 | medium | 第 1 轮 VF12 降级：hold 释放未按所有者归属化 |
| GLM | R8 | medium | supervisor 吞异常零感知 |
| GLM | R9 | medium | dead outbox 无重投路径 |
| GLM | R10 | medium | 单 kind 任务 `/items` outcome 恒 active |
| GLM | R11 | medium | fan-in waiting 对外折叠为 running |
| GLM | R12 | medium | retrieval 冷启动死锁：namespace_key 无发现端点 |
| GLM | R13 | medium | 并发同 external_key 的 identity 采纳竞态（R1 同根因） |
| GLM | R14 | medium | quarantine 永久滞留泄漏（第 1 轮 VF11 残余） |
| GLM | R15 | medium | DiagnosticSink 形同虚设 |
| GLM | R16 | medium | 分类/发现面缺失 |
| GLM | R17 | low | admission 不校验 local_object handle 存在性 |
| GLM | R18 | medium | 第 1 轮 VF6/VF7/VF25 等 fixed 项零专项测试，台账 §6.5 覆盖声明夸大 |
| GLM | R19 | medium | 可解释性最后一公里断裂 |
| GLM | R20 | low | 错误码双轨命名 |
| GLM | R21 | low | 可重试性无标志、item 级重试看得见发不出、列表缺 kind 过滤 |

### 2.1 映射表

| 来源 finding（reviewer-原编号）| 合并到 | 合并后问题（一句话）|
|------------------------------|--------|---------------------|
| GPT-R3 / v4f-R1 | `UF1` | 单通道同 source 不同 observation 复用旧 Snapshot；INSERT OR IGNORE 吞 change-set，悬挂 uuid、丢失 fact、指纹陈旧 |
| v4f-R2 | `UF2` | `latest_revision_uuid` UPDATE 无 CAS，并发不同内容 last-writer-wins |
| GPT-R6 / Grok-R3 / v4f-R17 | `UF3` | registered_api 观察查重在 Task INSERT 外的独立事务，无 in-flight reservation；并发双 201，accept 期裸约束可 500 |
| GLM-R2 | `UF4` | 已接受 observation 快照永不删除且无条件 409，失败采集无法同 key 补齐 |
| GLM-R1 / GLM-R13 / GPT-R4（API 切片） | `UF5` | scatter identity 采纳晚于 stage 信封冻结；retry / 并发同 key 在 seal 步 `INTAKE_SOURCE_MISSING` |
| GPT-R4（HTTP 切片） | `UF6` | `full_task` 复制旧 actual 后仍从 start 重跑，HTTP 可在旧 digest 下抓到新字节 |
| Grok-R8 | `UF7` | `full_task` retry 不复制 Execution `payload_extra`，`metadata_no_change` 可被 refresh 边吃掉 |
| Grok-R2 | `UF8` | delete 后同 `external_key` 再 ingest：lookup 跳过墓碑，UNIQUE 仍占槽，Task 已 201 |
| v4f-R6 | `UF9` | deactivated 项同 key 再 ingest 白跑整条管线，过渡账写 active→active，publication 末期 409 |
| GPT-R17 | `UF10` | Item 无跨 Task lifecycle/publication epoch；迟到 accept/publish 可穿越 delete/reactivate |
| Grok-R6 / v4f-R26 / v4f-R30 / GPT-R14（lifecycle 切片） | `UF11` | 七意图非法格未停在 admission：deactivated×rebuild 201；同态 deactivate/reactivate 201 no-op；二次 delete 不对称 |
| Grok-R15 | `UF12` | index.rebuild 规划期对 stale 目标 `continue`，Task 仍 SUCCESS，冻结集与 rebuild_count 可分叉 |
| GPT-R1 | `UF13` | 终态 Execution 仍接受迟到 Outcome，把原 Process 写成 succeeded 并物化下一 Process |
| Grok-R7 | `UF14` | Task 投影允许 `cancelling→failed` / `queued→failed`，违反 S02-T009 |
| GPT-R5 / v4f-R7 / Grok-R16 | `UF15` | 声明策略只做 kind 能力求交；媒体不匹配晚期 409 或被 worker 当成 stale fence 留下 running Process |
| Grok-R1 / v4f-R29 | `UF16` | HTTP reacquire 按「整图有守卫」执法，盖住 browser 起点与再获取后的已声明 clean 边；409 回滚后表现为 `recovery-exhausted` |
| GPT-R2 | `UF17` | inline kind `revision_number=1` 原位改 digest，已注册库升级稳定 `REGISTRY_DIGEST_MISMATCH` 503 |
| GPT-R10（fact 切片） / Grok-R10 / v4f-R3 / GLM-R3 | `UF18` | 生产把 `representation_fact_digest` 赋成 `output_manifest_digest`；与 `selected_output.py` 五键公式不是同一代数 |
| GPT-R10（evidence 切片） / Grok-R12 | `UF19` | 024 只在 `publication_state='indexed'` 时拦 `content_digest`；selected-output / artifact / vector 主体仍可普通 SQL 改写 |
| v4f-R4 | `UF20` | `SOURCE_KIND_ACQUIRE_CAPABILITIES["registered_api"]` 无 clean 定义消费；`actual_s05` 把 `registered_api.map` 封进闭集外真值 |
| v4f-R25 | `UF21` | `representation_path_digest` 纳入 `main_text_presence` 且 JOIN facts，公式变更未版本化，离线冻结物有漂移风险 |
| GPT-R9 / Grok-R4 / GLM-R7 | `UF22` | 每上传独立 `hold_owner`，但 cancel/TTL 放「最新一条」、ingest 放全部 pending；无 session/pending token |
| GPT-R8 | `UF23` | promote 先于 Team 校验；失败留下 catalog 外的 final CAS，GC 扫不到 |
| GPT-R15 / v4f-R18 / GLM-R14 | `UF24` | `reconcile_quarantine` 只恢复 live 目录行；TX2 tombstone 后 destroy 前崩溃则 quarantine 字节永久滞留 |
| v4f-R5 | `UF25` | snapshot/revision/source-object 属主引用从不释放；`intake_artifact` / `derived_generation` cleanup 无执行者 |
| Grok-R13 / GLM-R17 | `UF26` | local_object acquire 只要求任意未释放 reference；admission 不校验 handle 存在性 |
| v4f-R19 | `UF27` | pending TTL 无条件释放，排队 Task 采集期可 409 `OBJECT_REFERENCE_REQUIRED` |
| GPT-R11 | `UF28` | nested `payload_extra` / URL / stage envelope 绕过 root 拒密并把秘密与正文复制进 audit/CAS |
| GPT-R12 | `UF29` | 默认 `concurrent_writes_required=True` 但 Turso 报 false，且不进 overall `/ready` |
| GPT-R13 | `UF30` | 10+3 的 model/OCR/browser 仍由 stub / 固定 handler / 同源 glyph 证明，不是 production closure |
| Grok-R14 / GLM-R6 | `UF31` | 第 1 轮 VF16 的 no-sandbox 扫描对象是字面量 `["-headless"]`，raise 分支不可达 |
| v4f-R27 | `UF32` | supply 缺件默认 `/ready=200` + Task 201，能力清单无查询接口，缺件到 decode 才 503 |
| GPT-R7 / v4f-R8 / GLM-R16 | `UF33` | 无 workflow/strategy/capability/kind 只读目录；ProcessCapabilityManifest 未编译；OpenAPI Task 视图 `additionalProperties: true` |
| Grok-R5 | `UF34` | GET Task 不投影 `source_kind` / `acquisition_mode` / declared+actual strategy / `intake_item_uuid` |
| v4f-R9 / v4f-R15 / GLM-R12 / GLM-R21（列表切片） | `UF35` | 无 intake-items / process / namespace 列表；检索强制 `namespace_key` 却无发现端点；task 列表无 kind 过滤 |
| Grok-R9 / GLM-R10 | `UF36` | GET `/items` 用 scatter child 推导 outcome，单 kind 无 child 时恒 `active` |
| GLM-R11 | `UF37` | fan-in `waiting/scatter_children` 对外折叠为 `running`，无 `waiting_reason` |
| GLM-R4 / v4f-R10 / v4f-R14 / v4f-R21 / GLM-R19 | `UF38` | 真实失败原因 / process / stage_report / representation facts 在库内，公开与 operator 读面读不到（含固定 error_message、timeline 只回 digest） |
| v4f-R11 / GLM-R15 | `UF39` | DiagnosticSink 生产几乎无写入、无读取 API |
| v4f-R12 / GLM-R5 | `UF40` | metrics 目录约 2/3 从未 emit；`ALERT_*` 永不触发；repair 成功路径不计量 |
| v4f-R13 / v4f-R24 / v4f-R32 | `UF41` | admission 拒绝零记录；`payload_extra` 全线 `'{}'`；TTL/cancel 静默；`outbox.enqueued` 无调用方 |
| GLM-R8 | `UF42` | supervisor `drain_once`/`run` 吞 Exception 只写内存字段，无日志/指标，readiness 不读 `consecutive_failures` |
| v4f-R16 / GLM-R9 / GPT-R14（ops 切片） | `UF43` | outbox 8 次后 dead 无重投；未知 plan 死信不终结 owner；repair / kill / restart 无正式入口 |
| v4f-R23 / GLM-R21 | `UF44` | retry/cancel/delete 响应无 `applied/replay/noop`；无 `retryable` 标志；item 级重试看得见发不出 |
| Grok-R11 | `UF45` | 第 1 轮 VF25 只把四生命周期意图计入 `lifecycle_success`；rebuild/metadata 成功仍进 `indexed_success` |
| v4f-R31 | `UF46` | `index_rebuild_noop` / `exhausted_zero` 不投影到 Task 视图 |
| v4f-R22 | `UF47` | `_fail_process_tx` 在 `rowcount != 1` 时抛异常回滚整笔，失败事件瞬态无痕 |
| v4f-R28 | `UF48` | 「leaf-worker」只是 FastAPI 标题；同进程总启动 supervisor+GC+retention，无角色裁剪 |
| GPT-R16 | `UF49` | NH9 closed-set 每 strategy 一格、crash 靠 hook/事后 SQL；PROM-CAT 不断言 final CAS；既有 `test_stale_fencing_fail_*` 红 |
| GLM-R18 | `UF50` | 第 1 轮 VF6/VF7/VF25 等声称 fixed 零专项测试；台账 §6.5 用既有绿用例夸大覆盖 |
| GLM-R20 | `UF51` | 错误码 SCREAMING_SNAKE 与 kebab-case 双轨并存 |
| v4f-R20 | `UF52` | admission 对大 records 做全量哈希；请求体上限是否存在 [未验证] |

### 2.2 宽对照表

| 统一编号 | 合并后的问题 | GPT | Grok | v4f | GLM |
|----------|--------------|-----|------|-----|-----|
| `UF1` | 同 source 不同观察压进同一 Snapshot / 悬挂 change-set | `R3` | — | `R1` | — |
| `UF2` | `latest_revision_uuid` 无 CAS | — | — | `R2` | — |
| `UF3` | 观察查重不在 Task UoW / 无 reservation | `R6` | `R3` | `R17` | — |
| `UF4` | 失败后同 observation 永久 409 | — | — | — | `R2` |
| `UF5` | scatter identity 晚于信封；retry `SOURCE_MISSING` | `R4*` | — | — | `R1`/`R13` |
| `UF6` | HTTP full_task 在旧 actual 下重抓 | `R4*` | — | — | — |
| `UF7` | retry 丢掉 `metadata_disposition` | — | `R8` | — | — |
| `UF8` | delete 后同 key 再 ingest 201 后撞 UNIQUE | — | `R2` | — | — |
| `UF9` | deactivated 再 ingest 白跑 + 假账 | — | — | `R6` | — |
| `UF10` | Item 无 epoch，迟到 callback 穿越生命周期 | `R17` | — | — | — |
| `UF11` | 非法 lifecycle 格未停在 admission | `R14*` | `R6` | `R26`/`R30` | — |
| `UF12` | index.rebuild 规划期 skip 仍 SUCCESS | — | `R15` | — | — |
| `UF13` | 终态 Execution 仍接受迟到 Outcome | `R1` | — | — | — |
| `UF14` | `cancelling/queued → failed` 投影 | — | `R7` | — | — |
| `UF15` | 声明策略晚期失败或 Process 挂 running | `R5` | `R16` | `R7` | — |
| `UF16` | HTTP reacquire 整图执法 + 回旋失真 | — | `R1` | `R29` | — |
| `UF17` | kind rev1 原位 digest → 升级 503 | `R2` | — | — | — |
| `UF18` | `representation_fact_digest` 冒充 manifest digest | `R10*` | `R10` | `R3` | `R3` |
| `UF19` | evidence plane SQL 可变 / 024 可绕过 | `R10*` | `R12` | — | — |
| `UF20` | registered_api 闭集无 consumer + `.map` 泄漏 | — | — | `R4` | — |
| `UF21` | path digest 公式变更未版本化 | — | — | `R25` | — |
| `UF22` | hold 释放不按会话 | `R9` | `R4` | — | `R7` |
| `UF23` | pre-catalog 永久不可见 CAS | `R8` | — | — | — |
| `UF24` | tombstone 后 quarantine 滞留 | `R15` | — | `R18` | `R14` |
| `UF25` | source-object / artifact 永不释放 | — | — | `R5` | — |
| `UF26` | local_object 身份门不强制 upload_pending | — | `R13` | — | `R17` |
| `UF27` | pending TTL 与排队 Task 竞态 | — | — | `R19` | — |
| `UF28` | nested extras/URL/stage 复制秘密与正文 | `R11` | — | — | — |
| `UF29` | `concurrent_writes_required` 不进 `/ready` | `R12` | — | — | — |
| `UF30` | 10+3 live 仍是 stub/fixture | `R13` | — | — | — |
| `UF31` | no-sandbox 扫描字面量空转 | — | `R14` | — | `R6` |
| `UF32` | supply 默认全开门 | — | — | `R27` | — |
| `UF33` | workflow/capability 目录 API 缺失 | `R7` | — | `R8` | `R16` |
| `UF34` | GET Task 无实际绑边 | — | `R5` | — | — |
| `UF35` | 无 intake-items / namespace 列表 | — | — | `R9`/`R15` | `R12`/`R21*` |
| `UF36` | `/items` 单 kind 恒 active | — | `R9` | — | `R10` |
| `UF37` | waiting 折叠为 running | — | — | — | `R11` |
| `UF38` | 失败/process/stage/facts 读面断裂 | `R14*` | — | `R10`/`R14`/`R21` | `R4`/`R19` |
| `UF39` | DiagnosticSink 死 | — | — | `R11` | `R15` |
| `UF40` | metrics 死目录 / ALERT 永不触发 | — | — | `R12` | `R5` |
| `UF41` | 观测写入空槽 | — | — | `R13`/`R24`/`R32` | — |
| `UF42` | supervisor 吞异常 | — | — | — | `R8` |
| `UF43` | dead outbox 无重投且不终结 owner | `R14*` | — | `R16` | `R9` |
| `UF44` | 控制面幂等/可重试性对前端不可见 | — | — | `R23` | `R21` |
| `UF45` | `lifecycle_success` 口径未闭合 | — | `R11` | — | — |
| `UF46` | noop / exhausted_zero 不投影 | — | — | `R31` | — |
| `UF47` | stale-process-fence 回滚失败事件 | — | — | `R22` | — |
| `UF48` | leaf-worker 模式无实体 | — | — | `R28` | — |
| `UF49` | NH9 legal-edge / crash 证据不足 | `R16` | — | — | — |
| `UF50` | 第 1 轮 fixed 项零专项测试 | — | — | — | `R18` |
| `UF51` | 错误码双轨 | — | — | — | `R20` |
| `UF52` | 大 records 哈希 / 请求体上限 [未验证] | — | — | `R20` | — |

> `*` = 该 R# 被 SPLIT，源 id 在多条 UF 出现。GLM-R13 与 GLM-R1 同根，只在 UF5 计一次机制。

### 2.3 unified-findings 平铺台账

> 本节是 Step-1 问题汇聚台账。`最严严重级` = 来源中最严者。`verdict` / `class` / `disposition` 一律 pending。`reviewer 声称的 file:line` 是各方自称证据，**不是** Step-2 实测。

| UF# | 标题 | 最严严重级 | 来源 | verify_shard | 合并后问题（一句话）| reviewer 声称的 file:line |
|-----|------|------------|------|--------------|---------------------|---------------------------|
| UF1 | 同 source 不同观察压进同一 Snapshot | `critical` | GPT/v4f | intake | 命中旧 snapshot 只复用 UUID、不比 fingerprint；change-set UNIQUE 吞第二次 INSERT，Task 仍成功 | `acceptance_snapshot.py:139-171,337-453`；`acquisition_ingest.py:129-138,235-264`；`001_initial.sql:1178` |
| UF2 | `latest_revision_uuid` 无 CAS | `high` | v4f | intake | UPDATE 无 `AND latest_revision_uuid=?`，并发双内容 LWW | `acceptance_snapshot.py:191-195` |
| UF3 | 观察查重不在 Task UoW | `high` | GPT/Grok/v4f | intake | 预查独立事务；无 (team,source,observation) reservation；测试零 `INTAKE_OBSERVATION_*` | `task_create.py:97-98,452-480`；`scatter_intake.py:154-196`；`acceptance_snapshot.py:139-171` |
| UF4 | 失败采集无法同 key 补齐 | `high` | GLM | intake | 已存在快照无条件 409；全仓无 DELETE snapshot；文案「reuse original coordinates」无放行分支 | `scatter_intake.py:180-196`；`task_create.py:452-480` |
| UF5 | scatter identity 晚于信封冻结 | `critical` | GLM/GPT | intake | `_material` 先冻结含新 `intake_source_uuid` 的信封，outcome 回调才 INSERT OR IGNORE 采纳旧 uuid | `acquisition_ingest.py:384,423,447-476` 对照单条 `:129-137` |
| UF6 | HTTP full_task 在旧 actual 下重抓 | `critical` | GPT | workflow | retry 复制 sealed actual 后仍从 start 重跑 HTTP；seal 只比 clean step/process/strategy | `task_commands.py:293-318`；`runtime_core.py:107-163`；`acquisition_ingest.py:560-701`；`runtime_outcome.py:448-476` |
| UF7 | retry 丢掉 `metadata_disposition` | `high` | Grok | workflow | `_insert_root_execution` 不传 `payload_extra` → `'{}'`，no_change 边丢失 | `task_commands.py:293-318`；`task_create.py:216-222,367,448`；`kind_family.py:301-316` |
| UF8 | delete 后再 ingest 201 后撞 UNIQUE | `high` | Grok | intake | live lookup `deleted_at IS NULL`；UNIQUE 全行占槽；acceptance `INSERT OR IGNORE` 后按新 UUID UPDATE 0 行 | `acquisition_ingest.py:238-244`；`001_initial.sql:960`；`acceptance_snapshot.py:175-194` |
| UF9 | deactivated 再 ingest 白跑 + 假账 | `high` | v4f | intake | identity 不排 deactivated；过渡账写死 active→active；publication 要求 active 才 409 | `acquisition_ingest.py:235-246`；`acceptance_snapshot.py:172-195,492`；`lifecycle_publish.py:75-76` |
| UF10 | Item 无跨 Task epoch | `high` | GPT | intake | deactivate/delete 不 fence 其它 Task；accept/publish 不带 expected epoch | `lifecycle_apply.py:107-147`；`acceptance_snapshot.py:172-195`；`vector_publish_commit.py:168-190`；`lifecycle_publish.py:69-81` |
| UF11 | 非法 lifecycle 格未停在 admission | `high` | Grok/v4f/GPT | intake | `resolve_rebuild` 不 `require_active`；同态 deactivate/reactivate 返回 None 仍 201 succeeded | `targets.py:37-45,155-170`；`lifecycle_apply.py:92-105,231-247`；`acquisition_intents.py:108-114` |
| UF12 | index.rebuild skip 仍 SUCCESS | `medium` | Grok | intake | 规划期 stale `continue`；空 plans commit noop | `index_rebuild_plan.py:258-265` |
| UF13 | 终态 Execution 仍接受迟到 Outcome | `critical` | GPT | workflow | `accept_outcome` 只拒绝 cancelling；success 后仍物化下一 Process | `runtime_outcome.py:52-63,100-139`；`runtime_materialize.py:338-467,475-483` |
| UF14 | Task 六态边允许 cancelling→failed | `high` | Grok | workflow | `FAILED` 允许来源 `running\|cancelling\|queued` | `task_projection.py:63-65`；对照 S02-T009 |
| UF15 | 声明策略晚期失败或 Process 挂 running | `high` | GPT/v4f/Grok | workflow | admission 只求交 capability；mismatch `ConflictError` 被 worker 当 stale fence 重抛 | `strategies.py:193-208`；`runtime_materialize.py:105-114,198-214`；`worker.py:103-108`；`models.py:37-56` |
| UF16 | HTTP reacquire 整图执法 | `high` | Grok/v4f | workflow | 执法看 `plan.guards` 是否存在 absent 守卫，而非当前 hop 是否声明该边 | `runtime_materialize.py:65-94`；`kind_family.py:491-541`；`worker.py:104-108` |
| UF17 | kind rev1 原位 digest → 升级 503 | `critical` | GPT | workflow | `revision_number` 仍为 1；第 1 轮去重改变 canonical digest；无旧版 exact compat | `kind_family.py:239-253,361-369`；`workflow_registry.py:171-197`；`api/app.py:587-601` |
| UF18 | fact digest 冒充 manifest digest | `high` | 四方 | workflow | `"representation_fact_digest": selected["output_manifest_digest"]`；生产不调用 `project_selected_output` | `runtime_materialize.py:875-888,912-916`；`selected_output.py:88-124`；`018_nh2_selected_output_control.sql:6-32` |
| UF19 | evidence plane 仍可 SQL 改写 | `high` | GPT/Grok | persist | 024 只拦 indexed 行的 `content_digest`；改 state 再改 digest、改 selected-output/artifact/vector 不触发 | `024_nh_review_invariants.sql:5-51`；`018_nh2_selected_output_control.sql:6-32` |
| UF20 | registered_api.map 闭集泄漏 | `high` | v4f | workflow | 十个 CleanStrategyDefinition 无 registered_api capability；`actual_s05.py:26` 映射闭集外键并继承到 scatter child | `strategies.py:46-147,178-208`；`actual_s05.py:26-34`；`scatter_intake.py:651-657` |
| UF21 | path digest 公式未版本化 | `medium` | v4f | workflow | path digest 现含 `main_text_presence`（acquire 阶段恒 unknown） | `representation_history.py:42-57,78-85`；`acquisition_ingest.py:154,414` |
| UF22 | hold 释放不按会话 | `high` | GPT/Grok/GLM | persist | cancel `ORDER BY created_at DESC LIMIT 1`；ingest 释放该对象全部 `upload_pending` | `object_upload.py:72-120`；`object_upload_ttl.py:62-82`；`acceptance_snapshot.py:330-335`；`api/public/routes.py:136-169` |
| UF23 | pre-catalog 永久 CAS | `high` | GPT | persist | promote 后查 Team；GC 只扫 `mkb_stored_objects`；PROM-CAT 测试不看 final file | `object_upload.py:47-71`；`local_store.py:127-150,243-259`；`object_gc.py:134-167`；`test_new_harvest_crash_windows.py:390-433` |
| UF24 | tombstone 后 quarantine 滞留 | `medium` | GPT/v4f/GLM | persist | reconcile 跳过 tombstoned 行且无 destroy 收尾 | `object_gc.py:169-189,248-317`；`local_store.py:222-234` |
| UF25 | artifact / source-object 永不释放 | `high` | v4f | persist | delete 只按 `owner_uuid=item` 释放；cleanup 执行者仅 `vector_projection` | `acceptance_snapshot.py:318-335`；`lifecycle_apply.py:137-141,289` |
| UF26 | local_object 身份门过宽 | `medium` | Grok/GLM | intake | `_live_local_object` 任意未释放 reference 即可；admission 只校验 handle 格式 | `acquisition_ingest.py:703-728`；`object_upload.py:107-110`；`models.py:165` |
| UF27 | pending TTL vs 排队 Task | `low` | v4f | persist | TTL 无条件释放 upload_pending | `object_upload_ttl.py:40-60`；`acquisition_ingest.py:718-728` |
| UF28 | nested extras/stage 复制秘密与正文 | `high` | GPT | security | `PayloadExtraModel` 只验 JSON 大小；validator 不递归 source bag；stage envelope 复制 raw/clean | `common/models.py:24-35`；`api/models.py:414-426`；`config_snapshots.py:408-478`；`task_create.py:164-179`；`core.py:398-440` |
| UF29 | concurrent_writes 不进 ready | `high` | GPT | delivery | Settings 要求 true；Turso 报 false；`BASE_REQUIRED` 不含该项；测试把 overall ready 锁成正期待 | `runtime/config.py:21-25`；`turso/port.py:185-205`；`health.py:15-26`；`test_ns6_default_ready.py:16-39` |
| UF30 | 10+3 live 未闭 | `high` | GPT | delivery | 默认 stub / multimodal off；OCR 身份即 glyph5x7；browser 无 OS netns | `runtime/config.py:41-63`；`api/app.py:456-460`；`claude_cli.py:522-573`；`deterministic_ocr.py:62-83`；`browser.py:249-387` |
| UF31 | no-sandbox 扫描空转 | `medium` | Grok/GLM | security | `firefox_args = ["-headless"]` 后立刻扫描该列表 | `browser.py:249-251` |
| UF32 | supply 默认全开门 | `medium` | v4f | delivery | `runtime_supply_readiness_required=False`；缺 pdf 解析器仍 `/ready=200` | `config.py:63`；`api/app.py:265-271`；`acquisition_ingest.py:808-816` |
| UF33 | 无 workflow/capability 目录 API | `critical` | GPT/v4f/GLM | delivery | public/internal 无 `/workflows` `/strategies` `/capabilities`；capability digest 只是 process-key 排序 | `api/public/routes.py`；`api/internal/routes.py:17-161`；`workflow_registry.py:59-164,244`；`kind_family.py:30-34`；S03 `:420-537` |
| UF34 | GET Task 无实际绑边 | `high` | Grok | delivery | Task 视图无 kind/mode/strategy/item uuid；actual 列从未投影 | `task_views.py:61-94`；`actual_s05.py`；`observability.py:390-411` |
| UF35 | 无 intake-items / namespace 列表 | `high` | v4f/GLM | delivery | 检索强制 namespace；测试直读 `mkb_vector_namespaces`；无 intake-items 端点 | `api/models.py:608-613`；`retrieval_request.py:268-274`；`vector_publish_commit.py:266-290`；`task_commands.py:33-135` |
| UF36 | `/items` 单 kind 恒 active | `medium` | Grok/GLM | delivery | 用 child execution 推导 outcome；无 child → `active` | `task_projections.py:63-122`；`acceptance_snapshot.py:336-347` |
| UF37 | waiting 折叠为 running | `medium` | GLM | delivery | `_public_execution_status` 把 waiting 映射 running，无 waiting_reason | `runtime_scatter.py:108`；`task_views.py:203-215` |
| UF38 | 失败/process/stage 读面断裂 | `high` | GPT/v4f/GLM | delivery | `final_message` 固定文案；timeline 不选 status_before/after、不回 payload；无 processes/facts API | `runtime_outcome.py:501-616`；`observability.py:304-412,326-387`；`retrieval_pack.py:92-114` |
| UF39 | DiagnosticSink 死 | `high` | v4f/GLM | delivery | 生产写入点极少（retention / 两处 construct）；无读取 API | `observability.py:97-173,580`；`generation_construct.py:1277,1371`；`api/app.py:466` |
| UF40 | metrics 死目录 | `high` | v4f/GLM | delivery | `mkb_lease_recover_total` / `mkb_gc_*` / `mkb_worker_queue_lag_seconds` / `ALERT_*` 等零 emit | `metrics.py:15-17,82-229`；`api/app.py:596,601` |
| UF41 | 观测写入空槽 | `medium` | v4f | delivery | admission 拒绝不落事件；多处 `payload_extra='{}'`；TTL/cancel 无 metric | `task_create.py:76-109`；`events.py:16-61,95`；`object_upload_ttl.py:40-82` |
| UF42 | supervisor 吞异常 | `medium` | GLM | workflow | except 只写 `last_error`；health 不读 consecutive_failures | `workflow_supervisor.py:47-77`；`health.py` |
| UF43 | dead outbox 无重投且不终结 owner | `high` | v4f/GLM/GPT | delivery | attempts≥8 → dead；只读端点；未知 plan 死信时 Execution 仍 ready | `runtime_outbox.py:102-127,411-428`；`internal/routes.py:14-161`；`runtime_repair.py:25-124` |
| UF44 | 控制面幂等对前端不可见 | `medium` | v4f/GLM | delivery | retry 同指纹直接返回视图无 replayed；无 retryable 布尔 | `task_commands.py:190-191,247-262,382-383` |
| UF45 | `lifecycle_success` 口径未闭合 | `medium` | Grok | workflow | 分桶仅 deactivate/reactivate/delete/index.rebuild；Task 列只允许 `exhausted_zero` | `runtime_outcome.py:710-718`；`task_projection.py:51-52` |
| UF46 | noop / exhausted_zero 不投影 | `low` | v4f | delivery | `operation_mode: index_rebuild_noop` 不进 task_views | `index_rebuild_plan.py:47-48`；`task_views.py:61-94` |
| UF47 | fence 失败回滚失败事件 | `medium` | v4f | workflow | rowcount≠1 抛异常 → 整笔回滚，事件随之消失 | `runtime_outcome.py:487-541`；`worker.py:104-108` |
| UF48 | leaf-worker 模式无实体 | `medium` | v4f | delivery | FastAPI title 而已；总启动 supervisor+GC+retention | `api/app.py:604-625,657`；`workflow_supervisor.py:23` |
| UF49 | NH9 证据强度不足 | `medium` | GPT | tests | closed-set 每 strategy 一格；crash hook；PROM-CAT 不看 final CAS；`test_stale_fencing_fail_*` FAIL | `generate_closed_set_manifest.py:51-112`；`test_new_harvest_closed_set.py:558-630`；`test_ns6_phase2.py`；`migration_runner.py:109-177` |
| UF50 | 第 1 轮 fixed 项零专项测试 | `medium` | GLM | tests | `INTAKE_OBSERVATION_*` / `lifecycle_success` tests 零引用；review-fixes 7 例只钉部分 VF | `tests/e2e/test_nh1_nh9_review_fixes.py`；第 1 轮 VF-ledger §6.5 |
| UF51 | 错误码双轨 | `low` | GLM | delivery | SCREAMING_SNAKE 与 kebab 并存于同一闭集 | `test_nh8_intent_applicability.py:17-34` |
| UF52 | 大 records / 请求体上限 [未验证] | `low` | v4f | security | records 上限 10_000 条、单条无大小；全量 canonical_json+sha256 | `api/models.py:186`；`task_create.py:457-458,172-177` |

### 2.4 合并说明（避免过合并 / 过拆）

- **不把 UF1 与 UF3 合并**：UF1 是单通道「静默复用旧 Snapshot」；UF3 是 registered_api「查重事务边界」。机制与错误码不同。
- **不把 UF4 与 UF3 合并**：UF3 是并发 TOCTOU；UF4 是失败后的恢复出口缺失。
- **不把 UF8 与 UF9 合并**：墓碑占用 UNIQUE ≠ deactivated 复用活行。
- **不把 UF8 与 UF10 合并**：Grok-R2 是身份查找/UNIQUE；GPT-R17 是迟到 callback 穿越生命周期。
- **不把 UF33 与 UF34 合并**：Grok 明确把「缺 GET /workflows」判为 by-design 非 blocker，把「GET Task 无绑边」单列为 blocker。发现目录与 Task 投影是两个交付面。
- **UF38 有意簇合并**：失败文案、timeline payload、process/stage/facts 读面同属「库内富、对外贫」根因家族，Step-2 可在簇子表展开，但统一编号保持一条。
- **第 1 轮 VF 编号**：UF3/UF18/UF19/UF22/UF24/UF31/UF45/UF50 等是对第 1 轮声称-fixed 的再指控，**不是**沿用旧 VF 编号。

---

## 3. verified-findings 台账（逐条独立复核 · 核心）

> **本节是整份文档的灵魂。** 每条给出：复核后严重级、来源、verdict、归属类、实现者亲自 Read/Grep 的 `file:line`、初步处置。`VF-n == UF-n`。证据针对 HEAD `ba099ee`。

### 3.1 台账主表

| VF# | 对应UF | 标题 | 严重 | 来源 | 复核判定 | 归属类 | 关键证据（当前代码 file:line）| 初步处置 |
|-----|--------|------|------|------|----------|--------|-------------------------------|----------|
| VF1 | UF1 | 同 source 不同观察压进同一 Snapshot | `critical` | GPT/v4f | `valid` | `[true-bug]` | `acceptance_snapshot.py:139-145` 复用 snapshot **不比** fingerprint；`:397-415` `INSERT OR IGNORE` + UNIQUE `(team,snapshot)`（`001_initial.sql:1178`）；digest 不同则 `stored_change_set` 空，`:440-453` 把从未落库的 uuid 写进 Task | `fix` |
| VF2 | UF2 | `latest_revision_uuid` 无 CAS | `high` | v4f | `valid` | `[true-bug]` | `acceptance_snapshot.py:191-195` UPDATE 无 `AND latest_revision_uuid=?`；对照 metadata CAS `acceptance_lifecycle.py:304-305` | `fix` |
| VF3 | UF3 | 观察查重不在 Task UoW | `high` | GPT/Grok/v4f | `valid` | `[partial-delivery]` | `_assert_registered_api_observation_free` 独立事务 `task_create.py:97-98,452-470`，业务 INSERT 在 `:111`；`tests/` 零 `INTAKE_OBSERVATION_*` | `fix` |
| VF4 | UF4 | 失败采集无法同 key 补齐 | `high` | GLM | `valid` | `[partial-delivery]` | `scatter_intake.py:185-196` 已有快照无条件 409；全仓无 `DELETE FROM mkb_intake_snapshots`；409 本身符合 fail-loud，缺的是失败后复用出口 | `partial-fix` |
| VF5 | UF5 | scatter identity 晚于信封冻结 | `high` | GLM/GPT | `valid` | `[true-bug]` | scatter 在 `_material` 前写死新 uuid（`acquisition_ingest.py:391,423`）；`core.py:404-412` 把 `state` 冻进信封；回调 `:447-480` 才采纳旧 uuid。单条通道 `:129-165` 是先解析再 `_material` | `fix` |
| VF6 | UF6 | HTTP full_task 在旧 actual 下重抓 | `critical` | GPT | `valid` | `[partial-delivery]` | retry 复制 sealed actual（`task_commands.py:293-318`）但不传 `payload_extra`；HTTP 仍 `fetcher(url)`（`acquisition_ingest.py:560-596`）；seal 只比 step/process/strategy（`runtime_outcome.py:451-460`） | `fix` |
| VF7 | UF7 | retry 丢掉 `metadata_disposition` | `high` | Grok | `valid` | `[true-bug]` | 首次写入 `task_create.py:216-222`；retry `_insert_root_execution` 默认 `payload_extra=None`（`task_create.py:367`）；start-route 读 Execution extra（`runtime_materialize.py:186-195`） | `fix` |
| VF8 | UF8 | delete 后再 ingest 201 后撞 UNIQUE | `high` | Grok | `valid` | `[true-bug]` | lookup `deleted_at IS NULL`（`acquisition_ingest.py:243-244`）；UNIQUE 全行占槽（`001_initial.sql:960`）；`INSERT OR IGNORE` 后按新 UUID UPDATE 0 行（`acceptance_snapshot.py:175-195`） | `fix` |
| VF9 | UF9 | deactivated 再 ingest 白跑 + 假账 | `high` | v4f | `valid` | `[partial-delivery]` | identity 不排 `lifecycle_state`（`acquisition_ingest.py:239-244`）；过渡账写死 `'active','active'`（`acceptance_snapshot.py:487-492`）；publication 要求 active（`lifecycle_publish.py:75-76`）。第 1 轮 VF9.r | `fix` |
| VF10 | UF10 | Item 无跨 Task epoch | `high` | GPT | `valid-edge` | `[true-bug]` | delete 不 fence 其它 Execution（`lifecycle_apply.py:107-147`）；`vector_publish_commit.py:168-190` 构造 `IntakePublicationCommand` **无** `expected_item_revision`（publish 支持该字段：`lifecycle_publish.py:69-73`） | `fix` |
| VF11 | UF11 | 非法 lifecycle 格未停在 admission | `high` | Grok/v4f/GPT | `valid` | `[partial-delivery]` | `resolve_rebuild` 不传 `require_active`（`targets.py:38-45`，默认 False `:156`）；同态 deactivate/reactivate 返回 `None` 仍 `applied=False`（`lifecycle_apply.py:92-104,231-247`）。第 1 轮 VF9.r | `fix` |
| VF12 | UF12 | index.rebuild skip 仍 SUCCESS | `medium` | Grok | `valid-edge` | `[partial-delivery]` | 规划期 stale `continue`（`index_rebuild_plan.py:258-265`）。第 1 轮 VF9.r cardinality | `fix` |
| VF13 | UF13 | 终态 Execution 仍接受迟到 Outcome | `critical` | GPT | `valid` | `[true-bug]` | `accept_outcome` 只拒绝 `cancelling`（`runtime_outcome.py:60-62`），不拒绝 `succeeded/failed/cancelled`；随后 `_route_after_terminal_process_tx`（`:132-139`）；`_materialize_process_tx` INSERT 后 UPDATE Execution 用 `status NOT IN (terminal)` 且**不检查 rowcount**（`runtime_materialize.py:426-484`） | `fix` |
| VF14 | UF14 | Task 投影允许 cancelling→failed | `high` | Grok | `valid-pre-existing` | `[true-deferred]` | `task_projection.py:63-65` 确允 FAILED 来源为 running / cancelling / queued；S02-T009 基础边只有 cancelling→cancelled（`docs/baseline/domain-truth/S02-task-api.md:158`）。非 NH 引入，NH 未 reopen S02 | `defer-with-rationale` |
| VF15 | UF15 | 声明策略晚期失败或 Process 挂 running | `high` | GPT/v4f/Grok | `valid` | `[true-bug]` | admission 只求交 capability（`strategies.py:193-208`）；`pdf.ocr` 含 `http_static`（`:99-101`）故 `http_resource×pdf.ocr` 过 422；mismatch 抛 `ConflictError`（`runtime_materialize.py:105-114`）；worker **所有** ConflictError 当 fence 重抛（`worker.py:104-108`），同 UoW 回滚后 Process 仍 running | `fix` |
| VF16 | UF16 | HTTP reacquire 整图执法 | `high` | Grok/v4f | `valid` | `[true-bug]` | `plan_declares_reacquire = any(plan.guards)`（`runtime_materialize.py:85-94`）；HTTP 图只在 `decode_web_static → acquire_browser_reacquire` 声明该边（`kind_family.py:490-496`）；`decode_web_browser` / `decode_web_reacquire` 后继是 print/llm/web（`:512-541`）。第 1 轮 VF26 修错范围 | `fix` |
| VF17 | UF17 | kind rev1 原位 digest → 升级 503 | `critical` | GPT | `valid` | `[true-bug]` | `revision_number=1`（`kind_family.py:242`）；compose 去重改变 canonical（`:253`）；同 revision 不同 digest → `REGISTRY_DIGEST_MISMATCH` 503（`workflow_registry.py:192-197`）。第 1 轮一边 defer 升号（NH-VF21）一边改图 | `fix` |
| VF18 | UF18 | fact digest 冒充 manifest digest | `high` | 四方 | `valid` | `[true-bug]` | `"representation_fact_digest": selected["output_manifest_digest"]`（`runtime_materialize.py:884`）；NH1 代数要独立 fact 字段（`selected_output.py:108-124`）；生产不调用 `project_selected_output`。第 1 轮 VF19 名义修复 | `fix` |
| VF19 | UF19 | evidence plane 仍可 SQL 改写 | `high` | GPT/Grok | `valid(子项 overstated)` | `[partial-delivery]` | 024 对 fact/history 禁 UPDATE/DELETE、对 indexed `content_digest` 有 trigger（`024_nh_review_invariants.sql:22-51`）；**改 state 再改 digest** 不触发（`:46-48` WHEN 子句）。selected-output / artifact 无 append-only。子项「全部 evidence 可改」过称 | `partial-fix` |
| VF20 | UF20 | registered_api.map 闭集泄漏 | `medium` | v4f | `valid` | `[partial-delivery]` | `SOURCE_KIND_ACQUIRE_CAPABILITIES["registered_api"]`（`strategies.py:182`）无任何 `CleanStrategyDefinition` 消费；`src/runtime/binding/actual_s05.py:26` 映射 `"registered_api.map"`（不在十策略闭集）。公开 `RegisteredApiSourceDescriptor` 无 `clean_strategy`（`src/contracts/api/models.py:178-188`），「误伤合法成员」不成立 | `fix` |
| VF21 | UF21 | path digest 公式未版本化 | `medium` | v4f | `valid` | `[partial-delivery]` | `representation_path_digest` 含 `main_text_presence`（`representation_history.py:42-57`）；acquire 写 `"unknown"`（`acquisition_ingest.py:154,414`）。公式变更属实；「离线冻结物必炸」未在本环境复现 | `defer-with-rationale` |
| VF22 | UF22 | hold 释放不按会话 | `high` | GPT/Grok/GLM | `valid` | `[partial-delivery]` | 创建 `hold_owner=uuid7()`（`object_upload.py:105-120`）为真；cancel `ORDER BY created_at DESC LIMIT 1`（`object_upload_ttl.py:73-80`）；ingest 释放该对象**全部** pending（`acceptance_snapshot.py:330-335`）。第 1 轮 VF12 只修了写入侧 | `fix` |
| VF23 | UF23 | pre-catalog 永久 CAS | `high` | GPT | `valid` | `[partial-delivery]` | promote 在 Team 校验前（`object_upload.py:55-69`）；GC 只扫 catalog（`object_gc.py:146-166`）。已登记 `NH-VF13` | `defer-with-rationale` |
| VF24 | UF24 | tombstone 后 quarantine 滞留 | `medium` | GPT/v4f/GLM | `valid-edge` | `[partial-delivery]` | TX2 tombstone 后事务外 `_destroy_candidate`（`object_gc.py:313-315`）；`reconcile_quarantine` 跳过 tombstoned（`:178-184`）。第 1 轮 VF11 主窗已闭 | `fix` |
| VF25 | UF25 | artifact / source-object 永不释放 | `high` | v4f | `valid` | `[true-deferred]` | delete 只按 `owner_uuid=item`（`lifecycle_apply.py:137-141`）；cleanup 声明 `intake_artifact`（`:289`）；`index_retirement.py:32` 只执行 `vector_projection_soft_delete`。NH8 只承诺 logical tombstone | `defer-with-rationale` |
| VF26 | UF26 | local_object 身份门过宽 | `medium` | Grok/GLM | `valid` | `[partial-delivery]` | `_live_local_object` 任意未释放 reference（`acquisition_ingest.py:718-722`）；admission 只校验 handle 格式（`models.py:165`）。happy path upload→ingest 成立 | `defer-with-rationale` |
| VF27 | UF27 | pending TTL vs 排队 Task | `low` | v4f | `valid-by-design` | `n/a` | TTL 无条件释放（`object_upload_ttl.py:40-57`）是刻意取舍；失败为类型化 409。文档未写 TTL 语义，不构成正确性洞 | `acknowledge` |
| VF28 | UF28 | nested extras 绕过拒密 | `high` | GPT | `valid` | `[true-bug]` | `TaskCreateRequest` 只对 **root** `payload_extra` 调 `assert_safe_public_data`（`models.py:425`）；`GenericSemanticSource`/`RegisteredApiSourceDescriptor` 继承 `PayloadExtraModel` 只验 JSON 大小（`common/models.py:24-36`）。`assert_safe_public_data` 本身递归（`:128-136`），但没被用到 nested source。envelope 去正文仍是 `NH-VF3.r` | `fix` |
| VF29 | UF29 | concurrent_writes 不进 `/ready` | `high` | GPT | `valid-pre-existing` | `[true-deferred]` | `BASE_REQUIRED` 不含 `concurrent_writes`（`health.py:16-26`）；Turso 在 required=True 时仍报 false（`turso/port.py:196-197`）。NS6 测试把 overall ready + false 锁成正期待。非 NH 引入 | `defer-with-rationale` |
| VF30 | UF30 | 10+3 live 未闭 | `high` | GPT | `valid-owner-gated` | `[true-deferred]` | 默认 `ns1_cli_mode="stub"`、`multimodal_enabled=False`（`config.py:46-49`）。战役已披露；`NH-VF14.r`。不得改写成 fake-green，也不得升为本轮 true-bug | `deferred-by-owner` |
| VF31 | UF31 | no-sandbox 扫描空转 | `low` | Grok/GLM | `valid` | `[true-bug]` | `firefox_args = ["-headless"]` 后立刻扫描该列表（`browser.py:249-251`）。无生产 `--no-sandbox` 泄漏；第 1 轮 VF16 是名义修复 | `fix` |
| VF32 | UF32 | supply 默认全开门 | `medium` | v4f | `valid-by-design` | `[true-deferred]` | `runtime_supply_readiness_required=False`（`config.py:63`）；`_health_required` 因此只返回 BASE（`app.py:265-267`）。第 1 轮 VF15 只修 multimodal 强制 | `defer-with-rationale` |
| VF33 | UF33 | 无 workflow/capability 目录 API | `medium` | GPT/v4f/GLM | `valid(子项 overstated)` | `[true-deferred]` | public/internal 确无 `/workflows` `/strategies` `/capabilities`。T-O-379 / S01-T003 禁止 caller 点名 `workflow_key`；Grok 正确把「缺 GET /workflows」判非 blocker。v4f critical 过称。S03 只读面从未进入 NH AP | `defer-with-rationale` |
| VF34 | UF34 | GET Task 无实际绑边 | `high` | Grok | `valid` | `[partial-delivery]` | Task 视图无 kind/mode/strategy/item（`task_views.py:61-94`）；`actual_clean_strategy` 已封印在 Execution 列却从未投影。这是 actual-S05 的读面欠账，不是要求开放选图 | `fix` |
| VF35 | UF35 | 无 intake-items / namespace 列表 | `medium` | v4f/GLM | `valid` | `[true-deferred]` | 检索强制 namespace（`src/contracts/api/models.py:608-613`）为 Layer-A 安全决策；缺列表端点属实。NH DoD 未承诺这些发现面；测试直读表不能单独构成 true-bug | `defer-with-rationale` |
| VF36 | UF36 | `/items` 单 kind 恒 active | `medium` | Grok/GLM | `valid` | `[true-bug]` | 用 scatter child 推导 outcome，else `active`（`task_projections.py:111-122`）；single 写 membership 但不建 child（`acceptance_snapshot.py:336-347`） | `fix` |
| VF37 | UF37 | waiting 折叠为 running | `medium` | GLM | `valid-by-design` | `[true-deferred]` | `_public_execution_status` 把 waiting→running（`task_views.py:203-215`）是六态词表收窄。缺 `waiting_reason` 是解释字段，不是状态机断裂 | `defer-with-rationale` |
| VF38 | UF38 | 失败/process/stage 读面断裂 | `high` | GPT/v4f/GLM | `valid(子项 overstated)` | `[partial-delivery]` | `final_message` 固定文案（`runtime_outcome.py:616-617`）为真；timeline 故意只回 digest（`observability.py:406-409`）符合 S15-T050。子项「必须回完整 payload」过称。缺口是无 debug 门控 + 公开 error_message 不可用 | `partial-fix` |
| VF39 | UF39 | DiagnosticSink 死 | `medium` | v4f/GLM | `valid` | `[true-deferred]` | 生产写入：retention（`observability.py:580`）+ construct（`generation_construct.py:1161`）。GLM 声称的 `:1277,:1371` 在当前文件不存在（行号陈旧）。无读取 API。NH 未承诺填满诊断表 | `defer-with-rationale` |
| VF40 | UF40 | metrics 死目录 | `medium` | v4f/GLM | `valid` | `[true-deferred]` | 目录含 `mkb_lease_recover_total`/`mkb_gc_*`/`mkb_alert_raised_total`（`metrics.py:85-227`）；全仓 `increment(` 无这些名字。S15 闭集目录 ≠ 本战役 emit 承诺 | `defer-with-rationale` |
| VF41 | UF41 | 观测写入空槽 | `medium` | v4f | `valid` | `[true-deferred]` | admission 拒绝在 INSERT 前 raise（`task_create.py:76-109`）；`events.py:95,166` `payload_extra='{}'`。非 NH DoD | `defer-with-rationale` |
| VF42 | UF42 | supervisor 吞异常 | `medium` | GLM | `valid-pre-existing` | `[true-deferred]` | `drain_once`/`run` 捕 Exception 只写内存（`workflow_supervisor.py:51-61,72-77`），无 `logging.exception`。NS 引擎预存；第 1 轮 VF33 只覆盖 upload/GC 扫描 | `defer-with-rationale` |
| VF43 | UF43 | dead outbox 无重投且不终结 owner | `high` | v4f/GLM/GPT | `valid(子项 overstated)` | `[partial-delivery]` | `attempts >= 8` → `dead`（`runtime_outbox.py:417`）；internal 只有只读 `dead_outbox`（`api/internal/routes.py:133-134`）。「缺 requeue 命令」是 bounded v1 取舍；「未知 plan 死信后 Execution 仍 ready」是正确性切片 | `partial-fix` |
| VF44 | UF44 | 控制面幂等对前端不可见 | `medium` | v4f/GLM | `valid` | `[true-deferred]` | retry 同指纹直接返回视图（`task_commands.py:247-254`）无 `replayed`。create 的 200/201 可区分。属契约增字段 | `defer-with-rationale` |
| VF45 | UF45 | `lifecycle_success` 口径未闭合 | `medium` | Grok | `valid` | `[partial-delivery]` | 分桶仅四意图（`runtime_outcome.py:710-715`），缺 `intake.rebuild` / `intake.update_metadata`；Task 列只允 `exhausted_zero`（`task_projection.py:51-52`）。第 1 轮 VF25 部分修复 | `fix` |
| VF46 | UF46 | noop / exhausted_zero 不投影 | `low` | v4f | `valid` | `[true-deferred]` | `index_rebuild_plan.py:47-48` 写 `operation_mode`；`task_views.py:61-94` 不输出 | `defer-with-rationale` |
| VF47 | UF47 | fence 失败回滚失败事件 | `medium` | v4f | `valid-edge` | `[true-deferred]` | `rowcount != 1` 抛 ConflictError（`runtime_outcome.py:519-523`）是第 1 轮 VF24 的 fail-loud；同 TX 事件随之回滚。正确性优先于瞬态痕迹 | `defer-with-rationale` |
| VF48 | UF48 | leaf-worker 模式无实体 | `medium` | v4f | `valid-by-design` | `[true-deferred]` | `FastAPI(title="MKB leaf worker")`（`app.py:657`）仅为标题；单进程启动 supervisor+GC 是当前部署模型 | `defer-with-rationale` |
| VF49 | UF49 | NH9 证据强度不足 + VF24 旧测试红 | `medium` | GPT | `valid(子项 overstated)` | `[true-bug]` | `test_stale_fencing_fail_does_not_kill_new_generation`（`test_ns6_phase2.py:263-289`）在 fence 提升后仍调 `_fail_process_tx`，现会 `ConflictError`，与 VF24 新契约不同步。closed-set 每 strategy 一格（`generate_closed_set_manifest.py:86-98`）与进程级 kill 已登记 `NH-VF27.r`/`NH-VF42`，不得把整项升 campaign blocker | `partial-fix` |
| VF50 | UF50 | 第 1 轮 fixed 项零专项测试 | `medium` | GLM | `valid` | `[partial-delivery]` | `tests/` 零 `INTAKE_OBSERVATION_*`、零 `lifecycle_success` 断言。review-fixes 7 例只钉 VF1/2/8/11/15/18/31。台账 §6.5 用既有绿用例覆盖 VF6/7/25 过宽 | `fix` |
| VF51 | UF51 | 错误码双轨 | `low` | GLM | `valid-pre-existing` | `[true-deferred]` | SCREAMING 与 kebab 并存。信封形状统一。历史包袱，非 NH 引入 | `defer-with-rationale` |
| VF52 | UF52 | 大 records / 请求体上限缺失 | `low` | v4f | `stale-rejected` | `n/a` | `max_request_bytes` 默认 1MiB（`config.py:26`）；`reject_oversize_body` 先看 Content-Length 再 **stream 累加 cap**（`app.py:730-748`）。「上限不存在」不成立。records 10_000 是契约上限 | `stale-rejected` |

### 3.2 簇子表（第 1 轮声称-fixed 再核）

| 第 1 轮 VF | 本轮 VF | 第 1 轮声称 | 本轮核实 |
|------------|---------|------------|----------|
| VF7 观察 409 | VF3 / VF4 | `fixed` | 顺序 409 路径为真；不在 Task UoW、零测试、失败后无复用出口 |
| VF12 会话 hold | VF22 | `fixed` | 写入独立 hold 为真；cancel/ingest 未按 owner |
| VF19 fact digest | VF18 | `fixed` | 字段存在、值 = `output_manifest_digest` |
| VF16 no-sandbox | VF31 | `fixed` | 扫描字面量 `["-headless"]`，raise 不可达 |
| VF26 reacquire | VF16 | `fixed`（inline 半句） | inline 空文本不 409 为真；HTTP 整图执法是新洞 / 修错范围 |
| VF1 策略闭集 | VF15 / VF20 | `fixed` | 跨 kind 422 为真；同 kind 媒体不匹配可挂 running；`registered_api.map` 泄漏 |
| VF4 indexed digest | VF19 | `fixed` | 直接 UPDATE indexed digest 会 abort；改 state 再改 digest 可绕 |
| VF11 GC 对账 | VF24 | `fixed` | live restore 为真；post-tombstone destroy 窗仍漏 |
| VF25 lifecycle_success | VF45 | `fixed` | 四意图分桶为真；rebuild/metadata 仍进 `indexed_success` |
| VF24 fail_process rowcount | VF47 / VF49 | `fixed` | 代码 fail-loud 为真；旧 `test_stale_fencing_fail_*` 未同步，HEAD 红 |
| VF21 kind revision | VF17 | `deferred` | 第 1 轮仍改了 guard 去重，defer 期间把 rev1 digest 改掉，升级 503 现可复现 |
| VF13 uncatalogued CAS | VF23 | `partial/defer` | 仍在；与登记一致 |
| VF14 stub/OCR | VF30 | `deferred` | 仍在；GPT 升 blocker 过称 |
| VF9 7×state | VF9 / VF11 / VF12 | `partial` | metadata require_active 为真；rebuild/同态/deactivated ingest 未停 admission |

### 3.3 Step-2 核实方法

- HEAD：`ba099ee305577cca2281a669afbca364111f200b`（与四方审查基线一致）。
- 每条 UF 至少打开声称的主文件并用 Grep 反证（零命中 / 对照路径）。
- 未跑全仓 pytest；VF49 的红灯结论来自 **代码契约对照**（`_fail_process_tx` 现抛 `ConflictError` vs 测试期待 status 仍 running），与 GPT 实测 FAIL 一致，本合成人未再跑该单测。
- 未在临时库复现 GPT 的「failed Execution + late success」最小反例；判定依据是 `accept_outcome` 对 Execution 终态无守卫的静态路径，与 GPT 描述的代码位点吻合。

### 3.4 Step-4 一致性审查（UF ↔ VF · 计数 · file:line）

- UF1–UF52 与 VF1–VF52 **1:1**，无漏号、无重排。
- 原始 86 条 R# 全部进入 §2.1（GPT 1–17、Grok 1–16、v4f 1–32、GLM 1–21）；SPLIT 仅 GPT-R4/R10/R14 与 GLM-R21 列表切片。
- §1 / §3.1 / §4.1-A 三类计数对齐：true-bug 15、partial-delivery 18、true-deferred 17、n/a 2。
- §1 / §3.1 / §4.1-B 处置对齐：fix 25（含 VF6）、partial-fix 5、defer 19、owner 1、ack 1、stale 1。
- 表内 `cancelling→failed` 行曾因 `\|` 拆列，已改为文字列举，避免 Markdown 列漂移。
- 行号纠偏：GLM DiagnosticSink `:1277/:1371` 在当前 `generation_construct.py` 不存在，改为 `:1161`；outbox dead 钉到 `runtime_outbox.py:417`；namespace 422 钉到 `models.py:608-613`；`actual_s05.py` 实路径为 `src/runtime/binding/actual_s05.py`。

---

## 4. 复核汇总 + self-correction

### 4.1 分桶汇总

**A. 按三类归属（问责视图 · ★主视图）**

| 归属类 | 数量 | 编号 | 本阶段义务落点 |
|--------|------|------|----------------|
| `[true-bug]` | 15 | VF1 VF2 VF5 VF7 VF8 VF10 VF13 VF15 VF16 VF17 VF18 VF28 VF31 VF36 VF49 | §5.2 本阶段**必修**（漏修则升 blocker，不许 defer）|
| `[partial-delivery]` | 18 | VF3 VF4 VF6 VF9 VF11 VF12 VF19 VF20 VF21 VF22 VF23 VF24 VF26 VF34 VF38 VF43 VF45 VF50 | §5.2 补齐 + 剩余切片登记 §5.4 |
| `[true-deferred]` | 17 | VF14 VF25 VF29 VF30 VF32 VF33 VF35 VF37 VF39 VF40 VF41 VF42 VF44 VF46 VF47 VF48 VF51 | §5.4 承接（带 reopen 触发器）|
| `n/a`（rejected / 已修 / by-design 无缺口）| 2 | VF27 VF52 | 不进三类 |

> 三类合计 15+18+17=50；加 n/a 2 = 52。与 §1 一致。

**B. 按处置（disposition 视图）**：

- **`fix`（本会话修）**：VF1 VF2 VF3 VF5 VF6 VF7 VF8 VF9 VF10 VF11 VF12 VF13 VF15 VF16 VF17 VF18 VF20 VF22 VF24 VF28 VF31 VF34 VF36 VF45 VF50 = **25 项**
- **`partial-fix`**：VF4 VF19 VF38 VF43 VF49 = **5**
- **`defer-with-rationale`**：VF14 VF21 VF23 VF25 VF26 VF29 VF32 VF33 VF35 VF37 VF39 VF40 VF41 VF42 VF44 VF46 VF47 VF48 VF51 = **19**
- **`deferred-by-owner`**：VF30 = **1**
- **`stale-rejected`**：VF52 = **1**
- **`acknowledge`**：VF27 = **1**

### 4.2 净增承重盲区 + 与自审初稿的差异（self-correction）

> 实现者 = 第 1 轮台账作者同体。第 1 轮 `NH1-NH9-review-VF-ledger.md` §6 把若干项标 `fixed` / `self-claimed-only`。本轮以代码推翻。

- **净增盲区（peer 相对第 1 轮台账）**：
  - VF13（GPT 独家）：终态 Execution 无 Outcome 守卫。第 1 轮只修了 process fence rowcount（旧 VF24），没问 owner Execution 是否仍允许提交。
  - VF17（GPT 独家现况）：第 1 轮把 kind revision 登记 defer（NH-VF21），随后仍在 rev1 上去重 guards，把「潜在升级雷」变成可复现 503。
  - VF16（Grok 独家）：第 1 轮 VF26 把 reacquire 从「全部 kind」收到「plan 上有守卫」——修了 inline 误伤，留下 HTTP 整图执法。
  - VF5（GLM 独家）：scatter 信封时序与单条通道不对称；closed-set 全是首跑，测不到 retry。
  - VF8（Grok 独家）：tombstone 后再 ingest 不是二次 HTTP delete（那格 409 为零 Task），是同 key 新 ingest。
  - VF1/VF2（v4f 为主）：第 1 轮观察幂等只加固了 registered_api，单通道仍静默聚合。
- **本人第 1 轮台账被推翻 / 修正处**：
  - 「VF19 material 纳入 representation_fact_digest → fixed」→ **实测纠正**：`runtime_materialize.py:884` 值为 `output_manifest_digest` → 现 VF18 `valid` `[true-bug]`。
  - 「VF16 session no-sandbox → fixed」→ **实测纠正**：`browser.py:249-251` 扫描字面量 → 现 VF31。
  - 「VF12 会话 hold + cancel 一条 → fixed」→ **实测纠正**：cancel 是「最新一条」不是「调用者那一条」→ 现 VF22。
  - 「VF7 观察 409 零新行 → fixed」→ **实测纠正**：独立事务预查，无 reservation → 现 VF3。
  - 「VF26 reacquire 仅声明图 → fixed」→ **实测纠正**：执法键是 `plan.guards` 存在性 → 现 VF16。
  - 「24 项 fully-fixed / 无 blocked」→ **过称**；本轮不沿用该计数。

### 4.3 带证据驳回的跨-reviewer 误报

| V# | 误报方 | 误报内容 | 反证（file:line）| 结论 |
|----|--------|----------|-------------------|------|
| VF52 | v4f-R20 | API 请求体上限可能不存在 | `config.py:26` `max_request_bytes=1_048_576`；`app.py:730-748` 先 CL 再 stream 累加 cap | `stale-rejected` |
| VF33（子项） | v4f-R8 | 无 GET `/workflows` 即动态工作流未落地 / critical blocker | 选图权威在 `source_kind`（`workflow_registry.py:79-103`）；T-O-379 禁止 caller `workflow_key`；Grok-O12 | 主项「无目录端点」valid；blocker/「未落地」过称 |
| VF30（升 blocker） | GPT-R13 | 10+3 stub 使 NH 不能收口 | `NH-VF14.r` 已披露；`final-execution-plan.md` stub 不得冒充 complete | 现象 valid-owner-gated，不得当本轮 true-bug |
| VF29（升 NH blocker） | GPT-R12 | `concurrent_writes_required` 不进 ready 是 NH 生产断裂 | `health.py:16-26` 与 NS6 `test_ns6_default_ready.py` 已把该画像锁成正期待 | `valid-pre-existing` |
| VF38（子项） | v4f-R10 / GLM-R4 部分 | timeline 必须回完整 payload 否则可解释性断链 | `observability.py:406-409` 明文 v1 只回 digest；S15-T050 | 缺 debug 门控 valid；「违约 T050」stale |
| VF27 | v4f-R19 | pending TTL 与排队 Task 是正确性洞 | 类型化 409 是刻意 fail-loud | `valid-by-design` |

---

## 5. 初步修复方案（preliminary fix plan）

> 本节是台账的前瞻产物。本工作流**不落地代码**。三类 → 义务：`[true-bug]` 与可落地的 `[partial-delivery]` 进 §5.2；`[true-deferred]` 进 §5.4。`[true-bug]` 不得改写成 deferred。

### 5.1 修复策略

优先正确性状态机与观察身份（VF13 / VF1 / VF5 / VF8 / VF17），再收口第 1 轮名义修复（VF18 / VF22 / VF16 / VF31 / VF3），再补 caller 读面最小切片（VF34 / VF36 / VF38 error_message）。安全只修 nested extras（VF28），不在本轮重写 stage envelope（NH-VF3.r）。测试：先修 HEAD 红灯 `test_stale_fencing_fail_*`（VF49），再为观察三态 / hold 所有权补常驻护栏（VF50）。不把 S03 全量 workflow API、真模型、进程级 kill、physical purge 拉进本批。

### 5.2 逐项修复计划表

| V# | 计划修法 | 目标文件 | falsifiable 验证（修前应 RED）| 需 migration / owner-gate? | 依赖 / 批次 |
|----|----------|----------|-------------------------------|----------------------------|-------------|
| VF13 | `accept_outcome` 要求 Execution ∈ {ready,running,waiting}；materialize INSERT 前再查 owner 非终态；UPDATE Execution 检查 rowcount | `runtime_outcome.py` `runtime_materialize.py` | 终态 Execution + late success → `accepted=False` / 409；无新 Process | no | 批次 1 |
| VF1 | 已有 snapshot 时比较 fingerprint；不同则新 snapshot 或类型化 409；change-set 每次接受独立或按 digest 回读失败则 409 | `acceptance_snapshot.py`；可能 `001` UNIQUE | 同 key 不同正文 → 2 snapshot 或稳定 409；无悬挂 change_set | 可能 migration | 批次 1 |
| VF2 | UPDATE 加 `AND latest_revision_uuid=?`，rowcount≠1 → 409 | `acceptance_snapshot.py` | 并发双内容，败者 409 | no | 批次 1 |
| VF5 | scatter 在 `_material` 前预解析 identity（对齐 `:129-137`），或采纳后重算信封 | `acquisition_ingest.py` | child 失败 → `:retry` 不再 `INTAKE_SOURCE_MISSING` | no | 批次 1 |
| VF8 | admission/identity 对 deleted 同 key 409 零 Task，或显式复活协议 + 部分唯一 | `acquisition_ingest.py` `task_create.py` | delete 后再 ingest 同 key → 409、零新成功 Task | 可能部分唯一索引 | 批次 1 |
| VF17 | 图语义变化发 revision 2；保留 rev1 exact；补 persisted-DB upgrade fixture | `kind_family.py` `workflow_registry.py` | a608 风格 rev1 → HEAD 不再 503 | no（compat 行） | 批次 1 |
| VF6 | sealed full retry 从 frozen Snapshot 恢复，禁止在旧 actual 下重抓；若必须重抓则新 actual | `task_commands.py` `acquisition_ingest.py` `runtime_outcome.py` | HTTP 正文变 + retry → 冲突或新 actual，不得静默成功 | no | 批次 1 |
| VF3 | 观察占位与 Task INSERT 同 UoW；UNIQUE 映射 409；补 e2e | `task_create.py` | 同 observation 二次 409；并发至多一个 201 | 可能 reservation 表 | 批次 2 |
| VF7 | retry 复制 previous Execution `payload_extra` | `task_commands.py` | no_change Task `:retry` 仍走 no_change 步 | no | 批次 2 |
| VF15 | worker 只对明确 stale/lease/fence 重抛；domain Conflict 落 terminal failed；admission 或文档化「kind×strategy≠可达边」 | `worker.py` `runtime_materialize.py` | PDF+`doc.deterministic` → 失败 Task 而非永久 running | no | 批次 2 |
| VF16 | 仅当**当前 hop 的 compiled routes** 存在 reacquire 候选被拿掉时 409 | `runtime_materialize.py` | browser 起点 + 空正文不 409；static→reacquire 后仍 absent 落到已声明 clean | no | 批次 2 |
| VF18 | 从 `mkb_representation_facts` 取 fact_digest；与 `selected_output.py` 同一代数 | `runtime_materialize.py` | 生产行 digest ≠ 把 manifest 再哈希一次 | no | 批次 2 |
| VF22 | cancel/TTL 按 `owner_uuid` 或 pending token；ingest 只放本会话 | `object_upload_ttl.py` `acceptance_snapshot.py` `objects.py` | pending=2 → A cancel → pending=1 且 B 仍 live | 可能契约加 session id | 批次 2 |
| VF9 / VF11 | `resolve_rebuild(..., require_active=True)`；同态 lifecycle admission 409 零 Task；deactivated 再 ingest 409 或显式 reactivate 过渡 | `targets.py` `lifecycle_apply.py` `acceptance_snapshot.py` | 7×state HTTP 矩阵：非法格零 Task | no | 批次 2 |
| VF12 | 冻结 target 在执行前消失 → 409，禁止 SUCCESS 少 rebuild | `index_rebuild_plan.py` | team scope 跳过子集不得 succeeded | no | 批次 2 |
| VF10 | accept/publish 命令带 lifecycle epoch + row_revision CAS | `acceptance_snapshot.py` `vector_publish_commit.py` | delete × late accept 不得改墓碑 latest | 可能新列 | 批次 2 |
| VF28 | 所有 public nested extras 走 `assert_safe_public_data`；source dump 进 audit 前同样 | `models.py` `config_snapshots.py` | `source.payload_extra.api_token` → 422 | no | 批次 2 |
| VF20 | 闭集登记 `registered_api.map` 或删除映射并声明「采集侧非 clean 侧」；测试 sealed actual ⊆ 闭集 | `actual_s05.py` `strategies.py` | sealed `actual_clean_strategy` ∈ 注册表 | no | 批次 3 |
| VF31 | 守卫移到即将 POST 的 `moz:firefoxOptions.args`，或删除恒假守卫 | `browser.py` | 可变列表含 no-sandbox → 503 | no | 批次 3 |
| VF34 | GET Task 增加 bounded：kind / mode / declared+actual strategy / item uuid | `task_views.py` | 终态 GET 能读到 actual_clean_strategy | no | 批次 3 |
| VF36 | 无 child 时用 root/Task 终态映射 outcome | `task_projections.py` | succeeded 单 kind `/items` 非 active | no | 批次 3 |
| VF24 | reconcile 对 tombstoned+quarantine 调 destroy | `object_gc.py` | TX2 后 crash 再 scan，quarantine 文件消失 | no | 批次 3 |
| VF45 | 非 ingest 成功一律 `lifecycle_success` | `runtime_outcome.py` | rebuild succeeded 不进 indexed_success | no | 批次 3 |
| VF50 | 观察三态 409 e2e；hold 所有权；VF18 digest 断言 | `tests/e2e/test_nh1_nh9_review_fixes.py` 等 | 新测试修前 RED | no | 批次 3 |
| VF4 | 定义失败任务 observation 复用，或显式释放命令（本轮可只文档化 409 含义） | `scatter_intake.py` / docs | 失败后同 key 有合法出口或契约写明必须换 key | no | 批次 3 / 切分 |
| VF19 | 禁 indexed 行改身份列组合；selected-output append-only 可切到后续 | `024` 或新 migration | 先改 state 再改 digest abort | migration | 切分 |
| VF38 | 公开 view 放行 redacted `error_message`；debug 门控另开 | `runtime_outcome.py` `task_views.py` | GET Task 失败可见非固定文案 | no | 切分 |
| VF43 | 永久 outbox 错误终结 owner；requeue API 不进本批 | `runtime_outbox.py` `runtime_repair.py` | 未知 plan 8 次后 Task 非 queued 无 error | no | 切分 |
| VF49 | 改 `test_stale_fencing_fail_*` 期待 ConflictError / 新世代仍 running；legal-edge/process-kill 不进本批 | `test_ns6_phase2.py` | 该测试绿且仍证明新世代不被旧 fail 杀死 | no | 批次 3 |

### 5.3 批次 / 依赖

- **批次 1（正确性 / 升级）**：VF13 VF1 VF2 VF5 VF8 VF17 VF6 — 静默假账与升级 503，先做。
- **批次 2（第 1 轮名义修复 + 生命周期 admission）**：VF3 VF7 VF15 VF16 VF18 VF22 VF9 VF11 VF12 VF10 VF28 — 依赖批次 1 的 snapshot/identity 语义。
- **批次 3（读面 / 收尾 / 测试）**：VF20 VF31 VF34 VF36 VF24 VF45 VF50 VF49 — 不改观察身份。
- **切分（partial-fix 剩余）**：VF4 VF19 VF38 VF43 → §5.4。

### 5.4 承接登记（`[true-deferred]` + `[partial-delivery]` 剩余切片）

| V# | 归属类 / 来源 | 处置 | 后延原因 | reopen 触发器 | 承接位置 |
|----|--------------|------|----------|----------------|----------|
| VF14 | `[true-deferred]` | `defer-with-rationale` | S02-T009 未在 NH reopen | 上游 poll 到 cancelling→failed | S02 charter |
| VF21 | `[partial-delivery] 剩余切片` | `defer-with-rationale` | 公式已含 main_text_presence；离线双签名需 inventory | 离线证据对账失败 | 与 VF17 同批或 representation-path v2 |
| VF23 | `[partial-delivery]` 来源 NH-VF13 | `defer-with-rationale` | S13 大改；已登记 | GC 看到无 catalog 的 final 文件 | `deferred-items-ledger.md` `NH-VF13` |
| VF25 | `[true-deferred]` | `defer-with-rationale` | NH8 只承诺 logical delete | 磁盘因 delete 单调上涨 | retention / physical purge AP |
| VF26 | `[partial-delivery]` | `defer-with-rationale` | 四通道能经 public upload 接通；围栏非断链 | 非 upload 引用被当通道成功 | NH4 identity 补丁 |
| VF29 | `[true-deferred]` | `defer-with-rationale` | NS6 画像；Turso 单写者 | 多写者后端切换 | NS6 / constitution |
| VF30 | `[true-deferred]` | `deferred-by-owner` | 已披露 stub | owner 授权 subprocess/vLLM | `NH-VF14.r` |
| VF32 | `[true-deferred]` | `defer-with-rationale` | 默认 supply 非 required 是配置 | 生产打开 `runtime_supply_readiness_required` | deploy profile |
| VF33 | `[true-deferred]` | `defer-with-rationale` | S03 只读面不在 NH AP；禁 workflow_key 仍成立 | leaf-worker 发现 charter | S03 |
| VF35 | `[true-deferred]` | `defer-with-rationale` | namespace 强制是 Layer-A | 冷启动检索无法发现 key | 发现面 AP |
| VF37 | `[true-deferred]` | `defer-with-rationale` | 六态折叠有意 | fan-in 与 running 不可区分成事故 | Task view 增补 |
| VF39 | `[true-deferred]` | `defer-with-rationale` | 诊断表 reserved | 故障现场无法从 API 还原 | S15 debug |
| VF40 | `[true-deferred]` | `defer-with-rationale` | 目录闭集 ≠ emit 承诺 | 运维把死系列当覆盖 | S15 emit charter |
| VF41 | `[true-deferred]` | `defer-with-rationale` | admission 拒绝零记录是 fail-closed 副作用 | 需要拒绝审计 | security/obs |
| VF42 | `[true-deferred]` | `defer-with-rationale` | NS 预存；VF33 未覆盖此位点 | supervisor 空转 /ready 仍绿 | S15 |
| VF44 | `[true-deferred]` | `defer-with-rationale` | 幂等可工作，缺 applied/replay 字段 | 前端无法区分 | S02 |
| VF46 | `[true-deferred]` | `defer-with-rationale` | 低优先级投影 | noop 被当成真实 rebuild | Task view |
| VF47 | `[true-deferred]` | `defer-with-rationale` | fail-loud 正确性优先 | 需要独立 commit 诊断 | 与 VF38 debug 同 charter |
| VF48 | `[true-deferred]` | `defer-with-rationale` | 单进程部署模型 | 多节点 data_dir 分裂 | ops |
| VF51 | `[true-deferred]` | `defer-with-rationale` | 历史双轨 | 新 4xx 一律 SCREAMING | 错误码 charter |
| VF4.r | `[partial-delivery] 剩余切片` | `defer-with-rationale` | 本轮可先文档化 409；复用原坐标需产品法 | 失败后同 key 无法补齐成为事故 | 与 VF3 同批观察法 |
| VF19.r | `[partial-delivery] 剩余切片` | `defer-with-rationale` | selected-output/artifact append-only 需 migration | 普通 SQL 改 selection 被当证据 | `NH-VF4.r` 扩展 |
| VF38.r | `[partial-delivery] 剩余切片` | `defer-with-rationale` | process/stage/facts API 与 payload debug 门控 | 前端无法回答「卡在 decode」 | S15 v2 |
| VF43.r | `[partial-delivery] 剩余切片` | `defer-with-rationale` | requeue / kill / restart 不进本批 | dead 只能人工 SQL | internal ops |
| VF49.r | `[partial-delivery] 剩余切片` | `defer-with-rationale` | graph-derived legal cells + process kill | 已登记 `NH-VF27.r` / `NH-VF42` | NH9 rereview |

> **`[true-bug]` 不出现在本表。**

---

## 6. 处置执行回填（fixes 落地后 · append-only）

> 本工作流本轮**不执行代码修复**（任务止于 UF 汇聚 → 核实 → VF 注入 → 文档一致性 → AGENT 评价）。本节保持空，直到另一次修复会话按 `code-review-respond` append。

### 6.1–6.5

pending（非本轮范围）

---

## 7. AGENT 评审绩效

> 评价对象: `NH1–NH9 第 2 轮四份独立审查（GPT / Grok / v4f / GLM-5.3-Flash）`
> 评价人: `Grok`（实现者 / 合并人；以 §3 VF 判定为事后标准）
> 评价时间: `2026-08-31`

---

### 0. 评价结论

- **一句话评价**：四方都独立把第 1 轮若干 `fixed` 打回名义修复，价值最高的新洞来自 GPT（终态 Outcome / 升级 503）与 GLM（scatter 信封时序）；Grok 的校准最好（T-O / S01 / S15 把目录 API 和 timeline payload 从 blocker 里拿掉）；v4f 覆盖面最宽但把缺 GET `/workflows` 升到 critical 过称。
- **最佳AGENT**：`Grok`
- **最高价值 Finding**：`VF13`（GPT-R1：终态 Execution 仍接受迟到 Outcome 并推进）——这是唯一被坐实的「FAILED 后仍前进」状态机断裂。并列接近：`VF1`（v4f-R1 / GPT-R3 单通道悬挂账）与 `VF5`（GLM-R1 scatter retry 死路）。

---

### 1. Findings 质量清点

> 事后判定取 §3 VF verdict。质量：能独立复现、根因正确、严重级不过称 = `excellent`；主项真但范围/严重级漂 = `good`/`mixed`；被驳回或过称 blocker = `weak`。

| AGENT | 问题编号 | 原始严重程度 | 事后判定 | Finding 质量 | 分析与说明 |
|---------|----------|--------------|----------|--------------|------------|
| GPT | VF13 ← R1 | critical | true-positive | `excellent` | 独家。代码路径坐实；最小反例叙事完整。本轮最高价值 |
| GPT | VF17 ← R2 | critical | true-positive | `excellent` | 把已 defer 的 NH-VF21 从「潜在雷」推进到可复现升级 503；指出第 1 轮仍改了 rev1 |
| GPT | VF1 ← R3 | critical | true-positive | `excellent` | 与 v4f-R1 同根；GPT 用 Task 计数复现「两 Task 成功、一 Snapshot」 |
| GPT | VF6/VF5 ← R4 | critical | true-positive / partial | `good` | 一条 R 含 HTTP 重抓与 API retry 两根因；拆成 VF6+VF5 后都成立 |
| GPT | VF15 ← R5 | high | true-positive | `good` | worker 把 domain Conflict 当 fence 是真洞；「caller 不得点名 strategy」相对 Q2-B 偏政策 |
| GPT | VF3 ← R6 | high | true-positive | `excellent` | 无 worker 时双 201 的最小复现打穿「admission 已查重」叙事 |
| GPT | VF33 ← R7 | high | partial | `mixed` | S03 只读面缺失为真；把 ProcessCapabilityManifest 升 NH blocker 过称 |
| GPT | VF23 ← R8 | high | true-positive | `excellent` | 不存在 Team 上传留下 final CAS；NH-VF13 的实弹 |
| GPT | VF22 ← R9 | medium | true-positive | `good` | 与 Grok/GLM 同根；session identity 建议可执行 |
| GPT | VF18/VF19 ← R10 | high | true-positive / partial | `good` | fact 假字段 excellent；「整个 evidence plane 可改」过称（024 已护 fact/history） |
| GPT | VF28 ← R11 | high | true-positive | `excellent` | nested `payload_extra.api_token` 绕过 root 拒密；envelope 去正文应标为 VF3.r 切片 |
| GPT | VF29 ← R12 | high | partial | `mixed` | 现象真，但是 NS6 预存 + 测试锁成正期待；升 NH blocker 过称 |
| GPT | VF30 ← R13 | high | owner-gated | `mixed` | 诚实描述 stub/glyph；升本轮 blocker 违反已登记 `NH-VF14.r` |
| GPT | VF11/VF38/VF43 ← R14 | medium | partial | `mixed` | 大篮子：lifecycle no-op、读面、dead outbox 不终结 owner 应拆 |
| GPT | VF24 ← R15 | medium | true-positive | `good` | post-tombstone 窗与 v4f/GLM 一致 |
| GPT | VF49 ← R16 | medium | partial | `mixed` | HEAD 红灯 `test_stale_fencing_fail_*` 是真欠账；把 legal-edge/process-kill 再当 blocker 重复 NH-VF27.r |
| GPT | VF10 ← R17 | high | true-positive | `good` | epoch 缺失属实；触发是竞态边 |
| Grok | VF16 ← R1 | high | true-positive | `excellent` | 独家。第 1 轮 VF26 修错范围；T-O-388 产品例对齐；建议按当前 hop 执法 |
| Grok | VF8 ← R2 | high | true-positive | `excellent` | 独家。二次 HTTP delete 与同 key 再 ingest 分格，避免误伤已成立的 409 |
| Grok | VF3 ← R3 | high | true-positive | `excellent` | 点出零测试使第 1 轮 `self-claimed-only` 不能升 fully-fixed |
| Grok | VF22 ← R4 | high | true-positive | `excellent` | 「最新一条 ≠ 调用者那一条」一句话钉死 VF12 under-delivery |
| Grok | VF34 ← R5 | high | true-positive | `excellent` | 明确「缺 GET /workflows 不是 blocker、GET Task 无绑边才是」。本轮校准标杆 |
| Grok | VF11 ← R6 | high | true-positive | `excellent` | rebuild×deactivated 与同态 lifecycle 201 分格清楚 |
| Grok | VF14 ← R7 | high | true-positive | `good` | S02-T009 对照正确；自评 non-blocking 与本台账 true-deferred 一致 |
| Grok | VF7 ← R8 | high | true-positive | `excellent` | retry 丢 `payload_extra` 独家、可执行 |
| Grok | VF36 ← R9 | medium | true-positive | `excellent` | 与 GLM 同根；scatter 投影套到 single 的口径裂缝 |
| Grok | VF18 ← R10 | medium | true-positive | `good` | 严重级比四方最严（high）更准——路由功能仍 exactly-one |
| Grok | VF45 ← R11 | medium | true-positive | `good` | VF25 剩余切片准确 |
| Grok | VF19 ← R12 | medium | true-positive | `good` | 改 state 再改 digest；不把 024 说成完全无效 |
| Grok | VF26 ← R13 | medium | true-positive | `good` | 围栏缺口 vs 没接线，分寸对 |
| Grok | VF31 ← R14 | low | true-positive | `excellent` | 严重级最准：无生产泄漏，不能算 fully-fixed |
| Grok | VF12 ← R15 | medium | true-positive | `good` | VF9.r cardinality |
| Grok | VF15 ← R16 | low | true-positive | `good` | 求交粗于图边；不把它写成 VF1 回潮 |
| v4f | VF1 ← R1 | critical | true-positive | `excellent` | 悬挂 change-set + 丢 fact 的静态路径最完整 |
| v4f | VF2 ← R2 | high | true-positive | `excellent` | 独家 LWW；对照 metadata CAS |
| v4f | VF18 ← R3 | high | true-positive | `excellent` | 双公式漂移比「字段缺失」叙事更准 |
| v4f | VF20 ← R4 | high | true-positive | `good` | `.map` 泄漏为真；blocker 过严（公开契约无 clean_strategy） |
| v4f | VF25 ← R5 | high | true-positive | `good` | 物理释放缺口真；相对 NH8 logical-delete 应标 deferred |
| v4f | VF9 ← R6 | high | true-positive | `excellent` | 假账 active→active 钉得死 |
| v4f | VF15 ← R7 | high | true-positive | `good` | 晚期 409 为真；未看到 worker 吞 Conflict 的 running 形态（GPT 更深） |
| v4f | VF33 ← R8 | critical | partial | `weak` | 缺目录端点 valid；升 critical /「分类目标面 blocker」相对 T-O-379 过称 |
| v4f | VF35 ← R9 | high | true-positive | `mixed` | 列表维残缺为真；high 对未承诺发现面偏高 |
| v4f | VF38 ← R10 | high | partial | `mixed` | 数据在库里读不出为真；忽略 S15-T050 digest-only |
| v4f | VF39 ← R11 | high | true-positive | `mixed` | DiagnosticSink 写入极少为真；「全系统只有一处」相对 construct 调用过绝对 |
| v4f | VF40 ← R12 | high | true-positive | `good` | 死目录描述准；high 对 S15 未承诺 emit 偏高 |
| v4f | VF41 ← R13 | medium | true-positive | `good` | admission 零记录 |
| v4f | VF38 ← R14 | high | true-positive | `good` | 与 R10 同簇，stage 视角 |
| v4f | VF35 ← R15 | high | true-positive | `good` | 与 R9 同簇 |
| v4f | VF43 ← R16 | high | partial | `mixed` | 无 requeue 为真；bounded v1 已自认 empty |
| v4f | VF3 ← R17 | medium | true-positive | `good` | TOCTOU；严重级比 GPT/Grok 的 high 更接近 edge |
| v4f | VF24 ← R18 | medium | true-positive | `excellent` | 收尾窗精确 |
| v4f | VF27 ← R19 | low | by-design | `good` | 自认边界；本台账 acknowledge |
| v4f | VF52 ← R20 | low | stale-rejected | `weak` | 自标 [未验证] 却仍进 finding 表；上限实际存在 |
| v4f | VF38 ← R21 | medium | true-positive | `good` | stage_report 读面 |
| v4f | VF47 ← R22 | medium | true-positive | `good` | fail-loud 的观测背面，不否定 VF24 正确性 |
| v4f | VF44 ← R23 | medium | true-positive | `good` | |
| v4f | VF41 ← R24 | low | true-positive | `good` | |
| v4f | VF21 ← R25 | medium | true-positive | `good` | 公式变更；「离线必炸」未验证 |
| v4f | VF11 ← R26 | medium | true-positive | `good` | 与 Grok-R6 同根 |
| v4f | VF32 ← R27 | medium | by-design | `mixed` | 默认全开门是配置；与 VF15 方向相反的取舍 |
| v4f | VF48 ← R28 | medium | by-design | `good` | |
| v4f | VF16 ← R29 | low | true-positive | `good` | 回旋失真是 Grok-R1 的观测面 |
| v4f | VF11 ← R30 | low | true-positive | `good` | |
| v4f | VF46 ← R31 | low | true-positive | `good` | |
| v4f | VF41 ← R32 | low | true-positive | `good` | |
| GLM | VF5 ← R1 | high | true-positive | `excellent` | 独家机制（信封 vs 回调时序）+ 探针实证 retry `INTAKE_SOURCE_MISSING`。本轮通道④最深 |
| GLM | VF4 ← R2 | high | true-positive | `good` | 409 守卫本身正确；「永久无法补齐」是产品法缺口，不是预查写错 |
| GLM | VF18 ← R3 | high | true-positive | `excellent` | 「字段存在、值错误、零测试」比「字段缺失」更准确 |
| GLM | VF38 ← R4 | high | partial | `mixed` | 固定 error_message 为真；「任何接口都不能回答失败原因」过绝对（error.code 仍在） |
| GLM | VF40 ← R5 | high | true-positive | `good` | 亲跑 grep 零 emit；ALERT 永不触发 |
| GLM | VF31 ← R6 | medium | true-positive | `excellent` | 与 Grok 同根；「假修复」定性准 |
| GLM | VF22 ← R7 | medium | true-positive | `good` | 严重级比 Grok high 更接近窗口伤害 |
| GLM | VF42 ← R8 | medium | true-positive | `good` | supervisor 静默独家 |
| GLM | VF43 ← R9 | medium | true-positive | `good` | 只读 dead-outbox 差一个 requeue |
| GLM | VF36 ← R10 | medium | true-positive | `excellent` | TestClient 实测 succeeded→active |
| GLM | VF37 ← R11 | medium | true-positive | `good` | waiting 折叠；六态有意收窄 |
| GLM | VF35 ← R12 | medium | true-positive | `good` | namespace 冷启动；连官方测试直读表 |
| GLM | VF5 ← R13 | medium | true-positive | `good` | 与 R1 同根，不另开编号是对的 |
| GLM | VF24 ← R14 | medium | true-positive | `good` | VF11 残余，不否定主修复 |
| GLM | VF39 ← R15 | medium | true-positive | `mixed` | 形同虚设为真；行号 `:1277/:1371` 陈旧 |
| GLM | VF33 ← R16 | medium | true-positive | `good` | 发现面缺失不升 critical，校准优于 v4f |
| GLM | VF26 ← R17 | low | true-positive | `good` | |
| GLM | VF50 ← R18 | medium | true-positive | `excellent` | 点穿第 1 轮 §6.5 覆盖夸大；同时承认探针语义正确 |
| GLM | VF38 ← R19 | medium | true-positive | `good` | 解释性三表无 API |
| GLM | VF51 ← R20 | low | true-positive | `good` | 双轨历史包袱 |
| GLM | VF44 ← R21 | low | true-positive | `good` | |

---

### 2. 多维度评分 - 单向总分 10 分

| AGENT | 总分 | 证据链完整度 | 判断严谨性 | 修法建议可执行性 | 协作友好度 | 找到问题的覆盖面 | 严重级别准确度 |
|---------|------|------|------|------|------|------|------|
| Grok | **8.2** | 8.5 | 9.0 | 8.0 | 8.5 | 7.0 | 8.5 |
| GLM-5.3-Flash | **7.6** | 8.5 | 7.5 | 8.0 | 8.0 | 7.0 | 7.0 |
| GPT | **7.4** | 9.0 | 6.0 | 8.0 | 7.5 | 8.5 | 5.5 |
| v4f | **6.9** | 8.0 | 5.5 | 7.0 | 7.0 | 9.0 | 5.0 |

#### 逐 AGENT 评分说明

- **Grok（8.2，最佳）**：静态审查但每条主路径都重新 Read；§4 OOS 表主动降噪（GET `/workflows`、timeline digest-only、stub 不当 fake-green）。漏了 VF13 终态 Outcome 与 VF5 信封时序两条最重生产洞，覆盖面因此不是最高。严重级整体最准（VF18/VF31 降到 medium/low 被本台账采纳）。
- **GLM-5.3-Flash（7.6）**：唯一亲跑 review-fixes + 临时探针证明通道④ retry 死路；对第 1 轮 24 项 `fixed` 给出「约 20 真 / 2 假 / 1 降级」的可核对账。DiagnosticSink 行号陈旧；未打到 VF13/VF17/VF8。把通道④恢复链定为比第 1 轮任何 finding 都重——对 scatter 成立，但不能覆盖单通道悬挂账与状态机。
- **GPT（7.4）**：证据最强（临时库/TestClient 反例表、OpenAPI、升级 digest）。独家 VF13/VF17 改变本轮必修清单。扣分全在严谨性：把已登记 defer 的 stub、NS6 concurrent_writes、S03 发现面、NH9 process-kill 再打成关闭前 blocker，导致「13 个 blocker」膨胀。R4/R10/R14 大篮子需要合成人拆分。
- **v4f（6.9）**：覆盖面最大（32 条），VF1 change-set 悬挂与 VF2 LWW 是单通道账本最细的静态解剖。扣分在严重级：R8 目录接口 critical 与 T-O-379 冲突；大量观测面 high 未对照 S15-T050 / bounded v1。R20 自标未验证仍进结论表。子代理 DAG 声明清楚，主审二次验证后才采纳，协作态度好。

**漏报对照（相对本轮 VF true-bug）**

| 本轮 true-bug | GPT | Grok | v4f | GLM |
|---------------|-----|------|-----|-----|
| VF13 终态 Outcome | **独家** | 漏 | 漏 | 漏 |
| VF17 升级 503 | **独家** | 漏（遵守 NH-VF21，未追第 1 轮仍改图） | 漏 | 漏（明确「遵守升号 defer」） |
| VF5 scatter 信封 | R4 切片 | 漏 | 漏 | **独家主项** |
| VF1 悬挂 Snapshot | R3 | 漏 | **R1 最细** | 漏 |
| VF8 tombstone 再 ingest | 漏 | **独家** | 漏 | 漏 |
| VF16 reacquire 过宽 | 漏 | **独家** | R29 观测面 | 漏（把 VF26 判 fully-fixed） |

---

### 3. 对后续 rereview 的使用建议

- 修复后的第 3 轮优先复验 **VF1 / VF5 / VF6 / VF8 / VF13 / VF16 / VF17 / VF18 / VF22**，要求 falsifiable 测试，禁止再接受「字段存在即 fixed」。
- 不要把 S03 `/v1/workflows`、真模型、process-kill 重新混进 NH DoD；Grok 的 O 表应作为范围闸。
- GPT 的最小反例表应保留为回归种子（terminal Outcome、upgrade digest、same key different body、uncatalogued CAS）。

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `v0.1` | `2026-08-31` | `Grok` | **Step-1**：4 方 86 条原始 finding → 52 条 UF 汇聚台账；不填 VF |
| `v0.2` | `2026-08-31` | `Grok` | **Step-2/3**：对照 HEAD `ba099ee` 逐条核实并注入 VF1–VF52、§4 汇总、§5 初步修法；状态仍 `triaged`；未修代码；未写 AGENT 评价 |
| `v0.3` | `2026-08-31` | `Grok` | **Step-4**：对齐 §1/§3/§4 计数（verdict/severity/fix=25 含 VF6）；修复 VF14 表管道符拆列；纠偏 file:line（DiagnosticSink、outbox dead、namespace、actual_s05 路径） |
| `v0.4` | `2026-08-31` | `Grok` | **Step-5**：按 `code-review-eval.md` 写入 §7；最佳 AGENT=Grok（8.2）；最高价值 Finding=VF13（GPT-R1） |
