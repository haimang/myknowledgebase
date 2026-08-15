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
> **日期**：`2026-08-13`
>
> **作者**：`MKB owner + Grok workflow domain-truth-s14-s16`
>
> **文档性质**：`specification / index`
>
> **文档状态**：`active index`（S01–S16 均已 accepted；**D06** Runtime Topology = `draft / owner-calibrated`；**D07** 验收台账 = `draft / v0.5`；**D08** 四域能力迁移 = `draft / v0.1`；`18` 仍 pending → **尚未** `review-ready` / `frozen truth index`）
>
> **当前站位**：站① · specification 基线与设计编排
>
> **上游事实源**：业主已确认的产品方向 + owner-originated `D01` + `legacy-family/` 行为证据
>
> **下游消费者**：16 份子系统 spec、跨 Domain truth（含 **D06 运行拓扑**）、验收矩阵、truth freeze、重构计划

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
- **本阶段产物**：8 个核心 domain、16 个子系统的详细 specification，外加范围词汇表、**运行拓扑（D06）**、验收台账（**D07**）、legacy 四域能力迁移（**D08**）和真相冻结矩阵（`18`）。
- **本阶段不产出**：实现任务拆解、工期、迭代排期、具体代码和迁移执行计划。  
- **有限例外（D03-v1.0 / `T-O-141..159`；D04-v1.0 / `T-O-160..179`）**：Owner 冻结 **仓库目录宪法与 `src/contracts` typed SSOT 落点**，以及 **Turso 物理表闭集/列/索引/VIEW（D04）**；不因此开放随意实现排期或业务状态机旁路。
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

### 0.2a 执行真相层纪律（Owner 强制 · 2026-08-12）

1. **`docs/baseline/domain-truth/*` 是唯一执行真相（SSOT）**：实现、验收、对账、architecture tests **只**依赖 domain-truth（及 D04 物理 DDL 等已接受 formal）。  
2. **`docs/baseline/qna-truth/*` 仅为 progressive 中间态 / 证据层**：保留 T-O 形成过程；**不得**被实现引用为第二执行真相；不得「细节在 QNA、Spec 只写原则」。  
3. 已升格执行台账（E 包）的 Spec 版本：`S06-v1.1`、`S07-v1.1`、`S11-v1.1`、`S12-v1.1`、`S13-v1.1`（及既有高密度 `S01–S05`/`D01–D04`）。  
4. 冲突时以 **domain-truth 正文** 为准；QNA 与 formal 冲突必须回填 formal，而不是让实现读 QNA。

### 0.2b D 系 vs S 系裁决等级（Owner 强制 · 2026-08-12）

1. **所有 `D*` 真相层高于 `S*` 执行 Spec**：产品/宪法级裁决在 D；S 负责可编码执行台账且必须服从 D。  
2. 冲突时以 **最新 owner-frozen D 正文** 为准，并 **回填** 受影响 S；禁止 S 以局部细节反向覆盖 D。  
3. **D05-v1.0 frozen（`T-O-202..210`）**：LS-RAG 产品心智 SSOT；双通道/粒度0-1-2/promptA·B·C/ConstructToVectorizeGate/召回分账；直接约束 **S05–S10/S14** 与已冻 S06/S07/S11。
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

### 0.5 Python 技术栈：描述 · 要求 · 约束（Owner 强制 · 2026-08-12）

> **本节角色**：在 **index 层** 冻结 MKB 实现的语言/runtime/分层与依赖纪律，使脚手架、architecture tests 与重构计划有统一入口。  
> **不替代**：D03 目录宪法、D04 DDL、D06 运行拓扑、S11/S12/S13 执行台账中的细节算法与表结构。  
> **冲突裁决**：更细的物理/执行事实以对应 **domain-truth** 为准；本节只收 **栈级** 约束。实现选型若偏离「应当」项，须在重构计划或显式 change-request 中说明，不得静默突破「必须 / 禁止」。

#### 0.5.1 栈定位（描述）

| 维度 | 描述 |
|------|------|
| 产品形态 | **有状态 leaf-worker 单体**：一个 Python 应用、**一个发布单元**（`OD-06`）；内部模块清晰，**不**拆成多服务多发布物 |
| 语言 | **Python** 为实现语言；`legacy-python/` 仅退役参考（`OD-11`），**不得**作为依赖或复制目标 |
| 上游 | 以 `03-nano/orchestrator-core` 为已知首个调用方；MKB 自有 Contract，**不**被 03-nano 私有 DTO 反向污染 |
| 推理 | **adapter-first**：本地 **CUDA / vLLM**（默认经 `ai-mkb` 平面，D06）与可选外部推理，一律经 **S11 facade**，禁止业务层直连 |
| 数据 | **Turso / libSQL 方向** 单主库 + 本地对象盘；业务代码只依赖 **Ports**，驱动隔离在 `persistence` / `storage` |
| 真相 | 实现与 architecture tests 只服从 **`docs/baseline/domain-truth/*`**（及 D04 DDL）；禁止 QNA 第二 SSOT |

#### 0.5.2 语言与运行时（要求）

| ID | 级别 | 要求 |
|----|------|------|
| `PY-01` | **必须** | 实现语言为 **Python 3**；**v1 目标运行时下限 `Python ≥ 3.12`**（与当前工程机 3.12.x 对齐）。低于 3.12 不得作为发布基线。 |
| `PY-02` | **必须** | 单一可安装/可运行的应用根（推荐 `pyproject.toml` 管理依赖与入口）；**禁止** 为业务域再拆第二发布包冒充微服务。 |
| `PY-03` | **必须** | 类型纪律：**公共边界与跨层消息** 使用运行时可校验的 typed schema（落点 **`src/contracts/`**，D03）；非法 body **报错并抛弃**，禁止「裸 dict 当跨层合同」。 |
| `PY-04` | **应当** | 契约实现优先 **Pydantic v2**（或与之等价、可统一校验的 typed 层）；生成 OpenAPI / JSON Schema 须与 contracts 同源，禁止第二套手写 wire 模型。 |
| `PY-05` | **应当** | HTTP 面采用成熟 ASGI 栈（如 **FastAPI + Uvicorn/Hypercorn**）；路由仅暴露 S01/S15/S16 允许的 surface，不得默认挂载调试写盘 API。 |
| `PY-06` | **必须** | 进程内并发模型与 **S12 同进程多协程写** 兼容：默认 **单 OS 写权威进程** + asyncio/结构化并发承载 API、runtime engine、后台 loop；**禁止** 无协调多进程写同一 `mkb_primary` / `object_root`（D06/S12/S13）。 |
| `PY-07` | **必须** | 标准库与依赖声明可复现（lock 或等价 pin）；**禁止** 在生产路径依赖「未声明的全局 site-packages 魔法」。 |
| `PY-08` | **应当** | 测试：`pytest` + 分层 `tests/{unit,e2e,domain}`（D03）；architecture / import linter 进入 CI。 |

#### 0.5.3 仓库分层与 import 方向（要求 · 继承 D03）

| ID | 级别 | 要求 |
|----|------|------|
| `PY-10` | **必须** | 顶级/源码落点服从 **D03** 目标树：`api/`、`src/{runtime,contracts,services,persistence,storage,llm_adapters,workflows}`、`intake/`、`data/`、`tests/` 等。 |
| `PY-11` | **必须** | **依赖单向**：`api → runtime/services`；`services` **不得** import `api`；`contracts` **不得** import runtime/services/persistence/storage；`workflows/` **仅** 声明式定义，**禁止** claim/outbox/retry 实现。 |
| `PY-12` | **必须** | **`src/contracts/` = typed 协议唯一 SSOT**；禁止 services/runtime 平行维护「也算合同」的第二 schema 包。 |
| `PY-13` | **必须** | Domain/services **禁止** 直接 `import` Turso/libSQL/sqlite 驱动；**禁止** 对 `object_root` 裸 `pathlib` 写业务字节。 |
| `PY-14` | **必须** | Inference：**services 禁止** 直连 vLLM HTTP/SDK；只经 **`src/runtime/inference`（S11）**；adapter 仅在 `llm_adapters/`。 |
| `PY-15` | **必须** | **禁止** runtime import `legacy-family` / `legacy-python` / `legacy-specs` 作为依赖。 |
| `PY-16` | **必须** | Prompts：**正文 git 跟踪**（`data/prompts/**`）+ DB **仅 hash 指针**；运用路径 hash 校验 fail-closed（D03/S14）。 |

