# Nano-Agent 代码审查模板

> 审查对象: `MKB / HEAD 全仓（Leaf-Worker + LS-RAG + Turso + Inference Adapter + tests）`
> 审查类型: `code-review`
> 审查时间: `2026-08-20`
> 审查人: `Grok`
> 审查范围:
> - `README.md`（架构、数据流、已知 K1–K14）
> - `api/`（composition root、鉴权、公共/内部路由）
> - `src/llm_adapters/`、`src/runtime/inference/`
> - `src/persistence/`（Turso 主路径、sqlite 测试路径、migration）
> - `src/runtime/intake/`、`src/services/lsrag_*`、`src/workflows/`
> - `src/services/retrieval/`、`src/persistence/retrieval_access.py`
> - `src/runtime/workflow*`（claim/lease/outbox/supervisor）
> - `tests/unit`、`tests/domain`、`tests/integration`、`tests/e2e`
> 对照真相:
> - `README.md`（2026-08-20 @ `5e64a1e`）
> - `.adocs/code-review.md`
> - `docs/closure/new-start/deferred-items-ledger.md`
> - `docs/baseline/domain-truth/S11-inference-runtime.md`（对照 adapter/fence 声称）
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 该实现主体骨架成立，但当前不应标记为 completed，也不应把 `433 passed` 读成行为已被证明。生产路径上存在会停掉唯一 supervisor 的 outbox 毒丸、live 向量化静默丢层、以及一批**删掉被测函数也会绿**的测试。

- **整体判断**：合同、工作流、双栅栏检索 SQL、CAS 对象与 prompt 冻结的主骨架可读且多数 fail-closed；但 Turso 能力探针与真实写路径脱节，LLM 池会计与真实运输脱节，默认 stub 把“双通道”做成原文回声，测试层存在系统性假绿。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. 一条非法 `mkb_outbox` 行会在 `claim_outbox` 里把 `attempts+1` 连同 claim 一起回滚，supervisor 的 `drain_once` 在 outbox 循环抛错后**不会**再 claim Process、也不会 `repair_once`。这是单进程叶节点的存活级缺陷。
  2. live vectorize 把超过 16k 的非 g0-summary 单元从 required set 里删掉，再用缩小后的集合写 publication proof；检索和 e2e 仍会报 `ok`。这是检索完整性的假成功。
  3. `433 passed` 含有无法失败的测试（ReadPort 不调用服务、sidecar soak 不断言行、`or True`、串行“并发”、缺 jsonl 直接 return）。全量 8 个红是 harness/超时，不是“其余 433 条都证明了生产行为”。

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。

- **对照文档**：
  - `README.md`（对照 HEAD `5e64a1e` 的能力表、数据流、K1–K14）
  - `.adocs/code-review.md`
  - `docs/closure/new-start/deferred-items-ledger.md`（`NS1-V11`、`NS2-O1`/`O2`、已知 e2e 名）
  - `docs/baseline/domain-truth/S11-inference-runtime.md`（开头约束；未把全文当已实现证明）
- **核查实现**：
  - `api/app.py`、`api/dependencies.py`、`api/public/routes.py`
  - `src/llm_adapters/base.py`、`src/llm_adapters/local_vllm.py`
  - `src/runtime/inference/facade.py`、`claude_cli.py`、`generation_live.py`
  - `src/persistence/turso/port.py`、`sidecar.py`、`engine.py`、`factory.py`、`sqlite_port.py`、`migration_runner.py`
  - `src/runtime/workflow/dispatch.py`、`runtime_core.py`、`runtime_outbox.py`、`worker.py`、`workflow_supervisor.py`
  - `src/runtime/intake/generation_construct.py`、`vectorize.py`、`vector_publish_commit.py`、`clean_preflight.py`
  - `src/services/retrieval/retrieval_request.py`、`retrieval_rank.py`、`src/persistence/retrieval_access.py`
  - `src/services/lsrag_compiler/adopt.py`、`validate.py`、`src/services/billing.py`、`src/services/prompt_profiles.py`
  - 优先测试：`tests/unit/test_turso_driver.py`、`test_ns4_*`、`test_dispatch_*`、`tests/integration/test_ns4_cw_soak.py`、`tests/e2e/test_generation_pipeline_contracts.py`、`test_index_rebuild.py`、`test_single_intake_pipeline.py`
- **执行过的验证**：
  - 本轮**没有**复跑全量 `pytest`；433/8 数字采信 README 对 `5e64a1e` 的陈述，并与 deferred ledger 中的 5 个 inspection 用例名对账
  - `git rev-parse --short HEAD` → `5e64a1e`
  - `rg heartbeat(` → 生产调用点只有 `WorkflowCoreMixin.heartbeat` 定义，`WorkflowWorker.run_once` 零调用
  - `rg require_active` → 仅 `TeamService.require_active` 定义，检索路由未调用
  - `rg "assert .* or True"` → `tests/unit/test_turso_driver.py:99`
  - 派出 6 个只读子代理（LLM adapter / Turso / retrieval / LS-RAG / race / false-green）；下列判断均经本审查人独立打开源文件复核，**不**把子代理原文当证据
- **复用 / 对照的既有审查**：
  - `docs/code-review/new-start/NS2-reviewed-by-grok.md` — **仅作线索**（dispatch 池 vs handler 运输）。本轮独立复核了 `generation_construct.py` / `dispatch.py` / `runtime_core.py` 当前 HEAD，不采纳 NS2 文档里未再核对的 closure 指控

### 1.1 已确认的正面事实

