# new-harvest reference-anchor 评估索引

> **项目**：`myknowledgebase`（MKB）
> **阶段（别名）**：`new-harvest reference-anchor assessment`（`NH-RA`）
> **日期**：`2026-08-29`
> **作者**：`GPT`（fleet / panel：`new-harvest-reference-anchor`；parent independent-verify by Grok）
> **文档性质**：`assessment / index`（阶段评估编排器；measure-first，零决策——只 MARK 不裁决；**不属于 eval 家族**）
> **文档状态**：`active index`
> **流水线位置**：站① · 站② 九份 `assessment-analysis` 已落盘 `draft`（v0.2/v0.3，未 frozen）· 下一步 = 站③ `planning-proposed`
> **关联 owner 意图 SSOT**：[`pre-initial-planning-qna.md`](pre-initial-planning-qna.md) v0.5 `frozen`（`T-O-376..389`）；本轮 owner 指令：以 HEAD、公开网络/websearch、`legacy-family` 对内聚业务簇做正反例核查
> **关联上游收口**：[`initial-planning.md`](initial-planning.md) v0.1 draft；[`thoughts-on-initial-planning-by-GPT.md`](thoughts-on-initial-planning-by-GPT.md) v0.1 reviewed
> **下游消费者**：`docs/eval/new-harvest/planning-proposed.md` · `docs/eval/new-harvest/pre-charter-qna.md` · 后续 design / action-plan

---

## 0. TL;DR / Owner 意图与本阶段范围 `[核心]`

- **一句话**：本阶段以 9 个有界调查面，把 new-harvest 的关键疑问分别送入 HEAD 实测、公开网络 primary-source 核查和 legacy clean 考古，形成正例、反例、substrate-fit、缺口、净新契约与 owner-gate 候选，供 `planning-proposed` 使用。
- **0.1 Owner 提出的方向 / 为什么现在**：initial 已给出产品法和 first-cut DAG，上一轮 state-analysis 进一步发现：两阶段 S05 binding、Workflow one-of binding、真实 representation/runtime、五维语义投影与 retrieval facet 尚缺可执行事实；同时 API/pure clean/g0/tail 又已有可复用交付。若不先做 reference-anchor 核查，proposed-planning 会同时面临“重做已交付”和“低估净新 substrate”两种错误。
- **0.2 范围边界（Non-goals）**：本阶段只调查、测量、对比与 MARK；不修改产品代码，不选择并冻结 PDF/browser/OCR 库，不排 action-plan 执行序，不替 owner 修订 Truth，不接 live 供应商，不新增第五 source kind，不重开 cuts/g0，不启动 `.experiment`。
- **0.3 评估完成汇总**：`9 面已登记 / 站① HEAD 分母预核查 done / 站② 9 份 analysis 已产出（draft，经 review-fleet + parent 独立核验）/ 公开网络已检索但未冻结为执行方案 / 站③ planning-proposed 待写`。制品目录：`docs/eval/new-harvest/reference-anchor/`；审查：`.grok/reviews/new-harvest/`。**本 index 仍不裁决、不冻库选型。**

### 0.4 本 index 对上一轮建议的结构化回应

上一轮建议“保留六个产品/技术簇，把失败法改成横切线程，并将 runtime readiness 单列”。为保证单份 analysis 内聚，本 index 进一步做两处拆分：

1. 原“图与晚绑定”拆成：`01 Workflow 图代数与 kind 家族`、`02 两阶段 S05 binding 与恢复`；前者回答“图能否表达”，后者回答“选中事实如何封闭与重放”。
2. 原“表示 + clean”之间单列 `05 runtime adapter / readiness / security`；`03` 只研究 representation 与 acquire 法，`04` 只研究 clean 合同与策略，避免把产品语义和部署选型混为一谈。

因此站②不是 7 份，而是 **9 份**有界深评。

---

## 1. 评估地图 `[核心]`

> “健康”是站①预核查水位，不是站②最终 verdict：🔴=存在 S1 阻断候选；🟡=已有 substrate 但闭集/证据不完整；🟢=仅允许在 analysis 复核后使用。

| ID | 调查面 | 优先级 | 健康 | 预核查（站①） | 站② 详评文档 | 备注 |
|---|---|---|---|---|---|---|
| `01` | 声明式 Workflow 图代数与 kind 家族迁移 | `P0` | `🔴` | `done` | [`reference-anchor/assessment-analysis-01-workflow-graph-and-kind-family.md`](reference-anchor/assessment-analysis-01-workflow-graph-and-kind-family.md) `draft` | guard、one-of、merge、13 identity、compat revision |
| `02` | 两阶段 S05 binding、evidence seal 与 recovery | `P0` | `🔴` | `done` | [`reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md`](reference-anchor/assessment-analysis-02-s05-two-stage-binding-and-recovery.md) `draft` | truth-to-schema 冲突；policy vs actual binding |
| `03` | 表示、acquire/decode 与有限正向再获取 | `P0` | `🔴` | `done` | [`reference-anchor/assessment-analysis-03-representation-and-reacquisition.md`](reference-anchor/assessment-analysis-03-representation-and-reacquisition.md) `draft` | PDF/web/print/opaque doc、evidence chain |
| `04` | clean capability activation 与 admitted clean 合同 | `P0` | `🟡` | `done` | [`reference-anchor/assessment-analysis-04-clean-capability-and-admitted-clean.md`](reference-anchor/assessment-analysis-04-clean-capability-and-admitted-clean.md) `draft` | 10 strategy / 9 capability / 3 API operation；保留已交付 |
| `05` | PDF/browser/multimodal runtime 供给、readiness 与安全 | `P0` | `🔴` | `done` | [`reference-anchor/assessment-analysis-05-runtime-adapters-readiness-and-security.md`](reference-anchor/assessment-analysis-05-runtime-adapters-readiness-and-security.md) `draft` | adapter/资源/隔离/依赖/模型运输；不定产品路由 |
| `06` | 公共上传、S13 bytes identity 与 object lifecycle | `P1` | `🔴` | `done` | [`reference-anchor/assessment-analysis-06-public-upload-and-object-lifecycle.md`](reference-anchor/assessment-analysis-06-public-upload-and-object-lifecycle.md) `draft` | upload≠Item、catalog orphan、GC/read boundary |
| `07` | 五维语义双账本、S06 projection 与 retrieval facets | `P0` | `🔴` | `done` | [`reference-anchor/assessment-analysis-07-semantic-ledger-and-retrieval-facets.md`](reference-anchor/assessment-analysis-07-semantic-ledger-and-retrieval-facets.md) `draft` | non-API authority、context overlay、channel 名冲突 |
| `08` | publication 贯通、七意图与 Intake lifecycle | `P1` | `🟡` | `done` | [`reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md`](reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md) `draft` | 复用 tail/g0/API scatter；核验 intent applicability |
| `09` | fail-loud、replay/竞态、兼容迁移与闭集证明 | `P0` | `🔴` | `done` | [`reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md`](reference-anchor/assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md) `draft` | 横切面；汇总前八面的防假绿与恢复不变量 |