#### 0.5.4 持久化 · 对象 · 向量（约束）

| ID | 级别 | 约束 |
|----|------|------|
| `PY-20` | **必须** | 业务主库逻辑名 **`mkb_primary`**；**单可写 SSOT**；禁 DB-per-team、第二可写业务库、PostgreSQL 作为 v1 必选（S12/D04）。 |
| `PY-21` | **必须** | 默认启用 Turso **Concurrent Writes** 与 **Native Vector** 能力声明；不可用 → **readiness fail-loud**，禁止静默降级。 |
| `PY-22` | **必须** | 关系行形状服从 **D04** 表闭集；migration **单链**；checksum drift → not ready。 |
| `PY-23` | **必须** | 对象存储 v1 = **本地 filesystem** + `ObjectStorePort`（S13）；handle `mkbobj:v1:…`；bytes-first；禁公网 object CRUD。 |
| `PY-24` | **必须** | 向量存在 **≠** publication-valid **≠** serving；写侧 S08、发布 S09、检索 S10 dual-fence。 |
| `PY-25` | **禁止** | 把 queue ACK、log 行、HTTP 200、文件存在当作业务成功 SSOT。 |

#### 0.5.5 推理客户端与 `ai-mkb`（约束 · 继承 D06/S11）

| ID | 级别 | 约束 |
|----|------|------|
| `PY-30` | **必须** | 默认推理平面为专用容器/profile **`ai-mkb`**（OpenAI-compatible HTTP）；MKB 通过配置 `inference.vllm.base_url` 访问 **`:668` 和/或 `:669`**。 |
| `PY-31` | **必须** | 逻辑模型角色：embed **`qwen-vl-2b`**；LLM **`qwen35-a3b`**（多路 + MTP + 充足 KV，由部署保证）；经 S14 catalog/binding + S11 resolve。 |
| `PY-32` | **必须** | **G-10**：禁止 transport/429 驱动的 silent model/adapter/space swap。 |
| `PY-33` | **必须** | vLLM Bearer **≠** MKB InternalToken；两套凭证分账（S16/D06）。 |
| `PY-34` | **禁止** | 将「当前宿主机 GPU 被 ComfyUI 占用 / 668 未监听」写成实现 HARD 失败；资源由业主窗口调配（D06 非 blocker）。Live 推理测试仅可选 profile。 |
| `PY-35` | **应当** | HTTP 客户端对推理调用带超时、有界重试与并发闸（数值归 S11 配置键）；错误映射为稳定 `INFERENCE_*` / 邻域错误族。 |

#### 0.5.6 API · 安全 · 可观测（约束）

| ID | 级别 | 约束 |
|----|------|------|
| `PY-40` | **必须** | 业务 API：**InternalToken** valid/invalid 单轴；**401 先于任何资源读**；`team_uuid` 非授权凭证（S01/S16）。 |
| `PY-41` | **必须** | v1 异步结果 **polling only**；禁止默认 webhook/callback 设施（G-02）。 |
| `PY-42` | **必须** | `/live` **零** 外部依赖探测；`/ready` 聚合 migration/object/token/（可选）inference 等谓词；not ready → 拒新业务（S15）。 |
| `PY-43` | **必须** | 对外 envelope / log：**禁止** 泄漏 secret、绝对路径、stack、SQL、raw token（S16 redaction）。 |
| `PY-44` | **必须** | Metrics **低基数**；禁止以 `task_uuid` 等为默认 label 爆炸基数（S15）。 |
| `PY-45` | **应当** | 结构化日志 + 域事件同业务 TX 纪律（event 失败整 TX 失败；diagnostic 可 best-effort）。 |

#### 0.5.7 测试与架构门禁（要求）

| ID | 级别 | 要求 |
|----|------|------|
| `PY-50` | **必须** | Architecture tests 覆盖：import 方向、禁 driver/直连 vLLM、禁 legacy 依赖、contracts 非空且被边界调用。 |
| `PY-51` | **必须** | 验收 HARD 以 **domain-truth §6 + `D07` ledger** 为准；默认 CI **不**依赖 live GPU。 |
| `PY-52` | **必须** | 实现路径 **不得** 读取 `qna-truth/*` 作为执行配置或分支条件。 |
| `PY-53` | **应当** | 合同测试覆盖 Task Create/幂等/跨 team 隔离/retrieval 不建 Task 等 S01–S02/S10 基线。 |

#### 0.5.8 明确禁止的技术方向

| 禁止项 | 原因 |
|--------|------|
| 以 TypeScript/Cloudflare Worker 拓扑复刻多包 runtime 为 v1 | OD-06 / T-O-42 / D03 |
| 业务层直连 DB 驱动或对象盘路径 | D03/S12/S13 |
| 业务层直连 vLLM / 换模假隔离 | S11/D06 |
| PostgreSQL / 多写主库 / DB-per-team 作为 v1 默认 | S12 |
| R2/S3 作为 v1 对象 SSOT | S13 G-11 |
| 平台 UI、session、membership RBAC、billing 栈 | OD-01 |
| 把 MLX/macOS 叙事写回 v1 必选 | 已转向 CUDA 13 / 本地 vLLM |
| 未经理归档的「临时脚本」成为生产状态推进路径 | D01/S03 |

#### 0.5.9 推荐依赖轮廓（非完整 pin · 应当）

> 下列为 **方向性推荐**，便于脚手架对齐；**精确版本 pin 在实现仓 lockfile**，不在本索引冻结数字补丁号。

| 区域 | 推荐方向 |
|------|----------|
| 运行时 | CPython ≥ 3.12 |
| 包管理 | `pyproject.toml` + lock（uv/poetry/pip-tools 择一） |
| HTTP | FastAPI + ASGI server |
| 校验 | Pydantic v2（contracts） |
| 异步 | asyncio；后台任务同进程 loop |
| DB 适配 | libsql/Turso 官方或兼容客户端 **仅** `src/persistence` |
| 测试 | pytest、可选 hypothesis；import-linter / grimp 类架构门 |
| 观测 | Prometheus 文本 `/metrics`；可选 OTLP（默认关） |
| 推理客户端 | httpx/async OpenAI-compatible client，经 S11 封装 |

#### 0.5.10 验收勾稽

实现阶段至少证明：

1. `PY-01..03/06/10..16/20..25/30..33/40..44/50..52` 有自动化或 architecture 证据；  
2. D07 中 P0-CI 剖面 HARD 不因「未选 FastAPI」等应当项失败——**应当项偏离须文档化**，**必须项不可偏离**；  
3. 与 D03/D04/D06/S11–S13/S16 无未关闭冲突。

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
| `06` | `S06` | LS-RAG Structurizer | `P0` | `accepted` | `domain-truth/S06-lsrag-structurizer.md` | `D01, D02-v1.0, S03-S05, S07-S14` | `S06-v1.1`：**执行 SSOT**；E01–E10；自动路径+input freeze；generation账本；`mkb.structure_document@1`；`T-O-77..85`+`T-O-93..96`；QNA 非执行真相 |
| `07` | `S07` | LS-RAG Constructor | `P0` | `accepted` | `domain-truth/S07-lsrag-constructor.md` | `S04, S06, S11, S13-S14` | `S07-v1.1`：**执行 SSOT**；E01–E12；整包 dual-channel；ConstructionSchema；outbox；`T-O-126..140`；QNA 非执行真相 |
| `08` | `S08` | Embedding & Vectorization | `P0` | `accepted` | `domain-truth/S08-embedding-vectorization.md` | `D05, S07, S09, S11, S12–S14, D04` | `S08-v1.0`：**执行 SSOT**；E01–E12；`T-O-211..230`；ConstructGate；整包成败；幂等 upsert；Layer B 只抄写 S04；S09 handoff；QNA 非执行真相 |
| `09` | `S09` | Vector Index Lifecycle | `P0` | `accepted` | `domain-truth/S09-vector-index.md` | `S04, S08, S10, S12, S14, D04` | `S09-v1.0`：**执行 SSOT**；E01–E10；`T-O-231..246`；validate 对账；PublicationProof；ActiveIndexPointer；可服务谓词；metric/topk；QNA 非执行真相 |
| `10` | `S10` | LS-RAG Retrieval & Reranking | `P0` | `accepted` | `domain-truth/S10-lsrag-retrieval.md` | `S01, S04, S07-S09, S11, S12, S14` | `S10-v1.0`：**执行 SSOT**；E01–E10；`T-O-247..262`；dual-fence；Traceback/Inflation；rank；context-only；Bundle；QNA 非执行真相 |
| `11` | `S11` | Inference Runtime & Adapters | `P0` | `accepted` | `domain-truth/S11-inference-runtime.md` | `00, D03-D04, S06-S10, S14, S16` | `S11-v1.1`：**执行 SSOT**；E01–E11；Inference≠Adapter；全本地 vLLM；双层 filter；transport/闸/幂等；`T-O-180..201`；QNA 非执行真相 |
| `12` | `S12` | Turso Persistence | `P0` | `accepted` | `domain-truth/S12-turso-persistence.md` | `S01-S06, S09, S13, D04, D06` | `S12-v1.1`：**执行 SSOT**；E01–E11；单主库；TX-01..08；outbox/claim；CW+vector；**DDL 以 D04 为准**；`T-O-97..110`；QNA 非执行真相 |
| `13` | `S13` | Artifact & Object Storage | `P1` | `accepted` | `domain-truth/S13-artifact-storage.md` | `S04-S06, S12, S15-S16, D06` | `S13-v1.1`：**执行 SSOT**；E01–E11；local FS+Port；CAS；bytes-first；catalog/ref/GC；`T-O-111..125`；G-11 closed；QNA 非执行真相 |
| `14` | `S14` | Config, Prompt & Model Registry | `P1` | `accepted` | `domain-truth/S14-config-prompt-model-registry.md` | `00, S11, S15-S16, D03-D05` | `S14-v1.1`：**执行 SSOT**；E01–E11；`T-O-263..286`；L0–L4/registry bootstrap 写权威；QNA 证据层 |
| `15` | `S15` | Observability & Reliability | `P0` | `accepted` | `domain-truth/S15-observability-reliability.md` | `S01-S14, S16, D04` | `S15-v1.1`：**执行 SSOT**；E01–E11；`T-O-287..311`；retention/metric/alert/ready；`sec_token_loaded`；QNA 证据层 |
| `16` | `S16` | Security & Trust Boundary | `P0` | `accepted` | `domain-truth/S16-security-trust-boundary.md` | `S01-S15, D04` | `S16-v1.1`：**执行 SSOT**；E01–E12；`T-O-312..336`；token/egress/audit/redaction；QNA 证据层 |

### 1.2 跨系统基线与跨 Domain Truth 文档

| ID | 文档 | 状态 | 用途 |
|----|------|------|------|
| `00` | `spec-glossary.md` | `active / v2.9` | **S01–S16 + D08 calibrated**：既有治理词 + **ProviderOperation / CleanStrategy / FilterMeta / ContextMeta**；G-07/G-10/G-11 closed；G-01/G-12 deferred |
| `D01` | `domain-truth/D01-task-execution-process-flow.md` | `accepted / S06-calibrated` | `D01-v1.4`：三层状态；S06 generation非第四层runtime |
| `D02` | `domain-truth/D02-production-state-and-routing.md` | `frozen / v1.0 / S13-calibrated` | `T-O-86..92`；DR005/DR006 S06关闭；DR007 S12+S13部分关闭；generation/pointer/object physical |
| `D03` | `domain-truth/D03-repository-layout.md` | `accepted / v1.0 / T-O-141..159` | 仓库宪法：contracts typed 唯一SSOT；prompts git+hash；intake顶级；workflows≠runtime；Port 落点 |
| `D04` | `domain-truth/D04-turso-physical-schema.md` | `accepted / v1.1 / T-O-160..179+192..194` | **物理 schema**：55 表；+model_catalog/adapter_bindings/inference_invocations；embedding 隔离 |
| `D05` | `domain-truth/D05-layered-semantic-rag-handbook.md` | `frozen / v1.0 / T-O-202..210` + `T-O-352` | **LS-RAG handbook 已冻结**：双通道根本；粒度0/1/2；g=0 **summary** 必向量；construct门闩；promptA/B/C；失败引D01/S03；驱动S05–S10 |
| `D06` | `domain-truth/D06-runtime-topology.md` | `draft / owner-calibrated / v0.2` | **运行拓扑 SSOT**（原索引条目 `17` / `system-topology` **收敛至此**）：MKB 应用平面 + **`ai-mkb`** 推理平面；端口 **668/669**；角色 **`qwen-vl-2b` embed** + **`qwen35-a3b` LLM**（多路/MTP/充足 KV）；MKB 窗口停 ComfyUI；**宿主机资源业主调配，瞬时不符非 blocker**。**禁止**再维护 `docs/baseline/specs/17-system-topology.md` 第二源 |
| `D07` | `domain-truth/D07-v1-acceptance-truth.md` | `draft / owner-review / v0.5` | **验收 HARD 台账**：全局门闩 G01–G14、release 剖面、一域一槽；`18` 只做签署。v0.5 载入 **D08-A01..A20** 与 E2E-16..18 |
| `D08` | `domain-truth/D08-legacy-capabilities-migration.md` | `draft / owner-review / v0.1` | **legacy 四域能力 → `intake/` 拓扑**：chinatax/domain/REA operation 闭集；web/pdf/doc strategy；D03 §4.3 clean reopen；D04 三表 proposed。**不**恢复 branch taxonomy 或 Worker 栈 |
| `18` | `specs/18-acceptance-truth-freeze.md` | `pending` | 汇总不变量、验收矩阵、owner-gate closure 和冻结签署 |

> **已废止槽位**：历史编号 **`17` System Topology** 不再作为独立 pending 文档；职责由 **`D06`** 承接。文中若仍见旧称 `17`，一律读作 **D06**（直至各邻域 header 完成 D06-calibrated 回填）。

### 1.3 Owner 方向与子系统覆盖

