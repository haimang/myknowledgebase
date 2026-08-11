# OT-01 — Product Boundary

> **项目**：`myknowledgebase`（MKB）
>
> **文件 ID**：`OT-01`
>
> **文档性质**：`owner-truth / foundational only`
>
> **版本 / 日期**：`OT-01-v1.0 / 2026-08-10`
>
> **文档状态**：`frozen`
>
> **导入状态**：`baseline import complete / foundational QNA closed`
>
> **Truth 状态**：`OT01-T001..T012 locked / inherited`；`OT01-T013..T015 owner-frozen`
>
> **上游索引**：`docs/specs/index.md`

本文件只回答 MKB 是什么、负责什么、不负责什么，以及它与上游、平台、legacy 和执行底座之间的产品边界。API 字段、表、状态实现、算法、进程、部署参数和安全实现不属于本文件。

---

## 1. Inherited Locked Truth

### 1.1 权威来源

| 来源 | 导入范围 | 导入纪律 |
|---|---|---|
| `docs/baseline/spec-index.md` §0.1 | `OD-01..12` | 作为 owner 已确认方向直接迁入，不重问、不降级为候选方案 |
| `docs/baseline/domain-truth/S01-skill-worker-integration.md` `S01-v1.5` | `S01-T001..007`、`S01-T017`、`S01-T028`、`S01-T046..048` | 只迁入产品定位、接入责任、Team/trust 和内外状态所有权边界；wire、schema、状态细节留给 OT-03/Execution Spec |
| `docs/baseline/qna-truth/S04.md` | `T-O-42` | 直接迁入 MKB 与 `legacy-family` 完全独立的 application boundary |
| `docs/baseline/spec-glossary.md` `v1.4` | `MKB`、`Team/team_uuid`、`MKB Contract`、`ReferenceAnchor` | 沿用 canonical 含义，不重新发明同义身份 |

`docs/baseline/`中的旧 QNA 编排、未冻结候选、实施方案和文件数量不随这些 Truth 迁入。

### 1.2 `OD-01..12` 覆盖对账

| Baseline ID | 本文件落点 | 迁移结果 |
|---|---|---|
| `OD-01` | `OT01-T001`、`OT01-T004` | leaf-worker 与无平台职责被保留 |
| `OD-02` | `OT01-T003` | 已知首个上游与 MKB Contract 独立性被保留 |
| `OD-03` | `OT01-T001` | 相对平台无状态、业务内部有状态被保留 |
| `OD-04` | `OT01-T005` | `team_uuid` 与最小 Team Registry 投影被保留 |
| `OD-05` | `OT01-T006` | 简单内部 token 与无复杂授权平台被保留 |
| `OD-06` | `OT01-T002` | 单 Python 应用、单发布单元被保留 |
| `OD-07` | `OT01-T010` | 本地/外部推理的 adapter-first 边界被保留 |
| `OD-08` | `OT01-T008` | LS-RAG 核心产品定位被保留 |
| `OD-09` | `OT01-T007` | MKB 自有 Task Contract/Workflow、拒绝继承旧平台 API 被保留 |
| `OD-10` | `OT01-C004` | Turso 方向被保留为 execution constraint，不上提为新 owner 问题 |
| `OD-11` | `OT01-T012` | 当前 Python 重构已退役被保留 |
| `OD-12` | `OT01-C005` | UUID 法则被保留为全执行域约束 |

### 1.3 固化纪律

1. `OT01-T001..T012` 是上述 baseline Truth 的原义归并，不是新推荐。
2. 后续 QNA 不得通过改写措辞重新询问这些结论；若确需改变，必须明确写出被替代的 OT01 Truth ID 与新增范围上限。
3. S01 中 endpoint、payload、HTTP error、DDL、transaction、retry 和状态投影等细节没有丢失，但它们不是 Product Boundary Truth，将由 OT-03 或对应 Execution Spec 继承。
4. Legacy 行为只能证明生产经验、风险或反例，不能覆盖本文件的 owner Truth。

---

## 2. Foundational Statements

