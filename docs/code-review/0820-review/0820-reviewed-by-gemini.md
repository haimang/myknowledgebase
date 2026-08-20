# Nano-Agent 代码审查

> 审查对象: `MKB 全仓代码库架构、持久化、推理调度、LS-RAG 流转、安全边界与测试质量审查`
> 审查类型: `code-review | mixed`
> 审查时间: `2026-08-20`
> 审查人: `Gemini 3.7 Flash (High) / 资深 Python 后端架构师 + 分布式系统审查专家`
> 审查范围:
> - `api/` (`app.py`, `dependencies.py`, `public/routes.py`, `internal/routes.py`)
> - `src/persistence/` (`turso/`, `sqlite_port.py`, `engine.py`, `factory.py`, `migration_runner.py`, `retrieval_access.py`, `migrations/001-013`)
> - `src/storage/` (`local_store.py`)
> - `src/llm_adapters/` & `src/runtime/inference/` (`local_vllm.py`, `claude_cli.py`, `facade.py`, `supply.py`, `invocations.py`)
> - `src/runtime/workflow/` (`dispatch.py`, `runtime_core.py`, `runtime_gates.py`, `runtime_materialize.py`, `runtime_outcome.py`, `runtime_outbox.py`, `worker.py`, `supervisor.py`)
> - `src/runtime/intake/` (`clean_preflight.py`, `generation_construct.py`, `generation_live.py`, `vectorize.py`, `index_rebuild_*.py`, `acceptance_*.py`)
> - `src/services/` (`retrieval/`, `index_retirement.py`, `object_gc.py`, `registry.py`, `config_snapshots.py`, `artifacts.py`, `events.py`, `security_audit.py`, `observability.py`)
> - `intake/` (`text.py`, `web/sanitize.py`, `api/registry.py`, `api/providers/`)
> - `tests/` (`unit/`, `domain/`, `integration/`, `e2e/`, `intake/`, `local_runtime.py`)
> 对照真相:
> - `README.md`
> - `docs/baseline/domain-truth/` (D01–D08, S01–S16)
> - `docs/baseline/qna-truth/` (D02, S02–S16)
> - `docs/eval/new-start/after-MKB-0815-R4-first-wave.md`
> - `docs/closure/new-start/deferred-items-ledger.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> MKB 整体展现出了极其优秀的高内聚分层架构、严谨的不可变契约（Content-Addressed Storage / Immutable Generation Proof）以及细致的双重 Serving Fence 设计哲学；但深入代码与运行态审查后发现，系统在 **事务安全（commit 异常未回滚导致长连接永久死锁）**、**子进程生命周期（超时未 kill 产生僵尸进程）**、**数据流水线（HTML 换行被全局抹平为单行、超长块静默丢弃、锚定游标首项错位）**、**后台运维（Index Retirement 遇失效知识陷入死循环阻塞全库 GC）**、**网络安全（反向代理下内部运维接口与指标暴露）** 以及 **测试质量（存在 `assert ... or True` 恒真、自建字典断言自己、串行循环伪装并发写浸泡、原生 sqlite3 混用读 Turso 导致 5 个 E2E 崩溃）** 方面存在大量严重的生产级缺陷与“假绿”现象。当前代码库**绝不能**标记为 production/live 或 closed。

- **整体判断**：`核心设计架构高度完整，但存在多处 Critical/High 运行时致命缺陷与破坏性数据截断，且测试套件存在大量假绿与并发测试失真，当前全量运行为 9 failed / 432 passed 及 9 项 Ruff 报错，必须坚决打回重修。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 3 个核心判断**：
  1. **持久化与进程生命周期存在 Critical 级致命故障**：`transaction()` 上下文管理器在 `commit()` 抛出异常时未执行 `rollback()`，使单例长连接永久处于未结事务中，直接瘫痪后续所有数据库请求；`SubprocessClaudeCli` 在 `asyncio.wait_for` 超时后未调用 `process.kill()` 和 `wait()`，导致僵尸进程与 FD 泄漏失控。
  2. **数据流转与结构化存在静默破坏性缺陷**：HTML 提取器在最后一步执行 `\s+ -> " "`，彻底抹平了此前注入的所有段落与表格换行；向量化对超过 16k 的 g1/g2 块直接静默丢弃并伪造 100% 成功回执，产生永久检索盲区；Structurizer 文本锚定使用从头搜索 `clean.find(body)`，导致多处重复文本的坐标全部错位至首次出现点。
  3. **测试套件存在严重的“假绿”与测试失真**：发现了 `assert ... or True` 恒真断言、自造 dict 断言自己的假测试、断言未参与调用的局部异常对象、用 8 次串行循环伪装并发写浸泡测试；全量运行中 8 个历史失败因混用原生 `sqlite3.connect` 打开 Turso 库文件及全量调度超时触发，本轮全量复现为 `9 failed / 432 passed`。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `README.md`（45.4 KB 全景架构文档）
  - `docs/baseline/domain-truth/D01-task-execution-process-flow.md`
  - `docs/baseline/domain-truth/D04-turso-physical-schema.md`
  - `docs/baseline/domain-truth/D05-layered-semantic-rag-handbook.md`
  - `docs/baseline/domain-truth/S03-workflow-engine.md`, `S04-intake-asset-lifecycle.md`, `S06-lsrag-structurizer.md`, `S07-lsrag-constructor.md`, `S08-embedding-vectorization.md`, `S10-lsrag-retrieval.md`, `S11-inference-runtime.md`, `S12-turso-persistence.md`, `S16-security-trust-boundary.md`
  - `docs/eval/new-start/after-MKB-0815-R4-first-wave.md`
  - `docs/closure/new-start/deferred-items-ledger.md`
