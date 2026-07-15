# MyKnowledgeBase 重构 · Specification Index

> **文档角色**：本文件是本次 MKB 重构的 specification 总索引、设计编排器与真相冻结入口；它不是实现计划，也不是任一子系统的详细设计。
>
> **一句话用途**：先冻结系统范围、跨 Domain 架构真相和设计分母，再按依赖顺序逐一完成 16 个子系统 specification；每完成一项即回填本索引，全部闭合后冻结 truth layer，随后才进入重构规划与实施。
>
> **使用纪律**：本索引必须持续反映各详细 spec 的真实状态。详细 spec 与本索引冲突时，在 truth freeze 前以已接受的详细 spec 为候选真相并立即回填本文件；truth freeze 后，任何变更必须通过显式变更记录重新打开受影响条目。

---

> **项目**：`myknowledgebase`（MKB）
>
> **阶段**：`leaf-worker / LS-RAG re-foundation`
>
> **日期**：`2026-07-15`
>
> **作者**：`MKB owner + Codex`
>
> **文档性质**：`specification / index`
>
> **文档状态**：`active index`
>
> **当前站位**：站① · specification 基线与设计编排
>
> **上游事实源**：业主已确认的产品方向 + owner-originated `D01` + `legacy-family/` 行为证据
>
> **下游消费者**：16 份子系统 spec、跨 Domain truth、跨系统拓扑、验收矩阵、truth freeze、重构计划

## 状态词汇

### Index 状态

```text
active index
  → review-ready index
  → frozen truth index
  → superseded
```

- `active index`：仍在逐项设计和回填。
- `review-ready index`：16 个子系统均已接受，跨系统对账完成，等待最终冻结。
- `frozen truth index`：业主完成最终确认，成为重构计划的真相层入口。
- `superseded`：被新版本索引整体取代。

### 子系统状态

```text
pending → designing → owner-gate → accepted → frozen
```

- `pending`：尚未开始详细设计。
- `designing`：详细 spec 正在形成或评审。
- `owner-gate`：存在会改变系统边界或契约的待裁决事项。
- `accepted`：该子系统 spec 已接受，允许其他 spec 将其作为候选真相引用。
- `frozen`：仅在整个 truth layer 冻结时统一进入此状态。

---

## 0. TL;DR / Owner 意图与本阶段范围

- **一句话**：将 MKB 从包含平台职能的 Python 模块化单体，重新定义并设计为由 `03-nano/orchestrator-core` 调用、以任务为入口、以 LS-RAG 为核心、可使用本地 CUDA/vLLM 或外部推理服务的有状态 leaf-worker 单体应用。
- **为什么现在做**：现有 Python 版本完成了工作流骨架，但没有完成 LS-RAG 的关键业务语义；同时运行环境已从 MLX/macOS 叙事转向 NVIDIA CUDA 13.0，系统上游、部署拓扑和产品责任均已改变。
- **本阶段产物**：8 个核心 domain、16 个子系统的详细 specification，外加范围词汇表、系统拓扑和验收/真相冻结矩阵。
- **本阶段不产出**：实现任务拆解、工期、迭代排期、代码目录细节、具体代码和迁移执行计划。
- **最终出口**：所有 spec 接受并完成交叉对账后，将 `docs/baseline/` 冻结为 truth layer，再据此编写重构计划。

### 0.1 已确认的业主方向

| ID | 已确认方向 | 对 specification 的约束 |
|----|------------|--------------------------|
| `OD-01` | MKB 是 leaf-worker | 不建设用户平台、团队所有权、计费或 UI |
| `OD-02` | `03-nano/orchestrator-core` 是已知首个上游 | 对外用户接口和 user Durable Object 不属于 MKB；MKB Contract 不由 03-nano 当前私有协议决定 |
| `OD-03` | MKB 相对平台无状态，但业务内部有状态 | 必须设计 task、workflow、artifact、index、retry 等持久状态 |
| `OD-04` | 保留 `team_uuid` 与最小 Team Registry | 它是上游传入并预注册的审计、分区、追踪和检索过滤 ID，不代表本地 team ownership |
| `OD-05` | 使用简单内部 token | 不建设 session、复杂授权和 token 生命周期平台 |
| `OD-06` | 单体应用 | 一个 Python 项目、一个发布单元；内部仍保持清晰模块边界 |
| `OD-07` | 推理 adapter-first | 本地 vLLM/CUDA 与外部推理服务必须通过能力接口接入 |
| `OD-08` | 以 LS-RAG 为核心 | Structurizer、Constructor、双通道、Traceback 和 Reranker 是首要业务能力 |
| `OD-09` | 重新设计 Task CRUD 和 Workflow | 不继承旧平台 API 与 Worker 消息拓扑 |
| `OD-10` | 采用 Turso 方向 | 业务不得直接耦合驱动；并发、事务、进程模型和向量能力须先验证 |
| `OD-11` | 当前 Python 重构退役 | 已归档至 `legacy-python/`，不作为新实现依赖 |
| `OD-12` | 全域领域 ID UUID 化 | 边界接受 UUIDv4/v7，MKB 内生领域 ID 使用 UUIDv7；Task 使用 `(team_uuid, task_uuid)` 复合身份 |

### 0.2 Specification 设计纪律

1. **Contract-first**：先写边界、术语、不变量、状态机和输入输出，再讨论实现选择。
2. **Legacy 是证据，不是真相**：保留 LS-RAG 行为，剔除 Cloudflare 部署拓扑和平台化职责。
3. **零偷偷裁决**：改变产品范围、跨系统协议或不可逆数据模型的事项必须进入 §4 owner-gate。
4. **一项一 spec**：每个子系统只有一份权威详细 spec，禁止在多个文档中维护不同版本契约。
5. **每完成一项即回填**：更新本索引的状态、冻结结论、gate、依赖和修订历史。
6. **设计阶段不冒充实现阶段**：技术 spike 可以提供证据，但不得把原型行为写成已交付能力。
7. **冻结前完成横向对账**：ID、状态、错误、幂等、版本、删除和可观测字段必须跨 spec 一致。

### 0.3 单份 Domain Truth Spec 的固定目录

每份 `docs/baseline/domain-truth/` 文档必须使用以下九段式结构，标题顺序不得自行改变：

1. **Domain 介绍**：说明本域在 MKB 中的价值、scope fence 和完成定义；
2. **真相层**：用稳定 Truth ID 冻结 owner-gated Q&A、代码事实和已接受 verdict；
3. **总体方案陈述**：使用编号列表给出方案主轴；
4. **具体执行方案清单**：每个执行方向循环“编号与说明 → 真相层对应编号 → 执行台账 → 小结”；
5. **事实反例 + 风险台账**：代码证伪、禁止方向、风险、围栏和验收关联；
6. **测试与验收台账**：逐项写 HARD 不变量和所需证据，不用未来测试冒充已交付能力；
7. **Reference-anchor 台账**：提供可复验的 `file:line` 代码锚，并标注保留/改写/删除裁决；
8. **Domain verdict**：给出最终评价、未解决边界和对下游 spec 的约束；
9. **修订历史**：记录版本、日期、状态、owner 裁决和 reopen。

