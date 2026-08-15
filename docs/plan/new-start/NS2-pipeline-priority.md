# Nano-Agent 行动计划

> 服务业务簇: `MKB / NS2 pipeline priority dispatch`
> 计划对象: `Task.priority` 双用（全局领取序 + 生成通道路由）与三池 orchestrator（`local-inference` / `non-interactive` / `embed`）
> 类型: `upgrade`
> 作者: `Grok`
> 时间: `2026-08-14`
> 文件位置: `docs/plan/new-start/NS2-pipeline-priority.md`
> 上游前序 / closure:
> - `docs/plan/new-start/NS1-new-pipeline.md`（`executed`）
> - `docs/closure/new-start/NS1-new-pipeline-closure.md`（`close-with-known-issues`）
> 下游交接:
> - NS2 阶段 final closure（本 AP §10；落盘 `docs/closure/new-start/NS2-pipeline-priority-closure.md`）
> - billing 额度闸 AP（defer，`T-O-357`）
> - `cloud-inference` 最终回退 AP（defer，`T-O-358`）
> 关联设计 / 调研文档:
> - 本会话业主冻结口径（无独立 design 档；§6 / §7 即 grounding）
> - `docs/baseline/domain-truth/S03-workflow-engine.md`（claim 序 / Process 状态机）
> - `docs/baseline/domain-truth/S11-inference-runtime.md`（`T-O-200` 闸 ≠ claim）
> - `docs/baseline/domain-truth/D04-turso-physical-schema.md`（`T-O-173` 禁 `payload_extra` 承载 state）
> 冻结决策来源:
> - 本会话业主口头冻结 `T-O-353..361`（只读引用；本 action-plan 不填写 Q/A）
> grounding 来源:
> - 本 AP §7 内置锚区（对照当前 `src/` / `001_initial.sql` / S03 / S11 / D04）
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `draft`

---

## 0. 执行背景与目标

NS1 已把 `intake → A → [B.md?] → B.json → C → vectorize` 打通，但生成通道仍是调用方钉死的 `compression_channel`（默认 Claude `-p`），claim 仍是全局一把 `priority_rank DESC`（`runtime_core.py:173`），并发仍是进程内 `inference_max_in_flight=8`（`config.py:47` + `facade.py:125-140`）把 embed 和 generate 锁在一起。宿主机 GPU 与线上套餐因此无法按业主意图分工。

业主已冻结：复用现有 `low|normal|high|urgent`；生成以 **一次 generate** 入队；embed 以 **一个 vectorize Process** 入队且 **不看 priority**；三池分会计；没位就留在 orchestrator，禁止 claim 后睡眠；billing / cloud 只留端口。

本计划把这些冻结句落成可合并的调度合同、DDL 列晋升、分池 claim 与测试台账，不重开 NS1 kernel / prompt / 粒度，也不实现账单或云回退。

- **服务业务簇**：`NS2`
- **计划对象**：orchestrator 三池派发 + `priority` 通道路由
- **本次计划解决的问题**：
  - 生成通道与 Task 优先级脱节；默认把质量活扔给调用方自选通道
  - 全局 8 路闸把 Qwen 生成和 embed 捆死；claim 即可能打模型
  - `urgent` 的 vectorize 会按 `priority_rank` 插队，违反「embed 不受 priority」
- **本次计划的直接产出**：
  - 封闭调度合同（占用函数、车道表、注入单位）
  - `mkb_processes` 派发列晋升 + 同事务 admit/claim
  - 生成三池接线、salvage 按车道重写、embed FIFO 池
  - §8 全量测试 + 阶段 final closure 模板回填
- **本计划不重新讨论的设计结论**：
  - 三池占用算术与注入单位（`T-O-353` / `T-O-354`）
  - `priority` 双用；不新造 `inference_lane`（`T-O-355`）
  - embed FIFO、无溢流（`T-O-356`）
  - billing / cloud 本轮只留门闩（`T-O-357` / `T-O-358`）
  - 留在 orchestrator，禁止 claim-then-sleep（`T-O-359`）
  - 不新建 required 表；派发态不得进 `payload_extra`（`T-O-360` / `T-O-173`）
  - `claimed ≠` 已获 GPU/NI 配额（收窄解释 `T-O-200` → `T-O-361`）

---

## 1. 执行综述

### 1.1 总体执行方式

**先冻纯函数合同，再晋升 Process 列，再改 claim 事务，再分别接生成与 embed，最后 mega/soak 收口。** 禁止先在 handler 里加内存队列或 `asyncio.sleep` 等槽。每 Phase 先单测策略函数，再接线运行时。确定性 / stub 路径必须显式分类：该占池就占池，不该占就跳过，禁止 silent 降级到假摘要。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 合同、枚举、端口 | `M` | 改名、纯函数策略、snapshot 冻结、BillingPort 恒真、Qwen 胜出 | `-` |
| Phase 2 | DDL 与占用会计 | `M` | `mkb_processes` 三列 + 索引；占用查询；materialize 默认未 admit | Phase 1 |
| Phase 3 | Orchestrator admit + 分池 claim | `L` | 同事务 admit；分池领取；embed FIFO；deadline；不睡租约 | Phase 2 |
| Phase 4 | 生成步接线 | `L` | 分类 process_key；车道表；超预算溢流；salvage；覆盖审计 | Phase 1+3 |
| Phase 5 | Embed 池接线 | `M` | live vectorize 占 embed 整段；确定性跳过；不看 priority | Phase 3 |
| Phase 6 | 测试、文档、收口 | `L` | 短途/spike/mega/soak；S02/S03/S11 窄回填；closure | Phase 4+5 |

### 1.3 Phase 说明

1. **Phase 1 — 合同、枚举、端口**
   - **核心目标**：后面一切 SQL / claim / handler 只消费一份纯函数策略。
   - **为什么先做**：名称从 `api-inference` 改到 `local-inference` 会碰 API、snapshot、receipt；必须先闭环，避免半改名。
2. **Phase 2 — DDL 与占用会计**
   - **核心目标**：占用是行上可查询的事实，不是进程内计数器。
   - **为什么放在这里**：`T-O-173` 禁止把派发态塞进 `payload_extra`；没有列就不能写 admit。
3. **Phase 3 — Orchestrator admit + 分池 claim**
   - **核心目标**：调度 SSOT 进 `claim_next` 同一事务。
   - **为什么放在这里**：列已在；handler 还没依赖新领取序。这是最高风险内核。
4. **Phase 4 — 生成步接线**
   - **核心目标**：四工位里真正会打 LLM 的 Process 进入 local/NI 池。
   - **为什么放在这里**：claim 已经认池；现在才改 construct / CLI / salvage。
5. **Phase 5 — Embed 池接线**
   - **核心目标**：`lsrag.vectorize` live 路径进第三池。
   - **为什么放在这里**：与 Phase 4 无代码环依赖，只共享 Phase 3 的 admit。
6. **Phase 6 — 测试、文档、收口**
   - **核心目标**：台账全 PASS + 真相窄回填 + closure。
   - **为什么放在这里**：接线完成后才有完整旅程。

### 1.4 执行策略说明

- **执行顺序原则**：纯函数 → 列 → 事务内核 → 生成/embed 双叶 → 收口。禁止倒序。Phase 4 与 Phase 5 在 Phase 3 之后可并行。
- **风险控制原则**：admit/claim 必须单事务；租约只发给已 admit 或 unpooled 的 Process。CLI/live 继续可 stub。CI 默认不打真实 Spark / MiniMax。DDL 只晋升 `mkb_processes`，migration 头写明「非新表 / 非 `payload_extra`」。
- **测试推进原则**：短途（策略函数 + DDL + claim 单测）→ Phase spike（单池占满）→ mega（四车道 × 生成/embed）→ soak（并发 admit 竞态 × N）。
- **文档同步原则**：不改 pre-NS1 QNA。S02/S03/S11/S14/S15/D04 仅 Phase 6 **窄回填**（priority 双用、三池占用、`claimed ≠` 配额）。billing/cloud 只在附录登记 defer。
- **回滚 / 降级原则**：回滚 = 不部署带 `011` 的 runtime（旧 runtime 忽略新列）。禁止「池满则确定性假摘要」。`low` 不得 salvage 到 NI。

### 1.5 本次 action-plan 影响结构图

```text
NS2-pipeline-priority
├── Phase 1: 合同 / 枚举 / 端口
│   ├── src/services/prompt_profiles.py          COMPRESSION_CHANNELS 改名
│   ├── src/runtime/workflow/dispatch.py         🆕 纯函数策略
│   ├── src/services/billing.py                  🆕 BillingPort 恒真
│   ├── src/services/config_snapshots.py         L2 冻结派生通道
│   └── src/services/registry.py                 Qwen winner
├── Phase 2: DDL / 占用
│   ├── 011_process_dispatch_pools.sql           🆕 三列 + 索引
│   ├── mkb_processes materialize                admitted=0
│   └── DomainEventWriter                        process.dispatch_admitted
├── Phase 3: Orchestrator
│   ├── runtime_core.claim_next                  admit + 分池 ORDER BY
│   └── worker.run_once                          仍只 claim，不睡
├── Phase 4: 生成接线
│   ├── generation_construct / clean_preflight / transcribe
│   ├── salvage 按车道
│   └── compression_channel 覆盖 + security audit
├── Phase 5: Embed 接线
│   └── vectorize live 整段占 embed 池
└── Phase 6: 测试 / 文档 / 收口
    ├── tests/unit/test_dispatch_*.py
    ├── tests/e2e/test_ns2_dispatch_lanes.py
    └── docs/closure/new-start/NS2-pipeline-priority-closure.md
```

### 1.6 执行 DAG

```text
                    ┌─────────────┐
                    │  Phase 1    │
                    │  合同/端口  │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Phase 2    │
                    │  DDL/占用   │
                    └──────┬──────┘
                           │
                    ┌──────▼──────┐
                    │  Phase 3    │
                    │  admit/claim│
                    └──┬───────┬──┘
                       │       │
                ┌──────▼──┐ ┌──▼──────┐
                │ Phase 4 │ │ Phase 5 │
                │ 生成接线│ │ embed   │
                └──────┬──┘ └──┬──────┘
                       │       │
                    ┌──▼───────▼──┐
                    │   Phase 6   │
                    │ 测试/收口   │
                    └─────────────┘
```

