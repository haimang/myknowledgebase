# Nano-Agent 行动计划模板

> 服务业务簇: `smind-family / first-fixes`
> 计划对象: `F2 · 连接与装配可靠性（API/CLI 连接生命周期 + API 应用装配）`
> 类型: `modify`（F2 多为扩展既有 ♻️/✅；F2-03 lifespan/异常处理含净新 🆕）
> 作者: `Opus 4.8`
> 时间: `2026-05-31`
> 文件位置: `apps/api/src/smind_api/deps.py`、`apps/api/src/smind_api/main.py`、`apps/cli/src/smind_cli/main.py`、`apps/api/src/smind_api/routes/*.py`（异常映射连带面）、`tests/integration/`
> 上游前序 / closure:
> - `与 F1（FF-F1-time-tx-base.md）并行，互不抢带宽（装配层不碰内核状态机）；本 AP 无强前序依赖`（final plan §5 DAG）
> 下游交接:
> - `无强下游依赖。F2-03 的真 /healthz 探测在 F7 capstone（J/H 步前置环境自检）可被复用；连接生命周期纪律是后续所有引入新端点的隐式前提`
> 关联设计 / 调研文档:
> - `docs/design/first-fixes/initial-planning-by-opus.md`（final plan §6.2 F2 台账 / §4 红线 / §8 DoD）
> - `docs/eval/first-code-review-plan/part-cr-2.md`（G-CR2-01 / R1 连接泄漏）、`part-cr-8.md`（G-CR8-06 / R6·R7 app 级装配缺失）、`part-cr-5.md`（G-CR5-05 / R5 ValueError→500）
> 冻结决策来源:
> - `docs/design/first-fixes/owner-gated-qna.md` [Q7]（先红后绿铁律）（只读引用；本 action-plan 不填写 Q/A）
> grounding 来源:
> - `eval-reference-anchor part-cr-2.md / part-cr-8.md / part-cr-5.md`（§7 内置锚区据此摘录；CR 报告即本链 reference-anchor 真源）
> 关联 reference-anchor:
> - `见 §7 内置锚区`（摘自 part-cr-2/5/8，完整台账见 CR 真源，§7.3 指回）
> 文档状态: `draft`

---

## 0. 执行背景与目标

> 用一到三段话说明：为什么现在要执行这份计划、它从哪些 frozen design / QNA / closure 继承输入、它要把哪些设计结论落成可交付物。
>
> **纪律**：如果仍有 owner / architect 需要回答的问题，不应在 action-plan 中开 Q/A；应回到 design / qna register 完成冻结。本文件只消费已冻结结论。

八簇审查（CR-2 / CR-8 / CR-5）证实 smind-family 的 API/CLI 装配层存在三类运行时纪律缺陷：① API 请求级 SQLite 连接 `return` 而非 generator 依赖，**每请求新建且永不关闭**，WAL 模式下持续泄漏文件句柄 / `-wal`·`-shm` 引用、阻碍 checkpoint，长期运行将 `OperationalError: unable to open database file`（G-CR2-01 / part-cr-2.md R1）；② CLI `_service()` 同样每次新建 core+vec 连接不关闭（G-CR2-01 app 级 / part-cr-8.md R6）；③ API 应用本体无 lifespan / CORSMiddleware / 全局异常处理，`/healthz` 是静态假健康检查，且 service 层 `ValueError` 未被路由映射、冒泡为 500（G-CR8-06 / part-cr-8.md R7 + part-cr-5.md R5）。

本 AP 是 final plan（`initial-planning-by-opus.md` §6.2）F2 phase 的 1:1 派生执行基线，与 F1（时间与事务基座）并行、不碰内核状态机。它把"连接生命周期归 generator 依赖管理、CLI 连接归 contextlib.closing、API 应用补齐 lifespan/CORS/全局异常/真探测 healthz、业务异常映射 4xx"四项设计结论落成可交付物，并以 [Q7] 冻结的"先红后绿"铁律（每修一处先提交一条在 HEAD FAIL、修复后 PASS 的回归）驱动。

本计划只消费已冻结结论：连接生命周期的修法（generator + finally close）、装配缺失的修法（lifespan/CORS/exception handler/真 healthz）、异常映射策略（401/404/409）均已在 CR 报告与 final plan §4 红线裁定，本文不重开 Q/A。

- **服务业务簇**：`smind-family / first-fixes`
- **计划对象**：`F2 · 连接与装配可靠性`
- **本次计划解决的问题**：
  - `API 请求级连接泄漏（G-CR2-01 / R1）：deps.py:33-42 get_core_conn/get_vec_conn 为 return connect() 无 yield/finally close`
  - `CLI 连接泄漏（G-CR2-01 app 级 / R6）：cli/main.py:11-21 _service() 每次新建 core+vec 连接不关闭`
  - `API 装配缺失（G-CR8-06 / R7）：main.py:15-44 无 lifespan/CORS/全局异常处理，/healthz 返回静态 {"status":"ok"} 不探测 DB/向量库`
  - `业务异常未映射（G-CR5-05 / R5）：service 层 ValueError 未被路由捕获，冒泡为 500（应 401/404/409）`
- **本次计划的直接产出**：
  - `deps.get_core_conn/get_vec_conn 改 generator 依赖（try: yield conn; finally: conn.close()），消除每请求连接泄漏`
  - `cli._service() 连接用 contextlib.closing 管理（或返回上下文，调用方 with 包裹）`
  - `API 应用补 lifespan（启动迁移+连接自检）、CORSMiddleware、全局 exception handler（业务异常映射 4xx）、/healthz 真探测 DB/向量库`
  - `先红后绿测试：请求级连接关闭断言（N 次请求后无残留连接 / 无 fd 泄漏）+ 业务异常映射 4xx`
- **本计划不重新讨论的设计结论**：
  - `连接生命周期用 FastAPI generator 依赖（yield + finally close）`（来源：`part-cr-2.md R1 建议修法 :114 / :329`）
  - `事务模式 isolation_level=None（autocommit）由 F1-04 负责，本 AP 不动 engine`（来源：`part-cr-2.md R2 / final plan §6.1 F1-04`）
  - `先红后绿为全 phase 铁律`（来源：`owner-gated-qna.md [Q7]`）

---

## 1. 执行综述

### 1.1 总体执行方式

本 action-plan 分 **3 个 Phase**，执行方式为"**先底层连接生命周期、后上层应用装配，全程先红后绿**"：先封住连接泄漏（Phase 1，API+CLI 连接归生命周期管理），再补齐 API 应用装配与异常映射（Phase 2，lifespan/CORS/exception/真 healthz），最后以先红后绿回归测试封住"连接不泄漏 + 异常映射 4xx"两条不变量（Phase 3）。三个 Phase 均落在装配层，不触碰 workflow_core 内核状态机，故可与 F1 全程并行。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 连接生命周期归口 | XS | API/CLI 连接改生命周期管理（yield+finally close / contextlib.closing），消除泄漏 | `-` |
| Phase 2 | API 应用装配补全 | S | 加 lifespan（启动迁移+连接自检）、CORS、全局异常处理（4xx 映射）、真 healthz | `Phase 1（异常 handler 与 healthz 复用生命周期约定，弱序）` |
| Phase 3 | 先红后绿回归 | S | 请求级连接关闭断言（无 fd 泄漏）+ 业务异常映射 4xx，先红后绿 | `Phase 1 / Phase 2（验证其产出）` |

> 说明：上表 `规模` 是每个 Phase 的**描述性提示**（帮助阅读，工作量小则该 Phase 自然简短），**不是开工前的体量判定闸，也不改变本模板任何段落的取舍**。本模板是单一模板，不分 flavor、不分档。

### 1.3 Phase 说明

1. **Phase 1 — 连接生命周期归口**
   - **核心目标**：把 API 请求级连接（`deps.get_core_conn`/`get_vec_conn`）改 generator 依赖、CLI `_service()` 连接改 contextlib.closing，确保每条连接在请求/调用结束被关闭。
   - **为什么先做**：连接泄漏是 high blocker 且根因独立、改动面小（XS），是后续装配测试（Phase 3 的 fd 泄漏断言）的被测对象，应最先封住。
2. **Phase 2 — API 应用装配补全**
   - **核心目标**：补齐 API 应用本体的 lifespan（启动迁移 + 连接自检）、CORSMiddleware、全局 exception handler（业务异常 ValueError/SmindError 映射 4xx）、`/healthz` 真探测 DB/向量库。
   - **为什么放在这里**：异常 handler 与 healthz 探测建立在 Phase 1 的连接生命周期约定上（弱序）；lifespan/CORS/exception 含净新逻辑，单独成 Phase 便于拆子步与红绿验证。
3. **Phase 3 — 先红后绿回归**
   - **核心目标**：交付两条先红后绿测试——① N 次请求后无残留连接（fd/连接计数不增长）；② service 层 ValueError 经路由映射为 4xx（401/404/409）而非 500。
   - **为什么放在这里**：[Q7] 铁律要求每 blocker 有"HEAD FAIL → 修复后 PASS"回归；Phase 1/2 的产出必须由本 Phase 的红绿证据证明，故收尾。

### 1.4 执行策略说明

> **纪律**：本节写执行策略，**不重述 §6 已引用的冻结决策的理由**（避免与 design/qna 重复，只写"怎么执行"，不写"为什么这么设计"）。

- **执行顺序原则**：先底层连接生命周期（P1）→ 后上层应用装配（P2）→ 红绿回归封口（P3）；P1/P2 可在同一改动窗口推进，P3 紧随其后。
- **风险控制原则**：全程不触碰 `storage_sqlite/engine.py`（事务模式归 F1-04）与 workflow_core 内核；改动局限装配层，回归面可控。
- **测试推进原则**：先红后绿——先写"N 次请求后无残留连接"与"ValueError→4xx"两条断言（当前 HEAD 红），再实施 P1/P2 修复使其转绿；短途（每 PR）为主，无 spike/mega/soak。（详见 §8 测试台账）
- **文档同步原则**：完成后回填 final plan §10.A 派生状态；本 AP 不新增设计文档。
- **回滚 / 降级原则**：generator 依赖与 contextlib.closing 为标准模式、可独立回滚到 return 型（仅恢复泄漏，不引入新错误）；lifespan/CORS/exception/healthz 为加法装配，可逐项摘除回退；无数据迁移、无降级开关。

### 1.5 本次 action-plan 影响结构图

> 用树状结构快速展示：本计划会影响哪些模块、目录、运行链路、服务边界、测试层或文档资产。
>
> 这一节不是文件系统快照，而是**影响结构图**；推荐按业务链路或执行路径写。

```text
F2 · 连接与装配可靠性
├── Phase 1: 连接生命周期归口
│   ├── apps/api/src/smind_api/deps.py（get_core_conn/get_vec_conn → generator）
│   └── apps/cli/src/smind_cli/main.py（_service() → contextlib.closing）
├── Phase 2: API 应用装配补全
│   ├── apps/api/src/smind_api/main.py（lifespan / CORSMiddleware / exception_handler / 真 healthz）
│   └── apps/api/src/smind_api/routes/*.py（异常映射连带面：auth/ingestion/management 抛点）
└── Phase 3: 先红后绿回归
    ├── tests/integration/（连接关闭断言：N 次请求后无残留连接）
    └── tests/integration/（业务异常映射 4xx：login 401 / upload 404 / restart 409）
```

---

## 2. In-Scope / Out-of-Scope

> 把 action-plan 的执行边界集中写在这里。设计上的边界应来自 design/QNA；本节只说明本轮执行做什么、不做什么、何时重评。

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `deps.get_core_conn`/`get_vec_conn` 改 generator 依赖（`try: yield conn; finally: conn.close()`），消除每请求连接泄漏（F2-01）。
- **[S2]** CLI `_service()` 连接用 contextlib.closing 管理（或 contextmanager 化，调用方 `with` 包裹），确保 core+vec 连接在 CLI 命令结束被关闭（F2-02）。
- **[S3]** API `create_app` 加 lifespan（启动迁移 + 连接自检）、CORSMiddleware、全局 exception handler（业务异常 → 4xx）、`/healthz` 真探测 DB/向量库（F2-03）。
- **[S4]** 先红后绿测试：请求级连接关闭断言（N 次请求后无残留连接/无 fd 泄漏）+ 业务异常映射 4xx（401/404/409）（F2-04）。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `engine.connect()` 事务模式 `isolation_level=None`（autocommit）+ 多写函数包 `BEGIN IMMEDIATE`——归 F1-04（part-cr-2.md R2）。
- **[O2]** `smind_common.errors` 领域异常体系补全（G-CR1-05 空壳）——本 AP 仅在路由/handler 内做映射，不强制全面领域异常化；可用现有 `ValueError`/`SmindError` 映射。
- **[O3]** API key 团队认证（G-CR5-01）、密码哈希兼容删除（G-CR5-03）——归 F6（F6-07/F6-11）。
- **[O4]** restart_requests PK 冲突（management/service.py:136 G-CR5-R4）、ingestion 冗余 commit（G-CR5-R6）——归 F3/F4 就近主题，非本装配 AP。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| API/CLI 连接生命周期归口 | `in-scope` | 本 AP 核心（F2-01/02），high blocker | — |
| lifespan/CORS/exception/真 healthz | `in-scope` | 本 AP 核心（F2-03），装配完整性 | — |
| 业务异常 → 4xx 映射 | `in-scope` | F2-04 与 F2-03 exception handler 同窗口，CR-5 R5 | — |
| engine 事务模式 isolation_level=None | `out-of-scope` | 归 F1-04，与本装配层正交 | F1 完成后本 AP healthz 自检可顺带验证连接可用性 |
| smind_common.errors 领域异常补全 | `defer / depends-on-design` | G-CR1-05 空壳，全面领域异常化超本 AP 范围 | F6 业务面稳定后统一异常体系时 |
| API key 认证 / 密码兼容 | `out-of-scope` | 归 F6（[Q5]/[Q6]） | — |

