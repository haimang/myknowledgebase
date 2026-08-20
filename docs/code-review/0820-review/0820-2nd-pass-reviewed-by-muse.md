# Nano-Agent 代码审查报告

> 审查对象: `MKB 全仓 HEAD @ 8cb2cb4 / NS5-0820-bug-fixes 落地后 (375c4fa..HEAD)`
> 审查类型: `rereview`
> 审查时间: `2026-08-20`
> 审查人: `Muse Spark (OpenCode)`
> 审查范围:
> - `src/persistence/*` (`uow.py`, `turso/port.py`, `turso/sidecar.py`, `engine.py`, `factory.py`, `migration_runner.py`, `migrations/014*.sql`, `015*.sql`, `retrieval_access.py`)
> - `src/runtime/workflow/*` (`worker.py`, `runtime_core.py`, `runtime_outbox.py`, `runtime_outcome.py`, `runtime_gates.py`, `workflow_supervisor.py`, `dispatch.py`)
> - `src/runtime/intake/*` (`vectorize.py`, `vector_publish_commit.py`, `acquisition_ingest.py`, `acceptance_snapshot.py`, `generation_construct.py`, `generation_live.py`, `generation_evidence.py`, `types.py`, `clean_preflight.py`)
> - `src/services/retrieval/*` (`retrieval_rank.py`, `retrieval_pack.py`, `retrieval_request.py`), `src/services/object_gc.py`, `src/services/index_retirement.py`, `src/services/artifacts.py`, `src/storage/local_store.py`
> - `src/runtime/security.py`, `src/runtime/health.py`, `src/runtime/config.py`, `api/app.py`, `api/dependencies.py`, `src/llm_adapters/local_vllm.py`, `src/runtime/inference/claude_cli.py`, `src/runtime/inference/facade.py`
> - `src/contracts/api/models.py`, `src/contracts/common/models.py`, `src/contracts/lsrag/layered_content.py`
> - `tests/unit/*`, `tests/integration/test_ns5_turso_mainchain.py`, `intake/text.py`
> 对照真相:
> - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md` (103 VF, `75 [true-bug] + 12 [partial-delivery] + 9 [true-deferred] + 7 n/a`)
> - `docs/plan/new-start/NS5-0820-bug-fixes.md` (P1-P6, 62项, DAG `P1→P2→P3→P4→P6` / `P1→P5→P6`)
> - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md` (`closed-with-explicit-deferrals`, `r4`)
> - `docs/baseline/domain-truth/` S03/S08/S09/S10/S11/S12/S15/S16, D04
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 第1轮 6-Phase 修复把「不可恢复 IO / 出示证明说谎 / 毒丸冻 supervisor」等最危险的 fail-open 已翻转为 fail-closed，但以 0820-review 的完整目标（修复全部 in-scope 缺口 + 长期治理）衡量，**当前 HEAD 不满足关闭条件**。若干宣称 DONE 的能力在生产默认画像下是永久断点，且存在事务死锁与在线数据被覆盖的新风险。