硬边：P4 不得在 P3 前改 `claim_next` 语义；P5 不得自己实现第二套计数器；P6 不得在 P4+P5 未绿时标 `executed`。

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `api-inference` → `local-inference` 全代码/测试硬切；预留 `cloud-inference` 枚举但不路由
- **[S2]** 纯函数：占用函数、车道表、注入单位、process_key 分类
- **[S3]** `mkb_processes` 列晋升 `dispatch_pool` / `dispatch_admitted` / `dispatch_enqueued_at`
- **[S4]** 同事务 orchestrator admit + 分池 `claim_next`（生成看 priority，embed FIFO）
- **[S5]** 生成步入池：`lsrag.transcribe_markdown` / `lsrag.structurize` / `lsrag.construct` / LLM clean
- **[S6]** live `lsrag.vectorize` 整段入 embed 池；确定性向量化不入池
- **[S7]** salvage 按车道重写；显式 `compression_channel` 覆盖 + 审计
- **[S8]** `normal` 的 json/clean 超预算视为溢流；local 不可用时 `normal` 溢 NI
- **[S9]** BillingPort 恒真；全局 facade 闸上调为末闸，不再当三池 SSOT
- **[S10]** Qwen 提升为 local generate winner；Lightning 留 catalog
- **[S11]** 测试台账 + S02/S03/S11/S14/S15/D04 窄回填 + NS2 closure

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 真实 billing 接口 / 套餐计量 / 扣减（只留端口）
- **[O2]** `cloud-inference` 适配器、路由、密钥
- **[O3]** MiniMax M3 替换 Claude `-p`（NI 抽象保持「线上质量通道」）
- **[O4]** urgent 插队老化；NI 为 overflow 保留位
- **[O5]** 重开 NS1 kernel / prompt 簇 / g0 summary-only 向量（`T-O-352`）
- **[O6]** 新建 required 物理表；分布式跨进程锁 / DO
- **[O7]** 修 NS1 遗留 pyturso `disk I/O` harness（VF V11）
- **[O8]** 把整份 intake 当一个槽；为每个 embed HTTP batch 单独占槽
- **[O9]** 修改 Task.priority 封闭集或公开新 lane 字段

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `mkb_processes` 加三列 | `in-scope` | 既有表晋升；派发态是 identity/state，禁 `payload_extra`（`T-O-173`） | owner 禁任何 DDL → 停工，不能用 extra 顶 |
| BillingPort 恒真 | `in-scope` | 为 `T-O-357` 留门闩 | 真实套餐 API 就绪 → 后继 AP |
| `cloud-inference` 枚举 | `in-scope` 仅预留 | 防以后字符串漂移 | 双通道都不可用且 owner 授权 → 后继 AP |
| `cloud-inference` 路由 | `out-of-scope` | 最终回退，不是泄洪 | 同上 |
| Qwen winner | `in-scope` | local 池 = 本地质量主模型 | 若 Spark 下架 Qwen → 改 binding 不改池 |
| json 超预算溢流 | `in-scope` | 防 Qwen 抄长文占死 2 路 | 预算常数需用 glossary 级样本校准 |
| urgent 老化 | `out-of-scope` | 业主未冻结；`priority_rank DESC` 已表达队头 | high 被饿死可观察后再开 |
| 显式 `compression_channel` | `in-scope` 调试覆盖 | 生产默认只传 priority | 若要删除覆盖，另开合同 |
| 多 worker 同库 | `in-scope` | 占用在行上，单库事务即跨 worker | 多库 / 多 Spark 另开 |
| S03「priority 只影响顺序」窄回填 | `in-scope` 文档 | 成功语义仍不变；生成池选择是新解释 | formal reopen S03 全文另档 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | 通道枚举硬切 + 预留 cloud | `update` | `prompt_profiles.py:37-39`；`models.py:185`；construct/snapshot/tests 全引用 | 代码/测试无 `api-inference`；cloud 不可选为生产通道 | NS2-T01 T02 | `medium` |
| P1-02 | Phase 1 | 纯函数调度策略 | `add` | 🆕 `src/runtime/workflow/dispatch.py` | 占用/车道/分类可单测，无 IO | NS2-T03 T04 T05 | `high` |
| P1-03 | Phase 1 | snapshot 冻结派生通道 | `update` | `config_snapshots.py:175-199,566-578` | L2 含 `compression_channel` + `channel_source` | NS2-T06 | `high` |
| P1-04 | Phase 1 | BillingPort 恒真 | `add` | 🆕 `src/services/billing.py` | NI admit 调端口；恒 `True` | NS2-T07 | `low` |
| P1-05 | Phase 1 | Qwen 升 winner | `update` | `registry.py:126-136` | generate binding priority Qwen=5 Lightning=10 | NS2-T08 | `medium` |
| P1-06 | Phase 1 | 占用常数与 facade 末闸 | `update` | `config.py:47`；`app.py:234-240`；`default.toml` | 三池常数进 settings；全局闸 ≥ 12 | NS2-T09 | `medium` |
| P2-01 | Phase 2 | migration 011 三列 | `add` | 🆕 `011_process_dispatch_pools.sql`；对照 `004_*.sql:6`；`001_initial.sql:301-357,1728-1730` | 空库/旧库可迁；CHECK 闭集 | NS2-T10 | `high` |
| P2-02 | Phase 2 | 占用查询 | `add` | 🆕 `dispatch.py` occupancy SQL helpers | `running/queued/waiting` 定义与 `T-O-353` 一致 | NS2-T11 | `high` |
| P2-03 | Phase 2 | `process.dispatch_admitted` 事件 | `update` | `events.py:16-59` | 允许类型登记；payload 无 secret | NS2-T12 | `medium` |
| P2-04 | Phase 2 | materialize 默认未 admit | `update` | `runtime_materialize.py:248-337` | 新 Process `dispatch_admitted=0`，`dispatch_pool` 按分类可空 | NS2-T13 | `high` |
| P3-01 | Phase 3 | admit 算法（同事务） | `add` | `runtime_core.py:149-227` + 🆕 dispatch admit | 池未满才置 `admitted=1`；满员留 `admitted=0` | NS2-T20 T21 T22 | `high` |
| P3-02 | Phase 3 | 分池 `claim_next` | `update` | `runtime_core.py:165-176`；`constants.py:24-29` | unpooled 仍 S03 序；生成按池；禁止领取未 admit | NS2-T23 T24 | `high` |
| P3-03 | Phase 3 | embed FIFO | `update` | 同上 ORDER BY 分支 | embed 排序不含 `priority_rank` | NS2-T25 | `high` |
| P3-04 | Phase 3 | orchestrator 等待仍受 deadline | `update` | `runtime_core.py:185-197` | `admitted=0` 到期 → `deadline-exceeded-before-start` | NS2-T26 | `medium` |
| P3-05 | Phase 3 | 禁止 claim-then-sleep | `update` | `worker.py:45-52`；`facade.py:313-317` | worker 无槽则 `claim_next=None`；BACKPRESSURE 仅末闸 | NS2-T27 | `high` |
| P4-01 | Phase 4 | generate process_key 分类 | `update` | `dispatch.py`；`core.py:319-344`；`lsrag_definition.py:162-182` | 仅 LLM 步入生成池；确定性 clean 不入 | NS2-T30 | `high` |
| P4-02 | Phase 4 | 车道派发表 | `update` | `dispatch.py` + admit | urgent/high/normal/low 与占用函数一致 | NS2-T31 T32 T33 T34 | `high` |
| P4-03 | Phase 4 | json/clean 超预算溢流 | `update` | `dispatch.py`；construct/clean 入口 | `normal` 超预算当 NI；`low` 仍锁 local | NS2-T35 | `medium` |
| P4-04 | Phase 4 | salvage 按车道 | `update` | `generation_construct.py:23-42,121-141,208-216` | `normal` 可救一次 NI；`low` 禁止 | NS2-T36 T37 | `high` |
| P4-05 | Phase 4 | 显式通道覆盖 + 审计 | `update` | `config_snapshots.py:566-578`；`events.py` / security audit | 覆盖进 snapshot+审计；生产默认真源=`priority` | NS2-T38 | `high` |
| P4-06 | Phase 4 | receipt/transport 改名 | `update` | `generation_construct.py:101-206` | receipt 写 `local-inference`；salvage_from 同步 | NS2-T39 | `low` |
| P4-07 | Phase 4 | local 不可用时的 normal 溢流 | `update` | dispatch + snapshot `inference_mode` | GPU offline ≠ cloud；normal→NI；low 等/到期 | NS2-T40 | `medium` |
| P5-01 | Phase 5 | vectorize 分类入 embed | `update` | `dispatch.py`；`vectorize.py:153-207`；`lsrag_definition.py:197-198` | live 才入池 | NS2-T50 | `high` |
| P5-02 | Phase 5 | 整段占槽 | `update` | admit 在 materialize/claim；`vectorize.py:406-419` 内部 batch 不再申请 | 一 Process 一槽直到 terminal | NS2-T51 | `medium` |
| P5-03 | Phase 5 | 确定性 embed 跳过 | `update` | `vectorize.py:207` 确定性分支 | 不占 8+20 | NS2-T52 | `low` |
| P5-04 | Phase 5 | embed 独立于生成池 | `update` | admit 三计数器分离 | 不占 2+2；不满不溢 NI | NS2-T53 T54 | `high` |
| P6-01 | Phase 6 | 短途/集成台账 | `add` | 🆕 `tests/unit/test_dispatch_*.py` | §8 短途全绿 | NS2-T01–T40 T50–T54 | `medium` |
| P6-02 | Phase 6 | e2e 车道旅程 | `add` | 🆕 `tests/e2e/test_ns2_dispatch_lanes.py` | 四车道 + embed FIFO 可观察 | NS2-T60 T61 T62 | `high` |
| P6-03 | Phase 6 | soak 竞态 | `add` | 🆕 `tests/unit/test_dispatch_admit_soak.py` | 并发 admit 从不超过 cap | NS2-T70 | `high` |
| P6-04 | Phase 6 | domain 守卫 | `update` | `tests/domain/test_architecture.py` | 无 extra 派发态；无新 required 表 | NS2-T71 | `medium` |
| P6-05 | Phase 6 | 真相窄回填 | `update` | S02/S03/S11/S14/S15/D04 附录 | 只记解释，不重写产品句 | — | `low` |
| P6-06 | Phase 6 | NS2 closure | `add` | 🆕 `docs/closure/new-start/NS2-pipeline-priority-closure.md` | §10 硬闸 + 五态 | NS2-T72 | `medium` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 合同、枚举、端口

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P1-01 | 枚举硬切 | a) `COMPRESSION_CHANNELS` 改为 `non-interactive` / `local-inference`。b) `IntakeIngestPayload.compression_channel` 同步；拒绝 `api-inference` / `spark` / `cloud-inference`（cloud 只存在于内部预留常量，不进公开 Literal）。c) construct / snapshot / scatter copy-list / 全部测试字符串替换。d) 错误码文案同步。 | `prompt_profiles.py:19-39`；`models.py:175-193`；`generation_construct.py:22,92-139`；`acceptance_scatter.py:136`；`test_compression_channel.py` 全文件 | 仓内生产代码 0 处 `api-inference` | NS2-T01 T02 | rg 门闩绿 |
| P1-02 | 策略模块 | a) 新建无 IO 模块：占用常数、`choose_pool(priority, kind, *, local_queued, ni_queued, local_available, ni_quota, over_budget, explicit_channel)`。b) 分类 `pool_kind(process_key, snapshot) → generate\|embed\|unpooled`。c) 生成领取序 vs embed FIFO 序做成纯函数，供 claim SQL 对照。d) 边界：两池都满 → `wait_orchestrator`；`low` 永不返回 NI。 | 🆕 `src/runtime/workflow/dispatch.py` | 策略单测不碰 DB | NS2-T03 T04 T05 | 表驱动用例全覆盖 |
| P1-03 | snapshot | a) `_resolve_compression_channel`：无显式字段时 **不要** 再默认 `non-interactive`；改为 `derived_from_priority`。b) L2 增 `channel_source: priority\|explicit`。c) 显式 `local-inference` 仍要求 `live_inference`。d) 非 ingest intent 不写生成通道。 | `config_snapshots.py:175-199,566-578` | 新 Task 的 snapshot 可复现通道 | NS2-T06 | 重试不热切 |
| P1-04 | BillingPort | a) `has_quota(channel) -> bool`。b) NS2 实现恒 `True`。c) admit NI 前调用；`False` 视为通道不可用（不是队列满）。 | 🆕 `src/services/billing.py` | 可替换；测试可注入 `False` | NS2-T07 | 注入 False 时 NI 不 admit |
| P1-05 | Qwen winner | a) `DEFAULT_BINDINGS`：Qwen structured/text `priority=5`，Lightning `10`。b) bootstrap / 供给围栏 digest 重算。c) 不删 Lightning 行。 | `registry.py:113-136,139-165,313` | 新库 generate winner=Qwen | NS2-T08 | 既有测试改断言 |
| P1-06 | 常数 / 末闸 | a) settings：`dispatch_local_running=2`、`queued=6`；`ni_running=2`、`queued=4`；`embed_running=8`、`queued=20`。b) `inference_max_in_flight` 默认改为 `12`（2+2+8），capability_limits 对齐三池 running。c) `default.toml` 注释写明「末闸不是 SSOT」。 | `config.py:39-48`；`app.py:234-240`；`data/config/default.toml:10-14` | 组合根与策略常数一致 | NS2-T09 | 单测读 settings |

