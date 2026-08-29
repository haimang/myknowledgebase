# [AP-NH1 / Foundation contracts and proof baseline] Closure

> 阶段: `new-harvest/AP-NH1 — chosen-shape validation + proof baseline`
> 范围: `NH1-01..09 / NH1-T01..T07`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Codex`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH1-foundation-contracts-and-proof-baseline.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH1/`
> 关联 review: `inline §2–§3`

---

## 0. 一句话 verdict

> NH1 的可信 harness、机器分母、selected-output/S05/runtime 三个承重 spike 与下游接口全部验证通过，`stop-or-go=GO`；生产 CONTROL、migration、runtime supply 及 7 个 successor-owned 全仓红灯按 DAG 显式递交。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. selected-output 与 actual-S05 仍为 `SPIKE-ONLY`；AP-NH2/NH3 必须生产化，不能让 spike 表/模块成为第二 SSOT。
> 2. runtime smoke 证明形态可行，不是 AP-NH6 production readiness/SBOM 或 AP-NH7 live-to-query。
> 3. 全仓 7 个既存失败已分别 handoff NH5/NH6/NH7/NH8；不影响 NH1 hard gate，但必须在其 owner AP 收口。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH1-01` denominator | ✅ closed / verified | `1cdc066` + `test_nh1_denominator_inventory.py` 3 PASS + `T-R-NH-01/03` + `2026-08-29T17:12:10Z` |
| `NH1-02` Port recovery | ✅ closed / verified | `1cdc066` + `NH1-T02` named nodes PASS + Q26 + UTC |
| `NH1-03` namespace retrieval | ✅ closed / verified | `1cdc066` + omission 422 / Layer-A hit 200 + `T-R-NH-16` + UTC |
| `NH1-04` CONTROL spike | ✅ closed / verified | `1cdc066` + zero/one/double/missing/cycle PASS + Q11/Q18 + UTC |
| `NH1-05` actual-S05 spike | ✅ closed / verified | `1cdc066` + states/UoW/replay/conflict PASS + Q10/Q20 + UTC |
| `NH1-06` runtime smoke | ✅ closed / verified | `1cdc066` + `87eeadf` + `5 PASS ×3` + Q13/Q19/Q23 + UTC |
| `NH1-07` legal matrices | ✅ closed / verified | `1cdc066` + manifest digest `f7199ee…d235c3` + Q17/Q25 + UTC |
| `NH1-08` prompt inventory | ✅ closed / verified | `1cdc066` + 3 distinct SHA-256/readers + M-NH-07 + UTC |
| `NH1-09` foundation pack | ✅ closed / verified | evidence manifest/interfaces + `stop-or-go=GO` + Q26 + UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| L1 | `pytest test_nh1_denominator_inventory.py test_nh1_legal_matrix.py test_nh1_selected_output_control.py` | `11 passed` | T01/T04/T07 |
| L2 | AP §8.3 named Port/namespace/merge/S05 command | `17 passed` | T02–T05 |
| L3 | `pytest tests/e2e/test_nh1_runtime_smoke.py`，连续三轮 | `5 passed ×3` | T06 |
| substrate regression | workflow/compat + five clean/provider files | `36 passed` | no regression |
| static review | ruff + diff check + forbidden-source scans | PASS | scope/anti-fake-green |
| full suite diagnostic | `pytest -q` | `595 passed / 7 successor-owned failed / 602 collected` | campaign baseline |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| Harness | Port/UoW；namespace omission 422；real key hit；无 running-as-pass | named L2 nodes PASS；源码 scan 0 bypass | ✅ PASS |
| CONTROL | exactly-one；不改 unique binding；单 tail；零/双 fail | L1/L2 9 nodes PASS | ✅ PASS |
| S05 | legacy/unsealed/sealed；same UoW；replay/conflict | L2 5 nodes PASS | ✅ PASS |
| Runtime | real PDF/DOM/PDF-print；non-root；encrypted fail；三轮 | L3 `5 ×3` PASS | ✅ PASS |
| Interface pack | NH2–NH6 versioned input/output/error | 7 JSON interfaces + valid manifest | ✅ PASS |
| Stop-or-go | T01..T07 全 PASS 才 GO | all frozen minimum layers met | ✅ GO |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Production selected-output CONTROL/kind family | C | spike PASS | `AP-NH2` immediately after GO | NH2 |
| Production history + actual-S05 migration/propagation | C | spike PASS | `AP-NH3` after NH2 | NH3 |
| Upload and semantic contracts | C | cited only | `AP-NH4` / `AP-NH5` | NH4/NH5 |
| Production parser/browser/multimodal readiness/SBOM | C | feasibility PASS | `AP-NH6` after NH3 | NH6 |
| 10+3 live-to-retrieval | C | not claimed | `AP-NH7` join | NH7 |
| Four namespace/rebuild lifecycle failures | C | full-suite red | AP-NH8 named tests | NH8 |
| source running + realestate newline failures | C | full-suite red | NH5/NH6/NH7 owner phases | NH5/NH6/NH7 |
| Raw GET, fifth kind, existing-object upgrade, experiment launch | A | OOS | only a future frozen owner reopen | owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ 全部为 `verified`；handoff 均为 `deferred` |
| ✅ 证据为四元组 | ✅ implementation commit + named test/query + Truth/Q + UTC |
| scope diff 守卫 | ✅ 生产 builtin/`001_initial.sql` 未改；spike 文件显式标记 |
| deferred 已三分类 | ✅ A/C；无隐藏 B |
| owner-test 未复测 | N/A；无 owner-test 宣称 |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| `stop-or-go.md=GO` | ✅ | T01..T07 all PASS |
| NH2 selected-output interface v1 | ✅ | optional ports / durable projection / errors frozen |
| Denominator + 16 compat inventory | ✅ | machine-readable JSON |
| No production graph/DDL contamination | ✅ | source/diff scan |

**下阶段 kickoff checklist**：

- [x] 引用本 closure 和 `interfaces/nh2-*.json`
- [ ] AP-NH2 重新读取 RA01/RA03 与 frozen Q11/Q12/Q18/Q22
- [ ] 生产实现不得复用 scatter wait、不得复制 tail、不得删除 old pins

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| caller 无 `workflow_key` / 无 `action_branch` | ✅ 保持 | NH1 未改 public contracts；matrix scan |
| one input one binding / graph acyclic | ✅ 保持 | T04 duplicate/cycle negatives |
| legacy alias ≠ actual | ✅ 保持 | T05 domain-hex negative |
| L1/L2/L3/L4 不互换 | ✅ 保持 | evidence 按层分列；full-suite residual 未涂绿 |
| 503/skip/mock/Task success 不作 DoD | ✅ 保持 | T03/T06 assertions + stop-or-go |
