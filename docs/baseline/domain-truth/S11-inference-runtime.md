# S11 — Inference Runtime & Adapters

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D8 模型能力 / S11 Inference Runtime & Adapters`
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S11 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S11-v1.1`（v1.0 宪法 + **执行台账全面升格**；QNA 细节并入本文）
>
> **上游权威输入**：`D01–D04`、`S01–S07`、`S12–S13`；`qna-truth/S11.md v1.0`（**证据层 / 中间态 only**，非执行 SSOT）
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.1
>
> **下游消费者**：`S06–S10`、`S14–S16`、`17`、`18`、实现与 architecture tests

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S11.md` 仅保留 progressive 形成过程，**不得**被引用为第二执行真相；冲突时 **以本文为准**。禁止「细节在 QNA、Spec 只写原则」。

> **Owner 约束摘要**：禁 Workers AI/Gateway/DO 必选；Inference≠Adapter；v1 全本地 vLLM 默认；Gemini 理论可选；embedding 空间隔离 + 业务 filter；catalog 三表；transport 退避；并发闸；无 WAL 幂等 vectorize。

> **跨文档**：不拥有状态机/ANN/prompt 正文。调用成功≠业务成功。物理表 DDL 以 D04 为准；本文钉死 **写语义与执行步骤**。

> **D05校准声明（T-O-207/208）**：S11 **不**拥有 promptA/B/C 产品语义（正文 D03/S14；绑定 S05/S06/S07）。transport 退避 **不计入** Process `retry_count`；叶失败上报与 max_retries **归 S03**。vectorize 编排与 ConstructToVectorizeGate **归 S07/S08**；本文仅 embed 门面与幂等写路径。
>
> **S14-S16 战役校准（2026-08-12）**：catalog/binding **bootstrap 写权威 = S14 RegistryBootstrap**；**runtime resolve = S11-E03 唯一**（见 S11-E03 所有权矩阵与 `S14-T018`）；G-10 closed for v1 transport 与 S14-T005/S16 SupplyFence 一致；密钥/token/egress **不**归 S11（S16）；metric export 目录 **归 S15**。

> **S08校准声明（2026-08-12）**：`S08-v1.0` 拥有 `lsrag.vectorize` 编排、required-set 成败、records upsert 业务证明与 Layer B **抄写**；S11 继续只提供 `embed` + transport/闸 + Layer A 校验。E09 成功路径中的 outbox claim/`vectorize_*` 编排 **以 S08 为准**；S11-E09 描述的是 **可与 S08 对齐的幂等写辅助合同**，**不**另立第二 vectorize 编排真相。`vectorize_structure` 为 D04 kind 保留名；**v1 禁止消费**（S08-T003）。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S11 规定 leaf-worker 内 **如何安全、可审计、可背压地调用模型**，并把结果以 typed 形状交还 domain——使 S06/S07/S08/S10 不嵌入供应商 SDK，不把限流/并发/半成品向量写成业务成功。

### 1.2 拓扑

```text
services (S05–S10)
  │ 仅 import runtime.inference
  ▼
src/runtime/inference/     # 门面：binding、闸、transport policy、写 invocation
  │
  ▼
src/llm_adapters/          # LocalVllm* 默认；RemoteGemini* 可选骨架
  │
  ▼
