# Nano-Agent 代码审查

> 审查对象: `MKB NS1 — non-interactive agentic production path`
> 审查类型: `mixed`（closure-review + code-review + test-coverage）
> 审查时间: `2026-08-14`
> 审查人: `Grok`
> 审查范围:
> - `docs/plan/new-start/NS1-new-pipeline.md`（P1–P5 / S1–S9 / NS1-T01–T46）
> - `docs/closure/new-start/NS1-new-pipeline-closure.md`
> - `docs/eval/new-start/pre-NS1-qna.md`（`T-O-337..351`）
> - `src/runtime/intake/`、`src/services/{registry,lsrag_compiler,config_snapshots}.py`、`src/workflows/`
> - `src/contracts/api/models.py`、`api/internal/{prompts,routes}.py`
> - `data/schemas/lsrag.layered_content.v1.json`、`data/prompts/**`
> - `tests/unit/test_ns1*.py`、`tests/unit/test_adopt_layered_json.py`、`tests/unit/test_claude_cli_port.py`、`tests/domain/test_ns1_guards.py`、`tests/e2e/test_ns1_pipeline.py`
> 对照真相:
> - `docs/eval/new-start/pre-NS1-qna.md`（只读）
> - `docs/plan/new-start/NS1-new-pipeline.md`
> - `docs/closure/new-start/NS1-new-pipeline-closure.md`
> 文档状态: `changes-requested`

---

## 0. 总结结论

> 单条 CLI stub 主路径已经立住，但 NS1 **不应**按 closure 写成 P1–P5 全部 closed。Catalog Update 会弄坏下一次 ingest；live B.json 丢掉 markdown 物料；scatter child 不继承 `prompt_selection`。测试覆盖了骨架，没有盖住这些断点。

- **整体判断**：核心骨架可跑，运输/catalog/集合路径仍有 correctness 断点，closure 把残差缩成「只有 pyturso」是过称。
- **结论等级**：`changes-requested`
- **是否允许关闭本轮 review**：`no`
- **本轮最关键的 1-3 个判断**：
  1. Catalog PATCH 插入第二条 `active` 行，snapshot 要求恰好一行 → Update 后新 ingest 失败（`T-O-349` 未真正可运营）。
  2. `live_inference=True` 时 B.json 固定 `input_text=clean`，违反 `T-O-350`「有 markdown 则 `-p`=markdown」。
  3. 测试把 T42 标成 legal 旅程，实际仍绑 `promptB.json.generic` + `{0,1,2}`；`json.legal` / `json.realestate` 未 bootstrap。

---

## 1. 审查方法与已核实事实

- **对照文档**：
  - `docs/plan/new-start/NS1-new-pipeline.md`
  - `docs/eval/new-start/pre-NS1-qna.md`
  - `docs/closure/new-start/NS1-new-pipeline-closure.md`
- **核查实现**：
  - `src/runtime/intake/generation_construct.py`、`generation_live.py`、`acceptance_scatter.py`、`clean_preflight.py`、`core.py`
  - `src/services/registry.py`、`config_snapshots.py`、`lsrag_compiler.py`
  - `src/workflows/lsrag_definition.py`、`builtin_scatter.py`
  - `src/contracts/api/models.py`、`api/internal/prompts.py`、`api/internal/routes.py`
  - `src/runtime/inference/claude_cli.py`
- **执行过的验证**：
  - `.venv/bin/python -m pytest -q tests/domain/test_ns1_guards.py tests/unit/test_adopt_layered_json.py tests/unit/test_ns1_api_workflow.py tests/unit/test_ns1_prompt_catalog.py tests/e2e/test_ns1_pipeline.py` → **16 passed**（本轮独立复跑）
  - 源码 `rg`：`adopt_layered_json`、`transcribe_markdown`、`json_prompt_id`、`compiler.structurize`、`_live_summaries`
  - 未复跑全量 `tests/e2e`；6 个 pyturso 失败采纳 closure 点名并对照测试源码（`sqlite3.connect` + `persistence_backend="turso"`）
- **复用 / 对照的既有审查**：
  - 三路只读子代理（plan completeness / mechanism wiring / test coverage）作线索
  - 本审查对 R1–R3 及 catalog/live/scatter 锚点均 **独立重读** 对应文件，不把子代理结论当事实

### 1.1 已确认的正面事实

