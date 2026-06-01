# [FF-F3 / 内核恢复与一次性语义] Closure

> 阶段: `first-fixes/FF-F3 — 内核恢复与一次性语义（Kernel recovery & idempotency）`
> 范围: `F3-01..F3-09（单 sub-phase；关键路径 F1→F3→F6→F7 中段）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-05-31` · 作者: `Claude Opus 4.8 (1M context)`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md`
> 关联 design: `docs/design/first-fixes/owner-gated-qna.md（[Q4] recovery / [Q7] test-first）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F3-kernel-recovery.md`
> 关联 evidence: `inline §2 + action-plan §11 执行日志`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-4.md / part-cr-6.md / part-cr-7.md`
> 关联 commit: `2ff96cb`（fix(F3): 内核恢复 + 执行器契约 + 一次性语义 + recovery restart）

---

## 0. 一句话 verdict

> F3 收口：reap 接线到 worker 运行路径；**执行器契约**（`ExecutorResult` + `apply_executor_result`）把 step 终态/下游派生/run 推进/step_links 边收归内核 `succeed_claim`，在重查 claim active 后于同一 `BEGIN IMMEDIATE` 事务内落库——堵死过期租约竞态下的双重执行；restart 改 recovery 锚点模式（[Q4]）、退避读 schema 列指数化、删重复事件写入器；先红后绿 7 用例 + 全量 **65 passed**；close-type = closed-with-explicit-deferrals（force/kickstart restart 延后；跨库 vec 原子性 handoff F4）。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. `跨库 vec 写不在 core 事务内（仅 core 侧原子）→ FF-F4 协调`
> 2. `restart force/kickstart 全量面延后（本轮仅 recovery，已显式拒绝非 recovery mode）→ 后续轮次`

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| F3-01 reap 接线 worker | ✅ | `2ff96cb` + `test_t14`（reap=1）+ `2026-05-31`；grep `reap_expired_claims` 在 worker 2 处 |
| F3-02 终态归属内核 + 执行器契约 | ✅ | `2ff96cb` + `test_t06`（step succeeded/run advance/step_links 由内核写）+ `2026-05-31`；grep clean/rag `conn.commit`=0、`status='succeeded'`=0 |
| F3-03 幂等键 + 检查返回值 | ✅ | `2ff96cb` + `test_t07`（重复执行 artifact=1）+ `test_t14`（worker-A 迟到 succeed=False）+ `2026-05-31` |
| F3-04 restart available_at SQL | ✅ | `2ff96cb` + `test_t09`（rag step available_at ≤ now、就绪）+ `2026-05-31` |
| F3-05 restart recovery 模式 | ✅ | `2ff96cb` + `test_t09`（clean 不重置/rag 锚点重启）+ `test_t10`（force 拒绝）+ `2026-05-31` |
| F3-06 退避读 schema 列 + 指数 | ✅ | `2ff96cb` + `test_t11`（无显式退避→读 120s 列、available_at 未来 >60s）+ `2026-05-31` |
| F3-07 删重复事件写入器 + created_at DDL | ✅ | `2ff96cb` + `test_t12`（graph.write_workflow_event 不存在 + created_at `...SS.mmmZ`）+ `2026-05-31` |
| F3-08 workflow_step_links 接线 | ✅ | `2ff96cb` + `test_t06`（每条 downstream 写 1 条 next 边）+ `2026-05-31` |
| F3-09 并发双重执行 harness | ✅ | `2ff96cb` + `test_t14`（真实 now_iso lease 路径，at-most-once）+ `2026-05-31` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| F3 回归用例 | `python3 -m pytest tests/integration/p1_kernel_closure/test_kernel_recovery.py -q` | `7 passed in 0.23s` | F3-01..09 |
| 全量回归 | `python3 -m pytest tests/ -q` | `65 passed`（exit 0） | 全仓 |
| 执行器无终态/自提交 | `grep -c "conn.commit"` clean/rag service / `grep -c "status='succeeded'"` | `0 / 0` 两文件 | F3-02 |
| 单一事件写入器 | `grep -c "def write_workflow_event" graph.py` | `0` | F3-07 |
| reap 运行路径接线 | `grep -c "reap_expired_claims" worker/main.py` | `2` | F3-01 |
| 一次性语义 | `test_t14`：worker-A 迟到 succeed_claim 返回 False，cleaned artifact=1 / rag step=1 | at-most-once 成立 | F3-02/03/09 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| 故障恢复（reap 命中）| reap 接线 + 过期 claim 回收 | worker 每轮 reap；负 lease claim 被回收、step 可重 claim | ✅ PASS |
| 一次性语义（at-most-once）| 并发双重执行无重复副作用 | worker-A 迟到 succeed=False；artifact/step 计数=1 | ✅ PASS |
| 终态单一归属内核 | clean/rag 0 终态写入/0 commit | grep 双 0；内核 succeed_claim 落终态 | ✅ PASS |
| restart recovery 生效 | 按失败 stage 锚点、available_at 就绪 | rag 失败 run recovery：clean 不动、rag 就绪 | ✅ PASS |
| restart force/kickstart | 本轮 [Q4] 延后 | 非 recovery mode 显式置 failed | ⏸ 延后（degraded 声明，非伪装） |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| `restart force/kickstart 全量面` | B (主动 defer) | 非 recovery mode 显式拒绝（failed + reason） | 后续轮次产品需要全量重启时 | 后继 |
| `跨库 vec 写 core 事务覆盖` | C (handoff) | core 侧原子；vec 写在执行器内（确定性 id 幂等） | FF-F4 跨库一致性 | F4 执行者 |
| `执行器真实业务能力去桩` | A (charter→F6) | F3 仅定职责边界/契约；htmlCrawl/structurize/construct 真实算法属 F6 | FF-F6a/F6b（建在此契约上） | F6 执行者 |
| `prompt_versions/provider_configs 接线` | A (charter→F6c) | 未触碰 | FF-F6c | F6c 执行者 |
| `step_attempts id 改 (step_id,attempt) / per-request 事务` | B (non-blocker defer) | 现 `attempt_{claim_id}` + INSERT OR REPLACE | 后续可靠性窗口 | 后继 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ —— F3-01..09 全部 `verified`（commit `2ff96cb` + 命名测试 + run-time + grep）。force/kickstart `deferred`（显式拒绝，非伪装桩）。 |
| ✅ 证据为四元组，无裸 file:line | ✅ —— 见 §1/§2 |
| scope diff 守卫 | ✅ —— 改动限于 workflow_core/{executors(新),retry,events,graph,restart,__init__}、workflow_clean/service、workflow_rag/service、worker/main + 新增 test_kernel_recovery.py + 本 closure + AP §11；未触 F1 engine/F2 api |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ —— 见 §4（A×2 / B×2 / C×1） |
| owner-test 项未经 owner 复测的标 ⏸ PENDING | N/A —— F3 无 owner-test/live gate |

