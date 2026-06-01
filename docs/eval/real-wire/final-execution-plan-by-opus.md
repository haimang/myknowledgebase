# real-wire（真实接线）—— Final Execution Plan（by Opus 4.8）

> **stage**：`final` ← 开关；本文填 §2.C / §6[final] / §7.B / §8[final] / §10.A / §12 / §13
> **作者**：`Opus 4.8`（panel / 跨模型 handoff：reference-anchor 由 4 个 Explore 子代理 fan-out 调查）
> **时间**：`2026-06-01`
> **文档性质（自宣告 role）**：`final` = "**取代 initial + proposed 两份**，作 action-plan 制作前**唯一执行基线**；不再在前两份上增量。本文冻结零新决策——只把 owner 已在 `pre-charter-qna.md` register 的裁决汇编成可执行基线。"
> **上游权威输入**：
> - `docs/eval/real-wire/pre-charter-qna.md`（**frozen，最高口径**）— Q-RW-1..7 裁决 + 贯穿性 reframe
> - `docs/eval/real-wire/proposed-planning-by-opus.md`（被本态取代）— §6 sized 台账 + §2.B Δ
> - `docs/eval/real-wire/reference-anchor-by-opus.md` — 轴 A/B/C/D 锚定矩阵 + 反例 + 净新 + TR 过滤
> - `docs/eval/real-wire/state-analysis-after-FF7-by-opus.md` — mock `.tmp` 方案
> **输入权威次序**：`冻结 QnA（pre-charter-qna）> HEAD 代码实测 > design artifacts（proposed/reference-anchor）`
> **phase 命名 & 工作项 ID 方案**：`RW-A/B/C/D`（phase）/ `RWA-01..` `RWB-01..` `RWC-01..` `RWD-01..`（跨态稳定，沿用 proposed；本态新增 GAP 项续编）
> **裁定动词 rubric（§2.C）**：`CONFIRM / CORRECT / REFINE / RESIZE / GAP / SCOPE↓`
> **文档状态**：`frozen`
> **下游消费者**：`本轮派生 2 份 action-plan（RW-A / RW-B）；RW-C / RW-D 延后至后续 provider charter 再派生`

---

## 0. TL;DR

- **核心论点**：冻结 qna 把 real-wire 的近期范围**重定义**为「**mock + 占位 + 初始接口 + 预留/真接 mock↔real-wire 路由 + 测 mock**」，并把 **provider adapter（本地 MLX vs 外部厂商）整体推到后续 charter**。因此本执行基线只冻结并派生 **RW-A（mock 基座 + 协议接口 + 路由 + 1024 维迁移，keystone，不依赖任何 gate）** 与 **RW-B（prompt 本地文件 + SQLite-SSOT 语义链去桩，mock 下验证）** 两个 phase；**RW-C（真实 live）与 RW-D（PDF/vec0）SCOPE↓ 延后**。
- **一句话**：本轮交付「能被真实接线、且 mock 下端到端跑通并被测」的语义管线骨架——真实模型留待下一 charter 插槽。
- **本态相对上一态做了什么（proposed → final）**：① 据 Q-RW-1 把 **维度 1536→1024 全库迁移**（proposed 的 `MIG-RW-4=不做` **翻转为必做**，新增 GAP 项 `RWA-09`）；② 据 Q-RW-3 把 RWB-01 从「KV 导出 vs 重写」**CORRECT 为「本地文件注册 + SQLite-SSOT + 文件↔DB hash 对账」**，新增 `MIG-RW-5`；③ 据 reframe 把 **RW-C/RW-D 全部 SCOPE↓ 延后**，关键路径收缩为 RW-A→RW-B(mock)；④ §7.B 全 gate 由冻结 Q 关闭。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| pre-charter-qna（frozen）| qna | Q-RW-1..7 裁决 + reframe（本轮=mock+接口+路由+测 mock；provider 延后）| `pre-charter-qna.md`（最高口径）|
| proposed-planning | 上一态 plan | §6 sized 台账（RWA/B/C/D-*）+ §2.B Δ | `proposed-planning-by-opus.md`（被取代）|
| reference-anchor | eval/anchor | 轴 A/B/C/D 锚定(path:line+verdict) + 反例 + 净新 + TR 过滤 | `reference-anchor-by-opus.md` |
| state-analysis | eval | mock `.tmp/eval-fixtures` 组织 | `state-analysis-after-FF7-by-opus.md` |
| owner-gated-qna | qna | [Q1]vec0 degraded / [Q2]~~1536~~(被 Q-RW-1 覆盖为 1024) / [Q3]去桩增量 / [Q5]api-key / [Q7]先红后绿 | `owner-gated-qna.md` |

- **纪律继承（TR 红线，据冻结 qna 更新）**：TR-1 接口隔离(mock/live 同协议)；**TR-2 维度=1024（覆盖原 1536）、本轮须迁 schema**；TR-3 写/查同 embedder；TR-4 degraded/失败 fail-loud+reason；TR-5 密钥不进仓/日志、测试默认不打外网；TR-6 离线无 ML/无 Cloudflare binding（real 模型在 macOS/MLX，不进默认 Linux CI）。

---

## 2. 辨证审核（裁定上一阶段）★ 承重段

### 2.C critique vs proposed-planning

| item-ID | 裁定 | 处置 | 依据（冻结 Q / HEAD 锚）|
|---------|------|------|---------------------------|
| RWA-01 LLMProvider 协议 | CONFIRM | 保留为**接口+mock+路由**（真实客户端延后）| `[Q-RW-2]` 框架冻结；`ai_schemas.ts:170-179` |
| RWA-02 provider 工厂 | CONFIRM | `make_llm/make_embedder/make_vector_index`，按 Settings 选、未知 fail-loud | `[Q-RW-2/1]`；`providers_dedicated/service.py:114-151` |
| RWA-03 Settings+.env | REFINE | 扩 provider/model 字段 + `env_file`；**默认 mock/local/bruteforce**；**外部 key 字段预留备而不填**（Q-RW-7 外部 key 延后）| `[Q-RW-1/2/7]`；`settings.py:1-11` |
| RWA-04 装配工厂注入 | CONFIRM（high）| 替硬编码 + 写查同 embedder | `[Q-RW-1]`；注入点 `search.py:42`,`workflow_rag/service.py:186,243,263`,`apps/api/deps.py:114-128`,`worker/main.py:30,59` |
| RWA-05 MockLLMProvider + mock embedding | CONFIRM | 读 `llm_responses.json` 未命中 fail-loud；mock embedding=**LocalEmbedder@1024** | `[Q-RW-2/1]`；`embedder.py:66-92` |
| RWA-06 eval corpus | CONFIRM | `.tmp/eval-fixtures` + 精简可提交集 | `[Q-RW-1]`；state-analysis §7.2 |
| RWA-07 测试原语 | CONFIRM | `assert_used_real_chain`(provider/prompt 被真调) | `tests/fixtures/primitives.py` |
| RWA-08 先红后绿 | RESIZE | DoD 扩含**维度 1024 守卫 + 默认 mock + 路由分发**回归 | `[Q-RW-1/7]`；`check_assert_strength.py` |
| **RWA-09 维度 1536→1024 全库迁移** | **GAP（新增）** | proposed `MIG-RW-4=不做` 翻转为必做：`vec.sql:22,43` CHECK→1024、`schema.py:34` vec0 float[1024]、`store.py` INSERT 字面、`LocalEmbedder.DIMENSION`→1024、维度守卫泛化 `!=self.dimension` | `[Q-RW-1]`；`MIG-RW-4` |
| RWB-01 prompt 正文来源 | **CORRECT** | 由「KV 导出 vs 重写」改为**「本地文件注册正文（据 schema/用法本地编写）」**；legacy KV 不可达不导出 | `[Q-RW-3]`；`kv.ts:43`(key 分类法借),`schemas_common.ts:135-154`(schema 借) |
| RWB-02 渲染引擎 | REFINE | 渲染 + sha256 digest 校验 + **本地文件↔SQLite digest 对账**（不一致 fail-loud）| `[Q-RW-3]`；`MIG-RW-5`；`prompt_versions` DDL |
| RWB-03 prompt_versions seed + 接消费 | CONFIRM | **SQLite=prompt SSOT**（替代 Cloudflare KV）；接 `get_active_prompt` 到消费侧，消除 F6c 孤立 | `[Q-RW-3]`；`config_repo.py:31-49`；`MIG-RW-2` |
| RWB-04 structurize 去桩 | CONFIRM（high）| `service.py:64` 规则→prompt→**MockLLM**；规则化 fallback 留 | `[Q-RW-3]`；`rag_structurizer/service.py:30-71` |
| RWB-05 summary/construct 去桩 | CONFIRM | `service.py:122` build_summary→summarize prompt（mock）| `rag_constructor/service.py:64-97`；`summarizer.ts` 启发式 |
| RWB-06 clean LLM 去桩 | CONFIRM | `action_registry.py:90-99` gemini* degraded→真实 handler(LLM 模式, mock provider)；degraded 留 fallback | `[Q-RW-3]`；TR-4 |
| RWB-07 mock capstone | CONFIRM | 文档→prompt→LLM(mock)→embed(**1024**)→search 语义命中 + 使用链证据 | `tests/e2e/`；`assert_vector_authentic`(F7) |
| RWB-08 防假绿 | CONFIRM | mock 仅验「使用链发生 + 结构」，标 **non-delivery-quality** | `[Q-RW-3]`；`check_assert_strength.py` |
| RWC-01..06 真实 live（LLM/embedding 客户端 / 密钥 / smoke / 手册）| **SCOPE↓ DEFER** | 整体延后至**后续 provider charter**（provider adapter 未定）；接口与路由本轮已备 | `[Q-RW-2/6]` provider 延后；reframe |
| RWD-01..05 PDF/二进制 + 真实 vec0 | **SCOPE↓ DEFER** | 延后：`[Q-RW-4]`不接 PDF、`[Q-RW-5]`延后 vec0 | `[Q-RW-4/5]` |
| —（proposed NEW）prompt 正文来源载体 | **CLOSED** | 由 Q-RW-3 关闭：本地文件 + SQLite-SSOT + hash 对账 | `[Q-RW-3]` |

