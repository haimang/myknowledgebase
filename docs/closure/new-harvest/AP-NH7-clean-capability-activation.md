# [AP-NH7 / Clean capability activation] Closure

> 阶段: `new-harvest/AP-NH7 — 10+3 live-to-retrieval`
> 范围: `NH7-01..10 / NH7-T01..T10`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-30` · 作者: `Grok`
> 关联 charter: `docs/eval/new-harvest/final-execution-plan.md`
> 关联 design: `docs/eval/new-harvest/pre-charter-qna.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NH7-clean-capability-activation.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NH7/`
> 关联 review: `inline §2–§3`

---

## 0. 一句话 verdict

> NH7 已把 10 个 CleanStrategy + 3 个 registered-api operation 接到 default-root live-to-retrieval：namespaced + facet search 命中 admitted clean；`exhausted_zero` 独立于 indexed success；失败格零向量。七意图 / exact-clean / campaign mega 按 DAG 递交 NH8/NH9。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. 全仓仍有 5 个 namespace/rebuild 失败，属 NH8 红债，不是本 AP 假绿。
> 2. `tests/e2e/test_registered_api_scatter.py` 已无 `sqlite3.connect`（仅 `database_path` 文件名）；T08 PASS 主文件是 🆕 `test_nh7_registered_api_retrieval.py`。残留 `sqlite3.connect` 在 campaign 外：`test_inline_ingress_staging.py` / `test_ns1_pipeline.py` / `test_ns2_dispatch_lanes.py` / `test_human_review_gate.py`。
> 3. `web.llm_rewrite` 走 default-root CLI stub（非 patch）；print/DU/vision 走 S11 local fixture。库名仍不是 Truth。
> 4. NH1 promptA reader 清单在 canonical 对齐后已改 readers（三文件互斥 SHA 未改）。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `NH7-01` manifest | ✅ closed / verified | `1c74afe`/`6256a97` + T01 PASS + T-O-381 + `2026-08-30T02:28:40Z` |
| `NH7-02` admitted clean | ✅ closed / verified | T02/T10 PASS + T-O-386/383 + UTC |
| `NH7-03` promptA | ✅ closed / verified | `be74417` + T02 invocation/drift PASS + M-NH-07 + UTC |
| `NH7-04` inline/static | ✅ closed / verified | T03 PASS + T-O-376 + UTC |
| `NH7-05` PDF text-layer | ✅ closed / verified | T04 PASS + NH4 upload + UTC |
| `NH7-06` browser DOM | ✅ closed / verified | T05 PASS + Q22/T-O-402 + UTC |
| `NH7-07` print PDF | ✅ closed / verified | T06 PASS + Q23/T-O-403 + UTC |
| `NH7-08` five multimodal | ✅ closed / verified | T07 PASS + Q13/T-O-393 + UTC |
| `NH7-09` API + zero | ✅ closed / verified | T08/T09 PASS + Q17/T-O-397 + UTC |
| `NH7-10` publication chain | ✅ closed / verified | T03–T08 helper PASS + T-O-389 + UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| NH7 hard-gate suite | `tests.txt` command | `40 passed` | T01–T10 L1–L4 |
| Fake-green scan | `security/no-patch-namespace-zero.md` | 无 fetcher/LLM 赋值；namespace 422；empty 零向量 | FG-NH-01/05/06 |
| Publication chain | `queries/evidence-chain.json` | sealed actual ≠ legacy s05；S04 六键；g0=clean；proof+pointer | T03–T08 |
| Static review | `ruff check`; `git diff --check` | PASS | changed Python/tests |
| Independent review | this closure §3 | no STOP findings on live-to-query predicates | P4–P6 land `6256a97` |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 10+3 matrix | registry 生成 10+3；非法 fail-loud | T01 | ✅ PASS |
| clean contract | nonempty；PromptRef；确定性零调用；失败零向量 | T02/T10 | ✅ PASS |
| source lanes | default-root 无 patch；facet query | T03–T07 | ✅ PASS |
| API lanes | 三 member hit；exhausted_zero 独立 | T08/T09 | ✅ PASS |
| publication | actual/S04/g0/proof/pointer | T03–T08 helper | ✅ PASS |
| fake-green | 无 503/patch/empty/`publication_ready` 顶替 | scan + L4 | ✅ PASS |

Review notes (implementation land `6256a97`):

- Print lane counts sanitizer wrappers; call count is 0 on the PDF channel.
- `exhausted_zero` is a Task column + public view field; NOOP mapping still becomes SUCCEEDED but cannot write this disposition.
- Doc DU of non-image/non-PDF bytes uses S11 text_generate rather than illegal `text/plain` multimodal media_type. This is substrate-fit, not a new source kind.
- T08 does not 🔱 the sqlite3 scatter file.

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Seven intents / exact-clean bypass / metadata no_change | C | unchanged | AP-NH8 | NH8 |
| Index/reactivate namespace + rebuild STRUCTURE_PROFILE_INVALID | C | five repository failures | AP-NH8 | NH8 |
| Campaign mega / crash windows / closed-set generator | C | query 终态已在本 AP | AP-NH9 | NH9 |
| scatter sqlite3 直读（已关闭） | B | ✅ 仅 database_path 文件名；campaign 外 4 个 e2e 仍 sqlite3.connect | 后继 harness charter | successor |

---

## 5. 诚实收口 5 态

| 项 | 5 态 | 说明 |
|----|------|------|
| T01–T10 hard suite | verified | commit `6256a97` + 40 pytest PASS + Q17/`T-O-376..406` + `2026-08-30T02:28:40Z` |
| default-root live query | verified | T03–T08 namespaced+facet |
| exhausted_zero | verified | disposition + empty search + replay |
| full-repo remaining reds | deferred | NH8 namespace/rebuild |
| production S16 browser sign-off | deferred | already NH6 document gate; not re-forged |

---

## 6. Handoff

NH8 可假设 live clean 与 publication tail 已存在，不得再把 10+3 query 当第一次功能。NH9 回归 Capstone C–F，不补 NH7 通道。
