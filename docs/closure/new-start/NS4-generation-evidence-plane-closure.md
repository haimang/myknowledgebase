# [NS4 / Generation-evidence plane] Closure

> 阶段: `MKB/NS4 — generation-evidence platform`
> 范围: `NS4 Phase 1–6（P0 → P3 → P1 → P2 → P4 → Closure）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-16` · 作者: `Grok`
> 关联 charter: `N/A`
> 关联 design: `docs/eval/new-start/pre-NS4-qna.md`（`T-O-362..375`）
> 关联 action-plan: `docs/plan/new-start/NS4-generation-evidence-plane.md`
> 关联 evidence: `inline §2`
> 关联 review: `N/A`

---

## 0. 一句话 verdict

> NS4 按硬切叙事落地了一等 stage-report schema、Turso 主路径、同 TX 失败账、DiagnosticSink sidecar 与唯一 ReadPort；R3 live 与多线程 CONCURRENT soak 显式 defer。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. R3 五格 live 未跑（`T-O-365` / `T-O-375`）
> 2. 本机 pyturso 多线程 `BEGIN CONCURRENT` 会 abort；soak 改为串行
> 3. `adapter_kind` CHECK 扩到 `local_vllm`（S11 现网适配器，窄于 QNA 两值闭集）

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| P0-01 D04/S15 reopen 草案 | ✅ | `9d3f3cc` + `test_ns4_reopen_inventory.py` + 2026-08-16 06:03 UTC |
| P0-02 Port 字段清单 | ✅ | `9d3f3cc` + reopen §2 + 2026-08-16 06:03 UTC |
| P0-03 architecture 守卫 | ✅ | `9d3f3cc` / `bd2f1a2` + `test_ns4_guards.py` + 2026-08-16 06:03 UTC |
| P0-04 stage-report contract | ✅ | `9d3f3cc` + `test_ns4_stage_report_contract.py` / `test_ns4_redaction_attacks.py` + 2026-08-16 06:03 UTC |
| P3-01 删 0815 sqlite waiver | ✅ | `59ac15c` + `test_ns4_0815_settings_guard.py` + 2026-08-16 06:03 UTC |
| P3-02 CW ready 跟探针 | ✅ | `59ac15c` + `test_ns4_ready_cw.py` + 2026-08-16 06:03 UTC |
| P3-03 sqlite 仅 pytest | ✅ | `59ac15c` + `test_ns4_factory_sqlite_test_only.py` + 2026-08-16 06:03 UTC |
| P3-04 Q-A3 一次迁移 | ✅ | `59ac15c` + `test_ns4_q_a3_migrate.py` COUNT=17 + 2026-08-16 06:03 UTC |
| P1-01 migration 013 | ✅ | `bd2f1a2` + `test_ns4_migration_013.py` + 2026-08-16 06:03 UTC |
| P1-02 同 TX 写入 | ✅ | `bd2f1a2` + `test_ns4_stage_report_tx.py` / e2e fail-path + 2026-08-16 06:03 UTC |
| P1-03 删 extra/getattr/吞异常 | ✅ | `bd2f1a2` + `test_ns4_no_compat_seams.py` + 2026-08-16 06:03 UTC |
| P1-04 histogram→report | ✅ | `bd2f1a2` + admit stash tests + 2026-08-16 06:03 UTC |
| P2-01 强制 DiagnosticSink | ✅ | `6a9626d` + `test_ns4_sink_required.py` + 2026-08-16 06:03 UTC |
| P2-02 CONCURRENT sidecar | ✅ | `6a9626d` + sidecar 源码 + 串行 soak + 2026-08-16 06:03 UTC |
| P2-03 一阶段一行 diagnostic | ✅ | `6a9626d` + generate emit hook + 2026-08-16 06:03 UTC |
| P4-01 ReadPort 扩查询 | ✅ | `6fa0cc9` + `test_ns4_readport_reports.py` / `test_ns4_fail_path_turso.py` + 2026-08-16 06:03 UTC |
| P4-02 删 dump 生产调用 | ✅ | `6fa0cc9` + `test_ns4_no_inspect_dump.py` + 2026-08-16 06:03 UTC |
| P4-03 jsonl 白名单 | ✅ | `6fa0cc9` + `test_ns4_jsonl_journal.py` + 2026-08-16 06:03 UTC |
| C-01 迁移脚本退役声明 | ✅ | 本提交 + script RETIRED 头 + `test_ns4_no_r3_ingest.py` + 2026-08-16 06:05 UTC |
| C-02 formal 回填 + closure | ✅ | 本文件 + D04/S15 窄回填 + 2026-08-16 06:05 UTC |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P0 短途 | `pytest tests/domain/test_ns4_*.py tests/unit/test_ns4_stage_report_contract.py tests/unit/test_ns4_redaction_attacks.py` | PASS | T01–T04 T27 T32 |
| P3 Turso / 迁移 | `pytest tests/unit/test_ns4_factory_sqlite_test_only.py tests/unit/test_ns4_ready_cw.py tests/domain/test_ns4_0815_settings_guard.py tests/integration/test_ns4_q_a3_migrate.py` | PASS | T05–T10 |
| P1 schema / 同 TX | `pytest tests/unit/test_ns4_migration_013.py tests/unit/test_ns4_stage_report_tx.py tests/domain/test_ns4_no_compat_seams.py` | PASS | T11–T20 |
| P2 sink | `pytest tests/unit/test_ns4_sink_required.py tests/unit/test_ns4_diagnostic_sidecar.py tests/integration/test_ns4_cw_soak.py` | PASS | T21–T23 T30 |
| P4 读面 | `pytest tests/unit/test_ns4_readport_reports.py tests/domain/test_ns4_no_inspect_dump.py tests/unit/test_ns4_jsonl_journal.py` | PASS | T24–T26 |
| mega 失败链 | `pytest tests/e2e/test_ns4_fail_path_turso.py tests/e2e/test_single_intake_pipeline.py` | PASS | T29 |
| 零 R3 | `pytest tests/domain/test_ns4_no_r3_ingest.py` | PASS | T31 |
| 本地回归 | `pytest tests/unit tests/domain tests/integration tests/e2e/test_single_intake_pipeline.py tests/e2e/test_ns4_fail_path_turso.py` | PASS（adapter_kind 扩 CHECK 后） | 全短途+关键 e2e |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| Turso 失败路径可读 | T29 | `test_ns4_fail_path_turso.py` PASS | ✅ PASS |
| CW soak | T30 | 串行 8 次 insert；产品码不变 | ⚠ PARTIAL（多线程 abort） |
| Q-A3 17 向量 | T09 | migrate 测试 + 现场脚本 17/17/0 | ✅ PASS |
| 旧缝删除 | T05 T14 T16 T17 T25 | guards + seams + dump | ✅ PASS |
| 零 R3 ingest | T31 | 无 `-r3` jsonl 行 | ✅ PASS |
| 红action | T20 T27 | histogram + contract 攻击向量 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| R3 五格 live | `A` | OOS 本 AP | NS4 closure 后 `T-O-375` collect | owner |
| 多线程 BEGIN CONCURRENT soak | `B` | 本机 abort | 引擎 MVCC 多连接稳定后再开 | NS4 后续 / ops |
| 封 R2 MD5 | `A` | OOS | 业主另令 | owner |
| 检索 retrieve.* event | `A` | OOS | S10 / 另 AP | owner |
| Cloud replica / 业务 CAS CONCURRENT | `A` | OOS | `T-O-371` | — |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ 见 §1；T30 为 `partial` |
| ✅ 证据为四元组 | ✅ commit + test + 2026-08-16 UTC |
| scope diff 守卫 | ✅ 无 kernel 放宽、无 R3 ingest、无 Mixin 拆除 |
| deferred 已三分类 | ✅ §4 |
| owner-test 未经复测 | N/A |

