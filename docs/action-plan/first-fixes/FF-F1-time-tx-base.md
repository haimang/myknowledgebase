# Nano-Agent 行动计划 — FF-F1 时间与事务基座

> 服务业务簇: `smind-family / first-fixes`
> 计划对象: `F1 · 时间与事务基座（keystone）`
> 类型: `refactor`（统一时间 SSOT + 显式事务化，非新功能）
> 作者: `Claude (sub-agent, FF-F1 派生)`
> 时间: `2026-05-31`
> 文件位置: `docs/action-plan/first-fixes/FF-F1-time-tx-base.md`
> 上游前序 / closure:
> - `无（F1 是关键路径起点 keystone；不依赖任何前序 phase）`
> 下游交接:
> - `FF-F3-kernel-recovery.md`（F1-04 包裹的 workflow_core 多写函数与 F3-02 终态归属重构高度重叠，建议同窗口推进）
> - `FF-F6c-auth-config.md`（F6 各执行器/认证面依赖统一时间 SSOT 写时间列）
> 关联设计 / 调研文档:
> - `docs/design/first-fixes/initial-planning-by-opus.md`（§6.1 F1 台账、§2.C 定档、§4 红线第 1/3 条、§5 强耦合说明、§8 capstone/DoD、§10.A 派生图）
> - `docs/eval/first-code-review-plan/part-cr-1.md`（G-CR1-01/02/03 时间根因）、`part-cr-2.md`（G-CR2-02 isolation_level）、`part-cr-4.md`（G-CR4-R6/R15 多写原子性）
> 冻结决策来源:
> - `docs/design/first-fixes/owner-gated-qna.md`（只读引用 [Q7] test-first 铁律；本 AP 不填写 Q/A）
> grounding 来源:
> - `eval part-cr-1/2/4`（§7 内置锚区据此摘录 file:line）+ 实际源码核对（本 AP §7.1 锚表为真源）
> 关联 reference-anchor:
> - `见 §7 内置锚区`（本链 reference-anchor 由 part-cr-1~8 预完成，§7.1 为相关子集摘录）
> 文档状态: `draft`

---

## 0. 执行背景与目标

八簇代码审查（part-cr-1~8）的总判断是"管道接得上、语义为空、测试无法证明正确性"。其中最底层的单点根因是**时间格式三处分裂**与**事务模式未显式化**：系统同时存在三种时间串格式（`common.utc_now_iso` 的微秒+偏移、`_utils.now_iso` 的畸形丢秒串、SQL 侧 `CURRENT_TIMESTAMP`），且写入 `available_at`/`lease_expires_at` 的实际来源 `_utils.now_iso()` 与视图 `v_ready_steps`/`v_stale_claims` 的 `strftime('%Y-%m-%dT%H:%M:%fZ')` 字符串比较**不可比**——实测 `app_now <= sqlite_now` 返回 `False`（本应 `True`），导致 step 永不就绪、过期 claim 永不回收（part-cr-1 R1 / part-cr-4 R1 关联）。同时 engine `connect()` 未设 `isolation_level`，整个内核的事务正确性靠"每个 helper 末尾无条件 commit"这一脆弱约定续命（part-cr-2 R2，已实测 `BEGIN IMMEDIATE` 在裸 DML 后抛 `cannot start a transaction within a transaction`）。

F1 是关键路径 `F1 → F3 → F6 → F7` 的起点（keystone）：修好时间 SSOT 才能让 F3 的 reap/restart 真正命中；改 `isolation_level=None`（autocommit）是显式 `BEGIN IMMEDIATE` 事务模型成立的前提。本 AP 把 final plan §6.1 的 F1-01~05 落成可交付物：统一时间到单一函数、删除畸形实现与第三种格式、把 engine 转 autocommit 并**逐个包裹 workflow_core 全部多写 helper 为显式事务**，并以"先红后绿"的回归测试封住每个 blocker。

**关键耦合提示**：F1-04 包裹的多写函数（claim/succeed/fail/reap/restart/purge）与 FF-F3 的 F3-02 终态归属重构触碰**同一组 workflow_core 函数**。建议 F1-04 与 F3-02 在同一改动窗口推进，避免两次触碰同组函数引入重复回归（依据 initial-planning §5 强耦合说明、§10.A 时序）。

> **纪律**：本文件只消费已冻结结论（[Q7] test-first）；不开 Q/A、不等待 owner。

- **服务业务簇**：`smind-family / first-fixes`
- **计划对象**：`F1 时间与事务基座`（工作项 F1-01~05）
- **本次计划解决的问题**：
  - `时间格式三处分裂（common 微秒+偏移 / _utils 畸形丢秒 / SQL CURRENT_TIMESTAMP），导致 PY 写入值与 SQL strftime 字典序不可比（G-CR1-01/02/03）`
  - `内核实际写时间列的 _utils.now_iso() 缺 %S 秒字段，使 v_ready_steps/v_stale_claims 比较出错，step 永不就绪 / 过期 claim 永不回收（part-cr-1 R1）`
  - `engine 未设 isolation_level，BEGIN IMMEDIATE 与隐式事务可复现冲突；autocommit 后若多写不显式 BEGIN 则每写即提交、丧失原子性（末尾 commit 成 no-op）（G-CR2-02 + part-cr-4 R6）`
- **本次计划的直接产出**：
  - `smind_common.time 输出 YYYY-MM-DDTHH:MM:SS.mmmZ（毫秒 3 位 + Z），与 SQLite strftime('%Y-%m-%dT%H:%M:%fZ') 严格可比；内核全调用点单一来源`
  - `删除 workflow_core/_utils.now_iso/add_seconds_iso 畸形实现 + 清除 workflow_clean/service.py 的 CURRENT_TIMESTAMP`
  - `engine connect() 设 isolation_level=None + workflow_core 6 个多写 helper 全部显式 BEGIN IMMEDIATE...COMMIT 包裹 + 中途失败整体回滚`
  - `先红后绿回归套件：时间 round-trip + 秒位正则 + 跨 PY/SQL 比较一致性 + 多写原子性`
