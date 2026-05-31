# First Code Review — 总体规划 (Plan Index)

> 类型: `代码审查规划 / Review Charter`
> 范围: `smind-family Python monorepo 全量`
> 状态: `completed — CR-1~CR-8 八簇全部完成（part-cr-1~8.md），无簇可收口，全程序约 28 个 blocker；收口总账见 part-cr-8.md 附录与本文末"全审查收口声明"`
> 日期: `2026-05-31` · 作者: `Claude (Opus 4.8)`
> 校准基准: `legacy-family/`（原始 Cloudflare Worker TS 实现，只读参照）
> 关联设计: `docs/refactor/index.md`
> 关联评估: `docs/eval/smind-family-strucure-analysis-by-GPT.md`

---

## 0. 一句话定位

> 本文不是审查报告，而是**审查前的作战地图**：先确定 Python monorepo 的真实结构与依赖分层，再把代码切成可独立审查的**业务簇 (review cluster)**，定义每个簇的审查维度、legacy 校准映射与审查顺序。后续每个簇产出一份独立审查报告。

---

## 1. 审查目标与判定口径

owner 要求排查三类问题。先把口径定死，避免各簇审查标准漂移：

| 代号 | 名称 | 定义 | 典型形态 |
|------|------|------|----------|
| **B（盲点 / Blind spot）** | 应有未有 | 设计/SSOT/legacy 中存在的能力，当前 Python 实现缺失、被桩代替或被静默简化 | stub 函数、`return None`、`pass`、TODO、硬编码单一分支、schema 有表但无代码读写 |
| **D（断点 / Breakpoint）** | 链路断裂 | 数据流 / 状态机 / 调用链在某处中断，导致流程无法贯通 | step 创建后无人 claim、stage 命名不匹配、artifact 写了无人读、回调/finalizer 缺失、迁移未挂载 |
| **L（逻辑错误 / Logic error）** | 行为错误 | 代码能跑通但语义错误，与设计意图或 legacy 行为不一致 | 事务边界错误、claim/lease 竞态、retry/purge 语义偏差、SQL 条件写反、状态流转非法、错误吞掉 |

**附加横切维度**（每簇都要顺带检查，不单列簇）：

- **C1 事务与并发**：长任务是否在持锁事务内执行；`BEGIN IMMEDIATE` 边界；claim/lease 竞态。
- **C2 错误处理**：异常是否被静默吞掉（`except: pass`、宽 `except Exception`）；失败是否落 `step_attempts`。
- **C3 一致性**：`core.db` 与 `vec.db` 跨库操作是否依赖工作流状态机而非跨库事务（设计硬约束）。
- **C4 可观测性**：每个 step 是否落 `workflow_events` / `audit_logs`（设计硬约束："所有 workflow step 必须可观测"）。
- **C5 适配层纪律**：业务模块是否绕过 `ObjectStore` / `VectorStore` 直接碰文件或 sqlite-vec 方言（设计硬约束）。

---

## 2. Monorepo 真实结构（已勘探确认）

### 2.1 规模快照

| 维度 | 数值 |
|------|------|
| Python 文件数 | 78（apps + packages，含 `__init__`） |
| Python 运行时代码 | ≈ 3,492 行 |
| 测试文件 | 15 |
| packages 包数 | 19 |
| apps 入口 | 3（api / worker / cli） |
| legacy 参照 TS | ≈ 31,700 行（8 个 worker） |

> **关键观察：实现量约为 legacy 的 1/9。** 这意味着当前 Python 库**大概率是骨架 + 部分核心**，业务执行器多为桩实现。审查的首要任务不是"找少量 bug"，而是**系统性标定"哪些是真实现、哪些是占位"**，并判断断点位置。

### 2.2 包清单与代码量（按层归类）

```
Layer 0 — 基础契约 (foundation)
  common              5 files   33  smind_common: errors/ids/logging/time
  config              3 files   24  smind_config: loader/settings
  contracts           2 files   20  smind_contracts: workflow dataclasses（仅 2 个，疑似过薄）

Layer 1 — 基础设施 (infra / adapters)
  storage_sqlite     10 files  294  engine + migrations/runner + repositories(artifacts/chunks/requests/steps/workflow)
  storage_objects     2 files   24  FileSystemObjectStore
  vector_sqlite_vec   4 files  258  engine + schema + store

Layer 2 — 工作流内核 (kernel)
  workflow_core      11 files  849  scheduler/claim/leases/retry/restart/purge/graph/events/health/_utils

Layer 3 — 领域服务 (domain services)
  auth                2 files  116
  team                2 files   58
  ingestion           2 files  221
  management          2 files  164
  cleaners_universal  2 files   13  ← 疑似 stub
  providers_dedicated 2 files   13  ← 疑似 stub（硬编码 chinatax 单分支）
  browser_runtime     2 files   17  ← 疑似 stub
  rag_structurizer    2 files   13  ← 疑似 stub（朴素 \n 分段）
  rag_constructor     2 files   26  ← 疑似 stub
  rag_vectorizer      3 files  159  embedder/search

Layer 4 — 工作流编排 (orchestration)
  workflow_clean      2 files  133  process_clean_step
  workflow_rag        2 files  237  process_rag_step

Layer 5 — 应用入口 (apps)
  api                12 files  683  FastAPI: routes(auth/team/me/ingestion/management/search/ops/workflow_config) + deps
  worker              2 files   82  轮询调度心脏
  cli                 2 files   55
```

### 2.3 依赖图（已用 import 扫描确认，自底向上）

