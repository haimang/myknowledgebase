# real-wire（真实接线）—— pre-charter-qna（身份反转版 · by Opus 4.8）

> **范围（QNA_SCOPE）**：`real-wire 阶段 charter 前置决策——关闭 proposed-planning 的 6 个 OPEN gate（G-RW-1..6），为 final-execution-plan + 4 份 action-plan（RW-A/B/C/D）定档`
> **目的**：把会改变 real-wire `contract surface / 实现边界 / 执行顺序 / 验收标准 / 支持面披露` 的业主决策，收敛到这一份单一清单。后续 final / action-plan / closure 引用某个 `Q-RW-N` 时，**以本文件的「业主回答」为唯一口径**。
> **上游权威输入**：
> - `docs/eval/real-wire/proposed-planning-by-opus.md`（§7 gate + §6 工作台账 + §9 风险）
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 A/B/C/D 锚定 + 2 关键诚实发现）
> - `docs/eval/real-wire/state-analysis-after-FF7-by-opus.md`（mock/live `.tmp`/`.env` 方案 + 对账诚实）
> - `docs/design/first-fixes/owner-gated-qna.md`（[Q1]vec0 degraded / [Q2]本地 1536 / [Q3]去桩增量 / [Q7]先红后绿——扩展基线，不重开）
> **下游消费者**：`final-execution-plan-by-opus.md → 4 份 action-plan（RW-A/B/C/D）`
> **文档状态**：`draft（待业主回填）`

---

## 0. 身份反转声明（必读）

本文件采用 **身份反转版**，并按业主要求 **移除 GPT 占位**。角色对调关系如下：

| 槽位 | 标准版 | 本文件（反转 + 无 GPT） |
|------|--------|--------------------------|
| `当前建议 / 倾向` | GPT 提出 | **Opus 提出** |
| `Reasoning` | GPT 写 | **Opus 写（面向第一次参与决策的业主）** |
| second-opinion 三段 | Opus 填 | **Opus 自填**：`Opus 的问题分解` / `Opus 的路线权衡`（替代原"对 GPT 推荐线路的分析"——因无 GPT，改为 Opus 自评各路线 trade-off）/ `Opus 的最终推荐` |
| `业主回答` | 业主裁决 | **业主裁决（留空，待回填）** |

- 结构字段一律保留（`影响范围 / 为什么必须确认 / 当前建议 / Reasoning / 三段 Opus 分析 / 问题 / 业主回答`），仅替换 second-opinion 角色名。
- **Q 编号**：本阶段用 `Q-RW-N` 前缀，以与 first-fixes 的 `[Q1]..[Q7]` 冻结集区分，避免编号碰撞。
- **gate 映射**：6 个 OPEN gate → 7 题（G-RW-2 按模板 §3.4「不捆绑多决策」拆为 Q-RW-2 LLM 厂商 + Q-RW-3 prompt 正文来源）。

| Q-RW | 对应 gate | 决策簇 | 阻塞 phase |
|------|-----------|--------|-----------|
| Q-RW-1 | G-RW-1 | 1 语义引擎选型 | RW-C（RWC-02） |
| Q-RW-2 | G-RW-2(厂商) | 1 语义引擎选型 | RW-C（RWC-01）+ RW-B 风格 |
| Q-RW-3 | G-RW-2(正文) | 2 prompt 正文来源 | **RW-B 前置**（RWB-01） |
| Q-RW-4 | G-RW-3 | 3 输入面/索引扩展 | RW-D 启用 |
| Q-RW-5 | G-RW-4 | 3 输入面/索引扩展 | RW-D（RWD-04） |
| Q-RW-6 | G-RW-5 | 4 live 治理与凭据 | RW-C 护栏 |
| Q-RW-7 | G-RW-6 | 4 live 治理与凭据 | RW-A（RWA-03）+ RW-C（RWC-03） |

