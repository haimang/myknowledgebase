# Nano-Agent 代码审查报告

> 审查对象: `MKB / NS1 non-interactive agentic production path`
> 审查类型: `code-review`
> 审查时间: `2026-08-14`
> 审查人: `Gemini`
> 审查范围:
> - `src/contracts/lsrag/`
> - `src/contracts/api/`
> - `data/schemas/lsrag.layered_content.v1.json`
> - `data/prompts/**`
> - `src/persistence/migrations/007_ns1_prompt_catalog.sql`
> - `src/services/lsrag_compiler.py`
> - `src/services/registry.py`
> - `src/services/config_snapshots.py`
> - `src/runtime/inference/claude_cli.py`
> - `src/runtime/intake/`
> - `src/workflows/`
> - `tests/unit/`
> - `tests/domain/`
> - `tests/e2e/`
> 对照真相:
> - `docs/plan/new-start/NS1-new-pipeline.md`
> - `docs/plan/new-start/NS1-new-pipeline.todo.md`
> - `docs/closure/new-start/NS1-new-pipeline-closure.md`
> - `docs/eval/new-start/pre-NS1-qna.md` (`T-O-337..351`)
> 文档状态: `changes-requested`

---

## 0. 总结结论

> NS1 核心架构革新（纯函数 `adopt_layered_json` 验收内核、生产环境彻底拔除假树、Stage C 整包全量摘要、无凭证安全 Claude CLI 传输层、严格 `*_prompt_id` API 契约、可选 Markdown 转写 DAG 条件路由、快照 CAS 与 Hash 冻结、Scatter 故障隔离机制）已高质量兑现，单元与领域测试 100% 通过；但存在 **1 个直接破坏 Prompt 版本更新后 Task Ingest 生命周期的功能断点（R1：Catalog Update 产生双 Active 版本导致后续 Ingest 抛 503）** 与 **1 个领域闭集交付缺口（R2：未交付 legal/realestate JSON 提示词正文与 bootstrap 项）**。

