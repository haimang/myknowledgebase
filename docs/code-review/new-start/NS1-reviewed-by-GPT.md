# NS1 代码审查

> 审查对象: `NS1 non-interactive agentic production path`（HEAD `a64c952`）
> 审查类型: `code-review | closure-review`
> 审查时间: `2026-08-14`
> 审查人: `GPT`
> 审查范围:
> - `data/prompts/**`、`data/schemas/**`、`src/services/**`、`src/runtime/**`、`src/workflows/**`、`api/**`
> - `src/persistence/migrations/007_ns1_prompt_catalog.sql`、`tests/{unit,domain,e2e}/**`
> 对照真相:
> - `docs/plan/new-start/NS1-new-pipeline.md`
> - `docs/closure/new-start/NS1-new-pipeline-closure.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> NS1 的 layered kernel、identity-only API 和主图骨架已经落地，但真实 production 组合没有走计划中的 CLI 四跳；Markdown 分支和 clean-anchor 互相矛盾；catalog 的版本演进也会阻塞后续新任务。因此不能把 NS1 判为“全部完成”或关闭本轮 review。

- **整体判断**：`核心内核已完成，生产接线、catalog 完整性和验收证据仍为 partial。`
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. `live_inference=True` 时没有装配 Claude CLI，B.json/C 保留旧 InferenceFacade；计划所述 A → [B.md] → B.json → C production path 没有成立。
  2. Markdown 转录结果被送入 B.json，但 kernel 要求其 g0 和各块精确锚定 clean；真实 Markdown 格式变化会使 legal 分支 fail-closed。
  3. catalog 的 PATCH/new-version 使同一 prompt_id 有多个 active row，而 materialize 要求恰好一个，导致后续新任务失败。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/plan/new-start/NS1-new-pipeline.md`（全文，特别是 P1–P5、§8、§10）
  - `docs/closure/new-start/NS1-new-pipeline-closure.md`（全文）
- **核查实现**：
  - catalog / snapshot：`src/services/registry.py`、`src/services/config_snapshots.py`、`007_ns1_prompt_catalog.sql`
  - runtime / workflow：`api/app.py`、`src/runtime/inference/claude_cli.py`、`src/runtime/intake/{clean_preflight,generation_construct,generation_live,core}.py`、`src/services/lsrag_compiler.py`
  - tests：全部 NS1 命名 unit/domain/e2e 用例及关联的 scatter / generation / lifecycle 用例。
- **执行过的验证**：
  - `.venv/bin/python -m pytest -q tests/unit tests/domain` — PASS。
  - `.venv/bin/python -m pytest -q <NS1 unit/domain/e2e targeted set>` — PASS（覆盖 schema、catalog、adopt、CLI stub、主图与 scatter）。
  - `.venv/bin/python -m pytest -q tests/e2e` — non-zero；随后 `.venv/bin/python -m pytest --lf --tb=short -vv` 为 5 failed / 1 passed。
  - `.venv/bin/python -m ruff check .`、`.venv/bin/python -m compileall -q api src tests`、`git diff --check` — PASS。
  - 最小反例：多 active prompt version 的 snapshot materialize、Markdown g0 anchor、200,000-byte CLI argv 均已独立执行。
- **复用 / 对照的既有审查**：`none` — 本审查未读取或参考 `docs/code-review/` 中任何其他审查报告。

### 1.1 已确认的正面事实

- `LsragContractCompiler.adopt_layered_json` 已实现 profile、g0、精确子串、首次命中和 occurrence 证明；生产 intake 扫描不再调用 `compiler.structurize(clean_text)`。
- `IntakeIngestPayload` 只接收四个 `*_prompt_id`，并以 strict model 拒绝 `prompt_ref`、路径等 caller-controlled coordinates。
- 主图和 registered-api child 图已表达 optional Markdown 跳；`structurize.failed` 走 terminal failed，而非自动 human review。
- hash/path revalidation、prompt body 不入 DB、collect-all scatter 后 root fail-closed 均有实现和正向测试。

### 1.2 已确认的负面事实

- 当前完整 e2e 非绿色；最近失败重跑有 5 个 raw `sqlite3` inspection 失败（`disk I/O` / `file is not a database`）。无论是否为 Turso harness 既有问题，AP §10 所要求的全 PASS 证据当前不存在。
- closure 记录 6 个失败 case；本轮 `--lf` 重跑中其中 1 个已通过、5 个仍失败，说明该 residual 的计数也不是稳定的收口证据。
- action-plan front matter 仍为 `executing`；其 §11 规定全部完成后转为 `executed`。当前选择 `close-with-known-issues` 可以诚实描述风险，但不等同于实现/测试全完成。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | 对 runtime composition、catalog、migration、workflow、prompt asset、测试逐项核对。 |
| 本地命令 / 测试 | `yes` | 跑 unit/domain、NS1 定向、full/last-failure e2e、static gates，并执行三个最小反例。 |
| schema / contract 反向校验 | `yes` | 用实际 g0/anchor、catalog row 与 CLI request/receipt 合同验证。 |
| live / deploy / preview 证据 | `no` | owner scope 禁止 live migration、worker / Pages 发布；本审查不将其误报为缺失交付。 |
| 与上游 action-plan 对账 | `yes` | P1–P5、T01–T46 与 §10 hard gates 均已复核。 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | live production 未装配或使用 NS1 Claude CLI | critical | delivery-gap | yes | 统一 production 组合和 A/B.md/B.json/C transport。 |
| R2 | Markdown 转录与 clean-anchor 合同不可同时满足 | critical | correctness | yes | 保持 clean SSOT，并为 Markdown 设计可证明的辅助输入边界。 |
| R3 | catalog new-version 会阻塞后续新任务 | high | correctness | yes | 实现确定的 active-version 选择 / retirement，并覆盖 v10 等排序。 |
| R4 | catalog 资产、profile 与 DDL 未完成 P1 contract | high | delivery-gap | yes | 补 legal/realestate、接通四角色正文、收紧 DB invariant。 |
| R5 | CLI 不能运输 API 允许的大物料 | high | platform-fitness | yes | 改为经验证的大物料 transport，或明确收紧入口上限。 |
| R6 | CLI receipt、失败语义与 invocation audit 未形成闭环 | medium | protocol-drift | no | 以真实 frozen pointer 写账，持久化 A/B.md/B.json/C receipt 并定义 retry。 |
| R7 | 测试台账没有覆盖关键机制，完整 e2e 也未通过 | high | test-gap | yes | 补真实链路反例 / lifecycle / soak，并修复 Turso inspection harness 后重跑。 |

### R1. live production 未装配或使用 NS1 Claude CLI

- **严重级别**：`critical`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `api/app.py:280-285` 仅在 `not settings.live_inference` 时创建 `DeterministicNs1Stub` 或 `SubprocessClaudeCli`；live composition 注入的 `claude_cli` 为 `None`。
  - `src/runtime/intake/generation_construct.py:552-567` 的 live B.json 分支调用旧 `_live_structured_generate`；`:763-777` 的 live C 分支调用旧 `_live_layered_summary_generate`。
  - `src/runtime/intake/generation_construct.py:194-202` 的 Markdown worker 在 CLI 为 `None` 时直接报 `MARKDOWN_WORKER_UNAVAILABLE`。
- **为什么重要**：P3 的交付目标是 production 的 `claude -p` 四跳，而不是只提供一个仅离线 stub 可达的 port。当前真正 live path 既不验证 CLI argv/schema 合同，也不能执行 optional Markdown 跳。
- **审查判断**：`P3-01..P3-05 partial`；不能用“未做 live vendor 验证”解释，因为缺的是本地可静态证明的 production composition/wiring。
- **建议修法**：让 live composition 显式装配并使用一个生产 CLI port，或经正式设计变更把旧 facade 定义为替代生产 transport；为两种 settings 组合写 composition test，断言 A、B.md、B.json、C 的实际 port 与请求合同。