- **本计划不重新讨论的设计结论**：
  - `全 phase 先红后绿铁律（每 blocker 先红后绿回归为退出证据）`（来源：`[Q7]`）
  - `统一时间 SSOT 格式 = ...SS.mmmZ；事务原子性显式化（autocommit + 显式 BEGIN IMMEDIATE）`（来源：`initial-planning §4 红线第 1/3 条`，已 frozen）

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用 **"先底层 SSOT 后调用点、先审计后包裹事务、先红后绿"** 的执行方式，分 3 个 Phase：先把 `smind_common.time` 立为唯一时间真源（Phase 1），再清除内核与 clean 的两种偏离格式使全系统单一来源（Phase 2），最后做最高风险的事务模式切换——engine 转 autocommit 并逐个包裹多写 helper（Phase 3）。每个 Phase 的退出判据是对应的"修复前红、修复后绿"回归测试 PASS，而非编译通过或 `status==200`。本节只写执行策略，不重述时间/事务方案本身的设计理由（见 §6 引用）。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 时间 SSOT 立基（F1-01） | S | `smind_common.time` 输出 `...SS.mmmZ`，与 SQL strftime 严格可比 | `-` |
| Phase 2 | 双源/第三格式清除（F1-02 / F1-03） | S | 删 `_utils.now_iso/add_seconds_iso` 畸形实现 + 清 `CURRENT_TIMESTAMP`，内核全调用点单一来源 | `Phase 1` |
| Phase 3 | 事务模式显式化（F1-04，最高风险） | M | engine autocommit + 6 个多写 helper 显式 `BEGIN IMMEDIATE...COMMIT` 包裹 | `Phase 1（SSOT 稳定）` |

> 说明：上表 `规模` 是描述性提示，不是开工闸，不改变本模板任何段落取舍。F1-05 测试不单列 Phase，作为各 Phase 的"先红后绿"退出证据贯穿（§8 台账）。

### 1.3 Phase 说明

1. **Phase 1 — 时间 SSOT 立基**
   - **核心目标**：把 `smind_common.time.utc_now_iso()` 改为输出 `YYYY-MM-DDTHH:MM:SS.mmmZ`，并提供 `add_seconds_iso` 下沉到 common 作为唯一带偏移实现。
   - **为什么先做**：它是全系统时间真源；Phase 2 的内核改用 common、Phase 3 的事务回归都建在"格式已对"的前提上。
2. **Phase 2 — 双源/第三格式清除**
   - **核心目标**：删除 `workflow_core/_utils.now_iso/add_seconds_iso`，内核全调用点改 import `smind_common.time`；清除 `workflow_clean/service.py` 的 `CURRENT_TIMESTAMP`，统一走 SSOT/DDL DEFAULT。
   - **为什么放在这里**：消除第二、第三种格式，使"修一处生效全局"成立；必须在 Phase 1 SSOT 正确后才有意义。
3. **Phase 3 — 事务模式显式化（最高风险）**
   - **核心目标**：engine `connect()` 设 `isolation_level=None`（autocommit），并审计 + 逐个把 workflow_core 6 个多写 helper 包裹为显式 `BEGIN IMMEDIATE...COMMIT`，确保 autocommit 下多写仍原子（中途失败整体回滚）。
   - **为什么放在这里**：这是 M 级、high 风险、影响全局事务语义的改动，需要时间 SSOT 已稳固（Phase 1/2）后再做；且与 FF-F3 同窗口推进。

### 1.4 执行策略说明

> **纪律**：本节只写"怎么执行"，不重述 §6 冻结决策的设计理由。

- **执行顺序原则**：`先底层（time SSOT）→ 调用点迁移 → 事务模式切换；time → 内核迁移 → autocommit 三层依次推进，绝不在 SSOT 未对前改 autocommit。`
- **风险控制原则**：`F1-04 是唯一 high 风险项——先审计列出全部 6 个多写 helper 的事务边界，逐个包裹后立即跑该函数原子性回归，再进下一个；与 FF-F3 F3-02 同窗口避免重复触碰。`
- **测试推进原则**：`每个 blocker 先写当前 HEAD FAIL 的回归（红），修复后转绿；短途 unit（时间格式/正则/round-trip）+ 集成（跨 PY/SQL 比较、多写原子性）随 Phase 提交，详见 §8。`
- **文档同步原则**：`time SSOT 格式落点回链 database.md §9.2；本 AP 执行后由 FF-F7 closure 据真实断言定级，本阶段不预先标 ✅。`
- **回滚 / 降级原则**：`P 阶段无生产数据；若已有库含畸形时间串，附一次性归一迁移（非本 AP 范围，记 §9 风险）。F1-04 若某 helper 包裹后回归失败，回退该单函数包裹、保留其余，不整体回退。`

### 1.5 本次 action-plan 影响结构图