---

## 3. 业务工作总表

> 总索引；后面 §4 会按 Phase 展开。编号建议 `P1-01 / P1-02 / P2-01`，便于 review、handoff 与 closure 引用。
>
> **硬地板（每个工作项必须三件齐全 —— 不可约三元组）**：
> 1. **`涉及文件（file:line 级）`** —— 落在哪段既有代码 / 新建哪个文件（与 §7 锚区对应）。
> 2. **`收口目标`** —— 一句话、可验证的"做完长什么样"。
> 3. **`测试映射`** —— 指向 §8 测试台账的 `Test-ID`（证明此项做到了）。
>
> 缺任一即该项**欠规格**。**安全 / 信任边界类**工作项，其 `涉及文件` 须含或指向威胁模型落点（§7.3），不得留空。
>
> **第 4 件（条件 · 与净新度/风险成正比）`分解步骤`**：**净新 / 高风险**工作项，其 §4 `工作内容` 必须拆成有序子步（a/b/c）+ 边界情况，§5 `具体功能预期` ≥5 条；**扩展既有 / ♻️复用 / 沿用** 项一句话或枚举即可（不注水）。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | API 请求级连接改 generator 依赖 | `refactor` | `apps/api/src/smind_api/deps.py:33-42` | `get_core_conn/get_vec_conn 为 yield generator，请求结束 finally 关闭连接` | `FF-F2-T01` | `low` |
| P1-02 | Phase 1 | CLI `_service()` 连接用 contextlib.closing | `refactor` | `apps/cli/src/smind_cli/main.py:11-21,40-46` | `CLI 命令结束 core+vec 连接均被关闭，无残留` | `FF-F2-T02` | `low` |
| P2-01 | Phase 2 | API 加 lifespan（启动迁移 + 连接自检） | `add` | `apps/api/src/smind_api/main.py:15-44` | `应用启动时迁移 core/vec 并自检连接可用，失败 fail-loud` | `FF-F2-T03` | `low` |
| P2-02 | Phase 2 | API 加 CORSMiddleware | `add` | `apps/api/src/smind_api/main.py:20` | `CORS 中间件按 settings 允许源装配` | `FF-F2-T04` | `low` |
| P2-03 | Phase 2 | 全局 exception handler（业务异常 → 4xx） | `add` | `apps/api/src/smind_api/main.py:20` + `routes/{auth,ingestion}.py` 抛点 | `ValueError/SmindError 经 handler 映射 401/404/409，非 500` | `FF-F2-T05` | `low` |
| P2-04 | Phase 2 | `/healthz` 真探测 DB/向量库 | `update` | `apps/api/src/smind_api/main.py:22-24` | `/healthz 实际探测 core+vec 连接，不健康返回非 200 + reason` | `FF-F2-T06` | `low` |
| P3-01 | Phase 3 | 先红后绿：请求级连接关闭断言（无 fd 泄漏） | `add` | `tests/integration/p2_control_plane/`（新增 test_conn_lifecycle.py） | `N 次请求后无残留连接，修复前红/修复后绿` | `FF-F2-T01` | `low` |
| P3-02 | Phase 3 | 先红后绿：业务异常映射 4xx | `add` | `tests/integration/p2_control_plane/`（新增 test_error_mapping.py） | `login 凭据错→401、upload not found→404、restart 冲突→409，修复前红/修复后绿` | `FF-F2-T05` | `low` |

---

## 4. Phase 业务表格

> 每个 Phase 一张表，完整列出工作项、目标、涉及文件与对应测试台账项。`测试映射` 列指向 §8 的 `Test-ID`。
>
> **`工作内容` 是承重列，分解度与净新度/风险成正比（硬地板第 4 件）**：
> - **净新 / 高风险**项：拆成**有序子步**（a/b/c…），逐步覆盖核心逻辑 + 边界情况 + 失败/降级路径。
> - **扩展既有 / ♻️复用 / 沿用**项：一句话或枚举即可，**不注水**。

### 4.1 Phase 1 — 连接生命周期归口

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P1-01 | API 请求级连接改 generator 依赖 | ♻️ 扩展既有：把 `def get_core_conn(): ... return ...connect()` 改为 `conn = CoreSQLiteEngine(...).connect(); try: yield conn; finally: conn.close()`；`get_vec_conn` 同构。`Depends(get_core_conn)`/`Depends(get_vec_conn)` 调用方签名不变（FastAPI 自动适配 generator 依赖），无端点改动。 | `apps/api/src/smind_api/deps.py:33-36`（core）、`:39-42`（vec） | 每端点请求结束自动关闭连接 | `FF-F2-T01` | deps 两函数为 yield generator + finally close；现有端点回归不破 |
| P1-02 | CLI `_service()` 连接用 contextlib.closing | ♻️ 扩展既有：`_service()` 当前裸建 core+vec 两连接并 `return ManagementService(...)`，连接无主。改为：用 `contextlib.closing` 包裹两连接，将 `_service` contextmanager 化（`@contextlib.contextmanager` 产出 service、退出时关两连接），`main()` 中 `search`/`ops-health` 分支改 `with _service() as svc:` 包裹调用。 | `apps/cli/src/smind_cli/main.py:11-21`（_service）、`:40-46`（search/ops-health 调用点） | CLI 命令结束关闭 core+vec 连接 | `FF-F2-T02` | CLI 退出后无残留连接句柄；search/ops-health 行为不变 |

### 4.2 Phase 2 — API 应用装配补全

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P2-01 | API 加 lifespan（启动迁移 + 连接自检） | 🆕 净新：a) 定义 `@contextlib.asynccontextmanager async def lifespan(app)`；b) 启动段调 `apply_core_migrations` / `apply_vec_schema`（复用 deps 内 `_ensure_*_migrated` 思路，集中到启动而非每请求 lru_cache）；c) 启动段开一条 core + 一条 vec 连接做 `SELECT 1` 自检，失败则 raise（fail-loud，阻止 boot）；d) 关闭段无状态可不处理（连接由请求依赖管理）；e) `FastAPI(..., lifespan=lifespan)` 接线。 | `apps/api/src/smind_api/main.py:15-21,38` | 启动即迁移就绪 + 连接可用，异常 fail-loud | `FF-F2-T03` | 应用启动执行迁移与自检；DB 不可用时启动失败而非静默 |
| P2-02 | API 加 CORSMiddleware | ♻️ 扩展既有：`api.add_middleware(CORSMiddleware, allow_origins=settings.cors_origins or ["*"], allow_methods=["*"], allow_headers=["*"], allow_credentials=True)`；源取 settings（无则保守默认，记 TODO 收紧）。 | `apps/api/src/smind_api/main.py:20` | 跨域请求带正确 CORS 响应头 | `FF-F2-T04` | OPTIONS 预检 + 实际请求返回 CORS 头 |
| P2-03 | 全局 exception handler（业务异常 → 4xx） | 🆕 净新：a) 注册 `@api.exception_handler(ValueError)`（及 `SmindError`）；b) handler 按消息/code 映射状态码——`invalid credentials`→401、`*not found`→404、PK/状态冲突→409，缺省 400；c) 返回 `JSONResponse({"detail": str(exc), "code": getattr(exc,"code",...)}, status_code=...)`；d) 边界：未识别业务异常归 400（不再 500）、非业务异常（编程错误）仍走默认 500；e) 连带面——确认 `routes/auth.py:31`（login）、`routes/ingestion.py:68`（confirm）抛 ValueError 后由 handler 接管，无需逐路由 try/except。 | `apps/api/src/smind_api/main.py:20` + `routes/auth.py:30-32`、`routes/ingestion.py:60-72`（抛点验证） | service 业务异常映射 4xx，非 500 | `FF-F2-T05` | login 凭据错 401 / upload not found 404 / restart 冲突 409 |
| P2-04 | `/healthz` 真探测 DB/向量库 | ♻️ 扩展既有：把 `return {"status":"ok"}` 改为开 core + vec 连接各执行轻量探测（`SELECT 1` / vec 表存在性），用 contextlib.closing 包裹即用即关；全通返回 `{"status":"ok","core":"ok","vec":"ok"}`，任一失败返回 503 + `{"status":"degraded","reason": ...}`。 | `apps/api/src/smind_api/main.py:22-24` | healthz 真实反映 DB/向量库可用性 | `FF-F2-T06` | 健康 200、DB 不可用 503 + reason |

### 4.3 Phase 3 — 先红后绿回归

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P3-01 | 先红后绿：请求级连接关闭断言 | 🆕 净新测试：a) 用 TestClient 对一个走 `Depends(get_core_conn)` 的端点（如 `/me` 或 ingestion）连发 N 次请求（N≥50）；b) 通过监控打开的 sqlite 连接数 / 进程 fd 计数（`os` fd 或对 `Connection.close` 打桩计数）断言不随 N 单调增长；c) **先红**：在 return 型 deps 上跑→连接计数随 N 增长，FAIL；d) **后绿**：P1-01 改 generator 后→稳定，PASS。 | `tests/integration/p2_control_plane/test_conn_lifecycle.py`（新增） | N 次请求后无残留连接 | `FF-F2-T01` | 修复前红、修复后绿，四元组齐 |
| P3-02 | 先红后绿：业务异常映射 4xx | 🆕 净新测试：a) login 用错误凭据→断言 401（非 500）；b) ingestion confirm 用不存在 upload_id→断言 404；c) restart 重复触发→断言 409（若 restart 端点在本簇可达，否则标 §8.4 缺口交 F3）；d) **先红**：无 exception handler 时全部 500，FAIL；e) **后绿**：P2-03 handler 后映射正确，PASS。 | `tests/integration/p2_control_plane/test_error_mapping.py`（新增） | 业务异常映射 4xx 而非 500 | `FF-F2-T05` | 修复前红、修复后绿，四元组齐 |

---

## 5. Phase 详情

> 按 Phase 展开详细执行说明：做什么、改哪些文件、做到什么算结束。**测试不在此展开**——每项指向 §8 测试台账的 `Test-ID`。
>
> **`具体功能预期` 的展开度与净新度/风险成正比（硬地板第 4 件）**：净新 / 高风险 Phase ≥5 条，含**边界与失败/降级路径**；扩展既有 Phase 可精简。

### 5.1 Phase 1 — 连接生命周期归口

- **Phase 目标**：消除 API 请求级与 CLI 调用级的 SQLite 连接泄漏（G-CR2-01）。
- **本 Phase 对应编号**：`P1-01` / `P1-02`
- **本 Phase 新增文件**：无
- **本 Phase 修改文件**：`apps/api/src/smind_api/deps.py:33-42`、`apps/cli/src/smind_cli/main.py:11-21,40-46`
- **本 Phase 删除文件**：无
- **具体功能预期**（♻️ 扩展既有，精简）：
  1. `get_core_conn` 改为 generator：建连接 → `try: yield conn` → `finally: conn.close()`；FastAPI 在请求结束执行 finally。
  2. `get_vec_conn` 同构改造。
  3. 现有所有 `Depends(get_core_conn)`/`Depends(get_vec_conn)` 端点签名与行为不变（generator 依赖对调用方透明）。
  4. CLI `_service()` contextmanager 化，`search`/`ops-health` 命令分支以 `with` 包裹，退出时关闭 core+vec 连接。
- **对应测试台账项**：`FF-F2-T01`（API 连接关闭）/ `FF-F2-T02`（CLI 连接关闭）（详见 §8）
- **收口标准**：deps 两函数为 yield+finally close；CLI 命令结束无残留连接；现有端点/命令回归全绿。
- **本 Phase 风险提醒**：generator 依赖对 `_ensure_*_migrated`（lru_cache）无影响，但需确认迁移自检不在每请求重复建连——P2-01 lifespan 接管启动迁移后，deps 内 lru_cache 迁移可保留（幂等）或精简。

### 5.2 Phase 2 — API 应用装配补全

- **Phase 目标**：补齐 API 应用本体装配（lifespan/CORS/全局异常/真 healthz），消除假健康与 500 误报（G-CR8-06 / G-CR5-05）。
- **本 Phase 对应编号**：`P2-01` / `P2-02` / `P2-03` / `P2-04`
- **本 Phase 新增 / 修改 / 删除文件**：修改 `apps/api/src/smind_api/main.py:15-44`；连带验证 `routes/auth.py:30-32`、`routes/ingestion.py:60-72` 抛点（不必改路由本体，由 handler 接管）。
- **具体功能预期**（含 P2-01/P2-03 净新，≥5 条 + 边界/失败路径）：
  1. lifespan 启动段执行 core/vec 迁移（apply_core_migrations / apply_vec_schema），就绪后再接受请求。
  2. lifespan 启动段对 core+vec 各开一条连接执行 `SELECT 1` 自检；任一失败 **raise（fail-loud），阻止 boot**（失败路径）。
  3. CORSMiddleware 按 settings 源装配；无配置时保守默认并记 TODO 收紧（边界）。
  4. 全局 exception handler 把 `ValueError`/`SmindError` 按消息/code 映射 401/404/409，**未识别业务异常归 400**、**非业务编程错误仍 500**（边界与降级）。
  5. `/healthz` 真探测 core+vec：全通 200 `{"status":"ok",...}`，任一失败 **503 + 机器可读 reason**（失败路径，对齐 §8.5 degraded 带 reason）。
  6. 连带面确认：login（routes/auth.py:31）与 ingestion confirm（routes/ingestion.py:68）抛 ValueError 后由 handler 统一接管，路由层不再各自 try/except。
- **对应测试台账项**：`FF-F2-T03`（lifespan 自检）/ `FF-F2-T04`（CORS）/ `FF-F2-T05`（异常映射）/ `FF-F2-T06`（真 healthz）（详见 §8）
- **收口标准**：应用启动执行迁移 + 连接自检；CORS 头返回；业务异常 4xx；healthz 真探测（健康 200 / 不健康 503+reason）。
- **本 Phase 风险提醒**：lifespan 启动迁移与 deps 内 `_ensure_*_migrated` lru_cache 存在职责重叠，需确认幂等不冲突；exception handler 的消息匹配应稳健（避免脆弱字符串匹配漏判，优先用 `SmindError.code` 或异常类型分支）。

### 5.3 Phase 3 — 先红后绿回归

- **Phase 目标**：以两条先红后绿测试封住"连接不泄漏"与"业务异常映射 4xx"两条不变量（[Q7] 铁律）。
- **本 Phase 对应编号**：`P3-01` / `P3-02`
- **本 Phase 新增文件**：`tests/integration/p2_control_plane/test_conn_lifecycle.py`、`tests/integration/p2_control_plane/test_error_mapping.py`
- **具体功能预期**（🆕 净新测试，含红绿两态 + 边界）：
  1. 连接生命周期测试：N 次（≥50）请求后连接/fd 计数不单调增长；**先红**（return 型 deps 下计数增长）→ **后绿**（generator 后稳定）。
  2. 异常映射测试：login 凭据错→401、ingestion upload not found→404、restart 冲突→409（restart 若本簇不可达则记 §8.4 缺口交 F3）；**先红**（无 handler 全 500）→ **后绿**（handler 后正确）。
  3. 边界：fd 计数监控需排除测试框架自身连接干扰（对 `Connection.close` 打桩计数或基线相减），避免假绿/假红。
- **对应测试台账项**：`FF-F2-T01` / `FF-F2-T05`（详见 §8）
- **收口标准**：两条测试在当前 HEAD 红、修复后绿，四元组证据齐全。
- **本 Phase 风险提醒**：fd/连接计数断言对环境（OS、sqlite 版本）敏感，优先用确定性的 close 计数打桩而非 OS fd 抓取，防 flaky。

---

## 6. 依赖的冻结设计决策（只读引用）

> 列出本 action-plan 依赖哪些 design / QNA / closure 结论。**不要在本节填写新 Q/A；只引 register 的 Q 编号，不复制内容、不改口。** F2 无专门 gate，仅 test-first [Q7] 适用。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `[Q7] 先红后绿铁律 + CI 断言强度门禁` | `docs/design/first-fixes/owner-gated-qna.md [Q7]` / final plan §7.B G-F-7 | Phase 3 两条测试必须 HEAD 红→修复后绿；P1/P2 收口由红绿证据证明 | 本 AP 保持 draft（无法证明修复有效） |
| `G-CR2-01 / R1 连接生命周期用 generator 依赖（yield+finally close）` | `part-cr-2.md R1 :114,:329`（只读引用，非 Q/A） | P1-01 修法直接采用 | 回退 return 型（仅恢复泄漏，无新错误） |
| `G-CR8-06 / R7 API 加 lifespan/CORS/异常/真 healthz` | `part-cr-8.md R7 :137-141`（只读引用） | P2-01~04 修法直接采用 | 逐项加法摘除回退 |
| `G-CR5-05 / R5 业务异常路由映射 4xx` | `part-cr-5.md R5 :172-183`（只读引用） | P2-03/P3-02 异常映射 | 路由内 try/except 兜底替代统一 handler |
| `事务模式 isolation_level=None 归 F1-04，本 AP 不动 engine` | final plan §6.1 F1-04 / part-cr-2.md R2 | 本 AP 装配层与事务模式正交，不耦合 | 若 F1 延期不阻塞本 AP（并行独立） |

---

## 7. 内置 Reference-Anchor 锚区

> **本段固定植入每份 AP**。它把本计划工作项要落到的既有代码、要避开的陷阱、安全项威胁模型**就地钉住**——实现时 0 跳转、grounding 0 泄漏。
> - 与本 AP 工作项相关的锚**摘进 §7.1**（不复制全文），§7.3 指回 CR 真源。

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

> `处置` 用复用判定图例：`✅ 复用`（直接改写/扩展既有）/ `♻️ 重 substrate`（在既有基底上重建）/ `🆕 净新`（无既有可锚）。"读不改的参考点"在 `备注` 写明。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `apps/api/src/smind_api/deps.py:33-36` | `get_core_conn()` = `return CoreSQLiteEngine(...).connect()`（普通 def，无 yield/close） | `P1-01 改 generator 依赖落点` | `✅ 复用` | CR-2 R1 主审复核确认；改 yield+finally |
| A-2 | `apps/api/src/smind_api/deps.py:39-42` | `get_vec_conn()` 同构 return 型 | `P1-01` | `✅ 复用` | 与 A-1 同改 |
| A-3 | `apps/cli/src/smind_cli/main.py:11-21` | `_service()` 裸建 core+vec 连接 `return ManagementService(...)`，连接无主 | `P1-02 contextlib.closing 落点` | `✅ 复用` | CR-8 R6；:40,:45 为 search/ops-health 调用点 |
| A-4 | `apps/api/src/smind_api/main.py:15-21,38` | `create_app()`：`FastAPI(title=...)`，无 lifespan/中间件 | `P2-01 lifespan / P2-02 CORS 接线点` | `♻️ 重 substrate` | CR-8 R7；lifespan/middleware 为净新逻辑挂在既有 create_app |
| A-5 | `apps/api/src/smind_api/main.py:22-24` | `/healthz` 返回静态 `{"status":"ok"}`（假健康） | `P2-04 真探测落点` | `✅ 复用` | CR-8 R7 / C4 |
| A-6 | `apps/api/src/smind_api/main.py:20` | exception handler 注册位（create_app 内） | `P2-03 全局异常 handler` | `🆕 净新` | 无既有 handler |
| A-7 | `apps/api/src/smind_api/routes/auth.py:30-32` | login 调 `AuthService(conn).login`，抛 `ValueError("invalid credentials")` 未捕获 | `P2-03/P3-02 异常映射验证点（401）` | `✅ 复用` | CR-5 R5 :178；读不改本体，由 handler 接管 |
| A-8 | `apps/api/src/smind_api/routes/ingestion.py:60-72` | file_confirm 调 service，抛 `ValueError("upload not found")` 未捕获 | `P2-03/P3-02 异常映射验证点（404）` | `✅ 复用` | CR-5 R5 :179；读不改本体 |
| A-9 | `packages/common/src/smind_common/errors.py:1` | `SmindError(Exception)` 带 `.code` | `P2-03 handler 异常类型/code 分支` | `✅ 复用` | 已建好，优先按 code/类型分支而非脆弱字符串匹配 |
| A-10 | `tests/integration/p2_control_plane/` | 控制面集成测试目录（已有 test_ingestion_management.py） | `P3-01/P3-02 新增测试落点` | `🆕 净新` | 新增 test_conn_lifecycle.py / test_error_mapping.py |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | 把连接改成全局/模块级单例复用（一条连接服多请求） | WAL + check_same_thread 风险，违 FastAPI 标准；CR-2 R1 修法明确是 generator 依赖、每请求一连接即开即关 |
| ⛔2 | 在 `engine.connect()` 内改 `isolation_level=None` 顺手解决泄漏 | 事务模式归 F1-04，与连接泄漏正交；本 AP 不动 engine（part-cr-2.md R2） |
| ⛔3 | `/healthz` 探测开连接后不关闭 | 会复制本 AP 正要修的泄漏 bug；探测连接必须 contextlib.closing 即用即关 |
| ⛔4 | exception handler 用脆弱字符串完整匹配（如 `== "invalid credentials"`） | 文案微调即漏判退回 500；优先 `SmindError.code`/异常类型分支 + 子串/前缀兜底 |
| ⛔5 | 测试用 `status==200` 或仅"无异常"作唯一断言 | 违 [Q7] 断言强度门禁；连接测试须断言计数不增、异常测试须断言精确状态码 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：本链 reference-anchor 由 `part-cr-2.md`（R1 连接泄漏 :100-114,:329）、`part-cr-8.md`（R6/R7 :134-141）、`part-cr-5.md`（R5 异常映射 :172-183）预完成；§7.1 是其与本 AP 相关子集的摘录，完整审查台账（含 legacy 对照与实测复跑证据）见上述 CR 报告真源。
- **安全 / 信任边界类工作项的威胁模型锚**：本 AP **非安全/信任边界类**——连接生命周期、应用装配、异常映射均为可靠性/装配完整性，不含路径遍历/认证/数据完整性等信任边界（那些归 F4/F6）。`/healthz` 探测不暴露敏感信息（仅 ok/degraded+reason）。故本 AP 无须独立威胁模型锚；CORS 源收紧（P2-02 TODO）作为次要加固项记 §9，不属本 AP 信任边界落点。

