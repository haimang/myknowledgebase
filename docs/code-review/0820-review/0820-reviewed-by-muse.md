# MKB 深度代码审查

> 审查对象: `MKB @ HEAD 5e64a1e / myknowledgebase 全仓（Leaf-Worker + LS-RAG + Turso + Inference Adapter + Retrieval + Workflow + Security + Tests）`
> 审查类型: `code-review`
> 审查时间: `2026-08-20`
> 审查人: `Muse Spark (OpenCode)`
> 审查范围:
> - `api/app.py`、`api/public/routes.py`、`api/internal/routes.py`、`api/dependencies.py`
> - `src/llm_adapters/*`、`src/runtime/inference/*`（facade/supply/claude_cli/invocations + LocalVllmAdapter）
> - `src/persistence/turso/*`、`src/persistence/factory.py|engine.py|migration_runner.py`、`src/persistence/migrations/*.sql`、`src/storage/local_store.py`、`src/persistence/sqlite_port.py`
> - `src/runtime/intake/*`（11-file split）、`src/runtime/intake_pipeline.py`、`src/workflows/builtin_*`、`src/services/lsrag_*`、`src/services/retrieval/*`、`src/persistence/retrieval_access.py`、`intake/*`、`data/prompts|schemas|config`
> - `src/runtime/workflow*`（runtime_core/runtime_outbox/runtime_gates/runtime_materialize/runtime_repair/worker/supervisor/dispatch）、`src/runtime/task/*`、`src/runtime/security.py|health.py|metrics.py|http_acquisition.py|object_gc.py|index_retirement.py`
> - `src/runtime/config.py`、`src/services/*`（teams/config_snapshots/registry/observability/billing/artifacts/generation_read）
> - `tests/unit|domain|integration|e2e|intake` 全量（106 个测试文件，抽样 30+ 深度精读）
> 对照真相:
> - `README.md @ 5e64a1e`（`433 passed / 8 failed` 非全绿）
> - `docs/baseline/domain-truth/D01..D08`、`S01..S16`（含 S03 引擎、S05 清洗、S06 Strukturize、S07 Construct、S08 向量化、S09 Index、S10 Retrieval、S11 Inference、S14 注册表、S15 可观测、S16 安全）
> - `docs/closure/new-start/deferred-items-ledger.md`、`NS4-generation-evidence-plane.md`
> - `.adocs/code-review.md`（审查输出模板）
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 该实现的**主骨架可读且多数路径 fail-closed**，但以 Leaf-Worker 的生产姿态看**不应标记为 completed / live**。当前 `433 passed` 的绿灯被系统性假绿抬高：Turso 并发写被单进程锁掩盖、LLM 池会计与真实运输分叉、向量维度与候选截断在离线模式下永不暴露、安全栅栏在常见反向代理拓扑下绕过。

- **整体判断**: `主体合同、工作流、双栅栏检索 SQL、CAS 对象与 prompt 冻结可读；但 Turso 并发/向量能力探针与真实写路径脱节、worker 租约与真实推理时长失配、GC/回收扫描器单次异常就永久停摆、公共面在 proxy 后内外网隔离失效。测试层存在 waived 配置、grep 栅栏、串行冒充并发等多处假绿。`
- **结论等级**: `changes-requested`
- **是否允许关闭本轮 review**: `no`
- **本轮最关键的 1-3 个判断**:
  1. `Turso 写入仍是单连接 + BEGIN IMMEDIATE + 无 busy_timeout，任何第二进程/线程的并发写必得 BUSY 异常并冒泡为 500 或被吞掉；MVCC/原生向量的 readiness 探针与真实写入/ANN 路径不一致。`
  2. `Workflow lease 30s 与真实 handler 耗时 180s*3 + CLI 900s 完全失配且无 heartbeat；且 GC 事务内持锁做 unlink、readiness 探针持写锁 —— 高负载下必现 duplicate execution 与 claim 停摆。`
  3. `检索 N>1000 时先按 UUID 截断再打分、64/1024 维度切换导致新世代永不晋升为 serving、Claude CLI 无并发门限；这些在 deterministic-hash 离线模式下永远绿。`

---

## 1. 审查方法与已核实事实

- **对照文档**:
  - `README.md`（1.1 能力表 / 12.2 已知问题 K1-K14 / 10.5 测试分层 433/8 failed）
  - `docs/baseline/domain-truth/S03`（claim/lease/fencing/outbox/repair）、`S10/S09`（publication fence + retrieval dual fence）、`S11`（supply fence / gate / retry）、`S16`（egress/auth/secret）、`D04`（55 表 + 增量 013）
  - `docs/closure/new-start/deferred-items-ledger.md`（billing/cloud/GPU soak 明确 deferred）
  - `docs/eval/new-start/after-MKB-0815-R4-first-wave.md`（R4 4/4 live cell 失败）
- **核查实现**:
  - `api/app.py:200-536`（Container/lifespan/supervisor/GC/retirement/retention 4 个后台 loop + probe）
  - `api/dependencies.py:100-200`（IP → auth → token 限流 → operator/retry 审计）
  - `src/llm_adapters/local_vllm.py:1-309`、`src/runtime/inference/facade.py:1-550`、`supply.py:1-120`、`claude_cli.py:1-431`
  - `src/persistence/turso/port.py:1-137`、`engine.py:1-100`、`migration_runner.py:1-180`、`factory.py:1-60`、`local_store.py:1-180`
  - `src/runtime/intake/*.py` 11 文件（clean_preflight/acquisition_*/generation_*/vectorize/vector_publish*）
  - `src/runtime/workflow/runtime_core.py:340-580`（claim_next 444 行）、`worker.py:45`、`supervisor.py:53`、`runtime_outbox.py:25-341`、`dispatch.py:12-90`
  - `src/services/retrieval/retrieval_rank.py:126-418`、`retrieval_pack.py:34-362`、`retrieval_request.py:46-340`、`retrieval_access.py:99-214`
  - `src/runtime/security.py:45-481`（token/rate/egress/resolver/ip）、`http_acquisition.py:239-282`
  - `tests/` 全量 glob 106 文件，深度精读 30+（e2e 7 + integration 2 + unit 15 + domain 5 + intake 3），配合 `grep -rn TODO/FIXME/NotImplemented/raise 501` 与 `ruff F401` 验证
- **执行过的验证**:
  - `read README.md + .adocs/code-review.md + pyproject.toml`
  - `glob src/**/*.py (160 files) / tests/**/*.py (106 files) / api/**/*.py`
  - `rg 严重关键字：BEGIN|busy_timeout|claim_token|INFERENCE_.*RETRYABLE|DEGRADED|vector32|payload_extra|PYTEST_CURRENT_TEST|executescript|journal_mode`
  - `读 Turso port/engine/migration + IntakePipeline + Lsrag construct + retrieval rank/pack/request + workflow claim/admit/outbox + security egress + app lifespan 关键段落并追踪调用链`
  - `对 6 个攻击面各派 dedicated sub-agent 做 very thorough 并行审计并交叉去重`
  - `核对 `docs/code-review/new-start/` 既有 10 篇 review 与 `docs/verification/schema-reconciliation.md` 的已落地决议`
- **复用 / 对照的既有审查**:
  - `docs/code-review/new-start/NS1-reviewed-by-* + NS2-reviewed-by-* + 0820-reviewed-by-grok/GPT/gemini` — 仅作线索，不采纳结论，逐项独立复核文件:行号
  - `docs/closure/new-start/*.md` 的 verified/deferred 声明 — 逐项对代码复核是否真实落地而非 plan 即事实

### 1.1 已确认的正面事实

