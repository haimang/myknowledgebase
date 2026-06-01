# real-wire（真实接线）—— 初步规划（by Opus 4.8）

> **stage**：`initial`
> **作者**：`Opus 4.8`（panel / 跨模型 handoff：none）
> **时间**：`2026-06-01`
> **文档性质（自宣告 role）**：`initial` = "设计流程**第 ① 步**；不是 charter，不是 action-plan，**冻结零决策**——把 state-analysis 暴露的真实缺口整合成**少而厚（4 个内聚）**的候选 phase 与开放 gate"
> **上游权威输入**：
> - `docs/eval/real-wire/state-analysis-after-FF7-by-opus.md` — 缺口台账 D-01..D-09 + mock 资料/live-wiring 方案
> - `docs/design/first-fixes/owner-gated-qna.md` — [Q1]-[Q7]（real-wire 在其上扩展，不重开）
> - HEAD 实测锚（本文 §6 内联 file:line）：`rag_vectorizer/{embedder,search}.py`、`workflow_rag/service.py`、`workflow_clean/action_registry.py`、`config/{settings,config_repo}.py`、`apps/*/deps.py|main.py`、`storage_objects/filesystem_store.py`、`vector_sqlite_vec/{schema,vector_index}.py`、`legacy-family/**`（36 文件含内联 prompt）
> - 测试现状：`234 passed + 1 xfailed`；防假绿门禁 `tools/scripts/check_assert_strength.py`
> **phase 命名 & 工作项 ID 方案**：`RW-A | RW-B | RW-C | RW-D`（4 个内聚 phase）/ 工作项 `RWA-01..`（跨态稳定）
> **裁定动词 rubric**：initial=对 state-analysis 缺口/owner 提案做**整合裁定**（纳入 / refine / 不纳入），无 Δ-vs-plan 表
> **文档状态**：`draft`（v0.2，重构：7 稀疏 phase → 4 内聚 phase）
> **下游消费者**：`real-wire proposed-planning → charter/qna（关 G-RW-* gate）→ 4 份 action-plan（RW-A/B/C/D 各 1）`

---

## 0. TL;DR

- **核心论点**：first-fixes 夯实了**内核与管道**（234 passed），但**承载 RAG 价值的四件全空**——真实文档进入、prompt 载入与使用、LLM 推理、真实语义 embedding。real-wire 不推翻 first-fixes，而是**沿已留接口口子**（`Embedder`/`VectorIndex` 协议 + `get_active_prompt` 读取器 + `action_registry` degraded 位）把这四件接成真，**mock 先于 live、接口隔离、默认零配置零计费**，彻底纠正上一轮"mock 绿=能力通"的假绿。
- **一句话**：先建 **provider 基座 + mock 实现 + 真实样本（RW-A）**，再把 **prompt 驱动的语义处理链在 mock 下端到端去桩验证（RW-B）**，凭授权切 **live 真实模型（RW-C）**，按需扩 **PDF/二进制与真实 vec0（RW-D，条件）**。
- **本态相对上一态做了什么（v0.1→v0.2）**：把过于稀疏的 7 个 thin phase（RW1-RW7）**融合重构为 4 个内聚厚 phase**——RW-A=旧 RW1+RW2（provider 基座+mock+样本），RW-B=旧 RW3+RW4（prompt 载入+使用链去桩），RW-C=旧 RW5+真实 embedding（live），RW-D=旧 RW6+RW7（PDF/二进制+vec0，条件）。每 phase 1:1 派生 1 份**有真实深度**的 action-plan（§6 first-cut 已含 file:line 锚与子步）。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| state-analysis-after-FF7 | eval | 缺口 D-01..D-09 + mock `.tmp` 组织 + live `.env`/开关方案 | `docs/eval/real-wire/state-analysis-after-FF7-by-opus.md` |
| owner-gated-qna [Q1][Q2][Q3][Q7] | qna | embedding 本地1536 / vec0 degraded / 去桩增量 / 先红后绿——real-wire 在其上扩展 | `docs/design/first-fixes/owner-gated-qna.md` |
| `Embedder`/`VectorIndex` 协议（已留口）| 代码 | provider 局部替换不动上层 | `rag_vectorizer/embedder.py`、`vector_sqlite_vec/vector_index.py` |
| embedding 消费点（待工厂注入）| 代码实测 | `search.py:42-43`、`workflow_rag/service.py:186,243,263`（写/查 default_embedder）| 见 §6 RW-A |
| 语义去桩点（规则化桩）| 代码实测 | `workflow_rag/service.py:64`(structurize)、`:122`(build_summary)、`workflow_clean/action_registry.py:77,82,87`(clean/htmlCrawl/chinatax) | 见 §6 RW-B |
| `config_repo.get_active_prompt`（0 消费方）| 代码实测 | prompt 读取器孤立，待接消费链 | `config/config_repo.py` |
| legacy 内联 prompt | 代码实测 | **36 个 .ts 文件**含 prompt/systemInstruction（`flows/structurizer.ts`、`services/summarizer.ts`、`cloudflare_ai/providers/gemini.ts`…）；**非独立文件**，需抽取迁入 | `legacy-family/**` |
| 装配/注入点 | 代码实测 | `apps/api/deps.py:116,126`、`apps/worker/main.py:30,59`（硬编码构造）| 见 §6 RW-A |
| ObjectStore（仅文本）| 代码实测 | `put_text/get_text/exists/delete`，**无 put_bytes**；ingestion `file/confirm` 收 text | `storage_objects/filesystem_store.py:38-71`、`routes/ingestion.py:46-61` |
| vec0 退化点 | 代码实测 | `schema.py:68-76` except 退化为 TEXT 表 + fail-loud；`BruteForceVectorIndex` 待换 `Vec0VectorIndex` | `vector_sqlite_vec/{schema,vector_index}.py` |

