# Nano-Agent 代码审查模板

> 审查对象: `MKB baseline.v1 — Turso Physical Schema Constitution (D04 域)`
> 审查类型: `code-review`
> 审查时间: `2026-08-13`
> 审查人: `Grok`
> 审查范围:
> - `docs/baseline/domain-truth/D04-turso-physical-schema.md`（D04-v1.1 / D08-calibrated；55 required）
> - `docs/verification/schema-reconciliation.md`
> - `src/persistence/migrations/001_initial.sql` … `005_candidate_admission_result.sql`
> - `src/persistence/{migration_runner,sqlite_port,ports,retrieval_access}.py`
> - `src/runtime/{config,health,task,workflow,intake,inference}/`
> - `src/services/{events,observability,scatter_intake,registry,teams,artifacts,vector_purge,index_retirement}.py`
> - `api/app.py`、`data/config/default.toml`、`pyproject.toml`
> - `data/database/mkb_primary.db`（工作区遗留文件，gitignored）
> - `tests/e2e/*`、`tests/unit/test_readiness_composition.py`、`tests/unit/test_config_overrides.py`、`tests/domain/test_architecture.py`
> 对照真相:
> - `docs/baseline/domain-truth/D04-turso-physical-schema.md`（D04-v1.1 / T-O-160..179 / T-O-192..194 / D08-calibrated）
> - 邻域执行语义：`S12-turso-persistence.md`（Ports / TX / readiness；本轮不重开 S12 全文）
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 先给一句话 verdict。  
> 例如：`该实现主体成立，但当前不应标记为 completed。`  
> 或：`该实现已满足 action-plan / design doc 的收口标准，可以关闭本轮 review。`

- **整体判断**：D04 的 55 张 required 表与线性 migration 链已经到位，本地 SQLite 适配器也能把主路径业务行写进真实文件；但当前**不能**把 D04 标成 Turso 物理层 completed——引擎未装、P12 readiness 被改写、单条 TX-05 缺 ChangeSet、覆盖型 domain_events 未写。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. **Q1 — migration 闭集**：`001`–`005` 兑现 D04 §2.2 的 55 张 required 表 + 3 张已记录的 S08/S09 增表；禁止表未出现；DDL 足以承载 TX-01..08 的列/约束/索引。
  2. **Q2 — Turso 安装 / 驱动 / 物理初始化**：仓库没有 libSQL/Turso 依赖或适配器；运行栈是 stock `sqlite3` + `SqlitePersistence`；runner 与 lifespan `migrate()` 成立。工作区 `data/database/mkb_primary.db` 是 gitignored 遗留文件，只应用到 `003`，缺 `004`/`005`。`default.toml` 的 CW/native-vector 要求未被 Python 读取。
  3. **Q3 — 业务抽象与 e2e 落盘**：主路径在同一个 `persistence.transaction()` 里写真实行，e2e 用 `tmp_path / "mkb.sqlite3"` 落盘且部分测试会 reopen。单条 ingest 不写 ChangeSet；intake/generation/vector 的覆盖事件只登记不写入；e2e 从未观察 `mkb_domain_events` / `embedding` BLOB / `mkb_stored_objects`。

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。  
> 明确你看了哪些文件、跑了哪些命令、核对了哪些计划项 / 设计项 / closure claim。
> 如果引用了其他 reviewer 的结论，必须说明是独立复核、采纳、还是仅作为线索。

- **对照文档**：
  - `docs/baseline/domain-truth/D04-turso-physical-schema.md`（§1.3 P01–P18、§2.2 55 表、§2.4 TX-01..08、§3 列/索引、§4 VIEW、Appendix A）
  - `docs/verification/schema-reconciliation.md`（可执行偏差记录，**不是**第二宪法）
  - `docs/baseline/domain-truth/S12-turso-persistence.md` §4.1–4.2（Ports / CW / Native Vector；本轮只取执行语义）
- **核查实现**：
  - `src/persistence/migrations/001_initial.sql`（58 `CREATE TABLE`、14 `CREATE VIEW`）
  - `src/persistence/migrations/002_*.sql` … `005_*.sql`
  - `src/persistence/migration_runner.py`、`sqlite_port.py`、`ports.py`
  - `api/app.py` lifespan / composition root
  - `src/runtime/task/task_create.py`、`task_projection.py`、`task_projections.py`
  - `src/runtime/workflow/runtime_core.py`、`runtime_outcome.py`、`runtime_gates.py`
  - `src/runtime/intake/acceptance_snapshot.py`、`src/services/scatter_intake.py`
  - `src/services/events.py`、`src/runtime/intake/vector_publish_commit.py`
  - 全部列出的 e2e 与 readiness/architecture 测试
