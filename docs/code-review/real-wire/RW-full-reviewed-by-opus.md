# Nano-Agent 代码审查 · real-wire RW-A/B/C/D 全阶段

> 审查对象: `real-wire 阶段全部执行代码（commits 4bdc30f / 1dcf5b3 / fec0bb3 / ae8d3cf）`
> 审查类型: `mixed（code-review + closure-review + qna 对账）`
> 审查时间: `2026-06-01`
> 审查人: `Opus 4.8（独立复核轮 — 不复用 RW-cross-stage-review 结论，全部重验）`
> 审查范围:
> - `packages/provider_runtime/*`（协议/工厂/mock/retry/real_provider）
> - `packages/vector_sqlite_vec/*`（store / vector_index / schema / vec.sql）
> - `packages/config/*`（settings / prompt_renderer）
> - `packages/{workflow_rag,workflow_clean,rag_structurizer,rag_constructor,management,rag_vectorizer}/*`（装配/去桩/搜索）
> - `prompts/*.md`、`tests/e2e/test_real_wire_mock_capstone.py`、`tests/unit/test_rw_{a,b,c,d}_*.py`、`tests/fixtures/primitives.py`
> 对照真相:
> - `docs/eval/real-wire/pre-charter-qna.md`（frozen，最高口径，Q-RW-1..7 + reframe）
> - `docs/eval/real-wire/final-execution-plan-by-opus.md`（frozen，RWA-01..09 / RWB-01..08 台账）
> - `docs/closure/real-wire/RW-{A,B,C,D}-closure.md` + `RW-cross-stage-review.md`（被审查的 claim）
> 文档状态: `reviewed`

---

## 0. 总结结论

- **整体判断**：`RW-A/B/C/D 主体成立——四阶段无越界、279 passed 真实可复现、qna 7 题方向性一致、deferred 项诚实标注；但本轮把「脚手架 / 隔离实现」按 verified ✅ 收口的同时，对「这些实现在生产路径上不可达」披露不足——尤其 vec0 整条栈（工厂槽 + Vec0VectorIndex + 持久表）当前对生产 store 零可达，且向 macOS 的 handoff 暗含一个会触发数据库读写崩坏的地雷。`
- **结论等级**：`approve-with-followups`
- **是否允许关闭本轮 review**：`yes`（本轮 scope = mock+占位+接口+路由+测 mock，已达成；下列 follow-up 不属本轮交付承诺，但必须在 provider/macOS 轮**进入前**消化，否则 handoff 会假成立）
- **本轮最关键的 1-3 个判断**：
  1. **vec0 是「隔离脚手架」而非「可被接线的实现」**：`make_vector_index` 在业务码 **0 调用方**，`Settings.vector_index` 是死配置，`store.search` 硬编码 `BruteForceVectorIndex`，`Vec0VectorIndex` 自建 `:memory:` 连接、与持久层零关系。RW-D 把它收口为 ✅（scaffolding）尚可，但 verdict 行「交付真实 sqlite-vec KNN」+ cross-review 把它降格为「1 处 footgun」**双双低估了不可达范围**（R1）。
  2. **持久 `chunk_embedding_index` 存在「vec0 schema ↔ JSON 文本读写」的潜在错配地雷**：vec.sql 声明它为 `vec0(embedding float[1024])`，但 `store.py` 用 `json.dumps/json.loads` 读写——仅在 schema 降级为 TEXT 表时自洽。全仓**无任何代码把 sqlite-vec 扩展载入 store 连接**，故真实 vec0 表从不被实例化（永远降级）。一旦 macOS 轮按 handoff「装 sqlite-vec」并把扩展接进 store 连接，`CREATE VIRTUAL TABLE` 成功→store 的 JSON 读写即崩（R2）。
  3. **生产 `semantic_mode=llm` 全链路 0 端到端测试**：mock capstone **绕过**了 executor（`process_rag_step`）与 `SearchService`，手工拼 `structurize_via_llm/summarize_via_llm/store` 直调，且**完全省略 clean step**——比 final-plan §8 自述的 capstone（D clean→E structurize→F construct via pipeline）窄。dispatch 包装器有单测，但「executor 在 llm 模式下」无任何测试（R3）。

---

## 1. 审查方法与已核实事实

- **对照文档**：`pre-charter-qna.md`（frozen）、`final-execution-plan-by-opus.md`（frozen §2.C/§6/§8）、4 份 closure + cross-stage-review。
- **核查实现**：上列 §0 范围全部文件逐行读取。
- **执行过的验证（本人实跑，非引用 closure）**：
  - `python3 -m pytest -p no:cacheprovider` → **`279 passed, 2 skipped, 1 xfailed`**（与 closure 一致）。
  - `python3 tools/scripts/check_assert_strength.py` → **`52 文件, 0 个仅弱断言`**（与 closure 一致）。
  - `grep -rn 1536 packages apps tests --include=*.py --include=*.sql` → **仅 6 条迁移历史注释，0 生效字面**（与 closure 一致）。
  - `grep make_vector_index / make_embedder / make_llm / retry_with_backoff / BruteForceVectorIndex` 全仓调用图。
  - `grep enable_load_extension / sqlite_vec.load / load_extension`（store 连接侧）→ **0 命中**（关键事实，见 R2）。
