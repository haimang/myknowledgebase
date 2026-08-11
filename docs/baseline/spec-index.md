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
> **日期**：`2026-08-10`
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
| `D3` | 摄入资产 | `S04` Intake Asset Lifecycle | IntakeSource/IntakeSnapshot/IntakeItem/IntakeRevision/IntakeArtifact 的权威生命周期，并为未来 Knowledge 层保留语义空间 |
| `D4` | 内容处理 | `S05` Intake & Cleaning | 输入如何变成可结构化的规范内容 |
| `D5` | LS-RAG 构建 | `S06` Structurizer；`S07` Constructor | 如何从exact IntakeRevision形成grounded ordered structure、稳定block projection和original/summary双通道 |
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
| `01` | `S01` | Skill-Worker Integration | `P0` | `accepted` | `domain-truth/S01-skill-worker-integration.md` | `00, D01` | `S01-v1.5`：standalone Contract；Task五轴查询面分账；polling+action_required；无内部状态写面 |
| `02` | `S02` | Task API & Lifecycle | `P0` | `accepted` | `domain-truth/S02-task-api.md` | `00, D01, S01, S03-S05` | `S02-v1.3`：六态/CAS不变；status/readiness/items/action_required/visibility分账；restart/lineage |
| `03` | `S03` | Workflow Engine | `P0` | `accepted` | `domain-truth/S03-workflow-engine.md` | `D01-v1.4, S01-v1.5, S02-v1.3, S04-v1.2, S05-v1.1` | `S03-v1.3`：七表/八态不变；status/phase/wait/outcome/route分账；S05 exact capability key |
| `04` | `S04` | Intake Asset Lifecycle | `P0` | `accepted` | `domain-truth/S04-intake-asset-lifecycle.md` | `00-v1.2, D01-v1.4, S01-v1.5, S02-v1.3, S03-v1.3, S05-v1.1` | `S04-v1.2`：五类identity/十表；Source/Snapshot/Item/staging/pointers/cleanup状态族分账 |
| `05` | `S05` | Intake & Cleaning | `P1` | `accepted` | `domain-truth/S05-intake-cleaning.md` | `D01-v1.4, S01-v1.5, S02-v1.3, S03-v1.3, S04-v1.2, S12-S16` | `S05-v1.1`：四类source；typed evidence；mandatory preflight/gate；outcome/staging/runtime分账；exact capabilities |
| `06` | `S06` | LS-RAG Structurizer | `P0` | `designing / Round 2 reframe` | `qna-truth/S06.md` | `D01, D02-v1.0, S03-S05, S07-S14` | `S06-QNA-v0.7`：Q1-Q3/`T-O-77..85`冻结；D02 hold已解除，Q4-Q6按S06/S02/S05/S08-S09 owner边界重构 |
| `07` | `S07` | LS-RAG Constructor | `P0` | `pending` | `domain-truth/S07-lsrag-constructor.md` | `S04, S06, S11, S13-S14` | 待设计 |
| `08` | `S08` | Embedding & Vectorization | `P0` | `pending` | `domain-truth/S08-embedding-vectorization.md` | `S07, S09, S11, S14` | 待设计 |
| `09` | `S09` | Vector Index Lifecycle | `P0` | `pending` | `domain-truth/S09-vector-index.md` | `S04, S12, S14` | 待设计 |
| `10` | `S10` | LS-RAG Retrieval & Reranking | `P0` | `pending` | `domain-truth/S10-lsrag-retrieval.md` | `S04, S07-S09, S11, S14` | 待设计 |
| `11` | `S11` | Inference Runtime & Adapters | `P0` | `pending` | `domain-truth/S11-inference-runtime.md` | `00, S14, S16` | 待设计 |
| `12` | `S12` | Turso Persistence | `P0` | `pending` | `domain-truth/S12-turso-persistence.md` | `S02-S05, S09` | 待设计 |
| `13` | `S13` | Artifact & Object Storage | `P1` | `pending` | `domain-truth/S13-artifact-storage.md` | `S04-S05, S12` | 待设计 |
| `14` | `S14` | Config, Prompt & Model Registry | `P1` | `pending` | `domain-truth/S14-config-prompt-model-registry.md` | `00, S11` | 待设计 |
| `15` | `S15` | Observability & Reliability | `P0` | `pending` | `domain-truth/S15-observability-reliability.md` | `S01-S14` | 待设计 |
| `16` | `S16` | Security & Trust Boundary | `P0` | `pending` | `domain-truth/S16-security-trust-boundary.md` | `S01-S15` | 待设计 |

### 1.2 跨系统基线与跨 Domain Truth 文档

| ID | 文档 | 状态 | 用途 |
|----|------|------|------|
| `00` | `spec-glossary.md` | `active / v1.4` | 登记D02-v1.0、六StateFamily、状态镜像块、drift协议与S06 `T-O-77..85`工作词；S06开放kind不标frozen |
| `D01` | `domain-truth/D01-task-execution-process-flow.md` | `accepted / D02-state-calibrated` | `D01-v1.4`：三层状态所有权与exact states；phase/outcome/assets分账；S05 exact capabilities；target/vector-index移交对应下游 |
| `D02` | `domain-truth/D02-production-state-and-routing.md` | `frozen / v1.0` | `T-O-86..92`冻结共有域宪法、六StateFamily、四层ledger、六项镜像块与双向drift协议；Q1-Q6完成、Round 3 waived、campaign关闭 |
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

## 2. Legacy reference-anchor 与设计分母

### 2.1 当前证据源

- `legacy-family/`：原 TypeScript/Cloudflare 实现，只用于 LS-RAG 行为考古、生产踩坑与设计反例；依据 `T-O-42`，不形成代码、数据、协议、运行或验收兼容关系。
- `legacy-python/`：已退役 Python 重构，仅供失败经验和基础设施思想参考，不作为新运行时依赖、迁移来源或兼容目标。
- 业主已确认方向：本索引 §0.1，是产品范围和责任边界的上游输入。