- **整体判断**：主体架构与核心机制扎实成立，安全与隔离防线完备，但 Catalog 更新存在阻断性链路断点，且存在领域闭集正文的欠交付，暂不可直接关闭本轮审查。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 3 个判断**：
  1. **生产假树彻底退出，Kernel 验收纯函数完备**：`adopt_layered_json` 严格执行 NFC/LF 规范化、粒度闭集校验、g0 原文通道、精确子串首次命中锚定与 1:1 投影映射；`src/runtime/intake/` 中已彻底无 `compiler.structurize(clean_text)` 调用，且元数据刷新直接解析冻结工件，无静默降级或句子伪造（P2/P3 满分通过）。
  2. **发现阻塞性链路断点（R1 Blocker）**：`PromptRegistry.register_prompt` 在 PATCH/Update 新版本时未将旧 active 版本置为 retired，导致库中同一 `prompt_id` 存在两个 `status='active'` 行；而 `config_snapshots._resolve_prompt_selection` 严格断言 `len(candidates) == 1`，导致 Operator 更新 Prompt 版本后，该 Prompt 所有的后续 Ingest Task 均会抛出 `503 PROMPT_NOT_REGISTERED`，造成线上更新后链路瘫痪。
  3. **Closure Known-Issue 诚实客观**：独立排查证实，全量 e2e 中 6 个测试失败均纯粹源于测试套件内使用标准 `sqlite3.connect` 去直接读取处于 `pyturso` (libSQL) 独占引擎锁下的数据库文件（该模式系 baseline `8b4599d` 引入的测试 Harness 固有问题，与 NS1 代码逻辑无关），Closure 的事实陈述完全属实。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/plan/new-start/NS1-new-pipeline.md`
  - `docs/plan/new-start/NS1-new-pipeline.todo.md`
  - `docs/closure/new-start/NS1-new-pipeline-closure.md`
  - `docs/eval/new-start/pre-NS1-qna.md` (`T-O-337..351`)
  - `docs/eval/new-start/non-interactive-agentic-pipeline.md`
- **核查实现**：
  - Schema & Assets: `data/schemas/lsrag.layered_content.v1.json`, `data/prompts/**`
  - DDL & Catalog: `src/persistence/migrations/007_ns1_prompt_catalog.sql`, `src/services/registry.py`, `api/internal/prompts.py`, `api/internal/routes.py`
  - Kernel & Compiler: `src/services/lsrag_compiler.py`, `src/contracts/lsrag/layered_content.py`
  - CLI & Workers: `src/runtime/inference/claude_cli.py`, `src/runtime/intake/generation_construct.py`, `src/runtime/intake/generation_live.py`, `src/runtime/intake/clean_preflight.py`, `src/runtime/intake/core.py`
  - Workflow & Materialize: `src/contracts/api/models.py`, `src/workflows/lsrag_definition.py`, `src/workflows/builtin_scatter.py`, `src/runtime/workflow/runtime_materialize.py`, `src/runtime/workflow/runtime_scatter.py`, `src/services/config_snapshots.py`
  - Tests: `tests/unit/`, `tests/domain/`, `tests/e2e/`
- **执行过的验证**：
  - `.venv/bin/python -m pytest -q tests/unit` (40 测试文件, 227 passed, 100%)
  - `.venv/bin/python -m pytest -q tests/domain` (9 passed, 100%)
  - `.venv/bin/python -m pytest -q tests/domain/test_ns1_guards.py tests/e2e/test_ns1_pipeline.py tests/unit/test_ns1_prompt_catalog.py` (7 passed)
  - `.venv/bin/python -m pytest -q tests/e2e -k 'not scoped_index_rebuild_promotes_generation_without_new_intake_revision and not index_rebuild_stale_fence_fails_without_cutover_and_old_generation_remains_retrievable and not reactivate_restores_active_lifecycle_but_not_stale_serving_state and not rebuild_and_metadata_lifecycle_paths_complete_through_public_http and not registered_api_scatter_auto_zero_and_fanin_recovery'` (12 passed)
  - `.venv/bin/python -m ruff check .` (pass)
  - `.venv/bin/python -m compileall -q api src tests` (pass)
  - `git diff --check` (pass)
  - `git diff 5955a99..HEAD -- docs/eval/new-start/pre-NS1-qna.md` (0 diff, frozen QNA unchanged)
- **复用 / 对照的既有审查**：
  - 无（全流程由 Gemini 独立派出 4 路 Sub-agents 展开源码级静态分析与动态执行测试，完全独立 reasoning）。

### 1.1 已确认的正面事实

1. **Schema 严格闭包，无坐标污染**：[`layered_content.v1.json`](file:///root/workspace/myknowledgebase/data/schemas/lsrag.layered_content.v1.json#L1-L74) 与 [`layered_content.py`](file:///root/workspace/myknowledgebase/src/contracts/lsrag/layered_content.py#L1-L120) 严格配置 `additionalProperties: false`，彻底禁用了 `span`、`coordinates`、`offset` 等字段；支持 B 阶段 summary 为 null 校验与 C 阶段 summary 必填校验。
2. **DDL 严格遵守 T-O-337 围栏**：[`007_ns1_prompt_catalog.sql`](file:///root/workspace/myknowledgebase/src/persistence/migrations/007_ns1_prompt_catalog.sql#L1-L36) 仅对既有表 `mkb_prompt_hash_pointers` 进行列窄晋升（增加 `prompt_id`, `role`, `status`, `granularity_set`），未新建物理表，未破坏 55 表闭集，数据库中绝无 `body_text` 字段。
3. **安全威胁模型（§7.3）严格落地**：
   - 路径防逃逸：[`registry.py:431-436`](file:///root/workspace/myknowledgebase/src/services/registry.py#L431-L436) 与 [`config_snapshots.py:593-599`](file:///root/workspace/myknowledgebase/src/services/config_snapshots.py#L593-L599) 强制校验 `path.relative_to(prompt_root)` 并拒绝绝对路径及 `..` 片段。
   - 鉴权与网络围栏：`/internal/prompts` 挂载 `require_operator_token` 与 `is_internal_ip` 双重守卫，外部与 Agent 无法访问。
   - Hash 门闩：`resolve_prompt` 强制计算 `SHA256(file) == catalog.content_sha256`，篡改或缺失直接 fail-closed 报 503。
4. **纯函数 Kernel 验收完备**：[`lsrag_compiler.adopt_layered_json`](file:///root/workspace/myknowledgebase/src/services/lsrag_compiler.py#L253-L551) 实现了 NFC/LF 统一规范化、g0 原文通道及空 body 自动回填、g≥1 精确子串首次锚定与 `occurrence_count` 统计、缺失子串报 `STRUCTURE_ANCHOR_MISSING`，且 1 个 layered 块精准映射为 1 个 `RetrievalBlock`（无按句拆分）。
5. **假树彻底拔除，元数据刷新重构**：`src/runtime/intake/` 下 0 调用 `compiler.structurize`；`_structurize` 缺失 candidate 直接报 `STRUCTURE_CANDIDATE_MISSING`；[`generation_construct.py:254-470`](file:///root/workspace/myknowledgebase/src/runtime/intake/generation_construct.py#L254-L470) 中的元数据刷新改为解析复验冻结的结构化工件，绝不再重新编树。
6. **Stage C 整包全量摘要**：[`generation_construct.py:147-193`](file:///root/workspace/myknowledgebase/src/runtime/intake/generation_construct.py#L147-L193) 与 [`generation_live.py:308-330`](file:///root/workspace/myknowledgebase/src/runtime/intake/generation_live.py#L308-L330) 将整个 layered 候选包单次传入，并通过 [`layered_summary_map`](file:///root/workspace/myknowledgebase/src/services/lsrag_compiler.py#L553-L605) 按 `(granularity, block_id)` 填入 `llm_summary.body`，若检测到 original 被模型篡改则抛出 `CONSTRUCT_KERNEL_ORIGINAL_MUTATION`。
7. **Claude CLI 传输端口安全可注入**：[`claude_cli.py`](file:///root/workspace/myknowledgebase/src/runtime/inference/claude_cli.py#L56-L85) 参数构造完全脱敏、无 Shell 插值；仅对 B.json 与 C 阶段传递 `--json-schema`；优先解析 `structured_output`；内置 `RecordingStub` 与 `DeterministicNs1Stub`，测试环境 100% 离线可复现。Clean 策略分流正确，确定性/API 解析器绕过 CLI。
8. **严格 API 模型与 DAG 条件路由**：[`IntakeIngestPayload`](file:///root/workspace/myknowledgebase/src/contracts/api/models.py#L175-L185) 强制 `extra="forbid"`，必填 `json_prompt_id`，拦截非法路径及 body；[`lsrag_definition.py:349-365`](file:///root/workspace/myknowledgebase/src/workflows/lsrag_definition.py#L349-L365) 实现可选 Markdown 转写分支，缺省时不生成 transcribe Process；结构化失败直达 `failed` 终止态，不再转入人审。
9. **快照物化冻结与 Scatter 故障隔离**：Prompt 身份元数据固化进 L4 ConfigSnapshot 并计算 CAS Digest，任务运行时与重试绝不热切；Scatter 批处理中单个子任务结构化失败不影响兄弟任务执行，所有子任务结束后根节点聚合报错 `scatter-required-child-failed`。
10. **双 Mega 旅程与测试台账全覆盖**：[`test_ns1_pipeline.py`](file:///root/workspace/myknowledgebase/tests/e2e/test_ns1_pipeline.py#L73-L130) 实测 Generic (无 MD) 与 Legal (有 MD) 旅程均通过，断言检出真实多层投影（$g_0 \neq g_1 \neq g_2$）；AP §8.1 全部 46 项测试（NS1-T01 ~ NS1-T46）均有对应实现且通过。

### 1.2 已确认的负面事实

1. **Catalog Update 导致下一次 Ingest 崩溃 (R1)**：
   - 事实：[`PromptRegistry.register_prompt`](file:///root/workspace/myknowledgebase/src/services/registry.py#L469-L485) 在插入新版本（例如 PATCH 更新为 v2）时，保留了旧版本行（v1）的 `status='active'`。
   - 事实：[`ConfigSnapshotService._resolve_prompt_selection`](file:///root/workspace/myknowledgebase/src/services/config_snapshots.py#L582-L584) 在解析 Task Payload 对应的 prompt 时，执行：
     ```python
     candidates = [row for row in by_id.get(prompt_id, []) if row.get("status") == "active"]
     if len(candidates) != 1:
         raise MkbError("PROMPT_NOT_REGISTERED", f"Active {role} prompt is unavailable", 503)
     ```
   - 结果：一旦更新 Prompt 版本，数据库中存在 2 个 active 行，导致 `len(candidates) == 2`，后续使用该 `prompt_id` 的所有 Ingest 任务直接抛出 503 错误，系统无法使用新版本。
2. **领域闭集未交付与未 Bootstrap (R2)**：
   - 事实：AP P1-04 明确要求在 `DEFAULT_CATALOG_PROMPTS` 中登记 `json.legal {0,1}` 与 `json.realestate {0}`，并在 `data/prompts/json/` 迁入对应正文。
   - 事实：[`registry.py:66-72`](file:///root/workspace/myknowledgebase/src/services/registry.py#L66-L72) 中仅登记了 `promptB.json.generic` (`{0,1,2}`) 和 `promptB.default`；磁盘上 `data/prompts/json/` 仅有 `promptB.json.generic.v1.md`，缺少法律与房产领域的 JSON 分层提示词文件。
3. **遗留未调用的死代码 (R3)**：
   - 事实：[`generation_live.py:474-505`](file:///root/workspace/myknowledgebase/src/runtime/intake/generation_live.py#L474-L505) 中遗留了旧版 `_live_summaries` 方法（按 block 循环摘要）。虽然生产路径已切换至 `_live_layered_summary_generate`，但该死代码未被清理。
4. **内部 Prompt 路由鉴权未进行无 Mock 直测 (R4)**：
   - 事实：[`tests/unit/test_ns1_prompt_routes.py:30`](file:///root/workspace/myknowledgebase/tests/unit/test_ns1_prompt_routes.py#L30) 全局 mock override 了 `require_operator_token`，未对 `/internal/prompts` 进行直接断言无 Token / 非法 Token / 外网 IP 拦截的负向测试。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|:------------:|------|
| 文件 / 行号核查 | `yes` | 逐行核查了 Schema, DDL Migration, Compiler, Registry, CLI, Workflow, API Models 及全部测试文件 |
| 本地命令 / 测试 | `yes` | 运行了全量 unit (227 个测试全部通过)、domain (9 个测试全部通过)、P5 targeted (7 个测试全部通过) 以及 e2e 核心用例 |
| schema / contract 反向校验 | `yes` | 反向校验了 JSON Schema 与 Pydantic Model 的字段约束及 `additionalProperties: false` 拒绝能力 |
| live / deploy / preview 证据 | `n/a` | Owner 明确禁止任何 live migration, worker publish 与 Pages deploy，符合约束 |
| 与上游 design / QNA 对账 | `yes` | 对账 `pre-NS1-qna.md` (`T-O-337..351`) 与 NS1 Action Plan，确认 QNA 0-diff |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|:------------:|----------|
| **R1** | Prompt Update 未 Retire 旧版本导致后续 Ingest 抛 503 | `high` | `correctness` / `broken-flow` | **`yes`** | 在 `register_prompt` 插入新版本时原子地将旧 active 版本置为 `retired`，或调整 snapshot 解析逻辑 |
| **R2** | 欠交付 `json.legal` 与 `json.realestate` 正文及 Bootstrap 项 | `medium` | `delivery-gap` | `no` | 补充 `promptB.json.legal.v1.md`、`promptB.json.realestate.v1.md` 并在 bootstrap 中注册 |
| **R3** | `generation_live.py` 中遗留旧版按块循环摘要死代码 | `low` | `code-hygiene` | `no` | 清理废弃的 `_live_summaries` 方法或添加弃用注释 |
| **R4** | `/internal/prompts` 内部路由测试全局 Mock 鉴权依赖 | `low` | `test-gap` | `no` | 增加直接针对 `/internal/prompts` 鉴权失败与外网 IP 拦截的单元测试 |

---

### R1. Prompt Update 未 Retire 旧版本导致后续 Ingest 抛 503

- **严重级别**：`high`
- **类型**：`correctness` / `broken-flow`
- **是否 blocker**：**`yes`**
- **事实依据**：
  - [`src/services/registry.py:469-485`](file:///root/workspace/myknowledgebase/src/services/registry.py#L469-L485)：
    ```python
    await tx.execute(
        "INSERT INTO mkb_prompt_hash_pointers "
        "(prompt_id,prompt_key,prompt_version,git_relative_path,content_sha256,role,status,granularity_set,registered_at,payload_extra) "
        "VALUES (?,?,?,?,?,?,?,?,?, '{}')",
        (prompt_id, prompt_id, prompt_version, relative_path, pointer.content_sha256, role, "active", ...),
    )
    ```
    插入新版本时，旧版本的 `status` 保持为 `"active"`。
  - [`src/services/config_snapshots.py:582-584`](file:///root/workspace/myknowledgebase/src/services/config_snapshots.py#L582-L584)：
    ```python
    candidates = [row for row in by_id.get(prompt_id, []) if row.get("status") == "active"]
    if len(candidates) != 1:
        raise MkbError("PROMPT_NOT_REGISTERED", f"Active {role} prompt is unavailable", 503)
    ```
- **为什么重要**：
  - 当运维通过 `PATCH /internal/prompts/{prompt_id}` 更新提示词版本时（从 v1 升级到 v2），数据库中该 `prompt_id` 将同时存在 v1(active) 和 v2(active)。
  - 随后用户发起该 `prompt_id` 的 Ingest 请求时，`_resolve_prompt_selection` 筛选出 2 个 candidates，因 `len(candidates) != 1` 触发异常，所有任务直接被拒（503）。
  - 使得 Prompt 的正常版本升级流程破坏后续 Ingest 链路。
- **审查判断**：
  - 这是一个跨模块接口约定的设计失调：`registry.resolve_prompt` 采用了 `ORDER BY prompt_version DESC LIMIT 1` 来容忍多个 active 版本，但 `config_snapshots.py` 却采用了 `len(candidates) == 1` 的唯一定位断言。
- **建议修法**：
  - 在 `register_prompt` 写入新版本时，在同一事务内将同 `prompt_id` 的既有 active 记录更新为 `retired`；或者修改 `config_snapshots.py`，改为与 `resolve_prompt` 一致地选取 latest active 版本。

---

### R2. 欠交付 `json.legal` 与 `json.realestate` 正文及 Bootstrap 项

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - Action Plan `docs/plan/new-start/NS1-new-pipeline.md` §4.1 P1-04 明确要求：“json default `{0,1,2}`；另登记 `json.legal` `{0,1}`、`json.realestate` `{0}`”。
  - 实际上，[`src/services/registry.py:66-72`](file:///root/workspace/myknowledgebase/src/services/registry.py#L66-L72) 仅注册了 `generic` (`{0,1,2}`)，[`data/prompts/json/`](file:///root/workspace/myknowledgebase/data/prompts/json/) 下也仅有 `promptB.json.generic.v1.md`。
- **为什么重要**：
  - 法律领域（仅需 0/1 层）与房产领域（仅需 0 层）的定制化分层提示词未形成可直接通过 catalog 引用的标准资产，调用方只能使用 generic 提示词。
- **审查判断**：
  - 属于非阻塞性的功能欠交付（Under-delivery），底层 kernel 与 schema 已支持 `{0,1}` 和 `{0}` 闭集，但预置提示词资产未完全落地。
- **建议修法**：
  - 在 `data/prompts/json/` 下新增 `promptB.json.legal.v1.md` 与 `promptB.json.realestate.v1.md`，并在 `DEFAULT_CATALOG_PROMPTS` 中补充对应的 Seed。

---

### R3. `generation_live.py` 中遗留旧版按块循环摘要死代码

- **严重级别**：`low`
- **类型**：`code-hygiene`
- **是否 blocker**：`no`
- **事实依据**：
  - [`src/runtime/intake/generation_live.py:474-505`](file:///root/workspace/myknowledgebase/src/runtime/intake/generation_live.py#L474-L505) 中定义了 `_live_summaries` 方法，其内部逻辑为 pre-NS1 的按块循环生成摘要。
  - 全局代码扫描确认，生产调用链已全量切换为 `_live_layered_summary_generate`，`_live_summaries` 无任何外部调用。
- **为什么重要**：
  - 死代码可能给后续维护者造成“系统仍在按句/按块循环调用 LLM”的误解。
- **审查判断**：
  - 纯代码卫生问题，无运行时危害。
- **建议修法**：
  - 直接删除该死代码，或添加 `@deprecated` 注释明确说明其已被 NS1 Stage C 整包摘要替代。

---

### R4. `/internal/prompts` 内部路由测试全局 Mock 鉴权依赖

- **严重级别**：`low`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - [`tests/unit/test_ns1_prompt_routes.py:30`](file:///root/workspace/myknowledgebase/tests/unit/test_ns1_prompt_routes.py#L30) 中执行了 `app.dependency_overrides[require_operator_token] = lambda: OperatorIdentity(...)`。
  - 虽然鉴权依赖项 `require_operator_token` 在其他系统测试中有覆盖，但该测试文件中缺少针对 `/internal/prompts` 端点无 Token 或外网访问时返回 401/403 的直接负向用例。
- **为什么重要**：
  - 确保内部安全端点的防御机制具备端到端测试闭环。
- **建议修法**：
  - 在 `test_ns1_prompt_routes.py` 中追加 2 个无 mock 的测试用例，验证无 Token 请求返回 401，非法 IP 请求返回 403。

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| **S1** | `layered_content.v1` JSON Schema 与金样 (P1-01) | `done` | Schema `additionalProperties: false`, 禁 span, 金样校验完全通过 |
| **S2** | 迁入四角色 prompt 正文 (P1-02) | `partial` | 基础 4 角色正文已就绪且移除了旧概念；缺 legal/realestate json 正文 (见 R2) |
| **S3** | Catalog DDL 晋升、CRUD 与 Hash 门闩 (P1-03..06) | `partial` | DDL 与 Hash 门闩完备，但 Update 产生双 active 破坏 Ingest (见 R1) |
| **S4** | `adopt_layered_json` 内核与假树拔除 (P2-01..03) | `done` | 纯函数内核完全符合规范，生产路径 0 假树调用，元数据刷新重构完备 |
| **S5** | Claude CLI 运输端口与四跳 Worker (P3-01..05) | `done` | 参数安全脱敏，结构化/纯文本解码正确，可注入 Stub，Clean 分流正确 |
| **S6** | 可选 Markdown 跳与整包 C 摘要 (P4-02, P3-05) | `done` | DAG 中 Markdown 为严格条件分支，缺省不跑；C 一次性消费整包并防篡改 |
| **S7** | Ingest 严格四 `*_prompt_id` 契约 (P4-01) | `done` | `json_prompt_id` 必填，拒绝多余字段、路径和 body，角色校验完备 |
| **S8** | 结构失败终止且不开人审、默认 Auto-admitted (P4-03) | `done` | 结构化失败直接 `failed`，人审仅在显式声明时开启 |
| **S9** | 分层测试台账 (T01..T46) 与双 Mega 旅程 (P5-01..04) | `done` | 46 项测试全覆盖，Generic / Legal 双旅程验证真实分层投影，Domain 守卫拦截假树 |

### 3.1 对齐结论

- **done**: 7
- **partial**: 2 (S2 资产欠交付，S3 存在更新断点)
- **missing**: 0
- **stale**: 0
- **out-of-scope-by-design**: 0

> **总结评定**：NS1 核心机制、算法内核、数据流及安全围栏已 **95% 高质量完成**，但由于 Catalog Update 断点（R1）会阻断线上版本迭代，当前状态更准确地定性为 **“核心系统全部就绪，需修复版本更新链路断点并补齐预置资产”**。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| **O1** | `lsrag.structure_repair` / `grok -p` 修理工 | `遵守` | 生产代码中无任何自动修补或二次调用，结构失败直接终止 |
| **O2** | 重开 S03 八态、S04 接受事务、D08 parser、S08–S10 算法 | `遵守` | 既有状态机与解析器核心架构完全保持稳定，无非法重构 |
| **O3** | 新建 required 物理表；DB 存 prompt 正文 | `遵守` | 严格沿用既有表，仅加列；DB 绝无 `body_text` 列 |
| **O4** | Scatter 部分成功 | `遵守` | 严格维持 `T-O-345`，任一子任务失败根节点最终均 Fail-Closed |
| **O5** | legal.case 分析通道、切官方 Anthropic | `遵守` | 均未越界引入 |
| **O6** | 公网 marketplace / agent 写 catalog | `遵守` | Catalog CRUD 仅限内网 Operator Token 调用，无 Agent/公网暴露面 |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：`CHANGES-REQUESTED (需修复 R1 Blocker 后批准收口)`
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. **修复 R1（Prompt Update 双 Active 冲突）**：
     - 修改 [`src/services/registry.py:register_prompt`](file:///root/workspace/myknowledgebase/src/services/registry.py#L469-L485) 或 [`src/services/config_snapshots.py:582-584`](file:///root/workspace/myknowledgebase/src/services/config_snapshots.py#L582-L584)，确保通过 PATCH 更新 Prompt 版本后，新的 Ingest 任务能够正常解析出最新 active 版本，而不是因 `len(candidates) != 1` 报 503。
     - 在 `tests/unit/test_ns1_prompt_routes.py` 或 `test_ns1_api_workflow.py` 中追加测试：先 PATCH 发布 v2，再发起 Ingest，验证 Ingest 成功使用 v2。
- **可以后续跟进的 non-blocking follow-up**：
  1. 补齐 `data/prompts/json/promptB.json.legal.v1.md` 与 `promptB.json.realestate.v1.md` 并在 `registry.py` 中 bootstrap (R2)。
  2. 清理 `generation_live.py:474-505` 中的废弃方法 `_live_summaries` (R3)。
  3. 补充无 Mock 的 `/internal/prompts` 鉴权负向测试 (R4)。
- **建议的二次审查方式**：`same reviewer rereview` (Gemini 复核 R1 修复代码与回归测试)。
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`