- 公共业务路由走 `BusinessToken`；Task create 与 retrieval 另挂 `Ready`。Token 比较使用 SHA-256 fingerprint + `hmac.compare_digest`。
- 出站 HTTP 有 hostname pin（`PinnedNetworkBackend`）、redirect 逐跳复核、默认拒绝 literal IP / 私网 / HTTP。
- 检索候选 SQL 同时要求 active pointer、publication proof 完整计数、intake `lifecycle_state='active'`、`serving_revision_uuid=r.intake_revision_uuid`、`publication_state='indexed'`。
- Prompt 冻结：live generate 会再读磁盘字节并与 snapshot SHA 比对，不匹配 fail-closed。
- Construct kernel 拒绝 summary 改写 original（`CONSTRUCT_KERNEL_ORIGINAL_MUTATION`）。
- Task 同 UUID 不同 `creation_fingerprint` 走 `task-identity-conflict`；同指纹 replay 返回已有视图。
- sqlite 后端被 `PYTEST_CURRENT_TEST` 门禁；普通进程选 `sqlite` 会被 factory 拒绝。
- `heartbeat()` API 存在；claim 使用 `status='ready' AND row_revision=?`；outcome 使用 `running AND fencing_generation`。
- README 对 browser/OCR 未接线、billing stub、R4 live 失败、R5 仅方案、全量非全绿的陈述，与代码现状一致。

### 1.2 已确认的负面事实

- `claim_outbox` 在同一事务里 `attempts+1` 后解析 JSON；解析失败抛错导致整笔回滚，毒丸行永不 dead。
- `drain_once` 先耗 outbox；outbox 抛错则 Process claim 与 `repair_once` 均不执行。
- Facade 把最后一次 `INFERENCE_TRANSPORT_RETRYABLE` 改写成 `INFERENCE_TRANSPORT_EXHAUSTED`；该码不在 `_RECOVERABLE_ERROR_CODES`。
- live vectorize 仅对 g0 **summary** 超 16k fail-closed；其余超预算单元被从 required set 删除后仍写完整 proof。
- 活跃指针 UPDATE 只 CAS `pointer_row_revision`，不要求 `active_index_generation` 单调；generation 在 **另一笔** 只读事务里 `index_generation+1`。
- `ux_vec_coord_active` 不含 `index_generation`。
- Turso 生产 UoW 是单连接 + `asyncio.Lock` + `BEGIN IMMEDIATE`；CW 探针切 MVCC 再切回去；sidecar 另开连接并 `journal_mode=mvcc`，CONCURRENT 失败则静默 `BEGIN`。
- `PRAGMA foreign_keys = ON` 在 Turso connect 上 `except: pass`。
- `LIVE_INFERENCE=false` 时检索用 `deterministic_embedding(query, namespace.dimension)`，不看 namespace 的 adapter/model。
- `TeamService.require_active` 存在但 retrieval 路由不调用。
- `DefaultBillingService.has_quota` 恒真，且 composition root 注入两份独立实例。
- `WorkflowWorker.run_once` 默认 `lease_seconds=30`，从不 heartbeat；vLLM generate 超时 180s，Claude CLI 超时 900s 且超时不杀子进程。
- `tests/unit/test_ns4_readport_reports.py` 不调用 ReadPort；`test_ns4_diagnostic_sidecar.py` 的 product-code 测试不断言 sidecar；`test_ns4_cw_soak.py` 串行插入且只断言本地 `MkbError.code`；`test_turso_driver.py:99` 为 `or True`。
- 大量 e2e 在 `persistence_backend="turso"` 之后用 `sqlite3.connect` 打开同一文件（ledger `NS1-V11`）。
- 本轮未对 pyturso `cursor.rowcount` 做 live 实测；全部 CAS 直接读 driver cursor 的 `rowcount`。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 入口、adapter、Turso port、workflow、intake、retrieval、点名测试均打开核对 |
| 本地命令 / 测试 | `no` | 未复跑 pytest / ruff；433/8 采信 README @ `5e64a1e` |
| schema / contract 反向校验 | `yes` | 核对 `001_initial.sql` 向量唯一索引、publication proof 字段、FK PRAGMA |
| live / deploy / preview 证据 | `no` | 无部署实例；未打真实 vLLM / Claude / 多线程 Turso |
| 与上游 design / QNA 对账 | `yes` | 对 README 能力表与 deferred ledger；S11 只核开头约束，未把 D07 验收当已通过 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 非法 outbox 行永久卡住唯一 supervisor | `critical` | `correctness` | `yes` | 校验失败标 dead；drain 隔离 outbox 错误 |
| R2 | live vectorize 静默丢层仍发完整 publication proof | `critical` | `correctness` | `yes` | 任一 required unit 超预算 fail-closed |
| R3 | 一批测试删掉 SUT 也会绿 | `critical` | `test-gap` | `yes` | 删 tautology；断言真实 IO / 行数 / 服务调用 |
| R4 | 推理运输耗尽变成终态失败 | `high` | `correctness` | `yes` | `EXHAUSTED`/`BACKPRESSURE` 纳入 process-retryable |
| R5 | 活跃指针 CAS 不单调，generation 跨事务预留 | `high` | `correctness` | `yes` | 指针 UPDATE 要求 generation 递增 |
| R6 | 向量唯一键不含 generation，upsert 会撤回正在 serving 的行 | `high` | `correctness` | `yes` | 唯一键含 `index_generation`；禁止 UPDATE indexed 行 |
| R7 | Turso 主路径不用 CW/native vector，探针是剧场 | `high` | `platform-fitness` | `yes` | 写路径与 readiness 对齐；FK 必须读回 1 |
| R8 | 检索在 live 命名空间上用 hash 向量打分 | `high` | `correctness` | `yes` | namespace adapter 与 query embed 必须同空间 |
| R9 | dispatch_pool 不是真实运输 SSOT | `high` | `protocol-drift` | `yes` | salvage 重 admit；clean 接线或拒绝入池 |
| R10 | e2e 用 sqlite3 打开 Turso 文件，且普遍 waiver 宪法探针 | `high` | `test-gap` | `yes` | 用 pyturso/port 检查；分清 waiver 与 constitution |
| R11 | Claude CLI 超时不杀子进程 | `high` | `correctness` | `no` | timeout/cancel 时 kill + drain |
| R12 | 默认 stub 把 summary 写成 original 并发布 | `high` | `correctness` | `no` | 默认禁止 S09，或显式 stub disposition |
| R13 | recall_k 只在 UUID 前缀 1000 行上生效 | `high` | `correctness` | `no` | 超限 fail-visible，或走 native distance |
| R14 | 组合根未注入 local-inference clean LM | `high` | `delivery-gap` | `no` | 接线 facade 或拒绝 admit |
| R15 | 团队级 index.rebuild 会被一个未 serving item 毒死 | `high` | `correctness` | `no` | resolve 时跳过 serving 为空的目标 |
| R16 | lease=30s 且从不 heartbeat | `medium` | `platform-fitness` | `no` | worker 心跳；unsafe 阶段默认不可静默 replay |
| R17 | 人工 gate 发生在 item 已 active 之后 | `medium` | `protocol-drift` | `no` | pending_review 直到批准 |
| R18 | 停用/删除 Team 仍可检索 | `medium` | `security` | `no` | retrieval 调 `require_active` |
| R19 | IPv6-mapped 地址未当 loopback/私网 | `medium` | `security` | `no` | 解开 mapped/6to4 再判受限 |
| R20 | Billing 恒真，salvage/NI 配额门是空的 | `medium` | `scope-drift` | `no` | 生产禁止 stub 或显式 unlimited 配置 |
| R21 | structured JSON 抽取过宽，schema 未交给 vLLM | `medium` | `correctness` | `no` | 整段必须是一个对象；传 schema |
| R22 | `/docs` 无鉴权；bootstrap 失败被吞 | `medium` | `security` | `no` | 关 docs 或鉴权；bootstrap 打日志 |
| R23 | markdown artifact 运输字段写死 claude_cli | `medium` | `docs-gap` | `no` | 抄 receipt.transport |
| R24 | Task 幂等指纹含 audit.created_at | `medium` | `correctness` | `no` | 指纹只含耐久命令字段 |
| R25 | adopt 的 structure 树是两节点覆盖，g0 空体被填成 clean | `medium` | `correctness` | `no` | 拒绝空 g0；按层做真实锚点 |
| R26 | `native_ann` 配置是死开关 | `low` | `platform-fitness` | `no` | 接线或拒绝该值 |
| R27 | 限流 fail-open，IP 检查在鉴权前 | `medium` | `security` | `no` | 业务路由 fail-closed；先鉴权再记 IP |
| R28 | 全部 CAS 依赖未归一化的 pyturso `rowcount` | `high` | `platform-fitness` | `yes` | adapter 暴露 `changes()` 并加 Turso claim 测试 |