- **执行过的验证**：
  - 4 路 read-only review sub-agent（A schema / B driver-init / C TX / D e2e-persist），产出 `/tmp/grok-0/d04-review/{A,B,C,D}-*.md`
  - 编排侧对关键路径做 **file:line 二次复核**；本报告只采纳已复核行号
  - 独立 `sqlite3` 只读探测工作区 `data/database/mkb_primary.db`（表数、migration 账本、004/005 列是否存在）
  - 独立 `python3 -c "import libsql"` / `import turso`；`pyproject.toml` 依赖扫描
  - `.venv/bin/pytest tests/unit/test_readiness_composition.py tests/unit/test_config_overrides.py tests/unit/test_task_projections.py tests/domain/test_architecture.py -q --tb=line` → **23 passed**
  - 未在本轮重跑全量 e2e / 未启动 vLLM
- **复用 / 对照的既有审查**：
  - 本轮 4 路舰队笔记 — 作为线索；**关键 finding 均经编排侧独立 file:line / 命令复核**
  - `docs/code-review/baseline-dev/D01-reviewed-by-Grok.md`、`D02-reviewed-by-Grok.md` — 仅对照输出模板与已知 residual；不把 D01/D02 结论当 D04 证据
  - Agent B 未能 SELECT 工作区主库；编排侧独立 SELECT，**不以 Agent B 的“无法 dump”为准**

### 1.1 已确认的正面事实

- `001_initial.sql` 含 58 张 `CREATE TABLE`：D04 Appendix A 的 55 张 required 全部存在；另 3 张为 reconciliation 记录的 `mkb_vector_record_facets` / `mkb_publication_proofs` / `mkb_index_active_pointers`。
- 禁止表不存在：`mkb_process_claims`、`intake_scheduling_outbox`、`mkb_vec_process` / `smind_*`。D08 proposed 三表（provider/strategy）未升 required DDL。
- 14 张 VIEW 与 D04 §4 清单逐名对齐；migration 目录无 `CREATE TRIGGER` / `INSTEAD OF`。
- `002`–`005` 只做 ALTER/INDEX：cleanup `eligible_at`、scatter-root 唯一、`processes.root_execution_uuid`、`executions.cancelled_child_count`、`candidate_sets.admission_result`。
- runner 按 `NNN_*.sql` 线性发现，校验 checksum / 未知 id，要求文件以 `COMMIT;` 结束（`src/persistence/migration_runner.py:21-80`）。
- App lifespan 调用 `await container.persistence.migrate()`（`api/app.py:362`）。
- TX-01 生产路径在同一 UoW 写 `mkb_tasks` + `mkb_task_audits` + root `mkb_executions` + `mkb_outbox` + `task.created`（`src/runtime/task/task_create.py:75-186`）。
- Claim/fence 行内落在 `mkb_processes`（`runtime_core.py:201` 一带）；全库只写一张 `mkb_outbox`。
- `DomainEventWriter.write` 与 `_record_event_tx` 都在调用方 `tx` 上 INSERT；`SqlitePersistence.transaction` 异常 rollback（`sqlite_port.py:79-89`）。
- e2e 一律 `database_path=tmp_path / "mkb.sqlite3"`，无 mock / `:memory:`；多份测试在 TestClient 关闭后 `sqlite3.connect(...?mode=ro)`。
- 本轮聚焦测试 23 passed（readiness / config override 含 `mkb_domain_events` reopen / task projections / architecture）。

### 1.2 已确认的负面事实

- `pyproject.toml` 运行依赖无 `libsql` / `turso`；本机 `import libsql` / `import turso` 均为 `ModuleNotFoundError`。
- `src/persistence/` 只有 `SqlitePersistence`；无 `src/persistence/turso/`；`api/app.py:188` 硬编码 SQLite。
- `001_initial.sql:1463-1464` `embedding BLOB NOT NULL`；`001_initial.sql:1901` 的 `vec_idx_mkb_vector_records_embedding` 是普通 B-tree，不是 `libsql_vector_idx`。
- `SqlitePersistence.readiness` 成功路径把 `concurrent_writes` 写死为 `True`（`sqlite_port.py:112`）；`vector_backend="deterministic_exact"`（默认）把 `native_vector` 报 `True`（`sqlite_port.py:124-128`）。
- `data/config/default.toml:7-8` 的 `concurrent_writes_required` / `native_vector_required` 在全部 `*.py` 中无读取点。
- 工作区 `data/database/mkb_primary.db`（1 650 688 bytes，gitignored）账本只有 `001`/`002`/`003`；`PRAGMA` 确认无 `mkb_processes.root_execution_uuid`、无 `mkb_executions.cancelled_child_count`、无 `mkb_intake_candidate_sets.admission_result`。业务表行数为 0。
- 单条 accept（`acceptance_snapshot.py:65` 回调）不 INSERT `mkb_intake_change_sets` / `mkb_intake_change_set_facts`；全 `src/` 这两张表的 INSERT 只在 `scatter_intake.py:228-264`。
- `intake.snapshot_accepted` / `generation.artifact_accepted` / `vector.upserted` 只出现在 `DomainEventWriter.ALLOWED_TYPES`（`events.py:31-44`），生产路径无写入调用。
- e2e 无任何 `SELECT` 命中 `mkb_domain_events`、`mkb_stored_objects` 或 `mkb_vector_records.embedding` 列。
- `src/persistence/ports.py` 只有薄 `UnitOfWork` / `PersistencePort` + 两个只读 port；`TaskRepository` 无实现、无调用方。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | finding 与对齐项绑定 `path:line` 或 SQL 片段 |
| 本地命令 / 测试 | `yes` | 独立探测主库与 import；聚焦 pytest 23 passed；未跑全量 e2e |
| schema / contract 反向校验 | `yes` | 001–005 vs D04 §2.2/§3/§4 + reconciliation |
| live / deploy / preview 证据 | `n/a` | 无 Turso 云库 / 无 libSQL 进程可连 |
| 与上游 design / QNA 对账 | `yes` | 直接对账 D04-v1.1；QNA 不作为执行 SSOT |