- `layered_content.v1` 已落盘，`additionalProperties: false`，无 span 字段（`data/schemas/lsrag.layered_content.v1.json`）。
- 四角色正文目录存在：`data/prompts/{clean,markdown,json,summarizer}/` 各至少一份；B.json 正文不含 `semantic_understanding`。
- `007_ns1_prompt_catalog.sql` 是既有 `mkb_prompt_hash_pointers` 列晋升，不是第 56 张 required 表。
- 生产 structurize 走 `adopt_layered_json_with_report`（`generation_construct.py:581-595`）；`src/runtime/intake` 无 `compiler.structurize(`。
- Kernel 实现了 NFC/LF、g=0 回填、g≥1 精确子串首次命中、`occurrence_count`、按 layered 块投影（`lsrag_compiler.py:362-518`）。
- 主图与 scatter child 图有 `lsrag.transcribe_markdown`；无 `markdown_prompt_id` 可跳过。
- `IntakeIngestPayload` 必填 `json_prompt_id`，另三角可选（`api/models.py:175-184`）；`extra=forbid` 拒 `prompt_ref` / path。
- 结构失败路由 `structurize.failed` → `failed`，单测断言不开 human gate（`test_ns1_api_workflow.py:156-166`）。
- 确定性 / registered_api clean 不经 Claude（`clean_preflight.py:76-97,240-260`）。
- CLI port 可 stub；`--bare --system-prompt-file`；schema 仅 structured 请求带上。
- S14/D04 Appendix E 与 README 已回填四 role / identity-only API。
- 本轮复跑 NS1 定向 16 测全绿。

### 1.2 已确认的负面事实

- `register_prompt` INSERT 新 version 时 `status='active'`，不 retire 旧行（`registry.py:469-485`）。
- ingest snapshot 要求 `len(candidates) == 1`（`config_snapshots.py:582-584`）。Update 后再 ingest 同一 `prompt_id` 会 `PROMPT_NOT_REGISTERED`。
- `_structurize` 在 `live_inference` 分支固定 `input_text=clean`、`prompt_key="promptB.default"`（`generation_construct.py:551-562`），不用 `markdown_text`。
- scatter child manifest 的 `payload` 只有 source，没有 `prompt_selection` / `*_prompt_id`（`acceptance_scatter.py:115-127`）。
- CLI 缺 frozen selection 时回落到硬编码 `json/promptB.json.generic.v1.md`（`generation_construct.py:110-137`）。
- `_layered_profile` 在缺 json 行时默默用 `(0, 1, 2)`（`generation_construct.py:53-59`）。
- `_live_summaries` 仍按 projection block 循环 `text_generate`（`generation_live.py:474-505`）；`_construct` 已不调用，但是生产 mixin 残留。
- `DEFAULT_CATALOG_PROMPTS` 无 `promptB.json.legal` / `promptB.json.realestate`（`registry.py:66-72`）。磁盘也无对应 md。
- e2e「legal」旅程仍传 `promptB.json.generic` 并断言 g0/g1/g2（`test_ns1_pipeline.py:34-36`）。
- 无测试证明 catalog Update 后 in-flight digest 不变（计划 T34）。
- CRUD HTTP 测 override 了 operator token，未断言无 token / agent 禁写。
- `LsragContractCompiler.structurize` 仍是完整可调用 API（fixture 测试仍用）。
- 全量 e2e 仍有 6 个 pyturso/`sqlite3.connect` 残差（closure 已点名；本轮未复跑全量 e2e）。

### 1.3 证据可信度说明

| 证据类型 | 本轮是否使用 | 说明 |
|----------|--------------|------|
| 文件 / 行号核查 | `yes` | R1–R8 均有独立 `path:line` |
| 本地命令 / 测试 | `yes` | 定向 16 passed；未复跑全量 e2e |
| schema / contract 反向校验 | `yes` | `layered_content.v1` + `IntakeIngestPayload` + catalog 列 |
| live / deploy / preview 证据 | `n/a` | owner 禁止 live；本轮不声称 vendor 验证 |
| 与上游 design / QNA 对账 | `yes` | `T-O-337..351` 与 AP S1–S9 / P1–P5 |

---

## 2. 审查发现

### 2.1 Finding 汇总表

