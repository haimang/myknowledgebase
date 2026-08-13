# [D08 / Legacy Clean 四域迁移] Closure

> 阶段: `baseline-dev/D08 — legacy clean capabilities → intake 四域迁移与接线`
> 范围: `D08-A01..A20；intake/api、intake/web、intake/pdf、intake/doc；contracts/runtime/workflow/registry/semantics/e2e 附加更新`
> Close-type: `closed-with-explicit-deferrals`
> 状态: `closed`
> 日期: `2026-08-13` · 作者: `Codex (/root)`
> 关联 charter: `docs/baseline/domain-truth/D08-legacy-capabilities-migration.md`
> 关联 design: `docs/baseline/domain-truth/D08-legacy-capabilities-migration.md §3–§4`
> 关联 action-plan: `docs/baseline/domain-truth/D08-legacy-capabilities-migration.md §4；docs/baseline/domain-truth/D07-v1-acceptance-truth.md §7.D08`
> 关联 evidence: `inline §2`
> 关联 review: `docs/baseline/domain-truth/D07-v1-acceptance-truth.md；owner review pending`

---

## 0. 一句话 verdict

> D08 的 API/Web/PDF/Doc 四域迁移、精确 Process 接线、语义持久化与 D07-E2E-16..18 已在当前工作区全部实现并通过 230 项全量回归，以 `closed-with-explicit-deferrals` 收口；未提交 worktree、D04 proposed 三表、live vendor 接入及 owner freeze 均显式留在后续边界内。

> **本阶段最关键的 known gap（对下游影响）**：
> 1. D08 实现与本 closure 尚未形成独立 git commit；本文件的正向结论均归类为 `observed-OK-at-closure`，不得冒充 immutable `verified`。
> 2. `D08-v0.1` 仍为 `draft / owner-review`；本 closure 不代替 owner freeze，也不代替 `18` 的最终签署。
> 3. D04 proposed 三张 registry 表与 live registered-api vendor fetch 均不属于本次 required scope；未经 owner reopen/secret-ref/egress 设计不得自行落表或接入实网。

---

## 1. 工作项收口表

| Item | 状态 | 证据（commit + query/test + run-time） |
|------|------|----------------------------------------|
| API 域：三 provider × 三 operation 闭集、严格 raw schema、纯函数 parser、稳定 ExternalKey、双 digest | ✅ closed · `observed-OK-at-closure` | `commit/worktree: HEAD 02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/intake/test_api_chinatax.py tests/intake/test_api_domain.py tests/intake/test_api_realestate.py tests/unit/test_intake_provider_registry.py`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |
| API scatter：caller-frozen raw acquisition → map → seal → child，空集合 exhaustion 约束 | ✅ closed · `observed-OK-at-closure` | `commit/worktree: 486e17b/02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/e2e/test_registered_api_scatter.py`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |
| Web 域：结构化 sanitizer、删除元素闭集、属性白名单、deterministic/LLM/browser 显式策略 | ✅ closed · `observed-OK-at-closure` | `commit/worktree: e02c94a/02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/intake/test_web_clean.py tests/unit/test_intake_clean_dispatch.py`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |
| PDF 域：text-layer、document-understanding、OCR、browser-print-PDF 分流且无隐式降级 | ✅ closed · `observed-OK-at-closure` | `commit/worktree: 486e17b/02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/intake/test_pdf_clean.py tests/unit/test_intake_clean_dispatch.py tests/e2e/test_source_capability_paths.py`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |
| Doc 域：deterministic、document-understanding、OCR、Vision 分策略；图像禁 deterministic | ✅ closed · `observed-OK-at-closure` | `commit/worktree: e02c94a/02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/intake/test_doc_clean.py tests/e2e/test_source_capability_paths.py`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |
| Runtime/Workflow：runtime 仅经 `dispatch_clean`，线上图声明精确 clean Process key | ✅ closed · `observed-OK-at-closure` | `commit/worktree: e02c94a/486e17b/02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/unit/test_intake_clean_dispatch.py tests/unit/test_intake_source_capabilities.py`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |
| 附加更新：strategy/provider manifest digest、source-kind eligibility、五维 FilterMeta、Context tags、revision semantics | ✅ closed · `observed-OK-at-closure` | `commit/worktree: HEAD 02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/unit/test_intake_provider_registry.py tests/unit/test_intake_source_capabilities.py tests/e2e/test_registered_api_scatter.py`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |
| Prompt A：LLM clean 只读取冻结 ConfigSnapshot 指针，正文与 SHA-256 不一致时 fail-closed | ✅ closed · `observed-OK-at-closure` | `commit/worktree: HEAD 02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/unit/test_prompt_hash_mismatch.py tests/intake/test_web_clean.py tests/intake/test_pdf_clean.py tests/intake/test_doc_clean.py`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |
| Architecture/文档：删除 duck-type mapper，禁止 legacy import/vendor URL SSOT，回填 D08 Appendix 实现见证 | ✅ closed · `observed-OK-at-closure` | `commit/worktree: HEAD 02b141e + 未提交 D08 diff`；`test: .venv/bin/pytest -q tests/unit/test_intake_provider_registry.py && .venv/bin/ruff check . && git diff --check`；`result: pass`；`run-time: 2026-08-13 02:10 UTC`。 |

