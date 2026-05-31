# Nano-Agent 代码审查报告 — CR-2 · 关系存储与迁移 (core.db Storage Layer)

> 审查对象: `packages/storage_sqlite/`(engine / migrations/runner / repositories ×5)+ `docs/refactor/core.sql` 作为运行时 SSOT
> 审查类型: `code-review`
> 审查时间: `2026-05-31`
> 审查人: `Claude (Opus 4.8) 主审 + 3 个 sub-agent 分工作面调查（Face A 引擎/PRAGMA、Face B 迁移/schema、Face C repositories）`
> 审查范围:
> - `packages/storage_sqlite/src/storage_sqlite/engine.py`
> - `packages/storage_sqlite/src/storage_sqlite/migrations/runner.py` + `migrations/__init__.py` + `migrations/core.sql`
> - `packages/storage_sqlite/src/storage_sqlite/repositories/{workflow,steps,artifacts,chunks,requests}.py` + `__init__.py`
> - 连带调用面: `apps/api/src/smind_api/deps.py`、`apps/worker/src/smind_worker/main.py`、`packages/vector_sqlite_vec/.../engine.py`（仅 PRAGMA/连接一致性）
> 对照真相:
> - `docs/refactor/index.md`（§3 CR-2 范围、§1 B/D/L 口径与 C1–C5、§4.7 PRAGMA、§7 owner 口径）
> - `docs/refactor/core.sql`（23 表 + 11 视图）、`docs/refactor/database.md`（597 行 schema 设计）
> - `legacy-family/smind-admin/core/db.ts`、`legacy-family/smind-clean-dispatcher/core/db.ts`（D1 访问层校准）
> - `docs/eval/first-code-review-plan/part-cr-1.md`（G-CR1-01 时间格式 critical bug 上游）
> 文档状态: `changes-requested`

---

## 0. 总结结论

