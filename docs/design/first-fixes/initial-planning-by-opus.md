# first-fixes —— Final Execution Plan（by Opus 4.8）

> **stage**：`final`
> **作者**：Opus 4.8（panel / 跨模型 handoff：none）
> **时间**：2026-05-31
> **文档性质（自宣告 role）**：`final` = "**取代 initial + proposed 两份**，作 action-plan 制作前唯一执行基线；不再在前两份上增量"。本态由**冻结 QnA**（`owner-gated-qna.md`，Q1–Q7 全部裁决）关闭全部 OPEN gate。
> **[final] 输入权威次序**：`冻结 QnA（owner-gated-qna.md）> HEAD 代码实测（part-cr-1~8 锚点）> design artifacts（refactor/*）`。
> **reference-anchor 说明**：本链 reference-anchor 已由 `part-cr-1.md ~ part-cr-8.md` 八簇审查提前完成（每 blocker 带 file:line + legacy 对照 + 实测）；§6 锚定直接引用 CR 报告。
> 本文把八簇审查发现的全部 blocker 按**修复内聚性 + 依赖序**分簇为 F1–F7 七 phase，并由冻结 QnA 定档范围，作为下游 action-plan 的 1:1 派生基线（§10.A）。
> **上游权威输入**：
> - `docs/eval/first-code-review-plan/index.md` — 全局发现登记表（约 28 个去重 blocker，G-CRx-xx 编号）
> - `docs/eval/first-code-review-plan/part-cr-1.md ~ part-cr-8.md` — 八簇逐条审查报告（含 file:line、实测证据、legacy 对照）
> - `docs/refactor/index.md` / `core.sql` / `vec.sql` / `database.md` — 设计 SSOT
> - `legacy-family/` — 原 CF-worker 行为基线（只读校准）
> **phase 命名 & 工作项 ID 方案**：phase = `F1..F7`；工作项 = `F<n>-NN`（跨态稳定）；引用审查发现用原 `G-CRx-xx`。
> **裁定动词 rubric（§2.A）**：`纳入 / refine / 不纳入`
> **文档状态**：`frozen`（stage=final；7 gate 由 `owner-gated-qna.md` 全部 CLOSED）
> **下游消费者**：本文 §6 的 7 个 phase 簇 1:1 派生下游 action-plan（见 §10.A，F6 拆 3 份，共 9 份）。

---

## 0. TL;DR

- **核心论点**：八簇审查的结论是"管道接得上、语义为空、测试无法证明正确性"。修复不能逐条打补丁，而要按**根因依赖**推进：先立**时间与事务基座**（单点根因，波及 lease/restart/reap），再修**内核恢复与一次性语义**与**适配层安全/数据完整性**，然后注入**向量真实性**，再**执行器去桩**恢复真实业务能力，最后（贯穿始终地）**重建有意义测试并给 closure 重新定级**。每个 phase 的退出判据是"一条修复前红、修复后绿的有意义测试"，而非 `status==200`。
- **一句话**：先修根因基座、再修可靠性与安全、后补真实能力，全程以"先红后绿"的有意义测试驱动，杜绝再次假绿。
- **[proposed] 本态相对 initial 做了什么**：reference-anchor 由 CR 报告预完成，故不重做锚定；仅做 4 处 eval-driven 精化（见 §2.B）——其中最重要的是**纠正 F1-04 事务模式被低估**：`isolation_level=None` 非 drop-in，强制要求把所有内核多写函数包进显式 `BEGIN IMMEDIATE...COMMIT`，规模 S→M、与 F3 紧耦合。
- **[final] 本态相对 proposed 做了什么**：冻结 QnA（Q1–Q7 全部裁决=同意 Opus 推荐）关闭全部 7 个 OPEN gate；据此把 5 个 `refine` 工作项**定档具体范围**（F5=degraded+本地 1536 维 embedding；F6=增量 file+url+chinatax+基础结构化、PDF/浏览器/多 provider/scatter 显式 degraded；F3-05=recovery 模式；F6-07=API key 纳入；密码兼容删除）；§7.A→§7.B gate-closure；新增 §8 capstone+evidence pack、§10.A 派生图、§13 冻结槽。

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| `index.md` 全局发现登记表 | eval | 28 个去重 blocker + 严重度 + 位置 | `docs/eval/first-code-review-plan/index.md` |
| `part-cr-1.md` | eval | 时间格式根因、contracts 死代码 | G-CR1-01~03 |
| `part-cr-2.md` | eval | 连接泄漏、事务模式、表覆盖 | G-CR2-01~03 |
| `part-cr-3.md` | eval | 路径遍历、vec0 假绿、rowid 破坏 | G-CR3-01~14 |
| `part-cr-4.md` | eval | reap 死代码、双重执行、restart 失效 | G-CR4-01~13 |
| `part-cr-5.md` | eval | api_key 缺失、路径遍历源头 | G-CR5-01~05 |
| `part-cr-6.md` | eval | clean 执行链全桩、action registry 丢失 | G-CR6-01~05 |
| `part-cr-7.md` | eval | embedder 伪向量、structurize/construct 盲点 | G-CR7-01~07 |
| `part-cr-8.md` | eval | 测试结构性假绿、端到端语义空、收口总账 | G-CR8-01~06 + 附录 |
| `legacy-family/` | anchor | 原 CF-worker 行为基线 | 各 worker 源码 |

- **纪律继承**：沿用审查期的"事实 vs 推断"区分、legacy 校准、owner 4 项口径（stub 即盲点 / 逐 action parity / 并行分派 / 测试查假绿）。
- **[仅 initial] 借用骨架**：无既有 final 可借，按 `eval-planning.md` 骨架 initial 态填充。