```
common / config / contracts        ← 无内部依赖（叶子）

storage_sqlite                     ← 无内部依赖
storage_objects                    ← 无内部依赖
vector_sqlite_vec                  ← 无内部依赖
browser_runtime                    ← 无内部依赖
auth / team                        ← 无内部依赖（conn 由调用方注入）

cleaners_universal   → browser_runtime
ingestion            → storage_objects
rag_vectorizer       → storage_objects, vector_sqlite_vec
workflow_core        → storage_sqlite, vector_sqlite_vec
management            → workflow_core, rag_vectorizer, storage_objects
workflow_clean       → cleaners_universal, providers_dedicated, storage_objects
workflow_rag         → rag_constructor, rag_structurizer, rag_vectorizer, storage_objects, vector_sqlite_vec

apps/api    → auth, team, ingestion, management, storage_sqlite, storage_objects, vector_sqlite_vec, common, config
apps/worker → workflow_core, workflow_clean, workflow_rag, storage_sqlite, storage_objects, vector_sqlite_vec, common, config
apps/cli    → management, storage_sqlite, storage_objects, vector_sqlite_vec, config
```

**结论：依赖呈干净的有向无环分层**，没有发现循环依赖。这使得"自底向上"的审查顺序天然成立 —— 先审被依赖最多的底座，再审依赖它们的上层。

### 2.4 数据库 SSOT（schema 是真实的"应有"基线）

- `docs/refactor/core.sql`：**23 张表 + 11 个视图**（身份、ingestion、工作流内核、配置、运维四大域）。
- `docs/refactor/vec.sql`：`vector_namespaces` / `vector_records` + `chunk_embedding_index`(vec0 虚拟表) + 3 视图。
- 运行时由 `storage_sqlite/migrations/runner.py` 通过**向上搜索 `docs/refactor/core.sql` 路径**加载（注意：运行时耦合 docs 目录，列为待查断点 D）。

> Schema 是"应有能力"的权威清单。审查每个簇时，对照"schema 里有的表/视图，是否有代码真正读写"——**有表无代码 = 盲点 B**。

---

## 3. 审查业务簇划分（Review Clusters）

按"依赖层 + 业务内聚 + 可独立指派"三原则，切成 **8 个簇**。每个簇是一份独立审查报告的范围。

---

### CR-1 · 基础底座与契约 (Foundation & Contracts)

| 项 | 内容 |
|----|------|
| 包 | `common`, `config`, `contracts` |
| 关注 | ID 生成、时间戳格式（ISO/UTC 一致性）、日志、错误类型体系、配置加载与默认值、契约 dataclass 完整性 |
| legacy 校准 | `legacy-family/*/core/{log,errors}.ts`、`core/schemas_common.ts`、`core/schemas_smcp.ts` |
| 已知风险 | `contracts` 仅 2 个 dataclass，远薄于 schema 隐含的契约面（**疑 B**）；`time.py` 的时间格式必须与 SQL `strftime('%Y-%m-%dT%H:%M:%fZ')` 完全一致，否则视图 `available_at` 比较出错（**疑 L**） |
| 优先级 | 高（被所有层依赖，错误放大面最大） |

---

### CR-2 · 关系存储与迁移 (core.db Storage Layer)

| 项 | 内容 |
|----|------|
| 包 | `storage_sqlite`（engine / migrations/runner / repositories ×5） |
| 关注 | PRAGMA 设置（WAL/synchronous/foreign_keys/busy_timeout）；迁移幂等性与挂载；repositories 的 SQL 正确性；与 `core.sql` 23 表是否对齐 |
| legacy 校准 | `legacy-family/*/core/db.ts`（D1 访问层） |
| 已知风险 | 迁移靠**运行时搜索 `docs/refactor/core.sql`**——若打包/部署时 docs 不在路径则 schema 不建（**疑 D**）；只有 5 个 repository 文件，23 张表是否都有访问路径待核（**疑 B**） |
| 优先级 | 高 |

---

### CR-3 · 对象存储与向量层 (storage_objects + vec.db)

| 项 | 内容 |
|----|------|
| 包 | `storage_objects`, `vector_sqlite_vec` |
| 关注 | `FileSystemObjectStore` 的路径安全/原子写；`VectorStore` 的 upsert/delete/search；`vec0` 虚拟表 rowid 与 `vector_records.embedding_rowid` 的一一对应；distance metric 与维度一致性 |
| legacy 校准 | `legacy-family/smind-admin/core/r2.ts`；`legacy-family/smind-skill-rag-vectorizer/src/vectorizer_do.ts`、`vectorizer/engine.ts` |
| 已知风险 | C3 跨库一致性的物理落点全在此；rowid 映射错位会导致检索召回错乱（**疑 L**） |
| 优先级 | 高 |

---

### CR-4 · 工作流内核 (Workflow Kernel) — **最高优先**

| 项 | 内容 |
|----|------|
| 包 | `workflow_core`（scheduler / claim / leases / retry / restart / purge / graph / events / health） |
| 关注 | claim 事务（`BEGIN IMMEDIATE`）与 `v_ready_steps` 视图语义；lease 过期回收（`v_stale_claims`）；retry 退避与 `max_attempts`；restart/purge 请求消费；事件/审计落库（C4） |
| legacy 校准 | `smind-clean-dispatcher/flows/{processor,orchestrator,finalizer,restarter}.ts`；`smind-rag-dispatcher` 同名；`smind-skill-rag-vectorizer/src/purger_logic.ts` |
| 已知风险 | 这是全系统状态中心，B/D/L 影响面最大；`claim.py` 已读，需核对 lease 续约、心跳超时、attempt 计数与 `step_attempts` 落库链路是否完整 |
| 优先级 | **最高（先于一切业务簇）** |

---

### CR-5 · 控制面 (Control Plane)

| 项 | 内容 |
|----|------|
| 包 | `auth`, `team`, `ingestion`, `management` + `apps/api`（含 deps 注入、routes） |
| 关注 | 鉴权/API key 校验；team 权限边界；file/url/api 三类 ingestion 是否都建出正确的 source/document/workflow_run/step；management 查询与 restart/purge 入口；conn 注入是否到位（auth/team 不直接 import storage_sqlite） |
| legacy 校准 | `smind-admin/services/{auth,user,team,password,workflow}.ts`；`smind-admin/ingestion/{files,urls,apis}.ts`；`smind-admin/management/{list,static,apis_registry}.ts` |
| 已知风险 | ingestion 是否真正投递出可被 worker claim 的 step（**疑 D**，与 CR-8 联动）；三类源是否都实现还是只实现 file（**疑 B**） |
| 优先级 | 中高 |

---

### CR-6 · Clean 流水线 (Clean Pipeline)

| 项 | 内容 |
|----|------|
| 包 | `workflow_clean`, `cleaners_universal`, `providers_dedicated`, `browser_runtime` |
| 关注 | clean planner 选择执行器的 action registry；universal vs dedicated 路由；产物落 ObjectStore + artifact 元数据；finalizer 是否创建下游 rag step |
| legacy 校准 | `smind-clean-dispatcher/flows/*`、`services/{mapper,differ,io_renderer}.ts`；`smind-skill-clean-universal`（htmlCrawl/browserFetch/browserPDF/geminiClean 等 action）；`smind-skill-clean-dedicated-apis`（provider action registry） |
| 已知风险 | `cleaners_universal`(13行)、`providers_dedicated`(13行硬编码 chinatax 单分支)、`browser_runtime`(17行) **几乎确定是 stub**（**B 高危**）；legacy 此处有 ~10k 行能力，需逐 action 列差异矩阵 |
| 优先级 | 中 |

---

### CR-7 · RAG 流水线 (RAG Pipeline)

| 项 | 内容 |
|----|------|
| 包 | `workflow_rag`, `rag_structurizer`, `rag_constructor`, `rag_vectorizer` |
| 关注 | structurize → construct(chunk/summary/layer-json) → vectorize 三段；chunk 落 `chunks` 表与 `vec_status` 流转；embedding 写 vec.db 后回写 core.db `vectorized`（C3 五步序）；finalizer 收尾 |
| legacy 校准 | `smind-rag-dispatcher/flows/*`；`smind-skill-rag-structurizer`、`smind-skill-rag-constructor`（flows/constructor.ts、services/recorder.ts）、`smind-skill-rag-vectorizer`（callbacker/igniter/vectorizer_do/purger_logic） |
| 已知风险 | `rag_structurizer`(13行朴素分段)、`rag_constructor`(26行) **疑 stub**（**B 高危**）；vectorizer 是 legacy 平台耦合最高模块，本地化语义偏差风险最大（**L**） |
| 优先级 | 中 |

---

### CR-8 · 运行入口与端到端贯通 (Apps Wiring & E2E)

| 项 | 内容 |
|----|------|
| 包 | `apps/worker`（调度心脏）、`apps/cli`、`apps/api` 装配、search 路径、跨簇贯通 |
| 关注 | worker 主循环 stage 派发；restart/purge 消费顺序；search 端到端（embed→vec.db→core.db hydrate via `v_search_hydration`）；CLI 命令面 |
| legacy 校准 | 各 worker `src/index.ts` 入口路由；`smind-rag-dispatcher` 检索/hydration 路径 |
| 已知风险 | **已肉眼发现疑似 D/L**：`apps/worker/main.py` 派发用 `step["stage"].startswith("clean")`（无冒号）但 `startswith("rag:")`（有冒号），stage 命名约定不一致——需核对 step 创建侧的 stage 字符串，否则 clean 或 rag step 可能永远不被路由 |
| 优先级 | 中（依赖前序簇结论，但贯通性问题需尽早暴露） |

---

## 4. 推荐审查顺序

依赖图决定顺序：**先底座，后上层；先内核，后业务；最后端到端贯通。**

```
阶段一 · 地基（必须先做，错误放大面最大）
  CR-1 基础契约  →  CR-2 关系存储  →  CR-3 对象/向量层

阶段二 · 内核（全系统状态中心）
  CR-4 工作流内核   ← 最高优先，单独成批

阶段三 · 业务（可并行指派给不同审查方）
  CR-5 控制面  ‖  CR-6 Clean 流水线  ‖  CR-7 RAG 流水线

阶段四 · 贯通（综合前序结论）
  CR-8 入口与端到端
```

理由：
1. **底座先行** —— CR-1/2/3 被所有上层依赖，若时间格式、迁移、向量映射有错，会污染所有上层审查结论。
2. **内核单批** —— CR-4 是状态机核心，clean/rag 业务簇的正确性都以"内核语义正确"为前提，必须在业务簇之前定稿。
3. **业务可并行** —— CR-5/6/7 之间无强依赖（控制面建 step、clean/rag 各自消费），可分配给不同审查方同时进行。
4. **贯通收尾** —— CR-8 需要引用前序所有簇的结论来判断端到端是否真的跑通，故放最后。

---

## 5. legacy 校准方法论（owner 明确要求）

当 Python 侧"无法判断某行为是否正确 / 是否缺失"时，回到 `legacy-family/` 对应 TS 实现取证。三步法：

