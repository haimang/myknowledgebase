# [NS1 / New pipeline] Closure

> 阶段: `MKB/NS1 — non-interactive agentic production path`
> 范围: `NS1-P1–P5 全部 phase`
> Close-type: `close-with-known-issues`
> 状态: `close-with-known-issues`
> 日期: `2026-08-14` · 作者: `Codex`
> 关联 charter: `docs/plan/new-start/NS1-new-pipeline.todo.md`
> 关联 design: `docs/eval/new-start/non-interactive-agentic-pipeline.md`
> 关联 action-plan: `docs/plan/new-start/NS1-new-pipeline.md`
> 关联 evidence: `inline §2`
> 关联 review: `N/A — owner expressly prohibited live migration and deployment`

---

## 0. 一句话 verdict

> NS1 的 P1–P5 代码在第 1 轮三方审查后已补齐 catalog 运营面、CLI 生产接线、Markdown/clean 双物料合同与测试假绿；以 `close-with-known-issues` 收口。仍未关闭的残差只有既有 pyturso inspection harness，以及未授权的 live Claude vendor 验证。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. 完整 e2e 中若干 test-case 在标准 `sqlite3.connect` 读取 pyturso 文件时出现 `disk I/O` / `file is not a database`（baseline harness，非 NS1 机制）。
> 2. CLI 大物料 stdin 运输已在本地假 executable 证明不再 E2BIG；真实 `claude` 二进制的 vendor 验证需 owner 授权窗口。
> 3. 详见 `docs/code-review/new-start/NS1-review-VF-ledger.md` 与 `docs/closure/new-start/deferred-items-ledger.md`。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `P1-01..P1-06` 契约资产、四 role prompt、catalog、hash gate | ✅ closed | `(40b8ca2, 1ab1e37, 2f81be0 + P1 targeted pytest 16 passed, 2026-08-14 08:03 UTC)` |
| `P2-01..P2-03` layered adoption/kernel 与 production 假树退出 | ✅ closed | `(1971033, 1cc7d2e + adoption/compiler/generation pytest 19 passed and runtime scan, 2026-08-14 08:19 UTC)` |
| `P3-01..P3-05` Claude CLI port、四跳 worker 与 C whole-package | ✅ closed | `(fcb8d31, 72845a8, a6498c2 + CLI/stage regression 22 passed, 2026-08-14 08:34 UTC)` |
| `P4-01..P4-04` strict API、optional Markdown graph、failure routing、frozen pointers | ✅ closed | `(07e585b, b3022f8, a6d838b + P4 targeted 51 passed and e2e 2 passed, 2026-08-14 09:10 UTC)` |
| `P5-01..P5-04` guards、两条旅程、scatter isolation、truth/README 回填 | ✅ closed | `(d7cf742, 42538ee, 9017729 + P5 targeted 10 passed, docs/action-plan committed, 2026-08-14 09:23 UTC)` |
| `NS1-T44/T45/T46` 全量回归与 hash soak | 🟡 partial | `(d7cf742 + unit/domain/hash soak/non-residual e2e passed; full e2e has 6 pre-existing raw Turso inspection failures, 2026-08-14 09:23 UTC)` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P1–P4 targeted contracts | action-plan `§11.1–§11.4`; corresponding commit test commands | PASS | schema, catalog, adoption, CLI, API, workflow compatibility |
| Complete unit regression | `.venv/bin/python -m pytest -q tests/unit` | PASS, 100% | all unit tests including 32-round catalog resolve soak |
| Domain architecture regression | `.venv/bin/python -m pytest -q tests/domain` | PASS, 9 passed | D03 architecture and NS1 production fences |
| NS1 P5 acceptance | `.venv/bin/python -m pytest -q tests/domain/test_ns1_guards.py tests/e2e/test_ns1_pipeline.py tests/e2e/test_registered_api_scatter.py::test_registered_api_scatter_collects_child_failure_before_parent_terminal tests/unit/test_ns1_prompt_catalog.py tests/unit/test_prompt_hash_mismatch.py` | PASS, 10 passed | T40–T43 and T46 |
| Remaining e2e excluding known adapter cases | `.venv/bin/python -m pytest -q tests/e2e -k 'not scoped_index_rebuild_promotes_generation_without_new_intake_revision and not index_rebuild_stale_fence_fails_without_cutover_and_old_generation_remains_retrievable and not reactivate_restores_active_lifecycle_but_not_stale_serving_state and not rebuild_and_metadata_lifecycle_paths_complete_through_public_http and not registered_api_scatter_auto_zero_and_fanin_recovery'` | PASS, 12 passed | remaining generation/intake/source/scatter journeys |
| Full e2e re-pin | `.venv/bin/python -m pytest -q tests/e2e` | PARTIAL, 6 failures | all failures are raw `sqlite3` inspection of Turso files; no NS1 journey assertion failure |
| Static/build gates | `.venv/bin/python -m ruff check .`; `.venv/bin/python -m compileall -q api src tests`; `git diff --check` | PASS | repository static checks and bytecode compilation |
| Forbidden-path scan | `rg -n "compiler\.structurize\(|structurize\(\s*clean_text|body_text" src/runtime/intake src/persistence/migrations src/contracts/api/models.py` | no matches | production runtime, migrations, API contract |
| QNA immutability | `git diff 5955a99..HEAD -- docs/eval/new-start/pre-NS1-qna.md` | empty | frozen truth layer unchanged |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| No fake tree | production intake has no `compiler.structurize` or `structurize(clean_text)` | domain guard and production scan pass | ✅ PASS |
| Two mega journeys | generic without Markdown and legal with Markdown both complete | `test_ns1_pipeline.py` passes; process graph and g0/g1/g2 projection asserted | ✅ PASS |
| Failure isolation | one scatter child fails, sibling completes, root fails closed | existing scatter acceptance test passes with `scatter-required-child-failed` | ✅ PASS |
| Catalog safety and hash | role/path/hash/profile are frozen and repeated resolve is stable | catalog/hash suite plus 32 rounds × 4 prompt identities passes | ✅ PASS |
| API pointer safety | JSON identity required; body/path/prompt_ref rejected | strict Pydantic contract tests pass | ✅ PASS |
| Full local e2e | all e2e cases green | 6 cases blocked by pre-existing pyturso/raw-sqlite inspection incompatibility | ⚠ PARTIAL |
| Deployment fence | no live migration, worker release, or Pages release | command history contains only local tests/build/commits | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| Turso inspection parity for existing e2e cases (VF V11) | `C` | deferred, reproducible known issue | successor test-harness/adapter charter；use Turso port or a legal post-close snapshot, then rerun without exclusions | MKB owner |
| Live Claude stdin/file transport vendor verification (VF V5.r) | `A` | intentionally not run | owner authorizes a separate live verification charter and supplies approved runtime | MKB owner |
| live migration / worker publish / Pages publish | `A` | prohibited by current owner scope | separate release charter only; no runtime code depends on this verification | MKB owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred） | ✅；P1–P5 functional items are `observed-OK-at-closure`; T44 full e2e is explicitly `partial` |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ✅；§1 gives commit, reproducible test/scan, and UTC run-time for every closed item |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改） | ✅；final diff is limited to NS1 source/tests/plan/truth/README/closure paths and `git diff --check` passes |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅；§4 identifies owner, trigger, and successor charter |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称） | N/A；owner prohibited live migration/deployment, so no live owner-test is claimed |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| Read this closure and the NS1 action-plan log before follow-up work | ✅ | `docs/plan/new-start/NS1-new-pipeline.md` is the execution record |
| Preserve prompt identity-only API and frozen selected pointer semantics | ✅ | no body/path/prompt_ref wire; role/path/hash revalidated fail-closed |
| Repair Turso inspection harness before claiming all e2e green | ⏸ | six named raw-sqlite cases must be rerun after adapter-compatible inspection is available |
| Obtain explicit owner authorization before any live migration or deployment | ⏸ | current NS1 scope expressly forbids those actions |

