# 调查面 01 · 声明式 Workflow 图代数与 kind 家族迁移 — 深度评估

> **对象 / scope-fence**：Workflow 七表 steps/routes/guards/bindings/control/join 的表达力；四 kind 图 identity；13 single + 2 scatter identity；active/compat revision；kind 家族迁移时旧 pinned revision 如何共存；selected-output merge 是否能在不复制整条 publication tail 的情况下表达。
> **本面不含**：actual S05 digest 字段生命周期、seal CAS、recovery 窗口（交面 `02`）；representation / acquire / decode facts（交面 `03`）；clean strategy taxonomy（交面 `04`）；横切 replay/mega proof 清单（交面 `09`）。
> **日期**：`2026-08-29`
> **作者**：`Grok analysis-fleet / review-fleet`（fleet / panel：`new-harvest-reference-anchor`）
> **文档性质**：`assessment / analysis`（单面 measure-first 深评；零决策——只 MARK 不裁决）
> **文档状态**：`draft`
> **流水线位置**：站② · 上游 = [[assessment-index]]（消费其冻结分母）
> **对照参考**：HEAD `1221aa1`；QNA v0.5 `T-O-376..389`（只 CITE）；`docs/baseline/domain-truth/S03-workflow-engine.md` `S03-T007/T011/T012/T013/T017/T038/T053`；`D08-T002`；legacy-family clean 部分；Temporal / AWS Step Functions / CWL 1.2 / Airflow / BPMN-Camunda 官方页（访问日 `2026-08-29`）
> **上游权威输入**：
> - `docs/eval/new-harvest/assessment-index.md` — §2.2 冻结分母 `D-01`、`D-05..D-11` / §1 本面登记 / §3.01 / §7 / §8.1
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` — `T-O-377/379/382/384/387/388`（只 CITE，不扩冻）
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `pre-charter-qna.md`（owner-gate 裁决）· 设计/执行制品

---

## 0. Verdict（结论先行）`[核心]`

- **0.1 一句话缺口 / 现状判断**：HEAD 已有可复用的静态无环七表编译器、登记守卫 fail-closed、caller 禁 `workflow_key`、同 key 的 pinned compat revision；但 **不能** 在不复制 publication tail 的前提下表达 selected-output merge，也 **没有** kind 家族图（13 张 profile 线性图 + `acquisition_mode`/`media_type` 选图）。现 substrate 对「加静态节点/边」可组合，对「同 revision 多 acquire/clean 边 + 选边后并入单一下游 port」需净新 graph algebra。
- **0.2 Top blockers（最关键断点）**：
  1. `NH-RA01-B01`：单 input port 只能一条 binding（编译器 + DDL unique），无 one-of / merge-control → 七表现状表达不了 selected-output merge。
  2. `NH-RA01-B02` + `NH-RA01-B04`：守卫闭集 5 种且 0 条 representation-aware；factory 每图固定 acquire/decode/clean 三槽替换，不是同 revision 预声明多边。
  3. `NH-RA01-B03` + `NH-RA01-B06`：选图仍是 7 个 public profile key（mode/media 参与），6 张 live 图 caller 选不中；与 `T-O-387` 四 kind 家族冲突。
- **0.3 总体方向建议**（非裁决）：沿用七表 + 无环 + 登记守卫 + pinned revision 底座（`♻️重 substrate`）；把 kind 身份、representation 谓词、selected-output 并入点列为净新缝并 MARK `G-NH-02` / `G-NH-09` / `G-NH-03`（图消费侧）。禁止把 Temporal/Step Functions/CWL/Airflow 引擎或 legacy `action_branch` 写成落地栈。
- **0.4 如何读本台账**：见模板图例。本面主题轴 = **图表达力** / **kind 家族 identity** / **compat 共存** / **selected-output merge**。QNA 是目标法，不是 HEAD 已实现。

---

## 1. 方法与证据基线 `[核心]`

> 读了哪些代码/文档/参考；什么算可采信；怎么复现。**先证可证性，再下判断。**

- **1.1 本仓证据（如何测量）**：
  - HEAD 代码：`src/contracts/workflow/models.py`、`src/runtime/workflow/runtime_materialize.py`、`src/runtime/workflow/runtime_core.py`、`src/workflows/lsrag_definition.py`、`src/workflows/builtin_scatter.py`、`src/workflows/builtin_lsrag.py`、`src/workflows/lsrag_historical.py`、`src/services/workflow_registry.py`、`src/services/config_snapshots.py`、`src/runtime/task/task_create.py`、`src/services/registry.py`、`api/app.py`、`src/persistence/migrations/001_initial.sql`
  - 测试：`tests/unit/test_workflow_revision_compatibility.py`、`tests/unit/test_intake_source_capabilities.py`
  - Baseline：`docs/baseline/domain-truth/S03-workflow-engine.md`、`docs/baseline/domain-truth/D08-legacy-capabilities-migration.md`、`docs/baseline/spec-glossary.md`
  - QNA：`docs/eval/new-harvest/pre-initial-planning-qna.md`（`T-O-377/379/382/384/387/388` 只 CITE）
  - Index 冻结分母：`D-01`、`D-05..D-11` 原样引用；本面另测 `F01-D01..F01-D08`
- **1.2 外部 / 参考来源 + 置信**：

| 原子问题 | 搜索词（实际） | Primary URL | 版本/发布 | 访问日 | 支持的原子结论 | 限制/失败条件 | 置信 |
|----------|----------------|-------------|-----------|--------|----------------|---------------|------|
| 静态 DAG 上的条件分支 | `AWS Step Functions Choice state Map item selector official` | https://docs.aws.amazon.com/step-functions/latest/dg/state-choice.html | AWS SFN Developer Guide（页内 2026-08 抓取） | 2026-08-29 | Choice 是状态机定义里的静态规则表；按序取第一条真规则 | 无命中且无 `Default` → *failure to transition* | 高（官方） |
| 选边记录 vs 改图 | `site:temporal.io workflow versioning patches deterministic replay` | https://docs.temporal.io/develop/typescript/versioning | Temporal TS SDK Versioning | 2026-08-29 | `patched()` 把 marker 写入 Event History；Replay 必须再产出同一 marker | 未 patch 的 command 重排 → nondeterminism。页面仍警告 experimental Worker Versioning **March 2026 移除**（访问日 2026-08-29 已是过去时）；GA 以 Worker Versioning 为准。**本仓本来就不借** | 高（官方） |
| pinned execution 共存 | 同上 + `Safely deploying changes to Workflow code` | https://docs.temporal.io/develop/safe-deployments | Temporal safe-deployments | 2026-08-29 | Pin 到单一 code revision，或用 replay test 证明新代码兼容旧 history | Eager start 不尊重 Worker versioning | 高（官方） |
| selected-output merge | `CWL Common Workflow Language conditional step when expression official specification pickValue` | https://www.commonwl.org/v1.2/Workflow.html | CWL Workflow v1.2.1（标准 2020-08-07 批准；v1.2.1 澄清） | 2026-08-29 | `when` 跳过步骤产出 null；`pickValue` 从多 source 选非空 | **规范单源**（CWL 标准本身）。**Expressions（含 `when`）为 optional feature**；无表达式的 runner 不能实现 `when`。没有单独名叫 conditionals 的 optional feature 标题 | 高（规范）/ 落地须降级 |
| XOR join 失败模式 | `Apache Airflow branching TaskFlow official skip downstream` | https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html | Airflow 3.3.1 Docs | 2026-08-29 | 未选中边标 `skipped`；默认 `all_success` 会使 join 被级联 skip | 必须改 trigger rule，否则「能分支但不能汇合」 | 高（官方） |
| XOR 是否合并数据 | `BPMN exclusive gateway XOR join` | https://docs.camunda.io/docs/components/modeler/bpmn/exclusive-gateways/ | **Camunda 8.9 XOR 实现转述**（未打开 OMG 2.0 PDF） | 2026-08-29 | Exclusive split 只走一条；**joining XOR 是 pass-through，不合并并发 token/数据** | 无条件且无 default → incident。**不是** OMG official specification 正文 | 中（实现转述） |

- **1.3 ★ 可复现命令清单（measure-first）**：

```bash
# 共享分母（须与 index §2.2 对齐，不得另估）
uv run python - <<'PY'
from src.services.registry import DEFAULT_SOURCE_KINDS
from src.workflows.lsrag_definition import (
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    BUILTIN_SOURCE_PROFILE_WORKFLOWS,
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
)
from src.workflows.builtin_scatter import (
    BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW,
    BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW,
)
single = (BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, *BUILTIN_SOURCE_PROFILE_WORKFLOWS)
public = set(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.values())
print("source_kinds", len(DEFAULT_SOURCE_KINDS))
print("single_root_identities", len(single))
print("public_selector_keys", len(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS))
print("unselectable_single_identities", sum(x.workflow_key not in public for x in single))
print("scatter_identities", 2)
PY