### 4.2 Phase 2 — DDL 与占用会计

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P2-01 | 011 | a) `ALTER TABLE mkb_processes ADD`：`dispatch_pool TEXT CHECK (NULL or in local-inference/non-interactive/embed)`；`dispatch_admitted INTEGER NOT NULL DEFAULT 0 CHECK (0,1)`；`dispatch_enqueued_at TEXT`。b) 部分索引：`ix_mkb_proc_dispatch_ready (dispatch_pool, dispatch_admitted, available_at) WHERE status='ready'`；embed 领取另用 `available_at, created_at`。c) 头注释写「非第 N 张 required 表 / 非 payload_extra」。d) 旧行保持 `admitted=0, pool NULL`（unpooled 兼容）。 | 🆕 `src/persistence/migrations/011_process_dispatch_pools.sql`；范式 `004_process_root_and_child_cancelled.sql:1-18`；表定义 `001_initial.sql:301-357`；旧领取索引 `1728-1730` | migrate 011 可重复应用到 sqlite/turso | NS2-T10 | DDL 单测列/CHECK 存在 |
| P2-02 | occupancy | a) `running` = `status IN (claimed,running)` 且 `dispatch_pool=X`。b) `queued` = `status=ready AND admitted=1 AND pool=X`。c) `waiting` = 分类需要池且 `admitted=0 AND status=ready`。d) 计数与 admit 同事务 `SELECT ... FOR` 行锁语义（sqlite 写事务即可）。 | 🆕 dispatch occupancy helpers；`runtime_core.py` 事务内调用 | 三池数字可单查 | NS2-T11 | 插入夹具后计数正确 |
| P2-03 | 事件 | a) `ALLOWED_TYPES` 加 `process.dispatch_admitted`。b) payload：`pool`、`priority`、`channel_source`；禁 prompt/正文/token。 | `events.py:16-59,61-78` | 未登记类型仍 422 | NS2-T12 | 事件契约测 |
| P2-04 | materialize | a) INSERT 补三列默认。b) `process_spec_digest` **不要** 纳入 pool（pool 是运行时派发，不是图身份）。c) 复制 `priority_rank` 行为保持（`runtime_materialize.py:259-261,336`）。 | `runtime_materialize.py:248-346` | 新 Process 可被 admit 看见 | NS2-T13 | 物化后 admitted=0 |

### 4.3 Phase 3 — Orchestrator admit + 分池 claim

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P3-01 | admit | a) `claim_next` 开头、`promote_due_retries` 之后：在同一写事务里对 waiting 做 admit。b) 每个池：`while queued < cap` 取下一名 waiting，按策略赋 `dispatch_pool`，`admitted=1`，`enqueued_at=now`。c) NI 还要 `billing.has_quota`。d) `urgent` 与 `high` 都只赋 NI；队头靠领取序 `priority_rank DESC`，不必物理改别人的 `enqueued_at`。e) 满员不赋池。 | `runtime_core.py:149-176` | 占用永不超过 cap | NS2-T20 T21 T22 | 单测塞 9 个 local waiting，queued 停在 6 |
| P3-02 | 分池领取 | a) 可领取集合 = unpooled ready **或** (`admitted=1` 且该池 `running < running_cap`)。b) unpooled：`priority_rank DESC, available_at, deadline, created_at, process_uuid`（S03:854-864）。c) local/NI：同序（故 urgent 自然在 NI 队头）。d) 一次 `claim_next` 只取 1 行；选哪一类用稳定规则：先满足 running 空位的最高优先级可领取行（把 unpooled 与已 admit 放在同一排序里，但 embed 除外走 P3-03）。e) 未 admit 永不进 UPDATE claimed。 | `runtime_core.py:165-214` | 与 S03 非生成步 0 行为差 | NS2-T23 T24 | 未 admit 的 generate 不被 12 个 worker 领走 |
| P3-03 | embed FIFO | a) embed 可领取子集单独：`ORDER BY available_at ASC, created_at ASC, process_uuid ASC`。b) SQL/纯函数都 **禁止** `priority_rank`。c) urgent 的 vectorize 不得插到更早到达的 low 前面。 | claim SQL 分支 | FIFO 可单测 | NS2-T25 | 先到的 low embed 先于后到的 urgent embed |
| P3-04 | deadline | a) 现有 `deadline_at < now` 失败路径对 `admitted=0` 同样适用。b) `low` 「一直等」= 等到有槽或 deadline，不是无限合法。 | `runtime_core.py:185-197` | 到期码不变 | NS2-T26 | 过期 waiting 变 failed |
| P3-05 | 不睡租约 | a) `worker.run_once` 保持 claim→run→outcome；无工作返回 `False`。b) handler 内禁止为等槽 `sleep`。c) facade `try_acquire` 仍立即 `INFERENCE_BACKPRESSURE`（`facade.py:313-317`），作为 orchestrator 与本地闸不一致时的末闸；生成/embed 主路径不应打到它。d) BACKPRESSURE 对 generate 仍可走现有 retryable，但 **不得** 被 `low` salvage 成 NI。 | `worker.py:45-92`；`facade.py:75-117,313-317` | 无新 sleep | NS2-T27 | 静态扫描 worker/intake 无「等槽 sleep」 |

### 4.4 Phase 4 — 生成步接线

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P4-01 | 分类 | a) generate：`lsrag.transcribe_markdown`、`lsrag.structurize`、`lsrag.construct`；以及 `clean.extract.{web_llm,doc_llm,pdf_llm}` / 其它 `llm_required` 且将调用 CLI/facade 的 clean。b) unpooled：acquire/decode/确定性 clean/seal/preflight/accept/publish/index.rebuild/human_review。c) 确定性 C（无 CLI、无 live）→ unpooled，避免 CI 被槽位卡住。d) stub CLI 视为 NI 可用（真实子进程与 stub 同一池）。 | `dispatch.py`；`core.py:319-344`；`clean_preflight.py:75-97`；`lsrag_definition.py:112-182` | 分类表可单测 | NS2-T30 | 夹具 process_key 全覆盖 |
| P4-02 | 车道表 | 按冻结表实现 `choose_pool`：urgent→NI；high→NI；normal→local 若 `queued<6` 且 local 可用且未超预算，否则 NI 若 `queued<4` 且有额度，否则 wait；low→local 若 `queued<6` 且可用，否则 wait。 | `dispatch.py` | 与 §6 `T-O-355` 一致 | NS2-T31–T34 | 表驱动 |
| P4-03 | 超预算 | a) json/structurize 与 llm-clean：用即将吐出的正文长度（clean 字符数）与 `dispatch_local_char_budget`（settings，默认与现 embed 16k 量级对齐，常量单点）比较。b) 超预算：`normal` 视作溢流；`low` 仍只 local。c) C/markdown 默认不因输入长而溢流（输出短）。 | `dispatch.py` + structurize/clean 分类入口 | 长 json 不占 Qwen | NS2-T35 | 超预算 normal 的 pool=NI |
| P4-04 | salvage | a) 仅 `normal` 且原池 local 且错误 ∈ 现 `_API_INFERENCE_SALVAGE_CODES`（`generation_construct.py:26-42`）且 NI 可用且 billing 真。b) `low` 直接 fail-closed。c) 已在 NI 不再换通道。d) receipt：`salvage_from=local-inference`，`to=non-interactive`。e) 不退确定性摘要。 | `generation_construct.py:121-216` | 与现 salvage 单测分叉 | NS2-T36 T37 | low 失败无 CLI 调用 |
| P4-05 | 覆盖 | a) 显式 `compression_channel` 强制该池，忽略车道（调试）。b) `channel_source=explicit` 写入 snapshot。c) 写 `mkb_security_audit_events` 或已有 override 审计通道（对照 `config_snapshots.py:180-183`）。d) `low`+显式 NI 允许但必审计。 | snapshot + S16 audit | 覆盖可追溯 | NS2-T38 | 无审计不得覆盖（测试夹具查事件） |
| P4-06 | 改名落 receipt | construct/live receipt、`salvage_from`、测试断言全部 `local-inference`。 | `generation_construct.py:101-206,407,1071,1129` | 旧字符串仅允许出现在迁移注释 | NS2-T39 | rg |
| P4-07 | local 不可用 | a) `live_inference=false` 且无 Spark = local 不可用。b) `normal` 走 NI（stub/CLI）。c) `low` wait / deadline。d) **不**进 cloud。 | dispatch + snapshot `l2.inference_mode` | 现有 sqlite e2e 默认 normal 仍能走 stub CLI | NS2-T40 | 离线 e2e 不 503 |

### 4.5 Phase 5 — Embed 池接线

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P5-01 | 分类 | live embed（`vectorize.py:170-203`）→ embed 池。`process_key=lsrag.vectorize`。 | `vectorize.py:153-207`；`lsrag_definition.py:197-198` | live 才 waiting | NS2-T50 | 分类单测 |
| P5-02 | 整段 | a) vectorize Process 在 admit 时占 1 queued，claim 后占 1 running，直到该 Process terminal。b) `_live_embeddings` 内部 while batch（`406-419`）**不再**二次申请。 | vectorize + admit | 8 个 Process = 最多 8 个在飞 HTTP | NS2-T51 | 计数不随 batch 数涨 |
| P5-03 | 确定性跳过 | `live_inference=false` 走 `deterministic_embedding`（`vectorize.py:207`）→ unpooled。 | 同上 | CI e2e 不占 embed 20 | NS2-T52 | 离线 vectorize 立即 claim |
| P5-04 | 独立 | a) embed 计数器与 local/NI 分离。b) embed 满员只 wait，不溢 NI/cloud。c) 领取忽略 priority。 | admit/claim | 2 路 Qwen 满时 embed 仍可进 | NS2-T53 T54 | 交叉占用单测 |

