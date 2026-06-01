# smind-family · first-fixes 后真实接线（real-wire）状态分析

> **对象**：`after FF-F7（first-fixes F1–F7 全收口 + 跨阶段审查修复）`
> **日期**：`2026-06-01`
> **作者**：`Opus 4.8`（panel：none）
> **文档性质**：`eval / state-analysis`（本文是现状快照 + 前瞻交接；不是 closure / verdict / charter）
> **文档状态**：`draft`
> **对照基线**：`docs/eval/first-code-review-plan/part-cr-1~8.md（八簇审查）+ docs/design/first-fixes/owner-gated-qna.md（[Q1]-[Q7] 冻结裁决）`
> **上游权威输入**：
> - `docs/closure/first-fixes/FF-F1~F7-closure.md + FF-REVIEW-fixes-closure.md`
> - 代码核：`packages/rag_vectorizer/embedder.py`、`workflow_clean/*`、`workflow_rag/*`、`config/config_repo.py`、`auth/service.py`、`smind_common/net.py`；测试核：`tests/`（234 passed + 1 xfailed）
> **下游消费者**：`owner 决策（是否启动 real-wire 轮：LLM/embedding/prompt/PDF 真实接入）`

---

## 0. 水位 / 健康一句话（TL;DR）

- **一句话现状**：**内核与管道（编排/事务/幂等/安全/检索去重/测试有效性）真实可用且经测试**；但**承载 RAG 价值的四大件——真实文档进入、prompt 载入与使用、LLM 推理、真实语义 embedding——本轮一件都没接，连 mock 都没有**。
- **核心结论**：mock 测试验证的是**水管骨架 + 桩级实现**（HTTP 抓取被注入硬编码字符串、embedding 是哈希、清洗/结构化是规则、无 LLM、无 prompt、无真实样本语料）。说"链路通"只对"骨架流转"成立，对"RAG 能力"是 **over-claim**——本文据实纠偏，并给出 mock 补全与 live-wiring 的可执行方案。

---

## 1. 方法与对照基线

- **对照基线**：first-fixes 的 owner 冻结裁决 [Q1]-[Q7]（vec0/embedding/去桩范围/restart/认证/PBKDF2/test-first）+ 八簇审查发现。
- **证据来源**：全仓 grep（LLM/模型/prompt 消费点）+ 代码逐读（embedder/clean/rag/config）+ `pytest tests/`（234 passed + 1 xfailed）+ `check_assert_strength.py`（47 文件 0 仅弱断言）。复现命令见附录 A。
- **可采信证据**：commit + 测试名 + grep 命中数（四元组口径）；**mock 绿不作为"能力已验证"的证据**（part-cr-8 计数≠价值教训）。

---

## 2. 回看清单（交付快照）

### 2.1 交付价值台账（已完成什么）

| 单元 | 声称交付 | 真实落地（代码核） | 评级 | 锚点 |
|------|----------|--------------------|------|------|
| F1 时间/事务基座 | 时间 SSOT + 显式 BEGIN IMMEDIATE | 真实：`utc_now_iso`/`add_seconds_iso` 3位毫秒；多写 helper 包事务 | delivered | `common/time.py` |
| F2 连接/装配 | 生成器依赖/lifespan/CORS/异常映射/healthz | 真实 | delivered | `api/deps.py`,`app_support.py` |
| F3 内核恢复+执行器契约 | reap/ExecutorResult/确定性幂等/recovery restart | 真实（at-most-once 经 test_t14 真实负 lease 路径证） | delivered | `workflow_core/executors.py,retry.py,restart.py` |
| F4 适配层安全+rowid | 路径遍历封堵/rowid 不变量/purge 清退 | 真实 | delivered | `storage_objects/filesystem_store.py`,`vector_sqlite_vec/store.py` |
| F5 向量"真实性"+检索 | 本地 1536 embedding + VectorIndex degraded + search 过滤 | **桩级**：embedding=md5 哈希词袋（**非模型**）；vec0=暴力 cosine | placeholder（语义层）/ delivered（接口与管道层） | `rag_vectorizer/embedder.py`,`vector_sqlite_vec/vector_index.py` |
| F6a clean 去桩 | action registry + htmlCrawl + chinatax + degraded | htmlCrawl/chinatax 真实(ETL/解析)；structurize 入口规则化；browser/PDF/LLM degraded | partial（file/url 真实，PDF/browser/LLM 不做） | `workflow_clean/*`,`cleaners_universal/*`,`providers_dedicated/*` |
| F6b rag 去桩 | structurize schema + 双通道 + 独立 vectorize | structurize/summary=**规则化非 LLM**；vectorize step 真实；embedding=哈希 | partial（结构真实，语义桩级） | `rag_structurizer/*`,`rag_constructor/*`,`workflow_rag/service.py` |
| F6c 认证/配置 | API key 认证 + PBKDF2 + 配置载体 | API key/PBKDF2 真实；`get_active_prompt/provider` **仅读取器、无消费方** | delivered（认证）/ placeholder（配置消费） | `auth/service.py`,`config/config_repo.py` |
| F7 测试有效性 | 原语/去夹具掩盖/capstone/断言门禁/closure 重定级 | 真实（门禁 47 文件 0 命中；去掩盖 grep 0） | delivered | `tests/fixtures/primitives.py`,`tools/scripts/check_assert_strength.py` |
| 审查修复 | M1 去重/M2 计数/M3 fail-loud/L1-L6 | 真实 | delivered | `FF-REVIEW-fixes-closure.md` |

