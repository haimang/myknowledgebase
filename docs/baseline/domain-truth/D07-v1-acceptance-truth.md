# D07 — V1 Acceptance Truth & HARD Delivery Ledger

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 共有域**：全真相层 **验收标准 · HARD 测试要求 · 交付收口**
>
> **文档性质**：`shared-domain constitution / acceptance truth ledger`（**唯一验收收口台账 SSOT 候选**）
>
> **文档状态**：`draft / owner-review`（**未** owner-freeze；**未**替换索引 `18` 直至本文件 accepted 并与 `18` 分账）
>
> **Truth 版本 / 日期**：`D07-v0.4 / 2026-08-12`
>
> **文件路径**：`docs/baseline/domain-truth/D07-v1-acceptance-truth.md`
>
> **作者**：`MKB owner + Grok`（逐域审查 D01–D06 / S01–S16 验收矩阵后合成）
>
> **组织参考**：`context/legacy-specs/owner-truth/04-v1-success-and-non-goals.md`（OT-04 完成定义 / 可观察成败 / 质量底线 / non-goals）
>
> **权威输入**：全部 `docs/baseline/domain-truth/D01–D06`、`S01–S16` 已落盘 formal；`spec-index` v0.62；`spec-glossary` v2.8；D06 资源非 blocker 纪律
>
> **下游消费者**：实现测试计划、architecture tests、CI 门禁、owner release gate、`spec-index` 附录 A、未来 `18` 签署矩阵
>
> **与 `18` 分账**：本文件冻结 **「必须证明什么 / HARD 是什么 / 按域槽位」**；`18` 负责 **签署、跨域对账闭合清单、truth freeze 仪式**。禁止双源维护不同 HARD 表。

> **★ 台账纪律**
> 1. **一域一槽**：每个 domain-truth 文件在 **§3 总表 + §7 正文** 有且仅有一个主槽位。  
> 2. **HARD 不发明**：`*-A*` 行优先 **引用** 各域 §6；无 `*-A*` 的 D02/D04/D05 使用 `D07-D0x-A*` **派生**行并注明源章节。  
> 3. **不伪交付**：本文件 **不**声称测试已绿；只定义通过标准与证据类型。  
> 4. **SSOT**：实现验收以 domain-truth + 本 ledger 为准；**禁止**以 QNA 为执行验收 SSOT。  
> 5. **资源**：宿主机瞬时 GPU/容器不符 **不得** blocker（D06-T001..T004）；live inference 仅可选 profile。

---

## 0. 本文件回答什么 / 不回答什么

### 0.1 回答

1. MKB v1 **何时**可被声明交付完成（全局完成定义）；  
2. **每个 domain-truth** 的验收方法与 HARD 清单；  
3. caller 可观察的成功/失败与不可降低的质量底线；  
4. 跨域 **golden / release gate**（含 semantic retrieval usefulness）；  
5. 明确 **non-goals**（不得伪装成验收缺口）。

### 0.2 不回答

| 排除 | 归属 |
|---|---|
| 测试框架选型、用例代码、CI YAML | 实现期 |
| 精确 SLA 数值（QPS/p99）除非域内已冻 | S15/ops 或 defer |
| 签署仪式与最终 frozen 戳 | `18` |
| 实现排期 | OOS |

---

## 1. 全局 V1 完成定义（收口门闩）

> 继承 OT-04 精神，并按 **当前已 accepted** S08–S16/D05/D06 闭合更新。

| Gate ID | 完成条件（全部满足） | 主要证明槽位 |
|---|---|---|
| `D07-G01` | **单体闭环**：一 Python 应用、一发布单元、caller-neutral Contract；无 legacy runtime 依赖即可执行合法请求 | S01/D03/D06 |
| `D07-G02` | **接入闭环**：Team 投影 + InternalToken + Task+Audit 原子 + polling + 有限 command；同步 `retrieval.search` | S01/S02/S16/S10 |
| `D07-G03` | **Intake/Clean 闭环**：四类 source + typed evidence + mandatory preflight + bounded gate | S04/S05 |
| `D07-G04` | **Structure 闭环**：immutable generation + exact schema + full-valid 才 current | S06/D05 |
| `D07-G05` | **Construct 闭环**：整包 dual-channel + ConstructToVectorizeGate | S07/D05 |
| `D07-G06` | **Vectorize 闭环**：整包成败 + 幂等 + Layer A/B | S08 |
| `D07-G07` | **Publication 闭环**：PublicationProof + ActiveIndex + serving CAS；存在≠服务 | S09/S04 |
| `D07-G08` | **Retrieval 闭环**：dual-fence + traceback + context-only；无 answer 伪装 | S10 |
| `D07-G09` | **Inference 平面**：S11 facade + `ai-mkb` 角色 `qwen-vl-2b`/`qwen35-a3b`（运行窗口业主保证） | S11/D06/S14 |
| `D07-G10` | **持久化/对象**：单主库 TX/outbox + local object CAS/identity | S12/S13/D04 |
| `D07-G11` | **治理/观测/安全**：registry hash、events 非 SSOT、token/egress/redact | S14/S15/S16 |
| `D07-G12` | **状态宪法**：六 StateFamily；无第七 status 族；proof 上卷 | D01/D02 |
| `D07-G13` | **Semantic release gate**：有限代表性 corpus 上预期查询找回 grounded evidence + original traceback（非通用准确率 SLA） | S10 + golden（§4） |
| `D07-G14` | **本 ledger HARD 全集**按 release 剖面（§5）声明通过；无 open P0 HARD | 本文件 §3 总表 + §7 槽位 |

**禁止**：仅 contract/schema 绿而 G13 语义检索失败 → **不得**宣告 V1 完成。

---

## 2. 全局质量底线与 caller 可观察（压缩 OT-04）

### 2.1 Caller 可观察

| ID | 底线 | 证明 |
|---|---|---|
| `D07-Q01` | 仅 internal orchestrator；无 UI 验收面 | S01 |
| `D07-Q02` | 可区分 not_ready / success / failed / cancelled / action_required / soft-delete visibility | S02 |
| `D07-Q03` | succeeded 必有 durable proof；缺 proof 不得 succeeded | S02/S03/S09 |
| `D07-Q04` | scatter collect-all + child early ready 透明 | S02/S03/S04 |
| `D07-Q05` | cancel=forward-stop 非 rollback serving | S02/S03/S04 |
| `D07-Q06` | retrieval 同步；不建 Task；empty≠假 hit | S10/S01 |
| `D07-Q07` | 401 先于资源读；跨 team 无存在性泄漏 | S16/S01 |

### 2.2 不可降低质量底线

| ID | 底线 | 证明 |
|---|---|---|
| `D07-Q10` | 禁 silent loss；typed rejection/gap | S05/S04 |
| `D07-Q11` | immutable history（Task/Audit/Revision/Generation/proof） | S01–S07 |
| `D07-Q12` | exact binding/digest drift fail-loud | S03/S05/S06/S14 |
| `D07-Q13` | kernel 不可 agent 修；repair 新 artifact 全量复验 | S06 |
| `D07-Q14` | dual-fence 检索；禁仅 ANN | S09/S10 |
| `D07-Q15` | 禁 silent model/space swap | S11/G-10 |
| `D07-Q16` | log/queue/HTTP 无成功权 | D02/S12/S15 |
| `D07-Q17` | crash/redelivery 无双成功/断链 | S03/S12/S02 |

### 2.3 固定容量（验收不得扩张）

| ID | 上限 |
|---|---|
| `D07-C01` | 1 应用 / 1 发布单元 / 0 UI 平台 / 0 legacy 兼容产品 |
| `D07-C02` | 6 StateFamily；polling-only 异步；同步 retrieval |
| `D07-C03` | 4 source kinds；context-only retrieval（无 v1 answer） |
| `D07-C04` | 默认推理：`ai-mkb` + `qwen-vl-2b` + `qwen35-a3b`（D06） |

---

## 3. Domain Truth 槽位总表（Ledger Index）

| 槽位 | 域 | 权威文件 | 文档状态 | HARD 范围 | 一句话验收焦点 |
|---|---|---|---|---|---|
| `D01` | D1 runtime identity | `domain-truth/D01-task-execution-process-flow.md` | accepted / D01-v1.4 | D01-A01..A24 | 三层 Task/Execution/Process 身份、retry/cancel/scatter、proof 上卷 |
| `D02` | 共有状态宪法 | `domain-truth/D02-production-state-and-routing.md` | frozen / D02-v1.0 | D07-D02-A01..A08（派生） | 六 StateFamily、state-vs-fact、镜像/drift；无独立 *A* 表 → D07 派生 HARD |
| `D03` | 仓库布局 | `domain-truth/D03-repository-layout.md` | accepted / D03-v1.0 | D03-A01..A17 | 目录/import/contracts/prompts hash |
| `D04` | Turso 物理 schema | `domain-truth/D04-turso-physical-schema.md` | accepted / D04-v1.1 | D07-D04-A01..A12（派生） | 表闭集/migration/readiness 接合；无独立 *A* 表 |
| `D05` | LS-RAG handbook | `domain-truth/D05-layered-semantic-rag-handbook.md` | frozen / D05-v1.0 | D07-D05-A01..A10（派生） | 双通道/粒度/prompt 三身份/门闩；产品法验收 |
| `D06` | 运行拓扑 | `domain-truth/D06-runtime-topology.md` | draft / D06-v0.2 | D06-A01..A10 | ai-mkb/668·669/角色；资源非 blocker |
| `S01` | Skill-Worker Integration | `domain-truth/S01-skill-worker-integration.md` | accepted / S01-v1.5 | S01-A01..A39 | token/Team/Task+Audit/polling/standalone |
| `S02` | Task API | `domain-truth/S02-task-api.md` | accepted / S02-v1.3 | S02-A01..A40 | 六态/CAS/scatter/retry/rebuild/gate 投影 |
| `S03` | Workflow Engine | `domain-truth/S03-workflow-engine.md` | accepted / S03-v1.3 | S03-A01..A56 | 七表/claim/lease/retry/scatter/recovery/gate |
| `S04` | Intake Asset Lifecycle | `domain-truth/S04-intake-asset-lifecycle.md` | accepted / S04-v1.2 | S04-A01..A40 | identity/serving/acceptance/purge/tombstone |
| `S05` | Intake & Cleaning | `domain-truth/S05-intake-cleaning.md` | accepted / S05-v1.1 | S05-A01..A35 | 四类 source/preflight/gate/evidence |
| `S06` | Structurizer | `domain-truth/S06-lsrag-structurizer.md` | accepted / S06-v1.1 | S06-A01..A22 | schema/kernel/generation/current |
| `S07` | Constructor | `domain-truth/S07-lsrag-constructor.md` | accepted / S07-v1.1 | S07-A01..A22 | 双通道/整包成败/content_full |
| `S08` | Embedding & Vectorization | `domain-truth/S08-embedding-vectorization.md` | accepted / S08-v1.0 | S08-A01..A15 | vectorize/幂等/Layer A/B |
| `S09` | Vector Index | `domain-truth/S09-vector-index.md` | accepted / S09-v1.0 | S09-A01..A20 | PublicationProof/ActiveIndex/谓词 |
| `S10` | Retrieval & Reranking | `domain-truth/S10-lsrag-retrieval.md` | accepted / S10-v1.0 | S10-A01..A20 | dual-fence/traceback/rerank/context-only |
| `S11` | Inference Runtime | `domain-truth/S11-inference-runtime.md` | accepted / S11-v1.1 | S11-A01..A19 | facade/闸/transport/禁 silent swap |
| `S12` | Turso Persistence | `domain-truth/S12-turso-persistence.md` | accepted / S12-v1.1 | S12-A01..A23 | TX/outbox/claim/migration/CW+vector |
| `S13` | Artifact Storage | `domain-truth/S13-artifact-storage.md` | accepted / S13-v1.1 | S13-A01..A21 | CAS/bytes-first/GC/identity |
| `S14` | Config/Prompt/Model Registry | `domain-truth/S14-config-prompt-model-registry.md` | accepted / S14-v1.1 | S14-A01..A30 | snapshot/hash/override/bootstrap |
| `S15` | Observability & Reliability | `domain-truth/S15-observability-reliability.md` | accepted / S15-v1.1 | S15-A01..A20 | events/metric/ready-live/retention |
| `S16` | Security & Trust Boundary | `domain-truth/S16-security-trust-boundary.md` | accepted / S16-v1.1 | S16-A01..A24 | token/rate/egress/redact/ready |

