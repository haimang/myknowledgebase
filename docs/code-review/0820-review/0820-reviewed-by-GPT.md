# MKB 全代码库严格审查

> 审查对象: `myknowledgebase @ 5e64a1e25786355b33811140da9b55ff995a8234`
> 审查类型: `mixed`
> 审查时间: `2026-08-20`
> 审查人: `GPT / Codex 主审（聚合 LLM、Turso、Knowledge、LS-RAG、并发与测试专项子审查）`
> 审查范围:
> - `api/`, `src/`, `intake/`, `tests/`, `scripts/`, `data/`, `pyproject.toml`, `uv.lock`
> - public/internal endpoint、workflow supervisor/worker、LLM Adapter、Turso、CAS、Knowledge/LS-RAG、retrieval、全测试面
> 对照真相:
> - `README.md`
> - `docs/baseline/domain-truth/D01-D08.md` 所代表的 D01-D08 真相层（按实际文件拆分）
> - `docs/baseline/domain-truth/S01-S16.md` 所代表的 S01-S16 真相层（重点 S03/S04/S05/S06-S13/S15/S16）
> - `.adocs/code-review.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 该实现包含不少正确的合同与 fencing 原语，但当前存在可复现的进程崩溃、连接污染、错误并发能力声明、推理重复执行、对象生命周期失效和大量测试假绿；不能按 production-ready 或 completed 收口。

- **整体判断**：`核心骨架可辨认，但 persistence、inference、CAS lifecycle 和验证证据均有 blocker。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. Turso transaction cancellation 可污染唯一连接，diagnostic sidecar 的真实并发可触发 pyturso native panic/进程 `exit 134`；这是运行安全 blocker。
  2. 30 秒 Process lease 没有 heartbeat，却允许 180/900 秒推理；同时唯一 supervisor 串行执行，声明的 `2/2/8` pool cap 不是实际并发能力。
  3. Retrieval 只按 UUID 扫前 1000 条且 native ANN 未接线；对象 GC 又没有 production release/真实 orphan 路径，相关 green tests无法证明 Knowledge Base 的规模正确性与生命周期闭环。
- **Finding 统计**：`45` 条（`5 critical / 24 high / 14 medium / 2 low`），其中 `28` 条标记为 blocker。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `README.md`（完整读取 627 行）
  - `.adocs/code-review.md`（完整读取 177 行）
  - `docs/baseline/domain-truth/` 中与入口、workflow、intake、LS-RAG、Turso、storage、observability、安全相关的真相层
- **核查实现**：
  - `api/app.py`, `api/dependencies.py`, `api/public/routes.py`, `api/internal/routes.py`
  - `src/runtime/workflow*`, `src/runtime/intake/`, `src/runtime/inference/`, `src/llm_adapters/`
  - `src/persistence/`, `src/storage/`, `src/services/`, `src/workflows/`, `intake/`
  - `tests/unit`, `tests/domain`, `tests/integration`, `tests/e2e`, `tests/intake`
- **执行过的验证**：
  - `uv run pytest` → 本轮并行审查负载下为 `431 passed / 10 failed`，耗时约 `414.61s`；失败含长期 `running`、raw sqlite inspection 的 `disk I/O error/file is not a database` 和真实 profile failure。该数字不冒充稳定串行基线，但足以证明当前全量不绿。
  - `uv run ruff check .` → `9 errors`。
  - LLM 定向测试：`39 passed` 与证据/readiness 定向测试 `21 passed`；同时独立 live-profile case 连续卡在固定 5 秒轮询，退出 lifespan 后最终成功。
  - Turso/GC 定向 suite：`16 passed`；但独立故障注入仍稳定复现 cancellation 污染、并发 migrate/transaction lock、sidecar native abort、真实 orphan 不可回收和 tombstone reuse。
  - 临时库/子进程复现：Turso+SQLite cancellation、4-thread sidecar、双 adapter migrate/write、wheel 解包启动、drop-table readiness、CAS orphan/tombstone reuse、损坏 object identity。
  - 合同最小复现：明文 token 出现在 `Settings` repr/dump；Team/Task payload extra 接受 secret key；signed URL 被接受；单条 1,000,000 字符 registered record 被接受；非有限 metadata 值被静默 JSON 化为 `null`。
  - 依赖清单与官方安全公告核对：当前 `starlette==0.46.2`。
- **复用 / 对照的既有审查**：
  - 未把历史 closure/既有 review 当作成立证据；只将 README 的已知失败当线索并用当前 HEAD 复核。
  - 审查过程中出现的 `docs/code-review/new-start/0820-reviewed-by-gemini.md` 是外部并发改动，本报告未采纳其结论，也未修改该文件。

### 1.1 已确认的正面事实

- public Task/retrieval 主路径先做 token dependency；实测“无 token + malformed Task body”返回 `401 SEC_TOKEN_MISSING`，没有先泄露 schema/resource 差异。
- SQL 请求值普遍参数绑定；本轮没有发现请求可控的表名/列名 SQL injection。
- vector publication 的 record、proof、active-pointer CAS 与 serving revision 主体在一个 UoW 内；单进程、无 cancellation 时原子性设计成立。
- retrieval 对 Team UUID、active generation、Intake serving revision 有双 fence，并对 hydrated CAS body 再做 size/digest/schema 校验；Team lifecycle status 另见 R32。
- prompt 文件 traversal/hash mismatch、模型 binding identity 和 public error 基础脱敏存在明确 fail-closed 原语。

### 1.2 已确认的负面事实