- 合同层 `src/contracts/*` 统一 `extra=forbid` + `assert_safe_public_data`（对 TaskCreate 生效）+ `validate_external_uuid(v4/v7)` + `payload_extra 64KiB` / `inline 8MiB` / `overrides 16KiB allowlist` 边界基本落地；错误 envelope 不回显 raw body（`api/app.py:464-482` + `contracts/common/errors.py:42-89` 的 redact）。
- 关系事实与字节分离可读：`OutcomeArtifactCommitter.validate_and_commit` 把 `promote + catalog + callback UoW` 放同一事务；`vector_publish_commit` 的 `withdrawn→indexed + proof + active pointer CAS + lifecycle publish` 同一 UoW；检索 `mkb_v_vectors_active` 视图同时约束 `publication_state='indexed' && p.lifecycle_state='active' && t.status∈{queued,running} && deleted_at IS NULL` 的 dual fence 思路正确。
- Prompt/model 冻结链闭环：`ConfigSnapshotService.prepare` 把 L0+registry+binding+prompt hash + override digest 固化为 L4 snapshot，materialize 时 `SupplyFence.validate` 与 `prompt hash 校验` fail-closed，R4 虽 4/4 失败但不是静默漂移。
- Outbox 去重键 + CAS 更新（`row_revision` / `fencing_generation` / `dispatch_admitted` CAS）的主思路正确；`registered_api` scatter 的 root→child fanout 与 `human gate` 的 `idempotency_key + gate_revision CAS + outbox` 原子性正确。
- 出站 SSRF 防护较完整：`EgressPolicy` 拒绝 literal IP/私网/loopback/link-local/metadata/userinfo，逐跳 `check_url` + DNS 固定 + `PinnedNetworkBackend` connect 钉死 IP，`max_redirects=3` 逐跳复核，`8MiB` 上限。

### 1.2 已确认的负面事实

- 全量测试 `433 passed / 8 failed`（`tests/e2e` 3 个 + harness 5 个）非全绿且 `Ruff 9 errors` 非全绿；`README K1-K3` 已自认但仍以离线 stub 作为默认可用性宣称。
- `TursoPersistence` 仍是单文件单连接 `asyncio.Lock + BEGIN IMMEDIATE`，未设置 `busy_timeout`/`journal_mode=mvcc`，与 `Settings.concurrent_writes_required=true` / `probe_concurrent_writes → BEGIN CONCURRENT` 的意图脱节。
- `WorkflowWorker.run_once` 的 `claim 30s lease → mark_running → await handler.run(180s*3 + CLI 900s)` 全程无 heartbeat，必超时被 `recover_expired_leases` 加代 fence 形成 duplicate execution。
- `ObjectGcScanner` / `IndexGenerationRetirementScanner` 的 `run_forever` 无 `try/except`，一次 `BUSY` 即死；`HealthAggregator` 的 `/ready` 探针与 `require_ready` 无缓存且持写锁，突发 100 rps 争写锁。
- 检索候选 `ORDER BY vector_record_uuid LIMIT 1000` 先截断后打分，多于 1000 向量时召回是 UUID 顺序的随机子集；64→1024 维度切换导致同 `namespace_key` 冲突 `409 VECTOR_NAMESPACE_BINDING_CONFLICT` 且永不 serving。
- 默认 `MKB_NS1_CLI_MODE=stub` 的 `DeterministicNs1Stub` 把 B/C/Markdown 做成原文回声/截断，R4 live 4 cell 在此配置下永远过不了验收却仍计入 `passed`。
- 公共面默认 `docs_url=/docs` 未鉴权、`metrics` 默认不需 token 且不限流、`payload_extra` 的 `_SECRET_KEYS` 精确集漏掉 `apiKey/secretKey` 等驼峰、`request_ip` 仅看 `client.host` 导致经代理全员被判 internal。
- 测试层系统性假绿：`local_mock_settings` 豁免 `concurrent_writes/native_vector/live_inference` 使 e2e 永远走 `SqlitePersistence`/`deterministic-hash`；`skipIf(TURSO.is_file())` / `if not path.is_file(): return` 静默 pass；多处 `str(result)` 包含检查与 `>=2` 宽松阈值；grep 栅栏代替行为测试；`test_ns4_cw_soak` 串行冒充并发 soak。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 对 `api/src/intake/persistence/retrieval/storage/tests` 全部一手读源码并给 file:line，6 个子域独立审计后 dedup |
| 本地命令 / 测试 | `yes` | 读 `README/uv.lock/pyproject`、glob 160+106 文件、`rg` 关键字、`ruff` 检查；未重跑全量 441 case（已知 8 failed），但抽样读测试 oracle 并判定假绿类型 |
| schema / contract 反向校验 | `yes` | 反向核对 `001-013 migration` 与 `contracts` 的 `extra=forbid / allowlist / vector namespace` 约束，查出 ledger `!r` 插值与 `executescript` 回退缺口 |
| live / deploy / preview 证据 | `n/a` | 仓库无 Dockerfile/Compose/K8s/metrics 生产 URL；`MKB_LIVE_INFERENCE=false` + `stub` 为默认，不做 live 推理断言 |
| 与上游 design / QNA 对账 | `yes` | 逐项对照 `S01..S16/D01..D08/QNA`，对 `S03/S09/S10/S11/S16` 的 gate/fence/provenance 表做真伪判定 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | Turso 单连接 + BEGIN IMMEDIATE + 无 busy_timeout，跨进程/线程并发必 BUSY | `critical` | `correctness` | `yes` | 切 MVCC/BEGIN CONCURRENT + busy_retry 或文档化单写者并加 busy 重试 |
| R2 | Worker 无 heartbeat：30s lease vs 540s 真实推理，必 duplicate execution | `critical` | `correctness` | `yes` | 加 heartbeat loop 或把 lease 放大到 `generate*maxAttempts+backoff` |
| R3 | Claude CLI 超时泄漏子进程（未 kill），fd/secret 残留 | `high` | `correctness` | `yes` | Timeout 时 `process.kill(); await wait()` |
| R4 | 检索候选先按 UUID 截断 1000 再打分，N>1000 召回即错 | `high` | `correctness` | `yes` | 切 `VectorSearchPort` ANN；BLOB  fallback 必须全表扫或 fail-closed |
| R5 | 64→1024 维度 schism：同 namespace_key 新活模型永不 serving | `high` | `correctness` | `yes` | 按 `embedding_model_key/version` 分 namespace 或提供 index.rebuild 迁移 |
| R6 | SupplyFence 允许集过大：基于全部 enabled bindings 而非 winners | `high` | `security` | `yes` | 仅由 `active_inference_bindings()` winners 建 fence + 单测守护 |
| R7 | Claude CLI 无并发门限，可 fork 炸机 | `high` | `correctness` | `yes` | 复用 `ConcurrencyGate` 或经 `InferenceFacade` typed 通道 |
| R8 | GC 在事务内做 unlink 并持写锁，阻塞所有 claim/create | `high` | `correctness` | `yes` | 查 blocker → unlink → 第二事务复核 → 写 proof 的两阶段 |
| R9 | GC/Retirement 扫描器单次异常永久停摆 | `high` | `correctness` | `yes` | `try/except` + metric + backoff，保持与 retention loop 同级韧性 |
| R10 | claim_next 每轮只 fail 一个 deadline 过期项后直接 return None | `high` | `correctness` | `no` | 同事务内 loop 直到无过期或有候选，按 `available_at` 排序 |
| R11 | Fencing token 哈希从未校验，仅 generation 栅栏生效 | `medium` | `correctness` | `no` | 要么删 token 要么在 heartbeat/accept 加 `claim_token_hash=?` CAS |
| R12 | Task/Team 并发 PK 唯一冲突走 500 而非 409 | `high` | `correctness` | `yes` | 捕获 `IntegrityError` → `ConflictError task-identity-conflict` |
| R13 | request_ip 仅看 client.host，代理后内外网栅栏绕过 | `high` | `security` | `yes` | `MKB_TRUSTED_PROXY_CIDRS` + 仅可信 peer 才信 XFF |
| R14 | payload_extra 密钥检查漏驼峰 apiKey/secretKey，可存 vault | `high` | `security` | `yes` | 用 `_REDACT_KEY` 正则统一校验 |
| R15 | /docs、/redoc、/openapi.json 默认开放无鉴权 | `medium` | `security` | `yes` | `docs_url=None` 或加 `require_operator_token`；加安全头 |
| R16 | VECTORIZE 包错抹掉原始 code，space violation 被误重试 | `medium` | `correctness` | `yes` | 保留 `exc.code`，仅 transport 可重试 |
| R17 | content_full（带 header）嵌入 vs query 裸嵌入不一致 | `medium` | `correctness` | `no` | 要么只嵌 body，要么 query 侧同 header 投影 |
| R18 | retrieval 第二重栅栏兜底不完整，注入的 EligibilityPort 可喂脏 | `medium` | `correctness` | `no` | `_sql_batch_eligibility` 镜像全 S09+S04 谓词；注入端审计 team 一致性 |
| R19 | sqlite 后门由 PYTEST_CURRENT_TEST 环境变量轻易伪造 | `high` | `security` | `yes` | 需显式 `MKB_ALLOW_SQLITE=1` 豁免并告警 |
| R20 | migration ledger 用 !r 插值非参数化 | `high` | `security` | `yes` | 改参数化 `INSERT ... VALUES (?,?,?,?)` |
| R21 | Turso 下 executescript 回退用 connection.execute 多语句必失败 | `high` | `correctness` | `yes` | 分割执行或强制要求 executescript |
| R22 | /ready 探针持写锁 + 每请求都全量探活，可致 claim 饥饿 | `medium` | `correctness` | `no` | 读连接分离 + 1-2s 缓存/合并 |
| R23 | FixedWindowRateLimiter degraded 永久黏住、桶满即全局 fail-open | `medium` | `correctness` | `no` | 窗口滚动后自愈，窗口内 LRU 淘汰可观测 |
| R24 | Inference 重试无 jitter、中间尝试无审计/指标 | `low` | `correctness` | `no` | 加 jitter 与 `mkb_inference_transport_retry_total` |
| R25 | 408/425 等瞬时 4xx 被判 validation 不重试 | `medium` | `correctness` | `no` | `408/425` 归入 `TRANSPORT_RETRYABLE` |
| R26 | INTERNAL_UNEXPECTED 直接 fail-closed 而非按矩阵重试 | `medium` | `correctness` | `no` | 明确 `TimeoutException/NetworkError` → 重试，决定 INTERNAL 策略并文档化 |
| R27 | 双层背压分叉：Facade gate 与 DispatchCaps 各自为政 | `high` | `correctness` | `no` | 单源 `DispatchCaps` 透传或 pool 感知的 facade gate + 双指标 |
| R28 | 假绿：无 coverage/strict markers/conftest，测试配置宽松 | `high` | `test-gap` | `yes` | 加 `strict-markers/warning-as-error/coverage fail_under` 与共用 conftest |
| R29 | 假绿：local_mock 豁免掩盖 Turso/向量/live 三大探针 | `high` | `test-gap` | `yes` | 追加 `turso+并发+原生向量+live stub` 剖面的 e2e 必跑 |
| R30 | 假绿：grep 栅栏/skipIf/return/>= 宽松阈值充数 | `high` | `test-gap` | `yes` | 行为测试替换 grep，`return` 改 `skip/fail`，收紧 substring/`>=` |
| R31 | 假绿：串行 soak 冒充并发、单线程 e2e 污染全局 buffer | `medium` | `test-gap` | `no` | `ThreadPool/asyncio.gather` 真并发 + per-test 隔离 |
| R32 | 假绿：检索/发布栅栏仅单元覆盖，deactivate 后未端到端验证空 | `medium` | `test-gap` | `no` | 补 deactivate/delete/reactivate→检索空的 e2e |
| R33 | 浏览器/OCR/Vision 工作流已注册但 runtime 未注入，稳定 503 误导 | `high` | `scope-drift` | `yes` | 要么下线 profile 要么注入 `BrowserFetcher/clean_llm` 并加 readiness 子项 |
| R34 | Bootstrap/retention 的 pass 无日志无指标，运维盲飞 | `medium` | `correctness` | `no` | `mkb_registry_bootstrap_fail_total` + `mkb_retention_fail_total` + 警告日志 |
| R35 | N+1 hydration：每 hit 串行两次 read_verified，无 batch 缓存 | `medium` | `correctness` | `no` | 按 `generation_artifact_uuid` 批量水合、共享解析结果 |
| R36 | 入站无全局 body size 限，10k records 可 OOM | `medium` | `security` | `no` | `ContentLengthLimitMiddleware 10MiB` + `limit-concurrency` |