- **整体判断**：`6 阶段修复的主体成立且 honesty 值得肯定（VF36/VF52/VF62/VF40.r/VF85 等显式标 partial 未粉饰），但 UoW 取消窗口、默认 Turso 画像开箱 503、向量 upsert 误改在线行、安全边界可绕过等 blocker 使 0820-review 仍不能收口。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. `src/persistence/uow.py:26 的 BEGIN 在 try 外：CancelledError 在 BUSY 等待中可使单例连接永久滞留 in_transaction，后续全部写事务以 cannot start a transaction within a transaction 永久失败 — 新引入的可用性 blocker。`
  2. `默认 Settings.concurrent_writes_required=True 与 TursoPersistence.readiness() 强制 gates[concurrent_writes]=False 矛盾：HealthAggregator.REQUIRED 含该项 → /ready 恒 503 → WorkflowRuntime.claim_next 被 readiness fence 永久关闭 — 默认画像开箱即不可领活。`
  3. `vectorize 重放的 upsert 未以 (generation + publication_state) 限界：同一 (artifact, block, channel, model) 的服务中 indexed 行可被新世代向量化就地 UPDATE 为 withdrawn/next_generation，在 S09 proof 切回旧世代的瞬间造成在线检索静默丢数。`

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。明确看了哪些文件、跑了哪些命令、核对了哪些计划项。其他 reviewer 的结论仅作线索，逐项独立复核 file:line。

- **对照文档**：
  - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md` — 仅作「宣称已修清单」线索，不采纳其 verdict
  - `docs/plan/new-start/NS5-0820-bug-fixes.md` — P1-P6 62项与 DAG 依赖
  - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md` (`r1..r4`, hard-gate 8/10 PASS, 5 partial)
  - `docs/closure/new-start/deferred-items-ledger.md` — NS5 段三分类
- **核查实现**：
  - `git log --oneline 375c4fa..HEAD` 10 commits (`d728d0b` P1, `4ad95c5` P2, `fd5c969` P3, `52e3913` P4, `34c86b6` P5, `7bffb70` P6, `f7bec3f` ruff, `c7c74f2` hard-cut, `8cb2cb4` self-audit)
  - `git diff 375c4fa..HEAD --stat` 94 files +5637/-567
  - `Read` 关键文件 18 个并给 file:line（见 1.1/1.2 证据列）
  - 定制 4 路对抗性视角（幂等/竞态·durable、leaf-worker 接口/安全/稳定、Turso 载体/可观测/SSOT、修复完整性/逻辑冲突）并行审查后去重，交叉到本稿独立归因
- **执行过的验证**：
  - `git show d728d0b..8cb2cb4 --stat` 逐 phase 校验宣称修改落点
  - `Read src/persistence/uow.py:12-46`, `src/persistence/turso/port.py:152-177`, `src/runtime/health.py:26-44`, `src/runtime/security.py:476-499,502-507,524-536`, `src/contracts/api/models.py:50-59,362-377`, `api/app.py:527-538`, `src/llm_adapters/local_vllm.py:206-246`, `src/runtime/intake/vector_publish_commit.py:334-477`, `src/runtime/workflow/worker.py:65-162`, `src/services/retrieval/retrieval_rank.py:100-137,339-433`, `src/persistence/migrations/014*.sql,015*.sql`
  - 未重跑 `tests/e2e`（已知 VF86 `NS1-V11` sqlite3-on-Turso 永久红）；抽样读 `tests/unit/test_ns5_*.py`、`test_turso_driver.py`、`test_ns5_turso_mainchain.py` 判定 falsifiable 覆盖
- **复用 / 对照的既有审查**：
  - `0820-reviewed-by-*` 4 份与 `0820-2nd-pass-reviewed-by-gemini/grok` — 仅作线索，未采纳结论；本稿所有 finding 均有独立 file:line 复核

### 1.1 已确认的正面事实

- **UoW 取消安全（body 段）已落地**：`src/persistence/uow.py:32-46` 在 `yield` 内 `except BaseException → shield(rollback) → body_ok 时 discard`，`tests/unit/test_ns5_uow_cancel.py` 可证 `cancel 后可再 BEGIN`，关闭 VF1 主路径。
- **Sidecar 串行化彻底消除 exit 134**：`src/persistence/turso/sidecar.py:62-77` 单连接 + `threading.Lock` + 固定 `BEGIN IMMEDIATE`，`tests/unit/test_ns5_sidecar_serial.py` 4×20 线程 soak PASS，关闭 VF3。
- **Outbox 毒丸不再冻 supervisor**：`src/runtime/workflow/runtime_outbox.py:58-77,343-377` 先 `UPDATE in_flight` 提交再 `json.loads`，非法行在新事务标 `dead` 并写领域事件；`workflow_supervisor.py:42-64` 单 tick `try/except` 后仍 `claim_next/repair`，`test_ns5_outbox_poison.py` 钉死 VF61。
- **Heartbeat 已持有租约**：`src/runtime/workflow/worker.py:139-162` `lease/3` 心跳 + CAS 失败即 `fenced.set() → cancel(handler)` → `retryable_failure:lease-heartbeat-fenced`，关闭 VF10 的必现双跑（`allow_overlapping_run_once=False` 保证在 heartbeat 绿之前不并发）。
- **Publication proof 不再说谎**：`src/runtime/intake/vectorize.py:186-192` 超 16k 必 `VECTORIZE_BUDGET_CONTENT_FULL 422` 且 `required_units==succeeded_units` 校核；`vector_publish_commit.py:144-162` 指针 `active < excluded` 防回拨；`015` 的 `ux_vec_coord_active(... index_generation)` 使同坐标跨代可共存，关闭 VF27 核心与 VF55。
- **检索召回截断与双栅栏已 fail-closed**：`src/services/retrieval/retrieval_rank.py:129-136` `LIMIT+1 → RETRIEVE_SCAN_TRUNCATED 503`；`retrieval_rank.py:339-433` 的 `S04 + 重检 S09 proof` 双 fence 与 `_PROOF_COMPLETE_SET_PREDICATE` 闭环，关闭 VF47 的丢最高分与 VF54 的单通道 purge。
- **安全与交付 honesty**：`starlette>=1.0.1 + TrustedHost` 已落地离 CVE 段；`P2-07/08` 的指纹去审计时间戳、409 归一、脱敏 `redact()[:512]`、ledger 参数化、`014` 32hex 改写、`scored-first dedup (-ann_score)` 与 `LIVE mismatch 409` 均有可复核 file:line；`closure r4` 对 `VF36/52/62/40.r/85` 标 `partial` 未粉饰，符合 ledger `§0.4 no-free-defer` 硬规则。

### 1.2 已确认的负面事实

- **UoW `BEGIN` 窗口可被 `CancelledError` 撕裂**：`src/persistence/uow.py:26` 的 `await to_thread(connection.execute, begin_sql)` 在 `try` 外，取消发生在该 await 期间将跳过 `rollback/discard`，单例连接停留 `in_transaction`，后续 `BEGIN IMMEDIATE` 恒 `cannot start a transaction within a transaction`。
- **默认 Turso 画像永久 503**：`src/persistence/turso/port.py:152-177` 旁路 `probe_concurrent_writes` 成功也因 `concurrent_writes_required=True` 被强置 `gates["concurrent_writes"]=False`；而 `src/runtime/health.py:14-24` 的 `REQUIRED` 强含该项 → `HealthAggregator` 恒 `not_ready` → `api/app.py:291-294` 的 `workflow_claim_readiness` 恒 False，worker 零领活。所有 `concurrent_writes_required=False` 的测试对此失明。
- **`HealthAggregator` TTL 死代码 + 持写锁冲击**：`src/runtime/health.py:26-44` `ttl_seconds` 赋值后永不读取，`ready()` 仅做 `inflight` 合并；`TursoPersistence.readiness()` 全程 `async with _write_lock` 执行 `verify_migrations` + 旁路 probe，空载 `GET /ready` 每 50ms 与 `claim_next` 同锁竞争。
- **空 CIDR 时私网 peer 仍信任 XFF**：`src/runtime/security.py:492-498` `elif peer and _is_private_peer(peer): return presented`，默认 `Settings.trusted_proxy_cidrs=""` 下私网反代场景攻击者 `X-Forwarded-For: 127.0.0.1` 即可通过 `is_internal_ip` 闸进入 `/internal`/`/metrics` 且按伪造 IP 分桶绕过限流。
- **PATCH 持久化面绕过 extras 校验**：`src/contracts/api/models.py:50-59` `TeamPatchRequest` 与 `362-377` `TaskPatchRequest` 仅 `require_change` 无 `assert_safe_public_data`，注入 `apiKey/secretKey/signedUrl` 可持久化（`TeamCreateRequest`/`TaskCreateRequest` 已校验，形成不一致）。
- **Body cap 仅查 `content-length`**：`api/app.py:527-538` 的 `reject_oversize_body` 无长度即放行，`Transfer-Encoding: chunked` 的 10k records 仍在 `422` 前全缓冲，可 OOM。
- **向量 upsert 误改在线行**：`src/runtime/intake/vector_publish_commit.py:381-385` 的 `SELECT … WHERE team_uuid=? AND namespace_uuid=? AND generation_artifact_uuid=? AND block_or_unit_id=? AND channel=? AND embedding_model=? AND deleted_at IS NULL` 不含 `index_generation` 与 `publication_state`，`src/runtime/intake/vectorize.py:203-213` 复用 `existing_uuid` 后 `_upsert_vector_record_tx:392-426` 对找到的行直接 `UPDATE … SET publication_state='withdrawn', index_generation=? …`，若该行已是 `indexed` 且 serving，被就地篡改后 S09 proof 集塌陷（见 R4 详述）。
- **检索重检与 GC 持写锁**：`src/services/retrieval/retrieval_rank.py:465` 的 `_sql_batch_eligibility` 与 `src/persistence/retrieval_access.py:136,194` 的 `filter_retrieval_eligible` 均以 `BEGIN IMMEDIATE` 事务做只读 fence，放大 Turso 单写者竞争并使 `BUSY` 抖动为 `503`。
- **其余 honesty 缺口**：`VF36` raw/clean 共享 `handle/size` 仍 `digest≠bytes`、`VF52` 同 `namespace_key=default` 维切换仍 `409` 不切新 namespace、`VF40.r` 无 `pending` 状态以 `deactivated` 代替、`VF85` 3 处 source-grep 仍是 test-gap、`migration 014` 对存量重复 live 对象的唯一索引创建失败不自愈，均在 closure 已标 `partial` 但仍是逻辑断点。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 对 18 个承重文件一手 Read 并给精确 `file:line`，对 6-Phase 每 commit 的 `--stat` 与关键 diff 逐项对照 |
| 本地命令 / 测试 | `yes` | `git log --oneline/graph`, `git show --stat`, `git diff 375c4fa..HEAD --stat`, `Read` 全量；抽样读 `tests/unit/test_ns5_*.py` 判定 falsifiable，未重跑 `tests/e2e`（`VF86` 已诚实 defer） |
| schema / contract 反向校验 | `yes` | 逆向核对 `001_initial.sql` 索引定义与 `014/015` 迁移、`contracts/lsrag/layered_content.py:79-118` 与 `*.v1.json`、`api/models.py` extras 校验、`retrieval_rank` 双 fence SQL |
| live / deploy / preview 证据 | `n/a` | 无 Dockerfile/Compose/真机 Turso `concurrent_writes=True` / 真机 CW+native_vector constitution e2e；`NS5-T60 mega` 已用 Turso port 主链而非 e2e |
| 与上游 design / QNA 对账 | `yes` | 对 `S03` claim/lease/fencing/outbox、`S09` proof、`S10` dual fence、`S12` Turso、`S15` readiness、`S16` egress/token/extras 逐项判定 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | `immediate_transaction` 的 `BEGIN` 在 `try` 外，取消可使单例连接永久 `in_transaction` | `critical` | `correctness` | `yes` | `fix`：将 `BEGIN` 纳入 `try` 并在 `BaseException` 时 `shield(rollback)` 后 `discard` |
| R2 | 默认 `concurrent_writes_required=True` 时 `/ready` 与 `claim_next` 永久 503 | `critical` | `correctness` | `yes` | `fix`：健康模型承认串行 UoW 为 ready，或默认 `concurrent_writes_required=False` 并文档化 |
| R3 | `HealthAggregator.ttl_seconds` 死代码 + `readiness()` 持写锁冲击 | `high` | `correctness` | `yes` | `fix`：实现 TTL 缓存或 `probe` 去写锁 |
| R4 | 向量 upsert 不以 `index_generation/publication_state` 限界，可就地篡改在线 `indexed` 行 | `critical` | `correctness` | `yes` | `fix`：`SELECT` 追加 `AND index_generation=? AND publication_state='withdrawn'`，或禁止 `UPDATE` 已 `indexed` 行 |
| R5 | 空 `trusted_proxy_cidrs` 时私网 peer 盲信 `X-Forwarded-For` 首段，接管内网闸与限流桶 | `high` | `security` | `yes` | `fix`：空 CIDR 时永不解析 XFF，仅 `peer in cidrs` 才取 `presented` |
| R6 | `TeamPatchRequest`/`TaskPatchRequest` 未校验 `payload_extra`，可持久化 secret/signed URL/绝对路径 | `high` | `security` | `yes` | `fix`：补 `model_validator → assert_safe_public_data` 并复用服务层二次防御 |
| R7 | `ContentLengthLimitMiddleware` 不限 `chunked`，大 body 在 `422` 前仍全缓冲可 OOM | `high` | `security` | `yes` | `fix`：ASGI `receive` 层流式计数超 `cap` 立即 `413` |
| R8 | `LocalVllmAdapter._shared_client` 超时固化：探活 5s 污染后继 `generate 180s` 必超时 | `medium` | `correctness` | `no` | `fix`：`_shared_client` 按 `timeout` 分桶或探活走独立短连接 |
| R9 | 检索 `S04/S09` 重检读 fence 持 `BEGIN IMMEDIATE` 写锁，放大 Turso 单写者竞争 | `high` | `correctness` | `no` | `fix`：新增 `read_transaction()` 或直连只读游标 |
| R10 | `ObjectGcService` `TX1→unlink→TX2` 窗口内新 `reference` 可致 `活目录项 + 已删字节` 的 TOCTOU | `high` | `correctness` | `no` | `defer-with-rational`：显式标 `VF66.r T-O-120`，下阶段落目录 CAS SSOT |
| R11 | `_namespace_coordinates` 单独只读事务预留 `index_generation+1`，并发 publish 可预同号 409 抖动 | `medium` | `correctness` | `no` | `fix`：同 UoW `UPDATE … RETURNING` 原子预留 |
| R12 | `TeamService.create` 并发同 `team_uuid` `INSERT` 未捕 `IntegrityError` 走 `500` 而非 `409` | `medium` | `correctness` | `no` | `fix`：`try IntegrityError → ConflictError(409)`（同 `task_create.py:130-141`） |
| R13 | `DenialAuditSampler.decide` 溢出时用 `overflow` 桶，`undo` 仍以 `hash(remote_ip)` 算 key，配额错桶 | `medium` | `correctness` | `no` | `fix`：`decide` 返回 `effective_key` 供 `undo` 回滚 |
| R14 | `request_ip` 空 CIDR 时限流桶按伪造 XFF 分桶，_is_private_peer 未递归 `ipv4_mapped` 导致 `::ffff:*` 行为分裂 | `medium` | `security` | `no` | `fix`：限流桶键去 XFF 或同步递归 `mapped` |
| R15 | `migration 014` 对存量重复 live 对象的 `UNIQUE … WHERE tombstoned_at IS NULL` 建索引失败不自愈 | `medium` | `delivery-gap` | `no` | `fix`：迁移前离线去重检测或降为非唯一索引 + 应用层 fence 已覆盖 |

### R1. `BEGIN` 在 `try` 外的取消撕裂

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/persistence/uow.py:26` `await asyncio.to_thread(connection.execute, begin_sql)` 位置在 `try:` 之前
  - `src/persistence/uow.py:32-45` 的 `except BaseException → shield(rollback) → discard` 仅覆盖 `yield` 后的 `commit` 段
  - Turso `busy_timeout=5000` 与 `WorkflowWorker._heartbeat_loop:151` 的 `sleep(interval)`、`WorkflowSupervisor` 的 50ms `idle_seconds` 放大该窗口
