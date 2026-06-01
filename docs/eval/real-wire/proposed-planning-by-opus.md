# real-wire（真实接线）—— proposed-planning（by Opus 4.8）

> **stage**：`proposed`
> **作者**：`Opus 4.8`（panel / 跨模型 handoff：reference-anchor 由 4 个 Explore 子代理 fan-out 调查）
> **时间**：`2026-06-01`
> **文档性质（自宣告 role）**：`proposed` = "**取代 initial-planning**，作 pre-charter-qna 前**唯一精炼工作基线**——把 4 内聚 phase 的每个工作项绑定到 reference-anchor 的可借蓝本/避坑/净新 + sized + TR 过滤，但 gate 仍 OPEN（charter 期关）"
> **上游权威输入**：
> - `docs/eval/real-wire/initial-planning-by-opus.md` — 4 内聚 phase RW-A/B/C/D（被本态取代）
> - `docs/eval/real-wire/reference-anchor-by-opus.md` — 借鉴台账（轴 A/B/C/D 锚定矩阵 + 反例 + 净新 + TR 过滤 + 2 关键诚实发现）
> - `docs/eval/real-wire/state-analysis-after-FF7-by-opus.md` — 缺口 + mock/live `.tmp`/`.env` 方案
> - `docs/design/first-fixes/owner-gated-qna.md` — [Q1][Q2][Q3][Q7]（扩展基线，不重开）
> **phase 命名 & 工作项 ID 方案**：`RW-A/B/C/D`（phase）/ `RWA-01..` `RWB-01..` `RWC-01..` `RWD-01..`（跨态稳定，沿用 initial）
> **裁定动词 rubric**：proposed=**Δ 表 vs initial**：`KEEP / REFRAME / CLOSED / NEW`；复用判定 `✅复用 / ♻️重 substrate / 🆕净新`
> **文档状态**：`draft`
> **下游消费者**：`pre-charter-qna（关 G-RW-* gate）→ final-execution-plan → 4 份 action-plan（RW-A/B/C/D 各 1）`

---

## 0. TL;DR

- **核心论点**：reference-anchor 的调查证实——real-wire 可借的几乎全是**协议形状 + 算法/流程思路 + 输出 schema**（IAiProvider 协议、退避/错误分类、prompt key 分类法、输出 schema、上下文头注入、rowid 不变量、多级过滤），而 **Cloudflare 全部托管 binding（R2/Vectorize/Workers-AI/AI Gateway/DO/KV/Browser）一律重映射或净新**。HEAD 已留的 `Embedder`/`VectorIndex` 协议 + `ProviderRegistry` 范式 + `get_active_prompt` 读取器是 4 簇接线的现成挂载点——**RW-A 工作量因此下降（工厂是复用范式而非净新）**。
- **一句话**：4 phase（RW-A 基座→RW-B prompt 语义链→RW-C live→RW-D 扩展）不变，但每个工作项现已绑定到具体 `path:line` 蓝本 + 避坑 + TR 形态 + 规模。
- **本态相对上一态做了什么（initial v0.2 → proposed）**：① 把每个工作项**绑定 reference-anchor 蓝本/HEAD 锚/⛔避坑/TR**并 sized；② 两处**实质 REFRAME**：**RW-B 的 prompt 不是"迁入"而是"正文来源决策（正文在 KV 不在 repo）+ key 分类法/schema 复用"**（提升 G-RW-2 权重）；**RW-C 维度=1536 锁定确认、不迁 schema**（收窄 G-RW-1）；③ RW-A 工厂从"净新"降为"复用 `ProviderRegistry` 范式"。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| initial-planning v0.2 | 上一态 plan | 4 内聚 phase + first-cut 台账 + 6 OPEN gate | `initial-planning-by-opus.md` |
| reference-anchor | eval/anchor | 轴 A/B/C/D 锚定矩阵(path:line+verdict) + 反例 + 净新 + TR 过滤 + 核验记录 | `reference-anchor-by-opus.md` |
| state-analysis | eval | mock `.tmp/eval-fixtures` 组织 + `.env`/provider 开关方案 | `state-analysis-after-FF7-by-opus.md` |
| owner-gated-qna | qna | [Q1]vec0 degraded / [Q2]本地1536 / [Q3]去桩增量 / [Q7]先红后绿 | `owner-gated-qna.md` |

- **纪律继承（TR 红线，不变）**：TR-1 接口隔离(mock/live 同协议)；TR-2 维度=1536 不动 schema；TR-3 写/查同 embedder；TR-4 degraded/失败 fail-loud+reason；TR-5 密钥不进仓/日志、测试默认不打外网；TR-6 离线无 ML/无 Cloudflare binding。

---

## 2. 辨证审核（裁定 initial-planning）★ 承重段

### 2.B Δ 审核 vs initial-planning

| item-ID | 裁定 | 重分配 phase | 复用判定 | 理由 / 新证据（引 reference-anchor）|
|---------|------|--------------|----------|------------------|
| RWA-01 LLMProvider 协议 | KEEP | RW-A | ✅复用 | 蓝本 `ai_schemas.ts:170-179` IAiProvider + HEAD `embedder.py:28`/`vector_index.py:22` Protocol 范式 |
| RWA-02 provider 工厂 | **REFRAME**（降规模）| RW-A | ✅复用 | 不净新——复用已验证的 `providers_dedicated/service.py:114-151` ProviderRegistry 范式 |
| RWA-03 Settings+.env | KEEP | RW-A | ♻️重 substrate | `settings.py:1-11` 扩字段 + `env_file`；默认 mock/local |
| RWA-04 装配工厂注入 | KEEP（high）| RW-A | ✅复用 | 注入点已 grep 全：`search.py:42`/`workflow_rag:186,243,263`/`deps:114-128`/`worker:30,59`；写查同 embedder(TR-3)|
| RWA-05 MockLLMProvider | KEEP | RW-A | 🆕净新 | legacy 无 mock 层（直连 Workers-AI）；reference-anchor §3 净新 |
| RWA-06 eval corpus | KEEP | RW-A | 🆕净新 | state-analysis §7.2 `.tmp/eval-fixtures` 组织 |
| RWA-07 测试原语 | KEEP | RW-A | ♻️ | 扩 `tests/fixtures/primitives.py`（F7 已有底座）|
| RWB-01 prompt 抽取/迁入 | **REFRAME（核心转向）** | RW-B | 🆕净新(正文)+✅复用(key/schema) | **正文在 Cloudflare KV、不在 repo**（亲验 `structurizer/gemini.ts:167,294`+`kv.ts:100`）；可复用的是 `PROMPT_REGISTRY:43` key 分类法 + 输出 schema；**正文须 KV/owner 取或重写**→ 抬升 G-RW-2 |
| RWB-02 渲染引擎 | KEEP | RW-B | 🆕净新 | digest 校验 + 变量注入；失败 fail-loud |
| RWB-03 prompt_versions seed + 接消费 | KEEP | RW-B | ✅复用 | `get_active_prompt`(config_repo:31) 已有读取器、待接消费侧（消除 F6c 孤立）|
| RWB-04 structurize 去桩 | KEEP（high）| RW-B | ♻️重 substrate | `service.py:64` 规则桩→prompt→LLM；schema 蓝本 `schemas_common.ts:135-154` |
| RWB-05 summary/construct 去桩 | KEEP | RW-B | ♻️ | 借 `summarizer.ts` block-0 剥离/context_meta 回填启发式 |
| RWB-06 clean LLM 去桩 | KEEP | RW-B | ♻️ | `action_registry.py:90-99` gemini* degraded→真实 handler(LLM 模式)，degraded 留 fallback |
| RWB-07 mock capstone | KEEP | RW-B | 🆕 | 文档→prompt→LLM(mock)→embed→search 语义命中 + 使用链证据 |
| RWB-08 防假绿 | KEEP | RW-B | ✅复用 | `check_assert_strength.py` 扩覆盖；mock 标 non-delivery |
| RWC-01 真实 LLM client | KEEP | RW-C | 🆕净新(客户端)+✅复用(算法) | 借退避 `embedder.ts:40-164`+错误分类 `:73`；客户端按厂商净新(G-RW-2)|
| RWC-02 真实 embedding+维度守卫 | **REFRAME** | RW-C | 🆕净新 | **维度=1536 锁定确认、不迁 schema**（`vec.sql:22,43`）→ G-RW-1 收窄为"选 1536 维模型"；守卫泛化 `embedder.py:82` `!=self.dimension` |
| RWC-03 密钥管理 | KEEP | RW-C | ♻️ | ⛔避坑 `gemini.ts:96-132` 模块级 key 轮转→构造注入；`.env` git-ignored(TR-5)|
| RWC-04/05 live 切换/smoke | KEEP | RW-C | 🆕 | owner-triggered lane、不进默认 CI |
| RWC-06 live 文档 | KEEP | RW-C | ♻️ | 接入手册 + closure 据真实证据定级 |
| RWD-01 put_bytes/上传端点 | KEEP | RW-D | ♻️重 substrate | 借 `r2.ts:117-154` 二进制+MIME 签名思路；本地 FS + 原子写 + `_resolve_safe` |
| RWD-02 PDF 解析 | KEEP | RW-D | 🆕净新 | ⛔ `cleaner_web.ts:142-207` Browser Rendering+Vision 不可借；本地 pypdf/pdfminer(G-RW-3)|
| RWD-03 PDF capstone | KEEP | RW-D | 🆕 | gated |
| RWD-04 真实 vec0 | KEEP（延后）| RW-D | ♻️ | 接口已留口 `vector_index.py`；⛔ Vectorize/DO 不可借→sqlite-vec+F3 worker(G-RW-4)|
| RWD-05 PDF/vec0 先红后绿 | KEEP | RW-D | ✅复用 | 一致性回归(暴力 cosine↔vec0 不串味)|
| —（NEW）prompt 正文来源决策载体 | **NEW** | RW-B | 🆕净新 | 由 RWB-01 REFRAME 派生：需 owner 定正文来源（KV 导出 vs 据 schema 重写），是 RW-B 的前置 gate(G-RW-2)|