**合计（引用型 HARD）**：D01 24 + D03 17 + D06 10 + S01 39 + S02 40 + S03 56 + S04 40 + S05 35 + S06 22 + S07 22 + S08 15 + S09 20 + S10 20 + S11 19 + S12 23 + S13 21 + S14 30 + S15 20 + S16 24 = **497**  
**派生 HARD**：D02 8 + D04 12 + D05 10 = **30**  
**Ledger 总 HARD 意图行 ≈ 527**（以各域权威表为准；冲突时 **domain-truth 正文优先**，本文件回填）。

---

## 4. 跨域 Golden / Release 场景（收口必过）

| Scenario ID | 场景 | 必过断言 | 牵涉槽位 |
|---|---|---|---|
| `D07-E2E-01` | single intake → clean → structure → construct → vectorize → publish → serve | Task succeeded 仅当 PublicationProof+serving；全程 team 隔离 | S01–S10,S12,S13 |
| `D07-E2E-02` | scatter N required | counts 对账；一 child fail 不假成功；ready child 不回滚 | S02–S04,S03 |
| `D07-E2E-03` | preflight blocked + gate approve | running+action_required；exact decision 后恢复 same Execution | S01,S02,S05,S03 |
| `D07-E2E-04` | construct fail / max-retries | 无 partial serving；历史可查 | S07,S03,D05 |
| `D07-E2E-05` | reindex 新 generation 失败 | 旧 serving 仍可检索 | S04,S08,S09,S10 |
| `D07-E2E-06` | retrieval dual-fence | ANN-only 不得入 results；deactivated 不可见 | S09,S10,S04 |
| `D07-E2E-07` | summary hit traceback | traceback_status 可观测；失败不伪装 original | S10,D05 |
| `D07-E2E-08` | rerank fail | 保留 ANN 序；禁 dummy 0.5 | S10,S11 |
| `D07-E2E-09` | context-only | 响应无 answer/raw embedding | S10 |
| `D07-E2E-10` | semantic golden（G13） | 有限 corpus 预期 query 找回 expected unit + original | S10,S08,S09 |
| `D07-E2E-11` | inference facade | services 无 adapter import；silent swap 禁 | S11,D03,D06 |
| `D07-E2E-12` | crash/outbox/claim | 无双成功；recovery 幂等 | S03,S12 |
| `D07-E2E-13` | security admission | invalid token 401-before-read；ready 需 sec_token_loaded | S16,S15 |
| `D07-E2E-14` | prompt hash | 文件改 hash 未更新 → fail | S14,D03,D05 |
| `D07-E2E-15` | object bytes-first | promote 后 TX 回滚可 orphan GC；无假 success | S13,S12 |

---

## 5. Release 剖面（如何声明「通过」）

| 剖面 | 包含 | 用途 |
|---|---|---|
| **P0-CI** | architecture + 合同 + 单测可 mock 的 HARD（默认） | 每 PR |
| **P1-Integration** | DB/object/outbox/process 集成 HARD | nightly / pre-release |
| **P2-E2E** | §4 E2E-01..15（除依赖 live GPU 的部分可 mock embed） | release candidate |
| **P3-LiveInference** | D06-A08 + 真实 `ai-mkb` embed/LLM | **仅**业主运行窗口 `mkb_live_inference=1` |
| **P4-SemanticGolden** | E2E-10 / G13 | V1 完成签署前必过 |

**V1 交付声明** 最低：P0+P1+P2+P4 全绿；P3 在业主保证窗口至少一次绿或书面 waiver（须 owner 签名，记入 `18`）。

---

## 6. Non-goals（验收范围外）

| ID | 非目标 |
|---|---|
| `D07-N01` | Final answer / chat / agent UX |
| `D07-N02` | Raw vector 公共 CRUD |
| `D07-N03` | UI / membership RBAC 平台 / billing |
| `D07-N04` | Webhook 异步交付 |
| `D07-N05` | Legacy 兼容/迁移/dual-read |
| `D07-N06` | 第七 StateFamily |
| `D07-N07` | 通用准确率 SLA 或无限 golden |
| `D07-N08` | 以 ComfyUI 并存满血为默认 |
| `D07-N09` | 用 QNA 当执行验收 SSOT |
| `D07-N10` | 把瞬时 `docker ps` 当 HARD |

---

## 7. 分域槽位正文

> **读法**：每槽 = 验收方法 + HARD 表。实现以 **源 domain-truth** 完整行文为准；下表为收口索引。


### 7.D01 槽位 · D1 runtime identity

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/D01-task-execution-process-flow.md` |
| 状态 | accepted / D01-v1.4 |
| HARD 范围 | D01-A01..A24 |
| 验收方法 | 状态机集成 + identity schema gate + scatter fan-in/proof + lease fencing + recovery；架构扫描 Attempt 废止。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/D01-task-execution-process-flow.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `D01-A01` | Contract · 外部 Task Create 携带 execution_uuid/process_uuid/status → strict reject；无业务行 | Contract |
| `D01-A02` | Identity · 创建 Task 后内部生成 Execution/Process → 三类 UUID 全部不同；内部均 UUIDv7；task 仍按 team 复合寻址 | Identity |
| `D01-A03` | Single flow · 单IntakeItem/Revision完整运行 → 1 Task、1 current root、0 child、N Processes；最终proof上卷 | Single flow |
| `D01-A04` | Scatter · API 产生 N 个 required children → 1 Task、1 root、N child Executions；每 child 有独立 current Process | Scatter |
| `D01-A05` | Scatter zero · API合法产生0 memberships | accepted Snapshot required=0；按S04/Workflow policy明确终态，不得永远running |
| `D01-A06` | Fan-out crash · Snapshot/ChangeSet commit后、部分child创建时crash → recovery补齐到恰好N；不重复child Execution | Fan-out crash |
| `D01-A07` | Fan-in · 一个 required child 仍 running，其余成功 → root/Task 不得成功 | Fan-in |
| `D01-A08` | Fan-in proof · children 状态均 success，但一个 publication proof 缺失/无效 → root/Task 不得成功；对账报错 | Fan-in proof |
| `D01-A09` | Auto retry · Process 可重试失败后再次执行 → process_uuid/execution_uuid/task 不变；retry_count 增加 | Auto retry |
| `D01-A10` | Queue redelivery · 同一 queue message 重复送达 → 最多一个合法 claim；不新增 Process，不重复业务提交 | Queue redelivery |
| `D01-A11` | Lease fencing · lease 过期后新 runner claim，旧 runner 后到提交 → 旧 fencing token 被拒绝；新 runner 独占推进 | Lease fencing |
| `D01-A12` | Retry exhaustion · retry_count 达 max_retries → 不再 claim；Process terminal failed；Execution 可归约而非卡住 | Retry exhaustion |
| `D01-A13` | Full retry · 对 terminal failed Execution 执行整次 retry → Task 不变；新 Execution/Processes；retry_of 指向旧 Execution | Full retry |
| `D01-A14` | No dual identity · schema/migration 扫描 → 不存在与 Execution 同义的 `task_attempts/attempt_uuid` 业务身份 | No dual identity |
| `D01-A15` | Cancel · scatter 运行中取消 Task → cancel 传播 root/children/active Processes；无新 claim；收敛后才 Task cancelled | Cancel |
| `D01-A16` | Process cleanup · terminal Execution 过 retention → 先完成并验证terminal summary；无 dangling current_process FK；Task/Execution 仍可完整查询摘要 | Process cleanup |
| `D01-A17` | Event retention · Process projection 被清理 → 按 S15 策略保留的 event/log 不被隐式级联删除 | Event retention |
| `D01-A18` | Projection repair · 故意篡改 Task counters 后运行semantic recovery scanner → 从 Executions 重建正确 projection，并留下修复事件 | Projection repair |
| `D01-A19` | Resource/runtime split · 同一IntakeItem/Revision多次rebuild → Intake identity不变且不新增Revision；每次full run有新Execution lineage | Resource/runtime split |
| `D01-A20` | Table architecture · D01 schema review → 核心状态恰为 tasks/executions/processes；无 clean/rag 分表、无 relation/join 冗余表 | Table architecture |
| `D01-A21` | RAG specificity · Process registry/schema scan → 存在 clean/structurize/construct/vectorize/validate 业务类型和各自 guard | RAG specificity |
| `D01-A22` | Vector separation · 一个 vectorize Process 产生 M 个 vectors → Process row 不膨胀为 M 个假 Process；M 个向量由向量资产域承接 | Vector separation |
| `D01-A23` | Local I/O · Process 输入输出持久化 → 只保存 logical refs/relative locators/hash；无 R2 binding、DO ID、绝对路径 API identity | Local I/O |
| `D01-A24` | S01 migration · truth/schema gate → S01 Attempt 口径已 reopen 或 implementation gate 阻止双模型落地 | S01 migration |


### 7.D02 槽位 · 共有状态宪法

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/D02-production-state-and-routing.md` |
| 状态 | frozen / D02-v1.0 |
| HARD 范围 | D07-D02-A01..A08（派生） |
| 验收方法 | 全域状态枚举/owner 扫描 + 文档镜像校准；每份 S 交付时跑 D02 下游义务五条。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（D07 派生 · 源：D02 §5 Acceptance & Freeze + T-O-86..92）

| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `D07-D02-A01` | 全系统仅六 StateFamily；无第七 status 族 | architecture / 状态枚举扫描 |
| `D07-D02-A02` | phase/reason/outcome/readiness/pointer/proof 与 status 分账 | 合同/代码审查 |
| `D07-D02-A03` | 无跨 owner 写状态 | architecture |
| `D07-D02-A04` | 禁止从 projection/log/payload 猜 Truth | 集成负例 |
| `D07-D02-A05` | Outcome/proof 只向上；control 只向下 | 集成 |
| `D07-D02-A06` | 命中 D02 变化时同单元回填镜像块 | 文档/CI drift 检查 |
| `D07-D02-A07` | D02 不决定下游 exact kind/route/DDL | 文档边界审查 |
| `D07-D02-A08` | StateFamily 合法边违反 fail-closed | 状态机测试 |


### 7.D03 槽位 · 仓库布局

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/D03-repository-layout.md` |
| 状态 | accepted / D03-v1.0 |
| HARD 范围 | D03-A01..A17 |
| 验收方法 | 树扫描 + import linter + contracts 校验契约测 + prompt hash 集成。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/D03-repository-layout.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `D03-A01` | 顶级存在 `intake/` 且不在 `src/services/intake` 作为唯一源 | 树扫描 |
| `D03-A02` | 存在 `src/persistence`、`src/storage`、`data/objects | 树扫描 |
| `D03-A03` | data/prompts` 被 git 跟踪（至少示例 prompt） | git ls-files |
| `D03-A04` | 测试根为 `tests/{unit,e2e,domain} | 树扫描 |
| `D03-A05` | 存在 `public/`；不存在将 object_root 指到 public 的默认配置 | 配置检查 |
| `D03-A06` | architecture：services 不 import api | import linter |
| `D03-A07` | architecture：workflows 无 claim/outbox/retry 实现符号 | grep/AST |
| `D03-A08` | architecture：services 不直接 import libsql/turso driver（仅 persistence） | import linter |
| `D03-A09` | architecture：无 legacy-family 运行时 import | 扫描 |
| `D03-A10` | api/public` 路由集合 ⊆ S01 合同 | OpenAPI/路由测试 |
| `D03-A11` | contracts` 存在实质 schema 模块（非空包） | 树 + 导入测试 |
| `D03-A12` | public API handler 对 body 调用 contracts 校验 | 代码约定/测试 |
| `D03-A13` | ProcessCommand 进入 service 前已经校验 | 单元/架构测试 |
| `D03-A14` | contracts` 不 import runtime/services/persistence/storage | import linter |
| `D03-A15` | 不存在第二套跨层 schema 包与 contracts 并行当合同 | 架构扫描 |
| `D03-A16` | prompt 运用路径执行 hash 校验；DB 无 prompt 正文列（或测试夹具证明仅 hash） | 集成测试 |
| `D03-A17` | 非法 API body 不创建 Task/不写业务行 | 契约测试 |


### 7.D04 槽位 · Turso 物理 schema

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/D04-turso-physical-schema.md` |
| 状态 | accepted / D04-v1.1 |
| HARD 范围 | D07-D04-A01..A12（派生） |
| 验收方法 | migration bootstrap 集成 + readiness 故障注入 + schema 闭集扫描。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（D07 派生 · 源：D04 §6 migration/readiness + 表闭集）

| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `D07-D04-A01` | empty-DB 单链 migration 全模块 apply 成功 | 集成 bootstrap |
| `D07-D04-A02` | migration checksum drift → readiness false | 故障注入 |
| `D07-D04-A03` | required 表闭集完整；禁私自增减 required 表 | schema 扫描 |
| `D07-D04-A04` | 单主库 `mkb_primary`；禁第二可写业务库 | 配置/架构 |
| `D07-D04-A05` | domain 禁止 import driver | import linter |
| `D07-D04-A06` | 禁止 smind_ 业务表名 | 扫描 |
| `D07-D04-A07` | 禁止第二 outbox 表名 | schema |
| `D07-D04-A08` | 可观测三表 required 且非业务 SSOT | schema+集成 |
| `D07-D04-A09` | CW/vector 能力声明不匹配 → readiness false | readiness |
| `D07-D04-A10` | VIEW 只读（UPDATE 拒绝） | 集成 |
| `D07-D04-A11` | bootstrap registry 同 digest 幂等 | 集成 |
| `D07-D04-A12` | team 前缀访问路径；禁跨 team 全局 status 唯一路径 | 索引/查询审查 |


### 7.D05 槽位 · LS-RAG handbook

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/D05-layered-semantic-rag-handbook.md` |
| 状态 | frozen / D05-v1.0 |
| HARD 范围 | D07-D05-A01..A10（派生） |
| 验收方法 | 跨 S05–S10/S14 产品法集成与 golden；与 S 域 HARD 联测而非单独测 handbook。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（D07 派生 · 源：D05 T-O-202..210 + 下游强制清单）

| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `D07-D05-A01` | 生产链强制双通道 original+summary | 集成/golden |
| `D07-D05-A02` | 默认粒度 0/1/2；g=0 必为向量候选 | 集成 |
| `D07-D05-A03` | ConstructToVectorizeGate：非 full-valid construct 不可 vectorize | 集成（S07/S08） |
| `D07-D05-A04` | promptA/B/C identity+hash 绑定；DB 无第二正文 | 集成（S14/S05–S07） |
| `D07-D05-A05` | structure 失败仅走 D01/S03 max_retries 上卷 | 集成 |
| `D07-D05-A06` | retrieval 必须 Traceback/ContextTier 分账能力 | 集成（S10） |
| `D07-D05-A07` | summary 不进 structurizer kernel truth | 单元（S06） |
| `D07-D05-A08` | generation-scoped 坐标；禁裸跨代三元组 | 集成（S06–S10） |
| `D07-D05-A09` | D>S：S 与 D05 冲突以 D05 为准并回填 | 文档 drift 检查 |
| `D07-D05-A10` | 无 final-answer 作为 D05 成功条件 | 合同（S10 G-07） |


### 7.D06 槽位 · 运行拓扑

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/D06-runtime-topology.md` |
| 状态 | draft / D06-v0.2 |
| HARD 范围 | D06-A01..A10 |
| 验收方法 | 配置/合同单元 + architecture（禁 services→vLLM）+ 可选 live inference profile；默认 CI 不依赖瞬时 GPU。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/D06-runtime-topology.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `D06-A01` | 配置可表达 `base_url` ∈ {668,669,自定义} · HARD | — |
| `D06-A02` | 角色键 `qwen-vl-2b` / `qwen35-a3b` 存在于 catalog 合同 · HARD | — |
| `D06-A03` | S11 无 token 混用（MKB vs vLLM）单元 · HARD | — |
| `D06-A04` | services 层无 vLLM HTTP 直依赖 · HARD | — |
| `D06-A05` | /live` 不依赖 inference mock down · HARD | — |
| `D06-A06` | ready 在 inference probe 配置开启且失败时 not ready · HARD（mock） | 可选 live |
| `D06-A07` | 瞬时无 668 监听 **不** 失败默认 test suite · HARD（负例） | — |
| `D06-A08` | live：embed + generate 往返 · **OFF 默认** | ON 当 `mkb_live_inference=1 |
| `D06-A09` | 单写 DB/object_root 纪律 · HARD | — |
| `D06-A10` | 文档声明 ComfyUI 互斥窗口 · doc review | ops |