> 说明：上表 36 项已去重；同类 Turso/限流细节合并为单条以避免碎片化。`critical/high` 中标 `yes` 为收口 blocker。

### R1. Turso 单连接 + BEGIN IMMEDIATE + 无 busy_timeout，跨线程/进程并发必 BUSY

- **严重级别**: `critical`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/persistence/turso/port.py:63-91` 仅 `asyncio.Lock` + `BEGIN IMMEDIATE`，`_connect:71-75` 只设 `foreign_keys=ON`，未设 `busy_timeout`/`journal_mode`；`src/persistence/sqlite_port.py:69-71` 却正确设 `WAL + busy_timeout=5000`
  - `src/persistence/engine.py:13-40` 的 `probe_concurrent_writes` 临时切 `mvcc` 再切回，但 `port.py:91` 永不走 `BEGIN CONCURRENT`，`sidecar.py:35` 却尝试 `BEGIN CONCURRENT` 后回退，全局单写者假设与 `MKB_CONCURRENT_WRITES_REQUIRED=true` 声称矛盾
  - `K11` 承认多线程 BEGIN CONCURRENT 仅部分 serial soak
- **为什么重要**:
  - 任何并发 writer（`claim_next` + `sidecar diagnostics` + `object_gc` + `readiness probe`）在同一时机都会让败者得 `SQLITE_BUSY`，当前无重试直接冒泡为 `500` 或被外层 `retryable_failure` 误判，生产高并发或双 worker 部署必现间歇 500 与 outbox 毒丸。
- **审查判断**:
  - 探针与真实写路径不一致；`concurrent_writes` readiness 可能因库已含索引而 `mvcc` 切失败直接 `503`，而切成功后写入仍是悲观锁。
- **建议修法**:
  - `_connect` 设 `busy_timeout=5000` 并尝试 `PRAGMA journal_mode=mvcc` 记录结果；`transaction()` 按探针结果选 `BEGIN CONCURRENT` vs `BEGIN IMMEDIATE` 并对 `BUSY` 做指数退避重试 3 次；`readiness` 不持写锁，改读连接或独立锁。

### R2. Worker 无 heartbeat，30s lease 与 540s 真实推理失配必 duplicate execution

- **严重级别**: `critical`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/runtime/workflow/runtime_core.py:350-491` `claim_next(lease_seconds=30)` 后 `worker.py:51` 直接 `await handler.run(command)`，期间 `WorkflowCoreMixin.heartbeat` 从未被调用
  - `src/runtime/config.py:46` `inference_generate_timeout_seconds=180` * `inference_max_attempts=3` + `max_delay 30` ≈ 544s，`claude_cli.py:148` `timeout_seconds=900` 更长
  - `src/runtime/health.py` 与 `runtime_repair` 的 `recover_expired_leases` 会在 30s 后把 `running → ready` 并 `fencing_generation+1`
- **为什么重要**:
  - 任何活推理都必超时被 fence，产生 duplicate `vectorize/construct`、`outcome ConflictError`、vLLM 重放浪费；成功栅栏长时间阻塞。
- **审查判断**:
  - `heartbeat` 存在但未接线；`WorkflowWorker` 需在 `handler.run` 期间起 `heartbeat_loop`。
- **建议修法**:
  - `worker.run_once` 启动 `asyncio.create_task(heartbeat_every(10s))` 直到 handler 结束；或把 `lease_seconds` 计算为 `max(30, generate_timeout*maxAttempts+backoff)` 并文档化；加 900s stub 仍成功的一键用例。

### R3. Claude CLI 超时泄漏子进程

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/runtime/inference/claude_cli.py:299` `await asyncio.wait_for(process.communicate(payload), timeout)` 的 `except TimeoutError: raise CLAUDE_CLI_TIMEOUT` 分支未 `process.kill()/terminate()` + `await wait()`
  - `build_claude_argv:134` 可能把 16k 以内 prompt 放 argv
- **为什么重要**:
  - 子 `claude -p` 残留成僵尸、占 fd、`/proc/cmdline` 长时间暴露 prompt 文本，重复触发可打满进程表。
- **审查判断**:
  - 通过 API 可间接触发（`non-interactive` 任务）放大为 DoS 与敏感信息残留。
- **建议修法**:
  - `except TimeoutError: with suppress(Exception): process.kill(); await asyncio.wait_for(process.wait(), timeout=5)` 再抛；`CancelledError` 同理。

### R4. 检索候选先按 UUID 截断 1000 再打分

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/services/retrieval/retrieval_rank.py:126-130` `_fetch_candidate_rows ... ORDER BY r.vector_record_uuid LIMIT ?` 设 `_candidate_scan_limit=1000`，其后才 `_rank_ann_candidates` 打分
  - `retrieval_request.py:46-77` `recall_k/return_k` 最大 100，但与 `candidate_scan_limit` 无联动校验