| Owner 方向 | 命中子系统 | 覆盖说明 |
|------------|------------|----------|
| Turso 替换原 SQLite 方向 | `S09, S12` | 分离关系持久化和向量索引；先验证再冻结驱动与部署方式 |
| 本地 vLLM + 外部服务 | `S06-S08, S10-S11, S14, D06` | 能力面 adapter 归 S11；**运行拓扑默认 `ai-mkb` @ 668/669、角色 `qwen-vl-2b`/`qwen35-a3b` 归 D06** |
| leaf-worker 与 skill-worker 注册准备 | `S01-S03, S15-S16` | 首版 standalone；定义能力、任务、健康、token、状态和 polling；未来以 adapter 接入 skill-worker |
| 重做 CRUD 与 workflow | `S02-S05, S12-S13` | 从 task intent 与内部状态机重建，不沿用平台 API |
| Task / Execution / Process 三层切分 | `D01, S01-S05, S08-S09, S12, S15` | Task 只做外部 ACK/CRUD/aggregate；Execution 是 durable run；Process 是 RAG-specific 工序；single/scatter 共用同一入口 |
| 从第一天按 LS-RAG 执行 | `S04, S06-S10, S14-S15` | layered schema、双通道、坐标回溯和质量指标贯穿知识全生命周期 |
| 单体应用、废弃 packages 注册 | `D06` + 全部 | 组织/部署/进程与 `ai-mkb` 推理边归 **D06**；不取消领域和 adapter 边界 |

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
| 跨系统基线 spec | `2` | scope/glossary（`00`）、acceptance/truth freeze（`18`）；**运行拓扑不在此列** |
| 跨 Domain architecture truth | `8` | `D01` Flow；`D02` 状态宪法；`D03` 仓库布局；`D04` 物理 schema；`D05` LS-RAG handbook；**`D06` Runtime Topology**（原 `17`）；**`D07` 验收台账**；**`D08` legacy 四域能力迁移** |
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
| `smind-skill-clean-universal` | `S05, S11, S13, D08` | input/clean/Artifact 和 browser/PDF **strategy 分叉**；D08 写成可勾选 CleanStrategy |
| `smind-skill-clean-dedicated-apis` | `S04, S05, D08` | 三 provider operation、atomic key、content/meta digest；D08 吸收 parser/schema，删除隧道/cookie |
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
- **下游约束**：`S02/S03/S04/S12/S15/S16/D06` 必须继承 S01 与 D01 Truth ID；偏离必须同时 reopen 受影响真相。

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
- **D08 校准（2026-08-13）**：四域 **operation/strategy 闭集与 `intake/` 树** 归 `D08-v0.1`；本域 kind/preflight/gate 不变。registered_api HARD（A09–A13）以 D08 parser/双 digest 为证据；通道空壳不构成关闭。

### 3.6 `S06` LS-RAG Structurizer

- **状态**：`accepted / S06-v1.1`；**执行 SSOT = domain-truth only**（E01–E10）；QNA`qna-truth/S06.md`仅证据（`T-O-77..85`+`T-O-93..96`）；全系统尚未 frozen。
- **定位**：original structure compiler + grounded block projection；全自动生产路径；完整HITL out-of-scope。
- **已冻结**：ProcessCommand+input digest freeze；GenerationArtifact/Invocation/per-type current；StructureSchema registry；kernel/extension/repair；`structure_document`树+anchors+generation-local coordinates；分账`retrieval_block_projection`；首版`mkb.structure_document@1` node_kind闭集；仅自动retry；用户generation精修defer。
- **明确不做**：chunker/二次clean/summary worker；RAG内patch；GenerationCommit业务身份；legacy SMCP/R2/flat wire兼容。
- **下游约束**：S07消费structure+projection并产summary；S08–S10必须generation-scoped坐标；S12交付generation/schema DDL；readiness前bootstrap schema。
- **完成回填**：已发布正式Spec与20项验收；D01/D02/S01–S05/glossary/index已S06-calibrated。

### 3.7 `S07` LS-RAG Constructor

- **状态**：`accepted / S07-v1.1`；**执行 SSOT = domain-truth only**（E01–E12）；QNA `qna-truth/S07.md` 仅证据（`T-O-126..140`）；**Round 4 waived**。
- **范围**：meta fusion、summary、`content_full`、original/summary 双通道、filter metadata 和幂等构造。
- **已冻**：单文档 Execution 整包 dual-channel；projection 1:1；ConstructionSchema 多成员 artifact；整包 summary；S04 filter 权威；content_full 配方+outbox；`full_construct`/`metadata_refresh`；Typed Command/Outcome；readiness/预算/错误/scatter/OOS；v1 取消 original-only 成功。
- **关键不变量**：original 与 summary 共享 generation-scoped 坐标；summary 可 traceback original；整包 full-valid 或失败；success ≠ serving。
- **完成回填**：Construction Unit Schema、双通道规则、lineage 与 glossary v1.8 已登记。
- **证据授权**：仅 baseline + `legacy-family`；禁止 `legacy-specs` / `legacy-python`。

### 3.8 `S08` Embedding & Vectorization

- **状态**：`accepted / S08-v1.0`；**执行 SSOT = domain-truth only**（E01–E12）；QNA `qna-truth/S08.md` 仅证据（`T-O-211..230`）；**Round 4 waived**；全系统尚未 frozen。
- **权威 Spec**：`docs/baseline/domain-truth/S08-embedding-vectorization.md`。
- **定位**：ConstructToVectorizeGate 之后 document-side 向量写侧；`lsrag.vectorize` + mode；整包 required-set 成败；ContentFull 对账；有界批+渐进幂等 upsert；purge soft-delete；original HARD；Layer B **只抄写 S04**；S09 handoff。
- **明确不做**：serving/PublicationProof；S04 facet map 产品；ANN 算法；公网 vector CRUD；vec_process/外置 Vectorize SSOT。
- **关键不变量**：存在≠serving；outbox 非成功；半写不可 publication；S08 零 wire map。
- **完成回填**：formal Spec 已发布；S03/S07/S09/glossary 指针可随后校准。

### 3.9 `S09` Vector Index Lifecycle

- **状态**：`accepted / S09-v1.0`；**执行 SSOT = domain-truth only**（E01–E10）；QNA `qna-truth/S09.md` 仅证据（`T-O-231..246`）。
- **定位**：S08 写证明之后的 publication / IndexGeneration / 可服务谓词 / invalidation / metric·topk 默认；不拥有向量写编排与 S04 serving CAS。
- **已冻结**：`index.validate_publication` 整包对账；PublicationProofV1；ActiveIndexPointer；rebuild 五段；publication-valid 谓词；cosine 默认；topK default/cap；错误/readiness/容量/OOS。
- **关键不变量**：存在≠serving；Handoff≠Proof；禁仅 ANN 返回；S09 不写 serving_revision。
- **完成回填**：formal Spec 已发布；D04 additive pointer/proof 表；S03/S04/S08/S10/glossary 校准。

### 3.10 `S10` LS-RAG Retrieval & Reranking

- **状态**：`accepted / S10-v1.0`；**执行 SSOT = domain-truth only**（E01–E10）；QNA `qna-truth/S10.md` 仅证据（`T-O-247..262`）。
- **定位**：同步 `retrieval.search`；dual-fence 应用；Traceback/Inflation/Rerank/Pack；**v1 context-only**。
- **已冻结**：硬管道；return_k=10/recall_k=20/threshold=0.0；rerank ON 诚实 fallback；pack 预算；`RETRIEVE_*`；G-07 closed。
- **关键不变量**：禁仅 ANN 返回；Traceback 可观测；无 raw vector；无 answer v1；无 Task 污染。
- **完成回填**：formal Spec 已发布；G-07 closed；glossary/S09 分账对齐。

### 3.11 `S11` Inference Runtime & Adapters

- **状态**：`accepted / S11-v1.1`；**执行 SSOT = domain-truth only**（E01–E11）；QNA `qna-truth/S11.md` 仅证据（`T-O-180..201`）。
- **定位**：leaf-worker 内模型调用门面与 adapter；不拥有 Process 状态机 / ANN / prompt 正文。
- **已冻结**：Inference≠Adapter；v1 全本地 vLLM；四能力 facade；catalog/bindings/invocations；Layer A/B filter；transport 退避；并发闸；vectorize 无 WAL 幂等；readiness。
- **关键不变量**：services 禁 import adapters；调用成功≠业务成功；禁 transport 驱动换模型。
- **完成回填**：v1.1 执行台账升格；G-10 对 v1 transport 关闭。

### 3.12 `S12` Turso Persistence

- **状态**：`accepted / S12-v1.1`；**执行 SSOT = domain-truth only**（E01–E11）+ **DDL = D04**；QNA `qna-truth/S12.md` 仅证据（`T-O-97..110`）。
- **定位**：关系业务 SSOT 的持久化与事务域；不拥有业务状态机。
- **已冻结**：单主库；Ports；TX-01..08；outbox 投递环；claim/fence/lease；migration+readiness；CW+Native Vector 默认开；bytes-first；vector 派生最小合同；拒 PG。
- **关键不变量**：queue/文件/向量/view 不是业务成功；domain 不直连 driver；CAS fail-loud。
- **完成回填**：v1.1 执行台账升格；G-08 closed。

### 3.13 `S13` Artifact & Object Storage

- **状态**：`accepted / S13-v1.1`；**执行 SSOT = domain-truth only**（E01–E11）；QNA `qna-truth/S13.md` 仅证据（`T-O-111..125`）。
- **定位**：对象字节 substrate 域；不拥有业务状态机；存在≠成功。
- **已冻结**：v1 本地 Port；`mkbobj:v1`；team CAS；bytes-first；catalog/ref/purpose；verify-on-read；GC grace+fence；identity readiness；backup 协议；typed errors；无公网 object API。
- **关键不变量**：不可变+SHA-256；live ref 保护；orphan≠missing；domain 禁 path。
- **完成回填**：v1.1 执行台账升格；**G-11 closed**。

### 3.14 `S14` Config, Prompt & Model Registry

- **状态**：`accepted / S14-v1.1`；**执行 SSOT = domain-truth only**（E01–E11）；QNA `qna-truth/S14.md` 仅证据（`T-O-263..286`）；全系统尚未 frozen。
- **权威 Spec**：`docs/baseline/domain-truth/S14-config-prompt-model-registry.md`。
- **定位**：Config / Prompt / Model Registry **产品治理域**；回答配置分层、热更新、一致快照、Task override 白名单与模型产物复现；**不**拥有 Process 状态机、Inference transport、ANN、prompt 正文字节、Workflow 七表 SSOT、密钥生命周期、event retention 数值。
- **已冻结**：L0→L1→L2→L3→L4 分层；`resolve_for_new_execution` 一次 materialize → 不可变 `ConfigSnapshot`/`config_snapshot_digest`；binding-affecting 仅 future；Ops-only 可 last-good reload；override 窄白名单 + 成功写 `config.override_applied` / 拒绝写 security_audit；**RegistryBootstrap 写权威** vs **S11-E03 runtime resolve** 单一矩阵；Semantic 进 digest / Ops（`security.*`/`obs.*`）不进；feature_flags git + `flag_bundle_digest` 默认 OFF；ProvenanceEnvelope 最小字段；promptA/B/C + aux 命名空间；**无** latest/@champion 产品解析层；typed `CONFIG_*` 错误；readiness 含 registry_bootstrap/prompt_hash。
- **关键不变量**：每个模型产物可追溯 **model + prompt + schema + params**；log ≠ 业务 SSOT；Process 禁止再 merge L0–L3；禁 silent 换 model/adapter（G-10）；禁 agent 写 registry（G-12 deferred）；禁 DB 第二份 prompt 正文。
- **邻域交接**：D03 正文 git；D04/S11 表与 resolve；D05 prompt 三身份；S03 workflow 只读视图；S15 metric 目录收录 `mkb_registry_*`/`mkb_config_*`；S16 secret 值/生命周期。
- **完成回填**：formal `S14-v1.1` + 对抗评审矩阵；`T-O-263..286`；G-10/G-13/G-14 继承 closed；G-12 deferred；全局下一空号 **T-O-337**。

### 3.15 `S15` Observability & Reliability

- **状态**：`accepted / S15-v1.1`；**执行 SSOT = domain-truth only**（E01–E11）；QNA `qna-truth/S15.md` 仅证据（`T-O-287..311`）；全系统尚未 frozen。
- **权威 Spec**：`docs/baseline/domain-truth/S15-observability-reliability.md`。
- **定位**：事件保留、低基数 metric 导出、告警 runbook、ready/live、trace 关联、dead-letter 可观测、repair evidence、operator 只读面；**不**拥有业务 CAS/状态机、DDL 表名闭集、outbox 投递环、ANN 算法、对象 GC 协议、密钥/trust 主责。
- **已冻结**：三表 retention（events 90d / diagnostic 14d / security_audit 180d hot）+ 批 DELETE + pre-delete export fail 禁删；metric 闭集目录（含 S14 registry/config 与 S16 sec_*，未收录禁 export）；必告警闭集（含 `ALERT_OUTBOX_DEAD`/`ALERT_READINESS_FALSE`/`ALERT_SEC_*` 等）；`/live` 禁依赖 vs `/ready` 聚合（含 **`sec_token_loaded`**）→ 503；root `trace_uuid` 不替换；无外部 repair 写面；ObservabilityReadPort 内网+token+team 过滤；dead outbox 可查+告警，redrive 仅 S12+审计；typed `OBS_*`；redaction **sync-from S16-T056**；BackupScheduler 唯一 cron 调 S13。
- **关键不变量**：`team_uuid`/`task_uuid`/`trace_uuid` 贯穿业务域事件；**失败不能只存在于日志字符串**；domain_events 与业务 mutation 同 TX；events 非 CAS SSOT；禁业务 webhook 默认；禁公网匿名 operator。
- **完成回填**：formal `S15-v1.1`；`T-O-287..311`；与 S14/S16 钩子目录双向钉死。

### 3.16 `S16` Security & Trust Boundary

- **状态**：`accepted / S16-v1.1`；**执行 SSOT = domain-truth only**（E01–E12）；QNA `qna-truth/S16.md` 仅证据（`T-O-312..336`）；全系统尚未 frozen。
- **权威 Spec**：`docs/baseline/domain-truth/S16-security-trust-boundary.md`。
- **定位**：内部 token、轮换、EndpointClass、限流、replay 边界声明、egress/SSRF 宪法、secret 生命周期、path 消毒、debug 隔离、供应链围栏、security_audit 写语义、redaction 规则权威、威胁模型；**不**拥有业务状态机、DDL、retention 天数、ANN、object CAS 布局、prompt registry、完整 IdP/OAuth/RBAC 平台。
- **已冻结**：ops mint shared-secret；at-rest 仅指纹；timing-safe；主 header Bearer（兼容 `X-MKB-Internal-Token`）；ActiveTokenSet N=2 dual-active + 24h 重叠 + 吊销 audit；EndpointClass（Business/Operator/Repair 必 token；Live 可免；Ready 默认可免；Metrics 禁公网匿名）；限流 600/min token + 120/min IP；限流故障 degraded 但鉴权 fail-closed；业务防重放权威 = S01/S02 幂等；egress fail-closed + DNS→IP + redirect≤3 硬拒私网/metadata；SecretSlot env(+file)；生产 debug OFF；SupplyFence binding-only + G-10；`SEC_*` + audit 采样 + redaction 闭集。
- **关键不变量**：**简单认证 ≠ 无安全边界**；**`team_uuid` 绝不是授权凭证**；invalid token 先于任何资源读；禁 open proxy；禁 silent model swap；禁 log/audit 明文 token/secret。
- **完成回填**：formal `S16-v1.1`；`T-O-312..336`；G-02/G-10/G-29 closed 继承；G-12 deferred；与 S15 readiness/alert/retention 交叉合同完整。

---

## 4. Owner-Gate Registry

> 本表只登记尚未冻结的关键裁决。详细 spec 中发现新 gate 时，必须先在此分配 ID；裁决后记录结论并更新受影响 spec。

