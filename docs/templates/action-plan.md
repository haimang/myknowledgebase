# Nano-Agent 行动计划模板

> 服务业务簇: `{SERVICE_CLUSTER_NAME}`
> 计划对象: `{PLAN_OBJECT}`
> 类型: `new | upgrade | modify | refactor | migration | remove`
> 作者: `{AUTHOR}`
> 时间: `{DATE}`
> 文件位置: `{TARGET_PATHS}`
> 上游前序 / closure:
> - `{PREDECESSOR_CLOSURE_OR_GATE}`
> 下游交接:
> - `{SUCCESSOR_PLAN_OR_HANDOFF}`
> 关联设计 / 调研文档:
> - `{RELATED_DESIGN_DOCS}`
> - `{RELATED_INVESTIGATION_DOCS}`
> 冻结决策来源:
> - `{DESIGN_QNA_OR_DECISION_REGISTER}`（只读引用；本 action-plan 不填写 Q/A）
> grounding 来源:
> - `{design X | eval-reference-anchor Y | charter Z}`（§7 内置锚区据此摘录；无独立 reference-anchor 时，§7 就是本 AP 的 grounding 真源）
> 关联 reference-anchor:
> - `{独立文件链接 | 见 §7 内置锚区 | N/A}`
> 文档状态: `draft | reviewed | executing | executed | superseded`

---

## 0. 执行背景与目标

> 用一到三段话说明：为什么现在要执行这份计划、它从哪些 frozen design / QNA / closure 继承输入、它要把哪些设计结论落成可交付物。
>
> **纪律**：如果仍有 owner / architect 需要回答的问题，不应在 action-plan 中开 Q/A；应回到 design / qna register 完成冻结。本文件只消费已冻结结论。

- **服务业务簇**：`{SERVICE_CLUSTER_NAME}`
- **计划对象**：`{PLAN_OBJECT}`
- **本次计划解决的问题**：
  - `{PROBLEM_1}`
  - `{PROBLEM_2}`
  - `{PROBLEM_3}`
- **本次计划的直接产出**：
  - `{DELIVERABLE_1}`
  - `{DELIVERABLE_2}`
  - `{DELIVERABLE_3}`
- **本计划不重新讨论的设计结论**：
  - `{FROZEN_DECISION_1}`（来源：`{Q_OR_DESIGN_REF}`）
  - `{FROZEN_DECISION_2}`（来源：`{Q_OR_DESIGN_REF}`）

---

## 1. 执行综述

### 1.1 总体执行方式

> 用一段话概括：这份 action-plan 一共分几个 Phase，执行方式是“先审计后改动”、“先协议后实现”、“先底层后上层”、“先迁 consumer 后删除”等哪一种。这里写执行策略，不重新论证设计方案本身。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | `{PHASE_1_NAME}` | `XS / S / M / L / XL` | `{PHASE_1_SUMMARY}` | `-` |
| Phase 2 | `{PHASE_2_NAME}` | `XS / S / M / L / XL` | `{PHASE_2_SUMMARY}` | `{PHASE_DEP}` |
| Phase 3 | `{PHASE_3_NAME}` | `XS / S / M / L / XL` | `{PHASE_3_SUMMARY}` | `{PHASE_DEP}` |
| Phase N | `{PHASE_N_NAME}` | `XS / S / M / L / XL` | `{PHASE_N_SUMMARY}` | `{PHASE_DEP}` |

> 说明：上表 `规模` 是每个 Phase 的**描述性提示**（帮助阅读，工作量小则该 Phase 自然简短），**不是开工前的体量判定闸，也不改变本模板任何段落的取舍**。本模板是单一模板，不分 flavor、不分档。

### 1.3 Phase 说明

1. **Phase 1 — `{PHASE_1_NAME}`**
   - **核心目标**：`{PHASE_1_GOAL}`
   - **为什么先做**：`{WHY_FIRST}`
2. **Phase 2 — `{PHASE_2_NAME}`**
   - **核心目标**：`{PHASE_2_GOAL}`
   - **为什么放在这里**：`{WHY_SECOND}`
3. **Phase N — `{PHASE_N_NAME}`**
   - **核心目标**：`{PHASE_N_GOAL}`
   - **为什么放在这里**：`{WHY_N}`

### 1.4 执行策略说明

