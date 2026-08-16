# NS4 — Generation-evidence plane · Singular Owner-Gated Q&A

> **项目**：`myknowledgebase`（MKB）
>
> **范围**：`NS4`（new-start · generation-evidence **平台**：一等 schema、Turso 主路径、唯一读面；R3 只在本节点 closure 之后）
>
> **qna 位点**：`pre-charter`
>
> **角色配置**：提问 `Grok` · second-opinion `none` · 裁决 `owner`
>
> **second-opinion 模式**：`retired`（本文件不设、不渲染 second-opinion 栏）
>
> **方法约束**：`.adocs/qna-singular.md`（单轮一次性 · 一批问题、业主逐题裁决、一次冻结）
>
> **上游架构真相**：`D04`（Turso 物理宪法；`T-O-173` 禁 extra 当 proof；核心真相不得只活在 JSON）；`S11` invocation 账；`S12` Turso/CW/ready；`S15-v1.1` / `T-O-287..311`；NS1 `T-O-337..352`；NS2 `T-O-353..361`；NS3 叶无 I/O；`T-O-340` 禁静默换工人
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **工作笔记（非 Truth）**：`docs/eval/new-start/after-MKB-0815-R2-analysis-on-observability.md`；R2 `results/analysis.md`；`r3_objectives.md`
>
> **下游消费者**：NS4 charter / action-plan / D04+S15 窄 reopen / S12 Settings 硬切 / R3 live（仅 NS4 closure 后）
>
> **文档状态**：`locked / Q1–Q8 frozen / T-O-362..375 / ready for NS4 AP`
>
> **版本 / 日期**：`v1.0-qna-locked / 2026-08-16`

> **★ 接线叙事作废；本表为唯一口径**  
> 同路径曾存在接线版 `v1.0-qna-locked`（extra 口袋 / sqlite waiver / P1 后发 R3）。业主否决后整文件重写为 v0.2。该版预占号 **从未进入** `spec-index` / `domain-truth`。**本冻结**把 `T-O-362..375` 重新授予本节一句话口径；下游只许引用本表，不许引用已删正文。

> **★ 本 Campaign 证据授权**  
> 1. 已接受 baseline（`docs/baseline/**`）；  
> 2. NS1–NS3 已冻 `T-O` 与 closure（围栏，不是「继续 hotfix」许可）；  
> 3. 0815 R1 已封 + R2 RCA / 库行 / 源码为 `PROVEN` 水位；R2 未封，不升格为 Truth；  
> 4. 代码事实：`DiagnosticSink`、`ObservabilityReadPort`、`_persist_failed_generation_invocation`、`structure_reject`、`cli_structured_kind`、`probe_concurrent_writes`。  
> **禁止**吸收 `context/legacy-specs/**`、`context/legacy-python/**`、`context/legacy-python-2/**`。  
> 与本 QNA 冲突时，以本文件业主答复为准。

> **Owner-originated application boundary（继承 `T-O-42`）**：不建设 console 运营中台，不继承 `smind_logs` 作跨进程 SSOT。NS4「平台」= **主库一等证据面 + Turso 接线 + 唯一 ReadPort**，不是第二套 APM SaaS（`T-O-300`）。

> **本版统一叙事（业主 2026-08-16，写入围栏，题内不再提供相反推荐）**：
> 1. **能硬切必须硬切**。不合适的代码位置删除，不留兼容分支。  
> 2. **不得双写**。不得兼容旧 seam。不得用 hotfix / extra 口袋治理。  
> 3. **长期治理 schema 一次到位**，并用 contract 严格校验。  
> 4. **Turso 是核心业务功能**，必须在本节点推进，禁止无期限 defer。  
> 5. **P0–P4 全部完成并充分测试 → NS4 closure → 才允许 R3**。R3 不是 NS4 相位。

> **Singular 纪律**：
> 1. 全部仍需拍板的分叉一次写完。不生成第二轮。  
> 2. 每题：**完整选项**、**推荐**、**执行细节**、**Reasoning**、**内部证据**、**残差风险**。被叙事排除的旧路线仍列出，标为 **否决项**，防止再被选成「务实折中」。  
> 3. 本文件已冻结：`T-O-362..375`。Truth-ID append-only；后续仅 `T-O-376+`。NS2 已占用 `353..361`。  
> 4. 本文件不含 second-opinion 栏。  
> 5. 实现命名 / 单测文件名 / commit 拆法不进本题。

> **Truth-ID 连续性**：NS1=`T-O-337..352`；NS2=`T-O-353..361`；NS4 本文件=`T-O-362..375`；全局下一空号 **`T-O-376`**。禁止复用或改写已冻 baseline ID。

---

## 0. 状态总览

| 段 | 题号 | 层级 | 单一焦点 | 状态 |
|---|---|---|---|---|
| Pre-round fence | — | fence | 硬切 / 禁双写 / 禁 extra 当证据 / Turso 必推 / P0–P4 后才 R3 / kernel 不放宽 | `frozen / T-O-362..367 · 随 Q1–Q8 一并确认` |
| Evidence | — | evidence | R1/R2 库行；D04-P04 / `T-O-173`；S12 CW 探针 | `completed / 2026-08-16` |
| Cluster 1 | `Q1` | foundational | 平台治理形态 + 是否正式 reopen D04/S15 | `frozen / T-O-368 · owner 2026-08-16` |
| Cluster 2 | `Q2–Q3` | execution | 一等 schema 形状；写入 fail-closed 边界 | `frozen / T-O-369..370 · owner 2026-08-16` |
| Cluster 3 | `Q4–Q5` | execution | Turso/CW/CONCURRENT 范围；旧库 / Q-A3 迁移一次还是重置 | `frozen / T-O-371..372 · owner 2026-08-16` |
| Cluster 4 | `Q6–Q7` | execution | 相位顺序；唯一读面（删 dump） | `frozen / T-O-373..374 · owner 2026-08-16` |
| Cluster 5 | `Q8` | acceptance | R3 格、提示词、双轴验收（NS4 结束后） | `frozen / T-O-375 · owner 2026-08-16` |
| Truth-Gate | — | freeze product | `T-O-362..375` | `frozen / 2026-08-16` |

### 0.1 推荐组合（可整包接受）

| 题 | 推荐 | 一句话 |
|---|---|---|
| **Q1** | **B** | 正式立 NS4；**窄 reopen D04+S15**；不新开进程、不建设 APM 产品 |
| **Q2** | **B** | 一等列晋升 + **一张**证据表；`payload_extra` 不再承载 reject / kind / 失败语义 |
| **Q3** | **B** | 证据表 + generation/inference invocation **与 Process Outcome 同 TX**（缺行则整笔失败）；diagnostic 仍 best-effort（S15 分账，不是兼容层） |
| **Q4** | **B** | 应用与 0815 **硬切** `persistence_backend=turso` + `concurrent_writes_required=True`；诊断 sidecar `BEGIN CONCURRENT`；业务 CAS 保持默认 TX；sqlite **仅** pytest |
| **Q5** | **B** | **一次迁移** Q-A3 serving/向量到新 Turso schema，然后删除 sqlite 生产路径；旧失败 extra **不**回填；禁止双读 |
| **Q6** | **C** | 顺序：P0 冻合同 → **P3 Turso/CW 先立** → P1 schema+同 TX 写入 → P2 diagnostic → P4 删 dump / 只留 Port → closure → **然后** R3 |
| **Q7** | **B** | 删除 `inspect_dump` 直连路径；实验与产品 **只**走 `ObservabilityReadPort`；jsonl 只作 0815 封存期刊，不存 schema 证据 |
| **Q8** | **A** | 五格 `-r3`；g1 v3 冻结；产品轴 `R3_READY`；观测轴看 **一等行** 是否在，不看 extra |

