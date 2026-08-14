# Nano-Agent 行动计划

> 服务业务簇: `MKB / NS1 non-interactive agentic production path`
> 计划对象: `intake → A → [B.md?] → B.json → C → S07 current → vectorize` 的生产接线
> 类型: `upgrade`
> 作者: `Grok`
> 时间: `2026-08-14`
> 文件位置: `docs/plan/new-start/NS1-new-pipeline.md`
> 上游前序 / closure:
> - `docs/eval/new-start/pre-NS1-qna.md` v0.4（`locked / Q1–Q9 frozen / T-O-337..351`）
> 下游交接:
> - NS1 执行日志 / S14·D04 窄回填（catalog 列晋升）/ 修理工 campaign（defer）
> 关联设计 / 调研文档:
> - `docs/eval/new-start/non-interactive-agentic-pipeline.md`
> - `docs/eval/new-start/agent-in-the-loop-repair.md`
> - `docs/eval/new-start/proposed-workflow-imagined.md`
> 冻结决策来源:
> - `docs/eval/new-start/pre-NS1-qna.md`（只读引用；本 action-plan 不填写 Q/A）
> grounding 来源:
> - pre-NS1-qna §2 证据审查 + 本 AP §7 内置锚区
> 关联 reference-anchor:
> - 见 §7 内置锚区
> 文档状态: `executed`

---

## 0. 执行背景与目标

v1 围栏（S03/S04/D08/S08–S10）已可跑，但 **B 的模型输出不进 current**：`_structurize` 只记账，权威树是 `LsragContractCompiler.structurize(clean_text)` 的全文复制 + 断句。生产 Prompt 正文仍是 stub。NS1 QNA 已冻：`layered_content.v1` 为 B.json 交卷；kernel 验收后才 CAS；四角色 catalog 以 `prompt_id` 入口；C 只吃验收后 JSON；markdown 可跳、json 不可跳。

本计划把这些冻结句落成可合并代码与可复验测试，不重开产品问答。

- **服务业务簇**：`NS1`
- **计划对象**：catalog + kernel + CLI 工人 + 可选 B.md 跳 + Task API `prompt_id`
- **本次计划解决的问题**：
  - 假分层（g0=g1=全文，g2=句子）退出生产 current
  - stub prompt / 无 `layered_content` schema / 无 `prompt_id` 入口
  - 法律线缺少可跳过的 markdown 跳，C 未整包消费 B.json
- **本次计划的直接产出**：
  - `data/schemas/lsrag.layered_content.v1.json` + 迁入的 A / B.md / B.json / C 正文
  - `adopt_layered_json` kernel + `claude -p` 运输（可 stub）
  - catalog CRUD（内部）+ ingest 四字段 `*_prompt_id`
  - 图上可选 `lsrag.transcribe_markdown`；默认不因结构失败开门审
- **本计划不重新讨论的设计结论**：
  - B.json 交卷 = `layered_content.v1`；compiler 编树退出生产（`T-O-343`）
  - 粒度闭集挂 **json** 行；缺层失败不合成（`T-O-344`/`T-O-351`）
  - 失败显式、不人审恢复、sibling 跑完、root 仍 fail-closed（`T-O-341`/`T-O-345`）
  - API 只收 `prompt_id`；DB 无正文；`H(file)==hash`（`T-O-348`/`T-O-349`）
  - 四角色与 `A → [B.md?] → B.json → C`（`T-O-350`）
  - C 吃验收后 layered；S07 投影仍是 construction SSOT（`T-O-347`）
  - 锚定 = NFC/LF 精确子串 + 首次命中（`T-O-346`）
  - 修理工 / 官方 Anthropic 切换 **不在本 AP**（QNA defer）

---

## 1. 执行综述

### 1.1 总体执行方式

**先协议与资产，再 kernel，再运输，再 API/图，最后 mega 收口。** 不先铺 CLI 封装却继续用句子树。每 Phase 先 stub/单测再接线。确定性 clean 与 registered_api parser 全程不经 Claude。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | 契约资产与 catalog | `M` | schema、四角色正文、指针表窄晋升、内部 CRUD、bootstrap | `-` |
| Phase 2 | Kernel 验收 | `L` | `adopt_layered_json` 成为 structure current；假树退出生产 | Phase 1 |
| Phase 3 | CLI 工人与四跳 | `L` | `claude -p` 跑 A / B.md / B.json / C；hash 门闩；可 stub | Phase 2 |
| Phase 4 | API 与 Workflow | `M` | ingest `*_prompt_id`；markdown 可跳；默认 auto_admitted | Phase 1+3 |
| Phase 5 | 分层测试与收口 | `M` | unit / domain / e2e 全绿；mega 金样；文档回填 | Phase 2–4 |

### 1.3 Phase 说明

1. **Phase 1 — 契约资产与 catalog**
   - **核心目标**：没有 schema 与 `prompt_id` 行，后面所有 handler 无法编码。
   - **为什么先做**：`T-O-343/348/350` 的物理落点。
2. **Phase 2 — Kernel 验收**
   - **核心目标**：换 current 权威，不依赖真模型。
   - **为什么放在这里**：Q1 主轴；可用金样 JSON 单测。
3. **Phase 3 — CLI 工人与四跳**
   - **核心目标**：system / `-p` / schema 通道；B.md 可跳。
   - **为什么放在这里**：kernel 已能验收，运输可 stub。
4. **Phase 4 — API 与 Workflow**
   - **核心目标**：caller 只传 `prompt_id`；图表达可选 markdown。
   - **为什么放在这里**：catalog 与工人已在。
5. **Phase 5 — 分层测试与收口**
   - **核心目标**：unit / domain / e2e + mega；防假绿。
   - **为什么放在这里**：接线完成后才有完整旅程。

### 1.4 执行策略说明

- **执行顺序原则**：资产 → 纯函数 kernel → 可注入 CLI → 边界 API → 旅程测试。禁止倒序。
- **风险控制原则**：CLI 必须可 stub；CI 默认不打 MiniMax。DDL 只晋升既有 `mkb_prompt_hash_pointers` 列，不新建 required 表（服从 `T-O-337`）。
- **测试推进原则**：短途（每 PR unit/domain）→ Phase spike → AP 收口 mega → hash/路径 soak。
- **文档同步原则**：不改 QNA。S14/D04 仅在 Phase 5 写「窄回填」附录，不重写 handbook 产品句。
- **回滚 / 降级原则**：feature 以 catalog 缺省 + 旧 workflow revision 隔离。禁止「失败则退回 compiler 假树」——那是 silent fallback（`T-O-340`）。回滚 = 不部署新 WorkflowRevision，不是运行时降级。

### 1.5 本次 action-plan 影响结构图

```text
NS1-new-pipeline
├── Phase 1: 契约资产与 catalog
│   ├── data/prompts/** + data/schemas/lsrag.layered_content.v1.json
│   ├── mkb_prompt_hash_pointers 列晋升 + 内部 /prompts CRUD
│   └── S14 bootstrap / contracts/intake 或 contracts/prompt
├── Phase 2: Kernel 验收
│   ├── src/services/lsrag_compiler.py adopt_layered_json
│   └── generation_construct._structurize 不再 compiler.structurize(clean_text)
├── Phase 3: CLI 工人与四跳
│   ├── ClaudeCliPort（--bare --system-prompt-file --json-schema）
│   ├── clean llm / transcribe_markdown / structurize / construct
│   └── hash 校验 + invocation 账
├── Phase 4: API 与 Workflow
│   ├── IntakeIngestPayload *_prompt_id
│   ├── lsrag.transcribe_markdown 可选步
│   └── 默认 auto_admitted
└── Phase 5: 测试与收口
    ├── tests/unit + tests/domain + tests/e2e
    └── mega：legal(有 md) / generic(无 md) / 失败隔离
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `layered_content.v1` JSON Schema 与金样
- **[S2]** 迁入并登记四角色 prompt 正文；退役 `semantic_block` 作为交卷形
- **[S3]** catalog：`prompt_id`(=`prompt_key`) + role + status + json 行 `granularity_set`；内部 CRUD；运行时 hash 门闩
- **[S4]** `adopt_layered_json`；假树退出生产 current
- **[S5]** `claude -p` 运输（可 stub）：A、B.md、B.json、C
- **[S6]** 可选 markdown 跳；json 不可跳；C 整包只填 summary
- **[S7]** ingest 四 `*_prompt_id`；禁止 `prompt_ref`/路径
- **[S8]** 结构失败不置 `require_human_review`；生产默认 auto_admitted
- **[S9]** unit / domain / e2e / mega 测试台账

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** `lsrag.structure_repair` / `grok -p` 修理工（QNA defer）
- **[O2]** 重开 S03 八态、S04 接受事务、D08 parser、S08–S10 算法
- **[O3]** 新建 required 物理表；DB 存 prompt 正文
- **[O4]** scatter 部分成功（`T-O-345` 不 reopen `T-O-53`）
- **[O5]** legal.case 分析通道、agy、切官方 Anthropic
- **[O6]** 公网 marketplace / agent 写 catalog

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| `mkb_prompt_hash_pointers` 加列 | `in-scope` | 既有表晋升，非第 56 张 required 表 | 若 owner 禁任何 DDL → 退回 code-owned role 图（弱于 `T-O-351`） |
| `claude -p` 真机 | `defer` CI / `in-scope` 可选手动 | `T-O-342`：实测只证明运输 | 有 MiniMax 的 night job |
| 修理工 | `out-of-scope` | QNA 11.4 defer | 新 campaign |
| human_review 节点删除 | `out-of-scope` | 留 historical 图 | 另开 S05 图清理 |
| S14/D05 正文回填 | `in-scope` 附录级 | 不改产品句，只记窄解释 | formal reopen 另档 |

---

## 3. 业务工作总表

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| P1-01 | Phase 1 | 冻结 `layered_content.v1` schema + 金样 | `add` | 🆕 `data/schemas/lsrag.layered_content.v1.json`；锚 A-12 Zod | schema 校验金样；禁 span 字段 | NS1-T01 | `low` |
| P1-02 | Phase 1 | 迁入四角色 prompt 正文 | `add` | 🆕 `data/prompts/{clean,markdown,json,summarizer}/**`；A-20..A-27 | git 正文可 hash；B.json 无 semantic_understanding | NS1-T02 | `medium` |
| P1-03 | Phase 1 | 指针表窄晋升 + 角色列 | `update` | `001_initial.sql:785-795`；🆕 migration | 列齐：role/status/granularity_set | NS1-T03 | `high` |
| P1-04 | Phase 1 | bootstrap 默认 catalog 行 | `update` | `registry.py:26-32,169-193` | 四 role 各有 default；json 行有闭集 | NS1-T04 | `medium` |
| P1-05 | Phase 1 | 内部 catalog CRUD | `add` | 🆕 `api/internal/prompts.py`；`api/internal/routes.py:13` | 内部 token；Update=新 version | NS1-T05 NS1-T06 | `high` |
| P1-06 | Phase 1 | `resolve_prompt(prompt_id)` + hash 门闩 | `add` | `registry.py:498-523`；`clean_preflight.py:119-170` | `H(file)==hash` 失败 fail-closed | NS1-T07 | `high` |
| P2-01 | Phase 2 | `adopt_layered_json` | `add` | `lsrag_compiler.py:243-317` | 金样→structure+projection；假树不进生产 | NS1-T10 NS1-T11 | `high` |
| P2-02 | Phase 2 | `_structurize` 改走 adopt | `update` | `generation_construct.py:298-330` | live/离线都不再 `structurize(clean_text)` 当 current | NS1-T12 | `high` |
| P2-03 | Phase 2 | C 映射：layered summary → units | `update` | `generation_construct.py:472-500` | 整包 summary map；禁按句循环 | NS1-T13 | `medium` |
| P3-01 | Phase 3 | `ClaudeCliPort` + stub | `add` | 🆕 `src/runtime/inference/claude_cli.py` | argv 合同；测试可注入 | NS1-T20 | `high` |
| P3-02 | Phase 3 | A 走 CLI（仅 llm strategy） | `update` | `clean_preflight.py:27-87`；`strategies.py:56-65` | 确定性/API 不经 CLI | NS1-T21 | `medium` |
| P3-03 | Phase 3 | B.md 工人 | `add` | 🆕 transcribe handler；`core.py:281-306` | 只出 markdown；无 schema | NS1-T22 | `medium` |
| P3-04 | Phase 3 | B.json 工人 | `update` | `generation_construct.py:311-322` | `--json-schema`；读 `structured_output` | NS1-T23 | `high` |
| P3-05 | Phase 3 | C 工人整包 | `update` | `generation_live.py:419-448` | 一次 JSON；不改 original | NS1-T24 | `high` |
| P4-01 | Phase 4 | ingest `*_prompt_id` | `update` | `api/models.py:175-178` | extra=forbid；禁 prompt_ref/path | NS1-T30 NS1-T31 | `high` |
| P4-02 | Phase 4 | 图：可选 markdown 跳 | `update` | `lsrag_definition.py:84-202` | 无 markdown_id 则跳过 | NS1-T32 | `high` |
| P4-03 | Phase 4 | 默认 auto_admitted | `update` | `clean_preflight.py:491-496` | B 失败不开门 | NS1-T33 | `medium` |
| P4-04 | Phase 4 | materialize 冻 hash | `update` | `generation_live.py:60+`；command digest | 重试不热切 catalog | NS1-T34 | `high` |
| P5-01 | Phase 5 | domain 守卫 | `update` | `tests/domain/test_architecture.py` | 无 runtime 编树；无 DB body | NS1-T40 | `medium` |
| P5-02 | Phase 5 | e2e 金样旅程 | `add` | 🆕 `tests/e2e/test_ns1_pipeline.py` | 有/无 md 两条绿 | NS1-T41 NS1-T42 | `high` |
| P5-03 | Phase 5 | 失败隔离 e2e | `add` | 同上 / scatter 既有 | sibling 跑完；root fail-closed | NS1-T43 | `medium` |
| P5-04 | Phase 5 | 文档窄回填 | `update` | S14/D04 附录级 | 记列晋升与四 role | — | `low` |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — 契约资产与 catalog

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|------------------------------|----------|----------|----------|
| P1-01 | schema | a) 从 Zod `LayeredContentBlockSchema`/`StructuredJsonOutputSchema` 抽出 JSON Schema。b) `additionalProperties:false`；**无** span 字段。c) B.json 模式：`llm_summary` 可 null；C 模式同一 schema 但 summary.body required。d) 金样：generic 0/1/2、legal 0/1、realestate 仅 0。e) 非法：缺 g=0、多未声明层、含 span。 | 🆕 `data/schemas/lsrag.layered_content.v1.json`；A-12 `schemas_common.ts:116-154` | 文件 + 金样夹具 | NS1-T01 | schema 单测绿 |
| P1-02 | prompt 正文 | a) 从 `context/legacy-prompt` **改写迁入**（非原样）：A 去 HTML 抽取纪律；B.md 合并 legal markdown 规则、去掉「案情分析进 original」；B.json 出 `layered_content`、**删除** `semantic_understanding`、summary 槽 null；C 只填 summary。b) 路径 `data/prompts/{clean,markdown,json,summarizer}/<name>.v1.md`。c) 房产去噪能前移 A 的不留在 B.json。 | 🆕 上述 md；A-20..A-27 | 四 role 至少各一份可 hash 正文 | NS1-T02 | hash 稳定；B.json 无摘要权威 |
| P1-03 | DDL 窄晋升 | a) 新 migration：`mkb_prompt_hash_pointers` 增加 `prompt_id`（与现 `prompt_key` 对齐或生成稳定 id）、`role TEXT CHECK IN (clean,markdown,json,summarizer)`、`status CHECK IN (active,retired)`、`granularity_set TEXT`（json 行 NOT NULL JSON 数组）。b) **不**新建 required 表。c) 旧三行 stub 迁移为 clean/json/summarizer default。 | `001_initial.sql:785-795`；🆕 `00N_ns1_prompt_catalog.sql` | migrate 可逆说明写在 migration 头 | NS1-T03 | 空库 bootstrap 后列齐 |
| P1-04 | bootstrap | a) `DEFAULT_PROMPTS` 改为带 role/granularity/default 旗。b) json default `{0,1,2}`；另登记 `json.legal` `{0,1}`、`json.realestate` `{0}`。c) markdown default **不**自动绑到 ingest（有 id 才跑）。d) 冲突 hash → `REGISTRY_DIGEST_MISMATCH`。 | `registry.py:26-32,169-193` | 四 role default 行 | NS1-T04 | 与磁盘 hash 一致 |
| P1-05 | CRUD | a) `POST/GET/PATCH/DELETE /internal/prompts`。b) POST 登记 path+算 hash；PATCH=新 version 行；DELETE=`retired`。c) 拒绝绝对路径、`..`、写 body。d) `require_operator_token`。e) 禁 agent。 | 🆕 routes；`routes.py:13` | 内部 API | NS1-T05 NS1-T06 | 安全用例过 |
| P1-06 | resolve | a) `resolve_prompt(prompt_id)` → 最新 active version（除非 command 冻了 version）。b) 读盘、相对 `data/prompts`、`H==hash`。c) json 行缺 `granularity_set` → 配置失败。 | `registry.py`；`clean_preflight.py:119-170` | 统一解析口 | NS1-T07 | mismatch 503/配置失败 |

### 4.2 Phase 2 — Kernel 验收

| 编号 | 工作项 | 工作内容 | 涉及文件 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|----------|----------|----------|----------|
| P2-01 | adopt | a) 规范化 clean 与各 body（UTF-8/LF/NFC）。b) schema 校验。c) 按 json 行 `granularity_set` 检查层集合。d) 保证一块 g=0；空 body → 回填全文 span。e) g≥1：精确子串、首次命中、`occurrence_count`。f) 找不到 → `STRUCTURE_ANCHOR_MISSING`。g) B 阶段 summary 非空 → 失败。h) 投影：一块 layered → 一个 RetrievalBlock，**不按句切**。i) `structurize(clean_text)` 标 fixture-only。 | `lsrag_compiler.py:243-317` | 纯函数 API | NS1-T10 NS1-T11 | 金样过；句子树测必须 fail 若当生产 |
| P2-02 | 接线 structurize | a) 输入改为 adopt(clean, candidate_json)。b) 无 candidate 不得编树。c) 删「live 调用后仍 compiler.structurize」路径。 | `generation_construct.py:298-330` | current 来自 adopt | NS1-T12 | 源码扫描无生产调用旧入口 |
| P2-03 | construct 映射 | a) 用 C 回填后的 layered 按 `block_id` 取 `llm_summary.body`。b) 改 original/granularity/block_id → `CONSTRUCT_KERNEL_*`。c) 删 `_live_summaries` 按 projection 句子循环。 | `generation_construct.py:472-500`；`generation_live.py:419-448` | 整包 dual-channel | NS1-T13 | 无 per-sentence generate |

### 4.3 Phase 3 — CLI 工人与四跳

| 编号 | 工作项 | 工作内容 | 涉及文件 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|----------|----------|----------|----------|
| P3-01 | ClaudeCliPort | a) `--bare --system-prompt-file --tools ""`。b) B.json/C 加 `--output-format json --json-schema`。c) 解析 `structured_output` 优先于 `result` 字符串。d) Protocol + RecordingStub。e) argv 不含 secret；记 session/usage/exit。f) 非 0 / 空 / `is_error` → 运输错误（S03 retryable 仅闭集码）。 | 🆕 `claude_cli.py` | 可注入端口 | NS1-T20 | stub 断言 argv |
| P3-02 | A | llm strategy：`-p`=解码 HTML/文本；system=clean prompt 文件。确定性/API **不**调 port。 | `clean_preflight.py:27-87` | 分流正确 | NS1-T21 | API scatter 无 CLI |
| P3-03 | B.md | 新 `lsrag.transcribe_markdown`：system=markdown 正文；`-p`=clean；stdout 当 markdown 字节；无 schema。失败显式。 | 🆕 handler；`core.py` dispatch | 可选跳 | NS1-T22 | 无 id 不调用 |
| P3-04 | B.json | `-p`=markdown 或 clean（视上游）；schema=layered v1；adopt。 | `_structurize` | 不可跳 | NS1-T23 | 缺 json_prompt_id 在 API 层 422 |
| P3-05 | C | `-p`=回填后 layered；只填 summary；adopt 后的 block 对齐。 | `_construct` | 整包一次 | NS1-T24 | original 字节不变 |

### 4.4 Phase 4 — API 与 Workflow

| 编号 | 工作项 | 工作内容 | 涉及文件 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|----------|----------|----------|----------|
| P4-01 | payload | `IntakeIngestPayload` 增加：`json_prompt_id` required；`markdown_prompt_id`/`clean_prompt_id`/`summarizer_prompt_id` optional。拒绝 `prompt_ref`、`git_relative_path`、绝对路径。角色不匹配 422。 | `api/models.py:175-178` | 严格模型 | NS1-T30 NS1-T31 | extra=forbid |
| P4-02 | 图 | accept 后：若有 markdown_id → transcribe → structurize；否则 structurize。structurize 失败 → failed，不进 human_review。 | `lsrag_definition.py:149-167` | 可跳过步 | NS1-T32 | 两条路由测过 |
| P4-03 | 准入 | 去掉「B 失败 → human_review_required」。`require_human_review` 仅调用方显式、且不因 schema 失败置位。 | `clean_preflight.py:488-496` | 默认 auto | NS1-T33 | 结构失败 Task=failed |
| P4-04 | 冻结 | materialize 写入四跳解析后的 `{prompt_id,version,hash,path}` 进 command_input_digest。retry 同 digest。 | generation_live / workflow materialize | 不热切 | NS1-T34 | CRUD 新版本不影响 in-flight |

### 4.5 Phase 5 — 测试与收口

| 编号 | 工作项 | 工作内容 | 涉及文件 | 预期结果 | 测试映射 | 收口标准 |
|------|--------|----------|----------|----------|----------|----------|
| P5-01 | domain | 扫描：生产路径无 `structurize(clean_text)`；无 `body_text` 列；无 caller `prompt_ref`。 | `tests/domain/test_architecture.py` | 守卫 | NS1-T40 | 扫描绿 |
| P5-02 | e2e | stub CLI：无 md generic；有 md legal。断言投影不是 g0=g1=全文。 | 🆕 `test_ns1_pipeline.py` | 旅程 | NS1-T41 NS1-T42 | 2 旅程绿 |
| P5-03 | 隔离 | 一 child adopt 失败，另一成功跑完；root failed。 | e2e scatter fork | `T-O-345` | NS1-T43 | 计数正确 |
| P5-04 | 文档 | S14/D04 附录：列晋升、四 role、内部 CRUD 窄解释。不改 QNA。 | domain-truth 附录 | 可追溯 | — | 附录存在 |

---

## 5. Phase 详情

### 5.1 Phase 1 — 契约资产与 catalog

- **Phase 目标**：schema、正文、指针目录可独立测试。
- **本 Phase 对应编号**：`P1-01` … `P1-06`
- **本 Phase 新增文件**：`data/schemas/lsrag.layered_content.v1.json`；`data/prompts/{clean,markdown,json,summarizer}/*.md`；`src/persistence/migrations/00N_ns1_prompt_catalog.sql`；`src/contracts/prompt/catalog.py`；`api/internal/prompts.py`；`tests/unit/test_ns1_catalog.py`；`tests/unit/test_layered_schema.py`
- **本 Phase 修改文件**：`registry.py:26-32,169-193`；`api/internal/routes.py:13`；`src/contracts/api` 仅 CRUD 模型
- **具体功能预期**：
  1. Schema 拒 span、拒缺 g=0。
  2. B.json 正文不含 `semantic_understanding`。
  3. json 行无 `granularity_set` 不能 bootstrap。
  4. CRUD PATCH 不覆盖旧 version。
  5. `..` / 绝对路径 / body 字段 → 422。
  6. hash 篡改磁盘 → resolve 失败。
- **对应测试台账项**：`NS1-T01`–`T07`
- **收口标准**：空库 migrate+bootstrap；CRUD 往返；hash 门闩。
- **本 Phase 风险提醒**：DDL 与 `T-O-337`；列晋升须在 migration 头写明「非新表」。

### 5.2 Phase 2 — Kernel 验收

- **Phase 目标**：structure current = adopt(clean, layered)。
- **对应编号**：`P2-01`–`P2-03`
- **新增**：`tests/unit/test_adopt_layered_json.py`；金样 `tests/fixtures/ns1/`
- **修改**：`lsrag_compiler.py:243-317`；`generation_construct.py:298-330,472-500`
- **具体功能预期**：
  1. legal 金样 `{0,1}` 过；多一块 g=2 失败。
  2. g=0 空 body 回填后 digest=clean。
  3. 改一字的 body → `STRUCTURE_ANCHOR_MISSING`。
  4. 重复套话首次命中，`occurrence_count>=2`。
  5. 生产 `_structurize` 不再调用旧编树。
  6. construct 按 block_id 填 summary，block 数=layered 块数。
- **测试**：`NS1-T10`–`T13`
- **收口标准**：unit 全绿；架构扫描无生产旧入口。
- **风险**：漏改 metadata_refresh 里的 `compiler.structurize`（`generation_construct.py:76`）——refresh 必须 adopt 源 structure 字节，不得再编树。

### 5.3 Phase 3 — CLI 工人与四跳

- **Phase 目标**：四跳可 stub 跑通通道合同。
- **对应编号**：`P3-01`–`P3-05`
- **新增**：`src/runtime/inference/claude_cli.py`；`src/runtime/intake/transcribe_markdown.py`
- **修改**：`clean_preflight.py`；`core.py` dispatch；`generation_construct.py`；`generation_live.py`；`strategies.py` 仍只给 llm 绑 clean role
- **具体功能预期**：
  1. stub 记录 `--system-prompt-file` 为 resolve 后的相对路径。
  2. B.json argv 含 `--json-schema`；A/B.md 不含。
  3. 有 markdown 时 B.json 的 user 物料 digest=markdown；无则=clean。
  4. C user digest=验收后 layered（含 g=0 回填）。
  5. registered_api scatter 0 次 CLI。
  6. CLI 非 0 不写成 structure current。
- **测试**：`NS1-T20`–`T24`
- **收口标准**：注入 stub 的 unit + 一条单文件 spike。
- **风险**：把 MiniMax 写进 CI。

### 5.4 Phase 4 — API 与 Workflow

- **Phase 目标**：调用面与图表达 `T-O-350`。
- **对应编号**：`P4-01`–`P4-04`
- **修改**：`api/models.py:101-178`；`lsrag_definition.py` 及 `BUILTIN_SOURCE_PROFILE_WORKFLOWS` 副本；`builtin_scatter.py` child 图同样加可选 markdown；`clean_preflight.py:488-496`
- **具体功能预期**：
  1. 缺 `json_prompt_id` → 422。
  2. 提交 `prompt_ref` 或 path → 422。
  3. markdown_id 角色不是 `markdown` → 422。
  4. 无 markdown_id 的 execution 不出现 transcribe Process。
  5. 结构失败 Task=`failed`，无 open gate。
  6. in-flight 中 CRUD 新版本，retry 仍用旧 hash。
- **测试**：`NS1-T30`–`T34`
- **收口标准**：契约 + e2e 路由。
- **风险**：历史 workflow revision 兼容（只影响新 revision）。

### 5.5 Phase 5 — 测试与收口

- **Phase 目标**：三层覆盖 + mega + 文档。
- **对应编号**：`P5-01`–`P5-04`
- **新增**：`tests/e2e/test_ns1_pipeline.py`；`tests/domain/test_ns1_guards.py`
- **修改**：`test_architecture.py`；`test_generation_pipeline_contracts.py`（断言不再要求句子 g2）
- **具体功能预期**：见 §8。
- **测试**：`NS1-T40`–`T43` + 回归沿用
- **收口标准**：§10 硬闸。
- **风险**：旧 e2e 仍假设 g2 句子——必须改断言而非改回假树。

---

## 6. 依赖的冻结设计决策（只读引用）

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `T-O-337` | `pre-NS1-qna.md` | 不改 S03/S04/D08/S08–S10；不加第 56 表 | 停工 |
| `T-O-338` | 同上 | CLI 三通道；schema 只绑 B.json | 停工 |
| `T-O-339` | 同上 | 正文 git；无第四生产字母 | 与 `T-O-350` 并存：四 role 是 B 拆跳 |
| `T-O-340` | 同上 | 无运行时退回假树 | 禁止「降级 compiler」 |
| `T-O-341` `T-O-345` | 同上 | 失败面与 fan-in | 不做人审、不做部分成功 |
| `T-O-343` `T-O-346` | Q1/Q4 | adopt + 子串锚定 | Phase 2 无替代 |
| `T-O-344` `T-O-351` | Q2/Q9 | 闭集在 json 行 | P1-03 列 / 行约束 |
| `T-O-347` | Q5 | C 物料 | P3-05 |
| `T-O-348` `T-O-349` | Q6/Q7 | prompt_id + CRUD 版本 | P1-05 P4-01 |
| `T-O-350` | Q8 扩充 | 四角色两跳 B | P3-03 P4-02 |
| `T-O-42` `T-O-264` `T-O-269` | baseline | 零 legacy runtime；hash 门闩；不热切 | 安全测试 |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表

| 锚 ID | `path:line` | 落点 | 本 AP 用途 | 处置 | 备注 |
|-------|-------------|------|------------|------|------|
| A-1 | `src/runtime/intake/generation_construct.py:298-330` | `_structurize` live 后仍 compiler 编树 | P2-02 替换权威 | `♻️ 重 substrate` | 删 live-then-ignore |
| A-2 | `src/services/lsrag_compiler.py:243-317` | `structurize(clean_text)` 全文+断句 | P2-01 adopt；旧入口 fixture | `♻️ 重 substrate` | `_project_blocks` 299-317 勿当生产 |
| A-3 | `src/runtime/intake/generation_construct.py:472-500` | construct 用 summaries_by_block | P2-03 整包 map | `✅ 复用` | 换 summary 来源 |
| A-4 | `src/runtime/intake/generation_live.py:419-448` | `_live_summaries` 按 block 循环 | P3-05 删除循环 | `♻️ 重 substrate` | 违反整包 |
| A-5 | `src/runtime/intake/core.py:281-306` | process_key dispatch | P3-03 注册 transcribe | `✅ 复用` | |
| A-6 | `src/runtime/intake/clean_preflight.py:27-170` | clean + CleanPrompt hash | P3-02 / P1-06 | `✅ 复用` | llm 才 CLI |
| A-7 | `src/runtime/intake/clean_preflight.py:488-496` | admission / human_review | P4-03 | `✅ 复用` | |
| A-8 | `src/workflows/lsrag_definition.py:84-202` | 主图 | P4-02 | `✅ 复用` | 加可选步 |
| A-9 | `src/services/registry.py:26-32,169-193` | DEFAULT_PROMPTS bootstrap | P1-04 | `✅ 复用` | |
| A-10 | `src/persistence/migrations/001_initial.sql:785-795` | hash 指针表 | P1-03 加列 | `✅ 复用` | 不加新表 |
| A-11 | `src/contracts/api/models.py:175-178` | IntakeIngestPayload | P4-01 | `✅ 复用` | |
| A-12 | `legacy-family/.../schemas_common.ts:116-154` | Zod layered | P1-01 抽出 | 读不改 | 去 catchall/knowledge_tree |
| A-13 | `legacy-family/.../structurizer.ts:177-257` | designated_prompt + 整文 user + preprocess | P3-04 对照 | 读不改 | **禁** preprocess coerce |
| A-14 | `legacy-family/.../summarizer.ts:192-234` | 整包 JSON、剥 g=0 | P3-05 | 读不改 | 禁 silent 回填 context_meta |
| A-15 | `legacy-family/.../constructor.ts:92-140` | 缺 prompt fail-fast | P1-06 | `✅ 复用` 纪律 | |
| A-16 | `legacy-family/.../cleaner_web.ts:256-266` | WEB_CONTENT_CLEANUP + HTML user | P3-02 | 读不改 | |
| A-17 | `legacy-family/.../kv.ts:41-54` | 别名→KV | 不迁 KV | ⛔ | 用 catalog |
| A-18 | `src/contracts/intake/strategies.py:56-65` | llm→promptA.default | P3-02 改绑 clean role | `✅ 复用` | |
| A-19 | `src/runtime/workflow/runtime_scatter.py:276-428` | collect-all fan-in | 不改 | `✅ 复用` | `T-O-345` |
| A-20 | `context/legacy-prompt/promptA.clean.v1.md` | HTML 清洗 | P1-02 clean | `♻️` 改写迁入 | |
| A-21 | `promptB.markdown.legal.general.md` | 通知转录 | P1-02 markdown | `♻️` | |
| A-22 | `promptB.markdown.legal.clause.md` | 法条面包屑 | P1-02 markdown | `♻️` | |
| A-23 | `promptB.markdown.legal.qna.md` | 问答 | P1-02 markdown | `♻️` | |
| A-24 | `promptB.markdown.legal.case.md` | 案情；分析是生成 | P1-02 **不**把分析写入 original | 读 + 裁 | |
| A-25 | `promptB.json.structurizer.md` | semantic_block + B 内摘要 | **退役交卷形** | ⛔ 形状 | 切法可参考 |
| A-26 | `promptB.json.realestate.md` | 仅 g=0 layered | P1-02 `json.realestate` | `♻️` | 去噪尽量前移 A |
| A-27 | `promptC.constructor.md` | 整包填 llm_summary | P1-02 summarizer | `♻️` | |
| A-28 | `tests/unit/test_prompt_hash_mismatch.py` | hash 门闩 | P1-06 fork | `🔱` | |
| A-29 | `tests/e2e/test_generation_pipeline_contracts.py` | generation 契约 | P5 改断言 | `🔱` | 去掉句子 g2 假设 |
| A-30 | `tests/e2e/test_human_review_gate.py` | 显式 require 才开门 | P4-03 沿用 | `♻️` | |
| A-31 | `tests/domain/test_architecture.py` | D03 守卫 | P5-01 | `✅` | |
| A-32 | `api/internal/routes.py:13` | 内部 token 路由 | P1-05 | `✅` | |
| A-33 | `src/services/config_snapshots.py:525` | 读指针进 snapshot | P4-04 | `✅` | 冻 hash |

### 7.2 反例 ledger ⛔

| ⛔ | 反例 / 陷阱 | 为什么 |
|----|------------|--------|
| ⛔1 | 生产再调 `structurize(clean_text)` | `T-O-343` |
| ⛔2 | 按句合成缺层 | `T-O-344` |
| ⛔3 | caller `prompt_ref` / 路径 / KV key | `T-O-348` |
| ⛔4 | CRUD 写 body 或原地改 hash | `T-O-349` `T-O-274` |
| ⛔5 | 结构失败开 human gate | `T-O-341` |
| ⛔6 | 失败退回假树 | `T-O-340` |
| ⛔7 | C 吃 markdown 或未验收 JSON | `T-O-347` `T-O-350` |
| ⛔8 | 跳过 B.json | `T-O-350` |
| ⛔9 | Zod preprocess 补字段 / 清空 UUID 当成功 | LF-S06-06 |
| ⛔10 | summarizer 缺 context_meta 回填冒充成功 | summarizer.ts ~254-275 |
| ⛔11 | `designated_prompt` catchall | LF-S06-07 |
| ⛔12 | DB `body_text` / 公网 marketplace | S14 / G-12 |
| ⛔13 | agent 调 catalog CRUD | `T-O-270` `T-O-349` |
| ⛔14 | 路径 `..` 逃出 `data/prompts` | S16 / P1-05 |

### 7.3 上游真源指针 + 安全项威胁模型

- **QNA 真源**：`docs/eval/new-start/pre-NS1-qna.md` §1 `T-O-337..351`
- **S14/S16**：`T-O-264/269/270/274`；内部 token + 网络围栏（`api/internal/routes.py:10-13`）
- **威胁模型（P1-05/P1-06，不得空）**：
  1. 路径穿越读 `/etc/passwd` → 相对路径 + `relative_to(prompt_root)`。
  2. CRUD 写正文当第二 SSOT → schema 禁 `body`。
  3. 用旧 hash 调换磁盘 → resolve fail-closed。
  4. 外部调用 CRUD → 无 operator token / 非内网拒绝。
  5. 模型/agent 写 catalog → 无绑定；测试断言无 LLM 角色可调。

---

## 8. 测试台账

### 8.1 测试清单（主表）

| Test-ID | 测试项 | 类型 | 层 | 来源 | 映射 | PASS 证据（四元组） |
|---------|--------|------|----|------|------|---------------------|
| NS1-T01 | layered schema 金样/拒 span/缺 g=0 | 短途 | unit | 🆕 `tests/unit/test_layered_schema.py` | P1-01 → schema 冻 | commit + test + run-time |
| NS1-T02 | 迁入正文 hash；B.json 无 semantic_understanding | 短途 | unit | 🆕 `tests/unit/test_ns1_prompt_bodies.py` | P1-02 | commit + test + run-time |
| NS1-T03 | migration 列与 check | 短途 | 集成 | 🆕 `tests/unit/test_ns1_catalog_ddl.py` | P1-03 | commit + test + run-time |
| NS1-T04 | bootstrap 四 role + json 闭集 | 短途 | unit | 🔱 `registry` bootstrap 测 | P1-04 | commit + test + run-time |
| NS1-T05 | CRUD 新 version、不覆盖 | 短途 | unit | 🆕 `tests/unit/test_ns1_catalog_crud.py` | P1-05 | commit + test + run-time |
| NS1-T06 | CRUD 拒 path/body/无 token | 短途 | unit | 同上（攻击向量） | P1-05 → §7.3 | commit + test + run-time |
| NS1-T07 | 磁盘 hash 漂移 fail-closed | 短途 | unit | 🔱 `test_prompt_hash_mismatch.py` | P1-06 | commit + test + run-time |
| NS1-T10 | adopt：legal/generic/realestate 金样 | 短途 | unit | 🆕 `tests/unit/test_adopt_layered_json.py` | P2-01 | commit + test + run-time |
| NS1-T11 | adopt：锚定失败、回填 g=0、occurrence | 短途 | unit | 同上 | P2-01 | commit + test + run-time |
| NS1-T12 | 生产无 `structurize(clean_text)` | 短途 | domain | 🆕 `tests/domain/test_ns1_guards.py` | P2-02 P5-01 | commit + test + run-time |
| NS1-T13 | construct 不改 original；整包块数 | 短途 | unit | 🆕 `tests/unit/test_ns1_construct_map.py` | P2-03 | commit + test + run-time |
| NS1-T20 | CLI argv 合同（file/schema/tools） | 短途 | unit | 🆕 `tests/unit/test_claude_cli_port.py` | P3-01 | commit + test + run-time |
| NS1-T21 | 仅 llm clean 调 CLI；API 不调 | 短途 | unit | 🆕 `tests/unit/test_ns1_clean_dispatch.py` | P3-02 | commit + test + run-time |
| NS1-T22 | 无 markdown_id 不调 B.md | 短途 | unit | 同上 / workflow | P3-03 | commit + test + run-time |
| NS1-T23 | B.json `-p` 物料切换 md/clean | 短途 | unit | `test_claude_cli_port` | P3-04 | commit + test + run-time |
| NS1-T24 | C 不改 original；一次调用 | 短途 | unit | `test_ns1_construct_map` | P3-05 | commit + test + run-time |
| NS1-T30 | 缺 json_prompt_id → 422 | 短途 | 契约 | 🆕 `tests/unit/test_ns1_task_payload.py` | P4-01 | commit + test + run-time |
| NS1-T31 | 拒 prompt_ref/path；角色不匹配 | 短途 | 契约 | 同上 | P4-01 | commit + test + run-time |
| NS1-T32 | 有/无 markdown 路由 | spike | e2e | 🆕 `tests/e2e/test_ns1_pipeline.py` | P4-02 | commit + e2e + run-time |
| NS1-T33 | 结构失败无 open gate | spike | e2e | 🔱 `test_human_review_gate` 对照 | P4-03 | commit + e2e + run-time |
| NS1-T34 | in-flight 不热切新 version | 短途 | unit | `test_ns1_catalog_crud` | P4-04 | commit + test + run-time |
| NS1-T40 | architecture：无 DB body、无编树、无 prompt_ref wire | 短途 | domain | `test_architecture` + `test_ns1_guards` | P5-01 | commit + test + run-time |
| NS1-T41 | e2e generic：无 md，json+C，投影≠假树 | mega | e2e | `test_ns1_pipeline` | P5-02 | commit + e2e + run-time |
| NS1-T42 | e2e legal：有 md 再 json；C 吃 json | mega | e2e | 同上 | P5-02 | commit + e2e + run-time |
| NS1-T43 | e2e：一文件 adopt 失败，sibling 完成，root failed | mega | e2e | 🔱 scatter e2e | P5-03 | commit + e2e + run-time |
| NS1-T44 | 沿用 generation 契约（改断言） | 短途 | e2e | 🔱 `test_generation_pipeline_contracts.py` | P5 | commit + e2e + run-time |
| NS1-T45 | 沿用 D08 intake 四域 | 短途 | domain | ♻️ `tests/intake/**` | 回归 | commit + test + run-time |
| NS1-T46 | hash 漂移 ×N resolve | soak | unit | 🔱 T07 × 重复 | P1-06 退出闸 | commit + soak + run-time |

### 8.2 复用台账

| 既有用例 | 处置 | 改动 | 起跑线 |
|----------|------|------|--------|
| `tests/unit/test_prompt_hash_mismatch.py` | 🔱 fork → T07 | + catalog role / path root | 已存在 |
| `tests/e2e/test_generation_pipeline_contracts.py` | 🔱 | 投影不再要求句子 g2 | 已存在，须改 |
| `tests/e2e/test_human_review_gate.py` | ♻️ | 0；对照 T33 | 已存在 |
| `tests/e2e/test_single_intake_pipeline.py` | 🔱 | 补 json_prompt_id | 已存在 |
| `tests/e2e/test_registered_api_scatter.py` | ♻️ | 断言 0 CLI | 已存在 |
| `tests/intake/test_*.py` | ♻️ | 0 | 已存在 |
| `tests/domain/test_architecture.py` | ✅ 扩展 | + NS1 守卫 | 已存在 |
| `tests/unit/test_workflow_runtime.py` | ♻️ | 新步 key 若需 | 已存在 |

### 8.3 分层与跑法

| 类型 | 跑法 / 频率 | 主要层 | 触发 |
|------|-------------|--------|------|
| 短途 | `uv run pytest -q tests/unit tests/domain tests/intake` | unit·domain·契约 | 每 PR |
| spike | 单 Phase e2e 片段 | e2e | Phase 收口 |
| mega | `test_ns1_pipeline` 两旅程 + T43 | e2e | AP 收口 |
| soak | T46 hash 漂移重复 | unit | 退出硬闸 |

**层对照（业主 unit / e2e / domain）**：短途 unit = `tests/unit`；domain = `tests/domain` + `tests/intake`；e2e = `tests/e2e`。

### 8.4 测试缺口

- 不覆盖 `grok -p` 真修（O1）→ 后继 repair AP。
- 不覆盖 live MiniMax 质量（分层好不好）→ 手动 smoke，不进 P0-CI。
- 不覆盖 legal.case 分析通道 → 正文变体 campaign。
- 不覆盖 scatter 部分成功 → `T-O-345`。

### 8.5 测试保真

- 每项 PASS 必有 `commit + 测试名 + run-time(UTC)`；本 AP 在 `executed` 前 §11 回填。
- stub CLI **禁止**网络。
- 安全项 T06 必须含攻击向量，不得只测 happy-path。
- 旧 e2e 若仍断言句子 g2：改测试，不改回假树。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对 |
|-------------|------|----------|------|
| D04 列晋升 | 与「55 表闭集」叙事摩擦 | `medium` | 只加列；migration 头声明；§5.4 附录 |
| 旧 e2e 假树假设 | 绿测锁死错误语义 | `high` | Phase 2 同步改断言 |
| CLI 输出信封 | MiniMax vs 文档 `structured_output` | `medium` | port 双解析；CI 只用 stub |
| B.md 无 schema | 垃圾 markdown 砸 B.json | `medium` | 显式失败；不自动 skip |
| metadata_refresh 漏改 | 仍调旧 structurize | `high` | P2-02 清单含 refresh |
| Workflow 多变体图 | HTTP/PDF 副本漏加步 | `medium` | 生成器或清单测试 |

### 9.2 约束与前提

- **技术前提**：可跑 `uv`；SQLite 本地；不依赖 live LLM。
- **运行时前提**：生产 `--bare` + `ANTHROPIC_*` 由部署注入；本 AP 不配送密钥。
- **组织协作前提**：QNA 已锁；执行中产品改口回 QNA。
- **上线 / 合并前提**：§8 mega+soak 四元组；无「降级假树」开关。

### 9.3 文档同步要求

- QNA：不改。
- S14/D04：Phase 5 附录（列、四 role、内部 CRUD 窄解释）。
- README：若有 Task payload 示例，补 `json_prompt_id`。
- 测试：本 AP §8 即说明。

### 9.4 完成后的预期状态

1. ingest 必带 `json_prompt_id`；可选 markdown/clean/summarizer。
2. current structure 来自 adopt，不再是句子树。
3. C 整包填 summary，S07 投影为 construction SSOT。
4. catalog 内部 CRUD 出新 version；运行时 hash 门闩。
5. 结构失败 = Task failed，不开人审；scatter 仍整单 fail-closed。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

1. 生产无假树入口（`NS1-T12` `NS1-T40`）。
2. mega 两旅程：无 md / 有 md（`NS1-T41` `NS1-T42`）。
3. 失败隔离 + root fail-closed（`NS1-T43`）。
4. catalog 安全 + hash soak（`NS1-T06` `NS1-T46`）。
5. API 拒不可靠指针（`NS1-T30` `NS1-T31`）。

### 10.2 收口映射表

| 收口目标 | 工作项 | Test-ID | PASS 证据 | 状态 |
|----------|--------|---------|-----------|------|
| schema 冻 | P1-01 | T01 | `40b8ca2` + layered schema/prompt contract tests | `observed-OK-at-closure` |
| 正文可 hash | P1-02 | T02 | `40b8ca2`, `2f81be0` + prompt body/hash tests | `observed-OK-at-closure` |
| catalog DDL+CRUD+门闩 | P1-03..06 | T03–T07 T46 | `1ab1e37` + catalog/hash tests + 32-round soak | `observed-OK-at-closure` |
| adopt 权威 | P2-01..03 | T10–T13 T12 | `1971033`, `1cc7d2e` + adopt/compiler/generation tests | `observed-OK-at-closure` |
| 四跳通道 | P3-01..05 | T20–T24 | `fcb8d31`, `72845a8`, `a6498c2` + CLI/stage tests | `observed-OK-at-closure` |
| API/图 | P4-01..04 | T30–T34 T32 | `07e585b`, `b3022f8`, `a6d838b` + 51 targeted tests | `observed-OK-at-closure` |
| 旅程/隔离 | P5-02..03 | T41–T43 | `d7cf742` + two journeys/scatter failure e2e | `observed-OK-at-closure` |
| domain 守卫 | P5-01 | T40 | `d7cf742` + domain architecture guards | `observed-OK-at-closure` |

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | `T-O-343..351` 均有代码落点；假树退出生产 |
| 测试 | §8 短途+mega+soak 全 PASS，硬闸四元组齐 |
| 文档 | QNA 不动；S14/D04 附录已写 |
| 风险收敛 | 无运行时降级开关；无 DB 正文 |
| 可交付性 | 新 WorkflowRevision 可 ingest；旧 revision 不热切 |

### 10.4 NOT-成功识别

任一项 `degraded / 未观察` ⇒ 不得标 `executed`。用 `verified / observed-OK-at-closure / partial / 未观察 / deferred` 归类。

---

## 11. 执行日志回填（仅 `executed` 状态使用）

本节由执行者按 `.adocs/code-execution-log.md` 在每个 Phase 收口后 append；最终所有 Phase 完成后将文档状态更新为 `executed`。

## 11.1 Phase 1 执行日志

> 执行者：`Codex`
> 执行时间：`2026-08-14 08:03 UTC`
> 文档状态：`executing`
> 代码改动统计：`17 个 tracked 文件修改 / 12 个新文件 / 1 个 schema 版本落点`

- **实际执行摘要**：`P1-01..P1-06` 已完成；新增严格 `layered_content.v1` JSON Schema 与无 span 的 Python 边界校验、四角色 prompt 正文、007 migration、Registry catalog resolve/hash gate、内部 operator CRUD 与 P1 测试台账。
- **Phase 偏差（计划 vs 实际）**：
  - `P1-02 (substrate-fit)`：保留既有 `promptA.default`、`promptB.default`、`promptC.default` 兼容指针，同时新增 `markdown`/`json` 四角色路径；理由是当前 ConfigSnapshot、旧 hash 门闩和测试仍以三元 key 读取，先保证不热切与可回归，P3/P4 再切换主链入口。
  - `P1-05 (security-fit)`：CRUD 路由沿用现有 `/internal` operator token + internal-network router guard；测试通过 dependency override 只绕过测试网络地址，不改变生产 guard。
- **阻塞与处理**：
  - `full pytest` 初跑在既有 Turso/SQLite 直接读路径出现 4 个 disk I/O/file-format 失败；P1 定向测试与新 migration/bootstrap 无关联堆栈，已记录为 final full-suite 复验项，不以 degraded 结果冒充绿灯。
  - 既有 `test_d04_write_paths` 将 migration 尾项硬编码为 006；已按新增 NS1 migration 更新断言并补 catalog 列守卫。
- **测试发现**：`uv run pytest -q tests/unit/test_layered_schema.py tests/unit/test_ns1_prompt_bodies.py tests/unit/test_ns1_catalog_ddl.py tests/unit/test_ns1_prompt_catalog.py tests/unit/test_ns1_prompt_routes.py tests/unit/test_prompt_hash_mismatch.py tests/unit/test_d04_write_paths.py` → `16 passed`；`uv run ruff check .` → pass；`uv run python -m compileall -q api src` → pass；`git diff --check` → pass。P1 分簇 commits：`40b8ca2`（schema/prompts/contracts/tests）、`1ab1e37`（catalog/migration/CRUD/tests）、`2f81be0`（prompt body contract fix）。
- **后续 handoff**：P2 读取 P1 产出的 schema、catalog json 行闭集与 prompt hash；实现 `adopt_layered_json`，不得恢复 compiler 假树或按句补层。

### 11.1.1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点（file:line） | 备注 |
|--------|------|----|------------------------|------|
| `P1-01` | `✅ done` | `40b8ca2` | `data/schemas/lsrag.layered_content.v1.json`; `src/contracts/lsrag/layered_content.py` | strict/additionalProperties=false；拒绝 span/未知字段 |
| `P1-02` | `✅ done` | `40b8ca2`, `2f81be0` | `data/prompts/{clean,markdown,json,summarizer}/`; `data/prompts/prompt-*.md` | 四角色正文可 hash；B.json 不含旧交卷字段名 |
| `P1-03` | `✅ done` | `1ab1e37` | `src/persistence/migrations/007_ns1_prompt_catalog.sql` | 既有指针表列晋升，不新建 required 表 |
| `P1-04` | `✅ done` | `1ab1e37` | `src/services/registry.py:26-90,190-260` | role/status/granularity_set bootstrap |
| `P1-05` | `✅ done` | `1ab1e37` | `api/internal/prompts.py`; `api/internal/routes.py:13-90` | CRUD 不接 body；Update 为新 version |
| `P1-06` | `✅ done` | `1ab1e37` | `src/services/registry.py:350-500` | resolve 与 H(file)==hash fail-closed |

### 11.1.2 文档状态

`draft → executing（P1 closed / 2026-08-14）`；P2 已解锁。residual：Turso/SQLite direct-read full-suite 问题承接 NS1-P5 final verification。

## 11.2 Phase 2 执行日志

> 执行者：`Codex`
> 执行时间：`2026-08-14 08:19 UTC`
> 文档状态：`executing`
> 代码改动统计：`4 个 tracked 文件修改 / 2 个新测试文件 / 0 个 schema bump`

- **实际执行摘要**：`P2-01..P2-03` 已完成。kernel 新增 `normalize_layered_candidate`、`adopt_layered_json`/report、profile 闭集校验、g0 确定性回填、g≥1 精确子串首次锚定与 occurrence_count，并生成一块 layered 对应一块 projection；generation runtime、construct、metadata refresh 已移除旧 `compiler.structurize` 生产调用；C 改为整包 layered summary 对齐，original/block_id/granularity 变更会 fail-closed。
- **Phase 偏差（计划 vs 实际）**：
  - `P2-02 (substrate-fit)`：metadata refresh 不再从 clean 重新编树，而是解析并复验冻结的 structure/projection artifact；理由是 refresh 的来源是历史 full-valid immutable family，不具备 B 候选 JSON，直接重建会违反 source freeze。
  - `P2-03 (offline-fit)`：offline profile 用同一 projection block 集合生成确定性 C-shaped summary package，以保持无 live vendor 的本地证明；没有恢复按句摘要循环，live C 已改为整包单次 structured handoff，CLI 运输由 P3 继续收口。
- **阻塞与处理**：
  - 旧 generation e2e 在 P3 候选工人尚未落地时显式失败 `STRUCTURE_CANDIDATE_MISSING`；这是删除假树 fallback 后的预期 contract break，已转交 P3/P5 更新 fixture/stub，不以假树或静默补层恢复。
  - P1 已记录的 Turso/SQLite direct-read `disk I/O/file-format` full-suite 问题仍作为 P5 final verification residual；本 Phase 定向测试未复现该问题。
- **测试发现**：`uv run pytest -q tests/unit/test_adopt_layered_json.py tests/unit/test_lsrag_compiler.py tests/domain/test_ns1_guards.py tests/unit/test_prompt_hash_mismatch.py tests/unit/test_d04_write_paths.py` → `19 passed`；`uv run ruff check`（P2 touched files/tests）→ pass；`uv run python -m compileall -q api src` → pass；`git diff --check` → pass；`rg "compiler\\.structurize\\(" src/runtime/intake` → no match。P2 分簇 commits：`1971033`（kernel/adopt/T10-T11）、`1cc7d2e`（generation wiring/metadata/C mapping/T12-T13）。
- **后续 handoff**：P3 读取本 Phase 的 accepted layered state contract；实现可注入 Claude CLI A/B.md/B.json/C 四跳和 local RecordingStub，使 `_structurize` 在无 live vendor 时也只接收显式候选 JSON；不得回退 `structurize(clean_text)`。

### 11.2.1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点（file:line） | 备注 |
|--------|------|----|------------------------|------|
| `P2-01` | `✅ done` | `1971033` | `src/services/lsrag_compiler.py`; `tests/unit/test_adopt_layered_json.py` | profile/anchor/report/projection 已由 kernel 统一计算 |
| `P2-02` | `✅ done` | `1cc7d2e` | `src/runtime/intake/generation_construct.py`; `src/runtime/intake/generation_artifacts.py`; `tests/domain/test_ns1_guards.py` | runtime 无旧 fixture compiler 调用；refresh 解析冻结 artifact |
| `P2-03` | `✅ done` | `1cc7d2e` | `src/services/lsrag_compiler.py`; `src/runtime/intake/generation_construct.py`; `src/runtime/intake/generation_live.py` | whole-package summary map；original mutation/缺块 fail-closed |

### 11.2.2 文档状态

`executing（P1/P2 closed / 2026-08-14）`；P3 已解锁。residual：P3 候选工人与 P5 旧 e2e fixture 收口。

## 11.3 Phase 3 执行日志

> 执行者：`Codex`
> 执行时间：`2026-08-14 08:34 UTC`
> 文档状态：`executing`
> 代码改动统计：`11 个文件修改 / 4 个新测试文件 / 0 个 migration/schema bump`

- **实际执行摘要**：`P3-01..P3-05` 已完成。新增无 shell 的 `ClaudeCliPort`、subprocess transport、RecordingStub 与 deterministic local stub；接通 LLM clean、可选 Markdown 转写、B.json structured candidate、C whole-package summary；所有进入 kernel 的 candidate 仍经过 `adopt_layered_json`，C 不改变 original/block_id/granularity。
- **Phase 偏差（计划 vs 实际）**：
  - `P3-01 (transport-fit)`：纯文本模式兼容 Claude JSON envelope，并补 typed error/usage/session 解析；理由是实测 `claude -p` plain 与 structured 输出 envelope 形态不同，必须保留两条显式解码路径。
  - `P3-04 (offline-fit)`：非 live 组合根默认注入 deterministic local stub；理由是 owner 仅授权本地验证且 CI 禁 live vendor，仍需让完整 generation contract 在本地有可重复候选来源。
  - `P3-05 (registry-fit)`：为 live C 补 bootstrap schema identity `lsrag.layered_content.default@v1`；理由是 C 的 frozen binding 必须有独立 schema registry 坐标，不能借用旧 structure identity。
- **阻塞与处理**：
  - 旧 `tests/e2e/test_single_intake_pipeline.py::test_live_profile_uses_frozen_binding_for_vector_write_and_query` 仍提供旧 `{"status":"ok","stage":"structure"}` structured fixture，当前按设计失败 `STRUCTURE_CANDIDATE_INVALID/MISSING`；没有恢复 clean-text 假树 fallback，转交 `P5-02 / NS1-T41/T42` 更新 live fixture。
  - `full pytest` 的既有 Turso/SQLite direct-read `disk I/O/file-format` residual 延续 P1/P2 记录，交由 P5 final verification 复验。
- **测试发现**：commit 后重跑 `22 passed`（T20–T24、adopt、guard、hash、D04、offline generation e2e）；`uv run ruff check` → pass；`uv run python -m compileall -q api src tests/...` → pass；`git diff --check` → pass；`rg "compiler\\.structurize\\(" src/runtime/intake` → no match。P3 分簇 commits：`fcb8d31`（CLI/config/transport tests）、`72845a8`（handlers/wiring/registry）、`a6498c2`（worker stage tests）。
- **后续 handoff**：P4 需在新 payload 中强制 `json_prompt_id`、解析/冻结四 role prompt identity，并把 markdown branch 接入主图及 scatter child；不得让 request 携带 body/path 作为 prompt 指针。

### 11.3.1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点（file:line） | 备注 |
|--------|------|----|------------------------|------|
| `P3-01 / NS1-T20` | `✅ done` | `fcb8d31` | `src/runtime/inference/claude_cli.py:20-180`; `tests/unit/test_claude_cli_port.py` | argv 无 credential；structured/plain envelope；typed transport errors |
| `P3-02 / NS1-T21` | `✅ done` | `72845a8`, `a6498c2` | `src/runtime/intake/clean_preflight.py:72-96`; `tests/unit/test_ns1_clean_dispatch.py` | CLI 仅注入 llm-required clean strategy |
| `P3-03 / NS1-T22` | `✅ done` | `72845a8`, `a6498c2` | `src/runtime/intake/core.py:301-307`; `src/runtime/intake/generation_construct.py:163-219` | Markdown 输出独立 state/artifact，plain no-schema |
| `P3-04 / NS1-T23` | `✅ done` | `72845a8`, `a6498c2` | `src/runtime/intake/generation_construct.py:74-117,513-614`; `tests/unit/test_ns1_generation_cli.py` | markdown 优先作为 B.json material，否则 clean；candidate 统一 adopt |
| `P3-05 / NS1-T24` | `✅ done` | `72845a8`, `a6498c2` | `src/runtime/intake/generation_construct.py:119-161,711-820`; `src/services/registry.py:709-736` | C 一次消费全包；original immutable；live schema identity 已注册 |

### 11.3.2 文档状态

`executing（P1/P2/P3 closed / 2026-08-14）`；P4 已解锁并进入 STEP-1/STEP-2。

## 11.4 Phase 4 执行日志

> 执行者：`Codex`
> 执行时间：`2026-08-14 09:10 UTC`
> 文档状态：`executing`
> 代码改动统计：`13 个实现文件 / 17 个测试文件（含 1 个新建）/ 0 个 migration；workflow revision bump 4→4/2`

- **实际执行摘要**：`P4-01..P4-04` 已完成。`IntakeIngestPayload` 现在只接受四 role 的 prompt identity（`json_prompt_id` 必填）；materialize 从既有 catalog row 解析并冻结 `{prompt_id, version, content_sha256, git_relative_path, role, granularity_set}`；主图与 registered-api scatter child 均支持可选 Markdown 转写跳；B 结构失败使用 terminal failed route，不开启 human review；live structured/text resolver 按 frozen role pointer 复验路径与 hash。
- **Phase 偏差（计划 vs 实际）**：
  - `P4-02 (compatibility-fit)`：主图 revision 从 3 升至 4，scatter child 从 1 升至 2，并登记去掉 Markdown branch 的 pre-NS1 compatibility definitions；理由是既有 workflow digest 必须保持可解析，历史 revision 不能被当前图静默重写。
  - `P4-04 (optional-selection-fit)`：未提供 Markdown identity 时不写入 markdown selection fact，而是让 typed guard 缺失并 fail closed 到无 Markdown route；理由是 optional branch 不能由默认值或 payload_extra 猜测开启。
- **阻塞与处理**：
  - P4 无阶段内 blocker；此前 Turso/SQLite direct-read `disk I/O` 间歇性问题在 P5 全量复验中继续观察，不以 degraded 结果宣称全绿。
  - 没有执行 live migration、worker 发布或 Pages 发布；所有验证使用本地 SQLite/Turso 适配器与 deterministic stub。
- **测试发现**：P4 commit 后定向合同/运行时集合为 `51 passed`（`tests/unit/test_ns1_api_workflow.py`、prompt catalog/CLI/route/worker、workflow runtime/registry/revision compatibility、D02、Task API、source capability）；`tests/e2e/test_single_intake_pipeline.py::test_live_profile_uses_frozen_binding_for_vector_write_and_query` 与 generation contracts 为 `2 passed`；targeted `ruff`、`git diff --check` 通过。P4 分簇 commits：`07e585b`（API/快照/主图/scatter/compatibility）、`b3022f8`（payload 与 e2e/unit 合同）、`a6d838b`（结构失败不转 human review）。
- **后续 handoff**：P5 继续完成 domain architecture fences、无 Markdown/有 Markdown 两条 stub CLI mega 旅程、scatter child failure isolation、既有 generation/intake 回归与 hash soak，并回填 S14/D04/README；不得改变 prompt body git-only、JSON closed profile、no-live/no-publish 约束。

### 11.4.1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点（file:line） | 备注 |
|--------|------|----|------------------------|------|
| `P4-01 / NS1-T30/T31` | `✅ done` | `07e585b`, `b3022f8` | `src/contracts/api/models.py:175`; `src/services/config_snapshots.py:557`; `tests/unit/test_ns1_api_workflow.py:29` | json required；extra=forbid；role/path/hash/profile 校验 |
| `P4-02 / NS1-T32` | `✅ done` | `07e585b` | `src/workflows/lsrag_definition.py:162,349-403`; `src/workflows/builtin_scatter.py:398,462-480` | optional Markdown branch 与 pre-NS1 compatibility graph |
| `P4-03 / NS1-T33` | `✅ done` | `a6d838b` | `src/workflows/lsrag_definition.py:67`; `tests/unit/test_ns1_api_workflow.py:151` | structurize failed 直接 terminal failed，无 human fallback |
| `P4-04 / NS1-T34` | `✅ done` | `07e585b` | `src/runtime/workflow/runtime_materialize.py:130`; `src/runtime/intake/generation_live.py:67-117` | frozen selected pointers/input manifest；retry 不热切 |

### 11.4.2 文档状态

`executing（P1/P2/P3/P4 closed / 2026-08-14）`；P5 已解锁并进入 STEP-1/STEP-2/STEP-3。residual：Turso/SQLite direct-read full-suite stability 与 P5 最终 closure 证据。

## 11.5 Phase 5 执行日志

> 执行者：`Codex`
> 执行时间：`2026-08-14 09:23 UTC`
> 文档状态：`executing`
> 代码改动统计：`6 个代码/测试文件（含 1 个新 e2e 文件）/ 5 个文档文件待 docs cluster / 0 个 migration`

- **实际执行摘要**：`P5-01..P5-04` 与 `NS1-T44/T45/T46` 已完成。新增 domain architecture fences 与 generic/no-Markdown、legal/with-Markdown 两条本地 deterministic-stub 旅程；scatter 失败隔离复用现有 collect-all/fail-closed e2e；补充 32 轮四 role hash resolve soak；S14/D04 追加 catalog 窄附录，README 追加 identity-only payload 示例，QNA 未修改。
- **Phase 偏差（计划 vs 实际）**：
  - `P5-01 (guard-location-fit)`：守卫落在 `tests/domain/test_ns1_guards.py`，并保留 `test_architecture.py` 作为 D03 总守卫；理由是 NS1 规则需要在不导入运行时的情况下扫描 production source/migration/API boundary。
  - `P5-02 (semantic-fixture-fit)`：index-rebuild 旧断言从“必须返回 g0 全文”改为接受冻结 projection 的有效层原文；理由是 NS1 退出假树后，召回命中 g1/g2 是合法 layered semantics，不可为旧断言恢复全文复制。
  - `P5-03 (reuse-fit)`：没有复制 scatter runtime；直接复验既有 child failure / sibling completion / root fail-closed acceptance test，并额外用 NS1 graph failure route unit proof 锁定结构失败不转人审。
- **阻塞与处理**：
  - 完整 `tests/e2e` 在本地 `pyturso==0.7.2` raw inspection 路径仍有 6 个 test-case 失败（index rebuild 3、reactivate 1、intake rebuild/metadata 1、scatter auto-zero 1），均发生在测试用标准 `sqlite3.connect` 读取 Turso `mkb.sqlite3` 时，错误为 `disk I/O` / `file is not a database`；同类 residual 已在 P1–P4 日志记录，非 NS1 生产逻辑失败。
  - 处理方式是保留 fail-fast 证据并将该适配器/测试 harness 问题作为 closure known issue；没有把全量结果改写为 success，也没有用 SQLite fallback 改写 Turso 物理验证语义。
  - 没有执行 live migration、worker 发布或 Pages 发布；NS1 mega 使用 local deterministic stub。
- **测试发现**：`pytest -q tests/unit` → 100% pass；`pytest -q tests/domain` → `9 passed`；P5 targeted guards/mega/scatter/hash 集合 → `10 passed`；`pytest -q tests/e2e -k 'not ...'`（排除上述 pre-existing raw inspection cases）→ `12 passed`；`ruff check .`、`compileall -q api src tests`、`git diff --check` → pass。生产扫描仅在 domain guard 测试字符串中保留禁止模式，`src/runtime/intake`/`src/persistence/migrations`/API payload production scan 无违规。P5 代码/测试 commit：`d7cf742`。
- **后续 handoff**：NS1 closure 以 `close-with-known-issues` 收口；下游 test-harness/adapter charter 需要让 Turso inspection 使用 Turso port 或在 app close 后做合法 snapshot，再重跑 6 个 raw-sqlite cases。该 residual 不改变 NS1 prompt identity、layered adoption、workflow fail-closed 或 no-live/no-publish 结论。

### 11.5.1 逐工作项状态

| 工作项 | 状态 | PR | 实际落点（file:line） | 备注 |
|--------|------|----|------------------------|------|
| `P5-01 / NS1-T40` | `✅ done` | `d7cf742` | `tests/domain/test_ns1_guards.py:13-38` | 无 runtime 假树调用、无 migration `body_text`、无 caller prompt_ref/path |
| `P5-02 / NS1-T41/T42` | `✅ done` | `d7cf742` | `tests/e2e/test_ns1_pipeline.py:73-130` | generic/no-md 与 legal/with-md 均 succeeded；projection 覆盖 g0/g1/g2 且原文不全相同 |
| `P5-03 / NS1-T43` | `✅ done` | `d7cf742` | `tests/e2e/test_registered_api_scatter.py:484-499` | 一 child failed、sibling succeeded、root `scatter-required-child-failed` |
| `P5-04` | `✅ done` | `42538ee` | `docs/baseline/domain-truth/S14-config-prompt-model-registry.md:1070`; `docs/baseline/domain-truth/D04-turso-physical-schema.md:1920`; `README.md:22` | 窄附录与 payload 示例；不改 QNA |
| `NS1-T44/T45/T46` | `🟩 partial` | `d7cf742` | `tests/unit`; `tests/domain`; `tests/unit/test_ns1_prompt_catalog.py:108` | unit/domain/hash soak 与非 residual e2e 通过；6 个 Turso raw inspection cases deferred |

### 11.5.2 关键指标演进

| 指标 | P4 land | P5 land | Δ |
|------|----------|----------|---|
| deterministic mega journeys | 0 | 2 | +2（no-md / with-md） |
| architecture fences | 1 legacy compiler guard | 3 NS1 fences | +2（body_text / caller coordinates） |
| hash resolve soak | single drift/resolve cases | 32 rounds × 4 role IDs | +128 stable resolutions |

### 11.5.3 pre-existing 失败甩锅

| 失败项 | 证据（git / 命令） | 判断 |
|--------|---------------------|------|
| Turso file inspected with standard sqlite3 during existing e2e | `git show e118192:tests/e2e/test_index_rebuild.py:21`、`git show e118192:tests/e2e/test_intake_reactivate.py:21` both already use `persistence_backend="turso"` and raw `sqlite3.connect`; current full `pytest -q tests/e2e` errors are `disk I/O` / `file is not a database` at those inspection lines | `pre-existing adapter/test-harness issue; non-NS1 functional blocker, deferred to successor harness charter` |

### 11.5.4 文档状态

`executing（P1/P2/P3/P4/P5 implementation closed / 2026-08-14）`；closure 待生成。residual → successor test-harness/adapter charter（Turso inspection port parity）。