> **进度提示**：**RW-A（keystone）不依赖任何 gate，可立即起**。进 RW-B 须关 Q-RW-3；进 RW-C 须关 Q-RW-1/2/6/7；RW-D 由 Q-RW-4/5 决定。

---

## 1. 决策簇 1 · 语义引擎选型

### Q-RW-1 — embedding 路线：本地神经 vs 外部 API（维度硬约束 = 1536）（来源：`proposed §7 G-RW-1` / `reference-anchor 轴 C` / `[Q2]`）

- **影响范围**：`RWC-02`（真实 Embedder）、`vector_sqlite_vec/vec.sql:22,43`（维度 CHECK）、`rag_vectorizer/embedder.py:82`（维度守卫）、TR-2/TR-3（写查同 embedder）、整个检索质量。
- **为什么必须确认**：当前 `LocalEmbedder` 是**纯哈希词袋（非神经网络，无语义/无同义词召回）**——它能跑通管线但检索价值近零。要让 RAG「真的检索得准」，必须替换为有语义的 embedding。而**维度被 schema 钉死在 1536**（`vec.sql` 的 CHECK 约束 + 写查一致性 TR-3），这与「常见本地神经模型的维度」存在**正面冲突**，不先拍板会让 RWC-02 在实现期反复返工或撞 schema。
- **当前建议 / 倾向（Opus）**：**维度锁 1536 不动 schema（继承 [Q2]/TR-2）**；embedding 实现**首选外部 API 中恰为 1536 维者**（如 OpenAI `text-embedding-3-small`/`ada-002` 天然 1536），**本地神经为次选但需正视维度不匹配**。
- **Reasoning（写给第一次决策的业主）**：
  1. **问题为什么出现**：[Q2] 当初冻结的是「本地 1536-dim Embedder」，但落地成了哈希桩（占位），没有真神经模型。现在要补真模型，却发现「本地 + 神经 + 恰好 1536 维」三者很难同时满足——业界主流开源句向量模型几乎没有 1536 维的：MiniLM=384、bge-base=768、bge-large/e5-large=1024、gte-large=1024；**1536 恰好是 OpenAI 系列的维度**。
  2. **为什么这条更稳**：若坚持「本地神经」，要么找冷门 1536 维模型（生态差、可复现性低），要么对 768/1024 维做**投影/padding 到 1536**（人为拼接，破坏度量语义，等于又造一个隐性桩，重蹈 part-cr-8 假绿覆辙）。相比之下，OpenAI 1536 维模型**零改 schema、零投影、即插即用**，代价是要联网 + 计费（受 Q-RW-6 预算护栏约束，且默认 mock、live 单独 lane）。
  3. **不拍板的后果**：RWC-02 无法动工——它是 RW-C 的承重项；且会连累 §9「维度漂移」风险（外部 embedding≠1536 撞 CHECK）。维度路线悬空 = live 链路整体悬空。
- **Opus 的问题分解**：
  - 子问题 A：维度是否真的不可改？→ 几乎不可改：`vec.sql` CHECK + 已落数据 + TR-3 写查一致，改维度=全库 schema 迁移 + 重嵌入（proposed `MIG-RW-4` 已显式登记为「故意不迁」）。
  - 子问题 B：在 1536 约束下，本地神经是否可行？→ 仅当接受「投影/padding」或「找冷门 1536 模型」，两者都引入新债务。
  - 子问题 C：是否容忍外网/计费？→ 这正是与 Q-RW-6（预算）耦合点；若 owner 拒绝任何外网，则只能本地投影或维持哈希（标 degraded）。
- **Opus 的路线权衡（自评 trade-off，替代 GPT 二意见）**：
  | 路线 | 维度 | 语义质量 | 计费/外网 | 可复现 | 债务 | 综合 |
  |------|------|----------|-----------|--------|------|------|
  | (a) 外部 API · OpenAI 1536 | ✅天然 1536 | 高 | 需 | 中（依赖供方） | 低 | **推荐** |
  | (b) 本地神经 + 投影到 1536 | ⚠️人为 | 中（投影损度量） | 否 | 高 | 高（隐性桩） | 次选 |
  | (c) 本地冷门 1536 模型 | ✅ | 中 | 否 | 低（生态差） | 中 | 备选 |
  | (d) 维持 LocalEmbedder 哈希 | ✅ | ~零 | 否 | 高 | —（已是桩） | 仅 fallback，标 degraded |
