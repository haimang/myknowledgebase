# [AP-NH5 / Semantic ledger and retrieval facets] Closure

> 阶段: `new-harvest/AP-NH5 — strict semantic authority + S06 overlay + SQL facets`
> 范围: `NH5-01..08 / NH5-T01..T08-A`; `T08-B` explicit red handoff
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Codex`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH5-semantic-ledger-and-retrieval-facets.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH5/`
> 关联 review: `inline §2–§3`

---

## 0. 一句话 verdict

> NH5 已交付四 kind strict 六元组、provenance、S04-owned S06 context、v2 channel 分名、候选 SQL facet 与 metadata T08-A 切代，39 个 hard-gate 节点全绿；metadata 仍生成 3 个 acquire/decode/clean Process 被如实保留为 NH8-T03 红灯。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. T08-B `forbidden_process_count=3`；NH8 必须用 intent guard 令其归零，不得 xfail 或改期待值。
> 2. index/reactivate 四个旧 e2e 仍缺 namespace；同属 NH8 测试/兼容收口。
> 3. 本 AP 证明 facet 轴，不替代 NH7 的 10+3 live strategy matrix。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH5-01` strict input | ✅ closed / verified | `76f233b` + T01/T02 PASS + Q14/T-O-394 + `2026-08-29T21:38:33Z` |
| `NH5-02/03` six-tuple/UoW | ✅ closed / verified | `76f233b` + four-kind/UoW queries + T-O-389/394 + UTC |
| `NH5-04` S06 overlay | ✅ closed / verified | `76f233b` + overlay diff/g0 PASS + T-O-386/389 + UTC |
| `NH5-05` channel split | ✅ closed / verified | `76f233b` + v1/v2 L1/L3 PASS + Q15/T-O-395 + UTC |
| `NH5-06/07` facets/SQL | ✅ closed / verified | `76f233b` + T07 L4 + SQL shape + T-O-395 + UTC |
| `NH5-08` T08-A | ✅ closed / verified | `76f233b` + exact clean object + new revision/context/facet/search + Q27 + UTC |
| `NH5-08.d` T08-B | ⏸ deferred / observed red | `76f233b` + Port query count `3` + T-O-407 + UTC → NH8-T03 |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| NH5 hard-gate suite | `tests.txt` command | `39 passed` | L1/L2/L3/L4 |
| Four-kind authority | `six-tuple-four-kinds.json` | each kind=6 keys; no stub | S04/UoW |
| Overlay | `overlay-diff.json` | S04 diff empty; g0=clean | S06 |
| Channel compatibility | `channel-split.json` | v2 dual; v1 narrow; invalid 422 | public L3 |
| Facet query | `facet-sql.json` | six keys; EXISTS before LIMIT; L4 exclude | S08/S10 |
| Metadata | `metadata-lineage.json` | new revision, same clean object, new S06/facet | T08-A |
| Full repository diagnostic | `pytest -q --tb=short` | `748 passed / 5 successor-owned failed / 753 collected` | repository regression |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| semantic authority | generic nonunknown; API mapper; four kind six rows | T01–T03 | ✅ PASS |
| semantic atomicity | scalar/blob/digest/provenance coherent | UoW conflict tests | ✅ PASS |
| S06/g0 split | context=S04; g0=clean; model realm discarded | T04 | ✅ PASS |
| channel contract | v2 axes coexist; v1 channel narrow; no guessing | T05/T06 | ✅ PASS |
| SQL facets | six facets, unknown/namespace fail, candidate-level exclude | T07 L4 | ✅ PASS |
| metadata T08-A | clean identity exact, semantics/S06/facets/search cut over | T08-A | ✅ PASS |
| metadata T08-B | acquire/decode/clean Process count=0 | observed `3` | ⏸ RED HANDOFF, not NH5 hard gate |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Metadata exact-clean process absence | C | red count=3 | AP-NH8 `NH8-03/NH8-T03` | NH8 |
| Index/reactivate namespace test repair | C | four repository failures | AP-NH8 | NH8 |
| 10+3 vertical facet consumption | C | facet substrate ready | AP-NH7 after NH6 | NH7 |
| Historical stub semantics | C | no unknown backfill; not realm-matchable | explicit metadata cutover | NH8/operator |
| External vector engine | A | OOS | new owner decision | owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ hard gates=`verified`; T08-B=`deferred/observed red` |
| ✅ 证据为四元组 | ✅ implementation commit + named query/test + Truth + UTC |
| scope diff 守卫 | ✅ semantic/retrieval/compiler changes plus mechanical valid-fixture upgrades |
| deferred 已三分类 | ✅ A/C with owner/trigger |
| owner-test | N/A；T08-B 未标 PASS、未 xfail |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| four-kind six-tuple | ✅ | caller/mapper/system provenance |
| S06 context/g0 split | ✅ | structure payload carries context |
| v2 channel contract | ✅ | semantic/vector axes coexist |
| SQL facet projection | ✅ | all vector records receive six facets |
| metadata T08-A | ✅ | new revision and exact clean inheritance |
| T08-B | ⏸ | NH8 must remove three worker classes |

**下阶段 kickoff checklist**：

- [x] 引用本 closure and six query artifacts
- [ ] NH6 不改语义权威；只供 runtime capability
- [ ] NH7 每格 namespaced search 消费 v2 facets
- [ ] NH8 将 T08-B count 3→0 并修复旧 namespace tests

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| FilterMeta 不进 g0 | ✅ 保持 | overlay/g0 tests |
| `unknown` 不自动成为权威 | ✅ 保持 | contract/provider source scans |
| provenance 不参与 fingerprint | ✅ 保持 | semantic UoW equality |
| facet 在 SQL LIMIT/rank 前生效 | ✅ 保持 | captured SQL + L4 exclude |
| namespace 仍必填 | ✅ 保持 | T07 negative |
| metadata clean stored object exact | ✅ 保持 | ordinal 1/2 same digest+UUID |
| no T08-B fake green | ✅ 保持 | explicit count=3 red ledger |