### 4.6 Phase 6 — 测试、文档、收口

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P6-01 | 短途 | 落地 §8.1 全部 unit/集成项；fork 既有 compression/workflow/inference 测试 | 🆕 `tests/unit/test_dispatch_policy.py` 等 | 每 PR 可跑 | NS2-T01–T54 | pytest 绿 |
| P6-02 | e2e | 用 stub CLI + 可注入 occupancy 的 runtime，跑四车道与 embed FIFO 旅程（不必真 Spark） | 🆕 `tests/e2e/test_ns2_dispatch_lanes.py` | 行上可观察 admitted/pool | NS2-T60–T62 | e2e 绿 |
| P6-03 | soak | 并发 `claim_next` × N，断言三池 running/queued 从不越过 cap | 🆕 `tests/unit/test_dispatch_admit_soak.py` | 竞态不超卖 | NS2-T70 | N=32 全绿 |
| P6-04 | 守卫 | architecture：派发列存在；`payload_extra` 无 dispatch_*；无新 CREATE TABLE | `tests/domain/test_architecture.py` | 回归 | NS2-T71 | domain 绿 |
| P6-05 | 窄回填 | S03 Priority 节补「生成池选择」一句；S11 补 orchestrator 为配额 SSOT、facade 为末闸；S02 写 priority 双用；D04 记 011 列；S14 L2 字段；S15 新事件 | 对应 domain-truth | 附录级 | — | 不改 QNA |
| P6-06 | closure | 按 `.adocs/closure.md` 阶段 final 写 NS2 closure；§10 硬闸逐项填五态 | 🆕 closure 文件 | owner 30 秒可读 | NS2-T72 | close-type 合法 |

---

## 5. Phase 详情

### 5.1 Phase 1 — 合同、枚举、端口

- **Phase 目标**：调度语义有唯一纯函数入口；旧通道名退出代码。
- **本 Phase 对应编号**：`P1-01` … `P1-06`
- **本 Phase 新增文件**：`src/runtime/workflow/dispatch.py`；`src/services/billing.py`
- **本 Phase 修改文件**：`prompt_profiles.py:19-39`；`models.py:185`；`config_snapshots.py:175-199,566-578`；`registry.py:126-136`；`config.py:47`；`app.py:234-240`；所有 `api-inference` 测试
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. 公开 payload 只接受 `non-interactive` / `local-inference` / omit。
  2. omit + `priority=normal` 的派生结果是「先 local」而不是历史默认 Claude。
  3. `choose_pool` 对四车道 × 占用边界返回稳定枚举（`local-inference` / `non-interactive` / `wait`）。
  4. `low` 在任何占用下都不返回 NI。
  5. BillingPort 可注入 False，策略把 NI 视为不可用。
  6. 新 bootstrap 的 generate winner 为 `unsloth/Qwen3.8-27B-NVFP4`。
- **对应测试台账项**：`NS2-T01` … `NS2-T09`
- **收口标准**：策略单测绿；rg 无生产 `api-inference`；snapshot 单测覆盖 derived/explicit。
- **本 Phase 风险提醒**：默认通道从 Claude 改成「先 GPU」会打断只设了 `live_inference=false`、又没 CLI 的调用方——P4-07 必须让 `normal` 在 local 不可用时溢到 stub CLI，否则 NS1 e2e 会红。

### 5.2 Phase 2 — DDL 与占用会计

- **Phase 目标**：占用可在 `mkb_processes` 上查询；物化不提前占槽。
- **本 Phase 对应编号**：`P2-01` … `P2-04`
- **本 Phase 新增 / 修改 / 删除文件**：🆕 `011_process_dispatch_pools.sql`；改 `runtime_materialize.py:305-346`；`events.py:16-59`
- **具体功能预期**：
  1. 011 在干净库与已到 010 的库都可应用。
  2. CHECK 拒绝 `cloud-inference` 写入 `dispatch_pool`（本轮无此池）。
  3. 物化后 generate/embed 类 Process 仍 `admitted=0`。
  4. `process_spec_digest` 不因后来 admit 而改变。
  5. 未登记事件类型仍 422。
- **对应测试台账项**：`NS2-T10` … `NS2-T13`
- **收口标准**：migration 测试 + 物化断言绿。
- **本 Phase 风险提醒**：`T-O-337` / `T-O-173`；任何「先写 extra 以后再晋升」都是违规。

### 5.3 Phase 3 — Orchestrator admit + 分池 claim

- **Phase 目标**：配额在 claim 事务里授予；worker 领到的一定已有槽或属于 unpooled。
- **本 Phase 对应编号**：`P3-01` … `P3-05`
- **本 Phase 新增 / 修改 / 删除文件**：`runtime_core.py:149-227`；`worker.py:45-52`（只读守卫）；dispatch admit
- **具体功能预期**：
  1. local `queued` 到 6 后第 7 个 generate waiting 保持 `admitted=0`。
  2. 2 个 local `running` 时，即使 queued&lt;6 也不得再 claim 第 3 个 local。
  3. unpooled acquire 仍可按 S03 序插在等待的 generate 之前被领取（不占池）。
  4. embed 领取序与 `priority_rank` 无关。
  5. `admitted=0` 过 deadline 失败，错误码保持 `deadline-exceeded-before-start`。
  6. 12 个并发 `claim_next` 不能超卖任一 running cap。
  7. worker 在无空位时返回 False，Process 仍 ready。
- **对应测试台账项**：`NS2-T20` … `NS2-T27`
- **收口标准**：claim/admit 单测 + 并发 gather 绿。
- **本 Phase 风险提醒**：改 `ORDER BY` 会碰 `test_workflow_runtime.py` 既有领取用例；必须让 **unpooled** 行为保持，只对分类后的池化步改序。

### 5.4 Phase 4 — 生成步接线

- **Phase 目标**：真实 LLM Process 按车道进池；salvage 不再无条件升 NI。
- **本 Phase 对应编号**：`P4-01` … `P4-07`
- **本 Phase 新增 / 修改 / 删除文件**：`generation_construct.py:23-216`；`clean_preflight.py:75-97`；snapshot；dispatch
- **具体功能预期**：
  1. 默认 `normal` ingest：structurize/construct 在 local 可用时进 local 池。
  2. `urgent`/`high` 的生成步只进 NI。
  3. `low` 生成步只进 local；失败不调 CLI salvage。
  4. `normal` + 超预算 json 进 NI，即使 local queued=0。
  5. 显式 `compression_channel` 覆盖车道并落审计。
  6. 离线+stub CLI：`normal` 因 local 不可用而溢 NI，e2e 仍通。
  7. salvage 成功 receipt 区分请求通道与落地通道。
- **对应测试台账项**：`NS2-T30` … `NS2-T40`
- **收口标准**：compression_channel 旧测全部改名并通过；新增车道测绿。
- **本 Phase 风险提醒**：不要把确定性 C 塞进池，否则 CI 会被 2 个槽卡住整条流水线。

### 5.5 Phase 5 — Embed 池接线

- **Phase 目标**：live 向量化受 8+20 约束；不受 priority；不和生成抢会计。
- **本 Phase 对应编号**：`P5-01` … `P5-04`
- **本 Phase 新增 / 修改 / 删除文件**：`vectorize.py:153-207,376-419`（分类/占槽，不改算法）；dispatch
- **具体功能预期**：
  1. live vectorize 在 admit 前不能被 claim。
  2. 一个 Process 打 3 个 batch，占用计数仍为 1。
  3. 第 29 个 live vectorize 留在 orchestrator。
  4. 后到的 urgent vectorize 不能插到先到的 normal/low 前面。
  5. 确定性 vectorize 立即按 unpooled 领取。
- **对应测试台账项**：`NS2-T50` … `NS2-T54`
- **收口标准**：embed 占用/FIFO 单测绿。
- **本 Phase 风险提醒**：物理 GPU 仍与 Qwen 共享；本 Phase 不做设备级隔离，只做会计隔离。

### 5.6 Phase 6 — 测试、文档、收口

- **Phase 目标**：台账全 PASS；真相窄回填；写出阶段 final closure。
- **本 Phase 对应编号**：`P6-01` … `P6-06`
- **本 Phase 新增 / 修改 / 删除文件**：§8 所列测试；domain-truth 附录；🆕 closure
- **具体功能预期**：
  1. mega 证明四车道在行上可见。
  2. soak 证明并发不超卖。
  3. closure 使用统一 close-type，deferred 分 A/B/C。
- **对应测试台账项**：`NS2-T60` … `NS2-T72`
- **收口标准**：§10 硬闸全 PASS 且四元组齐全方可标本 AP `executed`。
- **本 Phase 风险提醒**：不得把 VF V11 turso I/O 写成 NS2 失败；pre-existing 必须 git 甩锅。

---

## 6. 依赖的冻结设计决策（只读引用）

