# Nano-Agent 行动计划

> 服务业务簇: `MKB / new-harvest / intake-four-channel-live`
> 计划对象: `10 CleanStrategy + 3 registered-api operation live-to-retrieval`（namespace + facet query）
> 类型: `upgrade`（激活已有 handlers/tail，不重写 `intake/`）
> 作者: `Grok workflow new-harvest-nh6-nh9-action-plans`
> 时间: `2026-08-29`
> 文件位置: `docs/plan/new-harvest/AP-NH7-clean-capability-activation.md`
> 上游前序 / closure:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 `frozen` §7.7（唯一执行基线 · 台账 A/B/C/D）
> - DAG：join `AP-NH2` + `AP-NH3` + `AP-NH5` + `AP-NH6`；**`local_object` 格另需 `AP-NH4`**
> - `AP-NH1` `stop-or-go.md=GO` 且 `NH1-T07` 已把 10+3 合法格预埋进 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`
> - `AP-NH2` kind-only + 合法边可达（`NH2-T05`）
> - `AP-NH3` actual S05 + typed fact/print/PDF 观察诚实（`NH3-T03`/`NH3-T04`）
> - `AP-NH4` public upload+stat 对 local PDF/doc/image 字节入口（`NH4-T01`/`NH4-T04`）
> - `AP-NH5` 六元组 + `semantic_channel`/`vector_channel` + facet SQL（`NH5-T03`/`NH5-T07`）
> - `AP-NH6` default-root 真实 parser/browser/print/OCR/Vision/DU 供给（`NH6-T03/T04/T06/T09`；`create_app()` 无 patch）
> 下游交接:
> - `AP-NH8` 七意图 / exact-clean / publication lifecycle（消费本 AP 已激活的 live clean，不在本 AP 旁路 reclean）
> - `AP-NH9` closed-set / crash / campaign mega（Capstone C–F 的 **query 终态** 必须已在本 AP 证明，NH9 不得第一次补功能）
> 关联设计 / 调研文档:
> - `docs/eval/new-harvest/final-execution-plan.md` v1.0 §4.2 OOS / §6 DAG / §7.7 A/B/C/D / §9.2 C–F / §11.A
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0 Q17 → `T-O-397`
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5 `T-O-376/378/381/386/388/389`
> 冻结决策来源:
> - `docs/eval/new-harvest/pre-charter-qna.md` v1.0：Q17/Q13/Q22/Q23/Q25/Q26 → `T-O-397` / `T-O-393` / `T-O-402` / `T-O-403` / `T-O-405` / `T-O-406`（只读引用；本 action-plan 不填写 Q/A）
> - `docs/eval/new-harvest/pre-initial-planning-qna.md` v0.5：`T-O-376` / `T-O-378` / `T-O-381` / `T-O-383` / `T-O-386` / `T-O-388` / `T-O-389`
> grounding 来源:
> - HEAD `1221aa1` 独立 `read_file` 核验 + final §7.7 四台账 + RA04/RA08（RA05 只消费「供给已接线」）
> 关联 reference-anchor:
> - [`assessment-analysis-04-clean-capability-and-admitted-clean.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-04-clean-capability-and-admitted-clean.md)（主面）
> - [`assessment-analysis-08-publication-and-intake-lifecycle.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-08-publication-and-intake-lifecycle.md)（publication/query 终验）
> - [`assessment-analysis-05-runtime-adapters-readiness-and-security.md`](../../eval/new-harvest/reference-anchor/assessment-analysis-05-runtime-adapters-readiness-and-security.md)（只消费 default-root 已接线；不在本 AP 选库/补隔离）
> 文档状态: `draft`
> 台账 ID 区间（final §11.A `7.7 AP-NH7`）：`NH7-01..10` / `NH7-A01..07` / `NH7-T01..10`
> HEAD: `1221aa1`
> Capstone：C/D/E/F 的 **query 终态** 在本 AP；供给在 NH6，upload 在 NH4，facet 键在 NH5
> migration: `M-NH-07` prompt catalog 对齐（本 AP 执行；不对齐方案另开 owner-gate）

**编号纪律**：工作项 / 锚 / Test-ID 必须使用上列冻结区间。禁止重编号、合并、删除。

---

## 0. 执行背景与目标

HEAD `1221aa1` 已交付 10 `CleanStrategyKey` / 9 Process capability / 3 registered-api operation 的 **纯函数闭集**（`T-R-NH-07`；33 unit 全绿）以及 publication tail CAS（`T-R-NH-15`；`vector_publish_commit.py:57-191`）。它 **没有** live-to-retrieval：6 张 LLM/print-pdf/vision 图公开选不中（`lsrag_definition.py:1003-1054`）；`clean_preflight.py:46-71` 用 process→strategy 反推，同一 `clean.extract.pdf_llm` 在 `print_pdf` 表示从未被 acquire 写出时物理不可达；默认组合根未注入 `browser_fetcher`/`clean_llm`（`api/app.py:330-345`，属 NH6）；source e2e 赋值 `_http_fetcher/_browser_fetcher`（`test_source_capability_paths.py:99-101`）并以 Task `succeeded`（同文件 `:166-168`）当绿；API scatter 停在 `publication_ready` 且零 `retrieval:search`（`test_registered_api_scatter.py:209-373`）；`WorkflowTerminalKind.NOOP` 映射 `ExecutionStatus.SUCCEEDED`（`runtime_outcome.py:505-509`）不能表达 `exhausted_zero`（`T-R-NH-24`）。

本 AP 只消费已冻结 `T-O-376/381/386/397` 与 DAG 前序，把 10+3 **合法格**从「函数存在」激活到 **default-root、真实 input、namespaced + facet query**。类型是 `upgrade`：保留 `intake/` handlers 与 publication tail，改接线、binding 权威、promptA 对齐、产品 disposition 与 L3+L4 终验。不重开 Q10–Q27，不把 GPT/Grok 推荐当尚未冻结的选项。Capstone C/D/E/F 的 query 终态必须在本 AP 落地；供给缺口交回 NH6，不得用 patch 顶 L3。

- **服务业务簇**：`new-harvest` / `S-NH-F7`
- **计划对象**：10 CleanStrategy + 3 registered-api operation live-to-retrieval（namespace + facet query）
- **本次计划解决的问题**：
  - 10+3 合法格未激活：公开图 6 张不可达、default-root 无供给、process→strategy 反推与 print 死合同（`T-O-381`；`NH-RA04-B01/B03/B05`）
  - admitted clean 合同与 promptA 三 id 分叉：空正文、LLM 未对齐即 `PROMPT_HASH_MISMATCH`、确定性路径可能偷调模型（`T-O-386`；`NH-RA04-B04/B08`）
  - 产品终态假绿：Task `succeeded` / `publication_ready` / 无 namespace / NOOP→succeeded 冒充可检索或 exhausted-zero（`T-O-376/397`；`FG-NH-03/04/05`；`T-R-NH-24`）
- **本次计划的直接产出**：
  - 由 registry 生成的 10+3 合法激活 manifest（非 10×4 / 7×4 笛卡尔积）；非法格 409/422 且按 `T-O-405` 分 admission vs runtime
  - 统一 nonempty admitted clean；LLM 绑 PromptRef；API 双 digest + 六元组；失败零向量
  - `M-NH-07` 三 promptA id 对齐；确定性路径零模型调用
  - 每合法格 ≥1 条 L3+L4：`create_app()` 无 patch、真实 input、search 带 namespace、hit 正文 = admitted clean（或声明的 summary 通道）
  - 独立 `result_disposition=exhausted_zero`：非 indexed success、零 child/Revision/vector/publication proof、exhaustion proof + retrieval empty + fingerprint replay
- **本计划不重新讨论的设计结论**：
  - 四通道真实 Process→可检索；503/假接线不算完成（来源：`T-O-376`）
  - 10 strategy + 3 operation 均须 live-to-vector；不含 live 爬虫 / 第五 kind（来源：Q1 / `T-O-381`）
  - 四通道同一份 admitted clean；g0=clean；promptA 仅 LLM（来源：Q6 / `T-O-386`）
  - 独立 `exhausted_zero`，禁止 `NOOP→SUCCEEDED` 冒充该产品终态（来源：Q17 / `T-O-397`；HEAD `runtime_outcome.py:505-509`）
  - 绑定后失败无向量（来源：Q3 / `T-O-383`）
  - 每合法格最低 L3+L4；不可用 33 unit 顶（来源：Q26 / `T-O-406`）
  - 不重写 `intake/` handlers；不锁 PDF/browser/OCR 库名（来源：`T-R-NH-07`；`T-O-393`）

---

## 1. 执行综述

### 1.1 总体执行方式

本 AP 采用 **「先合同后 live、先确定性后模型、先 single 后 scatter、query 才是终态」**：Phase 1 冻结合法格 manifest 与 nonempty admitted clean；Phase 2 对齐 promptA 并锁死确定性零模型调用；Phase 3–5 按 inline/static/PDF → browser/print → multimodal → API+zero 逐格接通 default-root；Phase 6 把每条成功路径收到 actual/S04/g0/S06/proof/pointer/namespace+facet query。禁止在 NH6 未 GO 时用 monkeypatch 顶 L3；禁止把 NH7 live 写进 NH6；禁止复制 publication tail。

### 1.2 Phase 总览

| Phase | 名称 | 规模 | 目标摘要 | 依赖前序 |
|------|------|------|----------|----------|
| Phase 1 | manifest + clean 合同 | `M` | 合法格（消费 NH1-T07 预埋 manifest）；nonempty admitted clean | NH1-T07；NH2 边可达 |
| Phase 2 | promptA | `M` | 三 id 对齐 `M-NH-07`；确定性路径零模型调用 | Phase 1；NH1-08 清单 |
| Phase 3 | 确定性/PDF | `M` | inline/static/PDF-first；真 text-layer（upload 或 HTTP）到 query | Phase 2；NH3 观察；local 另需 NH4；PDF 供给需 NH6 |
| Phase 4 | browser/print | `L` | 声明边 + 真 DOM；print fact→PDF clean，禁 HTML sanitizer | Phase 3；NH2 边；NH3 print fact；NH6 render/print |
| Phase 5 | multimodal + API | `XL` | 5 strategies 真 binary/model；3 op + exhausted_zero | Phase 4；NH6 multimodal；NH5 六元组 |
| Phase 6 | 产品闭包 | `L` | actual + six-tuple + g0/S06 + proof/pointer + namespace+facet query | Phase 3–5 每条 live 成功路径 |

> 说明：上表 `规模` 是描述性提示，不是开工闸，也不改变本模板段落取舍。

### 1.3 Phase 说明

1. **Phase 1 — manifest + clean 合同**
   - **核心目标**：机器可检的 10+3 合法格与 identity 分账；统一 nonempty admitted clean。
   - **为什么先做**：没有合法格表就会滑向 10×4 笛卡尔积或 33 unit 冒充闭集；空 clean 一旦进向量，后面 query 全是假绿。
2. **Phase 2 — promptA**
   - **核心目标**：LLM 策略可绑同一 catalog；旧 refs 可 replay；确定性路径 `complete()` 计数为 0。
   - **为什么放在这里**：未对齐则 Phase 3–5 一接 LLM 就 `PROMPT_HASH_MISMATCH`，且无法证明确定性仍是 clean。
3. **Phase 3 — 确定性/PDF**
   - **核心目标**：inline/doc、HTTP static、PDF-first、真 text-layer 走到 namespaced query。
   - **为什么放在这里**：不依赖 browser/model 的格先证明 tail+query 合同，给后续格当样板。
4. **Phase 4 — browser/print**
   - **核心目标**：仅 `main_text_presence=absent` 的已声明边进真实 DOM；print 产出 `%PDF-` 后走 PDF clean。
   - **为什么放在这里**：必须消费 NH2 声明边与 NH3 诚实 print fact，禁止 handler 暗升与 HTML sanitizer。
5. **Phase 5 — multimodal + API**
   - **核心目标**：5 个 model/binary 策略各一条 live query；三 operation member 命中；exhausted_zero 独立。
   - **为什么放在这里**：供给与语义面已在；本 Phase 只激活，不选库、不重写 mapper。
6. **Phase 6 — 产品闭包**
   - **核心目标**：每条成功路径可回溯 actual/S04/g0/S06/proof/pointer/facet；失败零 hit。
   - **为什么放在这里**：query 是产品终态；前面各格若只停在 Task succeeded 必须在此暴露。

### 1.4 执行策略说明

- **执行顺序原则**：manifest/clean 合同 → promptA → 不需模型的格 → 需 browser 的格 → 需 multimodal 的格 → API/zero → 全路径证据链。禁止先改 scatter 终态再让空 clean 进索引。
- **风险控制原则**：`R-F05` 供给未 GO 则 **T04–T08** 保持 `未观察`，禁止 patch；T03 仅 inline/static。`R-F10` 禁按 lane 复制 tail；`R-F13/14` 禁止 L1/Task/`publication_ready` 顶 L3/L4。
- **测试推进原则**：L1 manifest/CLEAN_EMPTY（T01/T02）→ L2 invocation/UoW/zero disposition（T02/T09）→ L3+L4 逐格 default-root query（T03–T08）→ 负例零向量（T10）。层不可互换（`T-O-406`）。T03–T08 是 L3+L4；NH6 未 GO **不得**用 patch 顶 L3（T03 亦不例外）。
- **文档同步原则**：激活 manifest、`result_disposition` 公开字段、evidence pack 目录预登记；不伪造 SHA；不改 QNA/final。
- **回滚 / 降级原则**：promptA 对齐必须保留旧 snapshot 可 replay；`exhausted_zero` 为加性 disposition，不得把历史 SUCCESS 零集合原地改口。若 NH1 `stop-or-go.md≠GO` 或 NH6 未接线，本 AP 保持 `draft`/`未观察`。

**每条 live 成功路径硬法**（T03–T08）：`create_app()` 无 patch；真实 input；`POST /v1/teams/{t}/retrieval:search` 带 `namespace_key` 或 `namespace_uuid`；hit 正文 = admitted clean（`vector_channel=original`）或声明的 summary 通道。

### 1.5 本次 action-plan 影响结构图

```text
AP-NH7 10+3 vertical activation
├── Phase 1: manifest + clean 合同
│   ├── CLEAN_STRATEGY_DEFINITIONS + REGISTERED_PROVIDER_OPERATIONS → 合法格
│   ├── closed_set_manifest.v1.json（消费 NH1-T07 预埋）
│   └── nonempty admitted clean / CLEAN_EMPTY 补测
├── Phase 2: promptA
│   ├── M-NH-07 canonical catalog + 旧 ref 兼容
│   └── 确定性路径 invocation count = 0
├── Phase 3: inline / static / PDF text-layer
│   ├── dispatch_clean PDF-first（✅ 保留）
│   ├── local_object ← NH4 upload
│   └── namespaced + facet query
├── Phase 4: browser / print
│   ├── 声明边 + NH3 main_text_presence
│   ├── 真 DOM / 真 %PDF-（供给来自 NH6）
│   └── print 走 PDF clean，不进 HTML sanitizer
├── Phase 5: multimodal + API
│   ├── 5 strategies 真 binary/model
│   ├── 3 operation member → search
│   └── exhausted_zero ≠ NOOP ≠ metadata no_change
└── Phase 6: 产品闭包
    ├── actual S05 + S04 六元组 + g0/S06
    ├── publication proof/pointer（✅ 复用 tail）
    └── namespace + facet 可回溯
```

---

## 2. In-Scope / Out-of-Scope

### 2.1 In-Scope（本次 action-plan 明确要做）

- **[S1]** `S-NH-F7`：10 strategy + 3 operation vertical live-to-retrieval（`T-O-376/381/386/397`）。
- **[S2]** 合法格由 registry 生成（identity：strategy ≠ process ≠ representation）；非法格 409/422；禁 10×4 与 7×4 笛卡尔积（`T-O-381/405`）。
- **[S3]** 统一 nonempty admitted clean：digest/evidence；LLM 加 PromptRef；API 双 digest + 六元组（`T-O-386/389`）。
- **[S4]** `M-NH-07` promptA 三 id 对齐；旧 snapshot refs 兼容；hash 漂移 fail-closed；确定性零模型调用。
- **[S5]** 改读 **sealed actual / 图 binding** 选 strategy，删除 `clean_preflight.py:46-71` process→strategy 反推（`NH7-A04`）。
- **[S6]** inline/static/PDF-first/真 text-layer、声明 browser DOM、print→PDF clean、5 multimodal、3 API member 各 ≥1 条 L3+L4。
- **[S7]** 独立 `result_disposition=exhausted_zero`；非 indexed success；零产物；proof + empty retrieval + fingerprint replay（`T-O-397`）。
- **[S8]** 每条成功路径：actual S05、S04 六元组、g0/S06、proof/pointer、namespace+facet query（`T-O-376/389/406`）。
- **[S9]** 改造反例测试：删除 source e2e patch；scatter 每 operation 加 namespaced search；补 `CLEAN_EMPTY` 负例。

### 2.2 Out-of-Scope（本次 action-plan 明确不做）

- **[O1]** 生产隔离 / SBOM / CVE / readiness 闭环（`S-NH-F6`；NH6 已做）。本 AP 只消费「default-root 已接线」。
- **[O2]** 七意图 applicability 矩阵与 422/409 code 闭集落地（`T-O-405` 主体属 NH8）。本 AP 只对 10+3 **能力格**非法组合 fail-loud，不生造 7×4 任务。
- **[O3]** crash 全窗 `W-NH-*` / closed-set mega / evidence pack 战役签收（NH9）。
- **[O4]** live connector / cookie / tunnel / 第五 kind / caller `workflow_key` / `action_branch`（`O-NH-01`）。
- **[O5]** 重写 `intake/{web,pdf,doc,api}/` handlers；复制 publication tail；按通道另写 structurize/g0（`O-NH-02`；`T-R-NH-07/15`）。
- **[O6]** existing-object new-cleaner upgrade（`O-NH-03`；`T-O-401`）。
- **[O7]** raw GET / 实验发车 / 云 OCR / CF/R2/SMCP（`O-NH-04/05/06`）。
- **[O8]** 锁死 PDF/browser/OCR **库名**为新 Truth（`T-O-393`）。
- **[O9]** rebuild/metadata exact-clean 旁路（`T-O-407`；NH8）。本 AP 的 ingest 路径必须跑真实 clean。

### 2.3 边界判定表

| 项目 | 判定 | 理由 | 重评条件 |
|------|------|------|----------|
| 10+3 live-to-retrieval + namespace/facet query | `in-scope` | `S-NH-F7`；Capstone C–F | 无 |
| process→strategy 反推改为 actual/图 binding | `in-scope` | `NH7-A04`；`T-O-382/383` | NH3 actual 未封则本 AP 不得标 L3 |
| `exhausted_zero` disposition/metrics/L4 | `in-scope` | Q17 / `T-O-397` | 无 |
| default-root 无 patch | `in-scope`（消费 NH6 接线） | `FG-NH-01`；`T-O-376` | NH6 未 GO → T04–T08 `未观察`；T03 inline/static 不依赖 NH6 binary |
| 七意图 7×4 / intent code 闭集 | `out-of-scope` | `S-NH-F8`；`T-O-405` | NH8 |
| parser/browser 隔离/SBOM | `out-of-scope` | `S-NH-F6` | NH6 |
| crash 全窗 / closed-set 生成器 | `out-of-scope` | `S-NH-F9` | NH9 |
| 重写 intake handlers / 复制 tail | `out-of-scope`（反例） | `T-R-NH-07/15`；`R-F10` | 无 |
| monkeypatch fetcher 当 L3 | `out-of-scope`（反例） | `FG-NH-01` | 无 |
| 33 unit / 函数存在 / 503 / Task succeeded / `publication_ready` | `out-of-scope`（反例） | 台账 D NOT-成功 | 无 |

---

## 3. 业务工作总表

> 编号列使用 final 台账 A 的 `NH7-nn`。每个工作项含不可约三元组：`file:line` / 收口目标 / Test-ID。

| 编号 | 所属 Phase | 工作项 | 类型 | 涉及文件（file:line） | 收口目标 | 测试映射（Test-ID） | 风险 |
|------|------------|--------|------|------------------------|----------|----------------------|------|
| `NH7-01` | Phase 1 | Activation manifest | add | `src/contracts/intake/strategies.py:15-160`；`intake/api/registry.py:73-148`；`src/workflows/lsrag_definition.py:929-1054`；`tests/fixtures/new_harvest/closed_set_manifest.v1.json`（NH1-T07 预埋） | registry 生成合法格；identity 分账；非法 409/422；禁止笛卡尔积 | `NH7-T01` | medium |
| `NH7-02` | Phase 1 | Admitted clean | update | `intake/web/__init__.py:25-29,88-90`；`intake/pdf/__init__.py:29-31,59-60`；`intake/doc/__init__.py:19-20,73-74,96-97`；`src/contracts/intake/semantics.py:37-52`；`src/runtime/intake/clean_preflight.py:122-140` | 正文非空；digest/evidence；LLM PromptRef；API 双 digest 六元组；失败零向量 | `NH7-T01` `NH7-T02` `NH7-T10` | high |
| `NH7-03` | Phase 2 | PromptA alignment | update | `src/contracts/intake/strategies.py:57-147`；`src/services/config_snapshots.py:57-59`；`src/services/prompt_profiles.py:49-50`；`data/prompts/prompt-a-clean-v1.md`；`data/prompts/clean/promptA.clean.v1.md`；`data/prompts/clean/promptA.documentation.default.v1.md`；`src/runtime/intake/clean_preflight.py:74-107` | 三 id 对齐 `M-NH-07`；旧 refs 兼容；hash 校验；drift failure；确定性零调用 | `NH7-T02` | high |
| `NH7-04` | Phase 3 | Inline/static lane | update | `intake/__init__.py:20-132`；`src/runtime/intake/clean_preflight.py:46-127`；`tests/e2e/test_source_capability_paths.py:99-101,166-168` | inline/doc + HTTP static + PDF-first 到 publish/query；空 fail；无 patch | `NH7-T02` `NH7-T03` `NH7-T10` | medium |
| `NH7-05` | Phase 3 | Text-layer lane | update | `intake/pdf/__init__.py:29-31`；`src/runtime/intake/types.py`（NH3 观察出口）；NH4 public upload；NH6 PDF parser | upload/HTTP 真 PDF；verified fact；`pdf.text_layer`；semantic/tail/query | `NH7-T04` | high |
| `NH7-06` | Phase 4 | Render lane | update | NH2 声明边；`src/runtime/intake/acquisition_ingest.py:533-536`（禁常量 profile）；NH6 `browser.render` | 声明/static-shell route；真 DOM；web deterministic/LLM；query | `NH7-T05` | high |
| `NH7-07` | Phase 4 | Browser-print lane | update | `src/contracts/intake/strategies.py:67-76`；`src/runtime/intake/clean_preflight.py:46-71`；NH3 print fact；NH6 `browser.print_pdf` | URL→print fact；PDF clean；no HTML sanitizer；query | `NH7-T06` | high |
| `NH7-08` | Phase 5 | DU/OCR/Vision lanes | update | `src/contracts/intake/strategies.py:88-150`；`intake/__init__.py:91-108`；NH6 S11 multimodal / 确定性 OCR ports | 5 strategies 合法表示；real binary/model；empty fail；各自 query | `NH7-T07` `NH7-T10` | high |
| `NH7-09` | Phase 5 | 3 operation+zero | update | `intake/api/registry.py:73-148`；`intake/api/__init__.py:14-28`；`src/runtime/workflow/runtime_scatter.py:76-98`；`src/runtime/workflow/runtime_outcome.py:505-509`；`tests/e2e/test_registered_api_scatter.py:209-373` | strict map；bad member fail；child publication/query；独立 exhausted_zero | `NH7-T08` `NH7-T09` `NH7-T10` | high |
| `NH7-10` | Phase 6 | First-publication closure | update | `src/runtime/intake/vector_publish_commit.py:57-191`；`src/runtime/intake/generation_assemble.py:17-62`；NH3 actual；NH5 S04/facet | actual S05；S04 six tuple；g0/S06；proof/pointer；namespace+facet query | `NH7-T03`..`NH7-T08` | high |

---

## 4. Phase 业务表格

### 4.1 Phase 1 — manifest + clean 合同

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH7-01` | Activation manifest | a) 以 `CLEAN_STRATEGY_DEFINITIONS`（10 行）+ `REGISTERED_PROVIDER_OPERATIONS`（3 行）为生成器，**禁止**手抄 10×4 或 7×4。b) 每格记录 `(strategy_key 或 provider/operation/version, channel, process_key, llm_required, browser_required, prompt_key, legal acquire, legal representation, kind 图边, 最低测试层 L3+L4)`。c) identity 分账：`process_key` 可服务多 strategy（`clean.extract.pdf_llm`→`pdf.document_understanding` **与** `web.browser_print_pdf`；`clean.ocr.local`→`pdf.ocr` **与** `doc.ocr`），matrix 以 strategy/operation 为行，不以 process 为行。d) 非法格：未知 strategy 409 `CLEAN_STRATEGY_UNSUPPORTED`；capability mismatch 409；image+`doc.deterministic` 409；print-pdf 当 HTML；HTTP PDF 当 web sanitizer（已被 PDF-first 挡住）。admission 可判定的非法组合（请求形状/未登记键）→ 422/409 **且不建 Task/Process**（`T-O-405`）；仅运行时可知的 mismatch → 绑定后 fail-loud、零向量（`T-O-383`）。e) 读 NH1-T07 预埋 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`，断言 10+3 合法格 digest 稳定且本 AP 激活集 ⊆ 该预埋集。f) 原 6 张 unselectable 图不得经 public kind resolver 作为独立 selector 返回（NH2 已并进 kind 图）。 | `strategies.py:15-160`；`intake/api/registry.py:73-148`；`lsrag_definition.py:929-1054`；`tests/fixtures/new_harvest/closed_set_manifest.v1.json`；🆕 `tests/unit/test_nh7_activation_manifest.py` | 合法格闭集可机器生成；非法格有 code；无笛卡尔积 | `NH7-T01` | 10+3 合法；非法 fail-loud |
| `NH7-02` | Admitted clean | a) 四通道成功 clean 必须 nonempty；web/doc/pdf LLM 空 → `CLEAN_EMPTY` 422；PDF 无层走 `CLEAN_PDF_TEXT_LAYER_MISSING` 422（**不是**空成功）。b) runtime `clean_digest=stable_digest({"text": result.text})`；evidence 含 strategy/capability/definition_digest。c) `llm_required=True` 必须 PromptRef（key/version/content_sha256）与 strategy 定义一致，否则 `PROMPT_HASH_MISMATCH`。d) API member：`clean_text min_length=1`、content+meta 双 digest、恰好 6 semantic tuples；schema 失败 `CLEAN_MEMBER_SCHEMA_INVALID` 422 **整批**失败，无 per-member skip。e) 失败路径：零 `mkb_vector_records` indexed 行，namespaced search 对 sentinel 空。f) 补测选定集目前缺失的 `CLEAN_EMPTY` 字面断言（`NH-RA04-B08`）。禁止把 33 unit 绿当本项完成。 | `intake/web/__init__.py:25-29,88-90`；`intake/pdf/__init__.py:29-31,59-60`；`intake/doc/__init__.py:19-20,73-74,96-97`；`semantics.py:37-52`；`clean_preflight.py:122-140`；`generation_assemble.py:17-62`（`:42` body=clean） | 空正文不能 complete；g0.body 仍 = clean（NH5 overlay） | `NH7-T01` `NH7-T02` `NH7-T10` | 正文非空；失败零 hit |

### 4.2 Phase 2 — promptA

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH7-03` | PromptA alignment | a) 消费 NH1-08 三文件互斥 SHA 清单（`promptA.default` / `promptA.clean` / `promptA.documentation.default`）。b) `M-NH-07`：登记 **一份** canonical catalog 身份，使全部 `llm_required` 策略的 `prompt_key/version` 与 Task 冻结 pointer、runtime `_clean_prompt_material` 读取的字节 **同一 SHA**。c) 旧 snapshot 已钉另外两 id 的 in-flight/pin Execution **exact replay**（不热切新 catalog）；新 Task 只写 canonical。d) 禁止用 `latest` 或文档域 profile 静默覆盖 strategy 钉。e) 字节漂移 → 既有 `PROMPT_HASH_MISMATCH` fail-closed（🔱 `test_prompt_hash_mismatch.py` 扩到 promptA clean 路径）。f) 确定性策略（`web.deterministic` / `pdf.text_layer` / `doc.deterministic`）与 `clean.map.registered_api`：`prompt_key is None`，对 `CleanLanguageModel.complete` **invocation count = 0**。g) 不对齐方案另开 owner-gate；`G-NH-14` 保持空号，本项是执行对齐不是新 Truth。 | `strategies.py:57-147`；`config_snapshots.py:57-59`；`prompt_profiles.py:49-50`；三 prompt 文件；`clean_preflight.py:74-107,183-188`；`registry.py` prompt loaders | LLM 可绑；确定性零调用；旧 pin 不 `PROMPT_HASH_MISMATCH` | `NH7-T02` | 三 id 对齐；drift 失败；零模型调用 |