- **核查实现**：
  - `api/` 路由、组合根、S16 鉴权与限流依赖
  - `src/persistence/` 所有 Turso/SQLite 适配器、连接管理、DDL 001–013、`retrieval_access.py`
  - `src/storage/` CAS 对象存储原子性与回收
  - `src/llm_adapters/` 与 `src/runtime/inference/` vLLM、Claude CLI、Facade、SupplyFence、Invocations
  - `src/runtime/workflow/` 调度三池、Claim/Lease/Fencing、Gate 决议、Outcome 回写、Outbox 死信
  - `src/runtime/intake/` Clean、Markdown 转录、Structurize、Construct、Vectorize、Index Rebuild、Snapshot
  - `intake/` HTML/Text/PDF 清洗与 Registered API (ChinaTax, REA, Domain)
  - `tests/` 全量 106 个测试文件、fixtures 与运行时
- **执行过的验证**：
  - `uv run pytest`（全量运行）：耗时 413.46s，结果 `9 failed, 432 passed`
  - `uv run pytest tests/unit/ -k "test_" -q`：`351 passed`
  - `uv run ruff check .`：输出 `9 errors`（包含未使用导入、未排序导入、未捕获 raise from、盲目 assert Exception 等）
  - 全仓语法树扫描、正则模式匹配、Subprocess 生命周期追踪、事务与锁边界静态模拟
- **复用 / 对照的既有审查**：
  - `docs/code-review/new-start/NS2-reviewed-by-sonnet.md`（作为对比线索复核发现，低优先级 salvage 逃逸已通过 `task_priority != "normal"` 修复，但引发了高优先级反向无法 salvage 的新 Bug）
  - `docs/closure/new-start/deferred-items-ledger.md`（复核 NS1-V11 项，确认原生 sqlite3 混用读 Turso 库文件是导致 5 个 E2E 失败的真实根因）

### 1.1 已确认的正面事实

1. **不可变证据链与内容寻址存储（CAS）落地严密**：`src/storage/local_store.py` 严格遵循“先写临时文件 -> fsync -> 原子 rename -> SHA-256 校验”流程，Team 空间与 Handle 校验隔离清晰。
2. **三池调度纯函数与 Claim 事务原子性成立**：`src/runtime/workflow/dispatch.py` 的 `choose_pool` 纯函数对 `urgent`/`high` 锁 NI、`low` 锁 local 逻辑清晰；`_admit_waiting_processes_tx` 在同一写事务内优先于 claim SELECT，且 claim 严格过滤 `dispatch_admitted = 1`。
3. **双重检索服务保护围栏（Double Serving Fence）设计严谨**：`src/persistence/retrieval_access.py` 与 `src/services/retrieval/retrieval_rank.py` 严格同时校验 `active index generation` 与 `mkb_intake_items.lifecycle_state = 'active'`，并验证不可变的 Publication Proof 完整性哈希。
4. **Supply Fence 拒绝静默换供**：`src/runtime/inference/supply.py` 与 `registry.py` 绑定校验在推理请求入口严格 fail-closed，禁止请求体内动态传入未登记 endpoint 或伪造模型。
5. **单元测试与领域状态机覆盖广泛**：`tests/unit/` 绝大部分核心状态机、契约序列化与纯函数测试（351 个）保持通过。

### 1.2 已确认的负面事实