```text
F1 时间与事务基座
├── Phase 1: 时间 SSOT 立基
│   └── packages/common/src/smind_common/time.py（utc_now_iso 改格式 + 新增 add_seconds_iso）
├── Phase 2: 双源/第三格式清除
│   ├── packages/workflow_core/src/workflow_core/_utils.py（删 now_iso/add_seconds_iso）
│   ├── workflow_core/{claim,leases,retry,restart,purge,events}.py（改 import smind_common.time）
│   └── packages/workflow_clean/src/workflow_clean/service.py（清 CURRENT_TIMESTAMP）
└── Phase 3: 事务模式显式化（最高风险，与 FF-F3 同窗口）
    ├── packages/storage_sqlite/src/storage_sqlite/engine.py（isolation_level=None）
    └── workflow_core 多写 helper（claim/succeed/fail/reap/restart/purge 包 BEGIN IMMEDIATE...COMMIT）
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `F1-01：smind_common.time.utc_now_iso() 输出 YYYY-MM-DDTHH:MM:SS.mmmZ；add_seconds_iso 下沉 common 作唯一带偏移实现。`
- **[S2]** `F1-02：删除 workflow_core/_utils.now_iso/add_seconds_iso，内核全调用点（claim/leases/retry/restart/purge/events）改用 smind_common.time。`
- **[S3]** `F1-03：清除 workflow_clean/service.py 两处 CURRENT_TIMESTAMP，统一走 SSOT/DDL DEFAULT。`
- **[S4]** `F1-04：engine connect() 设 isolation_level=None + 6 个 workflow_core 多写 helper 显式 BEGIN IMMEDIATE...COMMIT 包裹（审计 + 逐个 + 回归）。`
- **[S5]** `F1-05：先红后绿测试套件（时间 round-trip + 秒位正则 + 跨 PY/SQL 比较 + 多写原子性中途失败整体回滚）。`

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `reap_expired_claims 的 worker 循环接线（F3-01）—— 属 FF-F3；本 AP 只保证其时间比较与原子性正确，不接线运行时调用。`
- **[O2]** `执行器终态归属重构 / 执行器契约定义（F3-02）—— 属 FF-F3；本 AP 只包裹现有多写函数的事务，不改终态写入归属（但同窗口推进）。`
- **[O3]** `graph.write_workflow_event 死代码删除与 events created_at 交 DDL DEFAULT（F3-07）—— 属 FF-F3。`
- **[O4]** `retry 退避读 schema 列 / 错误分类透传（F3-06）、batch 单事务拆分（part-cr-4 R12）—— 属 FF-F3。`
- **[O5]** `已有库畸形时间串的一次性归一迁移 —— P 阶段无生产数据，按需附迁移脚本，本 AP 仅记风险（§9）。`

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `时间 SSOT 格式 + 内核迁移 + CURRENT_TIMESTAMP 清除` | `in-scope` | F1 的单点根因，必须一次性收口才"修一处生效全局" | `-` |
| `engine autocommit + 多写 helper 包 BEGIN IMMEDIATE` | `in-scope` | autocommit 是 BEGIN IMMEDIATE 成立前提，且会破坏 succeed/fail/reap 原子性，必须同 AP 内成对完成 | `-` |
| `reap 接线 / 执行器契约 / graph 死代码删除` | `out-of-scope` | 归 FF-F3，本 AP 与其同窗口但边界清晰：F1 管事务包裹，F3 管终态归属/接线 | `F3-02 终态重构落地时复核包裹边界` |
| `已有库时间串归一迁移` | `defer / depends-on-design` | P 阶段无生产数据 | `首次出现含畸形时间串的存量库时` |

---

## 3. 业务工作总表

> 编号沿用 final plan 的 `F1-NN`。三元组（涉及文件 file:line / 收口目标 / 测试映射）齐全。F1-04 为净新高风险，§4 工作内容拆有序子步。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| F1-01 | Phase 1 | 统一时间 SSOT：`utc_now_iso` 输出 `...SS.mmmZ` + `add_seconds_iso` 下沉 common | `update` | `packages/common/src/smind_common/time.py:4-5`（改）；`smind_common/__init__.py:4,6`（导出 add_seconds_iso） | `utc_now_iso() 形如 ^\d{4}-..\.\d{3}Z$，与 SQLite strftime('%Y-%m-%dT%H:%M:%fZ') 长度一致、字典序可比` | `FF-F1-T01` / `FF-F1-T02` / `FF-F1-T03` | `low` |
| F1-02 | Phase 2 | 删 `_utils.now_iso/add_seconds_iso` 畸形实现，内核全调用点改用 common | `remove` | `packages/workflow_core/src/workflow_core/_utils.py:5-12`（删）；`claim.py:5,34,64`、`leases.py:3,14,21,39`、`retry.py:3,14,87`、`restart.py:8,35,49,71,100`、`purge.py:8,35,54,81,92,109`、`events.py:6,34,66`（改 import） | `_utils 不再含时间函数；grep now_iso/add_seconds_iso 在内核 0 处指向 _utils；全部指向 smind_common.time` | `FF-F1-T04` | `medium`（调用点多） |
| F1-03 | Phase 2 | 清除 `CURRENT_TIMESTAMP`（第三格式），统一走 SSOT/DDL DEFAULT | `update` | `packages/workflow_clean/src/workflow_clean/service.py:118,124` | `service.py 0 处 CURRENT_TIMESTAMP；finished_at/updated_at 走 SSOT 函数值或省略交 DDL DEFAULT` | `FF-F1-T05` | `low` |
| F1-04 | Phase 3 | engine `isolation_level=None` + 审计并包裹 6 个多写 helper 为显式 `BEGIN IMMEDIATE...COMMIT` | `refactor` | `packages/storage_sqlite/src/storage_sqlite/engine.py:13`（设 isolation_level）；`claim.py:16,91-95`（已有 BEGIN，复核）；`leases.py:23,105`（heartbeat/reap 补 BEGIN）；`retry.py:64,167`（succeed/fail 补 BEGIN）；`restart.py:138`（补 BEGIN）；`purge.py:149`（补 BEGIN，跨库注意 vec_conn） | `engine 用 autocommit；6 个多写函数全部以 BEGIN IMMEDIATE 开、COMMIT 收、except rollback；中途失败整批回滚无半提交` | `FF-F1-T06` / `FF-F1-T07` | `high` |
| F1-05 | 贯穿 | 先红后绿测试：时间 round-trip + 秒位正则 + 跨 PY/SQL 比较一致 + 多写中途失败整体回滚 | `add` | `tests/unit/test_time_ssot.py`（🆕）；`tests/integration/p1_kernel_closure/test_time_tx_atomicity.py`（🆕） | `每个 blocker 一条当前 HEAD FAIL、修复后 PASS 的回归；§8.5 防假绿` | `FF-F1-T01..T07` | `low` |

---

## 4. Phase 业务表格

> `工作内容` 为承重列。F1-04 净新高风险，拆有序子步 a/b/c。

### 4.1 Phase 1 — 时间 SSOT 立基

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F1-01 | 统一时间 SSOT | 把 `utc_now_iso()` 由 `datetime.now(tz).isoformat()` 改为输出 `YYYY-MM-DDTHH:MM:SS.mmmZ`（毫秒 3 位 + Z），例如 `dt.strftime("%Y-%m-%dT%H:%M:%S.") + f"{dt.microsecond // 1000:03d}Z"`；新增 `add_seconds_iso(seconds)` 下沉 common 作为唯一带偏移实现，复用同一格式化逻辑；`__init__.py` 导出 `add_seconds_iso`。 | `packages/common/src/smind_common/time.py:4-5`；`smind_common/__init__.py:4,6` | `utc_now_iso()/add_seconds_iso(n)` 输出 24 字符、毫秒 3 位、Z 结尾；与 SQLite strftime 字典序可比 | `FF-F1-T01`/`T02`/`T03` | round-trip + 正则 + 跨 PY/SQL 比较三测全绿 |

### 4.2 Phase 2 — 双源/第三格式清除

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F1-02 | 删畸形实现 + 内核单一来源 | 删除 `_utils.py:5-12` 的 `now_iso/add_seconds_iso`（保留 `new_id`）；把 `claim/leases/retry/restart/purge/events` 的 `from ._utils import now_iso, add_seconds_iso` 改为 `from smind_common.time import utc_now_iso as now_iso, add_seconds_iso`（或直接改调用名），逐个调用点核对。 | `_utils.py:5-12`；`claim.py:5`、`leases.py:3`、`retry.py:3`、`restart.py:8`、`purge.py:8`、`events.py:6` 及各 `now_iso()`/`add_seconds_iso()` 调用行 | 内核全部时间值来自 common 单一函数；`_utils` 仅余 `new_id` | `FF-F1-T04` | grep 内核 0 处 `_utils.now_iso`；T04 跨 PY/SQL 一致性回归绿 |
| F1-03 | 清除第三格式 | 把 `service.py:118` 的 `finished_at=CURRENT_TIMESTAMP` 与 `:124` 的 `updated_at=CURRENT_TIMESTAMP` 改为绑定 SSOT 函数值（`now_iso()` 参数化）或交 DDL DEFAULT（若该列有合规 DEFAULT）；保持与内核同一格式。 | `packages/workflow_clean/src/workflow_clean/service.py:118,124` | service.py 0 处 `CURRENT_TIMESTAMP`；写入值与 SSOT 同格式可比 | `FF-F1-T05` | T05 断言 clean 写入的 finished_at 与 strftime 可比；grep 0 命中 |

### 4.3 Phase 3 — 事务模式显式化（最高风险）

| 编号 | 工作项 | 工作内容（有序子步 a/b/c + 边界）| 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F1-04 | engine autocommit + 多写 helper 显式事务包裹 | **a)** engine `connect()` 设 `conn.isolation_level = None`（autocommit），让 BEGIN/COMMIT/ROLLBACK 完全由代码掌控（engine.py:13 附近）。 **b)** 审计列全部 workflow_core 多写函数的事务边界：`claim_next_step`（已有 BEGIN IMMEDIATE，复核 commit/rollback 路径完整）、`heartbeat_claim`、`reap_expired_claims`、`succeed_claim`、`fail_claim`、`process_restart_requests`、`process_purge_requests`。 **c)** 逐个把"读后多写 + 末尾 commit"的函数改为：开头 `conn.execute("BEGIN IMMEDIATE")`，主体不变，末尾 `conn.commit()`，`except: conn.rollback(); raise`——逐个改完立即跑该函数的中途失败回滚回归（T07）。 **d) 边界**：`reap`/`restart`/`purge` 的循环批写——本 AP 保持现有"整批一事务"语义（拆批属 FF-F3 R12），但 autocommit 下必须显式 BEGIN 包整批，否则循环内每条 UPDATE 即提交、丧失批原子性。 **e) 边界（跨库）**：`process_purge_requests` 在 core 事务内调 `VectorStore(vec_conn).delete_chunks`——vec_conn 是另一连接，core 的 BEGIN IMMEDIATE 不覆盖 vec 写，需注释标明跨库非原子（归 FF-F4/F3 协调），本 AP 只保证 core 侧原子。 **f) 失败/降级**：任一 helper 包裹后 T07 回归失败，回退该单函数包裹保留其余，记 §9。 | `storage_sqlite/engine.py:13`；`claim.py:16,91-95`；`leases.py:7-24,27-106`；`retry.py:7-65,68-168`；`restart.py:29-139`；`purge.py:29-150` | autocommit 生效；6 个多写函数全部显式 `BEGIN IMMEDIATE...COMMIT`，except 回滚；中途失败无半提交 | `FF-F1-T06`/`T07` | T06（裸 DML 后 BEGIN IMMEDIATE 不冲突）+ T07（每个多写函数中途注入异常后整体回滚，0 残留行）全绿 |

---

## 5. Phase 详情

> 测试不在此展开，每项指向 §8 Test-ID。F1-04（Phase 3）净新高风险，`具体功能预期` ≥5 条含边界与失败路径。

### 5.1 Phase 1 — 时间 SSOT 立基

- **Phase 目标**：`smind_common.time` 成为全系统唯一时间真源，输出 `YYYY-MM-DDTHH:MM:SS.mmmZ`。
- **本 Phase 对应编号**：`F1-01`
- **本 Phase 新增文件**：`tests/unit/test_time_ssot.py`（F1-05 的 unit 部分）
- **本 Phase 修改文件**：`packages/common/src/smind_common/time.py:4-5`、`smind_common/__init__.py:4,6`
- **具体功能预期**：
  1. `utc_now_iso()` 返回串严格匹配 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$`（24 字符、含秒、毫秒 3 位、Z 结尾）。
  2. 返回串可被 `datetime.fromisoformat`（Z 替 `+00:00`）解析（round-trip）。
  3. 与 SQLite `strftime('%Y-%m-%dT%H:%M:%fZ','now')` 长度一致、字典序可比（PY now ≤ SQL 稍后 now 为 True）。
  4. `add_seconds_iso(n)` 同格式，且 `add_seconds_iso(60) > utc_now_iso()` 字典序成立。