### R1. 非法 outbox 行永久卡住唯一 supervisor

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/workflow/runtime_outbox.py:38-59`：同一事务 `UPDATE ... attempts=attempts+1` 后 `json.loads`；`JSONDecodeError` / digest 不匹配抛 `outbox-payload-invalid`，UoW rollback，attempts 永不增加
  - `src/runtime/workflow/runtime_outbox.py:77-104`：`_release_outbox` 只在 **claim 成功返回之后** 的 handler 异常里调用
  - `src/runtime/workflow_supervisor.py:39-51`：`drain_once` 先循环 `dispatch_outbox_once`；该调用抛错则后续 `run_once` / `repair_once` 不执行
- **为什么重要**：
  - 叶节点只有一个 supervisor。一条坏 payload 会让 outbox 扫描永远打在同一行上，工作流冻结，过期 lease 也无法回收。
- **审查判断**：
  - 这不是“at-least-once 的正常重试”。claim 没有在校验失败时留下 dead/attempts 证据。当前拓扑下可被一条脏行打停。
- **建议修法**：
  - 先 CAS 到 `in_flight` 并提交，再解析；解析失败标 `dead`。`drain_once` 必须 catch outbox 错误并继续 repair/process。

### R2. live vectorize 静默丢层仍发完整 publication proof

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/vectorize.py:185-204`：仅 g0 summary 超 `_LIVE_EMBED_CHAR_BUDGET`（16000）抛错；其余超预算单元从 `embeddable` 过滤后 `vector_inputs = embeddable`
  - 随后 handoff 的 `required_units`/`succeeded_units` 按缩小后的列表计数
  - `src/runtime/intake/vector_publish_commit.py:111-114`：`expected_count=actual_count=matched_count=len(ids)`
  - 检索 proof 谓词按 count 对齐，不比对 `required_set_digest` 与 live `(uuid, content_digest)` 集合
- **为什么重要**：
  - live 索引可以缺 g1/g2 original/summary 仍 `succeeded`。调用方以为分层检索完整。
- **审查判断**：
  - 这是假完整性，不是 typed skip。S07 合同还在，S08/S09 把它改写成子集并盖章。
- **建议修法**：
  - `len(embeddable) != len(plan.required)` 一律 `VECTORIZE_BUDGET_CONTENT_FULL`。读路径校验 `required_set_digest`。

### R3. 一批测试删掉 SUT 也会绿

- **严重级别**：`critical`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `tests/unit/test_ns4_readport_reports.py:8-22`：`ObservabilityReadService.__new__` 后只对本地 dict 做 get/assert，**零次**调用 ReadPort SQL
  - `tests/unit/test_ns4_diagnostic_sidecar.py:23-28`：构造 `MkbError` 后断言 `err.code` 仍是构造参数；sidecar 未实例化
  - `tests/integration/test_ns4_cw_soak.py:50-57`：注释写明串行；`product` 从未传入 sidecar；无 `SELECT COUNT(*)`
  - `tests/unit/test_turso_driver.py:99`：`assert "libsql_vector_idx" not in probe_native_vector.__doc__ or True` 恒真
  - `tests/unit/test_turso_driver.py:126-127`：只要求 `concurrent_writes == concurrent_writes_probe`，**不要求为 True**
  - `tests/unit/test_ns4_diagnostic_sidecar.py:15-20`：源码字符串含 `BEGIN CONCURRENT`；生产 `sidecar.py:35-37` CONCURRENT 失败则 `BEGIN`
  - `tests/domain/test_ns4_no_r3_ingest.py:13-14`：`runs.jsonl` 缺失直接 `return`
  - `tests/unit/test_dispatch_mega.py:350-365`：名为 concurrent soak，实为串行 `claim_next` + SqlitePersistence
- **为什么重要**：
  - README 用 433 passed 描述核心套件。这些绿不能证明 ReadPort、CW、sidecar、native-vector 声称。