详细 spec 的域内状态仍使用 `pending → designing → owner-gate → accepted → frozen`；单域 `accepted` 只表示可作为候选真相被下游引用，不代表全系统 truth layer 已冻结。

### 0.4 单份详细 Spec 的最低覆盖要求

每份子系统 spec 至少必须包含：

1. 目标、责任与非目标；
2. 术语和领域对象；
3. legacy 证据及“保留 / 改写 / 删除”裁决；
4. 上游、下游和信任边界；
5. 输入、输出及版本化契约；
6. 状态机和生命周期；
7. 数据模型与稳定 ID；
8. 不变量、幂等和一致性；
9. 并发、背压、超时、重试和取消；
10. 错误分类与恢复语义；
11. 配置、模型和 capability；
12. 安全、审计和可观测性；
13. 容量边界与性能目标；
14. 验收场景和反例；
15. owner-gate 与最终裁决；
16. 对其他 spec 和本索引的回填项。

---

## 1. Domain 与子系统地图

本次设计包含 **8 个核心 domain、16 个详细子系统**。Domain 是业务责任边界，子系统是必须独立完成 specification 的设计单元；二者不等同于部署单元或 Python package。

| Domain | Domain 名称 | 子系统 | 核心结果 |
|--------|-------------|--------|----------|
| `D1` | 上游集成 | `S01` Skill-Worker Integration | MKB 如何以独立契约被认证、调用和轮询，以及未来如何适配 skill-worker |
| `D2` | 任务执行 | `S02` Task API；`S03` Workflow Engine | 上游任务如何进入，内部如何可靠执行 |
| `D3` | 知识资产 | `S04` Knowledge Lifecycle | source/document/version/artifact 的权威生命周期 |
| `D4` | 内容处理 | `S05` Intake & Cleaning | 输入如何变成可结构化的规范内容 |
| `D5` | LS-RAG 构建 | `S06` Structurizer；`S07` Constructor | 如何形成 layered block 和 original/summary 双通道 |
| `D6` | 向量资产 | `S08` Embedding & Vectorization；`S09` Vector Index | 向量如何生成、持久化、升级和检索 |
| `D7` | LS-RAG 检索 | `S10` Retrieval & Reranking | 召回、Traceback、膨胀、重排和结果契约 |
| `D8` | 模型能力 | `S11` Inference Runtime | 本地与外部模型如何以统一能力接口工作 |
| `F1` | 数据基础 | `S12` Turso Persistence；`S13` Artifact Storage | 事务状态、正文和派生产物如何可靠持久化 |
| `F2` | 治理基础 | `S14` Config/Prompt/Model Registry | 配置和模型产物如何版本化、追溯和复现 |
| `F3` | 运行基础 | `S15` Observability & Reliability | 如何观察、恢复、对账和运营 leaf-worker |
| `F4` | 信任基础 | `S16` Security & Trust Boundary | 简单内部信任下仍必须成立的安全边界 |

### 1.1 Specification 进度总表

> 状态更新规则：创建详细 spec 时改为 `designing`；存在未决边界时改为 `owner-gate`；评审和回填完成后改为 `accepted`；只能在最终 truth freeze 时统一改为 `frozen`。

| 顺序 | ID | 子系统 | 优先级 | 状态 | 详细 Spec | 关键依赖 | 回填摘要 |
|------|----|--------|--------|------|-----------|----------|----------|
| `01` | `S01` | Skill-Worker Integration | `P0` | `accepted` | `domain-truth/S01-skill-worker-integration.md` | `00, D01` | `S01-v1.2`：standalone Contract；Task/Audit 原子接收；Task/Execution/Process 权限边界；接收 S02 restart causal truth；polling；future adapter |
| `02` | `S02` | Task API & Lifecycle | `P0` | `accepted` | `domain-truth/S02-task-api.md` | `00, D01, S01` | `S02-v1.0`：六态/CAS；scatter collect-all/items/early publication/cancel；full retry generation；atomic rebuild 新 Task；`task_restarts` 与 global lineage；QNA Q1–Q9 全部冻结并关闭 |
| `03` | `S03` | Workflow Engine | `P0` | `accepted` | `domain-truth/S03-workflow-engine.md` | `D01-v1.1, S01-v1.2, S02-v1.0` | `S03-v1.0`：Q1–Q9 / `T-O-12..29` 全冻结；六平面 Contract、七表 relational SSOT、compiler、exact Execution/Process states、fencing、single/scatter、semantic recovery、cleanup eligibility |
| `04` | `S04` | Knowledge Lifecycle | `P0` | `owner-gate` | `qna-truth/S04.md` → `domain-truth/S04-knowledge-lifecycle.md` | `D01-v1.1, S01-v1.2, S02-v1.0, S03-v1.0` | `3+3+3 progressive` 已启动；完成 legacy + web evidence review；Round 1 Q1-Q3 聚焦 canonical identity graph、version creation、publication/withdrawal |
| `05` | `S05` | Intake & Cleaning | `P1` | `pending` | `domain-truth/S05-intake-cleaning.md` | `S02-S04, S13` | 待设计 |
| `06` | `S06` | LS-RAG Structurizer | `P0` | `pending` | `domain-truth/S06-lsrag-structurizer.md` | `S04, S11, S13-S14` | 待设计 |
| `07` | `S07` | LS-RAG Constructor | `P0` | `pending` | `domain-truth/S07-lsrag-constructor.md` | `S04, S06, S11, S13-S14` | 待设计 |
| `08` | `S08` | Embedding & Vectorization | `P0` | `pending` | `domain-truth/S08-embedding-vectorization.md` | `S07, S09, S11, S14` | 待设计 |
| `09` | `S09` | Vector Index Lifecycle | `P0` | `pending` | `domain-truth/S09-vector-index.md` | `S04, S12, S14` | 待设计 |
| `10` | `S10` | LS-RAG Retrieval & Reranking | `P0` | `pending` | `domain-truth/S10-lsrag-retrieval.md` | `S04, S07-S09, S11, S14` | 待设计 |
| `11` | `S11` | Inference Runtime & Adapters | `P0` | `pending` | `domain-truth/S11-inference-runtime.md` | `00, S14, S16` | 待设计 |
| `12` | `S12` | Turso Persistence | `P0` | `pending` | `domain-truth/S12-turso-persistence.md` | `S02-S04, S09` | 待设计 |
| `13` | `S13` | Artifact & Object Storage | `P1` | `pending` | `domain-truth/S13-artifact-storage.md` | `S04, S12` | 待设计 |
| `14` | `S14` | Config, Prompt & Model Registry | `P1` | `pending` | `domain-truth/S14-config-prompt-model-registry.md` | `00, S11` | 待设计 |
| `15` | `S15` | Observability & Reliability | `P0` | `pending` | `domain-truth/S15-observability-reliability.md` | `S01-S14` | 待设计 |
| `16` | `S16` | Security & Trust Boundary | `P0` | `pending` | `domain-truth/S16-security-trust-boundary.md` | `S01-S15` | 待设计 |

