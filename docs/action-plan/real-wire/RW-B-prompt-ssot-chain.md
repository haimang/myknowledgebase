# 行动计划 · RW-B — prompt 本地文件 + SQLite-SSOT 语义链去桩（mock 下）

> 服务业务簇: `real-wire / prompt 驱动的语义处理链（注册/渲染/对账 + structurize/summary/clean 去桩）`
> 计划对象: `RW-B phase（final-execution-plan §6.B，台账 RWB-01..08）`
> 类型: `new + modify`（prompt SSOT 机制净新 / 语义链去桩改造）
> 作者: `Opus 4.8`
> 时间: `2026-06-01`
> 文件位置: `prompts/(新建本地文件夹) · packages/config/ · packages/rag_structurizer/ · packages/rag_constructor/ · packages/workflow_clean/ · packages/workflow_rag/ · tests/e2e/`
> 上游前序 / closure:
> - `docs/action-plan/real-wire/RW-A-provider-base.md`（协议/工厂/MockLLM/1024 — 本 AP 的前置）
> - `docs/eval/real-wire/final-execution-plan-by-opus.md` §6.B
> 下游交接:
> - `docs/action-plan/real-wire/RW-C-live-wiring.md`（真实 LLM 替 mock；本 AP 留好 prompt→provider 链）
> 关联设计 / 调研文档:
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（轴 B 锚定矩阵）
> 冻结决策来源:
> - `docs/eval/real-wire/pre-charter-qna.md`（frozen；只读引用 Q-RW-3 + reframe）
> grounding 来源:
> - `eval-reference-anchor 轴 B` + HEAD 实测（本 AP 期亲验 file:line）
> 关联 reference-anchor:
> - `docs/eval/real-wire/reference-anchor-by-opus.md`（§7.3 指回真源）
> 文档状态: `draft`

---

## 0. 执行背景与目标

冻结 Q-RW-3 定义了 prompt 体系：**Python 单体不用 KV**；prompt 正文存本地文件（owner 编辑层）→ 经 hash 注入 SQLite 动态存取，**SQLite 为 SSOT**（替代 Cloudflare KV）；本地文件经 hash 与 SQLite 对账确认。HEAD 已有 `prompt_versions` 表（`core.sql:362-376`，含 `template_path`+`template_digest`，**无独立 text 列**）与读取器 `get_active_prompt`（`config_repo.py:31`，**0 消费方**，F6c 遗留孤立）。RW-B 在 RW-A 的协议/工厂/MockLLM 基座上，把这套 prompt-SSOT 机制接通，并把 structurize/summary/clean 三段**规则化桩**去桩为「prompt→渲染→LLM(mock)」模式（保留规则化 fallback），最终用 mock capstone 证明「文档→prompt→LLM(mock)→embed(1024)→search 语义命中」的使用链真实发生。本 AP 全程 mock、零外网、零计费。

**SSOT 机制落地（据现有 DDL，无 schema 改）**：`prompt_versions` 在 SQLite 持有权威的 `(prompt_key, version, template_path, template_digest, status=active)` 注册；运行时 `get_active_prompt` 取该记录 → 按 `template_path` 加载本地文件 → 计算 sha256 与 `template_digest` 比对（不一致 fail-loud）→ 渲染变量 → 交 provider。SQLite 是「哪个 prompt/版本/digest 权威」的 SSOT，本地文件是被其 digest 校验的编辑层。

- **服务业务簇**：`real-wire / prompt 语义链`
- **计划对象**：`RW-B phase（RWB-01..08）`
- **本次计划解决的问题**：
  - prompt 正文无处存（KV 不可用，repo 无正文）；`get_active_prompt` 有读取器但 **0 消费方**（`config_repo.py:31`）。
  - structurize/summary/clean 是**规则化桩**（`rag_structurizer/service.py:30`、`rag_constructor/service.py:80`、`workflow_clean/action_registry.py:90-101` degraded），无 prompt/LLM 路径。
  - 无 prompt 渲染引擎、无本地文件↔SQLite digest 对账。
- **本次计划的直接产出**：
  - 本地 `prompts/` 文件夹 + 核心 prompt 正文（据输出 schema/用法本地编写）。
  - prompt 渲染引擎（变量注入 + sha256 digest 校验 + 文件↔SQLite 对账，不一致 fail-loud）。
  - `prompt_versions` seed（SQLite-SSOT）+ `get_active_prompt` 接入消费侧（消除 F6c 孤立）。
  - structurize/summary/clean 去桩为 prompt→render→MockLLM（规则化 fallback 留）。
  - mock capstone（语义命中 + 使用链证据）+ 防假绿标 non-delivery-quality。