### 7.S01 槽位 · Skill-Worker Integration

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S01-skill-worker-integration.md` |
| 状态 | accepted / S01-v1.5 |
| HARD 范围 | S01-A01..A39 |
| 验收方法 | API 契约 + 幂等/并发 + architecture dependency gate + polling 分账。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S01-skill-worker-integration.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S01-A01` | API · 无/错误 token 调用业务 endpoint → 在任何资源读取前返回 `401`；无 side effect | API |
| `S01-A02` | API · 任一有效 token 操作任意已注册 team → 不做 membership/RBAC gate；按资源状态正常处理 | API |
| `S01-A03` | Schema · Team 模型或 DDL 出现 owner/member/role/plan/billing 字段 → architecture/schema gate 失败 | Schema |
| `S01-A04` | Contract · 输入 UUIDv4 → 接受并 round-trip 保持 identity | Contract |
| `S01-A05` | Contract · 输入 UUIDv7 → 接受并 round-trip 保持 identity | Contract |
| `S01-A06` | Contract · nil、UUIDv1/v3/v5/v6/v8 或仅“像 UUID”的字符串 → 422`，不得落库 | Contract |
| `S01-A07` | Persistence · 两个 team 使用相同 task_uuid → 两行可同时存在且互不覆盖 | Persistence |
| `S01-A08` | API · 未注册 team 创建 Task → 404 team-not-registered`；Task/Audit/Execution/Process/scheduling intent 全部 0 行 | API |
| `S01-A09` | API · inactive/deleted team 创建 Task → 明确非 active 错误；无业务行 | API |
| `S01-A10` | Team lifecycle · deleted team 直接 activate → 拒绝；restore 后状态为 inactive，再 activate 才 active | Team lifecycle |
| `S01-A11` | Contract · Task/Audit 任一 UUID 不一致 → 整体拒绝；无行 | Contract |
| `S01-A12` | Persistence · Audit insert constraint/fault injection 失败 → Task insert rollback；无 scheduling intent | Persistence |
| `S01-A13` | Persistence · Task insert 成功但 commit 前 executor 轮询 → executor 不可 claim 未提交任务 | Persistence |
| `S01-A14` | Idempotency · 同复合键+同canonical create重放 → 返回同Task、同top-level Intake identity、同Audit；不创建第二current root；已accepted Snapshot/Item identity不重复 | Idempotency |
| `S01-A15` | Idempotency · 同复合键 + 不同 payload/audit/metadata 重放 → 409 task-identity-conflict`；原记录不变 | Idempotency |
| `S01-A16` | Audit · 尝试 PUT/PATCH Audit 或通过 Task PATCH 携带 audit → route 不存在或 strict reject；Audit bytes/fields 不变 | Audit |
| `S01-A17` | Time · 上游 created_at 非 UTC offset 输入 → 合法时接受并 normalize 查询输出；另存 MKB received_at，不覆盖原事实 | Time |
| `S01-A18` | Audit · audit_status 分别为 pending/approved/rejected/waived/not_required → 均只按 schema 保存；Task admission 不因 status 分支 | Audit |
| `S01-A19` | Concurrency · stale expected_revision PATCH → 409 revision-conflict`；current state 不变 | Concurrency |
| `S01-A20` | Surface · 首版 API/配置扫描 → 无 webhook URL、callback secret、callback retry worker | Surface |
| `S01-A21` | Task authority · 外部 PATCH status/progress/result/payload → strict reject；只能使用允许字段或 command | Task authority |
| `S01-A22` | Contract · payload_extra 含合法嵌套 JSON → round-trip；核心执行不读取保留键改变状态机；非 object 拒绝 | Contract |
| `S01-A23` | Request intents · 未知 request_intent 或 payload 与 discriminator 不匹配 → fail-loud，不入库 | Request intents |
| `S01-A24` | Retrieval · 同步 retrieval.search → 不创建 Task/Audit/Execution/Process 行 | Retrieval |
| `S01-A25` | Architecture · domain/application import 03-nano/NACP adapter DTO → dependency gate 失败 | Architecture |
| `S01-A26` | Standalone · 03-nano 完全不可达时启动和执行合法 Task | MKB 可独立完成；未来 adapter health 不影响 core readiness |
| `S01-A27` | UUID generator · 批量生成内部Intake/Execution/Process/Event ID → 全部为UUIDv7，无碰撞；时间排序只作优化，不作正确性前提 | UUID generator |
| `S01-A28` | Task lifecycle · 对已失败 Task 发出完整 retry command → task_uuid/trace_uuid 不变；产生新 UUIDv7 current root execution_uuid 与新 Processes；retry-of 指向旧 Execution，旧 Execution 保持终态 | Task lifecycle |
| `S01-A29` | Soft delete · 删除 Team 或 Task → 历史 Audit 与 durable Execution summaries 仍存在且可查询；不级联物理删除；Process retention 只按 D01/S03/S15 fence 执行 | Soft delete |
| `S01-A30` | Polling · Task 分别处于 not-ready/succeeded/failed/cancelled → 调用者能稳定区分状态；成功时得到 result/artifact 引用，失败时得到结构化错误 | Polling |
| `S01-A31` | Contract migration · Task Create 携带旧 `task_type`、execution_uuid、process_uuid 或内部 status → strict reject；adapter 外的 core 无兼容 alias；无业务行 | Contract migration |
| `S01-A32` | Architecture · schema/model/import 扫描 → 不存在 Attempt identity、`attempt_uuid`、`task_attempts`；Execution 是唯一完整运行身份 | Architecture |
| `S01-A33` | Single ingress · single`intake.ingest → 一个Task、一个current root；accepted Snapshot通常一个membership；内部clean→LS-RAG→publication；外部只轮询Task | Single ingress |
| `S01-A34` | Scatter ingress · IntakeSource一次accepted Snapshot产生N required Items → 一个Task、一个current root、N child Executions；Task无singular current_process；counts与Snapshot/ChangeSet对账 | Scatter ingress |
| `S01-A35` | Authority · caller 尝试以 execution/process UUID 触发、取消、retry 或改状态 → public Task Contract 不提供该写面；只能按 Task command 表达 intent | Authority |
| `S01-A36` | Completion guard · queue 为空/callback 成功，但向量或 filter metadata proof 缺失 → Execution/Task 不得成功；polling 返回未完成或结构化失败 | Completion guard |
| `S01-A37` | Human gate polling · clean完成且Execution有open gate → Task保持`running`；Get Task返回bounded`action_required`与安全gate link，不返回execution/process/fence | Human gate polling |
| `S01-A38` | Gate authority · caller直接PATCH Execution/Process或提交stale target/gate revision → direct route不存在；stale decision冲突且无状态变化 | Gate authority |
| `S01-A39` | Gate decision · authorized exact decision重复送达 → same idempotency/target/action幂等；append+CAS+outbox后恢复same Execution | Gate decision |


### 7.S02 槽位 · Task API

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S02-task-api.md` |
| 状态 | accepted / S02-v1.3 |
| HARD 范围 | S02-A01..A40 |
| 验收方法 | 六态穷举 + cancel 竞态 + scatter items + restart lineage + gate subresource。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S02-task-api.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S02-A01` | Task/Audit 正常创建 | 同事务提交，首态 queued，返回 poll links |
| `S02-A02` | Task/Audit 任一点失败 | Task、Audit、scheduling intent 全不存在 |
| `S02-A03` | 同 fingerprint 创建重放 | 返回同一 Task，行数不增加 |
| `S02-A04` | 同 Task identity 不同 fingerprint | 409 task-identity-conflict`，原数据不变 |
| `S02-A05` | 跨 team 使用相同 task_uuid | 两个 Task 隔离；查询/命令不串租户 |
| `S02-A06` | 外部 PATCH 内部字段 | strict reject；status/result/root/process 不变 |
| `S02-A07` | 六态合法/非法边穷举 | 只允许 §2.3 状态图与 retry-only 回边 |
| `S02-A08` | queued/running result polling | 202 task-result-not-ready`，不是 404 |
| `S02-A09` | success proof 缺失 | Task 不得 succeeded |
| `S02-A10` | cancel/success 竞态 1,000 次 | 每次只有一个 durable 赢家，无双终局 |
| `S02-A11` | queued cancel | cancelling 后 fenced 收敛 cancelled，无工作偷跑 |
| `S02-A12` | cancel 后 late worker commit | 被 generation/fencing/CAS 拒绝 |
| `S02-A13` | scatter 一个 child 失败、siblings active | Task running 且 failed_count 正确 |
| `S02-A14` | scatter required 全终态含失败 | Task failed；成功 child 保持 ready |
| `S02-A15` | scatter required全部proof-valid | root/Task succeeded，counts与Snapshot/ChangeSet一致 |
| `S02-A16` | child proof早于root terminal | child可按IntakeItem/ServingRevision读取/检索，Task仍running |
| `S02-A17` | parent failed 后 ready child | ready/检索可见性不被回滚 |
| `S02-A18` | scatter cancel 含已发布 child | Task cancelled；ready child 保留；未完成工作停止 |
| `S02-A19` | items 大集合分页 | Get Task 有界；items 无重复/遗漏；cursor 稳定 |
| `S02-A20` | counts projection被故障注入破坏 | recovery从SnapshotMembership/ChangeSet/summary重建并告警 |
| `S02-A21` | failed Task full retry | 同 Task 新 generation queued，旧 generation immutable |
| `S02-A22` | cancelled Task full retry | 同 Task 新 generation queued，cancel summary 保留 |
| `S02-A23` | active/succeeded full retry | 分别返回 active/retry-not-allowed，不建 generation |
| `S02-A24` | full retry 网络重放 | 同一 restart_uuid/target generation，不建双 root |
| `S02-A25` | atomic child rebuild | 创建新 Task/Audit/restart row，旧 scatter 不变 |
| `S02-A26` | atomic rebuild 事务逐点失败 | restart/Task/Audit/intent 全部回滚 |
| `S02-A27` | restart admission rejected | 可有 immutable rejected row；无 Task/Execution |
| `S02-A28` | restart status 拉取 | status/result 来自 Task join，无第二 writer |
| `S02-A29` | restart list 全过滤组合 | team 隔离、稳定 cursor、正确 current status |
| `S02-A30` | task/intake-item/restart三种lineage seed | 返回同一因果图语义且无内部UUID泄漏 |
| `S02-A31` | Task soft-delete 后 lineage | 返回 tombstone + last summary，因果不断链 |
| `S02-A32` | Process projection按资格清理后查询 | Task/items/generations/restart/lineage 结果仍完整 |
| `S02-A33` | queue wake-up 丢失/重复 | semantic recovery scanner补发；只产生一份业务执行事实 |
| `S02-A34` | response/error 泄漏扫描 | 无 token、stack、SQL、绝对路径、Process payload |
| `S02-A35` | IntakeItem deactivate/delete | 独立新Task/Audit；logical-first且不伪装为parent cancel |
| `S02-A36` | single Execution open gate | Task保持running；Get Task有bounded action_required，result仍not_ready |
| `S02-A37` | gate detail安全读取 | 返回gate kind/revision/target digest/evidence摘要；不泄漏Execution/Process/fence/secret/ |
| `S02-A38` | exact approve decision | append+CAS+outbox提交后same Execution恢复；重放幂等 |
| `S02-A39` | stale/double/conflicting decision | 409`且current gate/Task/Execution不被反转 |
| `S02-A40` | required child gate rejected | siblings继续；collect-all后root/Task failed，ready siblings不回滚 |