### 2.2 冻结设计分母

| 分母 | 当前值 | 含义 |
|------|--------|------|
| 核心 domain | `8` | 新系统的业务责任分组，不对应部署单元 |
| 详细子系统 spec | `16` | 必须逐项设计、接受并回填的最小完整集合 |
| 跨系统基线 spec | `3` | scope/glossary、system topology、acceptance/truth freeze |
| 跨 Domain architecture truth | `2` | `D01`：owner-originated runtime identity Flow；`D02-v1.0`：frozen shared-domain state constitution/ledger |
| Legacy TypeScript 项目 | `10` | 证据源数量，不代表新子系统数量 |
| 新 Python 发布单元 | `1` | leaf-worker 单体应用 |
| 已知首个上游调用单位 | `1` | `03-nano/orchestrator-core`；其他内部 orchestrator 必须遵守同一 MKB Contract |
| 平台租户所有权 domain | `0` | `team_uuid` 只作为上游审计/分区/过滤 ID，并通过最小 Team Registry 预注册 |
| UI 子系统 | `0` | MKB 不提供 UI |

这些分母在本索引处于 `active index` 时可以通过显式修订变更；进入 `frozen truth index` 后必须通过 reopen 记录修改。

### 2.3 Legacy reference-anchor 证据映射

| Reference anchor | 被哪些新 spec 查阅 | 仅允许的证据用途 |
|---|---|---|
| `smind-admin` | `S01, S02, S04, S05` | ingress、资源生命周期和平台职责泄漏反例 |
| `smind-clean-dispatcher` | `S03, S04, S05` | callback、diff/scatter、restart、关系散射与非事务 wakeup 踩坑 |
| `smind-rag-dispatcher` | `S03, S06-S09` | RAG 阶段、失败、purge 与跨 Worker 状态债务 |
| `smind-skill-clean-universal` | `S05, S11, S13` | input/clean/Artifact 行为和浏览器/PDF复杂度证据；不决定首版范围 |
| `smind-skill-clean-dedicated-apis` | `S04, S05` | API scatter、atomic key、content/meta digest 与 provider 分支证据 |
| `smind-skill-rag-structurizer` | `S06, S11, S14` | layered original/summary坐标、全文层、schema/model/prompt/repair行为与历史补丁证据 |
| `smind-skill-rag-constructor` | `S07, S11, S14` | LS-RAG 双通道、meta fusion 与 recorder 行为证据 |
| `smind-skill-rag-vectorizer` | `S03, S08, S09, S12, S15` | embedding/index/purge、队列与持久化耦合反例 |
| `smind-contexter` | `S06, S10, S11` | block/granularity坐标的真实消费、summary→original traceback、context expansion 与 rerank 行为证据 |
| `smind-console` | `S04/S15/S16` | file/child 查询、ACL、Artifact 反扫和 UI/platform 耦合反例；MKB 不建设替代 UI |

本表不是代码“新归宿”、数据迁移清单或兼容矩阵。任何 legacy package、schema、wire message、UUID/status 或 storage locator 进入 MKB runtime 都违反 `T-O-42`。

### 2.4 贯穿主题

- **职责而非部署单元**：新子系统边界不能重新复制 10 个 Worker 或 23 个 Python package。
- **业务状态内聚**：平台无状态不代表内部无状态，任务和知识资产状态必须由 MKB 负责。
- **模型与业务解耦**：LS-RAG 契约不能依赖 vLLM、某个云厂商或某个具体模型。
- **LS-RAG 双层语义**：summary 是语义索引，original 是最终 payload；两者通过稳定坐标关联。
- **外部 request intent 与内部 runtime 分离**：上游只创建/操作 Task；MKB 独占 Execution/Process、workflow、claim/retry 与结果证明。
- **单体不等于无边界**：只有一个发布单元，但领域、adapter、repository 和执行 lane 仍需明确。
- **统一扩展字段**：继承 `S01-T040/T041`，所有 MKB-owned 持久业务表必须包含非空默认 `{}` 的 `payload_extra`；引擎/第三方私表不强改。该字段只承接非权威开发期扩展，核心身份、状态、proof、路由、权限和查询语义必须晋升正式 schema 或版本化定义。

---

## 3. 逐子系统登记

### 3.1 `S01` Skill-Worker Integration

- **状态**：`accepted / D02-state-calibrated`；域内truth=`S01-v1.5`；全系统尚未frozen。
- **权威 Spec**：`docs/baseline/domain-truth/S01-skill-worker-integration.md`。
- **冻结范围**：MKB 先作为 standalone leaf-worker；MKB Contract 是权威接入协议；03-nano 或其他上游自行适配。
- **冻结身份**：边界 UUIDv4/v7、MKB 内生 UUIDv7；Task 权威键为 `(team_uuid, task_uuid)`；task/trace 由上游提供；Execution/Process 仅由 MKB 创建；Attempt identity 已废止。
- **冻结接入**：最小 Team Registry；只有 registered active team 可创建任务；Task + 独立 immutable Audit 1:1 原子落库。
- **冻结接入语义**：canonical 字段为 `request_intent`；旧 `task_type` 只允许 adapter 预翻译；Task/Workflow lifecycle 分离；single/scatter 均从一个 Task 进入。
- **冻结交付**：首版 polling，无 webhook/callback；Task 聚合 current root Execution；简单有效 token 可使用全部 Team/Task 功能，不做 team RBAC。
- **明确不做**：首版 skill-worker 注册/心跳/`SkillWorkerManifest`、用户身份、membership、计费、UI 和 03-nano 私有 RPC 兼容。
- **下游约束**：`S02/S03/S04/S12/S15/S16/17` 必须继承 S01 与 D01 Truth ID；偏离必须同时 reopen 受影响真相。

