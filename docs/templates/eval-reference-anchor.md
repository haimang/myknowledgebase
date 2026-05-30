# Nano-Agent Eval 模板 · reference-anchor

> **模板类型**：`eval / reference-anchor`
> **状态标记**：`provisional`（新近确立的实践，属"设计三件套"之 ②：initial-planning → **reference-anchor** → pre-charter-qna；待该三件套确认为稳定流程后再正式推广）。
> **一句话用途**：把某阶段**每一个可借鉴点**钉到具体 `path:line` / URL，给出"借/部分借/反例/净新"裁定，并用 **substrate-fit / 技术路线过滤**把借来的机制按 nano-agent 路线降级或重映射——**防止把"思路"误抄成"机制"**。
> **何时用**：design 之前，为某功能簇系统性盘点 `context/` 参考 + web 来源、产出可核验的"借鉴台账"。
> **何时不用**：① 找我方缺口 → 用 `eval-gap-study.md`；② 做设计决策 → 用 `design.md`（本文只喂 design，不替代）；③ 穷尽分析外部 CLI → 用 `investigation.md`。
>
> **使用纪律（共有脊 · 所有 eval 模板一致）**：
> 1. 本文是 **eval / reference-anchor**，**冻结零决策**——只产出"借鉴台账 + substrate 过滤"，喂给 design。
> 2. **机制 ≠ 思路**：每个借鉴点都必须过 §5 的技术路线（TR）过滤；凡与 nano-agent 路线冲突的机制，标降级/重映射，不得直抄。
> 3. 头部 / 性质声明 / TL;DR（此处为"如何读"）/ 输入锚定 / 修订历史为**共有脊**，跨 eval 模板一致。

---

# `{REFERENCE_ANCHOR_TITLE}`

> **对象**：`{PHASE_OR_CLUSTER} 的参考锚定`
> **日期**：`{DATE}`
> **作者**：`{AUTHOR}`（panel / sub-agents：`{PANEL_OR_NONE}`）
> **文档性质**：`eval / reference-anchor`（provisional；冻结零决策，喂 design）
> **文档状态**：`draft | reviewed | superseded`
> **上游权威输入**：
> - `{INITIAL_PLANNING_DOC}`
> **下游消费者**：`{DESIGN_DOCS_THIS_FEEDS}` → 之后 `{PRE_CHARTER_QNA}`

---

## 0. 如何读这份台账

### 0.1 Verdict 图例

| 符号 | 含义 |
|------|------|
| ✅ 借 | 机制与思路都可借，按路线落地 |
| 🔶 部分 | 思路可借、机制需改造（见 §5 TR 过滤） |
| ⛔ 反例 | 不可借；记为要避开的坑 |
| 🆕 净新 | 无参考可借，nano-agent 净新实现 |

### 0.2 置信分层

| 置信 | 含义 |
|------|------|
| `context-line` | 已落到 `context/<ref>/<file>:line`，最高置信 |
| `HEAD` | 已对本仓 HEAD 复核 |
| `web-high` / `web-low` | web 来源，标高/低置信 |

### 0.3 主题轴

> 本阶段的借鉴按以下主题轴（A、B、C…）组织：`{THEME_AXES}`

---

## 1. 逐主题轴锚定矩阵

> 每条主题轴一张表：`借鉴点 × 来源引擎`，给 path:line / URL + verdict + 置信。

### 1.A 轴 A — `{AXIS_A_NAME}`

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| `{POINT}` | `context/{ref}/{file}:{line}` | `{REF_ENGINE}` | `✅/🔶/⛔/🆕` | `context-line/HEAD/web-*` | `{WHAT_TO_BORROW_OR_NOT}` |

### 1.B 轴 B — `{AXIS_B_NAME}`

| 借鉴点 | 来源（path:line / URL） | 来源引擎 | Verdict | 置信 | 借什么 / 不借什么 |
|--------|-------------------------|----------|---------|------|--------------------|
| `{POINT}` | `{SOURCE}` | `{REF_ENGINE}` | `✅/🔶/⛔/🆕` | `{CONFIDENCE}` | `{NOTE}` |

*（按需扩展轴 C / D / …）*

---

## 2. 反例坑表（⛔）

> 明确"不可借/要避开"的点，连同为什么。

| 反例 | 来源 | 为什么不可借 | 我们怎么做 |
|------|------|--------------|------------|
| `{ANTI_PATTERN}` | `{SOURCE}` | `{WHY_NOT}` | `{OUR_APPROACH}` |

---

## 3. 净新表（🆕）

> 无参考可借、必须 nano-agent 净新实现的点。

| 净新点 | 为什么无参考 | 落点（哪个 design/相位） |
|--------|--------------|--------------------------|
| `{NET_NEW}` | `{WHY_NO_REF}` | `{WHERE}` |

---

## 4. [可选] Web 来源台账

> 非 `context/` 的 web 来源单列，标高/低置信。

| 主张 | URL | 置信 | 用途 |
|------|-----|------|------|
| `{CLAIM}` | `{URL}` | `web-high / web-low` | `{USE}` |

---

## 5. Substrate-fit / 技术路线（TR）过滤复核（核心价值段）

> 对每个 ✅/🔶 借鉴点，按 nano-agent 技术路线逐条过滤：**机制与我方 substrate 是否适配？冲突的降级/重映射成什么？** 这是阻止"盲目照抄"的闸门。

| 借鉴点 | 原机制 | 与 nano-agent 路线（TR-x）是否冲突 | 过滤后落地形态（降级/重映射/直采） |
|--------|--------|-------------------------------------|-------------------------------------|
| `{POINT}` | `{ORIGINAL_MECHANISM}` | `TR-{x}: 冲突 / 兼容` | `{ADAPTED_FORM}` |

- **substrate-fit 总结（对 HEAD）**：`{SUBSTRATE_FIT_SUMMARY}`

---

## 6. 核验记录

> 逐条可核：每个锚点是否被实际打开核对过。

| 锚点 | 是否核验 | 核验方式 | 备注 |
|------|----------|----------|------|
| `{ANCHOR}` | `✅ 已核 / ⏳ 待核` | `打开 file:line / 抓 web / HEAD grep` | `{NOTE}` |

---

## 附录

### A. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | `{DATE}` | `{AUTHOR}` | 初稿 |