---

## 2. 辨证审核（裁定上一阶段）★ 承重段

> initial 态：对"原始 evals（= 八簇审查 blocker）"做整合裁定，分配到内聚 phase。无 Δ 表。

### 2.A 对审查 blocker 的整合裁定（全部 blocker → phase 分簇）

> 口径：`纳入`=本轮修复；`refine`=纳入但需先经 owner gate 收敛范围；`不纳入`=延后（见 §3.2）。**所有 critical/high blocker 均纳入。**

| 来源项（blocker） | 严重度 | 整合裁定 | 落到 phase | 备注 |
|------|------|------|------|------|
| G-CR1-01 时间格式缺秒（根因） | critical | 纳入 | **F1** | 单点根因,修一处解 G-CR4-02/04 |
| G-CR1-02 common.utc_now_iso 不符 SSOT | high | 纳入 | **F1** | 统一为 `...SS.mmmZ` |
| G-CR1-03 时间/ID 双源实现 | high | 纳入 | **F1** | 确立单一 SSOT,内核复用 common |
| G-CR2-02 engine 未设 isolation_level | high | 纳入 | **F1** | BEGIN IMMEDIATE 前提,与时间同属基座 |
| G-CR4-R15 clean 用 CURRENT_TIMESTAMP（第三格式） | low | 纳入 | **F1** | 时间格式统一顺带收口 |
| G-CR2-01 API/CLI 连接泄漏 | high | 纳入 | **F2** | generator 依赖 + close |
| G-CR8-06 API 无 lifespan/CORS/异常/healthz | medium | 纳入 | **F2** | 装配完整性 |
| G-CR4-01 reap 死代码 | critical | 纳入 | **F3** | 依赖 F1 时间修复才命中 |
| G-CR4-03 / G-CR6-03 / G-CR7-06 执行器自提交→双重执行 | critical | 纳入 | **F3** | 终态归属内核 + 幂等键 + 检查返回值 |
| G-CR4-04 restart available_at 畸形 | high | 纳入 | **F3** | F1 修根因 + restart 改 SQL strftime |
| G-CR4-05 restart 总从 clean 重跑/mode 死参 | high | refine | **F3** | gate G-F-6:精细重启范围 |
| G-CR3-01 / G-CR5-02 路径遍历 | critical | 纳入 | **F4** | store 边界校验 + ingestion basename |
| G-CR3-04 rowid 重号静默删除审计记录 | critical | 纳入 | **F4** | rowid 单调不复用 |
| G-CR3-03 / G-CR7-02 孤儿 rowid 累积 | critical | 纳入 | **F4** | upsert 复用 rowid/幂等 |
| G-CR3-05 purge 不清对象 | high | 纳入 | **F4** | store.delete + purge 接线 |
| G-CR3-09 软/硬删不一致 | high | 纳入 | **F4** | 统一删除策略 |
| G-CR7-01 embedder 伪向量 | critical | refine | **F5** | gate G-F-2:embedding provider 选型 |
| G-CR3-02 vec0 静默退化 | critical | refine | **F5** | gate G-F-1:真实加载 or 显式 degraded |
| G-CR3-10 / G-CR7-R8 search 无 namespace/model 过滤 | high | 纳入 | **F5** | search 增过滤参数 |
| G-CR6-01 universal cleaner 全桩 | critical | refine | **F6** | gate G-F-3:去桩范围 |
| G-CR6-02 dedicated provider 硬编码桩 | critical | refine | **F6** | gate G-F-3 |
| G-CR6-04 action registry 丢失 | high | 纳入 | **F6** | registry + 分派 |
| G-CR6-05 finalizer scatter/child files 缺 | high | refine | **F6** | gate G-F-3:多文档源是否支持 |
| G-CR7-03 structurize 朴素分段（缺 67%） | high | refine | **F6** | gate G-F-3 |
| G-CR7-04 construct 缺 summary/layer-json（缺 55%） | high | refine | **F6** | gate G-F-3 |
| G-CR7-05 无独立 rag:vectorize step | high | 纳入 | **F6** | 拆出独立 step（与 F3 内核语义一致） |
| G-CR5-01 团队 API key 认证缺失 | high | refine | **F6** | gate G-F-4:是否纳入本轮 |
| G-CR8-01 测试结构性假绿 | critical | 纳入 | **F7** | 重建有意义测试 |
| G-CR8-02 夹具掩盖（手写时间绕过 bug） | critical | 纳入 | **F7** | 去掩盖 + 走真实写入路径 |
| G-CR8-05 closure 陈旧/复制 PASS | high | 纳入 | **F7** | closure 重新定级 |
| G-CR8-R8 测试固化桩输出 | medium | 纳入 | **F7** | 接真实实现时同步重写 |

> **非 blocker 的 medium/low followup**（G-CR1-04/05、G-CR2-04/05/06、G-CR3-06/07/08/11~14、G-CR4-06~13、G-CR5-03/04/05、G-CR6-07/08、G-CR7-09~11 等）：原则上**就近捆绑**到同主题 phase 一并修（如 G-CR4-07 退避接线 / G-CR4-08 错误分类 → F3；G-CR3-06 原子写 / G-CR3-11 错误处理 → F4），其余无内聚归属者延后（§3.2）。

### 2.B Δ 审核 vs initial-planning（eval-driven 精化，4 项）

> 本态唯一改动来源。reference-anchor 既由 CR 报告完成，proposed 仅修正"单簇审查看不出、跨簇锚定才浮现"的归属/规模问题。

