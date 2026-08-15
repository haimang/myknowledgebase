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

**Block：仅在 NS2-P1 EXIT 后解除；NS2-P3 blocked until P2 exit gate。**

- [ ] `P2-01 / NS2-T10`：新增 migration `011_process_dispatch_pools.sql`，给 `mkb_processes` 增加 `dispatch_pool`、`dispatch_admitted`、`dispatch_enqueued_at` 列及索引。
- [ ] `P2-02 / NS2-T11`：实现 occupancy 占用查询纯函数 / SQL helper（`running`, `queued`, `waiting` 定义）。
- [ ] `P2-03 / NS2-T12`：`events.py` 登记 `process.dispatch_admitted` 事件类型并做负载校验。
- [ ] `P2-04 / NS2-T13`：Process 物化默认 `dispatch_admitted=0`，`process_spec_digest` 不含 pool。
- [ ] STEP-1：重新拉取 P2 上下文（`001_initial.sql`, `004_*.sql`, `runtime_materialize.py`, `events.py`）。
- [ ] STEP-2：重新拉取 D04 真相，确认禁止 `payload_extra` 承载 state。
- [ ] STEP-3：开发、DDL 与 occupancy 测试（`NS2-T10..T13`）、审查和修复。
- [ ] STEP-4：按模板追加 P2 工作日志。
- [ ] STEP-6：分簇提交 P2（migration/occupancy/events/materialize/tests）。
- [ ] P2 EXIT：P2 tests 绿，P3 解锁。

---

## NS2-P3 — Orchestrator admit + 分池 claim

**Block：仅在 NS2-P2 EXIT 后解除；NS2-P4/P5 blocked until P3 exit gate。**

- [ ] `P3-01 / NS2-T20/T21/T22`：同事务 admit 算法（`claim_next` 内部在领取前对 waiting 做 admit，不超过各池 queued cap）。
- [ ] `P3-02 / NS2-T23/T24`：分池 `claim_next`（未 admit 永不 claim；unpooled 保持 S03 序；生成按池）。
- [ ] `P3-03 / NS2-T25`：embed FIFO claim（排序去除 `priority_rank`，先到先得）。
- [ ] `P3-04 / NS2-T26`：orchestrator waiting 仍受 deadline 约束（超时标记 `deadline-exceeded-before-start`）。
- [ ] `P3-05 / NS2-T27`：worker 不睡租约（无槽立即返回 False；facade BACKPRESSURE 作为末闸）。
- [ ] STEP-1：重新拉取 P3 上下文（`runtime_core.py`, `worker.py`, `facade.py`）。
- [ ] STEP-2：重新拉取 S03 claim 序真相及 `T-O-353..361`。
- [ ] STEP-3：开发、claim 逻辑测试（`NS2-T20..T27`）、审查和修复。
- [ ] STEP-4：按模板追加 P3 工作日志。
- [ ] STEP-6：分簇提交 P3（admit/claim/FIFO/worker/tests）。
- [ ] P3 EXIT：P3 tests 绿，P4 与 P5 解锁。

---

## NS2-P4 — 生成步接线

**Block：仅在 NS2-P3 EXIT 后解除；NS2-P6 blocked until P4+P5 exit gates。**

- [ ] `P4-01 / NS2-T30`：generate `process_key` 准确分类（LLM 步入池，确定性 clean 不入池）。
- [ ] `P4-02 / NS2-T31..T34`：车道派发表接线（urgent/high/normal/low 对应 local/NI 规则）。
- [ ] `P4-03 / NS2-T35`：长 json/clean 超预算视为溢流（`normal` 溢 NI，`low` 锁 local）。
- [ ] `P4-04 / NS2-T36/T37`：salvage 按车道重写（`normal` 可救一次 NI，`low` 严禁救 NI / 偷套餐）。
- [ ] `P4-05 / NS2-T38`：显式 `compression_channel` 覆盖与安全审计事件。
- [ ] `P4-06 / NS2-T39`：receipt / salvage_from 落地新通道名 `local-inference`。
- [ ] `P4-07 / NS2-T40`：local 不可用时 normal 溢 NI（离线 e2e 不 503）。
- [ ] STEP-1：重新拉取 P4 上下文（`generation_construct.py`, `clean_preflight.py`, `dispatch.py`）。
- [ ] STEP-2：重新拉取 S11/S16 威胁模型及 salvage 规则真相。
- [ ] STEP-3：开发、车道与 salvage 测试（`NS2-T30..T40`）、审查和修复。
- [ ] STEP-4：按模板追加 P4 工作日志。
- [ ] STEP-6：分簇提交 P4（generation wiring/salvage/audit/tests）。
- [ ] P4 EXIT：P4 tests 绿。

---

## NS2-P5 — Embed 池接线

**Block：仅在 NS2-P3 EXIT 后解除；NS2-P6 blocked until P4+P5 exit gates。**

- [ ] `P5-01 / NS2-T50`：live vectorize 分类入 embed 池（`lsrag.vectorize`）。
- [ ] `P5-02 / NS2-T51`：vectorize Process 整段占槽（一 Process 一槽，内部多 batch 不重复占槽）。
- [ ] `P5-03 / NS2-T52`：确定性向量化（`live_inference=false`）跳过池（unpooled）。
- [ ] `P5-04 / NS2-T53/T54`：embed 会计独立于生成池（满员不溢 NI，不与 local 抢槽）。
- [ ] STEP-1：重新拉取 P5 上下文（`vectorize.py`, `dispatch.py`, `lsrag_definition.py`）。
- [ ] STEP-2：重新拉取 S08/S11 真相，确认 embed 8+20 规则。
- [ ] STEP-3：开发、embed 池化测试（`NS2-T50..T54`）、审查和修复。
- [ ] STEP-4：按模板追加 P5 工作日志。
- [ ] STEP-6：分簇提交 P5（embed wiring/batch occupancy/tests）。
- [ ] P5 EXIT：P5 tests 绿。

---

## NS2-P6 — 测试、文档与全量收口

**Block：仅在 NS2-P4 EXIT 与 NS2-P5 EXIT 均满足后解除。**

- [ ] `P6-01`：短途与集成测试台账（`NS2-T01..T54` 全绿）。
- [ ] `P6-02 / NS2-T60/T61/T62`：e2e 四车道旅程、NS1 金样回归、embed FIFO 旅程。
- [ ] `P6-03 / NS2-T70`：soak 32 并发 claim 竞态无超卖测试。
- [ ] `P6-04 / NS2-T71`：domain 架构守卫（无新表、无 extra 派发态）。
- [ ] `P6-05`：真相文档窄回填附录（S02/S03/S11/S14/S15/D04）。
- [ ] `P6-06 / NS2-T72`：输出最终阶段 closure 至 `docs/closure/new-start/NS2-pipeline-priority-closure.md`。
- [ ] STEP-1：拉取全量测试和文档上下文。
- [ ] STEP-2：核对 §10 所有收口硬闸。
- [ ] STEP-3：运行全量 pytest、ruff、静态扫描。
- [ ] STEP-4：完成 action-plan §9 执行日志回填并改状态为 `executed`。
- [ ] STEP-6：分簇提交 P6（e2e/soak/guards/docs/closure）。
- [ ] P6 EXIT：NS2 收口完成，汇报用户。