- **复用 / 对照的既有审查**：`RW-cross-stage-review.md` — **仅作线索**，其 X1 footgun 经本轮独立复核后判定为**低估**（升级为 R1/R2）；其余 X2..X5 采纳。4 份 closure 的 ✅ claim 逐条反向核对（见 §3）。

### 1.1 已确认的正面事实

- **1024 迁移真实且全库自洽**：`vec.sql` 双 CHECK=1024 + vec0 `float[1024]`；`store.EMBEDDING_DIMENSION=1024` + 写侧维度漂移守卫 fail-loud（`store.py:37-41`）；`rag_vectorizer.DIMENSION=1024`；跨包不变量有测试守。grep 0 生效 1536。**独立复核：成立。**
- **provider 基座契约真实**：`LLMProvider` Protocol（`protocols.py:23-33`）；工厂按 Settings 选、未知 `UnknownProviderError`、外部厂商 `NotImplementedError` 占位、mlx 槽构造 ok（`factory.py`）；`MockLLMProvider` 未命中 `MockResponseMissing` fail-loud、`complete_json` 校验合法 JSON（`mock_llm.py:56-74`）。**成立。**
- **写/查同 embedder 名（TR-3）成立**：写侧 `workflow_rag/service.py:294 embedding_model=embedder.name`，查侧 `search.py:52 embedding_model=embedder.name`，两侧均经 `make_embedder(load_settings())` → 同 `local-bow-hash-v1`。**独立复核：embedding_model 维度一致。**
- **prompt digest 对账真实 fail-loud**：`prompt_renderer.render_prompt` 读文件算 digest，与 SQLite `template_digest` 不等即 `PromptError(prompt_digest_mismatch)`，**无静默用文件分支**；`prompt_versions` 复用既有表，**无 schema 改**。**成立。**
- **三段去桩真实接 provider 且留 fallback**：`structurize_via_llm`→`complete_json`+`_normalize_structured`+非法 JSON fail-loud；`summarize_via_llm`→`complete`+空回落 `build_summary`；clean `geminiUnderstanding`→`complete`，`llm=None` 时 `register_degraded`。默认 `semantic_mode=rule` 零回归。**成立。**
- **治理面成立**：`redact_secret` + `RealMLXLLMProvider.__repr__` 脱敏（key 不入 repr）；`api_keys` 实例内持有（非模块级全局，规避 `gemini.ts:96-132` 反例）；retry 错误分类（429/5xx 重试、401/422 立即抛、默认保守）逻辑正确。`.env` git-ignored + `.env.example` 占位。
- **防假绿原语真实**：`SpyEmbedder/SpyLLMProvider` 计数 + `assert_used_real_chain(min_calls=2)` 在 capstone 证明 provider/embedder 被真调。
- **无越界**：PDF（RWD-01/02/03）未碰、外部厂商 client 未实装——与 Q-RW-4 / reframe 一致。

### 1.2 已确认的负面事实

- `make_vector_index` 业务码 **0 调用方**；`Settings.vector_index` 从不被 store 读取；`store.search:160` 硬编码 `BruteForceVectorIndex`。→ vec0 选型对生产**完全无效**（R1）。
- 全仓**无任何代码**把 sqlite-vec 扩展载入 store/核心连接；持久 `chunk_embedding_index` 永远降级为 TEXT 表，`store.py` 的 `json.dumps/json.loads` 仅在该降级态自洽；真实 vec0 表从未被实例化（R2）。
- `retry_with_backoff` 业务码 **0 调用方**；`RealMLX*` 占位**未**用它包裹（R5，本轮可接受但 closure 表述为已交付能力）。
- mock capstone **不经** `process_rag_step` / `process_clean_step` / `SearchService`，且无 clean step；无任何测试在 executor 层跑 `semantic_mode=llm`（R3）。
- `SearchService` 从不向 `store.search` 传 `namespace_id` → 查询跨命名空间、`_resolve_metric(None)` 强制 cosine，绕过 namespace 级 `distance_metric` 配置（R6，pre-existing F5 设计）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | yes | §0 范围全部逐行读取 |
| 本地命令 / 测试 | yes | pytest 279 passed、门禁 0 弱、grep 调用图，均本人实跑 |
| schema / contract 反向校验 | yes | vec.sql CHECK / vec0 声明 ↔ store 读写格式反向比对（R2 根因）|
| live / deploy / preview 证据 | n/a | 真实 MLX / 真实 vec0 本环境不可跑（离线 Linux，无扩展/无 Apple Silicon）——与 closure 一致 |
| 与上游 design / QNA 对账 | yes | Q-RW-1..7 + reframe + final §2.C/§6/§8 逐项 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | vec0 整条栈是隔离脚手架、对生产 store 零可达（cross-review 低估为「footgun」）| high | delivery-gap / scope-drift | no（本轮 scope 内）| 升级 carry-over 描述；macOS 轮前接 store + 补集成测 |
| R2 | 持久 `chunk_embedding_index`：vec0 schema ↔ JSON 文本读写错配地雷；装扩展即崩 | high | correctness（latent）| no（当前降级态自洽）| handoff 必须显式警示 + serialize_float32 重构前不得载扩展进 store 连接 |
| R3 | 生产 `semantic_mode=llm` 全链路 0 端到端测试；capstone 绕过 executor/SearchService 且省 clean | medium | test-gap | no | 补 1 条「worker + semantic_mode=llm + seeded mock」集成 capstone |
| R4 | 「SQLite=prompt SSOT / 运行时唯一真相源」与实现矛盾（正文实读自本地文件）| medium | docs-gap / protocol-drift | no | 修正 SSOT 表述为「文件=正文 SSOT，SQLite=权威版本+digest 守卫」|
| R5 | `retry_with_backoff` 0 调用方，占位 provider 未用它包裹 | low | delivery-gap | no | closure 标「脚手架未接线」；实装 RealMLX 时包裹 |
| R6 | `SearchService` 不传 namespace_id → 绕过 namespace 级 metric 配置 | low | correctness（pre-existing）| no | 查侧传 namespace_id 或显式记账「team-wide cosine」 |
| R7 | `make_embedder/make_llm` 每调用新建实例 + `load_settings()` 每次重读 .env | low | efficiency | no | 进程级缓存 settings（非本轮）|