| item-ID | 裁定 | 重分配 phase | 理由 / 新证据（跨 CR 锚） |
|---------|------|--------------|----------------------------|
| F1-04 事务模式 | **REFRAME** | F1（耦合 F3） | CR-2 Face A 建议 `isolation_level=None`，但 CR-4 Face A 证明 happy-path 靠"隐式事务 + 末尾 commit"续命。改 autocommit 后多写函数若无显式 `BEGIN` 则每写即提交、丧失原子性（末尾 commit 成 no-op）。故 F1-04 必须**附带审计并包裹 workflow_core 全部多写 helper（claim/succeed/fail/reap/restart/purge）为显式 `BEGIN IMMEDIATE...COMMIT`**。规模 S→M，风险 med→high。 |
| G-CR4-09 重复事件写入器 | **NEW** | F3（联动 F1） | initial §2.A 漏收。`graph.write_workflow_event`（导出但死代码，commit+正确时间）vs `events.append_workflow_event`（内核实用，无 commit + 畸形 created_at）。删 graph、统一 events 并**去掉显式 created_at 交 DDL DEFAULT**（顺带消除该处时间 bug，与 F1 同源）。 |
| G-CR2-03 余项（非 api_keys 的 3 张零访问表） | **NEW** | workflow_step_links→F3/§3.2；prompt_versions/provider_configs→F6 | initial 只把 api_keys 放进 F6-07，漏了另 3 张。`prompt_versions`/`provider_configs` 是 F6 真实 cleaner/structurizer 所需的 prompt/provider 配置载体，归 F6。`workflow_step_links`（DAG 边表）当前 graph 只写 events 不写 links，需在 F3 明确"接线 or 显式延后 + 理由"。 |
| 执行器契约（F3↔F6 桥接） | **NEW（threaded）** | §4 红线 + F3-02/F6 | F3-02 把终态写入归还内核后，执行器契约变为"只产出结果对象、不写终态/不 commit"。F6 的全部真实执行器必须建在此契约上 → 升为贯穿红线（§4）与显式接口交付物，否则 F6 会复刻 G-CR4-03 的撕裂。 |

- **本态核心转向（一句话）**：从"逐 blocker 分簇"精化为"**承认 F1-04 事务模式是 F1↔F3 的耦合枢纽、并把执行器契约提为 F3→F6 的显式桥**"——其余结构不变。

### 2.C [final] critique vs proposed-planning（冻结 QnA 定档）

> 仅记录"冻结 QnA 对 proposed 的范围裁定"，不新增决策。

| item-ID | 裁定 | 处置 | 依据（冻结 Q） |
|---------|------|------|----------------|
| F5-02 vec0 | **RESIZE↓** | 定档 degraded（暴力 cosine + 强制告警 + `VectorIndex` 接口）；真实 vec0 移出本轮 | [Q1] |
| F5-01 embedding | **CONFIRM** | 本地小模型 + `Embedder` adapter；**强约束 模型维度=1536**（免触 schema/迁移） | [Q2] |
| F6-02/03/04/05/08 去桩 | **RESIZE↓** | 定档增量:file(文本)+url(HTML)+基础 structurize/construct+1 provider(chinatax);PDF/浏览器/多 provider/scatter **显式 degraded** | [Q3] |
| F3-05 restart | **CONFIRM** | recovery 模式(按 current_stage/失败 step 锚点);force/kickstart 延后;**前置必修 F3-04 available_at** | [Q4] |
| F6-07 API key | **CONFIRM** | 本轮纳入(校验中间件 + create_api_key + team 归属) | [Q5] |
| 密码兼容（§3.2 O3） | **CORRECT** | 从"延后"改为**本轮删除**不成立的 legacy 兼容声明,统一 PBKDF2(无存量用户) | [Q6] |
| 先红后绿(§4 红线) | **CONFIRM** | 升为全 phase 铁律 + CI 断言强度门禁 | [Q7] |
| 其余 F1/F2/F3/F4/F7 | **CONFIRM** | proposed 结构与规模不变 | — |

---

## 3. 范围与非范围（In/Out-Scope）

### 3.1 In-Scope
- **[S1]** F1–F7 七个 phase 覆盖的全部 critical/high blocker（§2.A `纳入`/`refine`）。
- **[S2]** 每个 phase 配套的"先红后绿"有意义测试（§8）—— 这是 phase 退出的硬前提。
- **[S3]** 就近捆绑的同主题 medium followup。
- **[S4]** closure 文档的重新定级（撤销基于假绿的 ✅）。

### 3.2 Out-of-Scope / 延后
- **[O1]** `contracts` 补全为真契约 SSOT（G-CR1-04）—— 当前是死代码,**先删或降级标注**,真正契约化延后;重评条件:F6 业务去桩后契约面稳定。
- **[O2]** 迁移版本化机制（G-CR2-06/G-CR3-14）—— 当前单条建表够用;重评条件:首次需要 schema 演进时。
- **[O3]** ~~legacy 密码兼容~~ **→ 改为 In-Scope**（[Q6] 裁定:无存量用户,**本轮删除**不成立的兼容声明、统一 PBKDF2）。作为 F6-07（认证面）的就近小项 F6-11。
- **[O4]** 5 个缺失 legacy RPC 中的非认证项（reset_password/update_workflow/static delete，G-CR5-04）—— 按产品需要补;重评条件:产品明确需求。
- **[O5]** repository 抽象统一覆盖 23 表（G-CR2-04）—— 架构取舍,先文档化"仅核心表走 repository";重评条件:F6 后统一重构窗口。

> **范围模态**：initial = 提案/条件式。`refine` 项的最终范围由 §7.A gate 在 proposed 态收敛。

---

## 4. 跨阶段贯穿主题（threaded themes）

- **技术路线红线**：
  1. **单一时间 SSOT** —— 全系统时间只经一个函数生成,格式 `YYYY-MM-DDTHH:MM:SS.mmmZ`,与 SQLite `strftime('%Y-%m-%dT%H:%M:%fZ')` 严格可比;禁止 `now_iso` 畸形格式、`CURRENT_TIMESTAMP`、`isoformat()+00:00` 三种变体并存。
  2. **终态写入单一归属 + 执行器契约** —— step 终态 + 下游派生 + run 推进只由内核 claim 函数（succeed/fail）在确认 claim 仍 active 的同一事务内完成;执行器只产出结果、不写终态、不 commit。**执行器契约**（F3-02 定义、F6 全部真实执行器遵守）:`execute(step, deps) -> ExecutorResult`（产物 + 下游意图 + 错误码），由内核统一落库。所有副作用带幂等键。
  3. **事务原子性显式化** —— 采用 `isolation_level=None`（autocommit）后,所有多写操作**必须**显式 `BEGIN IMMEDIATE...COMMIT` 包裹;禁止裸多写依赖隐式事务。这是 F1-04 与 F3 共同的硬约束。
  3. **适配层边界强制** —— ObjectStore/VectorStore 是安全边界,object_key 规范化、rowid 一一对应、维度校验在适配层内强制,不依赖调用方自律。
- **治理冻结面**：
  - **先红后绿铁律**：每个 blocker 的修复必须先提交一条"在当前 HEAD 上 FAIL、修复后 PASS"的回归测试,证明它真的修了且不会回归。
  - **closure 冻结**：在 F7 测试重建完成前,**任何 closure 不得重新标 ✅ PASS**;现有 P3–P7 的 `14 passed` 证据视为无效。
  - **去掩盖**：F7 前禁止新增任何"手写正确数据绕过被测路径"的夹具。
- **meaningful-test inventory（测试原语,F7 早期产出供各 phase 复用）**：
  - 冻结时钟 fixture（freeze/advance clock）→ 用于 F1 时间、F3 lease/reap。
  - 并发/竞态 runner（双 worker + 强制租约过期）→ 用于 F3 双重执行。
  - 恶意路径 fixtures（`../`、绝对路径、越界 key）→ 用于 F4 路径遍历。
  - 向量真实性断言（相关 chunk 排序靠前 + 显著分差）→ 用于 F5 embedding。
  - 真实样本输入（含 HTML/噪声/PDF 的 clean 输入）→ 用于 F6 去桩。

---

## 5. DAG（关键路径 + 并行窗）

```text
F1 时间与事务基座 ──┬──▶ F3 内核恢复与一次性语义 ──┐
                    │                                 ├──▶ F6 执行器去桩与能力补全 ──▶ F7 测试整合 + closure 重定级
F2 连接与装配 ──────┘（与 F1 并行,互不抢带宽）       │
F4 适配层安全与完整性 ──────▶ F5 向量真实性与检索 ────┘

F7（测试原语)：早期 lane 与 F1 并行产出 fixture 原语；消费 lane 贯穿各 phase（先红后绿）；整合 lane 收尾。

关键路径：F1 → F3 → F6 → F7（整合）
并行窗：F2 全程可与 F1/F3 并行（装配层,不碰内核状态机）；F4→F5 可与 F3 并行（适配层 vs 内核,不同 substrate）。
强耦合：F1-04（autocommit + 多写包 BEGIN）与 F3（内核多写函数）共享同一批 workflow_core 函数 —— 建议 F1-04 的"包裹显式事务"与 F3-02 的"终态归属重构"在同一改动窗口推进,避免两次触碰同组函数。
```

---

## 6. 逐 phase 工作台账

> initial 态：first-cut（初判规模/风险,模块待 reference-anchor 期 pin）。规模 XS≤0.5d / S≈1d / M≈2-3d / L≈1w+。

### 6.1 `F1 · 时间与事务基座`（keystone）

**[initial] first-cut**

| 编号 | 工作项 | 涉及模块（初判） | 规模 | 风险 |
|------|--------|------------------|------|------|
| F1-01 | 统一时间 SSOT:`smind_common.time` 输出 `...SS.mmmZ`,与 SQL strftime 可比 | `packages/common/.../time.py` | S | low |
| F1-02 | 删除 `workflow_core/_utils.now_iso/add_seconds_iso` 畸形实现,内核复用 common | `workflow_core/_utils.py` + 全调用点 | S | med（调用点多） |
| F1-03 | 清除 `CURRENT_TIMESTAMP` 等第三格式,clean/rag 时间走 SSOT/DDL DEFAULT | `workflow_clean/service.py` 等 | XS | low |
| F1-04 | engine `connect()` 设 `isolation_level=None`（autocommit），**并审计/包裹 workflow_core 全部多写 helper（claim/succeed/fail/reap/restart/purge）为显式 `BEGIN IMMEDIATE...COMMIT`** —— 否则 autocommit 下多写丧失原子性（末尾 commit 成 no-op） | `storage_sqlite/engine.py` + `workflow_core/*.py` 全部多写函数 | **M** | **high**（事务语义全局变更,与 F3 紧耦合,需逐函数回归） |
| F1-05 | 先红后绿:时间 round-trip + 秒位正则 + 跨 PY/SQL 比较一致性 + **多写函数原子性测试（中途失败整体回滚）** | `tests/unit/` | S | low |

### 6.2 `F2 · 连接与装配可靠性`（与 F1 并行）

