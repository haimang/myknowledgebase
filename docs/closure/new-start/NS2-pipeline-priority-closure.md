# [NS2 / Pipeline Priority Dispatch] Closure

> 阶段: `MKB/NS2 — Pipeline Priority & Dispatch Capacity Orchestration`
> 范围: `NS2-P1–P6 全部 6 个 Phase`
> Close-type: `close-with-known-issues`
> 状态: `close-with-known-issues`
> 日期: `2026-08-15` · 作者: `Antigravity`
> 关联 charter: `docs/plan/new-start/NS2-pipeline-priority.todo.md`
> 关联 action-plan: `docs/plan/new-start/NS2-pipeline-priority.md`
> 关联 evidence: `inline §2`
> 关联 baseline/truth: `S03-workflow-engine.md`, `S11-inference-runtime.md`, `D04-turso-physical-schema.md`

---

## 0. 一句话 verdict

> NS2 的全部 6 个 Phase（契约重构、DDL 物理列扩展、Orchestrator 同事务原子 admit 与分池 claim、生成端点与 Qwen/Claude `-p` salvage 接线、向量化并发与 FIFO、Mega 穷举与 Soak 浸泡测试）均已完整交付并严格验证通过。除继承自 NS1 的既有 pyturso raw sqlite file 并发测试读取波动（VF V11）外，NS2 全部调度与流水线优先级功能 100% 达成。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + runtime） |
|------|------|--------------------------------|
| `P1-01..P1-06` 契约重命名（`local-inference`）、三池容量常量、`choose_pool` 纯策略、BillingPort 协议、L2 快照扩展 | ✅ closed | `(2f90a35, 5b1e9ed + tests/unit/test_dispatch_policy.py, test_compression_channel.py 全绿)` |
| `P2-01..P2-04` DDL 迁移 011、`dispatch_pool` / `dispatch_admitted` 物理列及索引、`get_pool_occupancies`、领域事件 | ✅ closed | `(ff6b3e6, 2e4d073 + tests/unit/test_dispatch_ddl.py, test_dispatch_occupancy.py 全绿)` |
| `P3-01..P3-05` Orchestrator 同事务原子 admit、分池 `claim_next`、embed FIFO 排序、超时拦截、worker 零 sleep | ✅ closed | `(8604fc5, a1be4d0 + tests/unit/test_dispatch_claim.py 7 passed)` |
| `P4-01..P4-04` 生成接线（`generation_construct.py`）、`ProcessCommand.dispatch_pool`、Qwen 参数守卫、Claude `-p` salvage receipt、16k 字符预算溢流 | ✅ closed | `(9dc2357, d1d716d + tests/unit/test_dispatch_generation.py 4 passed)` |
| `P5-01..P5-04` 向量化池化（`lsrag.vectorize` 入 embed 池）、8+20 并发与 FIFO、InferenceFacade 末闸 12 与背压可恢复性 | ✅ closed | `(a3d7355 + tests/unit/test_dispatch_embed_and_gates.py 3 passed)` |
| `P6-01..P6-03` Mega 矩阵穷举测试、Soak 并发浸泡测试、全量回归与静态检查 | ✅ closed | `(tests/unit/test_dispatch_mega.py 2 passed, 298 unit/domain passed, ruff clean)` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| P1 契约与策略 | `uv run pytest tests/unit/test_dispatch_policy.py tests/unit/test_compression_channel.py` | PASS, 100% | `local-inference` 命名，3 池容量常量，`choose_pool` 纯策略 |
| P2 DDL 与容量感知 | `uv run pytest tests/unit/test_dispatch_ddl.py tests/unit/test_dispatch_occupancy.py` | PASS, 100% | 011 迁移，物理列，部分索引，`get_pool_occupancies` |
| P3 Orchestrator admit & claim | `uv run pytest tests/unit/test_dispatch_claim.py` | PASS, 7 passed | 同事务原子 admit，分池 claim，embed FIFO，超时拦截 |
| P4 生成执行与 salvage | `uv run pytest tests/unit/test_dispatch_generation.py` | PASS, 4 passed | Qwen JSON 参数防护，Claude `-p` 单次兜底，salvage receipt 审计 |
| P5 向量化与门闸 | `uv run pytest tests/unit/test_dispatch_embed_and_gates.py` | PASS, 3 passed | embed 池化，FIFO 保序，ConcurrencyGate 12/8/2/2，背压恢复 |
| P6 Mega 矩阵与 Soak | `uv run pytest tests/unit/test_dispatch_mega.py` | PASS, 2 passed | 4 优先级 × 4 状态纯策略穷举矩阵，50 并发混合 claim 浸泡 |
| 完整 unit & domain 回归 | `uv run pytest tests/unit/ tests/domain/` | PASS, 298 passed in 15.97s | 全量单元测试与领域架构守卫 |
| 代码静态扫描 | `uv run ruff check` | PASS, 0 warnings/errors | 仓库全局无 lint/format 违例 |
| 架构守卫测试 | `uv run pytest tests/domain/test_architecture.py` | PASS, 4 passed | 禁止代码中出现旧版 `api-inference` 标识 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| Gate 1: No api-inference | 生产源码与测试中禁止出现旧名称 `api-inference`（除向后兼容测试数据） | `test_no_api_inference_in_production_or_test_sources` 通过 | ✅ PASS |
| Gate 2: Same-transaction admission | 任务 admit 必须与 `claim_next` 在同一个数据库写事务内完成 | `_admit_waiting_processes_tx` 在 `claim_next` 事务内原子执行 | ✅ PASS |
| Gate 3: Pool capacity bounds | local <= 2(running)+6(queued), NI <= 2+4, embed <= 8+20 | 纯策略与数据库 occupancy 边界测试全部通过 | ✅ PASS |
| Gate 4: Embed FIFO invariant | embed 进程严格按 `available_at ASC, created_at ASC, process_uuid ASC` 领取，不被优先级插队 | `test_embed_fifo_claim_ignores_priority_rank` 通过 | ✅ PASS |
| Gate 5: Zero-sleep worker | worker 无槽或无可领任务时立即返回 `None` / `False`，绝不在内存中 sleep 等槽 | `claim_next` 零 sleep 立即退出 | ✅ PASS |
| Gate 6: Salvage once & receipt | local-inference 仅在失败时向 Claude `-p` 兜底 1 次，并记录 `salvage_from: "local-inference"` | `test_local_inference_failure_salvages_once_with_claude_cli` 通过 | ✅ PASS |
| Gate 7: Facade terminal gate | ConcurrencyGate 强制执行全局 12、embed 8、structured_generate 2、text_generate 2 | `test_facade_concurrency_gate_limits_and_backpressure` 通过 | ✅ PASS |

---

## 4. Known Issues & 残差说明

1. **Pyturso raw sqlite file direct inspection (VF V11 from NS1)**:
   - 若干直接通过外部 `sqlite3.connect` 打开正在被 pyturso 读写中的数据库文件的测试用例，偶发报 `disk I/O error` 或 `file is not a database`。此为已知环境缺陷，不影响业务逻辑。

---

## 5. 结论

NS2 全部 6 个 Phase 任务严格按照 DAG 依赖串行执行完毕，所有核心调度策略、并发门闸、持久化 DDL 以及端到端测试均验证通过。本阶段正式收口。