1. **全量测试套件并非全绿**：`uv run pytest` 输出 `9 failed, 432 passed`，其中 5 个由于测试代码混用原生 `sqlite3.connect` 打开 Turso 库文件触发 `disk I/O error`，另 4 个因全量调度超时触发。
2. **静态代码检查门未关闭**：`uv run ruff check .` 报告 9 处错误（`scripts/`, `src/persistence/turso/sidecar.py`, `src/runtime/inference/claude_cli.py`, `tests/`）。
3. **真实推理（Live Inference）不可用**：线上 4 个 R4 真实模型 Cell 均未通过（Prompt/Schema 格式与 Claude CLI 输出异常），离线测试全部依赖 `DeterministicNs1Stub` 伪造通过。
4. **测试中存在明确承认的假并发与伪造浸泡**：`tests/integration/test_ns4_cw_soak.py` 注释承认并发崩溃而改为 8 次串行循环，且断言的是未参与执行的局部变量。
5. **多处数据截断与静默丢弃真实存在**：HTML 提取抹平全部换行、向量化对 >16k 字符静默丢弃、Structurizer 文本锚定从头搜索导致重复文本坐标错位。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|---|---|---|
| 文件 / 行号核查 | `yes` | 逐行阅读并引用全部关键文件（45+ 处精准定位） |
| 本地命令 / 测试 | `yes` | 实际执行全量 `pytest` (9 failed)、单元测试及 `ruff check` (9 errors) |
| schema / contract 反向校验 | `yes` | 校验 DDL 001–013、Pydantic 契约、JSON Schemas 与 Publication Proof 谓词 |
| live / deploy / preview 证据 | `yes` | 对照 `after-MKB-0815-R4-first-wave.md` 核实真实推理失败现状 |
| 与上游 design / QNA 对账 | `yes` | 与 D01–D08 及 S01–S16 设计真相层逐项对账 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|---|---|---|---|---|---|
| **R1** | Claude CLI 子进程超时未 `kill()` 与回收导致僵尸进程与 FD 泄漏 | `critical` | `correctness` + `security` | `yes` | `wait_for` 超时捕获中执行 `process.kill()` 与 `await process.wait()` |
| **R2** | `transaction()` 中 `commit()` 异常未 `rollback()` 导致长连接永久死锁瘫痪 | `critical` | `correctness` | `yes` | 上下文管理器使用 `try...finally` 保证异常必回滚 |
| **R3** | `IndexGenerationRetirementService` 遇失效知识陷入死循环阻塞全库 GC | `critical` | `correctness` | `yes` | 遇到已停用/已撤销 Item 时将清理意图置为 completed/cancelled |
| **R4** | `purge_generation` 单通道软删除破坏 Proof 完整性谓词导致世代全量检索瘫痪 | `critical` | `correctness` | `yes` | 强制全世代 Purge 或更新 Proof 记录并更新 CAS Pointer |
| **R5** | HTML 提取器 `\s+ -> " "` 全局替换破坏所有段落与表格排版 | `critical` | `correctness` | `yes` | 移除末尾全局空白压平正则，保留 `\n` 并折叠空行 |
| **R6** | 向量化对 >16k 字符块静默丢弃并伪造成功回执造成永久检索黑洞 | `critical` | `correctness` | `yes` | 实现语义级二级滑动分块，禁止静默重写 `required_units` |
| **R7** | Structurizer 文本锚定 `clean.find(body)` 从头搜索导致重复文本坐标错位 | `critical` | `correctness` | `yes` | 引入阅读顺序游标匹配与动态规划对齐算法 |
| **R8** | `_deduplicate` 优先级反转导致高分 `original` 被低分 `summary` 错误置换 | `high` | `correctness` | `yes` | 将 `not_needed` 与 `resolved` 归为同一最高优先级，按得分择优 |
| **R9** | `_inflate_documents` 继承 `query.filters` 导致 `channel="original"` 膨胀必崩 | `high` | `correctness` | `yes` | 内部拓扑寻根查询剥离外部 channel 过滤参数 |
| **R10** | `LocalVllmAdapter` 每次请求局部新建 `AsyncClient` 导致连接池失效 | `high` | `platform-fitness` | `no` | 在 Adapter 内维护单例 `httpx.AsyncClient` 并管理生命周期 |
| **R11** | `OVER_BUDGET_PROCESS_KEYS` 遗漏 `transcribe` 与 `construct` 导致 OOM 风险 | `high` | `correctness` | `yes` | 将两项生成任务纳入 over budget 集合允许溢出分流 |
| **R12** | `_can_salvage_local_inference` 优先级逆变导致 `urgent`/`high` 任务无法降级熔断 | `high` | `correctness` | `yes` | 修改优先级判定为 `task_priority in {"normal", "high", "urgent"}` |
| **R13** | `_ns1_prompt_file` 在 `state=None` 时直接读取本地文件绕过 Snapshot 校验 | `high` | `security` | `yes` | 强制要求传入有效 state 与 role，缺失时严格 fail-closed |
| **R14** | `LocalObjectStore.delete_if_unreferenced` 未加锁导致与 `promote()` 并发竞态 | `high` | `correctness` | `yes` | 物理删除方法纳入 `self._write_lock` 互斥保护 |
| **R15** | Object GC 先物理 unlink 后提交 DB 事务导致事务回滚时数据不可逆损坏 | `high` | `correctness` | `yes` | 改为“先提交 Tombstone 事务，后物理 unlink”二阶段安全协议 |
| **R16** | Worker 崩溃导致暂存 CAS 物理文件永久泄漏（GC 缺乏磁盘反向扫描） | `high` | `platform-fitness` | `no` | 增加物理 CAS 目录对数据库的反向对账扫描与孤儿清理 |
| **R17** | `TursoPersistence` 缺少 `busy_timeout` 且与 Sidecar 产生并发锁冲突 Panic | `high` | `platform-fitness` | `yes` | 显式配置 `PRAGMA busy_timeout=5000`，移除 Sidecar 动态设 mode |
| **R18** | `probe_concurrent_writes` 健康探针切回模式破坏生产库 MVCC 配置 | `high` | `correctness` | `yes` | 禁止在生产主连接上动态修改并还原 `journal_mode` |
| **R19** | 反向代理下 `request_ip` 恒为私网导致 `/internal` 运维与 `/metrics` 接口暴露 | `high` | `security` | `yes` | 引入受信任代理网段配置并从 Forwarded 头安全解析真实客户端 IP |
| **R20** | `FixedWindowRateLimiter` 桶超限抛异常被捕获后全局 Fail-Open 限流失效 | `high` | `security` | `yes` | 引入 LRU 或溢出桶聚合，超限时实施保底限流而非全放行 |
| **R21** | `OutcomeArtifactCommitter` 内存字典未清理导致内存泄漏且无法分布式共享 | `high` | `platform-fitness` | `no` | commit 成功后 pop 清理，长远引入持久化暂存表 |
| **R22** | HTML Sanitizer 允许任意 `href`/`src` 协议导致存储型 XSS 漏洞 | `high` | `security` | `yes` | 对 URL scheme 强制白名单校验（仅允许 http/https/mailto） |
| **R23** | 本地 PDF 文本提取在 raw bytes 上正则扫描导致压缩 PDF 失败及 UTF-16 乱码 | `high` | `correctness` | `no` | 集成轻量标准 PDF 流解析库，杜绝 raw binary 正则假提取 |
| **R24** | ChinaTax / REA Provider 外部键与 HTML 解析缺陷导致主键冲突与排版压平 | `high` | `correctness` | `yes` | 严格校验 ID 避免转为 `"None"`，用真实正则识别 HTML 标签 |
| **R25** | Structurizer 粒度闭集在短文本上硬性报错 `GRANULARITY_SET_MISMATCH` | `high` | `correctness` | `no` | 允许短文本自适应退化或由 kernel 自动补全 g1/g2 锚定 |
| **R26** | C 阶段对 Original 内容强行逐字校验导致标点/转义微调时全包生成失败 | `high` | `correctness` | `no` | 采用以 `block_id` 为准的单向回填策略，降低对原文完全一致的过敏 |
| **R27** | `test_turso_driver.py` 包含 `assert ... or True` 恒真永绿断言 | `high` | `test-gap` | `yes` | 移除 `or True`，编写真实属性断言 |
| **R28** | `test_ns4_readport_reports.py` 自造字典断言自己，完全未调用被测类 | `critical` | `test-gap` | `yes` | 移除手工造假字典，通过真实服务接口传入数据测试契约 |
| **R29** | `test_ns4_diagnostic_sidecar.py` 断言未参与调用的局部 MkbError 对象 | `critical` | `test-gap` | `yes` | 注入故障 Sidecar 并断言真实业务流程中的错误码保持 |
| **R30** | `test_ns4_cw_soak.py` 用 8 次串行 for 循环冒充并发写浸泡测试并断言孤立变量 | `critical` | `test-gap` | `yes` | 改为真实多协程并发写入并断言数据库行数 |
| **R31** | 测试依赖文件缺失时通过 `if not file.is_file(): return` 静默假绿 | `high` | `test-gap` | `yes` | 改为显式 `pytest.skip` 并在遍历后断言匹配行数大于 0 |
| **R32** | E2E 测试使用原生 `sqlite3.connect` 检查 Turso 库导致 5 个用例崩溃 | `high` | `test-gap` | `yes` | 统一使用容器内置 `persistence` 或 `turso.connect` 检查 |
| **R33** | E2E 黄金摄取流水线被 `_LiveEmbeddingFixture` 全量 Mock 短路核心模型通信 | `high` | `test-gap` | `no` | 改在网络传输层使用 `httpx.MockTransport` 做协议级 Mock |
| **R34** | `test_ns4_sink_required.py` 内部完全缺失 `assert` 语句 | `medium` | `test-gap` | `no` | 补充显式断言检查调用结果或状态 |
| **R35** | 单元测试中大量读取源码做文本正则扫描伪装为行为测试 | `medium` | `test-gap` | `no` | 将 AST/文本扫描移至 `test_architecture.py`，单元测试走真实调用 |
| **R36** | Context Packing 对同代多 Hit 重复填充相同 Document Root 挤爆上下文 | `medium` | `correctness` | `no` | 增加已填充 Root 坐标去重集，同代仅填充一次 |
| **R37** | Reactivate 后 `index.rebuild` API 准入通过但 Worker 执行必崩 | `medium` | `correctness` | `no` | 准入层提前校验 Serving 状态，未就绪时即时返回 409 |
| **R38** | Process 重试缺乏指数退避与 Jitter 导致固定 1s 重试引发惊群雪崩 | `medium` | `platform-fitness` | `no` | 引入基于 retry_count 的全抖动指数退避算法 |
| **R39** | 取消状态下消费 Gate Decision 引发死信 Outbox 恶性重试 8 次 | `medium` | `correctness` | `no` | 检测到取消状态时直接将 Gate Outbox 标记为已完成 |
| **R40** | Outbox 进入 dead 状态未写入领域事件与监控告警导致任务静默死亡 | `medium` | `platform-fitness` | `no` | 在同事务中写入 `outbox.dead` 领域事件并递增指标 |
| **R41** | 迁移 010 使用 `lower(hex(randomblob(16)))` 生成 32 位 ID 破坏 UUID 校验 | `medium` | `correctness` | `no` | SQL 中按 `8-4-4-4-12` 格式化为标准 UUID 字符串 |
| **R42** | 时间戳微秒 (Python) 与毫秒 (SQLite) 精度不一致导致 SQL 比较偏差 | `medium` | `correctness` | `no` | 全系统统一通过 Python `utc_now()` 写入标准时间字符串 |
| **R43** | `coerce_json_object_text` 贪婪切片在 LLM 输出带外层括号时解析崩溃 | `medium` | `correctness` | `no` | 改用基于栈的 JSON 深度括号匹配器 |
| **R44** | ConcurrencyGate 在重试退避期间仍持有 Lease 导致级联 503 拒绝 | `medium` | `platform-fitness` | `no` | 在 sleep 退避前释放 lease，sleep 结束后重新获取 |
| **R45** | Ruff 静态检查存在 9 个错误未修复 (F401, I001, B904, B017, F811, F841) | `medium` | `test-gap` | `yes` | 运行 `ruff check --fix` 并手动清理剩余错误 |