---

## 2. Evidence / Validation 矩阵

| 验证项 | 命令 / 证据 | 结果 | 覆盖范围 |
|--------|-------------|------|----------|
| 四域 + D08 聚焦回归 | `.venv/bin/pytest -q tests/intake tests/unit/test_intake_clean_dispatch.py tests/unit/test_intake_provider_registry.py tests/unit/test_intake_source_capabilities.py tests/unit/test_prompt_hash_mismatch.py tests/e2e/test_registered_api_scatter.py tests/e2e/test_source_capability_paths.py` | `57/57 passed，exit 0` | 三 provider、Web、PDF、Doc、runtime dispatch、source eligibility、Prompt A、E2E-16..18。 |
| 全量回归 | `.venv/bin/pytest -q`；测试收集数由 `.venv/bin/pytest --collect-only -q` 核对 | `230/230 passed，exit 0` | 当前仓库 unit/domain/e2e 全集。 |
| 仓库级静态检查 | `.venv/bin/ruff check .` | `All checks passed，exit 0` | 全部 Python 生产代码与测试。 |
| Diff 结构检查 | `git diff --check` | `pass，exit 0` | 当前 tracked D08 diff 无 whitespace/error marker。 |
| D08 禁用依赖扫描 | `rg -n "legacy-family|chinatax\\.sourcemind|services\\.realestate\\.com\\.au|cloudflare\\.com/client" intake src --glob '*.py'` | `无匹配；rg exit 1 为预期` | 无 legacy-family import；无 D08 禁止的生产 URL 常量。 |
| D04 闭集守卫 | `git diff --name-only -- src/persistence/migrations` | `空输出` | 未将 proposed 3 表冒充 required DDL；55 表闭集不变。 |
| Scope diff 快照 | `git diff --stat && git ls-files --others --exclude-standard` | closure 创建前为 `29 tracked paths，1165 insertions，318 deletions；15 untracked implementation/test paths`；本 closure 为新增第 16 个 untracked path | 变更均落在 D08 文档、四域 intake、contracts/runtime/services/workflows 与对应测试范围。 |

**证据时间与等级**：以上验证完成于 `2026-08-13 02:10 UTC`。由于实现尚未形成独立 commit，全部正向证据为 `🟢 short-verified / observed-OK-at-closure`，不声明 live vendor、长期 soak 或 owner acceptance。

---

## 3. Hard-gate 判定