- **对应测试台账项**：`FF-F1-T01` / `FF-F1-T02` / `FF-F1-T03`（详见 §8）
- **收口标准**：`T01/T02/T03 修复前红、修复后绿；smoke 的空洞断言（"T" in ...）被真断言取代`
- **本 Phase 风险提醒**：`低；唯一注意点是 microsecond // 1000 截断而非四舍五入，与 SQLite %f 行为一致（均截断毫秒）`

### 5.2 Phase 2 — 双源/第三格式清除

- **Phase 目标**：消除第二（`_utils` 畸形）、第三（`CURRENT_TIMESTAMP`）种时间格式，内核全调用点单一来源。
- **本 Phase 对应编号**：`F1-02` / `F1-03`
- **本 Phase 修改文件**：`_utils.py:5-12`（删）、`claim.py:5`、`leases.py:3`、`retry.py:3`、`restart.py:8`、`purge.py:8`、`events.py:6`（改 import + 调用）、`workflow_clean/service.py:118,124`
- **具体功能预期**：
  1. `_utils.py` 删除 `now_iso/add_seconds_iso`，仅保留 `new_id`。
  2. 内核 6 个文件全部从 `smind_common.time` 取时间，写入 `available_at`/`lease_expires_at`/`created_at` 等列的值与 SQL 视图比较一致。
  3. `workflow_clean/service.py` 两处 `CURRENT_TIMESTAMP` 改为 SSOT 函数值或 DDL DEFAULT，0 处残留。