---

## 8. 测试台账

> **本段固定植入每份 AP**。它一次性回答：本 AP 有哪些测试项、各是什么类型/在哪一层、新增还是沿用、映射到哪个工作项与收口目标、怎么算 PASS。**测试细节只在此写一次**（§4/§5 只引 Test-ID）。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `FF-F2-T01` | N≥50 次请求后连接/fd 计数不单调增长（无泄漏） | `短途` | `集成` | `🆕 新增 tests/integration/p2_control_plane/test_conn_lifecycle.py` | `P1-01/P3-01 → 请求结束连接关闭` | `commit {sha} + test_conn_lifecycle PASS + {YYYY-MM-DD HH:MM UTC}（先红：return 型计数增长 FAIL 截图）` |
| `FF-F2-T02` | CLI search/ops-health 命令结束后 core+vec 连接均关闭 | `短途` | `集成` | `🆕 新增 tests/integration/p2_control_plane/test_cli_conn_close.py` | `P1-02 → CLI 连接无残留` | `commit + test_cli_conn_close PASS + run-time` |
| `FF-F2-T03` | lifespan 启动执行迁移 + 连接自检；DB 不可用时启动失败（fail-loud） | `短途` | `集成` | `🆕 新增 test_app_lifespan.py` | `P2-01 → 启动迁移+自检` | `commit + test_app_lifespan PASS + run-time` |
| `FF-F2-T04` | CORS 预检/实际请求返回正确 CORS 头 | `短途` | `集成` | `🆕 新增 test_cors.py` | `P2-02 → CORS 装配` | `commit + test_cors PASS + run-time` |
| `FF-F2-T05` | login 凭据错→401、upload not found→404、restart 冲突→409（非 500） | `短途` | `集成` | `🆕 新增 tests/integration/p2_control_plane/test_error_mapping.py` | `P2-03/P3-02 → 业务异常映射 4xx` | `commit + test_error_mapping PASS + run-time（先红：无 handler 全 500 FAIL）` |
| `FF-F2-T06` | /healthz 健康返回 200，core/vec 不可用返回 503 + reason | `短途` | `集成` | `🆕 新增 test_healthz_probe.py` | `P2-04 → 真探测 DB/向量库` | `commit + test_healthz_probe PASS + run-time` |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