- **Opus 的最终推荐**：路线 **(a) 外部 API 1536**，理由是它是唯一「不动 schema + 不造新桩 + 真语义」的组合；将 (d) 哈希保留为 `SMIND_EMBEDDER=local-hash` 的离线 degraded fallback（fail-loud 标注非交付质量）。若 owner 硬性要求「零外网」，则退 (b) 并把「投影」作为显式 degraded 决策记账。
- **问题**：是否确认 **embedding 维度锁定 1536（不迁 schema）**，且 **live embedding 走外部 1536 维 API（如 OpenAI text-embedding-3-small）**、本地哈希仅作离线 degraded fallback？**如确认，请同时回答：是否允许该 embedding 调用走外网（这与 Q-RW-6 预算挂钩）？若不允许外网，是否接受本地神经投影到 1536 的语义损失？**
- **业主回答**：

### Q-RW-2 — live LLM 厂商选型（来源：`proposed §7 G-RW-2(厂商)` / `reference-anchor 轴 A` / `RWC-01`）

- **影响范围**：`RWC-01`（真实 LLMProvider 客户端）、`RWA-01`（LLMProvider 协议形状）、`RWB-01..06`（prompt 正文风格/格式须贴合所选厂商）、Q-RW-6（计费）。
- **为什么必须确认**：真实 LLM 客户端的实现（鉴权头、端点、错误码分类、JSON 模式/工具调用形态、token 计费单位）**因厂商而异**；且 prompt 正文重写（Q-RW-3）的风格要贴合目标模型。厂商不定，RWC-01 无法落地，RW-B 的 prompt 重写也缺锚。
- **当前建议 / 倾向（Opus）**：**用 `LLMProvider` 协议（蓝本 `ai_schemas.ts:170-179`）隔离厂商**，先接**单一厂商**起步；倾向 **Anthropic 或 OpenAI**（文档/SDK 成熟、JSON 模式稳定）。legacy 用的是 Gemini（经 Workers-AI/AI Gateway），但那套 binding **不可移植**，仅其 prompt 协议形状可借。
- **Reasoning**：
  1. **问题为什么出现**：legacy 在 Cloudflare 上直连 Gemini（`gemini.ts`），整套鉴权/网关/重试都绑死在 Workers 运行时；移植到 Python 离线单体后这些 binding 全失效，必须重选一个能从普通进程直连的厂商。
  2. **为什么这条更稳**：把厂商藏在 `LLMProvider` 协议背后（TR-1 接口隔离），换厂商只换一个实现类，不动 structurize/summarize/clean 的调用侧；先单厂商可把 RWC-01 规模从「多 provider 抽象」压到「一个客户端 + 退避/错误分类」（退避算法可借 `embedder.ts:40-164`）。
  3. **不拍板的后果**：RWC-01 悬空；且 Q-RW-3 的 prompt 重写没有目标模型，写出来的 prompt 可能与最终厂商的格式（如系统提示位置、JSON 模式开关）不兼容，二次返工。
- **Opus 的问题分解**：
  - 子问题 A：单厂商 vs 多厂商抽象？→ 本轮单厂商足矣（[Q3] 多 provider 在范围外）；协议隔离保留未来扩展口。
  - 子问题 B：哪个厂商？→ 取决于 owner 已有账号/预算/合规；技术上 Anthropic/OpenAI/Gemini 均可经 `LLMProvider` 接入。
  - 子问题 C：是否需 LLM 的 JSON/结构化输出能力？→ 需要：structurize/summarize 的输出 schema（`schemas_common.ts:135-154`）要求结构化返回，厂商须支持 JSON 模式或工具调用。