- **对应测试台账项**：`FF-F1-T04` / `FF-F1-T05`（详见 §8）
- **收口标准**：`grep 内核 0 处指向 _utils 时间函数、service.py 0 处 CURRENT_TIMESTAMP；T04/T05 绿`
- **本 Phase 风险提醒**：`中；调用点多（claim/leases/retry/restart/purge/events 共 ~15 处），逐行核对漏改会留旧格式，靠 T04 跨 PY/SQL 比较兜底`

### 5.3 Phase 3 — 事务模式显式化（最高风险）

- **Phase 目标**：engine 转 autocommit，6 个多写 helper 全部显式 `BEGIN IMMEDIATE...COMMIT`，autocommit 下多写仍原子。
- **本 Phase 对应编号**：`F1-04`
- **本 Phase 修改文件**：`storage_sqlite/engine.py:13`、`leases.py:7-106`、`retry.py:7-168`、`restart.py:29-139`、`purge.py:29-150`（`claim.py:16` 复核）
- **具体功能预期**：
  1. engine `connect()` 设 `isolation_level=None`：裸 DML 后 `conn.in_transaction` 为 False，`BEGIN IMMEDIATE` 不再抛 `cannot start a transaction within a transaction`（part-cr-2 R2 实测复现的报错消失）。
  2. `succeed_claim`/`fail_claim`/`heartbeat_claim`/`reap_expired_claims`/`process_restart_requests`/`process_purge_requests` 全部以 `BEGIN IMMEDIATE` 开、`commit` 收，`except` 路径 `rollback() + raise`。
  3. **原子性边界**：在任一函数的中途（多条 UPDATE/INSERT 之间）注入异常，整组写回滚，DB 无半提交行（如 reap 的 task_claims/step_attempts/workflow_steps 三写要么全在要么全无）。
  4. **批写边界**：`reap`/`restart`/`purge` 的 for 循环整批包在一个 BEGIN IMMEDIATE 内（保持现有整批语义；拆批延后 FF-F3 R12），autocommit 下不显式包则循环内每条即提交。
  5. **跨库边界**：`process_purge_requests` 调 `VectorStore(vec_conn).delete_chunks` 写的是 vec 库，core 的事务不覆盖；注释标明跨库非原子，core 侧保证原子（vec 协调归 FF-F4/F3）。
  6. **失败/降级**：某 helper 包裹后 T07 仍失败，回退该单函数包裹、保留其余已通过的，记 §9 并 handoff。
- **对应测试台账项**：`FF-F1-T06` / `FF-F1-T07`（详见 §8）
- **收口标准**：`T06（裸 DML 后 BEGIN IMMEDIATE 不冲突）+ T07（6 个多写函数逐个中途失败整体回滚，0 残留）全绿，四元组齐全`
- **本 Phase 风险提醒**：`high；事务语义全局变更。与 FF-F3 F3-02 终态归属重构触碰同组函数——务必同窗口推进，避免两次包裹/两次回归。autocommit 下任何遗漏 BEGIN 的多写会静默丧失原子性（末尾 commit 成 no-op），T07 是唯一硬探针。`

---

## 6. 依赖的冻结设计决策（只读引用）