- **本态核心转向（一句话）**：从 initial 的"按缺口列 phase"精炼为"**按 reference-anchor 的可借蓝本/避坑/净新逐项绑定**"；最大实质转向 = **RW-B 的 prompt 由"迁入"→"正文来源决策（正文在 KV 不在 repo）+ key/schema 复用"**，及 **RW-C 维度=1536 锁定确认不迁 schema**。

---

## 3. 范围与非范围（In/Out-Scope）

> 范围模态 = proposed：**sized 但仍 gated**（charter 期由冻结 Q 关闭后定档）。

### 3.1 In-Scope（sized）

- **[S-A] RW-A provider 基座（L，keystone，不依赖 gate，可先行）** — 三协议统一(✅复用) + 工厂(✅复用 ProviderRegistry 范式) + Settings/.env(♻️) + MockLLMProvider(🆕) + eval corpus(🆕) + 装配注入(high) + 测试原语。
- **[S-B] RW-B prompt 语义链去桩（L，gated G-RW-2）** — prompt 正文来源(🆕，gate 前置) + key/schema 复用(✅) + 渲染引擎(🆕) + seed/接消费(✅) + structurize/summary/clean 去桩(♻️ high) + mock capstone(🆕)。
- **[S-C] RW-C live（L，gated G-RW-1/2/5/6）** — 真实 LLM/embedding(🆕+借算法) + 维度=1536 守卫(锁定) + 密钥管理(♻️避坑) + live smoke lane。
- **[S-D] RW-D 输入面/索引扩展（M，条件 gated G-RW-3/4）** — put_bytes/上传(♻️) + 本地 PDF 解析(🆕) + Vec0VectorIndex(♻️，延后)。

### 3.2 Out-of-Scope / 延后

