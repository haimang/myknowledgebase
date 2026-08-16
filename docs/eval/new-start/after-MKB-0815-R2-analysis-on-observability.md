# after MKB-0815-R2 · 可观测性状态分析（建议 NS4 开发节点）

> **对象**：`after MKB-0815-R2（NS3 叶服务抽出之后 / R1–R2 live dogfood 之后）`
> **日期**：`2026-08-16`
> **作者**：`Grok`（panel：`none`）
> **文档性质**：`eval / state-analysis`（本文是现状快照 + 前瞻交接；不是 closure / verdict / charter）
> **文档状态**：`draft`
> **对照基线**：`S15-v1.1` + `D04` 可观测三表 + NS3 closure + MKB-0815-R1/R2 封存 run
> **上游权威输入**：
> - `docs/baseline/domain-truth/S15-observability-reliability.md`（执行 SSOT）
> - `docs/baseline/domain-truth/D04-turso-physical-schema.md`（三表 DDL 闭集）
> - `docs/closure/new-start/NS3-megafile-governance-closure.md`
> - `.experiment/0815/runs/MKB-0815-R1/results/analysis.md`（已封）
> - `.experiment/0815/runs/MKB-0815-R2/results/analysis.md`（RCA + §22）
> - R1/R2 `runtime/mkb.db` 实测行数
> **下游消费者**：`建议中的 NS4 observability-evidence charter`；R3 live 发车前的观测闸；业主是否批准旁路 diagnostic 接线

---

## 0. 水位 / 健康一句话（TL;DR）

- **一句话现状**：**生命周期时间线已经 durable，工人失败证据几乎没有。** R2 库有 453 条 `mkb_domain_events`、0 条 `mkb_ops_diagnostic_logs`；8 条 generation invocation **全是成功**；5 次 structurize 失败的 `payload_extra` 仍是 `{}`。
- **核心结论**：S15 的表、Writer、ReadPort、retention 都在。缺的不是「再建一套可观测库」，而是 **把 B/C/CLI 每个可导出环节 hook 回已有 durable 面**。NS3 把 S06/S07 抽成无 I/O 叶服务是对的；观测 I/O 必须停在 Mixin / live adapter，不能渗进叶包。建议把下一正式开发节点叫做 **NS4 · generation-evidence plane**：不新开表名，用 `domain_events`（同 TX 生命周期）+ `generation_invocations`（成功与失败）+ `ops_diagnostic_logs`（旁路、best-effort、可走 Turso `BEGIN CONCURRENT`）三层把 R1/R2 看不见的 candidate 形状、CLI envelope kind、墙钟拆开。R3 live 应在这层接上之后再打，否则又会得到「只有 error_code、没有 witness」的 jsonl。

---

## 1. 方法与对照基线

- **对照基线**：S15「事件同 TX、诊断 best-effort、禁止第二套表名」；D04 三表 + `mkb_generation_invocations` / `mkb_inference_invocations`；NS3「叶服务无 I/O」。
- **证据来源**：
  - 代码：`src/services/{events,observability}.py`、`src/runtime/intake/{generation_construct,generation_live,generation_artifacts}.py`、`src/runtime/inference/claude_cli.py`、`src/persistence/{engine,turso/port}.py`、`src/runtime/workflow/runtime_*.py`
  - 实测库：`.experiment/0815/runs/MKB-0815-R{1,2}/runtime/mkb.db`
  - 分析：R1/R2 `results/analysis.md`、族方案 §10–§12
  - 外部：Turso concurrent writes（MVCC / `BEGIN CONCURRENT`，2025-10-06）；Embedded Replicas 写转发文档
- **可采信等级**（沿用 R2 RCA）：`PROVEN` 库行/源码；`LEADING` 时序；`UNKNOWN` 无 witness；`DECISION` NS4 设计。
- **复现入口**：附录 A。

---

## 2. 回看清单（交付快照）

### 2.1 交付价值台账