### 2.2 Deferred / Carried-over 台账（每条带 reopen 触发器）

| 编号 | 项目 | 为什么 defer | reopen 触发器 | 携带至 |
|------|------|--------------|----------------|--------|
| D-01 | 真实 LLM 推理（清洗/理解/AI 摘要） | [Q3] 不追 legacy 全 AI 策略；离线无 key/网络 | 需要 AI 级文本处理质量 + 接受网络/计费 | real-wire 轮 |
| D-02 | 真实语义 embedding（神经/外部 API） | [Q2] 本地；离线无 sentence-transformers/key | 检索语义质量不达标 / 需同义性 | real-wire 轮 |
| D-03 | 真实 vec0（sqlite-vec KNN） | [Q1] degraded | 数据量增大暴力 cosine 成瓶颈 | 生产化轮 |
| D-04 | prompt 从 legacy-family 载入 + 渲染 + 使用 | 无 LLM 消费方；本轮仅建读取器 | LLM 接入时（D-01 同步） | real-wire 轮 |
| D-05 | PDF / 二进制文档进入 | [Q3] degraded；ObjectStore 仅文本 | 需 PDF 源 | real-wire / 生产化轮 |
| D-06 | 真实样本语料（非内联字符串） | 本轮 mock 用硬编码小串 | 要做有意义的端到端语义验证 | real-wire 轮（见 §7） |
| D-07 | 断言门禁接 CI runner | 本环境无 CI | 有 CI 平台 | 平台轮 |
| D-08 | htmlCrawl SSRF 的 DNS-rebinding 防护 | 本轮主机名级守卫 | 生产暴露外部 url 抓取 | 生产化轮 |
| D-09 | purge 跨库（core/vec/FS）最终一致性 | 跨 substrate 架构限制 | 生产一致性要求 | 生产化轮 |

---

## 3. 对账诚实（本 flavor 灵魂段）

| 声称 | 真实 | 偏差类型 | 证据 | 影响 |
|------|------|----------|------|------|
| "mock 链路跑通了" | 仅骨架/管道流转跑通；LLM/embedding/prompt/真实样本均不在回路 | **over-claim** | 见下表 §3-mock | 误导"RAG 能力已验证" |
| "产生向量 ✅" | embedding 是 `hashlib.md5` 词袋，非模型推理 | placeholder | `rag_vectorizer/embedder.py:66-93`（仅 import math/re/hashlib） | 检索只有词面相关，无语义 |
| "F5 向量真实性" | 真实的是接口与管道；向量本身是哈希 | over-claim（命名） | `embedder.py` name=`local-bow-hash-v1` | closure 已标 degraded，命名仍易误读 |
| "prompt 配置已接线（F6-09）" | 只建了 `get_active_prompt` 读取器，**0 消费方**、表空、无模板载入 | frozen≠done / placeholder | grep `get_active_prompt` 仅定义+导出+测试 | prompt 的"使用"完全未实现/未验证 |
| "structurize/construct 去桩" | 真去桩为**规则化**，非 legacy 的 LLM 策略 | under-claim 风险（需说明非 AI） | `rag_structurizer/service.py` 正则 | 质量 ≠ legacy AI 输出 |