### 1.1 Owner 方向 ↔ 调查面映射

| Owner 方向 / frozen truth | 命中调查面 | 覆盖说明 |
|---|---|---|
| 四通道真实 Process→可检索向量，禁止诚实未部署（`T-O-376/381`） | `03/04/05/07/08/09` | 从真实表示、clean、runtime、语义、publication 到 mega proof 分账核查 |
| 四 kind、三轴、禁 caller `workflow_key`（`T-O-377/379`） | `01/03/04` | kind 选图；acquire/strategy 图内取值；策略不回流 branch taxonomy |
| 表示已知后晚绑定、绑定后 fail-loud（`T-O-382/383`） | `01/02/03/09` | 路由事实、seal 时刻、恢复法与失败证明分别核查 |
| 同 revision 已声明边、kind 家族、有限再获取（`T-O-384/387/388`） | `01/02/03` | 图表达力、actual binding、representation history 三面闭环 |
| upload=S13 handle，不创造 Item（`T-O-385`） | `06/09` | bytes-first 与 replay/GC/竞态共同核查 |
| 一份 admitted clean、promptA 仅 LLM 策略（`T-O-386`） | `04/05/08` | clean 身份、推理运输、尾链消费分开核查 |
| FilterMeta/ContextMeta 与 g0 分账（`T-O-389`） | `07/08/09` | acceptance authority、S06/retrieval 消费与完整性证明 |
| 当前代码 + websearch + legacy-family 正反例 | `01..09` | 每面强制使用统一三渠道协议；无适用 legacy 锚时明确标 `🆕`，不得硬凑 |
| 为 proposed-planning 提供准确内外部认知 | `01..09` | 各 analysis 输出稳定缺口 ID、契约草案、owner-gate 与验收格栅，再由站③汇总 |

### 1.2 调查面之间的边界

| 交界 | 权威归属 | 另一面只消费什么 |
|---|---|---|
| graph route vs binding seal | `01` 拥有图结构；`02` 拥有 binding 生命周期 | `01` 消费 seal contract；`02` 消费 selected route identity |
| representation vs clean | `03` 拥有 acquire/decode facts；`04` 拥有 admitted clean | `04` 只消费 typed representation；不得重新 fetch/decode |
| clean strategy vs runtime | `04` 拥有策略/证据/空成功法；`05` 拥有 adapter/模型/依赖/readiness | `04` 不选模型/二进制；`05` 不改 strategy taxonomy |
| upload vs local-object ingest | `06` 只到 handle/catalog；`03/04/08` 拥有后续 ingest | upload success 不得制造 Source/Item/Revision |
| semantics vs publication | `07` 拥有五维 authority/projection/facet；`08` 拥有 serving/pointer/lifecycle | `08` 不从 clean/g0/模型猜五维 |
| 各功能 vs assurance | `01..08` 拥有功能事实；`09` 拥有横切 replay/race/recovery/proof | `09` 不重写功能设计，只校验不变量和 fake-green |

---

## 2. 站① measure-first 预核查 `[核心]`

### 2.1 证据基线、渠道协议与可复现命令

#### 证据置信顺序

1. **HEAD 实测**：当前代码、DDL、测试输出；每条关键结论必须 `path:line` + 可复现命令。
2. **仓内 accepted/frozen 文档**：解释意图与旧 Truth；若与 HEAD 或另一冻结文档冲突，显式登记，不自动覆盖。
3. **legacy-family ReferenceAnchor**：只能证明历史能力、可借语义或反例；不得形成 runtime/schema/API/data 依赖。
4. **公开网络/websearch**：只证明外部机制、约束、失败模式和行业可选形态；不得证明 MKB 当前状态。技术核查优先官方文档、标准、规范、原始研究论文、官方安全公告/漏洞库；博客/聚合文只能提供搜索线索，不能单独支撑关键结论。

#### 正例 / 反例记账协议

每份 analysis 使用稳定锚 ID：

```text
RA-FF-CHANNEL-NN
```

每条锚必须记录：`结论原子句 / 来源与版本或访问日 / 正例或反例 / 置信 / substrate-fit verdict / 命中的疑问或缺口 ID`。

- **正例**：能证明某一不变量或机制在来源中真实成立；“能跑”但不满足本仓边界，只能标 `🔶部分借`。
- **反例**：失败模式、被明确禁止的机制、假成功或与本仓路线冲突的实现；反例不是为了贬低来源，而是钉住不得复发的条件。
- **🆕 净新**：三渠道均找不到 substrate-fit 先例时诚实登记；不得为满足数量硬凑外部类比。
- **最低证据包**：每面至少有 HEAD 正例/反例各 1 组；legacy 有适用证据则至少形成 1 条“借什么/不借什么”；WEB 对存在竞争路线的 S1 机制尽量使用 2 个相互独立的 primary sources，并至少核查一条限制/失败条件。若只有单一规范权威，允许单源，但必须 MARK “规范单源”并避免外推。数量用于防单源偏见，不是刷引用目标。

#### 可复现命令

```bash
# 共享结构分母
uv run python - <<'PY'
from intake import _REGISTERED_CLEAN
from intake.api.registry import REGISTERED_PROVIDER_OPERATIONS
from src.contracts.intake.strategies import CLEAN_STRATEGY_DEFINITIONS
from src.services.registry import DEFAULT_SEMANTICS, DEFAULT_SOURCE_KINDS
from src.workflows.builtin_scatter import (
    BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW,
    BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW,
)
from src.workflows.lsrag_definition import (
    BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW,
    BUILTIN_SOURCE_PROFILE_WORKFLOWS,
    SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS,
)

single = (BUILTIN_SINGLE_INTAKE_LSRAG_WORKFLOW, *BUILTIN_SOURCE_PROFILE_WORKFLOWS)
public = set(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS.values())
print("source_kinds", len(DEFAULT_SOURCE_KINDS))
print("clean_strategies", len(CLEAN_STRATEGY_DEFINITIONS))
print("clean_process_capabilities", len(_REGISTERED_CLEAN))
print("provider_operations", len(REGISTERED_PROVIDER_OPERATIONS))
print("single_root_identities", len(single))
print("public_selector_keys", len(SINGLE_SOURCE_PROFILE_WORKFLOW_KEYS))
print("unselectable_single_identities", sum(x.workflow_key not in public for x in single))
print("scatter_identities", len((BUILTIN_REGISTERED_API_SCATTER_ROOT_WORKFLOW, BUILTIN_REGISTERED_API_SCATTER_CHILD_WORKFLOW)))
print("semantic_definitions", len(DEFAULT_SEMANTICS))
PY

# Workflow / binding / route fact 分母
nl -ba src/contracts/workflow/models.py | sed -n '245,278p;373,443p;476,525p'
nl -ba src/runtime/workflow/runtime_materialize.py | sed -n '49,168p;505,514p'
rg -n "s05_binding_digest|domain_binding_digest" \
  src/persistence/migrations/001_initial.sql src/runtime/task src/runtime/workflow \
  src/runtime/intake src/services

# representation / runtime / dependency
nl -ba src/runtime/intake/acquisition_ingest.py | sed -n '403,676p'
nl -ba src/runtime/intake/types.py | sed -n '144,220p'
nl -ba api/app.py | sed -n '319,346p'
nl -ba pyproject.toml | sed -n '5,28p'

# public API / upload / semantic / retrieval
rg -n '^\s*@router\.' api/public/routes.py
rg -n '^\s*@router\..*(object|upload)|multipart' api/public/routes.py
nl -ba src/contracts/storage/models.py | sed -n '16,29p'
nl -ba src/runtime/intake/acceptance_snapshot.py | sed -n '576,641p'
nl -ba src/runtime/intake/generation_construct.py | sed -n '329,343p;1092,1229p'
nl -ba src/services/retrieval/models.py | sed -n '14,34p'

# legacy clean 分叉、语义与失败反例
rg -n "this.register|action_branch|plainTextAvailable|empty_response|return null|payload_filter_meta" \
  context/legacy-family/smind-skill-clean-universal \
  context/legacy-family/smind-skill-clean-dedicated-apis \
  context/legacy-family/smind-clean-dispatcher

# 已知相关测试水位
uv run pytest \
  tests/unit/test_intake_provider_registry.py \
  tests/unit/test_intake_clean_dispatch.py \
  tests/intake/test_web_clean.py \
  tests/intake/test_pdf_clean.py \
  tests/intake/test_doc_clean.py
uv run pytest \
  tests/e2e/test_registered_api_scatter.py::test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics
uv run pytest \
  tests/e2e/test_source_capability_paths.py::test_local_static_browser_and_pdf_sources_produce_distinct_frozen_acquisition_evidence
```

> 公开网络核查不在 shell 命令中伪造。站②必须在各 analysis §1.2/§3 记录真实搜索词、打开的 primary-source URL、版本/发布日期/访问日及支持的原子结论。

### 2.2 ★ 冻结分母（FROZEN denominators · HEAD `1221aa1`）

> 下表冻结的是 **本轮共同基线**，不是目标值。站②可以补本面专属分母，但不得另估或悄悄改写这些共享值；HEAD 变化须先修订 index 版本。

| ID | 分母 | HEAD 实测值 | 证据锚（`path:line` / 命令） | 喂给调查面 |
|---|---|---|---|---|
| `D-01` | source kind | `4` | `src/services/registry.py:171-208`; §2.1 script | `01/03/04/08` |
| `D-02` | CleanStrategyKey | `10` | `src/contracts/intake/strategies.py:15-151`; script | `03/04/05/09` |
| `D-03` | clean Process capability | `9`（8 single clean + 1 API map） | `intake/__init__.py:20-30`; script | `01/04/05` |
| `D-04` | registered API operation | `3` | `intake/api/registry.py:73-104`; script | `04/07/08/09` |
| `D-05` | single-root Workflow identity | `13` | `src/workflows/lsrag_definition.py:614-714,943-1069`; script | `01/09` |
| `D-06` | public selector / unselectable single identity | `7 / 6` | `lsrag_definition.py:929-940,1003-1069`; script | `01/04/09` |
| `D-07` | scatter Workflow identity | `2`（root + child） | `src/workflows/builtin_scatter.py:352-380,571-599`; script | `01/04/08/09` |
| `D-08` | guard predicate type / operator | `5 / eq-only` | `src/contracts/workflow/models.py:245-278` | `01/03` |
| `D-09` | representation-aware guard | `0` | `models.py:249-255`; `runtime_materialize.py:101-117` | `01/03` |
| `D-10` | 单 target input 可声明 source binding 数 | `1` | `src/contracts/workflow/models.py:482-525` | `01/02` |
| `D-11` | runtime registered CONTROL 实现 | `2`（human review / scatter join） | `src/runtime/workflow/runtime_materialize.py:505-514` | `01/09` |
| `D-12` | Execution actual S05 digest 字段 | `1`，`NOT NULL`，创建时由 domain digest 填入 | `001_initial.sql:245-246`; `task_create.py:167-181,337-368` | `02/09` |
| `D-13` | acquisition/decode evidence history | `单值 1+1`；声明式 reacquire edge `0` | `acquisition_ingest.py:597-676`; `clean_preflight.py:622-686`; graph routes | `02/03/09` |
| `D-14` | public `/v1` route / object-upload route | `28 / 0` | `api/public/routes.py:56-469`; §2.1 `rg` | `06/08` |
| `D-15` | S13 purpose / caller-upload purpose | `8 / 0` | `src/contracts/storage/models.py:16-29` | `06/09` |
| `D-16` | canonical intake SemanticDefinition | `10` | `src/services/registry.py:229-239`; script | `07/08` |
| `D-17` | FilterMeta+tags semantic key | `6`（5 维 + context_tags） | `src/contracts/intake/semantics.py:12-63`; `registry.py:234-239` | `07/08/09` |
| `D-18` | 非 API 通道实际五维写入 | `0`；当前 fallback 为 `source_kind` blob | `src/runtime/intake/acceptance_snapshot.py:589-615` | `07/08` |
| `D-19` | public retrieval filter key / FilterMeta facet key | `3 / 0` | `src/services/retrieval/models.py:14-34`; `retrieval_request.py:324-361` | `07/08/09` |
| `D-20` | 直接生产依赖 / PDF-browser-OCR 专用依赖 | `7 / 0` | `pyproject.toml:13-28` | `03/05` |
| `D-21` | 默认组合根 browser_fetcher / clean_llm 注入 | `0 / 0` | `api/app.py:332-345`; `src/runtime/intake/core.py:39-75` | `03/04/05` |
| `D-22` | legacy universal / dedicated 分叉 | `6 / 3` | universal `action_registry.ts:91-149`; dedicated `action_registry.ts:59-79` | `03/04/05/07` |
| `D-23` | 选定 clean/provider unit+intake 水位 | `33 passed / 0 failed` | 2026-08-29 复跑；§2.1 命令 | `04/05/09` |
| `D-24` | 三 provider e2e / source capability e2e | `1 passed / 1 failed` | API 20.72s；source static 停 `running` 22.08s | `04/08/09` |

### 2.3 贯穿主题（跨子系统根因）

- **冻结 ≠ 已实现**：QNA 的产品法是目标约束；每份 analysis 必须分开列“方向正确”“代码已有”“代码缺失”“旧 Truth 冲突”。
- **identity 分账**：source kind、acquire path、representation、strategy key、process key、prompt/adapter、actual binding、Item/Revision、vector publication 都不是同一身份。
- **决策事实必须 durable**：guard 命中的 representation、actual path、selected clean、digest seal 与 retry/recovery 不能只活在 handler local state。
- **通道是验收格，不是天然施工包**：跨 kind graph、upload、semantics、publication、assurance 的公共机制只核查一次；在 acceptance matrix 中再按通道展开。
- **借鉴必须过 substrate-fit**：legacy 或外部产品的 branch、plugin、云 Worker、R2、自由表达式、动态 loader，不因“成熟”就适合本仓。
- **正反例成对**：只找成功实现会掩盖失败边界；只找反例会错过已交付 substrate。每个 S1 缺口必须至少有一条支持机制和一条限制/失败证据。
- **测试是事实渠道，不是末期装饰**：unit 证明纯函数，integration 证明 binding，default-root e2e 证明接线，retrieval/facet 证明产品终态；层级不可互换。

### 2.4 对参考 / 既有叙事的失真校正

| 叙事/参考声称 | HEAD 实测 | 失真类型 | 证据 |
|---|---|---|---|
| “7 公开 + 5 选不中 / 12 张图” | 7 public selector + 6 unselectable；single identity 共 13 | `低估` | `lsrag_definition.py:929-940,1003-1069`; `D-05/06` |
| human_review 已足以证明晚绑定图可行 | guard route 是正例，但没有 selected-output merge；target input 仍只能绑一个 source | `类比过度` | `runtime_materialize.py:49-117,505-514`; `models.py:482-525` |
| QNA 已完成“无实际冲突”审查 | 两阶段 actual S05 与 S05/D04/glossary/DDL 创建时法仍冲突 | `高估` | QNA `760-769`; `S05-intake-cleaning.md:225-230`; DDL `245-246` |
| MKB clean 主要是空合同 | 10 strategy、9 capability、三 provider map 与 pure handlers 已存在，33 个相关 case 全绿 | `低估` | `D-02/03/04/23` |
| legacy clean 是可迁移生产实现 | 可借字段/分叉；runtime 含 action_branch、CF/R2/SMCP、任意 header/cookie、empty success、silent skip | `错置` | legacy anchors；`D08-T003/T004` |
| 有 ObjectStorePort/GC 即有上传 | public upload route/purpose/catalog service 均为 0 | `高估` | `D-14/15` |
| 五维已登记即可称语义可检索 | API 写入是正例；非 API 为 stub，S06 不读 Revision semantics，公开 facet 为 0 | `高估` | `D-16..19` |
| API 三 operation 仍需从零做 live | map→semantics→child publication 已有 e2e；主要待 retrieval/facet 与新 binding 回归 | `低估` | `tests/e2e/test_registered_api_scatter.py:209-321` |
| PDF/browser/OCR 库是本战役 OOS | 具体选择在 initial 未冻结，但真实 runtime 是 `T-O-381` 完成所必需 | `范围错置` | initial `133-142`; QNA `85,805-818` |

### 2.5 须净新的 gate（assessment gate registry）

> 下列是评估制品质量 gate，不是 owner 产品裁决。

| gate-ID | 用途 | 为什么净新 |
|---|---|---|
| `G-NH-RA-01` | HEAD denominator lock | 防 9 份 analysis 各自估 graph/strategy/filter 分母 |
| `G-NH-RA-02` | primary-source provenance | 本轮首次系统使用公开 websearch；必须阻止 SEO/二手摘要成为架构权威 |
| `G-NH-RA-03` | positive/negative pair | 防只收集“行业都这么做”的确认偏误，或只列 legacy 坑而漏掉已交付资产 |
| `G-NH-RA-04` | substrate-fit verdict required | 外部/legacy 每条锚必须明确直借、部分借、反例或净新 |
| `G-NH-RA-05` | cross-face invariant reconciliation | 同一事实只允许一个面拥有；冲突必须在双方 §5 显式对账 |
| `G-NH-RA-06` | anti-fake-green acceptance draft | 每份 analysis 必须区分 unit/integration/default-root e2e/retrieval，不接受 monkeypatch 冒充 live |
| `G-NH-RA-07` | owner-gate zero-decision check | analysis 只能 MARK 候选；不得把外部参考偏好偷偷冻成方案 |

---

## 3. 逐调查面登记 `[核心]`

### 3.01 声明式 Workflow 图代数与 kind 家族迁移

- **优先级 / 健康**：`P0 / 🔴`
- **调查范围**：Workflow steps/routes/guards/bindings/control/join 的表达力；四 kind graph identity；13 single + 2 scatter identity；active/compat revision；不含 actual S05 digest 字段生命周期（面 02）。
- **为什么需要评估**：`T-O-384/387/388` 要求同 revision 多 acquire/decode/clean 边，而 HEAD graph factory 每图固定三步、route fact 不见 representation、binding 无 one-of source。必须先判断是“现 substrate 可组合”还是“需净新 graph algebra”。
- **预核查初判（站①，待站②深挖）**：acyclic/static guard/compat revision 是正例；one-of merge、representation predicate、kind migration 是 S1 候选；human_review 只提供局部类比。
- **HEAD 正例候选**：`WorkflowDefinition` 静态无环/terminal coverage（`models.py:326-474`）；admission registered guard；compatibility definitions（`lsrag_definition.py:1073-1080`）。
- **HEAD / legacy 反例候选**：single-input binding（`models.py:482-525`）；7+6 profile 家族；legacy dispatcher 把 `action_branch` 原样下发（`smind-clean-dispatcher/services/mapper.ts:193-200`）。
- **公开网络核查包**：搜索“official declarative DAG conditional branch selected output merge immutable workflow version deterministic replay”；比较静态 graph/choice state/one-of result 的规范约束与失败模式，不预选引擎。
- **必须回答**：不复制整条 publication tail 时，当前七表能否表达 selected-output merge？kind graph 新 identity 如何与旧 pinned revision 共存？
- **详评文档**：`assessment-analysis-01-workflow-graph-and-kind-family.md`

### 3.02 两阶段 S05 binding、evidence seal 与 recovery

- **优先级 / 健康**：`P0 / 🔴`
- **调查范围**：policy/envelope binding、actual acquisition/clean/preflight binding、seal CAS、ProcessCommand、CandidateSet/Snapshot/Gate/Proof 传播、retry/recovery/restart；不拥有 graph shape（面 01）。
- **为什么需要评估**：QNA 的 late-bind 时序与 S05/D04/glossary/DDL 的创建时 actual binding 存在真实冲突；HEAD 又以 domain digest 冒充 S05 digest。
- **预核查初判**：exact revision/config/domain binding 与 Task fingerprint replay 是可复用 substrate；actual S05 两阶段 schema、状态和 transaction 是净新候选。
- **HEAD 正例候选**：Task create 双检（`task_create.py:67-104`）；Workflow/config exact freeze；Gate target 携带 binding（`runtime_materialize.py:546-590`）。
- **HEAD / legacy 反例候选**：`s05_binding_digest=domain_binding_digest`（`task_create.py:167-181`）；ProcessCommand 只用 domain binding（`runtime_core.py:888-915`）；legacy branch/action 无不可变 actual binding。
- **公开网络核查包**：搜索“official durable workflow deterministic replay activity choice recorded in history version marker immutable execution binding CAS state transition”；核查 choice-before/after crash、resume 与 version change 的法。
- **必须回答**：未封闭 actual binding 用什么合法状态表达？seal 与 route outcome 是否同事务？封闭前/后 retry、Task causal restart 分别重放什么？
- **详评文档**：`assessment-analysis-02-s05-two-stage-binding-and-recovery.md`

