# Nano-Agent 代码审查模板

> 审查对象: `MKB 0820-review 第2轮 — NS5-0820-bug-fixes 收口后全仓 HEAD`
> 审查类型: `rereview`
> 审查时间: `2026-08-20`
> 审查人: `Grok`
> 审查范围:
> - `src/`、`api/`、`intake/`、`tests/`（NS5 P1–P6 落地代码与配套测试）
> - `src/persistence/`（Turso 载体、UoW、migration 001–015、sidecar）
> - `src/runtime/workflow/`、`src/runtime/intake/`、`src/runtime/inference/`、`src/runtime/security.py`
> - `src/services/retrieval/`、`src/services/object_gc.py`、`src/storage/local_store.py`
> 对照真相:
> - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md`（第1轮 UF→VF 台账；本轮只把它当「宣称已修清单」，不把它的结论当证据）
> - `docs/plan/new-start/NS5-0820-bug-fixes.md`
> - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`
> - `docs/baseline/domain-truth/` D04 / S01 / S03 / S12 / S15 / S16
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 第1轮修复把一批不可恢复 IO 洞钉上了补丁，但 0820-review 的完整目标尚未达成：若干宣称 DONE 的 VF 在生产默认画像上仍是断点，测试保真不足以支撑收口，长期治理（就绪语义、HITL 生命周期、serving 行不可变、叶工人接口）仍未合拢。

- **整体判断**：该实现主体补丁成立，但当前不应标记为 completed；0820-review 不能关闭。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. P1-02 把 `concurrent_writes=false` 写进 S15 `REQUIRED` 合取：默认 Turso 宪法画像下 `/ready` 与 `claim_next` 永久 503；测试用 `concurrent_writes_required=False` 把该矛盾藏起来。
  2. VF40「human_review 用 deactivated 代替 pending」只挡住了检索泄漏，激活写在无人调用的 `resolve_gate` 上；公共 approve 路径 `consume_gate_decision` 不改 Item，发布被 `PUBLICATION_SERVING_FENCE` 挡住。
  3. 若干 DONE 宣称与代码相反：salvage 仍是同 Process 的 Claude 调用、证据仍有 `"_"` 回退、vectorize 仍 UPDATE 已 indexed 行、空 CIDR 仍信任私网 XFF、NS5 短途测试大量不证命题。

---

## 1. 审查方法与已核实事实

> 这一节只写事实，不写结论。

- **对照文档**：
  - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md`
  - `docs/plan/new-start/NS5-0820-bug-fixes.md`
  - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`
  - `docs/closure/new-start/deferred-items-ledger.md`（NS5 段）
  - `docs/baseline/domain-truth/S01-skill-worker-integration.md`、`S03-workflow-engine.md`、`S12-turso-persistence.md`、`S15-observability-reliability.md`、`S16-security-trust-boundary.md`、`D04-turso-physical-schema.md`
- **核查实现**：
  - git 区间 `d728d0b..8cb2cb4`（P1–P6 + remainder + self-audit）
  - `src/persistence/{uow,engine,factory,migration_runner,sqlite_port,turso/port,turso/sidecar}.py`
  - `src/runtime/workflow/{worker,runtime_core,runtime_outbox,runtime_outcome,runtime_gates,workflow_supervisor}.py`
  - `src/runtime/{health,security,config}.py`、`api/{app,dependencies}.py`
  - `src/runtime/intake/{vectorize,vector_publish_commit,acceptance_snapshot,generation_construct,generation_evidence,acquisition_ingest}.py`
  - `src/runtime/inference/{facade,claude_cli}.py`、`src/llm_adapters/local_vllm.py`
  - `src/services/{artifacts,object_gc,index_retirement,teams,events}.py`、`src/services/retrieval/*`
  - `tests/unit/test_ns5_*.py`、`tests/integration/test_ns5_turso_mainchain.py`
- **执行过的验证**：
  - `git log --oneline d728d0b^..HEAD` 与逐 commit `--stat`
  - 对上述路径的 `Read` / `Grep` 行级核对（本轮未复跑全量 pytest / ruff / live GPU / 真机 CW）
  - 9 路并行对抗性子代理（P1–P6 分簇 + 幂等/竞态/durable + leaf-worker 接口 + Turso/SSOT）；下列每条 blocker 均由本审查人再次打开源文件独立坐实，子代理结论只作线索，不作文凭
- **复用 / 对照的既有审查**：
  - 第1轮 `0820-reviewed-by-*.md` — **未读取、未引用、不采纳**。本轮只使用 VF 台账作为「第1轮声称要修什么」的编号地图，再对 HEAD 代码独立复核
  - VF-ledger / NS5 AP / NS5 closure — 作为 claimed-fix 对照，不作为正确性证据

### 1.1 审查 DAG（本轮实际执行）

```text
Wave 0  读取 VF 台账 / NS5 AP / closure / domain-truth / git 区间
   │
   ├── Wave 1 业务簇（并行进攻性审查）
   │     P1 运行时 IO / UoW / sidecar / heartbeat / outbox / GC
   │     P2 持久化诚实 / CAS / migration / ready
   │     P3 推理车道 / salvage / 证据
   │     P4 serving / vectorize / 检索 / generation
   │     P5 安全边界
   │     P6 测试保真 / 包装 / 后延诚实
   │
   └── Wave 2 横切（与 Wave 1 并行）
         幂等 / 竞态 / durable state
         leaf-worker 接口合规 / 安全 / 运行时稳定性
         Turso 业务流转 / 可观测性 / SSOT 双写
   │
Wave 3  独立归因 + 本文
```

### 1.2 已确认的正面事实

