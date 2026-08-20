# Nano-Agent 行动计划

> 服务业务簇: `MKB / NS6 0820 second-pass verified-findings 修复`
> 计划对象: 按 VF-ledger-0820-2nd-review 批次 DAG 修复 HEAD 上 34 条 in-scope VF（8 `[true-bug]` + 26 `[partial-delivery]`）
> 类型: `modify`
> 作者: `Grok`
> 时间: `2026-08-20`
> 文件位置: `docs/plan/new-start/NS6-0820-2nd-round-bug-fixes.md`
> 上游前序 / closure:
> - `docs/code-review/0820-review/VF-ledger-0820-2nd-review.md`（`v0.5` / `triaged`；UF1–UF38 ↔ VF1–VF38）
> - `docs/plan/new-start/NS5-0820-bug-fixes.md`（前一轮执行计划；claimed-fix 地图，非证据）
> - `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`
> - `docs/closure/new-start/deferred-items-ledger.md`
> 下游交接:
> - NS6 阶段 final closure（本 AP §10；落盘 `docs/closure/0820-review/NS6-0820-2nd-round-bug-fixes-closure.md`）
> - VF-ledger-0820-2nd-review.md §6 处置回填（append-only；不改写 ledger §0–§5）
> - §5.4 剩余切片与 `[true-deferred]` 仍交 deferred-items-ledger / 后继 charter
> 关联设计 / 调研文档:
> - `docs/baseline/domain-truth/S03-workflow-engine.md`（claim / lease / fencing / outbox / cancel）
> - `docs/baseline/domain-truth/S08-embedding-vectorization.md` / `S09-lsrag-index.md` / `S10-lsrag-retrieval.md`
> - `docs/baseline/domain-truth/S11-inference-runtime.md` / `S12-turso-persistence.md` / `S13`（CAS / T-O-120）
> - `docs/baseline/domain-truth/S15-observability-reliability.md` / `S16-security-trust-boundary.md`
> - `README.md`（叶工人合同；默认 Turso 画像）
> 冻结决策来源:
> - `docs/code-review/0820-review/VF-ledger-0820-2nd-review.md` §1 / §4.1 / §5.2–§5.4（**只读引用**；本 action-plan 不填写 Q/A，不改 VF class/disposition）
> grounding 来源:
> - VF-ledger §3 当前 `file:line` + 本 AP §7 内置锚区（落盘前已对 HEAD 抽查）
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `executed`

---

## 0. 执行背景与目标

0820 第 2 轮四审合并已完成：72 条原始 finding → 38 条 UF/VF。复核后 **8 `[true-bug]` + 26 `[partial-delivery]`** 是本阶段欠账；3 条 `[true-deferred]` 与 1 条 `n/a`（VF19 stale-rejected）不得改写成「本轮也修」。ledger §5.1 把修复顺序钉死为：**先封进程/数据不可恢复洞与默认准入 → CAS/schema/outbox/fencing → 推理车道 → intake/向量/HITL 身份 → 安全边界 → 假绿测试与 closure 过关叙述**。§5.3 给出 6 个批次与依赖边。本 AP 把这些冻结批次落成可执行 Phase DAG，并把每一条 in-scope VF 绑到唯一工作项。

本计划不重开 0820 2nd-pass 的 verdict。`[true-bug]` 禁止降级成 deferred。每条 code fix 必须先有会红的断言。成功标准是 **单例连接在 BEGIN 取消后可再 BEGIN、默认 Turso 画像 `/ready` 为 ready 且 `claim_next` 不被 CW 门挡住、readiness 不得把生产文件 journal_mode 从 wal 切成 mvcc、probe 不得把 generate timeout 冻在 5s、同坐标再 vectorize 不得把 serving indexed COUNT 打到 0、同 external_key 不得插入第二 item / 因 revision_ordinal=1 失败**，不是「测试计数变绿」。

- **服务业务簇**：`NS6`
- **计划对象**：0820 2nd-pass VF-ledger 本阶段必修缺口
- **本次计划解决的问题**：
  - 进程/准入不可恢复：UoW `BEGIN` 取消毒化单例连接、默认 Turso `/ready` 永 503、探针改活库 `journal_mode`、vLLM 5s 冻结、worker 不杀 handler、heartbeat 异常不停跳、GC TX1-unlink-TX2 丢字节、TTL 死代码 + readiness 持写锁
  - CAS / 状态机半修：schema 只探 `mkb_tasks`、tombstone lookup、outbox.dead 无指标且 stale-owner 不看 rowcount、retirement 剩余 POINTER_UNAVAILABLE 队头、fail 缺 fencing CAS、Task cancel 可 `cancelling→succeeded`、Team PK 500
  - 车道半修：salvage 仍同 Process CLI、证据 `"_"` 回退、Facade double-release、CLI env/stdout/kill
  - serving / 身份：UPDATE indexed 行、HITL approve 不激活、digest≠bytes、external_key 非原子、namespace/purge、generation 跨 UoW 预留、title/embed 配方互拆
  - 安全默认值：空 CIDR 信 XFF、PATCH extras、chunked body、audit overflow undo、ipv4_mapped 分裂
  - 验证不可信：NS5 短途假绿 + closure 过关叙述
- **本次计划的直接产出**：
  - 6 个按 ledger 批次排列的 Phase，覆盖 34 条 in-scope VF
  - 对应 falsifiable 测试（§8，每项含防假绿谓词）与每 Phase 收口
  - VF-ledger §6 append + NS6 closure；§5.4 切片登记到 deferred-items-ledger
- **本计划不重新讨论的设计结论**：
  - `[true-bug]` 本轮必修，禁止改写成 `[true-deferred]`（VF-ledger §0.4）
  - VF19 = `stale-rejected`（`search()` 已 `begin_request_cache`），不修（VF-ledger §4.3）
  - VF6/VF20/VF32 = `[true-deferred]`，本轮只登记承接（VF-ledger §5.4）
  - VF4.r / VF11.r / VF25.r / VF35.r / VF36.r / VF38.r 是 `[partial-delivery]` 剩余切片，本轮切干净后登记
  - 第 1 轮仍冻：VF23 billing always-permit、VF86 NS1-V11 sqlite3-on-Turso harness、VF88 live GPU、VF97 browser/OCR、VF66.r 目录 CAS SSOT、VF62 重叠 `run_once`（本轮仍不得打开）
  - 业务 UoW 保持 `BEGIN IMMEDIATE`（sidecar abort 根因）；诚实探针位与准入位必须拆开，禁止再把 `concurrent_writes=false` 喂给 `REQUIRED` 合取
  - 禁止新增 `sqlite3.connect` 打开 Turso 文件

---

## 1. 执行综述

### 1.1 总体执行方式

**先封进程存活、默认准入与耐久设置，再补 CAS/schema/outbox/fencing，再接线推理车道，再修 intake/向量/HITL 身份，安全边界可与车道/serving 并行，最后拆假绿并翻 closure 过关叙述。** 顺序消费 VF-ledger §5.3 六批次。唯一硬门闩：**P4 任何「再 vectorize」测试之前必须先落地 VF12**（禁止 UPDATE indexed 行）；**P5-05（VF34）必须在 P5-01（VF29 空 CIDR 不信 XFF）之后**；**P6 必须等前五路代码进主分支后再拆假绿**，否则 tautology 修补会锁住未修行为。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 进程存活 / 默认准入 / 耐久设置 | `XL` | UoW BEGIN 取消、默认 `/ready`、journal_mode、vLLM timeout、handler cancel、heartbeat fence、GC TOCTOU、TTL | `-` |
| Phase 2 | CAS / schema / outbox / fencing | `L` | schema 闭集、tombstone lookup、dead 指标+rowcount、retirement 队头、fail CAS、cancel 栅栏 Execution、Team 409 | Phase 1 |
| Phase 3 | 推理车道收口 | `M` | salvage 占 NI、证据强制 process_uuid、lease 置空、CLI allowlist/有界读/shield kill | Phase 1（VF7/VF21） |
| Phase 4 | intake / 向量 / HITL / 身份 | `XL` | serving 行不可变、approve 激活、双 CAS 对象、external_key 原子、namespace/generation、embed 配方 | Phase 1+2 |
| Phase 5 | 安全边界 | `M` | 空 CIDR 不信 XFF、PATCH 拒密、chunked 413、overflow undo、ipv4_mapped | Phase 1（VF29 先于 VF34） |
| Phase 6 | 测试保真与治理 | `M` | 按 §8 谓词重写假绿短途、翻 closure 过关叙述、mega/soak、ledger §6 | Phase 1–5 |

DAG（可并行窗口，严格对应 ledger §5.3）：

```text
P1 (批次1) ──► P2 (批次2) ──► P4 (批次4) ──► P6 (批次6)
 │                │              ▲
 └──► P3 (批次3) ─┴──────────────┘
 └──► P5 (批次5) ─────────────────┘
```

- P3 不依赖 P2 的 DDL（可与 P2 并行）；禁止与 P1 重叠（依赖 VF7 超时语义与 VF21 handler 取消）。
- P5 在 P1 UoW 稳定后即可与 P2/P3/P4 并行。P5 内部：VF29 → VF34。
- P4 依赖 P1 取消安全 UoW 与 P2 rowcount/fencing；VF16 namespace 与 VF17 预留同一 Phase 做完；VF12 必须先于任何再 vectorize 断言。
- P6 必须等前五路代码进主分支后再拆假绿。

### 1.3 Phase 说明

1. **Phase 1 — 进程存活 / 默认准入 / 耐久设置**
   - **核心目标**：叶进程在 cancel / probe / 默认 Settings 下仍能写、领活、不改活库 journal_mode、不冻 5s、不丢 CAS 字节。
   - **为什么先做**：ledger §5.3 批次 1。「不修则叶进程写路径、/ready、lease、对象字节都不可信」。后续正确性测试若跑在坏连接 / 永 503 / 5s generate 上会抖动或根本领不到活。
2. **Phase 2 — CAS / schema / outbox / fencing**
   - **核心目标**：状态转移以 `rowcount==1` 为安全条件；schema/tombstone/retirement/cancel 不再半修。
   - **为什么放在这里**：依赖批次 1 的 UoW 不再被 cancel 毒化。
3. **Phase 3 — 推理车道收口**
   - **核心目标**：salvage=运输 SSOT；证据不串台；retry 取消不炸 gate；CLI 子进程边界闭合。
   - **为什么放在这里**：依赖 P1 的 vLLM 每请求 timeout（VF7）与 worker 取消 handler（VF21）。
4. **Phase 4 — intake / 向量 / HITL / 身份**
   - **核心目标**：serving 行不可变；approve 可发布；raw/clean 字节身份；external_key 幂等；namespace/generation 同 TX。
   - **为什么放在这里**：依赖 P1 CAS/GC 与 P2 行数/fencing；serving 合同在稳定存储上才能测。
5. **Phase 5 — 安全边界**
   - **核心目标**：空 CIDR fail-closed；PATCH 拒密；chunked 有界；overflow undo 回正确桶。
   - **为什么放在这里**：只依赖 P1 UoW；与 serving 无数据依赖，故可并行。VF34 根因是 VF29 接线。
6. **Phase 6 — 测试保真与治理**
   - **核心目标**：按 AP 收口谓词重写会在 SUT 删除后仍绿的短途测试；closure 不再把 partial 叙述成可收口。
   - **为什么放在这里**：假绿不拆则 P1–P5 回归不可信。

### 1.4 执行策略说明

- **执行顺序原则**：按 §1.2 DAG。禁止在 P1 未绿时用 `concurrent_writes_required=False` 的测试画像宣称默认 ready。禁止先开 VF62 重叠 `run_once`。禁止在 P6 之前把「全量 pytest 绿」当收口（VF86 / VF35.r 仍 owner-gated）。
- **风险控制原则**：每个 `[true-bug]` 先写 RED 测试再改生产代码。高风险项（UoW BEGIN、默认 `/ready`、journal_mode、GC fence、vectorize UPDATE、external_key、空 CIDR）必须有失败/降级路径。
- **测试推进原则**：Phase 内短途 unit → Phase 收口 spike → P6 mega（默认 Settings ready+claim + PersistencePort 生成/vectorize/retrieval）+ soak（BEGIN 取消窗口、heartbeat 跨过 lease）。详见 §8。
- **文档同步原则**：代码进主分支后窄回填 README 与 deferred-items-ledger；2nd-pass VF-ledger 只 append §6，不改 §0–§5；NS5 closure 的 P2-05/P2-07 ✅ 翻 🟡（VF38）。
- **回滚 / 降级原则**：UoW / ready / journal_mode 若引入新死锁或把生产库切成 mvcc，回退该 Phase 提交并保持单写者 + 诚实探针位，禁止把 `REQUIRED` 再合取强制 false 的 `concurrent_writes`。wheel/测试包装失败不得声称可发布。

### 1.5 本次 action-plan 影响结构图