- **[O1] 断言门禁接 CI / SSRF DNS-rebinding / purge 跨库一致性** — 平台/生产化轮。
- **[O2] 多 provider(domain/realestate)/浏览器渲染/多模态 Vision** — [Q3] 范围外 / 无本地多模态；重评：产品需求。
- **[O3] embedding ≠1536 维模型** — TR-2 锁定 1536；若必须则单列 schema 迁移（倾向不做）。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线（TR-1..6）**：见 §1；新增强调——**Cloudflare binding 全 ⛔**，借的是其上的协议/算法/schema（reference-anchor §5 已逐项过滤）。
- **治理冻结面**：密钥不进仓/日志/夹具（TR-5/F6c⛔1）；`.env` git-ignored；测试默认 mock 不打外网；**live 测试单独 lane、owner-triggered、不进默认 CI**；防假绿门禁扩展覆盖 real-wire。
- **migration inventory（proposed sized）**：
  - `MIG-RW-1` `Settings` 新增 provider/key/model 字段 + `env_file`（RWA-03，无 DB 迁移）
  - `MIG-RW-2` `prompt_versions` seed 数据迁移（RWB-03，行级 seed，非 schema 改）
  - `MIG-RW-3` ObjectStore 二进制 + 上传端点（RWD-01，若启用）
  - `MIG-RW-4` **维度 schema 迁移 = 不做**（TR-2 锁 1536；显式登记为"故意不迁"）

---

## 5. DAG（关键路径 + 并行窗）

```text
RW-A(基座, 不依赖 gate) ──▶ RW-B(prompt 语义链, gated G-RW-2) ──▶ RW-C(live, gated G-RW-1/2/5/6)
                       └─▶ RW-D(PDF/vec0, gated G-RW-3/4; 依赖 RW-A 接口/存储; 并行窗不抢 RW-B/C 带宽)
关键路径：RW-A → RW-B → RW-C
说明：RW-A 可在所有 gate 未关时即起（默认 mock/local）；RW-B 进入前需 G-RW-2(prompt 正文来源)；
RW-C 进入前需 G-RW-1(embedding 路线)+G-RW-5/6(预算/密钥)；RW-D 倾向延后(真实 vec0 → 生产化)。
```

---

## 6. 逐 phase 工作台账（proposed：重分配 + verdict 绑定 + 拆解）

### 6.A RW-A · provider 基座与 mock 验证底座（keystone）

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚(file:line) + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|----------------------------------------------------------|------|------|
| RWA-01 | `LLMProvider` 协议(`complete`/`complete_json`→{text,usage}) | ✅蓝本 `ai_schemas.ts:170-179`；HEAD 范式 `embedder.py:28`,`vector_index.py:22`；TR-1 | ✅复用 | S |
| RWA-02 | provider 工厂 `make_llm/make_embedder/make_vector_index`(按 Settings 选, 未知 fail-loud) | ✅蓝本 `providers_dedicated/service.py:114-151`(ProviderRegistry)；⛔避坑 `wrangler.toml` 硬编码无开关；TR-1 | ✅复用 | M |
| RWA-03 | `Settings` 增 provider/key/model 字段 + `env_file`；默认 mock/local-hash/bruteforce | HEAD `settings.py:1-11`,`loader.py:1-9`；TR-5(默认不打外网)；TR-6 | ♻️ | S |
| RWA-04 | 装配工厂注入(替硬编码 + 写/查同 embedder) | HEAD 注入点 `search.py:42`,`workflow_rag/service.py:186,243,263`,`apps/api/deps.py:114-128`,`worker/main.py:30,59`；TR-3 | ✅复用 | L（high）|
| RWA-05 | `MockLLMProvider`(读 `llm_responses.json`, 未命中 fail-loud) + mock embedding(复用 LocalEmbedder) | 蓝本 `embedder.py:66-92`(LocalEmbedder 作 mock)；reference §3 净新；TR-4 | 🆕净新 | M |
| RWA-06 | eval corpus 装载器 + `.tmp/eval-fixtures` 构建 + 可提交精简集 | state-analysis §7.2；TR-5 | 🆕净新 | M |
| RWA-07 | real-wire 测试原语(`assert_used_real_chain`: provider/prompt 被真调) | HEAD `tests/fixtures/primitives.py`(F7 底座)；TR-4 | ♻️ | S |
| RWA-08 | 先红后绿: 工厂选型 + 默认 mock + 维度守卫 + 装配回归全绿 | `check_assert_strength.py`；[Q7] | ✅复用 | M |

