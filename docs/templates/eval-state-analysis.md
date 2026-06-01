# Nano-Agent Eval 模板 · state-analysis

> **模板类型**：`eval / state-analysis`
> **一句话用途**：里程碑/相位完成后，对系统**已交付的真实状态**做回溯快照（交付了什么、债务多少、声称 vs 真实是否对得上），再回身给下一周期交接。
> **何时用**：`after-<milestone>` 的状态分析、spike/test 水位复盘、债务盘点（debt profile）、"接下来该做什么"的回溯型 backlog。
> **何时不用**：① 给制品下收口结论 → 用 `closure.md`；② 复盘一次决策失误 → 用 `eval-retrospective.md`；③ 提案新阶段范围 → 用 `eval-general-purpose.md`。
>
> **使用纪律（共有脊 · 所有 eval 模板一致）**：
> 1. 本文是 **eval**，**不是 closure、不是 verdict、不是 charter**。它给现状一份冷静快照 + 前瞻交接，不替代收口或纲领。
> 2. **对账诚实红线（本 flavor 灵魂）**：必须把*声称*的价值与*真实*代码对账——`frozen ≠ done`、over/under-claim、占位/假零都要点名；每条 deferred 项必须带 **reopen 触发器**，不得静默吞掉。
> 3. 头部 / 性质声明 / TL;DR / 输入锚定 / 修订历史为**共有脊**，跨 eval 模板一致。

---

# `{STATE_ANALYSIS_TITLE}`

> **对象**：`after {MILESTONE}（{PHASE_RANGE}）`
> **日期**：`{DATE}`
> **作者**：`{AUTHOR}`（panel：`{PANEL_OR_NONE}`）
> **文档性质**：`eval / state-analysis`（本文是现状快照 + 前瞻交接；不是 closure / verdict / charter）
> **文档状态**：`draft | reviewed | superseded`
> **对照基线**：`{BASELINE_PREV_SNAPSHOT_OR_CHARTER}`
> **上游权威输入**：
> - `{CLOSURE_OR_REVIEW_1}`
> - `{CODE_OR_TEST_EVIDENCE}`
> **下游消费者**：`{NEXT_CHARTER_OR_OWNER_DECISION}`

---

## 0. 水位 / 健康一句话（TL;DR）

- **一句话现状**：`{ONE_LINE_HEALTH}`
- **核心结论**：`{TLDR_PARAGRAPH}`

---

## 1. 方法与对照基线

> 读了哪些代码/测试/closure；以什么为对照基线；什么算"可采信证据"。

- **对照基线**：`{BASELINE}`
- **证据来源**：`{CODE_PATHS / TEST_RUNS / GREP}`
- **复现入口**：见附录 A 的命令清单。

---

## 2. 回看清单（交付快照）

> 三类表按需取用：交付价值台账 / deferred 台账 / 逐单元评级矩阵。

### 2.1 交付价值台账

| 单元 | 声称交付 | 真实落地（代码核） | 评级 | 锚点 |
|------|----------|--------------------|------|------|
| `{UNIT}` | `{CLAIMED}` | `{REAL}` | `delivered / partial / placeholder / missing` | `{FILE_LINE}` |

### 2.2 Deferred / Carried-over 台账（每条带 reopen 触发器）

| 编号 | 项目 | 为什么 defer | reopen 触发器 | 携带至 |
|------|------|--------------|----------------|--------|
| `D-01` | `{ITEM}` | `{WHY_DEFERRED}` | `{REOPEN_TRIGGER}` | `{NEXT_PHASE}` |

---

## 3. 对账诚实（本 flavor 灵魂段）

> 把"声称 vs 真实"逐条对账。**frozen ≠ done**；over-claim 与 under-claim 都要点名；占位字段 / 假零 / 反例必须列出。

| 声称 | 真实 | 偏差类型 | 证据 | 影响 |
|------|------|----------|------|------|
| `{CLAIM}` | `{REALITY}` | `over-claim / under-claim / frozen≠done / placeholder / fake-zero` | `{FILE_LINE_OR_TEST}` | `{IMPACT}` |

- **诚实结论**：`{HONEST_SUMMARY_OF_GAP_BETWEEN_CLAIM_AND_TRUTH}`

---

## 4. 归因 / 缺口分析（如适用）

> 把问题归因到根源（如根因缝 S1..Sn、覆盖缺口、单点风险）。可选，但若本快照源于一批 review 发现，强烈建议写。

| 现象 | 归因（根源/缝/簇） | 根源位置 |
|------|---------------------|----------|
| `{SYMPTOM}` | `{ROOT_CAUSE}` | `{WHERE}` |

---

## 5. Verdict（价值-债务 / 达成度 / 健康评级）

| 维度 | 评级 | 一句话 |
|------|------|--------|
| 交付价值 | `{RATING}` | `{WHY}` |
| 累积债务 | `{RATING}` | `{WHY}` |
| 愿景/目标达成度 | `{RATING}` | `{WHY}` |
| **综合健康** | `{RATING}` | `{WHY}` |

- **反镀金提醒**：`{DONT_GOLD_PLATE / DONT_MANUFACTURE_WATER_LEVEL / DONT_OPEN_UNNEEDED_PHASE}`

---

## 6. 前瞻交接

> 给下一周期的输入：携带的 deferred（§2.2 汇总）+ 下一步建议 + start-gate 前置。

- **下一周期建议**：`{NEXT_CYCLE_RECOMMENDATION}`
- **start-gate 前置（下一 charter day-1 必须满足）**：
  - `{PREREQ_1}`
- **需 owner 拍板的问题**：
  - `{OWNER_QUESTION_OR_NONE}`

---

## 7. [profile · 可选] Spike / Test 水位评级

> 仅当本快照分析 spike/test 套件时启用。按桶给覆盖水位，对比上一基线。

| Spike / 单元 | 上一基线 | 本次 | D | W | E | 备注 |
|--------------|----------|------|---|---|---|------|
| `{SPIKE}` | `{PREV}` | `{NOW}` | `{D}` | `{W}` | `{E}` | `{NOTE}` |

- **水位裁定**：`{WATER_LEVEL_VERDICT}`

---

## 8. [profile · 可选] 债务评分台账（吸收 debt-repayment）

> 仅当本快照是债务盘点时启用。逐条债务打分 + 排序 + closure 判据。

| 编号 | 债务 | 内聚 | 紧急 | 复杂 | 风险 | 价值 | 建议顺序 |
|------|------|------|------|------|------|------|----------|
| `{ID}` | `{DEBT}` | `{H/M/L}` | `{H/M/L}` | `{H/M/L}` | `{H/M/L}` | `{H/M/L}` | `{ORDER}` |

- **closure 判据 / DAG**：`{CLOSURE_CRITERIA_OR_DAG}`

---

## 附录

### A. 复现命令

```bash
{GREP_OR_TEST_COMMANDS_TO_REPRODUCE_EVERY_CLAIM}
```

### B. 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | `{DATE}` | `{AUTHOR}` | 初稿 |