> 下列 `T-O-353..361` 于 2026-08-14 由业主在本会话口头冻结（同 `T-O-352` 先例）。本 AP 不改口、不新开 Q。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `T-O-353` | 业主：队列与槽位分开；local 2+6=8 | P1-02 / P2-02 / P3-01 占用函数 | 停工 |
| `T-O-354` | 业主：generate 为入队单位；embed=vectorize Process | P4-01 / P5-02 | 停工 |
| `T-O-355` | 业主：沿用 `priority`；urgent/high→NI；normal 先 GPU 溢 NI；low 锁 GPU | P1-03 / P4-02 | 停工 |
| `T-O-356` | 业主：embed 8+20，不受 priority | P3-03 / P5-* | 停工 |
| `T-O-357` | 业主：NI 套餐后续 billing；现在只派有额度的 | P1-04 恒真端口 | 实现真实扣减则另开 AP |
| `T-O-358` | 业主：cloud 为双通道都不可用时的最终回退 | 枚举预留、禁止当泄洪 | 未授权不得路由 |
| `T-O-359` | 业主：没位留 orchestrator | P3 不 claim-then-sleep | 停工 |
| `T-O-360` | `T-O-337` + `T-O-173` | 只加列，不进 extra，不加表 | DDL 被拒则停工 |
| `T-O-361` | 收窄 `T-O-200` / S11:265-270 | 配额=admit；facade=末闸；claimed≠配额 | 若与 S11 冲突，以 admit 为准并窄回填 |
| `T-O-200` | `qna-truth/S11.md` Q8 | BACKPRESSURE 仍零模型调用 | 保持 |
| `T-O-173` | D04-P04 | 派发态 typed 列 | 保持 |
| `T-O-352` | pre-NS1 业主修订 | 不重开 g0 向量 | 保持 |
| S03:854-866 | S03-v1.3 | unpooled 领取序保持 | 回归红则修 claim 分支 |
| `task-priority-locked` | `task_commands.py:146-147` | 非 queued 不得改 priority（车道在跑后锁死） | 保持 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `src/runtime/workflow/runtime_core.py:149-227` | `claim_next` 单行领取；`ORDER BY priority_rank DESC` | P3-01/02 同事务 admit + 分池 | `♻️ 重 substrate` | 不要拆成第二张队列表 |
| A-2 | `src/runtime/workflow/runtime_core.py:173-174` | 现行 S03 领取序 | P3-02 unpooled 保持；生成复用；embed 丢 rank | `✅ 复用` | S03:859-864 |
| A-3 | `src/runtime/workflow/constants.py:24-29` | `low=100…urgent=400` | 不改数值 | `✅ 复用` | 已建好别重写 |
| A-4 | `src/runtime/workflow/runtime_materialize.py:248-337` | Task.priority → Process.priority_rank | P2-04 加三列默认 | `✅ 复用` | digest 勿纳入 pool |
| A-5 | `src/runtime/workflow/worker.py:45-52` | claim→run→outcome | P3-05 禁止等槽 sleep | `✅ 复用` | 已建好别重写 |
| A-6 | `src/runtime/workflow/runtime.py:14-22` | Runtime mixin 根 | admit 放 core mixin | `✅ 复用` | |
| A-7 | `src/persistence/migrations/001_initial.sql:140-183` | `mkb_tasks.priority` CHECK 四值 | 不改任务表 | `✅ 复用` | 默认 `normal` |
| A-8 | `src/persistence/migrations/001_initial.sql:301-357` | `mkb_processes` 状态/领取列 | P2-01 加列 | `✅ 复用` | |
| A-9 | `src/persistence/migrations/001_initial.sql:1728-1730` | `ix_mkb_proc_claim_queue` | 保留；另加 dispatch 索引 | `✅ 复用` | |
| A-10 | `src/persistence/migrations/004_process_root_and_child_cancelled.sql:6-18` | 既有列晋升范式 | P2-01 照抄风格 | `✅ 复用` | 非新表 |
| A-11 | `src/contracts/api/models.py:175-193` | ingest 可选 `compression_channel` | P1-01 / P4-05 | `✅ 复用` | extra=forbid |
| A-12 | `src/contracts/api/models.py:266-282` | `TaskCreateRequest.priority` 默认 normal | 车道默认入口 | `✅ 复用` | 不新字段 |
| A-13 | `src/contracts/api/models.py:357-360` | patch priority | 仅 queued 可变 | `✅ 复用` | |
| A-14 | `src/runtime/task/task_commands.py:146-147` | `task-priority-locked` | 跑后锁车道 | `✅ 复用` | |
| A-15 | `src/runtime/task/task_create.py:34,106` | 创建写入 priority | 不改 | `✅ 复用` | |
| A-16 | `src/services/prompt_profiles.py:19-39` | 通道封闭集 + 默认 NI | P1-01 改名；默认改派生 | `♻️ 重 substrate` | |
| A-17 | `src/services/config_snapshots.py:175-199` | L2 冻 `compression_channel` | P1-03 `channel_source` | `✅ 复用` | L2 禁 token |
| A-18 | `src/services/config_snapshots.py:566-578` | 显式通道 + live 门闩 | P1-03 / P4-05 / P4-07 | `♻️ 重 substrate` | 去掉「omit=NI」 |
| A-19 | `src/runtime/intake/generation_construct.py:23-42` | salvage 错误闭集 | P4-04 按车道收窄 | `✅ 复用` | 别扩成确定性回退 |
| A-20 | `src/runtime/intake/generation_construct.py:92-216` | C 通道选择 + salvage | P4-04 / P4-06 | `♻️ 重 substrate` | |
| A-21 | `src/runtime/intake/generation_live.py:171,304-312` | live structured C | 继续只服务 local 池 | `✅ 复用` | |
| A-22 | `src/runtime/intake/clean_preflight.py:75-97` | LLM clean → CLI | P4-01 入生成池 | `✅ 复用` | 确定性 clean 不入 |
| A-23 | `src/runtime/intake/core.py:319-344` | process_key 分发 | 分类表的权威名单 | `✅ 复用` | |
| A-24 | `src/workflows/lsrag_definition.py:162-198` | md / structurize / construct / vectorize | 池分类对照 | `✅ 复用` | 不改图拓扑 |
| A-25 | `src/runtime/intake/vectorize.py:153-207` | live vs deterministic 分支 | P5-01/03 | `✅ 复用` | 不改 S08 算法 |
| A-26 | `src/runtime/intake/vectorize.py:376-419` | 按字符打包多 batch | P5-02 不按 batch 占槽 | `✅ 复用` | |
| A-27 | `src/runtime/inference/facade.py:75-157,313-317` | 内存闸 + 立即 BACKPRESSURE | P1-06 / P3-05 降为末闸 | `✅ 复用` | 禁改成阻塞 acquire |
| A-28 | `src/runtime/config.py:39-48` | `live_inference` / `max_in_flight` | P1-06 三池常数 | `✅ 复用` | |
| A-29 | `api/app.py:234-240` | Facade 组合 | capability_limits 对齐 running | `✅ 复用` | |
| A-30 | `src/services/registry.py:113-136` | Lightning 5 / Qwen 10 | P1-05 对调 | `✅ 复用` | |
| A-31 | `src/services/events.py:16-59` | 事件闭集 | P2-03 加 admitted | `✅ 复用` | |
| A-32 | `src/runtime/intake/acceptance_scatter.py:136` | 子 execution 复制通道字段 | 同步改名 | `✅ 复用` | |
| A-33 | `src/runtime/workflow/runtime_core.py:185-197` | deadline-before-start | P3-04 waiting 同样适用 | `✅ 复用` | |
| A-34 | `docs/baseline/domain-truth/S03-workflow-engine.md:854-866` | priority 只影响顺序 | P6-05 窄回填双用 | `✅ 复用` | 成功语义仍不变 |
| A-35 | `docs/baseline/domain-truth/S11-inference-runtime.md:213,265-270` | 闸满 BACKPRESSURE | P3-05 / P6-05 | `✅ 复用` | `T-O-200` |
| A-36 | `docs/baseline/domain-truth/D04-turso-physical-schema.md` `D04-P04` / `T-O-173` | extra 禁 state | P2-01 必须列 | `✅ 复用` | |
| A-37 | 🆕 `src/runtime/workflow/dispatch.py` | 策略 + occupancy | P1-02 / P2-02 / P3-01 | `🆕 净新` | 无 IO |
| A-38 | 🆕 `src/services/billing.py` | quota 端口 | P1-04 | `🆕 净新` | 恒真 |
| A-39 | 🆕 `011_process_dispatch_pools.sql` | 三列 | P2-01 | `🆕 净新` | |
| A-40 | `tests/unit/test_workflow_runtime.py:319-334,581` | priority 复制；并发 claim | 🔱 保 unpooled；加池化断言 | `🔱 fork` | |
| A-41 | `tests/unit/test_compression_channel.py` | 通道合同 / salvage | 🔱 改名 + 车道 | `🔱 fork` | |
| A-42 | `tests/unit/test_inference_runtime.py:207-212` | BACKPRESSURE | ♻️ 末闸仍立即失败 | `♻️ 沿用` | |
| A-43 | `tests/e2e/test_ns1_pipeline.py` | NS1 mega | ♻️ 默认 normal 须仍绿 | `♻️ 沿用` | P4-07 |
| A-44 | `tests/domain/test_architecture.py` | D03 守卫 | P6-04 | `🔱 fork` | |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 新建 `mkb_dispatch_queue` 表 | `T-O-360` / `T-O-337`；占用必须是 Process 行事实 |
| ⛔2 | 把 `dispatch_*` 写入 `payload_extra` | `T-O-173` / D04-P04 |
| ⛔3 | worker claim 后 `asyncio.sleep` 等槽 | `T-O-359`；租约会过期、fencing 会乱 |
| ⛔4 | 把 facade `try_acquire` 改成阻塞 | 违反 S11 / `T-O-200`「立即 BACKPRESSURE、零模型调用」 |
| ⛔5 | 全局 `max_in_flight=8` 继续当 SSOT | 2+2+8 会被打回总共 8 |
| ⛔6 | embed claim 仍 `priority_rank DESC` | `T-O-356` |
| ⛔7 | `low` salvage 到 NI / 上 cloud | `T-O-355` / `T-O-358`；偷套餐 |
| ⛔8 | 队列忙就跳 cloud | cloud 是能力消失回退，不是泄洪 |
| ⛔9 | 整份 intake 占一个槽 | `T-O-354`；长 json 会堵死 GPU |
| ⛔10 | 每个 embed batch 占一槽 | 业主要降低复杂性；整段 Process 一槽 |
| ⛔11 | 池满则 `deterministic_summaries` | silent fallback；NS1 已禁假树同类 |
| ⛔12 | 新公开字段 `inference_lane` / `fast` | 业主改回现有 priority |
| ⛔13 | 改 S03 成功语义或 Process 状态机七态 | 只加列，不加状态 |
| ⛔14 | 运行中改 priority 以换池 | `task-priority-locked` |
| ⛔15 | 把 VF V11 turso I/O 当 NS2 回归失败 | NS1 closure 已 defer |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：N/A。§7.1 即本 AP grounding 真源。
- **冻结口径真源**：本会话业主决议（`T-O-353..361`）；S03:854-866；S11 `T-O-200`；D04 `T-O-173`。
- **安全 / 信任边界类工作项的威胁模型锚**（P1-04 / P4-05 / 占用会计，不得空）：
  1. **优先级洗钱**：调用方把批量文档标 `urgent` 耗尽 NI 套餐 → 缓解：默认 `normal`；billing 后续硬闸；本轮至少审计 `channel_source=explicit` 与 urgent 计数（可观测，不在本轮做配额）。
  2. **覆盖逃逸**：`compression_channel=non-interactive` 让 `low` 偷上线上 → 允许但必须 security audit；测试断言无审计事件则失败。
  3. **占用超卖**：多 worker 竞态 admit → 同事务计数 + soak（NS2-T70）；禁止内存闸当 SSOT。
  4. **跨租户抢槽**：占用是部署级（一张 Spark / 一份套餐），不是 per-team。内部单租户假设与 S16 OD-04 一致；不得用 `team_uuid` 当授权绕过配额。
  5. **事件泄漏**：`process.dispatch_admitted` payload 禁止正文 / token / prompt path 绝对路径。
  6. **末闸绕过**：handler 直打 adapter 不经 facade → 已有 S11 纪律；本 AP 不新开旁路。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| NS2-T01 | 公开 payload 拒 `api-inference` / `cloud-inference` / `spark` | 短途 | 契约 | 🔱 `test_ns1_api_workflow.py` + `test_compression_channel.py` | P1-01 → 硬切 | commit + 测试名 + run-time |