- **整体判断**：`核心 SQL 与 schema 本体是正确的（实测干净建库、6 个 repo 全绿、PRAGMA 全对齐），但存储层在"连接生命周期 / 事务模式 / 表覆盖完整性"三个维度存在 blocker，当前不应标记为 completed。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 3 个判断**：
  1. **连接泄漏(blocker)**：`apps/api/.../deps.py` 的 `get_core_conn`/`get_vec_conn` 是 `return connect()` 而非 generator 依赖,每个 API 请求新建连接且**永不关闭** —— 已独立复核确认。
  2. **事务模式与 `BEGIN IMMEDIATE` 冲突(blocker, 潜伏断点)**：engine 未设 `isolation_level=None`/`autocommit`,Python sqlite3 默认会对裸 DML 隐式开事务,与内核 `claim.py` 的 `BEGIN IMMEDIATE` 冲突;**已实测复现报错**。系统当前不炸纯靠"每个 helper 末尾都 commit"的脆弱约定。
  3. **表覆盖盲点(blocker B + 认证断点 D)**：`api_keys`/`workflow_step_links`/`prompt_versions`/`provider_configs` 四张表在全 Python 代码库**零访问**;其中 `api_keys` 相对 legacy 是 team API key 认证的功能断点。repository 抽象仅真覆盖 6/23 表,另 13 张表由各业务包裸 SQL 访问。
- **重要澄清(避免误判)**：附录 A 中预测的 **A2(迁移运行时路径搜索 → 部署无 docs/ 则建不出 schema)经实测证伪 —— 不是断点**。包内 `migrations/core.sql` 真实存在、与 docs 副本逐字节相同、且被 `pyproject` 打包,fallback 路径成立。同时 **G-CR1-01 时间格式 critical bug 不经由 CR-2 污染**:core.sql 的 DB 侧格式正确,6 个 repo 全部走 DDL DEFAULT 写时间,不引用畸形的 `now_iso()`。

---

## 1. 审查方法与已核实事实

本轮采用"主审 + 3 工作面并行 sub-agent"模式:Face A(引擎/PRAGMA/连接)、Face B(迁移机制/schema 保真/core.sql DDL 完整性)、Face C(repositories SQL 正确性/表覆盖/时间写入)。三个 Face 独立调查后回归,主审对其中 2 个最关键且反直觉的发现(事务冲突、连接泄漏)做了**独立复跑验证**,再统一 reasoning 成本报告。

- **对照文档**：`index.md`(§3 CR-2/§1 口径/§4.7)、`core.sql`、`database.md`、`part-cr-1.md`。
- **核查实现**：`storage_sqlite/` 全部 10 个 py 文件、`deps.py`、`worker/main.py`、`vec engine.py`。
- **执行过的验证**：
  - `sqlite3 :memory: + PRAGMA foreign_keys=ON + executescript(core.sql)` → 23 表 + 11 视图干净建出,`foreign_key_check`=空,`integrity_check`=ok。
  - 逐个 `SELECT * FROM <view> LIMIT 0` 验证 11 视图无引用错误。
  - `grep -v "IF NOT EXISTS"` 于 core.sql 全部 67 个 CREATE → 空(完全幂等)。
  - 调用全部 6 个 repo 方法于真实 schema → `ALL REPO METHODS EXECUTED WITHOUT SQL ERROR`。
  - `find packages/storage_sqlite -name core.sql` + `diff` + 查 `pyproject` package-data → fallback 资源存在且打包(证伪 A2)。
  - **主审复跑**:裸 `INSERT` 后 `in_transaction=True` → `BEGIN IMMEDIATE` 抛 `cannot start a transaction within a transaction`;`commit` 后再 `BEGIN IMMEDIATE` 正常(确认 R2)。
  - **主审复核**:`deps.py:33-42` 为 `def ... return ...connect()`,无 `yield`/`finally close`(确认 R1)。
  - 全仓 `grep` 23 张表的实际访问点,建立访问矩阵。
- **复用 / 对照的既有审查**：`part-cr-1.md` G-CR1-01/02/03 —— 作为上游线索独立复核,确认其在 CR-2 的落点(仅 schema 侧 `v_ready_steps`/`v_stale_claims` 比较表达式,非 CR-2 写入路径)。

### 1.1 已确认的正面事实

- `core.sql` DDL **正确、完整、自洽、幂等**:23 表 + 11 视图实测干净建库,无悬挂 FK、无视图列引用错误、全 `IF NOT EXISTS`。
- 6 个 repository 的 SQL **零错误**:列名 / 占位符数量 / 表名 / NOT NULL 提供 全部与 core.sql 匹配,实跑全绿。
- `core.sql` ↔ `database.md` **高度一致**:11/11 视图名吻合、workflow_steps 字段、task_claims 状态枚举、部分唯一索引 `ux_task_claims_active_step`、step_attempts 终止原因 等抽查全部一致。
- **PRAGMA 全对齐**:core engine 5 条(WAL/NORMAL/foreign_keys=ON/busy_timeout=5000/temp_store=MEMORY)齐全、值正确、每次 connect 设置、FK 在任何事务前设置(时机正确)。
- **CR-2 时间写入干净**:6 个 repo 均不 import `now_iso`,时间列全走 DDL `DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))` 或内联 strftime(均为 SQLite 侧正确格式)。
- 附录 A 候选断点 **A2 证伪**:包内 `migrations/core.sql` 存在且被打包,schema 在任何部署形态下都能建立。

### 1.2 已确认的负面事实

- `deps.py` 请求级连接 `return` 而非 `yield`,**永不关闭**(连接/文件句柄泄漏)。
- engine 未配置事务控制模式,默认隐式事务与 `BEGIN IMMEDIATE` **可复现冲突**(已实测报错)。
- `api_keys` / `workflow_step_links` / `prompt_versions` / `provider_configs` **全代码库零访问**。
- repository 抽象仅覆盖 6/23 表,13 张表绕过抽象由各包裸 SQL 直接读写。
- 迁移系统为单条 `core-0001-ssot` 一次性建表,**无版本化演进能力**(无 0002+ 槽位、无 rollback)。
- 每个 repo 写方法独立 commit,**无跨方法事务**(create run + 多 step 非原子,中途失败留半成品)。
- `core.sql` 存在 docs / 包内 **双副本**,靠手工同步(当前一致,机制脆弱)。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | 全部 10 个 py 文件 + deps/worker + core.sql 逐处核行号 |
| 本地命令 / 测试 | yes | 实测建库(23 表/11 视图/FK/幂等)、6 repo 实跑、事务冲突复现、连接泄漏复核 |
| schema / contract 反向校验 | yes | core.sql ↔ database.md 一致性抽查;repo INSERT 列 ↔ DDL 列逐一比对 |
| live / deploy / preview 证据 | n/a | 存储层无需 live 部署证据 |
| 与上游 design / QNA 对账 | yes | index §4.7 PRAGMA、§7.1 BEGIN IMMEDIATE 约定;database.md §9.2 时间格式;part-cr-1 跨簇对账 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | API 请求级连接 `return` 而非 `yield`,永不关闭(连接泄漏) | high | correctness / L | yes | deps 改 generator 依赖,`finally: conn.close()` |
| R2 | engine 未配事务模式,默认隐式事务与 `BEGIN IMMEDIATE` 冲突(潜伏断点) | high | correctness / D | yes | connect() 设 `isolation_level=None`,显式掌控事务 |
| R3 | 4 张表全代码库零访问(真盲点);`api_keys` 相对 legacy 是认证断点 | high | scope-drift / B+D | yes | 确认 P1/P2 范围;补访问路径或文档标注"DDL 预留未接线" |
| R4 | (跨簇确认) G-CR1-01 时间格式 bug 在 schema 侧落点 = `v_ready_steps`/`v_stale_claims`;CR-2 本体不污染 | critical | correctness / L | yes(归 CR-1) | 修 `workflow_core/_utils.now_iso`;CR-2 schema/repo 无需改 |
| R5 | repository 抽象仅覆盖 6/23 表,13 张表裸 SQL 绕过抽象 | medium | scope-drift / B | no | 决策:统一抽象 or 文档化"仅核心表走 repository" |
| R6 | repo 各方法独立 commit,无跨方法事务(多写非原子) | medium | correctness / C1 | no | 为 run+steps 等多写提供事务封装(对标 legacy db.batch) |
| R7 | 迁移系统单条一次性建表,无版本化演进路径 | medium | delivery-gap / D | no | 引入有序 migration 列表或文档化 SSOT 重建约定 |
| R8 | 单连接单线程模型;`check_same_thread` 默认 True 是并发化隐藏断点 | low | correctness / D | no | 并发化前文档化假设;届时每线程独立连接 |
| R9 | core.sql 双副本(docs/包内)漂移风险 | low | correctness / D | no | 单一来源:构建期拷贝或 runner 只读包资源 |
| R10 | vec engine `foreign_keys=OFF` 与 core 不同 | low | platform-fitness | no | 合理分化(vec0 虚拟表),加注释说明即可 |
| R11 | create_step / purge create 硬编码占位 payload/scope | low | scope-drift / B | no | P1 占位,接线时提为入参 |

### R1. API 请求级连接 `return` 而非 `yield`,永不关闭(连接泄漏)

- **严重级别**：`high`
- **类型**：`correctness / L`
- **是否 blocker**：`yes`
- **事实依据**：
  - `apps/api/src/smind_api/deps.py:33-36` `get_core_conn()` = `return CoreSQLiteEngine(...).connect()`;`:39-42` `get_vec_conn()` 同构。均为普通 `def`,非 `yield` generator。
  - `:23,:30` 的 `conn.close()` 只属于 `_ensure_*_migrated` 两个 lru_cache 迁移辅助函数,与请求连接无关。
  - `main.py` 无 lifespan/teardown;全仓无对请求连接的 `.close()`。主审已复核确认。
- **为什么重要**：
  - 每个用 `Depends(get_core_conn)`/`get_vec_conn` 的端点(ops/management/ingestion/me/auth/search 等)每次请求新建一个 SQLite 连接且不关闭。WAL 模式下未关闭连接持有文件句柄、累积 `-wal`/`-shm` 引用、阻碍 checkpoint,长期运行 fd 泄漏 → 最终 `OperationalError: unable to open database file`。
- **审查判断**：
  - 这是相对 legacy(D1 由 Workers 运行时托管连接、无需关闭)的**迁移遗漏**,非平台差异可解释。FastAPI 的标准做法是 generator 依赖。确认为 blocker。
- **建议修法**：
  - `def get_core_conn(): conn = CoreSQLiteEngine(...).connect(); try: yield conn; finally: conn.close()`(vec 同理)。FastAPI 在请求结束执行 finally。

### R2. engine 未配事务模式,默认隐式事务与 `BEGIN IMMEDIATE` 冲突(潜伏断点)

- **严重级别**：`high`
- **类型**：`correctness / D`
- **是否 blocker**：`yes`
- **事实依据**：
  - `engine.py:13` `sqlite3.connect(self.db_path)` 未设 `isolation_level` / `autocommit`,使用 Python 3.12 默认 `LEGACY_TRANSACTION_CONTROL`(`isolation_level=''`)。
  - 内核 `workflow_core/claim.py:16` 以 `conn.execute("BEGIN IMMEDIATE")` 开事务。
  - **主审实测复现**:`conn.execute("INSERT ...")`(裸 DML)后 `conn.in_transaction == True`;紧接 `conn.execute("BEGIN IMMEDIATE")` 抛 `sqlite3.OperationalError: cannot start a transaction within a transaction`;而 `commit()` 后再 `BEGIN IMMEDIATE` 正常。
- **为什么重要**：
  - 整个内核(claim/retry/leases/restart/purge/graph)的事务正确性,依赖"每个 helper 末尾无条件 `commit()`"这一隐式纪律。worker happy-path 当前不炸,纯属 `process_restart_requests`/`process_purge_requests`/`succeed_claim` 恰好都在末尾 commit。任何新增/重排一个忘记 commit 的 DML,或在 `claim_one` 前出现裸写,就会触发 `BEGIN IMMEDIATE` 崩溃。这是"靠约定续命"的潜伏断点,与设计 SSOT §7.1 要求的显式 `BEGIN IMMEDIATE` 事务模型不自洽。
- **审查判断**：
  - 当前 happy-path 不触发(基于对所有 helper 末尾 commit 的逐一核对),但属设计层断点 D,根因在 engine 未把连接配成与显式事务相容的模式。
- **建议修法**：
  - `connect()` 内设 `conn.isolation_level = None`(autocommit,让 `BEGIN IMMEDIATE`/`commit`/`rollback` 完全由代码掌控),与现有"显式 BEGIN IMMEDIATE + 显式 commit"风格最自洽。

### R3. 4 张表全代码库零访问(真盲点);`api_keys` 相对 legacy 是认证断点

- **严重级别**：`high`
- **类型**：`scope-drift / B(盲点) + D(认证断点)`
- **是否 blocker**：`yes`（存储完整性维度;认证功能维度的最终裁决归 CR-5 控制面）
- **事实依据**：
  - `grep -rln` 对 `api_keys`(core.sql:54)、`workflow_step_links`(:321)、`prompt_versions`(:362)、`provider_configs`(:378)在全 `.py`(含 tests)**返回空** —— 无 INSERT/SELECT/UPDATE,无 repository。
  - `auth/service.py` 只用 `sessions`/`users`,无 API key 校验路径。
  - legacy `smind-admin/core/db.ts:429,455` 有完整 `findTeamByApiKeyHash`/`upsertTeamApiKey`(对 `smind_teams_keys`)。
- **为什么重要**：
  - `api_keys` 是 DDL 定义的认证机制,零访问 = team API key 认证未迁移(相对 legacy 断点 D)。`workflow_step_links` 是 DAG 边表(`graph.py` 只写 `workflow_events` 不写 links —— 影响图调度/依赖追踪)。`prompt_versions`/`provider_configs` 是配置版本表(P1 设计 §4.3-D 列出)。按 owner 口径 #1,"应有却零实现"明确登记为盲点 B。
- **审查判断**：
  - 确认为真盲点(区别于 R5 的"绕过抽象但有访问")。存储层维度判 blocker;但"是否阻断"取决于 P1/P2 范围 —— 若 P1 故意不接线,需文档标注,否则会被误当已实现。`api_keys` 认证缺口的业务裁决移交 CR-5。
- **建议修法**：
  - 确认 P 阶段范围;需要则补 service/repository,不需要则在 `database.md`/closure 显式标注"DDL 预留,P1 未接线"。

### R4. (跨簇确认) 时间格式 bug 在 schema 侧落点;CR-2 本体不污染

- **严重级别**：`critical`（归属 CR-1 / G-CR1-01）
- **类型**：`correctness / L`
- **是否 blocker**：`yes`（但修复点在 `workflow_core/_utils.py`,不在 CR-2）
- **事实依据**：
  - core.sql 的时间比较视图 `v_ready_steps`(:535 `ws.available_at <= strftime('%Y-%m-%dT%H:%M:%fZ','now')`)、`v_stale_claims`(:713 lease 比较)做**字符串字典序比较**。
  - core.sql 全部 40 处 strftime 统一为 `%Y-%m-%dT%H:%M:%fZ`(SQLite 侧 = 毫秒,正确),DB 侧无第二种格式。
  - 6 个 CR-2 repo 均不 import `now_iso`,时间列全走 DDL DEFAULT(Face B/C 双重确认 + 实跑产出 `...:53.774Z` 正常)。
- **为什么重要**：
  - 上游 `workflow_core/_utils.now_iso()` 格式串缺 `%S`,写出畸形串(秒被微秒挤占)。该畸形串经 **CR-1/workflow_core** 写入 `available_at`/`lease_expires_at`,与 DB 侧正确串在第 17 字符后结构错位,破坏 `v_ready_steps`/`v_stale_claims` 的字典序比较 → 漏调度 ready step、lease 回收失准。
- **审查判断**：
  - **CR-2 在时间维度无 bug**(schema 正确、repo 走 DEFAULT)。bug 经由 CR-1 簇写入污染同样这些表的其他列,schema 侧落点是两个比较视图。本条记录为跨簇确认,避免在 CR-2 重复计为本簇缺陷。
- **建议修法**：
  - 修 `workflow_core/_utils.now_iso/add_seconds_iso` 为 `%Y-%m-%dT%H:%M:%S.%fZ` 并截断到 3 位毫秒;CR-2 schema 与 repo 无需改动。

### R5. repository 抽象仅覆盖 6/23 表,13 张表裸 SQL 绕过抽象

- **严重级别**：`medium`
- **类型**：`scope-drift / B`
- **是否 blocker**：`no`
- **事实依据**：
  - 13 张表有裸 `conn.execute` 访问但无 Repository 类:`users/teams/team_members/sessions`→auth|team;`uploads/sources/documents/static_files`→ingestion|workflow_clean|management;`task_claims/step_attempts`→workflow_core;`workflow_events/audit_logs`→workflow_core/events,graph;`configs`→api/routes/workflow_config.py:19。详见 §附录访问矩阵。
- **为什么重要**：
  - 架构不一致:`storage_sqlite/repositories/` 名义上是 core.db 的访问抽象层,但仅 6/23 表走它,其余散落各包裸 SQL。这也是为什么时间写入风险分散到各包(R4 的传播面),以及表 schema 变更时无单点维护。
- **审查判断**：
  - 事实(绕过抽象,非真盲点 —— 数据确实被读写)。属设计取舍,非阻断,但需明确记录。
- **建议修法**：
  - owner 决策:统一所有 core.db 访问走 repository,或在设计文档明确"仅 workflow 核心表走 repository,其余业务表由各 service 自管"。

### R6. repo 各方法独立 commit,无跨方法事务(多写非原子)

- **严重级别**：`medium`
- **类型**：`correctness / C1`
- **是否 blocker**：`no`
- **事实依据**：
  - `workflow.py:create_run`、`steps.py:create_step`、`requests.py:create`、`chunks.py:set_vec_status` 均各自 `self.conn.commit()`。无跨方法事务封装。
  - legacy `smind-admin/core/db.ts:388` `createUserWithProfileAndTeam` 用 `db.batch([...])` 原子多写。
- **为什么重要**：
  - 创建一个 run + 其多个 step 是多次独立 commit,中途失败会留下半成品 run(无 step),无回滚保护。多写一致性弱于 legacy 的 batch 原子性。
- **审查判断**：
  - 单方法内无问题(短持锁、立即 commit);多写一致性是设计层缺口。
- **建议修法**：
  - 为 run+steps 等组合操作提供显式事务封装(一个 `BEGIN IMMEDIATE`...`commit` 包住多写)。

### R7. 迁移系统单条一次性建表,无版本化演进路径

- **严重级别**：`medium`
- **类型**：`delivery-gap / D`
- **是否 blocker**：`no`
- **事实依据**：
  - `runner.py:30` 仅 `core-0001-ssot` 一条,`executescript` 整个 core.sql,migration_id 已存在即 `return`。无 0002+ 机制,无单步 SQL 目录,无 down/rollback。
- **为什么重要**：
  - 已建库后改 core.sql 不会被应用。schema 演进(加列/加表)无承接槽位。对 v0.1 首建可用,作为长期迁移框架不完整。
- **审查判断**：
  - 设计债,非阻断。
- **建议修法**：
  - 引入有序 migration 列表(0001 SSOT + 后续增量,各自 id 记账),或文档明确"core.sql 为 SSOT 重建脚本,演进走新增 NNNN 文件"。

### R8. 单连接单线程模型;`check_same_thread` 默认 True 是并发化隐藏断点

- **严重级别**：`low`
- **类型**：`correctness / D（潜伏）`
- **是否 blocker**：`no`
- **事实依据**：
  - `worker/main.py:25` 创建单个 `core_conn` 贯穿主循环复用;`scheduler.py:10` 持有同一 conn。worker 单线程串行。
  - `engine.py:13` 未设 `check_same_thread=False`(默认 True)。API 端点全同步 `def`(全仓无 `async def`),连接同线程创建+使用,当前不报错。
- **为什么重要**：
  - SSOT §4.7 提"poller 并发可配置";一旦引入并发 poller 线程或 API `async def` 直接用这些 conn,`check_same_thread=True` 会抛 `SQLite objects created in a thread can only be used in that same thread`,且单连接无法支撑多线程并发 claim。
- **审查判断**：
  - 当前 pass(单线程安全),属随并发化触发的隐藏断点。
- **建议修法**：
  - 并发化前文档化"单 poller 单连接"假设;届时改每线程独立连接 + WAL(并发读 + 单写)。

### R9. core.sql 双副本(docs / 包内)漂移风险

- **严重级别**：`low`
- **类型**：`correctness / D`
- **是否 blocker**：`no`
- **事实依据**：
  - `runner.py:8-14` 运行时**优先**向上搜索 `docs/refactor/core.sql`,找不到才用包内 `migrations/core.sql`。两份当前逐字节相同,手工同步。
- **为什么重要**：
  - 开发态用 docs 副本、部署态(wheel)用包内副本。若漂移,两环境建出不同 schema,CI 不易发现。
- **审查判断**：
  - 当前无害(已同步),机制脆弱。
- **建议修法**：
  - 单一来源:构建期把 `docs/refactor/core.sql` 拷成包资源,或 runner 只读包资源、删除 repo 路径优先逻辑。

### R10. vec engine `foreign_keys=OFF` 与 core 不同

- **严重级别**：`low`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `vector_sqlite_vec/engine.py:17` 设 `PRAGMA foreign_keys=OFF`,其余 4 条 PRAGMA 与 core 一致。
- **审查判断**：
  - 合理分化:vec.db 承载 `vec0` 虚拟表,虚拟表通常不参与外键约束。SSOT §4.7 是面向 core 的通用建议,未单列 vec。非 bug。
- **建议修法**：
  - 加一行注释说明 vec 关闭 FK 的理由,避免后续误判。

### R11. create_step / purge create 硬编码占位 payload/scope

- **严重级别**：`low`
- **类型**：`scope-drift / B`
- **是否 blocker**：`no`
- **事实依据**：
  - `steps.py:35` `{"seed": True}`(无 payload_json 入参);`requests.py:59` PurgeRequest 忽略调用方 scope 固定写 `{"target": target_id}`;`requests.py:26` `scope or {"all": True}`;`workflow.py:36` `{"version": "p1"}`。
- **审查判断**：
  - 推断为 P1 脚手架占位,非 SQL 错误。
- **建议修法**：
  - 后续接线时把 payload/scope 提为入参。

---

## 3. In-Scope 逐项对齐审核

> 计划项来自 index §3 CR-2 表格的"关注"与"已知风险"(含附录 A 移交项 A2/A7)。

| 编号 | 计划项 / 设计项 / 已知风险 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| S1 | PRAGMA 设置(WAL/synchronous/foreign_keys/busy_timeout) | `done` | core engine 5 条全对齐、值正确、时机正确(R10 为合理分化) |
| S2 | 迁移幂等性与挂载 | `partial` | 幂等成立(全 IF NOT EXISTS),但无版本化演进(R7)、双副本漂移(R9) |
| S3 | repositories 的 SQL 正确性 | `done` | 6 repo 列名/占位符/NOT NULL 全匹配,实跑全绿 |
| S4 | 与 core.sql 23 表对齐 | `missing` | repository 仅覆盖 6/23;4 张表零访问(R3);13 张表绕过抽象(R5) |
| S5 | 已知风险 A2:运行时搜索 core.sql,部署无 docs 则建不出 | `done`(已核实=证伪) | 包内副本存在且打包,fallback 成立,**非断点** |
| S6 | 已知风险 A7:5 repo 覆盖 23 表,多数表无访问路径 | `done`(已核实=部分成立) | 确认 4 张真盲点 + 13 张绕过抽象;非"全部无访问" |
| S7 | (新增)连接生命周期与事务模式 | `missing` | R1 连接泄漏 + R2 事务模式冲突,均 blocker |
| S8 | (跨簇)时间格式与 schema 比较视图一致性 | `done`(已核实) | CR-2 本体干净;bug 在 CR-1,落点 v_ready_steps/v_stale_claims(R4) |

### 3.1 对齐结论

- **done**: `5`(S1、S3、S5、S6、S8)
- **partial**: `1`(S2)
- **missing**: `2`(S4、S7)
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 它更像"core.db 的 schema 与核心 SQL 已正确落地,但存储层的运行时纪律(连接关闭、事务模式)和覆盖完整性(13 张表无抽象、4 张表零访问)尚未收口",而不是 completed。schema 是这一簇里最成熟的部分;存储层封装与访问完整性是最薄弱的部分。

### 3.2 stub / 真实现标定表(index §7.1 必交项)

| 文件 | 公开符号 | 标定 | 依据 |
|------|----------|------|------|
| engine.py | `CoreSQLiteEngine.connect` | 真实现(有缺陷) | PRAGMA 正确,但缺事务模式配置(R2)、check_same_thread(R8) |
| migrations/runner.py | `apply_core_migrations` | 真实现(部分能力) | 建库幂等可用,但无版本化(R7)、双副本(R9) |
| repositories/workflow.py | `WorkflowRepository.create_run/get_run` | 真实现 | SQL 正确,config_snapshot 占位(R11) |
| repositories/steps.py | `StepRepository.create_step/get_step/list_ready_steps` | 真实现 | SQL 正确,payload 硬编码占位(R11) |
| repositories/artifacts.py | `ArtifactRepository.get_artifact` | 部分(仅读) | 无 create,artifact 写入路径不在本 repo |
| repositories/chunks.py | `ChunkRepository.get_chunk/set_vec_status` | 真实现 | SQL 正确,时间走内联 strftime(安全) |
| repositories/requests.py | `Restart/PurgeRequestRepository.create/backlog` | 真实现 | SQL 正确,scope 占位(R11) |
| — | `api_keys`/`workflow_step_links`/`prompt_versions`/`provider_configs` 访问层 | **缺失** | 全代码库零访问(R3) |

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | G-CR1-01 时间格式 bug 的根因修复 | `遵守(归 CR-1)` | CR-2 仅确认 schema 侧落点与"CR-2 本体不污染",不在 CR-2 改 `_utils.py`(R4) |
| O2 | vec.db / VectorStore 深度审查 | `遵守` | Face A 仅核对 vec engine PRAGMA/连接一致性,业务深审属 CR-3 |
| O3 | API key 认证功能的业务裁决 | `部分(移交 CR-5)` | CR-2 记录 `api_keys` 表零访问(存储完整性);认证链路是否必须属 CR-5 控制面 |
| O4 | A2 误报风险 | `误报已澄清` | 主审在规划阶段把 A2 列为候选断点;本轮实测**证伪**,如实记录为非断点,避免误判 |
| O5 | artifact 写入路径 | `部分(移交 CR-6/7)` | `artifacts` repo 仅 get,无 create;实际写入(clean/rag 产物)路径在业务簇审查 |

### 横切维度 C1–C5 对 CR-2 的逐项结论

| 维度 | 结论 | 证据 |
|------|------|------|
| C1 事务与并发 | `fail` | R2 事务模式与 BEGIN IMMEDIATE 可复现冲突 + R6 多写非原子 + R1 连接泄漏;当前 happy-path 靠 commit 约定续命 |
| C2 错误处理 | `partial` | repo 无 try/except,异常正常向上传播(可接受);但多写无 rollback 封装(R6) |
| C3 一致性 | `n.a.(本簇)` | CR-2 只触 core.db,无跨库;跨 core/vec 一致性属 CR-3/workflow。多写原子性缺口已记 R6 |
| C4 可观测性 | `n.a.` | step 事件/审计落库由 workflow_core/events.py、graph.py 承担,不在本簇 |
| C5 适配层纪律 | `partial` | repository 抽象被 13 张表的裸 SQL 绕过(R5);非 ObjectStore/VectorStore 越层,但属"存储访问层未被贯彻"的纪律问题 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**:`deps.py` 的 `get_core_conn`/`get_vec_conn` 改为 generator 依赖(`yield` + `finally: conn.close()`),消除每请求连接泄漏。
  2. **R2**:`engine.connect()` 设 `isolation_level=None`(autocommit),使 `BEGIN IMMEDIATE` 事务模型成立,消除"靠 commit 约定续命"的潜伏断点;并补一条"裸 DML 后 BEGIN IMMEDIATE"的回归测试。
  3. **R3**:裁定 `api_keys`/`workflow_step_links`/`prompt_versions`/`provider_configs` 四表的 P 阶段归属 —— 需要则补访问路径(尤其 `api_keys` 认证),不需要则在 `database.md`/closure 显式标注"DDL 预留,本阶段未接线"。
  4. **R4(联动 CR-1)**:修 `workflow_core/_utils.now_iso/add_seconds_iso` 时间格式 —— CR-2 schema/repo 无需改,但该修复完成前 `v_ready_steps`/`v_stale_claims` 比较仍不可靠。
- **可以后续跟进的 non-blocking follow-up**：
  1. **R5**:owner 决策 repository 抽象覆盖范围(统一 or 文档化"仅核心表")。
  2. **R6**:为 run+steps 等多写提供事务封装(对标 legacy `db.batch`)。
  3. **R7**:引入版本化迁移机制。
  4. **R9**:消除 core.sql 双副本,确立单一来源。
  5. **R8**:文档化单连接单线程并发假设;R10 为 vec FK 加注释;R11 接线时去硬编码占位。
- **建议的二次审查方式**：`same reviewer rereview`（R1/R2 修复后需复跑"BEGIN IMMEDIATE 回归 + 连接关闭"验证;R3 表归属需 owner 介入裁定）
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应,不要改写 §0–§5。`

