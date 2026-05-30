# [P7 / 收敛与替换] Closure

> 阶段: `P7 — 收敛与替换`
> 范围: `P7 单阶段收口`
> Close-type: `full-close`
> 状态: `closed`
> 日期: `2026-05-30` · 作者: `Copilot`
> 关联 charter: `docs/refactor/todo-list.md`
> 关联 design: `docs/refactor/index.md`
> 关联 action-plan: `docs/action-plan/P7.md`
> 关联 evidence: `inline §2`
> 关联 review: `N/A`

---

## 0. 一句话 verdict

> P7 已完成并收口为 `full-close`：legacy freeze enforcement 与 cutover guard 已落地，并纳入自动化回归。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| legacy freeze 守卫脚本 | ✅ | `working-tree` + `tools/scripts/check_legacy_freeze.sh` + `2026-05-30 UTC` |
| P7 cutover guard 回归 | ✅ | `working-tree` + `tests/integration/p7_cutover` + `2026-05-30 UTC` |
| 跨阶段总回归 | ✅ | `working-tree` + `pytest tests/integration tests/smoke` + `2026-05-30 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P7 集成 | `python3 -m pytest tests/integration/p7_cutover` | 通过 | legacy freeze enforcement |
| 跨阶段总回归 | `python3 -m pytest tests/integration tests/smoke` | `14 passed` | P0-P7 |
| 规范检查 | `python3 -m ruff check .` | 通过 | 全仓 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| freeze gate | 新代码路径不允许引入 legacy-family 运行时耦合 | 通过 | ✅ PASS |
| cutover gate | enforcement 已纳入自动测试 | 通过 | ✅ PASS |
| final regression gate | P0-P7 联合测试通过 | 通过 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 更细粒度 parity matrix 自动校验 | C | 后续可增强 | post-cutover 质量门禁迭代 | Future |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅（本 closure 的 ✅ 均为 `verified`） |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠（当前为 working-tree 证据，未形成 commit SHA） |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |

