# MKB（MyKnowledgeBase）

> 基于 **Python 3.12 + FastAPI + 本地 Turso Database** 的独立、有状态 LS-RAG 叶子工作器，面向内部编排器提供知识摄取、分层结构化、向量发布、上下文检索与可审计任务执行能力。

> **文档性质**：`report / project-README`（档 A：架构 README）
>
> **文档状态**：`reviewed`（已对账当前代码、测试分层、配置与收口文档，尚未由业主 frozen）
>
> **维护者**：MKB maintainers
>
> **最后核对（against HEAD）**：2026-09-06 @ `71f3555`（`main`）
>
> **对外地址**：N/A；仓库未提供部署清单、生产域名或已发布实例
>
> **总体状态**：核心合同、API、持久化、工作流、对象存储、检索和观测面已落地。NS5–NS9 把 fail-closed 边界、系统写 g0、quoted cuts、10k 分段与 R7 实弹写入内核。new-harvest（NH1–NH9 + CROSS-NH）把四 kind 清洗通道、kind-family 工作流、representation / actual S05、公共对象生命周期、语义 facet 与 default-root 供给接线写入代码。NHX1 把 Observation / ItemEpoch、对象 session、证据平面、部署角色、发现 / 运维面与 cutover 写入 migration `025`–`029`。确定性离线配置可本地运行。当前全量测试记录为 `1010 passed / 0 failed`（2026-08-31 @ `d843f00`；其后 HEAD 仅文档提交）。本次核对 `uv run pytest --collect-only` 仍为 1010 collected，Ruff 为 0。R4 真实推理评估仍为 `conditional-ready`。R7 仍为 2026-08-28 实弹 4/4（见 [`NS9-0815-R7-live-firing-closure.md`](docs/closure/new-start/NS9-0815-R7-live-firing-closure.md)），但按 `T-O-376` 不能据此宣称四通道接通。NHX1 官方 close-type 为 `implementation-complete-awaiting-live-verification`；内部 closure evidence 仍不完整（见 [`NHX1-closure-gaps.md`](docs/closure/new-harvest/NHX1-closure-gaps.md)）

状态词说明：`已落地` 表示有代码和本仓证据；`条件可用` 表示依赖特定配置、本机 binary/模型或仍有未闭合验证；`合同已落地 / 未接线` 表示类型、流程或拒绝语义存在，但默认组合根没有可运行实现；`代码已落地 / live 待验证` 表示实现与本地测试在，但真实推理或生产供给发车尚未授权；`计划中` 表示只有方案；`占位` 表示目录或接口预留但无业务实现。本文不以 `frozen`、历史 closure 或单次样例代替当前 `live` 证据。

## 1. 项目综述

MKB 是一个内部服务，而不是面向终端用户的聊天产品。调用方以 Team 为租户边界，创建异步 Task；服务把 Task 固化为不可变配置快照和工作流 Execution，再由进程内 supervisor 驱动细粒度 Process。摄取完成后，MKB 发布带来源回溯的分层向量，并通过同步检索接口返回 **context-only** 结果。最终答案生成、成员系统、平台级 RBAC、真实计费、前端 UI 和外部部署入口不属于当前可运行产品面。

核心能力：

- **异步任务协议**：支持摄取、重建、元数据更新、停用、恢复、删除和索引重建，采用创建后轮询，不提供 callback/webhook。
- **耐久工作流**：支持 claim、lease、重试、fencing、outbox、人工 gate、scatter/join、重启恢复和历史工作流 revision 兼容。新摄取默认解析到 kind-family 图；旧 profile key 仍 enabled-but-unselected，供 in-flight Execution 按 compiled digest 回放。
- **多来源摄取**：支持 inline、已有本地对象、静态 HTTP/PDF、浏览器 render/print，以及由调用方冻结 records 的 registered API 集合。公共面提供 streaming CAS 上传，但不提供 raw download。
- **LS-RAG 生成**：把内容组织为 `g0/g1/g2` 分层块；g1 默认走 quoted cuts（系统写 g0，模型只报锚点，管道在 `clean` 上切片）；保留 `original/summary` 双通道和 `content_full`，再执行向量化与发布校验。
- **有栅栏的检索**：同时校验当前 index generation 与 intake serving eligibility；调用方必须显式选择 Layer A namespace，可用语义 facet 过滤，返回可回溯上下文，不生成最终答案。
- **可审计基础设施**：本地 Turso Database、team-scoped SHA-256 CAS、事件/诊断/安全审计、Prometheus 文本指标、readiness 分组件探针，以及 NHX1 的 discovery / operator / cutover 面。

### 1.1 当前能力状态

| 能力 / 链路 | 状态 | 当前证据 |
|---|---|---|
| FastAPI 单体应用、探针、公共/内部路由 | `已落地` | [`api/app.py`](api/app.py)、[`api/public/routes.py`](api/public/routes.py)、[`api/internal/routes.py`](api/internal/routes.py)；含 catalog / capabilities / objects / cutover / operator |
| Team / Task / Execution / Process 持久状态机 | `已落地` | [`src/runtime/task_service.py`](src/runtime/task_service.py)、[`src/runtime/workflow_engine.py`](src/runtime/workflow_engine.py)、[`src/persistence/migrations/`](src/persistence/migrations/) |
| 本地 Turso Database 与 write-path / native-vector readiness | `已落地` | [`src/persistence/turso/`](src/persistence/turso/)；`/ready` 栅栏组件是 `write_path_ready`，不是 `concurrent_writes=true`；migration 为 `001`–`029` |
| 本地对象 CAS、公共 upload/stat/cancel、引用与孤儿 GC | `已落地` | [`api/public/routes.py`](api/public/routes.py)、[`src/services/object_upload.py`](src/services/object_upload.py)、[`src/services/object_gc.py`](src/services/object_gc.py)；**无** public raw download |
| inline / text / HTML / PDF text-layer 确定性摄取 | `已落地` | [`src/runtime/intake/`](src/runtime/intake/)、[`tests/intake/`](tests/intake/)；HTML 清洗保留段落换行 |
| kind-family 工作流与七意图 admission | `已落地` | [`src/workflows/kind_family.py`](src/workflows/kind_family.py)、[`src/services/intake_lifecycle/admission_matrix.py`](src/services/intake_lifecycle/admission_matrix.py)；新 `intake.ingest` 解析到 kind 图，不是旧 single-profile 选择器 |
| representation history 与 actual S05 binding | `已落地` | [`src/runtime/binding/actual_s05.py`](src/runtime/binding/actual_s05.py)、migration `019`/`020` |
| 语义六元组与检索 facet | `已落地` | [`src/services/retrieval/`](src/services/retrieval/)、migration `022`；v2 可按 `realm/type/semantic_channel/source_name/is_active/context_tags` 过滤 |
| PDF parser / browser render / browser print / deterministic OCR | `条件可用` | [`api/app.py`](api/app.py) 默认 `discover()` 注入；失败则 `None` 并稳定拒绝，不静默降级。生产 `/ready` 要 `MKB_RUNTIME_SUPPLY_READINESS_REQUIRED=true` 且本机 binary 在场 |
| Vision / doc-LLM / web-LLM / pdf-LLM | `条件可用` | 路径已接到 default-root；默认 `MKB_MULTIMODAL_ENABLED=false`，`clean_llm=None` 时对应 capability 503。战役 L4 使用 S11 local fixture / CLI stub，不是 0815 真模型发车 |
| registered API scatter | `已落地（调用方冻结输入）` | [`intake/api/registry.py`](intake/api/registry.py)、[`src/workflows/builtin_scatter.py`](src/workflows/builtin_scatter.py)；不是实时供应商客户端 |
| 离线 stub 生成与 deterministic-hash 检索 | `已落地` | 默认 `MKB_NS1_CLI_MODE=stub`、`MKB_LIVE_INFERENCE=false`；生产策略另行保持 Qwen embedding local、生成走 CLI |
| Claude/Agy/cursor-agent/Grok 生成路由 | `条件可用` | Claude `minimax-m3` 主路（3 并发）、Agy 备路（2 并发）、cursor-agent/Grok 轮换 fallback；总 CLI 并发上限 8；真实 executable/模型供给仍需部署验证 |
| 发布栅栏、双通道向量与 context-only retrieval | `已落地` | [`src/services/retrieval/`](src/services/retrieval/)；检索必须带 `namespace_key` 或 `namespace_uuid` |
| 系统写 g0、quoted cuts、10k 自适应分段 | `已落地（live 已验证）` | [`src/runtime/intake/generation_assemble.py`](src/runtime/intake/generation_assemble.py)、[`data/schemas/mkb.b-json-cuts.v1.json`](data/schemas/mkb.b-json-cuts.v1.json)、g1 catalog `v5`；R7 实弹 4/4（88→174 向量） |
| 部署角色、capability readiness、NHX1 cutover | `已落地` | [`src/runtime/roles.py`](src/runtime/roles.py)、[`src/services/nhx1_cutover.py`](src/services/nhx1_cutover.py)；默认 `deployment_role=all`。NHX1 final close 仍 blocked |
| TrustedHost、请求体上限、空 CIDR 不信 XFF | `已落地` | [`api/app.py`](api/app.py)、[`src/runtime/security.py`](src/runtime/security.py) |
| 前端与静态站点 | `占位` | `frontend/`、`public/` 仅有 `.gitkeep` |
| 生产部署与公开 URL | `未提供` | 仓库无 Dockerfile、Compose、Kubernetes、CI/CD 或 Sites hosting 配置 |

## 2. 技术栈

| 层级 | 技术 / 库 | 用途与取舍 |
|---|---|---|
| 语言 | Python `>=3.12,<3.13` | 使用强类型合同、async runtime；当前只支持 Python 3.12 |
| HTTP / ASGI | FastAPI `0.141.1`、Starlette `>=1.0.1`、Uvicorn `0.34.2` | 单一 ASGI 应用、严格 DTO、TrustedHost、同步检索与异步任务 API |
| 合同 / 配置 | Pydantic `2.11.4`、pydantic-settings `2.9.1` | 合同 `extra=forbid`、版本化 schema、`MKB_` 运行时配置 |
| HTTP 客户端 | HTTPX `0.28.1` | vLLM OpenAI-compatible transport 与受 SSRF 策略约束的来源获取 |
| 生产持久化 | `pyturso >=0.7.2` | 本地嵌入式 Turso Database；不是 Turso Cloud 远程副本 |
| 测试持久化 | Python `sqlite3` | 仅 pytest fixture（`PYTEST_CURRENT_TEST` 且已 import pytest）；普通运行显式选择 `sqlite` 会被拒绝 |
| 对象存储 | 本地文件系统 CAS | Team 隔离、SHA-256 内容寻址、原子 promote、DB 引用与孤儿回收；上传走 streaming CAS |
| 推理 | 本地 vLLM + 可选 Claude CLI `-p` | embed/generate 走有 supply fence 的适配器；CLI 支持 stub/subprocess/disabled |
| 本地供给 | isolated PDF parser、hardened browser、deterministic OCR、可选 S11 multimodal | `create_app()` 按 Settings `discover()`；缺 binary 则 fail-soft 为 `None`，不伪造 provenance |
| 测试 / 静态检查 | pytest `8.3.5`、pytest-asyncio `0.26.0`、Ruff `0.11.8` | unit/domain/integration/e2e/intake 分层；Ruff 已清零；最近一次全量 pytest 为 1010 全绿 |
| 构建 | setuptools `>=80`、uv lockfile | 生成 wheel/sdist；wheel 含 migration SQL、LS-RAG JSON schema 与 workflow JSON；运行还需要 checked-in `data/` 资源 |
| 许可证 | Proprietary | 当前不是开源许可；使用、分发与衍生以业主授权为准 |

项目没有前端框架、消息队列、Redis、外部向量数据库或独立 worker 进程。`deployment_role` 只描述同一二进制的进程所有权（`api` / `workflow_worker` / `maintenance` / `all`），不是把 API、worker 和 scheduler 拆成分布式服务。工作流 supervisor 与维护扫描器都在同一应用 lifespan 内按角色启动。

## 3. 模块总览

### 3.1 API 与组合根

[`api/`](api/) 定义唯一 FastAPI 应用、依赖注入、鉴权顺序和路由。`api.app:create_app()` 负责组装持久化、注册表、推理 facade、本地供给、工作流 worker、检索、GC、upload lifecycle、cutover 与 retention，并安装 TrustedHost 与请求体上限中间件；`api.app:app` 是 ASGI 入口，`mkb` 是命令行入口。

### 3.2 合同层

[`src/contracts/`](src/contracts/) 存放公共 API、intake、workflow、inference、vector、storage、observability、persistence、governance 和 LS-RAG 的版本化 Pydantic 模型。外部 UUID 仅接受 v4/v7，MKB 自己生成 UUIDv7；公共扩展只能进入显式 `payload_extra`。[`src/contracts/lsrag/`](src/contracts/lsrag/) 保存 layered content 与 quoted cuts 合同；[`src/contracts/governance.py`](src/contracts/governance.py) 与 [`src/contracts/api/objects.py`](src/contracts/api/objects.py) 覆盖 NHX1 / NH4 表面。

### 3.3 运行时与工作流

[`src/runtime/`](src/runtime/) 承担配置、健康检查、安全、HTTP 获取、推理调度、intake pipeline、Task 服务组合和 durable workflow engine。实现按 `task/`、`workflow/`、`inference/`、`intake/`、`supply/`、`binding/` 拆分；[`src/runtime/intake/generation_assemble.py`](src/runtime/intake/generation_assemble.py) 是系统写 g0 与锚点切片的组装器。[`src/workflows/`](src/workflows/) 保存当前声明式图以及供已冻结 Execution 恢复使用的历史 revision，含 kind-family 与 `kind_family_v1_manifest.json`。

### 3.4 领域服务

[`src/services/`](src/services/) 实现 Team、配置快照、prompt/model registry、摄取生命周期、LS-RAG structurize/construct、向量发布、检索、对象上传、事件、安全审计、观测读取、retention、operator control 与 NHX1 cutover。服务层依赖抽象端口，不自行选择数据库驱动。

### 3.5 持久化与对象存储

[`src/persistence/`](src/persistence/) 提供 migration、repository/access port、Turso 主路径和 pytest-only SQLite 实现。当前 migration 为 `001`–`029`。[`src/storage/`](src/storage/) 提供本地 CAS；对象内容和关系事实分离，数据库只保存逻辑 handle、digest 与引用。

### 3.6 来源适配

[`intake/`](intake/) 保存轻量来源类型、文本处理、Web sanitize、PDF/doc 原语和 registered provider raw schema；具体执行 handler 位于 `src/runtime/intake/`，本机供给位于 `src/runtime/supply/`。registered API 只校验调用方提交的冻结 records，不在服务内调用供应商 API。

### 3.7 配置、Schema 与 Prompt

[`data/config/`](data/config/) 是 checked-in 默认配置与 feature flags；[`data/prompts/`](data/prompts/) 是 prompt 字节真源；[`data/schemas/`](data/schemas/) 保存 LS-RAG layered content 与 `mkb.b-json-cuts.v1` schema。`data/database/`、`data/objects/`、`data/logs/` 是被 Git 忽略的运行时数据目录。

### 3.8 测试与工程文档

[`tests/`](tests/) 按 unit、domain、integration、e2e、intake 分层，另有 NH / NHX1 fixture 与 evidence harness。[`docs/baseline/domain-truth/`](docs/baseline/domain-truth/) 是设计真相层；`docs/closure/` 记录阶段收口（含 `0820-review/`、NS7–NS9 与 `new-harvest/`），`docs/evidence/new-harvest/` 保存战役四元组，`docs/eval/` 记录实际运行评估，`docs/plan/` 只代表方案，不能被当成已实现事实。`docs/runbooks/` 目前只有 NHX1 P7 信号手册。

## 4. 目录结构

```text
myknowledgebase/
├── pyproject.toml                 # 包元数据、Python/依赖约束、pytest 与 Ruff 配置
├── uv.lock                        # 可复现依赖锁
├── .env.example                   # 环境变量示例；不会被 Settings 自动读取
├── api/
│   ├── app.py                     # ASGI 应用、composition root、lifespan、TrustedHost 与探针
│   ├── dependencies.py            # 鉴权、限流、ready/internal-network 依赖
│   ├── public/routes.py           # /v1 Team、Task、object、catalog、gate、lineage、retrieval
│   └── internal/                  # /internal prompt、观测、operator 与 NHX1 cutover
├── intake/
│   ├── api/registry.py            # registered provider 版本化 raw schema/manifest
│   ├── text.py                    # 文本归一化；HTML 抽取保留段落换行
│   ├── web/sanitize.py            # Web 内容净化原语
│   ├── pdf/                       # PDF 表示观察原语
│   └── doc/                       # 文档清洗原语
├── src/
│   ├── contracts/                 # 跨边界严格合同与错误 envelope
│   │   └── lsrag/                 # layered content 与 quoted cuts 合同
│   ├── runtime/                   # 配置、安全、推理、摄取、工作流和后台扫描器
│   │   ├── intake/                # 含 generation_assemble（系统 g0 / cuts）
│   │   ├── supply/                # PDF / browser / OCR 本机供给
│   │   ├── binding/               # actual S05
│   │   ├── task/                  # Task 命令、投影与创建
│   │   └── workflow/              # durable engine 实现
│   ├── services/                  # 领域服务、LS-RAG、registry、retrieval、upload、cutover
│   ├── persistence/
│   │   ├── migrations/            # 001–029 数据库 migration
│   │   └── turso/                 # pyturso 生产主路径
│   ├── storage/                   # team-scoped 本地对象 CAS
│   ├── llm_adapters/              # 本地 vLLM adapter（含 cuts schema 路由）
│   └── workflows/                 # 当前图、kind-family 与历史兼容 revision
├── data/
│   ├── config/                    # L0 默认配置与 feature flags
│   ├── prompts/                   # 经 hash 注册的 prompt 字节（documentation g1 当前 active 为 v5）
│   ├── schemas/                   # lsrag.layered_content.v1 与 mkb.b-json-cuts.v1
│   ├── database/                  # 运行库（忽略；仅 .gitkeep 跟踪）
│   ├── objects/                   # CAS 对象（忽略；仅 .gitkeep 跟踪）
│   └── logs/                      # 运行日志目录（忽略；仅 .gitkeep 跟踪）
├── tests/                         # unit/domain/integration/e2e/intake/fixtures
├── scripts/                       # glossary 导入与 NS4 迁移辅助脚本
├── docs/                          # baseline、closure、eval、plan、review、evidence、runbooks、verification
├── frontend/                      # 占位，无 UI 实现
└── public/                        # 占位，无静态站点实现
```

`context/` 与 `.experiment/` 是业主上下文和评估运行目录，已被 `.gitignore` 排除，不是发布制品。

## 5. 核心架构与执行模型

### 5.1 运行拓扑

```text
内部编排器 / 运维调用方
          │ Bearer token + versioned JSON
          ▼
  FastAPI 单体进程（127.0.0.1:8080）
    ├── Team / Task / Object / Catalog API ──► TaskService / ObjectUpload ──► Turso Database
    ├── Retrieval API ───► RetrievalService ─► 向量记录 + CAS + semantic facets
    ├── WorkflowSupervisor / Worker ────────► Process / Outbox
    ├── vLLM / Claude CLI / 本机 PDF·browser·OCR（按配置 discover）
    └── GC / upload TTL / index retirement / retention 后台扫描器
```

应用启动时先执行 migration、prompt/model/workflow registry bootstrap 和对象根检查，再按 `deployment_role` 启动 supervisor、对象 GC、upload lifecycle、旧 index generation retirement 与观测 retention。新业务 Task、对象上传和检索受 `/ready` 栅栏约束；`/live` 与 `/healthz` 不依赖下游组件。

默认角色是 `all`（API + claims + maintenance + retention）。拆开部署时：`api` 不 claim 工作流；`workflow_worker` 拥有 supervisor；`maintenance` 拥有 GC / upload lifecycle / retirement / retention。这是同一二进制的进程所有权，不是多服务拆分承诺。

### 5.2 领域身份与状态

- **Team**：所有业务状态、对象和查询的租户边界。
- **Task**：调用方可见的幂等请求与结果投影；状态为 `queued → running/cancelling → succeeded/failed/cancelled`。产品终态可另见 `result_disposition`（migration `023`）。
- **Execution**：Task 的内部、冻结工作流实例，绑定 workflow key/revision、配置和 prompt/model digest。
- **Process**：可 claim、续租、重试和 fence 的最小执行单元。
- **Intake Item / Revision / Snapshot / Observation / ItemEpoch**：来源对象、不可变修订、被 Task 接受的成员集合，以及 NHX1 的观察身份与世代。
- **Index Generation**：不可变发布世代；active pointer 通过 compare-and-swap 切换，旧世代在 grace 后异步退休。
- **Namespace（Layer A）**：由 `{model_key}|{model_version}|{adapter_kind}|{dimension}` 组成的检索空间；`default` 不是可 serving 的 Layer A 名。

调用方只依赖 Team、Task、intake item、object handle、gate、generation artifact 等公共身份；Execution/Process UUID 不从公共 Task/retrieval 响应泄露。operator 调试面在 `/internal` 另开，且要求内网 peer。

### 5.3 主工作流

普通单来源摄取的主链为：

```text
acquire → decode → clean → seal candidate set → preflight
        → accept snapshot → [human review gate]
        → [markdown transcription] → structurize → construct
        → vectorize → validate publication → terminal
```

documentation g1 的 structurize 默认走 quoted cuts：模型只交起止锚点，组装器写入恰好一块 `g0.body = clean`，再在 `clean` 上切片。超过约 10k 字符的 cuts 输入会按标题边界自适应分段。clean / structurize / publication 等步骤在需要时要求 sealed actual S05，而不是只看政策别名。

当前注册 **18** 个 active workflow definition：3 个 kind-family（inline / local-object / http-resource，rev 2）、1 个历史 single inline 图、12 个来源 profile、registered API scatter root 和 scatter child。新 `intake.ingest` 按 source kind 解析到 kind-family（`registered_api` 走 scatter root）；旧 profile key 保持 enabled-but-unselected。另保留 **19** 条历史兼容 revision（含 kind-family rev 1 冻结 JSON），保证已冻结 Execution 不被新图重新解释。Task 创建后应轮询，不应假设请求内完成；当前没有 webhook/callback。

### 5.4 调度与推理通道

| 池 | 默认 running / queued | 用途 |
|---|---:|---|
| `local-inference` | `2 / 6` | 本地 vLLM structured/text generation |
| `non-interactive` | `2 / 4` | Claude CLI `-p` 或 deterministic stub |
| `embed` | `8 / 20` | embedding/vectorization |

默认调度仍记录四级 priority；启用 `MKB_MODEL_CAPACITY_PRIORITY_GATE_ENABLED=true` 后，所有会产生模型工作的 normal/low 公共请求在 admission 返回 `429 MODEL_AT_CAPACITY / model at capacity`，high/urgent 才进入生成链。生产配置以 `MKB_GENERATION_LOCAL_ENABLED=false` 关闭 Qwen 生成入口，但 `MKB_LIVE_INFERENCE=true` 继续保留 Qwen local embedding/vectorize/retrieval；当前没有 starvation aging，高压和 GPU soak 仍需部署侧验证。capability registry 登记 27 个 process_key；worker 可用 `MKB_WORKER_CAPABILITY_ALLOWLIST` 收窄 claim 面。

## 6. 来源接入与内容处理

### 6.1 调用方可提交的来源

| `source_kind` | 输入 | 当前运行能力 | 重要边界 |
|---|---|---|---|
| `inline_payload` | `external_key`、文本、media type、严格四维语义 | `已落地` | `realm/type/channel/source_name` 必填且不得为 `unknown`；合同上限 8,388,608 字符 |
| `local_object` | CAS handle + 严格四维语义 | `已落地` | 先经受鉴权 `objects:upload` 获得 pending handle，再以独立 `intake.ingest` Task 消费；上传本身不创建 Intake identity，也不返回 raw bytes |
| `http_resource` / `static` | HTTPS URL + 严格四维语义 | `已落地` | 不接收 caller headers/cookie/proxy；响应上限默认 8 MiB |
| `http_resource` / `pdf` | HTTPS PDF URL | `条件可用` | 默认尝试 isolated PDF parser；image-only PDF 需要 OCR 供给在场，否则稳定拒绝 |
| `http_resource` / `browser` | URL | `条件可用` | `HardenedBrowserRuntime.discover()` 成功才可用；render 与 print_pdf 是两条能力，不能互相冒充 |
| `registered_api` | provider/operation/version + `records[]` | `已落地` | records 必须由调用方冻结；MKB 不执行供应商网络请求 |

三个 generic kind（inline/local/http，含 PDF/browser mode）均要求 caller 提交 `realm/type/channel/source_name`，`context_tags` 可选；`is_active` 由系统派生。registered API 的同名维度由版本化 provider mapper 决定，caller 若重复提交只能逐字段相等，不能覆盖 mapper。

registered provider 是闭集：

- `chinatax / get_articles / v1`
- `domain / get_agency_listings / v1`
- `realestate / get_listings / v1`

每类 raw member 都有版本化 schema 和唯一外部键校验。集合输入由 scatter root 冻结/预检，再由 child workflow 独立发布成员。

### 6.2 出站 HTTP 安全

`HttpAcquirer` 默认只允许 HTTPS，拒绝 URL credential、literal IP、私网、loopback、link-local、metadata 与 reserved 地址；DNS 解析结果会被固定并对最多 3 次 redirect 逐跳复核。默认不允许 HTTP、私网或 literal-IP 例外，响应体上限 8 MiB。它不是通用代理，也不接受调用方自定义请求头。browser runtime 另有独立超时、字节上限与并发池；`--no-sandbox` / cloud OCR / Cloudflare Browser Rendering 不在本仓允许集。

### 6.3 内容策略边界

确定性 text/JSON/HTML 清洗与有限 PDF text extraction 已接线。HTML 抽取会保留段落换行，而不是把 `<br>` 压成单个空格。PDF parser、browser render/print、deterministic OCR 已注入默认组合根：`discover()` 成功则可用，失败则对应 capability 稳定 503，而不是静默降级。Vision / doc-LLM / web-LLM / pdf-LLM 的代码路径也在 default-root，但默认 `multimodal_enabled=false`；战役披露的 CLI stub 与 S11 local fixture **不是** 0815 真模型证明，也不能写成未接线。

## 7. Prompt、模型与配置真相层

### 7.1 Prompt registry

Prompt 正文只存在于 [`data/prompts/`](data/prompts/)；数据库保存 `prompt_id + version + relative path + SHA-256`。启动 bootstrap 注册目录，Task materialization 冻结所选 identity/hash；运行时字节与已注册 hash 不一致会 fail closed，历史 Task 不会随“最新 prompt”漂移。`DEFAULT_CATALOG_PROMPTS` 当前 **23** 条；角色闭集为 `clean | markdown | json | summarizer`。

documentation profile 的当前选择为：

| 角色 | 默认/选择规则 | 当前 active 版本 |
|---|---|---|
| clean A | `promptA.default`（历史兼容 `promptA.clean` / `promptA.documentation.default`） | `v1` |
| 可选 Markdown B | `qna / eval / closure / plan / code-review` flavor | 各 `v1` |
| JSON structurize B | `g0 / g1 / g2` | `g0 v1`、`g1 v5`（quoted cuts）、`g2 v2` |
| summary C | `promptC.documentation.default` | `v2` |

另有 generic `promptB.json.{generic,g0,g1,g2,legal,realestate}` 与 `promptC.summarizer`，供非 documentation domain。granularity 是闭集：`g0 → {0}`、`g1 → {0,1}`、`g2 → {0,1,2}`。flavor 只有在 `domain=documentation` 时合法；调用方可以给 prompt identity，但不能提交 prompt 正文、文件路径或自由 role。g1 v1–v4 字节仍保留在仓库中，供已冻结 Execution 按 hash 恢复，新 Task 解析到 v5。

### 7.2 模型与 supply fence

默认 catalog 包含 deterministic 64 维 embedding、本地 Qwen VL embedding、Qwen/Nemotron generation 以及默认关闭的 rerank。live binding 为：

| capability | 首选模型 | 备用 / 状态 |
|---|---|---|
| `embed` | `LifetimeMistake/Qwen3-VL-Embedding-2B-NVFP4` | live 模式期望 1024 维；offline 使用 `deterministic-hash-v1` 64 维 |
| `structured_generate` | `unsloth/Qwen3.8-27B-NVFP4` | Nemotron Lightning 为较低优先级 spare；cuts 请求显式透传 `mkb.b-json-cuts.v1` |
| `text_generate` | `unsloth/Qwen3.8-27B-NVFP4` | Nemotron Lightning 为较低优先级 spare |
| `rerank` | `qwen-rerank-2b` | 默认 disabled；检索诚实报告 fallback，不伪造 rerank |

composition root 与 registry 共用 binding digest；数据库侧如果被改成组合根未登记的 endpoint/model，admission/readiness 会失败，而不会静默换供应。multimodal 身份必须 pinned，禁止 `latest`。`runtime_profile=prod` 会强制 `ns1_cli_mode=subprocess`、`runtime_supply_readiness_required=true`、`generation_local_enabled=false` 与模型容量 priority gate；只有启用 local generation 时才要求 multimodal supply。

### 7.3 配置层次

- [`data/config/default.toml`](data/config/default.toml)：checked-in 默认说明；实际进程字段以 [`src/runtime/config.py`](src/runtime/config.py) 的 `Settings` 为准。
- [`data/config/feature_flags.yaml`](data/config/feature_flags.yaml)：三个 experimental flag 当前均为 `false`。
- 环境变量：只覆盖运行时部署值，统一使用 `MKB_` 前缀。
- Task `overrides`：最大 16 KiB 的显式 L3 bag，接受范围由快照服务 allowlist 决定；不能用来绕过 prompt/model/安全政策。
- Durable snapshot：在 admission 时把解析后的 workflow、registry、prompt/model digest 固化为历史事实。

## 8. LS-RAG 特色子系统

### 8.1 它做什么

MKB 的 LS-RAG 不把一篇文档压成单一向量。它保留原文、分层结构、摘要通道、generation artifact、向量记录和发布证明，让检索结果能从 summary 回溯到 original，并能解释“哪一版内容、prompt、模型和 index generation 产生了这个 hit”。

g1 默认不再让模型默写全书。管道写入恰好一块 `g0.body = clean`；模型只报能在原文对上的起句/止句；组装器切片后再交给既有 admit。内核拒绝谓词没有放宽：覆盖之后 `g0` 仍必须等于 `clean`，g1 仍必须是 `clean` 的连续子串。

NH3 之后，clean / structurize / publication 等步骤还要求 actual S05 处于 `sealed`：digest 绑定 representation path、selected route 与 clean strategy，政策别名不能冒充实际绑定。NH5 之后，写入向量同时投影语义六元组，检索可按 facet 过滤，而不是只靠事后 Python 过滤。

### 8.2 核心不变量

- **不可变输入与产物**：accepted revision、generation artifact、向量 generation 和 publication proof 不原地改写。
- **分层覆盖**：`g0` 是整篇层，`g1/g2` 逐级细化；当前生成合同要求实际 granularity set 与所选 profile 一致。
- **双通道**：可摘要的块保留 `original` 与 `summary`；`content_full` 是完整内容的稳定恢复面。
- **双重 serving fence**：只有 active index generation 且 intake item 仍具 serving eligibility 的记录可返回。
- **显式 Layer A**：检索必须指定 `namespace_key` 或 `namespace_uuid`；省略会 `422 RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`。
- **可追溯**：检索从 summary channel 解析 original，返回 generation refs/traceback；不能解析时明确标注状态。
- **context-only**：retrieval 返回证据上下文，不返回 `answer`，也不暴露 Execution/Process 内部身份。
- **语义 facet**：业务频道写 `semantic_channel`，向量双通道写 `vector_channel`；停用/删除内容不会因为旧向量仍在而继续 serving。

### 8.3 检索请求边界

`POST /v1/teams/{team_uuid}/retrieval:search` 接受 query、**必填** namespace selector、`return_k`、`recall_k`、threshold、pack 开关和闭集 filters。新请求应使用 `mkb.retrieval.v2`：业务频道写 `semantic_channel`，向量双通道写 `vector_channel`，两者可同请求共存；另可过滤 `realm/type/source_name/is_active/context_tags`。旧 `mkb.retrieval.v1` 的 `filters.channel` 只机械兼容 `original|summary`，其它值 422；v2 出现旧键 `channel` 同样 422。`return_k` 与 `recall_k` 最大 100，query 最大 8192 字符。调用方不能覆盖 vector/model/index/answer 策略。

离线 stub 的 namespace key 为：

```text
deterministic-hash-v1|v1|deterministic|64
```

live embed 的 key 随 Layer A 变化，形状为 `{model_key}|{model_version}|{adapter_kind}|{dimension}`。不要使用 `default`。`GET /v1/teams/{team_uuid}/namespaces` 可列出当前 active namespace。

### 8.4 如何扩展

- 新来源：先增加版本化 SourceDescriptor/raw schema，再登记 source/strategy manifest、实现 handler、声明 workflow profile，并补 admission、拒绝路径和 E2E。第五 source kind 与 caller 自选 `workflow_key` 当前明确非目标。
- 新 prompt：提交 prompt 字节，向 catalog 增加新的 identity/version/hash，不覆写已使用版本；补 bootstrap/hash-mismatch 与输出合同测试。
- 新模型：增加 catalog 与 binding，更新 composition supply fence 和 readiness probe；禁止仅修改数据库指针。
- 新 workflow：发布递增 revision，并保留仍可能被历史 Execution 引用的旧 definition。
- 新向量世代：构建并验证 publication proof 后 CAS 提升 active pointer，让 retirement scanner 回收 grace 到期的旧世代。

## 9. 服务接口与外部集成

### 9.1 服务边界与鉴权

MKB 本身就是内部 backend/leaf worker，不是浏览器 BFF。业务接口和 operator 接口都要求内部 token，首选 `Authorization: Bearer <token>`，兼容 `X-MKB-Internal-Token`。鉴权在资源读取之前执行；operator 路由还要求 ASGI peer 为 loopback/private/internal 地址。`X-Forwarded-For` 只在 peer 属于 `MKB_TRUSTED_PROXY_CIDRS` 时才被采用；空 CIDR 永不复制 XFF。`deployment_role` 不是 HTTP 用户角色。

### 9.2 探针与运维路由

| 路由 | 方法 | 鉴权 / 说明 |
|---|---|---|
| `/live`、`/healthz` | GET | 无依赖存活探针 |
| `/ready` | GET | 分组件 readiness；ready 为 200，否则 503。响应附带 `deployment_role` / `owned_loops` / `capability_manifest_digest` / `claimable_process_keys` |
| `/metrics` | GET | 仅 internal peer；可配置额外 bearer |
| `/docs`、`/redoc`、`/openapi.json` | GET | FastAPI 默认文档面；当前未单独关闭或鉴权，部署边缘需限制网络 |

`/ready` 始终列出 15 个分量：BASE 为 `schema_migration`、`registry_bootstrap`、`db_primary`、`write_path_ready`、`native_vector`、`object_root`、`inference_binding`、`obs_tables`、`sec_token_loaded`、`workflow_supervisor`；SUPPLY 为 `supply_pdf_parse`、`supply_browser_render`、`supply_browser_print_pdf`、`supply_ocr_deterministic`、`supply_s11_multimodal`。默认 `deployment_role=all` 且 `MKB_RUNTIME_SUPPLY_READINESS_REQUIRED=false` 时，**只有 BASE 参与 admission**（`all` 角色下 `workflow_supervisor` 恒为真）。`api` / `maintenance` 会去掉 `workflow_supervisor` 与 `inference_binding`。生产 profile 才把 supply 分量变成硬闸；`multimodal_enabled=false` 或 `generation_local_enabled=false` 时不会要求 `supply_s11_multimodal`。业务 UoW 走 `BEGIN IMMEDIATE`；即使 `MKB_CONCURRENT_WRITES_REQUIRED=true`，admission 也不把 `concurrent_writes=true` 当作就绪条件。

### 9.3 公共 `/v1` 路由

| 资源 | 路由与方法 | 说明 |
|---|---|---|
| Catalog | `GET /v1/catalog`、`GET /v1/capabilities` | 能力 / 工作流 / source-kind 发现；不暴露 graph selector |
| Intake / Namespace | `GET /v1/teams/{team_uuid}/intake-items`、`GET .../namespaces` | Item 分页与 active Layer A 列表 |
| Team | `POST/GET /v1/teams` | 创建/列出 Team |
| Team | `GET/PATCH/DELETE /v1/teams/{team_uuid}` | 读取、乐观 revision 更新、逻辑删除 |
| Team lifecycle | `POST .../{team_uuid}:activate|:deactivate|:restore` | 显式状态转换 |
| Object | `POST .../objects:upload`、`GET .../objects:stat`、`POST .../objects:cancel` | streaming CAS 上传、stat、取消；无 download |
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

Task `request_intent` 是闭集：`intake.ingest`、`intake.rebuild`、`intake.update_metadata`、`intake.deactivate`、`intake.reactivate`、`intake.delete`、`index.rebuild`。创建合同必须包含 `mkb.task.v1`、匹配 path 的 Team UUID、Task/trace UUID、intent 对应 payload 和 `mkb.task-audit.v1` audit。`Ready` 闸门用在 upload、create/retry Task、gate decide 与 retrieval。

对象上传：禁止 multipart；可选 `x-mkb-expected-sha256` 与 `Idempotency-Key`。有 idempotency key 时返回 `session_token`；无 key 时走 digest replay，不发 session。投影只含 handle / digest / disposition（`pending|ingested|expired|tombstoned`），从不返回 raw bytes 或宿主路径。

### 9.4 内部 `/internal` 路由

| 路由组 | 方法 | 用途 |
|---|---|---|
| `/internal/nhx1/cutover`、`/inventory`、`:begin-shadow`、`:stop-admission` | GET/POST | NHX1 shadow / activate / drain；默认状态 `legacy/legacy` |
| `/internal/teams/{team_uuid}/processes/{process_uuid}` 等 | GET | Process / Execution / Cleanup 脱敏调试投影 |
| `/internal/teams/{team_uuid}/outbox/{outbox_id}:requeue` 等 | POST | outbox 再入队、cleanup resume、execution stop、process restart |
| `/internal/prompts`、`/internal/prompts/{prompt_id}` | GET/POST/PATCH/DELETE | prompt catalog 运维，不接收 prompt 正文字节 |
| `/internal/teams/{team_uuid}/traces/{trace_uuid}/timeline` | GET | trace 时间线 |
| `/internal/teams/{team_uuid}/tasks/{task_uuid}/timeline` | GET | Task 事件/诊断时间线 |
| `/internal/teams/{team_uuid}/outbox/dead` | GET | dead outbox 读取 |
| `/internal/teams/{team_uuid}/security-audit` | GET | 安全审计读取 |

### 9.5 外部依赖与第三方接口

| 集成 | 配置 / 输入 | 当前状态 |
|---|---|---|
| 本地 vLLM OpenAI-compatible API | `MKB_INFERENCE_VLLM_BASE_URL`、token/secret-file | adapter 已落地；cuts schema 显式透传；真实 R4 生成链未通过验收 |
| NS1 agent CLI | `MKB_NS1_CLI_MODE=subprocess`、`MKB_NS1_PROVIDER_PLAN`、`MKB_NS1_PRIMARY_MODEL` | 无 shell 调用，material 走 stdin；Claude `minimax-m3` 主路，Agy 备路，cursor-agent/Grok 轮换 fallback；部署 executable 与真实 E2E 仍需验证 |
| 本机 PDF / browser / OCR | `MKB_PDF_PARSER_*`、`MKB_BROWSER_*`、`MKB_DETERMINISTIC_OCR_*` | default-root `discover()`；缺 binary 则该能力不可用。Tech Stack manifest 尚未冻结 |
| 任意 HTTPS 来源 | `http_resource.url` | 受 SSRF/redirect/size 策略约束的 server-side GET |
| chinatax/domain/realestate | 调用方提交冻结 `records[]` | 只有 raw schema + scatter，不含供应商 token/client/pagination 请求 |
| Turso Database | 本地 DB 文件 | `pyturso` embedded 主路径；cloud replica 未接入 |

应用没有第三方 token 缓存层、浏览器 CORS consumer 或公开 raw-vector/object CRUD。

## 10. 安装、运行、测试与部署

### 10.1 前置条件

