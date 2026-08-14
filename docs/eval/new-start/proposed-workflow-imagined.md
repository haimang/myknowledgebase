# Proposed workflow (imagined)

> **项目**：`myknowledgebase`（MKB）
>
> **文档性质**：`eval / new-start / proposed`（执行意见，**不是** frozen domain-truth）
>
> **文档状态**：`draft / owner-review`
>
> **日期**：`2026-08-14`
>
> **作者**：`Grok`
>
> **姊妹文档**：
> - `non-interactive-agentic-pipeline.md`（`claude -p` 三通道）
> - `agent-in-the-loop-repair.md`（Grok/agy 显式修 JSON）
>
> **权威输入**：
> - 已冻围栏：S03–S08、D05 `T-O-202..210`、D08 四域
> - 当时生产：`context/legacy-family/smind-skill-{clean-universal,rag-structurizer,rag-constructor}`
> - 当时正文：`context/legacy-prompt/prompt{A,B,C}.*`
> - 现实现：`src/workflows/lsrag_definition.py`、`src/runtime/intake/*`、`src/services/lsrag_compiler.py`、`data/prompts/prompt-*-v1.md`
> - 本会话业主约定：A/B/C = system instruction；`-p` = 物料；schema 卡 B；失败显式抛错不挡 sibling；人审不作恢复；shape 失败才请修理工
>
> **本文不擅自 reopen** 已冻 `T-O-*`。§7 列出需要 owner 点头才能改的张力。

---

## 0. 执行意见（先读这节）

**总评：围栏可留，生产语义必须换运输、换权威树、换 prompt 正文。**

v1 已经把 Task → acquire → clean → accept → structurize → construct → vectorize → publication 立成可跑的图。缺的不是又一套状态机，而是：

1. 当时真正干活的 **prompt 正文** 没有进 S14。
2. 当时真正交卷的 **`layered_content` schema** 没有成为 B/C 的 `--json-schema`。
3. 代码里 **B 的模型输出不进 current**：`_structurize` 就算 `live_inference` 也只记账，权威树永远是 `LsragContractCompiler` 的「一棵假树 + 按句切 g=2」。
4. 新工人（`claude -p` / `grok -p`）测通了接口，还没接到 handler。

建议按这个顺序做，不要并行拆围栏：

| 刀 | 做什么 | 不做 |
|---|---|---|
| **P0** | 把 `layered_content` 冻成 git schema；八份 legacy-prompt 迁入 `data/prompts/` 并登记 identity+hash | 不改 S03/S04 表 |
| **P1** | `lsrag.structurize` 改为 `claude -p` + promptB + schema；kernel **校验并投影** 模型 JSON，不再自己编树 | 不在 structurize 里暗换模型 |
| **P2** | LLM clean / 整包 C 同样走 CLI；确定性 clean 与 API parser 不动 | 不把 acquire 交给 Claude |
| **P3** | shape 失败走独立 `lsrag.structure_repair`（`grok -p` + `promptB.repair`） | kernel/保真失败不修 |
| **P4** | 领域变体（法律 markdown、房产 g=0）用 S14 identity 选 prompt，而不是 `designated_prompt` 字符串 | 默认路径不开人审 |

**一句话：** MiniMax 用当时的 A/B/C 正文出 `layered_content`；MKB 只做获取、接受、校验、投影、门闩、向量；坏形状请 Grok 修；坏一份不挡别份。

---

## 1. 当前 v1 流程（代码事实）

### 1.1 图

单条主图在 `src/workflows/lsrag_definition.py`。另有按 source/strategy 复制的 HTTP/PDF/OCR/Vision 变体，以及 `intake.ingest.scatter.registered_api.lsrag.v1` + child。

```text
start
  ├─ index.rebuild ──► succeeded          （lifecycle 捷径）
  └─ acquire
        ├─ deactivate/reactivate/delete/metadata_no_change ──► succeeded
        └─ decode → clean → seal → preflight → accept_snapshot
              ├─ admission_rejected ──► failed
              ├─ human_review_required ──► human_review_gate ──► structurize
              ├─ metadata_refresh ──► construct
              └─ auto_admitted ──► structurize → construct → vectorize
                                    → validate_publication → succeeded
```