- HEAD 为 `8cb2cb4`。NS5 代码提交链为 `d728d0b`（P1）→ `4ad95c5`（P2）→ `fd5c969`（P3）→ `52e3913`（P4）→ `34c86b6`（P5）→ `7bffb70`/`f7bec3f`（P6）→ remainder `c7c74f2`/`8cb2cb4`。
- 共享 helper `immediate_transaction` 捕获 `BaseException`，`commit()` 在 `try` 内，rollback 经 `asyncio.shield`；sqlite 与 turso 端口共用（`src/persistence/uow.py:12-46`）。
- Sidecar 改为单连接 + `threading.Lock` + `BEGIN IMMEDIATE`，不再每条 insert 切 `journal_mode`（`src/persistence/turso/sidecar.py:1-78`）。
- Outbox 先 CAS `in_flight` 再 parse；非法 JSON / digest 失败走独立 TX 标 `dead`（`src/runtime/workflow/runtime_outbox.py:41-82`）。
- Worker 在 `run_once` 内启动 heartbeat；CAS 失败会 `handler_task.cancel()`（`src/runtime/workflow/worker.py:66-160`）。
- `claim_next` 同 TX 循环 fail-expired（上限 64）后再 admit（`src/runtime/workflow/runtime_core.py:353-370`）。
- GC unlink 移出 persistence 写锁；tombstone 在第二 TX（`src/services/object_gc.py:196-272`）。`_pending` 在 `validate_and_commit` 的 `finally` 与 `discard` 中 pop（`src/services/artifacts.py:92-130`）。
- 指针 CAS 含 `active_index_generation < ?`（`src/runtime/intake/vector_publish_commit.py:144-162`）。015 unique 含 `index_generation`。
- live vectorize 超 16k 抛 `VECTORIZE_BUDGET_CONTENT_FULL`，不再缩 `required_units`（`src/runtime/intake/vectorize.py:185-192`）。
- 单通道 purge 在命令入口 422（`src/services/vector_purge.py:71-76`）。检索 LIMIT+1 超限 503（`src/services/retrieval/retrieval_rank.py:127-136`）。
- Facade `_invoke` 在 RETRYABLE 退避前放 lease；408/425 进 TRANSPORT_RETRYABLE。CLI 业务正文走 stdin。
- sqlite 后门要求 `PYTEST_CURRENT_TEST` **且** `pytest in sys.modules`（`src/persistence/factory.py:13-21`）。限流 overflow 不再全局 fail-open（`src/runtime/security.py:199-213`）。
- `pyproject.toml` 钉 `fastapi==0.141.1`、`starlette>=1.0.1`；package-data 含 `migrations/*.sql`。
- VF86 e2e `sqlite3.connect` Turso 文件、VF23 billing 恒真、VF88 live GPU、VF97 browser/OCR 仍登记为后延；closure 未把它们改写成「本轮已修」。
- `allow_overlapping_run_once=False` 仍关掉重叠 `run_once`（结构上 supervisor 也从未读该旗标）。

### 1.3 已确认的负面事实

- `TursoPersistence.readiness` 在 `concurrent_writes_required=True`（`Settings` / `default.toml` 默认）时强制 `concurrent_writes=False`（`src/persistence/turso/port.py:171-177`）。`HealthAggregator.REQUIRED` 含该字段（`src/runtime/health.py:14-24`）。`workflow_claim_readiness` 要求 `status=="ready"`（`api/app.py:291-294`）。
- `HealthAggregator._ttl_seconds` 被存储但从未读取（`src/runtime/health.py:26-44`）。`test_health_ready_coalesces_within_ttl` 只 `gather` 两次，断言 `1 <= n <= 2`。
- HITL Item 以 `deactivated` 插入（`acceptance_snapshot.py:106-123`）。`_apply_human_review_item_lifecycle_tx` 只被 `resolve_gate` 调用；全仓无其它 `resolve_gate(` 调用点。公共路径 `consume_gate_decision` 不改 Item lifecycle（`runtime_gates.py:197-285`）。发布要求 `lifecycle_state=='active'`（`lifecycle_publish.py:75-76`）。
- vectorize upsert 对已有坐标执行 `UPDATE ... publication_state='withdrawn'` 并改写 `index_generation`，无 `publication_state<>'indexed'` 栅栏（`vector_publish_commit.py:381-427`）。
- salvage 在同一 local Process 上 `cli.run`，不重新 admit NI Process（`generation_construct.py:192-226`）。`DefaultBillingService.has_quota` 恒真。
- `write_pending_generation_evidence_tx` 在 process 桶为空时回退 `take()` 默认键 `"_"`（`generation_evidence.py:50-52`）。
- 默认空 `trusted_proxy_cidrs` + 私网 ASGI peer 时，`request_ip` 返回 XFF 左值（`security.py:476-499`）。
- `TeamPatchRequest` / `TaskPatchRequest` 无 `assert_safe_public_data`（`src/contracts/api/models.py:50-59,362-377`）。
- body cap 只读 `Content-Length`；缺失或非数字则放行（`api/app.py:527-538`）。
- `LocalVllmAdapter._shared_client` 首次构造冻结 timeout；`probe` 使用 `min(timeout, 5)`；lifespan 不 `aclose`（`local_vllm.py:206-226`，`api/app.py:458-464`）。
- `FastAPI(...)` 未关 `docs_url`/`openapi_url`（`api/app.py:469`）。
- `verify_migrations` 在 checksum 之后只要求 `mkb_tasks` 存在（`migration_runner.py:159-163`）。
- 第1轮宣称的 VF36 双制品 digest=bytes、VF52 新 namespace、VF62 重叠 worker 仍未落地；closure 自己也标 under-delivery。
- `tests/e2e/` 仍大量 `sqlite3.connect` 打开 Turso 文件（VF86）。`test_ns5_turso_mainchain.py` 只跑 stub `intake.ingest`，不是生成+vectorize+retrieval 主链。

### 1.4 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 全部 blocker 与主要 finding 均回读 HEAD 源文件 |
| 本地命令 / 测试 | `no` | 未复跑 pytest / ruff / wheel unzip / Turso migrate；测试保真判断来自读测试源码 |
| schema / contract 反向校验 | `yes` | 对照 D04 表闭集、S01 六态、S16 extras/XFF、001 CHECK |
| live / deploy / preview 证据 | `n/a` | 无部署面 |
| 与上游 design / QNA 对账 | `yes` | S01/S03/S12/S15/S16/D04；未打开 qna-truth 当执行 SSOT |

---

## 2. 审查发现

