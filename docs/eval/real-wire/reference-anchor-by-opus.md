# real-wire 参考锚定（reference-anchor，by Opus 4.8）

> **对象**：`real-wire 阶段 4 簇（RW-A provider 基座 / RW-B prompt 语义链 / RW-C live / RW-D PDF+vec0）的参考锚定`
> **日期**：`2026-06-01`
> **作者**：`Opus 4.8`（panel / sub-agents：4 个 Explore 子代理 fan-out，各调查一簇；承重锚点由作者亲自抽验）
> **文档性质**：`eval / reference-anchor`（provisional；冻结零决策，喂 design）
> **文档状态**：`draft`
> **上游权威输入**：
> - `docs/eval/real-wire/initial-planning-by-opus.md`（4 内聚 phase RW-A/B/C/D）
> - `docs/eval/real-wire/state-analysis-after-FF7-by-opus.md`（缺口 + mock/live 方案）
> - 代码：`legacy-family/**`（8 个 Cloudflare Workers TS 包，只读参照）+ 当前仓 HEAD（Python）
> **下游消费者**：`real-wire design / proposed-planning` → 之后 `pre-charter-qna`（关 G-RW-* gate）

---

## 0. 如何读这份台账

### 0.1 Verdict 图例

| 符号 | 含义 |
|------|------|
| ✅ 借 | 机制与思路都可借，按 Python/SQLite/离线路线落地 |
| 🔶 部分 | 思路可借、机制需改造（见 §5 TR 过滤；多因 Cloudflare binding） |
| ⛔ 反例 | 不可借（Cloudflare 托管特有 / legacy 反模式），记为要避开的坑 |
| 🆕 净新 | 无参考可借，nano-agent 净新实现 |

### 0.2 置信分层

| 置信 | 含义 |
|------|------|
| `HEAD✓` | 当前仓 HEAD，作者已 grep/打开核对 |
| `legacy✓` | legacy-family（在仓内 TS），作者**亲自抽验过** path:line |
| `legacy~` | legacy-family，子代理定位、作者**未逐一打开**（§6 标 ⏳待核） |

### 0.3 主题轴

> 4 条轴 = initial-planning 的 4 内聚 phase：
> - **轴 A**：RW-A provider 基座（LLM/Embedder/VectorIndex 协议 + 工厂 + mock/live 开关 + 配置注入）
> - **轴 B**：RW-B prompt 驱动语义链（prompt 注册/schema/渲染/消费 + structurize/summary/clean 去桩）
> - **轴 C**：RW-C live 接线（真实 LLM/embedding 客户端 + 重试/错误分类/维度守卫 + 密钥）
> - **轴 D**：RW-D 输入面/索引扩展（PDF/二进制对象存储 + 真实 vec0 KNN）

> **横切 substrate 事实（决定大量 verdict）**：legacy 跑在 **Cloudflare Workers**——R2(对象存储 binding)、Vectorize(托管向量库)、Workers-AI(无 key 模型 binding)、AI Gateway(计费/路由)、Durable Objects(任务队列)、KV(prompt 正文存储)、Browser Rendering(PDF)。我方是 **Python + SQLite + 本地 FS + 离线无外网/无 ML 依赖、默认 mock**。**所有 Cloudflare binding 均 ⛔ 不可直采**，借的是其上的**算法/协议/流程思路**。

---

## 1. 逐主题轴锚定矩阵

### 1.A 轴 A — RW-A provider 基座

| 借鉴点 | 来源（path:line）| 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-----------------|----------|---------|------|--------------------|
| `IAiProvider` 双方法协议 `generateText/generateJson → {responseText, usage}` | `legacy/smind-skill-rag-constructor/cloudflare_ai/ai_schemas.ts:170-179` | rag-constructor | ✅ | legacy✓ | 借**协议形状**：我方 `LLMProvider` Protocol(`complete`/`complete_json`→{text,usage})；不借 TS `Env` 注入风格 |
| `Embedder` 协议（name/dimension/embed）| `packages/rag_vectorizer/.../embedder.py:28-35` | HEAD | ✅ | HEAD✓ | 已就位；`LLMProvider`/`VectorIndex` 照此 Protocol 范式 |
| `VectorIndex` 协议 + `BruteForceVectorIndex` | `packages/vector_sqlite_vec/.../vector_index.py:22-96` | HEAD | ✅ | HEAD✓ | 已就位；mock/live 同接口、局部替换的范本 |
| `LocalEmbedder`(确定性哈希) 作 mock/默认 | `embedder.py:66-92` | HEAD | ✅ | HEAD✓ | 直接当 **mock embedding** + 离线默认；非语义(已知) |
| `ProviderRegistry`(register/handler_for_uri) | `packages/providers_dedicated/.../service.py:114-151` | HEAD | ✅ | HEAD✓ | **已验证可用的工厂范式**，复制为 `LLMProviderRegistry`/embedder 工厂 |
| MODEL_CONFIG（alias→{modelId, 默认参数}）| `legacy/.../cloudflare_ai/providers/gemini.ts:61-86` | rag-constructor | 🔶 | legacy✓ | 借**模型档位表思路**→ Settings/provider_configs；不借 TS 字面 |
| `Settings`(pydantic, env_prefix=SMIND_) 扩展 | `packages/config/.../settings.py:1-11` | HEAD | 🔶 | HEAD✓ | 扩 provider/key/model 字段 + `env_file=".env"`；默认 mock/local/bruteforce |
| `load_settings()@lru_cache` 工厂落点 | `packages/config/.../loader.py:1-9` | HEAD | ✅ | HEAD✓ | 加 `make_llm/make_embedder/make_vector_index` |
| **注入点（必须改工厂注入）** | `search.py:42`、`workflow_rag/service.py:186,243,263`、`apps/api/deps.py:114-128`、`worker/main.py:30,59` | HEAD | ✅ | HEAD✓ | 写/查取**同一 embedder 实例**（⛔3）；全列入 RWA-04 |

### 1.B 轴 B — RW-B prompt 驱动语义链

| 借鉴点 | 来源（path:line）| 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-----------------|----------|---------|------|--------------------|
| **prompt KEY 注册表** `PROMPT_REGISTRY`（别名→KV key）| `legacy/smind-skill-rag-structurizer/core/kv.ts:43-51` | structurizer | ✅ | legacy✓ | 借 **key 分类法**→ `prompt_versions` 表行；不借 KV 存储 |
| `getPrompt(kv, key)` 双模式(静态注册/动态直通) + fail-fast | `.../core/kv.ts:100-117` | structurizer | 🔶 | legacy✓ | 借**取 prompt+缺失即 fail** 思路 → `get_active_prompt`(已存读取器) + 渲染；KV→DB+本地模板 |
| **prompt 正文（系统指令文本）** | ❌ **不在 repo**——经 `getPrompt(env.PROMPT_KV, key)` 从 Cloudflare KV 取（`structurizer/gemini.ts:167,294`）| (KV, 外部) | 🆕 | legacy✓ | **正文须从 KV/owner 取**；repo 仅有 key+schema+用法 → 见 §3 净新 |
| 结构化输出 schema `StructuredJsonOutputSchema`(context_meta + layered_content + 强制 llm_summary)| `legacy/.../core/schemas_common.ts:135-154` | structurizer | ✅ | legacy~ | 借 **输出 schema 形状** → pydantic 校验 LLM 响应；llm_summary 必返指令需在 prompt 复述 |
| 摘要 block-0 剥离启发式(`totalBlocks>1` 剥 body 省 token + 回填) | `legacy/.../services/summarizer.ts:194` 区 | constructor | 🔶 | legacy~ | 借**省 token 启发式**；Python 端重写 |
| context_meta 防御性回填(LLM 漏返则用输入回填) | `summarizer.ts:260` 区 | constructor | ✅ | legacy~ | 借**响应校验层回填**思路 |
| AI 调用结构(systemInstruction + contents + thinkingConfig) | `legacy/.../providers/gemini.ts:294-317` | structurizer | 🔶 | legacy✓ | 借**system/user 分离 + 参数透传**；Gemini schema 特有，按 provider 重映射 |
| **HEAD 去桩落点** | `rag_structurizer/service.py:30-71`(structurize)、`rag_constructor/service.py:64-97`(summary)、`workflow_clean/action_registry.py:72-99`(clean/gemini degraded)、`config_repo.py:31-49`(get_active_prompt 孤立)、`prompt_versions` DDL | HEAD | ✅ | HEAD✓ | LLM 模式走 prompt→render→provider，规则化保留 fallback |

### 1.C 轴 C — RW-C live 接线

| 借鉴点 | 来源（path:line）| 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-----------------|----------|---------|------|--------------------|
| 指数退避重试 `MAX_RETRIES=3 / INITIAL_DELAY=1s / BACKOFF=2` | `legacy/smind-skill-rag-vectorizer/vectorizer/embedder.ts:40-42,115-164` | vectorizer | ✅ | legacy✓ | **算法可直采**为 Python `time.sleep` 退避循环 |
| 错误分类 `isRetryableError`(429/timeout/overload/connection→可重试)| `.../vectorizer/embedder.ts:73-79` | vectorizer | ✅ | legacy✓ | **启发式可直采**；区分可重试 vs 401/422 不可重试 |
| 模型参数默认(temperature 0.2/0.5/0.8、thinkingBudget) | `legacy/.../providers/gemini.ts:61-86` | rag-constructor | 🔶 | legacy✓ | 借默认值表；按 provider(Gemini/Claude/OpenAI)重映射请求体 |
| HTTP 错误处理(检查 !ok + 取 body/status + 抛分类异常) | `legacy/.../cloudflare_ai/ai_gateway.ts:128-182` | rag-constructor | 🔶 | legacy~ | 借**状态/响应体提取**→ Python httpx；AI Gateway 路由本身不借 |
| **维度守卫** `if len(out)!=DIMENSION: raise` | `packages/rag_vectorizer/.../embedder.py:82-83` | HEAD | ✅ | HEAD✓ | 借并**泛化为 `!= self.dimension`**；live embedding ≠1536 即 fail-loud |
| 写/查 model 名过滤(防跨模型 cosine) | `packages/rag_vectorizer/.../search.py:40-49` | HEAD | ✅ | HEAD✓ | live 必须保留：按 `embedding_model` 过滤 |
| 维度硬约束位置(改造前须知) | `vec.sql:22,43`(CHECK=1536)、`store.py` INSERT 字面 1536、`schema.py:34`(vec0 float[1536]) | HEAD | ⛔/🔶 | HEAD✓ | 若 live 选 ≠1536 模型须迁 schema；**倾向 G-RW-1 锁 1536 不迁** |
| API key 轮转(逗号分隔多 key + 模块级 round-robin) | `legacy/.../providers/gemini.ts:96-132` | rag-constructor | 🔶 | legacy✓ | 借**多 key 轮转思路**；不借模块级闭包状态 → 构造注入(见 §2) |
| Workers-AI binding(env.AI 无 key) / AI Gateway / wrangler secret | `legacy/.../wrangler.toml` | 全部 | ⛔ | legacy~ | **不可直采**；我方走显式 API key(.env) + httpx 或本地 sentence-transformers |

### 1.D 轴 D — RW-D 输入面/索引扩展

| 借鉴点 | 来源（path:line）| 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-----------------|----------|---------|------|--------------------|
| R2 put 多态签名(Stream/ArrayBuffer/Uint8Array/string + contentType) | `legacy/smind-skill-clean-universal/core/r2.ts:117-154` | clean-universal | 🔶 | legacy✓ | 借**二进制+MIME 签名思路**→ `FileSystemObjectStore.put_bytes/get_bytes`(temp+os.replace 原子)；R2 binding 不借 |
| 文件上传状态机 initiate→confirm | `apps/api/.../routes/ingestion.py:46-73` + `ingestion/service.py` | HEAD | ✅ | HEAD✓ | 复用；扩 `content:str`→ 支持 bytes(base64/multipart) + mime_type 贯穿 |
| PDF 抽取管道(fetch→存 raw→AI Vision 理解) | `legacy/.../services/cleaner_web.ts:142-207`、`cleaner_doc.ts:115-122` | clean-universal | ⛔ | legacy~ | **Browser Rendering + Workers-AI Vision 不可借**；改本地 PDF 库(pypdf/pdfminer) → 见 §3 净新 |
| upsert rowid 不变量(显式>复用>MAX+1 单调 + 软删保留) | `packages/vector_sqlite_vec/.../store.py:18-108` | HEAD | ✅ | HEAD✓ | 已就位；接 vec0 时在虚表层复核不变量 |
| 多级过滤 search(team→namespace→model + metric 读配置) | `packages/vector_sqlite_vec/.../store.py:110-150` | HEAD | ✅ | HEAD✓ | 已就位；vec0 KNN 后仍套此过滤 |
| vec0 退化+迁移表(fail-loud + reason + `vec_schema_migrations`) | `packages/vector_sqlite_vec/.../schema.py:31-81` | HEAD | ✅ | HEAD✓ | 真实 vec0 = 反向：扩展可载时虚表替 TEXT，接口不变 |
| Vectorize/Durable Objects(托管向量库+任务队列) | `legacy/smind-skill-rag-vectorizer/src/vectorizer_do.ts`、`core/vector_db.ts` | vectorizer | ⛔ | legacy~ | **托管 binding 不可借**；我方 sqlite-vec + 现有 worker 轮询(F3 内核) |
| 上下文头注入 `buildContentFull`(meta 前缀 + `---` 分隔 → 提升检索相关性) | `legacy/smind-skill-rag-constructor/services/recorder.ts:70-95` | constructor | ✅ | legacy~ | 借**元数据前缀**思路；HEAD 已有 `with_context_header`(F6b)，可对齐增强 |

