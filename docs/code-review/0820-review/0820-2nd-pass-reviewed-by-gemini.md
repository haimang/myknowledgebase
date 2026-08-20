# Nano-Agent 代码审查报告 (0820-review 第 2 轮)

> 审查对象: `MKB 全仓 HEAD @ 0820 2nd-pass review (commit 8cb2cb4 after NS5 fixes)`
> 审查类型: `rereview`
> 审查时间: `2026-08-20`
> 审查人: `Gemini (2nd-pass independent review)`
> 审查范围:
> - `src/` 全仓 (`persistence`, `runtime`, `services`, `storage`, `contracts`, `llm_adapters`)
> - `api/` 全仓 (`app.py`, `dependencies.py`, `internal/`, `public/`)
> - `intake/` 全仓
> - `tests/` 全仓
> - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`
> - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md`
> 对照真相:
> - `README.md`
> - `docs/baseline/domain-truth/` (D01–D08, S01–S16)
> - `docs/plan/new-start/NS5-0820-bug-fixes.md`
> - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 本轮审查针对第一轮 0820-review 修复（提交 `d728d0b` 至 `8cb2cb4`）后的全量代码展开独立、进攻性、对抗性的深度静态审查。虽然第一轮修复在 Sidecar 串行化隔离、迁移 DDL 参数化、CAS rowcount 归一化、双写 Proof 完整性及检索 Context Packing 根去重等大部分已知问题上取得了实质性进展，但本轮审查在并发取消安全、生产默认配置契约、大模型客户端超时、向量多世代在线隔离、反向代理安全边界及垃圾回收时序等核心承重链路上发现了多处严重的**盲点、断点、逻辑冲突与数据丢失风险**。

- **整体判断**：第一轮修复工作完成了大量表面契约对齐，但在深层并发取消保护、默认配置自洽性、在线多世代隔离与安全信任边界上存在严重的逻辑冲突与盲区，当前系统在生产默认配置下无法正常提供服务，存在数据静默损坏与安全绕过隐患，**严禁标记为 completed 或收口**。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 3 个判断**：
  1. **【P0 致命阻塞 / 事务死锁瘫痪】** `src/persistence/uow.py:26` 中 `BEGIN IMMEDIATE` 置于 `try...except BaseException:` 外部，协程取消导致底层单例连接永久滞留在活跃事务中，后续所有写操作因 `cannot start a transaction within a transaction` 永久失败。
  2. **【P0 致命阻塞 / 开箱 503 与 Worker 领活死锁】** `Settings.concurrent_writes_required` 默认值为 `True`，但在 `TursoPersistence.readiness()` 中将 `gates["concurrent_writes"]` 强制写死为 `False`。由于 `HealthAggregator.REQUIRED` 强校验该项，导致默认生产配置下 `/ready` 恒定返回 503，Worker 领活栅栏永久关闭。
  3. **【P0 致命阻塞 / 在线服务向量被篡改】** `vector_publish_commit.py` 中 `_existing_vector_coordinate_uuid` 与 `_upsert_vector_record_tx` 的 SELECT 查询漏传 `AND index_generation=?`，导致新世代重建/重新向量化时查出旧世代正在 Serving 的线上向量并将其就地 UPDATE 篡改为 `withdrawn`，引发线上检索实时数据丢失。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md`（第 1 轮 103 项统一台账）
  - `docs/plan/new-start/NS5-0820-bug-fixes.md`（NS5 执行计划）
  - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`（第一轮修复收口报告）
  - `docs/baseline/domain-truth/` S01–S16 领域真相
- **核查实现**：
  - `src/persistence/` (`uow.py`, `turso/port.py`, `turso/sidecar.py`, `engine.py`, `factory.py`, `migration_runner.py`, `retrieval_access.py`)
  - `src/runtime/workflow/` (`worker.py`, `runtime_core.py`, `runtime_outbox.py`, `runtime_outcome.py`, `runtime_gates.py`, `workflow_supervisor.py`)
  - `src/runtime/security.py`, `api/dependencies.py`, `api/app.py`
  - `src/runtime/intake/` (`vectorize.py`, `vector_publish_commit.py`, `acceptance_snapshot.py`, `acquisition_ingest.py`)
  - `src/services/` (`object_gc.py`, `index_retirement.py`, `teams.py`, `artifacts.py`, `retrieval/`)
  - `src/llm_adapters/local_vllm.py`, `src/runtime/inference/claude_cli.py`, `src/runtime/inference/facade.py`
- **执行过的验证**：
  - `git log -n 15 --stat`（审查自 `375c4fa` 到 `8cb2cb4` 的全部 11 次提交）
  - `uv run pytest tests/unit tests/domain tests/integration -q`（实测 441 项用例全部 PASS，验证了已有断言集合在局部 Mock 约束下的通过性）
  - 启动 3 路专用 Reviewer 子代理，就【并发与 Durable 状态机】、【接口合规与安全边界】、【Turso 存储与可观测性】展开进攻性静态代码审计。
- **复用 / 对照的既有审查**：
  - 对照 `VF-ledger-0820-1st-review.md` 与 `NS5-0820-bug-fixes-closure.md`，逐项独立复核第一轮声称已修复项，拒绝盲信测试绿灯，专注于测试断言未覆盖的边缘竞态、未暴露的配置默认值冲突及取消时序安全。