**下阶段 kickoff checklist**：
- [ ] 引用本 closure 作为 single truth anchor
- [ ] 先修复并复跑 Turso inspection parity，再重新评估 `T44/T45` 全绿状态
- [ ] 不改变 NS1 的 no-body-in-DB、JSON closed profile、no-silent-fallback 约束

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| API 只传 prompt identity，catalog 提供 version/path/hash/role/profile | ✅ 保持 | `src/contracts/api/models.py`; `tests/unit/test_ns1_api_workflow.py`; P4 commits |
| prompt bytes remain git-only and DB has no `body_text` | ✅ 保持 | S14/D04 Appendix E; migration scan; `tests/domain/test_ns1_guards.py` |
| B JSON is the only granularity-profiled candidate and C consumes adopted layered JSON | ✅ 保持 | `data/schemas/lsrag.layered_content.v1.json`; adoption tests; NS1 two-journey e2e |
| Markdown is optional; omitted Markdown does not create `transcribe_markdown` | ✅ 保持 | `tests/unit/test_ns1_api_workflow.py`; `tests/e2e/test_ns1_pipeline.py` |
| structure failure is terminal and never silently opens human review | ✅ 保持 | `tests/unit/test_ns1_api_workflow.py::test_structurize_failure_routes_terminal_without_opening_human_review` |
| no live migration, worker release, or Pages release occurred | ✅ 保持 | owner scope and execution history; no deployment command was run |