### 7.S03 槽位 · Workflow Engine

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S03-workflow-engine.md` |
| 状态 | accepted / S03-v1.3 |
| HARD 范围 | S03-A01..A56 |
| 验收方法 | registry/compile 确定性 + claim 并发 + Outcome 幂等 + recovery 四窗口 + gate 路径。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S03-workflow-engine.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S03-A01` | 内部注册合法 Workflow | 七表原子提交、revision immutable、pointer正确 |
| `S03-A02` | registration 任一点失败 | revision child/pointer/cache均不留 partial truth |
| `S03-A03` | 相同 fingerprint重放 | 返回同 revision，行数不增加 |
| `S03-A04` | 同 revision number不同内容 | conflict，active pointer不变 |
| `S03-A05` | 跨 revision step/route/binding/control/guard | DB/compiler reject |
| `S03-A06` | graph cycle/self-edge/unreachable required step | registration reject |
| `S03-A07` | 无 terminal/terminal coverage缺失 | registration reject |
| `S03-A08` | route priority tie/free expression/SQL guard | registration reject |
| `S03-A09` | capability key/version不存在 | registration reject |
| `S03-A10` | binding port/type/multiplicity不匹配 | registration reject |
| `S03-A11` | binding 含绝对路径/secret/opaque JSON | registration/security reject |
| `S03-A12` | 同 revision重复 compile 1,000次 | canonical bytes/digest完全相同 |
| `S03-A13` | compiled cache删除 | 从七表重建同 digest |
| `S03-A14` | registry新 revision激活 | 旧 Execution binding不变，新 Execution使用新 revision |
| `S03-A15` | full Task retry | 新 root复制来源 exact revision/digest |
| `S03-A16` | 新 atomic rebuild Task | 解析当前 active revision，不复活旧 child |
| `S03-A17` | 未命中 route | 不建 Process；decision evidence存在 |
| `S03-A18` | eligible materialization崩溃注入 | Process/spec/intent全有或全无；commit前无 wake |
| `S03-A19` | 100并发 claim同 Process | 恰好一个 claim/fence成功 |
| `S03-A20` | queue重复 delivery | 不新增 Process/业务写；delivery diagnostics可增 |
| `S03-A21` | stale token/generation Outcome | reject且truth不变 |
| `S03-A22` | accepted Outcome重放 | idempotent no-op |
| `S03-A23` | retryable failure | same process进入retry_wait，retry_count+1 |
| `S03-A24` | due retry_wait | CAS回ready，重新claim使用新 fence |
| `S03-A25` | lease expiry可安全重放（含 recovery 上限边界） | 未耗尽时 recovery_count+1、retry_count不变、旧Outcome失效；已耗尽时 failed `recovery-exhausted`且 |
| `S03-A26` | lease expiry side effect不确定 | failed indeterminate-side-effect，不自动重跑 |
| `S03-A27` | max-retries耗尽 | Process failed，Execution可归约而非永久waiting |
| `S03-A28` | proof/output schema无效 | Process/Execution不得 succeeded |
| `S03-A29` | single完整流程 | 同一 Execution贯穿所有RAG phases，最终proof上卷 |
| `S03-A30` | controlled clean skip | guard/evidence存在，无假Process |
| `S03-A31` | scatter ChangeSet N required children | 恰好N个本ChangeSet child，root waiting/fan_in |
| `S03-A32` | Snapshot/ChangeSet commit后partial child crash | recovery补齐，不重复已有child |
| `S03-A33` | scatter child失败且siblings active | root waiting/Task running，siblings继续 |
| `S03-A34` | required children全终态含失败 | root failed，成功child仍ready可检索 |
| `S03-A35` | children全部proof-valid | root/Task succeeded，counts与manifest一致 |
| `S03-A36` | zero-required Snapshot/ChangeSet | typed terminal policy执行，不依赖queue empty |
| `S03-A37` | cancel/success竞态1,000次 | durable first-commit-wins，无双终局 |
| `S03-A38` | cancel后late Outcome | fence拒绝；descendants收敛后cancelled |
| `S03-A39` | cancel含已发布child | child保留；未完成work停止；无implicit purge |
| `S03-A40` | Task deadline过期前未claim | Process failed deadline-exceeded-before-start |
| `S03-A41` | ready wake丢失 | recovery补wake，不新建Process |
| `S03-A42` | terminal→next崩溃 | recovery按相同decision补materialization |
| `S03-A43` | waiting无reason/ref故障注入 | invariant检测、failed/quarantine evidence |
| `S03-A44` | revision/proof冲突 | fail loud，不热切/猜测/伪造 |
| `S03-A45` | recovery重复运行100次 | 行数/Outcome/child/业务提交不增加 |
| `S03-A46` | cleanup任一 fence未闭合 | 不设置eligible、不删除 |
| `S03-A47` | cleanup全部满足 | current pointer清空、summary完整、S12可删除Process |
| `S03-A48` | Process cleanup前后查询 | Execution/Task/items/restart/lineage/proof语义等价 |
| `S03-A49` | Workflow API CUD/Task graph override | strict reject；registry/runtime不变 |
| `S03-A50` | compiled/command/outcome泄漏扫描 | 无secret、绝对路径、平台plan、非必要runtime payload |
| `S03-A51` | allowlisted+preflight passed | Outcome后直接materialize next route，无gate/decision |
| `S03-A52` | human review required | Process terminal；Execution waiting+exact gate ref，无active lease |
| `S03-A53` | gate released | append+CAS+outbox后same Execution恢复，Workflow/S05 binding不变 |
| `S03-A54` | Preflight runtime/schema/evidence错误 | same Process retry/failed，不创建human gate |
| `S03-A55` | Outcome/gate/decision crash四窗口 | repair幂等；无duplicate gate/route/decision/Execution |
| `S03-A56` | stale gate/target/fence decision | typed conflict；current Execution/gate不变 |


### 7.S04 槽位 · Intake Asset Lifecycle

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S04-intake-asset-lifecycle.md` |
| 状态 | accepted / S04-v1.2 |
| HARD 范围 | S04-A01..A40 |
| 验收方法 | bootstrap + acceptance 事务 + serving CAS + purge fence + zero-legacy 扫描。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S04-intake-asset-lifecycle.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S04-A01` | 空DB首次bootstrap | schema+constraints+registries成功，readiness true，无legacy输入 |
| `S04-A02` | 同版本同manifest再次bootstrap | no-op，row/digest不变化 |
| `S04-A03` | 同版本registry digest不同 | fail-loud，readiness false，无原位覆盖 |
| `S04-A04` | cross-team IntakeSource/IntakeItem/IntakeRevision lookup | 不可见且无存在性泄漏 |
| `S04-A05` | single one-member intake | 一Snapshot/一membership/稳定Item/正确Revision decision |
| `S04-A06` | scatter N members | 一Snapshot、N memberships、恰好required child intents |
| `S04-A07` | zero-member complete-authoritative | typed zero result与合法absence policy，不悬挂running |
| `S04-A08` | partial Snapshot缺少旧Item | 不产生absence deactivation |
| `S04-A09` | complete-authoritative缺少旧Item | 产生typed absence action并按policy transition |
| `S04-A10` | 同observation/digest重放 | 返回同Snapshot，无重复Revision/membership/intent |
| `S04-A11` | 同observation异digest | intake-observation-conflict`并保留审计 |
| `S04-A12` | 语义tuple相同 | no-change，不建Revision，membership引用既有Revision |
| `S04-A13` | fingerprint参与值变化 | append新Revision，predecessor/ordinal/definitions正确 |
| `S04-A14` | 新semantic definition发布 | 新Revision可绑定新version；历史Revision解释不变 |
| `S04-A15` | candidate构建失败 | old serving继续，latest/serving按已提交truth保持 |
| `S04-A16` | proof-valid publish | Item/transition/outbox同事务CAS，检索双围栏放行 |
| `S04-A17` | stale pointer/proof publish | 冲突或proof invalid，无pointer改变 |
| `S04-A18` | deactivate | serving立即null，异步projection残留也不可检索 |
| `S04-A19` | reactivate | active但serving仍null，需重新proof publish |
| `S04-A20` | delete | durable tombstone，普通ingest/rebuild不复活 |
| `S04-A21` | Task cancel且已有published child | published child保留，未完成work停止，无隐式withdrawal |
| `S04-A22` | pages缺失/timeout | candidate abandoned，无Snapshot |
| `S04-A23` | member/bytes超限 | accept前fail-loud，不生成partial Snapshots |
| `S04-A24` | sealed后acceptance崩溃 | 重放收敛到一个Snapshot |
| `S04-A25` | commit后wake丢失 | outbox replay补wake，不重复truth |
| `S04-A26` | IntakeArtifact bytes orphan | grace后清理，不出现canonical引用 |
| `S04-A27` | canonical IntakeArtifact缺失 | fail-closed + repair intent，无virtual IntakeArtifact |
| `S04-A28` | recovery重复100次 | Snapshot/Revision/child/proof行数不增长 |
| `S04-A29` | reindex新generation失败 | old generation持续服务 |
| `S04-A30` | reindex验证成功 | CAS切generation，grace后旧代eligible cleanup |
| `S04-A31` | purge存在hold/reference | intake-retention-fenced`，无substrate删除 |
| `S04-A32` | 某substrate proof失败 | aggregate未complete，retry且serving不恢复 |
| `S04-A33` | 全部cleanup proofs完成 | physical purge complete，最小tombstone/audit仍可查 |
| `S04-A34` | payload_extra round-trip | 所有适用表存在；核心logic不读取未晋升key |
| `S04-A35` | schema/registry/workflow ref drift | startup readiness false，不自动猜修 |
| `S04-A36` | legacy dependency scan | runtime/config/DDL/API/event/startup零依赖 |
| `S04-A37` | CandidateSet缺S05 binding/PreflightOutcome或root digest不一致 | acceptance拒绝，无Snapshot/Revision/membership |
| `S04-A38` | blocked但可保存的partial observation | 按contract接受可信Intake事实，但无RAG准入；Item无review state |
| `S04-A39` | open gate release/reject | IntakeItem lifecycle、Revision与Snapshot不变；只影响Execution route |
| `S04-A40` | open gate引用Artifact进入GC候选 | retention/reference fence阻止删除直至gate终结 |


