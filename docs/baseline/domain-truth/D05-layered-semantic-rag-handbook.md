# D05 — Layered-Semantic RAG System Handbook

> **项目**：`myknowledgebase`（MKB）
>
> **Domain / 共有域**：跨 `D1–D8 / S03–S11` 的 **LS-RAG 产品与执行心智** 高等级裁决层
>
> **文档性质**：`higher-order domain truth / product & systems handbook`（**D 系最终裁决**）
>
> **文档状态**：`frozen / owner-gated`（**D05-v1.0**；全系统 truth layer 尚未 frozen）
>
> **Truth 版本 / 日期**：`D05-v1.0 / 2026-08-12`
>
> **冻结 Truth-ID**：`T-O-202..210`（见 §0.0）
>
> **作者 / 裁决者**：`MKB owner + Codex`
>
> **权威输入**：`D01–D04`、`S03-v1.3`、`S04–S07`、`S11–S13`；legacy-family ReferenceAnchor only
>
> **词汇权威**：`docs/baseline/spec-glossary.md` **v2.5 §4**
>
> **下游强制服从**：`S05–S10`、`S11`、`S14`（prompt）、`D03/D04`、拓扑 `17`、验收 `18`

> **★ 裁决等级**：`D*` > `S*`。实现只依赖 domain-truth + contracts。  
> **★ 本文不拥有**：Process 八态、`max_retries` 账本、Outcome 上报形状——**必须引用** `D01` / `S03`（见 §0.5、§2.5）。

> **★ Owner 冻结摘要（2026-08-12 · T-O-202..210）**  
> 1. 默认 **双通道** = LS-RAG 根本；  
> 2. 默认三粒度 **0/1/2**；  
> 3. **FullDocument（0）必入向量候选**；  
> 4. 向量化失败 **仅** 服从 D01/S03 max_retries + 上报；  
> 5. **construct 合法原料后门闩** 才 vectorize；  
> 6. 生产三 Prompt：**promptA=Clean · promptB=Structurizer · promptC=Summarizer**（`variant.version` + DB hash）；  
> 7. Traceback 默认可观测 degraded；Inflation 允许；v1 默认仅 construct 后 vectorize。

> **★ 骨架**  
> §0 业务逻辑·粒度·**三生产 Prompt**·债务·失败引用  
> §1 Intake·Artifact·D01/D02  
> §2 Recall·双通道·多粒度上下文  
> §3 glossary 引用  
> §4 D04 映射  
> §5 typed schema 详例 ↔ D03 contracts  

---

## 0.0 ★ Truth-Gate 台账（append-only · frozen）

| Truth-ID | 子类型 | 已锁定真相 | 下游强制 |
|---|---|---|---|
| `T-O-202` | `foundational / authority` | **D05** 是 LS-RAG 产品与执行心智 **高等级 handbook**；`D*` 裁决高于 `S*`；冲突以最新 frozen D05 为准并回填 S；不拥有 Process 状态机/`max_retries`（归 D01/S03）。 | 全 S05–S10/S14 |
| `T-O-203` | `product / dual-channel` | **默认双通道**（Original+Summary 共 GenerationScopedCoordinate、默认可索引）是 LS-RAG **根本**，非可选插件。 | S07/S08/S10 |
| `T-O-204` | `product / granularity` | v1 **默认粒度集合 {0,1,2}**：0=FullDocument 全文层；1=Section 章节层；2=Paragraph 段落层；定义与举例以 §0.3 为准；更细层须 profile 显式注册。 | S06/S07/S08 |
| `T-O-205` | `product / full-document vector` | **粒度 0（FullDocument）必须进入向量候选**（original 非空则必有 original 向量意图；summary 在 dual-channel 完备规则下进入 summary 意图）。 | S07/S08 |
| `T-O-206` | `product / construct-gate` | **仅** `lsrag.construct` full_valid + dual-channel 完备 + g=0 在场 + multi-pointer CAS 后，才可交付 `vectorize_construct`；禁止跳过 construct 直接 vectorize。 | S07/S08/S03 |
| `T-O-207` | `product / failure-ref` | 向量化/结构/构造/清洗叶失败的 retry、max_retries、向上归约 **只引用 D01/S03**（及 S11 transport 分账）；**D05 不新建**重试真相。 | S03/S05–S08/S11 |
| `T-O-208` | `product / prompt-trinity` | 生产主链模型指令 **三身份闭集**：**promptA=Clean**、**promptB=Structurizer**、**promptC=Summarizer**；命名 `prompt{A\|B\|C}.variant.version`；正文 git `data/prompts/**`；DB 仅 content_hash 指针；运行 hash 校验 fail-fast；锚定 §0.2/§0.6。 | S05/S06/S07/S14/D03 |
| `T-O-209` | `product / recall` | 召回：summary 可增强命中；Traceback 还原 original；Hit/Payload 分账；TracebackStatus 默认可观测；DocumentInflation 允许有界 g=0；ContextTier 交付多等级上下文。 | S10 |
| `T-O-210` | `product / pipeline` | 规范链：promptA@clean → promptB@structurize → promptC@construct → gate → vectorize → publication → retrieve；阶段成功分账；存在≠可服务。 | S05–S10 |