| Truth ID | 已固化 foundational truth | Baseline provenance |
|---|---|---|
| `OT01-T001` | MKB 是一个完全独立、面向内部 orchestrator 的 standalone leaf-worker。它相对上游平台是执行叶节点，但业务内部有状态，并负责持有完成自身任务所需的 Task、Workflow 运行、资产、索引、retry 与结果证明。 | `OD-01/03`、`S01-T001` |
| `OT01-T002` | MKB 是一个 Python 应用、一个发布单元。内部领域、adapter、repository 或 worker loop 只是模块边界，不构成新的产品、服务或部署单元。 | `OD-06`、`S01-T001` |
| `OT01-T003` | MKB 的上游类型限于 internal orchestrator；`03-nano/orchestrator-core` 是已知首个调用方。MKB Contract 是接入真相，上游负责适配；任何当前上游私有协议都不能反向定义 MKB 核心模型。 | `OD-02`、`S01-T002/T007` |
| `OT01-T004` | MKB 负责 leaf-worker 内的任务执行与 LS-RAG 结果，不负责面向终端用户的平台职能。用户、会话、组织成员关系、团队所有权、角色权限、套餐、计费和 UI 均由上游产品或平台拥有。 | `OD-01`、`S01-T006` |
| `OT01-T005` | `team_uuid` 是上游提供并在 MKB 最小预注册的审计、分区、追踪和检索过滤身份。Team Registry 只是接入投影；它不使 MKB 获得 team ownership、membership 或商业计划职责。 | `OD-04`、`S01-T017` |
| `OT01-T006` | MKB 的 v1 调用信任模型是简单内部 token。有效 token 代表内部调用权，不派生 team-scoped membership/RBAC；`team_uuid` 本身也不是授权凭证。 | `OD-05`、`S01-T046` |
| `OT01-T007` | 上游只通过版本化 MKB Contract 表达 request intent、创建和操作外部 Task、读取聚合结果；MKB 独占内部 Workflow、Execution、Process、claim、retry 与结果证明。Task CRUD 和 Workflow 必须按 MKB 自身语义重建，不继承旧平台 API 或 Worker 消息拓扑。 | `OD-09`、`S01-T002/T028/T047/T048` |
| `OT01-T008` | MKB v1 的首要业务能力是 LS-RAG 闭环；Structurizer、Constructor、original/summary 双通道、Traceback、Reranker 以及其必要的构建、索引与检索结果都服务于这一核心，而不是服务于通用 worker 或内容平台。 | `OD-08` |
| `OT01-T009` | v1 的异步结果交付方式是 polling，不提供 webhook/callback；v1 不要求注册为 skill-worker，也不实现主动注册、注销、心跳或 manifest 生命周期。未来真实接入需求只能通过边界 adapter 增量加入，不能改变 MKB Contract。 | `S01-T003..005` |
| `OT01-T010` | 本地 CUDA/vLLM 与外部推理服务都是 MKB 可使用的执行底座。任何具体 provider、模型或运行时都不能成为产品身份或 LS-RAG Contract 的所有者；它们必须位于能力 adapter 之后。 | `OD-07` |
| `OT01-T011` | MKB 是 greenfield application，与 `legacy-family` 不存在兼容、导入、数据迁移、dual-read、身份映射、切流或运行回滚关系。`legacy-family` 永久只作 ReferenceAnchor，不形成 runtime、schema、API、bootstrap 或 acceptance 依赖。 | `T-O-42` |
| `OT01-T012` | 已退役的当前 Python 重构位于 `legacy-python/`，只可提供历史经验；它不是新 MKB 的增量开发基线、运行依赖、迁移来源或兼容目标。 | `OD-11` |
| `OT01-T013` | MKB 是 knowledge 的处理、转换、存储与获取工具。它接收上游输入的文档，完成清洗、结构化，并在 LS-RAG 引擎驱动下形成结构化向量存储，再通过内部 Contract 向上游提供这些向量及其知识结果的检索/消费能力。 | `OT-01 Q1 / owner answer` |
| `OT01-T014` | MKB 不持有任何产品层功能。最终答案生成，以及上游基于 MKB 构建的问答、agent、应用工作流或任何其他业务，全部属于 MKB out-of-scope；MKB Contract 不得吸收这些业务语义。 | `OT-01 Q1 / owner answer` |
| `OT01-T015` | MKB 为完成 knowledge 处理职责而持有的内部业务流转状态、工作流状态、资产生命周期、重试、恢复与清理真相，不属于产品层功能。MKB 必须自行持有和管理这些内部状态与生命周期，不能以“无产品层职责”为由将其删除或外包给上游。 | `OT-01 Q1 / owner clarification` |

`OT01-T001..T015` 均已冻结。除非 owner 主动 reopen 并明确替代具体 Truth ID，OT-01 不再接受新的 QNA 或 scope delta。

---

## 3. Hard Scope / Non-goals