**§3-mock —— mock 里到底有/没有**：

| 组件 | mock 中状态 | 验证程度 |
|------|-------------|----------|
| url 文档进入 | 注入**硬编码 HTML 字符串**（`monkeypatch cleaners_universal.service.fetch_url`） | 仅管道流转 |
| chinatax 进入 | 注入**硬编码 JSON 字符串**（`monkeypatch providers_dedicated.service.fetch_api`） | 仅管道流转 |
| PDF/二进制进入 | **无**（ObjectStore 仅 put_text/get_text） | 不支持 |
| 真实样本语料 | **无**（测试内联 `_HTML`/`_CONTENT` 小串，无 `tests/fixtures/samples/` 文件集） | 未验证 |
| Prompt 载入/渲染/使用 | **无** | 未验证 |
| LLM 推理 | **无（连 mock provider 都没有）** | 未验证 |
| Embedding 推理 | 哈希函数（非模型，无 mock provider） | 仅验证哈希会跑 |
| 内核/事务/幂等/安全/检索去重 | 真实代码 | **已验证** |

- **诚实结论**：234 passed 证明的是 **"水管 + 桩级实现"** 的正确性（这部分真实、有价值），**不**证明 RAG 产品能力。"mock 跑通"应被理解为"骨架在桩级组件下端到端流转通过"，而非"LLM/embedding/prompt 驱动的真实处理通过"。后者**尚未具备验证条件**（无 provider 接口、无样本、无 prompt 载入）。

---

## 4. 归因 / 缺口分析

| 现象 | 归因（根源/缝） | 根源位置 |
|------|------------------|----------|
| 无任何 LLM 推理 | [Q3] 冻结"不追 legacy 全 AI"+ 离线无 key/网络；本轮未建 LLM provider 抽象 | 无 `llm_provider` 模块 |
| embedding 非模型 | [Q2] 本地 + 离线无 ML 依赖；`Embedder` 接口已留口但只有哈希实现 | `rag_vectorizer/embedder.py` |
| prompt 不可用 | 只建读取器、未建"模板载入→渲染→provider 调用"消费链；无消费方 | `config/config_repo.py`（孤立读取器） |
| mock 不含真实样本 | 测试为单测/集成便利用内联串；无样本语料管理 | `tests/` 无 samples 资产 |
| 缺 mock/live 开关 | Settings 无 provider 选择字段；无 provider 工厂 | `config/settings.py` |

---

## 5. Verdict（价值-债务 / 达成度 / 健康评级）

| 维度 | 评级 | 一句话 |
|------|------|--------|
| 交付价值 | **中-高** | 内核/事务/安全/测试有效性是真实、扎实的地基 |
| 累积债务 | **中** | RAG 语义四大件（LLM/embedding/prompt/真实样本）全部 deferred，但接口留口、债务显式记账 |
| 愿景达成度（"能用的 RAG"） | **低** | 当前是"语义为空的骨架"，离可用 RAG 还差 real-wire 一整轮 |
| **综合健康** | **中（地基稳、上层空）** | 地基可信；不要把骨架当成品 |

- **反镀金提醒**：不要为了"看起来通"而在 mock 里塞假 LLM/假语义当真功能（重蹈 part-cr-8 假绿）；real-wire 必须以"先红后绿 + 真实 provider/样本"为证据，degraded 必须 fail-loud + reason。

---

## 6. 前瞻交接

- **下一周期建议**：启动 **real-wire 轮**，顺序：① 建 `Embedder`/`LLMProvider`/`VectorIndex` 的 **provider 工厂 + mock/live 开关**（先把"使用链"在 **mock provider** 下真实跑通——注入确定性响应，验证 prompt→render→provider→产物）；② 真实样本语料（§7）；③ prompt 从 legacy-family 载入 + digest 校验 + 渲染；④ 再接 live key（§8）；⑤ 最后 PDF/二进制与真实 vec0。
- **start-gate 前置（real-wire day-1 必须满足）**：
  - 确定 LLM/embedding 厂商（OpenAI / Gemini / Anthropic / 本地 sentence-transformers）→ 决定 [Q2] 子选项与维度（必须仍=1536 或同步改 schema）。
  - 提供 key 与计费授权（见 §8）。
  - 真实样本语料就位（见 §7）。
- **需 owner 拍板的问题**：
  - Q-RW1：embedding 走**本地神经模型**（sentence-transformers，需装依赖/算力）还是**外部 API**（需 key+网络+计费）？维度是否锁 1536？
  - Q-RW2：LLM 厂商与模型？prompt 是否原样迁移 legacy 模板，还是借此轮重写？
  - Q-RW3：是否本轮接 PDF（需二进制存储 + PDF 解析依赖）？

---

## 7. Mock 测试需要构建的全部资料（及 `.tmp/` 本地组织）

> 目标：让 mock 不再是"硬编码小串"，而是**真实样本 + 可注入的 mock provider**，使"文档进入 / prompt 使用 / LLM 调用 / embedding 推理"四条链在**不依赖外网/算力**下被真实验证。以下 `.tmp/` 为**本地、git-ignored** 的构建区（不进仓；仓内 `tests/fixtures/samples/` 放精简版可提交样本）。

### 7.1 需要构建的资料清单

| 资料 | 用途 | 形态 | 由谁消费 |
|------|------|------|----------|
| HTML 样本集 | url htmlCrawl 真实抽取（含 script/style/嵌套/实体/中英混排） | `.html` 文件 | `fetch_url` mock 注入 |
| 纯文本/markdown 文档样本 | file 源 structurize 分 section | `.md`/`.txt` | `file_confirm.content` |
| chinatax 响应样本 | dedicated provider ETL 解析 | `.json`（items 数组） | `fetch_api` mock 注入 |
| PDF 样本（待 D-05 解禁） | PDF 链路（本轮仅占位，xfail） | `.pdf` | 未来 PDF 解析器 |
| prompt 模板集 | prompt 载入/渲染（迁自 legacy-family） | `.txt`/`.md` 模板 + 变量占位 | `get_active_prompt` 消费链 |
| prompt_versions seed | 把模板登记进表（team/global） | `.sql`/seed 脚本 | `config_repo` |
| **mock LLM 响应集** | LLM "使用"链验证（prompt→响应确定性映射） | `.json`（prompt_key/hash → 响应） | `MockLLMProvider`（待建） |
| **mock embedding 响应集** | embedding 推理接入验证（文本→确定性向量） | 由 `LocalEmbedder` 充当 or `.json` | `Embedder`（mock 实现） |
| 期望断言集 | 每条样本的"应得"语义属性（命中/分差/字段） | `.json`（expectations） | 测试断言 |

### 7.2 `.tmp/` 本地组织（git-ignored 构建区）

```text
.tmp/                      # 本地构建区, 加入 .gitignore, 不提交
└── eval-fixtures/
    ├── samples/
    │   ├── html/          # url 抓取样本: 001-tax-policy.html, 002-noisy.html ...
    │   ├── docs/          # file 源: policy.md, plain.txt ...
    │   ├── chinatax/      # provider 样本: articles-001.json ...
    │   └── pdf/           # (D-05 解禁后) sample-001.pdf
    ├── prompts/           # 迁自 legacy-family 的模板
    │   ├── structurize.v1.txt
    │   ├── clean.v1.txt
    │   └── summarize.v1.txt
    ├── prompt_versions.seed.json   # {team_id, prompt_key, version, template_path, digest}
    ├── mock/
    │   ├── llm_responses.json      # {prompt_key|hash: canned_response}
    │   └── embeddings.json         # (可选) {text_hash: vector} 或留空走 LocalEmbedder
    └── expectations.json           # 每样本期望: {query, expected_top_chunk, min_margin, must_contain}
```

### 7.3 怎么构建（步骤，本地、离线）