- **Opus 的路线权衡**：
  | 厂商 | 直连难度 | JSON 模式 | 与 legacy 一致 | 备注 |
  |------|----------|-----------|----------------|------|
  | Anthropic | 低 | 工具调用/结构化 | 否 | 本会话同源；SDK 成熟 |
  | OpenAI | 低 | 原生 JSON mode | 否 | 与 Q-RW-1 embedding 同厂可共用 key |
  | Gemini | 低 | 支持 | ✅（legacy 同款） | prompt 行为最接近 legacy，但需新 key |
- **Opus 的最终推荐**：若 Q-RW-1 选 OpenAI embedding，则 **LLM 也用 OpenAI**（单 key、单计费口径、最省接线）；若 owner 想最大程度复刻 legacy 语义行为，则选 **Gemini**。无论哪个，都经 `LLMProvider` 协议接入，单厂商起步。
- **问题**：live LLM 用哪个厂商（Anthropic / OpenAI / Gemini / 其他）？**如确认，请同时指明：是否接受「单厂商起步、协议隔离、暂不做多 provider 抽象」？**
- **业主回答**：

---

## 2. 决策簇 2 · prompt 正文来源

### Q-RW-3 — prompt 正文来源：从 Cloudflare KV 导出 vs 据 schema/用法重写（来源：`proposed §7 G-RW-2(正文)` / `reference-anchor 关键发现` / `RWB-01`）

- **影响范围**：`RWB-01`（RW-B 前置 gate）、`RWB-02..06`（渲染/structurize/summary/clean 去桩全部依赖有 prompt 正文）、`prompt_versions` seed（`RWB-03`/`MIG-RW-2`）、最终语义质量。
- **为什么必须确认**：reference-anchor **亲验确认**——legacy 的 prompt **正文（text）在 Cloudflare KV（`PROMPT_KV`）里，不在 repo**；`.ts` 文件（`structurizer/gemini.ts:167,294`、`kv.ts:43,100`）只有 **prompt key 注册表 + 输出 schema + 取用机制**，没有正文。这意味着「迁入 prompt」这个假设不成立——**正文要么从 KV 导出、要么据 schema/用法重写**。RW-B 的所有去桩工作都以「有真实 prompt 正文」为前提，此题不定，RW-B 整段无法动工。
- **当前建议 / 倾向（Opus）**：**据 schema + 用法重写少量核心 prompt（structurize / summarize）作为起点**，KV 导出列为**可选增强**（若 owner 能访问 KV 则导出比对、校准重写质量）。
- **Reasoning**：
  1. **问题为什么出现**：早期把 prompt 当成「在代码里、迁过来即可」；子代理调查穿透到 `kv.ts` 才发现正文存在外部托管 KV，repo 里只有钥匙和形状。这是本阶段最大的认知修正，也是 proposed 把 RWB-01 从「迁入」REFRAME 为「来源决策」的根因。
  2. **为什么这条更稳**：核心 prompt 数量不多（structurize、summarize 是主链），据其**输出 schema**（`schemas_common.ts:135-154` 明确规定了字段）+ **用法**（调用点上下文头注入）重写，能快速解锁 RW-B 且产物可控、可进 repo（KV 正文若不可访问就不会卡死）。KV 导出作为可选校准——有则更好，无则不阻塞。
  3. **不拍板的后果**：RW-B 整段（structurize/summary/clean 去桩 + mock capstone）全部阻塞；这是关键路径 RW-A→**RW-B**→RW-C 的中段，悬空则 live 永远到不了。