- production Turso UoW 不是 cancellation-safe；所谓 Concurrent Writes probe 与真实业务 transaction/multi-instance 行为不一致。
- CLI 与 vLLM 路径没有形成统一的 frozen model/schema/supply/evidence 语义；fallback 会绕开 lane cap，并能污染后续 Process 的 evidence。
- CAS 的 release、orphan reconciliation、tombstone reuse 三个生命周期闭环均未成立；成功 Process 还会永久留在内存 `_pending`。
- 多个名为 integration/e2e/soak/live 的测试没有执行其标题声称的生产路径，或包含永真断言、手工证据、私有 helper、stock sqlite 检查 Turso、固定短轮询。
- 构建成功不代表可部署：wheel 不含 migration SQL，也不含运行所需 prompt/config/schema assets。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 每条 finding 指向当前 HEAD 的实现/测试行号。 |
| 本地命令 / 测试 | `yes` | 全量、定向 suite、临时库和独立子进程复现均有使用。 |
| schema / contract 反向校验 | `yes` | 核对 migration、Pydantic contract、artifact/pointer/object ledger 与 public projection。 |
| live / deploy / preview 证据 | `partial` | 没有真实 vLLM/GPU/Claude 登录态和生产 edge；wheel、embedded Turso、子进程行为已本地验证。 |
| 与上游 design / QNA 对账 | `yes` | 以 domain-truth 的 frozen/accepted 不变量为对照；draft plan 不作为完成证据。 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | cancellation 可永久污染唯一 DB 连接 | `critical` | correctness | `yes` | 重做 cancellation-safe UoW |
| R2 | Turso diagnostic sidecar 并发触发 native abort | `critical` | correctness | `yes` | 禁止当前并发写法 |
| R3 | wheel 缺 migration SQL，安装制品无法启动 | `critical` | delivery-gap | `yes` | 修复 package-data 并做安装 smoke |
| R4 | Concurrent Writes/readiness 为错误能力证明，多实例立即锁失败 | `high` | platform-fitness | `yes` | singleton fail-closed 或实现真并发 |
| R5 | 30 秒 lease 无 heartbeat，长推理会被重复执行 | `high` | correctness | `yes` | worker heartbeat + transport cancel |
| R6 | 唯一 supervisor 串行执行，pool running cap 是假并发 | `high` | delivery-gap | `yes` | per-pool bounded worker set |
| R7 | Claude timeout/cancel 不回收子进程，输出也无上限 | `high` | correctness | `yes` | kill/wait + bounded streaming |
| R8 | Claude/salvage 绕开 frozen binding、NI cap 与真实 quota | `high` | protocol-drift | `yes` | typed durable fallback Process |
| R9 | CLI 泄露知识正文与父进程全部环境 secret | `high` | security | `yes` | stdin-only + env allowlist |
| R10 | salvage 失败证据可串到另一 Process/Team，失败 inference ledger 缺失 | `high` | correctness | `yes` | transaction-aware evidence |
| R11 | schema 未真正冻结/校验，live readiness 可在 supply 全坏时为 ready | `high` | correctness | `yes` | freeze schema bytes + exact probes |
| R12 | 对象 release 与真实 orphan GC 均未实现 | `high` | correctness | `yes` | release owner + FS reconciliation |
| R13 | tombstoned digest 可被新 live reference 复用 | `high` | correctness | `yes` | active partial uniqueness/trigger |
| R14 | OutcomeArtifactCommitter 永不清理 `_pending` | `high` | correctness | `yes` | post-commit ack/有界回收 |
| R15 | local/registered/browser acquisition 绕过预算并写入虚假 budget proof | `high` | security | `yes` | catalog-aware bounded streaming |
| R16 | 公共输入可持久化 secret/signed URL，且无总量/有限数值约束 | `high` | security | `yes` | 统一敏感字段与 aggregate budget |
| R17 | object/schema readiness 可把损坏或错挂载状态判为 ready | `high` | platform-fitness | `yes` | DB↔object identity/schema manifest |
| R18 | PDF/doc LLM 把二进制静默替换解码为文本 | `high` | correctness | `yes` | typed attachment 或拒绝 blob |
| R19 | 推理重试缺少 idempotency，退避期间占满 gate | `medium` | correctness | `no` | attempt identity/circuit breaker/jitter |
| R20 | Turso/CW/sidecar/GC 测试存在系统性假绿 | `critical` | test-gap | `yes` | 用独立进程/真实路径重写 |
| R21 | ReadPort/fail-path/live E2E 手工造结果或替换生产逻辑 | `high` | test-gap | `yes` | 从 public/worker 入口端到端验证 |
| R22 | 固定轮询与 stock sqlite inspection 造成假红/顺序依赖 | `medium` | test-gap | `no` | condition-driven drain + Turso ReadPort |
| R23 | 当前全量测试和 Ruff 均不绿 | `high` | delivery-gap | `yes` | 修复后无排除串行复跑 |
| R24 | Starlette 0.46.2 命中已公开 Host/request.url 漏洞范围 | `medium` | security | `no` | 升级兼容 FastAPI/Starlette |
| R25 | idle worker 约每 50ms 执行完整、会切 journal mode 的 readiness | `medium` | platform-fitness | `no` | 缓存静态能力、轻量健康快照 |
| R26 | Retrieval 只按 UUID 扫前 1000 条，native ANN 从未接线 | `critical` | correctness | `yes` | 实现 VectorSearchPort/native top-k |
| R27 | offline 查询可静默混用 live embedding 空间 | `high` | correctness | `yes` | Layer-A tuple 决定查询 embed |
| R28 | live vectorize 静默丢 required units 后仍签 full-valid | `high` | correctness | `yes` | required-set 必须完整成功 |
| R29 | 同一逻辑来源重复 ingest 总是新建 Source/Item | `high` | correctness | `yes` | 稳定 source/item resolve + Revision CAS |
| R30 | 重复文本 anchor 永远指向第一次出现 | `high` | correctness | `yes` | 单调/唯一 anchor 或拒绝歧义 |
| R31 | IntakeArtifact handle/digest/size 不描述同一 bytes | `high` | correctness | `yes` | raw/clean 分别 promote 真正 representation |
| R32 | Team inactive/deleted 后仍可 retrieval | `high` | security | `yes` | Team active 双阶段 read fence |
| R33 | retrieval hydration N+1 与 10k scatter/team rebuild 巨事务 | `high` | platform-fitness | `no` | request cache/batch + durable pagination |
| R34 | dedup 固定 summary-first，可丢更高分 original | `medium` | correctness | `no` | 以最终 score 为第一排序键 |
| R35 | 正常 publish 使用 namespace 计数分配 item generation | `medium` | protocol-drift | `no` | item×namespace pointer active+1 |
| R36 | GC/retirement scanner 一次 scan 级异常后永久退出 | `medium` | correctness | `no` | 外层 retry/backoff/health |
| R37 | 每阶段复制完整累计 state，正文/CAS/retention 成倍放大 | `medium` | platform-fitness | `no` | state 只传 receipts/handles |
| R38 | Python layered validator 与注册 JSON Schema 不等价 | `medium` | correctness | `no` | 单一 schema validator + differential tests |
| R39 | schema 支持的 title 在 adoption/construct 中静默丢失 | `medium` | correctness | `no` | 移除字段或纳入 projection/digest |
| R40 | Markdown transport 证据错误，默认 stub 根本不消费 Markdown | `medium` | test-gap | `no` | 修正 receipt + metamorphic test |
| R41 | 多个 active LLM clean workflow 从公共 DTO 永远不可达 | `medium` | delivery-gap | `no` | 不宣称 active 或补 selector/probe/E2E |
| R42 | vector.upserted 事件丢 generation artifact UUID | `low` | correctness | `no` | 使用已验证 state coordinate |
| R43 | denial audit 写失败会被 sampler 消耗，最终绕过 fail-closed audit | `medium` | security | `no` | audit成功后才提交采样状态 |
| R44 | Team payload_extra 无法清空且可静默保留旧值 | `low` | correctness | `no` | 按 model_fields_set 区分省略/空对象 |
| R45 | raw exception 字符串未经脱敏写入 Process/Outbox | `medium` | security | `no` | 持久层只写稳定安全摘要 |

### R1. cancellation 可永久污染唯一 DB 连接

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/persistence/turso/port.py:87-98`、`src/persistence/sqlite_port.py:83-94` 只捕获 `Exception`；Python 3.12 的 `asyncio.CancelledError` 继承 `BaseException`。
  - 临时 Turso/SQLite 库均复现：UoW body 被 cancel 后 `in_transaction=True`，下一次 `BEGIN` 报 `cannot start a transaction within a transaction`。
  - `commit()` 位于 `else`，commit 抛错也不会进入 rollback；被 cancel 的 `asyncio.to_thread()` 底层线程还可能在锁释放后继续操作。
- **为什么重要**：一个客户端断连、shutdown 或 worker cancellation 就能污染进程唯一连接，使后续 API、worker、readiness 全部持续失败，直到重启。
- **审查判断**：这是生产可用性和事务正确性的硬 blocker，SQLite 测试 backend 同样受影响。
- **建议修法**：用 cancellation-safe UoW helper 覆盖 begin/body/commit；捕获 `BaseException`，shield rollback/cleanup，并在 commit/线程状态不确定时废弃连接而非复用。

### R2. Turso diagnostic sidecar 并发触发 native abort

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/persistence/turso/sidecar.py:23-57` 每条日志新建连接、切 MVCC、执行 `BEGIN CONCURRENT`，没有串行化。
  - `src/services/observability.py:158-171` 通过 `asyncio.to_thread()` 进入 sidecar；`api/app.py:309-314` 在 Turso production composition 默认启用。
  - 独立子进程 4 threads/20 inserts 稳定触发 pyturso Rust panic `Positive root page is not mapped to a table id`，退出码 `134`；Python `except` 无法拦 native abort。
- **为什么重要**：并发失败诊断本应提高可观测性，现在反而可以杀死整个 Leaf Worker。
- **审查判断**：当前 sidecar 不能在 production 作为并发 writer 启用。
- **建议修法**：单一串行 writer/有界队列；禁止每条日志切 journal mode；在独立进程做真实并发 soak，并对 pyturso 使用验证过的严格版本。

### R3. wheel 缺 migration SQL，安装制品无法启动