### 6.B RW-B · prompt 驱动的语义处理链去桩（mock 下验证）

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|----------------------------------------------|------|------|
| RWB-01 | **prompt 正文来源 + key 分类法/schema 复用**（正文在 KV 不在 repo → 取/重写）| ⛔避坑：正文不在 repo（亲验 `structurizer/gemini.ts:167,294`,`kv.ts:100`）；✅蓝本 `PROMPT_REGISTRY kv.ts:43`,schema `schemas_common.ts:135-154`；**gate 前置 G-RW-2** | 🆕净新(正文)+✅复用(key/schema) | L |
| RWB-02 | prompt 渲染引擎(变量注入 + sha256 digest 校验, 失败 fail-loud) | HEAD `prompt_versions` DDL(template_digest)；TR-4 | 🆕净新 | M |
| RWB-03 | `prompt_versions` seed + 接 `get_active_prompt` 到消费侧 | HEAD `config_repo.py:31-49`(读取器已有, 0 消费方待接)；MIG-RW-2 | ✅复用 | M |
| RWB-04 | structurize 去桩: `service.py:64` 规则→prompt→LLM(mock); 规则化 fallback | HEAD `rag_structurizer/service.py:30-71`；✅蓝本 schema `schemas_common.ts:135-154`；TR-1 | ♻️重 substrate | L（high）|
| RWB-05 | summary/construct 去桩: `service.py:122` build_summary→summarize prompt | HEAD `rag_constructor/service.py:64-97`；借 `summarizer.ts` block-0 剥离/context_meta 回填 | ♻️ | M |
| RWB-06 | clean LLM 去桩: `geminiUnderstanding`/`*-geminiClean` degraded→真实 handler | HEAD `workflow_clean/action_registry.py:90-99`；degraded 留无 LLM fallback；TR-4 | ♻️ | M |
| RWB-07 | mock capstone: 文档→prompt→LLM(mock)→embed→search 语义命中 + 使用链证据 | HEAD `tests/e2e/`；`assert_vector_authentic`(F7)；TR-1 | 🆕 | M |
| RWB-08 | 防假绿: mock 仅验"使用链发生+结构", 标 non-delivery-quality | `check_assert_strength.py`；[Q7] | ✅复用 | S |

### 6.C RW-C · live 接线（真实 LLM + 真实 embedding，gated）

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|----------------------------------------------|------|------|
| RWC-01 | 真实 `LLMProvider`(厂商待 G-RW-2) + 退避/重试/速率/预算 + 错误分类 | ✅蓝本算法 `embedder.ts:40-164`(退避)+`:73`(isRetryableError); ⛔ Workers-AI/AI Gateway 不可借；TR-6 | 🆕净新+✅复用算法 | L（high）|
| RWC-02 | 真实 `Embedder`(本地 sentence-transformers / 外部 API, 待 G-RW-1) + **维度=1536 守卫** | ✅蓝本守卫 `embedder.py:82`(泛化 `!=self.dimension`)；**TR-2 锁 1536, 不迁 schema(`vec.sql:22,43`)** | 🆕净新 | L（high）|
| RWC-03 | 密钥管理: `.env`(git-ignored)+平台 secret; key 不入日志 | ⛔避坑 `gemini.ts:96-132` 模块级轮转→**构造注入**; TR-5/F6c⛔1 | ♻️ | S |
| RWC-04 | mock↔live 切换端到端: 同 capstone 在 mock 与 live 下结构一致 | HEAD `tests/`; TR-1 | 🆕 | M |
| RWC-05 | live smoke(owner-triggered, 不进默认 CI) + 预算护栏 | 治理冻结面; TR-5 | 🆕 | M |
| RWC-06 | live 接入手册 + closure 据真实证据定级 | — | ♻️ | S |

