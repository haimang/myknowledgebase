# 行动计划 · RW-C — 真实 live 接线（真实 LLM + 真实 embedding，gated 延后）

> 服务业务簇: `real-wire / live 接线（真实 provider 客户端 + 退避/错误分类/维度守卫 + 密钥 + live smoke lane）`
> 计划对象: `RW-C phase（final-execution-plan §6.C，台账 RWC-01..06）`
> 类型: `new`（真实 provider 客户端净新；替 mock）
> 作者: `Opus 4.8`
> 时间: `2026-06-01`
> 文件位置: `packages/providers_*/（真实 LLM/Embedder 客户端）· packages/config/（key 注入）· tests/（live lane）`
> 上游前序 / closure:
> - `docs/action-plan/real-wire/RW-A-provider-base.md`（协议/工厂/路由 — 真实实现挂载点）
> - `docs/action-plan/real-wire/RW-B-prompt-ssot-chain.md`（prompt 链 — 把 MockLLM 换真实 provider）
> - `docs/eval/real-wire/final-execution-plan-by-opus.md` §6.C（SCOPE↓ 延后）
> 下游交接:
> - `（live 接入手册 + closure，本轮不产）`
> 关联设计 / 调研文档:
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 C 锚定矩阵）
> 冻结决策来源:
> - `docs/eval/real-wire/pre-charter-qna.md`（frozen 框架；**provider 具体口径未冻结，待后续 provider charter**）
> grounding 来源:
> - `eval-reference-anchor 轴 C`（退避/错误分类算法 + 维度守卫 + 反例）
> 关联 reference-anchor:
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（§7.3 指回真源）
> 文档状态: `executed（scaffolding；2026-06-01, commit fec0bb3; closure: docs/closure/real-wire/RW-C-closure.md）— 脚手架 verified；真实 MLX 推理 + live smoke 仍 deferred 至 provider charter`

---

## 0. 执行背景与目标

> **⚠️ 本 AP 为 `draft (blocked)`**：冻结 qna 的 reframe 把「具体 LLM/embedding provider adapter（本地 MLX 模型 vs 外部厂商、厂商/模型、计费数值、外部 key）」**整体推到后续 provider charter**。本 AP 据 final §6.C 提前**铺好执行骨架与 grounding**，但**不得标 `executing/executed`，也不得开工真实客户端**，直到后续 charter 冻结 Q-RW-2(厂商/本地)、Q-RW-6(计费数值)、Q-RW-7(外部 key)。本节及 §6 列出阻塞条件。

RW-C 是把 RW-A 的协议/工厂/路由 + RW-B 的 prompt 链中的 **MockLLMProvider/mock embedding 替换为真实 provider** 的阶段。reference-anchor 轴 C 已确认：可借的是**退避/重试/错误分类算法**（`embedder.ts:40-164`/`:73`）与 HEAD 已有的**维度守卫**（`embedder.py:82`）+ **写/查 model 过滤**（`search.py:40-49`）；**Cloudflare Workers-AI/AI Gateway binding 一律 ⛔ 不可借**，真实客户端按厂商净新。维度锁 1024（RW-A 已迁），真实 embedding 须返 1024 维否则 fail-loud。

- **服务业务簇**：`real-wire / live 接线`
- **计划对象**：`RW-C phase（RWC-01..06）`
- **本次计划解决的问题（解锁后）**：
  - mock 无真实语义——真实 LLM 处理 + 真实 embedding 检索缺位。
  - 真实调用需退避/重试/错误分类/预算护栏；密钥需安全注入（不进仓/日志）。
- **本次计划的直接产出（解锁后）**：
  - 真实 `LLMProvider`（厂商客户端 + 退避/重试/速率/错误分类）。
  - 真实 `Embedder`（本地 MLX 或外部 API，**1024 维守卫**）。
  - 密钥管理（`.env` + 构造注入）+ mock↔live 切换端到端一致 + live smoke（owner-triggered，不进默认 CI）+ 接入手册。
- **本计划不重新讨论的设计结论（已框架冻结）**：
  - 维度 1024（来源：`Q-RW-1`，RW-A 已迁）。
  - `.env`+构造注入、严禁模块级全局 key 轮转（来源：`Q-RW-7` + 反例 ⛔）。
  - 默认 mock、live 单独 owner-triggered lane、不进默认 CI（来源：`Q-RW-6` 框架）。
