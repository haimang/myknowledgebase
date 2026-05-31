# [FF-F1 / 时间与事务基座] Closure

> 阶段: `first-fixes/FF-F1 — 时间与事务基座（Time & Transaction Bedrock）`
> 范围: `F1-01..F1-05（单 sub-phase，keystone）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-05-31` · 作者: `Claude Opus 4.8 (1M context)`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md`
> 关联 design: `docs/design/first-fixes/owner-gated-qna.md（[Q7] test-first 铁律）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F1-time-tx-base.md`
> 关联 evidence: `inline §2 + action-plan §11 执行日志`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-1.md / part-cr-2.md / part-cr-4.md`
> 关联 commit: `f46b86e`（fix(F1): 时间与事务基座 SSOT + 显式事务）

---

## 0. 一句话 verdict

> F1 keystone 收口：时间三格式收敛为单一 SSOT(`...SS.mmmZ`)、engine 转 autocommit、6 个 workflow_core 多写 helper 全部显式 `BEGIN IMMEDIATE...COMMIT/rollback`，T01–T07 先红后绿全绿（F1 子集 14 passed；全量 20 passed/1 xfail/1 pre-existing fail）；close-type = closed-with-explicit-deferrals（reap 接线/执行器契约/vec 跨库原子性按范围 handoff FF-F3/FF-F4）。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `process_purge_requests 的跨 DB vec 写不在 core 事务覆盖范围（仅 core 侧原子，已注释）→ FF-F4/F3 协调`
> 2. `tests/integration/p7_cutover/test_full_cutover_smoke 既有 failed（F1 前后一致，非本阶段引入）→ FF-F7 重建`

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------|
| F1-01 SSOT 时间(`utc_now_iso`/`add_seconds_iso` = `...SS.mmmZ`) | ✅ | `f46b86e` + `test_t01/t02/t03 PASSED` + `2026-05-31（子集 14 passed）`；实测 PY 与 SQLite 均 24 字符 `.mmmZ`（`2026-05-31T10:55:32.502Z` 双侧一致） |
| F1-02 删 `_utils` 时间函数 + 内核单一来源 | ✅ | `f46b86e` + 全量 `pytest tests/` 20 passed + `2026-05-31`；grep：内核 0 处引用 `_utils` 时间函数，`from ._utils import` 仅 `new_id`（claim/events/graph） |
| F1-03 清除 `CURRENT_TIMESTAMP` | ✅ | `f46b86e` + `test_t05_clean_finished_at_no_current_timestamp PASSED` + `2026-05-31`；grep：`packages/` 0 处 `CURRENT_TIMESTAMP` |
| F1-04 autocommit + 6 helper 显式事务 | ✅ | `f46b86e` + `test_t06 PASSED` + `test_t07[6 helper] PASSED` + `2026-05-31`；grep：`engine.py` `isolation_level = None` 在位 |
| F1-05 红→绿测试 T01–T07 | ✅ | `f46b86e` + `14 passed`(unit+integration 子集) ；先红：`git stash push -- packages` 还原 fix 后 `7 failed`，pop 后 14 passed |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 新测试套件 | `python3 -m pytest tests/unit/test_time_ssot.py tests/integration/p1_kernel_closure/ -v` | `14 passed`（T01-T03 + T04-T06 + T07×6 + 2 既有 reap-flow） | F1-01..05 |
| 全量回归 | `python3 -m pytest tests/` | `20 passed, 1 xfailed, 1 failed`；唯一 failed = `p7_cutover::test_full_cutover_smoke`，pre-F1 树同样 failed（见先红栏证伪 F1 致因） | 全仓 22 项 |
| 既有失败非 F1 引入 | `git stash push -- packages` → 跑 `p7_cutover` → `1 failed, 0 passed`（pre-F1 树）；`git stash pop` 恢复 | 确认 pre-existing，非 F1 回归 | scope |
| 时间格式同构 | `python3 -c "...strftime('%Y-%m-%dT%H:%M:%fZ','now')"` vs `utc_now_iso()` | 双方 `2026-05-31T10:55:32.502Z`（24 字符 `.mmmZ`） | F1-01 |
| 时间函数单一来源 | `grep -rn "now_iso\|add_seconds_iso" packages/workflow_core/src/ \| grep _utils` | 0 命中；仅 `from smind_common.time import ...` | F1-02 |
| 无 CURRENT_TIMESTAMP | `grep -rn "CURRENT_TIMESTAMP" packages/` | 0 命中 | F1-03 |
| autocommit | `grep -rn "isolation_level" packages/storage_sqlite/` | `engine.py:17 conn.isolation_level = None` | F1-04 |
| 先红后绿 | `git stash push -- packages` → 跑新测试 → `7 failed`；`git stash pop` → `14 passed` | T02-T07 pre-fix 红、post-fix 绿 | [Q7] |
| scope diff | `git diff --stat`（提交 f46b86e） | 12 文件，全部 F1 in-scope（10 源 + 2 测试） | scope guard |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 时间 SSOT 跨 PY/SQL 可比 | T01/T02/T03 绿 | 24 字符 `.mmmZ`，字典序可比 | ✅ PASS |
| 内核单一来源 + 第三格式清除 | T04/T05 绿 + grep 0 命中 | reap 走真实 now_iso 路径绿；clean finished_at `.mmmZ`；0 处 CURRENT_TIMESTAMP | ✅ PASS |
| autocommit + 6 helper 中途失败整体回滚 | T06 + T07(参数化 6 函数)绿 | 裸 DML 后 BEGIN IMMEDIATE 不抛错；6 helper 注入异常后 0 残留行 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| `reap_expired_claims worker 循环接线` | A (F1 OOS [O1]) | 比较正确 + 原子已就绪，未运行时接线 | FF-F3 F3-01 | F3 执行者 |
| `执行器终态归属重构 / 执行器契约` | A (F1 OOS [O2]) | F1 仅包裹现有多写事务，未改终态归属 | FF-F3 F3-02 | F3 执行者 |
| `graph.write_workflow_event 死代码删除 + events created_at 交 DDL DEFAULT` | A (F1 OOS [O3]) | 未触碰 | FF-F3 F3-07 | F3 执行者 |
| `retry 退避读 schema 列 / batch 拆单事务` | A (F1 OOS [O4]) | 未触碰；F1 保持整批单事务语义 | FF-F3 F3-06 / R12 | F3 执行者 |
| `process_purge 跨 DB vec 写原子性` | C (handoff) | core 侧原子；vec 侧不覆盖，已注释 | FF-F4 / F3 协调 | F4 执行者 |
| `p7_cutover::test_full_cutover_smoke 既有失败` | C (handoff) | pre-F1 树即失败，非 F1 引入 | FF-F7 测试有效性重建 | F7 执行者 |
| `已有库畸形时间串归一迁移` | B (主动 defer) | P 阶段无生产数据 | 首次出现含畸形时间串存量库时 | 后继 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ —— F1-01..05 全部 = `verified`（commit `f46b86e` + 命名测试 + run-time + grep 四元组；先红(7 failed)后绿(14 passed)成立） |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ✅ —— 见 §1/§2，证据为 `f46b86e` + 具名测试 + run-time + grep |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ —— 改动限于 common/{time,__init__}、workflow_core/{_utils,claim,leases,retry,restart,purge,events}、storage_sqlite/engine、workflow_clean/service、新增 2 个测试文件、action-plan §11、本 closure；未触 F3 终态归属/reap 接线 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ —— 见 §4（A×4 / C×2 / B×1，各有承接位置与责任方） |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A —— F1 无 owner-test/live gate；全部以本地 pytest 先红后绿验证 |

> 诚实附注：① 全量 22 项中唯一 `failed` 为 `p7_cutover::test_full_cutover_smoke`，已用 `git stash push -- packages` 在 pre-F1 树上复现同样 failed，确认 pre-existing、非 F1 引入（属 F7 测试重建范围）。② 测试环境原本未安装 workspace 包（仅残留 egg-info），本阶段以 `pip install -e packages/* apps/*` + `pip install pytest` 重建（owner 已授权调整测试环境），未改任何被测源的行为。③ 会话执行后段 bash stdout 显示层不稳定，最终结论以文件重定向 + 退出码 + git 持久态三者取证，下游可用 §2 命令原样复跑确认。
