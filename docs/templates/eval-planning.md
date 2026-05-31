# Nano-Agent Eval 模板 · planning（三态成熟链 initial → proposed → final）

> **模板类型**：`eval / planning`（**stage-aware**：一套骨架，`stage` 开关切换三态）
> **一句话用途**：给"多章节子阶段 / 需要 ≥2 份 action-plan"的策划链一个统一模板——**同一份文档**随成熟度走 `initial-planning → proposed-planning → final-execution-plan` 三态，骨架恒定、阶段块开关。
> **何时用**：一个子阶段会派生 **≥2 份 action-plan**、需要走完整三态成熟（initial 速写 → proposed 重锚 → final 冻结派生）。
> **何时不用**：① 一次性想清楚、单 action-plan 的轻量 scoping → `eval-general-purpose.md`；② 冻结阶段边界/退出判据 → `charter.md`；③ 写可验证验收 → `design.md` / `design-sketch.md`；④ 排单份执行序列 → `action-plan.md`。
>
> **核心认知（务必先读）**：initial / proposed / final **不是三种文档，是一个文档的三个成熟态**（open → narrowed → frozen）。承重不变量 = **每一态都对它的上一态做一次辨证裁定**（§2）：initial 裁定原始 evals、proposed 裁定 initial、final 裁定 proposed。详见 `docs/templates/re-design/better-planning.md`。
>
> **使用纪律（共有脊 · 所有 eval 模板一致）**：
> 1. 本文是 **eval**，**冻结零决策**——直到 `final` 阶段也只是"把 owner 已在 `qna.md` register 裁决的结论汇编成执行基线"，不在本文新冻结决策。
> 2. **逐级 supersede，不增量改前序**：proposed 取代 initial、final 取代两者；前序保留作历史 Δ 基线，**不回改**。
> 3. **stage 开关**：头部 `stage` 字段决定填哪些块；带 `[仅 X]` 标记的段只在对应态填，其余删。
> 4. 头部 / 性质声明 / TL;DR / 输入锚定 / 修订历史为**共有脊**，跨 eval 模板一致。

---

# `{SUBPHASE}` —— `{初步规划 | proposed-planning | Final Execution Plan}`（by `{AUTHOR}`）

> **stage**：`initial | proposed | final` ← **开关，决定下方 `[仅 X]` 块**
> **作者**：`{AUTHOR}`（panel / 跨模型 handoff：`{PANEL_OR_NONE}`）
> **时间**：`{DATE}`
> **文档性质（自宣告 role，按 stage 取一句）**：
> - `initial`  = "设计流程**第 ① 步**；不是 charter，不是 action-plan，冻结零决策"
> - `proposed` = "**取代 initial-planning**，作 pre-charter-qna 前**唯一精炼工作基线**"
> - `final`    = "**取代 initial + proposed 两份**，作 action-plan 制作前**唯一执行基线**；不再在前两份上增量"
> **上游权威输入**：
> - `{INPUT_1}` — `{RELEVANT_PART}`
> **[仅 final] 输入权威次序**：`冻结 QnA > HEAD 代码实测 > design artifacts`（声明谁压谁）
> **phase 命名 & 工作项 ID 方案**：`{MCCM1-4 / MIX1-9 / MP·NP …}`（参数化；ID 跨态稳定）
> **裁定动词 rubric（§2 用，可覆盖）**：`{见 §2 默认；或自定}`
> **文档状态**：`draft | reviewed | frozen | superseded`（stage 是独立成熟度轴，见上方 `stage` 字段；勿把 stage 值塞进 status）
> **下游消费者**：`{它派生/解锁的 action-plan 或 charter}`

---

## 0. TL;DR

- **核心论点**：`{ONE_PARAGRAPH_THESIS}`
- **一句话**：`{ONE_LINER}`
- **[仅 proposed/final] 本态相对上一态做了什么**：`{SUPERSESSION_ONE_LINER}`

---

## 1. Reference anchors / 输入与依据

| 输入 | 类型 | 提供了什么 | 锚点 |
|------|------|------------|------|
| `{INPUT}` | `eval / anchor / qna / closure / 上一态 plan` | `{WHAT}` | `{FILE_OR_LINE}` |

- **纪律继承**：`{INHERITED_DISCIPLINE_FROM_PRIOR_PHASE}`
- **[仅 initial] 借用骨架**：`{以哪份上一阶段 final 为格式骨架，如有}`

---

## 2. 辨证审核（裁定上一阶段）★ 承重段

> **这是让"状态转移"物化的段，三态都必须有，裁定对象随 stage 升级。**
> 裁定动词 rubric（参考，可覆盖；见附录 B 四套已知词表）：
> - `initial`  → 裁定**原始 evals / owner 提案**（整合/refine，**无 Δ-vs-plan 表**）
> - `proposed` → **Δ 表 vs initial**：`KEEP / REFRAME / CLOSED / NEW`（或 `采纳/调整/不纳入`）
> - `final`    → **critique vs proposed**：`CONFIRM / CORRECT / REFINE / RESIZE / GAP / SCOPE↑↓`