- **Opus 的问题分解**：
  - 子问题 A：KV 正文现在还能访问吗？→ 未知，取决于 owner 是否仍持有 Cloudflare 账号/`wrangler` 访问权。
  - 子问题 B：若能访问，导出值多少？→ 高：可作为重写的「黄金参照」校准语义；但即便导出，仍要适配新厂商格式（Q-RW-2）。
  - 子问题 C：重写需覆盖哪些 prompt？→ 至少 structurize（结构化抽取）、summarize（摘要/context_meta 回填）；clean 的 `geminiUnderstanding` 可作为第二批（RWB-06）。
- **Opus 的路线权衡**：
  | 路线 | 解锁速度 | 语义保真 | 依赖 KV 访问 | 入 repo | 备注 |
  |------|----------|----------|--------------|---------|------|
  | (a) 据 schema/用法重写核心 prompt | 快 | 中（需 mock 校验） | 否 | ✅ | **推荐起点** |
  | (b) KV 导出原文 | 慢（需账号） | 高 | ✅必需 | ✅ | 可选校准 |
  | (a)+(b) 重写为主、导出校准 | 中 | 高 | 部分 | ✅ | **最优若 KV 可达** |
- **Opus 的最终推荐**：**(a) 据 schema/用法重写核心 prompt（structurize/summarize）解锁 RW-B**；若 owner 能访问 KV，则并行 (b) 导出原文作为重写的校准参照，升级为 (a)+(b)。无论哪条，prompt 正文进 repo 并经 `prompt_versions` seed + sha256 digest 校验（RWB-02/03）。
- **问题**：prompt 正文采用哪条路线——**(a) 据 schema/用法重写核心 prompt** / **(b) 从 Cloudflare KV 导出原文** / **(a)+(b) 重写为主 + KV 导出校准**？**如选含 KV 导出的路线，请确认：你是否仍能访问 legacy 的 Cloudflare KV（`PROMPT_KV`）？**
- **业主回答**：

---

## 3. 决策簇 3 · 输入面与索引扩展范围（RW-D 启停）

### Q-RW-4 — 本轮是否接入 PDF / 二进制输入（来源：`proposed §7 G-RW-3` / `RWD-01/02` / `[Q3]`）

- **影响范围**：`RWD-01`（`ObjectStore.put_bytes/get_bytes` + 上传端点 + MIME）、`RWD-02`（本地 PDF 解析）、`RWD-03`（PDF capstone）；当前 `filesystem_store.py:38-71` **仅文本、无 put_bytes**。
- **为什么必须确认**：决定 RW-D 是否在本轮启用，以及是否扩展 ObjectStore 二进制能力（`MIG-RW-3`）。[Q3] 把 PDF 列为 degraded/增量，本轮做不做需 owner 点头——做则增 M~L 工作量，不做则 RW-D 上半段延后。
- **当前建议 / 倾向（Opus）**：**本轮先不接 PDF/二进制**，集中把 **url/file 文本链路真正接通**（RW-A→B→C 的语义闭环），PDF 留待文本链路验证后增量。
- **Reasoning**：
  1. **问题为什么出现**：legacy 的 PDF 走 Browser Rendering + Vision（`cleaner_web.ts:142-207`），这套 **不可移植**到离线 Python，必须换本地 PDF 库（pypdf/pdfminer），属净新工作。
  2. **为什么这条更稳**：real-wire 的核心价值是「让 RAG 语义真起来」——这条价值完全由文本链路（url/file → prompt → LLM → embed → search）承载；PDF 只是多一种输入源，不增语义深度。先把承重的文本链路打通、验证语义命中，再加输入源，是更小步、更可验证的路径。
  3. **不拍板的后果**：若误以为本轮含 PDF，会把 RWD-01/02 拉进关键路径、稀释 RW-A/B/C 带宽（§9「装配面大改回归」风险已够重）。
- **Opus 的问题分解**：
  - 子问题 A：业务上本轮是否有 PDF 文档必须处理？→ 取决于 owner 的真实语料；若 eval corpus 全是 url/text，则 PDF 非必需。
  - 子问题 B：put_bytes 扩展是否独立有价值？→ 有（二进制上传是通用能力），但可与 PDF 解析解耦、单独排期。
