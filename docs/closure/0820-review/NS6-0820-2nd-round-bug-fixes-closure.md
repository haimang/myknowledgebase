# [NS6 / 0820 2nd-round bug-fixes] Closure

> 阶段: `MKB/NS6 — 0820 second-pass verified-findings 修复`
> 范围: `P1–P6 代码执行合拢`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed-with-explicit-deferrals`
> 日期: `2026-08-20` · 作者: `Grok`
> 关联 charter: `N/A`
> 关联 design: `N/A`
> 关联 action-plan: `docs/plan/new-start/NS6-0820-2nd-round-bug-fixes.md`
> 关联 evidence: `inline §2`
> 关联 review: `docs/code-review/0820-review/VF-ledger-0820-2nd-review.md`

---

## 0. 一句话 verdict

> NS6 按 DAG 串行落地 P1–P6：默认 Turso 可 ready+claim，BEGIN 取消可再写，journal_mode 不被探针改写，serving indexed 不可 UPDATE，空 CIDR 不信 XFF。VF86/live GPU 显式 deferred，不以 441/441 为 DoD。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. VF86 / VF35.r e2e `sqlite3.connect` Turso 仍 NS1-V11。
> 2. VF6/20/32 与 VF4.r/11.r/25.r/36.r 仍 deferred。
> 3. VF62 重叠 `run_once` 仍关。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| P1-01 BEGIN cancel | ✅ | `119f3ed` + `test_ns6_uow_begin_cancel` + 2026-08-20 10:57 UTC |
| P1-02 默认 ready | ✅ | `119f3ed` + `test_ns6_default_ready` + 2026-08-20 10:57 UTC |
| P1-03 journal_mode | ✅ | `119f3ed` + `test_ns6_journal_mode_restore` + 2026-08-20 10:57 UTC |
| P1-04 vLLM timeout | ✅ | `119f3ed` + `test_ns6_vllm_timeout` + 2026-08-20 10:57 UTC |
| P1-05 handler cancel | ✅ | `119f3ed` + `test_ns6_worker_cancel` + 2026-08-20 10:57 UTC |
| P1-06 heartbeat fence | ✅ | `119f3ed` + `test_heartbeat_exception_fences` + 2026-08-20 10:57 UTC |
| P1-07 GC quarantine | ✅ | `119f3ed` + `test_ns6_gc_toctou` + 2026-08-20 10:57 UTC |
| P1-08 TTL | ✅ | `119f3ed` + `test_health_ttl_returns_cached_result_on_sequential_ready` + 2026-08-20 10:57 UTC |
| P2-01…P2-08 | ✅ | `bd60f3e` + `test_ns6_phase2.py` + 2026-08-20 10:57 UTC |
| P3-01…P3-04 | ✅ | `e10e8bd` + `test_ns6_phase3.py` + 2026-08-20 10:57 UTC |
| P4-01…P4-07 | ✅ | `2916c26` + `test_ns6_phase4.py` + 2026-08-20 10:57 UTC |
| P5-01…P5-05 | ✅ | `7be0fb5` + `test_ns6_phase5.py` + 2026-08-20 10:57 UTC |
| P6-01 假绿 | ✅ | `test_ns4_readport_reports` / sidecar insert / `_journal_row` 真调用 + TTL 顺序 probe==1 |
| P6-02 NS5 叙述 | ✅ | NS5 closure P2-05/P2-07 翻 🟡 |
| P6-03 mega/soak | ✅ | `test_ns6_default_ready` + `test_ns5_turso_mainchain` vector COUNT + `test_ns6_soak` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| NS6 短途 | `uv run pytest tests/unit/test_ns6_*.py tests/unit/test_ns4_readport_reports.py tests/unit/test_ns4_diagnostic_sidecar.py tests/unit/test_ns4_jsonl_journal.py` | 47 passed | P1–P6 |
| ruff | `uv run ruff check src tests api` | 0 | P6-03 |
| build | `uv build` | wheel 含 `016_ns6_source_external_key.sql` | P4-04 |
| migration | destroy-rebuild Turso migrate twice | `migration-destroy-rebuild-ok` | P4-04 |
| mega | `test_ns6_default_ready` + `test_ns5_turso_mainchain` | PASS；vector_records COUNT≥1 | P6-03 |
| soak | `test_ns6_soak` BEGIN×5 + heartbeat×3 | PASS | P6-03 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| NS6-T01 BEGIN | 取消后再 BEGIN | `test_ns6_uow_begin_cancel` PASS | ✅ PASS |
| NS6-T02 默认 ready | 无 waiver Settings | `test_ns6_default_ready` PASS | ✅ PASS |
| NS6-T03 journal_mode | 第二连接不变 | `test_ns6_journal_mode_restore` PASS | ✅ PASS |
| NS6-T21 serving | indexed COUNT | `test_upsert_does_not_update_indexed_rows` PASS | ✅ PASS |
| NS6-T28 XFF | 空 CIDR 不信 | `test_empty_cidr_ignores_private_xff` PASS | ✅ PASS |
| NS6-T33 假绿 | 真 SUT 调用 | ReadPort/sidecar/journal 不再 inspect.getsource | ✅ PASS |
| NS6-T35 mega | PersistencePort 主链 | `test_ns5_turso_mainchain` vector COUNT≥1 | ✅ PASS |
| NS6-T36 soak | BEGIN×5 + heartbeat×3 | `test_ns6_soak` PASS | ✅ PASS |
| NS6-T37 ruff/sqlite3 | 不新增 sqlite3-on-Turso | ruff 0；tests sqlite3.connect diff 0 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| VF86 sqlite3-on-Turso e2e | `A` | owner-gated | NS1-V11 harness | owner |
| VF6 014 dirty unique | `A` | deferred | 真实升级 UNIQUE 失败 | owner |
| VF20 retrieval write lock | `A` | deferred | ingest 期间检索 503 | owner |
| VF32 `/docs` | `A` | deferred | 公网 bind | owner |
| VF62 overlapping run_once | `A` | still closed | 后继 charter | owner |
| VF4.r D04 55 表 | `B` | remaining | 后继 schema | 下游 |
| VF11.r 进程组杀孙 | `B` | remaining | CLI charter | 下游 |
| VF25.r 未编目 orphan | `B` | remaining | T-O-120 | owner |
| VF23 billing | `A` | always-permit | billing AP | owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ 上表 ✅ 均为 short-verified / observed-OK-at-closure（本地 unit/集成，非 live GPU） |
| ✅ 证据为四元组 | ✅ commit + test 名 + 2026-08-20 10:57 UTC |
| scope diff 守卫 | ✅ 本轮仅 NS6 AP 文件与对应 src/tests/docs |
| deferred 已三分类 | ✅ §4 |
| owner-test 项未经 owner 复测的标 ⏸ PENDING | N/A |

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| 默认 Turso 可 ready+claim | ✅ | `test_ns6_default_ready` |
| 禁止 sqlite3-on-Turso 当绿 | ✅ | 本轮未新增 |
| VF-ledger §6 append | ✅ | `VF-ledger-0820-2nd-review.md` §6 |

**下阶段 kickoff checklist**：
- [ ] 引用本 closure 作为 single truth anchor
- [ ] VF86 harness 仍不得在本仓假装关闭

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 业务 UoW `BEGIN IMMEDIATE` | ✅ 保持 | `src/persistence/uow.py` |
| 禁止 `sqlite3.connect` 打开 Turso 生产路径 | ✅ 保持 | 本轮未新增该调用 |
| VF62 overlapping 仍关 | ✅ 保持 | supervisor `allow_overlapping_run_once=False` |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `r1` | `2026-08-20` | `Grok` | 代码执行后、收口测试前初稿 |
| `r2` | `2026-08-20` | `Grok` | 本地短途/ruff/build/migration/mega/soak 回填；close-type `closed-with-explicit-deferrals` |

---

## 10. 收口测试回填（r2）

本地于 `2026-08-20 10:57 UTC` 完成 owner 授权的静态检查、wheel build、Turso migration 销毁重建，以及 NS6 短途+soak+mega。

- `uv run pytest tests/unit/test_ns6_*.py` 及相关假绿改写：**47 passed**
- `uv run ruff check src tests api`：**0**
- `uv build`：wheel 含 `016_ns6_source_external_key.sql`
- Turso migrate → 删文件 → migrate：`migration-destroy-rebuild-ok`
- `test_ns5_turso_mainchain`：HTTP ingest succeeded **且** PersistencePort `mkb_vector_records` COUNT≥1
- `test_ns6_soak`：BEGIN 取消 ×5 + heartbeat raise ×3
- 未跑全量 pytest 441/441；VF86 e2e sqlite3-on-Turso 仍 deferred
- 未跑 live GPU / Claude 登录

以上 ✅ 归类为 **observed-OK-at-closure / short-verified**，不是 live-verified。