### 3.2 `S02` Task API & Lifecycle

- **状态**：`accepted / D02-state-calibrated`；域内truth=`S02-v1.3`；QNA Q1–Q9全部冻结，Round 4已由owner关闭；全系统尚未frozen。
- **权威 Spec**：`docs/baseline/domain-truth/S02-task-api.md`；问答证据保留于 `docs/baseline/qna-truth/S02.md v1.3`。
- **范围**：Task create/get/list/result/cancel/retry/delete、幂等、aggregate 状态机、scatter item projection、restart causation/global query、优先级、deadline、错误和 retention。
- **已冻结**：Task六态与lifecycle CAS；scatter collect-all、bounded aggregate + paginated TaskItems + canonical IntakeItem/Revision links、proof-gated early publication、forward-stop cancel；full retry同Task新generation；atomic restart创建新`intake.rebuild` Task且不创建IntakeRevision；`task_restarts`保存full/atomic因果且状态只join Task；team-scoped restart/lineage。
- **Legacy 核查**：已复验 API 发起 → Dedicated Cleaner 散射 → SMCP callback → Clean Dispatcher diff/register → child 并行 RAG 投递 → relation child completion，以及原子 list/artifact/timeline/restart；MKB 明确修复 identity UPSERT、非事务 wakeup、无 parent fan-in 与 route 散射债务。
- **Owner-gate closure**：Q1–Q9 与 `T-O-1..11` 全部获得 owner 确认；S02 不再增加 QNA，无域内开放 gate。
- **关键不变量**：上游不能创建或写 Execution/Process；相同 `task_uuid + payload digest` 必须幂等收敛；Task 不承载 RAG 工序状态；原子 CRUD 不得泄漏内部 stage/process identity。
- **已回填影响**：D01-v1.4/S01-v1.5继续确认五张Task ingress/runtime/restart真相表；S04十张canonical资产表与S05 gate/outcome supporting truth不构成runtime身份；S12必须交付exact DDL/transaction。
- **完成回填**：已冻结 Task Contract v1、状态图、HTTP surface、错误码、强制验收与 legacy reference-anchor。

### 3.3 `S03` Workflow Engine

- **状态**：`accepted / S03-v1.3 / D02-state-calibrated`；QNA`docs/baseline/qna-truth/S03.md v1.0`已冻结关闭，正式权威文档为`docs/baseline/domain-truth/S03-workflow-engine.md`。
- **定位**：S03 是 MKB 单体内部唯一 durable、declarative、future-agent-ready 的 LS-RAG Workflow Engine。v1 采用内部注册制：关系型 schema 是 Workflow SSOT，canonical JSON 是只读派生表示；对外只有 list/get，无 create/update/delete，也不实现 agent 直接定义 Workflow。
- **范围**：六平面 Workflow Contract；internal registry/revision；normalized step/route/binding/control/guard schema；deterministic compiler 与 compiled JSON/digest；capability/port registry 与本地 Process runtime contract；Execution binding/state/phase/tree/generation；Process dependency/materialization、I/O/outcome guard；durable scheduling；claim/lease/fencing；retry/backoff/timeout；priority/deadline；cancel/purge/case/scatter control；Workflow semantic recovery invariant/transition；Process projection cleanup eligibility。
- **继承的冻结真相**：Task/Execution/Process 三层身份及三张核心运行表；single=root Execution、scatter=root controller + 0..N child Executions；状态自下而上、control intent 自上而下；Process/Execution 未提交 proof 前 Task 不成功；queue 不是 SSOT且只能在 durable state 提交后 wake-up；full retry 新 root generation、automatic Process retry 不换 Process；collect-all、child proof-gated early publication 与 forward-stop/no-rollback cancel。
- **明确不负责**：Task HTTP/六态/CAS/restart ledger（S02）；IntakeSource/Snapshot/Item/Revision/Membership/ChangeSet真相（S04-S05）；LS-RAG schema/model/prompt与proof算法（S06-S11/S14）；Turso exact DDL/queue（S12）；storage backend（S13）；event/log/trace与retention数值（S15）。
- **Round 1 冻结结论**：`T-O-12` 六平面 Workflow Contract；`T-O-13` agent authoring/publish 为 v1 out-of-scope；`T-O-14` 内部注册且外部只读；`T-O-15` 关系型 schema 是 durable SSOT；`T-O-16` compiled JSON 是可重建派生表示。
- **Round 2 冻结结论**：`T-O-17` 七张 Workflow definition/control truth tables；`T-O-18` core truth 禁止 opaque JSON；`T-O-19` typed/guarded/acyclic route graph 与 S03 cutoff；`T-O-20` internal register/compile/immutable Execution binding；`T-O-21` Engine-interpreted plan + ProcessCommand/ProcessOutcome leaf contract。
- **Round 3 冻结结论**：`T-O-22..24` 冻结 Process `ready/claimed/running/retry_wait/succeeded/failed/cancelling/cancelled`、claim/lease/fencing 与 delivery/recovery/retry 分账；`T-O-25..27` 冻结 Execution `created/ready/running/waiting/succeeded/failed/cancelling/cancelled`、独立 RAG phase、single/scatter collect-all/cancel/terminal summary；`T-O-28..29` 冻结 semantic recovery 与 Process cleanup eligibility/cutoff。
- **交叉审计**：S03 QNA原始裁决与D01/S01/S02无冲突；S04-S05回填后，Workflow七表与Execution/Process状态不变，resource/S05 binding、fan-in分母、human_review waiting、proof target和recovery fence均已统一。
- **关键不变量**：对外没有 Workflow CUD；Task caller/工具不得借 payload 注入 graph；compiled JSON 不得反向成为 truth；registry/revision 变化不得热改已绑定 Execution；Process 只消费本工序 Command/返回 Outcome，route 只由 Engine 推进；不得重新引入 Attempt、clean/rag process 分表、跨 Worker callback SSOT、Task current_process 指针或 queue-send-as-success。
- **完成回填**：冻结 Workflow relational schema/registration/compiler/read contract、runtime binding、Execution/Process 状态机、process capability/port/guard、materialization、claim/fencing、retry/cancel、single/scatter fan-out/fan-in、semantic recovery、Process cleanup eligibility 和强制验收矩阵。

