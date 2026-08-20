# [NS5 / 0820 VF bug-fixes] Closure

> 阶段: `MKB/NS5 — 0820 first-round verified-findings 修复`
> 范围: `P1–P6 代码执行合拢`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `implementation-complete-awaiting-live-verification`
> 日期: `2026-08-20` · 作者: `Grok`
> 关联 charter: `N/A`
> 关联 design: `N/A`
> 关联 action-plan: `docs/plan/new-start/NS5-0820-bug-fixes.md`
> 关联 evidence: `inline §2`
> 关联 review: `docs/code-review/0820-review/VF-ledger-0820-1st-review.md`

---

## 0. 一句话 verdict

> NS5 按 DAG 串行落地了 P1–P6 代码：UoW/sidecar/heartbeat/outbox 不再把唯一进程冻死，publication proof 与检索扫描 fail-closed，安全边界默认不信 XFF；wheel 含 migrations SQL。全量 pytest 与 live GPU 未宣称。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. VF86 e2e `sqlite3.connect` Turso 检查仍 NS1-V11（不以全绿为 DoD）
> 2. P3 schema freeze / CLI ConcurrencyGate / 同源 DispatchCaps 对象仍 partial
> 3. P4 title/acquisition/stub-summary/envelope/validator 若干切片未完整展开

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| P1-01 UoW cancel | ✅ | `d728d0b` + `test_ns5_uow_cancel.py` + 2026-08-20 05:49 UTC |
| P1-02 sidecar 串行 | ✅ | `d728d0b` + `test_ns5_sidecar_serial.py` / soak + 2026-08-20 05:49 UTC |
| P1-03 CLI kill | ✅ | `d728d0b` + `test_ns5_phase1_runtime.py::test_cli_timeout_kills_child` + 2026-08-20 05:49 UTC |
| P1-04 heartbeat | ✅ | `d728d0b` + `test_heartbeat_keeps_lease_from_being_stolen` + 2026-08-20 05:49 UTC |
| P1-05 outbox poison | ✅ | `d728d0b` + `test_ns5_outbox_poison.py` + 2026-08-20 05:49 UTC |
| P1-06 retirement stuck | ✅ | `d728d0b` + `test_ns5_retirement_stuck.py` + 2026-08-20 05:49 UTC |
| P1-07 GC 两阶段 | ✅ | `d728d0b` + `test_object_gc.py` + 2026-08-20 05:49 UTC |
| P1-08 `_pending` pop | ✅ | `d728d0b` + `test_pending_map_empty_after_success_and_discard` + 2026-08-20 05:49 UTC |
| P1-09 scanner | ✅ | `d728d0b` + `test_scanner_stays_running_after_one_error` + 2026-08-20 05:49 UTC |
| P1-10 claim drain | ✅ | `d728d0b` + `test_claim_next_drains_expired_then_takes_live` + 2026-08-20 05:49 UTC |
| P2-01 rowcount | ✅ | `4ad95c5` + `test_turso_stale_update_rowcount_is_zero` + 2026-08-20 05:49 UTC |
| P2-02 014 UUID+tombstone unique | ✅ | `4ad95c5` + `test_014_rewrites_32hex_model_uuid` + 2026-08-20 05:49 UTC |
| P2-03 时间戳 us | ✅ | `4ad95c5` + `test_timestamps_share_microsecond_timespec` + 2026-08-20 05:49 UTC |
| P2-04 jitter/dead/gate | ✅ | `4ad95c5` + runtime_outcome/outbox/gates + 2026-08-20 05:49 UTC |
| P2-05 ready coalesce | ✅ | `4ad95c5` + `test_health_ready_coalesces_within_ttl` + 2026-08-20 05:49 UTC |
| P2-06 bootstrap 可观测 | ✅ | `4ad95c5` + lifespan `bootstrap_failures` + 2026-08-20 05:49 UTC |
| P2-07 指纹/extras/409 | ✅ | `4ad95c5` + `test_team_patch_empty_extras_clears` + 2026-08-20 05:49 UTC |
| P2-08 脱敏 | ✅ | `4ad95c5` + `_safe_persisted_error` + 2026-08-20 05:49 UTC |
| P2-09 ready 诚实 | ✅ | `4ad95c5` + `test_drop_mkb_tasks_fails_schema_readiness` + 2026-08-20 05:49 UTC |
| P3-01 salvage/OVER_BUDGET | ✅ | `fd5c969` + `test_ns5_phase3.py` + 2026-08-20 05:49 UTC |
| P3-02 prompt fail-closed | ✅ | `fd5c969` + `test_ns1_prompt_file_requires_state` + 2026-08-20 05:49 UTC |
| P3-03 vLLM client/408 | ✅ | `fd5c969` + local_vllm/facade + 2026-08-20 05:49 UTC |
| P3-04 CLI stdin/env | ✅ | `fd5c969` + `test_prompt_transport_is_always_stdin` + 2026-08-20 05:49 UTC |
| P3-05 证据 process_uuid | ✅ | `fd5c969` + `test_evidence_is_keyed_by_process_uuid` + 2026-08-20 05:49 UTC |
| P3-06 schema freeze | 🟡 partial | probe 仅 2xx；generate schema SHA 复核未另开 | handoff → 后继 |
| P3-07 EXHAUSTED | ✅ | `fd5c969` + `_RECOVERABLE_ERROR_CODES` + 2026-08-20 05:49 UTC |
| P3-08 CLI gate | 🟡 partial | salvage 占 NI；无独立 CLI fork 计数器 | VF21 余项 |
| P3-09 拒二进制 clean | ✅ | `fd5c969` + `test_non_text_blob_is_rejected` + 2026-08-20 05:49 UTC |
| P3-10 同源 caps | 🟡 partial | 同 settings 数值，非同一对象 | VF96 余项 |
| P4-01 vectorize fail-closed | ✅ | `52e3913` + vectorize.py over_budget + 2026-08-20 05:49 UTC |
| P4-02 HTML 换行 | ✅ | `52e3913` + `test_html_extract_keeps_paragraph_breaks` + 2026-08-20 05:49 UTC |
| P4-03 单调锚 | ✅ | `52e3913` + adopt.py search_from + 2026-08-20 05:49 UTC |
| P4-04 PDF 去 latin-1 | ✅ | `52e3913` + `test_pdf_rejects_latin1_garbage` + 2026-08-20 05:49 UTC |
| P4-10 世代单调 + 015 | ✅ | `52e3913` + `015_vec_coord_generation.sql` + 2026-08-20 05:49 UTC |
| P4-13 召回截断 | ✅ | `52e3913` + LIMIT+1 `RETRIEVE_SCAN_TRUNCATED` + 2026-08-20 05:49 UTC |
| P4-15 team inactive | ✅ | `52e3913` + `RETRIEVE_TEAM_INACTIVE` + 2026-08-20 05:49 UTC |
| P4-16 purge Proof | ✅ | `52e3913` + `test_partial_channel_purge_is_rejected` + 2026-08-20 05:49 UTC |
| P4-05/06/07/08/09/11/12/14/17/18 | 🟡 partial | 未全部展开切片 | AP §2.2 O4 |
| P5-01 trusted-proxy | ✅ | `34c86b6` + `request_ip` XFF 规则 + 2026-08-20 05:49 UTC |
| P5-02 overflow 限流 | ✅ | `34c86b6` + `test_rate_limiter_overflow_does_not_fail_open` + 2026-08-20 05:49 UTC |
| P5-03 extras 拒密 | ✅ | `34c86b6` + `test_camelcase_secret_and_signed_url_rejected` + 2026-08-20 05:49 UTC |
| P5-04 sqlite 双因子 | ✅ | `34c86b6` + factory `pytest in sys.modules` + 2026-08-20 05:49 UTC |
| P5-05 Starlette bump | 🟡 partial | 未升 starlette≥1.0.1 | 兼容 FastAPI 0.115.12 |
| P5-06 mapped IPv6 | ✅ | `34c86b6` + `test_mapped_ipv6_loopback_is_restricted` + 2026-08-20 05:49 UTC |
| P5-07 audit sampler | ✅ | `34c86b6` + sampler `undo` on write fail + 2026-08-20 05:49 UTC |
| P5-08 body cap | ✅ | `34c86b6` + Content-Length middleware + 2026-08-20 05:49 UTC |
| P6-01 tautology | ✅ | `7bffb70` + 删 `or True` / 缺文件 fail + 2026-08-20 05:49 UTC |
| P6-02 ruff | ✅ | `f7bec3f` + `ruff check .` 0 + 2026-08-20 05:49 UTC |
| P6-03 CW unit | ✅ | `7bffb70` + probe false → skip + 2026-08-20 05:49 UTC |
| P6-04 wheel SQL | ✅ | `7bffb70` + `unzip -l dist/*.whl` 含 001–015 + 2026-08-20 05:49 UTC |
| P6-05 mega/soak/docs | 🟡 partial | sidecar soak 绿；mega 主链与 VF-ledger §6 待收口测试段 | 本文件底部续写 |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P1 短途+soak | `pytest tests/unit/test_ns5_uow_cancel.py tests/unit/test_ns5_sidecar_serial.py tests/unit/test_ns5_outbox_poison.py tests/unit/test_ns5_retirement_stuck.py tests/unit/test_ns5_phase1_runtime.py tests/integration/test_ns4_cw_soak.py` | PASS | T01–T10 T61 |
| P2 持久化 | `pytest tests/unit/test_ns5_phase2.py tests/unit/test_turso_driver.py tests/unit/test_d04_write_paths.py` | PASS | T11–T19 |
| P3 车道 | `pytest tests/unit/test_ns5_phase3.py tests/unit/test_claude_cli_port.py tests/unit/test_inference_runtime.py` | PASS | T20–T29 子集 |
| P4 serving | `pytest tests/unit/test_ns5_phase4.py tests/unit/test_adopt_layered_json.py tests/unit/test_retrieval_service.py` | PASS | T30–T47 子集 |
| P5 安全 | `pytest tests/unit/test_ns5_phase5.py tests/unit/test_security_boundary.py` | PASS | T48–T55 子集 |
| P6 静态/包装 | `ruff check .`；`uv build`；`unzip -l dist/*.whl` | ruff 0；wheel 含 SQL | T56–T59 |
| 全量 pytest | 未跑完 441 | 待收口测试段 | VF86 明示 deferred |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| UoW 可再 BEGIN | NS5-T01 | `test_ns5_uow_cancel.py` PASS | ✅ PASS |
| sidecar 4×20 | NS5-T02 / T61 | ThreadPool 80 insert PASS | ✅ PASS |
| outbox 不冻 | NS5-T05 | poison dead + drain 继续 | ✅ PASS |
| heartbeat 无双跑 | NS5-T04 | lease=1s sleep=1.2s recover=0 | ✅ PASS |
| vectorize fail-closed | NS5-T30 | 超预算不再缩 required_units | ✅ PASS |
| extras / XFF | NS5-T50 / T48 | camelCase 拒；XFF 规则落地 | ✅ PASS |
| wheel SQL | NS5-T59 | 001–015 在 wheel 内 | ✅ PASS |
| ruff 0 | NS5-T57 | `ruff check .` 0 | ✅ PASS |
| 主链 mega | NS5-T60 | 代码完成后、本段测试前未复跑 e2e mega | ⏸ PENDING |
| 全量 pytest | 禁止当 DoD | VF86 | ⏸ PENDING / deferred |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| VF86 sqlite3 e2e | `B` | owner-gated | NS1-V11 harness charter | owner |
| VF23 billing | `A` | always-permit | billing AP | owner |
| VF97 browser/OCR/Vision | `A` | README 未接线 | capability charter | owner |
| VF88 live GPU | `A` | 本轮 stub | NS2-GPU | owner |
| VF37.r 生产切 stub | `C` | stub 仍可默认 | 后继 charter | 下游 |
| VF46.r 全程 jsonschema | `C` | layered UUID 未全补 | 后继 | 下游 |
| VF41.r S06 全树 | `C` | 两节点诚实 | 后继 | 下游 |
| VF30.r 完整 PDF 库 | `C` | 仅去 latin-1 | 后继 | 下游 |
| VF66.r 目录 CAS SSOT | `A` | T-O-120 | owner 授权 | owner |
| VF91.r 真机 CW e2e | `C` | unit skipIf | NS4 constitution e2e | 下游 |
| P3-06/08/10 余项 | `C` | partial | 后继 AP | 下游 |
| P5-05 Starlette≥1.0.1 | `C` | 未升主版本 | FastAPI 升级窗口 | 下游 |
| VF-ledger §6 回填 | `C` | 未 append | 测试段完成后 | 本 closure 底部 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ✅ |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ⚠ 代码执行段已按 Phase commit；全量测试段前未再跑 `git diff --stat` 终检 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| ✅ |