### 2.A [仅 initial] 对原始 evals / owner 提案的整合裁定

| 来源项 | 整合裁定 | 落到哪个 phase | 备注 |
|--------|----------|----------------|------|
| `{EVAL_ITEM}` | `纳入 / refine / 不纳入` | `{PHASE}` | `{NOTE}` |

### 2.B [仅 proposed] Δ 审核 vs initial-planning

| item-ID | 裁定（KEEP/REFRAME/CLOSED/NEW） | 重分配 phase | 复用判定（✅ 复用 / ♻️ 重 substrate / 🆕 净新） | 理由 / 新证据 |
|---------|--------------------------------|--------------|------------------------------------------|----------------|
| `{X3-01}` | `{VERDICT}` | `{PHASE}` | `{REUSE}` | `{WHY，引 reference-anchor/ARCH/TR}` |

- **本态核心转向（一句话）**：`{CORE_REFRAME}`（如：从"激活"改为"D1 引擎重建"）

### 2.C [仅 final] critique vs proposed-planning

| item-ID | 裁定（CONFIRM/CORRECT/REFINE/RESIZE/GAP/SCOPE↑↓） | 处置 | 依据（冻结 Q / HEAD 锚） |
|---------|---------------------------------------------------|------|---------------------------|
| `{X3-07}` | `{VERDICT}` | `{HANDLING}` | `{[Q8] / file:line}` |

---

## 3. 范围与非范围（In/Out-Scope）

### 3.1 In-Scope
- **[S1]** `{ITEM}` — `{WHY}`

### 3.2 Out-of-Scope / 延后
- **[O1]** `{ITEM}` — `{WHY_DEFER}`；重评条件：`{REVISIT}`

> **范围模态随 stage**：initial=提案/条件式；proposed=sized 但仍 gated；final=execution-ready 定档。

---

## 4. 跨阶段贯穿主题（threaded themes）

> 横切多个 phase 的主题：技术路线红线 / 治理冻结面 / migration inventory / 安全边界。

- **技术路线红线**：`{TR_RED_LINES，剔除的非 substrate 机制}`
- **治理冻结面**：`{独立 PR / 安全复核 / schema-freeze 测 …}`
- **[proposed/final] migration inventory**：`{036/037/... 编号 + 条件}`

---

## 5. DAG（关键路径 + 并行窗）

```text
{PHASE}1 ──▶ {PHASE}2 ──▶ {PHASE}3
{PHASE}A ──▶ {PHASE}B            （{并行窗说明 + 谁不抢谁带宽}）
关键路径：{CRITICAL_PATH}
```

---

## 6. 逐 phase 工作台账

> **台账模态随 stage 升级，ID 跨态稳定。**

### 6.x `{PHASE_NAME}`

**[initial] first-cut（初判，待 pin）**

| 编号 | 工作项 | 涉及模块（初判，待 reference-anchor 期 pin） | 规模 | 风险 |
|------|--------|-----------------------------------------------|------|------|
| `{X3-01}` | `{ITEM}` | `{MODULE}` | `XS/S/M/L` | `low/med/high` |

**[proposed] 重分配 + verdict 绑定 + 拆解**

| 编号 | 工作项 | reference 轴 + ✅蓝本 + HEAD 锚(file:line) + ⛔避坑 + TR | 复用 | 规模 |
|------|--------|----------------------------------------------------------|------|------|
| `{X4-03a}` | `{ITEM}` | `{ANCHORS}` | `✅/♻️/🆕` | `{SIZE}` |

**[final] action-plan 绑定**

| 编号 | lane | 工作项 | 复用 | 退出(exit) | evidence | migration | 来源 [Qn] |
|------|------|--------|------|------------|----------|-----------|-----------|
| `{X4-03a}` | `{LANE}` | `{ITEM}` | `✅/♻️/🆕` | `{EXIT}` | `{EVIDENCE}` | `{036…}` | `[Q?]` |

---

## 7. Owner decision gates

> **gate 模态随 stage：OPEN → 精炼 OPEN → CLOSED（由冻结 Q 关闭）。**

### 7.A [initial / proposed] 开放 gates

| 编号 | 决策点 | 影响 | 当前建议 / 倾向 | 状态 |
|------|--------|------|------------------|------|
| `G-X-1` | `{DECISION}` | `{IMPACT}` | `{RECOMMENDATION}` | `OPEN` |

### 7.B [仅 final] gate-closure map（全部由冻结 QnA 关闭）

| gate | 对应冻结 Q | 裁决结论（下游唯一口径） | 状态 |
|------|-----------|--------------------------|------|
| `G-X-1` | `[Q2]` | `{FROZEN_CONCLUSION}` | `CLOSED` |

- **结论**：`{设计阶段无 OPEN 决策项，可转入 action-plan / 仍余 N 项待 owner}`