D04: catalog / bindings / invocations / (S08) vector_records
```

### 1.3 Scope fence

**负责**：Inference 门面与能力合同；Adapter 边界；transport/闸/错误码；**invocation 写入语义**；catalog/binding 的 **运行时解析（resolve）与消费**（不拥有 catalog/binding 行 bootstrap 写权威——见 S14 所有权矩阵）；Layer A 执行规则；与 Layer B 的衔接义务；`inference_binding` readiness 探针语义（transport/local 可探 + required capability enabled）。

**不负责**：Process 八态与 max-retries 账本（S03）；ANN/serving（S09）；vectorize 业务编排主责（S08 消费本文）；prompt 正文（D03/S14）；DDL 形状（D04）；密钥（S16）。

### 1.4 完成定义

1. §2 Truth 与 §4 E 包可映射到代码与测试；  
2. architecture：services 禁 import llm_adapters；  
3. §6 HARD 矩阵全部有对应 E 包；  
4. 实现 **无需** 打开 QNA 即可编码。

---

## 2. 真相层

### 2.1 全局 T-O（摘要台账 · 全文权威仍为已冻 T-O 原文）

| ID | 一句话 |
|---|---|
| T-O-180..188 | 范围、禁 CF、Ports、双 adapter 族、能力、SSOT fence、prompt、D04 缺口关闭路径、非 Workers 模型方向 |
| T-O-189..193 | Inference≠Adapter；分能力；**v1 全本地**；空间隔离；三表 |
| T-O-195..198 | 本地模型钉选；路径；Layer A fail-closed；**Layer B 业务 filter** |
| T-O-199..201 | transport 退避；并发闸；无 WAL 幂等重放禁丢意图 |

### 2.2 域内 S11-T（执行向）

| ID | 内容 |
|---|---|
| S11-T001 | 业务只调 `runtime.inference`；禁 services→llm_adapters |
| S11-T002 | 能力闭集：embed / rerank / structured_generate / text_generate |
| S11-T003 | 结果必含 adapter_kind、model_key、model_version、usage?、latency_ms、request_digest |
| S11-T004 | structured 出口 = contracts 校验后的 typed 对象 |
| S11-T005 | v1 默认 adapter_kind=`local_vllm` 覆盖全部能力 |
| S11-T006 | 默认 model：embed `qwen3-vl-embedding@2b`；rerank `qwen3-vl-reranker@2b`；generate catalog instruct |
| S11-T007 | 路径：runtime/inference、llm_adapters、contracts/inference |
| S11-T008 | Layer A 键一致 fail-closed |
| S11-T009 | Layer B：team + intake + facets |
| S11-T010 | TransportRetryable 有界退避；不计 Process retry_count |
| S11-T011 | 闸满 → INFERENCE_BACKPRESSURE |
| S11-T012 | vectorize：outbox+幂等 upsert；可重 embed；禁丢意图 |
| S11-T013 | 最终调用写 mkb_inference_invocations |
| S11-T014 | readiness：local binding 可探测 |
| S11-T015 | invocation 禁 secret/prompt 正文/向量全文 |

---

## 3. 总体方案陈述

1. **双层架构**：runtime Inference 门面 + adapters 对接。  
2. **分能力合同**：四能力各自 typed I/O。  
3. **v1 全本地**：Gemini 可选骨架。  
4. **binding 驱动**：catalog + adapter_bindings 解析，禁硬编码散落。  
5. **双层 filter**：A 空间 / B 业务。  
6. **韧性三件套**：transport 退避、并发闸、outbox 幂等。  
7. **审计**：invocation 账非成功定义。  
8. **QNA 零依赖**：执行细节全部在本文 §4。

---

## 4. 具体执行方案清单

### 4.1 `S11-E01` — 目录、依赖与 architecture 围栏

**真相**：S11-T001/T007；T-O-189/196

**执行台账**：

| 路径 | 职责 |
|---|---|
| `src/runtime/inference/` | Facade、policies、gate、binding resolver、invocation writer（经 S12 ports） |
| `src/llm_adapters/local_vllm/` | vLLM HTTP/SDK |
| `src/llm_adapters/remote_gemini/` | 可选骨架；默认 disabled |
| `src/contracts/inference/` | Embed/Rerank/Structured/Text Request·Result·Usage·Error |

| 规则 | 验收 |
|---|---|
| services 禁止 `import ...llm_adapters` | architecture test fail |
| adapters 禁止 import services | 同上 |
| adapters 禁止写 tasks/processes | 同上 |

**小结**：依赖方向可机械测试。

---

### 4.2 `S11-E02` — 分能力 Inference Facade 与字段合同

**真相**：S11-T002..T004；T-O-184/190

**执行台账 — 方法闭集**：

| 方法 | 最小请求字段 | 最小成功结果 |
|---|---|---|
| `embed` | team_uuid?、texts[] 或 multimodal parts、binding 覆盖?、trace/process refs? | vectors[][] 或 vector[]、dimension、公共附属字段 |
| `rerank` | query、documents[]（id+text/ref）、top_n? | ordered {id, score}[]、公共附属 |
| `structured_generate` | prompt_key+hash 或已渲染且校验的系统/用户消息、json_schema_ref、profile | **typed object**（已 contracts.validate） |
| `text_generate` | 同上消息绑定、profile | text、公共附属 |

**公共附属字段（强制）**：`adapter_kind`、`model_key`、`model_version`、`usage{input_tokens?,output_tokens?,total_tokens?}`、`latency_ms`、`request_digest`、`invocation_uuid`。

**禁止返回**：path、API key、未校验 dict、绝对 URL 身份。

**小结**：无万能 `invoke(model, blob)`。

---

### 4.3 `S11-E03` — Catalog / Binding 解析（runtime resolve）与 bootstrap 协作

**真相**：S11-T005/T006/T013/T014；T-O-193/195；D04 §3.8；**写权威交接见 S14-T018 / S14-E05 所有权矩阵**

#### 所有权矩阵（与 S14 双向钉死 · 唯一）

| 职责 | 唯一归属 | 说明 |
|---|---|---|
| `mkb_model_catalog` / `mkb_adapter_bindings` **bootstrap INSERT/幂等 upsert** | **S14 RegistryBootstrap**（code-owned GreenfieldBootstrap / migration；默认 capability 清单 **协作** S11-E03 必须行集合） | S11 **不**平行 INSERT 同表作 SSOT 写面 |
| 默认行内容（embed/rerank/generate 钉选） | S11 声明必须行；S14 bootstrap **消费**该清单写入 | 冲突码 `BOOTSTRAP_FAIL` / digest mismatch → readiness 归 S14 `registry_bootstrap` |
| **运行时 resolve 算法** | **S11-E03 唯一** | S14 仅复述产品语义；**禁止**在 S14 另立完整解析序 |
| status/enabled 运维变更 | S14 bootstrap/ops 路径（禁公网 CUD）；变更仅 future resolve | S11 运行时只读 binding 行 |
| `mkb_inference_invocations` 写 | **S11** | 与 catalog 写分账 |
| readiness：`inference_binding` | **S11** | transport/local 可探 + required capability 有 enabled binding |
| readiness：`registry_bootstrap` | **S14** | prompt 指针 + catalog 行存在 + digest 一致；**不**双主 |

#### Bootstrap 必须行集合（内容权威 S11 · 写路径 S14）

| 表 | 必须存在的默认行（逻辑） |
|---|---|
| `mkb_model_catalog` | embed 2b、rerank 2b、local-json-generator@v1；各含 definition_digest |
| `mkb_adapter_bindings` | 每 capability 至少一条 `local_vllm` enabled priority 最高；remote 可 enabled=0 |

#### 解析顺序（**唯一权威** · 仅用于 **无 L4 冻结身份的新 resolve / bootstrap 校验**）

1. 读 enabled bindings：capability → 按 priority；  
2. team 覆盖（若有）优先于全局；  
3. 校验 model_key/version ∈ catalog 且 status=active；  
4. 锁定 binding 快照进 request_digest 材料。

**与 L4 冻结（S14-T007/T015）**：S11 **主业务路径** 输入必须携带已冻结 `model_key`/`model_version`/`adapter_kind`（来自 L4 / ProcessCommand / Execution binding digests）。S11 resolver **禁止**在 transport 失败后重 resolve 换 binding（G-10）。仅当调用方未携带冻结身份（bootstrap/diagnostic/新 resolve）时走本序。

**冲突**：同 version 异 digest → S14 `registry_bootstrap` readiness=false；S11 `inference_binding` 另测 transport 可探。

**小结**：写权威 S14；解析权威 S11；运行时不解析「最新 HF 字符串」。

---

### 4.4 `S11-E04` — 单次调用主路径（含闸与 transport）

**真相**：T-O-199/200；S11-T010/T011

**执行台账 — 逐步**：

| 步 | 动作 | 失败 |
|---|---|---|
| 1 | 解析 binding | CONFIG / ADAPTER_DISABLED |
| 2 | Layer A 预检（embed 时 dim/model） | SPACE_VIOLATION |
| 3 | ConcurrencyGate.try_acquire | **立即** BACKPRESSURE（不进 transport 环） |
| 4 | transport loop attempt=1..N | 见 E05 |
| 5 | structured → contracts.validate | VALIDATION_*；release gate |
| 6 | 写 `mkb_inference_invocations` | 仍须 best-effort 审计；业务失败不因 audit 改成功语义（若同 TX 业务写则按域 UoW） |
| 7 | Gate.release（finally） | — |
| 8 | 返回 domain | domain 负责 CAS/outbox |

**小结**：闸在模型调用前；transport 在闸内。

---

### 4.5 `S11-E05` — Transport 错误分类与有界退避

**真相**：T-O-199

**执行台账 — 分类**：

| 类 | 条件（逻辑） | 行为 |
|---|---|---|
| TransportRetryable | HTTP 429/503；超时；连接失败；rate_limited/overloaded/capacity 语义 | 退避后同 binding 重试 |
| ValidationNonRetryable | 4xx 校验、contracts、空输入策略、预算超限 | 立即失败 |
| ConfigNonRetryable | model 未注册、binding disabled、adapter 未启用 | 立即失败 |
| SpaceViolation | 跨 model/adapter/dim | 立即失败 |
| Backpressure | 闸满 | 见 E04；**不算** transport attempt |

**退避默认（可配置，有界）**：

| 参数 | 默认 |
|---|---|
| max_transport_attempts | 3 |
| initial_delay_ms | 1000 |
| backoff_factor | 2 |
| max_delay_ms | 30000 |
| jitter | 允许 |

**耗尽**：`INFERENCE_TRANSPORT_EXHAUSTED`；建议 Process `retryability=retryable`。  
**禁止**：换 model_key / adapter_kind / dimension 再试。  
**S03 分账**：内环 attempt **不**增加 `processes.retry_count`。

**小结**：对齐 vectorizer embedder 有界 429 退避，去掉 CF 错误码依赖。

---

### 4.6 `S11-E06` — 并发闸与 Backpressure

**真相**：T-O-200

**执行台账**：

| 项 | 规范 |
|---|---|
| 位置 | `runtime/inference` 进程内 |
| 粒度 | global_max_in_flight；可选 per-capability |
| 超额 | `INFERENCE_BACKPRESSURE`，retryable，**零**模型调用 |
| 与 claim | 正交：多 Process claimed 仍受闸约束 |
| 缓解 | outbox `available_at` 延后；或短等（须有上限，不无限吃 lease） |
| 禁止 | 删 outbox/任务疏通；用换模型减压 |
| 可观测 | failed invocation 或 diagnostic 记 BACKPRESSURE |

**小结**：替代 DO 串行/mutex 的容量语义。

---

### 4.7 `S11-E07` — Layer A 空间隔离执行

**真相**：T-O-192/197；S11-T008

**执行台账 — embed 写路径预检/后检**：

| 检查 | 失败码 |
|---|---|
| model ∈ catalog 且 modality 含 embed | CONFIG |
| binding.model 与请求一致 | SPACE_VIOLATION |
| 返回 dimension == namespace.dimension == binding 声明 | SPACE_VIOLATION |
| adapter_kind 写入/校验与 binding 一致 | SPACE_VIOLATION |

**检索/查询 embed**：query 所用 model/version/dim/adapter 必须匹配目标 namespace，否则 typed error 或空结果（实现选一，**禁止** 静默跨空间 ANN）。

**小结**：内部流转围栏，非业务 facet。

---

### 4.8 `S11-E08` — Layer B 业务 filter 义务

**真相**：T-O-198

**执行台账 — 最低业务 filter 集合**（S11 保证 embed 元数据可携带；S08/S10 写入/查询）：

| 维度 | 义务 |
|---|---|
| team_uuid | 始终强制 |
| intake source/item/revision | 按查询面可过滤；写向量时坐标完整 |
| 上游 facet（如 industry-domain + map） | 有 map 则必须物化为可索引 filter 值；检索可按域裁剪 |
| 扩展 facet | versioned 注册后晋升列或规范化结构；禁仅靠不可查 blob 当唯一真相 |

**分账**：S11 不拥有 facet 产品定义；**拒绝** 用换 embedding 模型模拟业务分区。

**小结**：业务 filter ≠ 空间隔离。

---

### 4.9 `S11-E09` — Vectorize 耐久与幂等（无 WAL）

**真相**：T-O-201；S11-T012

**执行台账 — 成功路径**：

```text
1. （S08 编排）claim outbox kind∈{vectorize_construct,...}；v1 **禁**消费 vectorize_structure
2. load embed input via generation/object + ContentFullRecipe 对账（禁止 content_full 常驻向量表）
3. Inference.embed (E04–E07) — **S11 边界**
4. UnitOfWork（S08/S12）:
     upsert mkb_vector_records (幂等键见 D04；Layer B 抄写 S04)
     insert mkb_inference_invocations succeeded
     optional domain_event