---

## 2. 反例坑表（⛔）

| 反例 | 来源 | 为什么不可借 | 我们怎么做 |
|------|------|--------------|------------|
| Cloudflare binding 全家桶(R2/Vectorize/Workers-AI/AI Gateway/DO/KV/Browser) | `legacy/**/wrangler.toml` + 各 binding 调用 | 平台托管特有，Python 离线无对应；无显式 key | 显式 API key(.env) + httpx / 本地 FS / sqlite-vec / F3 worker；逐项重映射(§5) |
| API key 模块级闭包轮转 `getApiKey()`(全局可变 index) | `legacy/.../providers/gemini.ts:96-132` | 全局可变状态难测、与依赖注入冲突 | **构造注入** `LLMProvider(api_keys=[...])`，工厂传入；轮转封装在 provider 实例内 |
| provider 硬编码无开关(只 Gemini) | `legacy/.../wrangler.toml`(GEMINI_* 写死) | 无 mock/live 切换、不可测离线 | `Settings.*_provider` 枚举 + 工厂分发；**默认 mock/local** |
| embedding 维度硬编码 1536(CHECK + INSERT 字面 + vec0 float[1536]) | `vec.sql:22,43`、`store.py`、`schema.py:34` | live 选 ≠1536 模型即撞 schema | **G-RW-1 锁 1536**(倾向)；若必须改则 schema 迁移单列 migration |
| PDF 走 Browser Rendering + Workers-AI Vision | `legacy/.../cleaner_web.ts:142-207` | 托管渲染/视觉模型不可得 | 本地 PDF 解析库(pypdf/pdfminer)；Vision 理解延后(无本地多模态) |
| clean-dedicated-apis 纯规则 ETL 当"AI 清洗" | `legacy/smind-skill-clean-dedicated-apis/services/action_registry.ts:60-106` | 无 prompt、非 LLM（[Q3] 已 degraded）| 保持规则化(已有 chinatax ETL)，不冒充 AI |

---

## 3. 净新表（🆕）

| 净新点 | 为什么无参考 | 落点（phase）|
|--------|--------------|--------------|
| **prompt 正文模板**(系统指令文本) | legacy 正文在 Cloudflare KV、**不在 repo**；repo 仅 key+schema+用法 | RW-B：从 KV/owner 取正文，或据 schema+用法**重写**模板（G-RW-2 决定原样迁 vs 重写）|
| `MockLLMProvider`(确定性响应注入) | legacy 无 mock 层（直连 Workers-AI）| RW-A：读 `llm_responses.json`，未命中 fail-loud |
| 本地 PDF 解析器 + browserPDF 去 degraded | legacy 用托管渲染/Vision；本地无 | RW-D：pypdf/pdfminer(依赖待 G-RW-3)|
| `put_bytes/get_bytes` + 二进制上传端点 + MIME 贯穿 | HEAD ObjectStore 仅文本；legacy 是 R2 binding | RW-D：扩 `FileSystemObjectStore`(沿用 `_resolve_safe`)|
| 真实 `Embedder`(本地 sentence-transformers 或外部 API) | 离线无 ML 依赖；legacy 是 Workers-AI | RW-C：新增实现 + 维度守卫(G-RW-1)|
| 真实 `LLMProvider`(厂商 SDK/httpx + 退避/分类/预算) | legacy 是 Workers-AI binding 不可移 | RW-C：借退避/分类**算法**，客户端净新(G-RW-2)|
| `Vec0VectorIndex`(sqlite-vec 扩展加载) | legacy 是 Vectorize 托管 | RW-D：接口已留口，实现净新(G-RW-4，倾向延后)|

---

## 4. Web 来源台账

> 本次调查**无 web 来源**（全部锚点落在仓内：legacy-family TS + 当前 HEAD Python）。N/A。

---

## 5. Substrate-fit / 技术路线（TR）过滤复核（核心价值段）

> TR 红线（继承 first-fixes + real-wire initial §4）：TR-1 接口隔离(mock/live 同协议)；TR-2 维度=1536 不动 schema；TR-3 写/查同 embedder；TR-4 degraded/失败 fail-loud+reason；TR-5 密钥不进仓/日志、测试默认不打外网；TR-6 离线无 ML/无 Cloudflare binding。

