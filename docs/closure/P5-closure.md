# [P5 / 检索与查询面] Closure

> 阶段: `P5 — 检索与查询面`
> 范围: `P5 单阶段收口`
> Close-type: `full-close`
> 状态: `closed`
> 日期: `2026-05-30` · 作者: `Copilot`
> 关联 charter: `docs/refactor/todo-list.md`
> 关联 design: `docs/refactor/index.md`
> 关联 action-plan: `docs/action-plan/P5.md`
> 关联 evidence: `inline §2`
> 关联 review: `N/A`

---

## 0. 一句话 verdict

> P5 已完成并收口为 `full-close`：query embedding、vec candidate、core hydration 与 API/CLI search surface 已联通。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `VectorStore.search` + `SearchService` | ✅ | `working-tree` + `tests/integration/p5_search_surface` + `2026-05-30 UTC` |
| `/search` 与 `/search/debug` API | ✅ | `working-tree` + P5 集成断言 + `2026-05-30 UTC` |
| CLI search 命令 | ✅ | `working-tree` + `smind-cli search` 路径接线 + `2026-05-30 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P5 集成 | `python3 -m pytest tests/integration/p5_search_surface` | 通过 | search/debug |
| 联合回归 | `python3 -m pytest tests/integration tests/smoke` | `14 passed` | P0-P7 阶段回归 |
| 规范检查 | `python3 -m ruff check .` | 通过 | 全仓 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| retrieval gate | query 可返回命中结果 | 通过 | ✅ PASS |
| hydration gate | 命中可回填 core 上下文 | 通过 | ✅ PASS |
| debug gate | `/search/debug` 可解释命中结果 | 通过 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| rerank/hybrid retrieval | A | 不在本阶段范围 | 后续检索增强阶段 | Future |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅（本 closure 的 ✅ 均为 `verified`） |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠（当前为 working-tree 证据，未形成 commit SHA） |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |

