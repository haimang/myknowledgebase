# [RW-C / live 接线脚手架] Closure

> 阶段: `real-wire/RW-C — 真实 live 接线（本轮=脚手架 + 占位槽 + 路由；真实 MLX 推理延后）`
> 范围: `RWC-01 退避/分类 · RWC-02 占位槽+维度守卫 · RWC-03 密钥构造注入 · RWC-04 mock↔live 路由一致；RWC-05/06 真实 live 延后`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/eval/real-wire/final-execution-plan-by-opus.md`（§6.C）
> 关联 design: `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 C）
> 关联 action-plan: `docs/action-plan/real-wire/RW-C-live-wiring.md`
> 关联 evidence: `inline §2`
> 关联 review: `inline（独立审查 → §5）`

---

## 0. 一句话 verdict

> RW-C 按 owner reframe 交付**可被真实接线的脚手架**（退避/重试 + 错误分类 + 真实 provider 占位槽 + 密钥构造注入脱敏 + mock↔live 路由一致性），全部 verified；**真实 MLX `complete`/`embed` 推理与 live smoke 显式 deferred 至 provider charter**，且本离线 Linux 环境无 MLX、不可跑（占位调用 fail-loud，closure 标 未观察）。274 passed + 1 xfailed，门禁 0 弱。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. 真实 MLX 推理未实装——`RealMLXLLMProvider.complete`/`RealMLXEmbedder.embed` 为 `ProviderDeferredError` 占位（provider charter + owner macOS 跑）。
> 2. live smoke / 预算护栏数值未落（无外部计费——本地 MLX；Q-RW-6 数值随 provider charter）。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| RWC-01 退避/重试 + 错误分类 | ✅ | commit `fec0bb3` + `test_rw_c_live_wiring.py::test_is_retryable_classification`/`_retry_recovers_after_transient`/`_non_retryable_immediate_raise`/`_exhausts_and_raises` PASS |
| RWC-02 真实 provider 占位槽 + 维度守卫 | ✅（scaffolding）| `…::test_real_mlx_llm_constructs_defers_on_call`/`_real_mlx_embedder_dimension_locked_1024` PASS（构造 ok / 推理 defer） |
| RWC-03 密钥构造注入 + 脱敏 | ✅ | `…::test_key_redacted_in_repr`/`_factory_injects_key_via_constructor_not_global` PASS（key 不入 repr） |
| RWC-04 mock↔live 路由一致性 | ✅（替身）| `…::test_mock_live_structural_parity` PASS（FakeLive 替身证契约） |
| RWC-01..04 工厂 mlx 槽路由 | ✅ | `test_rw_a_provider_base.py::test_factory_mlx_slot_constructs_defers_on_use` PASS |
| RWC-05 live smoke（owner-triggered） | ⏸ deferred | 真实 MLX 推理延后 + 离线 Linux 不可跑 → provider charter / owner macOS |
| RWC-06 live 接入手册 + live closure | ⏸ deferred | 同上 |
| 真实 MLX `complete`/`embed` 推理 | ⏸ 未观察 | 占位 `ProviderDeferredError`；本环境无 MLX |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| RW-C 单测 | `python3 -m pytest tests/unit/test_rw_c_live_wiring.py` | `9 passed` | RWC-01..04 脚手架 |
| 全量回归 | `python3 -m pytest` | `274 passed, 1 xfailed`（基线 265） | 全仓 |
| 断言强度门禁 | `python3 tools/scripts/check_assert_strength.py` | `51 文件 0 弱` | 防假绿 |
| 占位满足协议 | `isinstance(RealMLXLLMProvider(...), LLMProvider)` | True | RWC-02 |
| key 不泄漏 | `repr(provider)` 不含原始 key | 通过（攻击向量用例） | RWC-03/TR-5 |
| import 无循环 | `python3 -c "import provider_runtime, workflow_*..."` | OK | 装配层 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 退避/分类正确（可重试 vs 不可重试） | 429/5xx 重试；401/422 立即抛；默认保守不重试 | 4 retry 测 PASS | ✅ PASS |
| 占位槽构造 ok + 推理 fail-loud | 构造成功（路由接）；调用 `ProviderDeferredError` | PASS | ✅ PASS |
| 密钥不入日志/repr（TR-5/Q-RW-7） | 原始 key 不在 repr | 攻击向量用例 PASS | ✅ PASS |
| mock↔live 结构一致 | 同 `structurize_via_llm` 在 mock/FakeLive 下键集+section 形状一致 | PASS | ✅ PASS |
| 真实 MLX live smoke | 真实端到端 + owner 复核 | **未跑**（无 MLX/离线 Linux） | ⏸ PENDING（deferred → provider charter） |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 真实 MLX `complete`/`embed` 推理 | C | `ProviderDeferredError` 占位 | provider charter 实装；owner macOS/MLX 跑 | owner + 下游 |
| RWC-05 live smoke + 预算护栏数值 | C | 未跑（本地 MLX 无外部计费；数值待定） | provider charter（Q-RW-6） | owner |
| RWC-06 live 接入手册 + live closure | C | 未产 | provider charter | 下游 |
| 外部厂商 client（openai/anthropic/gemini） | A | 工厂构造即 deferred（非本地 MLX 方向，OOS） | 仅当方向改为外部厂商 | owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ —— RWC-01/03/04 + 工厂槽 = **verified**（commit+test+run-time）；RWC-02 = **verified（scaffolding 部分）**：构造/协议/守卫 verified，真实推理 = **未观察**（占位 defer，本环境不可跑）。 |
| ✅ 证据为四元组 | ✅ —— commit `fec0bb3` + 具名 test + 2026-06-01 10:42 UTC |
| scope diff 守卫 | ✅ —— 改动落在 provider_runtime（retry/real_provider/factory/__init__）+ tests；无越界 |
| deferred 已三分类且有承接位置 | ✅ —— §4 标 A/C，均带承接位置 + 触发条件 |
| owner-test/live 项未复测标 ⏸ | ✅ —— RWC-05/06 + 真实 MLX 推理标 ⏸ deferred / 未观察，无「我跑通了 live」式宣称 |