### 4.3 Phase 3 — 确定性/PDF

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH7-04` | Inline/static lane | a) `_clean` 改为读 **sealed actual / selected-output binding** 得到 `strategy_key`，删除/停用 `clean_preflight.py:54-71` 的 process→strategy 表（一 process 多 strategy 时禁止静默猜）。若 NH3 已删反推，本项只接线 actual digest。b) inline → `doc.deterministic`；HTTP static HTML → `web.deterministic`；`dispatch_clean` PDF-first **保留**（`intake/__init__.py:68-90`；`test_intake_clean_dispatch.py:164-176`）。c) 空 HTML/空 doc → `CLEAN_EMPTY`，零向量。d) 🔱 `test_source_capability_paths.py`：**删除** `:99-101` 对 `_http_fetcher/_browser_fetcher` 的赋值；禁止把 `_await_terminal` 超时后的 `running` 改成期待值（`:166-168`）；删 `sqlite3.connect`（`:172`），改 PersistencePort。该文件未清 patch/sqlite3 前 **不得**列入 T03 PASS 跑法。e) 🆕 default-root e2e：`create_app()` 无 patch；真实 inline 文本与 HTTP static fixture；search 带 namespace；hit = admitted clean。 | `clean_preflight.py:46-127`；`intake/__init__.py:20-132`；`test_source_capability_paths.py:99-101,166-168,172`；🆕 `tests/e2e/test_nh7_inline_static_retrieval.py` | 两条确定性格 L3+L4；反例测试不再 patch | `NH7-T02` `NH7-T03` | default-root 无 patch；query 命中 |
| `NH7-05` | Text-layer lane | a) 真实 PDF fixture（含 ToUnicode/可见文本层；**禁止**用字面量 `(...) Tj` 扫描当提取权威——观察法属 NH3，提取属 NH6 parser）。b) HTTP：`http_resource` + PDF media，走 `pdf.text_layer`。c) local：经 **NH4 public upload** 得 handle，再独立 `intake.ingest` + `local_object`（禁内部 `promote` 当 L3；`FG-NH-10`）。d) fact `text_layer=present` 且 clean nonempty；absent → `CLEAN_PDF_TEXT_LAYER_MISSING`，不得降级 DU/OCR、不得出向量。e) namespaced + facet query 命中 admitted clean。f) NH6 parser 未 GO → 本项 `未观察`，禁止 monkeypatch 提取函数当 L3。 | NH4 upload 路由；NH6 PDF supply；`intake/pdf/__init__.py:29-31`；🆕 `tests/e2e/test_nh7_pdf_text_retrieval.py` | 真 text-layer 可检索 | `NH7-T04` | 真 PDF query；无层零 hit |

### 4.4 Phase 4 — browser/print

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH7-06` | Render lane | a) 仅当 decode observer `main_text_presence=absent`（`T-O-402`）且 kind 图已声明 browser 边时 materialize `intake.acquire.http_browser`；`present`/`unknown`/缺键 **不得**暗升。b) 真实 SPA fixture；NH6 `browser.render` 产出 rendered DOM（非常量 `injected-browser-renderer.v1`）。c) clean：`web.deterministic`（rendered）与 `web.llm_rewrite` 各至少一格；后者必须 PromptRef 且计入模型调用。d) `create_app()` 无 `_browser_fetcher=` 测试赋值。e) namespaced query hit = admitted clean。f) NH6-T03 未 PASS → 本项 `未观察`。 | NH2 guards；NH3 fact；NH6 render；`acquisition_ingest.py:533-536`；🆕 `tests/e2e/test_nh7_browser_dom_retrieval.py` | SPA→DOM→query | `NH7-T05` | 真 DOM；无 patch；无常量 profile |
| `NH7-07` | Browser-print lane | a) 已声明 print 边：URL → `representation_kind=print_pdf` 且 bytes 以 `%PDF-` 起（NH3-T04 合同）；独立 print capability/profile/budget（`T-O-403`）。b) clean 绑 `web.browser_print_pdf`（channel=`pdf`，capability=`clean.extract.pdf_llm`），**禁止** HTML sanitizer（`web.deterministic`/`sanitize_html_document` 调用计数 = 0）。c) 选择权威 = sealed actual，不是 `representation==print_pdf` 反推。d) 真 PDF 再走 PDF DU/clean；query 命中。e) render 成功不得顶替 print。 | `strategies.py:67-76`；`clean_preflight.py:46-71`；NH6 print；🆕 `tests/e2e/test_nh7_print_pdf_retrieval.py` | print→PDF clean→query | `NH7-T06` | 无 HTML sanitizer；真 `%PDF-` |