### 1.2 跨系统基线与跨 Domain Truth 文档

| ID | 文档 | 状态 | 用途 |
|----|------|------|------|
| `00` | `specs/00-scope-glossary.md` | `pending` | 冻结产品范围、术语、统一 ID 和通用状态词汇 |
| `D01` | `domain-truth/D01-task-execution-process-flow.md` | `accepted / S02-calibrated` | `D01-v1.1`：Owner 主动提出 Task/Execution/Process；三表运行状态不变；接收第五张 `task_restarts` 因果表 |
| `17` | `specs/17-system-topology.md` | `pending` | 汇总 16 个子系统的运行拓扑、进程、资源和调用关系 |
| `18` | `specs/18-acceptance-truth-freeze.md` | `pending` | 汇总不变量、验收矩阵、owner-gate closure 和冻结签署 |

### 1.3 Owner 方向与子系统覆盖

| Owner 方向 | 命中子系统 | 覆盖说明 |
|------------|------------|----------|
| Turso 替换原 SQLite 方向 | `S09, S12` | 分离关系持久化和向量索引；先验证再冻结驱动与部署方式 |
| 本地 vLLM + 外部服务 | `S06-S08, S10-S11, S14` | 按 structured generation、summary、embedding、rerank 四类能力设计 adapter |
| leaf-worker 与 skill-worker 注册准备 | `S01-S03, S15-S16` | 首版 standalone；定义能力、任务、健康、token、状态和 polling；未来以 adapter 接入 skill-worker |
| 重做 CRUD 与 workflow | `S02-S05, S12-S13` | 从 task intent 与内部状态机重建，不沿用平台 API |
| Task / Execution / Process 三层切分 | `D01, S01-S05, S08-S09, S12, S15` | Task 只做外部 ACK/CRUD/aggregate；Execution 是 durable run；Process 是 RAG-specific 工序；single/scatter 共用同一入口 |
| 从第一天按 LS-RAG 执行 | `S04, S06-S10, S14-S15` | layered schema、双通道、坐标回溯和质量指标贯穿知识全生命周期 |
| 单体应用、废弃 packages 注册 | `17` + 全部 | 只影响组织与部署，不取消领域和 adapter 边界 |

---

## 2. Legacy 证据基线与迁移分母

### 2.1 当前证据源

- `legacy-family/`：原 TypeScript/Cloudflare 实现，是 LS-RAG 行为考古与迁移对照源。
- `legacy-python/`：已退役 Python 重构，仅供失败经验、基础设施思想和测试证据参考，不作为新运行时依赖。
- 业主已确认方向：本索引 §0.1，是产品范围和责任边界的上游输入。

### 2.2 冻结设计分母

| 分母 | 当前值 | 含义 |
|------|--------|------|
| 核心 domain | `8` | 新系统的业务责任分组，不对应部署单元 |
| 详细子系统 spec | `16` | 必须逐项设计、接受并回填的最小完整集合 |
| 跨系统基线 spec | `3` | scope/glossary、system topology、acceptance/truth freeze |
| 跨 Domain architecture truth | `1` | `D01`：owner-originated Task / Execution / Process Flow |
| Legacy TypeScript 项目 | `10` | 证据源数量，不代表新子系统数量 |
| 新 Python 发布单元 | `1` | leaf-worker 单体应用 |
| 已知首个上游调用单位 | `1` | `03-nano/orchestrator-core`；其他内部 orchestrator 必须遵守同一 MKB Contract |
| 平台租户所有权 domain | `0` | `team_uuid` 只作为上游审计/分区/过滤 ID，并通过最小 Team Registry 预注册 |
| UI 子系统 | `0` | MKB 不提供 UI |

这些分母在本索引处于 `active index` 时可以通过显式修订变更；进入 `frozen truth index` 后必须通过 reopen 记录修改。

### 2.3 Legacy 项目到新子系统映射

| Legacy 项目 | 新归宿 | 处理原则 |
|-------------|--------|----------|
| `smind-admin` | `S01, S02, S04, S05` | 保留 ingestion/资源生命周期证据；删除 auth/user/team ownership/平台 management |
| `smind-clean-dispatcher` | `S03, S05` | 将 queue/callback/restart 思想收敛为内部 workflow |
| `smind-rag-dispatcher` | `S03, S06-S09` | 保留阶段、失败和 purge 语义；删除跨 Worker 部署拓扑 |
| `smind-skill-clean-universal` | `S05, S11, S13` | 按首版输入范围选择迁移，浏览器/PDF 不自动纳入 |
| `smind-skill-clean-dedicated-apis` | `S05` | 默认候选扩展，不自动进入核心交付范围 |
| `smind-skill-rag-structurizer` | `S06, S11, S14` | LS-RAG 核心证据源 |
| `smind-skill-rag-constructor` | `S07, S11, S14` | LS-RAG 双通道、meta fusion 和 recorder 证据源 |
| `smind-skill-rag-vectorizer` | `S03, S08, S09, S12, S15` | 拆开队列、embedding、index、持久化和运行治理职责 |
| `smind-contexter` | `S10, S11` | 只迁 retrieval/traceback/context expansion/rerank；用户会话和对话编排上移 |
| `smind-console` | 无 | 整体退役，不建设替代 UI |

### 2.4 贯穿主题

- **职责而非部署单元**：新子系统边界不能重新复制 10 个 Worker 或 23 个 Python package。
- **业务状态内聚**：平台无状态不代表内部无状态，任务和知识资产状态必须由 MKB 负责。
- **模型与业务解耦**：LS-RAG 契约不能依赖 vLLM、某个云厂商或某个具体模型。
- **LS-RAG 双层语义**：summary 是语义索引，original 是最终 payload；两者通过稳定坐标关联。
- **外部 request intent 与内部 runtime 分离**：上游只创建/操作 Task；MKB 独占 Execution/Process、workflow、claim/retry 与结果证明。
- **单体不等于无边界**：只有一个发布单元，但领域、adapter、repository 和执行 lane 仍需明确。

