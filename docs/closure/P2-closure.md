# [P2 / 控制面与 ingestion] Closure

> 阶段: `P2 — 控制面与 ingestion`
> 范围: `P2 单阶段收口`
> Close-type: `full-close`
> 状态: `closed`
> 日期: `2026-05-30` · 作者: `Copilot`
> 关联 charter: `docs/refactor/todo-list.md`
> 关联 design: `docs/refactor/index.md`
> 关联 action-plan: `docs/action-plan/P2.md`
> 关联 evidence: `inline §2`
> 关联 review: `N/A`

---

## 0. 一句话 verdict

> P2 已完成并收口为 `full-close`：auth/team/workflow-config、file/url/api/static ingestion、workflow-start bridge 与 management 读面已在新 API 与 packages 中打通并通过集成回归。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| auth/session/team 控制面 | ✅ | `working-tree` + `test_ingestion_management.py` + `2026-05-30 15:29 UTC` |
| local object store + upload 基线 | ✅ | `working-tree` + file/static initiate-confirm 集成断言 + `2026-05-30 15:29 UTC` |
| file/url/api -> source/document/run/step 桥接 | ✅ | `working-tree` + ingestion 集成断言 + `2026-05-30 15:29 UTC` |
| workflow/document/static-file management 读面 | ✅ | `working-tree` + `/management/*` 集成断言 + `2026-05-30 15:29 UTC` |
| P2 + P1 + P0 回归与 lint | ✅ | `working-tree` + `pytest ...` / `ruff check .` + `2026-05-30 15:29 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P2 控制面集成 | `python3 -m pytest tests/integration/p2_control_plane` | 通过 | auth/team/ingestion/management |
| 联合回归 | `python3 -m pytest tests/integration/p2_control_plane tests/integration/p1_kernel_closure tests/smoke` | `9 passed` | P2 + P1 + P0 |
| 规范检查 | `python3 -m ruff check .` | 通过 | 全仓新增/修改代码 |
| workflow bridge | file/url/api submit 后 workflow list 有新增 run | 通过 | run/step 可见性 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| auth/team gate | register/login/session + team bootstrap/select 可用 | 集成测试通过 | ✅ PASS |
| ingestion gate | file/url/api 三类入口可落 source/document/workflow | 集成测试通过 | ✅ PASS |
| static gate | static initiate-confirm 可落 `static_files` 且不自动跑 run | 集成测试通过 | ✅ PASS |
| management gate | workflow/document/static file list/detail 可用 | 集成测试通过 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| clean pipeline planner/finalizer/universal/dedicated | C | 待实现 | P3 code/review todo | P3 |
| rag pipeline 闭环 | C | 待实现 | P4 code/review todo | P4 |
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