| 单元 | 声称交付 | 真实落地（代码核） | 评级 | 锚点 |
|------|----------|--------------------|------|------|
| Domain events 同 TX | S15：业务变迁必写 `mkb_domain_events`，失败整 TX 回滚 | `DomainEventWriter` 闭集约 50 种；runtime/task/intake/vectorize 均调用。R2 **453** 行 | `delivered` | `src/services/events.py:16-61`；R2 `COUNT=453` |
| Diagnostic 三表 | S15：`mkb_ops_diagnostic_logs` 可 best-effort | `DiagnosticSink` 完整。**生产路径几乎无人调用**。R1=0、R2=0 | `placeholder` | `observability.py:72-120`；retention 是唯一生产 `write` |
| Security audit | S16 写、S15 留 | R2 仅 6 行，全是 `config.compression_channel_override` allowed。R1=0 | `partial` | R2 `mkb_security_audit_events` |
| Generation invocation 账 | S11：invocation 非 log 替代 | `_record_generation_and_inference_invocations` 在 **成功 callback** 写入。live API 失败走 `_persist_failed_*`。**CLI structurize 失败不写**。R2 8 行全 succeeded | `partial` | `generation_live.py:329-381`；R2 invocations |
| Inference invocation | S11 门面账 | `mkb_inference_invocations`：R2=3、R1=1。远少于 generate 步次数 | `partial` | `generation_live.py:396`；`vectorize.py:515` |
| Process error 面 | 失败有 `error_code` | 有码无形状。R2 五次 structurize 失败 `payload_extra='{}'` | `partial` | R2 `mkb_processes` |
| Operator 只读面 | S15 ObservabilityReadPort | `timeline_by_trace` / `timeline_by_task` 已实现。**0815 inspect 绕过它**，直接 sqlite dump | `partial` | `observability.py:240-318`；R2 `inspect_dump.py` |
| Ready/live | `/ready` 含 `obs_tables` | 预检与 create_app 走 health。不证明工人证据 | `delivered` | `runtime/health.py` |
| R3-EVD 直方图 / CLI kind | 分析 §22；本会话已合代码 | 代码在，**尚未被 live 任务跑过**。旧失败行不会回填 | `partial` | `layered_reject_histogram`；`cli_structured_kind` |
| 实验导出 | jsonl + inspect JSON | 成功格有六件套；失败格无 candidate。墙钟只有整 Task | `partial` | R2 `inspect/`、`runs.jsonl` 12 行 |

### 2.2 Deferred / Carried-over 台账（每条带 reopen 触发器）

| 编号 | 项目 | 为什么 defer | reopen 触发器 | 携带至 |
|------|------|--------------|----------------|--------|
| `D-01` | 新物理表（第四套 obs 表） | S15 `T-O-288` 禁止第二套表名 | owner 正式 reopen D04+S15 | 不交 NS4 |
| `D-02` | 把观测 I/O 放进 `lsrag_structurize` 叶包 | NS3 硬闸：叶服务无 I/O | reopen NS3 叶边界 | 禁止 |
| `D-03` | 失败路径落模型正文 / stdout | redaction + `payload_extra` 禁 `content`/`prompt` | 永不作为默认 | 禁止 |
| `D-04` | Mixin 拆分 / 去上帝类 | NS3 已 defer；观测接线不顺带重构 | 独立 D03 charter | 不交 NS4 |
| `D-05` | APM / OTLP 全量 span | S15 允许 export，0815 不需要 | 有多机 SLO 需求 | S15 后续 |
| `D-06` | Turso Cloud Embedded Replica 写转发 | 0815 是本机 `pyturso`/`sqlite` waiver，不是 Cloud replica | 部署切 Cloud + replica | 运维 charter |
| `D-07` | 回填 R1/R2 旧失败行的直方图 | 当时 candidate 未入库，无法事后发明 | 无 | 关闭 |

---

## 3. 对账诚实（本 flavor 灵魂段）