---

## 3. 逐子系统登记

### 3.1 `S01` Skill-Worker Integration

- **状态**：`accepted / D01+S02-calibrated`；域内 truth = `S01-v1.2`；全系统尚未 frozen。
- **权威 Spec**：`docs/baseline/domain-truth/S01-skill-worker-integration.md`。
- **冻结范围**：MKB 先作为 standalone leaf-worker；MKB Contract 是权威接入协议；03-nano 或其他上游自行适配。
- **冻结身份**：边界 UUIDv4/v7、MKB 内生 UUIDv7；Task 权威键为 `(team_uuid, task_uuid)`；task/trace 由上游提供；Execution/Process 仅由 MKB 创建；Attempt identity 已废止。
- **冻结接入**：最小 Team Registry；只有 registered active team 可创建任务；Task + 独立 immutable Audit 1:1 原子落库。
- **冻结接入语义**：canonical 字段为 `request_intent`；旧 `task_type` 只允许 adapter 预翻译；Task/Workflow lifecycle 分离；single/scatter 均从一个 Task 进入。
- **冻结交付**：首版 polling，无 webhook/callback；Task 聚合 current root Execution；简单有效 token 可使用全部 Team/Task 功能，不做 team RBAC。
- **明确不做**：首版 skill-worker 注册/心跳/manifest、用户身份、membership、计费、UI 和 03-nano 私有 RPC 兼容。
- **下游约束**：`S02/S03/S04/S12/S15/S16/17` 必须继承 S01 与 D01 Truth ID；偏离必须同时 reopen 受影响真相。

### 3.2 `S02` Task API & Lifecycle

- **状态**：`accepted`；域内 truth = `S02-v1.0`；QNA Q1–Q9 全部冻结，Round 4 已由 owner 关闭；全系统尚未 frozen。
- **权威 Spec**：`docs/baseline/domain-truth/S02-task-api.md`；问答证据保留于 `docs/baseline/qna-truth/S02.md v1.3`。
- **范围**：Task create/get/list/result/cancel/retry/delete、幂等、aggregate 状态机、scatter item projection、restart causation/global query、优先级、deadline、错误和 retention。
- **已冻结**：Task 六态与 lifecycle CAS；scatter collect-all、bounded aggregate + paginated items + canonical Document、proof-gated early publication、forward-stop/no-rollback cancel；full retry 同 Task 新 generation；atomic restart 创建新 `document.rebuild` Task；独立 `task_restarts` 保存 full/atomic causal/admission truth且状态只 join Task；team-scoped global restart/lineage。
- **Legacy 核查**：已复验 API 发起 → Dedicated Cleaner 散射 → SMCP callback → Clean Dispatcher diff/register → child 并行 RAG 投递 → relation child completion，以及原子 list/artifact/timeline/restart；MKB 明确修复 identity UPSERT、非事务 wakeup、无 parent fan-in 与 route 散射债务。
- **Owner-gate closure**：Q1–Q9 与 `T-O-1..11` 全部获得 owner 确认；S02 不再增加 QNA，无域内开放 gate。
- **关键不变量**：上游不能创建或写 Execution/Process；相同 `task_uuid + payload digest` 必须幂等收敛；Task 不承载 RAG 工序状态；原子 CRUD 不得泄漏内部 stage/process identity。
- **已回填影响**：D01-v1.1/S01-v1.2 已明确四张核心 Task/运行表继续成立，并增加第五张 `task_restarts` 因果表；S12 必须交付 exact DDL/transaction，不能把因果降级为 tasks JSON。
- **完成回填**：已冻结 Task Contract v1、状态图、HTTP surface、错误码、强制验收与 legacy reference-anchor。

### 3.3 `S03` Workflow Engine

- **状态**：`accepted / S03-v1.0`；QNA `docs/baseline/qna-truth/S03.md v1.0` 已冻结关闭，正式权威文档为 `docs/baseline/domain-truth/S03-workflow-engine.md`。
- **定位**：S03 是 MKB 单体内部唯一 durable、declarative、future-agent-ready 的 LS-RAG Workflow Engine。v1 采用内部注册制：关系型 schema 是 Workflow SSOT，canonical JSON 是只读派生表示；对外只有 list/get，无 create/update/delete，也不实现 agent 直接定义 Workflow。
- **范围**：六平面 Workflow Contract；internal registry/revision；normalized step/route/binding/control/guard schema；deterministic compiler 与 compiled JSON/digest；capability/port registry 与本地 Process runtime contract；Execution binding/state/phase/tree/generation；Process dependency/materialization、I/O/outcome guard；durable scheduling；claim/lease/fencing；retry/backoff/timeout；priority/deadline；cancel/purge/case/scatter control；Workflow semantic recovery invariant/transition；Process projection cleanup eligibility。
- **继承的冻结真相**：Task/Execution/Process 三层身份及三张核心运行表；single=root Execution、scatter=root controller + 0..N child Executions；状态自下而上、control intent 自上而下；Process/Execution 未提交 proof 前 Task 不成功；queue 不是 SSOT且只能在 durable state 提交后 wake-up；full retry 新 root generation、automatic Process retry 不换 Process；collect-all、child proof-gated early publication 与 forward-stop/no-rollback cancel。
- **明确不负责**：Task HTTP/六态/CAS/restart ledger（S02）；Source/Document/Version/manifest 资源真相（S04-S05）；具体 LS-RAG schema/model/prompt 内容与 publication proof 算法（S06-S11/S14）；Turso exact DDL/driver 与 queue 选型（S12）；Artifact backend（S13）；完整 event/log/trace 与 retention 数值（S15）。
- **Round 1 冻结结论**：`T-O-12` 六平面 Workflow Contract；`T-O-13` agent authoring/publish 为 v1 out-of-scope；`T-O-14` 内部注册且外部只读；`T-O-15` 关系型 schema 是 durable SSOT；`T-O-16` compiled JSON 是可重建派生表示。
- **Round 2 冻结结论**：`T-O-17` 七张 Workflow definition/control truth tables；`T-O-18` core truth 禁止 opaque JSON；`T-O-19` typed/guarded/acyclic route graph 与 S03 cutoff；`T-O-20` internal register/compile/immutable Execution binding；`T-O-21` Engine-interpreted plan + ProcessCommand/ProcessOutcome leaf contract。
- **Round 3 冻结结论**：`T-O-22..24` 冻结 Process `ready/claimed/running/retry_wait/succeeded/failed/cancelling/cancelled`、claim/lease/fencing 与 delivery/recovery/retry 分账；`T-O-25..27` 冻结 Execution `created/ready/running/waiting/succeeded/failed/cancelling/cancelled`、独立 RAG phase、single/scatter collect-all/cancel/terminal summary；`T-O-28..29` 冻结 semantic recovery 与 Process cleanup eligibility/cutoff。
- **交叉审计**：S03 QNA 已逐项对照 D01-v1.1/S01-v1.2/S02-v1.0，结论 `PASS / NO REOPEN REQUIRED`；`ready`、`waiting+reason`、focus pointer 和 projection cleanup 是上游授权范围内的 exact specialization。
- **关键不变量**：对外没有 Workflow CUD；Task caller/工具不得借 payload 注入 graph；compiled JSON 不得反向成为 truth；registry/revision 变化不得热改已绑定 Execution；Process 只消费本工序 Command/返回 Outcome，route 只由 Engine 推进；不得重新引入 Attempt、clean/rag process 分表、跨 Worker callback SSOT、Task current_process 指针或 queue-send-as-success。
- **完成回填**：冻结 Workflow relational schema/registration/compiler/read contract、runtime binding、Execution/Process 状态机、process capability/port/guard、materialization、claim/fencing、retry/cancel、single/scatter fan-out/fan-in、semantic recovery、Process cleanup eligibility 和强制验收矩阵。