| 编号 | 标题 | 严重级别 | 类型 | 是否 blocker | 建议处理 |
|------|------|----------|------|--------------|----------|
| R1 | Catalog Update 产生双 active 行，ingest 解析失败 | `critical` | `correctness` | `yes` | PATCH 后 retire 旧 active，或 snapshot 按 version 选一行 |
| R2 | live B.json 忽略 markdown 物料 | `high` | `protocol-drift` | `yes` | live 与 CLI 一样：有 `markdown_text` 则 `-p` 用它 |
| R3 | scatter child 不继承 `prompt_selection` | `high` | `correctness` | `yes` | child manifest 写入冻结 selected_prompts |
| R4 | 未交付 `json.legal` / `json.realestate` 行与正文 | `medium` | `delivery-gap` | `no` | bootstrap + 正文 + e2e 用真实闭集 |
| R5 | `_live_summaries` 按句循环仍在生产 mixin | `medium` | `scope-drift` | `no` | 删除或标 private/test-only 并加守卫扫描 |
| R6 | T34 / T42 / T06 覆盖不足，存在假绿 | `medium` | `test-gap` | `no` | 补 Update-后再 ingest、legal `{0,1}` 旅程、无 token CRUD |
| R7 | CLI 缺 selection 时硬编码 generic 路径 | `medium` | `correctness` | `no` | 缺冻结指针应 fail-closed |
| R8 | closure 把残差收成「只有 pyturso」 | `medium` | `docs-gap` | `no` | 回填 R1–R3，勿标 P1–P5 全 closed |

### R1. Catalog Update 产生双 active 行，ingest 解析失败

- **严重级别**：`critical`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `src/services/registry.py:469-485` INSERT 新 version，`status='active'`，不 retire 旧行
  - `src/services/config_snapshots.py:582-584`：`len(candidates) != 1` → `PROMPT_NOT_REGISTERED`
  - `T-O-349`：Update = 新不可变版本，旧行保留，**但 ingest 必须仍能解析**
- **为什么重要**：
  - 业主要求的 CRUD 在第一次 PATCH 后让该 `prompt_id` 无法再开 Task
  - `resolve_prompt` 取 latest（`registry.py:411-415`）与 snapshot「恰好一行」不一致
- **审查判断**：
  - T-O-349 的「旧行保留」应指 **历史 version 可解析**，不是两行同时 active 抢解析
  - 实现把「不可变历史」做成了「双 active」
- **建议修法**：
  - PATCH 成功后将同 `prompt_id` 的旧 version 标 `retired`（或 `superseded`），新 version 为唯一 `active`
  - snapshot 按 `prompt_id` + 显式 version 选一行，不要 `len==1` 扫全部 active
  - 补测试：PATCH v2 后新 ingest 成功；已 materialize 的 Execution 仍用 v1 hash

### R2. live B.json 忽略 markdown 物料

- **严重级别**：`high`
- **类型**：`protocol-drift`
- **是否 blocker**：`yes`
- **事实依据**：
  - `generation_construct.py:551-562`：`live_inference` 时 `input_text=clean`、`prompt_key="promptB.default"`
  - 同函数 CLI 分支 `567-574` 才把 `markdown_text` 交给 `-p`
  - `T-O-350`：有 markdown 时 B.json 的 `-p` = markdown 正文
- **为什么重要**：
  - 打开 live 后，B.md 跳变成空转：图上跑了 transcribe，B.json 仍吃 clean
  - 硬编码 `promptB.default` 绕过 catalog `json_prompt_id`
- **审查判断**：
  - stub/CLI 路径符合 QNA；live 路径未接同一合同
- **建议修法**：
  - live 与 CLI 共用物料选择：`markdown_text or clean`
  - `prompt_key` / version 来自冻结 `selected_prompts["json"]`

### R3. scatter child 不继承 `prompt_selection`

- **严重级别**：`high`
- **类型**：`correctness`
- **是否 blocker**：`yes`
- **事实依据**：
  - `acceptance_scatter.py:115-127` child `payload` 只有 registered_api source
  - CLI 无 frozen selection 时回落 `json/promptB.json.generic.v1.md`（`generation_construct.py:110-115`）
  - `_layered_profile` 缺省 `(0, 1, 2)`（`generation_construct.py:53-59`）
  - child 图虽有 `transcribe_markdown`（`builtin_scatter.py:398-480`），物料绑定断了
- **为什么重要**：
  - 集合 ingest 无法把父 Task 的 `json_prompt_id` / 可选 markdown 传到 child
  - 法律/房产闭集在 scatter 上会被静默改成 generic `{0,1,2}`
- **审查判断**：
  - 图在、绑定不在，属于断点而非「scatter 不做 NS1」
- **建议修法**：
  - child manifest / snapshot 复制父 Execution 冻结的 `selected_prompts`
  - 缺 json 选择时 fail-closed，禁止硬编码 generic

### R4. 未交付 `json.legal` / `json.realestate` 行与正文

