<!--
═══════════════════════════════════════════════════════════════════════════
 模板使用说明区（META）—— 起草人/agent 必读；输出落盘前删除「剪切线」以上全部内容
═══════════════════════════════════════════════════════════════════════════

这是 nano-agent 通用 closure 模板。一份 closure 的价值 = 让 owner 和下游作者各自少问问题：
  · 对 owner（人）：30 秒判断「收口了吗 / 有没有骗我 / 还欠什么」
  · 对文档系统（下游作者）：kickoff 时读哪些 / 在什么 contract 上施工 / 哪些不能动

────────────────────────────────────────────────────────────────────────────
【第 1 步】选择档次（closure 不是一种东西，是三种规模）
────────────────────────────────────────────────────────────────────────────
  ▸ 子阶段 closure（sub-phase）  —— 单个 P*/W*/BN*/MI* 收口。保留 §0–§5。删除 §6–§9 全部。
  ▸ 阶段 final closure           —— 一个 charter 全部 phase 合拢。保留 §0–§7。视情况留 §8。
  ▸ grand consolidated           —— 多个 charter 回溯。保留全部 §0–§9。

  每个章节标题下的 `<!-- [档次: …] -->` 注释标明该节适用档次与必含/可选。
  不适用本档次的整节，连同其注释一起删除。

────────────────────────────────────────────────────────────────────────────
【第 2 步】填写纪律（这是 closure 与「自我表扬」的区别）
────────────────────────────────────────────────────────────────────────────
  1. close-type 必须使用统一 taxonomy，且与 §0 verdict 一致：
       · full-close                                      —— 本阶段 scope 全部 verified，无 known-issue / deferred / pending gate
       · closed-with-explicit-deferrals                  —— 代码/文档 scope done，但有显式推迟到下游的承诺（带 owner/trigger）
       · close-with-known-issues                         —— 可收口，但仍有显式 known gap / partial proof / bounded debt
       · implementation-complete-awaiting-live-verification —— 代码实现完成，但 charter hard gates 仍需 live / D1 / owner-test 验证
     旧 closure 可保留历史用语；新 closure 必须从上述 4 类选择，不再混用 freeform close 语义。
  2. 每个 ✅ 必须归类为「诚实收口 5 态」之一（见 §5），不允许无归类的 ✅：
       · verified              —— commit + D1 query/test + spike name + run-time 四元组齐全
       · observed-OK-at-closure—— 收口时刻 snapshot 正常，但未做 long-run soak（dev 阶段允许）
       · partial               —— A 级证据不全；必须列出缺什么 + handoff 给谁
       · 未观察                 —— 收口时刻无法主动 reproduce（long-outage / multi-tab race 等）
       · deferred              —— carry-over 到后续 phase；必须列出承接位置
     价值台账推荐 5 级证据标注：
       · ✅ live-verified      —— live / D1 / owner-test 等目标证据已完成
       · 🟢 short-verified     —— 本地 short/unit/type/docs gates 已完成，但不宣称 live
       · 🟡 partial            —— 仅完成一部分或证据不足
       · ⏸ live-pending        —— 代码存在，但 live/D1/owner gate 未跑或未闭
       · ❌ missing            —— 计划内能力未实现
  3. ✅ 的证据用四元组，不允许仅 file:line：
       (commit `abc1234` + query/test `SELECT … / foo.spike.test.mjs` + run-time `2026-MM-DD HH:MM UTC`)
  4. deferred 必须分三类：A=charter 未承诺(OOS) / B=本阶段主动 defer / C=handoff 给下游。
  5. 不允许「我修了」未经验证就标 ✅；未经 owner 复测的 owner-test 项标 ⏸ PENDING + 显式 handoff。