### 3.4 `S04` Knowledge Lifecycle

- **状态**：`owner-gate / 3+3+3 progressive Round 1 Q1-Q3 awaiting owner`；当前权威问答为 `docs/baseline/qna-truth/S04.md v0.1`。
- **定位**：S04 是 MKB 长期知识资产的 canonical identity、immutable version、provenance、publication 与 semantic invalidation 真相层；它不承载 Task/Execution/Process，也不把 legacy `smind_files` 直接本地化。
- **范围**：Source 与 external namespace；Source observation/manifest；Document 稳定身份；immutable DocumentVersion 与 digests/lineage；published pointer；deactivate/delete/tombstone；Artifact/LSRagBlock/VectorRecord 的 version-scoped lineage 与 invalidation contract。
- **职责 cutoff**：Artifact bytes/locator/GC 归 S13；Block/Vector exact schema 归 S06-S09；Turso DDL/outbox/physical cleanup 归 S12；S04 只冻结这些派生层必须引用哪个 Version、何时有效以及何时必须失效。
- **Legacy 审查结论**：保留 team scope、`atomic_id`、content/meta hash 分账、diff route 与父子 provenance；重写 file/relation mutable current row、裸 `(team_uuid, atomic_id)`、日志反扫 Artifact、Vector process兼任资产以及 purge/reset/delete 混义。
- **Round 1 foundational gates**：Q1 冻结 canonical identity graph；Q2 冻结 source-scoped external key 与 version creation rule；Q3 冻结 latest/published pointer及 deactivate/delete 的 logical-first、physical-convergence 语义。
- **后续方向**：Round 2 只能由已冻结 S04 `T-O` 生成 exact relational schema、状态/pointer 与 manifest/diff mutation；Round 3 再处理 recovery、retention、purge/reindex、迁移与验收。
- **关键不变量**：DocumentVersion 不静默覆盖；Task cancel 不撤销已发布知识；scatter absence 只有在 complete authoritative manifest 下才可推导失活；查询不能等待物理 Vector/Artifact 删除才停止暴露。
- **完成回填**：冻结 canonical resource graph、stable key/version fingerprint、publication/withdrawal state machine、source manifest、derived lineage/invalidation 与强制验收矩阵。

### 3.5 `S05` Intake & Cleaning

- **范围**：text、object/file、API payload、URL 或其他 source adapter 到规范内容的转换。
- **必须回答**：首版输入类型；MIME/encoding/size；browser、PDF、Vision、专用 API 和 scatter 是否纳入。
- **关键不变量**：规范化不得丢失来源 provenance；原始输入与 clean 产物必须可追溯。
- **完成回填**：冻结 Intake Contract v1、首版 action 范围和 clean artifact schema。

### 3.6 `S06` LS-RAG Structurizer

- **范围**：layered schema、context metadata、knowledge tree、block、granularity、original/summary 结构和 schema validation。
- **必须回答**：新 LS-RAG Schema v1 与 legacy schema 的关系；全文层和子块层；修复与 fail-loud 边界。
- **关键不变量**：`layered_content` 非空；block 坐标稳定；结构化不得静默丢失原始内容。
- **完成回填**：冻结 Structured Document Schema v1、坐标模型和验证规则。

### 3.7 `S07` LS-RAG Constructor

- **范围**：meta fusion、summary、`content_full`、original/summary 双通道、filter metadata 和幂等构造。
- **必须回答**：summary 质量门、空 summary、metadata 优先级、同一版本重建和旧产物失效。
- **关键不变量**：original 与 summary 共享稳定逻辑坐标；每个 summary 必须能定位 original。
- **完成回填**：冻结 Construction Unit Schema、双通道规则和 lineage。

### 3.8 `S08` Embedding & Vectorization

- **范围**：document/query embedding、model identity/revision/dimension、batch、normalization、truncation、GPU queue 和 rebuild。
- **必须回答**：本地/外部路由、批处理、部分失败、model upgrade 和 fingerprint。
- **关键不变量**：写入和查询必须处于相同 embedding space；不同模型/维度不得混算。
- **完成回填**：冻结 Embedder Contract、Vectorization Record 和升级策略。

### 3.9 `S09` Vector Index Lifecycle

- **范围**：index namespace、upsert/delete/search/rebuild、metadata filter、tombstone、backup、capacity 和 Turso/ANN adapter。
- **必须回答**：Turso exact vector 是否满足首版；何时需要 ANN；关系事务与 index 副作用如何对账。
- **关键不变量**：索引记录必须引用有效知识版本；查询必须声明 model/dimension/metric。
- **完成回填**：冻结 VectorIndex 接口、索引 schema、容量门槛和一致性协议。

### 3.10 `S10` LS-RAG Retrieval & Reranking

- **范围**：query embedding、filter、topK、hydration、summary traceback、全文膨胀、dedupe、rerank、context budget 和结果契约。
- **必须回答**：阈值、片段/全文策略、reranker 失败、过滤维度和是否包含 answer generation。
- **关键不变量**：summary 只作为索引；summary 命中时保留 `hit_content`，但 `payload_content` 必须回溯 original。
- **完成回填**：冻结 Retrieval Result v1、Traceback 算法、rerank 策略和 golden scenarios。

### 3.11 `S11` Inference Runtime & Adapters

- **范围**：StructuredGenerator、Summarizer、Embedder、Reranker，以及 vLLM/OpenAI-compatible/外部 provider adapter。
- **必须回答**：进程边界、健康、batch、timeout、retry、circuit breaker、fallback 和 capability declaration。
- **关键不变量**：产物必须记录实际模型、revision 和参数；fallback 不能冒充原模型结果。
- **完成回填**：冻结四类能力接口、provider routing 和故障分类。