> 不在本节填写新 Q/A，只引 register 的 Q 编号 / design 结论。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[Q7] 全 phase 先红后绿铁律` | `docs/design/first-fixes/owner-gated-qna.md §4 Q7（FROZEN）` | F1-01~04 每项以"当前 HEAD FAIL、修复后 PASS"回归为退出证据（§8）；F7 前禁夹具掩盖 | `保持 draft；回退 qna register（本 AP 不改口）` |
| `时间 SSOT 格式 = ...SS.mmmZ（红线第 1 条）` | `initial-planning §4 红线第 1 条（frozen）` | F1-01/02/03 的目标格式由此固定，禁止 now_iso 畸形/CURRENT_TIMESTAMP/isoformat+00:00 三变体并存 | `回退 design；本 AP 不重新论证格式选择` |
| `事务原子性显式化（autocommit + 显式 BEGIN IMMEDIATE，红线第 3 条）` | `initial-planning §4 红线第 3 条 + §2.C F1-04 REFRAME` | F1-04 必须成对完成"engine autocommit + 多写 helper 包裹"，否则丧失原子性 | `若 autocommit 被推翻则 F1-04 整体回退 design` |
| `F1-04 与 F3 强耦合，同窗口推进` | `initial-planning §5 强耦合说明 + §10.A 时序` | Phase 3 与 FF-F3 F3-02 在同一改动窗口触碰同组 workflow_core 函数 | `若 F3 延后，F1-04 仍可独立完成包裹，但需在 F3 落地时复核边界` |

---

## 7. 内置 Reference-Anchor 锚区

> 本 AP 无独立 reference-anchor 文件；§7.1 是 part-cr-1/2/4 相关子集摘录 + 实际源码核对，为本 AP grounding 真源。

### 7.1 锚表（本计划工作落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `packages/common/src/smind_common/time.py:4-5` | `utc_now_iso() = isoformat()`（微秒+偏移，不符 SSOT，G-CR1-02） | `F1-01 改格式 + 加 add_seconds_iso` | `✅ 复用` | 直接改写 |
| A-2 | `packages/common/src/smind_common/__init__.py:4,6` | common 导出面 | `F1-01 导出 add_seconds_iso` | `✅ 复用` | 已建好，仅扩导出 |
| A-3 | `packages/workflow_core/src/workflow_core/_utils.py:5-12` | `now_iso`（畸形丢秒 `%M:%fZ`）/`add_seconds_iso`（G-CR1-01 根因） | `F1-02 删除` | `♻️ 重 substrate` | 删时间函数，保 `new_id`（行为正确，与 common.new_id 一致） |
| A-4 | `workflow_core/{claim.py:5,34,64; leases.py:3,14,21,39; retry.py:3,14,87; restart.py:8,35,49,71,100; purge.py:8,35,54,81,92,109; events.py:6,34,66}` | 内核全部 `now_iso/add_seconds_iso` 调用点 | `F1-02 改 import 指向 common` | `✅ 复用` | 逐行核对，~15 处 |
| A-5 | `packages/workflow_clean/src/workflow_clean/service.py:118,124` | 两处 `CURRENT_TIMESTAMP`（第三格式，G-CR4-R15） | `F1-03 清除` | `✅ 复用` | 改 SSOT 值/DDL DEFAULT |
| A-6 | `packages/storage_sqlite/src/storage_sqlite/engine.py:13` | `sqlite3.connect()` 未设 isolation_level（G-CR2-02） | `F1-04 设 isolation_level=None` | `✅ 复用` | 仅加一行；PRAGMA 段已建好别动 |
| A-7 | `workflow_core/claim.py:16,91-95` | `claim_next_step` 已有 `BEGIN IMMEDIATE` + commit/rollback | `F1-04 复核（参照范式）` | `✅ 复用` | 已是正确事务范式，其余 5 函数照此包 |
| A-8 | `workflow_core/leases.py:23,105` / `retry.py:64,167` / `restart.py:138` / `purge.py:149` | 5 个多写 helper 的"末尾裸 commit"（无 BEGIN，G-CR4-R6 多写非原子） | `F1-04 补 BEGIN IMMEDIATE + except rollback 包裹` | `♻️ 重 substrate` | autocommit 后裸 commit 成 no-op，必须显式包 |
| A-9 | `tests/unit/test_time_ssot.py` | 时间 SSOT unit 测试 | `F1-05 新建` | `🆕 净新` | 将新建（tests/unit 当前空，仅 .gitkeep） |
| A-10 | `tests/integration/p1_kernel_closure/test_time_tx_atomicity.py` | 跨 PY/SQL 比较 + 多写原子性集成测试 | `F1-05 新建` | `🆕 净新` | 复用 `tests/fixtures/sqlite_kernel.py:make_kernel_dbs` 建库 |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 用 `strftime("%Y-%m-%dT%H:%M:%fZ")` 直接格式化 Python datetime | Python `%f`=6 位微秒且格式串缺 `%S`，产出畸形丢秒串（part-cr-1 R1 实测 `...07:26:979490Z`）；必须显式 `%S` + `microsecond//1000` |
| ⛔2 | 用 `isoformat()`（带 `+00:00` 偏移、6 位微秒） | `+` 字符 ASCII 小于数字，字典序更不可预测；不符 SSOT（part-cr-1 R2） |
| ⛔3 | 在表达式里继续用 `CURRENT_TIMESTAMP` | SQLite `CURRENT_TIMESTAMP` 产出 `YYYY-MM-DD HH:MM:SS`（空格分隔、无 T/无毫秒/无 Z），是系统第三种格式（G-CR4-R15） |
| ⛔4 | autocommit 下多写函数不显式 `BEGIN IMMEDIATE` | 每条 DML 立即提交，末尾 `commit()` 成 no-op，中途失败已半提交无法回滚（part-cr-4 R6 / part-cr-2 R2） |
| ⛔5 | 在已开事务（裸 DML 后）调 `BEGIN IMMEDIATE`（非 autocommit 时） | 抛 `cannot start a transaction within a transaction`（part-cr-2 R2 实测）；F1-04 设 autocommit 正是为消除此冲突 |
| ⛔6 | 在 `claim_next_step` 的 `BEGIN IMMEDIATE` 事务内调带自带 commit 的写入器（如 graph.write_workflow_event） | 提前 commit 破坏原子性（part-cr-4 R9 注：当前无该路径，属潜在地雷，删除归 FF-F3） |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**（如有）：`无独立文件；本链 reference-anchor 由 docs/eval/first-code-review-plan/part-cr-1.md（R1/R2/R3）、part-cr-2.md（R2/R6）、part-cr-4.md（R1/R6/R9/R12）预完成，§7.1 是其与 F1 相关子集的摘录（含 file:line + 实测）。完整借鉴台账见 CR 报告真源。`
- **安全 / 信任边界类工作项的威胁模型锚**：`本 AP 工作项不属安全/信任边界类（时间格式与事务原子性属 correctness/D，非鉴权/路径遍历等信任边界）——路径遍历/认证威胁模型见 FF-F4 / FF-F6c。F1-04 的"原子性破坏"威胁向量（autocommit 半提交导致状态撕裂）落点为 §7.1 A-8 + §8.1 FF-F1-T07 攻击向量用例（中途注入异常验回滚），不留空。`

---

## 8. 测试台账