> 编号稳定：`R1 / R2 / …`。只写影响 correctness / security / scope / delivery / test evidence 的问题。

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | 默认 Turso 宪法画像下 `/ready` 与 claim 永久 503 | `critical` | `correctness` | `yes` | 把探针位与准入位拆开，或真正兑现 CONCURRENT UoW |
| R2 | HITL approve 不激活 Item；`resolve_gate` 死代码 | `high` | `correctness` | `yes` | 把生命周期 CAS 接到 `consume_gate_decision` |
| R3 | vectorize 仍 UPDATE 已 serving 坐标 | `high` | `correctness` | `yes` | 禁止 UPDATE indexed 行；按 generation INSERT |
| R4 | salvage 仍不是运输 SSOT | `high` | `correctness` | `yes` | 占 NI occupancy 或 fail-closed；禁止同 Process 偷跑 CLI |
| R5 | 生成证据仍有跨 Process `"_"` 回退 | `high` | `correctness` | `yes` | 去掉默认桶；强制 process_uuid |
| R6 | 空 CIDR 仍信任私网 XFF | `high` | `security` | `yes` | 空 CIDR 只信 ASGI peer；XFF 仅 peer∈CIDR |
| R7 | Team/Task PATCH extras 跳过拒密 | `high` | `security` | `yes` | PATCH 走同一 `assert_safe_public_data` |
| R8 | body cap 只看 Content-Length | `high` | `security` | `no` | 实际读入时计数；chunked 同样 413 |
| R9 | vLLM 单例超时冻结且无 aclose | `high` | `platform-fitness` | `no` | 每请求 timeout；lifespan aclose；`trust_env=False` |
| R10 | Task cancel 不在同 TX 栅栏 Execution | `high` | `correctness` | `no` | cancel UoW 同时把 Execution/Process 标 cancelling |
| R11 | heartbeat 非取消异常会静默停跳 | `high` | `correctness` | `no` | 心跳失败即 fence+cancel handler |
| R12 | schema readiness 只探 `mkb_tasks` | `high` | `correctness` | `no` | 对照 D04 required 表闭集 fail-closed |
| R13 | VF36 digest≠bytes，rebuild 已依赖该谎言 | `high` | `correctness` | `no` | 双 CAS 对象；禁止用 envelope 冒充 clean 字节 |
| R14 | 标题进入 embed，查询侧不带 header | `medium` | `correctness` | `no` | 统一 body-only 或 query 同配方 |
| R15 | NS5 短途测试大量假绿 | `high` | `test-gap` | `yes` | 删源码扫描/ tautology；按 AP 收口谓词重写 |
| R16 | `/docs` `/openapi.json` 匿名 | `medium` | `security` | `no` | `docs_url=None` 或 operator token |
| R17 | UoW `BEGIN` 在 try 外 | `medium` | `correctness` | `no` | BEGIN 纳入同一 try/rollback |
| R18 | `outbox.dead` 无指标、trace 被替换 | `medium` | `delivery-gap` | `no` | 注入 metrics；沿用业务 `trace_uuid` |
| R19 | CLI stdout 上限在 `communicate()` 之后 | `medium` | `platform-fitness` | `no` | 有界读；finally shield kill |
| R20 | Facade 重试再获取失败时 `release(None)` | `medium` | `correctness` | `no` | finally 只 release 非空 lease |

### R1. 默认 Turso 宪法画像下 `/ready` 与 claim 永久 503

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/persistence/turso/port.py:171-177`：`concurrent_writes_required` 为真时覆盖 `gates["concurrent_writes"]=False`
  - `src/runtime/health.py:14-24`：`REQUIRED` 含 `concurrent_writes`
  - `api/app.py:291-294`：`workflow_claim_readiness` 要求 aggregator `"ready"`
  - `src/runtime/config.py:24`、`data/config/default.toml:7`：默认 `concurrent_writes_required = true`
  - `tests/local_runtime.py:21` 及几乎全部 e2e：显式 `False` waiver
- **为什么重要**：
  - S12 宪法要求 CW 默认启用、做不到则 fail-loud；S15 把该位当作准入合取。NS5 选择业务路径保持 `BEGIN IMMEDIATE`（避免 sidecar abort），却把「诚实的 false」直接喂给 `/ready`。结果不是「探针诚实」，而是**默认生产画像永不接纳 Task、永不 claim**。
  - 测试画像全部 waiver，所以 unit/integration 绿不能证明叶工人可启动。
- **审查判断**：
  - 这是 P1-02 与 S15 的逻辑冲突，不是文档笔误。waiver 路径上 `apply_capability_gates` 在 `required=False` 时把 `concurrent_writes` 报成 `True`（`engine.py:97-99`），那是另一方向的假绿。
- **建议修法**：
  - 拆成 `concurrent_writes_probe`（MVCC+CONCURRENT 实测）与 `write_path_ready`（单写者 IMMEDIATE+锁对叶工人足够）。`REQUIRED` 只合取后者，直到 UoW 真正 CONCURRENT。禁止 `required=True` 且强制 false 且仍宣称 closure ✅。

### R2. HITL approve 不激活 Item；`resolve_gate` 死代码

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/acceptance_snapshot.py:106-123`：`require_human_review` → `lifecycle_state='deactivated'`
  - `src/runtime/workflow/runtime_gates.py:164-195`：激活/拒绝写在 `_apply_human_review_item_lifecycle_tx`
  - 该函数仅被 `resolve_gate`（同文件 `:101`、`:127`）调用；全仓 `resolve_gate(` 只有定义
  - 公共路径 `consume_gate_decision`（`:197-285`）只 resume Execution / 路由，不碰 Item
  - `src/services/intake_lifecycle/lifecycle_publish.py:75-76`：非 active 抛 `PUBLICATION_SERVING_FENCE`
  - `001_initial.sql:961`：`lifecycle_state='active' OR serving_revision_uuid IS NULL`
- **为什么重要**：
  - 检索栅栏要求 active+serving，所以 HITL 中的 Item 不会漏检索——这是 closure 所谓 fail-closed。但 **approve 之后仍然 deactivated**，发布结构上不可能成功。`reactivate` 把「从未批准」与「运营停用」当成同一状态。
  - VF40 被登记成「016 pending 迁移」的余项，掩盖的是：**激活 CAS 接到了无人走的函数**。
- **审查判断**：
  - 这不是词汇表缺 `pending` 的 defer。这是 S05 人工门在当前 HEAD 上的断点。
