# 行动计划 · RW-A — provider 基座 + mock + 路由 + 1024 维迁移

> 服务业务簇: `real-wire / provider 基座（LLM / Embedder / VectorIndex 协议 + 工厂 + mock + 路由 + 维度迁移）`
> 计划对象: `RW-A phase（final-execution-plan §6.A，台账 RWA-01..09）`
> 类型: `new + migration + refactor`（协议净新 / 1024 维迁移 / 装配注入重接）
> 作者: `Opus 4.8`
> 时间: `2026-06-01`
> 文件位置: `packages/rag_vectorizer/ · packages/vector_sqlite_vec/ · packages/config/ · packages/providers_dedicated/(范式参照) · packages/workflow_rag/ · packages/management/ · apps/worker/ · tests/`
> 上游前序 / closure:
> - `docs/eval/real-wire/final-execution-plan-by-opus.md` §6.A / §7.B（gate CLOSED）
> - first-fixes 全收口（234 passed + 1 xfailed）
> 下游交接:
> - `docs/action-plan/real-wire/RW-B-prompt-ssot-chain.md`（消费本 AP 的协议/工厂/mock/1024）
> 关联设计 / 调研文档:
> - `docs/eval/real-wire/proposed-planning-by-opus.md`（被 final 取代，历史 Δ 基线）
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 A 锚定矩阵）
> 冻结决策来源:
> - `docs/eval/real-wire/pre-charter-qna.md`（frozen；只读引用 Q-RW-1/2/7 + reframe）
> grounding 来源:
> - `eval-reference-anchor 轴 A`（§7 内置锚区据此摘录）+ HEAD 实测（本 AP 期亲验 file:line）
> 关联 reference-anchor:
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（§7.3 指回真源）
> 文档状态: `draft`

---

## 0. 执行背景与目标

real-wire 的近期范围被冻结 qna 的 reframe 定义为「**mock + 占位 + 初始接口 + 预留/真接 mock↔real-wire 路由 + 测 mock**」，provider adapter（本地 MLX vs 外部厂商）延后至后续 charter。RW-A 是这条收敛后路线的 **keystone**：它把「能被真实接线」的协议接口、工厂、默认 mock 实现、路由开关、以及 **全库维度 1536→1024 迁移**一次性铺好，使后续 RW-B（prompt 语义链）能在一致的 1024 维管线上、经 mock provider 端到端跑通。本 AP 不依赖任何 OPEN gate（§7.B 全 CLOSED）。

- **服务业务簇**：`real-wire / provider 基座`
- **计划对象**：`RW-A phase（RWA-01..09）`
- **本次计划解决的问题**：
  - HEAD 的 embedding/向量库**硬编码维度 1536**，与冻结裁决 1024 冲突（`vec.sql:22,43,59`、`schema.py:34`、`store.py:65,199`、`embedder.py:21`）。
  - HEAD 的 embedding 实例**全程硬编码 `default_embedder()`**（`search.py:42`、`workflow_rag/service.py:186,243,263`、`management/service.py:84,98`），无 mock/live 切换、无工厂注入。
  - 无 `LLMProvider` 协议、无 mock LLM 层、无 provider 路由开关——RW-B 的 prompt→LLM 链无处挂载。
- **本次计划的直接产出**：
  - `LLMProvider` 协议 + `MockLLMProvider`（读固定响应，未命中 fail-loud）。
  - provider 工厂 `make_llm / make_embedder / make_vector_index`（按 `Settings` 选，未知 fail-loud）+ `Settings` 扩 provider/model 字段（默认 mock/local/bruteforce，外部 key 字段预留）。
  - 全库维度 **1536→1024** 迁移 + 维度守卫泛化 `!= self.dimension`。
  - 全部 embedding 注入点改走工厂（写/查同 embedder 实例），eval corpus 装载器 + real-wire 测试原语，先红后绿全绿（234+ 不回归）。
- **本计划不重新讨论的设计结论**：
  - 向量维度 = **1024**，embedding 仅本地 MLX/macOS（来源：`Q-RW-1`，覆盖 [Q2] 1536）。
  - LLM provider adapter（本地 vs 外部）**延后**；本轮只做协议接口 + Mock + 路由（来源：`Q-RW-2` + reframe）。
  - 密钥用 `.env`（git-ignored）+ 构造注入；外部厂商 key 本轮预留不填（来源：`Q-RW-7`）。

---

## 1. 执行综述

### 1.1 总体执行方式

**先底层后上层 + 先协议后实现 + 先红后绿**：先把维度迁到 1024 并定义协议（substrate），再建工厂/Settings/mock（路由层），再把全部硬编码注入点改走工厂（装配层），最后铺 eval corpus / 测试原语并红→绿收口。维度迁移排第一，因为整条管线（写/查/mock）必须先在 1024 上自洽，否则后续注入与 mock 都建立在不一致维度上。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 维度 1024 迁移 + 协议定义 | M | 全库 1536→1024 一致 + `LLMProvider`/`Embedder`/`VectorIndex` 协议就位 | - |
| Phase 2 | Settings + provider 工厂 + Mock 实现 | M | 路由层：按 env 选 provider，默认 mock/local/bruteforce，未知 fail-loud | Phase 1 |
| Phase 3 | 装配工厂注入（替硬编码） | L | 全部 embedding 注入点走工厂；写/查同实例 | Phase 2 |
| Phase 4 | eval corpus + 测试原语 + 红绿收口 | M | 样本装载 + `assert_used_real_chain` + 全量回归绿 | Phase 3 |

### 1.3 Phase 说明

1. **Phase 1 — 维度 1024 迁移 + 协议定义**
   - **核心目标**：全库维度统一 1024 + 三协议（含新 `LLMProvider`）就位。
   - **为什么先做**：管线写/查/mock 必须先在同一维度自洽；协议是后续工厂/mock 的类型契约。
2. **Phase 2 — Settings + provider 工厂 + Mock 实现**
   - **核心目标**：路由 substrate——`Settings` 选型 + 工厂分发 + `MockLLMProvider` + mock embedding。
   - **为什么放在这里**：协议定好后才能实现工厂返回类型；默认必须落在 mock/local（TR-5 不打外网）。
3. **Phase 3 — 装配工厂注入**
   - **核心目标**：把所有 `default_embedder()` 硬编码点改为工厂注入，保证写/查同一 embedder 实例。
   - **为什么放在这里**：工厂存在后才能替换；这是 high-risk 回归面，需在前两 Phase 绿后单独推进。
4. **Phase 4 — eval corpus + 测试原语 + 红绿收口**
   - **核心目标**：样本装载器 + 真实使用链断言原语 + 全量先红后绿。
   - **为什么放在这里**：测试设施验证前三 Phase；收口硬闸。

### 1.4 执行策略说明

- **执行顺序原则**：substrate（维度+协议）→ 路由（工厂+mock）→ 装配（注入）→ 测试收口。
- **风险控制原则**：维度迁移与装配注入各自单独 Phase + 全量回归门禁；维度常量单点化，杜绝散落字面。
- **测试推进原则**：每 Phase 先写红测（维度守卫红、工厂未知分支红、注入后写查一致红）再转绿；短途→spike，详见 §8。
- **文档同步原则**：迁移后更新 `vec.sql` 注释与相关 docstring 的「1536」表述；reference-anchor 的 deps.py 误锚在本 AP §7 已更正为 management/service.py。
- **回滚 / 降级原则**：维度迁移无历史数据回填（[Q4] restart-only）；若工厂引入回归，回退到直接 `default_embedder()` 并保留协议（接口不破）。

### 1.5 本次 action-plan 影响结构图

```text
RW-A provider 基座
├── Phase 1: 维度 1024 迁移 + 协议定义
│   ├── packages/vector_sqlite_vec/{vec.sql,schema.py,store.py}（1536→1024）
│   ├── packages/rag_vectorizer/embedder.py（DIMENSION + 守卫泛化）
│   └── packages/*/（LLMProvider/Embedder/VectorIndex 协议）
├── Phase 2: Settings + 工厂 + Mock
│   ├── packages/config/{settings.py,loader.py}（字段 + 工厂落点）
│   ├── packages/providers_*/（LLMProvider + MockLLMProvider）
│   └── provider 路由分发（按 Settings 枚举）
├── Phase 3: 装配工厂注入
│   ├── packages/rag_vectorizer/search.py:42
│   ├── packages/workflow_rag/service.py:186,243,263
│   └── packages/management/service.py:84,98
└── Phase 4: eval corpus + 测试原语 + 收口
    ├── .tmp/eval-fixtures/ + 装载器 + 精简可提交集
    └── tests/fixtures/primitives.py（assert_used_real_chain）+ 红绿全量
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `LLMProvider` 协议 + `MockLLMProvider`（接口 + mock + 未命中 fail-loud）。
- **[S2]** provider 工厂（`make_llm/make_embedder/make_vector_index`，按 `Settings` 选，默认 mock/local/bruteforce，未知 fail-loud）+ `Settings` 字段扩展（外部 key 预留）。
- **[S3]** 全库维度 **1536→1024** 迁移 + 维度守卫泛化。
- **[S4]** 全部 embedding 注入点改走工厂（写/查同实例）+ eval corpus 装载器 + 测试原语 + 红绿收口。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 真实 LLM / 真实 embedding 客户端（本地 MLX 模型 adapter）—— RW-C，provider charter 延后。
- **[O2]** 真实计费/速率/外部 key 落地 —— Q-RW-6/7 数值延后。
- **[O3]** prompt 链去桩、structurize/summary/clean —— RW-B。
- **[O4]** PDF/二进制、真实 vec0 —— RW-D 延后。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `LLMProvider` 协议 + Mock | in-scope | RW-B 的 prompt→LLM 链需挂载点 | — |
| 维度 1536→1024 迁移 | in-scope | 整条管线须在 1024 自洽（Q-RW-1）| — |
| 真实 MLX embedder 实现 | out-of-scope | provider adapter 延后（Q-RW-2 + reframe）| 后续 provider charter |
| 外部厂商 key 注入 | defer | Q-RW-7 外部 key 需求延后 | provider charter 定 provider |
| 真实 vec0 虚表 | out-of-scope | Q-RW-5 延后 | 暴力 cosine 撞瓶颈 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| RWA-09 | Phase 1 | 维度 1536→1024 全库迁移 | migrate | `vec.sql:13,22,43,59`、`schema.py:34`、`store.py:65,199`、`embedder.py:21` | 全库 1024 一致，grep 1536 残留=0 | RWA-T01 | medium |
| RWA-01 | Phase 1 | `LLMProvider` 协议（`complete`/`complete_json`→{text,usage}）| add | `packages/providers_*/...（新建）`、范式 `embedder.py:29`、`vector_index.py:23` | Protocol + 双方法签名就位 | RWA-T02 | low |
| RWA-03 | Phase 2 | `Settings` 增 provider/model 字段 + `env_file`，默认 mock/local/bruteforce，key 预留 | update | `settings.py:4-10` | 零配置即 mock 无外网，key 槽位备而不填 | RWA-T03 | low |
| RWA-02 | Phase 2 | provider 工厂 `make_llm/make_embedder/make_vector_index` | add | `loader.py:6`（新增工厂）、范式 `providers_dedicated/service.py:114-151` | 各分支返正确实现，未知 raise | RWA-T04 | medium |
| RWA-05 | Phase 2 | `MockLLMProvider`（读 `llm_responses.json`）+ mock embedding（LocalEmbedder@1024）| add | `packages/providers_*/...（新建）`、`embedder.py:66` | 未命中 fail-loud；mock embed=1024 维 | RWA-T05 | medium |
| RWA-04 | Phase 3 | 装配工厂注入（替全部 `default_embedder()` 硬编码，写/查同实例）| refactor | `search.py:42`、`workflow_rag/service.py:186,243,263`、`management/service.py:84,98` | 全注入点走工厂，写查同实例 | RWA-T06 | high |
| RWA-06 | Phase 4 | eval corpus 装载器 + `.tmp/eval-fixtures` + 精简可提交集 | add | `tests/fixtures/...（新建）`、`.tmp/eval-fixtures/` | 样本可载入测试 | RWA-T07 | low |
| RWA-07 | Phase 4 | real-wire 测试原语 `assert_used_real_chain` | add | `tests/fixtures/primitives.py` | 能断言 provider/embedder 被真调 | RWA-T08 | low |
| RWA-08 | Phase 4 | 先红后绿：工厂选型+默认 mock+1024 守卫+路由分发+装配回归 | add | `tests/...`、`tools/scripts/check_assert_strength.py` | 234+ 不回归；维度 !=1024 fail-loud | RWA-T01..T09 | medium |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 维度 1024 迁移 + 协议定义

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWA-09 | 维度 1536→1024 全库迁移 | a) 把维度常量单点化为 `DIMENSION = 1024`（`embedder.py:21`）；b) `vec.sql:22,43` CHECK `= 1536`→`= 1024`，`:59` `float[1536]`→`float[1024]`，`:13` 注释改 1024；c) `schema.py:34` vec0 `float[1536]`→`float[1024]`；d) `store.py:65,199` INSERT 字面 `1536`→引用维度常量（不再散落字面）；e) 维度守卫泛化为 `!= self.dimension`（`embedder.py:82`），`embed_text` 的 `dims != DIMENSION` 同步（`:101`）；f) grep 全仓 `1536` 残留=0（含 docstring）| `embedder.py:21,82,101`、`vec.sql:13,22,43,59`、`schema.py:34`、`store.py:65,199` | 全库 1024 一致，无 1536 残留 | RWA-T01 | grep `1536`=0 + 维度守卫红→绿 + 全量回归绿 |
| RWA-01 | `LLMProvider` 协议 | 按 HEAD `Embedder`(`embedder.py:29`)/`VectorIndex`(`vector_index.py:23`) 的 `Protocol` 范式新建 `LLMProvider`：`complete(prompt, **opts) -> {text, usage}`、`complete_json(prompt, schema, **opts) -> {text, usage}`；借 `ai_schemas.ts:170-179` 的双方法形状，不借 TS `Env` 注入 | `packages/providers_*/...（新建协议文件）` | Protocol + 双方法签名 + `@runtime_checkable` | RWA-T02 | 协议存在 + mock 实现满足 isinstance 检查 |

### 4.2 Phase 2 — Settings + provider 工厂 + Mock 实现

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWA-03 | `Settings` 扩展 | 在 `settings.py:4-10` 增字段：`llm_provider: str = "mock"`、`embedder_provider: str = "local-hash"`、`vector_index: str = "bruteforce"`、`llm_model: str | None = None`、（预留）`llm_api_key: str | None = None`、`embedder_model: str | None = None`；加 `env_file=".env"` 到 `SettingsConfigDict`；默认值确保**零配置即 mock/local/bruteforce、不打外网** | `settings.py:4-10` | 默认即 mock；`.env` 可覆盖；key 字段预留 None | RWA-T03 | 默认值测试 + env 覆盖测试 |
| RWA-02 | provider 工厂 | a) 在 `loader.py` 旁新增工厂 `make_llm(settings)`/`make_embedder(settings)`/`make_vector_index(settings)`；b) 各按 `Settings.*_provider` 枚举分发（如 `embedder_provider="local-hash"`→`LocalEmbedder`，`"mlx"`→延后占位抛 `NotImplementedError("deferred to provider charter")`）；c) **未知值 fail-loud** `raise ValueError(f"unknown provider: {v}")`；d) 复用 `providers_dedicated/service.py:114-151` 的 register/dispatch 范式（不引入全局可变状态）；e) 工厂为纯函数，按 settings 实例返回 | `loader.py:6`（旁新增）、范式 `providers_dedicated/service.py:114-151` | 三工厂按 env 返正确实现；未知 raise；mlx 槽位占位 | RWA-T04 | 各分支单测（mock/local/bruteforce/未知/mlx-占位）|
| RWA-05 | Mock 实现 | a) `MockLLMProvider(LLMProvider)`：构造接受 `responses: dict`（或读 `llm_responses.json` 路径）；b) `complete/complete_json` 按 prompt 的稳定 key（如 prompt sha256 或显式标签）查表；c) **未命中 fail-loud** `raise KeyError`/自定义 `MockResponseMissing`（机器可读 reason，TR-4）；d) mock embedding 直接复用 `LocalEmbedder`（`embedder.py:66`，现 1024 维）作默认/mock；e) mock 标注 non-delivery-quality（不冒充真实质量）| `packages/providers_*/...（新建）`、`embedder.py:66` | 命中返固定响应；未命中 fail-loud；mock embed=1024 | RWA-T05 | 命中/未命中两用例 + 维度=1024 断言 |

### 4.3 Phase 3 — 装配工厂注入

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWA-04 | 装配工厂注入 | a) 审计全部 embedding 调用点：`search.py:42`(`default_embedder()`)、`workflow_rag/service.py:186`(`.name`),`243`(`embedder=`),`263`(`.embed`)、`management/service.py:84,98`(`SearchService(...)` 构造)；b) 在装配边界（service 构造 / loader）改为经 `make_embedder(load_settings())` 注入，而非函数内硬编码；c) **保证写路径（vectorize）与查路径（search）取同一 embedder 实例/同一 provider 配置**（TR-3，防跨模型 cosine）；d) `default_embedder()` 保留为 mock/local 工厂的内部实现，不再被业务码直接调用；e) 边界情况：worker（`apps/worker/main.py` 经 workflow_rag 间接）随上游注入覆盖；f) grep 业务码 `default_embedder()` 直调点=0（仅工厂内部保留）| `search.py:42`、`workflow_rag/service.py:186,243,263`、`management/service.py:84,98` | 全注入点走工厂；写查同实例 | RWA-T06 | grep 业务码直调=0 + 写查同实例断言 + 234+ 回归绿 |

### 4.4 Phase 4 — eval corpus + 测试原语 + 红绿收口

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWA-06 | eval corpus | 装载器读 `.tmp/eval-fixtures/`（url/file 文本样本 + 期望片段）；提供精简可提交集（≤数 KB）入 `tests/fixtures/`，大样本留 `.tmp/`（git-ignored）；装载器返回结构化语料供 RW-B capstone 复用 | `tests/fixtures/...（新建）`、`.tmp/eval-fixtures/` | 样本可装载、可测试引用 | RWA-T07 | 装载测试 + 精简集进仓 |
| RWA-07 | 测试原语 | 扩 `tests/fixtures/primitives.py`：`assert_used_real_chain(...)` 断言 provider/embedder **被真实调用**（spy/计数，非仅返回值存在）；与 F7 的 `assert_vector_authentic` 协同 | `tests/fixtures/primitives.py` | 能断言使用链真实发生 | RWA-T08 | 原语自测（正/负例）|
| RWA-08 | 红绿收口 | 先红后绿覆盖：维度守卫(RWA-T01)、协议(RWA-T02)、Settings 默认(RWA-T03)、工厂分支含未知(RWA-T04)、mock 命中/未命中(RWA-T05)、注入写查一致(RWA-T06)；`check_assert_strength.py` 扫描新测；全量 234+ 不回归 | `tests/...`、`tools/scripts/check_assert_strength.py` | 全绿 + 断言强度门禁过 | RWA-T01..T09 | 全量 pass + 门禁 0 命中 |

---

## 5. Phase 详情

### 5.1 Phase 1 — 维度 1024 迁移 + 协议定义

- **Phase 目标**：全库维度统一 1024 + `LLMProvider` 协议就位。
- **本 Phase 对应编号**：`RWA-09` / `RWA-01`
- **本 Phase 新增文件**：`packages/providers_*/.../protocols.py`（`LLMProvider`）
- **本 Phase 修改文件**：`embedder.py:21,82,101`、`vec.sql:13,22,43,59`、`schema.py:34`、`store.py:65,199`
- **具体功能预期**：
  1. `DIMENSION = 1024` 单点定义；所有维度引用该常量，不散落字面。
  2. `vec.sql` 两处 CHECK 与 vec0 `float[]` 均为 1024；注释同步。
  3. `store.py` INSERT 不再写字面 `1536`，改引用维度常量或 namespace 维度。
  4. 维度守卫 `if len(out) != self.dimension: raise`（泛化），`embed_text` 的 `dims` 校验同步。
  5. grep 全仓 `1536` 残留=0（含 docstring/注释）。
  6. `LLMProvider` Protocol 双方法 + `@runtime_checkable`，签名稳定（{text, usage}）。
- **对应测试台账项**：`RWA-T01` / `RWA-T02`（详见 §8）
- **收口标准**：维度守卫红→绿 + grep 1536=0 + 协议 isinstance 检查通过。
- **本 Phase 风险提醒**：维度字面散落易遗漏——以 grep gate 兜底；[Q4] restart-only 无历史 1536 数据需回填，迁移以 schema+常量为主。

### 5.2 Phase 2 — Settings + provider 工厂 + Mock 实现

- **Phase 目标**：路由 substrate（选型 + 分发 + mock）。
- **本 Phase 对应编号**：`RWA-03` / `RWA-02` / `RWA-05`
- **本 Phase 新增 / 修改文件**：`settings.py:4-10`（改）、`loader.py`（旁增工厂）、`packages/providers_*/.../mock_llm.py`（新建）
- **具体功能预期**：
  1. `Settings` 默认 `llm_provider="mock"`/`embedder_provider="local-hash"`/`vector_index="bruteforce"`——零配置即离线 mock。
  2. `env_file=".env"` 接入；`.env` 可覆盖 provider/model；key 字段预留 None。
  3. 工厂三函数按枚举分发；`"mlx"` 等延后实现为占位 `NotImplementedError("deferred to provider charter")`。
  4. 未知 provider 值 **fail-loud** `ValueError`。
  5. `MockLLMProvider` 命中返固定响应、未命中 fail-loud（机器可读 reason）。
  6. mock embedding 复用 `LocalEmbedder`（1024 维）。
- **对应测试台账项**：`RWA-T03` / `RWA-T04` / `RWA-T05`
- **收口标准**：默认 mock 测试 + 工厂各分支（含未知/占位）+ mock 命中/未命中 全绿。
- **本 Phase 风险提醒**：默认值若误设为非 mock 会打外网——测试断言「零配置无外部调用」。

### 5.3 Phase 3 — 装配工厂注入

- **Phase 目标**：全部 embedding 注入点走工厂，写/查同实例。
- **本 Phase 对应编号**：`RWA-04`
- **本 Phase 修改文件**：`search.py:42`、`workflow_rag/service.py:186,243,263`、`management/service.py:84,98`
- **具体功能预期**：
  1. 业务码不再直调 `default_embedder()`；改经 `make_embedder(settings)` 注入。
  2. 写路径（vectorize, `workflow_rag/service.py:243,263`）与查路径（search, `search.py:42`）取同一 provider 配置。
  3. `management/service.py:84,98` 的 `SearchService(...)` 构造经工厂传入 embedder。
  4. worker 经 workflow_rag 间接覆盖。
  5. 失败/边界：provider 未知时构造期即 fail-loud（不延迟到查询期）。
- **对应测试台账项**：`RWA-T06`
- **收口标准**：grep 业务码直调=0 + 写查同实例断言 + 234+ 回归绿。
- **本 Phase 风险提醒**：high-risk 回归面（多点替换）——单独 Phase + 全量门禁；写查不一致会致跨模型 cosine 串味（TR-3）。

### 5.4 Phase 4 — eval corpus + 测试原语 + 红绿收口

- **Phase 目标**：测试设施 + 收口硬闸。
- **本 Phase 对应编号**：`RWA-06` / `RWA-07` / `RWA-08`
- **本 Phase 新增文件**：`tests/fixtures/`（corpus 装载器 + 精简集）、扩 `tests/fixtures/primitives.py`
- **具体功能预期**：
  1. corpus 装载器读 `.tmp/eval-fixtures/`，精简集进仓、大样本 git-ignored。
  2. `assert_used_real_chain` 用 spy/计数断言 provider/embedder 被真调（非仅存在）。
  3. 红绿覆盖 RWA-T01..T06；新测过断言强度门禁。
  4. 全量 234+ 不回归。
- **对应测试台账项**：`RWA-T07` / `RWA-T08` / `RWA-T09`
- **收口标准**：§8 全 PASS + 四元组证据齐全。
- **本 Phase 风险提醒**：测试原语若只验返回值不验调用，等于假绿——必须 spy 真实调用。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `Q-RW-1` 维度=1024 + embedding 仅本地 | `pre-charter-qna.md` | RWA-09 全库迁移；mock embed 1024 | blocked，回 qna |
| `Q-RW-2` provider adapter 延后；本轮接口+mock+路由 | `pre-charter-qna.md` | RWA-01/02/05 只做接口+mock+占位 | 不实装真实 client |
| `Q-RW-7` `.env`+构造注入；外部 key 预留 | `pre-charter-qna.md` | RWA-03 key 字段备而不填 | — |
| reframe 本轮=mock+接口+路由+测 mock | `pre-charter-qna.md`（最高口径）| 整个 RW-A 范围 | — |
| `[Q4]` restart-only | `owner-gated-qna.md` | RWA-09 无历史数据回填 | — |
| `[Q7]` 先红后绿 | `owner-gated-qna.md` | RWA-08 红绿铁律 | — |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `packages/rag_vectorizer/.../embedder.py:29` | `Embedder` Protocol | RWA-01 协议范式 | ✅ 复用 | 已建好，照此范式建 `LLMProvider` |
| A-2 | `packages/vector_sqlite_vec/.../vector_index.py:23` | `VectorIndex` Protocol | RWA-01 协议范式 | ✅ 复用 | 已建好别重写 |
| A-3 | `packages/rag_vectorizer/.../embedder.py:21,82,101` | `DIMENSION=1536` + 守卫 | RWA-09 改 1024 + 守卫泛化 | ♻️ 重 substrate | 单点化常量 |
| A-4 | `packages/vector_sqlite_vec/.../vec.sql:13,22,43,59` | 维度 CHECK + vec0 float[1536] | RWA-09 改 1024 | ♻️ 重 substrate | 4 处 |
| A-5 | `packages/vector_sqlite_vec/.../schema.py:34` | vec0 `float[1536]` DDL | RWA-09 改 1024 | ♻️ 重 substrate | — |
| A-6 | `packages/vector_sqlite_vec/.../store.py:65,199` | INSERT 字面 1536 | RWA-09 改引用常量 | ♻️ 重 substrate | 杜绝散落字面 |
| A-7 | `packages/config/.../settings.py:4-10` | `Settings` 字段 | RWA-03 扩字段 + env_file | ♻️ 重 substrate | 默认 mock/local |
| A-8 | `packages/config/.../loader.py:6` | `load_settings()@lru_cache` | RWA-02 工厂落点 | ✅ 复用 | 旁增 make_* |
| A-9 | `packages/providers_dedicated/.../service.py:114-151` | `ProviderRegistry` register/dispatch | RWA-02 工厂范式 | ✅ 复用 | 已验证可用范式 |
| A-10 | `packages/rag_vectorizer/.../embedder.py:66` | `LocalEmbedder` | RWA-05 作 mock embedding | ✅ 复用 | 1024 维后直接当 mock |
| A-11 | `packages/rag_vectorizer/.../search.py:42` | `default_embedder()` 查路径 | RWA-04 注入点 | ♻️ 重 substrate | 写查同实例 |
| A-12 | `packages/workflow_rag/.../service.py:186,243,263` | `default_embedder()` 写路径 | RWA-04 注入点 | ♻️ 重 substrate | vectorize step |
| A-13 | `packages/management/.../service.py:84,98` | `SearchService(...)` 构造 | RWA-04 注入点 | ♻️ 重 substrate | **更正 reference-anchor 的 deps.py 误锚** |
| A-14 | `tests/fixtures/primitives.py` | F7 测试原语底座 | RWA-07 扩 assert_used_real_chain | ✅ 复用 | — |
| A-15 | `legacy/.../cloudflare_ai/ai_schemas.ts:170-179` | IAiProvider 双方法协议 | RWA-01 协议形状借鉴 | 🔶 部分借 | 借形状不借 Env 注入（见 §7.3）|

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | provider 硬编码无开关（legacy 只 Gemini，`wrangler.toml`）| 无 mock/live 切换、不可离线测；本 AP 用 Settings 枚举 + 工厂分发，默认 mock |
| ⛔2 | API key 模块级闭包轮转（`gemini.ts:96-132`）| 全局可变状态难测、与注入冲突；本 AP key 字段预留、构造注入（Q-RW-7）|
| ⛔3 | 维度字面散落（`store.py` 字面 1536）| 改维度时易漏；本 AP 单点化常量 + grep gate |
| ⛔4 | 写/查 embedder 不一致 | 跨模型 cosine 串味（TR-3）；本 AP 写查同实例断言 |
| ⛔5 | mock 只验返回值不验调用 | 假绿（part-cr-8）；本 AP `assert_used_real_chain` spy 真实调用 |
| ⛔6 | 默认 provider 非 mock | 测试打外网（违 TR-5）；本 AP 默认 mock/local，断言零外部调用 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/real-wire/reference-anchor-by-opus.md`（轴 A）—— §7.1 是其与本 AP 相关子集的摘录；完整借鉴台账（✅借/🔶部分/⛔反例/🆕净新 + TR 过滤）见真源。**更正**：真源 §1.A 把 API embedding 注入点记为 `apps/api/deps.py:114-128`，HEAD 实测 deps.py 无 embedder 引用，实际在 `packages/management/service.py:84,98`（A-13）。
- **安全 / 信任边界类工作项**：本 AP 涉密钥的仅 RWA-03 的 `llm_api_key` 字段**预留不填**；威胁模型锚 = `Q-RW-7`（`.env` git-ignored + 构造注入 + 不入日志）+ 反例 ⛔2。本轮无真实 key 落地，无外网，威胁面最小；真实 key 注入的威胁模型在 RW-C charter 补。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| RWA-T01 | 维度守卫：embed 输出 !=1024 即 raise；全库 1024 一致 | 短途 | unit·契约 | 🆕 新增 `tests/.../test_dimension_1024.py` | RWA-09 → 全库 1024 | `commit + test PASS + grep 1536=0 + run-time` |
| RWA-T02 | `LLMProvider` 协议：mock 满足 isinstance + 双方法签名 | 短途 | unit | 🆕 新增 `test_llm_provider_protocol.py` | RWA-01 → 协议就位 | `commit + test + run-time` |
| RWA-T03 | `Settings` 默认即 mock/local/bruteforce；env 覆盖；零外部调用 | 短途 | unit | 🆕 新增 `test_settings_providers.py` | RWA-03 → 默认 mock | `commit + test + run-time` |
| RWA-T04 | 工厂三分支：mock/local/bruteforce 返正确类型；未知 raise；mlx 占位 NotImplementedError | 短途 | unit | 🆕 新增 `test_provider_factory.py` | RWA-02 → 按 env 选 | `commit + test + run-time` |
| RWA-T05 | `MockLLMProvider` 命中返固定响应；未命中 fail-loud；mock embed=1024 | 短途 | unit | 🆕 新增 `test_mock_llm_provider.py` | RWA-05 → mock + fail-loud | `commit + test + run-time` |
| RWA-T06 | 装配注入：业务码无直调 default_embedder()；写查同实例 | 短途 | 集成·回归 | 🔱 fork 既有 vectorize/search 测 + 注入断言 | RWA-04 → 写查同实例 | `commit + grep 直调=0 + 234+ PASS + run-time` |
| RWA-T07 | eval corpus 装载器：精简集可载 | 短途 | unit | 🆕 新增 `test_eval_corpus_loader.py` | RWA-06 → 样本可载 | `commit + test + run-time` |
| RWA-T08 | `assert_used_real_chain` 原语：真调过/未调 正负例 | 短途 | unit | 🆕 新增 `test_real_chain_primitive.py` | RWA-07 → 使用链断言 | `commit + test + run-time` |
| RWA-T09 | 全量回归 + 断言强度门禁 | 短途 | 回归·契约 | ♻️ 沿用 全量 pytest + `check_assert_strength.py` | RWA-08 → 234+ 不回归 | `commit + 全量 PASS + 门禁 0 命中 + run-time` |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| 既有 vectorize/search 集成测 | 🔱 fork → +注入断言 | + 写查同实例断言 | 已存在，PASS |
| 全量 pytest 套件（234 passed + 1 xfailed）| ♻️ 沿用 | 0 改动（迁移后须维持）| 已存在，纳入回归 |
| `tools/scripts/check_assert_strength.py` | ♻️ 沿用 | 0 改动 | 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·集成·契约·回归 | 开发中持续 |
| spike | RW-B capstone（本 AP 不含）| e2e | RW-B |
| mega / soak | 本轮 N/A（live 延后）| — | — |

### 8.4 测试缺口

- 不覆盖真实 LLM/embedding 调用（理由：provider adapter 延后）→ 交后继 RW-C charter；**本 AP 不假装覆盖**。
- 不覆盖 mock capstone 语义命中（理由：属 RW-B 链路）→ 交 RW-B。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 带四元组；计数 ≠ 价值。
- mock 标 **non-delivery-quality**；`assert_used_real_chain` spy 真实调用而非仅返回值。
- 维度迁移以 grep `1536`=0 作硬证据，不靠「测试数变多」糊弄。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| 1024 迁移残留 | 字面 1536 散落漏改 | medium | 常量单点化 + grep gate=0 + 守卫泛化 |
| 装配注入回归 | 多点替换致写查不一致 | high | 单独 Phase + 写查同实例断言 + 全量门禁 |
| 默认误打外网 | provider 默认非 mock | low | 默认 mock + 零外部调用断言（TR-5）|
| 工厂占位误用 | mlx 占位被当可用 | low | NotImplementedError 机器可读 reason |

### 9.2 约束与前提

- **技术前提**：Python 3.12；离线无 numpy/torch/sentence-transformers/sqlite_vec（mock/local 路径不依赖）。
- **运行时前提**：默认 mock/local/bruteforce、不打外网（TR-5）；real MLX 在 macOS（本轮不涉及）。
- **组织协作前提**：无外部 key（Q-RW-7 预留）。
- **上线 / 合并前提**：全量 234+ 不回归 + 断言强度门禁过。

### 9.3 文档同步要求

- 需更新：`vec.sql` 注释（1536→1024）、`embedder.py` docstring（[Q2] 1536 表述标注被 Q-RW-1 覆盖为 1024）。
- 需同步：本 AP §7 已更正 reference-anchor 的 deps.py 误锚。
- 测试说明：新测文件登记入 `tests/` README（如有）。

### 9.4 完成后的预期状态

1. 全库维度统一 1024，无 1536 残留，维度守卫 fail-loud。
2. `LLMProvider`/`Embedder`/`VectorIndex` 三协议 + 工厂 + Settings 路由就位，默认 mock/local/bruteforce 零外网。
3. `MockLLMProvider` + mock embedding（1024）可用，未命中 fail-loud。
4. 全部 embedding 注入点走工厂，写查同实例。
5. eval corpus + 测试原语就位，全量 234+ 不回归——RW-B 可在此基座上接 prompt 链。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

1. 全库 1024 一致、grep `1536`=0（由 `RWA-T01` 证明）。
2. 工厂按 env 选型 + 默认 mock + 未知 fail-loud（由 `RWA-T03/T04` 证明）。
3. 全部注入点走工厂、写查同实例（由 `RWA-T06` 证明）。
4. 全量 234+ 不回归 + 断言强度门禁 0 命中（由 `RWA-T09` 证明）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| 全库 1024 一致 | RWA-09 | RWA-T01 | `commit+test+grep+time` | 未观察 |
| `LLMProvider` 协议就位 | RWA-01 | RWA-T02 | `commit+test+time` | 未观察 |
| 默认 mock/local | RWA-03 | RWA-T03 | `commit+test+time` | 未观察 |
| 工厂按 env 选型 | RWA-02 | RWA-T04 | `commit+test+time` | 未观察 |
| mock + fail-loud | RWA-05 | RWA-T05 | `commit+test+time` | 未观察 |
| 写查同实例 | RWA-04 | RWA-T06 | `commit+grep+回归+time` | 未观察 |
| 样本可载 | RWA-06 | RWA-T07 | `commit+test+time` | 未观察 |
| 使用链断言 | RWA-07 | RWA-T08 | `commit+test+time` | 未观察 |
| 全量不回归 | RWA-08 | RWA-T09 | `commit+全量PASS+门禁+time` | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 三协议+工厂+mock+1024 迁移+装配注入就位 |
| 测试 | §8 全 PASS（退出硬闸四元组齐全）|
| 文档 | vec.sql/embedder docstring 维度表述同步；deps 误锚更正 |
| 风险收敛 | 1024 残留=0；写查一致；默认零外网 |
| 可交付性 | RW-B 可在此基座挂 prompt 链 |

### 10.4 NOT-成功识别

> 任一退出硬闸 `degraded / 未观察` ⇒ 不得标 `executed`；按 closure 五态如实归类 + handoff。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

- **实际执行摘要**：`（待执行回填）`
- **Phase 偏差**：`（待回填）`
- **阻塞与处理**：`（待回填）`
- **测试发现**：`（待回填）`
- **后续 handoff**：`RW-B`