| 编号 | 工作项 | 涉及模块 | 规模 | 风险 |
|------|--------|----------|------|------|
| F2-01 | `deps.get_core_conn/get_vec_conn` 改 generator 依赖（yield+finally close） | `apps/api/deps.py` | XS | low |
| F2-02 | CLI `_service()` 连接用 contextlib.closing | `apps/cli/main.py` | XS | low |
| F2-03 | API 加 lifespan（启动迁移+连接自检）、CORS、全局异常处理；`/healthz` 真探测 | `apps/api/main.py` | S | low |
| F2-04 | 先红后绿:请求级连接关闭断言（无 fd 泄漏）+ 业务异常映射 4xx 而非 500 | `tests/integration/` | S | low |

### 6.3 `F3 · 内核恢复与一次性语义`（依赖 F1）

| 编号 | 工作项 | 涉及模块 | 规模 | 风险 |
|------|--------|----------|------|------|
| F3-01 | worker `_run_once` 接线 `reap_expired_claims`（F1 后才命中） | `apps/worker/main.py` | XS | low |
| F3-02 | 终态归属内核 + **定义执行器契约**（`execute(step,deps)->ExecutorResult`）:执行器不写终态/下游/run/不 commit,由 succeed/fail 在确认 claim active 的同一显式事务内统一落库。**此契约是 F6 全部真实执行器的建造基准** | `workflow_clean/rag/service.py` + `workflow_core/retry.py` + 新契约模块 | L | high（重构执行器↔内核边界,F6 依赖） |
| F3-03 | 副作用幂等键（artifact/下游 step 用确定性 key,非 uuid4）；main 检查 succeed/fail 返回值 | `workflow_clean/rag` + `worker/main.py` | M | med |
| F3-04 | restart available_at 改 SQL strftime（F1 根因 + 局部双保险） | `workflow_core/restart.py` | XS | low |
| F3-05 | restart 精细重启（按 mode/失败 step 锚点）★ refine,待 gate G-F-6 | `workflow_core/restart.py` | M | med |
| F3-06 | 就近捆绑:retry 退避读 schema 列 + 指数（G-CR4-07）、错误分类透传（G-CR4-08） | `workflow_core/retry.py` | S | low |
| F3-07 | **删重复事件写入器（G-CR4-09）**:删 `graph.write_workflow_event`（死代码），统一 `events.append_workflow_event` 并去掉显式 `created_at`（交 DDL DEFAULT，消除该处时间 bug，与 F1 同源） | `workflow_core/{graph,events}.py` + `__init__.py` | S | low |
| F3-08 | `workflow_step_links`（DAG 边表，G-CR2-03 余项）:接线 step 链边写入 **或** 显式延后并记理由（当前 graph 只写 events 不写 links） | `workflow_core/graph.py` | S | med |
| F3-09 | 先红后绿:并发 harness —— claim→强制过期→reap→第二 worker 执行→断言 artifact/chunk **无重复** | `tests/integration/` + 并发原语 | M | med |

### 6.4 `F4 · 适配层安全与数据完整性`（与 F3 并行）

| 编号 | 工作项 | 涉及模块 | 规模 | 风险 |
|------|--------|----------|------|------|
| F4-01 | ObjectStore key 边界校验:拒绝绝对路径/`..`,resolve 后断言 in-root | `storage_objects/filesystem_store.py` | S | low |
| F4-02 | ingestion 对 filename basename 收口（纵深防御） | `ingestion/service.py` | XS | low |
| F4-03 | VectorStore rowid 单调不复用 + upsert 复用现有 rowid（消除孤儿 + 重号删除） | `vector_sqlite_vec/store.py` | M | med（数据完整性核心） |
| F4-04 | 软/硬删统一策略,保留审计可追溯 | `vector_sqlite_vec/store.py` | S | med |
| F4-05 | ObjectStore.delete + purge 接线删对象（合规清退） | `storage_objects` + `workflow_core/purge.py` | S | low |
| F4-06 | 就近捆绑:put_text 原子写 temp+replace（G-CR3-06）、get_text 错误处理（G-CR3-11） | `storage_objects` | XS | low |
| F4-07 | 先红后绿:路径遍历拒绝测试 + rowid 不变量测试（重复 upsert 0 孤儿 / 软删后新增不丢） | `tests/unit` + `tests/integration` | S | low |

### 6.5 `F5 · 向量真实性与检索`（依赖 F4 rowid）★ 范围由 [Q1][Q2] 定档

**[final] action-plan 绑定**

| 编号 | lane | 工作项（已定档） | 复用 | 退出(exit) | evidence | 来源 |
|------|------|------------------|------|------------|----------|------|
| F5-01 | embed | `Embedder` adapter 接口 + **本地小模型**（维度=1536，免触 schema）替换 SHA-256 伪向量 | 🆕 | 真实 query 的目标 chunk 排第一且分差显著；伪向量函数删除/标测试桩 | F5-04 语义相关性测试通过 | [Q2] / G-CR7-01 |
| F5-02 | vecidx | **degraded 定档**:保留暴力 cosine,但 `_fallback_vec_sql` 路径 `logger.warning` fail-loud + 抽象 `VectorIndex` 接口（真实 vec0 移出本轮） | ♻️ | 退化路径有强制告警;接口可被未来 vec0 实现替换;closure 标 degraded | 退化告警断言 + 接口契约测试 | [Q1] / G-CR3-02 |
| F5-03 | search | search 增 `namespace_id`/`embedding_model` 过滤,`distance_metric` 生效 | 🆕 | 跨 namespace/model 向量不混算;单元测试覆盖过滤 | filter 单测 | G-CR3-10 |
| F5-04 | test | 先红后绿:向量真实性（相关 chunk 排第一+分差）+ degraded 告警断言（取代"vec0 虚表断言",因本轮 degraded） | ✅ | 修复前红、修复后绿 | regression | [Q7] |