1. **建目录 + 忽略**：`mkdir -p .tmp/eval-fixtures/{samples/{html,docs,chinatax,pdf},prompts,mock}`；在 `.gitignore` 加 `.tmp/`。
2. **填样本**：HTML/文本/JSON 手写或脚本生成；每条配 `expectations.json` 一项（这条样本检索应命中哪个 chunk、分差阈值、必含字段）——**期望先写（先红依据）**。
3. **迁 prompt**：从 `legacy-family/**/prompts` 拷模板到 `.tmp/eval-fixtures/prompts/`，算 sha256 digest 写入 `prompt_versions.seed.json`。
4. **mock provider 响应**：`llm_responses.json` 按 prompt_key 给确定性响应（如 structurize 模板 → 固定结构化 JSON）；embedding 默认复用 `LocalEmbedder`（确定性），需要更强时 `embeddings.json` 注入。
5. **测试装载**：新增 `tests/fixtures/eval_corpus.py` 读取 `SMIND_EVAL_FIXTURES_DIR`（默认 `.tmp/eval-fixtures`），把样本/prompt/mock 响应喂给测试；`fetch_url`/`fetch_api`/`MockLLMProvider`/`Embedder(mock)` 经 monkeypatch 或 provider 工厂（§8 的 `provider=mock`）注入。
6. **可提交精简版**：把每类 1-2 个最小样本放 `tests/fixtures/samples/`（进仓、供 CI），大集留 `.tmp/`（本地）。

> **纪律**：`.tmp/` 是构建/暂存区，**不得**作为唯一真相进仓；CI 必须能用 `tests/fixtures/samples/` 的精简集独立跑（否则 CI 假绿）。

---

## 8. Live-wiring：密钥准备 / `.env` / 接线 / mock↔live 开关

> ⚠️ **本节是目标设计（尚未实现）**。当前代码：`Settings`（`config/settings.py`）只有 `app_env/data_dir/core_db_path/vec_db_path/object_store_dir`，env 前缀 `SMIND_`，**无任何 provider/key 字段、无 provider 工厂、无 .env 加载**。以下为接线方案。

### 8.1 需要的密钥与依赖

| 能力 | live 方案 | 需要的密钥/依赖 |
|------|-----------|------------------|
| LLM 推理 | OpenAI / Gemini / Anthropic API | `*_API_KEY` + 网络 + 计费 |
| Embedding | 外部 API（OpenAI text-embedding-3 等）**或** 本地 sentence-transformers | API key+网络 **或** 模型权重(本地, 装 `sentence-transformers`/`torch`) |
| 向量索引 | sqlite-vec(vec0) | `sqlite_vec` 扩展(本地装载) |

### 8.2 密钥存放与 `.env`

- **存放**：项目根 `.env`（**必须 git-ignored**，加入 `.gitignore`）；CI/生产用平台 secret 注入环境变量，不落盘。**密钥绝不进仓、不进日志**（对齐 F6c ⛔1）。
- **`.env` 内容（提案）**：
  ```dotenv
  # ── 运行模式开关 ──
  SMIND_APP_ENV=local
  SMIND_LLM_PROVIDER=mock            # mock | openai | gemini | anthropic
  SMIND_EMBEDDING_PROVIDER=local-hash # local-hash | local-st | openai
  SMIND_VECTOR_BACKEND=bruteforce    # bruteforce | vec0
  # ── LLM live 凭据 (仅 provider!=mock 时需要) ──
  SMIND_LLM_API_KEY=sk-...
  SMIND_LLM_MODEL=gpt-4o-mini
  SMIND_LLM_BASE_URL=                # 可选, 自建网关
  # ── Embedding live 凭据 (仅 provider=openai 时需要) ──
  SMIND_EMBEDDING_API_KEY=sk-...
  SMIND_EMBEDDING_MODEL=text-embedding-3-small
  SMIND_EMBEDDING_DIM=1536           # 必须=1536 否则需同步改 vec schema
  # ── 样本/mock 资料 ──
  SMIND_EVAL_FIXTURES_DIR=.tmp/eval-fixtures
  ```
- **加载**：`Settings.model_config` 增 `env_file=".env"`（pydantic-settings 原生支持），新增上述字段（带默认值，默认全 mock/local，**测试与离线零配置可跑**）。