### 3.4 `S04` Intake Asset Lifecycle

- **状态**：`accepted / S04-v1.2 / D02-state-calibrated`；QNA`docs/baseline/qna-truth/S04.md v1.1`的Q1-Q9/`T-O-30..48`全部冻结，正式权威文档为`domain-truth/S04-intake-asset-lifecycle.md`。
- **定位**：MKB摄入资产的canonical identity、accepted observation/collection、immutable semantic revision、provenance、serving、withdrawal、retention与greenfield governance真相层；不承载Task/Execution/Process，也不提前建立Knowledge层。
- **五类identity**：`IntakeSource`是ExternalKey namespace；`IntakeSnapshot`是accepted immutable observation；`IntakeItem`是source-scoped stable subject；`IntakeRevision`是immutable semantic state；`IntakeArtifact`是Snapshot或Revision的XOR-owned representation。
- **十表SSOT**：五张identity表，加`intake_snapshot_memberships`、semantic/action definitions、revision semantics与item transitions；staging/outbox/repair/cleanup ledgers是supporting truth，不是新增资产或runtime identity。
- **single/scatter**：single通常是一份Snapshot的一个membership；scatter是一份Snapshot的0..N memberships。root先消费accepted Snapshot/ChangeSet required set，之后才wake并行child Executions；scatter parent不伪造Item。
- **Revision/serving**：canonical semantic change才追加Revision；rebuild/model/index generation不建Revision。latest与serving分离，只有type-specific proof-valid CAS才能上线；Task cancel不撤销serving。
- **lifecycle**：Item只有`active/deactivated/deleted`；CoreEffect封闭，SemanticDefinition/ActionDefinition内部注册且immutable versioned；deactivate/delete logical-first，complete-authoritative Snapshot才可按absence失活。
- **large-scatter/recovery**：paged immutable CandidateSet→seal/size fence→one canonical acceptance transaction；recovery只修已提交projection/wakeup/intent，不从日志、queue、IntakeArtifact或payload_extra合成truth。
- **retention/reindex/purge**：deactivate、delete、rebuild/reindex、physical purge四intent分账；reindex采用generation proof-switch；各substrate独立cleanup proof；v1保留最小tombstone/audit skeleton且不开放deleted restore。
- **greenfield governance**：空DB确定性bootstrap schema/registry；同版本同digest no-op、异digest fail；仅做MKB自身forward schema evolution；startup drift拒绝readiness；验收扫描零legacy runtime dependency。
- **ReferenceAnchor纪律**：legacy-family只证明生产踩坑与设计分母，不继承代码、数据、wire/schema、UUID/status、storage、bootstrap或acceptance。
- **跨文档回填**：D01-v1.4、S01-v1.5、S02-v1.3、S03-v1.3与S05-v1.1已完成Intake/Candidate/Preflight/HITL、single/scatter、proof/rebuild/cleanup与状态族校准；D02-v1.0已冻结共有边界，exact kind继续归对应下游且不构成D02未完成。
- **关键不变量**：Snapshot不是attempt；Revision不原位覆盖；latest不等于serving；partial observation不推导全量absence；physical residue不授予retrieval eligibility；payload_extra不承载核心truth。
- **完成回填**：正式Spec冻结44条S04 Truth、logical schema、business flow、errors、risks、36项验收与reference-anchor台账；G26-G28关闭。

### 3.5 `S05` Intake & Cleaning

- **状态**：`accepted / S05-v1.1 / D02-state-calibrated`；QNA`docs/baseline/qna-truth/S05.md v1.0`的Q1-Q10/`T-O-49..76`全部冻结，正式权威文档为`domain-truth/S05-intake-cleaning.md`。
- **定位**：MKB摄入获取、解码、source-specific mapping、canonicalization、clean、CandidateSet构建与clean后/RAG前准入域；不创建Task/Execution/Process/Intake身份或第二套状态机。
- **能力范围**：v1覆盖inline/local、网页static/browser、PDF、registered API single/scatter/pagination、local OCR与Vision/model-assisted clean；四类source kind固定为`inline_payload/local_object/http_resource/registered_api`，获取和clean capability与source kind正交。
- **输入与身份**：`IntakeSourceKindDefinition`内部immutable versioned注册；strict descriptor/config/secret分账；ExternalKey由source-specific pure normalizer产生；media、encoding、stream/decompress/redirect/page/time budgets形成typed evidence。
- **输出与完整性**：只产出`AcquisitionEvidence/IntakeCandidateMember/CleanArtifactCandidate/paged IntakeCandidateSet`；raw/source-semantic/clean-derived分账；SHA-256+JCS+UTF-8/LF/NFC+结构HTML基线；stable page/root digest、rejection manifest与source-exhaustion proof共同控制seal。
- **Intake cutoff**：CandidateSet seal不是accepted Snapshot；只有S04 canonical acceptance transaction可提交Snapshot/Membership/Item/Revision/ChangeSet/outbox。AI/OCR/model变化不单独制造IntakeRevision。
- **Preflight**：allowlist只授予mandatory preflight通过后的自动资格；每条binding引用exact code-owned versioned`PreflightValidator`；validator只读frozen evidence并返回`passed|blocked`，runtime/schema/evidence错误复用S03 retry/failed。
- **Human gate**：`passed+allowlisted`直接继续RAG且不建gate；只有需要人工动作时创建Execution-owned`open→released|rejected|superseded` gate。ReviewTarget绑定exact generation/fence/Workflow/Intake/Artifact/Outcome，Decision以append+CAS+outbox恢复same Execution。
- **v1治理边界**：只冻结registration/binding、outcome/evidence、human gate/target、decision四组durable职责，不冻结物理表数；Execution锁定`s05_binding_digest`且retry/recovery/resume不热切。v1不建dynamic plugin/agent rules、runtime selfTest、shadow/canary、自动timeout或独立Reconciler。
- **ReferenceAnchor纪律**：legacy-family只证明能力面、SMCP typed I/O原理与silent skip/random child/callback成功等踩坑，不产生runtime/schema/API/storage/acceptance兼容。
- **关键不变量**：无validator不自动放行；missing Artifact不可人工伪造；root required evidence未过不推进children；waiting永不自动approve；`payload_extra`不承载identity/state/proof/route/auth/正文。
- **完成回填**：正式Spec冻结30条S05 Truth、logical contracts、single/scatter/preflight/HITL flows、typed errors、风险、35项验收与reference-anchor台账；G04/G30-G32关闭。