**业主整包接受（2026-08-16）**：Q1=B，Q2=B，Q3=B，Q4=B，Q5=B，Q6=C，Q7=B，Q8=A；围栏 F1–F12 一并确认。改口须在本文件追加修订并新 append `T-O-376+`。

### 0.2 本版直接否决（不得再选成折中）

| 否决 | 为什么 |
|---|---|
| 把 `structure_reject` / `cli_structured_kind` / 失败 status 塞进 `payload_extra` | 违反 `T-O-173` / D04「核心真相不得只活在 JSON」；业主禁止 extra 债务 |
| sqlite 生产/0815 waiver、CW 无期限 defer | Turso 是 D04/S12 核心，不是实验开关 |
| P1 后发 R3、P3/P4 后置 | 业主要求 P0–P4 测完、NS4 结束后才 R3 |
| 双写 extra+列、dump+Port、sqlite+turso 并行读 | 业主禁止双写与旧 seam |
| `getattr` 可选 persist、成功-only invocation 继续活着 | 兼容缝 |
| 新 APM 进程 / 公网 metrics 产品 | `T-O-300` / OD-01 |
| 放宽 kernel、静默换工人、删库却双路径 serving | 已冻围栏 |

---

## 1. ★ Truth-Gate 台账（冻结产物 · owner-gated · 供 planning §2 CITE）

> **已冻结（2026-08-16）**。业主整包接受新叙事推荐 + 围栏 F1–F12。ID `T-O-362..375` append-only。后续仅 `T-O-376+`。禁止改写本表已登记行。接线叙事下的同号预占 **作废**；只许引用本节一句话。
>
> 围栏 6 条（`T-O-362..367`）收窄本版硬切/Turso/顺序叙事。Q1–Q8（`T-O-368..375`）是本 campaign 新执行真相。

| Truth-ID | 子类型 | 真相内容（一句话 · 下游唯一口径） | 来源 Q | 下游约束 |
|----------|--------|----------------------------------|--------|----------|
| `T-O-362` | `foundational / fence-hard-cut` | NS4 **能硬切必须硬切**：删除不合适代码位置，不留兼容分支、适配开关、`getattr` 可选账、「成功才记账」。**禁止双写**：同一事实不得同时进 extra 与列、dump 与 Port、sqlite 与 turso。迁移窗口 = 一次性转换 + 删旧路径。 | 围栏 F1+F2 · 业主 2026-08-16 | AP 停工：兼容层 / 双路径 |
| `T-O-363` | `foundational / fence-no-extra-proof` | **禁止** hotfix 治理。`structure_reject` / `cli_structured_kind` / invocation 成败 **不得** 只活在 `payload_extra`。证据必须是一等列或 D04 登记表，并经 contract 校验。对齐 `T-O-173` / D04-P04。 | 围栏 F3；`T-O-173` | extra allowlist 删除证据键 |
| `T-O-364` | `foundational / fence-turso` | **Turso 是核心业务功能**，必须在本节点推进。禁止把 `persistence_backend=sqlite` 或 `concurrent_writes_required=False` 当作生产/0815 无期限默认。sqlite 仅测试夹具。 | 围栏 F4；D04；S12 | Settings 硬切；ready 的 CW 组件 |
| `T-O-365` | `foundational / fence-order` | **P0–P4 全部完成并充分测试 → NS4 closure → 才允许 R3**。R3 不是 NS4 相位。P1 绿、单测绿、或「先看一格」**均不**解除 ingest 禁令。 | 围栏 F5 · 业主 2026-08-16 | `WAIT_OWNER_LIVE` 升格为等 closure |
| `T-O-366` | `foundational / fence-d04-tx` | 增列或增证据表必须 **D04 窄 reopen**（禁止私自第四套黑表）。`domain_events` 仍同业务 TX。diagnostic **默认** best-effort（除非执行题改写）。禁正文 / prompt / stdout / secret 入账。 | 围栏 F6+F7+F8；`T-O-288/291/292/311` | reopen 清单；红action |
| `T-O-367` | `foundational / fence-kernel-preserve` | 叶包 `lsrag_*` 仍无 I/O；不去 Mixin / 不 YAML。kernel 不放宽；禁静默换工人；C3 salvage 仍 `GATED`。不改写 R1 已封结论；R2 未封分析不是 Truth。旧失败 `{}` extra **不事后发明** 直方图。 | 围栏 F9–F12；NS3；`T-O-346/340` | 叶守卫；迁移不造伪行 |
| `T-O-368` | `foundational / scope` | **正式立 NS4** 为 generation-evidence 平台。必交 **P0–P4**。**窄 reopen D04 + S15**（工人失败证据的列/表、校验、ReadPort）。不新开进程、不第二库、不建设 APM 产品。**R3 留在 0815 族，不并进 NS4 相位**。NS4 停工不含 R3 publish 数。 | Q1 · 业主接受推荐 **B** · 2026-08-16 | 写 NS4 AP + D04/S15 change-request |
| `T-O-369` | `execution / schema` | 失败证据物理合同 = **`mkb_generation_invocations` 列晋升**（`status`/`stage_key`/`error_code`/`adapter_kind`/`cli_structured_kind` + CHECK）+ **新 required 表 `mkb_generation_stage_reports`**（每 generate 阶段一行：disposition、直方图字段、`latency_ms`、`schema_digest`）。`layer_counts` 仅计数字典且必须登记 JSON schema。从 `payload_extra` **删除** reject/kind 键。禁止 extra+列双写。 | Q2 · 业主接受推荐 **B** · 2026-08-16 | D04 DDL；contracts 校验；architecture 禁 extra 键 |
| `T-O-370` | `execution / write-tx` | stage report + generation/inference invocation 与 Process Outcome **同一业务 TX**；缺行或插失败 → 整笔回滚。删除吞异常的 `_persist_failed_*`。产品 `error_code`（`STRUCTURE_*` / `CLAUDE_CLI_*` / `CONSTRUCT_*`）不被 `OBS_*` 覆盖。diagnostic 保持 commit 后旁路；无 sink 配置则进程不得启动 generate。禁止把 LLM wait 包进已 BEGIN 的写事务。 | Q3 · 业主接受推荐 **B** · 2026-08-16 | P1 写入；删除 `except: return` |
| `T-O-371` | `execution / turso` | 应用与 0815 **硬切** `persistence_backend=turso` 且 `concurrent_writes_required=True`（探针失败 = not ready）。诊断 sidecar：第二连接 + `BEGIN CONCURRENT`（冲突重试 1 次，再失败遵 diagnostic 可丢）。业务 CAS **保持默认 TX**，不改 CONCURRENT。sqlite **仅** pytest。禁止 sqlite+turso 双后端。Cloud Embedded Replica 不纳入本节点。P3 必须实测 CW，未测不得宣传 4×，也不得再 defer。 | Q4 · 业主接受推荐 **B** · 2026-08-16 | runner Settings；`/ready`；P3 验收 |
| `T-O-372` | `execution / migrate-once` | **一次迁移** Q-A3 serving 闭集（publication + 17 向量 + 必要 pointer）到新 Turso schema；Port 校验通过后 **删除** sqlite 生产打开路径。旧失败 extra **不**回填直方图。禁止双读旧库。迁移脚本 closure 后删除或标 `retired`，不得变成长期适配器。 | Q5 · 业主接受推荐 **B** · 2026-08-16 | P3 迁移脚本；Q-A3 只读保全经新路径 |
| `T-O-373` | `execution / dag` | NS4 DAG：**P0** 冻合同与守卫 → **P3** Turso/CW + Q-A3 一次迁移 + 删 sqlite 生产分支 → **P1** schema+同 TX 写入 + 删 extra/`getattr` → **P2** DiagnosticSink + CONCURRENT sidecar → **P4** 删 dump / 只留 Port → **closure** → **然后** R3。新 schema **不得**先落 sqlite 生产。任一相未绿不得进下一相。 | Q6 · 业主接受推荐 **C** · 2026-08-16 | NS4 AP 相位与测试台账 |
| `T-O-374` | `execution / read-surface` | **唯一观测读面** = `ObservabilityReadPort`（须含 invocation.status、stage report、events）。删除 `inspect_dump` 生产路径（或移入 tests 且不得被 collect 调用）。0815 jsonl / 六件套文件仅作 **run 期刊**：可记身份、终态、error_code、路径哈希；**禁止**再写 reject 形状。禁止 dump+Port 双写或过渡期对照。 | Q7 · 业主接受推荐 **B** · 2026-08-16 | P4；jsonl 字段白名单测试 |
| `T-O-375` | `execution / r3-after-closure` | R3 **仅**在 NS4 closure 且 P0–P4 台账全绿之后发车。格子：`N-A5,N-A3,N-A6,N-A2,Q-A5` + `-r3`；不开 A1/A4/A5g2。冻结 g1 v3；不改 C、不换 binding。产品轴维持 `R3_READY`（Q-A3 经新路径 intact）。观测轴按格：失败必须存在 **stage report 或 failed invocation 行**，否则 `obs-insufficient`；**不连坐**；不认 extra；diagnostic 行数不是唯一闸。closure 前零 ingest。 | Q8 · 业主接受推荐 **A** · 2026-08-16 | collect 时机；R3 分析双表数行 |

