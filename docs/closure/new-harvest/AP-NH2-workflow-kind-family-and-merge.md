# [AP-NH2 / Workflow kind family and merge] Closure

> 阶段: `new-harvest/AP-NH2 — kind family + selected-output + compat`
> 范围: `NH2-01..08 / NH2-T01..T07`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Codex`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH2-workflow-kind-family-and-merge.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH2/`
> 关联 review: `inline §2–§3`

---

## 0. 一句话 verdict

> NH2 已把 selected-output、typed fact guards、三张 kind graph、kind-only resolver 与 old-pin compat 生产化，T01–T07 全绿且旧 digest 零漂移；typed history/actual seal、live adapters 与有界 retirement 按 DAG 显式递交。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. RepresentationFact/AcquireDecodeHistory 尚无生产行；guard 接口已冻结但由 NH3 提供事实。
> 2. actual S05 seal 尚未接 selected-output；NH3 必须在同 Outcome UoW 完成。
> 3. kind edges 只证明可达声明；真实 browser/OCR/model 与 L4 query 仍分别归 NH6/NH7。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH2-01` CONTROL | ✅ closed / verified | `81f1271` + T02 6 PASS + Q11/T-O-391 + `2026-08-29T18:53:27Z` |
| `NH2-02` guards | ✅ closed / verified | `81f1271` + T03 8 PASS + Q12/Q22 + UTC |
| `NH2-03/04` graphs | ✅ closed / verified | `81f1271` + T04/T05 + tail digest `e36b5b…af13` + T-O-387/388 + UTC |
| `NH2-05/06` resolver/fence | ✅ closed / verified | `81f1271` + kind resolver / undeclared 409 PASS + T-O-379/384 + UTC |
| `NH2-07` compat | ✅ closed / verified | `81f1271` + old sequence PASS + digest diff 0/16 + Q18 + UTC |
| `NH2-08` redlines | ✅ closed / verified | `81f1271` + five architecture nodes PASS + T-O-377/398 + UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| Frozen NH2 suite | AP §8 T01–T07 command | `52 passed` | L1/L2/compat |
| Default-root regressions | single/scatter/identity/inline/local-image/generation nodes | `10 passed` | actual tail integration |
| Compatibility | `old_pin_sequence...`; digest inventory | sequence exact; `0/16` drift | Capstone A owner half |
| Redlines | `security/redline-scan.txt` | all PASS | caller/DSL/JOIN/tail/control |
| Full suite | `pytest -q` | `635 passed / 6 successor-owned failed / 641 collected` | repository diagnostic |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| kind-only | four kinds resolve unique identities; mode/media stable | resolver/UoW tests | ✅ PASS |
| one shared tail | three subgraph digests equal; one source | cardinality 1 | ✅ PASS |
| deterministic route | missing/unknown false; absent browser; cycles rejected | T03/T04 | ✅ PASS |
| compat | old pin completes unchanged; unknown digest zero process | T06 | ✅ PASS |
| redlines | no caller key/action_branch/free expression/JOIN/scatter alias | T07 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Typed representation/history rows | C | interface only | AP-NH3 Phase 1 | NH3 |
| Actual S05 seal + propagation | C | selected row available | AP-NH3 Phase 4 | NH3 |
| Real local runtime / 10+3 query | C | edges declared | AP-NH6 / AP-NH7 | NH6/NH7 |
| Old-key retirement | C | telemetry exists, still enabled | AP-NH8 after in-flight=0 | NH8 |
| Namespace/exact-clean/realestate six failures | C | full-suite red | NH5/NH8 owner phases | NH5/NH8 |
| General JOIN/DSL/loader | A | OOS/prohibited | future owner reopen only | owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ `verified`; successor work=`deferred` |
| ✅ 四元组证据 | ✅ commit + named tests/query + Truth + UTC |
| scope diff 守卫 | ✅ no actual-S05/history/runtime supply implementation |
| deferred 分类 | ✅ A/C，均有 owner/trigger |
| owner-test | N/A |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| NH1 GO | ✅ | upstream closure fixed |
| selected-output durable row/version | ✅ | M-NH-03 migrated |
| typed fact-read interface | ✅ | missing facts fail closed |
| three kind graph identities | ✅ | shared tail digest fixed |
| old pins executable | ✅ | sequence exact / metric present |

**下阶段 kickoff checklist**：

- [x] 引用本 closure 与 M-NH-03/M-NH-04 evidence
- [ ] NH3 重读 RA02/RA03/RA08 与 Q10/Q12/Q20–22/Q27
- [ ] history append 与 Process Outcome 同 UoW；禁止 output JSON 双 SSOT

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| one input one binding | ✅ 保持 | compiler negative + DDL unchanged |
| graph acyclic / distinct reacquire steps | ✅ 保持 | T04 |
| source kind is sole public graph selector | ✅ 保持 | T01/T05 |
| old compiled pin exact | ✅ 保持 | diff 0/16 + process sequence |
| scatter fan-in not XOR | ✅ 保持 | implementation/source scan |
| no free expression / action_branch | ✅ 保持 | T07 |