> **诚实说明**：RW-C **未交付真实 LLM/embedding 推理**，只交付其**外围脚手架与路由**（退避/分类/占位/key/切换契约）。真实 MLX 推理是 `ProviderDeferredError` 占位，本离线 Linux 环境无法验证（无 MLX/Apple Silicon）；mock↔live 一致性用 `_FakeLiveProvider` 替身证**契约**而非真实质量。不宣称 live 已验证。

---

## 6. Handoff / 下阶段（provider charter）entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| `LLMProvider`/`Embedder` 协议 + 工厂 mlx 槽 | ✅ | 实装时填 `RealMLX*.complete/embed` 即转真实 |
| 退避/重试/错误分类脚手架 | ✅ | 真实 client 直接包裹 `retry_with_backoff` |
| 密钥构造注入 + 脱敏 | ✅ | `.env`→Settings→构造；不入日志 |
| mock↔live 路由开关 | ✅ | `semantic_mode`/`llm_provider`/`mock_llm_responses_path` |
| MLX 运行时（macOS/Apple Silicon） | ⏸ | owner 环境；本 Linux 沙箱不可跑 |

**下阶段 kickoff checklist**：
- [ ] 引用 RW-A/B/C closure 作为 truth anchor
- [ ] provider charter 定具体 MLX 模型（LLM + 1024 维 embedding）+ 计费/护栏数值
- [ ] 实装 `RealMLXLLMProvider.complete`/`RealMLXEmbedder.embed` → 占位 defer 即转真实
- [ ] owner macOS 跑 live smoke（默认 skip lane）

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| 密钥不入仓/日志/repr（Q-RW-7/TR-5） | ✅ 保持 | 构造注入 + `redact_secret` + repr 脱敏；`.env` git-ignored |
| 非模块级全局 key 轮转（⛔ gemini.ts:96-132） | ✅ 保持 | `api_keys` 实例内持有 |
| 维度 1024（RWA-09 继承） | ✅ 保持 | `RealMLXEmbedder.dimension==1024` |
| degraded/延后 fail-loud + 机器可读 reason（TR-4） | ✅ 保持 | `ProviderDeferredError.reason` |
| 接口隔离 mock/live 同协议（TR-1） | ✅ 保持 | 占位 + FakeLive 均 isinstance `LLMProvider` |
| 默认不打外网（TR-5） | ✅ 保持 | 默认 mock；mlx 占位不发请求（占位 defer） |

---

## 修订历史

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| r1 | 2026-06-01 | Opus 4.8 | RW-C 初闭合（closed-with-explicit-deferrals；脚手架 verified，真实 MLX 推理 + live smoke deferred 至 provider charter，本环境未观察） |
