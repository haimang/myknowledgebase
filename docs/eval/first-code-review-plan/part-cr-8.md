# Nano-Agent 代码审查报告 — CR-8 · 入口与端到端贯通 + 测试有效性(收尾簇)

> 审查对象: `apps/worker` + `apps/api`(装配)+ `apps/cli` + search 端到端 + `tests/`(15 文件)+ 全程序级收口
> 审查类型: `code-review | mixed（端到端 + 测试 + 跨簇综合）`
> 审查时间: `2026-05-31`
> 审查人: `Claude (Opus 4.8) 主审 + 2 个 sub-agent（Face A 端到端装配、Face B 测试假绿核查）`
> 审查范围:
> - `apps/worker/src/smind_worker/main.py`、`apps/api/src/smind_api/{main,deps}.py`、`apps/cli/src/smind_cli/main.py`、`apps/api/routes/search.py`
> - search 链:route → `management/service.py`(SearchService 装配)→ `rag_vectorizer/search.py` → `vector_sqlite_vec/store.py` → core.db hydration(`v_search_hydration`)
> - `tests/`(integration p1–p7 + smoke + fixtures;unit/e2e 空)
> 对照真相:
> - `docs/refactor/index.md`(§5.7 检索路径、§7.1 事务)、`docs/eval/first-code-review-plan/index.md`(§1 口径、§7.4 测试纳入)
> - `docs/closure/initial-refactor/P3–P7-closure.md`(`14 passed` claim)
> - `part-cr-1.md ~ part-cr-7.md`(前 7 簇结论,本簇综合)
> 文档状态: `changes-requested`

---

## 0. 总结结论

- **整体判断**：`端到端"管道"装配基本接得上(ingestion→clean→rag→vectorize→search 各环节都能返回结构化结果),但"名义跑通、语义为空":worker 漏装 reap 致任一中断即死锁,embedding 是伪向量致检索无意义;且测试套件是结构性假绿,系统性掩盖了前 7 簇的全部 blocker。整个 P0–P7 不具备"已完成"的实质。`
- **结论等级**：`changes-requested`（实质 blocked）
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 3 个判断（均经主审实测）**：
  1. **测试是结构性假绿**：`tests/` 实为 **20 个测试函数**(非 closure 反复声称的 `14 passed`),`tests/unit`/`tests/e2e` 全空,无一条安全/并发/时间格式/向量真实性/语义断言;并有**夹具手写正确时间戳绕过 now_iso bug** 的确凿掩盖证据。
  2. **端到端名义通、语义空**:链路各环节都接得上并返回结果,但 ① worker 漏装 `reap_expired_claims`(G-CR4-01)→ 任一 worker 中断即对该文档死锁;② embedding 是 SHA-256 伪向量(G-CR7-01)→ 即便全程跑通,search 返回的相似度是哈希噪声。
  3. **closure 绿是无效证据**:P3–P7 五份 closure 复制粘贴同一句 `14 passed`(计数本身就陈旧错误),据此宣称的 vector/retrieval/cutover ✅ PASS 不能作为闭环有效证据。
- **附带纠偏(本簇复核确认)**：附录 **A1(stage 命名断点)再次证伪** —— worker 派发 `startswith("clean")`/`startswith("rag:")` 与实际 stage 字符串匹配,链路可路由。

---

## 1. 审查方法与已核实事实

- **核查实现**：上述 apps 装配 + search 链 + 15 个测试文件全读。
- **执行过的验证(主审亲测)**：
  - 测试函数计数:`grep -rc "def test_" tests/integration tests/smoke` → **20**(P5=2/P3=3/P1=2+2/P7=1/P4=2/P6=1/P2=3/smoke=4),与 closure 的 `14 passed` 不符。
  - `tests/unit/.gitkeep`、`tests/e2e/.gitkeep` —— 两目录**无实测文件**。
  - 夹具掩盖:`test_kernel_flow.py:75-83` 在调 `reap_expired_claims` 前 `UPDATE task_claims SET lease_expires_at = strftime('%Y-%m-%dT%H:%M:%fZ','now','-1 second')`(SQL 正确格式),**绕过** `now_iso()` 写入路径。
  - `grep "14 passed" docs/closure` → P3/P4/P5/P6/P7 五份**同句复制**。