---

## 2. 审查发现

> 使用稳定编号：`R1 / R2 / R3 ...`。  
> 每条 finding 都应包含：严重级别、类型、事实依据、为什么重要、审查判断、建议修法。  
> 只写真正影响 correctness / security / scope / delivery / test evidence 的问题，不写纯样式意见。

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 仓库未安装 Turso/libSQL，也无生产适配器 | `high` | `platform-fitness` | `yes`（相对 D04 收口） | 增加 libSQL extra + `TursoPersistence`，或正式 reopen 本地 sqlite 剖面 |
| R2 | readiness 把 D04-P12 CW/Native Vector 改写成“选中后端已就绪” | `high` | `protocol-drift` | `yes` | 读取 `*_required` 并真实探测；sqlite 默认不得报 `native_vector=True` |
| R3 | 单条 TX-05 不写 ChangeSet / facts | `high` | `correctness` | `yes` | 与 scatter 一样在 accept UoW 插入一成员 ChangeSet |
| R4 | intake/generation/vector 覆盖型 domain_events 只登记不写 | `medium` | `protocol-drift` | `no` | 在同一 UoW 写已登记 type |
| R5 | 公开 TX-08 把 gate 决策与 Execution waiting 投影拆成两笔 TX | `medium` | `protocol-drift` | `no` | 回填 D04/S12，或把 resume 折回 `decide_gate` |
| R6 | ANN 索引名是 B-tree，`embedding` 是 portable BLOB | `medium` | `platform-fitness` | `no` | Turso 变体 migration 建 `libsql_vector_idx`；禁止用同名 B-tree 当 ANN 证据 |
| R7 | 工作区 `mkb_primary.db` 只应用到 003，缺 004/005 | `medium` | `delivery-gap` | `no` | 不把遗留文件当已初始化主库；下次启动应跑完链 |
| R8 | Ports 仍是薄 SQL UoW，无按域 repository | `medium` | `delivery-gap` | `no` | 按 S12-E01 抽 Outbox/Claim/各域 repo |
| R9 | e2e 能落盘，但未观察 events / embedding / stored_objects | `medium` | `test-gap` | `no` | D07-E2E-01 关闭后 reopen 断言这些行 |
| R10 | scatter 子身份仍活在 `payload_extra` | `medium` | `protocol-drift` | `no` | 改成 typed 列，停止从 extra 读 CAS 坐标 |
| R11 | D04 正文未吸收已实现的 reconciliation 拼写 | `low` | `docs-gap` | `no` | reopen D04 §3 回填 |
| R12 | Task 投影 CAS 未把 `status`+`row_revision` 放进 UPDATE WHERE | `low` | `correctness` | `no` | 按 S12-E04 收紧谓词 |