- **Opus 的路线权衡**：
  | 选项 | 本轮范围 | 关键路径影响 | 备注 |
  |------|----------|--------------|------|
  | (a) 本轮不接 PDF | RW-A/B/C | 不稀释 | **推荐**；RW-D 延后 |
  | (b) 本轮仅接 put_bytes（不接 PDF 解析） | +RWD-01 | 轻 | 若有二进制上传需求 |
  | (c) 本轮全接 PDF | +RWD-01/02/03 | 重（并行窗） | 仅当有硬性 PDF 语料 |
- **Opus 的最终推荐**：**(a) 本轮不接 PDF**，RW-D 整段延后；除非 owner 的 eval 语料含必须处理的 PDF，则退 (c) 并把 PDF 解析作为 RW-D 并行窗（不抢 RW-B/C 带宽）。
- **问题**：本轮是否接入 PDF / 二进制输入？**(a) 不接，RW-D 延后** / **(b) 仅接二进制上传 put_bytes** / **(c) 全接含 PDF 解析**？**如选 (a)/(b)，请确认本轮 eval 语料中没有「必须处理的 PDF」。**
- **业主回答**：

### Q-RW-5 — 本轮是否接入真实 vec0（sqlite-vec）索引（来源：`proposed §7 G-RW-4` / `RWD-04` / `[Q1]`）

- **影响范围**：`RWD-04`（`Vec0VectorIndex` 替 `BruteForceVectorIndex`）、`RWD-05`（vec0↔暴力 cosine 一致性回归）；接口口已留（`vector_index.py:22`）。
- **为什么必须确认**：[Q1] 已冻结「vec0 degraded → 暴力 cosine + fail-loud + VectorIndex 接口」。本轮是否升级到真实 sqlite-vec 扩展，决定 RWD-04 启停。但离线环境**未装 sqlite-vec 扩展**，且 Vectorize/Durable Objects（legacy 的 KNN 基座）不可移植。
- **当前建议 / 倾向（Opus）**：**延后到生产化轮**。暴力 cosine 在当前语料规模**未成性能瓶颈**，接口隔离已就位，何时换零成本。
- **Reasoning**：
  1. **问题为什么出现**：[Q1] 当初因 sqlite-vec 装不上而退到暴力 cosine，并刻意留了 `VectorIndex` 接口缝便于将来替换。
  2. **为什么这条更稳**：vec0 是**性能优化**，不增语义质量（检索结果应与暴力 cosine 一致，这正是 RWD-05 的一致性回归要保证的）。在 RAG 语义都还没真起来（Q-RW-1/3 未解）时优化 KNN 速度，是反镀金——把带宽花在没成为瓶颈的地方。
  3. **不拍板的后果**：若误启用，要处理 sqlite-vec 扩展加载 + 虚表 rowid 不变量复核（`store.py` 的 `_next_embedding_rowid` 单调性在虚表层须重验），是 L 级工作，挤占 RW-C live 带宽。
- **Opus 的问题分解**：
  - 子问题 A：当前语料规模下暴力 cosine 慢吗？→ eval 语料量级（百~千 chunk）下，暴力 cosine 毫秒级，无瓶颈。
  - 子问题 B：sqlite-vec 扩展本轮能装上吗？→ 离线环境存疑（与 torch/numpy 同属未装依赖）。
- **Opus 的路线权衡**：
  | 选项 | 性能 | 工作量 | 语义增益 | 备注 |
  |------|------|--------|----------|------|
  | (a) 延后，继续暴力 cosine | 足够 | 0 | 0 | **推荐** |
  | (b) 本轮接 vec0 | 更快 | L | 0 | 仅当语料规模已撞瓶颈 |
- **Opus 的最终推荐**：**(a) 延后**。接口缝已留（[Q1]），待语料规模真的撞到暴力 cosine 瓶颈、或进入生产化轮时再做 RWD-04，并以 RWD-05 一致性回归守住「换索引不串味」。
- **问题**：本轮是否接入真实 vec0（sqlite-vec）？**(a) 延后，维持暴力 cosine** / **(b) 本轮接入**？
- **业主回答**：