- **纪律继承（不变）**：先红后绿 [Q7]；degraded fail-loud + reason；写/查同一 Embedder（⛔3）；测试默认不打外网（⛔6）；密钥不进仓/日志（F6c ⛔1）；维度=1536 不动 schema（[Q2]）。
- **借用骨架**：`docs/design/first-fixes/initial-planning-by-opus.md`。

---

## 2. 辨证审核（整合裁定）★ 承重段

### 2.A 对 state-analysis 缺口 / owner 提案的整合裁定（→ 4 内聚 phase）

| 来源项（state-analysis）| 整合裁定 | 落到 phase | 备注 |
|--------|----------|------------|------|
| mock provider + provider 工厂 + mock/live 开关 | 纳入（keystone）| **RW-A** | real-wire 灵魂：使用链离线可验证的前提 |
| D-06 真实样本语料 | 纳入 | **RW-A** | 与 mock provider 同 phase（样本喂 mock 链路）|
| 统一 `LLMProvider`/`Embedder`/`VectorIndex` 协议 + Settings/.env | 纳入 | **RW-A** | 接口隔离 keystone |
| D-04 prompt 载入+渲染+消费 | 纳入 | **RW-B** | 抽取 legacy 36 文件内联 prompt → 模板化 + seed + digest + 接消费 |
| D-01 LLM 推理（清洗/结构化/摘要去桩）| 纳入 | **RW-B**（mock 验证）+ **RW-C**（live）| 使用链先 mock 跑通, 再 live |
| structurize/clean/summary 规则桩 → prompt+LLM | refine（去桩, 规则化保留为 fallback）| **RW-B** | `service.py:64,122`、`action_registry.py:77` |
| D-02 真实语义 embedding | 纳入 | **RW-C** | 本地神经 或 外部 API（G-RW-1）；维度=1536 守卫 |
| live key/计费/速率/重试/密钥管理 | 纳入 | **RW-C** | owner-gated；live lane 不进默认 CI |
| D-05 PDF/二进制进入 | refine（条件）| **RW-D**（gated G-RW-3）| `put_bytes` + 上传端点 + PDF 解析 + browserPDF 去 degraded |
| D-03 真实 vec0(KNN) | refine（倾向延后）| **RW-D**（gated G-RW-4）| `Vec0VectorIndex` 替 BruteForce；接口已留口 |
| D-07 门禁接 CI / D-08 SSRF DNS-rebinding / D-09 purge 跨库一致性 | 不纳入（平台/生产化轮）| — | real-wire 不碰 |
| 多 provider(domain/realestate)/浏览器渲染 | 不纳入 | — | [Q3] 范围外 |