5. mark outbox done；**业务成功 = S08 ProcessOutcome full_valid**，非 outbox done
```

**失败矩阵**：

| 失败点 | outbox | 重放 |
|---|---|---|
| embed transport 耗尽 | 未 done | 再试；可 re-embed |
| upsert 失败 | 未 done | 再 embed+upsert 幂等 |
| done 标记失败 | 可能已有向量 | upsert 幂等 + done |
| 崩溃 | pending/in_flight | S12 投递恢复 |

**禁止**：`buffered_vectors` 必选表；静默删 outbox/Process 意图；embed 成功=Process 成功。

**小结**：正确性优先；可重 embed。

---

### 4.10 `S11-E10` — 错误码、配置与 Readiness

**真相**：S11-T014；E05–E06

**错误码表（稳定机读）**：

| code | 条件 | retryability |
|---|---|---|
| `INFERENCE_TRANSPORT_EXHAUSTED` | transport 退避耗尽 | retryable |
| `INFERENCE_BACKPRESSURE` | 闸满 | retryable |
| `INFERENCE_VALIDATION_*` | 输入/contracts | non_retryable |
| `INFERENCE_CONFIG_*` | catalog/binding | non_retryable |
| `ADAPTER_DISABLED` | remote 未启用等 | non_retryable |
| `INFERENCE_SPACE_VIOLATION` | Layer A 不一致 | non_retryable |
| `INFERENCE_INTERNAL_*` | 未分类内部错 | indeterminate/retryable（实现钉默认） |

**配置键（逻辑，落 data/config 或 env，禁秘密进 git）**：

| 键 | 含义 |
|---|---|
| `inference.gate.global_max_in_flight` | 全局并发 |
| `inference.gate.{capability}_max_in_flight` | 分能力 |
| `inference.transport.max_attempts` 等 | 退避 |
| `inference.vllm.base_url` | 本地端点 |
| `inference.default_adapter` | 默认 `local_vllm` |

**Readiness=false 当**：默认 local binding 缺失；catalog digest 漂移；vLLM 探针失败（若配置要求）。  
Remote 未启用 **不**单独导致默认就绪失败。

**小结**：错误与配置可编码、可测。

---

### 4.11 `S11-E11` — 与 S03/S06/S07/S08 交接

| 上游/下游 | 合同 |
|---|---|
| S03 | 只消费 Outcome retryability；内环 attempt 不计 retry_count；lease 须覆盖或 heartbeat |
| S06/S07 | 只调 structured/text_generate；成功后自管 generation CAS |
| S08 | **拥有** vectorize 编排与 records 写证明；只调 embed；Layer A 服从本文；E09 为幂等辅助对齐 |
| S10 | 调 embed(query)+rerank；强制 Layer A/B |
| S14 | 产品 registry + catalog/binding **bootstrap 写权威**；S11 仅 resolve/invocation + 必须行清单协作 |
| S15 | 指标/retention 数值 |

---

## 5. 事实反例、风险与实施切片

### 5.1 反例

| 反例 | 订正 |
|---|---|
| services 直调 vLLM | 只经 runtime.inference |
| 429 换 embedding 模型 | 禁止 |
| DO 删坏任务 | 禁止；S03/outbox |
| content_full 进向量表 | 禁止 |
| QNA 当实现说明书 | 禁止；以本文为准 |

### 5.2 风险

| 风险 | 缓解 |
|---|---|
| 重复 embed 成本 | E09 接受 v1；未来 staging reopen |
| 闸过小饿死 | 配置上调；观测 BACKPRESSURE |
| lease 与长退避 | max_delay 封顶 + heartbeat |

### 5.3 实施切片

1. contracts + facade + gate + transport  
2. LocalVllm embed/rerank/generate  
3. bootstrap catalog/bindings  
4. invocation 写入  
5. vectorize handler 幂等  
6. architecture tests E01  
7. Gemini 骨架 disabled  

---

## 6. 强制验收矩阵

| ID | 场景 | 期望 |
|---|---|---|
| S11-A01 | services→llm_adapters | 架构失败 |
| S11-A02 | structured 未校验成功 | 拒绝 |
| S11-A03 | 默认路径强制 remote | 失败/禁用 |
| S11-A04 | dim 与 namespace 不符 | SPACE_VIOLATION |
| S11-A05 | 429 后换 model | 禁止 |
| S11-A06 | transport 耗尽 | EXHAUSTED；retry_count 未因内环虚增 |
| S11-A07 | 闸满 | BACKPRESSURE；无模型调用 |
| S11-A08 | 多 claimed Process | 仍受闸 |
| S11-A09 | upsert 失败 | outbox 未 done |
| S11-A10 | 幂等重放 | 无双冲突行 |
| S11-A11 | 删 outbox 疏通 | 禁止 |
| S11-A12 | 仅有向量 | 非 Task success |
| S11-A13 | 跨 team | 拒绝 |
| S11-A14 | 无 team filter | 拒绝 |
| S11-A15 | industry-domain 过滤 | 仅匹配 |
| S11-A16 | prompt 进 invocation | 禁止 |
| S11-A17 | Workers 必选 | 不存在 |
| S11-A18 | catalog digest 漂移 | readiness false |
| S11-A19 | 无 QNA 依赖实现 | 审查/文档测试：Spec 自包含 E 包 |

---

## 7. Reference-anchor 台账

| 锚 | 裁决 |
|---|---|
| vectorizer embedder 429 退避 | 升级 E05；删 CF 码依赖 |
| DO mutex/删任务 | 升级 E06；删丢任务 |
| WAL | E09 不建表 |
| structurizer gemini JSON | 升级 structured_generate |
| Qwen3-VL-Embedding/Reranker-2B | 默认候选 E03 |

**QNA**：`qna-truth/S11.md` = 形成过程证据；**非**执行 SSOT。

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO / execution-complete for v1.1`**：S11 作为 **唯一执行真相** 已含 E01–E11 台账；实现不得外挂 QNA。