- **建议修法**：
  - `consume_gate_decision` 在 approve/reject 时调用 `_apply_human_review_item_lifecycle_tx`。reject 必须能处理「已是 deactivated」的 HITL 插入（当前 reject SQL 只更新 `lifecycle_state='active'` 行，对 HITL 插入是空操作）。016 再引入真正的 pending。加一条 e2e：approve 后 `lifecycle_state='active'` 且 publication 成功。

### R3. vectorize 仍 UPDATE 已 serving 坐标

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/vector_publish_commit.py:381-427`：按坐标（**不含** generation）查找后 `UPDATE ... publication_state='withdrawn', index_generation=?`
  - `015_vec_coord_generation.sql:7-10`：unique 含 generation，只能挡住 INSERT 第二行，挡不住 UPDATE 同行
  - 指针 CAS 的 `active < excluded`（`:144-162`）只防回拨指针，不防把正在 serving 的向量行改成 withdrawn
- **为什么重要**：
  - S09：存在≠serving；serving 行不可变。同 dual-channel UUID 再跑 vectorize 会把当前 proof 的 indexed 集合打穿，检索 complete-set 失败 → **世代黑屏**，不是混代。
  - P4-10 宣称「禁止 UPDATE indexed 行」。代码没做到。
- **审查判断**：
  - VF44/55/58 只修了指针半边。015 是必要但不够。
- **建议修法**：
  - 已 `publication_state='indexed'` 的行禁止 UPDATE。新 generation 必须 INSERT 新行。lookup 带上 `index_generation`。测试：publish 后再 vectorize，serving COUNT 不得掉到 0。

### R4. salvage 仍不是运输 SSOT

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/generation_construct.py:192-226`：`_can_salvage_local_inference` 检查 CLI 存在、`dispatch_pool=='local-inference'`、非 low、billing；然后 `_salvage_summary_via_cli` → 同 Process `cli.run`
  - `src/services/billing.py`：`has_quota` 恒真（VF23 后延）
  - 无新 NI Process、无 `get_pool_occupancies` 再 admit
- **为什么重要**：
  - VF11 的合同是「池=运输」。salvage 把 local 槽上的失败换成 900s Claude，占用的仍是 local lease；心跳/回收看到的还是 `local-inference`。S11「闸满 → 零模型调用」被 salvage 的 BACKPRESSURE/EXHAUSTED 列表打破（`generation_construct.py:106-122`）。
- **审查判断**：
  - P3-01 的「urgent+explicit local 可 salvage」谓词测了，occupancy SSOT 没测。closure ✅ 过宽。
- **建议修法**：
  - salvage 要么 materialize/admit 一条 NI Process（占 `non-interactive` occupancy），要么 NI 满/未绑定 CLI 则 fail-closed。禁止把 BACKPRESSURE 翻译成另一条模型调用。

### R5. 生成证据仍有跨 Process `"_"` 回退

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/intake/generation_evidence.py:9-52`：`process_uuid or "_"`；flush 时先 `take(process_uuid)`，空则 `take()` 默认桶
  - `generation_construct.py:287-289` 等路径记录失败证据时省略 `process_uuid`
- **为什么重要**：
  - VF17 要消灭的就是「第一次失败写到第二次 process_uuid」。默认桶 + 回退等于把 ContextVar 换成进程级无锁 dict，串台窗口还在。一旦 VF62 打开重叠 `run_once`，这会变成必现。
- **审查判断**：
  - `test_evidence_is_keyed_by_process_uuid` 只覆盖两个显式 key 的 happy path，不覆盖省略 uuid / 回退。
- **建议修法**：
  - 删除 `"_"` 与 fallback。无 `process_uuid` 禁止 stash。测试：salvage 成功后再失败，第一笔失败不得出现在第二 process 的 invocation 行。

### R6. 空 CIDR 仍信任私网 XFF

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/runtime/security.py:476-499`：`cidrs` 空且 `_is_private_peer(peer)` 时返回 XFF 左值
  - `src/runtime/config.py:25`：默认 `trusted_proxy_cidrs=""`
  - `api/dependencies.py:176-194`：`/metrics` `/internal` 用同一个 `request_ip` 做内网闸
- **为什么重要**：
  - AP 的攻击用例「ASGI 10.0.0.1 + XFF 8.8.8.8 → /metrics 403」成立，因为 8.8.8.8 不是内网。但：
    1. 不带 XFF 的私网 peer 仍是内网（docker 旁路直连 uvicorn 即可刮 `/metrics`，默认还 `metrics_require_token=false`）；
    2. 代理 append 后左值若是 `127.0.0.1`，`is_internal_ip` 为真，**伪造内网**；
    3. 限流身份可被轮换 XFF 打穿，直到 overflow 桶。
  - S16 / README：默认不盲信转发头。空 CIDR 把任意私网 peer 当成反代，与「仅 peer∈CIDR 才解析 XFF」相反。
- **审查判断**：
  - P5-01 的测试只锁了「带外网 XFF 时不当内网」，没锁「空 CIDR 不把 XFF 当身份」。宣称「默认不盲信 XFF」过宽。
- **建议修法**：
  - 空 CIDR：`request_ip = peer`，完全忽略 XFF。只有 peer 落在 `trusted_proxy_cidrs` 才取 XFF。补测：peer=10.0.0.1 + XFF=8.8.8.8 在空 CIDR 下身份仍是 10.0.0.1。

### R7. Team/Task PATCH extras 跳过拒密

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`yes`
- **事实依据**：
  - `TeamCreateRequest.reject_secret_extras` / `TaskCreateRequest.validate_identity_and_payload` 调用 `assert_safe_public_data`
  - `TeamPatchRequest`（`api/models.py:50-59`）、`TaskPatchRequest`（`:362-377`）没有
  - 持久化：`src/services/teams.py:93-104`；GET 回显不做 redact
- **为什么重要**：
  - VF78 的攻击向量是「公共 extras 不是 vault」。CREATE 拒 `apiKey`，PATCH `{token:x}` 仍入库并在 GET 回出。
- **审查判断**：
  - `test_ns5_phase5.py` 只打 CREATE helper。P5-03 半修。
- **建议修法**：
  - PATCH 模型同一 validator。GET 投影再跑一次拒密或 redact。补测 PATCH+GET 不得见 secret。