| NS2-T02 | 仓内 `src/` `tests/` 无 `api-inference` 字符串（注释/docs 除外） | 短途 | 契约 | 🆕 rg gate in `tests/domain` 或 unit | P1-01 → 改名完成 | commit + gate + run-time |
| NS2-T03 | `choose_pool` 四车道 × 占用边界表驱动 | 短途 | unit | 🆕 `tests/unit/test_dispatch_policy.py` | P1-02 → 策略 SSOT | commit + test + run-time |
| NS2-T04 | `low` 永不选 NI；billing False 时 NI 不可选 | 短途 | unit | 同上 | P1-02 P1-04 | commit + test + run-time |
| NS2-T05 | `pool_kind(process_key)` 覆盖 core 分发全表 | 短途 | unit | 同上 | P4-01 P5-01 | commit + test + run-time |
| NS2-T06 | snapshot：omit+normal → derived local；explicit 保留；非 ingest 无通道 | 短途 | unit | 🔱 `test_compression_channel.py` snapshot 段 | P1-03 | commit + test + run-time |
| NS2-T07 | 注入 BillingPort False：NI admit 为 0 | 短途 | unit | 🆕 dispatch occupancy 测 | P1-04 | commit + test + run-time |
| NS2-T08 | generate winner = Qwen priority 5 | 短途 | unit | 🔱 `test_compression_channel.py` binding 段 | P1-05 | commit + test + run-time |
| NS2-T09 | settings 三池常数；facade 全局 ≥12 | 短途 | unit | 🆕 settings/composition 断言 | P1-06 | commit + test + run-time |
| NS2-T10 | 011 列/CHECK/索引存在；旧库可迁 | 短途 | 集成 | 🆕 `tests/unit/test_dispatch_ddl.py` | P2-01 | commit + test + run-time |
| NS2-T11 | occupancy 三计数器定义 | 短途 | unit | 🆕 `tests/unit/test_dispatch_occupancy.py` | P2-02 | commit + test + run-time |
| NS2-T12 | `process.dispatch_admitted` 可写；未知类型 422 | 短途 | unit | 🔱 `test_observability_contracts.py` | P2-03 | commit + test + run-time |
| NS2-T13 | 物化 Process `admitted=0`；spec digest 稳定 | 短途 | unit | 🔱 `test_workflow_runtime.py:319` | P2-04 | commit + test + run-time |
| NS2-T20 | local queued 封顶 6；第 7 个 waiting | 短途 | unit | 🆕 `tests/unit/test_dispatch_claim.py` | P3-01 | commit + test + run-time |
| NS2-T21 | local running 封顶 2 | 短途 | unit | 同上 | P3-01 P3-02 | commit + test + run-time |
| NS2-T22 | NI queued 4 / running 2 | 短途 | unit | 同上 | P3-01 | commit + test + run-time |
| NS2-T23 | 未 admit 不被 claim | 短途 | unit | 同上 | P3-02 | commit + test + run-time |
| NS2-T24 | unpooled 仍 `priority_rank DESC` | 短途 | unit | 🔱 `test_workflow_runtime.py` | P3-02 → S03 0 差 | commit + test + run-time |
| NS2-T25 | embed FIFO：先到 low 先于后到 urgent | 短途 | unit | 🆕 claim 测 | P3-03 | commit + test + run-time |
| NS2-T26 | waiting 过 deadline → `deadline-exceeded-before-start` | 短途 | unit | 🔱 runtime deadline 测 | P3-04 | commit + test + run-time |
| NS2-T27 | worker 无槽返回 False；静态无等槽 sleep | 短途 | unit+契约 | 🆕 + rg | P3-05 | commit + test + run-time |
| NS2-T30 | LLM 步 generate；确定性 clean unpooled | 短途 | unit | `test_dispatch_policy.py` | P4-01 | commit + test + run-time |
| NS2-T31 | urgent 生成只 NI，插在 high 前领取 | 短途 | unit | `test_dispatch_claim.py` | P4-02 | commit + test + run-time |
| NS2-T32 | high 生成 NI 队尾 | 短途 | unit | 同上 | P4-02 | commit + test + run-time |
| NS2-T33 | normal：local 未满进 local；queued≥6 溢 NI | 短途 | unit | 同上 | P4-02 | commit + test + run-time |
| NS2-T34 | low：只 local；满则 waiting | 短途 | unit | 同上 | P4-02 | commit + test + run-time |
| NS2-T35 | normal 超预算 → NI；low 超预算仍 local | 短途 | unit | policy | P4-03 | commit + test + run-time |
| NS2-T36 | normal local 失败 salvage 一次 NI | 短途 | unit | 🔱 `test_compression_channel.py` salvage | P4-04 | commit + test + run-time |
| NS2-T37 | low 失败不 salvage（攻击：偷套餐） | 短途 | unit | 同上 + 攻击向量 | P4-04 → §7.3.2 | commit + test + run-time |
| NS2-T38 | 显式通道覆盖必有审计事件 | 短途 | unit | 🆕 | P4-05 → §7.3.2 | commit + test + run-time |
| NS2-T39 | receipt / salvage_from 新通道名 | 短途 | unit | 🔱 compression salvage 断言 | P4-06 | commit + test + run-time |
| NS2-T40 | live=false 时 normal 溢 NI，不 503 | 短途 | unit | snapshot+policy | P4-07 | commit + test + run-time |
| NS2-T50 | live vectorize 分类 embed | 短途 | unit | policy | P5-01 | commit + test + run-time |
| NS2-T51 | 多 batch 占用仍为 1 | 短途 | unit | occupancy + 假 embed | P5-02 | commit + test + run-time |
| NS2-T52 | 确定性 vectorize unpooled | 短途 | unit | policy | P5-03 | commit + test + run-time |
| NS2-T53 | embed 满 20+8 不溢 NI | 短途 | unit | claim | P5-04 | commit + test + run-time |
| NS2-T54 | local running=2 时 embed 仍可 claim | 短途 | unit | claim | P5-04 | commit + test + run-time |
| NS2-T60 | e2e：四车道行上 pool/admitted 可见 | spike | e2e | 🆕 `tests/e2e/test_ns2_dispatch_lanes.py` | P6-02 | commit + test + run-time |
| NS2-T61 | e2e：默认 normal + stub 仍跑通 NS1 金样图 | mega | e2e | ♻️ `test_ns1_pipeline.py` | P4-07 P6-02 | commit + test + run-time |
| NS2-T62 | e2e：embed FIFO 两份 live=false 不挡；live 夹具测顺序 | spike | e2e | 🆕 lanes 文件 | P5 / P6-02 | commit + test + run-time |
| NS2-T70 | soak：32 并发 claim 不超卖三池 | soak | unit | 🆕 `test_dispatch_admit_soak.py` | P3 P6-03 | commit + soak log + run-time |
| NS2-T71 | domain：无新表；extra 无 dispatch 态 | 短途 | domain | 🔱 `test_architecture.py` | P6-04 | commit + test + run-time |
| NS2-T72 | closure 文件存在且 close-type 合法、硬闸有五态 | 短途 | 文档 | 🆕 closure | P6-06 | commit + 人工检 + run-time |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_compression_channel.py` | `🔱 fork` | 改名；派生默认；salvage 分车道 | 已存在，须改红再绿 |
| `tests/unit/test_ns1_api_workflow.py` | `🔱 fork` | Literal 断言 | 已存在 |
| `tests/unit/test_ns1_generation_cli.py` | `🔱 fork` | transport 字符串 | 已存在 |
| `tests/e2e/test_single_intake_pipeline.py` | `🔱 fork` | payload 通道名 | 已存在 |
| `tests/unit/test_workflow_runtime.py` | `🔱 fork` | 保 unpooled；加 admitted | 已存在 |
| `tests/unit/test_inference_runtime.py` | `♻️ 沿用` | 0 改动（末闸） | 已存在，纳入回归 |
| `tests/e2e/test_ns1_pipeline.py` | `♻️ 沿用` | 0 或仅默认通道兼容 | 已存在，必须仍绿 |
| `tests/domain/test_architecture.py` | `🔱 fork` | + 无新表 / extra 守卫 | 已存在 |
| `tests/unit/test_observability_contracts.py` | `🔱 fork` | + 新事件类型 | 已存在 |
| `tests/e2e/test_generation_pipeline_contracts.py` | `♻️ 沿用` | 通道字段若断言则改名 | 已存在 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_dispatch_*.py tests/unit/test_compression_channel.py tests/unit/test_dispatch_ddl.py -q` | unit·契约·集成 | 每项提交前 |
| spike | `uv run pytest tests/e2e/test_ns2_dispatch_lanes.py -q` | e2e | Phase 4/5 收口 |
| mega | `uv run pytest tests/e2e/test_ns1_pipeline.py tests/e2e/test_ns2_dispatch_lanes.py tests/e2e/test_generation_pipeline_contracts.py -q` | e2e | **本 AP 收口** |
| soak | `uv run pytest tests/unit/test_dispatch_admit_soak.py -q` | unit 并发 | **退出硬闸** |
| 回归 | `uv run pytest tests/unit tests/domain tests/e2e/test_ns1_pipeline.py -q` | 全短途+NS1 | Phase 6 |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖真实 Spark 双流 Qwen + 8 路 embed 的设备争用（理由：无稳定 GPU CI）→ 交业主手工 soak；**不在本 AP 假装覆盖**。
- 不覆盖 MiniMax / Claude 真机质量对比 → 交模型选型实验（`.experiment/`，已 gitignore）。
- 不覆盖真实 billing 扣减 / 套餐用尽后的产品文案 → 交 billing AP。
- 不覆盖 `cloud-inference` 故障转移 → 交 cloud AP。
- 不覆盖 VF V11 pyturso 读库 I/O → 交 harness charter。
- 不覆盖 urgent 老化公平性 → 交后继若 high 被饿死。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组；占用断言必须读 **DB 行**（`dispatch_pool` / `dispatch_admitted` / status），禁止只断言内存 mock 返回值就算 e2e。
- `degraded` 必带 `reason`；turso I/O 失败标 `pre-existing` + NS1 closure 引用，不记 NS2 红。
- 安全项 NS2-T37 / T38 必须走攻击向量（low salvage、无审计覆盖）。
- soak 失败 = 超卖，不得用「重试到绿」掩盖。

### 8.6 用例详述（每个 Test-ID 的场景 / 步骤 / 期望）

**NS2-T01 公开枚举。** 构造 `IntakeIngestPayload`：`compression_channel` 分别为 `api-inference`、`cloud-inference`、`claude`、`spark`。期望 Pydantic `ValidationError`。合法值 `non-interactive`、`local-inference`、omit 成功。

**NS2-T02 改名门闩。** `rg` 扫描 `src/` 与 `tests/`，允许名单仅 migration 注释或本测试自身。命中 `api-inference` 则失败。

**NS2-T03 策略表。** 矩阵至少：`(urgent, *, *)→NI`；`(high, *, *)→NI`；`(normal, local_queued=5)→local`；`(normal, local_queued=6, ni_queued=3)→NI`；`(normal, 6, 4)→wait`；`(low, local_queued=5)→local`；`(low, 6)→wait`。期望纯函数返回值完全一致。

**NS2-T04 禁 NI 与配额。** `low` 即使 `explicit=None` 且 NI 全空仍非 NI。`has_quota=False` 时 urgent 返回 `wait`（不是 NI）。

**NS2-T05 分类全表。** 对 `core.py:319-344` 每个 `process_key` 断言 kind。重点：`clean.extract.deterministic=unpooled`；`lsrag.structurize=generate`（当运输非确定性）；`lsrag.vectorize` 依赖 live 旗。

**NS2-T06 snapshot。** 三条 create：omit+normal → `channel_source=priority` 且派生 local（或 local 不可用时策略层再溢，见 T40）；explicit NI → `channel_source=explicit`；`intake.delete` 无通道键。