---

## 2. Pre-round 围栏（本版叙事 · **已随 Q1–Q8 一并冻结**）

> 下列由业主本轮书面指令 + 已冻 D/S **唯一推出**。业主 2026-08-16 整包接受推荐时 **一并确认**。推翻须本文件追加修订并新 append `T-O-376+`。
>
> 冻结映射：F1+F2→`T-O-362`；F3→`T-O-363`；F4→`T-O-364`；F5→`T-O-365`；F6+F7+F8→`T-O-366`；F9–F12→`T-O-367`。

| # | 围栏 | 出处 | NS4 含义 |
|---|---|---|---|
| F1 | **硬切**：不合适位置删除，不留兼容分支 / 适配开关 / `getattr` 可选账 | 业主 2026-08-16 | CLI 失败路径必须与 live **同一强制写入**，或删掉「成功才记账」 |
| F2 | **禁双写**：同一事实不得同时进 extra 与列、dump 与 Port、sqlite 与 turso | 业主 2026-08-16 | 迁移窗口 = 一次性转换 + 删旧路径，不是并行跑 |
| F3 | **禁 hotfix / 禁 extra 当证据** | 业主；`T-O-173`；D04-P04；D04「核心真相不得只活在 JSON」 | reject 直方图、CLI kind、invocation 成败是 **列或新表**，不是口袋 |
| F4 | **Turso 必推**：本节点必须推进后端与 CW，禁止无期限 defer | 业主；D04 宪法；S12 ready | 0815/生产默认 turso；sqlite 降为测试夹具 |
| F5 | **顺序**：P0–P4 完成并充分测试 → NS4 closure → 才 R3 | 业主 2026-08-16 | R3 不是 NS4 相位；P1 绿不等于可发车 |
| F6 | 可观测三表名仍是事件/诊断/审计面；**增列或增表必须 D04 reopen** | `T-O-288`；D04 冻结声明 | 允许窄 reopen，不允许私自建第四套黑表 |
| F7 | `domain_events` 与业务同 TX；diagnostic **默认** best-effort（除非 Q3 改） | `T-O-291`/`T-O-292` | 分账不是兼容缝；Q3 决定证据表走哪边 |
| F8 | 禁正文 / prompt / stdout / secret 入账 | `T-O-311` | schema 校验同样拒绝这些键 |
| F9 | 叶包 `lsrag_*` 无 I/O；不去 Mixin / 不 YAML | NS3；`T-O-150/151`/`T-O-142` | 写入仍在 Mixin/runtime；硬切的是 seam，不是把 I/O 打进叶包 |
| F10 | kernel 不放宽；禁静默换工人；C3 salvage 仍 `GATED` | `T-O-346/344/347/340` | 观测平台再完整也不许用放宽换绿 |
| F11 | 不改写 R1 已封结论；R2 未封分析不是 Truth | 0815 族 | 本 QNA 不升格 R2 token |
| F12 | 旧失败行的 `{}` extra **不事后发明** 直方图 | R2 RCA D-07 | 迁移不伪造 witness |

Q1–Q8 已冻结，见 §1 / §9。

---

## 3. Existing Conditions 与证据水位

### 3.1 邻域已冻（只可引用或 **显式 reopen**）

| # | 条件 | 类 | 权威 |
|---|---|---|---|
| EC-01 | D04 是 Turso 主库物理宪法；改 required 表/列须 reopen + 新 `T-O` | MUST | D04 冻结声明 |
| EC-02 | `payload_extra` 禁止 identity/state/proof；核心真相不得只活在 JSON | MUST / 旧推荐违规 | `T-O-173`；D04-P04；D04 §3 类型表 |
| EC-03 | 可观测三表 required、非业务 SSOT；S15 不另起第二套表名 | MUST，可窄 reopen | `T-O-288` |
| EC-04 | `mkb_generation_invocations` 已是 required 表；**无** status / error_code / kind 一等列 | MUST | D04 §3.5.4 |
| EC-05 | `mkb_inference_invocations` 不得并回 generation 或只靠 diagnostic | MUST | `T-O-193` |
| EC-06 | S12：`concurrent_writes` 是 readiness 组件；探针已实现 | MUST | `T-O-305`；`probe_concurrent_writes` |
| EC-07 | Operator 只读面 = Observability Port；禁 file-debug 产品化 | MUST | `T-O-308` |
| EC-08 | v1 不做 APM SaaS、库内 metrics 时序表、webhook 默认 | FORBID | `T-O-300` |
| EC-09 | NS2 先例：派发态 **加列** 不进 extra、不加表（`T-O-360`） | 可类比 | NS2 |
| EC-10 | 0815 R3 五格名单已写，**不是**发车令；本版发车更晚 | DEFER→Q8 | `r3_objectives.md` |

### 3.2 0815 实测（`PROVEN`）——说明 hotfix 已经失败