- **审查判断**：
  - 这是假绿，不是弱断言。覆盖率数字会被这些用例抬高。
- **建议修法**：
  - 每个声称 IO 的测试必须打到真实函数：读回行、断言 count、调用服务方法。删 `or True` 与空 return。

### R4. 推理运输耗尽变成终态失败

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/inference/facade.py:332-342`：最后一次 `INFERENCE_TRANSPORT_RETRYABLE` 改写为 `INFERENCE_TRANSPORT_EXHAUSTED`
  - `src/runtime/intake/core.py:176-186`：可恢复集合含 `INFERENCE_TRANSPORT_RETRYABLE`，**不含** `EXHAUSTED` / `INFERENCE_BACKPRESSURE`
  - `src/runtime/intake/generation_live.py:257-269`：live generate 原样上抛 facade 的 `MkbError`
  - vectorize 把任意 `MkbError` 包成 `VECTORIZE_INFERENCE_FAILED`（该码在可恢复集合），所以 embed 能 process-retry，generate 不能
- **为什么重要**：
  - 瞬时 429/5xx/超时在 facade 内重试 3 次后，整个 structurize/markdown/C 变终态失败。可恢复列表对生产 generate 是死代码。
- **审查判断**：
  - `test_d01_review_fixes.py` 把 `INFERENCE_TRANSPORT_RETRYABLE` 标可恢复，但该码在成功走完 facade 后不会离开 facade。假绿。
- **建议修法**：
  - 把 `INFERENCE_TRANSPORT_EXHAUSTED` 与 `INFERENCE_BACKPRESSURE` 纳入 process-retryable，或停止改写最后一次 retryable 码。

### R5. 活跃指针 CAS 不单调，generation 跨事务预留

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/vector_publish_commit.py:263-279`：`_namespace_coordinates` 单独只读事务 `index_generation+1`，不 UPDATE namespace
  - `src/runtime/intake/vector_publish_commit.py:144-160`：指针 UPDATE 条件只有 `pointer_row_revision=?`，写入 `state["index_generation"]`，无 `active_index_generation < ?`
  - 对比 `src/runtime/intake/index_rebuild_commit.py`（rebuild 路径有旧 generation fence）
- **为什么重要**：
  - 晚到的 ingest publish 可以用更小的 generation 盖掉已经 cutover 的指针。若 retirement 已软删旧代，item 变黑；若未删，检索会回到旧代。
- **审查判断**：
  - 单进程 write_lock 降低同时 publish 概率，但不能防止“vectorize 预留 gen1 → rebuild 切到 gen2 → 晚 publish 写回 gen1”。e2e 没有这条时序。
- **建议修法**：
  - 在 vectorize UoW 内 `UPDATE namespace SET index_generation=index_generation+1 RETURNING`。指针 UPDATE 要求 `active_index_generation < excluded`。

### R6. 向量唯一键不含 generation，upsert 会撤回正在 serving 的行

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/persistence/migrations/001_initial.sql:1871-1874`：`ux_vec_coord_active` 为 `(team, namespace, generation_artifact_uuid, unit, channel, embedding_model)`，无 `index_generation`
  - `src/runtime/intake/vector_publish_commit.py:390-395`：同 coordinate UPDATE 把 `publication_state='withdrawn'` 并改 `index_generation`
  - 检索要求 `p.active_index_generation=r.index_generation` 且 `publication_state='indexed'`
- **为什么重要**：
  - 对同一 dual-channel artifact 的第二次 vectorize（retry / 重叠 worker）会把正在 serving 的行改成 withdrawn。指针仍指向旧 generation → 立即无结果。
- **审查判断**：
  - 与 R5 叠加时，retry 既能撤回 live 行，又能把指针回拨。
- **建议修法**：
  - 唯一键含 `index_generation`；serving 行不可变，只 INSERT 新 generation。

### R7. Turso 主路径不用 CW/native vector，探针是剧场

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/persistence/turso/port.py:66-98`：单例 `turso.connect`；每个 execute/fetch/commit 走 `asyncio.to_thread`；UoW 为 `BEGIN IMMEDIATE` + `_write_lock`
  - sqlite_port 设置 `check_same_thread=False`、`isolation_level=None`、WAL、`busy_timeout=5000`、`row_factory`；Turso port **全无**
  - `src/persistence/turso/port.py:72-75`：`PRAGMA foreign_keys = ON` 失败被吞
  - `src/persistence/engine.py:13-40`：CW 探针在**业务连接**上切 `journal_mode=mvcc`，试 `BEGIN CONCURRENT`，再 restore
  - `src/persistence/turso/sidecar.py:23-37`：每条诊断新连接，`journal_mode=mvcc`，CONCURRENT 失败则 `BEGIN`
  - 向量写入 `struct.pack` BLOB（`vectorize.py:303-304`）；排序是 Python cosine。`vector32` / `vector_distance_cos` 只出现在探针表
  - `build_persistence` 的 `vector_backend` 传给 sqlite，**不传** `TursoPersistence`
- **为什么重要**：
  - `/ready` 的 `concurrent_writes` / `native_vector` 不表示 serving 使用这些能力。FK 若未开启，schema 里的复合 FK 是注释。共享 FFI 连接跨线程是 pyturso 的已知陷阱。
- **审查判断**：
  - 本轮未 live 测量 pyturso cursor 线程安全性；但代码路径与官方“每线程新连接 + MVCC + BEGIN CONCURRENT”样本相反。把 CW 当已落地是文档/探针漂移。
- **建议修法**：
  - connect 后 `PRAGMA foreign_keys` 必须读回 1。journal_mode 一次设 sticky，不要在探针里来回切。要么 UoW 真用 CONCURRENT+conflict retry，要么 readiness 改名“single-writer-ok”。向量要么 `vector32` 写入并用 SQL distance，要么不要把 native_vector 当成 serving 证据。