| Gate ID | 决策点 | 影响范围 | 候选方向 | 状态 | 裁决/落点 |
|---------|--------|----------|----------|------|-----------|
| `G-01` | Skill-worker发现与注册方式 | `S01, D06` | 主动注册 / 上游静态配置 / 混合 | `deferred` | `S01-v1.5`：首版standalone，不注册；未来只通过防腐adapter reopen；运行拓扑见 D06 |
| `G-02` | Task结果交付方式 | `S01-S03, S15-S16` | 上游轮询 / callback / 双支持 | `closed` | `S01-v1.5/S02-v1.3`：首版polling；Task status/readiness/action_required分账；无webhook/callback或直接Execution/Process写面 |
| `G-03` | Workflow Program语义宪法 | `S03-S09, S12-S15` | topology清单 / 多平面声明式RAG程序 / 任意代码自动化 | `closed` | `T-O-12`：采用六平面端到端Contract；BindingSource声明规则，Engine注入runtime facts；topology只是Control子平面 |
| `G-04` | 首版 Intake 范围 | `S04-S05, S13` | text/object only / URL / PDF/browser/API/OCR/Vision | `closed` | `T-O-49..51 / S05-v1.1`：完整能力面纳入v1；source kind只有inline/local/HTTP/registered API，browser/PDF/OCR/Vision/scatter为正交capability/cardinality |
| `G-05` | parent-child/scatter首版范围 | `D01, S03-S07` | 首版支持 / schema预留后延 | `closed` | `D01-v1.4/S04-v1.2/S05-v1.1`：scatter为一等能力；Task→root→0..N child Executions；集合truth为Snapshot/Membership/ChangeSet，root/child preflight/gate原生支持 |
| `G-06` | MKB-native LS-RAG canonical structure形状 | `S06-S10` | legacy flat layered array / single-root ordered typed tree + deterministic block projection / blocks-only | `closed / S06-v1.0` | `T-O-94..95`：typed ordered tree + anchors + generation-local coords + 分账projection；`mkb.structure_document@1`；legacy flat排除 |
| `G-07` | Retrieval 是否承担 answer generation | `S01-S02, S10-S11` | 只返回 context / 可选生成任务 | `closed / S10-v1.0` | `T-O-260`：v1 **context-only**；不承担 answer；未来须显式 reopen |
| `G-08` | Turso 运行和进程模型 | `S03, S09, S12, D06` | 单进程 embedded / 多进程 / remote-sync | `closed / S12-v1.0` | `T-O-102/107..109`：单主库+同进程+CW；outbox/claim；扩写defer；部署合成见 D06 |
| `G-09` | 首版向量索引 | `S08-S10, S12` | Turso exact / 独立 ANN / 分阶段 | `closed foundation / S09-v1.0` | `T-O-107/110`+`T-O-231..246`：同库 ANN；publication/代数/谓词/metric·topk 默认已冻；精确商业 benchmark 曲线可与 S15 共治 |
| `G-10` | 模型 fallback 语义 | `S06-S08, S10-S11, S14, S16` | 禁止自动 fallback / 受控 fallback | `closed for v1 transport` | `S11-v1.1`+`S14-v1.1`+`S16-v1.1`：**禁** transport/429/registry/override/flag 驱动 silent 换 model/adapter（`T-O-199`/`T-O-267`/`T-O-335`）；跨模型须显式 binding/reopen |
| `G-11` | Asset storage首版backend | `S05-S07, S12-S13, D06` | 本地filesystem / S3-compatible | `closed / S13-v1.1` | `T-O-117`：v1=本地盘+Port；R2 因成本 defer；HF Xet 非 SSOT；object_root 挂载合成见 D06 |
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
| `G-28` | Greenfield bootstrap、MKB schema evolution与S04 acceptance | `S04, S12-S16, D06, 18` | 隐式代码默认 / deterministic schema+RegistryManifest+readiness/acceptance gate / legacy migration/cutover | `closed` | `T-O-47..48 / S04-v1.2`：empty-DB bootstrap、forward MKB migrations、drift fail-loud、完整acceptance与零legacy dependency |
| `G-29` | MKB 与 legacy-family 的应用边界 | `00, S01-S16, D06, 18` | compatibility/migration / reference-anchor only | `closed` | `T-O-42`：完全独立；无 importer、dual-read、identity mapping、cutover/rollback 或 runtime/schema/API/acceptance dependency |
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
  1. `00`、`D01–D08`、`S01–S16`、`18` 全部达到 `accepted`（**运行拓扑以 D06 为准**；**验收 HARD 以 D07 为准**；**四域能力以 D08 为准**；历史编号 `17` 已废止，不得再单列 pending）；
  2. §4 所有 gate 已裁决或被明确移出本次范围；
  3. 所有跨系统 ID、状态、错误、版本、删除和审计语义完成对账；
  4. LS-RAG golden scenarios 完整覆盖 summary traceback；
  5. Turso、向量索引和本地模型的关键假设有可复现 spike/benchmark 证据（**宿主瞬时资源以 D06 非 blocker 纪律解释**）；
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
| S06 Structurizer formal Spec | `S06-v1.0 / T-O-77..85`+`T-O-93..96` | 自动路径、generation账本、structure/projection contract、首版schema草稿、仅自动retry；HITL完整管线out-of-scope；不得重问 |
| S12 Turso Persistence formal Spec | `S12-v1.1 / T-O-97..110` | 单主库、TX矩阵、outbox/claim、migration/readiness、CW+vector默认开、模块化schema、E 包执行台账；不得重问拓扑/PG/第二SSOT；QNA 非执行真相 |
| 无 UI、无复杂平台鉴权 | 业主裁决 | `S16` 只设计内部最小安全边界 |
| Python 单体、废弃过细 packages | 业主裁决 | 内部模块化，但不建立多个 distribution |
| CUDA/vLLM + 外部服务 adapter | 业主裁决 | `S11` 设计能力接口，不再回到 MLX 叙事 |
| 当前 Python 实现已归档 | 当前仓库 | 只作历史证据，不继续增量开发 |
| TypeScript legacy 已保留 | `legacy-family/` | 用于行为考古，禁止成为运行依赖 |
| S08 Embedding formal Spec | `S08-v1.0 / T-O-211..230` | ConstructGate、整包成败、幂等 upsert、Layer B 抄写、S09 handoff；不得重问 |
| S09 Vector Index formal Spec | `S09-v1.0 / T-O-231..246` | validate/PublicationProof/ActiveIndexPointer/可服务谓词/metric·topk；不得重问 |
| S10 Retrieval formal Spec | `S10-v1.0 / T-O-247..262` | dual-fence、Traceback/Inflation、context-only、Bundle；G-07 closed；不得重问 |
| S11 Inference formal Spec | `S11-v1.1 / T-O-180..201` | Inference≠Adapter；全本地 vLLM；resolve 权威；G-10 closed for v1 transport |
| S13 Artifact formal Spec | `S13-v1.1 / T-O-111..125` | local CAS/Port/GC；G-11 closed |
| S14 Config/Prompt/Model Registry | `S14-v1.1 / T-O-263..286` | L0–L4、RegistryBootstrap 写权威、override/provenance；不得重问 |
| S15 Observability & Reliability | `S15-v1.1 / T-O-287..311` | retention/metric/alert/ready/operator；log≠SSOT；不得重问 |
| S16 Security & Trust Boundary | `S16-v1.1 / T-O-312..336` | token/egress/audit/redaction/SupplyFence；team≠credential；不得重问 |

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

当跨系统/cross-domain 与子系统真相文档（**`00 + D01–D08 + S01–S16 + 18`**）全部达到 `accepted`：

1. 生成 `18-acceptance-truth-freeze.md` 的最终矩阵；
2. 对账所有 contract、ID、状态机、error、event 和 version；
3. 关闭或显式延期所有 owner-gate；
4. 将本索引置为 `review-ready index`；
5. 由业主完成最终审阅；
6. 将本索引和全部 spec 统一标记为 `frozen`；
7. 记录 truth version/tag；
8. 从冻结 truth layer 生成重构计划，禁止用实施需要反向偷偷修改 spec。