---

### R1. Claude CLI 子进程超时未 `kill()` 与回收导致僵尸进程与 FD 泄漏

- **严重级别**：`critical`
- **类型**：`correctness` + `security`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/runtime/inference/claude_cli.py:300-304`](file:///root/workspace/myknowledgebase/src/runtime/inference/claude_cli.py#L300-L304)：
    ```python
    try:
        stdout_bytes, stderr_bytes = await asyncio.wait_for(
            process.communicate(payload), request.timeout_seconds
        )
    except TimeoutError as exc:
        raise MkbError("CLAUDE_CLI_TIMEOUT", "Claude CLI invocation timed out", 503) from exc
    ```
- **为什么重要**：
  `asyncio.wait_for` 超时仅取消了当前的 Python 协程等待，底层的 OS 子进程 `process` 仍在不受控地运行。代码未调用 `process.kill()`，也未 `await process.wait()`。
- **审查判断**：
  在生产高压或网络超时场景下，失控的 Claude CLI 进程会在宿主机后台大量累积，不仅持续消耗 CPU/RAM 与远端 API 配额，而且未关闭的 stdin/stdout/stderr 管道会迅速耗尽 Linux 文件描述符（FD）和 PID，导致整个主机级服务拒绝服务（DoS）。
- **建议修法**：
  ```python
  except (TimeoutError, asyncio.CancelledError) as exc:
      try:
          process.kill()
          await process.wait()
      except Exception:
          pass
      raise MkbError("CLAUDE_CLI_TIMEOUT", "Claude CLI invocation timed out", 503) from exc
  ```

---

### R2. `transaction()` 中 `commit()` 异常未 `rollback()` 导致长连接永久死锁瘫痪

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/persistence/sqlite_port.py:84-95`](file:///root/workspace/myknowledgebase/src/persistence/sqlite_port.py#L84-L95) 与 [`src/persistence/turso/port.py:88-99`](file:///root/workspace/myknowledgebase/src/persistence/turso/port.py#L88-L99)：
    ```python
    @asynccontextmanager
    async def transaction(self) -> AsyncIterator[SqliteUnitOfWork]:
        async with self._write_lock:
            connection = self._connect()
            await asyncio.to_thread(connection.execute, "BEGIN IMMEDIATE")
            try:
                yield SqliteUnitOfWork(connection)
            except Exception:
                await asyncio.to_thread(connection.rollback)
                raise
            else:
                await asyncio.to_thread(connection.commit)
    ```
- **为什么重要**：
  在 Python 的 `try...except...else` 中，`else` 块发生在 `try` 外部。当 `yield` 正常退出后进入 `else` 执行 `connection.commit()`，若 `commit()` 抛出异常（如锁争抢 `SQLITE_BUSY`、延迟外键约束失败、磁盘满等），`except` **不会捕获它**，`connection.rollback()` 永远不会被执行！
- **审查判断**：
  由于 `self._connection` 是单例长连接，连接将永久停留在未完结的未提交事务中。后续任何请求再次调用 `transaction()` 并执行 `BEGIN IMMEDIATE` 时，SQLite/Turso 均会抛出 `cannot start a transaction within a transaction`，导致整个服务持久化层永久瘫痪，直到进程被强制重启。
- **建议修法**：
  将 `commit()` 纳入 `try` 块或采用 `try...finally` 结构，确保未标记成功时必定触发 `rollback()`。

---

### R3. `IndexGenerationRetirementService` 遇失效知识陷入死循环阻塞全库 GC

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/services/index_retirement.py:320-327, 402-406, 497-518`](file:///root/workspace/myknowledgebase/src/services/index_retirement.py#L320-L327)：
    在 `soft_purge` 中调用 `_active_pointer_tx`，若 Item 已被 `deactivate` 或 `delete`，其状态变为 `deactivated`/`deleted`，Pointer 为 `withdrawn`，`_active_pointer_tx` 返回 `None`。`soft_purge` 捕获后直接返回 `POINTER_UNAVAILABLE`，**但未更新 intent 的状态（保持 `status='open'`）**。
- **为什么重要**：
  后台扫描器通过 `SELECT ... WHERE status='open' AND eligible_at <= now ORDER BY eligible_at LIMIT 100` 拾取任务。这些卡住的 intent 会永久占据队列头部。
- **审查判断**：
  一旦此类失效 intent 累积达到 100 个，`collect_due` 每次都将只返回这 100 个无法处理的死任务，导致**全系统所有正常的旧世代向量垃圾回收全部永久停滞（Head-of-Line Blocking）**，引发严重的数据库存储泄漏。
- **建议修法**：
  检测到 Item 已处于 `deactivated`/`deleted` 状态时，直接执行软删除并将 intent 标记为 `completed` 或转入专门的终态，严禁让未决 intent 长期滞留在 `open` 状态。

---

### R4. `purge_generation` 单通道软删除破坏 Proof 完整性谓词导致世代全量检索瘫痪

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/services/vector_purge.py:58-65`](file:///root/workspace/myknowledgebase/src/services/vector_purge.py#L58-L65) 与 [`src/services/retrieval/models.py:59-75`](file:///root/workspace/myknowledgebase/src/services/retrieval/models.py#L59-L75)：
    `VectorGenerationPurger` 允许 `channel_filter="original"` 仅软删除某个通道的向量记录。然而检索时的双重围栏严格依赖 SQL 谓词 `_PROOF_COMPLETE_SET_PREDICATE`：
    ```sql
    proof.actual_count=(SELECT COUNT(*) FROM mkb_vector_records AS proof_record
    WHERE ... AND proof_record.deleted_at IS NULL AND proof_record.publication_state='indexed')
    ```
- **为什么重要**：
  单通道删除后，未删除记录总数小于 `proof.actual_count`，完整性断言直接失败。
- **审查判断**：
  单通道 Purge 会导致该世代下剩余的所有未删除向量（如 summary 向量）在检索阶段被双重 Fence 100% 阻断，导致该知识在整个系统内完全无法被查出。
- **建议修法**：
  禁止孤立的单通道 Purge，强制 `purge_generation` 必须为全世代；或在单通道删除后同步生成新的 Publication Proof 并通过 CAS 更新指针。

---

### R5. HTML 提取器 `\s+ -> " "` 全局替换破坏所有段落与表格排版

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`intake/text.py:102-113`](file:///root/workspace/myknowledgebase/intake/text.py#L102-L113)：
    `DeterministicHtmlTextExtractor` 精细处理了 `_BLOCK` 标签并插入 `\n`，但在提取末尾执行了：
    ```python
    clean = _SPACE.sub(" ", canonical_text("".join(extractor.parts))).strip()
    ```
    其中 `_SPACE = re.compile(r"\s+")`。
- **为什么重要**：
  所有插入的换行符 `\n` 均被强制替换为**单个空格**。
- **审查判断**：
  整篇 HTML 文档被强行压平为无段落、无标题、无换行的单行扁平文本，彻底摧毁了文档的层次结构与表格二维关系，下游 B.json 结构化模型无法识别段落。
- **建议修法**：
  移除末尾的 `_SPACE.sub(" ", ...)`，改用保留换行并折叠连续空行（如 `\n{3,} -> \n\n`）的清洗逻辑。

---

### R6. 向量化对 >16k 字符块静默丢弃并伪造成功回执造成永久检索黑洞

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/runtime/intake/vectorize.py:186-205, 247-250`](file:///root/workspace/myknowledgebase/src/runtime/intake/vectorize.py#L186-L205)：
    ```python
    embeddable = [item for item in vector_inputs if len(item.content_full) <= _LIVE_EMBED_CHAR_BUDGET]
    vector_inputs = embeddable
    ...
    handoff = VectorizeHandoffV1(
        required_units=len(vector_inputs),
        succeeded_units=len(vector_inputs),
        skipped_empty_units=len(plan.skipped),
    )
    ```
- **为什么重要**：
  超过 16,000 字符的 g1/g2 块被直接从 `vector_inputs` 列表中就地过滤丢弃，且未进行子切分，随后 `required_units` 被重写为过滤后的长度并上报 100% 成功。
- **审查判断**：
  长篇章节在没有任何告警的情况下永久丢失向量索引，在检索端形成不可召回的永久黑洞（Recall Black Hole）。
- **建议修法**：
  对超预算块实施语义感知的二级滑动窗口切分（Sub-chunking），严禁静默重写 `required_units`。

---

### R7. Structurizer 文本锚定 `clean.find(body)` 从头搜索导致重复文本坐标错位

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/services/lsrag_compiler/adopt.py:226-235`](file:///root/workspace/myknowledgebase/src/services/lsrag_compiler/adopt.py#L226-L235)：
    ```python
    first_char = clean.find(normalized_body)
    start = _byte_offset(clean, first_char)
    finish = _byte_offset(clean, first_char + len(normalized_body))
    ```
- **为什么重要**：
  `clean.find()` 永远从索引 0 开始搜索。文档中重复出现的章节名（如 "Overview"、"Notes"）、相同数值、重复免责声明等，其第 2、第 3 个 block 的字节区间全部被错误锚定到第 1 处出现的位置。
- **审查判断**：
  `TextSpan` 坐标物理重叠错位，破坏了分层树状拓扑和阅读顺序。
- **建议修法**：
  引入阅读顺序单调递增游标（Monotonic Cursor），优先匹配当前游标之后的首次出现点。

---

### R28. `test_ns4_readport_reports.py` 自造字典断言自己，完全未调用被测类

- **严重级别**：`critical`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`tests/unit/test_ns4_readport_reports.py:8-23`](file:///root/workspace/myknowledgebase/tests/unit/test_ns4_readport_reports.py#L8-L23)：
    ```python
    def test_generation_evidence_bundle_shape() -> None:
        service = ObservabilityReadService.__new__(ObservabilityReadService)
        bundled = {"p1": {"invocations": [{"status": "failed", ...}], "reports": [...]}}
        event = {"process_uuid": "p1", "event_type": "process.status_changed"}
        extra = bundled.get(str(event.get("process_uuid") or ""), {})
        event["generation_invocations"] = extra.get("invocations", [])
        event["generation_stage_reports"] = extra.get("reports", [])
        assert event["generation_invocations"][0]["status"] == "failed"
        assert "structure_reject" not in event
    ```
- **为什么重要**：
  测试通过 `__new__` 实例化后**从未调用 `service` 的任何方法**，而是手工构造字典并断言自己赋值的字典字段。
- **审查判断**：
  这是典型的欺骗性“假绿测试”，被测核心代码完全未被执行，Ruff 也给出了 `F841 Local variable 'service' is assigned to but never used` 警告。
- **建议修法**：
  重写该测试，通过真实的 `ObservabilityReadService` 公共接口传入数据进行端到端契约校验。

---

### R29. `test_ns4_diagnostic_sidecar.py` 断言未参与调用的局部 MkbError 对象

- **严重级别**：`critical`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`tests/unit/test_ns4_diagnostic_sidecar.py:23-28`](file:///root/workspace/myknowledgebase/tests/unit/test_ns4_diagnostic_sidecar.py#L23-L28)：
    ```python
    def test_sidecar_failure_does_not_change_product_code() -> None:
        from src.contracts.common.errors import MkbError
        err = MkbError("STRUCTURE_ANCHOR_MISSING", "missing", 422)
        assert err.code == "STRUCTURE_ANCHOR_MISSING"
    ```
- **为什么重要**：
  测试标题声称验证 Sidecar 失败不影响产品错误码，实际只在本地构造了一个 `MkbError` 实例并断言它的入参属性。
- **审查判断**：
  完全没有调用 Sidecar 或 Sink，纯属假断言。
- **建议修法**：
  注入故障 Sidecar 并断言真实业务流程中的错误码保持不变。

---

### R30. `test_ns4_cw_soak.py` 用 8 次串行 for 循环冒充并发写浸泡测试并断言孤立变量

- **严重级别**：`critical`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`tests/integration/test_ns4_cw_soak.py:53-58`](file:///root/workspace/myknowledgebase/tests/integration/test_ns4_cw_soak.py#L53-L58)：
    ```python
    # This engine aborts if many threads open BEGIN CONCURRENT together.
    # Soak the sidecar serially: the product code must stay untouched.
    for index in range(8):
        _one(index)
    assert product.code == "STRUCTURE_ANCHOR_MISSING"
    ```
- **为什么重要**：
  测试注释直接承认“多线程 BEGIN CONCURRENT 会崩溃因此改为串行”；同时 `product` 变量在循环外部创建且从未传入 `_one` 函数。
- **审查判断**：
  串行冒充并发浸泡，断言与被测调用完全脱节，掩盖了底层并发写崩溃。
- **建议修法**：
  使用 `asyncio.gather` 进行真实多协程/多线程并发写入，断言真实的数据库行数。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|---|---|---|---|
| S1 | 异步任务状态机与耐久工作流 (claim, lease, fencing) | `done` | 核心状态机与 fencing token 约束严密 |
| S2 | 多来源确定性摄取 (inline, static, PDF, registered API) | `partial` | HTML 换行被抹平 (R5)，PDF 提取脆弱 (R23)，ChinaTax 缺 ID 赋为 `"None"` (R24) |
| S3 | LS-RAG 分层生成与双通道可追溯性 | `partial` | 锚定算法从头搜索错位 (R7)，超长块静默丢弃 (R6)，C 原文过敏 (R26) |
| S4 | 向量发布双重 Serving Fence 与 Context-only 检索 | `partial` | 根文档膨胀在 original 通道必崩 (R9)，去重优先级反转 (R8)，Purge 毁 Proof (R4) |
| S5 | 本地 Turso Database 并发与 CAS 存储 | `partial` | `transaction()` 缺回滚死锁 (R2)，Sidecar 并发冲突 (R17)，GC 物理删除时序错 (R15) |
| S6 | LLM Adapter (vLLM / Claude CLI) 与调度三池 | `partial` | CLI 僵尸进程泄漏 (R1)，连接池缺失 (R10)，预算键遗漏 (R11)，优先级逆变 (R12) |
| S7 | 安全边界与 S16 鉴权/限流 | `partial` | 反向代理私网绕过 (R19)，限流超限 Fail-Open (R20)，Sanitizer 缺协议过滤 (R22) |
| S8 | 测试套件完整性与真实性 | `missing` | 存在多处假绿与无效断言 (R27-R31)，全量 9 failed / 9 ruff errors，Mock 短路核心 (R33) |

### 3.1 对齐结论

- **done**: 1
- **partial**: 6
- **missing**: 1
- **stale**: 0
- **out-of-scope-by-design**: 0

> 总结：当前代码库处于**“骨架与核心合同设计完备，但各子系统落地实现中存在多处致命逻辑缺陷、数据截断与测试严重失真”**的未收口状态。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|---|---|---|---|
| O1 | 浏览器渲染、OCR、Vision、文档清洗 LLM 运行时 | `遵守` | 代码保持合同与稳定拒绝路径，未伪造 live 宣称 |
| O2 | Registered API 实时供应商网络请求与分页客户端 | `遵守` | 保持由调用方提交冻结 records 输入 |
| O3 | 终端用户登录、前端 UI、平台级 RBAC、真实计费 | `遵守` | 前端为占位，计费明确为 Stub |
| O4 | R5 方案（system-owned g0 与 quoted cuts）| `遵守` | 保持为计划中，未提前混入未经验收的半成品 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`MKB 当前实现主体骨架成立且具备高水准的设计契约，但存在 7 个 Critical 级与 19 个 High 级实质缺陷（包含 5 处严重测试假绿/伪造），全量测试未通过（9 failed / 9 ruff errors），真实推理未闭环，坚决不予通过本轮审查。`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker 清单**：
  1. **[R1] 修复 Claude CLI 僵尸进程与 FD 泄漏**：在 `wait_for` 超时和取消捕获中显式 `kill()` 并 `await wait()`。
  2. **[R2] 修复事务管理器死锁缺陷**：重构 `TursoPersistence.transaction()` 与 `SqlitePersistence.transaction()`，确保 `commit()` 失败时触发 `rollback()`。
  3. **[R3] 修复 Index Retirement 队头阻塞**：失效 Item 的旧世代清理 intent 标记为终态，解除垃圾回收死循环。
  4. **[R4] 修复 Purge 破坏 Proof 缺陷**：禁用孤立单通道 Purge 或同步更新 Proof 与 CAS 指针。
  5. **[R5] 修复 HTML 文本提取排版抹平**：移除末尾全局空白压平正则，保留段落与表格结构。
  6. **[R6] 修复向量化超长块静默丢弃**：实现二级滑动切分，杜绝静默重写 `required_units`。
  7. **[R7] 修复 Structurizer 文本锚定错位**：引入阅读顺序单调游标匹配。
  8. **[R8 & R9] 修复检索去重优先级反转与根文档膨胀崩溃**：修正 `_dedup_key` 优先级，并在拓扑寻根中剥离外部 channel 过滤。
  9. **[R11 & R12] 修复调度预算键遗漏与优先级逆变**：补齐 `OVER_BUDGET_PROCESS_KEYS`，修正 salvage 优先级判定。
  10. **[R17 & R18] 修复 Turso 并发连接与探针模式污染**：增加 `busy_timeout`，移除探针对生产主连接模式的动态修改。
  11. **[R19 & R20 & R22] 修复反向代理私网绕过、限流 Fail-Open 与 XSS 漏洞**。
  12. **[R27–R32, R45] 清理所有假绿测试与静态检查报错**：移除 `assert ... or True`、重构假字典/孤立变量测试、统一 E2E 数据库检查适配器消除 5 个 I/O 错误，达成全量 `pytest` 441/441 真实全绿与 `ruff check` 0 报错。
- **可以后续跟进的 non-blocking follow-up**：
  1. [R10] `LocalVllmAdapter` 连接池生命周期管理与单例复用。
  2. [R16] CAS 存储增加对磁盘物理目录的反向孤儿扫描。
  3. [R21] `OutcomeArtifactCommitter` 内存暂存向分布式持久化表演进。
  4. [R23] 集成轻量标准 PDF 流解析库替代 raw binary 正则。
  5. [R36] Context Packing 增加同代 Root 去重集以优化 Token 窗口。
- **建议的二次审查方式**：`independent reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> **本轮 review 不收口，等待实现者按 §6 响应并更新代码后重新审查。**