────────────────────────────────────────────────────────────────────────────
【第 3 步】输出前自检
────────────────────────────────────────────────────────────────────────────
  □ 「剪切线」以上全部删除（本 META 区块不得出现在产物里）
  □ 所有 `<!-- … -->` 注释删除（它们只给你看，不进产物）
  □ 所有 `{TOKEN}` 占位替换为真实内容（grep `{` 应只剩正文里的代码花括号）
  □ 不适用本档次的整节已删除
  □ §0 verdict 的 close-type 与 frontmatter 的 close-type 字面一致，且属于统一 taxonomy
  □ 每个 ✅ 都能在 §5 找到 5 态归类

  存放位置：docs/issue/{phase-cluster}/{phase-id}-closure.md
  命名：见 docs/issue/README.md（`{action-plan-id}-{slug}.md`）
═══════════════════════════════════════════════════════════════════════════
       ↓↓↓  剪切线 —— 你的 closure 从下一行开始  ↓↓↓
═══════════════════════════════════════════════════════════════════════════
-->

# [{PHASE_ID} / {SHORT_TITLE}] Closure

> 阶段: `{CHARTER}/{PHASE_ID} — {PHASE_NAME}`
> 范围: `{SCOPE}` <!-- 例: 单 work-item / P1–P6 / charter 全 phase 合拢 -->
> Close-type: `full-close | closed-with-explicit-deferrals | close-with-known-issues | implementation-complete-awaiting-live-verification` <!-- 四选一，删除其余三个 -->
> 状态: `closed | close-with-known-issues | implementation-complete-awaiting-live-verification`
> 日期: `{DATE}` · 作者: `{AUTHOR}`
> 关联 charter: `{CHARTER_PATH}`
> 关联 design: `{DESIGN_PATH_OR_NA}` <!-- charter-lite 阶段无 design 写 N/A -->
> 关联 action-plan: `{ACTION_PLAN_PATH}`
> 关联 evidence: `{EVIDENCE_DOC_OR_INLINE}` <!-- evidence 量大时拆独立文件并在此引用；量小时写「inline §2」 -->
> 关联 review: `{REVIEW_DOC_OR_NA}`

---

## 0. 一句话 verdict

<!-- 说明: 这是全文件被读最多的一行。一句话回答：收口了什么 + close-type + 最关键的 1-3 个 known gap。不写背景。 -->

> {ONE_LINE_VERDICT}

<!-- [档次: 全档可选] 若有对下游影响最大的 known gap，在此列 1-3 条；无则删除本块 -->
> **本阶段最关键的 known gap（对下游影响）**：
> 1. `{GAP_1}`
> 2. `{GAP_2}`

---

## 1. 工作项收口表

<!-- 金表格①｜[档次: 全档必含]｜逐项 red→green。证据列用四元组（见 META 第2步纪律3）。状态用 ✅ closed / 🟡 partial / ⏸ pending / ❌。 -->

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| `{ITEM_1}` | ✅ | `{EVIDENCE_QUADRUPLE_1}` |
| `{ITEM_2}` | 🟡 partial | `{EVIDENCE_2}` —— 缺 `{WHAT_MISSING}`，handoff → `{WHERE}` |

---

## 2. Evidence / Validation 矩阵

<!-- 金表格③｜[档次: 全档必含]｜可复现证明。命令/证据列必须是能被下游原样重跑的东西（命令、D1 query、deploy version id、test 计数）。 -->

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| `{CHECK_1}` | `{CMD_OR_ARTIFACT_1}` | `{RESULT_1}` | `{SCOPE_1}` |
| `{CHECK_2}` | `{CMD_OR_ARTIFACT_2}` | `{RESULT_2}` | `{SCOPE_2}` |

<!-- [档次: 全档可选] 关键 deploy/部署证据（preview version id 等）单列一张小表，便于下游核对 live 真相 -->

---

## 3. Hard-gate 判定

<!-- 金表格②｜[档次: 有 gate 才含；无显式 gate 的子阶段删除整节]｜二元出口闸。判定用 ✅ PASS / ⚠ PARTIAL / ❌ FAIL / ⏸ PENDING，每行给具体实测证据。 -->

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| `{GATE_1}` | `{CRITERION_1}` | `{ACTUAL_1}` | `{✅/⚠/❌/⏸}` |