---

## 4. 决策簇 4 · live 治理与凭据

### Q-RW-6 — live 计费 / 速率 / 预算上限（来源：`proposed §7 G-RW-5` / `RWC-05` / `§9 计费失控`）

- **影响范围**：`RWC-05`（live smoke 预算护栏）、`RWC-01`（速率/重试）、Q-RW-1/Q-RW-2（外部 API 调用的计费口径）、live lane 治理面。
- **为什么必须确认**：一旦接外部 LLM/embedding（Q-RW-1/2），就产生**真实计费**与**速率限制**。无预算护栏 = §9「计费失控」风险敞口（live 误打 API 烧钱）。护栏参数（预算上限、速率、单次 smoke 调用数）须 owner 给定，否则 RWC-05 无验收基线。
- **当前建议 / 倾向（Opus）**：**默认 mock、零外网、零计费**；live **单独 lane、owner-triggered、不进默认 CI**；给一个**保守的单次 smoke 预算上限 + 速率上限**，超限 fail-loud 中止。
- **Reasoning**：
  1. **问题为什么出现**：real-wire 第一次引入「会花钱的外部调用」，这是 mock 阶段不存在的新治理面。
  2. **为什么这条更稳**：默认 mock 保证日常开发/CI 零成本零外网（TR-5）；live 只在 owner 主动触发的独立 lane 跑一次性 smoke，配预算/速率护栏，把「失控烧钱」从可能性变成被守卫的边界。
  3. **不拍板的后果**：RWC-05 没有验收阈值（多少调用算通过？预算多少算超限？）；且若护栏缺位，一次 live 回归挂死循环就可能产生意外账单。
- **Opus 的问题分解**：
  - 子问题 A：预算单位与上限？→ 建议给「单次 live smoke 的美元上限」+「月度上限」双护栏。
  - 子问题 B：速率限制？→ 建议给「每秒/每分钟请求数」上限，配退避（借 `embedder.ts:40-164`）。
  - 子问题 C：超限行为？→ fail-loud 中止 + 机器可读 reason（TR-4），不静默降级。
- **Opus 的路线权衡**：
  | 维度 | 保守建议 | 说明 |
  |------|----------|------|
  | 默认模式 | mock | CI/日常零成本 |
  | live 触发 | owner-triggered lane | 不进默认 CI |
  | 单次 smoke 预算 | owner 给（如 $1） | 超限 fail-loud |
  | 速率 | owner 给（如 N req/s） | 配退避重试 |
- **Opus 的最终推荐**：确认「默认 mock + live 独立 owner-triggered lane + 预算/速率双护栏 + 超限 fail-loud」框架；具体数值（单次 smoke 美元上限 / 速率）由 owner 填。
- **问题**：是否确认上述 live 计费治理框架？**如确认，请给出：① 单次 live smoke 的预算上限（美元）；② 速率上限（每秒或每分钟请求数）；③ 是否需要月度总预算护栏。**
- **业主回答**：

### Q-RW-7 — 密钥管理：`.env`（git-ignored）vs 平台 secret（来源：`proposed §7 G-RW-6` / `RWA-03`/`RWC-03` / `F6c ⛔1` / `TR-5`）