---

## 0. 业务逻辑 · 粒度 · Prompt · 债务 · 失败收敛引用

### 0.1 LS-RAG 业务逻辑（冻结）

术语见 glossary：`LS-RAG`、`DualChannel`、`ContentLayer`、`VectorizationUnit`。

**LS-RAG 根本不变量（Owner）**：

1. **双通道默认开启**：每个应索引单元同时具备 **OriginalChannel** 与 **SummaryChannel** 的可索引资格（body 非空才物化向量行；construct 成功要求 dual-channel 完备——S07）。  
2. **默认三粒度** `0 | 1 | 2`（见 §0.3）；可 profile 扩展更细，但 v1 **系统默认只要求这三层**。  
3. **粒度 0（FullDocument）必须进入向量候选**（original 非空则必 embed；其 summary 在 dual-channel 完备规则下亦进入候选）。  
4. **construct 合法完成后** 才 fanout 给 vectorize（§0.4）。  
5. 召回：summary 可增强命中；**PayloadContent 优先 original**（Traceback）。

**一句话（冻结）**：

> 以 **GenerationScopedCoordinate** 为轴，在 **粒度 0/1/2** 上默认维护 **Original+Summary 双通道**；FullDocument 必入向量候选；construct 合法后方可 vectorize；召回命中语义层后还原原文，并按 ContextTier 交付有界上下文。

### 0.2 端到端业务链（规范 · 含三生产 Prompt 锚定）

> **生产链上的模型指令只有三类产品身份**（Owner 冻结命名）：  
> **`promptA`** = Clean · **`promptB`** = Structurizer · **`promptC`** = Summarizer。  
> 身份格式：`prompt{A|B|C}.<variant>.<version>`；运行真值 = **DB hash 指针** 校验的 git 正文（D03）。  
> 详语义见 **§0.6**。

```text
┌─ INTAKE / CLEAN（生产环节 1）────────────────────────────────────┐
│ S04 admit + S05 clean.* Process                                    │
│   ★ 绑定 promptA.<variant>.<version>  (+ content_hash)             │
│   产出: clean IntakeArtifact（verified plain text / elements）     │
│   phase 例: cleaning                                               │
└───────────────────────────────┬────────────────────────────────────┘
                                │ exact clean handle+digest
                                ▼
┌─ STRUCTURIZE（生产环节 2）───────────────────────────────────────┐
│ Process: lsrag.structurize                                         │
│   ★ 绑定 promptB.<variant>.<version>  (+ content_hash)             │
│   产出: StructureDocument + RetrievalBlockProjection (g=0/1/2)     │
│   phase: structurizing                                             │
└───────────────────────────────┬────────────────────────────────────┘
                                │ exact structure+projection refs
                                ▼
┌─ CONSTRUCT / SUMMARIZE（生产环节 3）─────────────────────────────┐
│ Process: lsrag.construct (mode=full_construct 时)                  │
│   ★ 绑定 promptC.<variant>.<version>  (+ content_hash)             │
│   产出: DualChannelProjection（Summary 通道）+ Construction*       │
│   phase: constructing                                              │
│   门闩: full_valid 后才 outbox vectorize_construct（§0.4）         │
└───────────────────────────────┬────────────────────────────────────┘
                                ▼
  vectorize (S08)  【无新 Prompt 产品身份；embed 经 S11，非 promptA/B/C】
  → index.validate_publication (S09)
  → Retrieve (S10) 【查询侧可有 rewrite prompt，OOS 本三元组；不叫 promptA/B/C】
```

**链上锚定一览（冻结）**

| 生产环节 | Process / capability | Prompt 产品身份 | 输入 | 输出 |
|---|---|---|---|---|
| **Clean** | S05 `clean.*`（如 web/doc/vision 等 exact keys） | **`promptA`** | raw/source evidence | clean IntakeArtifact |
| **Structurize** | `lsrag.structurize` | **`promptB`** | clean Artifact | structure + projection（多粒度 original） |
| **Summarize（Construct 内）** | `lsrag.construct` | **`promptC`** | structure+projection | dual-channel（填 Summary） |
| Vectorize | S08（placeholder key） | **无**（非本三元组） | dual-channel 合法原料 | VectorRecord |

### 0.3 默认三粒度定义与举例（Owner 冻结）

> 生产整数 `granularity` 语义保留；MKB **产品层** 使用下列定义。跨代身份仍用 **GenerationScopedCoordinate**（含 generation + unit id），**禁止**仅用裸整数当跨 rebuild identity。

| 粒度码 | 规范名 | 定义（冻结） |
|---|---|---|
| **`0`** | **FullDocumentLayer** / 全文层 | **整份 intake 文档在结构投影上的根层检索单元**：覆盖全文（或 clean 全文等价范围）的 original body；title 通常为文档标题。生产注释：`0 = 全文`。 |
| **`1`** | **SectionLayer** / 章节层 | **一级结构分块**：对应文档主要章节/一级标题下的连贯正文（一个 heading 主导的 section 范围）。生产注释：`1 = 章节`。 |
| **`2`** | **ParagraphLayer** / 段落层 | **章节内更细的检索单元**：通常对应段落、条款条项、列表项组或等价「可独立命中的短块」。生产注释：`2 = 段落`。 |

#### 0.3.1 粒度 0 — FullDocument 详解

- **必须存在**：每个成功 structure/construct 投影中，至少有一个 FullDocument 单元（S06 projection profile 强制 full-document block 语义）。  
- **向量候选**：Owner 冻结——**必须进入 vectorize 候选集**（original 非空 → 必有 original 向量意图；summary 在 dual-channel 完备后进入 summary 向量意图）。  
- **召回角色**：DocumentInflation 的目标层；直接命中 g=0 时 ContextTier=`document_root`。  
- **body 内容**：整文 original（可截断仅受 profile 预算约束，不得默认省略该 unit）。

#### 0.3.2 粒度 1 — 章节层举例

假设文档《A 市 2024 年度预算报告》：

| block 角色 | granularity | original.title 例 | original.body 范围 |
|---|---|---|---|
| 全文 | 0 | A 市 2024 年度预算报告 | 全文 |
| 第一章 | **1** | 一、总体情况 | 第一章全部段落拼接 |
| 第二章 | **1** | 二、收入预算 | 第二章全部段落拼接 |
| 第三章 | **1** | 三、支出预算 | 第三章全部段落拼接 |

章节层用于：「用户问收入总盘子」→ 易命中第二章 unit 的 summary/original，而无需先塞入全文。

#### 0.3.3 粒度 2 — 段落层举例

同一文档第二章内：

| block 角色 | granularity | original.title 例 | original.body 范围 |
|---|---|---|---|
| 章 | 1 | 二、收入预算 | 整章 |
| 段/条 | **2** | （二）税收收入 | 仅该小节/段落正文 |
| 段/条 | **2** | （三）非税收入 | 仅该小节/段落正文 |
| 段/条 | **2** | 表 2-1 说明段 | 表格说明段落 |

段落层用于：「用户问非税收入具体口径」→ 命中 g=2 细块，再 Inflation 可选附带 g=0 全文或依赖 g=1 章上下文（ContextTier 策略）。

#### 0.3.4 三层同文档并存规则

```text
同一文档 construct 后（默认）:
  ≥1 × (granularity=0, channel=original|summary)
  N₁ × (granularity=1, ...)
  N₂ × (granularity=2, ...)
每个 (unit, channel) 在 body 非空时 → 一个 VectorizationUnit
```

- 三层 **共享同一 EmbeddingSpace（Layer A）**；粒度不是 namespace。  
- v1 **不要求** g>2；若 profile 产出更细层，须显式注册，否则 validation fail-loud。

### 0.4 Construct → Vectorize 交付门闩（Owner 冻结）

**仅当** 同时满足，才允许 enqueue / 消费 `vectorize_construct`：

1. `lsrag.construct` ProcessOutcome 表示 **成功**（S07：`disposition=full_valid`）；  
2. per-type **current** 已 CAS：`construction_document` + `dual_channel_projection`（+ validation 面）；  
3. DualChannelProjection 满足 **整包 dual-channel 完备**（S07-T028：每个 non-empty original 位有 grounded summary）；  
4. 粒度默认集合中 **含 FullDocument（0）** 且其 original 可进入候选；  
5. outbox payload 仅 **exact construct generation refs + digests**（无全文）。

**禁止**：

- structurize 成功后直接 vectorize（跳过 construct）；  
- 半包 dual-channel、缺 g=0、缺 summary 完备仍投递 vectorize；  
- 以 pending 队列表行冒充「合法原料」。

### 0.5 向量化失败：只引用既有流程真相（禁止 D05 自建）

> **D05 不定义** retry 次数、backoff、lease、Outcome 字段。下列全部 **引用** 既有真相层。

| 关切 | 权威真相 | D05 强制消费方式 |
|---|---|---|
| 自动 retry / `max_retries` 止血 | **D01** `D01-T018/T027/T033`；**S03** `S03-T031`、E07 Outcome、`retry_count`/`max_retries` | vectorize Process 失败 → typed ProcessOutcome + `retryability`；由 **S03** 推进 `retry_wait→ready` 或 failed |
| 同一 process_uuid 重试 | D01-A09/A12；S03 Process 账本 | 不得因失败新建平行 Process 身份冒充同一步 |
| 向上报告 / 归约 | D01 Execution/Task 汇总；S03 route；S02 Task 投影 | max-retries 耗尽 → Process **显性 failed** → Execution 可归约；**禁止**卡死 waiting 抹账 |
| 模型 transport 内环 | **S11** transport 退避 **不计入** Process `retry_count` | embed 429 内环耗尽后，才作为一次 Process 失败证据交给 S03 |
| 背压 | S11 `INFERENCE_BACKPRESSURE` | Outcome `retryability=retryable`；S03 调度 |
| construct 失败 | **S07** 整包失败不 CAS + S03 max-retries | 无 vectorize 原料则 **不得** 进入 vectorize |

**vectorize 失败语义（产品层一句话，机制归 S03）**：  
向量化是叶 Process；失败不得静默丢意图；是否再试、何时终态 failed、如何上卷 Task，**全部由 S03/D01 状态机与 max_retries 决定**。

### 0.6 生产三 Prompt 身份冻结（`promptA` / `promptB` / `promptC`）

> **Owner 强制（v0.4）**：凡进入「可检索知识生产主链」的模型指令，必须先归入下列 **三产品身份** 之一并完成命名；  
> **Clean 与 Structurizer / Summarizer 同属生产环节**，不得把 Clean Prompt 排除在生产链标定之外。  
> 查询侧 rewrite/rerank 等 **不是** promptA/B/C。

#### 0.6.1 命名与真值模型（冻结）

```text
prompt_identity = prompt{A|B|C} . <variant> . <version>

例:
  promptA.default.v1
  promptA.web.v1
  promptA.document.v1
  promptB.default.v1
  promptC.default.v1
```

| 字段 | 含义 |
|---|---|
| `promptA` / `promptB` / `promptC` | **产品角色身份**（闭集；见 §0.6.2） |
| `variant` | 同角色下的变体（源类型/领域/策略分支），如 `default` / `web` / `document` / `vision` |
| `version` | 变体正文代次（`v1`/`v2`/…）；**同 version 正文 digest 必须稳定** |
| **正文载体** | **仅** `data/prompts/**` git 树（D03 `T-O-146`） |
| **DB 指针** | `{ prompt_identity, path?, content_hash }` — **只存 hash/指针，不存第二份可编辑正文**（D03 `T-O-155`） |
| **运行校验** | 加载时 `H(file bytes) == content_hash`，否则 **fail-fast**（禁 latest、禁静默换 key） |
| **绑定点** | 各叶 ProcessCommand / clean profile 的 `prompt_ref`；进入 **`command_input_digest` 冻结**（S03/S05/S06/S07） |

**逻辑类型（contracts / S14）**：

```text
PromptRefV1 = {
  identity: "promptA.default.v1",   // prompt{A|B|C}.variant.version
  content_hash: "sha256:…",         // DB 与 git 真值
  path?: "data/prompts/intake/clean/default.v1.md"
}
```

#### 0.6.2 三身份语义（冻结）

| 身份 | 规范名 | 生产环节 | 语义（必须做到） | 明确不做 |
|---|---|---|---|---|
| **`promptA`** | **CleanPrompt** | **清洗**（S05 clean.*） | 把源证据（HTML/文档页/API 载荷/图像页等）变成 **可结构的 clean 正文/elements**；保真、去噪、抽取核心文本；输出进入 clean IntakeArtifact | 不做多粒度 structure；不产权威 summary；不写向量；不发明 filter SSOT |
| **`promptB`** | **StructurePrompt** | **结构化**（`lsrag.structurize`） | 在 clean 之上引导/约束产出 **粒度 0/1/2** 的 original 分层（+ StructureSchema/response schema）；`llm_summary` 槽可空 | 不清洗源 HTML；不填 dual-channel summary 完备；不改 clean 权威 |
| **`promptC`** | **SummaryPrompt** | **摘要/构造**（`lsrag.construct` 内 Summarizer） | **整包一次**（或整包 plan）为应有 unit 填 **grounded SummaryChannel**；服务双通道完备 | 不改写 OriginalChannel；不跳过 g=0；不发明 S04 filter 权威键 |

**产品别名（可互换引用，身份码优先）**：

| 身份码 | 别名 | 旧 D05 用词 |
|---|---|---|
| promptA | CleanPrompt | （v0.3 缺失 → **v0.4 补入生产链**） |
| promptB | StructurePrompt | StructurePrompt |
| promptC | SummaryPrompt / SummarizerPrompt | SummaryPrompt |

#### 0.6.3 在 MKB 业务流程中的锚定（冻结）

```text
                    promptA                    promptB                    promptC
                       │                          │                          │
                       ▼                          ▼                          ▼
Source evidence ──► [S05 clean.*] ──► clean ──► [lsrag.structurize] ──► structure/projection
                                                              │
                                                              ▼
                                                    [lsrag.construct]
                                                      Summarizer 使用 promptC
                                                              │
                                                              ▼
                                                    dual-channel full_valid
                                                              │
                                                              ▼
                                                         vectorize …
```