### R8. 检索在 live 命名空间上用 hash 向量打分

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/services/retrieval/retrieval_request.py:97-99`：仅当 `self._live_inference` 才 `_embed_query`
  - `src/services/retrieval/retrieval_rank.py:145-148`：`query_embedding is None` 时 `deterministic_embedding(query, dimension=int(namespace["dimension"]))`
  - 写路径会冻结 snapshot 的 embed binding，namespace 冲突会拒绝混写；**读路径忽略 namespace.adapter_kind**
- **为什么重要**：
  - 把 `MKB_LIVE_INFERENCE` 拨回 false 不会拒绝搜索 1024-d Qwen 空间，而是用同维 hash 做 cosine。HTTP 200 + 若干 hits，排序是垃圾。
- **审查判断**：
  - 单元检索夹具用 `local_vllm` 行 + hash query，等于把该行为写成测试画像。
- **建议修法**：
  - `adapter_kind != deterministic` 时必须 live embed，否则 `RETRIEVE_SPACE_LAYER_A_MISMATCH`。

### R9. dispatch_pool 不是真实运输 SSOT

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - Admit：`runtime_core.py:304-315`，`local_available=self.live_inference`
  - Snapshot omit+normal：`config_snapshots.py:573-581` 写成 `local-inference`，**不**看 `live_inference`（只有 explicit local 才会 503）
  - Handler：`generation_construct.py:130-166` 以 `command.dispatch_pool` 为 SSOT；无 pool 时回落 `DEFAULT_COMPRESSION_CHANNEL="non-interactive"`
  - Salvage：`generation_construct.py:81-180` 在仍占 `local-inference` 槽时打 Claude；billing 恒真；不含 occupancy 重 admit
  - Clean：`clean_preflight.py:78-85` local-inference 需要注入 `clean_llm`；`api/app.py` 的 `IntakePipeline(...)` **没有** `clean_llm=`
  - `ns1_cli_mode=disabled` 时 construct C 走 `deterministic_summaries`（480 字截断原文），配置注释声称的 S11 structured_generate fallback **不存在**
- **为什么重要**：
  - 池会计、L2 snapshot、handler 运输、审计 receipt 可以是四个不同故事。live 打开后 LLM-clean 源会在 admit 之后以配置错误失败。normal 优先级的 schema/kernel 失败会在 GPU 槽上偷跑 Claude。
- **审查判断**：
  - NS2 单测证明 salvage **被要求发生**，不断言 NI occupancy。这是测试把漂移锁成合同。
- **建议修法**：
  - 单一函数决定 omit 策略；snapshot 存 **admit 后的** pool。Salvage 必须重新 admit 到 NI 或失败。local clean 接线或禁止入 local 池。NI 且 CLI 缺失时 fail-closed。

### R10. e2e 用 sqlite3 打开 Turso 文件，且普遍 waiver 宪法探针

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `tests/e2e/test_index_rebuild.py:18-27,120` 及 reactivate / rebuild_metadata / generation_contracts / scatter / vector_purge：`persistence_backend="turso"` + `sqlite3.connect`
  - `tests/local_runtime.py:17-25`：默认 turso，但 `concurrent_writes_required=False`、`native_vector_required=False`
  - README K1 / `deferred-items-ledger.md` `NS1-V11`：至少 5 个用例因此 `disk I/O` / `file is not a database`
  - 另 3 个全量失败是 5–8s 轮询未到终态（generation contracts 截止 5s）
- **为什么重要**：
  - 这些测试要么红在错误引擎上（假红，掩盖真正回归），要么绿在 waiver 的 `/ready` 上（假绿 constitution）。不能当作 Turso 或 durable supervisor 证据。
- **审查判断**：
  - owner 把 V11 标 true-deferred 不改变事实：当前套件不能证明生产检查路径。
- **建议修法**：
  - 检查走 `turso.connect` 或 persistence port。把 waiver 测试与 constitution 测试分开。终态等待与 lease/generate 超时同量级，超时必须 raise。

### R11. Claude CLI 超时不杀子进程

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/inference/claude_cli.py:291-302`：`asyncio.wait_for(process.communicate(...), timeout)`；`TimeoutError` 直接改 `CLAUDE_CLI_TIMEOUT`，无 `process.kill()` / `terminate()`
  - 默认 `timeout_seconds=900`；该码在 `_RECOVERABLE_ERROR_CODES`，会 process-retry
- **为什么重要**：
  - 超时后原 `claude` 继续跑，retry 再拉一个。CPU、供应商花费、FD 无界。
- **审查判断**：
  - `test_claude_cli_port.py` 覆盖 argv/stdin/JSON，不覆盖 timeout。
- **建议修法**：
  - except 里 kill、wait、再 raise。测试用 sleep 假二进制。

### R12. 默认 stub 把 summary 写成 original 并发布

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/config.py:44`：`ns1_cli_mode` 默认 `stub`
  - `src/runtime/inference/claude_cli.py:110-115,401-421`：stub C 在预算内 **原样复制** original
  - `src/services/lsrag_compiler/validate.py:129-131`：只要求 summary 非空
  - `tests/e2e/test_generation_pipeline_contracts.py:160-173` 断言 g0/g1/g2 集合与向量坐标，不断言 `summary != original`
- **为什么重要**：
  - 默认离线（以及 `LIVE_INFERENCE=true` 但 CLI 仍 stub）会把“双通道”发布成两个相同字节。检索 grounding 是回声。
- **审查判断**：
  - README 把 stub 标为已落地离线能力，这点诚实；不诚实的是 e2e 把它当成 LS-RAG 语义证明。R8 的 live+stub 组合会用真 embedder 索引假摘要。
- **建议修法**：
  - 无显式 allow-stub 不得 S09；或 `validation_disposition=stub` 且检索标明。kernel 拒绝 summary==original（live 路径）。

### R13. recall_k 只在 UUID 前缀 1000 行上生效

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/services/retrieval/retrieval_rank.py:127-130`：`ORDER BY r.vector_record_uuid LIMIT ?`，limit 默认 `candidate_scan_limit=1000`
  - 其后 Python 打分再切 `recall_k`/`return_k`
- **为什么重要**：
  - 超过约 1000 条 serving 行后，top-k 不是全索引 top-k。更好的命中如果 UUID 更大则永远看不见。
- **审查判断**：
  - 与 R7 一致：native vector readiness 与 serving 扫描无关。单元测试只插 5 行。
