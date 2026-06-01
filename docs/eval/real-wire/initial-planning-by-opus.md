# real-wire（真实接线）—— 初步规划（by Opus 4.8）

> **stage**：`initial`
> **作者**：`Opus 4.8`（panel / 跨模型 handoff：none）
> **时间**：`2026-06-01`
> **文档性质（自宣告 role）**：`initial` = "设计流程**第 ① 步**；不是 charter，不是 action-plan，**冻结零决策**——只把 state-analysis 暴露的真实缺口整合成候选 phase 与开放 gate"
> **上游权威输入**：
> - `docs/eval/real-wire/state-analysis-after-FF7-by-opus.md` — first-fixes 后真实状态 + deferred D-01..D-09 + mock 资料/live-wiring 方案
> - `docs/design/first-fixes/owner-gated-qna.md` — [Q1]-[Q7] 冻结裁决（real-wire 不重开，只在其上扩展）
> - HEAD 代码实测：`rag_vectorizer/embedder.py`(哈希 embedding)、`config/{settings,config_repo}.py`(无 provider 字段/孤立读取器)、`workflow_clean|rag/*`(规则化/无 LLM)；测试 `234 passed + 1 xfailed`
> **phase 命名 & 工作项 ID 方案**：`RW1..RW7`（phase）/ 工作项 `RW{n}-{nn}`（跨态稳定）
> **裁定动词 rubric**：initial=对 state-analysis 缺口与 owner 提案做**整合裁定**（纳入 / refine / 不纳入），无 Δ-vs-plan 表
> **文档状态**：`draft`
> **下游消费者**：`real-wire proposed-planning → charter/qna（关闭 G-RW-* gate）→ action-plan 派生`

---

## 0. TL;DR

- **核心论点**：first-fixes 把**内核与管道**夯实了（事务/幂等/安全/检索去重/测试有效性，234 passed），但**承载 RAG 价值的四大件全空**——真实文档进入、prompt 载入与使用、LLM 推理、真实语义 embedding。real-wire 阶段的唯一使命，是**沿 first-fixes 已留好的接口口子（`Embedder`/`VectorIndex` 协议 + `get_active_prompt` 读取器 + degraded 注册位），把这四件从"桩/无"接成"真"**，且全程 **mock 先于 live、接口隔离、默认零配置零计费**，绝不重蹈"mock 绿=能力通"的假绿。
- **一句话**：把"语义为空的骨架"接成"语义真实的 RAG"——先用可注入的 **mock provider + 真实样本语料 + 迁入的 prompt** 在离线把"文档→prompt→LLM→embedding→检索"整条**使用链**真实跑通并验证，再用一个**环境变量开关**切到 live（真实 key/模型）。
- **本态产出**：候选 phase（RW1-RW7）+ 6 个 owner 决策 gate（embedding 路线/LLM 厂商/PDF/vec0/计费/密钥管理）+ DAG + 风险登记；**不冻结任何决策**。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| state-analysis-after-FF7 | eval | 真实缺口台账 + deferred D-01..D-09 + mock 资料 `.tmp` 组织 + live-wiring `.env`/开关方案 | `docs/eval/real-wire/state-analysis-after-FF7-by-opus.md §2-§8` |
| owner-gated-qna [Q1][Q2][Q3] | qna | embedding=本地1536 / vec0 degraded / 去桩增量——real-wire 在其上**扩展而非推翻** | `docs/design/first-fixes/owner-gated-qna.md` |
| `Embedder` / `VectorIndex` 协议 | 代码 anchor | 已留的接口口子（provider 局部替换不动上层）| `rag_vectorizer/embedder.py`、`vector_sqlite_vec/vector_index.py` |
| `config_repo.get_active_prompt` | 代码 anchor | prompt 读取器（**0 消费方**，待接消费链）| `config/config_repo.py` |
| `action_registry` degraded 位 | 代码 anchor | `browser*/gemini*` degraded handler（待换真实）| `workflow_clean/action_registry.py:90-99` |
| 测试 234 passed + 门禁 | 代码 anchor | 内核/管道可信地基；防假绿门禁可复用于 real-wire | `tests/`、`tools/scripts/check_assert_strength.py` |

