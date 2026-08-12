# D06 — Runtime Topology Constitution

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 共有域**：跨全部子系统的 **运行时拓扑、进程边界、资源挂载、网络暴露面与部署假设**
>
> **文档性质**：`shared-domain constitution / runtime topology truth`
>
> **文档状态**：`draft / owner-calibrated`（**未** owner-freeze；**未**自动替换索引 `17` 条目，直至本文件 accepted）
>
> **Truth 版本 / 日期**：`D06-v0.2-draft / 2026-08-12`
>
> **作者 / 裁决输入**：`MKB owner`（`ai-mkb` 容器 profile、模型分工、资源调配主权）+ `Grok`（规范化）
>
> **权威输入**：
>
> - Owner 方向：`OD-01` leaf-worker、`OD-06` 单体、`OD-07` adapter-first、`OD-10` Turso
> - Owner 本机推理拓扑（2026-08-12）：专用容器 **`ai-mkb`**；vLLM 外放 **668 / 669**；  
>   **embedding = qwen-vl-2b**；**主力 LLM = qwen35-a3b**（多路 inference + MTP + 充足 KV cache）；  
>   **运行 MKB 时停 ComfyUI** 释放统一内存/GPU；**宿主机资源由业主调配**
> - 兄弟单位运行证据：`/mnt/usb/workspace/myaidev/`（compose/scripts/recipes/observe_proxy；**ReferenceAnchor only**，非 MKB 代码依赖）
> - `D03-v1.0` / `D04-v1.1` / `D05-v1.0` / `S01` / `S11`–`S16` accepted formals
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.8+
>
> **下游消费者**：部署与运维、S11 adapter 默认、architecture tests（逻辑面）、`spec-index`、`18` 验收、实现脚手架
>
> **与历史 `17` 的关系**：本文件意图 **承接并 supersede** `specs/17-system-topology.md`。  
> accepted 后索引应 `17 ≡ D06`，禁止双源拓扑 SSOT。

> **★ 草稿声明**：`D06-T*` 为候选真相，**尚未**占用全局 `T-O-*`。冻结时自 **T-O-337** 起 append。  
> 标记：`【Owner】` 本轮业主强制；`【已继承】` 已冻 D/S 可唯一推导；`【草案】` 可配置细节；`【显式 OOS】` v1 不做。

> **★ 约束级别（冻结后）**：「必须 / 禁止 / 仅允许」= 强制；「应当」= 默认，偏离须 reopen D06。

> **★ 宿主机资源主权（Owner 强制 · 非 blocker 纪律）**  
> 1. **宿主机物理资源的时间片与进程组合由业主调配**（含是否停 ComfyUI、是否只跑 `ai-mkb`、磁盘/统一内存余量）。  
> 2. 任何时刻若观测到 **宿主机现状与本 topology 叙述不一致**（例如 ComfyUI 仍在跑、`:668` 未监听、另一 profile 占 GPU、swap 高），**不得**据此将 MKB 规格、实现、验收或 truth freeze 判为 **blocker / fail / 不可设计**。  
> 3. **当 MKB 处于计划运行窗口时，业主保证** `ai-mkb` 与本文件要求的 inference 能力 **已经可用**；规格层只定义 **运行契约**，不把「此刻 `docker ps` 快照」写成不变量。  
> 4. Architecture tests / CI **默认** mock 或对 **逻辑端口与 adapter 合同** 验收；**禁止** 把「开发机瞬时 GPU 空闲」写成 HARD gate。

---

## 0. 分账宪法

### 0.1 本域回答什么

D06 回答 **MKB 运行时与本机推理侧如何接在一起**：

1. MKB **写权威进程**（leaf-worker 单体）扮演什么；  
2. 专用推理容器 **`ai-mkb`** 扮演什么、暴露哪些端口与模型角色；  
3. embedding / LLM 如何分账到 vLLM 服务面；  
4. MKB 数据面（DB / object_root / prompts）如何挂载；  
5. 就绪语义如何 **消费** 推理侧，而非拥有 GPU 调度；  
6. 哪些资源冲突 **只归运维窗口**，不归规格 blocker。

### 0.2 双平面拓扑（强制心智）

```text
Plane A — MKB Application Plane（写权威 · 业务 SSOT）
  MKB leaf-worker process(es)
    api / runtime / services / persistence / storage
    data/database · data/objects · data/prompts · data/config

Plane B — Inference Plane（无业务 SSOT · Owner 容器）
  Docker container name/profile: ai-mkb
    family: myaidev / ai-dev 工作台上的专用 profile
    vLLM OpenAI-compatible HTTP
    host ports: 668 (vLLM) and/or 669 (observe proxy → 668)
    models (logical roles):
      · embed  : qwen-vl-2b
      · llm    : qwen35-a3b  (+ MTP, multi-request, ample KV cache)

Owner ops window:
  start ai-mkb  ⇒  stop comfyui (and any other GPU hogs)  ⇒  MKB may run
```

- **Plane A** 持有 Task/Intake/向量业务真相（S01–S16）。  
- **Plane B** **仅**提供 inference HTTP；**不得**成为 Task/Intake/Publication SSOT。  
- MKB **只经 S11 facade** 调用 Plane B；禁止 services 直连 vLLM。

### 0.3 与邻域分账

| 邻域 | 拥有 | D06 |
|---|---|---|
| **D03** | 路径名字与模块职责 | 挂载如何指向 D03 路径 |
| **D04/S12** | `mkb_primary`、TX、同进程写纪律 | 应用面写权威进程假设 |
| **D05** | LS-RAG 业务管道 | 只投影谁在运行时被调用 |
| **S11** | Inference≠Adapter、错误/闸/transport、catalog resolve | 默认 **local vLLM base_url** 与模型角色绑定到本拓扑 |
| **S08/S10** | vectorize / retrieve 策略 | embed 调用经 S11 → `qwen-vl-2b` 角色 |
| **S06/S07** | structure/construct | LLM 调用经 S11 → `qwen35-a3b` 角色 |
| **S14** | registry / snapshot / PromptRef | 逻辑 model id 与 binding；**不**调度 Docker |
| **S15** | `/live` `/ready` `/metrics`、retention | ready 可 **引用** 推理探针，不拥有 GPU |
| **S16** | MKB internal token / EndpointClass | **≠** vLLM Bearer key；两套凭证分账 |
| **myaidev** | 容器镜像、recipes、observe_proxy、密钥文件布局 | **ReferenceAnchor**；MKB 不 import 其代码 |

### 0.4 明确禁止

- 把「当前宿主机 `docker ps` / `nvidia-smi` 快照」写成真相层 HARD 不变量；  
- 因 ComfyUI/其他容器瞬时占用而 reopen S11/S08 或阻塞 formal；  
- 要求 MKB 进程内嵌 vLLM 权重加载（v1 **默认** 边车容器 `ai-mkb`）；  
- 第二可写业务库 / 无协调多进程写 `object_root`；  
- 公网 object CRUD；legacy 多 Worker 业务拓扑；  
- 用 vLLM API key 代替 MKB InternalToken（或相反）。

---

## 1. Domain 介绍

### 1.1 价值

在 S01–S16 已钉死契约与状态之后，D06 冻结 **运行时接线**：

- MKB **在哪里跑**（应用平面）；  
- 模型 **从哪里来**（`ai-mkb` 推理平面）；  
- 默认 **怎么连**（668/669、模型角色）；  
- **资源争用** 如何归业主窗口，而非规格失败。

### 1.2 位置

```text
D03 layout · D04 schema · D05 LS-RAG handbook
        │
        ▼
D06 runtime topology  ★  应用平面 + ai-mkb 推理平面
        │
        ├── S11 local_vllm adapter defaults
        ├── S08/S10 embed path
        ├── S06/S07 generate path
        └── S15 ready aggregation (logical)
```

### 1.3 Scope fence

**负责：** 双平面进程图；`ai-mkb` 端口与模型角色；MKB 数据挂载；就绪消费规则；资源主权非 blocker 纪律；与 myaidev 的锚点引用。

**不负责：** Docker 镜像构建细节、vLLM 版本 pin 的 pip 命令、ComfyUI 生命周期实现、商业 GPU benchmark、K8s 多副本生产拓扑（defer）。

### 1.4 完成定义（冻结时）

1. §2 经 owner 冻结并分配 `T-O-*`；  
2. S11 默认 base_url / 模型角色与本文一致或显式映射表；  
3. 索引 `17` 收敛到 D06；  
4. HARD 验收 **不** 依赖瞬时宿主机 GPU 空闲。

---

## 2. 真相层（候选）

### 2.1 资源主权与非 blocker

