# MKB（MyKnowledgeBase）

> 基于 **Python 3.12 + FastAPI + 本地 Turso Database** 的独立、有状态 LS-RAG 叶子工作器，面向内部编排器提供知识摄取、分层结构化、向量发布、上下文检索与可审计任务执行能力。

> **文档性质**：`report / project-README`（档 A：架构 README）
>
> **文档状态**：`reviewed`（已对账当前代码与测试，尚未由业主 frozen）
>
> **维护者**：MKB maintainers
>
> **最后核对（against HEAD）**：2026-08-20 @ `5e64a1e`（`main`）
>
> **对外地址**：N/A；仓库未提供部署清单、生产域名或已发布实例
>
> **总体状态**：核心合同、API、持久化、工作流、对象存储、检索和观测面已落地；确定性离线配置可本地运行；当前全量测试为 `433 passed / 8 failed`，R4 真实推理评估仍为 `conditional-ready`，R5 仅为待执行方案

状态词说明：`已落地` 表示有代码和本仓证据；`条件可用` 表示依赖特定配置或仍有未闭合验证；`合同已落地 / 未接线` 表示类型、流程或拒绝语义存在，但默认组合根没有可运行实现；`计划中` 表示只有方案；`占位` 表示目录或接口预留但无业务实现。本文不以 `frozen`、历史 closure 或单次样例代替当前 `live` 证据。

## 1. 项目综述

MKB 是一个内部服务，而不是面向终端用户的聊天产品。调用方以 Team 为租户边界，创建异步 Task；服务把 Task 固化为不可变配置快照和工作流 Execution，再由进程内 supervisor 驱动细粒度 Process。摄取完成后，MKB 发布带来源回溯的分层向量，并通过同步检索接口返回 **context-only** 结果。最终答案生成、成员系统、平台级 RBAC、真实计费、前端 UI 和外部部署入口不属于当前可运行产品面。

核心能力：

- **异步任务协议**：支持摄取、重建、元数据更新、停用、恢复、删除和索引重建，采用创建后轮询，不提供 callback/webhook。
- **耐久工作流**：支持 claim、lease、重试、fencing、outbox、人工 gate、scatter/join、重启恢复和历史工作流 revision 兼容。
- **多来源摄取**：支持 inline、已有本地对象、静态 HTTP/PDF，以及由调用方冻结 records 的 registered API 集合。
- **LS-RAG 生成**：把内容组织为 `g0/g1/g2` 分层块，保留 `original/summary` 双通道和 `content_full`，再执行向量化与发布校验。
- **有栅栏的检索**：同时校验当前 index generation 与 intake serving eligibility，返回可回溯上下文，不生成最终答案。
- **可审计基础设施**：本地 Turso Database、team-scoped SHA-256 CAS、事件/诊断/安全审计、Prometheus 文本指标和 readiness 分组件探针。

### 1.1 当前能力状态

| 能力 / 链路 | 状态 | 当前证据 |
|---|---|---|
| FastAPI 单体应用、探针、公共/内部路由 | `已落地` | [`api/app.py`](api/app.py)、[`api/public/routes.py`](api/public/routes.py)、[`api/internal/routes.py`](api/internal/routes.py) |
| Team / Task / Execution / Process 持久状态机 | `已落地` | [`src/runtime/task_service.py`](src/runtime/task_service.py)、[`src/runtime/workflow_engine.py`](src/runtime/workflow_engine.py)、[`src/persistence/migrations/`](src/persistence/migrations/) |
| 本地 Turso Database 与并发写/native-vector readiness | `已落地` | [`src/persistence/turso/`](src/persistence/turso/)、2026-08-20 新库 readiness smoke 全组件为真 |
| 本地对象 CAS、引用与孤儿 GC | `已落地` | [`src/storage/local_store.py`](src/storage/local_store.py)、[`src/services/object_gc.py`](src/services/object_gc.py) |
| inline / text / HTML / PDF text-layer 确定性摄取 | `已落地` | [`src/runtime/intake/`](src/runtime/intake/)、[`tests/intake/`](tests/intake/) |
| 浏览器渲染、OCR、Vision、文档/网页 LLM 清洗 | `合同已落地 / 未接线` | 工作流和稳定拒绝路径存在；[`api/app.py`](api/app.py) 未注入 browser/OCR/clean-LLM runtime |
| registered API scatter | `已落地（调用方冻结输入）` | [`intake/api/registry.py`](intake/api/registry.py)、[`src/workflows/builtin_scatter.py`](src/workflows/builtin_scatter.py)；不是实时供应商客户端 |
| 离线 stub 生成与 deterministic-hash 检索 | `已落地` | 默认 `MKB_NS1_CLI_MODE=stub`、`MKB_LIVE_INFERENCE=false`；核心非 E2E 套件通过 |
| 本地 vLLM / Claude CLI 真实推理 | `条件可用` | 适配器已接线；最新 R4 四个真实 cell 均未通过，见 [`after-MKB-0815-R4-first-wave.md`](docs/eval/new-start/after-MKB-0815-R4-first-wave.md) |
| 发布栅栏、双通道向量与 context-only retrieval | `已落地` | [`src/services/retrieval/`](src/services/retrieval/)、[`src/persistence/retrieval_access.py`](src/persistence/retrieval_access.py) |
| R5 system-owned g0 与 quoted cuts | `计划中` | [`R5-system-g0-and-quoted-cuts.md`](docs/eval/new-start/R5-system-g0-and-quoted-cuts.md) 状态为 `WAIT_OWNER_TO_EXECUTE`，对应代码/Schema/Prompt 尚未落地 |
| 前端与静态站点 | `占位` | `frontend/`、`public/` 仅有 `.gitkeep` |
| 生产部署与公开 URL | `未提供` | 仓库无 Dockerfile、Compose、Kubernetes、CI/CD 或 Sites hosting 配置 |

## 2. 技术栈