- **为什么重要**：
  - `asyncio.CancelledError` 是 `BaseException`，若恰在 `BEGIN IMMEDIATE` 的 `to_thread` 阻塞期间被取消，外层 `asyncio.wait_for`/`task.cancel` 直接跳出 `immediate_transaction` 上下文，`rollback` 永不执行，`discard()` 永不调，`self._connection` 仍指向 `in_transaction=True` 的句柄，下一次 `claim_next`/`publish` 的 `BEGIN IMMEDIATE` 恒抛 `cannot start a transaction within a transaction`，唯一写者永久瘫痪。
  - P1-01 修复了 body 取消，但遗漏了 entry 取消，形成「修了一半」的新 blocker。
- **审查判断**：
  - 本项是 NS5 后**新引入**的不可恢复 IO blocker，虽测试未暴露（无取消在 `BEGIN` 窗口的单测），但故障注入下必现。
- **建议修法**：
  - 将 `BEGIN` 纳入 `try`：`body_ok` 置 `False` 前先 `try: await to_thread(execute, begin_sql) except BaseException: try: shield(rollback) except: discard() ; raise`，或 `BEGIN` 失败即 `discard()`。补单测：`wait_for(claim_next, timeout=0.001)` 在 `BEGIN` 阻塞期间 cancel 后仍可 `BEGIN` 成功。