---

### R1. vec0 整条栈是隔离脚手架、对生产 store 零可达

- **严重级别**：`high`
- **类型**：`delivery-gap / scope-drift`
- **是否 blocker**：`no`（Q-RW-5 v1.1 本轮 scope = 写代码 + fake/skip 测，已满足）
- **事实依据**：
  - `grep make_vector_index packages apps`：除工厂定义与 `__init__` 导出外，**业务码 0 调用方**（仅 `test_rw_d_vec0.py` 调用）。
  - `Settings.vector_index="bruteforce"`（`settings.py:15`）从不被 `VectorStore` 读取；`store.search:160` 永远 `BruteForceVectorIndex(distance_metric=self._resolve_metric(...))`。
  - `Vec0VectorIndex.query`（`vector_index.py:153-194`）自建 `sqlite3.connect(":memory:")`、自载 `sqlite_vec`、用候选集临时建虚表——与持久 `VectorStore` / `chunk_embedding_index` **零关系**。
  - `test_vec0_bruteforce_parity_cosine` 比对的是两个**内存索引**在同一候选集上的排序，不触达 store。
- **为什么重要**：
  - RW-D verdict 行写「交付 `Vec0VectorIndex`（真实 sqlite-vec KNN）」，§1 收口为 `✅（scaffolding）`，cross-review 把「vec0 不接 store」降为单条 `🟡 footgun X1`。三处叠加给读者「vec0 实现已就位、只差接一根线」的印象，**实际是**：工厂槽、Setting、内存索引三件套彼此孤立，**没有任何一条生产路径**能走到 vec0，且「接线」不是连一根线，而是 R2 所述的持久层读写格式重构（serialize_float32 + 直接表 KNN + rowid 不变量复核）。
  - 这影响下游对「macOS 轮还剩多少活」的估算：handoff 列「跑 2 skip 测确认 parity」会让人以为 vec0 已基本可用，实则 parity 绿 ≠ 生产可用。
- **审查判断**：
  - **不是假绿、不是 blocker**——RW-D closure §4（持久 vec0 store 集成 = carry-over B）与 §5 诚实声明「不宣称 vec0 已在生产路径生效」已托底；本轮 scope 也确实只要求「写 + skip 测」。
  - **但披露层级不对等**：verdict/§1 的 ✅ 与 §4 的 carry-over 之间，缺一句「本实现当前对生产 store 不可达」的顶层提示。cross-review 的 X1 文字「设 vec0 不生效（静默用 BruteForce）」也只说对了一半（还有 R2 的崩坏面）。
- **建议修法**：
  - RW-D closure §0 verdict 与 cross-review §4 X1 增补一句：「`make_vector_index`/`Settings.vector_index`/`Vec0VectorIndex` 三者当前**均未接入生产 store**，vec0 选型对 `store.search` 完全无效（非仅『静默退化』，见持久层读写错配）」。
  - macOS 轮 kickoff 把「接 store」列为 vec0 真实生效的**前置**，而非与 parity 测并列的可选项。

### R2. 持久 `chunk_embedding_index`：vec0 schema ↔ JSON 文本读写错配地雷

- **严重级别**：`high`
- **类型**：`correctness（latent / handoff 触发）`
- **是否 blocker**：`no`（当前离线降级态自洽，279 passed）
- **事实依据**：
  - `vec.sql:` `CREATE VIRTUAL TABLE IF NOT EXISTS chunk_embedding_index USING vec0(embedding float[1024])`——声明为 vec0 虚表（需扩展）。
  - `store.py:91-97` 写：`INSERT OR REPLACE INTO chunk_embedding_index (rowid, embedding) VALUES (?, json.dumps(embedding))`；`store.py:158` 读：`json.loads(row["embedding"])`——**JSON 文本**读写。
  - `schema.py:46-84`：`CREATE VIRTUAL TABLE ... vec0` 抛 `OperationalError(...vec0...)` 时降级为 `_FALLBACK_TEXT_TABLE`（`embedding TEXT NOT NULL`）。
  - `grep enable_load_extension / sqlite_vec.load`（store/核心连接侧，排除 `vector_index.py`）→ **0 命中**。即 store 连接从不载扩展 → `vec0` 虚表必抛 → **必走 TEXT 降级**。`json.dumps/json.loads` 仅在此 TEXT 态正确。