> Test-ID 形如 `FF-F1-T01`；每项含类型/层/来源/映射/PASS 四元组。贯彻"先红后绿"：每个 blocker 一条当前 HEAD FAIL、修复后 PASS 的回归。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `FF-F1-T01` | `utc_now_iso()/add_seconds_iso()` 可被 `fromisoformat` 解析（round-trip） | `短途` | `unit` | `🆕 新增 tests/unit/test_time_ssot.py::test_round_trip` | `F1-01 → 返回串合法可解析` | `commit {sha} + test_round_trip PASS + {YYYY-MM-DD HH:MM UTC}` |
| `FF-F1-T02` | 秒位正则 `^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z$` 匹配 | `短途` | `unit` | `🆕 新增 ::test_seconds_regex`（当前 HEAD 对 isoformat 输出必红） | `F1-01 → 格式 ...SS.mmmZ` | `commit + test_seconds_regex PASS + run-time` |
| `FF-F1-T03` | 跨 PY/SQL 比较一致：`utc_now_iso() <= SQLite strftime('%Y-%m-%dT%H:%M:%fZ','now')` 稍后调用为 True，长度一致 | `短途` | `集成` | `🆕 新增 tests/integration/p1_kernel_closure/test_time_tx_atomicity.py::test_py_sql_comparable`（HEAD 必红） | `F1-01 → 字典序可比` | `commit + test_py_sql_comparable PASS + run-time` |
| `FF-F1-T04` | 内核写入 `available_at`/`lease_expires_at` 后，`v_ready_steps`/`v_stale_claims` 时间比较正确（step 就绪 / 过期 claim 可被 reap） | `spike` | `集成/回归` | `🔱 fork tests/integration/p1_kernel_closure/test_kernel_flow.py::test_expired_claim_can_be_reclaimed + 加"内核走真实 now_iso 写入路径"断言` | `F1-02 → 内核单一来源、比较正确` | `commit + test_kernel_flow PASS + run-time` |
| `FF-F1-T05` | clean 写入的 `finished_at`/`updated_at` 与 SSOT 同格式可比；grep 0 处 CURRENT_TIMESTAMP | `短途` | `集成/契约` | `🆕 新增 ::test_clean_time_no_current_timestamp` | `F1-03 → 第三格式清除` | `commit + test_clean_time_no_current_timestamp PASS + run-time` |
| `FF-F1-T06` | autocommit 下裸 DML 后 `BEGIN IMMEDIATE` 不抛 `cannot start a transaction within a transaction` | `短途` | `集成/回归` | `🆕 新增 ::test_begin_immediate_after_bare_dml`（当前 HEAD 必红，复现 part-cr-2 R2） | `F1-04 → isolation_level=None 生效` | `commit + test_begin_immediate_after_bare_dml PASS + run-time` |
| `FF-F1-T07` | 6 个多写 helper（claim/succeed/fail/reap/restart/purge）中途注入异常后整体回滚，DB 0 残留行（原子性攻击向量用例） | `soak` | `集成/回归` | `🆕 新增 ::test_multiwrite_atomic_rollback`（参数化 6 函数；HEAD 在 autocommit 假设下必红） | `F1-04 → 多写原子，中途失败整批回滚` | `commit + test_multiwrite_atomic_rollback PASS + run-time` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/integration/p1_kernel_closure/test_kernel_flow.py::test_expired_claim_can_be_reclaimed` | `🔱 fork → FF-F1-T04` | `+ 断言内核走真实 now_iso 写入路径（去手写时间掩盖）；fixture 用真实 reap 比较` | `已存在，PASS（但当前靠 SQL 侧手写 strftime 过期，掩盖 _utils bug）` |
| `tests/fixtures/sqlite_kernel.py::make_kernel_dbs / seed_minimum_graph` | `♻️ 沿用` | `0 改动` | `已存在，纳入回归（T03/T04/T07 建库复用）` |
| `tests/smoke/test_shared_imports_smoke.py:10`（`assert "T" in utc_now_iso()`） | `♻️ 沿用（但标记假绿）` | `不在本 AP 改（归 FF-F7）；T02 真断言取代其覆盖职责` | `已存在，PASS（空洞断言，§8.5 记假绿）` |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·集成·契约·回归 | 开发中持续（T01/T02/T05/T06） |
| spike | journey 用例 | 集成·回归 | 每 Phase 收口（T04 Phase 2 收口） |
| soak | deterministic（6 函数 × 注入异常）| 集成·回归 | 退出硬闸（T07 Phase 3 收口） |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 `reap 接线后的并发双 worker 双重执行回归`（理由：接线属 F3-01、双重执行属 F3-02/F3-09）→ 交后继 `FF-F3-kernel-recovery.md`；**不在本 AP 假装覆盖**。
- 不覆盖 `process_purge_requests 跨 core/vec 双库的端到端原子性`（理由：vec 写不在 core 事务内，跨库协调归 FF-F4/F3）→ 本 AP 仅保证 core 侧原子并注释标明。
- 不覆盖 `已有库畸形时间串的归一迁移正确性`（理由：P 阶段无生产数据）→ 按需附迁移时补测。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带**四元组**（commit + 测试名 + run-time UTC）；计数 ≠ 价值。
- T02/T03/T06/T07 必须先在**当前 HEAD 复现红**（T02 对 isoformat 输出、T06 复现 part-cr-2 R2 报错、T07 在 autocommit+无 BEGIN 下半提交），修复后转绿——禁止只提交绿测。
- `degraded` 必带机器可读 `reason`；既有 `test_kernel_flow` 的"SQL 侧手写 strftime 过期"属夹具掩盖，T04 fork 时**去掩盖**走真实写入路径（[Q7] 纪律）。
- F1-04 原子性是"信任边界类"correctness——T07 必须含**攻击向量用例**（在 6 个多写函数的写与写之间注入异常验回滚），不得只测 happy-path。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| `F1-04 autocommit 全局事务语义变更` | 改 isolation_level=None 后所有多写若漏包 BEGIN 即丧失原子性，末尾 commit 成 no-op | `high` | 审计列全 6 函数逐个包裹 + 逐个跑 T07；与 FF-F3 同窗口避免重复触碰 |
| `F1-04 与 FF-F3 F3-02 触碰同组函数` | claim/succeed/fail/reap/restart/purge 同时被 F1（包事务）与 F3（终态归属重构）修改 | `medium` | 建议同改动窗口推进（initial-planning §5/§10.A）；若 F3 延后，F1-04 独立完成包裹，F3 落地时复核边界 |
| `内核 ~15 处时间调用点漏改` | F1-02 逐行改 import，漏一处即留旧畸形格式 | `medium` | grep 校验 0 处指向 _utils 时间函数 + T04 跨 PY/SQL 比较兜底 |
| `process_purge 跨库 vec 写非原子` | core BEGIN IMMEDIATE 不覆盖 vec_conn 写 | `low` | 注释标明跨库非原子，core 侧保证原子；端到端协调交 FF-F4/F3 |
| `已有库含畸形时间串` | 历史数据混格式，比较仍错 | `low` | P 阶段无生产数据；必要时附一次性归一迁移（§8.4 缺口） |

### 9.2 约束与前提

- **技术前提**：`Python sqlite3；SQLite %f = SS.SSS（毫秒），Python %f = 6 位微秒——格式化必须显式 %S + microsecond//1000 截断对齐 SQLite 截断行为。`
- **运行时前提**：`engine.connect() 的 PRAGMA 段（WAL/busy_timeout 等）保持不动；isolation_level=None 仅在 connect 内设置一行。`
- **组织协作前提**：`F1-04（Phase 3）与 FF-F3 执行者协调同窗口，避免对同组 workflow_core 函数双重改动/双重回归。`
- **上线 / 合并前提**：`§8 全部 T01~T07 四元组齐全 PASS；T07（多写原子性）为退出硬闸。`

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/refactor/database.md §9.2（确认 time SSOT 格式落点，只读对账，不改设计）`
- 需要同步更新的说明文档 / README：`无（F1 不引入新对外接口）`
- 需要同步更新的测试说明：`tests/unit/、tests/integration/p1_kernel_closure/ 新增用例纳入回归说明（由 FF-F7 统一整合 closure 定级）`

### 9.4 完成后的预期状态

1. `全系统时间只经 smind_common.time 一个函数生成，格式 YYYY-MM-DDTHH:MM:SS.mmmZ，与 SQLite strftime 严格可比；_utils 时间函数与 CURRENT_TIMESTAMP 三种变体全部消除。`
2. `内核写入的 available_at/lease_expires_at 与 v_ready_steps/v_stale_claims 比较正确——step 能就绪、过期 claim 能被 reap（为 FF-F3 reap 接线扫清根因）。`
3. `engine 用 autocommit，workflow_core 6 个多写 helper 全部显式 BEGIN IMMEDIATE...COMMIT，中途失败整体回滚，不再靠"末尾 commit"约定续命。`
4. `tests/unit 从空到有 time SSOT 单测；p1_kernel_closure 新增跨 PY/SQL 比较 + 多写原子性回归，每 blocker 一条先红后绿证据。`
5. `F1 keystone 收口，关键路径 F1 → F3 解锁；F1-04 与 F3-02 的同窗口边界已注明。`

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

> 收口 = §8 测试台账逐项 PASS，且每项映射回 §3 工作项收口目标。

### 10.1 收口硬闸

所有退出层测试项必须 **PASS 且四元组证据齐全**：

1. `时间 SSOT 格式正确且跨 PY/SQL 可比`（由 `FF-F1-T01`/`T02`/`T03` 证明）
2. `内核单一来源 + 第三格式清除，比较正确`（由 `FF-F1-T04`/`T05` 证明）
3. `autocommit 生效且 6 个多写 helper 中途失败整体回滚`（由 `FF-F1-T06`/`T07`（soak/退出硬闸）证明）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| `utc_now_iso 输出 ...SS.mmmZ 且可被 fromisoformat 解析` | `F1-01` | `FF-F1-T01`/`T02` | `commit + test + run-time` | `未观察（draft）` |
| `跨 PY/SQL 字典序可比` | `F1-01` | `FF-F1-T03` | `commit + test + run-time` | `未观察（draft）` |
| `内核全调用点单一来源、比较正确` | `F1-02` | `FF-F1-T04` | `commit + test + run-time` | `未观察（draft）` |
| `CURRENT_TIMESTAMP 清除` | `F1-03` | `FF-F1-T05` | `commit + test + run-time` | `未观察（draft）` |
| `autocommit 生效、BEGIN IMMEDIATE 不冲突` | `F1-04` | `FF-F1-T06` | `commit + test + run-time` | `未观察（draft）` |
| `6 个多写 helper 中途失败整体回滚` | `F1-04` | `FF-F1-T07` | `commit + test + run-time` | `未观察（draft）` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | `时间三格式收敛为单一 SSOT；engine autocommit + 6 个多写 helper 显式事务原子化` |
| 测试 | §8 测试台账全 PASS（退出硬闸 T07 四元组齐全）|
| 文档 | `database.md §9.2 时间格式对账确认；closure 定级交 FF-F7（本 AP 不预标 ✅）` |
| 风险收敛 | `F1-04 high 风险经逐函数 T07 回归收敛；与 FF-F3 同窗口边界已注明` |
| 可交付性 | `grep 0 处 _utils 时间函数 / 0 处 CURRENT_TIMESTAMP；F1 → F3 解锁` |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。本 AP 状态 `draft`，§10.2 全部为"未观察"；执行后按 closure 五态（`verified / observed-OK-at-closure / partial / 未观察 / deferred`）如实归类 + handoff，不 silent overclaim。F1-04 若某 helper 包裹回退（§5.3 失败路径），该项标 `partial` 并 handoff FF-F3。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态 = `draft`，本节省略。执行完成后改用 append 模板 `respond-execution-log` 回填；residual 交后继 charter，不回填本阶段。