### 3.12 `S12` Turso Persistence

- **范围**：数据库模式、transaction、repository、migration、并发、进程模型、backup/restore 和故障恢复。
- **必须回答**：具体 Turso engine/driver/version；单进程或多进程；claim 原子性；不支持 SQL 特性的规避。
- **关键不变量**：domain 不直接依赖 Turso driver；所有状态转移拥有明确事务边界。
- **完成回填**：冻结 persistence ports、transaction matrix、部署约束和技术 spike 结论。

### 3.13 `S13` Artifact & Object Storage

- **范围**：raw/cleaned/structured/constructed/export artifact、object key、hash、atomic write、cleanup、backend adapter 和 orphan detection。
- **必须回答**：首版本地文件系统还是对象服务；不可变产物；加密、压缩和 retention。
- **关键不变量**：artifact 默认不可变；数据库只保存引用和必要索引，不承载无界正文。
- **完成回填**：冻结 Artifact Contract、路径规则和跨 substrate reconciliation。

### 3.14 `S14` Config, Prompt & Model Registry

- **范围**：workflow version、prompt digest、schema version、model alias/revision、threshold、batch、feature flag 和受控 override。
- **必须回答**：配置来源、热更新、一致快照、task override 白名单和产物复现。
- **关键不变量**：每个模型产物可追溯到模型、prompt、schema 和参数版本。
- **完成回填**：冻结配置优先级、版本标识和 provenance schema。

### 3.15 `S15` Observability & Reliability

- **范围**：log、trace、metric、task/workflow event、queue/GPU/index 指标、dead-letter、reconciliation、health 和 operator API。
- **必须回答**：事件保存位置、基数控制、告警、ready/live、trace 传播和数据修复权限。
- **关键不变量**：`team_uuid/task_uuid/trace_uuid` 贯穿事件；失败不能只存在于日志字符串。
- **完成回填**：冻结事件 envelope、指标目录、健康语义和运维动作。

### 3.16 `S16` Security & Trust Boundary

- **范围**：内部 token、rotation、网络边界、request limit、replay、SSRF、路径安全、secret、日志脱敏和模型供应链。
- **必须回答**：token 由谁签发/轮换；哪些 endpoint 内部可见；URL fetch 是否允许；调试能力如何隔离。
- **关键不变量**：简单认证不等于无安全边界；`team_uuid` 不得被解释为授权凭证。
- **完成回填**：冻结 threat model、信任边界、最小安全基线和 secret 生命周期。

---

## 4. Owner-Gate Registry

> 本表只登记尚未冻结的关键裁决。详细 spec 中发现新 gate 时，必须先在此分配 ID；裁决后记录结论并更新受影响 spec。

| Gate ID | 决策点 | 影响范围 | 候选方向 | 状态 | 裁决/落点 |
|---------|--------|----------|----------|------|-----------|
| `G-01` | Skill-worker 发现与注册方式 | `S01, 17` | 主动注册 / 上游静态配置 / 混合 | `deferred` | `S01-v1.2`：首版 standalone，不注册；未来只通过防腐 adapter reopen |
| `G-02` | Task 结果交付方式 | `S01-S03, S15-S16` | 上游轮询 / callback / 双支持 | `closed` | `S01-v1.2`：首版 polling；无 webhook/callback；内部 Execution/Process 不扩大外部写面 |
| `G-03` | Workflow Program 语义宪法 | `S03-S09, S12-S15` | topology 清单 / 多平面声明式 RAG 程序 / 任意代码自动化 | `closed` | `T-O-12`：采用六平面端到端 Contract；Source 声明规则，Engine 注入 runtime facts；topology 只是 Control 子平面 |
| `G-04` | 首版 Intake 范围 | `S04-S05, S13` | text/object only / URL / PDF/browser | `open` | 待 `S05` |
| `G-05` | parent-child/scatter 首版范围 | `D01, S03-S07` | 首版支持 / schema 预留后延 | `closed` | `D01-v1.1`：scatter 是首版一等能力；Task → root controller → 0..N child Executions；资源 manifest 细节待 S04-S05 |
| `G-06` | LS-RAG Schema 与 legacy 兼容策略 | `S06-S10` | 新 v1 / legacy v2 兼容 / 双读迁移 | `open` | 待 `S06` |
| `G-07` | Retrieval 是否承担 answer generation | `S01-S02, S10-S11` | 只返回 context / 可选生成任务 | `open` | 待 `S10` |
| `G-08` | Turso 运行和进程模型 | `S03, S09, S12, 17` | 单进程 embedded / 多进程 / remote-sync | `open` | 待 `S12` spike |
| `G-09` | 首版向量索引 | `S08-S10, S12` | Turso exact / 独立 ANN / 分阶段 | `open` | 待 `S09` benchmark |
| `G-10` | 模型 fallback 语义 | `S06-S08, S10-S11, S14` | 禁止自动 fallback / 受控 fallback | `open` | 待 `S11` |
| `G-11` | Artifact 首版 backend | `S05-S07, S12-S13, 17` | 本地 filesystem / S3-compatible | `open` | 待 `S13` |
| `G-12` | Agent authoring 与 Workflow publication 治理 | `S03, S14-S16` | v1 实现 / future adapter-ready / 永不支持 | `deferred` | `T-O-13`：第一次重构 out-of-scope；只保留 future-agent-ready schema/interface，未来接入必须 reopen |
| `G-13` | Workflow Registry、SSOT 与 compiled representation | `S03, S12-S14` | 外部 CRUD + JSON truth / 内部注册 + relational truth + compiled JSON / code-only hardcode | `closed` | `T-O-14..16`：内部注册；外部仅 list/get；normalized DB schema 是 SSOT；compiled JSON 是可重建派生表示 |
| `G-14` | Workflow normalized table 与 JSON 边界 | `S03, S12, S14` | 单表 JSON / 七表职责拆分 / 更细粒度规范化 | `closed` | `T-O-17..18`：冻结七表职责、跨 revision 围栏、typed extension 与 compiled/diagnostic JSON 非权威边界 |
| `G-15` | Workflow route/control graph 语义 | `S03, S05-S09, S12` | rank 线性 / typed acyclic graph / 支持业务 loop | `closed` | `T-O-19`：typed/guarded/acyclic RAG graph；branch/fan-out/fan-in；retry/cancel cycles 归 Engine；S03 cutoff 已冻结 |
| `G-16` | Compiled plan、Execution binding 与 Process runtime boundary | `S03, S05-S09, S12-S15` | whole JSON 直交 Process / Engine interpret + command/outcome / direct local function coupling | `closed` | `T-O-20..21`：internal register/compile；Execution exact binding；eligible Process materialization；ProcessCommand/Outcome leaf contract |
| `G-17` | Process state、claim/lease/fencing/retry | `S03, S12, S15` | pending-heavy / eligibility-ready + fenced lease / queue-delivery-driven | `closed` | `T-O-22..24 / S03-v1.0`：exact八态、atomic claim/current fence、delivery/recovery/retry三账、same-process retry/max-retries |
| `G-18` | Execution status、RAG phase 与 scatter/cancel convergence | `S02-S09, S12, S15` | 混合大 enum / control status + separate RAG phase / Process 直写 Task | `closed` | `T-O-25..27 / S03-v1.0`：Execution exact八态、typed waiting、独立phase、manifest collect-all、cancel convergence、terminal summary |
| `G-19` | Workflow semantic recovery 与 Process cleanup eligibility | `S03, S12, S15` | 无恢复机制 / S03 定义语义不变量与幂等 repair、S12 执行扫描/outbox/cleanup / 独立通用 reconciler | `closed` | `T-O-28..29 / S03-v1.0`：最小repair matrix、无独立Reconciler强制、summary-before-cleanup、S12/S15 cutoff、无S03 operator写面 |
| `G-20` | Canonical knowledge identity graph | `S04-S10, S12-S13` | mutable file/relation / Source+manifest+Document+immutable Version / content blob即Document | `owner-gate` | `S04 Round 1 / Q1`：冻结 Source、Document、Version、membership 与 derived asset 的身份所有权 |
| `G-21` | DocumentVersion creation 与 external identity scope | `S04-S09, S12-S15` | 裸atomic_id+原位覆盖 / source-scoped key+content/context/filter变化追加Version / 每次执行都建Version | `owner-gate` | `S04 Round 1 / Q2`：冻结 version fingerprint、no-change、metadata update、rebuild/reindex边界 |
| `G-22` | Publication、deactivate 与 delete 语义 | `S02-S04, S09-S10, S12-S16` | latest即current / proof-gated published pointer+logical fence+physical convergence / 以vector存在判断可见 | `owner-gate` | `S04 Round 1 / Q3`：冻结 published linearization、tombstone 与 authoritative absence fence |