| 锚定项 | promptA | promptB | promptC |
|---|---|---|---|
| **Workflow phase** | `cleaning`（及 clean 相关） | `structurizing` | `constructing` |
| **Process capability** | S05 exact `clean.*` keys | `lsrag.structurize` | `lsrag.construct` |
| **Command 字段** | clean profile / ProcessCommand `prompt_ref` → promptA.* | StructurizeCommand `prompt_ref` → promptB.* | ConstructCommand `summary_prompt_ref` → promptC.* |
| **调用点（实现）** | `src/services` clean handler → `runtime.inference` + promptA 正文 | S06 handler → structured_generate + promptB | S07 Summarizer → structured/text_generate + promptC |
| **成功门闩** | clean candidate/admission 规则（S05） | structure full-valid current（S06） | dual-channel full_valid + §0.4 gate（S07） |
| **失败** | S03 max_retries / Outcome（**不**在 D05 另建） | 同左 | 同左 |
| **metadata_refresh** | 通常 **不**重跑 promptA/B | 可跳过 structurize | `reuse_summaries=true` 时可 **显式空** promptC（S07）；否则仍绑 promptC |
| **git 路径约定** | `data/prompts/intake/clean/<variant>.<version>.*` | `data/prompts/lsrag/structure/<variant>.<version>.*` | `data/prompts/lsrag/construct/<variant>.<version>.*` |
| **DB** | `mkb_prompt_hash_pointers`（或 S14 表）行：identity + content_hash | 同左 | 同左 |

#### 0.6.4 默认 variant 登记（v1 bootstrap · 冻结身份，正文可迭代）

| identity（示例） | 角色 | 对应生产 ReferenceAnchor（非 MKB key） |
|---|---|---|
| `promptA.web.v1` | 网页清洗 | `WEB_CONTENT_CLEANUP_V1` → KV `CLEANER:WEBTS:GEMINICLEAN:V1`（`cleaner_web.ts`） |
| `promptA.document.v1` | 文档抽取 | `DOCUMENT_CONTENT_EXTRACTION_V1` → KV `CLEANER:DOCTS:GEMINIDOCUMENT:V1`（`cleaner_doc.ts`） |
| `promptA.default.v1` | 通用 clean 默认（实现可选映射到 web/document） | — |
| `promptB.default.v1` | 通用结构化 | `RAG_STRUCTURIZER_V1_GENERAL`（`structurizer.ts`） |
| `promptC.default.v1` | 通用整包摘要 | `RAG:CONSTRUCTOR:GEMINI_SUMMARY:V2`（`constructor.ts`） |

> legacy KV key **仅 ReferenceAnchor**；MKB **不得**以 KV 字符串为 SSOT。迁移时：git 正文 + `content_hash` + identity `promptA|B|C.*`。

#### 0.6.5 与 schema / 双通道 / 粒度的协作

```text
promptA  →  clean bytes/elements
promptB + StructureSchema (+ response schema)  →  g=0/1/2 Original 骨架
promptC + Construction dual-channel rules       →  Summary 通道完备
ContentFullRecipe（确定性，非 Prompt）         →  embed 输入文本
```

- **多粒度的主工具是 promptB**（+ schema），不是 promptA/C。  
- **双通道 Summary 侧主工具是 promptC**。  
- **Original 保真**依赖 promptA 输出质量 + promptB 不改写 + S06 kernel。

#### 0.6.6 强制与禁止

**强制**：

1. 主链 Clean / Structurize / full_construct 必须解析到 **promptA / promptB / promptC** 之一的 `PromptRefV1`；  
2. hash 校验失败 = 配置/依赖失败（readiness 或 Process non_retryable/依赖类错误，按 S03/S05 错误轴）；  
3. S14 registry 登记 identity→path→hash；S05/S06/S07 只引 ref。

**禁止**：

1. 无名 Prompt 字符串散落 services；  
2. 把 Clean 排除在「生产 Prompt」之外；  
3. 用 promptC 改 original，或用 promptB 做 HTML 清洗；  
4. DB 存第二份可独立编辑的 Prompt 正文；  
5. vectorize 冒充第四生产 Prompt 身份挤进 A/B/C。

### 0.7 债务 / 风险 → MKB 方案（摘要）

完整表见 v0.2 考古；关键项：

| ID | 债务 | MKB 方案 |
|---|---|---|
| D-01 | vec_process 三职 | artifact + outbox + vector_records |
| D-02 | R2/callback 成功 | proof + CAS + PublicationProof |
| D-03 | 裸坐标跨代 | GenerationScopedCoordinate |
| D-06 | step-name 跳步 | ConstructMode typed |
| D-07 | filter 写读不一致 | Layer B 统一 team+facets |
| D-08 | traceback 静默降级 | TracebackStatus 可观测（默认 degraded） |
| D-14 | 空 summary 仍成功 | 整包 dual-channel 完备 |
| D-Prompt | Prompt 仅在 KV、无命名、Clean 未进生产链标定 | **§0.6 promptA/B/C** + D03 git+hash |

---

## 1. Intake 流程 · Artifact 地图 · D01/D02 映射

### 1.1 流程图

```text
[S04/S05 Intake]
  admit → clean Artifact @ Revision
  StateFamily: Item / CandidateSet / Gate
  phase: cleaning | awaiting_human_review | …
        │
        ▼
[S03 Execution — 单文档]
  phase_key: structurizing → constructing → vectorizing_indexing
             → validating_publication
        │
        ├─ Process lsrag.structurize  → structure_* current
        ├─ Process lsrag.construct    → construction_* current + outbox
        │         ▲ 合法原料门闩（§0.4）
        ├─ Process vectorize*         → mkb_vector_records
        │         ▲ 失败 → S03 max_retries（§0.5）
        └─ Process index.validate_publication → PublicationProof
```

scatter：每 child Execution 独立全链。

### 1.2 Artifact 种类与生产位

| 层 | 种类 | 生产 Process | 备注 |
|---|---|---|---|
| Intake | clean IntakeArtifact | S05→S04（**promptA**） | structurize 输入 |

| S06 | structure_document, retrieval_block_projection, report | structurize（**promptB**） | **无权威 summary**；含 g=0/1/2 投影单元 |
| S07 | construction_document, dual_channel_projection | construct（**promptC** Summarizer） | **双通道完备**；ContentFull digests |
| Handoff | outbox `vectorize_construct` | construct 成功 TX | 非 SSOT |
| S08 | VectorRecord 行 | vectorize | channel × unit |
| S09 | PublicationProof | validate_publication | serving 资格 |

### 1.3 D01/D02 对应

| 概念 | 真相 | LS-RAG |
|---|---|---|
| 六 StateFamily | D02 | **不是** structurize/construct 阶段 |
| phase_key | S03/D01 | 业务焦点坐标 |
| Process max_retries | D01/S03 | vectorize/construct/structurize 共用机制 |
| Generation current | S06/S07 typed fact | 非 StateFamily |
| Task success | D01 | 需 publication proof，非仅有向量 |

---

## 2. Recall 流程 · 双通道增强 · 多粒度上下文

### 2.1 召回流程

```text
Query → Layer B filter → embed (Layer A)
  → ANN topK → hydrate active VectorRecords
  → TRACEBACK if summary hit → PayloadContent=original
  → INFLATION optional → attach g=0 original (budget)
  → Rerank? → pack ContextTier → RetrievalResult[]
```

### 2.2 双通道如何增强召回（根本机制）

| 通道 | 索引作用 | 命中后 |
|---|---|---|
| **Summary** | 短、语义密，对齐改写 query | HitContent=summary；Traceback → Payload=original |
| **Original** | 细节/专名直接命中 | Hit=Payload=original |

**默认双通道向量化** ⇒ 同一坐标两条（或一条若对侧空——但 construct 成功应避免应有侧空）。

### 2.3 粒度 0/1/2 与 ContextTier

| 命中 | 默认 ContextTier | 可选增强 |
|---|---|---|
| g=2 段 | `focus_fragment` | Inflation → g=0 `document_root` |
| g=1 章 | `focus_fragment`（中等） | Inflation → g=0 |
| g=0 全文 | `document_root` | 过预算则 drop/可观测截断（S10 profile） |

前端可同时拿到：**细块原文（focus）+ 全文层（root）**，对应生产 inflation 策略。

### 2.4 RetrievalResult 最小字段

`score`, `hit_channel`, `hit_content|_ref`, `payload_content|_ref`, `coordinate`, `granularity`（0/1/2）, `generation_refs`, `traceback_status`, `context_tier`, `filters_echo`。

### 2.5 失败与上报（再声明引用）

召回路径错误分类归 S10/S11；**生产路径** vectorize/structurize/construct 失败归 **S03 ProcessOutcome + max_retries + D01 上卷**。D05 不重复定义。

---

## 3. 术语（glossary 引用）

定义 SSOT：`spec-glossary.md` v2.3 §4。

强制词：`LS-RAG`, `DualChannel`, `Granularity0/1/2`（FullDocument/Section/Paragraph）, `GenerationScopedCoordinate`, `StructurePrompt`, `SummaryPrompt`, `VectorizationUnit`, `ContentFull`, `Traceback`, `DocumentInflation`, `HitContent`, `PayloadContent`, `ContextTier`, `PublicationProof`, …

禁用：`smind_vec_process` 作 SSOT、向量表 content_full 列、裸三元组跨代、R2 成功。

---

## 4. D04 映射确认

| 产品 | D04 |
|---|---|
| 双通道 | `mkb_vector_records.channel` |
| 粒度 unit | `block_or_unit_id` + 应用层 granularity 元数据（payload_extra 或晋升列；**产品语义 0/1/2**） |
| FullDocument 必索引 | S08 验收：存在 g=0 original 向量意图/行（在 construct 完备前提下） |
| 交付门闩 | outbox 仅在 construct CAS 后 |
| 禁 vec_process / content_full 列 | 已确认 |
| Traceback | 同 generation+unit，不同 channel |

> **列建议（不改 D04 闭集也可）**：若 `block_or_unit_id` 不编码粒度，S08 应在 record `payload_extra` 或未来 D04 小迁移中晋升 `granularity SMALLINT`——**产品要求在 D05；物理晋升走 D04 change-request**。

---

## 5. Typed Schema 详例 ↔ D03 contracts

### 5.1 落点

```text
src/contracts/lsrag/shared/     # coordinate, channel, granularity enum
src/contracts/lsrag/structure/  # structurize command/outcome, structure shapes
src/contracts/lsrag/construct/  # construct command/outcome, dual-channel shapes
src/contracts/vector/           # vectorize intent, vector record id, retrieve result
src/contracts/inference/        # embed I/O
data/prompts/lsrag/structure/** # StructurePrompt 正文
data/prompts/lsrag/construct/** # SummaryPrompt 正文
```

### 5.2 双通道 + 三粒度 — Typed 实例（详例）

> 以下为 **逻辑 JSON 形状示例**（contracts 校验后的对象）；生产 wire 禁止 path/R2。

#### 5.2.1 `GenerationScopedCoordinateV1`

```json
{
  "team_uuid": "019f…",
  "execution_uuid": "019f…",
  "structure_generation_uuid": "019f…",
  "construct_generation_uuid": "019f…",
  "unit_id": "u_sec_02_p03",
  "granularity": 2,
  "structure_node_ref": "node_…",
  "projection_block_ref": "blk_…"
}
```

#### 5.2.2 `ConstructionUnitV1`（单单元双通道）

```json
{
  "coordinate": { "/* GenerationScopedCoordinateV1 */": "…" },
  "granularity": 1,
  "original": {
    "channel": "original",
    "title": "二、收入预算",
    "body_handle": "mkbobj:v1:…:…",
    "body_digest": "sha256:…",
    "char_length": 4200
  },
  "summary": {
    "channel": "summary",
    "title": "收入预算摘要",
    "body_handle": "mkbobj:v1:…:…",
    "body_digest": "sha256:…",
    "grounds_coordinate": { "unit_id": "u_sec_02" },
    "disposition": "present_grounded"
  },
  "content_full": {
    "recipe_version": "mkb.content_full.v1",
    "original_digest": "sha256:…",
    "summary_digest": "sha256:…"
  }
}
```

#### 5.2.3 `DualChannelProjectionV1`（整包 · 含 0/1/2）

```json
{
  "schema_ref": { "key": "mkb.construction_document", "version": "1", "digest": "sha256:…" },
  "structure_ref": { "generation_uuid": "…", "digest": "sha256:…" },
  "units": [
    {
      "unit_id": "u_doc",
      "granularity": 0,
      "original": { "title": "A市2024预算报告", "body_digest": "sha256:full…" },
      "summary": { "body_digest": "sha256:full_sum…", "disposition": "present_grounded" }
    },
    {
      "unit_id": "u_sec_01",
      "granularity": 1,
      "original": { "title": "一、总体情况", "body_digest": "sha256:…" },
      "summary": { "body_digest": "sha256:…", "disposition": "present_grounded" }
    },
    {
      "unit_id": "u_sec_02",
      "granularity": 1,
      "original": { "title": "二、收入预算", "body_digest": "sha256:…" },
      "summary": { "body_digest": "sha256:…", "disposition": "present_grounded" }
    },
    {
      "unit_id": "u_sec_02_p01",
      "granularity": 2,
      "original": { "title": "（二）税收收入", "body_digest": "sha256:…" },
      "summary": { "body_digest": "sha256:…", "disposition": "present_grounded" }
    },
    {
      "unit_id": "u_sec_02_p02",
      "granularity": 2,
      "original": { "title": "（三）非税收入", "body_digest": "sha256:…" },
      "summary": { "body_digest": "sha256:…", "disposition": "present_grounded" }
    }
  ],
  "completeness": {
    "units_total": 5,
    "original_nonempty": 5,
    "summary_grounded": 5,
    "full_document_present": true,
    "granularity_set": [0, 1, 2]
  }
}
```

**校验规则（contracts + S07）摘录**：

- `full_document_present == true`  
- `granularity_set` ⊇ `{0,1,2}`（若文档过短可无 g=1/2，但 **不得无 g=0**；无中层时须显式 `not_applicable` 审计——**短文例外**须 profile 声明，默认期望三层）  
- 每个 `original` 非空 unit 的 `summary.disposition == present_grounded`  
- 禁止 `channel` 缺失的向量意图

#### 5.2.4 `VectorizationUnitV1` 扇出（由上例生成）

```text
for unit in units:
  for channel in {original, summary}:
    if body non-empty:
      emit {
        team_uuid, namespace_ref,
        generation_artifact_uuid: dual_channel_projection_gen,
        block_or_unit_id: unit.unit_id,
        granularity: unit.granularity,   # 0|1|2
        channel,
        content_digest: content_full[channel].digest,
        layer_b: { intake_item, revision, facets… }
      }
```