handler 分发在 `src/runtime/intake/core.py` `_material_for`：acquire / decode / 八条 `clean.*` / `clean.map.registered_api` / seal / preflight / accept / structurize / construct / vectorize / publish / rebuild。

### 1.2 每步实际干什么

| 步骤 | process_key | 代码 | 现逻辑 |
|---|---|---|---|
| acquire | `intake.acquire.*` | `acquisition_ingest.py` | 读 inline/local/http/API，写 AcquisitionEvidence。**不跑 prompt** |
| decode | `intake.decode.*` | 同族 | declared/detected media，解码文本或保留 bytes |
| clean | `clean.extract.*` / `clean.map.registered_api` | `clean_preflight.py` → `intake.dispatch_clean` | 确定性 / web sanitize / PDF 分流 / API parser。仅 `llm_required` strategy 读 `promptA.default.v1` 哈希 |
| seal / preflight | `intake.collection.seal` / `intake.preflight_validate` | 同文件 | 封 CandidateSet；空 clean → `rejected`；`require_human_review` → gate |
| accept | `intake.accept_snapshot` | `acceptance_snapshot.py` | **唯一**写出 Snapshot/Item/Revision 的地方 |
| human_review | control `human_review_gate` | `runtime_materialize.py` | Execution `waiting(human_review)`。业主已判不必要，**图上还在** |
| structurize | `lsrag.structurize` | `generation_construct.py` | 见 §1.3 |
| construct | `lsrag.construct` | 同文件 | 见 §1.3 |
| vectorize / publish | `lsrag.vectorize` / `index.validate_publication` | `vectorize.py` / `vector_publish_commit.py` | 双通道行 + PublicationProof |

### 1.3 当前 B/C 的真相对（必须写进意见）

**Structurize（B）——模型不是权威。**

```311:330:src/runtime/intake/generation_construct.py
            if self._live_inference:
                generation_invocation = await self._live_structured_generate(
                    ...
                    prompt_key="promptB.default",
                    schema_key="lsrag.structure.default",
                )
            compiler = LsragContractCompiler()
            structure, projection = compiler.structurize(clean_text=clean, ...)
```

`live_structured_generate` 的 JSON **不参与** `compiler.structurize`。compiler 做的是：

- 一棵树：`root(document)` + 一片 `paragraph`，span = 全文；
- 投影：`g0:document` = 全文，`g1:document` = **同一全文**，`g2:*` = 正则按句切。

也就是说：D05 要的「语义分层」在代码里被实现成了「全文复制两遍 + 断句」。promptB 正文两句占位，schema 登记是 `{"schema_key":"lsrag.structure.default",...}` 存根，不是 Zod `layered_content`。

**Construct（C）——模型会被吃进去。**

`_live_summaries` 按 **projection block**（含所有 g2 句子）逐条 `text_generate` + `promptC.default`。`compiler.construct(..., summaries_by_block_id=summaries)` 真用这些字符串。离线则 `deterministic_summaries`。

所以今天是：**C 在给句子摘要，B 没有语义切块。** 和当时「B 切块、C 整包填 `llm_summary`」正好反了。

### 1.4 当前 prompt 资产

| identity | 路径 | 正文 |
|---|---|---|
| `promptA.default.v1` | `data/prompts/prompt-a-clean-v1.md` | 两句：规范化、不加事实 |
| `promptB.default.v1` | `data/prompts/prompt-b-structure-v1.md` | 两句：忠实结构、summary 不是 kernel |
| `promptC.default.v1` | `data/prompts/prompt-c-summary-v1.md` | 两句：摘要通道、不改原文 |

登记在 `src/services/registry.py` `DEFAULT_PROMPTS`。LLM strategy 绑 A（`src/contracts/intake/strategies.py`）。**没有** legal / realestate / repair / document-extract 变体。

---

## 2. 映射回当时的 PROMPT 与 Worker

### 2.1 当时主链（ReferenceAnchor）

