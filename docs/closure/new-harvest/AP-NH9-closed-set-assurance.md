# [AP-NH9 / Closed-set assurance] Closure

> 阶段: `new-harvest/AP-NH9 — closed-set / crash / race / compat / security mega`
> 范围: `NH9-01..11 / NH9-T01..T11`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Grok`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH9-closed-set-assurance.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH9/`
> 关联 review: `inline §3`

---

## 0. 一句话 verdict

> NH9 已把 82 work IDs 与 13 正格/负格冻成可哈希闭集，九窗 crash/race 有具名 node，13 合法格经 namespace+facet 可检索，失败格零命中，并 join NH6 安全门与九包四元组。experiment 骨架空日期/分数且不进 join。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. CROSS-NH 仍须做九 AP 耦合审查与全量回归。
> 2. S16 签收未伪造；生产 `--no-sandbox` 仍禁。
> 3. HEAD `test_registered_api_scatter.py` 仍 ⛔ 不得当 T07 PASS（handler 赋值文件）；T07 主文件是 `test_new_harvest_closed_set.py`。
> 4. `.experiment` 被 gitignore，允许存在，不是 T11 EXIT0。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH9-01` closed-set | ✅ closed / verified | `8754df3` + T01 PASS + Q26/`T-O-406` + `2026-08-30T06:10:00Z` |
| `NH9-02` replay | ✅ closed / verified | `50c2246` + T02 PASS + `T-O-383` + UTC |
| `NH9-03` fail-loud zeros | ✅ closed / verified | T03 PASS + Q3 + UTC |
| `NH9-04` W-windows | ✅ closed / verified | `8196a0a` + T04/T05 PASS + Q20 + UTC |
| `NH9-05` upload/GC | ✅ closed / verified | `6390d9b` + T06 PASS + Q24 + UTC |
| `NH9-06` scatter query | ✅ closed / verified | T07 PASS + Q17 + UTC |
| `NH9-07` old pin | ✅ closed / verified | `6fbb1a7` + T08 PASS + Q10/Q18 + UTC |
| `NH9-08` retrieval mega | ✅ closed / verified | T09 16 passed + Q26 + UTC |
| `NH9-09` runtime security | ✅ closed / verified | `f7db57c` + T10 12 passed + Q19 + UTC |
| `NH9-10` evidence pack | ✅ closed / verified | T11 checker + this pack + `T-O-406` + UTC |
| `NH9-11` experiment | ✅ closed / deferred | 非 DoD；日期/分数 null；`in_closure_join=false` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| Closed-set digest | `queries/closed-set-digest.json` | NH1 digest kept; 82/13/4 | T01 |
| Crash windows | `queries/crash-windows.json` | 九窗 node | T04–T06 |
| Mega cells | `queries/mega-cells.json` | 13 legal cells | T09 |
| Negative zeros | `queries/negative-zero-hits.json` | empty/unknown/child-fail | T03/T07 |
| Security | `security/runtime-security.txt` | T10 12 passed | T10 |
| FG index | `security/fg-nh-01-17.md` | 17 green; tests.txt is PASS evidence | T11 |
| Static review | `ruff check`; `git diff --check` | PASS | changed Python |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| Coverage | 82 works; 10+3; 七意图非笛卡尔 | T01 | ✅ PASS |
| Replay/fault | 九窗 deterministic; 无双根 | T02/T04/T05 | ✅ PASS |
| Object/scatter | 不丢 bytes; zero/child query | T06/T07 | ✅ PASS |
| Compat | old pin 完结; alias 非 actual | T08 | ✅ PASS |
| Product | 13 正格 L4; 失败格 0 | T03/T09 | ✅ PASS |
| Security | NH6 isolation/readiness/backpressure | T10 | ✅ PASS |
| Evidence | 九包六类; FG 17; 无过期 waiver | T11 | ✅ PASS |

Review notes:

- Task identity replay is HTTP 200 vs 201, not a JSON `replayed` field.
- Failed ingest has no Layer-A namespace; T03 seeds a control document and isolates with facets.
- Scatter child-fail uses `_FailOneScatterChild` only as a fault injector; PASS is parent `scatter-required-child-failed` plus failed-item namespaced search empty.
- PROM-CAT injects `after_promote_before_catalog` on the existing upload UoW hook.
- S16 is not signed here.

---

## 4. Deferred / Carry-over ledger

| ID | 类型 | 内容 | 承接 |
|----|------|------|------|
| CROSS-NH | B | 九 AP 耦合审查 + 全量回归 | `CROSS-NH-REVIEW/TEST/CLOSE` |
| S16 | C | 不伪造签收 | owner / later security charter |
| experiment | A | 发车日不冻、不进 DoD | `T-O-380` |

---

## 5. ✅ 诚实收口 5 态

| Item | 5 态 |
|------|------|
| T01–T10 | verified |
| T11 pack | verified |
| experiment | deferred |
| S16 | 未观察（未伪造） |

---

## 6. 下游作者 kickoff

读：本 closure、`docs/evidence/new-harvest/AP-NH9/`、`docs/plan/new-harvest/todo-list.md` 的 CROSS-NH。
不要改冻结 T-O。不要把 `.experiment` 分数写进 DoD。