> 诚实附注：
> 1. **契约形态偏差（据实记录）**：AP §4 设想"执行器产物也经 ExecutorResult.artifacts 交内核写"；实际落地为"执行器直接写**数据**副作用（artifact/chunk/vec/object）但用确定性幂等 id，内核只统管**终态/下游 step/step_links/run 推进**"。该形态同样满足红线"终态单一归属 + 反双重执行"（test_t14 证），且保留既有丰富 rag 逻辑、改动面更小。
> 2. **中间 bug 自查**：F3-06 退避一度把 `retry_backoff_seconds=None` 直注 SQL 致 `NOT NULL constraint failed: available_at`；已修为"读 schema 列 + 指数"，test_t11 守回归。
> 3. **先红后绿真实性**：test_t14 走**真实 now_iso lease 写入路径**（负 lease_seconds 使 claim 即过期），不手写 SQL 覆盖 lease_expires_at（吸取 G-CR8-02 夹具掩盖教训）。
> 4. **会话 IO**：执行期 bash/Read 显示层间歇截断/串读；最终结论以文件重定向 + 退出码 + git 持久态取证。
> 5. **据实更正（重启前自查）**：① 关联 commit 实际为 `2ff96cb`（早前误记 `2d289e9`，已全文更正）。② F3 执行器契约重构使 F1 的 `test_t05_clean_finished_at_no_current_timestamp` 一度变红（该测试直接调 `process_clean_step` 并断言 step=succeeded，旧契约下执行器自写终态、新契约下由内核写）——这是 F3 应同步更新而遗漏的测试，已据新契约修正（先 claim 再 `succeed_claim(...,result)`，断言内核写的 SSOT finished_at），全量回归 **65 passed**（exit 0），与本档 §1/§3 一致。③ 记账更正（2026-06-01 重启后复核）：早前一版注记曾把"65 passed"反向改成"66 passed"——那是错误的（虚高 1 个）；真实总数始终为 **65**（`pytest --co` 实测 65 个用例、无 skip/xfail/deselected，`test_t05` 单测 1 passed），现已改回 65 并与 §1/§3 统一。