> **融合理由（回应"phase 过 thin"）**：旧 RW1(接口)与 RW2(mock+样本)无 mock 实现则接口空转、无样本则 mock 无可喂——二者**强内聚**，合为 RW-A。旧 RW3(prompt 载入)与 RW4(使用链)——prompt 载入的唯一目的就是被使用链消费，分开则 RW3 又是个孤立读取器（重蹈 F6c 教训），合为 RW-B。RW-C 把"切 live"与"真实 embedding"合（同属外部依赖接入 + 密钥 + 维度守卫）。RW-D 把"输入面扩展(PDF)"与"索引扩展(vec0)"合（同属能力面扩展、同 gated、同非关键路径）。

---

## 3. 范围与非范围（In/Out-Scope）

> 范围模态 = initial：**提案/条件式**，待 proposed sizing + charter 关 gate。

### 3.1 In-Scope（候选，4 内聚簇）

- **[S-A] provider 基座 + mock + 样本（RW-A，keystone）** — 统一三协议 + provider 工厂 + Settings/.env + MockLLMProvider + mock embedding + eval corpus + real-wire 测试原语 + mock/live 开关。
- **[S-B] prompt 驱动语义链去桩（RW-B）** — 抽取/迁入 legacy 内联 prompt + 渲染引擎 + digest + 接 `get_active_prompt` 到 structurize/clean/summary 消费侧 + prompt→render→LLM(mock) + mock capstone 语义验证（规则化保留 fallback）。
- **[S-C] live 接线（RW-C，gated）** — 真实 LLMProvider + 真实 Embedder（本地神经/外部 API）+ 维度守卫 + 计费/速率/重试 + 密钥管理 + live smoke lane。
- **[S-D] 输入面与索引扩展（RW-D，条件 gated）** — ObjectStore 二进制 + PDF 上传/解析 + browserPDF 去 degraded；`Vec0VectorIndex` 真实 KNN。

### 3.2 Out-of-Scope / 延后

- **[O1] 断言门禁接 CI runner** — 平台轮（脚本已就绪）。
- **[O2] SSRF DNS-rebinding / purge 跨库最终一致性** — 生产化轮。
- **[O3] 多 provider(domain/realestate) / 浏览器渲染 / LLM-clean(geminiUnderstanding) 之外的 legacy 全 AI 策略** — [Q3] 范围外；重评：产品需求。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线（TR）**：
  - **接口隔离**：mock 与 live 同协议（`LLMProvider`/`Embedder`/`VectorIndex`），切换只换实现、不动上层链路。
  - **维度=1536 不可破**：任何 embedding 实现输出≠1536 即 fail-loud（不动 vec schema，[Q2]）。
  - **写/查同 embedder**（⛔3）；**degraded/失败 fail-loud + 机器可读 reason**（不静默回退桩）。
  - **mock 先于 live**：使用链必须先在 mock provider + 真实样本下验证通过才接 live。
- **治理冻结面**：密钥不进仓/日志/夹具（F6c ⛔1），`.env` git-ignored，CI/生产用平台 secret；**测试默认 mock、不打外网**（⛔6）；**live 测试单独 lane、owner-triggered、不进默认 CI**（防计费/不稳定）；防假绿门禁扩展覆盖 real-wire 新测试。
- **migration inventory**（proposed/final 细化）：`prompt_versions` seed 迁移、`Settings` 新字段、（RW-D）ObjectStore 二进制 + 上传端点 schema、（RW-C）embedding 维度迁移（若选 ≠1536 须同步 vec.sql，倾向不允许）。

---

## 5. DAG（关键路径 + 并行窗）

```text
RW-A provider 基座+mock+样本 ──▶ RW-B prompt 语义链去桩(mock 验证) ──▶ RW-C live 接线(gated)
                             └─▶ RW-D 输入面/索引扩展(gated G-RW-3/4; 依赖 RW-A 接口与存储, 并行窗不抢 RW-B/C 带宽)
关键路径：RW-A → RW-B → RW-C
RW-D：条件启用, 倾向 RW-C 后或并行; 真实 vec0 倾向延后生产化
```

---

## 6. 逐 phase 工作台账（first-cut，待 pin）

### 6.A RW-A · provider 基座与 mock 验证底座（keystone）

> 内聚主题：**把"接口口子"接成"可注入的 provider 基座 + 默认 mock 实现 + 真实样本"**，让此后所有语义验证在离线、确定性、零计费下可跑。

| 编号 | 工作项 | 涉及模块（初判，待 pin）| 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RWA-01 | 新建 `LLMProvider` 协议（`complete(prompt,*,system?)->str`、可注入）+ 统一现有 `Embedder`/`VectorIndex` 到 provider 命名 | `packages/llm_provider/`（净新）| M | med |
| RWA-02 | provider 工厂 `make_llm/make_embedder/make_vector_index`（按 Settings 选实现，未知→fail-loud）| `packages/config/.../providers.py`（净新）| M | med |
| RWA-03 | `Settings` 增 provider/key/模型字段 + `env_file=".env"` 加载；**默认全 mock/local-hash/bruteforce** | `config/settings.py:1-9` | S | low |
| RWA-04 | 装配处改工厂注入：替 `apps/api/deps.py:116,126`、`worker/main.py:30,59` 的硬编码；rag 写(`service.py:186,243,263`)/查(`search.py:42`)**取同一 embedder 实例**（⛔3）| `apps/*/deps.py`、`worker/main.py`、`workflow_rag/*`、`rag_vectorizer/search.py` | L | **high**（触装配面，回归风险）|
| RWA-05 | `MockLLMProvider`（读 `llm_responses.json`，prompt_key→确定性响应；未命中 fail-loud）+ mock embedding（默认复用 LocalEmbedder）| `llm_provider/mock.py` + fixtures | M | low |
| RWA-06 | eval corpus 装载器 `tests/fixtures/eval_corpus.py`（读 `SMIND_EVAL_FIXTURES_DIR`，默认 `.tmp/eval-fixtures`）+ `.tmp` 目录构建脚本 + 可提交精简集 `tests/fixtures/samples/` | `tests/fixtures/`、`.tmp/eval-fixtures/`（见 state-analysis §7.2）| M | low |
| RWA-07 | real-wire 测试原语（注入 fetch/provider/embedder 的 monkeypatch helper + `assert_used_real_chain`：断言 provider/prompt 被真调用，非流转）| `tests/fixtures/primitives.py`（扩展）| S | med |
| RWA-08 | 先红后绿：工厂按 env 返回正确实现 + 默认 mock + 维度守卫 + 装配回归全绿 | `tests/unit/test_providers.py`、全量回归 | M | med |

### 6.B RW-B · prompt 驱动的语义处理链去桩（mock 下端到端验证）

> 内聚主题：**把 legacy 内联 prompt 抽取迁入 + 渲染 + 接到消费侧，使 structurize/clean/summary 走 `prompt→render→LLM(mock)→产物`**，在 mock provider + 真实样本下端到端语义验证（规则化保留为 fallback）。