- **建议修法**：
  - fenced 行数超过扫描上限时 fail-visible；或 SQL `vector_distance_*`。

### R14. 组合根未注入 local-inference clean LM

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `api/app.py:315-329`：`IntakePipeline(..., inference=..., claude_cli=..., live_inference=...)`，无 `clean_llm`
  - `src/runtime/intake/clean_preflight.py:78-85`：`dispatch_pool==local-inference` 且 `llm is None` → `COMPRESSION_CHANNEL_UNAVAILABLE`
  - `src/runtime/workflow/dispatch.py:20-28`：`clean.extract.{web,doc,pdf}_llm` 在 generate 池里
- **为什么重要**：
  - `live_inference=true` 时这些 process 会被 admit 进 local 池，然后稳定失败。单测注入 `_LLM()` 所以 CI 绿。
- **审查判断**：
  - 合同拒绝路径存在，但 live 打开后是 admit-then-fail，浪费池容量。
- **建议修法**：
  - 为 local 池绑 facade-backed CleanLanguageModel，或这些 key 不得 choose_pool=local。

### R15. 团队级 index.rebuild 会被一个未 serving item 毒死

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/services/intake_lifecycle/targets.py`：index.rebuild resolve 收集 active+latest，不要求 `serving_revision_uuid`
  - `src/runtime/intake/index_rebuild_plan.py:258-264`：执行时要求 serving==latest，否则 `INDEX_REBUILD_TARGET_STALE`
  - reactivate 恢复 lifecycle 但不恢复 serving（e2e 名称即此）；随后团队 rebuild 会因这一条失败整单
- **为什么重要**：
  - 运维“整队重建索引”在有一条刚 reactivate、尚未 ingest.rebuild 的 item 时整单失败。
- **审查判断**：
  - 单条 reactivate→ingest.rebuild 有测试；团队 rebuild + 混合 serving 集没有。
- **建议修法**：
  - resolve 阶段跳过 `serving_revision_uuid IS NULL`；不要把可跳过目标升级为 Task 失败。

### R16. lease=30s 且从不 heartbeat

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/workflow/worker.py:45-53`：`lease_seconds=30`，handler.run 期间无 heartbeat
  - `src/runtime/workflow/runtime_core.py:546-557`：heartbeat 已实现
  - `src/runtime/workflow/runtime_materialize.py:308-313`：`safe_replay: True` 写死
  - 当前 supervisor `drain_once` 串行，handler 期间不会 `repair_once`，单进程下双跑被拓扑掩盖
- **为什么重要**：
  - 第二 worker、崩溃恢复、或以后并发 drain 会在 generate/CLI 仍运行时把 fence+1 并重跑。HTTP/LLM/CLI 有副作用。outcome CAS 防双提交，不防双调用。
- **审查判断**：
  - 对**当前**单 supervisor 不是活漏洞；对声称的 durable worker 合同是未完成实现。标 medium 而非 critical，因为拓扑暂时掩盖。
- **建议修法**：
  - handler 全程心跳；lease ≥ generate/CLI 超时；获取/生成阶段 `safe_replay=false`，过期走 indeterminate，不静默 replay。

### R17. 人工 gate 发生在 item 已 active 之后

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/intake/acceptance_snapshot.py`：accept 插入 `lifecycle_state='active'`
  - 图：accept_snapshot → human_review；reject 失败的是 execution，不 deactivate item
- **为什么重要**：
  - 人工审查不能撤销已 admitted 的 item。reject 留下 active 未发布成员。
- **审查判断**：
  - e2e 只测 approve→succeeded。控制节点在，质量门不在。
- **建议修法**：
  - 批准前 `pending_review`；reject 必须 CAS lifecycle。

### R18. 停用/删除 Team 仍可检索

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：
  - `api/public/routes.py:452-469`：retrieval 只要求 token + ready
  - `src/services/teams.py:141-148`：`require_active` 存在，`rg` 显示无其他生产调用
  - 候选 SQL 无 `mkb_teams.status`
- **为什么重要**：
  - Team deactivate/delete 只改团队行。intake 与 pointer 仍 active，租户停用后知识仍可搜。
- **审查判断**：
  - 内部 leaf 的全局 bearer 模型下，这是租户生命周期洞，不是跨 team 读。
- **建议修法**：
  - 检索前 `require_active`；候选/revalidate SQL 加 `teams.status='active'`。

### R19. IPv6-mapped 地址未当 loopback/私网

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/security.py:335-344`：`_restricted` 直接看 `is_loopback` / `is_private`
  - CPython 中 `IPv6Address('::ffff:127.0.0.1').is_loopback` 为 False；mapped RFC1918 / metadata 同样
  - pin-after-resolve 本身是对的，但判定集合不含 mapped unwrap
- **为什么重要**：
  - DNS（或未来允许 literal）若返回 mapped 地址，可以打到 loopback / link-local / 169.254.169.254。
- **审查判断**：
  - 现有 SSRF 测试覆盖私网 DNS 与 redirect，无 `::ffff:127.0.0.1`。本轮未跑 ipaddress 复现，依据是稳定的 CPython 语义。
- **建议修法**：
  - 对 `ipv4_mapped` / `sixtofour` 递归 `_restricted`。补测试。

### R20. Billing 恒真，salvage/NI 配额门是空的

- **严重级别**：`medium`
- **类型**：`scope-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/services/billing.py:16-21`
  - `api/app.py:293,325` 两处 `DefaultBillingService()`
  - `choose_pool` / salvage 把 `has_quota("non-interactive")` 当真门
  - ledger `NS2-O1` 已登记 true-deferred
- **为什么重要**：
  - 不绕过 running cap，但绕过唯一配额门。代码长得像已执行的政策。
- **审查判断**：
  - README K10 诚实。仍报是因为 salvage（R9）把 stub 用成真通道切换许可。
- **建议修法**：
  - 生产默认 fail-closed，或配置显式 `billing_unlimited=true` 且审计该选择。

