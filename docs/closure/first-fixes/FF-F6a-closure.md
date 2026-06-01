# [FF-F6a / Clean 执行器去桩] Closure

> 阶段: `first-fixes/FF-F6a — Clean 执行器去桩与能力补全`
> 范围: `action registry 分派 + universal htmlCrawl 真抓取清洗 + dedicated chinatax 真 ETL + browser/PDF/多 provider/scatter 显式 degraded（F6-01/01b/02/03/08/DG）`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-06-01` · 作者: `Opus 4.8`
> 关联 charter: `docs/design/first-fixes/initial-planning-by-opus.md（§6.6 F6 绑定表 / §4 红线第 2 条 / §2.C [Q3]）`
> 关联 design: `N/A（消费冻结 [Q3][Q7] + F3-02 契约，不新开 Q/A）`
> 关联 action-plan: `docs/action-plan/first-fixes/FF-F6a-cleaners.md（§11 执行日志已回填）`
> 关联 evidence: `inline §2 + AP §11.3 四元组表`
> 关联 review: `docs/eval/first-code-review-plan/part-cr-6.md（G-CR6-01/02/04/09）+ part-cr-4.md（R3 clean 侧）`

---

## 0. 一句话 verdict

> F6a 收口：clean 分派由 `CleanActionRegistry`(branch→handler) 驱动（创建侧写 action_branch、执行侧据此选 handler、list_actions 可枚举含 degraded 标记），消除 `provider or universal` if/else 硬选；universal `htmlCrawl` 真抓取（UA/超时/状态码/UrlFetchError 分类 + stdlib html.parser 去标签保正文，删 URL-当正文兜底）、dedicated `chinatax` 真 ETL（真发请求/解析结构化 items，删字符串前缀桩）；browser/PDF/LLM/多 provider/scatter 显式 degraded（抛带 reason 的 DegradedActionError、list_actions 标记）；clean 执行器 F3-02 契约（无自提交/重放安全，grep gate + 重放测试守护）；先红后绿 24 用例，全量 137→**161 passed**（exit 0）；close-type=closed-with-explicit-deferrals。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. htmlCrawl **SSRF 面**（url 可指向内网）本轮未防护 → follow-up 交 FF-F6c/下一轮安全。
> 2. browser/PDF/LLM/多 provider/scatter 为 [Q3] 显式 degraded（非已实现）；端到端 clean→rag→search 语义命中交 F7 capstone。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + test + run-time） |
|------|------|----------------------------------------|
| F6-01 action registry + 分派 + 创建侧写 action_branch + list_actions | ✅ | `2dbceab + test_clean_action_registry(5) + test_clean_contract_and_dispatch(无硬选 gate) + 2026-06-01 03:52 UTC` |
| F6-01b clean 执行器 F3-02 契约（无自提交/重放安全） | ✅（主体由 F3 交付，本 AP 复核+测试守护） | `2dbceab + test_clean_contract_and_dispatch(无自提交 gate + 重放安全) + 2026-06-01 03:52 UTC` |
| F6-02 universal htmlCrawl 真抓取清洗（去标签保正文/UA/超时/错误分类） | ✅ | `2dbceab + test_html_crawl_extract(5) + test_html_crawl_fetch(4) + 2026-06-01 03:52 UTC` |
| F6-03 dedicated provider registry + chinatax 真 ETL | ✅ | `2dbceab + test_provider_registry(5) + p3 test_chinatax(注入) + 2026-06-01 03:52 UTC` |
| F6-08 finalizer scatter/多文档源 显式 degraded | ✅ | `2dbceab + test_clean_contract_and_dispatch::test_scatter_multi_document_degraded + 2026-06-01 03:52 UTC` |
| F6a-DG browser/PDF/多 provider degraded（带 reason + list_actions 标记） | ✅ | `2dbceab + test_clean_action_registry::{test_degraded_handler_raises_with_reason,test_list_actions_marks_degraded} + 2026-06-01 03:52 UTC` |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| registry 分派 + 无硬选 + 能力发现 | `pytest tests/unit/test_clean_action_registry.py` | `5 passed`；register/get/未知抛 UnknownActionError/默认真实 branch/degraded 标记 | CleanActionRegistry |
| 无 if/else 硬选 + 无自提交（drift gate） | `test_clean_contract_and_dispatch.py`（读 service 源码断言） | `or clean_payload`/`maybe_clean_with_provider`/`status='succeeded'`/`conn.commit()`/`CURRENT_TIMESTAMP` 0 命中 | clean service 契约 |
| 重放安全（确定性 id） | `test_clean_replay_safe_deterministic_artifact` | 重复 process_clean_step → 1 cleaned_text artifact | F3-02 / G-CR4-03 clean 侧 |
| htmlCrawl 去标签保正文 | `pytest tests/unit/test_html_crawl_extract.py` | `5 passed`；无残留标签/丢 script-style/解码实体/保段落（≥3 段）| html.parser 提取 |
| htmlCrawl 抓取错误分类 | `pytest tests/unit/test_html_crawl_fetch.py` | `4 passed`；注入抓取/错误传播 UrlFetchError/不回退 URL 当正文/空抽取抛错 | fetch_url + html_crawl |
| chinatax 真 ETL | `pytest tests/unit/test_provider_registry.py` + p3 注入集成 | `5 passed`；解析结构化 items/错误分类/registry 路由 + degraded；无 `[provider:chinatax]` 前缀 | ProviderRegistry + chinatax_etl |
| degraded 显式抛错 | `test_degraded_handler_raises_with_reason` + scatter | browser/PDF/gemini/domain/realestate/scatter 抛 DegradedActionError(reason) | F6-08 / F6a-DG |
| 全量回归 + 桩测 fork | `python3 -m pytest tests/` | `161 passed`（exit 0；137+24）；p3-1/p4/p5 fork 为注入真实链路 | 全仓 |

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| registry 分派 + 无硬选 + action_branch + 可枚举 | grep 0 命中 + 单测过 | T01/T02 绿 | ✅ PASS |
| clean 执行器无自提交 + 重放安全 | grep 0 命中 + 重复执行 1 artifact | T03 绿 | ✅ PASS |
| htmlCrawl 真抓取 + 去标签保正文（先红后绿）+ chinatax 真 ETL | 桩对保段落/实体/真发请求红 → 新绿 | T04/T05/T07/T08 绿 | ✅ PASS |
| browser/PDF/多 provider/scatter 显式 degraded（reason，无装成完成的桩） | 调用抛 DegradedActionError + list_actions 标记 | T06/T09/T10 绿 | ✅ PASS |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| browserFetch/browserPDF/geminiUnderstanding（浏览器/PDF/LLM） | A（[Q3] degraded OOS） | 注册 degraded handler 抛 reason | 下一轮接 playwright/PDF 库/LLM | 下一轮 |
| domain/realestate 多 provider | A（[Q3] degraded OOS） | registry degraded handler | 产品需要时按 registry 扩展 | 下一轮 |
| finalizer scatter/child files 多文档源 | A（[Q3] OOS） | child_files>0 抛 DegradedActionError；单文档源正常 | chinatax 等需散射多文档时 | 下一轮 |
| cleaned_text 落 ObjectStore（CR-6 R5） | B（主动 defer） | 现状 sqlite_ref 内联 | F4 路径安全协调后 | 下一轮 |
| htmlCrawl SSRF 防护（url 指向内网） | C（handoff） | 本轮未防护，记 follow-up | `FF-F6c` / 下一轮安全 | F6c/安全 |
| 端到端 clean→rag→search 语义命中 capstone B/C 步 | C（handoff） | 依赖 F6b rag 去桩 + F5 embedding | `FF-F7` capstone | F7 |
| p3 桩固化等值断言全面重写 | C（handoff） | 本 AP 已 fork p3-1/p4/p5 为真实链路；其余 p3 桩断言重写 | `FF-F7-03` | F7 |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态 | ✅ — §1 全部 **verified**（commit + test + run-time 四元组齐全，先红后绿可证；F6-01b 主体 F3 交付，本 AP 复核+gate 守护） |
| ✅ 证据为四元组，无裸 file:line | ✅ |
| scope diff 守卫（仅改 in-scope 文件，无越界） | ✅ — 改 browser_runtime/cleaners_universal/providers_dedicated/workflow_clean(+registry 新)/ingestion，均在 §3 工作总表 + §7.1 锚表内；3 个桩时代集成测试 fork（§8.2 预期） |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ — §4 七项均标 A/B/C + 承接位置 + 责任方 |
| owner-test 项未经复测标 ⏸ | N/A — 无 owner-test 项（均本地可复现，真实网络 monkeypatch 注入） |

> **诚实附注**：
> 1. **F6-01b 主体由 F3 交付**：clean 执行器迁 ExecutorResult 契约（无自提交/commit）在 FF-F3 已完成；本 AP 仅复核（grep gate 守护 0 自提交）+ 新增重放安全测试，未重复实现。如实标注，不冒领 F3 工作。
> 2. **registry handler 为内容层（非每 handler 返 ExecutorResult）**：忠实适配 F3 既有的"process_clean_step 单点组装 ExecutorResult + 确定性 artifact 写入"，保持终态单一归属、改动面最小。见 AP §11.4。
> 3. **degraded 用正向断言而非 xfail 占位**：断言 degraded handler 真抛 `DegradedActionError(reason)`，强于 xfail（验证 degraded 契约真实生效，杜绝"桩被当成完成"，⛔2）。
> 4. **桩时代测试 fork 是真实化而非掩盖**：p3-1/p4/p5 原靠"离线 fetch 失败把 URL 当正文"的桩兜底（删兜底后实测 404 fail-loud）；fork 为 monkeypatch 注入本地 HTML/JSON 的真实 htmlCrawl/chinatax 测试（更强断言，不打外网 ⛔6）。
> 5. 全量 161 passed 含 F1-F5 既有 137 用例无回归。