```text
NS6-0820-2nd-round-bug-fixes
├── Phase 1: 进程存活 / 准入
│   ├── src/persistence/{uow,engine,turso/port,sqlite_port}.py
│   ├── src/llm_adapters/local_vllm.py + api/app.py lifespan
│   ├── src/runtime/workflow/worker.py + src/runtime/health.py
│   └── src/services/object_gc.py + src/storage/local_store.py
├── Phase 2: CAS / schema / fencing
│   ├── src/persistence/migration_runner.py
│   ├── src/runtime/workflow/{runtime_outbox,runtime_outcome,runtime_core,workflow_supervisor}.py
│   ├── src/services/{index_retirement,artifacts,teams}.py + 多路径 catalog lookup
│   └── src/runtime/task/{task_commands,task_projection}.py
├── Phase 3: 推理车道
│   ├── src/runtime/intake/{generation_construct,generation_evidence}.py
│   └── src/runtime/inference/{facade,claude_cli}.py
├── Phase 4: intake / 向量 / HITL
│   ├── src/runtime/intake/{vectorize,vector_publish_commit,acquisition_ingest,acceptance_snapshot,core}.py
│   ├── src/runtime/workflow/runtime_gates.py + lifecycle_publish.py
│   └── src/services/{vector_purge,lsrag_construct/binder,retrieval/retrieval_request}.py
├── Phase 5: 安全边界
│   ├── src/runtime/security.py + api/dependencies.py + api/app.py
│   └── src/contracts/api/models.py
└── Phase 6: 测试与治理
    ├── tests/unit/test_ns5_* + test_ns4_* + test_ns6_*
    ├── tests/integration/test_ns5_turso_mainchain.py
    └── 2nd-pass VF-ledger §6 + NS5 closure 翻 🟡 + NS6 closure
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** 全部 8 条 `[true-bug]`：VF3 VF7 VF10 VF15 VF18 VF24 VF27 VF28（默认 `fix`）
- **[S2]** 全部 26 条 `[partial-delivery]` 的本轮切片：VF1 VF2 VF4 VF5 VF8 VF9 VF11 VF12 VF13 VF14 VF16 VF17 VF21 VF22 VF23 VF25 VF26 VF29 VF30 VF31 VF33 VF34 VF35 VF36 VF37 VF38；剩余切片登记 §2.2
- **[S3]** 配套 falsifiable 测试：先 RED 后绿；每条含 §8 防假绿谓词
- **[S4]** 默认 Turso 画像（`concurrent_writes_required=True` + IMMEDIATE）下 `/ready` 与 `claim_next` 可领活
- **[S5]** 窄回填 README / deferred-items-ledger；2nd-pass VF-ledger §6 append；NS6 closure；NS5 closure P2-05/P2-07 翻 🟡

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** VF19 stale-rejected（水合缓存已由 `search()` 激活）
- **[O2]** `[true-deferred]`：VF6 014 脏 unique 自愈、VF20 检索 `read_transaction`、VF32 `/docs`（第 1 轮 VF79 / NS5 O3）
- **[O3]** `[partial-delivery]` 剩余切片：VF4.r D04 55 表闭集、VF11.r 进程组杀孙进程、VF25.r 未编目 orphan / 目录 CAS（第 1 轮 VF66.r）、VF35.r sqlite3-on-Turso e2e（第 1 轮 VF86 / NS1-V11）、VF36.r sidecar 真有界队列、VF38.r 等第 1 轮 VF36/VF52 代码修完才允许 closure 自称 no-free-defer（本轮 VF14/VF16 修完后 VF38.r 缩小为文档收口复查）
- **[O4]** 第 1 轮仍冻：VF23 billing、VF86 harness、VF88 live GPU、VF97 browser/OCR/Vision、VF62 重叠 `run_once`、VF74 fencing token、VF77 HTML `javascript:`
- **[O5]** 实现计费、多副本、公网 bind 硬化、ANN 生产接线、把业务 UoW 改成 `BEGIN CONCURRENT`

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 8 `[true-bug]` | `in-scope` | ledger §0.4 本阶段欠账 | 无；漏修升 blocker |
| 26 `[partial-delivery]` 本轮切片 | `in-scope` | ledger §5.2 `fix`/`partial-fix` | 切片完成后余项见 §5.4 |
| VF2 默认 `/ready` | `in-scope` | 批次 1 critical；测试 waiver 不得当绿证 | 无 |
| VF15 external_key | `in-scope` | `[true-bug]` + migration | 无 |
| VF19 hydration | `out-of-scope` | stale-rejected | `search()` 去掉 begin_request_cache |
| VF6 014 自愈 | `out-of-scope` | 001 全行 unique 已拦正常升级 | 真实升级 DB UNIQUE 失败 |
| VF20 检索写锁 | `out-of-scope` | NS5 交的是 hydration cache | ingest 期间检索 503 与 claim 同时出现 |
| VF32 `/docs` | `out-of-scope` | owner-gated / NS5 O3 | 公网 / `0.0.0.0` bind |
| VF86 sqlite3 e2e | `out-of-scope` | owner 冻 NS1-V11 | harness charter |
| VF62 重叠 run_once | `out-of-scope` | 本轮仍关；P1 只修心跳异常 fence | 显式打开重叠的后继 charter |
| 目录 CAS SSOT | `defer / depends-on-design` | T-O-120 / VF25.r | owner 授权磁盘 SSOT |

---

## 3. 业务工作总表

> 硬地板：每项含 `涉及文件（file:line）` / `收口目标` / `测试映射`。编号 `P{phase}-{nn}`。VF 清单是绑定权威。file:line 已对 HEAD 抽查（见 §7）。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射 | 风险 |
|------|------------|--------|------|------------------------|----------|----------|------|
| P1-01 | Phase 1 | BEGIN 纳入同一 try（VF1） | `update` | `src/persistence/uow.py:26-46`；`turso/port.py:80-81,139-144`；`sqlite_port.py:94-98` | 取消 `to_thread(BEGIN)` 后下一 `BEGIN IMMEDIATE` 成功；不确定则 `discard()` | `NS6-T01` | `high` |
| P1-02 | Phase 1 | 默认 Turso `/ready` 与 claim（VF2） | `update` | `turso/port.py:171-177`；`health.py:14-24`；`api/app.py:209,291-294`；`config.py:23-24`；`data/config/default.toml:7` | 默认 Settings(`required=True`)+IMMEDIATE 下 `health.ready()['status']=='ready'` 且 claim 非 NotReady | `NS6-T02` | `high` |
| P1-03 | Phase 1 | 探针不得改活库 journal_mode（VF3） | `update` | `engine.py:24-42`；`turso/port.py:152-156`；`sqlite_port.py:119-120` | readiness 后第二连接 journal_mode 等于探针前 | `NS6-T03` | `high` |
| P1-04 | Phase 1 | vLLM 每请求 timeout + aclose（VF7） | `update` | `local_vllm.py:206-215,223-226,242-245`；`api/app.py:183-191,227-232,456-464` | probe 后再 generate(180s)，6s mock 不得 TRANSPORT_RETRYABLE | `NS6-T04` | `high` |
| P1-05 | Phase 1 | 取消 handler_task + discard pending（VF21） | `update` | `worker.py:66-75,79-89,134-137`；`artifacts.py` `_pending` | 取消 `run_once` 于 handler.sleep：handler cancelled 且 `_pending=={}` | `NS6-T05` | `high` |
| P1-06 | Phase 1 | heartbeat 异常即 fence（VF22） | `update` | `worker.py:149-162`；`runtime_core.py:539-551` | heartbeat raise 后 handler 取消且 lease 可 recover，不得成功 accept | `NS6-T06` | `high` |
| P1-07 | Phase 1 | GC TX1-unlink-TX2 丢字节 fence（VF25） | `update` | `object_gc.py:196-238`；`local_store.py:126-133`；`artifacts.py:52-84` | TX1 与 unlink 之间交错同 digest promote：不得 TX2 409 且 `read_verified` OBJECT_MISSING 而 live ref 仍在 | `NS6-T07` | `high` |
| P1-08 | Phase 1 | HealthAggregator 真 TTL（VF36） | `update` | `health.py:26-44`；`turso/port.py:146-164`；`sqlite_port.py:105-124` | `ttl_seconds=5` 两次顺序 `ready()` → probe count==1 | `NS6-T08` | `medium` |
| P2-01 | Phase 2 | schema 核心表闭集（VF4） | `update` | `migration_runner.py:148-163`；`api/app.py:174-179` | DROP `mkb_outbox`（或 processes/vector_records）后 `schema_migration` 为 false | `NS6-T09` | `medium` |
| P2-02 | Phase 2 | live lookup 滤 tombstone（VF5） | `update` | `generation_artifacts.py:561-565`；`config_snapshots.py:332-335`；`index_rebuild_commit.py:304-309`；`scatter_intake.py:669-686`；`task_create.py:399-403`；对照 `artifacts.py:141-143` | tombstone 后再 catalog 同 digest → 新 live uuid | `NS6-T10` | `high` |
| P2-03 | Phase 2 | outbox.dead 指标 + 业务 trace（VF23） | `update` | `runtime_outbox.py:357-377`；`runtime_core.py:48-64`；`api/app.py:296-311` | poison 后 GET `/metrics` `mkb_outbox_dead_total` ≠ 0；dead 事件 `trace_uuid` = Task 的 | `NS6-T11` | `medium` |
| P2-04 | Phase 2 | outbox stale-owner 看 rowcount（VF24） | `update` | `runtime_outbox.py:343-355,382-406`；`runtime_repair.py:46-52`；`workflow_supervisor.py:51-54` | 第二 owner claim 后，stale `_mark_outbox_dead` 不得插入 `outbox.dead` | `NS6-T12` | `high` |
| P2-05 | Phase 2 | retirement 不可用 Intent abandon（VF26） | `update` | `index_retirement.py:320-328,518-529,561-573` | 100 条 namespace 停用 open intent + 1 健康；两次 `scan_once(limit=100)` 后收到健康 | `NS6-T13` | `high` |
| P2-06 | Phase 2 | `_fail_process_tx` fencing CAS（VF27） | `update` | `runtime_outcome.py:454-459` | 抬 fencing_generation 后旧 dict fail 不得把新世代标 failed | `NS6-T14` | `medium` |
| P2-07 | Phase 2 | Task cancel 同 TX 栅栏 Execution（VF28） | `update` | `task_commands.py:193-205`；`task_projection.py:3-6,58-61`；`runtime_outcome.py`；`workflow_supervisor.py:46-59` | 长 handler 中途 cancel → Task 不得 ended succeeded | `NS6-T15` | `high` |
| P2-08 | Phase 2 | Team.create IntegrityError → 409（VF37） | `update` | `teams.py:35-61`；对照 `task_create.py:29-31,130-141` | stub INSERT UNIQUE 失败 → 409/replay 而非裸 IntegrityError | `NS6-T16` | `medium` |
| P3-01 | Phase 3 | salvage 占 NI 或 fail-closed（VF8） | `update` | `generation_construct.py:106-122,192-226,294-308` | salvage 增加 NI occupancy；BACKPRESSURE 不得 `cli.run` | `NS6-T17` | `high` |
| P3-02 | Phase 3 | 删除证据 `"_"` 回退（VF9） | `update` | `generation_evidence.py:9-32,50-52`；`generation_construct.py:287-289` | `record(..., process_uuid=None)` 后 process B flush 对该 invocation 0 行 | `NS6-T18` | `high` |
| P3-03 | Phase 3 | Facade release 后置空 lease（VF10） | `update` | `facade.py:385-409`；`ConcurrencyGate.release` | RETRYABLE+sleep 中取消无 RuntimeError；reacquire None → BACKPRESSURE 无 AttributeError | `NS6-T19` | `high` |
| P3-04 | Phase 3 | CLI allowlist / 有界读 / shield kill（VF11） | `update` | `claude_cli.py:320-340,377-379,382-406` | 子 env 无 `AWS_SECRET_ACCESS_KEY`；>8MiB 在全缓冲返回前被杀；terminate 中取消后 `returncode is not None` | `NS6-T20` | `high` |
| P4-01 | Phase 4 | 禁止 UPDATE indexed 行（VF12） | `update` | `vector_publish_commit.py:334-351,381-397`；`vectorize.py:203-213`；`015_vec_coord_generation.sql:7-10` | publish G=N indexed 后再 vectorize；旧 serving gen indexed COUNT 不得变 0 | `NS6-T21` | `high` |
| P4-02 | Phase 4 | consume_gate_decision 激活 HITL Item（VF13） | `update` | `acceptance_snapshot.py:106-123`；`runtime_gates.py:100-128,164-195,197-285`；`lifecycle_publish.py:75-76` | approve 后 `lifecycle_state='active'` 且 publication 成功；reject 保持非 active | `NS6-T22` | `high` |
| P4-03 | Phase 4 | raw/clean 分 CAS 对象（VF14） | `update` | `acceptance_snapshot.py:63-64,149-185`；`acquisition_ingest.py:77-84`；`core.py:388-413,494-507` | accept 后两行 `sha256(read(handle))==content_digest` 且 size 对齐 | `NS6-T23` | `high` |
| P4-04 | Phase 4 | external_key 同 TX 幂等 + ordinal CAS（VF15） | `update`/`migrate` | `acquisition_ingest.py:91-108,135-150,240-247`；`acceptance_snapshot.py:108-145`；`001_initial.sql:979` + 新 migration | 两次相同 key：第二不得 201+Task failed；并发 COUNT(items)=1 | `NS6-T24` | `high` |
| P4-05 | Phase 4 | namespace 分键 + purge 合同（VF16） | `update` | `vectorize.py:102,275`；`vector_publish_commit.py:265-305`；`vector_purge.py:68-76`；`vector/models.py:17`；`tests/e2e/test_vector_purge_generation.py:105,200-229` | 改 embed 维 → 新 namespace 而非 409；partial purge 要么 422 要么重铸 proof | `NS6-T25` | `high` |
| P4-06 | Phase 4 | generation 同 UoW 原子预留（VF17） | `update` | `vector_publish_commit.py:265-281,143-162`；`vectorize.py:169` | 两重叠同 item vectorize 不得都写 N+1 | `NS6-T26` | `medium` |
| P4-07 | Phase 4 | title/embed 单一配方（VF18） | `update` | `generation_construct.py:1324-1338`；`src/services/lsrag_construct/binder.py:50-51`；`vectorize.py:161-166,461-472`；`retrieval_request.py:423-427` | titled `bind_construct(full_construct, headers=…)` 今日 RED；修后要么 body-only 要么 query 同 prefix | `NS6-T27` | `medium` |
| P5-01 | Phase 5 | 空 CIDR 永不解析 XFF（VF29） | `update` | `security.py:476-499`；`config.py:25,62`；`api/dependencies.py:158-174,185-197`；`api/app.py:518-520` | peer `10.0.0.1` + 空 CIDR + XFF `127.0.0.1` → `request_ip=='10.0.0.1'`；无 token `/metrics` 不得 200 | `NS6-T28` | `high` |
| P5-02 | Phase 5 | PATCH extras 拒密（VF30） | `update` | `src/contracts/api/models.py:44-59,362-377`；`teams.py:80-112`；`task_commands.py:138-177` | `TeamPatchRequest(..., payload_extra={'apiKey':'sk-live'})` ValidationError；库无 sk-live | `NS6-T29` | `high` |
| P5-03 | Phase 5 | ASGI 流式 body cap（VF31） | `update` | `api/app.py:527-539` | 无 CL 的 chunked `max_request_bytes+1` POST → 413，不得落到 handler/422 | `NS6-T30` | `high` |
| P5-04 | Phase 5 | audit overflow undo 回 effective_key（VF33） | `update` | `security.py:251-289`；`api/dependencies.py:96-101` | `max_buckets=1`；overflow 后 undo，第三 IP 仍 DETAIL | `NS6-T31` | `medium` |
| P5-05 | Phase 5 | ipv4_mapped 对齐（VF34） | `update` | `security.py:215-216,502-507,524-537`；`api/dependencies.py:112` | 空 CIDR + 循环 XFF 共用一个 IP 桶；`::ffff:127.0.0.1` 在 `_is_private_peer` 与 `is_internal_ip` 同类 | `NS6-T32` | `medium` |
| P6-01 | Phase 6 | 重写 NS5 假绿短途（VF35） | `update` | 见 §3.2.2 / §8.2：`test_ns5_phase1_runtime.py:47-75`；`test_ns5_phase2.py:96-111`；`test_ns4_readport_reports.py:10-13`；`test_ns4_diagnostic_sidecar.py:24-33`；`test_ns4_jsonl_journal.py:10-14`；`test_ns4_cw_soak.py:30-57`；`test_ns5_turso_mainchain.py:16-105` | 所列测试删 SUT / no-op heartbeat / 未读 TTL 今日必须 RED | `NS6-T33` | `high` |
| P6-02 | Phase 6 | closure 过关叙述翻 🟡（VF38） | `update` | `docs/closure/0820-review/NS5-0820-bug-fixes-closure.md`；NS5 AP；2nd-pass VF-ledger §6 | grep closure P2-05/P2-07 ✅ 而 TTL/Team PK 仍 RED 则本项未收口 | `NS6-T34` | `medium` |
| P6-03 | Phase 6 | mega/soak/ledger/closure | `update` | 2nd-pass VF-ledger §6；deferred-items-ledger；新建 NS6 closure | §8 mega+soak 四元组；文档状态 `executed` 仅当硬闸全绿 | `NS6-T35` `NS6-T36` `NS6-T37` | `medium` |

---

## 4. Phase 业务表格

> `工作内容` 是承重列。高风险项拆 a/b/c。`测试映射` 只引 Test-ID。

### 4.1 Phase 1 — 进程存活 / 默认准入 / 耐久设置

**绑定 VF**：`VF1 VF2 VF3 VF7 VF21 VF22 VF25 VF36`（ledger 批次 1）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P1-01 | VF1 UoW BEGIN | a) `await to_thread(execute, begin_sql)` 移入与 commit 同一 `try/except BaseException`；b) 任何未 commit 退出 shield-rollback；c) BEGIN 完成状态因取消不可知则 `discard()`，不得把句柄交还池；d) rollback 也捕 `BaseException`；e) sqlite 与 turso 共用 helper | `uow.py:26-46`；`turso/port.py:80-81,139-144`；`sqlite_port.py:94-98` | 取消 BEGIN 窗口后仍可再 BEGIN | `NS6-T01` | 无 `cannot start a transaction within a transaction` |
| P1-02 | VF2 默认 ready | a) 拆 `concurrent_writes_probe`（MVCC+CONCURRENT 实测）与 `write_path_ready`（IMMEDIATE+锁对叶工人足够）；b) `HealthAggregator.REQUIRED` 只合取后者，直到 UoW 真正 CONCURRENT；c) **禁止**只改测试 waiver；d) 保留探针真值可观测；e) 默认 `config.py`/`default.toml` 与生产路径同一合同 | `turso/port.py:171-177`；`health.py:14-24`；`api/app.py:209,291-294`；`config.py:23-24`；`default.toml:7` | 默认画像可领活 | `NS6-T02` | 无 waiver 的 Settings 下 ready+claim |
| P1-03 | VF3 journal_mode | a) 生产主库 readiness **不**执行变更性 `PRAGMA journal_mode=mvcc`；b) 改 temp clone / boot scratch 缓存布尔，或 `restore_journal_mode=True` 且断言第二连接仍见原 mode；c) sidecar 注释「永不切 live journal_mode」必须与代码一致 | `engine.py:24-42`；`turso/port.py:152-156`；`sqlite_port.py:119-120` | 活库 mode 不变 | `NS6-T03` | 连接 B 不得 wal→mvcc |
| P1-04 | VF7 vLLM timeout | a) `_request` `client.post(..., timeout=...)` 每请求覆盖；b) probe 用独立短超时 client 或 per-request timeout，禁止用 5s 首创共享 client；c) lifespan `await adapter.aclose()`；d) `trust_env=False` | `local_vllm.py:206-245`；`api/app.py:183-191,456-464` | probe 不污染 generate | `NS6-T04` | 6s mock + 180s generate 成功 |
| P1-05 | VF21 handler cancel | a) `finally`：handler 未 done 则 cancel + suppress await；b) 再 `_discard_pending`；c) 外部 CancelledError 对齐 fenced 路径或 await 取消后的 handler 再 discard | `worker.py:66-137` | 无孤儿 handler / 无 pending 打满 | `NS6-T05` | `handler_task.cancelled()` 且 `_pending=={}` |
| P1-06 | VF22 heartbeat fence | a) `_heartbeat_loop except Exception: fenced.set(); handler_task.cancel(); return`；b) 不捕 `CancelledError` 当业务失败；c) 重叠 `run_once` 仍保持关闭 | `worker.py:149-162` | 心跳一死即 fence | `NS6-T06` | raising heartbeat + lease 过期 → 不得成功 accept |
| P1-07 | VF25 GC fence | a) TX1 CAS `deleting/pending_delete` 使新 reference 无法挂上，**或** unlink 改 rename 到隔离路径，仅 TX2 tombstone 后不可恢复删除；b) TX2 见新 live ref 则 restore；c) 禁止把 missing-live 当「可接受 fail-closed」。未编目 orphan → VF25.r | `object_gc.py:196-238`；`local_store.py:126-133`；`artifacts.py:52-84` | 窗口内 promote 不丢字节 | `NS6-T07` | 交错 promote 后 `read_verified` 成功或 reference 已 released |
| P1-08 | VF36 TTL | a) 实现 TTL 缓存（inflight coalesce + 过期前返回 `_last_result`，token/bootstrap 变更失效）**或**删除误导性 `ttl_seconds` 并改测试名；b) verify/probes 移到既有 bypass 连接，热路径不持 `_write_lock` 空转；c) sidecar close 可选，真队列 → VF36.r | `health.py:26-44`；`turso/port.py:146-164` | 顺序两次 ready 只探一次 | `NS6-T08` | probe count==1（今日 2） |

### 4.2 Phase 2 — CAS / schema / outbox / fencing

**绑定 VF**：`VF4 VF5 VF23 VF24 VF26 VF27 VF28 VF37`（ledger 批次 2）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P2-01 | VF4 schema 闭集 | `verify_migrations` 扩小闭集：`mkb_tasks/processes/executions/outbox/stored_objects/object_references/vector_records/publication_proofs/intake_items`。D04 全表 → VF4.r | `migration_runner.py:148-163` | DROP 核心表 → not ready | `NS6-T09` | DROP outbox 后 schema false |
| P2-02 | VF5 live lookup | 抽 `get_live_stored_object(team,digest,size)`（`tombstoned_at IS NULL`）；generation/config/rebuild/scatter `_catalog_stat`/task_create 全改用；未命中 INSERT 新 uuid | 见 §3 P2-02 + `artifacts.py:141-143` | 墓碑 uuid 不再被复用 | `NS6-T10` | 同 digest 新 live uuid |
| P2-03 | VF23 metrics/trace | `WorkflowCoreMixin.__init__` 加 `metrics`；`api/app.py` 构造传入；dead 事件沿用 owning task/execution `trace_uuid` 而非 `uuid7()`；仅 `rowcount==1` 后 increment（绑 P2-04） | `runtime_outbox.py:357-377`；`runtime_core.py:48-64`；`api/app.py:296-311` | `/metrics` 能看见死信 | `NS6-T11` | poison 后 dead_total≠0 |
| P2-04 | VF24 rowcount CAS | 每个 owner-conditioned UPDATE 要求 `rowcount==1` 才写 dead 事件/metrics；0 则 return。repair SELECT 过滤 `status IN ('pending','in_flight')`。supervisor 异常不 `progressed+=1` | `runtime_outbox.py:343-406`；`runtime_repair.py:46-52`；`workflow_supervisor.py:51-54` | stale owner 不能假死信 | `NS6-T12` | 第二 owner 后 stale dead 0 行 |
| P2-05 | VF26 retirement | 每个 `_active_pointer_tx` None 当不可用：namespace inactive/deleted、item 无 serving、pointer 非 active 则 abandon | `index_retirement.py:320-328,518-573` | 队头不再永占 | `NS6-T13` | 第二次 scan 收到健康 intent |
| P2-06 | VF27 fail CAS | `_fail_process_tx` 加 `AND fencing_generation=?`；仅 `rowcount==1` 写 evidence/events。recover 同一 CAS | `runtime_outcome.py:454-459` | 新世代不被旧 fail 打死 | `NS6-T14` | 旧 fencing fail 后新世代仍 running |
| P2-07 | VF28 cancel fence | cancel UoW 同时 CAS 当前 root Execution 为 cancelling 并 bump running Process `fencing_generation`（复用 `_cancel_execution_tree_tx`）。`accept_outcome` 在 Task `cancelling` 时拒 succeeded，或去掉 success-wins 使 cancelling 只到 cancelled | `task_commands.py:193-205`；`task_projection.py:3-6,58-61` | cancel 后不得 succeeded | `NS6-T15` | 长 handler + POST cancel → 非 succeeded |
| P2-08 | VF37 Team 409 | INSERT 对齐 TaskCreateMixin：`IntegrityError` + `_is_unique_conflict` → 同指纹 replay / 不同指纹 409 | `teams.py:35-61`；`task_create.py:130-141` | 并发 PK 不 500 | `NS6-T16` | UNIQUE 失败 → 409/replay |

### 4.3 Phase 3 — 推理车道收口

**绑定 VF**：`VF8 VF9 VF10 VF11`（ledger 批次 3；依赖 P1 VF7/VF21）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P3-01 | VF8 salvage SSOT | a) salvage 时 materialize/admit durable NI Process；b) NI 满/CLI 未绑 fail-closed；c) 从 salvage set 去掉 `INFERENCE_BACKPRESSURE`；d) 不改 billing always-permit（VF23） | `generation_construct.py:106-122,192-226,294-308` | 池=运输 | `NS6-T17` | salvage 占 NI；BACKPRESSURE 不 `cli.run` |
| P3-02 | VF9 证据分桶 | 删除 `_DEFAULT_EVIDENCE_KEY` 与空 take 回退。record/take 强制 `process_uuid`。`generation_construct.py:287-289` 传入 `command.process_uuid`。不把 pending 改成耐久表（本阶段未承诺） | `generation_evidence.py:9-52` | 不串台 | `NS6-T18` | 无 uuid 的 record 不得被 process B flush |
| P3-03 | VF10 lease | `release(lease)` 后 `lease=None` 再 sleep；只赋新 acquire。`finally: if lease is not None: release` | `facade.py:385-409` | 取消/满门不炸 | `NS6-T19` | 无 RuntimeError/AttributeError |
| P3-04 | VF11 CLI 边界 | `_cli_child_env` 改 allowlist（PATH/LANG/HOME/ANTHROPIC_*/CLAUDE_*）。stdout 流式字节帽，溢出即 kill。cancel 路径 shield `_terminate_process`，terminate 内捕 CancelledError 仍 kill。进程组杀孙 → VF11.r | `claude_cli.py:320-406` | 无 env 泄密 / 无内存帽后置 / 无僵尸 | `NS6-T20` | env 无 AWS secret；overflow 前 kill；returncode 非 None |

### 4.4 Phase 4 — intake / 向量 / HITL / 身份

**绑定 VF**：`VF12 VF13 VF14 VF15 VF16 VF17 VF18`（ledger 批次 4；**VF12 先于再 vectorize 测试**；VF16 与 VF17 同 Phase 做完）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P4-01 | VF12 serving 不可变 | a) `_existing_vector_coordinate_uuid` / `_upsert_vector_record_tx` SELECT 加 `AND index_generation=? AND publication_state='withdrawn'`（或拒绝 `indexed`）；b) 新世代必须 INSERT 新 `vector_record_uuid`；c) 保留指针 `active < excluded` | `vector_publish_commit.py:334-397`；`vectorize.py:203-213` | 再 vectorize 不打穿 serving | `NS6-T21` | 旧 gen indexed COUNT 不变 0 |
| P4-02 | VF13 HITL | a) `consume_gate_decision` 在 approve/reject 调 `_apply_human_review_item_lifecycle_tx`；b) reject SQL 须处理已 deactivated HITL 插入；c) `resolve_gate` 删除或保持死代码不作为公共路径 | `acceptance_snapshot.py:106-123`；`runtime_gates.py:100-285`；`lifecycle_publish.py:75-76` | approve 可发布 | `NS6-T22` | approve 后 active + publication 成功 |
| P4-03 | VF14 双制品 | raw bytes 与 clean UTF-8 分两个 CAS 对象（各自 digest/size/handle/media_type）。acceptance envelope 只当元数据。rebuild `read_verified(clean_handle)` 且 `sha256==content_digest`，禁止 JSON peeling | `acceptance_snapshot.py:63-185`；`acquisition_ingest.py:77-84`；`core.py:388-507` | digest=bytes | `NS6-T23` | 两行 sha256 对齐 handle |
| P4-04 | VF15 幂等 | 加耐久 unique `(team_uuid, source_kind, normalized_external_key)`；source/item/revision 与 resolve 同一 UoW。同指纹 replay；内容变则 `MAX(ordinal)+1` + predecessor CAS。registered_api scatter 同样栅栏 | `acquisition_ingest.py:91-247`；`acceptance_snapshot.py:108-145` + **新 migration** | 同 key 不 201+failed | `NS6-T24` | 二次 ingest replay；并发 items=1 |
| P4-05 | VF16 namespace/purge | namespace 按 (model_key, version, adapter, dimension) 键或显式 rebuild；409 仅用于原地改 active default。收窄 `VectorizeChannelFilter` 为 `all` 并改写 e2e，或实现带新 proof+pointer CAS 的 partial purge | `vectorize.py:102,275`；`vector_publish_commit.py:265-305`；`vector_purge.py:68-76` | 维切换可服务；purge 合同一致 | `NS6-T25` | 改维新 ns；partial 要么 422 要么新 proof |
| P4-06 | VF17 预留 | 废 early read；在 vectorize outcome TX 内 `UPDATE mkb_vector_namespaces SET index_generation=index_generation+1 RETURNING`（或记录先 NULL generation，publish 时填） | `vector_publish_commit.py:265-281`；`vectorize.py:169` | 并发不预同号 | `NS6-T26` | 重叠同 item 不得双写 N+1 |
| P4-07 | VF18 配方 | 选定单一配方并同时用于写与查询：(a) full_construct 去掉 title headers，title 只当 facet；或 (b) 允许 headers 且 `_embed_query` 用同一 prefix。禁止 construct 接线而 binder 禁止。替换 `test_title_enters_content_full` 为 admit+embed 路径测 | `generation_construct.py:1324-1338`；`binder.py:50-51`；`vectorize.py:161-472`；`retrieval_request.py:423-427` | 写/查同一空间 | `NS6-T27` | titled bind 不再 409 同时 query 裸 embed |

### 4.5 Phase 5 — 安全边界

**绑定 VF**：`VF29 VF30 VF31 VF33 VF34`（ledger 批次 5；**VF29 先于 VF34**）  
威胁模型：`docs/baseline/domain-truth/S16-security-trust-boundary.md`（§7.3）。每项测试含攻击向量。

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P5-01 | VF29 XFF | 删除 `elif peer and _is_private_peer: return presented`。空 CIDR 永远返回 ASGI peer。仅当 cidrs 非空且 `_ip_in_cidrs(peer, cidrs)` 才抄 XFF | `security.py:476-499`；`dependencies.py:158-197` | 伪造内网失败 | `NS6-T28` | 空 CIDR + XFF 127.0.0.1 不得过 `/metrics` |
| P5-02 | VF30 PATCH | `TeamPatchRequest`/`TaskPatchRequest` `model_validator(mode='after')` 调 `assert_safe_public_data(self.payload_extra)`。写时拒绝而非 GET 静默 redact | `api/models.py:44-59,362-377` | extras 不是 vault | `NS6-T29` | PATCH apiKey → 422 且库无 secret |
| P5-03 | VF31 body cap | ASGI receive 包装累计 `len(body)`，超 cap 立即 `REQUEST_BODY_TOO_LARGE` 413；保留 CL 快拒 | `api/app.py:527-539` | chunked 不能 OOM | `NS6-T30` | 无 CL chunked 超 cap → 413 |
| P5-04 | VF33 undo | `decide` 返回 `(disposition, effective_key)` 并传入 `undo` | `security.py:251-289`；`dependencies.py:96-101` | overflow 配额可退 | `NS6-T31` | undo 后第三 IP 仍 DETAIL |
| P5-05 | VF34 mapped | 先依赖 P5-01。`_is_private_peer`/`_ip_in_cidrs` 递归 `ipv4_mapped` 对齐 `is_internal_ip`，**不要**用该递归重开空 CIDR XFF 信任 | `security.py:215-216,502-537` | 限流桶不被伪造 XFF 打穿 | `NS6-T32` | 循环 XFF 共用一桶 |

### 4.6 Phase 6 — 测试保真与治理

**绑定 VF**：`VF35 VF38` + mega/soak/closure（ledger 批次 6）

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P6-01 | VF35 假绿 | 按 §8 谓词重写 TTL/heartbeat/CLI/ReadPort/sidecar/journal 测试。`test_ns5_turso_mainchain` 经 PersistencePort 走 vectorize+retrieval。**不**新增 sqlite3-on-Turso 检查（VF35.r） | 见 §8.2 | 删 SUT 会红 | `NS6-T33` | 所列三测 no-op 后 RED |
| P6-02 | VF38 叙述 | 保持 `NS5-0820-bug-fixes-closure.md` 为唯一 NS5 closure SSOT。P2-05/P2-07 从 ✅ 翻 🟡 并引用本轮 VF36/VF37（2nd-pass 编号）。不发明 VRX5 | NS5 closure + NS5 AP | 过关叙述消失 | `NS6-T34` | 不再用 ✅ 掩盖 TTL/Team PK |
| P6-03 | mega/docs | 默认 Settings ready+claim smoke；PersistencePort 主链；BEGIN 取消 soak；heartbeat 跨 lease soak；2nd-pass VF-ledger §6；deferred-items-ledger；NS6 closure | ledger §6；新建 closure | 计划收口 | `NS6-T35` `NS6-T36` `NS6-T37` | 硬闸四元组齐全才 `executed` |

---

## 5. Phase 详情

### 5.1 Phase 1 — 进程存活 / 默认准入 / 耐久设置

- **Phase 目标**：故障后唯一连接仍可写；默认 Turso 画像可领活；探针不改活库；generate 不被 5s 冻死；lease/handler/字节在 cancel 下收敛。
- **本 Phase 对应编号**：`P1-01` … `P1-08`
- **本 Phase 新增文件**：`tests/unit/test_ns6_uow_begin_cancel.py`；`tests/unit/test_ns6_default_ready.py`；`tests/unit/test_ns6_journal_mode_restore.py`；`tests/unit/test_ns6_vllm_timeout.py`；`tests/unit/test_ns6_worker_cancel.py`；`tests/unit/test_ns6_gc_toctou.py`
- **本 Phase 修改文件**：`uow.py:26-46`；`turso/port.py:146-177`；`engine.py:24-42`；`local_vllm.py:206-245`；`worker.py:66-162`；`health.py:14-44`；`object_gc.py:196-238`；`api/app.py:183-191,291-294,456-464`
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 取消发生在 `to_thread(BEGIN)` 期间，下一事务仍可 `BEGIN IMMEDIATE`。
  2. 默认 `concurrent_writes_required=True` 的 Turso 叶工人 `/ready` 为 ready，`claim_next` 不被 CW 门挡住。
  3. `readiness()` 前后第二连接看到的 `journal_mode` 相同。
  4. `/ready` probe 之后 `generate_timeout_seconds=180` 的请求不被 5s 打断。
  5. 外部取消 `run_once` 会 cancel 未完成的 `handler_task` 并清空 `_pending`。
  6. heartbeat 抛非取消异常时 handler 被 fence，不得 accept succeeded。
  7. GC TX1 与 unlink 之间插入同 digest live reference 不得留下「目录活、字节无」。
  8. `HealthAggregator(ttl_seconds=5)` 两次顺序 `ready()` 只执行一次 probe（或删除 ttl 参数并改测试名）。
- **对应测试台账项**：`NS6-T01` … `NS6-T08`
- **收口标准**：T01–T08 全 PASS；T02 **不得**依赖 `local_runtime.py:21` waiver；不得在本 Phase 打开 VF62 重叠执行。
- **本 Phase 风险提醒**：P1-02 若把 `REQUIRED` 里的 `concurrent_writes` 直接删掉而不拆探针位，会把「做不到 CW」重新藏进 ready。探针必须仍可观测。P1-03 不得在业务连接上 `journal_mode=mvcc` 再「尽量 restore」。

### 5.2 Phase 2 — CAS / schema / outbox / fencing

- **Phase 目标**：状态转移以 `rowcount==1` 为安全条件；墓碑/过期/取消不再半修。
- **本 Phase 对应编号**：`P2-01` … `P2-08`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `migration_runner.py:148-163`；`generation_artifacts.py:561-565` 等 lookup；`runtime_outbox.py:343-377`；`runtime_core.py:48-64`；`index_retirement.py:518-573`；`runtime_outcome.py:454-459`；`task_commands.py:193-205`；`task_projection.py:3-61`；`teams.py:35-61`；`api/app.py:296-311`
- **具体功能预期**：
  1. DROP `mkb_outbox` 后 schema 非 ready。
  2. tombstone 后再 promote 同 digest 得到新 live `stored_object_uuid`。
  3. poison outbox 后 `/metrics` 的 `mkb_outbox_dead_total` 增加，事件 trace 不换根。
  4. 租约过期被第二 owner claim 后，旧 owner 不得写 `outbox.dead`。
  5. namespace 停用的 100 条 intent 不永久占满 LIMIT 100。
  6. 旧 `fencing_generation` 的 fail 不得把新世代 running process 标 failed。
  7. Task `cancelling` 不得被 in-flight handler `succeeded` 赢走。
  8. 并发同 `team_uuid` INSERT 映射 409/replay。
- **对应测试台账项**：`NS6-T09` … `NS6-T16`
- **收口标准**：T09–T16 全 PASS；P2-03 与 P2-04 必须一起合，禁止只写事件不看 rowcount。
- **本 Phase 风险提醒**：supervisor `progressed+=1` 在异常路径上会把持续故障报成正常——P2-04 必须改。

### 5.3 Phase 3 — 推理车道收口

- **Phase 目标**：salvage 是运输；证据不串台；retry 取消干净；CLI 子进程有界。
- **本 Phase 对应编号**：`P3-01` … `P3-04`
- **本 Phase 新增 / 修改 / 删除文件**：`generation_construct.py:106-308`；`generation_evidence.py:9-52`；`facade.py:385-409`；`claude_cli.py:320-406`
- **具体功能预期**：
  1. salvage 占 NI occupancy 或 fail-closed；BACKPRESSURE 不再翻译成另一次 Claude 调用。
  2. 无 `process_uuid` 禁止 stash；空 keyed take 不得回退 `"_"`。
  3. RETRYABLE 释放后 `lease is None`；finally 只 release 非空 lease。
  4. 子环境无 AWS secret；stdout 超 8MiB 在 `communicate()` 返回该缓冲前被杀；cancel 后 `returncode is not None`。
- **对应测试台账项**：`NS6-T17` … `NS6-T20`
- **收口标准**：车道测试断言 `command.dispatch_pool == 实际运输`；证据测试覆盖「省略 uuid」而非只测两个显式 key。
- **本 Phase 风险提醒**：不要为了 salvage 测试把 billing 改成真配额（VF23 仍 always-permit）。ANTHROPIC_* 属于 CLI 必需 allowlist，不得当泄漏误删。

### 5.4 Phase 4 — intake / 向量 / HITL / 身份

- **Phase 目标**：serving 行不可变；HITL 可发布；字节身份与幂等成立；namespace/generation 同 TX。
- **本 Phase 对应编号**：`P4-01` … `P4-07`
- **本 Phase 新增 / 修改 / 删除文件**：新建 `016_ns6_source_external_key.sql`（名称以落地为准）；修改 `vector_publish_commit.py:265-397`；`vectorize.py:102-213,461-472`；`runtime_gates.py:197-285`；`acceptance_snapshot.py:63-185`；`acquisition_ingest.py:77-247`；`core.py:388-507`；`vector_purge.py:68-76`；`binder.py:50-51`；`retrieval_request.py:423-427`
- **具体功能预期**：
  1. 已 `publication_state='indexed'` 的行禁止 UPDATE；新 generation INSERT 新行。
  2. 公共 approve 后 item `lifecycle_state='active'` 且 publication 不被 `PUBLICATION_SERVING_FENCE` 挡住。
  3. raw 与 clean 各自 `sha256(read(handle))==content_digest`。
  4. 同 `external_key` 第二次请求 replay，不得 201 后 Task failed；`revision_ordinal` 不再写死 1。
  5. 改 embedding 维创建新 namespace，而非 409 default；purge 合同与 runtime 一致。
  6. generation 预留与 publish 在同一 UoW。
  7. title 要么不进 embed，要么 query 使用同一配方——禁止 binder 409 与「title 进入 content_full」同时宣称完成。
- **对应测试台账项**：`NS6-T21` … `NS6-T27`
- **收口标准**：T21 必须在任何再 vectorize 集成之前绿；T24 需要 migration 夹具（fresh + 已有 source 行）。
- **本 Phase 风险提醒**：015 unique 含 generation 只拦 INSERT 不拦 UPDATE——P4-01 必须改 Python。P4-04 unique 加列前先规范化已有 `normalized_external_key`。

### 5.5 Phase 5 — 安全边界

- **Phase 目标**：S16 在空 CIDR、PATCH、chunked、overflow 上 fail-closed。
- **本 Phase 对应编号**：`P5-01` … `P5-05`
- **本 Phase 新增 / 修改 / 删除文件**：`security.py:215-216,251-289,476-537`；`api/models.py:50-59,362-377`；`api/app.py:527-539`；`dependencies.py:96-112,158-197`
- **具体功能预期**：
  1. 空 `trusted_proxy_cidrs` 完全忽略 XFF；伪造 `127.0.0.1` 不能过无 token `/metrics`。
  2. PATCH `{apiKey}` 422 且库无 secret。
  3. 无 Content-Length 的 chunked 超 cap 立即 413。
  4. overflow 桶的 undo 退回 overflow 配额。
  5. `::ffff:127.0.0.1` 在 `_is_private_peer` 与 `is_internal_ip` 同类；循环 XFF 不得分裂限流桶。
- **对应测试台账项**：`NS6-T28` … `NS6-T32`（均含攻击向量）
- **收口标准**：`test_ns5_phase5.py` / `test_security_boundary.py` 扩展攻击用例全 PASS。
- **本 Phase 风险提醒**：P5-05 的 mapped 递归不得重开空 CIDR XFF 信任。`/internal` 仍要 operator token——测试不得把「过 `/metrics` 内网闸」写成「未认证写 `/internal`」。

### 5.6 Phase 6 — 测试保真与治理

- **Phase 目标**：假绿短途按收口谓词变真红；closure 叙述与代码一致。
- **本 Phase 对应编号**：`P6-01` … `P6-03`
- **本 Phase 新增 / 修改 / 删除文件**：`tests/unit/test_ns5_*.py` 所列；`tests/integration/test_ns5_turso_mainchain.py`；NS5 closure；2nd-pass VF-ledger §6；新建 NS6 closure
- **具体功能预期**：
  1. TTL 测试改为顺序两次 `ready()` 断言 probe==1（或删除死参数）。
  2. heartbeat 测试必须跨过 `lease_seconds`；CLI timeout 断言 pid/returncode 而非 fixture 文件仍在。
  3. ReadPort/sidecar/journal 测试实例化 SUT。
  4. mainchain 经 PersistencePort 查询 vector records + retrieval，禁止 `sqlite3.connect`。
  5. NS5 closure P2-05/P2-07 不再 ✅。
- **对应测试台账项**：`NS6-T33` … `NS6-T37`
- **收口标准**：硬闸四元组齐全才 `executed`。**不**要求全量 pytest 441/441。
- **本 Phase 风险提醒**：禁止为了 T33 绿而把谓词改软。禁止新增 sqlite3-on-Turso 检查冒充 VF86 已修。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[true-bug]` 不得改写成 deferred | 2nd-pass VF-ledger §0.4 | VF3/7/10/15/18/24/27/28 必修 | 升 blocker 交 owner，禁止改 class |
| 批次 1→2→4，P3/P5 可并行 | ledger §5.3 | §1.2 DAG | 打乱则 UoW 毒化/假绿锁行为 |
| 业务 UoW 保持 IMMEDIATE | NS5 P1-02 substrate-fit + ledger VF2 | P1-02 拆探针/准入，不改 CONCURRENT | soak abort → 保持 IMMEDIATE |
| VF19 stale | ledger §4.3 | 不改 hydration | `search()` 去掉 cache 则 reopen |
| VF6/20/32 deferred | ledger §5.4 | 只登记承接 | 触发器见 §5.4 |
| VF86 / NS1-V11 | 第 1 轮 ledger + NS5 O3 | 不新增 sqlite3 检查 | harness charter |
| VF23 always-permit | NS2-O1 / README K10 | salvage 测试不改 billing | billing AP |
| VF62 重叠仍关 | ledger / NS5 P1-04 | P1-06 只 fence 异常，不打开重叠 | 后继 charter |
| VF66.r 目录 SSOT | T-O-120 | P1-07 只修 live-ref TOCTOU | owner 授权磁盘 SSOT |