### R2. 默认画像永久 503

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/persistence/turso/port.py:171-177` `if not required: pass else: gates["concurrent_writes"]=False`（旁路探针真值被覆盖）
  - `src/runtime/health.py:14-24` `REQUIRED` 强含 `concurrent_writes`
  - `api/app.py:291-294` `readiness = health.ready().status=="ready"` 供 `WorkflowRuntime` 的 `claim_next` 前栅
  - `src/runtime/config.py:24` `concurrent_writes_required` 默认 `True`（生产/0815 默认）
- **为什么重要**：
  - P1-02 为规避 `pyturso` `BEGIN CONCURRENT` 的 `exit 134` 而将业务 UoW 固定为 `IMMEDIATE` 并诚实降级 `readiness.concurrent_writes=False`，但未同步健康模型：单写者仍是可用的 ready 语义被误判为 not_ready，导致开箱即 `ready=not_ready`，`claim_next` 被 `_assert_ready_for_claim` 挡死，worker 零领活。所有 `concurrent_writes_required=False` 的短途测试对此失明。
- **审查判断**：
  - 这是 NS5 的**逻辑冲突类 blocker**（诚实串行 vs 诚实就绪语义未对齐），不是存量 deferred。
- **建议修法**：
  - 二选一：**(A)** 健康模型承认串行即 ready：`TursoPersistence.readiness` 保留探针真值，新增 `write_serialization="immediate"`，`HealthAggregator.REQUIRED` 将 `concurrent_writes` 改为 `write_path_ready = cw or serialization=="immediate"`；**(B)** 将默认 `concurrent_writes_required` 改 `False` 并文档化「单写者即 ready，CW 仅为性能探针」。任选其一并补 `required=True + IMMEDIATE` 时断言 `ready` 的用例。

### R3. `HealthAggregator` 无 TTL 且持写锁

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/health.py:26-44` `self._ttl_seconds` 赋值后从未读取，`ready()` 仅做 `inflight` 合并，`_compute` 每次触 `probe`
  - `src/persistence/turso/port.py:146-164` `readiness()` 全程 `async with _write_lock` 执行 `verify_migrations` + 旁路 `probe_concurrent_writes/restore_journal_mode=False` 两次探针
- **为什么重要**：
  - 空载 `WorkflowSupervisor` 每 `idle_seconds=0.05` 触一次 `claim_next` 的 readiness  fence，外加外部 LB `/ready` 探活，高频探针在 `asyncio.Lock` 上与业务 `BEGIN IMMEDIATE` 串行排队，`BUSY` 时写路径被读探针间接限流 5s，P50 被放大为 `lease-heartbeat-fenced` 误判。
- **审查判断**：
  - P2-05 宣称「短 TTL + in-flight coalesce + 不切 journal_mode」仅实现后两者，TTL 缺失属 delivery-gap。
- **建议修法**：
  - 在 `HealthAggregator` 实现 `deadline = now + ttl` 缓存：`if cached and now < expires and inflight is None: return cached`；或将 `readiness()` 中 `probe` 移出 `_write_lock`（`verify_migrations` 改走只读连接）。

### R4. 向量 upsert 误改在线 `indexed` 行

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/vector_publish_commit.py:381-385` 查重 `SELECT … WHERE deleted_at IS NULL` 不含 `index_generation` 与 `publication_state`
  - `src/runtime/intake/vector_publish_commit.py:392-426` 对命中行直接 `UPDATE … SET publication_state='withdrawn', index_generation=? … WHERE team_uuid=? AND vector_record_uuid=?`，不校验旧 `publication_state`
  - `src/runtime/intake/vectorize.py:203-213` 在事务外以 `existing_uuid` 复用 `vector_record_uuid` 后于回调内沿用同一 `next_generation`
  - `src/persistence/migrations/015_vec_coord_generation.sql` 已将 `ux_vec_coord_active` 改为含 `index_generation`，但读路径未跟进
- **为什么重要**：
  - 同一 `(team, ns, artifact, block, channel, model)` 在不同 `index_generation` 本应是不同物理行（015 后），但查不含 `index_generation` 会把 `generation=5` 且 `publication_state='indexed'` 的在线行查出并就地 `UPDATE` 为 `withdrawn/6`，导致在线 S09 proof 的 `actual_count` 瞬间塌陷，`_fetch_candidate_rows` 的 `proof.actual_count=proof.matched_count` 栅栏次轮检索即 `PUBLICATION_PROOF_MISMATCH` 或静默丢数。`P4-10` 宣称 DONE 但该子项仍为 open。
- **审查判断**：
  - 这是 NS5 后仍 open 的**服务数据丢失 risk**，虽需特定重向量化并发才触发，但 `Vectorize` 的 `existing_uuid` 复用使 happy-path 即可命中（同一 artifact 重放）。
- **建议修法**：
  - 将 `SELECT` 追加 `AND index_generation=? AND publication_state='withdrawn'`（或至少 `!= 'indexed'`），未命中则 `INSERT`；命中 `indexed` 行直接抛 `VECTORIZE_COORDINATE_FENCE` 走重试并重新分配 `vector_record_uuid`。补回归：先 publish 一 generation 达 `indexed`，再对同一坐标重向量化断言在线行不变。

### R5. 空 CIDR 时私网 peer 盲信 XFF

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/security.py:492-498` `elif peer and _is_private_peer(peer): return presented`（空 `trusted_proxy_cidrs` 时）
  - `src/runtime/security.py:502-507` `_is_private_peer` 未递归 `ipv4_mapped`，`524-536` 的 `is_internal_ip` 已递归，形成行为分裂
  - `api/dependencies.py:162` `require_operator_token` 与 `api/app.py:518-525` 的 `require_metrics_access` 均以 `is_internal_ip(request_ip(...))` 为闸
- **为什么重要**：
  - 默认部署（`MKB_TRUSTED_PROXY_CIDRS=""`）下 K8s/容器网络 peer 恒为私网，攻击者 `X-Forwarded-For: 127.0.0.1, 8.8.8.8` 即可使 `request_ip()` 返回首段并通过内网闸，同时限流桶按伪造 IP 分桶绕过 `ip_limit`。
- **审查判断**：
  - P5-01 宣称 `trusted-proxy CIDR` 已 fail-closed，但空 CIDR 分支仍 fail-open，测试 `test_request_ip` 仅覆正向 CIDR 未覆空 CIDR + 私网。
- **建议修法**：
  - 空 `cidrs` 时永不解析 XFF（直接 `return peer`），仅 `peer in cidrs` 才取 `forwarded.split(",")[0]`；`_is_private_peer` 同步递归 `ipv4_mapped`。

