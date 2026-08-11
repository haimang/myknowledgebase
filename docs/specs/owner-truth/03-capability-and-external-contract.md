# OT-03 — Capability and External Contract

> **项目**：`myknowledgebase`（MKB）
>
> **文件 ID**：`OT-03`
>
> **文档性质**：`owner-truth / foundational only`
>
> **版本 / 日期**：`OT-03-v1.0 / 2026-08-10`
>
> **文档状态**：`frozen`
>
> **导入状态**：`baseline import complete / foundational QNA closed`
>
> **Truth 状态**：`OT03-T001..T031 locked / inherited`；`OT03-T032 owner-frozen`
>
> **上游索引**：`docs/specs/index.md`
>
> **上游 Owner Truth**：`OT-01-v1.0`、`OT-02-v1.0`

本文件只回答 MKB v1 可以被调用来做什么、接受哪些输入类别、上游可以观察和控制哪些 Task/结果语义，以及 LS-RAG 与 retrieval 的产品截止线。Endpoint、payload 字段、Process key、Workflow graph、模型、Prompt、embedding、索引、表结构、算法和部署参数不属于本文件。

---

## 1. Inherited Locked Truth

### 1.1 权威来源

| 来源 | 导入范围 | 导入纪律 |
|---|---|---|
| `docs/specs/owner-truth/01-product-boundary.md` `OT-01-v1.0` | knowledge 处理/转换/存储/获取闭环、LS-RAG 核心、最终答案与上游业务 OOS、单体与 trust boundary | 作为已冻结上游 Owner Truth；本文件只能细化 capability 与外部可观察结果，不能扩大产品责任 |
| `docs/specs/owner-truth/02-domain-model.md` `OT-02-v1.0` | Task/Execution/Process、Intake/derived asset 身份、六 StateFamily、state-vs-fact、proof owner | 只引用身份和状态宪法，不重新设计实体、状态或 transition |
| `docs/baseline/domain-truth/S01-skill-worker-integration.md` `S01-v1.5` | caller-neutral MKB Contract、Team/token、Task/Audit、固定 request intents、polling、受控 caller 权限和 gate decision | 导入外部 capability 与行为；wire、字段、HTTP 和 persistence 细节下沉 ES-01/08 |
| `docs/baseline/domain-truth/S02-task-api.md` `S02-v1.3` | Task 六态、五类可观察事实、collect-all、cancel、retry/rebuild、result readiness、generation/restart/lineage 查询 | 导入上游可观察语义；CAS、cursor 编码、transaction 和 route 设计下沉 Execution Spec |
| `docs/baseline/domain-truth/S05-intake-cleaning.md` `S05-v1.1` | 四类 source、完整 acquisition/clean capability、typed evidence、mandatory preflight、ExecutionGate | 导入有限 capability 与 admission 结果；handler、canonicalizer、validator、表与恢复实现不进入本文件 |
| `docs/baseline/qna-truth/S06.md` `T-O-77..85` | immutable generation/invocation 历史、current selection、versioned Structure Schema、kernel/extension/repair 边界 | 只导入已冻结九条 Truth；Q4–Q6 的 held/reframe/open 内容一律不导入 |
| `docs/baseline/spec-glossary.md` `v1.4` | canonical Task、Intake、Artifact、Retrieval 与 proof 词义 | 沿用 canonical vocabulary，不创建同义 contract 或新身份 |

### 1.2 导入覆盖对账

| Foundational cluster | 本文件落点 | 已覆盖的冻结来源 |
|---|---|---|
| 外部调用权与有限 capability | `OT03-T001..T010` | `S01-T002/T005/T017..046/T047..061`、`S02-T001..007/T032..041` |
| 输入、acquisition、clean 与 admission | `OT03-T011..T018` | `S05-T001..T030` |
| Task、result 与控制的可观察语义 | `OT03-T019..T025` | `S02-T008..T042`、`S01-T052..060` |
| LS-RAG artifact/schema 与 retrieval 截止线 | `OT03-T026..T031` | `OD-08`、`T-O-77..85`、`OT01-T008/T013/T014`、`OT02-T017/T018/T023` |
| Raw-vector 外部截止线 | `OT03-T032` | `OT-03 Q1 / owner answer` |

### 1.3 导入截止线

1. `OT03-T001..T031` 是冻结 baseline Truth 与 OT-01/02 的原义归并，不是新的 capability 推荐。
2. S06 只有 `T-O-77..85` 具备 frozen 身份；其 Q4 exact structure、Q5 curation/inspection、Q6 generation retry reframe 及所有 held/open 候选均不得被本文件提升为 Truth。
3. Baseline 中已经冻结、但属于 wire 或实现层的字段、enum、HTTP code、cursor、CAS transaction、logical table、handler、validator、model、Prompt、embedding 和 index 细节继续有效地约束对应 Execution Spec，不因未逐项抄入 Owner Truth 而丢失。
4. `legacy-family/`只提供 ReferenceAnchor；其 Cloudflare topology、callback、schema、storage key、job/status 与兼容行为不进入 MKB Contract。
5. 基础导入阶段没有自动生成 QNA；后续 Round 1 仅准入并关闭一个真实 foundational 歧义。OT-03现已冻结，不把 execution unknown 包装成新一轮 owner 问题。

