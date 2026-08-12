# S11 — Inference Runtime & Adapters

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D8 模型能力 / S11 Inference Runtime & Adapters`
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`
>
> **文档状态**：`accepted`（S11 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S11-v1.0`
>
> **上游权威输入**：`D01-v1.4`、`D02-v1.0`、`D03-v1.0`（`T-O-141..159`）、`D04-v1.1`（`T-O-160..179` + `T-O-192..194` + `T-O-197..198`）、`S01–S07` accepted、`S12–S13` accepted；冻结的 `qna-truth/S11.md v1.0`（Q1–Q9 / `T-O-180..201`；Round 4 waived）
>
> **词汇权威**：`docs/baseline/spec-glossary.md`
>
> **事实证据**：`legacy-family` structurizer/constructor/vectorizer/contexter AI 栈（ReferenceAnchor）；2026-08 Qwen3-VL-Embedding/Reranker、Gemini Embedding、Ranking API 检索（非 Workers）
>
> **下游消费者**：`S06–S10`、`S08` vectorize、`S14` registry 产品面、`S15` 指标、`S16` 密钥、`17` topology、`18` 验收

> **Owner-originated 约束（2026-08-11 / Round 1–3）**：  
> 1. **脱离 Workers AI / AI Gateway / DO 内嵌推理** 作为 v1 必选路径；  
> 2. **Inference ≠ Adapter**：Inference 属 **runtime**（分能力抽象）；Adapter 属 **对接层**（`src/llm_adapters/`）；  
> 3. **v1 默认全本地**（Local vLLM）；Gemini 仅 **理论/可选** 通道；  
> 4. **不同 embedding 模型向量严禁混用**；空间隔离 + **业务 filter 层**（team / intake / 上游 facet）；  
> 5. **catalog 独立三表**（D04-v1.1）；  
> 6. **transport 有界退避、推理并发闸、无 WAL 幂等重放**。

> **跨文档审计声明**：S11 **不**拥有 Task/Execution/Process/Intake/Generation 状态机合法边；**不**拥有 ANN/serving（S09）；**不**拥有 prompt 正文 SSOT（D03/S14）。推理调用成功 **≠** 业务成功。冲突时：状态机以 S02–S07 为准；物理表以 D04 为准；typed 消息以 contracts 为准。

> **Legacy 边界（T-O-42 / T-O-181）**：不继承 `env.AI`、AI Gateway 必选、DO 队列/WAL 拓扑、`smind_vec_process`、SMCP callback=模型成功、silent prompt fallback。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S11 回答：在单体 leaf-worker 内，如何用 **分能力的 Inference 运行时** + **可替换 Adapter** 完成 embed / rerank / structured_generate / text_generate，并与 Process、outbox、向量表、双层 filter 对账——而不把供应商 SDK、Workers 拓扑或模型字符串泄漏进业务状态机。

S11 解决十二个核心问题：

1. Inference 与 Adapter 如何分层；  
2. 业务如何只依赖 Inference 门面；  
3. v1 能力闭集与 typed I/O；  
4. 本地默认 vs Gemini 理论通道；  
5. 本地模型钉选与 catalog 绑定；  
6. 代码落点（runtime/inference vs llm_adapters）；  
7. embedding 空间隔离（Layer A）；  
8. 业务检索 filter（Layer B）；  
9. transport 429/限流合同；  
10. 本地并发闸与背压；  
11. vectorize 两阶段耐久与禁丢意图；  
12. 与 D04 三表 / S03 retry 的分账。

### 1.2 在整体拓扑中的位置

```text
S03/S06/S07/S08/S10 services
  │ only runtime.inference (capability API)
  ▼
src/runtime/inference/     [S11 门面：binding 解析、闸、transport policy、写 invocation]
  │
  ▼
src/llm_adapters/          [S11 对接：LocalVllm* 默认；RemoteGemini* 可选骨架]
  │
  ├── local vLLM (ai-dev)  embed / rerank / generate
  └── (optional) Gemini / Ranking API
  │
  ▼
D04: mkb_model_catalog / mkb_adapter_bindings / mkb_inference_invocations
     mkb_vector_records (+ Layer A/B filters) via S08/S12 UoW