1. **定位**：用 §3 各簇的"legacy 校准"映射找到对应 TS 文件（legacy 源码结构良好：`core/` `services/` `flows/` `ingestion/` `management/`，非纯 bundle）。
2. **取证**：以 legacy 行为为"应有语义"基线，逐条比对 Python 实现。区分两类差异：
   - **有意收敛**（设计已声明，如 queue→DB claim、DO→lease）：不算缺陷，但需确认语义等价。
   - **无意丢失**（legacy 有、设计未声明要删、Python 也没有）：记为盲点 B。
3. **裁决**：每条差异标注 `等价 / 有意简化 / 盲点B / 断点D / 逻辑错误L`，并附 legacy 文件:行号 与 Python 文件:行号双向引用。

> 注意：legacy 是**只读冻结参照**（`.gitignore` 已忽略、P7 freeze guard 强制），审查中只读不改。

---

## 6. 每簇审查报告产出约定

每个 CR 簇产出一份报告，建议路径 `docs/eval/first-code-review-plan/CR-<n>-<slug>.md`，统一含：

1. **范围与文件清单**（实际审了哪些文件 + 行数）。
2. **发现表**：`ID | 类型(B/D/L) | 严重度(blocker/high/med/low) | 位置(file:line) | legacy对照 | 描述 | 建议`。
3. **横切检查结论**（C1–C5 逐项 pass/fail + 证据）。
4. **stub/真实现标定表**：本簇每个公开函数标 `真实现 / 部分 / stub / 缺失`。
5. **诚实声明**：未覆盖项、不确定项、需 owner 决策项。

汇总层在本 `index.md` 末尾维护一张**全局发现登记表**（跨簇去重后）。

---

## 7. owner 已确认指令（2026-05-31 定稿）

以下 4 项已由 owner 拍板，作为各簇审查的强制口径：

1. **审查粒度 — stub 标定即发现。** "应有却只是桩/未实现"明确登记为**盲点 B**，与已写代码内部的 D/L 同等对待。各簇 §4 的 stub/真实现标定表为**必交项**。
2. **legacy parity 深度 — 逐 action 完整 parity。** CR-6（clean 每个 action）与 CR-7（rag 每个 provider / 每个执行阶段）必须做**完整 parity matrix**，逐条比对 legacy 行为，不接受粗粒度"是否 stub"了事。每条差异标注 `等价/有意简化/盲点B/断点D/逻辑错误L` + 双向 file:line 引用。
3. **并行分派 — 阶段三分派给不同审查方。** CR-5 / CR-6 / CR-7 同时发起、各出独立报告。三簇间共享依赖（如 contracts、storage、workflow_core 的语义）以本文 §2 依赖图 + CR-1~CR-4 结论为准，避免重复审查底座。
4. **测试纳入 — 查"假绿"。** 现有 15 个测试文件纳入 **CR-8**：核查测试是否真正覆盖业务路径、有无 mock 过度/断言空洞导致的"假绿"（P7 closure 声称 `14 passed`，需验证这 14 条到底验了什么）。

### 7.1 对各簇范围的连带调整

- **CR-6 / CR-7** 工作量上调：需逐 action/provider 拉出 legacy 清单（clean: htmlCrawl / browserFetch / browserPDF / geminiClean / geminiUnderstanding + dedicated provider 动作族；rag: structurizer / constructor / vectorizer 各自的 action 与 purge/restart 分支），与 Python 侧逐项对照成矩阵。
- **CR-8** 范围扩入 `tests/`（unit / integration / smoke / p7_cutover），交付"测试有效性结论"小节。

---

## 附录 A · 启动阶段已肉眼捕获的候选问题（未验证，供各簇take）

> 以下为本次结构勘探中顺手发现的疑点，**尚未验证**，交由对应簇正式核实，避免遗漏。

| # | 类型 | 位置 | 描述 | 移交簇 |
|---|------|------|------|--------|
| A1 | ~~D/L~~ **证伪** | `apps/worker/main.py` 派发分支 | **CR-5/CR-6 实测证伪**：实际 step 写 `stage='clean'`↔`startswith("clean")`、`'rag:structurize'`↔`startswith("rag:")` 均匹配，step 可正常路由；命名不一致仅低危脆弱性，非断点 | 已关闭（非 bug） |
| A2 | D | `storage_sqlite/migrations/runner.py` | 迁移运行时向上搜索 `docs/refactor/core.sql`，部署若不含 docs/ 则 schema 不建立 | CR-2 |
| A3 | B | `contracts`(20行) | 仅 2 个 dataclass，远薄于 schema 23 表隐含的契约面 | CR-1 |
| A4 | B | `cleaners_universal`(13)/`providers_dedicated`(13)/`browser_runtime`(17) | 几乎确定是 stub；providers 硬编码 `chinatax.gov.cn` 单分支 | CR-6 |
| A5 | B | `rag_structurizer`(13)/`rag_constructor`(26) | 朴素 `\n` 分段；legacy 对应 ~6.8k 行，疑大量能力缺失 | CR-7 |
| A6 | L | `smind_common/time.py` ↔ `core.sql` | 时间戳格式须与 `strftime('%Y-%m-%dT%H:%M:%fZ')` 严格一致，否则 `v_ready_steps.available_at` 比较错误 | CR-1 / CR-4 |
| A7 | B | `storage_sqlite/repositories/`(5文件) | 5 个 repository 覆盖 23 张表，多数表可能无访问路径 | CR-2 |

---

## 附录 B · 全局发现登记表（各簇完成后回填，跨簇去重）