- **为什么重要**：
  - 真实 vec0 表的 `embedding float[1024]` 列**不接受 JSON 字符串**，写入须 `sqlite_vec.serialize_float32(...)` blob，读出亦为 blob（`json.loads(blob)` 必抛）。
  - 当前「永远不出事」唯一原因是：**没人把扩展载进 store 连接**，于是虚表创建失败、静默降级 TEXT、JSON 读写恰好自洽。这是一个靠「扩展缺席」维持的脆弱平衡。
  - macOS 轮的 handoff（RW-D §6 / cross-review §6.1）明确写「owner macOS 装 sqlite-vec → 跑测试」。一旦有人为了让持久表「真用 vec0」而在 store 连接上 `enable_load_extension + sqlite_vec.load`，`apply_vec_schema` 的 `CREATE VIRTUAL TABLE` 即**成功**（不再降级）→ 此后 `store.upsert_chunk` 把 `json.dumps(...)` 塞进 vec0 float 列 → **写崩或维度错配**；即便侥幸写入，`store.search` 的 `json.loads(blob)` 也**读崩**。这正是 owner 关注的「数据库读写错乱」的具体落点。
- **审查判断**：
  - RW-D §4 carry-over B「store.search 仍 TEXT-JSON+BruteForce；store 读写改 serialize_float32」**承认了重构待做**，方向正确。
  - **但 handoff 缺一道明确护栏**：没有任何文字警告「在完成 serialize_float32 重构**之前**，不得把 sqlite-vec 扩展接入 store 连接，否则现有 vectorize/search 集成测全崩」。当前 handoff 把「装扩展」当作无害前置，实则它与「JSON store」互斥。
- **建议修法**：
  - handoff 增护栏：`macOS 装 sqlite-vec 仅用于 Vec0VectorIndex 的 :memory: 自载路径（跑 parity skip 测）；在 store 持久层完成 serialize_float32 读写重构前，禁止在 core/vec 连接上 load 扩展`。
  - 或：把 store 的写入路径加一道断言——若检测到 `chunk_embedding_index` 为 vec0 虚表（非 TEXT），拒绝 `json.dumps` 写入并 fail-loud，杜绝静默错配。
  - vec.sql 注释已写「Application writes must keep ...rowid mapping valid」，但未点明「写入格式随表类型而变」——补一句。

### R3. 生产 `semantic_mode=llm` 全链路 0 端到端测试

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - `test_real_wire_mock_capstone.py:69-114`：Pass 2 直调 `structurize_via_llm(doc.text, provider, p_struct)` / `summarize_via_llm(...)` / `store.upsert_chunk` / `store.search`——**不经** `process_rag_step`、`process_clean_step`、`management.SearchService`。
  - capstone **无 clean step**（直接喂 `doc.text` 给 structurize）；而 final-plan §8 自述 capstone 为「…D clean(mock LLM)→E structurize→F construct/summary→…」。
  - 唯一设 `semantic_mode="llm"` 的测试是 `test_structurize_dispatch_routes_rule_vs_llm`（test_rw_b_prompt_ssot.py），它只调 `_structurize_dispatch` 包装器，**不跑** `process_rag_step` 整段；无任何测试设 `SMIND_SEMANTIC_MODE=llm` 跑 worker / executor。
- **为什么重要**：
  - dispatch 包装器（`_structurize_dispatch`/`_summarize_dispatch`）有单测，但「executor 在 llm 模式下读 artifact→render→provider→写 artifact/chunk」与「process_clean_step 在 llm 模式建 registry」**整段无回归**。这两段恰是 provider charter 真正要替换占位的接缝。
  - RWB-07 收口语「文档→prompt→MockLLM→embed→search 使用链真实发生」在**库函数层**成立，但读者易理解为「生产管线在 llm 模式端到端验证过」——并未。
- **审查判断**：mock 下 scope 可接受（真实 provider 是 RW-C），但「capstone 绕过生产装配」削弱了它作为「使用链证据」的价值——它证明的是积木能拼，不是流水线接对了。
- **建议修法**：补 1 条集成 capstone：seed prompt + 写 `SMIND_SEMANTIC_MODE=llm` + 经 `run_worker`/`process_rag_step` 全跑（mock provider 经 `mock_llm_responses_path` 注入），断言 `produced_by=llm` 落到 artifact、`SearchService.search` 命中目标文。

### R4. 「SQLite=prompt SSOT / 运行时唯一真相源」与实现矛盾