| 声称 | 真实 | 偏差类型 | 证据 | 影响 |
|------|------|----------|------|------|
| 「S15 可观测已落地」 | 表、Writer、retention、ReadPort 在；**诊断表空、失败 invocation 空** | `frozen≠done` | R2 diag=0；invocations 8 条全成功 | 0815 只能靠 error_code 归因 |
| 「generation invocation 覆盖 generate 步」 | 只覆盖 **成功** CLI markdown/B/C 和成功 Qwen B/C。失败 NI B 不落行 | `over-claim` | R2 5 次 structurize 失败 vs 2 条 structurize/construct invocation | 「吐了 g2」只能 LEADING |
| 「CLI 失败可观测」 | `CLAUDE_CLI_OUTPUT_INVALID` 一句话；envelope 类型丢失 | `placeholder` | R2 N-A5 root-2；`_cli_layered_candidate` 无 persist-failed | 分不清 list/str/空 |
| 「inspect 等于可观测平面」 | inspect 是 run 目录 JSON，不经 S15 ReadPort，失败格几乎无 artifact | `over-claim` | `inspect_dump.py` 直连 sqlite | 实验证据与产品面分叉 |
| 「DiagnosticSink 可用」 | 实现完整，生产几乎只有 retention 失败才写 | `placeholder` | 全库 `DiagnosticSink.write` 生产调用 1 处 | 表是空壳 |
| 「Turso 并发写已 mandatory」 | `concurrent_writes_required` 默认 True；**R2 Settings 显式 False + sqlite** | `frozen≠done` | `runner.py` `_settings`；`probe_concurrent_writes` | 0815 没练到 MVCC |
| 「R3-EVD 已加强可观测」 | 代码已合，旧行不会长出 extra | `under-claim` 若说已观测到；对「已接线」则诚实 | 现库 `payload_extra='{}'` | 必须 live 新 Task 才有直方图 |
| 「Q-A3 publish 证明观测够用」 | 证明成功路径六件套够用；**失败路径仍然瞎** | `over-claim` | 唯一 publish vs 11 失败 | 不能用单格成功洗白观测债 |

- **诚实结论**：MKB 不缺可观测**骨架**，缺 **工人失败的 hook**。R1/R2 把这件事从「可能」变成 `PROVEN`：同一套 kernel 码反复出现，库里却没有层直方图、没有 CLI kind、没有失败 invocation。NS4 若再只写 S15 原则文档而不接线，会重复 0815。

---

## 4. 归因 / 缺口分析

### 4.1 现在代码里的直接观测 / debug 节点

按流水线从外到内。**直接观测** = 写入三表 / invocation / process 列 / 公开 metric。**Debug 节点** = 仅 stderr、print、inspect 文件、jsonl。

| 环节 | 直接观测（durable） | Debug / 旁路 | R1–R2 实际看见 |
|------|---------------------|--------------|----------------|
| Task create / status | `task.created` / `task.status_changed` | 无 | 有 |
| Admit / claim / dispatch | `process.dispatch_admitted`（pool/priority/channel_source） | 无 | 有；能证明 N=NI、Q=local |
| Process 生命周期 | materialized / claimed / status / outcome / cleanup | 无 | 有，占事件大半 |
| Acquire–accept | intake snapshot/candidate 事件 | 无 | 有 |
| Markdown CLI | 成功才 `generation_invocations` + receipt 进 **state**（成功才落 artifact） | runner print | R2 多条 markdown succeeded invocation |
| Structurize **成功** | invocation + artifact + `generation.artifact_accepted` | inspect 六件套 | 仅 Q-A3 / R1 A5 / 部分 B-only |
| Structurize **失败（CLI）** | 仅 `error_code` + `error_message` | jsonl | **无 invocation、无直方图、无 envelope** |
| Structurize **失败（live/Qwen）** | live 路径有 `_persist_failed_generation_invocation` | 同左 | R2 Q 失败仍无 structurize failed 行（多在 admit 后，invocation 已成功或未写） |
| Construct 失败 | kernel 码；成功才有 C invocation | jsonl | R1 A5g2 / R2 wave1 N-A6 |
| Vectorize | `vector.upserted`；inference 行 | 无 | 成功格有 |
| Retrieval | HTTP 200/422；inspect request/response 文件 | **不写 domain_events** | F5 后 6×200 只在文件里 |
| DiagnosticSink | 表存在 | 几乎不写 | 0 行 |
| Experiment runner | 无 | `print` + `runs.jsonl` + `inspect/` | 主证据面 |

关键代码缝（`PROVEN`）：