```text
clean-universal / dedicated-apis
    │  WEB_CONTENT_CLEANUP_V1 | DOCUMENT_CONTENT_EXTRACTION_V1 | 无 LLM parser
    ▼  纯文本
rag-structurizer
    │  designated_prompt || RAG_STRUCTURIZER_V1_GENERAL
    │  user = 整份 plainText
    ▼  context_meta + layered_content[]（llm_summary 占位）
rag-constructor
    ├─ summarizer.ts     ← 当时的「rag-summarizer」
    │    RAG:CONSTRUCTOR:GEMINI_SUMMARY:V2
    │    user = 上游 JSON（多块时剥 g=0 body）
    ├─ meta_fuser
    └─ recorder          original+summary 两条向量意图
    ▼
rag-vectorizer
```

没有第四个 summarizer skill。摘要是 constructor 的一职。

### 2.2 八份正文 → 当时 → 现在 → 新流程

| 当时正文 | 当时工人 | v1 现在 | 新流程应落在 |
|---|---|---|---|
| `promptA.clean.v1.md` | `cleaner_web` + `WEB_CONTENT_CLEANUP_V1` | stub `promptA.default`；仅 llm strategy 读 hash | `claude -p --system-prompt-file promptA`，`-p`=HTML/解码正文 |
| （八份没有）`DOCUMENT_CONTENT_EXTRACTION_V1` | `cleaner_doc` / browserPDF / vision | `doc.*` / `pdf.*` strategy 有，prompt 无正文 | 补 `promptA.document.v1` |
| dedicated-apis 三 provider | 纯 parser | `clean.map.registered_api` **已对齐** | **保持**，不经 Claude |
| `promptB.markdown.legal.{general,clause,qna,case}` | 法律线 **B 的第一刀**（markdown 中间态）；不在 structurizer.ts 默认契约里 | **无处可挂** | P4：可选 `transcribe` 步，或把切法写进 `promptB.legal.*` 直接出 JSON |
| `promptB.json.structurizer.md` | 旧方言：`semantic_block` + B 内写 `semantic_understanding`；仅 g=0/1；g=0 原文空 | 无 | **退役**。切法并入 `promptB.legal.v1`，摘要槽留给 C |
| `promptB.json.realestate.md` | 现行 Zod 方言；仅 g=0；B 内二次去噪 | 无变体 | `promptB.realestate.v1`；去噪能在 A 做的不要留在 B |
| `promptC.constructor.md` | `summarizer.ts` 整包回填 `llm_summary` | stub；按 g2 句子逐条 generate | `claude -p` + promptC，`-p`=B 的 JSON，同一份 schema |

### 2.3 当时契约 vs v1 契约

| | 当时 Zod（生产） | 旧法律 B | v1 compiler（现在权威） |
|---|---|---|---|
| 根 | `context_meta` + `layered_content[]` | `title/meta` + `semantic_block[]` | `StructureDocument.nodes` + `RetrievalBlockProjection` |
| 粒度 | 整数，注释说 0=全文 | 仅 0/1 | 强制集合 {0,1,2}；1 与 0 同文 |
| 原文 | `{title,body}` | `original_title` + 字符串 | span 回切 clean |
| 摘要 | `llm_summary` 由 C 填 | B 就写 `semantic_understanding` | C 按 block 字符串 map |
| 身份 | `block_id` 整数占位 | 同 | UUID + `g0:document` / `g2:0001` |

新流程的 `--json-schema` **应采用当时 Zod `layered_content`**（B 交卷、C 回填），不用 compiler 的节点树当模型输出。kernel 的职责从「编树」改成「对着 clean 做 coverage / digest / 双通道投影」。

---

## 3. 缺口分析

### 3.1 产品 / 契约

| ID | 缺口 | 严重度 | 说明 |
|---|---|---|---|
| G1 | prompt 正文未迁 | P0 | 八份在 `context/legacy-prompt`，运行时是 stub |
| G2 | 无生产 JSON Schema 文件 | P0 | registry 里 `lsrag.structure.default` 不是可校验 schema |
| G3 | 两套 JSON 方言未收口 | P0 | `semantic_block` vs `layered_content`；必须只留一套给 CLI |
| G4 | 法律 markdown 中间态无 Process | P1 | 四变体（含生成性 case）在 v1 图上消失 |
| G5 | 粒度闭集冲突 | P1 | 法律 0/1、房产 0、D05 默认 0/1/2、compiler 用句子冒充 2 |
| G6 | B 写摘要 vs C 写摘要 | P0 | 旧 structurizer 违反 D05；新流程必须拆开 |
| G7 | 领域变体无 identity | P1 | 当时 `designated_prompt`；现在只有 `*.default.v1` |
| G8 | 文档抽取 prompt 缺失 | P1 | D08 有 vision/pdf_llm，没有 `promptA.document` 正文 |