| 借鉴点 | 原机制（Cloudflare/legacy）| 与 TR 是否冲突 | 过滤后落地形态 |
|--------|------------------------------|------------------|------------------|
| IAiProvider 协议 | TS interface + `Env` 注入 | TR-1 兼容 | Python `LLMProvider` Protocol + 工厂注入(直采思路) |
| MODEL_CONFIG/参数默认 | 字面表 + Workers-AI 模型 | TR-6 冲突(模型不可得) | 借**参数默认值**，模型走外部 API/本地(降级) |
| 退避重试 + 错误分类 | TS 循环 + msg 启发式 | 全兼容 | **直采**为 Python 实现 |
| prompt KEY 注册表 | TS `PROMPT_REGISTRY` + KV 取正文 | TR-6 冲突(KV 不可得) | key 分类法→`prompt_versions` 表；正文 KV→DB+本地模板(正文净新) |
| 输出 schema(Zod) | Zod 运行时校验 | TR-1 兼容 | 映射 pydantic/dataclass 校验 LLM 响应 |
| R2 put 二进制 | R2 bucket binding | TR-6 冲突(binding) | `put_bytes`(本地 FS + 原子写 + `_resolve_safe`)(重映射) |
| PDF Browser Rendering + Vision | Cloudflare 托管 | TR-6 冲突 | 本地 PDF 库(净新)；多模态 Vision 延后 |
| Vectorize/DO 队列 | 托管向量库 + Durable Objects | TR-6 冲突 | sqlite-vec(vec0) + F3 worker 轮询(已有)(重映射) |
| API key 轮转 | 模块级全局状态 | TR-5 部分冲突(可测性) | 构造注入 + 实例内轮转(降级反模式) |
| 维度硬编码 1536 | DDL CHECK + 字面 | TR-2 = **守住**(不改) | 锁 1536(G-RW-1)；adapter 边界 fail-loud |
| 写/查同 embedder + model 过滤 | HEAD 已有 | TR-3 = **守住** | live 保留 |

- **substrate-fit 总结（对 HEAD）**：real-wire 可借的几乎都是**协议形状 + 算法/流程思路 + 输出 schema**（IAiProvider、退避/错误分类、prompt key 分类法、输出 schema、上下文头注入、rowid 不变量、多级过滤）；**所有 Cloudflare 托管 binding（R2/Vectorize/Workers-AI/AI Gateway/DO/KV/Browser）一律重映射或净新**。最大的诚实风险点：**(1) prompt 正文不在 repo**（KV 外部）→ RW-B 需正文来源决策(G-RW-2)；**(2) 维度=1536** 必须守住或单列 schema 迁移(G-RW-1)。HEAD 已留的 `Embedder`/`VectorIndex` 协议 + `ProviderRegistry` 范式 + `get_active_prompt` 读取器，是 4 簇接线的现成挂载点。

---

## 6. 核验记录

| 锚点 | 是否核验 | 核验方式 | 备注 |
|------|----------|----------|------|
| `ai_schemas.ts:170-179` IAiProvider | ✅ 已核 | 作者 grep 打开 | 双方法协议确认 |
| `gemini.ts:61-96` MODEL_CONFIG/PROMPT_MAPPING/thinkingBudget | ✅ 已核 | 作者 grep | 确认 |
| `embedder.ts:40-164` 退避/isRetryableError/重试循环 | ✅ 已核 | 作者 grep | 确认 |
| `r2.ts:117-154` put 多态二进制签名 | ✅ 已核 | 作者 grep | 确认 |
| `structurizer/core/kv.ts:43-117` PROMPT_REGISTRY/getPrompt + `gemini.ts:167,294` | ✅ 已核 | 作者 grep | **确认 prompt 正文经 KV 取、不在 repo** |
| HEAD 注入点(search/workflow_rag/deps/worker)、Embedder/VectorIndex/ProviderRegistry 协议、settings/loader、vec.sql 维度、ObjectStore 仅文本、ingestion 端点 | ✅ 已核 | 本会话多轮 grep/读 | first-fixes 期已反复核 |
| 结构化/摘要 schema(`schemas_common.ts`)、summarizer block-0 剥离/回填、recorder buildContentFull、vectorizer engine/DO、cleaner PDF 流程 | ⏳ 待核 | 子代理定位、作者未逐一打开 | 行号近似，design 期开工前 pin |

---

## 附录

### A. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-06-01 | Opus 4.8 | 初稿：4 Explore 子代理 fan-out 调查 legacy-family + HEAD，按轴 A/B/C/D 落锚定矩阵 + 反例 + 净新 + TR 过滤；承重锚点亲验；**关键发现：legacy prompt 正文在 KV 不在 repo** |
