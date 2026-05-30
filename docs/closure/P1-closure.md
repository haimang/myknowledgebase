# [P1 / 数据库与状态内核] Closure

> 阶段: `P1 — 数据库与状态内核`
> 范围: `P1 单阶段收口`
> Close-type: `full-close`
> 状态: `closed`
> 日期: `2026-05-30` · 作者: `Copilot`
> 关联 charter: `docs/refactor/todo-list.md`
> 关联 design: `docs/refactor/database.md`
> 关联 action-plan: `docs/action-plan/P1.md`
> 关联 evidence: `inline §2`
> 关联 review: `N/A`

---

## 0. 一句话 verdict

> P1 已完成并收口为 `full-close`：`core.db/vec.db` migration、repository 基线、claim/lease/retry/reaper 内核与 request 持久化闭环已经可运行并有自动化测试覆盖。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `core.db` engine + migration runner | ✅ | `working-tree` + `tests/fixtures/sqlite_kernel.py` + `2026-05-30 15:29 UTC` |
| `vec.db` schema + VectorStore 写删 | ✅ | `working-tree` + `test_requests_and_vec.py::test_vec_store_upsert_and_delete` + `2026-05-30 15:29 UTC` |
| workflow kernel（claim/heartbeat/retry/reaper） | ✅ | `working-tree` + `test_kernel_flow.py` + `2026-05-30 15:29 UTC` |
| restart/purge request 持久化 | ✅ | `working-tree` + `test_requests_and_vec.py::test_restart_and_purge_requests_persist` + `2026-05-30 15:29 UTC` |
| P1 integration + lint 收口 | ✅ | `working-tree` + `pytest tests/integration/p1_kernel_closure tests/smoke` / `ruff check .` + `2026-05-30 15:29 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P1 集成回归 | `python3 -m pytest tests/integration/p1_kernel_closure tests/smoke` | `8 passed` | kernel/request/vec + P0 smoke |
| 代码规范 | `python3 -m ruff check .` | 通过 | 全量新增与修改代码 |
| migration 入口 | `apply_core_migrations()` + `apply_vec_schema()` | 通过 | core/vec schema bootstrap |
| ready-step/claim 语义 | `claim_next_step()` + `reap_expired_claims()` 集成测试 | 通过 | claim 唯一性与过期回收 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| schema gate | `core.sql/vec.sql` 可从空库应用 | 通过 fixture 初始化与 migration | ✅ PASS |
| kernel gate | claim/heartbeat/success/fail/retry/reclaim 可跑通 | `test_kernel_flow.py` 全通过 | ✅ PASS |
| request gate | restart/purge request 可持久化并进入 backlog view | `test_requests_and_vec.py` 通过 | ✅ PASS |
| vector gate | 最小 upsert/delete 路径可用 | vec store integration 通过 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| auth/team/ingestion 北向控制面 | C | 待实现 | P2 code/review todo | P2 |
| clean planner/universal/dedicated/finalizer | C | 待实现 | P3 code/review todo | P3 |
| rag pipeline（structurizer/constructor/vectorizer） | C | 待实现 | P4 code/review todo | P4 |
| search/query 面 | C | 待实现 | P5 code/review todo | P5 |
| ops/recovery/cutover | C | 待实现 | P6/P7 code/review todo | P6-P7 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅（本 closure 的 ✅ 均为 `verified`） |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠（当前为 working-tree 证据，未形成 commit SHA） |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |

