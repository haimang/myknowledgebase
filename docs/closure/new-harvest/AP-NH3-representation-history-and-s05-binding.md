# [AP-NH3 / Representation history and S05 binding] Closure

> 阶段: `new-harvest/AP-NH3 — representation history + honest representation + actual S05`
> 范围: `NH3-01..10 / NH3-T01..T08`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Codex`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH3-representation-history-and-s05-binding.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH3/`
> 关联 review: `inline §2–§3`

---

## 0. 一句话 verdict

> NH3 已把 typed fact/history、诚实表示、声明式 reacquire、policy/actual 分账、同 UoW sealed-once CAS 与 exact replay 法律生产化，T01–T08 全绿；真实 browser/PDF/OCR 供给及 rebuild/metadata 旁路仍按冻结 DAG 递交 NH6/NH8。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `BrowserPrintResult` 仅由 L2 测试 port 证明合同，default-root live Chromium/PDF parser/OCR 供给归 AP-NH6。
> 2. rebuild/metadata 已证明不写新 actual，但 exact-clean 的图内 bypass 尚未落地，归 AP-NH8。
> 3. 旧物理 `s05_binding_digest` 仍作 compatibility policy alias；有界物理 retire 需 NH8 compat 证明。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH3-01/02` fact/history | ✅ closed / verified | `b008702` + NH3-T01 PASS + Q12/T-O-392 + `2026-08-29T19:56:38Z` |
| `NH3-03/04/05` honest representation | ✅ closed / verified | `b008702` + NH3-T02–T04 PASS + Q23/T-O-378/403 + UTC |
| `NH3-06` declared reacquire | ✅ closed / verified | `b008702` + NH3-T05 PASS + path digest evidence + Q22/T-O-388/402 + UTC |
| `NH3-07` policy/actual split | ✅ closed / verified | `b008702` + NH3-T06 PASS + three-state query/no-backfill scan + Q10/T-O-390 + UTC |
| `NH3-08/09` seal/propagation | ✅ closed / verified | `b008702` + NH3-T07 PASS + W-SEL/W-SEAL and cross-table query + Q20/T-O-400 + UTC |
| `NH3-10` replay law | ✅ closed / verified | `b008702` + NH3-T08 PASS + exact generation matrix + Q21/Q27/T-O-401/407 + UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| Frozen NH3 suite | `tests.txt` 的 T01–T08 命令 | `36 passed` | L1/L2/F |
| Outcome UoW | `test_nh3_fact_history_uow.py` | success/rollback/repeat PASS | fact + Process CAS |
| Path determinism | `queries/representation-path.json` | same exact; branch distinct | finite reacquire |
| Actual propagation | `queries/actual-propagation.json` | root/candidate/snapshot/gate/2 children one actual | actual-only chain |
| Fault/security | `security/redline-scan.txt` | W-SEL/W-SEAL/reseal/scans PASS | R-F02/R-F03/R-F12 |
| Static review | `ruff check`; `git diff --check` | PASS | changed production/tests |
| Full repository diagnostic | `pytest -q --tb=short` | `672 passed / 6 successor-owned failed / 678 collected` | non-NH3 regressions |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| durable facts | one row/step; same UoW; rollback zero; repeat 409 | T01 | ✅ PASS |
| finite path | declared only; unknown false; stable/different digest | T05 + query | ✅ PASS |
| actual truth | legacy/unsealed/sealed distinct; no backfill | T06 + migration trigger | ✅ PASS |
| single-CAS | route + seal + clean eligibility same commit; hostile reseal 409 | T07 | ✅ PASS |
| propagation | Command/Candidate/Snapshot/Gate/child use actual or explicit unsealed | T07 cross-table | ✅ PASS |
| replay | Process retry stable; full_task exact; rebuild no actual; upgrade absent | T08 | ✅ PASS |
| honesty | ZIP/OPC/opaque; PDF four-state; real print bytes/profile | T02–T04 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Live browser print/PDF parser/OCR | C | contracts + typed failure only | AP-NH6 runtime supply | NH6 |
| 10+3 activation and admitted-clean vertical | C | substrate ready | AP-NH7 after NH4–NH6 | NH7 |
| Rebuild/metadata exact-clean bypass | C | no-new-actual law verified; current test still red | AP-NH8 | NH8 |
| Legacy physical alias retirement | C | zero actual readers; writes retained for compatibility | AP-NH8 in-flight/compat gate | NH8 |
| Namespace and realestate repository failures | C | six default-root diagnostics red | AP-NH5/AP-NH8 owner work | NH5/NH8 |
| Live proof classification | A | no L3/L4 claim in NH3 | NH6/NH7 evidence | NH6/NH7 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ `verified`; successor obligations=`deferred` |
| ✅ 证据为四元组 | ✅ implementation commit + named test/query + Truth + UTC |
| scope diff 守卫 | ✅ two migrations, runtime/contracts, focused tests and timing fence only |
| deferred 已三分类 | ✅ A/C，均有 owner/trigger |
| owner-test | N/A；T04 明确为 L2，未冒充 live |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| NH3-T01..T08 | ✅ | 36/36 PASS |
| M-NH-01 actual schema | ✅ | migration 020, no backfill, sealed triggers |
| M-NH-02 history schema | ✅ | migration 019, Outcome UoW append |
| honest representation contracts | ✅ | BrowserPrintResult/PDF observation/OPC |
| actual propagation | ✅ | Command through scatter children |
| full_task exact | ✅ | complete sealed selection copied |

**下阶段 kickoff checklist**：

- [x] 引用本 closure、M-NH-01/M-NH-02 与 query evidence
- [ ] NH4 严格按 DAG 开工，不吸收 NH6 runtime supply
- [ ] NH6 以真实 profile/version 实现 BrowserPrintResult，不把 L2 提升为 live
- [ ] NH8 消费 rebuild no-new-actual 法律并关闭当前 exact-clean failure

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| Q12 fact/history 为唯一 route authority | ✅ 保持 | reader tx query + T01/T05 |
| domain policy 不冒充 actual | ✅ 保持 | scan zero + three-state query |
| actual sealed once | ✅ 保持 | CAS WHERE fence + triggers + hostile reseal |
| graph-only reacquire | ✅ 保持 | undeclared 409; unknown no browser |
| no decode OCR theft | ✅ 保持 | source scan + four-state matrix |
| no upgrade intent/scope | ✅ 保持 | T08 scan |
| no L3 overclaim | ✅ 保持 | T04 evidence explicitly L2 |