**本例** ⇒ 5 units × 2 channels = **10** 条向量候选；其中 **g=0 两条**（original+summary）**必须存在**。

#### 5.2.5 `ConstructCommandV1` / `ConstructOutcomeV1`（摘录）

```json
// Command
{
  "mode": "full_construct",
  "structure_generation_ref": { "uuid": "…", "digest": "…" },
  "projection_generation_ref": { "uuid": "…", "digest": "…" },
  "construction_schema_ref": { "key": "mkb.construction_document", "version": "1", "digest": "…" },
  "summary_prompt_ref": { "key": "lsrag.construct.summary.v1", "content_hash": "…" },
  "structure_prompt_ref_echo": { "key": "lsrag.structure.v1", "content_hash": "…" },
  "command_input_digest": "sha256:…"
}

// Outcome succeeded
{
  "disposition": "full_valid",
  "construction_document_ref": { "uuid": "…", "digest": "…" },
  "dual_channel_projection_ref": { "uuid": "…", "digest": "…" },
  "completeness": { "full_document_present": true, "granularity_set": [0, 1, 2] },
  "outbox_intent_ref": { "kind": "vectorize_construct", "id": "…" }
}
```

#### 5.2.6 `RetrieveResultItemV1`（双通道命中例）

```json
{
  "score": 0.81,
  "hit_channel": "summary",
  "hit_content_ref": { "digest": "sha256:sum…" },
  "payload_content_ref": { "digest": "sha256:orig…" },
  "traceback_status": "resolved",
  "granularity": 2,
  "context_tier": "focus_fragment",
  "coordinate": { "unit_id": "u_sec_02_p02", "construct_generation_uuid": "…" },
  "inflated_document": {
    "context_tier": "document_root",
    "granularity": 0,
    "payload_content_ref": { "digest": "sha256:full…" }
  }
}
```

#### 5.2.7 promptB（Structure）绑定的响应 schema 要点

生产 JSON Schema 对模型声明（锚：`getStructuredJsonSchemaAsObject`）：

- `granularity`：**0 = 全文，1 = 章节，依此类推**  
- 每块必有 `original_content` + `llm_summary` 对象（结构阶段 summary 内字段可为 null）  
- `layered_content.minItems ≥ 1`（至少全文块）

MKB contracts + **promptB** 正文须等价约束 **0/1/2 三层**（短文 profile 例外另册）。

### 5.3 SMCP → contracts

| SMCP | MKB |
|---|---|
| STEP_START + r2_key | ProcessCommand + handles |
| STEP_CALLBACK | ProcessOutcome（S03 形状） |
| designated_prompt | `PromptRef` → promptA/B/C identity + content_hash |
| case_mode meta | ConstructMode |

---

## 6. Owner 冻结台账（= `T-O-202..210`）

| 项 | Truth-ID | 状态 |
|---|---|---|
| D05 高等级权威 / D>S | T-O-202 | **frozen** |
| 双通道根本 | T-O-203 | **frozen** |
| 粒度 0/1/2 | T-O-204 | **frozen** |
| FullDocument 必向量候选 | T-O-205 | **frozen** |
| construct→vectorize 门闩 | T-O-206 | **frozen** |
| 失败仅引 D01/S03 | T-O-207 | **frozen** |
| promptA/B/C + hash | T-O-208 | **frozen** |
| 召回 Traceback/Inflation/ContextTier | T-O-209 | **frozen** |
| 生产链阶段分账 | T-O-210 | **frozen** |

---

## 7. 下游强制清单

| 下游 | 必须 |
|---|---|
| S05 | **promptA** 绑定 clean.*；variant 覆盖 web/document/vision… |
| S06 | **promptB** + schema 产 g=0/1/2；强制 full-document；summary 不进 kernel |
| S07 | **promptC** 填 Summary；双通道完备；g=0；合法后 outbox vectorize |
| S08 | 扇出双通道；g=0 必候选；失败走 S03 Outcome/max_retries；**非** promptA/B/C |
| S09 | PublicationProof |
| S10 | Traceback + ContextTier；Result 分账 |
| S14 | 登记 promptA/B/C identity→path→hash |
| S03 | 唯一 max_retries / 上卷权威；Command digest 含 prompt_ref |

---

## 8. Domain verdict

**`FROZEN / owner-gated / D05-v1.0`**：`T-O-202..210` 已锁定；S05–S10/S14 必须服从并回填；全系统 truth layer 仍待其余域闭合后统一 frozen。

开放（不阻塞本冻结）：S08 exact capability key 拆分；`granularity` 是否晋升 D04 列；S14 物理 registry 实现。

---

## 9. 修订历史

| 版本 | 日期 | 状态 | 说明 |
|---|---|---|---|
| v0.1–v0.4 | 2026-08-12 | drafts → product-core | 考古、六节骨架、Owner 裁决、promptA/B/C |
| **D05-v1.0** | **2026-08-12** | **`frozen / owner-gated`** | 正式冻结 `T-O-202..210`；glossary/index 回填；S 系校准入口 |