### 3.03 表示、acquire/decode 与有限正向再获取

- **优先级 / 健康**：`P0 / 🔴`
- **调查范围**：HTTP static/browser/print PDF、local/inline bytes、MIME sniff、PDF text-layer observation、image/opaque document、acquisition/decode evidence chain、有限正向 reacquire；不评 clean 输出质量（面 04）或具体 runtime 选型（面 05）。
- **为什么需要评估**：guard 必须消费诚实 representation；HEAD 只保存单份 evidence，从不产 `print_pdf`，PDF 无层在 decode 失败，docx 被强制 UTF-8。
- **预核查初判**：verified MIME、URL redaction、image evidence 空文本观察是正例；PDF literal scanner、browser profile 常量、opaque binary、single evidence 是反例/缺口。
- **HEAD 正例候选**：media sniff/critical mismatch（`types.py:174-220`）；HTTP evidence/redacted identity；image decode 不制造文本（`acquisition_ingest.py:620-632`）。
- **HEAD / legacy 反例候选**：literal PDF（`types.py:144-171`）；`rendered|transferred` 无 print（`acquisition_ingest.py:527-538`）；legacy 任意 headers、Cloudflare content/PDF 直调。
- **公开网络核查包**：搜索“official PDF text extraction encrypted/scanned detection security sandbox MIME sniff content type mismatch browser print to PDF API evidence”；对 PDF parser、browser protocol、document MIME 的能力与限制分别取证。
- **必须回答**：representation fact 最小闭集是什么？多 acquire/decode history 如何 digest？静态空壳、真 PDF、扫描 PDF、opaque doc 各在何时停止/前进？
- **详评文档**：`assessment-analysis-03-representation-and-reacquisition.md`

### 3.04 clean capability activation 与 admitted clean 合同

- **优先级 / 健康**：`P0 / 🟡`
- **调查范围**：10 strategy、9 process capability、三 API operation、strategy↔process↔representation compatibility、promptA 义务、非空 admitted clean、provider parser/双 digest；不拥有 adapter 部署（面 05）或 S06 结构化（面 08）。
- **为什么需要评估**：当前 pure clean/API map 已有大量交付，但 route/default composition 未把闭集接活；若不精确核查，会重写已交付或漏掉 strategy identity 与 process key 非一一映射。
- **预核查初判**：strict strategy registry、structural HTML sanitizer、PDF/doc typed fail、API semantic mapper 是正例；三 promptA identity、unselectable graphs、legacy empty success/per-member skip 是反例。
- **HEAD 正例候选**：`strategies.py:15-164`; `intake/__init__.py:20-132`; API `MappedProviderMember` 非空 clean（`semantics.py:37-52`）；33 passed。
- **HEAD / legacy 反例候选**：strategy 默认 `promptA.default` vs snapshot/profile `promptA.clean` / documentation default；legacy web/doc `plainTextAvailable=true` 无非空检查；dedicated parser catch 后 skip。
- **公开网络核查包**：搜索“official document cleaning pipeline deterministic vs LLM provenance prompt version content hash OCR empty output contract provider mapping schema validation”；外部锚只用于机制/失败法，不拿供应商宣传代替真实测试。
- **必须回答**：合法 compatibility matrix 如何生成？每个 strategy 的 admitted clean/evidence 最小合同是什么？API exhausted-zero 与 empty member 如何分账？
- **详评文档**：`assessment-analysis-04-clean-capability-and-admitted-clean.md`

### 3.05 PDF/browser/multimodal runtime 供给、readiness 与安全

- **优先级 / 健康**：`P0 / 🔴`
- **调查范围**：PDF parser process isolation、browser binary/driver、print PDF、multimodal request/adapter/model、资源池/预算/readiness、依赖与许可证、安全边界；不改变 clean strategy 或路由 taxonomy。
- **为什么需要评估**：默认组合根 browser/clean_llm 均未注入；S11 Generate/Claude clean 是 text-only；仓库无专用依赖。`T-P-NH-6`“复用现有推理面即可”尚无事实支撑。
- **预核查初判**：依赖注入、InferenceFacade、concurrency gate、egress fence 是可复用 substrate；binary multimodal transport、browser/PDF supply/readiness 是净新或重 substrate。
- **HEAD 正例候选**：`IntakeCoreMixin` 分离 browser/clean ports（`core.py:39-75`）；Inference binding/facade；HTTP egress limits。
- **HEAD / legacy 反例候选**：app 未注入（`api/app.py:332-345`）；GenerateRequest 仅 `input_text`（`inference/models.py:96-118`）；CLI 拒 binary（`claude_cli.py:497-519`）；legacy 硬绑 Cloudflare/Gemini aliases。
- **公开网络核查包**：对候选 parser/browser/multimodal runtime 分别搜索官方安装、支持矩阵、进程隔离、sandbox、资源限制、许可证、安全公告和真实二进制输入协议；不得只看 feature list。
- **必须回答**：复用现有 pool 是否只是不增调度池，还是也不扩请求协议？readiness 如何证明 binary 能力真实在场？恶意 PDF/browser 逃逸的隔离线在哪里？
- **详评文档**：`assessment-analysis-05-runtime-adapters-readiness-and-security.md`

### 3.06 公共上传、S13 bytes identity 与 object lifecycle

- **优先级 / 健康**：`P1 / 🔴`
- **调查范围**：authenticated upload contract、stream/size/digest、CAS replay、catalog-without-business-ref、orphan grace、concurrent upload、read boundary、随后 local_object ingest；不创造/修改 Intake identity。
- **为什么需要评估**：S13 CAS/GC 内核已在，但 public route/purpose 为 0；“直接暴露 promote”无法自动解决 catalog、GC 与竞态。
- **预核查初判**：team-scoped deterministic handle、verify-on-read、catalog unique 与 GC delete fence 是正例；public surface、caller purpose、orphan hold/ingest race 是缺口。
- **HEAD 正例候选**：`LocalObjectStore.promote/read_verified`（`local_store.py:71-123`）；stored-object unique（DDL `837-873,1800-1801`）；GC recheck（`object_gc.py:133-245`）。
- **HEAD / legacy 反例候选**：public route 0；purpose 0；legacy admin presign/confirm 可借“两步”但 R2/file-row identity 不可借。
- **公开网络核查包**：搜索官方/标准“resumable upload checksum idempotency content-addressed storage orphan cleanup upload security filename MIME malware race”；同时查安全规范的反例与限制。
- **必须回答**：upload-only 还是 upload+read？catalog orphan 在何事务创建？grace 内 upload→ingest 与 GC 如何防竞态？同 digest/size/media 差异如何返回？
- **详评文档**：`assessment-analysis-06-public-upload-and-object-lifecycle.md`