### R8. body cap 只看 Content-Length

- **严重级别**：`high`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：
  - `api/app.py:527-538`：无 CL / `int()` 失败则 `call_next`
  - ChinaTax `records` 上限 10k，字段本身无字节帽
- **为什么重要**：
  - 叶工人单进程。chunked 或缺 CL 的 JSON 会在 Starlette 缓冲阶段把内存打满。VF84 的「413 before JSON parse」对无 CL 不成立。
- **审查判断**：
  - 有 CL 的超限路径是真的。作为 DoS 面仍 fail-open。
- **建议修法**：
  - 在 ASGI receive 上累计字节；超过 cap 截断并 413。CL 只是快路径。

### R9. vLLM 单例超时冻结且无 aclose

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/llm_adapters/local_vllm.py:206-215,223-226,242-245`：首次 `AsyncClient(timeout=...)` 后忽略后续 timeout；`probe` 用 `min(timeout, 5)`
  - `api/app.py:183-191,458-464`：live/`inference_probe_enabled` 时 `/ready` 先 probe；lifespan 只 `persistence.close()`
  - 默认 `trust_env=True`（httpx），与 acquisition 的 `trust_env=False` 不一致
- **为什么重要**：
  - 一次 `/ready` probe 可以把后续 generate 冻在 ~5s，触发 RETRYABLE → EXHAUSTED → salvage Claude（放大 R4）。连接池也不在关闭时释放。
- **审查判断**：
  - VF15「单例 client」落地了形状，丢掉了超时语义。P3-03 部分。
- **建议修法**：
  - `client.post(..., timeout=...)` 每请求覆盖。probe 用独立短超时 client 或 per-request timeout。lifespan `await adapter.aclose()`。`trust_env=False`。

### R10. Task cancel 不在同 TX 栅栏 Execution

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/task/task_commands.py:193-205`：只 CAS Task `cancelling` + 入 `cancel_execution` outbox
  - supervisor 串行：先 `run_once`（当前 handler）再 drain 后续 outbox（`workflow_supervisor.py:46-64`）
  - `accept_outcome` 以 Execution 状态为栅栏，不看 Task（`runtime_outcome.py` 成功路径）
  - `project_task_status_tx` 允许 `cancelling → succeeded`
- **为什么重要**：
  - S02：`cancelling` 只应走向 `cancelled`。180s/900s handler 在 cancel 收据之后仍可 success-win。对上游编排器，这是叶工人取消语义不可信。
- **审查判断**：
  - 在 VF62 保持串行时窗口最大（当前 handler 必须跑完才处理 cancel outbox）。不是 NS5 引入的新设计，但是 0820 宣称运行时安全收口后仍未封。
- **建议修法**：
  - cancel UoW 同时把当前 root Execution/running Process 标 `cancelling`，`accept_outcome` 拒绝 succeeded。或 supervisor 在 `run_once` 前先 drain cancel/gate outbox。

### R11. heartbeat 非取消异常会静默停跳

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/runtime/workflow/worker.py:148-162`：循环只捕 `CancelledError`；`heartbeat()` 抛错则任务结束，handler 继续
  - `test_heartbeat_keeps_lease_from_being_stolen`：lease=1s，0.8s 时 `recover`——租约尚未到期，**删掉 heartbeat 循环也会 `recovered==0`**
- **为什么重要**：
  - VF10 的生产条件是 30s lease vs 180/900s 推理。心跳任务一死，原 reclaim 双跑窗口回来；generate/vectorize `safe_replay=false` 会变成 `indeterminate-side-effect`，intake 则可能重放。
- **审查判断**：
  - 心跳存在，但「失败即 fence」没做；T04 测试不证命题。
- **建议修法**：
  - `except Exception: fenced.set(); handler_task.cancel(); return`。测试必须跨过 `lease_seconds`。

### R12. schema readiness 只探 `mkb_tasks`

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/persistence/migration_runner.py:159-163`：checksum 之后 `return "mkb_tasks" in tables`
  - D04 required 闭集 55+ 表；`/ready` 的 `obs_tables` 只查三张可观测表（`api/app.py:174-179`）
- **为什么重要**：
  - VF101 要的是「DROP 必选表 → schema 非 ready」。现在 DROP `mkb_outbox` / `mkb_vector_records` / `mkb_processes` 仍 `schema_migration=true`，claim 会在 CAS 里炸，而不是 503。
- **审查判断**：
  - `test_drop_mkb_tasks_fails_schema_readiness` 只打了他们特殊处理的那一张表。
- **建议修法**：
  - fail-closed 对照 D04 required 表名闭集（至少 processes/outbox/vector_records/intake_items/object 目录）。

### R13. VF36 digest≠bytes，rebuild 已依赖该谎言

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `acceptance_snapshot.py:149-185`：raw 与 clean 行共用 `refs["output_ref"]` / `output_size`，digest 却是语义 `raw_digest`/`clean_digest`
  - `src/runtime/intake/core.py:494-507`：rebuild 从该 envelope 读 `clean_text`
- **为什么重要**：
  - `sha256(read(handle)) != content_digest`。当前 ANN 命中走 generation artifact，所以「检索读到错误字节」尚未发生；但 rebuild 已经按「clean handle 里是 JSON envelope」这条私货工作。完成 VF45 瘦 envelope 或按 digest 做 CAS 读取，都会把 rebuild 打穿。
  - deferred-items 把它标成 `[true-bug] 未关` 是诚实的；closure 把它当 O4 余项则过宽——这是 S13 bytes-first 违例，不是「存储重复」。
- **审查判断**：
  - 不阻断「无 HITL 的 stub ingest 检索」主路径，但阻断「S13 身份可治理」。0820 长期治理目标未完成。
- **建议修法**：
  - raw/clean 分对象 promote。rebuild 按 digest+handle 读正文，禁止依赖 envelope 私货。

### R14. 标题进入 embed，查询侧不带 header

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - VF95：title 进入 `content_full` headers（`generation_construct.py:1324-1338`）
  - VF43：`_embed_bodies` 只在 `metadata_headers` 传入时剥 header；vectorize 仅 `metadata_refresh` 传入（`vectorize.py:161-197,461-472`）
  - 查询 embed 用裸 `query`（`retrieval_request.py`）