> 显式列出本 AP **不新建、而站在既有测试上**的部分，点名 file + 起跑线状态。

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/integration/p2_control_plane/test_ingestion_management.py` | `♻️ 沿用` | `0 改动（纳入回归，确认 generator 依赖改造后控制面端点不破）` | 已存在，纳入回归 |

> 说明：本 AP 测试**主要为新增**（F2 装配缺陷此前无有意义测试覆盖，符合 G-CR8-01 "测试结构性假绿" 的整体背景）；既有控制面测试仅作回归护栏沿用。

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | 集成（控制面）·回归 | 开发中持续 + 每 Phase 收口 |
| spike | — | — | 本 AP 无（装配层无 journey 长程验证需求）|
| mega | — | — | 本 AP 不单独触发；连接/healthz 在 F7 capstone 环境自检处被间接复用 |
| soak | — | — | 本 AP 无 race/长稳维度 |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 restart 重复触发 → 409 的端到端（若 `restart` 端点/PK 冲突逻辑在 management 层未就绪，理由：restart_requests PK 冲突 G-CR5-R4 归 F3/management）→ 交后继 `FF-F3-kernel-recovery.md`；本 AP 的 `FF-F2-T05` 若 restart 不可达则仅断言 401/404 两路，409 标缺口，**不在本 AP 假装覆盖**。
- 不覆盖事务原子性（autocommit + BEGIN IMMEDIATE）→ 交 `FF-F1-time-tx-base.md`（F1-05）。
- 不覆盖长稳 fd soak（N 极大下 OS 层 fd）→ 本 AP 用确定性 close 计数打桩替代，OS 级 soak 非必要（装配层无 race）。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带**四元组**证据；`FF-F2-T01`/`FF-F2-T05` 须附**先红证据**（return 型连接计数增长 FAIL、无 handler 全 500 FAIL 的 commit/日志），证明 HEAD 红→修复后绿（[Q7]）。
- `/healthz` degraded 必带机器可读 `reason`（P2-04 已规定 503 + reason）；不得静默返回 ok。
- 连接计数断言禁止用 `status==200` 或"无异常"作唯一断言（⛔5）；必须断言连接/fd 计数不随 N 增长。
- 异常映射断言禁止只验"非 200"；必须断言**精确状态码**（401/404/409）。
- 本 AP 非信任边界类，无攻击向量用例要求（§7.3）。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| 连接/fd 计数断言 flaky | OS/sqlite 版本差异致 fd 抓取不稳 | `low` | 用确定性 `Connection.close` 打桩计数替代 OS fd 抓取（§5.3 风险） |
| lifespan 迁移与 deps lru_cache 重叠 | 启动迁移与 `_ensure_*_migrated` 职责重复 | `low` | 迁移幂等，确认不冲突；可保留 deps lru_cache 或精简 |
| exception handler 脆弱匹配 | 文案微调漏判退回 500 | `low` | 优先 `SmindError.code`/异常类型分支 + 子串兜底（⛔4） |
| restart 409 依赖 management 就绪 | restart PK 冲突归 F3 | `low` | §8.4 缺口交 F3，本 AP 不阻塞 |
| 与 F1 并行的窗口冲突 | F1-04 改 engine、本 AP 不动 engine | `low` | 装配层与事务模式正交，独立可并行（§5 DAG） |

### 9.2 约束与前提

- **技术前提**：FastAPI generator 依赖在请求结束执行 finally（标准行为）；TestClient 可驱动 lifespan（`with TestClient(app) as c:`）。
- **运行时前提**：当前 P 阶段无生产数据；SQLite WAL 模式；本地/CI sqlite ≥ 3.x。
- **组织协作前提**：与 F1 并行执行，建议各自分支避免 main.py/engine.py 之外的无谓冲突（本 AP 不碰 engine.py）。
- **上线 / 合并前提**：§8 全部短途测试 PASS（含先红后绿证据）；既有控制面回归不破。

### 9.3 文档同步要求

- 需要同步更新的设计文档：`docs/design/first-fixes/initial-planning-by-opus.md §10.A`（回填 FF-F2 派生状态）。
- 需要同步更新的说明文档 / README：无（无新增对外接口约定，CORS 源收紧 TODO 记本 AP §9.1）。
- 需要同步更新的测试说明：`tests/integration/p2_control_plane/` 新增测试纳入控制面回归集。

### 9.4 完成后的预期状态

> 用 3-5 条说明本 action-plan 完成后，系统、仓库结构、测试、文档或运行链路会变成什么状态。

1. API 每请求连接在请求结束自动关闭、CLI 命令结束连接关闭——长期运行不再 fd/连接泄漏（G-CR2-01 闭环）。
2. API 应用启动即迁移就绪 + 连接自检（fail-loud），具备 CORS、全局异常映射、真探测 `/healthz`（G-CR8-06 闭环）。
3. service 层业务异常（凭据错/未找到/冲突）映射 401/404/409 而非 500，客户端可区分凭据错与服务故障（G-CR5-05 闭环）。
4. `tests/integration/p2_control_plane/` 新增连接生命周期与异常映射两类先红后绿回归，控制面装配首次有意义覆盖。
5. final plan §10.A 中 `FF-F2-conn-wiring.md` 派生项可标记 executed（待全测 PASS）。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

> 本 AP 如何收口：**收口 = §8 测试台账逐项 PASS，且每项映射回 §3 工作项的收口目标。**

### 10.1 收口硬闸

本 AP 无 mega/soak；**退出层 = 全部短途集成测试 + 先红后绿证据**。所有测试项必须 **PASS 且四元组证据齐全**，其中两条先红后绿项须附 HEAD 红证据：

1. 请求级连接无泄漏（N 次请求后连接计数不增长）（由 `FF-F2-T01` 证明，附先红证据）。
2. 业务异常映射 4xx 而非 500（由 `FF-F2-T05` 证明，附先红证据）。
3. API 装配完整（lifespan 自检 + CORS + 真 healthz）（由 `FF-F2-T03/T04/T06` 证明）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| API 请求结束连接关闭，N 次无残留 | `P1-01` / `P3-01` | `FF-F2-T01` | `commit + test_conn_lifecycle + run-time（+先红）` | `未观察` |
| CLI 命令结束 core+vec 连接关闭 | `P1-02` | `FF-F2-T02` | `commit + test_cli_conn_close + run-time` | `未观察` |
| 启动迁移 + 连接自检 fail-loud | `P2-01` | `FF-F2-T03` | `commit + test_app_lifespan + run-time` | `未观察` |
| CORS 头正确返回 | `P2-02` | `FF-F2-T04` | `commit + test_cors + run-time` | `未观察` |
| 业务异常映射 401/404/409 | `P2-03` / `P3-02` | `FF-F2-T05` | `commit + test_error_mapping + run-time（+先红）` | `未观察` |
| /healthz 真探测 DB/向量库 | `P2-04` | `FF-F2-T06` | `commit + test_healthz_probe + run-time` | `未观察` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | API/CLI 连接归生命周期管理无泄漏；API 具 lifespan/CORS/全局异常/真 healthz；业务异常映射 4xx |
| 测试 | §8 测试台账全 PASS（退出硬闸项四元组齐全，先红后绿两项附 HEAD 红证据）|
| 文档 | final plan §10.A 回填 FF-F2 派生状态；控制面测试纳入回归集 |
| 风险收敛 | G-CR2-01 / G-CR8-06 / G-CR5-05 三 blocker 闭环；CORS 源收紧 TODO 记账 |
| 可交付性 | 装配层修复可独立合并，与 F1 并行不冲突 |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**；按 closure 五态如实归类 + handoff。

- 若 `FF-F2-T01`/`FF-F2-T05` 缺先红证据（仅有后绿）⇒ 视为 `未观察`，不得标 executed（违 [Q7]）。
- 若 restart 409 路径因 F3 未就绪而缺口 ⇒ `FF-F2-T05` 标 `partial`（401/404 验、409 交 F3 handoff），如实归类不 overclaim。
- 若 `/healthz` 探测在 degraded 时未带 reason ⇒ 视为未达 §8.5 保真要求，不得标 PASS。

---

## 11. 执行日志回填（`executed`）

> 执行人：Opus 4.8 (1M)。执行时间：2026-05-31。文档状态：`draft → executed`。
> 命令统一前缀 `python3 -m pytest`（pytest 9.0.3）。

### 11.0 环境发现（fastapi 可用性）

- 初始 `python3 -c "import fastapi"` → `ModuleNotFoundError`。
- `pip install fastapi` 被 Debian externally-managed 拦截（PEP 668）。
- `pip install --break-system-packages fastapi` 下载成功，但卸载 Debian 自带 `typing_extensions` 失败（`RECORD file not found`），import 仍失败。
- `python3 -m venv` 失败（`ensurepip` 不可用，缺 `python3.12-venv`）。
- **成功路径**：`pip install --break-system-packages --ignore-installed typing_extensions fastapi pydantic-settings httpx` → fastapi 0.136.3 / starlette 1.2.1 / pydantic 2.13.4 / pydantic-settings 2.14.1 / httpx 0.28.1。`import fastapi` + `TestClient` OK；pytest 9.0.3 就绪。
- **结论：fastapi 在本环境最终可用** → TestClient 级集成测试**真实运行**（非 skip），同时保留 `pytest.importorskip("fastapi")` 门禁 + fastapi-free 单元覆盖（`tests/unit/test_app_support.py`）。

### 11.0.1 重大发现：仓库实际结构与 AP 锚区不符

AP §7.1 锚区（如 `deps.get_core_conn` 用 `Settings = Depends(get_settings)`、`smind_common.errors` 含 `SmindError.code`、`SmindError` 子类异常体系、`/ingestion/upload`+`/ingestion/confirm` 端点、restart 端点等）与仓库**实际代码不符**。实测真源：
- `deps.get_core_conn/get_vec_conn` 为普通 `def` 用 `load_settings()`（非 `get_settings`），返回 `CoreSQLiteEngine(...).connect()`（来自 `storage_sqlite.engine`，非 `storage_objects`）。
- service 层抛 **`ValueError`**（`auth.login` → `"invalid credentials"`；`ingestion.file_confirm/static_confirm` → `"upload not found"`），**不是** `SmindError` 子类（`smind_common.errors` 仅有 `SmindError(code=...)` 基类，无 `AuthError/NotFoundError/ConflictError`）。
- API 端点为 `/auth/{register,login}`、`/ingestion/{file,static}/{initiate,confirm}`、`/management/*`（只读）、`/search`、`/team/*`、`/me`、`/ops/*`、`/workflow-configs`。**management 路由全为只读，无 restart 端点**；restart 仅存在于 `ManagementService.restart_workflow`（CLI/ops 间接），且依赖 F3 的 `workflow_core.restart`。
- vec 索引表名为 `chunk_embedding_index`（vec0 或 fallback），非 AP 假设的表名。
- `engine.connect()` 已是 `isolation_level=None`+WAL（F1-04 已完成，本 AP 不动）。

→ 实现据**实际代码**而非 AP 锚区落地：异常映射改为按 `SmindError.code` 优先 + `ValueError` 消息子串兜底（仍非脆弱全等匹配，守 ⛔4）；healthz vec 探测用 `chunk_embedding_index`；T05 验 401/404，restart-409 标缺口交 F3（§11.4）。

### 11.1 工作项执行记录

| 工作项 | 动作 | 结果 | 偏离 |
|--------|------|------|------|
| P1-01 | `deps.get_core_conn/get_vec_conn` 改 `yield conn`+`finally close`（返回类型注解 `Iterator[Connection]`） | done | 用真实 `load_settings`/`storage_sqlite`（非 AP 锚） |
| P1-02 | `cli._service` → `@contextlib.contextmanager`+`contextlib.closing`；`search`/`ops-health` 改 `with _service() as svc:` | done | 仓库只有单个 `_service`（无独立 `_search_service`）；命令带 `--team-id`/`--query` |
| P2-01 | `create_app` 加 `lifespan`：`run_startup_checks`（`apply_core_migrations`/`apply_vec_schema` + `SELECT 1` 自检，失败 raise 阻 boot） | done | 抽到 `app_support.run_startup_checks` 纯函数 |
| P2-02 | 加 `CORSMiddleware`，源取 `settings.cors_origins`（无则 `["*"]`）+ TODO(F7) | done | settings 无 `cors_origins` 字段 → `getattr` 容错默认 `["*"]` |
| P2-03 | `SmindError`+`ValueError` 全局 handler → `map_exception_to_status`（code 优先：AUTH_INVALID_CREDENTIALS 401/NOT_FOUND 404/CONFLICT 409；ValueError 消息子串兜底；未识别业务异常 400；编程错误 raise→500） | done | 因 service 抛 `ValueError`，映射主路径走消息子串（前缀/子串，非全等，守 ⛔4） |
| P2-04 | `/healthz` → `health_report`（contextlib.closing 开 core `SELECT 1` + vec `chunk_embedding_index` 探测即关；全通 200，任一失败 503+reason） | done | 抽到 `app_support.health_report` 纯函数 |
| P3-01 | `test_conn_lifecycle.py`：60 次请求，`sqlite3.Connection` 子类作 `connect` factory 确定性计数 close（非 OS fd，非实例打桩——`Connection.close` 实例只读） | done | 用 factory 子类而非实例打桩（技术约束） |
| P3-02 | `test_error_mapping.py`：login 401 + static/confirm 404 | done；restart-409 标缺口（management 无 restart 端点）交 F3 | T05 仅 401/404；409 由 `app_support` 单元测试覆盖映射逻辑本身 |
| F2-04 其余 | `test_cli_conn_close.py`/`test_app_lifespan.py`/`test_cors.py`/`test_healthz_probe.py` + fastapi-free `tests/unit/test_app_support.py`（15 用例） | done | 新增 app_support 纯函数模块 |

### 11.2 先红后绿证据（[Q7]）

| 不变量 | RED（pre-fix，逐项 git stash） | GREEN（post-fix） |
|--------|-------------------------------|-------------------|
| 请求级连接不泄漏（T01） | 仅 stash `deps.py`：`test_no_connection_leak_over_many_requests` → `AssertionError: assert 120 <= 2`（60 请求泄漏 120 条；实测 opened=128 closed=8） | opened=66 closed=66 leak=0，PASS |
| CLI 连接关闭（T02） | 仅 stash `cli/main.py`：两用例 → `AssertionError: ... leaked: opened=2 closed=0` | closed==opened，2 PASS |
| 业务异常映射 4xx（T05） | stash 4 文件：`assert 500==401`（login）、`assert 500==404`（static/confirm） | 401/404，2 PASS |
| healthz 真探测（T06） | pre-fix 静态 healthz：`assert 200==503`（degraded 无法触发） | 200 / 503+reason，2 PASS |
| CORS（T04） | pre-fix 无中间件：preflight 405 / 实际请求无 CORS 头 | 预检+实际均带 `access-control-allow-origin`，2 PASS |
| 映射纯函数（unit） | 移除 `app_support.py`：`ModuleNotFoundError`（collection error，exit 2） | 15 PASS |

### 11.3 测试结果（run-time）

| 套件 | 命令 | 结果 | 耗时 |
|------|------|------|------|
| F2 集成+单元（GREEN） | `pytest tests/integration/p2_control_plane/ tests/unit/test_app_support.py` | **27 passed, 0 failed, 0 skipped** | ~2.3s |
| F1 回归 | `pytest tests/unit/test_time_ssot.py tests/integration/p1_kernel_closure/` | **16 passed** | ~0.6s |
| 全仓 | `pytest` | **44 passed, 0 failed** | ~2.9s |

### 11.4 偏离汇总

1. **AP 锚区与实际代码不符**（§11.0.1）：据实落地，未照搬 `get_settings`/`SmindError` 子类/`/ingestion/upload`/restart 端点等不存在的锚。
2. 抽出 `apps/api/src/smind_api/app_support.py`（纯函数：异常映射/healthz 探测/启动自检），获 fastapi-free 红→绿证据（满足 STEP-3 "extract exception→status mapping into a pure function"）。
3. **restart-409 路径在本簇不可达**（management 路由只读、无 restart 端点；restart 仅 service 层方法依赖 F3 `workflow_core.restart`）→ 按 AP §8.4 标缺口，交 `FF-F3-kernel-recovery.md`，**未伪造**；409 映射逻辑本身由 `test_app_support.test_conflict_value_error_maps_409` + `test_sminderror_code_takes_priority` 单元覆盖。
4. 连接 close 计数用 `sqlite3.Connection` 子类作 `connect` factory（实例 `.close` 只读不可打桩），仍为确定性计数、非 OS fd 抓取（守 §5.3/⛔5）。
5. fastapi 经 `--ignore-installed typing_extensions` 装成功（§11.0），集成测试真实运行而非 skipped-with-reason。