### R21. structured JSON 抽取过宽，schema 未交给 vLLM

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/inference/facade.py:49-66`：`find('{')` + `rfind('}')` 切片
  - `src/llm_adapters/local_vllm.py:161-162`：只设 `response_format: json_object`，不传 `json_schema_ref`
  - `_live_structured_generate` 不传 facade `validator=validate_layered_content`
  - `src/services/lsrag_compiler/adopt.py:66-67`：g0 body 空则填 clean
- **为什么重要**：
  - 截断/拼接对象可能 `json.loads` 成功。模型可省略 g0，kernel 用全文冒充分层。schema 文件对 vLLM 是死的。
- **审查判断**：
  - kernel 之后多数垃圾会 fail-closed；g0 填充是明确的静默修复，不是拒绝。
- **建议修法**：
  - 整段必须是一个 JSON object；把 layered schema 交给 vLLM；拒绝空 g0。

### R22. `/docs` 无鉴权；bootstrap 失败被吞

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：
  - `api/app.py:450`：`FastAPI(...)` 默认 docs/redoc/openapi
  - `api/app.py:407-414`：`registry.bootstrap` / `workflows.bootstrap` 的 `MkbError` `pass`，无日志
  - `main()` bind `127.0.0.1:8080`；容器映射 8080 会改变攻击面
  - README 已标 K9
- **为什么重要**：
  - 内部 token 模型下 OpenAPI 仍是枚举面。bootstrap 失败只体现在 `/ready`，stdout 无证据。
- **审查判断**：
  - 对“只在 loopback 跑”可接受；对 leaf-worker 公共 endpoint 审查必须记下。outbox 不看 ready（race 子代理），bootstrap 失败时仍可能消费已有 outbox。
- **建议修法**：
  - `docs_url=None` 或 operator auth。bootstrap 失败打结构化日志。outbox/repair 与 claim 共用 ready 栅栏。

### R23. markdown artifact 运输字段写死 claude_cli

- **严重级别**：`medium`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/intake/generation_construct.py:544-554`：live markdown receipt `transport=api_inference`
  - 同文件约 618-623：artifact 元数据 `"transport": "claude_cli"` 写死
- **为什么重要**：
  - 审计会把 vLLM markdown 算到 Claude 头上。冻结 prompt 本身是对的，运输身份在撒谎。
- **审查判断**：
  - 不改检索对错，改可追责性。与 dispatch SSOT 声明冲突。
- **建议修法**：
  - 抄 `receipt["transport"]`，并纳入 invocation `request_digest`。

### R24. Task 幂等指纹含 audit.created_at

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/task/task_create.py:53-71`：`stable_digest(request.model_dump(mode="json"))`
  - audit 合同含 `created_at`
- **为什么重要**：
  - 客户端重试若刷新审计时间，合法 replay 变 `task-identity-conflict`。真正冲突检测被时钟字段污染。
- **审查判断**：
  - 不同业务 payload 仍会冲突（好）。并发双 INSERT 未映射 unique violation（write_lock 掩盖）。
- **建议修法**：
  - 指纹只含 team/task/intent/payload/priority/deadline。unique violation 再读行比较指纹。

### R25. adopt 的 structure 树是两节点覆盖，g0 空体被填成 clean

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/services/lsrag_compiler/adopt.py:66-67,176-227`：空 g0→clean；树为 root+单 paragraph 覆盖全文；g1/g2 用 `str.find` 第一次出现
  - `tests/unit/test_adopt_layered_json.py` 把重复子串锚到首次出现写成预期
  - `tests/unit/test_lsrag_compiler.py` 仍测历史 `compiler.structurize()`，不是生产 adopt
- **为什么重要**：
  - “分层 structure document”不是分层树。重复短语会错锚。R5 方案里的 system-owned g0 尚未存在，当前 g0 经常是 clean 隧道。
- **审查判断**：
  - 这是产品语义缺口，不是崩溃。与 README“分层块、original 回溯”的对外描述不完全相符。
- **建议修法**：
  - 拒绝空 g0；每层非重叠跨度；历史 `structurize()` 标 deprecated 并停止当生产测试。

### R26. `native_ann` 配置是死开关

- **严重级别**：`low`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/config.py:27`：`vector_backend` 含 `native_ann`
  - `src/persistence/factory.py:53-58`：Turso 构造器不接收该参数
- **为什么重要**：
  - 运维以为能打开 ANN。实际检索仍是 Python 扫描（R13）。
- **审查判断**：
  - 低危配置谎言，与 R7/R13 同源。
- **建议修法**：
  - 未实现则 reject `native_ann`。

### R27. 限流 fail-open，IP 检查在鉴权前

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：
  - `api/dependencies.py:104-116`：先 `check_ip` 再 `authenticate`
  - `src/runtime/security.py:207-215`：记账异常 `degraded=True` 且 `allowed=True`
  - `src/runtime/security.py:104-106`：`matched = compare_digest(...) or matched` 在首次匹配后短路，与“不提前返回”注释相反
- **为什么重要**：
  - 未认证洪水能填满 bucket 并触发 fail-open。注释说“只在 token 验证之后”对 IP 维为假。双 token 短路泄漏哪一个匹配（低）。
- **审查判断**：
  - `test_security_boundary.py` 把 fail-open 断言成正确行为。对内部叶节点是明确取舍，不是疏忽；作为公共 endpoint 审查必须否决默认 fail-open。
- **建议修法**：
  - 业务路由 degraded 时 fail-closed。先鉴权再记 IP。用非短路 `|=` 比较两个 fingerprint。

### R28. 全部 CAS 依赖未归一化的 pyturso `rowcount`

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/workflow/runtime_core.py:462-477` 等：`updated.rowcount != 1` 决定 claim/heartbeat/pointer/vector fence
  - `src/persistence/turso/port.py`：`execute` 原样返回 driver cursor，无 `changes()` 包装
  - CAS 单测在 `SqlitePersistence`（`test_d04_write_paths.py`）；无 Turso `claim_next` 测试
- **为什么重要**：
  - DB-API `rowcount` 在部分驱动上是 `-1` 或“成功即 1”。若 pyturso 恒 1，fence 失效（双 claim / 陈旧指针）。若恒 -1，claim 永不成功。