- Python 3.12；3.11 和 3.13 不在项目声明范围。
- [uv](https://docs.astral.sh/uv/)；依赖以仓库内 `uv.lock` 为准。
- 默认离线启动不需要 GPU、vLLM、CLI、浏览器或 OCR binary。
- 生产生成路由需要部署方提供 Claude/Agy/cursor-agent/Grok executable 与 MiniMax 配置；Qwen local embedding 仍需要兼容 local-vLLM endpoint、模型和 secret，并先通过探针/评估。

### 10.2 安装与本地启动

```bash
uv sync --extra dev

# Settings 不会自动加载 .env；请在启动进程前 export。
export MKB_INTERNAL_TOKENS='replace-with-a-local-secret'
export MKB_DATA_DIR='data'
export MKB_LIVE_INFERENCE='false'             # offline deterministic embedding
export MKB_GENERATION_LOCAL_ENABLED='true'   # local development compatibility
export MKB_MODEL_CAPACITY_PRIORITY_GATE_ENABLED='false'
export MKB_NS1_CLI_MODE='stub'

uv run mkb
```

服务默认监听 `http://127.0.0.1:8080`。TrustedHost 默认允许 `localhost` 与 `127.0.0.1`。开发时也可运行：

```bash
uv run uvicorn api.app:app --host 127.0.0.1 --port 8080 --reload
```

另一个终端执行：

```bash
curl -fsS http://127.0.0.1:8080/live
curl -fsS http://127.0.0.1:8080/ready
```

`/ready` 必须返回 200 后再创建 Task 或上传对象。首次启动会创建/迁移 `data/database/mkb_primary.db` 和对象根；两者均是运行时数据，不应提交。默认离线 profile 不要求 PDF/browser/OCR/multimodal 分量为真。

### 10.3 最小 API 旅程

下面使用 UUIDv4（API 同时接受 v4/v7）创建 Team、提交 inline ingest，再轮询并检索。示例依赖本机 Python 3.12 与较新的 curl。离线 stub 必须带 Layer A namespace；省略会 `422 RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`。

```bash
export MKB_BASE_URL='http://127.0.0.1:8080'
export MKB_TOKEN='replace-with-a-local-secret'
export TEAM_UUID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"
export TASK_UUID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"
export TRACE_UUID="$(uv run python -c 'import uuid; print(uuid.uuid4())')"
export CREATED_AT="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
# 离线 deterministic embed 的 Layer A key；live 模式不要复用这个值。
export NAMESPACE_KEY='deterministic-hash-v1|v1|deterministic|64'

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
        \"media_type\": \"text/plain\",
        \"realm\": \"documentation\",
        \"type\": \"article\",
        \"channel\": \"knowledge-base\",
        \"source_name\": \"readme-quickstart\",
        \"context_tags\": [\"product:mkb\"]
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
    \"schema_version\": \"mkb.retrieval.v2\",
    \"team_uuid\": \"$TEAM_UUID\",
    \"namespace_key\": \"$NAMESPACE_KEY\",
    \"query\": \"分层检索上下文\",
    \"filters\": {\"realm\": \"documentation\", \"vector_channel\": \"summary\"},
    \"return_k\": 3,
    \"recall_k\": 5
  }"
```

创建接口对相同身份和相同内容支持幂等 replay；重用 UUID 却改变内容会产生冲突。若 Task `failed`，先读取 Task result、generation artifacts 和 internal timeline，而不是直接改数据库。`local_object` 路径应先 `objects:upload` 再 ingest，不要把上传当成摄取完成。

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

| 层 | 覆盖 | 2026-09-06 @ `71f3555` 收集 / 最近全量执行 |
|---|---|---|
| `tests/unit` | 合同、服务、engine、security、registry、persistence、NS/NH/NHX1 原语 | 637 collected |
| `tests/domain` | 领域状态机、不变量、evidence harness | 82 collected |
| `tests/integration` | 跨服务/持久化组合、migration parity、cutover | 77 collected |
| `tests/intake` | 来源类型与清洗 | 19 collected |
| `tests/e2e` | 完整 Task、scatter、lifecycle、publication、retrieval、crash/race | 195 collected |
| 全量 `pytest` | 全仓 1010 个 collected case | 最近一次全量执行：2026-08-31 @ `d843f00` → **`1010 passed / 0 failed / 0 skip / 0 xfail`**。HEAD `71f3555` 相对该提交仅为文档，collect-only 仍为 1010 |
| Ruff | `E/F/I/UP/B` | 本次 `uv run ruff check .` 为 `All checks passed` |
| `uv build` | sdist + wheel | 包装范围 `api*` / `src*` / `intake*`；wheel 含 `001`–`029` SQL、`src/contracts/lsrag/*.json`、`src/workflows/*.json`；`project.license` TOML table 仍有 setuptools deprecation warning |
| R4 live cells | 真实 prompt/inference 生成 | 4/4 未通过；既有 corpus retrieval 6/6 为 HTTP 200，不能据此宣称端到端 live |
| R7 live cells | 系统 g0 + cuts + 10k 分段 | 2026-08-28 实弹 4/4；按 `T-O-376` **不等于** 四通道接通 |
| NH7 default-root L4 | 10 CleanStrategy + 3 registered-api 到 retrieval | 战役 L4 通过；使用 fixture/stub，不是 0815 真模型 |
| NHX1 P9 | closed-set / race / SIGKILL / persisted upgrade | 本地 assurance 通过；final close 仍 blocked |

测试默认静态配置写在 `pyproject.toml`。pytest fixture 可以选择 stock SQLite；生产/普通本地服务必须走 Turso 路径。FastAPI TestClient 当前会发出 Starlette 的 `httpx` → `httpx2` deprecation warning，不影响断言。

### 10.6 构建与部署

`uv build` 生成标准 sdist 与 wheel，包范围为 `api*`、`src*`、`intake*`，并打包 `src/persistence/migrations/*.sql`、`src/contracts/lsrag/*.json` 与 `src/workflows/*.json`。运行还需要 checked-in `data/prompts`、`data/config`、`data/schemas`，因此单独复制 wheel 并不等于完整部署制品；部署必须显式挂载/打包这些资源并提供可写 DB/object 路径。

仓库当前没有容器、systemd、Kubernetes、CI/CD、反向代理或 hosting manifest，也没有 deploy 命令和生产 URL。部署方需自行负责进程守护、TLS、网络 ACL、可信代理 CIDR、secret 注入、数据卷、备份与恢复，以及（若启用）PDF/browser/OCR/multimodal binary。完成这些工作前不能把本仓状态标为 production/live。

## 11. 安全与配置策略

### 11.1 配置加载时机

项目没有前端或构建时公开变量。所有 `Settings` 都在服务进程组合时读取，统一映射为 `MKB_<FIELD_NAME>`，不暴露给浏览器。由于模块级 `api.app:app` 会在 import 时构造容器，环境变量必须在 `uv run mkb` 或 Uvicorn 启动之前设置。

`SettingsConfigDict` 当前没有 `env_file`，所以仅复制 `.env.example` 为 `.env` **不会自动生效**。可使用 shell `export`，或显式让进程管理器/Uvicorn 加载 env file。`.env.example` 只列 8 项，不含 role / supply / browser / OCR / multimodal / upload TTL。

### 11.2 环境变量参考

| 变量 | 默认值 | 说明 |
|---|---|---|
| `MKB_INTERNAL_TOKENS` | 空 | 逗号分隔 active bearer；服务 ready 至少需要有效 token |
| `MKB_INTERNAL_TOKEN` / `MKB_INTERNAL_TOKEN_PREVIOUS` | 空 | 单 token 与轮换兼容槽；合并后最多允许两个不同 active token |
| `MKB_DATA_DIR` | `data` | 默认运行时数据根 |
| `MKB_DATABASE_PATH` | `<data_dir>/database/mkb_primary.db` | 本地 Turso 数据库文件 |
| `MKB_OBJECT_ROOT` | `<data_dir>/objects` | 本地 CAS 根 |
| `MKB_PERSISTENCE_BACKEND` | `turso` | `sqlite` 只允许 pytest 环境；`MKB_ALLOW_SQLITE` 不是许可因子 |
| `MKB_CONCURRENT_WRITES_REQUIRED` | `true` | 保留能力探针；`/ready` 用 `write_path_ready` 做 admission |
| `MKB_NATIVE_VECTOR_REQUIRED` | `true` | readiness 必须证明 native vector capability |
| `MKB_VECTOR_BACKEND` | `deterministic_exact` | 当前 scan profile，不是 ANN 性能证明。`native_ann` 会在 composition 被拒绝：VectorSearchPort 未实现 |
| `MKB_DEPLOYMENT_ROLE` | `all` | `api` / `workflow_worker` / `maintenance` / `all`；控制进程循环所有权 |
| `MKB_RUNTIME_PROFILE` | `dev` | `test` / `dev` / `prod`；`prod` 强制 subprocess CLI、supply ready、local generation off 与容量 priority gate |
| `MKB_WORKER_CAPABILITY_ALLOWLIST` | 空 | 逗号分隔 process_key；收窄 workflow-worker claim 面 |
| `MKB_SUPERVISOR_FAILURE_THRESHOLD` | `3` | `workflow_worker` 角色下 supervisor 连续失败阈值 |
| `MKB_PROMPT_ROOT_PATH` | 仓库 `data/prompts` | 可显式挂载另一个经审计 prompt tree |
| `MKB_CONFIG_ROOT_PATH` | 仓库 `data/config` | 可显式挂载配置根 |
| `MKB_INFERENCE_VLLM_BASE_URL` | `http://127.0.0.1:668` | origin，不要带 `/v1`；adapter 自行追加路径 |
| `MKB_INFERENCE_VLLM_TOKEN` | 空 | 首选 deploy-injected bearer，`SecretStr` 持有，不进入 DB/snapshot |
| `MKB_INFERENCE_SECRET_SLOT` / `MKB_INFERENCE_SECRET_FILE` | 空 | token 未设置时的成对 file fallback |
| `MKB_INFERENCE_PROBE_ENABLED` | `false` | 为真时 readiness 探测实际 active model binding |
| `MKB_LIVE_INFERENCE` | `false` | 仅控制 Qwen live embed/vectorize；假时使用 deterministic hash。不要用它关闭生成 |
| `MKB_GENERATION_LOCAL_ENABLED` | `true` | 是否允许新 generation Process 进入 Qwen/local-vLLM；生产应为 `false` |
| `MKB_MODEL_CAPACITY_PRIORITY_GATE_ENABLED` | `false` | 为真时 model-bearing normal/low API 请求返回 `429 MODEL_AT_CAPACITY` |
| `MKB_NS1_CLI_MODE` | `stub` | `stub`、`subprocess` 或 `disabled`；独立于 `LIVE_INFERENCE` |
| `MKB_NS1_CLI_EXECUTABLE` | `claude` | subprocess 模式的可执行文件，不经过 shell |
| `MKB_NS1_PROVIDER_PLAN` | `claude,agy,cursor-agent,grok` | 新生成 provider 顺序；fallback 仅处理容量/传输类错误 |
| `MKB_NS1_PRIMARY_MODEL` | `minimax-m3` | Claude 主路模型名 |
| `MKB_NS1_AGY_EXECUTABLE` / `MKB_NS1_CURSOR_AGENT_EXECUTABLE` / `MKB_NS1_GROK_EXECUTABLE` | `agy` / `cursor-agent` / `grok` | 备选 CLI executable，不经过 shell |
| `MKB_NS1_CLI_MAX_CONCURRENCY` | `8` | 所有 NS1 CLI provider 总并发上限 |
| `MKB_NS1_CLAUDE_CONCURRENCY` / `MKB_NS1_AGY_CONCURRENCY` | `3 / 2` | Claude / Agy provider 并发上限 |
| `MKB_NS1_FALLBACK_CONCURRENCY` | `3` | cursor-agent / Grok 各自并发上限 |
| `MKB_INFERENCE_GENERATE_TIMEOUT_SECONDS` | `180` | 生成调用超时，范围 1–3600 秒 |
| `MKB_MULTIMODAL_ENABLED` | `false` | 为真才构造 S11 clean LLM |
| `MKB_MULTIMODAL_MODEL_KEY` / `MKB_MULTIMODAL_MODEL_VERSION` | Qwen2.5-VL pinned | 禁止 `latest` |
| `MKB_MULTIMODAL_CONCURRENCY` | `2` | multimodal 池 |
| `MKB_DETERMINISTIC_OCR_ENABLED` | `true` | 是否尝试 discover OCR |
| `MKB_DETERMINISTIC_OCR_TIMEOUT_SECONDS` / `MKB_DETERMINISTIC_OCR_CONCURRENCY` | `10 / 2` | OCR 超时与并发 |
| `MKB_RUNTIME_SUPPLY_READINESS_REQUIRED` | `false` | 为真且角色 owns claims 时，PDF/browser/OCR（及可选 multimodal）进入 `/ready` 硬闸 |
| `MKB_DISPATCH_LOCAL_RUNNING` / `MKB_DISPATCH_LOCAL_QUEUED` | `2 / 6` | local generation 池容量 |
| `MKB_DISPATCH_NI_RUNNING` / `MKB_DISPATCH_NI_QUEUED` | `2 / 4` | non-interactive 池容量 |
| `MKB_DISPATCH_EMBED_RUNNING` / `MKB_DISPATCH_EMBED_QUEUED` | `8 / 20` | embedding 池容量 |
| `MKB_DISPATCH_LOCAL_CHAR_BUDGET` | `16000` | local pool 同时在途字符预算 |
| `MKB_INFERENCE_MAX_IN_FLIGHT` / `MKB_INFERENCE_MAX_ATTEMPTS` | `12 / 3` | facade 总并发与最大尝试次数 |
| `MKB_OBJECT_MAX_BYTES` | `268435456` | 单 CAS 对象上限，默认 256 MiB |
| `MKB_OBJECT_UPLOAD_PENDING_TTL_SECONDS` | `86400` | 未被 ingest/cancel 的 upload pending hold 生存期；到期后才 release 并开始 GC grace |
| `MKB_OBJECT_STAGING_TTL_SECONDS` | `3600` | 中断上传遗留 staging 文件的回收时限；staging 从不进入 catalog |
| `MKB_MAX_REQUEST_BYTES` | `1048576` | HTTP 请求体上限，默认 1 MiB；超限 413。`objects:upload` 例外，按对象上限流式计数 |
| `MKB_HTTP_TRUSTED_HOSTS` | `localhost,127.0.0.1` | TrustedHost allowlist；pytest 会额外允许 `testserver` |
| `MKB_TRUSTED_PROXY_CIDRS` | 空 | 非空且 peer 命中时才信任 `X-Forwarded-For`；空值永不复制 XFF |
| `MKB_RATE_LIMIT_IP_PER_MIN` | `120` | 进程内固定窗口 IP 限流 |
| `MKB_RATE_LIMIT_TOKEN_PER_MIN` | `600` | token fingerprint 限流 |
| `MKB_RATE_LIMIT_WINDOW_SECONDS` | `60` | 限流窗口 |
| `MKB_METRICS_REQUIRE_TOKEN` | `false` | `/metrics` 始终要求 internal peer；为真时再要求 bearer |
| `MKB_EGRESS_MAX_REDIRECTS` | `3` | 出站 HTTP 重定向上限，最大也为 3 |
| `MKB_EGRESS_ALLOW_LITERAL_IP` | `false` | 是否允许 URL literal IP |
| `MKB_EGRESS_ALLOW_PRIVATE_DEFAULT` | `false` | 是否默认允许私网目的地址 |
| `MKB_EGRESS_ALLOW_HTTP` | `false` | 是否允许明文 HTTP |
| `MKB_ACQUISITION_MAX_RESPONSE_BYTES` | `8388608` | 来源响应上限，默认 8 MiB |
| `MKB_PDF_PARSER_ENABLED` | `true` | 是否尝试 discover isolated PDF parser |
| `MKB_PDF_PARSER_BINARY` / `MKB_PDF_PARSER_TIMEOUT_SECONDS` / `MKB_PDF_PARSER_CONCURRENCY` | 空 / `8` / `2` | parser 路径、超时与并发 |
| `MKB_BROWSER_RUNTIME_ENABLED` | `true` | 是否尝试 discover hardened browser |
| `MKB_BROWSER_BINARY` / `MKB_BROWSER_WEBDRIVER_BINARY` | 空 | 显式 binary；未设则走 discover |
| `MKB_BROWSER_RENDER_TIMEOUT_SECONDS` / `MKB_BROWSER_PRINT_TIMEOUT_SECONDS` | `20 / 30` | render / print 超时 |
| `MKB_BROWSER_RENDER_MAX_BYTES` / `MKB_BROWSER_PRINT_MAX_BYTES` | `8 MiB / 32 MiB` | 输出上限 |
| `MKB_BROWSER_RENDER_CONCURRENCY` / `MKB_BROWSER_PRINT_CONCURRENCY` | `2 / 1` | 浏览器池 |
| `MKB_OBJECT_GC_ENABLED` | `true` | 是否启动 orphan object GC（兼管 upload lifecycle scanner） |
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

注意：当前 [`.env.example`](.env.example) 把 vLLM URL 示例写成端口 `670`，而 `Settings` 与 [`data/config/default.toml`](data/config/default.toml) 的默认端口是 `668`。部署时必须显式选定真实 endpoint，不要把示例端口误认为运行真源。cutover 没有独立 env，状态在表 `mkb_nhx1_cutover_state`，默认 key `"nhx1"`。

### 11.3 密钥与审计政策

- real token 不得提交到 `.env.example`、配置、prompt、Task payload、数据库或 artifact。
- inference token 优先来自环境变量；secret file 只能与逻辑 slot 成对配置，内容不会进入 durable snapshot。
- active internal token 以 SHA-256 fingerprint 比较并使用 constant-time 校验；支持双 token 平滑轮换。
- 公共错误、事件和诊断对 token/secret/connection/presigned URL/宿主绝对路径做递归脱敏（redaction）或拒绝。
- 鉴权失败会写受采样控制的安全审计；关键 auth audit 无法持久化时 fail closed。限流器记账异常会降级并暴露 metric，但不会跳过 token 鉴权。

### 11.4 网络、CORS 与响应头

应用现在安装 `TrustedHostMiddleware`（默认 `localhost,127.0.0.1`），并在 ASGI 层拒绝超过 `MKB_MAX_REQUEST_BYTES` 的普通请求体。唯一例外是受鉴权 `objects:upload`：请求体不被全量缓存，而由 streaming CAS 按 `MKB_OBJECT_MAX_BYTES` 独立计数。它仍然没有 CORS middleware、HTTPS redirect middleware，也没有显式 CSP、HSTS、X-Frame-Options 等响应头。既定姿态是只在受控内部网络提供服务，而不是直接暴露到浏览器或公网。生产边缘仍需承担 TLS、Origin 策略、安全头、超时限制、可信代理 CIDR 配置，以及 `/docs`/`/metrics` 网络隔离。

## 12. 已知事项与设计取舍

### 12.1 设计亮点

- **历史不会漂移**：prompt/model/workflow/config 都以 identity、revision 和 digest 冻结；hash/supply 不匹配时失败关闭。
- **状态与字节分离**：关系事实进 Turso，内容进 team-scoped CAS；原子 promote、引用计数语义和 grace GC 降低半提交风险。公共上传只给 handle，不给 raw read。
- **检索不越权**：publication fence 与 intake lifecycle fence 同时生效；Layer A namespace 必须显式选择，停用/删除内容不会因旧向量仍在而继续 serving。
- **失败也是证据**：Task/Process、outbox、generation invocation、stage report、domain event、diagnostic log 和 security audit 提供分层诊断面。
- **内部身份不外泄**：公共 API 围绕 Team/Task/业务 artifact，Execution/Process 留在 runtime/observability 边界内。
- **可恢复演进**：新 workflow revision 不覆盖旧图，in-flight/frozen Execution 仍可按原 definition 恢复；kind-family 成为新准入，旧 profile 不被暗中改写。
- **g0 由系统持有**：quoted cuts 把「默写全书」从模型职责里拿掉，admit 规则保持不变。
- **缺供给就拒绝**：browser/OCR/PDF/Vision 不再靠静默降级或 monkeypatch 冒充；`discover()` 失败走 typed 503。

### 12.2 已知问题与待验证项

| 编号 | 事项 | 当前影响 | 关闭 / reopen 触发器 |
|---|---|---|---|
| K1 | 全量 pytest 已从历史 `11 failed` 收成 `1010 passed` | 本地回归不再是红灯；这只证明已执行断言通过，不能代替独立审查或 0815 级综合实验 | 回归时保持 0 fail / 0 skip / 0 xfail；新债必须 RED-first 入账 |
| K2 | Ruff 静态门 | 本次 `uv run ruff check .` 为 0 | 回归时保持 0 |
| K3 | R4 四个 live cell 均失败 | 真实 A/Markdown/B/C 链不能称为 live；失败包括 g0 anchor/granularity 与 Claude CLI empty result | 修复并重跑 [`after-MKB-0815-R4-first-wave.md`](docs/eval/new-start/after-MKB-0815-R4-first-wave.md) 中的 corpus/cell；R5/R7 代码相或 inline 实弹不能代替这次记分 |
| K4 | R7 已发车（2026-08-28） | R7 四格实弹 4/4 入库（88→174 向量、检索无 422），见 [`NS9-0815-R7-live-firing-closure.md`](docs/closure/new-start/NS9-0815-R7-live-firing-closure.md)；按 `T-O-376` **不等于** 四通道接通 | 已闭合为 inline generation 证据；后续四通道 live 另开 0815 级实验 |
| K5 | browser/OCR/Vision/doc-LLM 已接线，但生产供给未闭合 | default-root 已 `discover()`；缺 binary/模型会稳定拒绝。S16 egress/browser 未签；Tech Stack manifest 未冻结；战役 L4 使用 fixture/stub | 冻结真实组件 digest/SBOM，完成 S16 具名签收，并用真模型重跑 10+3 L3/L4 |
| K6 | registered API 没有供应商客户端 | 不能实时调用 chinatax/domain/realestate；分页与 exhaust 由调用方冻结证明 | 若产品要求实时连接器，另建 token/client/retry/pagination/egress 边界并验收 |
| K7 | `.env.example` 端口与 Settings 默认不一致，且 `.env` 不自动加载；示例也未列 role/supply knobs | 新贡献者可能连接错误 endpoint 或以为配置已生效 | 统一端口/加载政策并加配置测试；此前以 `Settings` 和显式 export 为准 |
| K8 | 无部署制品、生产 URL、TLS/CORS/CSP | TrustedHost 与请求体上限已在应用内；仍不是公网就绪服务 | 增加经过 review 的部署/边缘配置、备份恢复和生产 smoke |
| K9 | `/docs`、`/redoc`、`/openapi.json` 使用 FastAPI 默认开放策略 | 内网可用，但若误暴露会扩大接口枚举面 | 在部署 edge 限制或由应用显式关闭/鉴权 |
| K10 | billing 是 always-permit stub | 没有额度、结算或真实 admission 计费能力 | 产品要求 billing 时替换 [`src/services/billing.py`](src/services/billing.py) 并补 fail-closed policy |
| K11 | 并发/GPU/云侧证据不完整 | 业务写路径是序列化 `BEGIN IMMEDIATE`；cloud replica、urgent starvation aging、GPU soak 未完成；`native_ann` 配置值会被 composition 拒绝 | 对目标部署形态完成 soak 和故障注入，记录可复现证据 |
| K12 | `frontend/` 与 `public/` 只是占位 | 没有最终用户 UI、SEO、i18n 或静态内容产品 | 只有产品范围正式加入 UI 时才实现；否则保持空边界 |
| K13 | 总 spec index、D06/D07/D08 与 release 签署尚未 frozen | domain truth 仍有 owner-review 草案；D07 定义验收标准，但不证明这些标准已经通过。new-harvest 没有回写 [`spec-index.md`](docs/baseline/spec-index.md) | 完成 owner freeze、P0–P4 所需证据或正式 waiver，并更新 spec-index |
| K14 | `pyproject.toml` 使用已弃用的 license table 写法 | 当前 build 成功，但 setuptools 提示 2027-02-18 后将不再支持 | 在截止日前改为 SPDX string / `license-files`，并复跑 `uv build` |
| K15 | NHX1 closure evidence 不完整 | 代码与本地 `1010 passed` 已在；缺独立二次审查、0815 级 NHX1 实验、Tech Stack manifest、CLI 组合验证、声明式 workflow↔策略入库证明、逐 Test-ID 四元组。官方 close-type 为 `implementation-complete-awaiting-live-verification` | 先补 [`NHX1-closure-gaps.md`](docs/closure/new-harvest/NHX1-closure-gaps.md) 第 2 节 1–6 项内部证据；再由业主决定是否追加、移除或重定义 `T-O-419` / `NHX1-T22-O`。不得伪造 full-close |
| K16 | S16 egress/browser 与 experiment 发车仍 owner-gated | NH6/NH9 把签收栏留下但未伪造签名；`.experiment` 日期/分数仍 null（`T-O-380`） | 具名 S16 attestation 与独立 experiment charter；二者都不进入当前 HEAD 的已落地谓词 |
| K17 | raw object GET/export/list/presign 与 remote R2 | 公共对象面只有 upload/stat/cancel | 产品明确要求导出面时另开 charter；禁止借 ingest/retry 偷渡 |
| K18 | existing-object 新 cleaner upgrade 明确 OOS | 不能借 rebuild/retry 给旧对象换新清洗器（`T-O-401` / `T-O-420`） | 另开 owner-gated charter |

### 12.3 明确的非目标

- MKB retrieval 只返回 grounded context，不负责生成最终回答或维护聊天会话。
- MKB 不提供终端用户身份、组织成员、平台 RBAC、计费产品或浏览器登录。
- MKB 不提供公开的原始对象上传字节回读、向量 CRUD 或数据库管理 API。
- MKB 不把 plan、closure、已有冻结 corpus、一次成功 retrieval，或 0815-R7 inline 4/4 当成当前四通道端到端 live 证明。
- MKB 是单应用、单部署单元；`deployment_role` 只描述同一二进制的进程所有权，当前没有把 API、worker 和 scheduler 拆为分布式服务的承诺。
- MKB 不把本地 `1010 passed` 或执行者自审当成 NHX1 full-close。

## 13. 总体评价

当前 HEAD 已形成一套边界清晰、证据优先的有状态 LS-RAG 内部工作器：合同、耐久执行、Turso/CAS、分层生成、发布栅栏、检索和审计面彼此衔接。NS5–NS9 把 cancel、CAS、XFF、publication fence、系统写 g0、quoted cuts 和 R7 inline 实弹收成内核。new-harvest 把四 kind 清洗、kind-family 工作流、representation / S05、公共对象生命周期、语义 facet 与 default-root 供给接线写入主链；NHX1 再把 Observation/ItemEpoch、对象 session、证据平面、部署角色、发现/运维面与 cutover 补进 025–029。离线 deterministic 配置适合本地开发；全仓测试记录为 `1010 passed`，Ruff 为 0。

它还不是可对外宣称 production/live 的完整产品：R4 真实推理链失败，R7 只证明 inline generation 而不是四通道接通，browser/OCR/Vision 虽已接线但生产 binary / S16 / Tech Stack 未闭合，NHX1 closure evidence 不完整，部署和边缘 TLS 也不在仓库内。下一阶段最有价值的工作是补齐 NHX1 内部验收证据与真实供给签收，而不是扩大公开接口面。

## 附录 A：文档与真相层导航

| 目录 / 文档 | 应如何使用 |
|---|---|
| [`docs/baseline/spec-index.md`](docs/baseline/spec-index.md) | 设计文档入口；索引本身尚未 frozen |
| [`docs/baseline/domain-truth/`](docs/baseline/domain-truth/) | D01–D08、S01–S16 的领域/子系统真相层 |
| [`docs/baseline/qna-truth/`](docs/baseline/qna-truth/) | owner 问答与决策证据，不自动代表实现 |
| [`docs/closure/`](docs/closure/) | 阶段性 closure、handoff、deferred ledger；历史结论需与当前 HEAD 复核 |
| [`docs/closure/0820-review/`](docs/closure/0820-review/) | NS5/NS6 0820 修复收口 |
| [`docs/closure/new-start/NS9-0815-R7-live-firing-closure.md`](docs/closure/new-start/NS9-0815-R7-live-firing-closure.md) | R7 实弹 4/4；只证明 inline generation |
| [`docs/closure/new-harvest/`](docs/closure/new-harvest/) | NH1–NH9、CROSS-NH 与 NHX1 收口；NHX1 不是 full-close |
| [`docs/closure/new-harvest/NHX1-closure-gaps.md`](docs/closure/new-harvest/NHX1-closure-gaps.md) | NHX1 内部 closure 缺口；优先于「只差 T22-O」 |
| [`docs/evidence/new-harvest/`](docs/evidence/new-harvest/) | 战役四元组（manifest / tests / queries / security）；CROSS-NH 仅有 review |
| [`docs/eval/`](docs/eval/) | 实际运行分析、live cell 结果和后续评估 |
| [`docs/eval/new-start/R5-system-g0-and-quoted-cuts.md`](docs/eval/new-start/R5-system-g0-and-quoted-cuts.md) | R5 施工台账；页眉 `WAIT_OWNER_TO_EXECUTE` 只约束 live 枪，不否定代码已存在 |
| [`docs/eval/new-harvest/final-execution-plan.md`](docs/eval/new-harvest/final-execution-plan.md) | NH1–NH9 冻结执行基线；不是当前 HEAD 的实现证明 |
| [`docs/eval/new-harvest/pre-initial-planning-qna.md`](docs/eval/new-harvest/pre-initial-planning-qna.md) / [`pre-charter-qna.md`](docs/eval/new-harvest/pre-charter-qna.md) / [`pre-NHX1-qna.md`](docs/eval/new-harvest/pre-NHX1-qna.md) | `T-O-376..422`；QNA 冻结 ≠ 已实现 |
| [`docs/plan/`](docs/plan/) | 待执行或已执行方案；不能作为已落地证据 |
| [`docs/plan/new-harvest/todo-list.md`](docs/plan/new-harvest/todo-list.md) | NH1–NH9 全 `[x]`；`NHX1-P9` / `NHX1-FINAL-CLOSE` 仍 `[!]` |
| [`docs/code-review/`](docs/code-review/) | 外部/交叉 code review 记录，含 `0820-review/`、`new-start/`、`new-harvest/` |
| [`docs/runbooks/new-harvest/phase7-signals.md`](docs/runbooks/new-harvest/phase7-signals.md) | NHX1 P7 运维信号；SSOT 在 [`src/runtime/signals.py`](src/runtime/signals.py) |
| [`docs/verification/`](docs/verification/) | Schema 与 workflow 合同核对笔记 |

若代码、测试和文档口径冲突，先以可执行代码和当前复现实证界定“现状”，再回到 domain truth/owner decision 判断“应当是什么”；不要用 draft plan 反向声明代码已经完成。

## 附录 B：修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|---|---|---|---|
| v1.0 | 2026-08-20 | Codex（按 MKB maintainers 委托） | 扫描全仓并按架构 README 模板重写；对齐 `5e64a1e` 的 API、运行时、配置、测试和 R4/R5 状态 |
| v1.1 | 2026-08-21 | Grok（按 MKB maintainers 委托） | 对账 `86037dd`：FastAPI 0.141.1、migration 001–017、g1 v5/cuts、必填 namespace、`write_path_ready`、TrustedHost/XFF/body cap、全量 `558/11`、Ruff 0；R5 改为代码已落地 / live 待验证 |
| v1.2 | 2026-08-28 | Antigravity Pair Engineer | R7 实弹 4/4（88→174 向量、Layer A 检索无 422）：系统写 g0/quoted cuts/10k 分段改 `已落地（live 已验证）`；发车中修复 NS9-FX1/FX2；全量 `561/11`（572 collected） |
| v1.3 | 2026-09-06 | Grok（按 MKB maintainers 委托） | 对账 `71f3555`：NH1–NH9 + CROSS-NH 收口，NHX1 P1–P9 代码落地但 closure 未齐；migration 001–029；18 个 active workflow + 19 条兼容 revision；公共 object/catalog/operator/cutover；browser/OCR/PDF 改 default-root 接线 / 条件可用；全量记录 `1010 passed`（`d843f00`），collect-only 仍 1010；Ruff 0；R7 仍成立且不等于四通道接通 |
| v1.4 | 2026-09-07 | MKB maintainers | 生成链增加 Claude `minimax-m3` / Agy / cursor-agent / Grok provider router、3/2/8 CLI 并发边界与容量 fallback；model-bearing normal/low admission 返回 `429 MODEL_AT_CAPACITY`；Qwen local generation 与 Qwen embedding 解耦，embedding 继续保持 local Layer A |