| 层级 | 技术 / 库 | 用途与取舍 |
|---|---|---|
| 语言 | Python `>=3.12,<3.13` | 使用强类型合同、async runtime；当前只支持 Python 3.12 |
| HTTP / ASGI | FastAPI `0.115.12`、Uvicorn `0.34.2` | 单一 ASGI 应用、严格 DTO、同步检索与异步任务 API |
| 合同 / 配置 | Pydantic `2.11.4`、pydantic-settings `2.9.1` | `extra=forbid`、版本化 schema、`MKB_` 运行时配置 |
| HTTP 客户端 | HTTPX `0.28.1` | vLLM OpenAI-compatible transport 与受 SSRF 策略约束的来源获取 |
| 生产持久化 | `pyturso >=0.7.2` | 本地嵌入式 Turso Database；不是 Turso Cloud 远程副本 |
| 测试持久化 | Python `sqlite3` | 仅 pytest fixture；普通运行显式选择 `sqlite` 会被拒绝 |
| 对象存储 | 本地文件系统 CAS | Team 隔离、SHA-256 内容寻址、原子 promote、DB 引用与孤儿回收 |
| 推理 | 本地 vLLM + 可选 Claude CLI `-p` | embed/generate 走有 supply fence 的适配器；CLI 支持 stub/subprocess/disabled |
| 测试 / 静态检查 | pytest `8.3.5`、pytest-asyncio `0.26.0`、Ruff `0.11.8` | unit/domain/integration/e2e/intake 分层；当前全量与 Ruff 并非全绿 |
| 构建 | setuptools `>=80`、uv lockfile | 生成 wheel/sdist；运行依赖保持精简 |
| 许可证 | Proprietary | 当前不是开源许可；使用、分发与衍生以业主授权为准 |

项目没有前端框架、消息队列、Redis、外部向量数据库或独立 worker 进程。工作流 supervisor 与维护扫描器都在同一应用 lifespan 内启动。

## 3. 模块总览

### 3.1 API 与组合根

[`api/`](api/) 定义唯一 FastAPI 应用、依赖注入、鉴权顺序和路由。`api.app:create_app()` 负责组装持久化、注册表、推理 facade、工作流 worker、检索、GC 与 retention；`api.app:app` 是 ASGI 入口，`mkb` 是命令行入口。

### 3.2 合同层

[`src/contracts/`](src/contracts/) 存放公共 API、intake、workflow、inference、vector、storage、observability 和 persistence 的版本化 Pydantic 模型。外部 UUID 仅接受 v4/v7，MKB 自己生成 UUIDv7；公共扩展只能进入显式 `payload_extra`。

### 3.3 运行时与工作流

[`src/runtime/`](src/runtime/) 承担配置、健康检查、安全、HTTP 获取、推理调度、intake pipeline、Task 服务组合和 durable workflow engine。[`src/workflows/`](src/workflows/) 保存当前声明式图以及供已冻结 Execution 恢复使用的历史 revision。

### 3.4 领域服务

[`src/services/`](src/services/) 实现 Team、配置快照、prompt/model registry、摄取生命周期、LS-RAG structurize/construct、向量发布、检索、事件、安全审计、观测读取与 retention。服务层依赖抽象端口，不自行选择数据库驱动。

### 3.5 持久化与对象存储

[`src/persistence/`](src/persistence/) 提供 migration、repository/access port、Turso 主路径和 pytest-only SQLite 实现。[`src/storage/`](src/storage/) 提供本地 CAS；对象内容和关系事实分离，数据库只保存逻辑 handle、digest 与引用。

### 3.6 来源适配

[`intake/`](intake/) 保存轻量来源类型、文本处理、Web sanitize 和 registered provider raw schema；具体执行 handler 位于 `src/runtime/intake/`。registered API 只校验调用方提交的冻结 records，不在服务内调用供应商 API。

### 3.7 配置、Schema 与 Prompt

[`data/config/`](data/config/) 是 checked-in 默认配置与 feature flags；[`data/prompts/`](data/prompts/) 是 prompt 字节真源；[`data/schemas/`](data/schemas/) 保存 LS-RAG schema。`data/database/`、`data/objects/`、`data/logs/` 是被 Git 忽略的运行时数据目录。

### 3.8 测试与工程文档

[`tests/`](tests/) 按 unit、domain、integration、e2e、intake 分层。[`docs/baseline/domain-truth/`](docs/baseline/domain-truth/) 是设计真相层；`docs/closure/` 记录阶段收口，`docs/eval/` 记录实际运行评估，`docs/plan/` 只代表方案，不能被当成已实现事实。

## 4. 目录结构

```text
myknowledgebase/
├── pyproject.toml                 # 包元数据、Python/依赖约束、pytest 与 Ruff 配置
├── uv.lock                        # 可复现依赖锁
├── .env.example                   # 环境变量示例；不会被 Settings 自动读取
├── api/
│   ├── app.py                     # ASGI 应用、composition root、lifespan 与探针
│   ├── dependencies.py            # 鉴权、限流、ready/internal-network 依赖
│   ├── public/routes.py           # /v1 Team、Task、gate、lineage、retrieval API
│   └── internal/routes.py         # /internal prompt 与运维观测 API
├── intake/
│   ├── api/registry.py            # registered provider 版本化 raw schema/manifest
│   ├── text.py                    # 文本归一化
│   └── web/sanitize.py            # Web 内容净化原语
├── src/
│   ├── contracts/                 # 跨边界严格合同与错误 envelope
│   ├── runtime/                   # 配置、安全、推理、摄取、工作流和后台扫描器
│   ├── services/                  # 领域服务、LS-RAG、registry、retrieval、observability
│   ├── persistence/
│   │   ├── migrations/            # 001–013 数据库 migration
│   │   └── turso/                 # pyturso 生产主路径
│   ├── storage/                   # team-scoped 本地对象 CAS
│   ├── llm_adapters/              # 本地 vLLM adapter
│   └── workflows/                 # 当前图与历史兼容 revision
├── data/
│   ├── config/                    # L0 默认配置与 feature flags
│   ├── prompts/                   # 经 hash 注册的 prompt 字节
│   ├── schemas/                   # LS-RAG 数据 schema
│   ├── database/                  # 运行库（忽略；仅 .gitkeep 跟踪）
│   ├── objects/                   # CAS 对象（忽略；仅 .gitkeep 跟踪）
│   └── logs/                      # 运行日志目录（忽略；仅 .gitkeep 跟踪）
├── tests/                         # unit/domain/integration/e2e/intake/fixtures
├── scripts/                       # glossary 导入与 NS4 迁移辅助脚本
├── docs/                          # baseline、closure、eval、plan、review、verification
├── frontend/                      # 占位，无 UI 实现
└── public/                        # 占位，无静态站点实现
```

## 5. 核心架构与执行模型

### 5.1 运行拓扑