| 面 | R2 | 含义 |
|---|---|---|
| `mkb_domain_events` | 453 | 生命周期够 |
| `mkb_ops_diagnostic_logs` | 0 | sink 未接入 |
| `mkb_generation_invocations` | 8 全成功 | 失败 CLI/admit 不落行 |
| 失败 `payload_extra` | `{}` | 旧行无 witness；R3-EVD 直方图挂 extra = **债务形状** |
| 实验后端 | sqlite + CW=False | Turso/MVCC **未观察** |
| 实验读面 | `inspect_dump` 直连 sqlite | 与 `T-O-308` 分叉 |
| 唯一 publish | Q-A3 · 17 向量 | 硬切 schema 时必须回答迁不迁（Q5） |

### 3.3 现码缝（硬切对象，不是要包一层）

| 缝 | 现状 | 硬切后应消失 |
|---|---|---|
| CLI 失败不写 invocation | `_cli_layered_candidate` 无对等 persist | 「成功才记账」代码路径删除 |
| `getattr(..., _persist_failed_*)` | construct 偶然打到 live mixin | 可选调用删除；写入是类型契约 |
| extra 直方图 / kind | `details` → `payload_extra` | 这些键从 extra allowlist **删除** |
| DiagnosticSink 仅 retention | 生产 0 行 | Mixin 强制持有；无 sink 不得跑 generate |
| `inspect_dump` 直连 | 绕过 Port | 模块删除或测试禁用生产路径 |
| runner sqlite waiver | Settings 关 CW | 该分支删除 |

---

## 4. 决策簇 1 — 平台治理

### Q1 — NS4 立成什么？D04/S15 怎么 reopen？

- **影响范围**：是否写 NS4 AP；是否正式 change-request D04 表/列闭集与 S15 写入纪律；S15 formal 要不要改句；会不会长出第二进程
- **为什么必须确认**：业主要的是「新观测平台 + 长期治理 + schema 硬切」。这 **不可能** 只在 0815 执行日志里热修，也 **不可能** 不碰 D04——一等列/新表会改变 required 物理闭集。形态不钉，AP、migration、S15 会各写各的。
- **驱动输入**：F3–F6；D04 冻结声明；`T-O-288`；EC-02；业主「搭建新的平台」

#### 选项清单

| 选项 | 方案 | 含义 |
|---|---|---|
| **A** | **只立 NS4 AP，不 reopen D04/S15** | 私自加列/加表或继续用 extra。**否决项**（违宪或回到债务）。 |
| **B** | **正式 NS4 + 窄 reopen D04 与 S15（推荐）** | NS4 是能力节点（P0–P4）。D04 增列/至多增证据表进 required 闭集。S15 补：失败工人证据的写入/校验/ReadPort 合同。**不**新开进程，**不**建设 APM 产品。R3 仍在 0815，NS4 closure 之后。 |
| **C** | **只 reopen S15/D04，不立 NS4 编号** | 治理入口是 baseline 补丁。工程仍要做，但没有 new-start 停工相位，P0–P4 易散。 |
| **D** | **新独立观测域（例如 S17）+ 新进程/库** | 第二套库或 sidecar 服务。撞 OD-01 / `T-O-300` / 单主库 `T-O-102`。 |
| **E** | **不立平台，R3 照旧发** | 业主已否决。 |

#### 当前建议 / 倾向（Grok）

**推荐 B（正式 NS4 + 窄 reopen D04/S15；单主库一等面，不是新进程）。**

#### 推荐执行细节（选 B 时）

1. NS4 charter 必交 = P0–P4（合同、Turso/CW、schema+写入、diagnostic、唯一读面）。退出条件 **不含** R3 publish 数。  
2. 同步提交 D04 窄 reopen：列/表清单以 Q2 为准；required 表数若 +1 必须写进 D04 §2.2。  
3. S15 窄 reopen：ReadPort 必须能按 process 读出失败工人证据；**禁止**把 extra 写成合法证据面。  
4. 「平台」= 主库 schema + Turso 接线 + 唯一 Port。禁止新微服务、禁止公网 marketplace。  
5. 明确禁止：A 的黑表/extra；D 的第二库；E。

#### Supporting Reasoning

- **为何必须 reopen**：D04 写明改 required 表/列要 owner `T-O`。硬切 schema 却不 reopen，等于地下 DDL。  
- **为何仍要 NS4 编号**：P0–P4 是有序工程相位，需要 AP 停工句；纯 baseline 补丁没有「测完才能 R3」的闸。  
- **反对 D**：业主要平台，不是要第二套运维产品。单主库已冻。  
- **反对 A**：这就是被删掉的前一版。

#### 内部证据

- D04 冻结声明；`T-O-288`；NS2 加列先例 `T-O-360`。  
- S11 曾正式 reopen D04 增三表（`T-O-193`）——本节点可走同一窄门，不是另立宪法。

#### 残差风险

- 窄 reopen 写太宽会滑成 S15 全文重开。AP 必须把 reopen 句限制在「工人失败证据 + 校验 + Port」。  
- 表数 +1 要改 D04 多处闭集数字，漏改即索引漂移。

#### 问题（请业主裁决）

**Q1：治理形态选 A / B / C / D / E？若选 B，是否确认：NS4 必交 P0–P4；窄 reopen D04+S15；不新开进程/第二库；R3 不并进 NS4 相位？**

- **业主回答**：接受推荐 **B** 全部执行细节（正式立 NS4；必交 P0–P4；窄 reopen D04+S15；不新开进程/第二库；R3 不并进 NS4 相位）。→ **冻结为 `T-O-368`**
- **裁决状态**：`accepted / frozen`

---

## 5. 决策簇 2 — 一等 schema 与写入

### Q2 — 工人失败证据的物理合同是什么？（禁止 extra 口袋）

- **影响范围**：D04 DDL；`mkb_generation_invocations` / `mkb_processes` / 可能的新表；contracts 校验器；architecture 测试；现 `payload_extra` allowlist **删除**
- **为什么必须确认**：业主要求长期治理 schema 硬切到位、严格校验。D04 已禁止 extra 当 proof。形状不钉，reopen 无法写列清单。
- **驱动输入**：F3；EC-02/04；D04 §3.5.4（invocation 现无 status 列）；R2 失败码表

#### 选项清单

| 选项 | 方案 | 物理落点 | 校验 |
|---|---|---|---|
| **A** | **只加列，不加表**（NS2 派发态同构） | `mkb_generation_invocations` 晋升：`status` CHECK∈`succeeded,failed`、`error_code`、`stage_key`、`adapter_kind`、`cli_structured_kind`；`mkb_processes` 晋升：`reject_has_g0`、`reject_block_count`、`reject_granularity_set`、`reject_layer_counts`（JSON **仅此计数袋**，有 schema digest） | contracts + CHECK + 单测拒 extra 键 |
| **B** | **加列 + 一张证据表（推荐）** | A 的 invocation 列 **加上** 新 required 表 `mkb_generation_stage_reports`（每 generate 阶段一行）：`process_uuid`、`stage_key`、`disposition`、`error_code`、`cli_structured_kind`、`has_g0`、`block_count`、`granularity_set`、`layer_counts`、`latency_ms`、`schema_digest`。`payload_extra` **禁止**再出现上述键。 | 表级 NOT NULL/CHECK；`layer_counts` 走已登记 JSON schema（digest 入列）；非法不得入 TX |
| **C** | **新观测表族** `mkb_obs_*`（多表） | 独立证据家族，invocation 只留指针 | 平台感最强；D04 表数跳变大 |
| **D** | **继续 extra 闭集键** | 前一版 Q2-C | **否决项** |
| **E** | **只靠 jsonl / inspect 文件** | 无库内合同 | **否决项** |