| Non-goal ID | MKB 明确不负责 | 边界说明 |
|---|---|---|
| `OT01-N001` | 用户注册、登录、session、用户 Durable Object、聊天历史或 WebSocket 产品面 | 属于上游 user/orchestrator 状态 |
| `OT01-N002` | Team owner/member/role/permission、plan、billing、余额或商业成本归属 | 最小 Team Registry 不得成长为平台 ownership domain |
| `OT01-N003` | Web/React UI 或其他终端用户界面 | MKB 只提供内部 Contract |
| `OT01-N004` | 通用多租户配置平台、任意动态 Workflow designer 或 generic agent/worker 平台 | 只建设完成 MKB v1 LS-RAG 闭环所需的有限能力 |
| `OT01-N005` | v1 webhook/callback、skill-worker 注册控制面、心跳和上游私有 RPC 兼容 | v1 使用 polling；未来只允许 adapter 适配 |
| `OT01-N006` | 多应用、微服务或复刻 legacy Cloudflare 多 Worker/Queue 拓扑 | 固定为一个 Python 应用和一个发布单元 |
| `OT01-N007` | legacy importer、compatibility adapter、dual-read、ID/status 翻译、migration、cutover 或 rollback 产品 | `legacy-family`和`legacy-python`均不进入新运行时 |
| `OT01-N008` | 由 caller 创建、写入或直接推进内部 Execution/Process/Workflow 状态 | 对外权限止于 Task/Contract 边界 |
| `OT01-N009` | 最终答案生成，以及基于 MKB 的问答、agent、产品 Workflow、用户体验或任何上游业务逻辑 | 上游可以消费 MKB 的知识/向量结果，但消费后的业务永久不属于 MKB |

本节中的 non-goal 不是待办项，也不因为 Execution Spec 需要“预留扩展性”而自动进入未来范围。

---

## 4. Open Foundational Decisions

### 4.1 Round 1 准入结论

本轮只准入 `1` 个问题：baseline `G-07` 留下的“Retrieval 是否承担 answer generation”。它不能从 `OT01-T001..T012` 唯一推导，会改变 MKB 的产品责任、外部结果语义和 v1 能力边界，并且可以完全不使用实现细节表达，因此属于合格的 foundational 问题。

其余 baseline 未关闭项不进入 owner QNA：

- `G-06` canonical structure exact shape；
- `G-08` Turso 运行/进程模型；
- `G-09` 向量索引 backend；
- `G-10` 模型 fallback；
- `G-11` Artifact storage backend。

这些事项均可在现有 Owner Truth 下由 Execution Spec 以技术证据裁决。`G-01` skill-worker registration 与 `G-12` Workflow authoring 已分别由 `OT01-T009` 和 `OT01-N004/N005` 排除在 v1 外，也不得重复提问。

### 4.2 Q1 — MKB Retrieval 是否止于可追溯 Context，还是还负责生成最终答案 — `frozen`

**单一决策轴**：MKB v1 的产品责任是否包含面向消费方的 final answer generation。

**已继承 Truth**：

- `OT01-T003/T004`：MKB 是 internal orchestrator 下游的 leaf-worker，不拥有终端用户产品面；
- `OT01-T008`：MKB 核心是 LS-RAG 的结构化、索引、Traceback、Rerank 与 Retrieval 闭环；
- `OT01-T010`：推理模型和 provider 只是能力底座，不能反向定义产品边界；
- `S01-T025`：`retrieval.search` 在 v1 是同步查询，不创建 Task/Execution/Process；
- baseline `G-07`：该边界保持 `open`，此前没有 owner Truth 可直接复用。

**Scope Impact Audit — 推荐回答 A**：

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

#### 推荐回答 A

**MKB v1 的责任止于返回 structured、grounded、可追溯且经过 rerank 的 Retrieval Result；不生成面向最终用户的自然语言答案。最终答案合成由上游 orchestrator 或产品层负责。**

这里的 Retrieval Result 可以提供 original payload、命中的 summary/hit、稳定 anchor、provenance、score/rerank 结果以及组装答案所需的受预算 context；exact contract 由 OT-03/ES-07 裁决。MKB 内部为了 structurize、summarize、construct 或 rerank 使用模型，不属于 final answer generation，也不受本题禁止。

#### Reasoning