---

## 5. Specification 工作目标

- **一句话目标**：形成一套无平台职能泄漏、无 legacy 部署拓扑复制、契约完整且可验收的 MKB leaf-worker truth layer。
- **完成定义**：
  1. `00`、`S01-S16`、`17`、`18` 全部达到 `accepted`；
  2. §4 所有 gate 已裁决或被明确移出本次范围；
  3. 所有跨系统 ID、状态、错误、版本、删除和审计语义完成对账；
  4. LS-RAG golden scenarios 完整覆盖 summary traceback；
  5. Turso、向量索引和本地模型的关键假设有可复现 spike/benchmark 证据；
  6. 业主批准 truth freeze；
  7. 本索引与全部详细 spec 状态统一改为 `frozen`。

---

## 6. Out of Scope

| ID | 排除项 | 原因 | 未来承接 |
|----|--------|------|----------|
| `O-01` | 用户注册、登录、session | 属于上游平台 | `03-nano` |
| `O-02` | team 成员、owner、role、permission、plan、billing | MKB 只维护最小 Team Registry 投影；不拥有 team 平台 | `03-nano` / 上游平台 |
| `O-03` | 计费、套餐、provider 成本归属 | leaf-worker 不拥有商业平台职能 | 上游平台 |
| `O-04` | Web/React UI | MKB 无 UI | 上游产品层 |
| `O-05` | 用户 Durable Object、聊天历史、WebSocket | 属于 user/orchestrator 状态 | `03-nano` |
| `O-06` | 通用多租户配置系统 | 不再存在 team-owned 配置 | 上游或单机配置 |
| `O-07` | 任意动态 workflow designer | 会重新引入平台控制面 | 明确需求后另立项 |
| `O-08` | 实施排期和代码任务拆分 | truth freeze 前禁止进入执行规划 | 冻结后的重构计划 |

---

## 7. 已完成 / 勿重做

| 已确定事项 | 来源 | 后续关系 |
|------------|------|----------|
| MKB leaf-worker 产品定位 | 业主裁决 | 沿用，不再讨论平台化回退 |
| `03-nano/orchestrator-core` 为上游 | 业主裁决 | 所有接口设计以此为调用方 |
| `team_uuid` 为审计/分区/追踪 ID，并需本地预注册 | 业主裁决 + `S01-v1.2` | 允许最小 Team Registry；不得重新引入 membership/ownership/billing |
| Task/Audit 接入基线 | `S01-v1.2` | `(team_uuid, task_uuid)`、root trace、`request_intent`、immutable Audit、原子创建、polling 必须被下游继承 |
| Task/Execution/Process Flow | `D01-v1.1 + S01-v1.2` | Owner-originated 三层切分；Attempt 已废止；single/scatter、retry、状态归约与三表运行架构不得重问 |
| Task API / Aggregate Lifecycle | `S02-v1.0` | 六态/CAS、collect-all/items、early publication、cancel、generation、atomic rebuild、restart causal truth 与 lineage 不得重问 |
| 无 UI、无复杂平台鉴权 | 业主裁决 | `S16` 只设计内部最小安全边界 |
| Python 单体、废弃过细 packages | 业主裁决 | 内部模块化，但不建立多个 distribution |
| CUDA/vLLM + 外部服务 adapter | 业主裁决 | `S11` 设计能力接口，不再回到 MLX 叙事 |
| 当前 Python 实现已归档 | 当前仓库 | 只作历史证据，不继续增量开发 |
| TypeScript legacy 已保留 | `legacy-family/` | 用于行为考古，禁止成为运行依赖 |

---

## 8. 后续使用方式

### 8.1 逐项设计流程

每次只推进一个主要子系统：

```text
选择本索引中的 pending 项
  → 状态改为 designing
  → 读取对应 legacy 证据
  → 编写详细 spec
  → 登记 owner-gate
  → 完成评审与裁决
  → spec 状态改为 accepted
  → 回填本索引
  → 推进下一项
```

### 8.2 每次接受详细 Spec 后必须回填

1. §1.1 的状态和回填摘要；
2. §3 对应子系统的最终冻结结论；
3. §4 新增或已关闭的 owner-gate；
4. §2.2 如有变化的设计分母；
5. §6 新增或移除的范围；
6. §9 交叉引用；
7. 附录修订历史。

### 8.3 Truth Freeze 流程

当 20 份详细/跨系统/cross-domain truth 文档全部达到 `accepted`：

