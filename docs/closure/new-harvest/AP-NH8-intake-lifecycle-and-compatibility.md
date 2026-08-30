# [AP-NH8 / Intake lifecycle and compatibility] Closure

> 阶段: `new-harvest/AP-NH8 — 七意图 / exact-clean / lifecycle query / old-pin`
> 范围: `NH8-01..08 / NH8-T01..T10`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Grok`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH8-intake-lifecycle-and-compatibility.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH8/`
> 关联 review: `inline §3`

---

## 0. 一句话 verdict

> NH8 已把七意图非法格停在 admission、rebuild/metadata 真正旁路 acquire/decode/clean，并以 namespaced search 证明 deactivate/reactivate/delete/index.rebuild 与 API Item 同法；old pin 可完结、新 Task 只 kind graph、upgrade 入口=0。crash/closed-set mega 按 DAG 交给 NH9。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. NH9 仍须做 closed-set / crash 全窗 / Capstone I–J；本 AP 不注入 W-NH-* kill。
> 2. HEAD scatter 文件仍可能含 sqlite3 段；T08 PASS 主文件是 🆕 `test_nh8_api_item_intents.py`。
> 3. 公开二次 `intake.delete` 对已 deleted Item 是 409 `intake-item-deleted`（零新 Task），不是同 idempotency_key 的服务层 no-op。
> 4. registered_api member 的 frozen clean 是 `mkb.scatter-clean-member.v1` JSON envelope；replay 解包正文，不把 CAS sha256 误当成 `clean_digest`。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH8-01` applicability | ✅ closed / verified | `27fc3ca` + T01 PASS + Q25/`T-O-405` + `2026-08-30T04:53:13Z` |
| `NH8-02` rebuild exact-clean | ✅ closed / verified | T02 PASS + Q27/`T-O-407` + UTC |
| `NH8-03` metadata no-change/changed | ✅ closed / verified | T03 + T08-B=0 PASS + Q27/`T-O-394` + UTC |
| `NH8-04` deactivate/reactivate/delete | ✅ closed / verified | T04/T05/T06 PASS + Q25 + UTC |
| `NH8-05` index.rebuild | ✅ closed / verified | T07 PASS + Q25 + UTC |
| `NH8-06` API Item 同服务 | ✅ closed / verified | T08 PASS + Q25 + UTC |
| `NH8-07` old/new retirement | ✅ closed / verified | T09 PASS + Q18/`T-O-398` + UTC |
| `NH8-08` restart/rebuild matrix | ✅ closed / verified | T10 PASS + Q21/`T-O-401` + UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| NH8 hard-gate suite | `tests.txt` command | `29 passed` | T01–T10 L1–L4 |
| Fake-green scan | `security/intent-negatives.md` | 零 sqlite3；namespace 422；process-absence=0 | FG-NH-05/12/15/17 |
| Queries | `queries/*.json` | intent/rebuild/metadata/lifecycle/index/api/lineage | T01–T10 |
| Static review | `ruff check`; `git diff --check` | PASS | changed Python/tests |
| Independent review | this closure §3 | no STOP on exact-clean or query-law predicates | land `27fc3ca` |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| Applicability | 非法格 422/409 ∈闭集；Task/Process=0 | T01 | ✅ PASS |
| Exact-clean | acquire/decode/clean=0；digest exact；T08-B=0 | T02/T03 | ✅ PASS |
| Lifecycle query | namespaced empty until new publish；tombstone 409 | T04–T06 | ✅ PASS |
| Index | generation+1；Revision 不变；hits 仅新代 | T07 | ✅ PASS |
| API Item | 同服务；role≠scatter_child | T08 | ✅ PASS |
| Compat/lineage | old pin 完结；kind-only；upgrade=0 | T09/T10 | ✅ PASS |

Review notes (implementation land `27fc3ca`):

- Start-route priorities: index.rebuild 0, rebuild 1, metadata_no_change 2, metadata_refresh 3, acquire 10.
- `request_intent_rebuild` / `request_intent_metadata_refresh` live on the shared tail (unique `guard_key`).
- Rebuild preflight no longer demands decode/clean process evidence; lineage is `rebuild_input_evidence` + frozen artifact.
- `metadata_disposition` is computed in `IntakeTargetResolver` and stored on root execution `payload_extra` so start-route guards can see no_change before any Process.
- Combined HEAD rebuild/metadata artifact-set exclusivity is not a T02/T03 unique node; metadata_refresh may copy S06 receipts without running `lsrag.structurize`.
- Dual-channel search after rebuild can return split original chunks that reconstruct the admitted clean; T05 asserts reconstruction, not a single full-string hit.

`M-NH-09` signed: behavioral, no DDL. Compat retirement review signed: in-flight retire fail-closed, rollback by re-injecting compatibility definitions.

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Closed-set generator / crash windows / Capstone I–J | C | query 终态已在本 AP | AP-NH9 | NH9 |
| HEAD scatter sqlite3 nodes | B | ⛔ 未列入 T08 PASS 主文件 | NH9 若 🔱 须先 Port 化 | successor |
| Existing-object new-cleaner upgrade | A | OOS `O-NH-03` / `T-O-401` | 新 owner-gate | owner |
| S16 browser egress sign-off | A | NH6 已诚实未伪造；本 AP 不重开 | none | — |

---

## 5. 诚实收口 5 态

| 项 | 5 态 | 说明 |
|----|------|------|
| T01–T10 hard gates | verified | commit `27fc3ca` + named pytest + `2026-08-30T04:53:13Z` |
| Capstone H | verified | T02–T08 namespaced query |
| Campaign mega / crash | deferred | NH9 |
| Owner live soak | 未观察 | 本仓 default-root short gates only |

---

## 6. Kickoff 给下游

NH9 可以开始。不得第一次补七意图/exact-clean/lifecycle query。消费 `docs/evidence/new-harvest/AP-NH8/` 与本 closure。