- **为什么重要**:
  - Team 向量 >1000 时召回是 UUID 随机子集而非语义最近，`recall_k` 合同失真；安静错误，测试用小库永不暴露。
- **审查判断**:
  - 该分支仅在 `native_vector` 不可用/未用 `VectorSearchPort.ann_search` 时生效，默认离线 `deterministic_exact` 必命中。
- **建议修法**:
  - `native_vector_required=true` 时必须走 `VectorSearchPort` 走 `vector_distance_cos` 的 ANN；BLOB fallback 要么全表扫（`COUNT(*) == scan_limit` 否则 fail-closed）要么 `native_vector` 不可用则 readiness 非 ready。

### R5. 64 ↔ 1024 维度分裂致新世代永不晋升

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/runtime/intake/core.py:56` / `src/services/config_snapshots.py:723` 默认 `dimension 64` deterministic，`migrations/009_*` 把 `qwen-vl-2b` 设 `1024`，`vectorize.py:366` `_embedding_profile` 强制校验 `dimension == _embedding_dimension`
  - `vector_publish_commit.py:289-304` `_ensure_namespace` 对同 `namespace_key='default'` 的旧 64 维度抛 `VECTOR_NAMESPACE_BINDING_CONFLICT 409`
  - `docs/baseline/domain-truth/S08` 未定义 namespace 版本化
- **为什么重要**:
  - Team 先 deterministic 后切 `live_inference=true`（或反之）则所有新向量 publish 失败但 generation artifact 已落库，形成半提交；旧 64 维度向量继续 serving，结果质量静默错。
- **审查判断**:
  - 不是测试可发现的边界，属配置演进缺口。
- **建议修法**:
  - 按 `embedding_model_key/version/dimension` 分 `namespace_uuid`（新 namespace 插入），或提供 `index.rebuild` 迁移脚本；`409` 文案给 `S08-A04` 指引。

### R6. SupplyFence 允许集基于全部 enabled 而非 winners

- **严重级别**: `high`
- **类型**: `security`
- **是否 blocker**: `yes`
- **事实依据**:
  - `api/app.py:231-240` `SupplyFence([SupplyBinding.from_binding(b) for b in default_enabled_inference_bindings()])` 展开 5 行（embed×1 + structured×2 + text×2），`registry.py:126-136` 显示 5；`registry.active_inference_bindings()` 仅 3 winners
  - `facade._preflight:375` 按 `base_url+secret_slot` 二阶段校验，备用 Lightning 模型仍在允许集
- **为什么重要**:
  - 攻击面扩大：伪造备用模型 `binding_digest`（字段公开可推导）即可过 fence，即使 L4 从未冻结它。
- **审查判断**:
  - 违背 S11「fence 精确等于 L1 winners」条文。
- **建议修法**:
  - 启动时以 `active_inference_bindings()` winners 建 fence；加单测 `supply_fence_contains_only_winners`。

### R7. Claude CLI 无并发门限

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/runtime/inference/claude_cli.py:281` + `generation_construct.py:164` 直接 `await self._claude_cli.run(req)`，不经 `InferenceFacade.ConcurrencyGate`；Facade 的 `global 12 / embed 8 / generate 2+2` 不覆盖 CLI
- **为什么重要**:
  - 突发多 Team `clean.extract.*_llm` / `lsrag.structurize` 可 fork 任意多 `claude -p`，打爆内存/`E2BIG`。
- **审查判断**:
  - 与 `R27` 双层背压同根，CLI 是第三条无门限路径。
- **建议修法**:
  - 为 CLI 设 `ConcurrencyGate(max = dispatch_local_running+ni_running)` 或经 Facade typed `claude_generate` 通道；暴露 `mkb_inference_backpressure_total{pool}`。

### R8. GC 在事务内做物理 unlink 并持写锁

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/services/object_gc.py:198-269` `async with persistence.transaction(): ... await storage.delete_if_unreferenced(...); path.unlink ... _insert proof`，`sqlite_port/turso port` 事务全程持 `_write_lock`
  - `local_store.py:34` 同样仅 `asyncio.Lock`
- **为什么重要**:
  - 单次 8MiB+ unlink 在慢盘上阻塞 `claim_next`/`Task.create`/`cancel` 数十毫秒到秒级，放大 `BUSY` 与 `R2` 超时。
- **审查判断**:
  - GC 需与 business TX 分离。
- **建议修法**:
  - 乐观两阶段：事务内 ` blocker?` 读 → 事务外 `unlink` → 第二事务复核 `blocker==0` 再写 `mkb_object_delete_proofs`；失败则回滚并 metric。

### R9. GC / Retirement 扫描器单次异常永久停摆

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/runtime/object_gc.py:42-50` / `src/runtime/index_retirement.py:40-46` `while not stop.is_set(): await run_once(); await wait_for(stop.wait())` 无 `try/except`
  - `api/app.py:519-523` 的 retention loop 却有 `try/except: pass`
- **为什么重要**:
  - 一次 `SQLITE_BUSY` 或 FS 异常即让扫描任务异常退出，外层 `lifespan:442-446` 仅 `suppress(CancelledError)` 不重启，导致 GC 停 → 磁盘无界增长，retirement 停 → `withdrawn` 堆积拖慢 ANN。
- **审查判断**:
  - 韧性不对称。
- **建议修法**:
  - 包 `try: await run_once() except Exception as exc: metrics.increment(fail_total); diagnostics.write(LOG=...) ; await sleep(backoff)`；抽 `run_forever` 基类。

### R10. claim_next 每轮只处理一个 deadline 过期项后直接 return None

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `src/runtime/workflow/runtime_core.py:353-379` `SELECT ... WHERE deadline_at < ? LIMIT 1` 的过期项 `fail` 后 `return None`，不继续 `admit/claim`
  - `worker.py:48` 每 `drain_once` 只调一次 `claim_next`，因此 100 个过期 ready 需 100 轮才排空，期间好任务饿死
  - 且 `LIMIT 1` 无 `ORDER BY` 取任意行
- **为什么重要**:
  - 队列头过期任务的清理吞吐低，可用容量被虚占。
- **审查判断**:
  - 正确性非丢数据，但高负载下可观测为「空闲但不接活」。
- **建议修法**:
  - 同事务 `while expired: fail; expired = fetchone(ORDER BY available_at)` 直到无过期再 `admit/claim`。

### R11. Fencing token 哈希未参与校验

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `runtime_core.py:350-476` 生成 `claim_token`/`claim_token_hash` 并写入 `UPDATE ... SET claim_token_hash=?`，但 `mark_running:494-543` 与 `accept_outcome` 仅校验 `fencing_generation`
  - `worker.py:51` 丢弃 `claim_token`
- **为什么重要**:
  - 代际 fence 是必要的，但 token 本可提供更强的执行期绑定；现为 dead code，易误导审计以为双因子。
- **审查判断**:
  - 按 `S03-T027` 允许 `process_uuid+generation` 单 fence，当前符合 spec 最低要求。
- **建议修法**:
  - 要么删除 token 代码，要么在 `mark_running/heartbeat/accept_outbox` 加 `AND claim_token_hash=?` 的 `compare_digest` 校验；加架构测试锁死。

### R12. Task/Team 并发 PK 冲突误报 500

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/runtime/task/task_create.py:59-91` / `src/services/teams.py:45-58` 的二阶段 `SELECT → INSERT` 在单进程 `asyncio.Lock` 下串行，但在 Turso `BEGIN CONCURRENT` 下可重叠，败者 `INSERT` 得 `IntegrityError: UNIQUE failed` 未被捕获，直接 500
  - 无 `INSERT OR IGNORE` + `rowcount` 分支
- **为什么重要**:
  - 上游编排器重试同一 `task_uuid`（幂等 replay）命中 500 而非 409，导致重试风暴与误判。
- **审查判断**:
  - 单进程串行时隐藏，真实部署必现。
- **建议修法**:
  - 包 `try: INSERT except IntegrityError: raise ConflictError("task-identity-conflict")`；对 Team 同理；补 `INSERT ... ON CONFLICT DO NOTHING` 的确定性分支。

### R13. request_ip 仅看 client.host，代理后内外网栅栏绕过

- **严重级别**: `high`
- **类型**: `security`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/runtime/security.py:463-481` `request_ip = request.client.host`，注释称转发头需可信代理层；`api/dependencies.py:150-165` `require_operator_token` / `require_metrics_access` 均依赖 `is_internal_ip(request_ip(...))`
  - 默认 `uvicorn.run(..., host=127.0.0.1)` 但未强制 `proxy_headers` 配置，README 未给反代清单