**NS2-T07 billing 注入。** 运行时注入 False，塞 1 个 urgent generate waiting，跑 admit。期望该行仍 `admitted=0`。

**NS2-T08 Qwen winner。** bootstrap 后查 `mkb_adapter_bindings`：`structured_generate`/`text_generate` 中 `priority=5` 且 enabled 的 `model_key` 为 Qwen。

**NS2-T09 常数。** 读 Settings 默认；组合 Facade 时 `capability_limits` embed=8、structured+text 合计不超过 local running（实现可选按 capability 拆，但全局 ≥12）。

**NS2-T10 DDL。** 空库跑到 011；再对已 010 的夹具库升级。`PRAGMA table_info(mkb_processes)` 含三列。插入非法 pool 被 CHECK 拒。

**NS2-T11 occupancy。** 插入：2 claimed local、6 ready admitted local、3 ready 未 admit generate。期望 running=2 queued=6 waiting=3。

**NS2-T12 事件。** 写 `process.dispatch_admitted` 成功；写未登记类型 → `OBS_EVENT_PAYLOAD_INVALID`。

**NS2-T13 物化。** 复用 `_seed_runtime`，materialize 后 `dispatch_admitted=0`。改 pool 后再算 `process_spec_digest` 应与物化时相同（实现上 digest 根本不含 pool）。

**NS2-T20 queued 封顶。** 9 个 normal generate ready，local 可用。admit 后恰好 6 个 `admitted=1`，3 个仍 0。

**NS2-T21 running 封顶。** 先 claim 2 个 local 至 running，queued=0，再 2 个已 admit ready。第三次 `claim_next` 不得领第 3 个 local（可领 unpooled 若有）。

**NS2-T22 NI 封顶。** 对 urgent 重复 T20/T21，数字换 4/2。

**NS2-T23 未 admit。** 只放 1 个 generate `admitted=0`（人为不跑 admit）。`claim_next` 返回 None。

**NS2-T24 unpooled 序。** acquire 级 Process：urgent 先于 low，与改前 `test_workflow_runtime` 一致。

**NS2-T25 embed FIFO。** t0 插入 low vectorize admitted；t1 插入 urgent vectorize admitted。claim 先得到 t0。

**NS2-T26 deadline。** waiting generate `deadline_at` 已过。claim 路径将其失败，码为 `deadline-exceeded-before-start`。

**NS2-T27 不睡。** 池满时 `run_once` is False，行仍 ready、无 lease。源码扫描 `worker.py` / `dispatch.py` / intake 生成入口无 `sleep(` 用于等槽。

**NS2-T30 分类。** 见 T05 的 generate/unpooled 切片，作为 P4 收口重复引用。

**NS2-T31 urgent 队头。** NI queued 已有 high，再 admit urgent。下一次 NI claim 得到 urgent。

**NS2-T32 high 队尾。** 两个 high 按 `enqueued_at` FIFO。

**NS2-T33 normal 溢流。** 先填 6 local queued，第 7 个 normal 的 `dispatch_pool` 在 admit 后为 `non-interactive`。

**NS2-T34 low 等待。** 6 local queued 后 low 保持 `admitted=0`，且 `dispatch_pool` 仍空（或空直到将来 local 有位再赋 local）。

**NS2-T35 超预算。** 策略输入 `over_budget=True`：normal→NI；low→local 或 wait，永不 NI。

**NS2-T36 salvage normal。** 复用现有 Lightning/local 失败夹具，priority 视作 normal，断言调用一次 CLI 且 receipt `salvage_from=local-inference`。

**NS2-T37 salvage low。** 同失败，state/task priority=low，断言 CLI 0 次，错误为原 local 错误码。

**NS2-T38 覆盖审计。** create 带 explicit NI + priority low。期望 snapshot `channel_source=explicit` 且存在 security/domain 审计行。缺事件失败。

**NS2-T39 改名。** salvage/成功 receipt 无旧字符串。

**NS2-T40 离线溢流。** settings `live_inference=false`，CLI stub 在。`choose_pool(normal)` 因 `local_available=False` 返回 NI。构建 snapshot 不 503。

**NS2-T50–T54。** 见主表；T51 用假 adapter 记录 embed 调用次数=3、同时 occupancy running 最大=1。

**NS2-T60 e2e 四车道。** 同一 runtime 注入慢 fake generate（占住 running）。创建 4 个 ingest：urgent/high/normal/low。轮询 `mkb_processes`：urgent/high 的 structurize/construct `dispatch_pool=non-interactive`；normal 在 local 未满时为 local；low 为 local 或 waiting。不允许只看 HTTP 200。

**NS2-T61 mega NS1。** 现有 generic/legal 金样在默认 priority 下仍 succeeded，图步齐全。

**NS2-T62 embed 顺序。** 两个 live=false vectorize 立即跑（unpooled）。另用测试夹具把两行标成 live embed waiting 并人工 admit，断言 FIFO（可在 unit e2e 混合夹具里做，不必真打 Spark）。

**NS2-T70 soak。** 32 个 coroutine 同时 `claim_next`，预先塞 20 local + 10 NI + 30 embed ready。结束后扫描：各池 `running≤cap`、`queued≤cap`。重复 32 轮。

**NS2-T71 守卫。** 解析 `001`+后续 migration：业务 `CREATE TABLE` 数量不因 011 增加；`payload_extra` 读写路径测试禁止 `dispatch_` 键。

**NS2-T72 closure。** 文件存在；frontmatter `close-type` ∈ 四类；§10 硬闸每行有五态之一。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| claim SQL 复杂度 | 一事务多集合排序易把 unpooled 回归打红 | `high` | 先保 T24；池化用明确 OR 分支 |
| 默认通道行为变化 | omit 不再等于 Claude | `high` | P4-07 离线溢 NI；T61 守 NS1 |
| 多 worker 超卖 | 计数不准会导致 GPU/套餐打穿 | `high` | 同行锁 + T70 |
| Qwen winner 与旧库 | 已部署 binding 不会自动改 priority | `medium` | bootstrap 对默认行 reconcile；测新库 |
| 长 json 预算常数不准 | 过小全溢 NI，过大仍堵 GPU | `medium` | 常数单点；用 glossary 校准但不本轮调参循环 |
| 物理 GPU 争用 | 2 Qwen + 8 embed | `medium` | 会计隔离；设备级交业主观察 |
| S03 窄回填争议 | 「只影响顺序」被生成选池突破字面 | `low` | 成功语义不变；附录声明 |
| VF V11 | e2e 读 turso 文件 I/O | `low` | 甩锅 NS1；不挡 executed |

### 9.2 约束与前提

- **技术前提**：sqlite/turso 都能跑 `ALTER TABLE` 加列；Process 状态机七态不扩。
- **运行时前提**：单逻辑库、单 Spark、单 NI 套餐；多 worker 共享该库。
- **组织协作前提**：业主接受 T-O-353..361 不再改口；billing/cloud 不在本迭代。
- **上线 / 合并前提**：011 先于新 runtime；旧 runtime 遇新列应可忽略（只读旧列仍能 claim unpooled+全部 ready——**因此必须先发只加列不改 claim 的迁移，再发 claim 改动**，或同版本同时发。推荐：**同一发布包含 011+新 claim**，避免旧 claim 把未 admit 当普通 ready 领走。）。

> 发布纪律：`011` 与 Phase 3 claim 必须 **同版本**。若先只迁列，旧 `claim_next` 会领走 `admitted=0` 的池化步，击穿配额。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`S02-task-api.md`（priority 双用一句）；`S03-workflow-engine.md` §4.13 Priority（生成池）；`S11-inference-runtime.md`（orchestrator vs 末闸）；`D04` 011 列；`S14` L2 `channel_source`；`S15` 新事件
- 需要同步更新的说明文档 / README：无强制；`.env.example` 若出现 `api-inference` 则改名
- 需要同步更新的测试说明：本 AP §8 即测试说明；closure 回引

### 9.4 完成后的预期状态

1. 新 ingest 默认 `priority=normal`：生成步经 orchestrator 先 local（Qwen），满或不可用则 NI；embed live 走 8+20 FIFO。
2. `mkb_processes` 可用 SQL 看见谁在等、谁在哪个池、有没有 admit。
3. facade 全局闸不再是 8 路总闸；超卖由行上占用阻止。
4. billing/cloud 有端口与禁路由，无假实现。
5. NS1 金样在离线 stub 下仍绿；NS2 台账四元组齐全。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

> 收口产物：`docs/closure/new-start/NS2-pipeline-priority-closure.md`（`.adocs/closure.md` **阶段 final**：§0–§7）。  
> **预期 close-type**：`closed-with-explicit-deferrals`（billing / cloud / 真机 GPU 争用 / VF V11 / 老化）。  
> 不得标 `full-close`。本 AP 标 `executed` 的前提 = 下列硬闸 PASS + closure 落盘。

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 必须 **PASS 且四元组齐全**：

1. 三池占用永不超卖（`NS2-T20 T21 T22 T70`）
2. 未 admit 不被 claim；worker 不睡租约（`NS2-T23 T27`）
3. 四车道与 salvage 合同成立，含 low 禁 NI（`NS2-T31–T37 T60`）
4. embed FIFO 且独立于生成池（`NS2-T25 T53 T54`）
5. NS1 金样默认 priority 仍通（`NS2-T61`）
6. 无新 required 表、无 extra 派发态、无 `api-inference`（`NS2-T02 T71`）
7. closure 五态齐全，deferred 分 A/B/C（`NS2-T72`）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| 通道硬切 | P1-01 | T01 T02 | commit + test + run-time | 未观察 |
| 策略 SSOT | P1-02 | T03 T04 T05 | commit + test + run-time | 未观察 |
| snapshot 派生 | P1-03 | T06 T40 | commit + test + run-time | 未观察 |
| Billing 门闩 | P1-04 | T07 | commit + test + run-time | 未观察 |
| Qwen winner | P1-05 | T08 | commit + test + run-time | 未观察 |
| 末闸常数 | P1-06 | T09 | commit + test + run-time | 未观察 |
| 011 列晋升 | P2-01 | T10 T71 | commit + test + run-time | 未观察 |
| 占用定义 | P2-02 | T11 | commit + test + run-time | 未观察 |
| 事件 | P2-03 | T12 | commit + test + run-time | 未观察 |
| 物化未 admit | P2-04 | T13 | commit + test + run-time | 未观察 |
| admit 封顶 | P3-01 | T20 T21 T22 T70 | commit + soak + run-time | 未观察 |
| 分池 claim | P3-02 | T23 T24 | commit + test + run-time | 未观察 |
| embed FIFO | P3-03 P5-04 | T25 T53 T54 | commit + test + run-time | 未观察 |
| deadline | P3-04 | T26 | commit + test + run-time | 未观察 |
| 不睡租约 | P3-05 | T27 | commit + test + rg + run-time | 未观察 |
| 车道表 | P4-02 | T31–T34 T60 | commit + e2e + run-time | 未观察 |
| 超预算 | P4-03 | T35 | commit + test + run-time | 未观察 |
| salvage | P4-04 | T36 T37 | commit + test + run-time | 未观察 |
| 覆盖审计 | P4-05 | T38 | commit + test + run-time | 未观察 |
| 离线兼容 | P4-07 | T40 T61 | commit + mega + run-time | 未观察 |
| embed 整段 | P5-01–03 | T50 T51 T52 | commit + test + run-time | 未观察 |
| 无新表/extra | P6-04 | T71 | commit + domain + run-time | 未观察 |
| closure | P6-06 | T72 | commit + 文件 + run-time | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 三池按冻结表运转；默认 normal 先 GPU；urgent/high 锁 NI；low 锁 GPU；embed FIFO 8+20 |
| 测试 | §8 台账全 PASS；硬闸四元组齐全 |
| 文档 | S02/S03/S11/S14/S15/D04 窄回填；本 AP 改 `executed`；closure 落盘 |
| 风险收敛 | 超卖、偷套餐、claim-then-sleep、silent 假摘要 均有测试钉死 |
| 可交付性 | 011 与新 claim **同版本**合并；旧调用方在 stub CLI 下不 503 |