### 6.D RW-D · 输入面与索引扩展（PDF/二进制 + 真实 vec0，条件 gated）

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚 + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|----------------------------------------------|------|------|
| RWD-01 | `ObjectStore.put_bytes/get_bytes` + 二进制上传端点 + MIME 贯穿 | ✅蓝本签名思路 `r2.ts:117-154`; HEAD `filesystem_store.py:38-71`(仅文本,`_resolve_safe`),`routes/ingestion.py:46-73`; MIG-RW-3 | ♻️重 substrate | M |
| RWD-02 | 本地 PDF 解析(pypdf/pdfminer, 待 G-RW-3) + `browserPDF` 去 degraded | ⛔避坑 `cleaner_web.ts:142-207`(Browser Rendering+Vision 不可借); HEAD `action_registry.py:90-95`; TR-6 | 🆕净新 | L |
| RWD-03 | PDF 端到端 capstone(上传→解析→clean→rag→vector→search) | gated; HEAD `tests/e2e/` | 🆕 | M |
| RWD-04 | `Vec0VectorIndex`(sqlite-vec 扩展加载) 替 BruteForce(延后) | ✅蓝本接口 `vector_index.py:22`; ⛔ Vectorize/DO 不可借→sqlite-vec; rowid 不变量虚表层复核; TR-2 | ♻️ | L（high）|
| RWD-05 | 先红后绿: PDF 解析正确 + vec0↔暴力 cosine 一致性回归 | [Q7] | ✅复用 | M |

---

## 7. Owner decision gates

### 7.A 开放 gates（OPEN，精炼）

| 编号 | 决策点 | 影响 phase | 精炼后建议 / 倾向（据 reference-anchor）| 状态 |
|------|--------|-----------|------------------|------|
| G-RW-1 | embedding 路线：本地神经(sentence-transformers) vs 外部 API；**维度锁 1536** | RW-C(RWC-02) | **锁 1536 已基本定（TR-2）**；剩"本地神经 vs 外部 API"——倾向本地神经(零计费/可复现)，装不上退外部 API | OPEN（收窄）|
| G-RW-2 | **prompt 正文来源**：从 Cloudflare KV 导出 vs 据 schema+用法重写；+ LLM 厂商 | RW-B(RWB-01) + RW-C(RWC-01) | **新权重升高**（正文不在 repo）；倾向：先据 schema/用法**重写**少量核心 prompt(structurize/summarize)，KV 导出为可选；厂商 owner 定 | OPEN（升权）|
| G-RW-3 | 本轮是否接 PDF/二进制 | RW-D 启用 | 倾向本轮先不接(先真接通 url/file 文本链路) | OPEN |
| G-RW-4 | 本轮是否接真实 vec0 | RW-D(RWD-04) | 倾向延后生产化(暴力 cosine 未成瓶颈) | OPEN |
| G-RW-5 | 计费/速率/预算上限 | RW-C live 护栏 | owner 给预算+速率；live 默认关 | OPEN |
| G-RW-6 | 密钥管理：`.env` vs 平台 secret | RW-A(RWA-03)+RW-C(RWC-03) | `.env`(git-ignored) 起步, 生产平台 secret | OPEN |

- **结论**：6 gate 全 OPEN（charter/qna 期关）。**RW-A 不依赖任何 gate，可先行**；进 RW-B 须关 G-RW-2，进 RW-C 须关 G-RW-1/5/6，RW-D 由 G-RW-3/4 决定。

---

## 8. 测试计划