---

## 8. 测试计划

- **A 短途（in-worker route/unit）**：`{SCOPE}`
- **B spike（live HTTP/WS，入 cap + denominator）**：`{SCOPE}`
- **D mega（owner-triggered 长程）**：`{SCOPE}`
- **[仅 final] 长程 capstone**：`{命名下游 test-surface 文件，如 test/mega-journey/...mega.test.mjs；A–J 步}`
- **[仅 final] Evidence pack（每 phase 收口）** + **DoD**：`{EVIDENCE_AND_DOD}`

---

## 9. 风险登记

| 风险 | 触发 | 影响 | 缓解 |
|------|------|------|------|
| `{RISK}` | `{TRIGGER}` | `{IMPACT}` | `{MITIGATION}` |

---

## 10. 后继解锁 + action-plan 派生图

- **解锁的下游价值**：`{web-v90 / FE / 下游 charter}`

### 10.A [仅 final] action-plan 派生与排序

> final 的 §6 phase 簇 **1:1 映射**下游 action-plan 文件；在此枚举并排序。

| phase 簇 | 派生的 action-plan 文件 | 台账 ID 区间 | 时序 / 依赖 |
|----------|--------------------------|--------------|-------------|
| `{MCX3-MP1/2/3}` | `{docs/action-plan/.../MCX3-*.md}` | `{X3-01..07}` | `{ORDER + 依赖约束}` |
| `{MCX4-NP1/2/3}` | `{docs/action-plan/.../MCX4-*.md}` | `{X4-01..04}` | `{并行窗 + [Q?] 不抢带宽}` |

---

## 11. Final recommendation

- **推荐序列**：`{RECOMMENDED_SEQUENCE}`
- **一句话总结**：`{CLOSING_ONE_LINER}`

---

## 12. [仅 final] HEAD 代码实测 / 净新章节（可选）

> final 常 append 净新事实/债章节（标【新增章节】）：HEAD 代码实测（修正前序前提）/ 前端 IF 债 / API surface / docs 台账。

| # | HEAD 事实（实测锚 file:line） | 对前序前提的修正 | 处置 |
|---|--------------------------------|------------------|------|
| `ARCH-X1` | `{FACT}` | `{CORRECTION}` | `{HANDLING}` |

---

## 13. [仅 final] 冻结槽（双填充，至少一个）

> 按子阶段性质选填 owner-decision-freeze 和/或 contract-surface-freeze。

### 13.A owner-decision-freeze（QnA 裁决索引，NORMATIVE）
| Q | 主题 | 冻结结论（下游唯一口径） | 来源 |
|---|------|--------------------------|------|
| `Q1` | `{TOPIC}` | `{CONCLUSION}` | `qna register` |

### 13.B contract-surface-freeze（如适用）
- **冻结的 surface（N 个）**：`{SURFACES}`
- **背书方式**：`{前端碰撞 review / consumer endorsement}`

---

## 14. 交叉引用与修订历史

- **交叉引用**：`{related docs}`
- **修订历史**（可选；跨模型 proposed 可缺）：

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | `{DATE}` | `{AUTHOR}` | 初稿（stage=`{STAGE}`） |

---

## 附录 A · stage 速用指南（填哪些块）

| 段 | initial | proposed | final |
|----|---------|----------|-------|
| §2 辨证审核 | 2.A 整合裁定（无 Δ 表） | 2.B Δ 表 vs initial | 2.C critique vs proposed |
| §6 工作台账 | first-cut | 重分配+绑定+拆解 | action-plan 绑定 |
| §7 gates | 7.A OPEN | 7.A OPEN（精炼） | 7.B gate-closure map |
| §8 测试 | A/B/D 概要 | +DoD | +capstone+evidence pack |
| §10 派生 | 解锁价值 | 解锁价值 | +10.A action-plan 派生图 |
| §12/§13 | — | — | 净新章节 + 冻结槽 |
| 自宣告 role | 第①步 | 取代 initial | 取代两份 |

> **省略态合法**：轻量子阶段可 `initial → final`（跳 proposed）或 `initial → re-planning → charter`（跳 final，如 pro-to-product）。省略须在头部 `文档性质` 注明。

## 附录 B · 裁定动词 rubric 参考（§2 可覆盖，实测随作者/lineage 变）

| 来源 | proposed 阶段词表 | final 阶段词表 |
|------|-------------------|----------------|
| MCCM（Opus） | `KEEP / REFRAME / CLOSED / NEW` | `CONFIRM / CORRECT / REFINE / GAP` |
| MCX（Opus） | `CONFIRM / REFINE / CORRECT / RESIZE` | `+ SCOPE↑ / SCOPE↓` |
| MI（GPT proposed） | `采纳 / 调整后采纳 / 不纳入` | `保留 / 升级 / 撤销 / 新增` |

> 复用判定符通用：`✅ 复用 / ♻️ 重 substrate / 🆕 净新`。