- **严重级别**：`critical`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `pyproject.toml:32-35` 只声明 package discovery，没有 package-data。
  - `src/runtime/config.py:109-111` 从安装包内 `src/persistence/migrations` 找 SQL；`api/app.py:402-404` 启动无条件 migrate。
  - 从干净 `git archive HEAD` 构建并解包 wheel 后，migration 目录只有 `__init__.py`，无 `.sql`；`data/prompts/config/schemas` 也不在 wheel。调用 migration discovery 得到 `migration-missing 503`。
- **为什么重要**：仓库 checkout 能运行不等于发布制品能运行；当前 `uv build PASS` 是假完成信号。
- **审查判断**：正式 wheel 安装后的 `mkb` 必然无法完成 startup/bootstrap。
- **建议修法**：用 package-data/importlib.resources 或明确 deploy-assets 包装全部 runtime assets；新增“build wheel → 空环境安装 → migrate/bootstrap/ready”门禁。

### R4. Concurrent Writes/readiness 为错误能力证明，多实例立即锁失败

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/persistence/engine.py:21-39` 只在单连接临时切 MVCC，空跑一次 `BEGIN CONCURRENT/ROLLBACK`，随后恢复原 journal mode。
  - `src/persistence/turso/port.py:63-64,87-98` 实际所有读写共用单连接、进程内 `asyncio.Lock` 和 `BEGIN IMMEDIATE`。
  - 两个 adapter 同库并发 migrate 的 10/10 复现均有一方 `database is locked`；重叠业务 transaction 第二方约 3ms 即失败，无 busy retry。
- **为什么重要**：`uvicorn --workers N`、滚动重启或双实例共享本地库会启动失败/随机 500；readiness 却向运维声称 concurrent writes 可用。
- **审查判断**：当前实现是 singleton serial writer，不是可横向扩展的 concurrent-writes backend。
- **建议修法**：二选一：强制 singleton 并诚实将该能力置 false；或每 UoW 独立连接、真实 `BEGIN CONCURRENT`、冲突分类/有界退避及跨进程 migration lock。

### R5. 30 秒 lease 无 heartbeat，长推理会被重复执行

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/workflow/worker.py:45-53` 默认 lease 30 秒，handler 执行期间从不续租。
  - `src/runtime/workflow/runtime_core.py:546-558` 虽提供 heartbeat，却没有生产调用方。
  - vLLM generate timeout 默认 180 秒（`src/runtime/config.py:46`），Claude request 默认 900 秒（`src/runtime/inference/claude_cli.py:31`）。
- **为什么重要**：多副本或 repair scanner 可在原推理仍运行时回收并重放 Process；fencing 只阻止 loser 提交 DB，不能撤销重复模型费用/外部副作用。
- **审查判断**：lease 与实际 stage 上界不相容，属于确定性竞态。
- **建议修法**：长 stage 启动 heartbeat task；heartbeat/fence 丢失立即取消 transport；将 lease/heartbeat policy 冻结进 Process，并做“长推理 + reclaim”故障测试。

### R6. 唯一 supervisor 串行执行，pool running cap 是假并发

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/workflow_supervisor.py:43-50` 在循环中逐个 `await worker.run_once()`，没有创建并发 task。
  - `src/runtime/workflow/dispatch.py:12-18` 声称 local/NI/embed running cap 为 `2/2/8`，真实 composition 只会有一个 workflow handler in-flight。
- **为什么重要**：一个 900 秒 CLI 会 head-of-line block 全部 ingestion、generation、embed、outbox 和 repair 进展；pool occupancy 和 facade semaphore 单测不能改变这一点。
- **审查判断**：README 的池容量是 admission 上限，不是当前 worker 的吞吐能力；作为运行能力描述具有误导性。
- **建议修法**：claim loop + per-pool bounded worker task set/semaphore，配套 shutdown、heartbeat、fencing 和 backpressure；以真实 supervisor 并行两个 Process 验证。

### R7. Claude timeout/cancel 不回收子进程，输出也无上限

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/inference/claude_cli.py:288-304` 只对 `process.communicate()` 做 `wait_for`；timeout/cancel 分支没有 terminate/kill/wait。
  - `GenerateResponse.text` 无长度上限（`src/contracts/inference/models.py:156-165`）；CLI 一次性缓冲 stdout/stderr，vLLM payload也未冻结 output token cap。
  - CLI timeout 被归为可重试，旧 child 仍可能运行，新 attempt 又启动一个 child。
- **为什么重要**：孤儿进程、GPU/额度重复消耗与无界输出可造成 OOM/进程耗尽；shutdown 也可能长时间悬挂。
- **审查判断**：subprocess lifecycle 不完整，不能作为可靠 production adapter。
- **建议修法**：timeout/`CancelledError` 下 shield `terminate → bounded wait → kill → wait`；stdin/stdout/stderr 有界流式处理；冻结 max output tokens/bytes。

### R8. Claude/salvage 绕开 frozen binding、NI cap 与真实 quota

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - inference adapter kind 闭集不含 `claude_cli`（`src/contracts/inference/models.py:18-20`）；CLI request 的 model 可空，生产调用未传 model，组合根直接注入裸 port（`api/app.py:304-308`）。
  - `src/runtime/intake/generation_construct.py:168-180,270-284` 在同一个 local Process 内直接切到 CLI；没有重新经过 `choose_pool`/NI occupancy。
  - `src/services/billing.py:16-21` quota 永远 permit；CLI success ledger 的 model/version/binding 可为 null。
  - config snapshot虽保存 vLLM URL（`src/services/config_snapshots.py:184-202`），runtime只取 binding/mode而忽略 frozen endpoint；adapter/SupplyFence由重启后的当前 Settings重建，旧 Execution可被静默改发新 endpoint。
- **为什么重要**：provider/model 会漂移，NI 满载仍可额外调用 Claude，且真实费用/并发不受 frozen policy 控制。
- **审查判断**：这是 silent model/adapter switch 的实际实现，不符合 frozen supply 与 durable workflow 语义。
- **建议修法**：若允许 fallback，将其物化为新的 durable Process，冻结 exact model/endpoint binding，并重新做 NI admission/quota/idempotency；重启时比较旧 Execution supply identity；否则 local 失败应 fail closed。