| 编号 | 工作项 | 涉及模块（初判，待 pin）| 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RWB-01 | 抽取 legacy 内联 prompt（**36 .ts 文件**：`structurizer.ts`/`summarizer.ts`/`constructor.ts`/`cloudflare_ai/providers/gemini.ts`/clean gemini）→ 整理为模板 + 变量占位 | `legacy-family/**` → `.tmp/eval-fixtures/prompts/` + 仓内精简集 | L | med |
| RWB-02 | prompt 渲染引擎（变量注入 + sha256 digest 校验，载入失败/digest 不符 fail-loud）| `config/prompt_render.py`（净新）| M | med |
| RWB-03 | `prompt_versions` seed（team/global + template_path + digest）+ 把 `get_active_prompt` 接到消费侧（消除 F6c 孤立读取器）| seed 脚本 + `config_repo` 消费接线 | M | med |
| RWB-04 | structurize 去桩：`workflow_rag/service.py:64` LLM 模式走 `get_active_prompt('structurize')→render→llm.complete→解析 schema`；规则化为 fallback | `workflow_rag/service.py:61-101`、`rag_structurizer/*` | L | **high** |
| RWB-05 | summary/construct 去桩：`service.py:122` `build_summary` LLM 模式走 summarize prompt；规则摘要 fallback | `workflow_rag/service.py:103-229`、`rag_constructor/*` | M | high |
| RWB-06 | clean LLM 去桩：`action_registry.py` 的 `geminiUnderstanding`/`*-geminiClean` 从 degraded 换为真实 handler（LLM 模式）；degraded 仍保留为无 LLM 时 fallback | `workflow_clean/action_registry.py:77-99` | M | med |
| RWB-07 | mock capstone：文档(真实样本)→prompt→LLM(mock)→embedding→检索 端到端**语义命中**（`assert_vector_authentic`）+ **使用链证据**（prompt 被取用/provider 被调，非仅流转）| `tests/e2e/test_real_wire_capstone.py`（净新）| M | med |
| RWB-08 | 先红后绿 + 防假绿：mock 响应仅验"使用链发生+结构正确"，**显式标 non-delivery-quality**（质量验证留 RW-C live）；断言门禁覆盖新测试 | 同上 + 门禁 | S | med |

### 6.C RW-C · live 接线（真实 LLM + 真实 embedding，gated by G-RW-1/2/5/6）

> 内聚主题：**把 mock provider 换成真实外部/本地模型**——同一协议、只换实现 + 密钥/计费/速率/重试保护 + 维度守卫 + owner-triggered live smoke。

| 编号 | 工作项 | 涉及模块（初判，待 pin）| 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RWC-01 | 真实 `LLMProvider` 实现（厂商待 G-RW-2）+ 超时/重试/速率/预算上限保护 + 错误分类(可重试/不可重试) | `llm_provider/<vendor>.py`（净新）| L | **high** |
| RWC-02 | 真实 `Embedder` 实现（本地 sentence-transformers 或 外部 API，待 G-RW-1）+ **维度=1536 守卫**（≠1536 fail-loud）| `rag_vectorizer/embedders/<impl>.py`（净新）| L | **high** |
| RWC-03 | 密钥管理：`.env`(git-ignored) 起步 + 平台 secret 兼容；key 不入日志/dump；`.gitignore` 加 `.env`/`.tmp` | `config/settings.py`、`.gitignore` | S | med（安全）|
| RWC-04 | mock↔live 切换端到端验证：同一 capstone 在 `provider=mock` 与 `provider=<live>` 下结构一致（live 仅 owner-triggered）| `tests/live/`（默认 skip）| M | high |
| RWC-05 | live smoke（owner-triggered，**不进默认 CI**）：真实 key 一次性端到端 + 预算护栏 + 结果 owner 复核 | `tests/live/test_live_smoke.py` | M | high |
| RWC-06 | 文档：live 接入手册（`.env` 字段、切换、计费护栏、回退 mock）+ closure 据真实证据定级 | `docs/...` | S | low |

### 6.D RW-D · 输入面与索引扩展（PDF/二进制 + 真实 vec0，条件 gated）

> 内聚主题：**能力面扩展**——把输入从"文本 only"扩到 PDF/二进制，把索引从"暴力 cosine"扩到真实 vec0 KNN。条件启用、非关键路径。