| 全局ID | 来源簇 | 类型 | 严重度 | 位置 | 一句话 | 状态 |
|--------|--------|------|--------|------|--------|------|
| G-CR1-01 | CR-1 (R1) | L/correctness | **critical** | `workflow_core/_utils.py:6,10` | `now_iso` 格式串缺 `%S` 丢秒(`07:31:863796Z`)。**CR-4 已精确纠偏**:真正落点是 `lease_expires_at` 比较(reap/v_stale_claims,见 G-CR4-02)+ restart 的 available_at(G-CR4-04);**fresh/retry step 的 v_ready_steps 不受影响**(走 SQL strftime),CR-1 原"fresh step 永不就绪"断言撤回 | open · blocker |
| G-CR1-02 | CR-1 (R2) | L/correctness | high | `common/time.py:5` | `utc_now_iso()` 用 isoformat 输出微秒+`+00:00`,不符 SSOT `...SS.mmmZ` | open · blocker |
| G-CR1-03 | CR-1 (R3) | D/correctness | high | `common/time.py` ↔ `_utils.py` | 时间/ID 双重实现且格式分裂,无单一 SSOT | open · blocker |
| G-CR1-04 | CR-1 (R4) | B/scope-drift | medium | `contracts/workflow.py` | 仅 2 个无校验 dataclass 且全仓 0 import(死代码),远薄于 legacy 40+ schema | open · 待owner决策 |
| G-CR1-05 | CR-1 (R5) | B/scope-drift | medium | `common/errors.py` | `SmindError` 空壳、0 使用,远薄于 legacy 25+ 错误码+HTTP 映射 | open · followup |
| G-CR1-06 | CR-1 (R6) | B/platform-fitness | low | `common/logging.py` | `get_logger` 无结构化/级别阈值/审计落库 | open · followup |
| G-CR1-07 | CR-1 (R7) | correctness | low | `config/settings.py:6-9` | `Settings` 相对路径默认值致 cwd 依赖脆弱 | open · followup |
| G-CR1-08 | CR-1 (R8) | test-gap | medium | `tests/smoke` | 唯一覆盖 CR-1 的断言仅 `"T" in utc_now_iso()`,假绿 | open · 移交CR-8 |

| G-CR2-01 | CR-2 (R1) | L/correctness | high | `apps/api/.../deps.py:33-42` | `get_core_conn`/`get_vec_conn` 用 `return` 非 `yield`,每请求连接永不关闭(泄漏) | open · blocker |
| G-CR2-02 | CR-2 (R2) | D/correctness | high | `storage_sqlite/engine.py:13` | engine 未设 `isolation_level=None`,默认隐式事务与内核 `BEGIN IMMEDIATE` 可复现冲突,靠 commit 约定续命 | open · blocker |
| G-CR2-03 | CR-2 (R3) | B+D/scope-drift | high | `core.sql` api_keys/workflow_step_links/prompt_versions/provider_configs | 4 表全代码库零访问(真盲点);api_keys 相对 legacy 是认证断点 | open · blocker · 部分移交CR-5 |
| G-CR2-04 | CR-2 (R5) | B/scope-drift | medium | `storage_sqlite/repositories/` | repository 仅覆盖 6/23 表,13 表裸 SQL 绕过抽象 | open · 待owner决策 |
| G-CR2-05 | CR-2 (R6) | C1/correctness | medium | `storage_sqlite/repositories/*` | 各方法独立 commit,无跨方法事务,多写非原子(弱于 legacy db.batch) | open · followup |
| G-CR2-06 | CR-2 (R7) | D/delivery-gap | medium | `migrations/runner.py:30` | 迁移单条一次性建表,无版本化演进路径 | open · followup |
| G-CR2-07 | CR-2 (R8) | D/correctness | low | `engine.py:13` | 单连接单线程;check_same_thread 默认 True 是并发化隐藏断点 | open · 潜伏 |
| G-CR2-08 | CR-2 (R9) | D/correctness | low | `runner.py:8-14` | core.sql docs/包内双副本漂移风险(当前一致) | open · followup |

> CR-1 verdict: **changes-requested**,不收口,3 blocker(G-CR1-01/02/03)。报告全文见 `part-cr-1.md`。
> 注:G-CR1-01 物理落点在 CR-4 的 `_utils.py`,根因是 CR-1 未确立时间格式单一 SSOT,故 CR-1/CR-4 联合 own;CR-4 审查时需复核该修复。
>
> CR-2 verdict: **changes-requested**,不收口,3 个本簇 blocker(G-CR2-01/02/03)+ 联动 G-CR1-01。报告全文见 `part-cr-2.md`。
> 关键澄清:① 附录 A 的 **A2(迁移路径搜索断点)经实测证伪** —— 包内 core.sql 存在且打包,非断点;② **G-CR1-01 时间 bug 不经 CR-2 污染** —— core.sql 的 DB 侧格式正确、6 个 repo 全走 DDL DEFAULT;③ A7(覆盖缺口)确认:真覆盖 6 / 绕过抽象 13 / 真盲点 4。
> 正面事实:core.sql 实测干净建库(23 表+11 视图,FK/integrity/幂等全通过),6 repo SQL 全绿,PRAGMA 全对齐。

| G-CR3-01 | CR-3 (R1) | B+L/**security** | **critical** | `storage_objects/filesystem_store.py:11-20` | object_key 零校验,`../`/绝对路径双逃逸,经未校验 HTTP filename 可达 → 任意文件读写 + 跨 team 越权 | open · blocker · 主审实测 |
| G-CR3-02 | CR-3 (R2) | B+D/platform-fitness | **critical** | `vector_sqlite_vec/{engine,schema,store}.py` | sqlite-vec/vec0 从不加载,向量索引静默退化为 TEXT 表 + 暴力 cosine;P4/P5 closure 假绿 | open · blocker · 主审实测 |
| G-CR3-03 | CR-3 (R3) | L/correctness | **critical** | `store.py:32,126-130` | 重复 upsert 致孤儿 rowid 累积,违反一一对应不变量 | open · blocker · 主审实测 |
| G-CR3-04 | CR-3 (R4) | L/correctness | **critical** | `store.py:128,41-67` | 软删后新增 rowid 重号 + `INSERT OR REPLACE` 静默删除软删审计记录 | open · blocker · 主审实测 |
| G-CR3-05 | CR-3 (R5) | B+D/delivery-gap | high | `filesystem_store`/`workflow_core/purge.py` | 对象存储无 delete,purge 不清对象 → purged 内容永久残留(合规) | open · blocker |
| G-CR3-06 | CR-3 (R6) | C1/correctness | high | `filesystem_store.py:14` | put_text 非原子写 + 读回不校验 hash/size → 静默损坏 | open · followup |
| G-CR3-07 | CR-3 (R7) | L/correctness | high | `store.py:46,144,154` | embedding_dimension 硬编码 1536 + _cosine 维度静默截断 | open · followup |
| G-CR3-08 | CR-3 (R8) | B/scope-drift | high | `filesystem_store.py` | 对象存储仅 text 无二进制(PDF 无法存);当前被 API str 掩盖 | open · followup |
| G-CR3-09 | CR-3 (R9) | L/correctness | high | `store.py:76-88` | delete_chunk 软删 vr 但硬删 index,软硬删不一致(喂养 R3/R4) | open · followup |
| G-CR3-10 | CR-3 (R10) | B/correctness | high | `store.py:91-100` | search 仅按 team_id 过滤,无 namespace/model → 跨模型错误打分 | open · followup |
| G-CR3-11 | CR-3 (R11) | C2/correctness | medium | `filesystem_store.py:16` / `search.py:125` | get_text 裸 FileNotFoundError 无人捕获 + search TOCTOU | open · followup |
| G-CR3-12 | CR-3 (R12) | C3+D/correctness | medium | `workflow_core/purge.py:31` | ~~purge 崩溃 request 卡 'processing' 不被重捞~~ **CR-4 实测证伪**:批末单 commit,崩溃整批回滚 → request 退回 pending 可重捞;改记为 G-CR4-12 批量单事务问题 | **superseded by G-CR4-12** |
| G-CR3-13 | CR-3 (R13) | C3/correctness | medium | `workflow_rag/service.py:167-233` | vectorize 崩溃留 vec 孤儿向量无补偿;replay 放大 R3(读路径 post-filter 安全) | open · followup |
| G-CR3-14 | CR-3 (R14) | D/delivery-gap | medium | `vec.sql:22,43,58` | 维度三处硬编码 + 无维度迁移路径(同 CR-2 迁移缺口) | open · followup |

> CR-3 verdict: **changes-requested**(实质接近 blocked),不收口,4 个 critical blocker(G-CR3-01/02/03/04)+ 1 合规 blocker(05)。报告全文见 `part-cr-3.md`。
> 关键澄清:① 4 个 critical 全部经主审独立实测复现(路径遍历/vec0 退化/孤儿 rowid/重号删除);② **G-CR1-01 时间 bug 不经 CR-3 污染**(store 用内联 strftime 正确);③ C3 架构方向正确、读路径 post-filter 安全不脏读;④ **closure 假绿**:P4/P5 以 ✅ PASS 宣称 vector/retrieval 完成,实为暴力实现,移交 CR-8 测试有效性核查。
> 正面事实:vec.db 关系层 schema 实测干净建库(4 表/6 索引/3 视图,5 项 CHECK 逐条生效,幂等)。

| G-CR4-01 | CR-4 (R1) | D/correctness | **critical** | `workflow_core/leases.py:27` / `worker/main.py` | `reap_expired_claims` 死代码(无运行时调用),lease 故障回收不执行,崩溃 worker 的 step 因唯一索引永久卡 running | open · blocker · 主审实测 |
| G-CR4-02 | CR-4 (R2) | L/correctness | **critical** | `workflow_core/_utils.py:6,10` | now_iso/add_seconds_iso 缺 %S → lease_expires_at 畸形,reap/v_stale_claims 比较失真(误/漏回收)。**G-CR1-01 在内核真正落点**,与 G-CR1-01/02/03 同根 | open · blocker · 主审实测 |
| G-CR4-03 | CR-4 (R3) | L/correctness | **critical** | `workflow_clean/service.py:118,129` / `worker/main.py:53` | 执行器自提交 succeeded+下游 step,早于 succeed_claim;main 忽略返回值;副作用无幂等键 → 过期租约竞态下双重执行 | open · blocker · 主审实测 |
| G-CR4-04 | CR-4 (R4) | L+D/correctness | high | `workflow_core/restart.py:79` | restart 写畸形 available_at → v_ready_steps 比较非确定性 → 被重启 step ~40% 概率本分钟永不就绪,restart 静默失效 | open · blocker |
| G-CR4-05 | CR-4 (R5) | B+L/scope-drift | high | `workflow_core/restart.py:72-99` | restart 总从 clean 重跑,mode 死参,丢失 legacy 按失败 step/阶段精细重启 | open · blocker |
| G-CR4-06 | CR-4 (R6) | L/correctness | high | `management/service.py:136,148` | 确定性 request_id + 无 ON CONFLICT → 二次 restart/purge PK 冲突 500(重启一次后永不可再重启) | open · followup |
| G-CR4-07 | CR-4 (R7) | B/correctness | medium | `workflow_core/retry.py:74` | retry 退避恒 1s,schema retry_backoff_seconds(60)从不读,reap 退避 0s | open · followup |
| G-CR4-08 | CR-4 (R8) | B/correctness | medium | `worker/main.py:54-56` | error_code 恒 EXECUTOR_FAILURE,丢失 legacy 错误分类与不可重试判定 | open · followup |
| G-CR4-09 | CR-4 (R9) | B+D/correctness | high | `workflow_core/graph.py` vs `events.py` | 重复事件写入器:graph 导出但死代码(commit+正确时间)vs events 内用(无commit+畸形时间),导出面错位 | open · followup |
| G-CR4-10 | CR-4 (R10) | B/scope-drift | medium | `workflow_core/{restart,purge}.py:12-26` | create_*_request `**kwargs:str` 类型错误 + scope/include_objects 不可达(关联 G-CR3-05) | open · followup |
| G-CR4-11 | CR-4 (R11) | L/correctness | medium | `workflow_core/retry.py:35` | step_attempts id=attempt_{claim_id} 依赖 claim↔attempt 1:1,与 UNIQUE(step,attempt) 语义错位 | open · followup |
| G-CR4-12 | CR-4 (R12) | C1/correctness | medium | `workflow_core/{restart,purge}.py` | restart/purge 整批单事务 → 一个坏 request 拖垮整批核心改动('processing' 从不持久可见) | open · followup |
| G-CR4-13 | CR-4 (R13) | C4/correctness | medium | `workflow_core/{restart,purge}.py` | 失败/中间态转移只写 audit 不写 event;孤儿文档 purge 跳过 event | open · followup |

> CR-4 verdict: **changes-requested**(实质 blocked),不收口,5 个 blocker(G-CR4-01~05)。报告全文见 `part-cr-4.md`。
> 关键澄清(本簇独立纠正前序):① **纠正 CR-1/G-CR1-01** —— 时间 bug 真正落点是 lease_expires_at 比较(G-CR4-02)+ restart available_at(G-CR4-04);fresh/retry step 的 v_ready_steps **不受影响**,CR-1"fresh step 永不就绪"撤回。② **纠正 CR-3/G-CR3-12** —— purge 崩溃不卡 processing,实为批量单事务回滚退 pending(改记 G-CR4-12)。
> 正面事实:claim 单 worker 原子安全(BEGIN IMMEDIATE + 唯一索引兜 TOCTOU);主状态转移 event+audit 双写;purge 跨库崩溃靠 delete_chunks 幂等自愈。

### 阶段三(并行分派)· CR-5 / CR-6 / CR-7

| G-CR5-01 | CR-5 (R1) | B+D/security | high | `auth/service.py` / `api_keys` 表 | 团队 API key 认证整簇缺失(api_keys 零访问),legacy 有 validate_api_key 全链路 | open · blocker(条件) |
| G-CR5-02 | CR-5 (R2) | B/security | high | `ingestion/service.py:17` / `routes/ingestion.py` | 路径遍历源头:HTTP `filename` 零校验直拼 object_key(CR-3 G-CR3-01 的可达注入入口),控制面未纵深防御 | open · blocker |
| G-CR5-03 | CR-5 (R3) | L/correctness | medium | `auth/service.py:17` | 密码哈希与 legacy 不兼容,"legacy 兼容"claim 不成立 | open · followup |
| G-CR5-04 | CR-5 (R4) | B/scope-drift | medium | `apps/api/routes/*` | legacy 20 RPC 中 5 个缺失(reset_password/update_workflow/static delete/create_api_key/validate_api_key) | open · followup |
| G-CR5-05 | CR-5 (R5) | L/correctness | medium | `apps/api/routes/*` | service 层 ValueError 未映射 HTTP 状态码 → 业务错误返 500 | open · followup |
| G-CR6-01 | CR-6 (R1) | B/scope-drift | **critical** | `cleaners_universal/service.py` | universal cleaner 7-9 个 action 全未实现(纯正则桩),无 fetch/浏览器/PDF/Gemini | open · blocker |
| G-CR6-02 | CR-6 (R2) | B/scope-drift | **critical** | `providers_dedicated/service.py` | dedicated provider 硬编码 chinatax 单分支,只加前缀不发请求,无 registry/scatter/child files | open · blocker |
| G-CR6-03 | CR-6 (R3) | L/correctness | **critical** | `workflow_clean/service.py:118,129` | 执行器自提交 succeeded + 下游副作用无幂等键(承接 G-CR4-03,clean 侧落点) | open · blocker |
| G-CR6-04 | CR-6 (R4) | B+D/scope-drift | high | `workflow_clean/service.py` | action registry/list_actions 抽象整体丢失,执行器 if/else 硬选 | open · blocker |
| G-CR6-05 | CR-6 (R9) | B/scope-drift | high | `workflow_clean/service.py` | finalizer 仅标准交接,scatter/差分/child files 全缺 | open · followup |
| G-CR7-01 | CR-7 (R1) | B/correctness | **critical** | `rag_vectorizer/embedder.py:6` | embedder 是 SHA-256 伪向量(零语义),RAG 检索价值归零;legacy 调真实 Workers AI embedding | open · blocker · 主审实测 |
| G-CR7-02 | CR-7 (R4) | L/correctness | **critical** | `workflow_rag/service.py` | construct 调 upsert 不传 embedding_rowid + 每次新 chunk_id → 触发 G-CR3-03 孤儿累积 | open · blocker |
| G-CR7-03 | CR-7 (R2) | B/scope-drift | high | `rag_structurizer/service.py` | structurize 朴素 `\n` 分段,丢失 ~67% legacy AI 结构化能力 | open · blocker |
| G-CR7-04 | CR-7 (R3) | B/scope-drift | high | `rag_constructor/service.py` | construct 仅定长拼接,summary 通道 + layer-json 完全缺失(~55% 缺) | open · blocker |
| G-CR7-05 | CR-7 (R5+R6) | L+D/correctness | high | `workflow_rag/service.py` | 无独立 rag:vectorize step(内联于 construct),偏离五步序,违反"每 step 可 claim/重试/重启" | open · blocker |
| G-CR7-06 | CR-7 (R7) | L/correctness | high | `workflow_rag/service.py:226,233` | 执行器自提交 succeeded + run completed 早于 succeed_claim(rag 侧 G-CR4-03 落点) | open · blocker |

> **CR-5 verdict**: changes-requested,不收口,2 blocker(G-CR5-01 条件/02)。RPC parity 15/20(75%)。控制面 CRUD + 三类 ingestion 数据流真实成立(都建出 source/document/run/step),认证面(api_key 缺失)、路径安全、密码兼容未收口。报告 `part-cr-5.md`。
> **CR-6 verdict**: changes-requested(近 blocked),不收口,4 blocker。**clean action parity:universal 0/7、dedicated 0/3 真实现** —— legacy ~10.6k 行 clean 能力在 Python 仅 ~31 行真实算法,整条 clean 执行链是占位桩,url/PDF 源会产出垃圾污染下游全部 chunk/embedding。报告 `part-cr-6.md`。
> **CR-7 verdict**: changes-requested(近 blocked),不收口,6 blocker。**embedder 是 SHA-256 伪向量(已实测,RAG 价值归零)**;structurize+construct ~2/3 为盲点;无独立 vectorize step + 自提交 + 孤儿 rowid 联动 CR-3/CR-4。正面:search 读路径(v_search_hydration+post-filter+半文件降级)是本簇唯一较完整真实现。报告 `part-cr-7.md`。
> **跨簇纠偏**:附录 **A1(stage 命名断点)经 CR-5/CR-6 实测证伪** —— 实际 stage 字符串与 worker 派发匹配,非 bug,已关闭。

### 收尾簇 · CR-8

| G-CR8-01 | CR-8 (R1) | test-gap | **critical** | `tests/`(20 函数) | 测试结构性假绿:20 函数全弱/空洞/桩固化,unit/e2e 空,无正确性/安全/并发/语义断言 | open · blocker · 主审实测 |
| G-CR8-02 | CR-8 (R2) | test-gap | **critical** | `tests/.../test_kernel_flow.py:75-83` | 夹具手写 SQL 覆盖 lease_expires_at(正确格式)绕过 now_iso bug,孤立单测掩盖 reap 死代码 + 时间 bug + 双重执行 | open · blocker · 主审实测 |
| G-CR8-03 | CR-8 (R3) | D/correctness | high | `apps/worker/main.py:35-57` | worker 漏装 reap → 任一 worker 中断即对该文档死锁(G-CR4-01 的 E2E 确认) | open · blocker |
| G-CR8-04 | CR-8 (R4) | B/correctness | **critical** | search 端到端 | embedding 伪向量 → 端到端"名义通、语义空"(G-CR7-01 的 E2E 确认) | open · blocker |
| G-CR8-05 | CR-8 (R5) | docs-gap | high | `docs/closure/.../P3-P7-closure.md:37` | closure `14 passed` 陈旧(实为 20)且五份复制,vector/retrieval/cutover ✅ 为无效证据 | open · blocker |
| G-CR8-06 | CR-8 (R7) | D/delivery-gap | medium | `apps/api/main.py` | API 无 lifespan/CORS/全局异常处理;/healthz 假健康检查 | open · followup |

> **CR-8 verdict**: changes-requested(实质 blocked),不收口,4 blocker(G-CR8-01~05)。报告 `part-cr-8.md`(含全程序级 8 簇收口总账)。
> 关键:① **测试是结构性假绿**(20 函数非 closure 称的 14,unit/e2e 空,夹具掩盖时间 bug)—— 这是前 7 簇 blocker 能全部潜伏却显绿的根因。② 端到端管道接得上但**语义为空**(伪向量)+ **故障恢复缺装**(reap)。③ A1 第三次证伪。

---

## 全审查收口声明(8 簇完成 · 2026-05-31)

CR-1~CR-8 八簇全部完成,**无任一簇可收口**,全程序合计 blocker 去重后约 28 个。整体判断:`smind-family` 当前是"管道接得上、语义为空、测试无法证明正确性"的骨架,P0–P7 不具备"已完成"实质。

**根因主线**(详见 part-cr-8.md 附录):① 时间格式单点根因(G-CR1-01)波及 lease/restart;② 假绿链(vec0 退化 + 伪 embedder + clean/rag 全桩 + 弱测试 + 陈旧 closure)使核心能力空缺被系统性掩盖;③ 执行器/内核职责撕裂致双重执行;④ 适配层安全缺陷(路径遍历)。

**修复优先级**:P0 语义/安全/数据完整性(时间根因→reap→双重执行→路径遍历→rowid 重号→真实 embedding)→ P1 可靠性 → P2 能力去桩 → **P3 重建测试有效性 + closure 重新定级(在此之前任何"已完成"声明不可信)**。

**诚实账**:本轮 4 处早期候选/前序结论经独立实测被推翻或收窄(A2、CR-1 v_ready_steps、CR-3 G-CR3-12、A1),均已就地更正 —— 多 agent 独立验证 + 主审复核的流程有效防止了错误结论沉淀。