1. `_cli_layered_candidate`（`generation_construct.py:372`）成功才组 receipt；`cli.run` 抛错或 `structured` 非 object 时 **没有** 对等的 `_persist_failed_generation_invocation`。
2. `LsragStructurizeService.admit` 失败发生在 CLI **已经成功交出 JSON 之后**。此时有 candidate，旧代码直接抛 `STRUCTURE_*`，不写 invocation。R3-EVD 把直方图挂上 `MkbError.details`→`payload_extra`，但仍 **不写** `mkb_generation_invocations`。
3. `IntakeCoreMixin._outcome_from_error` 过去丢掉 `details`。已补 allowlist；**旧行不会回填**。
4. `DiagnosticSink` 未注入 intake Mixin。工人阶段零 diagnostic。
5. `_record_event_tx` 与业务同连接。LLM 等待若包在同一写事务里会锁库；今日实现是 **等模型返回后再开 TX**，所以不是锁等待模型，而是 **失败时少一次 TX**。

### 4.2 逻辑结构：observability plane 该建在哪

```text
                    ┌─────────────────────────────┐
                    │  S15 ObservabilityReadPort  │  只读；实验 inspect 应改走这里
                    └─────────────▲───────────────┘
                                  │
         ┌────────────────────────┼─────────────────────────┐
         │ 同 TX（业务成功/失败 SSOT 旁的时间线）              │ 旁路（不得回滚业务）
         │  DomainEventWriter                                 │  DiagnosticSink
         │  generation_invocations (成功+失败)                │  + 可选第二连接 BEGIN CONCURRENT
         │  process.error_* / payload_extra                   │
         └────────────────────────▲─────────────────────────┘
                                  │ 只允许 I/O 层调用
         ┌────────────────────────┴─────────────────────────┐
         │  Intake Mixin / generation_live / claude_cli     │  ← NS4 接线面
         │  WorkflowRuntime admit/claim                     │
         └────────────────────────▲─────────────────────────┘
                                  │ 无 I/O（NS3 已锁）
         ┌────────────────────────┴─────────────────────────┐
         │  lsrag_structurize / lsrag_construct / compiler  │  禁止观测写入
         └──────────────────────────────────────────────────┘
```

**合适创建位置**不是新服务进程，也不是叶包内部，而是：

| 位置 | 为什么合适 | 为什么不是别处 |
|------|------------|----------------|
| `generation_construct` Mixin（CLI B/C/markdown 之后） | 唯一同时看见 receipt、candidate、admit 异常的地方 | 叶服务禁止 I/O |
| `generation_live._persist_failed_*`（已有） | live/Qwen 失败模板，CLI 应对齐 | 不要复制第三套 |
| `IntakeCoreMixin._outcome_from_error` | 所有叶失败汇合点 | 不要在每个 except 手写 SQL |
| `DiagnosticSink` 独立连接 | 诊断失败不得回滚 CAS | 不要塞进业务 UoW |
| `ObservabilityReadService` | 产品/实验同一读面 | 不要让 0815 永远直连 sqlite |

**结构逻辑**：NS3 拆的是「判定」（admit/construct kernel），NS4 补的是「判定之后的证据出口」。两者正交。把出口放回叶包 = 撤回 NS3。新建第四表 = 撤回 S15。

### 4.3 现象 → 根源

| 现象 | 归因（根源/缝/簇） | 根源位置 |
|------|---------------------|----------|
| R2 失败无 candidate 化石 | CLI/admit 失败不写 invocation；admit 不落 artifact | `_cli_layered_candidate`；`_structurize` except |
| `GRANULARITY_SET_MISMATCH` 不知是否吐了 g2 | 只有 message 字符串 | 旧 `_outcome_from_error` 丢 details |
| `CLAUDE_CLI_OUTPUT_INVALID` 无法分型 | decode 把非 object 收成 None | `claude_cli.py`（kind 已补，未 live） |
| diagnostic 表恒 0 | 无生产 hook | Mixin 未持有 DiagnosticSink |
| 实验靠目录 JSON | inspect 是文件面不是产品面 | `inspect_dump.py` |
| R2 不用 Turso 并发写 | 实验 Settings 关闸 | `runner.py` `concurrent_writes_required=False` |

---

## 5. Verdict（价值-债务 / 达成度 / 健康评级）