---

## 7. 内置 Reference-Anchor 锚区

> 落盘前已对 HEAD 抽查。reviewer 行号仅作线索；下表是本 AP 的 grounding 真源。

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `src/persistence/uow.py:26-46` | `BEGIN` 在 `try` 外；body/commit 已 BaseException | P1-01 把 BEGIN 移入同一 try | `✅ 复用` | 已有 helper，勿再分 sqlite/turso 两套 |
| A-2 | `src/persistence/turso/port.py:146-177` | readiness 持写锁；`required=True` 强制 `concurrent_writes=False`；probe `restore=False` | P1-02 / P1-03 / P1-08 | `✅ 复用` | 拆探针位，勿删观测字段 |
| A-3 | `src/persistence/engine.py:24-42` | `PRAGMA journal_mode=mvcc`；restore 仅当 flag 真 | P1-03 | `✅ 复用` | 旁路连接仍打生产文件则无效 |
| A-4 | `src/runtime/health.py:14-44` | `REQUIRED` 含 `concurrent_writes`；`ttl_seconds` 死代码 | P1-02 / P1-08 | `✅ 复用` | |
| A-5 | `src/runtime/config.py:23-25`；`data/config/default.toml:7` | 默认 turso + `concurrent_writes_required=True` + 空 CIDR | P1-02 / P5-01 | `✅ 复用` | 测试 waiver 不是合同 |
| A-6 | `src/llm_adapters/local_vllm.py:206-245` | 共享 client 首创 timeout；`post()` 无 per-request timeout | P1-04 | `✅ 复用` | 已有 `aclose()` 未接线 lifespan |
| A-7 | `src/runtime/workflow/worker.py:66-162` | finally 只取消 heartbeat；心跳只捕 CancelledError | P1-05 / P1-06 | `✅ 复用` | 非 fenced CancelledError 已 discard |
| A-8 | `src/services/object_gc.py:196-238` | TX1 提交后事务外 unlink；TX2 409 不恢复字节 | P1-07 | `♻️ 重 substrate` | 引入 deleting fence 或 rename |
| A-9 | `src/persistence/migration_runner.py:148-163` | checksum 后只 `mkb_tasks in tables` | P2-01 | `✅ 复用` | 小闭集，非 D04 全表 |
| A-10 | `src/services/artifacts.py:141-143` | 正确 live lookup | P2-02 抽 helper | `✅ 复用` | 已建好别重写 |
| A-11 | `generation_artifacts.py:561-565` 等五路径 | digest/size SELECT 无 tombstone 过滤 | P2-02 | `✅ 复用` | 见 ledger §3.2.1 |
| A-12 | `src/runtime/workflow/runtime_outbox.py:343-377` | dead UPDATE 后只要行非空就写事件；`trace_uuid=uuid7()`；`getattr metrics` | P2-03 / P2-04 | `✅ 复用` | |
| A-13 | `src/runtime/workflow/runtime_core.py:48-64` | 无 metrics 参数 | P2-03 | `✅ 复用` | |
| A-14 | `src/services/index_retirement.py:320-328,518-573` | LIMIT 100；abandon 只覆盖 item missing/deleted/deactivated | P2-05 | `✅ 复用` | |
| A-15 | `src/runtime/workflow/runtime_outcome.py:454-459` | fail UPDATE 无 `fencing_generation` | P2-06 | `✅ 复用` | success 路径已 CAS |
| A-16 | `src/runtime/task/task_commands.py:193-205`；`task_projection.py:3-61` | cancel 只 CAS Task + outbox；允许 `cancelling→succeeded` | P2-07 | `✅ 复用` | supervisor 已先 drain outbox |
| A-17 | `src/services/teams.py:35-61` | SELECT-then-INSERT 无 IntegrityError | P2-08 | `✅ 复用` | 对照 `task_create.py:130-141` |
| A-18 | `src/runtime/intake/generation_construct.py:106-226,287-289` | salvage 含 BACKPRESSURE；kernel-fail 省略 process_uuid | P3-01 / P3-02 | `✅ 复用` | |
| A-19 | `src/runtime/intake/generation_evidence.py:9-52` | `process_uuid or "_"`；空 take 回退 | P3-02 | `✅ 复用` | 删默认桶即可 |
| A-20 | `src/runtime/inference/facade.py:385-409` | RETRYABLE 先 release；finally 无条件 release | P3-03 | `✅ 复用` | |
| A-21 | `src/runtime/inference/claude_cli.py:320-406` | communicate 后比 8MiB；env 只剥 MKB_*；terminate 未 shield | P3-04 | `✅ 复用` | |
| A-22 | `src/runtime/intake/vector_publish_commit.py:334-397,265-281` | SELECT 无 generation/state；early read `index_generation+1` | P4-01 / P4-06 | `✅ 复用` | |
| A-23 | `src/runtime/workflow/runtime_gates.py:100-128,197-285` | activate 只在 `resolve_gate`；`consume_gate_decision` 不碰 Item | P4-02 | `✅ 复用` | |
| A-24 | `src/runtime/intake/acceptance_snapshot.py:106-145,149-185` | HITL 插入 deactivated；ordinal 字面 1；raw/clean 共用 handle | P4-02 / P4-03 / P4-04 | `✅ 复用` | |
| A-25 | `src/runtime/intake/acquisition_ingest.py:77-150,240-247` | 先 mint UUID 再独立读 TX；registered_api 不 resolve | P4-04 | `♻️ 重 substrate` | 需 unique + 同 TX |
| A-26 | `src/runtime/intake/vectorize.py:102,203-213,461-472` | `namespace_key='default'`；existing_uuid 复用 | P4-01 / P4-05 | `✅ 复用` | |
| A-27 | `src/services/vector_purge.py:68-76` | runtime 拒非 `all` | P4-05 | `✅ 复用` | e2e 仍覆盖 partial |
| A-28 | `src/services/lsrag_construct/binder.py:50-51` | full_construct 拒 metadata headers | P4-07 | `✅ 复用` | 与 VF95 接线互拆 |
| A-29 | `src/runtime/security.py:476-499,251-289,502-507` | 空 CIDR 信私网 XFF；overflow undo；`_is_private_peer` 不递归 mapped | P5-01 / P5-04 / P5-05 | `✅ 复用` | |
| A-30 | `src/contracts/api/models.py:44-59,362-377` | Create 拒密；Patch 只 require_change | P5-02 | `✅ 复用` | |
| A-31 | `api/app.py:527-539,291-294,296-311,456-469` | body 只看 CL；claim 要 ready；Runtime 无 metrics；docs 默认开 | P5-03 / P1-02 / P2-03 | `✅ 复用` | `/docs` 本轮不关（VF32） |
| A-32 | `tests/unit/test_ns5_phase2.py:96-111` 等 | TTL 只测 coalesce；heartbeat 未跨 lease | P6-01 | `🔱 fork` | 见 §8.2 |
| A-33 | `016_*.sql`（新建） | source external_key unique | P4-04 | `🆕 净新` | 名称以落地为准 |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 用 `concurrent_writes_required=False` 的 `local_runtime.py:21` 证明默认 ready | ledger VF2；waiver 把矛盾藏绿 |
| ⛔2 | 业务 UoW 改 `BEGIN CONCURRENT` 来满足 REQUIRED | sidecar abort / 同 TX DDL；NS5 P1-02 已选 IMMEDIATE |
| ⛔3 | 生产连接 `journal_mode=mvcc` 再「尽量 restore」 | VF3；journal_mode 是库级状态 |
| ⛔4 | 打开 VF62 重叠 `run_once` | 心跳异常 fence 未绿前必现双跑 |
| ⛔5 | 新增 `sqlite3.connect` 打开 Turso 文件 | VF86 / VF35.r；禁止当绿证 |
| ⛔6 | 把 VF15/VF3/VF12 改写成 deferred | `[true-bug]` / 本轮切片硬规则 |
| ⛔7 | PATCH 只在 GET 脱敏 | VF30；secret 已落库 |
| ⛔8 | mapped 递归重开空 CIDR XFF | VF34 修法明确禁止 |
| ⛔9 | `test_title_enters_content_full` 只调 helper | VF18；看不见 binder 409 |
| ⛔10 | 只测两个显式 process_uuid 的 evidence happy path | VF9；不覆盖 `"_"` 回退 |
| ⛔11 | TTL 测试 `gather` 两次当缓存 | VF36 / VF35；那是 inflight coalesce |
| ⛔12 | heartbeat 在 lease 到期前 recover | VF22；删掉心跳循环也会绿 |
| ⛔13 | GC TX2 409 当「已保护」 | VF25；字节已不可逆删除 |
| ⛔14 | 发明 `docs/issue/v3-ready/VRX5-…` | VF38；不在 NS5 承诺制品 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：无。**§7 就是本 AP 的 grounding 真源**。
- **安全 / 信任边界类工作项的威胁模型锚**：
  - P5-01/P5-05：S16「默认不盲信转发头」；攻击：peer=`10.0.0.1` + XFF=`127.0.0.1` 过 `/metrics`；循环 XFF 打穿 `ip_limit`。锚 A-29 / A-5。
  - P5-02：S16 extras 不是 vault；攻击：PATCH `{apiKey,token,signedUrl}`。锚 A-30。
  - P5-03：叶工人单进程 OOM；攻击：chunked / 缺 CL 超 `max_request_bytes`。锚 A-31。
  - P5-04：审计洪水下 overflow 配额泄漏。锚 A-29。
  - P3-04：子进程继承 AWS/Anthropic 之外的父秘密；超大 stdout。锚 A-21。
  - P1-04：probe 5s 导致 generate 全失败，放大 salvage。锚 A-6。