> **纪律**：本节写执行策略，**不重述 §6 已引用的冻结决策的理由**（避免与 design/qna 重复，只写"怎么执行"，不写"为什么这么设计"）。

- **执行顺序原则**：`{ORDERING_STRATEGY}`
- **风险控制原则**：`{RISK_STRATEGY}`
- **测试推进原则**：`{TEST_STRATEGY}`（短途→spike→mega→soak 如何推进，详见 §8 测试台账）
- **文档同步原则**：`{DOCS_STRATEGY}`
- **回滚 / 降级原则**：`{ROLLBACK_OR_DEGRADE_STRATEGY}`

### 1.5 本次 action-plan 影响结构图

> 用树状结构快速展示：本计划会影响哪些模块、目录、运行链路、服务边界、测试层或文档资产。
>
> 这一节不是文件系统快照，而是**影响结构图**；推荐按业务链路或执行路径写。

```text
{PLAN_OBJECT}
├── Phase 1: {PHASE_1_NAME}
│   ├── {AFFECTED_BOUNDARY_1}
│   └── {AFFECTED_BOUNDARY_2}
├── Phase 2: {PHASE_2_NAME}
│   ├── {AFFECTED_BOUNDARY_3}
│   └── {AFFECTED_BOUNDARY_4}
└── Phase N: {PHASE_N_NAME}
    ├── {AFFECTED_BOUNDARY_5}
    └── {AFFECTED_BOUNDARY_6}
```

---

## 2. In-Scope / Out-of-Scope

> 把 action-plan 的执行边界集中写在这里。设计上的边界应来自 design/QNA；本节只说明本轮执行做什么、不做什么、何时重评。

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `{IN_SCOPE_ITEM}`
- **[S2]** `{IN_SCOPE_ITEM}`
- **[S3]** `{IN_SCOPE_ITEM}`
- **[S4]** `{IN_SCOPE_ITEM}`

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `{OUT_OF_SCOPE_ITEM}`
- **[O2]** `{OUT_OF_SCOPE_ITEM}`
- **[O3]** `{OUT_OF_SCOPE_ITEM}`
- **[O4]** `{OUT_OF_SCOPE_ITEM}`

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `{ITEM}` | `in-scope` | `{WHY}` | `{REVISIT_CONDITION}` |
| `{ITEM}` | `out-of-scope` | `{WHY}` | `{REVISIT_CONDITION}` |
| `{ITEM}` | `defer / depends-on-design` | `{WHY}` | `{REVISIT_CONDITION}` |

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
> **第 4 件（条件 · 与净新度/风险成正比）`分解步骤`**：**净新 / 高风险**工作项，其 §4 `工作内容` 必须拆成有序子步（a/b/c）+ 边界情况，§5 `具体功能预期` ≥5 条；**扩展既有 / ♻️复用 / 沿用** 项一句话或枚举即可（不注水）。**`工作内容` 是全表最承重的一列（厚样本里占篇幅最大、最被下游消费），不可压成一句话——三元组管"落在哪/做到什么/怎么证明"，本条管"具体怎么一步步建"。**

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | `{WORK_ITEM}` | `add | update | remove | refactor | migrate` | `{FILE:LINE}` | `{ONE_LINE_EXIT}` | `{ID}-T01` | `low | medium | high` |
| P1-02 | Phase 1 | `{WORK_ITEM}` | `…` | `{FILE:LINE}` | `{ONE_LINE_EXIT}` | `{ID}-T02` | `…` |
| P2-01 | Phase 2 | `{WORK_ITEM}` | `…` | `{FILE:LINE}` | `{ONE_LINE_EXIT}` | `{ID}-T03` | `…` |

---

## 4. Phase 业务表格

> 每个 Phase 一张表，完整列出工作项、目标、涉及文件与对应测试台账项。`测试映射` 列指向 §8 的 `Test-ID`（测试细节只在 §8 写一次，此处不重复展开测试方法）。
>
> **`工作内容` 是承重列，分解度与净新度/风险成正比（硬地板第 4 件）**：
> - **净新 / 高风险**项：拆成**有序子步**（a/b/c…），逐步覆盖核心逻辑 + 边界情况 + 失败/降级路径，**不要压成一句话**。
>   - *范式（净新高风险状态机）*：`a) preview 调用 + 渲染 diff → b) arm 存 job 句柄/置 status → c) useEffect 轮询 + 卸载清 interval → d) terminal 三态映射(succeeded/failed/cancelled) + 渲染结果 → e) 进行中阻塞重复触发 → f) cancel 流转 → g) 轮询失败 backoff/超时 → h) 防泄漏 cleanup`。
> - **扩展既有 / ♻️复用 / 沿用**项：一句话或枚举即可（如"扩 N 个 adapter：…"），**不注水**。

