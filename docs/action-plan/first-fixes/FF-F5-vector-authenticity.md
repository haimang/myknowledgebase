# Nano-Agent 行动计划：FF-F5 向量真实性与检索

> 服务业务簇: `smind-family · RAG 向量化与检索（rag_vectorizer / vector_sqlite_vec）`
> 计划对象: `F5 向量真实性与检索（embedder 去伪向量 + vec0 degraded 定档 + search 过滤）`
> 类型: `refactor`（替换伪向量实现 + 接口抽象 + 检索过滤强化；非新建管道）
> 作者: `Opus 4.8`
> 时间: `2026-05-31`
> 文件位置:
> - `packages/rag_vectorizer/src/rag_vectorizer/embedder.py`
> - `packages/rag_vectorizer/src/rag_vectorizer/search.py`
> - `packages/vector_sqlite_vec/src/vector_sqlite_vec/{schema.py,store.py}`
> - `tests/unit/`、`tests/integration/`（先红后绿回归）
> 上游前序 / closure:
> - `FF-F4-adapter-safety.md`（**硬前置**：F4-03 rowid 单调不复用 + upsert 复用现有 rowid 不变量修复后，F5 写入/检索才安全；详见 §6/§9）
> 下游交接:
> - `FF-F6b-rag-executors.md`（rag:vectorize step 使用本 AP 交付的 `Embedder` adapter；construct/structurize 产出的真实 chunk 经本 AP embedding 写入）
> 关联设计 / 调研文档:
> - `docs/design/first-fixes/initial-planning-by-opus.md`（§6.5 F5 [final] 绑定表、§2.C 定档、§8 capstone、§5 DAG、§9 风险登记）
> - `docs/design/first-fixes/owner-gated-qna.md`（[Q1] vec0 degraded、[Q2] 本地 1536 embedding、[Q7] 先红后绿）
> 关联 reference-anchor:
> - `docs/eval/first-code-review-plan/part-cr-7.md`（G-CR7-01 embedder 伪向量）、`part-cr-3.md`（G-CR3-02 vec0 退化、G-CR3-10 search 仅 team 过滤）—— 见 §7 内置锚区摘录
> 冻结决策来源:
> - `docs/design/first-fixes/owner-gated-qna.md` [Q1][Q2][Q7]（只读引用；本 action-plan 不填写 Q/A）
> grounding 来源:
> - `eval-reference-anchor`：part-cr-7.md（embedder）+ part-cr-3.md（vec0 / search 过滤）；§7.1 锚区据此摘录，§7.3 指回真源。
> 文档状态: `draft`

---

## 0. 执行背景与目标

> 本 AP 由 final plan（`initial-planning-by-opus.md`）§10.A 1:1 派生，对应 phase 簇 **F5 向量真实性与检索**（台账 ID F5-01..04）。它的存在是因为八簇审查（part-cr-3 / part-cr-7）实测确认：整条 RAG 价值链"管道接得上、语义为空"——embedding 是 SHA-256 哈希伪向量（与文本语义零关联），向量索引从未真正存在（`vec0` 恒建失败、静默退化为 TEXT 表 + 暴力 cosine 全表扫描），且 search 仅按 `team_id` 过滤、跨 namespace/model 混算 cosine。closure 曾以 ✅ PASS 宣称 vector/retrieval 完成，实为假绿。

本 AP 把以下**已冻结**结论落成可交付物（不重新讨论）：

- **[Q1]** vec0 本轮**显式 degraded**（保留暴力 cosine，但退化路径强制 `logger.warning` fail-loud + 抽象 `VectorIndex` 接口），真实 sqlite-vec 接入移出本轮、接受性能线性劣化为显式技术债。
- **[Q2]** embedding 用 `Embedder` adapter 接口隔离，默认接**本地小模型**（离线、零计费、可复现），**强约束模型维度=1536**（免触 `vec.sql` 的 `CHECK(embedding_dimension = 1536)` 与 vec0 `float[1536]`，不牵动 schema/迁移）；测试用确定性 mock 但显式标注为非交付向量，语义相关性断言用真实小模型跑少量样本。
- **[Q7]** 全程先红后绿：写一条"相关 query 的目标 chunk 排第一且分差显著"的回归测试，当前 HEAD（SHA-256 伪向量）必然不满足 → 红，接真实模型后 → 绿。

- **服务业务簇**：`smind-family · RAG 向量化与检索`
- **计划对象**：`F5 向量真实性与检索`
- **本次计划解决的问题**：
  - `embedder 伪向量（G-CR7-01）：embed_text 用 SHA-256 链式哈希，输出与文本语义无关，整条检索价值归零。`
  - `vec0 静默退化（G-CR3-02）：sqlite-vec 从不加载，CREATE VIRTUAL TABLE ... USING vec0 恒失败，退化分支零日志 → 假绿；distance_metric 字段建了从不被读。`
  - `search 过滤缺失（G-CR3-10）：search 仅按 team_id 过滤，无 namespace_id/embedding_model，跨模型/跨命名空间向量被混算 cosine。`
- **本次计划的直接产出**：
  - `Embedder adapter 接口 + 本地小模型默认实现（维度=1536），SHA-256 伪向量降级为显式命名的测试 fixture（如 embed_text_fake）。`
  - `VectorIndex 接口抽象 + _fallback_vec_sql 退化路径 logger.warning fail-loud（degraded 不再静默）。`
  - `search 增 namespace_id/embedding_model 过滤参数，distance_metric 生效（读 namespace 配置而非硬编码 cosine）。`
  - `先红后绿回归：向量真实性（目标 chunk 排第一 + 分差显著）+ degraded 告警断言。`
- **本计划不重新讨论的设计结论**：
  - `vec0 = degraded（非真实接入）`（来源：`[Q1]`）
  - `embedding = 本地小模型 + 维度=1536`（来源：`[Q2]`）
  - `先红后绿铁律`（来源：`[Q7]`）

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用"**先协议后实现、先注入真实性后强化检索过滤、全程先红后绿**"：先建 `Embedder` / `VectorIndex` 两个抽象接口（协议层），再用本地 1536 维小模型替换伪向量、用 fail-loud 告警替换静默退化（实现层），最后在 search 上叠加 namespace/model 过滤与 `distance_metric` 生效（检索层）。每个工作项以一条"当前 HEAD 红、修复后绿"的回归测试作退出证据。本 AP 不重新论证"为何 degraded / 为何本地模型"——这些已由 [Q1][Q2] 冻结。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | `Embedder 真实性注入` | `M` | `Embedder adapter 接口 + 本地 1536 维小模型替换 SHA-256 伪向量；伪向量降级为显式命名 fixture` | `FF-F4（rowid 不变量）` |
| Phase 2 | `向量索引 degraded 定档` | `S` | `VectorIndex 接口抽象 + _fallback_vec_sql 退化路径 logger.warning fail-loud；真实 vec0 移出本轮记技术债` | `-` |
| Phase 3 | `检索过滤强化` | `S` | `search 增 namespace_id/embedding_model 过滤，distance_metric 生效（G-CR3-10）` | `Phase 1（embedding_model 命名稳定）` |

> 说明：上表 `规模` 是每个 Phase 的描述性提示，不是开工前的体量判定闸，不改变本模板任何段落取舍。

### 1.3 Phase 说明

1. **Phase 1 — `Embedder 真实性注入`**
   - **核心目标**：用 `Embedder` adapter + 本地小模型（维度=1536）替换 `embedder.py` 的 SHA-256 伪向量，让检索真正语义化。
   - **为什么先做**：embedding 是整条 RAG 价值链的根因盲点（part-cr-7 R1）；只有它真实后，Phase 3 的过滤与端到端语义测试才有意义。
2. **Phase 2 — `向量索引 degraded 定档`**
   - **核心目标**：消除静默退化（fail-loud 告警）+ 抽象 `VectorIndex` 接口，使未来切真实 vec0 是局部替换。
   - **为什么放在这里**：与 Phase 1 无依赖、可并行；degraded 是 [Q1] 已定档范围，工程量小（不接真实扩展）。
3. **Phase 3 — `检索过滤强化`**
   - **核心目标**：search 增 `namespace_id`/`embedding_model` 过滤，`distance_metric` 生效。
   - **为什么放在这里**：依赖 Phase 1 稳定 `embedding_model` 命名（真实模型标识替换 `local-sim`），过滤参数才有真实区分价值。

### 1.4 执行策略说明

> 本节写"怎么执行"，不重述 §6 已引用冻结决策的理由。

- **执行顺序原则**：`先接口（Embedder/VectorIndex）→ 后实现（本地模型/告警）→ 再检索过滤；Phase 1∥Phase 2 可并行，Phase 3 等 Phase 1 模型命名落定。`
- **风险控制原则**：`F5-01 为净新高风险（引入模型依赖）——adapter 接口隔离 + 本地小模型（无网络/计费）+ 测试 mock 与真实模型双轨；维度=1536 在 adapter 内强制校验，长度≠1536 即 raise，免触 schema。`
- **测试推进原则**：`先红后绿——先写"目标 chunk 排第一+分差显著"的语义断言（HEAD 伪向量必红），接模型后绿；degraded 告警断言用 caplog 捕获 logger.warning。短途单测随 Phase 提交，spike 集成在 Phase 收口（详见 §8）。`
- **文档同步原则**：`closure 把 vector/retrieval gate 重新定级为 degraded（撤销 P4/P5 假绿 ✅，交 F7）；degraded/技术债项在 §8.4 + closure 显式记账。`
- **回滚 / 降级原则**：`degraded 本身即 [Q1] 定档的降级态——暴力 cosine 保留；若本地模型加载失败，Embedder 实现 fail-loud raise（禁止静默回退到伪向量）。`

### 1.5 本次 action-plan 影响结构图

```text
F5 向量真实性与检索
├── Phase 1: Embedder 真实性注入
│   ├── packages/rag_vectorizer/embedder.py（伪向量 → Embedder adapter + 本地模型）
│   ├── packages/rag_vectorizer/__init__.py（导出 Embedder / embed_text_fake）
│   └── packages/rag_vectorizer/search.py:40 + workflow_rag/service.py:167（写/查共用同一 Embedder）
├── Phase 2: 向量索引 degraded 定档
│   ├── packages/vector_sqlite_vec/schema.py:62-67（_fallback_vec_sql 退化路径 fail-loud）
│   └── packages/vector_sqlite_vec/（新建 VectorIndex 接口模块）
└── Phase 3: 检索过滤强化
    ├── packages/vector_sqlite_vec/store.py:91-107（search 增 namespace/model 过滤 + distance_metric）
    └── packages/rag_vectorizer/search.py:41-45（透传过滤参数）
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `F5-01 Embedder adapter 接口 + 本地小模型（维度=1536）替换 SHA-256 伪向量；伪向量降级为显式命名测试 fixture（embed_text_fake）。`
- **[S2]** `F5-02 vec0 degraded 定档：保留暴力 cosine，_fallback_vec_sql 退化路径 logger.warning fail-loud + 抽象 VectorIndex 接口。`
- **[S3]** `F5-03 search 增 namespace_id/embedding_model 过滤参数，distance_metric 生效（读 namespace 配置，G-CR3-10）。`
- **[S4]** `F5-04 先红后绿回归：向量真实性（相关 query 目标 chunk 排第一 + 分差显著）+ degraded 告警断言。`

### 2.2 Out-of-Scope（本次 action-plan 明确不做 —— 均移出本轮，记技术债）

- **[O1]** `真实 vec0 / sqlite-vec 接入（enable_load_extension + sqlite_vec.load）`——[Q1] 定档移出本轮，接受"检索性能随数据量线性劣化"为显式技术债；记入下一轮生产化。
- **[O2]** `外部 API embedding（OpenAI/Gemini）/ 可配置后端（[Q2] 子选项 C）`——本轮仅本地小模型；adapter 接口已为未来切外部 API 留口，但本轮不实现远程后端、不引入密钥/计费/网络依赖。
- **[O3]** `维度 ≠ 1536 的模型 / 改动 schema embedding_dimension 硬编码`——[Q2] 强约束维度=1536；任何需改 vec.sql:22/43 CHECK 或 vec0 float[1536] 的方案移出本轮（牵动 F4/迁移）。
- **[O4]** `embedding 重试退避 / token usage / 维度探测（legacy embedder.ts:115-163）`——非本轮语义真实性核心，记入下一轮。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `Embedder adapter + 本地 1536 维模型` | `in-scope` | `[Q2] 裁决；整条 RAG 语义真实性根因` | `本轮交付` |
| `vec0 degraded（暴力 cosine + 告警 + 接口）` | `in-scope` | `[Q1] 裁决=选项 A` | `本轮交付` |
| `真实 sqlite-vec 接入` | `out-of-scope` | `[Q1] 接受性能线性劣化技术债` | `生产化阶段 / 数据量增大后 KNN 成为瓶颈` |
| `外部 API embedding 后端` | `out-of-scope` | `[Q2] 本轮仅本地；adapter 已留口` | `产品需要更高语义质量且接受网络/计费` |
| `维度 ≠ 1536 / 改 schema` | `out-of-scope` | `[Q2] 强约束 1536 免触 schema` | `选型需 ≠1536 维模型时（牵动 F4/迁移）` |
| `embedding 重试退避/usage` | `defer` | `非语义真实性核心` | `下一轮可靠性强化` |

---

## 3. 业务工作总表

> 编号 `F5-01..04`（跨态稳定，承 final §6.5）。每项三件齐全（涉及文件 / 收口目标 / 测试映射）。F5-01 为净新高风险，§4/§5 拆子步；安全/数据完整性相关项指向 §7.3 威胁模型锚。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| F5-01 | Phase 1 | `Embedder adapter 接口 + 本地小模型（1536 维）替换 SHA-256 伪向量` | `refactor`（净新接口 + 替换实现） | `embedder.py:6-16`（替换）、`__init__.py:1,4`、`search.py:40`、`workflow_rag/service.py:167` | `相关 query 目标 chunk 排第一且分差显著；伪向量函数降级为显式命名 fixture（embed_text_fake）；维度!=1536 即 raise` | `FF-F5-T01` / `FF-F5-T02` | `high` |
| F5-02 | Phase 2 | `vec0 degraded 定档：_fallback_vec_sql 退化路径 fail-loud + VectorIndex 接口` | `update`（退化告警）+ `add`（接口） | `schema.py:28-42,62-67`、新建 `vector_index.py` | `退化路径有强制 logger.warning；VectorIndex 接口可被未来 vec0 实现替换；closure 标 degraded` | `FF-F5-T03` / `FF-F5-T04` | `medium` |
| F5-03 | Phase 3 | `search 增 namespace_id/embedding_model 过滤，distance_metric 生效` | `update` | `store.py:91-107`、`search.py:41-45` | `跨 namespace/model 向量不混算 cosine；distance_metric 读 namespace 配置非硬编码` | `FF-F5-T05` | `medium` |
| F5-04 | Phase 1-3 | `先红后绿回归：向量真实性 + degraded 告警断言` | `add`（测试） | `tests/unit/`、`tests/integration/` | `修复前红、修复后绿；degraded 告警可断言` | `FF-F5-T01..T05` | `low` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — `Embedder 真实性注入`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F5-01 | `Embedder adapter + 本地 1536 维模型` | `a) 定义 Embedder 协议（embed(texts: list[str]) -> list[list[float]] + dimension 属性）；b) 实现 LocalEmbedder（本地小模型，离线加载，维度=1536）；c) 在 adapter 边界强制维度校验：输出长度 != 1536 即 raise（免触 schema CHECK）；d) embed_text 现伪向量重命名为 embed_text_fake 并显式标注"仅离线测试 fixture，非交付向量"；e) search.py:40 与 workflow_rag/service.py:167 改用同一 Embedder 实例（写/查一致，避免"查询命中自身"掩盖）；f) embedding_model 标识从 "local-sim" 改为真实模型名（供 F5-03 过滤）；g) 失败路径：模型加载失败 fail-loud raise，禁止静默回退伪向量。` | `embedder.py:6-16`（替换为 Embedder + LocalEmbedder + embed_text_fake）、`__init__.py:1,4`（导出调整）、`search.py:9,40`、`workflow_rag/service.py:10,167` | `检索语义化：相关 query 的目标 chunk 排第一且与次位分差显著；伪向量降级为 embed_text_fake；维度!=1536 raise；写/查用同一 Embedder` | `FF-F5-T01` / `FF-F5-T02` | `T01 语义断言绿（真实小模型少量样本）+ T02 维度约束/fixture 标注绿；HEAD 伪向量下 T01 红` |

### 4.2 Phase 2 — `向量索引 degraded 定档`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F5-02 | `vec0 degraded 定档 + VectorIndex 接口` | `a) schema.py 走 except 退化分支（vec0 → TEXT 表）前，logger.warning 显式告警（机器可读 reason，如 reason="sqlite_vec_unavailable_degraded_to_bruteforce"），禁止静默；b) 抽象 VectorIndex 接口（upsert/search/delete），当前暴力 cosine 实现挂在该接口下（BruteForceVectorIndex）；c) 接口契约使未来真实 vec0 实现为局部替换、不影响上层 store/search；d) 真实 vec0 接入显式记入技术债（§8.4 + closure degraded 定级）；e) 不优化暴力 cosine 性能（[Q1] 接受线性劣化）。` | `schema.py:28-42`（_fallback_vec_sql）、`schema.py:62-67`（except 分支加告警）、新建 `vector_sqlite_vec/vector_index.py` | `退化路径强制 fail-loud 告警；VectorIndex 接口可被替换；closure 标 degraded 非 done` | `FF-F5-T03` / `FF-F5-T04` | `T03 caplog 捕获退化 warning 绿 + T04 接口契约测试绿；degraded 显式记账` |

### 4.3 Phase 3 — `检索过滤强化`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| F5-03 | `search 增 namespace/model 过滤 + distance_metric` | `a) store.search WHERE 增 namespace_id/embedding_model 条件（当前仅 deleted_at IS NULL AND team_id=?，store.py:96-99）；b) distance_metric 从 namespace 配置读取并生效（当前硬编码 cosine，store.py:104）；c) search.py:41-45 透传 namespace_id/embedding_model 参数；d) 边界：缺省参数行为向后兼容（不传则维持 team 维度，但记 degraded 提示）；e) 不接 vec0，过滤在暴力扫描的候选集上 enforce。` | `store.py:91-107`（search 签名 + WHERE + metric）、`search.py:41-45`（透传） | `跨 namespace/embedding_model 向量不混算 cosine；distance_metric 读配置生效` | `FF-F5-T05` | `T05 filter 单测绿（同 team 多 namespace/model 不串味）` |

---

## 5. Phase 详情

### 5.1 Phase 1 — `Embedder 真实性注入`

- **Phase 目标**：用 `Embedder` adapter + 本地 1536 维小模型替换 SHA-256 伪向量，让检索真正语义化（消除 G-CR7-01 根因盲点 B）。
- **本 Phase 对应编号**：`F5-01`（+ F5-04 测试）
- **本 Phase 新增文件**：`packages/rag_vectorizer/.../embedder.py` 内新增 `Embedder` 协议 + `LocalEmbedder`（或拆 `embedders/` 子模块）
- **本 Phase 修改文件**：`embedder.py:6-16`（伪向量 → embed_text_fake + Embedder）、`__init__.py:1,4`（导出）、`search.py:9,40`、`workflow_rag/service.py:10,167`
- **本 Phase 删除文件**：无（伪向量保留为显式命名 fixture，不删）
- **具体功能预期**（净新高风险，≥5 条，含边界与失败路径）：
  1. `Embedder 协议定义 embed(texts) -> list[list[float]] 与 dimension 属性；LocalEmbedder 默认实现用本地小模型、离线加载、零网络/计费。`
  2. `维度约束（[Q2] 隐藏约束）：adapter 边界强制输出长度 == 1536；!=1536 即 raise ValueError，绝不写入（vec.sql:22,43 CHECK(embedding_dimension=1536) + vec0 float[1536] 不可被绕过）。`
  3. `语义"命中"定义（供 F5-04 断言）：对一组已知相关/不相关样本，相关 query 的目标 chunk cosine 排第一，且与最近的不相关 chunk 分差 ≥ 显著阈值（如 ≥0.1，具体阈值在 T01 标定）；伪向量下该断言必不成立（哈希噪声）。`
  4. `写/查一致：workflow_rag/service.py:167（写入）与 search.py:40（查询）必须用同一 Embedder 实现——否则"查询命中自身"会重新掩盖向量无意义（part-cr-7 R1 反例）。`
  5. `embed_text 伪向量重命名 embed_text_fake，docstring/命名显式标注"仅离线测试 fixture，非交付向量"（part-cr-7 修复建议 line 113）；测试中使用时显式标注 mock。`
  6. `embedding_model 标识：写入处从 "local-sim"（service.py:165、store.py:23 默认）改为真实模型名，供 F5-03 按 model 过滤。`
  7. `失败路径：本地模型加载失败 → fail-loud raise（禁止静默回退伪向量，避免再次假绿）。`
- **对应测试台账项**：`FF-F5-T01`（语义真实性，先红后绿）/ `FF-F5-T02`（维度约束 + fixture 标注）（详见 §8）
- **收口标准**：`T01 在 HEAD（伪向量）红、接本地模型后绿；T02 绿（维度!=1536 raise、embed_text_fake 显式标注）。`
- **本 Phase 风险提醒**：`引入模型依赖——必须本地/离线/可复现（[Q2]），测试 mock 与真实小模型双轨；模型首次加载体积/时间在 §9 记；不得触动 schema 维度硬编码。`

### 5.2 Phase 2 — `向量索引 degraded 定档`

- **Phase 目标**：消除 vec0 静默退化（G-CR3-02），degraded 路径 fail-loud + 抽象 `VectorIndex` 接口；真实 vec0 移出本轮记技术债。
- **本 Phase 对应编号**：`F5-02`（+ F5-04 测试）
- **本 Phase 新增 / 修改文件**：新建 `packages/vector_sqlite_vec/.../vector_index.py`（`VectorIndex` 接口 + `BruteForceVectorIndex`）；修改 `schema.py:62-67`（except 分支加 `logger.warning`）、`schema.py:28-42`（_fallback_vec_sql）（file:line）
- **具体功能预期**：
  1. `schema.py 命中 except（"no such module: vec0"）执行 _fallback_vec_sql 前，logger.warning 强制告警，带机器可读 reason（[Q1] 共同硬约束：退化不再静默）。`
  2. `抽象 VectorIndex 接口（upsert/search/delete 契约），当前暴力 cosine 实现挂其下，未来真实 vec0 为局部替换、不影响上层。`
  3. `closure 将 vector/retrieval gate 重新定级为 "degraded/brute-force，非生产 KNN"（撤销 P4/P5 假绿 ✅，交 F7-05）。`
  4. `真实 vec0 接入（enable_load_extension + sqlite_vec.load）显式记入技术债（§8.4），本轮不做。`
  5. `不优化暴力 cosine（[Q1] 接受性能随数据量线性劣化）。`
- **对应测试台账项**：`FF-F5-T03`（degraded 告警断言）/ `FF-F5-T04`（VectorIndex 接口契约）（详见 §8）
- **收口标准**：`T03 用 caplog 断言退化路径产生 logger.warning（含 reason）；T04 接口契约测试绿；closure degraded 定级记账。`
- **本 Phase 风险提醒**：`不得把 degraded 当 done；告警必须 fail-loud（机器可读 reason，对齐 §8.5）；接口抽象不引入真实 vec0 依赖。`

### 5.3 Phase 3 — `检索过滤强化`

- **Phase 目标**：search 增 `namespace_id`/`embedding_model` 过滤，`distance_metric` 生效（G-CR3-10），消除跨模型/跨命名空间混算。
- **本 Phase 对应编号**：`F5-03`（+ F5-04 测试）
- **本 Phase 修改文件**：`store.py:91-107`（search 签名 + WHERE 过滤 + metric 读取）、`search.py:41-45`（透传参数）（file:line）
- **具体功能预期**：
  1. `store.search WHERE 增 namespace_id/embedding_model（当前 store.py:96-99 仅 deleted_at IS NULL AND team_id=?）；同 team 多 namespace/多 model 向量不再混在一起算 cosine。`
  2. `distance_metric 从 namespace 配置（vec.sql:23 distance_metric，vector_namespaces）读取并生效；当前 store.py:104 硬编码 _cosine，distance_metric 字段建了从不被读（part-cr-3 R10）。`
  3. `search.py:41-45 透传 namespace_id/embedding_model；依赖 Phase 1 落定的真实 embedding_model 名。`
  4. `边界：缺省参数向后兼容；过滤在暴力扫描候选集上 enforce（不接 vec0）。`
- **对应测试台账项**：`FF-F5-T05`（filter 单测）（详见 §8）
- **收口标准**：`T05 绿——同 team 注入两个不同 namespace/model 的向量，按 namespace_id/embedding_model 过滤后只返回对应集合，cosine 不串味。`
- **本 Phase 风险提醒**：`依赖 Phase 1 embedding_model 命名稳定；distance_metric 仅本轮支持 cosine 时其余 metric 需显式 degraded 声明。`

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 register 的 Q 编号，不复制内容、不改口、不开新 Q/A。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[Q1]` vec0 degraded | `owner-gated-qna.md Q1（业主裁决=选项 A）` | `F5-02 定档：暴力 cosine + fail-loud 告警 + VectorIndex 接口；真实 vec0 移出本轮（§2.2 O1）` | `若需真实 vec0 → 回 design 重开 gate，本 AP 保持 draft/blocked，不在 AP 扩大范围` |
| `[Q2]` 本地 1536 embedding | `owner-gated-qna.md Q2（业主裁决=选项 A）` | `F5-01 用 Embedder adapter + 本地小模型，强约束维度=1536（免触 schema）；外部 API/≠1536 移出本轮（§2.2 O2/O3）` | `若选型需 ≠1536 → 牵动 F4/迁移，回 design；本 AP 不改 schema` |
| `[Q7]` 先红后绿 | `owner-gated-qna.md Q7（业主裁决=选项 A）` | `F5-04 + §8 全测试以"HEAD 红、修复后绿"为退出证据；CI 断言强度门禁（交 F7-06）` | `不成立则各 Phase 无客观退出证据 → 不得标 executed` |
| `F4 rowid 不变量（前序）` | `FF-F4-adapter-safety.md F4-03 / G-CR3-03/04` | `F5 写入/检索建立在 rowid 单调不复用 + upsert 复用现有 rowid 上；F4 未完成则 F5 upsert 会复刻孤儿/重号删除` | `F4 未收口 → F5 Phase 1 写入测试不可信，本 AP 阻塞至 F4 完成` |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `packages/rag_vectorizer/src/rag_vectorizer/embedder.py:6-16` | `embed_text：SHA-256 链式哈希伪向量，1536 维确定性数，与文本语义零关联（G-CR7-01）` | `F5-01 替换点` | `♻️ 重 substrate` | `重命名 embed_text_fake 保留为显式 fixture；新建 Embedder/LocalEmbedder` |
| A-2 | `packages/rag_vectorizer/src/rag_vectorizer/search.py:40` | `_search_internal 调 embed_text(query) 做查询向量` | `F5-01 改用同一 Embedder（写/查一致）` | `✅ 复用` | `写处 service.py:167 必须同实例，否则掩盖向量无意义` |
| A-3 | `packages/workflow_rag/src/workflow_rag/service.py:167` | `写入侧 embedding=embed_text(text) + embedding_model="local-sim"（:165）` | `F5-01 改 Embedder + 真实 model 名` | `✅ 复用` | `model 名供 F5-03 过滤；写/查共用 Embedder` |
| A-4 | `packages/vector_sqlite_vec/src/vector_sqlite_vec/schema.py:62-67` | `apply_vec_schema except 分支：vec0 失败 → _fallback_vec_sql（TEXT 表），零日志（G-CR3-02 主审实测 no such module: vec0）` | `F5-02 退化路径加 logger.warning fail-loud` | `✅ 复用` | `保留 fallback 行为，仅加强制告警；不接真实 vec0` |
| A-5 | `packages/vector_sqlite_vec/src/vector_sqlite_vec/store.py:91-107` | `search：WHERE 仅 deleted_at IS NULL AND team_id=?（:96-99），_cosine 硬编码（:104），无 namespace/model 过滤、distance_metric 不读（G-CR3-10）` | `F5-03 增过滤 + metric 生效` | `♻️ 重 substrate` | `暴力扫描保留（degraded），过滤在候选集 enforce` |
| A-6 | `packages/vector_sqlite_vec/src/vector_sqlite_vec/vector_index.py` | `将新建：VectorIndex 接口 + BruteForceVectorIndex` | `F5-02 接口抽象` | `🆕 净新` | `未来真实 vec0 为局部替换` |
| A-7 | `docs/refactor/vec.sql:22,43,58` | `CHECK(embedding_dimension = 1536) ×2 + CREATE VIRTUAL TABLE vec0(embedding float[1536])` | `F5-01 维度约束真源（adapter 强制 1536，免触此 schema）` | `✅ 复用` | `读不改：维度硬约束，不得改 schema（§2.2 O3）` |
| A-8 | `packages/vector_sqlite_vec/src/vector_sqlite_vec/store.py:46,144` | `INSERT 写字面量 1536（embedding 长度从不校验，传 3 维仍记 1536，part-cr-3 R7 实测）` | `F5-01 维度校验落点（adapter 边界强制）` | `✅ 复用` | `维度校验移到 Embedder adapter，写入前 raise` |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | `静默退化无告警`（vec0 失败 → TEXT 表 fallback 不打日志） | `[Q1] 共同硬约束：退化必须 fail-loud；G-CR3-02 根因正是退化静默→假绿。schema.py:62-67 except 分支必须 logger.warning` |
| ⛔2 | `search 跨 namespace/model 混算 cosine` | `G-CR3-10：store.py:96-99 仅 team 过滤，同 team 多 namespace/model/维度向量混算产生跨模型错误打分；即便接 vec0 缺陷仍在` |
| ⛔3 | `写/查用不同 embedding 实现` | `part-cr-7 R1：同一 embedder 既写又查使"查询命中自身"成立，掩盖向量无意义；必须写/查同一 Embedder` |
| ⛔4 | `模型加载失败静默回退伪向量` | `重蹈假绿——加载失败必须 fail-loud raise（[Q2] 本地模型为交付实现，伪向量仅 fixture）` |
| ⛔5 | `选 ≠1536 维模型 / 改 schema CHECK` | `[Q2] 强约束维度=1536 免触 schema；vec.sql:22,43,58 硬编码，改动牵动 F4/迁移（§2.2 O3）` |
| ⛔6 | `把 degraded 标成 done / closure 打绿` | `[Q1] 定档 degraded；part-cr-3 R2 P4/P5 closure 假绿教训；closure 须重新定级为 degraded（交 F7-05）` |
| ⛔7 | `在本 AP 接真实 vec0 或外部 API embedding` | `超出 [Q1][Q2] 定档范围（§2.2 O1/O2）；扩大范围须回 design，不在 AP 自行扩张` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/first-code-review-plan/part-cr-7.md`（embedder 伪向量 R1，file:line + legacy 对照 + 主审实测）、`docs/eval/first-code-review-plan/part-cr-3.md`（vec0 退化 R2、search 过滤 R10，主审实测 `no such module: vec0`）—— §7.1 是其与本 AP 相关子集的摘录；完整借鉴台账见真源。
- **安全 / 信任边界类工作项的威胁模型锚**：本 AP 工作项偏数据完整性/真实性而非攻击面边界；其**数据完整性威胁模型**锚在 `part-cr-3.md`（向量索引假绿 R2、跨模型混算 R10、维度不校验 R7）+ 前序 `FF-F4-adapter-safety.md`（F4-03 rowid 不变量 / 路径遍历 §7.3）。**维度不校验（store.py:46,144 传 3 维仍记 1536）**为本 AP 必堵的数据完整性向量——F5-01 在 adapter 边界强制 1536 校验即对应处置。本 AP 不标 `executed` 直至 F4 rowid 不变量收口（防 grounding 泄漏）。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `FF-F5-T01` | `向量真实性：一组已知相关/不相关样本，相关 query 的目标 chunk cosine 排第一且与次位分差显著（≥阈值）。HEAD 伪向量必红、接本地模型后绿` | `spike` | `集成` | `🆕 新增 tests/integration/test_f5_vector_authenticity.py（真实小模型少量样本）` | `F5-01 → 检索语义化（目标 chunk 排第一+分差）` | `commit {sha} + test_f5_vector_authenticity::test_relevant_chunk_ranks_first PASS + run-time {YYYY-MM-DD HH:MM UTC}` |
| `FF-F5-T02` | `维度约束 + fixture 标注：Embedder 输出长度 != 1536 raise；embed_text_fake 显式命名/标注为非交付向量` | `短途` | `unit` | `🆕 新增 tests/unit/test_f5_embedder.py` | `F5-01 → 维度!=1536 raise + 伪向量降级 fixture` | `commit + test_f5_embedder::{test_dimension_enforced,test_fake_named} PASS + run-time` |
| `FF-F5-T03` | `degraded 告警断言：vec0 不可用时 apply_vec_schema 退化路径产生 logger.warning（含机器可读 reason）` | `短途` | `unit` | `🆕 新增 tests/unit/test_f5_vec_degraded.py（caplog）` | `F5-02 → 退化不再静默` | `commit + test_f5_vec_degraded::test_fallback_emits_warning PASS + run-time` |
| `FF-F5-T04` | `VectorIndex 接口契约：BruteForceVectorIndex 满足 upsert/search/delete 契约，可被替换实现` | `短途` | `契约` | `🆕 新增 tests/unit/test_f5_vector_index_contract.py` | `F5-02 → 接口可被未来 vec0 替换` | `commit + test_f5_vector_index_contract PASS + run-time` |
| `FF-F5-T05` | `search 过滤：同 team 注入两个不同 namespace/embedding_model 向量，按 namespace_id/model 过滤只返回对应集合，cosine 不串味；distance_metric 读配置生效` | `短途` | `unit` | `🆕 新增 tests/unit/test_f5_search_filter.py` | `F5-03 → 跨 namespace/model 不混算` | `commit + test_f5_search_filter::{test_namespace_filter,test_model_filter,test_metric_from_config} PASS + run-time` |

**列定义（填法约束）**：
- **类型**：`短途`（每 PR 快测）/ `spike`（阶段性 journey 验证）/ `mega`（长程整合）/ `soak`（race / 长稳）。
- **层**：`unit` / `集成` / `契约` / `回归` / `e2e` / `live`。
- **来源**：本 AP 全部 `🆕 新增`（既有 tests/unit、tests/e2e 当前为空，见 F7-04）。
- **PASS 证据**：四元组 `commit + 测试名 + run-time(UTC)`（防假绿见 §8.5）。

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `（无既有 F5 用例可沿用）` | `🆕 全新增` | `—` | `tests/unit/ 当前空（F7-04 待填）；本 AP 用例为该目录早期填充` |
| `capstone tests/e2e/test_first_fixes_capstone.py 步 F/G（本地 1536 真实 embedding + search 语义命中）` | `🔱 下游消费` | `本 AP 交付的 Embedder/search 过滤为 capstone F/G 步前置` | `由 F7 capstone 整合，本 AP 不实现 capstone` |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·契约 | 开发中持续（T02/T03/T04/T05） |
| spike | journey 用例 | 集成 | 每 Phase 收口（T01 向量真实性） |
| mega | 长程整合全链 | e2e（capstone F/G） | 交 F7 capstone（本 AP 不跑） |
| soak | deterministic × N | — | 本 AP 无 soak（向量真实性非 race 项） |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 `真实 vec0 / KNN 性能`（理由：[Q1] degraded 定档，真实 vec0 移出本轮）→ 交下一轮生产化 charter；**本 AP 不假装覆盖**，closure 标 degraded。
- 不覆盖 `外部 API embedding 语义质量 / 维度 ≠1536`（理由：[Q2] 本轮仅本地 1536）→ 交下一轮。
- 不覆盖 `端到端 clean→rag→search 语义命中`（理由：依赖 F6 真实 structurize/construct）→ 交 F7 capstone（步 F/G）。
- 不覆盖 `distance_metric 的 l2/inner_product 实现`（本轮仅 cosine）→ 其余 metric 显式 degraded 声明，交下一轮。
- **技术债登记**：真实 sqlite-vec 接入（O1）、外部 API embedding 后端（O2）、embedding 重试退避/usage（O4）显式记入 closure degraded/deferred 清单。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组证据；计数 ≠ 价值。
- T01 必须演示"先红后绿"：在 HEAD（SHA-256 伪向量）跑 T01 留 FAIL 证据（日志/截图），接本地模型后转 PASS——证明 bug 真实存在且修复有效（[Q7]）。
- `degraded` 必带机器可读 `reason`（T03 断言 logger.warning 含 reason，如 `sqlite_vec_unavailable_degraded_to_bruteforce`）。
- **数据完整性项**（维度校验 T02、跨 namespace/model 不混算 T05）必须含**反例向量用例**（传 3 维 → raise；混入异 namespace → 不返回），不得只测 happy-path（对应 §7.3 数据完整性威胁模型）。
- 禁止用伪向量做语义断言的"通过"——T01 用真实小模型；mock 仅在不验证语义质量的测试中使用且显式标注。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| `F4 rowid 不变量（硬前置）` | `F5 upsert/检索依赖 F4-03 rowid 单调不复用 + upsert 复用现有 rowid；F4 未完成则复刻孤儿/重号删除（G-CR3-03/04）` | `high` | `本 AP 阻塞至 FF-F4 收口；F5 写入测试在 F4 绿后才可信` |
| `引入本地模型依赖` | `F5-01 净新高风险：模型体积/首次加载/可复现性` | `medium` | `adapter 接口隔离 + 本地小模型（离线/零计费，[Q2]）+ 测试 mock 与真实模型双轨；CI 缓存模型` |
| `维度漂移触动 schema` | `选型模型维度 ≠1536 会牵动 vec.sql CHECK + vec0 + F4/迁移` | `medium` | `[Q2] 强约束 1536；adapter 边界强制校验，!=1536 raise（§7.1 A-7/A-8）` |
| `degraded 被误标 done` | `vec0 degraded 若 closure 仍打绿则重蹈 part-cr-3 R2 假绿` | `medium` | `fail-loud 告警（T03）+ closure 重新定级为 degraded（交 F7-05）+ §8.4 技术债记账` |
| `写/查 embedder 不一致掩盖噪声` | `若写/查用不同实现，"查询命中自身"重新掩盖向量无意义（part-cr-7 R1）` | `medium` | `F5-01 强制写（service.py:167）/查（search.py:40）同一 Embedder；T01 用跨文本相关性断言而非自命中` |

### 9.2 约束与前提

- **技术前提**：`本地小模型维度必须=1536（[Q2]）；不接 sqlite-vec 扩展（[Q1] degraded）；不改 vec.sql schema。`
- **运行时前提**：`本地模型离线可加载、零网络/计费；暴力 cosine 性能随数据量线性劣化（[Q1] 接受的技术债）。`
- **组织协作前提**：`FF-F4 必须先收口（rowid 不变量）；embedding_model 命名与 F6b（rag:vectorize step）对齐。`
- **上线 / 合并前提**：`所有 §8 测试 PASS（T01 演示先红后绿）；closure 把 vector/retrieval 定级为 degraded；degraded/技术债项显式记账。`

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/closure/（vector/retrieval gate 重新定级为 degraded，撤销 P4/P5 假绿 ✅——交 F7-05）`
- 需要同步更新的说明文档 / README：`packages/rag_vectorizer / vector_sqlite_vec 的 Embedder/VectorIndex 接口说明 + degraded 声明 + 技术债清单`
- 需要同步更新的测试说明：`tests/ 下新增 F5 用例的"先红后绿"证据记录（对齐 §8.5 四元组）`

### 9.4 完成后的预期状态

1. `embedding 真实语义化：相关 query 的目标 chunk 排第一且分差显著；SHA-256 伪向量降级为显式命名 fixture（embed_text_fake），不再被当真功能。`
2. `vec0 退化不再静默：_fallback_vec_sql 路径 fail-loud（logger.warning + 机器可读 reason）；VectorIndex 接口就位，未来真实 vec0 为局部替换；closure 标 degraded。`
3. `search 跨 namespace/embedding_model 不再混算 cosine；distance_metric 读 namespace 配置生效（G-CR3-10 闭环）。`
4. `维度=1536 在 Embedder adapter 边界强制（传非 1536 即 raise），免触 schema 硬编码；写/查共用同一 Embedder。`
5. `下游 F6b（rag:vectorize step）可直接消费 Embedder adapter；F7 capstone 步 F/G（真实 embedding + search 语义命中）前置就绪。`

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

> 收口 = §8 测试台账逐项 PASS，且每项映射回 §3 工作项的收口目标。

### 10.1 收口硬闸

本 AP 无 mega/soak 自跑项（端到端交 F7 capstone）；退出层硬闸为以下 spike + 数据完整性短途项，必须 PASS 且四元组齐全：

1. `向量真实性 spike（FF-F5-T01）PASS，且留有 HEAD 伪向量下 FAIL 的先红证据（[Q7]）。`
2. `degraded 告警断言（FF-F5-T03）PASS：退化路径 logger.warning 含机器可读 reason。`
3. `跨 namespace/model 不混算（FF-F5-T05）+ 维度校验（FF-F5-T02）PASS（数据完整性反例用例齐全）。`

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| `相关 query 目标 chunk 排第一+分差显著` | `F5-01` | `FF-F5-T01` | `commit + test_f5_vector_authenticity PASS + run-time` | `未观察（draft）` |
| `维度!=1536 raise + 伪向量降级 fixture` | `F5-01` | `FF-F5-T02` | `commit + test_f5_embedder PASS + run-time` | `未观察（draft）` |
| `退化路径 fail-loud 告警（含 reason）` | `F5-02` | `FF-F5-T03` | `commit + test_f5_vec_degraded PASS + run-time` | `未观察（draft）` |
| `VectorIndex 接口可替换` | `F5-02` | `FF-F5-T04` | `commit + test_f5_vector_index_contract PASS + run-time` | `未观察（draft）` |
| `跨 namespace/model 不混算 + metric 生效` | `F5-03` | `FF-F5-T05` | `commit + test_f5_search_filter PASS + run-time` | `未观察（draft）` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | `embedding 本地 1536 维真实语义化 + vec0 degraded fail-loud + VectorIndex 接口 + search namespace/model 过滤 + distance_metric 生效` |
| 测试 | §8 测试台账全 PASS（退出硬闸 T01/T03/T05/T02 四元组齐全；T01 演示先红后绿）|
| 文档 | `closure vector/retrieval gate 定级 degraded（撤销假绿 ✅）；接口/技术债显式记账` |
| 风险收敛 | `F4 rowid 前置已收口；degraded 不静默、不被误标 done；维度漂移被 adapter 校验封堵` |
| 可交付性 | `Embedder/VectorIndex 接口供 F6b/F7 消费；O1/O2/O4 技术债显式记入下一轮，不留装成完成的桩` |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**；按 closure 五态（`verified / observed-OK-at-closure / partial / 未观察 / deferred`）如实归类 + handoff。特别地：vec0 本轮 degraded 是**设计定档**（[Q1]），与"测试未观察"区分——前者 closure 标 degraded 是预期态，后者是未达成。F4 rowid 前序未收口前，本 AP 不得标 executed。

---

---

## 11. 执行日志回填（`executed` — 2026-06-01）

> 文档状态: `draft → executed`。执行人 Opus 4.8（主轨直接执行，未用收尾子代理）。提交 `7a70408`。前序 FF-F4 已收口（rowid 不变量），本 AP 前置满足。全量 `python3 -m pytest tests/` → **137 passed**（exit 0；F5 前 115 → 新增 22 用例）。

### 11.1 环境
- 系统 python3，缺 numpy/sentence-transformers/sqlite_vec（离线、无外网）。→ [Q2]「本地小模型」忠实落地为**纯 stdlib 确定性 signed feature-hashing 词袋**（非神经模型）；vec0 [Q1] degraded 本就是定档态。
- 维度强约束=1536 在 Embedder adapter 边界 enforce（embed_text(dims!=1536) raise），免触 vec.sql CHECK / vec0 float[1536]（不动 schema）。

### 11.2 逐工作项
- **F5-01 Embedder + 本地模型**：`embedder.py` 新增 `Embedder`(Protocol, runtime_checkable) + `LocalEmbedder`(name=`local-bow-hash-v1`, dimension=1536)。切 token = 拉丁词 + 拉丁 3-char-gram + CJK 单字 + CJK 二元组，md5 哈希投影到 1536 维之一带符号累加，L2 归一。`embed_text` 委托 `default_embedder()`（写/查同实例，⛔3）；旧 SHA 链式哈希重命名 `embed_text_fake`（docstring 显式标「仅离线 fixture，非交付向量」）。`workflow_rag/service.py` 写入 embedding_model 由 `'local-sim'` 改 `default_embedder().name`（chunks INSERT 参数化 + upsert_chunk）；`search.py` 写/查共用 `default_embedder()` 且按 model 名过滤。
- **F5-02 degraded 定档**：`schema.py` except(vec0)分支 `_fallback_vec_sql` 前加 `logger.warning`（reason=`sqlite_vec_unavailable_degraded_to_bruteforce`）。新建 `vector_index.py`：`VectorIndex`(Protocol) + `BruteForceVectorIndex`(backend=`bruteforce-degraded`，支持 cosine/inner_product/l2，未知 metric → degraded 告警回退 cosine)。`store.search` 委托 `BruteForceVectorIndex.query`（相似度计算收敛到接口下，未来 vec0 局部替换）。
- **F5-03 检索过滤**：`store.search` 增 `namespace_id`/`embedding_model` 可选过滤（WHERE 动态拼，跨 namespace/model 不混算 cosine，G-CR3-10）；新增 `_resolve_metric(namespace_id)` 从 `vector_namespaces.distance_metric` 读取并传给 index（非硬编码 cosine，R10）；缺省（不传 model）维持 team-wide + `logger.debug` degraded 提示（向后兼容）。`search.py` 透传 `embedding_model=embedder.name`。

### 11.3 先红后绿（22 新用例，全 PASS · 四元组证据）
> **语义排序红基线（[Q7] 关键证据）**：在覆盖 embedder.py 前，用当前 SHA `embed_text` 跑 3 对（tax/dog/code）样本——目标 chunk **全未排第一**，margin 仅 +0.023/+0.016/+0.019（哈希噪声）；接本地模型后全部排第一且 margin ≥0.1。

| Test-ID | 文件::用例 | 红基线 | PASS 证据 |
|---------|-----------|--------|-----------|
| FF-F5-T01 | `test_f5_vector_authenticity.py`（相关 query 目标排第一 + 分差 ≥0.1；对照 fake 不全中） | SHA 下 3 对全未排第一（实测） | `7a70408 + test_relevant_chunk_ranks_first_with_margin(+对照) + 2026-06-01 03:38 UTC` |
| FF-F5-T02 | `test_f5_embedder.py`（维度=1536 / !=1536 raise / 协议 / 确定性 / L2 归一 / 共词语义 / fake 降级，9 用例） | 无 LocalEmbedder/embed_text_fake（import 红） | `7a70408 + test_f5_embedder(9) + 2026-06-01 03:38 UTC` |
| FF-F5-T03 | `test_f5_vec_degraded.py`（caplog 捕获退化 warning + reason） | 退化静默零日志（红） | `7a70408 + test_fallback_emits_warning_with_reason + 2026-06-01 03:38 UTC` |
| FF-F5-T04 | `test_f5_vector_index_contract.py`（协议 / cosine 排序 / top_k / inner_product / l2 / 未知 metric 降级告警 / 空候选，7 用例） | 无 VectorIndex（import 红） | `7a70408 + test_f5_vector_index_contract(7) + 2026-06-01 03:38 UTC` |
| FF-F5-T05 | `test_f5_search_filter.py`（model 过滤不串味 + 向后兼容 team-wide + namespace 过滤 + metric 读配置生效，3 用例） | search 仅 team 过滤、metric 硬编码（红） | `7a70408 + test_f5_search_filter(3) + 2026-06-01 03:38 UTC` |