### 3.6 `S06` LS-RAG Structurizer

- **状态**：`designing / Round 2 reframe / qna-truth/S06.md v0.7`；Round 1 Q1-Q3与`T-O-77..85`已冻结，D02-v1.0前置hold已解除；Q4-Q6按S06/S02/S05/S08-S09责任重构，正式Spec尚未创建。
- **重新定位**：S06是LS-RAG original内容结构建模与grounded block projection域。它消费exact accepted `IntakeRevision + clean IntakeArtifact + frozen S05 evidence/binding`，产出可验证的ordered structure、source anchors、stable coordinates、block projection和Process proof；不是generic text chunker、第二次clean或summary worker。
- **上游继承**：复用S03 `lsrag.structurize` Process capability与八态/claim/fence/retry；structure/model/prompt rebuild不制造IntakeRevision；S06 success不切serving；single按Revision构建，scatter children各自构建且不形成跨Item大树；logical handle取代路径/R2 key。
- **ReferenceAnchor结论**：legacy证明全文层、layered original/summary与共享坐标具有真实生产消费者；同时暴露flat `block_id+granularity`缺parent/order/anchor/generation、模型UUID幻觉、block 0注入/移除反复、自动修补schema drift、整文单次模型调用与物理key callback成功等债务。
- **Web结论**：Docling/Unstructured/LlamaIndex支持“typed hierarchy/provenance先于structure-aware chunk projection”；RAPTOR支持多层抽象价值但summary tree继续归S07；JSON Schema只能证明形状，不能替代tree/coverage/order/anchor语义证明。
- **已冻结foundation**：immutable GenerationArtifact/Invocation历史、per-Execution/per-type full-valid current pointer、Task-scoped受限read、immutable StructureSchemaDefinition、exact producer/consumer binding、deterministic kernel/governed extension与S03 max-retries收敛。
- **D02冻结回流**：D02-v1.0已冻结六StateFamily、四层ledger、六项镜像块和drift协议；Execution subject、artifact bundle、node/anchor/block kind、curation/loss及S08/S09责任仍由对应下游QNA/Spec冻结后回填D02。S06 v0.5 Q4-Q5与Q6旧稿只作reframe素材，不自动转正；后续Truth-ID从`T-O-93`继续。
- **关键不变量**：S06不建私有状态机；GenerationInvocation不是Attempt；invalid/repair-failed artifact不切current；source identity/fidelity不可由agent修补；S06 success不等于Execution/Task/serving success。
- **完成回填条件**：关闭S06仍不可由既有Truth推导的必要决策后，直接发布正式Spec，冻结logical schema、coordinate/anchor、large-input execution、proof/error/idempotency、binding/rebuild/recovery和下游S07-S10 contract，再回流D01/S01-S05、D02与glossary；不以固定Q1-Q9题数作为完成条件。

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
| `G-01` | Skill-worker发现与注册方式 | `S01, 17` | 主动注册 / 上游静态配置 / 混合 | `deferred` | `S01-v1.5`：首版standalone，不注册；未来只通过防腐adapter reopen |
| `G-02` | Task结果交付方式 | `S01-S03, S15-S16` | 上游轮询 / callback / 双支持 | `closed` | `S01-v1.5/S02-v1.3`：首版polling；Task status/readiness/action_required分账；无webhook/callback或直接Execution/Process写面 |
| `G-03` | Workflow Program语义宪法 | `S03-S09, S12-S15` | topology清单 / 多平面声明式RAG程序 / 任意代码自动化 | `closed` | `T-O-12`：采用六平面端到端Contract；BindingSource声明规则，Engine注入runtime facts；topology只是Control子平面 |
| `G-04` | 首版 Intake 范围 | `S04-S05, S13` | text/object only / URL / PDF/browser/API/OCR/Vision | `closed` | `T-O-49..51 / S05-v1.1`：完整能力面纳入v1；source kind只有inline/local/HTTP/registered API，browser/PDF/OCR/Vision/scatter为正交capability/cardinality |
| `G-05` | parent-child/scatter首版范围 | `D01, S03-S07` | 首版支持 / schema预留后延 | `closed` | `D01-v1.4/S04-v1.2/S05-v1.1`：scatter为一等能力；Task→root→0..N child Executions；集合truth为Snapshot/Membership/ChangeSet，root/child preflight/gate原生支持 |
| `G-06` | MKB-native LS-RAG canonical structure形状 | `S06-S10` | legacy flat layered array / single-root ordered typed tree + deterministic block projection / blocks-only | `open / S06` | `T-O-80..83`已冻结Schema authority/kernel原则；node/edge/anchor/block exact kind由S06裁决并按T-O-87回填D02，legacy兼容已排除 |
| `G-07` | Retrieval 是否承担 answer generation | `S01-S02, S10-S11` | 只返回 context / 可选生成任务 | `open` | 待 `S10` |
| `G-08` | Turso 运行和进程模型 | `S03, S09, S12, 17` | 单进程 embedded / 多进程 / remote-sync | `open` | 待 `S12` spike |
| `G-09` | 首版向量索引 | `S08-S10, S12` | Turso exact / 独立 ANN / 分阶段 | `open` | 待 `S09` benchmark |
| `G-10` | 模型 fallback 语义 | `S06-S08, S10-S11, S14` | 禁止自动 fallback / 受控 fallback | `open` | 待 `S11` |
| `G-11` | Asset storage首版backend | `S05-S07, S12-S13, 17` | 本地filesystem / S3-compatible | `open` | 待`S13` |
| `G-12` | Agent authoring 与 Workflow publication 治理 | `S03, S14-S16` | v1 实现 / future adapter-ready / 永不支持 | `deferred` | `T-O-13`：第一次重构 out-of-scope；只保留 future-agent-ready schema/interface，未来接入必须 reopen |
| `G-13` | Workflow Registry、SSOT 与 compiled representation | `S03, S12-S14` | 外部 CRUD + JSON truth / 内部注册 + relational truth + compiled JSON / code-only hardcode | `closed` | `T-O-14..16`：内部注册；外部仅 list/get；normalized DB schema 是 SSOT；compiled JSON 是可重建派生表示 |
| `G-14` | Workflow normalized table 与 JSON 边界 | `S03, S12, S14` | 单表 JSON / 七表职责拆分 / 更细粒度规范化 | `closed` | `T-O-17..18`：冻结七表职责、跨 revision 围栏、typed extension 与 compiled/diagnostic JSON 非权威边界 |
| `G-15` | Workflow route/control graph 语义 | `S03, S05-S09, S12` | rank 线性 / typed acyclic graph / 支持业务 loop | `closed` | `T-O-19`：typed/guarded/acyclic RAG graph；branch/fan-out/fan-in；retry/cancel cycles 归 Engine；S03 cutoff 已冻结 |
| `G-16` | Compiled plan、Execution binding 与 Process runtime boundary | `S03, S05-S09, S12-S15` | whole JSON 直交 Process / Engine interpret + command/outcome / direct local function coupling | `closed` | `T-O-20..21`：internal register/compile；Execution exact binding；eligible Process materialization；ProcessCommand/Outcome leaf contract |
| `G-17` | Process state、claim/lease/fencing/retry | `S03, S12, S15` | pending-heavy / eligibility-ready + fenced lease / queue-delivery-driven | `closed` | `T-O-22..24 / S03-v1.3`：exact八态、atomic claim/current fence、delivery/recovery/retry三账、same-process retry/max-retries；Outcome与status分账 |
| `G-18` | Execution status、RAG phase与scatter/cancel convergence | `S02-S09, S12, S15` | 混合大enum / control status + separate RAG phase / Process直写Task | `closed` | `T-O-25..27 / S03-v1.3`：exact八态、typed waiting reason、独立phase、Snapshot/ChangeSet collect-all；phase不决定Process粒度 |
| `G-19` | Workflow semantic recovery与Process cleanup eligibility | `S03, S12, S15` | 无恢复机制 / S03定义语义不变量与幂等repair、S12执行扫描/outbox/cleanup / 独立通用reconciler | `closed` | `T-O-28..29 / S03-v1.3`：repair含S05四窗口、无独立Reconciler、terminal-summary-before-cleanup、S12/S15 cutoff |
| `G-20` | Intake aggregate identity ownership | `S04-S10, S12-S13` | mutable file/relation / IntakeSource+Snapshot+Item+immutable Revision+scoped IntakeArtifact / content blob即Item | `closed` | `T-O-30..31 / S04 Q1`：五类ownership、membership、single/scatter、无伪parent Item与future Knowledge cutoff已冻结 |
| `G-21` | IntakeRevision creation 与 external identity scope | `S04-S09, S12-S15` | 裸atomic_id+原位覆盖 / source-scoped key+semantic-change追加Revision / 每次执行都建Revision | `closed` | `T-O-32..33 / S04 Q2`：stable Item、immutable Revision、runtime generation分账；semantic dimensions 内部注册且版本化 |
| `G-22` | Serving、deactivate 与 delete 语义 | `S02-S04, S09-S10, S12-S16` | latest即serving / proof-gated serving pointer+logical fence+physical convergence / 以vector存在判断可见 | `closed` | `T-O-34..35 / S04 Q3`：latest/serving、proof CAS、tombstone、authoritative absence 与 versioned action/route 已冻结 |
| `G-23` | S04 relational truth topology 与 semantic/action registry | `S04-S05, S12-S15` | mutable Item JSON / 十张 normalized truth tables+immutable internal registries / 每个分支单独增表 | `closed` | `T-O-36..37 / S04 Q4`：十表职责、registry/JSON cutoff已冻结；所有 MKB-owned 持久业务表强制 `payload_extra`，关键语义须晋升 |
| `G-24` | Snapshot acceptance 与 Revision decision transaction | `S03-S05, S12, S15` | 分步最终一致 / CandidateSet到Snapshot+ChangeSet+child intent原子提交 / queue message为SSOT | `closed` | `T-O-38..39 / S04 Q5`：幂等 acceptance、semantic comparison、authoritative absence、outbox 与 typed Workflow route cutoff 已冻结 |
| `G-25` | Intake lifecycle、CoreEffect 与可扩展 ActionDefinition | `S02-S04, S09-S10, S12-S16` | 业务原因扩成状态 / 三态core+有限effect+versioned action / 自定义action直接写状态 | `closed` | `T-O-40..41 / S04 Q6`：active/deactivated/deleted、CAS/audit/outbox transition、typed facts 与 route binding 已冻结 |
| `G-26` | Large-scatter acceptance recovery | `S03-S05, S12-S15` | 无界单事务 / paged sealed CandidateSet+size fence+single acceptance+deterministic recovery / partial Snapshot | `closed` | `T-O-43..44 / S04-v1.2/S05-v1.1`：open→sealed→accepted与open→abandoned；唯一canonical commit；不得合成未提交truth |
| `G-27` | MKB-only Intake retention、reindex与physical purge | `S04, S08-S10, S12-S15` | purge混合reset / 四intent+generation switch+substrate proofs+tombstone skeleton / 直接硬删 | `closed` | `T-O-45..46 / S04-v1.2`：lifecycle/pointers/cleanup proofs分账；v1无deleted restore/tombstone hard delete |
| `G-28` | Greenfield bootstrap、MKB schema evolution与S04 acceptance | `S04, S12-S18` | 隐式代码默认 / deterministic schema+RegistryManifest+readiness/acceptance gate / legacy migration/cutover | `closed` | `T-O-47..48 / S04-v1.2`：empty-DB bootstrap、forward MKB migrations、drift fail-loud、完整acceptance与零legacy dependency |
| `G-29` | MKB 与 legacy-family 的应用边界 | `00, S01-S16, 17-18` | compatibility/migration / reference-anchor only | `closed` | `T-O-42`：完全独立；无 importer、dual-read、identity mapping、cutover/rollback 或 runtime/schema/API/acceptance dependency |
| `G-30` | S05 source/input/output与CandidateSet完整性 | `S04-S06, S12-S16` | opaque payload/child_files / strict definitions+typed evidence+deterministic seal | `closed` | `T-O-59..64 / S05-v1.1`：四类descriptor、ExternalKey normalizer、typed output、canonical digest与staging合法边全部冻结 |
| `G-31` | Allowlist与mandatory preflight最小闭环 | `S03-S05, S12, S15-S16` | allowlist绕过 / code-owned只读validator / 通用policy-plugin平台 | `closed` | `T-O-52/T-O-65/T-O-70..74`：每条allowlist exact绑定validator；passed自动路由无gate；只冻结四组durable职责，外围治理defer |
| `G-32` | Human review ownership、binding与恢复 | `S02-S05, S12-S16` | Intake review状态 / Execution durable gate+exact target / Process持lease等待 | `closed` | `T-O-53..58/T-O-73/T-O-75..76`：Execution-owned四态gate、append decision+CAS+outbox、same-Execution resume、binding不热切与四窗口recovery |
| `G-33` | S06 generation历史、schema authority与current selection foundation | `S03-S09, S12-S15` | 覆盖Revision JSON / immutable history+exact schema+CAS current / mutable latest file | `closed foundation` | `T-O-77..82`：GenerationArtifact/Invocation、受限read、per-type pointer、StructureSchemaDefinition与consumer exact binding已冻结；type/bundle归S06 Round 2 |
| `G-34` | S06 deterministic kernel、governed extension与failure convergence | `S05-S08, S11, S14-S15` | 完全信任LLM+原位修补 / governed new-artifact repair+full validation / deterministic-only | `closed foundation` | `T-O-83..85`：kernel不可agent修、extension受注册policy、repair新artifact且全量复验、S03 max-retries止血 |
| `G-35` | 全生产状态、路由与kind矩阵校准 | `D01-D02, S01-S09, S12-S16` | monolithic status / shared-domain constitution+six StateFamilies+downstream mirrors / D02执行总Spec | `closed / D02-v1.0` | `T-O-86..92`冻结共有宪法、六StateFamily、四层ledger、六项镜像块与双向drift协议；具体业务kind/route明确归下游，非D02 blocker |

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
| `team_uuid`为审计/分区/追踪ID，并需本地预注册 | 业主裁决 + `S01-v1.5` | 允许最小Team Registry；不得重新引入membership/ownership/billing |
| Task/Audit接入基线 | `S01-v1.5` | `(team_uuid, task_uuid)`、root trace、`request_intent`、immutable Audit、原子创建、polling/action_required必须被下游继承；Task status/readiness/items/action_required/visibility必须分账 |
| Task/Execution/Process Flow | `D01-v1.4 + S01-v1.5` | Owner-originated三层切分；Attempt废止；preflight归Process、human gate归Execution waiting；三层exact state及phase/outcome/asset边界不得重问 |
| Task API / Aggregate Lifecycle | `S02-v1.3` | 六态/CAS、Snapshot/ChangeSet items/collect-all、cancel/generation/restart、running+action_required与Task五轴查询面不得重问 |
| Declarative Workflow Engine | `S03-v1.3` | 六平面、关系型Workflow SSOT、七表、S05 exact capability binding、Process状态/claim/retry、human_review waiting、semantic recovery不得重问 |
| Intake Asset Lifecycle | `S04-v1.2` | 五类identity、十表SSOT、typed CandidateSet/preflight acceptance、Revision/serving、retention/purge与各状态族解耦不得绕过 |
| Intake & Cleaning | `S05-v1.1` | 四类source、完整clean能力面、typed evidence/CandidateSet、mandatory preflight、minimal ExecutionGate、binding不热切、Candidate合法边与v1 scope cutoff不得扩张或绕过 |
| Production State Constitution & Ledger | `D02-v1.0 / T-O-86..92` | D02已冻结：六StateFamily、state-vs-fact、四层ledger、六项镜像块及双向drift协议；具体执行/路由归下游，命中状态语义时同轮回填 |
| S06 frozen foundation | `qna-truth/S06.md v0.7 / T-O-77..85` | Q1-Q3保持冻结；D02 hold已解除，Q4-Q6按owner domain重构且不得新增私有状态机；新Truth从`T-O-93`继续 |
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