> **[Q1/Q2] 定档差异**:F5 由"接真实 vec0 + 真实 embedding(high/M)"收窄为"degraded 向量索引 + 本地 1536 维 embedding";真实 vec0 与外部 API embedding 移出本轮(记入下一轮技术债)。

### 6.6 `F6 · 执行器去桩与能力补全`（依赖 F1-F5 substrate,最大 phase）★ 范围由 [Q3][Q5][Q6] 定档为**增量**

**[final] action-plan 绑定**（去桩范围 = file+url+chinatax+基础结构化；其余显式 degraded）

| 编号 | lane | 工作项（已定档） | 退出(exit) | evidence | 来源 |
|------|------|------------------|------------|----------|------|
| F6-01 | registry | action registry + executor 分派抽象（替换 if/else），执行器遵守 F3-02 契约 | 新 action 可注册;无 if/else 硬选 | registry 单测 | G-CR6-04 |
| F6-02 | clean | universal cleaner:**实现 `htmlCrawl`（url HTML 抓取+清洗）**;`browserFetch/browserPDF` **显式 degraded**（skip/xfail + 声明） | url→干净正文(去标签/保正文);PDF/浏览器明确不支持 | 真实 HTML 样本测试 | [Q3] / G-CR6-01 |
| F6-03 | provider | dedicated provider **registry + chinatax 真实 ETL**（真发请求/解析）;多 provider degraded | chinatax 真实抓取解析;registry 可扩展 | chinatax 集成测试(可 mock 网络) | [Q3] / G-CR6-02 |
| F6-04 | rag | structurize **真实结构化**（schema 化输出,非朴素分段;不追 legacy 全 AI 策略） | 输出结构化 schema 非裸 paragraphs | structurize 单测 | [Q3] / G-CR7-03 |
| F6-05 | rag | construct **chunk + summary 双通道**（layer-json 视 [Q3] 增量;若超范围则 degraded 声明） | chunk + summary 产出;不止 chunk_text | construct 单测 | [Q3] / G-CR7-04 |
| F6-06 | rag | 拆出独立 `rag:vectorize` step（与 F3 "每 step 可 claim/重试/重启" 一致） | vectorize 是独立可重试 step | step 链测试 | G-CR7-05 |
| F6-07 | auth | 团队 API key 认证（校验中间件 + create_api_key + team 归属） | API key 可创建并通过校验 | auth 集成测试 | [Q5] / G-CR5-01 |
| F6-08 | clean | finalizer scatter/child files（多文档源）**显式 degraded**（[Q3] 不支持多文档源） | 单文档源正常;多文档源明确不支持 | degraded 声明 | [Q3] / G-CR6-05 |
| F6-09 | config | `prompt_versions`/`provider_configs` 接线:structurizer prompt 版本 + provider 配置载体 | F6-03/04 从配置读 prompt/provider | 配置读取测试 | G-CR2-03 |
| F6-10 | test | 先红后绿:真实样本（HTML/噪声）clean→rag→search 端到端语义测试（PDF 样本标 xfail） | 端到端语义命中 | e2e regression | [Q7] |
| F6-11 | auth | **删除不成立的 legacy 密码兼容声明,统一 PBKDF2**（[Q6]） | 无 legacy 哈希死代码 | auth 单测 | [Q6] / G-CR5-03 |

> **[Q3] 定档差异**:F6 由"可能全量复刻 legacy ~17k 行"收窄为"file+url(htmlCrawl)+chinatax+基础结构化"增量;**PDF/浏览器渲染/多 provider/scatter/layer-json(若超范围) 一律显式 degraded**（degraded 声明 + 测试 skip/xfail + 不留装成完成的桩）。这把 F6 从数周大工程压到可控范围。

### 6.7 `F7 · 测试有效性重建与 closure 重定级`（贯穿 + 收尾）

| 编号 | 工作项 | 涉及模块 | 规模 | 风险 |
|------|--------|----------|------|------|
| F7-01 | 测试原语:冻结时钟 / 并发 runner / 恶意路径 fixture / 向量真实性断言 / 真实样本（早期产出,供各 phase 复用） | `tests/fixtures` | M | med |
| F7-02 | 去夹具掩盖:reap 测试走真实 now_iso 写入路径,删除手写时间覆盖 | `tests/integration/p1_kernel_closure` | S | low |
| F7-03 | 重写桩固化测试（p3 等值断言）为语义属性断言 | `tests/integration/p3` 等 | S | med（随 F6 进度） |
| F7-04 | 填充 `tests/unit` 与 `tests/e2e`（当前空） | `tests/unit, tests/e2e` | M | low |
| F7-05 | closure 重新定级:撤销基于陈旧 `14 passed` 的 ✅,以真实断言为证据 | `docs/closure/` | S | low |
| F7-06 | 测试套件健康度量:断言强度门禁（禁止仅 status==200/!="" 作为唯一断言） | `tests/` + CI | S | med |

---

## 7. Owner decision gates

> final 态:全部由冻结 QnA（`owner-gated-qna.md`，Q1–Q7）关闭。

### 7.B gate-closure map（全部由冻结 QnA 关闭）