> **计数说明**：历史公式曾写 `00+D01+D02+S01–S16+17+18 = 21`（未单列当时尚未存在的 D03–D05）。现以 **`00 + D01–D08 + S01–S16 + 18`** 为完整集合；**`17` 不再计数**。

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
- S06 Formal Spec：`docs/baseline/domain-truth/S06-lsrag-structurizer.md`
- S06 Progressive QNA：`docs/baseline/qna-truth/S06.md`
- S14 Formal Spec：`docs/baseline/domain-truth/S14-config-prompt-model-registry.md`
- S15 Formal Spec：`docs/baseline/domain-truth/S15-observability-reliability.md`
- S16 Formal Spec：`docs/baseline/domain-truth/S16-security-trust-boundary.md`
- S14–S16 战役审计：`docs/baseline/qna-truth/_s14-s16-campaign-audit.md`
- **运行拓扑（D06 · 原 `17`）**：`docs/baseline/domain-truth/D06-runtime-topology.md`（`D06-v0.2-draft`；**禁止**再创建 `docs/baseline/specs/17-system-topology.md`）
- **验收台账（D07）**：`docs/baseline/domain-truth/D07-v1-acceptance-truth.md`（`D07-v0.5-draft`）
- **四域能力迁移（D08）**：`docs/baseline/domain-truth/D08-legacy-capabilities-migration.md`（`D08-v0.1-draft`）
- Truth freeze：`docs/baseline/specs/18-acceptance-truth-freeze.md`（待创建）

---

## 附录 A · Truth Freeze Checklist