| 编号 | 工作项 | 涉及模块（初判，待 pin）| 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RWD-01 | `ObjectStore.put_bytes/get_bytes`（沿用 `_resolve_safe` 边界，原子写）+ 二进制上传端点 | `storage_objects/filesystem_store.py:38-71`、`routes/ingestion.py`、`ingestion/service.py` | M | med |
| RWD-02 | PDF 解析器（依赖待 G-RW-3：pypdf/pdfminer）+ `browserPDF` 从 degraded 换真实 handler；解析失败 fail-loud | `cleaners_universal/*`、`workflow_clean/action_registry.py:90-95` | L | high |
| RWD-03 | PDF 端到端（上传→解析→clean→rag→vector→search）capstone（gated）| `tests/e2e/`、样本 `.tmp/.../pdf/` | M | med |
| RWD-04 | `Vec0VectorIndex`（sqlite-vec 扩展加载 `enable_load_extension`+`sqlite_vec.load`）替 `BruteForceVectorIndex`；接口已留口；rowid 不变量在 vec0 层复核 | `vector_sqlite_vec/{schema,vector_index,store}.py` | L | **high** |
| RWD-05 | 先红后绿：PDF 解析正确 + vec0 KNN 与暴力 cosine 结果一致性回归（degraded→真实切换不串味）| `tests/...` | M | high |

---

## 7. Owner decision gates

### 7.A 开放 gates（OPEN）

| 编号 | 决策点 | 影响 phase | 当前建议 / 倾向 | 状态 |
|------|--------|-----------|------------------|------|
| G-RW-1 | embedding 路线：本地神经(sentence-transformers, 需装依赖/算力) vs 外部 API(key/网络/计费)；维度是否锁 1536 | RW-C(RWC-02) | 倾向**本地神经**(零计费/可复现)；**锁 1536** 免动 schema | OPEN |
| G-RW-2 | LLM 厂商/模型（OpenAI/Gemini/Anthropic）+ prompt 原样迁 legacy vs 借机重写 | RW-B(RWB-01) + RW-C(RWC-01) | 厂商由 owner 定；prompt **先原样迁移**(保 digest 可追溯), 重写延后 | OPEN |
| G-RW-3 | 本轮是否接 PDF/二进制源 | RW-D 是否启用 | 倾向**本轮先不接**(先真接通 url/file 文本链路), PDF 下一子轮 | OPEN |
| G-RW-4 | 本轮是否接真实 vec0 | RW-D(RWD-04) | 倾向**延后生产化**(暴力 cosine 未成瓶颈) | OPEN |
| G-RW-5 | 计费/速率/预算上限由谁定、上限多少 | RW-C live 护栏 | owner 给预算 + 速率；live 默认关、按需开 | OPEN |
| G-RW-6 | 密钥管理：本地 `.env` vs 平台 secret manager | RW-A(RWA-03)+RW-C(RWC-03) | 本地 `.env`(git-ignored) 起步, 生产用平台 secret | OPEN |

> **结论**：本态 6 gate 全 OPEN——proposed 期 sizing、charter/qna 期 owner 关闭后方可派生 4 份 action-plan。**关键路径 RW-A 不依赖任何 gate**（默认 mock/local），可先行；G-RW-1/G-RW-2 是 RW-C 的前置；G-RW-3/G-RW-4 决定 RW-D 是否本轮做。

---

## 8. 测试计划