- **本态核心转向（一句话）**：从 proposed 的「4 phase 全 sized、维度锁 1536、prompt 待 gate」**收敛为**「**本轮仅 RW-A+RW-B(mock) 可执行 + 维度迁 1024 + prompt 走本地文件/SQLite-SSOT**，RW-C/RW-D 随 provider charter 延后」。

---

## 3. 范围与非范围（In/Out-Scope）

> 范围模态 = final：**execution-ready 定档**。

### 3.1 In-Scope（本轮执行）

- **[S-A] RW-A · provider 基座 + mock + 路由 + 1024 迁移（L，keystone，不依赖任何 gate）** — 三协议接口(✅复用) + 工厂(✅复用 ProviderRegistry 范式) + Settings/.env 默认 mock(♻️，外部 key 预留) + MockLLMProvider + mock embedding@1024(🆕/✅) + eval corpus(🆕) + 装配注入(high) + 测试原语 + **维度 1536→1024 全库迁移(GAP)**。
- **[S-B] RW-B · prompt 本地文件 + SQLite-SSOT 语义链去桩（L，mock 下，无待决 gate）** — 本地文件注册正文(🆕，据 schema 本地编写) + key/schema 复用(✅) + 渲染引擎 + 文件↔SQLite digest 对账(🆕) + seed/接消费(✅) + structurize/summary/clean 去桩(♻️ high, 走 MockLLM) + mock capstone + 防假绿。

### 3.2 Out-of-Scope / 延后

- **[O-C] RW-C 真实 live（LLM/embedding 客户端 + 密钥 + smoke）** — 延后至**后续 provider charter**；重评条件：owner 在后续 charter 明确 provider adapter（本地 MLX 模型 vs 外部厂商）+ Q-RW-6 计费数值 + Q-RW-7 外部 key。
- **[O-D] RW-D PDF/二进制 + 真实 vec0** — `[Q-RW-4]`本轮不接 PDF、`[Q-RW-5]`延后 vec0；重评条件：语料含必须处理的 PDF / 暴力 cosine 撞性能瓶颈 / 生产化轮。
- **[O-E] 断言门禁接 CI / 多 provider / 浏览器渲染 / 多模态 Vision** — 平台化轮 / [Q3] 范围外。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线（TR-1..6）**：见 §1；**Cloudflare binding 全 ⛔**，借协议/算法/schema。**TR-2 据 Q-RW-1 改写为维度=1024、本轮须迁 schema**。
- **治理冻结面**：密钥不进仓/日志/夹具（TR-5/F6c⛔1）；`.env` git-ignored + `.env.example` 占位进仓 + **构造注入**（严禁 `gemini.ts:96-132` 模块级全局轮转）；测试默认 mock 不打外网；**real（MLX/macOS）lane 延后、不进默认 Linux CI**；防假绿门禁覆盖 real-wire mock。
- **migration inventory（final 定档）**：
  - `MIG-RW-1` `Settings` 增 provider/model 字段 + `env_file`；外部 key 字段预留（RWA-03，无 DB 迁移）
  - `MIG-RW-2` `prompt_versions` seed（RWB-03，SQLite-SSOT 行级 seed，非 schema 改）
  - `MIG-RW-3` ObjectStore 二进制 + 上传端点（RWD-01）—— **延后**
  - `MIG-RW-4` **维度 schema 1536→1024 全库迁移** —— **本轮必做**（`vec.sql:22,43` CHECK + `schema.py:34` vec0 float[1024] + `store.py` INSERT 字面；翻转自 proposed「不做」；RWA-09）
  - `MIG-RW-5` **本地文件 ↔ SQLite prompt digest 对账机制**（RWB-02，新增：注册/同步步 + digest 列消费）

---

## 5. DAG（关键路径 + 并行窗）

```text
RW-A(mock 基座+接口+路由+1024 迁移, 不依赖任何 gate) ──▶ RW-B(prompt 本地文件+SQLite-SSOT 链, mock 下)
                                                          ┊
        [本轮到此为止——下一 provider charter 解锁 ↓]      ┊
RW-C(真实 live) ◀┄┄ 延后 (provider adapter 未定: Q-RW-2/6/7)
RW-D(PDF/vec0)  ◀┄┄ 延后 (Q-RW-4/5)

关键路径（本轮）：RW-A → RW-B（皆 mock；本 charter 终点）
说明：RW-A 内 RWA-09(1024 迁移) 是 RWA-04/05/07 与整个 RW-B 的前置（管线须先在 1024 上自洽）。
```

---

## 6. 逐 phase 工作台账（final：action-plan 绑定）

### 6.A RW-A · provider 基座 + mock + 路由 + 1024 迁移（keystone）

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Q] |
|------|------|--------|------|------------|----------|-----------|----------|
| RWA-01 | interface | `LLMProvider` 协议(`complete`/`complete_json`→{text,usage}) | ✅ | Protocol + 双方法签名就位 | 类型存在 + 契约测试 | — | Q-RW-2 |
| RWA-02 | routing | 工厂 `make_llm/make_embedder/make_vector_index`(按 Settings 选, 未知 fail-loud) | ✅ | 各分支返正确实现; 未知 raise | 分支单测 | — | Q-RW-2/1 |
| RWA-03 | config | `Settings` 增 provider/model 字段 + `env_file`; 默认 mock/local/bruteforce; 外部 key 字段预留 | ♻️ | 零配置即 mock 无外网; key 槽位备而不填 | 默认值测试 | MIG-RW-1 | Q-RW-1/2/7 |
| RWA-04 | wiring | 装配工厂注入(替硬编码 + 写/查同 embedder 实例) | ✅ | 全注入点走工厂; 写查同实例 | grep 无残留硬编码 + 全量回归不降 | — | Q-RW-1 |
| RWA-05 | mock | `MockLLMProvider`(读 `llm_responses.json`, 未命中 fail-loud) + mock embedding(LocalEmbedder@1024) | 🆕/✅ | 未命中 fail-loud; mock embed=1024 维 | mock 命中/未命中测试 | — | Q-RW-2/1 |
| RWA-06 | fixtures | eval corpus 装载器 + `.tmp/eval-fixtures` 构建 + 精简可提交集 | 🆕 | 样本可载入测试 | 装载测试 | — | Q-RW-1 |
| RWA-07 | test | real-wire 测试原语 `assert_used_real_chain`(provider/prompt 被真调) | ♻️ | 能断言使用链真实发生 | 原语自测 | — | — |
| RWA-08 | test | 先红后绿: 工厂选型 + 默认 mock + **1024 维守卫** + 路由分发 + 装配回归全绿 | ✅ | 234+ 不回归; 维度 !=1024 fail-loud | 红→绿 diff + 全量 pass | — | Q-RW-1/7/[Q7] |
| **RWA-09** | migration | **维度 1536→1024 全库迁移**: `vec.sql:22,43` CHECK、`schema.py:34` vec0 float[1024]、`store.py` INSERT 字面、`LocalEmbedder.DIMENSION`、守卫泛化 `!=self.dimension` | ♻️ | 全库 1024 一致; 旧 1536 残留=0 | grep 1536 残留=0 + 维度守卫测试 | **MIG-RW-4** | Q-RW-1 |

### 6.B RW-B · prompt 本地文件 + SQLite-SSOT 语义链去桩（mock 下）

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Q] |
|------|------|--------|------|------------|----------|-----------|----------|
| RWB-01 | prompt-ssot | **本地文件注册 prompt 正文**(本地合适文件夹; 据输出 schema+用法本地编写; legacy KV 不导出) | 🆕(正文)+✅(key/schema) | 核心 prompt(structurize/summarize)正文落本地文件 | 文件存在 + 内容据 schema | — | Q-RW-3 |
| RWB-02 | prompt-ssot | prompt 渲染引擎(变量注入 + sha256 digest) + **本地文件↔SQLite digest 对账**(不一致 fail-loud) | 🆕 | 渲染正确; 文件/DB digest 不一致即 fail-loud | 渲染测试 + 对账失败用例 | **MIG-RW-5** | Q-RW-3 |
| RWB-03 | prompt-ssot | `prompt_versions` seed(**SQLite=SSOT**, 替代 Cloudflare KV) + 接 `get_active_prompt` 到消费侧 | ✅ | 消费侧读 SQLite; F6c 孤立消除 | 消费侧调用测试 | **MIG-RW-2** | Q-RW-3 |
| RWB-04 | de-stub | structurize 去桩: `service.py:64` 规则→prompt→MockLLM; 规则化 fallback 留 | ♻️ | mock 下走 prompt→render→provider; 无 LLM 时 fallback | 去桩前后行为测试 | — | Q-RW-3 |
| RWB-05 | de-stub | summary/construct 去桩: `service.py:122` build_summary→summarize prompt(mock) | ♻️ | mock 下摘要走 prompt; fallback 留 | 测试 | — | Q-RW-3 |
| RWB-06 | de-stub | clean LLM 去桩: `action_registry.py:90-99` gemini* degraded→真实 handler(LLM 模式, mock) | ♻️ | LLM 模式走 mock provider; degraded fallback 留 | 测试 | — | Q-RW-3 |
| RWB-07 | capstone | mock capstone: 文档→prompt→LLM(mock)→embed(1024)→search 语义命中 + 使用链证据 | 🆕 | 端到端 mock 通过 + 证据链断言 | e2e 测试 | — | Q-RW-3/1 |
| RWB-08 | anti-false-green | 防假绿: mock 仅验「使用链发生+结构」, 标 non-delivery-quality | ✅ | 断言强度门禁过; mock 不冒充质量 | 门禁扫描 | — | Q-RW-3/[Q7] |

### 6.C / 6.D（延后，carry 至后续 provider charter）

| 编号区间 | phase | 延后理由 | 解锁条件 |
|----------|-------|----------|----------|
| RWC-01..06 | RW-C 真实 live | provider adapter 未定(Q-RW-2/6/7 延后) | 后续 provider charter 关 provider/计费/外部 key |
| RWD-01..05 | RW-D PDF/vec0 | Q-RW-4 不接 PDF / Q-RW-5 延后 vec0 | 语料含 PDF / 暴力 cosine 撞瓶颈 / 生产化轮 |

---

## 7. Owner decision gates

### 7.B gate-closure map（全部由冻结 QnA 关闭）

| gate | 对应冻结 Q | 裁决结论（下游唯一口径）| 状态 |
|------|-----------|--------------------------|------|
| G-RW-1 | Q-RW-1 | 向量维度=**1024**（覆盖 [Q2] 1536）; embedding **仅本地 MLX/macOS**; 本轮做接口+mock(1024)+路由+1024 迁移, 具体 MLX 模型 adapter 延后 | **CLOSED** |
| G-RW-2(正文) | Q-RW-3 | prompt=**本地文件 + SQLite-SSOT + hash 对账**, 替代 Cloudflare KV; 正文据 schema 本地编写 | **CLOSED** |
| G-RW-2(厂商) | Q-RW-2 | LLM provider adapter（本地 MLX vs 外部厂商）**延后至后续 charter**; 本轮只做协议接口+MockLLMProvider+路由 | **framework-closed · provider 延后** |
| G-RW-3 | Q-RW-4 | 本轮**不接 PDF**, RW-D 上半段延后 | **CLOSED** |
| G-RW-4 | Q-RW-5 | **延后 vec0**, 维持暴力 cosine | **CLOSED** |
| G-RW-5 | Q-RW-6 | 计费/速率框架定(默认 mock + fail-loud); **$/速率数值随 provider 延后** | **framework-closed · 数值延后** |
| G-RW-6 | Q-RW-7 | `.env`(git-ignored)+构造注入定; **外部厂商 key 需求随 provider 延后**; app 自身 api-key([Q5])不受影响 | **framework-closed · 外部 key 延后** |

- **结论**：**本轮可执行范围（RW-A + RW-B mock）无任何 OPEN 决策项，可转入 action-plan**。剩余 framework-closed 项（LLM provider adapter / 计费数值 / 外部 key）全部归后续 provider charter，不阻塞本轮。

---

## 8. 测试计划