### 1.1 已确认的正面事实

- **Sidecar 串行化与原生崩溃防御**：`TursoDiagnosticSidecar` 已改用单一物理连接并加 `threading.Lock()` 互斥，写操作固定为 `BEGIN IMMEDIATE`，彻底消除了多线程并发调用 `pyturso` 触发的底层 native panic (exit 134)。
- **迁移账本参数化执行**：`migration_runner.py` 中记录已执行迁移的 INSERT 语句已全部改为安全参数化执行，彻底根除了字符串插值 SQL 注入隐患；`014` 与 `015` 迁移脚本语法兼容且具备幂等性。
- **驱动层 CAS 行数归一化**：`TursoUnitOfWork` 统一包装了 `cursor.rowcount`，在驱动返回负值时回退使用 `connection.changes()`，保证了基于 `rowcount == 1` 的 CAS 判定准确。
- **Publication Proof 严格 Fail-Closed**：向量化超预算（>16,000 chars）直接抛出 `VECTORIZE_BUDGET_CONTENT_FULL` (422)；`VectorizeHandoffV1` 强制要求 `required_units == succeeded_units == len(vector_inputs)`，杜绝了静默缩小向量集签署假 Proof 的行为。
- **单通道 Purge 保护**：`src/services/vector_purge.py` 严格禁止了 `channel_filter != 'all'`，防止局部单通道删除破坏双通道 Proof 一致性。
- **检索 Context Packing Root 去重**：`RetrievalPackMixin._pack` 使用集合记录已挂载的 `generation_artifact_uuid`，同代多个 Hit 仅挂载一次文档 Root，消除了上下文窗口膨胀。
- **Task 创建幂等指纹**：`_creation_fingerprint` 正确剥离了 `audit.created_at` 与 `audit.reviewed_at` 等动态字段，主键冲突正确捕获并返回 409 或幂等回放视图。

### 1.2 已确认的负面事实

- **`immediate_transaction` 存在致命取消漏洞**：`await asyncio.to_thread(connection.execute, begin_sql)` 位于 `try:` 外部。协程在开启事务等待期间收到 `asyncio.CancelledError` 会直接跳出上下文管理器，跳过 rollback 且不调用 `discard()`，导致单例连接永久滞留在活跃事务中，后续所有写事务完全报废（见 R1）。
- **默认生产配置与健康检查逻辑冲突导致开箱 503**：`Settings.concurrent_writes_required` 默认值为 `True`，但在 `TursoPersistence.readiness()` 中将 `concurrent_writes` 强置为 `False`。`HealthAggregator` 判定其未 ready，导致默认启动后 `/ready` 恒为 503，Worker 领活栅栏永久关闭（见 R2）。
- **LocalVllmAdapter 单例 Client 导致 180s 生成被强制降至 5s 超时**：探活初始化 `_client` 默认超时为 5s，后续 `generate` 请求调用 `client.post` 未显式传递 `timeout` 参数，使大模型长文本生成在 5s 后必发超时失败（见 R3）。
- **向量记录 Upsert 遗漏 `index_generation` 导致在线 Serving 向量被篡改**：`vector_publish_commit.py` 中查重查询未包含 `index_generation`，新世代重新向量化直接将旧世代在线 Serving 向量更新为 `withdrawn`，引发线上检索实时数据丢失（见 R4）。
- **反向代理信任穿透与 XFF 伪造漏洞**：`security.py` 在空 CIDR 白名单下对私网 peer 盲信 XFF，攻击者伪造 XFF 即可突破 `/internal` 与 `/metrics` 网络限制并绕过 IP 限流（见 R5）。
- **Team / Task PATCH 接口遗漏脱敏校验**：PATCH 模型未调用 `assert_safe_public_data`，且正则未覆盖 `_REDACT_KEY` 全集，允许注入敏感密钥持久化并泄漏（见 R6）。
- **IndexGenerationRetirement 队头阻塞**：`_close_unavailable_intent_tx` 漏判命名空间停用与 Item 缺失 serving revision 等场景，导致到期 Intent 永久处于 `open` 状态阻塞回收队列（见 R7）。
- **Object GC 两阶段物理 Unlink 存在 TOCTOU 竞态**：物理删除在事务外执行，与并发同 digest 写入交织时会导致物理文件被误删，造成数据丢失（见 R8）。
- **死信 Prometheus 指标静默丢弃**：`WorkflowRuntime` 从未绑定 `metrics` 实例，导致 Outbox 进入 dead 状态时 `mkb_outbox_dead_total` 上报静默失败（见 R9）。
- **Worker 外部取消导致 Handler 协程孤立泄漏**：`worker.py` 在取消时未取消/等待 `handler_task`，导致后台无主执行且内存 `_pending` 残留（见 R10）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 逐行静态分析 `src/`, `api/`, `tests/` 最新代码 |
| 本地命令 / 测试 | `yes` | 运行 `pytest` 全量测试套件（441 passed）并分析测试断言覆盖边界 |
| schema / contract 反向校验 | `yes` | 对账 `001`–`015` 迁移 DDL 与 Python 实体模型及 SQL 查询条件 |
| live / deploy / preview 证据 | `n/a` | 纯本地环境与代码静态分析 |
| 与上游 design / QNA 对账 | `yes` | 对账 S01–S16 规范、VF-ledger 103 条台账及 NS5-0820-bug-fixes-closure |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | `immediate_transaction` 取消安全漏洞导致单例连接永久死锁 | `critical` | correctness / platform-fitness | `yes` | fix |
| R2 | 默认生产配置与健康检查逻辑冲突导致 `/ready` 恒为 503 且 Worker 无法领活 | `critical` | correctness / platform-fitness | `yes` | fix |
| R3 | `LocalVllmAdapter` 探活固化 5s 超时导致大模型生成普遍失败 | `critical` | correctness / delivery-gap | `yes` | fix |
| R4 | `vector_publish_commit.py` 查重漏传 `index_generation` 篡改在线 Serving 向量 | `critical` | correctness | `yes` | fix |
| R5 | 默认空 CIDR 白名单下私网 peer 盲信 XFF 导致内网安全栅栏与限流被穿透 | `high` | security | `yes` | fix |
| R6 | `TeamPatchRequest` 与 `TaskPatchRequest` 遗漏脱敏校验导致密钥持久化泄露 | `high` | security | `yes` | fix |
| R7 | `IndexGenerationRetirement` 漏判不可用场景引发回收队头阻塞 | `high` | correctness | `yes` | fix |
| R8 | `ObjectGC` 两阶段物理 Unlink 存在 TOCTOU 竞态导致文件丢失 | `high` | correctness / platform-fitness | `yes` | fix |
| R9 | `WorkflowRuntime` 丢失 `metrics` 实例导致死信指标静默丢弃 | `high` | platform-fitness | `yes` | fix |
| R10 | `WorkflowWorker` 取消时遗漏 `handler_task` 取消与 `_pending` 清理 | `high` | correctness / platform-fitness | `yes` | fix |
| R11 | `_fail_process_tx` 状态更新 SQL 缺少 `fencing_generation` CAS 检查 | `medium` | correctness | `no` | fix |
| R12 | `reject_oversize_body` 中间件仅看 Content-Length 允许 Chunked 绕过引致 OOM | `medium` | security | `no` | fix |
| R13 | `HealthAggregator` 的 `ttl_seconds` 未实现时间戳缓存导致主库写锁高频争用 | `medium` | platform-fitness | `no` | fix |
| R14 | `ArtifactRetrievalAccess` 检索水合缓存未被上层服务激活 | `medium` | platform-fitness | `no` | fix |
| R15 | `TeamService.create` 并发主键冲突未捕获导致 HTTP 500 | `medium` | correctness | `no` | fix |
| R16 | `ClaudeCli` 在协程取消时 `_terminate_process` 未 shield 引致僵尸进程 | `low` | platform-fitness | `no` | fix |