| gate | 对应冻结 Q | 裁决结论（下游唯一口径） | 状态 |
|------|-----------|--------------------------|------|
| G-F-1 | [Q1] | vec0 本轮 **degraded**（暴力 cosine + 强制 fail-loud 告警 + `VectorIndex` 接口抽象）;真实 vec0 移出本轮,接受性能线性劣化技术债 | CLOSED |
| G-F-2 | [Q2] | embedding 用 `Embedder` adapter + **本地小模型**;**模型维度=1536**（免触 schema/迁移）;测试 mock 显式标注 | CLOSED |
| G-F-3 | [Q3] | clean/rag 去桩**增量**:file(文本)+url(htmlCrawl)+chinatax+基础 structurize/construct;PDF/浏览器/多 provider/scatter **显式 degraded** | CLOSED |
| G-F-4 | [Q5] | 团队 API key 认证**本轮纳入**（校验中间件 + create_api_key + team 归属） | CLOSED |
| G-F-5 | [Q6] | **不保留** legacy 密码兼容（无存量用户）;删兼容声明,统一 PBKDF2 | CLOSED |
| G-F-6 | [Q4] | restart 本轮做 **recovery 模式**（按 current_stage/失败 step 锚点）;force/kickstart 延后;前置必修 F3-04 | CLOSED |
| G-F-7 | [Q7] | 全 phase **先红后绿铁律** + CI 断言强度门禁 + 禁止夹具掩盖 | CLOSED |

- **结论**：设计阶段**无 OPEN 决策项**,7 个 gate 全部 CLOSED,可转入 action-plan 派生（§10.A）。

---

## 8. 测试计划（meaningful-test 为一等公民）

> 用户明确要求"meaningful test"。核心原则:**每个 blocker 必须有一条在当前 HEAD FAIL、修复后 PASS 的回归**;禁止 `status==200 / !="" / 桩恒等输出` 作为唯一断言;禁止夹具手写正确数据绕过被测路径。

- **A 短途（unit / in-process,随 phase 提交）**：
  - F1:时间 round-trip(`fromisoformat` 可解析)+ 秒位正则 + PY 写入值 ≤/≥ SQL now 比较一致性。
  - F4:路径遍历拒绝(`../`/绝对路径)+ rowid 不变量(重复 upsert 0 孤儿 / 软删后新增不丢审计)+ cosine 维度不等 raise。
  - F3:claim/reap 用真实 now_iso + 冻结时钟,断言过期 claim 被回收且 step 退回 retry_wait。
- **B spike（integration / 真实路径,入门槛断言）**：
  - F3:并发 harness —— 双 worker + 强制租约过期 → 断言 artifact/chunk **无重复**(双重执行回归)。
  - F5:真实 embedding 语义命中(相关 query 的目标 chunk 排第一且分差显著)+ vec0 虚表类型断言(或 degraded 标注校验)。
  - F2:请求级连接关闭(无泄漏)+ 业务异常映射 4xx。
- **D mega（owner-triggered 长程 capstone）**：
  - 端到端:多 team 隔离 → ingestion(真实 HTML/PDF 样本)→ clean(真实 action)→ rag(真实 structurize/construct)→ 真实 embedding 向量化 → search 语义命中 → purge 清对象+向量 → restart 从失败阶段恢复。全程断言语义正确性 + 数据/审计完整性,而非仅流转。
- **[贯穿] 假绿防回归**：F7-06 断言强度门禁纳入 CI;closure 在 F7 前冻结(不得标 ✅)。

- **[final] 长程 capstone**：`tests/e2e/test_first_fixes_capstone.py`（A–J 步端到端）:
  - A 多 team 隔离建账 → B file(文本)+url(HTML)双源 ingestion → C worker claim + clean(htmlCrawl 真实清洗) → D 强制租约过期 + reap + 第二 worker(断言无重复副作用) → E rag structurize(结构化)+construct(chunk+summary) → F 独立 rag:vectorize step + 本地 1536 维真实 embedding → G search 语义命中(相关 chunk 排第一,分差显著) → H purge(断言 vec 向量删 + **对象删** + core 状态) → I restart recovery(从失败阶段恢复,断言重启 step 就绪) → J 路径遍历注入被拒。
  - 全程断言**语义正确性 + 数据/审计完整性**,而非仅流转;PDF/浏览器/多 provider 步骤标 `xfail`(degraded 声明)。
- **[final] Evidence pack（每 phase 收口）**：每 phase 交付 ① 先红后绿回归测试(commit 含"修复前 FAIL"截图/日志)② 该 phase 的 G-CRx-xx 闭环对照 ③ degraded 项的显式声明清单。
- **DoD（全 plan 收口判据）**：① F1–F7 全部 phase 的先红后绿测试通过;② capstone A–J 通过(degraded 步骤 xfail 明示);③ CI 断言强度门禁生效;④ closure 据真实断言重新定级(撤销旧 `14 passed` 的 ✅);⑤ 全部 degraded/延后项有显式记账(不留装成完成的桩)。

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| vec0 扩展运维不可控 | 部署环境无 sqlite-vec | F5-02 无法真实加载 | 抽象 VectorIndex 接口;degraded fallback **显式告警**(非静默);gate G-F-1 |
| 去桩范围爆炸(legacy ~17k 行) | F6 试图全量复刻 | 工期数周失控 | gate G-F-3 增量限定 source 类型 + 显式降级声明 |
| 真实 embedding 引入外部依赖/成本 | F5-01 接外部 API | 测试不稳定/计费 | adapter 接口 + 本地小模型 + 测试用确定性 mock(显式标注非交付) |
| F3-02 终态重构影响面大 | 改执行器/内核边界 | 回归风险高 | 先 F1(事务模式)稳固,再小步重构 + 并发回归(F3-07) |
| 旧桩固化测试需大量改写 | F6 接真实实现 | p3 等值断言批量失败 | F7-01 先建原语,逐 phase 替换(F7-03) |
| F1 时间格式改动影响已有数据 | 已有库含畸形时间串 | 比较仍混格式 | 当前为 P 阶段无生产数据;必要时附一次性归一迁移 |

---

## 10. 后继解锁 + action-plan 派生图