- **为什么重要**：
  - 两条「已修」VF 在主路径上互相拆台：向量空间带 `title:` 前缀，查询不带，cosine 系统性偏移。
- **审查判断**：
  - `test_title_enters_content_full` 直接调用 helper，看不见这条裂痕。
- **建议修法**：
  - 主路径也 body-only embed，title 留 facet；或 query 使用同一配方。不要两条同时「完成」。

### R15. NS5 短途测试大量假绿

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `tests/unit/test_ns5_phase2.py:96-111`：名叫 TTL，断言并发 coalesce，`ttl_seconds` 未使用
  - `tests/unit/test_ns5_phase1_runtime.py`：CLI 超时测的是 fixture 脚本文件仍在，不是 child pid；heartbeat 在租约到期前 recover
  - `tests/unit/test_ns5_phase3.py`：stdin/env/salvage/evidence/gate 多为集合归属或私有 gate，不跑生产 SUT
  - `tests/unit/test_ns5_phase4.py`：HTML 只断言 `"\n" in text`；purge 用 `model_construct` + 私有 assert
  - `tests/unit/test_ns4_readport_reports.py`：`inspect.getsource`，不实例化服务
  - `tests/unit/test_ns4_diagnostic_sidecar.py:24-33`：本地 `MkbError` 从不进入 `insert`
  - `tests/integration/test_ns5_turso_mainchain.py`：stub ingest，无 vectorize/retrieval
- **为什么重要**：
  - 0820 的收口纪律是「先红后绿、删 SUT 会红」。P6-01 拆了 `or True`，但 tautology 换成了源码扫描、未调用的局部对象、时间窗口不够的心跳。closure 用「unit+domain+integration ~440 PASS」当证据，测的是套件计数，不是 VF 谓词。
- **审查判断**：
  - 测试保真本身就是 0820 完整目标之一。假绿不拆，P1–P5 的回归不可信。
- **建议修法**：
  - 按 AP §8 的收口谓词重写 T01–T59：pid 不在、跨过 lease 的 heartbeat、TTL 顺序两次、salvage 占 NI、digest=bytes、XFF 空 CIDR。源码扫描只允许 architecture ratchet，不允许冒充行为测试。

### R16. `/docs` `/openapi.json` 匿名

- **严重级别**：`medium`
- **类型**：`security`
- **是否 blocker**：`no`
- **事实依据**：
  - `api/app.py:469`：`FastAPI(title=..., lifespan=lifespan)` 使用默认 docs
  - `main()` 绑 `127.0.0.1`（`:572`）；`create_app` 不强制该 bind
- **为什么重要**：
  - OpenAPI 枚举 `/internal/prompts` 写面。S16 把 operator 面放在内网+token。docker / `0.0.0.0` 时这是侦察面。VF79 后延在「只绑 loopback」时勉强成立，与「叶工人可被编排器当稳定依赖」不一致。
- **审查判断**：
  - 关 docs 是一行。后延成本高于修复成本。
- **建议修法**：
  - `docs_url=redoc_url=openapi_url=None`，或挂 `require_operator_token`。

### R17. UoW `BEGIN` 在 try 外

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `src/persistence/uow.py:26-31`：`await asyncio.to_thread(connection.execute, begin_sql)` 然后才 `try`
  - 取消 `to_thread` 不能撤销已经在工作线程执行的 `BEGIN IMMEDIATE`
  - Turso 无对应 cancel 测试
- **为什么重要**：
  - VF1 的症状就是唯一连接停在未结事务。body cancel 已覆盖；BEGIN/rollback 的 BaseException 窗口还在。
- **审查判断**：
  - P1-01 主体成立，边未封。
- **建议修法**：
  - BEGIN 纳入同一 try；任何未 commit 的退出都 shield-rollback，不确定则 discard。rollback 也捕 `BaseException`。

### R18. `outbox.dead` 无指标、trace 被替换

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `runtime_outbox.py:357-377`：写 `outbox.dead` 事件后 `getattr(self, "metrics", None)`——`WorkflowRuntime` 未注入 metrics
  - `trace_uuid=uuid7()` 新根，违反 S15「root 不替换」
- **为什么重要**：
  - VF73 要可观测死信。事件在库里，`/metrics` 上 `mkb_outbox_dead_total` 恒 0，告警目录是空壳。按 task/trace 拉时间线看不到毒丸。
- **审查判断**：
  - 毒丸不再冻 supervisor（VF61 成立）。可观测半修。
- **建议修法**：
  - 注入 `MetricRegistry`；沿用 outbox/process 的业务 `trace_uuid`；UPDATE 检查 `rowcount==1`。

### R19. CLI stdout 上限在 `communicate()` 之后

- **严重级别**：`medium`
- **类型**：`platform-fitness`
- **是否 blocker**：`no`
- **事实依据**：
  - `claude_cli.py:328-340`：先 `communicate()` 再比 `CLAUDE_CLI_STDOUT_LIMIT_BYTES`
  - terminate 不在 `finally`/`shield` 中
- **为什么重要**：
  - VF9 要有界 stdout + 超时必杀。内存 DoS 发生在检查之前；取消发生在 `_terminate_process` 中可能留下僵尸。
- **审查判断**：
  - timeout→kill 路径存在。T03 测试不看 pid。
- **建议修法**：
  - 有界读或 `limit`；`finally: await asyncio.shield(_terminate_process(...))`。测试断言 `process.returncode is not None`。

### R20. Facade 重试再获取失败时 `release(None)`

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `facade.py:385-409`：RETRYABLE 时先 `release(lease)`，再 `lease = try_acquire()`；若 `None` 抛 BACKPRESSURE，`finally: release(lease)` 此时 lease 为 `None` → `lease.capability` AttributeError
- **为什么重要**：
  - 闸满本应是干净的 `INFERENCE_BACKPRESSURE`，会被打成 `INFERENCE_INTERNAL_UNEXPECTED`，再被 salvage 矩阵吃掉（放大 R4）。
- **审查判断**：
  - VF22 放 lease 再 sleep 的主路径是对的；再获取失败的收尾不对。
- **建议修法**：
  - `finally` 仅当 `lease is not None` 才 release。

---

## 3. In-Scope 逐项对齐审核