### 3.2 实现 / 运输

| ID | 缺口 | 严重度 | 代码锚 |
|---|---|---|---|
| G9 | B 模型输出丢弃 | **P0** | `generation_construct.py` `_structurize`：invocation 只入账，compiler 另编树 |
| G10 | B 没有语义切块 | **P0** | `lsrag_compiler.py` `_project_blocks`：g0=g1=全文，g2=句子 |
| G11 | C 跟句子走 | P0 | `_live_summaries` 对每个 g2 调一次；与当时整包 constructor 相反 |
| G12 | CLI 工人未接线 | P0 | 仍走 S11 `structured_generate` / `text_generate` |
| G13 | 无人值守修理工 | P1 | 无 `structure_repair`；只有 S03 retry |
| G14 | 人审仍在默认图 | P1 | `human_review` step + `require_human_review` |
| G15 | scatter 整单连坐 | P2 | child 全 `required`；修失败仍 `scatter-required-child-failed` |
| G16 | `agy` 无 system 旗标 | P2 | 第二修理工未就绪 |

### 3.3 已对齐、不要拆

- 四类 source kind、三轴 binding、D08 `dispatch_clean`。
- API 三 provider 纯函数 + FilterMeta 五维 + 双 digest。
- 只有 S04 accept 才写 Intake 身份。
- ConstructToVectorizeGate、publication proof。
- Prompt 正文 git + DB 只存 hash（纪律在，内容空）。
- sibling collect-all（不 fail-fast 杀邻居）。

---

## 4. 新流程分析

### 4.1 目标链（单文件）

```text
S05 acquire / decode
        │
        ├─ deterministic / API map ──► clean 正文     （不经 Claude）
        └─ llm / vision / ocr ──► claude -p + promptA
                                    -p = HTML 或链接（链接须先 acquire 或开最小取链工具）
        │
        ▼
S04 seal → preflight → accept          （失败 = 本文件 failed；不人审）
        │
        ▼
claude -p + promptB.<variant>
  --json-schema = layered_content.v1
  -p = accepted clean 正文
        │
        ▼
MKB kernel：schema + coverage + 不发明原文
        │
   ┌────┴────┐
   │ 全过    │ 仅 shape 失败
   ▼         ▼
   C     grok -p + promptB.repair
         同一 schema，-p = 坏 JSON + 验证报告
              │
         从零复验；预算 1（可选 +agy）
              │
         仍失败 / kernel 债 ──► 本文件 failed，sibling 继续
        │
        ▼
claude -p + promptC
  -p = 已通过的 layered JSON
  只填 llm_summary.* ；original 原样
        │
        ▼
kernel 挂双通道 + ConstructToVectorizeGate
        │
        ▼
vectorize → publication
```

### 4.2 三通道（不变）

| 通道 | A | B | B-repair | C |
|---|---|---|---|---|
| system | `promptA.*` | `promptB.<variant>` | `promptB.repair.v1` | `promptC.*` |
| `-p` | 源 HTML / 解码正文 | clean 正文 | 坏 JSON + 报告 | B 的 JSON |
| schema | 无（纯文本） | **layered_content.v1** | **同一份** | 同一份（只校验 summary 已填） |

### 4.3 kernel 新职（相对今天）

今天 kernel **生产** 树。明天 kernel **验收** 模型树：

1. `layered_content` 过 JSON Schema。
2. 至少一块 `granularity=0`。
3. g≥1 的 `original_content.body` 必须能在 clean 上锚定（子串或显式 span）；对不上 = kernel 失败，**不送修理工**。
4. g=0 的 `body` 若空：kernel **用 clean 全文回填**（确定性「原文隧道」，不是模型发明）。这收口当时加了又删的 block-0 注入，并满足「g=0 必入向量候选」。
5. 投影出 retrieval blocks：一块 layered block → 一个 unit，**不再按句切除非该 variant 声明要 g=2**。
6. C 之后：每个应有 unit 的 `llm_summary.body` 非空才 `full_valid`。

### 4.4 领域变体（P4，不挡 P1）