### R9. CLI 泄露知识正文与父进程全部环境 secret

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/inference/claude_cli.py:59-62,149-152` 把小于 16 KiB 的业务正文直接放 argv，可从 `/proc/*/cmdline`、进程监控或崩溃采集读取。
  - `SubprocessClaudeCli(env=None)`（`:281-298`）继承完整父进程环境；`api/app.py:304-308` 未传最小 env。
  - `Settings` 的 internal token 字段是普通字符串并保留在 `Container.settings`；本轮实测 token 同时出现在 `repr(Settings)` 与 `model_dump()`。
- **为什么重要**：Claude CLI/插件或被替换 executable 可获得全局 internal token、vLLM token、DB/object 路径和宿主其他 secret，横向权限远大于其业务需要。
- **审查判断**：当前子进程秘密隔离不成立。
- **建议修法**：所有业务 material stdin-only；显式 env allowlist 并剔除全部无关 `MKB_*`/secret；internal token 用 `SecretStr`/指纹化部署对象，子进程最好独立低权限账户/容器。

### R10. salvage 失败证据可串到另一 Process/Team，失败 inference ledger 缺失

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/generation_live.py:257-281,329-338` 在 local 失败时把 evidence 放进 ContextVar；`src/runtime/intake/generation_evidence.py:10-33` 在长期 supervisor task context 中保存。
  - `src/runtime/workflow/runtime_outcome.py:460-463` 只在 Process 最终失败时 flush；salvage 成功不会 flush 原失败。后续 flush 用“当前”Process 的 team/execution/process（`generation_evidence.py:45-98`）。
  - local 与 CLI receipt 都用 ordinal 0，而 DB 有 `(process_uuid, invocation_ordinal)` unique + `INSERT OR IGNORE`，冲突可静默丢证据。
  - 失败 flush 只写 generation ledger，不写 `mkb_inference_invocations`；composition 也未给 facade 注入 recorder。
- **为什么重要**：失败调用可能消失，或被记到另一个 Process/Team；模型失败率、审计 lineage 和故障定位均不可信。
- **审查判断**：evidence plane 存在跨业务身份污染，不是单纯“少一条日志”。
- **建议修法**：取消跨调用 ContextVar；attempt evidence 显式随 stage result/outcome 传递，成功/失败在同一 UoW 双写 generation+inference ledger；ordinal 唯一，冲突比较内容并 fail loud。

### R11. schema 未真正冻结/校验，live readiness 可在 supply 全坏时为 ready

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - config snapshot 的 frozen materials 没有 schema bytes coordinate（`src/services/config_snapshots.py:191-220`）；runtime 重新读取当前 DB schema digest（`generation_live.py:133-168`）。
  - vLLM structured payload 只发送 `{"type":"json_object"}`（`src/llm_adapters/local_vllm.py:161-166`），production 调 facade 未传 schema validator；registry digest 也不是 schema 文件 bytes 的 hash。
  - `inference_probe_enabled` 默认 false；`api/app.py:180-189` 此时 `inference_binding` 仅等于 registry readiness；从不探 Claude executable/auth/model。vLLM generic probe 接受 3xx 且不核对 exact model。
- **为什么重要**：同一 Execution retry 可使用漂移后的 schema；ledger digest无法证明模型/validator看到的 schema；所有实际 supply 不可用时 `/ready` 仍可接受 Task。
- **审查判断**：frozen schema 与 readiness 都只证明“登记存在”，不证明“当前 exact capability 可执行”。
- **建议修法**：materialize 时冻结 actual schema bytes SHA；运行时复验并传完整 schema/validator；live 模式强制按 local/NI/embed exact winner 分组件 probe，3xx 不算健康。

### R12. 对象 release 与真实 orphan GC 均未实现

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - 全库 production code 无 `UPDATE mkb_object_references ... released_at` 或 delete reference；唯一 release 在 `tests/unit/test_object_gc.py:169-177` 的手工 SQL。
  - `src/services/object_gc.py:145-162` 只从 `mkb_stored_objects` 取候选；promote 成功、catalog UoW 回滚产生的 filesystem-only object 没有行，永不可见。
  - `intake.delete` 只创建 open cleanup intent（`src/services/intake_lifecycle/lifecycle_apply.py:270-300`），没有 intake-item cleanup consumer；成功对象永久 live-ref。
- **为什么重要**：失败路径产生永久磁盘泄漏，成功路径也永远不释放；数据删除/retention 和 README 的“orphan GC 已落地”均不成立。
- **审查判断**：当前 GC 只能处理测试人工构造的“cataloged but unreferenced”状态，正常生产路径几乎不会产生该状态。
- **建议修法**：实现 domain-owned reference release 与 item-delete cleanup worker；promote 前 reservation journal 或安全 filesystem reconciliation；每类 substrate 写 completion proof。

### R13. tombstoned digest 可被新 live reference 复用

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - CAS 物理路径按 `(team,digest)`；GC tombstone 后相同 bytes 可重建同一路径。
  - `src/services/artifacts.py:131-149`、`src/services/config_snapshots.py:330-365`、`src/runtime/intake/generation_artifacts.py:554-589`、`src/runtime/intake/index_rebuild_commit.py:304-325` 等 lookup 未过滤 `tombstoned_at IS NULL`。
  - 真实复现：GC tombstone 后再次 promote/catalog，相同旧 `stored_object_uuid` 仍 tombstoned，却新增 `released_at=NULL` live ref。
- **为什么重要**：catalog、物理 bytes、live reference 与 delete proof 相互矛盾；GC 永久跳过该新 incarnation，gate/readiness 可能认为对象不存在。
- **审查判断**：对象 incarnation 模型缺失，属于数据一致性 blocker。
- **建议修法**：禁止 tombstone 接收 live ref（trigger/constraint）；对 active row 使用 partial unique，新 incarnation 新建 row，或设计严格可审计 resurrection CAS。

### R14. OutcomeArtifactCommitter 永不清理 `_pending`

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/services/artifacts.py:44-50` 创建进程级 `_pending` dict；`:63-81` 每个 `(process_uuid,fence)` 插入。
  - `validate_and_commit`（`:89-120`）成功后没有 `pop`；失败/取消同样没有清理。
  - callback closure 来自 `src/runtime/intake/core.py:127-139`，会捕获 refs、stage callback，后者可继续捕获完整 state/records/生成结果。
- **为什么重要**：长期服务每完成一个 Process 都永久保留 command、stat 和业务 closure，最终 OOM，并延长敏感知识内容驻留内存。
- **审查判断**：注释所称“bounded in-memory pending descriptors”与实现不符。
- **建议修法**：增加 transaction commit 后的 ack/cleanup 协议；commit 结果不确定时保留可重试 descriptor，但设置容量/TTL/stale-fence recovery，并做 weakref/规模测试。

### R15. local/registered/browser acquisition 绕过预算并写入虚假 budget proof

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - local object 直接 `Path.read_bytes()`（`src/runtime/intake/acquisition_ingest.py:358-369`, `src/storage/local_store.py:103-118`），不查 DB catalog/live-ref/tombstone，也不应用默认 8 MiB acquisition budget。
  - registered records 直接 `canonical_json(records)`，browser injected result也可为无界 bytes/string；统一 `_representation_from_bytes` 在没有实际 size check 时硬编码 `budget_verdict="within_configured_acquisition_budget"`（`:456-499`）。
  - object max 可达 256 MiB，contract 没有 expected size，全部在校验前一次性读入/解码。
- **为什么重要**：未 catalog/released/orphan bytes 可进入业务；大对象造成内存 DoS，同时 durable evidence 谎称已通过预算。
- **审查判断**：这是 public source boundary 的真实校验绕过与伪证明。
- **建议修法**：catalog-aware read port；读前验证 live object coordinate/size，所有 source 统一流式硬预算；budget proof 必须绑定实际配置值与实测 byte count。

### R16. 公共输入可持久化 secret/signed URL，且无总量/有限数值约束

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `PayloadExtraModel` 只检查 JSON/64 KiB（`src/contracts/common/models.py:24-36`）；Team create/patch、Task patch、nested source/audit 没有统一敏感 key/path/core-field fence。
  - 本轮实测 Team extra 接受 `{"token":"must-not-persist","status":"deleted"}`，Task patch 接受 `api-key`；`Settings` 明文 token 可 dump。
  - `HttpSourceDescriptor` 接受 `?X-Amz-Signature=secret&token=abc`；`ConfigSnapshotService.redacted_request_envelope` 对非-inline直接返回完整 envelope（`src/services/config_snapshots.py:427-463`），会将 URL/payload 写 DB/CAS。
  - registered raw string没有长度上限，单条 1,000,000 字符通过；records 最多 10,000。metadata `semantics: Any` 接受 NaN，Pydantic JSON dump 将其静默变为 `null`，可与真实 null 形成 idempotency fingerprint 碰撞。
- **为什么重要**：误传 credential 会进入 DB/immutable artifact；合法请求可造成巨型 parse/事务/存储；不同业务输入可被静默视为同一幂等请求。
- **审查判断**：边界并非 README 声称的“严格 DTO + secret 不落盘”。
- **建议修法**：统一递归 forbidden-key/credential URL/finite JSON validator；请求 aggregate bytes/depth/member/string caps；presigned/auth query 只能变成 registered secret slot，绝不进入 URL；fingerprint基于拒绝非标准 JSON后的 canonical bytes。

### R17. object/schema readiness 可把损坏或错挂载状态判为 ready

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/storage/local_store.py:41-49,134-139` identity 存在时不解析，只检查存在与 `os.access(W_OK)`；预置 `identity.json="not-json"` 实测 readiness 为 true。
  - identity 不与 DB 绑定，错挂对象根/不匹配备份仍可 ready。
  - `src/persistence/migration_runner.py:147-155` schema readiness 只比较 ledger ID/checksum；完整 migrate 后 `DROP TABLE mkb_tasks`，persistence readiness 仍全 true。组合根额外只看 3 张 observability 表。
- **为什么重要**：损坏恢复、错卷、部分 schema 丢失后服务会开放新业务，直到首个 Task/retrieval 才失败。
- **审查判断**：readiness 对核心持久化完整性证明不足。
- **建议修法**：版本化 schema manifest/关键 invariant probe；object identity schema + DB/object pair identity；真实 fsync/rename/read/delete probe，非空无 identity fail closed。

### R18. PDF/doc LLM 把二进制静默替换解码为文本

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/inference/claude_cli.py:371-386` 丢弃 media type，并把 blob 以 UTF-8 `errors="replace"` 转成文本。
  - PDF/doc-understanding 路径可把原 blob 交给该 wrapper；非法字节不会 fail closed，而是变成 replacement characters。
- **为什么重要**：Claude 看到的不是原文档，仍可能返回“成功”clean artifact，形成静默语义损坏。
- **审查判断**：binary/multimodal capability 尚未真正实现，不能用 lossy text transport 冒充。
- **建议修法**：使用 typed file/attachment/multimodal transport；未实现时对 blob-only PDF/doc profile明确拒绝，补非 UTF-8/PDF 测试。

### R19. 推理重试缺少 idempotency，退避期间占满 gate

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：`src/runtime/inference/facade.py:313-349` 在一个 concurrency lease 内最多重试三次且 sleep 不释放 slot；`:486-487` 无 jitter/Retry-After。`src/llm_adapters/local_vllm.py:152-167` 没有 provider idempotency/request key。
- **为什么重要**：请求已执行但响应断线时会重复生成/计费；endpoint outage 时所有 slot 可被 sleeping retry 占满，多实例同步形成 herd。
- **审查判断**：workflow fence 只能保护 DB commit，不能撤销 provider side effect。
- **建议修法**：传稳定 attempt/idempotency identity；只重试明确 pre-send 错误或 provider 支持的幂等请求；加入 jitter、Retry-After、circuit breaker 和 attempt ledger。

### R20. Turso/CW/sidecar/GC 测试存在系统性假绿

- **严重级别**：`critical`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `tests/integration/test_ns4_cw_soak.py:53-57` 明写多线程会 abort，随后只串行 insert 8 次，最终断言测试前创建的 `MkbError.code` 没变。
  - `tests/unit/test_ns4_diagnostic_sidecar.py:15-28` 只搜源码字符串，failure test 根本不调用 sidecar。
  - `tests/unit/test_turso_driver.py:99` 有字面 `... or True`；`:112-128` 只比较同源映射字段，不创建重叠事务。
  - `tests/unit/test_object_gc.py:33-63,169-177` 手工插 catalog orphan、手工 release，恰好避开 production 缺失路径。
- **为什么重要**：相关 suite `16 passed`，而相同代码仍可触发 native abort、multi-instance lock、真实 orphan 泄漏和无 release；绿色结论具有反证意义。
- **审查判断**：这是本轮最严重的 false-green 集群，不能用覆盖数量替代生产语义。
- **建议修法**：native crash test 放独立子进程；两个真实 Turso adapter/barrier 重叠；GC 从真实 promote→rollback/lifecycle API 开始；禁止手改最终表制造前置条件。

### R21. ReadPort/fail-path/live E2E 手工造结果或替换生产逻辑

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `tests/unit/test_ns4_readport_reports.py:9-22` 从未使用创建的 `ObservabilityReadService`，而是手工 dict merge 后断言自己写的数据。
  - `tests/e2e/test_ns4_fail_path_turso.py:31-69` 手工 stash evidence、伪造 Process、关闭 FK、直接调用 private flush/read helper；未运行真实失败链。
  - `tests/e2e/test_single_intake_pipeline.py:173-323` 的“live”case替换整个 production inference facade为永远成功 fixture，并关闭 inference probe。
  - CLI tests只测立即成功，并把业务正文在 argv 固化为正确行为。
- **为什么重要**：生产 SQL、tenant scope、adapter HTTP、SupplyFence、timeout、schema、recorder 和 worker outcome 均可损坏而测试继续绿。
- **审查判断**：这些测试最多是 helper/semantic golden，不能命名或引用为 live/integration/E2E 证据。
- **建议修法**：从 public Task/真实 worker 触发 injected adapter failure，经正式 operator API 读 evidence；用本地假 HTTP server驱动真实 LocalVllmAdapter/Facade/readiness。

### R22. 固定轮询与 stock sqlite inspection 造成假红/顺序依赖

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - 多个 E2E 使用固定 5 秒 + 20ms polling，例如 `tests/e2e/test_generation_pipeline_contracts.py:83-90`；本轮多次在截止时仍 `running`，关闭 lifespan 后最终成功。
  - 多个 case 以 Turso backend 运行后用 stock `sqlite3.connect` 检查同一文件，例如 `test_generation_pipeline_contracts.py:29-38,92-110`；本轮出现 `disk I/O error/file is not a database`。
  - 历史 artifact integration test 缺本地 `.experiment` 文件即 skip，且不是由当前代码生成。
- **为什么重要**：高负载/USB 环境产生假红；raw driver 混用不验证 pyturso 语义，还可能与 journal/连接冲突。反过来干净 CI 可因 skip 假绿。
- **审查判断**：当前全量失败数受测试 harness 噪声影响，但“不是全绿”本身确定。
- **建议修法**：直接有界 `drain_once()`/condition-based eventually；超时输出 Process/outbox/supervisor error；物理检查先关闭 app并用 Turso ReadPort；历史证据与 required CI 分离。

### R23. 当前全量测试和 Ruff 均不绿

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：本轮 `uv run pytest` 为 `431 passed / 10 failed`（并行审查负载下）；Knowledge 混合 E2E 为 `69 passed / 7 failed`；README 自身也承认 `433/8`。`uv run ruff check .` 报 9 项，包括永真/盲异常相关测试问题。
- **为什么重要**：至少包含真实 `STRUCTURE_PROFILE_INVALID`、长期 running 和 driver inspection 错误；不能将 isolated unit green 等同于端到端可用。
- **审查判断**：release/closure gate 没有关闭，准确稳定 failure count 应在修复 test harness 后串行重建。
- **建议修法**：先关闭 critical/high bug和假绿，再在干净环境、无并发审查进程、无排除项下串行全跑；失败时保留 DB/Process/outbox诊断。

### R24. Starlette 0.46.2 命中已公开 Host/request.url 漏洞范围

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：当前环境为 `starlette==0.46.2`。官方 reviewed advisory [GHSA-86qp-5c8j-p5mr / CVE-2026-48710](https://github.com/advisories/GHSA-86qp-5c8j-p5mr) 标明 `<=1.0.0` 受 malformed Host 影响，patched `1.0.1`；仓库未使用 TrustedHost middleware，并在 `api/app.py:117-119` 读取 `request.url.path`。
- **为什么重要**：本仓该读取目前只影响错误 taxonomy，不直接做 auth；但任何部署 edge/middleware 若按 `request.url.path` 做安全策略会进入公告影响面。
- **审查判断**：当前直接可利用性受入口代理配置影响，故非本轮 blocker；版本仍是已知受影响依赖。
- **建议修法**：升级到与新 FastAPI 兼容且含修复的 Starlette；边缘拒绝 malformed Host，应用启用明确 TrustedHost；增加 dependency audit CI。

### R25. idle worker 约每 50ms 执行完整、会切 journal mode 的 readiness

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：`claim_next` 每次先 `_assert_ready_for_claim`（`src/runtime/workflow/runtime_core.py:337-346`）；该 closure调用完整 `HealthAggregator`，无缓存。supervisor idle 约 50ms 再试（`workflow_supervisor.py:47-49,68-72`），Turso readiness 每次验证 migrations、切 journal mode、执行 vector SQL。
- **为什么重要**：空闲服务约 20 次/秒碰 migration/registry/object/DB capability，与业务和 sidecar争锁并放大 journal/pyturso 风险。
- **审查判断**：readiness 被当成 hot-path claim predicate，职责错误且成本过高。
- **建议修法**：启动/周期缓存静态 capability；claim只读健康快照/轻量 ping；禁止每次 readiness 切全局 journal mode，并暴露 probe age。

### R26. Retrieval 只按 UUID 扫前 1000 条，native ANN 从未接线

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/services/retrieval/retrieval_rank.py:100-130` 以 `ORDER BY r.vector_record_uuid LIMIT ?` 截断，默认 `candidate_scan_limit=1000`（`retrieval_request.py:52`）。
  - `retrieval_rank.py:132-191` 拉 BLOB 后在 Python decode/score；`rg "vector_top_k|native_ann" src/services/retrieval` 无产品调用。
  - `src/runtime/config.py:26` 暴露 `native_ann`，但 Turso factory和 `api/app.py:257-264` 没把该选择接到 RetrievalService。
- **为什么重要**：超过 1000 条后，截断集合外的最高相似向量永远不参与评分；UUIDv7近似时间排序还会系统性偏旧，新知识稳定不可召回。
- **审查判断**：这是 Knowledge Base 核心 recall 的确定性错误，native-vector readiness 不代表 retrieval 使用了 native ANN。
- **建议修法**：实现 Turso `VectorSearchPort`/native top-k先取 `recall_k`，再应用现有 publication/serving双 fence；exact profile必须完整扫描或超过上限明确拒绝，不能静默 UUID 截断。

### R27. offline 查询可静默混用 live embedding 空间

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：`src/services/retrieval/retrieval_request.py:96-99` 只看进程级 `_live_inference`；false 时 `retrieval_rank.py:145-149` 无条件按 namespace dimension生成 deterministic hash，不核对 namespace 的 model/version/adapter。测试甚至用 local_vllm namespace + offline service 跑绿（`tests/unit/test_retrieval_service.py:130-135`）。
- **为什么重要**：live Qwen vectors 与同维 hash vectors 直接 cosine/L2，维度正确但语义空间完全不同；系统不报错，只返回貌似合法的无意义结果。
- **审查判断**：Local/Cloud切换的一致性 fence 缺失。
- **建议修法**：查询 embed由 namespace完整 Layer-A tuple决定；只有 exact deterministic tuple可本地 hash，live supply缺失必须 fail closed/readiness false。

### R28. live vectorize 静默丢 required units 后仍签 full-valid

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：compiler 在 `src/services/lsrag_compiler/construct.py:108-131` 生成完整 `plan.required`；runtime `src/runtime/intake/vectorize.py:183-205` 只对超长 g0 summary报错，其他超 16k 的 g1/g2 original/summary直接从 `embeddable` 过滤。`:238-250` 又用缩水后数量写 `required_units==succeeded_units`，publication只验证该缩水集合。
- **为什么重要**：部分知识块没有向量，Task/proof仍 full-valid，属于静默数据丢失和虚假完整性证明。
- **审查判断**：S08 required-set invariant 被 runtime重定义。
- **建议修法**：任一 required unit失败就 fail loud；如需再切块，应在 S06/S07 生成有 provenance 的新 unit，不能在 S08 drop。

### R29. 同一逻辑来源重复 ingest 总是新建 Source/Item

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - 单文档每次 acquire 生成全新 Source/Snapshot/Item/Revision UUID（`src/runtime/intake/acquisition_ingest.py:91-97`），acceptance无条件 insert Item和 ordinal=1 Revision（`acceptance_snapshot.py:98-128`）。
  - registered API也为每次 collection/member生成新 identities（`acquisition_ingest.py:207-211,266-270`；`src/services/scatter_intake.py:389-428`）。
  - `external_key/connector_key/member key` 未用于跨 Task resolve existing Source/Item。
- **为什么重要**：相同业务资源二次 observation 不会 no-change/append Revision/absence diff，而是重复建库、重复检索，lifecycle lineage断裂。
- **审查判断**：README 所述 stable IntakeItem/Revision lifecycle主链对重复 ingest 不成立。
- **建议修法**：先按稳定 source identity resolve Source，再以 `(team,source,normalized_external_key)` CAS resolve/create Item；fingerprint相同 no-change，变化 append Revision，absence/deleted策略显式化。

### R30. 重复文本 anchor 永远指向第一次出现

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：`src/services/lsrag_compiler/adopt.py:224-255` 使用 `clean.find(normalized_body)`，虽记录 occurrence count，却不消歧/拒绝。最小复现 `clean="same\nsame"` + 两个 g1 `same` block，两个 span 均为 `(0,4)`；validator只验每个 span自身。
- **为什么重要**：重复法条、模板段、免责声明会产生错误 traceback，summary/unit看似正常但指向错误原文位置。
- **审查判断**：provenance correctness 失真；既有 `test_adopt_layered_json` 还把“first exact anchor”固定为绿例。
- **建议修法**：按 block顺序单调分配 occurrence，或要求 kernel可验证的 occurrence ordinal/上下文；不能唯一消歧时 fail closed。

### R31. IntakeArtifact handle/digest/size 不描述同一 bytes

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：`src/runtime/intake/acceptance_snapshot.py:63-70,132-178` 让 raw/clean 两个 Artifact都指向同一个 accept-stage envelope handle/stored object/size，却分别写 raw/clean semantic digest；object reference记录的是 envelope实际 digest。rebuild只能读取所谓 clean artifact再解析 `envelope["state"]["clean_text"]`（`src/runtime/intake/core.py:462-474`）。
- **为什么重要**：对 `logical_handle` bytes做 SHA-256 不等于该 Artifact `content_digest`；通用 Artifact reader会判损坏，raw/clean也无法独立 retention/export。
- **审查判断**：locator、size、digest的基本不变量被混用为“stage envelope digest”和“semantic digest”。
- **建议修法**：raw/clean representation分别 promote；Artifact handle/digest/size必须绑定同一 bytes，semantic digest放专门字段/ledger。

### R32. Team inactive/deleted 后仍可 retrieval

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：Team transition仅更新 `mkb_teams.status`（`src/services/teams.py:110-139`）；namespace resolve、candidate、eligibility、body access均不 join/check Team active（入口见 `src/services/retrieval/retrieval_request.py:343-359`）。
- **为什么重要**：停用/删除 Team后，知道 UUID 且持全局 internal token的调用方仍可检索内容；tenant lifecycle不是read fence。
- **审查判断**：Item-level serving fence正确，但 Team-level lifecycle fence缺失。
- **建议修法**：retrieval初始事务验证 Team active，final eligibility再次检查；Team delete/deactivate需定义 serving withdrawal/cleanup语义并做 E2E。

### R33. retrieval hydration N+1 与 10k scatter/team rebuild 巨事务

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - retrieval 对 candidate串行逐个 hydrate（`retrieval_request.py:138-140`）；summary再读 original，inflation再读 root。每次 `load_retrieval_body` 都查 DB、读完整 object、hash并 parse全 JSON（`src/persistence/retrieval_access.py:168-215,260-291`）。
  - public registered records上限 10,000（`src/contracts/api/models.py:134`），acceptance/child materialize在单 callback/UoW逐 member执行；team index rebuild无界 fetchall并在单 outcome TX clone/cutover全部计划。
- **为什么重要**：单 retrieval可重复读取/parse同一大 artifact数十到百次；大 scatter/rebuild长期占唯一写锁、巨大事务回滚，阻塞全服务。
- **审查判断**：bounded API参数没有转化为 bounded I/O/transaction；这是实际 availability风险。
- **建议修法**：request-scoped artifact cache/batch coordinates；真实 paged staging + per-item/bounded child workflows；设置 hard cap和可观测进度。

### R34. dedup 固定 summary-first，可丢更高分 original

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：`src/services/retrieval/retrieval_pack.py:260-273` 将 resolved summary priority设 0、original设 1，并在 ANN score之前比较。
- **为什么重要**：同 unit original=0.99、summary=0.10时仍保留 summary，违反双通道同池/无隐式 channel权重的预期，结果 score不代表最佳 hit。
- **审查判断**：这是检索质量的隐藏策略，而非普通 tie-break。
- **建议修法**：最终 relevance score为第一排序键；traceback质量只在同分时 tie-break，或把 summary boost正式版本化并公开诊断。

### R35. 正常 publish 使用 namespace 计数分配 item generation

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：`src/runtime/intake/vector_publish_commit.py:263-279` 从 namespace `index_generation+1` 分配普通 publish；index rebuild却从 item pointer `active+1`（`index_rebuild_plan.py:355-362`）。
- **为什么重要**：不同 Item发布会让某 Item代数按 namespace全局最大值跳跃，并发 Item可共享候选值；item×namespace retirement/audit语义混乱。
- **审查判断**：两条发布路径对 generation coordinate定义不一致。
- **建议修法**：普通 publish也从 `(team,item,namespace)` pointer CAS预留 `active+1`；namespace计数只用于空间级 epoch。

### R36. GC/retirement scanner 一次 scan 级异常后永久退出

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：`src/runtime/object_gc.py:42-50` 与 `src/runtime/index_retirement.py:40-46` 的 `run_forever` 不捕获 `run_once` 异常；service只捕获已枚举 candidate的单项异常，candidate discovery DB错误会穿透并杀后台 task。
- **为什么重要**：一次短暂 DB I/O错误即可让维护任务停到进程重启，当前 readiness也不暴露 scanner已死。
- **审查判断**：维护 loop没有 supervisor语义。
- **建议修法**：外层捕获非 cancellation异常，记录低基数 metric/diagnostic、指数退避继续；readiness/metrics暴露 last success/error age。

### R37. 每阶段复制完整累计 state，正文/CAS/retention 成倍放大

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：`src/runtime/intake/core.py:373-398` 把完整 state写进每个 stage CAS envelope；Markdown/construct/vectorize反复 `next_state=dict(state)`（`generation_construct.py:607-614,1339-1375`；`vectorize.py:233-279`）。
- **为什么重要**：接近 8 MiB 的输入会在多个 stage envelope重复 raw/decoded/clean/markdown/layered正文，放大序列化、CAS空间、引用与retention，也扩大敏感正文副本面。
- **审查判断**：所谓 body-free vector outcome并不 body-free，只是字段继续藏在 inherited state。
- **建议修法**：stage state只传 typed receipt/handle/digest；需正文时从 owning artifact verify-on-read，增加对象放大率/正文泄漏测试。

### R38. Python layered validator 与注册 JSON Schema 不等价

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：checked-in schema要求 `knowledge_tree` UUID/数组、date-time和 URI；`src/contracts/lsrag/layered_content.py:82-96` 主要只查字段名和 string/null。最小复现可接受 `upstream_file_uuids="not-an-array"`。
- **为什么重要**：local/kernel路径可把不符合注册 schema的结果标为 full-valid，Claude schema path与vLLM/kernel语义不一致。
- **审查判断**：schema digest不能代表实际 validator语义。
- **建议修法**：从唯一 schema生成/复用 validator，或完整实现类型/format；做 schema-vs-runtime differential/fuzz tests。

### R39. schema 支持的 title 在 adoption/construct 中静默丢失

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：wire允许 `original_content.title`/`llm_summary.title`；`src/services/lsrag_compiler/adopt.py:216-245,307-324` 只读取 body；construct channel与dual projection也只保存 body（`construct.py:54-68`, `payloads.py:170-184`）。现有 fixtures几乎都让 title为 null。
- **为什么重要**：章节/条款标题通过 schema与模型生成后无声消失，无法进入 vector/retrieval/content_full。
- **审查判断**：公开 schema表达了未被下游实现的能力。
- **建议修法**：要么从 schema/prompt删除 title，要么把经锚定的 title纳入 projection、digest、content_full和retrieval。

### R40. Markdown transport 证据错误，默认 stub 根本不消费 Markdown

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：local Markdown receipt正确为 `api_inference`，但 stage output在 `src/runtime/intake/generation_construct.py:615-624` 无条件写 `transport="claude_cli"`。B.json含 clean+markdown，但 deterministic stub的 `clean_text_from_bjson_material` 只取 clean（`src/runtime/inference/claude_cli.py:65-76,417-421`）。
- **为什么重要**：artifact/proof与invocation ledger对 provider陈述冲突；offline E2E可证明“走过 markdown节点”，却不能证明 Markdown影响结构。
- **审查判断**：这是错误 evidence + 业务效果假绿的组合。
- **建议修法**：output引用实际 receipt transport；metamorphic test固定 clean、改变 markdown并验证结构受控变化；stub必须显式消费或明确不提供语义证明。

### R41. 多个 active LLM clean workflow 从公共 DTO 永远不可达

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：doc-LLM/web-LLM/PDF-understanding/browser-print/Vision definitions在 `src/workflows/lsrag_definition.py:1003-1069` 注册；但 profile map只有普通七类（`:929-940`），`WorkflowRegistryService.resolve_for_source` 与 public `_source_profile()` 不会产生这些 selector（`src/services/config_snapshots.py:490-514`）。
- **为什么重要**：registry/readiness显示 definition存在，合法 public Task却永远选不到；属于明确半成品/死路径。
- **审查判断**：README 将其描述为“合同落地/未接线”是诚实的，但 active bootstrap和测试容易被误读为 capability已可用。
- **建议修法**：未完成项不要计入 active capability；若开放，增加严格 source/profile selector、composition probe和 public DTO→terminal E2E。

### R42. vector.upserted 事件丢 generation artifact UUID

- **严重级别**：`low`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：`src/runtime/intake/vectorize.py:333-337` 读 `record.generation_artifact_uuid` 或不存在的 `state.construction_dual_channel_artifact_uuid`；persisted records没设前者，真实 key为 `dual_channel_artifact_uuid`。
- **为什么重要**：向量事件无法关联 owning generation，降低审计与故障定位。
- **审查判断**：不影响 serving correctness，但事件证据不完整。
- **建议修法**：直接使用已验证的 `state["dual_channel_artifact_uuid"]` 并为 event payload加断言。

### R43. denial audit 写失败会被 sampler 消耗，最终绕过 fail-closed audit

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：`api/dependencies.py:63-97` 先调用 sampler `decide()`并推进 detail/summary状态，再尝试 DB write。写失败虽抛 `SEC_AUDIT_WRITE_FAIL`，但状态不回滚；达到 detail+summary上限后 disposition变 `DROP`，函数直接返回。测试 `tests/unit/test_security_boundary.py:207-230` 只测第一次失败。
- **为什么重要**：audit DB持续故障时，前几次 invalid token为 503，之后请求恢复普通401且没有任何成功 audit row，违反 S16“invalid auth audit fail-closed/至少聚合summary”不变量。鉴权仍拒绝，故不是访问绕过。
- **审查判断**：失败证据被内存采样器误认为已持久化。
- **建议修法**：采样 reservation只有 audit commit成功后才确认；失败时不得消耗detail/summary quota，或为 summary建立可靠聚合计数/重试。

### R44. Team payload_extra 无法清空且可静默保留旧值

- **严重级别**：`low`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：`src/contracts/api/models.py:45-53` 将空 `payload_extra={}` 当作“无 mutation”；即使同时修改name使请求通过，`src/services/teams.py:91-103` 又以 truthiness选择旧值，空对象无法清除已有metadata。Task patch已正确使用 `model_fields_set`，两者语义不一致。
- **为什么重要**：调用方明确请求清空扩展metadata却收到成功响应、旧值仍保留，属于静默写入错误。
- **审查判断**：真实边界 bug，但影响局限于 Team extension bag。
- **建议修法**：以 `"payload_extra" in model_fields_set` 区分省略和显式空对象，并补 clear/idempotency测试。

### R45. raw exception 字符串未经脱敏写入 Process/Outbox

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：`src/runtime/workflow/worker.py:52-60` 把 `str(exc)` 放入 failure outcome；`src/runtime/workflow/runtime_outcome.py:443-452` 原样写 `mkb_processes.error_message`。outbox失败也在 `src/runtime/workflow/runtime_outbox.py:102-104,331-341` 把 `str(exc)` 写 `last_error`。这些写入前未调用统一 redaction。
- **为什么重要**：HTTP/provider/OS/driver exception常包含 URL query、绝对路径、SQL或credential，可能进入持久化证据；public Task最终message目前多为generic，但DB/运维面仍违反 secret-at-rest约束。
- **审查判断**：错误被“有界截断”不等于安全脱敏。
- **建议修法**：业务表只存稳定code和预定义安全message；raw detail经严格redact后仅进受控diagnostic sink，增加 secret/path/DSN fault tests。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | versioned public DTO、token-before-resource、team-scoped SQL | `done` | 入口顺序、UUID/DTO 主体和 SQL team 参数已核实；不代表 Team lifecycle read fence完整。 |
| S2 | publication proof + active pointer + Intake serving dual-fence | `done` | 当前 candidate/final revalidation 主体成立；R26/R27/R32 是其外围召回/Team/space缺口。 |
| S3 | durable workflow claim/lease/retry/fencing | `partial` | DB fence原语存在；R1/R5/R6 使 cancellation、长任务和真实并发不成立。 |
| S4 | 本地 Turso + Concurrent Writes readiness | `stale` | embedded Turso可做简单 commit；Concurrent Writes/multi-instance声明与真实 BEGIN IMMEDIATE/lock行为相反。 |
| S5 | Local/Cloud inference adapter consistency | `partial` | vLLM typed facade较完整；Claude/salvage未进入同一 binding/schema/readiness/evidence模型。 |
| S6 | Knowledge Source→Item→Revision lifecycle | `missing` | 首次 ingest成立；重复 observation总是新 Source/Item，no-change/absence/append Revision主链缺失。 |
| S7 | LS-RAG full-valid structurize/construct/vectorize/publish | `partial` | 小输入 deterministic happy path可跑；required unit silent drop、anchor、Artifact bytes、schema差异破坏完整性。 |
| S8 | context-only retrieval quality与规模能力 | `partial` | dual fence/body integrity成立；前1000 UUID截断、跨 embedding space、N+1和summary-first使规模/质量不成立。 |
| S9 | CAS reference/GC/delete lifecycle | `missing` | 无生产 release、无 filesystem-only orphan reconciliation、tombstone reuse和pending内存泄漏。 |
| S10 | 进程内 local/NI/embed pool并发 | `missing` | composition始终串行 await一个 worker。 |
| S11 | public endpoint production security | `partial` | token/SSRF基本原语存在；输入secret/size、Team read fence、依赖版本和部署edge仍有硬缺口。 |
| S12 | integration/e2e/soak 作为 closure evidence | `stale` | 多项测试为永真、自证、手工造状态或替换生产组件；当前全量仍失败。 |
| S13 | wheel/sdist 可部署制品 | `missing` | wheel缺 migrations及 runtime assets，无法从干净安装启动。 |

### 3.1 对齐结论

- **done**: `2`
- **partial**: `5`
- **missing**: `4`
- **stale**: `2`
- **out-of-scope-by-design**: `0`

> 当前状态更接近“合同与小数据单进程 happy path 已形成，但 production persistence、推理供应、知识身份、检索规模、对象清理和验证证据未收口”，而不是 completed/production-ready。

### 3.2 本轮未充分验证的区域

- 未启动真实 vLLM、1024维 Qwen、Claude CLI登录态或 GPU，因此不能评价真实 prompt遵从率、模型吞吐、OOM与供应商 wire差异；这不削弱已由代码/子进程复现的 lease、schema、CLI lifecycle问题。
- 仓库没有 Turso Cloud/libSQL remote replica接线，无法验证 remote sync/replica consistency；本报告只评价当前 local embedded pyturso路径。
- 未执行 kill -9、disk-full、fsync failure和10k scatter/大 Team rebuild，以避免破坏共享工作区；相应结论来自明确无界调用链，仍建议二审故障注入。
- 本轮全量 pytest与专项并行取证有资源重叠，故 `10 failed` 不被当作稳定计数；多个独立专项仍得到失败，README自身也承认8失败，所以“当前不全绿”无争议。
- 依赖安全只做了直接运行依赖/官方公告的 bounded核对，不替代完整 SBOM、transitive CVE和许可证审计。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | 最终答案生成、聊天会话、UI、membership/RBAC平台 | `遵守` | 仓库没有把 context-only retrieval冒充 answer service。 |
| O2 | Turso Cloud remote replica | `遵守` | 当前明确是 local embedded；本报告不把 remote缺失本身列 blocker。 |
| O3 | browser/OCR/Vision/doc/web LLM live capability | `部分违反` | README诚实声明未接线；但多个 definition仍 active bootstrap，易被 registry/readiness/test误当可达能力（R41）。 |
| O4 | 公网部署、TLS、Host/CORS/security headers | `遵守但有条件` | 作为部署边缘可 deferred；若声称 public endpoint/production-ready，缺部署清单、request size/Host策略仍必须另行验收。 |
| O5 | 真实 billing/quota | `部分违反` | billing stub本身已披露；但 salvage把 always-permit当真实NI quota，已经影响当前执行正确性（R8）。 |
| O6 | R5 system-owned g0 / quoted cuts | `遵守` | 仍是计划，本轮未把其未实现误报为当前 blocker。 |
| O7 | FileResponse/StaticFiles | `误报风险` | Starlette Range公告虽覆盖版本，但仓库当前没有 FileResponse/StaticFiles；本报告未把该特定DoS列为可利用 blocker。 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested — 当前实现不得以 production-ready、live-complete 或全量验证通过收口。`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. 修复 R1/R2：transaction cancellation/commit cleanup和sidecar native crash；在独立子进程、多连接和取消故障注入下稳定通过。
  2. 修复 R3/R4：可安装 wheel必须自带/明确提供全部 migrations/assets；明确 singleton或实现真实多实例并发/migration协调，readiness不得误报。
  3. 修复 R5-R11：长Process heartbeat、实际per-pool worker、CLI子进程回收/秘密隔离、typed frozen Claude binding、evidence双账与schema/exact-supply readiness。
  4. 修复 R26-R32：取消前1000 UUID截断、禁止跨 embedding space、required vector set完整、稳定 Source/Item/Revision identity、正确anchor/Artifact coordinate和Team lifecycle read fence。
  5. 修复 R12-R18：实现reference release、真实orphan reconciliation、tombstone incarnation、pending回收、统一source预算、公共输入secret/size/finite约束、可靠DB↔object readiness，并停止用lossy text冒充binary document-understanding。
  6. 重写 R20/R21 的假绿测试；清理 R22 harness；让全量 pytest、Ruff和干净wheel安装 smoke在无排除项下通过。
- **可以后续跟进的 non-blocking follow-up**：
  1. R19、R25、R33-R40 的 retry/circuit breaker、readiness成本、N+1/巨事务、state放大、validator/title/Markdown质量问题。
  2. R24依赖升级、R36 scanner supervision、R41-R45 的 capability/event/audit/Team patch/error-redaction，以及真实GPU/Claude/Turso目标部署soak。
- **建议的二次审查方式**：`independent reviewer`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