### 3.07 五维语义双账本、S06 projection 与 retrieval facets

- **优先级 / 健康**：`P0 / 🔴`
- **调查范围**：非 API ingest 五维权威、ContextMeta tags、Revision semantics、g0 分账、S06 system-owned context overlay、vector/retrieval facet、metadata update；不重开 cuts/kernel。
- **为什么需要评估**：10 semantic definitions 已登记、API 六元组已写，但非 API 为 stub；S06 input 只有 clean/markdown；retrieval 无 FilterMeta facets，且 `channel` 已表示 original/summary。
- **预核查初判**：API strict semantics、Revision semantic table、system g0 是正例；caller contract 0、model context 保留、facet 0 是 S1 候选。
- **HEAD 正例候选**：`FilterMeta/ContextMeta/SemanticTuple`（`semantics.py:12-63`）；API e2e 写六键；system-owned g0（`generation_assemble.py:17-62`）。
- **HEAD / legacy 反例候选**：fallback `{"source_kind":...}`（`acceptance_snapshot.py:589-615`）；S06 不读 revision semantics；legacy metadata 可借分账，但不得把 member JSON/R2 当权威表。
- **公开网络核查包**：搜索官方“vector search metadata filtering faceted search payload index filter schema reserved field name system metadata overlay provenance”；比较 query-time join、denormalized payload、facet index 的约束，不选产品。
- **必须回答**：非 API 五维从 caller、闭集派生还是二者合并？`unknown` 是否允许？business `channel` 公共字段如何与 vector channel 分名？S06 怎样覆盖模型 context 而不污染 g0？
- **详评文档**：`assessment-analysis-07-semantic-ledger-and-retrieval-facets.md`

### 3.08 publication 贯通、七意图与 Intake lifecycle

- **优先级 / 健康**：`P1 / 🟡`
- **调查范围**：admitted clean→structurize/construct/vectorize/publication/retrieval；seven intent applicability；rebuild/metadata/lifecycle 是否重 clean；single/scatter serving pointer；不重写生成算法或拥有语义来源。
- **为什么需要评估**：尾链/g0/API scatter 已有实绩，不应重做；但 source e2e 红、API 未检索终验、七意图尚无四通道 applicability matrix。
- **预核查初判**：single graph tail、g0、publication proof、API child `publication_ready`、lifecycle CAS 是正例；“Task succeeded=可检索”、四通道×七意图笛卡尔积、legacy key success 是反例。
- **HEAD 正例候选**：`lsrag_definition.py:161-218,425-448`; `generation_assemble.py:17-62`; API e2e `209-321`; lifecycle tests。
- **HEAD / legacy 反例候选**：source capability e2e static 停 running；测试未 retrieval query；legacy finalizer 以 R2 key/output payload 推成功。
- **公开网络核查包**：搜索官方“atomic index publication alias pointer compare-and-swap soft delete reactivate rebuild immutable revision retrieval consistency”；核查 serving cutover 与 stale vector exclusion。
- **必须回答**：七意图对 source kind 的合法 applicability 是什么？每格产品终态是什么？“可检索”必须包含哪些 proof/query/facet？metadata/rebuild 如何复用 exact clean？
- **详评文档**：`assessment-analysis-08-publication-and-intake-lifecycle.md`

### 3.09 fail-loud、replay/竞态、兼容迁移与闭集证明

- **优先级 / 健康**：`P0 / 🔴`
- **调查范围**：Task/intake/upload/binding replay、ConflictError/CAS、crash windows、retry/recovery、old Workflow compatibility、default-root e2e、retrieval/facet mega matrix；横切 01–08，不重新设计其功能。
- **为什么需要评估**：`T-O-383` 是所有路径成功定义；initial 将主要证明推到 NH5，当前又有 monkeypatch、Turso harness 和 source timeout 红灯。
- **预核查初判**：Task fingerprint、acyclic workflow、API fan-in recovery、compat definitions 是正例；domain digest 冒充 actual、legacy silent skip/empty success、sqlite3-on-Turso、monkeypatch browser 是反例。
- **HEAD 正例候选**：`task_create.py:67-104`; registered API zero/fan-in/gate/child failure tests（`test_registered_api_scatter.py:299-499`）；compat workflows。
- **HEAD / legacy 反例候选**：`test_source_capability_paths.py:99-101` monkeypatch；`README.md:606-615` known failures；legacy per-member catch/empty success。
- **公开网络核查包**：搜索官方/原始研究“idempotency key replay conflict CAS crash consistency exactly-once illusion at-least-once workflow version compatibility fault injection property testing”；外部例子必须映射到本仓具体 crash window。
- **必须回答**：每面最少哪组 failure/replay/race tests 才能冻结？old pinned + new kind graph 如何共同验证？哪些测试允许 fixture，哪些禁止 monkeypatch？
- **详评文档**：`assessment-analysis-09-assurance-replay-concurrency-and-compatibility.md`

---

## 4. Owner-gate 候选汇总 `[核心]`

> 全部只是 MARK。站②可增补/拆分；最终交 `pre-charter-qna.md`，本 index 不给倾向。