---

### R1. `immediate_transaction` 取消安全漏洞导致单例连接永久死锁

- **严重级别**：`critical`
- **类型**：`correctness | platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/persistence/uow.py:26-46`](file:///root/workspace/myknowledgebase/src/persistence/uow.py#L26-L46)
    ```python
    26:     await asyncio.to_thread(connection.execute, begin_sql)
    27:     body_ok = False
    28:     try:
    29:         yield
    30:         body_ok = True
    31:         await asyncio.to_thread(connection.commit)
    32:     except BaseException:
    ...
    ```
- **为什么重要**：
  在异步 ASGI 架构中，客户端断开、请求超时或 Task Cancel 会随时向正在等待 `to_thread(connection.execute, begin_sql)` 的协程抛出 `asyncio.CancelledError`。由于第 26 行在 `try:` 外部，异常发生时 `rollback()` 未执行，`discard()` 未被调用，底层 Turso/SQLite C 驱动已处于未提交事务状态。下一个请求复用该连接执行 `BEGIN IMMEDIATE` 必抛 `cannot start a transaction within a transaction`，且同样在 `try` 外部抛出再次跳过 `discard()`，导致单例物理连接永久停在未结事务中，彻底瘫痪进程的所有写操作。
- **审查判断**：这是极高危险的取消安全性漏洞，违背了第一轮 P1-01 / VF1 的收口目标。
- **建议修法**：
  将 `begin_sql` 的执行移入 `try...except BaseException:` 块内部：
  ```python
  @asynccontextmanager
  async def immediate_transaction(
      connection: Any,
      *,
      discard: Callable[[], None],
      begin_sql: str = "BEGIN IMMEDIATE",
  ) -> AsyncIterator[None]:
      body_ok = False
      try:
          await asyncio.to_thread(connection.execute, begin_sql)
          try:
              yield
              body_ok = True
              await asyncio.to_thread(connection.commit)
          except BaseException:
              rolled_back = False
              try:
                  await asyncio.shield(asyncio.to_thread(connection.rollback))
                  rolled_back = True
              except Exception:
                  discard()
              else:
                  if body_ok or not rolled_back:
                      discard()
              raise
      except BaseException:
          discard()
          raise
  ```

---

### R2. 默认生产配置与健康检查逻辑冲突导致 `/ready` 恒为 503 且 Worker 无法领活

- **严重级别**：`critical`
- **类型**：`correctness | platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/runtime/config.py:24`](file:///root/workspace/myknowledgebase/src/runtime/config.py#L24): `concurrent_writes_required: bool = True`
  - [`src/persistence/turso/port.py:174-177`](file:///root/workspace/myknowledgebase/src/persistence/turso/port.py#L174-L177):
    ```python
    if not self.concurrent_writes_required:
        pass
    else:
        gates = {**gates, "concurrent_writes": False}
    ```
  - [`src/runtime/health.py:14-24, 50-61`](file:///root/workspace/myknowledgebase/src/runtime/health.py#L14-L24): `HealthAggregator.REQUIRED` 包含 `"concurrent_writes"`。
- **为什么重要**：
  在开箱默认配置下（`MKB_PERSISTENCE_BACKEND=turso`），`Settings.concurrent_writes_required` 为 `True`。`TursoPersistence.readiness()` 主动将 `gates["concurrent_writes"]` 强制置为 `False`。`HealthAggregator` 判定必选组件未 OK，`/ready` 接口永远返回 503 `status="not_ready"`。同时 `api/app.py:291-294` 中的 Worker 领活探活 `workflow_claim_readiness()` 永远为 `False`，导致工作流 Worker 在生产默认配置下完全拒绝工作！
- **审查判断**：这是第一轮 P1-02（诚实不谎报 CONCURRENT）与 P2-09（Readiness 校验）在配置默认值上的严重架构断裂。单写架构使用 `BEGIN IMMEDIATE` 是正确设计，但默认配置与健康检查断言未自洽闭合。
- **建议修法**：
  将 `src/runtime/config.py` 中的 `concurrent_writes_required: bool = False`（或在 `TursoPersistence.readiness` 与 `HealthAggregator` 中校准，当使用 Turso 串行 UoW 时不将多写并发作为健康检查阻断项）。

---

### R3. `LocalVllmAdapter` 探活固化 5s 超时导致大模型生成普遍失败

- **严重级别**：`critical`
- **类型**：`correctness | delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/llm_adapters/local_vllm.py:206-215`](file:///root/workspace/myknowledgebase/src/llm_adapters/local_vllm.py#L206-L215):
    ```python
    def _shared_client(self, *, timeout: float) -> httpx.AsyncClient:
        client = self._client
        if client is None:
            client = httpx.AsyncClient(timeout=timeout, ...)
            self._client = client
        return client
    ```
  - [`src/llm_adapters/local_vllm.py:225`](file:///root/workspace/myknowledgebase/src/llm_adapters/local_vllm.py#L225): `probe()` 调用 `_shared_client(timeout=min(self.timeout_seconds, 5))` 初始化了 `self._client`。
  - [`src/llm_adapters/local_vllm.py:244-245`](file:///root/workspace/myknowledgebase/src/llm_adapters/local_vllm.py#L244-L245):
    ```python
    client = self._shared_client(timeout=self.timeout_seconds if timeout is None else timeout)
    response = await client.post(f"{self.base_url}{path}", json=payload, headers=self._headers())
    ```
- **为什么重要**：
  在 `httpx` 中，如果复用已实例化的 `client`，单次请求的超时必须在 `client.post(..., timeout=...)` 中显式指定，否则继承 client 默认超时。应用在 `/ready` 或启动时调用 `probe()`，使 `self._client` 默认超时被固定为 5 秒。随后的 `generate()`（业务期望 180 秒）虽然向 `_shared_client` 传了 180，但未重建 client，且 `client.post` 漏传了 `timeout` 参数！所有实际大模型生成请求均在 5 秒后被 `httpx` 强制超时中断，导致生成任务无法完成。
- **审查判断**：第一轮 P3-03 引入单例 `AsyncClient` 时遗留的严重调用参数遗漏。
- **建议修法**：
  在 `_request` 中调用 `client.post` 时显式传入 `timeout=timeout`：
  ```python
  response = await client.post(
      f"{self.base_url}{path}",
      json=payload,
      headers=self._headers(),
      timeout=self.timeout_seconds if timeout is None else timeout,
  )
  ```

---

### R4. `vector_publish_commit.py` 查重漏传 `index_generation` 篡改在线 Serving 向量

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/runtime/intake/vector_publish_commit.py:346-350`](file:///root/workspace/myknowledgebase/src/runtime/intake/vector_publish_commit.py#L346-L350), [`src/runtime/intake/vector_publish_commit.py:381-386`](file:///root/workspace/myknowledgebase/src/runtime/intake/vector_publish_commit.py#L381-L386)
  - `_existing_vector_coordinate_uuid` 与 `_upsert_vector_record_tx` 的 SELECT 查询：
    ```sql
    SELECT vector_record_uuid FROM mkb_vector_records WHERE team_uuid=? AND namespace_uuid=?
    AND generation_artifact_uuid=? AND block_or_unit_id=? AND channel=? AND embedding_model=?
    AND deleted_at IS NULL
    ```
- **为什么重要**：
  `015_vec_coord_generation.sql` 将唯一索引调整为包含 `index_generation`，允许新旧世代向量共存。但 Python 层的查重 SELECT 语句漏掉了 `AND index_generation=?`。当同一个 Artifact 进行二次索引或 Rebuild（生成新世代 $G_2$）时，查出了旧世代 $G_1$ 正在 Serving 的向量记录，并直接执行 UPDATE 将其状态改写为 `publication_state='withdrawn'`，同时将 `index_generation` 篡改为 $G_2$！这导致旧世代正在对外服务的向量被立即破坏（线上检索搜不到），发生严重的数据不可见与服务中断。
- **审查判断**：第一轮 P4-10 引入 015 迁移后，未在 Python 查询层同步补齐世代约束，造成迁移与应用逻辑脱节。
- **建议修法**：
  在 `_existing_vector_coordinate_uuid` 与 `_upsert_vector_record_tx` 的 SQL 查询中增加 `AND index_generation=?`。

---

### R5. 默认空 CIDR 白名单下私网 peer 盲信 XFF 导致内网安全栅栏与限流被穿透

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/runtime/security.py:495-498`](file:///root/workspace/myknowledgebase/src/runtime/security.py#L495-L498):
    ```python
    elif peer and _is_private_peer(peer):
        # Empty CIDR: a private ASGI peer is treated as an untrusted
        # reverse proxy, so the forwarded client is the identity.
        return presented
    ```
- **为什么重要**：
  在 Kubernetes、Docker 或常规 Nginx 代理后，ASGI `peer` 均为私网地址（如 `10.x`, `172.17.x` 或 `127.0.0.1`）。当 `trusted_proxy_cidrs` 为空时，上述代码依然信任外部传入的 `X-Forwarded-For`。外部攻击者发送请求附带 `X-Forwarded-For: 127.0.0.1`，`request_ip` 返回 `"127.0.0.1"`，在 `require_operator_token` 与 `require_metrics_access` 中通过 `is_internal_ip` 判定，从而突破内网 IP 栅栏。同时，攻击者可通过轮换伪造 XFF IP 彻底击穿 IP 限流。
- **审查判断**：严重违背 VF75 安全基准（默认必须 Fail-Closed，未配置 CIDR 时严禁信任 XFF）。
- **建议修法**：
  删除 `elif peer and _is_private_peer(peer): return presented` 分支。仅在 `cidrs` 明确配置且 `peer` 匹配时才解析 XFF。

---

### R6. `TeamPatchRequest` 与 `TaskPatchRequest` 遗漏脱敏校验导致密钥持久化泄露

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/contracts/api/models.py:50-60, 362-377`](file:///root/workspace/myknowledgebase/src/contracts/api/models.py#L50-L60), [`src/services/teams.py:80-112`](file:///root/workspace/myknowledgebase/src/services/teams.py#L80-L112)
- **为什么重要**：
  `TeamCreateRequest` 和 `TaskCreateRequest` 配置了 `assert_safe_public_data` 校验，但 `TeamPatchRequest` 与 `TaskPatchRequest` 遗漏了该校验。调用方可通过 `PATCH /v1/teams/{team_uuid}` 传入 `{"payload_extra": {"apiKey": "sk-secret", "token": "xxx"}}`，绕过创建时的安全门将密钥存入数据库。而在 `GET` 接口中，`payload_extra` 会被原样返回，造成持久化凭证泄露。此外，`models.py` 的 `_SECRET_KEY_PATTERN` 缺少 `cookie`, `credential`, `dsn`, `passphrase` 等关键字，与 `security.py` 的 `_REDACT_KEY` 脱节。
- **审查判断**：第一轮 P5-03（VF78）遗留的 PATCH 路径脱敏漏洞。
- **建议修法**：
  在 `TeamPatchRequest` 与 `TaskPatchRequest` 增加 `@model_validator(mode="after")` 执行 `assert_safe_public_data`，并将 `_SECRET_KEY_PATTERN` 统一替换为 `_REDACT_KEY`。

---

### R7. `IndexGenerationRetirement` 漏判不可用场景引发回收队头阻塞

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/services/index_retirement.py:320-328, 507-551, 561-573`](file:///root/workspace/myknowledgebase/src/services/index_retirement.py#L320-L328)
- **为什么重要**：
  `collect_due` 按 `ORDER BY eligible_at LIMIT 100` 拉取待清理 Intent。当关联 Namespace 停用、Item 处于 active 但 `serving_revision_uuid IS NULL`、或 Pointer 状态非 active 时，`_close_unavailable_intent_tx` 未能将其收敛为 `abandoned`，返回 `POINTER_UNAVAILABLE`，但数据库中 Intent 保持 `open` 且 `eligible_at <= now`。下次扫描时这批 Intent 依然排在最前。一旦堆积达到 100 条，扫描器将永远只拉取这批无法处理的行，导致整个系统的旧世代向量回收发生永久性队头阻塞。
- **审查判断**：第一轮 P1-06（VF63）未完全覆盖的边界断点。
- **建议修法**：
  在 `_close_unavailable_intent_tx` 中将 Namespace 停用及 Item 无 serving revision 的场景一并标记为 `abandoned` 并关闭 Intent。

---

### R8. `ObjectGC` 两阶段物理 Unlink 存在 TOCTOU 竞态导致文件丢失

- **严重级别**：`high`
- **类型**：`correctness | platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/services/object_gc.py:196-272`](file:///root/workspace/myknowledgebase/src/services/object_gc.py#L196-L272)
- **为什么重要**：
  GC 过程分为：TX1（检查无引用）-> 事务外物理 `unlink` -> TX2（复核并 tombstone）。若在 TX1 结束后，业务并发上传了相同 digest 并挂载了新引用，随后 GC 执行物理 `unlink` 将刚写入的文件删除。TX2 虽因发现新引用而抛出 409 回滚，但磁盘上的物理文件已被不可逆删除！后续业务读取该对象必报 `OBJECT_MISSING` (404)，引发静默数据丢失。
- **审查判断**：第一轮 P1-07（VF64–67）两阶段 GC 移出写锁后产生的并发 TOCTOU 时序漏洞。
- **建议修法**：
  在 TX1 中引入 `pending_delete` 锁标记，阻止并发请求在物理删除前挂载引用；若物理删除后发现冲突，自动补全重新刷盘。

---

### R9. `WorkflowRuntime` 丢失 `metrics` 实例导致死信指标静默丢弃

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/runtime/workflow/runtime_outbox.py:371-377`](file:///root/workspace/myknowledgebase/src/runtime/workflow/runtime_outbox.py#L371-L377): `metrics = getattr(self, "metrics", None)`
  - [`src/runtime/workflow/runtime_core.py:48-85`](file:///root/workspace/myknowledgebase/src/runtime/workflow/runtime_core.py#L48-L85), [`api/app.py:296`](file:///root/workspace/myknowledgebase/api/app.py#L296)
- **为什么重要**：
  `WorkflowCoreMixin` 初始化参数中未定义 `metrics`，`api/app.py` 构造 `WorkflowRuntime` 时也未传入 `metrics`。`getattr(self, "metrics", None)` 恒为 `None`。当 Outbox 重试耗尽（8 次）或数据损坏进入 `dead` 状态时，Prometheus 指标 `mkb_outbox_dead_total` 永远无法上报，导致线上死信监控静默失灵。
- **审查判断**：第一轮 P2-04（VF73）死信可观测性落地的代码级断点。
- **建议修法**：
  在 `WorkflowCoreMixin.__init__` 中增加 `metrics: MetricRegistry | None = None`，并在 `api/app.py:296` 构造时传入 `metrics=metrics`。

---

### R10. `WorkflowWorker` 取消时遗漏 `handler_task` 取消与 `_pending` 清理

- **严重级别**：`high`
- **类型**：`correctness | platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - [`src/runtime/workflow/worker.py:66-138`](file:///root/workspace/myknowledgebase/src/runtime/workflow/worker.py#L66-L138), [`src/services/artifacts.py:50-84`](file:///root/workspace/myknowledgebase/src/services/artifacts.py#L50-L84)
- **为什么重要**：
  `run_once` 在被外部 Task 取消时，`finally:` 块仅取消了 `heartbeat_task`，遗漏了 `handler_task`，导致 Handler 协程在后台成为孤儿任务继续运行。同时，若取消发生在 `accept_outcome` 执行前，未调用 `_discard_pending`，导致 `OutcomeArtifactCommitter._pending` 残留。累积 1024 次后打满上限，引发 `OBJECT_PENDING_OUTPUT_LIMIT` 拒绝服务。
- **审查判断**：第一轮 P1-04 与 P1-08 修复中的异常分支遗漏。
- **建议修法**：
  在 `worker.py` 的 `finally:` 块中补齐 `if not handler_task.done(): handler_task.cancel()` 以及无条件调用 `self._discard_pending(claim.command)`。

---

### R11. `_fail_process_tx` 状态更新 SQL 缺少 `fencing_generation` CAS 检查

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - [`src/runtime/workflow/runtime_outcome.py:454-470`](file:///root/workspace/myknowledgebase/src/runtime/workflow/runtime_outcome.py#L454-L470)
- **为什么重要**：
  `_fail_process_tx` 的 `WHERE` 条件仅有 `status NOT IN ('succeeded','failed','cancelled')`，缺少 `AND fencing_generation=?`。若租约恢复（`recover_expired_leases`）判定失败时，任务已被其他 Worker 续约进入新世代，该操作会将正在运行的新世代 Process 错误标记为 `failed`。
- **建议修法**：
  在 `_fail_process_tx` 的 UPDATE 语句中强制增加 `AND fencing_generation=?` 判定。

---

### R12. `reject_oversize_body` 中间件仅看 Content-Length 允许 Chunked 绕过引致 OOM

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：
  - [`api/app.py:527-539`](file:///root/workspace/myknowledgebase/api/app.py#L527-L539)
- **为什么重要**：
  中间件仅检查 `request.headers.get("content-length")`。使用 `Transfer-Encoding: chunked` 发送超大请求体时，中间件直接放行，FastAPI 在 Pydantic 反序列化时将全部数据读入内存，可被利用引发 OOM 拒绝服务。
- **建议修法**：
  在 ASGI 层面包装 `receive` 事件流，累加 chunk 字节数，一旦超过 `max_request_bytes` 立即中断并返回 413。

---

### R13. `HealthAggregator` 的 `ttl_seconds` 未实现时间戳缓存导致主库写锁高频争用

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - [`src/runtime/health.py:26-45`](file:///root/workspace/myknowledgebase/src/runtime/health.py#L26-L45)
- **为什么重要**：
  `ready()` 仅进行了并发 In-flight 折叠，未基于时间戳缓存评估结果。外部高频探活或 Worker 轮询每次均执行全量物理建连、PRAGMA 校验与表扫描，造成不必要的写锁竞争。
- **建议修法**：
  增加 `_last_result` 与 `_last_evaluated_at`，在 `ttl_seconds` 窗口内直接返回缓存字典。

---

### R14. `ArtifactRetrievalAccess` 检索水合缓存未被上层服务激活

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - [`src/persistence/retrieval_access.py:45-120`](file:///root/workspace/myknowledgebase/src/persistence/retrieval_access.py#L45-L120)
- **为什么重要**：
  虽然实现了 `_HYDRATION_CACHE`，但 `RetrievalService` 及检索 API 路由在处理查询时从未调用 `begin_request_cache()`，导致水合缓存默认始终为 `None`，每个 Hit 均重复执行磁盘读取和 JSON 解析。
- **建议修法**：
  在 `RetrievalService.retrieve()` 入口使用 `with begin_hydration_cache():` 激活请求级缓存。

---

### R15. `TeamService.create` 并发主键冲突未捕获导致 HTTP 500

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - [`src/services/teams.py:35-62`](file:///root/workspace/myknowledgebase/src/services/teams.py#L35-L62)
- **为什么重要**：
  并发相同 Team 创建请求穿透 `existing` 检查后同时发起 INSERT，后提交者抛出数据库 `IntegrityError`，未被捕获重试直接向上传播为 HTTP 500 异常。
- **建议修法**：
  参考 `task_create.py` 捕获唯一冲突并重新比对指纹，一致则返回已存在视图，不一致则返回 409。

---

### R16. `ClaudeCli` 在协程取消时 `_terminate_process` 未 shield 引致僵尸进程

- **严重级别**：`low`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - [`src/runtime/inference/claude_cli.py:382-406`](file:///root/workspace/myknowledgebase/src/runtime/inference/claude_cli.py#L382-L406)
- **为什么重要**：
  协程取消时，`_terminate_process` 中的 `wait_for(process.wait(), timeout=2.0)` 会再次抛出 `CancelledError`，跳过随后的 `kill()` 与 `wait()`，导致子进程未被父进程回收。
- **建议修法**：
  在取消处理路径中使用 `await asyncio.shield(_terminate_process(process))`。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | P1-01 UoW cancel/rollback 安全 | `partial` | 捕获了 BaseException，但 `execute(begin_sql)` 在 try 外部，存在致命取消死锁（见 R1） |
| S2 | P1-02 Turso 串行化与 Sidecar 安全 | `done` | Sidecar 锁互斥 + BEGIN IMMEDIATE 落地，无 exit 134 崩溃 |
| S3 | P1-03 CLI timeout kill/wait | `done` | 增加了 terminate/kill 流程，部分取消时序需 shield（见 R16） |
| S4 | P1-04 Worker Heartbeat 机制 | `partial` | 心跳循环正常，但外部取消未回收 handler 且 _fail_process 漏 CAS（见 R10, R11） |
| S5 | P1-05 Outbox 毒丸隔离与跳过 | `done` | 非法 JSON 独立标 dead，Supervisor 单 tick 跳过正常 |
| S6 | P1-06 Retirement 失效 Intent 收敛 | `partial` | 漏判 namespace 停用与空 serving revision，存在队头阻塞（见 R7） |
| S7 | P1-07 GC 两阶段与 Tombstone 索引 | `partial` | 014 索引生效，但事务外 unlink 存在 TOCTOU 物理文件误删风险（见 R8） |
| S8 | P1-08 `_pending` 映射清理 | `partial` | 成功/失败正常清理，但在特定取消分支下仍有内存泄漏（见 R10） |
| S9 | P2-01 Turso rowcount 归一化 | `done` | `_RowcountCursor` 统一回退 `changes()`，CAS 判定准确 |
| S10 | P2-02 迁移 Ledger 参数化与 014 UUID 改写 | `done` | 014 迁移正确修复 32-hex UUID，ledger INSERT 已参数化 |
| S11 | P2-03 微秒时间戳一致性 | `done` | `time.py` 与 SQL 统一 timespec 精度 |
| S12 | P2-04 Outbox.dead 事件与指标上报 | `partial` | 领域事件写入正常，但缺少 metrics 注入导致指标丢弃（见 R9） |
| S13 | P2-05 /ready 探针与模式隔离 | `partial` | 旁路连接隔离有效，但默认配置下 503 且 ttl 未生效（见 R2, R13） |
| S14 | P2-07 Task 幂等指纹与 PK 冲突 | `done` | Task 幂等剥离时间戳并返回 409，Team 并发需补齐（见 R15） |
| S15 | P3-03 vLLM 单例 Client 与重试退避 | `partial` | 实现了单例与 lease 释放，但漏传 timeout 导致请求全部 5s 超时（见 R3） |
| S16 | P3-04 CLI stdin-only 与环境变量白名单 | `done` | 正文走 stdin，环境变量去除了 MKB_* 变量 |
| S17 | P3-06 Schema freeze 与 2xx 探针 | `done` | snapshot 冻结 schema SHA，探针严格检查 2xx 与 model_key |
| S18 | P4-01 Vectorize 超预算 Fail-closed | `done` | 超 16k 抛 422，Proof 签署严格要求 100% 完整覆盖 |
| S19 | P4-02 HTML 换行保留 | `done` | 修复了空格替换，保留了段落排版 |
| S20 | P4-10 世代单调 CAS 与 015 联合索引 | `partial` | 015 迁移落地，但 Python 查重查询漏传 generation 破坏在线数据（见 R4） |
| S21 | P4-14 检索 dedup 分数优先与 Root 去重 | `done` | `-ann_score` 优先，Root 去重生效，水合缓存需上层激活（见 R14） |
| S22 | P4-16 单通道 Purge 禁止 | `done` | 严格校验 `channel_filter == 'all'`，防止破坏 Proof |
| S23 | P5-01 Trusted-proxy CIDR 边界 | `partial` | 空 CIDR 时私网 peer 仍盲信 XFF 导致安全穿透（见 R5） |
| S24 | P5-03 Extras 驼峰与 Presigned URL 拒密 | `partial` | Create 路径拦截正常，但 PATCH 路径完全漏验（见 R6） |
| S25 | P5-04 SQLite 双因子后门防护 | `done` | 要求 `PYTEST_CURRENT_TEST` + 真实 pytest 导入，防御牢固 |
| S26 | P5-08 入站 Body 大小限制 | `partial` | 检查了 Content-Length，但未防范 Chunked 传输 OOM（见 R12） |
| S27 | P6-04 Wheel 包含迁移 SQL 文件 | `done` | `package-data` 正确包含 `migrations/*.sql` |

### 3.1 对齐结论

- **done**: `17`
- **partial**: `10`
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `0`

> 总结：当前代码处于**“核心设计框架已建立，但高危并发竞态、取消时序盲点与默认配置冲突仍未收口”**的状态，不能视作通过审查。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | VF86 sqlite3 打开 Turso e2e 测试 | `遵守` | 本轮未伪造该路径断言，通过 `test_ns5_turso_mainchain.py` 经由 Turso port 检查主链 |
| O2 | VF23 Billing 真实扣费 | `遵守` | 保持 `DefaultBillingService.has_quota` 恒真合同，未擅自扩充范围 |
| O3 | VF97 browser/OCR/Vision 实际接线 | `遵守` | 保持未接线并明确披露，未引入伪造依赖 |
| O4 | VF88 Live GPU 真实调用 | `遵守` | 保持基于 mock/stub 的可证伪静态测试 |
| O5 | 目录 CAS SSOT (T-O-120) | `遵守` | 数据库继续作为唯一 CAS SSOT，未越界修改存储层架构 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`本轮实现存在 4 个 Critical 致命阻塞与 6 个 High 高危漏洞，不满足收口标准，严禁关闭本轮 review。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **[Fix R1]** 重构 `src/persistence/uow.py`，将 `await connection.execute(begin_sql)` 移入 `try...except BaseException:` 保护中，取消时强制 `discard()`。
  2. **[Fix R2]** 调整 `src/runtime/config.py` 中的 `concurrent_writes_required` 默认值为 `False`（或校准 `TursoPersistence.readiness` 与 `HealthAggregator` 的判定逻辑），确保默认启动下 `/ready` 为 200 且 Worker 正常领活。
  3. **[Fix R3]** 修复 `src/llm_adapters/local_vllm.py:245`，在 `client.post` 中显式传递 `timeout=timeout`，消除 5s 强制超时。
  4. **[Fix R4]** 修复 `src/runtime/intake/vector_publish_commit.py` 中的 `_existing_vector_coordinate_uuid` 与 `_upsert_vector_record_tx`，在 SQL 查询中增加 `AND index_generation=?`，防止在线 Serving 向量被篡改。
  5. **[Fix R5]** 修复 `src/runtime/security.py:495-498`，移除空 CIDR 下对私网 peer 自动信任 XFF 的逻辑。
  6. **[Fix R6]** 修复 `src/contracts/api/models.py`，为 `TeamPatchRequest` 与 `TaskPatchRequest` 增加 `assert_safe_public_data` 校验，并统一 `_SECRET_KEY_PATTERN` 正则。
  7. **[Fix R7]** 修复 `src/services/index_retirement.py`，将停用 Namespace 及空 serving revision 的 Intent 标记为 `abandoned`，消除回收队头阻塞。
  8. **[Fix R8]** 修复 `src/services/object_gc.py`，消除物理 Unlink 后的 TOCTOU 数据丢失竞态。
  9. **[Fix R9]** 为 `WorkflowRuntime` / `WorkflowCoreMixin` 注入 `metrics` 实例，修复死信指标丢弃。
  10. **[Fix R10]** 修复 `src/runtime/workflow/worker.py`，在 `finally:` 块中完整取消 `handler_task` 并调用 `_discard_pending`。
- **可以后续跟进的 non-blocking follow-up**：
  1. **[Followup R11]** 为 `_fail_process_tx` 增加 `AND fencing_generation=?` 保护。
  2. **[Followup R12]** 为 `reject_oversize_body` 中间件增加流式 chunk 累加计数拦截。
  3. **[Followup R13]** 为 `HealthAggregator` 增加真实基于时间戳的 TTL 结果缓存。
  4. **[Followup R14]** 在 `RetrievalService` 入口显式启用 `begin_hydration_cache()`。
  5. **[Followup R15]** 在 `TeamService.create` 中捕获并发主键冲突并转为 409。
  6. **[Followup R16]** 使用 `asyncio.shield` 保护 `ClaudeCli._terminate_process`。
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者针对上述 blocker 进行代码修复并再次提请审查。