| variant | 粒度 | 备注 |
|---|---|---|
| `promptB.default.v1` | 0 + 1，鼓励 2 | 通用文章；从旧 structurizer + D05 折中 |
| `promptB.legal.v1` | 0 + 1，按目录聚块 | 合并四份 markdown 的切法，**直接出 JSON**，不再落 markdown 文件 |
| `promptB.legal.case.v1` | 0 + 固定两块（回顾/分析） | 「分析」是生成，标 `content_role=analysis`，不进 original 向量或单独通道；P4 再开 |
| `promptB.realestate.v1` | 仅 0 | listing；去噪尽量前移到 A |
| `promptB.repair.v1` | 同输入 | 只修形状 |

法律 markdown 四文件：P1 **不当独立 Process**。把面包屑 / QnA / 目录规则写进 `promptB.legal.v1`。若模型切不好，再加 `transcribe_markdown` 前置，而不是一上来恢复四段 Worker。

`promptB.json.structurizer.md` 的 `semantic_understanding` **禁止**进 B。摘要只走 C。

### 4.5 失败

与 `agent-in-the-loop-repair.md` 一致：

- 运输/空输出 → S03 retryable 或 failed（同 CLI，不换模型）。
- hash mismatch → 配置失败。
- shape/schema → repair（预算 1）。
- kernel/保真 → 立刻 failed。
- 不进 human gate。
- sibling 继续。root 是否部分成功 **P2 以后再改**；P1 保持「required child 失败则 root 失败，但先跑完再聚」。

### 4.6 与现图的叠法

**不改步骤顺序。** 改叶内部：

- `clean.extract.web_llm|pdf_llm|doc_llm|ocr|vision` → CLI + promptA（P2）。
- `lsrag.structurize` → CLI + promptB + kernel 验收（P1）。
- 新增可选 `lsrag.structure_repair`（P3），插在 structurize 与 construct 之间，仅 shape 失败进入。
- `lsrag.construct` → CLI + promptC 整包（P2）；不再对 g2 句子循环。
- `human_review`：生产默认 guard 永不命中（P1 就可关）；节点可留一版以免 historical revision 断。

---

## 5. 代码逻辑梳理（落地时动哪里）

### 5.1 保留

| 模块 | 为什么留 |
|---|---|
| `src/workflows/lsrag_definition.py` 拓扑 | 围栏对 |
| `intake/{api,web,pdf,doc}` + `dispatch_clean` | D08 SSOT；API/确定性不能换模型 |
| `acceptance_*.py` / S04 事务 | 接受身份不能散 |
| `runtime_scatter.py` collect-all | sibling 隔离已经有 |
| `vectorize.py` / publication | 门闩后不要动 |
| `registry.py` hash 指针机制 | 换正文，不换纪律 |

### 5.2 改

| 模块 | 改法 |
|---|---|
| `data/prompts/*` + `DEFAULT_PROMPTS` | 迁入 A/B/C 生产正文；加 legal/realestate/repair/document |
| 新 `data/schemas/lsrag.layered_content.v1.json` | B/C/`--json-schema` 的唯一形状 |
| `src/services/lsrag_compiler.py` | 增加 `adopt_layered_json(clean, layered) → StructureDocument+Projection`；旧 `structurize(clean_text)` 仅留作离线/测试 fixture，**退出生产 current** |
| `generation_construct.py` `_structurize` | spawn `claude -p`；读 `structured_output`；`adopt_layered_json`；失败分类 |
| 新 `structure_repair` handler | spawn `grok -p`；同一 schema；新 artifact；从零 `adopt` |
| `generation_construct.py` `_construct` / `_live_summaries` | 整包 JSON 一枪，按 `block_id` 填 summary；禁止按句循环 |
| `generation_live.py` | 抽 `ClaudeCliPort` / `GrokCliPort`；invocation 记二进制、session_id、usage |
| `strategies.py` | llm strategy 继续只绑 promptA；document 变体绑 `promptA.document` |
| workflow guards | 默认 `auto_admitted`；`require_human_review` 生产关 |

### 5.3 明确不要做