1. **责任与拓扑一致**：MKB 已被冻结为 internal leaf-worker，上游 orchestrator 才拥有用户请求编排与最终交互。把 final answer 放在上游能维持 `OT01-T003/T004` 的责任分界。
2. **保留 LS-RAG 的独立价值**：MKB 最有区分度的输出是 grounded context、original traceback 和 provenance。它们可以被多个上游回答策略复用，不需要绑定某一种 answer prompt、语气或产品体验。
3. **避免产品面横向扩张**：一旦 MKB 生成最终答案，就必须同时承担 answer prompt、引用呈现、安全策略、拒答、语言/格式、质量评估以及可能的会话上下文；这些都不是现有 v1 能力。
4. **保持可审计性**：Retrieval Result 可以直接检查“命中了什么、来自哪里、为何排序”。最终自然语言答案引入新的生成误差面，会把 retrieval quality 与 answer quality 混为一个不可独立验收的结果。
5. **保持调用闭环有限**：baseline 已冻结 `retrieval.search` 为同步查询。只返回 context 不需要新增异步 answer Task、answer lifecycle、answer storage 或第七个 StateFamily。
6. **不限制内部推理能力**：推荐方案只排除最终答案产品责任，不排除 Structurizer、Constructor、summary、rerank 等现有 LS-RAG 内部模型调用，也不改变 adapter-first 方向。

#### 选择后果

| 选择 | 产品结果 | Scope 判定 |
|---|---|---|
| **A — 只返回 grounded Retrieval Result（推荐）** | 上游负责 final answer；MKB 的质量与验收止于召回、Traceback、Rerank、provenance 和 context contract | `no expansion` |
| **B — MKB 同时负责 final answer generation** | 会新增答案生成和上游业务责任 | `rejected / OOS` |

Owner 已拒绝 B 及任何同类产品层扩张。answer generation 不得以同步接口、异步 Task、可选 plugin 或 future-ready 预留等形式回流。

#### 推荐 A 的明确 Non-goals

- 不生成最终自然语言回答、answer citation presentation 或用户可见解释；
- 不建设 chat/session/memory、answer persona、answer prompt 产品面或回答审核平台；
- 不创建 answer-generation Task、answer lifecycle、answer storage 或 answer-specific StateFamily；
- 不把内部 summary、structure generation 或 rerank 错认成终端答案生成。

#### Owner 回答

> MKB 的职责是接收上游输入文档，完成文档清洗、结构化，并在 LS-RAG 引擎驱动下完成结构化向量存储，再提供接口供上游消费。MKB 只是 knowledge 的处理、转换、存储、获取工具，不持有产品层功能；任何基于 MKB 的上游业务都是 OOS。MKB 内部业务流转状态和生命周期管理不属于产品层，因此必须由 MKB 自己持有。

**裁决**：`接受 A，并进一步收紧产品边界`。

**冻结落点**：

- `OT01-T013`：文档 → 清洗 → 结构化 → LS-RAG 结构化向量存储 → 上游检索/消费；
- `OT01-T014`：final answer 与全部上游业务 OOS；
- `OT01-T015`：内部状态和生命周期是 MKB 必须自持的工具内部真相，不是产品层。

**Scope 结论**：`no expansion / boundary narrowed and closed`。

### 4.3 Round 1 Closure

| 项目 | 结论 |
|---|---|
| 准入问题 | `1` |
| 已回答 | `1` |
| 新冻结 Truth | `OT01-T013..T015` |
| 未回答 foundational 问题 | `0` |
| 下一轮 QNA | `none` |
| OT-01 状态 | `frozen` |

Owner 已明确拒绝其他形式的 scope expansion，因此不自动生成 Round 2。任何未来产品层能力都不能以 OT-01 的“待补问题”名义进入；只有 owner 主动 reopen 才能改变本结论。

---

## 5. Owner Decisions

| Decision cluster | 已有 owner 裁决 | 固化落点 | 后续处理 |
|---|---|---|---|
| 产品身份与拓扑 | leaf-worker、内部有状态、Python 单体、单发布单元 | `OT01-T001/T002` | 不再讨论平台化或服务拆分 |
| 上游与责任 | 首个上游为 `03-nano/orchestrator-core`；MKB Contract 独立；上游只拥有 Task 侧交互 | `OT01-T003/T007` | 私有上游协议只在 adapter 处理 |
| 平台职责 | 无 user/team ownership/RBAC/billing/UI；保留最小 Team 投影和简单 token | `OT01-T004..T006` | 不再以 legacy 平台字段为理由扩张 |
| Knowledge 工具闭环 | 上游输入文档；MKB 清洗、结构化、LS-RAG 向量化存储并提供检索/消费接口 | `OT01-T008/T010/T013` | exact input、vector 与 retrieval contract 归 OT-03/Execution Spec |
| 产品层截止线 | final answer 及任何基于 MKB 的上游业务全部 OOS；内部流转状态和生命周期仍由 MKB 自持 | `OT01-T014/T015` | 不再生成产品层 QNA；内部状态不得因 OOS 被删减 |
| 首版接入 | polling；不做 callback 或 skill-worker registration lifecycle | `OT01-T009` | 未来只有出现真实接入需求才可提出 bounded delta |
| Greenfield 边界 | legacy-family 仅 ReferenceAnchor；legacy-python 已退役 | `OT01-T011/T012` | 不建立兼容、迁移或增量开发路径 |