---

## 2. Foundational Statements

### 2.1 外部调用权与有限 capability

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT03-T001` | MKB v1 只通过 caller-neutral、版本化的内部 MKB Contract 被 internal orchestrator 调用。简单内部 token 证明调用权，`team_uuid`负责审计、隔离、追踪与过滤但不构成授权；只有已注册且 active 的 Team 可以发起新 Task。 | `OT01-T003/T005/T006`、`S01-T002/T017/T021/T022/T046` |
| `OT03-T002` | v1 提供有限的 Team 接入投影能力：注册、读取/列举、修改描述、activate、deactivate、soft-delete 与显式 restore。inactive/deleted Team 不能发起新 Task，但其既有 Task、结果和审计仍可按权限查询；该能力不得扩张为 membership、RBAC 或 billing。 | `S01-T018..T022`、`OT01-T005/T006` |
| `OT03-T003` | v1 持久异步 request intent 固定为 `intake.ingest`、`intake.rebuild`、`intake.update_metadata`、`intake.deactivate`、`intake.delete`、`index.rebuild`。它们表达 knowledge resource 动作，不等于 clean、structurize、construct、vectorize 等内部 Process 类型。 | `S01-T023..T026` |
| `OT03-T004` | `retrieval.search` 是 v1 的同步查询能力，不创建持久 Task、Execution 或 Process。若未来要求异步 retrieval，必须作为明确的 foundational scope delta 重新裁决，不能由实现自行打开。 | `S01-T025`、`OT01-T013/T014` |
| `OT03-T005` | 对持久异步工作，上游只面对一个 Task 聚合边界：创建和查询 Task、有限修改非语义描述、轮询状态/结果/原子项、发送 cancel 或 full-retry 控制、请求 atomic IntakeItem rebuild、查看 generation/restart/lineage，并在确有人工 gate 时提交受控 decision。Exact endpoint 与 envelope 由 ES-01 定义。 | `S01-T028..T031/T057..T061`、`S02-T001/T019/T024..T041` |
| `OT03-T006` | 每个 Task Create 必须携带一个且仅一个独立、immutable 的上游业务 Audit snapshot，并与 Task 原子成立。MKB只校验和保存该 snapshot，不解释其业务审批状态，也不把运行日志当作 Audit。 | `S01-T032..T038`、`S02-T004` |
| `OT03-T007` | Task 的原始 identity、request intent、业务输入与 Audit 创建后不可变。Contract 输入必须严格、版本化并拒绝未知核心字段；同一身份的相同创建重放必须收敛，不同输入不得覆盖既有 Task；可变控制必须使用条件式并发保护。Exact schema、fingerprint 与 revision 表达归 ES-01。 | `S01-T023/T026/T029/T039/T044/T045`、`S02-T031` |
| `OT03-T008` | v1 异步结果只通过 polling 交付，不提供 webhook/callback；MKB也不承担 skill-worker 主动注册、注销、心跳或 manifest lifecycle。 | `S01-T003..T005`、`OT01-T009` |
| `OT03-T009` | Caller 无权创建、更新、command 或依赖内部 Execution、Process、Workflow phase、claim、lease、retry counter、status、progress 或 result truth。所有控制从 Task 向下传播，所有 Outcome/proof 从 runtime 向 Task 聚合。 | `S01-T028/T031/T047/T048/T052`、`OT02-T002..T006` |
| `OT03-T010` | Task、result、items、generation、restart 与 lineage 的公共读面必须 team-scoped、有界且可稳定轮询；它们可以返回安全的业务 identity、状态、proof/result summary 与 causal links，但不得泄漏 token、stack、绝对路径、driver detail 或内部 Process payload。 | `S02-T019/T032..T040` |

### 2.2 输入、acquisition、clean 与 admission

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT03-T011` | v1 只有四类外部 source kind：`inline_payload`、`local_object`、`http_resource`、`registered_api`。这是固定 taxonomy 上限；browser、PDF、OCR、Vision、single、scatter 与 pagination 是 capability 或 cardinality，不是额外 source kind。 | `S05-T001/T002` |
| `OT03-T012` | v1 acquisition/clean capability 必须覆盖 inline/local 输入、网页 static/browser 获取、PDF、registered API single/scatter/pagination、local OCR 与 Vision/model-assisted clean。该清单是有限的已冻结能力面，不能因 legacy 实现缺口缩减，也不能被解释为任意插件平台。 | `S05-T001..T004`、`OT01-T008/T013` |
| `OT03-T013` | Source kind、acquisition capability、clean capability 与 cardinality 必须保持正交。Source/capability definition 由 MKB 内部以 immutable versioned contract 拥有；caller 只能选择 contract 允许的输入，不能自造 source kind、注入 handler、validator、agent rule 或动态 plugin。 | `S05-T002/T004/T027` |
| `OT03-T014` | 输入 contract 必须把稳定 source identity、运行配置、secret reference 与正文/bytes 分账；source member 必须能由 source-specific、版本化且可证明的稳定 ExternalKey 识别。Credential、绝对路径或任意 fetch options 不能伪装成 identity；无法形成稳定 key 时不得以随机值或 content hash 猜测。 | `S05-T005..T007` |
| `OT03-T015` | Acquisition/Clean 跨域产出必须是 typed evidence/candidate，而不是 opaque child file 或万能 payload；raw representation、source-grounded canonical semantics 与 clean-derived output必须分账。OCR/Vision/model clean 可以形成派生产物，但不能单独制造 IntakeRevision。 | `S05-T008..T010`、`OT02-T010/T012/T013` |
| `OT03-T016` | single/scatter collection 必须保留 complete、partial、rejected 与 gap 的可证明事实。可信 partial 事实可以保存，但缺页、重复、required rejection、未证明 source exhaustion 或 artifact 缺失不能被宣称为完整输入并进入成功路径。 | `S05-T012/T013/T015` |
| `OT03-T017` | 所有进入 LS-RAG 的输入都必须经过 mandatory preflight，allowlist 只能决定通过验证后的自动 admission，不能绕过验证。Required anomaly 必须阻断对应 scope；runtime/schema/evidence 错误走统一 retry/failed，不能降格成人工可批准的业务 blocked。 | `S05-T014..T018`、`S01-T058` |
| `OT03-T018` | `passed + allowlisted` 直接继续 LS-RAG，不创建虚构 gate；只有 non-allowlisted 或确实 reviewable 的 blocked 情况可以进入 human path。Human review 是 existing Execution 的 durable gate，MKB只提供 Task-scoped `action_required` 与受控 decision contract，不建设 UI，也不允许人工伪造缺失 evidence 或绕过 full validation。 | `S05-T018/T020..T024`、`S01-T059..T061` |