#### 选项 B · 建议列闭集（推荐合同草稿，冻结后进 D04 reopen）

`mkb_generation_invocations` **新增（硬切，旧行迁移或作废见 Q5）**：

| 列 | 约束 |
|---|---|
| `status` | NOT NULL CHECK ∈ `succeeded,failed` |
| `stage_key` | NOT NULL CHECK ∈ `markdown,structurize,construct` |
| `error_code` | NULL；`failed` 时 NOT NULL |
| `adapter_kind` | NOT NULL CHECK ∈ `claude_cli,local_inference` |
| `cli_structured_kind` | NULL；CLI 信封失败时 NOT NULL CHECK ∈ 闭集（`object,list,string,empty_result,missing,…`） |

`mkb_generation_stage_reports` **新表**：

| 列 | 约束 |
|---|---|
| `report_uuid` | PK |
| `team_uuid,trace_uuid,task_uuid,execution_uuid,process_uuid` | 关联；process 非空 |
| `stage_key` | 同上 CHECK |
| `disposition` | CHECK ∈ `accepted,rejected,transport_failed` |
| `error_code` | rejected/transport 时 NOT NULL |
| `has_g0` | BOOL NULL（仅 structurize reject） |
| `block_count` | INT NULL |
| `granularity_set` | TEXT NULL（规范化如 `0,1`） |
| `layer_counts` | TEXT NULL（**只**计数字典，登记 schema + digest 列） |
| `latency_ms` | INT NOT NULL |
| `schema_digest` | NOT NULL |
| `occurred_at` | NOT NULL |

**禁止**：candidate JSON、clean、prompt、stdout、original 入任何列。  
**`mkb_processes.payload_extra`**：从 allowlist **删除** `structure_reject` / `cli_structured_kind`（硬切，不是弃用注释）。

#### 当前建议 / 倾向（Grok）

**推荐 B（invocation 列晋升 + 一张 stage report 表）。**

#### 推荐执行细节（选 B 时）

1. D04 reopen 清单只含上表；不顺手改无关表。  
2. 现码 extra 直方图函数改为 **填 report 行**，返回值不得再并进 extra。  
3. architecture 测试：extra JSON 出现已迁键 → fail；叶包仍无 persistence import。  
4. 明确禁止：D/E；以及「列和 extra 先双写一版」。  
5. 选 A 若业主要零新表：直方图挤进 processes 列，语义仍一等，但 process 行会变宽、与 Outcome 混存。

#### Supporting Reasoning

- **反对 D**：正是业主否决的债务，且已违 `T-O-173`。  
- **反对 A 作首选**：invocation 适合「叫没叫、什么信封」；层直方图是 **admit 报告**，和调用账不同粒度。硬塞 processes 会把 Outcome 行变成第二报告。一张表是平台最小增量。  
- **反对 C**：多表族尚未有第二消费者，容易做成迷你 APM。  
- **B**：调用账与阶段报告分表，两者都有 CHECK/schema digest，extra 清空证据职责。

#### 内部证据

- D04 §3.5.4 invocation 列闭集无 status。  
- R2：5 次 structurize 失败 vs 2 条成功 invocation。  
- NS2：加列不进 extra。  
- D04 类型表：核心真相不得只活在 JSON。

#### 残差风险

- `layer_counts` 仍是小 JSON。必须有登记 schema + digest，禁止演变为第二 extra。  
- 旧库 8 条成功 invocation 无新列：见 Q5 迁移。

#### 问题（请业主裁决）

**Q2：证据物理合同选 A / B / C / D / E？若选 B，是否确认：上表列闭集；extra 删除 reject/kind 键；禁止双写 extra+列？**

- **业主回答**：接受推荐 **B** 全部执行细节（invocation 列晋升 + 新表 `mkb_generation_stage_reports`；extra 删除 reject/kind 键；禁止双写 extra+列）。→ **冻结为 `T-O-369`**
- **裁决状态**：`accepted / frozen`

---

### Q3 — 写不进一等行时，Process 算不算失败？

- **影响范围**：UoW 边界；`_persist_failed_*` 现「吞异常」必须删除；S15 diagnostic 分账是否保持；error_code 会不会被 `OBS_*` 污染
- **为什么必须确认**：硬切意味着「没行就当没发生」不再合法。但 diagnostic 按 `T-O-292` 允许丢。必须钉：哪些面缺行 = 整笔业务失败。
- **驱动输入**：F1/F7；`T-O-289/291/292/310`；live 现 `except: return`

#### 选项清单

| 选项 | 方案 | invocation / stage report | diagnostic |
|---|---|---|---|
| **A** | **全部 best-effort** | 写失败只 stderr | 同左 | **否决项**（成功-only 的亲戚） |
| **B** | **证据同 TX fail-closed；诊断旁路（推荐）** | 与 Process Outcome **同一业务 TX**；插失败 → 整笔回滚，Process 不得标产品成功/产品失败已提交 | 业务 commit **之后** best-effort；丢行只 metric/stderr，不改码 |
| **C** | **证据与诊断全部同 TX fail-closed** | 同 B | sink 失败也回滚业务 |
| **D** | **独立 TX 但 Process 必须看到账** | 先独立写账再 CAS；账失败改标 `OBS_*` 覆盖原 `STRUCTURE_*` | 旁路 |

#### 当前建议 / 倾向（Grok）

**推荐 B。**

#### 推荐执行细节（选 B 时）

1. 删除 `_persist_failed_generation_invocation` 的 `except: return`。失败写入并入 Outcome 提交 TX。  
2. 原产品 `error_code`（`STRUCTURE_*` / `CLAUDE_CLI_*` / `CONSTRUCT_*`）保持权威；**不得**被 `OBS_EVENT_APPEND_FAIL` 替换。若证据插失败：整 TX 失败，由 runtime 以 `OBS_*` **外层**暴露，产品码留在未提交的 draft 里（不落半成品成功）。  
3. DiagnosticSink 继续独立短事务（Turso 上见 Q4 CONCURRENT）。无 sink 配置 = 进程 **不得**启动 generate（构造期硬切），不是写失败才发现。  
4. 明确禁止：A；D 用 OBS 码洗掉 STRUCTURE 码；「先兼容一版吞异常」。

#### Supporting Reasoning

- **反对 A**：R2 已证明 best-effort 账 = 空账。  
- **反对 C**：把 S15 允许丢失的诊断面升级成 CAS，LLM 后一次 sink 抖动会吞掉真实 STRUCTURE 失败，反而看不清。分账是宪法，不是兼容。  
- **反对 D**：两个 TX 之间会有「有账无 process / 有 process 无账」。硬切要的是同笔事实。  
- **B**：工人证据与 Outcome 同命运；诊断仍可丢——这是 `T-O-291` vs `T-O-292`，不是旧 seam。

#### 内部证据

- `T-O-291` events 同 TX；`T-O-292` diagnostic best-effort；`T-O-310` 同此拆法。  
- live persist 吞异常 = 当前空账主因之一。

#### 残差风险

- 同 TX 会拉长写事务。**仍然禁止**把 LLM wait 包进 BEGIN（F 已含）。先等模型，再开 TX 写 Outcome+报告。  
- C 若被选：须正式改写 `T-O-292`。

#### 问题（请业主裁决）