### R1. 仓库未安装 Turso/libSQL，也无生产适配器

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`（若要把本轮标成 D04 / Turso 物理层收口）
- **事实依据**：
  - `pyproject.toml:13-19` 运行依赖只有 FastAPI 栈；无 `libsql` / `turso`。
  - 本机 `import libsql` / `import turso` → `ModuleNotFoundError`。
  - `src/persistence/__init__.py:1-3` 只导出 `SqlitePersistence`；`api/app.py:62,188-192` 组合根硬编码该类。
  - S12-E01 规定的 `src/persistence/turso/` 不存在。
- **为什么重要**：
  - D04-P01 / T-O-161 把物理库钉在 Turso 单主库 `mkb_primary`；D04-P12 / T-O-170 要求 Concurrent Writes + native ANN。没有引擎与适配器，这些定律无法在目标平台验收。
- **审查判断**：
  - SQLite 本地/CI 剖面本身可以存在（`sqlite_port.py:1-4` 也这么写）。缺的是可替换的 Turso 驱动，以及组合根的选择面。当前不是“Turso 已安装、sqlite 只是 stand-in”，而是“只有 sqlite stand-in”。
- **建议修法**：
  - 增加官方 libSQL 客户端（主依赖或 extra），落地 `src/persistence/turso/` 实现 `PersistencePort` + `migrate()`，由 Settings 选择。保留 `SqlitePersistence` 作显式 CI 剖面。

### R2. readiness 把 D04-P12 CW/Native Vector 改写成“选中后端已就绪”

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `data/config/default.toml:7-8`：`concurrent_writes_required = true`，`native_vector_required = true`。
  - 全仓库 `*.py` 无这两个键的读取点；`Settings.vector_backend` 默认 `deterministic_exact`（`src/runtime/config.py:25`）。
  - `sqlite_port.py:109-114` 成功路径：`"concurrent_writes": True` 写死；`"native_vector"` 在 deterministic 剖面为 `True`（`:124-128`），仅当显式 `native_ann` 才 `False`（`:130-136`）。
  - `tests/unit/test_readiness_composition.py:17-44` 把上述改写锁成回归。
  - `HealthAggregator.REQUIRED` 含这两个名字（`src/runtime/health.py:13-23`），但默认进程不会因缺 CW/ANN 变 `not_ready`。
- **为什么重要**：
  - D04-P12 / T-O-170：能力缺失 → `readiness=false`。当前默认 `/ready` 在 stock sqlite + 兼容 B-tree 上仍可 200，等于用剖面名覆盖了引擎能力。
- **审查判断**：
  - fail-closed 只对“有人主动选 native_ann”成立。这与宪法默认“要求 native vector”相反。
- **建议修法**：
  - Settings 读取 `*_required`。CW 探测 `BEGIN CONCURRENT` 或 libSQL 能力 API；vector 探测真实 ANN/top-k。`deterministic_exact` 只能作为显式 waiver，不能在 `native_vector_required=true` 时报 `native_vector=True`。

### R3. 单条 TX-05 不写 ChangeSet / facts

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - D04 §2.4 TX-05 最小表集含 candidate→snapshot/item/revision/membership/**changeset** + outbox + domain_events。
  - `acceptance_snapshot.py:65-237` 写 snapshot/item/revision/artifacts/membership/candidate CAS/execution+task 指针/transition，**没有** `mkb_intake_change_sets`。
  - `rg "INSERT INTO mkb_intake_change_sets"` 全 `src/` 只命中 `src/services/scatter_intake.py:228`。
- **为什么重要**：
  - ChangeSet 是 S04 接受事务的 typed SSOT。单条 ingest 成功提交后可以没有 ChangeSet 行，scatter 与单条接受面不一致，后续 fan-in / rebuild 只能靠推断。
- **审查判断**：
  - 不是“表没建”，是生产写路径漏了 TX-05 规定集合。Scatter 路径已经证明同一 UoW 能写这两张表。
- **建议修法**：
  - 在 `_accept_snapshot` 回调里插入一成员 ChangeSet + `accept_revision` fact，与 snapshot/revision 同 TX；插入失败则整笔 accept 失败。

### R4. intake/generation/vector 覆盖型 domain_events 只登记不写

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/services/events.py:31-44` 登记了 `intake.snapshot_accepted`、`intake.candidate_accepted`、`generation.artifact_accepted`、`generation.pointer_cas`、`generation.invocation_recorded`、`vector.upserted`。
  - 生产 `rg` 这些字符串只出现在 allowlist，无 `events.write(..., event_type=...)`。
  - 对应 UoW 会写 `process.outcome_accepted`（`runtime_core.py:611` / outcome 路径），因此 `mkb_domain_events` 表会被碰到，但不是 D04 §3.1.3 的 intake/generation/vector 族。
- **为什么重要**：
  - D04-P14 / T-O-167：覆盖类变迁必须同 TX 写 domain_events，插入失败整 TX 失败。缺这些 type，按 trace 拉业务时间线会对不齐。
- **审查判断**：
  - 同 TX 纪律在 Task/claim/outcome 上成立；缺口是覆盖 type，不是“事件表完全没写”。
- **建议修法**：
  - accept / pointer CAS / vector upsert 成功后经 `DomainEventWriter.write(tx, …)` 发已登记 type；并把 `_record_event_tx` 收到同一 allowlist/redaction 路径（见 R8 相关）。

### R5. 公开 TX-08 把 gate 决策与 Execution waiting 投影拆成两笔 TX

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `task_projections.py:308-396`：`decide_gate` 同 UoW 写 `mkb_execution_gate_decisions` + gates CAS + `mkb_outbox` `gate_decision` + `gate.decided`，然后返回。
  - Execution 从 `waiting` 恢复发生在后续 `consume_gate_decision`（`runtime_gates.py:166` 一带）。
  - D04 §2.4 TX-08 与 S12-E04 要求 decision 与 waiting 投影原子。该拆分与 D02 R3 / S01“HTTP ≠ release”一致。