### 2.3 Task、result 与控制的可观察语义

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT03-T019` | Task aggregate status 只有 `queued/running/cancelling/succeeded/failed/cancelled`。Status、result readiness、TaskItem outcome、`action_required` 和 soft-delete visibility 是五个正交可观察事实；不得拼成 `reviewing`、`retrying`、`partially_succeeded` 或其他新状态。 | `S02-T008..T015`、`S02` §1.3.1、`OT02` §2.2 |
| `OT03-T020` | Polling 必须明确区分尚未 ready、ready success、terminal failure 与 terminal cancellation；运行中的 progress/items、open gate 的 `action_required` 与资源 visibility 独立表达。未完成不能伪装成不存在，open gate 时 Task 仍为 `running`。 | `S02-T037/T039/T040` |
| `OT03-T021` | Task `succeeded` 必须由 current root 的 type-specific durable proof 支持。LS-RAG build/rebuild 的 proof 必须绑定 exact IntakeRevision，并证明预期 vector/filter metadata 已发布且验证；queue empty、日志、单次 callback、文件存在、latest Revision 或单个 vector ACK 都不是成功。 | `S01-T056`、`S02-T011`、`OT02-T023` |
| `OT03-T022` | single 与 scatter 对外都只有一个 Task。Scatter 使用 collect-all：required child 失败不取消健康 siblings；proof-valid child 可以先独立 ready、读取和检索，parent 后续 failed/cancelled 不回滚它；mixed outcome 通过 bounded items/counts 表达，不新增 partial-success Task status。 | `S02-T016..T023` |
| `OT03-T023` | Cancel 是 forward-stop，不是 rollback、delete 或 purge。接收 cancel 只表示控制意图已受理；只有 active descendants 已收敛且不可能 late business commit 时 Task 才能成为 `cancelled`，已 proof-valid 的 Intake/Vector 结果继续保留。 | `S02-T013/T014/T022` |
| `OT03-T024` | 外部重做分为两种可观察语义：full Task retry 保持 Task identity、创建新的 generation/root tree；atomic IntakeItem rebuild 为稳定 Item 创建新的 `intake.rebuild` Task。两者都保留 immutable 旧历史与因果，不允许 caller 选择内部 stage/process recovery，也不因 rebuild 自动创建 IntakeRevision。 | `S01-T057`、`S02-T010/T015/T024..T031` |
| `OT03-T025` | Task soft-delete 只改变可见性，不等于 cancel、IntakeItem delete 或物理清理。Task/Audit、restart causation、generation terminal summary、proof/result 与 lineage 不得因 Process cleanup、日志 retention 或 Task soft-delete而断裂。 | `S02-T034..T036` |

### 2.4 LS-RAG 与 retrieval 产品截止线

| Truth ID | 已固化 foundational truth | Provenance |
|---|---|---|
| `OT03-T026` | MKB v1 的 LS-RAG capability 包含完成 Structurizer、Constructor、original/summary 双通道、Traceback、Reranker、结构化向量构建/存储与 retrieval 所需的有限闭环。它们都是 knowledge 工具内部能力，不形成通用 agent、内容编辑或产品 Workflow 平台。 | `OD-08`、`OT01-T008/T013..T015` |
| `OT03-T027` | 每次 S06 generation、repair 或 retry 只要形成输出，就必须形成 immutable GenerationArtifact 历史；每次相关模型调用无论是否形成 artifact，都必须留下 durable GenerationInvocation、exact binding、因果与 token evidence。日志不能替代该历史，旧产物不能原位覆盖。 | `T-O-77` |
| `OT03-T028` | 每个 `(team_uuid, execution_uuid, artifact_type)` 任一时刻只有一个受并发保护的 current selection，且只能指向归属、binding 与 full validation 均通过的 immutable logical artifact。Invalid/repair-failed 产物只留历史；v1 以 Task-scoped surface 提供 list/get/current 查询，Create 只归 current-fenced Process，普通 Update/Delete 不开放。该 pointer 不是 Intake serving 或 index pointer。 | `T-O-78/T-O-79`、`OT02-T017/T018` |
| `OT03-T029` | Structure Schema 由 MKB 内部拥有并 immutable versioned；Execution、artifact、producer 与 consumer 必须绑定和加载 exact key/version/digest，不兼容、缺失或 digest drift 必须 fail-loud，retry/resume/recovery 不得切换 `latest`。外部 caller、工具和 agent 没有 Schema CUD。 | `T-O-80/T-O-81` |
| `OT03-T030` | Structure Schema 必须同时约束 strict shape、不可由 agent 修补的 deterministic kernel、可受控修补的 governed extension 与 semantic/source proof。Repair 只能产生新的 immutable artifact 并从零 full-validate；失败返回 typed evidence，由统一 Process retry/max-retries 收敛。不得放宽 Schema、generic fallback、局部复验、切 latest 或改写历史；S06 成功不等于 Task、serving 或 retrieval 成功。 | `T-O-82..T-O-85` |
| `OT03-T031` | Retrieval 的产品结果止于同步返回 structured、grounded、可追溯且可供上游消费的 vector-backed semantic Retrieval Result，包括完成 original/summary traceback 与 rerank 所需的知识证据；exact result shape、budget、ranking 和 index 查询由 ES-07 冻结。该结果不包含 `OT03-T032` 禁止的 raw vector。MKB 不生成最终自然语言答案，也不承载上游问答、agent、会话或其他产品业务。 | `OT01-T008/T013/T014`、`S01-T025`、`OT03-T032 clarification` |
| `OT03-T032` | MKB v1 的公共 Contract 不提供最低层级 raw embedding vector 的读取、列举、导出或其他 vector primitive API。上游只通过同步 `retrieval.search` 消费 structured、grounded、可追溯且经过 rerank 的 semantic Retrieval Result；VectorRecord、EmbeddingSpace 与 IndexGeneration保持 MKB 内部 substrate。该裁决不删除 MKB 内部的向量构建、存储、验证、重建、检索或清理职责。 | `OT-03 Q1 / owner answer` |

---

## 3. Hard Scope / Non-goals

| Non-goal ID | 明确禁止进入 OT-03/v1 capability 或 external contract | 边界说明 |
|---|---|---|
| `OT03-N001` | Final answer generation、Chat、Agent、会话、问答策略、用户可见 citation presentation 或任何上游业务 | Retrieval 只返回 grounded knowledge/vector result |
| `OT03-N002` | Endpoint path、HTTP verb/code、payload 字段、serialization、cursor 编码、DDL、表数与 transaction 实现 | 归 ES-01/04/07/08，不提交 owner QNA |
| `OT03-N003` | 由 caller 选择或操作 Process key、Workflow graph、phase、claim、lease、fence、retry counter 或内部 route | Caller 权限止于 Task 与受控 gate decision |
| `OT03-N004` | 新增第七 StateFamily、`reviewing/retrying/partially_succeeded` 等新 Task status或组合状态 | 六 StateFamily 与五类 Task 可观察事实已经冻结 |
| `OT03-N005` | 第五类 source kind、caller-defined handler/validator、动态脚本、plugin marketplace 或 generic ingestion platform | 四类 source 与有限 capability 是 v1 上限 |
| `OT03-N006` | 以 allowlist、人工 decision 或 model output 绕过 preflight、required evidence、kernel 或 full validation | 所有成功都必须走相同 proof boundary |
| `OT03-N007` | v1 webhook/callback、skill-worker registration/control plane 或异步 retrieval Task | v1 异步工作只 polling；retrieval 固定同步 |
| `OT03-N008` | 任意 mutable generation artifact、按 mtime/latest/ordinal 猜 current、外部 Schema CUD 或历史重解释 | 违反 `T-O-77..85` |
| `OT03-N009` | 在本文件冻结 exact tree/node/block/anchor 字段、artifact type 清单、generation bundle 或 one-shot commit | 这些没有被 `T-O-77..85` 冻结，归 ES-06 在既有边界内设计 |
| `OT03-N010` | Model/provider/Prompt、OCR/Vision engine、embedding、vector backend、index schema、rerank 算法或容量参数 | 都是 Execution Spec 技术裁决 |
| `OT03-N011` | 将 OCR/Vision/summary/clean output 直接当 IntakeRevision，或将 Generation current 当 serving/index current | Identity 与 SelectionPointer 必须按 OT-02 分账 |
| `OT03-N012` | Human-review UI、通用内容编辑、协作审核、RAG artifact 人工 patch 或 CMS | Gate 只是有限的 Execution admission control，不扩大产品层 |
| `OT03-N013` | Legacy API/schema/status/storage compatibility、import、migration、dual-read 或 cutover | `legacy-family`永久只作 ReferenceAnchor |
| `OT03-N014` | 为未来可能性预留新的 intent、source kind、callback、plugin、状态、服务或文件 | 新 externally visible capability 必须由 owner 主动 reopen，不能由 ES 暗中开放 |
| `OT03-N015` | Raw embedding vector read/list/export、VectorRecord CRUD、caller-supplied raw-vector query 或通用 vector database surface | “消费向量”已由 Owner 收口为消费 semantic Retrieval Result；最低层级 vector substrate 不对上游开放 |

---

## 4. Open Foundational Decisions

### 4.1 Round 1 准入结论

本轮只准入 `1` 个问题：Owner 所说“向上游提供这些向量的消费能力”是否意味着 raw vector 本身也是公共 Contract 资源。

该问题同时满足 `docs/specs/index.md` §2.3：

1. `OT01-T013` 使用“向量及其知识结果的检索/消费能力”，但 `S01-T025` 只冻结同步 `retrieval.search`，两者不能无歧义地确定 raw vector 是否对外；
2. 两种答案会改变 externally visible capability、Contract 稳定面和 v1 验收对象；
3. “只提供语义 Retrieval Result”与“同时提供 raw vector read/export”是两个产品结果实质不同、均可实现的选择；
4. 该问题可以不讨论 endpoint、payload、embedding model、dimension、metric、index 或 backend。

其余候选轴全部剔除，见 §4.3；本轮不为达到题数而生成第 2、3 题。

### 4.2 Q1 — “上游消费向量”是否包含 raw vector read/export

**单一决策轴**：MKB v1 的公共 Contract 是只提供由内部向量存储驱动的 semantic Retrieval Result，还是还把已存储的 raw embedding vector 作为上游可读取/导出的公共资源。

**已继承 Truth**：

- `OT01-T013/T014`：MKB负责 knowledge 处理、转换、存储与获取，但不承担 final answer 或上游业务；
- `OT01` Q1：MKB 返回 grounded Retrieval Result，包含召回、Traceback、Rerank、provenance 与 context，exact contract 转交 OT-03/ES-07；
- `OT03-T004/T031`：v1 已冻结同步 `retrieval.search`，不创建 Task/Execution/Process；
- `S04-T015/T016/T023`：正常检索只能读取 exact proof-valid ServingRevision/IndexGeneration，vector row 存在本身不授予 retrieval eligibility；
- `OT02-T017/T018/T023`：Vector 是 derived fact/asset，不是 Intake identity、Process 或 serving pointer；
- `OT03-N010`：embedding space、vector backend 与 index schema 是 executional，不应自动变成产品 Contract。

**尚未关闭的歧义**：上述 Truth 已确定“检索什么可以被返回”，但没有明确“存储层的 raw embedding 数组是否也必须成为可独立读取/导出的 v1 产品能力”。由 ES-07 擅自选择任何一边，都会暗中改变外部 Contract，因此必须在这里一次性收口。

#### Scope Impact Audit — 推荐选项 A

```text
Scope Impact Audit
- New product responsibility: no
- New externally visible behavior: no
- New V1 capability: no
- New domain identity or StateFamily: no
- New deployment/runtime unit: no
- New owner-truth file: no
- New execution-spec file: no
- Raises a fixed capacity ceiling: no
- Can be solved inside an existing file and boundary: yes
- Classification: no expansion
```

#### 推荐执行选项 A — 只公开 semantic Retrieval Result

**推荐将“上游消费向量”解释为：上游通过同步 `retrieval.search` 消费由 MKB 向量存储计算出的 grounded Retrieval Result；raw embedding vector、VectorRecord list/get/export 和向量存储 CRUD 均保持 MKB 内部。**

推荐边界如下：

1. 上游提交语义检索请求，MKB内部完成 query embedding、eligibility fence、vector search、hydration、Traceback、dedupe、rerank 与 context budgeting；
2. 上游获得 structured hit/context、original/summary lineage、稳定 anchor、provenance、score/rerank 与必要 proof reference；
3. 上游不直接读取或导出存储的 embedding 数组，也不把 MKB 当作通用 vector database；
4. Exact query/result 字段、过滤项、score 表达和 algorithm 继续由 ES-07 自行冻结，不回流 owner；
5. MKB 内部仍完整持有 VectorRecord、EmbeddingSpace、IndexGeneration、publication proof、rebuild 与 retrieval lifecycle；“不公开 raw vector”不等于删除向量能力。

#### 完整 Reasoning

1. **与 Owner 已冻结的产品语言一致**：Owner 将 MKB 定义为 knowledge 处理与获取工具，而不是 storage primitive 产品。Grounded Retrieval Result 让上游消费向量产生的知识结果，同时不把内部存储表示提升为新的产品面。
2. **与唯一已冻结的 retrieval 入口一致**：Baseline 只冻结了同步 `retrieval.search`，并将 Task、Execution、Process 排除在查询路径外；没有冻结 VectorRecord 的公共 CRUD/list/export。选项 A 是对现有 contract 的收紧解释，不新增入口。
3. **避免把 execution binding 变成长期产品承诺**：Raw vector 只有结合 exact embedding model/revision、dimension、metric、normalization、truncation 与 index generation 才有语义。公开数组会迫使这些本应由 ES-05/07 可演进的技术 binding 成为上游兼容面。
4. **保持 serving 与物理存在分离**：S04 已冻结“vector 存在不等于可检索”。若允许绕过 RetrievalEligibility 直接读取 VectorRecord，上游可能消费 deactivated、旧 ServingRevision、旧 IndexGeneration 或尚未 publication-valid 的数据，破坏既有 logical fence。
5. **保持 LS-RAG 的产品价值**：MKB 的差异化输出是 original/summary 双通道、Traceback、provenance、rerank 和 grounded context。Raw float array 不携带这些语义，反而会把 MKB 降格成存储导出层。
6. **限制容量与兼容范围**：Raw-vector read/export 会新增大体积传输、分页/批量导出、空间版本兼容、retention 与 reindex 可见性等独立验收面。它们都超出当前固定的同步 Retrieval Result 闭环。
7. **不会削弱上游业务能力**：上游生成 final answer 或执行业务只需要稳定、可追溯的 Retrieval Result；它无需理解 MKB 选择了哪个 embedding 或 vector backend，也不会因内部 reindex/model upgrade 被迫同步升级。
8. **保留有证据的未来变化路径**：若未来出现一个明确上游必须读取 raw vectors 的真实需求，Owner可以主动 reopen `OT03-Q1`，以 bounded foundational delta 增加只读能力。当前不为假设性复用预留开放面。

#### 选择后果

| 选择 | 产品结果 | Scope 判定 |
|---|---|---|
| **A — 只公开 semantic Retrieval Result（推荐）** | 上游消费 grounded hit/context、Traceback、provenance 与 rerank；embedding/vector/index substrate完全由MKB内部管理 | `no expansion` |
| **B — 同时提供 raw vector read/export** | Raw embedding 成为稳定公共资源；V1还需承诺其可见性、版本语义、批量读取/导出和跨 reindex/model upgrade 行为 | `bounded foundational delta` |

选项 B 即使只读，也不是一个 payload 字段差异：它会新增 externally visible capability 和独立成功标准。若 Owner 选择 B，OT-03 必须先明确这个新增上限，再由 ES-07 设计 exact contract；不得顺势增加 vector mutation、通用 similarity API 或 vector database 产品职责。

若选择 B，其 bounded delta 仅限于：为 retrieval-eligible、proof-valid 的存储向量增加只读 read/export 能力，并相应修订 `OT03-T031/N010/C014`。它不会授权 raw vector ingest、caller-supplied vector query、create/update/delete、跨 Team 读取，也不会新增 Task intent、StateFamily、部署单元或 spec 文件；这些内容继续作为明确 non-goal。其直接代价是 ES-07 必须新增 raw-vector 可见性、embedding-space 版本语义、批量读取边界和 reindex/model-upgrade 兼容验收。

#### 推荐 A 的明确 Non-goals

- 不禁止 MKB 内部创建、读取、验证、重建或清理 VectorRecord；
- 不删除 Retrieval Result 中的 score、anchor、provenance、proof 或 original/summary context；
- 不在本题决定 query/result 字段、filter 集、topK、ranking、embedding、index 或 backend；
- 不开放 caller 对 vector、embedding space 或 index generation 的 CRUD；
- 不把 final answer generation重新带回 MKB；
- 不因为未来“可能复用 raw vector”而预留未被真实需求证明的公共 endpoint。

#### Owner 回答

> 不提供最低等级的 raw vector。选择 A。

**裁决**：`接受 A / rejected B`。

**冻结落点**：

- `OT03-T032`：公共 Contract 只提供 semantic Retrieval Result；raw vector substrate保持内部；
- `OT03-N015`：禁止 raw vector read/list/export、CRUD、caller-supplied raw-vector query与通用vector database surface；
- `OT03-C016`：ES-07必须维持这一对外截止线。

**Scope 结论**：`no expansion / external contract narrowed and closed`。

### 4.3 未准入候选轴

| 候选决策轴 | 准入判定 | 证据与处置 |
|---|---|---|
| Retrieval 是否生成 final answer | `rejected / already frozen` | `OT01-T014` 已将 final answer 与全部上游业务冻结为 OOS |
| Retrieval 是否异步创建 Task | `rejected / already frozen` | `S01-T025`、`OT03-T004` 已冻结同步且不创建 Task/Execution/Process |
| 正常检索是否包含历史/非 serving Revision | `rejected / already frozen` | `S04-T015/T016/T023` 已冻结 exact ServingRevision + IndexGeneration eligibility；历史审计走已有 Task/generation read surface |
| 是否支持 caller-supplied query vector | `rejected / unsupported expansion` | Baseline 将 query embedding 放在 MKB 内部 retrieval 链路，Owner只提出消费已存知识/向量结果；没有证据要求新增 raw-vector input capability，默认不得开放 |
| Exact filter/topK/result 字段 | `rejected / executional` | Baseline 已将 filter、ranking、budget 与 result schema交 ES-07；其设计必须保持 bounded、strict 且不改变本题裁决的产品边界 |
| 是否提供通用 artifact browser/export | `rejected / already bounded or OOS` | `T-O-79` 只冻结 Task-scoped GenerationArtifact history；通用内容管理/浏览平台被 `OT01-N004/N009`、`OT03-N012` 排除 |
| Exact tree/node/block/anchor/artifact type | `rejected / executional` | S06 `T-O-80..85` 只冻结 schema/kernel 宪法，exact kind 已明确移交 ES-06，不得上提 owner |
| Vector backend、embedding model、index、rerank 与容量参数 | `rejected / executional` | `OT03-N010/C012..C015` 已指定 ES-05/07 以技术证据裁决 |

### 4.4 Round 1 Closure

| 项目 | 当前结论 |
|---|---|
| 通过准入的 foundational 问题 | `1` |
| 已回答 | `1` |
| 等待 Owner 回答 | `0` |
| 新冻结 Truth | `OT03-T032` |
| 重问 baseline 已冻结 Truth | `0` |
| 上提 executional unknown | `0` |
| 自动生成后续问题 | `0` |
| 后续 QNA 轮次 | `none` |
| OT-03 状态 | `frozen / v1.0` |

Q1已关闭。其余候选轴均为已冻结、可由现有Truth唯一推导、executional或unsupported expansion，不存在第二个合格 foundational 问题。除非 Owner 主动 reopen 并明确要替代的 `OT03-Txxx`，OT-03不再生成问题。

---

## 5. Owner Decisions

| Decision cluster | 已有 owner 裁决 | 固化落点 | 后续处理 |
|---|---|---|---|
| MKB Contract | 上游按 MKB Contract 适配；MKB 不继承调用方私有协议，caller 无内部 runtime 写权 | `OT03-T001/T005/T009/T010` | Wire 与 adapter 归 ES-01/08 |
| 有限调用面 | 最小 Team 投影、六种异步 intent、Task polling/control/history，以及同步 retrieval | `OT03-T002..T008` | 不自动增加 intent、callback 或 async retrieval |
| 输入与 clean | 四类 source，覆盖 inline/local/web/PDF/API/OCR/Vision 与 single/scatter/pagination | `OT03-T011..T016` | Exact schema/handler 归 ES-03/05 |
| Admission | allowlist 不能绕过 mandatory preflight；需要人工时使用既有 ExecutionGate 与 Task-scoped decision | `OT03-T017/T018` | 不建设 UI、policy/plugin 平台或新状态 |
| Task/result | 六态、五轴分账、collect-all、forward-stop cancel、full retry/atomic rebuild、proof-backed success | `OT03-T019..T025` | Exact route/CAS/transaction 归 ES-01/02/04 |
| LS-RAG artifact/schema | immutable history/current selection、exact versioned Structure Schema、kernel/extension 与 full revalidation | `OT03-T027..T030` | Exact structure 与实现归 ES-05/06 |
| Retrieval cutoff | 只返回可追溯 semantic Retrieval Result；最低层级 raw vector不对外；final answer和任何上游业务OOS | `OT03-T026/T031/T032`、`OT01-T013/T014` | Exact result schema归ES-07，但不得开放raw-vector primitive surface |

本节登记的owner裁决已全部固化。OT-03没有待批准事项，也不因后续Execution Spec设计自动reopen。

---

## 6. Constraints on Execution Specs

| Constraint ID | 必须由 Execution Spec 继承的约束 | 主要落点 |
|---|---|---|
| `OT03-C001` | ES-01 必须实现 caller-neutral、team-scoped 的有限外部 contract，并完整保留六种异步 request intent 与同步 `retrieval.search` 的边界；不得暴露 Execution/Process CRUD。 | `ES-01/08` |
| `OT03-C002` | Team Registry 只能实现有限接入投影和 active admission，不得增加 membership、RBAC、billing 或 platform ownership。 | `ES-01/08` |
| `OT03-C003` | Task Create、immutable Audit、strict versioning、idempotent replay、条件式 mutation 与 immutable original input 必须成为可验证 contract；exact fields、fingerprint 与 error mapping 由 ES-01 自行关闭。 | `ES-01/04` |
| `OT03-C004` | v1 异步交付只使用 polling；Task/result/items/generation/restart/lineage 必须有界、team-scoped，并在 Process cleanup 后仍可解释。 | `ES-01/02/04/08` |
| `OT03-C005` | Task 六态及 status/readiness/item/action_required/visibility 五轴不得改变；open gate、retry、mixed scatter 或 soft-delete 不得新增状态。 | `ES-01/02/03` |
| `OT03-C006` | Cancel、full retry、atomic rebuild、collect-all、early child readiness 与 proof-preserving semantics 必须保持；内部 CAS、fence、outbox 与 recovery 由 ES-01/02/04 选择最小实现。 | `ES-01/02/04` |
| `OT03-C007` | ES-03 只能使用四类 source kind，并覆盖已冻结 acquisition/clean capability；source/capability/cardinality 分账，caller 不得注入动态 handler/plugin。 | `ES-03/05` |
| `OT03-C008` | Raw、canonical semantics、clean-derived output、typed evidence/CandidateSet、complete/partial/rejection/gap 必须可区分且可证明；AI/OCR 不得越权创建 Revision。 | `ES-03/04/05` |
| `OT03-C009` | Mandatory preflight 适用于所有路径；allowlist 只决定 passed 后自动 admission。Runtime error不得人工 override，真实 human gate 必须通过既有 Execution/Task 边界表达。 | `ES-02/03/08` |
| `OT03-C010` | LS-RAG/Task success 必须消费绑定 exact IntakeRevision 的 vector/filter publication proof；文件、queue、日志、latest pointer 或单个 ACK 不得代替。 | `ES-02/03/04/06/07` |
| `OT03-C011` | ES-05/06 必须实现 immutable GenerationArtifact/Invocation 历史、每 type 唯一 full-valid current selection和 Task-scoped history read；不得原位覆盖、猜 latest 或开放普通 Delete。 | `ES-04/05/06` |
| `OT03-C012` | Structure Schema 必须内部 immutable versioned，producer/consumer exact-bind 并 fail-loud；exact tree/node/block/artifact type 由 ES-06 在该边界内自行冻结，不回流 owner。 | `ES-02/05/06/07` |
| `OT03-C013` | Kernel 不能被 agent patch；governed extension repair必须生成新 artifact 并 full-validate，失败统一交 S03 retry/max-retries，禁止 schema loosening、generic fallback 和私有 retry 状态机。 | `ES-02/05/06` |
| `OT03-C014` | ES-07 必须提供 structured、grounded、traceable、reranked 的同步 semantic Retrieval Result，并保持 exact IntakeRevision/derived/vector provenance；不得生成 final answer、返回 raw vector 或吸收上游业务。 | `ES-06/07` |
| `OT03-C015` | Endpoint、payload、Process key、model、Prompt、embedding、index、ranking、storage backend、容量和恢复参数必须由既有 Execution Spec给出默认方案与证据；不得创建新的 owner 问题、文件、StateFamily 或部署单元。 | 全部 ES |
| `OT03-C016` | ES-07只能公开semantic query与Retrieval Result，不得提供raw embedding vector read/list/export、VectorRecord CRUD、caller-supplied raw-vector query或通用vector-database API。内部VectorRecord/EmbeddingSpace/IndexGeneration可以完整设计，但不能泄漏为产品Contract。 | `ES-05/07/08` |

---

## 7. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| `OT-03-v0.1` | `2026-08-10` | `pending consolidation` | 创建 Capability and External Contract 基础文件；原义归并 S01-v1.5、S02-v1.3、S05-v1.1、S06 `T-O-77..85` 以及 OT-01/02 的冻结 Truth，形成 31 条 inherited foundational truth、14 条 hard non-goal 与 15 条 Execution constraint；明确排除 S06 未冻结 Q4–Q6、endpoint/payload/Process key、模型/索引实现及 final answer；未启动或生成 QNA，未新增 capability、domain、StateFamily、文件或部署单元。 |
| `OT-03-v0.2` | `2026-08-10` | `owner-review-needed` | 完成 Round 1 foundational 准入：仅“上游消费向量是否包含 raw vector read/export”无法从既有 Truth 无歧义推导，形成 Q1 并推荐只公开 semantic Retrieval Result；完整登记 Scope Impact Audit、两项选择、B的bounded delta上限、reasoning、non-goals及8类未准入候选。Q1等待Owner回答，不自动生成后续问题。 |
| `OT-03-v1.0` | `2026-08-10` | `frozen` | Owner选择A并明确“不提供最低等级的raw vector”；新增`OT03-T032/N015/C016`，将公共Contract收口为同步semantic Retrieval Result，raw vector与全部vector primitive保持内部。Q1关闭；closure审计未发现其他foundational分歧，不生成Round 2。 |