- **执行过的验证(sub-agent)**：search 链装配追踪、端到端链路逐环判定、13 个测试文件断言强度分级、7 类 blocker 假绿归因。
- **复用 / 对照的既有审查**：part-cr-1~7 全部 —— 本簇为综合层,引用各 G-CRx-xx 编号,不重复深挖业务内部。

### 1.1 已确认的正面事实

- **端到端管道接得上**:ingestion 建 `stage='clean'` step → worker `startswith("clean")` 匹配 claim → clean 建 `rag:structurize` step → `startswith("rag:")` 匹配 → structurize→construct→(内联)vectorize → search route→SearchService→store.search→`v_search_hydration` 出结果。各环节装配正确、stage 命名匹配。
- **search 装配正确**:SearchService(`rag_vectorizer/search.py:12`)由 ManagementService 装配,`workspace_key=team_id` 在索引侧(`ns_{team_id}`)与查询侧一致;route 经 `get_auth_context`+`require_team` 鉴权;debug 端点 candidate/hydrated/filtered 计数自洽。
- **hydration 正确**:`v_search_hydration` + post-filter(要求 vec_status='vectorized' 且 doc active)在 rag 完成后满足,读路径不脏读(承接 CR-3 正面结论)。
- **worker 单连接事务连续性**:restart→purge→claim 复用单连接保证串行一致(承接 CR-4 正面)。

### 1.2 已确认的负面事实

- worker 主循环漏装 reap(G-CR4-01 的装配层确认)。
- embedder 伪向量使整条 search 链语义为空(G-CR7-01 的 E2E 确认)。
- API/CLI 每次请求/调用新建连接且不关闭(G-CR2-01 的 app 级确认)。
- API 无 lifespan / CORS / 全局异常处理;`/healthz` 是静态假健康检查。
- 测试 20 函数全部为弱/空洞/桩固化断言;unit/e2e 空;closure `14 passed` 计数陈旧且五份复制。
- 多处测试固化桩输出(p3 `text=="raw-file-content-123"`),会**阻碍后续修复**(接真实实现即破)。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | apps 装配 + 15 测试文件 + closure 逐处核行号 |
| 本地命令 / 测试 | yes | 测试函数计数、unit/e2e 空、夹具掩盖 SQL、closure 复制 均主审实测 |
| schema / contract 反向校验 | yes | search 链 ↔ v_search_hydration;stage 字符串 ↔ worker 派发 |
| live / deploy / preview 证据 | n/a | — |
| 与上游 design / QNA 对账 | yes | closure `14 passed` vs 实际 20;index §7.4 测试纳入口径 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 测试结构性假绿:20 函数全弱/空洞,unit/e2e 空,无正确性断言 | critical | test-gap | yes | 重建测试:语义/并发/安全/时间/向量真实性断言 |
| R2 | 夹具手写正确时间戳绕过 now_iso bug + reap 死代码被孤立单测掩盖 | critical | test-gap | yes | reap 测试走真实 now_iso 写入路径;worker 接线 reap |
| R3 | worker 漏装 reap → 任一 worker 中断即对该文档死锁(E2E) | high | correctness / D | yes | `_run_once` 接线 reap(承接 G-CR4-01) |
| R4 | embedding 伪向量 → 端到端语义为空(E2E) | critical | correctness / B | yes | 接真实 embedding(承接 G-CR7-01) |
| R5 | closure `14 passed` 陈旧且五份复制,vector/retrieval/cutover ✅ 为无效证据 | high | docs-gap | yes | closure 重新定级,以真实断言为证据 |
| R6 | API/CLI 连接每次新建不关闭(app 级) | medium | correctness / C | no | generator 依赖 + close(承接 G-CR2-01) |
| R7 | API 无 lifespan/CORS/全局异常处理;/healthz 假健康 | medium | delivery-gap / D | no | 加 lifespan(启动自检)、CORS、exception handler、真 healthz |
| R8 | 测试固化桩输出(p3 等值断言),阻碍后续修复 | medium | test-gap | no | 改为语义属性断言,接真实实现时同步重写 |
| R9 | worker 无优雅退出(SIGTERM/KeyboardInterrupt),退出留 running claim | low | correctness | no | 退出前 reap + close |