### 7.S05 槽位 · Intake & Cleaning

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S05-intake-cleaning.md` |
| 状态 | accepted / S05-v1.1 |
| HARD 范围 | S05-A01..A35 |
| 验收方法 | 四类 source golden + preflight allowlist + gate decision CAS + evidence lineage。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S05-intake-cleaning.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S05-A01` | fresh DB bootstrap | definitions/handlers/bindings确定性注册；二次no-op |
| `S05-A02` | same version different digest | readiness fail-loud |
| `S05-A03` | inline payload | body先staging，descriptor无正文 |
| `S05-A04` | local object | logical ref有效，absolute path拒绝 |
| `S05-A05` | static HTTP success | declared/detected/verified media与raw digest完整 |
| `S05-A06` | redirect/stream/decompress over budget | 消费期间终止，无complete candidate |
| `S05-A07` | browser/PDF acquisition | acquisition与clean capability分账 |
| `S05-A08` | local OCR / Vision clean | producer/model/prompt/loss/quality lineage完整 |
| `S05-A09` | registered API single | strict envelope/member schema与stable key |
| `S05-A10` | scatter pagination complete | exhaustion proof + stable ordering + root digest |
| `S05-A11` | provider合法空集合 | 只有profile证明exhausted才complete |
| `S05-A12` | required member malformed | rejection evidence保留，root不得自动进RAG |
| `S05-A13` | duplicate normalized key | 按definition fail/merge，结果确定性 |
| `S05-A14` | same page replay same digest | idempotent |
| `S05-A15` | same page replay different digest | conflict + abandon/fail |
| `S05-A16` | missing page/count/Artifact | seal拒绝 |
| `S05-A17` | JSON/text/HTML golden canonicalization | SHA-256/JCS/NFC/structure parser结果稳定 |
| `S05-A18` | cleaner/model版本变化，source semantics未变 | 不制造IntakeRevision |
| `S05-A19` | allowlist缺validator/check-set | activation/start fail；不fallback |
| `S05-A20` | allowlisted + passed | Outcome存在，继续RAG，无gate/decision |
| `S05-A21` | allowlisted + blocked reviewable | open gate + Execution waiting |
| `S05-A22` | blocked且missing Artifact | 不允许human approve |
| `S05-A23` | validator runtime/schema error | S03 retry/failed，不转human blocked |
| `S05-A24` | non-allowlisted + passed | open human gate |
| `S05-A25` | approve exact target | decision/gate/Execution/outbox原子，恢复same Execution |
| `S05-A26` | stale generation/fence/target decision | typed conflict + audit，无状态变化 |
| `S05-A27` | duplicate decision idempotency key | 同结果幂等；异内容冲突 |
| `S05-A28` | Outcome→transition crash | 只重放transition，不重跑/热切validator |
| `S05-A29` | gate→waiting crash | repair projection，不建duplicate gate |
| `S05-A30` | decision→outbox crash | 重放outbox，不重写decision |
| `S05-A31` | new validator version after Execution start | retry/resume继续旧binding |
| `S05-A32` | existing Task要求升级 | S02 causal restart/new generation，旧gate失效 |
| `S05-A33` | long-lived open gate | 不自动approve；Artifact/evidence引用受保护 |
| `S05-A34` | payload_extra注入identity/proof/secret | schema/lint拒绝 |
| `S05-A35` | runtime/config/DDL/API scan | 零legacy/Cloudflare/R2/D1/SMCP dependency |


### 7.S06 槽位 · Structurizer

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S06-lsrag-structurizer.md` |
| 状态 | accepted / S06-v1.1 |
| HARD 范围 | S06-A01..A22 |
| 验收方法 | fail-closed 输入 + kernel invalid + repair 新 artifact + readiness schema。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S06-lsrag-structurizer.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S06-A01` | 缺 clean artifact / digest 不匹配 | fail-closed，无 Process success |
| `S06-A02` | Command materialize 后替换 clean 再 retry | 仍用原 digest；或 conflict |
| `S06-A03` | 生成 invalid tree（多 root/环） | kernel fail；pointer 不变；Invocation 有账 |
| `S06-A04` | leaf 无 anchor | kernel fail |
| `S06-A05` | coverage 遗漏/乱序 | kernel fail |
| `S06-A06` | extension repair 成功 | 新 artifact；全量复验；pointer 更新 transition |
| `S06-A07` | repair 触碰 kernel | invalid；不 CAS |
| `S06-A08` | max-retries 耗尽 | Process failed；历史完整 |
| `S06-A09` | full-valid success | structure+projection+report current 一致 |
| `S06-A10` | 下游拼装跨 generation projection | 拒绝 / fail-loud |
| `S06-A11` | schema version 异 digest bootstrap | readiness false |
| `S06-A12` | 无注册 schema 启动 | readiness false |
| `S06-A13` | scatter child 独立 structure | 无跨 Item 大树 |
| `S06-A14` | required child structure fail | 按 Workflow loss policy 归约；S06 不静默丢 |
| `S06-A15` | Task-scoped read 跨 Task 访问 | 403/deny |
| `S06-A16` | S06 success 后 serving 未自动切换 | serving 仍旧直至 S09 proof |
| `S06-A17` | 禁止用户 generation 精修 API 作为 v1 必过 | 无该 surface 或明确 defer |
| `S06-A18` | legacy package import / SMCP 依赖扫描 | 零命中 |
| `S06-A19` | large-input 超 budget | fail-loud 或 profile 声明的合法 disposition，非截断冒充成功 |
| `S06-A20` | model 返回 summary 字段 | 忽略或 invalid（不得进入 kernel truth） |
| `S06-A21` | process-local 无限 repair | 禁止；受 repair_budget + S03 |
| `S06-A22` | 实现可不打开 QNA | 文档自包含审查 |