- **审查判断**：
  - **本轮未对 pyturso 0.7.2 的 cursor.rowcount 做 live 实测。** 标 blocker 是因为整个正确性模型压在这个未封装的驱动细节上，且测试从未在生产驱动上证明 CAS。
- **建议修法**：
  - `TursoUnitOfWork` 在 DML 后读 `changes()` 并返回自己的结果类型。加 Turso 上的 claim + stale revision 测试。

---

## 3. In-Scope 逐项对齐审核

> 对照 README §1.1 能力表与 §12.2 已知事项，而不是某一份已冻结 action-plan。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | FastAPI 单体、探针、公共/内部路由已落地 | `partial` | 路由与鉴权在；`/docs` 开放；bootstrap 失败静默；`/ready` 组件名会泄漏 |
| S2 | Team/Task/Execution/Process 状态机已落地 | `partial` | 主路径在；outbox 毒丸可停 supervisor；lease/heartbeat 未接线 |
| S3 | 本地 Turso 与并发写/native-vector readiness 已落地 | `partial` | 迁移与嵌入式文件在；CW/vector **探针 ≠ 写路径**；FK PRAGMA 可被吞 |
| S4 | 本地 CAS / GC 已落地 | `done` | 未把 GC 实现逐行打穿；object handle 的 team 前缀检查已看到 |
| S5 | inline 确定性摄取已落地 | `partial` | 离线 stub 路径能跑通任务；发布的不是语义双通道（R12） |
| S6 | browser/OCR/Vision/doc-LLM 合同已落地未接线 | `done` | 与 README 一致；组合根未注入 |
| S7 | 离线 stub + hash 检索已落地 | `partial` | 功能在；测试把 stub 当 LS-RAG 证明；live 关时 hash 会打进 live 空间（R8） |
| S8 | 本地 vLLM / Claude CLI adapter 已接线 | `partial` | 类在；运输/池/salvage/clean_llm 不一致；CLI 超时不杀进程 |
| S9 | 发布栅栏 + context-only retrieval 已落地 | `partial` | 读 SQL 双栅栏强；指针 CAS / 子集 publish / 停用 Team / 1000 行扫描削弱它 |
| S10 | 全量测试 433/8，核心非 E2E 套件通过 | `stale` | 数字或许可复现；其中相当一部分绿不是行为证明（R3/R10） |
| S11 | R5 system-owned g0 | `out-of-scope-by-design` | README / eval 为 WAIT_OWNER；代码未落地 |
| S12 | 真实 billing | `out-of-scope-by-design` | `NS2-O1`；但 stub 被 salvage 当真门用 |
| S13 | cloud-inference | `out-of-scope-by-design` | `NS2-O2`；CHECK 拒绝该 pool 名 |

### 3.1 对齐结论

- **done**: `2`
- **partial**: `8`
- **missing**: `0`
- **stale**: `1`
- **out-of-scope-by-design**: `2`

> 这更像“核心骨架与大量 fail-closed 合同已落地，但运输/持久化/测试证据仍未收口”，而不是 completed。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | `NS1-V11` sqlite3 检查 Turso 文件 | `遵守`（作为不修项） | 代码与测试仍在；本轮把它当 **测试证据 blocker**，不当成“实现者偷偷修了” |
| O2 | `NS2-O1` 真实 billing | `部分违反` | 未实现计量，但 salvage/admit 把恒真端口当政策执行 |
| O3 | `NS2-O2` cloud-inference | `遵守` | 无 cloud adapter；CHECK 拒绝该名 |
| O4 | R5 system g0 / quoted cuts | `遵守` | 无对应 schema/prompt/代码 |
| O5 | 前端 / 公网部署 / CORS | `遵守` | `frontend/` `public/` 仍占位 |
| O6 | 多进程 worker | `误报风险` | 代码按单进程写；lease/occupancy/限流在第二副本上会错。不把多进程标为当前活漏洞，但 R16/R27/R28 是预先破裂面 |
| O7 | 把“代码风格”当 blocker | `遵守` | 本轮未报纯风格 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：实现骨架不能支撑“生产 leaf-worker 已可靠”或“433 绿=行为已证”的收口。先修 R1–R3、R4–R10、R28 再谈关闭。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. R1：outbox 毒丸必须能 dead-letter；`drain_once` 不得因 outbox 解析失败跳过 repair
  2. R2：live vectorize 不得把缩小后的集合当成完整 required set
  3. R3：删除或重写不能失败的测试（ReadPort、sidecar product-code、CW soak、`or True`）
  4. R4：运输耗尽必须 process-retryable，或停止改写错误码
  5. R5/R6：指针单调 CAS + 向量唯一键含 generation
  6. R7/R28：Turso adapter 归一化 `changes()`、FK 读回 1、readiness 不再为未使用的 CW/ANN 撒谎
  7. R8/R9：检索空间与 dispatch 运输各自只有一个 SSOT
  8. R10：Turso e2e 检查不得再用 `sqlite3.connect`；constitution 与 waiver 分套件
- **可以后续跟进的 non-blocking follow-up**：
  1. R11 CLI kill、R14 clean_llm、R15 团队 rebuild 目标过滤
  2. R12 stub disposition、R13 扫描上限 fail-visible、R16 heartbeat
  3. R17–R27（gate 生命周期、Team 检索、SSRF mapped、billing 显式、docs、指纹、adopt 树）
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

### 5.1 本轮审查深度限制（诚实）

以下区域**不够深**，二次审查应补：

- **未跑全量 pytest / ruff**，8 个红的精确 node id 以 README/ledger 为准，未在本机复现。
- **未 live 测 pyturso `rowcount`、跨线程同一 connection、MVCC+索引**。R28/R7 的最坏情况仍是风险，不是已观察的生产事故。
- **scatter/join 只核了“部分成功仍 serving”的合同**，未逐步走完 fan-in 失败撤回。
- **object GC / retention SQL** 未逐条对账孤儿条件。
- **S11 全文 / D04 55 表** 未做逐条 DDL 对账；向量唯一索引与 publication 列已抽查。
- **未打开浏览器或打 live vLLM**。R4 live cell 失败采信 `docs/eval` 与 README，未复跑。

本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