| 维度 | 评级 | 一句话 |
|------|------|--------|
| 交付价值 | `medium` | 生命周期时间线与成功六件套够做「跑没跑、进了哪池」 |
| 累积债务 | `high` | 工人失败面空；诊断表空；实验面与 S15 读面分叉 |
| 愿景/目标达成度 | `low-medium` | S15 十条价值里，0815 只用到「事件同 TX」一条 |
| **综合健康** | `conditional` | 骨架健康，hook 不健康；不挡 Q-A3 成功，挡不住下一枪归因 |

- **反镀金提醒**：不要上 APM、不要新表、不要在叶服务打点、不要把模型正文写入 events。NS4 只接线已存在的三表 + invocation 账。R3 live 前至少接上 **失败 invocation + extra 直方图 + CLI kind**（后两项代码已在，缺 CLI 失败落账与 DiagnosticSink 旁路）。

---

## 6. 前瞻交接

### 6.1 建议的 NS4 开发节点（非正式 charter，供业主拍板）

NS1 身份/catalog → NS2 三池 → NS3 叶边界 → **NS4 generation-evidence plane**。

| 节点 | 目标 | 验收 | 不做什么 |
|------|------|------|----------|
| **NS4-P0** | 冻结本文 + 证据闭集（直方图 / kind / 失败 invocation 字段） | 本文 + architecture 守卫：叶包仍无 I/O | 不改 kernel |
| **NS4-P1** | CLI 失败与 admit 失败都写 `mkb_generation_invocations`（status=failed，无 body） | R3 任一 structurize 失败 → invocation 行 + `error_code` | 不落 stdout |
| **NS4-P2** | Mixin 注入 `DiagnosticSink`；阶段开始/结束/拒绝写 diagnostic（best-effort） | R3 live 后 `mkb_ops_diagnostic_logs` > 0；业务失败不因 sink 失败而改码 | 不进业务 TX |
| **NS4-P3** | 旁路连接 + 可选 `BEGIN CONCURRENT`（见 §6.3） | probe 绿才开 MVCC；sqlite waiver 仍串行 sink | 不把 LLM 等待包进写事务 |
| **NS4-P4** | 实验 inspect 改走 `ObservabilityReadService` + invocation/extra | `inspect_dump` 不再是唯一入口 | 不删 jsonl |
| **NS4-P5** | R3 live 消费 P1–P2 | 新 `-r3` 失败行 extra ≠ `{}` | 不删 Q-A3 |

P1–P2 是 R3 前 **最小加强**（P1 尚未做完：CLI 失败仍可能不落 invocation）。P3 是 Turso 性能；P4 是产品/实验读面合一。

### 6.2 start-gate（下一 charter day-1）

- 不新增 D04 表名。
- 叶包 `lsrag_*` architecture 测试保持「无 persistence import」。
- Q-A3 serving 仍在。
- 红action：extra/diagnostic 禁 `content`/`prompt`/stdout。
- R3 live 命令仍是 `collect.py --cells N-A5,N-A3,N-A6,N-A2,Q-A5 --suffix -r3 --no-extras --rerun`。

### 6.3 需 owner 拍板

1. NS4 是否立为正式 new-start 阶段（有 AP/closure），还是只作为 R3 前补丁簇？
2. P1（失败也写 invocation）是否允许在 R3 live **之前**再合一次？（推荐是）
3. 0815 实验库是否保持 sqlite waiver，还是 R3 起改 `persistence_backend=turso` 以练 `BEGIN CONCURRENT`？
4. inspect 是否必须在 NS4-P4 前继续双写（文件 + 表）？

### 6.4 下一周期建议

先做 **NS4-P1**（CLI/admit 失败 invocation），再发 R3 live。否则 N-A5 再红仍只有一句话。P2 DiagnosticSink 可与 P1 同 PR，但必须独立 TX。P3 仅当 owner 打开 Turso 后端。

---

## 7. [profile] Spike / Test 水位评级