当 21 份详细/跨系统/cross-domain truth 文档（`00 + D01 + D02 + S01-S16 + 17 + 18`）全部达到 `accepted`：

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
- Intake & Cleaning：`docs/baseline/domain-truth/S05-intake-cleaning.md`
- S06 Progressive QNA：`docs/baseline/qna-truth/S06.md`
- 系统拓扑：`docs/baseline/specs/17-system-topology.md`（待创建）
- Truth freeze：`docs/baseline/specs/18-acceptance-truth-freeze.md`（待创建）

---

## 附录 A · Truth Freeze Checklist

| 检查项 | 状态 | 证据/备注 |
|--------|------|-----------|
| `00` Scope & Glossary accepted | `pending` | |
| `D01` Task/Execution/Process Flow accepted | `accepted / D02-state-calibrated` | Owner-originated；D01-v1.4/S01-v1.5已接收restart、Intake、preflight与ExecutionGate truth，并完成exact state/phase/outcome/asset分账 |
| `D02` Production State Constitution & Ledger | `frozen / v1.0` | `T-O-86..92`、六StateFamily、镜像块与drift协议已冻结；Q1-Q6完成、Round 3 waived，S06 D02 hold解除 |
| `S01-S16` 全部 accepted | `pending` | |
| `17` System Topology accepted | `pending` | |
| `18` Acceptance Matrix accepted | `pending` | |
| Owner-gate 全部 closed/deferred | `pending` | |
| 跨 spec ID 对账完成 | `pending` | |
| 跨 spec 状态机对账完成 | `D02 baseline completed / downstream ongoing` | D01/S01-S05及六StateFamily已按D02-v1.0对账；S06-S16后续仍须逐Spec继承并回填，不等于全baseline状态对账完成 |
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
| `v0.15` | `2026-07-15` | `MKB owner + Codex` | 依据 owner 新词汇整体重置 S04 为 Intake Asset Lifecycle；采用 IntakeSource/Snapshot/Item/Revision/Artifact，保留 Knowledge namespace；建立 `00-scope-glossary.md v0.1`，重写 G-20..G-22，并登记 D01/S01-S03 在 S04 定稿前保持不动。 |
| `v0.16` | `2026-07-15` | `MKB owner + Codex` | Owner 接受 S04 Q1-Q3 并要求执行语义可扩展；冻结 `T-O-30..35`、关闭 G-20..G-22；将 glossary 升至 v0.2；登记 closed invariant kernel + versioned semantic/action definitions + typed Workflow facts，并生成 Round 2 G-23..G-25 / Q4-Q6。 |
| `v0.17` | `2026-07-15` | `MKB owner + Codex` | Owner 接受 S04 Q4-Q6 并重申所有 MKB-owned 持久业务表强制 `payload_extra`（继承 S01 引擎私表例外）；冻结 `T-O-36..41`、关闭 G-23..G-25；将 glossary 升至 v0.3并登记 extension-field promotion rule；生成 Round 3 G-26..G-28 / Q7-Q9。 |
| `v0.18` | `2026-07-15` | `MKB owner + Codex` | Owner 明确 MKB 与 legacy-family 完全独立；冻结 `T-O-42`并关闭 G-29，将全索引 legacy 关系校准为 reference-anchor only；Q8 改为 MKB-only lifecycle，撤回旧 Q9 migration/cutover并将 G-28/Q9 重建为 greenfield bootstrap、MKB schema evolution 与 S04 acceptance。glossary 升至 v0.4。 |
| `v0.19` | `2026-07-15` | `MKB owner + Codex` | Owner接受S04 Q7-Q9；冻结`T-O-43..48`并关闭G26-G28；发布S04-v1.0。完成D01-v1.2、S01-v1.3、S02-v1.1、S03-v1.1 Intake语义回填及全量一致性审计；glossary迁移后的权威路径更新为`spec-glossary.md`并升至v1.0，补登记S04 ports、IntakeItemTransition、SkillWorkerManifest等已知定义；G06移除legacy兼容/双读候选。 |
| `v0.20` | `2026-07-16` | `MKB owner + Codex` | Owner接受收紧后的S05 Q7-Q10并锁定QNA；发布S05-v1.0，冻结四类source/typed candidate-clean contract、mandatory preflight、minimal ExecutionGate、exact binding与四窗口recovery；关闭G04并登记/关闭G30-G32；glossary升至v1.1，完成D01/S01-S05一致性校准。 |
| `v0.21` | `2026-07-16` | `MKB owner + Codex` | 启动S06 3+3+3 progressive QNA；依据D01/S01-S05将S06重述为grounded original structure compiler；完成Structurizer/Dispatcher/Constructor/Recorder/Traceback及Git补丁史核查，并用Docling/Unstructured/LlamaIndex/RAPTOR/JSON Schema一手资料校验；登记G33-G34并重写G06，提出Round 1 Q1-Q3。 |
| `v0.22` | `2026-07-18` | `MKB owner + Codex` | Owner要求暂停S06并发起全状态合集校准；建立D02-v0.2 DAG、状态族/路由/kind与冲突台账；完成D01-v1.4、S01-v1.5、S02-v1.3、S03-v1.3、S04-v1.2、S05-v1.1状态边界回填；S06-v0.6保留T-O-77..85并hold Q4-Q6；glossary升至v1.2。开放提案仍为owner-gate，未扩充v1。 |
| `v0.23` | `2026-07-19` | `MKB owner + Codex` | 冻结D02 QNA Round 1 `T-O-86..89`：D02成为共有域状态宪法与Truth镜像ledger，六StateFamily成为owner-frozen最小状态集合，具体执行/路由归下游冻结后双向回填；撤回D02直接裁决route authority的扩张。D02升至v0.3、glossary升至v1.3，进入Q4-Q6 ledger execution owner-gate。 |
| `v0.24` | `2026-08-10` | `MKB owner + Codex` | Owner要求直接收口并冻结D02：接受Q4-Q6、冻结`T-O-90..92`，发布D02-v1.0四层宪法/ledger并waive Round 3；G35关闭，glossary升至v1.4；S06升至v0.7并解除D02 hold，剩余业务问题归对应下游而不再上提D02。 |