### 4.1 Phase 1 — `{PHASE_1_NAME}`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P1-01 | `{ITEM_NAME}` | `{ITEM_DESCRIPTION}` | `{FILE:LINE}` | `{EXPECTED_OUTPUT}` | `{ID}-T01` | `{DONE_CRITERION}` |
| P1-02 | `{ITEM_NAME}` | `{ITEM_DESCRIPTION}` | `{FILE:LINE}` | `{EXPECTED_OUTPUT}` | `{ID}-T02` | `{DONE_CRITERION}` |

### 4.2 Phase 2 — `{PHASE_2_NAME}`

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| P2-01 | `{ITEM_NAME}` | `{ITEM_DESCRIPTION}` | `{FILE:LINE}` | `{EXPECTED_OUTPUT}` | `{ID}-T03` | `{DONE_CRITERION}` |

*（按需继续扩展 Phase 3 / Phase 4 / ...）*

---

## 5. Phase 详情

> 按 Phase 展开详细执行说明：做什么、改哪些文件、做到什么算结束。**测试不在此展开**——每项指向 §8 测试台账的 `Test-ID`，避免与 §8 重复。
>
> **`具体功能预期` 的展开度与净新度/风险成正比（硬地板第 4 件）**：净新 / 高风险 Phase ≥5 条，含**边界与失败/降级路径**（如状态机的 cancel/failed/超时/防重入）；扩展既有 Phase 可精简。与 §4 `工作内容` 分解度一致。

### 5.1 Phase 1 — `{PHASE_1_NAME}`

- **Phase 目标**：`{PHASE_GOAL}`
- **本 Phase 对应编号**：`P1-01` / `P1-02`
- **本 Phase 新增文件**：`{NEW_FILE_1}`
- **本 Phase 修改文件**：`{MODIFIED_FILE_1}`（file:line）
- **本 Phase 删除文件**（如无可删去）：`{DELETED_FILE_1}`
- **具体功能预期**：
  1. `{FUNCTION_EXPECTATION_1}`
  2. `{FUNCTION_EXPECTATION_2}`
- **对应测试台账项**：`{ID}-T01` / `{ID}-T02`（详见 §8）
- **收口标准**：`{EXIT_CRITERION_1}` / `{EXIT_CRITERION_2}`
- **本 Phase 风险提醒**：`{PHASE_RISK_1}`

### 5.2 Phase 2 — `{PHASE_2_NAME}`

- **Phase 目标**：`{PHASE_GOAL}`
- **本 Phase 对应编号**：`P2-01`
- **本 Phase 新增 / 修改 / 删除文件**：`{FILES}`（file:line）
- **具体功能预期**：
  1. `{FUNCTION_EXPECTATION_1}`
- **对应测试台账项**：`{ID}-T03`（详见 §8）
- **收口标准**：`{EXIT_CRITERION_1}`
- **本 Phase 风险提醒**：`{PHASE_RISK_1}`

*（按需继续扩展更多 Phase）*

---

## 6. 依赖的冻结设计决策（只读引用）

> 列出本 action-plan 依赖哪些 design / QNA / closure 结论。**不要在本节填写新 Q/A，也不要在这里等待 owner 回答；只引 register 的 Q 编号，不复制内容、不改口。**
>
> 如果某条关键结论尚未冻结，本 action-plan 应保持 `draft`（blocked）或回退到 design 阶段。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `{Q1_OR_DECISION}` | `{DESIGN_OR_QNA_LINK}` | `{IMPACT_ON_PHASES}` | `{BLOCK_OR_ROLLBACK}` |
| `{Q2_OR_DECISION}` | `{DESIGN_OR_QNA_LINK}` | `{IMPACT_ON_PHASES}` | `{BLOCK_OR_ROLLBACK}` |

---

## 7. 内置 Reference-Anchor 锚区

