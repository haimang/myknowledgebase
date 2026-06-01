# [FF-F7 / 测试有效性重建与 closure 重定级] Closure

> 阶段: `first-fixes/FF-F7 — 测试有效性重建与 closure 重定级`
> 范围: `测试原语 + 去夹具掩盖 + capstone A–J + closure 重定级 + 断言强度门禁（F7-01..06）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md（§6.7 F7 / §8 capstone / §4 防假绿）`
> 关联 design: `N/A（消费冻结 [Q7] test-first + 断言门禁 + 禁夹具掩盖）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F7-test-integrity.md（§11 已回填）`
> 关联 evidence: `inline §2 + AP §11.3`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-8.md（R1/R2/R5/R8 结构性假绿）`

---

## 0. 一句话 verdict

> F7 收口：建可复用测试原语（5 类 + self-test 防原语假绿）；去 part-cr-8 R2 夹具掩盖（`test_kernel_flow` 删 SQL strftime 手写覆盖 → 真实 SSOT `add_seconds_iso`，grep 0 命中）；填 e2e capstone A–J（语义+完整性，PDF/浏览器步 [Q3] degraded xfail）；closure 重定级（更正 FF-F1 "fastapi 缺失" 误诊 + 5 份 initial-refactor closure 陈旧 `14 passed` 作废 + gate 据真实断言重定级 retrieval→degraded[Q1]）；断言强度门禁脚本（仅弱断言测试 CI 失败，self-test + 全套件 44 文件 0 命中）；全量 192→**203 passed + 1 xfailed**（exit 0）。F7 多项已在 F4-F6c 提前交付（如实复核）。close-type=closed-with-explicit-deferrals。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. 断言门禁脚本+self-test 已落地，但**接入 CI 配置**为 follow-up（本环境无 CI runner）。
> 2. capstone 的 PDF/浏览器/多 provider 步、真实 vec0 向量真实性为 [Q1][Q3] degraded（xfail），交下一轮。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| F7-01 测试原语供给（5 类 + self-test） | ✅ | `f878165 + test_f7_primitives(5) + 2026-06-01 04:20 UTC` |
| F7-02 去夹具掩盖（reap 走真实 SSOT，0 手写 SQL） | ✅ | `f878165 + test_expired_claim_can_be_reclaimed + grep strftime 0 命中 + 2026-06-01 04:20 UTC` |
| F7-03 去桩固化断言（随 F6a 完成，本阶段复核） | ✅ | `2dbceab(F6a) + p3/p4/p5 真实链路语义断言 + 2026-06-01 04:20 UTC` |
| F7-04a tests/unit 填充（F4-F6c 累积 + F7） | ✅ | `f878165 + pytest tests/unit 真实断言 + 2026-06-01 04:20 UTC` |
| F7-04b e2e capstone A–J | ✅ | `f878165 + test_first_fixes_capstone(语义+完整性) + degraded xfail + 2026-06-01 04:20 UTC` |
| F7-05 closure 重定级（FF-F1 fastapi + 5 closure 计数/gate） | ✅ | `f878165 + 重定级附记 + grep "14 passed" 仅在更正注内 + 2026-06-01 04:20 UTC` |
| F7-06 断言强度门禁 | ✅ | `f878165 + test_assert_strength_gate + 44 文件 0 命中 + 2026-06-01 04:20 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 测试原语 self-test | `pytest tests/unit/test_f7_primitives.py` | `5 passed`；每原语喂应成功/应失败双向 | primitives |
| 去夹具掩盖 | `grep -rn "strftime.*lease_expires_at" tests/` | `0 命中`；reap 走 `add_seconds_iso(-1)` 真实 SSOT | test_kernel_flow |
| e2e capstone | `pytest tests/e2e/test_first_fixes_capstone.py` | `1 passed + 1 xfailed`；A-J 语义+完整性，degraded xfail | 全链 + 隔离 + purge + 路径遍历 |
| 断言强度门禁 | `python3 tools/scripts/check_assert_strength.py tests/` + `pytest tests/unit/test_assert_strength_gate.py` | `44 文件 0 命中` + `5 passed`（弱-only 报 / 弱前置+强 过 / is None 不误报） | 门禁脚本 + self-test |
| closure 重定级 | `grep "14 passed" docs/closure` | 仅出现在 F7-05 更正注内（已标作废）；FF-F1 fastapi 误诊更正 | P3-P7 + FF-F1 |
| 全量回归 | `python3 -m pytest tests/` | `203 passed + 1 xfailed`（exit 0；192+11） | 全仓 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| capstone A–J 端到端语义（degraded xfail，G 步向量命中） | 语义+完整性断言通过 | capstone PASS + PDF/浏览器 xfail | ✅ PASS |
| 断言强度门禁生效且全套件过关 | 仅弱断言被拒 + 全套件 0 命中 | self-test PASS + 44 文件 0 命中 | ✅ PASS |
| closure 无陈旧计数当证据，gate 据真实断言重定级 | 14 passed 作废 + 重定级 | 5 closure + FF-F1 更正 | ✅ PASS |
| test_kernel_flow 无手写 SQL 时间覆盖 | grep 0 命中 | 0 命中 ✓ | ✅ PASS |
| 5 类原语 self-test PASS | 每原语双向自检 | test_f7_primitives 5 passed | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| 断言门禁接入 CI 配置 | C（handoff） | 脚本+self-test+全套件过关已落地；CI step 未接 | 有 CI runner 时接 pre-commit/CI | 平台/下一轮 |
| 真实 vec0/外部 embedding 向量真实性 | A（[Q1][Q2] degraded OOS） | 本地 1536 + 暴力 cosine；capstone G 用 degraded 断言 | 生产化阶段 | 下一轮 |
| PDF/浏览器/多 provider 真实样本 e2e | A（[Q3] degraded OOS） | capstone 对应步 xfail(strict)+reason | 接真实实现时 | 下一轮 |
| soak/长稳竞态 ×N | B（主动 defer） | 一次性双 worker 竞态已覆盖（F3/F6b 重放幂等） | 后继质量门禁迭代 | 下一轮 |
| P0/P1/P2 closure gate 结论重定级 | A（part-cr-8 R5 仅点名 P3/P5/P7） | 仅纠计数 | 某 phase 收口暴露其 gate 假绿时 | 下一轮 |
| htmlCrawl SSRF（F6a/F6c handoff） | C（handoff） | 仍未处置 | 下一轮安全 | 安全/下一轮 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ — §1 全部 **verified**（commit + test + run-time 四元组齐全；F7-03/04a 标注为 F4-F6c 提前交付的复核） |
| ✅ 证据为四元组，无裸 file:line | ✅ |
| scope diff 守卫（仅改 in-scope 文件，无越界） | ✅ — 改 tests/fixtures(+primitives)/tests/unit/tests/e2e/test_kernel_flow/tools/scripts + closure 文档，均在 §3 工作总表 + §7.1 锚表内 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ — §4 六项均标 A/B/C + 承接位置 |
| owner-test 项未经复测标 ⏸ | N/A — 无 owner-test 项 |

> **诚实附注**：
> 1. **F7 多项提前在 F4-F6c 交付，如实复核非重做**：F7-03 桩固化重写随 F6a 完成；F7-04a unit 填充随 F4-F6c 累积；向量真实性原语随 F5。本阶段对这些据实标注覆盖来源，不冒领为 F7 新工作。
> 2. **去夹具掩盖用真实 SSOT 路径而非时钟注入**：内核 `now_iso()` 读真实墙钟、无时间注入接口；沿用 F3 已确立的 `add_seconds_iso(-1)`（真实 SSOT Python 写路径，非 SQL strftime 手写）作为去掩盖范式——根除 part-cr-8 R2 的"SQL 手写正确格式绕过 now_iso"，grep 0 命中。
> 3. **FF-F1 "fastapi 缺失" 是误诊，已更正**：F1 会话误把 PEP-668 读为"无 fastapi"；实测 p2-p7+api smoke 全运行（203 passed）。F7-05 在 FF-F1 closure 追加更正附记，p2-p7 从"未观察"改为 verified——这是 part-cr-8 R5"陈旧/错误结论当证据"教训的同源纠偏。
> 4. **门禁 self-test 防门禁假绿**：断言门禁本身有 self-test（弱-only 必报、is None/== "" 不误报），避免门禁自身成为新的假绿点。
> 5. 全量 203 passed + 1 xfailed 含 F1-F6c 既有 192 用例无回归。
