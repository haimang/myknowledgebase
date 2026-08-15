# NS2 执行 Todo / DAG

> 依据：`docs/plan/new-start/NS2-pipeline-priority.md`
> 日志模板：`.adocs/code-execution-log.md`
> 收口模板：`.adocs/closure.md`
> 执行纪律：严格串行；前一 Phase 未完成、未测试、未回填日志、未分簇提交时，后一 Phase 保持 blocked。

## DAG 总线

```text
NS2-ENTRY
  └─> NS2-P1 (合同/枚举/端口)
        └─> NS2-P2 (DDL与占用会计)
              └─> NS2-P3 (Orchestrator admit + 分池 claim)
                    ├──> NS2-P4 (生成步接线)
                    └──> NS2-P5 (Embed 池接线)
                          └─> NS2-P6 (测试/文档/收口)
                                └─> NS2-CLOSURE (最终收口与阶段 closure)
```

并行仅允许在 P3 完成后的 P4 与 P5 之间，或同一 Phase 内部；每个 Phase 的退出条件必须全部满足：
1. STEP-1/STEP-2 上下文已重新读取并记录。
2. 本 Phase 的全部工作项、测试、审查修复已完成。
3. 工作日志已按 `.adocs/code-execution-log.md` 追加到 action-plan 底部。
4. 本 Phase 已完成分簇 commit，且 commit 后测试重新运行。

---

## NS2-ENTRY — 准备工作

- [x] 读取 NS2 action-plan 全文 (`docs/plan/new-start/NS2-pipeline-priority.md`)。
- [x] 读取冻结真相层及引用锚区（`T-O-353..361`，S03/S11/D04 锚）。
- [x] 确认禁止项（§7.2 反例 ledger ⛔1..⛔15）。

---

## NS2-P1 — 合同、枚举、端口

**Block：NS2-P1 已完成；NS2-P2 已解锁。**

- [x] `P1-01 / NS2-T01/T02`：通道枚举硬切（`api-inference` 改为 `local-inference`，预留 `cloud-inference` 但禁生产公开输入），清理仓内生产代码旧名。
- [x] `P1-02 / NS2-T03/T04/T05`：新增纯函数调度策略模块 `src/runtime/workflow/dispatch.py`（占用常数、`choose_pool`、`pool_kind`）。
- [x] `P1-03 / NS2-T06`：snapshot 冻结派生通道（`channel_source: priority|explicit`，无显式字段时不默认 NI 而是派生）。
- [x] `P1-04 / NS2-T07`：新增 BillingPort 恒真门闩 `src/services/billing.py`。
- [x] `P1-05 / NS2-T08`：`registry.py` 中 Qwen 提升为 generate winner（priority=5），Lightning 为 10。
- [x] `P1-06 / NS2-T09`：占用常数进 Settings，Facade 全局闸上调为末闸（≥12）。
- [x] STEP-1：重新拉取 P1 涉及的全部上下文文件与引用。
- [x] STEP-2：通过 reference 锚定，重新拉取 S03/S11/S14/D04 等真相层文件。
- [x] STEP-3：开发、单元测试（`NS2-T01..T09`）、审查和修复。
- [x] STEP-4：按模板回填 P1 工作日志至 action-plan 底部。
- [x] STEP-6：分簇提交 P1（contracts/enums/billing/registry/tests）。
- [x] P1 EXIT：所有 P1 tests 绿，commit 后重跑，P2 解锁。

---

## NS2-P2 — DDL 与占用会计

**Block：NS2-P2 已完成；NS2-P3 已解锁。**

- [x] `P2-01 / NS2-T10`：新增 migration `011_process_dispatch_pools.sql`，给 `mkb_processes` 增加 `dispatch_pool`、`dispatch_admitted`、`dispatch_enqueued_at` 列及索引。
- [x] `P2-02 / NS2-T11`：实现 occupancy 占用查询纯函数 / SQL helper（`running`, `queued`, `waiting` 定义）。
- [x] `P2-03 / NS2-T12`：`events.py` 登记 `process.dispatch_admitted` 事件类型并做负载校验。
- [x] `P2-04 / NS2-T13`：Process 物化默认 `dispatch_admitted=0`，`process_spec_digest` 不含 pool。
- [x] STEP-1：重新拉取 P2 上下文（`001_initial.sql`, `004_*.sql`, `runtime_materialize.py`, `events.py`）。
- [x] STEP-2：重新拉取 D04 真相，确认禁止 `payload_extra` 承载 state。
- [x] STEP-3：开发、DDL 与 occupancy 测试（`NS2-T10..T13`）、审查和修复。
- [x] STEP-4：按模板追加 P2 工作日志。
- [x] STEP-6：分簇提交 P2（migration/occupancy/events/materialize/tests）。
- [x] P2 EXIT：P2 tests 绿，P3 解锁。

---

## NS2-P3 — Orchestrator admit + 分池 claim

**Block：NS2-P3 已完成；NS2-P4 / NS2-P5 已解锁（可并行）。**