### R2. Markdown 转录与 clean-anchor 合同不可同时满足

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `generation_construct.py:568-572` 在有 Markdown state 时将 `markdown_text` 作为 B.json 的 `-p` material。
  - `lsrag_compiler.py:494-500` 要求 g0 归一化后等于完整 clean，且每个 original body 都是 clean 的精确子串。
  - `data/prompts/markdown/promptB.markdown.legal.v1.md:5-8` 要求 worker 输出标题、章节、条款、列表等 Markdown 表达。
  - 独立反例：clean 为 `Chapter one\nA legal notice`，Markdown 为 `# Chapter one\n\nA legal notice` 时，`adopt_layered_json` 返回 `STRUCTURE_ANCHOR_MISSING: The g0 body is not the complete clean artifact`。
- **为什么重要**：实际 Markdown 转写一旦插入标记，就会使 legal branch 必然失败；现有 e2e 的 deterministic stub 对 markdown role 原样回显，不能代表该输入变换。
- **审查判断**：P4-02 的拓扑存在，但 P3-03/P3-04 的业务路径没有闭合；`T42 partial`。
- **建议修法**：不改变 clean 为 original/anchor SSOT 的冻结约束。把 clean 与 Markdown 以有类型的双物料交给 B.json，并明确要求其 `original_content` 只从 clean 复制；或者为 Markdown 建立可验证的 source mapping。若打算允许 Markdown 成为 original，则必须重新打开上游 anchor 决策，而不能在 runtime 静默放宽。

### R3. catalog new-version 会阻塞后续新任务

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `registry.py:441-485` 的 `register_prompt` 为 PATCH/new version 插入 active row，不会 retire 旧 active row。
  - `config_snapshots.py:582-584` 对某一 role/id 的 active candidates 要求 `len(candidates) == 1`。
  - 独立反例向同一 json prompt 注册 v1 和 v2 后调用 `_resolve_prompt_selection`，得到 `PROMPT_NOT_REGISTERED: Active json prompt is unavailable`。
  - `registry.py:411-417` 用 `ORDER BY prompt_version DESC` 选择“最新”，其字符串排序也会将 `v9` 排在 `v10` 前。
- **为什么重要**：P1-05 的核心承诺是 PATCH 新 immutable version，P4-04 又要求新 execution materialize 当前选择、旧 execution 固定旧选择。按当前实现，首次升级便令新 intake 无法创建。
- **审查判断**：P1-05/P1-06/P4-04 均为 `partial`；当前 `v1 → v2` registry unit 没有覆盖真实 Task materialize。
- **建议修法**：定义一个规范化的 version ordering，并在单一事务内明确“latest active”的选择语义（例如新 version 激活时 retire / supersede 旧 version，或 snapshot resolver 使用同一 deterministic latest resolver）。补新 execution、in-flight execution、retry 三段 lifecycle test，至少覆盖 `v2`/`v10`。

### R4. catalog 资产、profile 与 DDL 未完成 P1 contract