- **严重级别**：`medium`
- **类型**：`docs-gap / protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `pre-charter-qna.md` Q-RW-3 业主回答：「**SQLite 为 prompt 的 SSOT**…用 SQLite 内的 KV 替代 Cloudflare KV…SQLite 为运行时唯一真相源，本地文件仅便利编辑层」。
  - 实现 `prompt_renderer.render_prompt`：`raw = path.read_text(...)`（正文**实读自本地文件**）→ 算 digest → 与 SQLite `template_digest` 对账。SQLite 仅存 `template_path + template_digest`，**不存正文**（`seed_prompt_version` 的 INSERT 列无 body）。
  - 文件缺失 → `PromptError(prompt_file_missing)`。即**SQLite 不足以独立渲染**，删掉本地文件即渲染失败。
- **为什么重要**：
  - 与 KV 模型本质不同：Cloudflare KV **持有正文**，读 KV 即得正文；此处 SQLite **不持有正文**，正文权威在文件。称其「替代 KV / 运行时唯一真相源」字面不成立——真正的内容 SSOT 是文件，SQLite 是「哪个版本/digest 权威」的选择器 + 防篡改守卫。
  - `prompt_renderer.py` 的模块 docstring 自己写对了：「SQLite 是『哪个 prompt/版本/digest 权威』的 SSOT；本地文件是被其 digest 校验的编辑层」——**代码注释比 qna/closure 的口径准确**。矛盾在 qna/closure 的措辞，不在实现。
- **审查判断**：实现的完整性模型（文件存内容 + DB 守 digest，篡改即 fail-loud）**比字面的「DB 即真相」更强**，无功能缺陷。属表述漂移：下游若据「SQLite 为运行时唯一真相源」推断「可只备份 SQLite、丢弃 prompts/ 目录」会踩空。
- **建议修法**：在 RW-B closure §7 与（如可）qna Q-RW-3 追加修订脚注：「运行时正文实读自 `prompts/*.md`；SQLite 持 path+digest，为**权威版本选择 + 防篡改守卫**，非正文载体。备份须含 `prompts/` 目录」。

### R5. `retry_with_backoff` 0 调用方，占位 provider 未用它包裹

- **严重级别**：`low`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：`grep retry_with_backoff packages apps` 仅 `__init__` 导出，0 业务调用；`RealMLXLLMProvider.complete`/`RealMLXEmbedder.embed` 直接 `raise ProviderDeferredError`，未经 retry 包裹。
- **为什么重要**：RWC-01 收口「退避/重试 + 错误分类」为 ✅ verified（commit+test）。算法单测确实绿，但它当前是**未接线的纯算法**——真实 client 延后，故无处可包。读者可能高估「重试已生效」。
- **审查判断**：符合 reframe（真实推理延后），不是假绿（逻辑正确且自测）。仅披露口径问题。
- **建议修法**：RWC closure 在 RWC-01 行注「脚手架就绪、未接线（无真实 client 可包）」；provider charter 实装时由 `RealMLX*.complete` 包 `retry_with_backoff`。

### R6. `SearchService` 不传 namespace_id → 绕过 namespace 级 metric 配置

- **严重级别**：`low`
- **类型**：`correctness（pre-existing F5，非 RW 引入）`
- **是否 blocker**：`no`
- **事实依据**：写侧 `workflow_rag/service.py:293 namespace_id=f"ns_{run['team_id']}"`；查侧 `search.py:48-53` 调 `vec_store.search(...)` **不传 namespace_id** → `store.search` 跳过 namespace 过滤、`_resolve_metric(None)` 直接返 `"cosine"`，不读 `vector_namespaces.distance_metric`。
- **为什么重要**：若未来某 namespace 配 `l2`/`inner_product`，写侧（`_ensure_namespace` 默认 'cosine'）与查侧（强制 cosine）当前恰好都 cosine、不出错；但 namespace 级 metric 配置（store `_resolve_metric` / F5-03 R10）在生产搜索路径**永不生效**。属潜伏不一致，非当前 bug。
- **审查判断**：RW 阶段未触此路径，沿用既有 F5 设计；列出仅为完整性。
- **建议修法**：查侧传 `namespace_id`（与写侧对称），或在 closure/设计登记「生产搜索固定 team-wide + cosine，namespace metric 暂不可达」。

### R7. `make_embedder/make_llm` 每调用新建实例 + `load_settings()` 每次重读 .env

- **严重级别**：`low`
- **类型**：`efficiency`
- **是否 blocker**：`no`
- **事实依据**：`workflow_rag/service.py:218,276`、`management/service.py:91,106` 每次 `make_embedder(load_settings())`；`load_settings()` 每调用重建 `Settings`（pydantic 重读 `.env`）。
- **为什么重要**：`LocalEmbedder` 无状态、写查同 name → 功能无害（cross-review X5 已记）。但 `load_settings()` 每次重解析 `.env`，理论上同一 run 内若 `.env` 被改会读到漂移值；性能上是热路径重复 IO。
- **建议修法**：进程级缓存 settings（`@lru_cache`），实例可不缓存。非本轮。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| RWA-01 | LLMProvider 协议 | done | `protocols.py` 双方法 Protocol，runtime_checkable |
| RWA-02 | 工厂 make_llm/embedder/vector_index | done | 选型 + 未知 fail-loud + 占位槽；**但 make_vector_index 下游 0 接线（见 R1）** |
| RWA-03 | Settings + .env + key 预留 | done | 默认 mock/local/bruteforce；key 字段 None；env_prefix SMIND_ |
| RWA-04 | 装配注入（写查同 embedder）| done | embedder 两侧同 name；**注意：未覆盖 vector_index（store 硬编码，R1）** |
| RWA-05 | MockLLMProvider 未命中 fail-loud | done | `MockResponseMissing` + complete_json JSON 校验 |
| RWA-06 | eval corpus 装载器 | done | `tests/fixtures/eval_corpus.py` 可载提交集 |
| RWA-07 | assert_used_real_chain 原语 | done | Spy 计数 + min_calls 断言 |
| RWA-08 | 先红后绿全绿 | done | 279 passed（本人复现）+ 门禁 0 弱 |
| RWA-09 | 维度 1536→1024 全库迁移 | done | vec.sql/schema/store/embedder 全 1024 + 写守卫；grep 0 生效 1536 |
| RWB-01 | 本地文件注册 prompt 正文 | done | `prompts/{structurize,summarize,clean-understand}.md` 存在 |
| RWB-02 | 渲染 + digest 对账 fail-loud | done | `render_prompt` 文件↔DB digest 不一致即 raise |
| RWB-03 | prompt_versions seed + 接消费 | done | `get_active_prompt` 由 render 消费，F6c 孤立消除；**SSOT 表述见 R4** |
| RWB-04 | structurize 去桩 | done | `complete_json`+`_normalize_structured`+非法 JSON fail-loud；rule fallback 留 |
| RWB-05 | summary 去桩 | done | `complete`+空回落 build_summary |
| RWB-06 | clean LLM 去桩 + degraded | done | llm 模式真 handler；`llm=None` 降级 fail-loud |
| RWB-07 | mock capstone 语义命中 + 使用链 | **partial** | 命中 + spy 断言成立；**但绕过 executor/SearchService 且无 clean step（R3）** |
| RWB-08 | 防假绿 non-delivery-quality | done | 门禁 0 弱 + mock 标注 |
| RWC-01 | 退避/重试 + 分类 | partial | 算法 + 单测成立；**0 调用方、未接线（R5）** |
| RWC-02 | 真实 provider 占位槽 + 维度守卫 | done(scaffolding) | 构造 ok / 调用 defer；维度锁 1024 |
| RWC-03 | 密钥构造注入 + 脱敏 | done | api_keys 实例内持有；repr 脱敏 |
| RWC-04 | mock↔live 路由一致 | done | FakeLive 替身证契约 |
| RWC-05/06 | live smoke / 手册 | out-of-scope-by-design | reframe 延后 provider charter |
| RWD-04 | Vec0VectorIndex + 工厂槽 + 分数转换 | **partial** | 协议/分数/降级/fail-loud 成立；**生产 store 不可达（R1）+ 持久读写错配地雷（R2）** |
| RWD-05 | vec0↔暴力 parity | out-of-scope-by-design | skipif gate → macOS（本环境 2 skipped，未观察，诚实标注）|
| RWD-01/02/03 | PDF/二进制 | out-of-scope-by-design | Q-RW-4 延后，未碰 |

### 3.1 对齐结论

- **done**: 18
- **partial**: 3（RWB-07 / RWC-01 / RWD-04）
- **missing**: 0
- **stale**: 0
- **out-of-scope-by-design**: 4（RWC-05/06、RWD-05、RWD-01/02/03）

> 它更像**「mock 语义骨架（RW-A/B）真实可执行且被测，外加 RW-C/D 的一批隔离脚手架」**，而非「四阶段全部 verified 交付」。3 个 partial 的共性是：**实现/算法本身成立，但与生产装配的接缝未接、未测**——这正是 provider/macOS 轮真正要做的活，不应被本轮的 ✅ 收口掩盖。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | PDF/二进制（RWD-01/02/03）| 遵守 | `storage_objects` 未加 put_bytes；无 PDF 解析；与 Q-RW-4 一致 |
| O2 | 外部厂商 LLM/embedding client | 遵守 | 工厂 openai/anthropic/gemini → `NotImplementedError`；未实装 |
| O3 | 真实 MLX 推理 | 遵守 | `RealMLX*` 调用 `ProviderDeferredError`；本环境不可跑，标未观察 |
| O4 | 真实 vec0 KNN / parity | 遵守（执行）/ 误报风险（披露）| skipif → macOS 正确；**但「实现已就位」的披露过强，易被误读为已可生产用（R1/R2）** |
| O5 | live 计费数值护栏 | 遵守 | 默认 mock 零外网；数值随 provider 延后（Q-RW-6）|

> **反向核查（reviewer 是否误判 deferred 为 blocker）**：未误判。本轮 scope 经 reframe 明确为「mock+占位+接口+路由+测 mock」，R1-R7 **无一要求本轮交付真实推理/真实 KNN**——它们要求的是**披露口径校正 + handoff 护栏 + 一条集成测**，均属「关闭前不必、handoff 前必须」。

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`approve-with-followups` — RW-A/B/C/D 本轮 scope 达成，无假绿、无越界、测试真实可复现、qna 方向性一致；扣分项集中在「脚手架按 verified 收口时对『生产不可达 / handoff 地雷』披露不足」。
- **是否允许关闭本轮 review**：`yes`
- **关闭前必须完成的 blocker**：
  1. **无**（本轮交付承诺已兑现）。
- **进入 provider / macOS 轮之前必须消化的 follow-up（非本轮 blocker，但 handoff 假成立的根源）**：
  1. **R2 护栏**：handoff 显式写「serialize_float32 store 重构完成前，禁止把 sqlite-vec 扩展载入 core/vec 连接」+（建议）store 写入对 vec0 虚表 fail-loud。**最高优先**——这是真正会炸数据库读写的项。
  2. **R1 披露**：closure verdict + cross-review X1 补「vec0 三件套对生产 store 零可达」一句，macOS kickoff 把「接 store」列为 vec0 生效前置。
  3. **R3 测试**：补 1 条 executor 层 `semantic_mode=llm` 集成 capstone。
- **可以后续跟进的 non-blocking follow-up**：
  1. R4 SSOT 表述校正（文件=正文 SSOT）。
  2. R5 retry 接线标注；R6 查侧 namespace_id；R7 settings 缓存。
- **建议的二次审查方式**：`no rereview needed`（本轮）；provider/macOS 轮**进入时**由 independent reviewer 复核 R1/R2/R3 是否已消化。
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> **一句话**：本轮可收口——但请把「✅ verified」与「生产可达」两件事在 closure 里分开写。当前最危险的不是任何已知缺口，而是 handoff 里那句轻描淡写的「macOS 装 sqlite-vec 跑测试」——在 store 用 serialize_float32 重构之前，它是一颗会让现有 vectorize/search 集成测集体崩溃的地雷。

---

## 6. 实现者回应

### 6.1 对本轮审查的回应

> 执行者: `Opus 4.8（实现者回合 — 与 §0–§5 reviewer 同模型，但本节为修复执行，不改写审查正文）`
> 执行时间: `2026-06-02`
> 回应范围: `R1–R7`
> 对应审查文件: `docs/code-review/real-wire/RW-full-reviewed-by-opus.md`

- **总体回应**：`R1/R2/R3/R4/R5 已修（代码 3 项 + 文档 2 项）；R6 deferred-with-rationale（改查询作用域风险>价值）；R7 stale-rejected（前提部分失实：load_settings 已 lru_cache）。`
- **本轮修改策略**：`先消化 reviewer 标为「handoff 前必须」的 R2（地雷护栏）→ R1（vec0 选型真生效）→ R3（executor llm 端到端测）；再做 R4/R5 文档校正。所有改动保持默认行为零回归（新参数皆带安全默认），全量 279→283 passed、门禁仍 0 弱。`
- **实现者自评状态**：`ready-for-rereview`

### 6.2 逐项回应表

| 审查编号 | 审查问题 | 处理结果 | 处理方式 | 修改文件 |
|----------|----------|----------|----------|----------|
| R1 | vec0 整条栈对生产 store 零可达；`Settings.vector_index` 死配置 | fixed | `VectorStore` 新增 `vector_index` 参数 + `_make_query_index()`，`search` 不再硬编码 BruteForce；经 `SearchService` → `management.search` 把 `Settings.vector_index` 注入。vec0 选型现真生效（离线无扩展即 fail-loud `sqlite_vec_unavailable`，非静默退化）。**残留**：`make_vector_index` 工厂函数仍仅测试调用（store 路径用 kind 字符串避免 `provider_runtime` 循环导入），已在 §6.6 登记。 | `packages/vector_sqlite_vec/.../store.py`、`packages/rag_vectorizer/.../search.py`、`packages/management/.../service.py` |
| R2 | 持久 `chunk_embedding_index`（vec0 schema）↔ JSON 读写错配地雷；装扩展即崩 | fixed | `store.upsert_chunk`/`search` 前置 `_guard_json_store_compatible()`：探测 `sqlite_master.sql` 含 `vec0` 即 fail-loud `vec0_native_store_unimplemented`，杜绝「扩展载入 store 连接 → JSON 写坏/读崩」。handoff 护栏写入 RW-D closure §0。 | `packages/vector_sqlite_vec/.../store.py`、`docs/closure/real-wire/RW-D-closure.md` |
| R3 | 生产 `semantic_mode=llm` 全链路 0 端到端测试；capstone 绕过 executor | fixed | 新增集成测 `test_semantic_mode_llm_executor_end_to_end`：经真实 worker（claim/lease/executor 全栈）在 `SMIND_SEMANTIC_MODE=llm` 下跑 clean→structurize(llm)→construct→summary(llm)→vectorize，再经 `SearchService` 检索；断言 `produced_by=llm`、vectorize succeeded、document active、search 命中。mock 经 `mock_llm_responses_path` 注入（key=executor 同源渲染的 prompt）。 | `tests/integration/p4_rag_pipeline/test_rw_b_llm_executor_e2e.py` |
| R4 | 「SQLite=prompt SSOT/运行时唯一真相源」与实现矛盾（正文实读自文件） | fixed | RW-B closure §7 该行措辞校正为「SQLite=权威版本选择+防篡改 digest 守卫的 SSOT；本地文件=正文内容 SSOT」，并提示 qna Q-RW-3「运行时唯一真相源」应读为「版本/digest 唯一真相源」。**未改 frozen qna 正文**（尊重 owner 文档归属；权威校正落实现者侧 closure）。 | `docs/closure/real-wire/RW-B-closure.md` |
| R5 | `retry_with_backoff` 0 调用方，占位 provider 未包裹 | fixed | RW-C closure RWC-01 状态由 `✅` 细化为 `✅（算法 verified · 未接线）`，明记「就绪未接线的脚手架，provider charter 实装 RealMLX 时包裹」。代码本身按 reframe 不接线（无真实 client 可包），不做无意义包裹。 | `docs/closure/real-wire/RW-C-closure.md` |
| R6 | `SearchService` 不传 namespace_id → 绕过 namespace 级 metric 配置 | deferred-with-rationale | 改查询作用域（加 namespace 过滤 / 改 metric 解析）会改变既有 F5 检索语义，回归面 > 价值（当前全 cosine，写查两侧实际一致、无 bug）。属 pre-existing F5 设计，非 RW 引入。承接见 §6.6。 | —（未改）|
| R7 | `make_embedder/make_llm` 每调用新建 + `load_settings()` 每次重读 .env | stale-rejected（settings 部分）+ rejected（embedder 部分） | **前提失实**：`load_settings` 已 `@lru_cache(maxsize=1)`（`loader.py:6`），**并非**每次重读 .env；故「settings 重读」不成立。`make_embedder` 新建 `LocalEmbedder` 无状态、写查同 name，无害（cross-review X5 已记），无需缓存。不改。 | —（未改）|

> 独立复核状态：`R1/R2/R3 = independently-verified（新测真跑、全量回归绿）`；`R4/R5 = self-claimed-doc-fix（措辞校正，无可执行断言）`；`R6 = deferred-by-rationale`；`R7 = stale-rejected-by-code（loader.py:6 lru_cache 实证）`。

### 6.3 Blocker / Follow-up 状态汇总

| 分类 | 数量 | 编号 | 说明 |
|------|------|------|------|
| 已完全修复 | 5 | R1, R2, R3, R4, R5 | 代码 3（R1/R2/R3）+ 文档 2（R4/R5）|
| 部分修复，需二审判断 | 0 | — | — |
| 有理由 deferred | 1 | R6 | 改查询作用域风险>价值；承接 macOS/生产化轮 |
| 拒绝 / stale-rejected | 1 | R7 | 前提失实（load_settings 已 lru_cache）|
| 仍 blocked | 0 | — | 本轮无 blocker |

### 6.4 变更文件清单

- `packages/vector_sqlite_vec/src/vector_sqlite_vec/store.py` — R1：`vector_index` 参数 + `_make_query_index`；R2：`_embedding_index_is_native_vec0` + `_guard_json_store_compatible`（写/查前置）。
- `packages/rag_vectorizer/src/rag_vectorizer/search.py` — R1：`SearchService` 收 `vector_index` 注入 `VectorStore`。
- `packages/management/src/management/service.py` — R1：`search`/`search_debug` 传 `vector_index=load_settings().vector_index`。
- `tests/unit/test_rw_d_vec0.py` — R1/R2：新增 3 测（默认 bruteforce 回归 / vec0 setting 真生效 fail-loud / native-vec0 错配守卫）。
- `tests/integration/p4_rag_pipeline/test_rw_b_llm_executor_e2e.py` — R3：新增 executor 层 `semantic_mode=llm` 端到端集成测。
- `docs/closure/real-wire/RW-B-closure.md` — R4：SSOT 措辞校正。
- `docs/closure/real-wire/RW-C-closure.md` — R5：RWC-01 retry 未接线标注。
- `docs/closure/real-wire/RW-D-closure.md` — R1/R2 修复记录 + handoff 护栏。
- `docs/closure/real-wire/RW-cross-stage-review.md` — X1 footgun 标记为复审已修。

### 6.5 验证结果

| 验证项 | 命令 / 证据 | 结果 | 覆盖的 finding |
|--------|-------------|------|----------------|
| 全量回归 | `python3 -m pytest -p no:cacheprovider` | `283 passed, 2 skipped, 1 xfailed`（基线 279，净 +4）| 全部（零回归）|
| 断言强度门禁 | `python3 tools/scripts/check_assert_strength.py` | `53 文件, 0 个仅弱断言` | 防假绿 |
| R1/R2 store 单测 | `pytest tests/unit/test_rw_d_vec0.py` | `8 passed, 2 skipped`（新增 3 全绿）| R1, R2 |
| R3 executor llm e2e | `pytest tests/integration/p4_rag_pipeline/test_rw_b_llm_executor_e2e.py` | `1 passed`（断言 `produced_by=llm` 真成立，mock 命中非短路）| R3 |
| 受影响既有套件 | `pytest test_f5_search_filter / test_vector_store_rowid / p4 / p5 / capstone` | 全绿 | R1/R2 零回归 |

```text
283 passed, 2 skipped, 1 xfailed, 1 warning in ~8s
断言强度门禁通过: 扫描 53 文件, 0 个仅弱断言测试
```

> 说明：`Vec0VectorIndex` 真实 KNN / parity 仍为 `2 skipped`（离线 Linux 无 sqlite-vec 扩展，skipif→macOS）——R1/R2 未声称真实 vec0 已跑通，只声称「setting 已可达 + 错配已 fail-loud」，与本环境能力一致，不谎报。

### 6.6 未解决事项与承接

| 编号 | 状态 | 不在本轮完成的原因 | 承接位置 |
|------|------|--------------------|----------|
| R1（残留）| deferred | `make_vector_index` 工厂函数仍仅测试调用（store 路径用 kind 字符串避循环导入）；持久原生 vec0 表 + `serialize_float32` 读写重构未做 | RW-D carry-over「持久 vec0 store 集成」（macOS 轮）|
| R6 | deferred | 改 `SearchService` 查询作用域回归面 > 价值（当前全 cosine 无 bug）| macOS / 生产化轮（与 namespace metric 真启用一并评估）|
| R7 | rejected | 前提失实（load_settings 已 lru_cache）；embedder 新建无害 | —（无需承接）|

### 6.7 Ready-for-rereview gate

- **是否请求二次审查**：`yes`
- **请求复核的范围**：`only R1/R2/R3（代码改动 + 新测）；R4/R5 closure 措辞；R6/R7 处置判断`
- **实现者认为可以关闭的前提**：
  1. 二审确认 R2 守卫 + handoff 护栏足以防「macOS 装扩展即崩」的数据库读写错配（本轮最高优先项已落地）。
  2. 二审认可 R6 deferred / R7 stale-rejected 的理由（或指出需在本轮处理的具体回归风险）。