本节只登记既有裁决，不构成新一轮 owner approval 请求。

---

## 6. Constraints on Execution Specs

| Constraint ID | 必须由 Execution Spec 继承的约束 | 主要落点 |
|---|---|---|
| `OT01-C001` | 所有实现必须留在一个 Python 应用、一个发布单元内；内部模块、adapter 和 worker loop 不得擅自升级为新服务。 | `ES-08`，全部 ES |
| `OT01-C002` | MKB Contract 必须 caller-neutral；`03-nano` 或其他内部 orchestrator 的 DTO、RPC 和注册协议只能在边界适配。 | `ES-01/08` |
| `OT01-C003` | MKB 必须持有完成 knowledge 处理所需的 durable internal truth，包括工作流流转状态、资产生命周期、retry、recovery 与 cleanup。它们是工具内部职责而非产品层；transport、queue、log 或 callback 均不得成为业务状态 SSOT，caller 也不得获得内部 runtime mutation 权。 | `ES-01/02/03/04/08` |
| `OT01-C004` | 持久化沿用 Turso 方向，但 domain 不得直接耦合 driver；并发、事务、进程模型和向量能力由 ES-04 以技术证据裁决，不上提 owner。 | `OD-10` → `ES-04` |
| `OT01-C005` | 领域 ID 全部 UUID 化；边界接受 UUIDv4/v7，MKB 内生领域 ID 使用 UUIDv7，Task 权威身份为 `(team_uuid, task_uuid)`。计数、revision 和底层 rowid 不得冒充领域身份。 | `OD-12`、`S01-T008..012` → 全部 ES |
| `OT01-C006` | Team 只能是最小接入投影；token 只有 valid/invalid 权限口径。实现不得增加 membership、team RBAC、session 或 billing 字段与流程。 | `ES-01/08` |
| `OT01-C007` | 本地/外部推理必须通过 capability adapter；任何 provider-specific 行为不得渗入 LS-RAG product contract。 | `ES-05/06/07` |
| `OT01-C008` | Execution 必须闭合文档清洗、结构化、LS-RAG 构建、结构化向量存储与上游检索/消费链路；不得用 generic workflow/agent/platform 抽象扩大产品责任或替换 Structurizer、Constructor、双通道、Traceback、Reranker 的业务语义。 | `ES-02/03/06/07` |
| `OT01-C009` | runtime dependency、config、schema、API、bootstrap 和 acceptance 必须保持零 legacy 依赖；legacy 只能作为有来源的 evidence/rationale。 | 全部 ES |
| `OT01-C010` | OT-03/ES-07 可以设计向量与 Retrieval Result 的上游消费接口，但不得生成 final answer、承载上游业务规则或新增 answer-specific Task、storage、prompt product、状态与验收面。 | `OT-03`、`ES-01/05/07/08` |

Execution Spec 可以自行选择满足这些约束的最小、可测试方案。表、字段、endpoint、算法、driver、token rotation、network exposure、rate limit 和部署参数均不得回流为 OT-01 owner 问题。`OT01-T001..T015` 只有 owner 主动 reopen 才能改变。

---

## 7. Revision History

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| `OT-01-v0.1` | `2026-08-10` | `pending consolidation` | 创建 Product Boundary 基础文件；原义归并 `OD-01..12`、S01-v1.5 的产品边界 Truth 与 `T-O-42`，建立 12 条 inherited Truth、8 条 hard non-goal 和 9 条 Execution constraint；未生成 QNA 或新增产品范围。 |
| `OT-01-v0.2` | `2026-08-10` | `owner-review-needed` | 完成 OT-01 第一轮问题准入；只保留 baseline `G-07` 的 final-answer product-boundary 决策，提供无扩张推荐 A、reasoning、选择后果与 non-goals；其余 open gate 均判为 executional 或已 deferred。 |
| `OT-01-v1.0` | `2026-08-10` | `frozen` | Owner 接受 Q1 推荐并进一步收紧边界：冻结文档清洗→结构化→LS-RAG结构化向量存储→上游检索/消费的knowledge工具闭环；final answer与全部上游业务OOS；MKB内部流转状态和生命周期明确为必须自持的非产品层真相。关闭QNA且不生成下一轮。 |