- **纪律继承**（自 first-fixes 不变）：先红后绿铁律 [Q7]；degraded 必 fail-loud + 机器可读 reason；写/查共用同一 Embedder（⛔3）；测试默认不打外网（⛔6）；密钥不进仓/不进日志（F6c ⛔1）；维度=1536 不动 schema（[Q2]）。
- **借用骨架**：以 `docs/design/first-fixes/initial-planning-by-opus.md` 为格式骨架。

---

## 2. 辨证审核（整合裁定）★ 承重段

### 2.A 对 state-analysis 缺口 / owner 提案的整合裁定

| 来源项 | 整合裁定 | 落到哪个 phase | 备注 |
|--------|----------|----------------|------|
| D-01 真实 LLM 推理 | 纳入 | RW1（接口）+ RW4（使用链 mock）+ RW5（live） | 先 mock provider 验证使用链, 再 live |
| D-02 真实语义 embedding | 纳入 | RW1（接口）+ RW5（live：本地神经 或 外部 API） | 维度锁 1536（[Q2]）；走 `Embedder` 口子 |
| D-04 prompt 载入+渲染+使用 | 纳入 | RW3（载入/渲染/接消费）+ RW4（用） | legacy 模板迁入 + digest 校验 + 接 `get_active_prompt` |
| D-06 真实样本语料 | 纳入 | RW2 | `.tmp/eval-fixtures` 构建 + 可提交精简集进 CI |
| mock provider（LLM/embedding 可注入确定性响应）| 纳入（real-wire 灵魂）| RW1 + RW2 | 让"使用链"在离线被**真实验证**, 非硬编码串 |
| mock↔live 环境变量开关 + provider 工厂 | 纳入 | RW1（keystone） | `SMIND_*_PROVIDER`；默认全 mock/local |
| D-05 PDF/二进制进入 | refine（条件纳入）| RW6（gated by G-RW-3） | 需 `put_bytes` + PDF 解析依赖；owner 决定本轮是否做 |
| D-03 真实 vec0(KNN) | refine（倾向延后）| RW7（gated by G-RW-4） | 暴力 cosine 未成瓶颈前不接；倾向 out-of-scope |
| D-07 断言门禁接 CI | 不纳入（平台轮）| — | 无 CI runner；脚本已就绪 |
| D-08 SSRF DNS-rebinding / D-09 purge 跨库一致性 | 不纳入（生产化轮）| — | real-wire 不碰；生产化处理 |
| 多 provider(domain/realestate) / 浏览器渲染 | 不纳入 | — | [Q3] 范围外, 非 real-wire 主线 |

---

## 3. 范围与非范围（In/Out-Scope）

> 范围模态 = initial：**提案 / 条件式**，待 proposed sizing、charter/qna 关闭 gate。

### 3.1 In-Scope（候选）

- **[S1] provider 抽象 + mock/live 开关（RW1，keystone）** — 建 `LLMProvider` 协议 + provider 工厂（`make_llm/make_embedder/make_vector_index`），按 `Settings` 选实现；默认全 mock/local，接口隔离。
- **[S2] mock provider + 真实样本语料（RW2）** — `MockLLMProvider`（确定性响应）+ `tests/fixtures` 样本/期望集 + `.tmp/eval-fixtures` 构建组织；让使用链离线可验证。
- **[S3] prompt 载入/渲染/消费接线（RW3）** — legacy-family 模板迁入 + `prompt_versions` seed + digest 校验 + 渲染引擎 + 把 `get_active_prompt` 接到 clean/structurize 消费侧。
- **[S4] prompt→LLM 使用链去桩（RW4）** — structurize/clean/summary 在 LLM 模式下走 `prompt→render→provider→产物`；规则化保留为 fallback；mock provider 下端到端 capstone 验证（先红后绿）。
- **[S5] live 接入（RW5，gated）** — 真实 LLM + 真实 embedding（本地神经 或 外部 API）+ 维度守卫 + 重试/超时/计费保护；live 测试不进默认 CI。

### 3.2 Out-of-Scope / 延后（候选）