- **A 短途（unit/in-process）**：工厂选型+默认 mock+维度守卫(RWA-08)；prompt 载入/digest/渲染(RWB)。
- **B spike（集成, mock provider + 真实样本, 入 CI, 不打外网）**：文档→prompt→LLM(mock)→embed→search 语义命中 + 使用链证据(RWB-07/08)。
- **D mega（owner-triggered, live, 默认 skip 不进 CI）**：真实 key 一次性端到端 live smoke(RWC-05) + 预算护栏。
- **防假绿**：`check_assert_strength.py` 扩覆盖；mock 标 non-delivery-quality；live/mock 分 lane。
- **DoD（proposed sized）**：
  - RW-A：工厂按 env 返正确实现 + 默认 mock + 装配回归全绿（234+ 不回归）。
  - RW-B：mock capstone 语义命中 + 使用链证据 + 规则化 fallback 仍绿。
  - RW-C：live smoke owner 复核通过 + 默认零外网零计费可跑 + 维度守卫 fail-loud。
  - RW-D（若做）：PDF 端到端 + vec0↔暴力 cosine 一致性。

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| 装配面大改回归 | RWA-04 替多处硬编码 | 写/查 embedder 不一致 | 工厂单点 + 写查同实例断言 + 全量门禁 |
| **prompt 正文缺失** | RWB-01 正文在 KV 不在 repo | RW-B 无 prompt 可用 | G-RW-2 决策(重写 vs KV 导出)；先重写核心 prompt 解锁 |
| mock 假绿 | mock 响应当真质量 | 重蹈 part-cr-8 | mock 仅验使用链+结构, 标 non-delivery; 质量只在 RW-C live |
| 维度漂移 | 外部 embedding≠1536 | 撞 schema CHECK | TR-2 锁 1536(G-RW-1); adapter fail-loud |
| 密钥泄漏 | key 误入仓/日志 | 凭据暴露 | `.env` git-ignored + 构造注入(非全局) + 不入日志 |
| 计费失控 | live 误打 API | 费用 | 默认 mock + live owner-triggered + 预算护栏(G-RW-5) |
| 离线无 ML 依赖 | 本地神经需 torch | RWC-02 装不上 | G-RW-1; 退外部 API 或保持哈希(标 degraded) |

---

## 10. 后继解锁 + action-plan 派生

- **解锁的下游价值**：语义真实 RAG（真实 LLM 处理 + 真实 embedding 检索）；prompt 可运营(版本/digest)；PDF 源(若 RW-D)；生产 KNN(若 RW-D)。
- **派生预期**（final §10.A 才 1:1 绑定）：**4 phase → 4 份 action-plan**（RW-A/B/C/D 各 1）；关键路径 RW-A→RW-B→RW-C 串行，RW-D 条件并行/延后。RW-A 工作项已 sized（S/M/L），可作 final 派生与排序的直接输入。

---

## 11. Final recommendation

- **推荐序列**：pre-charter-qna 关 **G-RW-1（embedding 路线, 已收窄至本地神经 vs 外部 API）+ G-RW-2（prompt 正文来源, 权重升高）** → final → **RW-A（keystone, 不依赖 gate, 可立即起）→ RW-B（mock 下 prompt+LLM 使用链端到端, 先红后绿, 零花费零外网）**→ 凭 G-RW-5/6 进 **RW-C（live）**；RW-D 按 G-RW-3/4 决定（倾向延后）。
- **一句话总结**：proposed 把 4 内聚 phase 的每个工作项钉到 reference-anchor 的**蓝本/避坑/TR/规模**——可借的是协议+算法+schema，Cloudflare 托管一律重映射/净新；两处实质转向（**prompt 正文不在 repo→来源决策**、**维度锁 1536 不迁 schema**）已据实并入，gate 待 charter 关闭后即可派生 4 份 action-plan。

---

## 14. 交叉引用与修订历史

- **交叉引用**：`reference-anchor-by-opus.md`（锚定台账）、`initial-planning-by-opus.md`（被取代）、`state-analysis-after-FF7-by-opus.md`、`owner-gated-qna.md`、`tools/scripts/check_assert_strength.py`。

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-01 | Opus 4.8 | proposed 初稿（stage=proposed）：取代 initial v0.2；§2.B Δ 审核绑定 reference-anchor；§6 工作项 sized + 蓝本/避坑/TR 绑定；两处 REFRAME（prompt 正文来源 / 维度锁 1536）；6 gate 精炼仍 OPEN |
