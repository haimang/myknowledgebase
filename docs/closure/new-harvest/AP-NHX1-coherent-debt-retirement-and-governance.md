# [NHX1 / coherent-debt-retirement-and-governance] Closure

> 阶段: `NHX1 — coherent debt retirement and governance`
> 范围: `Phase 1–9 全部工程代码、测试、证据与本地审查`
> Close-type: `implementation-complete-awaiting-live-verification`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-08-31` · 作者: `Codex`
> 关联 charter: `docs/eval/new-harvest/pre-NHX1-qna.md`
> 关联 design: `docs/eval/new-harvest/after-2nd-pass-review-coherent-fixes-design.md`
> 关联 action-plan: `docs/plan/new-harvest/AP-NHX1-coherent-debt-retirement-and-governance.md`
> 关联 evidence: `docs/evidence/new-harvest/AP-NHX1/`
> 关联 review: `docs/code-review/new-harvest/NHX1-third-pass-review.md`

---

## 0. 一句话 verdict

> NHX1 Phase 1–9 的工程实现、迁移、全仓测试与本地第三轮审查已完成，但 T-O-419 的真实 production model/binary/S16 具名 owner attestation 缺失，因此保持 `implementation-complete-awaiting-live-verification`，不宣称 full-close。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `NHX1-T22-O` 尚未提供真实 10+3 production supply 与 S16 owner 签收，阻断最终 live closure。
> 2. 本地结果证明工程路径，不替代真实环境的 L3/L4/S16 证据。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `P1-01..P1-04` Truth denominator / fixtures / harness | ✅ | commit `4c6c5c2` + `tests/domain/test_nhx1_truth_and_coverage.py tests/domain/test_nhx1_harness_integrity.py tests/domain/test_nhx1_evidence_pack.py`（17 passed）+ `2026-08-31T01:49:46Z` |
| `P2-01..P2-05` schema / ports / registries | ✅ | commit `3ce2a0a` + persisted upgrade/schema/constraint suite（64 passed correction gate）+ `2026-08-31T02:07:52Z` |
| `P3-01..P3-05` observation / epoch / lifecycle | ✅ | commit `b6769e1` + identity/epoch/scatter/rebuild/lifecycle suite（38 passed）+ `2026-08-31T02:56:34Z` |
| `P4-01..P4-06` revision / binding / outcome / retry / outbox | ✅ | commit `386f829` + workflow replay/outcome/outbox suite（40 passed）+ `2026-08-31T03:34:15Z` |
| `P5-01..P5-06` session / evidence / CAS / publication / cleanup | ✅ | commit `ff104a9` + object/evidence/publication/cleanup suite（92 passed）+ `2026-08-31T04:38:50Z` |
| `P6-01..P6-04` role / capability / readiness / security | 🟡 partial | commit `d4ea697` + role/supply/NH6 suite（61 passed）+ `2026-08-31T04:58:17Z`; T22-E ready-for-owner-gate, T22-O pending |
| `P7-01..P7-04` discovery / control / signals / errors | ✅ | commit `f90289d` + public/operator/signal suite（44 passed）+ `2026-08-31T05:40:40Z` |
| `P8-01..P8-03` shadow / cutover / drain / rollback | ✅ | commit `5e775f7` + cutover/compat/drain suite（32 passed）+ `2026-08-31T05:50:08Z` |
| `P9-01..P9-04` closed set / race / crash / full repo | 🟡 partial | commit `c3aa550` + `d843f00` + closed-set/race/crash/full repo（1010 passed）+ `2026-08-31T07:39:33Z`; live owner gate pending |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 全仓测试 | `uv run pytest -q` | `EXIT0 · 1010 passed · zero failed/skip/xfail` | P1–P9 当前代码 |
| 静态检查 | `uv run ruff check api intake src tests` | `EXIT0 · All checks passed!` | API/runtime/services/contracts/tests |
| 工作树静态 | `git diff --check` | `EXIT0` | 当前提交与文档边界 |
| graph-derived manifest | `tests/fixtures/new_harvest_nhx1/generate_manifest.py` | `888 route + 27 process + 21 intent cells；digest 938ff6…` | NHX1-T27 |
| deterministic race | `tests/e2e/test_nhx1_race_soak.py` | 3 fixed seeds PASS；无 sleep 判定 | NHX1-T28 |
| subprocess crash | `tests/e2e/test_nhx1_subprocess_crash.py` | 实际 SIGKILL process group + cold restart PASS | NHX1-T29 |
| execution evidence | `docs/evidence/new-harvest/AP-NHX1/tests.txt` | P1–P9 四元组与全 Test-ID join 已记录 | NHX1-T01..T30 |
| third-pass review | `docs/code-review/new-harvest/NHX1-third-pass-review.md` | 未发现未解释 critical/high 工程缺口 | 本地审查 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| P1→P2→…→P8 DAG | 前序工程 EXIT、证据、日志、分簇 commit 齐全 | 每阶段均有独立 code/docs commit 与测试记录 | ✅ PASS |
| migration integrity | 025–029 forward-only；001/018–024 不改写 | persisted upgrade、checksum、SQL attack 全绿 | ✅ PASS |
| public/operator boundary | public safe catalog/views；operator token/network + CAS/receipt；无 raw SQL | strict models、internal guard、control tests 全绿 | ✅ PASS |
| graph/race/crash/full repo | compiler-derived cells、真实 kill、全仓无排除 | 888/27/21；SIGKILL；1010 passed | ✅ PASS |
| `NHX1-T22-E` | engineering profile 可运行，缺 supply 不 claim | role/capability/readiness/security 61 passed | ✅ READY-FOR-OWNER-GATE |
| `NHX1-T22-O` | 真实 model/binary/S16 具名签收 | 本地没有 owner attestation | ⏸ PENDING |
| Final closure | T22-E + T22-O join 后才能 full-close | T22-O 未满足 | ⏸ BLOCKED |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 真实 production model/binary identity、10 strategies + 3 operations L3/L4 evidence、S16 named attestation | `C` | pending | T-O-419 / `NHX1-T22-O`；提供后重跑 production T22/T30 | Owner / deployment operator |
| local `all` role 的 historical proofless lifecycle repair diagnostic 不作为 hard readiness gate | `B` | documented compatibility | split `workflow_worker` deployment 由 supervisor threshold 硬闸；未来 all-role policy变更需新 review | MKB runtime owner |
| existing-object new cleaner/validator upgrade | `A` | out of scope | T-O-420；另开 owner-gated charter，不借 retry/rebuild 实现 | Owner / future charter |
| raw object GET/export/list/presign 与 remote R2 adapter | `A` | out of scope | T-O-415 scope boundary；不进入 NHX1 closure | Owner / future charter |
| experiment 发车/评分 | `A` | out of scope | 继续隔离，不进入 NHX1 closed set | Owner / experiment charter |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred） | ✅ P1–P5、P7–P8 为 `verified`；P6/P9 的 T22-O 为 `partial/live-pending` |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ✅ 每项在 §1 与 evidence tests.txt 有 commit、命令/计数、UTC |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改） | ✅ 全仓架构守卫、ruff、git diff check 通过；仅本计划代码/测试/证据/审查文件变更 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ §4 明确列出 A/B/C、触发条件与责任方 |
| owner-test 项未经 owner 复测的标 ⏸ PENDING | ✅ `NHX1-T22-O` 明确 pending；未用 stub、fixture、skip、xfail 冒充 |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| 引用本 closure 与 AP evidence 作为 single truth anchor | ✅ | `docs/evidence/new-harvest/AP-NHX1/` |
| 保持 v2-only / no legacy writer revival | ✅ | cutover service 与 tests 已验证 |
| 提供真实 10+3 production supply identity | ⏸ | T22-O owner action |
| 完成 S16 security/network/process-tree named attestation | ⏸ | T22-O owner action |
| 重跑 production-profile T22/T30 evidence executor | ⏸ | T22-O 完成后执行 |

**下阶段 kickoff checklist**：

- [x] 引用本 closure 作为 single truth anchor
- [ ] 注入具名真实 model/binary/S16 owner evidence，禁止更改本地期待以绕过 gate
- [ ] 重跑 NHX1-T22/T30，随后只补 closure 的最终 owner join 与 verdict

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| Source/Observation/Snapshot/ItemEpoch 身份分账 | ✅ 保持 | P3 tests、migration 025、T-O-408/409 |
| rev1 exact + rev2 active；old pin 不被改写 | ✅ 保持 | P4/P8 tests、rev1 manifest、T-O-411 |
| ProcessingBinding 10 + 3，不把 registered API 当第 11 strategy | ✅ 保持 | P4/P6 capability tests、T-O-412 |
| handle 只代表 bytes；session token 拥有 exact pending/ref | ✅ 保持 | P5 session tests、T-O-413 |
| legacy evidence append-only verdict/correction | ✅ 保持 | migration 027/029、P5/P8 evidence tests、T-O-414 |
| public safe / operator fenced / no workflow selector or raw SQL | ✅ 保持 | architecture、P7 public/operator tests、T-O-415 |
| api/workflow_worker/maintenance/all ownership explicit | ✅ 保持 | P6 role/readiness tests、T-O-416 |
| logical delete 后 retention cleanup/GC proof；tombstone key permanent | ✅ 保持 | P5/P8 cleanup/GC/intent tests、T-O-417/T-O-421 |
| canonical UPPER_SNAKE errors + legacy aliases | ✅ 保持 | signal/error tests、T-O-418 |
| production gate absent 时不 close | ✅ 保持 | T22-O pending、T-O-419 |
| existing-object upgrade OOS | ✅ 保持 | scope ledger、T-O-420 |
| critical dead outbox terminalizes owner；requeue preserves predecessor | ✅ 保持 | P4/P7 operator tests、T-O-422 |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `r1` | `2026-08-31` | `Codex` | NHX1 P1–P9 engineering implementation, full local assurance, and explicit T22-O owner-pending closure |