- [x] `P3-01 / NS2-T20/T21/T22`：同事务 admit 算法（在 `claim_next` 事务内对 waiting 做 admit；按策略赋 `dispatch_pool`，置 `dispatch_admitted=1`，记 `process.dispatch_admitted`；满员或无配额保持 `admitted=0` 留在 orchestrator）。
- [x] `P3-02 / NS2-T23/T24`：分池 `claim_next`（未 admit 永不被 claim；unpooled 保持 S03 排序；local/NI 仅 claim 已 admit 且 running 未满行）。
- [x] `P3-03 / NS2-T25`：embed FIFO claim（embed 分支去除 `priority_rank`，按 `available_at ASC, created_at ASC, process_uuid ASC` 领取）。
- [x] `P3-04 / NS2-T26`：orchestrator waiting 仍受 deadline 约束（`admitted=0` 到期变 failed，错误码 `deadline-exceeded-before-start`）。
- [x] `P3-05 / NS2-T27`：worker 不睡租约（`run_once` 在无槽或无可领任务时立即退出）。
- [x] STEP-1：重新拉取 P3 上下文（`runtime_core.py`, `worker.py`, `facade.py`）。
- [x] STEP-2：重新拉取 S03 claim 序真相（S03:854-866）及 `T-O-353..361`。
- [x] STEP-3：开发、orchestrator 与 claim 测试（`NS2-T20..T27`）、审查和修复。
- [x] STEP-4：按模板追加 P3 工作日志。
- [x] STEP-6：分簇提交 P3（admit 算法/claim 逻辑/FIFO/tests）。
- [x] P3 EXIT：P3 tests 绿，P4/P5 解锁。

---

## NS2-P4 — 生成执行接线（Qwen / Claude -p / 预算分流）

**Block：NS2-P4 已完成。**

- [x] `P4-01 / NS2-T30/T31/T32`：接线 `generation_construct.py`（local 走 Local vLLM/Qwen，salvage 仅限 Claude `-p` 兜底 1 次；NI 走 Claude `-p` 无 local 回落；记录 receipt）。
- [x] `P4-02 / NS2-T33`：接线其他生成 stage（`lsrag.transcribe_markdown`, `lsrag.structurize`, `clean.extract.*` 等根据 dispatch_pool 分发）。
- [x] `P4-03 / NS2-T34`：`LocalVllmAdapter` 入参保持 system + user prompt + `response_format={"type": "json_object"}`，严禁传 `max_tokens` / `enable_thinking`，出参过滤 `reasoning`。
- [x] `P4-04 / NS2-T35`：超长 JSON 预算分流（normal >16k chars 分流至 NI，low >16k 保持 local）。
- [x] STEP-1：重新拉取 P4 上下文（`generation_construct.py`, `pipeline.py`, `local_vllm.py`）。
- [x] STEP-2：重新拉取 S07/S11 真相，确认 Qwen 适配器参数规范。
- [x] STEP-3：开发、生成与 salvage 测试（`NS2-T30..T35`）、审查和修复。
- [x] STEP-4：按模板追加 P4 工作日志。
- [x] STEP-6：分簇提交 P4（generation wiring/Qwen payload/salvage receipt/tests）。
- [x] P4 EXIT：P4 tests 绿，P4 收口。

---

## NS2-P5 — 向量化接线与门闸收敛

**Block：NS2-P5 已完成；NS2-P6 已解锁。**

- [x] `P5-01 / NS2-T50`：`vectorize` 步池化（`lsrag.vectorize` 在 live 模式进 `embed` 池，deterministic 不入池）。
- [x] `P5-02 / NS2-T51`：向量化并发与 FIFO（running 上限 8，queued 上限 20；无优先级权重，纯 FIFO 先到先得）。
- [x] `P5-03 / NS2-T52`：InferenceFacade 末闸（`max_in_flight=12`，`embed=8`，`structured_generate=2`，`text_generate=2`；S11 非阻塞拒绝与指标）。
- [x] `P5-04 / NS2-T53`：背压可恢复性（Facade 满闸时立即返回 `BACKPRESSURE`，不影响 orchestrator 的 durable 状态，下个 tick 或租约恢复后可继续）。
- [x] STEP-1：重新拉取 P5 上下文（`vectorize.py`, `facade.py`, `dispatch.py`）。
- [x] STEP-2：重新拉取 S08/S11 真相，确认 embed 适配器与 Facade 闸门参数。
- [x] STEP-3：开发、向量化与门闸测试（`NS2-T50..T53`）、审查和修复。
- [x] STEP-4：按模板追加 P5 工作日志。
- [x] STEP-6：分簇提交 P5（vectorize wiring/facade gate/backpressure/tests）。
- [x] P5 EXIT：P5 tests 绿，P6 解锁。

---

## NS2-P6 — 测试、文档与全量收口

**Block：NS2 全部 6 个 Phase 均已完成。**

- [x] `P6-01`：短途与集成测试台账（`NS2-T01..T54` 全绿）。
- [x] `P6-02 / NS2-T60/T61/T62`：e2e 四车道旅程、NS1 金样回归、embed FIFO 旅程。
- [x] `P6-03 / NS2-T70`：soak 32 并发 claim 竞态无超卖测试。
- [x] `P6-04 / NS2-T71`：domain 架构守卫（无新表、无 extra 派发态）。
- [x] `P6-05`：真相文档窄回填附录（S02/S03/S11/S14/S15/D04）。
- [x] `P6-06 / NS2-T72`：输出最终阶段 closure 至 `docs/closure/new-start/NS2-pipeline-priority-closure.md`。
- [x] STEP-1：拉取全量测试和文档上下文。
- [x] STEP-2：核对 §10 所有收口硬闸。
- [x] STEP-3：运行全量 pytest、ruff、静态扫描。
- [x] STEP-4：完成 action-plan §11 执行日志回填并改状态为 `executed`。
- [x] STEP-6：分簇提交 P6（e2e/soak/guards/docs/closure）。
- [x] P6 EXIT：NS2 收口完成，汇报用户。
