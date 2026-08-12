# S10 — LS-RAG Retrieval & Reranking

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 子系统**：`D7 LS-RAG 检索 / S10 LS-RAG Retrieval & Reranking`（召回·Traceback·Inflation·Rerank·结果契约）
>
> **日期**：`2026-08-12`
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **文档性质**：`domain truth / formal subsystem specification`（**唯一执行真相 SSOT**）
>
> **文档状态**：`accepted`（S10 域内已接受；全系统 truth layer 尚未 frozen）
>
> **Truth 版本**：`S10-v1.0`
>
> **上游权威输入**：`D01–D05`、`S01–S09`、`S11–S13`；`qna-truth/S10.md v1.0`（**证据层 / progressive 中间态 only**，非执行 SSOT）；冻结 Truth `T-O-247..262`
>
> **词汇权威**：`docs/baseline/spec-glossary.md` v2.7+
>
> **事实证据**：`context/legacy-family/` 仅作 ReferenceAnchor（Contexter topK/topN/internal_retrieve、Console debug、写侧 filter 对照）；网络 Reference-Check（multi-tenant RAG 安全、ParentDocument、两阶段 rerank、empty 语义）仅作设计对照；**禁止** `legacy-specs` / `legacy-python` 作为本域证据源
>
> **下游消费者**：`S01`、`S04`、`S09`、`S11`、`S12`、`S14–S16`、跨系统拓扑 `17`、验收冻结 `18`、实现与 architecture tests

> **★ 执行 SSOT 声明（Owner 强制）**：实现、验收、对账 **只依赖本 domain-truth 文件**。`qna-truth/S10.md` 仅保留 progressive 形成过程（`T-O-247..262` 冻结轨迹），**不得**被引用为第二执行真相；冲突时 **以本文为准**。禁止「细节在 QNA、Spec 只写原则」。实现 **无需** 打开 QNA 即可编码。

> **★ 约束级别**：「必须 / 禁止 / 仅允许」= 强制；「应当」= 默认，偏离须 reopen S10；「可以 / 建议」= 非冻结不变量。

> **Owner 产品边界**：S10 是 **query-side LS-RAG 检索与重排域**。实现同步 `retrieval.search`：在 S09 publication-valid 与 S04 eligibility 双围栏下，完成 Layer A embed、ANN 召回、hydrate、Traceback、DocumentInflation、Rerank 与 ContextTier packing，返回 **grounded context**（`results[]` + 可选 `pack`）。**不**拥有：PublicationProof / ActiveIndexPointer / publication-valid **定义**（S09）；Item lifecycle / serving CAS（S04）；向量 body 写（S08）；Process 八态 / `max_retries`（S03/D01）；facet 产品 map（S04）；promptA/B/C 正文（D05/S14）；推理 transport（S11）；**v1 answer generation / chat**（G-07 closed = context-only）。

> **S09 分账（T-O-244/245/250）**：S10 **必须应用** publication-valid 谓词与 `max_topk`；拥有 `return_k`/`recall_k`/threshold/rerank 策略；禁客户端换 metric。

> **S04 分账（T-O-249）**：关系侧 eligibility 仅经 `IntakeEligibilityPort`；S10 不写 lifecycle/serving。

> **S11 分账（T-O-253）**：仅经 facade 调 `embed`/`rerank`；Layer A 匹配；禁 silent model swap。

> **S01 分账（T-O-248）**：`retrieval.search` 同步；**不**创建 Task/Audit/Execution/Process。

> **Legacy 边界（T-O-255）**：不继承存在即服务、user≠team 假隔离、traceback 静默当 original、rerank dummy 0.5、空上下文仍 GENERATE、裸 file#block#g 跨代坐标。

---

## 1. Domain 介绍

### 1.1 Domain 价值

S10 把 **已发布且可服务的索引资产** 变成 **可审计、可资格围栏、可溯源原文的检索结果**，并保证：

1. ANN 命中 alone **不能** 返回业务 hit（dual fence）；  
2. summary 命中可增强召回，但 Payload **优先 original** 且 Traceback **可观测**；  
3. Inflation 有界，ContextTier 可交付多等级上下文；  
4. Rerank 提升精度但失败时 **诚实回退** ANN，不伪造分数；  
5. v1 **只返回 context**，不假装「有据回答」；  
6. 实现者 **无需** 打开 QNA 即可编码与验收。

### 1.2 在整体拓扑中的位置

```text
S08 lsrag.vectorize → S09 index.validate_publication + ActiveIndexPointer
  → S04 serving CAS
  ▼
S10 retrieval.search  (sync; no Task/Execution/Process)
  ├── validate request (team forced, k clamps, registered filters)
  ├── S11 embed(query)  // Layer A ↔ namespace
  ├── S09 VectorSearchPort (ANN, publication-valid, team, top_k=recall_k)
  ├── score threshold (config; default 0.0)
  ├── S04 IntakeEligibilityPort (batch)
  ├── hydrate dual-channel bodies (generation-scoped)
  ├── TRACEBACK (summary → original) + status
  ├── DocumentInflation (g=0 roots, dual cap)
  ├── S11 rerank (default ON) → final order
  ├── pack? (budgeted ContextTier view)
  └── RetrievalBundle { disposition, results[], pack?, diagnostics }
```

### 1.3 Scope fence

**S10 负责：**

- 同步 surface `retrieval.search` 的逻辑契约与实现端口；  
- dual-fence **应用**（消费 S09 谓词 + S04 EligibilityPort）；  
- query embed / rerank 策略与失败语义；  
- `return_k` / `recall_k` / score threshold 默认与 clamp；  
- hydrate、Traceback、DocumentInflation、dedup；  
- ContextTier packing 预算与 `pack` 视图；  
- RetrievalResult / RetrievalBundle 字段闭集；  
- `RETRIEVE_*` 错误分类、empty 机读、readiness 视角、v1 OOS。

**S10 不负责：**

| 排除项 | 归属 |
|---|---|
| Task/Execution/Process 状态机与 max_retries | D01 / S03 |
| PublicationProof 算法 / ActiveIndexPointer CAS | **S09** |
| Item lifecycle / serving_revision CAS | **S04** |
| filter/facet **产品** map | **S04** |
| 向量 upsert / ContentFull 配方 | S08 |
| ANN 物理存在 / TX / outbox 引擎 | D04 / S12 |
| embed/rerank **transport** 与 adapter | **S11** |
| answer / chat / agent | **OOS v1**（T-O-260） |
| Auth 细粒度 RBAC | S16 |
| 质量 SLA 数值 / golden 平台 | S15 |
| promptA/B/C 正文 | D05 / S14 |

### 1.4 身份与关键对象

| 对象 | 定义 | 非定义 |
|---|---|---|
| **RetrievalSearchPort** | 同步检索入口实现 | 非 Process capability；非 Task |
| **RetrievalBundle** | disposition + results + pack? + diagnostics | 非 chat transcript |
| **RetrievalResult** | 单 hit 可审计记录（Hit/Payload 分账） | 非 raw vector |
| **Traceback** | summary→同 generation-scoped original | 非跨 rebuild 裸三元组 |
| **DocumentInflation** | 有界附加 g=0 original | 非无限全文灌入 |
| **PackView** | 预算内 ContextTier 组装视图 | 非唯一真相；results[] 权威 |
| **RankPolicy** | recall_k / return_k / threshold / rerank | 非 S09 max_topk 定义权 |

### 1.5 完成定义

1. §2 全部 Truth 被 contracts 与 transition 实现；  
2. 无 publication-valid 或 eligibility 的 hit **不可** 出现在 results；  
3. TracebackStatus 必填；失败不可伪装 original；  
4. rerank 失败无 dummy 分；  
5. pack 超预算可观测；  
6. Response **无** answer / raw embedding；  
7. 零 legacy Contexter 资格/假隔离语义依赖；  
8. 实现 **无需** 打开 QNA；  
9. §6 验收矩阵通过。

---

## 2. 真相层

### 2.1 Owner Truth 登记（全局 T-O · S10 段 · 执行摘要）

| Truth-ID | 摘要 | 本域强制 |
|---|---|---|
| `T-O-247` | S10 = 检索/重排域；不吞 S08/S09/S04/S11 | scope |
| `T-O-248` | `retrieval.search` 同步；无 Task/Execution/Process | surface |
| `T-O-249` | dual fence；禁仅 ANN 返回 | eligibility |
| `T-O-250` | 应用 publication-valid + max_topk；策略归 S10 | index consume |
| `T-O-251` | 双通道；Traceback 可观测；Inflation 允许 | product |
| `T-O-252` | generation-scoped 坐标 | coordinate |
| `T-O-253` | Layer A/B；S11 embed/rerank only | inference |
| `T-O-254` | RetrievalResult 最小字段 | result |
| `T-O-255` | legacy-family only；greenfield | evidence |
| `T-O-256` | G-07 residual → R2 关闭；召回错误归 S10/S11 | residual |
| `T-O-257` | 硬 dual-fence 管道；empty≠error；无 raw vector | pipeline |
| `T-O-258` | Traceback + Inflation 双 cap；generation-scoped | traceback |
| `T-O-259` | return_k=10；recall_k=20；threshold=0.0；rerank ON 诚实 fallback | rank |
| `T-O-260` | G-07 closed：context-only；无 answer | G-07 |
| `T-O-261` | results[] + pack 预算默认 | packing |
| `T-O-262` | RETRIEVE_*；readiness；OOS；R3 waived | contract/ops |

### 2.2 域内 Truth 编号（S10-T）

| ID | 冻结内容 | 来源 | 验收要点 |
|---|---|---|---|
| `S10-T001` | 同步 `retrieval.search`；不创建 Task/Audit/Execution/Process。 | T-O-248 | S01-A24 |
| `S10-T002` | v1 **context-only**；无 answer 字段；禁 `include_answer`。 | T-O-260 | G-07 closed |
| `S10-T003` | 管道序：validate → embed → ANN(publication-valid+team) → threshold → EligibilityPort → hydrate → Traceback → Inflation → Rerank → pack → Bundle。 | T-O-257 | 不可跳段 |
| `S10-T004` | 禁止仅 ANN 命中返回业务 hit。 | T-O-249/257 | architecture |
| `S10-T005` | Empty（ok+empty/`RETRIEVE_EMPTY` 机读）≠ Error（4xx/5xx typed）。 | T-O-257 | |
| `S10-T006` | Empty 原因可含：`no_hit` / `all_filtered` / `below_threshold` / `blank_query`。 | T-O-257/262 | diagnostics |
| `S10-T007` | Error：缺 team、k 越 cap、Layer A 不匹配、未知 filter、非法 pin、依赖失败、schema 非法。 | T-O-257 | |
| `S10-T008` | `team_uuid` 服务端强制；未知 filter key fail-closed。 | T-O-257 | |
| `S10-T009` | v1 禁止客户端覆盖 active `index_generation`；禁 client metric / raw query vector / model override。 | T-O-257/250 | |
| `S10-T010` | 公共面 **永不** 返回 raw embedding。 | T-O-257 | |
| `S10-T011` | 必须应用 S09 publication-valid 最小谓词（见 S09-E07）。 | T-O-250 | |
| `S10-T012` | 必须 batch 调用 S04 `IntakeEligibilityPort`。 | T-O-249 | |
| `S10-T013` | `return_k` 默认 10；clamp `[1, max_topk]`；越界 fail-loud。 | T-O-259 | |
| `S10-T014` | `recall_k` 默认 20；`return_k ≤ recall_k ≤ max_topk`。 | T-O-259 | |
| `S10-T015` | `retrieve.default_score_threshold` 默认 **0.0**；配置化；legacy 0.65 非 Truth。 | T-O-259 | |
| `S10-T016` | Rerank 默认 ON（S11）；query 与 embed **同源**；documents = Traceback 后 payload。 | T-O-259 | |
| `S10-T017` | Rerank 失败：保留 ANN 序与 `ann_score`；`rerank_status=failed|skipped`；**禁** dummy 假分。 | T-O-259 | |
| `S10-T018` | 成功 rerank：主 `score`=rerank；保留 `ann_score` 分账。 | T-O-259 | |
| `S10-T019` | summary hit 必须尝试 Traceback；`traceback_status` 必填。 | T-O-258 | |
| `S10-T020` | Traceback 键 = generation-scoped coordinate + channel 切换；禁裸 file#block#g 身份。 | T-O-252/258 | |
| `S10-T021` | Traceback 失败：per-hit 可回退 summary 文本；**禁**标成 original；不整查询 fail-closed。 | T-O-258 | |
| `S10-T022` | original hit：`traceback_status=not_needed`；payload=hit。 | T-O-258 | |
| `S10-T023` | DocumentInflation 默认 ON；目标同 generation g=0 original。 | T-O-258 | |
| `S10-T024` | Inflation 默认预算：`inflation_max_roots=3`；`inflation_per_root_max_chars=8000`（配置化）。 | T-O-261 | |
| `S10-T025` | 超预算可观测 truncate/drop；禁 silent。 | T-O-258/261 | |
| `S10-T026` | `results[]` 权威；每条含 D05 最小字段 + scores/status。 | T-O-254/261 | |
| `S10-T027` | `pack`：v1 默认 `include_pack=true`；`pack_max_hits=5`；`pack_max_chars=12000`。 | T-O-261 | |
| `S10-T028` | pack 失败不影响 results；`pack_truncated` 可观测。 | T-O-261 | |
| `S10-T029` | 同 generation+unit dedup；优先 resolved original payload。 | T-O-261 | |
| `S10-T030` | v1 diversify OFF；channel boost OFF。 | T-O-259/261 | |
| `S10-T031` | ContextTier：g=1/2 → `focus_fragment`（+可选 root）；g=0 → `document_root`。 | T-O-251；D05 | |
| `S10-T032` | Payload 优先 original（resolved 时）。 | T-O-251 | |
| `S10-T033` | Hydrate 正文来自 dual-channel/artifact；非向量表 content_full 列；非 ANN metadata 当 SSOT。 | T-O-254；D04 | |
| `S10-T034` | 错误前缀闭集：`RETRIEVE_*` / `RETRIEVE_DEPENDENCY_*` / 推理映射；禁主用 `PUBLISH_*`。 | T-O-262 | |
| `S10-T035` | 无 Process；无私有 max_retries 账本。 | T-O-248/262 | |
| `S10-T036` | Readiness=false 条件见 §4.9。 | T-O-262 | |
| `S10-T037` | OOS 清单见 §4.9。 | T-O-262 | |
| `S10-T038` | Layer A 不匹配 → fail-closed（非 empty）。 | T-O-253 | |
| `S10-T039` | contracts 落点：`src/contracts/vector/`（request/response/result）。 | D03；T-O-262 | |
| `S10-T040` | 不新增 StateFamily；query 不是第七状态。 | D02 | |
| `S10-T041` | 进度/日志非 SSOT。 | — | |
| `S10-T042` | filters_echo 回显已应用（注册键）；不含 secret。 | T-O-254 | |
| `S10-T043` | 域事件（低基数，可选）：`retrieve.completed` / `retrieve.empty` / `retrieve.failed` / `retrieve.rerank_failed`（S15 保留）。 | T-O-262 | |
| `S10-T044` | G-07 关闭声明：v1 不承担 answer generation。 | T-O-260 | index |
| `S10-T045` | 实现无需打开 QNA。 | SSOT | |

### 2.3 继承上游（不重开）

- **S09**：publication-valid、ActiveIndexPointer、cosine、default topK/max_topk、VectorSearchPort。  
- **S04**：lifecycle、serving CAS、EligibilityPort、facet 权威。  
- **S08**：records 坐标/channel/Layer B 抄写；存在≠可服务。  
- **S07/S06/D05**：dual-channel、generation-scoped、Hit/Payload、ContextTier 产品法。  
- **S11**：embed/rerank facade、Layer A、G-10。  
- **S01**：同步 surface。  
- **D04/S12**：同库 ANN substrate、ports、readiness probe。

---

## 3. 总体方案陈述

1. **读侧独立 surface**：同步检索，不污染 Task/Process runtime。  
2. **双围栏硬管道**：索引谓词 + 关系 eligibility；ANN 只是候选源。  
3. **双通道语义**：summary 助召回；original 助交付；Traceback 可观测。  
4. **小块命中、有界膨胀**：parent/g=0 按预算附加。  
5. **两阶段排序**：宽 `recall_k` → rerank → `return_k`；失败诚实。  
6. **结构 hits + 可选 pack**：审计与组装分账。  
7. **Context-only v1**：拒幻觉式「空上下文仍回答」。  
8. **错误与 readiness 可验收**：`RETRIEVE_*` 族；依赖邻域 probe。  
9. **QNA 零依赖**：全部执行细节在本文 §4。

---

## 4. 具体执行方案清单

### 4.1 `S10-E01` — Surface、目录与能力边界

**真相**：S10-T001/T002/T039/T044；T-O-248/260

| 项 | 规范 |
|---|---|
| 公共 surface | `retrieval.search`（逻辑名；HTTP 路径由 S01/路由层绑定，本 Spec 钉语义） |
| 同步 | 必须；单请求内完成；无 outbox 副作用作为成功条件 |
| 持久副作用 | **禁止** 创建 Task/Audit/Execution/Process 行 |
| answer | **禁止** v1 |
| 代码落点 | `src/services/` 原子检索 capability；`src/contracts/vector/` schemas |
| 非能力 | 不是 S03 ProcessCapability key |

---

### 4.2 `S10-E02` — Dual-fence 服务管道

**真相**：S10-T003..T012；T-O-257/249/250

**强制序**

```text
1. validate_request
2. resolve_namespace + Layer A binding (S11)
3. embed_query (S11 embed)
4. vector_search (S09 port): team forced + publication-valid + recall_k
5. apply_score_threshold
6. batch_eligibility (S04 IntakeEligibilityPort)
7. hydrate (generation-scoped dual-channel bodies)
8. traceback
9. inflation
10. dedup
11. rerank (S11; default ON)
12. truncate_to_return_k
13. pack (if include_pack)
14. emit RetrievalBundle
```

**禁止**：跳过 4–6；把 file_status/ready/processing_status 当唯一资格；fail-open 去 team filter。

**Empty vs Error**

| 类别 | 条件 | 响应 |
|---|---|---|
| empty | 无 ANN 命中；全 threshold 滤掉；全 fence 滤掉；blank query（trim 后） | disposition=`empty`；results=[]；可带 empty_reason |
| error | 缺 team；return_k/recall_k 非法；Layer A 不匹配；未知 filter；非法 pin；namespace 未知；S11/S12/S09 硬依赖失败；schema 非法 | typed error code；非「假 empty」 |

---

### 4.3 `S10-E03` — Rank policy（threshold / recall / return / rerank）

**真相**：S10-T013..T018；T-O-259

| 参数 | 默认 | 规则 |
|---|---|---|
| `return_k` | 10 | 1..max_topk（S09） |
| `recall_k` | 20 | return_k ≤ recall_k ≤ max_topk |
| `score_threshold` | 0.0 | 配置键 `retrieve.default_score_threshold`；请求可降不可超实现 max（若设） |
| rerank | ON | S11 `rerank`；本地 binding |
| diversify | OFF | v1 |
| channel boost | OFF | v1 双通道同池 |

**Rerank I/O**

```text
in: query (same as embed), documents[{id, text=payload}], top_n=return_k (or pool size)
out: ordered {id, score}[]
on_fail: keep ANN order + ann_score; rerank_status=failed
on_skip (0/1 cand): rerank_status=skipped; keep ann_score
forbidden: fabricate 0.5 / 1.0 as fake model score when failed
```

**Final score**

- rerank success → `score = rerank_score`；`ann_score` retained  
- else → `score = ann_score`

---

### 4.4 `S10-E04` — Traceback 与 generation-scoped hydrate

**真相**：S10-T019..T022/T033；T-O-258/252

**算法**

1. Hydrate hit 行：channel、generation refs、unit_id、granularity、body/ref。  
2. 若 `channel=summary`：按 **同 team + 同 generation-scoped coordinate** 取 `channel=original` 正文。  
3. 成功：`payload=original`，`traceback_status=resolved`，保留 `hit_content=summary`。  
4. 失败：`traceback_status=failed|degraded`；payload 可=summary 文本；**禁止** 将语义标为「已还原 original」。  
5. 若 `channel=original`：`traceback_status=not_needed`，payload=hit。

**禁止**：ANN metadata 当原文 SSOT；`content_full` 向量表列；裸 `file#block#g` 跨 rebuild 身份。

---

### 4.5 `S10-E05` — DocumentInflation 与 ContextTier

**真相**：S10-T023..T025/T031；T-O-258/261

| 项 | 规范 |
|---|---|
| 默认 | ON |
| 触发 | 非 g=0 焦点 hit |
| 目标 | 同 generation 的 g=0 **original** |
| max roots / query | 3（配置） |
| per-root max chars | 8000（配置） |
| 超限 | 可观测 truncate 或 skip + diagnostic count |
| ContextTier on hit | g=2/1 → `focus_fragment`；g=0 → `document_root` |

---

### 4.6 `S10-E06` — RetrievalBundle 契约（Request/Response）

**真相**：S10-T026..T030/T002/T010；T-O-260/261/262

**Request 最小闭集**

```text
team_uuid                 # required; server-enforced
query                     # required string
namespace_key | namespace_uuid
return_k?                 # default 10
recall_k?                 # default 20
score_threshold?          # default config 0.0
filters?                  # registered Layer B pins only
include_pack?             # default true
# FORBIDDEN: raw_query_vector, distance_metric, embedding_model,
#            index_generation (v1 public), include_answer, stream
```

**Response 最小闭集**

```text
disposition: ok | empty | error
results: RetrievalResult[]      # may be empty
pack?: PackView                 # if include_pack and disposition ok|empty
diagnostics: {
  recall_k, return_k, threshold_applied,
  ann_hit_count, eligible_count, filtered_count,
  rerank_status, pack_truncated?,
  empty_reason?: no_hit|all_filtered|below_threshold|blank_query
}
```

**RetrievalResult 最小字段**

```text
score                    # final
ann_score
rerank_score?            # present if rerank succeeded for this id
hit_channel
hit_content | hit_content_ref
payload_content | payload_content_ref
coordinate               # generation-scoped
granularity              # 0|1|2
generation_refs
traceback_status         # not_needed|resolved|failed|degraded
context_tier
filters_echo
# FORBIDDEN: embedding[], secrets, filesystem paths, provider raw bodies
```

**PackView 最小**

```text
text?                    # optional assembled string
segments[]?              # optional structured segments with tier + refs
pack_hit_count
pack_char_count
truncated: boolean
```

---

### 4.7 `S10-E07` — Packing 算法

**真相**：S10-T027..T029；T-O-261

1. 输入：已排序 `results`（≤ return_k）。  
2. Dedup：同 `(generation, unit)` 保留最高排序一条（优先 resolved original payload）。  
3. 按序纳入 pack，直到 `pack_max_hits` 或 `pack_max_chars`。  
4. 每 hit：写入 focus payload；若 inflation 成功且预算允许，附加 document_root 片段。  
5. 停止时设 `pack_truncated` 若仍有剩余未纳入 hit 或正文被截。  
6. pack 异常：省略 pack 或 empty pack + diagnostic；**results 仍返回**。

---

### 4.8 `S10-E08` — 与 S09/S04/S11 端口合同

| 端口 | 方向 | 合同 |
|---|---|---|
| S09 VectorSearchPort | S10 → S09 | team、namespace、query_embedding、top_k=recall_k、filters；**必须** publication-valid；禁 skip；禁 client metric |
| S04 IntakeEligibilityPort | S10 → S04 | team/item/serving_revision/lifecycle 批验 |
| S11 embed | S10 → S11 | query text；dim 匹配 namespace |
| S11 rerank | S10 → S11 | query + docs；失败映射 `RETRIEVE_INFERENCE_*` 或降级 ANN |

---

### 4.9 `S10-E09` — 错误、Readiness、OOS

**真相**：S10-T034..T037；T-O-262

**错误前缀**

| 前缀 | 含义 | 示例 |
|---|---|---|
| `RETRIEVE_EMPTY` | 业务空结果（可作 disposition=empty 机读） | no_hit |
| `RETRIEVE_FILTER_INVALID` | 未知/非法 filter 或 pin | |
| `RETRIEVE_TOPK_INVALID` | return_k/recall_k 越界或不满足不等式 | |
| `RETRIEVE_SPACE_*` | Layer A 不匹配 | non_retryable 语义 |
| `RETRIEVE_SCHEMA_*` | 请求 schema | |
| `RETRIEVE_DEPENDENCY_*` | S04/S09/S12 依赖 | |
| `RETRIEVE_INFERENCE_*` | embed/rerank（可映射 S11 码） | SPACE_VIOLATION → hard fail |

**禁止** 以 `PUBLISH_*` / `INDEX_*` 作为 search API 主 taxonomy。

**Readiness=false 当**

1. S09/S12 vector 或 ANN probe 失败；  
2. 默认 namespace / ActiveIndexPointer 策略缺失且配置强制；  
3. S11 默认 embed binding 不可用；  
4. rerank 默认 ON 且 rerank binding 不可用且策略要求硬依赖（若配置允许 degrade，须显式；**v1 默认**：rerank 不可用 → readiness 仍可 true，但运行时 `rerank_status=failed` 回退 ANN——**推荐**：readiness 对 embed 硬、对 rerank 软）；  
5. vector retrieve contracts 未注册。