### 7.S07 槽位 · Constructor

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S07-lsrag-constructor.md` |
| 状态 | accepted / S07-v1.1 |
| HARD 范围 | S07-A01..A22 |
| 验收方法 | 整包 dual-channel + binding cross-gen 拒绝 + budget fail-loud + 不切 serving。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S07-lsrag-constructor.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S07-A01` | 缺 structure/projection 或 digest 不匹配 | fail-closed；无 CAS |
| `S07-A02` | 跨 generation 拼装 structure 与 projection | CONSTRUCT_BINDING_CROSS_GENERATION |
| `S07-A03` | 模型改写 original | kernel fail |
| `S07-A04` | 应有 summary 缺失/空 → 整包失败 | 无 CAS；非 partial success |
| `S07-A05` | full-valid 成功 | 成员 current 一致；outbox 可观测 |
| `S07-A06` | 同 command_input_digest 重试 | 同 digest；幂等或 conflict |
| `S07-A07` | max-retries 耗尽 | Process failed；无 usable current；历史可查 |
| `S07-A08` | metadata_refresh + reuse_summaries | 新 generation；meta/content_full 更新；dual-channel 仍完备 |
| `S07-A09` | filter 模型发明键 | reject |
| `S07-A10` | content_full 重算 digest 不匹配 | S08 对账失败路径 |
| `S07-A11` | 无 ConstructionSchema 注册启动 | readiness false |
| `S07-A12` | 超预算 | CONSTRUCT_BUDGET_*`；无截断成功 |
| `S07-A13` | scatter child 独立 construct | 无跨 Item 大包 |
| `S07-A14` | Outcome 无 path/R2/正文 | contract test |
| `S07-A15` | 零 legacy constructor/SMCP 依赖 | 扫描零命中 |
| `S07-A16` | S07 success 不切 serving/index | serving 仍旧 |
| `S07-A17` | 无公网 construct API | surface 测试 |
| `S07-A18` | pending 队列表不作为 SSOT | 架构测试 |
| `S07-A19` | original-only 尝试 CAS | 禁止 |
| `S07-A20` | process-local summary repair 成功路径 | v1 不存在 |
| `S07-A21` | 无 plan 盲调模型 | 禁止 |
| `S07-A22` | 实现可不打开 QNA | 文档自包含审查 |


### 7.S08 槽位 · Embedding & Vectorization

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S08-embedding-vectorization.md` |
| 状态 | accepted / S08-v1.0 |
| HARD 范围 | S08-A01..A15 |
| 验收方法 | ConstructGate + 整包 dual-channel + 幂等 upsert + Layer A 隔离。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S08-embedding-vectorization.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S08-A01` | construct 未 full_valid 不能 full_valid vectorize | 集成 / 门闩单测 |
| `S08-A02` | dual-channel required 缺一失败 | 集成 |
| `S08-A03` | g=0 original 缺失/stripped → fail | 单测 |
| `S08-A04` | ContentFull 错 digest → CONTENT_MISMATCH | 单测 |
| `S08-A05` | 同 command_input_digest 重放幂等 | 集成 |
| `S08-A06` | 半写后失败 → 无 publication；重试覆盖成功 | 故障注入 |
| `S08-A07` | outbox 重复投递不双成功分裂 | 集成 |
| `S08-A08` | Layer A 混模拒绝 | 单测 |
| `S08-A09` | 权威 industry_domain 有值则 record 可滤 | 集成 |
| `S08-A10` | S08 不写 serving pointer | architecture / 集成 |
| `S08-A11` | transport 429 不增加 process.retry_count 直至耗尽 | 与 S11 联测 |
| `S08-A12` | purge_generation 只 soft-delete 指定 generation | 集成 |
| `S08-A13` | services 不 import llm_adapters / db driver | architecture |
| `S08-A14` | 零 smind_vec_process / content_full 列 | schema 扫描 |
| `S08-A15` | 实现路径不读 qna-truth 作 SSOT | 文档/代码审查 |


### 7.S09 槽位 · Vector Index

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S09-vector-index.md` |
| 状态 | accepted / S09-v1.0 |
| HARD 范围 | S09-A01..A20 |
| 验收方法 | PublicationProof 对账 + ActiveIndex CAS + 谓词/topk/metric 合同。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S09-vector-index.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S09-A01` | Handoff full_valid + 全量行 → Proof + triples | 集成 |
| `S09-A02` | 缺 unit → PUBLISH_MISSING_UNIT；无 Proof 提升 | 故障 |
| `S09-A03` | Handoff 与库 digest 漂移 → fail | 故障 |
| `S09-A04` | 半写 generation 不可 publication | 故障 |
| `S09-A05` | S09 不写 serving_revision | architecture |
| `S09-A06` | S04 CAS 失败保留旧 serving + Proof 仍在 | 集成 |
| `S09-A07` | candidate CAS active 后谓词只见新 gen | 集成 |
| `S09-A08` | grace 前旧 gen 不可服务；后 soft-deleted | 集成 |
| `S09-A09` | rebuild 失败 active 不变 | 故障 |
| `S09-A10` | deactivate → withdrawn；S10 双围栏拒绝 | 集成 |
| `S09-A11` | top_k > max_topk 拒绝 | 合同 |
| `S09-A12` | 客户端 metric override 拒绝 | 合同 |
| `S09-A13` | soft-deleted 不计入 actual | 单元 |
| `S09-A14` | Layer A 不匹配 fail | 单元 |
| `S09-A15` | 幂等同 digest 重放 | 集成 |
| `S09-A16` | ANN 缺失 readiness=false | readiness |
| `S09-A17` | hard capacity fail-loud | 容量 |
| `S09-A18` | 禁仅 ANN 命中返回（缺谓词） | architecture |
| `S09-A19` | S08 purge vs S09 retire intent 分离 | 集成 |
| `S09-A20` | scatter 子 Execution 独立 proof | 集成 |


### 7.S10 槽位 · Retrieval & Reranking

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S10-lsrag-retrieval.md` |
| 状态 | accepted / S10-v1.0 |
| HARD 范围 | S10-A01..A20 |
| 验收方法 | dual-fence + traceback/inflation + rerank 诚实 fallback + context-only。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S10-lsrag-retrieval.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S10-A01` | 合法 serving+active gen → 返回 hits；含 generation_refs | 集成 |
| `S10-A02` | ANN 命中但 publication 不 valid → 不入 results | 集成 |
| `S10-A03` | ANN 命中但 lifecycle deactivated → 不入 results | 集成 |
| `S10-A04` | 缺 team → error 非 empty | 合同 |
| `S10-A05` | 未知 filter key → RETRIEVE_FILTER_INVALID | 合同 |
| `S10-A06` | return_k > max_topk → fail-loud | 合同 |
| `S10-A07` | recall_k < return_k → fail 或 clamp 策略按实现 fail-loud | 合同 |
| `S10-A08` | summary hit → traceback resolved + payload original | 集成 |
| `S10-A09` | missing original → status failed/degraded；不标 original | 故障 |
| `S10-A10` | inflation 附加 g=0；超 roots/chars 可观测 | 集成 |
| `S10-A11` | rerank fail → ANN order + ann_score；无 0.5 | 故障 |
| `S10-A12` | Layer A mismatch → error | 单元 |
| `S10-A13` | Response 无 embedding[] / 无 answer | architecture |
| `S10-A14` | blank query → empty | 合同 |
| `S10-A15` | include_pack true → pack 字段与 truncated 行为 | 集成 |
| `S10-A16` | dual channel same unit dedup | 单元 |
| `S10-A17` | 不创建 Task/Process 行 | architecture |
| `S10-A18` | soft-deleted vectors 不可服务 | 集成 |
| `S10-A19` | non-active index_generation 不可被 client 选择 | 合同 |
| `S10-A20` | readiness：embed 缺失 false；contracts 缺失 false | readiness |


### 7.S11 槽位 · Inference Runtime

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S11-inference-runtime.md` |
| 状态 | accepted / S11-v1.1 |
| HARD 范围 | S11-A01..A19 |
| 验收方法 | architecture facade + 禁 silent swap + 闸/transport + catalog readiness。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S11-inference-runtime.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S11-A01` | services→llm_adapters | 架构失败 |
| `S11-A02` | structured 未校验成功 | 拒绝 |
| `S11-A03` | 默认路径强制 remote | 失败/禁用 |
| `S11-A04` | dim 与 namespace 不符 | SPACE_VIOLATION |
| `S11-A05` | 429 后换 model | 禁止 |
| `S11-A06` | transport 耗尽 | EXHAUSTED；retry_count 未因内环虚增 |
| `S11-A07` | 闸满 | BACKPRESSURE；无模型调用 |
| `S11-A08` | 多 claimed Process | 仍受闸 |
| `S11-A09` | upsert 失败 | outbox 未 done |
| `S11-A10` | 幂等重放 | 无双冲突行 |
| `S11-A11` | 删 outbox 疏通 | 禁止 |
| `S11-A12` | 仅有向量 | 非 Task success |
| `S11-A13` | 跨 team | 拒绝 |
| `S11-A14` | 无 team filter | 拒绝 |
| `S11-A15` | industry-domain 过滤 | 仅匹配 |
| `S11-A16` | prompt 进 invocation | 禁止 |
| `S11-A17` | Workers 必选 | 不存在 |
| `S11-A18` | catalog digest 漂移 | readiness false |
| `S11-A19` | 无 QNA 依赖实现 | 审查/文档测试：Spec 自包含 E 包 |


### 7.S12 槽位 · Turso Persistence

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S12-turso-persistence.md` |
| 状态 | accepted / S12-v1.1 |
| HARD 范围 | S12-A01..A23 |
| 验收方法 | TX 矩阵 + outbox/claim + migration/CW/vector readiness + 禁 PG 必选。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S12-turso-persistence.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S12-A01` | domain import driver | 架构失败 |
| `S12-A02` | 双可写库 | 拒绝 |
| `S12-A03` | Task 创建缺 audit | TX 失败 |
| `S12-A04` | claim 无 fence 写 outcome | 拒绝 |
| `S12-A05` | stale fence | 拒绝 |
| `S12-A06` | lease 过期 recovery | CAS 回 ready/failed |
| `S12-A07` | commit 前发 queue | 禁止 |
| `S12-A08` | 崩溃 outbox pending | 重启后投递 |
| `S12-A09` | 重复投递 | 幂等 |
| `S12-A10` | Candidate partial accept | 失败 |
| `S12-A11` | pointer CAS 冲突 | fail-loud |
| `S12-A12` | 无 bytes 登记 handle | 禁止 success |
| `S12-A13` | migration checksum drift | readiness false |
| `S12-A14` | 缺 StructureSchema | readiness false |
| `S12-A15` | CW 缺失（默认） | readiness false |
| `S12-A16` | vector 能力缺失（默认） | readiness false |
| `S12-A17` | vector 无 team/generation | 拒绝 |
| `S12-A18` | 仅有向量行 | 不自动 serving/Task success |
| `S12-A19` | 跨 team 读 | 拒绝 |
| `S12-A20` | legacy smind 依赖 | 零命中 |
| `S12-A21` | PG 必选路径 | 不存在 |
| `S12-A22` | VIEW 上 UPDATE | 禁止 |
| `S12-A23` | 实现可不打开 QNA | 文档自包含 |


### 7.S13 槽位 · Artifact Storage

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S13-artifact-storage.md` |
| 状态 | accepted / S13-v1.1 |
| HARD 范围 | S13-A01..A21 |
| 验收方法 | bytes-first crash suite + ref/GC fence + identity readiness + 无 public object。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S13-artifact-storage.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S13-A01` | promote 后崩溃再 TX 回滚 | orphan 可 GC；无业务 success |
| `S13-A02` | 同 team 同 digest 并发 promote | 复用；无不同内容覆盖 |
| `S13-A03` | 跨 team 同 digest | 不复用 |
| `S13-A04` | open gate_evidence | GC 不删 |
| `S13-A05` | serving/current 保护 | 不 release/GC |
| `S13-A06` | 篡改文件 verify | INTEGRITY + incident |
| `S13-A07` | live ref 删文件 | MISSING 非静默清 |
| `S13-A08` | 超 256MiB 默认 | BUDGET |
| `S13-A09` | path `.. | 拒绝 |
| `S13-A10` | identity mismatch | readiness false |
| `S13-A11` | domain pathlib 写 root | arch fail |
| `S13-A12` | public object HTTP | 不存在 |
| `S13-A13` | delete fence 竞态 | 中止删 |
| `S13-A14` | grace=0 | 拒绝/readiness fail |
| `S13-A15` | backup verify 失败 | 不标记完整 |
| `S13-A16` | handle team 不符 | AUTH |
| `S13-A17` | staging 过期 | 可清且无 live ref |
| `S13-A18` | Process terminal | 不级联硬删对象 |
| `S13-A19` | crash suite fsync | 完整或可回收 |
| `S13-A20` | zero legacy r2/SMCP storage | 扫描零命中 |
| `S13-A21` | 实现可不打开 QNA | 文档自包含 |