- **为什么重要**：
  - 崩溃窗口：decision+outbox 已提交、resume 未应用。outbox replay 可恢复，但不是一笔物理 TX-08。
- **审查判断**：
  - 有意的两步协议，不是半写 bug。相对 D04 字面仍是漂移，应回填宪法而不是假装已对齐。
- **建议修法**：
  - 要么 reopen D04/S12 把 S01 两步写成正式 TX 切分，要么把 execution resume 折进 `decide_gate`，outbox 只作 wake/replay 提示。

### R6. ANN 索引名是 B-tree，`embedding` 是 portable BLOB

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`（相对 sqlite 剖面的 TX 写入）；与 R1/R2 一起构成 Turso 收口 blocker
- **事实依据**：
  - `001_initial.sql:1463-1464`：`-- Stock SQLite compatible representation of Turso native F32_BLOB(d).` / `embedding BLOB NOT NULL`。
  - `001_initial.sql:1898-1901`：注释写明 Turso 应变体为 `libsql_vector_idx`；实际 DDL 是 `CREATE INDEX … ON mkb_vector_records(embedding)`。
  - 工作区主库 `PRAGMA table_info`：`embedding` 类型 `BLOB`；index SQL 无 `libsql_vector_idx`。
- **为什么重要**：
  - D04-P16/P12 的最终向量合同是 F32 + 可 probe 的 ANN。同名 B-tree 不能当 ANN 证据。
- **审查判断**：
  - 作为 portable 001 可执行，且注释诚实。未折叠进 D04 正文前，这是平台债，不是漏表。
- **建议修法**：
  - 保留 portable 001；Turso adapter 提供替换 index 的 migration 变体。readiness 禁止用索引名存在当作 ANN。

### R7. 工作区 `mkb_primary.db` 只应用到 003，缺 004/005

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `.gitignore:7-16` 忽略 `data/database/*` 与 `*.db`，只反忽略 `.gitkeep`（符合 D03 不检入 `*.db`）。
  - 独立只读：58 表、14 VIEW、账本三行 `001_initial` / `002_…` / `003_scatter_root_uniqueness`（applied_at `2026-08-12T14:44:09Z`）。
  - 当前文件 checksum：`004` = `38c770a5…`，`005` = `2aef1954…`，账本无这两行。
  - `PRAGMA`：`root_execution_uuid` / `cancelled_child_count` / `admission_result` 均不存在。八张核心业务表 `COUNT(*)=0`。
- **为什么重要**：
  - 有人可能把工作区文件当成“物理库已初始化”。它只是一次旧 lifespan 的遗留 WAL 库，落后当前链两步。e2e 不用这条路径。
- **审查判断**：
  - 物理初始化的产品定义是“启动时 `migrate()` + bootstrap”，不是检入一份满库。遗留文件陈旧，不能当 Q2 的“已完成”证据。
- **建议修法**：
  - 不要把该文件写进文档当已初始化主库。需要本地默认路径时启动一次 app / 调 `migrate()` 补 `004`/`005`。可加只读运维命令打印已应用 migration id。

### R8. Ports 仍是薄 SQL UoW，无按域 repository

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/persistence/ports.py:10-63`：`UnitOfWork.execute/fetch*`、`PersistencePort.transaction/readiness`、未使用的 `TaskRepository.get_task`、只读 `IntakeEligibilityPort` / `RetrievalBodyPort`。
  - S12-E01 还要求 OutboxPort / ClaimPort / MigrationPort / 按域 Repository，以及 `src/persistence/turso/`。
  - 生产 INSERT/UPDATE 散落在 `src/runtime/**` 与 `src/services/**` 的原始 SQL。
- **为什么重要**：
  - TX 完整性目前靠“调用方共用一个 `tx`”，没有编译期强制 TX-01..08 表参与。domain 零 SQL 未兑现。
- **审查判断**：
  - 对“能不能把行写下盘”足够；对“抽象是否对齐 S12/D04 执行面”不够。
- **建议修法**：
  - 抽 typed repo，接受 `UnitOfWork`；SQL 只留在 `src/persistence/`。Outbox/Claim 不可绕过。

### R9. e2e 能落盘，但未观察 events / embedding / stored_objects

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - D07-E2E-01 `test_single_intake_publishes_grounded_retrieval_context`（`tests/e2e/test_single_intake_pipeline.py:44`）只断言 HTTP Task + `/retrieval:search`，不 reopen SQLite。
  - 最强 reopen：`test_generation_pipeline_contracts.py:88-119` 读 artifacts/pointers/`vector_records` 元数据/outbox，不读 `embedding`。
  - `tests/e2e/` 无 `mkb_domain_events`、`mkb_stored_objects`、`SELECT … embedding`（非 `embedding_model_*`）。
  - 仅 `test_inline_ingress_staging.py:108-118` 断言 `mkb_object_references` 计数。
- **为什么重要**：
  - 检索成功是 embedding 落盘的间接证据（`retrieval_rank.py` 解码 `row["embedding"]`），不是 D04-P14/P16 的直接验收。
- **审查判断**：
  - “主路径能在 tmp sqlite 落盘”成立。“D04 业务存取已被 e2e 证明完整”不成立。
- **建议修法**：
  - E2E-01 在 TestClient 退出后 `mode=ro` 断言：`mkb_tasks` / processes / outbox / generation artifacts / `length(embedding)=dimension*4` / `mkb_stored_objects` ⋈ references / 至少一条 `task.created`。

### R10. scatter 子身份仍活在 `payload_extra`

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - Agent C 指出 `scatter_intake.py` 把 `intake_revision_uuid` / `member_ordinal` / `change_set_uuid` 写入 `mkb_executions.payload_extra`，`runtime_core.py:525-534` 再当投影/CAS 真相读回。编排侧确认 ChangeSet 本身有正式表，但子执行坐标仍走 extra。
  - D04-P04 / T-O-173：`payload_extra` 禁止承载 identity/state/proof。
- **为什么重要**：
  - 身份若只活在 JSON，索引/唯一约束无法保护，且与“核心真相不得只活在 JSON”冲突。
- **审查判断**：
  - 005 已把 `admission_result` 从 extra 拉回列（`clean_preflight.py:544-545`），说明项目知道这条纪律；scatter 子坐标还没做完。
- **建议修法**：
  - 为 revision/ordinal/changeset 增加 typed 列或绑定表，停止从 `payload_extra` 读这些键。

### R11. D04 正文未吸收已实现的 reconciliation 拼写

- **严重级别**：`low`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - Executions CHECK 是 `created,ready,running,waiting,succeeded,failed,cancelling,cancelled`（`001_initial.sql:251-252`），不是 D04 草稿的 `pending`/`compensating`。
  - `mkb_domain_events` 拆成 `aggregate` + `severity`，变迁列是 `status_before`/`status_after`（`001_initial.sql:55-74`）。
  - `mkb_tasks.created_at` 存在（`001_initial.sql:174`）。
  - `publication_state` 默认 `withdrawn`（`001_initial.sql:1469-1470`）。
  - `docs/verification/schema-reconciliation.md` 记录了这些，并写明自己不是第二宪法。
- **为什么重要**：
  - 实现者若只读 D04 §3 会按过期草稿改 DDL，或把正确实现误判为偏差。
- **审查判断**：
  - 可执行拼写与 D02/S03/S09 一致，不是削弱。债在 D04 正文。
- **建议修法**：
  - 正式 reopen D04 §3，把四条可执行拼写/默认值折进宪法。

### R12. Task 投影 CAS 未把 `status`+`row_revision` 放进 UPDATE WHERE

- **严重级别**：`low`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `task_projection.py:47-80`：Python 预检查 generation/root/合法边后，`UPDATE … WHERE team_uuid=? AND task_uuid=? AND status NOT IN ('succeeded','failed','cancelled')`。
  - S12-E04 要求 `WHERE status=? AND revision=?`（或等价 generation）。
- **为什么重要**：
  - 今日 sqlite `BEGIN IMMEDIATE` + 进程锁串行化，谓词偏弱不会立刻双写。换 CW 适配器后会竞态。
- **审查判断**：
  - 本地剖面可接受 residual；不是当前 sqlite 主路径的 P0。
- **建议修法**：
  - UPDATE WHERE 带上期望 `status` + `row_revision`（以及提供时的 generation / root）。

---

## 3. In-Scope 逐项对齐审核

> 如果存在 action-plan / design doc / closure claim，就必须有这一节。  
> 结论统一使用：`done | partial | missing | stale | out-of-scope-by-design`。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | Q1：55 张 required 表闭集在 migration 中存在 | `done` | `001` 58 表 = 55 required + 3 已记录增表 |
| S2 | Q1：禁止表 / D08 proposed 未偷升 required | `done` | 无 `smind_*` / 第二 outbox / vec_process / provider 三表 |
| S3 | Q1：§3 关键列/CHECK/UNIQUE/索引足以承载 TX | `done` | CAS、claim 行内、outbox dedupe、events 七索引、VIEW 14 张只读 |
| S4 | Q1：线性 checksum migration 链 | `done` | `001`–`005` + runner drift/unknown fail-closed |
| S5 | Q1：业务流转 DDL 就绪（TX-01..08 表能放下） | `done` | 表/列在；写路径完整性见 S11 |
| S6 | Q2：Turso/libSQL 已安装且可 import | `missing` | 依赖与 site-packages 皆无 |
| S7 | Q2：驱动层齐全（port + Turso adapter + 组合选择） | `partial` | sqlite adapter + Protocol 在；Turso adapter / 工厂不在 |
| S8 | Q2：migration runner + 启动时 apply | `done` | `migrate()` 在 lifespan；e2e/unit 走同一条链 |
| S9 | Q2：命名主库物理初始化已完成 | `partial` | 产品路径是启动 migrate，不是检入 `.db`；工作区遗留库停在 003 |
| S10 | Q2：readiness 兑现 D04-P12 CW + Native Vector | `missing` | 写死/改写；`*_required` 未被读取 |
| S11 | Q3：TX-01..08 生产写路径同 UoW | `partial` | TX-01..04/07 主体成立；单条 TX-05 缺 ChangeSet；TX-08 拆步 |
| S12 | Q3：domain_events 与触发业务同 TX | `partial` | 写入纪律成立；覆盖 type 大量未发 |
| S13 | Q3：单 outbox + claim 行内 | `done` | 全库只写 `mkb_outbox`；claim 列在 `mkb_processes` |
| S14 | Q3：抽象对齐 S12-E01（typed ports / 零 SQL） | `partial` | 薄 UoW 能干活；无 Outbox/Claim/各域 repo |
| S15 | Q3：e2e 仿真数据可落盘 | `partial` | tmp sqlite 真实落盘；events/embedding/catalog 观察不全 |
| S16 | D04 §4 VIEW 只读可验收 | `done` | 14/14，无 INSTEAD OF |
| S17 | 最终向量本体在 `mkb_vector_records.embedding` | `partial` | 列与写入路径在；类型是 BLOB；e2e 不读该列 |
| S18 | reconciliation 增表不替代 D04 表 | `done` | proofs/pointers/facets 旁路，不替换 records/outbox |

### 3.1 对齐结论

- **done**: `8`
- **partial**: `7`
- **missing**: `2`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像“SQLite 本地主库骨架与主路径落盘已经能跑，Turso 引擎合同与部分 TX 覆盖仍未收口”，而不是 D04 completed。

---

## 4. Out-of-Scope 核查

> 本节用于检查实现是否越界，也用于确认 reviewer 是否把已冻结的 deferred 项误判为 blocker。

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | `mkb_process_claims` / 附属 claim 表（defer，OG-01） | `遵守` | 未建表；claim 行内 |
| O2 | 第二 outbox / `intake_scheduling_outbox`（forbid） | `遵守` | 只写 `mkb_outbox` |
| O3 | `mkb_vec_process` / `smind_*` / `content_full` | `遵守` | DDL 与生产 SQL 均未出现 |
| O4 | D08 proposed provider/strategy 三表（非 required） | `遵守` | 合同在 `src/contracts/intake` + registry digest，未偷升 DDL |
| O5 | S15 retention 数值 / Prometheus export | `遵守` | 本轮不审 S15 运维数值 |
| O6 | S09 ANN 算法参数 / serving publication 策略 | `遵守` | 只审物理落点与 index 存在；不把“有向量=已 serving”当缺陷 |
| O7 | 把 gitignored 的空/陈旧 `mkb_primary.db` 当 D03 违规 | `误报风险` | D03 禁止检入 `*.db`；陈旧文件是工作区遗留，不是提交物 |
| O8 | 要求 e2e 填满全部 55 张表才算“能落盘” | `误报风险` | registry/bootstrap 表由启动填充；本轮只要求主路径可观察，不把 35 张未 SELECT 全部升 blocker |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：D04 表闭集与本地 sqlite 主路径落盘主体成立，但 Turso 安装/驱动/P12 readiness 未兑现，且单条 TX-05 缺 ChangeSet——本轮 **changes-requested**，不能关闭。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1+R2**：要么交付可探测的 Turso/libSQL 适配器并让 `*_required` 真正 fail-closed；要么显式 reopen D04/S12，把 `deterministic_exact` + stock sqlite 写成 baseline.v1 官方本地剖面，并停止在该剖面上把 `native_vector`/`concurrent_writes` 报成宪法意义上的 True。
  2. **R3**：单条 ingest accept 与 scatter 一样，在同一 UoW 写入 `mkb_intake_change_sets` + facts；缺行则 TX 失败。
- **可以后续跟进的 non-blocking follow-up**：
  1. R4：补 intake/generation/vector 覆盖事件；`_record_event_tx` 并入 `DomainEventWriter`。
  2. R5：回填 TX-08 两步协议，或把 resume 折回 decision UoW。
  3. R6/R11：Turso index 变体 + 把 reconciliation 折进 D04 §3。
  4. R8/R10/R12：typed ports、scatter 身份出 extra、Task CAS 谓词。
  5. R7/R9：不要把工作区 `.db` 当已初始化证据；E2E-01 直接观察 events / embedding / stored_objects。
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

---

## 6. 实现者回应（2026-08-13 · Grok）

本轮按审查 R1–R12 与 spec-index `PY-13`/`PY-20`/`PY-21`/`PY-22` 实装，不改写 §0–§5。

| Finding | 处置 |
|---------|------|
| R1 | 锁定官方 `libsql>=0.1.11`；新增 `src/persistence/turso/` + `build_persistence()`；组合根按 `Settings.persistence_backend` 选择。无 Turso Cloud token，使用 local/embedded `libsql.connect(path)`。 |
| R2 | Settings 读取 `concurrent_writes_required` / `native_vector_required`（宪法默认 true）。真实探测 `BEGIN CONCURRENT` 与 `vector32`/`libsql_vector_idx`。stock sqlite + 宪法默认 → `/ready=not_ready`。同名 B-tree 不再冒充 ANN。 |
| R3 | 单条 accept 同 UoW 写 `mkb_intake_change_sets` + facts，并回填 `mkb_tasks.change_set_uuid`。 |
| R4 | accept / generation artifact+pointer+invocation / vector upsert 写覆盖型 domain_events；`_record_event_tx` 并入 `DomainEventWriter` allowlist+redaction。事件插入失败回滚业务行。 |
| R5 | 不把 resume 折进 `decide_gate`（避免 reopen D02）。`schema-reconciliation.md` 第 13 条把 S01 两步写成可执行 TX-08。 |
| R6 | 保留 portable BLOB；libsql 适配器对 `vector32`/`libsql_vector_idx` 做真实探测。本地 libsql：`native_vector_probe=true`，`BEGIN CONCURRENT` 仍 false。 |
| R7 | 不把工作区遗留 `.db` 当 SSOT；空库 migrate 现应用 `001`–`006`。 |
| R8 | 本轮不抽全套 typed repo（非 blocker）。Ports 增加 `migrate`/`close`；驱动仍只在 persistence。 |
| R9 | `test_single_intake_publishes_grounded_retrieval_context` 关闭后 reopen 断言 ChangeSet、覆盖事件、`mkb_stored_objects`、`length(embedding)=dimension*4`。 |
| R10 | migration `006` 增加 `scatter_*` 列；fan-in/投影读 typed 列，不再从 `payload_extra` 取身份。 |
| R11 | 继续以 reconciliation 为可执行拼写，不另起表账。 |
| R12 | Task 投影 UPDATE WHERE 含期望 `status` + `row_revision`。 |

**验证摘录**

- `import libsql` 成功（`libsql-import.txt`）。
- 空库 migrate：`001`…`006`（含 `004`/`005`）。
- constitution sqlite `/ready=not_ready`；libsql 本地 `native_vector_probe=true`、`concurrent_writes_probe=false`（无 Cloud CW）。
- mock e2e 两次 succeeded；reopen：ChangeSet=1，facts=1，`task.created` + `intake.*` + `generation.*` + `vector.upserted`，stored_objects=29，vectors 6×`length=256`（dim=64）。

---

## 附录 A — 三问对照（给实现者的短表）

| 用户问题 | 结论 | 一句话 |
|----------|------|--------|
| 1. migration 是否到位、能否支撑业务流转 | **DDL 到位；单条流转仍缺 ChangeSet 行** | 55/55 表 + 索引/VIEW 能放下 TX-01..08；单条 accept 没写 TX-05 规定的 ChangeSet |
| 2. Turso 安装 / 驱动 / migration / 物理初始化 | **未安装 Turso；sqlite 驱动+runner 齐；遗留主库停在 003** | 无 libSQL；启动会 migrate；不要把 `data/database/mkb_primary.db` 当成已交付的初始化库 |
| 3. 业务抽象是否对齐、e2e 能否落盘 | **主路径能落盘；抽象偏薄；e2e 观察不全** | tmp sqlite 有真实行；Ports 仍是原始 SQL；events/embedding/catalog 缺直接断言 |

## 附录 B — 本轮独立探测摘录

```text
sqlite3 3.45.1
libsql: NOT INSTALLED
turso: NOT INSTALLED

data/database/mkb_primary.db  size=1650688  (gitignored)
table_count=58  view_count=14
mkb_schema_migrations:
  001_initial
  002_index_generation_retirement_grace
  003_scatter_root_uniqueness
  -- 004 / 005 absent
processes.root_execution_uuid = False
executions.cancelled_child_count = False
candidate_sets.admission_result = False
core business row counts = 0

current file checksums:
  001_initial 2911e720…
  002_…       163516fc…
  003_…       e54cc8a7…
  004_…       38c770a5…   (not in leftover DB)
  005_…       2aef1954…   (not in leftover DB)

pytest (focused): 23 passed
  tests/unit/test_readiness_composition.py
  tests/unit/test_config_overrides.py
  tests/unit/test_task_projections.py
  tests/domain/test_architecture.py
```