> 本轮 review 不收口。CR-2 的 schema 本体与核心 SQL 是健康的(实测干净建库 + repo 全绿 + PRAGMA 对齐),但**存储层运行时纪律(连接泄漏 R1、事务模式 R2)与访问完整性(零访问表 R3、绕过抽象 R5)未收口**;叠加上游 CR-1 时间格式 bug 在本簇比较视图的落点(R4),需先修 R1/R2/R3/R4 再复审。

---

## 附录 · 23 表访问矩阵(Face C 实证,主审复核)

| 表 | repository 覆盖 | 其他包裸 SQL 访问点 | 结论 |
|---|---|---|---|
| users | 否 | auth/service.py:52,62,69; api/routes/me.py:21,35 | 绕过抽象 |
| teams | 否 | team/service.py:14 | 绕过抽象 |
| team_members | 否 | team/service.py:19 | 绕过抽象 |
| api_keys | 否 | **无** | **真盲点(R3)** |
| sessions | 否 | auth/service.py:76,102; team/service.py:53 | 绕过抽象 |
| uploads | 否 | ingestion/service.py:20,33,57,177; workflow_clean:37 | 绕过抽象 |
| sources | 否 | ingestion:67,88,109,146; workflow_clean:42,52,63,77 | 绕过抽象 |
| documents | 否 | ingestion:74,95,116,153; rag:75,200; purge:103; management:58 | 绕过抽象 |
| static_files | 否 | ingestion:160; workflow_clean:37; management:77 | 绕过抽象 |
| workflow_runs | **是** workflow.py | — | 真覆盖 |
| artifacts | **是** artifacts.py(仅读) | — | 真覆盖(无 create,写路径待 CR-6/7) |
| chunks | **是** chunks.py | rag/service.py 也写 vec 状态 | 真覆盖(写部分在 rag) |
| workflow_steps | **是** steps.py | claim/leases/retry 裸 UPDATE | 真覆盖(写分散) |
| task_claims | 否 | workflow_core/{claim,leases,retry}.py | 绕过抽象 |
| step_attempts | 否 | workflow_core/{leases:52,retry:29,121}.py | 绕过抽象 |
| workflow_step_links | 否 | **无** | **真盲点(R3)** |
| workflow_events | 否 | workflow_core/{events:21,graph:21}.py | 绕过抽象 |
| configs | 否 | api/routes/workflow_config.py:19(仅读) | 绕过抽象 |
| prompt_versions | 否 | **无** | **真盲点(R3)** |
| provider_configs | 否 | **无** | **真盲点(R3)** |
| restart_requests | **是** requests.py | restart.py 裸 UPDATE | 真覆盖 |
| purge_requests | **是** requests.py | purge.py 裸 UPDATE | 真覆盖 |
| audit_logs | 否 | workflow_core/events.py:52 | 绕过抽象 |

**统计**:真覆盖 6 / 绕过抽象 13 / 真盲点 4。