> **v1 钉死**：embed binding 缺失 → readiness=false；rerank binding 缺失 → readiness **仍可 true**，查询路径 ANN fallback（与 T-O-259 一致）。

**OOS（v1 禁止义务）**

- answer generation / chat / session / agent  
- 异步 retrieval Task  
- 客户端 raw vector / 自选 metric / 自选 embedding model  
- Hybrid BM25 产品  
- 强制 shadow/canary 评测平台  
- 公网 vector CRUD  
- MMR diversify 默认算法  
- AuthZ 细粒度 RBAC（S16）  
- 质量 SLA / golden 平台数值（S15）  
- 公共诊断非 active `index_generation` 开关  

---

### 4.10 `S10-E10` — 与邻域交接

| 邻域 | 合同 |
|---|---|
| S01 | surface 同步；路由不写 Task |
| S04 | EligibilityPort only；不写 serving |
| S09 | 谓词 + VectorSearchPort + max_topk |
| S08 | 只读 records 形状假设 |
| S07/S06 | 坐标与 dual-channel 假设 |
| S11 | embed/rerank |
| S12 | TX 只读查询一致性；probe |
| S13 | payload ref 解引用（若用 object ref） |
| S14 | 可版本化默认预算/threshold 配置 |
| S15 | 事件与指标；非 SSOT |
| S16 | token/team 边界；细 RBAC defer |

---

## 5. 事实反例 + 风险台账

### 5.1 反例（禁止方向）

| 反例 | 订正 |
|---|---|
| 存在即服务 / 无 dual fence | T-O-249/257 |
| source_name 假隔离 / 死参数 filter | T-O-257 fail-closed |
| Traceback 静默 summary-as-original | T-O-258 |
| 裸 file#block#g 跨代 | T-O-252 |
| rerank dummy 0.5 | T-O-259 |
| 空上下文仍 GENERATE | T-O-260 |
| 返回 raw embedding | T-O-257 |
| 客户端换 metric / model | T-O-250/253 |
| 主用 PUBLISH_* 作 search 错误 | T-O-262 |
| pack silent drop 无信号 | T-O-261 |

### 5.2 风险与围栏

| 风险 | 围栏 |
|---|---|
| fence 漏实现 | 验收 A 矩阵禁 ANN-only |
| threshold 误杀 | 默认 0.0 + 配置标定 |
| rerank 不可用 | 诚实 ANN fallback |
| pack 超长 | 双 cap + truncated flag |
| G-07 回潮 chat | OOS + 禁 answer 字段 |
| filter 产品漂移 | 仅 S04 注册键 |

### 5.3 默认量级（配置化，非商业 SLO）

| 项 | 默认 |
|---|---|
| return_k | 10 |
| recall_k | 20 |
| max_topk | 100（S09） |
| score_threshold | 0.0 |
| pack_max_hits | 5 |
| pack_max_chars | 12000 |
| inflation_max_roots | 3 |
| inflation_per_root_max_chars | 8000 |

---

## 6. 测试与验收台账

| ID | 场景 | 类型 |
|---|---|---|
| S10-A01 | 合法 serving+active gen → 返回 hits；含 generation_refs | 集成 |
| S10-A02 | ANN 命中但 publication 不 valid → 不入 results | 集成 |
| S10-A03 | ANN 命中但 lifecycle deactivated → 不入 results | 集成 |
| S10-A04 | 缺 team → error 非 empty | 合同 |
| S10-A05 | 未知 filter key → RETRIEVE_FILTER_INVALID | 合同 |
| S10-A06 | return_k > max_topk → fail-loud | 合同 |
| S10-A07 | recall_k < return_k → fail 或 clamp 策略按实现 fail-loud | 合同 |
| S10-A08 | summary hit → traceback resolved + payload original | 集成 |
| S10-A09 | missing original → status failed/degraded；不标 original | 故障 |
| S10-A10 | inflation 附加 g=0；超 roots/chars 可观测 | 集成 |
| S10-A11 | rerank fail → ANN order + ann_score；无 0.5 | 故障 |
| S10-A12 | Layer A mismatch → error | 单元 |
| S10-A13 | Response 无 embedding[] / 无 answer | architecture |
| S10-A14 | blank query → empty | 合同 |
| S10-A15 | include_pack true → pack 字段与 truncated 行为 | 集成 |
| S10-A16 | dual channel same unit dedup | 单元 |
| S10-A17 | 不创建 Task/Process 行 | architecture |
| S10-A18 | soft-deleted vectors 不可服务 | 集成 |
| S10-A19 | non-active index_generation 不可被 client 选择 | 合同 |
| S10-A20 | readiness：embed 缺失 false；contracts 缺失 false | readiness |