### R1. 测试结构性假绿:20 函数全弱/空洞,unit/e2e 空,无正确性断言

- **严重级别**：`critical` · **类型**：`test-gap` · **blocker**：`yes`
- **事实依据**：
  - 主审实测:integration+smoke 共 **20 个 `def test_`**;`tests/unit`、`tests/e2e` 仅 `.gitkeep`。
  - 断言模式普遍为 `status_code==200`、`len(items)>=N`、`text.strip()!=""`、`x is not None`、断言桩恒等输出。无安全/并发/时间格式 round-trip/vec0 真实性/embedding 语义/崩溃恢复断言。
- **为什么重要**：测试只证明"管道能流转、返回非空",不证明"行为正确"。这正是前 7 簇 blocker 能全部潜伏却显示绿色的根本原因。
- **审查判断**：test-gap,blocker。owner 决策 #4 的核心确认。
- **建议修法**：分层重建 —— 语义相关性断言(相关 chunk 排序靠前)、并发竞态(双 worker + 过期租约)、安全(路径遍历拒绝)、时间格式 round-trip、vec0 虚拟表真实性、崩溃恢复;补 unit/e2e。

### R2. 夹具手写正确时间戳绕过 now_iso bug + reap 死代码被孤立单测掩盖

- **严重级别**：`critical` · **类型**：`test-gap（夹具掩盖）` · **blocker**：`yes`
- **事实依据**：
  - `test_kernel_flow.py:75-83`:调 `reap_expired_claims` 前 `UPDATE task_claims SET lease_expires_at = strftime('%Y-%m-%dT%H:%M:%fZ','now','-1 second')` —— 用 SQLite strftime(正确格式)手写覆盖,**绕过** `claim_next_step` 经 `now_iso()`(畸形)的真实写入路径。
  - 该测试用 `action='mock'` 不执行步骤体,故也不触发执行器自提交副作用(掩盖 G-CR4-03)。
- **为什么重要**：这一处夹具同时掩盖三个 blocker:① reap 在 worker 运行时是死代码(G-CR4-01)—— 测试孤立调用 reap 制造"reap 有效"假象;② now_iso 时间格式缺秒(G-CR4-02/G-CR1-01)—— 手写正确格式绕过;③ 双重执行(G-CR4-03)—— mock 不触发副作用。
- **审查判断**：本次审查最强的"夹具掩盖"证据(主审逐行核实)。测试证明的是"若格式正确且有人调 reap 则有效",而非"系统会自动回收过期租约"。
- **建议修法**：reap 测试让 claim 用真实 `now_iso()` 写 lease(极小 lease_seconds + 冻结时钟),禁止手写 SQL 覆盖;新增 worker 循环调用 reap 的集成断言;过期竞态测试用真实执行器。

### R3. worker 漏装 reap → 任一 worker 中断即对该文档死锁

- **严重级别**：`high` · **类型**：`correctness / D` · **blocker**：`yes`
- **事实依据**：`apps/worker/main.py:35-57` `_run_once` 序列无 `reap_expired_claims`;该函数仅在 `__init__.py` 导出。承接 G-CR4-01。
- **为什么重要**：E2E 视角 —— worker 崩溃/超时后,其 claim 永久 active、step 永久 running,`ux_task_claims_active_step` 阻止再 claim → 该文档流水线死锁。
- **审查判断**：装配层 blocker(实现了 reap 却忘了在主循环装配)。
- **建议修法**：`_run_once` 开头接线 `reap_expired_claims(core_conn)`(须先修 G-CR4-02 时间格式,否则不命中)。

