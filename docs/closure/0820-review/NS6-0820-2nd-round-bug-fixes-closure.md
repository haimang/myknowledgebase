# [NS6 / 0820 2nd-round bug-fixes] Closure

> 阶段: `MKB/NS6 — 0820 second-pass verified-findings 修复`
> 范围: `P1–P6 代码执行合拢 + 自我审核测试↔修复循环`
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

> NS6 按 DAG 串行落地 P1–P6 后，自我审核确认 8/8 `[true-bug]` 代码已切，但 T21–T26 等多处测试是假绿、VF15 scatter 漏栅栏、VF16 purge 合同仍分裂、mega 仍带 CW waiver。审核循环已硬切这些 in-scope 缺口：serving 真 upsert + 017 generation unique、HITL/digest/accept replay 经 PersistencePort、purge=`all` 且不再 sqlite3 打开 Turso 文件、默认 Turso Settings 主链含 retrieval。VF86 harness 与 441/441 仍不是 DoD。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. VF86 / VF35.r e2e `sqlite3.connect` Turso 仍 NS1-V11（禁止用 sqlite3 当绿；不得拿它当「没做 Turso 产品路径」的借口）。
> 2. VF6/20/32 与 VF4.r/11.r/25.r/36.r 仍 deferred。
> 3. VF62 重叠 `run_once` 仍关——这是 NS5 未关的 carry-forward，**不是**业主把 `[partial-delivery]` 改写成 true-deferred。
> 4. 同 key 二次 ingest：accept 已 replay 且 items=1；structurize outcome-commit 仍可能 `retry-exhausted`（VF15.r）。
> 5. BEGIN-cancel soak 仍是 asyncio `to_thread` 门，不是 pyturso cancel-during-BEGIN（SIGSEGV 陷阱；已知 hotfix）。

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
| P4-01…P4-07 | ✅ | `2916c26` + 审核循环：T21 真 upsert、T22 PersistencePort HITL、T23 `read_verified`、T24 items=1、T25 purge=`all`、T26 generation CAS + 2026-08-20 11:44 UTC |
| P5-01…P5-05 | ✅ | `7be0fb5` + `test_empty_cidr_does_not_admit_metrics_via_xff` + 2026-08-20 11:44 UTC |
| P6-01 假绿 | ✅ | journal 真 import `collect._journal_row`；CLI timeout 杀 pid；sidecar 查 `mkb_ops_diagnostic_logs` |
| P6-02 NS5 叙述 | ✅ | NS5 closure P2-05/P2-07 翻 🟡 |
| P6-03 mega/soak | ✅ | 默认 Settings（无 CW/NV waiver）ingest→vector COUNT→retrieval；soak BEGIN×5 + heartbeat×3 |
| 审核循环 | ✅ | registered_api unique；017 Layer-A generation unique；GC 无 quarantine fail-closed；factory 懒加载 sqlite；glossary 改 Turso+PersistencePort |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| NS6 短途 | `uv run pytest tests/unit/test_ns6_*.py tests/unit/test_ns6_audit_cycle.py` 及相关假绿改写 | PASS（含 T21–T26/T22 HTTP） | 审核循环 |
| unit+domain+integration | `uv run pytest tests/unit tests/domain tests/integration --ignore=tests/e2e` | exit 0（2026-08-20 11:44 UTC） | 观察非 VF86 红，不是 441/441 徽章 |
| ruff | `uv run ruff check src tests api` | 0 | P6-03 |
| mega | `test_ns5_turso_mainchain` 默认 Settings + PersistencePort COUNT + `retrieval:search` | PASS | P6-03 |
| soak | `test_ns6_soak` BEGIN×5 + heartbeat×3 | PASS | P6-03 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| NS6-T01 BEGIN | 取消后再 BEGIN | `test_ns6_uow_begin_cancel` PASS | ✅ PASS |
| NS6-T02 默认 ready | 无 waiver Settings | `test_ns6_default_ready` PASS | ✅ PASS |
| NS6-T03 journal_mode | 第二连接不变 | `test_ns6_journal_mode_restore` PASS | ✅ PASS |
| NS6-T21 serving | indexed COUNT | 真调用 `_upsert_vector_record_tx`；indexed gen=1 COUNT=1 且 gen=2 INSERT | ✅ PASS |
| NS6-T28 XFF | 空 CIDR 不信 | `request_ip` + 公网 peer `/metrics` ≠ 200 | ✅ PASS |
| NS6-T33 假绿 | 真 SUT 调用 | journal import `_journal_row`；sidecar SELECT log_code；CLI pid 已死 | ✅ PASS |
| NS6-T35 mega | PersistencePort 主链 | 默认 Settings（无 waiver）+ vector COUNT + retrieval HTTP | ✅ PASS |
| NS6-T36 soak | BEGIN×5 + heartbeat×3 | `test_ns6_soak` PASS | ✅ PASS |
| NS6-T37 ruff/sqlite3 | 不新增 sqlite3-on-Turso | ruff 0；tests sqlite3.connect diff 0 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| VF86 sqlite3-on-Turso e2e (a) | `A` | owner-gated | NS1-V11 harness；禁止用 sqlite3.connect 当绿 | owner |
| VF6 014 dirty unique | `A` | deferred | 真实升级 UNIQUE 失败 | owner |
| VF20 retrieval write lock | `A` | deferred | ingest 期间检索 503 | owner |
| VF32 `/docs` | `A` | deferred | 公网 bind | owner |
| VF62 overlapping run_once | `B` | NS5 carry-forward，本轮仍关 | **不是**业主 true-deferred；后继 charter 在 heartbeat soak 之后 | owner |
| VF4.r D04 55 表 | `B` | remaining | 后继 schema | 下游 |
| VF11.r 进程组杀孙 | `B` | remaining | CLI charter | 下游 |
| VF25.r 未编目 orphan | `B` | remaining | T-O-120 | owner |
| VF36.r sidecar 有界队列 | `B` | remaining | TTL 已切；队列仍 remainder | 下游 |
| VF15.r 同指纹 re-structurize | `B` | remaining | accept replay + items=1 已切；structurize outcome-commit 仍可能 retry-exhausted | 下游 |
| 第1轮 VF23 billing | `A` | always-permit | 与本轮 VF23 outbox metrics **不同号** | owner |
| VF88 live GPU | `A` | deferred-by-owner | 本轮不得假装关 | owner |
| VF97 browser/OCR | `A` | deferred-by-owner | 本轮不得假装关 | owner |
| T01 soak hotfix | `C` | known-hotfix | asyncio `to_thread` 门；禁止 in-process 取消真实 sqlite BEGIN | 文档 |

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
| `r3` | `2026-08-20` | `Grok` | 六轴自我审核 + 测试↔修复：补 VF12/15/16/25/35 硬切与 T21–T26/T35 谓词；观察 unit/domain/integration；S12/S13/S15/S16/S09/S10 窄回填 |

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