- **严重级别**：`medium`
- **类型**：`delivery-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - AP P1-04：bootstrap `json.legal {0,1}`、`json.realestate {0}`
  - `registry.py:66-72` 只有 `promptB.json.generic` + 兼容 `promptB.default`，均为 `{0,1,2}`
  - `data/prompts/json/` 仅 `promptB.json.generic.v1.md`
- **为什么重要**：
  - `T-O-344/351` 的领域闭集没有可调用的 catalog 行
  - T42 无法证明 legal 闭集
- **审查判断**：
  - 最小「每 role 一份」够跑通 generic；领域变体 under-delivery
- **建议修法**：
  - 补正文、bootstrap、e2e 分别绑 `{0,1}` / `{0}`

### R5. `_live_summaries` 按块循环仍在生产 mixin

- **严重级别**：`medium`
- **类型**：`scope-drift`
- **是否 blocker**：`no`
- **事实依据**：
  - AP P2-03：删除 `_live_summaries` 按句循环
  - `generation_live.py:474-505` 仍对每个 projection block `text_generate`
  - `_construct` 已改走整包 layered
- **为什么重要**：
  - 残留入口可被误接，破坏 `T-O-347` / `T-O-138`
- **审查判断**：
  - 当前主路径不用，但是计划明确要删
- **建议修法**：
  - 删除该方法，或移出 production mixin，守卫扫描点名禁止

### R6. T34 / T42 / T06 覆盖不足，存在假绿

- **严重级别**：`medium`
- **类型**：`test-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - 无「PATCH 后 retry / 新 ingest」测试（T34）
  - `test_ns1_pipeline.py` 的 markdown 旅程仍用 `promptB.json.generic` 并断言 g0/g1/g2（T42）
  - `test_ns1_prompt_routes.py` override operator token，无 401/agent 用例（T06）
  - T33 只测路由表，不是 live structurize 失败后的 gate 表
- **为什么重要**：
  - R1 在现有绿灯下完全看不见
  - 「legal 旅程」名实不符
- **审查判断**：
  - 骨架测试真实存在且本轮 16 passed；不能当作机制全覆盖
- **建议修法**：
  - 补 T34、真正 legal `{0,1}` e2e、无 token CRUD、structurize-fail e2e

### R7. CLI 缺 selection 时硬编码 generic 路径

- **严重级别**：`medium`
- **类型**：`correctness`
- **是否 blocker**：`no`
- **事实依据**：
  - `generation_construct.py:110-137` fallback `json/promptB.json.generic.v1.md`
  - receipt 即使走了 frozen pointer 仍可能写死该相对路径
- **为什么重要**：
  - 违反 `T-O-348` fail-closed；审计撒谎
- **审查判断**：
  - 与 R3 叠加后，scatter 会静默用 generic
- **建议修法**：
  - 无冻结 json 指针 → `PROMPT_NOT_REGISTERED`；receipt 写实际 path

### R8. closure 把残差收成「只有 pyturso」

- **严重级别**：`medium`
- **类型**：`docs-gap`
- **是否 blocker**：`no`
- **事实依据**：
  - closure §0：唯一 known gap 是 6 个 e2e 用 `sqlite3` 打开 pyturso 文件
  - 上述 R1–R3 不在 deferred ledger
  - AP 文首仍是 `executing`，§11 却把 P1–P5 标 `✅ done`
- **为什么重要**：
  - 下游会按「NS1 已完成」开工
- **审查判断**：
  - pyturso 残差属实，且与 NS1 断言无关；**不是**唯一残差
- **建议修法**：
  - closure 改为 `partial`：列出 R1–R3；T44 保持 partial

---

## 3. In-Scope 逐项对齐审核