- **影响范围**：`RWA-03`（`Settings` + `env_file`）、`RWC-03`（密钥注入）、所有 live 凭据载体；治理红线「密钥不进仓/不进日志/不进夹具」。
- **为什么必须确认**：live 接线需要 API key（Q-RW-1/2 的厂商凭据）。key 的**存放位置 + 注入方式**直接决定泄漏面。F6c ⛔1 与 TR-5 已定红线（不进仓/日志），但**载体形式**（本地 `.env` vs 平台 secret manager）须 owner 拍板，且要避开 legacy 的反例。
- **当前建议 / 倾向（Opus）**：**起步用 `.env`（git-ignored）+ 构造注入**；生产环境迁平台 secret manager。**严禁**模块级全局 key 轮转（legacy `gemini.ts:96-132` 的反例）。
- **Reasoning**：
  1. **问题为什么出现**：legacy 在 Cloudflare 上用 `env.GEMINI_API_KEY` + 模块级 `getApiKey()` 轮转（`gemini.ts:96-132`）；移植到 Python 进程后，这套全局轮转既不可移植也是泄漏/测试污染反例。
  2. **为什么这条更稳**：`.env` + `Settings(env_file=...)`（`settings.py` 扩展）让密钥**只存本地、git-ignored、不进仓**；通过**构造注入**（把 key 经 provider 构造函数传入，而非模块级全局）避免 legacy 的轮转反例，也便于测试用假 key 注入。生产再升级平台 secret 是平滑路径。
  3. **不拍板的后果**：RWA-03/RWC-03 无法定密钥载体；且若放任模块级全局 key，会重蹈 legacy 反例（测试间 key 串味、日志泄漏面扩大）。
- **Opus 的问题分解**：
  - 子问题 A：本地载体？→ `.env`（git-ignored）+ `.env.example`（仅占位、可进仓）。
  - 子问题 B：注入方式？→ 构造注入（非模块级全局），便于 mock/live 切换与测试隔离。
  - 子问题 C：生产载体？→ 平台 secret manager（本轮可不实装，仅留迁移路径）。
- **Opus 的路线权衡**：
  | 载体 | 泄漏面 | 易用 | 测试隔离 | 本轮适配 |
  |------|--------|------|----------|----------|
  | (a) `.env` + 构造注入 | 低（git-ignored） | 高 | 好 | **推荐起步** |
  | (b) 平台 secret manager | 最低 | 中 | 好 | 生产轮 |
  | (c) 环境变量直读（无 `.env`） | 中 | 中 | 一般 | 备选 |
- **Opus 的最终推荐**：**(a) `.env`（git-ignored）+ 构造注入起步**，提供 `.env.example` 占位模板进仓；生产迁 (b) 平台 secret。密钥永不进仓/日志/夹具（TR-5/F6c⛔1），并写测试断言 key 不出现在日志。
- **问题**：密钥载体是否确认 **`.env`（git-ignored）+ 构造注入起步、生产迁平台 secret**？**如确认，请指明：本轮是否需要直接对接某个平台 secret manager（如需，请指明平台），还是本轮仅做 `.env` 起步、平台 secret 留作后续？**
- **业主回答**：

---

## 5. 回填后生效约束

- 业主仅在本文件「业主回答」处填写；一旦填写，即成为 `final-execution-plan` 与 4 份 action-plan 的**唯一口径**。
- 引用方只看 `Q-RW-N 编号 + 业主回答`，不在其他文档重复抄写 Opus 的分析。
- 如需推翻某答案，在本文件同一题下**追加修订说明**（带日期），不在别处悄悄改口。
- **gate→题 闭合检查**：G-RW-1→Q-RW-1；G-RW-2→Q-RW-2(厂商)+Q-RW-3(正文)；G-RW-3→Q-RW-4；G-RW-4→Q-RW-5；G-RW-5→Q-RW-6；G-RW-6→Q-RW-7。**7 题全部回填后，6 个 OPEN gate 即可在 final 关闭。**

---

## 6. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-01 | Opus 4.8 | 初稿（身份反转版，无 GPT 占位）：6 OPEN gate → 7 题（G-RW-2 拆厂商/正文）归 4 簇；每题含 Opus 当前建议 + Reasoning + 问题分解 + 路线权衡 + 最终推荐；业主回答待回填。点名 Q-RW-1 的「本地神经 vs 1536 维」正面冲突与 Q-RW-3 的「prompt 正文在 KV 不在 repo」核心修正 |