```

### 1.3 Scope fence

**S11 负责：**

- Inference 门面与分能力合同；  
- Adapter 实现边界与默认路由；  
- transport 退避 / 背压闸 / 错误分类；  
- catalog/binding/invocation **写入语义**（DDL 属 D04）；  
- 与 prompt hash 校验的衔接（不存正文）；  
- readiness：本地默认 adapter/binding 可探测。

**S11 不负责：**

| 排除项 | 归属 |
|---|---|
| Task/Execution/Process 合法边、max-retries 账本 | S02/S03 |
| 向量 ANN、serving publication | S09 |
| vectorize 业务编排细节（outbox kind 消费） | S08（消费 S11） |
| prompt 正文与发布产品 | D03/S14 |
| 密钥与威胁模型 | S16 / `17` |
| retention/告警数值 | S15 |
| Workers AI / DO 拓扑 | **禁止** |

### 1.4 Domain 完成定义

1. §2 `T-O-180..201` 可映射到 ports、目录、表、测试；  
2. services 不 import llm_adapters；  
3. 429 不换 model；闸与 transport 错误码分账；  
4. vectorize 无 WAL 表、幂等 upsert、不丢 outbox；  
5. Layer A/B filter 可验收；  
6. §6 HARD 矩阵可通过（实现期）。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O）

| Truth-ID | 摘要 |
|---|---|
| `T-O-180` | S11=推理运行时+适配；不拥有状态机/ANN/prompt 正文 |
| `T-O-181` | 禁 Workers AI / Gateway / DO 内嵌推理为 v1 必选 |
| `T-O-182` | Domain 只经 Inference；Adapter 独占 SDK |
| `T-O-183` | LocalVllm + RemoteGemini **实现族可并存**（默认路由由 T-O-191 收窄） |
| `T-O-184` | 能力：embed / rerank / structured_generate / text_generate |
| `T-O-185` | 调用成功≠业务成功；向量存在≠serving |
| `T-O-186` | Prompt=git+hash；adapter 无正文 SSOT |
| `T-O-187` | D04 曾缺 catalog 表 → 由 T-O-193 关闭 |
| `T-O-188` | 非 Workers 模型方向（本地 Qwen VL embed 等） |
| `T-O-189` | **Inference（runtime）≠ Adapter（对接）** |
| `T-O-190` | 分能力 Inference 抽象 |
| `T-O-191` | **v1 全本地默认**；Gemini 理论/可选 |
| `T-O-192` | 不同 embedding 严禁混用；adapter/model 空间 filter |
| `T-O-193` | 三表：catalog / bindings / invocations |
| `T-O-195` | 本地分能力模型钉选（embed/rerank/instruct） |
| `T-O-196` | 落点：`runtime/inference` + `llm_adapters` |
| `T-O-197` | Layer A 空间隔离 + 调用 fail-closed 基线 |
| `T-O-198` | Layer B 业务 filter（team/intake/上游 facet） |
| `T-O-199` | Transport 有界退避；与 S03 分账；禁换模型 |
| `T-O-200` | Inference 有界并发闸 + BACKPRESSURE |
| `T-O-201` | 无 WAL；outbox+幂等 upsert；禁丢意图 |

> `T-O-194` 为 D04 表计数（55），不属 S11 产品语义但为本域物理前提。

### 2.2 域内 Truth（S11-T）

| ID | 冻结内容 | 来源 |
|---|---|---|
| `S11-T001` | Inference 门面是业务唯一入口；Adapter 禁止被 services 直接 import。 | T-O-189/190/196 |
| `S11-T002` | 能力方法闭集：`embed`、`rerank`、`structured_generate`、`text_generate`。 | T-O-184/190 |
| `S11-T003` | 统一结果附属：`adapter_kind`、`model_key`+`version`、`usage?`、`latency_ms`、`request_digest`。 | T-O-190 |
| `S11-T004` | structured 出口必须 contracts 校验通过；非法 → 失败抛弃。 | D03 + T-O-190 |
| `S11-T005` | v1 默认 binding：`adapter_kind=local_vllm` 覆盖全部能力；remote_gemini 可登记 disabled/theoretical。 | T-O-191 |
| `S11-T006` | 默认模型逻辑：embed=`qwen3-vl-embedding@2b` 级；rerank=`qwen3-vl-reranker@2b` 级；generate=catalog 登记的 local instruct（digest 幂等）。 | T-O-195 |
| `S11-T007` | 路径：`src/runtime/inference/**`、`src/llm_adapters/**`、`src/contracts/inference/**`。 | T-O-196 |
| `S11-T008` | Layer A：`(namespace, model_key, version, dimension, adapter_kind)` 写读一致；不匹配 fail-closed。 | T-O-192/197 |
| `S11-T009` | Layer B：team 强制；intake 坐标；上游 facet（如 industry-domain+map）可索引过滤；B 不替代 A。 | T-O-198 |
| `S11-T010` | TransportRetryable 有界退避；不计入 Process retry_count；禁换模型。 | T-O-199 |
| `S11-T011` | 并发闸满 → `INFERENCE_BACKPRESSURE`（retryable）；claimed≠获配额。 | T-O-200 |
| `S11-T012` | vectorize：outbox + 幂等 records；可重 embed；禁删未终态意图；无 WAL 必选表。 | T-O-201 |
| `S11-T013` | 每次最终调用写 `mkb_inference_invocations`；可选链 `generation_invocations`。 | T-O-193 |
| `S11-T014` | Readiness：默认 local binding + catalog digest 可用；remote 未启用不得挡默认就绪（除非配置强制）。 | T-O-191 |
| `S11-T015` | payload_extra / invocation 禁 secret、prompt 正文、向量全文。 | S01/D04 |

---

## 3. Contract schema 与逻辑结构

### 3.1 分层

| 层 | 目录 | 允许 | 禁止 |
|---|---|---|---|
| Inference | `src/runtime/inference/` | 能力 API、binding 解析、闸、transport policy、经 Ports 写 invocation | 持有供应商 SDK、推进业务状态机 |
| Adapter | `src/llm_adapters/` | HTTP/SDK、协议翻译、原始响应解析到 contracts | import services；写 Task/Process；存 prompt 正文 |
| Contracts | `src/contracts/inference/` | Request/Result/Usage/Error 形状 | I/O |

**依赖方向：**

```text
services → runtime.inference → llm_adapters
services 🚫 llm_adapters
llm_adapters 🚫 services / 🚫 业务表直写
```

### 3.2 能力合同（逻辑）

```text
InferenceFacade
  embed(EmbedRequest) -> EmbedResult
  rerank(RerankRequest) -> RerankResult
  structured_generate(StructuredGenerateRequest) -> StructuredGenerateResult
  text_generate(TextGenerateRequest) -> TextGenerateResult
```

**公共结果字段：** `adapter_kind`、`model_key`、`model_version`、`usage?`、`latency_ms`、`request_digest`、`invocation_uuid?`。

**EmbedResult：** 向量矩阵或单向量 + `dimension`（必须与 binding/namespace 声明一致）。  
**RerankResult：** 有序 ids + scores（或稳定并列规则）。  
**StructuredGenerateResult：** **已校验** typed 对象（非原始 dict）。

### 3.3 默认路由与模型

| capability | v1 默认 adapter | v1 默认 model 逻辑键 | 证据主候选 |
|---|---|---|---|
| embed | `local_vllm` | `qwen3-vl-embedding@2b` | `Qwen/Qwen3-VL-Embedding-2B` |
| rerank | `local_vllm` | `qwen3-vl-reranker@2b` | `Qwen/Qwen3-VL-Reranker-2B` |
| structured_generate | `local_vllm` | `local-json-generator@v1` | catalog 登记 instruct 权重 digest |
| text_generate | `local_vllm` | 可与 structured 同权重不同 profile | 同上 |

Gemini / Ranking API：允许 **disabled** binding 与适配器骨架；**非** v1 默认 readiness 路径。

### 3.4 物理表（D04 拥有 DDL；S11 拥有语义）

| 表 | S11 义务 |
|---|---|
| `mkb_model_catalog` | bootstrap 默认模型行；同 version 同 digest 幂等 |
| `mkb_adapter_bindings` | 默认 local 启用；remote 可 disabled |
| `mkb_inference_invocations` | 每次最终调用 append；禁正文/secret |
| `mkb_vector_records` | 由 S08 经 UoW 写入；S11 保证 embed 维度/model 与 binding 一致 |

### 3.5 错误轴（最小）

| 错误类 | 示例码 | retryability 建议 |
|---|---|---|
| Transport 耗尽 | `INFERENCE_TRANSPORT_EXHAUSTED` | retryable |
| 背压 | `INFERENCE_BACKPRESSURE` | retryable |
| 校验/schema | `INFERENCE_VALIDATION_*` | non_retryable |
| 配置/binding | `INFERENCE_CONFIG_*` / `ADAPTER_DISABLED` | non_retryable |
| 空间/隔离 | `INFERENCE_SPACE_VIOLATION` | non_retryable |

---

## 4. 业务流转与运行合同

### 4.1 调用通式

```text
domain command (S06/S07/S08/S10)
  → resolve binding (capability → adapter_kind + model)
  → ConcurrencyGate.acquire
  → transport loop (same binding):
       adapter.call
       on TransportRetryable → backoff ≤ N
       on other → fail
  → contracts validate (structured)
  → record inference_invocation
  → Gate.release
  → return to domain (domain 再 CAS/outbox)
```

### 4.2 Transport 退避（T-O-199）

- **可重试**：429、503、超时、连接失败、rate_limited/overloaded（语义类）。  
- **默认**：max_attempts≈3，initial_delay_ms≈1000，factor≈2，max_delay 封顶可配。  
- **不计入** Process `retry_count`。  
- **禁止** 换 model/adapter 重试。

### 4.3 并发闸（T-O-200）

- 全局 + 可选 per-capability 上限。  
- 满：`INFERENCE_BACKPRESSURE`，不调模型。  
- 与 claim 正交；可用 outbox `available_at` 延后。  
- 禁止删任务疏通。

### 4.4 Vectorize 两阶段（T-O-201）

```text
outbox vectorize_*
  → embed
  → UoW: upsert mkb_vector_records + invocation
  → outbox done
fail before done → redeliver; re-embed allowed; upsert idempotent
never drop undischarged intent
```

### 4.5 双层 Filter（T-O-197/198）

```text
Layer A space: namespace + model + version + dim + adapter_kind
Layer B business: team_uuid ∧ intake coords ∧ facets (e.g. industry-domain)
retrieve: A gate → ANN → B filters → lifecycle/serving (S04/S09)
```

### 4.6 显式 defer

| 项 | 状态 |
|---|---|
| 多 OS 进程分布式推理锁 | defer（单发布单元） |
| 向量 WAL / buffered_vectors 表 | defer reopen |
| Gemini 默认路径 / 强制 readiness | 非 v1 默认 |
| instruct 权重具体 HF id | catalog 登记，非本 Spec 绑死字符串 |
| 数值 SLA/告警阈值 | S15 |

---

## 5. 事实反例、风险与实施切片

### 5.1 Legacy 反例 → 禁令

| Legacy | MKB |
|---|---|
| `env.AI.run` / Gateway 必选 | Local vLLM 默认；禁 CF 必选 |
| DO 队列 + 删坏任务 | outbox + S03；禁丢意图 |
| WAL 必选 | v1 幂等 upsert + 可重 embed |
| content_full 在 vec 表 | 禁；generation/object |
| 429 换模型 | 禁 |
| 业务直调 gemini/AI | 只经 runtime.inference |

### 5.2 风险

| 风险 | 缓解 |
|---|---|
| vLLM 过载 | 闸 + backpressure + outbox 延迟 |
| 重复 embed 成本 | 接受 v1；未来 staging reopen |
| 混空间 | Layer A fail-closed + 禁 silent fallback |
| 业务漏 filter | Layer B 强制 team；facet 可索引 |

### 5.3 实施切片

1. contracts/inference + runtime/inference 门面 + gate/policy；  
2. LocalVllmAdapter（embed/rerank/generate）；  
3. catalog/binding bootstrap + invocation 写入；  
4. transport 退避 + 背压测试；  
5. vectorize handler 幂等 upsert；  
6. Gemini adapter 骨架（disabled）；  
7. architecture tests（import 图、禁换模型）。

---

## 6. 强制验收矩阵

| ID | HARD 场景 | 期望 |
|---|---|---|
| `S11-A01` | services import llm_adapters | architecture 失败 |
| `S11-A02` | 未 parse dict 当 structured 成功 | 拒绝 |
| `S11-A03` | 默认路径调用 remote_gemini（未启用） | ADAPTER_DISABLED / 不默认成功 |
| `S11-A04` | embed 使用错误 dimension vs namespace | SPACE_VIOLATION |
| `S11-A05` | 429 后换 model 重试 | 禁止；同 binding 退避或耗尽 |
| `S11-A06` | transport 耗尽 | 上抛；Process retry_count 未因内环 +N 误增 |
| `S11-A07` | 并发超闸 | BACKPRESSURE；无模型调用 |
| `S11-A08` | claim 多 Process 仍受闸约束 | 不并行打爆超过上限 |
| `S11-A09` | upsert 失败 outbox 仍 pending | 可重放；可重 embed |
| `S11-A10` | 幂等重放 | 不双写 conflicting vectors |
| `S11-A11` | 删 outbox 疏通队列 | 禁止 |
| `S11-A12` | 仅有向量行 | 不自动 Task success / serving |
| `S11-A13` | 跨 team 检索 | 拒绝 |
| `S11-A14` | Layer B 缺 team | 拒绝 |
| `S11-A15` | industry-domain facet 可过滤（当已登记 map） | 仅返回匹配域 |
| `S11-A16` | prompt 正文进 DB invocation | 禁止 |
| `S11-A17` | Workers AI 为 v1 必选路径 | 不存在 |
| `S11-A18` | catalog 异 digest 同 version | bootstrap/readiness fail |

---

## 7. Reference-anchor 台账

| Anchor | 用途 | 裁决 |
|---|---|---|
| structurizer/constructor `cloudflare_ai` | structured gen + usage | 升级 Port；删 Gateway 必选 |
| vectorizer `embedder.ts` | 429 退避 | 升级 T-O-199 |
| vectorizer DO mutex/429 | 资源忙 | 升级闸 T-O-200；删 DO |
| vectorizer WAL | 两阶段 | v1 用幂等+outbox；WAL defer |
| contexter embed/rerank 拆分 | 能力分面 | 保留 |
| Qwen3-VL-Embedding/Reranker-2B | 本地默认候选 | T-O-195 |
| Gemini Embedding / Ranking API | 理论通道参考 | 非默认 |

---

## 8. Domain verdict

### 8.1 Verdict

**`ACCEPTED / GO`**：S11 推理运行时与适配宪法（分层、全本地默认、能力面、双层 filter、catalog 三表、transport/闸/重放）已闭合，可作为实现与 S08/S10 formal 的权威输入。

### 8.2 强制结论

1. Inference∈runtime；Adapter∈对接；services 只调门面；  
2. v1 默认 Local vLLM 全能力；Gemini 理论可选；  
3. 禁 CF 必选路径与 DO/vec_process/WAL 回潮；  
4. Layer A 空间隔离 + Layer B 业务 filter；  
5. transport 有界退避；并发闸；outbox+幂等 records；  
6. 调用/向量存在 ≠ 业务成功。

### 8.3 下游

| 下游 | 承接 |
|---|---|
| S08 | vectorize handler 调 embed；幂等写 records |
| S09 | ANN/serving；消费 Layer A/B |
| S10 | 检索编排；rerank + 业务 filter |
| S03 | 消费 retryability；lease 与长退避共存 |
| S14 | registry 产品面（v1 code-owned 即可） |
| S15 | 指标/retention |
| D04 | 已含三表；无新强制表 |

### 8.4 一句话

S11 用 runtime 分能力推理门面 + 本地 vLLM 默认适配，在可审计的 transport/闸/幂等重放下服务 LS-RAG，而不把供应商或 Workers 拓扑写进业务真相。

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 主要变更 |
|---|---|---|---|---|
| `S11-v1.0` | `2026-08-12` | `MKB owner + Codex` | `accepted` | 吸收 Q1–Q9 / `T-O-180..201`；冻结分层、全本地、模型钉选、落点、双层 filter、三表语义、transport/闸/vectorize 耐久与验收矩阵。 |