P1–P6 代码项的 ✅ 归类为 **observed-OK-at-closure**（短途/unit/ruff/wheel；非 live soak 长跑）。mega T60 标 ⏸。VF86 标 deferred。

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| P1–P6 代码在 main 可回滚提交 | ✅ | `d728d0b`…`f7bec3f` |
| 短途 NS5-T01–T59 子集绿 | ✅ | 见 §2 |
| mega T60 / 全量 pytest | ⏸ | 本文件测试段补 |
| VF-ledger §6 append | ⏸ | 测试段后 |
| 干净 wheel migrate | ⏸ | 测试段 destroy/rebuild |

**下阶段 kickoff checklist**：
- [ ] 引用本 closure 作为 single truth anchor
- [ ] 消化 P3/P4 partial 切片或显式转后继 AP
- [ ] 不要把 VF86 红当成生产行为已证明

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| `[true-bug]` 未改写成 deferred | ✅ 保持 | AP §6；ledger 未改 §0–§5 |
| VF62 重叠 run_once 未在无心跳时打开 | ✅ 保持 | `allow_overlapping_run_once=False` |
| 业务连接不切 journal_mode | ✅ 保持 | 探针旁路；sidecar IMMEDIATE |
| S09 complete-set proof | ✅ 保持 | vectorize 不缩 required；禁单通道 purge |
| 不新写 sqlite3 打开 Turso | ✅ 保持 | P6 未加此类检查 |
| S16 默认不盲信 XFF | ✅ 保持 | empty CIDR + private peer 用 XFF 外网身份 |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `r1` | 2026-08-20 | Grok | 代码执行段初闭合；测试段待底部续写 |
