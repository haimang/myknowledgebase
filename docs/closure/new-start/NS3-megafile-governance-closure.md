# [NS3 / Capability-boundary extraction] Closure

> 阶段: `MKB/NS3 — S06/S07 leaf extraction and compiler package split`
> 范围: `NS3-P1–P5 全部 5 个 Phase`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed-with-explicit-deferrals`
> 日期: `2026-08-15` · 作者: `Grok`
> 关联 charter: `N/A`
> 关联 design: `N/A`
> 关联 action-plan: `docs/plan/new-start/NS3-megafile-governance.md`
> 关联 evidence: `inline §2`
> 关联 review: `N/A`

---

## 0. 一句话 verdict

> NS3 按 S06/S07 能力边界抽出无 I/O 叶服务、compiler 收成稳定公开面的包、architecture 锁死错误拆法；去 Mixin / YAML 工作流 / `_accept_snapshot` 拆分 / 行数闸显式 defer。

---

## 1. 工作项收口表

| Item | 五态 | 证据（commit + test + run-time） |
|------|------|--------------------------------|
| `P1-01` 错误拆法守卫 | `verified` | `e29e293` + `tests/domain/test_architecture.py` NS3 守卫 + 2026-08-15 10:54 UTC |
| `P1-02` 组合根冻结 | `verified` | `e29e293` + T04/T05/T07 + 2026-08-15 10:54 UTC |
| `P2-01` `lsrag_structurize` 包 | `verified` | `5b9b265` + `test_lsrag_structurize_service.py` + 2026-08-15 10:54 UTC |
| `P2-02` `_structurize` 改调服务 | `verified` | `5b9b265` + Mixin 无 `adopt_layered_json_with_report` + 2026-08-15 10:54 UTC |
| `P2-03` P2 独立测试 | `verified` | `5b9b265` + P2 短途 + `test_ns1_pipeline.py` + 2026-08-15 10:54 UTC |
| `P3-01` `lsrag_construct` 包 | `verified` | `32523c8` + `test_lsrag_construct_service.py` + 2026-08-15 10:54 UTC |
| `P3-02` `_construct` / reconstruct 接线 | `verified` | `32523c8` + 无 `compiler.construct(` + salvage 回归 + 2026-08-15 10:54 UTC |
| `P3-03` P3 独立测试 | `verified` | `32523c8` + P3 短途 + NS1/generation e2e + 2026-08-15 10:54 UTC |
| `P4-01` compiler 收成包 | `verified` | `0451e90` + `test_lsrag_compiler.py` / `test_lsrag_compiler_package.py` + 2026-08-15 10:54 UTC |
| `P4-02` P4 独立测试 | `verified` | `0451e90` + compiler 金样 0 差 + 2026-08-15 10:54 UTC |
| `P5-01` mega / soak / 回归 | `verified` | NS1 + NS2 lanes + generation e2e + soak + dispatch 短途 + 2026-08-15 10:54 UTC |
| `P5-02` S06/S07 路径窄回填 | `verified` | S06-E01 / S07-E01 各一句「已落地」+ 2026-08-15 10:54 UTC |
| `P5-03` NS3 closure | `verified` | 本文件；无 LOC 成功句；无 `D-MEGA` ledger |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P1 守卫 | `uv run pytest tests/domain/test_architecture.py tests/unit/test_dispatch_policy.py` | PASS | T01–T08 |
| P2 短途 | `uv run pytest tests/unit/test_lsrag_structurize_service.py tests/unit/test_lsrag_compiler.py tests/unit/test_adopt_layered_json.py tests/unit/test_layered_schema.py tests/unit/test_ns1_generation_cli.py tests/domain/test_architecture.py` | PASS | T10–T25 |
| P2 出闸 | `uv run pytest tests/e2e/test_ns1_pipeline.py` | PASS | T23 |
| P3 短途 | `uv run pytest tests/unit/test_lsrag_construct_service.py tests/unit/test_dispatch_generation.py tests/unit/test_compression_channel.py tests/unit/test_lsrag_structurize_service.py tests/unit/test_lsrag_compiler.py tests/domain/test_architecture.py` | PASS | T30–T46 |
| P3 出闸 | `uv run pytest tests/e2e/test_ns1_pipeline.py tests/e2e/test_generation_pipeline_contracts.py` | PASS | T42 T48 |
| P4 短途 | `uv run pytest tests/unit/test_lsrag_compiler.py tests/unit/test_lsrag_compiler_package.py tests/unit/test_adopt_layered_json.py tests/unit/test_layered_schema.py tests/unit/test_lsrag_structurize_service.py tests/unit/test_lsrag_construct_service.py tests/domain/test_architecture.py` | PASS | T50–T58 |
| P5 mega | `uv run pytest tests/e2e/test_ns1_pipeline.py tests/e2e/test_ns2_dispatch_lanes.py tests/e2e/test_generation_pipeline_contracts.py` | PASS | T60–T62 |
| P5 soak / NS2 | `uv run pytest tests/unit/test_dispatch_admit_soak.py tests/unit/test_dispatch_claim.py tests/unit/test_dispatch_policy.py tests/unit/test_compression_channel.py` | PASS | T63 T70 T71 |
| ruff | `uv run ruff check src tests api` | 见 §2 终态跑法 | T66 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 五态 | 判定 |
|------|------|------|------|------|
| 1. NS1 金样 | T60 T23 T48 | `test_ns1_pipeline.py` PASS | `verified` | PASS |
| 2. NS2 车道与 soak | T61 T63 T71 | lanes + soak + claim 短途 PASS | `verified` | PASS |
| 3. generation 成员合同 | T62 T42 | `test_generation_pipeline_contracts.py` PASS | `verified` | PASS |
| 4. 服务无 I/O；salvage 在 Mixin；low 不升 NI | T14 T35 T39 T75 | 包 AST + `test_dispatch_generation.py` | `verified` | PASS |
| 5. 错误拆法守卫 | T01–T06 T65 T72 T73 | architecture NS3 守卫 PASS | `verified` | PASS |
| 6. compiler 公开面 0 差 | T50–T53 T18 | compiler 金样 + package 测 PASS | `verified` | PASS |
| 7. 诚实 closure 非 LOC | T68 T69 | 本文件无「>500 减少」句 | `verified` | PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 去 Mixin / 重写 `WorkflowRuntime` | `A` | OOS | owner 正式 reopen D03 | owner |
| YAML / Fluent 工作流 | `A` | OOS | reopen S03 | owner |
| `_accept_snapshot` 334L 拆分 | `A` | OOS | S04 charter | owner |
| 通用测试 Factory / 单测行数闸 | `A` | OOS | 不交后继 | — |
| Transactional Command 框架 | `A` | OOS | 已有 UoW + callback | — |
| `D-MEGA-*` ledger | `A` | 拒绝登记 | 非 NS2 defer | — |
| billing / cloud / GPU soak / VF V11 | `C` | 仍交 NS2 deferred | NS2 closure §4 | 既有承接方 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| ✅ in-scope 项均为 `verified`；OOS 进 §4 A |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ✅ |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| ✅ 生产改动限于 intake generation Mixin/artifacts + 三个 services 包 + architecture/新单测 + S06/S07 一句 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ 无 B 类主动 defer |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| N/A |

本阶段成功标准是能力边界落地与金样 0 差，**不是**文件行数下降。

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| S06/S07 叶服务可无 I/O 单测 | ✅ | `lsrag_structurize` / `lsrag_construct` |
| Mixin 仍为单一 `ProcessStageHandler` | ✅ | P1 守卫冻结 |
| NS2 三池 / salvage 未改 | ✅ | T61 T70 T71 |
| 无新表 / 无 `payload_extra` dispatch 态 | ✅ | NS2-T71 仍绿 |

**下阶段 kickoff checklist**：
- [ ] 引用本 closure 作为 single truth anchor
- [ ] 若动 acceptance TX，另开 S04 charter；不要沿用 NS3 行数叙事
- [ ] 不要把 Gemini eval 升格为下游 charter

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| Mixin 组合根 | ✅ 保持 | `test_ns3_workflow_runtime_mixin_root_is_frozen` / pipeline 守卫 |
| 无 YAML 工作流 | ✅ 保持 | `test_ns3_workflows_have_no_yaml_resources` |
| 无 `contracts/lsrag/models.py` | ✅ 保持 | `test_ns3_does_not_dump_compiler_ir_into_contracts_lsrag_models` |
| services 禁 llm_adapters / HTTP | ✅ 保持 | `test_services_do_not_reach_api_concrete_persistence_or_inference_transport` |
| NS2 generate keys | ✅ 保持 | `test_ns3_generate_process_keys_remain_classified` |
| salvage `low` 不升 NI | ✅ 保持 | `test_low_priority_local_failure_does_not_salvage_to_cli` |
| 无新 required 表 | ✅ 保持 | `test_ns2_dispatch_does_not_add_required_tables_or_payload_extra_keys` |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `r1` | `2026-08-15` | `Grok` | 初闭合 |