- **[O1] 真实 vec0(KNN)（RW7）** — 暴力 cosine 未成瓶颈前延后；重评条件：数据量增大检索慢。
- **[O2] PDF/二进制进入（RW6）** — 条件纳入（G-RW-3）；重评条件：owner 确认本轮要 PDF 源。
- **[O3] 多 provider/浏览器渲染** — [Q3] 范围外；重评条件：产品需求。
- **[O4] SSRF DNS-rebinding / purge 跨库一致性 / 断言门禁接 CI** — 生产化/平台轮；重评条件：生产暴露/有 CI。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线（TR）**：
  - **接口隔离**：mock 与 live 走**同一协议**（`LLMProvider`/`Embedder`/`VectorIndex`），切换只换实现、不动上层链路。
  - **维度=1536 不可破**：任何 embedding 实现输出≠1536 即 fail-loud（不动 vec schema，[Q2]）。
  - **写/查同 embedder**（⛔3）、**degraded/失败 fail-loud + reason**（不静默回退桩）。
  - **mock 先于 live**：使用链必须先在 mock provider + 真实样本下验证通过，才接 live。
- **治理冻结面**：
  - 密钥**不进仓、不进日志、不进测试夹具**（F6c ⛔1）；`.env` git-ignored；CI/生产用平台 secret。
  - **测试默认 mock、不打外网**（⛔6）；live 测试单独 lane、owner-triggered、不进默认 CI（防计费/不稳定）。
  - 防假绿门禁（`check_assert_strength.py`）扩展覆盖 real-wire 新测试。
- **migration inventory**（proposed/final 期细化）：`prompt_versions` seed 迁移、`Settings` 新字段、（若 RW6）ObjectStore 二进制 + 上传端点 schema。

---

## 5. DAG（关键路径 + 并行窗）

```text
RW1 provider 抽象+开关 ──▶ RW2 mock provider+样本 ──▶ RW3 prompt 载入/渲染 ──▶ RW4 使用链去桩(mock 验证) ──▶ RW5 live 接入(gated)
                       └─▶ RW6 PDF/二进制(gated G-RW-3)  （并行窗：依赖 RW1 的 ObjectStore 二进制扩展, 不抢 RW2-4 带宽）
RW7 真实 vec0 (gated G-RW-4, 倾向延后生产化)
关键路径：RW1 → RW2 → RW3 → RW4 → RW5
```

---

## 6. 逐 phase 工作台账（first-cut，待 pin）

### 6.1 RW1 · provider 抽象与 mock/live 开关（keystone）

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RW1-01 | 新建 `LLMProvider` 协议（`complete(prompt)->str` / 可注入）+ `MockLLMProvider` | `packages/llm_provider/`（净新） | M | med |
| RW1-02 | provider 工厂 `make_llm/make_embedder/make_vector_index`（按 Settings 选实现）| `config/providers.py`（净新） | M | med |
| RW1-03 | `Settings` 增 provider/key 字段 + `.env` 加载（env_file）；默认全 mock/local | `config/settings.py` | S | low |
| RW1-04 | deps/worker 装配处改用工厂注入（替 `default_embedder()` 硬编码）；写/查同 embedder | `apps/*/deps.py`、`worker/main.py`、`workflow_rag/*` | M | high（触装配面）|
| RW1-05 | 先红后绿：工厂按 env 返回正确实现 + 默认 mock + 维度守卫单测 | `tests/unit/test_providers.py`（净新）| S | low |

### 6.2 RW2 · mock provider 与真实样本语料

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RW2-01 | `tests/fixtures/eval_corpus.py` 读 `SMIND_EVAL_FIXTURES_DIR`（默认 `.tmp/eval-fixtures`）| `tests/fixtures/`（净新）| S | low |
| RW2-02 | 样本语料：html/docs/chinatax + 每条 `expectations.json`（期望先写=先红依据）| `.tmp/eval-fixtures/` + 精简集 `tests/fixtures/samples/` | M | low |
| RW2-03 | `MockLLMProvider` 读 `llm_responses.json`（prompt_key→确定性响应）；embedding mock 默认复用 LocalEmbedder | `llm_provider/mock.py` + fixtures | S | low |
| RW2-04 | 先红后绿：样本注入 fetch/provider，端到端在 mock 下产真实结构化/向量/检索 | `tests/integration/real_wire/`（净新）| M | med |

### 6.3 RW3 · prompt 载入 / 渲染 / 消费接线

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RW3-01 | 从 `legacy-family/**/prompts` 迁模板 + 算 digest + `prompt_versions` seed | `.tmp` + seed 脚本 + `config_repo` | M | med |
| RW3-02 | prompt 渲染引擎（变量占位注入 + digest 校验，载入失败 fail-loud）| `config/prompt_render.py`（净新）| M | med |
| RW3-03 | 把 `get_active_prompt` 接到 clean/structurize 消费侧（LLM 模式用）| `workflow_clean/*`、`workflow_rag/*` | M | high |
| RW3-04 | 先红后绿：prompt 载入→digest 校验→渲染→可被消费方取用（mock provider）| `tests/.../test_prompt_pipeline.py`（净新）| M | med |