### R4. embedding 伪向量 → 端到端语义为空

- **严重级别**：`critical` · **类型**：`correctness / B` · **blocker**：`yes`
- **事实依据**：索引侧(`workflow_rag/service.py:167 embed_text`)与查询侧(`search.py:40 embed_text`)同一伪向量函数(`embedder.py:6` SHA-256 链)。store.search 暴力 cosine 可运行、对相同文本自匹配,但跨文本相似度是哈希噪声。承接 G-CR7-01。
- **为什么重要**：这是"名义跑通、语义为空"的根因 —— 端到端链路完整、能返回结果,但结果无任何检索意义。
- **审查判断**：交付级 blocker。
- **建议修法**：接入真实 embedding provider;伪向量仅可作显式标注的测试桩,不计入交付。

### R5. closure `14 passed` 陈旧且五份复制,✅ PASS 为无效证据

- **严重级别**：`high` · **类型**：`docs-gap` · **blocker**：`yes`
- **事实依据**：实际 20 测试函数;`14 passed` 在 P3/P4/P5/P6/P7 五份 closure 逐字复制(计数未随测试增量更新);据此宣称 vector gate/retrieval gate/cutover gate ✅ PASS。
- **为什么重要**：closure 是"已完成"的权威声明,但其证据(回归计数)既陈旧又无正确性内涵 —— 把假绿当成收口依据。
- **审查判断**：docs-gap,blocker(影响"是否已完成"的判定)。
- **建议修法**:closure 的 vector/retrieval/cutover gate 重新定级为 degraded/未达;以真实断言(语义/真实性)为证据,而非计数。

### R6. API/CLI 连接每次新建不关闭(app 级)

- **严重级别**：`medium` · **类型**：`correctness / C` · **blocker**：`no`
- **事实依据**：`deps.py:33-42` return 型依赖无 yield/close;`cli/main.py:11-21` `_service()` 每次新建 core+vec 连接不关闭。承接 G-CR2-01。
- **建议修法**：generator 依赖 `try: yield finally: close`;CLI 用 contextlib.closing。

### R7. API 无 lifespan/CORS/全局异常处理;/healthz 假健康

- **严重级别**：`medium` · **类型**：`delivery-gap / D` · **blocker**：`no`
- **事实依据**：`main.py:15-44` 无 lifespan/on_event、无 CORSMiddleware、无 exception_handler;`/healthz` 返回静态 `{"status":"ok"}`,不探测 DB/向量库。
- **建议修法**：加 lifespan(启动迁移+连接自检)、CORS、统一异常处理;healthz 实际探测。

### R8. 测试固化桩输出,阻碍后续修复

- **严重级别**：`medium` · **类型**：`test-gap` · **blocker**：`no`
- **事实依据**：`p3_clean_pipeline:114` `payload["text"]=="raw-file-content-123"`、`:149` `=="api-payload-xyz"` 把 strip 桩的恒等输出钉死为"正确";接真实清洗即破,须同步重写。
- **建议修法**：改为断言清洗后语义属性(去标签/保留正文),而非等值原始输入。

### R9. worker 无优雅退出

- **严重级别**：`low` · **类型**：`correctness` · **blocker**：`no`
- **事实依据**：`run_worker` 非 once 模式 `while True` 无信号处理;崩溃退出不 reap 不 close,留 running claim(放大 R3)。
- **建议修法**：SIGTERM/KeyboardInterrupt 处理,退出前 reap + close。

---

## 3. In-Scope 逐项对齐审核

> 计划项来自 index §3 CR-8 关注 + §7.4 测试纳入。

