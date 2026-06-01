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
| 跨阶段总回归 | `python3 -m pytest tests/integration tests/smoke` | `14 passed`（陈旧·见末尾 F7-05 附记，first-fixes 后真实 192 passed） | P0-P7 |
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



---

## F7-05 据实更正与重定级（2026-06-01，first-fixes 收口后）

> 由 FF-F7-05 撤销基于陈旧/复制计数 `14 passed` 的判定（part-cr-8 R5：计数 ≠ 价值）。

- **计数更正**：原「联合回归 `14 passed`」为陈旧/跨 closure 复制的计数（part-cr-8 实测当时实为 20 个测试函数）。first-fixes 阶段（F1–F7）重建测试有效性后，全量 `python3 -m pytest tests/` 现为 **192 passed（exit 0）**，含真实语义/安全/时间/向量真实性/重放幂等断言。原 `14 passed` 作废。
- **gate 据真实断言重定级（closure 五态）**：
  - clean/ingestion gate → **verified**：F6a 已把 clean 去桩为真实 htmlCrawl/chinatax（`test_clean_contract_and_dispatch` / `test_html_crawl_extract` 等），原桩恒等断言已 fork 为语义属性断言。
  - retrieval/vector gate → **degraded（reason=[Q1] vec0 degraded）**：检索为本地确定性 1536 维 embedding + 暴力 cosine（F5），真实 vec0 移出本轮；向量真实性由 `tests/integration/p4_rag_pipeline/test_f5_vector_authenticity` + capstone G 步证明（相关 chunk 排第一 + 分差），非"返回非空"。
  - cutover/regression gate → **verified（在 degraded 范围内）**：first-fixes 192 passed + capstone A–J（PDF/浏览器步 xfail-degraded）。
- **原 ✅ 撤销说明**：本 closure 原基于陈旧计数的 ✅ PASS 视为无效证据，已据 first-fixes 真实断言四元组重新归类如上；degraded 项显式带 reason，不 silent overclaim。