---

## 4. Deferred / Carry-over ledger

<!-- 金表格④｜[档次: 全档必含]｜防隐藏债 + 前向链接。类型三分类：A=charter 未承诺(OOS) / B=本阶段主动 defer / C=handoff 给下游。每项必须有承接位置与责任方。 -->

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| `{DEFERRED_1}` | `A/B/C` | `{STATUS_1}` | `{NEXT_PHASE_OR_TRIGGER_1}` | `{OWNER_1}` |

---

## 5. 诚实收口声明

<!-- [档次: 全档必含]｜把 §1 / §3 里的每个 ✅ 归类为 5 态之一。这是 closure 区别于自我表扬的核心纪律。 -->

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred）| `{✅/⚠/❌}` |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | `{✅/⚠/❌}` |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改）| `{✅/⚠/❌}` |
| deferred 已三分类（A/B/C）且每项有承接位置 | `{✅/⚠/❌}` |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无「我修了」式宣称）| `{✅/⚠/❌/N/A}` |

<!-- [档次: 全档可选] 若有 ✅ 因 dev-phase 约束取不到四元组，在此逐条显式归类为 observed-OK / partial / 未观察 之一 -->

---

<!-- ════════ 以下为扩展块：子阶段 closure 删除 §6–§9 全部 ════════ -->

## 6. Handoff / 下阶段 entry-gate 预核对

<!-- 金表格⑤｜[档次: stage-final+ 必含；子阶段删除整节]｜让下阶段作者能判断「可否启动」。逐条列下阶段的 entry-gate 条件与当前满足状态。 -->

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| `{ENTRY_COND_1}` | `✅/⏸` | `{NOTE_1}` |

<!-- [档次: stage-final+ 可选] 下阶段 kickoff checklist：下阶段第一个 PR body 应包含的决策项 -->
**下阶段 kickoff checklist**：
- [ ] 引用本 closure 作为 single truth anchor
- [ ] `{KICKOFF_DECISION_1}`

---

## 7. Cross-cut 不变量（0-drift 确认）

<!-- [档次: 有硬约束的阶段才含；否则删除整节]｜逐条确认本阶段未漂移的硬约束（wire vocabulary / tenant wrapper / 协议版本 等），附 grep/查询证据。 -->

| 不变量 | 状态 | 证据 |
|--------|------|------|
| `{INVARIANT_1}` | `✅ 保持` | `{PROOF_1}` |

---

<!-- ════════ 以下为 grand consolidated 专属：仅多 charter 回溯时保留 §8–§9 ════════ -->

## 8. 价值 / 负债台账

<!-- [档次: 仅 grand]｜跨阶段回溯时汇总真实价值与背上的债。负债用 severity 🔴 blocking / 🟡 structural / 🟢 maintenance。 -->

**价值台账**

| 章节 | 真实价值 | 状态 |
|------|----------|------|
| `{PHASE_X}` | `{VALUE_X}` | `{STATUS_X}` |

**负债台账**

| # | 负债 | 级别 | 来源 | 消化路径 |
|---|------|------|------|----------|
| 1 | `{DEBT_1}` | `🔴/🟡/🟢` | `{SOURCE_1}` | `{REMEDIATION_1}` |

---

## 9. Closing statement + 定位裁定

<!-- [档次: 仅 grand]｜叙述为什么做这一组阶段、共同 DNA、整合价值裁定。子阶段/stage-final 不需要叙事段落。 -->

`{CLOSING_NARRATIVE}`

---

## 修订历史

<!-- [档次: 多次 append / 复审才需；一次性收口可删除整节]｜每次 owner/reviewer 复审后的口径修正记一行。 -->

| 版本 | 日期 | 作者 | 变更 |
|------|------|------|------|
| `r1` | `{DATE}` | `{AUTHOR}` | 初闭合 |