- **解锁的下游价值**：修复后系统从"管道空壳"变为"可信知识库内核" —— 真实清洗、真实向量检索、可恢复工作流、可证明正确性的测试;为后续产品化(更多 source/provider、生产部署)解锁可靠基线。
### 10.A [final] action-plan 派生与排序

> final 的 §6 phase 簇 1:1 映射下游 action-plan 文件;在此枚举并排序。建议目录 `docs/action-plan/first-fixes/`。

| phase 簇 | 派生的 action-plan 文件 | 台账 ID 区间 | 时序 / 依赖 |
|----------|--------------------------|--------------|-------------|
| F1 时间与事务基座 | `FF-F1-time-tx-base.md` | F1-01..05 | **最先**(keystone);F1-04 与 F3 同窗口 |
| F2 连接与装配 | `FF-F2-conn-wiring.md` | F2-01..04 | 与 F1 并行 |
| F3 内核恢复与一次性语义 | `FF-F3-kernel-recovery.md` | F3-01..09 | 依赖 F1;F3-02 定义执行器契约(F6 前置) |
| F4 适配层安全与完整性 | `FF-F4-adapter-safety.md` | F4-01..07 | 与 F3 并行 |
| F5 向量真实性与检索 | `FF-F5-vector-authenticity.md` | F5-01..04 | 依赖 F4 rowid;范围已 [Q1][Q2] 定档 |
| F6 执行器去桩与能力 | `FF-F6a-cleaners.md` / `FF-F6b-rag-executors.md` / `FF-F6c-auth-config.md`（按规模拆 3 份） | F6-01..11 | 依赖 F1–F5 + F3-02 契约;范围已 [Q3][Q5][Q6] 定档 |
| F7 测试整合与 closure | `FF-F7-test-integrity.md` | F7-01..06 | 原语 lane 早启;整合 lane 收尾 |

- **解锁的下游价值**：修复后系统从"管道空壳"变为"可信知识库内核"——真实清洗(file/url)、真实本地向量检索、可恢复工作流、可证明正确性的测试;为生产化(真实 vec0、外部 embedding、PDF/浏览器/多 provider)解锁可靠基线。

---

## 11. Final recommendation

- **推荐序列**：`F1(基座) → [F2 ∥ F4] → F3 → F5 → F6 → F7(整合)`;F7 测试原语 lane 与 F1 并行启动,先红后绿贯穿全程。
- **一句话总结**：先用 F1 拔掉时间/事务的单点根因,再并行修可靠性(F2)与安全完整性(F4),然后修内核一次性语义(F3)与向量真实性(F5),最后去桩补真实能力(F6)并以重建的有意义测试(F7)封住假绿 —— 把"名义跑通、语义为空"的骨架变成可证明正确的内核。

---

## 13. [final] 冻结槽

### 13.A owner-decision-freeze（QnA 裁决索引，NORMATIVE）

| Q | 主题 | 冻结结论（下游唯一口径） | 来源 |
|---|------|--------------------------|------|
| Q1 | vec0 | degraded（暴力 cosine + fail-loud 告警 + `VectorIndex` 接口）;真实 vec0 移出本轮 | qna register |
| Q2 | embedding | `Embedder` adapter + 本地小模型,**维度=1536** | qna register |
| Q3 | 去桩范围 | 增量:file+url(htmlCrawl)+chinatax+基础结构化;PDF/浏览器/多 provider/scatter degraded | qna register |
| Q4 | restart | recovery 模式(current_stage 锚点);force 延后;前置修 F3-04 | qna register |
| Q5 | API key | 本轮纳入(校验中间件 + create_api_key) | qna register |
| Q6 | 密码兼容 | 不保留,删声明统一 PBKDF2 | qna register |
| Q7 | test-first | 全 phase 先红后绿铁律 + CI 断言强度门禁 | qna register |

> 引用方只看 `Q 编号 + 业主回答`（见 `owner-gated-qna.md`），不在本文或 action-plan 重复抄写分析。

---

## 14. 交叉引用与修订历史

- **交叉引用**：`docs/design/first-fixes/owner-gated-qna.md`（冻结裁决）、`docs/eval/first-code-review-plan/{index,part-cr-1..8}.md`、`docs/refactor/index.md`、`docs/templates/eval-planning.md`。
- **修订历史**：

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-05-31 | Opus 4.8 | 初稿（stage=`initial`）：28 blocker 分簇为 F1–F7 七 phase,投射 DAG + 测试计划 + 7 个 owner gate |
| v0.2 | 2026-05-31 | Opus 4.8 | 提升 stage=`proposed`（reference-anchor 由 CR 报告预完成）。4 项 eval-driven 精化（§2.B）：① F1-04 事务模式 REFRAME（autocommit 需包裹多写,S→M/high,耦合 F3）；② 收纳 G-CR4-09 重复事件写入器→F3-07；③ G-CR2-03 余项归位（workflow_step_links→F3-08，prompt/provider_configs→F6-09）；④ 执行器契约提为贯穿红线 + F3-02/F6 桥接。 |
| v0.3 | 2026-05-31 | Opus 4.8 | 提升 stage=`final`（`owner-gated-qna.md` Q1–Q7 冻结，均同意 Opus 推荐）。§2.C critique vs proposed（7 项 RESIZE/CONFIRM/CORRECT）；§7.A→§7.B gate-closure（7 gate 全 CLOSED）；F5/F6 由 refine 定档为 degraded+本地 1536 embedding / 增量 file+url+chinatax；O3 密码兼容转 in-scope 删除（F6-11）；新增 §8 capstone A–J + evidence pack + DoD、§10.A action-plan 派生图（F6 拆 3 份）、§13 owner-decision-freeze。 |