| 编号 | 计划项 | 审查结论 | 说明 |
|------|--------|----------|------|
| S1 | worker 主循环 stage 派发 | `partial` | 派发匹配正确(A1 证伪);但漏装 reap(R3) |
| S2 | restart/purge 消费顺序 | `done` | 顺序正确(承接 CR-4);批量单事务问题归 G-CR4-12 |
| S3 | search 端到端(embed→vec→hydrate) | `partial` | 装配/hydration 正确;embedding 伪向量致语义为空(R4) |
| S4 | CLI 命令面 | `partial` | health/search/ops-health 可用;连接不关闭(R6) |
| S5 | API 装配(lifespan/中间件/healthz) | `missing` | 无 lifespan/CORS/异常处理;假 healthz(R7) |
| S6 | 测试有效性 / 假绿核查(owner #4) | `done`(已核实=假绿) | 20 函数全弱;夹具掩盖;closure 计数陈旧(R1/R2/R5/R8) |
| S7 | A1 stage 命名(附录) | `done`(已核实=证伪) | 实际匹配,非 bug |

### 3.1 对齐结论

- **done**: `3`(S2、S6、S7)
- **partial**: `3`(S1、S3、S4)
- **missing**: `1`(S5)
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 它更像"管道装配接得上但故障恢复缺装(reap)、语义层为空(伪向量)、且测试无法证明任何正确性",而非 completed。

### 3.2 stub / 真实现标定表(index §7.1)

| 符号 | 标定 | 依据 |
|------|------|------|
| `apps/worker.run_worker/_run_once` | 真实现(漏装 reap) | R3 |
| `apps/api.create_app` | 真实现(无 lifespan/中间件) | R7 |
| `apps/api.deps.get_core_conn/get_vec_conn` | 真实现(连接泄漏) | R6 |
| `apps/cli.main` | 真实现(连接不关闭) | R6 |
| search 链(route→SearchService→store→hydration) | 真实现(语义空) | R4,装配对、向量伪 |
| `tests/`(20 函数) | 部分(弱/空洞/桩固化) | R1/R2/R8;unit/e2e 缺失 |

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 各业务簇内部逻辑(claim/retry/clean action/rag/向量) | `遵守` | 本簇只审装配+贯通+测试,引用 G 编号不重复深挖 |
| O2 | G-CR4-01/02/03、G-CR7-01、G-CR3-02 根因修复 | `遵守(归属各簇)` | 本簇做 E2E/测试层确认,根因修法在原簇 |
| O3 | A1 附录候选 | `已关闭(证伪)` | 复核确认非 bug |

### 横切维度 C1–C5 对 CR-8 的逐项结论

| 维度 | 结论 | 证据 |
|------|------|------|
| C1 事务与并发 | `partial` | worker 单连接事务连续(正面);无并发测试覆盖竞态(R1) |
| C2 错误处理 | `fail` | API 无全局异常处理(R7);测试不验错误路径 |
| C3 一致性 | `partial` | hydration 读路径安全(正面);写路径漂移测试缺失 |
| C4 可观测性 | `fail` | /healthz 假健康(R7);无 metrics;测试不验事件 |
| C5 适配层纪律 | `n.a.(本簇)` | 装配层引用各簇结论 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`（实质 blocked）
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1/R2**:重建测试有效性 —— 消除夹具掩盖(reap 走真实 now_iso)、补语义/并发/安全/时间/向量真实性断言、填充 unit/e2e。这是阻止"假绿再次发生"的前提。
  2. **R3**:worker 接线 reap(依赖 G-CR4-02 时间修复)。
  3. **R4**:接入真实 embedding(依赖 G-CR7-01),使端到端语义非空。
  4. **R5**:closure 的 vector/retrieval/cutover gate 重新定级,撤销基于陈旧 `14 passed` 的 ✅。
- **可以后续跟进的 non-blocking follow-up**：R6 连接关闭;R7 lifespan/CORS/异常/healthz;R8 桩固化测试重写;R9 优雅退出。
- **建议的二次审查方式**：`independent reviewer`(测试重建后需复跑;E2E 需在真实 embedding + reap 接线后做一次贯通验证)
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应,不要改写 §0–§5。`

> 本轮 review 不收口。端到端管道接得上但语义为空(伪向量)、故障恢复缺装(reap),测试套件系统性假绿无法证明任何正确性。CR-8 同时第三次复核确认 A1 非 bug。

---

## 附录 · 全程序级收口总账(8 簇综合)

> CR-8 作为收尾簇,汇总 CR-1~CR-8 的整体判断。详见各 `part-cr-N.md` 与 `index.md` 全局登记表。

### A. 八簇 verdict 总览

| 簇 | Verdict | blocker | 标志性发现 |
|----|---------|---------|-----------|
| CR-1 基础契约 | changes-requested | 3 | 时间格式缺秒(根因)、contracts 死代码 |
| CR-2 关系存储 | changes-requested | 3 | 连接泄漏、事务模式冲突、4 表零访问 |
| CR-3 对象/向量 | 近 blocked | 5 | 路径遍历、vec0 假绿、rowid 破坏 |
| CR-4 工作流内核 | 实质 blocked | 5 | reap 死代码、双重执行、restart 失效 |
| CR-5 控制面 | changes-requested | 2 | API key 缺失、路径遍历源头 |
| CR-6 Clean | 近 blocked | 4 | clean 执行链全是桩(0/7、0/3) |
| CR-7 RAG | 近 blocked | 6 | embedder 伪向量、structurize/construct 大面积盲点 |
| CR-8 入口/测试 | 实质 blocked | 4 | 测试结构性假绿、端到端语义为空 |

**全程序合计 blocker ≈ 32(去重后约 28)。无任一簇可收口。**

### B. 跨簇主线问题(根因聚合)

1. **时间格式根因(G-CR1-01)**:`_utils.now_iso` 缺 `%S` → 真正破坏 lease 比较(G-CR4-02)与 restart 就绪(G-CR4-04);本簇确认测试用夹具绕过它。修一处 + 统一时间 SSOT 可解多簇。
2. **"假绿"链**:vec0 退化(G-CR3-02)+ 伪 embedder(G-CR7-01)+ clean 全桩(G-CR6-01/02)被弱测试(CR-8 R1)+ 陈旧 closure(R5)联合掩盖 —— 系统"看起来完成"实则核心能力为空。
3. **执行器/内核职责撕裂(G-CR4-03)**:执行器自提交 succeeded + 无幂等键 + main 忽略返回值 → 双重执行,贯穿 CR-4/6/7。
4. **stub 即盲点(owner #1)**:CR-6/CR-7 的 clean/rag 执行器是占位桩,legacy ~17k 行能力在 Python 仅数十行真实算法。
5. **适配层安全/能力缺陷**:路径遍历(CR-3/CR-5)、对象存储无 delete(CR-3)、无二进制(CR-3)。

### C. 建议修复优先级(供 owner 排期)

- **P0(语义/安全/数据完整性)**:时间格式根因(G-CR1-01)→ reap 接线(G-CR4-01)→ 双重执行(G-CR4-03)→ 路径遍历(G-CR3-01/CR5-02)→ rowid 重号静默删除(G-CR3-04)→ 真实 embedding(G-CR7-01)。
- **P1(可靠性)**:连接泄漏(G-CR2-01)、事务模式(G-CR2-02)、restart 失效(G-CR4-04)、vec0 真实加载或显式 degraded(G-CR3-02)。
- **P2(能力补全)**:clean/rag 执行器去桩(CR-6/CR-7 盲点)、API key 认证(G-CR5-01)、purge 清对象(G-CR3-05)。
- **P3(收口前提)**:**重建测试有效性(CR-8 R1/R2)+ closure 重新定级(R5)** —— 在此之前任何"已完成"声明都不可信。

### D. 跨簇纠偏记录(诚实账)

本轮审查中,4 个早期候选/前序结论经独立实测被推翻或收窄,均已在 index.md 更正:
- **A2**(CR-2):迁移路径搜索断点 → 证伪(包内 core.sql 存在且打包)。
- **CR-1 v_ready_steps 断言**(CR-4):"fresh step 永不就绪"过度 → 收窄至仅 restart 路径。
- **CR-3 G-CR3-12**(CR-4):"purge 卡 processing" → 证伪(批回滚退 pending),改记批量单事务问题。
- **A1**(CR-5/6/8):stage 命名断点 → 证伪(实际匹配)。