### R6. PATCH 持久化面绕过 `payload_extra` 校验

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/contracts/api/models.py:50-59` `TeamPatchRequest.require_change` 与 `362-377` `TaskPatchRequest.require_mutation` 均未调用 `assert_safe_public_data`
  - 对照 `TeamCreateRequest:44-47` 与 `TaskCreateRequest:347-359` 的 `reject_secret_extras` 已校验
  - `src/contracts/common/models.py:128-144` `assert_safe_public_data` 本体已覆盖 `apiKey/secretkey` 下划线折叠与驼峰正则、`signed URL` 与绝对路径
- **为什么重要**：
  - 公共持久化的另一入口 `PATCH` 可写入 `{"apiKey":"sk-live","hook":"https://example.com?X-Amz-Signature=xxx","path":"/etc/shadow"}`，`GET` 已脱敏但 DB 行已落地，备份/日志泄露。
- **审查判断**：
  - P5-03 宣称 `extras 拒密` 的测试仅覆 Create，PATCH 面是额外存储沉淀的 bypass。
- **建议修法**：
  - 为 `TeamPatchRequest`/`TaskPatchRequest` 补 `model_validator(mode="after") → assert_safe_public_data(self.payload_extra)`，服务层二次防御；补 `PATCH` 的 `apiKey/camelCase/signedUrl/绝对路径` 四用例。

### R7. Body cap 可被 `chunked` 绕过

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `api/app.py:527-538` `reject_oversize_body` 仅 `if length: int(length)>cap → 413`，否则 `await call_next(request)`
  - `uvicorn` 默认接受 `Transfer-Encoding: chunked` 的无 `content-length` 请求
  - `src/contracts/api/models.py:139` `records: list[dict] = Field(max_length=10_000)` 在 `422` 前已全缓冲
- **为什么重要**：
  - VF84 根因即 `10k records + extras 在 422 前 OOM`，当前仅堵诚实 `content-length`，恶意 `chunked` 仍可把 body 全部缓冲至 Pydantic 校验前，leaf-worker 单进程被直接 OOM。
- **审查判断**：
  - P5-08 宣称 done，但对抗条件下仍 fail-open。
- **建议修法**：
  - 改为 ASGI `receive` 层包装：累计 `len(chunk)` 超 `cap` 立即 `413`，或在 `TrustedHost` 之前前置 `ContentLengthLimitMiddleware(BaseHTTPMiddleware)` 的流式分支。补 `chunked + 1_048_577 bytes` 单测。

### R8. vLLM 单例 client 超时固化

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/llm_adapters/local_vllm.py:206-215` `_shared_client(timeout)` 首创后永不更新 `timeout`
  - `src/llm_adapters/local_vllm.py:223-226` `probe` 以 `min(timeout_seconds,5)` 创 client，随后 `src/llm_adapters/local_vllm.py:242-245` 的 `embed/generate` 复用同一 `httpx.AsyncClient` 且 `_request` 的 `client.post` 未显式传 `timeout`
  - `src/runtime/config.py` `generate_timeout_seconds` 默认 `180`
- **为什么重要**：
  - 先 `GET /ready` 触探活即固化 5s，随后 `vectorize` 的 `generate 180s` 必 `INFERENCE_TRANSPORT_RETRYABLE`，三重试后变 `retryable_failure` 惊群。
- **审查判断**：
  - 非阻塞但稳定性问题，P3-03 宣称 done 时未覆 `probe → generate` 的超时污染路径。
- **建议修法**：
  - `_shared_client` 按 `timeout` 分桶或 `probe` 走独立 `httpx.AsyncClient(timeout=5)` 并 `aclose`；或 `_request` 层 `client.timeout = httpx.Timeout(timeout)`。

### R9. 检索读 fence 持写锁

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/persistence/retrieval_access.py:136,194` `filter_retrieval_eligible / load_retrieval_body` 均 `async with persistence.transaction()`
  - `src/services/retrieval/retrieval_rank.py:465` `_sql_batch_eligibility` 同为 `transaction()`
  - `src/persistence/turso/port.py:140-144` `transaction = immediate_transaction → BEGIN IMMEDIATE`
- **为什么重要**：
  - 只读的 `S04`  eligibility 与 `S09` 重检本可在 `READ` 事务完成，当前以 `IMMEDIATE` 串行化并与 `claim_next/vectorize/publish` 争锁，`busy_timeout 5000` 内表现为 `RETRIEVE_DEPENDENCY_ELIGIBILITY 503` 抖动，自 DoS 探针（R3）同锁放大。
- **审查判断**：
  - VF53 的 `N+1 → chunked + cache` 已缓解扇出，但事务类型未改，压力下升 blocker。
- **建议修法**：
  - 为 `PersistencePort` 新增 `read_transaction()`（`BEGIN`/`BEGIN READONLY`）或在 `retrieval_access` 内直连只读游标 `to_thread(connection.execute)` 不持 `_write_lock`。

### R10. GC 两阶段 `unlink` 的 TOCTOU

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/services/object_gc.py:188-272` `TX1 验证 blocker → unlink 在锁外 → TX2 复核后写 proof+tombstone`，`src/storage/local_store.py:126-133` `delete_if_unreferenced` 持 `local_store._write_lock` 但与 `persistence` 无原子性
  - `src/services/artifacts.py:131-149` 的 `promote` 与 GC 对同一 `stored_object_uuid` 的引用写入可交织
- **为什么重要**：
  - `GC-TX1` 通过 → 并发 `OutcomeArtifactCommitter.validate_and_commit` 为同一 `digest` 插入新活 `reference` → GC 线程 `unlink` 已不可逆 → `TX2` 复检抛 `409` 回滚 tombstone，但字节已丢，后续 `read_verified` 报 `OBJECT_MISSING` 而非`tombstoned`，需人工修复。
- **审查判断**：
  - P1-07 已把 `unlink` 移出写锁外是正确改进，但未引入目录 CAS 真 SSOT，故诚实标 `VF66.r T-O-120` defer 合理。
- **建议修法**：
  - 维持 current 行为但文档化运维收敛手顺；真修复需 `stored_object_uuid` 级 `UNIQUE` + `INSERT reference + UPDATE tombstone` 同一 CAS，或 `unlink → rename + TX2 成功后再 unlink`。

### R11. 世代预留不在同一 `UoW`

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/intake/vector_publish_commit.py:272-281` `_namespace_coordinates` 单独只读事务取 `index_generation+1`，后于 `vectorize.py:169` 与 `vector_publish_commit.py:136-167` 的 `publish` 回调内才 CAS 指针 `active < excluded` 与 `MAX(index_generation, ?)`
  - `src/runtime/intake/vectorize.py:286-330` 的 `callback` 才 `INSERT` 向量行并以 `next_generation` 落库
- **为什么重要**：
  - 两并发 `vectorize` 可预同号，重试时 `BUSY` 已使预留值过时，后者 `publish` 的 `pointer CAS` 失败 `PUBLICATION_POINTER_FENCE 409` 抖动，虽不会回拨指针，但已落库的 `vector_records` 世代号与指针不一致需 `retirement` 额外回收。
- **审查判断**：
  - `VF44/VF58` 指针单调已靠 `active < excluded` 封死回拨，剩余为分配可观测性瑕疵，`medium`。
- **建议修法**：
  - 将 `_namespace_coordinates` 改为 `UPDATE mkb_vector_namespaces SET index_generation=index_generation+1 RETURNING` 原子预留，或 `vectorize` 行先 `index_generation=NULL` 待 `publish` 回填。

### R12. `TeamService.create` 并发 PK 走 `500`

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/services/teams.py:35-61` `SELECT → INSERT` 无 `except IntegrityError`
  - 对比 `src/runtime/task/task_create.py:130-141` 已 `changes()==0 + try IntegrityError → ConflictError(409/replay)`
- **为什么重要**：
  - 双上游/双 Pod 同时 `PUT /teams/{uuid}` 可致 `UNIQUE constraint failed` 冒泡为 `500`，重试风暴放大且破坏幂等 `409 identity-conflict` 合同。
- **审查判断**：
  - 与 `task_create` 不一致，属遗漏项。
