# [NS2 / Pipeline Priority Dispatch] Closure

> 阶段: `MKB/NS2 — Pipeline Priority & Dispatch Capacity Orchestration`
> 范围: `NS2-P1–P6 全部 6 个 Phase`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed-with-explicit-deferrals`
> 日期: `2026-08-15` · 作者: `Grok`
> 关联 charter: `docs/plan/new-start/NS2-pipeline-priority.todo.md`
> 关联 design: `N/A`
> 关联 action-plan: `docs/plan/new-start/NS2-pipeline-priority.md`
> 关联 evidence: `inline §2`
> 关联 review: `docs/code-review/new-start/NS2-review-VF-ledger.md`

---

## 0. 一句话 verdict

> NS2 三池 admit/claim、priority 双用到生成运输、salvage 按车道、指定 e2e/soak 与合规 closure 已落地；billing 真接口、cloud 路由、真机 GPU 争用、VF V11、urgent 老化显式 defer。

---

## 1. 工作项收口表

| Item | 五态 | 证据（commit + test + run-time） |
|------|------|--------------------------------|
| `P1-01` 通道硬切 | `verified` | `tests/unit/test_compression_channel.py` + `tests/domain/test_architecture.py::test_no_api_inference_in_production_or_test_sources` · 2026-08-15 |
| `P1-02` 纯策略 | `verified` | `tests/unit/test_dispatch_policy.py` · 2026-08-15 |
| `P1-03` snapshot 派生 | `verified` | `_resolve_compression_channel` + `_execution_payload` 写入派生通道 · `test_compression_channel.py` · 2026-08-15 |
| `P1-04` BillingPort | `verified` | `test_billing_false_blocks_ni_admission_for_urgent` (T07) · 2026-08-15 |
| `P1-05` Qwen winner | `verified` | `test_dispatch_generation.py` Qwen payload · 2026-08-15 |
| `P1-06` Settings / 末闸 | `verified` | `DispatchCaps.from_settings` 注入 `WorkflowRuntime`；facade 默认 12 · 2026-08-15 |
| `P2-01` 011/012 列与索引 | `verified` | `test_dispatch_ddl.py` fresh + 010→011 升级 · 2026-08-15 |
| `P2-02` occupancy | `verified` | `test_dispatch_occupancy.py`；waiting 只计需要池的 process_key · 2026-08-15 |
| `P2-03` 事件 | `verified` | payload=`pool/priority/channel_source` · `test_observability_contracts.py` · 2026-08-15 |
| `P2-04` 物化未 admit | `verified` | `test_workflow_runtime.py` · 2026-08-15 |
| `P3-01` 同事务 admit 封顶 | `verified` | `test_dispatch_claim.py` + soak T70 · 2026-08-15 |
| `P3-02` 分池 claim | `verified` | 未 admit 不领；generate 与 embed 独立选择 · 2026-08-15 |
| `P3-03` embed FIFO | `verified` | embed 之间 FIFO；与 generate 按 `available_at` 二选一 · 2026-08-15 |
| `P3-04` waiting deadline | `verified` | `test_unadmitted_waiting_process_fails_on_deadline_elapsed` · 2026-08-15 |
| `P3-05` 不睡租约 | `verified` | worker 无槽立即返回 · 2026-08-15 |
| `P4-01` process_key 分类 | `verified` | `pool_kind` 表 · 2026-08-15 |
| `P4-02` 车道表 | `verified` | 纯函数 + 行上 admit · 2026-08-15 |
| `P4-03` 超预算 | `verified` | `choose_pool(over_budget=)` 接入 admit；structurize/llm-clean 用 audit `size_bytes` · 2026-08-15 |
| `P4-04` salvage 按车道 | `verified` | T36 + T37 low 禁 CLI · 2026-08-15 |
| `P4-05` 显式覆盖 + 审计 | `verified` | T38 `config.compression_channel_override` · 2026-08-15 |
| `P4-06` receipt 改名 | `verified` | `salvage_from=local-inference` · 2026-08-15 |
| `P4-07` 离线 normal 溢 NI | `verified` | e2e lanes + NS1 金样 · 2026-08-15 |
| `P5-01` live vectorize 分类 | `verified` | snapshot / `live_inference` 合成 L2 · 2026-08-15 |
| `P5-02` 整段占槽 | `verified` | 一 Process 一 orchestrator 槽 · 2026-08-15 |
| `P5-03` 确定性跳过 | `verified` | T52 `dispatch_pool IS NULL` · 2026-08-15 |
| `P5-04` embed 独立 | `verified` | T54 local running=2 仍领 embed · 2026-08-15 |
| `P6-01` 短途台账 | `verified` | `tests/unit/test_dispatch_*.py` + compression · 2026-08-15 |
| `P6-02` e2e 四车道 | `verified` | `tests/e2e/test_ns2_dispatch_lanes.py` · 2026-08-15 |
| `P6-03` soak | `verified` | `tests/unit/test_dispatch_admit_soak.py` 32×32 gather · 2026-08-15 |
| `P6-04` T71 守卫 | `verified` | `test_ns2_dispatch_does_not_add_required_tables_or_payload_extra_keys` · 2026-08-15 |
| `P6-05` 真相窄回填 | `verified` | S02/S03/S11/S14/S15/D04 附录 · 2026-08-15 |
| `P6-06` 合规 closure | `verified` | 本文件 · 2026-08-15 |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 策略 / DDL / occupancy / claim | `uv run pytest tests/unit/test_dispatch_*.py tests/unit/test_compression_channel.py` | PASS | P1–P5 短途 + T07/T37/T38/T52/T54 |
| 并发 soak | `uv run pytest tests/unit/test_dispatch_admit_soak.py` | PASS | T70 32 coroutine × 32 轮 |
| 四车道 e2e | `uv run pytest tests/e2e/test_ns2_dispatch_lanes.py` | PASS | T60/T62 行上 pool/admitted |
| NS1 金样 | `uv run pytest tests/e2e/test_ns1_pipeline.py` | PASS | T61 离线 stub |
| unit + domain | `uv run pytest tests/unit tests/domain` | PASS | 全短途回归 |
| ruff | `uv run ruff check src tests api` | PASS | 静态 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 五态 | 判定 |
|------|------|------|------|------|
| 1. 三池永不超卖 | T20 T21 T22 T70 | claim 单测 + soak gather | `verified` | PASS |
| 2. 未 admit 不领；不睡 | T23 T27 | claim WHERE admitted=1；worker 立即 False | `verified` | PASS |
| 3. 四车道 + low 禁 NI | T31–T37 T60 | policy + salvage T37 + e2e | `verified` | PASS |
| 4. embed FIFO 独立 | T25 T53 T54 | FIFO + local 满仍领 embed | `verified` | PASS |
| 5. NS1 金样 | T61 | `test_ns1_pipeline.py` | `verified` | PASS |
| 6. 无新表 / extra / api-inference | T02 T71 | architecture 守卫 | `verified` | PASS |
| 7. closure 五态 + A/B/C | T72 | 本文件 | `verified` | PASS |

---

## 4. Deferred ledger

### A — charter 未承诺（OOS）

| 项 | 说明 | 承接 |
|----|------|------|
| `cloud-inference` 适配器 / 路由 | 公开 Literal 拒绝；CHECK 拒绝写入 | cloud AP `T-O-358` |
| MiniMax 替换 Claude `-p` | NI 仍是 Claude CLI | 模型选型 charter |
| urgent 老化 | 仅 priority_rank 队头，无老化时钟 | 后继若 high 被饿死 |

### B — 本阶段主动 defer

| 项 | 说明 | reopen 触发器 |
|----|------|----------------|
| 表级状态耦合 CHECK | SQLite `ALTER` 无法廉价加表级 CHECK；写路径已清空非法 retry 组合 | 需要表重建或新引擎约束 |
| Turso 真机 010→011 | 本环境已覆盖 sqlite 010 fixture；无 Turso 升级 harness | 授权 Turso 升级窗口 |

### C — handoff

| 项 | 说明 | 承接 |
|----|------|------|
| 真实 billing 扣减 | 仅恒真 `BillingPort` | billing AP `T-O-357` |
| 真机 GPU soak | AP §8.4 明确不假装覆盖 | owner 手工 soak |
| VF V11 pyturso I/O | NS1 既有 harness 残差 | `NS1-V11` / harness charter |

---

## 5. 诚实收口 5 态

| 五态 | 本阶段条目 |
|------|------------|
| `verified` | P1–P6 上表全部 in-scope 项；§3 七条硬闸 |
| `observed-OK-at-closure` | 无 |
| `partial` | 无（V14 表级 CHECK / Turso 真机已进 §4 B，不标 PASS） |
| `未观察` | 真机 GPU 争用（§4 C） |
| `deferred` | §4 A/B/C |

---

## 6. 下游施工合同

1. 生成运输必须以 `ProcessCommand.dispatch_pool` 为 SSOT；禁止 handler 再从 omit payload 默认 NI。
2. admit 与 claim 必须在同一写事务；未 `dispatch_admitted=1` 的池化步不得被领取。
3. 派发态只活在 `mkb_processes` 列上，禁止 `payload_extra` 键名 `dispatch_*`，禁止为调度新建 required 表。
4. `low` 不得 salvage 到 NI；显式通道必须有 security audit。
5. retry_wait / lease recovery 必须清空 admission，promote 后重新竞争 queued cap。
6. facade 是末闸，不是三池 SSOT；改容量走 Settings → `DispatchCaps`。

---

## 7. 不可动清单

- 不把 `cloud-inference` 当泄洪池。
- 不把整份 intake 或每个 embed HTTP batch 当成 orchestrator 槽。
- 不改 Task.priority 封闭集，不公开新 lane 字段。
- 不把 VF V11 / 真机 GPU / 真实扣费写成已验证。
- 不在 worker / handler 里为等槽 `sleep`。