- **A 短途（unit / in-process）**：provider 工厂选型 + 默认 mock + 维度守卫（RWA-08）；prompt 载入/digest/渲染（RWB）；mock provider 确定性响应。
- **B spike（集成，mock provider + 真实样本，入 CI）**：文档→prompt→LLM(mock)→embedding→检索语义命中 + 使用链证据（RWB-07/08）；**全程不打外网**。
- **D mega（owner-triggered，live，默认 skip 不进 CI）**：真实 key 一次性端到端 live smoke（RWC-05）；预算/速率护栏。
- **防假绿**：沿用 `check_assert_strength.py`；real-wire 新测试必含"语义命中 + 使用链发生"证据；mock 响应显式标 non-delivery-quality（质量验证只在 live）；live 与 mock 分 lane。
- **DoD（概要，proposed/final 细化）**：RW-A 工厂+mock+样本+装配回归全绿；RW-B mock capstone 语义命中 + 使用链证据；RW-C live smoke owner 复核通过 + 默认零外网零计费可跑；（RW-D 若做）PDF 端到端 + vec0 一致性。

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| 装配面大改回归 | RWA-04 替换多处硬编码注入 | 全链 embedding 写/查不一致 | 工厂单点 + 写/查同 embedder 断言 + 全量回归门禁 |
| mock 假绿 | mock 响应被当真实 LLM 质量 | 重蹈 part-cr-8 假绿 | mock 仅验"使用链发生+结构"，标 non-delivery；质量只在 RW-C live |
| legacy prompt 抽取失真 | 36 .ts 内联 prompt 散乱、含 CF-AI 特定语法 | 迁入 prompt 与 legacy 行为偏差 | 原样迁 + digest 锁 + mock 响应对齐；重写延后(G-RW-2) |
| 维度漂移 | 外部 embedding≠1536 | 撞 vec schema CHECK | adapter fail-loud；G-RW-1 锁 1536 |
| 密钥泄漏 | key 误入仓/日志/夹具 | 凭据暴露 | `.env` git-ignored + 不入日志(F6c ⛔1) + 扫描 |
| 计费失控 | live 测试/循环误打 API | 费用 | 默认 mock + live owner-triggered + 预算/速率护栏(G-RW-5) |
| 离线无 ML 依赖 | 本地神经 embedding 需 torch | RWC-02 装不上 | G-RW-1 决策；装不上退外部 API 或保持哈希(标 degraded) |

---

## 10. 后继解锁 + action-plan 派生

- **解锁的下游价值**：语义真实的 RAG（真实 LLM 处理 + 真实 embedding 检索）；prompt 可运营（版本/digest）；PDF 源（若 RW-D）；生产 KNN（若 RW-D）。
- **派生预期**（initial 占位，final §10.A 才 1:1 绑定）：**4 个 phase → 4 份 action-plan**（RW-A/B/C/D 各 1）；关键路径 RW-A→RW-B→RW-C 串行，RW-D 条件并行/延后。

---

## 11. Final recommendation

- **推荐序列**：先关 **G-RW-1/G-RW-2**（embedding 路线 + LLM 厂商）→ proposed sizing → **RW-A（keystone，不依赖 gate，可立即起）→ RW-B（mock 下把 prompt+LLM 使用链端到端跑通，先红后绿，零花费零外网）**→ 凭 **G-RW-5/G-RW-6** 授权进 **RW-C（live）**；**RW-D 按 G-RW-3/G-RW-4 决定本轮是否做**（倾向延后）。
- **一句话总结**：real-wire = 沿 first-fixes 已留接口，把"语义为空的骨架"接成"语义真实的 RAG"——**4 个内聚 action-plan（基座/语义链/live/扩展），mock 先验使用链、开关切 live、接口隔离、默认零配置零计费**，把上一轮"mock 绿=能力通"的假绿用"使用链真发生 + live owner 复核"彻底纠正。

---

## 14. 交叉引用与修订历史

- **交叉引用**：`state-analysis-after-FF7-by-opus.md`（缺口源）、`first-fixes/initial-planning-by-opus.md`（骨架）、`owner-gated-qna.md`（[Q1][Q2][Q3] 扩展基线）、`check_assert_strength.py`（防假绿门禁）。

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-01 | Opus 4.8 | 初稿（7 稀疏 phase RW1-RW7）|
| v0.2 | 2026-06-01 | Opus 4.8 | **重构：融合为 4 个内聚厚 phase（RW-A 基座+mock+样本 / RW-B prompt 语义链去桩 / RW-C live / RW-D PDF+vec0），first-cut 台账加 file:line 锚与子步深度**；冻结零决策 |