| 检查项 | 状态 | 证据/备注 |
|--------|------|-----------|
| `00` Scope & Glossary accepted | `accepted / active v2.9` | S01–S16 + D08 词表已登记；非 frozen truth index 入口（待 D06/D07/D08 accepted + `18`） |
| `D01` Task/Execution/Process Flow accepted | `accepted / S06-calibrated` | D01-v1.4 + S06 generation非第四层runtime |
| `D02` Production State Constitution & Ledger | `frozen / v1.0 / S06-calibrated` | `T-O-86..92`；S06 DR005/DR006已回填 |
| `D03` Repository Layout | `accepted / v1.0` | `T-O-141..159` |
| `D04` Turso Physical Schema | `accepted / v1.1` | `T-O-160..179+192..194` |
| `D05` LS-RAG Handbook | `frozen / v1.0` | `T-O-202..210` |
| `D06` Runtime Topology | `draft / owner-calibrated / v0.2` | **原 `17` 收敛**；`ai-mkb`+668/669+模型角色；**待 owner freeze → accepted** |
| `D07` V1 Acceptance Truth | `draft / owner-review / v0.5` | HARD 台账；已载入 D08 槽；**待 owner freeze → accepted** |
| `D08` Legacy Capabilities Migration | `draft / owner-review / v0.1` | 四域闭集 + intake 树 + D04 proposed；**待 owner freeze** |
| `S01-S16` 全部 accepted | `met` | S01–S16 domain-truth accepted（S14–S16 v1.1 对抗评审校准） |
| ~~`17` System Topology~~ | **`superseded by D06`** | **不再**维护 `specs/17-system-topology.md` |
| `18` Acceptance Matrix accepted | `pending` | 全量验收矩阵与 truth freeze 签署尚未编写 |
| Owner-gate 全部 closed/deferred | `partial` | G-01/G-12 **deferred**；其余 G-02..G-11/G-13..G-35 **closed**（或 closed foundation）；无 open owner-gate |
| 跨 spec ID 对账完成 | `pending / residual` | T-O 连续至 336；event_type 闭集/错误族全表对账归 18 |
| 跨 spec 状态机对账完成 | `D02 baseline + S01-S16 calibrated` | D01/S01–S16 及治理/观测/安全交接已校准；全系统 truth layer 仍未 frozen |
| 错误、事件、版本语义对账完成 | `partial` | S14 `CONFIG_*` / S15 `OBS_*` / S16 `SEC_*` 已域内冻结；跨域 matrix 归 18 |
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
| `v0.25` | `2026-08-11` | `MKB owner + Codex` | Owner接受S06 Q4–Q6推荐B；冻结`T-O-93..96`；发布`S06-v1.0`正式Spec与`mkb.structure_document@1`草稿；关闭G-06；回填D01/D02/S01–S05/glossary v1.5；S06进入accepted。 |
| `v0.26` | `2026-08-11` | `MKB owner + Codex` | 发布`S12-v1.0`正式Spec（`T-O-97..110`）；关闭G-08；G-09 partial（同库vector合同）；回填D01–S06/D02/glossary v1.6；S12 accepted。 |
| `v0.27` | `2026-08-11` | `MKB owner + Codex` | 接受 S13-v1.0：冻结 local object store、CAS/bytes-first/catalog/ref/GC、`T-O-111..125`；关闭 G-11；登记 S13 accepted 与 glossary v1.7。 |
| `v0.28` | `2026-08-11` | `MKB owner + Codex` | 启动 S07 progressive QNA（`qna-truth/S07.md v0.1`）：后被 Owner 拒绝（越权引用 legacy-specs/legacy-python）。 |
| `v0.29` | `2026-08-11` | `MKB owner + Codex` | S07 QNA **整版重写**为 `v0.2`：证据授权收紧为 baseline + `legacy-family` only；剔除全部未授权树；重述 `T-O-126..131` 与 Round 1 Q1–Q3（推荐 Q1=B / Q2=C / Q3=C）；S07 保持 `designing`。 |
| `v0.30` | `2026-08-11` | `MKB owner + Codex` | Owner 接受 S07 Q1–Q3 推荐；冻结 `T-O-132..134`；中场评估 I；注入 Round 2 Q4–Q6（`qna-truth/S07.md v0.3`）。 |
| `v0.31` | `2026-08-11` | `MKB owner + Codex` | Owner 接受 S07 Q4–Q6 推荐；冻结 `T-O-135..137`；中场评估 II；注入 Round 3 Q7–Q9（`qna-truth/S07.md v0.4`）。 |
| `v0.32` | `2026-08-11` | `MKB owner + Codex` | S07 Q7 **按 Owner 产品模型重写并冻结** `T-O-138`：单文档 Execution、整包 artifact 二元成败、一次 summary 全部粒度、S03 重试+显性失败后续；收窄 T-O-133/136 成功面（`qna-truth/S07.md v0.5`）。 |
| `v0.33` | `2026-08-11` | `MKB owner + Codex` | Owner 接受 S07 Q7–Q9；冻结 `T-O-138..140`；中场评估 III；**Round 4 waived**；QNA `v1.0` 收口待 formal Spec。 |
| `v0.34` | `2026-08-11` | `MKB owner + Codex` | 发布 `S07-v1.0` formal Spec（`T-O-126..140`）；S07 进入 accepted；glossary 升至 v1.8；完成 S06/S03/D01 等 S07-calibrated 回填与真相层全局检查。 |
| `v0.35` | `2026-08-11` | `MKB owner + Codex` | 登记 D03 仓库目录宪法草稿 `D03-repository-layout.md v0.1`（owner-review）：intake 顶级、Workflow≠Runtime、persistence/storage、prompts git、tests/、public/。 |
| `v0.36` | `2026-08-11` | `MKB owner + Codex` | D03 升 `v0.2-draft`：业主纠正 dataclass = Zod 级强制 typed 协议层（业务流转/内部 RPC/通信标准）；非空 DTO 目录。 |
| `v0.37` | `2026-08-11` | `MKB owner + Codex` | D03 升 `v0.3-draft`：更名 contracts；SMCP 双层 schema 考古；按域分册；任何消息体必校验、非法报错抛弃。 |
| `v0.38` | `2026-08-11` | `MKB owner + Codex` | D03 升 `v0.4-draft`：contracts 为 typed 唯一 SSOT；prompts git 正文+DB hash 指针；收紧消息体范围与 Workflow I/O；index 阶段纪律有限例外说明。 |
| `v0.39` | `2026-08-11` | `MKB owner + Codex` | **冻结 D03-v1.0**：`T-O-141..159`；仓库目录宪法进入真相层；glossary v1.9；阶段纪律有限例外（仅 D03）正式登记。 |
| `v0.40` | `2026-08-11` | `MKB owner + Codex` | **冻结 D04-v1.0**：`T-O-160..179`；Turso 物理表/索引/VIEW 真相层（52 表、可观测三表、最终向量 F32+ANN）；glossary v2.0；S12/S09/S15 分账回填；阶段有限例外扩至 D03+D04。 |
| `v0.41` | `2026-08-12` | `MKB owner + Codex` | S11 Round 1 冻结 `T-O-189..193`；D04-v1.1 增 3 表至 55（catalog/bindings/invocations）+ embedding 隔离；S11 Round 2 Q4–Q6 open。 |
| `v0.42` | `2026-08-12` | `MKB owner + Codex` | S11 Round 2 冻结 `T-O-195..198`；Q6 双层 filter（空间隔离 vs 业务 team/intake/上游 facet）；D04-v1.1-cal；建议 R3 waived。 |
| `v0.43` | `2026-08-12` | `MKB owner + Codex` | S11 Round 3 冻结 `T-O-199..201`（transport 退避、inference 闸、无 WAL 幂等重放）；QNA v1.0 locked；**Round 4 waived**；待 formal Spec。 |
| `v0.44` | `2026-08-12` | `MKB owner + Codex` | 发布 **S11-v1.0** formal Spec（`T-O-180..201`）；S11 accepted；G-10 部分关闭；D03/S03/S06/S07/glossary 校准；family 审计。 |
| `v0.45` | `2026-08-12` | `MKB owner + Codex` | **Owner 强制：domain-truth 唯一执行 SSOT**。升格 `S06-v1.1`/`S07-v1.1`/`S11-v1.1`/`S12-v1.1`/`S13-v1.1`（E 包执行台账从 QNA 并入）；登记 index §0.2a；QNA 降为证据层 only，禁止实现依赖 QNA。 |
| `v0.46` | `2026-08-12` | `MKB owner + Codex` | 启动 **D05 LS-RAG handbook** `v0.1-draft`：legacy-family 全链考古；双通道/多粒度向量通道/反向召回规范草案；OG-D05-01..06 owner-gate；登记 §0.2b D>S 裁决等级。 |
| `v0.47` | `2026-08-12` | `MKB owner + Codex` | **D05-v0.2 整篇重写**（Owner 六节骨架）：sub-agent fleet 考古 SMCP/RPC/全链；§0 债务→MKB 方案；§1 Intake+Artifact+D01/D02；§2 Recall+双通道+ContextTier；§3 glossary v2.2；§4 D04 映射；§5 contracts 对应。 |
| `v0.48` | `2026-08-12` | `MKB owner + Codex` | **D05-v0.3 product-core**：Owner 冻结双通道/粒度0·1·2详解与举例/g=0必向量化/construct→vectorize门闩；失败只引 D01/S03 max_retries；补 **Prompt 标定** 与 **双通道 typed 详例**；glossary v2.3。 |
| `v0.49` | `2026-08-12` | `MKB owner + Codex` | **D05-v0.4**：冻结生产三 Prompt **`promptA=Clean · promptB=Structurizer · promptC=Summarizer`**（`variant.version`+DB hash）；Clean 纳入生产链锚定；glossary v2.4。 |
| `v0.50` | `2026-08-12` | `MKB owner + Codex` | **冻结 D05-v1.0**（`T-O-202..210`）；glossary v2.5；S03/S05/S06/S07/S11 D05-calibrated；promptA/B/C 生产链与 ConstructToVectorizeGate 回填。 |
| `v0.51` | `2026-08-12` | `MKB owner + Codex` | 启动 **S08** progressive QNA `qna-truth/S08.md v0.1`：pre-round `T-O-211..220`；legacy-family 四路考古；Round 1 Q1–Q3 open；S08 → `designing`。 |
| `v0.52` | `2026-08-12` | `MKB owner + Codex` | S08 Round 1 冻结 `T-O-221..224`（含原文 detach/reattach）；中场评估 I；Round 2 Q4–Q6 open；QNA v0.2。 |
| `v0.53` | `2026-08-12` | `MKB owner + Codex` | S08 QNA **v0.3**：Q4–Q6 推荐/Reasoning 业内 reference 升级（Outbox、幂等 upsert、soft-delete、reindex、pre-embed filter）+ 外链索引。 |
| `v0.54` | `2026-08-12` | `MKB owner + Codex` | S08 Round 2 冻结 `T-O-225..227`；中场评估 II；Round 3 Q7–Q9 open；QNA v0.4。 |
| `v0.55` | `2026-08-12` | `MKB owner + Codex` | S08 Round 3 冻结 `T-O-228..230`（Q8=执行写面 only，不覆盖 S04）；Mid III；**Round 4 waived**；QNA v1.0 locked 待 formal Spec。 |
| `v0.56` | `2026-08-12` | `MKB owner + Codex` | 发布 **S08-v1.0** formal Spec（`T-O-211..230`）；domain-truth 唯一执行 SSOT；S08 accepted；QNA 降为证据层。 |
| `v0.57` | `2026-08-12` | `MKB owner + Codex` | **S08 全族回填**：D01/S03 废止 `lsrag.vectorize_index`；S07/S11/S12/D02/D04/D05 校准；glossary v2.6；冲突扫描闭环。 |
| `v0.58` | `2026-08-12` | `MKB owner + Codex` | 发布 **S10-v1.0** formal Spec（`T-O-247..262`）；S10 accepted；**G-07 closed** context-only；glossary/index 校准；QNA locked。 |
| `v0.59` | `2026-08-12` | `MKB owner + Codex` | 发布 **S09-v1.0** formal Spec（`T-O-231..246`）；S09 accepted；**G-09 closed foundation**；PublicationProof/ActiveIndexPointer/可服务谓词；QNA locked。 |
| `v0.60` | `2026-08-12` | `MKB owner + Grok workflow domain-truth-s14-s16` | 发布 **S14-v1.1 / S15-v1.1 / S16-v1.1** 执行 SSOT（`T-O-263..336`）；QNA 证据层 locked；S11 catalog/binding 写权威矩阵与 S14 双向钉死；G-10 加固 closed for v1 transport；G-12 deferred 不变。 |
| `v0.61` | `2026-08-12` | `MKB owner + Grok workflow domain-truth-s14-s16` | **S14–S16 战役全真相层审计**：§1.1/§3.14–3.16/§7/附录 A 回填；glossary → **v2.8**；对抗扫描（race/盲点/覆盖）；审计报告 `qna-truth/_s14-s16-campaign-audit.md`；索引保持 **`active index`**（`17`/`18` pending，**不**宣称 frozen truth index）。 |
| `v0.62` | `2026-08-12` | `MKB owner + Grok` | **废止独立 `17` System Topology 槽位**：运行拓扑收敛至 **`D06-runtime-topology.md`（v0.2-draft）**；§1.2/§1.3/§2.2/§4/§5/§8.3/§9/附录 A 全部改指 D06；完成定义改为 `00+D01–D06+S01–S16+18`；宿主机资源非 blocker 纪律见 D06。 |
| `v0.63` | `2026-08-12` | `MKB owner + Grok` | 新增 **§0.5 Python 技术栈：描述 · 要求 · 约束**（`PY-01..53`）：CPython≥3.12、单体发布、contracts typed SSOT、Ports 隔离 Turso/对象/vLLM、`ai-mkb` 推理平面、安全/观测与 architecture 门禁；与 D03/D04/D06/S11–S16 勾稽。 |
| `v0.64` | `2026-08-13` | `MKB owner + Grok` | 登记 **D08-v0.1**（legacy 四域能力 → intake 拓扑）与 **D07-v0.5** 槽位回填；D03/D04/S05 D08-calibrated；跨 Domain truth 计数 6→8；完成集合改为 `00+D01–D08+S01–S16+18`；glossary v2.9。 |