- **严重级别**：`high`
- **类型**：`delivery-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - action-plan P1-04 明定 `json.legal={0,1}`、`json.realestate={0}`。`registry.py:66-72` 只有 generic/default `{0,1,2}`；`data/prompts/json/` 也只有 `promptB.json.generic.v1.md`。
  - 默认 clean/summarizer pointer 仍是 `prompt-a-clean-v1.md`、`prompt-c-summary-v1.md`（`registry.py:67,71`；`config_snapshots.py:50-53,566-570`），而迁入的 `clean/promptA.clean.v1.md` 与 `summarizer/promptC.summarizer.v1.md` 未被默认生产 selection 使用。
  - `007_ns1_prompt_catalog.sql:13-14` 对 `granularity_set` 只有长度检查；并未保证 JSON role 非空、值为 JSON array，也未禁止 non-json row 带 profile。`test_ns1_catalog_ddl.py:21-34` 只验证列和非法 role。
- **为什么重要**：法律和房产的 frozen closed profiles 不是 optional test data；它们是 P1 catalog 的实际可选能力。默认 A/C 又没有真正迁到新 role assets，因而“四角色 prompt 正文已迁入 production”的结论不成立。
- **审查判断**：P1-01..P1-04 均 `partial`；T01/T03/T04/T42 未给出计划要求的资产/profile 证据。
- **建议修法**：增加并 bootstrap immutable legal/realestate JSON assets/rows，安全迁移默认 A/C 至实际 role assets（必要时使用新 version，避免破坏已冻结 pointer）；在 migration 或等效 DB trigger 中施加 role/profile invariant，并针对 SQLite 与目标 Turso backend 验证。

### R5. CLI 不能运输 API 允许的大物料

- **严重级别**：`high`
- **类型**：`platform-fitness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `claude_cli.py:66-75` 把完整 user material 作为单一 `-p` argv argument，`:146-153` 以 `stdin=DEVNULL` 创建进程。
  - `src/contracts/api/models.py:101-105` 允许 inline content 达 8 MiB；B/C 的 JSON package 还会放大物料。
  - 独立以 `/bin/true` 模拟 subprocess，200,000-byte user prompt 已返回 `CLAUDE_CLI_TRANSPORT_FAILED`（底层 `E2BIG`）。
- **为什么重要**：合法 API request 远超过单 argv 参数上限，非交互生产路径会在 transport 前失败；当前没有上限保护、chunking/streaming 策略或边界测试。
- **审查判断**：P3 transport 不能支持本服务已公开允许的输入范围，属于 production fitness 缺口。
- **建议修法**：采用 CLI 已验证的 file/stdin 或受控临时物料协议；若该 CLI 只支持 argv，必须把入口和后续 package 限制收紧到可证明安全的上限并在 API/worker 同时校验。补大 clean、Markdown、layered C package 的边界 tests。

### R6. CLI receipt、失败语义与 invocation audit 未形成闭环