| ID | 候选真相 | 标签 |
|---|---|---|
| `D06-T001` | **宿主机资源时间片由业主调配**。规格描述的是 **MKB 运行窗口内应满足的契约**，不是开发机 24×7 常驻清单。 | 【Owner】 |
| `D06-T002` | 观测到宿主机资源/容器与本文不符 **不得** 构成 MKB 设计、实现或验收的 **blocker**。仅可记为 **ops gap**（运维待办）。 | 【Owner】 |
| `D06-T003` | **当 MKB 运行时**，业主保证：`ai-mkb` 已启动且本文件要求的 embed + LLM 推理角色可用；冲突负载（至少包括 **ComfyUI**）已按业主策略停止或迁出。 | 【Owner】 |
| `D06-T004` | CI / architecture tests **禁止** 将「本机 GPU free / comfyui exited / 668 listening」作为默认 HARD。允许 **可选** integration profile `mkb_live_inference=1` 在业主保证窗口内跑。 | 【Owner】 |

### 2.2 应用平面（MKB）

| ID | 候选真相 | 标签 |
|---|---|---|
| `D06-T010` | MKB v1 = **单一发布单元** leaf-worker（OD-06 / D03-T002 / S01-T001）。 | 【已继承】 |
| `D06-T011` | 业务写权威默认 **单 OS 进程** 承载 API + runtime engine + 后台协程（outbox/claim/GC/retention 钩子）；**禁止** 无协调多进程写同一 `mkb_primary` 或同一 `object_root`。 | 【已继承】 |
| `D06-T012` | 数据挂载逻辑名服从 D03：`data/database/`（`mkb_primary`）、`data/objects/`（`object_root`）、`data/prompts/`、`data/config/`、可选 `data/logs/`。 | 【已继承】 |
| `D06-T013` | Business / Operator / Repair / Live / Ready / Metrics 面的 **MKB EndpointClass** 服从 S16；路径导出服从 S15。与 vLLM 端口 **分平面**。 | 【已继承】 |
| `D06-T014` | `retrieval.search` 同步在 MKB 应用进程内执行；**不**创建 Task；embed/rerank 出站到 Plane B。 | 【已继承】 S10 |

### 2.3 推理平面 — 容器 `ai-mkb`

| ID | 候选真相 | 标签 |
|---|---|---|
| `D06-T020` | v1 **默认推理平面** = Docker 容器 / compose profile，**逻辑名 `ai-mkb`**（可实现为 `container_name: ai-mkb` 或等价专用 profile）。它建立在 **myaidev / ai-dev 工作台族** 之上，但是 **MKB 专用**，不与日常 `ai-neo` 实验 profile 混用同一运行契约。 | 【Owner】 |
| `D06-T021` | `ai-mkb` **内置 / 持有 vLLM**，对外提供 **OpenAI-compatible** HTTP inference（至少 chat/completions 与 embeddings 能力面按模型角色暴露）。 | 【Owner】 |
| `D06-T022` | 宿主机端口约定：  
  · **`668`** — vLLM 主 API（或直连 upstream）；  
  · **`669`** — observe proxy（若启用）→ 转发至容器内 vLLM，并可注入观测字段。  
  MKB 配置允许指向二者之一；**默认推荐应用走 `669`（有 proxy 时）或 `668`（直连）**，由部署 env 选择，**不得**写死单一实现细节为唯一合法。 | 【Owner】 |
| `D06-T023` | 推理鉴权：vLLM / proxy 使用 **独立 Bearer**（myaidev 式 secret 文件注入，如 `docs/secrets/key1` → `/run/secrets/vllm_api_key`）。**≠** MKB InternalToken。S11 adapter 持有 inference credential ref（S16 secret slot），禁止把 vLLM key 写入业务表或 git。 | 【Owner】+【已继承】S16 精神 |
| `D06-T024` | `ai-mkb` **不**承载 MKB 业务库写权威、不持有 Intake/Task SSOT、不实现 PublicationProof。 | 【Owner】 |
| `D06-T025` | GPU / 统一内存调度、镜像 tag、是否挂 `/workspace/models` USB 路径等 **实现细节** 由业主在 myaidev 侧维护；D06 只冻结 **逻辑角色与端口契约**。 | 【Owner】 |

### 2.4 模型角色闭集（MKB 消费）

| ID | 候选真相 | 标签 |
|---|---|---|
| `D06-T030` | **Embedding 角色（Layer A 默认）** 逻辑名 **`qwen-vl-2b`**（业主命名；具体 HF id / 本地目录由 S14 catalog + 部署绑定，可映射如 Qwen2-VL-2B 或业主登记的等价 NVFP4/本地路径）。S08/S10 的 `embed` **必须** 经 S11 打到该角色，**禁止** silent 换空间。 | 【Owner】 |
| `D06-T031` | **主力 LLM 角色** 逻辑名 **`qwen35-a3b`**（对应 myaidev 族 `Qwen3.6-35B-A3B` / `VLLM_PROFILE=qwen35-a3b` 一类；精确权重路径部署绑定）。S06/S07（及任何 v1 `structured_generate` / `text_generate`）默认绑定该角色。 | 【Owner】 |
| `D06-T032` | `qwen35-a3b` **必须** 配置为支持 **多路（并发）inference**：vLLM 侧允许多 in-flight / multi-seq 请求；MKB S11 并发闸与之对齐，**禁止** 默认串行化成单 flight 作为唯一合法（数值闸仍可配置）。 | 【Owner】 |
| `D06-T033` | `qwen35-a3b` **必须** 启用 **MTP speculative decoding**（或业主验证等价加速）；失败时的降级策略归 S11（可观测、禁 silent 换 base model）。 | 【Owner】 |
| `D06-T034` | `qwen35-a3b` **必须** 提供 **充足 KV cache** 预算，以支撑 MKB 生产上下文（structure/construct/clean 的长输入与多并发）。具体 GiB / `max-model-len` 由部署 recipe 标定；**规格要求「按生产并发标定且 fail-loud 不足」**，不在 D06 钉死单一数字。 | 【Owner】 |
| `D06-T035` | v1 **不要求** 在同一 `ai-mkb` 内再挂 122B 作默认；122B / DiffusionGemma / gpt-oss 等为 myaidev **实验 profile**，非 MKB 默认拓扑。 | 【Owner】 |
| `D06-T036` | Rerank 能力：若 v1 使用独立 rerank 模型，须在 S14/S11 登记；**未登记前** S10 可按已冻策略在 rerank 失败时诚实回退 ANN（S10-T）。 | 【已继承】S10 |

### 2.5 运行窗口与 ComfyUI

| ID | 候选真相 | 标签 |
|---|---|---|
| `D06-T040` | **MKB 运行窗口** 内，业主 **停止 ComfyUI**（及同类高占用 GPU 工作负载），以释放统一内存/计算给 `ai-mkb` + MKB。 | 【Owner】 |
| `D06-T041` | ComfyUI 与 `ai-mkb` **默认互斥**（同机同 GPU 时间片）。并行仅当业主显式运维例外，**不**写入 v1 支持矩阵。 | 【Owner】 |
| `D06-T042` | 开发期可在无 MKB 窗口时运行 ComfyUI；**不**触发 D06 违规。 | 【Owner】 |

### 2.6 网络与调用边

| ID | 候选真相 | 标签 |
|---|---|---|
| `D06-T050` | 上游 orchestrator → **MKB Business HTTP**（S01；InternalToken；polling）。 | 【已继承】 |
| `D06-T051` | MKB → **`ai-mkb`**：`http://127.0.0.1:668` 或 `http://127.0.0.1:669`（或 Docker 网络内可达的 `http://ai-mkb:668` 等）。逻辑配置键建议：`inference.vllm.base_url`（S11）。 | 【Owner】 |
| `D06-T052` | S11 adapter **必须** 支持 Bearer 注入；超时/退避/闸服从 S11；**禁止** 429/transport 驱动 silent 换 `qwen35-a3b`→其他逻辑模型（G-10）。 | 【已继承】 |
| `D06-T053` | 可选公网入口（如历史 `vllm.saobao.com`）仅服务 **推理平面** 调试；**不是** MKB Contract 的一部分；MKB 生产调用默认 **本机/内网 loopback 或 bridge**。 | 【Owner】 |
| `D06-T054` | MKB `/live` **不得** 依赖 vLLM；MKB `/ready` **可以** 聚合「配置要求的 inference probe」（S11/S15）；probe 失败 → not ready，**不**改写业务状态机。 | 【已继承】+【Owner】 |

### 2.7 凭证分账

| ID | 候选真相 | 标签 |
|---|---|---|
| `D06-T060` | **MKB InternalToken**：业务 API；S16 生命周期。 | 【已继承】 |
| `D06-T061` | **vLLM API key**：仅 `ai-mkb` / proxy；文件或 secret slot 注入 S11。 | 【Owner】 |
| `D06-T062` | 两套 token **禁止** 混用或互相推导授权。 | 【Owner】 |

---

## 3. 总体方案陈述

1. **双平面**：MKB 应用平面 + `ai-mkb` 推理平面。  
2. **推理容器专用**：`ai-mkb` 提供 vLLM；端口 **668/669**。  
3. **模型角色**：embed=`qwen-vl-2b`；LLM=`qwen35-a3b`（多路 + MTP + 充足 KV）。  
4. **运行窗口**：启 MKB 前业主停 ComfyUI；资源主权在业主。  
5. **非 blocker**：瞬时宿主机不符 ≠ 规格失败。  
6. **S11 only** 出站推理；G-10 禁 silent swap。  
7. **数据平面** 仍单写权威 + D03 路径。  
8. **supersede 原 `17`** 的运行拓扑职责。

---

## 4. 具体执行方案清单

### 4.1 `D06-E01` — 规范运行时图（MKB 窗口）

**真相**：`D06-T001..003`、`T010..014`、`T020..025`、`T030..034`、`T040..041`、`T050..054`

```text
┌─────────────────────────────────────────────────────────────────┐
│ Host (Owner-scheduled MKB window)                               │
│                                                                 │
│  [ComfyUI] ── STOPPED for this window ──                        │
│                                                                 │
│  ┌──────────────────────────┐    HTTP Bearer     ┌───────────┐ │
│  │ MKB leaf-worker          │ ─────────────────► │  ai-mkb   │ │
│  │ (Plane A, write auth)    │  :668 and/or :669  │ (Plane B) │ │
│  │  api+runtime+bg          │ ◄── OpenAI API ──  │  vLLM     │ │
│  │  S11 inference facade    │                    │           │ │
│  └───────────┬──────────────┘                    │ roles:    │ │
│              │                                   │  embed    │ │
│              ▼                                   │  qwen-vl-2b│ │
│     data/database · objects · prompts            │  llm      │ │
│                                                  │  qwen35-a3b│ │
│  Upstream ──InternalToken──► MKB Business        │  +MTP+KV  │ │
│  (polling)                                       └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
```

**小结**：规格验收此图的 **边与角色**；不验收「此刻 docker 是否已创建」。

---

### 4.2 `D06-E02` — `ai-mkb` 端口与入口选择

| 入口 | 用途 | MKB 默认 |
|---|---|---|
| `host:668` | vLLM 直连 | 可 |
| `host:669` | observe proxy → vLLM | **推荐**（若 proxy 启用；利于排障，非强制） |
| Docker DNS `ai-mkb:668` | 同 bridge 网络 | 可 |

**配置（逻辑键，S11/S14）**：

```text
inference.vllm.base_url = http://127.0.0.1:669   # 或 :668
inference.vllm.api_key_secret_ref = secret://vllm_api_key
inference.roles.embed = qwen-vl-2b
inference.roles.llm   = qwen35-a3b
```

**小结**：668/669 **都合法**；部署二选一或主备，写入 ConfigSnapshot。

---

### 4.3 `D06-E03` — 模型角色 → S11 capability

| MKB capability（S11） | 拓扑角色 | 备注 |
|---|---|---|
| `embed` | `qwen-vl-2b` | Layer A；S08/S10 |
| `structured_generate` / `text_generate` | `qwen35-a3b` | S05–S07；MTP+多路 |
| `rerank` | 登记或诚实跳过 | 服从 S10 |

**执行台账**：

1. S14 catalog 登记逻辑 id → 部署 binding（served-model-name / 路径）；  
2. S11 resolve 失败 → fail-loud / ready=false（按配置）；  
3. **禁止** 用 122B 实验权重冒充 `qwen35-a3b` 而不改 binding。

---

### 4.4 `D06-E04` — qwen35-a3b 服务期望（对 `ai-mkb` 的契约）

业主在 `ai-mkb` 内保证（实现可落 myaidev recipe 变体）：

| 期望 | 说明 |
|---|---|
| 多路 inference | 支持并发请求；与 S11 global/per-capability 闸协同 |
| MTP | speculative decoding 开启；指标可观测（proxy 可选） |
| 充足 KV | 按生产 max concurrency × context 标定；不足 fail-loud |
| OpenAI 兼容 | 至少 chat/completions（及工具面若 S06 需要） |
| 鉴权 | Bearer；未授权 401 |