- **为什么重要**:
  - 经 Nginx/Envoy 后 `client.host == 代理 IP (10.x)` 使 `is_internal_ip==True` 对所有外网生效，`/internal/*` 与 `/metrics` 变公网可达，IP 限流坍缩为单桶 120/min 全局。
- **审查判断**:
  - Leaf-Worker 既定单机 loopback 时无害，但任何 `0.0.0.0` 或 K8s Service 前置即高危。
- **建议修法**:
  - 新增 `MKB_TRUSTED_PROXY_CIDRS`，仅当 `client.host ∈ trusted` 时才解析 `X-Forwarded-For/Forwarded`；否则忽略；默认不信任；加集成测试验证外网经代理仍 `403`。

### R14. payload_extra 密钥检查漏驼峰，vault 可持久化

- **严重级别**: `high`
- **类型**: `security`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/contracts/common/models.py:111-119` `_SECRET_KEYS` 精确集 `{"authorization","token","password","secret","api_key"...}`，`src/runtime/security.py:420-423` `_REDACT_KEY` 却是正则 `api[_-]?key|secret|credential|cookie|signature|connection|dsn|passphrase`
  - `TaskCreateRequest:343` 校验但 `TeamPatchRequest/TaskPatchRequest:44/357` 未校验；`name/title/description` 等自由文本未校验
  - 存储后 `task_views.py:74` 原样返回
- **为什么重要**:
  - 持有效 token 的内部调用方可 `PATCH ... {payload_extra:{apiKey:"sk-live..."}}` 永久落库，任意 token 持有者可 `GET` 窃取，且 `Retention` 永不清理 `mkb_tasks`。
- **审查判断**:
  - 校验与脱敏两套正则不一致，属必堵口。
- **建议修法**:
  - `assert_safe_public_data` 改 `if _REDACT_KEY.search(key): raise`；对 `TeamCreate/Patch/TaskPatch` 全量加校验；`task_views` 对 `payload_extra` 做 redacted 视图或至少审计。

### R15. /docs 默认开放无鉴权无网络隔离

- **严重级别**: `medium`
- **类型**: `security`
- **是否 blocker**: `yes`
- **事实依据**:
  - `api/app.py:451` `FastAPI(title=...)` 默认 `docs_url=/docs, redoc_url=/redoc, openapi_url=/openapi.json` 无 `dependencies`
  - `README:301` 自认开放且未在应用层限制
- **为什么重要**:
  - 经 F13 bypass 后外部可匿名枚举 `S01/S02/S10` 全量 schema，定向构造 `payload_extra` 注入与 SSRF 探测。
- **审查判断**:
  - 内网姿态可接受，但生产边缘必须关。
- **建议修法**:
  - `create_app(docs_url=None, redoc_url=None, openapi_url=None)` 或置于 `require_operator_token` 后；加 `TrustedHost` + `X-Content-Type-Options: nosniff / X-Frame-Options: DENY`；部署 helm 强制网络 ACL。

### R16. VECTORIZE 错把 space violation 包为可重试

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/runtime/intake/vectorize.py:376` `except MkbError as exc: raise MkbError("VECTORIZE_INFERENCE_FAILED", ...)` 抹掉 `INFERENCE_TRANSPORT_RETRYABLE` vs `INFERENCE_SPACE_VIOLATION/SPACE_VIOLATION` 区分
  - `intake/core.py:_RECOVERABLE_ERROR_CODES` 仅认 `VECTORIZE_INFERENCE_FAILED` 为可重试
- **为什么重要**:
  - Layer-A 维度/适配器绑定漂移等永久性 `409/422` 被重试 `max_retries` 次，浪费配额并掩盖配置错误。
- **审查判断**:
  - 错误分类是 S11 `非重试` 核心。
- **建议修法**:
  - 保留 `exc.code` 直抛；仅对 `TRANSPORT_RETRYABLE/BACKPRESSURE` 映射为 `VECTORIZE_INFERENCE_FAILED`，其余保持原码并从 recoverable 集排除。

### R17. content_full（header+body）与检索 query 裸嵌入不一致

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `src/services/lsrag_compiler/construct.py:59` / `vectorize.py:206-208` `content_full = header(sorted metadata_headers)+body` 用于离线嵌入；`retrieval_rank.py:194-216` query 嵌入直接 `deterministic_embedding(query.strip())` 未做同 header 投影
  - `retrieval_pack.py:116-155` hydrate 仅 `dual_channel_projection.units[].original/summary`，`vector_records.content_digest == stable_digest({"text": content_full})`
- **为什么重要**:
  - `metadata_refresh` 会改变 header，导致已向量化的 `content_full` 与在线 query 的余弦系统性偏低，召回质量静默下降但不报错。
- **审查判断**:
  - 属 S05/S08 已知未对齐，CI 以短文本遮蔽。
- **建议修法**:
  - 选一：只嵌 `body`，header 仅作 facet 过滤；或 query 侧同投 header；加用例断言 `vector.content_digest == stable_digest(body)` vs `content_full_digest` 区分。

### R18. 检索第二重栅栏兜底不完整

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `retrieval_rank.py:279-322` `_apply_batch_eligibility` 注入 `IntakeEligibilityPort` 时仅信其返回；`_sql_batch_eligibility` 回退仅查 `item.lifecycle_state='active' && serving==rev`，未镜像完整 S09 `p.lifecycle_state='active' && proof 完整 && validation_disposition='full_valid'` 谓词
  - 错误映射把任意 `Exception` 归 `RETRIEVE_DEPENDENCY_ELIGIBILITY 503`
- **为什么重要**:
  - 注入的 adapter 喂脏 `approved` 集时仅靠第二重 `_revalidate_publication_fence` 兜底；兜底抛 `503` 时诊断丢失 `filtered_count` 区分。
- **审查判断**:
  - 防御深度正确但第一重不完整降低可观测性。
- **建议修法**:
  - `_sql_batch_eligibility` 镜像全谓词；注入端校验 `team_uuid` 一致性并审计；统一错误码为 `RETRIEVE_DEPENDENCY_*` 并 metric 区分。

### R19. sqlite 后门由环境变量伪造

- **严重级别**: `high`
- **类型**: `security`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/persistence/factory.py:12-16` `sqlite_backend_permitted() = bool(os.environ.get("PYTEST_CURRENT_TEST"))`，任意部署 `export PYTEST_CURRENT_TEST=1` 即可绕过「生产与 0815 必须 Turso」宪法
  - `config.py:23` 默认 `persistence_backend=turso` 但无启动期强制检查
- **为什么重要**:
  - 生产误用 `sqlite` 将失去 MVCC/原生向量与并发探针，静默降级。
- **审查判断**:
  - 防护只防君子。
- **建议修法**:
  - 要求显式 `MKB_ALLOW_SQLITE=1` 豁免 + 启动日志 + `mkb_factory_sqlite_allow_total`；或校验 `sys.argv` 与 `PYTEST_VERSION` 双因子。

### R20. Migration ledger 用 Python !r 插值

- **严重级别**: `high`
- **类型**: `security`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/persistence/migration_runner.py:132-138` `ledger_sql = f"VALUES ({migration_id!r}, {checksum!r}, {utc_now()!r}, 'mkb')"` 拼进 `executescript`，非参数化
- **为什么重要**:
  - 文件名即 `migration_id` 可控时 `!r` 非 SQL 标准转义，且与 `?` 绑定纪律分裂。
- **审查判断**:
  - 低概率但可被污染的供应链面。
- **建议修法**:
  - `executescript` 执行 DDL，另起 `execute("INSERT INTO mkb_schema_migrations VALUES (?,?,?,?)", (id, checksum, now, 'mkb'))` 参数化。

### R21. Turso 下 executescript 回退执行多语句

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `yes`
- **事实依据**:
  - `migration_runner.py:65-72` `executescript = getattr(connection, "executescript", None); if callable: ... else: connection.execute(executable)`；`pyturso` 通常无 `executescript`，`execute` 不支持多语句脚本首个 `CREATE` 即 `syntax error`