```text
内部编排器 / 运维调用方
          │ Bearer token + versioned JSON
          ▼
  FastAPI 单体进程（127.0.0.1:8080）
    ├── Team / Task API ──► TaskService ──► Turso Database
    ├── Retrieval API ───► RetrievalService ─► 向量记录 + CAS
    ├── WorkflowSupervisor / Worker ────────► Process / Outbox
    ├── vLLM / Claude CLI adapter（按配置）
    └── GC / index retirement / retention 后台扫描器
```

应用启动时先执行 migration、prompt/model/workflow registry bootstrap 和对象根检查，再启动 supervisor、对象 GC、旧 index generation retirement 与观测 retention。新业务 Task 受 `/ready` 栅栏约束；`/live` 与 `/healthz` 不依赖下游组件。

### 5.2 领域身份与状态

- **Team**：所有业务状态、对象和查询的租户边界。
- **Task**：调用方可见的幂等请求与结果投影；状态为 `queued → running/cancelling → succeeded/failed/cancelled`。
- **Execution**：Task 的内部、冻结工作流实例，绑定 workflow key/revision、配置和 prompt/model digest。
- **Process**：可 claim、续租、重试和 fence 的最小执行单元。
- **Intake Item / Revision / Snapshot**：来源对象、不可变修订和被 Task 接受的成员集合。
- **Index Generation**：不可变发布世代；active pointer 通过 compare-and-swap 切换，旧世代在 grace 后异步退休。

调用方只依赖 Team、Task、intake item、gate、generation artifact 等公共身份；Execution/Process UUID 不从公共 Task/retrieval 响应泄露。

### 5.3 主工作流

普通单来源摄取的主链为：

```text
acquire → decode → clean → seal candidate set → preflight
        → accept snapshot → [human review gate]
        → [markdown transcription] → structurize → construct
        → vectorize → validate publication → terminal
```

当前注册 15 个 active workflow definition：inline 主图、12 个来源 profile、registered API scatter root 和 scatter child；另保留历史兼容 revision，保证已冻结 Execution 不被新图重新解释。Task 创建后应轮询，不应假设请求内完成；当前没有 webhook/callback。

### 5.4 调度与推理通道

| 池 | 默认 running / queued | 用途 |
|---|---:|---|
| `local-inference` | `2 / 6` | 本地 vLLM structured/text generation |
| `non-interactive` | `2 / 4` | Claude CLI `-p` 或 deterministic stub |
| `embed` | `8 / 20` | embedding/vectorization |

normal/low Task 在未显式指定时优先 local-inference，high/urgent 优先 non-interactive；`MKB_LIVE_INFERENCE=false` 时本地 live supply 不可用，默认离线配置使用 deterministic stub/hash。当前没有 starvation aging；高压和 GPU soak 仍需部署侧验证。

## 6. 来源接入与内容处理

### 6.1 调用方可提交的来源

| `source_kind` | 输入 | 当前运行能力 | 重要边界 |
|---|---|---|---|
| `inline_payload` | `external_key`、文本、media type、title | `已落地` | content 上限 8,388,608 字符；适合文本/JSON/HTML |
| `local_object` | 已存在的 `mkbobj:v1:<team>:<sha256>` handle | `已落地（前置条件）` | 公共 API 没有对象上传端点，调用方需通过受信任的内部装载流程先创建 handle |
| `http_resource` / `static` | HTTPS URL | `已落地` | 不接收 caller headers/cookie/proxy；响应上限默认 8 MiB |
| `http_resource` / `pdf` | HTTPS PDF URL | `条件可用` | 只处理有限 PDF text layer；image-only PDF 需要未接线 OCR |
| `http_resource` / `browser` | URL | `合同已落地 / 未接线` | 默认组合根未注入 browser fetcher，会稳定失败而非静默降级 |
| `registered_api` | provider/operation/version + `records[]` | `已落地` | records 必须由调用方冻结；MKB 不执行供应商网络请求 |

registered provider 是闭集：

- `chinatax / get_articles / v1`
- `domain / get_agency_listings / v1`
- `realestate / get_listings / v1`

每类 raw member 都有版本化 schema 和唯一外部键校验。集合输入由 scatter root 冻结/预检，再由 child workflow 独立发布成员。

### 6.2 出站 HTTP 安全

`HttpAcquirer` 默认只允许 HTTPS，拒绝 URL credential、literal IP、私网、loopback、link-local、metadata 与 reserved 地址；DNS 解析结果会被固定并对最多 3 次 redirect 逐跳复核。默认不允许 HTTP、私网或 literal-IP 例外，响应体上限 8 MiB。它不是通用代理，也不接受调用方自定义请求头。

### 6.3 内容策略边界

确定性 text/JSON/HTML 清洗与有限 PDF text extraction 已接线。OCR、Vision、browser rendering、doc-LLM、web-LLM 和 PDF-understanding 的合同、工作流或拒绝路径已经存在，但 `create_app()` 没有注入相应 runtime；因此这些 profile 不能描述为 live capability。

## 7. Prompt、模型与配置真相层

### 7.1 Prompt registry

Prompt 正文只存在于 [`data/prompts/`](data/prompts/)；数据库保存 `prompt_id + version + relative path + SHA-256`。启动 bootstrap 注册目录，Task materialization 冻结所选 identity/hash；运行时字节与已注册 hash 不一致会 fail closed，历史 Task 不会随“最新 prompt”漂移。

documentation profile 的当前选择为：

| 角色 | 默认/选择规则 | 当前 active 版本 |
|---|---|---|
| clean A | `promptA.documentation.default` | `v1` |
| 可选 Markdown B | `qna / eval / closure / plan / code-review` flavor | 各 `v1` |
| JSON structurize B | `g0 / g1 / g2` | `g0 v1`、`g1 v4`、`g2 v2` |
| summary C | `promptC.documentation.default` | `v2` |

granularity 是闭集：`g0 → {0}`、`g1 → {0,1}`、`g2 → {0,1,2}`。flavor 只有在 `domain=documentation` 时合法；调用方可以给 prompt identity，但不能提交 prompt 正文、文件路径或自由 role。

### 7.2 模型与 supply fence

默认 catalog 包含 deterministic 64 维 embedding、本地 Qwen VL embedding、Qwen/Nemotron generation 以及默认关闭的 rerank。live binding 为：