| Gate | 判据 | 实测 | 判定 |
|------|------|------|------|
| `D08-A01` | 注册表恰含三个 versioned operation；未知键 fail-closed | `worktree@02b141e`；registry closed-set test；未知 operation 得 `CLEAN_PROVIDER_OPERATION_UNSUPPORTED`；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A02` | ChinaTax raw fixture 完成字段映射、有效性规则与双 digest | `worktree@02b141e`；`test_api_chinatax.py`；pass，且 `全文有效` 得 `is_active=1`；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A03` | Domain 扁平 address/price/geo/media 并应用 agency 对照表 | `worktree@02b141e`；`test_api_domain.py`；pass，且 `12106` 得 McGrath Box Hill；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A04` | REA 拍平 tieredResults、清除描述 HTML、sold/withdrawn inactive | `worktree@02b141e`；`test_api_realestate.py`；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A05` | schema/ExternalKey 失败形成 typed rejection，不 silent skip | `worktree@02b141e`；provider registry rejection test；pass，错误码 `CLEAN_MEMBER_SCHEMA_INVALID`；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A06` | 空集合仅在 exhaustion proof 存在时 complete | `worktree@02b141e`；no-proof seal unit + zero-member E2E；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A07` | FilterMeta 五维与 Context tags 进入 member/semantic，不只进 clean_text | `worktree@02b141e`；provider tests + scatter revision-semantics SQL assertion；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A08` | Web deterministic 使用结构 parser、删除标签与属性白名单，不调用 LLM | `worktree@02b141e`；Web sanitizer/domain tests；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A09` | Web LLM 先消毒再调用注入模型；缺模型 fail-closed | `worktree@02b141e`；Web LLM positive/negative tests；pass，缺模型得 `CLEAN_LLM_UNAVAILABLE`；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A10` | rendered 表示必须走 browser port；缺 browser fail-closed | `worktree@02b141e`；rendered/browser tests；pass，缺端口得 `CLEAN_BROWSER_UNAVAILABLE`；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A11` | print-PDF/HTTP PDF 不进入 HTML sanitizer | `worktree@02b141e`；forbidden-sanitizer monkeypatch dispatch test；pass，channel=`pdf`；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A12` | PDF 无文本层不得空成功；understanding 无 LLM fail-closed | `worktree@02b141e`；PDF text-layer/understanding positive/negative tests；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A13` | Doc understanding/OCR/Vision 独立；图像禁 deterministic | `worktree@02b141e`；Doc domain tests + image OCR workflow E2E；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A14` | Runtime clean 变换只委派 `dispatch_clean` | `worktree@02b141e`；runtime architecture source test + full suite；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A15` | HTTP/PDF/doc-LLM/API scatter workflow 声明精确 Process key | `worktree@02b141e`；workflow required-process-key tests；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A16` | 三 provider raw fixture 完成 scatter → map → seal 并带正确 binding evidence | `worktree@02b141e`；registered-api three-case E2E；pass，三个 Task 均 succeeded；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A17` | static Web 与 PDF strategy 通过 Task 终态可观测 | `worktree@02b141e`；source-capability E2E；pass，观察 `web.deterministic` 与 `pdf.text_layer`；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A18` | 无 legacy import 与禁止的 vendor URL SSOT | `worktree@02b141e`；architecture test + production `rg` scan；pass/no matches；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A19` | 三 member schema `extra=forbid` | `worktree@02b141e`；三 schema + public descriptor extra-field negatives；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D08-A20` | 同 raw + 同 operation version 产生相同 key 与双 digest | `worktree@02b141e`；provider idempotence test；pass；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |
| `D07-E2E-16..18` | API scatter、Web strategy、PDF strategy 形成 caller-observable 终态 | `worktree@02b141e`；两份 E2E test files；`6/6 passed`；`2026-08-13 02:10 UTC` | ✅ PASS · `observed-OK-at-closure` |

---

## 4. Deferred / Carry-over ledger

| 项 | 类型 | 当前状态 | 承接位置 / 触发条件 | 责任方 |
|----|------|----------|---------------------|--------|
| D08 实现与 closure 的独立 review/commit | `C` | 代码、文档、测试均在 worktree；本地 gates 全绿，但尚无承载完整实现的 commit SHA | review 当前 `git diff` 与 untracked 文件；确认 scope 后形成有界提交并重跑 §2 | repository maintainer / owner |
| D04 proposed 三张 provider/operation/strategy registry 表 | `B` | 明确保持 proposed；本轮没有 DDL/migration | 仅在 owner 正式 reopen D04、更新 55 表闭集与迁移计划后实施 | owner + schema maintainer |
| Live registered-api vendor fetch | `A` | 非 D08 P0；当前只支持 caller-frozen raw fixtures，禁止内置隧道/cookie/API key | 未来确认进入默认路径时，先完成 secret-ref、egress allowlist、request schema 与 redaction review | owner + security/integration maintainer |
| Live model/browser/vendor soak | `A` | D08 使用注入端口与 mock I/O 完成 CI/E2E；未声明真实 vendor 或长期 soak | 仅在 release profile 要求 P3/live 证据时执行，且不得改变 deterministic CI 判据 | release owner |
| D08 owner freeze 与 `18` 签署 | `C` | `D08-v0.1` 仍为 `draft / owner-review`；实现 Appendix 已回填但未升 accepted | owner review D08/D07/本 closure 后，由 `18` 完成 truth freeze 与跨域签署 | MKB owner |

---

## 5. 诚实收口声明

| 收口纪律 | 兑现声明 |
|----------|----------|
| 每个 ✅ 归类 5 态（verified / observed-OK-at-closure / partial / 未观察 / deferred） | ✅ §1 与 §3 的每个正向项均显式归类为 `observed-OK-at-closure`；没有把未提交实现标为 `verified`。 |
| ✅ 证据为四元组（commit + query/test + run-time），无裸 file:line | ⚠ 每项均给出 base commit/worktree、可重跑 test、结果和 UTC 时间；因实现尚未提交，commit 分量明确写为 `HEAD 02b141e + 未提交 D08 diff`，故证据等级不高于 observed-OK。 |
| scope diff 守卫（`git diff --stat` 与 in-scope 一致，无越界修改） | ✅ tracked 与 untracked 路径均已审计；只涉及 D08 文档、四域 intake、配套 contracts/runtime/services/workflows 与测试；`git diff --check` 通过。 |
| deferred 已三分类（A/B/C）且每项有承接位置 | ✅ §4 使用 A/B/C 分类，并为每项列出触发条件、承接位置和责任方。 |
| owner-test 项未经 owner 复测的标 ⏸ PENDING（无“我修了”式宣称） | N/A：D08 P0/P2 不要求 live owner-test；owner freeze 单独作为 §4 的 C 类 handoff，未宣称完成。 |

本 closure 没有 `live-verified` 项。当前可证明的是本地 unit/per-domain/E2E/full-suite 与 architecture gates 的短时绿灯；不能从这些证据推出真实 vendor 可用性、生产长期稳定性或 owner acceptance。

---

## 6. Handoff / 下阶段 entry-gate 预核对

| 入口条件 | 状态 | 备注 |
|----------|------|------|
| 以 D08、D07 §7.D08 与本 closure 为同一组 truth/evidence anchor | ✅ | 三者分别定义能力闭集、验收 ledger 与实现快照；本 closure 不覆盖前两者。 |
| 三 provider raw contract 与 exact binding 可供下游使用 | ✅ | 只允许 `chinatax/get_articles/v1`、`domain/get_agency_listings/v1`、`realestate/get_listings/v1`。 |
| 四域 clean strategy 与 workflow Process key 可供下游使用 | ✅ | strategy manifest 与 source-kind eligibility digest 已登记；未知 binding fail-closed。 |
| 当前实现形成 immutable commit | ⏸ | 需 maintainer review/commit；在此之前只能引用 `worktree@02b141e`。 |
| D08 truth owner-freeze | ⏸ | 由 owner/`18` 完成；实现 agent 不得自行把 draft 改为 accepted。 |
| D04 proposed 表升级为 required | ⏸ | 当前不是下阶段 entry requirement；只有 D04 owner reopen 才触发。 |

**下阶段 kickoff checklist**：

- [ ] 引用本 closure 作为 D08 实现证据入口，同时读取 D08 与 D07 原文。
- [ ] 在提交前审阅 `git diff --stat`、`git diff` 与全部 untracked provider/contracts/tests 文件。
- [ ] 保持三个 provider-operation 闭集和四个 source kind，不引入 branch-name taxonomy。
- [ ] 不创建 D04 proposed 表，除非 owner 已正式 reopen D04。
- [ ] 形成 commit 后重跑 `.venv/bin/ruff check .`、`git diff --check` 与 `.venv/bin/pytest -q`。

---

## 7. Cross-cut 不变量（0-drift 确认）

| 不变量 | 状态 | 证据 |
|--------|------|------|
| source kind 仍恰为 `inline_payload/local_object/http_resource/registered_api`；provider 不是第五类 kind | ✅ 保持 · `observed-OK-at-closure` | `src/services/registry.py` source-kind bootstrap + `tests/unit/test_intake_source_capabilities.py`；全量测试通过。 |
| registered-api 权威闭集恰为三个 provider-operation-version binding | ✅ 保持 · `observed-OK-at-closure` | `tests/unit/test_intake_provider_registry.py` closed-set 与 unknown-key 断言通过。 |
| `intake/{api,web,pdf,doc}` 是 clean 变换 SSOT；runtime 只围栏与 dispatch | ✅ 保持 · `observed-OK-at-closure` | runtime architecture source scan 与 dispatch 单测通过；无 runtime HTML/provider parser。 |
| Raw/source-semantic/clean-derived 分账；ExternalKey 不由随机 UUID 代替 | ✅ 保持 · `observed-OK-at-closure` | provider parsers输出稳定业务键、raw/content/meta/clean digest；idempotence tests 通过。 |
| HTTP PDF/print-PDF 优先进入 PDF 域，不被 `http_resource` 暗路由到 Web sanitizer | ✅ 保持 · `observed-OK-at-closure` | `test_http_pdf_text_layer_never_enters_web_sanitizer` 与 HTTP PDF LLM dispatch 单测通过。 |
| LLM clean 只引用冻结 Prompt A key/version/hash，不在 strategy/runtime 复制第二份正文 | ✅ 保持 · `observed-OK-at-closure` | Prompt hash mismatch 单测通过；策略定义只含 pointer coordinate。 |
| D04 required DDL 闭集不变，schema/strategy 用 contracts + code-owned digest 表达 | ✅ 保持 · `observed-OK-at-closure` | `git diff --name-only -- src/persistence/migrations` 空；registry bootstrap tests 随全量 suite 通过。 |
| 禁止 legacy runtime、live tunnel/cookie/Cloudflare URL 常量与 branch-name 路由 | ✅ 保持 · `observed-OK-at-closure` | D08 architecture test 与生产目录 forbidden-string scan 均通过。 |