> **本段固定植入每份 AP**（业主指令）。它把本计划工作项要落到的既有代码、要避开的陷阱、以及安全项的威胁模型**就地钉住**——实现时 0 跳转、grounding 0 泄漏。
>
> - 若另有独立 `eval-reference-anchor`：把与本 AP 工作项相关的锚**摘进 §7.1**（不复制全文），并在 §7.3 指回真源。
> - 若没有独立 reference-anchor：**§7 就是本 AP 的 grounding 真源**，必须填实。

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

> `处置` 用 README §4.4 **复用判定**图例：`✅ 复用`（直接改写/扩展既有）/ `♻️ 重 substrate`（在既有基底上重建）/ `🆕 净新`（无既有可锚）。"读不改的参考点"在 `备注` 写明（如"已建好，别重写"）。**外部参考仓**（cf-agents/codex/gemini/claude-code）的借鉴另用 §7.3 + reference-anchor 的借鉴 verdict 图例，不在本表混用。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| A-1 | `{path:line}` | `{WHAT_IT_IS}` | `{P?-?? 替换点 / 落点}` | `✅ 复用` | `{NOTE，如"已建好别重写"}` |
| A-2 | `{path:line}` | `{WHAT_IT_IS}` | `{P?-??}` | `♻️ 重 substrate` | `{NOTE}` |
| A-3 | `{NEW_FILE}` | `{将新建}` | `{P?-??}` | `🆕 净新` | `{NOTE}` |

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | `{ANTI_PATTERN_1}` | `{WHY，可引 Q 编号}` |
| ⛔2 | `{ANTI_PATTERN_2}` | `{WHY}` |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**（如有）：`{LINK}` —— §7.1 是其与本 AP 相关子集的摘录；完整借鉴台账（含 ✅借/🔶部分借/⛔反例/🆕净新 verdict 与 substrate-fit/TR 过滤）见真源。
- **安全 / 信任边界类工作项的威胁模型锚**：`{威胁模型文件:行 或 §7.1 中的对应锚}` —— **不得留空**。若威胁模型尚未在任何上游做过，本 AP 不得标 `executed`，应先补 reference-anchor / design（防 grounding 泄漏进 AP）。

---

## 8. 测试台账

> **本段固定植入每份 AP**（业主指令）。它一次性回答：本 AP 有哪些测试项、各是什么类型 / 在哪一层、是**新增还是沿用既有用例**、映射到哪个工作项与收口目标、怎么算 PASS。**测试细节只在此写一次**（§4/§5 只引 Test-ID）。词表用仓内真实用语。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `{ID}-T01` | `{WHAT_IT_VERIFIES}` | `spike` | `live(D1)` | `🔱 fork {既有 spike} + {加的断言}` | `P2-03 → {收口目标}` | `commit {sha} + {test/spike 名} PASS + D1 {Q?} + {YYYY-MM-DD HH:MM UTC}` |
| `{ID}-T02` | `{WHAT_IT_VERIFIES}` | `spike` | `live` | `♻️ 沿用 {既有 spike}（0/少改动）` | `P3-01 → {收口目标}` | `commit + {test} PASS + run-time` |
| `{ID}-T03` | `{契约 / drift gate}` | `短途` | `契约` | `♻️ 沿用 {check-*-drift.mjs}` | `P1-02 → {收口目标}` | `commit + gate 0 命中 + run-time` |
| `{ID}-T04` | `{race / 长稳}` | `soak` | `live(D1)` | `🆕 新增 {test/spike/*-soak.spike.test.mjs}` | `P4-01 → N 次 deterministic 全 ordering 一致` | `commit + soak log + D1 {Q?} + run-time` |

**列定义（填法约束）**：
- **类型**：`短途`（每 PR 快测）/ `spike`（阶段性 journey 验证）/ `mega`（长程整合）/ `soak`（race / 长稳 deterministic × N）。
- **层**：`unit` / `集成` / `契约`（seam / drift gate）/ `回归` / `e2e` / `live(D1 forensic)`。
- **来源（新增 vs 复用 —— 必填，回答 owner 的"是新增还是复用既有用例"）**：
  - `🆕 新增`：点名将新建的 `test/...` 文件。
  - `♻️ 沿用`：点名既有用例（0 或少改动，纳入本 AP 回归）。
  - `🔱 fork`：点名 base 既有 spike + 写明本 AP 加了什么断言。
- **PASS 证据**：四元组 `commit + 测试/查询名 + run-time(UTC)`（对齐 closure 的诚实收口；**防假绿**见 §8.5）。