> 对照 NS5 AP §2.1 / §3 与 closure 收口表。结论：`done | partial | missing | stale | out-of-scope-by-design`。

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 | P1-01 VF1 UoW cancel | `partial` | body cancel 成立；BEGIN 在 try 外（R17）；无 Turso cancel 测 |
| S2 | P1-02 VF2/VF3 sidecar + CW 诚实 | `partial` | sidecar 串行 IMMEDIATE 成立；CW 诚实位打死默认 `/ready`（R1）；probe 不 restore journal_mode |
| S3 | P1-03 VF9 CLI kill | `partial` | timeout/cancel 调 terminate；stdout 帽在 communicate 后（R19）；测试不看 pid |
| S4 | P1-04 VF10 heartbeat | `partial` | 循环存在；异常停跳（R11）；T04 未跨过 lease |
| S5 | P1-05 VF61 outbox 毒丸 | `done` | 先 lease 再 parse；非法 JSON 标 dead；drain 继续 |
| S6 | P1-06 VF63 retirement | `done` | deactivate/delete/missing 会 abandon；其它 INVALID_TARGET 仍可能占队 |
| S7 | P1-07 VF64–67 GC | `partial` | 两阶段 unlink 落地；TX1→unlink 窗口可丢字节；多处 catalog 查找仍不跳 tombstone |
| S8 | P1-08 VF68 `_pending` pop | `done` | finally pop + discard + 1024 帽 |
| S9 | P1-09 VF69 scanner | `done` | 捕 Exception 不捕 CancelledError |
| S10 | P1-10 VF70 claim drain | `partial` | 最多 64 条过期；仍可能在有活行时 return None |
| S11 | P2-01 VF4 rowcount | `partial` | Turso wrapper 在；`changes()` 语义与 `-1` 未测 |
| S12 | P2-02 VF5/VF7 ledger+014 | `partial` | ledger 参数化成立；014 只加连字符，version nibble 仍随机 |
| S13 | P2-03 VF8 时间戳 us | `done` | Python `utc_now` timespec 对齐；VIEW 仍 `%f` 但不在 claim 热路径 |
| S14 | P2-04 VF71/72/73 jitter/dead/gate | `partial` | process jitter 有；dead 事件有、指标无（R18）；cancelling gate ACK 有 |
| S15 | P2-05 VF94 ready TTL | `partial` | 仅 in-flight coalesce；TTL 死代码 |
| S16 | P2-06 VF98 bootstrap 可观测 | `partial` | `bootstrap_failures` 能 503；计数器打错 series |
| S17 | P2-07 VF99/102/103 指纹/extras/409 | `partial` | created_at 已排除；Team PK 仍 500；PATCH `{}` 清空成立 |
| S18 | P2-08 VF100 脱敏 | `partial` | Process 路径走 redact；Execution `final_error_message` 仍截断原文 |
| S19 | P2-09 VF101 ready 诚实 | `partial` | identity 非 JSON 失败；schema 只探 mkb_tasks（R12） |
| S20 | P3-01 VF11/12/13 salvage/OVERFLOW | `partial` | OVER_BUDGET 键已加；salvage 仍同 Process CLI（R4） |
| S21 | P3-02 VF14 prompt state | `partial` | `role` 非空时 fail-closed；`role=None` 仍可读盘 |
| S22 | P3-03 VF15/22/24 client/lease/408 | `partial` | 408/425 + 放 lease 成立；timeout 冻结（R9）；`release(None)`（R20） |
| S23 | P3-04 VF16 stdin/env | `partial` | 正文 stdin；env 是 MKB_* 否认名单不是 allowlist |
| S24 | P3-05 VF17 证据 process_uuid | `partial` | 有分桶；有 `"_"` 回退（R5） |
| S25 | P3-06 VF18 schema freeze | `partial` | L4 SHA 有；generate 仍 `load_layered_json_schema()` 读盘 |
| S26 | P3-07 VF19 EXHAUSTED 可重试 | `done` | 进入 `_RECOVERABLE_ERROR_CODES`；与 R4 组合成经济上近乎无界 |
| S27 | P3-08 VF21 CLI gate | `partial` | 生产注入同一 gate；salvage 占的是内存 `cli` 计数不是 NI 行 |
| S28 | P3-09 VF26 拒二进制 | `partial` | CLI clean 拒非 text；`errors='replace'` 仍在 stdout decode |
| S29 | P3-10 VF96 同源 caps | `partial` | 同一常数注入；`structured_generate` 与 `text_generate` 各吃一份 local_running |
| S30 | P4-01 VF27 vectorize fail-closed | `done` | 超预算 422，不缩 required |
| S31 | P4-02/03 VF28/29 HTML/锚点 | `done` | 换行保留；单调 cursor |
| S32 | P4-05 VF34/35/36 预算/身份/digest | `partial` | cap/同 key 有切片；VF36 仍共享 handle（R13） |
| S33 | P4-08 VF40 human_review | `partial` | 检索 fail-closed；approve 不激活（R2） |
| S34 | P4-10 VF44/55/58 generation CAS | `partial` | 指针单调 + 015；仍 UPDATE indexed（R3） |
| S35 | P4-13 VF47/51/52 召回/空间 | `partial` | LIMIT+1 与 LIVE mismatch 成立；VF52 仍 409 default |
| S36 | P4-14/15/16 pack/team/purge | `done` | 分数优先、team 应用层闸、禁单通道 purge |
| S37 | P5-01 VF75 XFF | `partial` | 公网 peer 不能伪造内网；空 CIDR 仍信私网 XFF（R6） |
| S38 | P5-02 VF76 限流 overflow | `done` | overflow 拒绝；异常 fail-closed（比 S16 fail-open 更严） |
| S39 | P5-03 VF78 extras | `partial` | CREATE 拒密；PATCH 不拒（R7） |
| S40 | P5-04/05/06 sqlite/Starlette/mapped-v6 | `done` | 双因子、Starlette 1.6.0、ipv4_mapped 递归 |
| S41 | P5-07 VF83 audit undo | `partial` | undo 存在；overflow key 对不上；无「第 2 次仍 503」测试 |
| S42 | P5-08 VF84 body cap | `partial` | 有 CL 则 413；无 CL 放行（R8） |
| S43 | P6-01 VF85 tautology | `partial` | `or True` 已删；源码扫描/未调用对象仍绿（R15） |
| S44 | P6-02 VF87 ruff | `done` | 以 closure 自称与 pyproject select 为准；本轮未复跑 |
| S45 | P6-03 VF91 CW unit | `partial` | skipIf 避免两 False 绿；从未断言 CW True |
| S46 | P6-04 VF93 wheel SQL | `done` | package-data 含 001–015；prompts/config 仍不在 wheel |
| S47 | P6-05 mega/soak/closure | `partial` | sidecar 80 insert 真 soak；T60 被换成 stub ingest；AP 仍 `executing` |
| S48 | S5 VF-ledger §6 append | `partial` | 有 append；§6.1 把 VF85 写成「代码落地」与 §6.2 自相矛盾 |