### 7.S14 槽位 · Config/Prompt/Model Registry

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S14-config-prompt-model-registry.md` |
| 状态 | accepted / S14-v1.1 |
| HARD 范围 | S14-A01..A30 |
| 验收方法 | prompt hash + L4 materialize + override allowlist + bootstrap digest。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S14-config-prompt-model-registry.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S14-A01` | git prompt 变更但未更新指针 → 运用路径 `PROMPT_HASH_MISMATCH · 集成 | T-O-264/285 |
| `S14-A02` | 指针 hash 与文件一致 → 加载成功；envelope 含 prompt_identity+hash · 集成 | T-O-282 |
| `S14-A03` | DB/schema **无** `body_text` 列 / 禁止写入正文 · architecture | T-O-264 |
| `S14-A04` | materialize 后修改 L1 active → in-flight 仍用 L4；新 Execution 用新值 · 集成 | T-O-269/277/278 |
| `S14-A05` | ops log level reload 成功不改 binding_digest · 集成 | T-O-278/281 |
| `S14-A06` | ops reload 失败 → last-good + `CONFIG_OPS_RELOAD_FAIL`；binding 不变 · 故障 | T-O-278 |
| `S14-A07` | override 未知键 → `CONFIG_OVERRIDE_REJECTED · 合同 | T-O-279 |
| `S14-A08` | override `model_key` → reject · 合同 | T-O-279/267 |
| `S14-A09` | override `top_k` 在 cap 内 → 进入 snapshot digest · 集成 | T-O-279 |
| `S14-A10` | override 超 cap → reject · 合同 | T-O-279 |
| `S14-A11` | empty-DB bootstrap 幂等两次同 digest · 集成 | T-O-275 |
| `S14-A12` | 同 version 异 definition_digest → readiness false / `BOOTSTRAP_FAIL` 或 `REGISTRY_DIGEST_MISMATCH · 集成 | T-O-273/285 |
| `S14-A13` | required capability 无 enabled binding → `BINDING_NOT_FOUND · 合同 | T-O-285 |
| `S14-A14` | model status disabled → `MODEL_DISABLED · 合同 | T-O-285 |
| `S14-A15` | RegistryPort 无外部 CUD 路径（architecture + HTTP 若有） · architecture | T-O-280 |
| `S14-A16` | workflow 视图只读；无法经 S14 写 S03 七表 · architecture | T-O-268 |
| `S14-A17` | Semantic knob 变更改变 binding_digest；Ops knob 不改变 · 单元 | T-O-281 |
| `S14-A18` | feature flag 默认 OFF；远程 flag 客户端不存在 · architecture | T-O-281 |
| `S14-A19` | structured_generate provenance 缺 schema digest → fail · 合同 | T-O-282 |
| `S14-A20` | envelope 写入 prompt 正文 / secret → 拒绝 · 安全 | T-O-282/286 |
| `S14-A21` | aux.*` 不能被 S06 binding 接受 · architecture | T-O-283 |
| `S14-A22` | resolve 不接受 `model_version=latest · 合同 | T-O-284 |
| `S14-A23` | display_name 变更不改变 resolve 结果 · 单元 | T-O-284 |
| `S14-A24` | digest mismatch **不**映射为 429/transient · 合同 | T-O-285 |
| `S14-A25` | path 含 `..` → reject · 安全 | T-O-286 |
| `S14-A26` | secret 不出现在 git config fixture / envelope dump · 安全 | T-O-286 |
| `S14-A27` | services 不直连 llm_adapters 绕过 catalog（与 S11 共测） · architecture | T-O-266；S11 |
| `S14-A28` | 无 agent 写 registry API · architecture | T-O-270 |
| `S14-A29` | 实现树不依赖 QNA 路径 · architecture | SSOT |
| `S14-A30` | 禁止依赖 legacy-specs/python 树 · architecture | T-O-274 |


### 7.S15 槽位 · Observability & Reliability

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S15-observability-reliability.md` |
| 状态 | accepted / S15-v1.1 |
| HARD 范围 | S15-A01..A20 |
| 验收方法 | event 同 TX + metric 低基数 + live/ready 分账 + operator token。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S15-observability-reliability.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S15-A01` | 业务 TX 含 domain_events 插入失败 → 整 TX 回滚 · unit/integration | T-O-291 |
| `S15-A02` | 业务成功行存在时必有对应 event（适用 TX-01..08） · integration | T-O-291/289 |
| `S15-A03` | diagnostic 写失败不回滚业务且 drop metric>0 · unit | T-O-292 |
| `S15-A04` | 业务事件缺 team 或 trace 被拒 · unit | T-O-290 |
| `S15-A05` | retention job 删除仅发生在过期窗；未过期保留 · integration | T-O-302 |
| `S15-A06` | Process cleanup 后 events 仍在（未过 retention） · integration | T-O-297 |
| `S15-A07` | metric 注册含 task_uuid label → 拒绝/drop · unit | T-O-303 |
| `S15-A08` | /metrics` 返回 Prometheus text 且无 uuid label 泄漏 · integration | T-O-303 |
| `S15-A09` | /live` 路径零 DB 调用 · unit | T-O-305 |
| `S15-A10` | obs_tables 缺失 → `/ready` 503 · integration | T-O-305 |
| `S15-A11` | readiness false 持续触发 alert 信号 · integration | T-O-304 |
| `S15-A12` | 已持久化 trace 在 recovery 路径不被替换 · unit | T-O-306 |
| `S15-A13` | 无外部 HTTP 可写 process CAS 的 repair API · architecture | T-O-307 |
| `S15-A14` | timeline 无 token → 拒绝 · integration | T-O-308 |
| `S15-A15` | dead 行可 list 且 metric 可见 · integration | T-O-309 |
| `S15-A16` | redrive 仅经 S12 Port 审计路径 · architecture | T-O-309 |
| `S15-A17` | payload 含 secret 字段 schema 拒绝 · unit | T-O-311 |
| `S15-A18` | security_audit 与 domain_events 无混写路径 · architecture | T-O-293 |
| `S15-A19` | 无业务库 metrics 时序表 migration · architecture | T-O-288 |
| `S15-A20` | 实现模块可在不打开 QNA 条件下对照本文编码 · review | SSOT |


### 7.S16 槽位 · Security & Trust Boundary

| 字段 | 值 |
|---|---|
| 权威 SSOT | `domain-truth/S16-security-trust-boundary.md` |
| 状态 | accepted / S16-v1.1 |
| HARD 范围 | S16-A01..A24 |
| 验收方法 | token 401-before-read + rate/egress + redaction + sec_token_loaded ready。 |
| 槽位完成定义 | 本域全部 HARD 在目标 release 剖面通过；与上游 D/S 无未关闭冲突 |
| 关键禁令（抽样） | 见源文件 §5 反例；本 ledger 不重复维护第二反例 SSOT |

#### HARD 清单（权威来源：`domain-truth/S16-security-trust-boundary.md`）
| ID | HARD 断言摘要 | 证据/方法 |
|---|---|---|
| `S16-A01` | API · 无 token 调 Task Create → 401 `SEC_TOKEN_MISSING`；无业务行；可 audit | API |
| `S16-A02` | API · valid token + 任意已注册 team → 无 membership gate；按资源状态处理 | API |
| `S16-A03` | API · invalid token + 存在的 task_uuid → 401；**不**因资源存在返回不同 body 枚举 | API |
| `S16-A04` | Token · dual-active 两指纹 → 两者均可 200 | Token |
| `S16-A05` | Token · revoke previous → 旧 401；新 200；audit 有 revoke | Token |
| `S16-A06` | Token · timing-safe 单测 → 固定时间比较路径存在 | Token |
| `S16-A07` | Header · Bearer 优先于 X-header → 冲突时以 Bearer 为准 | Header |
| `S16-A08` | Rate · 超 token/IP 配额 → 429 `SEC_RATE_LIMITED`；无业务行 | Rate |
| `S16-A09` | Rate · 限流器故障注入 → 请求仍可走鉴权；degraded metric=1 | Rate |
| `S16-A10` | Audit · audit 写失败注入 → 5xx `SEC_AUDIT_WRITE_FAIL`；无业务行 | Audit |
| `S16-A11` | Audit · invalid-token 洪水 → metric 上升；audit 行受采样上限 | Audit |
| `S16-A12` | Egress · URL=`http://169.254.169.254/ → SEC_EGRESS_DENIED | Egress |
| `S16-A13` | Egress · redirect 链至私网 → SEC_EGRESS_REDIRECT_DENIED` 或 DENIED | Egress |
| `S16-A14` | Debug · 生产 profile 调 file-debug → SEC_DEBUG_DISABLED | Debug |
| `S16-A15` | Redact · 日志含 Authorization → 输出为 redacted | Redact |
| `S16-A16` | Path · 错误路径含绝对 path → 对外 envelope 无绝对 path | Path |
| `S16-A17` | Isolation · 缺 team 的检索 → fail-closed（邻域+SEC_TEAM_SCOPE） | Isolation |
| `S16-A18` | Supply · 任意 base_url override → SEC_MODEL_ENDPOINT_REJECTED` / UNBOUND | Supply |
| `S16-A19` | Probe · /live` 无 token → 200；无 secret | Probe |
| `S16-A20` | Probe · 空 ActiveTokenSet `/ready → 503；`sec_token_loaded` 失败 | Probe |
| `S16-A21` | Metrics · 模拟公网匿名策略 → 部署文档禁止；可选 bearer 可测 | Metrics |
| `S16-A22` | Secret · 未知 slot → SEC_SECRET_UNRESOLVED | Secret |
| `S16-A23` | Replay · 幂等 Create 重放 → 同业务结果（S01/S02）；非新 SSOT 表 | Replay |
| `S16-A24` | OOS · 不存在 OAuth login 路由 → architecture 扫描通过 | OOS |


---

## 8. 与索引 / 18 / OT-04 的关系

| 文档 | 关系 |
|---|---|
| `spec-index` | 完成定义应引用 **D07 HARD + G01–G14**；附录 A 可勾选本文件槽位 |
| 历史 `18` | 签署与最终 freeze 仪式；可引用 D07 作为验收矩阵 SSOT |
| OT-04 legacy | 精神祖先；本文件为 **现行 domain-truth 时代** 的执行验收台账 |
| 各域 §6 | **逐条 HARD 权威**；D07 为 ledger 与全局收口 |

---

## 9. 滚动构建记录（v0.1 → v0.4 reasoning）

| 版本 | 构建动作 | 推理结论 |
|---|---|---|
| **v0.1** | 建槽位总表 + OT-04 风格全局门闩 | 需要「一域一槽」否则无法收口 22 份真相 |
| **v0.2** | 注入 S01–S07/D01/D03 全量 A 表 | 前半链路 HARD 已充分；必须全量引用而非摘要丢 ID |
| **v0.3** | 注入 S08–S16/D06 + D02/D04/D05 派生 HARD | 后半链路与无 A 表的 D 域必须可勾选 |
| **v0.4** | E2E 场景 + release 剖面 + non-goals + 资源非 blocker | 可对 owner 声明「如何算交付」；P3 live 可选 |

---

## 10. Domain verdict（草稿）

| 项 | 状态 |
|---|---|
| 槽位覆盖 D01–D06 / S01–S16 | **完整** |
| HARD 权威 | 以各域正文为准；本文件 ledger |
| 可支持 V1 收口 | **是（草稿）**；待 owner freeze → accepted |
| 开放 | golden corpus 具体条目表（归 P4 资产，可另文）；D06 仍 draft |

**草稿结论**：`D07-v0.4` 足以作为 **验收与 HARD 交付标准** 的工作 SSOT 候选；owner 冻结后应回填 `spec-index`（D07 行）并与 `18` 分账签署。

---

## 11. 修订历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| `D07-v0.1` | 2026-08-12 | draft | 槽位骨架 + 全局门闩 |
| `D07-v0.2` | 2026-08-12 | draft | S01–S07/D01/D03 HARD 注入 |
| `D07-v0.3` | 2026-08-12 | draft | S08–S16/D06 + D02/D04/D05 派生 |
| `D07-v0.4` | 2026-08-12 | draft / owner-review | **收口版**：E2E、release 剖面、non-goals、全槽位 HARD 台账 |

---

## Appendix A — HARD 计数核对

| 槽位 | 计数 |
|---|---:|
| D01 | 24 |
| D02 (派生) | 8 |
| D03 | 17 |
| D04 (派生) | 12 |
| D05 (派生) | 10 |
| D06 | 10 |
| S01 | 39 |
| S02 | 40 |
| S03 | 56 |
| S04 | 40 |
| S05 | 35 |
| S06 | 22 |
| S07 | 22 |
| S08 | 15 |
| S09 | 20 |
| S10 | 20 |
| S11 | 19 |
| S12 | 23 |
| S13 | 21 |
| S14 | 30 |
| S15 | 20 |
| S16 | 24 |
| **合计** | **527** |

若源文件增删 `*-A*`，以源文件为准并在本附录重计。