| gate-ID | 决策点 | 影响范围 | 候选选项（不裁决） | 来源面 | 落点 |
|---|---|---|---|---|---|
| `G-NH-01` | S05 两阶段 binding 的 schema/命名 | Execution/Process/Snapshot/Gate/recovery | `保留 policy+新增 actual / nullable actual+sealed state / 其他经证据支持方案` | `02/09` | `pre-charter-qna.md` |
| `G-NH-02` | selected-output merge 如何进入 Workflow | graph schema/runtime/DDL/migration | `one-of binding / registered merge-control / graph duplication（需评估代价）` | `01/02` | `pre-charter-qna.md` |
| `G-NH-03` | representation route fact 的 durable authority | acquire/decode/guard/recovery | `Process output evidence / 正式 representation fact row / 其他 typed authority` | `01/03` | `pre-charter-qna.md` |
| `G-NH-04` | PDF/browser/multimodal runtime 边界 | S11/pools/dependencies/readiness/security | `扩既有 inference request/adapter / 独立本地 adapter但复用pool / 独立 capability supply` | `03/04/05` | `pre-charter-qna.md` |
| `G-NH-05` | 非 API 五维权威来源与 unknown 法 | public ingest/S04/S06/retrieval | `caller required / kind-closed derivation / caller+derivation merge`；另裁 `unknown` | `07/08` | `pre-charter-qna.md` |
| `G-NH-06` | FilterMeta channel 的公共查询命名 | API contract/retrieval/filter compatibility | `semantic_channel / source_channel / 重命名 vector channel / 其他无歧义方案` | `07/08/09` | `pre-charter-qna.md` |
| `G-NH-07` | public object surface | upload/security/GC/API | `upload-only / upload+authenticated read / 仅业务 artifact read` | `06` | `pre-charter-qna.md` |
| `G-NH-08` | exhausted-zero registered API 终态 | scatter/Task/result/vector/metrics | `typed no-op success / distinct no-change terminal / explicit empty failure` | `04/08/09` | `pre-charter-qna.md` |
| `G-NH-09` | Workflow substrate 是否留在 new-harvest | campaign scope/DAG/AP | `NH 内前置 AP / 独立 engine campaign / 在不破产品法前提下采用现 substrate 方案` | `01/02` | `pre-charter-qna.md` |
| `G-NH-10` | 外部依赖与隔离接受线 | package/deploy/license/security | `in-process / isolated subprocess / sidecar-local`（逐能力裁） | `05` | `pre-charter-qna.md` |
| `G-NH-11` | actual seal 与 selected-route Outcome 是否必须同事务 | Execution/Process/UoW/crash window | `必须同 UoW / 允许先 Outcome 再独立 seal CAS / 其他经证据支持的线性化点` | `02` | `pre-charter-qna.md` |
| `G-NH-12` | Task causal restart 对已封闭 actual 的继承 | restart/generation/rebind | `新 generation 清空 actual / 复制封闭 actual 禁止再选 / 按 intent 分` | `02` | `pre-charter-qna.md` |
| `G-NH-13` | 空壳 / 主文缺失是否进入 representation 闭集 | acquire/decode/guard | `typed fact 可供 eq guard / 仅 clean 质量信号 / 其他经证据支持方案` | `03` | `pre-charter-qna.md` |
| `G-NH-15` | print-to-PDF 与 page-render 是否同一 browser 供给 | runtime supply | `同一本地 browser 不同 CDP 方法 / 分供给 / 其他经证据支持的本地形态` | `05` | `pre-charter-qna.md` |
| `G-NH-16` | 上传成功是否必须写 catalog+live ref/hold | S13 catalog/GC | `catalog+pending/hold / 只 promote 靠 grace / catalog 无 ref` | `06` | `pre-charter-qna.md` |
| `G-NH-17` | 七意图非法格是否要专用 fail-loud 码/表 | Task intent × kind | `仅现有 schema 422/409 / 增补稳定错误码与测试矩阵 / 其他经证据支持方案` | `08` | `pre-charter-qna.md` |
| `G-NH-18` | 测试分层是否写入 charter | completeness 义务 | `写入 charter 四层不可互换 / 仅写入 planning / 其他经证据支持的分层` | `09` | `pre-charter-qna.md` |
| `G-NH-19` | rebuild / 有变更 metadata 是否禁止再执行 clean Process | lifecycle/exact-clean | `跳过 decode+clean 只 replay frozen digest / 允许 byte-equal no-op / 其他经证据支持方案` | `08` | `pre-charter-qna.md` |

> `G-NH-14` **故意空号**：面 04 的 promptA 三套 catalog 默认 id 对齐已由 QNA §10.2 标为**执行延期**，不占 owner-gate。站② analysis 不得再占用 `G-NH-11` 作他义。

---

## 5. 阶段工作目标雏形（非冻结）`[核心]`

- **一句话目标**：把 new-harvest 的 9 个承重面从“产品法 + 初判”推进到“HEAD 分母已冻、内外正反例已核、substrate-fit 已判、缺口/净新契约/owner-gate/验收格栅可直接回灌 planning-proposed”的事实水位。
- **拟纳入**：
  - 9 份 `assessment-analysis`，每份遵守 `.adocs/templates/assessment-analysis.md`；
  - 共享 denominator 与 face-specific denominator；
  - HEAD / baseline / legacy / WEB Reference Anchor Matrix；
  - 稳定缺口 ID、跨面不变量、净新契约草案、owner-gate 候选；
  - 防假绿验收格栅草案与核验记录；
  - 一份站③ synthesis，将 9 面结论映射回 initial 的 `T-P-NH-* / G-NH-* / NH*-*`，再写 proposed。

### 5.1 站②完成定义

单面 analysis 只有同时满足下列条件才可标 `reviewed`，全部交叉冲突关闭后才可标 `frozen`：

1. 消费本 index 对应共享分母，不另估；新增分母有命令与 `path:line`；
2. 每个 S1/S2 gap 有 HEAD 证据；负证据不能只写“搜索没找到”；
3. legacy 锚明确“借什么/不借什么”，无 runtime/schema/API 依赖回流；
4. WEB 锚记录 primary source、版本/日期/访问日、支持的原子结论与限制条件；
5. Reference Anchor Matrix 同时有正例和反例，或诚实标 `🆕`；
6. 每条外部机制完成 substrate-fit，不以流行度替代适配性；
7. 缺口 ID、跨面不变量、契约草案、owner-gate、验收格栅齐全；
8. 与相邻面的事实冲突已互相引用并对账；
9. 核验记录列出 read/grep/run/websearch，未核项不得隐藏。

---

## 6. 边界 / Out-of-Scope `[核心]`

| 编号 | 排除项 | 为什么不在本阶段 | 承接相位 |
|---|---|---|---|
| `[O1]` | 修改 production/test 代码或 schema | assessment 只测量与供料 | proposed 后 design/action-plan |
| `[O2]` | 冻结具体 PDF/browser/OCR/model 选型 | 需先完成面 03/05 的多源核查与 owner gate | pre-charter QNA / design |
| `[O3]` | 排施工日历、PR 序列、人员分工 | 属执行规划，不属 assessment | planning-final / action-plan |
| `[O4]` | live chinatax/domain/REA connector、cookie/tunnel | 已被 `T-O-381` 排除 | 独立 connector campaign（若 owner reopen） |
| `[O5]` | 第五 source kind、caller workflow_key、legacy action_branch | frozen fence；核查只用作反例 | 除非新 Truth 推翻 |
| `[O6]` | cuts/g0 算法、按通道另写 S06 kernel | `T-O-376/386/389` 明确不重开 | 生成面独立 campaign |
| `[O7]` | 前端、public chat/answer generation | 不属于 intake four-channel | 独立产品阶段 |
| `[O8]` | `.experiment` 发车与评分 | `T-O-380` 未冻结发车日 | owner 实验令 |
| `[O9]` | 导入/编译/运行 legacy-family | `T-O-42` 只准 ReferenceAnchor | never，除非推翻绿地边界 |
| `[O10]` | 用 index 中的候选选项替 owner 决策 | assessment 零决策 | `pre-charter-qna.md` |

---

## 7. 已交付 · 勿重做 `[核心]`