| Spike / 单元 | 上一基线（R1） | 本次（R2） | D | W | E | 备注 |
|--------------|----------------|------------|---|---|---|------|
| 生命周期 events | 532 | 453 | 覆盖够 | 形状空 | 可检索 | 第二枪 6 Task |
| Diagnostic 行 | 0 | 0 | 无 | 无 | 无 | 表空 |
| Generation invocation | 9 全成功 | 8 全成功 | 成功路径 | 失败路径 | 无失败样本 | |
| Inference invocation | 1 | 3 | 稀 | 稀 | 稀 | |
| Process extra 非空 | 0 | 0 | 无 | 无 | 代码已补未跑 | |
| 检索证据 | 6×422 文件 | 6×200 文件 | 文件有 | 表无 | 无 event | |
| Publish 六件套 | A5 | Q-A3 | 有 | 仅 1 格 | 有 | |

- **水位裁定**：时间线 **W 已够**；工人失败证据 **D 未开**。R3 若只改提示词、不接 P1，水位不会动。

---

## 8. [profile] 债务评分台账

| 编号 | 债务 | 内聚 | 紧急 | 复杂 | 风险 | 价值 | 建议顺序 |
|------|------|------|------|------|------|------|----------|
| `OBS-01` | CLI/admit 失败不写 invocation | H | H | L | L | H | 1 |
| `OBS-02` | DiagnosticSink 未接入 intake | H | H | L | L | H | 2 |
| `OBS-03` | extra 直方图未 live | H | M | L | L | H | 随 R3 |
| `OBS-04` | inspect 绕过 ReadPort | M | M | M | L | M | 4 |
| `OBS-05` | 实验关 Turso 并发写 | M | L | M | M | M | 5 |
| `OBS-06` | 检索不写 domain_events | L | L | L | L | L | 6 |
| `OBS-07` | Mixin 过大不便接线 | H | L | H | H | L | 不交 NS4 |

- **closure 判据 / DAG**：

```text
OBS-01 -> OBS-03 -> R3 live
OBS-02 -> R3 live（可并行 OBS-01）
OBS-04 可后置
OBS-05 仅当 backend=turso
OBS-06 可选
OBS-07 禁止搭车
```

R3 live 的 closure：新失败行 `generation_invocations.status=failed` 或 `payload_extra.structure_reject` / `cli_structured_kind` 至少一项非空。

---

## 6.3 展开：Turso 结构、旁路写入、并发写（可落地接线）

> 本节对应业主第 3 问。结论先说：**不要为观测新建表；不要把观测写进业务 UoW；旁路用第二连接 + 可选 `BEGIN CONCURRENT`。**

### 6.3.1 库里已经有的结构（禁止再发明）

| 表 | 角色 | 写纪律 |
|----|------|--------|
| `mkb_domain_events` | 生命周期时间线，非 SSOT | **同业务 TX**；失败回滚整笔 |
| `mkb_ops_diagnostic_logs` | 诊断，非 SSOT | **独立 TX**；失败不回滚业务（S15） |
| `mkb_security_audit_events` | 准入/覆盖 | 独立；R2 已有 channel override |
| `mkb_generation_invocations` | 工人调用账（无正文） | 成功 callback 同 TX；失败应用独立 TX（live 已如此） |
| `mkb_inference_invocations` | 门面调用账 | 同上 |
| `mkb_processes.payload_extra` | 失败诊断袋 | 随 outcome；只允许闭集键 |

S15 `T-O-288`：禁止第二套可观测表名。NS4 新证据形状进 **JSON 闭集**（`structure_reject` / `cli_structured_kind` / diagnostic `log_code`），不进 DDL。

### 6.3.2 旁路写入方式（对照现码）

今日业务写路径：

```text
stage 跑完（可能已等 LLM 数分钟）
  -> 开 persistence.transaction()
  -> CAS process + domain_events + 成功 invocation
  -> commit
```

失败 CLI 路径在等 LLM **之后** 往往 **不再开第二笔账**。旁路正确形态：

```text
LLM / admit 返回
  -> 业务 TX：CAS + error_code + extra +（可选）failed invocation
  -> 提交
  -> 旁路 TX（可失败）：DiagnosticSink.write(...)
```

或对「纯诊断、不影响码」：

```text
LLM 返回
  -> 旁路连接 BEGIN CONCURRENT
  -> INSERT diagnostic
  -> COMMIT
  -> 再开业务 TX
```