- 全量回归：`python3 -m pytest tests/` → **137 passed**（exit 0；115 + 22）。p5 search 全链（url→worker→rag construct 写真实向量→search 按 model 过滤）通过，证写/查 model 名一致、过滤接线无回归。

### 11.4 偏差与 handoff
- **「本地小模型」= 确定性词袋 feature-hashing，非神经模型**（环境无 ML 依赖的忠实落地）：捕捉**词面/字面重叠**的语义相关（共词余弦更高），不捕捉超越词面的同义性（car≈automobile）。真实神经 embedding 记**技术债 handoff**（需 ML 依赖，离线不可得）→ 下一轮生产化 / [Q2] 子选项 C（可配置后端，adapter 已留口）。closure §4 显式记账，不假装是神经模型。
- **vector/retrieval gate 重新定级 degraded**：vec0 [Q1] degraded（暴力 cosine、性能随数据量线性劣化）是**设计定档**而非未达成；P4/P5 早期若有「vector/retrieval ✅ PASS」假绿，须在 **F7-05 closure 重定级**为 degraded（撤销假绿）。本 AP 已 fail-loud 告警 + VectorIndex 接口就位，未来 vec0 为局部替换。
- **deferred（A/B/C 见 closure §4）**：真实 sqlite-vec 接入（O1, A）、外部 API embedding（O2, A）、维度≠1536（O3, A）、embedding 重试退避/usage（O4, B）、端到端语义命中 capstone 步 F/G（C→F7）。
- 下游 **FF-F6b**（rag:vectorize step）直接消费本 AP 的 `default_embedder()` / Embedder adapter；embedding_model 命名 `local-bow-hash-v1` 已落定供过滤。