1. 不要在 `_structurize` 里「先 compiler 再把模型当装饰」。
2. 不要把 `StructureDocument` 节点树当成 `--json-schema`（模型填不了 span/digest）。
3. 不要恢复 KV `designated_prompt` 任意字符串。
4. 不要把 legal.case 的「案情分析」写进 original 通道。
5. 不要为 Claude/Grok 新建第四套 retry 账本。

---

## 6. 分阶段执行意见

### P0 — 资产（不接线也可做）

1. 冻结 `layered_content.v1` JSON Schema（从 structurizer Zod 抽出：`context_meta`、`layered_content[].block_id/granularity/original_content/llm_summary`）。
2. 将 `promptA.clean.v1.md`、整理后的 `promptB`（去 `semantic_understanding`、改输出为 layered）、`promptC.constructor.md` 写入 `data/prompts/`，更新 S14 hash。
3. 起草 `promptB.repair.v1`（只修形状）。
4. 契约测试：schema 金样（法律 0/1、房产仅 0、C 填满 summary）。

**完成定义：** `ruff` + 新 schema 单测绿；运行时仍走旧 compiler（行为不变）。

### P1 — B 换权威（主风险刀）

1. `ClaudeCliPort`：`--bare --system-prompt-file --output-format json --json-schema --tools ""`。
2. `_structurize`：CLI → `adopt_layered_json` → 现有 artifact/pointer/CAS。
3. 假 CLI 单测：argv 含 promptB 与 schema；kernel 拒绝发明原文；g=0 空 body 回填 clean。
4. 默认关闭 human_review guard。

**完成定义：** 一条 inline e2e（可 stub CLI）产出的 projection **不再**出现「g0 与 g1 全文相同 + g2 句子」。live 关时可用检具 JSON，禁止再调用旧 `compiler.structurize(clean_text)` 当生产。

### P2 — A 与 C

1. llm clean strategy：`claude -p` + promptA；确定性/API 不动。
2. construct：整包 promptC，一次 JSON；`summaries_by_block_id` 从 `llm_summary.body` 映射。
3. 真机烟测：短 HTML → A 纯文本 → B JSON → C summary → gate。

### P3 — 修理工

按 `agent-in-the-loop-repair.md` 加 `lsrag.structure_repair`。先 Grok。agy 等 system 注入口确认。

### P4 — 变体与法律线

`promptB.legal` / `promptB.realestate` 进 registry；Workflow binding 按 source profile 选 identity（已有 `BUILTIN_SOURCE_PROFILE_WORKFLOWS` 可挂）。case 分析通道单独开。

### P5 — 聚合（可选）

scatter child 允许 `optional` / 部分成功。与修理工无关，单独 owner 决定。

---

## 7. 与已冻 Truth 的张力（需 owner）

| 已冻 | 本提案 | 建议 |
|---|---|---|
| D05：B 默认粒度 {0,1,2} | 法律/房产 profile 可少于 3 层 | **窄 reopen**：默认 generic 要 0/1/2；领域 profile 显式声明闭集 |
| D05：调用点 `runtime.inference` | 调用点 `claude -p` / `grok -p` | 回填 S11「A/B/C 运输 = CLI port」；embed 仍走 facade |
| S06：kernel 不可 agent 修 | 仍遵守；repair 只动 extension/形状 | 无需 reopen |
| S05 human gate | 默认不走 | 不删 StateFamily；生产 binding 关 eligibility |
| `T-O-53` 坏 member 整 scope 阻塞 | sibling 跑完；root 暂仍失败 | P1 不改；P5 再议 |

---

## 8. Verdict

| 面 | 判定 |
|---|---|
| 围栏（S03/S04/D08/gate/vector） | **留** |
| 当前 compiler 当生产 structurizer | **废**（可留作 fixture） |
| 当时 `layered_content` + 八份 prompt | **收**为 CLI 契约与 system instruction |
| `claude -p` 主链 / `grok -p` 修形状 | **收**（修理工真机未跑，P3 才算交付） |
| 人审当恢复、B 内写摘要、按句冒充分层 | **废** |
| 总评 | **GO，按 P0→P3 执行。** 未完成 P1 之前，不得声称「已用 MiniMax 做语义分层」。 |

**执行口令：** 先冻 schema 和正文，再让 B 的 JSON 成为 current，再接 A/C 和修理工。不要先铺 CLI 封装却继续用句子树当权威。