### 6.4 RW4 · prompt→LLM 使用链去桩（mock 验证）

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RW4-01 | structurize/clean/summary 在 LLM 模式：`prompt→render→llm.complete→产物`；规则化为 fallback | `workflow_rag/*`、`workflow_clean/*` | L | high |
| RW4-02 | capstone（mock）：文档→prompt→LLM→embedding→检索 端到端语义命中 | `tests/e2e/test_real_wire_capstone.py`（净新）| M | med |
| RW4-03 | 防假绿：断言"使用链真发生"（prompt 被取用 / provider 被调 / 产物含 LLM 影响），非仅流转 | 同上 | S | med |

### 6.5 RW5 · live 接入（gated by G-RW-1/2/5/6）

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RW5-01 | 真实 `LLMProvider` 实现（厂商待 G-RW-2）+ 超时/重试/速率/预算保护 | `llm_provider/<vendor>.py`（净新）| L | high |
| RW5-02 | 真实 `Embedder` 实现（本地神经 或 外部 API，待 G-RW-1）+ 维度=1536 守卫 | `rag_vectorizer/embedders/`（净新）| L | high |
| RW5-03 | live smoke（owner-triggered，不进默认 CI）：真实 key 一次性端到端验证 | `tests/live/`（净新, 默认 skip）| M | high |

### 6.6 RW6 · PDF/二进制进入（gated by G-RW-3，可并行）

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RW6-01 | `ObjectStore.put_bytes/get_bytes`（沿用 `_resolve_safe` 边界）+ 二进制上传端点 | `storage_objects/*`、`ingestion/*`、`api/routes` | M | med |
| RW6-02 | PDF 解析器（依赖待定：pypdf/pdfminer）+ `browserPDF` 去 degraded 换真实 handler | `cleaners_universal/*`、`action_registry` | L | high |

### 6.7 RW7 · 真实 vec0（gated by G-RW-4，倾向延后）

| 编号 | 工作项 | 涉及模块（初判，待 pin） | 规模 | 风险 |
|------|--------|--------------------------|------|------|
| RW7-01 | `Vec0VectorIndex`（sqlite-vec 扩展加载）替 `BruteForceVectorIndex`；接口已留口 | `vector_sqlite_vec/*` | L | high |

---

## 7. Owner decision gates

### 7.A 开放 gates（OPEN）

| 编号 | 决策点 | 影响 | 当前建议 / 倾向 | 状态 |
|------|--------|------|------------------|------|
| G-RW-1 | embedding 路线：本地神经(sentence-transformers, 需装依赖/算力) vs 外部 API(需 key/网络/计费)；维度是否锁 1536 | RW5-02 选型 + 是否动 schema | 倾向**本地神经**(零计费/可复现)；**锁 1536** 免动 schema | OPEN |
| G-RW-2 | LLM 厂商/模型（OpenAI/Gemini/Anthropic）+ prompt 是否原样迁 legacy vs 借机重写 | RW5-01 + RW3 | 厂商由 owner 定；prompt **先原样迁移**(保 digest 可追溯), 重写延后 | OPEN |
| G-RW-3 | 本轮是否接 PDF/二进制源 | 是否启用 RW6（+ 二进制存储/解析依赖） | 倾向**本轮先不接**(先把 url/file 文本链路真接通), PDF 下一子轮 | OPEN |
| G-RW-4 | 本轮是否接真实 vec0 | 是否启用 RW7 | 倾向**延后生产化**(暴力 cosine 未成瓶颈) | OPEN |
| G-RW-5 | 计费/速率/预算上限由谁定、上限多少 | RW5 live 保护参数 | 需 owner 给预算上限 + 速率；live 默认关、按需开 | OPEN |
| G-RW-6 | 密钥管理：本地 `.env` vs 平台 secret manager | RW1-03 + 部署 | 本地 `.env`(git-ignored) 起步, 生产用平台 secret | OPEN |

> **结论**：real-wire 是"在 first-fixes 冻结裁决上扩展"，本态 6 个 gate 全 OPEN——proposed 期 sizing、charter/qna 期由 owner 关闭后方可派生 action-plan。

---

## 8. 测试计划