### 3.1 对齐结论

- **done**: `15`
- **partial**: `32`
- **missing**: `0`
- **stale**: `0`
- **out-of-scope-by-design**: `1`（见 §4；此处不把 O3 项计进 S 表）

> 这更像「不可恢复 IO 的骨架补丁已打上，但默认就绪、HITL、serving 不可变、车道 SSOT、安全默认值与测试保真仍未收口」，而不是 completed。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | VF20/25/32/33/57 acknowledge | `遵守` | 未见本轮改 SupplyFence/逐字 Construct 合同 |
| O2 | VF6/VF92 stale-rejected | `遵守` | 未回头「修复」executescript 回退或检索 tautology 空集 |
| O3 | VF23 billing / VF88 GPU / VF97 未接线 / VF86 sqlite3 e2e | `遵守` | 仍后延；e2e 仍 sqlite3-on-Turso。不得用 T60 替代品宣称 mega 绿 |
| O4 | VF30.r PDF 库 / VF37.r 默认切 stub / VF41.r 全树 / VF46.r 全程 jsonschema / VF66.r 目录 SSOT / VF91.r 真机 CW | `遵守` | 切片边界清楚 |
| O5 | VF62 重叠 `run_once` 未开 | `遵守` | 旗标 false；但旗标从未被读取，属于「结构未接」而非「安全地关掉」 |
| O6 | VF36/VF52/VF40.r 被 closure 标 under-delivery | `部分违反` | 登记后延是诚实的；把 VF40 只当成「缺 pending 词」则掩盖了 R2 断点。VF36 被 rebuild 依赖，不能当纯存储债 |
| O7 | VF77 HTML `javascript:` | `遵守` | sanitizer 仍放行；当前只抽 text、无产品 UI。若 HTML 被存储/回出必须 reopen |
| O8 | VF79 `/docs` | `误报风险` | 作为「公网 SaaS 才要关」后延，对叶工人过宽。R16 建议本轮顺手关，不把它升成与 R1 同级的宪法冲突 |
| O9 | 把 VF86 红当成生产行为已证明 | `遵守` | closure 明确禁止；T60 替代测试没有越权宣称 441/441 |
| O10 | `[true-bug]` 改写成 deferred | `部分违反` | VF36/VF52 在 deferred-items 仍标 `[true-bug] 未关`——账是诚实的。问题是 NS5 工作项把它们从 in-scope 滑到「下游」而 AP §0.4 禁止用 deferred 规避本阶段欠账。本轮审查把 R13 标 non-blocker 是因为检索主路径暂未读错字节，**不等于同意改 class** |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：NS5 第1轮修复让「唯一连接被 cancel 冻死、毒丸冻 supervisor、vectorize 静默缩 proof、限流全局 fail-open」这类不可恢复洞有了真实补丁，但 **0820-review 的完整目标未达成**。默认宪法画像不能就绪，HITL 不能发布，serving 行仍可变，车道/证据/XFF/PATCH 仍有断点，测试保真不能支撑「P1–P6 ✅」。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **R1**：拆开 `concurrent_writes` 探针与准入，使默认 Turso + IMMEDIATE 叶工人可以 `/ready` 并 claim；测试不得只靠 waiver 证明就绪。
  2. **R2**：公共 `consume_gate_decision` 必须激活/关闭 HITL Item；补 e2e 断言 lifecycle 与 publication。
  3. **R3**：禁止 UPDATE 已 indexed 的向量行；补「再 vectorize 不得打穿 serving COUNT」。
  4. **R4 + R5**：salvage 占 NI 或 fail-closed；删除证据 `"_"` 回退。
  5. **R6 + R7**：空 CIDR 不信 XFF；PATCH extras 拒密。
  6. **R15**：重写会在 SUT 删除后仍绿的 NS5 短途测试，至少覆盖 R1–R7 的谓词。
- **可以后续跟进的 non-blocking follow-up**：
  1. R8 实际读入 cap、R9 vLLM timeout/aclose/`trust_env`、R16 关 docs。
  2. R10 cancel 同 TX 栅栏、R11 心跳失败即 fence、R12 D04 表闭集、R17 BEGIN 纳入 try。
  3. R13 双 CAS 对象、R14 embed/query 配方、R18 dead 指标与 trace、R19/R20 CLI/Facade 收尾。
  4. VF52 namespace 分键、VF62 重叠 worker（必须先有 R11+R4）、VF86 harness、VF66.r 目录 SSOT——保持后延，但不要用 stub ingest 冒充 T60。
- **建议的二次审查方式**：`same reviewer rereview`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

### 5.1 对「0820 完整目标」的直接回答

| 目标 | 本轮判断 |
|------|----------|
| 完成 0820-review 找到的全部问题的修复 | **否**。75 条 `[true-bug]` 里，不可恢复 IO 的主干多已动刀，但 VF11/17/36/40/44/75/78/85 等在生产路径上仍残；默认就绪被 P1-02 自己打死。 |
| 完成 MKB 长期治理型更新与维护 | **否**。就绪语义、HITL 生命周期 SSOT、serving 行不可变、叶工人取消语义、S16 默认不信转发头、测试保真——这些是治理，不是「再补一个 if」。 |

叶工人身份（S01）在路由形状上成立：无公开 Execution/Process 写面、六态轮询、token 单轴。把它交给上游编排器当稳定依赖，**在默认 Settings 下做不到**。

本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