---

## 11. 自我审核循环回填（r3 · 2026-08-20 11:44 UTC）

六个独立 explore 子代理对齐 closure 六轴后，进入测试↔修复，再与 VF-ledger / deferred-ledger 对账。

### 11.1 六轴汇聚

| 轴 | 审核结论 | 本循环动作 |
|----|----------|------------|
| 1. VF-ledger 欠交付 | 8/8 true-bug 代码已切；in-scope 漏 VF16 purge 合同、VF35 journal/CLI、T21–T26 假绿 | 硬切 purge=`all`+PersistencePort、journal import、真 upsert/HITL/digest/CAS |
| 2. 未完成硬切 | VF15 `registered_api` 漏 unique；GC unlink fallback；mega 仍 CW waiver | scatter 同 TX resolve；fail-closed quarantine；默认 Settings mega + retrieval |
| 3. 新假绿 | T21 lookup-only、T23 hashlib 同义反复、T24 只查 index 名、T22 无测试 | 重写谓词；观察 unit/domain/integration（exit 0），**不以 441/441 为绿徽章** |
| 4. sqlite-as-driver | 生产默认是 Turso；sqlite 仍 eager import；glossary 要 sqlite；e2e sqlite3-on-Turso 未减 | factory 懒加载；`src.persistence` 不再 re-export SqlitePersistence；glossary 改 Turso+port |
| 5. hotfix vs 治理 | 合同大多耐久；S12/S15/S16 未回填；GC path/fallback 是 hotfix | 窄回填 S12/S13/S15/S16/S09/S10；GC path=`quarantine/<team>/`；缺 API fail-closed |
| 6. deferred vs Turso | (a) sqlite3-on-Turso harness 合法推迟；(b) TursoPersistence migrate/ready/vectorize 本轮必修 | 付 (b)：默认 ready、journal pyturso、mega 无 waiver + retrieval。**不**用 VF86 掩盖 (b) |

### 11.2 为什么这些 deferred 符合业主预期

- **VF86 (a)**：业主冻结 NS1-V11。禁止把 `sqlite3.connect(Turso 文件)` 当绿。本循环还**删掉了** purge e2e 里那条 sqlite3 检查，改 PersistencePort，方向与冻结一致。
- **441/441 不是 DoD**：AP §8.4 / §10.3 写明。本循环**观察了** unit/domain/integration（exit 0），但拒绝用全量 pytest 当绿徽章，因为 e2e 仍有 VF86 噪声和 generation drain 红。
- **sqlite3-on-Turso e2e 推迟，不等于 Turso 未整合**：生产 factory 默认 turso；`/ready` 用 `write_path_ready`；业务 UoW 仍 `BEGIN IMMEDIATE`；T02/T03/T35 走 `TursoPersistence`。业主点名的是 **Turso 产品路径**，不是 sqlite3 打开 Turso 文件的检查器。
- **VF6/20/32、VF4.r/11.r/25.r/36.r、billing、VF88、VF97**：ledger §5.4 / AP O 表已冻，本轮只登记。
- **VF62**：NS5 `[partial-delivery]` 未关，NS6 AP 明确本轮仍关。登记为 carry-forward，**不**改写成业主 true-deferred。

### 11.3 本循环验证

- `uv run pytest tests/unit tests/domain tests/integration --ignore=tests/e2e`：**exit 0**
- `uv run ruff check src tests api`：**0**
- 未跑全量 441/441；未跑 VF86 剩余 e2e sqlite3 检查器；未跑 live GPU
- T24：items=1 且 accept_snapshot succeeded；同指纹 structurize 再生成仍可能失败（VF15.r）