- **本计划仍需后续 charter 冻结（阻塞项）**：
  - provider 具体选择（本地 MLX 模型 vs 外部厂商；厂商/模型）—— `Q-RW-2`（延后）。
  - 计费/速率/预算数值 —— `Q-RW-6`（延后）。
  - 外部厂商 key 需求 —— `Q-RW-7`（延后）。

---

## 1. 执行综述

### 1.1 总体执行方式

**解锁后**：先实现真实客户端（借退避/分类算法）→ 接 RW-A 工厂的 `"mlx"`/厂商占位槽 → mock↔live 切换一致性验证 → owner-triggered live smoke + 预算护栏。本轮（provider charter 前）仅**铺骨架与 grounding**，不开工。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 真实 LLM/embedding 客户端 | L | 厂商客户端 + 退避/分类 + 1024 守卫 | RW-A/B + provider charter |
| Phase 2 | 密钥管理 + 切换一致性 | M | `.env`+构造注入 + mock↔live 端到端结构一致 | Phase 1 + Q-RW-7 |
| Phase 3 | live smoke + 预算护栏 + 手册 | M | owner-triggered live 一次性 smoke + 护栏 + closure | Phase 2 + Q-RW-6 |

### 1.3 Phase 说明

1. **Phase 1 — 真实客户端**：核心目标=真实 LLM/embedding 替 mock；为什么先做=切换/smoke 依赖真实实现。
2. **Phase 2 — 密钥 + 切换**：核心目标=安全注入 + mock↔live 一致；放这里=客户端就绪后才能验切换。
3. **Phase 3 — smoke + 护栏**：核心目标=owner 复核的一次性 live + 预算/速率护栏；放这里=收口硬闸。

### 1.4 执行策略说明

- **执行顺序原则**：客户端 → 密钥/切换 → smoke/护栏。
- **风险控制原则**：默认 mock；live 默认关、owner-triggered；预算/速率护栏 fail-loud。
- **测试推进原则**：mock 一致性入 CI（不打外网）；live smoke 为 mega（owner-triggered，默认 skip）。
- **文档同步原则**：live 接入手册 + closure 据真实证据定级。
- **回滚 / 降级原则**：live 失败回落 mock；维度漂移 fail-loud；外部模型装不上回落（G-RW-1 备选）。

### 1.5 本次 action-plan 影响结构图

```text
RW-C live 接线（gated）
├── Phase 1: 真实客户端
│   ├── packages/providers_*/（真实 LLMProvider：退避/分类/速率）
│   └── packages/providers_*/（真实 Embedder：本地 MLX/外部 API + 1024 守卫）
├── Phase 2: 密钥 + 切换
│   ├── packages/config/（.env 构造注入；key 不入日志）
│   └── mock↔live 切换一致性
└── Phase 3: smoke + 护栏 + 手册
    ├── tests/（live lane，owner-triggered，默认 skip）
    └── 预算/速率护栏 + 接入手册 + closure
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（解锁后明确要做）

- **[S1]** 真实 `LLMProvider`（厂商客户端 + 退避/重试/速率/错误分类）。
- **[S2]** 真实 `Embedder`（本地 MLX 或外部 API，1024 维守卫泛化）。
- **[S3]** 密钥管理（`.env`+构造注入，不入日志）+ mock↔live 切换一致性。
- **[S4]** live smoke（owner-triggered，不进默认 CI）+ 预算/速率护栏 + 接入手册 + closure。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 多 provider 抽象（[Q3] 范围外；单厂商/单模型起步）。
- **[O2]** PDF/二进制、真实 vec0 —— RW-D。
- **[O3]** 计费/速率具体数值的产品化策略 —— 由 Q-RW-6 给定后落地，不在此设计。
- **[O4]** 维度 schema 改动（锁 1024，TR-2）。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 真实客户端实现 | defer / depends-on-charter | provider 具体口径未冻结（Q-RW-2）| 后续 provider charter |
| 退避/错误分类算法 | in-scope（解锁后）| 算法可直采（embedder.ts:40-164/:73）| — |
| 1024 维守卫 | in-scope（解锁后）| 维度漂移 fail-loud（TR-2）| — |
| 外部 key 注入 | defer | Q-RW-7 外部 key 需求延后 | provider charter |
| live 默认进 CI | out-of-scope | TR-5 测试不打外网 | — |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| RWC-01 | Phase 1 | 真实 `LLMProvider`（退避/重试/速率/错误分类）| add | `packages/providers_*/...（新建）`、借 `embedder.ts:40-164,:73` | 真实客户端 + 退避/分类；接工厂槽 | RWC-T01 | high |
| RWC-02 | Phase 1 | 真实 `Embedder`（本地 MLX/外部 API）+ 1024 守卫 | add | `packages/providers_*/...（新建）`、`embedder.py:82` | 真实 embedding；!=1024 fail-loud | RWC-T02 | high |
| RWC-03 | Phase 2 | 密钥管理（`.env`+构造注入，不入日志）| add | `packages/config/...`、`.env`(git-ignored) | key 构造注入；不入仓/日志 | RWC-T03 | high |
| RWC-04 | Phase 2 | mock↔live 切换端到端一致 | add | `tests/...` | 同 capstone 在 mock/live 结构一致 | RWC-T04 | medium |
| RWC-05 | Phase 3 | live smoke（owner-triggered）+ 预算/速率护栏 | add | `tests/...（live lane，默认 skip）` | 一次性 live smoke + 护栏 fail-loud | RWC-T05 | high |
| RWC-06 | Phase 3 | live 接入手册 + closure 据真实证据定级 | add | `docs/...` | 手册 + closure 五态如实定级 | RWC-T06 | low |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 真实 LLM/embedding 客户端

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWC-01 | 真实 `LLMProvider` | a) 按 charter 定厂商实现 `complete/complete_json`（httpx 或本地 MLX 推理）；b) 退避循环借 `embedder.ts:40-42,115-164`（MAX_RETRIES=3/INITIAL_DELAY=1s/BACKOFF=2）；c) 错误分类借 `embedder.ts:73-79`（429/timeout/overload/connection→可重试；401/422→不可重试）；d) HTTP 错误提取借 `ai_gateway.ts:128-182`（检 !ok + body/status + 抛分类异常）；e) 模型参数默认借 `gemini.ts:61-86`，按厂商重映射请求体；f) **不借 Workers-AI/AI Gateway binding**（⛔）；g) 接 RW-A 工厂的厂商/mlx 槽（替占位 NotImplementedError）| `packages/providers_*/...（新建）`；借 `embedder.ts:40-164` | 真实客户端 + 退避/分类；工厂可返回 | RWC-T01 | 退避/分类单测（注入假错误）+ 接工厂 |
| RWC-02 | 真实 `Embedder` | a) 按 G-RW-1 charter 定（本地 MLX 模型 / 外部 1024 维 API）实现 `embed`；b) **维度守卫泛化 `!= self.dimension(1024)` fail-loud**（`embedder.py:82`）；c) 写/查同 embedder（TR-3，复用 search.py:40-49 model 过滤）；d) 边界：模型装不上/维度≠1024 → fail-loud + reason；e) 接 RW-A 工厂 embedder 槽 | `packages/providers_*/...（新建）`；`embedder.py:82`、`search.py:40-49` | 真实 embedding；!=1024 fail-loud | RWC-T02 | 维度守卫 + 写查一致 |

### 4.2 Phase 2 — 密钥管理 + 切换一致性

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWC-03 | 密钥管理 | a) `.env`(git-ignored) + `.env.example` 占位进仓；b) key 经 provider **构造注入**（`LLMProvider(api_keys=[...])`），轮转封装实例内——**严禁** `gemini.ts:96-132` 的模块级全局轮转（⛔）；c) key 不入日志/不入仓/不入夹具（TR-5/F6c⛔1）；d) 边界：缺 key 时 live 路径 fail-loud，mock 路径不需 key | `packages/config/...`、`.env` | key 构造注入；不入仓/日志 | RWC-T03 | 缺 key fail-loud + 日志无 key 断言（攻击向量用例）|
| RWC-04 | 切换一致性 | RW-B 的 mock capstone 在 `live` 模式（真实 provider）下结构一致（步骤/契约一致，质量不同）；Settings 切 mock↔live | `tests/...` | 同 capstone mock/live 结构一致 | RWC-T04 | mock/live 双跑结构一致断言 |

### 4.3 Phase 3 — live smoke + 护栏 + 手册

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWC-05 | live smoke + 护栏 | a) owner-triggered live lane（默认 skip，不进默认 CI）；b) 一次性端到端 live smoke（真实 key）；c) 预算/速率护栏（按 Q-RW-6 数值）：超限 fail-loud 中止；d) 本地 MLX 路线则护栏=本地算力/并发 | `tests/...（live lane）` | 一次性 live smoke + 护栏 fail-loud | RWC-T05 | owner 复核 + 护栏超限 fail-loud 用例 |
| RWC-06 | 手册 + closure | live 接入手册（key 准备/.env/切换）+ closure 据真实证据五态定级（verified/observed-OK/partial/未观察/deferred）| `docs/...` | 手册 + closure 如实定级 | RWC-T06 | 手册完整 + closure 不 overclaim |

---

## 5. Phase 详情

### 5.1 Phase 1 — 真实客户端

- **Phase 目标**：真实 LLM/embedding 替 mock；退避/分类 + 1024 守卫。
- **本 Phase 对应编号**：`RWC-01` / `RWC-02`
- **本 Phase 新增文件**：`packages/providers_*/.../{real_llm,real_embedder}.py`
- **具体功能预期**：
  1. 真实 `complete/complete_json`（厂商或本地 MLX）。
  2. 退避循环（MAX_RETRIES=3/BACKOFF=2）+ 错误分类（可重试 vs 不可重试）。
  3. HTTP 错误提取 + 分类异常。
  4. embedding 维度守卫 `!=1024` fail-loud。
  5. 写/查同 embedder（TR-3）。
  6. 不借 Cloudflare binding；接 RW-A 工厂槽。
- **对应测试台账项**：`RWC-T01` / `RWC-T02`
- **收口标准**：退避/分类/维度守卫单测 + 接工厂。
- **本 Phase 风险提醒**：维度漂移撞 schema——守卫 fail-loud；厂商请求体差异——按厂商重映射。

### 5.2 Phase 2 — 密钥管理 + 切换一致性

- **Phase 目标**：安全注入 + mock↔live 一致。
- **本 Phase 对应编号**：`RWC-03` / `RWC-04`
- **具体功能预期**：
  1. `.env`+构造注入；轮转封装实例内（不全局）。
  2. key 不入仓/日志/夹具。
  3. 缺 key live fail-loud、mock 不需 key。
  4. mock↔live 同 capstone 结构一致。
  5. 攻击向量用例：日志扫描无 key。
- **对应测试台账项**：`RWC-T03` / `RWC-T04`
- **收口标准**：缺 key fail-loud + 日志无 key + 切换一致。
- **本 Phase 风险提醒**：模块级全局 key 轮转反例（⛔）——构造注入规避。

### 5.3 Phase 3 — live smoke + 护栏 + 手册

- **Phase 目标**：owner 复核的一次性 live + 护栏 + closure。
- **本 Phase 对应编号**：`RWC-05` / `RWC-06`
- **具体功能预期**：
  1. live lane 默认 skip、owner-triggered。
  2. 一次性端到端 live smoke。
  3. 预算/速率护栏超限 fail-loud。
  4. 接入手册。
  5. closure 五态如实定级。
- **对应测试台账项**：`RWC-T05` / `RWC-T06`
- **收口标准**：owner 复核 + 护栏 fail-loud + closure 不 overclaim。
- **本 Phase 风险提醒**：计费失控——默认 mock + owner-triggered + 护栏。

---

## 6. 依赖的冻结设计决策（只读引用）

> **⚠️ 阻塞**：下表前三项**尚未冻结**（待后续 provider charter）。据模板纪律，本 AP 保持 `draft (blocked)`，不得标 executing/executed。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `Q-RW-2`（provider 具体：本地 MLX vs 外部厂商/模型）| **未冻结，待 provider charter** | RWC-01/02 实现形态 | **blocked**，回 charter |
| `Q-RW-6`（计费/速率/预算数值）| **未冻结，待 provider charter** | RWC-05 护栏阈值 | **blocked** |
| `Q-RW-7`（外部厂商 key 需求）| **未冻结，待 provider charter** | RWC-03 是否需外部 key | **blocked**（本地 MLX 则无需）|
| `Q-RW-1` 维度 1024 | `pre-charter-qna.md`（frozen）| RWC-02 守卫 1024 | — |
| `Q-RW-7` 框架（.env+构造注入）| `pre-charter-qna.md`（frozen）| RWC-03 注入方式 | — |
| `Q-RW-6` 框架（默认 mock+owner-triggered lane）| `pre-charter-qna.md`（frozen）| RWC-05 lane 策略 | — |
| RW-A/RW-B 完成 | 前置 AP | 真实实现挂工厂槽、替 MockLLM | RW-A/B 未完成则 blocked |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| C-1 | `legacy/.../vectorizer/embedder.ts:40-42,115-164` | 指数退避重试（MAX_RETRIES=3/BACKOFF=2）| RWC-01 退避循环 | 🔶 部分借（算法直采）| Python time.sleep 退避 |
| C-2 | `legacy/.../vectorizer/embedder.ts:73-79` | `isRetryableError` 错误分类 | RWC-01 分类 | 🔶 部分借（启发式直采）| 429/timeout→重试；401/422→否 |
| C-3 | `legacy/.../cloudflare_ai/ai_gateway.ts:128-182` | HTTP 错误提取 | RWC-01 错误处理 | 🔶 部分借 | →httpx；AI Gateway 路由不借 |
| C-4 | `legacy/.../providers/gemini.ts:61-86` | MODEL_CONFIG/参数默认 | RWC-01 请求体默认 | 🔶 部分借 | 按厂商重映射 |
| C-5 | `packages/rag_vectorizer/.../embedder.py:82` | 维度守卫 `!=DIMENSION` | RWC-02 守卫泛化 1024 | ✅ 复用 | RW-A 已迁 1024 |
| C-6 | `packages/rag_vectorizer/.../search.py:40-49` | 写/查 model 过滤 | RWC-02 写查同 embedder | ✅ 复用 | live 必保留（TR-3）|
| C-7 | `packages/providers_dedicated/.../service.py:114-151` | ProviderRegistry 工厂范式 | RWC-01/02 接工厂槽 | ✅ 复用 | RW-A 已建工厂 |
| C-8 | `packages/config/.../settings.py`（RW-A 扩后）| provider/key/model 字段 | RWC-03 key 注入 | ✅ 复用 | RW-A 已预留 key 字段 |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | Workers-AI/AI Gateway binding | Cloudflare 托管不可移；显式 httpx/本地 MLX |
| ⛔2 | API key 模块级闭包轮转（`gemini.ts:96-132`）| 全局可变难测；构造注入 + 实例内轮转（Q-RW-7）|
| ⛔3 | live 默认进 CI / 打外网 | 违 TR-5；live owner-triggered + 默认 skip |
| ⛔4 | 维度≠1024 静默写入 | 撞 schema CHECK；守卫 fail-loud（TR-2）|
| ⛔5 | key 入日志/仓/夹具 | 凭据泄漏（F6c⛔1）；不入日志 + 攻击向量用例 |
| ⛔6 | closure overclaim 为「语义已交付」| 假绿；据真实证据五态定级 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/real-wire/reference-anchor-by-opus.md`（轴 C）—— §7.1 摘录；完整 TR 过滤见真源 §5。可借皆**算法/协议**，Cloudflare binding 全 ⛔。
- **安全 / 信任边界（本 AP 最重）**：真实 key 注入是核心信任边界。威胁模型锚 = `Q-RW-7`（.env git-ignored + 构造注入 + key 不入日志）+ 反例 ⛔2/⛔5。**RWC-03 必须含攻击向量用例**（日志扫描无 key、缺 key fail-loud），否则不得标 executed。SSRF 边界沿用 `smind_common/net.py` 的 `assert_safe_url`（若外部 API 走 httpx）。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| RWC-T01 | 退避/重试/错误分类（注入假 429/timeout/401）| 短途 | unit | 🆕 新增 `test_real_llm_retry.py` | RWC-01 → 退避/分类 | `commit + test + run-time` |
| RWC-T02 | 真实 embedding 维度=1024；!=1024 fail-loud；写查同 embedder | 短途 | unit·契约 | 🆕 新增 `test_real_embedder_dim.py` | RWC-02 → 1024 守卫 | `commit + test + run-time` |
| RWC-T03 | 密钥：缺 key live fail-loud；日志无 key（攻击向量）| 短途 | unit·安全 | 🆕 新增 `test_key_injection.py` | RWC-03 → 安全注入 | `commit + test + run-time` |
| RWC-T04 | mock↔live 同 capstone 结构一致 | 集成 | e2e | 🔱 fork RW-B capstone + live 模式 | RWC-04 → 切换一致 | `commit + test + run-time` |
| RWC-T05 | live smoke 端到端（owner-triggered）+ 护栏超限 fail-loud | mega | live | 🆕 新增 `tests/live/test_live_smoke.py`（默认 skip）| RWC-05 → live + 护栏 | `commit + live PASS + owner 复核 + run-time(UTC)` |
| RWC-T06 | closure 据真实证据五态定级 | — | — | 文档复核 | RWC-06 → 不 overclaim | `closure 文档 + 证据链` |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| RW-B mock capstone | 🔱 fork → +live 模式 | + live 结构一致断言 | RW-B 后存在 |
| `smind_common/net.py` SSRF guard | ♻️ 沿用 | 0 改动（外部 API httpx 时）| 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR（mock，注入假错误）| unit·契约·安全 | 开发中 |
| 集成 | mock↔live 一致（live 部分 owner-triggered）| e2e | Phase 2 收口 |
| mega | live smoke（owner-triggered，默认 skip）| live | **本 AP 收口（owner 复核）** |

### 8.4 测试缺口

- 默认 CI **不覆盖 live**（理由：TR-5 不打外网）→ live 在 owner-triggered lane；**不在默认 CI 假装覆盖**。
- 不覆盖多 provider/多模型对比（理由：单厂商起步）→ 后续轮。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ live smoke 带四元组 + owner 复核；degraded 带机器可读 reason。
- 安全项（key）必须含攻击向量用例（日志无 key、缺 key fail-loud），不得只测 happy-path。
- closure 据真实证据五态定级，不 overclaim 为「RAG 语义已交付」。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| provider 口径未冻结 | Q-RW-2/6/7 待 charter | high（阻塞）| 本 AP draft(blocked)，待 charter |
| 维度漂移 | 真实 embedding≠1024 | high | 守卫 fail-loud（TR-2）|
| 密钥泄漏 | key 入仓/日志 | high | .env git-ignored + 构造注入 + 攻击向量用例 |
| 计费失控 | live 误打 API | high | 默认 mock + owner-triggered + 护栏 |
| 本地 MLX 装不上 | torch/MLX 依赖 | medium | G-RW-1 备选（外部 API / 保持 mock 标 degraded）|

### 9.2 约束与前提

- **技术前提**：RW-A/RW-B 完成；provider charter 已冻结 Q-RW-2/6/7。
- **运行时前提**：默认 mock 不打外网；live 在 owner 机器（本地 MLX 则 macOS）。
- **组织协作前提**：owner 提供 key/预算/速率（Q-RW-6/7）。
- **上线 / 合并前提**：live smoke owner 复核 + 默认零外网零计费可跑 + 守卫 fail-loud。

### 9.3 文档同步要求

- 需新增：live 接入手册（key 准备/.env/切换）。
- 需同步：closure（据真实证据定级）。

### 9.4 完成后的预期状态（解锁后）

1. 真实 LLM 处理 + 真实 embedding（1024）检索，语义真实。
2. 密钥安全注入（不入仓/日志），mock↔live 切换一致。
3. live smoke owner 复核通过，默认 mock 零外网零计费可跑。
4. 接入手册 + closure 据真实证据五态定级。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸（解锁后）

1. 退避/分类 + 1024 守卫（`RWC-T01/T02`）。
2. 密钥安全注入 + 攻击向量用例（`RWC-T03`）。
3. mock↔live 切换一致（`RWC-T04`）。
4. live smoke owner 复核 + 护栏 fail-loud（`RWC-T05`）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| 退避/分类 | RWC-01 | RWC-T01 | — | blocked |
| 1024 守卫 | RWC-02 | RWC-T02 | — | blocked |
| 安全注入 | RWC-03 | RWC-T03 | — | blocked |
| 切换一致 | RWC-04 | RWC-T04 | — | blocked |
| live + 护栏 | RWC-05 | RWC-T05 | — | blocked |
| closure 定级 | RWC-06 | RWC-T06 | — | blocked |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | 真实 LLM/embedding 替 mock + 密钥 + live smoke |
| 测试 | §8 全 PASS（live smoke owner 复核 + 安全攻击向量）|
| 文档 | live 手册 + closure 五态定级 |
| 风险收敛 | 维度守卫 + key 不泄漏 + 护栏 fail-loud |
| 可交付性 | 语义真实 RAG 可用 |