### 8.2 强制结论

1. domain-truth only；  
2. Inference≠Adapter；全本地默认；  
3. 双层 filter；三表语义；  
4. transport+闸+幂等 vectorize；  
5. 调用≠业务成功。

### 8.3 下游

S08/S09/S10/S03/S14/S15 必须消费本文 E 包，不得另写并行推理运行时真相。

### 8.4 一句话

S11-v1.1 把推理从「原则」升格为 **可编码执行台账**，并独占执行真相层。

---

## 附录 · NS2 窄回填：orchestrator 配额 vs facade 末闸

NS2 收窄 `T-O-200`：三池 running/queued 配额的 SSOT 是 orchestrator 在 `claim_next` 同一写事务里的 admit（`dispatch_admitted=1` 才可领）。`InferenceFacade.max_in_flight` / capability_limits 是末闸，默认对齐 12=2+2+8，不是三池会计。`claimed` 不等于已获 GPU/NI 配额。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 变更 |
|---|---|---|---|
| S11-v1.0 | 2026-08-12 | accepted | 初版 formal（偏宪法） |
| S11-v1.1 | 2026-08-12 | accepted | **执行 SSOT 强制**；QNA 细节并入 E01–E11；禁止执行依赖 QNA |
| S11-v1.1-cal-d05 | 2026-08-12 | accepted / D05-calibrated | 接收 D05-v1.0：不拥有 promptA/B/C；max-retries 外引 S03 |