**Q3：写入策略选 A / B / C / D？若选 B，是否确认：删除吞异常；证据与 Outcome 同 TX；diagnostic 保持旁路；产品 error_code 不被 OBS 覆盖？**

- **业主回答**：接受推荐 **B** 全部执行细节（删除吞异常；证据与 Outcome 同 TX；diagnostic 保持旁路；产品 error_code 不被 OBS 覆盖）。→ **冻结为 `T-O-370`**
- **裁决状态**：`accepted / frozen`

---

## 6. 决策簇 3 — Turso 与旧库

### Q4 — Turso / concurrent writes / `BEGIN CONCURRENT` 本节点推到哪？

- **影响范围**：`Settings.persistence_backend`；`concurrent_writes_required`；`/ready`；0815 runner；pytest 夹具；sidecar 连接
- **为什么必须确认**：业主不接受「Turso 是核心却无限 defer」。D04 整部宪法按 Turso 主库写。R2 的 sqlite waiver 是实验例外，不是产品默认。推到哪一截（只换引擎 / 开 CW 探针 / 诊断 CONCURRENT / 业务也 CONCURRENT）会改变就绪门与 CAS 语义。
- **驱动输入**：F4；S12 CW；`probe_concurrent_writes`；Turso MVCC（2025-10-06）；Embedded Replica 写转发

#### 选项清单

| 选项 | 后端 | CW ready | `BEGIN CONCURRENT` | sqlite |
|---|---|---|---|---|
| **A** | 仍 sqlite waiver | False | 不做 | 生产+0815 | **否决项**（前一版 Q6-A） |
| **B** | **turso 硬切（推荐）** | **True**（探针失败 = not ready） | **仅诊断 sidecar** 第二连接；冲突重试 1 次，再失败遵 Q3（诊断可丢） | **仅 pytest** / 内存夹具；生产与 0815 删除 sqlite 分支 |
| **C** | turso | True | 诊断 **和** 业务 CAS 都 CONCURRENT | 仅 pytest |
| **D** | Turso Cloud Embedded Replica | 视部署 | 写转发主库（旁路更慢） | — |
| **E** | turso 引擎，但 CW 仍 False | 关 | 不做 | 半切 | **否决项**（引擎换了、核心能力没推） |

#### 当前建议 / 倾向（Grok）

**推荐 B。**

#### 推荐执行细节（选 B 时）

1. 删除 0815 runner 里 `persistence_backend=sqlite` 与 `concurrent_writes_required=False` 的生产默认。  
2. `/ready` 的 `concurrent_writes` 组件必须绿才能接新 Task。  
3. 业务 UoW 保持默认事务（CAS 同行冲突语义清晰）。**不**把 admit/CAS 改成 CONCURRENT。  
4. DiagnosticSink：第二连接 + `PRAGMA journal_mode=mvcc` + `BEGIN CONCURRENT`。  
5. 可测假说进 NS4-P3 验收：同文件 N 线程写 diagnostic，CW 开 vs 关的墙钟与 `BUSY` 计数。未测不得宣传 4×，但 **必须测**，不得再标 `未观察` 然后 defer。  
6. 明确禁止：A/E；D 纳入本节点；「先 sqlite 跑通 schema 再切」的双后端。

#### Supporting Reasoning

- **为何不是 A**：A 把 D04 宪法降成「有空再练」。业主已否决。  
- **为何业务不 CONCURRENT（反对 C 作默认）**：CAS 与同一 `process` 行碰撞时，CONCURRENT 的行级冲突语义要另写，容易把「谁赢」做成隐式路由。诊断插入无 CAS，最适合 CONCURRENT。这是正确性切分，不是 defer Turso。  
- **反对 E**：换文件格式却关掉宪法里的 CW 门，等于假推进。  
- **反对 D**：0815 单机；replica 写转发与旁路加速相反。

#### 内部证据

- D04 标题与职责就是 Turso 物理宪法。  
- S12 / `T-O-305` 已把 `concurrent_writes` 列为 ready 组件。  
- 探针代码已在 `engine.py`；R2 只是关掉了它。

#### 残差风险

- pyturso 与现 sqlite 文件是否同文件可升——见 Q5。若不能同文件升，必须一次导入后删旧路径。  
- CW 探针在某环境红：进程 not ready，R3 更不能发。这是闸，不是 bug 绕过理由。

#### 问题（请业主裁决）

**Q4：Turso 推进选 A / B / C / D / E？若选 B，是否确认：0815/生产硬切 turso+CW=True；诊断 CONCURRENT；业务 CAS 默认 TX；sqlite 仅测试；禁止双后端？**

- **业主回答**：接受推荐 **B** 全部执行细节（0815/生产硬切 turso+CW=True；诊断 CONCURRENT；业务 CAS 默认 TX；sqlite 仅测试；禁止双后端）。→ **冻结为 `T-O-371`**
- **裁决状态**：`accepted / frozen`

---

### Q5 — 现有 0815 库和 Q-A3：一次迁移，还是硬重置？

- **影响范围**：Q-A3 17 向量 / task `01a00887-…`；R3 金标分母；是否允许短暂无 serving；migration 脚本是否进 NS4
- **为什么必须确认**：硬切 schema + 硬切 turso 之后，旧 sqlite 文件不是合法生产面。业主同时要长期迁移方案。**双读旧库+新库是禁止的。** 只能：一次迁完删旧路径，或宣布 serving 重置。
- **驱动输入**：F2/F12；R2 唯一 publish；前一版「不删库」与本版硬切的冲突

#### 选项清单

| 选项 | 方案 | Q-A3 | 旧失败行 |
|---|---|---|---|
| **A** | **硬重置** | 新 Turso 库空 serving；Q-A3 不作准 | 丢弃（本就无 witness） |
| **B** | **一次迁移后删旧路径（推荐）** | 脚本把 Q-A3 publication + 17 向量 + 必要 pointer **导入新 schema/后端**；校验 Port 可读后 **删除** sqlite 生产打开路径 | extra `{}` **不**发明直方图；失败 process 可迁骨架行，report 表不补伪行 |
| **C** | **双读**：检索走旧 sqlite，新写入走 turso | 旧 serving 活着 | — | **否决项** |
| **D** | **同文件原地改引擎、不迁数据形状** | 旧 extra 键继续合法 | — | **否决项**（兼容旧 seam） |

#### 当前建议 / 倾向（Grok）

**推荐 B。**

#### 推荐执行细节（选 B 时）

1. NS4 含一次性 `migrate_0815_q_a3`（或等价）：只迁 **serving 闭集**（publication、向量、Q-A3 六件套指针），不迁「把 {} 变成直方图」。  
2. 迁移验收：ReadPort 对 Q-A3 `trace/task` 能读时间线；检索 Layer A 不再 422；行数 17 不变。  
3. 验收通过后删除：runner sqlite 分支、`inspect_dump` 对旧文件的依赖。  
4. 明确禁止：C/D；迁移后仍打开旧文件「以防万一」。  
5. 选 A 须书面接受：R3 金标在新 publish 出现前 **无语料**，H3 运输对照消失。

#### Supporting Reasoning

- **反对 C/D**：业主禁双写/兼容。  
- **反对 A 作默认**：一次迁移是「长期治理型迁移」，不是兼容层。丢掉目前唯一 serving 会让 NS4 验收少一条真实 publication。  
- **B**：迁的是 **已证明的成功产品行**，不是失败 witness 伪造。迁完只留一条路径。