| 已交付项 | 交付/证据 | 本阶段对它的关系 |
|---|---|---|
| 四类 strict SourceDescriptor 与 caller 禁 workflow_key | `src/contracts/api/models.py:107-178`; `workflow_registry.py:78-104` | `沿用；核查 kind graph delta` |
| 10 strategy registry / 9 clean capability | `strategies.py:15-164`; `intake/__init__.py:20-132` | `沿用；只核 live reachability/evidence` |
| deterministic web/doc 与 PDF/doc/vision typed clean 函数 | `intake/{web,pdf,doc}/`; 33 passed | `沿用；禁止重写，核 adapter 与缺口` |
| 三 provider strict schema/parser/digest/semantic tuples | `intake/api/`; `src/contracts/intake/providers/`; `semantics.py` | `沿用；只补统一 binding/retrieval/failure delta` |
| registered API scatter root/child 与 publication-ready | `builtin_scatter.py`; API e2e | `沿用；核 retrieval 与新 truth 回归` |
| Workflow immutable revision、无环、registered guard、compatibility definitions | `models.py`; `workflow_registry.py`; `lsrag_definition.py:1073-1080` | `重 substrate，只补 representation/merge/kind migration` |
| Task fingerprint replay、Gate CAS、部分 recovery | `task_create.py`; `runtime_gates.py`; API recovery e2e | `沿用；扩至 actual binding/upload/new paths` |
| S13 team CAS、verify-on-read、catalog、GC delete fence | `local_store.py`; `artifacts.py`; `object_gc.py` | `沿用；只建 public upload delta` |
| S04 Revision semantic table与 10 definitions | DDL；`registry.py:229-239` | `沿用；补 non-API authority/consumer/facet` |
| system-owned g0=clean、LS-RAG tail、publication proof、retrieval route | `generation_assemble.py:17-62`; Workflow tail；`api/public/routes.py:452-469` | `不动算法；只核四通道接通和语义投影` |
| Intake lifecycle/rebuild/metadata 基础服务与测试 | `src/runtime/intake/{acceptance_lifecycle,acquisition_intents,index_rebuild*}.py`; e2e | `沿用；核七意图 applicability 与不重 clean` |

---

## 8. 后续使用方式（流水线指引）`[核心]`

### 8.1 站②产出顺序（调查依赖，不是施工顺序）

```text
Wave A：01 graph ─┐
        03 representation ─┬─▶ 02 binding（冻结前消费 01/03）
        04 clean ──────────┤
        06 upload          ├─▶ 05 runtime（冻结前消费 03/04）
        07 semantics ──────┤
                           └─▶ 08 publication/lifecycle（消费 04/07）

Wave C：01..08 的稳定 gap / invariant ─▶ 09 assurance synthesis
```

- `01/03/04/06/07` 可并行开始 HEAD/legacy/web 核查；
- `02` 可同步调查，但冻结前必须消费 `01` selected-route 与 `03` evidence findings；
- `05` 冻结前必须消费 `03` representation protocol 与 `04` clean port；
- `08` 冻结前必须消费 `04` admitted clean 与 `07` semantic projection；
- `09` 最后冻结，统一所有 failure/replay/race/compatibility/acceptance 分母。

### 8.2 统一 analysis 输出合同

每份 analysis 除模板共有段外，必须在交接中输出以下可机器/人工汇总的稳定 ID：

| 类型 | ID 方案 | 下游用途 |
|---|---|---|
| Reference anchor | `RA-FF-CHANNEL-NN`（如 `RA-03-HEAD-01`） | 回溯正反例与 substrate-fit |
| blocker/gap | `NH-RAFF-BNN`（如 `NH-RA03-B01`） | proposed 工作项与风险来源 |
| cross-face invariant | `NH-C-NN`（如 `NH-C-01`） | 防相邻 AP 各自发明合同 |
| net-new seam | `NH-N-FF-NN`（如 `NH-N-02-01`） | design / spike 输入 |
| owner-gate | `G-NH-NN`（如 `G-NH-01`） | pre-charter QNA |
| acceptance draft | `NH-A-FF-NN`（如 `NH-A-04-01`） | planning-final/action-plan Test-ID |

### 8.3 站③+ 出口

1. 9 份 analysis 的缺口台账、净新契约、owner-gate、acceptance grid 汇入 `planning-proposed.md`；
2. proposed 必须逐条说明 initial 的 `T-P-NH-1..14` 是 `证实 / refine / 证伪`，并对 `NH1..NH5` DAG/AP 作有因调整；
3. 真相冲突或 owner-gate 进入 `pre-charter-qna.md`，assessment 不裁；
4. owner 裁决后再形成 final planning/design/action-plan；
5. 任何新 HEAD 变更若改变 §2.2 分母，先新修订本 index，再冻结下游 analysis。

### 8.4 websearch 使用纪律

- 每个技术问题先写原子问题，再搜索；禁止用一个大查询寻找“最佳架构”。
- 外部 claim 若可能随版本变化，必须核对发布日期/版本与当前访问日；只引用直接支持该 claim 的页面。
- 搜索技术问题只以 primary sources 作结论依据；不同路线的比较至少覆盖两个独立来源，明确哪部分是推断。
- 每一来源控制摘录，仅记录必要短句或完全转述；URL 紧邻结论，不堆“参考链接清单”。
- 外部正例必须同时找官方限制、错误语义、安全/兼容边界；没有反方资料时标置信不足。
- 任何外部云服务/框架机制必须经过 `T-O-42`、单体仓、local runtime、S03/S04/S13/S16 边界过滤；最终可借的是机制，不是栈。

---

## 9. 交叉引用 `[可选]`

- [`pre-initial-planning-qna.md`](pre-initial-planning-qna.md) — owner-gated foundational truth
- [`initial-planning.md`](initial-planning.md) — 待 proposed 裁定的 first-cut
- [`thoughts-on-initial-planning-by-GPT.md`](thoughts-on-initial-planning-by-GPT.md) — 本 index 的疑问、簇调整和 start-gate 来源
- `.adocs/templates/assessment-index.md` — 本文骨架
- `.adocs/templates/assessment-analysis.md` — 站②单面制品骨架
- `docs/baseline/domain-truth/D08-legacy-capabilities-migration.md` — legacy 可借/禁借的仓内基线
- `docs/baseline/spec-glossary.md` — SourceKind/CleanStrategy/FilterMeta/S05Binding/ReferenceAnchor 词汇权威

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|---|---|---|---|
| v0.1 | 2026-08-29 | GPT | 初稿：9 面评估地图、HEAD 冻结分母、三渠道正反例协议、owner-gate、勿重做与站②流水线 |
| v0.2 | 2026-08-29 | Grok parent independent-verify | 站② 九份 analysis 已产出（`reference-anchor/`，`draft`）；§4 增补 analysis 新 MARK 的 `G-NH-11..13,15..19`（不裁决，`G-NH-14` 空号）；进度条与地图链接更新 |