### 4.5 Phase 5 — multimodal + API

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH7-08` | DU/OCR/Vision lanes | a) 五格：`pdf.document_understanding`、`pdf.ocr`、`doc.document_understanding`、`doc.ocr`、`doc.vision`。b) 合法表示：PDF bytes / `image/*` / 文档 bytes；image 不得走 `doc.deterministic`。c) 无 prompt 的确定性 OCR 走 NH6 local port；model-bound 走 S11 multimodal（PromptRef+media+digest/handle），**禁止** `GenerateRequest.input_text` 偷运。d) empty/bad/timeout → typed fail，零向量。e) 各格 default-root query。f) 禁 cloud OCR、禁 `latest` 模型、禁 CLI 冒充 OCR/Vision（HEAD `:76` 排除必须保持）。 | `strategies.py:88-150`；`intake/__init__.py:91-108`；NH6-05/06；🆕 `tests/e2e/test_nh7_multimodal_lanes.py` | 5 格 L3+L4 | `NH7-T07` `NH7-T10` | 真 binary/model；空失败 |
| `NH7-09` | 3 operation+zero | a) 保持三 operation 严格 map（chinatax `get_articles` / domain `get_agency_listings` / realestate `get_listings`）；live fetch OOS，caller-frozen records。b) 每 member 子 publication + **namespaced search 命中**（🔱 scatter e2e 加 search；删 sqlite3）。c) bad/empty member → 422 整批，零向量。d) `records=[]` + immutable exhaustion proof → 登记 `result_disposition=exhausted_zero`（与 metadata `no_change` 分字面）。Task 技术状态可 `succeeded`/`complete`，**不计 indexed success**；不造 child/Revision/vector/**publication proof**；retrieval 合法空；同 fingerprint replay 同 disposition。e) **禁止**把 `WorkflowTerminalKind.NOOP→SUCCEEDED`（`runtime_outcome.py:505-509`）或 scatter join 现 `SUCCESS`（`runtime_scatter.py:76-98`）单独当该产品终态；join 仍可 complete，但必须写出可查询 disposition + metrics 标签。f) 无 exhaustion proof 的空集仍 422 `SCATTER_EXHAUSTION_PROOF_REQUIRED`。 | `registry.py:73-148`；`intake/api/__init__.py:14-28`；`runtime_scatter.py:76-98`；`runtime_outcome.py:505-509`；`test_registered_api_scatter.py:209-373`；🆕 T09 文件 | 三 member query；zero 独立且零产物 | `NH7-T08` `NH7-T09` `NH7-T10` | disposition 可查询；search 空 |

### 4.6 Phase 6 — 产品闭包

| 编号 | 工作项 | 工作内容 | 涉及文件 / 模块（file:line） | 预期结果 | 测试映射（Test-ID） | 收口标准 |
|------|--------|----------|------------------------------|----------|----------------------|----------|
| `NH7-10` | First-publication closure | a) 每条 T03–T08 成功路径经 PersistencePort 读 Execution `actual_binding_digest` 为 sealed（禁 legacy `s05` 64-hex；`FG-NH-08`）。b) S04 六元组非 stub（消费 NH5）。c) g0.body digest = admitted clean；S06 `context_meta` = S04。d) `mkb_publication_proofs` + active pointer CAS（**复用** `vector_publish_commit.py:57-191`，不复制 tail）。e) search 带 namespace + 至少一个 NH5 facet 键（`semantic_channel` 或 `realm`）命中；`vector_channel=original` 的 hit 正文 = admitted clean；summary 通道仅当测试显式声明。f) 失败格（T10）零 indexed 向量、search 空。 | `vector_publish_commit.py:57-191`；NH3 actual；NH5 facet；T03–T08 各 e2e | 证据链可回溯 | `NH7-T03`..`NH7-T08` | actual/S04/g0/proof/facet 齐 |

---

## 5. Phase 详情

### 5.1 Phase 1 — manifest + clean 合同

- **Phase 目标**：机器可生成 10+3 合法格；admitted clean 非空合同成为后续 live 的前置闸。
- **本 Phase 对应编号**：`NH7-01` / `NH7-02`
- **本 Phase 新增文件**：`tests/unit/test_nh7_activation_manifest.py`；`tests/unit/test_nh7_clean_empty.py`（T10/T02 伴生，可与 T10 同文件）
- **本 Phase 修改文件**：不改 `strategies.py` 闭集行（✅ 生成 matrix）；`semantics.py:44` 保持 `min_length=1`；必要时扩 admitted-clean schema 文档化字段（不锁列名字面）
- **本 Phase 删除文件**：无
- **具体功能预期**：
  1. `len(strategy_cells)==10` 且 `len(op_cells)==3`，digest 与 NH1-T07 预埋 manifest 一致。
  2. matrix 行是 strategy/operation，不是 process_key；`clean.extract.pdf_llm` 对应两行合法格而非一行。
  3. 不存在 40 格或 28 格「全合法」表。
  4. 未知 strategy 409 且零 Task（若走 public ingest）或零 Process 成功。
  5. `CLEAN_EMPTY` / `CLEAN_PDF_TEXT_LAYER_MISSING` / empty member 均不能写出 indexed 向量。
  6. API 成功 member 有 content_digest 与 meta_digest 两个 64-hex，且六元组齐全。
- **对应测试台账项**：`NH7-T01` / `NH7-T02` / `NH7-T10`（详见 §8）
- **收口标准**：T01 PASS；空正文负例已挂号（T10 可后跑，但合同字段在本 Phase 冻结）
- **本 Phase 风险提醒**：手抄矩阵会与 NH1-T07/NH9 生成器分叉；禁止把七意图格写进本 manifest 当 NH8 完成。

### 5.2 Phase 2 — promptA

- **Phase 目标**：LLM 可绑；确定性可证明零模型调用。
- **本 Phase 对应编号**：`NH7-03`
- **本 Phase 新增 / 修改 / 删除文件**：catalog/snapshot 默认 id 对齐（`config_snapshots.py:57-59`；`strategies.py:63-147`；`prompt_profiles.py:49-50`）；🔱 `tests/unit/test_prompt_hash_mismatch.py`；🆕 invocation count 测试
- **具体功能预期**：
  1. 新 ingest 的 LLM 策略 `prompt.key == definition.prompt_key` 且 `content_sha256` 等于 catalog 文件。
  2. 旧 pin 使用非 canonical id 时仍能按冻结指针跑完，不强制热切。
  3. 修改 prompt 文件字节但不改 pointer → `PROMPT_HASH_MISMATCH`。
  4. 跑 `web.deterministic` / `pdf.text_layer` / `doc.deterministic` / API map 时 `llm.complete` call count = 0。
  5. CLI 回退不得用于 OCR/Vision（保持 HEAD `:76`）。
- **对应测试台账项**：`NH7-T02`
- **收口标准**：invocation counts PASS；drift FAIL closed
- **本 Phase 风险提醒**：把 documentation 域 prompt 设成全站默认会让既有 JSON 路径漂移；只对齐 **clean** 角色。

### 5.3 Phase 3 — 确定性/PDF

- **Phase 目标**：inline/static/PDF-first/真 text-layer 在 default-root 走到 query。
- **本 Phase 对应编号**：`NH7-04` / `NH7-05`
- **本 Phase 新增 / 修改 / 删除文件**：改 `clean_preflight.py:46-71`；🆕 `tests/e2e/test_nh7_inline_static_retrieval.py`；🆕 `tests/e2e/test_nh7_pdf_text_retrieval.py`；🔱 删 source e2e patch
- **具体功能预期**：
  1. strategy 来自 sealed actual，不来自 representation 三值折叠。
  2. HTTP PDF 不进 web sanitizer（回归 T02 PDF-first）。
  3. inline 与 static 各一次 namespaced hit，正文 = clean。
  4. local PDF 经 public upload handle，不经 `storage.promote`。
  5. 无文本层 PDF 零 hit，且不盗 OCR 码（观察已由 NH3 分码）。
  6. L3 成功路径源码扫描无 `pipeline._http_fetcher =`。
- **对应测试台账项**：`NH7-T02` / `NH7-T03` / `NH7-T04`
- **收口标准**：T03/T04 L3+L4 PASS；NH6/NH4 未 GO 则保持未观察
- **本 Phase 风险提醒**：假 PDF fixture（仅 Tj 字面量）会在 NH3 诚实观察后失败；必须用真文本层样本。

### 5.4 Phase 4 — browser/print

- **Phase 目标**：声明边真实 DOM 与诚实 print-PDF 可检索。
- **本 Phase 对应编号**：`NH7-06` / `NH7-07`
- **本 Phase 新增 / 修改 / 删除文件**：🆕 `tests/e2e/test_nh7_browser_dom_retrieval.py`；🆕 `tests/e2e/test_nh7_print_pdf_retrieval.py`；接线消费 NH6 ports
- **具体功能预期**：
  1. 仅 `absent` 命中已声明 browser 边；unknown fail-closed。
  2. rendered DOM 含 SPA 主文，不是 lambda `"<main>browser capability text</main>"`。
  3. `web.llm_rewrite` 有 PromptRef 且模型被调用 ≥1；`web.deterministic` rendered 调用 = 0。
  4. print 输出 `%PDF-` + 非常量 profile；clean 走 pdf 通道。
  5. print 路径 `sanitize_html_document` / `clean_html_representation` 零调用。
  6. 两条 query 命中。
- **对应测试台账项**：`NH7-T05` / `NH7-T06`
- **收口标准**：Capstone D query 终态
- **本 Phase 风险提醒**：共享 browser binary 不等于共享 capability；render 绿不得关闭 T06。

### 5.5 Phase 5 — multimodal + API

- **Phase 目标**：5 multimodal 格 + 3 API member 可检索；zero 独立。
- **本 Phase 对应编号**：`NH7-08` / `NH7-09`
- **本 Phase 新增 / 修改 / 删除文件**：🆕 `tests/e2e/test_nh7_multimodal_lanes.py`；🔱 `tests/e2e/test_registered_api_scatter.py` 加 search、删 sqlite3；🆕 exhausted_zero 测试；Task/Execution 投影加 `result_disposition`；scatter join 写 disposition（不把 NOOP 当产品终态）
- **具体功能预期**：
  1. 五格各自 query hit = 该格 admitted clean。
  2. 空 OCR/Vision 不成功、零向量。
  3. 三 provider member 各至少一次 namespaced search 命中。
  4. `publication_ready` 不得单独作为 T08 PASS。
  5. exhausted_zero：counts 全 0、items `[]`、无 publication proof、search 空、metrics 标签 ≠ indexed success、disposition 字段字面 `exhausted_zero`。
  6. 同 fingerprint 再提交 → 同一 disposition，不造第二批 child。
  7. NOOP 映射 succeeded **不足以** 关闭 T09。
- **对应测试台账项**：`NH7-T07` / `NH7-T08` / `NH7-T09` / `NH7-T10`
- **收口标准**：Capstone E/F query 终态；zero 独立
- **本 Phase 风险提醒**：scatter 今日 SUCCESS 零成员是 typed complete 的半边；缺 disposition 仍是 `T-R-NH-24`。

### 5.6 Phase 6 — 产品闭包

- **Phase 目标**：证据链可回溯；假绿扫描全红则不得 executed。
- **本 Phase 对应编号**：`NH7-10`
- **本 Phase 新增 / 修改 / 删除文件**：T03–T08 各文件加证据链断言；不重写 tail
- **具体功能预期**：
  1. actual sealed ≠ domain/legacy alias。
  2. 六元组键集完整且非 `{"source_kind":...}`。
  3. g0 digest = clean digest。
  4. proof 行 + pointer `lifecycle_state=active`。
  5. facet 过滤能命中本格、排除对照格。
  6. 失败格 search 空。
- **对应测试台账项**：`NH7-T03`..`NH7-T08`（正例链）+ `NH7-T10`（负例零向量；台账 D「cross-query」）
- **收口标准**：台账 D 六行谓词
- **本 Phase 风险提醒**：只查 `publication_state=indexed` 而不 POST search 仍是 `FG-NH-04`。

---

## 6. 依赖的冻结设计决策（只读引用）

> 只引 register 的 Q / Truth-ID，不复制业主答文，不改口，不开新 Q/A。

| 决策 / Q ID | 冻结来源 | 本计划中的影响 | 若不成立的处理 |
|-------------|----------|----------------|----------------|
| `T-O-376` | pre-initial QNA | 每条接通路径必须真实 Process→可检索；503 不得当 DoD | 本 AP 不得标 executed |
| `T-O-378` | pre-initial QNA | 假 PDF / monkeypatch / 空 clean 不得冒充完成 | T03–T07 必须真 fixture |
| `T-O-381` | Q1 / pre-initial | 10+3 全部 live-to-vector | 缺格 = 本 AP 未完成 |
| `T-O-383` | Q3 / pre-initial | 绑定后失败无向量 | T10 硬闸 |
| `T-O-386` | Q6 / pre-initial | 一份 admitted clean；promptA 仅 LLM | T02/T10 |
| `T-O-388` | Q8 / pre-initial | 声明式再获取；print 诚实 | T05/T06 禁暗升 |
| `T-O-389` | Q9 / pre-initial | 六元组进 S04 不进 g0 | T03–T08 证据链消费 NH5 |
| Q17 / `T-O-397` | pre-charter | 独立 exhausted_zero | T09；禁 NOOP 顶替 |
| Q13 / `T-O-393` | pre-charter | parser/OCR local ports vs S11 multimodal | T07 分账；不锁库名 |
| Q22 / `T-O-402` | pre-charter | 仅 absent 走已声明 browser | T05 |
| Q23 / `T-O-403` | pre-charter | render/print 分 capability | T05≠T06 |
| Q25 / `T-O-405` | pre-charter | 非法格 admission 不建 Task；本 AP 只用于 10+3 能力非法组合 | T01；七意图矩阵交 NH8 |
| Q26 / `T-O-406` | pre-charter | L1–L4 不可互换；waiver 只延期 | T03–T08 不得降层 |
| `T-R-NH-24` | final HEAD 实测 | NOOP→succeeded 无 exhausted_zero | T09 必须加 disposition |
| `T-R-NH-07/15` | final | handlers/tail 已交付 | 禁重写 intake/；禁复制 tail |

---

## 7. 内置 Reference-Anchor 锚区

### 7.1 锚表（本计划工作要落在哪些既有代码 / 新建点上）

> `处置` 用 README §4.4 复用判定。台账 B 冻结 `NH7-A01`..`NH7-A07`，禁止改 ID。

| 锚 ID | `path:line` | 落点（这是什么）| 本 AP 用途（对应工作项）| 处置 | 备注 |
|-------|-------------|------------------|--------------------------|------|------|
| `NH7-A01` | `src/contracts/intake/strategies.py:15-160` | 10 strategy 闭集 + `resolve_clean_strategy` 409 | `NH7-01` 生成 matrix；未知键非法格 | `✅ 复用` | 非笛卡尔积；不增第 11 策略 |
| `NH7-A02` | `intake/__init__.py:20-132` | 9 capability `dispatch_clean`；PDF-first | `NH7-04` 保留 handlers；PDF 不进 HTML | `✅ 复用` | **禁重写** intake 通道函数 |
| `NH7-A03` | `intake/api/registry.py:73-148` | 3 API strict map + member 422 | `NH7-09` preservation；live fetch OOS | `✅ 复用` | 整批失败；无 silent skip |
| `NH7-A04` | `src/runtime/intake/clean_preflight.py:46-127` | process→strategy 反推 + representation 三值折叠 | `NH7-04/07` 改读 sealed actual / 图 binding | `♻️ 重 substrate` | 一 process 多 strategy；HEAD 反例 |
| `NH7-A05` | `src/runtime/intake/vector_publish_commit.py:57-191` | publication tail CAS（vector fence + proof + pointer） | `NH7-10` 复用 tail；query 仍必需 | `✅ 复用` | 不复制 tail；`layer_b` 现仅 `source_kind` 由 NH5 扩 facet |
| `NH7-A06` | `tests/e2e/test_source_capability_paths.py:99-101,166-168` | patch `_http_fetcher/_browser_fetcher`；断言 `succeeded` | `NH7-04` 🆕 default-root tests；删 patch | `🆕 净新`（测试） | `FG-NH-01`；同文件 `:172` sqlite3 亦禁 |
| `NH7-A07` | `tests/e2e/test_registered_api_scatter.py:209-373` | 三 op map + `publication_ready` + zero `succeeded` 无 search | `NH7-09` ♻️ 加 namespaced search + disposition | `♻️ 重 substrate` | `T-R-NH-24`；`FG-NH-04/12` |

独立核对（2026-08-29，`1221aa1`）：上表行号与 `read_file` 一致。补充只读点（不占新 NH7-Axx）：`runtime_scatter.py:76-98` 零成员 SUCCESS；`runtime_outcome.py:505-509` NOOP→SUCCEEDED；`lsrag_definition.py:1003-1054` 6 张 unselectable；`api/app.py:330-345` 默认无 browser/clean_llm（NH6 接线后本 AP 消费）；`src/runtime/intake/generation_assemble.py:17-62` g0=clean（`:42` body=clean）。

### 7.2 反例 ledger ⛔（别碰区 / 已知陷阱）

| ⛔ | 反例 / 陷阱 | 为什么（依据）|
|----|------------|----------------|
| ⛔1 | monkeypatch `_http_fetcher/_browser_fetcher/_clean_llm` 当 L3 | `FG-NH-01`；`T-O-378`；`NH7-A06` |
| ⛔2 | `publication_ready` / Task `succeeded` 当 query | `FG-NH-03/04`；`NH-RA08-B02` |
| ⛔3 | search 无 namespace | `FG-NH-05`；`src/contracts/api/models.py:505-510` 与 `src/services/retrieval/retrieval_request.py:265-270` 现必 422 |
| ⛔4 | 33 unit / 函数存在 / 图 bootstrap 当 live | `T-R-NH-07` vs `T-O-381`；`FG-NH-13` |
| ⛔5 | 503 / 未部署当 in-scope DoD | `FG-NH-02`；`T-O-376` |
| ⛔6 | 空/空白 clean 或 legacy success flag | `FG-NH-06`；`T-O-378/386` |
| ⛔7 | `WorkflowTerminalKind.NOOP→SUCCEEDED` 冒充 exhausted_zero | `T-O-397`；`T-R-NH-24`；`runtime_outcome.py:505-509` |
| ⛔8 | 笛卡尔 10×4 或 7×4 | `T-O-381/405`；`FG-NH-15` |
| ⛔9 | process→strategy 反推 / print 当 HTML | `NH7-A04`；`NH-RA04-B03/B05` |
| ⛔10 | 只测 API 代表四通道 | `FG-NH-14` |
| ⛔11 | sqlite3 直读 Turso | `FG-NH-12`；scatter/source e2e HEAD 均中招 |
| ⛔12 | 复制 13 profile / 按 lane 复制 tail | `FG-NH-09`；`R-F10` |
| ⛔13 | 把 `_await_terminal` 超时 `running` 改成期待值 | `FG-NH-17`；RA08 称该 e2e 停 running |
| ⛔14 | 重写 `intake/` handlers | `T-R-NH-07`；本 AP 类型 upgrade 激活 |

### 7.3 上游真源指针 + 安全项威胁模型

- **独立 reference-anchor**：RA04 主面（10/9/3、prompt、zero/member）；RA08 publication/query 终验；RA05 **只消费**「供给已接线 / 禁止测试后赋 port」。完整借鉴台账见真源，不把 RA 当新 Truth。
- **安全 / 信任边界类工作项的威胁模型锚**（不得留空）：
  - **假接线**：L3 成功路径赋值 fetcher（`NH7-A06`；`FG-NH-01`）→ T03/T05 源扫描 + 无 patch 跑法。
  - **假检索**：无 namespace / 只 `publication_ready`（`NH-RA08-B02`；`FG-NH-04/05`）→ T03–T09 强制 POST search。
  - **空知识入库**：空 clean / empty member skip（`FG-NH-06`；legacy silent skip）→ T10。
  - **指标欺诈**：exhausted_zero 计入 indexed success（`T-O-397`）→ T09 metrics 断言。
  - **browser SSRF / no-sandbox**：属 NH6 `T-O-399`；本 AP 不降级安全门，T05/T06 使用已硬化 supply。
- 威胁模型尚未在上游做过的部分不得标 `executed`。本 AP 安全项覆盖假接线/假检索/空入库/指标欺诈；runtime 逃逸仍以 NH6/NH9 为准。

---

## 8. 测试台账

> 分层遵守 `T-O-406`：L1 unit / L2 integration·UoW / L3 default-root e2e / L4 retrieval-facet mega。fault 是标签不是替代层。T03–T08 最低 L3+L4。NH6 未 GO ⇒ **T04–T08**（供给依赖格）保持 `未观察`，**不得**用 patch 顶 L3。**T03 只覆盖 inline/static**，不依赖 NH6 binary，browser 不在本 Test-ID。

### 8.1 测试清单（主表）

| Test-ID | 测试项（验证什么）| 类型 | 层 | 来源 | 映射（工作项 → 收口目标）| PASS 证据（四元组）|
|---------|------------------|------|----|------|---------------------------|---------------------|
| `NH7-T01` | matrix/identity/illegal combos | 契约 | L1 | 🆕 `tests/unit/test_nh7_activation_manifest.py`；读 `tests/fixtures/new_harvest/closed_set_manifest.v1.json` | `NH7-01/02` → 合法格闭集 | `commit SHA + matrix PASS + T-O-381 + UTC` |
| `NH7-T02` | prompt hash/drift/deterministic no-model | 集成 | L1/L2 | 🔱 `tests/unit/test_intake_clean_dispatch.py` + `tests/unit/test_prompt_hash_mismatch.py`；🆕 invocation count | `NH7-03/04` → 对齐且零调用 | `commit SHA + invocation counts PASS + Q6 + UTC` |
| `NH7-T03` | inline/static→retrieval | live/mega | L3/L4 | 🆕 `tests/e2e/test_nh7_inline_static_retrieval.py`（PASS 主文件）。HEAD `test_source_capability_paths.py` 未清 patch/sqlite3 前 = **⛔** 不得进跑法 | `NH7-04/10` → query | `commit SHA + query PASS + T-O-376 + UTC` |
| `NH7-T04` | PDF text→retrieval | live/mega | L3/L4 | 🆕 `tests/e2e/test_nh7_pdf_text_retrieval.py`（真实 PDF fixture；local 经 NH4 upload） | `NH7-05/10` → 真 text-layer query | `commit SHA + real PDF query PASS + Q1 + UTC` |
| `NH7-T05` | browser DOM→retrieval | live/mega | L3/L4 | 🆕 `tests/e2e/test_nh7_browser_dom_retrieval.py` | `NH7-06/10` → SPA query | `commit SHA + SPA query PASS + Q23 + UTC` |
| `NH7-T06` | print PDF→retrieval | live/mega | L3/L4 | 🆕 `tests/e2e/test_nh7_print_pdf_retrieval.py` | `NH7-07/10` → print query | `commit SHA + print query PASS + Q23 + UTC` |
| `NH7-T07` | 5 multimodal strategies | live/mega | L3/L4 | 🆕 `tests/e2e/test_nh7_multimodal_lanes.py`（5 格） | `NH7-08/10` → 5 lanes query | `commit SHA + 5 lanes PASS + Q13/Q19 + UTC` |
| `NH7-T08` | 3 API members→query | live/mega | L3/L4 | 🆕 `tests/e2e/test_nh7_registered_api_retrieval.py`（PASS 主文件）。HEAD scatter 未删 sqlite3、未补 search 前 = **⛔** | `NH7-09/10` → 3 operation query | `commit SHA + 3 operation query PASS + Q1 + UTC` |
| `NH7-T09` | exhausted_zero 独立 disposition | 集成/mega | L2/L4 | 🆕 `tests/e2e/test_nh7_exhausted_zero.py`。HEAD scatter `:352-373` 未改前 = **⛔** 不得当 T09 证据 | `NH7-09` → zero 产品终态 | `commit SHA + zero/proof/metrics PASS + Q17 + UTC` |
| `NH7-T10` | empty/bad member/worker failure 零向量 | fault | L1/L3/L4 | ♻️/🆕 空/坏 member/worker fail → 零向量 query | `NH7-02/08/09` → 失败零 hit | `commit SHA + negative query PASS + T-O-383 + UTC` |

#### `NH7-T01`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/unit/test_nh7_activation_manifest.py::test_registry_emits_10_strategy_and_3_ops_not_cartesian`；`::test_identity_strategy_process_representation_split`；`::test_illegal_cells_409_or_422`；`::test_consumes_nh1_preembedded_closed_set_manifest` |
| 用途 | 证明 `NH7-01/02`；`T-O-381/405`；禁 10×4/7×4；消费 NH1-T07 预埋路径 |
| 前置 | 纯 registry import；读取 `tests/fixtures/new_harvest/closed_set_manifest.v1.json`（该文件由 NH1-T07 写入；缺失 = T01 FAIL，不得在本 AP 手抄一份顶替）。10+3 子 digest 字段名锁死：`strategy_cells` / `op_cells` / `intent_illegal` + canonical `digest` |
| 步骤 | a) 从 `CLEAN_STRATEGY_DEFINITIONS` + `REGISTERED_PROVIDER_OPERATIONS` 生成格。b) 断言 10+3，`digest` 与 fixture 上述字段逐字一致。c) 断言 `clean.extract.pdf_llm` / `clean.ocr.local` 各映射 **两** strategy 行。d) 构造未知 strategy、image+deterministic、web strategy+pdf capability。e) 扫描 fixture 无 28/40 全合法表。 |
| 断言细节 | `len(strategy_cells)==10`；`len(op_cells)==3`；非法：HTTP 409/422 或 `MkbError.status in {409,422}`；admission 可判定者零 Task（public create 路径）或矩阵 disposition≠live。`web.browser_print_pdf.channel=="pdf"`。NH9 生成器扩 82 后这四个字段的 canonical 字节必须仍与 NH1-T07 预埋相等。 |
| 负例 | 手抄 10×4；把 6 张 unselectable workflow_key 标 live；把 exhausted_zero 写成 succeeded 格 |
| 跑法 | `uv run pytest tests/unit/test_nh7_activation_manifest.py -q` |
| 层与来源 | L1；`🆕` |

#### `NH7-T02`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🔱 `tests/unit/test_intake_clean_dispatch.py::test_http_pdf_text_layer_never_enters_web_sanitizer`（`:164-176` 保留）。🔱 `tests/unit/test_prompt_hash_mismatch.py` 扩 `::test_promptA_clean_byte_drift_is_prompt_hash_mismatch`。🆕 `tests/unit/test_nh7_llm_invocation_count.py::test_deterministic_and_api_map_zero_complete_calls`；`::test_llm_required_strategy_invokes_complete` |
| 用途 | `NH7-03/04`；`T-O-386`；PDF-first 正例；确定性零模型 |
| 前置 | Recording LLM / 计数包装；禁止把 LLM 配成恒返回空串当成功。L2：真实 PersistencePort 冻结 pointer 后再改文件字节 |
| 步骤 | a) 回归 HTTP PDF 不进 `clean_html_representation`。b) 对 web/pdf_text/doc deterministic 与 API map 注入 recording LLM，dispatch 后 `complete_calls==0`。c) 对 `web.llm_rewrite`（或任一 llm_required）`complete_calls>=1`。d) bootstrap 后改 promptA 文件字节 → `PROMPT_HASH_MISMATCH`。e) canonical catalog 下 strategy.prompt_key 与 pointer 一致。 |
| 断言细节 | PDF-first evidence.channel==`pdf`。确定性路径无 `PROMPT_HASH_MISMATCH`。漂移码稳定。三 SHA 对齐后新 Task 不再因 default vs clean id 互斥而 503。 |
| 负例 | 确定性路径偷调模型；用 monkeypatch 把 LLM 设为 None 然后声称零调用（必须有 recording 对象可计数） |
| 跑法 | `uv run pytest tests/unit/test_intake_clean_dispatch.py tests/unit/test_prompt_hash_mismatch.py tests/unit/test_nh7_llm_invocation_count.py -q` |
| 层与来源 | L1/L2；`🔱` + `🆕` |

#### `NH7-T03`

| 字段 | 要求 |
|---|---|
| 测试位置 | **PASS 主文件** 🆕 `tests/e2e/test_nh7_inline_static_retrieval.py::test_inline_doc_deterministic_namespace_facet_hit`；`::test_http_static_web_deterministic_namespace_facet_hit`。🔱 `tests/e2e/test_source_capability_paths.py` **仅当**已删除 `:99-101` patch、已删 `sqlite3.connect`、search 带 namespace、不以 `running`/`succeeded` 单独 PASS 时列入跑法；否则 §8.2 标 ⛔ 不得 🔱 进 PASS。🆕 `tests/domain/test_nh7_no_fetcher_patch.py::test_l3_success_tests_do_not_assign_fetchers`（L1 伴生，**不得**单独关闭 T03） |
| 用途 | `NH7-04/10`；Capstone C 的 inline/static query；`FG-NH-01/03/05/12/13` |
| 前置 | `create_app()` default-root；NH5 facet 键可用；合法 namespace；**禁止**赋值 `_http_fetcher/_browser_fetcher/_clean_llm`；禁止 sqlite3；NH6 对 static HTTP 至少能走 `http_fetcher`（HEAD 已注入 `http_acquirer`）。**T03 是 NH6 无关的确定性格**：只测 inline/static；browser/PDF/print/multimodal **不在本 ID**。NH6 未 GO **不**使 T03 标 `未观察` |
| 步骤 | a) ingest inline 非空文本（generic 四字段合法）。b) 轮询至 terminal，**不得**以 succeeded 当 PASS。c) POST search + namespace + `vector_channel=original` + 一个 facet（realm 或 `semantic_channel`）。d) HTTP static 真实 HTML fixture（可用本进程测 fixture server 或已允许的回环；**不得** patch pipeline fetcher）。e) 断言 hit 正文 = admitted clean。f) 源扫描 L3 成功测试无 fetcher 赋值。 |
| 断言细节 | HTTP 200 且 retrieval `disposition=ok`；hit payload 含 clean sentinel；`g0` digest = clean（Port 读 layered artifact）；actual sealed；六元组非 stub；proof/pointer 存在。无 namespace → 422 `RETRIEVE_SCHEMA_NAMESPACE_REQUIRED`。 |
| 负例 | 复制 HEAD source e2e 的 patch+sqlite3；Task succeeded 当命中；空 clean 入库 |
| 跑法 | `uv run pytest tests/e2e/test_nh7_inline_static_retrieval.py tests/domain/test_nh7_no_fetcher_patch.py -q`。HEAD 源文件未清 patch 不得追加 |
| 层与来源 | L3/L4；`🆕` 主；源文件未清 = ⛔ |

#### `NH7-T04`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh7_pdf_text_retrieval.py::test_http_pdf_text_layer_namespace_hit`；`::test_local_upload_pdf_text_layer_namespace_hit`；`::test_absent_text_layer_zero_vector` |
| 用途 | `NH7-05/10`；Capstone C PDF；`T-O-378` 真文本层；local 经 NH4 |
| 前置 | 真实 PDF fixture（有文本层 / 无文本层各一）；NH6 parser GO；local 案 NH4-T01 路由存在；`create_app()` 无 patch；namespace；NH5 登记 facet 键（`realm` 或 `semantic_channel`）；禁止 Tj 字面量扫描当 PASS 依据 |
| 步骤 | a) HTTP 获取含文本层 PDF → `pdf.text_layer`。b) public `objects:upload` 同一类 PDF → ingest `local_object`。c) 两案 namespaced **+ facet** search hit = 提取正文（至少一个 NH5 登记键命中本格、排除对照格）。d) 无层 PDF：decode 观察 absent（NH3），clean `CLEAN_PDF_TEXT_LAYER_MISSING` 或等价 typed fail，search 空。 |
| 断言细节 | present：hit 含 fixture 可见字符串（非 `(pdf capability text)` 伪造）；facet 排除对照格。local：DB 有 Item 仅在 ingest 后；upload 当时 search 空（消费 NH4-T04 两步法）。absent：indexed 向量 0。 |
| 负例 | 内部 `promote` 当 local L3；假 `%PDF-` + 正则提取；无层降级 DU |
| 跑法 | `uv run pytest tests/e2e/test_nh7_pdf_text_retrieval.py -q` |
| 层与来源 | L3/L4；`🆕`；NH6/NH4 未 GO → `未观察` |

#### `NH7-T05`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh7_browser_dom_retrieval.py::test_absent_main_text_declared_browser_dom_query`；`::test_web_llm_rewrite_namespace_hit`；`::test_present_or_unknown_does_not_materialize_browser` |
| 用途 | `NH7-06/10`；Capstone D render；`T-O-402/403` |
| 前置 | NH6-T03 PASS；default-root 已注入真实 `browser_fetcher`；SPA fixture；无 patch；namespace；NH5 登记 facet 键 |
| 步骤 | a) static 起点 HTML 空壳 → fact `main_text_presence=absent` → 已声明 browser 边。b) 断言 rendered DOM 含 SPA 主文 sentinel。c) `web.deterministic` namespaced **+ facet** query。d) `web.llm_rewrite` namespaced **+ facet** query + PromptRef。e) present/unknown 对照：零 `intake.acquire.http_browser` 成功 Process。 |
| 断言细节 | profile ≠ `injected-browser-renderer.v1`。L3 测试源无 `_browser_fetcher =`。hit = admitted clean；至少一个 NH5 登记键命中本格、排除对照格。unknown 不得抓浏览器。 |
| 负例 | lambda HTML；常量 profile；handler 暗升 |
| 跑法 | `uv run pytest tests/e2e/test_nh7_browser_dom_retrieval.py -q` |
| 层与来源 | L3/L4；`🆕`；NH6 未 GO → `未观察` |

#### `NH7-T06`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh7_print_pdf_retrieval.py::test_print_fact_pdf_clean_namespace_hit`；`::test_print_path_does_not_call_html_sanitizer`；`::test_render_success_does_not_close_print_lane` |
| 用途 | `NH7-07/10`；Capstone D print；`T-O-388/403` |
| 前置 | NH3-T04 合同；NH6-T04 PASS；default-root print capability；无 patch；namespace；NH5 登记 facet 键 |
| 步骤 | a) 声明 print 边跑 URL。b) fact `representation_kind=print_pdf` 且 raw startswith `%PDF-`。c) strategy actual = `web.browser_print_pdf`。d) 包装/计数 `sanitize_html_document` 零调用。e) namespaced **+ facet** query（至少一个 NH5 登记键命中/排除）。f) 仅 render 成功的对照不得写入 print 格 PASS。 |
| 断言细节 | evidence.channel==`pdf`；capability==`clean.extract.pdf_llm`；hit 来自 PDF clean 正文；facet 排除对照格。无 print supply → 本文件保持未观察，不得改期待 503 当正例。 |
| 负例 | HTML sanitizer；representation 反推；用 T05 绿关闭 T06 |
| 跑法 | `uv run pytest tests/e2e/test_nh7_print_pdf_retrieval.py -q` |
| 层与来源 | L3/L4；`🆕` |

#### `NH7-T07`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh7_multimodal_lanes.py::test_pdf_document_understanding_query`；`::test_pdf_ocr_query`；`::test_doc_document_understanding_query`；`::test_doc_ocr_query`；`::test_doc_vision_query` |
| 用途 | `NH7-08/10`；Capstone E；`T-O-393/399` |
| 前置 | NH6-T06/T07/T09；真实 binary/model；PromptRef；local 经 NH4；无 cloud；无 `latest`；无 patch |
| 步骤 | a) 五格各一次合法 ingest。b) 断言 admitted clean 非空。c) 各一次 namespaced+facet search。d) 空/坏输入对照（可与 T10 共享 fixture）零 hit。 |
| 断言细节 | 五格 hit 正文各等于该格 clean。OCR/Vision 不走 CLI。S11 路径请求含 media/digest 或 handle，不是纯 `input_text`。 |
| 负例 | 五格只跑一个宣称全绿；models-list 当 ready；503 当 PASS |
| 跑法 | `uv run pytest tests/e2e/test_nh7_multimodal_lanes.py -q` |
| 层与来源 | L3/L4；`🆕`；不可降层；缺供给 → `未观察` 而非 skip-pass |

#### `NH7-T08`

| 字段 | 要求 |
|---|---|
| 测试位置 | **PASS 主文件** 🆕 `tests/e2e/test_nh7_registered_api_retrieval.py::test_chinatax_member_namespace_hit`；`::test_domain_member_namespace_hit`；`::test_realestate_member_namespace_hit`。HEAD `::test_registered_api_three_raw_provider_operations_map_seal_and_persist_semantics` **仅当**已删除 `import sqlite3` / `sqlite3.connect`、每 operation 已 POST namespaced search 且命中以 search body 为准时才可追加；否则 §8.2 **⛔** 不得 🔱 |
| 用途 | `NH7-09/10`；Capstone F member query；`FG-NH-04/05/12/14` |
| 前置 | caller-frozen records（与 HEAD cases `:214-245` 同构合法 member）；namespace；NH5 六元组；`create_app()`；禁止 live 爬虫 |
| 步骤 | a) 三 (provider, operation) 各 ingest。b) 不等 `publication_ready` 当 PASS。c) 各 POST search + namespace + facet。d) Port 读 child proof/pointer。 |
| 断言细节 | 三 hit 各含该 member `clean_text` sentinel。六元组键集完整。search 省略 namespace → 422。 |
| 负例 | 只断言 `:321` `publication_ready`；sqlite3 直读；三 op 只跑一个 |
| 跑法 | `uv run pytest tests/e2e/test_nh7_registered_api_retrieval.py::test_chinatax_member_namespace_hit tests/e2e/test_nh7_registered_api_retrieval.py::test_domain_member_namespace_hit tests/e2e/test_nh7_registered_api_retrieval.py::test_realestate_member_namespace_hit -q`。HEAD scatter 未清 sqlite3+search 前 **不得**追加 |
| 层与来源 | L3/L4；**PASS = 🆕**；未清 sqlite3/search 的 HEAD = ⛔ 进 §8.2，不得出现在 8.1 来源列当 🔱 |

#### `NH7-T09`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh7_exhausted_zero.py::test_disposition_exhausted_zero_not_indexed_success`；`::test_exhaustion_proof_retrieval_empty`；`::test_same_fingerprint_replay_same_disposition`；`::test_noop_terminal_alone_is_not_product_zero`。**不**把未改的 HEAD `test_registered_api_scatter.py:352-373` 列入测试位置 |
| 用途 | `NH7-09`；Q17 / `T-O-397`；`T-R-NH-24` |
| 前置 | `records=[]` + `collection_exhaustion_proof=caller_frozen_records.v1`（或 NH 冻结的同等 immutable proof 字面）；同 fingerprint 再提交；metrics 可查询（标签或计数器） |
| 步骤 | a) 提交合法零集合。b) 读 Task：技术状态可 succeeded，`result_disposition=="exhausted_zero"`。c) Port：child/item/revision/vector/publication_proof count = 0。d) namespaced search 空且 HTTP 2xx（`disposition=empty` 或 hits=[]）。e) 指标：indexed success **不** +1。f) replay 同 disposition。g) 仅触发 NOOP 映射的合成路径 **不能** 写出 `exhausted_zero`。h) 无 proof 空集仍 422。 |
| 断言细节 | 字面与 metadata `no_change` 不等。不得出现 child execution。search 必须真实 POST。 |
| 负例 | NOOP→succeeded 当本项 PASS；把 zero 写成 failed 诱导重试；计入 indexed；用 HEAD `:352-364` `status==succeeded`+counts0 当 T09 |
| 跑法 | `uv run pytest tests/e2e/test_nh7_exhausted_zero.py::test_disposition_exhausted_zero_not_indexed_success tests/e2e/test_nh7_exhausted_zero.py::test_exhaustion_proof_retrieval_empty tests/e2e/test_nh7_exhausted_zero.py::test_same_fingerprint_replay_same_disposition tests/e2e/test_nh7_exhausted_zero.py::test_noop_terminal_alone_is_not_product_zero -q` |
| 层与来源 | L2/L4；`🆕` 唯一 PASS。源码扫描须覆盖 scatter 文件：未改的 `:352-373` 不得当回归绿件 |

#### `NH7-T10`

| 字段 | 要求 |
|---|---|
| 测试位置 | 🆕 `tests/e2e/test_nh7_failure_zero_vector.py::test_clean_empty_zero_vector_query`；`::test_empty_member_batch_fail_zero_vector`；`::test_bad_member_schema_zero_vector`；`::test_worker_failure_after_bind_zero_vector`。🆕 unit `tests/unit/test_nh7_clean_empty.py::test_web_doc_pdf_llm_raise_clean_empty`（补 `NH-RA04-B08`；L1 不得单独关闭 T10） |
| 用途 | `NH7-02/08/09`；`T-O-383`；台账 D 负例 + cross-query 无残留向量 |
| 前置 | default-root；namespace；失败后仍 POST search。worker fail：绑定后注入 typed 失败（缺 blob / LLM 超时 / 坏 image），**不是**未部署 503 正例 |
| 步骤 | a) 空 HTML/空 rewrite/空 doc → `CLEAN_EMPTY`。b) member `clean_text=""` 或缺键 → 422 整批。c) 绑定后 worker fail。d) 各案 namespaced search 对 sentinel 空；Port 计 indexed 向量 0。e) 对照：同 namespace 下一篇合法文档仍可命中（证明 search 本身可用）。 |
| 断言细节 | 失败案 HTTP 非「检索命中」；向量表无该 Task 的 indexed 行。unit 有 `CLEAN_EMPTY` 字面。L1 空 raise 不得顶 L4 零 hit。 |
| 负例 | empty member skip 后其余入库；503 当失败正例却标通道 DoD |
| 跑法 | `uv run pytest tests/unit/test_nh7_clean_empty.py tests/e2e/test_nh7_failure_zero_vector.py -q` |
| 层与来源 | L1/L3/L4；`🆕`；L1 不可单独 PASS |

### 8.2 复用台账（沿用 / fork 的既有用例明细）

| 既有用例 | 处置 | 改动 | 起跑线状态 |
|----------|------|------|------------|
| `tests/unit/test_intake_clean_dispatch.py::test_http_pdf_text_layer_never_enters_web_sanitizer` | `♻️ 沿用` + 纳入 T02 | 0 改动正例 | HEAD PASS |
| `tests/unit/test_prompt_hash_mismatch.py` | `🔱 fork` | + promptA clean 路径漂移 | HEAD 测 promptB/L4；需扩 |
| `tests/e2e/test_source_capability_paths.py` | 未删 patch/sqlite3 前 = **⛔ 反例**（不得 🔱 进 T03 PASS）。清 patch、Port 化、补 namespace search 后才可 🔱 | 删除 `:99-101`；禁止 `running` 期待值 | HEAD 红/假接线（D-24）；RA08 `NH-RA08-B01` |
| `tests/e2e/test_registered_api_scatter.py:209-373` | 未删 sqlite3、未补 search 前 = **⛔** 不得以 HEAD 绿灯关 T08，也不得标 🔱 进 8.1 来源列。T08 PASS 主文件 = 🆕 `test_nh7_registered_api_retrieval.py`。HEAD `:352-373` zero 段未改成 `exhausted_zero`+namespaced empty 前 = **⛔** 不得当 T09 或回归绿件 | `publication_ready` 保留但不足 | HEAD 三 op map 绿、零 search、zero=`succeeded` |
| `tests/unit/test_intake_provider_registry.py` 等 33 绿 | `♻️ 沿用` 分母对照 | 0；**不得当 L3** | `T-R-NH-07` |
| NH1-T07 `closed_set_manifest.v1.json` | `♻️ 沿用` 预埋 | T01 只读 | NH1 产物；缺失则 T01 FAIL |
| NH4-T04 upload→ingest | `♻️ 消费` 两步法 | T04 local PDF 走 public upload | 属 NH4 |
| NH5-T07 facet search | `♻️ 消费` 键与 SQL 过滤 | T03–T08 带 facet | 属 NH5 |
| NH6-T03/T04/T06/T09 | `♻️ 消费` 供给 GO | 本 AP 不补隔离 | 属 NH6；未 GO 则 T05–T07 未观察 |

### 8.3 分层与跑法（各类型在哪跑、何时跑）

| 类型 | 跑法 / 频率 | 主要层 | 触发时机 |
|------|-------------|--------|----------|
| 短途 | `uv run pytest tests/unit/test_nh7_activation_manifest.py tests/unit/test_nh7_llm_invocation_count.py tests/unit/test_nh7_clean_empty.py tests/domain/test_nh7_no_fetcher_patch.py -q` | L1 | 每 PR |
| 集成 | T02 dispatch+prompt；T09 disposition UoW | L1/L2 | Phase 1–2 / Phase 5 |
| default-root live | T03–T08 `create_app()` | L3 | T03（inline/static）可在 NH6 前跑；T04–T08 等 NH6 GO |
| mega query | T03–T09 namespaced+facet search | L4 | **本 AP 退出硬闸** |
| fault | T10 零向量 | L3/L4 | 与各格并行，收口必跑 |
| soak / crash 全窗 | 本 AP 不跑 | — | 交 NH9 |

本 AP 台账 C 最低层不得自行降：T01 L1；T02 L1/L2；T03–T08 L3/L4；T09 L2/L4；T10 含 L4 负例。

### 8.4 测试缺口（本 AP 明确不覆盖什么 + 交给谁）

- 不覆盖生产隔离 / SBOM / CVE / `/ready` 正负与 NH6 供给本身（理由：`S-NH-F6`；RA05）→ `AP-NH6`。本 AP **消费** `create_app()` 已接线；未 GO 则 **T04–T08** `未观察`。T03 仅 inline/static，不在此条。
- 不覆盖七意图合法/非法 applicability 与 intent code 闭集（理由：`T-O-405` 主体）→ `AP-NH8`。本 AP 只测 10+3 能力非法格。
- 不覆盖 rebuild/metadata exact-clean 旁路、deactivate 后 query 法（理由：`T-O-407`）→ `AP-NH8`。
- 不覆盖 crash 全窗 `W-NH-CREATE/SEL/SEAL/PROCESS/FANIN/PUB/OUTBOX` 与 closed-set 生成器（理由：`S-NH-F9`）→ `AP-NH9`。Capstone C–F 的 **query 终态** 必须已在本 AP，NH9 只回归不补功能。
- 不覆盖 live connector / 供应商爬虫（理由：`T-O-381` OOS；`NH7-A03` live fetch OOS）。
- 不覆盖 existing-object upgrade（理由：`T-O-401`）。
- **不在本 AP 假装覆盖** NH5 facet SQL 实现（只消费键）；**不假装覆盖** NH4 upload 生命周期竞态。

### 8.5 测试保真（防假绿 · 刻死）

- ✅ 每个 PASS 必带四元组：`commit SHA + pytest node PASS + Truth/Q + UTC`。计数 ≠ 价值（33 unit ≠ 10+3 live）。
- 本 AP 适用 FG（必须在对应细则点名）：
  - `FG-NH-01`：T03–T07 成功路径无 fetcher/LLM patch。
  - `FG-NH-02`：503 只出现在独立负例，不得关闭正格。
  - `FG-NH-03/04`：T03–T08 以 search hit 为准，不以 Task succeeded / `publication_ready`。
  - `FG-NH-05`：所有 L4 body 有 namespace。
  - `FG-NH-06`：T02/T10 空 clean 不得入库。
  - `FG-NH-07`：证据链六元组非 stub（消费 NH5）。
  - `FG-NH-08`：actual 非 legacy 64-hex。
  - `FG-NH-10`：T04 local 经 public upload。
  - `FG-NH-12`：禁 sqlite3 直读。
  - `FG-NH-13`：T03–T08 不得降成 L1。
  - `FG-NH-14`：inline/local/http/API 各自 representative + 全部合法 strategy 格。
  - `FG-NH-17`：禁止把 running 改成期待值；waiver 不得改期待。
- `degraded` 必带机器可读 `reason`；NH6 未就绪标 `未观察`，不是 skip-pass。
- 安全项 T03/T08/T09/T10 含攻击向量：patch、无 namespace、空 member skip、NOOP 冒充 zero、指标虚增。

---

## 9. 风险、依赖与完成后状态

### 9.1 风险与依赖

| 风险 / 依赖 | 描述 | 当前判断 | 应对方式 |
|-------------|------|----------|----------|
| DAG：NH1 STOP | chosen-shape 证伪 | high（外部） | 本 AP 不得开工 |
| DAG：NH2/NH3 | 边不可达 / actual 未封 / print 不诚实 | high | join 失败则 T05–T07 无法合法选中 |
| DAG：NH6 供给 | default-root 无 binary/model | high | **T04–T08** `未观察`；禁 patch（`R-F05`/`FG-NH-01`）。T03 inline/static 不依赖 NH6 binary |
| DAG：NH4 | local 无 public handle | high（local 格） | T04/T07 local 案等 NH4 |
| DAG：NH5 | facet 键未落地 | high | L4 不能只 source_kind |
| `R-F10` | 按 lane 复制 publication tail | high | architecture：三 kind 共享 tail 源；只复用 `NH7-A05` |
| `R-F13/14` | L1 或 Task/flag 顶 L3/L4 | high | T03–T08 硬闸 query |
| `R-F05` | 供应链/license 阻塞 NH6 | high | 本 AP 不改 pin；owner waiver 只延期 |
| promptA 对齐伤旧 pin | 热切 catalog | medium | 旧 ref exact replay |
| zero 指标分叉 | succeeded 仍被当 indexed | high | T09 metrics 标签 |
| print 死合同残留 | 反推未删 | high | `NH7-A04` 必须改读 actual |

### 9.2 约束与前提

- **技术前提**：HEAD `1221aa1` 10/9/3 纯函数与 tail CAS 保留；NH2 kind 图已声明全部合法边；NH3 actual/fact/print 诚实；NH5 六元组+facet SQL；NH6 default-root 注入真实 ports。
- **运行时前提**：`create_app()` 无测试变异可达供给；namespace 必填；生产禁 `--no-sandbox`（NH6）。**T04–T08** 在 NH6 未 GO 时不得标 PASS。T03 只测 inline/static，可在 NH6 前标 PASS，**仍禁止** patch。
- **组织协作前提**：不重开 Q17；不新增 owner-gate；`G-NH-14` 保持空号（promptA 为执行项）。不改 AP-NH1..NH5 文件。
- **上线 / 合并前提**：`NH7-T01`..`NH7-T10` 规定最低层 PASS；10+3 manifest 无 waiver 覆盖 `T-O-376/378/381/383`。

### 9.3 文档同步要求

- 需要同步更新的设计文档：公开 Task `result_disposition` 字段说明（执行期；不改 QNA/final）
- 需要同步更新的说明文档 / README：live 闭集「函数存在 ≠ 通道接通」改为指向本 AP evidence
- 需要同步更新的测试说明：§8 + evidence pack `docs/evidence/new-harvest/AP-NH7/`

### 9.4 完成后的预期状态

1. 10 strategy + 3 operation 每合法格至少一条 default-root L3+L4：真实 input → nonempty admitted clean → namespaced+facet hit。
2. `_clean` 以 sealed actual/图 binding 选工人；print 走 PDF clean；HTTP PDF 不进 HTML sanitizer。
3. promptA canonical catalog 对齐；确定性零模型调用；漂移 fail-closed。
4. `exhausted_zero` 可查询、不计 indexed、零产物、retrieval 空、可 replay。
5. 失败格零向量；Capstone C–D–E–F 的 query 终态已在本 AP，NH8/NH9 不第一次补这些功能。

---

## 10. 收口（Definition of Done = 测试台账全 PASS 映射）

### 10.1 收口硬闸

所有退出层测试必须 **PASS 且四元组证据齐全**。NH6 未 GO 的 L3/L4 项保持 `未观察` ⇒ **不得**标 `executed`。

1. 10+3 合法矩阵由 registry 生成；非法格 fail-loud；无 10×4/7×4（`NH7-T01`..`NH7-T09`）。
2. clean 非空；PromptRef 适用于 LLM；确定性零调用；失败零向量（`NH7-T02`/`NH7-T10`）。
3. inline/static/PDF/browser/print/5 multimodal 均 default-root 无 patch 从真实 input 到 query（`NH7-T03`..`NH7-T07`）。
4. 三 API member 各 namespaced 命中（`NH7-T08`）。
5. exhausted_zero 独立：非 indexed success、零产物、proof+empty+replay；NOOP 不足（`NH7-T09`）。
6. 每成功路径 actual/S04/g0/S06/proof/pointer/facet 可回溯（`NH7-T03`..`NH7-T08` + T10 负例无残留）。
7. 假绿扫描：无 503/patch/empty/`publication_ready`/无 namespace 顶替（§8.5 FG 清单）。
8. 10+3 manifest 无 waiver 覆盖 foundational completeness（final §7.7 DoD）。

### 10.2 收口映射表（收口目标 ↔ Test-ID ↔ 证据）

| 收口目标 | 工作项 | Test-ID | PASS 证据（四元组）| 状态 |
|----------|--------|---------|---------------------|------|
| 10+3 合法矩阵；非法格 fail | `NH7-01` | `NH7-T01`..`NH7-T09` | `commit SHA + manifest/test map PASS + T-O-381 + UTC` | `未观察` |
| clean 非空；evidence/digest/PromptRef；失败零向量 | `NH7-02` `NH7-03` | `NH7-T02` `NH7-T10` | `commit SHA + clean artifacts PASS + T-O-386 + UTC` | `未观察` |
| source lanes：default-root 无 patch，真实 input 到 query | `NH7-04`..`NH7-08` | `NH7-T03`..`NH7-T07` | `commit SHA + Task/Process/query trace PASS + T-O-376 + UTC` | `未观察` |
| API lanes：每 operation member 命中；zero 独立且零产物 | `NH7-09` | `NH7-T08` `NH7-T09` | `commit SHA + child proof+result PASS + Q17 + UTC` | `未观察` |
| semantic/publication：actual/S04/g0/S06/proof/pointer/facet 可回溯 | `NH7-10` | `NH7-T03`..`NH7-T08`；负例 `NH7-T10` + cross-query | `commit SHA + evidence chain PASS + T-O-389/406 + UTC` | `未观察` |
| fake-green：无 503/patch/empty/publication flag 顶替 | 全项 | scan + L3/L4 | `commit SHA + FG report PASS + T-O-406 + UTC` | `未观察` |

**谓词形态（判定句，禁止「测试通过」空话）**：

- **合法矩阵**：从 `CLEAN_STRATEGY_DEFINITIONS` 与 `REGISTERED_PROVIDER_OPERATIONS` 生成的合法格恰好 10+3；fixture `tests/fixtures/new_harvest/closed_set_manifest.v1.json` digest 可复现；不存在 7 intents×4 kinds 或 10 strategies×4 kinds 的全合法表；未知 strategy 或非法 representation 返回 409/422，且 admission 可判定者经 PersistencePort 计 `mkb_tasks` 新增 = 0（或 runtime 可知者 Task failed 且 indexed 向量 = 0）。
- **clean contract**：成功格 admitted `clean_text` 去空白后长度 ≥ 1 且 `clean_digest` 为 64-hex；`llm_required` 格 evidence 含与 definition 一致的 PromptRef；确定性格与 API map 的 `CleanLanguageModel.complete` 调用次数 = 0；失败格 namespaced search hits 不含该 sentinel。
- **source lanes**：`create_app()` 默认组合根、测试源码无 `._http_fetcher =` / `._browser_fetcher =` / `._clean_llm =` 赋值；inline、HTTP static、真 PDF text-layer、browser DOM、print-PDF、五 multimodal 各至少一次 `POST /v1/teams/{t}/retrieval:search`（含 `namespace_key` **且** 至少一个 NH5 登记 facet 键 `realm` 或 `semantic_channel` 命中本格、排除对照格）HTTP 2xx 且 hit 正文等于该格 admitted clean。
- **API lanes**：chinatax/domain/realestate 各至少一次 member search 命中其 `clean_text`；`records=[]`+exhaustion proof 的父 Task `result_disposition=="exhausted_zero"`，child/revision/vector/publication_proof 计数 = 0，search 空，indexed-success 计数器不增加，同 fingerprint replay 同 disposition。
- **semantic/publication**：同一成功 Execution 上 actual 已 sealed 且不等于 legacy `s05` alias；S04 六键齐全且 JSON ≠ `{"source_kind": ...}`；g0.body digest = clean digest；存在 publication proof 与 active pointer；facet 键可命中本格、排除对照格。
- **fake-green**：T03–T08 PASS 命令不包含仍赋值 fetcher 的 HEAD 节点；无 namespace 的 search 不得 200；`publication_ready` 不得作为唯一断言。

### 10.3 Definition of Done

| 维度 | 完成定义 |
|------|----------|
| 功能 | §10.2 六条谓词成立；Capstone C/D/E/F query 终态可被 NH9 回归 |
| 测试 | `NH7-T01`..`NH7-T10` 全 PASS（退出硬闸项四元组齐全）；NH6 未 GO 的项不得用 patch 改写成 PASS |
| 文档 | 本 AP 仍 `draft` 直至执行回填；evidence pack 文件存在且 SHA 真实 |
| 风险收敛 | `R-F13/14` 由 L4 query 关闭；`R-F05` 不在本 AP 假装关闭 |
| 可交付性 | NH8 可假设 live clean 已存在；NH9 不第一次补 10+3 功能 |

**Evidence pack 目录**（final §9.3；本 AP 只规定文件名，不伪造 SHA）：`docs/evidence/new-harvest/AP-NH7/`

1. `manifest.json`：commit、Truth/Q（Q17/`T-O-376/381/386/397`）、work `NH7-01..10`、test `NH7-T01..10`、UTC
2. `tests.txt`：node IDs、exit code、duration、environment
3. `queries/matrix.json`、`queries/inline-static.json`、`queries/pdf-text.json`、`queries/browser-dom.json`、`queries/print-pdf.json`、`queries/multimodal-5.json`、`queries/api-3.json`、`queries/exhausted-zero.json`、`queries/negatives.json`、`queries/evidence-chain.json`
4. `migrations/`：`M-NH-07` catalog 对齐 before/after（若有 DDL/指针行）；无则记录「catalog-only」
5. `security/`：no-patch 扫描、namespace 422、empty-clean 零向量、zero 非 indexed
6. `closure.md`：台账 D 逐目标 PASS/FAIL 与 NOT-success 扫描

### 10.4 NOT-成功识别

> 任一退出硬闸测试 `degraded / 未观察` ⇒ **不得标 `executed`**。

下列任一成立即 **NOT-成功**（抄 final §7.7 并补本 AP 假绿）：

1. 33 unit 全绿宣称 10+3 live
2. 函数/图/process_key 存在宣称通道接通
3. 503 / 诚实未部署当正格 DoD
4. Task `succeeded` 当可检索
5. `publication_ready` 当 query
6. 无 namespace 的 retrieval 200
7. patched fetcher/LLM 当 L3
8. 空 clean / empty member skip 入库
9. `NOOP→succeeded` 当 `exhausted_zero`
10. exhausted_zero 计入 indexed success 或造了 child/vector/proof
11. 笛卡尔 10×4 或 7×4
12. process→strategy 反推仍在成功路径
13. print 走 HTML sanitizer
14. local 格用内部 `promote` 冒充 upload
15. 只测 API 宣称四通道
16. sqlite3 直读 Turso
17. 把 `running` 改成期待值保绿
18. NH9 才第一次补本应属于本 AP 的 query 终态

---

## 11. 执行日志回填（仅 `executed` 状态使用）

> 文档状态为 `draft`，本节省略实填。执行完成后改用 append 模板 `respond-execution-log`。residual 交后继 charter，不回填本阶段。

- **实际执行摘要**：待执行后回填。
- **Phase 偏差**（逐条带分类）：待执行后回填。
- **阻塞与处理**：待执行后回填。NH6 未 GO 必须记 `未观察`，禁止 patch 后改记 PASS。
- **测试发现**（含全绿计数 + 新暴露事实）：待执行后回填。
- **后续 handoff**：`AP-NH8`（七意图 / exact-clean；假定 live clean 已存在）；`AP-NH9`（closed-set 回归 Capstone C–F，不补功能）。

---

## 附录 · 修订历史

| 版本 | 日期 | 作者 | 主要变更 |
|------|------|------|----------|
| `v0.1` | `2026-08-29` | Grok workflow new-harvest-nh6-nh9-action-plans | 由 final §7.7 派生；HEAD `1221aa1` 独立核行号；消费 NH1–NH6 交接与 RA04/RA08 |
| `v0.2` | `2026-08-29` | Grok fix-fleet | 吸收已核实 review：T09 PASS 只跑 🆕 exhausted_zero 四 node，HEAD zero 段 ⛔；T03/T08 8.1 来源改为 🆕/⛔ 对齐跑法；T03 从「NH6 未 GO ⇒ T03–T08 未观察」排除；⛔3 锚改为 `src/contracts/api/models.py:505-510` + `retrieval_request.py:265-270`；g0 overlay `generation_assemble.py:17-62` |
| `v0.3` | `2026-08-29` | Grok recon-fix | T04/T05/T06 步骤与 source-lanes 谓词补 NH5 facet 命中/排除；T01 锁死 manifest `strategy_cells`/`op_cells`/`intent_illegal`/`digest` 字段 |