# 本面专属分母
uv run python - <<'PY'
from src.contracts.workflow.models import WorkflowStepKind, WorkflowRouteKind
from src.workflows.lsrag_definition import BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, BUILTIN_SOURCE_PROFILE_WORKFLOWS
from src.workflows.builtin_scatter import BUILTIN_SCATTER_WORKFLOWS
from src.workflows.builtin_lsrag import BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS
all_defs = [BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, *BUILTIN_SOURCE_PROFILE_WORKFLOWS, *BUILTIN_SCATTER_WORKFLOWS]
print("join_steps", sum(1 for d in all_defs for s in d.steps if s.step_kind is WorkflowStepKind.JOIN))
print("join_routes", sum(1 for d in all_defs for r in d.routes if r.route_kind is WorkflowRouteKind.JOIN))
print("compat_count", len(BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS))
print("inline_steps_routes", len(BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.steps), len(BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW.routes))
PY

# 守卫闭集与单 binding 约束（行号以本次 read 为准）
nl -ba src/contracts/workflow/models.py | sed -n '99,105p;245,278p;418,525p'
nl -ba src/runtime/workflow/runtime_materialize.py | sed -n '49,168p;428,441p;505,514p'
nl -ba src/services/workflow_registry.py | sed -n '78,104p;88,95p'
nl -ba src/workflows/lsrag_definition.py | sed -n '881,940p;1003,1080p'
nl -ba src/services/config_snapshots.py | sed -n '492,516p'
```

- **1.4 范围围栏**：本面**只**覆盖声明式图代数、kind 家族 identity、compat revision 共存、selected-output merge 表达力。actual S05 digest/seal/recovery 不在此（面 `02`）；representation fact 权威不在此（面 `03` 拥有，本面只消费「图能否读该 fact」）；clean 策略名单不在此（面 `04`）；replay/mega 矩阵不在此（面 `09`）。

---

## 2. 当前结构分析（HEAD 实测 · measure-first）★ `[核心]`

> 按主题轴逐条测，每条钉 `path:line`。先冻结本面分母，再逐轴展开。

### 2.1 ★ 冻结分母（FROZEN denominators · HEAD）

> 共享行原样引用 [[assessment-index]] §2.2；本面专属行另测。下游不得另估共享值。

| 分母 | HEAD 实测值 | 证据锚（`path:line`） | 来源 |
|------|-------------|------------------------|------|
| `D-01` source kind | `4` | `src/services/registry.py:171-208` | index §2.2 |
| `D-05` single-root Workflow identity | `13` | `src/workflows/lsrag_definition.py:612-714,943-1069`；本次脚本 `single_root_identities=13` | index §2.2 |
| `D-06` public selector / unselectable | `7 / 6` | `lsrag_definition.py:929-940` vs `1003-1069` | index §2.2 |
| `D-07` scatter identity | `2`（root + child） | `builtin_scatter.py:352-380,571-599` | index §2.2 |
| `D-08` guard predicate / operator | `5 / eq-only` | `models.py:249-256` | index §2.2 |
| `D-09` representation-aware guard | `0` | `models.py:249-255`；`runtime_materialize.py:101-117`；本次脚本无 REP GUARD HIT | index §2.2 |
| `D-10` 单 target input 可声明 source binding 数 | `1` | `models.py:496-497`；DDL `001_initial.sql:1770-1771` `ux_workflow_binding_slot` | index §2.2 |
| `D-11` runtime registered CONTROL 实现 | `2`（human review / scatter join） | `runtime_materialize.py:505-514` | index §2.2 |
| `F01-D01` 每张 single-root 图 step 数 | `17`（13 张全同） | 本次脚本 | 本面新测 |
| `F01-D02` route 数 | inline `51`；其余 single `45`；scatter root `24`；scatter child `17` | 本次脚本 | 本面新测 |
| `F01-D03` JOIN step / JOIN route 使用 | `0 / 0` | 本次脚本；`src/workflows/**` 无 `WorkflowStepKind.JOIN` | 本面新测 |
| `F01-D04` compatibility 计划数 | `16`（含 scatter-child pre-markdown 1 + single 历史） | `builtin_lsrag.py:40-44`；本次脚本 | 本面新测 |
| `F01-D05` 多 binding 命中同一 port 的图 | `0` | 本次脚本 `multi_binding_graphs=0` | 本面新测 |
| `F01-D06` 图内 CONTROL key 闭集 | `{human_review_gate, scatter_children_join}` | 本次脚本；`runtime_materialize.py:505-514` | 本面新测 |
| `F01-D07` 选图是否消费 `acquisition_mode`/`media_type` | `是`（http mode∈{static,browser,pdf}；local media pdf/image） | `config_snapshots.py:500-516` | 本面新测 |
| `F01-D08` 每图 acquire/decode/clean 槽位数 | `1 / 1 / 1`（factory 三槽替换） | `lsrag_definition.py:913-925` | 本面新测 |

### 2.2 轴「方向正确 / 代码已有 / 代码缺失 / 旧 Truth 冲突」

> 强制把 QNA 目标法与 HEAD 实现分列，避免把 `T-O-384/387/388` 写成已实现。

#### 方向正确（QNA / S03 目标法 · 非 HEAD 事实）

- `T-O-384`：晚绑定住在**同一 immutable revision**；预声明 live 边；只用已登记 guard/control 选边；选边后封闭 digest；禁止表外暗调 `process_key`。
- `T-O-387`：选图键 = 四 `source_kind`；三张 single-root kind 图 + `registered_api` scatter 对；`acquisition_mode`/`media_type` **不再选图**。
- `T-O-388`：mode 只是起点边；绑定清洁工人前允许有限正向再获取；不同 `step_key`、禁止自边/环。
- `T-O-379` / `T-O-377`：三轴取值；caller 不得点名 `workflow_key`；禁 `action_branch` taxonomy。
- `S03-T011/T012/T007/T017`：无环、登记谓词无自由表达式、active pointer + 已激活 revision immutable、Execution 创建绑 exact revision。

#### 代码已有（HEAD 正例 · 可复用 substrate）

- **静态无环 + terminal coverage 编译器**：`WorkflowDefinition._validate_graph` 禁止自边（`models.py:389-390`）、DFS 环检测（`418-432`）、start 可达（`441-443`）、每步可达 terminal（`445-460`）、PROCESS/CONTROL 必须覆盖 succeeded/failed/cancelled（`462-474`）。
- **登记守卫、缺键 fail-closed**：predicate 闭集 5 种、operator 仅 `eq`（`models.py:249-256`）；runtime 缺 context 键 → False（`runtime_materialize.py:110-113`）。
- **caller 禁 `workflow_key`**：`resolve_for_source` 只用 purpose + source_kind/profile（`workflow_registry.py:78-88,91-103`）。
- **compat revision（同 workflow_key）**：runtime 按 Execution 存储的 `compiled_digest` 取计划，**不**取当前 active 图（`runtime_core.py:591-597,615-621`）；`api/app.py:304` 注入 `BUILTIN_EXECUTION_COMPATIBILITY_WORKFLOWS`；单测证明 v1 pinned Execution 在 v4 active 后仍走旧 process_key 序列且 revision_uuid 不变（`tests/unit/test_workflow_revision_compatibility.py:106-168`）。
- **optional predecessor 跳过**：construct 两 optional port + 注释（`lsrag_definition.py:185-193`）；runtime 对未成功的 optional prior_output `continue`（`runtime_materialize.py:435-441`）。**只证明「未访问 optional 不当事故」**，不证明 selected-output merge。
- **human_review CONTROL + BRANCH guards**：admission_result 三值选边（`lsrag_definition.py:366-383`）；CONTROL 实现打开 durable gate（`runtime_materialize.py:513-534`）。
- **scatter CONTROL join**：`scatter_children_join`（`runtime_materialize.py:505-512`；`builtin_scatter.py:154-156,352-358`）。这是 collect-all fan-in，不是 XOR selected-output。

#### 代码缺失（相对 `T-O-384/387/388`）

- 无 one-of binding / 无 merge-selected-output CONTROL。
- 无 representation/media/acquire/strategy predicate。
- 无同 revision 多 acquire/decode/clean 边：factory 三槽替换（`lsrag_definition.py:913-925`）。
- 无 kind 家族 identity：resolver 映射 7 个 profile key（`SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS` `929-940`）。
- 6 张 live 图不在 public selector（vision/doc-llm/web-llm/browser-web-llm/pdf-understanding/print-pdf）。
- `WorkflowStepKind.JOIN` / `WorkflowRouteKind.JOIN` 在定义层存在（`models.py:32,52`）但 **0 张图使用**（`F01-D03`）。

#### 旧 Truth / 叙事冲突（显式登记，不自动覆盖）

| 声称 | HEAD 实测 | 失真类型 | 证据 |
|------|-----------|----------|------|
| QNA `T-O-387`「今日选不中的 5 张图」 | unselectable = **6** | 低估（index §2.4 已校正） | 本次脚本；`1003-1054` |
| human_review 已证明晚绑定图 | 只证明登记 BRANCH + CONTROL waiting；无 representation context、无 merge | 类比过度 | `runtime_materialize.py:119-168,505-514`；`D-09=0`；`D-10=1` |
| compat definitions 足以支撑 kind 家族迁移 | compat **必须** `workflow_key ∈ active keys`（`runtime_core.py:93-95,608-614`）；同 key 升 revision 是正例，**key 塌缩不是** | 外推 | 见 §2.4 |
| S03-T053「创建即有 actual S05 digest」vs `T-O-384` 选边后封闭 | HEAD `s05_binding_digest=domain_binding_digest` 在 Task 创建写入 | 跨面冲突，权威交面 `02` | `task_create.py:179-180`；本面只消费「图选边时刻」 |
| glossary `BindingSource` 含 `literal` | Pydantic `WorkflowBindingSourceKind` **无** `literal`（`models.py:99-105`）；DDL 有（`001_initial.sql:551-553`） | schema 宽于合约 | 不构成本面 S1 |
| D08-T002 禁止把 branch 登记为 workflow_key taxonomy | HEAD 仍用 13 个 `intake.ingest.single.*.lsrag.v1` 冒充 profile | 未收敛 | `lsrag_definition.py:929-1054` |

### 2.3 轴 A · 七表表达力（HEAD 核验）

七表物理存在：`mkb_workflow_registry/revisions/steps/routes/bindings/controls/guards`（`001_initial.sql:447-669`）。定义层对应 steps/routes/bindings/guards；CONTROL 以 `step.control_key` 出现，join 以 route_kind 建模但未使用。

**编译期能证明的**：单 start、无环、required reachability、terminal coverage、guard 必须被 route 引用、priority 对 (from, selector) 唯一、单 port 单 binding。

**运行期能证明的**：按 priority 扫描候选边；第一条非 fan_out 命中即停（`runtime_materialize.py:63-73`）；fan_out 可累积多条。守卫只读 `_typed_route_context_tx` 的五类事实：`request_intent` / `admission_result` / `metadata_disposition` / `markdown_selection` / `admission_markdown_selection`（`119-162`）。**没有任何 representation / media_type / acquisition_mode / clean_strategy 进入 route context。**

**不能证明的**：同一下游 required port 从多条成功 clean 边择一；图内「再获取」第二条 acquire（会被「单 acquire 槽 + 单 binding」挡住，即便编译器允许不同 `step_key` 的第二个 PROCESS 节点）。

### 2.4 轴 B · 13+2 identity vs 四 kind 家族

Public 7 key（`929-940`）：

| profile selector | workflow_key |
|------------------|--------------|
| `inline_payload` | `intake.ingest.single.inline.lsrag.v1` |
| `local_object` | `intake.ingest.single.local-object.lsrag.v1` |
| `local_object.pdf` | `intake.ingest.single.local-pdf.lsrag.v1` |
| `http_resource.static` | `intake.ingest.single.http-static.lsrag.v1` |
| `http_resource.browser` | `intake.ingest.single.http-browser.lsrag.v1` |
| `http_resource.pdf` | `intake.ingest.single.http-pdf.lsrag.v1` |
| `local_object.image` | `intake.ingest.single.local-ocr.lsrag.v1` |

Unselectable 6（`1003-1054`）：vision-rejected / doc-llm / http-web-llm / http-browser-web-llm / local-pdf-understanding / **http-browser-print-pdf**。

`ConfigSnapshotService._source_profile` 用 `http_resource.{static,browser,pdf}` 和 `local_object.pdf` / `local_object.image` 选图（`config_snapshots.py:500-516`）。这直接违反 `T-O-387`「mode/media 不再选图」。未知 http mode 返回 `None` → resolver 503（`workflow_registry.py:101-102`）。

`print-pdf` 被做成**独立** `workflow_key`（`1048-1054`），且 **不在** public map，与 kind 家族「http_resource 图内含 print 边」冲突。

Scatter 2 identity 与 `T-O-387`「registered_api 维持 scatter、不并入 mega」**对齐**，是正例（`builtin_scatter.py:1-6,30-31`）。

### 2.5 轴 C · factory 线性图 vs 同 revision 多边

`_source_profile_workflow` 复制整份 `_pre_metadata_refresh_execution_document()`，再替换三个 `process_key`（`881-926`）。注释写明「each source/profile has its own workflow identity」「shared LS-RAG tail stays byte-for-byte」——即 **用复制整图换取 tail 字节稳定**，而不是一张 kind 图上预声明多 acquire/clean 边。结果：13 张 17-step 图，publication tail（structurize→construct→vectorize→validate_publication）被复制 13 次。

线性骨架（所有 single-root 共用 step_key 名）：

```text
start
  ├─[intent=index.rebuild]→ index_rebuild → succeeded
  └─[else]→ acquire ─→ decode ─→ clean ─→ seal ─→ preflight ─→ accept
                                              ├─[update_metadata]→ construct → …
                                              ├─[auto+markdown]→ transcribe_markdown → structurize → construct → vectorize → publication
                                              ├─[auto]→ structurize → construct → …
                                              ├─[human_review]→ human_review CONTROL → (markdown|structurize)
                                              └─[rejected]→ failed
```

`T-O-384/387/388` 要求的 kind 家族图（目标法，非 HEAD）：

```text
caller typed source_kind ──resolve──► 一张 http_resource revision（例）
start
  ├─ acquire.static ──decode.html──┬─ clean.web
  │                                └─ clean.web_llm
  ├─ acquire.browser ─decode.html──┬─ clean.web
  │                                └─ clean.web_llm
  └─ acquire.print ──decode.pdf───┬─ clean.pdf_text
                                  └─ clean.pdf_llm
         │
         ▼  selected-output merge（同一 clean_candidate port）
        seal → preflight → accept → [LS-RAG tail 一份]
守卫读 representation fact（面 03 拥有）；非法跨 kind 边不画。
```

HEAD 缺的不是「能不能再声明一个 PROCESS 节点」（编译器允许不同 `step_key`），而是：(1) 选图身份；(2) representation 谓词；(3) 多条成功边如何并入**同一个**下游 port。

### 2.6 轴 D · compat：正例范围与不够之处

正例范围：

- 同一 `workflow_key` 升 `revision_number`（inline 现 rev=4，历史 v1/v2 仍可执行）。
- `_without_ns1_markdown_branch` 为 13 张 single 各生成 `revision_number - 1` 的 pre-markdown 计划（`1073-1080`）。
- scatter child 另有 pre-markdown rev=1（`builtin_scatter.py:602-639`）。
- Execution 行钉 `workflow_uuid + workflow_revision_uuid + compiled_digest`（`task_create.py:176-178`）。
- registry `register()` 遇新 revision_number 则 **insert 新行、不 mutate 旧 revision**（`workflow_registry.py:179-184`）。

不够之处（kind 家族迁移）：

1. `compatibility definition must belong to an active workflow key`（`runtime_core.py:93-95`）。若退役 `intake.ingest.single.http-static.lsrag.v1` 且不把它留在 `additional_definitions`，旧 Execution 409 `workflow-binding-mismatch`。
2. bootstrap **只** register 当前 `BUILTIN_WORKFLOWS`（`workflow_registry.py:64-66`），compat 计划靠内存 map + 库内历史 revision 行；key 塌缩不是这条路径覆盖的场景。
3. 因此：compat 是「同 identity 的 immutable revision 共存」正例，**不是**「13 key → 3 kind key」的迁移正例。

### 2.7 轴 E · human_review 能证明什么、不能证明什么

| 能证明 | 不能证明 |
|--------|----------|
| 登记 BRANCH 按 durable `admission_result` 选边 | 表示已知后选 acquire/clean |
| CONTROL 打开 exact gate，缺证据 fail-closed | 多条 live clean 边预声明 |
| 未命中 guard 不 materialize 下游 PROCESS | selected-output merge |
| 与 scatter 共用同一 CONTROL 入口分发 | kind 家族选图 |

结论：human_review 是**局部类比**（静态边 + 登记谓词 + 晚于某 Process Outcome 的分支），不是晚绑定 kind 图的存在性证明。

### 2.8 四个必须回答

1. **不复制整条 publication tail 时，当前七表能否表达 selected-output merge？**  
   **不能。** 编译器拒绝同一 input port 第二条 binding（`models.py:496-497`）；DDL unique `ux_workflow_binding_slot`（`001_initial.sql:1770-1771`）同样拒绝。optional 多 port 是**不同类型槽**的跳过，不是同 schema 多源择一。CONTROL 闭集无 merge-selected-output。复制 13 张整图（含 tail）是现状绕法，正是题目要排除的。

2. **kind graph 新 identity 如何与旧 pinned revision 共存？compat 是正例还是不够？**  
   **同 key 升 revision = 正例；key 家族塌缩 = 不够。** 旧 pinned 依赖 `workflow_key` 仍属 `_active_workflow_keys` 且 compiled plan 在内存 map 中。要把 13 个 key 收成 3 张 kind 图，必须另做 identity 共存设计（保留旧 key 为 active-but-unselected，或新 gate 改 binding 检查）。本面只 MARK，不裁。

3. **现 substrate 是「可组合」还是「需净新 graph algebra」？**  
   **混合：节点/边可组合；merge / representation predicate / kind identity 需净新 algebra。** 钉到四块缺失：one-of binding、merge-control、representation predicate、同 revision 多 acquire 边（factory/resolver 层，非编译器禁第二 `step_key`）。

4. **human_review 分支能证明什么、不能证明什么？**  
   见 §2.7。局部类比 ✅；晚绑定 kind 图 ❌。

---

## 3. 借鉴锚定矩阵（Reference Anchor Matrix）★ `[核心]`

> 每个可借鉴点钉到 `path:line` / URL，给**借鉴 verdict**。这是「能借什么」的台账，不是设计决策。

| 锚 ID | 借鉴点 | 来源锚（`path:line` / URL） | 借鉴 verdict | 借什么 / 不借什么 |
|-------|--------|------------------------------|--------------|--------------------|
| `RA-01-HEAD-01` | 静态无环 + terminal coverage 编译器 | `src/contracts/workflow/models.py:389-390,418-474` | `✅借` | 借：registration-time 无环/可达/覆盖。不借：把编译通过当成 kind 家族完成。 |
| `RA-01-HEAD-02` | 登记守卫缺键 fail-closed | `runtime_materialize.py:86-117`；`models.py:245-278` | `✅借` | 借：闭集 + eq + 缺键 False。不借：把现 5 谓词当成 representation 谓词。 |
| `RA-01-HEAD-03` | caller 禁 `workflow_key` | `workflow_registry.py:78-88` | `✅借` | 借：purpose+kind 选图入口。不借：今日 profile 二级键。 |
| `RA-01-HEAD-04` | 同 key pinned compat revision | `runtime_core.py:591-621`；`lsrag_definition.py:1073-1080`；`test_workflow_revision_compatibility.py:106-168` | `✅借` | 借：digest 钉计划、不热切 active。不借：当作 kind-key 塌缩方案。 |
| `RA-01-HEAD-05` | optional predecessor 跳过 | `lsrag_definition.py:185-193`；`runtime_materialize.py:435-441` | `🔶部分借` | 借：「未访问 ≠ 事故」。不借：当作 selected-output merge。 |
| `RA-01-HEAD-06` | 单 port 单 binding | `models.py:496-497`；`001_initial.sql:1770-1771` | `⛔反例`（相对目标法） | 这是 HEAD 对 merge 的硬拒绝；不是产品反模式，是缺口证据。 |
| `RA-01-HEAD-07` | 无 representation predicate | `models.py:249-255`；`runtime_materialize.py:101-117`；`D-09=0` | `⛔反例` | 守卫看不见表示。扩展须登记，禁止自由表达式。 |
| `RA-01-HEAD-08` | factory 三槽替换 + 整图复制 | `lsrag_definition.py:881-926` | `⛔反例` | 证明「复制 tail」是当前唯一绕法。 |
| `RA-01-HEAD-09` | 7 public / 6 unselectable | `929-940,1003-1054` | `⛔反例` | live 矩阵图 caller 选不中。 |
| `RA-01-HEAD-10` | print-pdf 独立 workflow_key | `1048-1054` | `⛔反例` | 与 `T-O-387` http_resource 图内 print 边冲突。 |
| `RA-01-HEAD-11` | CONTROL 仅 2、无 merge | `runtime_materialize.py:505-514` | `⛔反例` | scatter join ≠ XOR merge。 |
| `RA-01-HEAD-12` | compat 必须挂 active key | `runtime_core.py:93-95,608-614` | `🔶部分借` | 借：防孤儿计划。限制：挡 key 退役。 |
| `RA-01-HEAD-13` | mode/media 选图 | `config_snapshots.py:500-516` | `⛔反例` | 违反 `T-O-387`。 |
| `RA-01-HEAD-14` | JOIN kind 未使用 | `models.py:32,52`；`F01-D03=0` | `🔶部分借` | 借：schema 预留 join 槽。不借：今日已实现 merge。 |
| `RA-01-LEGACY-01` | universal 6 条能力分叉清单；`browserPDF-geminiClean` **未** register 仍被 switch 接受并强制 Vision | `action_registry.ts:91-148`（无该键）；`cleaner_web.ts:296-301`；`D08-T002` | `🔶部分借` / 暗路由 `⛔` | **借**：web static / browser / print-pdf / doc understanding 映射到三轴。**不借**：`action_branch` 作选图键；**不借**未登记别名。 |
| `RA-01-LEGACY-02` | dispatcher 原样下发 branch | `smind-clean-dispatcher/services/mapper.ts:193-200` | `⛔反例` | 不借：Workers 队列图、SMCP payload 透传 `action_branch`。 |
| `RA-01-LEGACY-03` | dedicated 3 provider branch 当路由 | `smind-skill-clean-dedicated-apis/services/action_registry.ts:59-79`；`flows/router.ts:42-54` | `⛔反例` | 不借：缺 branch 即失败的 worker 内路由。API 分叉属 scatter 内 operation，不是 workflow_key。 |
| `RA-01-LEGACY-04` | structurizer 用 branch 选模型策略 | `smind-skill-rag-structurizer/flows/structurizer.ts:17,184-186` | `⛔反例` | 证明 branch 把 acquire/clean/**model** 绑死。不借任何模型策略回流。 |
| `RA-01-WEB-01` | Temporal pin + patch marker 进 history | https://docs.temporal.io/develop/typescript/versioning ；访问日 2026-08-29 | `🔶部分借` | 借：选择/版本事实进 history，不靠改已 pin 的图。不借：Temporal 运行时、patch API、Worker Versioning 栈。限制：页面仍警告 pre-2025 experimental WV 于 **March 2026 移除**（访问日已是过去时）；GA 以 Worker Versioning 为准。 |
| `RA-01-WEB-02` | Temporal replay 防非确定 | https://docs.temporal.io/develop/safe-deployments ；2026-08-29 | `🔶部分借` | 借：旧 history × 新代码必须 replay。不借：云 Worker 部署模型。限制：eager start 无视 versioning。 |
| `RA-01-WEB-03` | Step Functions Choice 静态规则表 | https://docs.aws.amazon.com/step-functions/latest/dg/state-choice.html ；2026-08-29 | `🔶部分借` | 借：条件边预声明；无命中 fail-loud。不借：JSONata/JSONPath 自由表达式、AWS 引擎。 |
| `RA-01-WEB-04` | CWL `pickValue` 多源选非空 | https://www.commonwl.org/v1.2/Workflow.html （Changelog：`when` + `pickValue`）；2026-08-29 | `🔶部分借` | 借：skipped→null + `the_only_non_null`/`first_non_null` 形式。不借：`when` 表达式、JS sandbox。**规范单源**（CWL 标准）。 |
| `RA-01-WEB-05` | CWL `when` 自由表达式；**Expressions（含 `when`）为 optional** | 同上；「Expressions in CWL are an optional feature」 | `⛔反例` | 与 `S03-T012` 冲突；无表达式的 runner 不能实现 `when`。 |
| `RA-01-WEB-06` | Airflow skip 级联导致 join 假绿/假死 | https://airflow.apache.org/docs/apache-airflow/stable/core-concepts/dags.html §Branching/Trigger Rules ；2026-08-29 | `⛔反例` | 借失败法：XOR 后默认 AND-join 会跳过汇合。不借 Python callable 选边。 |
| `RA-01-WEB-07` | **Camunda XOR 实现转述**：joining XOR pass-through，不合并数据 | https://docs.camunda.io/docs/components/modeler/bpmn/exclusive-gateways/ （Camunda 8.9）；**未**打开 OMG PDF | `🔶部分借` | 借：split≠merge；join XOR 只是 pass-through。不借：FEEL 自由条件。无 default → incident。去掉「official specification」口吻。 |
| `RA-01-BASELINE-01` | S03 七表/无环/登记谓词/pin | `S03-workflow-engine.md` `S03-T007/T011/T012/T013/T017/T038/T053` | `✅借` | 借宪法。冲突项（T053 创建时 digest）交面 02，不在本面改写。 |
| `RA-01-BASELINE-02` | D08 6 分叉不是 kind | `D08-legacy-capabilities-migration.md` `D08-T002` | `✅借` | 借：分叉→acquire×strategy。不借：branch 名当 workflow_key。 |

每条 RA 的原子句 / 正反 / 置信 / substrate-fit / 命中缺口见上表 + §4/§7。置信分层：HEAD 实测 > 仓内文档锚 > 外部参考。

---

## 4. 缺口 / 断点台账 ★ `[核心]`

> 编号稳定，供下游引用。

| 编号 | 缺口 / 断点 | 严重度 | 证据（`path:line`） | 影响 |
|------|-------------|--------|----------------------|------|
| `NH-RA01-B01` | 七表现状无法表达 selected-output merge（单 port 单 binding；无 merge CONTROL） | `S1 阻断` | `models.py:496-497`；`001_initial.sql:1770-1771`；`runtime_materialize.py:505-514` | 同 revision 多 clean 边无法并入 seal 而不复制整图。命中 `G-NH-02`。 |
| `NH-RA01-B02` | 无 representation-aware guard；route context 无表示事实 | `S1 阻断` | `models.py:249-255`；`runtime_materialize.py:101-117,119-168`；`D-09=0` | `T-O-384/388` 的选边没有图内谓词。图消费侧点到 `G-NH-03`（权威在面 03）。 |
| `NH-RA01-B03` | identity 是 13 profile key 而非 3+scatter kind 家族 | `S1 阻断` | `lsrag_definition.py:929-1069`；`D-05/D-06` | 与 `T-O-387` 冲突；非法跨 kind 边靠「根本不画在同一张图」回避，而非 kind 图闭集。 |
| `NH-RA01-B04` | factory 每图固定三槽，不是同 revision 多 acquire/decode/clean 边 | `S1 阻断` | `lsrag_definition.py:913-925`；`F01-D08` | `T-O-388` 再获取无法画成不同 `step_key` 的正向边（现状只有一个 acquire 槽）。 |
| `NH-RA01-B05` | `acquisition_mode`/`media_type` 仍是选图键 | `S1 阻断` | `config_snapshots.py:500-516`；`workflow_registry.py:94-103` | 直接违反 `T-O-387`；未知 mode → 503。 |
| `NH-RA01-B06` | public 7 vs unselectable 6：live 矩阵图 caller 走不到 | `S1 阻断` | `929-940` vs `1003-1054`；`test_intake_source_capabilities.py:253-318` 只测 7+2 resolve_by_key | `T-O-381` live 闭集在图入口不可达。防假绿见 §9。 |
| `NH-RA01-B07` | print-pdf 独立 workflow_key 且不可选 | `S1 阻断` | `1048-1054` | kind 家族要求 print 为 http_resource 图内边。 |
| `NH-RA01-B08` | kind-key 塌缩与 compat「必须 active key」未和解 | `S2 重要` | `runtime_core.py:93-95,608-614` | 只升 revision 不够；退役旧 key 会 409 旧 Execution。交 `G-NH-09` 与面 09。 |
| `NH-RA01-B09` | human_review 被误当成晚绑定完成证明 | `S2 重要` | `runtime_materialize.py:222-232,505-534`；index §2.4 | 规划若停在「已有 BRANCH」会漏 merge/谓词。 |
| `NH-RA01-B10` | JOIN step/route 预留但 0 使用；scatter join 走 CONTROL | `S3 次要` | `models.py:32,48-54`；`F01-D03` | 若选 merge-control，需决定走 JOIN kind 还是新 CONTROL，避免第三通道。 |
| `NH-RA01-B11` | DDL guard operator 宽于合约 eq-only | `S3 次要` | `001_initial.sql:638-640` vs `models.py:256` | 防未来误开 `ne/lt/in_registered_set` 当自由比较。 |
| `NH-RA01-B12` | QNA「5 张选不中」vs HEAD 6 | `S3 次要` | QNA `T-O-387` 行；本次脚本 | 文档分母已冻 6；分析不得再写 5。 |

---

## 5. 跨功能系统一致性 ★ `[核心]`

- **5.1 整体形态一句话**：S03 七表继续当唯一声明式程序 SSOT；面 01 决定「图上能画什么边、怎么选边、identity 几张」；面 02 决定「选中事实何时封闭进 actual digest」；面 03 决定 representation fact 权威；面 04 决定 admitted clean；面 09 证明旧 pinned + 新 kind 图可一起 replay。

- **5.2 功能间一致性契约（不变量 C1..Cn）**：

| 编号 | 不变量 | 跨哪些面/模块 | 违反后果 |
|------|--------|----------------|----------|
| `NH-C-01` | Workflow 定义 SSOT 仍是七张关系表 + 编译派生物；禁止回到 step-list JSON 或 `action_branch` | `01` / S03 / D08 | 绿地边界 `T-O-42/377` 破裂 |
| `NH-C-02` | v1 图必须静态、无环、无自边；再获取 = 不同 `step_key` 正向边 | `01` / `03` / `09` | 业务环或 try-all-acquire |
| `NH-C-03` | 守卫仅登记谓词 + eq-only；禁止 Python/SQL/JS/JSONata/FEEL 自由表达式 | `01` / `03` | 非确定选边、注入面 |
| `NH-C-04` | caller 不得点名 `workflow_key`；选图权威 = `source_kind`（目标法） | `01` / `04` / public API | 开放 workflow_key = 第五种动态路由 |
| `NH-C-05` | Execution 创建钉 exact workflow/revision/compiled digest；同 Execution retry 不热切**图** | `01` / `02` / `09` | 运行中换程序 |
| `NH-C-06` | 若存在 selected-output merge，必须在**同一 revision** 预声明，且并入点不得复制整条 publication tail | `01` / `02` / `08` | 13 张克隆图复发 |
| `NH-C-07` | kind 家族基数：3 single-root + scatter_root/child；mode/media 不是选图键 | `01` / `03` / `04` | 继续 7+6 profile |
| `NH-C-08` | 旧 pinned revision 必须仍能解析到 reviewed 计划；新 kind 图不得重放进旧 digest | `01` / `09` | 升级绞杀旧 Execution 或静默换图 |
| `NH-C-09` | 图消费的 representation fact 权威在面 03；本面只声明「哪类谓词可读哪些 typed fact」 | `01` / `03` / `02` | 两处各发明表示列 |

- **5.3 数据 / 控制流贯穿图**：

```text
TaskCreate (typed source_kind [+ 今日非法的 mode/media])
    │  ConfigSnapshotService._source_profile     ← B05 仍用 mode/media
    ▼
WorkflowRegistry.resolve_for_source(purpose, kind, profile)
    │  今日：7 public key / 6 张 503-or-unselected
    │  目标：kind → 1 of {inline, local_object, http_resource} or scatter_root
    ▼
Execution pin (workflow_uuid, revision_uuid, compiled_digest)  ← NH-C-05
    │
    ▼
Engine._assert_execution_binding → _plans_by_compiled_digest
    │  active graph 与 compat graph 分账
    ▼
route_context (intent/admission/markdown only)  ← B02 无 representation
    │  _guard_matches fail-closed
    ▼
materialize PROCESS / CONTROL
    │  input port ← 恰好一条 binding                ← B01
    │  optional unvisited skip                       ← 局部类比
    ▼
[面 02] 选边 Outcome 后封闭 actual S05 digest（本面不拥有）
    ▼
publication tail（structurize…validate）应一份共享，而非 13 份拷贝
```

- **5.4 与邻面的消费 / 提供**：
  - **提供给 02**：selected-route identity 的图定义（哪条边被 guard 选中）；不提供 digest 生命周期。
  - **消费 03**：representation fact 一旦存在，守卫才能扩展登记；本面不发明 MIME/PDF 层字段。
  - **消费 04**：live clean `process_key` 闭集必须能画在 kind 图上；本面不改 strategy 名单。
  - **提供给 08**：publication tail 应保持一份；merge 发生在 seal 之前。
  - **提供给 09**：compat 计划清单、key 共存约束、防假绿「新图注册但 selector 仍 7」。

---

## 6. 净新契约 / 架构边界草案 `[核心]`

> 无先例可借（或仅部分借）处，从零草拟。**草案，非冻结。不写具体 `guard_key` / `step_key` 字面。**

### 6.1 净新聚合 / 解耦点

| 缝 ID | 聚合点 | 为什么净新 | 草案形态（并列，不裁） |
|-------|--------|------------|------------------------|
| `NH-N-01-01` | selected-output 并入 | CWL `pickValue` 不可直搬（表达式）；HEAD 单 binding；BPMN XOR join 不并数据 | `one-of binding` **或** `registered merge-control` **或** 继续 `graph duplication`（须评估与 `T-O-387` 冲突代价）→ `G-NH-02` |
| `NH-N-01-02` | representation 谓词登记 | 5 谓词闭集无表示；外部 Choice/when 都是自由表达式 | 代码登记新 `predicate_type` + 从 durable fact 投影 eq 操作数；权威 fact 行归面 03（`G-NH-03`） |
| `NH-N-01-03` | kind 家族 identity + resolver | 13 key + mode 选图 | 选图只认 `source_kind`；旧 13 key 的 pinned 共存策略另缝 |
| `NH-N-01-04` | 同 revision 多 acquire/decode/clean 边 | factory 三槽；编译器其实允许不同 `step_key` | 停用「一槽替换」工厂；边必须预声明且无环正向；每个 acquire 步骤至多成功一次（`T-O-388` 法，实现不在本面锁） |
| `NH-N-01-05` | 旧 key 与新 kind key 共存 | compat 要求 active key | 保留旧 key 为 enabled-unselected **或** 扩展 binding 检查 **或** 不塌缩 key（即 duplication） |

### 6.2 净新契约叙述规格

- **输入**：Task 的 typed `source_kind`（及作为**起点边**而非选图键的 acquire 声明——字面不冻）；durable representation fact（面 03）；已登记 guard 闭集。
- **输出**：一张 immutable kind 图上的 selected route identity（哪些 step 被 materialize、哪些被 skip）；单一下游 port 上的一份 admitted 前 clean candidate（merge 之后）；Execution 仍钉原 revision digest。
- **边界失败**：未声明边不得 handler 暗调；无 representation fact 不得匹配表示守卫（fail-closed）；多源若声明 XOR 却出现两个非空 → 完整性失败（CWL `the_only_non_null` 的失败法可 remap）；无命中且无登记 fallback → 失败（Step Functions 无 Default 的失败法可 remap）。
- **不进入本契约**：S05 digest 列、CAS、PDF 引擎、strategy 名单、HTTP 路径。

### 6.3 架构边界（与既有 / 相邻面）

- 不新增第五 source kind。
- 不把 merge 做成 Python if 链或表外 `dispatch_clean`。
- 不把 publication tail 分叉成 per-strategy workflow_key。
- scatter 保持独立 identity（`T-O-387`）。
- `G-NH-09`：若判断「需净新 graph algebra」是否仍放在 new-harvest 施工——**只 MARK**：`NH 内前置 AP` / `独立 engine campaign` / `在不破产品法前提下采用现 substrate 方案（即继续复制图）`。

---

## 7. Substrate-fit / 技术路线过滤 ★ `[核心]`

> 把每个「借来的机制」按本仓路线降级或重映射。能跑但越界 → 最多 `🔶部分借`。

本仓过滤器：单体 Python 3.12 FastAPI、local Turso、S03 七表声明式无环图、eq-only 登记守卫、S13 bytes-first、`T-O-42` 绿地、禁止 CF/R2/SMCP/动态 plugin/自由表达式。

| 借鉴点 | 原机制（参考处） | 是否冲突本仓路线 / 约束 | 落地形态（降级 / 重映射 / 直采） |
|--------|------------------|--------------------------|-----------------------------------|
| HEAD 无环编译器 / fail-closed / pin | `models.py` / `runtime_core.py` | 不冲突 | **直采** 为底座 |
| HEAD optional skip | `runtime_materialize.py:435-441` | 不冲突，但表达力不够 | **降级**：仅作 skip 语义，不作 merge |
| HEAD 13 profile factory | `lsrag_definition.py:881-926` | 冲突 `T-O-387` | **重 substrate**：停用三槽工厂；可暂时保留旧 key 作 compat |
| legacy 6/3 branch 清单 | `action_registry.ts` | 分叉清单不冲突；taxonomy 冲突 `T-O-377` | **部分借** 清单 → 三轴；**禁止** branch 选图 |
| legacy dispatcher 透传 | `mapper.ts:198` | 冲突 SMCP/Workers | **反例**，不落地 |
| Temporal `patched()` marker | Temporal TS versioning | 引擎/history 栈冲突；「选择进 history」不冲突 | **重映射**：route decision payload 已有 `guard_results`（`runtime_materialize.py:74-83`）≈ marker；扩 representation 结果，不引入 Temporal |
| Temporal Worker pin | 同上 / safe-deployments | 多 Worker 部署模型冲突 | **重映射**：已有 Execution 钉 revision_uuid+digest |
| SFN Choice + JSONata | AWS Choice 文档 | JSONata 冲突 `S03-T012`；静态 Choices[] 不冲突 | **重映射**：已登记 guard 列表 + priority；无命中 fail-loud 可借 |
| CWL `when` 表达式 | CWL 1.2 Conditional | 自由 JS 冲突；optional feature 冲突「必须实现」 | **反例** 表达式；只借 skipped=null 语义 |
| CWL `pickValue` | CWL 1.2 Changelog / WorkflowStepInput | 多 source 列表冲突 HEAD 单 binding | **重映射** 到 `G-NH-02` 三选项之一；`the_only_non_null` 失败法可作验收 |
| Airflow `@task.branch` | Airflow 3.3.1 Dags | Python callable 选边冲突 | **反例**；只借「skip 级联杀死 join」失败法 |
| BPMN XOR + FEEL | Camunda exclusive gateway | FEEL 冲突；XOR join 不并数据 | **部分借** split/join 分账；merge 仍净新 |
| SFN Map ItemSelector | AWS ItemSelector | scatter 已有独立图；非本面 S1 | 不借作 selected-output；API scatter 已交付（index §7） |

**🆕 净新（三渠道无 substrate-fit 先例可直采）**：在 **eq-only 登记谓词 + 七表 + 禁止自由表达式** 约束下，把「同 schema 多 prior_output 并入单 required port」做成确定性、可 replay 的代数。CWL `pickValue` 最近但越界；HEAD optional 多 **不同** port 最近但类型不同。故 merge 缝标 `🆕`，同时保留「复制图」为已存在但产品法不允许的绕法。

---

## 8. 反例坑表 + 净新表 `[核心]`

### 8.1 反例坑表 ⛔

| 反例 | 来源锚 | 为什么不可借 |
|------|--------|--------------|
| `action_branch` 当选图/选工人/选模型键 | `action_registry.ts:60,91-162`；`mapper.ts:198`；`structurizer.ts:184-186`；`T-O-377` | 把 acquire×clean×model 压成字符串；回流 Workers 路由 |
| dispatcher / SMCP 透传 branch | `mapper.ts:193-200` | 违反 `T-O-42` 绿地 |
| 自由表达式守卫（JSONata / `when` / FEEL / Python callable） | SFN Choice；CWL Conditional；Camunda conditions；Airflow branch | 违反 `S03-T012`；非确定 + 注入面 |
| 运行中改图 / 热切 revision | Temporal 文档明确非确定风险；`S03-T017` | 破坏 pinned Execution |
| XOR 后用 AND-join 默认规则 | Airflow `all_success` 级联 skip | 假死：选边成功但 tail 不跑 |
| BPMN XOR join 当数据 merge | Camunda：joining XOR pass-through | 并不出单一 clean candidate |
| 用 13 张克隆图冒充 kind 家族 | `lsrag_definition.py` factory | 复制 tail；mode 选图；unselectable live 边 |
| 把 human_review 当晚绑定完成 | index §2.4；本面 §2.7 | 类比过度 |
| 把 monkeypatch / 503 / 空正文当通道 DoD | `T-O-376/378` | 本面 selector 503 尤其危险（未知 profile） |
| Temporal/SFN/CWL/Airflow 引擎本身 | 各官方栈 | 本仓单体 + 七表；禁止写成采用引擎 |

### 8.2 净新表 🆕

| 项 | 为什么无先例 | 草案落点 |
|----|--------------|----------|
| eq-only 登记谓词下的同 schema selected-output merge | CWL pickValue 依赖表达式+多 source；HEAD 禁多 binding | `NH-N-01-01` / `G-NH-02` / §6 |
| kind 家族 identity（3+scatter）替换 13 profile key 且不绞杀旧 pin | Temporal pin 是 code version 不是 relational workflow_key 塌缩 | `NH-N-01-03` / `NH-N-01-05` |
| representation 谓词闭集扩展 | 外部全是自由表达式；HEAD 0 条 | `NH-N-01-02` / 面 03 权威 |
| 同 revision 多 acquire 正向边 + 每步至多成功一次 | legacy 一次性选 branch；HEAD 单槽 | `NH-N-01-04`；观察器语义交面 03 |

---

## 9. 验收格栅草案（防假绿）`[核心]`

> 草案——落地验收归下游执行计划。测试层不可互换。

| 功能 F | 收口目标（一句话可验证） | Test-ID（拟） | 测试层 | 防假绿要点 |
|--------|--------------------------|----------------|--------|------------|
| kind 选图 | 仅凭 `source_kind` 解析到对应 kind 图；mode/media 不再改变 `workflow_key` | `NH-A-01-01` | 单元 + 集成 | 注册新 kind 图但 public selector 仍 7 profile ≠ 完成 |
| live 边可达 | 每条 in-scope live clean/acquire 边出现在对应 kind revision 的 steps 中，且 caller 不必 `resolve_by_key` | `NH-A-01-02` | 单元（定义）+ 集成（resolver） | unselectable 6 张「能 bootstrap」≠ caller 可达 |
| representation 守卫 | 缺 representation context 时表示类守卫 fail-closed，不选边、不暗升 | `NH-A-01-03` | 单元 | unit 编译通过但 runtime 无 representation context ≠ 完成 |
| selected-output merge | 两条预声明 clean 边仅一条成功时，下游单 port 拿到该输出；两条都成功且声明 XOR 时 fail-loud | `NH-A-01-04` | 单元 + 集成 | 复制整图「各跑各的 tail」不算 merge |
| 无环再获取 | 第二 acquire 为不同 `step_key` 正向边；自边/环 registration 失败 | `NH-A-01-05` | 单元 | 同 step retry 不是图上的再获取 |
| pinned compat | 旧 revision Execution 在新 kind 图激活后仍按旧 compiled_digest 跑完，不热切 | `NH-A-01-06` | 集成 | 只测「还能 register 旧定义」不够；必须跑完旧 process_key 序列 |
| 禁 workflow_key / 禁 branch | 公共 Task 合同不含 workflow_key；代码无 action_branch 选图 | `NH-A-01-07` | 单元 / 架构测试 | 内部 `resolve_by_key` 仅限 bootstrap/compat，不得出现在 caller 面 |
| 无自由表达式 | 新谓词必须走闭集登记；注入 JS/SQL 字符串 registration 失败 | `NH-A-01-08` | 单元 | 不得以「SFN Choice 能写 JSONata」为通过依据 |
| default-root 可达 | 默认组合根下 kind 图能 materialize 到 seal（本面到图，live adapter 交 05） | `NH-A-01-09` | default-root e2e | 禁止 monkeypatch browser/http 冒充接线；禁止 503 当 DoD |
| 检索终态不在本面冒充 | 本面完成 ≠ 可检索向量 | （交 `08/09`） | retrieval-facet mega | Task succeeded / publication proof 不足以为本面收口 |

---

## 10. 优先级建造建议 + owner-gate 候选 `[核心]`

- **10.1 建造顺序（依赖序，分批不一次性深做）**：

| 顺序 | 工作簇 | 依赖 | 复用判定 |
|------|--------|------|----------|
| `P0-a` | 冻结「可组合 vs 净新」测量（本文）并交 `G-NH-02/09` | index 分母 | `✅复用` 测量 |
| `P0-b` | 扩展登记谓词骨架（类型槽，不冻字面）+ 消费面 03 fact 形状 | 面 03 最小 representation 合同 | `♻️重 substrate`（守卫表） |
| `P0-c` | kind identity + resolver：停 mode/media 选图 | `G-NH-09` 是否本战役做图 | `♻️重 substrate`（registry） |
| `P0-d` | selected-output 缝的实现（one-of **或** merge-control **或** 明确拒绝并接受 duplication 的产品法代价） | `G-NH-02` 裁决 | `🆕净新` |
| `P0-e` | 把 6 张 unselectable live 边并进 kind 图（不再独立 key） | P0-c/d | `♻️重 substrate` |
| `P1-a` | 旧 13 key pinned 共存证明扩到面 09 | P0-c | `✅复用` compat 路径 + 新 identity 测试 |
| `P1-b` | 停用三槽 factory；单测禁止「复制 tail 算 merge」 | P0-d | `♻️重 substrate` |

- **10.2 owner-gate 候选（只 MARK 不裁决 → 上交 [[assessment-index]] §4 / 下游决策登记）**：

| gate-ID | 决策点 | 候选选项（不预设倾向） | 影响 |
|---------|--------|------------------------|------|
| `G-NH-02` | selected-output merge 如何进入 Workflow | `one-of binding` / `registered merge-control` / `graph duplication（须评估代价）` | 七表 schema/runtime/DDL/migration；本面 S1 `NH-RA01-B01` |
| `G-NH-09` | Workflow substrate 是否留在 new-harvest | `NH 内前置 AP` / `独立 engine campaign` / `在不破产品法前提下采用现 substrate 方案` | 战役范围；若选 duplication 则与 `T-O-387` 对质 |
| `G-NH-03` | representation route fact 的 durable authority（**本面只点图消费侧**） | `Process output evidence` / `正式 representation fact row` / `其他 typed authority` | 守卫可读什么；权威落点交面 03，本面不裁 |

无本面私自新增 `G-NH-11+`。身份共存策略视为 `G-NH-09` 的子问题，不另开 gate。

---

## 11. 核验记录 `[核心]`

> 对抗性自检：关键锚点均经工具核验；与叙事冲突处以实测为准。

| 锚点（host-ID） | 是否核验 | 方式（grep/read/run） | 备注 / 修正 |
|------------------|----------|------------------------|--------------|
| `D-01/D-05..D-11` | `✅` | `uv run python` 分母脚本 | 与 index 一致：kind=4，single=13，public=7，unsel=6，scatter=2，pred=5 eq-only，rep-guard=0，binding=1，CONTROL=2 |
| `RA-01-HEAD-01` `_validate_graph` | `✅` | `read_file` `models.py:418-474` | 行号以本次 read 为准（非 prompt 记忆） |
| `RA-01-HEAD-02` `_guard_matches` | `✅` | `read_file` `runtime_materialize.py:86-117` | 缺键 False 在 110-113 |
| `RA-01-HEAD-03` `resolve_for_source` | `✅` | `read_file` `workflow_registry.py:78-104` | |
| `RA-01-HEAD-04` compat | `✅` | `read_file` `runtime_core.py:88-100,591-625`；`test_workflow_revision_compatibility.py:106-168`；`api/app.py:304` | 修正：compat 必须 active key，不能外推 kind 塌缩 |
| `RA-01-HEAD-05` optional skip | `✅` | `lsrag_definition.py:185-193`；`runtime_materialize.py:435-441` | 明确不证明 merge |
| `RA-01-HEAD-06` 单 binding | `✅` | `models.py:496-497`；DDL `1770-1771` | 编译器 + unique index 双围栏 |
| `RA-01-HEAD-08` factory | `✅` | `lsrag_definition.py:881-926` | |
| `RA-01-HEAD-09/10` 7+6 / print-pdf | `✅` | 脚本 + `1003-1054` | 修正 QNA「5 张」→ HEAD 6 |
| `RA-01-HEAD-11` CONTROL=2 | `✅` | `runtime_materialize.py:505-514` | 修正：报错文案仍写 “Only the bounded human-review”，但 scatter join 先分支；实现仍是 2 |
| `RA-01-HEAD-13` mode 选图 | `✅` | `config_snapshots.py:492-516` | |
| `F01-D01..D08` | `✅` | 本次 python 脚本 | inline 17/51；其他 single 17/45；JOIN=0；compat=16 |
| `RA-01-LEGACY-01..04` | `✅` | `read_file` universal `action_registry.ts:91-148`；`mapper.ts:193-200`；dedicated `59-79` + `router.ts:42-54`；structurizer `17,184-186` | 未 import/编译/运行 legacy |
| `RA-01-WEB-01..07` | `✅` | `web_search` + `web_fetch` 打开 Temporal / SFN Choice / CWL 1.2 / Airflow Dags / Camunda XOR | 访问日 2026-08-29；CWL pickValue MARK 规范单源 |
| `S03-T007/011/012/013/017/038/053` | `✅` | `read_file` `S03-workflow-engine.md:166-181,217,242` | |
| `D08-T002` | `✅` | `read_file` `D08-legacy-capabilities-migration.md:93` | |
| `T-O-377/379/382/384/387/388` | `✅` | `grep`+`read_file` QNA 表 + Q7/Q8 正文 | 只 CITE |
| pytest 大集合 | `未` 本面全跑 | 按纪律：只跑 index 已列小集合若需要 | 本面结论不依赖 live e2e；index `D-24` source e2e 红灯交面 09。未假装全绿 |
| `WorkflowStepKind.JOIN` 使用 | `✅` | `grep` `src/workflows` 无匹配 | |

**声称 vs 实测修正**：prompt 行号提示与本次 read 一致（未漂移到错误符号）。CONTROL 报错字符串低估 scatter join，以代码分支为准（仍 2 实现）。QNA「5 张选不中」以 HEAD 6 为准。

---

## 12. 收尾 Verdict 与交接 `[核心]`

- **本面裁定**（分析裁定，非 owner 产品裁决）：HEAD Workflow 图代数是 **可复用底座 + 四块净新缝**。不复制 publication tail 时 **不能** 表达 selected-output merge。compat definitions 是 **同 key revision 共存正例**，对 kind 家族 identity 塌缩 **不够**。human_review 是局部类比。总体方向：`♻️重 substrate` 七表/无环/登记守卫/pin；`🆕净新` merge 代数、kind identity、representation 谓词消费。健康维持 index 预核查 `🔴`。
- **交接下游**：缺口台账（§4）→ 规划；净新契约（§6）→ 设计；owner-gate 候选（§10.2：`G-NH-02/09/03`）→ 决策登记；验收格栅（§9）→ 执行计划。面 02 必须消费本面 selected-route / merge 缺口；面 03 必须提供 representation fact 形状；面 09 必须把 `NH-A-01-06` 纳入旧 pinned 证明。
- **冻结前置**：本分析保持 `draft`。要升 `reviewed`/`frozen` 需：review-fleet 对账邻面 §5；owner 未在本文被代裁；`G-NH-02/09` 仍为 MARK；HEAD 若改 `D-05..D-11` 须先修订 index。

---

## 附录 A · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| v0.1 | 2026-08-29 | Grok analysis-fleet | 初稿（measure-first + 三渠道正反例 + 缺口台账 + 净新缝 + owner-gate MARK） |
| v0.2 | 2026-08-29 | Grok fix-fleet | 吸收已核实 review：R3-I10 Temporal experimental WV 限制句改过去时；R3-I11 CWL Expressions optional（非单独 conditionals feature）；R3-I12 BPMN 改 Camunda 实现转述；R2 §5 补未注册 `browserPDF-geminiClean` 暗路由。状态仍 `draft` |