- **严重级别**：`medium`
- **类型**：`protocol-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - `_cli_layered_candidate` / `_cli_layered_summary` 使用 frozen pointer 的真实路径（`generation_construct.py:110-115,157-162`），但 receipt 的 `prompt_relative_path` 硬编码 generic/new assets（`:135-143,181-190`）；自定义或 legacy pointer 会产生 request 与 receipt 不一致。
  - CLI B/C receipt 只写 stage state（`:643-644,856-857`）；DB invocation 写入仅发生在旧 `generation_invocation` 存在时（`:691-700,908-916`）。A adapter 只返回文本（`claude_cli.py:219-238`），没有保存 session/usage/exit。
  - `CLAUDE_CLI_TIMEOUT` / `CLAUDE_CLI_TRANSPORT_FAILED`（`claude_cli.py:154-177`）不在 `core.py:172-190` 的 recoverable closed set，直接终态。
- **为什么重要**：P3-01 明定 session/usage/exit 和 invocation 账；P4-04 要求 frozen path/hash。审计对象写错或不落库会使重试、追踪与合规证据不可用。
- **审查判断**：功能 happy path 可运行，但 transport ledger/retry contract 不完整。
- **建议修法**：receipt 从实际 frozen pointer 派生，统一以 body-free durable invocation record 写入 A/B.md/B.json/C；让 worker 再次验证 port 返回的 `exit_code/is_error`；把明确的 transient CLI 错误纳入受控 retry code set，并测试 non-zero、timeout、is_error、custom pointer。

### R7. 测试台账没有覆盖关键机制，完整 e2e 也未通过

- **严重级别**：`high`
- **类型**：`test-gap`
- **是否 blocker**：`yes`
- **事实依据**：
  - `tests/e2e/test_ns1_pipeline.py:33-44` 的两条 journey 都使用 `promptB.json.generic`，并只断言 `{0,1,2}`（`:119-129`）；没有 legal `{0,1}` profile 或真实 Markdown 变换。
  - `tests/e2e/test_registered_api_scatter.py:470-481` 在进入 handler 前直接伪造失败，而非让 malformed candidate / anchor miss 穿过 `adopt_layered_json`；它证明 fan-in，不能证明新 kernel 的 failure routing。
  - `tests/unit/test_ns1_prompt_catalog.py:110-129` 的 T46 只是 32×4 次未变更 bytes 的 resolve；没有计划所称的 hash drift × N。
  - `tests/unit/test_ns1_api_workflow.py:88-110` 仅直接调用 resolver；没有“创建 execution → 更新 catalog → retry → 断言旧 hash/path”生命周期测试（T34）。
  - `rg --files tests/fixtures | rg 'ns1|layered'` 无结果，未见 P1-01 要求的 generic/legal/realestate 可审计金样文件。
  - 本轮 full e2e 为 non-zero；`--lf` 显示 index rebuild、reactivate、rebuild/metadata、scatter auto-zero 的 5 个 Turso/raw-sqlite inspection failures。
- **为什么重要**：这些正是 NS1 与旧 pipeline 的分界机制。当前 green suites 主要证明 private method、deterministic stub 和 generic happy path，无法支撑“所有机制均已覆盖”或 §10 hard-gate pass。
- **审查判断**：P5-02/P5-03 和 T01/T20–T24/T33/T34/T42/T43/T46 都是 `partial`；全 e2e residual 在修复前必须保持 partial，而不是 completion evidence。
- **建议修法**：增加 checked-in golden fixtures；真实 Markdown transform → B → adopt、legal/realestate profile、真实 anchor/profile failure 的 scatter、version update/retry、CLI failure/large payload、drift soak。以 Turso-compatible inspection adapter / legal snapshot 修复 e2e harness 后，重新跑无排除的 `tests/e2e`。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / closure claim | 审查结论 | 说明 |
|------|------------------------|----------|------|
| P1-01 | schema + generic/legal/realestate 金样 | partial | schema/validator 和 kernel 存在；缺 checked-in 金样，schema/validator 本身也不强制 g0。 |
| P1-02 | 四角色正文迁入 | partial | 四个新文件存在，但默认 clean/summarizer 仍选 legacy files；legal/realestate JSON assets 缺失。 |
| P1-03 | 指针表窄晋升 + role/profile 列约束 | partial | 加列、role/status check 已做；profile JSON/role invariant 没有物理约束。 |
| P1-04 | bootstrap 四角色和 JSON closed profiles | partial | generic 有；legal `{0,1}` 与 realestate `{0}` 不存在。 |
| P1-05 | 内部 CRUD，update=new immutable version | partial | CRUD/路径拒绝存在，但 version update 会破坏后续 materialize。 |
| P1-06 | resolve + hash fail-closed | partial | hash/path gate 有效；latest version 是 lexical sort，且与 snapshot selection 不一致。 |
| P2-01 | `adopt_layered_json` | done | clean normalization、profile、g0、anchor、projection、report 均已实现。 |
| P2-02 | production 走 adopt，退出假树 | done | `_structurize` candidate→adopt；domain guard 阻止 runtime fake-tree call。 |
| P2-03 | C 整包 summary map | done | C package mapping 和 original mutation rejection 已实现/测试。 |
| P3-01 | `ClaudeCliPort` + stub + transport ledger | partial | port/stub/argv 已有；live composition 未用、ledger/retry 未闭环。 |
| P3-02 | A 仅 llm strategy 走 CLI | partial | 离线 unit 成立；live production 未装配 CLI。 |
| P3-03 | B.md worker | partial | 图和 worker 存在；live 中 CLI 缺失，真实 Markdown 与 anchor 也不相容。 |
| P3-04 | B.json schema + Markdown/clean material | partial | kernel 接线存在；Markdown input cannot satisfy clean anchor，live 未走 CLI。 |
| P3-05 | C 整包一次 | partial | local CLI/stub path 成立；live 仍走 facade，CLI audit 未持久化。 |
| P4-01 | identity-only ingest | done | strict `*_prompt_id` model 和 role/path/hash revalidation 已落地。 |
| P4-02 | optional Markdown graph | partial | 路由拓扑正确，但实际 Markdown path 被 R1/R2 阻断。 |
| P4-03 | structure failure terminal，不开人审 | done | graph route 和 unit proof 均存在。 |
| P4-04 | frozen role pointer，retry 不热切 | partial | selection snapshot code 存在，但 version 更新会阻塞新任务、receipt 可错、无 lifecycle retry proof。 |
| P5-01 | domain guards | done | fake-tree / DB body / public coordinate 守卫通过。 |
| P5-02 | generic/no-md 与 legal/with-md mega | partial | generic journey通过；“legal”仍是 generic profile，且 Markdown stub 不转换内容。 |
| P5-03 | child adopt failure isolation | partial | fan-in 已测，但注入失败绕过 adopt。 |
| P5-04 | truth/README 窄回填 | done | 相关附录和 README example 已存在；action-plan 顶层状态仍需与最终 verdict 一致。 |

### 3.1 对齐结论

- **done**: `7`
- **partial**: `15`
- **missing**: `0`（缺少的 assets/fixtures/profile 被计入所属工作项的 partial）
- **stale**: `1`（closure 的 e2e failure count 与本轮重跑不一致）
- **out-of-scope-by-design**: `3`（见 §4）

> 这更像“layered kernel 和 API/图骨架已完成，但 catalog、CLI production transport 与可信验收尚未收口”，而不是 completed。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | `lsrag.structure_repair` / `grok -p` 修理工 | 遵守 | 未发现 repair worker 被作为 NS1 fallback 接入。 |
| O2 | 重开 S03/S04/D08/S08–S10 | 遵守 | 本审查未把这些已有机制的产品重设计当作 NS1 blocker。 |
| O3 | 新 required 表或 DB 存 prompt body | 遵守 | 使用既有 pointer 表加列；domain scan 未见 `body_text`。 |
| O4 | scatter 部分成功 | 遵守 | 当前结论仍是 sibling collect-all、root fail-closed，不要求 reopen partial-success。 |
| O5 | live vendor 验证、migration / worker / Pages 发布 | 误报风险 | owner 明确禁止；本审查的 R1 是静态 production wiring 缺失，不是要求执行 live/deploy。 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`changes-requested — NS1 不满足 action-plan 的全部完成和测试收口标准。`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. 修正 live composition，使 A → [B.md] → B.json → C 真正经批准的 CLI transport，或以正式设计变更替换该计划目标；同时修复 Markdown/clean anchor input contract。
  2. 修复 catalog version selection、补齐 legal/realestate profile/assets、接通实际四角色默认 assets，并收紧 profile storage invariant。
  3. 解决 CLI 大物料 transport，并补齐 frozen-pointer/retry、真实 adopt failure、legal profile、hash-drift、CLI error 的测试。
  4. 修复 Turso inspection harness 后运行无排除的 full e2e；在全绿前将相关 hard gate 保持为 `partial`。
- **可以后续跟进的 non-blocking follow-up**：
  1. 将 CLI invocation receipt（含真实 pointer、session/usage/exit、retry disposition）统一写入可查询 ledger。
  2. 使 action-plan、closure 的状态和失败计数在复跑后同步，避免过期 evidence。
- **建议的二次审查方式**：`independent reviewer`
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。