- **为什么重要**:
  - 首个生产 `migrate()` 即失败，回退到 `503 not ready` 永久。
- **审查判断**:
  - 单测用 `sqlite3` 掩盖，Turso 真库首次启动必现。
- **建议修法**:
  - 检测并以 `;` 分割（跳过字符串/注释）循环 `execute`，或在 CI 用真 `turso` 跑 `migrate` 单测。

### R22. /ready 探针持写锁且每请求全量探活

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `src/persistence/turso/port.py:100-130` `readiness()` 在 `async with _write_lock` 内做 `verify_migrations + probe_concurrent_writes + probe_native_vector` 的 `to_thread` 阻塞；`api/app.py:166-197` `_probe` 又在 `transaction()` 内查 `sqlite_master` 三表
  - `api/dependencies.py:191-194` `require_ready` 与 `workflow_claim_readiness:277-280` 每次 `claim_next` 前都调 `health.ready()`
- **为什么重要**:
  - 100 rps 突发探活与 `claim_next/outbox` 竞争写锁，周期性 claim 停摆；`readiness false → claim 直接 `NotReadyError` 进 repair loop。
- **审查判断**:
  - liveness 与 business 状态面耦合。
- **建议修法**:
  - `readiness` 用独立读连接；`/ready` 结果缓存 1-2s 并合并并发请求；`obs_tables` 检查不用事务。

### R23. 限流器 degraded 永久黏住与桶满全局 fail-open

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `src/runtime/security.py:185-215` 任何异常即 `self.degraded=True` 不复位；`max_buckets=4096` 对 `(dim,identity,bucket)` 去抖，攻击者以 IPv6 /64 轻易打满 → 后续全员绕过限流
  - `api/dependencies.py:105,146` 仅设 gauge，无 `mkb_sec_rate_limited_total{degraded}` 区分
- **为什么重要**:
  - 噪声告警与限流失效并存。
- **审查判断**:
  - 属 S16 承诺的独立 `30/min/IP` 未对 `/metrics` 生效的同类缺口。
- **建议修法**:
  - 窗口滚动后自愈 `degraded=False`，成功 ` _allow` 后重置；LRU 淘汰时 metric；对 `/metrics` 单设 `30/min` 桶。

### R24. 推理重试无 jitter、中间尝试无审计

- **严重级别**: `low`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `src/runtime/inference/facade.py:319` `_retry_delay = initial*2^attempt capped 30s` 无随机；`262-343` 每逻辑调用仅一次 `record_success/failure`，中间 `TRANSPORT_RETRYABLE` 不记 `InvocationRecord`，仅 `mkb_sec_supply_reject_total` 计数
- **为什么重要**:
  - vLLM 重启后 N worker 同步 `1s/2s/4s` 重放放大过载；重试率不可观测。
- **审查判断**:
  - 按 S11-E05 允许 jitter 但未实现。
- **建议修法**:
  - `delay * (0.8 + 0.4*rand)`；重试前 `metrics.increment("mkb_inference_transport_retry_total", capability, code)`。

### R25. 408/425 等瞬时 4xx 被判 validation 不重试

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `src/llm_adapters/local_vllm.py:212` 仅 `429/503/>=500` → `TRANSPORT_RETRYABLE`，其余 `4xx` → `INFERENCE_VALIDATION_REMOTE`
  - `408 Request Timeout` 实际瞬时
- **为什么重要**:
  - 408 直接 fail-closed 成 `502`，浪费外层 `max_retries` 的 Process 重试。
- **审查判断**:
  - 修正为 `status in {408,429,503}` 或按 body `code==rate_limited` 皆重试。
- **建议修法**:
  - 白名单加入 `408,425`；超时应为 `RequestError` 而非状态，已正确。

### R26. INTERNAL_UNEXPECTED 直接 fail-closed 未按矩阵重试

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `facade.py:343` `except Exception → MkbError(INFERENCE_INTERNAL_UNEXPECTED,503)` 后 `record_failure`+`raise` 不重试；S11-E05 写「INTERNAL = indeterminate/retryable（impl 钉死默认值）」当前钉为不重试
- **为什么重要**:
  - `httpx.TimeoutException` 若以泛异常冒泡将走 Process 级重试而非传输级 3 次退避，偏离 S11-T010。
- **审查判断**:
  - 需显式把 `httpx.TimeoutException/NetworkError` 映为重试。
- **建议修法**:
  - `INFERENCE_INTERNAL_UNEXPECTED` 加入重试集或前置映射 `httpx` 超时为 `TRANSPORT_RETRYABLE` 并文档化钉死策略。

### R27. 双层背压分叉：Facade gate 与 DispatchCaps 各管各

- **严重级别**: `high`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `api/app.py:245-250` `InferenceFacade(capability_limits={embed:8, structured:2, text:2}, global 12)`，`DispatchCaps.from_settings(local 2/6, ni 2/4, embed 8/20)` 给编排器；`retrieval.search` 的 embed 直连 facade 绕过编排
  - `S11-E06` 的「gate 满则零模型调用」取决于谁先满
- **为什么重要**:
  - `检索 spike 8 embed` 可饿死 `vectorize`，`local` 编排 admit 2 而 facade 允许 4 generate 导致背压不一致。
- **审查判断**:
  - NS2 称「orchestrator 与 facade 双 gate」，但未统一 `dispatch_pool` 语义。
- **建议修法**:
  - 单源 `DispatchCaps` 对象透传两处，或使 Facade 按 `dispatch_pool` 感知；双指标 `mkb_inference_backpressure_total{gate=facade|orchestrator}`。

### R28. 假绿：无覆盖率/strict 校验/conftest，测试配置宽松

- **严重级别**: `high`
- **类型**: `test-gap`
- **是否 blocker**: `yes`
- **事实依据**:
  - `pyproject.toml:38-41` 仅 `-q --tb=short`，无 `--strict-markers --strict-config -W error --durations --maxfail --xfail-strict`，无 `tool.coverage fail_under`
  - `tests/` 无顶层 `conftest.py`，各文件自造 `tmp_path`/`Settings`/`token`，无 determin clock/uuid、env 清理、网络禁用 guard
- **为什么重要**:
  - 覆盖率数字可凭 `passed N` 虚高，关键路径 `BEGIN CONCURRENT/ANN/live` 零覆盖仍绿。
- **审查判断**:
  - 门槛型缺陷。
- **建议修法**:
  - 加 `addopts = -q --tb=short --strict-markers --strict-config -W error::DeprecationWarning --durations=10`，`[tool.coverage] branch=true fail_under=75` 并在 CI 对 `src/persistence/*, src/runtime/workflow/*, src/services/retrieval/*` 设最低。

### R29. 假绿：local_mock 豁免掩盖三大探针

- **严重级别**: `high`
- **类型**: `test-gap`
- **是否 blocker**: `yes`
- **事实依据**:
  - `tests/local_runtime.py:21-25` `concurrent_writes_required=False, native_vector_required=False, live_inference=False, inference_probe_enabled=False`；几乎所有 `tests/e2e` 复用它
  - `tests/unit/test_turso_driver.py:87` 仅 1 个向量用例，`tests/integration/test_r3_turso_evidence_ready.py:12` 用 `skipIf(not TURSO.is_file())` 在 CI 直接跳过
- **为什么重要**:
  - `SqlitePersistence` 的 `BEGIN IMMEDIATE` 与 `deterministic-hash 64d` 使 e2e 永不走 `BEGIN CONCURRENT/BLOB→vector32/真实 vLLM 超时` 分支，`prod` 探针失败在测试中静默豁免。
- **审查判断**:
  - 最严重的 false-green 根因。
- **建议修法**:
  - 增加 `turso` 真库的 `concurrent_writes_required=True, native_vector_required=True` 剖面，至少让 `scatter/human/index_rebuild/retrieval` 各有一条走真 Turso + `ThreadPool` 并发；`skipIf` 改为 `failIfMissingInCI`。

### R30. 假绿：grep/skipIf/return/阈值宽松充数

- **严重级别**: `high`
- **类型**: `test-gap`
- **是否 blocker**: `yes`
- **事实依据**:
  - `tests/unit/test_ns4_jsonl_journal.py:10-15` 仅 `assert "_JOURNAL_FORBIDDEN" in text`；`tests/domain/test_r4_launch_lock.py:26` `if not path.is_file(): return` 静默 pass；`tests/e2e/test_single_intake_pipeline.py:379` `assert structured_calls >=2` 而非 `==3`
  - `tests/e2e/test_index_rebuild.py:402` `assert payload in old_layers or (payload and payload in old_text)` 子串即过；多处 `assert "answer" not in str(result)` 对 `str(result)` 子串而非 `json.dumps`
- **为什么重要**:
  - 删掉被测函数也绿的「删测仍绿」类假绿。
- **审查判断**:
  - 合同栅栏被文本包含替代行为验证。
- **建议修法**:
  - grep 栅栏改真实行为调用；`return` 改 `pytest.skip/fail`；`>=` 改精确等值 + `invocation_uuid` 唯一性；`str` 改 `json.dumps(sorted)` schema 校验。

### R31. 假绿：串行冒充并发、全局 buffer 污染

- **严重级别**: `medium`
- **类型**: `test-gap`
- **是否 blocker**: `no`
- **事实依据**:
  - `tests/integration/test_ns4_cw_soak.py:55` `for i in range(8): _one(i)` 注释「Soak serially」刻意避开 `BEGIN CONCURRENT` 冲突；`tests/unit/test_ns4_stage_report_tx.py:12` / `test_ns4_fail_path_turso.py:21` 共享进程全局 `record_pending_generation_evidence` buffer，`take()` 在开头清一次但无 `finally` 隔离
  - `tests/e2e` 的 `monotonic < deadline: sleep(0.02)` 轮询无 `pytest-timeout`，硬编码 5-8s 忽略 backoff 天花板
- **为什么重要**:
  - 并发回归在单线程串行下永不失败；并行执行顺序依赖导致偶发绿。
- **审查判断**:
  - 需真并发 + 隔离。
- **建议修法**:
  - `ThreadPoolExecutor/asyncio.gather` 真并发 8 写 `sidecar.insert` 并断言 code；`conftest` 对 `record_pending_*` 做 `autouse` 清理；轮询抽 `wait_for_terminal(..., timeout=10)` 并在超时 dump `mkb_processes/mkb_executions`。

### R32. 假绿：检索双栅栏仅单元覆盖，deactivate 未端到端验证

- **严重级别**: `medium`
- **类型**: `test-gap`
- **是否 blocker**: `no`
- **事实依据**:
  - `tests/unit/test_retrieval_service.py:279` 空结果 `set(units)==set(units)` 恒真、`315-335` 连续 mutate 测空但无非空基线；`tests/e2e/test_single_intake_pipeline.py:148` 用 `read_only sqlite3` 旁路打开 Turso 文件查 `embedding`，未对 `native_vector` 语义断言
  - `tests/e2e/test_source_capability_paths.py:71-145` 仅 `status==succeeded`，不查 `publication_state/index_generation` fence；无 `deactivate→检索空→reactivate→检索恢复` e2e
- **为什么重要**:
  - 停用/删除后旧向量仍 serving 的回归被单元「空即过」掩盖。
- **审查判断**:
  - 关键不变量无 e2e 活证。
- **建议修法**:
  - 补 `intake.deactivate/delete/update_metadata` 后 `retrieval:search == empty` 且 `deleted_at/pointer` 一致性的 e2e；基线先断言非空再 mutate。

### R33. 浏览器/OCR/Vision 工作流已注册但 runtime 未注入

- **严重级别**: `high`
- **类型**: `scope-drift`
- **是否 blocker**: `yes`
- **事实依据**:
  - `src/workflows/lsrag_definition.py:882-1070` 12 个 `BUILTIN_SOURCE_PROFILE_WORKFLOWS` 含 `browser/ocr/vision/doc_llm/web_llm`，`src/runtime/intake/core.py:342-367` 皆有 `process_key` 分发，但 `api/app.py:317-330` `IntakePipeline(..., http_fetcher=acquirer, browser_fetcher=None, clean_llm=None)` 仅 `HttpAcquirer`
  - `intake/web/__init__.py:64` / `intake/doc/__init__.py:58` / `clean_preflight.py:76` 明确 `cli_clean_supported=False` 对 `ocr/vision` 永不 salvage，稳定 `CLEAN_*_CAPABILITY_UNAVAILABLE 503`
  - `README 6.3` 标记「合同已落地/未接线」但 `registry` 仍对外宣称 source_kind 可用，readiness 亦不检查
- **为什么重要**:
  - 上游以为 `http_resource/browser` 可用而批量投放，全部稳定失败，错误码正确但可用性误导与部署后才发现。
- **审查判断**:
  - 配置与注册表不一致。
- **建议修法**:
  - 视标：要么从 `BUILTIN_SOURCE_PROFILE_WORKFLOWS` 下线三 profile 直到 `BrowserFetcher`（Playwright）与 `clean_llm`（OCR/Vision 模型经 SupplyFence）落地，要么注入并加 `readiness.browser/ocr` 子项与 `MKB_BROWSER_ENABLED` 开关。

### R34. Bootstrap/retention 的 pass 无日志无指标

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `api/app.py:407-413` `try: registry.bootstrap() except MkbError: pass` / `try: workflows.bootstrap() except MkbError: pass` 无 log/metric；`api/app.py:523` `except Exception: pass`；`persistence/engine.py:33,40` rollback/回切 `except: pass`
- **为什么重要**:
  - 运维只见 `503 not ready` 但无根因，`retention` 失败静默丢弃观测证据。
- **审查判断**:
  - 与 GC/retirement 的「单次即死」相反，这是「静默吞掉」。
- **建议修法**:
  - `except MkbError as exc: metrics.increment("mkb_registry_bootstrap_fail_total", code=exc.code); diagnostics.write(log_code="REGISTRY_BOOTSTRAP_FAIL")` 再 pass；retention 同理 `mkb_retention_fail_total`。

### R35. N+1 hydration 串行放大 retrieval 尾延迟

- **严重级别**: `medium`
- **类型**: `correctness`
- **是否 blocker**: `no`
- **事实依据**:
  - `src/services/retrieval/retrieval_pack.py:34-116` `_to_result_work` 每 `summary` hit 调两次 `load_retrieval_body`（summary+original），`188-259` `_inflate_documents` 串行 `for item in work: await _load_material(...)`
  - `retrieval_request.py:138-141` 对 `return_k=50, recall_k=100` 即 100 次 `transaction + storage.read_verified + JSON parse`
- **为什么重要**:
  - 尾延迟线性放大，`candidate_scan_limit 1000` 时更显著；虽正确但可观测为检索 P99 抖动。
- **审查判断**:
  - 性能隐患非 correctness，但影响 SLO。
- **建议修法**:
  - 按 `generation_artifact_uuid → projection` 加内存缓存，批量 `SELECT ... WHERE generation_artifact_uuid IN (...)` + 并发 `read_verified`。

### R36. 入站无全局 body size 限

- **严重级别**: `medium`
- **类型**: `security`
- **是否 blocker**: `no`
- **事实依据**:
  - `api/app.py:451` `FastAPI()` 未加 `ContentLengthLimitMiddleware`，`contracts/api/models.py:129` `records` 最大 10k 但无字节上限，`payload_extra 64KiB` + `inline 8MiB` 可叠加；`RequestValidationError:464` 已缓冲完才 422
- **为什么重要**:
  - 100 并发大包可在 Pydantic 校验前 OOM。
- **审查判断**:
  - 需早期 413。
- **建议修法**:
  - Starlette 中间件 `max_body=10MiB` 早期 413，`uvicorn --limit-concurrency` 配合；`records` 加 `max_bytes` 联合约束。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | Task 幂等创建、Task lineage、result/generations/items/gates/restart 投影 | `done` | `task_create.py:59-91` 指纹 409 vs 200、`task_views/task_projections` 严格 scoped，public 不泄 execution/process |
| S2 | Task state machine（queued/running/succeeded/failed/cancelled）与 cancel/retry/restart 语义 | `partial` | 状态机与 `success-wins over cancelling`落地，但并发 PK 500、priority 改写对历史执行未隔离（见 R12） |
| S3 | Workflow engine：claim/lease/fencing/outbox/human gate/scatter/repair 重启恢复 | `partial` | claim/CAS/outbox 竿线可读，但 lease 30s 无心跳必 fence（R2）、过期项逐个 return None（R10）、扫描器单次即死（R9） |
| S4 | Intake asset lifecycle：sealed candidate → snapshot/accept → serving eligibility | `done` | `clean_preflight/acceptance_*` 两段 TX 的 CAS 正确，`lifecycle_apply` 的 `withdrawn` 与 pointer 同 TX |
| S5 | Intake cleaning：deterministic/web/pdf/doc + prompt 冻结 | `partial` | `sanitize_html`/文本归一落地，但 browser/ocr/vision 未注入稳定 503、CLI clean 回退条件与 prompt 二重读（见 R33、A2） |
| S6 | LS-RAG structurize：g0/g1/g2 分层、granularity 闭集 | `done` | `adopt_layered_json` + `g0 mandatory` 校验落地，`prompt_profiles` flavor 隔离 |
| S7 | LS-RAG construct：dual-channel + ContentFullRecipe + whole-artifact 投影 | `partial` | 投影与 2-channel 落地，但 `content_full` header 嵌入与检索 query 不一致（R17）、salvage 码过宽 |
| S8 | Embedding/Vectorization：Layer A 冻结、withdrawn→indexed 发布 | `partial` | UoW 内 `withdrawn→indexed` 正确，但 64/1024 维度 schism（R5）、`16k` 预算仅 live 生效 |
| S9 | Vector index：proof + active pointer CAS + grace retirement | `done` | `vector_publish_commit` 同 TX `proof+pointer+CAS+namespace MAX` 正确，但 retirement 扫描缺 `FOR UPDATE` 竞态 |
| S10 | Retrieval：dual fence、context-only、pack/truncate、rerank honest fallback | `partial` | 双栅栏思路对，但候选截断错（R4）、N+1（R35）、forbidden keys 对 Pydantic 对象绕过 |
| S11 | Inference runtime：SupplyFence/ConcurrencyGate/Transport 重试 | `partial` | Facade gate/readiness 骨架对，但 fence 过宽（R6）、CLI 无门限（R7）、408/INTERNAL 重试与 jitter（R24-R26）、双层背压分叉（R27） |
| S12 | Turso 持久化：migration/事务/CAS 隔离 | `partial` | 单测通过，但 Turso 单连接/IMMEDIATE/busy/probe 脱节（R1/R21/R20/R22），迁移 ledger 非参数化 |
| S13 | Artifact storage：CAS + atomic promote + 引用计数 + GC | `partial` | `promote` 原子+fsync 正确，但 GC 事务内 unlink（R8）、`identity.json` 非 `O_EXCL` 竞态 |
| S14 | Config/prompt/model registry 冻结与 binding | `done` | L0→L4 snapshot + `prompt content_sha256` + `binding_digest` CAS 冻结链闭环 |
| S15 | Observability：事件/诊断/审计/retention/metrics | `partial` | 三灯表 + bounded retention 落地，但 bootstrap/retention 静默 pass（R34）、GC/retirement 死摆（R9）、readiness 持锁（R22） |
| S16 | Security：auth→resource 排序、egress SSRF、secret/redaction、限流 | `partial` | 主姿态 fail-closed，但代理 IP 绕过（R13）、payload_extra 驼峰（R14）、docs 开放（R15）、限流 degraded 粘住（R23）、全局 body 限缺失（R36） |

### 3.1 对齐结论

- **done**: `5`（S1/S4/S6/S9/S14）
- **partial**: `11`（S2/S3/S5/S7/S8/S10/S11/S12/S13/S15/S16）
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 这更像“**核心骨架与证据链已闭环，但并发/向量/推理/安全四个生产剖面仍有必现的失配与假绿**”，而不是 completed。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | Billing 真实计费/额度（T-O-357） | `遵守` | `DefaultBillingService` 始终 true 且 `README K10` 显式 stub，未伪装计费能力 |
| O2 | 前端与静态站点 `frontend/public` | `遵守` | 仅 `.gitkeep` 占位，README 标 OOS，未越界实现半成品 UI |
| O3 | 生产部署（Docker/K8s/TLS/域名） | `遵守` | 仓库无部署清单符合「单机内网 leaf-worker」定位，未宣称公网就绪 |
| O4 | 浏览器渲染/OCR/Vision 若未接线应稳定拒绝 | `部分违反` | 已注册 workflow 但未注入 runtime，虽稳定 503 却仍被 registry 宣称为可用 source（R33）—— 属 deferred 但对外可用性误导 |
| O5 | 已冻结 corpus / 既往 closure 当 live 证据 | `遵守` | README 自限「不把 plan/closure/既有 corpus 当 live 证明」，R4 明示 4/4 失败未洗白 |
| O6 | 对外向量/对象 CRUD 直连 | `遵守` | 无公开 raw vector/object CRUD，仅团队内 lineage/generation 读 |
| O7 | R5 system-owned g0 / quoted cuts | `遵守` | 仅 `docs/plan` 方案，`data/prompts/data/schemas/src` 均未落地，未越界 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**: `changes-requested — 该实现主体成立，但当前不应标记为 R5/live/completed；以现有默认配置与测试信号上线会遭遇可复现的 lease fence、BUSY 500、GC/retirement 停摆与内外网隔离绕过。`
- **是否允许关闭本轮 review**: `no`
- **关闭前必须完成的 blocker**（按优先级）:
  1. `R1 Turso 并发：补 busy_timeout + MVCC/CONCURRENT 选择 + BUSY 重试，并把 readiness 改读连接/缓存`（否则双 writer 必 500）
  2. `R2 Worker 心跳：handler 期间 heartbeat loop 或等效 lease 放大，定死最长 wall-time 公式并单测 900s stub`（否则活推理必 duplicate）
  3. `R9 扫描器韧性：GC/retirement 的 run_forever 加 try/except+metric+backoff，统一 retention 的韧性语义`
  4. `R8 GC 持锁 unlink：改为事务外 unlink 的两阶段并复核 blocker`
  5. `R12 并发 PK 500→409：Task/Team INSERT 捕获 IntegrityError`（否则上游幂等重试风暴）
  6. `R13 代理后内网绕过：可信代理 CIDR + 仅可信才信 XFF，并对 /internal 与 /metrics 集成测旁路`
  7. `R14 payload_extra 驼峰 vault：校验改 _REDACT_KEY 正则并对 Team/Task PATCH 补校验`
  8. `R6 SupplyFence 缩小为 winners：启动期以 active_inference_bindings 建 fence 并单测守护`
  9. `R7 CLI 并发门限：给 claude_cli 独立 gate 或走 facade typed 通道`
  10. `R4 检索截断：切 VectorSearchPort ANN，BLOB 模式 fail-closed；并补 64/1024 的 namespace 迁移（R5）`
  11. `R28-R30 假绿门槛：补 conftest/coverage/strict markers，补一条 turso+并发+原生向量的 e2e 必跑，把 grep/return/>= 改行为断言`
  12. `R15 /docs 收口：默认关闭或置于 operator 鉴权后，加安全头与网络 ACL 文档`
  13. `R3 CLI 僵尸：超时必 kill+wait`（生产 DoS 面）
  14. `R33 能力误导：下线或注入 browser/ocr/vision 并补 readiness 子项`
  15. `R20+R21 迁移：ledger 参数化 + Turso executescript 真执行`（否则新库首次迁移即错）
- **可以后续跟进的 non-blocking follow-up**:
  1. `R16 错误分类：VECTORIZE 保留原始 code，space violation 不重试`
  2. `R17 content_full vs query header 一致性方案二选一并补用例`
  3. `R10 claim_next 过期循环与 ORDER BY；R11 token 死码清理`
  4. `R22 readiness 缓存/合并；R23 限流 degraded 自愈与 LRU 可观测`
  5. `R24-R26 推理重试 jitter/408/INTERNAL 策略钉死并文档化`
  6. `R27 双层背压统一为单源 DispatchCaps + 双指标`
  7. `R35 检索批量水合；R36 全局 body 限 10MiB；R34 bootstrap/retention 指标化`
  8. `R18 检索第一重栅栏完备化；R19 sqlite 豁免改显式 MKB_ALLOW_SQLITE`
- **建议的二次审查方式**: `independent reviewer`（Turso 并发与检索 ANN 需真库复跑，安全代理绕过需集成测，测试假绿需跑 coverage 门槛）
- **实现者回应入口**: `请按 .adocs/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