### 8.3 怎么 wire 到系统（接线点）

1. **provider 接口已留口**：`rag_vectorizer.Embedder`（协议）、`vector_sqlite_vec.VectorIndex`（协议）已存在；**需新建** `LLMProvider` 协议（`packages/llm_provider/`）。
2. **provider 工厂**（新建 `config/providers.py`）：按 Settings 选择实现——
   - `make_embedder(settings)` → `LocalEmbedder`(local-hash) / `SentenceTransformerEmbedder`(local-st) / `OpenAIEmbedder`(openai)。
   - `make_llm(settings)` → `MockLLMProvider`(mock, 读 `.tmp` 响应集) / `OpenAILLM` / `GeminiLLM` ...
   - `make_vector_index(settings)` → `BruteForceVectorIndex` / `Vec0VectorIndex`。
3. **注入**：`apps/*/deps.py` 与 worker 在装配处调工厂，替换现在硬编码的 `default_embedder()`；rag/clean 执行器从 deps 取 `embedder`/`llm`，**写/查共用同一 embedder**（保持 F5 ⛔3）。
4. **prompt 消费链**（接 D-04）：clean/structurize 执行器在 LLM 模式下 → `get_active_prompt(team,key)` → 载模板 → 渲染变量 → `llm.complete(prompt)` → 产物；degraded/mock 模式走规则化或 mock provider。
5. **维度守卫**：`OpenAIEmbedder` 维度≠1536 时 fail-loud（对齐 F5 adapter 边界）。

### 8.4 mock ↔ live 开关（参数控制）

- **单一开关来源 = 环境变量（`SMIND_*_PROVIDER` / `SMIND_VECTOR_BACKEND`）**，经 `Settings` 读入，provider 工厂据此选实现。
- **默认值 = 全 mock/local**：不配 `.env`、不给 key 时，系统**自动**走 `mock` LLM + `local-hash` embedding + `bruteforce` 向量——**测试与离线开发零配置、零计费、确定性**。
- **切 live**：在 `.env` 把对应 `*_PROVIDER` 改为 `openai`/`gemini`/`local-st`/`vec0` 并提供 key；**仅该实现替换，上层链路不变**（接口隔离的价值）。
- **测试强制 mock**：测试 fixture 固定 `SMIND_LLM_PROVIDER=mock` 等（或工厂在 `app_env=test` 时禁用 live），防止 CI 误打外部 API/产生计费（对齐 ⛔6 不打外网）。
- **CLI/运行时覆盖（可选）**：worker/CLI 加 `--llm-provider`/`--embedding-provider` 参数覆盖 env，便于一次性 live 验证。

---

## 附录

### A. 复现命令

```bash
cd /workspace/repo/smind-family
# 全量 + 门禁 + 防假绿
python3 -m pytest tests/ -q                              # 234 passed + 1 xfailed
python3 tools/scripts/check_assert_strength.py tests/    # 47 文件 0 命中
grep -rn "strftime.*lease_expires_at" tests/             # 0 (无夹具掩盖)
# 证"无 LLM / embedding 是哈希 / prompt 无消费"
grep -rniE "openai|gemini|anthropic|transformers|torch" packages/ apps/ --include=*.py | grep -v test   # 仅注释/degraded 文案
sed -n '66,93p' packages/rag_vectorizer/src/rag_vectorizer/embedder.py   # embed=md5 哈希词袋
grep -rn "get_active_prompt" packages/ apps/ --include=*.py | grep -v "config_repo\|__init__\|test"      # 0 消费方
# 证"无真实样本 / mock 用硬编码串"
grep -rn "_HTML\s*=\|_CONTENT\s*=\|_CHINATAX_JSON\s*=" tests/             # 内联硬编码样本
ls tests/fixtures/samples/ 2>/dev/null || echo "无样本语料目录"
# 证"配置无 provider/key 字段"
cat packages/config/src/smind_config/settings.py        # 仅 db/object/app_env, 无 provider/key
```

### B. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-01 | Opus 4.8 | 初稿：first-fixes 后 real-wire 状态分析；据实纠偏"mock 跑通"over-claim；给出 mock 资料 `.tmp/` 构建与 live-wiring 开关方案 |