#### 内部证据

- Q-A3：`full_valid`，投影 `{0:1,1:8}`，17 向量。  
- 旧失败 extra 无法事后发明（F12）。

#### 残差风险

- 迁移脚本本身会成为一次性代码。NS4 closure 后必须删或标 `retired`，禁止变成双路径适配器。  
- 若物理上无法从该 sqlite 文件进 pyturso，B 变成「导出→新文件→删旧」，语义仍是一次迁移。

#### 问题（请业主裁决）

**Q5：旧库处置选 A / B / C / D？若选 B，是否确认：只迁 Q-A3 serving 闭集；不回填失败直方图；迁完删除 sqlite 生产路径；禁止双读？**

- **业主回答**：接受推荐 **B** 全部执行细节（一次迁移 Q-A3 serving 闭集；不回填失败直方图；迁完删除 sqlite 生产路径；禁止双读）。→ **冻结为 `T-O-372`**
- **裁决状态**：`accepted / frozen`

---

## 7. 决策簇 4 — 相位与读面

### Q6 — P0–P4 内部顺序（R3 只能在 closure 之后）

- **影响范围**：NS4 AP DAG；何时删 sqlite；schema 是否从未写进 sqlite 生产；测试闸
- **为什么必须确认**：业主已钉「全部 P0–P4 测完才 R3」。未钉的是 **相位谁先谁后**。Turso 若后置，一等 schema 会先落在即将删除的 sqlite 上，制造一次性兼容。
- **驱动输入**：F4/F5；Q4/Q5

#### 选项清单

| 选项 | 顺序 | 问题 |
|---|---|---|
| **A** | P0→P1→P2→P3→P4→closure→R3 | schema 先落 sqlite，再切 turso = 二次迁移。**偏兼容。** |
| **B** | P0→P1+P2→P3→P4→… | 同 A，诊断也先 sqlite。 |
| **C** | **P0→P3 Turso/CW→P1 schema 写入→P2 diagnostic→P4 Port→closure→R3（推荐）** | 新合同只在 Turso 上出生；sqlite 生产路径在 P3 结束时已死 |
| **D** | 并行乱序，以 R3 日期倒推 | **否决项** |
| **E** | P0–P2 后先发 R3 | **否决项**（业主已否） |

#### 当前建议 / 倾向（Grok）

**推荐 C。**

#### 推荐执行细节（选 C 时）

1. **P0**：冻本 QNA + D04/S15 reopen 草案 + architecture 守卫（禁 extra 证据键、禁叶 I/O、禁 dump 新调用）。  
2. **P3**：硬切 turso+CW；Q5 迁移（若选 B）在此完成；删除 sqlite 生产分支；CW 探针测试。  
3. **P1**：按 Q2/Q3 建列/表 + 同 TX 写入；删除 extra 路径与 `getattr` persist。  
4. **P2**：Mixin 强制 DiagnosticSink；CONCURRENT sidecar；`log_code` CHECK。  
5. **P4**：删除 `inspect_dump` 生产路径；实验检视改 Port；单测锁死直连。  
6. 每相独立测试台账。**任一相未绿不得进下一相。** 全绿才 closure。  
7. 明确禁止：E；以及 P3 未完成就在 sqlite 上 CREATE 新证据表。

#### Supporting Reasoning

- **反对 A/B**：会逼出「sqlite 版 schema → turso 版 schema」双形状，正是业主禁止的。  
- **C**：引擎先正，合同只出生一次。  
- R3 不在本 DAG 内。

#### 内部证据

- 前一版把 P3 后置，正是业主第 3 条不理解/不接受的来源。  
- D04 假设主库就是 Turso。

#### 残差风险

- P3 前置拉长「看见第一张 stage report」的日历时间。这是硬切代价。  
- Q5-A（重置）时 P3 更简单：新空库。

#### 问题（请业主裁决）

**Q6：相位顺序选 A / B / C / D / E？若选 C，是否确认：新 schema 不得先落 sqlite 生产；P0–P4 全绿才 closure；closure 前零 R3 ingest？**

- **业主回答**：接受推荐 **C** 全部执行细节（P0→P3→P1→P2→P4→closure→R3；新 schema 不得先落 sqlite 生产；P0–P4 全绿才 closure；closure 前零 R3 ingest）。→ **冻结为 `T-O-373`**
- **裁决状态**：`accepted / frozen`

---

### Q7 — 唯一读面：删掉 dump 之后，jsonl 还算不算证据？

- **影响范围**：删除或封禁 `inspect_dump.py`；0815 `inspect/` 目录；`ObservabilityReadPort` 必交字段；MD5 封存还剩什么
- **为什么必须确认**：业主禁双写、禁 file-debug 当平面。`T-O-308` 已指定 Port。0815 族又用目录+MD5 当不可变实验证据。必须切开：**观测平面** vs **实验期刊**。
- **驱动输入**：F2；`T-O-308`；0815 封条纪律

#### 选项清单

| 选项 | 观测平面 | 0815 期刊 | dump |
|---|---|---|---|
| **A** | Port | 删 jsonl，只留表 | 删 | 封条失去离线目录 |
| **B** | **Port（推荐）** | **保留 jsonl / 六件套文件** 作为 run 期刊（**禁止**再写 reject 形状；只记 task_id / error_code / 路径哈希） | **删除**直连 dump |
| **C** | Port + dump 双写 | jsonl | 留 | **否决项** |
| **D** | 只 dump | jsonl | 留 | **否决项** |

#### 当前建议 / 倾向（Grok）

**推荐 B。**

#### 推荐执行细节（选 B 时）

1. 生产与 0815 检视入口只剩 Port：`timeline_by_task` 必须含 invocation.status、stage report、events。  
2. `inspect_dump.py` 删除或移入 `tests/` 且不得被 collect 调用。  
3. jsonl 字段白名单：身份、终态、error_code、artifact 路径、哈希。**禁止** `structure_reject` 对象。那是表的职责。  
4. 明确禁止：C/D；以及「过渡期 dump 对照 Port」。

#### Supporting Reasoning

- **反对 A**：0815 MD5 封条需要不可变目录。表是活库，下一枪会变。期刊 ≠ 第二 schema。  
- **反对 C/D**：双写 / 旧 seam。  
- **B**：平面唯一，封条仍在。

#### 内部证据

- `T-O-308`；R2 失败格无 candidate 化石——缺的是 **写**，dump 再留也造不出旧行。

#### 残差风险

- 期刊若偷写直方图，会再长出双形状。白名单测试必须红。

#### 问题（请业主裁决）

**Q7：读面选 A / B / C / D？若选 B，是否确认：删除 dump 生产路径；Port 为唯一观测读面；jsonl 仅期刊且禁 reject 形状？**

- **业主回答**：接受推荐 **B** 全部执行细节（删除 dump 生产路径；Port 为唯一观测读面；jsonl 仅期刊且禁 reject 形状）。→ **冻结为 `T-O-374`**
- **裁决状态**：`accepted / frozen`

---

## 8. 决策簇 5 — NS4 之后的 R3

### Q8 — R3 何时、哪几格、提示词、怎样算过？（本枪不得先于 NS4 closure）