- **A 短途（unit/in-process，入 CI 不打外网）**：工厂选型 + 默认 mock + **1024 维守卫** + 路由分发 + 装配回归（RWA-08/09）；prompt 载入 / digest / 渲染 / **本地文件↔SQLite 对账**（RWB-02/03）。
- **B spike（集成, mock provider + 真实样本, 入 CI 不打外网）**：mock capstone 文档→prompt→LLM(mock)→embed(1024)→search **语义命中 + 使用链证据**（RWB-07/08）。
- **D mega（owner-triggered 长程）**：**本轮 N/A**——真实模型 live smoke（macOS/MLX）随 RW-C 延后至后续 provider charter。
- **长程 capstone（本轮）**：`tests/e2e/test_real_wire_mock_capstone.py`——A 装载 eval corpus → B 注册本地 prompt 入 SQLite + digest 对账 → C ingest 文档 → D clean(mock LLM) → E structurize(mock LLM) → F construct/summary(mock LLM) → G embed(1024) → H search 语义命中 → I 断言使用链(`assert_used_real_chain`+`assert_vector_authentic`) → J 防假绿标 non-delivery-quality。
- **Evidence pack（每 phase 收口）+ DoD**：
  - **RW-A**：工厂按 env 返正确实现 + 默认 mock + **全库 1024 一致(grep 1536 残留=0)** + 维度守卫 fail-loud + 装配回归全绿（234+ 不回归）。Evidence：分支单测 + grep 残留 + 全量 pass。
  - **RW-B**：mock capstone 语义命中 + 使用链证据 + 本地文件↔SQLite digest 对账 + 规则化 fallback 仍绿 + 防假绿门禁过。Evidence：e2e + 对账失败用例 + 门禁扫描。

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| **1024 迁移回归** | RWA-09 改 vec.sql/schema/store/LocalEmbedder | 写/查维度不一致、旧数据撞 CHECK | 单点维度常量 + 守卫泛化 `!=self.dimension` + grep 1536 残留=0 + 全量门禁；本轮无历史数据(restart-only [Q4]) |
| 装配面大改回归 | RWA-04 替多处硬编码 | 写/查 embedder 不一致 | 工厂单点 + 写查同实例断言 + 全量回归 |
| prompt 文件↔DB 漂移 | 本地文件改了未同步 SQLite | SSOT 不一致、跑到旧 prompt | RWB-02 digest 对账 fail-loud(不一致即拒) |
| mock 假绿 | mock 响应当真质量 | 重蹈 part-cr-8 | mock 仅验使用链+结构, 标 non-delivery; 质量只在后续 live |
| 范围蔓延进 live | 误把 RW-C/RW-D 拉进本轮 | 撞未定 provider gate、超范围 | §3.2 明确 SCOPE↓ 延后；§7.B framework-closed 标注 |
| MLX 维度假设落空 | 后续选的 1024 模型其实非 1024 | live 期撞 schema | 本轮锁 1024 + 守卫 fail-loud; 1024 对本地神经友好(bge/e5/gte-large 原生 1024) |

---

## 10. 后继解锁 + action-plan 派生图

- **解锁的下游价值**：mock 下端到端语义管线骨架（可被真实接线）；prompt 可运营（本地文件编辑 + SQLite-SSOT + digest 对账）；全库 1024 维就绪；为后续 provider charter 留好接口+路由插槽。

### 10.A action-plan 派生与排序

> final 的 §6 phase 簇 **1:1 映射**下游 action-plan 文件。

| phase 簇 | 派生的 action-plan 文件 | 台账 ID 区间 | 时序 / 依赖 |
|----------|--------------------------|--------------|-------------|
| RW-A | `docs/action-plan/real-wire/RW-A-provider-base.md` | RWA-01..09 | **第 1（keystone，不依赖 gate）**；内部 RWA-09(1024 迁移) 前置于 RWA-04/05/07 |
| RW-B | `docs/action-plan/real-wire/RW-B-prompt-ssot-chain.md` | RWB-01..08 | **第 2**（依赖 RW-A 的接口/工厂/mock/1024）；mock 下，无待决 gate |
| RW-C（延后）| —（后续 provider charter 派生）| RWC-01..06 | 待 provider adapter / 计费 / 外部 key 关闭 |
| RW-D（延后）| —（后续轮派生）| RWD-01..05 | 待 PDF 需求 / vec0 瓶颈 |

---

## 11. Final recommendation

- **推荐序列**：派生并执行 **RW-A action-plan（keystone：协议接口 + 工厂 + 默认 mock + 装配注入 + 1024 全库迁移 + 测试原语，先红后绿）→ RW-B action-plan（本地文件 + SQLite-SSOT prompt 链 + structurize/summary/clean 去桩走 MockLLM + mock capstone + 防假绿）**；两者皆 mock、零外网、零计费、零外部依赖。本轮终点 = mock capstone 语义命中 + 使用链证据全绿。RW-C/RW-D 待后续 provider charter。
- **一句话总结**：final 据冻结 qna 把 real-wire 收敛为「**可被真接线的 mock 骨架**」——维度迁 1024、prompt 走本地文件/SQLite-SSOT、provider 留插槽，派生 RW-A/RW-B 两份 action-plan，真实模型留待下一 charter。

---

## 12. HEAD 代码实测 / 净新章节【新增章节】