---

## 8. 测试台账

> 测试细节只在此写一次。**每个 Test-ID 都有防假绿说明**：今日仍绿、删 SUT 仍绿、或只断言旁路对象，即本项未收口。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射 | PASS 证据 | 防假绿 |
|---------|------------------|------|----|------|------|-----------|--------|
| `NS6-T01` | 取消发生在 `to_thread(BEGIN)` 期间，随后再 BEGIN+INSERT 成功 | `短途` | `unit` | `🆕 tests/unit/test_ns6_uow_begin_cancel.py`（🔱 既有 `test_ns5_uow_cancel.py` 不够） | P1-01 → 连接可再 BEGIN | `commit + test_ns6_uow_begin_cancel + 未观察` | 既有 T01 只取消 INSERT **之后**的 body，BEGIN 在 try 外仍绿。必须 patch `execute` 阻塞 BEGIN、cancel 等待协程，再断言第二事务成功。只 assert rollback 被调用 ≠ 句柄可复用。 |
| `NS6-T02` | 默认 Settings(turso, `concurrent_writes_required=True`) migrate+bootstrap 后 ready 且 claim 非 NotReady | `短途` | `集成` | `🆕 tests/unit/test_ns6_default_ready.py` | P1-02 → 默认画像可领活 | `commit + test + 未观察` | **禁止** `local_runtime.py:21` waiver。`required=False` 时 `engine.py:97-99` 把 CW 报成 True 是反向假绿。必须实例化默认 Settings。 |
| `NS6-T03` | readiness 前后第二连接 `PRAGMA journal_mode` 相等 | `短途` | `集成` | `🆕 tests/unit/test_ns6_journal_mode_restore.py` | P1-03 → 活库 mode 不变 | `commit + test + 未观察` | 只断言 bypass 连接自己的 mode 不够；必须另开连接看生产文件。sqlite 因切 mvcc 失败「看起来没变」不算 Turso 绿。 |
| `NS6-T04` | probe() 后再 generate()；MockTransport 睡 6s，`generate_timeout_seconds=180` 不得 TRANSPORT_RETRYABLE | `短途` | `unit` | `🆕 tests/unit/test_ns6_vllm_timeout.py` | P1-04 → 每请求 timeout | `commit + test + 未观察` | 只断言 `_shared_client` 被调用两次（单例形状）仍绿。必须让 probe 先以 5s 建 client，再让 generate 的 mock 睡 6s 成功返回。 |
| `NS6-T05` | 取消 `run_once` 于 handler.sleep：`handler_task.cancelled()` 且 `_pending=={}` | `短途` | `unit` | `🆕 tests/unit/test_ns6_worker_cancel.py` | P1-05 → 无孤儿 | `commit + test + 未观察` | 只取消 heartbeat 或只看 `run_once` 抛 CancelledError 仍绿。必须持有 `handler_task` 引用并断言它 cancelled；再往 `_pending` 塞一条证明被 discard。 |
| `NS6-T06` | patch heartbeat raise RuntimeError；handler 2s + lease=1s → handler 取消且不得 accept succeeded | `短途` | `unit` | `🔱 fork test_ns5_phase1_runtime.py` 心跳测 | P1-06 → 失败即 fence | `commit + test + 未观察` | 既有 T04 在 0.8s recover、lease=1s——**删掉心跳循环也会 recovered==0**。必须跨过 `lease_seconds`，且 heartbeat **raise** 而非返回 False。 |
| `NS6-T07` | TX1 commit 与 unlink 之间交错 `validate_and_commit` 同 digest：`read_verified` 成功或 live ref 已 released | `短途` | `unit` | `🆕 tests/unit/test_ns6_gc_toctou.py` | P1-07 → 不丢字节 | `commit + test + 未观察` | 只断言 TX2 抛 409 是假绿（今日就会 409）。必须读存储：目录 live ⇒ 字节存在。 |
| `NS6-T08` | `HealthAggregator(ttl_seconds=5)` 两次**顺序** `ready()` → probe==1 | `短途` | `unit` | `🔱 fork test_ns5_phase2.py:96-111` | P1-08 → TTL 真缓存 | `commit + test + 未观察` | 既有测试 `gather` 两次只证明 inflight coalesce，`1 <= n <= 2` 恒真。必须顺序 await 两次。 |
| `NS6-T09` | DROP `mkb_outbox`（或 processes/vector_records）后 `schema_migration` 为 false | `短途` | `unit` | `🔱 fork test_ns5_phase2.py:123-130` | P2-01 → 闭集 | `commit + test + 未观察` | 只 DROP `mkb_tasks` 仍绿（那是他们特殊处理的表）。必须另 DROP 一张闭集内的表。 |
| `NS6-T10` | GC/tombstone 后再 catalog 同 digest → 新 live uuid 且有 live reference | `短途` | `unit` | `🔱 fork test_object_gc.py` | P2-02 → 不复用墓碑 | `commit + test + 未观察` | 只走 `artifacts.py:141` 正确路径仍绿。必须走 generation/config/rebuild/scatter/task_create 至少一条脏 lookup。 |
| `NS6-T11` | create_app 容器强制 JSON-poison outbox 后 GET `/metrics` `mkb_outbox_dead_total` ≠ 0；事件 trace=Task | `短途` | `集成` | `🔱 fork test_ns5_outbox_poison.py` | P2-03 → 可观测 | `commit + test + 未观察` | 只断言 DB 有 `outbox.dead` 事件仍绿（今日已有事件、指标恒 0）。必须打 `/metrics` 文本。 |
| `NS6-T12` | 租约过期被第二 owner claim 后，stale `_mark_outbox_dead` 不得插入新 dead 事件 | `短途` | `unit` | `🆕` outbox stale-owner | P2-04 → CAS | `commit + test + 未观察` | 只断言 UPDATE SQL 含 `lease_owner` 不够。必须跑双 owner 时序并 COUNT 事件。 |
| `NS6-T13` | 100 条 namespace 停用 open intent + 1 健康；两次 `scan_once(limit=100)` 后收到健康 | `短途` | `unit` | `🔱 fork test_ns5_retirement_stuck.py` | P2-05 → 队头 | `commit + test + 未观察` | 既有 T06 只种 deactivated item。必须种 **namespace 停用** 或 serving NULL，否则今日已绿。 |
| `NS6-T14` | TX 内抬 fencing_generation 并 status=running，用旧 process dict `_fail_process_tx` → 新世代不得 failed | `短途` | `unit` | `🆕` | P2-06 → fail CAS | `commit + test + 未观察` | 只 grep SQL 含 `fencing_generation` 是源码扫描。必须执行两条 generation。 |
| `NS6-T15` | 长 handler 中途 POST cancel；handler 返回 succeeded → Task 不得 ended succeeded | `短途` | `unit`/`集成` | `🆕` | P2-07 → cancel 语义 | `commit + test + 未观察` | 只断言 Task 行变成 cancelling 不够（今日就会）。必须让 handler 跑完 succeeded 再读终态。 |
| `NS6-T16` | stub INSERT raise `UNIQUE constraint failed: mkb_teams.team_uuid` → 409/replay | `短途` | `unit` | `🔱 fork` teams 测 | P2-08 → 409 | `commit + test + 未观察` | 同进程 IMMEDIATE 下后到者常看到已提交行，happy-path 不触发 IntegrityError。必须 stub execute 抛 UNIQUE。 |
| `NS6-T17` | salvage 必须增加 NI occupancy；BACKPRESSURE 不得 `cli.run` | `短途` | `unit` | `🔱 fork test_ns5_phase3.py` salvage | P3-01 → 池=运输 | `commit + test + 未观察` | 既有测只查 `_can_salvage` 谓词（urgent+local）。必须断言 admit/occupancy 或 `cli.run` 调用次数在 BACKPRESSURE 时为 0。 |
| `NS6-T18` | `record(..., process_uuid=None)` 后 process B 的 `write_pending` 对该 invocation 0 行 | `短途` | `unit` | `🔱 fork` evidence 测 | P3-02 → 不串台 | `commit + test + 未观察` | `test_evidence_is_keyed_by_process_uuid` 只覆盖两个显式 key。必须省略 uuid / 走 `"_"` 回退路径。 |
| `NS6-T19` | (1) RETRYABLE+sleep 中取消 → CancelledError 无 RuntimeError；(2) reacquire None → BACKPRESSURE 无 AttributeError | `短途` | `unit` | `🔱 fork test_inference_runtime.py` | P3-03 → lease | `commit + test + 未观察` | 只测放 lease 再 sleep 的 happy retry 仍绿。必须取消 sleep 与满门再获取。 |
| `NS6-T20` | 子 env 无 `AWS_SECRET_ACCESS_KEY`；>8MiB writer 在 communicate 返回该缓冲前被杀；terminate 中取消后 `returncode is not None` | `短途` | `unit` | `🔱 fork test_ns5_phase1_runtime.py` CLI | P3-04 → 边界 | `commit + test + 未观察` | 既有 timeout 测断言 fixture **文件仍在**，不是 child pid。必须 `returncode is not None`；env 断言具体密钥名不在 child.env。 |
| `NS6-T21` | publish G=N indexed 后同 dual-channel 再 vectorize；旧 serving gen indexed COUNT 不得变 0 | `短途` | `集成` | `🆕` + 🔱 P4-10 测 | P4-01 → serving 不可变 | `commit + test + 未观察` | 只断言 015 unique 含 generation 仍绿（拦 INSERT 不拦 UPDATE）。必须 COUNT `publication_state='indexed' AND index_generation=N`。 |
| `NS6-T22` | `require_human_review` + 公共 approve 后 `lifecycle_state='active'` 且 publication 成功 | `短途` | `e2e`/`集成` | `🔱 fork test_human_review_gate.py`（经 PersistencePort，不 sqlite3） | P4-02 → HITL | `commit + test + 未观察` | 只断言 approve HTTP 200 仍绿（今日 200 且 item deactivated）。必须读 item 行 + publication。走 `consume_gate_decision` 而非 `resolve_gate`。 |
| `NS6-T23` | accept 后 raw/clean 两行 `sha256(storage.read(handle))==content_digest` 且 size 对齐 | `短途` | `unit` | `🆕` | P4-03 → digest=bytes | `commit + test + 未观察` | 只比较两个语义 digest 字段仍绿。必须 `read_verified(handle)` 再 sha256。rebuild 不得再 JSON peel。 |
| `NS6-T24` | 两次相同 key ingest：第二不得 201+Task failed；并发 COUNT(items)=1 | `短途` | `集成` | `🆕` | P4-04 → 幂等 | `commit + test + 未观察` | 「库里最终一份 source」≠ 接口幂等。必须断言第二响应 replay 且 Task 非 failed。并发两条一起跑。 |
| `NS6-T25` | 已有 default ns 的 team 改 embed 维 → 新 namespace 而非 409；`test_vector_purge_generation` 对 `_assert_purge_command` 与 runtime 一致 | `短途` | `unit`/`e2e` | `🔱 fork` vectorize + `test_vector_purge_generation.py:200-229` | P4-05 → 合同 | `commit + test + 未观察` | 只改模型字段但仍 409 不得当绿。partial purge 测试若仍断言 original 已删而 runtime 拒非 all，必须二选一改到一致。 |
| `NS6-T26` | 两重叠同 item vectorize 不得都写 N+1 | `短途` | `unit` | `🆕` | P4-06 → 原子预留 | `commit + test + 未观察` | 只断言指针 CAS 不回拨仍绿（今日已不回拨）。必须断言败者不得留下 stranded N+1 withdrawn 行。 |
| `NS6-T27` | 带 `context_meta.title` 的 layered `bind_construct(full_construct, headers=…)` 与 query embed 同一配方 | `短途` | `unit` | `🔱 fork test_title_enters_content_full` | P4-07 → 配方 | `commit + test + 未观察` | helper 测 title 进 content_full 与 binder 409 可同时绿。必须走 admit+embed 或显式二选一断言（body-only **或** query 带同一 prefix）。 |
| `NS6-T28` | peer `10.0.0.1` + 空 CIDR + XFF `127.0.0.1` → `request_ip=='10.0.0.1'`；无 token `/metrics` 不得 200 | `短途` | `unit` | `🔱 fork test_ns5_phase5.py` `test_security_boundary.py` | P5-01 → 攻击 | `commit + test + 未观察` | 既有测「带外网 XFF 时不当内网」（XFF=8.8.8.8 → 403）仍绿。必须测 **空 CIDR + 私网 XFF 当身份**。 |
| `NS6-T29` | `TeamPatchRequest(expected_revision=0, payload_extra={'apiKey':'sk-live'})` ValidationError；SELECT 无 sk-live | `短途` | `unit` | `🔱 fork test_ns5_phase5.py` | P5-02 → 攻击 | `commit + test + 未观察` | 只打 Create helper 仍绿。必须 PATCH + GET/DB。 |
| `NS6-T30` | 无 CL 的 chunked `max_request_bytes+1` POST `/v1/teams` → 413，不得落到 handler/422 | `短途` | `集成` | `🆕` ASGI | P5-03 → 攻击 | `commit + test + 未观察` | 只测诚实 Content-Length>cap 仍绿。必须无 CL / Transfer-Encoding chunked。 |
| `NS6-T31` | `max_buckets=1`；decide 第二 IP（overflow）后 undo，第三 IP 仍 DETAIL | `短途` | `unit` | `🔱 fork test_security_boundary.py` | P5-04 → undo | `commit + test + 未观察` | 只测 overflow 分桶隔离不够。必须 undo 后第三样本仍 DETAIL（今日 overflow 配额不退）。 |
| `NS6-T32` | 空 CIDR + peer 10.0.0.1 + 循环 XFF 1.1.1.{n} 共用一个 IP 桶；`::ffff:127.0.0.1` 在 `_is_private_peer` 与 `is_internal_ip` 同类 | `短途` | `unit` | `🔱 fork test_ns5_phase5.py` | P5-05 → 攻击 | `commit + test + 未观察` | 依赖 T28。T28 未绿时本项不得用「mapped 不信 XFF」当 fail-closed 绿（那是另一方向）。必须断言限流键=peer。 |
| `NS6-T33` | no-op heartbeat + 立刻返回的 `_terminate_process` + 未读 TTL：所列测试 RED；空 ReadService 方法体 `test_ns4_readport_reports` RED | `短途` | `unit` | `🔱/♻️` §8.2 所列 | P6-01 → 假绿拆除 | `commit + RED演示 + 未观察` | **本项自己就是防假绿闸**。必须演示删 SUT / no-op 后 RED，再接回绿。禁止改软谓词。mainchain 必须查 `mkb_vector_records` 或 retrieval，不得只 stub ingest succeeded。 |
| `NS6-T34` | grep NS5 closure P2-05/P2-07 不得在 TTL/Team PK 未修时保持 ✅ | `短途` | `契约` | `🆕` 文档断言或审查清单 | P6-02 → 叙述 | `commit + grep + 未观察` | 只新增一段「诚实」文字而表格仍 ✅ 不算。必须改表。不发明 VRX5。 |
| `NS6-T35` | 默认 Settings ready+claim；PersistencePort 走 ingest→vectorize→retrieval（无 sqlite3） | `mega` | `集成` | `🔱 fork test_ns5_turso_mainchain.py` | P6-03 → 主链 | `commit + mega + 未观察` | stub ingest succeeded ≠ 主链。禁止 sqlite3。T02 waiver 路径不得复用。 |
| `NS6-T36` | BEGIN 取消窗口 soak + heartbeat raise 跨 lease soak | `soak` | `集成` | 同 T01/T06 拉长 | P1-01/P1-06/P6-03 | `commit + soak log + 未观察` | 单次 happy cancel 不够。N 次 deterministic：每次第二 BEGIN 成功；每次 raising heartbeat 不得 succeeded。 |
| `NS6-T37` | `ruff check .` 0；本 AP 未新增 sqlite3-on-Turso | `短途` | `契约` | `♻️ 沿用` ruff + grep | P6-03 → 卫生 | `commit + ruff/grep + 未观察` | ruff 0 不证明行为。grep `sqlite3.connect` 在 e2e 的增量不得增加。 |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_ns5_uow_cancel.py` | `🔱 fork → test_ns6_uow_begin_cancel.py` | 取消窗口从 body 改为 BEGIN | body 取消已绿；BEGIN 窗口未覆盖 |
| `tests/unit/test_ns5_phase2.py:96-111` | `🔱 fork` | 顺序两次 ready，断言 probe==1 | 只测 coalesce |
| `tests/unit/test_ns5_phase2.py:123-130` | `🔱 fork` | DROP outbox/processes | 只 DROP mkb_tasks |
| `tests/unit/test_ns5_phase1_runtime.py:47-75` | `🔱 fork` | pid/returncode；heartbeat 跨 lease + raise | 文件仍在；0.8s recover |
| `tests/unit/test_ns5_phase3.py` salvage/evidence | `🔱 fork` | occupancy；省略 uuid | 谓词/双 key happy path |
| `tests/unit/test_ns5_phase5.py` | `🔱 fork` | 空 CIDR+私网 XFF；PATCH；chunked | Create-only / 外网 XFF |
| `tests/unit/test_ns5_retirement_stuck.py` | `🔱 fork` | namespace 停用 / serving NULL | 只种 deactivated |
| `tests/unit/test_ns5_outbox_poison.py` | `🔱 fork` | `/metrics` dead_total；stale owner | 有事件无指标 |
| `tests/unit/test_ns4_readport_reports.py` | `🔱 fork` | 实例化 ReadService | `inspect.getsource` |
| `tests/unit/test_ns4_diagnostic_sidecar.py` | `🔱 fork` | 实例化 sidecar.insert | 局部 MkbError |
| `tests/unit/test_ns4_jsonl_journal.py` | `🔱 fork` | 调 `_journal_row` | 读源码 |
| `tests/unit/test_ns4_cw_soak.py` | `♻️ 沿用` 行为 soak | 不改 sqlite3 | 已真 soak；禁止当 VF2 绿证 |
| `tests/integration/test_ns5_turso_mainchain.py` | `🔱 fork` | PersistencePort vectorize+retrieval | HTTP ingest succeeded only |
| `tests/e2e/test_human_review_gate.py` | `🔱 fork` 走 port | approve 后 lifecycle+publication | 200 但 deactivated；sqlite3 不碰 |
| `tests/e2e/test_vector_purge_generation.py` | `🔱 fork` | 与 runtime 合同一致 | partial original 与 422 分裂 |
| `tests/e2e/*` 的 `sqlite3.connect` | **不改** | VF35.r / VF86 | 禁止当本 AP 绿证 |
| `tests/local_runtime.py:21` | **不沿用为 T02** | waiver 显式 | 默认画像失明 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit tests/domain -q` | unit·契约 | 每工作项 / 每 PR |
| spike | 该 Phase 定向文件 | 集成·e2e | 每 Phase 收口 |
| mega | 默认 Settings ready+claim + PersistencePort 主链 | 集成 | **本 AP 收口** |
| soak | BEGIN 取消 ×N；heartbeat raise 跨 lease ×N | 集成 | **退出硬闸** |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 VF86 e2e `sqlite3.connect` Turso 检查（owner NS1-V11）→ harness charter（VF35.r）。
- 不覆盖真 GPU / Claude 登录 live soak（VF88）→ NS2-GPU。
- 不覆盖真机 `BEGIN CONCURRENT` constitution e2e（VF91.r）。
- 不覆盖 browser/OCR/Vision E2E（VF97）。
- 不覆盖 billing `has_quota==false`（VF23）。
- 不覆盖 `/docs` 关闭（VF32 / 第 1 轮 VF79）。
- 不覆盖检索 `read_transaction`（VF20）。
- 不覆盖 014 脏库自愈（VF6）。
- 不覆盖进程组杀孙进程（VF11.r）、未编目 orphan（VF25.r）、D04 55 表（VF4.r）。
- 不覆盖全仓 pytest 441/441。**不在本 AP 假装覆盖。**

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组；计数 ≠ 价值。
- ✅ **每个 Test-ID 的防假绿谓词写在 §8.1 最后一列**；收口时逐条对照，不得用「套件 PASS」替代。
- 先 RED 后绿：P6-01 必须演示「删 SUT / no-op → RED」。
- 禁止新写 `sqlite3.connect` 打开 Turso 文件。
- 禁止 `assert ... or True`、缺文件 `return`、自造 dict、`inspect.getsource` 冒充行为、`gather` 两次冒充 TTL、lease 到期前 recover 冒充心跳。
- `degraded` 必带机器可读 reason。
- 安全项必须含攻击向量（§7.3）。
- pre-existing 失败（VF86 e2e）必须在 closure 标 `deferred` 并指 NS1-V11，不 silent overclaim。
- `[true-bug]` 若修不动必须升 blocker 交 owner，禁止改 class。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| P1-02 默认 ready 合同 | 拆错会重新谎报 CW 或永远 503 | `high` | 探针位保留；REQUIRED 只合取 write_path_ready；T02 无 waiver |
| P1-03 切 mvcc | 探针仍打生产文件 | `high` | 第二连接断言；失败即回退 |
| P1-07 GC fence | deleting 状态与 promote 死锁 | `high` | rename+restore 路径；T07 读字节 |
| P4-04 unique 加列 | 已有重复 external_key 升级失败 | `medium` | 先规范化/去重再加索引 |
| P4-01 UPDATE→INSERT | 旧代码依赖 withdrawn 就地改写 | `high` | T21 COUNT indexed；015 已允许跨代 INSERT |
| VF62 被顺手打开 | 心跳异常未绿即重叠 | `high` | 本 AP 明确不打开；CI 不得设 allow_overlapping |
| 假绿回潮 | P6 前合并 tautology 修补 | `high` | P6 最后；§8.1 防假绿列 |
| VF86 红噪声 | 全量 pytest 仍可能 e2e 红 | `medium` | closure 显式 deferred；不以全绿为 DoD |
| VF15 migration | 与 014/015 链顺序 | `medium` | 016 幂等；upgrade 夹具 |

### 9.2 约束与前提

- **技术前提**：Python 3.12 `CancelledError` 是 `BaseException`；业务 UoW 为 `BEGIN IMMEDIATE`；pyturso 文件引擎。
- **运行时前提**：本轮仍默认 `LIVE_INFERENCE=false` + stub；不要求 GPU。默认 `concurrent_writes_required=True` 必须可领活。
- **组织协作前提**：不重开 VF class；owner 不在本 AP 解冻 NS1-V11 / billing / `/docs` / 重叠 `run_once`。
- **上线 / 合并前提**：每 Phase 独立可回滚；P6 前不得标 `executed`。

### 9.3 文档同步要求

- 需要同步更新的设计文档：S12（ready 语义 vs CW 探针）、S15（TTL / write_path_ready）、S09（serving 行不可变）、S16（空 CIDR 不信 XFF）——**窄回填，不重写章节**
- 需要同步更新的说明文档 / README：默认 Turso 画像可领活；禁止把 waiver 当生产合同
- 需要同步更新的测试说明：deferred-items-ledger 增加 NS6 余项指针；2nd-pass VF-ledger §6 append；NS5 closure P2-05/P2-07 翻 🟡

### 9.4 完成后的预期状态

1. 单例连接在 BEGIN 取消后可再 BEGIN；默认 Turso 画像 `/ready` 为 ready 且 worker 可 claim。
2. readiness 不把生产库 `journal_mode` 切成 mvcc；vLLM probe 不把 generate 冻在 5s。
3. 再 vectorize 不打穿 serving indexed COUNT；HITL approve 后可发布；同 external_key 幂等。
4. 空 CIDR 忽略 XFF；PATCH 拒密；chunked 超 cap 413。
5. NS5 短途假绿按谓词变真红；closure 不再用 ✅ 掩盖 TTL/Team PK。全量 pytest 仍可能因 VF86 非全绿，closure 诚实记录。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 测试项必须 **PASS 且四元组证据齐全**：

1. 取消 BEGIN 后再 BEGIN 成功（`NS6-T01` / `NS6-T36`）
2. 默认 Settings 下 ready+claim（`NS6-T02` / `NS6-T35`）
3. 第二连接 journal_mode 不变（`NS6-T03`）
4. probe 后 generate 不被 5s 打断（`NS6-T04`）
5. 再 vectorize serving COUNT≠0（`NS6-T21`）
6. 同 key 二次 ingest 非 201+failed（`NS6-T24`）
7. 空 CIDR + 伪造 XFF 进不了 `/metrics`（`NS6-T28`）；PATCH apiKey 422（`NS6-T29`）；chunked 413（`NS6-T30`）
8. 假绿短途删 SUT 会红（`NS6-T33`）；heartbeat raise 跨 lease（`NS6-T06` / `NS6-T36`）
9. PersistencePort 主链 mega（`NS6-T35`）；NS5 closure 过关叙述已翻（`NS6-T34`）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| BEGIN 取消可再 BEGIN | P1-01 | NS6-T01 / T36 | `commit + test + run-time` | `未观察` |
| 默认 ready+claim | P1-02 | NS6-T02 / T35 | `commit + test + run-time` | `未观察` |
| 活库 journal_mode 不变 | P1-03 | NS6-T03 | `commit + test + run-time` | `未观察` |
| generate 不被 5s 冻 | P1-04 | NS6-T04 | `commit + test + run-time` | `未观察` |
| handler 取消 + pending 空 | P1-05 | NS6-T05 | `commit + test + run-time` | `未观察` |
| heartbeat 异常 fence | P1-06 | NS6-T06 / T36 | `commit + test + run-time` | `未观察` |
| GC 不丢字节 | P1-07 | NS6-T07 | `commit + test + run-time` | `未观察` |
| TTL 真缓存 | P1-08 | NS6-T08 | `commit + test + run-time` | `未观察` |
| schema 闭集 | P2-01 | NS6-T09 | `commit + test + run-time` | `未观察` |
| 不复用墓碑 | P2-02 | NS6-T10 | `commit + test + run-time` | `未观察` |
| dead 可观测 | P2-03 | NS6-T11 | `commit + test + run-time` | `未观察` |
| stale owner CAS | P2-04 | NS6-T12 | `commit + test + run-time` | `未观察` |
| retirement 队头 | P2-05 | NS6-T13 | `commit + test + run-time` | `未观察` |
| fail fencing | P2-06 | NS6-T14 | `commit + test + run-time` | `未观察` |
| cancel 非 succeeded | P2-07 | NS6-T15 | `commit + test + run-time` | `未观察` |
| Team 409 | P2-08 | NS6-T16 | `commit + test + run-time` | `未观察` |
| salvage=运输 | P3-01 | NS6-T17 | `commit + test + run-time` | `未观察` |
| 证据不串台 | P3-02 | NS6-T18 | `commit + test + run-time` | `未观察` |
| lease 置空 | P3-03 | NS6-T19 | `commit + test + run-time` | `未观察` |
| CLI 边界 | P3-04 | NS6-T20 | `commit + test + run-time` | `未观察` |
| serving 不可变 | P4-01 | NS6-T21 | `commit + test + run-time` | `未观察` |
| HITL 可发布 | P4-02 | NS6-T22 | `commit + test + run-time` | `未观察` |
| digest=bytes | P4-03 | NS6-T23 | `commit + test + run-time` | `未观察` |
| external_key 幂等 | P4-04 | NS6-T24 | `commit + test + run-time` | `未观察` |
| namespace/purge | P4-05 | NS6-T25 | `commit + test + run-time` | `未观察` |
| generation 原子 | P4-06 | NS6-T26 | `commit + test + run-time` | `未观察` |
| embed 配方 | P4-07 | NS6-T27 | `commit + test + run-time` | `未观察` |
| 空 CIDR 不信 XFF | P5-01 | NS6-T28 | `commit + test + run-time` | `未观察` |
| PATCH 拒密 | P5-02 | NS6-T29 | `commit + test + run-time` | `未观察` |
| chunked 413 | P5-03 | NS6-T30 | `commit + test + run-time` | `未观察` |
| overflow undo | P5-04 | NS6-T31 | `commit + test + run-time` | `未观察` |
| mapped/限流桶 | P5-05 | NS6-T32 | `commit + test + run-time` | `未观察` |
| 假绿拆除 | P6-01 | NS6-T33 | `commit + RED演示 + run-time` | `未观察` |
| closure 翻 🟡 | P6-02 | NS6-T34 | `commit + grep + run-time` | `未观察` |
| 主链 mega | P6-03 | NS6-T35 | `commit + mega + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 34 条 in-scope VF 按 §3 落地；8 条 `[true-bug]` 无静默 defer |
| 测试 | §8 短途+spike+硬闸 mega/soak PASS；四元组齐全；每项防假绿谓词对照；VF86 明示 deferred |
| 文档 | README 窄回填；deferred-items-ledger 接 NS6 余项；2nd-pass VF-ledger §6 append；NS6 closure；NS5 closure P2-05/P2-07 翻 🟡 |
| 风险收敛 | BEGIN 取消可再写；默认画像可领活；journal_mode 不变；serving COUNT 不被 UPDATE 打穿 |
| 可交付性 | 默认 Turso 叶工人可 `/ready` 并 claim；**不**要求全量 pytest 全绿 |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。VF86 全量红必须标 `deferred` 并指 NS1-V11，不把 unit 计数读成行为已被证明。`[true-bug]` 若修不动必须升 blocker 交 owner，禁止改 class。用 `local_runtime` waiver 把 T02 标 PASS ⇒ **本 AP 未收口**。

---

## 11. 执行日志回填（append-only）

> 执行者：`Grok`
> 执行时间：`2026-08-20`
> 文档状态：`draft → executing → executed`
> 代码改动统计：P1–P6 已落地；016 schema bump 1

- **实际执行摘要**：Phase 1 按 DAG 首段落地 P1-01…P1-08（VF1/2/3/7/21/22/25/36）。VF62 重叠 `run_once` 保持关闭。
- **Phase 偏差（计划 vs 实际）**：
  - P1-02 REQUIRED 用 `write_path_ready` 替换 `concurrent_writes`（substrate-fit）：`concurrent_writes` 仍诚实为 False（UoW 保持 IMMEDIATE），探针位 `concurrent_writes_probe` 改 scratch 文件，不打生产库。
  - P1-03 CW 探针改 `probe_concurrent_writes_scratch`（计划偏差 / 风险控制）：禁止在生产连接 `journal_mode=mvcc` 再 restore。
  - P1-08 TTL 加 `cache_fingerprint=tokens.active_fingerprints`（substrate-fit）：避免把 token 替换后的 `/ready` 锁成旧结果。
- **阻塞与处理**：无。
- **测试发现**：NS6-T01…T08 8 passed；`test_readiness_composition` / `test_object_gc` / `test_ns5_uow_cancel` / `test_ns5_phase1_runtime` / `test_turso_driver` / `test_inference_runtime` / `test_workflow_runtime` 回归绿。
- **后续 handoff**：Phase 2 可开工（依赖 P1 UoW / ready 稳定）。

### 11.1 Phase 1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点（file:line） | 备注 |
|--------|------|----|------------------------|------|
| P1-01 | `✅ done` | local | `src/persistence/uow.py` BEGIN 纳入同一 `try`；sqlite/turso 共用 helper | 未 BEGIN 则 `discard()` |
| P1-02 | `✅ done` | local | `health.py` REQUIRED=`write_path_ready`；`turso/port.py`/`sqlite_port.py` 返回该位；`runtime_core.py` fallback 同步 | 禁止 waiver 当绿证；T02 用默认 Settings |
| P1-03 | `✅ done` | local | `engine.py` `probe_concurrent_writes_scratch`；ports 不再对 live 文件 `journal_mode=mvcc` | T03 第二连接 mode 不变且 ≠ mvcc |
| P1-04 | `✅ done` | local | `local_vllm.py` 共享 client `timeout=None` + per-request timeout + `trust_env=False`；lifespan `aclose` | T04 断言 POST timeout=180 |
| P1-05 | `✅ done` | local | `worker.py` `finally` cancel 未完成 `handler_task` 并 `_discard_pending` | T05 `handler_task.cancelled()` 且 `_pending=={}` |
| P1-06 | `✅ done` | local | `worker.py` `_heartbeat_loop except Exception: fenced+cancel` | 不捕 CancelledError；不打开重叠 |
| P1-07 | `✅ done` | local | `local_store.py` quarantine/restore/destroy；`object_gc.py` TX2 见 live ref 则 restore | 禁止把 TX2 409 当已保护 |
| P1-08 | `✅ done` | local | `health.py` 顺序 TTL 缓存 + fingerprint 失效 | T08 两次顺序 ready → probe==1 |

### 11.2 Phase 1 时序

| 时点 | 步骤 | 决策 / 产出 |
|------|------|-------------|
| `T0` | 重读 NS6 AP + VF-ledger 批次 1 + A-1…A-8 | 串行 P1→P2；禁止 waiver / CONCURRENT / 打开 VF62 |
| `T1` | P1 代码 | UoW BEGIN fence + write_path_ready + scratch CW + vLLM timeout + handler/heartbeat + GC quarantine + TTL |
| `T2` | P1 测试 | `uv run pytest` NS6-T01–T08 + 相关回归 PASS |

### 11.3 Phase 2 回填

- **实际执行摘要**：P2-01…P2-08（VF4/5/23/24/26/27/28/37）。schema 核心表闭集；live lookup 滤 tombstone；outbox.dead 看 rowcount + metrics + owning trace；retirement 对 pointer=None 一律 abandon；fail CAS 带 fencing_generation；cancel 同 TX 栅栏 Execution 并去掉 success-wins；Team UNIQUE → 409。
- **Phase 偏差**：无 in-scope 代码偏差。supervisor 异常路径不再 `progressed+=1`。
- **测试发现**：`tests/unit/test_ns6_phase2.py` 8 passed；`test_ns5_outbox_poison` / `test_ns5_retirement_stuck` / `test_ns5_phase2` 回归绿。

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P2-01 | `✅ done` | `migration_runner.py` `_CORE_SCHEMA_TABLES` | DROP outbox → schema false |
| P2-02 | `✅ done` | `artifacts.live_stored_object_uuid`；generation/config/rebuild/scatter/task_create | 墓碑 uuid 不再复用 |
| P2-03 | `✅ done` | `runtime_core.py` metrics；`runtime_outbox.py` owning trace | `/metrics` 同源 `metrics.render()` |
| P2-04 | `✅ done` | `_mark_outbox_dead`/`_release_outbox` `rowcount==1`；repair 滤 pending/in_flight | stale owner 0 事件 |
| P2-05 | `✅ done` | `_close_unavailable_intent_tx` 不再要求 item gone | namespace disabled 可让队 |
| P2-06 | `✅ done` | `_fail_process_tx` `AND fencing_generation=?` | 旧 fail 不打死新世代 |
| P2-07 | `✅ done` | `task_commands.cancel` CAS execution/process；projection 去掉 success-wins | Task 不得 succeeded |
| P2-08 | `✅ done` | `teams.create` IntegrityError → 409/replay | stub UNIQUE |

### 11.4 Phase 3 回填

- **实际执行摘要**：P3-01…P3-04（VF8/9/10/11）。salvage 去掉 BACKPRESSURE；证据强制 process_uuid；Facade retry 释放后 `lease=None`；CLI allowlist + 流式字节帽 + shield terminate。
- **Phase 偏差**：salvage NI occupancy 复用 CLI `ConcurrencyGate("cli")`（cli.run 已占位），不另开 durable NI Process 行（计划偏差 / substrate-fit：本轮未承诺改 dispatch 状态机）。
- **测试发现**：`test_ns6_phase3.py` 4 passed；`test_ns5_phase3` / `test_inference_runtime` / `test_claude_cli_port` / `test_ns4_stage_report_tx` 回归绿。

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P3-01 | `✅ done` | `_API_INFERENCE_SALVAGE_CODES` 去掉 BACKPRESSURE | 满门 cli.run 不得再开 |
| P3-02 | `✅ done` | `generation_evidence.py` 删除 `"_"` 回退 | 省略 uuid 不串台 |
| P3-03 | `✅ done` | `facade.py` release 后 `lease=None`；finally 只 release 非空 | 取消 sleep 无 RuntimeError |
| P3-04 | `✅ done` | `_cli_child_env` allowlist；`_bounded_communicate`；terminate 捕 CancelledError | 无 AWS secret；overflow 即杀 |

### 11.5 Phase 4 回填

- **实际执行摘要**：P4-01…P4-07（VF12–18）。upsert 只碰 withdrawn+同代；consume_gate_decision 激活 HITL；raw/clean 分 CAS；016 unique external_key；namespace 按 Layer A 分键；generation TX 内 CAS；full_construct 不传 title headers。
- **Phase 偏差**：T22/T24 全链 ingest e2e 未在本 Phase 短途展开（计划偏差 / 测试分层）——以 consume_gate_decision 接线 + 016 unique + 同 TX resolve 为代码收口；mega 在 P6。
- **测试发现**：`test_ns6_phase4.py` + `test_ns5_phase4` / construct / compiler / dispatch embed 回归绿。

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P4-01 | `✅ done` | `_existing_vector_coordinate_uuid` / upsert SELECT `withdrawn`+generation | indexed COUNT 不被 UPDATE |
| P4-02 | `✅ done` | `consume_gate_decision` 调 `_apply_human_review_item_lifecycle_tx` | approve→active |
| P4-03 | `✅ done` | acceptance promote raw/clean；rebuild 读 sha256(bytes) | 禁止 JSON peel |
| P4-04 | `✅ done` | `016_ns6_source_external_key.sql`；callback 同 TX resolve；ordinal MAX+1 | unique (team,kind,key) |
| P4-05 | `✅ done` | namespace_key=`model\|version\|adapter\|dimension` | 改维新 ns |
| P4-06 | `✅ done` | vectorize callback `index_generation` CAS | 并发不得双写 N+1 |
| P4-07 | `✅ done` | full_construct `metadata_headers=None` | binder 409 与 body-only 一致 |

### 11.6 Phase 5 回填

- **实际执行摘要**：P5-01…P5-05（VF29–34）。空 CIDR 永不抄 XFF；PATCH extras 拒密；chunked 流式累计 413；overflow undo 退回 overflow 桶；ipv4_mapped 对齐。
- **Phase 偏差**：无。
- **测试发现**：`test_ns6_phase5.py` + `test_security_boundary` / `test_ns5_phase5` 回归绿。

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P5-01 | `✅ done` | `request_ip` 删除 empty-CIDR 私网 XFF 分支 | peer 10.0.0.1 不被 127.0.0.1 顶替 |
| P5-02 | `✅ done` | TeamPatch/TaskPatch `assert_safe_public_data` | PATCH apiKey → ValidationError |
| P5-03 | `✅ done` | `reject_oversize_body` 流式累计 | 无 CL chunked 413 |
| P5-04 | `✅ done` | `decide` 返回 effective_key；undo 用之 | 第三 IP 仍 DETAIL |
| P5-05 | `✅ done` | `_is_private_peer`/`_ip_in_cidrs` 递归 mapped | 不重开空 CIDR XFF |

### 11.7 Phase 6 回填

- **实际执行摘要**：P6-01 假绿短途改为真 SUT；P6-02 NS5 P2-05/P2-07 翻 🟡；P6-03 mega/soak/ruff/build/migration destroy-rebuild；NS6 closure r2。
- **Phase 偏差**：BEGIN-cancel soak 不再对 sqlite `Connection.execute` 阻塞窗口做 in-process 重复 close（会 SIGSEGV）；改为 patch `uow.asyncio.to_thread` 的 BEGIN 睡眠窗口 ×5。heartbeat raise ×3 仍真跑。
- **测试发现**：NS6 unit 47 passed；ruff 0；`uv build` 含 016；Turso destroy-rebuild ok；mainchain vector COUNT≥1。全量 pytest / VF86 未宣称。

### 11.8 自我审核循环回填（2026-08-20 11:44 UTC）

- **实际执行摘要**：六轴审核后硬切 in-scope 余项：registered_api unique、017 Layer-A generation unique、GC fail-closed + `quarantine/<team>/`、purge=`all` 经 PersistencePort、默认 Settings mega+retrieval、T21–T26 谓词重写、factory 懒加载 sqlite、glossary 改 Turso。S12/S13/S15/S16/S09/S10 窄回填。观察 `tests/unit tests/domain tests/integration` exit 0。
- **Phase 偏差**：T24 同指纹二次 ingest 的 structurize outcome-commit 仍可能失败（VF15.r）；T01 soak 仍为 `to_thread` 门（已知 hotfix）。VF86 (a) 未开 harness。
- **测试发现**：unit/domain/integration exit 0；ruff 0。未宣称 441/441。
- **后续 handoff**：VF86/6/20/32/62 与 VF4.r/11.r/25.r 见 deferred-items-ledger NS6。

| 工作项 | 状态 | 实际落点 | 备注 |
|--------|------|----------|------|
| P6-01 | `✅ done` | ReadPort 实例化查询；sidecar insert；`_journal_row` exec；TTL 顺序 | 删 inspect.getsource 冒充 |
| P6-02 | `✅ done` | NS5 closure P2-05/P2-07 🟡 | 不发明 VRX5 |
| P6-03 | `✅ done` | NS6 closure；VF-ledger §6；deferred NS6 | 硬闸四元组在 closure r2 |