D06 **不**复制 `start-vllm-qwen35-a3b` 的每一 CLI 旗标；那些留在 myaidev ops。

---

### 4.5 `D06-E05` — qwen-vl-2b embedding 期望

| 期望 | 说明 |
|---|---|
| 稳定向量维 | 与 S08 Layer A / namespace 登记一致 |
| 经 S11 `embed` | 禁业务直连 |
| 可与 LLM 同容器或同 vLLM 多模型 | **部署选择**；须保证 embed 延迟与可用性满足 ready 策略 |
| 权重落盘 | 业主保证运行窗口可用；路径不进 MKB 业务契约 |

若 embed 与 LLM **争用** 导致超时：属运维/闸参数，**不**自动改 D05 管道。

---

### 4.6 `D06-E06` — 应用平面挂载与后台（继承压缩）

与 v0.1 相同纪律，摘要：

- 单写 `mkb_primary` + `object_root` identity；  
- outbox/claim/GC/retention/backup 钩子同发布单元；  
- `/live` 无依赖；`/ready` 聚合 S12/S13/S16/`sec_token_loaded`/可选 inference probe。

---

### 4.7 `D06-E07` — 业主运行窗口 checklist（ops，非 CI HARD）

> 下列为 **运维清单**，**不是** architecture test 默认门禁。

1. 停止 `comfyui`（及冲突 GPU 任务）；  
2. 启动 `ai-mkb`（vLLM + 角色模型已 load）；  
3. 验证 `curl :668/health` 或 `:669` 等价；  
4. 验证 embed + chat 各一发（带 vLLM Bearer）；  
5. 启动 / 恢复 MKB 应用进程；  
6. 确认 MKB `/ready` 与业务探测。

窗口结束：可停 MKB 与/或 `ai-mkb`，恢复 ComfyUI——**规格无异议**。

---

### 4.8 `D06-E08` — 与 D05 管道的运行时投影

```text
S05 clean (promptA)  --llm-->  ai-mkb:qwen35-a3b
S06 structurize (B)  --llm-->  ai-mkb:qwen35-a3b
S07 construct (C)    --llm-->  ai-mkb:qwen35-a3b
S08 vectorize        --embed-> ai-mkb:qwen-vl-2b
S10 retrieve         --embed-> ai-mkb:qwen-vl-2b
                     --rerank?-> (if bound)
```

业务序 **不** 因 Docker 改变。

---

## 5. 事实反例 + 风险

### 5.1 反例

| 反例 | 订正 |
|---|---|
| 因 ComfyUI 在跑宣布 S11 无效 | ops gap；T002 |
| 把 vLLM key 当 MKB token | T060–062 |
| services 直连 668 | S11 only |
| 默认绑定 122B 却宣称 qwen35-a3b | 改 binding 或改角色名 |
| CI 无 GPU 即 fail build | T004 |
| 多进程抢写同一 DB 文件 | T011 |
| 规格要求 24×7 与 ComfyUI 共存满血 | T040–041 互斥窗口 |

### 5.2 风险

| 风险 | 缓解 |
|---|---|
| embed+LLM 同卡 OOM | 业主窗口资源保证；闸与 KV 标定 |
| 669 proxy 改 response schema | S11 客户端宽松解析；可切 668 |
| 逻辑名与 HF id 漂移 | S14 binding + content/hash 类登记 |
| 开发机瞬时不符导致评审恐慌 | **T001–T004 非 blocker 纪律** |

---

## 6. 测试与验收台账

| ID | 项 | 默认 CI | 业主 live 窗口 |
|---|---|---|---|
| `D06-A01` | 配置可表达 `base_url` ∈ {668,669,自定义} | HARD | — |
| `D06-A02` | 角色键 `qwen-vl-2b` / `qwen35-a3b` 存在于 catalog 合同 | HARD | — |
| `D06-A03` | S11 无 token 混用（MKB vs vLLM）单元 | HARD | — |
| `D06-A04` | services 层无 vLLM HTTP 直依赖 | HARD | — |
| `D06-A05` | `/live` 不依赖 inference mock down | HARD | — |
| `D06-A06` | ready 在 inference probe 配置开启且失败时 not ready | HARD（mock） | 可选 live |
| `D06-A07` | 瞬时无 668 监听 **不** 失败默认 test suite | HARD（负例） | — |
| `D06-A08` | live：embed + generate 往返 | **OFF 默认** | ON 当 `mkb_live_inference=1` |
| `D06-A09` | 单写 DB/object_root 纪律 | HARD | — |
| `D06-A10` | 文档声明 ComfyUI 互斥窗口 | doc review | ops |

