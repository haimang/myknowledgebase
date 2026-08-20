# Nano-Agent 行动计划

> 服务业务簇: `MKB / NS5 0820 first-round verified-findings 修复`
> 计划对象: 按 VF-ledger 批次 DAG 修复 HEAD 上 87 条 in-scope VF（75 `[true-bug]` + 12 `[partial-delivery]`）
> 类型: `modify`
> 作者: `Grok`
> 时间: `2026-08-20`
> 文件位置: `docs/plan/new-start/NS5-0820-bug-fixes.md`
> 上游前序 / closure:
> - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md`（`v0.4` / `triaged`；UF1–UF103 ↔ VF1–VF103）
> - `docs/closure/new-start/NS4-generation-evidence-plane-closure.md`
> - `docs/closure/new-start/deferred-items-ledger.md`（NS1-V11 / NS2-O1 / NS2-GPU）
> 下游交接:
> - NS5 阶段 final closure（本 AP §10；落盘 `docs/closure/new-start/NS5-0820-bug-fixes-closure.md`）
> - VF-ledger §6 处置回填（append-only；不改写 ledger §0–§5）
> - §5.4 剩余切片与 `[true-deferred]` 仍交 deferred-items-ledger / 后继 charter（billing / harness / PDF / S06 全树 / constitution e2e）
> 关联设计 / 调研文档:
> - `docs/baseline/domain-truth/S03-workflow-engine.md`（claim / lease / fencing / outbox）
> - `docs/baseline/domain-truth/S08-embedding-vectorization.md` / `S09-lsrag-index.md` / `S10-lsrag-retrieval.md`
> - `docs/baseline/domain-truth/S11-inference-runtime.md` / `S12-turso-persistence.md` / `S13`（CAS / T-O-120）
> - `docs/baseline/domain-truth/S16-security-trust-boundary.md`（token / egress / audit / extras）
> - `README.md`（K1–K14；433/8；未接线合同）
> 冻结决策来源:
> - `docs/code-review/0820-review/VF-ledger-0820-1st-review.md` §1 / §4.1 / §5.2–§5.4（**只读引用**；本 action-plan 不填写 Q/A，不改 VF class/disposition）
> grounding 来源:
> - VF-ledger §3 当前 `file:line` + 本 AP §7 内置锚区
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `executing`

---

## 0. 执行背景与目标

0820 四审合并已完成：154 条原始 finding → 103 条 UF/VF。复核后 **75 `[true-bug]` + 12 `[partial-delivery]`** 是本阶段欠账；9 条 `[true-deferred]` 与 7 条 `n/a`（含 2 条 stale-rejected）不得改写成「本轮也修」。ledger §5.1 把修复顺序钉死为：**先封进程/数据不可恢复洞 → serving 正确性 → 车道/证据/安全 → 假绿测试与包装**。§5.3 给出 6 个批次与依赖边。本 AP 把这些冻结批次落成可执行 Phase DAG，并把每一条 in-scope VF 绑到唯一工作项。

本计划不重开 0820 的 verdict。`[true-bug]` 禁止降级成 deferred。每条 code fix 必须先有会红的断言。成功标准是 **单例连接在 cancel 后可再 BEGIN、publication proof 的 required set 不得被静默缩小、唯一 supervisor 不得被一条坏 outbox 挡住 claim/repair、检索不得按 uuid7 前缀丢掉新知识**，不是「测试计数变绿」。

- **服务业务簇**：`NS5`
- **计划对象**：0820 VF-ledger 本阶段必修缺口
- **本次计划解决的问题**：
  - 运行时不可恢复：UoW 取消污染唯一连接、sidecar native abort、CLI 僵尸、outbox 毒丸冻 supervisor、GC unlink/rollback 分裂、retirement 死循环
  - serving 假完整：live vectorize 丢层仍签 proof、HTML 抹平换行、重复锚点、UUID 截断 1000、单通道 purge 灭世代
  - 车道/证据/安全：salvage 不是运输 SSOT、30s lease 无 heartbeat、payload_extra 可存 secret、限流 degraded 永久 fail-open
  - 验证不可信：tautology 假绿、ruff 9 errors、wheel 缺 migration SQL
- **本次计划的直接产出**：
  - 6 个串行（可部分并行）Phase，覆盖 87 条 in-scope VF
  - 对应 falsifiable 测试（§8）与每 Phase 收口
  - VF-ledger §6 append + NS5 closure；§5.4 切片登记到 deferred-items-ledger
- **本计划不重新讨论的设计结论**：
  - `[true-bug]` 本轮必修，禁止改写成 `[true-deferred]`（VF-ledger §0.4）
  - VF20/VF25/VF32/VF33/VF57 = `acknowledge` / by-design，不改合同（VF-ledger §4.1 / §5.2 ack）
  - VF6/VF92 = `stale-rejected`，不修（VF-ledger §4.3）
  - VF23 billing 恒真本阶段只承诺 always-permit（NS2-O1 / README K10）
  - VF86 e2e sqlite3↔Turso 由 owner 冻结为 NS1-V11 harness charter
  - VF97 browser/OCR/Vision 未接线，README 已披露，本轮不注入
  - 目录当 CAS SSOT 已 defer（T-O-120 / VF66.r）
  - SupplyFence = composition allow-list 而非 L1 winners（VF20）

---

## 1. 执行综述

### 1.1 总体执行方式

**先封不可恢复 IO，再诚实持久化，再接线推理车道，再修 serving 正确性，安全边界可与车道/serving 并行，最后拆假绿并打包装。** 顺序消费 VF-ledger §5.3 六批次。唯一 DAG 调整：把 **VF10（heartbeat）从批次 3 提前到 Phase 1**，作为 VF62 并发化的硬前置——否则 Phase 1 打开 per-pool worker 会把 VF10 的条件竞态变成必现双跑。VF62 在 VF10 落地前必须保持 `max_running=1`（结构可先改，重叠执行不得合并）。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 运行时安全 / 不可恢复 IO | `XL` | UoW / sidecar / CLI kill / heartbeat / outbox / GC / retirement / claim drain | `-` |
| Phase 2 | 持久化诚实与平台卫生 | `L` | rowcount、ledger 参数化、014 UUID、时间戳、outbox.dead、ready 缓存、身份/脱敏 | Phase 1 |
| Phase 3 | 推理 / 车道 / 证据 | `L` | salvage SSOT、OVER_BUDGET、CLI 门限、schema freeze、EXHAUSTED、统一 DispatchCaps | Phase 1（VF9/VF1/VF10） |
| Phase 4 | 摄取 / 结构 / 检索 serving | `XL` | vectorize fail-closed、HTML/锚点、generation CAS、UUID 截断、purge proof、team fence | Phase 1+2 |
| Phase 5 | 安全边界 | `M` | trusted-proxy、限流 overflow、extras 密钥、sqlite 后门、Starlette、audit sampler、body cap | Phase 1 |
| Phase 6 | 测试保真与包装 | `M` | 拆 tautology、ruff、CW 单元诚实、wheel package-data、mega/soak、closure | Phase 1–5 |

DAG（可并行窗口）：

```text
P1 ──► P2 ──► P3 ──► P4 ──► P6
 │                         ▲
 └──► P5 ──────────────────┘