- **A 短途（unit / in-process）**：provider 工厂选型 + 默认 mock + 维度守卫（RW1-05）；prompt 载入/digest/渲染（RW3-04）；mock provider 确定性响应。
- **B spike（集成，mock provider + 真实样本，入 CI）**：文档→prompt→LLM(mock)→embedding→检索端到端语义命中（RW2-04/RW4-02）；断言"使用链真发生"而非流转（RW4-03）。**全程不打外网。**
- **D mega（owner-triggered，live，默认 skip 不进 CI）**：真实 key 一次性端到端 live smoke（RW5-03）；带预算/速率保护。
- **防假绿**：沿用 `check_assert_strength.py`；real-wire 新测试必含"语义命中 + 使用链证据"，degraded/mock 必带 reason；live 与 mock 分 lane。
- **DoD（概要，proposed/final 细化）**：mock 使用链 capstone 绿 + 真实样本语义命中（assert_vector_authentic）+ live smoke owner 复核通过 + 默认配置零外网零计费可跑。

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| 装配面大改回归 | RW1-04 替换 `default_embedder()` 硬编码注入点多 | 全链路 embedding 写/查不一致 | 工厂单点 + 写/查同 embedder 断言 + 全量回归门禁 |
| mock 假绿（mock 响应当真功能）| mock provider 响应被当成真实 LLM 质量 | 重蹈 part-cr-8 假绿 | mock 仅验"使用链发生"+ 显式标 non-delivery；live smoke 才验质量 |
| 维度漂移 | 外部 embedding 模型≠1536 | 撞 vec schema CHECK | adapter 边界 fail-loud；G-RW-1 锁 1536 |
| 密钥泄漏 | key 误入仓/日志/夹具 | 凭据暴露 | `.env` git-ignored + 不入日志（F6c ⛔1）+ 扫描门禁 |
| 计费失控 | live 测试/循环误打外部 API | 费用 | 默认 mock + live owner-triggered + 预算/速率保护（G-RW-5）|
| 离线无 ML 依赖 | 本地神经 embedding 需 torch/sentence-transformers | RW5-02 装不上 | G-RW-1 决策；装不上则退外部 API 或保持本地哈希(标 degraded) |
| 外网不稳/SSRF | live 抓取/调用打真实网络 | 不稳定/安全面 | SSRF 守卫已在（主机名级）；live 测试隔离 lane |

---

## 10. 后继解锁 + action-plan 派生

- **解锁的下游价值**：语义真实的 RAG（真实 LLM 处理 + 真实 embedding 检索）；prompt 可运营（版本/digest）；PDF 源（若 RW6）；生产 KNN（若 RW7）。
- **派生预期**（initial 仅占位，final §10.A 才 1:1 绑定）：RW1-RW7 phase 簇预计各派生 1 份 action-plan；关键路径 RW1→RW2→RW3→RW4→RW5 串行，RW6 并行窗，RW7 延后。

---

## 11. Final recommendation

- **推荐序列**：先关 **G-RW-1/G-RW-2**（embedding 路线 + LLM 厂商）→ proposed sizing → 走 **RW1（keystone 接口/开关）→ RW2（mock+样本）→ RW3（prompt 载入）→ RW4（mock 使用链 capstone，先红后绿）**，**在不花一分钱、不打外网的前提下把整条使用链真实验证通**；再凭 **G-RW-5/G-RW-6** 授权进 **RW5（live）**。RW6（PDF）按 G-RW-3 决定是否并行，RW7（vec0）倾向延后生产化。
- **一句话总结**：real-wire 不是推翻 first-fixes，而是**沿已留接口把"语义为空的骨架"接成"语义真实的 RAG"——mock 先验使用链、开关切 live、接口隔离、零配置零计费默认**，把上一轮我自己犯的"mock 绿=能力通"假绿，用"使用链真发生 + live owner 复核"的证据彻底纠正。

---

## 14. 交叉引用与修订历史

- **交叉引用**：`state-analysis-after-FF7-by-opus.md`（缺口来源）、`first-fixes/initial-planning-by-opus.md`（格式骨架）、`owner-gated-qna.md`（[Q1][Q2][Q3] 扩展基线）、`tools/scripts/check_assert_strength.py`（防假绿门禁复用）。

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-01 | Opus 4.8 | 初稿（stage=initial）：real-wire 七 phase first-cut + 6 OPEN gate + DAG + 风险；冻结零决策 |