- **本计划不重新讨论的设计结论**：
  - prompt=本地文件 + SQLite-SSOT + hash 对账，替代 Cloudflare KV（来源：`Q-RW-3`）。
  - 正文据 schema/用法本地编写，legacy KV 不导出（来源：`Q-RW-3`）。
  - 本轮走 MockLLM，真实 LLM 延后（来源：`Q-RW-2` + reframe）。

---

## 1. 执行综述

### 1.1 总体执行方式

**先 SSOT 机制后去桩 + 先红后绿**：先把 prompt 正文/seed/渲染/对账打通（substrate），再逐段去桩（structurize→summary→clean），最后用 capstone 串起整条链并防假绿。去桩保留规则化 fallback，确保无 prompt/LLM 时仍可降级运行（TR-4）。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | prompt SSOT 机制（正文+seed+渲染+对账）| M | 本地文件 → SQLite-SSOT → 渲染 → digest 对账，接入 get_active_prompt | RW-A |
| Phase 2 | structurize 去桩 | M | `structurize_text` 增 prompt→MockLLM 模式，规则 fallback 留 | Phase 1 |
| Phase 3 | summary/construct + clean 去桩 | M | `build_summary` + clean gemini* degraded→LLM 模式（mock）| Phase 1 |
| Phase 4 | mock capstone + 防假绿 | M | 端到端 mock 使用链 + 语义命中 + non-delivery-quality 标注 | Phase 2,3 |

### 1.3 Phase 说明

1. **Phase 1 — prompt SSOT 机制**
   - **核心目标**：本地文件 + SQLite-SSOT + 渲染 + digest 对账 + 接消费侧。
   - **为什么先做**：去桩的三段都依赖「能取到并渲染 prompt」；对账是 SSOT 的诚实闸。
2. **Phase 2 — structurize 去桩**
   - **核心目标**：`structurize_text` 增 prompt→render→MockLLM 模式。
   - **为什么放在这里**：structurize 是语义链第一段，schema 最明确（`schemas_common.ts:135-154`）。
3. **Phase 3 — summary/construct + clean 去桩**
   - **核心目标**：`build_summary` + clean `geminiUnderstanding` 等 degraded→LLM 模式（mock）。
   - **为什么放在这里**：依赖同一渲染/provider 机制；与 structurize 同构。
4. **Phase 4 — mock capstone + 防假绿**
   - **核心目标**：端到端 mock 链 + 使用链证据 + 防假绿。
   - **为什么放在这里**：验证前三 Phase 串通；收口硬闸。

### 1.4 执行策略说明

- **执行顺序原则**：SSOT 机制 → 逐段去桩 → capstone 串通。
- **风险控制原则**：每段去桩保留规则化 fallback；digest 不一致 fail-loud（不静默用旧 prompt）。
- **测试推进原则**：每段先红（桩行为）后绿（prompt 模式）；capstone 为 spike，详见 §8。
- **文档同步原则**：`prompts/` 目录加 README 说明编辑→seed→对账流程。
- **回滚 / 降级原则**：无 prompt/provider 时回落规则化 fallback（已有桩逻辑保留为 fallback 分支）。

### 1.5 本次 action-plan 影响结构图