**禁止**：把 LLM HTTP/CLI wait 包进已 `BEGIN` 的写事务（SQLite 会锁死；Turso MVCC 也会拉长冲突窗口）。0815 现状基本遵守「先等后写」；旁路只要 **不要共用那一个 UoW**。

`DiagnosticSink` 已是 best-effort + metric + stderr。缺的是 **Intake Mixin 持有 sink 并在每个 generate 阶段调用**。

### 6.3.3 Turso 并发写：检索结论与本仓库已有探针

外部事实（可引用）：

- Turso Beta 用 **MVCC** 实现 `BEGIN CONCURRENT`，提交时行级冲突，不再整库单写者。官方称带计算的多线程写入可达 SQLite 约 **4×**，并消除典型 `SQLITE_BUSY`（[Concurrent Writes](https://turso.tech/blog/beyond-the-single-writer-limitation-with-tursos-concurrent-writes)，2025-10-06）。
- Embedded Replica：**读本地、写转发主库**，转发写不能并行（[SDK reference](https://docs.turso.tech/sdk/ts/reference)）。这与 0815 本机 `import turso` 嵌入引擎不是同一部署。
- 本仓库已实现探针，且与手册一致：先 `PRAGMA journal_mode=mvcc`，再 `BEGIN CONCURRENT` / `ROLLBACK`（`src/persistence/engine.py:13-34`）。`TursoPersistence` 在 `concurrent_writes_required=True` 时把探针结果打进 `/ready`。

0815 R2 **主动关掉** 该闸（`concurrent_writes_required=False`，backend=`sqlite`）。所以「用并发写增强观测性能」在本 run **未观察**。

### 6.3.4 可接线方案（按部署分叉）

**方案 A — 0815 / R3 默认（sqlite waiver，推荐先做）**

1. Mixin 构造时注入已有 `DiagnosticSink(persistence, metrics)`。
2. `_cli_layered_candidate` / `_structurize` except：先 `_persist_failed_generation_invocation`（复制 live 函数，独立 TX），再抛原错。
3. sink.write：`log_code` 用闭集 `GEN_STRUCTURIZE_REJECT` / `GEN_CLI_ENVELOPE` / `GEN_CONSTRUCT_REJECT`；payload 只含直方图或 kind + `latency_ms`。
4. 仍用同一 sqlite 文件、**另一短事务**。不启用 MVCC。性能足够（每失败 1 行）。

**方案 B — 本机 pyturso + MVCC（owner 打开 turso backend 后）**

1. `Settings.persistence_backend=turso`，`concurrent_writes_required=True`。
2. 新增 `ObservabilitySidecar`：`TursoPersistence` **第二个连接** 到同一文件（或 `connect` 后再 `PRAGMA journal_mode=mvcc`）。
3. sidecar 写路径：

```text
conn.execute("BEGIN CONCURRENT")
conn.execute("INSERT INTO mkb_ops_diagnostic_logs (...)", bind)
conn.execute("COMMIT")
```

冲突：重试 1 次，仍失败 → increment `mkb_retention_job_fail` 同类低基数 metric + stderr，**不**改 Process 码（S15 diagnostic 失败策略）。

4. 业务 CAS 继续走主 `UnitOfWork`（可保持默认事务；不必把 admit 改成 CONCURRENT，避免与 CAS 行冲突语义纠缠）。
5. 适用：多 Task 并行 ingest 时诊断写入不再和成功路径抢单写锁。

**方案 C — Turso Cloud Embedded Replica（明确不纳入 NS4）**

写转发主库、replica 读。观测旁路若打 replica 会串行转发，**更慢**。只在多节点读多写少时有意义。0815 单机 dogfood 不需要。

### 6.3.5 性能原则（真实、可测）

| 做法 | 要 | 不要 |
|------|----|------|
| 批量 | 一阶段一条 diagnostic，禁止 per-block INSERT | 在 C 的每块循环写库 |
| 事务跨度 | 只包 INSERT | 包 `claude -p` / vLLM HTTP |
| 冲突 | sidecar CONCURRENT + 1 次重试 | 业务 CAS 用 CONCURRENT 碰同一 process 行 |
| 基数 | log_code 闭集、无 uuid label | 把 task_uuid 当 Prometheus label |
| 体积 | 直方图 counts + kind | stdout / original / prompt |

可测假说（NS4-P3）：同文件 turso、8 线程各写 100 条 diagnostic。sqlite 单写者墙钟 vs MVCC `BEGIN CONCURRENT` 墙钟。未测不得宣称 4×。

---

## 6.4 MKB-0815 系列：可观测加强分析与执行推荐

结合 R1/R2 RCA，0815 真正缺的观测是下面这张「失败能回答什么」。

| 失败码（已出现） | 现在能回答 | NS4 后应能回答 |
|------------------|------------|----------------|
| `STRUCTURE_SUMMARY_INVALID` | 填了 summary | 仍只要码；直方图可选 |
| `STRUCTURE_ANCHOR_MISSING` | g0 或 substring | `has_g0`、`block_count`、是否缺层 |
| `STRUCTURE_GRANULARITY_SET_MISMATCH` | 层集合不对 | `set` 是否含 2、`counts["2"]` |
| `STRUCTURE_SCHEMA_INVALID` | 哪条 schema 句 | 保持 message；不要正文 |
| `CLAUDE_CLI_OUTPUT_INVALID` | 不是 object | `cli_structured_kind` |
| `CONSTRUCT_KERNEL_ORIGINAL_MUTATION` | C 改了 original | 已够；可选 failed C invocation |
| 检索 422 | F5 后已消失 | 可选 `retrieval.search` event；非阻塞 |

**执行推荐（有序）**

1. **R3 前（仍建议做，未发车）**：NS4-P1——CLI 与 admit 失败写 `generation_invocations`。P2——Mixin 接 `DiagnosticSink`。二者都不改 kernel、不删库。
2. **R3 live**：5 格 `-r3`。验收改为：失败行必须带 extra 或 failed invocation，否则该格观测不合格（即使 error_code 仍是旧码）。
3. **R3 后**：NS4-P4 inspect 走 ReadPort；需要时再开 P3 Turso sidecar。
4. **不要**为了观测重建 `mkb.db`。

这与已冻的 R3 目标兼容：提示词 v3 解决「少吐 g2」；观测解决「若仍吐 g2 能证明」。两件事一起才构成完整 R3。

---

## 附录

### A. 复现命令

```bash
# 三表与 invocation 水位（R2）
sqlite3 .experiment/0815/runs/MKB-0815-R2/runtime/mkb.db \
  "SELECT 'events',COUNT(*) FROM mkb_domain_events
   UNION ALL SELECT 'diag',COUNT(*) FROM mkb_ops_diagnostic_logs
   UNION ALL SELECT 'sec',COUNT(*) FROM mkb_security_audit_events
   UNION ALL SELECT 'gen_inv',COUNT(*) FROM mkb_generation_invocations
   UNION ALL SELECT 'inf_inv',COUNT(*) FROM mkb_inference_invocations;"

sqlite3 .experiment/0815/runs/MKB-0815-R2/runtime/mkb.db \
  "SELECT event_type,COUNT(*) FROM mkb_domain_events GROUP BY 1 ORDER BY 2 DESC;"

sqlite3 .experiment/0815/runs/MKB-0815-R2/runtime/mkb.db \
  "SELECT json_extract(payload_extra,'$.stage_key'), json_extract(payload_extra,'$.status')
   FROM mkb_generation_invocations;"

sqlite3 .experiment/0815/runs/MKB-0815-R2/runtime/mkb.db \
  "SELECT step_key,error_code,payload_extra FROM mkb_processes WHERE error_code IS NOT NULL;"

# 谁在写诊断
rg -n "DiagnosticSink|diagnostics.write" src tests

# 失败 invocation 是否只在 live
rg -n "_persist_failed_generation_invocation|_cli_layered_candidate" src/runtime/intake

# Turso 并发写探针
rg -n "BEGIN CONCURRENT|probe_concurrent_writes" src/persistence

# 事件闭集
rg -n "ALLOWED_TYPES" -A 50 src/services/events.py
```

### B. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-16 | Grok | 初稿：对账 R1/R2 库行；建议 NS4 evidence plane；Turso 旁路/CONCURRENT 接线 |