| capability | 首选模型 | 备用 / 状态 |
|---|---|---|
| `embed` | `LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4` | live 模式期望 1024 维；offline 使用 `deterministic-hash-v1` 64 维 |
| `structured_generate` | `unsloth/Qwen3.8-27B-NVFP4` | Nemotron Lightning 为较低优先级 spare |
| `text_generate` | `unsloth/Qwen3.8-27B-NVFP4` | Nemotron Lightning 为较低优先级 spare |
| `rerank` | `qwen-rerank-2b` | 默认 disabled；检索诚实报告 fallback，不伪造 rerank |

composition root 与 registry 共用 binding digest；数据库侧如果被改成组合根未登记的 endpoint/model，admission/readiness 会失败，而不会静默换供应。

### 7.3 配置层次

- [`data/config/default.toml`](data/config/default.toml)：checked-in 默认说明；实际进程字段以 [`src/runtime/config.py`](src/runtime/config.py) 的 `Settings` 为准。
- [`data/config/feature_flags.yaml`](data/config/feature_flags.yaml)：三个 experimental flag 当前均为 `false`。
- 环境变量：只覆盖运行时部署值，统一使用 `MKB_` 前缀。
- Task `overrides`：最大 16 KiB 的显式 L3 bag，接受范围由快照服务 allowlist 决定；不能用来绕过 prompt/model/安全政策。
- Durable snapshot：在 admission 时把解析后的 workflow、registry、prompt/model digest 固化为历史事实。

## 8. LS-RAG 特色子系统

### 8.1 它做什么

MKB 的 LS-RAG 不把一篇文档压成单一向量。它保留原文、分层结构、摘要通道、generation artifact、向量记录和发布证明，让检索结果能从 summary 回溯到 original，并能解释“哪一版内容、prompt、模型和 index generation 产生了这个 hit”。

### 8.2 核心不变量

- **不可变输入与产物**：accepted revision、generation artifact、向量 generation 和 publication proof 不原地改写。
- **分层覆盖**：`g0` 是整篇层，`g1/g2` 逐级细化；当前生成合同要求实际 granularity set 与所选 profile 一致。
- **双通道**：可摘要的块保留 `original` 与 `summary`；`content_full` 是完整内容的稳定恢复面。
- **双重 serving fence**：只有 active index generation 且 intake item 仍具 serving eligibility 的记录可返回。
- **可追溯**：检索从 summary channel 解析 original，返回 generation refs/traceback；不能解析时明确标注状态。
- **context-only**：retrieval 返回证据上下文，不返回 `answer`，也不暴露 Execution/Process 内部身份。

### 8.3 检索请求边界

`POST /v1/teams/{team_uuid}/retrieval:search` 接受版本 `mkb.retrieval.v1`、query、namespace selector、`return_k`、`recall_k`、threshold、pack 开关和有限 filters（intake item/source kind/channel）。`return_k` 与 `recall_k` 最大 100，query 最大 8192 字符。调用方不能覆盖 vector/model/index/answer 策略。

### 8.4 如何扩展

- 新来源：先增加版本化 SourceDescriptor/raw schema，再登记 source/strategy manifest、实现 handler、声明 workflow profile，并补 admission、拒绝路径和 E2E。
- 新 prompt：提交 prompt 字节，向 catalog 增加新的 identity/version/hash，不覆写已使用版本；补 bootstrap/hash-mismatch 与输出合同测试。
- 新模型：增加 catalog 与 binding，更新 composition supply fence 和 readiness probe；禁止仅修改数据库指针。
- 新 workflow：发布递增 revision，并保留仍可能被历史 Execution 引用的旧 definition。
- 新向量世代：构建并验证 publication proof 后 CAS 提升 active pointer，让 retirement scanner 回收 grace 到期的旧世代。

## 9. 服务接口与外部集成

### 9.1 服务边界与鉴权

MKB 本身就是内部 backend/leaf worker，不是浏览器 BFF。业务接口和 operator 接口都要求内部 token，首选 `Authorization: Bearer <token>`，兼容 `X-MKB-Internal-Token`。鉴权在资源读取之前执行；operator 路由还要求 ASGI peer 为 loopback/private/internal 地址。若经过反向代理，只有受信任的边缘层可以重写 client address，应用不盲信 forwarded headers。

### 9.2 探针与运维路由

| 路由 | 方法 | 鉴权 / 说明 |
|---|---|---|
| `/live`、`/healthz` | GET | 无依赖存活探针 |
| `/ready` | GET | 分组件 readiness；ready 为 200，否则 503 |
| `/metrics` | GET | 仅 internal peer；可配置额外 bearer |
| `/docs`、`/redoc`、`/openapi.json` | GET | FastAPI 默认文档面；当前未单独关闭或鉴权，部署边缘需限制网络 |

readiness 组件包括 migration、registry bootstrap、primary DB、concurrent writes、native vector、object root、inference binding、observability tables 和 internal token loaded。

### 9.3 公共 `/v1` 路由

| 资源 | 路由与方法 | 说明 |
|---|---|---|
| Team | `POST/GET /v1/teams` | 创建/列出 Team |
| Team | `GET/PATCH/DELETE /v1/teams/{team_uuid}` | 读取、乐观 revision 更新、逻辑删除 |
| Team lifecycle | `POST .../{team_uuid}:activate|:deactivate|:restore` | 显式状态转换 |
| Task | `POST/GET /v1/teams/{team_uuid}/tasks` | 创建或分页/过滤列出异步 Task |
| Task | `GET/PATCH/DELETE .../tasks/{task_uuid}` | 读取、修改允许字段、软删除 |
| Task control | `POST .../{task_uuid}:cancel|:retry` | 取消或创建受控 retry/restart |
| Task result | `GET .../{task_uuid}/result` | 读取终态结果投影 |
| Generation evidence | `GET .../{task_uuid}/generation-artifacts[/{generation_artifact_uuid}]` | 分页/读取不可变生成产物元数据 |
| Generation pointers | `GET .../{task_uuid}/generation-artifact-pointers` | 读取当前 full-valid 指针选择 |
| Intake/generation projection | `GET .../{task_uuid}/items`、`GET .../{task_uuid}/generations` | Task 所属成员与向量世代投影 |
| Human gate | `GET .../{task_uuid}/gates[/{gate_uuid}]`、`POST .../{gate_uuid}:decide` | 查询和决策人工 gate |
| Restart/lineage | `GET /v1/teams/{team_uuid}/task-restarts[/{restart_uuid}]`、`GET .../task-lineage` | 重启记录与 lineage |
| Retrieval | `POST /v1/teams/{team_uuid}/retrieval:search` | 同步、无业务副作用的 context-only 检索 |