```

P3 不依赖 P2 的 DDL（可在 P2 收口后立即开始；禁止与 P1 重叠）。P5 在 P1 UoW 稳定后即可与 P2/P3/P4 并行。P6 必须等前五路代码进主分支后再拆假绿，否则 tautology 修补会锁住未修行为。

### 1.3 Phase 说明

1. **Phase 1 — 运行时安全 / 不可恢复 IO**
   - **核心目标**：进程唯一连接、唯一 supervisor、物理对象与子进程在故障后仍可前进。
   - **为什么先做**：ledger §5.3 批次 1。后续正确性测试若跑在坏连接 / 冻 supervisor / 缺字节 CAS 上会抖动。
2. **Phase 2 — 持久化诚实与平台卫生**
   - **核心目标**：CAS 行数、迁移 ledger、时间精度、dead 可观测、readiness 不切 journal_mode。
   - **为什么放在这里**：依赖 Phase 1 的 cancellation-safe UoW；为 Phase 4 的 generation 单调与时间比较垫底。
3. **Phase 3 — 推理 / 车道 / 证据**
   - **核心目标**：dispatch_pool 成为运输 SSOT；CLI 可取消且有门限；失败证据不串台。
   - **为什么放在这里**：依赖可 kill 的 CLI（VF9）与可滚动 UoW（VF1）；heartbeat 已在 P1。
4. **Phase 4 — 摄取 / 结构 / 检索 serving**
   - **核心目标**：publication proof 与检索召回不再说谎。
   - **为什么放在这里**：依赖 P1 CAS/GC 与 P2 时间戳/rowcount；serving 合同在稳定存储上才能测。
5. **Phase 5 — 安全边界**
   - **核心目标**：代理后内外网隔离、限流 fail-closed、extras 拒 secret、审计写失败不耗桶。
   - **为什么放在这里**：只依赖 P1 UoW；与 serving 无数据依赖，故可并行。
6. **Phase 6 — 测试保真与包装**
   - **核心目标**：删 tautology、ruff 清零、wheel 含 `*.sql`、mega/soak 收口。
   - **为什么放在这里**：假绿不拆则 P1–P5 回归不可信；包装不修则安装路径无法证明。

### 1.4 执行策略说明

- **执行顺序原则**：按 §1.2 DAG。禁止先开 VF62 重叠 `run_once` 再补 VF10。禁止在 P6 之前把「全量 pytest 绿」当收口（VF86 仍 owner-gated）。
- **风险控制原则**：每个 `[true-bug]` 先写 RED 测试再改生产代码。高风险项（UoW / sidecar / outbox / GC 两阶段 / vectorize proof / generation CAS / extras）必须有失败/降级路径。
- **测试推进原则**：Phase 内短途 unit → Phase 收口 spike → P6 mega（生成+检索主链）+ soak（sidecar 4 线程、lease reclaim）。详见 §8。
- **文档同步原则**：代码进主分支后窄回填 README K 项与 deferred-items-ledger；VF-ledger 只 append §6，不改 §0–§5。
- **回滚 / 降级原则**：UoW / sidecar / supervisor 若引入新死锁，回退该 Phase 提交并保持单写者 + 诚实 `concurrent_writes=false`，禁止探针假绿。wheel 包装失败不得声称可发布。

### 1.5 本次 action-plan 影响结构图

```text
NS5-0820-bug-fixes
├── Phase 1: 运行时安全
│   ├── src/persistence/{sqlite_port,turso/port,engine,sidecar}.py
│   ├── src/runtime/inference/claude_cli.py
│   ├── src/runtime/workflow/{worker,runtime_core,runtime_outbox,workflow_supervisor}.py
│   └── src/services/{object_gc,index_retirement,artifacts}.py + src/storage/local_store.py
├── Phase 2: 持久化诚实
│   ├── src/persistence/{turso/port,migration_runner}.py + migrations/014_*.sql
│   ├── src/runtime/workflow/{runtime_outcome,runtime_gates,runtime_outbox}.py
│   └── api/app.py + src/runtime/{task,health}.py + src/storage/local_store.py
├── Phase 3: 推理车道
│   ├── src/runtime/intake/{generation_construct,generation_live,generation_evidence,clean_preflight}.py
│   ├── src/runtime/inference/{facade,claude_cli}.py + src/llm_adapters/local_vllm.py
│   └── src/runtime/workflow/dispatch.py + src/services/{config_snapshots,billing}.py
├── Phase 4: serving 正确性
│   ├── intake/text.py + src/services/lsrag_compiler/{adopt,construct,validate}.py
│   ├── src/runtime/intake/{vectorize,vector_publish_commit,acquisition_*,acceptance_*}.py
│   └── src/services/retrieval/* + src/services/vector_purge.py + retrieval_access.py
├── Phase 5: 安全边界
│   ├── src/runtime/security.py + api/dependencies.py + api/app.py
│   └── src/contracts/{common,api}/models.py + pyproject.toml/uv.lock
└── Phase 6: 测试与包装
    ├── tests/unit/test_ns4_* + test_turso_driver.py + test_object_gc.py
    ├── pyproject.toml package-data + ruff
    └── mega/soak + closure + VF-ledger §6
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** 全部 75 条 `[true-bug]` 按 §3 工作项修复（默认 `fix`）
- **[S2]** 全部 12 条 `[partial-delivery]` 的本轮切片（VF2/VF30/VF37/VF41/VF46/VF62/VF66/VF73/VF91/VF93/VF95/VF96）；剩余切片登记 §2.2
- **[S3]** 配套 falsifiable 测试：先 RED 后绿；P6 拆除 VF85 tautology 簇
- **[S4]** wheel 打入 `src/persistence/migrations/*.sql`；`ruff check .` 清零
- **[S5]** 窄回填 README 已知问题与 deferred-items-ledger；VF-ledger §6 append；NS5 closure

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** VF20/VF25/VF32/VF33/VF57 acknowledge / by-design（不改合同）
- **[O2]** VF6/VF92 stale-rejected（不修）
- **[O3]** `[true-deferred]`：VF23 billing、VF74 claim_token、VF77 HTML XSS、VF79 /docs、VF86 NS1-V11 harness、VF88 live GPU、VF89 全仓禁 grep、VF90 coverage fail_under、VF97 browser/OCR/Vision
- **[O4]** `[partial-delivery]` 剩余切片：VF30.r 完整 PDF 库、VF37.r 生产默认切出 stub、VF41.r S06 全树、VF46.r 全程 jsonschema SSOT、VF66.r 目录 SSOT（T-O-120）、VF91.r 真机 CW+native_vector e2e
- **[O5]** 实现计费、多副本 fencing token、公网 bind 硬化、ANN 生产接线（本轮只 fail-closed / 拒绝未接线 `native_ann`）

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 75 `[true-bug]` | `in-scope` | ledger §0.4 本阶段欠账 | 无；漏修升 blocker |
| 12 `[partial-delivery]` 本轮切片 | `in-scope` | ledger §5.2 `fix`/`partial-fix` | 切片完成后余项见 5.4 |
| VF10 heartbeat | `in-scope`（提前到 P1） | VF62 并发化硬依赖 | 若 VF62 改为永续 serial 则可退回 P3 |
| VF23 billing | `out-of-scope` | NS2-O1 always-permit | billing AP 立项 |
| VF86 sqlite3 e2e | `out-of-scope` | owner 冻 NS1-V11 | harness charter |
| VF97 browser/OCR | `out-of-scope` | README 未接线 | 注入 Fetcher + readiness |
| VF6 executescript 回退 | `out-of-scope` | stale-rejected | pyturso 失去 executescript |
| 目录 CAS SSOT | `defer / depends-on-design` | T-O-120 | owner 授权磁盘 SSOT |
| native ANN 生产 | `defer / depends-on-design` | README 已标 scan profile | VectorSearchPort 立项 |
| VF81 Starlette bump | `in-scope` | 兼容 FastAPI 的最小升级 | 若 0.115.12 无法吃 starlette≥1.0.1 → 升级 FastAPI 主版本 |

---

## 3. 业务工作总表

> 硬地板：每项含 `涉及文件（file:line）` / `收口目标` / `测试映射`。编号 `P{phase}-{nn}`。VF 清单是绑定权威，一项可覆盖多条 VF。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | cancellation-safe UoW（VF1） | `update` | `src/persistence/sqlite_port.py:83-95`；`src/persistence/turso/port.py:87-99` | cancel/commit 失败后下一 `BEGIN IMMEDIATE` 成功；不确定则丢弃连接 | `NS5-T01` | `high` |
| P1-02 | Phase 1 | Turso 写路径诚实 + sidecar 串行（VF2/VF3） | `update` | `turso/port.py:63-91`；`engine.py:13-40`；`sidecar.py:23-57`；`observability.py:158-171`；`api/app.py:309-314` | readiness 与真实 BEGIN 一致；4×20 sidecar insert 不得 exit 134 | `NS5-T02` | `high` |
| P1-03 | Phase 1 | Claude CLI timeout kill/wait（VF9） | `update` | `src/runtime/inference/claude_cli.py:288-304` | timeout/cancel 后 child pid 不在；stdout 有界 | `NS5-T03` | `high` |
| P1-04 | Phase 1 | heartbeat + 有界 worker（VF10/VF62） | `update` | `worker.py:45-53`；`runtime_core.py:546-558`；`workflow_supervisor.py:39-51`；`dispatch.py:12-18` | lease=1s handler=2s 败者 fenced；VF10 未绿之前 `run_once` 不得重叠 | `NS5-T04` | `high` |
| P1-05 | Phase 1 | outbox 毒丸隔离（VF61） | `update` | `runtime_outbox.py:38-59,77-104`；`workflow_supervisor.py:39-51` | 非法 JSON 标 dead；同 tick 仍 claim 下一条 Process | `NS5-T05` | `high` |
| P1-06 | Phase 1 | retirement 失效 intent 收口（VF63） | `update` | `src/services/index_retirement.py:314-327,396-406` | 100 stuck + 1 健康 → 第二次 scan 收到健康 intent | `NS5-T06` | `high` |
| P1-07 | Phase 1 | GC 两阶段 + 锁 + released_at + tombstone 查找（VF64/65/66/67） | `update` | `src/services/object_gc.py:145-269`；`local_store.py:67-74,120-132`；`artifacts.py:131-149`；`lifecycle_apply.py:270-300` | unlink 在写锁外；rollback 不丢无信号字节；lookup 跳过 tombstone | `NS5-T07` | `high` |
| P1-08 | Phase 1 | `_pending` pop（VF68） | `update` | `src/services/artifacts.py:44-120`；`src/runtime/intake/core.py:127-139` | 成功/失败/取消后 map 空 | `NS5-T08` | `medium` |
| P1-09 | Phase 1 | scanner 异常不退出（VF69） | `update` | `src/runtime/object_gc.py:42-50`；`src/runtime/index_retirement.py:40-46`；`api/app.py:417-446` | `scan_once` 抛一次后 task 仍 running | `NS5-T09` | `medium` |
| P1-10 | Phase 1 | claim 排空过期项（VF70） | `update` | `src/runtime/workflow/runtime_core.py:353-379` | 3 过期 + 1 活 → 一次 `claim_next` 领到活 Process | `NS5-T10` | `medium` |
| P2-01 | Phase 2 | 归一化 pyturso rowcount（VF4） | `update` | `turso/port.py:24-25`；`runtime_core.py:462-477,553-558` | stale UPDATE `rowcount==0`；匹配 CAS `==1` | `NS5-T11` | `medium` |
| P2-02 | Phase 2 | ledger 参数化 + 014 UUID 改写（VF5/VF7） | `update`/`migrate` | `migration_runner.py:65-71,132-138`；`migrations/010_spark_vl_embed_model_key.sql:12`；新建 `014_*.sql` | ledger INSERT 无 f-string；升级后 model_uuid 为带连字符 UUID | `NS5-T12` | `medium` |
| P2-03 | Phase 2 | 时间戳统一 us（VF8） | `update` | `src/runtime/time.py:10-23`；`artifacts.py:140,148` | `%f` 写入不得被 us cutoff 排除 | `NS5-T13` | `low` |
| P2-04 | Phase 2 | retry jitter + 取消 gate noop + outbox.dead 事件（VF71/72/73） | `update` | `runtime_core.py:62,80`；`runtime_outcome.py:137-151`；`runtime_gates.py:186-187`；`runtime_outbox.py:90-105,331-341`；`events.py:58-59` | 两次 retry 的 next_retry_at 不同；cancelling gate 行 done；dead 有事件+指标 | `NS5-T14` | `medium` |
| P2-05 | Phase 2 | /ready 短 TTL、claim 不切 journal_mode（VF94） | `update` | `turso/port.py:100-130`；`engine.py:13-40`；`workflow_supervisor.py:26,68-72`；`api/app.py:166-197` | idle 1s 不得 ~20 次 `PRAGMA journal_mode=mvcc` | `NS5-T15` | `medium` |
| P2-06 | Phase 2 | bootstrap/retention 失败可观测（VF98） | `update` | `api/app.py:405-414,517-523` | PROMPT_NOT_REGISTERED → `/ready` 503 且计数器 +1 | `NS5-T16` | `low` |
| P2-07 | Phase 2 | Task 指纹 / extras 清空 / PK 409（VF99/102/103） | `update` | `task_create.py:53-114`；`api/models.py:45-73,267-286`；`teams.py:39-103` | 仅 created_at 变化 → replay；PATCH `{}` 清空 extras；并发同 UUID → 409 | `NS5-T17` | `medium` |
| P2-08 | Phase 2 | Process/Outbox 错误脱敏（VF100） | `update` | `worker.py:52-60`；`runtime_outcome.py:443-452`；`runtime_outbox.py:102-104,331-341` | `error_message` 无 token/绝对路径 | `NS5-T18` | `medium` |
| P2-09 | Phase 2 | object/schema readiness 真校验（VF101） | `update` | `local_store.py:41-49,134-139`；`migration_runner.py:147-155` | identity 非 JSON → storage 非 ready；DROP `mkb_tasks` → schema_migration false | `NS5-T19` | `medium` |
| P3-01 | Phase 3 | salvage/pool/OVER_BUDGET SSOT（VF11/12/13） | `update` | `generation_construct.py:81-180,270-284`；`runtime_core.py:300-315`；`config_snapshots.py:573-591`；`dispatch.py:20-36` | salvage 占 NI 或 fail-closed；urgent+explicit local 可 salvage；超预算 construct 溢流 NI | `NS5-T20` | `high` |
| P3-02 | Phase 3 | prompt 缺 state fail-closed（VF14） | `update` | `generation_construct.py:351-370` | `state=None` → `PROMPT_NOT_REGISTERED` | `NS5-T21` | `medium` |
| P3-03 | Phase 3 | vLLM 单例 client + 放 lease 再 sleep + 408/425（VF15/22/24） | `update` | `local_vllm.py:66-98,187-215`；`facade.py:262-349,486-487`；`api/app.py:225-252` | 两次 embed 共用 client；cap=2 sleep 期间第三请求不得见满门；408→RETRYABLE | `NS5-T22` | `medium` |
| P3-04 | Phase 3 | CLI stdin-only + env allowlist（VF16） | `update` | `claude_cli.py:59-62,149-152,281-298`；`config.py:15-17` | 100-byte prompt 不在 `process.args`；子环境无 `MKB_INTERNAL_TOKEN` | `NS5-T23` | `high` |
| P3-05 | Phase 3 | 证据绑 process_uuid（VF17） | `update` | `generation_evidence.py:10-98`；`generation_live.py:257-338`；`runtime_outcome.py:460-463` | salvage 成功后再失败，不得把第一次失败写成第二 process_uuid | `NS5-T24` | `high` |
| P3-06 | Phase 3 | schema SHA 冻结 + 精确 probe（VF18） | `update` | `config_snapshots.py:191-221`；`generation_live.py:133-168`；`local_vllm.py:161-166,187-195`；`config.py:38` | freeze 后改 schema digest → generate fail-closed；vLLM 302 → inference 非 ready | `NS5-T25` | `high` |
| P3-07 | Phase 3 | EXHAUSTED 可 process-retry（VF19） | `update` | `facade.py:332-342`；`intake/core.py:176-186` | 三次 RETRYABLE → `retryable_failure` 而非终态 failed | `NS5-T26` | `medium` |
| P3-08 | Phase 3 | CLI ConcurrencyGate（VF21） | `update` | `generation_construct.py:401-408,454-461,584-590`；`claude_cli.py:381`；`clean_preflight.py:107-108` | max=1 时第二次 `cli.run` → BACKPRESSURE | `NS5-T27` | `medium` |
| P3-09 | Phase 3 | 非 text media 拒绝（VF26） | `update` | `claude_cli.py:371-386`；`clean_preflight.py:86-119` | PDF header blob 不得成功替换文本 | `NS5-T28` | `medium` |
| P3-10 | Phase 3 | Facade 与 DispatchCaps 同源（VF96） | `update` | `api/app.py:241-251,294`；`facade.py`；`dispatch.py`；`retrieval_request.py:97-99` | embed=8 满门时 DispatchCaps.embed_running 也满 | `NS5-T29` | `medium` |
| P4-01 | Phase 4 | vectorize 超预算 fail-closed（VF27） | `update` | `vectorize.py:185-204,247-248`；`vector_publish_commit.py:111-114` | g1 original>16000 → 422，不得缩水 required_units 后签满 | `NS5-T30` | `high` |
| P4-02 | Phase 4 | HTML 保留换行（VF28/VF31） | `update` | `intake/text.py:12,17-72,96-113`；`intake/api/providers/realestate.py:102-103` | `extract_html_text('<p>A</p><p>B</p>')` 含换行 | `NS5-T31` | `high` |
| P4-03 | Phase 4 | 单调 anchor cursor（VF29） | `update` | `src/services/lsrag_compiler/adopt.py:224-235` | `clean='same\nsame'` 第二 span 在第一之后或 kernel fail | `NS5-T32` | `high` |
| P4-04 | Phase 4 | PDF 去掉 latin-1 回退（VF30） | `update` | `src/runtime/intake/types.py:32-34,144-171` | 无 BOM UTF-16 不得返回 latin-1 垃圾；Flate 无 Tj 仍 422 | `NS5-T33` | `medium` |
| P4-05 | Phase 4 | acquisition 预算 + Source/Item resolve + artifact 字节一致（VF34/35/36） | `update` | `acquisition_ingest.py:91-97,358-496`；`acceptance_snapshot.py:63-178`；`local_store.py:103-118` | 超 cap 不得 `within_configured...`；同 key 两次 items=1；`sha256(read(handle))==digest` | `NS5-T34` | `high` |
| P4-06 | Phase 4 | stub 双通道可区分（VF37） | `update` | `config.py:44`；`claude_cli.py:110-115,401-421`；`tests/e2e/test_generation_pipeline_contracts.py:160-173` | stub g0 summary != original | `NS5-T35` | `medium` |
| P4-07 | Phase 4 | JSON 栈匹配 + markdown transport + 两节点树诚实（VF38/39/41） | `update` | `facade.py:49-66`；`local_vllm.py:161-162`；`generation_construct.py:544-623`；`adopt.py:66-67,176-210` | 多顶层对象拒绝；artifact.transport==receipt；3 节文档 `len(nodes)==2` 显式限制 | `NS5-T36` | `medium` |
| P4-08 | Phase 4 | human_review 前不 active（VF40） | `update` | `acceptance_snapshot.py:98-112`；`runtime_gates.py:122-138` | reject 后 lifecycle 不是 active | `NS5-T37` | `medium` |
| P4-09 | Phase 4 | vectorize 保留原错误码 + body-only embed（VF42/43） | `update` | `vectorize.py:161-168,376,402-440`；`retrieval_request.py:401-412` | SPACE_VIOLATION 原样上抛且不重试；header 不系统性拉低 cosine | `NS5-T38` | `medium` |
| P4-10 | Phase 4 | generation 单调 CAS + unique 含 generation（VF44/55/58） | `update`/`migrate` | `vector_publish_commit.py:144-160,263-279,379-395`；`001_initial.sql:1871-1874`；`index_rebuild_plan.py:360-361`；新建 `015_*.sql` | 延迟 publish 不得回拨指针；同 coordinate 再 upsert 不得把 serving COUNT 打到 0 | `NS5-T39` | `high` |
| P4-11 | Phase 4 | envelope 只留 receipts（VF45） | `update` | `intake/core.py:373-387`；`generation_construct.py:607-614,1339-1375`；`vectorize.py:233-268` | vectorize output JSON 无 raw/clean/markdown 正文 | `NS5-T40` | `medium` |
| P4-12 | Phase 4 | layered validator 补 UUID/array/date-time/URI（VF46） | `update` | `src/contracts/lsrag/layered_content.py:79-118` | `upstream_file_uuids` 为字符串必须失败 | `NS5-T41` | `medium` |
| P4-13 | Phase 4 | 召回截断 fail-closed + Layer A 查询空间（VF47/51/52） | `update` | `retrieval_rank.py:100-149`；`retrieval_request.py:52,96-99`；`vector_publish_commit.py:289-303`；`config.py:26-27` | 1001 条高分在尾部必须命中或显式错误；live ns + LIVE=false → mismatch；dim 切换新 namespace | `NS5-T42` | `high` |
| P4-14 | Phase 4 | dedup/inflate/pack/hydration（VF48/49/53/56） | `update` | `retrieval_pack.py:187-273,328-350`；`retrieval_rank.py:86-89`；`retrieval_access.py:168-215` | 高分 original 保留；channel=original 可 inflate；同代 root 只附一次；20 hit 同代一次 read | `NS5-T43` | `medium` |
| P4-15 | Phase 4 | Team inactive 不可检索（VF50） | `update` | `api/public/routes.py:452-469`；`teams.py:110-148`；`retrieval_request.py:343-359` | deactivate 后同 token → 409 或空+team-inactive | `NS5-T44` | `high` |
| P4-16 | Phase 4 | 禁止单通道 purge 破 Proof（VF54） | `update` | `src/services/vector_purge.py:58-93`；`src/services/retrieval/models.py:59-75` | 只 purge original 后不得空 serving | `NS5-T45` | `high` |
| P4-17 | Phase 4 | upserted UUID + rebuild 跳过非 serving（VF59/60） | `update` | `vectorize.py:221-337`；`targets.py:113-120`；`index_rebuild_plan.py:253-264` | 事件 UUID 非空；team rebuild 只重建 serving item | `NS5-T46` | `medium` |
| P4-18 | Phase 4 | title 进入 dual 或从 schema 删除（VF95） | `update` | `adopt.py:61-65,216-245`；`construct.py:54-68`；`payloads.py:170-184` | title 进入 content_full **或** schema 不再接受 title | `NS5-T47` | `low` |
| P5-01 | Phase 5 | trusted-proxy CIDR（VF75） | `update` | `security.py:463-481`；`api/dependencies.py:150-165`；`config.py` | ASGI 10.0.0.1 + XFF 8.8.8.8 对 /metrics /internal → 403（默认空 CIDR） | `NS5-T48` | `high` |
| P5-02 | Phase 5 | 限流 overflow 桶而非全局 fail-open（VF76） | `update` | `security.py:104-106,185-215`；`api/dependencies.py:104-116` | max_buckets=2 后第三 IP 不得使后续永远 allowed | `NS5-T49` | `high` |
| P5-03 | Phase 5 | extras 拒 secret/camelCase/signed URL（VF78） | `update` | `src/contracts/common/models.py:24-36,111-119`；`src/contracts/api/models.py:33-54,357-372` | TeamCreate `{apiKey:sk-live}` 与 TaskPatch `{token:x}` → 422 且库无 secret | `NS5-T50` | `high` |
| P5-04 | Phase 5 | sqlite 后门双因子（VF80） | `update` | `src/persistence/factory.py:12-16,39-41` | 仅 `PYTEST_CURRENT_TEST` + backend=sqlite 在非 pytest 进程必须 raise | `NS5-T51` | `medium` |
| P5-05 | Phase 5 | Starlette ≥1.0.1 + TrustedHost（VF81） | `update` | `pyproject.toml:14`；`uv.lock`；`api/app.py:117-130` | `starlette.__version__ >= 1.0.1`；GHSA-86qp-5c8j-p5mr 不再匹配 | `NS5-T52` | `medium` |
| P5-06 | Phase 5 | IPv6-mapped 递归受限（VF82） | `update` | `security.py:334-344,472-481` | `::ffff:127.0.0.1` + allow_literal_ip → SEC_EGRESS_DENIED | `NS5-T53` | `medium` |
| P5-07 | Phase 5 | audit sampler 写成功才提交（VF83） | `update` | `api/dependencies.py:63-97` | BrokenAudit limit=1：第 2 次 invalid token 仍 503 而非无审计 401 | `NS5-T54` | `high` |
| P5-08 | Phase 5 | 入站 body cap middleware（VF84） | `update` | `api/app.py:451,464`；`src/contracts/api/models.py:129,134` | Content-Length>cap → 413 before JSON parse | `NS5-T55` | `medium` |
| P6-01 | Phase 6 | 拆除 tautology 簇（VF85） | `update` | `tests/unit/test_turso_driver.py:99`；`test_ns4_readport_reports.py:8-22`；`test_ns4_diagnostic_sidecar.py:7,23-28`；`tests/integration/test_ns4_cw_soak.py:53-57`；`tests/domain/test_ns4_no_r3_ingest.py:13-14` | 删 sidecar.insert / ReadPort helper 后对应测试 RED；再接到真 SUT 绿 | `NS5-T56` | `high` |
| P6-02 | Phase 6 | ruff 9 errors 清零（VF87） | `update` | ruff 位点（`test_ns4_migration_013.py:99` B017 等） | `uv run ruff check .` 0 error | `NS5-T57` | `low` |
| P6-03 | Phase 6 | CW 单元不得两 False 仍绿（VF91） | `update` | `tests/unit/test_turso_driver.py:112-127`；`tests/local_runtime.py:17-25` | 断言 `concurrent_writes is True`（或 skipIf 真机不可用） | `NS5-T58` | `medium` |
| P6-04 | Phase 6 | wheel 含 migrations/*.sql（VF93） | `update` | `pyproject.toml:32-35`；`src/runtime/config.py:109-111` | `unzip -l dist/*.whl` 含 `migrations/*.sql`；干净 venv migrate 不 503 | `NS5-T59` | `high` |
| P6-05 | Phase 6 | mega/soak/文档/closure | `update` | README；`deferred-items-ledger.md`；VF-ledger §6；新建 closure | §8 mega+soak PASS 四元组；ledger §6 append；文档状态 `executed` 仅当硬闸全绿 | `NS5-T60` `NS5-T61` `NS5-T62` | `medium` |

---

## 4. Phase 业务表格

> `工作内容` 是承重列。高风险项拆 a/b/c；扩展既有项枚举即可。`测试映射` 只引 Test-ID。

### 4.1 Phase 1 — 运行时安全 / 不可恢复 IO

**绑定 VF**：`VF1 VF2 VF3 VF9 VF10 VF61 VF62 VF63 VF64 VF65 VF66 VF67 VF68 VF69 VF70`  
（VF10 从批次 3 提前；VF62 在 `NS5-T04` 绿之前不得重叠执行。）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P1-01 | VF1 UoW | a) `except BaseException` 覆盖 `CancelledError`；b) `commit()` 移入 try，失败 rollback；c) rollback/cleanup `shield`；d) commit/线程状态不确定则关闭连接，下次 `_connect` 新句柄；e) sqlite 与 turso 同一 helper | `sqlite_port.py:83-95`；`turso/port.py:87-99` | 取消后再 BEGIN 成功 | `NS5-T01` | 无 `cannot start a transaction within a transaction` |
| P1-02 | VF2/VF3 Turso+sidecar | a) `_connect` 设 `busy_timeout=5000`，`PRAGMA foreign_keys` 读回 1；b) journal_mode 一次设稳，探针改旁路连接；c) UoW 要么 CONCURRENT+BUSY retry，要么 readiness `concurrent_writes=false`；d) sidecar 单连接有界队列，禁止每 insert 切 mode；e) 4 线程 soak 不得 abort | `turso/port.py:63-91`；`engine.py:13-40`；`sidecar.py:23-57`；`observability.py:158-171`；`api/app.py:309-314` | 探针与写路径同故事；sidecar 不杀进程 | `NS5-T02` | exit 134 不再复现；ready 字段与下一 UoW SQL 一致 |
| P1-03 | VF9 CLI kill | a) Timeout/Cancelled/finally：terminate→wait→kill→wait；b) stdout 上限；c) 假挂起可执行测 | `claude_cli.py:288-304` | child 回收 | `NS5-T03` | timeout 后 pid 不在 |
| P1-04 | VF10/VF62 | a) `run_once` 启 heartbeat（lease/3）；b) heartbeat CAS 失败立即取消 handler；c) generate/CLI `safe_replay=false` 或抬 lease；d) supervisor 结构改为 per-pool worker 集；e) **重叠 `run_once` 仅在 a–c 绿后打开**；打开前 max_running=1 | `worker.py:45-53`；`runtime_core.py:546-558`；`workflow_supervisor.py:39-51` | 长 handler 不被 reclaim 双跑；可选两 Process 时间戳重叠 | `NS5-T04` | 两 runtime：lease=1s sleep=2s → 败者 fenced 且运输取消 |
| P1-05 | VF61 outbox | a) 先 CAS in_flight 并提交；b) 再 parse；JSON/digest 失败新 TX 标 dead；c) `drain_once` catch 后仍 claim+repair | `runtime_outbox.py:38-59,77-104`；`workflow_supervisor.py:39-51` | 毒丸不冻 supervisor | `NS5-T05` | payload=`not-json` 后该行 dead，同 tick claim 第二条 |
| P1-06 | VF63 retirement | POINTER_UNAVAILABLE 且 item 已 deactivate/delete/missing → 软删仍活 retired gen，CAS intent completed/abandoned | `index_retirement.py:314-327,396-406` | 队头不再永久占满 | `NS5-T06` | 100 stuck + 1 健康 → 第二次 scan 收到健康 |
| P1-07 | VF64–67 GC | a) TX1 再检查 blockers；b) unlink 在写锁外；c) TX2 复核后 proof+tombstone；d) `delete_if_unreferenced` 取 `_write_lock`（勿跨 persistence TX 长持）；e) `released_at` CAS + item-delete consumer；f) lookup `tombstoned_at IS NULL`（部分 unique 放 P2 014 若同迁） | `object_gc.py:145-269`；`local_store.py:67-132`；`artifacts.py:131-149`；`lifecycle_apply.py:270-300` | unlink/rollback 分裂消失 | `NS5-T07` | tombstone UPDATE 在 unlink 后 raise → 有 missing-live 信号；同 digest 新 catalog → 新 uuid |
| P1-08 | VF68 pending | `validate_and_commit` finally pop；失败/取消也 pop；限制 map 大小 | `artifacts.py:44-120`；`intake/core.py:127-139` | 无进程级泄漏 | `NS5-T08` | 一成功 Process 后 `_pending` 空 |
| P1-09 | VF69 scanner | `run_once` 包 `except Exception`（不捕 CancelledError），metric+backoff；对齐 retention | `src/runtime/object_gc.py:42-50`；`index_retirement.py:40-46` | 一次 BUSY 不永停 | `NS5-T09` | OperationalError 后 task running |
| P1-10 | VF70 claim | 同 UoW 有界循环 fail-expired，直到无过期再 admit/claim；不得在仍有活行时 `return None` | `runtime_core.py:353-379` | 过期不饿死活任务 | `NS5-T10` | 3 过期+1 活 → 一次领到活 Process |

### 4.2 Phase 2 — 持久化诚实与平台卫生

**绑定 VF**：`VF4 VF5 VF7 VF8 VF71 VF72 VF73 VF94 VF98 VF99 VF100 VF101 VF102 VF103`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P2-01 | VF4 rowcount | `TursoUnitOfWork.execute` 归一化 `rowcount>=0` else `changes()`；补 Turso CAS 测 | `turso/port.py:24-25`；`runtime_core.py:462-477` | fence 读真实 changes | `NS5-T11` | stale UPDATE==0；匹配 CAS==1 |
| P2-02 | VF5/VF7 | ledger INSERT 参数化；不改 010 checksum；014 把 32-hex 改写连字符 UUID；可选同迁 VF67 部分 unique | `migration_runner.py:132-138`；新建 `014_*.sql` | 升级路径 UUID 合法 | `NS5-T12` | monkeypatch `utc_now` 含引号仍入库；seed qwen-vl-2b 升 014 后匹配 RFC UUID |
| P2-03 | VF8 | `utc_now`/`normalize_rfc3339` 同一 timespec；artifacts 改传 Python `utc_now()` | `time.py:10-23`；`artifacts.py:140,148` | 无 us/ms 字典序坑 | `NS5-T13` | `%f` 行不被 us cutoff 排除 |
| P2-04 | VF71/72/73 | retry_count full jitter；cancelling/cancelled 时 gate outbox done/noop；同 UoW 写 `outbox.dead` + `mkb_outbox_dead_total` | `runtime_core.py:62,80`；`runtime_gates.py:186-187`；`runtime_outbox.py:90-105,331-341` | 可观测 dead；取消不恶性重试 | `NS5-T14` | 两次 next_retry_at 不同；8 次 dispatch 行 done；/metrics 含 dead_total |
| P2-05 | VF94 | HealthAggregator 短 TTL + in-flight coalesce；CW/vector 探针旁路连接；claim 不切 journal_mode | `turso/port.py:100-130`；`engine.py:13-40`；`workflow_supervisor.py:26,68` | idle 不 20Hz 切 mode | `NS5-T15` | idle 1s 切 mode 次数 ≪ 20 |
| P2-06 | VF98 | bootstrap/retention `except MkbError` 先 increment+diagnostic 再 pass | `api/app.py:405-414,517-523` | 静默 pass 变可观测 | `NS5-T16` | 强制 PROMPT_NOT_REGISTERED → ready 503 且计数器+1 |
| P2-07 | VF99/102/103 | 指纹排除 audit 时间戳；`payload_extra in model_fields_set`（含 `{}`）；INSERT 捕 IntegrityError → 409/replay | `task_create.py:53-114`；`api/models.py:45-73`；`teams.py:39-103` | 幂等与冲突语义正确 | `NS5-T17` | created_at+1s replay 200；PATCH `{}` 存空对象；并发同 UUID 409 |
| P2-08 | VF100 | 只持久化 error_code + 预声明安全消息；`str(exc)` 经 `_safe_text` | `worker.py:52-60`；`runtime_outcome.py:443-452`；`runtime_outbox.py:102-341` | 落盘无 secret | `NS5-T18` | handler 含 token/路径 → error_message 无这些 |
| P2-09 | VF101 | parse identity.json；`sqlite_master` 必选表（含 mkb_tasks）；JSON/OSError fail-closed | `local_store.py:41-49,134-139`；`migration_runner.py:147-155` | ready 不再谎报 | `NS5-T19` | DROP mkb_tasks → schema false；identity='not-json' storage false |

### 4.3 Phase 3 — 推理 / 车道 / 证据

**绑定 VF**：`VF11 VF12 VF13 VF14 VF15 VF16 VF17 VF18 VF19 VF21 VF22 VF24 VF26 VF96`  
（不含 VF10，已在 P1。）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P3-01 | VF11/12/13 | a) salvage 新开 durable NI Process 或再 admit；b) NI 满/CLI 未绑 fail-closed；c) snapshot 冻 admit-time pool；d) 去掉 `task_priority=='normal'`（保留 low 不 salvage 若仍是政策）；e) transcribe/construct 进 OVER_BUDGET | `generation_construct.py:81-180,270-284`；`runtime_core.py:300-315`；`config_snapshots.py:573-591`；`dispatch.py:20-36` | 池=运输 | `NS5-T20` | salvage 占 NI occupancy 或闭；explicit local+urgent 可 salvage；16k+ construct → NI |
| P3-02 | VF14 | `_ns1_prompt_file` 强制 state+role | `generation_construct.py:351-370` | 无 Snapshot 不读盘 | `NS5-T21` | state=None raise |
| P3-03 | VF15/22/24 | adapter 持有一个 AsyncClient（lifespan aclose）；sleep 前放 lease 再获取；full jitter；408/425→RETRYABLE | `local_vllm.py:66-215`；`facade.py:262-349,486-487` | 连接池有效；退避不占满门 | `NS5-T22` | 两次 embed 一个 client；cap=2 sleep 期间第三请求不满门；FakeTransport 408→RETRYABLE |
| P3-04 | VF16 | 业务正文永远 stdin；argv 不含 prompt；env allowlist 去掉 MKB_*；`internal_token` SecretStr | `claude_cli.py:59-62,149-152,281-298`；`config.py:15-17` | 无 argv/环境泄密 | `NS5-T23` | 100-byte prompt 不在 process.args；子环境无 MKB_INTERNAL_TOKEN |
| P3-05 | VF17 | 废 ContextVar；证据绑 process_uuid；成功/失败同 UoW flush | `generation_evidence.py:10-98`；`generation_live.py:257-338`；`runtime_outcome.py:460-463` | 不串台 | `NS5-T24` | 第一失败不得写入第二 process_uuid |
| P3-06 | VF18 | L4 物化 schema SHA；generate 复核；vLLM 传 json_schema；live_inference 时强制 probe，仅 2xx+精确模型健康 | `config_snapshots.py:191-221`；`generation_live.py:133-168`；`local_vllm.py:161-195`；`config.py:38` | freeze 真冻结 | `NS5-T25` | 改 schema digest → fail-closed；302 → ready.inference false |
| P3-07 | VF19 | EXHAUSTED/BACKPRESSURE 进 `_RECOVERABLE_ERROR_CODES`（或停止改写最后一次 RETRYABLE） | `facade.py:332-342`；`intake/core.py:176-186` | generate 可 process-retry | `NS5-T26` | 三次 RETRYABLE → retryable_failure |
| P3-08 | VF21 | CLI 路径走 ConcurrencyGate（ni_running 或 local+ni）；salvage 必须占门 | `generation_construct.py:401-590`；`claude_cli.py:381`；`clean_preflight.py:107-108` | 无界 fork 消失 | `NS5-T27` | max=1 第二次 cli.run → BACKPRESSURE |
| P3-09 | VF26 | 非 `text/*` → `CLEAN_MEDIA_UNSUPPORTED`；禁止 `errors='replace'` | `claude_cli.py:371-386` | blob 不当文本 | `NS5-T28` | PDF header 不得成功 clean |
| P3-10 | VF96 | 同一 DispatchCaps 注入 Runtime 与 Facade；retrieval embed 计入 embed pool | `api/app.py:241-294`；`retrieval_request.py:97-99` | 双层背压合一 | `NS5-T29` | facade embed=8 满 ⇒ DispatchCaps.embed_running 满 |

### 4.4 Phase 4 — 摄取 / 结构 / 检索 serving

**绑定 VF**：`VF27 VF28 VF29 VF30 VF31 VF34 VF35 VF36 VF37 VF38 VF39 VF40 VF41 VF42 VF43 VF44 VF45 VF46 VF47 VF48 VF49 VF50 VF51 VF52 VF53 VF54 VF55 VF56 VF58 VF59 VF60 VF95`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P4-01 | VF27 | a) `len(embeddable)!=len(plan.required)` → `VECTORIZE_BUDGET_CONTENT_FULL`；b) 不改写 required_units；c) 不 publish；d) 读路径可校验 required_set_digest | `vectorize.py:185-248`；`vector_publish_commit.py:111-114` | 无静默盲区 | `NS5-T30` | g1>16000 live vectorize 422 |
| P4-02 | VF28/31 | 停止对 HTML 输出 `_SPACE.sub`；复用 `clean_plain_text` | `intake/text.py:96-113` | 段落换行保留 | `NS5-T31` | `<p>A</p><p>B</p>` 含换行 |
| P4-03 | VF29 | 单调 cursor `find(body, cursor)`；不可消歧 → STRUCTURE_ANCHOR_MISSING | `adopt.py:224-235` | 重复文本不错锚 | `NS5-T32` | 两相同 g1 第二 span 在第一之后或 fail |
| P4-04 | VF30 | 去掉 latin-1 回退；压缩/加密/纯图保持 422。不引入完整 PDF 库（余项 VF30.r） | `src/runtime/intake/types.py:32-34,144-171` | 不返回乱码 | `NS5-T33` | 无 BOM UTF-16 非 latin-1 垃圾 |
| P4-05 | VF34/35/36 | 物化前套 `acquisition_max_response_bytes`；budget 带 `{limit,observed}`；按 (team,source_kind,key) resolve Source 再 CAS Item；raw/clean 分对象 promote | `acquisition_ingest.py:91-496`；`acceptance_snapshot.py:63-178` | 身份与字节一致 | `NS5-T34` | 超 cap 假 proof 消失；同 key items=1；digest 对齐 bytes |
| P4-06 | VF37 | stub 派生 summary（prefix/hash）使双通道不等；e2e 断言 `summary!=original`。生产默认切 stub → VF37.r | `claude_cli.py:110-115,401-421`；e2e contracts | 离线双通道可区分 | `NS5-T35` | stub g0 summary!=original |
| P4-07 | VF38/39/41 | decoder/栈匹配拒绝多顶层对象；artifact.transport 抄 receipt；保持 g0 tunnel + 文档化 v1 两节点（全树 VF41.r） | `facade.py:49-66`；`generation_construct.py:544-623`；`adopt.py:66-67,176-210` | 运输字段诚实 | `NS5-T36` | `'see {a} or {b}'` 不吞成一对象；live markdown transport==api_inference |
| P4-08 | VF40 | Item 在 approve 前 pending/reviewing；reject 同 UoW deactivate | `acceptance_snapshot.py:98-112`；`runtime_gates.py:122-138` | 无已 active 再拒 | `NS5-T37` | require_human_review+reject 后非 active |
| P4-09 | VF42/43 | 4xx/SPACE_VIOLATION 原样上抛；只 embed body（headers 当 facets）或 query 同 header | `vectorize.py:161-440`；`retrieval_request.py:401-412` | 错误码与向量空间一致 | `NS5-T38` | SPACE_VIOLATION 不重试；header 不系统性拉低 cosine |
| P4-10 | VF44/55/58 | a) 同 UoW `UPDATE index_generation=index_generation+1 RETURNING`；b) 指针 `active < excluded`；c) 015：active unique 含 `index_generation`；d) 禁止 UPDATE indexed 行；e) per-item pointer `active+1` 分配 | `vector_publish_commit.py:144-395`；`001_initial.sql:1871-1874`；`index_rebuild_plan.py:360-361` | 世代单调且 serving 行不可变 | `NS5-T39` | 预留 gen=1、rebuild=2、延迟 publish 不得写回 1；再 upsert serving COUNT≠0 |
| P4-11 | VF45 | 后期 envelope 只带 receipts/handles/digests | `intake/core.py:373-387`；construct/vectorize 所列 | 正文不倍增 | `NS5-T40` | vectorize JSON 无 raw/clean/markdown 正文 |
| P4-12 | VF46 | 补 UUID/array/date-time/URI 检查。全程 jsonschema → VF46.r | `layered_content.py:79-118` | 明显非法被拒 | `NS5-T41` | 字符串 UUID 数组失败 |
| P4-13 | VF47/51/52 | 超 scan_limit fail-closed 或扫全 fenced set；未接线 `native_ann` 拒绝；query embed 跟 namespace Layer A；namespace 按 (model,version,adapter,dim) 分键或显式 rebuild | `retrieval_rank.py:100-149`；`retrieval_request.py:52,96-99`；`vector_publish_commit.py:289-303` | 召回与空间诚实 | `NS5-T42` | 1001 尾部高分命中或显式错误；LIVE=false+live ns → mismatch |
| P4-14 | VF48/49/53/56 | 先 `-ann_score`；inflate 剥 `filters.channel`；request-scoped cache generation artifact；`_pack` 对 root 去重 | `retrieval_pack.py:187-350`；`retrieval_rank.py:86-89`；`retrieval_access.py:168-215` | 不丢高分 original；不重复填 root | `NS5-T43` | original 0.99 vs summary 0.10 保留 original；两 g1 同 root 只附一次 |
| P4-15 | VF50 | retrieval 调 `require_active`；SQL 加 `teams.status='active' AND deleted_at IS NULL` | `routes.py:452-469`；`teams.py:110-148` | 停用 Team 不可搜 | `NS5-T44` | deactivate 后 409 或空+team-inactive |
| P4-16 | VF54 | 拒绝 `channel_filter!='all'`，或部分 purge 后铸新 Proof 并 CAS 指针 | `vector_purge.py:58-93`；`retrieval/models.py:59-75` | 不灭世代 | `NS5-T45` | 只 purge original 后仍可 serving 或显式整代 purge |
| P4-17 | VF59/60 | 事件用 `dual_channel_artifact_uuid`；resolve 要求 serving_revision 非空且=latest；team scope 跳过非 serving | `vectorize.py:221-337`；`targets.py:113-120`；`index_rebuild_plan.py:253-264` | rebuild 不被毒行打死 | `NS5-T46` | 一 serving + 一 reactivated 非 serving → 只重建 serving |
| P4-18 | VF95 | title 投进 ChannelRecord/content_full **或** 从 schema/validator/prompt 删除 | adopt/construct/payloads/schema | 不再静默丢字段 | `NS5-T47` | dual 含 title 或 schema 拒 title |

### 4.5 Phase 5 — 安全边界

**绑定 VF**：`VF75 VF76 VF78 VF80 VF81 VF82 VF83 VF84`  
威胁模型：`docs/baseline/domain-truth/S16-security-trust-boundary.md`（§7.3）。每项测试含攻击向量。

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P5-01 | VF75 | a) Settings `MKB_TRUSTED_PROXY_CIDRS` 默认空；b) 仅 peer∈CIDR 才解析 XFF/Forwarded；c) /internal /metrics 继续内部 IP 闸；d) 攻击：伪造 XFF 不能变内部 | `security.py:463-481`；`dependencies.py:150-165` | 代理后不把全世界当内网 | `NS5-T48` | ASGI 10.0.0.1+XFF 8.8.8.8 → /metrics 403 |
| P5-02 | VF76 | 容量击中并入 overflow 身份并限流该桶；不为预期 overflow 设 degraded；成功 `_allow` 后复位 | `security.py:185-215` | 无全局 fail-open | `NS5-T49` | max_buckets=2 后第三 IP 不得使后续永远 allowed |
| P5-03 | VF78 | a) 所有公共 PayloadExtra 用 `_REDACT_KEY`（含 camelCase）；b) 拒绝 presigned URL；c) Team/Task PATCH 走同一检查；d) GET 脱敏；e) 攻击：`apiKey`/`secretKey`/`token` 不得入库 | `common/models.py:24-36,111-119`；`api/models.py:33-54,357-372` | extras 不是 vault | `NS5-T50` | `{apiKey:sk-live}` → 422 且 SELECT 无 secret |
| P5-04 | VF80 | sqlite 仅当 PYTEST_CURRENT_TEST **且**（sys.modules 有 pytest 或 `MKB_ALLOW_SQLITE=1`） | `factory.py:12-16,39-41` | 生产伪造环境变量不够 | `NS5-T51` | 非 pytest 进程 backend=sqlite raise |
| P5-05 | VF81 | 升级到依赖 starlette≥1.0.1 的 FastAPI；TrustedHostMiddleware；CI pip-audit | `pyproject.toml`；`uv.lock`；`api/app.py:117-130` | CVE 范围离开 | `NS5-T52` | starlette≥1.0.1 |
| P5-06 | VF82 | `address.ipv4_mapped` 则对 v4 递归 `_restricted`/`is_internal_ip` | `security.py:334-344,472-481` | mapped loopback 被拒 | `NS5-T53` | `::ffff:127.0.0.1` → SEC_EGRESS_DENIED |
| P5-07 | VF83 | decide() 当 reservation；写成功才 commit sampler；写失败不推进桶；store 宕机保持 SEC_AUDIT_WRITE_FAIL | `dependencies.py:63-97` | 无审计 401 消失 | `NS5-T54` | BrokenAudit 第 2 次 invalid token 仍 503 |
| P5-08 | VF84 | ASGI middleware 缓冲前按 Settings cap 413；限制 ChinaTax 自由字符串 | `api/app.py:451,464`；`api/models.py:129-134` | 大 body 不 OOM | `NS5-T55` | Content-Length>cap → 413 before parse |

### 4.6 Phase 6 — 测试保真与包装

**绑定 VF**：`VF85 VF87 VF91 VF93`（加文档/closure，无新 VF）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P6-01 | VF85 | 删 `or True`；ReadPort 走真实服务；sidecar 实例化；CW soak ThreadPool+行数；缺文件 `pytest.fail`；journal 调 `_journal_row` | 见 §3 P6-01 文件列 / ledger §3.2.1 | 删 SUT 会红 | `NS5-T56` | 删除 insert/helper 后 RED，接回后绿 |
| P6-02 | VF87 | `ruff check --fix` + 手修 B904/B017/F841。**不得声称全量 pytest 441/441**（VF86 仍冻） | ruff 位点 | 静态门绿 | `NS5-T57` | `ruff check .` 0 |
| P6-03 | VF91 | unit 断言 CW **True**（或明确 skip）。真机 constitution e2e → VF91.r | `test_turso_driver.py:112-127`；`local_runtime.py:17-25` | 两 False 不再绿 | `NS5-T58` | 相等且均为 False 今日必须 RED |
| P6-04 | VF93 | `[tool.setuptools.package-data]` 含 `src/persistence/migrations/*.sql`；CI：uv build → 干净 venv migrate smoke | `pyproject.toml:32-35` | 安装可启动 | `NS5-T59` | wheel 含 `*.sql`；空环境 migrate 非 503 |
| P6-05 | mega/soak/docs | 主链 mega；sidecar 4 线程 soak；lease reclaim soak；README/deferred ledger 窄回填；VF-ledger §6 append；写 NS5 closure | README；deferred-items-ledger；VF-ledger §6 | 计划收口 | `NS5-T60` `NS5-T61` `NS5-T62` | 硬闸四元组齐全才 `executed` |

---

## 5. Phase 详情

### 5.1 Phase 1 — 运行时安全 / 不可恢复 IO

- **Phase 目标**：故障后唯一连接、唯一 supervisor、子进程与物理对象仍可前进。
- **本 Phase 对应编号**：`P1-01` … `P1-10`
- **本 Phase 新增文件**：`tests/unit/test_ns5_uow_cancel.py`；`tests/unit/test_ns5_sidecar_serial.py`（或扩展既有 soak 为真并发）；`tests/unit/test_ns5_outbox_poison.py`
- **本 Phase 修改文件**：`sqlite_port.py:83-95`；`turso/port.py:63-99`；`engine.py:13-40`；`sidecar.py:23-57`；`claude_cli.py:288-304`；`worker.py:45-53`；`runtime_core.py:353-379,546-558`；`runtime_outbox.py:38-104`；`workflow_supervisor.py:39-51`；`object_gc.py:145-269`；`index_retirement.py:314-406`；`local_store.py:67-132`；`artifacts.py:44-149`；`api/app.py:309-314,417-446`
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. UoW body 被 cancel 后连接不留在 `in_transaction`。
  2. commit 抛错走 rollback；不确定则弃连接。
  3. sidecar 并发 insert 不触发 pyturso abort。
  4. Claude timeout 后 OS 进程被 kill 且 wait。
  5. heartbeat 失败立即取消运输；VF10 未绿时 supervisor 不重叠 `run_once`。
  6. 非法 outbox 标 dead，drain 继续 claim/repair。
  7. GC unlink 不在持写锁的 TX 内；tombstone lookup 跳过已墓碑 digest。
  8. scanner 一次 BUSY 后 loop 仍在。
- **对应测试台账项**：`NS5-T01` … `NS5-T10`
- **收口标准**：T01–T10 全 PASS；sidecar 子进程 soak 非 exit 134；不得在本 Phase 合并打开 VF62 重叠执行。
- **本 Phase 风险提醒**：真正 `BEGIN CONCURRENT` 可能暴露 pyturso 更多 abort——若 soak 不稳，诚实把 `concurrent_writes` 置 false，禁止探针假绿。

### 5.2 Phase 2 — 持久化诚实与平台卫生

- **Phase 目标**：CAS、迁移、时间、dead 可观测、ready 不切 live journal_mode。
- **本 Phase 对应编号**：`P2-01` … `P2-09`
- **本 Phase 新增 / 修改 / 删除文件**：新建 `src/persistence/migrations/014_ns5_uuid_and_tombstone.sql`；修改 `migration_runner.py:132-138`；`turso/port.py:24-25,100-130`；`time.py`；`runtime_outcome.py`；`runtime_outbox.py:331-341`；`task_create.py:53-114`；`teams.py`；`local_store.py:41-49,134-139`；`api/app.py:166-197,405-523`
- **具体功能预期**：
  1. Turso CAS 读归一化 changes。
  2. ledger 参数化；010 遗留 32-hex 由 014 改写。
  3. outbox dead 写领域事件与指标。
  4. idle supervisor 不再 20Hz 切 MVCC。
  5. Task 指纹不含 audit.created_at；空 extras 可清空；PK 冲突 409。
- **对应测试台账项**：`NS5-T11` … `NS5-T19`
- **收口标准**：014 在 fresh 与 upgrade 夹具都绿；ready 探针不再持业务连接切 mode。
- **本 Phase 风险提醒**：014 不得改 010 checksum；upgrade 夹具必须覆盖已有 `qwen-vl-2b` 行。

### 5.3 Phase 3 — 推理 / 车道 / 证据

- **Phase 目标**：dispatch_pool = 运输 SSOT；CLI 可取消、有门限、不泄密；证据不串台。
- **本 Phase 对应编号**：`P3-01` … `P3-10`
- **本 Phase 新增 / 修改 / 删除文件**：`generation_construct.py:81-370,401-590`；`generation_evidence.py`；`generation_live.py:133-338`；`facade.py:49-66,262-349`；`local_vllm.py:66-215`；`dispatch.py:20-36`；`config_snapshots.py:191-221,573-591`；`claude_cli.py:59-62,149-152,281-298,371-386`；`api/app.py:225-294`；`intake/core.py:176-186`
- **具体功能预期**：
  1. salvage 占 NI 或 fail-closed，不再偷跑 Claude 占 local 槽。
  2. prompt 缺 Snapshot 不读盘。
  3. CLI 正文只走 stdin；子环境无 MKB token。
  4. 失败证据绑定 process_uuid。
  5. schema SHA 冻结；EXHAUSTED 可 process-retry。
  6. Facade 与 DispatchCaps 同一计数器。
- **对应测试台账项**：`NS5-T20` … `NS5-T29`
- **收口标准**：车道测试断言 `command.dispatch_pool == snapshot.l2 == 实际运输`。
- **本 Phase 风险提醒**：不要为了 salvage 测试把 billing 改成真配额（VF23 仍 always-permit）。

### 5.4 Phase 4 — 摄取 / 结构 / 检索 serving

- **Phase 目标**：publication proof 与检索召回不再说谎。
- **本 Phase 对应编号**：`P4-01` … `P4-18`
- **本 Phase 新增 / 修改 / 删除文件**：新建 `015_vec_coord_generation.sql`；修改 `vectorize.py`；`vector_publish_commit.py`；`intake/text.py`；`adopt.py`；`acquisition_ingest.py`；`acceptance_snapshot.py`；`retrieval_rank.py`；`retrieval_pack.py`；`retrieval_request.py`；`vector_purge.py`；`targets.py`；`index_rebuild_plan.py`
- **具体功能预期**：
  1. 任一 required unit 超预算 → 不 publish。
  2. HTML 换行保留；重复锚点单调。
  3. 指针 generation 单调；serving 行不可 UPDATE 成 withdrawn。
  4. 召回超 scan_limit fail-closed 或全扫；offline 不得 hash 打进 live 空间。
  5. Team inactive 不可检索；单通道 purge 不得灭 Proof。
  6. stub summary ≠ original（本轮切片；生产默认可仍 stub，VF37.r）。
- **对应测试台账项**：`NS5-T30` … `NS5-T47`
- **收口标准**：vectorize/检索/purge 相关 spike 全绿；015 升级夹具覆盖已有 serving 行。
- **本 Phase 风险提醒**：unique 加 `index_generation` 必须先背填，禁止在有重复 active 行时硬加索引。

### 5.5 Phase 5 — 安全边界

- **Phase 目标**：S16 在反向代理与公共 extras 上 fail-closed。
- **本 Phase 对应编号**：`P5-01` … `P5-08`
- **本 Phase 新增 / 修改 / 删除文件**：`security.py`；`dependencies.py`；`config.py`；`common/models.py`；`api/models.py`；`factory.py`；`api/app.py`；`pyproject.toml`；`uv.lock`
- **具体功能预期**：
  1. 默认不信 XFF。
  2. 限流 overflow 不全局放行。
  3. camelCase secret 与 signed URL 422。
  4. 伪造 PYTEST_CURRENT_TEST 不够开 sqlite。
  5. audit 写失败不把 invalid token 变成无审计 401。
  6. 超 cap body 413。
- **对应测试台账项**：`NS5-T48` … `NS5-T55`（均含攻击向量）
- **收口标准**：`test_security_boundary` 扩展用例全 PASS。
- **本 Phase 风险提醒**：TrustedHost 过严会打本机测试 Host；夹具必须设允许名单。Starlette 升级若卡住 FastAPI 0.115.12，升级 FastAPI 主版本，禁止强钉不兼容组合。

### 5.6 Phase 6 — 测试保真与包装

- **Phase 目标**：回归可信；安装制品可 migrate；本 AP 可 closure。
- **本 Phase 对应编号**：`P6-01` … `P6-05`
- **本 Phase 新增 / 修改 / 删除文件**：VF85 所列测试；`pyproject.toml` package-data；README；`deferred-items-ledger.md`；VF-ledger §6；新建 `docs/closure/new-start/NS5-0820-bug-fixes-closure.md`
- **具体功能预期**：
  1. 删 SUT 后 tautology 变红。
  2. ruff 0 error。
  3. CW 两 False 不再绿。
  4. 干净 wheel 含 SQL 且 migrate 成功。
  5. mega/soak 四元组；ledger §6 逐 VF 回填。
- **对应测试台账项**：`NS5-T56` … `NS5-T62`
- **收口标准**：§10 硬闸全 PASS。**禁止**用「全量 pytest 全绿」代替——VF86 仍 deferred。
- **本 Phase 风险提醒**：在 P1–P5 未合并前拆 tautology 会把未修缺陷锁进新断言；P6 必须最后。

---

## 6. 依赖的冻结设计决策（只读引用）

> 不填写新 Q/A。只引 ledger / domain-truth / deferred ledger。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[true-bug]` 本轮必修 | VF-ledger §0.4 / §4.1 | P1–P5 不得把 75 条改成 defer | AP 保持 draft；回 owner |
| 六批次 DAG + VF10 提前 | VF-ledger §5.3 + 本 AP §1.1 | Phase 顺序；VF62 门闩 | 若取消 VF62 并发，VF10 可退回 P3 |
| VF20 fence=enabled-set | VF-ledger §5.2 VF20 | P3 不改 SupplyFence 构建源 | 若 owner 要 winner-only，另开 AP |
| VF23 always-permit billing | NS2-O1 / README K10 / VF-ledger §5.4 | P3 salvage 仍走恒真 has_quota | billing AP |
| VF86 NS1-V11 harness 冻结 | deferred-items-ledger NS1-V11 | P6 不修 sqlite3 e2e；不声称全绿 | harness charter |
| VF97 未接线 | README 未接线合同 / VF-ledger §5.4 | 不注入 BrowserFetcher | capability charter |
| T-O-120 目录非 CAS SSOT | S13 / VF66.r | P1 只做 released_at + journal，不做磁盘 SSOT | owner 授权后再开 |
| S09 complete-set proof | S09 / VF-ledger 不变量 | P4-01/P4-16 不得缩 required set / 单通道破 COUNT | 视为 blocker |
| S16 不盲信 XFF | S16 / README 9.1 | P5-01 默认空 CIDR | 公网 bind 时 reopen VF79 |
| VF6/VF92 不修 | VF-ledger §4.3 | 不进 §3 | 代码漂移后再核 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `src/persistence/sqlite_port.py:83-95` / `turso/port.py:87-99` | UoW `except Exception` + `else commit` | P1-01 替换点 | `✅ 复用` | 抽共用 cancellation-safe helper，别分叉两套语义 |
| A-2 | `src/persistence/turso/port.py:63-91` | 单连接 + IMMEDIATE + 无 busy_timeout | P1-02 | `✅ 复用` | sqlite_port:69-71 是对照，别把测试后端当生产 |
| A-3 | `src/persistence/engine.py:13-40` | CW 探针切 journal_mode | P1-02 / P2-05 | `✅ 复用` | 禁止在业务连接上切 mode |
| A-4 | `src/persistence/turso/sidecar.py:23-57` | 每 insert 新连接 + CONCURRENT | P1-02 | `♻️ 重 substrate` | 改为单连接队列 |
| A-5 | `src/runtime/inference/claude_cli.py:288-304` | wait_for 无 kill | P1-03 / P3-04 | `✅ 复用` | |
| A-6 | `src/runtime/workflow/worker.py:45-53` | claim 30s 后裸 await handler | P1-04 | `✅ 复用` | heartbeat 已在 runtime_core:546-558，接线即可 |
| A-7 | `src/runtime/workflow/runtime_outbox.py:38-59` | 同 TX attempts+1 后 json.loads | P1-05 | `✅ 复用` | |
| A-8 | `src/runtime/workflow_supervisor.py:39-51` | drain_once 先 outbox 后 process | P1-04 / P1-05 | `✅ 复用` | 先隔离错误，再并发 |
| A-9 | `src/services/object_gc.py:190-269` | TX 内 unlink | P1-07 | `♻️ 重 substrate` | 两阶段；勿改 `src/runtime/object_gc.py` 那份 54 行 scanner 当服务 |
| A-10 | `src/storage/local_store.py:67-74,120-132` | promote 有锁 / delete 无锁 | P1-07 | `✅ 复用` | |
| A-11 | `src/services/index_retirement.py:314-327,396-406` | POINTER_UNAVAILABLE 不更新 intent | P1-06 | `✅ 复用` | 勿与 `src/runtime/index_retirement.py` 撞名 |
| A-12 | `src/runtime/intake/vectorize.py:185-204,247-248` | 滤 required 后签满 | P4-01 | `✅ 复用` | |
| A-13 | `intake/text.py:102-113` | `_SPACE.sub` 抹换行 | P4-02 | `✅ 复用` | `:96-99` `clean_plain_text` 已是正确配方 |
| A-14 | `src/services/lsrag_compiler/adopt.py:224-235` | `find` 从 0 | P4-03 | `✅ 复用` | |
| A-15 | `src/runtime/intake/vector_publish_commit.py:144-160,263-279,379-395` | 指针非单调；unique 无 generation | P4-10 | `✅ 复用` | rebuild fence 在 `index_rebuild_commit.py:105-124` 可对照 |
| A-16 | `src/services/retrieval/retrieval_rank.py:100-130` | UUID LIMIT 1000 | P4-13 | `✅ 复用` | 本轮不接 ANN |
| A-17 | `src/services/vector_purge.py:58-93` | 单通道软删 | P4-16 | `✅ 复用` | proof 谓词 `retrieval/models.py:59-75` |
| A-18 | `src/runtime/security.py:185-215,463-481` | degraded fail-open；client.host | P5-01 / P5-02 | `✅ 复用` | |
| A-19 | `src/contracts/common/models.py:24-36,111-119` | extras 只 JSON/64KiB；精确小写密钥集 | P5-03 | `✅ 复用` | TeamCreate 无 `assert_safe_public_data` |
| A-20 | `src/persistence/factory.py:12-16` | 仅看 PYTEST_CURRENT_TEST | P5-04 | `✅ 复用` | |
| A-21 | `pyproject.toml:32-35` | 无 package-data | P6-04 | `✅ 复用` | |
| A-22 | `tests/unit/test_ns4_readport_reports.py:8-22` 等 | tautology 簇 | P6-01 | `✅ 复用` | 详见 ledger §3.2.1 |
| A-23 | `src/persistence/migrations/014_*.sql` | 将新建 | P2-02 | `🆕 净新` | 不改 010 |
| A-24 | `src/persistence/migrations/015_*.sql` | 将新建 | P4-10 | `🆕 净新` | vec unique + generation |
| A-25 | `docs/closure/new-start/NS5-0820-bug-fixes-closure.md` | 将新建 | P6-05 | `🆕 净新` | |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 把 `[true-bug]` 改写成 `[true-deferred]` | VF-ledger §0.4 诚实闸 |
| ⛔2 | VF62 重叠 `run_once` 在 VF10 心跳未绿时合并 | 把 valid-conditional 变成必现双跑 |
| ⛔3 | 在业务连接上 `PRAGMA journal_mode=mvcc` 再 restore | VF2；探针剧场 / 锁抖动 |
| ⛔4 | live vectorize 缩 required_units 后仍签 full-valid | VF27；S09 complete-set |
| ⛔5 | `sqlite3.connect` 打开 Turso 文件当检查 | VF86 / NS1-V11；本轮不修也不新写这种检查 |
| ⛔6 | `assert ... or True` / 自造 dict 断言自己 | VF85；P6 必须先 RED |
| ⛔7 | 声称全量 pytest 441/441 | VF86 仍冻；harness 红不是生产绿 |
| ⛔8 | 盲信 XFF 而无 CIDR | S16 / README 9.1 / VF75 |
| ⛔9 | 目录扫描当 CAS SSOT | T-O-120 / VF66.r |
| ⛔10 | 改 010 checksum 修 UUID | VF7：加 014 |
| ⛔11 | 把 `src/runtime/object_gc.py` 当成 `src/services/object_gc.py` | Phase-4 已纠正的撞名 |
| ⛔12 | winner-only SupplyFence | VF20 acknowledge |
| ⛔13 | 放宽 S06 闭集 / S07 original 相等 | VF32/VF33 by-design |
| ⛔14 | 生产 wheel 不含 `migrations/*.sql` 仍标可发布 | VF93 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：N/A。§7.1 即本 AP grounding 真源；对照 VF-ledger §3 当前 `file:line`。
- **安全 / 信任边界类工作项的威胁模型锚**：`docs/baseline/domain-truth/S16-security-trust-boundary.md`（token / extras / egress / audit / 内网闸）。对应工作项：`P3-04`（CLI env）、`P2-08`（落盘脱敏）、`P5-01`…`P5-08`。测试必须含攻击向量（伪造 XFF、camelCase secret、overflow 限流、BrokenAudit、超 cap body、mapped IPv6）。若 S16 与实现冲突，以 S16 + VF-ledger 复核为准，不在 AP 开新 Q。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NS5-T01` | cancel 后再 BEGIN 不得套娃事务 | `短途` | `unit` | `🆕 新增 tests/unit/test_ns5_uow_cancel.py` | P1-01 → 连接可再 BEGIN | `commit + test_ns5_uow_cancel + 未观察` |
| `NS5-T02` | sidecar 4 线程×20 insert 不 abort；ready 与下一 UoW 一致 | `soak` | `集成` | `🔱 fork tests/integration/test_ns4_cw_soak.py` + 真 ThreadPool + 行数 + 子进程 | P1-02 → 无 exit 134 | `commit + soak + 未观察` |
| `NS5-T03` | CLI timeout 后 child pid 不在 | `短途` | `unit` | `🔱 fork tests/unit/test_claude_cli_port.py` + 假挂起二进制 | P1-03 → pid 回收 | `commit + test + 未观察` |
| `NS5-T04` | lease=1s handler=2s：败者 fenced 且运输取消；重叠仅心跳绿后 | `短途` | `unit` | `🔱 fork tests/unit/test_workflow_runtime.py` | P1-04 → 无双跑 | `commit + test + 未观察` |
| `NS5-T05` | 非法 outbox 标 dead，同 tick claim 下一条 | `短途` | `unit` | `🆕 tests/unit/test_ns5_outbox_poison.py` | P1-05 → supervisor 不冻 | `commit + test + 未观察` |
| `NS5-T06` | 100 stuck retirement + 1 健康 → 第二次收到健康 | `短途` | `unit` | `🆕 tests/unit/test_ns5_retirement_stuck.py` | P1-06 → 队头不永占 | `commit + test + 未观察` |
| `NS5-T07` | GC unlink 后 TX 失败有 missing-live；tombstone digest 新 catalog 新 uuid | `短途` | `unit` | `🔱 fork tests/unit/test_object_gc.py` + promote-rollback | P1-07 → 两阶段安全 | `commit + test + 未观察` |
| `NS5-T08` | 成功 Process 后 `_pending` 空 | `短途` | `unit` | `🆕` 或扩 artifacts 测 | P1-08 → 无泄漏 | `commit + test + 未观察` |
| `NS5-T09` | scanner 抛一次仍 running | `短途` | `unit` | `🆕` runtime scanner 测 | P1-09 → 不永停 | `commit + test + 未观察` |
| `NS5-T10` | 3 过期 + 1 活 → 一次 claim 领到活 | `短途` | `unit` | `🔱 fork` runtime_core 测 | P1-10 → 不饿死 | `commit + test + 未观察` |
| `NS5-T11` | Turso CAS rowcount 0/1 | `短途` | `unit` | `🆕` Turso CAS（禁止只跑 sqlite） | P2-01 → 归一化 changes | `commit + test + 未观察` |
| `NS5-T12` | ledger 参数化；014 UUID 改写 | `短途` | `unit` | `🔱 fork tests/unit/test_d04_write_paths.py` + upgrade 夹具 | P2-02 → UUID 合法 | `commit + test + 未观察` |
| `NS5-T13` | us/ms cutoff 不丢行 | `短途` | `unit` | `🆕` | P2-03 → 时间一致 | `commit + test + 未观察` |
| `NS5-T14` | jitter；cancelling gate done；outbox.dead 事件+指标 | `短途` | `unit` | `🆕` + 扩 outbox 测 | P2-04 → 可观测 dead | `commit + test + 未观察` |
| `NS5-T15` | idle 1s 切 journal_mode ≪ 20 | `短途` | `集成` | `🆕` | P2-05 → 无 20Hz 探针 | `commit + test + 未观察` |
| `NS5-T16` | bootstrap 失败 ready 503 + 计数器 | `短途` | `unit` | `🆕` | P2-06 → 可观测 | `commit + test + 未观察` |
| `NS5-T17` | 指纹/空 extras/PK 409 | `短途` | `unit` | `🔱 fork` task/teams 测 | P2-07 → 幂等与 409 | `commit + test + 未观察` |
| `NS5-T18` | error_message 无 token/路径 | `短途` | `unit` | `🆕` 攻击向量 | P2-08 → 脱敏 | `commit + test + 未观察` |
| `NS5-T19` | identity 非 JSON / DROP mkb_tasks → 非 ready | `短途` | `unit` | `🆕` | P2-09 → ready 诚实 | `commit + test + 未观察` |
| `NS5-T20` | salvage 占 NI；urgent+local 可 salvage；construct 超预算溢流 | `短途` | `unit` | `🔱 fork tests/unit/test_compression_channel.py` `test_dispatch_policy.py` | P3-01 → 池=运输 | `commit + test + 未观察` |
| `NS5-T21` | state=None 读 prompt 失败 | `短途` | `unit` | `🔱 fork test_ns1_generation_cli.py` | P3-02 → fail-closed | `commit + test + 未观察` |
| `NS5-T22` | 单例 client；sleep 放 lease；408 RETRYABLE | `短途` | `unit` | `🔱 fork test_inference_runtime.py` | P3-03 → 门限与重试 | `commit + test + 未观察` |
| `NS5-T23` | argv 无正文；子环境无 token（攻击） | `短途` | `unit` | `🔱 fork test_claude_cli_port.py` | P3-04 → 不泄密 | `commit + test + 未观察` |
| `NS5-T24` | salvage 证据不串 process_uuid | `短途` | `unit` | `🆕` | P3-05 → 不串台 | `commit + test + 未观察` |
| `NS5-T25` | schema digest 漂移 fail-closed；302 非 ready | `短途` | `unit` | `🆕` | P3-06 → freeze | `commit + test + 未观察` |
| `NS5-T26` | 三次 RETRYABLE → retryable_failure | `短途` | `unit` | `🔱 fork test_d01_review_fixes.py`（修正锁错码） | P3-07 → 可重试 | `commit + test + 未观察` |
| `NS5-T27` | CLI max=1 第二次 BACKPRESSURE | `短途` | `unit` | `🆕` | P3-08 → 有门限 | `commit + test + 未观察` |
| `NS5-T28` | PDF blob 不得成功 clean | `短途` | `unit` | `🔱 fork test_ns1_clean_dispatch.py` | P3-09 → 拒二进制 | `commit + test + 未观察` |
| `NS5-T29` | facade embed 满 ⇒ DispatchCaps.embed_running 满 | `短途` | `unit` | `🆕` | P3-10 → 同源背压 | `commit + test + 未观察` |
| `NS5-T30` | g1>16k 不签满 proof | `短途` | `unit` | `🆕` | P4-01 → fail-closed | `commit + test + 未观察` |
| `NS5-T31` | HTML 提取含换行 | `短途` | `unit` | `🆕` 或扩 intake text 测 | P4-02 → 换行保留 | `commit + test + 未观察` |
| `NS5-T32` | 重复 body 第二锚点在后 | `短途` | `unit` | `🔱 fork test_adopt_layered_json.py` | P4-03 → 单调锚 | `commit + test + 未观察` |
| `NS5-T33` | UTF-16 无 BOM 非 latin-1 垃圾 | `短途` | `unit` | `🆕` | P4-04 → 不乱码 | `commit + test + 未观察` |
| `NS5-T34` | 超 cap 假 proof；同 key items=1；digest=bytes | `短途` | `unit` | `🆕` | P4-05 → 身份/字节 | `commit + test + 未观察` |
| `NS5-T35` | stub summary!=original | `短途` | `e2e` | `🔱 fork test_generation_pipeline_contracts.py` | P4-06 → 双通道可区分 | `commit + test + 未观察` |
| `NS5-T36` | 多 JSON 对象拒绝；transport=receipt | `短途` | `unit` | `🆕` | P4-07 → 运输诚实 | `commit + test + 未观察` |
| `NS5-T37` | reject 后 item 非 active | `短途` | `unit` | `🆕` | P4-08 → gate 时序 | `commit + test + 未观察` |
| `NS5-T38` | SPACE_VIOLATION 不重试 | `短途` | `unit` | `🆕` | P4-09 → 原码上抛 | `commit + test + 未观察` |
| `NS5-T39` | 延迟 publish 不回拨；再 upsert serving≠0 | `短途` | `unit` | `🆕` + 015 upgrade | P4-10 → 世代单调 | `commit + test + 未观察` |
| `NS5-T40` | vectorize JSON 无正文 | `短途` | `unit` | `🆕` | P4-11 → envelope 瘦 | `commit + test + 未观察` |
| `NS5-T41` | 字符串 UUID 数组失败 | `短途` | `契约` | `🆕` layered_content | P4-12 → validator | `commit + test + 未观察` |
| `NS5-T42` | 1001 尾部高分命中或错误；LIVE=false+live ns mismatch | `短途` | `unit` | `🔱 fork test_retrieval_service.py` | P4-13 → 召回/空间诚实 | `commit + test + 未观察` |
| `NS5-T43` | 高分 original 保留；root 去重 | `短途` | `unit` | `🔱 fork` pack 测 | P4-14 → dedup/pack | `commit + test + 未观察` |
| `NS5-T44` | deactivate 后检索 409/空（攻击：停用 Team 仍持 token） | `短途` | `unit`/`e2e` | `♻️ 沿用 test_intake_reactivate.py` + 扩 retrieval | P4-15 → team fence | `commit + test + 未观察` |
| `NS5-T45` | 单通道 purge 不灭 serving | `短途` | `unit` | `🆕` | P4-16 → Proof | `commit + test + 未观察` |
| `NS5-T46` | team rebuild 跳过非 serving | `短途` | `unit` | `🔱 fork` rebuild 测 | P4-17 → 不毒死 | `commit + test + 未观察` |
| `NS5-T47` | title 进入 dual 或 schema 拒 | `短途` | `契约` | `🆕` | P4-18 → 字段不丢 | `commit + test + 未观察` |
| `NS5-T48` | 伪造 XFF 不能进 /metrics（攻击） | `短途` | `unit` | `🔱 fork test_security_boundary.py` | P5-01 → 不盲信代理 | `commit + test + 未观察` |
| `NS5-T49` | 桶满不全局放行（攻击） | `短途` | `unit` | `🔱 fork test_security_boundary.py` | P5-02 → overflow 限流 | `commit + test + 未观察` |
| `NS5-T50` | apiKey/signed URL 422 且库无 secret（攻击） | `短途` | `unit` | `🔱 fork` contracts + teams | P5-03 → extras 拒密 | `commit + test + 未观察` |
| `NS5-T51` | 非 pytest 伪造 PYTEST_CURRENT_TEST 开 sqlite 失败（攻击） | `短途` | `unit` | `🔱 fork test_ns4_factory_sqlite_test_only.py` | P5-04 → 双因子 | `commit + test + 未观察` |
| `NS5-T52` | starlette≥1.0.1 | `短途` | `契约` | `🆕` 锁版本断言或 pip-audit | P5-05 → 离开 CVE 范围 | `commit + audit + 未观察` |
| `NS5-T53` | mapped IPv6 loopback 拒绝（攻击） | `短途` | `unit` | `🔱 fork test_security_boundary.py` | P5-06 → unwrap mapped | `commit + test + 未观察` |
| `NS5-T54` | BrokenAudit 第二次仍 503 非无审计 401（攻击） | `短途` | `unit` | `🔱 fork test_security_boundary.py:207-230` | P5-07 → sampler 提交 | `commit + test + 未观察` |
| `NS5-T55` | 超 cap 413 before parse（攻击） | `短途` | `集成` | `🆕` ASGI middleware | P5-08 → body cap | `commit + test + 未观察` |
| `NS5-T56` | tautology 删除 SUT 变红再接回 | `短途` | `unit` | `♻️/🔱` ledger §3.2.1 所列 | P6-01 → 假绿拆除 | `commit + 各 test + 未观察` |
| `NS5-T57` | `uv run ruff check .` 0 | `短途` | `契约` | `♻️ 沿用` ruff | P6-02 → 静态门 | `commit + ruff + 未观察` |
| `NS5-T58` | CW 两 False 不再绿 | `短途` | `unit` | `🔱 fork test_turso_driver.py:112-127` | P6-03 → 探针诚实 | `commit + test + 未观察` |
| `NS5-T59` | wheel 含 sql；干净 venv migrate | `spike` | `契约` | `🆕` packaging smoke | P6-04 → 可安装 | `commit + unzip/migrate + 未观察` |
| `NS5-T60` | 生成+vectorize+retrieval 主链（不含 VF86 检查） | `mega` | `e2e` | `🔱 fork test_generation_pipeline_contracts.py` + 新断言 summary!=original / proof 完整 | P6-05 → 主链 | `commit + mega + 未观察` |
| `NS5-T61` | sidecar 4×20 子进程 soak | `soak` | `集成` | 同 T02 作为退出硬闸复跑 | P1-02/P6-05 → 不 abort | `commit + soak log + 未观察` |
| `NS5-T62` | 长推理 + reclaim：败者 fenced、运输取消 | `soak` | `集成` | 同 T04 拉长 | P1-04/P6-05 → 无双跑 | `commit + soak log + 未观察` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/integration/test_ns4_cw_soak.py` | `🔱 fork → 真并发 soak` | ThreadPool + 行数 + 禁 product 旁路 | 串行 tautology，必须先 RED |
| `tests/unit/test_turso_driver.py` | `🔱 fork` | 删 `or True`；CW 断言 True | `:99` 恒真；`:112-127` 两 False 可绿 |
| `tests/unit/test_ns4_readport_reports.py` | `🔱 fork` | 调真实 ReadPort | 自造 dict |
| `tests/unit/test_ns4_diagnostic_sidecar.py` | `🔱 fork` | 实例化 sidecar | 未调用 SUT |
| `tests/unit/test_object_gc.py` | `♻️ 沿用` + 加 promote-rollback | 非 tautology | 已存在 |
| `tests/unit/test_claude_cli_port.py` | `🔱 fork` | timeout kill；argv/env | 无 timeout 覆盖 |
| `tests/unit/test_workflow_runtime.py` | `🔱 fork` | heartbeat + reclaim | 无长 handler |
| `tests/unit/test_d01_review_fixes.py` | `🔱 fork` | 锁 EXHAUSTED 而非已吞掉的 RETRYABLE | 假绿风险 |
| `tests/e2e/test_generation_pipeline_contracts.py` | `🔱 fork` | `summary!=original`；不新增 sqlite3 检查 | 存在；VF86 路径不碰 |
| `tests/e2e/test_intake_reactivate.py` | `♻️ 沿用` | 0 或少改；P4-15 可扩 | 已有 deactivate→search `[]` |
| `tests/unit/test_security_boundary.py` | `🔱 fork` | XFF/overflow/BrokenAudit/mapped IP | 已有审计测 |
| `tests/unit/test_ns4_factory_sqlite_test_only.py` | `🔱 fork` | 双因子 | 已存在 |
| `tests/e2e/test_index_rebuild.py` 等 sqlite3 检查 | **不改** | VF86 owner-gated | 已知 disk I/O；禁止当本 AP 绿证 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit tests/domain -q` | unit·契约 | 每工作项 / 每 PR |
| spike | 该 Phase 定向文件 | 集成·e2e | 每 Phase 收口 |
| mega | 生成→检索主链（不含 VF86 检查） | e2e | **本 AP 收口** |
| soak | sidecar 4 线程；lease reclaim | 集成 | **退出硬闸** |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 VF86 e2e `sqlite3.connect` Turso 检查（owner NS1-V11）→ harness charter。
- 不覆盖真 GPU / Claude 登录 live soak（VF88）→ NS2-GPU。
- 不覆盖真机 `concurrent_writes=True` constitution e2e（VF91.r）→ NS4 constitution e2e。
- 不覆盖 browser/OCR/Vision E2E（VF97）→ capability charter。
- 不覆盖 billing `has_quota==false`（VF23）→ billing AP。
- 不覆盖全仓 pytest 441/441。**不在本 AP 假装覆盖。**

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组；计数 ≠ 价值。
- 先 RED 后绿：P6-01 必须演示「删 SUT → RED」。
- 禁止新写 `sqlite3.connect` 打开 Turso 文件。
- 禁止 `assert ... or True`、缺文件 `return`、自造 dict。
- `degraded` 必带机器可读 reason。
- 安全项必须含攻击向量（§7.3）。
- pre-existing 失败（VF86 e2e）必须在 closure 标 `deferred` 并指 NS1-V11，不 silent overclaim。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| pyturso CONCURRENT abort | P1 若改真 CONCURRENT 可能更多 native panic | `high` | soak 不稳则诚实 `concurrent_writes=false` |
| VF62×VF10 时序 | 先并发后心跳 = 必现双跑 | `high` | P1-04 硬门闩；CI 测重叠执行 |
| 015 unique 加列 | 已有重复 active 行会升级失败 | `medium` | 先背填/清理再加索引 |
| Starlette/FastAPI 组合 | 0.115.12 可能吃不下 starlette 1.x | `medium` | 升级 FastAPI 主版本；TrustedHost 夹具 |
| VF86 红噪声 | 全量 pytest 仍可能 8 failed | `medium` | closure 显式 deferred；不以全绿为 DoD |
| 假绿回潮 | P6 前合并 tautology 修补 | `high` | P6 最后；§8.5 RED 演示 |
| sidecar 生产默认开 | abort 可杀进程 | `high` | P1-02 未绿前可关默认 sidecar |

### 9.2 约束与前提

- **技术前提**：Python 3.12 `CancelledError` 是 `BaseException`；当前 pyturso 有 `executescript`（VF6 已驳回）。
- **运行时前提**：本轮仍默认 `LIVE_INFERENCE=false` + stub；不要求 GPU。
- **组织协作前提**：不重开 VF class；owner 不在本 AP 解冻 NS1-V11 / billing / browser。
- **上线 / 合并前提**：每 Phase 独立可回滚；P6 前不得标 `executed`。

### 9.3 文档同步要求

- 需要同步更新的设计文档：S12（CW 诚实）、S09/S10（proof/召回 fail-closed 窄句）、S03（heartbeat 接线）、S16（trusted-proxy CIDR）——**窄回填，不重写章节**
- 需要同步更新的说明文档 / README：K 项（CW 剧场、lease、wheel SQL、假绿拆除后的测试陈述）
- 需要同步更新的测试说明：deferred-items-ledger 增加 NS5 余项指针；VF-ledger §6 append

### 9.4 完成后的预期状态

1. 单例连接在 cancel/commit 失败后可再 BEGIN；sidecar 并发不再 abort。
2. publication proof 的 required set 不被静默缩小；检索不再按 UUID 前缀丢掉新知识；单通道 purge 不灭世代。
3. salvage/dispatch_pool 与真实运输一致；CLI 超时回收进程且不把正文放 argv。
4. 公共 extras 拒 secret；默认不信 XFF；限流 overflow 不再全局放行。
5. tautology 拆除；ruff 0；wheel 含 SQL。全量 pytest 仍可能因 VF86 非全绿，closure 诚实记录。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 测试项必须 **PASS 且四元组证据齐全**：

1. 取消 UoW 后再 BEGIN 成功（`NS5-T01`）
2. sidecar 4×20 子进程不 abort（`NS5-T02` / `NS5-T61`）
3. 非法 outbox 不冻 supervisor（`NS5-T05`）
4. 长推理 reclaim 败者 fenced 且运输取消（`NS5-T04` / `NS5-T62`）
5. vectorize 超预算不签满 proof（`NS5-T30`）
6. 主链 mega：summary≠original 且 proof 完整（`NS5-T60`）
7. extras 攻击向量 422（`NS5-T50`）；伪造 XFF 进不了 /metrics（`NS5-T48`）
8. wheel 含 `*.sql` 且干净 venv migrate（`NS5-T59`）
9. tautology 删 SUT 会红（`NS5-T56`）；`ruff check .` 0（`NS5-T57`）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| UoW 可再 BEGIN | P1-01 | NS5-T01 | `commit + test + run-time` | `未观察` |
| sidecar 不 abort | P1-02 | NS5-T02 / T61 | `commit + soak + run-time` | `未观察` |
| CLI child 回收 | P1-03 | NS5-T03 | `commit + test + run-time` | `未观察` |
| 无双跑 | P1-04 | NS5-T04 / T62 | `commit + soak + run-time` | `未观察` |
| outbox 不冻 supervisor | P1-05 | NS5-T05 | `commit + test + run-time` | `未观察` |
| retirement 不占死队头 | P1-06 | NS5-T06 | `commit + test + run-time` | `未观察` |
| GC 两阶段 | P1-07 | NS5-T07 | `commit + test + run-time` | `未观察` |
| 无 _pending 泄漏 | P1-08 | NS5-T08 | `commit + test + run-time` | `未观察` |
| scanner 不永停 | P1-09 | NS5-T09 | `commit + test + run-time` | `未观察` |
| 过期不饿死活任务 | P1-10 | NS5-T10 | `commit + test + run-time` | `未观察` |
| rowcount 归一化 | P2-01 | NS5-T11 | `commit + test + run-time` | `未观察` |
| 014 UUID | P2-02 | NS5-T12 | `commit + test + run-time` | `未观察` |
| 时间戳一致 | P2-03 | NS5-T13 | `commit + test + run-time` | `未观察` |
| dead 可观测 | P2-04 | NS5-T14 | `commit + test + run-time` | `未观察` |
| ready 不切 mode | P2-05 | NS5-T15 | `commit + test + run-time` | `未观察` |
| bootstrap 可观测 | P2-06 | NS5-T16 | `commit + test + run-time` | `未观察` |
| 指纹/extras/409 | P2-07 | NS5-T17 | `commit + test + run-time` | `未观察` |
| 落盘脱敏 | P2-08 | NS5-T18 | `commit + test + run-time` | `未观察` |
| ready 诚实 | P2-09 | NS5-T19 | `commit + test + run-time` | `未观察` |
| 池=运输 | P3-01 | NS5-T20 | `commit + test + run-time` | `未观察` |
| prompt fail-closed | P3-02 | NS5-T21 | `commit + test + run-time` | `未观察` |
| client/lease/408 | P3-03 | NS5-T22 | `commit + test + run-time` | `未观察` |
| CLI 不泄密 | P3-04 | NS5-T23 | `commit + test + run-time` | `未观察` |
| 证据不串台 | P3-05 | NS5-T24 | `commit + test + run-time` | `未观察` |
| schema freeze | P3-06 | NS5-T25 | `commit + test + run-time` | `未观察` |
| EXHAUSTED 可重试 | P3-07 | NS5-T26 | `commit + test + run-time` | `未观察` |
| CLI 门限 | P3-08 | NS5-T27 | `commit + test + run-time` | `未观察` |
| 拒二进制 clean | P3-09 | NS5-T28 | `commit + test + run-time` | `未观察` |
| 同源背压 | P3-10 | NS5-T29 | `commit + test + run-time` | `未观察` |
| vectorize fail-closed | P4-01 | NS5-T30 | `commit + test + run-time` | `未观察` |
| HTML 换行 | P4-02 | NS5-T31 | `commit + test + run-time` | `未观察` |
| 单调锚 | P4-03 | NS5-T32 | `commit + test + run-time` | `未观察` |
| PDF 不乱码 | P4-04 | NS5-T33 | `commit + test + run-time` | `未观察` |
| 身份/字节/预算 | P4-05 | NS5-T34 | `commit + test + run-time` | `未观察` |
| stub 双通道可区分 | P4-06 | NS5-T35 | `commit + test + run-time` | `未观察` |
| JSON/transport | P4-07 | NS5-T36 | `commit + test + run-time` | `未观察` |
| gate 时序 | P4-08 | NS5-T37 | `commit + test + run-time` | `未观察` |
| 原码上抛 | P4-09 | NS5-T38 | `commit + test + run-time` | `未观察` |
| 世代单调 | P4-10 | NS5-T39 | `commit + test + run-time` | `未观察` |
| envelope 瘦 | P4-11 | NS5-T40 | `commit + test + run-time` | `未观察` |
| validator | P4-12 | NS5-T41 | `commit + test + run-time` | `未观察` |
| 召回/空间 | P4-13 | NS5-T42 | `commit + test + run-time` | `未观察` |
| dedup/pack | P4-14 | NS5-T43 | `commit + test + run-time` | `未观察` |
| team fence | P4-15 | NS5-T44 | `commit + test + run-time` | `未观察` |
| purge Proof | P4-16 | NS5-T45 | `commit + test + run-time` | `未观察` |
| rebuild 跳过非 serving | P4-17 | NS5-T46 | `commit + test + run-time` | `未观察` |
| title 字段 | P4-18 | NS5-T47 | `commit + test + run-time` | `未观察` |
| 不盲信 XFF | P5-01 | NS5-T48 | `commit + test + run-time` | `未观察` |
| 限流 overflow | P5-02 | NS5-T49 | `commit + test + run-time` | `未观察` |
| extras 拒密 | P5-03 | NS5-T50 | `commit + test + run-time` | `未观察` |
| sqlite 双因子 | P5-04 | NS5-T51 | `commit + test + run-time` | `未观察` |
| Starlette 离开 CVE | P5-05 | NS5-T52 | `commit + audit + run-time` | `未观察` |
| mapped IPv6 | P5-06 | NS5-T53 | `commit + test + run-time` | `未观察` |
| audit sampler | P5-07 | NS5-T54 | `commit + test + run-time` | `未观察` |
| body cap | P5-08 | NS5-T55 | `commit + test + run-time` | `未观察` |
| tautology 拆除 | P6-01 | NS5-T56 | `commit + RED演示 + run-time` | `未观察` |
| ruff 0 | P6-02 | NS5-T57 | `commit + ruff + run-time` | `未观察` |
| CW 单元诚实 | P6-03 | NS5-T58 | `commit + test + run-time` | `未观察` |
| wheel 含 SQL | P6-04 | NS5-T59 | `commit + unzip/migrate + run-time` | `未观察` |
| 主链 mega | P6-05 | NS5-T60 | `commit + mega + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 87 条 in-scope VF 按 §3 落地；`[true-bug]` 无静默 defer |
| 测试 | §8 短途+spike+硬闸 mega/soak PASS；四元组齐全；VF86 明示 deferred |
| 文档 | README K 窄回填；deferred-items-ledger 接 NS5 余项；VF-ledger §6 append；NS5 closure |
| 风险收敛 | sidecar 不 abort；UoW 可再 BEGIN；VF62 未在无心跳时重叠 |
| 可交付性 | 干净 wheel 含 `migrations/*.sql` 且 migrate 成功；**不**要求全量 pytest 全绿 |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。VF86 全量红必须标 `deferred` 并指 NS1-V11，不把 433 passed 读成行为已被证明。`[true-bug]` 若修不动必须升 blocker 交 owner，禁止改 class。

---

## 11. 执行日志回填（append-only）

> 执行者：`Grok`
> 执行时间：`2026-08-20`
> 文档状态：`draft → executing`
> 代码改动统计：Phase 1 落地中

- **实际执行摘要**：Phase 1 按 DAG 首段落地 P1-01…P1-10（VF1/2/3/9/10/61–70）；VF62 重叠 `run_once` 保持关闭。
- **Phase 偏差（计划 vs 实际）**：
  - P1-02 Turso UoW 保持 `BEGIN IMMEDIATE`（计划偏差 / substrate-fit）：`BEGIN CONCURRENT` 会拒绝同 TX DDL（`test_turso_adapter_runs_manual_vector_sql`），且 sidecar 并发 abort 的根因是第二连接而非业务 UoW。探针改旁路连接，`concurrent_writes_probe` 仍走真实 MVCC+CONCURRENT。
  - P1-07 同 digest 新 catalog UUID 的部分 unique 仍交 P2-02 / 014（顺序调整）：P1 只做 lookup `tombstoned_at IS NULL` + 两阶段 unlink。
- **阻塞与处理**：无。VF10 已接线；`allow_overlapping_run_once=False`。
- **测试发现**：NS5-T01…T10 相关短途 + sidecar 4×20 ThreadPool soak 绿；`test_workflow_runtime` / `test_object_gc` / `test_turso_driver` 回归绿。
- **后续 handoff**：Phase 2 可开工（依赖 P1 UoW 稳定）。

### 11.1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点（file:line） | 备注 |
|--------|------|----|------------------------|------|
| P1-01 | `✅ done` | local | `src/persistence/uow.py`；`sqlite_port.py` `transaction`；`turso/port.py` `transaction` | `except BaseException` + shield rollback + discard |
| P1-02 | `✅ done` | local | `turso/port.py` `_connect`/`readiness`；`sidecar.py`；`engine.py` `restore_journal_mode` | sidecar 单连接+锁+IMMEDIATE；UoW 不切 journal_mode |
| P1-03 | `✅ done` | local | `claude_cli.py` `_terminate_process` | terminate→wait→kill→wait；stdout cap |
| P1-04 | `✅ done` | local | `worker.py` `_heartbeat_loop`；`workflow_supervisor.py` `allow_overlapping_run_once=False` | VF62 重叠未打开 |
| P1-05 | `✅ done` | local | `runtime_outbox.py` `_lease_outbox_row`/`_mark_outbox_dead`；`workflow_supervisor.py` `drain_once` catch | poison 标 dead 后同 tick 继续 |
| P1-06 | `✅ done` | local | `index_retirement.py` `_close_unavailable_intent_tx` | 失活 item 的 intent → abandoned |
| P1-07 | `✅ done` | local | `object_gc.py` `delete_candidate` 两 TX；`local_store.py` `_write_lock`；`artifacts.py` tombstone skip；`lifecycle_apply.py` `released_at` | 部分 unique → P2 |
| P1-08 | `✅ done` | local | `artifacts.py` `discard`/`finally pop`；`worker.py`/`intake/core.py` | 失败/取消也 pop |
| P1-09 | `✅ done` | local | `src/runtime/object_gc.py`；`src/runtime/index_retirement.py` | `except Exception` 不捕 CancelledError |
| P1-10 | `✅ done` | local | `runtime_core.py` `claim_next` 有界循环 | 过期不 `return None` |

### 11.2 时序执行日志

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| `T0` | 重读 AP + VF-ledger + A-1…A-11 | DAG 串行；P5 不插队 |
| `T1` | P1 代码 | UoW helper + sidecar 串行 + heartbeat |
| `T2` | P1 测试 | `uv run pytest` NS5-T01–T10 相关文件 PASS |

### 11.3 文档状态

`draft → executing（2026-08-20 Phase 1）`。
residual：VF67 部分 unique → P2-02。

### 11.4 Phase 2 回填

- **实际执行摘要**：P2-01…P2-09（VF4/5/7/8/71–73/94/98–103）。014 改写 32-hex UUID + live tombstone unique。
- **Phase 偏差**：HealthAggregator 只做 in-flight coalesce，不做跨调用 TTL 缓存（计划偏差 / substrate-fit）——TTL 会把 token 替换后的 /ready 锁成旧结果。journal_mode 抖动已在 P1 探针旁路消除。
- **测试发现**：`test_ns5_phase2.py` + turso/migration/readiness/task 回归绿。

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P2-01 | `✅ done` | `turso/port.py` `_RowcountCursor` | stale UPDATE rowcount==0 |
| P2-02 | `✅ done` | `migration_runner.py` 参数化 INSERT；`014_ns5_uuid_and_tombstone.sql` | 含 VF67 部分 unique |
| P2-03 | `✅ done` | `time.py` us；`artifacts.py` `utc_now()` | |
| P2-04 | `✅ done` | retry full jitter；gate cancelling noop；`outbox.dead` 事件 | |
| P2-05 | `✅ done` | HealthAggregator in-flight coalesce | 无跨调用 TTL |
| P2-06 | `✅ done` | lifespan bootstrap_failures + metric | |
| P2-07 | `✅ done` | fingerprint 排除 audit 时间；PATCH `{}`；PK 409 | |
| P2-08 | `✅ done` | `_safe_persisted_error` | |
| P2-09 | `✅ done` | identity.json parse；`mkb_tasks` sqlite_master | |