**必须留存证据**：contract schemas、管道集成报告、fence 否定用例、traceback fixtures、rerank fallback 报告、pack 预算 golden。

---

## 7. Reference-anchor 台账

### 7.1 权威文档锚

- `qna-truth/S10.md` v1.0（`T-O-247..262` 轨迹）  
- `S09-v1.0` 谓词/topk；`S04` EligibilityPort；`D05` 召回产品法；`S01-T025`  
- `spec-glossary` RetrievalEligibility / Traceback / ContextTier / IndexTopKPolicy  

### 7.2 Legacy 代码事实锚（ReferenceAnchor only）

| 组件 | 用途 |
|---|---|
| contexter `ai/topK.ts` | 读路径；filter 假隔离；traceback |
| contexter `ai/topN.ts` | rerank；dummy 分反例 |
| contexter `rag/internal_retrieve.ts` | inflation 预算正/反例 |
| contexter `core/db_vec.ts` | returnValues false 正例 |
| console vec-debug | 运维≠eligibility 正例 |

### 7.3 网络对照（非 Truth）

| 主题 | 对照 |
|---|---|
| 双层授权 / fail-open | AWS multi-tenant RAG |
| ACL / fail-closed / embedding 隐私 | OWASP RAG Security Cheat Sheet |
| Parent / small-to-big | LangChain ParentDocumentRetriever |
| 两阶段 rerank | Pinecone / NVIDIA cascade |
| empty 200 | REST search 惯例 |
| 分数字段分账 | Azure semantic/reranker scores |

### 7.4 证据使用判定

- legacy / 网络 **不得** 成为运行时依赖或兼容目标。  
- 仅用于正/反例与验收启发。

---

## 8. Domain verdict

### 8.1 最终评价

S10-v1.0 将 progressive `T-O-247..262` 升格为 **唯一可编码执行真相**：dual-fence 管道、Traceback/Inflation、rank policy、context-only 出口、Bundle 契约、错误/readiness/OOS 均已闭包。与 S01/S02/S09 同构的九段式可验收结构 + E01–E10 执行台账。

**`ACCEPTED / GO`**

### 8.2 未解决边界（明确移交，非本域 blocker）

| 主题 | 归属 |
|---|---|
| Facet wire map 产品定义 | S04 |
| Auth 细粒度 / 限流数值 | S16 |
| 质量 benchmark / golden 平台 | S15 |
| Hybrid BM25 / MMR 默认算法 | 未来 reopen |
| Answer surface | 未来 versioned 扩展（非本 v1） |
| 配置默认值的多环境 profile 管理 | S14 |

### 8.3 对下游约束

- **S01/路由**：暴露同步 retrieval.search；不写 Task。  
- **S04**：EligibilityPort 稳定批验语义。  
- **S09**：VectorSearchPort 强制 publication-valid；max_topk 稳定。  
- **S11**：embed/rerank 可用性与 Layer A。  
- **S12**：只读一致性与 ANN probe。  
- **G-07**：**closed** = context-only（T-O-260）。  
- **contracts**：`src/contracts/vector/` 必须覆盖 Bundle。

### 8.4 完成状态

| 项 | 状态 |
|---|---|
| QNA progressive | **locked / Round 3 waived** |
| Formal Spec | **S10-v1.0 accepted** |
| 执行 SSOT | **本文 only** |
| G-07 | **closed / context-only** |

---

## 9. 修订历史

| 版本 | 日期 | 作者 | 状态 | 变更 |
|---|---|---|---|---|
| `S10-v1.0` | `2026-08-12` | `MKB owner + Codex` | `accepted` | 自 `qna-truth/S10.md v1.0`（`T-O-247..262`）升格唯一执行 SSOT；九段式 + E01–E10；dual-fence/Traceback/rank/pack/context-only/契约闭包；Round 3 waived；G-07 closed |