Task `request_intent` 是闭集：`intake.ingest`、`intake.rebuild`、`intake.update_metadata`、`intake.deactivate`、`intake.reactivate`、`intake.delete`、`index.rebuild`。创建合同必须包含 `mkb.task.v1`、匹配 path 的 Team UUID、Task/trace UUID、intent 对应 payload 和 `mkb.task-audit.v1` audit。

### 9.4 内部 `/internal` 路由

| 路由组 | 方法 | 用途 |
|---|---|---|
| `/internal/prompts`、`/internal/prompts/{prompt_id}` | GET/POST/PATCH/DELETE | prompt catalog 运维，不接收 prompt 正文字节 |
| `/internal/teams/{team_uuid}/traces/{trace_uuid}/timeline` | GET | trace 时间线 |
| `/internal/teams/{team_uuid}/tasks/{task_uuid}/timeline` | GET | Task 事件/诊断时间线 |
| `/internal/teams/{team_uuid}/outbox/dead` | GET | dead outbox 读取 |
| `/internal/teams/{team_uuid}/security-audit` | GET | 安全审计读取 |

### 9.5 外部依赖与第三方接口

| 集成 | 配置 / 输入 | 当前状态 |
|---|---|---|
| 本地 vLLM OpenAI-compatible API | `MKB_INFERENCE_VLLM_BASE_URL`、token/secret-file | adapter 已落地；真实 R4 生成链未通过验收 |
| Claude CLI | `MKB_NS1_CLI_MODE=subprocess`、`MKB_NS1_CLI_EXECUTABLE` | 无 shell 调用，material 走 stdin；真实供应商验证仍需完成 |
| 任意 HTTPS 来源 | `http_resource.url` | 受 SSRF/redirect/size 策略约束的 server-side GET |
| chinatax/domain/realestate | 调用方提交冻结 `records[]` | 只有 raw schema + scatter，不含供应商 token/client/pagination 请求 |
| Turso Database | 本地 DB 文件 | `pyturso` embedded 主路径；cloud replica 未接入 |

应用没有第三方 token 缓存层、浏览器 CORS consumer 或公开 raw-vector/object CRUD。

## 10. 安装、运行、测试与部署

### 10.1 前置条件