---

## 7. Reference-anchor

### 7.1 内部

| 锚 | 用途 |
|---|---|
| S11 local vLLM / G-10 | adapter 与禁 swap |
| S08/S10 Layer A | embed 角色 |
| S06/S07 generate | LLM 角色 |
| S12/S13 写权威 | 应用平面 |
| S15/S16 探针与 token | 分平面凭证 |
| D03 路径 | 挂载名 |

### 7.2 兄弟单位 myaidev（ReferenceAnchor only）

| 锚 | 用途 |
|---|---|
| `myaidev/docker-compose.yml` 端口 668/669 | 端口族来源 |
| `scripts/start-vllm-qwen35-a3b.sh` / `start-ai-neo-qwen35-a3b.sh` | LLM profile 形态 |
| `docs/recipes/qwen-35B-A3B.md` | MTP/多路/KV 运维经验 |
| `docs/vllm-observe.md` | 669 proxy 语义 |
| `docs/secrets/key1` 挂载模式 | vLLM 鉴权注入（**不**复制密钥进 MKB 仓） |

### 7.3 不继承

- ComfyUI 常驻与 MKB 同时满载；  
- 以 122B 为 MKB 默认；  
- model-disguise 作为 MKB 默认真相（允许运维层使用，但 catalog 须诚实 `actual_backend` 或显式 binding）。

---

## 8. Domain verdict

### 8.1 评价

| 项 | 状态 |
|---|---|
| v0.2 相对 v0.1 | **重写对齐 Owner：`ai-mkb` + 668/669 + qwen-vl-2b / qwen35-a3b + ComfyUI 互斥窗口 + 资源非 blocker** |
| 是否替代 D03/D04/D05 | **否**；仅补运行合成 |
| 与 S11 | 默认 base_url/角色须在 S11 校准回填（冻结时） |
| blocker 纪律 | **T001–T004 为业主强制** |

### 8.2 冻结前可选确认（非阻塞理解）

1. embed 权重最终 HF/本地精确 id 字符串；  
2. MKB 默认 `base_url` 选 668 还是 669；  
3. embed 与 LLM 同 vLLM 进程还是双引擎同容器。

以上均可部署期决定，**不**阻塞 D06 作为拓扑契约草稿。

### 8.3 下游

- S11：默认 local endpoint 与角色名；  
- S14：catalog 逻辑 id；  
- S15：可选 inference 组件进 `/ready`；  
- 索引：`17` → D06。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| `D06-v0.1-draft` | 2026-08-12 | draft | 首稿；泛化单机 vLLM:8000 草案 |
| `D06-v0.2-draft` | 2026-08-12 | draft / owner-calibrated | **Owner 改写**：`ai-mkb` 容器；668/669；`qwen-vl-2b` embed + `qwen35-a3b` LLM（多路/MTP/充足 KV）；MKB 窗口停 ComfyUI；**宿主机资源业主调配，瞬时不符非 blocker** |

---

## Appendix A — 资源非 blocker（给评审的固定话术）

> 「本机现在 ComfyUI 占着 GPU / 668 没起来 / swap 很高」→ **运维状态**，不是 D06/S11 缺陷。  
> 「MKB 能不能设计 embed 走 qwen-vl-2b」→ **能**；运行窗口由业主拉起 `ai-mkb` 并停 ComfyUI。  
> 「CI 没有 GB10」→ **默认 mock**；live 推理是可选 profile。

---

## Appendix B — 建议索引回填（accepted 时）

1. 登记 `D06` accepted；`17` ≡ D06 或 pending 删除。  
2. 完成定义中「17 accepted」改为「D06 accepted」。  
3. Glossary：`AiMkbInferencePlane`、`InferenceRoleEmbed`、`InferenceRoleLlm`、`OwnerResourceWindow`。  
4. S11 header 增加 D06-calibrated：默认 `ai-mkb` @ 668/669；角色 `qwen-vl-2b` / `qwen35-a3b`。