- **影响范围**：`WAIT_OWNER_LIVE` 解除条件升格为 **NS4 closure**；`collect.py --cells`；catalog；双轴验收（观测轴改为 **一等行**）
- **为什么必须确认**：发车窗口已被围栏钉死，但格子、v3、通过标准仍会改变分母。观测轴必须从「extra 非空」改成「report/invocation 行存在」，否则验收还在认债务形状。
- **驱动输入**：F5；`r3_objectives.md`；`T-O-348/349`；R2 矩阵

#### 选项清单（本门是组合题：矩阵 × 提示词 × 观测轴；发车时刻 **不可选**「NS4 中途」）

| 选项 | 格子 | 提示词 | 观测轴 |
|---|---|---|---|
| **A（推荐）** | 五格 `N-A5,N-A3,N-A6,N-A2,Q-A5` + `-r3`；不开 A1/A4/A5g2 | 冻结 g1 **v3**；不改 C、不换 binding | 失败格必须有 **stage report 或 failed invocation 行**；否则 `obs-insufficient`；**不连坐**；diagnostic 行数不是唯一闸 |
| **B** | 五格 + A5g2 | v3 | 同 A |
| **C** | 近全矩阵 + A1/A4 | v3 | 同 A |
| **D** | 五格 | 再写 v4 / 加厚 C | 同 A |
| **E** | 任一矩阵 | 任一提示词 | 仍认 extra 非空 | **否决项**（验收认债务） |
| **F** | 重跑 Q-A3 原键或 NS4 未 closure 就 ingest | — | — | **否决项** |

**产品轴**（所有合法选项共用，不放宽 kernel）：

```text
Q-A3 serving intact（若 Q5-A 重置，则改为「新语料至少一份 publication」）
+ at least one of {N-A5, Q-A5} publish
+ zero GRANULARITY_SET_MISMATCH on this -r3 g1 set
+ retrieval re-score has no Layer A 422
+ no kernel patch
+ Q cells not lane_contaminated
+ NS4 closure already recorded
```

#### 当前建议 / 倾向（Grok）

**推荐 A。**

#### 推荐执行细节（选 A 时）

1. 本 QNA 与 NS4 AP **均不**授权 ingest。唯一发车条件：NS4 closure 文档已写且 P0–P4 测试台账全绿。届时命令仍是：
   ```bash
   .venv/bin/python .experiment/0815/runs/MKB-0815-R2/collect.py \
     --cells N-A5,N-A3,N-A6,N-A2,Q-A5 \
     --suffix -r3 --no-extras --rerun
   ```
2. A5g2 仍门闩：本枪 N-A5 或 Q-A5 publish 后再议。  
3. catalog 保持 v3 active；不 register。  
4. R3 分析必须产品表 + 观测表（数 **行**，不数 extra 键）。  
5. 明确禁止：E/F；NS4 进行中「先跑一格看看」。

#### Supporting Reasoning

- 格子/提示词逻辑与前一版相同，**不**被硬切叙事推翻。  
- 必须改的是观测轴定义：再认 extra = 暗中恢复债务。  
- 发车时刻已由 F5 钉死，本题不提供中途发车的合法项。

#### 内部证据

- R2：v3 针对 g1 吐 2；A1/A4 是体积问题。  
- 前一版 Q8-B 的 extra 判据与本版 F3 冲突，必须换。

#### 残差风险

- NS4 变长后 v3 假说更晚才打。这是业主用顺序换治理的显式代价。  
- Q5-A 时产品轴第一行改写，须在答复里点明。

#### 问题（请业主裁决）

**Q8：R3 组合选 A / B / C / D / E / F？若选 A，是否确认：仅 NS4 closure 后发车；五格；v3 冻结；观测轴看一等行；不连坐；不认 extra？**

- **业主回答**：接受推荐 **A** 全部执行细节（仅 NS4 closure 后发车；五格 `-r3`；v3 冻结；观测轴看一等行；不连坐；不认 extra）。→ **冻结为 `T-O-375`**
- **裁决状态**：`accepted / frozen`

---

## 9. 题 × 业主选择 × 冻结 Truth 映射（已冻结）

| 题 | 焦点 | Owner 选择 | Truth-ID | 状态 |
|---|---|---|---|---|
| 围栏 F1+F2 | 硬切；禁双写 | 一并确认 | `T-O-362` | `frozen` |
| 围栏 F3 | 禁 extra 当证据 | 一并确认 | `T-O-363` | `frozen` |
| 围栏 F4 | Turso 本节点必推 | 一并确认 | `T-O-364` | `frozen` |
| 围栏 F5 | P0–P4 → closure → R3 | 一并确认 | `T-O-365` | `frozen` |
| 围栏 F6–F8 | D04 reopen；TX 分账；禁正文 | 一并确认 | `T-O-366` | `frozen` |
| 围栏 F9–F12 | 叶无 I/O；kernel；R1；不造伪行 | 一并确认 | `T-O-367` | `frozen` |
| Q1 | 平台 + D04/S15 reopen | **B** | `T-O-368` | `frozen` |
| Q2 | 一等 schema | **B** | `T-O-369` | `frozen` |
| Q3 | 同 TX fail-closed | **B** | `T-O-370` | `frozen` |
| Q4 | Turso/CW/CONCURRENT | **B** | `T-O-371` | `frozen` |
| Q5 | Q-A3 一次迁移 | **B** | `T-O-372` | `frozen` |
| Q6 | 相位顺序 | **C** | `T-O-373` | `frozen` |
| Q7 | 唯一读面 | **B** | `T-O-374` | `frozen` |
| Q8 | R3 组合 | **A** | `T-O-375` | `frozen` |

全局下一空号 **`T-O-376`**。下游 NS4 AP §2、D04/S15 reopen、R3 执行 **只引编号 + 本表口径**。接线叙事不得再被引用。

---

## 10. 本文件不回答

| 排除项 | 理由 | 去处 |
|---|---|---|
| 单测文件名 / commit 拆法 | 实现微调 | NS4 AP |
| 是否封 R2 MD5 | 族封条，不改 NS4 合同 | 业主另令 |
| 放宽锚 / 静默补层 | 已冻 | 另开 campaign |
| 去 Mixin / YAML | NS3 OOS | reopen D03/S03 |
| billing / cloud-inference | `T-O-357/358` | 独立 AP |
| APM SaaS / 第四套黑表不经 D04 | `T-O-300/288` | 禁止 |
| 金标问句改写 | 检索质量 | R3-05 / S10 |

---

## 11. 使用约束

1. 业主只在本文件填 `业主回答`。下游只引 `Q 编号 + 本表口径`。  
2. 冻结后推翻须本文件追加修订并新 append `T-O-376+`。  
3. `T-O-362..375` **仅以 §1 一句话为准**。接线叙事正文不得被 AP 引用。  
4. 本 qna 只产 `T-O`。D04/S15 正文回填发生在 reopen 执行期，不在冻结时预写 formal。

---

## 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-16 | Grok | 初稿（接线 / extra / sqlite waiver / P1 后 R3） |
| v1.0-qna-locked（接线 · **vacated**） | 2026-08-16 | Grok | 曾整包冻结同号；业主否决后整文件删除，ID 未进 baseline |
| v0.2-rewrite | 2026-08-16 | Grok | 硬切 / 禁双写 / 禁 extra 证据 / Turso 必推 / P0–P4 后 R3 |
| v1.0-qna-locked | 2026-08-16 | Grok | 业主整包接受新叙事推荐；冻结 Q1–Q8 + 围栏 F1–F12；注入 `T-O-362..375`；下一空号 `T-O-376` |