- Python 3.12；3.11 和 3.13 不在项目声明范围。
- [uv](https://docs.astral.sh/uv/)；依赖以仓库内 `uv.lock` 为准。
- 默认离线启动不需要 GPU、vLLM 或 Claude CLI。
- live inference 需要部署方自行提供兼容 endpoint、模型和 secret，并先通过探针/评估。

### 10.2 安装与本地启动

```bash
uv sync --extra dev

# Settings 不会自动加载 .env；请在启动进程前 export。
export MKB_INTERNAL_TOKENS='replace-with-a-local-secret'
export MKB_DATA_DIR='data'
export MKB_LIVE_INFERENCE='false'
export MKB_NS1_CLI_MODE='stub'

uv run mkb
```

服务默认监听 `http://127.0.0.1:8080`。开发时也可运行：

```bash
uv run uvicorn api.app:app --host 127.0.0.1 --port 8080 --reload
```

另一个终端执行：

```bash
curl -fsS http://127.0.0.1:8080/live
curl -fsS http://127.0.0.1:8080/ready
```

`/ready` 必须返回 200 后再创建 Task。首次启动会创建/迁移 `data/database/mkb_primary.db` 和对象根；两者均是运行时数据，不应提交。

### 10.3 最小 API 旅程

下面使用 UUIDv4（API 同时接受 v4/v7）创建 Team、提交 inline ingest，再轮询并检索。示例依赖本机 Python 3.12 与较新的 curl：

```bash
export MKB_BASE_URL='http://127.0.0.1:8080'
export MKB_TOKEN='replace-with-a-local-secret'
export TEAM_UUID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"
export TASK_UUID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"
export TRACE_UUID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"
export CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"

curl -fsS -X POST "$MKB_BASE_URL/v1/teams" \
  -H "Authorization: Bearer $MKB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"schema_version\": \"mkb.team.v1\",
    \"team_uuid\": \"$TEAM_UUID\",
    \"name\": \"README quickstart\"
  }"

curl -fsS -X POST "$MKB_BASE_URL/v1/teams/$TEAM_UUID/tasks" \
  -H "Authorization: Bearer $MKB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"schema_version\": \"mkb.task.v1\",
    \"team_uuid\": \"$TEAM_UUID\",
    \"task_uuid\": \"$TASK_UUID\",
    \"trace_uuid\": \"$TRACE_UUID\",
    \"request_intent\": \"intake.ingest\",
    \"payload\": {
      \"domain\": \"documentation\",
      \"granularity\": \"g1\",
      \"compression_channel\": \"non-interactive\",
      \"source\": {
        \"source_kind\": \"inline_payload\",
        \"external_key\": \"readme-quickstart\",
        \"content\": \"MKB 把知识摄取为可回溯的分层检索上下文。\",
        \"media_type\": \"text/plain\"
      }
    },
    \"audit\": {
      \"schema_version\": \"mkb.task-audit.v1\",
      \"team_uuid\": \"$TEAM_UUID\",
      \"task_uuid\": \"$TASK_UUID\",
      \"trace_uuid\": \"$TRACE_UUID\",
      \"audit_type\": \"business_review\",
      \"audit_status\": \"not_required\",
      \"source\": \"readme-quickstart\",
      \"created_at\": \"$CREATED_AT\"
    }
  }"

# 重复执行，直到 status 进入 succeeded / failed / cancelled。
curl -fsS \
  -H "Authorization: Bearer $MKB_TOKEN" \
  "$MKB_BASE_URL/v1/teams/$TEAM_UUID/tasks/$TASK_UUID"

curl -fsS -X POST "$MKB_BASE_URL/v1/teams/$TEAM_UUID/retrieval:search" \
  -H "Authorization: Bearer $MKB_TOKEN" \
  -H 'Content-Type: application/json' \
  -d "{
    \"schema_version\": \"mkb.retrieval.v1\",
    \"team_uuid\": \"$TEAM_UUID\",
    \"query\": \"分层检索上下文\",
    \"return_k\": 3,
    \"recall_k\": 5
  }"
```

创建接口对相同身份和相同内容支持幂等 replay；重用 UUID 却改变内容会产生冲突。若 Task `failed`，先读取 Task result、generation artifacts 和 internal timeline，而不是直接改数据库。

### 10.4 常用命令

| 目的 | 命令 |
|---|---|
| 同步开发依赖 | `uv sync --extra dev` |
| 启动服务 | `uv run mkb` |
| 核心测试 | `uv run pytest -q tests/unit tests/domain tests/integration` |
| 全量测试 | `uv run pytest` |
| 单独跑 intake / E2E | `uv run pytest tests/intake` / `uv run pytest tests/e2e` |
| 静态检查 | `uv run ruff check .` |
| 自动格式化 | `uv run ruff format .` |
| 构建 wheel/sdist | `uv build` |

### 10.5 测试分层与当前结果

| 层 | 覆盖 | 2026-08-20 @ `5e64a1e` 结果 |
|---|---|---|
| `tests/unit` | 合同、服务、engine、security、registry、persistence 原语 | 与 domain/integration 合跑：`PASS` |
| `tests/domain` | 领域状态机和不变量 | 与 unit/integration 合跑：`PASS` |
| `tests/integration` | 跨服务/持久化组合 | 与 unit/domain 合跑：`PASS` |
| `tests/intake` | 来源类型与清洗 | 包含在全量执行；全量没有 intake 单元失败 |
| `tests/e2e` | 完整 Task、scatter、lifecycle、publication、retrieval | 全量存在 8 个失败，详见 §12 |
| 全量 `pytest` | 全仓 441 个 collected case | `433 passed, 8 failed`（约 302 秒），**不是全绿** |
| Ruff | `E/F/I/UP/B` | `9 errors`，**不是全绿** |
| `uv build` | sdist + wheel | `PASS`；有 `project.license` TOML table 的 setuptools deprecation warning |
| 新 Turso 库 readiness smoke | migration/bootstrap/DB/vector/CAS/security/obs | 所有组件为真 |
| README 离线 API smoke | 新 Turso 库上的 Team → Task → retrieval | ready `200`、Team/Task create `201`、Task `succeeded`、retrieval `200 / ok / 3 hits` |
| R4 live cells | 真实 prompt/inference 生成 | 4/4 未通过；既有 corpus retrieval 6/6 为 HTTP 200，不能据此宣称端到端 live |

测试默认静态配置写在 `pyproject.toml`。pytest fixture 可以选择 stock SQLite；生产/普通本地服务必须走 Turso 路径。

### 10.6 构建与部署

`uv build` 已在本次核对中成功生成标准 sdist 与 wheel，包范围为 `api*`、`src*`、`intake*`。运行还需要 checked-in `data/prompts`、`data/config`、`data/schemas`，因此单独复制 wheel 并不等于完整部署制品；部署必须显式挂载/打包这些资源并提供可写 DB/object 路径。

仓库当前没有容器、systemd、Kubernetes、CI/CD、反向代理或 hosting manifest，也没有 deploy 命令和生产 URL。部署方需自行负责进程守护、TLS、网络 ACL、可信代理地址、secret 注入、数据卷、备份与恢复；完成这些工作前不能把本仓状态标为 production/live。

## 11. 安全与配置策略

### 11.1 配置加载时机

项目没有前端或构建时公开变量。所有 `Settings` 都在服务进程组合时读取，统一映射为 `MKB_<FIELD_NAME>`，不暴露给浏览器。由于模块级 `api.app:app` 会在 import 时构造容器，环境变量必须在 `uv run mkb` 或 Uvicorn 启动之前设置。

`SettingsConfigDict` 当前没有 `env_file`，所以仅复制 `.env.example` 为 `.env` **不会自动生效**。可使用 shell `export`，或显式让进程管理器/Uvicorn 加载 env file。

### 11.2 环境变量参考

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MKB_INTERNAL_TOKENS` | 空 | 逗号分隔 active bearer；服务 ready 至少需要有效 token |
| `MKB_INTERNAL_TOKEN` / `MKB_INTERNAL_TOKEN_PREVIOUS` | 空 | 单 token 与轮换兼容槽；合并后最多允许两个不同 active token |
| `MKB_DATA_DIR` | `data` | 默认运行时数据根 |
| `MKB_DATABASE_PATH` | `<data_dir>/database/mkb_primary.db` | 本地 Turso 数据库文件 |
| `MKB_OBJECT_ROOT` | `<data_dir>/objects` | 本地 CAS 根 |
| `MKB_PERSISTENCE_BACKEND` | `turso` | `sqlite` 只允许 pytest 环境 |
| `MKB_CONCURRENT_WRITES_REQUIRED` | `true` | readiness 必须证明并发写能力 |
| `MKB_NATIVE_VECTOR_REQUIRED` | `true` | readiness 必须证明 native vector capability |
| `MKB_VECTOR_BACKEND` | `deterministic_exact` | 当前 scan profile；该名字不是 ANN 性能证明，可选 `native_ann` |
| `MKB_PROMPT_ROOT_PATH` | 仓库 `data/prompts` | 可显式挂载另一个经审计 prompt tree |
| `MKB_CONFIG_ROOT_PATH` | 仓库 `data/config` | 可显式挂载配置根 |
| `MKB_INFERENCE_VLLM_BASE_URL` | `http://127.0.0.1:668` | origin，不要带 `/v1`；adapter 自行追加路径 |
| `MKB_INFERENCE_VLLM_TOKEN` | 空 | 首选 deploy-injected bearer，`SecretStr` 持有，不进入 DB/snapshot |
| `MKB_INFERENCE_SECRET_SLOT` / `MKB_INFERENCE_SECRET_FILE` | 空 | token 未设置时的成对 file fallback |
| `MKB_INFERENCE_PROBE_ENABLED` | `false` | 为真时 readiness 探测实际 active model binding |
| `MKB_LIVE_INFERENCE` | `false` | 控制 live embed/vectorize；假时使用 deterministic hash |
| `MKB_NS1_CLI_MODE` | `stub` | `stub`、`subprocess` 或 `disabled`；独立于 `LIVE_INFERENCE` |
| `MKB_NS1_CLI_EXECUTABLE` | `claude` | subprocess 模式的可执行文件，不经过 shell |
| `MKB_INFERENCE_GENERATE_TIMEOUT_SECONDS` | `180` | 生成调用超时，范围 1–3600 秒 |
| `MKB_DISPATCH_LOCAL_RUNNING` / `MKB_DISPATCH_LOCAL_QUEUED` | `2 / 6` | local generation 池容量 |
| `MKB_DISPATCH_NI_RUNNING` / `MKB_DISPATCH_NI_QUEUED` | `2 / 4` | non-interactive 池容量 |
| `MKB_DISPATCH_EMBED_RUNNING` / `MKB_DISPATCH_EMBED_QUEUED` | `8 / 20` | embedding 池容量 |
| `MKB_DISPATCH_LOCAL_CHAR_BUDGET` | `16000` | local pool 同时在途字符预算 |
| `MKB_INFERENCE_MAX_IN_FLIGHT` / `MKB_INFERENCE_MAX_ATTEMPTS` | `12 / 3` | facade 总并发与最大尝试次数 |
| `MKB_OBJECT_MAX_BYTES` | `268435456` | 单 CAS 对象上限，默认 256 MiB |
| `MKB_RATE_LIMIT_IP_PER_MIN` | `120` | 进程内固定窗口 IP 限流 |
| `MKB_RATE_LIMIT_TOKEN_PER_MIN` | `600` | token fingerprint 限流 |
| `MKB_RATE_LIMIT_WINDOW_SECONDS` | `60` | 限流窗口 |
| `MKB_METRICS_REQUIRE_TOKEN` | `false` | `/metrics` 始终要求 internal peer；为真时再要求 bearer |
| `MKB_EGRESS_MAX_REDIRECTS` | `3` | 出站 HTTP 重定向上限，最大也为 3 |
| `MKB_EGRESS_ALLOW_LITERAL_IP` | `false` | 是否允许 URL literal IP |
| `MKB_EGRESS_ALLOW_PRIVATE_DEFAULT` | `false` | 是否默认允许私网目的地址 |
| `MKB_EGRESS_ALLOW_HTTP` | `false` | 是否允许明文 HTTP |
| `MKB_ACQUISITION_MAX_RESPONSE_BYTES` | `8388608` | 来源响应上限，默认 8 MiB |
| `MKB_OBJECT_GC_ENABLED` | `true` | 是否启动 orphan object GC |
| `MKB_OBJECT_GC_GRACE_SECONDS` | `86400` | 对象回收 grace，默认 24 小时 |
| `MKB_OBJECT_GC_INTERVAL_SECONDS` / `MKB_OBJECT_GC_BATCH_SIZE` | `600 / 100` | GC 扫描节奏 |
| `MKB_WORKFLOW_CLEANUP_RECOVERY_WINDOW_SECONDS` | `60` | terminal Process 标记 cleanup-eligible 前的恢复窗口 |
| `MKB_INDEX_RETIREMENT_ENABLED` | `true` | 是否启动旧 index generation retirement |
| `MKB_INDEX_RETIREMENT_GRACE_SECONDS` | `3600` | 切换后的不可变 grace |
| `MKB_INDEX_RETIREMENT_INTERVAL_SECONDS` / `MKB_INDEX_RETIREMENT_BATCH_SIZE` | `600 / 100` | retirement 扫描节奏 |
| `MKB_OBS_RETENTION_DOMAIN_EVENTS_DAYS` | `90` | domain events 保留期 |
| `MKB_OBS_RETENTION_DIAGNOSTIC_LOGS_DAYS` | `14` | diagnostic logs 保留期 |
| `MKB_OBS_RETENTION_SECURITY_AUDIT_DAYS` | `180` | security audit 保留期 |
| `MKB_OBS_RETENTION_INTERVAL_SECONDS` / `MKB_OBS_RETENTION_BATCH_SIZE` | `3600 / 1000` | retention 扫描节奏 |

注意：当前 [`.env.example`](.env.example) 把 vLLM URL 示例写成端口 `670`，而 `Settings` 与 [`data/config/default.toml`](data/config/default.toml) 的默认端口是 `668`。部署时必须显式选定真实 endpoint，不要把示例端口误认为运行真源。

### 11.3 密钥与审计政策

- real token 不得提交到 `.env.example`、配置、prompt、Task payload、数据库或 artifact。
- inference token 优先来自环境变量；secret file 只能与逻辑 slot 成对配置，内容不会进入 durable snapshot。
- active internal token 以 SHA-256 fingerprint 比较并使用 constant-time 校验；支持双 token 平滑轮换。
- 公共错误、事件和诊断对 token/secret/connection/presigned URL/宿主绝对路径做递归脱敏（redaction）或拒绝。
- 鉴权失败会写受采样控制的安全审计；关键 auth audit 无法持久化时 fail closed。限流器记账异常会降级并暴露 metric，但不会跳过 token 鉴权。

### 11.4 网络、CORS 与响应头

当前应用没有 CORS middleware、TrustedHost/HTTPS redirect middleware，也没有显式 CSP、HSTS、X-Frame-Options 等响应头。它的既定姿态是只在受控内部网络提供服务，而不是直接暴露到浏览器或公网。生产边缘必须承担 TLS、Host/Origin 策略、安全头、请求大小/超时限制、可信代理解析和 `/docs`/`/metrics` 网络隔离。

## 12. 已知事项与设计取舍

### 12.1 设计亮点

- **历史不会漂移**：prompt/model/workflow/config 都以 identity、revision 和 digest 冻结；hash/supply 不匹配时失败关闭。
- **状态与字节分离**：关系事实进 Turso，内容进 team-scoped CAS；原子 promote、引用计数语义和 grace GC 降低半提交风险。
- **检索不越权**：publication fence 与 intake lifecycle fence 同时生效，停用/删除内容不会因旧向量仍在而继续 serving。
- **失败也是证据**：Task/Process、outbox、generation invocation、stage report、domain event、diagnostic log 和 security audit 提供分层诊断面。
- **内部身份不外泄**：公共 API 围绕 Team/Task/业务 artifact，Execution/Process 留在 runtime/observability 边界内。
- **可恢复演进**：新 workflow revision 不覆盖旧图，in-flight/frozen Execution 仍可按原 definition 恢复。

### 12.2 已知问题与待验证项

| 编号 | 事项 | 当前影响 | 关闭 / reopen 触发器 |
|---|---|---|---|
| K1 | 全量 pytest 为 `433 passed / 8 failed` | 不能声明全绿；5 个失败落在已登记的 raw sqlite/pyturso inspection harness，另有 3 个 E2E 在全量运行中未进入预期终态；其中 inline isolated rerun 通过，generation/source isolated 仍停在 `running` | 修复 [`deferred-items-ledger.md`](docs/closure/new-start/deferred-items-ledger.md) 的 NS1-V11 类项，并让全量套件无排除通过 |
| K2 | Ruff 当前有 9 个错误 | 静态检查门未关闭；集中在迁移脚本、CLI、sidecar/soak 测试和测试变量 | `uv run ruff check .` 为 0 |
| K3 | R4 四个 live cell 均失败 | 真实 A/Markdown/B/C 链不能称为 live；失败包括 g0 anchor/granularity 与 Claude CLI empty result | 修复并重跑 [`after-MKB-0815-R4-first-wave.md`](docs/eval/new-start/after-MKB-0815-R4-first-wave.md) 中的 corpus/cell |
| K4 | R5 仅是 `WAIT_OWNER_TO_EXECUTE` 方案 | system-owned g0、quoted cuts、候选组装未在当前代码中存在 | owner 批准并落地代码、schema、prompt、migration、tests 后重新核对 |
| K5 | browser/OCR/Vision/doc-LLM/web-LLM 未注入 | 对应 source profile 会稳定拒绝或不可用 | 部署经过 review 的 capability，实现注入并补 readiness/live test |
| K6 | registered API 没有供应商客户端 | 不能实时调用 chinatax/domain/realestate；分页与 exhaust 由调用方冻结证明 | 若产品要求实时连接器，另建 token/client/retry/pagination/egress 边界并验收 |
| K7 | `.env.example` 端口与 Settings 默认不一致，且 `.env` 不自动加载 | 新贡献者可能连接错误 endpoint 或以为配置已生效 | 统一端口/加载政策并加配置测试；此前以 `Settings` 和显式 export 为准 |
| K8 | 无部署制品、生产 URL、TLS/安全头/CORS/Host 策略 | 仅适合本机或受控内部网络，不是公网就绪服务 | 增加经过 review 的部署/边缘配置、备份恢复和生产 smoke |
| K9 | `/docs`、`/redoc`、`/openapi.json` 使用 FastAPI 默认开放策略 | 内网可用，但若误暴露会扩大接口枚举面 | 在部署 edge 限制或由应用显式关闭/鉴权 |
| K10 | billing 是 always-permit stub | 没有额度、结算或真实 admission 计费能力 | 业务要求 billing 时替换 [`src/services/billing.py`](src/services/billing.py) 并补 fail-closed policy |
| K11 | 并发/GPU/云侧证据不完整 | multithread BEGIN CONCURRENT 仅有部分 serial soak；cloud replica、urgent starvation aging、GPU soak 未完成 | 对目标部署形态完成 soak 和故障注入，记录可复现证据 |
| K12 | `frontend/` 与 `public/` 只是占位 | 没有最终用户 UI、SEO、i18n 或静态内容产品 | 只有产品范围正式加入 UI 时才实现；否则保持空边界 |
| K13 | 总 spec index、D06/D07/D08 与 release 签署尚未 frozen | domain truth 仍有 owner-review 草案；D07 定义验收标准，但不证明这些标准已经通过 | 完成 owner freeze、P0–P4 所需证据或正式 waiver，并更新 [`spec-index.md`](docs/baseline/spec-index.md) |
| K14 | `pyproject.toml` 使用已弃用的 license table 写法 | 当前 build 成功，但 setuptools 提示 2027-02-18 后将不再支持 | 在截止日前改为 SPDX string / `license-files`，并复跑 `uv build` |

### 12.3 明确的非目标

- MKB retrieval 只返回 grounded context，不负责生成最终回答或维护聊天会话。
- MKB 不提供终端用户身份、组织成员、平台 RBAC、计费产品或浏览器登录。
- MKB 不提供公开的原始对象上传/下载、向量 CRUD 或数据库管理 API。
- MKB 不把 plan、closure、已有冻结 corpus 或一次成功 retrieval 当成当前端到端 live 证明。
- MKB 是单应用、单部署单元；当前没有把 API、worker 和 scheduler 拆为分布式服务的承诺。

## 13. 总体评价

当前 HEAD 已形成一套边界清晰、证据优先的有状态 LS-RAG 内部工作器：合同、耐久执行、Turso/CAS、分层生成、发布栅栏、检索和审计面彼此衔接，离线 deterministic 配置适合本地开发与大部分核心验证。它还不是可对外宣称 production/live 的完整产品：全量测试与 lint 未全绿，R4 真实推理链失败，R5 仍是方案，部分来源 capability 未接线，部署和边缘安全也不在仓库内。下一阶段最有价值的工作是先关闭当前可复现失败并完成真实推理验收，再根据目标环境补部署、soak 和运维证据，而不是扩大公开接口面。

## 附录 A：文档与真相层导航

| 目录 / 文档 | 应如何使用 |
|---|---|
| [`docs/baseline/spec-index.md`](docs/baseline/spec-index.md) | 设计文档入口；索引本身尚未 frozen |
| [`docs/baseline/domain-truth/`](docs/baseline/domain-truth/) | D01–D08、S01–S16 的领域/子系统真相层 |
| [`docs/baseline/qna-truth/`](docs/baseline/qna-truth/) | owner 问答与决策证据，不自动代表实现 |
| [`docs/closure/`](docs/closure/) | 阶段性 closure、handoff、deferred ledger；历史结论需与当前 HEAD 复核 |
| [`docs/eval/`](docs/eval/) | 实际运行分析、live cell 结果和后续评估 |
| [`docs/plan/`](docs/plan/) | 待执行方案；不能作为已落地证据 |
| [`docs/code-review/`](docs/code-review/) | 外部/交叉 code review 记录 |
| [`docs/verification/`](docs/verification/) | Schema 与 workflow 合同核对笔记 |

若代码、测试和文档口径冲突，先以可执行代码和当前复现实证界定“现状”，再回到 domain truth/owner decision 判断“应当是什么”；不要用 draft plan 反向声明代码已经完成。

## 附录 B：修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|---|---|---|---|
| v1.0 | 2026-08-20 | Codex（按 MKB maintainers 委托） | 扫描全仓并按架构 README 模板重写；对齐 `5e64a1e` 的 API、运行时、配置、测试和 R4/R5 状态 |