### 8.2 复用台账（沿用 / fork 的既有用例明细）

> 显式列出本 AP **不新建、而站在既有测试上**的部分，点名 file + 起跑线状态。

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `{test/spike/...spike.test.mjs}` | `🔱 fork → {新名}` | `+ {新断言}` | `已存在，PASS` |
| `{test/...}` | `♻️ 沿用` | `0 改动` | `已存在，纳入回归` |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·集成·契约·回归 | 开发中持续 |
| spike | journey 用例 | e2e·live | 每 Phase 收口 |
| mega | 长程整合全链 | live 全链 | **本 AP 收口** |
| soak | deterministic × N（race / 长稳）| live(D1) | **退出硬闸** |

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖 `{X}`（理由：`{WHY}`）→ 交后继 `{AP / charter}`；**不在本 AP 假装覆盖**。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带**四元组**证据；**计数 ≠ 价值**（对齐 closure 诚实收口 / bug-analysis Z.4-Z.5）。
- `degraded` 必带机器可读 `reason`；`pre-existing` 失败必带 **git 证据甩锅**，不 silent overclaim。
- **安全 / 信任边界**项的测试必须含**攻击向量用例**（对应 §7.3 威胁模型），不得只测 happy-path。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| `{RISK_OR_DEP}` | `{DESCRIPTION}` | `low | medium | high` | `{MITIGATION}` |

### 9.2 约束与前提

- **技术前提**：`{TECH_CONSTRAINTS}`
- **运行时前提**：`{RUNTIME_CONSTRAINTS}`
- **组织协作前提**：`{COLLABORATION_CONSTRAINTS}`
- **上线 / 合并前提**：`{RELEASE_CONSTRAINTS}`

### 9.3 文档同步要求

- 需要同步更新的设计文档：`{DOC_1}` / `{DOC_2}`
- 需要同步更新的说明文档 / README：`{README_OR_GUIDE}`
- 需要同步更新的测试说明：`{TEST_DOC}`

### 9.4 完成后的预期状态

> 用 3-5 条说明本 action-plan 完成后，系统、仓库结构、测试、文档或运行链路会变成什么状态。

1. `{POST_COMPLETION_STATE_1}`
2. `{POST_COMPLETION_STATE_2}`
3. `{POST_COMPLETION_STATE_3}`

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

> 本 AP 如何收口：**收口 = §8 测试台账逐项 PASS，且每项映射回 §3 工作项的收口目标。** 不再用模糊的"测试通过"。整体测试方法已在 §8 写清，本节只做映射与硬闸判定。

### 10.1 收口硬闸

所有 `mega + soak + 退出层` 测试项必须 **PASS 且四元组证据齐全**：

1. `{GLOBAL_EXIT_CRITERION_1}`（由 `{Test-ID}` 证明）
2. `{GLOBAL_EXIT_CRITERION_2}`（由 `{Test-ID}` 证明）
3. `{GLOBAL_EXIT_CRITERION_3}`（由 `{Test-ID}` 证明）

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| `{EXIT_GOAL_1}` | `P?-??` | `{ID}-T0?` | `commit + test + run-time` | `verified / observed-OK / partial / 未观察 / deferred` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | `{FUNCTION_DOD}` |
| 测试 | §8 测试台账全 PASS（退出硬闸项四元组齐全）|
| 文档 | `{DOC_DOD}` |
| 风险收敛 | `{RISK_DOD}` |
| 可交付性 | `{DELIVERY_DOD}` |

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**；按 closure 五态（`verified / observed-OK-at-closure / partial / 未观察 / deferred`）如实归类 + handoff，不 silent overclaim。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态非 `executed` 时本节省略。执行完成后回填实际发生了什么、偏差、新暴露的事实、已关闭的风险。
>
> **详细回填改用 append 模板 `respond-execution-log`（本 AP §11 的厚版）**；薄占位留在此处。residual 交后继 charter，**不回填本阶段**。

- **实际执行摘要**：`{EXECUTION_SUMMARY}`
- **Phase 偏差**（逐条带分类）：`{PHASE_VARIANCE}`
- **阻塞与处理**：`{BLOCKERS_AND_RESOLUTION}`
- **测试发现**（含全绿计数 + 新暴露事实）：`{TEST_FINDINGS}`
- **后续 handoff**：`{FOLLOW_UP_HANDOFF}`