### 10.4 NOT-成功识别

> **本 AP 当前=blocked**：provider charter 未冻结前不得开工。解锁后任一退出硬闸 `degraded/未观察` ⇒ 不得标 executed；live 质量据真实证据定级，不 overclaim。

---

## 11. 执行日志回填（executed — scaffolding）

> 文档状态：`executed（scaffolding）`（2026-06-01，commit `fec0bb3`）。按 owner reframe，本轮交付**可被真实接线的脚手架 + 路由 + 占位槽**；真实 MLX 推理与 live smoke **延后至 provider charter**（且本离线 Linux 环境不可跑）。全量 274 passed + 1 xfailed；门禁 51 文件 0 弱。

**工作记录（逐项）**

- **RWC-01 退避/重试 + 错误分类**：`provider_runtime/retry.py` — `retry_with_backoff`（指数退避 MAX_RETRIES=3/INITIAL_DELAY=1s/BACKOFF=2，借 `embedder.ts:40-164`；`sleep` 可注入测试零等待）+ `is_retryable_error`（借 `:73`，429/5xx/timeout/connection 重试；401/403/422 不重试；**默认保守不重试**）。
- **RWC-01/02 真实 provider 占位槽**：`provider_runtime/real_provider.py` — `RealMLXLLMProvider`/`RealMLXEmbedder`（构造**成功**→工厂路由已接；`complete`/`embed` 抛 `ProviderDeferredError`（reason=`provider_adapter_deferred_Q-RW-2`）fail-loud）；embedder 维度锁 1024。
- **RWC-03 密钥管理**：构造注入 `api_keys`（实例内持有，**非**模块级全局轮转——规避 `gemini.ts:96-132` ⛔ 反例）；`redact_secret` + `__repr__` 脱敏（原始 key 不入 repr/日志，Q-RW-7/TR-5）。工厂 `mlx` 槽经 `Settings.llm_api_key/llm_model` 构造注入。
- **RWC-04 mock↔live 路由一致性**：`_FakeLiveProvider` 替身（真实 MLX 离线不可跑）证 `structurize_via_llm` 在 mock 与 live-替身下**结构/契约一致**（键集 + section 形状），文本质量不比较。
- **工厂 mlx 槽**：`make_llm/make_embedder` 的 `mlx` 分支由「构造即 raise」改为「构造返回占位（路由通）+ 调用时 fail-loud」；外部厂商（openai/anthropic/gemini）仍构造即 deferred（非本地 MLX 方向）。
- **测试**：`tests/unit/test_rw_c_live_wiring.py` 9 项（分类/退避恢复/不可重试立即抛/耗尽抛/占位 defer/维度 1024/key 脱敏/工厂注入不泄漏/mock↔live 结构一致）。同步把 RW-A 的 mlx 测改为「构造 ok + 调用 defer」。

- **Phase 偏差 / scope 调整**：按 owner reframe，RW-C 本轮范围由「真实 live 客户端」收窄为「**脚手架 + 占位槽 + 路由**」。RWC-05（live smoke owner-triggered lane）/ RWC-06（live 接入手册 + live closure）/ 真实 MLX `complete`/`embed` 推理 —— **deferred 至 provider charter**，且本离线 Linux 环境无 MLX、不可跑。
- **阻塞与处理**：真实 MLX 推理在本环境不可验（无 MLX/Apple Silicon）→ 占位 fail-loud + closure 据实标 `未观察(本环境不可跑)`，不谎报 verified。
- **测试发现**：274 passed（+9，从 265 基线）+ 1 xfailed；无 import 循环；占位 provider 满足 `LLMProvider` 协议（isinstance）。
- **后续 handoff**：provider charter — 实装 `RealMLXLLMProvider.complete`/`RealMLXEmbedder.embed`（真实 MLX 推理）→ 占位 fail-loud 即转真实；retry/分类/key 注入/路由脚手架已就绪可直接复用；live smoke 在 owner macOS 跑。