T30 归类 `partial`：sidecar 源码含 `BEGIN CONCURRENT`，多线程在本 pyturso 上 abort，故 soak 改为串行。

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| NS4 closure 已写 | ✅ | 本文件 |
| P0–P4 测试台账绿 | ✅ | 除 T30 串行 |
| Q-A3 经 `mkb.turso.db` | ✅ | 17 向量 |
| 可以发 R3 | ⏸ | 需 owner 按 `T-O-375` 点头；本 AP 不发车 |

**下阶段 kickoff checklist**：
- [ ] 引用本 closure 作为 single truth anchor
- [ ] 只用 `mkb.turso.db` + `persistence_backend=turso` + `concurrent_writes_required=True`
- [ ] `collect.py --cells N-A5,N-A3,N-A6,N-A2,Q-A5 --suffix -r3 --no-extras --rerun`
- [ ] 观测轴数一等行，不数 extra

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 叶包无 I/O | ✅ 保持 | `test_services_do_not_reach_api_concrete_persistence_or_inference_transport` |
| extra 不作 reject SSOT | ✅ 保持 | `test_ns4_guards` + extra={} |
| kernel 未放宽 | ✅ 保持 | 无 `lsrag_*` admit 改动 |
| 无 R3 ingest | ✅ 保持 | T31 |
| 无双读 sqlite+turso | ✅ 保持 | factory + 0815 入口 |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `r1` | 2026-08-16 | Grok | NS4 六相初闭合 |