```text
RW-B prompt 语义链
├── Phase 1: prompt SSOT 机制
│   ├── prompts/（新建：structurize.md / summarize.md / clean-understand.md 正文）
│   ├── packages/config/config_repo.py:31（get_active_prompt 接消费）
│   ├── prompt 渲染引擎（新建：变量注入 + sha256 + 文件↔SQLite 对账）
│   └── prompt_versions seed（core.sql:362 表，行级 seed）
├── Phase 2: structurize 去桩
│   └── packages/rag_structurizer/service.py:30,64
├── Phase 3: summary/construct + clean 去桩
│   ├── packages/rag_constructor/service.py:80（build_summary）
│   └── packages/workflow_clean/action_registry.py:90-101（gemini* degraded）
└── Phase 4: mock capstone + 防假绿
    ├── tests/e2e/test_real_wire_mock_capstone.py（新建）
    └── tools/scripts/check_assert_strength.py
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** 本地 `prompts/` 正文（核心 structurize/summarize/clean-understand）+ `prompt_versions` seed（SQLite-SSOT）。
- **[S2]** prompt 渲染引擎（变量注入 + sha256 digest 校验 + 本地文件↔SQLite 对账，fail-loud）+ 接入 `get_active_prompt` 消费侧。
- **[S3]** structurize/summary/clean 去桩为 prompt→render→MockLLM（规则化 fallback 留）。
- **[S4]** mock capstone（语义命中 + 使用链证据）+ 防假绿。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 真实 LLM 调用（用 RW-A 的 MockLLMProvider）—— RW-C。
- **[O2]** prompt 质量/语义保真的「真实交付级」评估 —— mock 只验使用链+结构，质量在 RW-C live。
- **[O3]** KV 导出（legacy KV 不可达不导出，正文本地编写）。
- **[O4]** prompt 多版本/灰度运营 UI —— 平台化轮。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| prompt 渲染 + digest 对账 | in-scope | SSOT 机制核心（Q-RW-3）| — |
| structurize/summary/clean 去桩 | in-scope | 语义链主体；走 MockLLM | — |
| 真实 LLM 替 mock | out-of-scope | provider 延后（Q-RW-2）| RW-C charter |
| prompt 正文 KV 导出 | out-of-scope | KV 不可达（Q-RW-3）| — |
| prompt_versions 加 text 列 | defer | 现 DDL（path+digest）已够 SSOT；无需 schema 改 | 若需 DB 内联正文则单列 migration |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| RWB-01 | Phase 1 | 本地 prompt 正文（据 schema/用法编写）| add | `prompts/*.md（新建）` | 核心 prompt 正文落本地文件 | RWB-T01 | medium |
| RWB-02 | Phase 1 | prompt 渲染引擎 + sha256 + 文件↔SQLite 对账 | add | `packages/config/...（新建 renderer）`、`config_repo.py:20,47` | 渲染正确；digest 不一致 fail-loud | RWB-T02 | high |
| RWB-03 | Phase 1 | `prompt_versions` seed + 接 `get_active_prompt` 消费侧 | add | `core.sql:362-376`、`config_repo.py:31` | 消费侧读 SQLite；F6c 孤立消除 | RWB-T03 | medium |
| RWB-04 | Phase 2 | structurize 去桩（规则→prompt→MockLLM）| modify | `rag_structurizer/service.py:30,64` | mock 下走 prompt 链；规则 fallback 留 | RWB-T04 | high |
| RWB-05 | Phase 3 | summary 去桩（build_summary→summarize prompt）| modify | `rag_constructor/service.py:80` | mock 下摘要走 prompt；fallback 留 | RWB-T05 | medium |
| RWB-06 | Phase 3 | clean LLM 去桩（gemini* degraded→LLM 模式 mock）| modify | `workflow_clean/action_registry.py:90-101` | LLM 模式走 mock；degraded fallback 留 | RWB-T06 | medium |
| RWB-07 | Phase 4 | mock capstone（文档→prompt→LLM(mock)→embed(1024)→search）| add | `tests/e2e/test_real_wire_mock_capstone.py（新建）` | 端到端通过 + 使用链证据 | RWB-T07 | medium |
| RWB-08 | Phase 4 | 防假绿（mock 标 non-delivery-quality）| add | `tools/scripts/check_assert_strength.py`、capstone 断言 | 断言强度门禁过；不冒充质量 | RWB-T08 | low |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — prompt SSOT 机制

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWB-01 | 本地 prompt 正文 | a) 建 `prompts/` 文件夹（owner 编辑层）；b) 据输出 schema（借 `schemas_common.ts:135-154` 的 context_meta/layered_content/强制 llm_summary 形状）+ 用法编写 `structurize.md`；c) 据摘要 block-0 剥离/context_meta 回填启发式（借 `summarizer.ts:194,260`）编写 `summarize.md`；d) 据 clean understanding 用法编写 `clean-understand.md`；e) 正文含变量占位（如 `{{input_text}}`）；f) legacy KV 不导出，正文本地原创 | `prompts/structurize.md`、`prompts/summarize.md`、`prompts/clean-understand.md`（新建）| 三核心 prompt 正文就位、含变量占位 | RWB-T01 | 文件存在 + 含 schema 要求字段指令 |
| RWB-02 | prompt 渲染引擎 + 对账 | a) `render(prompt_key, variables) ` 流程：`get_active_prompt`(SQLite) → `template_path` 加载文件 → 计算 sha256 → 与 `template_digest` 比对；b) **不一致 fail-loud**（机器可读 reason，TR-4），不静默用旧/文件；c) 变量注入（`{{var}}` 替换，缺变量 fail-loud）；d) 返回渲染后文本交 provider；e) 边界：文件缺失/digest 缺失/变量缺失各自 fail-loud；f) 渲染纯函数、可测 | `packages/config/...（新建 prompt_renderer.py）`、`config_repo.py:20`(template_digest),`:47` | 渲染正确；文件↔SQLite 不一致即 fail-loud | RWB-T02 | 渲染正例 + digest 不一致/变量缺失 fail-loud 用例 |
| RWB-03 | seed + 接消费 | a) seed `prompt_versions` 行（`prompt_key`/`version`/`template_path`/`template_digest=文件 sha256`/`status='active'`）；b) seed 走幂等迁移/启动注册；c) 把 `get_active_prompt`(`config_repo.py:31`) 接到 structurize/summary/clean 消费侧（消除 F6c 0-消费方孤立）；d) 提供「注册/同步」步：编辑文件后重算 digest 回写 seed | `core.sql:362-376`、`config_repo.py:31` | SQLite 为 SSOT；消费侧读 DB | RWB-T03 | seed 后 get_active_prompt 返活跃记录 + 消费侧调用 |

### 4.2 Phase 2 — structurize 去桩

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWB-04 | structurize 去桩 | a) `structurize_text`(`service.py:30`) 增「LLM 模式」分支：取 `render('structurize', {input_text})` → `MockLLMProvider.complete_json(prompt, schema)` → pydantic 校验响应（借 `schemas_common.ts:135-154` 形状）；b) 校验层防御性回填（LLM 漏返字段用输入回填，借 `summarizer.ts:260` 思路）；c) **保留现规则化逻辑（`:30-64`）作 fallback**（无 provider/degraded 时）；d) 模式由 RW-A 工厂/Settings 决定（mock 默认）；e) 边界：响应非法 JSON / schema 不符 → fail-loud + reason；f) structurize 输出契约不变（下游 construct 兼容）| `rag_structurizer/service.py:30,64` | mock 下走 prompt→MockLLM→schema 校验；规则 fallback 留 | RWB-T04 | LLM 模式 + fallback 两路径测试 + schema 校验 |

### 4.3 Phase 3 — summary/construct + clean 去桩

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWB-05 | summary 去桩 | `build_summary`(`service.py:80`) 增 LLM 模式：`render('summarize', {chunk})` → `MockLLMProvider.complete` → 回填 context_meta；保留现规则化摘要（heading+首句截断）作 fallback；模式由 Settings 决定 | `rag_constructor/service.py:80` | mock 下摘要走 prompt；fallback 留 | RWB-T05 | LLM 模式 + fallback 两路径 |
| RWB-06 | clean LLM 去桩 | `action_registry.py:90-101` 的 `geminiUnderstanding`/`*-geminiClean` 由 `register_degraded`→注册真实 handler（LLM 模式，走 MockLLMProvider + render('clean-understand')）；**无 LLM 模式时保留 degraded fallback**（`DegradedActionError`）；遵守 F3 终态单一归属（handler 只产正文）| `workflow_clean/action_registry.py:90-101` | LLM 模式走 mock；degraded fallback 留 | RWB-T06 | LLM 模式 handler + degraded fallback 两路径 |

### 4.4 Phase 4 — mock capstone + 防假绿

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| RWB-07 | mock capstone | a) e2e：装载 eval corpus（RW-A 的 RWA-06）→ b) 注册本地 prompt 入 SQLite + digest 对账 → c) ingest 文档 → d) clean(MockLLM) → e) structurize(MockLLM) → f) construct/summary(MockLLM) → g) embed(1024) → h) search 语义命中 → i) `assert_used_real_chain`(RWA-07) + `assert_vector_authentic`(F7) 断言 provider/prompt 被真调；j) 断言 search 命中期望片段 | `tests/e2e/test_real_wire_mock_capstone.py`（新建）| 端到端 mock 通过 + 使用链证据 | RWB-T07 | A–J 步全绿 + 使用链断言 |
| RWB-08 | 防假绿 | mock 测仅验「使用链发生 + 结构合法」，**标 non-delivery-quality**（不断言语义质量等同真实）；`check_assert_strength.py` 扫 capstone 断言；mock/真实质量分层注释 | `tools/scripts/check_assert_strength.py`、capstone 注释 | 断言强度门禁过；不冒充质量 | RWB-T08 | 门禁 0 命中 + non-delivery 标注 |

---

## 5. Phase 详情

### 5.1 Phase 1 — prompt SSOT 机制

- **Phase 目标**：本地文件 → SQLite-SSOT → 渲染 → digest 对账 → 接消费。
- **本 Phase 对应编号**：`RWB-01` / `RWB-02` / `RWB-03`
- **本 Phase 新增文件**：`prompts/{structurize,summarize,clean-understand}.md`、`packages/config/.../prompt_renderer.py`
- **本 Phase 修改文件**：`config_repo.py:31`（接消费侧）、`prompt_versions` seed
- **具体功能预期**：
  1. 三核心 prompt 正文据 schema/用法本地编写，含 `{{var}}` 占位。
  2. 渲染引擎：取 SQLite 活跃记录 → 加载 `template_path` → sha256 比对 `template_digest`。
  3. digest 不一致 → fail-loud（机器可读 reason），不静默降级。
  4. 变量缺失/文件缺失 → fail-loud。
  5. `prompt_versions` seed（path+digest+status=active）幂等。
  6. `get_active_prompt` 接入消费侧，F6c 0-消费方孤立消除。
- **对应测试台账项**：`RWB-T01` / `RWB-T02` / `RWB-T03`
- **收口标准**：渲染正例 + 对账 fail-loud 用例 + seed/消费链路绿。
- **本 Phase 风险提醒**：digest 对账是 SSOT 诚实闸——必须 fail-loud，否则文件改了跑旧 prompt 即假 SSOT。

### 5.2 Phase 2 — structurize 去桩

- **Phase 目标**：`structurize_text` 增 prompt→MockLLM 模式（规则 fallback 留）。
- **本 Phase 对应编号**：`RWB-04`
- **本 Phase 修改文件**：`rag_structurizer/service.py:30,64`
- **具体功能预期**：
  1. LLM 模式：render('structurize') → MockLLM.complete_json → schema 校验。
  2. 防御性回填（LLM 漏返字段用输入回填）。
  3. 规则化逻辑保留为 fallback。
  4. 模式由 Settings/工厂决定（默认 mock）。
  5. 响应非法 JSON / schema 不符 → fail-loud。
  6. structurize 输出契约不变（下游兼容）。
- **对应测试台账项**：`RWB-T04`
- **收口标准**：LLM 模式 + fallback 两路径 + schema 校验绿。
- **本 Phase 风险提醒**：去桩不能破坏输出契约——下游 construct 依赖 structurize 形状。

### 5.3 Phase 3 — summary/construct + clean 去桩

- **Phase 目标**：`build_summary` + clean gemini* degraded→LLM 模式（mock）。
- **本 Phase 对应编号**：`RWB-05` / `RWB-06`
- **本 Phase 修改文件**：`rag_constructor/service.py:80`、`workflow_clean/action_registry.py:90-101`
- **具体功能预期**：
  1. `build_summary` LLM 模式 render('summarize')→MockLLM；规则摘要 fallback 留。
  2. clean `geminiUnderstanding` 等由 register_degraded→真实 handler（LLM 模式 mock）。
  3. 无 LLM 模式时保留 `DegradedActionError` fallback。
  4. 遵守 F3 终态单一归属（handler 只产正文）。
  5. 边界：mock 未命中 → fail-loud。
- **对应测试台账项**：`RWB-T05` / `RWB-T06`
- **收口标准**：各两路径（LLM/fallback）绿。
- **本 Phase 风险提醒**：clean handler 不得复刻 artifact 写入（F3-02 终态单一归属）。

### 5.4 Phase 4 — mock capstone + 防假绿

- **Phase 目标**：端到端 mock 使用链 + 防假绿。
- **本 Phase 对应编号**：`RWB-07` / `RWB-08`
- **本 Phase 新增文件**：`tests/e2e/test_real_wire_mock_capstone.py`
- **具体功能预期**：
  1. A–J 步端到端（corpus→prompt 注册+对账→ingest→clean→structurize→summary→embed(1024)→search→使用链断言→命中断言）。
  2. `assert_used_real_chain` 断言 provider/prompt 被真调。
  3. search 命中期望片段。
  4. mock 标 non-delivery-quality（不断言质量等同真实）。
  5. 断言强度门禁过。
- **对应测试台账项**：`RWB-T07` / `RWB-T08`
- **收口标准**：A–J 全绿 + 使用链证据 + 门禁 0 命中。
- **本 Phase 风险提醒**：capstone 易假绿——必须 spy 真实调用 + 命中断言，不能只验「跑完不报错」。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `Q-RW-3` prompt=本地文件+SQLite-SSOT+hash 对账 | `pre-charter-qna.md` | 整个 Phase 1 + 去桩取 prompt 方式 | blocked，回 qna |
| `Q-RW-2` provider 延后；本轮 MockLLM | `pre-charter-qna.md` | 去桩走 MockLLMProvider（RW-A 产）| 不接真实 LLM |
| `Q-RW-1` 维度 1024 | `pre-charter-qna.md` | capstone embed 1024 | 依赖 RW-A 完成 |
| reframe 本轮=mock+测 mock | `pre-charter-qna.md`（最高口径）| 质量只验使用链+结构，不验交付级 | — |
| `[Q3]` 去桩增量（LLM degraded）| `owner-gated-qna.md` | clean/structurize degraded→LLM 模式 + fallback | 保留 fallback |
| `[Q7]` 先红后绿 | `owner-gated-qna.md` | 每段先红后绿 | — |
| RW-A 协议/工厂/MockLLM/1024 | `RW-A-provider-base.md` | 本 AP 全程依赖 | RW-A 未完成则 blocked |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| B-1 | `packages/config/.../config_repo.py:31` | `get_active_prompt` 读取器 | RWB-03 接消费侧 | ✅ 复用 | 已有读取器，0 消费方（F6c）|
| B-2 | `packages/config/.../config_repo.py:19,20,47` | `template_path`/`template_digest` 字段 | RWB-02 对账载体 | ✅ 复用 | path+digest 已够 SSOT，无需加 text 列 |
| B-3 | `packages/storage_sqlite/.../migrations/core.sql:362-376` | `prompt_versions` DDL（path+digest+status）| RWB-03 seed | ✅ 复用 | 现有表，行级 seed（无 schema 改）|
| B-4 | `packages/rag_structurizer/.../service.py:30,64` | `structurize_text` 规则化桩 | RWB-04 去桩落点 | ♻️ 重 substrate | 增 LLM 模式，规则留 fallback |
| B-5 | `packages/rag_constructor/.../service.py:80` | `build_summary` 规则化桩 | RWB-05 去桩落点 | ♻️ 重 substrate | 增 LLM 模式 |
| B-6 | `packages/rag_constructor/.../service.py:91` | `with_context_header`（F6b）| capstone 上下文头 | ✅ 复用 | 借元数据前缀思路（recorder.ts:70-95）|
| B-7 | `packages/workflow_clean/.../action_registry.py:90-101` | gemini* `register_degraded` | RWB-06 去桩落点 | ♻️ 重 substrate | degraded→真实 handler，fallback 留 |
| B-8 | `packages/workflow_clean/.../action_registry.py:50-58` | `register`/`register_degraded` 机制 | RWB-06 用 | ✅ 复用 | 已有分派机制 |
| B-9 | `tests/e2e/`、F7 `assert_vector_authentic` | e2e 底座 + 向量真实性断言 | RWB-07 capstone | ✅ 复用 | 与 RWA-07 协同 |
| B-10 | `legacy/.../core/kv.ts:43-51`（PROMPT_REGISTRY）| prompt key 分类法 | RWB-01/03 key 命名 | 🔶 部分借 | 借 key 分类法，不借 KV 存储 |
| B-11 | `legacy/.../core/schemas_common.ts:135-154` | 结构化输出 schema 形状 | RWB-01/04 prompt+校验 | 🔶 部分借 | 借 schema 形状→pydantic；llm_summary 必返指令需在 prompt 复述 |
| B-12 | `legacy/.../services/summarizer.ts:194,260` | block-0 剥离 / context_meta 回填启发式 | RWB-01/04/05 | 🔶 部分借 | Python 端重写启发式 |
| B-13 | `legacy/.../core/kv.ts:100-117`（getPrompt fail-fast）| 取 prompt 缺失即 fail | RWB-02 渲染 fail-loud | 🔶 部分借 | KV→DB+本地文件 |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | prompt 正文存 KV / 仓内硬编码 | Q-RW-3 不用 KV；正文本地文件 + SQLite-SSOT |
| ⛔2 | digest 不一致静默用文件/旧 prompt | 假 SSOT；本 AP 不一致即 fail-loud |
| ⛔3 | 去桩删除规则化逻辑 | 无 fallback 路径违 TR-4/[Q3]；本 AP 规则化留 fallback |
| ⛔4 | mock 响应当真实质量断言 | 假绿（part-cr-8）；本 AP 标 non-delivery-quality |
| ⛔5 | clean handler 复刻 artifact 写入 | 违 F3-02 终态单一归属；handler 只产正文 |
| ⛔6 | structurize 去桩破坏输出契约 | 下游 construct 依赖形状；契约不变 + schema 校验 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：`docs/eval/real-wire/reference-anchor-by-opus.md`（轴 B）—— §7.1 是其与本 AP 相关子集的摘录。**关键诚实发现**（真源 §1.B/§3）：**legacy prompt 正文在 Cloudflare KV、不在 repo**，repo 仅有 key 注册表 + 输出 schema + 用法；故 RWB-01 正文为本地原创（据 schema/用法）。
- **安全 / 信任边界**：本 AP 无密钥/外网（MockLLM）；prompt 渲染的信任边界 = digest 对账（防文件被篡改后静默生效）——威胁模型锚 = ⛔2 + Q-RW-3「hash 对账确认」。无真实 key 落地。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| RWB-T01 | 本地 prompt 正文存在 + 含 schema 要求字段指令 + 变量占位 | 短途 | unit | 🆕 新增 `test_prompt_files.py` | RWB-01 → 正文就位 | `commit + test + run-time` |
| RWB-T02 | 渲染：正例渲染正确；digest 不一致/变量缺失/文件缺失 fail-loud | 短途 | unit·契约 | 🆕 新增 `test_prompt_renderer.py` | RWB-02 → 渲染+对账 fail-loud | `commit + test + run-time` |
| RWB-T03 | seed 后 `get_active_prompt` 返活跃记录；消费侧读 SQLite | 短途 | 集成 | 🆕 新增 `test_prompt_versions_seed.py` | RWB-03 → SSOT 接消费 | `commit + test + run-time` |
| RWB-T04 | structurize：LLM 模式走 MockLLM+schema 校验；fallback 规则化；契约不变 | 短途 | 集成 | 🔱 fork 既有 structurize 测 + LLM 模式断言 | RWB-04 → 去桩+fallback | `commit + test + run-time` |
| RWB-T05 | summary：LLM 模式走 MockLLM；fallback 规则化 | 短途 | 集成 | 🔱 fork 既有 summary 测 | RWB-05 → 去桩+fallback | `commit + test + run-time` |
| RWB-T06 | clean：gemini* LLM 模式走 mock；degraded fallback 仍抛 | 短途 | 集成 | 🔱 fork 既有 clean 测 | RWB-06 → 去桩+fallback | `commit + test + run-time` |
| RWB-T07 | mock capstone A–J：文档→prompt→MockLLM→embed(1024)→search 命中 + 使用链证据 | spike | e2e | 🆕 新增 `tests/e2e/test_real_wire_mock_capstone.py` | RWB-07 → 端到端 mock | `commit + e2e PASS + run-time` |
| RWB-T08 | 防假绿：capstone 断言强度门禁过；mock 标 non-delivery-quality | 短途 | 契约 | ♻️ 沿用 `check_assert_strength.py` | RWB-08 → 不假绿 | `commit + 门禁 0 命中 + run-time` |
| RWB-T09 | 全量回归 | 短途 | 回归 | ♻️ 沿用 全量 pytest | RWB 整体 → 不回归 | `commit + 全量 PASS + run-time` |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| 既有 structurize/summary/clean 测 | 🔱 fork → +LLM 模式断言 | + LLM 模式 + fallback 双路径 | 已存在，PASS |
| `check_assert_strength.py` | ♻️ 沿用 | 0 改动 | 已存在 |
| 全量 pytest（RW-A 后基线）| ♻️ 沿用 | 0 改动 | 纳入回归 |
| F7 `assert_vector_authentic` + RWA-07 `assert_used_real_chain` | ♻️ 沿用 | 0 改动 | capstone 复用 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | 本地 / 每 PR | unit·集成·契约·回归 | 开发中持续 |
| spike | mock capstone（A–J）| e2e | Phase 4 收口 / 本 AP 收口 |
| mega / soak | 本轮 N/A（live 延后）| — | — |

### 8.4 测试缺口

- 不覆盖真实 LLM 语义质量（理由：MockLLM；质量在 live）→ 交 RW-C；**mock 标 non-delivery-quality，不假装覆盖**。
- 不覆盖 prompt 多版本灰度（理由：运营面）→ 平台化轮。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 带四元组；mock 标 non-delivery-quality。
- capstone 必须 `assert_used_real_chain`（spy provider/prompt 真调）+ search 命中断言，不接受「跑完不报错」。
- digest 对账必须有「不一致 fail-loud」反例用例（不只测 happy-path）。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| RW-A 未完成 | 协议/工厂/MockLLM/1024 缺 | high（前置）| blocked 直到 RW-A 收口 |
| digest 假 SSOT | 不一致静默降级 | high | 不一致 fail-loud + 反例用例 |
| 去桩破坏契约 | structurize 输出形状变 | medium | schema 校验 + 契约不变断言 |
| capstone 假绿 | 只验跑完不报错 | medium | spy 真调 + 命中断言 + 门禁 |
| prompt 正文偏离 | 本地原创偏离 legacy 行为 | medium | 据 schema/用法编写；质量在 live 校准 |

### 9.2 约束与前提

- **技术前提**：RW-A 完成（协议/工厂/MockLLM/1024）；Python 3.12。
- **运行时前提**：MockLLM、零外网、零计费（TR-5）。
- **组织协作前提**：无外部 key。
- **上线 / 合并前提**：capstone 绿 + 全量不回归 + 门禁过。

### 9.3 文档同步要求

- 需新增：`prompts/README.md`（编辑→重算 digest→seed→对账流程）。
- 需同步：config 包 README 标注 `get_active_prompt` 已接消费（F6c 孤立消除）。
- 测试说明：capstone 文件登记。

### 9.4 完成后的预期状态

1. prompt 正文存本地文件，SQLite（path+digest）为 SSOT，文件↔DB digest 对账 fail-loud。
2. `get_active_prompt` 接入消费侧，F6c 0-消费方孤立消除。
3. structurize/summary/clean 可走 prompt→render→MockLLM（规则化 fallback 留）。
4. mock capstone 证明「文档→prompt→LLM(mock)→embed(1024)→search 语义命中」使用链真实发生。
5. mock 标 non-delivery-quality——RW-C 可直接把 MockLLM 换真实 provider。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

1. prompt 渲染 + digest 对账 fail-loud（由 `RWB-T02` 证明）。
2. SQLite-SSOT seed + 接消费侧（由 `RWB-T03` 证明）。
3. 三段去桩 LLM 模式 + fallback 双路径（由 `RWB-T04/T05/T06` 证明）。
4. mock capstone A–J 全绿 + 使用链证据（由 `RWB-T07` 证明）。
5. 防假绿门禁 0 命中 + 全量不回归（由 `RWB-T08/T09` 证明）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| prompt 正文就位 | RWB-01 | RWB-T01 | `commit+test+time` | 未观察 |
| 渲染+对账 fail-loud | RWB-02 | RWB-T02 | `commit+test+time` | 未观察 |
| SSOT 接消费 | RWB-03 | RWB-T03 | `commit+test+time` | 未观察 |
| structurize 去桩 | RWB-04 | RWB-T04 | `commit+test+time` | 未观察 |
| summary 去桩 | RWB-05 | RWB-T05 | `commit+test+time` | 未观察 |
| clean 去桩 | RWB-06 | RWB-T06 | `commit+test+time` | 未观察 |
| mock capstone | RWB-07 | RWB-T07 | `commit+e2e+time` | 未观察 |
| 防假绿 | RWB-08 | RWB-T08 | `commit+门禁+time` | 未观察 |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | prompt SSOT 机制 + 三段去桩 + mock capstone 串通 |
| 测试 | §8 全 PASS（capstone + 对账反例 + 双路径）|
| 文档 | prompts/README + config README 同步 |
| 风险收敛 | digest 对账 fail-loud；契约不变；不假绿 |
| 可交付性 | RW-C 可把 MockLLM 换真实 provider |

### 10.4 NOT-成功识别

> 任一退出硬闸 `degraded / 未观察` ⇒ 不得标 `executed`；mock 质量按 non-delivery-quality 如实标注，不 silent overclaim 为「RAG 语义已交付」。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

- **实际执行摘要**：`（待执行回填）`
- **Phase 偏差**：`（待回填）`
- **阻塞与处理**：`（待回填）`
- **测试发现**：`（待回填）`
- **后续 handoff**：`RW-C（真实 provider 替 mock）`