| # | HEAD 事实（实测锚 file:line）| 对前序前提的修正 | 处置 |
|---|--------------------------------|------------------|------|
| ARCH-RW1 | `vec.sql:22,43` CHECK=1536、`schema.py:34` vec0 float[1536]、`store.py` INSERT 字面 1536、`embedder.py:82` 守卫 `!=DIMENSION(1536)` | proposed `MIG-RW-4=不做(锁 1536)` 被 Q-RW-1 **推翻**→ 必迁 1024 | RWA-09 全库迁移 + 守卫泛化 |
| ARCH-RW2 | `config_repo.py:31-49` `get_active_prompt` 存在但 **0 消费方**；`prompt_versions` DDL 有 `template_digest` 列 | proposed 设「KV 导出 vs 重写」前提被 Q-RW-3 **改为本地文件+SQLite-SSOT**；digest 列正是文件↔DB 对账载体 | RWB-02/03 接消费 + digest 对账(MIG-RW-5) |
| ARCH-RW3 | reference-anchor §5：可借皆协议/算法/schema，Cloudflare binding 全 ⛔；MLX/real 仅 macOS、不进默认 Linux CI | proposed 把 RW-C(live) 列入本轮关键路径；reframe **推翻**→ live 延后 | RW-C/RW-D SCOPE↓；本轮关键路径=RW-A→RW-B(mock) |
| ARCH-RW4 | [Q4] restart-recovery only（无历史向量数据需回填）| 降低 RWA-09 迁移风险（无存量 1536 数据需重嵌入）| 迁移以 schema+常量为主，无数据回填 |

---

## 13. 冻结槽

### 13.A owner-decision-freeze（QnA 裁决索引，NORMATIVE）

| Q | 主题 | 冻结结论（下游唯一口径）| 来源 |
|---|------|--------------------------|------|
| Q-RW-1 | embedding 维度 + 路线 | 维度=**1024**（覆盖 [Q2] 1536）; embedding 仅本地 MLX/macOS; 本轮接口+mock(1024)+路由+1024 迁移, MLX 模型 adapter 延后 | pre-charter-qna register |
| Q-RW-2 | LLM provider | provider adapter（本地 MLX vs 外部厂商）延后; 本轮协议接口+MockLLMProvider+路由 | 同上 |
| Q-RW-3 | prompt 来源 | 本地文件 + SQLite-SSOT + 文件↔DB hash 对账（替代 Cloudflare KV）; 正文据 schema 本地编写 | 同上 |
| Q-RW-4 | PDF/二进制 | 本轮不接, RW-D 上半段延后 | 同上 |
| Q-RW-5 | 真实 vec0 | 延后, 维持暴力 cosine | 同上 |
| Q-RW-6 | 计费/速率 | 框架定(默认 mock+fail-loud); 数值随 provider 延后 | 同上 |
| Q-RW-7 | 密钥管理 | `.env`+构造注入定; 外部厂商 key 需求随 provider 延后; app 自身 api-key 不受影响 | 同上 |
| reframe | 本轮范围 | mock + 占位 + 初始接口 + 预留/真接 mock↔real 路由 + 测 mock; provider adapter 延后 | 同上（最高口径）|

---

## 14. 交叉引用与修订历史

- **交叉引用**：`pre-charter-qna.md`（frozen，最高口径）、`reference-anchor-by-opus.md`（锚定台账）、`proposed-planning-by-opus.md`（被取代）、`state-analysis-after-FF7-by-opus.md`、`owner-gated-qna.md`、`tools/scripts/check_assert_strength.py`。

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v1.0 | 2026-06-01 | Opus 4.8 | final 定档（stage=final）：取代 initial+proposed。§2.C critique vs proposed（含 GAP=RWA-09 1024 迁移、CORRECT=RWB-01 本地文件+SQLite-SSOT、SCOPE↓=RW-C/RW-D 延后）；§6 RW-A/RW-B action-plan 绑定（lane/exit/evidence/migration/[Q]）；§7.B 全 gate 由冻结 Q 关闭；§12 HEAD 实测 4 条修正前序前提；§13.A 冻结槽索引。派生 2 份 action-plan（RW-A/RW-B），RW-C/RW-D 延后至后续 provider charter |