| 编号 | 计划项 / 设计项 / closure claim | 审查结论 | 说明 |
|------|----------------------------------|----------|------|
| S1 / P1-01 | `layered_content.v1` + 金样 | `partial` | schema 在；无 `tests/fixtures/ns1/`；`knowledge_tree` 仍留；领域金样仅 inline |
| S2 / P1-02 | 四角色正文，退役 semantic_block | `partial` | 每 role 一份 generic/legal-md；无 json.legal / json.realestate |
| S3 / P1-03..06 | catalog 列 + CRUD + hash 门闩 | `partial` | DDL/hash 在；Update 与 snapshot 冲突（R1） |
| S4 / P2-01..02 | adopt 为 current，假树退出生产调用 | `done` | 生产 intake 无 `compiler.structurize(` |
| S5 / P3-01..05 | CLI 四跳可 stub | `partial` | stub 主路径在；live 忽略 markdown；transcribe 未独立成文件（可接受） |
| S6 | markdown 可跳；json 不可跳；C 吃 adopted JSON | `done` | 图 + e2e 步列表 + construct map |
| S7 / P4-01 | ingest 只收 `*_prompt_id` | `done` | 公共 DTO 无 `prompt_ref`/path |
| S8 / P4-03 | 结构失败不开门审 | `done` | 路由 + unit；e2e 偏薄（R6） |
| S9 / P5 | unit/domain/e2e 覆盖全部机制 | `partial` | 骨架绿；T34/T42/T06/领域闭集不足 |
| P4-04 | materialize 冻 hash，retry 不热切 | `partial` | 字段会冻；无 T34；Update 后新 ingest 坏 |
| P5-02 | 两条 mega 旅程 | `partial` | 有/无 md 都绿；legal 不是 `{0,1}` |
| P5-03 | sibling 完成、root fail-closed | `done` | 复用 scatter e2e；不是 adopt 失败（可接受） |
| P5-04 | S14/D04 附录 | `done` | Appendix E + README |
| Closure「P1–P5 全 closed」 | 全部 phase | `stale` | 与树不一致 |
| Closure「唯一残差 pyturso」 | T44 | `partial` | pyturso 真实，但不是唯一 gap |

### 3.1 对齐结论

- **done**: `6`（S4、S6、S7、S8、P5-03、P5-04）
- **partial**: `8`（S1–S3、S5、S9、P1-01/02/04/05、P3-04、P4-04、P5-02）
- **missing**: `0`（无整项消失；断点在接线）
- **stale**: `1`（closure「P1–P5 全 closed」）
- **out-of-scope-by-design**: `修理工 / live vendor / 部分成功 / 删 human_review 节点`

> 这更像「generic CLI stub 主路径完成，catalog 运营面与 live/scatter 绑定未收口」，不是 completed。

---

## 4. Out-of-Scope 核查

| 编号 | Out-of-Scope / Deferred 项 | 审查结论 | 说明 |
|------|----------------------------|----------|------|
| O1 | `lsrag.structure_repair` / `grok -p` | `遵守` | 无修理工 Process |
| O2 | 重开 S03/S04/D08/S08–S10 | `遵守` | 未改状态机/接受事务/parser |
| O3 | 新建 required 表；DB 存正文 | `遵守` | 007 只加列；无 `body_text` |
| O4 | scatter 部分成功 | `遵守` | 仍 `scatter-required-child-failed` |
| O5 | live Claude / 部署 | `遵守` | 无 vendor 验证声称 |
| O6 | 公网 marketplace / agent 写 catalog | `遵守` | 路由在 `/internal`；测试未证明无 token 拒绝（R6） |
| — | pyturso 六例 | `误报风险` | 是 harness residual，**不要**当成 NS1 机制失败；也 **不要**当成唯一 residual |

---

## 5. 最终 verdict 与收口意见

- **最终 verdict**：NS1 的 adopt kernel、identity-only ingest、可选 markdown 图、stub 四跳在单文件 CLI 路径上成立。Catalog Update、live markdown 物料、scatter 指针继承未到位。测试覆盖骨架并留下假绿。closure 过称。
- **是否允许关闭本轮 review**：`no`
- **关闭前必须完成的 blocker**：
  1. 修 R1：Update 后仍能 ingest；旧 version 可被冻结 Execution 解析
  2. 修 R2：live B.json 与 CLI 共用「markdown 或 clean」物料，且用冻结 `json_prompt_id`
  3. 修 R3：scatter child 继承 `selected_prompts`，缺 json 选择 fail-closed
- **可以后续跟进的 non-blocking follow-up**：
  1. bootstrap `json.legal` / `json.realestate` 并改 T42
  2. 删除 `_live_summaries`；CLI receipt 写真实 path
  3. 补 T34 / 无 token CRUD / structurize-fail e2e
  4. 回写 closure deferred ledger；Turso inspection 另 charter
- **建议的二次审查方式**：`same reviewer rereview`（只复核 R1–R3 与对应测试）
- **实现者回应入口**：`请按 docs/templates/code-review-respond.md 在本文档 §6 append 回应，不要改写 §0–§5。`

> 本轮 review 不收口，等待实现者按 §6 响应并再次更新代码。

---

## 6. 实现者回应（append-only）

> 实现者在此追加。审查人不得改写 §0–§5。