- **建议修法**：
  - 复用 `task_create._is_unique_conflict`，`INSERT` 包 `except IntegrityError → raise ConflictError("TEAM_IDENTITY_CONFLICT", 409)` 或 `INSERT OR IGNORE + 回查`。

### R13. 审计采样器 `undo` 错桶

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/security.py:259-264` `decide` 溢出时 `key=(category,"overflow",bucket)` 覆盖原 key
  - `api/dependencies.py:96-101` `undo` 仍以 `hash(remote_ip)` 为 `source_identity` 重算 key，与 `overflow` 桶不一致
- **为什么重要**：
  - 洪水下写失败的 `overflow` 配额永不回收，下一分钟合法 `invalid_token` 仍 `DROP`，首个溢出样本的配额泄漏。
- **审查判断**：
  - P5-07 已 `decide 预占 + 写成功才 commit`，该溢出桶 `undo` 错位是边缘遗漏。
- **建议修法**：
  - `decide` 返回 `(disposition, effective_key)` 元组，`undo` 用回传 `effective_key`。

### R14. 限流桶可伪造与 `ipv4_mapped` 分裂

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/security.py:185-213` 限流键 `hash_remote_address(remote_ip)` 取自 `request_ip` 首段，空 CIDR 时首段为伪造 XFF
  - `src/runtime/security.py:502-507` `_is_private_peer` 未递归 `ipv4_mapped`，`345-350/536-537` 的 `_restricted/is_internal_ip` 已递归
- **为什么重要**：
  - 攻击者 `X-Forwarded-For: 1.1.1.{1..N}` 轮询可使单 `ip_limit=120` 形同虚设（桶分裂）；`::ffff:10.0.0.1` 在 `request_ip` 误判非私网→不信任 XFF（可用性误拒），而 egress 侧正确拦截审计分裂。
- **审查判断**：
  - 与 R5 同根的限流/审计可观测性瑕疵。
- **建议修法**：
  - 空 CIDR 时限流键用 `peer` 而非 `presented`；`_is_private_peer` 增加 `mapped` 递归。