1. 生成 `18-acceptance-truth-freeze.md` 的最终矩阵；
2. 对账所有 contract、ID、状态机、error、event 和 version；
3. 关闭或显式延期所有 owner-gate；
4. 将本索引置为 `review-ready index`；
5. 由业主完成最终审阅；
6. 将本索引和全部 spec 统一标记为 `frozen`；
7. 记录 truth version/tag；
8. 从冻结 truth layer 生成重构计划，禁止用实施需要反向偷偷修改 spec。

如果实施阶段发现 specification 错误，必须显式 reopen：

```text
implementation finding
  → change request
  → 标记受影响 spec
  → owner 裁决
  → 更新 truth version
  → 重新冻结
```

---

## 9. 交叉引用

- Legacy TypeScript：`legacy-family/`
- 退役 Python 实现：`legacy-python/`
- Specification 目录：`docs/baseline/specs/`
- Domain Truth 目录：`docs/baseline/domain-truth/`
- Task/Execution/Process Flow：`docs/baseline/domain-truth/D01-task-execution-process-flow.md`
- 系统拓扑：`docs/baseline/specs/17-system-topology.md`（待创建）
- Truth freeze：`docs/baseline/specs/18-acceptance-truth-freeze.md`（待创建）

---

## 附录 A · Truth Freeze Checklist

| 检查项 | 状态 | 证据/备注 |
|--------|------|-----------|
| `00` Scope & Glossary accepted | `pending` | |
| `D01` Task/Execution/Process Flow accepted | `accepted / S02-calibrated` | Owner-originated；D01-v1.1/S01-v1.2 已接收 S02 restart truth |
| `S01-S16` 全部 accepted | `pending` | |
| `17` System Topology accepted | `pending` | |
| `18` Acceptance Matrix accepted | `pending` | |
| Owner-gate 全部 closed/deferred | `pending` | |
| 跨 spec ID 对账完成 | `pending` | |
| 跨 spec 状态机对账完成 | `pending` | |
| 错误、事件、版本语义对账完成 | `pending` | |
| LS-RAG golden scenarios 冻结 | `pending` | |
| Turso/process spike 证据完成 | `pending` | |
| Vector capacity benchmark 完成 | `pending` | |
| CUDA/vLLM adapter spike 完成 | `pending` | |
| Out-of-scope 与上游责任确认 | `pending` | |
| 业主 truth freeze 批准 | `pending` | |

## 附录 B · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-07-14` | `MKB owner + Codex` | 建立 8 domain、16 子系统、3 跨系统 baseline 的 specification 索引与冻结流程 |
| `v0.2` | `2026-07-15` | `MKB owner + Codex` | 固化九段式 Domain Truth 目录；接受并回填 S01；关闭 polling gate、延期 skill registration；校准最小 Team Registry 与 UUID 口径 |
| `v0.3` | `2026-07-15` | `MKB owner + Codex` | 登记 owner-originated D01；将 S01 回填为 v1.1；废止 Attempt/task_type 双义，校准 S02/S03 责任与 single/scatter gate。 |
| `v0.4` | `2026-07-15` | `MKB owner + Codex` | 删除并重建 S02 Q&A；登记 3+3 progressive Round 1 owner-gate，S02 scope 收敛为 Task API/aggregate lifecycle。 |
| `v0.5` | `2026-07-15` | `MKB owner + Codex` | 登记 S02 Round 1 Q1–Q3 全部冻结与 `T-O-1..4`；复验 legacy scatter 发起、注册、并行投递、完成、原子查询/重启及实现债务；进入 Round 2 Q4–Q5。 |
| `v0.6` | `2026-07-15` | `MKB owner + Codex` | 冻结 S02 Q4–Q5 与 `T-O-5..7`；新增独立 `task_restarts` durable causal/admission truth及 D01/S01 待回填影响；QNA 调整为 3+2+4，进入 Round 3 Q6–Q9。 |
| `v0.7` | `2026-07-15` | `MKB owner + Codex` | Owner 接受 S02 Q6–Q9 并关闭后续 QNA；发布 `S02-v1.0` 正式 spec；S02 进入 accepted；D01-v1.1/S01-v1.2 回填第五张 `task_restarts` 因果表与 retry 口径。 |
| `v0.8` | `2026-07-15` | `MKB owner + Codex` | 按 D01-v1.1/S02-v1.0 重新校准 S03 为单体内部 durable LS-RAG Workflow Engine；启动 3+3+3 progressive QNA；登记 Round 1 foundational gates G-03/G-12/G-13。 |
| `v0.9` | `2026-07-15` | `MKB owner + Codex` | 依据 owner 对 SMCP、声明式/agent-programmable Workflow 与 Process 解耦竞争优势的纠偏，深审 legacy protocol/mapper/IoManager/orchestrator/editor/tooling；撤回旧 Q1–Q3，将 G-03/G-12/G-13 重置为 Workflow 多平面宪法、agent authoring/publishing、local compiler + Process command/outcome contract。 |
| `v0.10` | `2026-07-15` | `MKB owner + Codex` | 冻结 S03 Round 1 `T-O-12..16`：六平面 Contract；agent authoring 为 v1 out-of-scope；内部注册、关系型 Workflow SSOT 与只读 compiled JSON。关闭 G-03/G-13、defer G-12，登记 Round 2 G-14..G-16。 |
| `v0.11` | `2026-07-15` | `MKB owner + Codex` | 冻结 S03 Round 2 `T-O-17..21`：七张 Workflow truth tables、JSON cutoff、typed acyclic routes、S03 ownership cutoff、internal compile/binding 与 ProcessCommand/Outcome。关闭 G-14..G-16，登记 Round 3 G-17..G-19。 |
| `v0.12` | `2026-07-15` | `MKB owner + Codex` | 按 owner 要求深审 Clean/RAG 两个 Dispatcher，为 S03 Q7/Q8 建立内部 reference anchors并区分 legacy fact 与 MKB upgrade；确认 legacy 无闭环通用 reconciler/Process compaction 证据，将 Q9 缩限为 Workflow semantic recovery invariant/transition 与 Process projection cleanup eligibility，移除 operator/revision 混题并重写 G-19。 |
| `v0.13` | `2026-07-15` | `MKB owner + Codex` | Owner 接受 S03 Q7–Q9；冻结 `T-O-22..29`并关闭 QNA Campaign；完成 D01/S01/S02 无冲突审计；发布 `S03-v1.0` 正式 spec，S03 进入 accepted，关闭 G-17..G-19并将 S04 依赖校准为 S02-S03。 |
| `v0.14` | `2026-07-15` | `MKB owner + Codex` | 启动 S04 3+3+3 progressive QNA；完成 legacy file/relation/diff/scatter/Artifact/Vector/Purge 与外部一手资料审查；将 S04 校准为长期 identity/version/publication/invalidation truth layer，登记 Round 1 G-20..G-22。 |