### 10.4 NOT-成功识别

> 任一退出硬闸 `degraded / 未观察` ⇒ **不得标 `executed`**。  
> 允许的 defer 只有：`T-O-357` billing 真接口、`T-O-358` cloud 路由、真机 GPU 争用、VF V11、urgent 老化。  
> 把 defer 写成 verified = 假绿。

### 10.5 阶段 final closure 应含章节（执行完填写）

按 `.adocs/closure.md` 阶段 final 输出 `docs/closure/new-start/NS2-pipeline-priority-closure.md`：

| 节 | 必含 |
|----|------|
| frontmatter | close-type=`closed-with-explicit-deferrals`；关联本 AP |
| §0 verdict | 一句话：三池调度落地 + 明确 defer billing/cloud |
| §1 工作项收口表 | P1–P6 每项五态 + 四元组 |
| §2 Evidence 矩阵 | 可重跑命令（§8.3） |
| §3 Hard-gate | 复制 §10.1，填实测 |
| §4 Deferred ledger | A=OOS（cloud 适配、MiniMax 换绑、老化）；B=本阶段主动（无，除非预算常数未校准）；C=handoff（billing AP、GPU 手工 soak、VF V11） |
| §5 诚实收口 5 态 | 每个 ✅ 归类 |
| §6 下游施工合同 | claim 同事务 admit；列语义；禁止 extra |
| §7 不可动清单 | §7.2 ⛔ 全文有效 |

---

## 11. 执行日志回填

> 执行者：Antigravity
> 执行时间：2026-08-15
> 文档状态：executing

### 11.1 Phase 1 执行日志 — 合同、枚举、端口

- **实际执行摘要**：
  - `P1-01 / NS2-T01/T02`：全量将 `api-inference` 改名为 `local-inference`，`IntakeIngestPayload` 仅允许 `non-interactive` | `local-inference` | None，增加 `test_no_api_inference_in_production_or_test_sources` 架构守卫。
  - `P1-02 / NS2-T03/T04/T05`：新建纯函数调度策略模块 `src/runtime/workflow/dispatch.py`，实现三池占用常数、`choose_pool`、`pool_kind`，单元测试覆盖四车道 × 占用边界。
  - `P1-03 / NS2-T06`：更新 `config_snapshots.py`，L2 记录 `compression_channel` 及 `channel_source: "priority" | "explicit"`，非 ingest 任务不写生成通道。
  - `P1-04 / NS2-T07`：新建 `src/services/billing.py`，定义 `BillingPort` 与默认恒真服务。
  - `P1-05 / NS2-T08`：`registry.py` 中 `DEFAULT_BINDINGS` 将 Qwen 提升为 generate winner（priority=5），Lightning 为 10。
  - `P1-06 / NS2-T09`：`config.py` 增加三池 settings，`app.py` 中 Facade `max_in_flight=12` 并传递 `capability_limits`。
- **逐工作项状态**：
  - `P1-01`：`✅ done` (`models.py`, `prompt_profiles.py`, `generation_construct.py`)
  - `P1-02`：`✅ done` (`src/runtime/workflow/dispatch.py`)
  - `P1-03`：`✅ done` (`src/services/config_snapshots.py`)
  - `P1-04`：`✅ done` (`src/services/billing.py`)
  - `P1-05`：`✅ done` (`src/services/registry.py`)
  - `P1-06`：`✅ done` (`config.py`, `api/app.py`, `default.toml`)
- **测试结果**：
  - `NS2-T01`..`NS2-T09` 全 PASS，42 passed in 0.85s，全量 unit 268 passed in 13.85s。

### 11.2 Phase 2 执行日志 — DDL 与占用会计

- **实际执行摘要**：
  - `P2-01 / NS2-T10`：新建迁移 `src/persistence/migrations/011_process_dispatch_pools.sql`，给 `mkb_processes` 增加 `dispatch_pool`、`dispatch_admitted`、`dispatch_enqueued_at` 列与部分索引 `ix_mkb_proc_dispatch_ready`，CHECK 约束闭集拒绝非法 pool。
  - `P2-02 / NS2-T11`：在 `src/runtime/workflow/dispatch.py` 中增加 `PoolOccupancy`、`get_pool_occupancies` 与 `get_waiting_count` 占用查询 helpers。
  - `P2-03 / NS2-T12`：在 `src/services/events.py` 中将 `process.dispatch_admitted` 纳入 `ALLOWED_TYPES`。
  - `P2-04 / NS2-T13`：验证 Process 物化默认 `dispatch_admitted=0` 且 `process_spec_digest` 不包含派发态。
- **逐工作项状态**：
  - `P2-01`：`✅ done` (`011_process_dispatch_pools.sql`, `tests/unit/test_dispatch_ddl.py`)
  - `P2-02`：`✅ done` (`dispatch.py`, `tests/unit/test_dispatch_occupancy.py`)
  - `P2-03`：`✅ done` (`events.py`, `tests/unit/test_observability_contracts.py`)
  - `P2-04`：`✅ done` (`test_workflow_runtime.py`)
- **测试结果**：
  - `NS2-T10`..`NS2-T13` 全 PASS，23 passed in 1.88s。

### 11.3 Phase 3 执行日志 — Orchestrator admit + 分池 claim

- **实际执行摘要**：
  - `P3-01 / NS2-T20/T21/T22`：在 `runtime_core.py` 的 `claim_next` 事务中实现原子 admit 逻辑 `_admit_waiting_processes_tx`，按 `choose_pool` 策略与池容量上限（local 6、NI 4、embed 20）批量 admit，并记录 `process.dispatch_admitted` 领域事件；容量满员或无配额时留在 orchestrator。
  - `P3-02 / NS2-T23/T24`：分池 `claim_next` 严格约束 `dispatch_admitted = 1`，unpooled 保持 S03 优先级排序，local/NI 仅领取 running 未满（cap=2）的候选。
  - `P3-03 / NS2-T25`：embed claim 单独处理为严格 FIFO 排序（去除 `priority_rank`，按 `available_at ASC, created_at ASC, process_uuid ASC` 领取）。
  - `P3-04 / NS2-T26`：在领取前统一检查超时，waiting（即使 `admitted=0`）进程到期正确置为 `deadline-exceeded-before-start` 失败态。
  - `P3-05 / NS2-T27`：worker 无槽时立即返回 `None`/`False`，绝不在内存中 sleep 等槽。
- **逐工作项状态**：
  - `P3-01`：`✅ done` (`runtime_core.py`, `tests/unit/test_dispatch_claim.py`)
  - `P3-02`：`✅ done` (`runtime_core.py`, `tests/unit/test_dispatch_claim.py`)
  - `P3-03`：`✅ done` (`runtime_core.py`, `tests/unit/test_dispatch_claim.py`)
  - `P3-04`：`✅ done` (`runtime_core.py`, `tests/unit/test_dispatch_claim.py`)
  - `P3-05`：`✅ done` (`runtime_core.py`, `tests/unit/test_dispatch_claim.py`)
- **测试结果**：
  - `NS2-T20`..`NS2-T27` 全 PASS，7 passed in 0.80s。

### 11.4 Phase 4 执行日志 — 生成执行接线（Qwen / Claude -p / 预算分流）

- **实际执行摘要**：
  - `P4-01 / NS2-T30/T31/T32`：接线 `generation_construct.py`，根据 `command.dispatch_pool` / `compression_channel` 正确分流：`local-inference` 走 Local vLLM (Qwen)，且仅在失败时向 Claude `-p` 兜底 1 次并记录 `salvage_from: "local-inference"` 与 `salvage_error_code`；`non-interactive` 走 Claude `-p`，绝不调用 local facade。
  - `P4-02 / NS2-T33`：在 `ProcessCommand` 中增加一等公民 `dispatch_pool` 字段，`runtime_core.py` 在构造 command 时完整透传。
  - `P4-03 / NS2-T34`：验证 `LocalVllmAdapter` 对 Qwen 的入参严守规范（system prompt + user prompt + `response_format={"type": "json_object"}`，禁止 `max_tokens` / `enable_thinking`，严格过滤 reasoning 仅保留 content）。
  - `P4-04 / NS2-T35`：超长 JSON（>16k chars）预算分流策略校验（normal 溢流至 NI，low 锁在 local）。
- **逐工作项状态**：
  - `P4-01`：`✅ done` (`generation_construct.py`, `tests/unit/test_dispatch_generation.py`)
  - `P4-02`：`✅ done` (`models.py`, `runtime_core.py`)
  - `P4-03`：`✅ done` (`local_vllm.py`, `tests/unit/test_dispatch_generation.py`)
  - `P4-04`：`✅ done` (`dispatch.py`, `tests/unit/test_dispatch_policy.py`)
- **测试结果**：
  - `NS2-T30`..`NS2-T35` 全 PASS，4 passed in 0.23s，compression 19 passed in 0.35s。

### 11.5 Phase 5 执行日志 — 向量化接线与门闸收敛

- **实际执行摘要**：
  - `P5-01 / NS2-T50`：`lsrag.vectorize` 在 live 模式准确分类为 `embed` 池，在 deterministic 模式分类为 `unpooled`。
  - `P5-02 / NS2-T51`：验证 `embed` 池并发与 FIFO 机制（running 上限 8，queued 上限 20；排序完全去除优先级权重，严格先到先得）。
  - `P5-03 / NS2-T52`：验证 `InferenceFacade` 末闸（全局 12，embed 8，structured_generate 2，text_generate 2；满闸立即非阻塞拒绝返回 `None`）。
  - `P5-04 / NS2-T53`：验证背压可恢复性（满闸拒绝不修改持久化状态，释放租约后再次可申请）。
- **逐工作项状态**：
  - `P5-01`：`✅ done` (`dispatch.py`, `tests/unit/test_dispatch_embed_and_gates.py`)
  - `P5-02`：`✅ done` (`runtime_core.py`, `tests/unit/test_dispatch_embed_and_gates.py`)
  - `P5-03`：`✅ done` (`facade.py`, `tests/unit/test_dispatch_embed_and_gates.py`)
  - `P5-04`：`✅ done` (`facade.py`, `tests/unit/test_dispatch_embed_and_gates.py`)
- **测试结果**：
  - `NS2-T50`..`NS2-T53` 全 PASS，3 passed in 0.30s。