### R15. `014` 对存量脏库不幂等

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/persistence/migrations/014_ns5_uuid_and_tombstone.sql:17-20` `CREATE UNIQUE INDEX … WHERE tombstoned_at IS NULL`，`src/persistence/migration_runner.py:121-145` 仅按 ledger `checksum` 跳过
  - 若旧库已有两 live 同 `(team, digest, size)`，建索引直接 `UNIQUE constraint failed` → `apply_migrations` 整体 `rollback` → `readiness.schema_migration=False` 永久
- **为什么重要**：
  - NS5 后旧部署升级路径可因存量脏数据永久 `not_ready`，可重入性承诺不成立。
- **审查判断**：
  - 应用层 `GC` 后已 `duplicate_catalog` fence 已覆盖，但 DDL 强约束仍是硬闸。
- **建议修法**：
  - 迁移前 `SELECT … GROUP BY … HAVING COUNT>1` 检测到则 `RAISE ABORT('duplicate live object')` 指引离线去重，或改 `UNIQUE` 为普通 `INDEX` 将唯一性交由 `GC` 后台收敛。

---

## 3. In-Scope 逐项对齐审核

> 结论：`done | partial | missing | stale | out-of-scope-by-design`。以 `docs/plan/new-start/NS5-0820-bug-fixes.md` §3/§4 的 62 项为权威，映射到 VF-ledger `75 [true-bug] + 12 [partial-delivery] = 87` in-scope。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| P1-01 | UoW cancel/commit 不污染唯一连接 (VF1) | `partial` | body 取消已 done（`test_ns5_uow_cancel.py`），但 `BEGIN` 窗口取消撕裂致永久 `in_transaction`（R1） |
| P1-02 | Turso 写路径诚实 + sidecar 串行 (VF2/VF3) | `partial` | sidecar 串行 done 极优，但默认画像 `concurrent_writes` 强制 `False` 致 `REQUIRED` 永久 503（R2）与 `readiness` 持写锁（R3） |
| P1-03 | CLI timeout kill/wait + stdout 有界 (VF9) | `done` | `claude_cli.py:329-405` 的 `terminate→wait2s→kill` 与 `8MiB` 上限已钉死 `test_cli_timeout_kills_child` |
| P1-04 | heartbeat + 有界 worker (VF10) / 重叠 run_once (VF62) | `done` | heartbeat Done；重叠执行仍 `allow_overlapping_run_once=False` 属显式 defer，符合硬规则 |
| P1-05 | outbox 毒丸隔离 (VF61) | `done` | `attempts+1` 提交后 `json.loads`，非法行新事务 `dead` + 事件/metric，`drain_once` 同 tick 可领下一条 |
| P1-06 | retirement 失效 intent 收口 (VF63) | `done` | `_close_unavailable_intent_tx` 对 `null/deactivated/deleted` 已收口，`test_ns5_retirement_stuck.py` 100 阻塞 case |
| P1-07 | GC 两阶段 + released_at + tombstone 查找 (VF64/65/66/67) | `partial` | `TX1→unlink(锁外)→TX2` 已优于旧持锁 unlink，但 `活引用+已删字节` 的 TOCTOU 仍在（R10），`T-O-120` 诚实 defer |
| P1-08 | `_pending` pop (VF68) | `done` | `finally pop` + `discard` 双保险，`test_pending_map_empty_after_success_and_discard` |
| P1-09 | scanner 异常不退出 (VF69) | `done` | `object_gc.py:42-50` / `index_retirement.py:40-46` 的 `except Exception + metric + backoff` 且 lifespan 不重启误判已消 |
| P1-10 | claim 排空过期项 (VF70) | `done` | `runtime_core.py:353-368` `for _ in 64: fail_one_expired → continue`，一次可领活 |
| P2-01 | 归一化 pyturso rowcount (VF4) | `done` | `TursoUnitOfWork.execute: changes()` 回退，`test_turso_stale_update_rowcount_is_zero` |
| P2-02 | ledger 参数化 + 014 UUID 改写 (VF5/VF7) | `partial` | 参数化与 32hex 改写 done，但存量脏库 `014` 唯一索引可失败（R15） |
| P2-03 | 时间戳统一 us (VF8) | `done` | `time.py` `%f` ↔ us 切面已对齐 |
| P2-04 | retry jitter + 取消 gate noop + outbox.dead 事件 (VF71/72/73) | `done` | `runtime_outcome.py:146-149` `random.uniform(0, cap)` + `runtime_gates.py:225` cancelling noop + `mkb_outbox_dead_total` |
| P2-05 | /ready 短 TTL + claim 不切 journal_mode (VF94) | `partial` | 不切 `journal_mode` 已靠旁路，但 TTL 缓存未实现且持写锁（R3） |
| P2-06 | bootstrap/retention 失败可观测 (VF98) | `done` | `lifespan:422-431` `bootstrap_failures++` 且 `HealthAggregator` 融合 |
| P2-07 | Task 指纹 / extras 清空 / PK 409 (VF99/102/103) | `partial` | Task 指纹已去 `created_at` 且 409 已分流，但 `Team.create` 并发 PK 仍 `500`（R12） |
| P2-08 | Process/Outbox 错误脱敏 (VF100) | `done` | `redact()[:512]` + `_safe_persisted_error` 已覆盖 |
| P2-09 | object/schema readiness 真校验 (VF101) | `done` | `local_store.readiness` JSON 校验 + `verify_migrations` 含 `mkb_tasks` |
| P3-01 | salvage/pool/OVER_BUDGET SSOT (VF11/12/13) | `done` | `OVER_BUDGET_PROCESS_KEYS` 含 `transcribe/construct`，`_can_salvage` 优先级已正 |
| P3-02 | prompt 缺 state fail-closed (VF14) | `done` | `generation_construct.py:375-388` `state is None → PROMPT_NOT_REGISTERED` |
| P3-03 | vLLM 单例 + 放 lease 再 sleep + 408/425 (VF15/22/24) | `partial` | 单例与放 lease 已 done，但探活 5s 污染 `generate 180s`（R8） |
| P3-04 | CLI stdin-only + env allowlist (VF16) | `partial` | `prompt_transport=stdin + argv 不放 prompt + MKB_* 过滤` done，但 env 仍非白名单允 `AWS_*`（R6 衍生，medium） |
| P3-05 | 证据绑 process_uuid (VF17) | `done` | `generation_evidence.py` 已按 `process_uuid` Key，同 UoW flush |
| P3-06 | schema SHA 冻结 + 精确 probe (VF18) | `done` | L4 `schemas+layered_sha256` 与 `json_schema` 严格校核，`probe` 仅 `2xx`+精确模型 |
| P3-07 | EXHAUSTED 可 process-retry (VF19) | `done` | `_RECOVERABLE_ERROR_CODES` 含 `EXHAUSTED/BACKPRESSURE` |
| P3-08 | CLI ConcurrencyGate (VF21) | `done` | 三处 `try_acquire("cli")` + stub/mixed 分流 |
| P3-09 | 非 text media 拒绝 (VF26) | `done` | `media_type prefix text/` 拒绝 `CLEAN_MEDIA_UNSUPPORTED` |
| P3-10 | Facade 与 DispatchCaps 同源 (VF96) | `done` | 单例 `DispatchCaps + ConcurrencyGate` 注入两路 |
| P4-01 | vectorize 超预算 fail-closed (VF27) | `done` | `VECTORIZE_BUDGET_CONTENT_FULL 422` 且 `handoff required==succeeded==len(vector_inputs)` |
| P4-02 | HTML 保留换行 (VF28/VF31) | `done` | `_HORIZONTAL_SPACE` 仅坍水平空格，`DetectorHtmlTextExtractor` 保留 `\n` |
| P4-03 | 单调 anchor cursor (VF29) | `done` | `find(body, search_from[granularity])` 单调 |
| P4-04 | PDF 去 latin-1 回退 (VF30) | `done` | 无 latin-1 垃圾；`VF30.r` 完整库属 O4 defer |
| P4-05 | acquisition 预算 + Source/Item resolve + artifact 字节一致 (VF34/35/36) | `partial` | 预算与 `Source` 复用 done，**VF36 raw/clean 仍共享 handle/size 但 digest 不同** 显式 partial（R4 相关） |
| P4-06 | stub 双通道可区分 (VF37) | `done` | `_stub_summary_body` 恒 `summary:{digest}:…` ≠ original；`VF37.r` 生产切 stub 属 O4 |
| P4-07 | JSON 栈匹配 + markdown transport + 两节点树诚实 (VF38/39/41) | `done` | `JSONDecoder.raw_decode` 栈匹配 + `artifact.transport` 抄 receipt，`VF41.r` 全树 O4 |
| P4-08 | human_review 前不 active (VF40) | `partial` | `deactivated` 代替 `pending` 使检索不泄漏，但 `CHECK` 无 `pending` 的生命周期断点仍在 `VF40.r` |
| P4-09 | vectorize 保留原错误码 + body-only embed (VF42/43) | `done` | `SPACE_VIOLATION` 原样上抛不包 `VECTORIZE_INFERENCE_FAILED`，`_embed_bodies` 去 header |
| P4-10 | generation 单调 CAS + 015 (VF44/55/58) | `partial` | 指针 `active < excluded` 与 `015` 已加，但 upsert 仍可改写 `indexed` 行（R4）且 `_namespace_coordinates` 非原子（R11） |
| P4-11 | envelope 只留 receipts (VF45) | `done` | `intake/core.py:373-387` 后期 envelope 仅 receipts/handle/digest |
| P4-12 | layered validator 补 UUID/array/date-time/URI (VF46) | `done` | `VF46.r` 全程 jsonschema O4 |
| P4-13 | 召回截断 fail-closed + Layer A 校验 (VF47/51/52) | `partial` | `LIMIT+1` 与 `LIVE mismatch 409` done，**VF52 同 `default` 维切换仍 `409` 不切新 namespace** partial |
| P4-14 | dedup/inflate/pack/hydration (VF48/49/53/56) | `done` | `(-ann_score, priority)` 分数优先、`inflate` 剥 `channel`、`hydration_cache`、root 去重 |
| P4-15 | Team inactive 不可检索 (VF50) | `done` | `require_active` + `teams.status='active'` SQL fence |
| P4-16 | 禁止单通道 purge 破 Proof (VF54) | `done` | `channel_filter != 'all' → 422` |
| P4-17 | upserted UUID + rebuild 跳过非 serving (VF59/60) | `done` | `dual_channel_artifact_uuid` 事件 + rebuild 跳 `serving_revision IS NULL` |
| P4-18 | title 进入 content_full (VF95) | `done` | `adopt.py:61-65` `title:` 前缀进入 `content_full` |
| P5-01 | trusted-proxy CIDR (VF75) | `partial` | 显式 CIDR 走 `ip_in_cidrs` 已 fail-closed，但空 CIDR 私网 peer 仍盲信 XFF（R5） |
| P5-02 | 限流 overflow 桶而非全局 fail-open (VF76) | `partial` | `overflow` 分桶已隔离，但 `undo` 错桶使配额泄漏（R13）与 XFF 分桶可伪造（R14） |
| P5-03 | extras 拒 secret/camelCase/signed URL (VF78) | `partial` | Create 已拒，但 PATCH 绕过（R6）与 `_REDACT_KEY` 值脱敏分裂 |
| P5-04 | sqlite 后门双因子 (VF80) | `done` | `PYTEST_CURRENT_TEST && "pytest" in sys.modules`（较旧单因子强，但 `sys.modules` 可伪造，risk 保留 medium） |
| P5-05 | Starlette ≥1.0.1 + TrustedHost (VF81) | `done` | `pyproject.toml:15` `>=1.0.1` + `uv.lock 1.6.0` + `TrustedHostMiddleware` |
| P5-06 | IPv6-mapped 递归受限 (VF82) | `partial` | egress `_restricted` 已递归，但 `request_ip._is_private_peer` 未（R5/R14） |
| P5-07 | audit sampler 写成功才提交 (VF83) | `partial` | `decide/undo` 已落地，但 overflow 桶错位（R13） |
| P5-08 | 入站 body cap middleware (VF84) | `partial` | `content-length` 分支 done，`chunked` 可绕过（R7） |
| P6-01 | 拆除 tautology 簇 (VF85) | `partial` | `or True` 已删，多处 source-grep 仍是 test-gap（显式 partial） |
| P6-02 | ruff 9 errors 清零 (VF87) | `done` | `f7bec3f` `ruff check → 0` |
| P6-03 | CW unit 诚实 (VF91) | `done` | `concurrent_writes is True else skip`，`VF91.r` 真机 e2e 属 O4 |
| P6-04 | wheel 含 migrations/*.sql (VF93) | `done` | `setuptools.package-data` 含 `001..015 + *.json`，`migrate` 可重入 |
| P6-05 | mega/soak/docs (VF86/VF89/VF90) | `partial` | Turso port 主链 `test_ns5_turso_mainchain` 已替代 `sqlite3.connect` 主链，但 `T60 mega` 与 `全量 pytest 441` 仍被 `VF86 NS1-V11` 挡住，`AP executing` 未收口 |

### 3.1 对齐结论

- **done**: `43`
- **partial**: `19` （其中 5 为 closure 已显式标 `VF36/52/62/40.r/85` 的 honesty partial，14 为本轮新判的半修/逻辑冲突）
- **missing**: `0` （无 true-bug 被静默改写为 deferred）
- **stale**: `0`
- **out-of-scope-by-design**: `9 [true-deferred]` + `6 O4` 余片（`VF30.r/37.r/41.r/46.r/66.r/91.r`）按 AP `§2.2 O3/O4` 诚实 defer，已落 `deferred-items-ledger.md`

> 用一句话总结：`这更像“不可恢复 IO 与 proof 栅栏已合拢、检索不再说谎、毒丸与租约已持有；但默认画像就绪语义、向量在线行不可变、安全边界可绕过与 body 有界仍未收口”的 70% 完成态，而非 completed。`

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | `VF23 billing always-permit`, `VF88 live GPU`, `VF89 grep-test 范式`, `VF90 coverage/config`, `VF97 browser/OCR/Vision` | `遵守` | AP `§2.2 O3` 明确 `true-deferred`，closure `§4` 与 `deferred-items-ledger` 已登记承接，本轮未误判为 blocker |
| O2 | `VF74 claim_token/fencing_token`, `VF77 HTML XSS href/src`, `VF79 /docs 无鉴权`, `VF86 sqlite3-on-Turso e2e`, `V11 harness` | `遵守` | `VF74` 多副本 token 本轮不要求，`VF77` 非主线 XSS（仅 `href/src` 协议未限），`VF79` `FastAPI(docs_url=None)` 未做属合规债但按 AP 为 `O3` deferred，`VF86` 已用 Turso port 主链替身 |
| O3 | `VF30.r 完整 PDF 库`, `VF37.r 生产切 stub`, `VF41.r S06 全树`, `VF46.r 全程 jsonschema`, `VF66.r 目录 CAS SSOT (T-O-120)`, `VF91.r 真机 CW+native_vector e2e` | `遵守` | 6 O4 余片属 `partial-delivery` 剩余切片，closure `§4` 已标 `C` 并链到后继 charter，本稿不将其升为本轮 blocker |
| O4 | `VF6 executescript 回退`, `VF92 检索双栅栏 tautology` | `遵守` | `stale-rejected`，当前 `migration_runner.py` 的 `executable` 多语句 C 已兼容 `pyturso`，`92` 的 `proof.actual_count` 已严格 |
| O5 | `VF20 SupplyFence 宽` / `VF25 httpx 异常` / `VF32 短文本粒度` / `VF33 C 逐字` / `VF57 eligibility 镜像` | `遵守` | 5 项为 `acknowledge/valid-by-design`，本轮未改合同，审查未误报 |
| O6 | `R1 BEGIN 取消窗口` 本轮新发现 | `误报风险` | 需判定为**新 blocker 而非 out-of-scope**：P1-01 半修引入的可用性回退，应纳入下轮必修而非 defer |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`主体修复成立但 0820-review 不能收口。`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1 — UoW `BEGIN` 取消窗口** (`src/persistence/uow.py:26`)：将 `BEGIN` 纳入 `try/BaseException` 的 `shield(rollback)+discard`，补 `wait_for(... BEGIN busy) → cancel` 后仍可 `BEGIN` 的 falsifiable 用例。
  2. **R2 — 默认 Turso 画像永久 503** (`turso/port.py:171-177 + health.py:14-24`)：对齐 `concurrent_writes` 就绪语义（承认串行即 ready）或改默认 `concurrent_writes_required=False`，并以 `required=True + IMMEDIATE` 断言 `ready`。
  3. **R4 — 向量 upsert 误改在线行** (`vector_publish_commit.py:381-426` / `vectorize.py:203-213`)：查重追加 `AND index_generation=? AND publication_state='withdrawn'`，禁止就地篡改 `indexed` 行；补 `publish indexed 后重向量化在线行不变` 的集成用例。
  4. **R5 — 空 CIDR 盲信 XFF 接管内网闸** (`security.py:492-498`)：空 `trusted_proxy_cidrs` 时永不取 XFF，仅 `peer in cidrs` 才取 `forwarded.split(",")[0]`。
  5. **R6 — PATCH 绕过 `payload_extra` 校验** (`contracts/api/models.py:50-59,362-377`)：为两 `*PatchRequest` 补 `assert_safe_public_data`，覆盖 `apiKey/camelCase/signedUrl/绝对路径`。
  6. **R7 — Body cap `chunked` 绕过** (`api/app.py:527-538`)：ASGI `receive` 流式计数超 `max_request_bytes` 立即 `413`。
- **可以后续跟进的 non-blocking follow-up**：
  1. **R3 — Health TTL 与去写锁** (`health.py:26-44` / `turso/port.py:146-164`)：实现 `ttl_seconds` 缓存 + 探针移出 `_write_lock`，降低自 DoS。
  2. **R8 — vLLM 超时固化** (`local_vllm.py:206-246`)：探活/推理分 client 或按 `timeout` 分桶。
  3. **R9 — 检索读持写锁** (`retrieval_access.py:136,194` / `retrieval_rank.py:465`)：新增 `read_transaction()` 供只读 fence。
  4. **R10 — GC TOCTOU** (`object_gc.py:188-272`) 与 `R15 — 014 脏库自愈`：文档化运维手顺，后继落 `T-O-120` 目录 CAS。
  5. **R11 — 世代预留原子化** (`vector_publish_commit.py:272-281`)：`UPDATE … RETURNING` 原子分配。
  6. **R12/R13/R14 — 团队并发 409 / 审计错桶 / 限流桶伪造**：分别为 `<20 行` 补丁，顺带修复。
  7. **其余 honesty partial** (`VF36` 双制品 digest、`VF52` 维切新 namespace、`VF40.r` pending、`VF85` source-grep) 与 `O4` 6 余片按既有 ledger 承接。
- **建议的二次审查方式**：`same reviewer rereview`（聚焦 R1/R2/R4/R5/R6/R7 六项必修的增量 diff + 新增 falsifiable 单测 + Turso `concurrent_writes_required=True` 画像的 `/ready` 与 `claim_next` 可领活冒烟）
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
